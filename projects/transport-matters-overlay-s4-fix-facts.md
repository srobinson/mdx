# Overlay Registry PR#377 fix round — source facts + test matrix

- **HEAD (exact)**: `9fa9041f7a6428ac3b504e44a1b5a737e5f217f7`
  (`fix(overlay): preserve sticky denial on install failure`)
- **Branch / PR**: `feat/overlay-registry-capture-cache` / PR#377
- **Scope**: acquisition/retention owners, ratified Decision 4, transport-contract status matrix, H1–M5 coverage and reuse symbols only
- **Repo changes in this pass**: none (facts artifact only)

Findings IDs from orchestrator fix brief (`overlay-registry-build`, 2026-08-09T07:13Z): **H1, H2, M3, M4, M5** (five findings; no H3/M1/M2 in this round).

---

## 1. Authority documents

### 1.1 Ratified Decision 4 (grace ladder)

| Source | Role |
| --- | --- |
| `~/.mdx/projects/tm-registry-decisions-memo.md` §4 | Written recommendation (14-day signed grace; terminal at earliest of grace, `expires_at`, harness version change) |
| Scout ratification note | Stuart ratified 2026-08-08 ("build it", cm `019fe082`) in `~/.mdx/projects/transport-matters-scout-overlay-registry-s4.md` § Decision 4 |
| Spec open-decision text | `~/.mdx/projects/transport-matters-spec-overlay-registry.md` § Open Decision 4 still carries the **pending** baseline wording (immediate PASSTHROUGH on 403). **Ratified memo supersedes that baseline.** |

**Ratified ladder (normative for this fix round):**

1. On first entitlement failure (`403` / product reason `account_unavailable`), the **exact held, signature-valid** artifact **keeps applying**.
2. Human surface shows lapse + deadline throughout grace.
3. Terminal `PASSTHROUGH` at the **earliest** of:
   - signed `entitlement_grace_expires_at` (default issued_at + 14d),
   - artifact `expires_at`,
   - harness / harness_version change (tuple no longer matches).
4. Guards: only **signed** timestamps bound authority; first-lapse / latest-observed wall-clock is monotonic so clock rollback **shortens** grace, never extends it; an unsigned `403` cannot invent or extend grace.

Disk-era note (memo): the live disk registry never emits `403`; the ladder and field must still be wired and test-pinned.

### 1.2 Registry transport contract (status → client behavior)

Owner text: `~/.mdx/projects/transport-matters-spec-overlay-registry.md` § "Registry transport contract".

| Status | Meaning | Client behavior (spec table) | Fix-round policy note |
| --- | --- | --- | --- |
| `200` | Signed artifact for tenant + exact tuple | Validate locally; promote only after full validation | Affirmative candidate path |
| `304` | Held digest still current | Revalidate held metadata; keep accepted cache | Affirmative; must not reopen post-grace denial from **stale** 304 (H2) |
| `401` | Token absent/invalid | Keep an **unexpired** accepted cache; else PASSTHROUGH | Bound by **artifact expiry only** (M4), not entitlement grace |
| `403` | Lacks entitlement / `overlays:read` | Spec **pending** text said immediate PASSTHROUGH + retain bytes. **Decision 4 ratified: keep applying through signed grace** (M3) | Grace ≠ immediate deny |
| `404` | No published artifact for tuple | Keep still-valid accepted cache; 404 never revokes signed state | Bound by artifact expiry (M4) |
| `406` | No supported representation | Keep an **unexpired** accepted cache; else PASSTHROUGH | M5: retain, do not force deny |
| `5xx` / network | Registry unavailable | Keep an **unexpired** accepted cache; else PASSTHROUGH | Bound by artifact expiry (M4) |

**Invariant (spec):** only a **newer signed** artifact whose disposition is `PASSTHROUGH` retires held APPLY authority. Status codes are not authority.

---

## 2. Current acquisition / retention owners at HEAD

