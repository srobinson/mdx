---
title: Helioy Rust Architecture Proposal
date: 2026-03-18
tags: [rust, architecture, helioy, mcp, workspace, proposal]
type: proposal
status: draft
---

# Helioy Rust Architecture Proposal

A reference architecture for all Rust crates in the helioy ecosystem, synthesized from community research, production patterns, and the current state of context-matters, attention-matters, frontmatter-matters, and nancyr.

## 1. Current State

The helioy ecosystem has four Rust projects at different maturity levels:

| Project | Layout | Crates | MCP Approach | DB | Edition |
|---------|--------|--------|-------------|-----|---------|
| context-matters | workspace, `crates/` flat | 3 (core/store/cli) | Manual JSON-RPC | sqlx + SQLite | 2024 |
| attention-matters | workspace, `crates/` flat | 3 (core/store/cli) | rmcp 0.15 | rusqlite | 2024 |
| frontmatter-matters | single crate | 1 | Manual JSON-RPC | rusqlite | 2021 |
| nancyr | workspace, `crates/` flat | 6 (core/driver/monitor/brain/cli/runtime) | N/A | N/A | 2021 |

context-matters is the most architecturally mature. It already follows the hexagonal pattern the research identifies as consensus: zero-I/O core crate with a `ContextStore` trait, SQLite adapter crate, thin CLI binary with MCP server. attention-matters mirrors this structure. frontmatter-matters is a monolith that predates the workspace pattern. nancyr has the right workspace layout but uses edition 2021 and cross-workspace path dependencies (importing am-core/am-store directly).

## 2. Consensus Patterns from the Research

Four research documents covering workspace layout, MCP servers, HTTP servers, and testing/DI converge on these patterns:

### 2.1 Workspace Layout

**Consensus**: Virtual manifest root, flat `crates/` directory, workspace inheritance for version/edition/dependencies, `{project}-` prefix on crate names. Every major Rust project (Zed, Ruff, uv, Biome, Vector, Nushell) follows this.

**context-matters alignment**: Full. Virtual manifest, flat `crates/`, workspace inheritance for version/edition/license/dependencies. The `cm-` prefix convention is correct.

**Gaps**:
- frontmatter-matters is a monolith. It should adopt the workspace pattern.
- nancyr uses `resolver = "2"` and edition 2021. Both should be updated to resolver 3 and edition 2024.
- nancyr imports am-core and am-store via relative path dependencies across workspace boundaries. This creates an implicit coupling that breaks independent builds.

### 2.2 Trait Boundaries (Hexagonal Architecture)

**Consensus**: Core crate defines port traits with zero I/O. Adapter crates implement traits against concrete infrastructure. Binary crates wire adapters to core. Port traits require `Clone + Send + Sync + 'static` for async compatibility.

**context-matters alignment**: Partial. `ContextStore` trait in cm-core is well-defined with thorough documentation. However, the trait uses synchronous signatures and the store crate uses sqlx's async API, creating an impedance mismatch noted in the trait's doc comment. The trait is also not bounded by `Send + Sync`.

**attention-matters alignment**: Uses rmcp's `#[tool_router]` macros, which handle dispatch internally. The core/store/cli split follows the same pattern.

**Gap**: The `ContextStore` trait's synchronous signatures work today because sqlx uses `block_in_place` internally, but this becomes a problem if a second adapter (HTTP, in-memory test store) is added. The trait should use async signatures.

### 2.3 MCP Server Architecture

**Consensus**: Two viable approaches. rmcp (5.3M+ downloads, Tier 2 conformance) for macro-driven schema generation. Manual JSON-RPC for teams wanting full protocol control or external schema sources. Both are production-proven.

**Helioy split**: context-matters and frontmatter-matters use manual JSON-RPC with `tools.toml` + `build.rs` schema generation. attention-matters uses rmcp 0.15.

**Assessment**: The manual approach is the right choice for context-matters. The `tools.toml` pattern produces a single source of truth for MCP schemas, CLI help text, and SKILL.md documentation. rmcp's macros derive schemas from Rust types, which inverts the ownership: the schema serves the agent, not the compiler. Having tool descriptions, parameter names, and enum values defined in a human-readable TOML file that generates code is superior to scattering `#[tool(description = "...")]` annotations across impl blocks.

**Recommendation**: Standardize on manual JSON-RPC + `tools.toml` for all helioy MCP servers. attention-matters should migrate away from rmcp. The protocol surface for a tools-only stdio server is approximately 100 lines of routing code; the rmcp dependency adds proc-macro compile time and macro-generated code that is harder to debug.

