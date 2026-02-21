---
title: fmm vs fallow five findings
type: research
tags: [rust, fmm, fallow, dependency-graph, incremental-indexing, helioy]
summary: fmm already has SQLite incremental indexing and static language descriptors, but lacks fallow style content hash validation, dense file ids, flat graph storage, framework plugins, and SCC cycle reporting.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

# fmm vs fallow five findings

## Executive Summary

fmm is a Rust workspace for code structural intelligence. It indexes source files into `.fmm.db`, then serves topology, symbol lookup, outlines, dependency graphs, and blast radius through CLI and MCP.

Against the five fallow primitives, the highest value lift is the two tier incremental cache. The second priority is a staged internal graph model: path sorted `FileId(u32)` first, then flat edge storage and SCC reporting.

## Project Metadata

- Language: Rust 2024 workspace (`Cargo.toml:1-7`).
- Crates: `fmm-core`, `fmm-cli`, `fmm-store` (`Cargo.toml:1-16`).
- Parsing: tree-sitter for TypeScript, Python, Rust, Go, Java, C family, Ruby, PHP, Zig, Lua, Scala, Swift, Kotlin, Dart, Elixir (`Cargo.toml:18-37`).
- Store: SQLite via `rusqlite` (`Cargo.toml:57-58`).
- Parallelism: rayon and indicatif (`Cargo.toml:53-55`).
- File walking: `ignore::WalkBuilder` is already used for source discovery (`crates/fmm-cli/src/cli/files.rs:1-32`).
- Index signal: repo is fmm indexed. `fmm validate` reported all indexed files up to date during this review.

## Architecture Snapshot

- `crates/fmm-core/src/parser/`: parser trait, registry, language parsers, static descriptors.
- `crates/fmm-core/src/manifest/`: in memory manifest, export indexes, reverse dependency map.
- `crates/fmm-core/src/search/`: structural queries and dependency graph traversal.
- `crates/fmm-store/src/`: SQLite schema, reader, writer, store implementation.
- `crates/fmm-cli/src/cli/sidecar.rs`: `fmm generate` indexing pipeline.
- `crates/fmm-cli/src/cli/watch.rs`: live file update path.

## Finding 1. Bitcode incremental cache with `(mtime, size)` fast path then xxh3 content hash

### Status in fmm today

fmm has incremental indexing, but the invalidation key is only time based.

The current generate path scans files, opens the store, bulk loads prior indexed timestamps, and filters dirty files by comparing source mtime to the stored `indexed_at` value (`crates/fmm-cli/src/cli/sidecar.rs:113-142`). It then parses dirty files in parallel with one `ParserCache` per rayon worker (`crates/fmm-cli/src/cli/sidecar.rs:182-288`), serializes rows (`crates/fmm-cli/src/cli/sidecar.rs:291-318`), writes SQLite in one transaction (`crates/fmm-cli/src/cli/sidecar.rs:320-337`), then rebuilds reverse deps (`crates/fmm-cli/src/cli/sidecar.rs:340-353`).

The timestamp helper reads filesystem metadata and returns an RFC3339 mtime (`crates/fmm-cli/src/fs_utils.rs:16-25`). Store level staleness checks query `files.indexed_at` and compare it to source mtime (`crates/fmm-store/src/writer.rs:19-31`). Bulk staleness loads `path, indexed_at` for every file (`crates/fmm-store/src/writer.rs:37-46`).

The SQLite schema stores `path`, `loc`, `modified`, imports, dependencies, named imports, namespace imports, function names, and `indexed_at` (`crates/fmm-store/src/schema.rs:82-92`). It does not store file size or content hash. The workspace dependencies include serde, serde_json, toml, and indexmap, but no bitcode or xxh3 dependency (`Cargo.toml:60-64`).

`ParserCache` is a parser instance cache, not a parsed file result cache. It stores a registry and parser instances keyed by extension (`crates/fmm-core/src/extractor/mod.rs:52-55`) and reads the entire file before parsing (`crates/fmm-core/src/extractor/mod.rs:72-89`).

The watch path uses the same timestamp check before parsing a single changed file (`crates/fmm-cli/src/cli/watch.rs:150-173`).

### Gap analysis

fallow's two tier shape can skip reads when `(mtime, size)` matches, then fall through to content hash when metadata changed or is suspect. fmm skips reads only when `indexed_at >= source_mtime`. It has no size guard, no content identity, and no cache version boundary for parse results.

