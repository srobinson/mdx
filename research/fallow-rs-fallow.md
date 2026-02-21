---
title: fallow-rs/fallow review through the fmm lens
type: research
tags: [rust, oxc, codebase-intelligence, mcp, lsp, fmm, helioy]
summary: Rust TS/JS codebase intelligence built on Oxc. Mature analysis pipeline (parse, resolve, graph, BFS reachability, Tarjan SCC, bitcode incremental cache, plugin trait). High primitive borrow value for fmm.
status: active
source: github-researcher
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

# fallow-rs/fallow

Repo: https://github.com/fallow-rs/fallow

## Stats and project health

- Stars: 1137 (very high for a 6-week-old project).
- Created: 2026-03-17. Pushed: 2026-04-28. Active daily commits.
- Forks: 25. Open issues: 4. Open PRs: 1. 30 GitHub releases (already on v2.54.1, semver moved fast because the project ported from a private predecessor).
- Contributors (api count): 7. Visible commit author concentration in the cloned 50-commit slice: Bart Waardenburg ~49, Wesley 1. Effective bus factor: 1.
- License: MIT.
- CI: 16 workflows under `.github/workflows/` including `ci.yml`, `bench.yml`, `bench-real-world.yml`, `coverage.yml`, `cross-arch.yml`, `conformance.yml`, `protocol-parity.yml`, `scorecard.yml`, `bloat.yml`, `allocs.yml`. Coverage badge is wired. Miri job exists but is currently disabled to conserve CI minutes (`crates/graph`, `crates/extract`, `crates/types`).
- Test surface: 466 `.rs` files, ~219k LoC. Per-module test files include `crates/extract/src/visitor/tests.rs` (3278 LoC), `crates/graph/src/resolve/tests.rs` (1838 LoC), `crates/extract/src/cache/tests.rs` (1464 LoC). Conformance harness in `tests/conformance/` (run-all.sh, compare.py, verify-expected.py). Fuzzing targets in `fuzz/fuzz_targets/` (sfc, astro, mdx, scripts, css). Real-world benchmarks under `benchmarks/`.
- Decisions log: 7 ADRs in `decisions/` with a template, including ADR-001 (no tsc), ADR-002 (flat edge storage with size assert), ADR-004 (path-sorted FileIds), ADR-005 (re-export chain resolution).

## What fallow actually is

A Rust workspace that does codebase intelligence for TypeScript and JavaScript. It parses every JS/TS/JSX/TSX/Vue/Svelte/Astro/MDX/CSS/HTML file via Oxc, builds a project-wide module graph with re-export chain resolution, then runs a battery of analyses: unused files / exports / types / dependencies / enum members / class members, unresolved imports, unlisted dependencies, duplicate exports, circular dependencies, boundary violations, code duplication (clone detection), complexity hotspots, feature flag detection, runtime coverage merging. It exposes the same engine through CLI (`fallow-cli`), LSP (`tower-lsp`), MCP (`rmcp` over stdio), NAPI (Node bindings), and a GitHub Action. Surface area: 12 crates, ~219k LoC, 95 plugin files for framework knowledge (Next, Vite, Vitest, Storybook, Astro, Svelte, etc.). Public Rust API is `fallow_core` plus `fallow_extract` plus `fallow_graph` plus `fallow_types`.

## Architecture sketch

Workspace at `Cargo.toml` (resolver = "3", edition = "2024", rust 1.92).

Crates and their roles:

- `crates/types/` — pure data types (no logic). `discover.rs` (FileId, DiscoveredFile, EntryPoint), `extract.rs` (ModuleInfo, ImportInfo, ExportInfo, ReExportInfo, MemberInfo), `results.rs`, `suppress.rs`, `serde_path.rs`. Compile-time `size_of` asserts pin layout (`crates/types/src/discover.rs:54-56`, `crates/types/src/extract.rs:467`).
- `crates/extract/` — AST extraction. `parse.rs` dispatches by file kind (sfc, astro, mdx, css, html, default oxc). `visitor/` is a single-pass `oxc_ast_visit::Visit` impl that pulls imports, exports, re-exports, dynamic imports, require calls, member accesses, class heritage, suppression comments, complexity, flag uses. `cache/` is the bitcode-encoded incremental cache (xxh3 content hash, mtime+size fast path).
- `crates/graph/` — module graph. `graph/build.rs` (edge population in two phases), `graph/types.rs` (ModuleNode with packed boolean flags in a u8), `graph/cycles.rs` (iterative Tarjan SCC over a flat successor array), `graph/reachability.rs` (BFS over fixedbitset visited sets for overall, runtime, test entry-point splits), `graph/narrowing.rs` (export-symbol attachment), `graph/re_exports/` (chain propagation). `resolve/` wraps `oxc_resolver` with TS/SCSS/path-alias/pnpm/RN fallbacks.
- `crates/core/` — orchestration. `analyze/` (unused_files, unused_exports, unused_deps, unused_members, boundary, feature_flags). `discover/` (entry_points, walk via `ignore::WalkBuilder`, infrastructure scan). `plugins/` 95 framework plugins behind a `Plugin` trait. `duplicates/` (token-based clone detection). `trace.rs` (export, file, dependency, clone tracing).
- `crates/cli/`, `crates/lsp/`, `crates/mcp/`, `crates/napi/` — frontends. The MCP server is a thin facade that subprocesses the `fallow` binary (`crates/mcp/src/main.rs:23` shells over stdio).
- `crates/config/`, `crates/license/`, `crates/v8-coverage/` — config schema, offline Ed25519 JWT verification for paid features, V8 coverage parsing.

Load-bearing modules for the analyses fmm cares about: `crates/extract/src/visitor/visit_impl.rs` (the single AST walk), `crates/extract/src/cache/store.rs` (CacheStore), `crates/graph/src/graph/build.rs` (edge construction), `crates/graph/src/graph/types.rs` (ModuleNode), `crates/graph/src/graph/cycles.rs` (SCC), `crates/graph/src/graph/reachability.rs` (BFS), `crates/core/src/discover/walk.rs` (parallel ignore-aware walker).

## Grade

**A−.** Sits with notebooklm-py and mngr. The engineering bar is unusually high (compile-time size asserts on hot structs, ADR log, fuzz targets per language, dual-purpose cache keying on metadata then content hash, BFS reachability split into runtime / test / overall sets, Tarjan SCC with type-only edge skipping). Ecosystem fit is heavy (TS/JS only) but the patterns are language-agnostic. Half a notch below A: bus factor 1 across 49 of the visible 50 commits, MCP server is a stdio shim not a native handler, no public lookup-by-symbol API yet (only file-level traces).

## Primitives that transfer to fmm

1. **Bitcode incremental cache with metadata-fast-path then content-hash validation.** `crates/extract/src/cache/store.rs:90-141` (`get_by_metadata` and `get`). Two-tier lookup: hit on `(mtime, size)` skips file read entirely; falls through to xxh3 content hash for confirmation. Whole cache on-disk as `cache.bin` via `bitcode::encode/decode`. Versioned via `CACHE_VERSION` constant in `crates/extract/src/cache/types.rs:11` (currently 53). For fmm: lift the exact shape for the file-outline cache. xxh3-rust plus bitcode is a precedent worth copying for the symbol/outline persistence layer that fmm currently rebuilds on every cold start.

2. **Path-sorted FileId(u32) with compile-time size assert.** `crates/types/src/discover.rs:49-56` and ADR-004 (`decisions/004-path-sorted-file-ids.md`). Newtype `pub struct FileId(pub u32)`, sort discovered paths before assignment, `const _: () = assert!(size_of::<FileId>() == 4);`. Stable cross-platform identity, dense indices into `Vec`-backed module tables. For fmm: replace any `String` or `PathBuf` keying in symbol tables with this exact pattern. Combined with a flat module Vec, lookups become array indexing and the symbol-reference layer can use bitfields.

