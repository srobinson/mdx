---
title: frontmatter-matters Architecture Alignment Spec
date: 2026-03-18
tags: [frontmatter-matters, architecture, alignment, rust, mcp, workspace]
type: spec
status: active
---

# frontmatter-matters Architecture Alignment Spec

Alignment plan between the current frontmatter-matters codebase (v0.1.41) and the Helioy Rust Architecture Proposal.

## 1. Executive Summary

**Today**: frontmatter-matters is a single-crate Rust monolith (edition 2021) with 42,224 LOC across 147 indexed files. It parses source files using tree-sitter (17 language grammars), extracts structural metadata (exports, imports, dependencies, line ranges), stores the index in SQLite (rusqlite, bare), and serves queries via both a CLI (clap) and an MCP stdio server (manual JSON-RPC + tools.toml + build.rs). It has 907 tests, CI with clippy/fmt/test/release-build, release-please with cross-compilation builds for 5 targets, and npm publishing.

**Where the proposal wants it to go**: Split into a workspace with fmm-core/fmm-store/fmm-cli, adopt workspace inheritance, upgrade to edition 2024/resolver 3.

**Key architectural difference from attention-matters**: fmm's storage model is a batch-indexed cache, not a transactional persistence layer. During `fmm generate`, the extractor writes parsed metadata to SQLite. At serve time, `Manifest::load()` reads the entire index into memory as a `Manifest` struct. All MCP tool handlers and CLI commands operate on this in-memory `Manifest`. The MCP server reloads the Manifest from SQLite on each `tools/call` request (to pick up re-indexes from file watchers), but individual tool handlers never touch rusqlite. This means the store trait is a loader/writer boundary (how to get a Manifest in and out of storage), not a per-operation persistence port like `AmStore` in attention-matters.

**What is already aligned**: Manual JSON-RPC + tools.toml + build.rs for MCP (no rmcp migration needed). thiserror already in dependencies. Release profile with lto/codegen-units=1/strip/opt-level=3. release-please with conventional commits. CI with dtolnay/rust-toolchain + Swatinem/rust-cache.

**Gaps concentrated in three areas**: (1) single-crate monolith needs workspace split, (2) edition 2021 needs 2024 upgrade, (3) no store trait boundary exists.

## 2. Current State Analysis

### 2.1 Module Inventory

```
src/                          103 files   31,135 LOC
  main.rs                                    191 LOC   Binary entrypoint, clap dispatch
  lib.rs                                      10 LOC   Module re-exports
  cli/                         19 files    3,747 LOC   CLI commands, clap, generate pipeline,
                                                       watch, init, status, file collection
  mcp/                         13 files    3,720 LOC   MCP server + tool handlers + tests
  parser/                      30 files   11,095 LOC   Tree-sitter grammars (17 langs)
  manifest/                    10 files    3,519 LOC   In-memory index + dependency matching
  search/                       7 files    1,653 LOC   Query engine (bare, filter, graph)
  format/                       5 files    1,139 LOC   Output formatters (YAML, list, search)
  db/                           4 files    1,702 LOC   SQLite reader/writer + schema
  config/                       1 file       484 LOC   .fmmrc.toml configuration
  extractor/                    1 file        90 LOC   File processor + parser cache
  resolver/                     2 files      584 LOC   Cross-package import resolution
tests/                          9 files    8,411 LOC   Integration tests
fixtures/                      23 files    1,617 LOC   Test fixtures
benches/                        1 file       372 LOC   Parser benchmarks
```

### 2.2 Public API Surface

**Domain types** (all in src/manifest/mod.rs and src/parser/mod.rs):
- `Manifest` (39 fields, 12 public methods) -- central in-memory index
- `FileEntry` (12 fields) -- per-file metadata
- `ExportLines` -- line range for a symbol
- `ExportLocation` -- file path + optional line range
- `ExportEntry` (7 fields, 4 methods) -- parser output per export
- `Metadata` (8 fields, 1 method) -- parser output per file
- `ParseResult` -- raw parser output (tree + metadata)
- `Parser` trait -- language parser interface (fn name, fn parse)
- `ParserRegistry` (11 public methods) -- language registration and lookup
- `RegisteredLanguage` -- registered parser entry
- `LanguageTestPatterns` -- per-language test file detection
- `Config` (5 public methods) -- runtime configuration
- `GlossaryEntry`, `GlossaryMode`, `GlossarySource` -- glossary types

**Database layer** (src/db/):
- `open_or_create(root) -> Connection` -- create/migrate DB for indexing
- `open_db(root) -> Connection` -- open existing DB for reading
- `reader::load_manifest_from_db(conn, root) -> Manifest` -- load full index
- `writer::*` -- 12 public functions for writing index data

**MCP server** (src/mcp/mod.rs):
- `McpServer` (4 public methods: new, with_root, call_tool, run)
- `JsonRpcError` -- error type
- 8 tool handlers in src/mcp/tools/

**Search layer** (src/search/):
- `bare_search`, `filter_search`, `dependency_graph`, `dependency_graph_transitive`
- Query types: `BareSearchResult`, `FileSearchResult`, `ExportHit`, `SearchFilters`

**Format layer** (src/format/):
- 15 formatter functions (format_list_files, format_file_outline, etc.)

### 2.3 Dependency Inventory

| Category | Dependencies |
|----------|-------------|
| Tree-sitter grammars (17) | tree-sitter, tree-sitter-typescript, -python, -rust, -go, -java, -cpp, -c-sharp, -ruby, -php, -c, -zig, -lua, -scala, -swift, -kotlin-ng, -elixir, -dart-orchard, streaming-iterator |
| CLI | clap (derive, cargo), clap_complete, clap_mangen, clap-markdown, color-print, colored |
| File handling | ignore, notify, notify-debouncer-full, ctrlc |
| Parallelism | rayon, indicatif (rayon feature) |
| Database | rusqlite (bundled) |
| Serialization | serde (derive), serde_json, toml (parse) |
| Date/time | chrono (serde) |
| Error handling | anyhow, thiserror |
| Pattern matching | regex, glob |
| Cross-package resolution | oxc_resolver |
| Build deps | toml, serde, serde_json, indexmap (serde) |
| Dev deps | tempfile, criterion, rusqlite |

### 2.4 Test Inventory

**907 tests total** (all passing), distributed across:

| Suite | Count | Type |
|-------|-------|------|
| Unit tests (src/) | 615 | Parser tests, MCP tool tests, search tests, manifest tests, writer tests, formatter tests |
| tests/cross_language_validation.rs | 105 | Multi-language parser validation |
| tests/edge_cases.rs | 57 | Edge case coverage |
| tests/mcp_tools.rs | 41 | MCP tool integration |
| tests/glossary.rs | 25 | Glossary feature |
| tests/fixture_validation.rs | 23 | Fixture-based validation |
| tests/cli_integration.rs | 14 | CLI integration |
| tests/cross_package_resolution.rs | 12 | Cross-package imports |
| tests/named_import_precision.rs | 8 | Named import precision |
| tests/cli_flags.rs | 7 | CLI flag parsing |

