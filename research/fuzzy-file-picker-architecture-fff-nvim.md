---
title: fff.nvim — Rust-backed fuzzy file picker and MCP file search
type: research
tags: [neovim, rust, fuzzy-search, file-picker, mcp, lmdb, simd, frecency]
summary: fff.nvim is a Rust-core fuzzy file finder that exposes identical search to Neovim (via mlua), MCP clients, and Node/Bun through a shared fff-core crate; differentiators are bigram-filtered SIMD path matching, frecency+query-combo ranking, and regex-to-bigram decomposition for grep.
status: active
source: github-researcher
confidence: high
created: 2026-04-21
updated: 2026-04-21
---

## Executive Summary

`dmtrKovalenko/fff.nvim` (5,263 stars, created 2025-07-31, highly active — nightly releases) is an opinionated fuzzy file picker and live-grep engine implemented as a Rust workspace (~18k LOC Rust) with a thin Lua UI (~6.5k LOC) and an MCP server binary. The project's stated goal is "just file search, done fff well" — a narrower, faster alternative to telescope.nvim / fzf-lua for the file-picker and grep use cases, plus a first-class MCP tool for AI agents. The headline novelty is that every consumer (Neovim via mlua, MCP server, Node/Bun via C FFI) calls the same `fff-core` search engine with zero FFI overhead on the Lua and MCP sides — and the engine is built around an inverted bigram index over file contents plus SIMD-friendly chunked path storage feeding [`neo_frizbee`](https://docs.rs/neo_frizbee) for fuzzy matching.

## Architecture

### Workspace layout

Six-crate Cargo workspace (`Cargo.toml`):

| Crate | Role |
|---|---|
| `fff-core` | Search engine: indexing, watcher, scoring, grep, bigram index, frecency/query LMDB dbs. ~14k LOC. |
| `fff-query-parser` | Single-pass query → `FFFQuery { fuzzy_query, constraints }` parser. Published to crates.io. |
| `fff-grep` | Vendored subset of BurntSushi's `grep-searcher` specialised for in-memory slices. |
| `fff-nvim` | `mlua` module compiled as a `luaopen_fff_nvim` shared lib. |
| `fff-mcp` | `rmcp`-based stdio MCP server for AI agents. Calls `fff-core` directly. |
| `fff-c` | Stable C FFI wrapping `fff-core` for Node/Bun packages. |

External-facing packages under `packages/`: per-platform prebuilt-binary npm packages (`fff-bin-darwin-arm64`, `fff-bin-linux-x64-musl`, etc.), a `@ff-labs/fff-node` and `@ff-labs/fff-bun` wrapper, and a `pi-fff` (Raspberry-Pi / misc) extension.

### Language split

- **Rust (~18k LOC)** — all indexing, matching, scoring, grep, disk I/O, watching, LMDB access. Release profile uses `lto = "fat"`, `codegen-units = 1`, `mimalloc` as the global allocator.
- **Lua (~6.5k LOC)** — UI shell only. One monster file: `lua/fff/picker_ui.lua` (2,828 LOC) drives the floating-window picker. Everything else is renderers (`file_renderer.lua`, `grep_renderer.lua`, `combo_renderer.lua`), a config module, a health check, an auto-downloader for the prebuilt binary, and a preview subsystem.
- **TypeScript** — thin wrappers in `packages/fff-bun` and `packages/fff-node` that load the C FFI library via Bun's FFI or Node's N-API.

### Neovim integration path

```
Neovim (Lua) → lua/fff/picker_ui.lua
             → lua/fff/rust/init.lua  (package.loadlib of luaopen_fff_nvim)
             → crates/fff-nvim (mlua exports: init_db, init_file_picker, fuzzy_search_files,
                                 live_grep, scan_files, refresh_git_status, …)
             → crates/fff-core (FilePicker, FrecencyTracker, QueryTracker, grep, bigram)
```

Global Lazy statics in `fff-nvim/src/lib.rs` (`FILE_PICKER: SharedPicker`, `FRECENCY`, `QUERY_TRACKER`) hold `Arc<RwLock<Option<T>>>`. Comment calls this out explicitly: "the global state for neovim lives here for efficiency; lua ffi is pretty bad with the overhead of converting raw pointer into tables."

The MCP server shares the same statics pattern and calls `fff-core` APIs directly — no C FFI, no IPC beyond the MCP stdio transport.

### Indexing and watcher lifecycle

`FilePicker::new_with_shared_state` spawns a background scan thread that walks the tree with the `ignore` crate (honours `.gitignore` + `.ignore`), collecting files into a `Vec<FileItem>` sorted by `(parent_dir, filename)`. A separate `BackgroundWatcher` wraps the `notify` + `notify-debouncer-full` crates with a 250ms debounce window. On macOS above 4,096 watched paths it falls back from per-directory FSEventStreams to a single recursive watch to avoid exhausting the per-process stream limit — that kind of platform knowledge is throughout the codebase.

