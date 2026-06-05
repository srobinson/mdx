---
title: "context-matters: Project Scaffold and Plugin Integration Spec"
type: projects
tags: [context-matters, rust, mcp, helioy, scaffold, plugin]
summary: Implementation spec for the context-matters Cargo workspace structure, dependencies, binary entry point, plugin registration, configuration, and build/test setup.
status: active
created: 2026-03-14
updated: 2026-03-14
---

## 1. Cargo Workspace Layout

context-matters follows the same workspace pattern as attention-matters: a root `Cargo.toml` workspace with multiple crates under `crates/`.

```
context-matters/
├── Cargo.toml                    # workspace root
├── Cargo.lock                    # committed for reproducibility
├── justfile                      # build/test/lint recipes
├── tools.toml                    # SINGLE SOURCE OF TRUTH for all tool docs
├── release-please-config.json    # version automation
├── CLAUDE.md                     # project instructions for Claude Code
├── README.md
├── crates/
│   ├── cm-core/                  # domain types, traits, query logic
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── types.rs          # Entry, Scope, Kind, Tag types
│   │       ├── error.rs          # CmError enum (thiserror)
│   │       ├── store.rs          # ContextStore trait definition
│   │       └── query.rs          # query building, FTS5 helpers
│   ├── cm-store/                 # SQLite adapter (ContextStore impl)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── sqlite.rs         # SqliteContextStore implementation
│   │       ├── schema.rs         # DDL, migrations, pragmas
│   │       ├── config.rs         # Config loading (TOML + env vars)
│   │       └── project.rs        # default_base_dir, directory setup
│   │   └── migrations/
│   │       ├── 001_initial_schema.sql
│   │       ├── 002_fts5_setup.sql
│   │       └── 003_triggers.sql
│   └── cm-cli/                   # CLI binary + MCP server
│       ├── Cargo.toml
│       ├── build.rs              # reads ../../tools.toml, generates schema + help
│       └── src/
│           ├── main.rs           # clap CLI, serve subcommand, tokio runtime
│           ├── mcp/
│           │   ├── mod.rs        # McpServer struct, JSON-RPC stdio loop
│           │   ├── schema.rs     # loads generated_schema.rs
│           │   ├── generated_schema.rs  # AUTO-GENERATED from tools.toml
│           │   └── tools/        # tool handler functions
│           │       ├── mod.rs
│           │       ├── recall.rs
│           │       ├── store.rs
│           │       ├── deposit.rs
│           │       ├── browse.rs
│           │       ├── get.rs
│           │       ├── update.rs
│           │       ├── forget.rs
│           │       ├── stats.rs
│           │       └── export.rs
│           └── cli/
│               ├── mod.rs
│               └── generated_help.rs  # AUTO-GENERATED from tools.toml
├── npm/
│   └── context-matters/
│       ├── package.json          # npm wrapper for npx distribution
│       ├── bin/
│       │   └── cm                # shell stub (overwritten by install.js)
│       └── scripts/
│           └── install.js        # GitHub release binary downloader
└── target/
```

### Crate Responsibilities

**cm-core**: Pure domain logic. Zero I/O, zero async. Defines the `ContextStore` trait, domain types (`Entry`, `Scope`, `Kind`), and query construction helpers. Any storage backend implements `ContextStore`. The trait uses synchronous method signatures. Async wrapping is the adapter's concern: cm-store's public API exposes async methods that call `ContextStore` methods internally (sqlx handles the thread pool), while a future rusqlite adapter would use `tokio::task::spawn_blocking`.

**cm-store**: SQLite implementation of `ContextStore`. Owns the schema, migrations, configuration loading, and all sqlx interaction. Provides `CmStore` (the concrete store type) and `Config` for settings resolution.

**cm-cli**: Binary crate producing the `cm` executable. Contains the MCP server (`McpServer`) and optional CLI subcommands for manual inspection. The `serve` subcommand is the primary mode, launched by Claude Code via `npx context-matters serve`.

### Why Three Crates