### 2.1 Python (durable sole writer)

| Symbol | Path | Role |
| --- | --- | --- |
| `OverlayAcceptedCache` | `api/src/transport_matters/overlay_cache.py` | Sole durable accepted-cache owner: `validate`, `install`, `metadata`, `record_acquisition` |
| `_evaluate_candidate` | same ~L259 | Candidate decode → equal-envelope affirm → validation floor carve-out → `validate_overlay_artifact` → new record |
| `_held_status` | same ~L416 | Projects VERIFIED vs PASSTHROUGH from `allow_cached_use`, last reason, and **`entitlement_grace_expires_at`** |
| `_effective_now` / `_observe_record` | same | Monotonic observation clock via `latest_observed_at` |
| `OverlayCacheRecord` | `api/src/transport_matters/overlay_cache_record.py` | Durable record shape (bytes, etag, revision, expires, grace, observation, reason, allow flag) |
| `candidate_matches_accepted_envelope` | same | Byte-exact equal held envelope gate for 200/equal skip |
| `affirm_accepted_record` | same | Clears reason, sets `allow_cached_use=True` |
| `update_acquisition_record` / `_acquisition_state` | same ~L133–176 | Sticky denial until affirmative `(None, None)` |
| `validate_overlay_artifact` | `api/src/transport_matters/harnesses/compatibility_store.py` | Shared production validation order (schema → tenant → tuple → signature → revision → expiry → min TM → digest) |
| `production_signature_verifier` | `api/src/transport_matters/harnesses/signature_verification.py` | Sole production verifier factory |
| `write_atomic_json` / residue helpers | `api/src/transport_matters/atomic_io.py` | Only atomic write stack |
| Capture overlay RPC | `api/src/transport_matters/api/v1/overlay_capture_rpc_routes.py` | Loopback `/v1/capture/overlays/{validate,install,metadata}` → cache |

### 2.2 TypeScript (acquisition policy + product projection)

| Symbol | Path | Role |
| --- | --- | --- |
| `HttpOverlayRegistry` + `RESPONSE_KINDS` | `packages/overlay/src/adapters/httpOverlayRegistry.ts` | HTTP status → registry result kind (`403→forbidden`, `401→unauthorized`, `404→missing`, `406→not_acceptable`, `304→not_modified`; other/5xx → `unavailable`) |
| `OverlaySyncService.resolveResult` | `packages/overlay/src/service/OverlaySyncService.ts` | Candidate install vs non-candidate `recordAcquisition` |
| `acquisitionPolicy` | same ~L143 | Maps result kind → `{allowCachedUse, reason}` sent to capture plane |
| sticky install catch | same ~L122–125 | Held `PASSTHROUGH`+`account_unavailable` survives failed install (9fa9041) |
| `CaptureOverlayCandidateAdapter` | `packages/overlay/src/adapters/captureOverlayCandidate.ts` | Binds `OverlayCandidatePort` to capture RPC |
| `OverlayCandidatePort` | `packages/overlay/src/ports.ts` | `currentStatus` / `installCandidate` / `recordAcquisition` |
| Wire DTOs | `packages/contract/src/overlay/wire.ts` | Closed reasons, artifact doc incl. `entitlement_grace_expires_at` |

### 2.3 Live policy map (HEAD, pre-fix-round)