The current strategy is fast for normal edit flows. It is weaker for timestamp preserving checkouts, clock skew, generated files with restored mtimes, or content changes where mtime semantics lie. It also reparses when only mtime changes and content is identical.

### Recommendation

**Adapt.** Do not lift fallow's whole bitcode file cache blindly because fmm already has SQLite as the durable store. Lift the keying model and validation sequence.

Concrete landing points:

1. Add `source_mtime`, `source_size`, `content_hash`, and `parser_cache_version` to the `files` table near the existing `indexed_at` metadata (`crates/fmm-store/src/schema.rs:82-92`).
2. Replace `load_indexed_mtimes()` with `load_file_fingerprints()` in the `FmmStore` trait, next to the current mtime API (`crates/fmm-core/src/store.rs:36-44`).
3. In Phase 1 of `generate`, check `(mtime, size, parser_cache_version)` first before reading content (`crates/fmm-cli/src/cli/sidecar.rs:113-142`).
4. On metadata mismatch, compute xxh3 on file bytes. If hash matches, update metadata without reparsing.
5. Apply the same check in `watch::index_file()` before parsing (`crates/fmm-cli/src/cli/watch.rs:150-173`).

Keep SQLite as the canonical index. Use bitcode only if a separate raw parse result cache is introduced later.

### Estimated effort

Medium. One schema migration, one new fingerprint type, store reader and writer changes, generate and watch pipeline updates, and tests for unchanged content with changed mtime.

## Finding 2. Path sorted `FileId(u32)` with compile time `size_of` assert

### Status in fmm today

fmm keys files by path strings throughout the hot data model.

`Manifest.files` is `HashMap<String, FileEntry>` (`crates/fmm-core/src/manifest/mod.rs:154-158`). Export locations carry file paths as strings through `ExportLocation` and index maps (`crates/fmm-core/src/manifest/mod.rs:158-170`). Reverse deps use `HashMap<String, Vec<String>>` (`crates/fmm-core/src/manifest/mod.rs:171-175`). `FileEntry` stores per file exports, imports, dependencies, LOC, and sidecar derived fields (`crates/fmm-core/src/manifest/mod.rs:34-72`).

The SQLite schema mirrors this shape. `files.path` is a `TEXT PRIMARY KEY`, `exports.file_path` is text, and `reverse_deps` stores `target_path` plus `source_path` text pairs (`crates/fmm-store/src/schema.rs:82-123`).

No `FileId` or `file_id` symbol exists in fmm search results, and exact source search found no `size_of` assertions in the crates. There is no measured memory layout contract for hot structs.

### Gap analysis

Path strings are stable and convenient for MCP output, but expensive as internal graph identity. They require hashing and allocation in maps, repeat path text across tables, and make dense graph storage harder.

fallow's `FileId(u32)` gives deterministic dense identity after sorting paths. It also creates a natural bridge from path based external APIs to array backed internals.

### Recommendation

**Adapt.** Add dense internal file ids while preserving path strings at public boundaries.

Suggested shape:

1. Introduce `FileId(pub u32)` in `fmm-core` with `const _: () = assert!(std::mem::size_of::<FileId>() == 4);`.
2. Assign ids after collecting and sorting canonical relative paths. `collect_files_multi()` already sorts and deduplicates (`crates/fmm-cli/src/cli/files.rs:123-136`), which is the right source of deterministic ordering.
3. Store a path table in SQLite. Use ids in internal edge, export, and reverse dependency tables.
4. Keep path strings in MCP and CLI output so no user facing protocol break leaks through.

### Estimated effort

Large. This cuts across manifest construction, store schema, reader and writer code, search helpers, MCP output adapters, and tests. It should be done before flat edge storage.

## Finding 3. Flat edge storage with `Range<u32>` per node and `size_of::<Edge>() == 32` assert

### Status in fmm today

fmm stores dependency graph state as reverse adjacency lists keyed by path string.

The in memory manifest has `reverse_deps: HashMap<String, Vec<String>>` (`crates/fmm-core/src/manifest/mod.rs:171-175`). The SQLite schema persists each reverse edge as a row in `reverse_deps(target_path, source_path)` (`crates/fmm-store/src/schema.rs:118-124`). Loading reconstructs `HashMap<String, Vec<String>>` by pushing each source into the target entry (`crates/fmm-store/src/reader.rs:291-308`). Writing deletes all reverse deps and inserts rows from a `HashMap<String, Vec<String>>` (`crates/fmm-store/src/writer.rs:329-346`).