### 2.5 CI/CD

- **ci.yml**: fmt, clippy, test, release build, generated docs sync check
- **release.yml**: release-please + cross-compilation (5 targets: aarch64-apple-darwin, x86_64-apple-darwin, x86_64-unknown-linux-gnu, aarch64-unknown-linux-gnu, x86_64-pc-windows-msvc) + npm publish
- **docs.yml**: documentation deployment

## 3. Gap Analysis

### 3.1 Workspace Layout

**Current state**: Single `[package]` Cargo.toml. All code in one crate.

**Target state**: Virtual manifest with `crates/fmm-core/`, `crates/fmm-store/`, `crates/fmm-cli/`.

**Gap severity**: **High**. This is the primary structural change. The single Cargo.toml mixes 17 tree-sitter parsers, CLI deps (clap, colored, clap_complete, clap_mangen, clap-markdown, color-print), file-watching deps (notify, ctrlc), database deps (rusqlite), and cross-package resolution (oxc_resolver). Splitting isolates concerns and enables parallel compilation of independent crates.

### 3.2 Edition and Resolver

**Current state**: Edition 2021, no explicit resolver (defaults to 2).

**Target state**: Edition 2024, resolver 3.

**Gap severity**: **Low**. Mechanical change. Edition 2024 is backwards-compatible with 2021 for the patterns fmm uses. Resolver 3 is the default for edition 2024 workspaces.

### 3.3 Store Trait Boundary

**Current state**: No trait boundary. `Manifest::load()` calls `db::open_db()` then `db::reader::load_manifest_from_db()` directly. The MCP server holds an `Option<Manifest>` and calls `Manifest::load()` on reload. The write path in `cli::generate` calls `db::writer::*` functions directly, passing a `&Connection`.

**Target state**: A store trait in fmm-core that abstracts the "load a Manifest from storage" and "persist indexed data to storage" operations. This enables fmm-core to remain zero-I/O while fmm-store provides the SQLite adapter.

**Gap severity**: **Medium**. The current coupling between Manifest and db is tight but localized. The MCP server and CLI commands consume `Manifest` (in-memory), not the database directly. The trait boundary is at the Manifest loading/writing edge, not spread across dozens of call sites like in attention-matters.

**Architectural note**: fmm's access pattern is fundamentally batch-oriented:
1. **Write path** (`fmm generate`): Parse all files with rayon, serialize to SQLite via `db::writer::*`
2. **Read path** (`fmm serve` / any query command): Load entire Manifest from SQLite into memory, answer queries from RAM

This means the trait surface is narrow: load a Manifest, write indexed data. Individual query operations (search, glossary, dependency graph) operate purely on the in-memory `Manifest` and never touch the database.

### 3.4 Error Handling

**Current state**: `thiserror` is already a dependency (v2.0). However, inspection needed to confirm all error types use thiserror derives vs manual impls.

**Gap severity**: **Low**. thiserror is already present. Any manual error types can be mechanically migrated.

### 3.5 Testing Infrastructure

**Current state**: 907 tests using `cargo test`. No cargo-nextest. No insta snapshot tests. MCP tool tests exercise handlers via `McpServer::call_tool()` (in-process, bypassing JSON-RPC). CLI integration tests in `tests/cli_integration.rs` and `tests/cli_flags.rs`.

**Target state**: cargo-nextest, insta snapshot tests for MCP response format stability, subprocess MCP protocol tests via assert_cmd.

**Gaps**:
- No cargo-nextest in justfile or CI
- No insta snapshot tests for tool response structures
- No subprocess-level MCP protocol tests (the existing mcp/tests.rs uses call_tool(), not stdio)
- Benchmarks exist (criterion) but only for parser performance

### 3.6 Justfile Recipes

**Current state**: Has build, test, fmt, clippy, check, install, ci, gen-docs, release. Uses `cargo test` not nextest. Missing `--workspace` flags (irrelevant today, required after workspace split).

**Gap severity**: **Low**. Mechanical update after workspace split.

## 4. Target Workspace Layout

```
fmm/
  Cargo.toml              # Virtual manifest: [workspace] only
  Cargo.lock
  justfile
  tools.toml              # Single source of truth (stays at root)
  build.rs                # Generates into crates/fmm-cli/src/
  .fmmrc.toml             # Runtime config (stays at root)
  crates/
    fmm-core/
      Cargo.toml
      src/
        lib.rs
        types.rs           # Manifest, FileEntry, ExportLines, ExportLocation
        parser/            # Parser trait, ExportEntry, Metadata, ParseResult,
          mod.rs             ParserRegistry, RegisteredLanguage, LanguageTestPatterns,
          builtin/           all 17 language parsers, query_helpers, template
            mod.rs
            typescript/
            python/
            rust/
            go.rs
            java.rs
            ... (all language modules)
        search/            # Query engine: bare_search, filter_search,
          mod.rs             dependency_graph, dependency_graph_transitive,
          ...                SearchFilters, BareSearchResult, etc.
        manifest/          # Manifest operations: add_file, remove_file,
          mod.rs             validate_file, rebuild_reverse_deps,
          dependency_matcher.rs   dependency matching, glossary building,
          glossary_builder.rs     call_site_finder, private_members
          call_site_finder/
          private_members/
        format/            # All formatters: YAML, list, search output
          mod.rs
          ...
        config.rs          # Config, TestPatterns
        extractor.rs       # FileProcessor, ParserCache
        resolver/          # CrossPackageResolver, workspace resolver
          mod.rs
          workspace.rs
        error.rs           # Domain error types (thiserror)
        store.rs           # FmmStore trait definition
    fmm-store/
      Cargo.toml
      src/
        lib.rs
        schema.rs          # CREATE_SCHEMA_SQL, schema version, migrations
        reader.rs          # load_manifest_from_db, load_files, load_exports, etc.
        writer.rs          # upsert_file_data, serialize_file_data, etc.
        connection.rs      # open_or_create, open_db, apply_pragmas
        error.rs           # StoreError (thiserror, wraps rusqlite::Error)
    fmm-cli/
      Cargo.toml
      src/
        main.rs            # Clap dispatch, error printing
        cli/               # All CLI command handlers
          mod.rs             generate, validate, clean, watch, init, status,
          ...                search, glossary, lookup, read, deps, outline, ls, exports
        mcp/               # MCP server + tool handlers
          mod.rs             McpServer<S: FmmStore>, JsonRpcRequest/Response/Error,
          tools/             run(), handle_request(), handle_tool_call()
          schema.rs
          args.rs
          generated_schema.rs  # Generated by build.rs
        generated_help.rs  # Generated by build.rs
  tests/                   # Integration tests (stay at workspace root or move to fmm-cli)
  fixtures/                # Test fixtures
  benches/                 # Parser benchmarks (move to fmm-core)
  examples/
  .github/
    workflows/
      ci.yml
      release.yml
      docs.yml
```

