---
title: Raw wire schema design critique
type: review
tags: [transport-matters, issue-382, raw-wire, schema, architecture]
summary: Four blockers and two majors in the proposed raw wire schema design.
status: active
source: codex
confidence: high
created: 2026-08-19
updated: 2026-08-19
---

# Findings

## BLOCKER 1: Collapsed array items merge incompatible element contracts

**Claim.** `mint_request_schema` merges every element at one `items` position. The merge loses both element variant identity and array cardinality. Codex already treats tool elements as tagged variants through `CODEX_REQUEST_TAG_SPINE`, and `_parse_tools` preserves type specific fields. A single object schema for all items authorizes fields wherever any variant supplied them. Sources: `/Users/alphab/.mdx/projects/tm-wire-schema-design.md:mint_request_schema`, `api/src/transport_matters/codex/request_parser.py:CODEX_REQUEST_TAG_SPINE`, `api/src/transport_matters/codex/request_parser.py:_parse_tools`.

**Failure scenario.** The reference contains these two raw tool elements:

```json
[
  {"type":"custom","name":"exec","format":{"type":"grammar"}},
  {"type":"function","name":"wait","strict":false,"parameters":{"type":"object"}}
]
```

The candidate adds `format` to the function element and appends a second function element of the same shape. The collapsed schema has already observed `format`, `strict`, and `parameters` under `items`, and it records no count. `compare_request_schema` can return `EXACT`. The maintainer loses two useful signals: a function tool gained a field, and the harness changed the number of tools.

**Fix.** Mint a union of complete observed element schemas. Preserve a stable discriminator such as `type` with `const` where one exists. Record the observed minimum and maximum item counts. Classify a new field on an existing variant and a count outside the reference range as `DEGRADED`. A repeated known variant can remain content compatible while still preventing an `EXACT` structural verdict.

## BLOCKER 2: The schema comparison relation has unclassified changes

**Claim.** `compare_request_schema` defines candidate property additions, required property removal, strict type supersets, and disjoint types. It defines no verdict for removal of a reference optional property, a candidate type subset, or overlapping type sets where neither side contains the other. Any implementation with `EXACT` as the fallthrough will hide real drift. Source: `/Users/alphab/.mdx/projects/tm-wire-schema-design.md:compare_request_schema`.

**Failure scenario.** The reference observes `cache_control` in one probe and omits it in two, so the property exists but is optional. The candidate omits it in all three probes. No listed rule applies. A second reference observes `metadata` as both `string` and `null`; the candidate observes only `null`. The type sets differ, but the candidate set is neither a strict superset nor disjoint. Both changes can become `EXACT`.

**Fix.** Define an exhaustive relation for every property presence pair and every type set relation. Classify loss of a reference optional property and any nonidentical overlapping type set as `DEGRADED`. Keep `BREAKING` for total removal of a demonstrated required property and for disjoint types. Permit `EXACT` only after structural equality. Add an assertion that no relation reaches an implicit default.

## BLOCKER 3: Three correlated observations do not establish a required contract

**Claim.** `required` means present in A1, B, and A2. Those probes test two prompts and one repeated prompt. They are neither independent samples nor a protocol declaration. Treating a move from three of three to two of three as `BREAKING` turns a weak observation into a consumer guarantee. Sources: `/Users/alphab/.mdx/projects/tm-wire-schema-design.md:mint_request_schema`, `/Users/alphab/.mdx/projects/tm-wire-schema-design.md:compare_request_schema`, `api/src/transport_matters/baseline_capture.py:harvest_controlled_baseline`.

**Failure scenario.** The reference harness sends `service_tier` for all three controlled requests. A new harness sends it for A1 and A2 but omits it for B because prompt B selects a different request path. The field still exists, both shapes parse, and no sample shows a retype. The proposed rule returns `BREAKING`. A valid prompt conditional field is then described as a removed requirement.

**Fix.** Persist presence counts and probe labels as evidence beside the generated schema. Classify three of three to zero of three as `BREAKING`. Classify three of three to one or two of three as `DEGRADED`. `DEGRADED` already prevents promotion, so the gate remains conservative without claiming a contract that three captures cannot prove.

## BLOCKER 4: The new schema walker duplicates the existing raw JSON walker

**Claim.** `mint_request_schema` needs the same recursive traversal, typed path, JSON kind, and pointer construction already implemented by `_observe_native`. Reusing only `json_kind` and pointer helpers still leaves a second traversal. The proposed reuse of `_pointer_tokens` is unsafe for array collapse because that function converts every decimal pointer token to an integer without inspecting its parent container. Sources: `/Users/alphab/.mdx/projects/tm-wire-schema-design.md:mint_request_schema`, `api/src/transport_matters/request_inventory.py:_observe_native`, `api/src/transport_matters/request_inventory.py:_pointer`, `api/src/transport_matters/request_inventory.py:_pointer_tokens`, `api/src/transport_matters/json_tags.py:json_kind`.