### 2.4 Error Handling

**Consensus**: `thiserror` in library crates, `anyhow` at the application boundary, `IntoResponse` mapping for HTTP. For MCP: return operational errors as successful tool responses with recovery guidance, reserve JSON-RPC errors for infrastructure failures.

**context-matters alignment**: Full. `CmError` uses thiserror in cm-core. `cm_err_to_string()` in the CLI crate converts domain errors to actionable messages with recovery guidance ("Entry not found. Verify the ID using cx_browse or cx_recall."). The `isError:true` workaround for Claude Code's Promise.all bug is implemented.

**No changes needed here.** This is already best-in-class.

### 2.5 HTTP Server (Future Interface)

**Consensus**: Axum 0.8 is the default. `State<AppState>` for type-safe injection. tower-http middleware stack (TraceLayer, CorsLayer, CompressionLayer, TimeoutLayer). `thiserror` domain errors mapped to HTTP status codes via `IntoResponse`.

**Helioy relevance**: nancyr already depends on axum 0.8. No helioy crate currently serves HTTP, but if context-matters or attention-matters add an HTTP API, axum is the correct choice.

### 2.6 Testing and DI

**Consensus**: Trait-based DI with manual stubs over heavy mocking. `#[sqlx::test]` for database integration tests. `assert_cmd` for CLI integration tests. `cargo-nextest` for parallel execution. `proptest` for serialization round-trips. `insta` for snapshot testing.

**context-matters alignment**: Good. Unit tests cover helpers (clamping, snippets, cursor encoding, error formatting). Integration tests use in-memory SQLite. 1,288 LOC of integration tests in cm-store, 744 LOC in cm-cli.

**Gaps**:
- No `#[sqlx::test]` usage. Tests manually create in-memory pools.
- No snapshot testing for MCP tool output format stability.
- No CLI integration tests via `assert_cmd` (MCP protocol tests use the tool handlers directly, bypassing the JSON-RPC loop).
- No subprocess integration tests for the stdio MCP server.

### 2.7 CI/CD and Release

**Consensus**: `dtolnay/rust-toolchain@stable` + `Swatinem/rust-cache@v2` + `cargo-nextest`. `release-plz` for automated versioning and changelog generation. `cargo-dist` for binary releases.

**context-matters alignment**: Already uses release-plz (evidenced by `chore(main): release` commits in git history). Already uses conventional commits.

**Gap**: No evidence of `cargo-nextest` in the justfile. The `just test` recipe uses `cargo test --workspace`.

## 3. Reference Architecture

The following is the target architecture for all helioy Rust workspaces. It codifies what context-matters already does well and fills the gaps identified above.

### 3.1 Workspace Layout

```
{project}/
  Cargo.toml              # virtual manifest, [workspace] only
  Cargo.lock
  justfile                 # check, build, test, fmt, install
  tools.toml               # tool + CLI command definitions (single source of truth)
  crates/
    {prefix}-core/         # domain types, traits, error types. Zero I/O.
    {prefix}-store/        # database adapter (sqlx or rusqlite)
    {prefix}-cli/          # CLI binary + MCP stdio server
    {prefix}-http/         # HTTP binary (when needed)
  .github/
    workflows/
      ci.yml               # fmt, clippy, nextest, coverage
      release.yml          # release-plz
```

**Naming convention**: `cm-` for context-matters, `am-` for attention-matters, `fmm-` for frontmatter-matters, `nancy-` for nancyr.

**Workspace Cargo.toml requirements**:
- `resolver = "3"`, edition 2024
- `[workspace.package]` for version, edition, license, repository
- `[workspace.dependencies]` for all shared dependencies
- `[profile.release]` with lto, codegen-units=1, strip, opt-level=3

### 3.2 Core Crate Contract

The core crate defines the domain. It has zero I/O dependencies. No sqlx, no tokio, no network, no filesystem.

```rust
// {prefix}-core/src/lib.rs
pub mod types;   // Domain structs, enums
pub mod error;   // thiserror enums
pub mod store;   // Port trait(s)
pub mod query;   // Query builders, filters
```

