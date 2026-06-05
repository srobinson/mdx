# Scout: overlay-s4-time-fix — reuse and quality map

HEAD `ab21eab6c6e66eaaebdf4a1571d3c81b0cf850ca`, clean tree. Scout pass only, no writes.
Builder brief: gpt-sol. Blind spot to guard: the seam between the two time axes, not any one file.

## The two time axes (the seam)

The cache runs on two clocks that must never contaminate each other:

1. **Server observation axis** (`latest_observed_at`): minted only from `OverlayAcceptedCache._now` (default `overlay_cache.py:_utc_now`, format `+00:00` with microseconds). Monotonic high-water mark. Never derived from caller input. Owns expiry judgment.
2. **Caller order axis** (`refreshed_at`): supplied verbatim by the RPC caller (`api/v1/overlay_capture_rpc_routes.py:OverlayCandidateRequest` / `OverlayMetadataRequest`; minted in the product plane by `packages/overlay/src/service/OverlaySyncService.ts` as `this.clock.now().toISOString()`, format `Z` with milliseconds). Owns ordered retention: which acquisition observation counts as newer.

The format mismatch is real in production: the Python clock and the TS clock emit different aliases of the same instant, and both pass `canonicalization.py:require_utc_instant` (its regex accepts `Z`, `+00:00`, and any fractional-digit count).

## Owning symbols: writers, readers, precedence

### `canonicalization.py:require_utc_instant`
Owner of instant *shape*. Layer 1, stdlib only. Validates strict RFC3339 UTC; does not normalize, so semantically equal aliases remain distinct strings. Readers: `overlay_cache.py:_latest_instant`, `overlay_cache.py:_require_request_instant` (maps failure to `OverlayCacheError("invalid_request")`), `overlay_cache_record.py:OverlayCacheRecord._validate_metadata`, `overlay_artifact.py:OverlayArtifactDocument._validate_document`. No writer; pure gate.

### `overlay_cache.py:_latest_instant`
Owner of the max-instant precedence rule. Parses via `datetime.fromisoformat`; on a tie (`>=`) returns the *left* (candidate) string. Readers: `_effective_now`, `_observe_record`, `_record_acquisition`, `_is_strictly_newer_instant`. The tie-returns-left choice is what lets aliases through `_is_strictly_newer_instant` (below).

### `overlay_cache.py:_is_strictly_newer_instant`
Owner of the ordered-retention gate predicate. Current definition: `candidate != current` (string inequality) AND `_latest_instant(candidate, current) == candidate`. Readers: `OverlayAcceptedCache._record_acquisition` (unconditional gate when a record exists) and `OverlayAcceptedCache._evaluate_candidate` (gate on install when the prior record carries a denial — `last_acquisition_reason` set or `allow_cached_use` false — and again on the byte-equal affirm path).

**Alias defect (confirmed by reading, not yet pinned by any test):** for the same instant re-encoded (`02:00:00Z` vs `02:00:00+00:00` vs `02:00:00.000Z`), string inequality is true and `_latest_instant` returns the candidate on the semantic tie, so the alias counts as *strictly newer*. The tie rule (first writer wins; pinned for byte-equal ties by `test_overlay_cache_acquisition.py:test_stale_affirmative_cannot_clear_a_fresher_denial`) silently becomes last-writer-wins across aliases. Since Python and TS mint different alias formats by default, this is the production path, not a corner.

### `OverlayCacheRecord.refreshed_at` (`overlay_cache_record.py:OverlayCacheRecord`)
Writers, all under the per-tuple lock, all through `atomic_io.write_atomic_json`:
- `OverlayAcceptedCache._evaluate_candidate` via new-record construction and `overlay_cache_record.py:affirm_accepted_record` (install paths),
- `OverlayAcceptedCache._record_acquisition` via `overlay_cache_record.py:update_acquisition_record`.

