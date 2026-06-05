# Overlay S4 compose-fix facts

- **HEAD**: `1ce90289ec2b438e0effdd6621ef7d5ab87ec19e` (`fix(overlay): harden cache time precedence`)
- **Tree**: clean on `feat/overlay-registry-capture-cache`
- **Pass**: assistant fact pass only; no repository writes; no review
- **Sources**: `docs/ARCHITECTURE.md` (no overlay-cache detail), controlling spec `~/.mdx/projects/transport-matters-spec-overlay-registry.md`, current `overlay_cache.py` / `overlay_cache_record.py` / `overlay_capture_rpc_routes.py`, `test_overlay_cache_acquisition.py`

## Spec precedence (verbatim by section name only)

- **Writers and precedence** — Accepted local cache sole writer is the capture plane validator; higher valid revision replaces lower for the exact tuple.
- **Registry transport contract** — status matrix including `304` keep accepted cache; `403` baseline still reads immediate PASSTHROUGH with Open Decision 4 note (ratified Decision 4 grace ladder supersedes that baseline in implementation).
- **Contract rules** — Revision is strictly increasing for `(tenant_subject, harness, harness_version)`. Equal or lower revisions cannot replace an accepted cache.
- **Cache** — Capture plane validates and owns the accepted cache; a failed candidate never overwrites a last known valid entry.
- **Slice 4: Capture validation and accepted cache** — validate/install/metadata ports; shared verifier; one accepted cache under `ChannelSpec.home`; retain last valid after invalid candidate; sanitized metadata only.

`docs/ARCHITECTURE.md` has no accepted-cache or acquisition-order text at this HEAD.

---

## Two time axes and narrowest owners

| Axis | Durable field | Role | Narrowest owner |
| --- | --- | --- | --- |
| Server observation | `latest_observed_at` | Trusted high-water for grace/expiry | **`OverlayAcceptedCache._effective_now`** = `_latest_instant(self._now(), record.latest_observed_at)` (or bare `_now()` when no record). Writers that advance the stored field: `_observe_record`, acquisition/affirm/accept paths via `observed_at` / `accepted_at`. |
| Caller order | `refreshed_at` | Ordered retention: which acquisition/install observation may write | **Total denial/acquisition order gate inside `OverlayAcceptedCache._record_acquisition`** (direction-dependent predicate over `_is_strictly_newer_instant`). Candidate install/affirm gates in `_evaluate_candidate` use strict-only. Persist bound: `_bounded_refreshed_at`. |

### Instant helpers (exact, HEAD)

```text
_latest_instant(left, right) → left if fromisoformat(left) >= fromisoformat(right) else right
_is_strictly_newer_instant(candidate, current) → fromisoformat(candidate) > fromisoformat(current)
_bounded_refreshed_at(candidate, effective_now) →
  effective_now if candidate is strictly newer than effective_now else candidate
```

Shape gate only: `canonicalization.require_utc_instant` (accepts `Z` and `+00:00`); request failures become `OverlayCacheError("invalid_request")` via `_require_request_instant`. No second datetime comparator elsewhere in the cache module.

---

## Entry paths: one incoming observation → order compare → persistence

All public cache methods take `_storage_boundary` + per-tuple `_record_lock`. RPC entry: `overlay_capture_rpc_routes.py` → `OverlayAcceptedCache.{validate,install,metadata,record_acquisition}`.

### A. `POST .../metadata` acquisition (`record_acquisition` → `_record_acquisition`)

1. Validate `refreshed_at` UTC; reject unknown `reason` not in `OVERLAY_PASSTHROUGH_REASONS`.
2. `_load_held` (see below).
3. **Order gate** when a record already exists:
   - if `allow_cached_use is False` (denial write): ordered iff `not _is_strictly_newer_instant(record.refreshed_at, refreshed_at)` i.e. candidate is **not older** (`>=` semantic).
   - else (affirmative / retention / neutral): ordered iff `_is_strictly_newer_instant(refreshed_at, record.refreshed_at)` i.e. candidate is **strictly newer**.
4. If not ordered: `_observe_record` may ratchet `latest_observed_at` only; return `_loaded_status` / held status; **no** acquisition field mutation.
5. If ordered:
   - `observed_at = _latest_instant(now, latest_observed_at)`
   - `update_acquisition_record(..., refreshed_at=_bounded_refreshed_at(refreshed_at, observed_at), observed_at=...)`
   - `write_atomic_json` record path
   - return `_held_status` if held artifact, else `_passthrough_status` with reason