The attention-matters pattern (am-core / am-store / am-cli) separates concerns cleanly:
- cm-core is testable without a database. Unit tests validate type construction, query building, and invariant enforcement without touching SQLite.
- cm-store is testable with in-memory SQLite. Integration tests verify schema migrations, CRUD operations, and FTS5 queries.
- cm-cli is testable end-to-end. The MCP server can be tested against a CmStore backed by in-memory SQLite.

Alternative considered: a single crate. Rejected because the trait abstraction (SQLite first, Postgres later) requires a clean boundary between trait definition and implementation. Putting the trait in the same crate as the SQLite implementation would create a circular dependency when adding a Postgres adapter later.

## 2. Dependencies with Exact Versions

All versions pinned to what the helioy ecosystem currently uses (attention-matters v0.1.17, fmm v0.1.40) or the latest stable where a dependency is new.

### workspace Cargo.toml

```toml
[workspace]
resolver = "3"
members = [
    "crates/cm-core",
    "crates/cm-store",
    "crates/cm-cli",
]

[workspace.package]
version = "0.1.0"
edition = "2024"
license = "MIT"
repository = "https://github.com/srobinson/context-matters"

[workspace.dependencies]
cm-core = { path = "crates/cm-core" }
cm-store = { path = "crates/cm-store" }

# Database
sqlx = { version = "0.8", features = ["runtime-tokio", "sqlite"] }

# Async runtime
tokio = { version = "1", features = ["macros", "rt-multi-thread", "io-std", "signal", "time"] }

# CLI
clap = { version = "4", features = ["derive"] }

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"
toml = "0.8"

# Identity
uuid = { version = "1.9", features = ["v7", "serde"] }
blake3 = "1"

# Encoding
base64 = "0.22"

# Error handling
anyhow = "1"
thiserror = "2.0"

# Observability
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }

# Date/time
chrono = { version = "0.4", features = ["serde"] }
```

### cm-core/Cargo.toml

```toml
[package]
name = "cm-core"
version.workspace = true
edition.workspace = true
license.workspace = true
description = "Domain types and traits for the context-matters store"

[dependencies]
serde = { workspace = true }
serde_json = { workspace = true }
uuid = { workspace = true }
blake3 = { workspace = true }
thiserror = { workspace = true }
chrono = { workspace = true }

[dev-dependencies]
serde_json = { workspace = true }
```

### cm-store/Cargo.toml

```toml
[package]
name = "cm-store"
version.workspace = true
edition.workspace = true
license.workspace = true
description = "SQLite persistence layer for context-matters"

[dependencies]
cm-core = { workspace = true }
sqlx = { workspace = true }
tokio = { workspace = true }
serde = { workspace = true }
serde_json = { workspace = true }
toml = { workspace = true }
tracing = { workspace = true }
uuid = { workspace = true }
chrono = { workspace = true }
anyhow = { workspace = true }

[dev-dependencies]
tempfile = "3"
tokio = { workspace = true, features = ["test-util"] }
```

### cm-cli/Cargo.toml

```toml
[package]
name = "cm-cli"
version.workspace = true
edition.workspace = true
license.workspace = true
description = "CLI and MCP server for context-matters"
build = "build.rs"

[[bin]]
name = "cm"
path = "src/main.rs"

[dependencies]
cm-core = { workspace = true }
cm-store = { workspace = true }
tokio = { workspace = true }
clap = { workspace = true }
base64 = { workspace = true }
serde = { workspace = true }
serde_json = { workspace = true }
anyhow = { workspace = true }
tracing = { workspace = true }
tracing-subscriber = { workspace = true }
uuid = { workspace = true }
chrono = { workspace = true }

[build-dependencies]
serde = { workspace = true }
serde_json = { workspace = true }
toml = { workspace = true }
indexmap = { version = "2", features = ["serde"] }

[target.'cfg(unix)'.dependencies]
libc = "0.2"

[dev-dependencies]
assert_cmd = "2"
predicates = "3"
tempfile = "3"
```

### Dependency Rationale