**Failure scenario.** A tool schema contains `{"properties":{"0":{"type":"string"}}}`. JSON Pointer represents the object key as `/properties/0`. `_pointer_tokens` turns `0` into an array index. A schema walker that collapses numeric tokens can therefore treat a valid object property as an array position. A separate recursive walker may avoid that bug, but the repository then has two path semantics for the same raw body.

**Fix.** Extract the nested visitor in `_observe_native` into one public raw JSON traversal that emits the decoded value, the typed path, the RFC 6901 pointer, and the JSON kind. Build both `observe_request_json` and `mint_request_schema` on that traversal. Keep RFC 6901 tokens as strings when parsing a pointer. Resolve an array index only from the actual parent container.

## MAJOR 1: A1 versus A2 misses stable runtime values and existing normalization

**Claim.** `runtime_generated_pointers` identifies values only when A1 differs from A2. Runtime values can remain equal inside one bundle. The design omits `mask_cross_launch_body` and `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` from its reuse map even though they already handle raw request text, current dates, working directories, run identifiers, runtime homes, proxy URLs, and launch specific request keys. Sources: `/Users/alphab/.mdx/projects/tm-wire-schema-design.md:runtime_generated_pointers`, `/Users/alphab/.mdx/projects/tm-wire-schema-design.md:compare_content`, `api/src/transport_matters/session/wire_normalization.py:mask_cross_launch_body`, `api/src/transport_matters/session/wire_normalization.py:_CROSS_LAUNCH_MASKS`, `api/src/transport_matters/session/wire_normalization.py:CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`.

**Failure scenario.** A1 and A2 run on 2026-08-19 in the same workspace. Both system strings contain the same date and working directory, so neither pointer is classified as runtime generated. The reference bundle was captured on 2026-08-18 or in another checkout. `compare_content` reports a system prompt update even when the only changes are the date and path. A deterministic `prompt_cache_key` derived from prompt A escapes for the same reason.

**Fix.** Apply `mask_cross_launch_body` before content digests and exclude the existing launch specific keys from content. Keep structure on the unmasked raw body. Add A1 versus A2 scalar leaf pointers as a second source of exclusions, using the union from the reference and candidate bundles. Do not add container digests because one changed leaf makes the root digest change and can exclude the entire report.

## MAJOR 2: The content boundary is undefined and leaves IR fields available to comparison code

**Claim.** `compare_content` says that it compares stable pointers, which includes every raw scalar. The owner limited content reporting to system prompts and tool definitions. The design does not define raw roots for those two categories. It also calls `normalized_request` the last IR residue while retaining `ProbeEvidence.inventory`, `RequestStringLeaf.tm_ir_section`, `PointerEvidence.tm_ir_sections`, and the whole current `AbaAnalysis` shape. The current comparison accepts complete bundles, so those fields remain available to gate code. Sources: `/Users/alphab/.mdx/projects/tm-wire-schema-design.md:compare_content`, `api/src/transport_matters/baseline_evidence.py:ProbeEvidence`, `api/src/transport_matters/baseline_evidence.py:PointerEvidence`, `api/src/transport_matters/baseline_evidence.py:AbaAnalysis`, `api/src/transport_matters/baseline_evidence.py:compare_baseline_bundles`, `api/src/transport_matters/request_inventory.py:RequestStringLeaf`, `api/src/transport_matters/request_inventory.py:_provider_semantics`, `api/src/transport_matters/baseline_capture.py:_build_probe_evidence`.

**Failure scenario.** The system prompt and tools are byte identical, while `temperature` changes from `0.2` to `0.5`. The proposed stable pointer scan reports a content update outside the owner's two categories. If an implementation filters by `tm_ir_section`, a TM change that reclassifies a developer item from `messages` to `system` changes the report with identical raw bytes. Keeping `compare_baseline_bundles(reference, candidate)` also leaves that internal classification in the same call that produces the gate outcome.

**Fix.** Define provider specific selectors over decoded raw JSON that return only system and tool roots. Extract the useful raw classification logic from `_provider_semantics` into a wire content enum that has no `InternalRequest` or `TmIrSection` dependency. Define the version 3 artifact fields explicitly and delete `normalized_request`, `PointerEvidence.tm_ir_sections`, and the old mixed comparison fields. Make the gate function accept only `RequestSchema` values. Make a separate content function accept only selected raw nodes, and keep its return type absent from promotion logic.
