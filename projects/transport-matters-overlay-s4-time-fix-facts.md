# Overlay S4 time-fix facts

HEAD: `ab21eab6c6e66eaaebdf4a1571d3c81b0cf850ca` (`fix(overlay): preserve kill switch denial`)  
Scope: `api/src/transport_matters/overlay_cache.py`, `overlay_cache_record.py`, `canonicalization.require_utc_instant`, tests in `test_overlay_cache*.py`.  
No repository writes. Fact pass only.

## UTC instant parsing

- Shared gate: `canonicalization.require_utc_instant(name, value)`.
- Shape: `_RFC3339_UTC_RE = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)"` (fullmatch), then `datetime.fromisoformat` for calendar validity.
- Accepts only uppercase `T` and terminal `Z` or `+00:00`. Non-UTC offsets, space separators, and lowercase `z` fail.
- Request path: every public `refreshed_at` goes through `_require_request_instant` → `require_utc_instant`; `ValueError` becomes `OverlayCacheError("invalid_request")`.
- Record path: `OverlayCacheRecord` model validator requires UTC instants on `expires_at`, `entitlement_grace_expires_at`, `validated_at`, `refreshed_at`, `latest_observed_at`, `entitlement_lapse_observed_at` when present.
- Comparison path: `_latest_instant` re-validates both sides with `require_utc_instant` before `datetime.fromisoformat` compare.
- Default clock: `_utc_now()` = `datetime.now(UTC).isoformat()` (typically `+00:00` form, not `Z`). Injectable via `OverlayAcceptedCache(now=...)`.
- No code rejects instants merely because they are future relative to wall clock. Parsing is shape/calendar only.

## Ordering and equality

Two distinct high-water marks:

| Field | Role | Advanced by |
| --- | --- | --- |
| `record.refreshed_at` | Client observation order gate | Acquisition / install / affirm only when `_is_strictly_newer_instant(candidate, record.refreshed_at)` |
| `record.latest_observed_at` | Trusted time floor for expiry/grace | `_latest_instant(now, latest_observed_at)` on observe, acquisition, affirm, accept |

Helpers (exact):

```text
_latest_instant(left, right) → left if fromisoformat(left) >= fromisoformat(right) else right
_is_strictly_newer_instant(candidate, current) →
  candidate != current and _latest_instant(candidate, current) == candidate
```

Facts:

- String equality short-circuits “strictly newer”: identical strings are never newer.
- Datetime-equal but string-different forms (`Z` vs `+00:00`) pass the string check, then `_latest_instant` returns `left` on `>=`, so the candidate is treated as strictly newer.
- `_effective_now(record)` = wall `now` if no record, else `_latest_instant(now, record.latest_observed_at)`. Never decreases.
- Stale/equal client `refreshed_at` under denial or any acquisition write path returns loaded status and does not mutate the record (install path only applies the gate when a denial/reason or `allow_cached_use is False` is present; acquisition always applies it when a record exists; equal-envelope affirm also gates).

## Tied denial handling

Sticky denial policy lives in pure record helpers:

- `_acquisition_state`: if prior `allow_cached_use is False`, keep `(prior last_acquisition_reason or new reason, False)`. Later non-affirmative or partial allowances cannot reopen.
- Affirmative acquisition: `reason is None and allow_cached_use is None` clears reason, sets `allow_cached_use=True`, clears entitlement lapse via `_entitlement_lapse_observed_at` early return `None`.
- Kill-switch vs 403 (HEAD fix ab21eab6): `_entitlement_lapse_observed_at` only stamps when `record.allow_cached_use and reason == "account_unavailable" and allow_cached_use is False`. A prior kill-switch denial (`allow_cached_use=False`, e.g. reason `disabled`) therefore keeps `entitlement_lapse_observed_at is None` and stays terminal PASSTHROUGH; a later 403 cannot open grace.
- Order gate on tied/stale client time: `test_stale_affirmative_cannot_clear_a_fresher_denial` pins equal-revision 200, higher-revision 200, and 304 with older `refreshed_at` leave fresher denial intact (`refreshed_at` high water preserved).
- Equal held envelope + newer `refreshed_at` affirm path clears denial without revalidation (`affirm_accepted_record`); equal revision with non-byte-identical envelope rejects and does not clear denial (`test_equal_revision_requires_complete_immutable_envelope_without_clearing_denial`).

## Future-dated observations

Two inputs can be “in the future”:

1. **Wall clock / injected `now`**  
   - Any observe/accept/acquire path sets `latest_observed_at = max(now, prior)`.  
   - Tests pin clock rollback cannot reopen grace or artifact expiry after a future observation (`test_observed_time_prevents_clock_rollback_*`, `test_held_metadata_read_persists_observation_before_clock_rollback`).  
   - Effect on authority: `is_expired(..., now=effective_now)` uses the high water, so a future clock can only expire earlier (shorten authority), never reopen.