| Dependency | Why | Why not the alternative |
|---|---|---|
| sqlx | Compile-time checked queries, async-ready pool, migration system | rusqlite (used by am/fmm) is synchronous and requires manual connection management. sqlx's migration system and prepared statement checking justify the switch for a new project. The adapter pattern means the choice is encapsulated inside cm-store. |
| uuid 1.9+ | UUIDv7 for time-sortable entry IDs. v1.9.0 added proper monotonicity counters within the same millisecond (earlier versions lacked ordering guarantees for rapid sequential generation). | ULID (functionally equivalent, no RFC, smaller ecosystem). TypeID (adds type prefix, unnecessary complexity for single-entity store). |
| blake3 | Content hashing for deduplication. Faster than SHA-256, produces 256-bit digests. 80M+ downloads, official reference implementation with auto-detected SIMD. | SHA-256 (3-15x slower). xxHash3 (faster but zero collision resistance, wrong for dedup). |
| thiserror 2.0 | Derive Error for cm-core types. Same version as fmm. | Manual Error impl. thiserror eliminates boilerplate. |
| chrono | ISO 8601 timestamps with timezone support. | time crate. chrono is already in the fmm dependency tree. |

### Why No rmcp

The initial design specified rmcp (the official Rust MCP SDK). It was dropped in favor of the manual JSON-RPC pattern used by fmm because:

1. **Help documentation coupling.** rmcp's `#[tool]` proc macro requires string literal descriptions. This couples tool documentation to the MCP transport layer, preventing reuse by a CLI or future web app.
2. **tools.toml as single source of truth.** The fmm pattern (tools.toml + build.rs code generation) produces MCP schema, CLI help, and skill docs from one file. rmcp's macros cannot consume external documentation sources.
3. **Proven in the ecosystem.** fmm's manual MCP implementation is under 300 lines and handles the full stdio protocol including error recovery. The protocol is simple enough that a library adds more complexity than it removes.
4. **Parity guarantee.** When a CLI is added, it consumes the same generated help constants as the MCP server. When a web app is added, it reads tools.toml directly. All three transports stay synchronized by construction.

### Why sqlx Instead of rusqlite

attention-matters uses rusqlite directly. context-matters uses sqlx instead because:

1. **Migration system**: sqlx provides `sqlx::migrate!()` which embeds migration SQL files at compile time and runs them automatically. attention-matters rolls its own migration logic in schema.rs with version-gated ALTER TABLE statements. For a new project, sqlx migrations are cleaner.
2. **Compile-time query checking**: `sqlx::query!()` validates SQL against the schema at compile time. This catches column name typos and type mismatches before runtime.
3. **Connection pooling**: sqlx provides `SqlitePool` out of the box, relevant when the server eventually supports concurrent clients over HTTP transport.
4. **Async compatibility**: sqlx queries are natively async. While SQLite is inherently sequential, sqlx runs operations on a thread pool, so the tokio runtime is never blocked.

The `ContextStore` trait in cm-core uses synchronous method signatures. cm-store wraps these in its own async public API layer, where sqlx handles thread pool dispatch internally. A future rusqlite adapter would use `tokio::task::spawn_blocking` in its own async API to avoid blocking the tokio runtime.

## 3. Binary Entry Point

### main.rs Structure

```rust
mod mcp;
mod cli;

use std::path::PathBuf;

use cm_store::{CmStore, Config};
use anyhow::{Context, Result};
use clap::{ColorChoice, Parser, Subcommand};

#[derive(Parser)]
#[command(
    name = "cm",
    about = "Structured context store for AI agents",
    version,
    color = ColorChoice::Auto
)]
struct Cli {
    /// Enable verbose debug output
    #[arg(long, global = true)]
    verbose: bool,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Start MCP server on stdio transport
    Serve,
    /// Show store statistics
    Stats,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // Initialize tracing (stderr only, never stdout - MCP uses stdout)
    let filter = if cli.verbose { "debug" } else { "info" };
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_writer(std::io::stderr)
        .init();

    match &cli.command {
        Commands::Serve => cmd_serve().await,
        Commands::Stats => cmd_stats().await,
    }
}
```

### Initialization Sequence (cmd_serve)

```
1. Load config (TOML file + env var overrides)
2. Create data directory (~/.context-matters/) if missing
3. Run sqlx migrations (create tables, FTS5 virtual table, indexes)
4. Open connection pool
5. Construct McpServer with store
6. Call server.run().await (JSON-RPC stdio loop, same pattern as fmm)
7. On shutdown: checkpoint WAL
```

