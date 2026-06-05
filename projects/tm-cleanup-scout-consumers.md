# Baseline bundle leaf consumer map

## Scope and result

I inspected live `main` at `13cee80ca3be39ec100e496ca50a1fdc8ab7b3c1`. `HEAD`, `main`, and `origin/main` matched, and the worktree was clean before inspection. The store inspection covered the 16 bundle JSON files under `~/.transport-matters/baselines/bundles` without changing them.

None of the requested `RequestStringLeaf` fields participates in the structure gate. Four fields have no production reader after construction: `token_count`, `character_count`, `byte_count`, and `api_role`. `provenance` has one evidence classification reader. Leaf `sha256` has an artifact validation reader and a test only aggregation reader. Those two fields can still leave the stored leaf after their named consumers change.

The word `sha256` needs a narrow scope here. `RequestStringLeaf.sha256` is derivable and removable. Other hashes carry current evidence and must remain unless a later design replaces their jobs: `RequestJsonNode.sha256`, `PointerEvidence.value_sha256_by_probe`, `ContentStringLeaf.value_sha256`, `ProbeEvidence.raw_request_sha256`, and `TranscriptEvidence.sha256`.

## Gate and report ownership

The structure path is:

1. `api/src/transport_matters/baseline_capture.py` / `harvest_controlled_baseline` decodes each probe's `raw_request_base64` and passes the raw bytes to `mint_request_schema`.
2. `api/src/transport_matters/request_schema.py` / `mint_request_schema` walks those raw JSON bodies and produces `RequestSchema`. It never reads `RequestInventory`.
3. `api/src/transport_matters/baseline_comparison.py` / `_compare_direction` passes only `reference.request_schema` and `candidate.request_schema` to `compare_request_schema`.
4. `api/src/transport_matters/request_schema.py` / `compare_request_schema` derives exact, degraded, or breaking from schema nodes.

The content path is separate:

1. `api/src/transport_matters/baseline_evidence.py` / `build_content_observations` decodes each probe's raw request bytes, walks the masked body, and computes `ContentStringLeaf.value_sha256` from each visited string.
2. `api/src/transport_matters/baseline_evidence.py` / `compare_content` compares those content observations and returns findings without a `DriftOutcome`.
3. `api/src/transport_matters/baseline_comparison.py` / `comparison_diagnostics` prints only the number of content findings.

The artifact load path gives the leaf fields their only broad coupling. `api/src/transport_matters/baseline_store.py` / `read_baseline_bundle` runs `BaselineBundle.model_validate`. That invokes `ProbeEvidence.validate_raw_evidence` for every probe and `BaselineBundle.validate_probe_contract` for the bundle. A literal field deletion from JSON under the current model fails before a comparison or report runs. This is schema and validator coupling. It does not make the field part of either comparison.

The two command reports do not read leaf fields:

- `api/src/transport_matters/baseline_compare.py` / `_print_report` prints cell coordinates, pair outcomes, structure findings, and content finding counts. `main` reaches it through `read_current_baselines`, so current model validation can stop the command before the first report line.
- `api/src/transport_matters/baseline_harvest.py` / `main` prints the written bundle, `reference_outcome`, structure findings, and content finding count. Reference loading can fail before capture under an incompatible leaf shape. With the reader updated, removing these fields leaves the report unchanged.

The drift related readers are also independent of leaf metadata:

- `api/src/transport_matters/baseline_store.py` / `promotes_baseline` reads only `reference_outcome`. That outcome came from `compare_request_schema`.
- `api/src/transport_matters/baseline_staleness.py` / `assess_baseline_staleness` reads `harness_version` from the current pointer. It does not load the bundle.

Direct dependency and text searches found no baseline bundle route under `api/src/transport_matters/api`, and no baseline bundle contract or leaf consumer under `www` or `shared`. Similar `provenance` and `sha256` names in resource viewing, session storage, and harness certification belong to unrelated models.

## Field dispositions

