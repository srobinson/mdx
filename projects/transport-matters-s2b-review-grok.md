# Adversarial review: PR #293 (S2b compatibility releases + channel state)

- **Reviewer:** grok (`transport-matters:general:1:2.3`)
- **Target:** `main...feat/s2b-compatibility-releases` / `gh pr diff 293`
- **Baseline:** `070e10e1` · **Head:** `f8fe90db`
- **Tree check (pre-verdict):** branch `feat/s2b-compatibility-releases`, clean working tree, `f8fe90db` (shared tree left pristine; no writes/checkouts/gates)
- **Scope:** 14 changed files only (correctness, then hygiene)
- **Method:** code-review lens + code-hygiene on the 14 files; offline import probes for digests/matcher/validator (not `just check` / `just test`)

## Summary

S2b lands a clean pure leaf (`compatibility.py`) and an I/O boundary (`compatibility_store.py`), honors the three scout reuse dispositions, and ships real fixture matrices rather than tautologies. Embedded data matches the plan (claude 2.1.211, codex 0.144.4, min=baseline, all four pointers paused, no grok). Production fail-closed is real: `RejectAllSignatureVerifier` rejects cached updates; paused embedded pointers cannot authorize via `match_release`.

One **Major** gap: channel-identity validation is asymmetric. The embedded loader rejects unknown channel ids; `validate_channel_update` accepts them. That is the path a trust-rooted update will use.

## Disposition verification (approved scout items)

| Disposition | Verdict | Evidence |
| --- | --- | --- |
| `canonical_digest` in `canonicalization.py`; `_intent_fingerprint` adopts it byte-identically | **Honored** | `canonicalization.py:79-81`; `launch_service.py:448-464`; guard `controlplane/test_launch_service.py:13-43` recomputes pre-helper `sha256(canonical_json).digest()` |
| Dead `detect_harness` (singular) deleted | **Honored** | Removed from `capabilities.py`; tests call `detect_harness_descriptor`; no production callers remain |
| No third `--version` parser; `resolve_codex_cli_version` not forked | **Honored** | `normalize_version` is pure full-match dotted numeric only; docstring defers extraction to observation adapter; `cli/codex_session.py` untouched in the diff |

## Contract focus (correctness)

| Rule | Verdict | Notes |
| --- | --- | --- |
| Stub rejects every mutable cached update | Pass | `RejectAllSignatureVerifier.verify` → `False`; test asserts `signature is not trusted` |
| Monotonic sequence rejects stale/replay | Pass | `sequence <= held` rejected; equal and older covered; newer and other-pointer accepted |
| Digest recompute via `canonical_digest` | Pass | `compute_release_digest` → `canonical_digest(release_digest_payload(...))`; no `hashlib` under `harnesses/` |
| Outcome codes exact | Pass | `harness_update_required`, `harness_version_blocked`, `harness_version_unknown`, `compatibility_release_unavailable`, plus route/target `connection_unavailable` / `target_unavailable` |
| Embedded paused fail-closed | Pass | All four states `paused`; matcher returns `compatibility_release_unavailable` until `status=active` |
| Unorderable version → unknown → cannot launch | Pass | `normalize_version` fails closed; `match_release` → `harness_version_unknown`; no new dependency |
| Pure leaf / I/O split | Pass | `compatibility.py` imports only re/typing/pydantic/canonicalization/HarnessId; store owns files/json/channel/resources |
| Embedded loader mirrors `channel.py` | Pass | `importlib.resources.files` + `lru_cache(maxsize=1)` + package artifact entry in `pyproject.toml` |
| Data invariants | Pass | Digests recompute offline; baselines/minima; no grok; pointers paused for stable+preview × claude+codex |
| Adapter revision set | Pass | 32 installed = 32 referenced; missing-revision rejection tested |

## Test rigor (matrix checklist)

| Required case | Present | Would fail pre-impl? |
| --- | --- | --- |
| Below minimum | Yes | Asserts `harness_update_required` + minimum version |
| Unknown / unorderable | Yes | Parametrized raw inputs → `harness_version_unknown` |
| Blocked version/route/target/release | Yes | Distinct outcomes and reason codes |
| Supersession clears | Yes | Superseded version block → `compatible` |
| Paused / revoked / missing pointer | Yes | Unavailable for all three |
| Tampered digest | Yes | Content change without reseal → reject |
| Stale / replay sequence | Yes | Equal and older held sequences |
| Missing adapter revision | Yes | Subtracts `claude-wire-request-r1` |
| Cached rejection (stub) | Yes | RejectAll on otherwise valid update |
| Embedded activation fail-closed | Yes | Paused unavailable; in-memory active compatible |
| Digest self-consistency | Yes | Recomputes every embedded digest |

