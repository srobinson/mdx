# fmm evaluation for agent maps and code health

**Repository:** `/Users/alphab/Dev/LLM/DEV/helioy/fmm`  
**Repository SHA:** `5f8a1296d72f507a2e4bd1950001a442dc6b31fc`  
**Date:** 2026-06-17  
**Index status:** `.fmm.db` exists and `fmm validate` reported all 416 source files indexed and current.  
**Surface checked:** CLI, MCP tools, fmm-core parser, manifest, graph, search, similarity, and fmm-store SQLite schema.

## A. TASK 1 today: MAP.md for LLM agents

### Existing primitives that serve the task

fmm already has enough low level structural data to feed an agent generated codebase map.

1. **Repository topology and hotspots**
   - CLI: `fmm ls`, with directory, `--group-by subdir`, `--sort-by loc`, `--sort-by downstream`, `--filter`, `--limit`, and `--offset`.
   - MCP: `fmm_list_files`.
   - Evidence: `Commands::Ls` owns grouping, sorting, filters, pagination, and JSON output in `crates/fmm-cli/src/cli/mod.rs:571-625`. `fmm_list_files(group_by: "subdir")` on this repo returned 416 files, 63,978 LOC, with buckets for `crates/`, `fixtures/`, and `npm/`.
   - Use for MAP.md: module inventory, largest files, highest fan in files, source versus test split.

2. **File level structure**
   - CLI: `fmm outline FILE`.
   - MCP: `fmm_file_outline`.
   - Evidence: `Commands::Outline` exposes symbols, signatures, visibility, kind, private members, and JSON output in `crates/fmm-cli/src/cli/mod.rs:547-569`. The MCP tool surfaced `Commands` as a 660 line enum with command variants and line ranges in `crates/fmm-cli/src/cli/mod.rs:60-719`.
   - Use for MAP.md: entry points, public abstractions, large symbols, test modules, private helper placement.

3. **Symbol lookup and exact source reads**
   - CLI: `fmm lookup`, `fmm read`.
   - MCP: `fmm_lookup_export`, `fmm_read_symbol`.
   - Evidence: `McpServer.handle_tool_call` dispatches `fmm_lookup_export` and `fmm_read_symbol` in `crates/fmm-cli/src/mcp/mod.rs:339-354`. `fmm_read_symbol(name: "McpServer.handle_tool_call")` returned exact lines `308-393`.
   - Use for MAP.md: exact citations for key entry points and contracts without broad source reads.

4. **Dependency graph and blast radius**
   - CLI: `fmm deps FILE`, `fmm cycles`.
   - MCP: `fmm_dependency_graph`, `fmm_dependency_cycles`.
   - Evidence: `Commands::Cycles` exposes `--filter` and `--edge-mode` in `crates/fmm-cli/src/cli/mod.rs:529-545`. `fmm_dependency_graph` on `crates/fmm-core/src/parser/mod.rs` returned local dependencies, external packages, and downstream files with depth annotations. `fmm_dependency_cycles --filter source` found nine source cycles, including CLI command modules, formatter modules, manifest/store modules, parser modules, resolver modules, and store modules.
   - Use for MAP.md: module boundaries, cross crate dependencies, risky cycles, core fan in seams.

5. **Impact analysis by symbol**
   - CLI: `fmm glossary PATTERN`.
   - MCP: `fmm_glossary`.
   - Evidence: `GlossarySource` stores `file`, `lines`, `kind`, `used_by`, `namespace_callers`, and reexport metadata in `crates/fmm-core/src/manifest/glossary_builder.rs:30-52`. `fmm_glossary(pattern: "Manifest.add_file", precision: "call-site")` showed the definition at `crates/fmm-core/src/manifest/mod.rs:183-301` and source callers.
   - Use for MAP.md: key abstraction impact, imported API edges, safe refactor notes.

6. **Indexed search across exports, files, imports, dependencies, and LOC**
   - CLI: `fmm search`, `fmm exports`.
   - MCP: `fmm_search`, `fmm_list_exports`.
   - Evidence: `SearchOptions` contains `term`, `export`, `imports`, `loc`, `min_loc`, `max_loc`, `depends_on`, `directory`, and JSON output in `crates/fmm-cli/src/cli/search.rs:60-71`. `fmm search --min-loc 600` found nine files over 600 LOC, including `crates/fmm-cli/src/cli/mod.rs` and `crates/fmm-core/src/similarity.rs`.
   - Use for MAP.md: package surface discovery, large file inventory, import based subsystem grouping.

