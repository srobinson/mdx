# Scout — agent-state derivation seams (Mode-1)

Scout pass for the tm-agent-state build (canvas runs only). Design reference:
`tm-agent-state-proposal.md` (locked). Scope: map what exists for reuse; no
design, no build. All citations are file + symbol. Repo: `transport-matters`
at `350e50c` (clean tree). Codex source: `~/.mdx/research/openai-codex`.

## Reuse Map

### Seam 1 — Crude status derivation to replace

The status is not ad-hoc if/else; it is an XState machine over a flat 6-value
vocabulary. "Crude" means the vocabulary collapses the distinctions the 4-tier
model needs.

- **Vocabulary (wire enum):** `packages/contract/src/activity/wire.ts` —
  `activityStatuses` = `["starting","thinking","running-tools","needs-you","stalled","exited"]`,
  `ActivityStatus`, `emptyStatusCounts()`. There is **no `idle` value at all**;
  idle is unrepresentable today.
- **Decision core:** `packages/activity/src/domain/runActivityMachine.ts` —
  `runActivityMachine`. Context helpers:
  `packages/activity/src/domain/runActivityContext.ts` —
  `statusAfterUsageRecord()`, `statusBeforeStall()`, `DEFAULT_STALL_TIMEOUT_MS`.
- **The two product bugs, located exactly:**
  1. *Idle reads as needs_you:* action `applyTurnNeedsUser` maps **both**
     `record.assistant_turn_ended` and `record.question_asked` to
     `status: "needs-you"`. A completed turn and a genuine AskUserQuestion land
     in the same bucket.
  2. *Gated run reads as Thinking/Tools:* no permission/gate signal is parsed
     anywhere (`permission|gated|approval|can_use_tool` grep over
     `packages/activity` + `packages/contract` = zero hits). A gated run either
     retains the prior `thinking` (gate before the tool_use row lands) or shows
     `running-tools` (tool_use journaled before the gate renders). Gating is
     invisible, so the run inherits whatever preceded it.
- **Full chain (raw → strip):**
  `packages/activity/src/adapters/postgresRecords.ts` (`EVENT_KIND_TURN_FILTER`,
  `PgActivityEventRecord`) →
  `packages/activity/src/adapters/transcriptRecords.ts`
  (`activityRecordsFromPgEvent` → `claudeActivityRecords` / `codexActivityRecords`) →
  `packages/activity/src/service/runActivityEvents.ts`
  (`activityRecordToEvent`, `runLifecycleFactToEvent`; kind table
  `activityRecordKindEventTypes` in `packages/activity/src/ports.ts`) →
  `runActivityMachine` →
  `packages/activity/src/projections/workspaceActivity.ts`
  (`runActivityProjection`, `WorkspaceActivityProjections`; note
  `status: snapshot.value as ActivityStatus`, an unchecked cast) →
  `packages/activity/src/server/activityRouter.ts` (`runToWire`, `rollup`,
  `activityResponse` inside `createActivityRouter`; REST + SSE stream) →
  `www/packages/core/src/activityStreamEvents.ts` →
  `www/packages/canvas/src/model/runVitalsStore.ts` (`useRunVitalsStore`,
  `applyActivityStreamFrame`) →
  `www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx`
  (`RunVitalsStrip`, `STATUS_LABELS`, `needsYou` special-case).

### Seam 2 — Wire+transcript signals already parsed (Slice-1 fuel)

Two parse planes exist and share no code. Plane A (TS,
`packages/activity/src/adapters/transcriptRecords.ts`) is the **only** status
source. Plane B (Python transport IR: `api/src/transport_matters/ir.py`,
`api/src/transport_matters/adapters/anthropic.py`,
`api/src/transport_matters/codex/response_parser.py`) is the frozen exchange
recorder; richer, but feeds status nothing.