## 5. fmm-core Crate Spec

### 5.1 Purpose

Pure domain logic. Zero I/O dependencies. No rusqlite, no tokio, no filesystem (except tree-sitter parsing which reads file content passed to it, not files directly), no network.

**Exception**: tree-sitter grammars link native C code at compile time. This is a build-time dependency, not a runtime I/O dependency. The parser functions receive `&str` content, not file paths.

**Exception**: `oxc_resolver` performs filesystem operations for cross-package import resolution. This stays in fmm-core because it is intrinsic to the parsing domain (resolving import paths to actual files). It is not a persistence concern.

**Exception**: `FileProcessor` in `src/extractor/mod.rs` calls `std::fs::read_to_string(path)` to load file content before passing it to tree-sitter parsers. This is runtime filesystem I/O inside fmm-core. Accepted as a pragmatic exception for the initial split. A future refinement could refactor `FileProcessor` to receive `&str` content from the caller, pushing file I/O to fmm-cli. Not blocking for the workspace migration.

**Note**: The `ignore` crate (gitignore-aware file walking) is used only in `src/cli/files.rs`, which stays in fmm-cli. No `ignore` dependency in fmm-core.

### 5.2 Module Structure

```rust
// fmm-core/src/lib.rs
pub mod types;       // Manifest, FileEntry, ExportLines, ExportLocation,
                     //   PreserializedRow, ExportRecord, MethodRecord
pub mod parser;      // Parser trait, ExportEntry, Metadata, ParseResult,
                     //   ParserRegistry, all 17 language modules
pub mod search;      // Query engine (operates on &Manifest)
pub mod manifest;    // Manifest operations, dependency matching,
                     //   glossary building, call_site_finder, private_members
pub mod format;      // Output formatters
pub mod config;      // Config, TestPatterns
pub mod extractor;   // FileProcessor, ParserCache
pub mod resolver;    // CrossPackageResolver, workspace resolution
pub mod error;       // FmmError (thiserror)
pub mod store;       // FmmStore trait

/// Crate version, exposed for fmm-store's `write_meta` implementation.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
```

### 5.3 FmmStore Trait

The trait captures fmm's two-phase access pattern: batch write during indexing, full load during serving.

**Critical design constraint**: The generate hot path uses a two-phase pipeline: `serialize_file_data` (parallel via rayon, pure CPU, returns `PreserializedRow`) then `upsert_preserialized` (sequential, wrapped in a single SQLite transaction for thousands of files). If the trait exposes per-file writes, each call becomes its own implicit transaction, destroying batch performance on large codebases. The trait must preserve batch semantics.

```rust
// fmm-core/src/store.rs

use crate::types::{Manifest, PreserializedRow};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

/// Persistence port for fmm's indexed data.
///
/// fmm's storage model is batch-oriented:
/// - Write path: `fmm generate` parses files in parallel (rayon),
///   serializes to `PreserializedRow`, then batch-writes to storage
///   inside a single transaction.
/// - Read path: `fmm serve` loads the entire Manifest into memory.
///
/// Implementors: `SqliteStore` (production), `InMemoryStore` (tests).
pub trait FmmStore {
    type Error: std::error::Error + Send + Sync + 'static;

    // --- Read path ---

    /// Load the complete Manifest from storage.
    ///
    /// Returns the full in-memory index. All query operations
    /// operate on the returned Manifest, not on the store directly.
    ///
    /// # Errors
    /// Returns an error if the store does not exist or the schema
    /// version is incompatible.
    fn load_manifest(&self) -> Result<Manifest, Self::Error>;

    // --- Write path (indexing) ---

    /// Load the map of previously indexed file modification times.
    ///
    /// Returns (path -> mtime_rfc3339) for all indexed files.
    /// Used by the incremental indexer to skip unchanged files.
    ///
    /// # Errors
    /// Returns an error on storage access failure.
    fn load_indexed_mtimes(&self) -> Result<HashMap<String, String>, Self::Error>;

    /// Batch-write indexed file data.
    ///
    /// Accepts pre-serialized rows (produced by the parallel parse
    /// pipeline) and writes them within a single transaction. When
    /// `full_reindex` is true, deletes all existing file data before
    /// writing (the current `delete_all_files` + insert pattern).
    ///
    /// This is the primary write path for `fmm generate`. The
    /// implementor must wrap the entire batch in a transaction for
    /// performance (thousands of files per invocation).
    ///
    /// # Errors
    /// Returns an error on storage write failure.
    fn write_indexed_files(
        &self,
        rows: &[PreserializedRow],
        full_reindex: bool,
    ) -> Result<(), Self::Error>;

    /// Write or update a single file's indexed data.
    ///
    /// Used by `fmm watch` for incremental single-file updates.
    /// Implementors may use an implicit transaction for the single write.
    ///
    /// # Errors
    /// Returns an error on storage write failure.
    fn upsert_single_file(
        &self,
        row: &PreserializedRow,
    ) -> Result<(), Self::Error>;

    /// Remove a single file's indexed data by relative path.
    ///
    /// Used by `fmm watch` when a file is deleted from the filesystem.
    /// Returns true if a row was actually deleted, false if the file
    /// was not in the index.
    ///
    /// # Errors
    /// Returns an error on storage access failure.
    fn delete_single_file(
        &self,
        rel_path: &str,
    ) -> Result<bool, Self::Error>;

    /// Rebuild and persist the reverse dependency graph.
    ///
    /// Called after all files are indexed. The provided Manifest must
    /// reflect the current stored state (i.e., call after
    /// `write_indexed_files`, not before). The implementor computes
    /// downstream dependents and persists the graph.
    ///
    /// # Errors
    /// Returns an error on storage write failure.
    fn rebuild_and_write_reverse_deps(
        &self,
        manifest: &Manifest,
        root: &Path,
    ) -> Result<(), Self::Error>;

    /// Write or update workspace package entries.
    ///
    /// # Errors
    /// Returns an error on storage write failure.
    fn upsert_workspace_packages(
        &self,
        packages: &HashMap<String, PathBuf>,
    ) -> Result<(), Self::Error>;

    /// Write storage metadata (fmm version, generated_at timestamp).
    ///
    /// The implementor reads the fmm version from fmm-core (e.g.,
    /// `fmm_core::VERSION`) and computes the current timestamp
    /// internally. This encapsulates metadata concerns within the
    /// store boundary.
    ///
    /// # Errors
    /// Returns an error on storage write failure.
    fn write_meta(&self) -> Result<(), Self::Error>;
}
```