Persisted **verbatim from caller input, unbounded**. Which writer wins: the one whose caller-supplied `refreshed_at` is "strictly newer" under the predicate above; ties lose (no write).

**Future-skew wedge (confirmed by reading):** one request with a far-future `refreshed_at` (wrong client clock) persists that instant. Afterward every sane-clocked `record_acquisition` fails the strictly-newer gate in `_record_acquisition` and is a silent no-op until real time passes the bogus instant. Direction of harm is the bad one: if the wedged state is affirmative (`allow_cached_use` true), a genuine 403 lapse **cannot be recorded**, so cached authority is *extended*, not shortened. The same wedge blocks denial-clearing installs. This violates the fail-closed direction the rest of the module pays for.

### `OverlayCacheRecord.latest_observed_at`
Writers: `OverlayAcceptedCache._observe_record` (metadata reads and install-miss paths, via `overlay_cache_record.py:replace_cache_record`), `_record_acquisition` and the affirm path (via `update_acquisition_record` / `affirm_accepted_record`, `observed_at` argument). Every write is `_latest_instant(self._now(), record.latest_observed_at)`: monotone non-decreasing, server clock only, never touched by `refreshed_at`. Readers: `OverlayAcceptedCache._effective_now`. Precedence: max wins; a rolled-back clock loses. **Keep this axis uncontaminated** — the builder must not fold caller `refreshed_at` into it.

Future skew here (server clock briefly future) wedges `_effective_now` high, which only makes artifacts look expired sooner and inflates `cacheAgeSeconds` (`overlay_cache.py:_age_seconds` floors at 0). Authority shortens; nothing is extended. That asymmetry is the model to copy.

### `OverlayAcceptedCache._effective_now`
Owner of trusted time: `max(now, latest_observed_at)`. Readers: `_load_held` and `_evaluate_candidate` (as `now=` into `compatibility_store.validate_overlay_artifact`), `_held_status` (grace check via `harnesses/compatibility.py:is_expired`, and `_age_seconds`). `is_expired` is the sole owner of the expiry comparison; it fails closed on missing/malformed/unorderable inputs and treats the boundary instant as expired. Do not add a second expiry comparator.

### Sticky denial and lapse
- `overlay_cache_record.py:_acquisition_state`: owner of denial stickiness. A record with `allow_cached_use` false keeps its reason and stays denied until the affirmative `reason=None, allow_cached_use=None` (304) path; pinned by `test_denial_is_sticky_until_an_affirmative_result` and `test_403_cannot_reopen_a_prior_kill_switch_denial` (kill-switch `disabled` outranks a later 403).
- `overlay_cache_record.py:_entitlement_lapse_observed_at`: owner of first-lapse-wins. First `account_unavailable` with `allow_cached_use=False` against a held affirmative record stamps `observed_at` (server axis); repeats keep the first stamp; pinned by `test_first_403_retains_exact_held_artifact_until_signed_grace`.
- `overlay_cache_record.py:affirm_accepted_record`: the only writer that clears lapse, reason, and restores `allow_cached_use` — byte-exact re-accept or new accept only.

### Terminal PASSTHROUGH
`OverlayAcceptedCache._held_status` owns mode derivation: artifact disposition `PASSTHROUGH` → mode PASSTHROUGH reason `disabled` (or the recorded reason); lapse observed → allowed only while `entitlement_grace_expires_at` unexpired at `_effective_now`; otherwise `allow_cached_use`. `_load_held` maps a validator `artifact_expired` on a record carrying `last_acquisition_reason` back to that recorded reason, which is how terminal status keeps naming the real cause (`account_unavailable` at grace end) — pinned by `test_first_403_retains_exact_held_artifact_until_signed_grace` and `test_non_entitlement_failures_retain_until_artifact_expiry`.

## Behavior today, by scenario

