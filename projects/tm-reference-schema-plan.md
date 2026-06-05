---
title: Transport Matters Release Reference Schema Plan
type: projects
tags: [transport-matters, harnesses, compatibility, certification, baseline, request-schema, scout, plan]
summary: Reuse map and implementation plan for shipping a per-model reference request schema with each blessed harness range
status: active
project: transport-matters
confidence: high
created: 2026-08-23
updated: 2026-08-23
---

# Transport Matters Release Reference Schema Plan

## Inspection boundary

Source was inspected at `d4ce12a5a398fe841c5e1ac64bac713320f01c4a` on `main`. `CLAUDE.md` is a symlink to the pre-existing modified `TLDR.md`; this pass read those additions and did not touch them. No repository file, store, backend, provider, or process was changed.

Labels mean:

- **ESTABLISHED**: proved by current source or a measured artifact named below.
- **INFERRED**: recommended design derived from that evidence.

This plan covers release authoring, package data, certification binding, comparison semantics, and the verdict storage seam. Building the feature, deriving support state in the live launch path, and triggering comparison on launch remain outside this pass.

## Decision

- **Reference source:** existing controlled baseline machinery. `GateProjection.request_schema` is already derived from exact A/B/A request bytes and carries the evidence hashes and source identity needed for certification.
- **Granularity:** one logical reference per launched model. Protocol classes remain a derived report view. The measured package cost is about 110 KB for all 16 cells, about 7 KB per cell.
- **Range:** ship an explicit top version and require every reference schema to have been observed at that version. Until broader equality is proved, the honest blessed range is one version: `minimum_version == baseline_version == maximum_version`.
- **Current live run requirement:** yes. Existing sealed records contain one-way digests, their bound run directories are absent, and no current channel home contains baseline bundles. Retained immutable baseline bundles would remove the need for a new provider turn in a future mint.
- **Verdict home:** a content-addressed verdict projection under the active channel's baseline store. The immutable bundle and signed release remain the authority. Postgres does not need a new source of derived truth for the first slice.

## Reuse Map

### 1. The blessed range already has one owner

**ESTABLISHED**

`api/src/transport_matters/harnesses/compatibility.py:HarnessCompatibilityRelease` already declares `baseline_version`, `minimum_version`, and optional `maximum_version`. `_validate_version_range` enforces `minimum <= baseline <= maximum`. `blessed_ceiling` uses `maximum_version` or conservatively falls back to `baseline_version`. `range_position` distinguishes below floor, inside, at ceiling, and above ceiling. `match_release` keeps above-ceiling launches available and marks them for best effort verification.

The embedded releases currently say:

| harness | baseline | floor | declared ceiling | effective ceiling |
| --- | --- | --- | --- | --- |
| Claude | 2.1.211 | 2.1.211 | absent | 2.1.211 |
| Codex | 0.144.4 | 0.144.4 | absent | 0.144.4 |
| Grok | 1.0.4 | 1.0.4 | 1.0.4 | 1.0.4 |

`api/src/transport_matters/harnesses/certification_evidence.py:CapturedRunEvidenceSource._check_version` accepts any observed version from the floor through the effective ceiling. `api/src/transport_matters/harnesses/certification_minting.py:successor_entry` preserves the existing range. No production function derives or widens it.

**INFERRED**

Keep these range fields. A release author supplies the floor and top. The certification gate must prove that every shipped reference was observed at `blessed_ceiling(release)`. A first release should use a one-version range. A later release may lower the floor or raise the ceiling only from explicit comparison evidence covering the claimed interval. Range production belongs to release authoring, never to target discovery or lazy launch verification.

### 2. Request schema inference already exists

**ESTABLISHED**

`api/src/transport_matters/request_schema.py:mint_request_schema` derives `RequestSchema` from a provider profile and exact raw request bytes. `compare_request_schema` performs a directed reference-to-candidate comparison.

The controlled baseline chain already supplies the full input and provenance:

1. `api/src/transport_matters/baseline_capture.py:harvest_controlled_baseline` captures A/B/A for one launched model.
2. `api/src/transport_matters/baseline_evidence.py:BaselineBundle` retains the exact raw request evidence.
3. `api/src/transport_matters/baseline_projection.py:project_baseline` chooses the provider profile and calls `mint_request_schema` over all three requests.
4. `api/src/transport_matters/baseline_projection.py:GateProjection` carries the schema, bundle ID, source identity, three request hashes, cell coordinates, and deriver digest.
5. `api/src/transport_matters/baseline_projection_store.py:read_current_gate_projections` reads the published projection or re-derives it from the immutable bundle.