7. **Stored structural data**
   - fmm-core `Manifest` stores `files`, `export_index`, `export_locations`, `export_all`, `method_index`, `reverse_deps`, `function_index`, workspace packages, and workspace roots in `crates/fmm-core/src/manifest/mod.rs:76-126`.
   - `FileEntry` stores exports, export lines, export metadata, methods, imports, dependencies, dependency kinds, LOC, modified date, function names, named imports, namespace imports, nested functions, and closure state in `crates/fmm-core/src/manifest/file_entry.rs:36-87`.
   - The SQLite schema stores `files`, `exports`, `methods`, `reverse_deps`, `workspace_packages`, and `meta` in `crates/fmm-store/src/schema.rs:92-171`.
   - Use for MAP.md: source of truth for a generated structural model.

8. **Index refresh and validation**
   - CLI: `fmm generate`, `fmm validate`, `fmm watch`.
   - Evidence: `Commands::Generate` says existing entries update only when the source file changes, using mtime based incremental indexing in `crates/fmm-cli/src/cli/mod.rs:61-89`. `Commands::Validate` is CI oriented and exits nonzero for stale or missing files in `crates/fmm-cli/src/cli/mod.rs:109-135`. The SQLite writer stores `source_mtime`, `source_size`, `content_hash`, and `parser_cache_version` in `crates/fmm-store/src/schema.rs:105-109` and loads fingerprints in `crates/fmm-store/src/writer.rs:21-69`.
   - Use for MAP.md: rerun after commits, avoid reparsing unchanged files, fail CI when the index is stale.

### Missing for a first class MAP.md workflow

1. **No map generator or map schema**
   - No CLI command such as `fmm map`, no MCP tool such as `fmm_codebase_map`, and no stored module summary model. An agent can compose a map from primitives, but fmm does not produce a canonical MAP.md.

2. **No semantic seam extraction**
   - Current data is file, symbol, import, dependency, and LOC oriented. It does not classify architectural roles such as entry point, adapter, domain core, persistence, presentation, public API, test harness, generated file, or boundary violation.

3. **No git aware index or query surface**
   - `fmm generate` and `fmm validate` accept paths, not commits or refs. The stored schema tracks filesystem freshness and content fingerprints, not repository SHA. `build.rs` can embed `FMM_GIT_SHA` into the binary version in `crates/fmm-cli/build.rs:84-90`, and `just build-local` sets that variable from `git rev-parse --short=7 HEAD` in `justfile:15-16`, but that is binary version stamping, not index or map stamping.

4. **No structural diff across prior SHA and current SHA**
   - fmm has mtime and content hash freshness, plus `fmm watch`, but no command that compares two fmm databases, two commits, two generated maps, or two symbol graphs.

5. **No persisted map history**
   - fmm has no snapshot table keyed by SHA, no prior map pointer, no generated map cache, and no incremental map update contract.

### Feasibility of SHA stamping and incremental reruns

A fine tuned agent can build a practical MAP.md today by wrapping fmm with external Git and file persistence:

1. `sha=$(git rev-parse HEAD)`.
2. `fmm generate && fmm validate`.
3. Query `fmm_list_files`, `fmm_file_outline`, `fmm_dependency_graph`, `fmm_dependency_cycles`, `fmm_glossary`, `fmm_search`, and `fmm_read_symbol`.
4. Write MAP.md with the SHA in frontmatter or header.
5. Compare the generated file against the previous committed MAP.md with Git or a separate map diff script.

That would be useful, but fmm itself does not expose the Git or diff primitive. Incremental indexing exists at the file freshness layer. Incremental map update across commits remains external.

## B. TASK 2 today: code duplication, refactoring opportunities, and general code health

### Existing primitives that serve the task

1. **Near symbol similarity**
   - CLI: `fmm similar NAME`.
   - MCP: `fmm_find_similar`.
   - Evidence: `Commands::Similar` supports explicit `--signature`, `--kind`, `--directory`, `--limit`, `--include-tests`, and JSON output in `crates/fmm-cli/src/cli/mod.rs:425-453`. `fmm-core` implements `find_similar` in `crates/fmm-core/src/similarity.rs:102-170`, ranking by name tokens, signature shape, declaration kind, and dependency neighborhood. On this repo, `fmm_find_similar(name: "ParserRegistry")` returned similar fields and impls with signal scores.
   - Health use: catches likely reuse targets before adding code, and gives leads for similar abstractions.

