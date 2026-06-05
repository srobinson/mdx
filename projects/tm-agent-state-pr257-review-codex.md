# PR #257 review

Reviewed `agent-state-slice1` at `536140e44852d8b859b55da2cbf817f1e610358e` against `tm-agent-state-spec-slice1.md`. The PR remains open and non draft. The repository worktree was pristine at the reviewed head before verdict.

## Major

### 1. Same row usage erases the new fail loud Claude stop reason anomaly

Confidence: 98/100.

Evidence:

- `packages/activity/src/adapters/transcriptRecords.ts`, `claudeRow` calls `addClaudeStopReasonRecord` before appending the row's `usage` record.
- `packages/activity/src/adapters/transcriptRecords.ts`, `addClaudeStopReasonRecord` emits `transcript-error` for `refusal` and every unknown string value.
- `packages/activity/src/adapters/transcriptRecords.ts`, `recordBuilder` assigns increasing `subSeq` values, so ingestion preserves the resulting `transcript-error` then `usage` order.
- `packages/activity/src/domain/runActivityMachine.ts`, `applyTranscriptError` enters `stalled`, while `applyUsage` clears the stalled fields and restores `statusAfterUsageRecord`. The `stalled` state's `usage.recorded` transitions target the recorded prior status.
- `packages/activity/fixtures/claude/claude-code-transcript.json`, fixture `turn-end-with-usage`, and `packages/activity/src/service/sameRowDedupe.test.ts`, test `counts one request's usage once across its duplicated content-block rows`, document the production shaped Claude behavior: assistant rows normally carry `message.usage`.
- The new `sameRowDedupe.test.ts` cases `surfaces a refusal as a visible anomaly, not idle` and `surfaces an unknown stop_reason as a visible anomaly instead of silence` omit usage, so they do not exercise the real same row sequence.

Observable result: a Claude assistant row with `stop_reason: "refusal"` or an unknown stop reason plus normal usage enters `stalled` for one sub event, then immediately restores the preceding active state and clears `transcriptError`. The required fail loud anomaly is absent from the materialized projection and browser strip.

Required correction: preserve usage accounting while making the stop reason anomaly the final observable state for that row. Add regression coverage with `message.usage` present for both refusal and unknown stop reasons.

## Confirmed clean

- Contract vocabulary, tier derivation, structured `needs_you`, and testing subpath separation conform to the spec.
- The machine split, idle wake transitions, exhaustive machine to wire mapping, router payload, and strip tier derivation conform.
- Browser code does not import `@tm/activity`; the contract package retains zero runtime dependencies.
- Frozen API capture plane files and `docs/ARCHITECTURE.md` are untouched.
- New and modified files remain within the repository's LOC guardrails. The largest modified production file is `runActivityMachine.ts` at 698 lines.

No builds, typechecks, or tests were run as part of this review.