Key differences from attention-matters:
- No in-memory system to load. attention-matters loads the entire DAESystem into RAM at startup because its geometric computations require full state. context-matters queries SQLite directly, so startup is just "open pool, run migrations."
- sqlx migrations replace the manual schema versioning. Migration files live in `crates/cm-store/migrations/` and are embedded at compile time.
- No rmcp. The MCP server uses manual JSON-RPC over stdio (same pattern as fmm). Tool documentation comes from tools.toml via build.rs code generation.

### Shutdown Signal Handler

```rust
async fn shutdown_signal() {
    #[cfg(unix)]
    {
        use tokio::signal::unix::{signal, SignalKind};
        let mut sigterm = signal(SignalKind::terminate()).expect("SIGTERM handler");
        let mut sigint = signal(SignalKind::interrupt()).expect("SIGINT handler");
        tokio::select! {
            _ = sigterm.recv() => {}
            _ = sigint.recv() => {}
        }
    }
    #[cfg(not(unix))]
    {
        tokio::signal::ctrl_c().await.expect("ctrl-c handler");
    }
}
```

## 4. Plugin Registration

context-matters registers as an MCP server inside the existing `helioy-tools` plugin. It does not create a separate plugin.

### Registration in helioy-tools/.mcp.json

Add a `cm` entry to the existing `.mcp.json`:

```json
{
  "mcpServers": {
    "am": {
      "command": "npx",
      "args": ["-y", "attention-matters", "serve"]
    },
    "fmm": {
      "command": "npx",
      "args": ["-y", "frontmatter-matters", "serve"]
    },
    "mdx": {
      "command": "npx",
      "args": ["-y", "--package", "mdcontext", "mdcontext-mcp"]
    },
    "cm": {
      "command": "npx",
      "args": ["-y", "context-matters", "serve"]
    },
    "linear-server": {
      "type": "http",
      "url": "https://mcp.linear.app/mcp",
      "headers": {
        "Authorization": "Bearer ${LINEAR_API_KEY}"
      }
    },
    "supabase": {
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server-supabase@latest"],
      "env": {
        "SUPABASE_ACCESS_TOKEN": "$SUPABASE_ACCESS_TOKEN"
      }
    }
  }
}
```

### How This Works

When Claude Code loads the helioy-tools plugin:
1. It reads `.mcp.json` and starts each MCP server as a subprocess.
2. The `cm` server launches via `npx -y context-matters serve`.
3. npx downloads the npm package (if not cached), which runs `scripts/install.js` on postinstall.
4. install.js downloads the prebuilt `cm` binary from GitHub Releases for the current platform.
5. The `cm serve` command starts the MCP server on stdio.
6. Claude Code discovers tools prefixed `cx_` from the server's tool list.
7. Tools appear in the IDE as `mcp__plugin_helioy-tools_cm__cx_recall`, etc.

### Tool Namespace

The full MCP tool name visible to Claude Code follows this pattern:
```
mcp__plugin_helioy-tools_cm__cx_{tool_name}
```

Where:
- `mcp__plugin_helioy-tools` = plugin namespace (from plugin.json name)
- `cm` = server name (from .mcp.json key)
- `cx_{tool_name}` = tool name declared by the server

### npm Package for Distribution

The npm package follows attention-matters exactly:

**npm/context-matters/package.json:**
```json
{
  "name": "context-matters",
  "version": "0.1.0",
  "description": "Structured context store for AI agents - MCP server with SQLite backend",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/srobinson/context-matters"
  },
  "keywords": [
    "mcp",
    "context",
    "ai",
    "claude",
    "agent",
    "sqlite",
    "mcp-server"
  ],
  "bin": {
    "cm": "bin/cm"
  },
  "scripts": {
    "postinstall": "node scripts/install.js"
  },
  "files": [
    "bin/cm",
    "scripts/install.js"
  ]
}
```

