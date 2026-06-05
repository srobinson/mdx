# PR #260 code review

Head: `342bc57d403fa73ff70ea93ba40aaabe31997c4b`

Verdict: issues found. The causal admission and nonpollution design is mostly present, but three paths violate the converged PR-3 contract.

## 1. HIGH, confidence 96: interrupted calls remain causally unresolved

Paths: `packages/activity/src/adapters/transcriptRecords.ts:codexRow`, `packages/activity/src/domain/runActivityContext.ts:foldTurnOpen`, `packages/activity/src/domain/runActivityContext.ts:foldToolResult`, `packages/activity/src/domain/runActivityContext.ts:foldToolError`, `packages/activity/src/domain/wireCandidate.ts:wireCandidateAdmitted`

`resolvedToolCallIds` grows only through tool result and tool error folds. Codex `turn_aborted` produces only `record.transcript_error`, and the checked in real fixture carries a `turn_id` but no `call_id`. `foldTurnOpen` then discards abandoned `pendingToolCallIds` without adding them to the persistent resolution set, even though its own contract says those results will never arrive.

The unchanged latest wire exchange therefore remains admissible. After an interrupt, the same reconcile can replace the transcript's stalled or reasoning state with stale `running-tools`; later empty reconciles keep reasserting it. A read only aggregate scan of 3,711 local Codex session files found one `turn_aborted` with an unresolved `exec_command`, confirming the missing output path occurs in real data.

The test named as covering interrupt journals sends an ordinary tool result. It does not exercise `turn_aborted` or a turn open that abandons pending IDs. This violates spec section 3.2 and E6.

## 2. HIGH, confidence 92: a corroborating transcript anomaly is erased by retraction

Paths: `packages/activity/src/domain/runActivityContext.ts:markApplied`, `packages/activity/src/domain/runActivityContext.ts:foldTranscriptError`, `packages/activity/src/domain/runActivityContext.ts:foldWireRetracted`, `packages/activity/src/service/activityIngestion.ts:reconcileWireSnapshot`

A cold start wire anomaly asserts `stalled` and sets `wireAssertedExchangeId`. When the transcript later records the same anomaly, `foldTranscriptError` also yields `stalled`. `markApplied` clears wire ownership only when the status value changes, so the marker survives even though the record stream has taken ownership.

That record makes the cold start predicate false. The wire step refuses the candidate, sees the stale ownership marker, and sends `wire.retracted`. Retraction clears `stalledReason` and `transcriptError`, then restores `lastActiveStatus`, commonly `starting`. A durable transcript hard anomaly is therefore laundered into an active state, violating transcript precedence and the hard stall invariant.

T6 covers the initial wire anomaly. No test covers transcript catch up to the same `stalled` status.

## 3. MEDIUM, confidence 95: retraction makes `sinceTs` application time dependent

Paths: `packages/activity/src/service/activityIngestion.ts:reconcileWireSnapshot`, `packages/activity/src/domain/runActivityContext.ts:foldWireRetracted`, `packages/activity/src/domain/runActivityContext.ts:markApplied`, `packages/activity/src/pgWireIntegration.test.ts:T10a`

The service mints `wire.retracted` with `new Date().toISOString()`. `foldWireRetracted` routes that event through `markApplied`, which stamps the wall clock value into `sinceTs` whenever the restored status differs. Fresh materialization after the same deletion has no retraction event and retains the transcript timestamp. Identical durable state therefore projects different user visible timing before and after restart.

The context documents `sinceTs` as data derived and replay safe. Spec T10 requires the exact prewire transcript state with transcript derived timing. T10a masks the defect by replacing the expected `sinceTs` with the restored value before equality comparison.

## Confirmed clean areas

- `foldWireAsserted` and every current wire caller preserve `lastActiveStatus` and `pendingToolCallIds`.
- Tool result and tool error folds persist resolved IDs in actor context. The delayed answer before wire write case is refused by the causal key.
- Retraction recomputes status from record owned pending IDs and `lastActiveStatus`.
- The PR changes no migration or frozen capture plane production file. The Python change is a contract test only.
- Changed production files remain below 700 lines. No added function exceeds approximately 150 lines. No separate duplication or ownership defect met the review threshold.

Review method: static diff and history review, five independent review lenses, confidence rescoring, checked in fixture inspection, and read only aggregate transcript shape checks. GitHub CI was 9 of 9 green. Per the code review workflow, no local build or test command was run and no GitHub review was posted.