| Registry kind | TS `acquisitionPolicy` (HEAD) | Python `_held_status` when held exists | Aligns with fix brief? |
| --- | --- | --- | --- |
| `not_modified` | `{null, null}` affirmative | `affirm` path clears denial if install/equal envelope; acquisition clear always | H2: must be **freshness-ordered** |
| `forbidden` (403) | `{false, account_unavailable}` | `allow_cached_use=false` → immediate PASSTHROUGH; bytes retained | **M3 NO** — must keep applying through signed grace |
| `unauthorized` (401) | `{true, account_unavailable}` | Reuse gated by **entitlement grace** when reason set | **M4 NO** — should gate on **artifact expiry** only |
| `missing` (404) | `{true, artifact_missing}` | Same grace gate | **M4 NO** |
| `unavailable` (5xx/net) | `{true, registry_unavailable}` | Same grace gate | **M4 NO** |
| `not_acceptable` (406) | `{false, artifact_invalid}` | Immediate deny when flag false | **M5 NO** — keep unexpired cache |
| `disabled` | `{false, disabled}` | Immediate deny | Out of H1–M5 |
| `candidate` install fail | sticky if held denial else 4xx→`artifact_invalid` / else `registry_unavailable` | n/a (TS projection) | Sticky denial already pinned (adjacent to M3) |

---

## 3. 403 vs 401/404/406/5xx/network — and grace vs artifact expiry

### 3.1 Status family distinction (builder must not collapse)

| Family | Wire | Product reason (typical) | Retention during failure | Application during failure | Bound |
| --- | --- | --- | --- | --- | --- |
| Entitlement | **403** | `account_unavailable` | Always retain held bytes | **Apply through signed grace** (Decision 4 / M3) | earliest of grace, `expires_at`, tuple change |
| Auth token | **401** | `account_unavailable` | Keep if unexpired | Keep applying while unexpired | **`expires_at` only** (M4) |
| Missing publish | **404** | `artifact_missing` | Keep if still valid | Keep applying while valid | **`expires_at` only**; never revokes (M4) |
| Representation | **406** | `artifact_invalid` (today) / keep held | Keep unexpired | Keep applying while unexpired | **`expires_at` only** (M5) |
| Transport | **5xx / network** | `registry_unavailable` | Keep unexpired | Keep applying while unexpired | **`expires_at` only** (M4) |

`account_unavailable` appears for **both** 401 and 403 in product vocabulary. The **status / allow flag / bound field** distinguishes them; builders must not treat every `account_unavailable` as grace-gated.

### 3.2 Field distinction

| Field | Owner | Authority |
| --- | --- | --- |
| `entitlement_grace_expires_at` | Signed artifact + cache record | **Only** for entitlement-lapse (403) ladder; must not bound 401/404/406/5xx reuse |
| `expires_at` | Signed artifact + cache record | Absolute artifact lifetime; bounds all "keep unexpired cache" rows |
| `latest_observed_at` | Cache record (local, monotonic max with clock) | Clock-rollback safety; never extends signed deadlines |
| `allow_cached_use` | Cache record (acquisition machine) | Sticky deny / affirm; must interact correctly with M3 (403 is not "never apply") |
| `last_acquisition_reason` | Cache record | Sanitized last reason for freeze/diagnostics |

HEAD defect pattern: `_held_status` applies **grace** whenever `reason is not None` and `allow_cached_use` is true — that incorrectly puts M4 families on the grace clock.

---

## 4. Test matrix: H1 through M5

### 4.1 Finding → required behavior → existing tests → gap