| Signal | Claude | Codex | Feeds status today? |
|---|---|---|---|
| thinking/reasoning | Plane A: **not parsed** (only `text`+`tool_use` blocks read). Plane B: `_parse_thinking_block()` → `ThinkingBlock` | Plane A: `reasoning` response_item **deliberately dropped**. Plane B: `_reasoning_block()` | **No** — `active{reasoning}` has no source in the status plane yet |
| text | Plane A: `claudeAssistantText()`/`joinTextBlocks()` → rides as `messageText` only | Plane A: `codexMessageText()` | Partial — `last_message` only; `active{generating}` has no status source |
| tool_use | Plane A: `claudeActivityRecords()` → `tool-use` record (AskUserQuestion excepted) | Plane A: `function_call` → `tool-use` (`request_user_input` excepted) | **Yes** → `running-tools` (`applyToolUse`) |
| turn boundaries | Plane A: user msg → `turn-open`; `stop_reason === "end_turn"` → `turn-end` | Plane A: `task_started` → `turn-open`, `task_complete` → `turn-end`, `turn_aborted` → `transcript-error` | **Yes** → `thinking` / `needs-you` |
| stop_reason | Plane A: only `"end_turn"` consumed; `max_tokens`/`tool_use`/`refusal`/`pause_turn` silently ignored. Plane B: full capture | Plane B: `_response_stop_reason()` | Partial |
| token usage | Plane A: `claudeUsage()` (per `requestId`) | Plane A: `token_count` → `codexUsage()` | **Yes** → `applyUsage` |
| AskUserQuestion | Plane A: `block.name === "AskUserQuestion"` → `question-asked` | Plane A: `name === "request_user_input"` → `question-asked` | **Yes but conflated** into `needs-you` with turn-end; this is the ready-made seed for `needs_you{asked}` |
| permission gate | none anywhere | none anywhere | **No** — `needs_you{gated}` has zero source today (Slice 3 for Claude; codex events for Codex) |

Net: the Slice-1 active-tier split + idle fix needs (a) new reasoning/text
parsing in Plane A (both harnesses already deliver the raw material to it), and
(b) splitting `applyTurnNeedsUser`. No new capture required, as the brief
assumes.

### Seam 3 — Canonical-model home (recommendation, not a decision)

`packages/AGENTS.md` contract clause: contract packages publish wire DTOs
crossing the product-plane↔browser seam with **zero runtime deps** (enforced by
`packages/contract/src/packagePurity.test.ts`), and explicitly allow "optional
status enums as `as const` values and pure dep-free derivations of those enums
(e.g. `emptyStatusCounts()`)". Browser packages never import context packages.

Recommendation: the canonical 4-tier **wire vocabulary** (tier values,
sub-states, and the structured `needs_you` payload DTO) belongs on
`@tm/contract/activity` — extend `wire.ts`, where `ActivityStatus` +
`emptyStatusCounts()` already live and where the strip already consumes from.
The **derivation** (per-harness adapters, machine, harness-schema registry)
stays in `@tm/activity` (`src/domain` + `src/adapters`), matching the
proposal's anti-corruption-layer shape. A new subpath
(`@tm/contract/agent-state`) is only warranted if agent-state becomes its own
bounded context; today it is a projection of the Activity context, so a new
subpath would split one context across two contract surfaces. Keep the
XState state names decoupled from the wire enum via an explicit mapping
function (see Quality Map on the `snapshot.value` cast).

### Seam 4 — Codex protocol type generation (`~/.mdx/research/openai-codex`)

- **Approval events:** `EventMsg::ExecApprovalRequest` /
  `EventMsg::ApplyPatchApprovalRequest` in
  `codex-rs/protocol/src/protocol.rs`; payload structs
  `ExecApprovalRequestEvent` (call_id, approval_id, turn_id, command, cwd,
  reason, available_decisions, parsed_cmd, …) and
  `ApplyPatchApprovalRequestEvent` (call_id, turn_id, changes, reason,
  grant_root) in `codex-rs/protocol/src/approvals.rs`. Responses:
  `Op::ExecApproval` / `Op::PatchApproval` with `ReviewDecision`
  (approved / approved_for_session / denied / timed_out / abort / amendment
  variants) in `codex-rs/protocol/src/protocol.rs`.
- **App-server status:** `waitingOnApproval` / `waitingOnUserInput` are **not**
  top-level statuses; they are `ThreadActiveFlag` values nested under
  `ThreadStatus::Active { activeFlags }`. `ThreadStatus` full set:
  `notLoaded | idle | systemError | active`. Both in
  `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`; runtime derivation
  `resolve_thread_status` in `codex-rs/app-server/src/thread_status.rs`;
  delivered via `ThreadStatusChangedNotification`. Codex itself models
  idle-vs-waiting exactly as our canonical model wants.
