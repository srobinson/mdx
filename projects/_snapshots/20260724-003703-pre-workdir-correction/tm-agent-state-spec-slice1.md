# Slice-1 Build Spec — Active-tier split + idle fix + needs_you{asked}

Builder: fresh Fable instance (pane %933). Reviewers: codex + opus + grok +
fable(scout) — review against this spec.
Grounding: `tm-agent-state-scout-seam.md` (reuse map), `tm-agent-state-proposal.md`
(design, locked). Scope: wire+transcript only. No permission-gate detection, no
codex protocol pin, no ScrollbackRing work (Slices 2/3). Stall mechanism untouched.

Locked decisions baked in: wire vocabulary lives on `@tm/contract/activity`
(`wire.ts`, extended in place); derivation stays in `@tm/activity`; in-place
enum replace, no back-compat, no parallel field.

## 1. Canonical wire vocabulary (`packages/contract/src/activity/wire.ts`)

**Call: flat `as const` string union, not a `{tier, sub}` DTO.** One line why:
`status_counts` rollups, SSE delta frames, and the strip all key on one flat
string, and the tier is a pure dep-free derivation — structure would churn
every consumer for zero information gain.

```ts
export const activityStatuses = [
  "starting",
  "reasoning",        // was "thinking" — extended thinking / reasoning tokens
  "generating",       // NEW — producing response text
  "running-tools",
  "needs-you-asked",  // was half of "needs-you" — explicit AskUserQuestion
  "needs-you-gated",  // RESERVED — no source until Slice 2/3; ships now so the
                      // enum never takes a second structural change
  "idle",             // NEW — turn complete, waiting; NOT needs-you
  "stalled",          // untouched (decision d)
  "exited",
] as const;
```

Terminal stays the single `exited` value: `exit_reason` on `ActivityWireRun`
already carries the done/error distinction; splitting it adds churn, no info.

**Tier derivation** (pure, dep-free — allowed by the `packages/AGENTS.md`
contract clause, same family as `emptyStatusCounts()`):

```ts
export type ActivityStatusTier = "active" | "needs_you" | "idle" | "stalled" | "terminal";
export function activityStatusTier(status: ActivityStatus): ActivityStatusTier;
// starting|reasoning|generating|running-tools → "active"
// needs-you-asked|needs-you-gated → "needs_you"
// idle → "idle" · stalled → "stalled" · exited → "terminal"
```

`stalled` maps to its own tier: it is TM's health overlay, not a canonical
model tier; do not shoehorn it into active or idle.

**Structured needs_you payload** — declared now so Slice 2 only adds a variant:

```ts
export interface ActivityNeedsYouAsked { kind: "asked"; }
export type ActivityNeedsYou = ActivityNeedsYouAsked; // Slice 2 adds { kind: "gated"; ... }
```

`ActivityWireRun` gains `needs_you: ActivityNeedsYou | null` (null unless the
status is a needs-you value). Question text stays on `last_message` (already
flows via `messageText`); do not duplicate it into the payload in Slice 1.

`emptyStatusCounts()` regenerates mechanically from the new array. Fixtures on
`@tm/contract/activity/testing` (`packages/contract/src/activity/fixtures.ts` /
`testing.ts`) update to the new vocabulary + `needs_you` field.

## 2. Domain machine (`packages/activity/src/domain/runActivityMachine.ts`)

State renames/additions (machine state names may mirror wire values, but the
wire never reads them directly again — see mapping fn below):

- **Rename `thinking` → `reasoning`.** All existing `thinking`-targeting
  transitions (turn-open, tool-result-leaves-no-pending, stall-recovery
  fallback) retarget to `reasoning`. Rationale: pre-first-block and post-tools
  the model is computing; `reasoning` is the honest active default, refined by
  the next parsed record. `runActivityContext.ts` helpers
  (`statusAfterUsageRecord`, `statusBeforeStall`, `lastActiveStatus` values)
  follow the rename mechanically.
- **Split `applyTurnNeedsUser`** into two actions:
  `record.assistant_turn_ended` → new state `idle`;
  `record.question_asked` → new state `needs-you-asked`. Both keep the current
  behavior of clearing stalled fields and `pendingToolCallIds`. The existing
  needs-you transitions (tool_result answers the question → back to active)
  move to `needs-you-asked`; `idle` gets the same wake-up transitions
  (turn-open, tool_use, question_asked, usage, exited).
- **New states `generating`** (entered on new event `record.generating`) and
  event `record.reasoning` (→ `reasoning`, reenter). Both follow the
  `applyTurnOpen` pattern: `clearStalledFields()`, set status +
  `lastActiveStatus`. Add both events to every non-final state's `on` map,
  matching how `record.tool_use` is wired today.
- **`needs-you-gated`**: no machine state in Slice 1 (no event source). The
  wire value exists; the machine cannot reach it. Document with one comment.

**Event plumbing:** add record kinds `reasoning` and `generating` to
`activityRecordKinds` and `activityRecordKindEventTypes` in
`packages/activity/src/ports.ts`; `activityRecordToEvent` in
`packages/activity/src/service/runActivityEvents.ts` follows the table.

**Mapping function (kills the cast):** in
`packages/activity/src/projections/workspaceActivity.ts`, replace
`status: snapshot.value as ActivityStatus` in `runActivityProjection` with an
exhaustive `wireStatusFromMachineState(state): ActivityStatus` (switch with a
`never` default so a new machine state fails compile, not leaks to the wire).
Home: `packages/activity/src/domain/` next to the machine. The projection also
derives `needs_you`: `{ kind: "asked" }` when the mapped status is
`needs-you-asked`, else `null`.