Measured evidence in `~/.mdx/projects/tm-cleanup-scout-artifact.md` places `request_schema` plus cohort coordinates at 114,865 bytes for 16 cells, 7.2 KB per cell. The current channel homes contain no `baselines` directory, so this measurement is historical rather than a claim about a live store today.

**INFERRED**

Use the gate projection as release-authoring input. Introduce no second schema minter, schema digest definition, or provider-specific inference path. The mint plan should bind immutable bundle references rather than mutable current pointers. Authoring re-derives each projection from its bundle, then records the bundle ID, source identity, request hashes, and deriver digest in certification evidence.

### 3. Certification currently discards the needed output

**ESTABLISHED**

`api/src/transport_matters/harnesses/certification_run_reader.py:CapturedExchange` holds `request_raw`, validated request IR, response bytes, and transport bytes. `api/src/transport_matters/harnesses/certification_evidence.py:CapturedRunEvidenceSource.collect` reads those exchanges, validates them, and reduces them to five digests.

The sealed outputs contain no request schema:

- `api/src/transport_matters/harnesses/certification.py:CertificationRuntimeRun` stores IDs, observed version, five evidence digests, and predicate results.
- `api/src/transport_matters/harnesses/certification.py:CertificationRecordV1` stores fixtures, suites, runtime runs, and seven facets.
- `api/src/transport_matters/harnesses/certification_minting.py:MintOutcome` returns the record, release entry, and reproduction flag.

Each embedded record has one runtime run and seven facets. None has a schema field. The `wire_evidence_digest` and request hashes are one-way, so package consumers cannot reconstruct a schema. The shipped Claude and Codex mint plans point to run directories that no longer exist. The current certification record also proves release edge membership, while one scenario does not prove one schema per launched model or effort.

**INFERRED**

Add a reference evidence collection to the next certification record schema. Each item should bind a release reference key to:

- immutable baseline bundle ID;
- observed harness version;
- source identity and deriver digest;
- the three raw request hashes;
- the canonical digest of the resulting `RequestSchema`.

`validate_certification_for_release` should require exact key and digest equality between certification evidence and the release payload. This closes the current gap where a hand-edited release can be resealed without evidence that the shipped schema came from the cited capture.

The change is a certification record schema break. Use a single v2 record path and migrate the three embedded releases together. A parallel v1 and v2 authoring path would create duplicate activation rules.

### 4. Minimal release payload

**ESTABLISHED**

`api/src/transport_matters/harnesses/compatibility.py:CompatibilityReleaseEntry` currently contains only the release, routes, and targets. `release_digest_payload` covers those three collections. `api/src/transport_matters/harnesses/compatibility_store.py:_require_digest_integrity` recomputes the digest, and `_require_certified_active_pointers` requires an exact embedded certification record before activation.

`HarnessCompatibilityRelease.schema_digests` contains three harness-level opaque digests for wire request, wire response, and transcript. It neither carries a schema nor distinguishes launched models.

**INFERRED**

Add a required `request_schema_references` collection to `HarnessCompatibilityRelease`. Define its pure vocabulary in a new small module, for example `harnesses/release_reference.py`, because `compatibility.py` is already 649 lines. Keeping the collection inside the release makes `release_digest_payload` and `successor_entry` cover and preserve it through their existing whole-release dumps. `CompatibilityReleaseEntry` should perform the cross-reference checks against routes and targets.

One reference should minimally contain:

| field | purpose |
| --- | --- |
| `route_id` and `provider_id` | select the transport contract used by the launch |
| `launch_model_id` | retain the native model or alias the operator launched |
| `canonical_model_id` | bind the native launch identity to the release compatibility edge |
| `effort` | state which concrete launch tuple produced the schema; nullable where effort is absent |
| `observed_harness_version` | prove the schema came from the blessed top |
| `request_schema` | the self-contained reference used at runtime |
| `request_schema_digest` | stable provenance key for verdict invalidation; validate it against the canonical schema payload |

Entry validation should require unique `(route_id, launch_model_id, effort)` keys, existing route and canonical target references, a valid provider profile, and `observed_harness_version == blessed_ceiling(release)`. Certification validation should require complete coverage of the baseline cohort selected by the mint plan.

The current `RequestSchema` and `RequestSchemaNode` models are frozen but allow unknown fields and contain mutable nested dictionaries. Harden the existing schema owner for strict parsing and deep immutability before placing it inside signed release data. This keeps one semantic model while meeting the release package's executable-content standard.

