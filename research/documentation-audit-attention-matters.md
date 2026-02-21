---
title: Documentation Audit - attention-matters
type: research
tags: [attention-matters, documentation, audit, drift]
summary: Systematic audit of CLAUDE.md, README.md, and PROJECT.md against actual codebase state at v0.1.18
status: active
source: codebase-analyst
confidence: high
created: 2026-03-21
updated: 2026-03-21
---

## Executive Summary

Audited three documentation files against the actual codebase (46 files, 21,065 LOC, 367 tests). The docs are generally solid but have accumulated drift since the architecture shifted from `rmcp` to a custom JSON-RPC implementation and several modules were extracted from `compose.rs`. Version numbers, test counts, module maps, and known-issue statuses are the primary areas needing updates.

---

## 1. CLAUDE.md Audit

### Accurate Items

- **Architecture section**: Three-crate description (`am-core`, `am-store`, `am-cli`) and their roles are correct.
- **Conventions**: `f64`, `Quaternion` derive, constants from phi/pi, OpenClaw variant, SLERP threshold - all verified in code.
- **Module descriptions**: All 14 listed modules exist and descriptions are accurate for: `constants`, `quaternion`, `phasor`, `occurrence`, `neighborhood`, `episode`, `system`, `tokenizer`, `query`, `surface`, `compose`, `batch`, `feedback`, `time`, `serde_compat`.
- **Memory section**: Accurate description of the `am` MCP server integration.

### Drift / Inaccuracies

| Item | Doc Says | Reality | Severity |
|---|---|---|---|
| `just test` command | `cargo test --workspace` | `cargo nextest run --workspace && cargo test --workspace --doc` | Medium |
| `just check` command | "clippy with warnings-as-errors" | Runs `fmt` first, then `clippy --fix --allow-dirty` | Low |

### Gaps - Missing from Module Map

| Module | File | LOC | Purpose |
|---|---|---|---|
| `scoring` | `crates/am-core/src/scoring.rs` | 501 | Neighborhood scoring logic (extracted from compose) |
| `recency` | `crates/am-core/src/recency.rs` | 159 | Recency-weighted scoring (extracted from compose) |
| `salient` | `crates/am-core/src/salient.rs` | 52 | Salient detection, extraction, typed marking |
| `activation_stats` | `crates/am-core/src/activation_stats.rs` | 10 | `ActivationStats` struct |
| `store_trait` | `crates/am-core/src/store_trait.rs` | 155 | `AmStore` trait (persistence abstraction in am-core) |

### Gaps - Missing Commands

| Command | What It Does |
|---|---|
| `just clippy` | Runs clippy separately (check = fmt + clippy) |
| `just check-pedantic` | Pedantic clippy on am-core |
| `just bench` | Criterion benchmarks for drift |
| `just bench-baseline` / `just bench-gate` | Benchmark comparison gates |
| `just release` | Release build |
| `just install` | Build release then `cargo install` |
| `just audit` | `cargo audit` |

### Suggestions

1. Add the 5 missing modules to the module map.
2. Update `just test` to reflect the nextest + doc test reality.
3. Update `just check` description to "format then clippy with auto-fix".
4. Consider listing `just bench` since criterion benchmarks exist in both `am-core` and `am-store`.

---

## 2. README.md Audit

### Accurate Items

- **Project description and origins narrative**: Accurate.
- **How it works pipeline diagram**: Matches the actual `QueryEngine` flow.
- **Architecture diagram**: Conscious/subconscious structure, phasor interference, query pipeline steps all verified.
- **Install commands**: Both npx and cargo install paths are correct.
- **MCP server section**: `am serve` is the correct command.
- **CLI commands**: All listed commands exist (query, ingest, stats, inspect, export, import, sync).
- **Math section**: Constants, mechanisms, conservation laws all verified against `constants.rs`.
- **Architecture table descriptions**: am-core ("pure math, zero I/O"), am-store ("persistence, SQLite"), am-cli ("CLI + MCP server") are accurate.
- **Development section**: `just` commands are listed (same inaccuracies as CLAUDE.md).
- **License**: MIT, confirmed in `Cargo.toml`.