- **Schema gen machinery:** types derive both `TS` (ts-rs) and `JsonSchema`
  (schemars). Generator: `codex-rs/app-server-protocol/src/export.rs`
  (`generate_types`); binaries `export.rs` (arbitrary `--out`) and
  `write_schema_fixtures.rs` (`just write-app-server-schema` →
  `cargo run -p codex-app-server-protocol --bin write_schema_fixtures`).
  **Output is checked in**: `codex-rs/app-server-protocol/schema/typescript/`
  (per-type ts-rs files incl. `v2/ThreadStatus.ts`, `v2/ThreadActiveFlag.ts`)
  and `schema/json/` (aggregate `codex_app_server_protocol.v2.schemas.json`).
- **Proposed acquisition path (map-only):** resolve installed codex version →
  `rust-v<version>` tag → **pull the vendored `schema/typescript` (or the v2
  JSON bundle) directly from the tagged tree — no Rust build needed** — and
  store the resolved tag as the pin. Caveats: workspace `Cargo.toml` says
  `0.0.0` (version exists only in the tag); the clone is on `main` at
  `rust-v0.143.0-alpha.10-310-g…` and **`rust-v0.144.0` is not an ancestor of
  that HEAD** (divergent release line), so version→tag resolution needs a
  nearest-tag fallback; `sdk/typescript/src/events.ts` is a hand-written
  higher-level `codex exec` surface — not a protocol source, do not vendor it.

### Seam 5 — ScrollbackRing / PTY access path (Slice 3, map only)

- **Components (all TS, `@tm/runtime`):**
  `packages/runtime/src/domain/terminal/ScrollbackRing.ts` — `ScrollbackRing`
  (`append()`, `snapshot()`, `DEFAULT_SCROLLBACK_BYTES` = 2 MiB, chunks are
  `PtyChunk { seq, data: Uint8Array, emittedAt: Date }`);
  `packages/runtime/src/service/TerminalFanout.ts` — `TerminalFanout` (owns the
  ring as public field `scrollback`, plus viewer queues);
  `packages/runtime/src/service/RunManager.ts` — `RunManager` (private `runs`
  map; wires `session.onData` → `fanout.append`). The Python
  `api/src/transport_matters/api/v1/terminal_bridge.py` no longer holds a
  bridge (moved to gateway, slice 4f); only origin-trust/WS-close helpers remain.
- **Ring content:** raw pre-VT PTY bytes (node-pty `encoding: null` via
  `packages/runtime/src/adapters/NodePtyAdapter.ts`); ANSI intact. Rendering
  happens only browser-side (`@xterm/xterm` in
  `www/packages/canvas/src/viewers/terminal/terminalSession.ts`). **No headless
  renderer / VT parser / ansi-strip dep exists anywhere** (checked all
  package.jsons + pyproject); Slice 3 introduces the repo's first.
- **In-process tail read:** `TerminalFanout.scrollback` is public and
  `ScrollbackRing.snapshot()` returns the full ring copy, but `RunManager`
  exposes **no public ring accessor** — the only public route is `attach()`
  (mints a real viewer attachment). Slice 3 needs one small new `RunManager`
  accessor (peek/snapshot by runId) and optionally a `tail(nBytes)` on
  `ScrollbackRing`. Both are additive.
- **Quiescence primitive: none found** in the PTY path (searches:
  `quiesc|idle|inactiv|last.?output|lastData|debounce|lastActivity|settleTimer`).
  The only usable raw material is per-chunk `PtyChunk.emittedAt`. Activity's
  stall timeout (`DEFAULT_STALL_TIMEOUT_MS`, `silence-timeout` in
  `runActivityContext.ts`) is transcript-driven — a different signal source,
  not reusable as-is for TUI quiescence.
- **Topology confirmed:** the ring lives in the `@tm/gateway` node process
  (`packages/gateway/src/main.ts` `createDefaultRuntimeRouterDeps` builds the
  singleton `RunManager`), and the Activity context mounts on the **same**
  Fastify instance (`packages/gateway/src/app.ts` `buildGateway`) when
  `TRANSPORT_MATTERS_DATABASE_URL` is set. Python api is only the interim proxy
  (`api/src/transport_matters/api/v1/run_proxy.py` — `RunRouteProxy`). The
  proposal's "in-process with Activity" premise holds today.

## Quality Map

1. **`snapshot.value as ActivityStatus` unchecked cast** —
   `packages/activity/src/projections/workspaceActivity.ts`
   (`runActivityProjection`). XState state names ARE the wire enum; any new
   machine state leaks to the wire uncompiled-checked. Groom: introduce an
   explicit machine-state → wire-status mapping function as part of Slice 1
   (it is where the 4-tier mapping naturally lands anyway).
