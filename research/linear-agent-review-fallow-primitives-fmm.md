---
title: Linear agent review for fallow primitives in fmm
type: research
tags: [linear, fmm, rust, fallow, agent-review, nancy]
summary: Reviewed and corrected the fmm fallow primitives Linear issue set so Nancy has clearer issue boundaries, dependency handoffs, convention plugin sequencing, and graph migration seams.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-30
updated: 2026-04-30
---

# Linear agent review for fallow primitives in fmm

## Executive Summary

Reviewed Linear issues ALP-2087 through ALP-2092 for Nancy execution quality, convention plugin scope, issue boundaries, and cross issue handoffs. The issue set is technically sound after review, with the main correction being that ALP-2091 was split into trait, registry adapter, and first concrete convention plugin work.

A request to spawn three additional agents was attempted through warroom tooling, but this runtime was not inside tmux. I left existing agents alone, messaged three live Helioy review agents through helioy-bus, and proceeded with the review. No agent replies arrived before completion.

## Project Metadata

* Project: fmm.
* Language: Rust 2024 workspace.
* Linear project: `fmm`.
* Team: Alphabio.
* Role label: `rust-engineer`.
* Source research:
  * `~/.mdx/research/fmm-vs-fallow-five-findings.md`
  * `~/.mdx/research/fallow-rs-fallow.md`
* Review date: 2026-04-30.

## Architecture Evidence Checked

fmm tools were used first for structural validation.

* `crates/fmm-cli/src/cli/sidecar.rs`
  * `generate` is 358 lines inside a 521 LOC file.
  * It has separate dry run staleness logic at lines 68 to 83 and bulk dirty filtering at lines 113 to 142.
* `crates/fmm-cli/src/cli/watch.rs`
  * `index_file` at lines 150 to 173 uses the same mtime check before parsing.
* `crates/fmm-store/src/writer.rs`
  * `is_file_up_to_date` at lines 19 to 31 compares `indexed_at` to source mtime.
  * `load_indexed_mtimes`, `rebuild_and_write_reverse_deps`, and `write_reverse_deps` are the current store seams.
* `crates/fmm-store/src/schema.rs`
  * `CREATE_SCHEMA_SQL` defines path text storage and lacks source size, content hash, parser cache version, `FileId`, and edge kind columns.
* `crates/fmm-core/src/manifest/mod.rs`
  * `Manifest` at lines 154 to 200 stores `files`, export maps, and `reverse_deps` using path strings.
  * The file is 539 LOC with broad downstream blast radius.
* `crates/fmm-core/src/parser/registry.rs`
  * `ParserRegistry` at lines 32 to 41 already stores parser descriptors and convention adjacent indexes.
  * `is_reexport_file` at lines 168 to 170 and `is_language_test_file` at lines 177 to 199 are existing convention behaviors.
* `crates/fmm-core/src/parser/types.rs`
  * `RegisteredLanguage` at lines 34 to 43 carries reexport filenames and language test patterns.
* `crates/fmm-core/src/search/dependency_graph_transitive.rs`
  * `dependency_graph_transitive` is a BFS traversal, not SCC reporting.
* Large file risk from fmm file listing:
  * `crates/fmm-core/src/resolver/workspace_tests.rs`: 679 LOC.
  * `crates/fmm-cli/src/cli/mod.rs`: 643 LOC.
  * `crates/fmm-core/src/parser/builtin/python/mod.rs`: 619 LOC.
  * `crates/fmm-store/src/reader.rs`: 566 LOC.
  * `crates/fmm-core/src/manifest/glossary_builder.rs`: 566 LOC.
  * `crates/fmm-core/src/manifest/mod.rs`: 539 LOC.
  * `crates/fmm-cli/src/cli/sidecar.rs`: 521 LOC.

## Linear Updates Made

### ALP-2087: Adopt fallow-rs primitives in fmm

Updated the parent issue to include the complete current execution order and handoff contracts:

1. ALP-2088: fingerprint invalidation.
2. ALP-2089: core `FileId` identity.
3. ALP-2121: SQLite path table for durable `FileId` storage.
4. ALP-2119: TypeScript type only edge metadata.
5. ALP-2090: in memory flat graph storage.
6. ALP-2120: migration of existing dependency query APIs to `GraphIndex`.
7. ALP-2092: SCC cycle reporting.
8. ALP-2091: convention plugin trait.
9. ALP-2122: convention plugin registry adapter.
10. ALP-2123: first concrete convention plugin for test classification.

Added explicit handoff contracts so Nancy workers know what each predecessor must leave behind.

### ALP-2091: Define fmm convention plugin trait contract

Updated the issue title and description to narrow scope. ALP-2091 now owns only the trait contract and static defaults surface. It no longer owns registry implementation or the first concrete plugin.

Key guardrails now present:

* Keep `Parser` and `RegisteredLanguage` behavior unchanged.
* Put the trait outside parser construction.
* Do not add framework plugins.
* Prove static defaults can be read without constructing parser instances.

### ALP-2122: Add fmm convention plugin registry adapter

Created this sub issue under ALP-2087.

URL: `https://linear.app/alphabio/issue/ALP-2122/add-fmm-convention-plugin-registry-adapter`

Purpose: add the convention plugin registration surface after ALP-2091, while avoiding a second source of truth beside `ParserRegistry`.

Important acceptance criteria:

* Plugins can be registered and enumerated without constructing parser instances.
* Existing `ParserRegistry` convention behavior remains unchanged.
* Existing descriptor conventions are reachable through one adapter path.
* ALP-2123 can consume the adapter.

### ALP-2123: Move test file classification into first convention plugin