### Drift / Inaccuracies

| Item | Doc Says | Reality | Severity |
|---|---|---|---|
| am-core test count | "201 tests" (architecture table) | 225 tests | Medium |
| Total test count | "253 tests" (development section) | 367 tests (225 am-core + 121 am-cli + 5 am-cli unit + 16 proptest) | High |
| MCP tools listed | 10 tools | 12 tools (missing `am_query_index`, `am_retrieve`) | High |
| `just test` | "cargo test --workspace" | Uses nextest + doc tests | Low |
| MCP server description | Implies `rmcp`-based `#[tool_router]` | Now uses custom JSON-RPC 2.0 implementation (`jsonrpc.rs`) | High |

### Gaps

1. **Missing CLI commands**: `gc`, `forget`, `init` are documented in PROJECT.md but absent from README's CLI section.
2. **Missing MCP tools**: `am_query_index` and `am_retrieve` (two-phase retrieval) are not listed in the tools line.
3. **No mention of configuration**: No `.am.config.toml` or `AM_DATA_DIR` documentation (PROJECT.md covers this well).
4. **No mention of hooks integration**: The Claude Code hooks setup for auto-sync is missing.
5. **Inspect modes**: Not shown in README (only `am inspect neighborhoods --limit 5` is shown as an example).
6. **Benchmarks**: No mention of criterion benchmarks for drift (`am-core`) or save_system (`am-store`).

### Suggestions

1. Update test count to 367 (or use "350+" to avoid future staleness).
2. Add `am_query_index` and `am_retrieve` to the MCP tools list, updating the count to 12.
3. Add `gc`, `forget`, and `init` to the CLI section.
4. Remove any implication of `rmcp` - the server is now a custom JSON-RPC 2.0 implementation over stdio.
5. Consider linking to PROJECT.md for detailed configuration documentation.

---

## 3. PROJECT.md Audit

### Accurate Items

- **Crate topology diagram**: Correct (workspace resolver = "3", edition 2024, three crates under `crates/`, npm wrapper).
- **Dependency direction**: `am-cli -> am-store -> am-core`, `am-cli -> am-core`. Verified.
- **am-core module table**: All 14 modules listed exist with accurate descriptions.
- **am-store module table**: All 6 modules listed exist (store, project, config, schema, json_bridge, error).
- **S3 manifold model description**: Accurate.
- **Key constants table**: All values verified against `constants.rs`.
- **Query pipeline**: All 7 steps (tokenize, activate, drift, interfere, couple, surface, compose) match code.
- **Ingest pipeline**: 3-sentence chunks, golden-angle phasor spacing, epoch assignment - all correct.
- **Feedback loop**: BOOST_DRIFT_FACTOR = 0.15, DEMOTE_DECAY = 2 - verified.
- **Conscious vs. subconscious**: `usize::MAX` sentinel, GC exemption - verified.
- **CLI reference**: All 11 commands listed exist.
- **Inspect modes**: All modes verified.
- **MCP tools table**: All 12 tools listed, descriptions accurate.
- **Claude Code setup command**: Correct.
- **Hooks JSON**: Correct structure.
- **Sync content rules and chunking**: EXCHANGES_PER_EPISODE = 5, content inclusion/exclusion rules verified.
- **GC description**: Floor pass, aggressive pass, exemptions, DB_GC_TARGET_RATIO (80%) all accurate.
- **npm distribution section**: Correct.
- **Conventions section**: All accurate.
- **Configuration section**: Resolution order, TOML format, env var overrides all correct.

### Drift / Inaccuracies

