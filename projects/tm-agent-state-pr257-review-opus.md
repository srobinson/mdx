# PR #257 review — agent-state Slice 1 (opus)

Branch `agent-state-slice1`, head `536140e4`. Reviewed against
`~/.mdx/projects/tm-agent-state-spec-slice1.md`. Tree verified pristine at
`536140e4` before and after review (no writes; probe ran from an out-of-repo
scratchpad).

Verdict: **1 major, 2 minor.** The contract/domain/mapping/browser conformance is
otherwise faithful to the spec, the import boundary holds (`RunVitalsStrip`
pulls `activityStatusTier` from `@tm/core`, not `@tm/activity`), fixtures stay on
the testing subpath, and the exhaustive `wireStatusFromMachineState` correctly
kills the cast. The major defeats the slice's headline fail-loud goal in
production.

---

## MAJOR 1 — A Claude `refusal` / unmapped stop_reason never reaches `stalled`: the same-row `usage` record silently erases the anomaly

**Where:** `transcriptRecords.ts` `claudeRow` + `addClaudeStopReasonRecord`
(emits the `transcript-error` record), and `runActivityMachine.ts` — the
`stalled` state's `usage.recorded` restore chain, `applyUsage`, and
`statusAfterUsageRecord` (`runActivityContext.ts`).

**Mechanism.** For a real Claude Code assistant row, `claudeRow` emits records in
block order and Claude Code repeats `message.usage` on every assistant row (the
`sameRowDedupe.test.ts` "counts one request's usage once" case documents this).
So a refusal row produces three records on one store `seq`:

```
[ generating (text), transcript-error (refused-turn), usage ]
```

The machine applies them in `subSeq` order:
1. `generating` → state `generating`, `lastActiveStatus = "generating"`.
2. `transcript-error` → `applyTranscriptError` → state `stalled`,
   `stalledReason = "transcript-error"`, `stalledFrom = "generating"`.
3. `usage` in the `stalled` state → `statusAfterUsageRecord` returns
   `stalledFrom ?? "reasoning"` = `"generating"`, so the `usageRestoresGenerating`
   guard fires, and `applyUsage` calls `clearStalledFields()` and sets status
   back to `generating`.

**Final machine state: `generating`, `transcriptError: null`.** The refusal is
completely gone from the wire. Same for an unmapped stop_reason
(`unmapped-stop-reason:<value>`), which also rides a row carrying `usage`.

This directly violates the spec's core §3/§6 requirement: *"refusal →
transcript-error record with reason refused-turn (visible stalled/anomaly path,
NOT idle)"* and Decision 1 (*"refusal → visible anomaly path"*). The PR adds the
intent (a `transcript-error` record is produced) but the downstream machine
reverts it, so the fail-loud behavior is non-functional end to end.

**Empirically confirmed** (out-of-repo probe, real row shape
`{content:[{type:"text",...}], stop_reason:"refusal", usage:{...}}`):

```
REFUSAL records: [ 'generating', 'transcript-error', 'usage' ]
REFUSAL final state: generating | transcriptError: null   (expected: stalled)
```

**Why the suite missed it.** `sameRowDedupe.test.ts` "surfaces a refusal as a
visible anomaly" and "surfaces an unknown stop_reason" both use
`content: []` and omit `usage`, so no trailing `usage` record is emitted and the
run stays `stalled`. The fixture is not representative of a Claude Code row (no
usage, no text), so the observable-end-state assertion the spec §6 explicitly
demanded is being made against a shape that cannot occur in practice. Note the
`max_tokens` case is safe (`usage` restores to `idle`, matching intent) — only
the transcript-error stall is broken.