| ID | Required behavior (fix brief) | Primary code owners (HEAD) | Existing tests that touch the seam | HEAD status vs requirement |
| --- | --- | --- | --- | --- |
| **H1** | Remove equal-revision recovery carve-out: equal/lower never replace; unusable/corrupt held → PASSTHROUGH + diagnostic evidence; recovery only via **strictly higher** valid signed revision | `overlay_cache.py` `_evaluate_candidate` L314–316 (`validation_floor = None` when `held is None` and raw revision equals floor); install path | `test_unusable_higher_revision_remains_the_validator_floor` (pins equal-revision **repair** of corrupt held at same revision → VERIFIED); `test_equal_revision_requires_complete_immutable_envelope_without_clearing_denial`; `test_byte_exact_equal_held_revision_skips_candidate_validation_and_preserves_bytes` (byte-exact same envelope, not recovery) | **Open.** Equal-revision repair path and floor-nulling carve-out still present. Need failing-before test: corrupt held + equal valid revision stays PASSTHROUGH / floor intact; only higher revision recovers. |
| **H2** | Acquisition machine monotonic: affirmative clears denial **only if fresher than the denial**; stale 200/304 after **post-grace 403** must never reopen authority | `overlay_cache_record.py` `_acquisition_state` L162–176; `affirm_accepted_record`; equal-envelope affirm in `_evaluate_candidate` | `test_denial_is_sticky_until_an_affirmative_result` (sticky for non-affirmative only); `test_not_modified_restores_cached_use_and_clears_stale_reason` (**unconditional** affirm); equal-revision skip tests | **Open.** Affirmative always clears. Need ordered observations + post-grace 403 then stale 304/200 does not restore VERIFIED. |
| **M3** | 403 implements ratified ladder: first 403 → held artifact **keeps applying**; record first-lapse/observation; terminal PASSTHROUGH at earliest of grace / expiry / harness change; unsigned 403 never extends authority | TS `acquisitionPolicy` `forbidden` L149–150; Python `record_acquisition` + `_held_status`; observation clock | `test_403_retains_bytes_but_never_applies_held_state` (**pins immediate deny**); TS `maps 403 directly to PASSTHROUGH even when accepted bytes are held` (**pins immediate deny**); `test_held_state_is_reusable_only_inside_signed_grace` (grace with `allow_cached_use=True`); clock-rollback tests; RPC `test_capture_overlay_metadata_records_403_without_deleting_bytes`; sticky install `keeps a 403 denial after a candidate install fails` | **Open / inverted.** HEAD implements pre-ratification immediate PASSTHROUGH for 403. Tests that pin immediate deny must flip to Decision 4 ladder and **quote the transport-contract/Decision 4 row** in docstrings. Disk registry still never emits 403 (exercise via direct acquisition). |
| **M4** | 401/404/5xx/network retention bounded by **artifact expiry only**, never `entitlement_grace_expires_at`; 404 never revokes signed state | TS policy for unauthorized/missing/unavailable; Python `_held_status` bound selection | TS `lets the cache enforce signed grace for unauthorized|missing|unavailable` (**wrong bound name/intent**); Python `test_held_state_is_reusable_only_inside_signed_grace` parametrizes those reasons on **grace**; artifact-expiry clock-rollback tests exist but do not isolate "grace field ignored for non-403" | **Open / inverted.** Need tests that hold grace already past but `expires_at` still future → still VERIFIED for 401/404/5xx; and grace still future but `expires_at` past → PASSTHROUGH. Quote transport-contract rows. |
| **M5** | 406 keeps an **unexpired** accepted cache | TS `not_acceptable` policy L156–158 | TS `does not let 406 reuse a held artifact` (**pins deny**); HTTP map `httpOverlayRegistry.test.ts` 406→`not_acceptable` | **Open / inverted.** Policy should allow cached use; cache enforces `expires_at`. Flip TS test; add Python retention pin if missing. |

### 4.2 Adjacent coverage (keep; not the five findings)

| Area | Tests |
| --- | --- |
| Channel isolation / atomic write / residue | `test_cache_roots_are_isolated_by_channel_home`, `test_install_is_atomic_restrictive_and_recovers_residue` |
| Invalid candidate never clobbers | `test_invalid_candidate_never_clobbers_valid_held_bytes` |
| Restart revalidation / reject-all | `test_restart_revalidates_through_production_verifier`, `test_restart_fails_closed_when_trust_is_unconfigured` |
| Metadata sanitization | `test_metadata_never_exposes_account_token_or_operation_values`, `test_acquisition_reason_persists_without_an_accepted_artifact` |
| Process race / locks | `test_process_race_cannot_finish_revision_two_after_revision_three`, `test_validation_writes_only_its_tuple_lock_and_etag_grants_no_authority` |
| Capture RPC surface | `api/v1/test_overlay_capture_rpc_routes.py` (validate/install/metadata, not product routes, structured errors) |
| Artifact schema / grace field shape | `harnesses/test_overlay_artifact.py` (incl. grace between issue and expiry), `packages/contract/src/overlay/overlay.test.ts` |
| HTTP status mapping | `httpOverlayRegistry.test.ts` |
| Adapter binding | `captureOverlayCandidate.test.ts` |
| Sync service refresh mechanics | dedupe, retry, 200 delivery, 304 no install, install HTTP mapping |