2. **Dependency cycles**
   - CLI: `fmm cycles`.
   - MCP: `fmm_dependency_cycles`.
   - Evidence: `dependency_cycles_with_path_filter` is implemented in `crates/fmm-core/src/search/dependency_cycles.rs:12-45`. The tool found nine source cycles in this repo.
   - Health use: identifies modules where refactors can reduce coupling.

3. **Large files and high fan in files**
   - CLI: `fmm ls --sort-by loc`, `fmm ls --sort-by downstream`, `fmm search --min-loc N`.
   - MCP: `fmm_list_files`, `fmm_search`.
   - Evidence: `fmm_list_files(sort_by: "downstream", filter: "source")` returned `crates/fmm-core/src/parser/mod.rs` with 82 downstream files and `crates/fmm-core/src/manifest/mod.rs` with 79 downstream files. `fmm search --min-loc 600` returned nine large files.
   - Health use: prioritizes refactor targets and high risk seams.

4. **Blast radius and refactor safety**
   - CLI: `fmm deps`, `fmm glossary`.
   - MCP: `fmm_dependency_graph`, `fmm_glossary`.
   - Evidence: `fmm_dependency_graph(file: "crates/fmm-core/src/parser/mod.rs", depth: 2, filter: "source")` returned upstream and downstream closure. `fmm_glossary(pattern: "Manifest.add_file", precision: "call-site")` returned definition and source callers.
   - Health use: validates who will be affected before moving APIs or splitting files.

5. **Function and symbol size hints**
   - CLI: `fmm outline FILE`.
   - MCP: `fmm_file_outline`.
   - Evidence: outlines include symbol size and line ranges, such as `Commands` at 660 lines and `McpServer.handle_tool_call` at 86 lines.
   - Health use: surfaces large symbols and candidates for decomposition.

### Missing for real duplication and health detection

1. **No bulk clone detector**
   - `find_similar` is a targeted nearest neighbor probe. It does not enumerate all duplicate clusters, compare function bodies, compute token shingles, or report copy paste clones across the codebase.

2. **No complexity metrics**
   - fmm records LOC and symbol ranges, but not cyclomatic complexity, nesting depth, branch count, match arm count, unsafe density, async boundary count, allocation hotspots, or error handling patterns.

3. **No whole repo health score or report**
   - There is no `fmm health` command that ranks findings by severity, confidence, location, and remediation.

4. **No unused export or dead code proof**
   - `fmm_glossary` and dependency data can suggest low use, but fmm does not claim dead code. It lacks exhaustive intra file call tracing for all symbols and runtime entrypoint awareness.

5. **No architectural rule engine**
   - fmm cannot state that `cli` depends on `core` correctly, that `core` must not depend on `store`, or that generated files are exempt from size limits. Those rules need config and enforcement.

6. **No test coverage mapping by behavior**
   - Filters can separate source and tests, and dependency graph can show test dependents. fmm does not map a symbol to its exercising tests or assert coverage quality.

### Current effectiveness

A fine tuned agent can do a useful triage pass today. It can find cycles, oversized files, high fan in files, refactor blast radius, and similarity leads. It cannot do comprehensive duplicate detection or health scoring without reading source and applying its own heuristics.

## C. Concrete tooling improvements

1. **Add `fmm map` and MCP `fmm_codebase_map`**
   - Gap closed: no canonical MAP.md generator.
   - Shape:
     - Inputs: `paths`, `format` (`markdown` or `json`), `include_tests`, `max_symbols_per_file`, `include_cycles`, `include_hotspots`, `stamp_git`.
     - Output JSON: repository metadata, SHA, index timestamp, module buckets, entry points, public seams, dependency hotspots, cycles, key symbols, test surface, generated file notes.
     - Markdown output: deterministic MAP.md suitable for commit.

2. **Add index snapshots keyed by Git SHA**
   - Gap closed: no stable prior state for per commit comparisons.
   - Shape:
     - `fmm generate --snapshot --stamp-git` stores `git_sha`, branch, dirty flag, indexed paths, schema version, and generated timestamp.
     - SQLite tables: `snapshots`, `snapshot_files`, `snapshot_exports`, `snapshot_edges` or a compact serialized graph keyed by SHA.
     - MCP: `fmm_snapshot_status`.

3. **Add `fmm diff` and MCP `fmm_structural_diff`**
   - Gap closed: no diff aware rerun.
   - Shape:
     - Inputs: `base` and `head` as SHAs, snapshot IDs, DB paths, or map files.
     - Output: added, removed, moved, and changed files; added, removed, and signature changed symbols; changed dependency edges; new or resolved cycles; changed fan in; changed large symbols.
     - Markdown mode: concise change log to patch an existing MAP.md.