New files added after the initial scan land in an "overflow" partition (`base_count..` into the `files` Vec) with their own arena, so the base bigram index doesn't need rebuilding on every mutation. Deletions use tombstones (`FileItemFlags::DELETED`) to preserve bigram-index stability.

A dedicated rayon thread pool (`BACKGROUND_THREAD_POOL`, typically total − 2 threads) runs scan / warmup / bigram-build work so the main rayon pool can stay available for search.

## Key Patterns

### 1. SIMD-friendly chunked path storage

`crates/fff-core/src/simd_path.rs` stores paths as 16-byte aligned chunks (`SIMD_CHUNK_BYTES = 16`) with content-based deduplication across files, and an inline `SmallVec<[u32; 4]>` of chunk indices on each `FileItem`. `neo_frizbee` (the fuzzy matcher) consumes these chunk pointers directly — "zero-copy SIMD matching." Chunk size must stay in sync with `neo_frizbee`'s internal chunk size (comment in `simd_path.rs:7`).

A single `ArenaPtr` (raw `*const u8`) is passed to scoring closures. Safety is asserted by convention: the arena is only mutated during full re-scans, search holds a read lock.

### 2. Bigram inverted index for grep

`crates/fff-core/src/bigram_filter.rs` builds a 16-bit-keyed inverted index over file **contents** at scan time: 95 printable ASCII chars lowercased → bigram keys in `[0, 65536)`, mapped to columns in a packed bitset where each bit is a file index. Capped at `MAX_BIGRAM_COLUMNS = 5000`. For 500k files ≈ 305MB, for 50k files ≈ 30MB. Built in parallel from rayon threads using atomic `AtomicU16` column lookups and `AtomicU64` bitset words.

`crates/fff-core/src/bigram_query.rs` (998 LOC) is the novel bit: it **decomposes a regex pattern** via `regex-syntax` HIR walking into an `And`/`Or` tree of consecutive and sparse-1 (`a.b → (a,b)`) bigrams. The tree is evaluated against the bigram bitset to produce a candidate file set **before** running the real regex. The sparse-1 key is the clever part — it lets `foo.bar` prune via the cross-boundary `(o,b)` pair even though the `.` kills any consecutive cross-boundary bigram.