**Root cause / altitude.** `applyUsage` unconditionally clears the stall and
restores an active status regardless of *why* the run stalled. That is correct
for a `silence-timeout` stall (new activity legitimately un-stalls it) but wrong
for a `transcript-error` stall, which is a hard anomaly that a routine same-row
usage fact must not clear. The deep fix keys the restore on
`stalledReason === "silence-timeout"`: a `transcript-error` stall stays stalled
under `usage.recorded` and only leaves via a genuine new act (turn-open,
tool_use, etc., which already target out of `stalled`). Fix the mechanism, not
the fixture. The regression test must then assert `stalled` on the real row
shape (text + usage present).

---

## MINOR 2 — DRY: the status→`needs_you` derivation is hand-rolled in two packages

**Where:** `wireStatus.ts` `needsYouFromWireStatus` and
`fixtures.ts` `defaultNeedsYou` are byte-identical:
`status === "needs-you-asked" ? { kind: "asked" } : null`.
`workspaceActivity.test.ts` re-derives the same expression a third time as its
own expected value.

The `@tm/contract` fixtures package cannot import `@tm/activity`, so the copy in
`fixtures.ts` cannot reuse `needsYouFromWireStatus` as written. The single home is
the contract itself: the derivation is a pure, dep-free function of the status
enum, exactly the family the `packages/AGENTS.md` contract clause already admits
(`activityStatusTier`, `emptyStatusCounts`). Hoist a `needsYouForStatus(status)`
into `contract/src/activity/wire.ts`; `needsYouFromWireStatus`, `defaultNeedsYou`,
and the projection all delegate to it, and the test asserts against the authority
instead of a re-implementation. Per the repo DRY rule ("zero tolerance … refactor
the existing one so both callers share it"), the current two copies are a defect.

---

## MINOR 3 — `refusal` / `unmapped` acceptance tests assert against an unrepresentative fixture

**Where:** `sameRowDedupe.test.ts` "surfaces a refusal as a visible anomaly" and
"surfaces an unknown stop_reason as a visible anomaly".

Called out separately from Major 1 because it stands even after the machine fix:
these are the spec §6 red-first acceptance tests, and they use `content: []` with
no `usage`, a row shape Claude Code never writes. They should exercise the real
shape (a text block + `usage`) and assert the observable end-state is `stalled`
with `transcriptError` set. As written they lock in the wrong behavior (see
Major 1) and would keep passing if the machine regressed further.

---

## Checked and clean

- Contract: flat `activityStatuses` matches the spec verbatim (incl. reserved
  unreachable `needs-you-gated`); `activityStatusTier` exhaustive, no default,
  `stalled` its own tier; `ActivityNeedsYou` payload + `needs_you` on
  `ActivityWireRun`; production barrel exports types + `activityStatusTier` only;
  fixtures on the testing subpath.
- Mapping: `snapshot.value as ActivityStatus` cast gone; exhaustive
  `wireStatusFromMachineState` with `never` default; `needs_you` derived
  `{kind:"asked"}` only on `needs-you-asked`; `sameRunActivityProjection`
  compares `needsYou?.kind`.
- Domain split: `applyTurnNeedsUser` correctly split into `applyTurnIdle`
  (assistant_turn_ended → idle) and `applyQuestionAsked` (question_asked →
  needs-you-asked); `reasoning`/`generating` events wired into every non-final
  state matching the `record.tool_use` pattern; `idle` has the wake-up set
  (turn_open, reasoning, generating, tool_use, question_asked, usage, exited) and
  correctly has no stall timer; `idle` deliberately omits `tool_result`, which is
  safe (a turn only ends after its tools resolve, so no late tool_result reaches
  idle).
- Parsing: Claude `thinking`→`reasoning`, `text`→`generating`; Codex `reasoning`
  no longer dropped; Codex assistant `message`→`generating` with `task_complete`
  owning the boundary; usage/scaffold DRY dedupe (`tokens`, `transcriptRowParser`,
  `RowParser`) landed without leaving parallel copies.
- Browser: `STATUS_LABELS` covers all nine statuses; `needsYou` special-case
  replaced by `activityStatusTier(status) === "needs_you"`; import boundary intact.