Not tautologies: builders seal digests via `compute_release_digest`; negative cases mutate sealed payloads or subtract installed revisions.

## Issues

### Issue 1 — Severity: Major
- **File:** `api/src/transport_matters/harnesses/compatibility_store.py:129`
- **Description:** `validate_channel_update` never checks channel ids against `all_channel_specs()`, while `embedded_compatibility_manifest` does (`compatibility_store.py:220-225`). Offline probe: a trusted update with `channel="nightly"` is accepted. That breaks the single channel-identity rule for the path that becomes live once a trust root replaces `RejectAllSignatureVerifier`. Embedded and update validation are two doors into the same activation material; only one door checks the registry.
- **Suggestion:** Share one `_require_known_channels(manifest)` (or inline the same `known_channels` loop) and call it from both `validate_channel_update` and the embedded loader. Add a store test that AcceptAll + `channel="nightly"` raises `ChannelUpdateRejectedError`.
- **Status:** resolved in `11e800a1` — `_require_known_channels` single def, called from both doors; `test_unknown_channel_is_rejected` (nightly)

### Issue 2 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/compatibility.py:249` and `match_release` (`:379`)
- **Description:** `expires_at` is modeled and embedded as null, but neither `validate_channel_update` nor `match_release` enforces expiry. Contract text says an expired update cannot activate. Offline probe: `status=active` with `expires_at="2000-01-01T00:00:00Z"` still returns `compatible`. Acceptable deferral while only paused embedded data exists and no clock is injected, but the field is currently decorative.
- **Suggestion:** Either document expiry as application-service responsibility at activation (S2c/S2f) with an explicit comment on the field, or thread an optional `now` into validation/matching and reject expired active pointers. Prefer one owner, not both places half-doing it.
- **Status:** resolved in `11e800a1` — pure `is_expired(..., now=)`; enforced in `match_release` and `validate_channel_update`; fail-closed without trusted time; null expiry still matches with default `now=None`

### Issue 3 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/test_compatibility.py` (schema gap; validators live in `compatibility.py:132-238`)
- **Description:** Fixture matrices thoroughly cover matcher and store rules, but do not assert model-validator rejects for `minimum_version > baseline_version`, unnormalized baseline, active block with `superseded_by`, or target scope missing `model_id`. Those validators work (probed offline) yet a regression deleting them would not trip the current test files.
- **Suggestion:** Add a small parametrized schema-negative class next to the matcher matrices (three to five cases). Keep builders happy-path only.
- **Status:** resolved in `11e800a1` — `TestSchemaNegatives` covers all four cases

## Delta re-verify (`f8fe90db..11e800a1`, 2026-07-16)

- **Head:** `11e800a1` · tree clean · branch `feat/s2b-compatibility-releases` · no writes/gates
- **Findings:** 3/3 resolved; no new Major/Blocker from shared channel helper, expiry default, MappingProxyType freeze, or release-attributed block filter
- **Extra delta hardening (not regressions):** full `RELEASE_FACETS` coverage, digest validation on route/target/block evidence, foreign-harness block reject at manifest, deep-immutable signed maps
- **Verdict:** `verify: clean`

## Hygiene (14 files only)

| Check | Result |
| --- | --- |
| New file LOC < 700 | Pass (`compatibility.py` 449, store 244, tests 280/238, support 169) |
| Function size | Pass (`match_release` ~70 LOC; `validate_channel_update` ~50) |
| Duplication | Pass (no private sha256 in harnesses; payload assembly correctly domain-owned) |
| Parallel implementations | Pass (no third version parser; no second digest owner) |
| Boundary / dependency direction | Pass (leaf pure; store adapts resources + channel registry) |
| Dead code removal | Pass (`detect_harness` removed in the touching PR) |
| `*_test_support` in package | Matches repo convention (`launch_test_support`, `session_test_support`, etc.); not a new smell |

## Craftsmanship verdict

Tight leaf/store split, dispositions executed without leftover forks, and fail-closed defaults that match the contract; the only material hole is the unknown-channel asymmetry on the update validator.

## Counts

- **Blockers:** 0
- **Majors:** 1
- **Minors:** 2