Graph construction scans every source file, then often scans every target file for non relative dependency matching (`crates/fmm-core/src/manifest/dependency_matcher/reverse.rs:23-73`). Store rebuild creates a manifest from DB rows, computes reverse deps, converts absolute paths back to relative paths, and writes the table (`crates/fmm-store/src/writer.rs:283-326`).

`fmm_dependency_graph` resolves direct local deps from the file entry, then reads downstream through the reverse map (`crates/fmm-core/src/search/dependency_graph.rs:13-79`). Transitive graph queries use BFS with `HashSet` visited sets and `VecDeque` queues, expanding downstream through `manifest.reverse_deps` (`crates/fmm-core/src/search/dependency_graph_transitive.rs:22-168`). List files computes downstream count by looking up `manifest.reverse_deps[path].len()` (`crates/fmm-cli/src/mcp/tools/list_files.rs:93-105`).

### Gap analysis

The current representation is good for direct path keyed lookups. It is not optimized for whole graph traversal, transitive search, cycle analysis, or memory locality. Every node and edge carries string hashing overhead, and adjacency vectors are independently allocated.

fallow's flat edge storage is a better fit after fmm has dense `FileId`s. A contiguous `Vec<Edge>` plus per node ranges allows cheap scans, fewer allocations, and compact traversal state.

### Recommendation

**Adapt after Finding 2.** Avoid starting with edge flattening while paths are still the internal identity. The first milestone should create dense ids and a path table. The second should introduce a `GraphIndex` beside the existing manifest API.

Suggested shape:

1. Build `GraphIndex { nodes: Vec<Node>, edges: Vec<Edge> }` from stored file rows after manifest load.
2. Give each node upstream and downstream ranges, or build two flat edge arrays if both directions are hot.
3. Add size assertions for `FileId`, `Node`, and `Edge`.
4. Keep `Manifest.reverse_deps` as a compatibility adapter during migration, then retire it when search paths use `GraphIndex`.

### Estimated effort

Large. It depends on FileId work and touches graph building, dependency queries, list files downstream counts, transitive search, glossary reverse lookups, and persistence.

## Finding 4. `Plugin` trait with static defaults for framework presets

### Status in fmm today

fmm has a parser trait and static language descriptors. It does not have a framework plugin system.

The parser contract is `Parser: Send + Sync`, with `parse`, `parse_file`, `language_id`, and `extensions` (`crates/fmm-core/src/parser/types.rs:150-165`). `ParserRegistry` stores extension factories, language ids, descriptors, source extensions, and reexport filenames (`crates/fmm-core/src/parser/registry.rs:32-41`). Builtins are registered in one hardcoded list (`crates/fmm-core/src/parser/registry.rs:82-118`). The public `register()` method allows custom extension factories in process (`crates/fmm-core/src/parser/registry.rs:63-75`).

The static descriptor shape already resembles the useful part of fallow's static defaults. `RegisteredLanguage` stores `language_id`, `extensions`, `reexport_filenames`, and language test patterns as static slices (`crates/fmm-core/src/parser/types.rs:34-43`). TypeScript and TSX descriptors use static extension and reexport filename arrays (`crates/fmm-core/src/parser/builtin/typescript/mod.rs:327-361`). Python uses `__init__.py` and Python test naming conventions (`crates/fmm-core/src/parser/builtin/python/mod.rs:609-625`).

Config still has a hardcoded fallback language set (`crates/fmm-core/src/config/defaults.rs:31-40`), although `Config::default_with_registry()` can derive languages from the registry (`crates/fmm-core/src/config/mod.rs:71-82`).

### Gap analysis

fmm's current extension point is language parsing, not project or framework knowledge. There is no trait for framework enablers, entry patterns, virtual modules, generated files, route conventions, always used symbols, or config files.

fallow's exact plugin corpus is TS heavy and too broad for fmm. The trait shape is useful if fmm wants better framework aware indexing and glossary behavior without hardcoding rules into parser modules.

### Recommendation

**Adapt narrowly.** Preserve fmm's `Parser` and `RegisteredLanguage` model. Add a smaller `ConventionPlugin` trait for non parser conventions.