**npm/context-matters/scripts/install.js:**
Clone from `attention-matters/npm/attention-matters/scripts/install.js` with these substitutions:
- `REPO = "srobinson/context-matters"`
- `BIN_NAME = "cm"`
- `PLATFORM_MAP` identical (same four targets: darwin-arm64, darwin-x64, linux-arm64, linux-x64)

**SHA-256 verification:** The install script should verify the downloaded binary against `sha256sums.txt` (already uploaded to every GitHub Release by the release workflow). After downloading the tarball, fetch `sha256sums.txt` from the same release, compute the SHA-256 of the downloaded file, and compare. Reject the binary on mismatch. This closes the most significant security gap in the postinstall download pattern with minimal additional code.

**npm/context-matters/bin/cm:**
Shell stub script (placeholder overwritten by install.js with the real binary):
```bash
#!/usr/bin/env bash
echo "Binary not installed. Run: cargo install --path crates/cm-cli" >&2
exit 1
```

### Development Mode (Before npm Publish)

During development, before the npm package is published, register the server locally in `.mcp.json`:

```json
"cm": {
  "command": "/Users/alphab/Dev/LLM/DEV/helioy/context-matters/target/release/cm",
  "args": ["serve"]
}
```

Or with cargo:
```json
"cm": {
  "command": "cargo",
  "args": ["run", "--manifest-path", "/Users/alphab/Dev/LLM/DEV/helioy/context-matters/Cargo.toml", "-p", "cm-cli", "--", "serve"],
  "cwd": "/Users/alphab/Dev/LLM/DEV/helioy/context-matters"
}
```

## 5. Configuration

Follow the attention-matters config pattern: TOML file with environment variable overrides.

### Config File Location

Resolution order (first found wins):
1. `$CWD/.cm.config.toml` (project-local override)
2. `$CM_DATA_DIR/.cm.config.toml` (if env var is set)
3. `~/.context-matters/.cm.config.toml` (global fallback)

### Environment Variables

| Variable | Type | Default | Purpose |
|---|---|---|---|
| `CM_DATA_DIR` | path | `~/.context-matters` | Base directory for cm.db and config |
| `CM_LOG_LEVEL` | string | `info` | Tracing filter level |

### Config File Format

```toml
# context-matters configuration
#
# Config file resolution (first found wins):
#   1. $CWD/.cm.config.toml        (project-local)
#   2. ~/.context-matters/.cm.config.toml  (global fallback)
#
# Environment variables override all file settings:
#   CM_DATA_DIR, CM_LOG_LEVEL

# Directory where the database lives.
# Override with CM_DATA_DIR env var.
# data_dir = "~/.context-matters"
```

### Default Data Directory Layout

```
~/.context-matters/
├── cm.db               # SQLite database (WAL mode)
├── cm.db-wal           # WAL file (auto-managed)
├── cm.db-shm           # shared memory file (auto-managed)
└── .cm.config.toml     # optional config file
```

### Config Implementation (cm-store/src/config.rs)

```rust
use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct Config {
    pub data_dir: PathBuf,
    pub log_level: String,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            data_dir: default_base_dir(),
            log_level: "info".to_string(),
        }
    }
}

fn default_base_dir() -> PathBuf {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home).join(".context-matters")
}

/// Load config with precedence: env vars > TOML file > defaults.
pub fn load() -> Config { /* ... */ }
```

## 6. Build and Test Setup

### justfile

```just
default:
    @just --list

build:
    cargo build --workspace

test:
    cargo test --workspace

fmt:
    cargo fmt --all

clippy:
    cargo clippy --workspace --all-targets --fix --allow-dirty -- -D warnings

check: fmt clippy

check-pedantic:
    cargo clippy -p cm-core --all-targets -- -W clippy::pedantic -D warnings

install:
    cargo install --path crates/cm-cli

serve-dev:
    cargo run -p cm-cli -- serve

# Run with verbose logging
serve-debug:
    CM_LOG_LEVEL=debug cargo run -p cm-cli -- serve

# Regenerate sqlx offline query cache (commit .sqlx/ after running)
sqlx-prepare:
    cargo sqlx prepare --workspace
```

### Release Profile

In workspace Cargo.toml:

```toml
[profile.release]
lto = true
codegen-units = 1
strip = true
opt-level = 3
```