2. **Client `refreshed_at`**  
   - Validated only as UTC instant, not bounded by `now` or `latest_observed_at`.  
   - If a future (or otherwise strictly newer) `refreshed_at` is accepted while mutating, it becomes the durable order high water.  
   - Later real-time observations with smaller `refreshed_at` hit `_is_strictly_newer_instant` false and are no-ops (status only). That is a wedge of later observations relative to real time, distinct from the wall-clock high water.

## Accepted cache high-water persistence

- Path: `{channel_home}/overlay-cache/v1/{canonical_digest(tenant, harness, harness_version)}.json` via `write_atomic_json`.
- Persisted fields of interest: `refreshed_at`, `latest_observed_at`, `entitlement_lapse_observed_at`, `last_acquisition_reason`, `allow_cached_use`, plus accepted artifact envelope when held.
- `_observe_record` writes only when `latest_observed_at` actually advances (`observed_at == record.latest_observed_at` → no write).
- `validate()` takes the tuple lock but never writes a record (`persist_observation=False`).
- `install()` / `record_acquisition()` / `metadata()` may persist under the same lock.

## Terminal PASSTHROUGH

Status construction:

- `_passthrough_status` always `mode="PASSTHROUGH"` with a reason; may still attach a held artifact reference when evaluating a rejected candidate against a held artifact.
- `_held_status`:
  - artifact disposition `PASSTHROUGH` → mode PASSTHROUGH, reason `last_acquisition_reason or "disabled"`.
  - if `entitlement_lapse_observed_at is not None`: allowed while grace not expired (`is_expired(entitlement_grace_expires_at, now=effective_now)`); then PASSTHROUGH with `account_unavailable` (or stored reason).
  - else: allowed iff `allow_cached_use`; kill-switch/false → PASSTHROUGH with stored reason or `artifact_expired`.
- Terminal after grace/expiry keeps last acquisition reason (e.g. `account_unavailable`, non-entitlement failure reasons).
- Denial without held bytes: PASSTHROUGH reason record / cache_miss; acquisition reasons without artifact persist as reason-only records.

## Per-tuple locking

- `_record_lock(harness, harness_version)`: `exclusive_file_lock(root / f".overlay-cache-v1-{cache_key}.lock")`.
- `cache_key = canonical_digest({tenant_subject, harness, harness_version})`.
- Lock is blocking `flock` (`lock.exclusive_file_lock`); serializes concurrent holders for that tuple only.
- All public methods wrap `_storage_boundary` (OSError → `unavailable`) + `_record_lock`.
- Test pin: `test_validation_writes_only_its_tuple_lock_and_etag_grants_no_authority` asserts exactly one `.overlay-cache-v1-*.lock` and no `.json` from validate alone.

## Minimal future-skew options vs invariant

Invariant target: **a wrong clock may only shorten authority and must not wedge later observations.**

| Option | Authority shortening | Later observations | Fit |
| --- | --- | --- | --- |
| **A. Status quo** | Wall `latest_observed_at` max shortens grace/expiry (good). Client future `refreshed_at` can raise order water (bad). | Future client `refreshed_at` wedges lower real-time updates (fails invariant). | Current failure |
| **B. Reject client `refreshed_at` > effective_now** (`invalid_request` or no-op without advancing water) | Unchanged wall ratchet. | Future client stamp cannot raise order water; later real stamps still apply. | Matches invariant with one gate |
| **C. Clamp stored `refreshed_at` to `min(client, effective_now)` when writing** | Unchanged wall ratchet. | Prevents future wedge; collapses distinct future stamps onto now. | Works; slightly looser than B |
| **D. Drive order water only from server `_now()` / `_effective_now`** | Same. | Removes client order authority entirely. | Stronger redesign than needed |
| **E. Cap or ignore future wall `now` when advancing `latest_observed_at`** | Would prevent premature expiry from a fast clock (opposite of “may only shorten”). | No wedge effect. | Contradicts stated invariant |

### Current failure mechanism (exact)

Client `refreshed_at` is an unbounded UTC instant that, once strictly newer and persisted, becomes the durable acquisition/install order high water; any later observation with a smaller real-time `refreshed_at` is dropped, so a wrong/future client clock can wedge later observations. Separately, `latest_observed_at = max(wall, prior)` already implements shorten-only authority for grace and artifact expiry and is pinned against rollback reopen.

### Safest minimal shape

Keep the `latest_observed_at` max ratchet unchanged. Add one bound on client order time: refuse to advance `refreshed_at` when the client instant is strictly after `_effective_now(record)` (option B; clamp C is acceptable second choice). Do not let client future stamps raise the order high water; do not soften the wall high water (that would re-open expired authority).

## Test inventory (time / denial / lock)

- Acquisition sticky/terminal: `test_overlay_cache_acquisition.py` (403 grace stickiness, kill-switch preserve, sticky denial, 304 clear, stale affirmative, observed-time rollback suite).
- Envelope/lock/authority: `test_overlay_cache.py` (tuple lock on validate, equal-revision affirm, invalid candidate non-clobber, revision floor).

