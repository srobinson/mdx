# PR #312 provider-rejection verdict surface — independent deep review (opus)

Branch `feat/launch-verdict-surface` @ f0bfb7e0 / a333aa11 / a18e2cb7. Read-only review. Gate not run (separate reviewer).

## Verdict: MERGE-READY

No blockers. Both load-bearing risks are handled correctly and provably. Findings below are LOW/INFO, ranked most-severe first.

---

## Risk 1 — Closed-vocabulary completeness: PASS (exhaustive)

Every mirror the scout enumerated is updated and the cross-language agreement is guarded by a test:

- DB check-constraint: `0027_model_rejected_kind.py` appends `model_rejected` (up) and downgrades cleanly (nulls rows + restores 6-kind constraint). Migration head bumped in `session/testing.py::EXPECTED_MIGRATION_HEAD_REVISION`, round-trip smoke extended in `test_migration_roundtrip.py`, dedicated round-trip in `test_migrate.py`.
- Python literal + enum: `live_status.py::LiveStatusKind` + `LIVE_STATUS_KINDS` + `MODEL_REJECTION_KIND`; `session/models.py::RunLiveStatusKind.MODEL_REJECTED = [6]` (index matches appended tuple position).
- Sticky-kind mirror: `live_status_contracts.py::RUN_LIVE_STATUS_STICKY_KINDS` includes it.
- Python control-plane mirror: `controlplane/activity.py::ACTIVITY_STATUSES` + `ActivityNeedsYouKind` + `ACTIVITY_NEEDS_YOU_KINDS`.
- TS port: `packages/activity/src/ports.ts::RUN_LIVE_STATUS_KINDS`; generated `contracts/pg-contracts.json`.
- Activity event union: `runActivityEvent.ts::ModelRejectedRecordedEvent` added to `RunActivityEvent`.
- XState machine: `record.model_rejected` added to every live state; `needs-you-model-rejected` state created via the renamed `stickyNeedsYouState()` factory (auth/usage/model-rejected now share one shape). `wireStatus.ts`, `activityStatusTier`, `needsYouForStatus`, `wireCandidate`, `runActivityEvents.ts` all extended.
- Wire contract: `packages/contract/src/activity/wire.ts` (status, tier, `ActivityNeedsYouModelRejected`, union, `needsYouForStatus`) + `index.ts` export.
- Roster: `observe_models.py::RosterItem.needs_you` + `service.py` passes `item.needs_you`.
- Watch: no code change needed — `envelope.py::_watch_subject` renders `-> needs_you [{status}]` generically; parametrized `test_watch.py` proves the model-rejected string reaches the PTY.
- Mirror guard: `test_type_mirrors.py` asserts both `needs-you-model-rejected` and `model_rejected` are present, keeping Python and TS in lockstep.

Machine exhaustiveness is genuinely enforced: `runActivityMachineGraph.test.ts:73` asserts strict set-equality between observed applied transitions and `expectedGraphTransitions`, which now enumerates model_rejected from all 9 source states plus the full sticky transition set out of the new state. The absent self-loop (`needs-you-model-rejected -> record.model_rejected -> itself`) is correctly filtered by `isAppliedTransition` (same exchangeId re-assert is a no-op), consistent with the pre-existing auth/usage states — not a gap. `emptyStatusCounts()` derives from `activityStatuses` so the histogram picks up the key automatically. `Record<ActivityStatus,...>` sites (`STATUS_LABELS` in RunVitalsStrip) updated; any miss would fail tsc.

## Risk 2 — Premature `submitted` / rejection precedence: PASS

`delivery_proof.py::_query` now gathers claims + `model_rejected` and orders: duplicate (`>1 claim`) → rejection → submitted. Rejection wins over an earlier/finalized request (`if rejected:` precedes the submitted branch). `submitted` now requires `finalized AND response_succeeded`; a bare outbound request is `finalized=False` → pending; a finalized *error* response is `response_succeeded=False` → pending → deadline `unknown`. Both event orders are tested: `test_rejection_wins_when_request_arrives_before_late_verdict` (early request row present, late verdict via a run event wake) and `test_rejection_before_submission_resolves_failed_without_exchange`. `test_failed_response_without_semantic_verdict_never_proves_submission` locks the tightened submitted gate.

The classifier→verdict race is closed structurally:
- Codex: `wire_store_observer._submit_wire_exchange` awaits the `observe_model_rejection` future *before* submitting the wire exchange, so the `model_rejected` row is committed before the delivery doorbell can wake the proof. `test_wire_store_observer` asserts `operations == ["live:model_rejected", "wire"]`. The returned future is meaningful under lane contention: `_drain` loops on `lane.latest` and only completes its future in the `finally` after draining, and `lane.future` is set/read/cleared under `self._lock` (verified `_offer` lines 476-529).
- Claude: proof now also subscribes to run events (`subscribe_run_events`), so a transcript-classifier write wakes it; and `resolve()` re-queries at the deadline, so even a missed wake still resolves `failed` from the durable row.

Surface-don't-gatekeep preserved: no target/model preflight added; `test_provider_rejection_surfaces_after_run_spawn[claude,codex]` asserts `gateway.spawn_count == 1` and `run_id == "run-created"` alongside the failed receipt.

## Item verification (a-e)

