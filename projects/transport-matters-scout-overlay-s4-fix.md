---
title: "Scout: overlay S4 fix round (PR#377)"
type: projects
tags: [transport-matters, overlay, registry, cache, scout]
summary: "Reuse Map, Quality Map, and tests-first plan for the PR#377 fix round: H1 equal-revision recovery removal, H2 acquisition ordering, M3 signed grace ladder, M4/M5 artifact-expiry-only retention."
status: final
created: 2026-08-09
related: [transport-matters-spec-overlay-registry, tm-registry-decisions-memo]
project: transport-matters
confidence: high
---

# Scout: overlay S4 fix round, PR#377

Scouted at exact HEAD `9fa9041f7a6428ac3b504e44a1b5a737e5f217f7` (`feat/overlay-registry-capture-cache`, tree clean). Sources: `docs/ARCHITECTURE.md`, the chartered spec, the ratified decisions memo (`tm-registry-decisions-memo.md`, Decision 4 ratified as the signed grace ladder with a fourteen day default), and current cache, service, and test code. No repo writes were made.

## Reuse Map

Every piece of state the fix round touches, its owning symbol, writers, readers, and the precedence that holds today. Cite these owners in the build; a new owner is a defect.

| State | Owning symbol | Writers | Readers | Current precedence |
| --- | --- | --- | --- | --- |
| Accepted cache record file (`{digest}.json` under `ChannelSpec.home`/`overlay-cache/v1`) | `api/src/transport_matters/overlay_cache.py:OverlayAcceptedCache` | `OverlayAcceptedCache.install` (via `OverlayAcceptedCache._evaluate_candidate` → `atomic_io.py:write_atomic_json`), `OverlayAcceptedCache.record_acquisition` (via `OverlayAcceptedCache._record_acquisition`), `OverlayAcceptedCache.metadata` (observation persist via `OverlayAcceptedCache._observe_record`) | `OverlayAcceptedCache._load_held`; RPC `api/src/transport_matters/api/v1/overlay_capture_rpc_routes.py:read_overlay_metadata`, `validate_overlay_candidate`, `install_overlay_candidate`, `record_overlay_metadata` | Per tuple exclusive lock `OverlayAcceptedCache._record_lock` over `lock.py:exclusive_file_lock`. Higher valid revision replaces lower through `compatibility_store.py:validate_overlay_artifact` (`_require_newer_revision`, `revision_rollback`). Exception: the equal-revision recovery inside `_evaluate_candidate` (H1 target). |
| Accepted artifact envelope fields (revision, digests, expiry, grace deadline, bytes) | `api/src/transport_matters/overlay_cache_record.py:OverlayCacheRecord` | Minted only inside `OverlayAcceptedCache._evaluate_candidate` on acceptance; affirmed by `overlay_cache_record.py:affirm_accepted_record` on a byte-exact re-serve | `overlay_cache_record.py:decode_cached_artifact`, `record_matches_artifact`, `candidate_matches_accepted_envelope` | All-or-nothing envelope enforced by `OverlayCacheRecord._validate_metadata`; byte-exact equal revision short-circuits validation via `candidate_matches_accepted_envelope`. |
| Acquisition state (`last_acquisition_reason`, `allow_cached_use`) | `api/src/transport_matters/overlay_cache_record.py:_acquisition_state` via `update_acquisition_record` | TS `packages/overlay/src/service/OverlaySyncService.ts:acquisitionPolicy` decides values; delivered through `packages/overlay/src/adapters/captureOverlayCandidate.ts:CaptureOverlayCandidateAdapter.recordAcquisition` → RPC `record_overlay_metadata` → `OverlayAcceptedCache.record_acquisition` | `OverlayAcceptedCache._held_status`, `_load_held` fallback reason | Sticky denial: once `allow_cached_use` is false, `_acquisition_state` preserves the held reason and denial through any later non-affirmative write. Cleared only by `affirm_accepted_record` (accepted install or byte-exact 200) or a full-`None` affirm (304 path). Writes are NOT ordered by `refreshed_at` (H2 target). |
| Signed grace deadline | `api/src/transport_matters/overlay_artifact.py:OverlayArtifactDocument.entitlement_grace_expires_at` (publisher-signed) | Offline publication pipeline only; validated to fall between issue and expiry by the document model | `OverlayAcceptedCache._held_status`, `_evaluate_candidate` (copied into the record), `_artifact_reference` | Signed field; an unsigned status code can never extend it. Currently gates cached use for EVERY non-null reason (M3/M4 target). |
| Mode and reason derivation (`VERIFIED` / `PASSTHROUGH`) | `api/src/transport_matters/overlay_cache.py:OverlayAcceptedCache._held_status` and `_passthrough_status` | Derivation only, no persistence | RPC metadata reads; TS `OverlaySyncService.statuses` via `packages/overlay/src/projections/status.ts` | `allowed = allow_cached_use and (reason is None or grace unexpired)`; artifact expiry enforced upstream in `_load_held` through `validate_overlay_artifact`. |
| Observed-time monotonicity | `api/src/transport_matters/overlay_cache.py:_latest_instant`, `OverlayAcceptedCache._effective_now`, `OverlayAcceptedCache._observe_record` | Every cache operation advances `latest_observed_at` | `_effective_now` feeds expiry and grace checks | Monotone: a rolled back clock can never reopen expiry or grace. This is the anchor M3's first-lapse bound must reuse. |
| Validation, signature, revision floor | `api/src/transport_matters/harnesses/compatibility_store.py:validate_overlay_artifact` with `signature_verification.py:production_signature_verifier` | None (pure check) | `_evaluate_candidate`, `_load_held` | Strictly-greater revision against the held floor; expiry against effective now; trust through the shared `SignatureVerifier` seam. |
| TS in-memory refresh status | `packages/overlay/src/service/OverlaySyncService.ts:OverlaySyncService.statusByRelease` | `OverlaySyncService.refresh` | `OverlaySyncService.statuses` | Mirror of capture-plane truth; per tuple in-flight dedupe via `OverlaySyncService.inFlight`. Not durable, holds no policy of record. |
| HTTP status → acquisition policy mapping | `packages/overlay/src/service/OverlaySyncService.ts:acquisitionPolicy` | Static function | `OverlaySyncService.resolveResult` | Sole mapper of registry outcomes (`not_modified`, `disabled`, `forbidden`, `unauthorized`, `missing`, `not_acceptable`, `unavailable`) to `{allowCachedUse, reason}` (M3/M4/M5 target). |