---

## Addendum: semantic alias equality and tied 403 (topic overlay-s4-time-fix-tie)

HEAD still `ab21eab6c6e66eaaebdf4a1571d3c81b0cf850ca`. No repository writes.

### Directive constraints

1. Semantic alias equality (`Z` vs `+00:00`, same calendar instant) must count as **not newer**.
2. A **tied 403** (same semantic `refreshed_at` as the held denial water) must be **impossible to drop** through ordering luck (string-form or equal-time second writer).

### Current predicate

```text
_is_strictly_newer_instant(candidate, current) =
  candidate != current and _latest_instant(candidate, current) == candidate
```

`_latest_instant` returns `left` when `fromisoformat(left) >= fromisoformat(right)`.

### Reconciliation vs `_record_acquisition`

Gate at top of `_record_acquisition` (always when a record exists):

```text
if record is not None and not _is_strictly_newer_instant(refreshed_at, record.refreshed_at):
    return _loaded_status(...)  # no mutation
```

- String-equal ties: correctly not newer → 403 preserved.
- Alias-equal ties (`2026-08-10T03:00:00Z` held, candidate `2026-08-10T03:00:00+00:00`): `candidate != current` is true, `_latest_instant` returns candidate on datetime equality → treated as **strictly newer** → mutation proceeds.
- On that false-newer path, an affirmative (`reason=None`, `allow_cached_use=None`) runs `update_acquisition_record` → `_acquisition_state` clears denial (`None, True`) and clears lapse → **tied 403 drops** solely because of alias form.
- A second 403 at alias-equal time would also enter the mutate path; sticky `_acquisition_state` would keep denial, so same-class denials do not self-drop, but affirmatives do.

### Reconciliation vs candidate paths (`_evaluate_candidate`)

Two gates both call the same helper:

1. **Denial install gate** (persist only): when prior has `last_acquisition_reason is not None` or `allow_cached_use is False`, require strictly newer `refreshed_at` else return loaded status / `record=None`.
2. **Equal-envelope affirm gate** (persist only): require strictly newer before `affirm_accepted_record` (which clears denial, lapse, sets allow).

Alias-equal affirmative 200 (byte-exact held envelope) or any denial-gated install with alias-equal `refreshed_at` therefore also clears or rewrites when it should no-op. Clean VERIFIED installs (no denial reason) still do not order-gate new revisions; that is out of scope for the tied-403 constraint but is a separate order hole.

### Minimal owner preserving tie precedence

**Owner:** `_is_strictly_newer_instant` in `overlay_cache.py` (sole order predicate shared by `_record_acquisition` and both candidate gates).

**Required semantics:** after `require_utc_instant` on both sides, return true iff

```text
datetime.fromisoformat(candidate) > datetime.fromisoformat(current)
```

(equivalently: max is candidate **and** instants are not equal). Drop the `candidate != current` string short-circuit as the equality test; string form must not affect order.

No change required to `_acquisition_state` / sticky denial for this tie class once the predicate refuses equal-time mutation: first writer under the per-tuple lock wins at a semantic tie; second writer cannot drop a recorded 403 by alias form or identical stamp.

Optional non-owner: callers already no-op correctly when the predicate returns false; do not fork tie logic into `_record_acquisition` and `_evaluate_candidate` separately.

### Exact before-failing test shape

One behavioral test (or two tight siblings) that fails on HEAD and passes after the predicate fix:

```text
setup:
  install APPLY artifact at refreshed_at = T0 ("…Z")
  record_acquisition(
    reason="account_unavailable",
    allow_cached_use=False,
    refreshed_at = T1 ("2026-08-10T03:00:00Z"),
  )
  assert mode PASSTHROUGH or VERIFIED-in-grace per grace bounds;
  assert allow_cached_use is False;
  assert refreshed_at == T1 Z form;
  assert entitlement_lapse_observed_at == observed high water for first 403

cases (each must leave record bytes / denial fields unchanged):
  A. record_acquisition affirmative
       reason=None, allow_cached_use=None,
       refreshed_at = T1 alias ("2026-08-10T03:00:00+00:00")
  B. install byte-exact equal held envelope (304-equivalent affirm path)
       refreshed_at = T1 alias
  C. optional: same two ops with refreshed_at exactly T1 Z (string-equal control)

assert after each:
  status still denied (reason "account_unavailable", allow_cached_use False)
  record["refreshed_at"] remains T1 Z (no form rewrite)
  record["entitlement_lapse_observed_at"] unchanged
  record["allow_cached_use"] is False
```

Before fix: A and B clear denial (ordering luck). After fix: all no-ops.

### Decision line

Semantic `>` on parsed UTC instants is the sole newer-predicate; at a non-strict tie the held denial (including 403) retains precedence and cannot be dropped.
