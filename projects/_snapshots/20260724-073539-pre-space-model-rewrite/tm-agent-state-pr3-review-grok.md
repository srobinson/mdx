# Agent-state PR-3 code review (Grok) — PR #260

| Field | Value |
|-------|--------|
| PR | #260 |
| Branch | `agent-state-pr3-wire-activity` |
| Head | `342bc57d403fa73ff70ea93ba40aaabe31997c4b` |
| Spec | `~/.mdx/projects/tm-agent-state-spec-pr3.md` (rev 2, converged) |
| Lenses | code-review + code-hygiene (emphasis: hygiene + boundaries) |
| Tree | pristine at review |
| CI | 9/9 SUCCESS on head |
| Verdict | **clean / sign-off** |

## Scope

Product-plane consumer of the already-merged wire store (PR-2 on main). Five commits:

1. contracts + `parseTmEventsPayload`
2. `readWireSnapshotForRun` + shared `askToolNames`
3. domain: `stream:"wire"`, admission, `foldWireAsserted`, `wire.retracted`
4. ingestion reconcile step + telemetry
5. pg acceptance T1–T12 + shared harness

Diff is almost entirely `packages/activity/**` plus the existing Python/TS pg-contracts parity test extended for wire table/payload names.

## VERIFY matrix

| # | Check | Result |
|---|--------|--------|
| 1 | No duplication — wire reuses existing folds / `record.*` | **Pass.** Candidates mint existing `record.question_asked` / `tool_use` / `transcript_error` / `assistant_turn_ended` with `stream:"wire"` (`wireCandidate.wireCandidateEvent`). Status folds gain a one-line wire head routing to `foldWireAsserted` (does not rewrite `lastActiveStatus` / `pendingToolCallIds`). `askToolNames` owned once in `harnessRegistry`; `transcriptRecords` consumes it (no third literal set). |
| 2 | Product-plane only; no cross-import into frozen/api impl | **Pass.** Implementation lives under `packages/activity`. Domain stays pure (`wireCandidate` has no ports import). Service owns snapshot→candidate mapping and store IO via `ActivityStore.readWireSnapshotForRun`. No frozen-plane, no Python production write path, no gateway/www. |
| 3 | No dead code / leftover scaffolding across 5 commits | **Pass.** New surfaces are wired end-to-end: contracts → parse → reader → domain → ingestion → telemetry → tests. Exports on `domain/index.ts` match consumers. No parallel abandoned stream/cursor design. |
| 4 | Sizing thresholds | **Pass.** Largest production files still under 700: `runActivityContext.ts` 675, `runActivityMachine.ts` 636, `postgresRecords.ts` 509. New modules small (`wireCandidate` 70, etc.). |
| 5 | `tm_events` parse reuses `parseTmEventsPayload` | **Pass.** Two new cases in the same function (`WIRE_EXCHANGE_PAYLOAD_TYPE` / `DELETED`), shared `wireExchangePayload` helper; `TmEventsActivityListener` still only calls `parseTmEventsPayload`. Both flavors reduce to reconcile via existing `markReconcileNeeded`/`runId` routing. |
| 6 | Zero migration / zero production API | **Pass.** No `api/migrations/**`. No production `api/src` write path. Sole `api/` touch is `session/test_activity_pg_contracts.py` extending the existing TS↔Python contract parity suite (test-only). |

## Spec fidelity (correctness, secondary to hygiene brief)

- **§1 reconcile order:** record batch → `reconcileWireSnapshot` → `run-exited` (`activityIngestion.reconcile`).
- **§2 mapping:** priority ask → other tool_use → response_error/refusal → idle; `response_id IS NOT NULL` + subagent exclusion in SQL.
- **§3.2 admission:** `wireCandidateAdmitted` on `resolvedToolCallIds` (grown by `foldToolResult`/`foldToolError`) and cold-start (`recordSessionId === null`) for idle/anomaly.
- **§3.3 baseline + retraction:** `foldWireAsserted` / `statusAfterWireRetraction` recompute; `wire.retracted` guarded from the four wire-assertable states; graph tests updated.
- **Cursor law:** wire never advances `seqCursors` or record watermark; `isNewEvent` always true for wire; usage restore blocked while wire-owned.

## Local verification

```text
pnpm --filter @tm/activity exec vitest run \
  src/domain/wireActivity.test.ts \
  src/adapters/tmEvents.test.ts \
  src/service/wireIngestion.test.ts \
  src/domain/runActivityMachineGraph.test.ts
# 4 files, 38 tests passed
```

CI product-plane + full matrix green on head.

## Non-blocking notes

1. **`runActivityContext.ts` at 675/700.** Next material domain addition should extract before growing further (e.g. wire folds already cluster well).
2. **Spec wording “packages/activity only”** vs the tiny Python contract-parity test. Correct for the shared-contract pattern already used for lifecycle; not a production API surface.

## Issues

None at confidence ≥80.

## Verdict

**clean / sign-off.** PR-3 implements the converged wire-activity spec with reuse of existing folds and parse path, product-plane boundaries held, zero migrations, sizing under guardrails, and no dead parallel implementation.