**`PreserializedRow` moves to fmm-core.** Currently defined in `db/writer.rs`, this is a pure data struct (path, serialized JSON strings, LOC, mtime) with no rusqlite dependency. It is the intermediate representation between the parallel parse pipeline (fmm-core concern) and the storage write (fmm-store concern). Moving it to `fmm-core/src/types.rs` makes the trait self-contained.

**Methods intentionally excluded from the trait:**

- **`is_file_up_to_date`**: The actual function never fails (returns `bool`, swallows query errors). The main generate path uses `load_indexed_mtimes` for batch comparison, not per-file checks. This function is only used in dry-run and watch modes. It stays as a convenience method on `SqliteStore`, not on the trait.

- **`file_mtime_rfc3339`**: Lives in `db/writer.rs` but performs filesystem I/O (`std::fs::metadata`), not database I/O. Moves to fmm-cli as a utility function during the migration.

- **`serialize_file_data`**: Pure CPU transformation (`ParseResult -> PreserializedRow`). This belongs in fmm-core, not behind the store trait. The CLI's parallel pipeline calls this, then passes the results to `write_indexed_files`.

**Design rationale**:

1. **Narrow read surface**: Only `load_manifest()`. All query operations (search, glossary, dependency graph, list files, etc.) operate on the returned `Manifest`, not on the store. This matches fmm's architecture where the database is a serialization format, not a query engine.

2. **Batch write semantics**: `write_indexed_files` accepts pre-serialized rows and handles transactions internally. This preserves the current performance characteristics where thousands of files are written in a single transaction. `upsert_single_file` provides the watch-mode path separately.

3. **Sync signatures**: rusqlite is sync. No async impedance mismatch.

4. **Associated error type**: fmm-core is zero-I/O and cannot depend on rusqlite. `SqliteStore` sets `type Error = StoreError` (wrapping `rusqlite::Error`). `InMemoryStore` uses a lightweight test error.

5. **`&self` not `&mut self`**: The SQLite store uses internal connection management. Write operations use transactions internally. WAL mode (already enabled via pragmas) permits `&self` for writes.

6. **`write_meta` is parameterless by design**: The store reads the fmm version from a `fmm_core::VERSION` constant and computes the timestamp internally. This encapsulates metadata concerns. The version string can also be accepted at `SqliteStore` construction time.

### 5.4 Domain Types to Extract

These types currently live in various src/ modules and move to fmm-core:

**From src/manifest/mod.rs** (all move to fmm-core/src/types.rs):
- `Manifest`
- `FileEntry`
- `ExportLines`
- `ExportLocation`

**From src/parser/mod.rs** (all move to fmm-core/src/parser/):
- `ExportEntry`
- `Metadata`
- `ParseResult`
- `Parser` (trait)
- `ParserRegistry`
- `RegisteredLanguage`
- `LanguageTestPatterns`

**From src/db/writer.rs** (moves to fmm-core/src/types.rs):
- `PreserializedRow` (pure data struct, no rusqlite dependency)
- `ExportRecord`, `MethodRecord` (serialization intermediates used by PreserializedRow)

**From src/search/mod.rs** (all move to fmm-core/src/search/):
- `BareSearchResult`, `ExportHit`, `ExportHitCompact`, `FileSearchResult`
- `ImportHit`, `NamedImportHit`, `SearchFilters`, `DEFAULT_SEARCH_LIMIT`

**From src/manifest/glossary_builder.rs** (moves to fmm-core/src/manifest/):
- `GlossaryEntry`, `GlossaryMode`, `GlossarySource`

**From src/config/mod.rs** (moves to fmm-core/src/config.rs):
- `Config`, `TestPatterns`

### 5.5 Error Types

```rust
// fmm-core/src/error.rs
use thiserror::Error;

#[derive(Debug, Error)]
pub enum FmmError {
    #[error("file not found in index: {0}")]
    FileNotFound(String),

    #[error("export not found: {0}")]
    ExportNotFound(String),

    #[error("configuration error: {0}")]
    Config(String),

    #[error("parser error: {0}")]
    Parse(String),

    #[error("resolver error: {0}")]
    Resolve(String),
}
```

Note: Most current error handling in fmm uses `anyhow::Result` and string-based errors (`Err(format!("..."))`) rather than typed domain errors. The MCP tool handlers return `Result<String, String>` where the `Err(String)` is displayed directly to the user. Introducing `FmmError` is a progressive improvement, not a blocking prerequisite for the workspace split. The initial migration can preserve the existing anyhow/string error patterns and refine them incrementally.

## 6. fmm-store Crate Spec

### 6.1 Purpose

SQLite adapter implementing the `FmmStore` trait. Owns the database schema, migrations, connection management, and all rusqlite interactions.

### 6.2 Module Structure

```rust
// fmm-store/src/lib.rs
mod schema;       // CREATE_SCHEMA_SQL, SCHEMA_VERSION, ensure_schema, migrations
mod reader;       // load_manifest_from_db, load_files, load_exports, etc.
mod writer;       // upsert_file_data, serialize_file_data, etc.
mod connection;   // open_or_create, open_db, apply_pragmas
mod error;        // StoreError

pub use error::StoreError;

pub struct SqliteStore { /* Connection */ }

impl fmm_core::store::FmmStore for SqliteStore {
    type Error = StoreError;
    // ...
}
```

### 6.3 StoreError

```rust
// fmm-store/src/error.rs
use thiserror::Error;

#[derive(Debug, Error)]
pub enum StoreError {
    #[error("database error: {0}")]
    Database(#[from] rusqlite::Error),

    #[error("no index found at {path}. Run `fmm generate` first.")]
    NoIndex { path: String },

    #[error("index built with fmm v{stored} but running v{running}. Run `fmm generate --force` to rebuild.")]
    VersionMismatch { stored: String, running: String },

    #[error("schema migration failed: {0}")]
    Migration(String),

    #[error("{0}")]
    Other(#[from] anyhow::Error),
}
```

### 6.4 What Moves from Current Codebase