### Test Infrastructure

**cm-core tests**: Pure unit tests. No external dependencies, no async. Test type construction, validation, query builder logic.

**cm-store tests**: Integration tests using in-memory SQLite via sqlx's `SqlitePool::connect(":memory:")`. Test migrations, CRUD operations, FTS5 queries, scope filtering. All tests are `#[tokio::test]`.

**cm-cli tests**: End-to-end tests using `assert_cmd` to invoke the compiled binary. Test that `cm serve` starts and responds to MCP initialization, `cm stats` prints output.

### sqlx Migrations Directory

Migrations live in `crates/cm-store/migrations/` and are embedded at compile time via `sqlx::migrate!()`.

```
crates/cm-store/migrations/
├── 001_initial_schema.sql        # core tables: entries, scopes, entry_relations
├── 002_fts5_setup.sql            # FTS5 virtual table + sync triggers
└── 003_triggers.sql              # updated_at trigger, FTS sync triggers
```

Migration filenames use sequential numbering (001, 002, ...) for deterministic ordering across environments. sqlx supports this naming pattern and tracks applied migrations in a `_sqlx_migrations` table automatically. Subsequent migrations continue the sequence (004, 005, ...).

### sqlx Compile-Time Checking Setup

sqlx's `query!()` macro validates SQL against a real database at compile time. This requires either a live database connection or cached query metadata.

**Development workflow:**
- Create a `.env` file at the workspace root: `DATABASE_URL=sqlite:~/.context-matters/cm.db`
- sqlx reads this automatically during compilation
- Add `.env` to `.gitignore`

**CI workflow (offline mode):**
- Run `cargo sqlx prepare --workspace` locally after changing any SQL queries
- This generates a `.sqlx/` directory with cached query metadata
- Commit `.sqlx/` to the repo
- CI builds use the cached metadata, requiring no database connection

**justfile recipe:**
```just
sqlx-prepare:
    cargo sqlx prepare --workspace
```