| Leaf field | Production readers | Structure or content status | Concrete break on deletion | Disposition |
| --- | --- | --- | --- | --- |
| `provenance` | `api/src/transport_matters/baseline_evidence.py` / `_session_derived` reads `leaf.provenance.kind`; `_classify_pointer` calls it during `classify_aba`. Pydantic also validates the nested `ProvenanceAssessment` during bundle load. `api/src/transport_matters/baseline_capture.py` / `_build_probe_evidence` supplies no annotations, so production capture always creates the unknown assessment. | Neither gate nor content reporting. The read can select `PointerEvidence.value_evidence = session-generated`, but no production report or gate consumes `value_evidence`. `_runtime_generated_pointers` uses presence and node digests instead. | Capture raises on the missing attribute in `_session_derived`, and stored bundle loading fails the required model field. `api/src/transport_matters/test_request_inventory.py` / `test_annotation_can_supply_explicit_provenance`, `test_leaves_are_sorted_and_unknown_leaves_are_retained_conservatively`, and the provider role tests assert the field. | Drop with a change to `_session_derived` and its unused session derived classification path. Current production evidence and outcomes remain the same because all stored and produced leaves are unknown. |
| `token_count` | No production reader after `request_inventory._make_leaf` constructs it. Pydantic validates the nested `TokenCount` during load. The optional `AuthoritativeTokenCount` input is separate; baseline capture does not pass authoritative counts. | Neither structure nor content. | Current bundle parsing fails because the field is required. `api/src/transport_matters/test_request_inventory.py` / `test_unicode_digest_character_and_byte_counts` and `test_authoritative_token_count_binds_pointer_and_digest` assert its value and quality. | Safe to drop from the stored leaf and remove the dead stored output. |
| `character_count` | No production reader after construction. Pydantic checks that it is nonnegative during load. | Neither structure nor content. | Current bundle parsing fails because the field is required. `api/src/transport_matters/test_request_inventory.py` / `test_unicode_digest_character_and_byte_counts` asserts the Unicode code point count. | Safe to drop. Compute `len(value)` at any future call site that needs it. |
| `byte_count` | No production reader after construction. Pydantic checks that it is nonnegative during load. | Neither structure nor content. | Current bundle parsing fails because the field is required. `api/src/transport_matters/test_request_inventory.py` / `test_unicode_digest_character_and_byte_counts` asserts the UTF 8 byte count. | Safe to drop. Compute `len(value.encode("utf-8"))` if a future caller needs it. |
| `api_role` | No production reader of `RequestStringLeaf.api_role`. Provider semantic helpers in `request_inventory.py` compute it, and annotation validation reads `LeafAnnotation.api_role` before construction, but later evidence classification reads `tm_ir_section` instead. Pydantic validates the optional role during load. | Neither structure nor content. Content grouping comes from `request_schema.opaque_content_group` and the JSON path. | Current bundle parsing fails because the field is required. `api/src/transport_matters/test_request_inventory.py` / `test_claude_raw_shape_has_proven_roles_and_sections`, `test_codex_roles_sections_and_additional_tools_do_not_need_ir_parser_support`, `test_codex_developer_messages_map_to_system_without_claiming_provenance`, and `test_unrecognized_api_roles_remain_unlabelled` assert it. No CLI or API output changes after the model and tests are updated. | Safe to drop. Nothing consumes populated roles. |
| `sha256` on `RequestStringLeaf` | `api/src/transport_matters/baseline_evidence.py` / `ProbeEvidence.validate_raw_evidence` compares `(pointer, value, sha256)` tuples from a rebuilt inventory and the stored inventory. `api/src/transport_matters/request_inventory.py` / `RequestInventory.aggregate` copies it into `RequestLeafReference`, but dependency inspection finds only `test_request_inventory.py` calling `aggregate`. Pydantic validates its hex shape during load. | Neither structure nor content. ABA stability, `PointerEvidence.value_sha256_by_probe`, `static_nodes`, and `static_fingerprint` use `RequestJsonNode.sha256`, a separate field generated from raw JSON visits. Content reporting computes `ContentStringLeaf.value_sha256` from raw request strings. | Every `read_baseline_bundle` and `read_current_baselines` call fails under the current required field and validator, so `baseline_compare` and reference based harvest stop before reporting. `api/src/transport_matters/test_request_inventory.py` / `test_unicode_digest_character_and_byte_counts` and `test_aggregate_retains_native_members_without_synthetic_identity` assert it. | Drop with changes to `ProbeEvidence.validate_raw_evidence` and `RequestInventory.aggregate`. The validator can compare pointer and value, then recompute the digest when needed. Preserve the nonleaf hash fields named above. |
| Repeated per probe leaf objects | `api/src/transport_matters/baseline_evidence.py` / `ProbeEvidence.validate_raw_evidence` expects one full inventory in every probe. `classify_aba` builds a leaf map for each probe. `_direct_prompt_pattern` reads per probe values for differing prompt derived leaves; `_session_derived` reads provenance; `_classify_pointer` collects `tm_ir_section`. No comparator, report, route, web code, or staleness reader consumes the per probe inventories after validation. | Neither gate depends on the copies. Structure and content both use raw request bytes. The ABA evidence builder needs per probe access, but identical leaves do not need distinct stored objects. | Collapsing objects without updating the model fails `ProbeEvidence.validate_raw_evidence` and the fixtures used by `api/src/transport_matters/test_baseline_evidence.py` / `test_aba_runtime_exclusions_contain_only_changed_non_container_nodes` and `test_bundle_store_is_version_four_and_validates_embedded_raw_evidence`. | Lossless for leaves identical across probes, with the validator and ABA reader adapted to resolve a shared leaf. Keep per probe values for leaves that differ. |

