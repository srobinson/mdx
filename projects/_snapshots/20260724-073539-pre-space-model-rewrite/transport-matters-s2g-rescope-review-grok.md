# Review: feat/s2g-mint-activation (main..2539089a) — certification facet re-scope

- **Range**: `main..2539089a` (HEAD `2539089a`)
- **Branch**: `feat/s2g-mint-activation`
- **Reviewer**: grok (read-only; no repo writes)
- **Date**: 2026-07-18
- **Topic**: `tm-s2g-facet-rescope`
- **Tree at verdict**: pristine (`git status --porcelain` empty)

## Verdict

**Clean.** The 13→7 observability facet re-scope is coherent, closed, and fail-closed on production runtime evidence. HARD constraints hold. Authoritative pre-merge gate green.

## Scope reviewed

| Area | Files |
|------|--------|
| Facet model / gate | `certification.py`, `certification_test_support.py`, `test_certification.py` |
| Mint pipeline | `certification_minting.py`, `mint_harness_certification_record.py`, `test_certification_minting.py` |
| Atomic write-once | `atomic_io.py` |
| Store comment / docs | `compatibility_store.py`, `COMPATIBILITY-PUBLISHING.md`, `test_compatibility_store.py` |

10 files, +1289 / −120 across three commits (mint + integrity + re-scope).

## Cross-family focus

### (a) Vacuous / hollow facet predicates (esp. 4 auth, 7 launch)

**No production hollow pass path.**

- Production collector is `RealRuntimeEvidencePending`: any real mint that needs runtime scenarios raises until observability evaluators exist (`certification_minting.py`). Covered by `test_real_runtime_source_fails_closed`.
- Suite passes cannot be declared: closed argv, env injection stripped, junit proof requires `executed > 0` with zero failures/errors. Collect-only / all-skipped / missing report / exit-nonzero all refuse the mint.
- Plan facets are reference-only (`PlannedFacet`); `outcome="passed"` is stamped only at assembly after suites + runtime collection.
- Auth (`authentication_checkable` → `authentication_evidence_current`) and launch (`launch_capture_proven` → `launch_captured_owned_session`) are required facets; `DECLARABLE_FACETS` is empty so none may skip runtime evidence.

Structural opacity remains by design for this slice: predicate `evidence_digest` values are not yet bound to probe/session owners (evaluators are the later slice). That is intentional fail-closed tooling, not a silent green path.

### (b) Facets 5/6 drift reuse — no parallel path

- Docs and facet comments name the existing owners: wire via `drift_capture` → `blocks_store.emit_drift_evidence` over Tier-1 bytes; transcript via index adapters / owned copies.
- **No new drift scanner, emitter, or alternate store path** appears in the range.
- Evaluators that would *call* those owners are not in this PR; production mint cannot invent wire/transcript zero-drift claims.

### (c) Old 13-facet vocabulary retired

- `CERTIFICATION_FACETS` / `CertificationFacetId` / `FACET_PREDICATES` are the seven observability facets and their seven predicates only.
- Grep of harnesses: no residual `exact_harness_version`, `model_effort_actuation`, `facts_version_identity_agrees`, `ended_and_durable`, etc.
- Unrelated `project_layout` / `project_layout_revision` fields in the compatibility release schema are not certification facets.
- Tests renamed (`test_the_facet_vocabulary_is_the_closed_seven`, edge coverage on `launch_profile_resolved`).

### (d) HARD constraints

| Constraint | Evidence |
|------------|----------|
| Pointers still paused | Embedded channel states in `compatibility_releases_v1.json` remain `"status": "paused"` (4 states). `test_every_embedded_pointer_starts_paused` unchanged in spirit. **Manifest/release JSON not modified in this range** (0-byte diff). |
| `COMPATIBILITY_ROLLOUT` still advisory | `compatibility_service.py`: `COMPATIBILITY_ROLLOUT = "advisory"`; pinned by existing service test. Not touched by this range. |
| Manifest not touched | No channel/manifest/rollout/release JSON paths in `main..2539089a`. |

## Other integrity notes (non-blocking)

- `write_atomic_bytes_once` (`os.link` create-only) + concurrent-writer test: correct immutability seam for records.
- Double clean-worktree / HEAD recheck around mint write: honest `transport_matters_revision`.
- Successor reseal path uses `model_validate` + `compute_release_digest` (not `model_copy` of digests alone).
- Activation gate still binds `fixture_set_digest` + `certification_digest` ↔ release `evidence_digest`.

## Issues

None open (0 bugs, 0 suggestions blocking merge).

### Optional follow-up (out of range; not a merge blocker)

When observability evaluators land, consider failing closed if a scenario cites `wire_payloads_zero_drift` / `transcripts_zero_drift` while `wire_evidence_digest` / `transcript_evidence_digest` is null. Today null is allowed on the run model; production mint cannot reach it without evaluators.

## Authoritative gate

| Gate | Result |
|------|--------|
| `just check` | **exit 0** — desktop typecheck+102 tests; www format/lint/typecheck; api ruff + mypy (641 files) |
| `just test` | **exit 0** — desktop **102**; www vitest suites **1771 passed** (1247+24+8+286+185+21; some package skips only); api **2934 passed** in 172s |

**Tree after gate**: still pristine (no format churn left dirty).

## Summary line (bus)

`review: clean; gate: check+test green (api 2934, desktop 102, www 1771) findings: ~/.mdx/projects/transport-matters-s2g-rescope-review-grok.md`
