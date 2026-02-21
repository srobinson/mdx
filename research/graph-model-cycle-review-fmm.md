---
title: Graph model and cycle reporting review for fmm Linear issues
type: research
tags: [rust, fmm, graph, linear, scc, dependency-analysis]
summary: Reviewed ALP-2087 through ALP-2092 with graph storage, edge metadata, and SCC reporting lens; split query adapter work into ALP-2120 and clarified GraphIndex rebuild semantics.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-30
updated: 2026-04-30
---

# Graph model and cycle reporting review for fmm Linear issues

## Executive Summary

fmm currently stores graph identity and reverse dependencies as path keyed structures. The Linear plan is directionally correct, but ALP-2090 was too broad because it combined graph storage, query migration, and compatibility verification.

The review split query migration into ALP-2120, clarified that `GraphIndex` should be rebuilt from SQLite canonical rows rather than persisted as derived ranges, and changed SCC reporting to a separate cycle query/tool instead of an optional field on `fmm_dependency_graph`.

## Project Metadata

- Language: Rust 2024 workspace.
- Key crates: `fmm-core`, `fmm-store`, `fmm-cli`.
- Store: SQLite through `rusqlite`.
- Existing graph identity: path strings.
- Existing graph query surface: `fmm_dependency_graph`, `fmm_search depends_on`, `fmm_list_files sort_by=downstream`.
- Existing cycle behavior: traversal loop avoidance only, no SCC reporting.

## Architecture

### Current graph model

- `Manifest.files` is `HashMap<String, FileEntry>` and `Manifest.reverse_deps` is `HashMap<String, Vec<String>>` in `crates/fmm-core/src/manifest/mod.rs:154-175`.
- SQLite stores `files.path`, `exports.file_path`, and `reverse_deps.target_path/source_path` as text in `crates/fmm-store/src/schema.rs:82-123`.
- Reverse deps load directly into the manifest map in `crates/fmm-store/src/reader.rs:291-308`.
- Reverse deps are rebuilt by loading all file rows, constructing a temporary manifest, calling `rebuild_reverse_deps`, then writing path pairs in `crates/fmm-store/src/writer.rs:283-326`.
- `build_reverse_deps` scans files and dependencies, resolving local, dotted, Python, and workspace edges in `crates/fmm-core/src/manifest/dependency_matcher/reverse.rs:23-73`.

### Current query model

- Direct graph query combines resolved local dependencies, external imports, and `manifest.reverse_deps` in `crates/fmm-core/src/search/dependency_graph.rs:13-79`.
- Transitive graph query uses BFS with `HashSet<String>` visited state and `VecDeque` queues in `crates/fmm-core/src/search/dependency_graph_transitive.rs:22-168`.
- `depends_on` transitive search also uses `manifest.reverse_deps` in `crates/fmm-core/src/search/filter_search.rs:130-152`.
- `fmm_list_files` downstream counts read `manifest.reverse_deps[path].len()` in `crates/fmm-cli/src/mcp/tools/list_files.rs:93-105`.
- MCP graph dispatch is in `crates/fmm-cli/src/mcp/tools/graph.rs:9-77` and tool routing is in `McpServer.handle_tool_call` at `crates/fmm-cli/src/mcp/mod.rs:275-352`.

### Current TypeScript edge metadata gap

- TypeScript `extract_dependencies` treats `import type` the same as runtime imports by collecting import sources into dependencies in `crates/fmm-core/src/parser/builtin/typescript/extract_imports.rs:43-91`.
- Tests currently assert `import type { Config } from './config'` appears in `metadata.dependencies` in `crates/fmm-core/src/parser/builtin/typescript/tests/edge_cases.rs:35-66`.
- Tests currently assert type only named imports are included in `named_imports` in `crates/fmm-core/src/parser/builtin/typescript/tests/named_imports.rs:69-78`.
- `PreserializedRow` has JSON fields for imports, dependencies, named imports, namespace imports, and function names, but no edge kind metadata in `crates/fmm-core/src/types.rs:17-29`.

## Key Patterns

### Rebuild derived graph arrays from canonical SQLite rows

`GraphIndex` should be in memory derived state. Persist canonical rows only: file id to path mappings and dependency edge rows with edge kind. Rebuild the dense arrays and ranges deterministically on load.

This avoids schema coupling to in memory range layout and keeps `.fmm.db` resilient to graph struct changes. It also fits the current store pattern, where `.fmm.db` is regeneratable and `SCHEMA_VERSION` can force rebuilds.

### Split storage from query migration

ALP-2090 should own graph data structures and deterministic rebuild. ALP-2120 should own migration of existing query APIs to those structures. This keeps public behavior parity tests focused and prevents ALP-2090 from spanning store, graph core, search, MCP, and list file output in one overloaded worker issue.

### Use directional ranges for hot upstream and downstream queries

fmm has hot upstream and downstream traversal. The recommended shape is a node with compact dependency and dependent ranges into flat arrays:

- dependency range: outgoing edges from source file to target file
- dependent range: incoming edges where this file is the target

Two directional flat arrays are acceptable for the first implementation because they simplify hot queries. If memory pressure appears later, replace duplicated edge records with one edge table plus sorted index arrays.

### Use a new cycle query surface