Created this sub issue under ALP-2087.

URL: `https://linear.app/alphabio/issue/ALP-2123/move-test-file-classification-into-first-convention-plugin`

Purpose: prove the convention plugin system with an existing fmm convention rather than inventing a framework corpus.

The first plugin target is existing test file classification, currently backed by `ParserRegistry.is_language_test_file`, `RegisteredLanguage.test_patterns`, and generic config defaults.

### Existing reviewer additions validated

While this review was running, additional issue changes appeared under ALP-2087. I did not revert them. I incorporated their handoffs into the parent issue.

* ALP-2120: `Migrate dependency query APIs to GraphIndex`.
  * This cleanly separates query migration from ALP-2090 graph storage.
  * It blocks ALP-2092.
* ALP-2121: `Add SQLite file path table for FileId storage`.
  * This cleanly separates durable storage migration from ALP-2089 core identity.
  * It blocks ALP-2090.

## Review Findings

### Parent issue quality

ALP-2087 now states the outcome and acceptance criteria at the right level. It includes enough execution order and guardrails for Nancy, while detailed implementation remains in sub issues.

### Sub issue boundaries

The current set is better aligned for Nancy:

* ALP-2088 remains one concern: two tier cache invalidation.
* ALP-2089 owns core deterministic file identity.
* ALP-2121 owns durable SQLite identity storage.
* ALP-2119 owns edge kind metadata.
* ALP-2090 owns graph storage only.
* ALP-2120 owns migrating existing dependency APIs to the graph.
* ALP-2092 owns cycle reporting.
* ALP-2091, ALP-2122, and ALP-2123 split the convention plugin work into executable steps.

### Dependencies and blockers

Validated blockers now form a safe chain:

* ALP-2089 blocks ALP-2121, ALP-2119, ALP-2090, and ALP-2092.
* ALP-2121 blocks ALP-2090.
* ALP-2119 blocks ALP-2090 and ALP-2092.
* ALP-2090 blocks ALP-2120 and ALP-2092.
* ALP-2120 blocks ALP-2092.
* ALP-2091 blocks ALP-2122.
* ALP-2122 blocks ALP-2123.

### Documentation handoffs

The parent now names each handoff explicitly. This is important because Nancy workers will otherwise make local design choices that can diverge across issues.

Important handoffs:

* Fingerprint helper from ALP-2088 must be shared by generate, dry run, and watch.
* File id rules from ALP-2089 must feed the SQLite table work in ALP-2121.
* Edge kind metadata from ALP-2119 must be carried by ALP-2090 and filtered by ALP-2092.
* Graph construction from ALP-2090 must be stable before ALP-2120 moves public queries.
* Registry adapter from ALP-2122 must give ALP-2123 a single consumer path.

## DRY Risks and Reuse Targets

Workers should reuse these seams before adding new logic:

* Staleness:
  * `is_file_up_to_date` in `crates/fmm-store/src/writer.rs`.
  * `load_indexed_mtimes` as the replacement seam for fingerprint loading.
  * Existing dry run and generate filtering in `sidecar.rs` should converge on one helper.
* Serialization:
  * `serialize_file_data` and `PreserializedRow` reexports in `crates/fmm-store/src/writer.rs`.
* Graph:
  * `build_reverse_deps` is the old matching source to subsume, not duplicate indefinitely.
  * `dependency_graph`, `dependency_graph_transitive`, and `transitive_dependents` need one shared graph traversal adapter after ALP-2120.
* Conventions:
  * `ParserRegistry.is_language_test_file` and `is_reexport_file` are existing convention behaviors.
  * `RegisteredLanguage` descriptors should not be copied into a conflicting registry.

## Decomposition Seams

Recommended extraction seams for workers:

* `crates/fmm-core/src/fingerprint.rs` or a store adjacent module for file fingerprint types and staleness decisions.
* `crates/fmm-core/src/file_id.rs` for `FileId` and deterministic assignment rules.
* `crates/fmm-store/src/file_paths.rs` for durable path identity storage.
* `crates/fmm-core/src/graph/{types,build,index,cycles}.rs` for graph storage and SCC logic.
* `crates/fmm-core/src/conventions/{mod,registry}.rs` for convention plugin trait and adapter.

Files that should not absorb much more implementation logic:

* `crates/fmm-cli/src/cli/sidecar.rs`: 521 LOC.
* `crates/fmm-core/src/manifest/mod.rs`: 539 LOC.
* `crates/fmm-store/src/reader.rs`: 566 LOC.
* `crates/fmm-core/src/parser/registry.rs`: 239 LOC but already owns mixed parser and convention adjacent state.

## Relevance to Helioy

This review improves the work queue that upgrades fmm as Helioy's structural intelligence layer. The changes reduce the chance that Nancy workers implement incompatible local designs across cache invalidation, identity, graph storage, cycle reporting, and conventions.

## Remaining Risks

* ALP-2089 plus ALP-2121 is still a significant cross crate migration. The split is better, but workers may need a small design note before implementation.
* ALP-2119 remains blocked by ALP-2089 in Linear. This is safe but conservative. If schedule matters, type only metadata could be implemented earlier with a compatibility adapter.
* ALP-2123 may expose tension between parser descriptors and convention plugins. The issue now calls out the adapter risk.
* Manual sort order was not updated in this pass. Linear blockers are the source of truth.
* The three messaged review agents did not reply before completion.

## Recommendations Not Applied Directly

* I did not create a separate ADR issue. The existing research docs and Linear handoffs are enough for this implementation wave.
* I did not remove or merge concurrent reviewer issues ALP-2120 and ALP-2121 because they improve issue boundaries.
* I did not change repo files.
