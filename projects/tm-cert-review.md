# Certification fabrication review

Reviewed `0709d1ae8f61cd3e1222781d2eaa8899f0ffca55` against `84d2c66d7bd048e36cadf6e2ac91cc5a48d9f16d` in a clean detached worktree.

## P1: The patch rewrites an immutable certification identity in place

Location: `api/src/transport_matters/harnesses/compatibility_releases_v1.json` release `codex-0.144.4-r2`; `api/src/transport_matters/harnesses/certification_records_v1/codex-0.144.4-r2.json`; `certification_minting.py` symbols `mint_outcome` and `write_record_once`.

The same release ID now names a different target set, release digest, evidence digest, and certification record. The record still says it was minted from Transport Matters revision `78fe70d2cbf77569cb9e3a291de93b805d8a5876` at `2026-07-18T22:29:41.458112Z`. A mint at reviewed head `0709d1ae` would record that head, fail reproduction against the old record, derive `codex-0.144.4-r3`, and refuse to overwrite the existing r2 file. The checked in replacement therefore did not come from the new mint path.

Impact: historical runs and references to r2 cannot distinguish the original six-edge artifact from the replacement one. More directly, the active embedded trust root has bypassed the gate this patch adds. Internal digest consistency only proves that the edited files agree with each other.

The repository contract calls records immutable, requires changed evidence to receive a new release ID, and provides `write_record_once` to enforce that rule. Pre-release status limits distribution risk but does not restore provenance.

## P2: Enumeration is not bound to the certified harness version

Location: `api/scripts/mint_harness_certification_record.py` symbol `_live_enumeration`.

The script resolves whichever `codex` or `claude` appears first on the operator's current `PATH`. It does not inspect that binary's version, compare it with `MintPlan.baseline_version`, or bind it to the executable and version in the captured run. On this machine it enumerated Codex `0.146.0` while the record certifies Codex `0.144.4`.

Impact: a model added only in a newer CLI can certify an older release, while a model removed from a newer CLI can invalidate an honest older edge. The gate would have caught `gpt-5-codex` in the #308 workflow only if the PATH binary were the same Codex 0.144.4 build whose run was certified. #293 itself authored a paused manifest before any mint, so a mint gate could not prevent that authorship.

## P2: Enumeration evidence is transient and unauditable

Location: `certification_minting.py` symbols `require_edges_in_enumeration` and `_assemble_record`; `certification.py` model `CertificationRecordV1` and validator `validate_certification_for_release`.

The enumerated model set, probe revision, executable identity, harness version, and an evidence digest are discarded after an in-memory subset check. None is sealed into `CertificationRecordV1` or checked during activation. The replacement record and release digests can be reproduced from the edited JSON alone, without enumeration evidence.

Impact: activation and later review cannot distinguish a record produced by independent enumeration from a manually narrowed and resealed record. Package integrity prevents an untrusted runtime edit, but cannot prove publisher derivation.

## P2: Credential free enumeration inherits ambient credential tokens

Location: `api/scripts/mint_harness_certification_record.py` symbol `_live_enumeration`; `model_enumeration.py` symbol `run_model_enumeration_probe`; `environment.py` symbol `probe_environment`.

`_live_enumeration` passes `os.environ` into the model enumeration runner. The runner calls `probe_environment` with `home_dir=None`. In that mode, the helper removes harness home variables but preserves credential variables such as `CODEX_ACCESS_TOKEN`, `CODEX_API_KEY`, and `OPENAI_API_KEY`. The certification documentation describes enumeration as credential free, yet the publisher path gives the probed executable ambient tokens it does not need.

No credential disclosure was observed. The runner behavior predates this branch, but this branch newly makes its result a certification prerequisite and invokes it from the publisher path.

## Verified facts

- The official fail-closed path is complete. Missing adapter or binary raises. Probe failure, timeout, nonzero exit, and parser drift return no enumeration, which `_live_enumeration` converts to `CertificationMintingError`; `main` returns status 1. Direct absent or empty enumeration also fails before suites in `require_edges_in_enumeration`.
- The new fabricated-model test passes at the reviewed head. A controlled run against the parent implementation minted a successor record carrying the fabricated `gpt-5-codex` model and its four efforts, proving the prior behavioral hole.
- Manifest, plan, and record now agree on the sole edge `codex.chatgpt.oauth / gpt-5.6-sol / null`. Certification, fixture-set, and release digests recompute, and activation validation passes.
- Live Codex 0.146.0 enumeration listed `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, and `gpt-5.2`. `gpt-5-codex` is absent. `gpt-5.4-mini` exists only as `visibility: hide` in the raw bundled catalog, and the production parser correctly excludes it. Because the probe is not version bound, this does not prove the catalog of Codex 0.144.4.
- Every removed catalog target carried `support_tier: observed_unverified`. No `tested` edge was removed.
- Focused branch verification: 34 tests passed across the enumeration gate, shipped mint plans, embedded manifest, and activation gate. `--verify-activation codex-0.144.4-r2` passed. The first attempted test command was discarded because the shared editable environment imported the main checkout; the rerun pinned the detached `api/src` and collected the intended tests.
