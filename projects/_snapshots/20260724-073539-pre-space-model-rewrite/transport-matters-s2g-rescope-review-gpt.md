# PR #305 adversarial review: S2g seven facet certification rescope

Verdict: **issue**

Reviewed `main..2539089a3da0371248981c8e1c6ff8e764440a91` on `feat/s2g-mint-activation` against the seven observability facet contract. The branch is safely non-activating today, but the activation validator and the evidence owners still admit false certification once real minting is enabled.

## Findings

### High

1. **Facet predicates are not bound to their claimed evidence owners.**

   [`CertificationPredicateResult` and `CertificationRuntimeRun`](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/harnesses/certification.py#L198-L239) accept arbitrary SHA256 shaped predicate digests, empty `run_id`, empty `session_ids`, an empty observed version, and absent wire and transcript evidence digests. [`_resolve_facet_references`](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/harnesses/certification.py#L366-L400) checks only that a scenario contains a passing predicate with an allowed identifier. It never binds that predicate digest to detection, version matching, authentication probe evidence, Tier 1 wire bytes, transcript copies, or an owned launch bundle. A sealed in-memory record with those empty identities and absent drift digests passed `validate_certification_for_release`. The whole-record digest prevents later mutation, but it also seals unproven assertions. Activation needs owner-specific structural requirements and deterministic digest derivation for every predicate.

2. **Model and effort edge coverage can be supplied by an unrelated facet.**

   [`_validate_edge_coverage`](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/harnesses/certification.py#L415-L429) unions `edge_refs` from all seven facets. The publishing contract assigns every supported edge to the [launch profile facet](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/COMPATIBILITY-PUBLISHING.md#L47-L49). A direct validation probe moved every edge from `launch_profile_resolved` to `harness_installed`; the sealed record still activated. Require the launch profile facet to equal the release edge set, and reject edge references on facets that do not own them.

3. **Codex wire zero drift cannot detect new fields inside input items.**

   The new facet promises to re-run the existing S2d scanners over owned bytes. [`unknown_request_fields`](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/codex/request_parser.py#L82-L88) inspects only top-level `provider_extras`. Unknown per-item keys merely set `keep_raw` in [`_parse_message_item`](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/codex/request_parser.py#L211-L243), so they remain invisible to the drift predicate. The active plan already records this [known detector gap](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/RUNTIME-SURFACING-S2-PLAN.md#L199-L202). Close the item vocabulary before `wire_payloads_zero_drift` can mint.

4. **Transcript zero drift silently accepts unknown or malformed records.**

   [`ClaudeAdapter.normalize`](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/index/adapters/claude.py#L113-L138) returns `None` for unknown record types or records without a string UUID. [`CodexAdapter.normalize`](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/index/adapters/codex.py#L119-L155) does the same for non-dict payloads and unknown record or event types. The [tailer advances and commits these records](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/index/tailer.py#L223-L257), while its drift hook covers commit failures and locator divergence. A new provider record can therefore be treated as an ordinary meta skip and still satisfy a zero drift assertion. Certification needs a closed allowlist for intentional meta records and must classify every other skipped record as transcript drift.

### Medium

5. **The committed-bytes guarantee accepts ignored files and symlinks outside the repository.**

   Suite selectors need only [`Path.exists()`](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/harnesses/certification_minting.py#L216-L239). Fixture expansion follows any [`glob` match for which `is_file()` succeeds](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/harnesses/certification_minting.py#L327-L340). The cleanliness check uses [`git status --untracked-files=all`](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/harnesses/certification_minting.py#L360-L392), which omits ignored files. A plan can therefore execute or hash ignored bytes, or follow a repository symlink to external bytes, while attributing the result to `HEAD`. Resolve every selected path within the repository and require it to be a tracked regular file at the pinned revision.

6. **Production reproduction is defeated by the fresh certification timestamp.**

   The CLI supplies [`datetime.now()`](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/scripts/mint_harness_certification_record.py#L48-L64), `certified_at` is part of the record, and [`certification_digest` hashes the whole record](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/harnesses/certification.py#L361-L363). The [reproduction comparison](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/harnesses/certification_minting.py#L536-L545) can match only if the new timestamp equals the timestamp sealed into the release. Tests hide the defect by reusing one fixed timestamp. Reproduction needs a stable recorded instant or a digest that excludes mint metadata.

7. **The successor instruction deletes the predecessor from the manifest history.**

   The CLI tells the publisher to [replace the release](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/scripts/mint_harness_certification_record.py#L73-L82). The publishing contract requires a [new immutable compatibility release](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/COMPATIBILITY-PUBLISHING.md#L51-L60). Append the derived successor and move the pointers. Removing the predecessor erases the immutable audit lineage and can invalidate historical facts that cite it.

8. **The governing compatibility contract still requires the retired behavioral matrix.**

   The rescope says certification never asserts harness feature behavior, while the governing contract says certification covers [launch behavior, session bootstrap, project layout, and runtime home behavior](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/HARNESS-COMPATIBILITY.md#L7-L10). Its activation gates still require [prompt-free and prompted launches, second turns, tools, resume, shutdown, project and home coverage, and Grok parity](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/HARNESS-COMPATIBILITY.md#L669-L687). The exact old facet identifiers are retired, but the authoritative behavioral obligations remain. Update the governing contract in the same change so publication has one coherent authority.

9. **The suite environment re-enables ambient pytest plugins.**

   The runner claims a controlled environment, but [`_suite_environment`](https://github.com/littleorgans/transport-matters/blob/2539089a3da0371248981c8e1c6ff8e764440a91/api/src/transport_matters/harnesses/certification_minting.py#L81-L96) removes `PYTEST_DISABLE_PLUGIN_AUTOLOAD` from the inherited environment. This turns plugin autoload back on. An ambient plugin can alter collection, deselect intended cases, or manufacture report behavior while the JUnit check still sees at least one execution. Force plugin autoload off and explicitly load the closed plugin set required by each suite.

## Confirmed invariants

- The exact 13 retired facet and predicate identifiers are absent from the repository.
- The seven facets are required and `DECLARABLE_FACETS` is empty.
- Plans contain evidence references and cannot supply outcome fields.
- JUnit evidence rejects missing reports, failures, errors, all-skipped selections, and zero executions.
- The worktree and `HEAD` are checked before collection and before write.
- Record creation uses one atomic no-replace write, so concurrent writers cannot overwrite a record.
- Activation and explicit verification call the same `validate_certification_for_release` gate.
- No certification records ship in this branch. Stable and preview pointers for Claude and Codex remain paused. Compatibility enforcement remains advisory.
- `RealRuntimeEvidencePending` intentionally fails closed. The production CLI cannot mint a runtime-backed record until the seven real evaluators exist. This is a correct safety boundary.
- Existing canonicalization, atomic I/O, path validation, drift capture, transcript tailer, and compatibility store owners are reused. No parallel substrate was introduced.
- All new production files remain below the repository's 700 line threshold.

## Verification

- Branch and head: `feat/s2g-mint-activation` at `2539089a3da0371248981c8e1c6ff8e764440a91`.
- Base: `main` at `04300cf26f441155e09c88b08a5421163b968e22`.
- `git diff --check main..2539089a`: clean.
- Focused certification tests: 87 passed.
- Broad local gate requested by the reviewer, `just check && just test-affected`: user confirmed green. GitHub Actions were excluded by instruction.
- Repository status before and after report: clean, with no tracked, staged, or untracked changes.

Finding count: 9 total, 4 high and 5 medium.
