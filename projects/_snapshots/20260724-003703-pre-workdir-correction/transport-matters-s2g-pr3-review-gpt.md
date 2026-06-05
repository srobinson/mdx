# PR #305 review: S2g PR3 mint and activation tooling

Verdict: **issue**, 5 findings. Top severity: **medium**.

Reviewed `main..feat/s2g-mint-activation` at:

- Base: `04300cf26f441155e09c88b08a5421163b968e22`
- Head: `d6b141dc32302b54bba2dc1de55e501016c67cd0`
- PR: <https://github.com/littleorgans/transport-matters/pull/305>

## Findings

### 1. Medium: inherited pytest options can mint a passing suite without executing tests

[`run_planned_suites`](https://github.com/littleorgans/transport-matters/blob/d6b141dc32302b54bba2dc1de55e501016c67cd0/api/src/transport_matters/harnesses/certification_minting.py#L199-L218) invokes the closed argv without a controlled environment and treats every zero return code as `outcome="passed"`. Pytest reads `PYTEST_ADDOPTS` from the inherited environment. A focused reproduction set `PYTEST_ADDOPTS='--collect-only -p no:cacheprovider'`; pytest collected all 12 selected tests, executed none, exited 0, and this function returned:

```text
(CertificationSuiteResult(suite_id='proof', ..., outcome='passed'),)
```

Once the real runtime source replaces the current fail-closed placeholder, this is a direct no-test pass path into a mintable and activatable record. The current pending runtime source limits immediate impact but does not make the later machinery sound.

Run suites under a controlled per-kind environment and prove actual execution rather than process success alone. At minimum remove option and plugin injection variables. Prefer a machine-readable result that requires the selected tests to execute with no failures, errors, or collection-only mode. Add the environment reproduction as a red-before test.

### 2. Medium: the recorded git revision is not bound to the code that the suites execute

[`_mint`](https://github.com/littleorgans/transport-matters/blob/d6b141dc32302b54bba2dc1de55e501016c67cd0/api/scripts/mint_harness_certification_record.py#L48-L69) records `git rev-parse HEAD` but never requires a clean worktree or confirms that HEAD and the tree remain stable through suite and evidence collection. The subprocesses execute the live checkout. A developer can therefore change a test, adapter, or future runtime predicate implementation without committing it, mint against those bytes, and produce a record that attributes the result to the unchanged HEAD SHA. Fixture hashing covers only the plan's cited files and does not detect pre-existing dirty source.

Require a clean tracked and untracked tree plus a stable HEAD before evidence collection, then recheck both immediately before the record write. An isolated checkout at the recorded revision would make the binding stronger. Add a dirty-test-source rejection case.

### 3. Medium: the write-once record operation has an exists-then-write race

[`write_record_once`](https://github.com/littleorgans/transport-matters/blob/d6b141dc32302b54bba2dc1de55e501016c67cd0/api/src/transport_matters/harnesses/certification_minting.py#L419-L429) checks `path.exists()` and then opens the same path through `write_text`. Two mint processes can both observe absence and both truncate/write the record, so the last writer wins. A crash can also expose a partial final file. The sequential test does not exercise either boundary.

Use one atomic no-replace filesystem operation and share the repository's atomic I/O machinery rather than adding another write pattern. Add a concurrent writer test proving exactly one success and a complete surviving document.

### 4. Minor: the plan still declares each facet's passing outcome

The [`MintPlan.facets`](https://github.com/littleorgans/transport-matters/blob/d6b141dc32302b54bba2dc1de55e501016c67cd0/api/src/transport_matters/harnesses/certification_minting.py#L95-L110) field accepts full `CertificationFacet` objects. That model includes `outcome: Literal["passed"]`, so every plan JSON must supply a passing facet status despite the adjacent contract saying facets carry references only and outcomes are derived.

The activation validator still requires resolvable suite and runtime references, so this field alone cannot bypass evidence. It nevertheless violates the no-status input contract. Define a plan-specific facet reference model without `outcome`, then construct the record facet after its cited results have passed.

### 5. Minor: the new path guard duplicates the existing certification guard

[`_require_repo_relative_pattern`](https://github.com/littleorgans/transport-matters/blob/d6b141dc32302b54bba2dc1de55e501016c67cd0/api/src/transport_matters/harnesses/certification_minting.py#L146-L150) reimplements the same absolute and upward-traversal policy already owned by [`certification._require_repo_relative`](https://github.com/littleorgans/transport-matters/blob/d6b141dc32302b54bba2dc1de55e501016c67cd0/api/src/transport_matters/harnesses/certification.py#L152-L160), with divergent empty and tilde handling. Avoiding a private import is correct, but copying the guard conflicts with the repository's zero-duplication rule.

Promote one public repo-relative path validator and let both record and minting models share it, with error context supplied by the caller.

## Verified behavior

- Suite kinds use closed argv. Pytest runs from `api/`; vitest runs from the selector's `packages/<name>` or `www/packages/<name>` root. Every selector is rewritten relative to that root and must exist. Absolute and `..` selectors are rejected.
- Fixture patterns expand to sorted exact files. The same set is hashed before and after all suites; changed, added, removed, or unmatched cited fixtures refuse the mint.
- `RealRuntimeEvidencePending.collect` raises unconditionally. The production CLI always installs that source, so this PR cannot mint a record from synthetic runtime claims.
- `mint_outcome` assembles the record, derives reproduction from the actual certification and fixture digests, rebuilds successor release and target models through validation, recomputes the successor release digest, and runs `validate_certification_for_release` before returning an outcome.
- `--verify-activation` calls the same `validate_certification_for_release` function used by the embedded active-pointer gate.
- The manifest and rollout files are absent from the diff. Stable and preview pointers for Claude and Codex remain paused. `COMPATIBILITY_ROLLOUT` remains `"advisory"`.
- All three new files remain below the repository size threshold.

## Checks

- `git diff --check main..feat/s2g-mint-activation`: pass.
- The 12 new minting tests plus the two paused-pointer pins and advisory-rollout pin: 15 passed in 0.08 seconds.
- Focused no-test reproduction: pytest collected 12 and executed zero under `PYTEST_ADDOPTS=--collect-only`; `run_planned_suites` returned a passing suite result.
- GitHub Actions jobs did not start. The backend check annotation reports failed account payments or a spending-limit condition, so CI provides no code evidence.
- Repository writes by this reviewer: zero. The only authorized write is this external report.