Harness version change ending grace needs no code: the cache key digest (`OverlayAcceptedCache._cache_key`) includes the exact version, so a new version is a different tuple and reads `cache_miss` by construction.

## Quality Map

Strong and worth preserving as-is:

- Atomic write, residue recovery, restrictive mode: `test_overlay_cache.py:test_install_is_atomic_restrictive_and_recovers_residue`, `test_atomic_io.py`.
- Channel isolation, ETag non-authority, sanitized metadata: `test_cache_roots_are_isolated_by_channel_home`, `test_validation_writes_only_its_tuple_lock_and_etag_grants_no_authority`, `test_metadata_never_exposes_account_token_or_operation_values`.
- Clock rollback pinning: `test_observed_time_prevents_clock_rollback_from_reopening_grace` and the two expiry variants. M3 extends this pattern rather than inventing a new one.
- Cross process ordering under the lock: `test_process_race_cannot_finish_revision_two_after_revision_three`.
- Verifier regression pin at `c58998d9` and fail-closed trust: `test_restart_fails_closed_when_trust_is_unconfigured`.

Tests currently pinning behavior this fix round overturns (these flip first, red before green):

- `test_overlay_cache.py:test_403_retains_bytes_but_never_applies_held_state` and `test_denial_is_sticky_until_an_affirmative_result` pin the deterministic 403 baseline that ratified Decision 4 replaces (M3).
- `test_overlay_cache.py:test_held_state_is_reusable_only_inside_signed_grace` is parametrized over reasons and pins the grace bound for non-lapse reasons, which M4 removes.
- `test_overlay_cache.py:test_equal_revision_requires_complete_immutable_envelope_without_clearing_denial` pins the equal-revision recovery H1 deletes.
- `OverlaySyncService.test.ts`: "maps 403 directly to PASSTHROUGH even when accepted bytes are held" and "keeps a 403 denial after a candidate install fails" (M3), "does not let 406 reuse a held artifact" (M5).

Gaps with no coverage today:

- No test orders two acquisition writes; a stale affirm (`reason=None, allow_cached_use=None`) carrying an older `refreshed_at` clears a newer denial through `_acquisition_state`'s first branch (H2).
- No durable discriminator separates a 403 lapse from a 401 outage: both write `account_unavailable`, differing only in the client-supplied `allow_cached_use` flag. M3 cannot be expressed from durable state without one (see deviations).

## Tests-first plan

Order: H1, H2 land first (pure Python, no contract change), then M3 with M4 and M5 riding the same `_held_status` and `acquisitionPolicy` edits. Inner loop `just test-affected`, gates `just check` and `just test` verbatim.

### H1: remove equal-revision recovery

Current: `OverlayAcceptedCache._evaluate_candidate` nulls the validation floor when the held artifact fails revalidation and the raw candidate revision equals `prior_record.accepted_revision` (`_raw_revision`), letting an equal revision re-enter after record corruption. Spec: equal or lower revisions cannot replace an accepted cache; recovery is a strictly higher revision.

1. New test `test_equal_revision_never_recovers_a_broken_record`: corrupt the held record's artifact bytes on disk, then `install` a valid candidate at the same revision; assert `PASSTHROUGH` with reason `revision_rollback`, the broken record untouched, and a strictly higher revision accepted afterwards. Docstring: "Revision is strictly increasing for `(tenant_subject, harness, harness_version)`. Equal or lower revisions cannot replace an accepted cache."
2. Delete the two-line floor-nulling in `_evaluate_candidate` and `_raw_revision`; the floor is then unconditionally `prior_record.accepted_revision` when a prior record exists.
3. Rewrite `test_equal_revision_requires_complete_immutable_envelope_without_clearing_denial` to its surviving half: the byte-exact path (`candidate_matches_accepted_envelope`) still affirms a healthy held record without clearing denial semantics it should not clear.

### H2: ordered acquisition monotonicity

Current: `OverlayAcceptedCache._record_acquisition` writes caller-supplied `refreshed_at`, reason, and allow flag unconditionally; only `latest_observed_at` is monotone. Retries and reordered refresh results can regress newer state, including a stale 304 affirm clearing a fresh denial.