- **Semantically equal UTC aliases:** pass `require_utc_instant`; compare as *strictly newer* through `_is_strictly_newer_instant`; `_latest_instant` resolves the tie to the candidate. No test pins alias behavior anywhere in `test_overlay_cache_acquisition.py` or `test_overlay_cache.py`.
- **Tied 403 (byte-identical instant):** no-op — gate fails, prior state (affirmative or kill switch) stands; pinned for stale and kill-switch cases, tie-with-alias unpinned and currently reopens the write path.
- **Future-dated observation:** persisted verbatim into `refreshed_at`; wedges all later sane-clocked acquisitions/installs; can extend authority by blocking a genuine lapse. Unpinned.
- **Rollback after terminal:** safe. `latest_observed_at` high-water is persisted before the rollback read (`_observe_record` runs on held metadata reads and on record-only misses), so `_effective_now` stays past grace/expiry; pinned by the three `*clock_rollback*` tests and `test_held_metadata_read_persists_observation_before_clock_rollback`.

## Recommended shape (one minimal change, two clauses, same owners)

Keep both axes and their owners; change only the two functions that already own the seam. Precedence rule in one sentence: **the server observation axis bounds the caller order axis, and newness is semantic, with ties (including aliases) losing.**

1. **Semantic strict-newness.** Redefine `overlay_cache.py:_is_strictly_newer_instant` as parsed `datetime` strict `>` (drop the string inequality). Aliases of an equal instant become ties and lose, restoring first-writer-wins everywhere the predicate is read. No caller changes; both read sites inherit it.
2. **Bound the persisted order token.** At the two persist sites that accept caller `refreshed_at` (`_record_acquisition`, `_evaluate_candidate` accept/affirm paths), store `min(refreshed_at, _effective_now(record))` — i.e., the earlier instant, reusing `_latest_instant`'s parsing discipline (a small inverse helper beside it; search below found no existing min-instant owner). The gate still compares the caller value, but the *stored* value can never lead the server's trusted time, so a future client clock can no longer wedge later observations. A future-dated denial is then recorded at effective-now (authority shortens, clearable next tick); a future-dated affirmative extends nothing.

Why this shape and not alternatives: normalizing instants at `require_utc_instant` (returning a canonical string) touches a layer-1 gate consumed by signed-payload validation (`overlay_artifact.py`) where byte-stability matters — larger blast radius for the same effect. Minting `refreshed_at` server-side changes the RPC contract and the TS `OverlaySyncService` clock seam. Rejecting future `refreshed_at` as `invalid_request` makes loopback millisecond skew a hard failure. The clamp is the only shape where a wrong clock in either direction can only shorten authority and never wedge.

Pinning tests to demand from the builder (observable end-state, failing before the fix): an alias-encoded tied 403 must not clear or overwrite same-instant state; a far-future `refreshed_at` followed by a sane-clocked genuine lapse must record the lapse (mode PASSTHROUGH at grace end, not wedged VERIFIED).

Review tripwires for the build: no second writer to `latest_observed_at`; no caller input on the server axis; no new expiry comparator beside `is_expired`; no datetime comparison outside `_latest_instant`/`_is_strictly_newer_instant` and their new inverse.

## Reuse searches run

- `grep -rn "_is_strictly_newer_instant|_latest_instant|require_utc_instant|_record_acquisition|latest_observed_at"` over `*.py` → the six files mapped above; no other owner.
- `grep -rn "fromisoformat"` (non-test) → `canonicalization.require_utc_instant`, `harnesses/compatibility._parse_instant`/`is_expired`, `certification_evidence`, two `cli/` display paths, `session/ingest` (`Z`→`+00:00` replace, transcript-side only). **None found** that owns a general min/earliest-instant or alias-normalizing helper; the inverse helper proposed above has no existing home to reuse.
- `grep -rn "normalize|monotonic|latest_"` (non-test) → only version normalization, `time.monotonic` deadlines, and the symbols already mapped. None found for instant normalization.
- TS side: `refreshedAt` minted in `packages/overlay/src/service/OverlaySyncService.ts` (`clock.now().toISOString()`), carried through `packages/runtime/src/adapters/CaptureRpcClient.ts` and `packages/contract/src/overlay/wire.ts`. No TS-side ordering logic competes with the Python gate.

