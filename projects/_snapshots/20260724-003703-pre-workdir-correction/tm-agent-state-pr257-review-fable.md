# PR #257 review — fable (spec author / conformance anchor)

Target: branch `agent-state-slice1`, head `536140e4`, reviewed against
`tm-agent-state-spec-slice1.md` and the scout reuse map. Process: 3 adversarial
finder passes (domain line-scan + removed-behavior, cross-file/boundary trace,
adapter DRY + test rigor) + my own conformance pass; candidates verified
against the live PR tree (`git show 536140e4:`). Working tree confirmed
pristine before and during review; no writes to the repo.

**Verdict: 0 major, 3 minor, 3 notes.** Spec conformance is complete on every
section; the enum replace is unusually clean. The minors are hardening, not
blockers, but per house rules they should land before merge.

## Minors (most severe first)

### M1 — `claudeRow` groups assistant blocks by type instead of iterating in block order
`packages/activity/src/adapters/transcriptRecords.ts` — `claudeRow`.
Spec §3 requires records emitted "in block order … last wins" and named
grouping as the failure mode. The implementation emits a fixed
reasoning-if-any-thinking → joined-text `generating` → tool_use-loop sequence
regardless of actual block positions. A multi-block assistant row shaped
`[text, tool_use, text]` would end on `tool-use` → status `running-tools`
instead of `generating`. Unreachable today only because Claude Code journals
one content block per row (stated in the file's own comment), i.e. the
correctness rests on a journal-shape invariant, not the parser.
The paired test gap makes this worse: the only block-order test
(`transcriptRecords.test.ts`, the "emits records in block order" case) uses a
pre-sorted `[thinking, text, tool_use]` fixture for which grouping and true
order produce identical output — it asserts the property's name, not the
property. **Fix:** iterate `message.content` in order (cheap; the builder
scaffold already supports it) and add an interleaved fixture asserting the
final record.

### M2 — `needs-you-gated` payload contract is internally inconsistent (latent, gate slice)
`packages/activity/src/domain/wireStatus.ts` — `needsYouFromWireStatus`;
`packages/contract/src/activity/fixtures.ts` — `defaultNeedsYou`;
`packages/contract/src/activity/wire.ts` — the `needs_you` field comment.
The comment promises "null unless status is a needs-you value", and
`activityStatusTier` puts `needs-you-gated` in the `needs_you` tier, but both
derivations return `null` for it. Unreachable in Slice 1 (no machine state
emits gated), so no live bug — but when the gate slice makes it reachable, a
`needs_you`-tier run would ship `needs_you: null` unless both functions change
in lockstep. **Fix now (cheap):** tighten the wire.ts comment to "asked only in
this slice" and drop a lockstep marker at `needsYouFromWireStatus` so the gate
slice cannot miss it.

### M3 — needs-you-asked → idle on turn-end is guarded only by adapter behavior
`packages/activity/src/domain/runActivityMachine.ts` — the
`record.assistant_turn_ended` transition from `needs-you-asked`.
Old `needs-you` treated turn-end as a self-transition; the new machine moves to
`idle`, clearing the payload. Safe today because neither adapter can emit
`question-asked` followed by `turn-end` for the same waiting turn (Claude
AskUserQuestion rows carry `stop_reason: "tool_use"` → no turn-end record;
Codex `request_user_input` pauses without `task_complete`). That invariant
lives in the adapters and nothing locks it. **Fix:** one adapter-level test per
harness asserting a question row does not also produce a `turn-end`, so a
future harness/stop_reason change fails a test instead of silently
un-flagging a blocked run.

## Notes (no action required)

- **N1 — Codex turn boundary now rests solely on `task_complete`.** On main the
  assistant `message` item also emitted `turn-end`; the PR maps it to
  `generating` per spec, so a truncated rollout missing `task_complete` now
  parks in `generating` → visible `stalled` after the timeout instead of idle.
  Spec-intended; the degradation path is loud, which is the design's stated
  preference.
- **N2 — `needs_you` wire field has no browser reader yet.** The strip derives
  from `activityStatusTier(status)`; the field is the declared Slice-2 seam per
  spec §1. The SSE parser (`parseActivityStreamFrame`) tolerates its absence
  (no break on stale payloads) and does not validate its shape — consistent
  with the parser's existing laxness.
- **N3 — `sameRunActivityProjection` compares `needsYou?.kind` redundantly**
  (`packages/activity/src/projections/workspaceActivity.ts`): the payload is a
  pure function of `status`, which is compared adjacently. Harmless, and
  defensible once the gate slice makes the payload vary independently.

## Conformance confirmed (spec section → evidence)

- **§1 contract:** `wire.ts` matches the spec's literal shape — 9-value flat
  `as const` union with `needs-you-gated` reserved, `activityStatusTier` with
  `stalled` as its own tier, `ActivityNeedsYou` union, `needs_you` on
  `ActivityWireRun`; barrel exports types + derivations only, fixtures stay on
  `/testing`; `packagePurity` untouched, zero runtime deps.
- **§2 machine:** rename complete (no `thinking`/bare `needs-you` survivors);
  `applyTurnNeedsUser` split as specified; `record.reasoning`/`record.generating`
  handled in all 7 non-final states; idle wake-ups present; stall timeout on
  active states only (absent on needs-you-asked/idle, matching old needs-you);
  stall-restore guards cover the full 6-status set `statusAfterUsageRecord` can
  return; `wireStatusFromMachineState` exhaustive with `never` default; the
  question-answered `tool_result` path survives on `needs-you-asked`. The new
  `runActivityMachineGraph.test.ts` locks the full transition table (moved from
  the old test, strengthened not weakened).
- **§3 adapters:** stop_reason table literal-exact including Stuart's refusal
  split (`refused-turn`) and correct null/undefined handling (no
  `unmapped-stop-reason:null` spam); Claude thinking → `reasoning`; Codex
  `reasoning` no longer dropped; the required DRY dedupe genuinely landed
  (`transcriptRowParser` scaffold owns coercion/builder/drop-reporting once;
  shared `tokens()` normalizer under both usage readers — semantically the
  spec's fold); file at 370 LOC, no split needed.
- **§4 browser/router:** `runToWire` threads `needs_you`; `STATUS_LABELS`
  complete for 9 statuses with the spec's labels; `needsYou` derives from the
  contract tier authority via `@tm/core` re-export.
- **§6 tests:** red-first behaviors all present and observable (turn-end →
  "idle" machine + strip level; refusal → anomaly; max_tokens → idle; unknown
  stop_reason fail-loud; Codex reasoning no longer silent). No weakened or
  deleted assertions found in any test diff; e2e strip spec assertions stay
  exact.
- **Boundaries/frozen:** nothing under `api/` or `docs/ARCHITECTURE.md` in the
  diff; no `www/` import of `@tm/activity`; no surviving old status literals
  (remaining `"thinking"` hits are the transcript content-block type, a
  distinct concept).