**FTS5 limitation:** `sqlx::query!()` compile-time checking does not work reliably with FTS5 MATCH syntax. Virtual table column semantics break the EXPLAIN-based type inference that the macro relies on (see sqlx issue #1637). Use runtime-checked `sqlx::query()` for all FTS5 queries. Use `sqlx::query!()` for standard table CRUD where compile-time checking provides value.

**Early development:** If compile-time checking proves cumbersome before the schema stabilizes, use `sqlx::query()` everywhere initially and migrate standard CRUD queries to `sqlx::query!()` later. FTS5 queries must always use `sqlx::query()`.

### CLAUDE.md

```markdown
# context-matters

Rust workspace implementing a structured context store for AI agents, served as an MCP server.

## Architecture

- `cm-core` - Domain types, ContextStore trait, query construction. Zero I/O.
- `cm-store` - SQLite adapter via sqlx. Schema, migrations, config.
- `cm-cli` - CLI binary and MCP server.

## Commands

\`\`\`sh
just check    # fmt + clippy with warnings-as-errors
just build    # cargo build --workspace
just test     # cargo test --workspace
just fmt      # cargo fmt
\`\`\`

## Conventions

- Tool prefix: `cx_`
- Database: `~/.context-matters/cm.db`
- Config: `~/.context-matters/.cm.config.toml`
- All timestamps: chrono DateTime<Utc>, stored as ISO 8601
- IDs: UUID v7 (time-sortable), stored as lowercase hex TEXT in SQLite
- Content hashing: BLAKE3 for deduplication
- Tool documentation: centralized in `tools.toml`, generated by `build.rs`
- MCP server: manual JSON-RPC over stdio (no rmcp), same pattern as fmm
```

### release-please-config.json

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "packages": {
    ".": {
      "release-type": "simple",
      "component": "context-matters",
      "include-component-in-tag": false,
      "bump-minor-pre-major": true,
      "bump-patch-for-minor-pre-major": true,
      "extra-files": [
        {
          "type": "toml",
          "path": "Cargo.toml",
          "jsonpath": "$.workspace.package.version"
        },
        {
          "type": "json",
          "path": "npm/context-matters/package.json",
          "jsonpath": "$.version"
        }
      ],
      "changelog-sections": [
        { "type": "feat", "section": "Features" },
        { "type": "fix", "section": "Bug Fixes" },
        { "type": "perf", "section": "Performance" },
        { "type": "refactor", "section": "Refactoring", "hidden": true },
        { "type": "docs", "section": "Documentation", "hidden": true },
        { "type": "chore", "section": "Miscellaneous", "hidden": true },
        { "type": "test", "section": "Tests", "hidden": true },
        { "type": "ci", "section": "CI", "hidden": true }
      ]
    }
  }
}
```

## 7. Complete File Manifest

Every file that needs to be created, with its purpose:

### Root

| File | Purpose |
|---|---|
| `Cargo.toml` | Workspace definition, shared dependencies |
| `Cargo.lock` | Dependency lockfile (committed) |
| `tools.toml` | Single source of truth for all tool and parameter documentation |
| `justfile` | Build/test/lint recipes |
| `release-please-config.json` | Automated release versioning |
| `CLAUDE.md` | Project instructions for Claude Code |
| `README.md` | Project documentation |
| `.gitignore` | Standard Rust gitignore + `.context-matters/` + `.env` |
| `.sqlx/` | Cached query metadata for sqlx offline mode (committed) |
| `.env` | `DATABASE_URL` for sqlx compile-time checking (gitignored) |

### crates/cm-core/

| File | Purpose |
|---|---|
| `Cargo.toml` | Crate manifest (domain types, no I/O deps) |
| `src/lib.rs` | Public API re-exports |
| `src/types.rs` | `Entry`, `Scope`, `Kind` (enum), `Tag`, `EntryMetadata` |
| `src/error.rs` | `CmError` enum via thiserror |
| `src/store.rs` | `ContextStore` trait with synchronous methods |
| `src/query.rs` | `QueryBuilder` for structured query construction |

### crates/cm-store/

| File | Purpose |
|---|---|
| `Cargo.toml` | Crate manifest (sqlx, tokio) |
| `src/lib.rs` | Public API: `CmStore`, `Config`, `load` |
| `src/sqlite.rs` | `SqliteContextStore` implementing `ContextStore` |
| `src/schema.rs` | SQLite pragma setup, post-migration validation |
| `src/config.rs` | TOML + env var config loading |
| `src/project.rs` | `default_base_dir()`, directory creation |
| `migrations/001_initial_schema.sql` | Core tables: entries, scopes, entry_relations |
| `migrations/002_fts5_setup.sql` | FTS5 virtual table and sync triggers |
| `migrations/003_triggers.sql` | updated_at trigger, FTS sync triggers |

### crates/cm-cli/

| File | Purpose |
|---|---|
| `Cargo.toml` | Crate manifest (tokio, clap, serde_json) |
| `build.rs` | Reads `../../tools.toml`, generates MCP schema + CLI help + skill docs |
| `src/main.rs` | CLI entry point, clap parser, serve/stats commands |
| `src/mcp/mod.rs` | McpServer struct, JSON-RPC stdio loop (follows fmm pattern) |
| `src/mcp/schema.rs` | Loads generated_schema.rs for tools/list response |
| `src/mcp/generated_schema.rs` | AUTO-GENERATED by build.rs from tools.toml |
| `src/mcp/tools/mod.rs` | Tool dispatch and shared helpers |
| `src/mcp/tools/*.rs` | One file per cx_* tool handler |
| `src/cli/mod.rs` | CLI subcommand implementations |
| `src/cli/generated_help.rs` | AUTO-GENERATED by build.rs from tools.toml |

### npm/context-matters/

| File | Purpose |
|---|---|
| `package.json` | npm package manifest |
| `bin/cm` | Shell stub (replaced by install.js) |
| `scripts/install.js` | GitHub release binary downloader |

### GitHub Actions (future, not blocking v0.1.0)

| File | Purpose |
|---|---|
| `.github/workflows/ci.yml` | Build, test, clippy, fmt check |
| `.github/workflows/release.yml` | Cross-compile binaries, npm publish |
| `.github/workflows/release-please.yml` | Automated version bumps |