## 3. Parsing (`packages/activity/src/adapters/transcriptRecords.ts`)

Emit records **in block order** within one assistant message (reasoning →
generating → tool-use as they appear); the last record wins as current status,
which is the correct "most recent act" semantic for journaled (non-streamed)
messages.

- **Claude** (`claudeActivityRecords`): parse `thinking` blocks → one
  `reasoning` record per message (before text/tool records). Parse `text`
  blocks → one `generating` record (text continues to ride as `messageText`).
  `AskUserQuestion` handling unchanged.
- **Codex** (`codexActivityRecords`): stop dropping the `reasoning`
  response_item → `reasoning` record. `message` item → `generating` record in
  addition to `codexMessageText()`.
- **stop_reason widening (fail-loud, SCHEMA-LOCK principle).** Replace the
  single `"end_turn"` check with an explicit exhaustive table:
  `end_turn | max_tokens` → `turn-end` (turn is over → idle);
  `refusal` → `transcript-error` record with reason `refused-turn` (visible
  stalled/anomaly path, NOT idle);
  `tool_use | pause_turn` → no record (tool records / continuation already
  carry status); **any other value** → `transcript-error` record with reason
  `unmapped-stop-reason:<value>` (drives the existing `stalled` path — visible,
  never silent). Table is `as const`; add a telemetry counter if
  `packages/activity/src/telemetry.ts` exposes a seam, else skip.
- **Scaffold dedupe (in-file, while touched):** fold `claudeUsage()` /
  `codexUsage()` onto the shared `usageTotals()` normalizer once, and extract
  the repeated `safeRecord`/drop-sink/builder scaffold shared by both
  `*ActivityRecords()` functions. File is 316 LOC; stay in-file unless the
  additions push past ~600, then split a sibling `recordScaffold.ts`.

## 4. Browser + router

- `packages/activity/src/server/activityRouter.ts`: `runToWire` adds
  `needs_you`; `rollup` is mechanical via `emptyStatusCounts()`.
- `www/packages/core/src/activityStreamEvents.ts`: type-level only (imports
  from `@tm/contract/activity`).
- `www/packages/canvas/src/model/runVitalsStore.ts`: counts follow the enum;
  no logic change expected beyond types.
- `www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx`: new
  `STATUS_LABELS`: starting "Starting", reasoning "Thinking", generating
  "Responding", running-tools "Tools", needs-you-asked "Needs you",
  needs-you-gated "Needs you", idle "Idle", stalled "Stalled", exited
  "Exited". Replace the hand-rolled `needsYou` special-case with
  `activityStatusTier(status) === "needs_you"` from the contract (DRY: one
  tier authority).

## 5. PR breakdown — ONE PR

**Recommendation: a single PR**, commits ordered contract → domain → adapters →
router/browser. The slice-4 contract→core→canvas family (#254/#255/#256) worked
because it was purely additive; an in-place enum replace breaks every consumer's
typecheck the moment `wire.ts` changes, so no intermediate PR can leave the
monorepo compiling without reintroducing the parallel/staged vocabulary that
decision (b) forbids. Atomicity is forced by the typechecker; use commit
granularity, not PR granularity, for review navigation.

## 6. Acceptance + gates

**Red-first tests** — each must FAIL on main before its change lands, and
assert the observable end-state, not an intermediate mapping:

1. `packages/activity/src/domain/runActivityMachine.test.ts`:
   `record.assistant_turn_ended` → status `idle` (fails today: `needs-you`);
   `record.question_asked` → `needs-you-asked`; `record.reasoning` →
   `reasoning`; `record.generating` → `generating`; wake-from-idle on
   turn-open.
2. `packages/activity/src/adapters/transcriptRecords.test.ts`: a Claude
   assistant message with a `thinking` block emits a `reasoning` record (fails
   today: nothing); a Codex `reasoning` item emits a `reasoning` record (fails
   today: dropped); an unknown stop_reason (e.g. `"banana"`) emits
   `transcript-error` with `unmapped-stop-reason:banana` (fails today: silent);
   `stop_reason: "refusal"` emits `transcript-error` with `refused-turn`
   (anomaly, not idle); `stop_reason: "max_tokens"` → turn-end → status `idle`.
3. `packages/activity/src/projections/workspaceActivity.test.ts`: mapped wire
   status for every machine state (exhaustiveness locked by the `never`
   switch); `needs_you` payload `{kind:"asked"}` only on `needs-you-asked`.
4. Strip-level observable: `RunVitalsStrip` renders "Idle" (not "Needs you")
   for an idle run, and "Needs you" for `needs-you-asked` (test beside
   `RunVitalsStrip.tsx`; fails today).

**Gates, verbatim (repo recipes, run at repo root):**

```
just check
just test
```

`just test` already runs the full serial suite including
`pnpm --filter @tm/contract test`, `@tm/activity`, the shell/canvas vitest
pools, and the api pytest suite — required in full because the enum change is
structural. Judge gate success by output content (pass counts), not a piped
exit code.

## Decisions — RESOLVED (Stuart, 2026-07-10)

1. **stop_reason mapping**: `end_turn | max_tokens` → idle; `refusal` →
   `transcript-error` (`refused-turn`, visible anomaly path). Baked into §3/§6.
2. **`needs-you-gated`**: reserved now as an unreachable enum value; the
   zero-count `status_counts` bucket is accepted. Baked into §1.