### 4.3 Test authoring rules (from orchestrator)

- Every fix: **failing before**, **passing after**.
- **M3/M4** tests must quote the transport-contract row (and for M3, Decision 4) in docstrings so the 403-vs-rest inversion cannot recur.
- Gates: `just check`, `just test-affected feat/overlay-registry`, `just test` (builder owns; this pass does not run them).

---

## 5. Minimal symbols the builder must reuse (no reinvention)

| Capability | Reuse exactly |
| --- | --- |
| Validation engine | `validate_overlay_artifact` + default `production_signature_verifier` |
| Canonical digests / schema | `overlay_artifact.py` (`OverlayArtifactDocument`, grace field validation) |
| Durable store | `OverlayAcceptedCache` only (extend in place) |
| Record transitions | `replace_cache_record`, `affirm_accepted_record`, `update_acquisition_record`, `candidate_matches_accepted_envelope` — fix `_acquisition_state` / `_held_status` here, do not fork |
| Expiry helper | `is_expired` from harnesses compatibility |
| Atomic I/O | `write_atomic_json` / `write_atomic_bytes` / residue helpers |
| Capture loopback | existing overlay capture RPC routes + `CaptureOverlayCandidateAdapter` |
| Product acquisition map | single `acquisitionPolicy` in `OverlaySyncService` |
| Closed vocabularies | `@tm/contract/overlay` + Python `OVERLAY_PASSTHROUGH_REASONS` |
| Test seals | `harnesses/overlay_artifact_test_support` (`apply_artifact` / `seal_raw` patterns already used by `test_overlay_cache.py`) |

**Do not touch:** OverrideStore / apply path / request pipeline (Slice 4 boundary). Do not add a second verifier, second cache root, or TS durable cache.

---

## 6. Highest-risk seams for the fix round

1. **Policy inversion debt:** several green tests currently pin the **pre-Decision-4** 403 behavior and the **grace-for-all-reasons** projection. Fixes will require deliberate test rewrites, not only new cases.
2. **`_held_status` single gate:** one boolean expression currently couples all non-null reasons to `entitlement_grace_expires_at`. Split: 403/account entitlement uses grace∩expiry; other retention uses expiry only.
3. **H1 vs byte-exact equal path:** keep `candidate_matches_accepted_envelope` for true identical held bytes; delete only the **corrupt equal-revision recovery** carve-out (`validation_floor = None` when held missing).
4. **H2 freshness:** affirmative 200/304 must consult acquisition observation order (and post-grace denial), not merely sticky-until-affirm.
5. **TS is not authority:** capture plane enforces bounds; TS must send the correct `allowCachedUse` so durable state matches Decision 4 / transport table.

---

## 7. Five-row executive matrix

| ID | One-line fact at HEAD |
| --- | --- |
| H1 | Equal-revision recovery carve-out still live at `overlay_cache.py:314-316`; corrupt same-rev repair still pinned green |
| H2 | `_acquisition_state` clears on any affirmative; 304 restore test pins unconditional reopen |
| M3 | 403 still immediate PASSTHROUGH in TS+Python; Decision 4 grace-apply not implemented for forbid path |
| M4 | Non-403 retention incorrectly uses entitlement grace clock in `_held_status` + shared grace tests |
| M5 | 406 mapped to `allowCachedUse:false`; TS test pins non-reuse against transport contract |

---

*Produced for PR#377 fix round at SHA `9fa9041f7a6428ac3b504e44a1b5a737e5f217f7`. No repository modifications.*