| Current location | Target location | Notes |
|-----------------|----------------|-------|
| src/db/mod.rs (open_or_create, open_db, pragmas, schema) | fmm-store/src/connection.rs + schema.rs | Schema SQL and version management |
| src/db/reader.rs (load_manifest_from_db, load_files, load_exports, load_methods, load_reverse_deps, load_workspace_packages) | fmm-store/src/reader.rs | Read path, unchanged logic |
| src/db/writer.rs (upsert_preserialized, delete_all_files, rebuild_and_write_reverse_deps, upsert_workspace_packages, write_meta, write_reverse_deps, load_files_map, load_indexed_mtimes, is_file_up_to_date, upsert_file_data) | fmm-store/src/writer.rs | Write path. Transaction management stays internal to SqliteStore |
| src/db/writer.rs (serialize_file_data, PreserializedRow, ExportRecord, MethodRecord) | fmm-core/src/types.rs | Pure data serialization, no rusqlite dependency |
| src/db/writer.rs (file_mtime_rfc3339) | fmm-cli/src/cli/util.rs | Filesystem I/O (std::fs::metadata), not a storage concern |
| src/db/writer_tests.rs | fmm-store/src/writer_tests.rs or tests/ | Writer unit tests |
| DB_FILENAME constant | fmm-store/src/connection.rs | ".fmm.db" |

## 7. fmm-cli Crate Spec

### 7.1 Purpose

Binary crate. Thin orchestrator that wires fmm-core and fmm-store together. Contains:
1. Clap CLI definitions and argument parsing
2. MCP stdio server
3. `main.rs` dispatch
4. File watching (notify)
5. `fmm init` / `fmm generate` orchestration
6. Generated code from build.rs (schema, help text)

### 7.2 Module Structure

```rust
// fmm-cli/src/main.rs
use clap::Parser;
use fmm_core::config::Config;
use fmm_store::SqliteStore;

fn main() {
    let cli = Cli::parse();
    // ...
    match cli.command {
        Commands::Serve | Commands::Mcp => {
            let store = SqliteStore::open(&root)?;
            let mut server = McpServer::new(store);
            server.run()?;
        }
        Commands::Generate { .. } => {
            let store = SqliteStore::open_or_create(&root)?;
            generate(&store, &config, ...)?;
        }
        // ...
    }
}
```

### 7.3 McpServer Becomes Generic

```rust
// Before (current)
pub struct McpServer {
    manifest: Option<Manifest>,
    load_error: Option<String>,
    root: PathBuf,
}

// After
pub struct McpServer<S: FmmStore> {
    store: S,
    manifest: Option<Manifest>,
    load_error: Option<String>,
    root: PathBuf,
}

impl<S: FmmStore> McpServer<S> {
    pub fn new(store: S) -> Self { /* ... */ }

    fn reload(&mut self) {
        match self.store.load_manifest() {
            Ok(m) => { self.manifest = Some(m); self.load_error = None; }
            Err(e) => { self.manifest = None; self.load_error = Some(e.to_string()); }
        }
    }

    // Tool handlers remain unchanged: they take &Manifest, not &S
    // e.g. tools::tool_lookup_export(manifest, &self.root, &arguments)
}
```

**Tool handlers do not change.** Every MCP tool handler currently takes `(&Manifest, &Path, &Value)` and returns `Result<String, String>`. This signature is already store-agnostic. The generic `S: FmmStore` only affects `McpServer::reload()` and the CLI generate/watch commands.

### 7.4 What Stays in fmm-cli

| Current location | Notes |
|-----------------|-------|
| src/main.rs | Clap dispatch, error printing |
| src/cli/ (all modules) | CLI command handlers |
| src/mcp/ (mod.rs, tools/, args.rs, schema.rs) | MCP server + tool handlers |
| src/mcp/generated_schema.rs | Generated by build.rs |
| src/cli/generated_help.rs | Generated by build.rs |

### 7.5 build.rs

The current build.rs at the workspace root generates files into `src/mcp/` and `src/cli/`. After the split, build.rs moves to `crates/fmm-cli/build.rs` and generates into `crates/fmm-cli/src/`. The `tools.toml` stays at the workspace root; build.rs reads it via `CARGO_MANIFEST_DIR` parent traversal or a workspace-root-relative path.

Alternative: keep `tools.toml` inside `crates/fmm-cli/` since it is consumed only by that crate's build.rs. This avoids path complexity. The SKILL.md template generation writes to `templates/SKILL.md` at the workspace root; this path would need adjustment.

**Recommendation**: Move `tools.toml` into `crates/fmm-cli/`. Keep `templates/SKILL.md` generation pointing to workspace root via `CARGO_MANIFEST_DIR/../../templates/SKILL.md`. This keeps the build.rs self-contained.

## 8. Dependency Mapping

### 8.1 fmm-core Dependencies

```toml
[dependencies]
# Parsing (17 grammars)
tree-sitter = "0.26"
tree-sitter-typescript = "0.23"
tree-sitter-python = "0.25"
tree-sitter-rust = "0.24"
tree-sitter-go = "0.25"
tree-sitter-java = "0.23"
tree-sitter-cpp = "0.23"
tree-sitter-c-sharp = "0.23"
tree-sitter-ruby = "0.23"
tree-sitter-php = "0.24"
tree-sitter-c = "0.24"
tree-sitter-zig = "1.1"
tree-sitter-lua = "0.5"
tree-sitter-scala = "0.24"
tree-sitter-swift = "0.7"
tree-sitter-kotlin-ng = "1.1"
tree-sitter-elixir = "0.3"
tree-sitter-dart-orchard = "0.3"
streaming-iterator = "0.1"

# Cross-package resolution
oxc_resolver = "11"

# Serialization (domain types derive Serialize/Deserialize)
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
toml = { version = "0.8", features = ["parse"] }

# Date/time (Manifest.generated uses chrono::DateTime<Utc>)
chrono = { version = "0.4", features = ["serde"] }

# Error handling
thiserror = "2.0"
anyhow = "1.0"

# Pattern matching (search, glossary, config)
regex = "1"
glob = "0.3"

# Parallelism (extractor uses rayon for parallel parsing)
rayon = "1.10"

[dev-dependencies]
tempfile = "3.14"
criterion = { version = "0.5", features = ["html_reports"] }
```

**Note on rayon**: The `FileProcessor` and parallel indexing logic use rayon. This is used during `fmm generate` (CLI concern), but the `ParserCache` and `FileProcessor` types live in fmm-core. rayon stays in fmm-core because the extractor module provides the parallel processing API that CLI calls into.

**Note on anyhow**: Many fmm-core functions currently return `anyhow::Result`. The pragmatic path is to keep anyhow in fmm-core during the initial split and progressively migrate to typed errors. Forcing all error types to be concrete before the workspace split would be a massive diff with high risk.

### 8.2 fmm-store Dependencies