A `BigramOverlay` (RwLock'd) tracks file mutations since the base index was built, so edits during a session don't invalidate the index.

### 3. Query parser: constraints vs fuzzy

`fff-query-parser` is a single-pass parser that splits a query string into `FFFQuery { fuzzy_query: FuzzyQuery, constraints: Vec<Constraint> }`. The syntax is deliberately lightweight:

- `*.rs`, `*.{ts,tsx}` → `Constraint::Extension`
- `src/` → `Constraint::PathSegment`
- `**/*.rs` → `Constraint::Glob` (routed through [zlob](https://github.com/dmtrKovalenko/zlob), the author's own "fastest globbing library")
- `!foo` → `Constraint::Not(...)` (negation wrapper)
- `git:modified`, `status:staged` → `Constraint::GitStatus(...)`
- `type:rust` → `Constraint::FileType(...)`
- bare tokens → `FuzzyQuery::Parts([...])` — multi-part queries are AND-matched across parts, scores averaged

### 4. Multi-part fuzzy matching pipeline

`score.rs:match_fuzzy_parts` implements a cascading filter: first part runs SIMD match against all candidates → each subsequent part runs against only the surviving subset → final scores are averaged across parts. Early-exit when any part yields zero matches. This is noticeably smarter than FZF's multi-token OR-of-subsequences model.

### 5. Frecency with mode-specific decay

`frecency.rs` is LMDB-backed (`heed` crate) with exponential decay. Neovim mode uses a 10-day half-life (`DECAY_CONSTANT = ln(2)/10`); AI mode uses a 3-day half-life (`AI_DECAY_CONSTANT = ln(2)/3`) with a 7-day cap. Reasoning (in comments): AI sessions are shorter and more intense, so frecency should forget faster. Also separate modification-time thresholds: AI mode's "very recent" is 30s, Neovim mode's is 2 min. An `AI_MODE_COOLDOWN_SECS = 5 * 60` prevents burst-edit score inflation from AI agents.

### 6. Combo-boost from query history

`query_tracker.rs` (LMDB) records `(project_path, query) → QueryMatchEntry { file_path, open_count, last_opened }`. When the same query selects the same file ≥ `min_combo_count` (default 3) times, subsequent scores get a `combo_boost_score_multiplier` (default 100). This is a lightweight "this user always picks X for query Y" reinforcement signal, orthogonal to frecency.

### 7. Content-searched grep in frecency order

`grep.rs` drives search by iterating files **in frecency order** — most-relevant first — so pagination can early-terminate once enough results are found. Files are memory-mapped on Unix (`memmap2`), heap-buffered on Windows (Windows mmap holds file handles open and blocks editors' atomic-save-via-rename). Auto-detects definition lines (`struct`, `fn`, `class`, etc.) via a hand-rolled byte-level keyword scanner — "avoids regex overhead entirely" — so MCP output can auto-expand definition bodies for the agent's context.

### 8. Cross-mode suggestions

Novel UX: file search with zero results falls back to showing a grep suggestion for the same query (and vice versa). Labelled with a "No results found. Suggested …" banner. Selecting a grep suggestion opens the file at the match line.

## Performance Claims vs How They're Achieved

README claims work on the Linux kernel (100k files, 8GB) smoothly. The mechanisms that make that plausible:

1. **`lto = "fat"` + `codegen-units = 1`** release profile and march=native locally.
2. **`mimalloc`** as the global allocator in both `fff-nvim` and `fff-mcp`.
3. **SIMD path matching** via `neo_frizbee` consuming pre-chunked, 16-byte-aligned paths with no runtime copying.
4. **Bigram pre-filter** on grep — regex patterns are decomposed into bigram AND/OR trees that cheaply eliminate the bulk of files before any line-by-line scan.
5. **Parallel search via rayon** with a dedicated background pool so UI queries don't starve.
6. **Memory-mapped file content** on Unix for grep.
7. **Cascading multi-part matching** — subsequent query parts only scan the surviving subset.
8. **Ordered search with early termination** — frecency-sorted grep, partial `select_nth_unstable_by` for pagination when fewer than half the results are needed (`sort_and_paginate_dirs` in `score.rs`).
9. **Tombstone-on-delete + overflow partition** — avoids rebuilding the bigram index on every file mutation.
10. **LMDB** (`heed`) for frecency and query history — sub-millisecond reads, crash-safe.

There is a `chart.png` in the README showing fff-MCP beating built-in Claude Code tools. The benchmark methodology is not in-repo; treat the chart as marketing. The underlying architectural choices are solid regardless.

## Dependencies (notable)

- `neo_frizbee 0.10.1` — the fuzzy matcher. Fork/reimplementation of frizbee with SIMD and `match_end_col` support.
- `zlob 1.3.0` — author's own glob crate.
- `heed 0.22.0` — typed safe wrapper over LMDB.
- `ignore 0.4.22`, `notify 9.0.0-rc.3`, `notify-debouncer-full` (vendored fork `fff-notify-debouncer-full`).
- `git2 0.20.2` (vendored libgit2, no TLS in the workspace default).
- `mlua 0.11.1` with `luajit` and `module` features.
- `rmcp` for MCP server.
- `rayon`, `parking_lot`, `mimalloc`, `memmap2`, `ahash`, `smallvec`, `glidesort`.
- `regex-syntax 0.8` — HIR walking for regex → bigram decomposition.

## What differentiates it from similar plugins

vs **telescope.nvim** / **fzf-lua** / **snacks.picker**:

- **Scope.** Telescope is a picker framework; fff is a file finder + grep and nothing else. "Opinionated" is the author's word for it.
- **Single engine, multiple consumers.** Telescope picker pipelines run in Lua; fzf-lua shells out to fzf + ripgrep; fff-core runs in-process in Rust and is consumed identically by Neovim, MCP, and Node/Bun. That engine reuse is rare.
- **Bigram inverted index over file contents.** Telescope + ripgrep grep files directly each query; fff builds a content bigram index at scan time and uses regex → bigram decomposition (including sparse-1 bigrams) to prune the candidate set before running the regex. This is the single most unusual algorithmic idea in the repo.
- **Frecency + combo-boost baked in.** Not a plugin, not an extension — first-class in `fff-core`. Mode-specific decay constants for Neovim vs AI.
- **MCP server as a first-class target**, not a bolt-on. The MCP layer (`crates/fff-mcp/src/main.rs` `MCP_INSTRUCTIONS`) ships a prompt telling agents to "search BARE IDENTIFIERS only," "stop after 2 greps and READ the code," etc. — an opinionated prompt-engineering layer around the tool.
- **Cross-mode suggestions** — file search fallback to grep and vice versa — I haven't seen this in any other picker.

## Code Quality Signals

- **Tests:** 5,262 LOC of Rust integration tests covering bigram overlay coherence, filesystem delete handling, fuzz of file operations, grep, and watcher behaviour. Lua side has plenary tests (`tests/fff_core_spec.lua`, 129 LOC — thin).
- **Benches:** `crates/fff-core/benches/{bigram_bench,memmem_bench,parse_bench}.rs`. Criterion-based; a recent commit converted grep bench to criterion.
- **CI:** 8 workflows — `rust.yml` (test + fmt + clippy on Ubuntu + macOS, zig-built zlob), `lua.yml`, `nix.yml`, `release.yaml` (per-platform prebuilds via `cargo-zigbuild` targeting glibc 2.17 baseline + musl + aarch64 Android), `panvimdoc.yaml` (vimdoc generation), `spelling.yaml`, `stylua.yaml`, `external-tests.yml`. `clippy -- -D warnings` is enforced.
- **Docs:** rustdoc on public modules is generally good (`lib.rs` of each crate has a runnable doctest-style example). README is long and opinionated. Vimdoc auto-generated via panvimdoc.
- **Release cadence:** v0.6.1 on 2026-04-19; nightly prereleases running multiple per day (e.g. 4 nightlies on 2026-04-20). Very active.
- **Contributors:** 18 distinct authors in shallow clone, 58 open issues, active outside-contributor PRs merging daily.
- **Code hygiene:** rustfmt + clippy -D warnings + stylua + luacheck + biome (for TS). `_typos.toml` for typo linting. Nix flake for reproducible builds.
- **File-size concern:** `file_picker.rs` (2,384 LOC), `grep.rs` (2,479 LOC), `score.rs` (1,464 LOC), `picker_ui.lua` (2,828 LOC) are all well over the 700-LOC refactor-first threshold Stuart uses. Functional, but any non-trivial change in those files lands in big diffs.

## Relevance to Helioy

- **attention-matters / retrieval boosting:** frecency with mode-specific decay constants (Neovim vs AI) is a direct prior art for how to tune activation/decay for different usage patterns. The AI-mode cooldown (`AI_MODE_COOLDOWN_SECS = 5 * 60`) to prevent burst-edit score inflation is the same concern as rate-limiting AM ingestion.
- **markdown-matters (md):** the bigram inverted-index + regex-to-bigram-decomposition pattern is a viable approach to fast full-text search over md's content. The sparse-1 bigram trick would port cleanly.
- **fmm / code-nav:** the `is_definition_line` byte-level keyword scanner and `is_import_line` logic are a fast-path way to classify code lines without regex — useful pattern if fmm ever needs to do heuristic classification without parsing.
- **MCP tooling for file search:** the `MCP_INSTRUCTIONS` constant in `fff-mcp/src/main.rs` is a good reference for how to prompt-engineer tool descriptions for AI agents (tight rules, explicit wrong-pattern examples, hard stop conditions like "stop after 2 greps"). Helioy's tools could adopt this style.
- **Single engine, many consumers:** the pattern of one Rust core crate fanning out to mlua module + MCP binary + C FFI → Node/Bun is exactly what nancyr and helioy-tools are trending toward. `fff-core` plus the `shared::{SharedPicker, SharedFrecency, SharedQueryTracker}` `Arc<RwLock<Option<T>>>` pattern is a clean template.

## Sources Consulted

- `README.md` — full read
- `Cargo.toml`, `Makefile`, `.github/workflows/rust.yml`, `release.yaml` head
- `crates/fff-core/src/{lib.rs, file_picker.rs, score.rs, bigram_filter.rs, bigram_query.rs, grep.rs, frecency.rs, query_tracker.rs, simd_path.rs, background_watcher.rs, types.rs}`
- `crates/fff-nvim/src/lib.rs` (mlua exports)
- `crates/fff-mcp/src/{main.rs, server.rs}` (MCP instructions + tool handlers)
- `crates/fff-query-parser/src/lib.rs`
- `crates/fff-c/src/lib.rs` (FFI surface)
- `crates/fff-grep/src/lib.rs`
- `lua/fff/{main.lua, picker_ui.lua, rust/init.lua}`
- `gh api repos/dmtrKovalenko/fff.nvim` for stars/activity, `gh release list` for cadence, `git log` for commit history

## Open Questions

- The performance chart in README has no repro script in-repo; actual benchmark methodology vs Claude Code tools is unknown.
- `neo_frizbee` (the SIMD fuzzy matcher) — worth a deeper look as a standalone library; it appears to be the author's fork/reimplementation of frizbee.
- How big does the bigram index get in practice on Helioy-scale repos? `MAX_BIGRAM_COLUMNS = 5000` implies behaviour degrades gracefully past 5000 distinct printable bigrams (it should, since most ASCII bigrams never appear in code).
- Does the regex → bigram decomposition handle Unicode correctly? The code is explicitly ASCII-lowercased and bounded to 32..=126; non-ASCII patterns presumably fall back to `BigramQuery::Any` and skip prefiltering.