**304 path:** product maps not-modified → `reason=None, allow_cached_use=None`. That pair is the affirmative clear in `_acquisition_state` / `_entitlement_lapse_observed_at`.

### B. `POST .../install` candidate (`install` → `_evaluate_candidate` with `persist_observation=True`)

1. `_load_held`; if prior record exists, **first** `_observe_record` (server axis advance before any candidate decision).
2. If prior carries denial (`last_acquisition_reason is not None` or `allow_cached_use is False`) and candidate `refreshed_at` is not strictly newer: return held/loaded status, `record=None` (no install write).
3. Decode JSON; on failure `_rejected_candidate` (status only; does not mutate acquisition).
4. **Byte-equal envelope** (`candidate_matches_accepted_envelope`): 304-equivalent affirm of held bytes.
   - requires strictly newer `refreshed_at`; else status-only.
   - else `affirm_accepted_record` with `_bounded_refreshed_at`; clears lapse, reason, sets `allow_cached_use=True`; caller `install` writes if `evaluation.record` set.
5. Else `validate_overlay_artifact` with floor `prior_record.accepted_revision` (strictly greater; no equal-revision recovery) and `now=_effective_now(prior_record)`.
6. On accept: new `OverlayCacheRecord` with fresh envelope, `allow_cached_use=True`, reasons/lapse cleared, `refreshed_at=_bounded_refreshed_at(...)`, `latest_observed_at=accepted_at`; install writes.
7. On validation reject: `_rejected_candidate` status only; held bytes retained.

### C. `POST .../validate` (`persist_observation=False`)

Same evaluation as install but **no** `_observe_record`, **no** order gate against denial, **no** affirm write, **no** disk write. Pure candidate judgment.

### D. `GET .../metadata` (`metadata`)

`_load_held` → if held or record-only miss, `_observe_record` then `_held_status` / `_passthrough_status`. Observes server time only; never touches `refreshed_at` or acquisition reason.

### E. Rollback / clock rollback

- Observation high-water is persisted on metadata reads and on ordered acquisition/install paths before a later rolled-back wall clock is consulted.
- `_effective_now` uses max(wall, `latest_observed_at`), so grace/expiry cannot reopen after a past observation.
- Stale affirm after a later denial: order gate fails; `_observe_record` still ratchets `latest_observed_at` on the no-op path (`test_stale_observation_ratchets_time_before_clock_rollback`).

---

## Denial reason trace (every hop)

Incoming product policy (TS `acquisitionPolicy`, not re-audited here) supplies `reason` + `allow_cached_use` into `record_acquisition`.

### 1. `update_acquisition_record`

Calls:

1. `_entitlement_lapse_observed_at(record, reason, allow_cached_use, observed_at)`
2. `_acquisition_state(record, reason, allow_cached_use)` → `(next_reason, next_allowed)`
3. Writes `refreshed_at`, `latest_observed_at=observed_at`, `entitlement_lapse_observed_at`, `last_acquisition_reason`, `allow_cached_use` onto new or replaced `OverlayCacheRecord`.

### 2. `_entitlement_lapse_observed_at` (first-lapse-wins, server axis)

- Affirm `(reason is None and allow_cached_use is None)` → clear to `None`.
- No record or no artifact bytes → `None` (no grace stamp).
- Existing `entitlement_lapse_observed_at` → keep first stamp.
- Else stamp `observed_at` only when `record.allow_cached_use and reason == "account_unavailable" and allow_cached_use is False` (true first 403 lapse against affirmative held state).
- Prior kill-switch denial (`allow_cached_use` already False) never stamps a later 403; grace cannot open under `disabled`.

### 3. `_acquisition_state` (sticky denial)

| Input | Result |
| --- | --- |
| `reason is None and allow_cached_use is None` | `(None, True)` clear / 304 affirm |
| Prior `allow_cached_use is False` | `(prior.last_acquisition_reason or reason, False)` sticky; later 403 cannot overwrite kill-switch reason |
| `allow_cached_use is False` | `(reason, False)` first denial |
| `allow_cached_use is None` with reason | `(reason, prior.allow or True)` retention-style |
| `allow_cached_use is True` | `(reason, True)` |