4. **Add `fmm health` and MCP `fmm_health_report`**
   - Gap closed: no code health rollup.
   - Shape:
     - Inputs: `paths`, `include_tests`, `ruleset`, `severity_threshold`, `json`.
     - Output: ranked findings with category, severity, confidence, file, line range, evidence, and remediation. Initial rules can cover file LOC, symbol LOC, dependency cycles, high fan in, high fan out, unstable public seam, and large test files.

5. **Add clone detection via structural fingerprints**
   - Gap closed: no real duplication detector.
   - Shape:
     - CLI: `fmm clones`.
     - MCP: `fmm_clone_clusters`.
     - Inputs: `min_tokens`, `min_similarity`, `language`, `paths`, `exclude_tests`, `normalize_names`, `normalize_literals`.
     - Output: duplicate clusters with functions, file line ranges, similarity score, shared token count, and suggested owner function.
     - Implementation: store per symbol token or AST fingerprints during parse, then cluster with deterministic locality sensitive hashing or sorted shingles.

6. **Add symbol query filters**
   - Gap closed: outlines show symbol size, but there is no repo wide symbol search by size or kind.
   - Shape:
     - CLI: `fmm symbols --kind fn --min-lines 150 --visibility public --directory crates/fmm-core/src`.
     - MCP: extend `fmm_list_exports` or add `fmm_list_symbols`.
     - Output: symbol name, file, line range, size, signature, visibility, kind, downstream count.

7. **Add architecture rule config**
   - Gap closed: no boundary enforcement.
   - Shape:
     - `.fmmrc.toml` sections: `layers`, `allowed_dependencies`, `generated_paths`, `size_limits`, `entrypoints`, `owners`.
     - CLI: `fmm lint-architecture`.
     - Output: dependency violations, cycle violations, size limit violations, missing owner or entrypoint annotations.

8. **Add map diff assisted rewrite**
   - Gap closed: agents need to patch MAP.md safely after each main commit.
   - Shape:
     - CLI: `fmm map --update MAP.md --base <sha> --head <sha>`.
     - Output: patch plan or unified diff, plus citations to structural changes.
     - Safety: fail if MAP.md header SHA does not match the supplied base.

9. **Add dead code candidate reporting with explicit confidence**
   - Gap closed: no unused export triage.
   - Shape:
     - CLI: `fmm unused --entrypoints <glob> --public-api <glob>`.
     - Output: unused candidates only, never proof, with reasons such as no named import, no dependency edge, test only, reexport only, or public API exempt.

10. **Expose stable JSON contracts for all reports**
    - Gap closed: generated agent artifacts need deterministic inputs.
    - Shape:
      - Every report command supports `--json` and includes schema version, fmm version, source SHA, query parameters, and sorted results.

## D. Verdict

**TASK 1:** partial. A fine tuned agent can write a useful first MAP.md with fmm today, but the biggest blocker is the absence of a first class map model plus Git SHA and structural diff support.

**TASK 2:** partial. A fine tuned agent can produce useful triage leads with fmm today, but the biggest blocker is the absence of bulk clone detection, complexity metrics, and a ranked health report.

## Verification log

- `git rev-parse HEAD` returned `5f8a1296d72f507a2e4bd1950001a442dc6b31fc`.
- `fmm validate` reported all 416 files indexed and current.
- `cargo metadata --no-deps --format-version 1` confirmed workspace crates `fmm`, `fmm-core`, and `fmm-store` at version `0.3.6`.
- `cargo run -q -p fmm -- --help` listed navigation commands, project commands, and MCP server support.
- `cargo run -q -p fmm -- status` reported no config file, supported extensions, workspace path, and 416 indexed source files.
- `cargo run -q -p fmm -- ls --group-by subdir --limit 10` validated topology output.
- `cargo run -q -p fmm -- similar ParserRegistry --limit 5` validated similarity output.
- `cargo run -q -p fmm -- cycles --filter source` validated source cycle reporting.
- `cargo run -q -p fmm -- search --min-loc 600 --limit 20` validated size based search.
- MCP calls used directly on this repo: `fmm_list_files`, `fmm_file_outline`, `fmm_read_symbol`, `fmm_dependency_graph`, `fmm_dependency_cycles`, `fmm_glossary`, `fmm_find_similar`, and `fmm_search`.