1. New test `test_stale_acquisition_cannot_regress_newer_state`: record a denial at `refreshed_at=T2`, then deliver an affirm (`reason=None`, `allow_cached_use=None`) at `refreshed_at=T1 < T2`; assert the denial, reason, and recorded `refreshed_at` are unchanged and the returned status reflects held state. Equal `refreshed_at` remains an idempotent retry.
2. Enforce in `_record_acquisition`: when a record exists and the incoming `refreshed_at` predates `record.refreshed_at` (compare through `_latest_instant`'s parsing, do not add a second time comparator), skip the write and return current status. Scope is acquisition only; install ordering is already governed by revision monotonicity.
3. TS side needs no change: `OverlaySyncService.inFlight` dedupes within one process; H2 closes the cross process and retry window at the durable owner.

### M3: first-403 signed grace ladder (ratified Decision 4)

Current: `acquisitionPolicy` maps `forbidden` to `{allowCachedUse: false, reason: "account_unavailable"}`, the immediate-passthrough baseline. The memo ratifies the ladder: on first 403 the exact cached artifact keeps applying until the earliest of the signed `entitlement_grace_expires_at`, artifact expiry, or harness version change; the first lapse observation is recorded so a rolled back clock shortens grace, never extends it; an unsigned 403 never extends authority.

1. Python test `test_first_403_starts_grace_and_terminal_is_earliest_bound` (parametrized: grace deadline first, artifact expiry first): install with a signed grace deadline, record a 403 lapse, assert `VERIFIED` with the lapse reason inside the window, `PASSTHROUGH` with the same reason at the earliest bound, and the lapse observation persisted on first 403 only (a second 403 does not move it). Docstring quotes the transport row: "`403` | Account lacks entitlement or `overlays:read` | Enter `PASSTHROUGH` immediately. Retain cache bytes for diagnostics but do not apply them. Open Decision 4 may replace this baseline with a signed grace rule." and notes the ratified Decision 4 grace rule now governs.
2. Python test `test_clock_rollback_cannot_reopen_lapsed_grace`: after the terminal instant, roll `now` back; assert `PASSTHROUGH` persists, reusing the `_latest_instant` anchor exactly as the existing rollback tests do.
3. Mechanism: extend `OverlayCacheRecord` with an optional lapse observation instant (validated by `_validate_metadata`, cleared by `affirm_accepted_record`), set once by `update_acquisition_record` when the acquisition marks a lapse; `_held_status` applies the grace bound only when a lapse is recorded. The RPC input (`overlay_capture_rpc_routes.py:record_overlay_metadata`, TS `OverlayAcquisitionInput`) gains the lapse marker; `acquisitionPolicy` maps `forbidden` to lapse-with-retention instead of `allowCachedUse: false`.
4. Flip the two pinned Python baseline tests and the two pinned TS 403 tests to the ladder; keep the `9fa9041f` property intact: an install failure during grace must not escalate the recorded lapse into a denial (extend "keeps a 403 denial after a candidate install fails" into its grace-era equivalent).

### M4: 401/404/5xx/network retention bounded by artifact expiry only

Current: `_held_status` gates cached use on the grace deadline for every non-null reason, so `account_unavailable` (401), `artifact_missing` (404), and `registry_unavailable` (5xx, network) lose retention at the grace deadline even though the artifact is unexpired. Since the document model forces grace between issue and expiry, these reasons always under-retain.

1. Python test `test_outage_reasons_retain_until_artifact_expiry` (parametrized over the three reasons): install with a grace deadline earlier than expiry, record the reason with retention allowed, advance past the grace deadline but before expiry, assert `VERIFIED` with the reason; advance past expiry, assert `PASSTHROUGH` with `artifact_expired` semantics from `_load_held`. Docstrings quote the transport rows: "`401` | Account token is absent or invalid | Keep an unexpired accepted cache. Otherwise `PASSTHROUGH`.", "`404` | No artifact has been published for the exact tuple | Keep any still valid accepted cache. A `404` never revokes signed state. Otherwise `PASSTHROUGH`.", "`5xx` or network failure | Registry unavailable | Keep an unexpired accepted cache. Otherwise `PASSTHROUGH`."
2. Implementation is the M3 mechanism's other half: `_held_status` consults the grace deadline only under a recorded lapse; artifact expiry already fails closed in `_load_held` through `validate_overlay_artifact`, so no new expiry check is added anywhere.
3. Re-scope `test_held_state_is_reusable_only_inside_signed_grace` to the lapse case only.

### M5: 406 retention bounded by artifact expiry only

Current: `acquisitionPolicy` maps `not_acceptable` to `{allowCachedUse: false, reason: "artifact_invalid"}`, revoking a held artifact on an unsigned status code, and the TS test pins it.

1. TS test `keeps a held artifact through 406 until artifact expiry` replacing "does not let 406 reuse a held artifact": a 406 result records its reason with retention allowed and the held status stays usable. Docstring quotes the transport row: "`406` | No supported artifact schema representation | Keep an unexpired accepted cache. Otherwise `PASSTHROUGH`."
2. Python coverage rides the M4 parametrized test by adding the 406-mapped reason to its reason set.
3. Change `acquisitionPolicy` `not_acceptable` to retention-allowed. Reason choice is the builder's smallest edit: keeping `artifact_invalid` is acceptable since M4 makes non-lapse reasons retention-neutral, but note `artifact_invalid` elsewhere means a failed candidate; if a cleaner label is wanted it must come from the existing closed `OVERLAY_PASSTHROUGH_REASONS` union, not a new member, unless the orchestrator approves a contract extension in both planes.

## Owner deviations observed

1. Denial authority currently crosses the RPC as the client-supplied boolean `allowCachedUse` decided by TS `acquisitionPolicy`, while the spec places acceptance and retention policy in the capture plane. M3 shrinks this: the signed grace deadline plus the capture-recorded lapse observation become the durable authority, and the boolean degrades toward advisory. The build should not add any further policy meaning to the client flag.
2. 401 and 403 share the reason `account_unavailable`, so the durable record cannot distinguish outage from lapse; the pre-fix code papers over it with the client flag. The M3 lapse-observation field is the fix; a new reason string would extend the closed contract union across both planes and is not required.
3. The equal-revision recovery (H1) is an unrecorded precedence exception to the spec's strictly-increasing revision rule; no decision log entry authorizes it.

No other deviation from the spec's writer table was found. Searches run for competing writers: `write_atomic_json` call sites (all inside `OverlayAcceptedCache`), `OverlayCacheRecord` constructors (cache and record modules plus tests only), `entitlement_grace` readers (document model, cache, record, tests only). None found outside the named owners.