SCC reporting is graph level diagnostic output. `fmm_dependency_graph` is file centered traversal output. A separate `fmm_dependency_cycles` surface keeps compatibility clean and supports whole graph, file scoped, runtime, and all edge modes.

## Detailed Findings

### 1. GraphIndex persistence decision

Decision: rebuild `GraphIndex` from SQLite rows on load. Do not persist derived adjacency ranges or a serialized graph blob.

Updated ALP-2090 to require canonical persistence of file id to path rows and dependency edge rows with edge kind metadata. Ranges remain derived in memory.

### 2. Range design and query compatibility

Current direct and transitive graph queries depend on `manifest.reverse_deps` and path strings. Migrating them at the same time as storage would overload ALP-2090.

Created ALP-2120 to migrate:

- `dependency_graph`
- `dependency_graph_transitive`
- `filter_search depends_on`
- `fmm_list_files sort_by=downstream`
- MCP path based graph output

### 3. Edge kind metadata and TypeScript behavior

ALP-2119 exists and is necessary. Current TypeScript behavior treats `import type` as a normal dependency, which would create noisy runtime cycle reports. Runtime cycle reporting must exclude type only edges by default.

Mixed TypeScript imports should be runtime edges unless every import in the statement is type only.

### 4. Cycle reporting API surface

Updated ALP-2092 to prefer a new `fmm_dependency_cycles` tool/query rather than adding optional fields to `fmm_dependency_graph`.

Suggested args:

- optional `file`
- optional `filter`: `all | source | tests`
- optional `edge_mode`: `runtime | all`

Default edge mode should be `runtime`, excluding type only edges.

### 5. Runtime versus type only cycle filtering

Runtime cycle reports must exclude type only edges. Optional all edge mode can include type only edges if cheap and clearly named. Tests should cover runtime cycles, type only only cycles, mixed cycles, self loops, and no cycle graphs.

### 6. Issue split decision

ALP-2090 should be split into graph storage and query adapter work. Edge metadata is already split into ALP-2119, so no additional edge metadata issue was needed.

Created ALP-2120 for query adapter migration.

### 7. Files likely to exceed 500 to 700 LOC

Current large files that should not absorb graph work directly:

- `crates/fmm-core/src/manifest/dependency_matcher_tests.rs`: 640 LOC.
- `crates/fmm-store/src/memory_store.rs`: 589 LOC.
- `crates/fmm-store/src/reader.rs`: 566 LOC.
- `crates/fmm-core/src/manifest/glossary_builder.rs`: 566 LOC.
- `crates/fmm-core/src/manifest/private_members/tests.rs`: 559 LOC.
- `crates/fmm-core/src/manifest/mod.rs`: 539 LOC.
- `crates/fmm-cli/src/cli/sidecar.rs`: 521 LOC.

Recommended seams:

- Add `crates/fmm-core/src/graph/{types,build,index,cycles}.rs`.
- Add store graph loader and writer helpers rather than expanding `reader.rs` and `writer.rs`.
- Keep MCP cycles in a new `crates/fmm-cli/src/mcp/tools/cycles.rs`.
- Keep query adapter logic outside presentation formatters and MCP tool modules.

## Linear Updates

Reviewed:

- ALP-2087
- ALP-2088
- ALP-2089
- ALP-2090
- ALP-2091
- ALP-2092
- ALP-2119
- ALP-2121

Updated:

- ALP-2087: execution order now includes ALP-2120 and clarifies graph derived state rebuild policy.
- ALP-2088: acceptance criteria now guards graph rebuild behavior when fingerprint hits occur.
- ALP-2089: clarified `FileId` as internal graph identity, deterministic for the same active file set, not durable external identity.
- ALP-2090: narrowed scope to in memory `GraphIndex`, canonical SQLite rows, deterministic rebuild, directional ranges, and no public query migration.
- ALP-2092: changed cycle reporting API recommendation to a new query/tool with runtime default edge filtering.
- ALP-2120: created query adapter issue under ALP-2087, blocked by ALP-2090 and blocking ALP-2092.
- ALP-2120: removed an erroneous ALP-2091 blocker because convention plugins are independent of graph query migration.

## Dependencies

Critical dependency order after review:

1. ALP-2088 for fingerprint invalidation, independent but must not corrupt graph rows.
2. ALP-2089 for `FileId` core identity.
3. ALP-2121 for SQLite file path table storage, created by another reviewer and correctly blocking ALP-2090.
4. ALP-2119 for TypeScript type only edge metadata.
5. ALP-2090 for in memory flat graph storage.
6. ALP-2120 for query adapter migration.
7. ALP-2092 for SCC cycle reporting.

## Relevance to Helioy

The graph work directly affects fmm as Helioy's code structural intelligence layer. Rebuilding compact in memory graph arrays from canonical SQLite rows gives agents faster traversal while preserving path based MCP contracts.

## Open Questions

- Should ALP-2119 keep its current dependency on ALP-2089, or should parser level edge kind extraction be allowed to land before `FileId` storage? Current ordering reduces schema churn, so no change was made.
- Should all edge cycle mode be mandatory or optional? The issue now allows it if cheap.
- Should `GraphIndex` replace `Manifest.reverse_deps` entirely in the same release, or keep it as a temporary compatibility adapter through one migration cycle?