| Item | Doc Says | Reality | Severity |
|---|---|---|---|
| Version | "0.1.15" | `0.1.18` (`Cargo.toml` workspace.package.version) | High |
| Schema version | "Schema version 5" (appears twice) | `SCHEMA_VERSION = 7` in `schema.rs` | High |
| am-core public exports | "74 public exports" | 57 exports in `lib.rs` (could be more with re-exports, but the stated 74 is wrong) | Medium |
| am-cli server description | "rmcp `#[tool_router]`, 12 MCP tool handlers" | Custom JSON-RPC 2.0 implementation, no rmcp dependency | High |
| am-cli test LOC | "cli.rs (619 LOC)" | 701 LOC | Low |
| am-core test counts | "164 unit tests + 7 integration tests (331 LOC)" | 225 total tests, integration.rs = 329 LOC | Medium |
| am-cli test counts | "40+ integration tests split across cli.rs (619 LOC) and shutdown.rs (216 LOC)" | 121 tests across cli.rs (701 LOC), shutdown.rs (216 LOC), and new file mcp_protocol_test.rs (636 LOC) | Medium |
| Total test count | "282+ tests" | 367 tests | Medium |
| Autocheckpoint | "400KB autocheckpoint" | Code says "100 pages" (`schema.rs`) | Low |
| compose.rs LOC | "2959 LOC, 1276 production" (known issues) | 2,478 LOC (reduced after scoring/recency/salient extraction) | Medium |
| `pub fn conn()` exposure | Listed as known issue | No `pub fn conn()` found in store.rs | Fixed |
| `partial_cmp().unwrap()` panics | Listed as high-priority known issue | All instances replaced with `total_cmp()` - tests verify NaN handling | Fixed |
| N+1 load_system | Listed as high-priority known issue | Fixed: single 3-way JOIN (comment in code: "replaces the previous 1 + N + N*M query pattern") | Fixed |
| `DefaultHasher` for dedup | Listed as medium-priority known issue | `rustc-hash` (FxHasher) is a dependency; comment in server.rs references the fix | Fixed |
| Input size limits missing | Listed as medium-priority known issue | `check_input_size()` now guards `am_query`, `am_query_index`, `am_activate_response`, `am_salient`, `am_ingest`, `am_feedback`. Buffer still unchecked. | Partially Fixed |
| `activation_count += 1` wrapping | Listed as medium-priority known issue | Now uses `saturating_add(1)` in both `occurrence.rs:42` and `feedback.rs:216` | Fixed |
| pedantic clippy warnings | "163 clippy::pedantic warnings" | `just check-pedantic` exists; count may have changed | Stale count |

### Gaps - Missing from am-core Module Table

Same 5 modules missing as in CLAUDE.md: `scoring`, `recency`, `salient`, `activation_stats`, `store_trait`.

### Gaps - Missing from am-cli Module Table

| Module | File | LOC | Purpose |
|---|---|---|---|
| `colors` | `colors.rs` | 56 | ANSI color constants for CLI output |
| `generated_help` | `generated_help.rs` | 70 | Build-generated help text constants for MCP tools |
| `generated_schema` | `generated_schema.rs` | 242 | Build-generated JSON schema for MCP tool list |
| `jsonrpc` | `jsonrpc.rs` | 280 | Custom JSON-RPC 2.0 protocol: request/response types, stdio loop |
| `sync_dispatch` | `sync_dispatch.rs` | 317 | Sync dispatch logic (extracted from sync) |

### Gaps - Missing from am-store Module Table

| Module | File | LOC | Purpose |
|---|---|---|---|
| `memory_store` | `memory_store.rs` | 538 | `InMemoryStore` - in-memory implementation of `AmStore` trait |

### Gaps - Missing from Dependencies Table

| Crate | Version | Purpose |
|---|---|---|
| `rustc-hash` | 2 | Deterministic hashing (FxHasher) for dedup window |
| `proptest` | 1 (dev) | Property-based testing in am-core |
| `criterion` | 0.5 (dev) | Benchmarking framework |
| `assert_cmd` | 2 (dev) | CLI integration testing |
| `insta` | 1 (dev) | Snapshot testing |
| `predicates` | 3 (dev) | Test assertion predicates |
| `tempfile` | 3 (dev) | Temporary file/directory creation for tests |
| `indexmap` | 2 (build) | Ordered map in build script |
| `thiserror` | 2 | Error derive macro (workspace dep) |

### Gaps - Missing Test File