Suggested static surface:

- `id() -> &'static str`
- `languages() -> &'static [&'static str]`
- `enablers() -> &'static [&'static str]`
- `entry_patterns() -> &'static [&'static str]`
- `generated_patterns() -> &'static [&'static str]`
- `virtual_module_prefixes() -> &'static [&'static str]`
- `always_used_symbols() -> &'static [&'static str]`

Register these separately from parser factories. Use them first for test classification, reexport hubs, framework entry points, and files that should be excluded or treated as generated.

### Estimated effort

Medium. The trait and registry are small. The real work is deciding the first two or three convention plugins and wiring them into search and glossary without scope creep.

## Finding 5. Iterative Tarjan SCC over flat successor array, type only edges filtered

### Status in fmm today

fmm does not report dependency cycles as SCCs. It only prevents traversal loops.

Transitive dependency graph traversal uses BFS with `visited_up` and `visited_down` sets (`crates/fmm-core/src/search/dependency_graph_transitive.rs:31-34`, `crates/fmm-core/src/search/dependency_graph_transitive.rs:131-135`). It guards expansion by checking visited sets before pushing or accepting nodes (`crates/fmm-core/src/search/dependency_graph_transitive.rs:74-123`, `crates/fmm-core/src/search/dependency_graph_transitive.rs:146-163`). Search `depends_on` has a separate transitive dependents BFS with `seen` and `queue` (`crates/fmm-core/src/search/filter_search.rs:130-152`). Tests confirm cycles do not loop and the target file is excluded from its own result (`crates/fmm-core/src/search/tests/transitive_graph.rs:102-125`, `crates/fmm-core/src/search/tests/filters.rs:68-80`).

There is no SCC or Tarjan implementation in source search. fmm also lacks a type only edge bit. TypeScript tests intentionally include `import type` in dependencies and named imports (`crates/fmm-core/src/parser/builtin/typescript/tests/edge_cases.rs:35-66`, `crates/fmm-core/src/parser/builtin/typescript/tests/named_imports.rs:69-78`). The extraction code captures regular import statement sources and classifies relative paths as dependencies without preserving type only metadata (`crates/fmm-core/src/parser/builtin/typescript/extract_imports.rs:43-91`).

### Gap analysis

Current behavior is enough for blast radius traversal. It is not enough for cycle diagnostics because it never groups strongly connected components or distinguishes runtime cycles from type only cycles.

fallow's Tarjan implementation depends on flat successor ranges and edge metadata. fmm lacks both prerequisites today.

### Recommendation

**Skip for now. Adapt later if cycle reporting becomes a product surface.**

If adopted later, sequence it after FileId and flat graph storage:

1. Add edge kind metadata during parsing and dependency extraction. For TypeScript, preserve `import type` as type only rather than merging it into plain dependencies.
2. Build successor ranges over `FileId` edges.
3. Run iterative Tarjan to produce SCCs.
4. Expose cycles as a new query or an optional field on deep dependency graph output.

Do not add SCC detection to the current string keyed graph. It would work functionally, but it would lock in the wrong storage shape and produce noisy TS cycles until type only imports are represented.

### Estimated effort

Medium after the graph refactor. Large if done before FileId and edge metadata.

## Prioritized Punch List

1. Add file fingerprints to the SQLite index: mtime, size, content hash, cache version. Wire two tier invalidation into generate and watch.
2. Introduce `FileId(u32)` and path sorted assignment. Keep paths at CLI and MCP boundaries.
3. Build a `GraphIndex` with flat edge arrays behind existing dependency query APIs.
4. Add edge kind metadata, starting with TypeScript type only imports.
5. Add SCC cycle reporting only after flat graph and edge kind metadata exist.
6. Add a narrow convention plugin trait only when there are concrete framework rules to encode.

## Relevance to Helioy

fmm sits on Helioy's structural intelligence path. The cache and graph changes directly reduce latency for agent orientation across Helioy repos. The plugin idea should stay small until a Helioy component needs framework convention knowledge in structural queries.

## Open Questions

- Should fmm store fingerprints in the existing `files` table, or split them into a dedicated cache table for migration safety?
- Should the first `FileId` migration be in memory only before changing SQLite schema?
- Which query should own cycle reporting: `fmm_dependency_graph`, `fmm_search --depends-on`, or a new tool?
