# Review: PR #307 / feat/s2g-evaluator-source (main..171801b9)

- **Range**: `main..171801b9` (HEAD `171801b9`)
- **Branch**: `feat/s2g-evaluator-source`
- **Reviewer**: grok (read-only; no repo writes)
- **Date**: 2026-07-19
- **Topic**: `tm-s2g-evaluator-build`
- **Tree at verdict**: pristine

## Verdict

**Clean.** `CapturedRunEvidenceSource` is the production runtime evidence path: seven observability derivations compose promoted existing owners, fail closed on absent bindings/artifacts/rows and on drift findings, C1 run-bound digest bindings are enforced at validation, and the codex `minted:false` treatment is correct PK-adoption semantics, not a facet weakening. HARD constraints hold; no package mint or pointer flip.

## Scope

13 files, +1335 / −33:

| Area | Files |
|------|--------|
| Evidence source | `certification_evidence.py` (new), `test_certification_evidence.py` (new) |
| C1 validator | `certification.py` (`RUN_BOUND_PREDICATE_DIGESTS`, `release_edge_set` public) |
| Mint wiring | `certification_minting.py` (`ScenarioRunBinding`), mint script, minting tests |
| Owner promotions | `drift_capture.detect_unknown_shapes`, `tailer.transcript_drift_spans` |
| Support | `certification_test_support.py`, protocol meta frames + fixture |

## Cross-family focus

### (a) Seven derivations compose existing owners — no duplicate scanners

| Facet / predicate | Owner used |
|-------------------|------------|
| installation_observed | stored `LocalHarnessObservation` (connections store) vs capture facts |
| release_version_matched | `match_release` over as-if-active channel state |
| launch_profile_actuated | `launch_options` / `ResolverSnapshots` + `release_edge_set` |
| authentication_evidence_current | stored access rows (authenticated + freshness) |
| wire_payloads_zero_drift | **promoted** `detect_unknown_shapes` + stored `wire_contract_drift` |
| transcripts_zero_drift | **promoted** `transcript_drift_spans` / `iter_complete_records` + stored transcript drift |
| launch_captured_owned_session | `compatibility_facts` + owned session binding + non-empty index |

Live wire observer now calls the same public `detect_unknown_shapes`. Transcript offline scan uses the one `_plan_ingest_records` loop. No parallel drift path.

### (b) Fail-closed on absent bindings and Postgres rows

- Unbound scenario, missing run dir, missing facts/sessions/exchanges/transcripts → `CertificationMintingError`
- Missing observation / access / target snapshot (edges unenumerable) → refuse
- Observation diverging from capture-time facts → refuse
- Offline wire/transcript findings or same-run stored drift rows → refuse
- Plan without `scenario_bindings` keeps `RealRuntimeEvidencePending` (still fail-closed)

Tests name the failing owner per case (`TestRunDirRefusals`, `TestStoredSnapshotRefusals`, `TestZeroDriftRefusals`).

### (c) Codex `minted:false` is sound

`OwnedSessionFacts.minted` is PK adoption strategy (`True` = native id is session PK for claude; `False` = synthetic PK for codex). Facet 7 requires `native_session_id` + `source_descriptor` only; requiring `minted=True` would falsely fail every codex owned capture. Not a weakening of launch/capture proof.

### (d) HARD constraints

| Constraint | Evidence |
|------------|----------|
| Pointers paused | Embedded channel states remain `"paused"`; no release/manifest JSON in range |
| `COMPATIBILITY_ROLLOUT` advisory | Unchanged `= "advisory"` |
| No mint | No embedded certification records written; as-if-active state is evaluation-only (`model_copy`, never persisted) |

C1: `RUN_BOUND_PREDICATE_DIGESTS` ties wire/transcript/launch_capture predicate digests to the sealed run fields; validator + test support + unit tests pin the binding.

## Notes (non-blocking)

- As-if-active channel state is explicit for pre-flip evaluation; signature intentionally not re-sealed and not published.
- Wire actuation corroboration checks provider + non-empty model on every exchange; full per-edge effort actuation remains the record's edge_refs + resolver enumeration, which matches this slice's observability composition.

## Issues

None (0 bugs, 0 merge-blocking suggestions).

## Authoritative gate

| Gate | Result |
|------|--------|
| `just check` | **exit 0** — desktop typecheck+102; www format/lint/typecheck; api ruff + mypy (646 files) |
| `just test` | **exit 0** — desktop **102**; www **1771** passed; api **3214** passed |

Tree remained pristine after the gate.

## Summary line (bus)

`review: clean; gate: check+test green (api 3214, desktop 102, www 1771) findings: ~/.mdx/projects/transport-matters-pr307-review-grok.md`