2. **`stop_reason` under-consumed** — `transcriptRecords.ts` branches only on
   `"end_turn"`; `max_tokens`, `refusal`, `pause_turn`, `tool_use` silently
   leave the run in its prior state. This is exactly the silent-misclassify
   failure SCHEMA-LOCK forbids. Groom: widen in Slice 1 with fail-loud handling
   of unmapped values.
3. **Two disconnected parse planes** — thinking/text/tool_use/stop_reason/usage
   are each parsed twice (TS `transcriptRecords.ts` vs frozen Python
   `ir.py`/`adapters/anthropic.py`/`codex/response_parser.py`) with no shared
   contract. Plane B is richer (ThinkingBlock, full stop_reason) but frozen and
   invisible to status. Not fixable now (api plane frozen); name the boundary
   in the build docs so Slice 1 adds parsing to Plane A rather than reaching
   into Plane B.
4. **claude/codex scaffold duplication in `transcriptRecords.ts`** —
   `claudeUsage()`/`codexUsage()` wrap near-identical normalizers; both
   `*ActivityRecords()` repeat the `safeRecord`/drop-sink/builder scaffold.
   Slice 1 touches this file for reasoning/text parsing: fold the shared
   scaffold then, before a third harness lands.
5. **LOC guardrails: clean.** Nothing in scope over 700 (largest:
   `runActivityMachine.test.ts` 627, `RunManager.ts` 538,
   `runActivityMachine.ts` 446). Slice 1 grows the machine + its test; watch
   the 700 line on the test file.
6. Minor, note-only: `terminal_bridge.py` name no longer matches its contents
   (frozen plane, rename when unfrozen); bundled artifact
   `api/src/transport_matters/gateway/main.js` (~55k lines) pollutes source
   greps — exclude in tooling; `RUN_START_FAILED_CLOSE_CODE` +
   Python-parity comments in `RunManager.ts` are deliberate migration leftovers.

## Plan

Proposed Slice-1 steps (wire+transcript-only active-tier split + idle fix; no
new capture), each bound to the reuse map:

1. **Contract:** extend `packages/contract/src/activity/wire.ts` with the
   canonical vocabulary (active{reasoning|generating|running_tool},
   needs_you{gated|asked}, idle, terminal) replacing `activityStatuses`
   in place — no users/back-compat, and `emptyStatusCounts()` +
   `@tm/contract/activity/testing` fixtures regenerate from the enum. Same
   PR-family shape as slice-4 (#254/#255/#256: contract → core → canvas).
2. **Domain:** split `applyTurnNeedsUser` in `runActivityMachine.ts`:
   `record.assistant_turn_ended` → `idle`; `record.question_asked` →
   `needs_you{asked}`. Add the idle state. This alone kills the worst bug.
3. **Adapters (Plane A):** in `transcriptRecords.ts`, parse Claude `thinking`
   blocks and stop dropping Codex `reasoning` items → new record kind →
   `active{reasoning}`; map text/agent-message presence → `active{generating}`;
   widen `stop_reason` handling with fail-loud on unmapped values (Quality Map
   2, SCHEMA-LOCK principle).
4. **Projection/router:** replace the `snapshot.value` cast with an explicit
   mapping function (Quality Map 1); thread through `runToWire`/`rollup`.
5. **Browser:** update `STATUS_LABELS` + `needsYou` handling in
   `RunVitalsStrip.tsx` and counts in `runVitalsStore.ts`.
6. **Fixtures/gates:** golden fixtures via `@tm/contract/activity/testing` +
   machine tests; gate on the repo recipes (`just check` / package `test`
   scripts) verbatim, full frontend suite given the contract enum change is
   structural.

Decisions needed before build:
- **(a) Canonical-model home** — recommendation above: `@tm/contract/activity`
  for wire vocabulary, `@tm/activity` domain for derivation. Needs sign-off.
- **(b) Enum replacement strategy** — in-place replace (recommended; no
  back-compat surface) vs additive parallel field.
- **(c) Codex pin acquisition** — vendored `schema/typescript` pulled from the
  `rust-v<version>` tag (recommended; no Rust toolchain in the loop) vs running
  `write_schema_fixtures` from source; either way the version→tag resolver
  needs the nearest-tag fallback (0.144.0 is not an ancestor of current main).
- **(d) `stalled` semantics** — recommend leaving the stall timeout mechanism
  untouched in Slice 1 (transcript-silence signal is orthogonal to the tier
  split).