Bump the embedded manifest contract and filename to v2 because older readers use strict models and cannot interpret the new required collection. Do not overload the existing harness-level `schema_digests` map with per-model payloads.

### 5. Per model wins over protocol class

**ESTABLISHED**

`api/src/transport_matters/baseline_comparison.py:fold_model_equivalence_classes` already computes classes from the complete pair set and verifies transitivity. The class is an ephemeral report value. It is absent from release and certification data.

The measured 16-cell cohort at source `03dc8d62` folded into five protocol classes:

```text
claude  {best, default, fable, fable[1m], opus, opus[1m], opusplan, sonnet, sonnet[1m]} | {haiku}
codex   {gpt-5.5} | {gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra}
grok    {grok-4.5, grok-4.6}
```

Claude therefore has ten aliases and two structural classes. The historical analysis in `~/.mdx/projects/tm-model-identity-scout-baseline.md` also proves why the alias remains the durable key: an alias can repoint to another protocol generation. If storage were keyed by the newly derived class, that change would miss its old reference and bootstrap as current.

**INFERRED**

Ship one logical reference per launched model. Full duplication costs about 110 KB across all measured cells and avoids durable class membership, representative selection, and alias repoint invalidation. `fold_model_equivalence_classes` remains useful for authoring diagnostics and for collapsing repeated operator findings. It should not define release identity.

Physical content deduplication can wait until package size justifies it. If later added, every model still needs an explicit logical reference to a content-addressed schema. A class name must never replace the model key.

One unresolved coordinate needs proof before implementation: `VerificationCell` includes effort, while `BaselineCell` and its store key omit it. The release reference should record the selected effort. A focused evidence pass must prove schema invariance across accepted efforts or expand logical coverage to model and effort. The current certification record cannot prove that fact.

### 6. Authoritative comparison needs a separate support projection

**ESTABLISHED**

`api/src/transport_matters/request_schema.py:compare_request_schema` is directed. Candidate-added object properties produce a `DEGRADED` drift finding. Candidate-removed properties produce a `BREAKING` drift finding. These are `DriftOutcome` values for one comparison.

`api/src/transport_matters/baseline_comparison.py:compare_model_pair` runs both directions and folds the two reports to their worst outcome. That is correct for peer equivalence and is the wrong production entry for a candidate judged against an authoritative release reference.

`CLAUDE.md:Support state and its cause are separate keys` requires:

- missing reference properties: support state `degraded`;
- additional candidate properties: support state remains `blessed`, with findings;
- no findings: `blessed`.

`StructureFinding` has a pointer, branch tag, prose reason, and optional drift outcome. It has no typed change kind. Parsing its prose would create a second hidden contract.

**INFERRED**

Keep `compare_request_schema` as the one structural comparison engine. Give each `StructureFinding` a typed direction or change kind at its existing creation sites. Add a small pure support projection that consumes the directed report and returns separate fields:

```text
state: blessed | degraded
findings:
  missingProperties: [...]
  additionalProperties: [...]
```

The support projection must ignore the pairwise worst fold. A rename naturally produces one missing and one additional pointer and therefore degrades. Candidate expansion records an additional pointer while remaining blessed. Any reference contraction that cannot be represented by the typed vocabulary must fail a test or map conservatively to missing evidence; it must never disappear through a prose match.

### 7. Digest and live evidence constraints

**ESTABLISHED**

`api/src/transport_matters/harnesses/compatibility.py:compute_release_digest` hashes `release_digest_payload`. `api/src/transport_matters/harnesses/certification.py:certification_digest` hashes the full record. `validate_certification_for_release` requires the record fixture digest and certification digest to equal the release fields. `reproduction_digest` excludes only mint time.

`api/scripts/reseal_compatibility_manifest.py` can recompute a self-consistent release digest after a manual edit. That proves package integrity, not schema provenance. `api/scripts/mint_harness_certification_record.py` consumes persisted run directories and database snapshots; it launches no provider itself. A plan without scenario bindings fails closed through `RealRuntimeEvidencePending`.

The current package cannot backfill references. The records retain only digests, both shipped plan run directories are absent, and stable, preview, and dev homes have no baseline store. A fresh complete baseline cohort is therefore required for the first v2 release.

**INFERRED**

Bind four layers:

1. The release digest covers the complete model reference payload.
2. Each reference validates its canonical schema digest.
3. The certification record covers immutable baseline provenance and those schema digests.
4. Activation requires exact release-to-record reference key and digest equality.

