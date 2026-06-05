# PR #260 review — spec author (scout 1)

**PR:** `agent-state-pr3-wire-activity` (5 commits `1afc11d..342bc57`) vs `main`
(`157f781`). CI 9/9 green (gh confirmed). Tree pristine before and after
review. Anchor: `~/.mdx/projects/tm-agent-state-spec-pr3.md` (rev 3, mine).
Lenses: code-review (high effort, full diff read) + code-hygiene.

**Verdict: conditional signoff.** Spec fidelity is excellent — every invariant
I specified is implemented and tested, several with more rigor than the spec
demanded. One medium behavioral finding the spec was silent on (F1) needs a
disposition before merge; two clarifications (the red-first question, an api
touch) resolve in the PR's favor.

## Scope fidelity vs spec (all pass)

| Spec requirement | Evidence |
|---|---|
| 5 commits exactly as sliced (§5) | contracts+parse / reader+askToolNames / domain / ingestion / acceptance — commit subjects and contents match one-to-one |
| Payload parse cases (§1 step 4) | `tmEvents.ts:wireExchangePayload` shared by both types; malformed → `undefined`; `ports.ts:WireExchangePayload` joins the union |
| Reader = one-row snapshot (§1 step 6) | `postgresRecords.ts:readWireSnapshotForRun`; SQL has `response_id IS NOT NULL`, `track_role IS DISTINCT FROM 'subagent'`, `ORDER BY created_at DESC, exchange_id DESC LIMIT 1`; comment correctly states ordering picks the newest STORED row and is not the admission rule |
| Narrow DTO, not `ActivityRecord` (§5 c2) | `ports.ts:WireExchangeSnapshot` with the exact rationale comment |
| `askToolNames` extracted, no third copy (§2) | `harnessRegistry.ts:askToolNames`/`isAskToolName`; `transcriptRecords.ts` `claudeRow` AND `codexRow` consume it; `REFUSAL_STOP_REASON`/`REFUSED_TURN_REASON` consolidated too |
| State mapping first-match-wins (§2) | `runActivityEvents.ts:wireCandidateFromSnapshot` — ask → tools → anomaly (`response_error`, then refusal) → idle; at most one candidate |
| Causal admission (§3.2) | `domain/wireCandidate.ts:wireCandidateAdmitted` — asked: id unresolved; running-tools: NO id resolved; idle/anomaly: `recordSessionId === null` cold-start predicate. Pure domain, no clocks, no cursor |
| Resolution set durable-equivalent (§3.2) | `runActivityContext.ts:resolvedToolCallIds` fed by `foldToolResult` AND `foldToolError`, empty-id guarded (`withResolvedToolCallId`), rebuilt by replay |
| Baseline preservation (§3.3) | `foldWireAsserted` never writes `lastActiveStatus`/`pendingToolCallIds`; wire branches in `foldQuestionAsked`/`foldToolUse`/`foldTurnIdle`/`foldTranscriptError`; unit test asserts non-pollution directly |
| Retraction = recompute (§3.3) | `statusAfterWireRetraction` = pending ? running-tools : `lastActiveStatus`; `wire.retracted` guard factory covers all six active restore targets; graph test enumerates every state × target pair |
| Ownership semantics (§3.3) | `markApplied`: explicit patch wins, non-wire status change clears; kept across status-neutral replay (tested) |
| Reconcile order (§3.4) | `activityIngestion.ts:reconcile` — records → `reconcileWireSnapshot` → run-exited; terminal skip; watermark untouched by wire step (tested) |
| Wire never touches cursors (§1 step 7) | `eventStream` checks discriminator FIRST; `markApplied` skips `seqCursors` for wire; `isNewEvent` wire → true with the admission living in the service; unit test locks cursor-space isolation |
| T1–T12 user-observable, projection-level (§6) | `pgWireIntegration.test.ts`: 13 tests (T10 split a/b per spec), all asserting `runActivityProjection().status`/`needsYou`; T1 asserts pre-wire `reasoning` ("Thinking") then `needs-you-asked` |
| Zero migrations, zero frozen-plane runtime edits | Diff exhaustive: no `api/migrations`, no api runtime files; `@tm/contract` untouched |
| Gates | CI green on the verbatim gates; suites gate fail-closed on `TRANSPORT_MATTERS_TEST_DATABASE_URL` (set-but-unreachable pg fails, unset skips) |

Beyond spec (positive): `foldUsage` gained a wire-asserted accrue-only guard —
without it, a usage event would patch `context.status` to the baseline while
the machine STATE stayed wire-asserted, splitting the status mirror. Correct
and unit-tested. The shared `pgIntegrationHarness.ts` extraction (record +
wire suites) is clean consolidation: minimal DDL sourced entirely from
`pgContracts.ts` constants, shape cross-guarded by the api-side contract-lock
test; no record-plane tests were lost in the move (deleted lines are the
relocated harness only).

