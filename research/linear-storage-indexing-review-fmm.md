---
title: Linear storage and incremental indexing review for fmm fallow issues
type: research
tags: [fmm, linear, sqlite, incremental-indexing, fileid, graph-storage]
summary: Reviewed ALP-2087 through ALP-2092 with a storage lens, clarified fingerprint and FileId boundaries, and created ALP-2121 for SQLite path identity migration.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-30
updated: 2026-04-30
---

# Linear storage and incremental indexing review for fmm fallow issues

## Executive Summary

The issue set was mostly sound, but ALP-2088 and ALP-2089 had two execution risks: duplicate source mtime storage and an overloaded FileId scope that mixed core identity with durable SQLite migration. I updated Linear to make fingerprints a `files` table concern, reuse existing `files.modified` as source mtime, require a shared generate and watch decision helper, and split SQLite FileId path storage into a new issue, ALP-2121.

## Project Metadata

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/fmm`
- Language: Rust 2024 workspace
- Store: SQLite via `fmm-store`
- Index signal: fmm indexed repo, 370 indexed files, 53,146 LOC
- Relevant parent issue: ALP-2087, project `fmm`
- Reviewed issues: ALP-2087, ALP-2088, ALP-2089, ALP-2090, ALP-2092, plus existing downstream ALP-2119 and ALP-2120
- New issue created: ALP-2121

## Architecture

### Current incremental indexing path

`generate` in `crates/fmm-cli/src/cli/sidecar.rs:25-382` collects files, opens SQLite, loads indexed timestamps, checks dirty files, parses dirty files, writes rows, then rebuilds reverse dependencies. Its staleness check uses `load_indexed_mtimes` and compares `indexed_at` against source mtime at `crates/fmm-cli/src/cli/sidecar.rs:113-142`.

`watch::index_file` in `crates/fmm-cli/src/cli/watch.rs:150-173` independently computes the relative path, reads mtime, calls `is_file_up_to_date`, parses, serializes, writes, then rebuilds reverse deps.

The store currently exposes `FmmStore::load_indexed_mtimes` at `crates/fmm-core/src/store.rs:36-44`. The direct store check is `is_file_up_to_date` at `crates/fmm-store/src/writer.rs:19-31`.

### Current SQLite schema

`CREATE_SCHEMA_SQL` in `crates/fmm-store/src/schema.rs:82-92` defines `files(path, loc, modified, imports, dependencies, named_imports, namespace_imports, function_names, indexed_at)`. `SCHEMA_VERSION` is `2` at `crates/fmm-store/src/schema.rs:6`.

`ensure_schema` drops and rebuilds on schema version mismatch at `crates/fmm-store/src/schema.rs:8-21`. Because `.fmm.db` is a regeneratable index, this is acceptable. It also means implementers must not assume `CREATE TABLE IF NOT EXISTS` changes existing tables.

`serialize_file_data` writes the filesystem mtime into `PreserializedRow.mtime` at `crates/fmm-core/src/types.rs:91-95`, and `upsert_preserialized` stores it in `files.modified` at `crates/fmm-store/src/writer.rs:59-80`. This made `source_mtime` as a new column ambiguous.

### Current path identity and graph shape

`Manifest` stores `files`, export indexes, and `reverse_deps` keyed by string paths at `crates/fmm-core/src/manifest/mod.rs:154-175`. There is no exported `FileId` symbol today.

SQLite also uses path strings: `files.path`, `exports.file_path`, `methods.file_path`, and `reverse_deps.target_path/source_path` at `crates/fmm-store/src/schema.rs:82-123`.

File discovery canonicalizes paths in `collect_files` at `crates/fmm-cli/src/cli/files.rs:11-77`; `collect_files_multi` then sorts and deduplicates `PathBuf`s at `crates/fmm-cli/src/cli/files.rs:123-137`. `resolve_root` canonicalizes roots at `crates/fmm-cli/src/cli/resolve.rs:10-24`, and `resolve_root_multi` computes a common ancestor at `crates/fmm-cli/src/cli/resolve.rs:41-62`.

Graph traversal is string keyed. Direct graph queries read `Manifest.reverse_deps` at `crates/fmm-core/src/search/dependency_graph.rs:69-76`. Transitive graph queries use BFS with visited sets at `crates/fmm-core/src/search/dependency_graph_transitive.rs:22-168`.

## Key Patterns

1. **Fingerprint data belongs on `files` for now.** The `files` row already represents the durable per file index row. Adding `source_size`, `content_hash`, and `parser_cache_version` there avoids a join and keeps fingerprint lifecycle aligned with file row lifecycle.
2. **Do not duplicate source mtime.** `files.modified` already stores source mtime. ALP-2088 now requires reusing it or renaming it safely under a schema version bump.
3. **Generate and watch need one staleness decision helper.** The current paths duplicate the stale check shape. ALP-2088 now requires a shared helper used by generate, dry run, and watch.
4. **Core FileId and SQLite identity migration are separate tasks.** ALP-2089 now owns `FileId`, deterministic assignment, normalization, and adapters. ALP-2121 owns durable SQLite path identity.
5. **Graph storage and query migration are separate tasks.** ALP-2090 now owns `GraphIndex` storage and builder. Existing ALP-2120 owns moving public query APIs onto `GraphIndex`.

## Detailed Findings

### ALP-2088, two tier cache invalidation

Validated issue references against current repo symbols:

- `generate`: `crates/fmm-cli/src/cli/sidecar.rs:25-382`
- `index_file`: `crates/fmm-cli/src/cli/watch.rs:150-173`
- `is_file_up_to_date`: `crates/fmm-store/src/writer.rs:19-31`
- `load_indexed_mtimes`: `crates/fmm-store/src/writer.rs:37-46`
- `FmmStore::load_indexed_mtimes`: `crates/fmm-core/src/store.rs:36-44`
- `CREATE_SCHEMA_SQL`: `crates/fmm-store/src/schema.rs:79-137`

Corrections applied in Linear:

- Clarified that fingerprint fields stay on `files` for this issue.
- Clarified that `files.modified` already stores source mtime and should be reused or renamed, not duplicated.
- Added explicit guidance not to rely on `CREATE TABLE IF NOT EXISTS` for migrations.
- Required one shared fingerprint decision helper across generate, dry run, and watch.
- Added parser cache version mismatch to test coverage.

Remaining risk: ALP-2088 is still a meaningful issue because it touches schema, store APIs, generate, dry run, watch, and tests. It is manageable only if the implementer extracts a focused fingerprint module rather than growing `sidecar.rs` or `watch.rs`.

### ALP-2089, FileId path identity

Validated issue references against current repo symbols:

- `Manifest`: `crates/fmm-core/src/manifest/mod.rs:154-200`
- `FileEntry`: `crates/fmm-core/src/manifest/mod.rs:34-72`
- `CREATE_SCHEMA_SQL`: `crates/fmm-store/src/schema.rs:82-123`
- `collect_files`: `crates/fmm-cli/src/cli/files.rs:11-77`
- `collect_files_multi`: `crates/fmm-cli/src/cli/files.rs:123-137`
- `resolve_root`: `crates/fmm-cli/src/cli/resolve.rs:10-24`

Corrections applied in Linear:

- Fixed wording that implied `collect_files_multi` already sorts relative paths. It sorts canonical `PathBuf`s; normalized relative path assignment still needs to be defined.
- Added explicit path normalization rule: canonicalize root, strip root, normalize slash separated relative paths, reject paths outside root.
- Clarified that ids need not stay stable when the indexed file set changes. Downstream storage must tolerate rebuild or remapping.
- Split durable SQLite path identity migration into ALP-2121.

### ALP-2121, new issue for SQLite FileId storage

Created ALP-2121: `Add SQLite file path table for FileId storage`.

Purpose:

- Own the durable storage migration after ALP-2089 introduces core `FileId` identity.
- Add `file_paths` or equivalent mapping from `file_id` to normalized relative path.
- Handle schema version bump, stale path row cleanup, and path based public output compatibility.
- Block ALP-2090 so flat graph storage does not invent its own path migration.

### ALP-2090, flat graph storage

Validated current graph storage references:

- `Manifest.reverse_deps`: `crates/fmm-core/src/manifest/mod.rs:171-175`
- `build_reverse_deps`: `crates/fmm-core/src/manifest/dependency_matcher/reverse.rs:23-73`
- `dependency_graph`: `crates/fmm-core/src/search/dependency_graph.rs:13-79`
- `dependency_graph_transitive`: `crates/fmm-core/src/search/dependency_graph_transitive.rs:22-168`
- `load_files_map`: `crates/fmm-store/src/writer.rs:212-276`
- `rebuild_and_write_reverse_deps`: `crates/fmm-store/src/writer.rs:283-326`
- `write_reverse_deps`: `crates/fmm-store/src/writer.rs:329-346`

Corrections applied in Linear:

- Added ALP-2121 as a blocker.
- Clarified that ALP-2090 owns `GraphIndex` storage and builder, not full public query migration.
- Clarified that ALP-2120 owns dependency query API migration.
- Preserved the requirement that public behavior remains unchanged while ALP-2090 lands.

### ALP-2092, SCC cycle reporting

ALP-2092 had already been updated by another reviewer before this pass. It now names ALP-2120 as a blocker and chooses a separate `fmm_dependency_cycles` surface rather than overloading `fmm_dependency_graph`.

This is consistent with the storage review. SCC reporting should depend on the graph backed query layer, not just the raw flat graph builder.

### Files at LOC risk

Relevant current sizes:

- `crates/fmm-cli/src/cli/mod.rs`: 643 LOC
- `crates/fmm-cli/src/cli/sidecar.rs`: 521 LOC
- `crates/fmm-cli/src/cli/watch.rs`: 463 LOC
- `crates/fmm-store/src/reader.rs`: 566 LOC
- `crates/fmm-store/src/memory_store.rs`: 589 LOC
- `crates/fmm-core/src/manifest/mod.rs`: 539 LOC
- `crates/fmm-core/src/manifest/glossary_builder.rs`: 566 LOC

Recommended decomposition seams:

- `crates/fmm-cli/src/cli/fingerprint.rs` or equivalent for shared generate, dry run, and watch staleness decisions.
- `crates/fmm-core/src/file_id.rs` or `crates/fmm-core/src/identity.rs` for `FileId`, path normalization, and id assignment.
- `crates/fmm-store/src/path_table.rs` for SQLite path identity round trips.
- `crates/fmm-core/src/graph/` for `GraphIndex`, `Node`, `Edge`, and cycle logic.
- Keep MCP adapters thin under `crates/fmm-cli/src/mcp/tools/`.

## Dependencies

No code dependencies were changed. The issue set now expects future implementation to add or choose hashing support for content fingerprints, likely `xxh3-rust` if following fallow, but that was not added during this review.

## Relevance to Helioy

These changes keep fmm suitable as Helioy's structural context substrate. The review reduces the chance that Nancy agents implement incompatible graph identity or duplicate cache logic across generate and watch.

## Open Questions

- Whether `files.modified` should be renamed to `source_mtime` in a schema bump or kept as is for compatibility.
- Whether ALP-2088 should be split further if the implementing agent cannot keep the fingerprint module isolated.
- Whether ALP-2121 should convert all existing path foreign keys to id foreign keys immediately or first land a path table adapter beside the current text columns.