After v2 lands, a retained immutable baseline bundle can support offline re-minting without another provider turn. A newly observed top version or a missing model cell still requires live capture.

### 8. Persistent verdict home

**ESTABLISHED**

Channels use separate Postgres databases and separate homes. The baseline pipeline currently persists all of its evidence and retry lifecycle beneath `<channel home>/baselines`: immutable bundles, content-addressed projections, current pointers, and attempts. `api/src/transport_matters/baseline_projection_store.py:read_gate_projection` already applies the house rule for derived state: a changed deriver or missing projection becomes a cache miss and the immutable bundle is re-read.

No Postgres table owns baseline bundles, projections, attempts, request schemas, or support verdicts. `harness_drift_evidence` owns lower-level events and cannot represent `blessed` with no finding. A current pointer can move, so it is an unstable key for a version support decision. `BaselineCaptureAttempt` also records success without the bundle ID it produced, while several immutable bundles may exist for one version.

**INFERRED**

Persist a typed support verdict artifact under the active channel home, for example:

```text
<channel home>/baselines/verdicts/<release digest>/<bundle store tail>.json
```

Address and validate it with:

```text
release_id
release_digest
route_id
launch_model_id
effort
normalized_harness_version
reference_schema_digest
candidate_bundle_id
candidate_schema_digest
support_deriver_digest
```

Store `state`, `missing_properties`, and `additional_properties` as separate fields. A new release, reference schema, candidate bundle, or support policy yields another address or a cache miss. Re-derivation reads the signed release and immutable bundle, following the existing gate projection pattern.

Add the successful bundle ID to `BaselineCaptureAttempt`, or add an equivalent version-specific result pointer, so later readers select the exact candidate without scanning several immutable bundles. A Postgres representation may later serve as a disposable query cache keyed by the same digests. It should not become the authority.

## Quality Map

### Measurements

| production file | LOC | assessment |
| --- | ---: | --- |
| `harnesses/certification_evidence.py` | 669 | 31 lines from the hard limit; extract before adding schema duties |
| `baseline_evidence.py` | 657 | 43 lines from the hard limit; keep release vocabulary elsewhere |
| `harnesses/compatibility.py` | 649 | 51 lines from the hard limit; add only a field import and validators after extracting vocabulary |
| `harnesses/certification_minting.py` | 611 | keep orchestration; move reference collection to an adapter |
| `harnesses/certification.py` | 605 | keep record composition and activation validation |
| `launch_verification.py` | 601 | launch trigger remains outside this slice |
| `request_schema.py` | 584 | existing comparison core; typed finding change fits here |
| `harnesses/connections_store.py` | 534 | avoid growing it with support verdict SQL; use a focused store |

No relevant function exceeds 150 lines. `LaunchVerificationCoordinator._verify_under_lock` is 141 lines and remains outside this release-authoring slice.

### Duplication

**ESTABLISHED**

The structural duplicate scan found no competing request-schema minter or release digest owner. It did flag the argparse shells in `baseline_compare.py:main` and `baseline_publish.py:main` as a 0.945 similarity pair.

**INFERRED**

Avoid a third copied argparse shell for release authoring. Extend the existing certification operator script or extract one shared operator command boundary. Reuse `mint_request_schema`, `project_baseline`, `read_current_gate_projections`, `canonical_digest`, and `compute_release_digest` directly.

### Boundaries

- Package release data owns the blessed range and immutable references.
- Baseline bundles own raw provider evidence.
- Gate projections own recomputable comparison input.
- Certification records own provenance and activation proof.
- The channel baseline store owns a disposable support verdict projection.
- The support projection owns product state semantics. `DriftOutcome` remains comparison semantics.

The new release reference vocabulary should be pure and must not import storage, Postgres, capture, or launch modules. The baseline adapter may depend on that vocabulary. Runtime consumers may depend on package references and the support projection.

### Cycles and dead code

The source dependency scan found one runtime cycle between `index/record_ingest.py` and `index/tailer.py`. It does not intersect the proposed reference path. No cycle exists among compatibility, certification, baseline projection, and request schema owners.

No dead owner was found in the relevant pipeline. `mint_outcome` has the production operator caller `api/scripts/mint_harness_certification_record.py`. `RealRuntimeEvidencePending` is the deliberate fail-closed source when bindings are absent.

### Grooming required with the feature