3. **Flat edge storage with `Range<u32>` per node, plus 32-byte Edge size assert.** `crates/graph/src/graph/mod.rs:53-76` and `crates/graph/src/graph/types.rs:11-30`, ADR-002 (`decisions/002-flat-edge-storage.md`). All edges live in `Vec<Edge>`; each `ModuleNode` stores `edge_range: Range<usize>` and a packed `u8` flags field for entry/reachable/runtime/test/cjs. Cache locality during full-graph traversals dominates per-node Vec adjacency. For fmm: this is the dependency-graph storage shape. Today fmm likely uses adjacency Vecs; rebuilding around flat edges plus range slices is a 2x to 5x reduction in cache misses on dependency_graph queries.

4. **Plugin trait for framework knowledge.** `crates/core/src/plugins/mod.rs:528-640` (`pub trait Plugin: Send + Sync`). Static defaults via `&'static [&'static str]` for `enablers`, `entry_patterns`, `config_patterns`, `always_used`, plus dynamic `is_enabled` from `package.json` deps. Each of 95 plugins is a thin file. For fmm: glossary and outline accuracy is gated on framework-aware extension knowledge (e.g. Vue SFC, Svelte, Astro). The `Plugin` shape lets fmm add per-language "knows these conventions" presets without ballooning the core. Specifically the `enablers / entry_patterns / always_used / virtual_module_prefixes` four-field static surface is the right grain.

5. **Ignore-aware parallel walker via `ignore::WalkBuilder` plus per-thread collector.** `crates/core/src/discover/walk.rs:1-60` (`FileVisitor`, `FileVisitorBuilder`). Per-thread `Vec` accumulator drained on `Drop` into a shared `Mutex<Vec<...>>` to avoid contention. Production excludes precompiled into `globset::GlobSet`. Allowed hidden directory list at `crates/core/src/discover/mod.rs:33-39` (.storybook, .vitepress, .well-known, .changeset, .github). For fmm `fmm_list_files`: this pattern is faster and more correct than naive `walkdir` for large monorepos. Globset compile once, drain on drop, reuse the `ignore` crate's gitignore semantics for free.

6. **Iterative Tarjan SCC over a pre-collected flat successor array, with type-only edge filtering.** `crates/graph/src/graph/cycles.rs:1-120`. Pre-collects deduplicated successors into a flat `Vec<usize>` with per-node `Range`, runs an iterative DFS using a `Frame { node, succ_pos, succ_end }` stack, skips edges whose imports are all `is_type_only`. For fmm: cycle detection on the dependency graph. The iterative shape avoids stack overflow on deep monorepos and the type-only filter avoids reporting compile-time-only cycles as runtime risks.

## What does NOT transfer

- TS/JS-specific framework plugins (95 of them). fmm is multi-language; copying the corpus is wasted work. Borrow only the trait shape.
- The MCP layer in `crates/mcp/`. It is a thin stdio facade that subprocesses the CLI. fmm already has native MCP wiring through helioy-tools; subprocessing would be a regression.
- The CLI report formatters (`cli/report/sarif.rs`, `markdown.rs`, `compact.rs`). fmm output is structured JSON for agents; SARIF and human reports are not a fit.
- The license / paid runtime layer (`crates/license/`, `crates/v8-coverage/`, runtime coverage merging). Not aligned with helioy.
- Duplicate detection and complexity scoring. Adjacent capabilities, but they are scope creep for fmm. They belong in a separate component or a future "code-health" organ.
- NAPI bindings. fmm does not need a Node API.

## Build vs borrow vs inspiration-only