**Trait design rules**:
1. **Async/sync depends on the store backend.** sqlx projects use async signatures. rusqlite projects use sync signatures. Do not force async on a sync store; the impedance mismatch adds complexity without benefit for single-client stdio servers.
2. Trait bounds: `Send + Sync + 'static` on the trait itself (async projects) or on the associated error type (sync projects).
3. **Associated error type, not concrete.** Core is zero-I/O and must not depend on rusqlite or sqlx. Use `type Error: std::error::Error + Send + Sync + 'static` so each adapter brings its own error type. This was validated in attention-matters where `BrainStore` sets `Error = StoreError` (wrapping `rusqlite::Error`) and `InMemoryStore` uses a trivial enum.
4. Return `Result<T, Self::Error>`.
5. Document every method with `# Errors` section listing possible error variants.
6. **Trait scope: full persistence port.** Include all persistence operations (both MCP server and CLI), not just the server surface. This keeps all store access behind one contract and enables test doubles for CLI code paths too.

```rust
// Async variant (sqlx projects like context-matters)
pub trait ContextStore: Send + Sync + 'static {
    async fn create_entry(&self, new_entry: NewEntry) -> Result<Entry, CmError>;
    async fn get_entry(&self, id: Uuid) -> Result<Entry, CmError>;
    // ...
}

// Sync variant (rusqlite projects like attention-matters, frontmatter-matters)
pub trait AmStore {
    type Error: std::error::Error + Send + Sync + 'static;
    fn load_system(&self) -> Result<DAESystem, Self::Error>;
    fn save_system(&self, system: &DAESystem) -> Result<(), Self::Error>;
    // ...
}
```

**Consumer pattern: generics, not `dyn`.** All consumers use generics: `McpServer<S: Store>`, tool handlers take `&S` where `S: Store`. This is zero-cost (monomorphized) and makes the trait the real programming interface. The concrete store type is chosen only in `main.rs`.

**InMemoryStore must be `Send`.** If the server wraps state in `std::sync::Mutex` (which requires `T: Send`), the test store must also be `Send`. Use `std::sync::Mutex` (not `RefCell`) for interior mutability in test stores. This was a concrete issue in attention-matters where `RefCell`-based `InMemoryStore` could not be used with `AmServer`.

### 3.3 Store Crate Contract

Implements the core trait against a concrete database. Owns the schema, migrations, connection pooling, and configuration.

```rust
// {prefix}-store/src/lib.rs
pub struct {Prefix}Store { /* pool(s) */ }

impl {prefix}_core::ContextStore for {Prefix}Store {
    async fn create_entry(&self, new_entry: NewEntry) -> Result<Entry, CmError> {
        // sqlx queries
    }
}
```

**Database choice**:
- **rusqlite + tokio-rusqlite** as the default for new helioy MCP servers. Simpler, honest about the threading model, lower dependency weight.
- **sqlx + SQLite** for projects already invested in sqlx's migration framework (context-matters). Note: sqlx's SQLite backend is not truly async. It uses a dedicated thread per connection with channel dispatch. The async API is a convenience wrapper, not a performance advantage over rusqlite for single-client stdio servers.
- **rusqlite (bare)** for CPU-bound indexers (frontmatter-matters). No async overhead. `spawn_blocking` at the boundary when called from async code.

context-matters staying on sqlx is the right call given its existing migration infrastructure and test setup. New helioy Rust projects should default to rusqlite + tokio-rusqlite unless there is a specific reason to prefer sqlx.

### 3.4 CLI + MCP Crate

The binary crate is a thin orchestrator. Its `main.rs` contains only:
1. Argument parsing (clap)
2. Tracing initialization (stderr only)
3. Store construction
4. Subcommand dispatch

```rust
#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    init_tracing(cli.verbose);

    match cli.command {
        Commands::Serve => {
            let store = open_store().await?;  // CmStore: concrete type chosen here
            McpServer::new(store).run().await?;
        }
        Commands::Stats => { /* ... */ }
    }
}
```

The `McpServer` is generic over the store trait:

```rust
pub struct McpServer<S: ContextStore> {
    store: Arc<S>,
}
```

**MCP implementation**: Manual JSON-RPC over stdio. `tools.toml` + `build.rs` generates schemas and help text. Tool handlers are async functions generic over the store: `async fn cx_recall(store: &impl ContextStore, args: &Value) -> Result<String, String>`. Internal helpers like `ensure_scope_chain` follow the same pattern.

**Error-as-UI pattern**: All `CmError` variants convert to actionable strings with recovery guidance. Operational errors return as successful MCP responses. JSON-RPC errors reserved for protocol failures.

### 3.5 HTTP Crate (When Needed)

A separate binary crate for HTTP API access to the same store. Not needed for most helioy tools today. When added:

```rust
// {prefix}-http/src/main.rs
#[tokio::main]
async fn main() -> Result<()> {
    let store = open_store().await?;
    let state = AppState { store: Arc::new(store) };

    let app = Router::new()
        .route("/entries", get(list_entries).post(create_entry))
        .layer(ServiceBuilder::new()
            .layer(TraceLayer::new_for_http())
            .layer(CompressionLayer::new())
            .layer(TimeoutLayer::new(Duration::from_secs(30))))
        .with_state(state);

    axum::serve(listener, app).await?;
}
```

Domain errors map to HTTP status codes via `IntoResponse`:

```rust
impl IntoResponse for CmError {
    fn into_response(self) -> Response {
        let (status, msg) = match &self {
            CmError::EntryNotFound(_) => (StatusCode::NOT_FOUND, self.to_string()),
            CmError::DuplicateContent(_) => (StatusCode::CONFLICT, self.to_string()),
            CmError::Database(_) => (StatusCode::INTERNAL_SERVER_ERROR, "internal error".into()),
            // ...
        };
        (status, Json(json!({ "error": msg }))).into_response()
    }
}
```

### 3.6 Testing Strategy

**Layer 1: Unit tests in core crate.** Pure logic, no I/O. Types, validation, query construction, error formatting. These run instantly.

**Layer 2: Integration tests in store crate.** Use `#[sqlx::test]` (for sqlx projects) or manual in-memory SQLite. Each test gets an isolated database with migrations applied. Test all trait methods against real SQL.

**Layer 3: Tool handler tests in CLI crate.** Test each MCP tool handler function against an in-memory store. Verify response format, error messages, edge cases. Use `insta` for snapshot testing of response structures.

**Layer 4: Subprocess MCP protocol tests.** Spawn the compiled binary, send JSON-RPC messages via stdin, assert on stdout. Cover: initialize handshake, tools/list, tools/call, error responses, unknown methods. Use `assert_cmd` for this.

**Property testing**: Apply `proptest` to serialization round-trips (cursor encode/decode, entry serialization) and scope path parsing.

### 3.7 CI Pipeline

```yaml
# .github/workflows/ci.yml
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: Swatinem/rust-cache@v2
      - run: cargo fmt --all --check
      - run: cargo clippy --workspace --all-targets -- -D warnings
      - run: cargo install cargo-nextest --locked
      - run: cargo nextest run --workspace
```

**Release pipeline**: release-plz watches main for conventional commits, creates release PRs with changelogs, publishes to crates.io on merge. This is already in place for context-matters.

### 3.8 Build Automation

Justfile with standard recipes:

```just
default:
    @just --list

check: fmt clippy
build:
    cargo build --workspace
test:
    cargo nextest run --workspace
fmt:
    cargo fmt --all
clippy:
    cargo clippy --workspace --all-targets --fix --allow-dirty -- -D warnings
install:
    cargo install --path crates/{prefix}-cli
```

Switch `cargo test` to `cargo nextest run` for better isolation and parallel execution. Keep justfile over xtask; the helioy projects are not complex enough to warrant a Rust-based build system.

## 4. Cross-Workspace Concerns

### 4.1 Shared JSON-RPC Plumbing

context-matters and frontmatter-matters both implement the same manual JSON-RPC types (`JsonRpcRequest`, `JsonRpcResponse`, `JsonRpcError`) and the same stdio loop. This is approximately 100-150 lines duplicated across projects.

**Decision: Do not extract a shared crate.** The duplication is small, the code is simple, and extracting it creates a cross-workspace dependency that complicates independent releases. Each project's MCP server has project-specific protocol extensions (error handling, workarounds, server instructions). The cost of coordination exceeds the cost of duplication.

If the pattern stabilizes further and a third or fourth project needs it, reconsider. But for now, copy-paste is the correct strategy for ~100 lines of straightforward serde code.

### 4.2 The tools.toml + build.rs Pattern

This is the highest-value pattern to standardize. A single TOML file defining tool names, descriptions, parameter schemas, and CLI help text, with `build.rs` generating:
- `generated_schema.rs` for MCP `tools/list` responses
- `generated_help.rs` for CLI help strings (consumed by clap `#[command(about = ...)]`)
- `SKILL.md` for Claude Code skill documentation

**Scope: all commands, not just MCP tools.** tools.toml should define CLI-only commands (e.g., forget, import, export) alongside MCP tools. This prevents help text drift between the two surfaces. Commands that have no MCP equivalent simply omit the `mcp_description` field.

context-matters has this. frontmatter-matters has this. attention-matters has adopted it (Phase 2 migration complete).

### 4.3 Cross-Workspace Dependencies

nancyr currently imports `am-core` and `am-store` via relative path dependencies. This is fragile: it assumes a specific directory layout, breaks `cargo publish`, and creates hidden coupling.