| File | LOC | Purpose |
|---|---|---|
| `tests/mcp_protocol_test.rs` | 636 | MCP JSON-RPC protocol-level integration tests |
| `tests/proptest.rs` | 169 | Property-based tests for am-core |

### Known Issues - Status Summary

| Issue | Status |
|---|---|
| `partial_cmp().unwrap()` NaN panics | **FIXED** - all replaced with `total_cmp()` |
| N+1 `load_system` queries | **FIXED** - single 3-way JOIN |
| `retrieve_by_ids` linear scan | Needs verification |
| Batch activation inflation | Needs verification |
| Full O(N) serialize on every write | Needs verification |
| `format!()` for SQL construction | **FIXED** - no `format!` SQL found in store.rs |
| `drain_buffer` crash window | Needs verification |
| Missing indexes | Needs verification |
| `activation_count += 1` wrapping | **FIXED** - uses `saturating_add` |
| `token_count()` hot-path allocation | Needs verification |
| `DefaultHasher` for dedup | **FIXED** - uses `rustc-hash` |
| No input size limits | **PARTIALLY FIXED** - 6 of 8 tools guarded, `am_buffer` still unchecked |
| Duplicate centroid computation | Needs verification |
| `am_feedback`/`am_batch_query` no tests | Needs verification (mcp_protocol_test.rs may cover these) |
| `pub fn conn()` exposure | **FIXED** - no longer exists |
| compose.rs god module | **PARTIALLY FIXED** - `scoring.rs`, `recency.rs`, `salient.rs` extracted. Down from 2959 to 2478 LOC |

### Suggestions

1. Bump version to 0.1.18.
2. Bump schema version to 7.
3. Replace the rmcp server description with custom JSON-RPC 2.0 implementation.
4. Add the 5 missing am-core modules, 5 missing am-cli modules, and 1 missing am-store module to their tables.
5. Update all test counts: 225 (am-core), 121 (am-cli), 367 total.
6. Add `mcp_protocol_test.rs` and `proptest.rs` to test coverage section.
7. Move fixed issues out of the Known Issues section (or mark them fixed with the version that resolved them).
8. Update the compose.rs LOC in the known issues section.
9. Add the missing dev/build dependencies to the table.
10. Recount am-core public exports (57 re-exports in lib.rs, verify if 74 includes method-level exports).

---

## Cross-Document Consistency Issues

| Topic | CLAUDE.md | README.md | PROJECT.md | Actual |
|---|---|---|---|---|
| `just test` | `cargo test --workspace` | `cargo test --workspace` | `cargo test --workspace` | `cargo nextest run --workspace && cargo test --workspace --doc` |
| Test count | not stated | 253 | 282+ | 367 |
| MCP tool count | not stated | 10 | 12 | 12 |
| Server implementation | not stated | implies rmcp | "rmcp `#[tool_router]`" | Custom JSON-RPC 2.0 |
| Version | not stated | not stated | 0.1.15 | 0.1.18 |
| Schema version | not stated | not stated | 5 | 7 |

---

## Priority Actions

**High** (factually wrong, could mislead contributors or agents):
1. PROJECT.md version: 0.1.15 -> 0.1.18
2. PROJECT.md schema version: 5 -> 7
3. All three docs: rmcp references -> custom JSON-RPC 2.0
4. README.md: add `am_query_index` and `am_retrieve` to MCP tools list
5. PROJECT.md: mark 6 fixed known issues as resolved

**Medium** (drift that accumulates confusion):
6. All three docs: update `just test` description
7. CLAUDE.md + PROJECT.md: add 5 missing am-core modules to module maps
8. PROJECT.md: add missing am-cli modules (jsonrpc, colors, generated_help, generated_schema, sync_dispatch)
9. README.md + PROJECT.md: update test counts to 367
10. PROJECT.md: add `memory_store` to am-store module table

**Low** (minor, not misleading):
11. PROJECT.md: update compose.rs LOC (2959 -> 2478)
12. PROJECT.md: add missing dev dependencies to table
13. PROJECT.md: verify remaining open known issues