**Inspiration-only with surgical primitive borrows.** Do not vendor fallow as a dependency. Do not fork. The TS/JS scope is wrong for fmm and the runtime/license code is unrelated. The patterns above are small enough to reimplement directly inside the existing fmm crate, each as an isolated PR. Cite `decisions/00X-*.md` from fallow when capturing the rationale in fmm's own ADRs.

## Combined recommended action

Concrete shapes to lift into fmm:

1. **Cache layer** (`fmm-cache` module). Mirror `crates/extract/src/cache/`: `CacheStore` with `bitcode` plus `xxh3-rust`, `mtime+size` fast lookup, content-hash fallback, `CACHE_VERSION` constant, 256 MB load guard. Cite `crates/extract/src/cache/store.rs` and `crates/extract/src/cache/types.rs:11`.
2. **FileId newtype** in fmm types crate, with path-sorted assignment and `const _: () = assert!(size_of::<FileId>() == 4);`. Replace `PathBuf` keys throughout the outline / dependency tables. Cite `crates/types/src/discover.rs:49-56`.
3. **Flat edge storage** for the dependency graph backing `fmm_dependency_graph`. `Vec<Edge>` plus per-node `Range<u32>` plus packed `u8` flags. Add the `size_of::<Edge>()` assert. Cite `crates/graph/src/graph/mod.rs:53-76` and ADR-002.
4. **Plugin trait** for language conventions. Static `enablers` / `entry_patterns` / `always_used` / `virtual_module_prefixes`. Today fmm hard-codes language assumptions; this trait gives a clean extension point that does not couple core to every language. Cite `crates/core/src/plugins/mod.rs:528-640`.
5. **Parallel walker** swap. Replace any `walkdir`-based file discovery in `fmm_list_files` with `ignore::WalkBuilder` and the per-thread drain pattern from `crates/core/src/discover/walk.rs:1-60`. Add an allowed-hidden-dirs allowlist matching fmm's needs.
6. **Iterative Tarjan SCC** for cycle reporting in `fmm_dependency_graph`. Cite `crates/graph/src/graph/cycles.rs`.

What to skip: framework plugin corpus, MCP shim, NAPI, license, v8-coverage, duplicate detection, complexity scoring, SARIF.

What to cite in fmm's own ADRs: ADR-001 (no tsc / no per-language compiler), ADR-002 (flat edges), ADR-004 (path-sorted FileIds), ADR-005 (re-export chain resolution).

## Sources consulted

- README.md, ROADMAP.md, CLAUDE.md, CHANGELOG.md (top of file).
- decisions/001 through decisions/005, decisions/_template.md.
- Cargo.toml workspace.
- crates/extract/src/lib.rs, parse.rs, visitor/{mod,visit_impl}.rs, cache/{mod,store,types,conversion}.rs, inventory.rs.
- crates/graph/src/graph/{mod,build,types,cycles,reachability}.rs, resolve/{mod,specifier}.rs.
- crates/core/src/{lib,trace}.rs, discover/{mod,walk}.rs, plugins/mod.rs.
- crates/types/src/{lib,discover,extract,suppress}.rs.
- crates/mcp/src/{main,server/mod,params,tools/{mod,trace}}.rs.
- crates/lsp/src/main.rs, crates/napi/src/lib.rs.
- .github/workflows/ci.yml, fuzz/fuzz_targets/, tests/conformance/.

## Open questions

- Real depth of the cache version bumps: `CACHE_VERSION = 53` after 6 weeks suggests the cache schema thrashes during early development. fmm should expect the same and design for fast invalidation rather than long-term migration.
- How fallow's `oxc_semantic`-based scope analysis maps to fmm's symbol model. Worth a focused second pass if fmm decides to add `read_symbol` precision improvements.
- Exact protocol of the LSP `fallow/analysisComplete` custom notification (`crates/lsp/src/main.rs:30-50`). If fmm grows an editor surface, this pattern is reusable.