```toml
[dependencies]
fmm-core = { path = "../fmm-core" }
rusqlite = { version = "0.32", features = ["bundled"] }
anyhow = "1.0"
thiserror = "2.0"
chrono = { version = "0.4", features = ["serde"] }
serde_json = "1.0"

[dev-dependencies]
tempfile = "3.14"
```

### 8.3 fmm-cli Dependencies

```toml
[dependencies]
fmm-core = { path = "../fmm-core" }
fmm-store = { path = "../fmm-store" }

# CLI
clap = { version = "4.5", features = ["derive", "cargo"] }
clap_complete = "4.5"
clap_mangen = "0.2"
clap-markdown = "0.1"
color-print = "0.3"
colored = "3.0"

# File handling (watch mode, init)
ignore = "0.4"
notify = "8.2"
notify-debouncer-full = "0.7"
ctrlc = "3.4"

# Progress bars (generate command)
indicatif = { version = "0.17", features = ["rayon"] }

# Serialization (JSON-RPC, tool responses)
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# Error handling
anyhow = "1.0"

[build-dependencies]
toml = { version = "0.8", features = ["parse"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
indexmap = { version = "2", features = ["serde"] }

[dev-dependencies]
tempfile = "3.14"
assert_cmd = "2"
```

## 9. Workspace Cargo.toml

```toml
[workspace]
members = ["crates/*"]
resolver = "3"

[workspace.package]
version = "0.1.41"
edition = "2024"
authors = ["Stuart Robinson <stuart@alphabio.com>"]
license = "MIT"
repository = "https://github.com/srobinson/fmm"
homepage = "https://srobinson.github.io/fmm/"

[workspace.dependencies]
# Internal
fmm-core = { path = "crates/fmm-core" }
fmm-store = { path = "crates/fmm-store" }

# Shared across multiple crates
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
anyhow = "1.0"
thiserror = "2.0"
chrono = { version = "0.4", features = ["serde"] }
toml = { version = "0.8", features = ["parse"] }
tempfile = "3.14"

# Parsing
tree-sitter = "0.26"
tree-sitter-typescript = "0.23"
tree-sitter-python = "0.25"
tree-sitter-rust = "0.24"
tree-sitter-go = "0.25"
tree-sitter-java = "0.23"
tree-sitter-cpp = "0.23"
tree-sitter-c-sharp = "0.23"
tree-sitter-ruby = "0.23"
tree-sitter-php = "0.24"
tree-sitter-c = "0.24"
tree-sitter-zig = "1.1"
tree-sitter-lua = "0.5"
tree-sitter-scala = "0.24"
tree-sitter-swift = "0.7"
tree-sitter-kotlin-ng = "1.1"
tree-sitter-elixir = "0.3"
tree-sitter-dart-orchard = "0.3"
streaming-iterator = "0.1"

# Database
rusqlite = { version = "0.32", features = ["bundled"] }

# CLI
clap = { version = "4.5", features = ["derive", "cargo"] }

# Cross-package
oxc_resolver = "11"
rayon = "1.10"
regex = "1"
glob = "0.3"

[profile.release]
lto = true
codegen-units = 1
strip = true
opt-level = 3

[profile.bench]
opt-level = 3
lto = false
```

## 10. Migration Strategy

### Principle: Each Phase Compiles and Passes Tests

No flag day. Each phase produces a working, testable system. The `fmm` binary remains a single installable artifact. Agents using `fmm serve` see no behavioral difference at any point.

### Phase 1a: Workspace Scaffolding (no code moves)

**Goal**: Convert the single crate into a workspace with one member crate that contains all existing code. Verify the build works identically. Edition stays at 2021 in this step to isolate workspace-level issues from edition issues.

1. Create the workspace directory structure:
   ```
   mkdir -p crates/fmm-cli
   ```
2. Create root `Cargo.toml` as a virtual manifest pointing to `crates/fmm-cli`
3. Move the existing `src/`, `tests/`, `fixtures/`, `benches/`, `examples/`, `build.rs` into `crates/fmm-cli/`
4. Create `crates/fmm-cli/Cargo.toml` with all current dependencies (copy from root)
5. Update root `Cargo.toml` to workspace format with `[workspace.package]` and `[workspace.dependencies]`
6. Update `crates/fmm-cli/Cargo.toml` to use `workspace = true` for shared fields
7. Update build.rs paths (CARGO_MANIFEST_DIR is now `crates/fmm-cli/`)
8. Update `.github/workflows/ci.yml` (add `--workspace` to test/clippy, add `--package fmm-cli` to release build)
9. Update justfile recipes (add `--workspace` flags, update install path to `crates/fmm-cli`)
10. Verify: `cargo test --workspace` passes all 907 tests
11. Verify: `cargo build --release` produces identical binary
12. Verify: `fmm generate && fmm serve` works end-to-end

**This phase is the riskiest**: path references in build.rs, test fixtures, and CI all need updating. Doing it before any code restructuring isolates workspace-level issues from module-level issues.

**Specific path risks**:
- Integration tests in `tests/*.rs` use relative paths to `fixtures/`. After moving to `crates/fmm-cli/tests/`, use `env!("CARGO_MANIFEST_DIR")` to construct fixture paths. Grep for fixture path patterns before the move.
- `fmm generate` self-indexing: fmm indexes itself. The `ignore` walker walks from the root, so `crates/*/src/` files are discovered. Verify `.fmm.db` location and end-to-end behavior.
- The release.yml cross-compilation step needs `--package fmm-cli` since a virtual manifest has no default `[[bin]]` target.

### Phase 1b: Edition 2024 Upgrade

**Goal**: Upgrade to edition 2024, resolver 3. Separate from workspace scaffolding for clean bisection.

1. Run `cargo fix --edition` to apply mechanical migrations
2. Update `[workspace.package]` edition to "2024"
3. Resolver 3 is implicit with edition 2024 workspaces (the explicit `resolver = "3"` in §9 is redundant but harmless)
4. Verify: `cargo test --workspace` passes all 907 tests
5. Verify: `cargo clippy --workspace` passes

### Phase 2: Extract fmm-core

**Goal**: Create fmm-core with domain types and pure logic. fmm-cli depends on fmm-core.

1. Create `crates/fmm-core/Cargo.toml` with parsing, search, format, manifest, config, extractor, resolver dependencies
2. Create `crates/fmm-core/src/lib.rs` with module declarations
3. Move modules from `crates/fmm-cli/src/` to `crates/fmm-core/src/`:
   - `parser/` (entire module tree including all 17 language parsers)
   - `manifest/` (including dependency_matcher, glossary_builder, call_site_finder, private_members)
   - `search/` (entire module)
   - `format/` (entire module)
   - `config/` -> `config.rs`
   - `extractor/` -> `extractor.rs`
   - `resolver/` (entire module)