## Findings

### F1 (medium, behavior the spec was silent on) — a re-asserted unchanged exchange clears a silence-timeout stall on every reconcile

Chain (all shipped code): run's latest exchange handed off tools →
`running-tools` (wire- or transcript-derived) → 10-minute silence →
`applySilenceTimeout` → `stalled{silence-timeout}` (and the new action clears
`wireAssertedExchangeId`). Any subsequent reconcile (a UI read re-arms the
loop via `materialize`, or any NOTIFY for the run) runs
`reconcileWireSnapshot`: the same running-tools candidate is still admissible
(its ids never resolved — the harness is dead or the tool genuinely
long-running), so the wire step sends `record.tool_use`, and `stalled` has a
`record.tool_use → running-tools` transition with `isNewEvent` true for wire
events. The stall clears with NO new evidence, the stall timer restarts, and
the run flaps stalled↔running-tools on the read/reconcile cadence.

Blast radius: exactly the runs whose latest turn handed off non-ask tools —
`needs-you-asked` and `idle` have no stall timer, and idle/anomaly candidates
are refused once records exist. But that tool-handoff case is common, and the
silence-stall overlay (the operator's "something may be wrong" signal) is
effectively disabled for it.

Two defensible dispositions — Stuart's call, since the spec never addressed
the stall/re-assert interplay (my gap, not the builder's):

1. **Preserve the stall (recommended):** do NOT clear
   `wireAssertedExchangeId` in `applySilenceTimeout`; in
   `reconcileWireSnapshot`, refuse the candidate when
   `candidate.exchangeId === context.wireAssertedExchangeId &&
   context.stalledReason === "silence-timeout"` (same fact, no new evidence —
   E5's re-assert stays intact because there the transcript flipped status and
   cleared ownership). Red test: silence-stalled tool-handoff run + forced
   reconcile → stays `stalled`.
2. **Rule the wire evidence wins:** a >10-min quiet tool handoff IS
   `running-tools` (long Bash calls are real); then the current behavior is
   intended — document it in the spec and pin it with the same test asserting
   `running-tools`.

Either way the behavior must be chosen and tested; today it is an accident.

### F2 (clarification, answers the brief) — the one non-red test is T12, and it still gates

T12 asserts the ABSENCE of an effect (subagent ask → primary tier unchanged,
`reasoning` + `needsYou` null), which is precisely main's behavior — it is
necessarily green on the pre-behavior tree. It is NOT an always-true
assertion: with the wire step active, removing `track_role IS DISTINCT FROM
'subagent'` from `WIRE_SNAPSHOT_BY_RUN_SQL` makes the snapshot return the
subagent ask, the admission passes (id unresolved, no cold-start involvement),
the run projects `needs-you-asked`, and T12 fails. It meaningfully gates the
E8 isolation contract. The 12/13 red count is honest; the erratum is in MY
spec, which wrongly listed T12 among the fails-on-main set — isolation tests
gate by killing the guard, not by failing before the feature.

### F3 (minor, hygiene advisory) — `runActivityContext.ts` at 675 LOC

Up from 543; under the 700 guardrail but the next meaningful addition (the
gate slice) must refactor first. Natural seam when that day comes: the fold
family (pure reducers) vs the context/event vocabulary. No action in this PR.

## Observations (no action)

- `wireCandidateFromSnapshot` lets an ask block with a NULL `tool_use_id` fall
  through to running-tools — a literal deviation from §2 priority 1, but
  correct: a null id cannot anchor the resolution contract, and it is
  unreachable from the real writer (`ir.py:ToolUseBlock.id` is required, so
  `wire_store.py:_insert_response_blocks` always stamps it). Defensive only.
- The snapshot read is two indexed point queries (exchange row, then blocks)
  instead of one JOIN — fine at reconcile cadence.
- `telemetry.wireRetracted(runId)` takes a run id while
  `wireAdmitted`/`wireRefused` do not — mild API asymmetry, retraction is the
  rare event worth attribution.
- The api-plane touch is `session/test_activity_pg_contracts.py` +
  `contracts/pg-contracts.json` — the established cross-plane contract-lock
  test pattern (test-only, mirrors the existing run-lifecycle entries); not
  frozen-plane drift.
- Domain purity holds: `wireCandidate.ts` imports only `runActivityContext`;
  the snapshot→candidate mapping correctly lives in `service/` where the ports
  DTO and harness vocabulary are visible.