Note in passing: Python 3.14 (PEP 758) unparenthesized `except A, B:` clauses appear in `overlay_cache.py:_load_held`, `overlay_cache_record.py:candidate_matches_accepted_envelope`, and `overlay_capture_rpc_routes.py:_candidate_bytes` — valid on the repo's 3.14.5, flagged only so the builder does not "fix" them.

## Addendum: tie precedence reconciliation (follow-up directive)

The two constraints — alias equality counts as *not newer*, and a tied 403 must be impossible to drop through ordering luck — conflict under a single symmetric predicate. Ties-lose alone reintroduces the bad direction: an affirmative install at instant T followed by a 403 whose `refreshed_at` is also T (same poll tick, or the same instant re-encoded) would be a silent no-op in `_record_acquisition`, and cached authority is *extended*. That is exactly the drop-through-ordering-luck the directive forbids, and it is the behavior at HEAD today for the byte-identical tie.

**Reconciliation: the tie-break is direction-dependent, matching the module's direction of harm.** The ordering gate exists to protect held state from stale or replayed *affirmations*; denials never needed that protection, because denial-vs-denial precedence is already owned downstream by `overlay_cache_record.py:_acquisition_state` (sticky denial keeps the first reason — a tied 403 cannot overwrite a kill-switch `disabled`) and `overlay_cache_record.py:_entitlement_lapse_observed_at` (first lapse wins). So:

- **Affirmative or neutral writes** (`allow_cached_use` is not False): require semantic *strictly newer* (parsed instants, aliases equal, ties and aliases lose). A tied or alias-encoded affirmation cannot clear a same-instant denial.
- **Denial writes** (`allow_cached_use is False`): require semantic *not older* (`>=`). A tied 403 lands; a strictly older 403 still loses to a fresher affirmation, preserving `test_stale_affirmative_cannot_clear_a_fresher_denial`'s mirror-image logic in both directions.

**Minimal owner:** the single gate inside `OverlayAcceptedCache._record_acquisition`, expressed as one new predicate beside `_is_strictly_newer_instant` (an "orders ahead" predicate over parsed instants taking whether the write denies cached use), reusing `_latest_instant`'s parsing discipline. `_evaluate_candidate`'s two gate sites are affirmative by construction (candidate installs and byte-equal affirms) and keep the strict predicate, gaining only semantic comparison. Denial-vs-denial and lapse precedence stay where they live: `_acquisition_state` and `_entitlement_lapse_observed_at`. No third writer, no new state.

**Exact before-failing test shapes** (both fail at HEAD, observable end-state):

1. *Tied 403 lands.* Install an APPLY artifact with `refreshed_at="2026-08-08T02:00:00Z"`; call `record_acquisition(reason="account_unavailable", allow_cached_use=False, refreshed_at="2026-08-08T02:00:00Z")` (byte-identical tie). Assert the persisted record has `allow_cached_use is False` and `entitlement_lapse_observed_at` stamped; advance `now` past signed grace and assert `metadata` reports `PASSTHROUGH` / `account_unavailable`. At HEAD the gate drops the tied write and the terminal read stays `VERIFIED`-derived: fails.
2. *Alias affirmation cannot clear a denial.* Record a denial at `refreshed_at="2026-08-08T03:00:00Z"`; then call the affirmative `record_acquisition(reason=None, allow_cached_use=None, refreshed_at="2026-08-08T03:00:00+00:00")` (semantically equal alias). Assert mode stays `PASSTHROUGH` with the denial reason and `allow_cached_use is False` persists. At HEAD the alias counts as strictly newer and the affirmation clears the denial: fails.

The clamp recommendation from the main map is unchanged and composes with this: bounded stored `refreshed_at` prevents the wedge; the direction-dependent tie-break prevents the drop.