Cleared only by affirm path above or by `affirm_accepted_record` (install accept / byte-equal re-serve).

### 4. `_held_status` → mode + status reason

- `disposition == PASSTHROUGH` → mode PASSTHROUGH, reason `last_acquisition_reason or "disabled"`.
- Else if `entitlement_lapse_observed_at is not None`: `allowed = not is_expired(entitlement_grace_expires_at, now=_effective_now)`; during grace VERIFIED with lapse reason; after grace PASSTHROUGH with stored reason.
- Else: `allowed = allow_cached_use`; false → PASSTHROUGH with reason or `artifact_expired`.
- Non-lapse retention reasons with `allow_cached_use True` stay VERIFIED until artifact expiry (expiry owned by `_load_held` / `validate_overlay_artifact` / `is_expired`).

### 5. `_load_held` reason when artifact unusable

- missing file → `cache_miss`
- corrupt JSON/model → `artifact_invalid`
- no bytes → `last_acquisition_reason or cache_miss`
- decode fail / envelope mismatch → `artifact_invalid`
- `validate_overlay_artifact` fail: if `artifact_expired` **and** `last_acquisition_reason` set, **preserve acquisition reason** (terminal still names `account_unavailable` etc.); else validator reason.
- healthy held: third tuple element is `"cache_miss"` placeholder; real reason comes from the record via `_held_status`.

### 6. Metadata mode surface

`_status` / `_passthrough_status` project `mode`, `reason`, `lastRefreshAt` (= stored `refreshed_at`), `cacheAgeSeconds` from validated_at→`_effective_now`, never account tokens or operation values.

---

## Three RED cases: exact current mechanisms at HEAD

Pinned in `test_overlay_cache_acquisition.py`. At `1ce90289` these are **green** under the hardened time-precedence code (not open defects).

### RED-1 — Semantically equal UTC alias must not clear a denial

- Test: `test_semantically_equal_utc_alias_is_not_newer`
- Setup: denial at `refreshed_at=Z`; affirm `(None, None)` with alias `+00:00` same instant.
- Mechanism: `_is_strictly_newer_instant` is pure parsed `>`; aliases compare equal → affirm branch of `_record_acquisition` gate fails → status-only + optional `_observe_record`; sticky denial fields unchanged.

### RED-2 — Tied 403 must land (cannot be dropped by ordering luck)

- Test: `test_tied_403_cannot_be_ignored`
- Setup: install APPLY at `T`; `record_acquisition(account_unavailable, allow_cached_use=False, refreshed_at=T)` same instant; advance past signed grace; metadata terminal.
- Mechanism: denial branch uses **not older** (`>=`): tied write is ordered → `update_acquisition_record` → `_acquisition_state` sets allow False → `_entitlement_lapse_observed_at` stamps first `observed_at` → after grace `_held_status` yields PASSTHROUGH / `account_unavailable`.

### RED-3 — Future-dated client observation must not wedge a later real 403

- Test: `test_future_dated_observation_cannot_wedge_a_later_403`
- Setup: affirm with far-future `refreshed_at`; then real-time 403; then past grace metadata.
- Mechanism: every persist of caller order uses `_bounded_refreshed_at(refreshed_at, observed_at|_effective_now)` so stored `refreshed_at` cannot lead server effective time; later real `refreshed_at` is strictly newer than the clamped stamp and the denial lands.

Related pins (not the three RED cases but same seam): `test_stale_affirmative_cannot_clear_a_fresher_denial` (stale 304 / stale 200), `test_stale_observation_ratchets_time_before_clock_rollback`, kill-switch vs 403 `test_403_cannot_reopen_a_prior_kill_switch_denial`.

---

## Owner summary (requested)

| Concern | Narrowest single owner |
| --- | --- |
| Effective observation time | `OverlayAcceptedCache._effective_now` |
| Total denial / acquisition write order | Direction-dependent order gate in `OverlayAcceptedCache._record_acquisition` (denial: semantic `>=`; affirm/neutral: semantic `>`; shared compare helper `_is_strictly_newer_instant`; store bound `_bounded_refreshed_at`) |

Downstream sticky reason precedence after a write is admitted remains `_acquisition_state` + first-lapse `_entitlement_lapse_observed_at`; mode projection remains `_held_status`. Do not invent a second owner for those.