- (a) Classifiers are exact structured matches, never message-parsing. `is_claude_model_rejection`: `error=="model_not_found" AND isApiErrorMessage is True AND apiErrorStatus==404`. `is_codex_model_rejection`: server-only (`from_client` guard), `type=="error" AND status==400 AND error.type=="invalid_request_error"`. Neither reads `message`. Note the builder correctly followed the REQUIREMENTS over the scout here — the scout suggested also matching the unsupported-model message signature; the code does not, honoring "NEVER parse the human-readable message." Near-miss negatives tested for both.
- (b) Codex reads the WIRE: `_model_rejection_write` classifies `artifacts.transport.messages` (transport.json), never the rollout. Rollout cannot override — structurally enforced: `observe_transcript_record` early-returns for any non-claude harness, so codex rollout records never reach the classifier, and the codex verdict reads only transport.json. See gap #2 below re: an explicit test.
- (c) `CODEX_ERROR_EVENT_TYPE = "error"` added to `CODEX_KNOWN_SERVER_EVENT_TYPES`; `test_model_rejection` asserts `unknown_server_event_types(("error",)) == ()`, so no double-report as generic drift.
- (d) Sticky clears only on genuine later success or exit: `_offer` pops the sticky only on a terminal from a different generation with `provider_event != "flow_abort"`; machine transitions off only on real activity/exit. `test_model_rejection_is_sticky_until_a_later_success` and `wireActivity.test.ts` "selected model rejection" prove stickiness + recovery baseline (`lastActiveStatus` preserved).
- (e) Acceptance scenarios present: prompted (test_launch_manage, both harnesses), interactive roster (`test_roster_preserves_structured_model_rejection` with whoami+roster), Watch transition (parametrized `test_watch`), and still-spawns (spawn_count assertion). Migration constraint round-trip, exhaustive machine graph, roster serialization, proof ordering all covered. Fail-before/pass-after holds for the constraint, roster, machine, and proof tests.

## Findings (LOW / INFO)

1. LOW — Codex signature breadth. `status==400 && error.type=="invalid_request_error"` labels ANY 400 invalid_request as `model_rejected`, not only model rejection. This is the owner-specified signature (requirements item a), so per-spec, but a non-model 400 (e.g. malformed input) would surface a mislabeled `needs-you-model-rejected`. Blast radius is bounded: it never gatekeeps, the run stays live, and it clears on the next successful turn. Worth an explicit owner ack that the signature is intentionally coarse.

2. LOW (rigor) — Acceptance chaining. Prompted claude/codex acceptance (scout tests #1/#2) is proven as layered seam tests, not one end-to-end chain feeding the real native record through classifier → persist → read_store → proof → receipt. Each link is individually tested (classifier match; sticky persist; `read_store.model_rejected` True from a real persisted row in `test_read_store`; proof rejection-wins; launch surfaces failed via `FakeDeliveryProof`). The rollout-can't-override property (item b) is enforced structurally and proven indirectly (sticky clears only on genuine success), but no test explicitly feeds the misleading rollout `task_complete` and asserts the codex verdict is unchanged, which the scout's failing-test #2 called for. Coverage gap vs the plan, not a correctness defect.

3. INFO — Tightened `submitted` semantics. `submitted` now needs positive response evidence (`response_complete AND response_id IS NOT NULL AND response_error IS NULL`), so a prompted launch whose response has not completed within the bounded deadline resolves `unknown` where it previously resolved `submitted`. Verified the happy path still yields `submitted`: `InternalResponse.id` is a required field and `_response_error` returns None on success (only set when `provider_extras["error"]` is a dict). Intended and documented (CONTROLPLANE.md, LAUNCH-CONTRACT.md). Recommend the verify/gate step exercise a genuine successful prompted launch on both harnesses to de-risk the tightened gate live.

4. INFO — `duplicate_provider_requests` precedence. Duplicate is checked before rejection in `_query`, so a rejection turn that also produced a duplicate claim surfaces `unknown` not `failed`. Per the scout's step order; edge case.

## Over-engineering check (owner directive CLEAN AND SIMPLE): PASS — leaves code better

- `async_wait.py::wait_for_first` is a genuine DRY extraction: the identical gather/cancel pattern in `delivery_wait.py::_wait_for_doorbell` is refactored onto it in the same PR (two real callers, zero speculation).
- `_offer_sticky` generalizes `_offer_condition` (which now delegates) — model_rejected reuses the exact sticky machinery, no parallel path.
- `stickyNeedsYouState()` / renamed comments — one factory for three needs-you states, honest generalization.
- No new endpoints, MCP verbs, or services beyond the plan. `whoami()+roster()` reused; `GET /v1/runs/{id}` untouched; `RosterItem` extended, not duplicated. Migration is minimal. Tests are proportionate (parametrized, not gold-plated).

## Builder trust note

High confidence; delegatable at sizeable scope. This was the scout's #1 blast-radius risk (a closed cross-language vocabulary crossing ~11 mirrors plus a race-prone proof), and the builder landed every mirror, added the `test_type_mirrors` cross-language guard, and enforced machine exhaustiveness through a strict set-equality graph test rather than hand-waving it. It demonstrated real understanding of the correctness core: rejection precedence, the live-before-wire ordering that closes the codex doorbell race, and the run-events subscription that wakes the claude proof. Notably it followed the REQUIREMENTS over the scout where they diverged (never parse the message, despite the scout suggesting a message-signature match) and chose DRY extractions over copy-paste. The soft spots are all minor: no single end-to-end acceptance chain, one missing rollout-override test, and the intentionally-coarse codex 400 signature. None are shortcuts or quality erosion — this is careful, boundary-aware work.