1. Extract pure release reference and certification reference evidence models before adding substantive code to the three files near 700 lines.
2. Add typed finding kinds at the comparison source. Never classify support by parsing `StructureFinding.reason`.
3. Name the existing `schema_digests` semantics in code or documentation so the per-model reference digest cannot be mistaken for that map.
4. Resolve the missing effort coordinate with evidence or an explicit model-and-effort key.
5. Keep model identity fields explicit. Native launch identity, canonical compatibility identity, and wire model are different facts in current source.
6. Remove v1 package and certification paths in the same migration. The repository is pre-release and staged duplicate contracts have no value.

## Plan

### Phase 1: Define the v2 package contract

1. Add pure `ReleaseRequestSchemaReference` and certification provenance models in small owner-focused modules.
2. Add required references to `HarnessCompatibilityRelease` and add route and target cross-reference validation to `CompatibilityReleaseEntry`.
3. Bump the manifest and certification record contracts to v2. Replace the embedded v1 resources in one change.
4. Verify the existing whole-release digest covers the collection and extend activation validation to require exact reference key and schema digest equality.
5. Require every reference version to equal the effective ceiling. Keep the first range one version wide.

Focused proof:

- duplicate or missing model reference is rejected;
- unknown route or canonical identity is rejected;
- wrong observed version is rejected;
- changing one schema byte invalidates the release digest;
- changing one certification reference digest prevents activation;
- every active embedded release has a complete reference set.

### Phase 2: Make baseline projections certification input

1. Extend `MintPlan` with immutable baseline bundle bindings for each logical model cell.
2. Add one adapter that reads each bundle, calls `project_baseline`, and returns the release reference plus certification provenance.
3. Validate common harness, provider, top version, capture policy, runtime template, and source identity before assembly.
4. Validate model coverage per explicit launch identity. Include effort after its invariance decision.
5. Update `mint_outcome` and `successor_entry` to seal the reference collection and the chosen range.
6. Re-capture the current Claude, Codex, and Grok cohorts because the existing raw inputs are unavailable.

Focused proof:

- an archived immutable bundle supports an offline mint with no provider call;
- a digest-only certification record cannot stand in for a bundle;
- a mixed-version cohort is rejected;
- one omitted alias is rejected even when another alias has an exact schema;
- a changed deriver re-derives from the bundle before minting.

### Phase 3: Add the authoritative comparison API

1. Add typed structural change kinds to `StructureFinding` creation sites.
2. Add the pure support projection over one directed `compare_request_schema(reference, candidate)` report.
3. Return support state and findings as separate keys.
4. Leave `compare_model_pair` and equivalence folding unchanged for peer diagnostics.

Mutation proof:

- candidate property removal yields `degraded` plus `missingProperties`;
- candidate property addition yields `blessed` plus `additionalProperties`;
- rename yields `degraded`, one missing pointer, and one additional pointer;
- identical schema yields `blessed` with empty findings;
- reversing reference and candidate changes the directed verdict and no symmetric fold reaches this API.

### Phase 4: Establish verdict persistence, without wiring the launch trigger

1. Add a small support verdict artifact model and store beneath `<channel home>/baselines/verdicts`.
2. Address it by release digest and candidate bundle tail. Validate reference, candidate, and support deriver digests on read.
3. Treat a missing or stale artifact as a cache miss and re-derive from the signed release plus immutable bundle.
4. Store state and finding causes separately.
5. Record the successful candidate bundle ID in attempt state or a dedicated version result pointer.
6. Leave trigger timing and launch orchestration for the dedicated consumer slice.

Focused proof:

- stable and preview homes return independent verdicts for the same model and version;
- an idempotent rewrite preserves identical bytes;
- a new release, reference digest, bundle, or deriver does not reuse the old verdict;
- blessed with no findings round trips;
- blessed with additions and degraded with missing properties remain distinct.

### Phase 5: Integration gates

1. Run focused request schema, baseline projection, certification minting, compatibility store, and migration tests.
2. Run the certification script in offline fixture mode, then `--verify-activation` against the produced package copy.
3. Inspect the produced manifest and record, including reference counts, top version binding, canonical digests, and package size.
4. Run `just check` and inspect `git status` because that target may apply fixers.
5. Run `just test` and record the exact pass, skip, and duration values.
6. Recheck file sizes and runtime dependency cycles before delivery.

## Explicit exclusions

- No launch-time trigger or background scheduling.
- No support state derivation inside inventory or resolver.
- No request-to-IR or IR-to-overlay significance map.
- No protocol-class storage key.
- No provider turns during this scout.
