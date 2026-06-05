# PR #303 review: S2g PR1 certification substrate

Verdict: issue. One medium finding and one minor finding.

Scope: `main..feat/s2g-certification-substrate`

- Base: `1f9c13175ace3de434956783d8c0738d65ace384`
- Head: `808835ec2db6ddcaa0339a1d3609cf458d94a4fb`
- Reviewed tree: local clean `main`; branch inspected through committed git objects

## Findings

### Medium: invalid UTF 8 record data escapes the packaging defect exception boundary

`embedded_certification_record()` reads a record as UTF 8 at `api/src/transport_matters/harnesses/certification.py:464-471`, but the read block catches only `FileNotFoundError` and `OSError`. Invalid UTF 8 raises `UnicodeDecodeError`, which is not an `OSError`. `_require_certified_active_pointers()` at `api/src/transport_matters/harnesses/compatibility_store.py:245-259` catches only `CertificationValidationError`, so this corrupt record path reaches callers as `UnicodeDecodeError` instead of the promised `CompatibilityDataError`.

This does not bypass certification. It still fails hard. It does violate the single packaging defect error contract for a corrupt embedded record, which was the prior medium finding this revision claims to close.

The regression at `api/src/transport_matters/harnesses/test_compatibility_store.py:344-360` injects a loader that already raises `CertificationValidationError`. It therefore proves the outer conversion only and does not exercise the loader exception that previously leaked. A read only behavioral probe against the committed branch implementation returned `UnicodeDecodeError` from an injected `Traversable.read_text()` decode failure.

Suggested correction: map `UnicodeDecodeError` or `UnicodeError` to `CertificationValidationError` in the embedded loader, then add an end to end gate test using an invalid UTF 8 record resource and assert `CompatibilityDataError`.

### Minor: `certified_at` does not enforce the specified RFC3339 UTC shape

The fixed spec defines `certified_at` as RFC3339 UTC. `CertificationRecordV1.certified_at` is an unrestricted `str` at `api/src/transport_matters/harnesses/certification.py:263-283`; the identity validator checks only the git revision. A record with a malformed or non UTC timestamp can therefore construct, receive a matching canonical digest, and pass activation.

Suggested correction: validate a timezone aware RFC3339 instant normalized to UTC, and add malformed, offset, and naive timestamp rejection tests.

## Verified behavior

- The facet vocabulary is closed by a 13 value `Literal`, a 13 item tuple, and a matching predicate map. Predicate ids are also a closed `Literal`.
- Every facet is required exactly once. Duplicate and missing facets fail. Outcomes are constrained to `passed`; only `approval_structured_input` may be declared unsupported.
- Fixture files carry repository relative paths and SHA 256 values. Fixture set digests sort path and hash pairs before canonical hashing.
- The activation gate is on `embedded_compatibility_manifest()` and validates every active pointer against a package record, the pointed release identity, both digest bindings, evidence references, and complete route, model, and effort coverage.
- Missing records and validation mismatches map to `CompatibilityDataError`. JSON and Pydantic corruption map correctly. The invalid UTF 8 read path above remains uncovered.
- All four committed pointers remain `paused`, so the new record loader is never invoked for the shipped manifest. The current runtime path is vacuously inert.
- Canonical digest behavior was exercised from the committed branch without filesystem writes. Rebuilding the same record produced the same digest. Independent facet, fixture, and predicate mutations each changed the digest and were rejected by `validate_certification_for_release()` against the sealed release.
- The audit test constructs a compatible launch decision and facts artifact, removes required runtime proof, and confirms validation still fails. The production certification validator accepts no audit input.
- `COMPATIBILITY_ROLLOUT` remains `advisory`; the added pin test fixes that build property for this slice.
- The five reported self review minors are present: nonempty fixture references, empty and unsafe fixture path rejection, release id path segment rejection, removal of the dead constant, and compliant module wording.

## Verification state

- `git diff --check`: clean.
- Repository status after read only probes: `## main...origin/main`, no tracked or untracked changes.
- GitHub CI did not execute. Every primary job has zero steps and a billing or spending limit annotation. The red checks provide no code signal.
- The PR body reports `just check` clean and `just test-affected` with 2,893 passing tests. Those suites were not rerun during this read only review.