## `api_role` corpus result

Across the 16 live bundles:

| State | Leaves | Share |
| --- | ---: | ---: |
| null | 20,163 | 93.65% |
| nonnull | 1,368 | 6.35% |

The populated values are 639 `developer`, 357 `system`, and 372 `user`. No production code reads the field when populated. The ABA classifier uses `tm_ir_section`; the content builder derives its group from profile and JSON path.

## Dedup assessment

Collapsing identical across probes leaf objects is semantically lossless for every current consumer, subject to changing the current serialized model and two readers.

The evidence is stronger than digest equality alone:

- For every same digest A1, B, A2 leaf triplet in the 16 bundle corpus, the complete leaf object is identical across all three probes. There are zero differences in value, counts, `api_role`, `tm_ir_section`, or `provenance` within those triplets.
- `PointerEvidence.value_sha256_by_probe` and `presence_by_probe` retain the per probe equality and presence proof.
- Each `ProbeEvidence.raw_request_base64` retains the original value independently. `ProbeEvidence.validate_raw_evidence` can rebuild the leaf from those bytes, so a shared stored leaf does not weaken validation.
- `classify_aba` decides stable values from `RequestJsonNode.sha256`. For stable triplets, `_classify_pointer` selects the stable branch before prompt and provenance classification. Its remaining leaf read is the set of `tm_ir_section` values, identical in the live triplets and reproducible from one shared leaf.
- Python code treats leaves as immutable value objects. No consumer relies on object identity.

Two current implementation assumptions must change:

1. `ProbeEvidence.validate_raw_evidence` compares a full leaf tuple inside each probe inventory. It needs to resolve the shared leaf, or validate each probe's pointer and raw value against it.
2. `classify_aba` expects `probe.inventory.leaves` to be a full per probe collection. It needs a resolver that presents shared leaves and probe specific leaves through the same lookup.

These are representation dependencies. They do not block deduplication. Content comparison, structure comparison, CLI reporting, baseline promotion, staleness, and all searched API and web code remain unchanged once those readers accept the compact representation.

## Recommended cleanup boundary

- Drop directly: `token_count`, `character_count`, `byte_count`, and `api_role`.
- Drop after named reader changes: `provenance` and `RequestStringLeaf.sha256`.
- Deduplicate full leaf objects whose A1, B, and A2 objects are identical. Retain probe associations and probe specific leaves.
- Keep the nonleaf hash evidence that owns ABA classification, content comparison, raw request integrity, transcript integrity, and `static_fingerprint`.

This boundary removes the measured leaf waste without changing the structure gate, content findings, report text, promotion result, or staleness result.