4. Move domain types from manifest/mod.rs to `crates/fmm-core/src/types.rs`:
   - `Manifest`, `FileEntry`, `ExportLines`, `ExportLocation`
5. Update all `use crate::` imports in moved modules to reference the new crate structure
6. Update `crates/fmm-cli/Cargo.toml` to depend on `fmm-core`
7. Update `crates/fmm-cli/src/` imports: `use fmm_core::{...}` instead of `use crate::{...}`
8. Move `benches/` to `crates/fmm-core/benches/` (parser benchmarks belong in core)
9. Move `fixtures/` to workspace root (shared by core tests and CLI integration tests)
10. Verify: `cargo test --workspace` passes all 907 tests
11. Verify: `cargo build --release` produces identical binary

**Critical dependency chain**: `manifest/mod.rs` imports `crate::parser::Metadata` and `crate::db::reader`. The parser dependency moves to fmm-core. The db dependency must be severed: `Manifest::load()` and `Manifest::load_from_sqlite()` currently call `crate::db::*` directly.

**How to sever Manifest -> db (two-step)**:

Phase 2 (fmm-core extraction, db module still in fmm-cli):
- Remove `load()` and `load_from_sqlite()` from `Manifest` (they depend on `crate::db`)
- In fmm-cli, `McpServer::reload()` calls `db::open_db(&self.root)` + `db::reader::load_manifest_from_db()` directly (temporary intermediate state)
- The db module remains in fmm-cli during this phase

Phase 3 (fmm-store extraction):
- The db module moves to fmm-store as `SqliteStore`
- `SqliteStore::load_manifest()` replaces the direct db calls
- `McpServer<S: FmmStore>` calls `self.store.load_manifest()`

### Phase 3: Extract fmm-store

**Goal**: Create fmm-store with the SQLite adapter. Define and implement the FmmStore trait.

1. Create `crates/fmm-store/Cargo.toml` depending on fmm-core and rusqlite
2. Define `FmmStore` trait in `crates/fmm-core/src/store.rs`
3. Move modules from `crates/fmm-cli/src/` to `crates/fmm-store/src/`:
   - `db/mod.rs` -> split into `connection.rs` + `schema.rs`
   - `db/reader.rs` -> `reader.rs`
   - `db/writer.rs` -> `writer.rs`
   - `db/writer_tests.rs` -> tests
4. Create `SqliteStore` struct implementing `FmmStore`
5. Create `StoreError` with thiserror
6. Update `crates/fmm-cli/Cargo.toml` to depend on `fmm-store`
7. Update fmm-cli: replace all `crate::db::*` calls with `FmmStore` trait methods. Key files:
   - `sidecar.rs`: imports `crate::db` and `rusqlite::params`. Orchestrates the generate pipeline. Replace `db::open_or_create`, `db::writer::*`, and `db::open_db` calls with `FmmStore` methods.
   - `watch.rs`: imports `crate::db`, `crate::db::writer`, and `rusqlite::params`. Uses raw SQL for file deletion. Replace `db::open_db` with store access, `db::writer::upsert_file_data` with `FmmStore::upsert_single_file`, and `remove_file_from_db` raw SQL with `FmmStore::delete_single_file`.
   - `mcp/mod.rs`: replace `Manifest::load()` with `store.load_manifest()`.
8. Make `McpServer` generic over `S: FmmStore`
9. Create `InMemoryStore` for testing (in fmm-store dev-dependencies or fmm-cli test support)
10. Verify: `cargo test --workspace` passes all 907 tests
11. Verify: `cargo build --release` produces identical binary

### Phase 4: Quality and Polish

**Goal**: Bring testing, CI, and tooling to the reference standard.

1. Switch `just test` and CI to `cargo nextest run --workspace`
2. Add `insta` snapshot tests for MCP tool response format stability
3. Add subprocess MCP protocol tests via `assert_cmd` (initialize, tools/list, tools/call)
4. Standardize justfile recipes per reference architecture
5. Update CI to use nextest
6. Verify npm publish and release pipeline still work with new workspace paths

## 11. Testing Strategy

### Current Test Distribution After Split

