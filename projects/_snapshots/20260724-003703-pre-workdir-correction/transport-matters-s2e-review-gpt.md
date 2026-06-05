# PR #298 adversarial review

Range: `4de2e2131512331f52c2c2e7405653ce56883b60...0320ffd6dfc9514f32e86fb3147eb8d50635f57b`

Verdict: 0 Blocker, 3 Major, 2 Minor.

## Major

1. `api/src/transport_matters/index/adapters/__init__.py:10,55-75`

   Historical dispatch compares recorded revisions with the one current adapter stored for a harness. The registry cannot retain and select r1 after an r2 adapter is registered, and it couples the independently versioned transcript reader and session bootstrap facets to one current instance. Valid r1 runs will become `historical_contract_unsupported` at the first revision advance even if the r1 implementation remains installed. This is revision gating, not the required versioned reader registry. The production registry also remains keyed by unvalidated strings and concrete adapter imports rather than the canonical `HarnessId` descriptor set.

   Code: https://github.com/littleorgans/transport-matters/blob/0320ffd6dfc9514f32e86fb3147eb8d50635f57b/api/src/transport_matters/index/adapters/__init__.py#L54-L75

2. `api/src/transport_matters/harnesses/compatibility_facts.py:155-165`

   The compatibility artifact is documented and contracted as frozen, but every call unconditionally replaces the existing file. A retry with a different release, revision set, executable, or timestamp rewrites the historical dispatch authority. The content derived audit identity then creates a second audit action instead of surfacing the conflict. The idempotency test covers only an identical retry. Accept identical existing facts and reject divergent facts before replacement.

   Code: https://github.com/littleorgans/transport-matters/blob/0320ffd6dfc9514f32e86fb3147eb8d50635f57b/api/src/transport_matters/harnesses/compatibility_facts.py#L155-L165

3. `api/src/transport_matters/harnesses/compatibility_facts.py:228-247`

   The control plane audit projection omits `recorded_revisions`. The approved plan requires release identity, observed version, and adapter revisions in both the run facts and the audit. The durable artifact contains the revisions, but neither the audit details nor its UUID expose them. An operator cannot determine which historical transcript and session contracts governed the run from the audit record.

   Code: https://github.com/littleorgans/transport-matters/blob/0320ffd6dfc9514f32e86fb3147eb8d50635f57b/api/src/transport_matters/harnesses/compatibility_facts.py#L228-L247

## Minor

1. `api/src/transport_matters/harnesses/compatibility_facts.py:207-212`

   `compatibility_facts_dispatch_id()` duplicates the existing control plane audit UUID protocol in `blocks_store._drift_dispatch_id()`: `uuid5(NAMESPACE_URL, "transport-matters:{verb}:{identity}")`. Only the identity payload varies. The repository's DRY rule requires one public audit dispatch identity helper with the variation passed as data.

   New code: https://github.com/littleorgans/transport-matters/blob/0320ffd6dfc9514f32e86fb3147eb8d50635f57b/api/src/transport_matters/harnesses/compatibility_facts.py#L202-L212

   Existing precedent: https://github.com/littleorgans/transport-matters/blob/0320ffd6dfc9514f32e86fb3147eb8d50635f57b/api/src/transport_matters/harnesses/blocks_store.py#L233-L237

2. `api/src/transport_matters/harnesses/compatibility_facts.py:177-199`

   Schema classification runs before model validation. Missing, null, string, zero, and negative `fact_schema_version` values are all reported as `HistoricalContractUnsupported`, although the reader contract says corrupt or invalid documents raise `CompatibilityFactError`. Reserve the unsupported outcome for a well formed positive integer version that this build does not implement. Route malformed version values through typed artifact validation.

   Code: https://github.com/littleorgans/transport-matters/blob/0320ffd6dfc9514f32e86fb3147eb8d50635f57b/api/src/transport_matters/harnesses/compatibility_facts.py#L177-L199

## Code hygiene

- Scope was limited to the 18 changed files. They total 4,124 lines at the PR head. Every file remains below 700 lines; the largest is `session/test_ingest.py` at 654 lines. No changed function crosses about 150 lines.
- Atomic model JSON writing has one public implementation in `storage/disk_helpers.py`. `session_facts.py`, the new compatibility writer, and the storage mixin share it. No private cross module import or third tempfile implementation was added.
- The new compatibility model has a cohesive owner and reuses `RELEASE_REVISION_FIELDS` and `FrozenStringMap`.
- No production writer call, release match call, inventory join, or migration landed in this slice.
- The audit UUID duplication above is the remaining in scope DRY violation.

Craftsmanship verdict: Strong artifact modeling and atomic write consolidation, but the slice is not merge ready because its historical registry cannot retain versioned readers and its frozen fact authority can be rewritten.

Verification note: No tests or gates were run, as required by the shared tree review brief.