**Options**:
1. Publish am-core and am-store to crates.io and depend on released versions.
2. Use a cargo workspace that spans both projects (monorepo).
3. Keep the path dependency but document the requirement.

**Recommendation**: Option 1 for production. Option 3 is acceptable during active development, but the path must be relative to the workspace root and documented in CLAUDE.md.

## 5. Concrete Next Steps

Ordered by impact and independence.

### 5.1 context-matters (High Priority)

1. **Migrate `ContextStore` trait to async signatures.** Change all `fn` to `async fn` in the trait. Update cm-store's impl. Update all tool handler call sites. This unblocks a clean in-memory test store and future HTTP adapter.

2. **Add `Send + Sync + 'static` bounds to `ContextStore` trait.** Required for generic `S: ContextStore` used across async task boundaries and in `Arc<S>`.

3. **Switch `just test` to `cargo nextest run --workspace`.** Better isolation, parallel execution, flaky test detection.

4. **Add `insta` snapshot tests for MCP tool response format.** Catch unintended format changes that break agent behavior.

5. **Add subprocess MCP protocol tests.** Use `assert_cmd` to spawn the binary and test the full JSON-RPC loop for initialize, tools/list, and one tools/call path.

### 5.2 attention-matters (Done)

~~6. **Migrate from rmcp to manual JSON-RPC + tools.toml.**~~ Complete (ALP-1468). rmcp, schemars, and tokio removed. Manual JSON-RPC + tools.toml + build.rs in place. AmStore trait with associated error type in am-core, BrainStore and InMemoryStore implementations, AmServer generic over `S: AmStore`. See `~/.mdx/projects/attention-matters-architecture-alignment.md` for the full spec.

7. Already on edition 2024, resolver 3.

### 5.3 frontmatter-matters (Medium Priority)

8. **Split into a workspace with fmm-core, fmm-store, fmm-cli.** The monolithic Cargo.toml mixes 15+ tree-sitter parsers, CLI deps, and database deps. Splitting isolates concerns and enables parallel compilation.

9. **Adopt workspace inheritance.** Version, edition, shared dependencies in root Cargo.toml.

10. **Update to edition 2024, resolver 3.**

### 5.4 nancyr (Lower Priority)

11. **Update to edition 2024, resolver 3.**

12. **Resolve the am-core/am-store path dependency.** Either publish to crates.io or document the layout requirement.

### 5.5 Ecosystem-Wide

13. **Standardize justfile recipes.** Every Rust project gets `check`, `build`, `test`, `fmt`, `clippy`, `install` with identical semantics.

14. **Standardize CI pipeline.** Copy the ci.yml template to all projects. dtolnay/rust-toolchain + Swatinem/rust-cache + nextest.

15. **Standardize release profile.** `lto = true`, `codegen-units = 1`, `strip = true`, `opt-level = 3`. Already present in context-matters and frontmatter-matters.

### 5.6 markdown-matters Migration Path

markdown-matters is currently TypeScript (39K LOC). An incremental migration to Rust is viable, starting with the highest-value, lowest-risk layer.

**Phase 1: Core indexing crate (`mdm-core`).** Markdown parsing via pulldown-cmark or comrak, plus SQLite FTS5 indexing. This is the performance-critical path and benefits most from Rust. Use rusqlite (not sqlx) since indexing is CPU-bound batch work. Ship as a workspace with `mdm-core`, `mdm-store`, `mdm-cli` following the reference architecture.

**Phase 2: MCP server.** Lift the manual JSON-RPC + tools.toml pattern from context-matters. The protocol surface is identical.

**Phase 3: Vector search.** The hnswlib-based vector search can stay TypeScript short-term or migrate later. This is the highest-risk, lowest-urgency component.

**TypeScript interim guidance:** If markdown-matters stays TypeScript short-term, migrate from better-sqlite3 to `node:sqlite` (built-in since Node 22.5). Eliminates the native addon build step and simplifies the dependency chain.

## 6. What This Proposal Does Not Cover

- **Inter-service communication.** helioy-bus handles agent messaging. This proposal covers individual Rust crate architecture, not the bus protocol.
- **helioy-bus and helioy-plugins.** helioy-bus (Python) and helioy-plugins (shell) are out of scope for Rust architecture guidance.
- **Deployment and distribution.** Binary packaging (cargo-dist, npm wrappers) is deferred until the projects are ready for public distribution.
- **Shared library extraction.** The research shows that premature extraction of shared crates is a common anti-pattern. Each helioy project should evolve independently until patterns genuinely stabilize across three or more projects.