| Test location | Target crate | Count (approx) | Notes |
|--------------|-------------|----------------|-------|
| src/parser/builtin/*/tests.rs | fmm-core | ~350 | Language parser unit tests |
| src/mcp/tests.rs | fmm-cli | ~90 | MCP tool handler tests (use call_tool()) |
| src/search/tests.rs | fmm-core | ~50 | Search engine tests |
| src/manifest/tests.rs | fmm-core | ~30 | Manifest operation tests |
| src/db/writer_tests.rs | fmm-store | ~20 | Writer unit tests |
| src/db/mod.rs tests | fmm-store | ~5 | Schema management tests |
| src/manifest/call_site_finder/tests.rs | fmm-core | ~20 | Call site tests |
| src/manifest/private_members/tests.rs | fmm-core | ~20 | Private member tests |
| src/format/yaml_formatters_tests.rs | fmm-core | ~15 | Formatter tests |
| src/cli/search_tests.rs | fmm-cli | ~15 | CLI search tests |
| tests/*.rs (9 files) | fmm-cli (integration) | ~195 | Full integration tests |

### New Tests to Add (Phase 4)

1. **MCP protocol subprocess tests** (fmm-cli): Spawn `fmm serve`, send JSON-RPC via stdin, assert on stdout. Cover: initialize handshake, tools/list, tools/call for each tool, error responses, unknown method.

2. **insta snapshot tests** (fmm-cli): Snapshot the JSON output of each MCP tool handler. Catches unintended format changes that break agent behavior.

3. **FmmStore trait contract tests** (fmm-store): Test that `SqliteStore` and `InMemoryStore` both satisfy the trait contract. Write tests generic over `S: FmmStore`.

4. **Cross-crate integration tests** (workspace root tests/): Verify the full pipeline: parse -> store -> load -> query.

## 12. CI/CD Alignment

### ci.yml Changes

```yaml
- name: Test
  run: cargo nextest run --workspace    # was: cargo test

- name: Clippy
  run: cargo clippy --workspace --all-targets --all-features -- -D warnings

- name: Build (release)
  run: cargo build --workspace --release
```

### release.yml Changes

The release pipeline builds the `fmm` binary from `crates/fmm-cli/`. The `cargo build --release --target ${{ matrix.target }}` command continues to produce the same binary because the `[[bin]]` target is in `crates/fmm-cli/Cargo.toml`.

Update the install path in justfile:
```just
install:
    cargo install --path crates/fmm-cli
```

### npm Publish

The npm package at `npm/frontmatter-matters/` references the binary by name (`fmm`), not by crate path. No changes needed to the npm publish step.

## 13. Justfile (Target State)

```just
default:
    @just --list

gen-docs:
    touch crates/fmm-cli/tools.toml
    cargo build -p fmm-cli 2>&1 | grep -vE "^\s*(Compiling|Finished|Running|Fresh)" || true

build:
    cargo build --workspace

release:
    cargo build --workspace --release

test:
    cargo nextest run --workspace

fmt:
    cargo fmt --all

clippy:
    cargo clippy --workspace --all-targets --fix --allow-dirty -- -D warnings

check: fmt clippy

install:
    cargo install --path crates/fmm-cli

ci: check test build
    @echo "All CI checks passed"
```

## 14. Risk Assessment

### High Risk

| Risk | Mitigation |
|------|------------|
| Path breakage during workspace scaffolding (Phase 1) | Phase 1 moves code without restructuring modules. Build.rs paths, fixture paths, and test helper paths are the known fragile spots. Verify all 907 tests pass before proceeding. |
| Circular dependency during fmm-core extraction | Manifest::load() -> db is the only core->store dependency. Sever it explicitly in Phase 2 before Phase 3. Plan the cut point before moving code. |
| Integration test fixture paths break | Move fixtures to workspace root. Update fixture path resolution to use `CARGO_WORKSPACE_DIR` (available in Rust 2024 nightly, or compute from `CARGO_MANIFEST_DIR` + parent traversal). |

### Medium Risk

| Risk | Mitigation |
|------|------------|
| build.rs path resolution after workspace split | build.rs uses `CARGO_MANIFEST_DIR`. After moving to `crates/fmm-cli/build.rs`, tools.toml path changes. Test build.rs output manually. |
| Release pipeline binary path changes | The `[[bin]]` target in fmm-cli produces the same `fmm` binary name. Cross-compilation `cargo build --release --target X` needs `--package fmm-cli` or `--workspace`. |
| Tree-sitter C compilation slows workspace builds | Tree-sitter grammars compile C code. This is already slow (17 grammars). Putting them all in fmm-core means fmm-core compiles slowly but fmm-store and fmm-cli compile fast in parallel. No regression from current state. |

### Low Risk

| Risk | Mitigation |
|------|------------|
| FmmStore trait surface is wrong | The trait mirrors the existing db::writer and db::reader public API. Audit every `db::` call site before defining the trait. |
| Edition 2024 introduces compilation errors | Edition 2024 changes are minimal and backwards-compatible for fmm's patterns. `cargo fix --edition` handles mechanical migrations. |
| InMemoryStore behavior diverges from SQLite | Keep InMemoryStore minimal. Use it for MCP handler tests. Integration tests keep using real SQLite. |

## 15. Open Questions for Stuart

1. **tools.toml location**: Keep at workspace root (current location, convenient for humans) or move to `crates/fmm-cli/` (cleaner for build.rs)? Recommendation: move to `crates/fmm-cli/`.

2. **Test fixture location**: Keep fixtures at workspace root `fixtures/` (shared by all crates) or duplicate into each crate's `tests/fixtures/`? Recommendation: workspace root, with a shared test-support crate or path constant if needed.

3. **Progressive error typing**: The current codebase uses `anyhow::Result` extensively in fmm-core code. Should Phase 2 introduce typed `FmmError` everywhere, or preserve `anyhow` in fmm-core and refine incrementally? Recommendation: preserve `anyhow` initially, type errors progressively.

4. **InMemoryStore scope**: Should `InMemoryStore` live in fmm-store's dev-dependencies or in a separate `fmm-test-support` crate? For a project of fmm's size, a separate crate is overkill. Recommendation: in fmm-store as `#[cfg(test)]` module, re-exported for fmm-cli tests via a `test-support` feature.

## 16. Success Criteria

### Phase 1a: Workspace Scaffolding
- [ ] Virtual manifest at root with `[workspace]`
- [ ] Single member crate `crates/fmm-cli` contains all existing code
- [ ] `[workspace.package]` for version, edition, license, repository
- [ ] `[workspace.dependencies]` for all shared dependencies
- [ ] All 907 existing tests pass
- [ ] `cargo build --release` produces identical binary
- [ ] CI pipeline passes
- [ ] `fmm generate && fmm serve` works end-to-end

### Phase 1b: Edition 2024 Upgrade
- [ ] Edition 2024, resolver 3
- [ ] `cargo fix --edition` applied
- [ ] All 907 existing tests pass
- [ ] Clippy passes

### Phase 2: fmm-core Extraction
- [ ] `crates/fmm-core/` contains: parser, manifest, search, format, config, extractor, resolver, types
- [ ] fmm-core has zero rusqlite dependency
- [ ] `PreserializedRow`, `ExportRecord`, `MethodRecord` moved to fmm-core/src/types.rs
- [ ] `serialize_file_data` moved to fmm-core (pure CPU transformation)
- [ ] `Manifest::load()` and `Manifest::load_from_sqlite()` removed from Manifest
- [ ] fmm-cli calls `db::open_db` + `db::reader::load_manifest_from_db` directly (intermediate state)
- [ ] All parser tests pass in fmm-core
- [ ] All search/format/manifest tests pass in fmm-core
- [ ] Benchmarks run from fmm-core
- [ ] fmm-cli depends on fmm-core, all integration tests pass
- [ ] All 907 tests pass across workspace

### Phase 3: fmm-store Extraction
- [ ] `crates/fmm-store/` contains: SQLite reader, writer, schema, connection management
- [ ] `FmmStore` trait defined in fmm-core with associated error type
- [ ] `SqliteStore` implements `FmmStore` with batch write semantics (`write_indexed_files` uses single transaction)
- [ ] `StoreError` uses thiserror, wraps rusqlite::Error
- [ ] `McpServer<S: FmmStore>` is generic over the store trait
- [ ] `InMemoryStore` implements `FmmStore` for testing
- [ ] `file_mtime_rfc3339` moved from db/writer.rs to fmm-cli utility
- [ ] `sidecar.rs` no longer imports `rusqlite` or `crate::db` directly; all persistence goes through `FmmStore`
- [ ] `watch.rs` no longer imports `rusqlite` or `crate::db` directly; file removal uses `FmmStore::delete_single_file`
- [ ] DB unit tests pass in fmm-store
- [ ] All 907 tests pass across workspace
- [ ] `fmm generate && fmm serve` works end-to-end

### Phase 4: Quality and Polish
- [ ] `just test` uses `cargo nextest run --workspace`
- [ ] CI uses nextest
- [ ] insta snapshot tests cover all 8 MCP tool response formats
- [ ] Subprocess MCP protocol tests pass (initialize, tools/list, tools/call)
- [ ] Justfile recipes standardized per reference architecture
- [ ] Release pipeline produces correct binaries from workspace layout
- [ ] npm publish works with new paths
