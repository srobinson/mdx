---
title: Rust Multi-Interface Workspace Patterns (CLI + Server + MCP)
type: research
tags: [rust, workspace, architecture, cli, mcp, http-server, hexagonal, traits, cargo]
summary: How production Rust projects architect workspaces that serve CLI, HTTP, MCP, LSP, and WASM interfaces from shared core crates, with trait-based abstraction boundaries and workspace inheritance for build/release.
status: active
source: deep-research
confidence: high
created: 2026-03-18
updated: 2026-03-18
---

## Executive Summary

Production Rust projects converge on a layered workspace pattern: a zero-I/O core/domain crate defining traits as ports, adapter crates implementing those traits against concrete infrastructure, and thin binary crates (CLI, HTTP server, MCP server, LSP) that wire adapters to the core. Workspace inheritance (`workspace.package`, `workspace.dependencies`) eliminates duplication. Release tooling (release-plz, cargo-release) handles multi-crate publish ordering. The pattern scales from 3 crates (context-matters) to 220+ crates (Zed).

## 1. Workspace Layout Patterns

### The Universal Structure

Every major Rust project examined follows the same structural skeleton:

```
project/
  Cargo.toml              # virtual manifest (no [package])
  Cargo.lock
  crates/
    project-core/          # domain types, traits, zero I/O
    project-store/         # database adapter
    project-cli/           # thin CLI binary
    project-server/        # HTTP/MCP/LSP binary
  justfile OR xtask/       # build automation
```

The root `Cargo.toml` is a **virtual manifest** containing only `[workspace]`. Matklad (rust-analyzer author) is emphatic: "putting the main crate into the root pollutes the root with `src/`, requires passing `--workspace` to every Cargo command, and adds an exception to an otherwise consistent structure."

### Real Project Crate Counts

| Project | Crates | Binaries | Domain |
|---------|--------|----------|--------|
| Zed | ~220 | 1 (editor) | Code editor |
| Vector | ~93 | 1 (vector) | Observability pipeline |
| Biome | ~80 | 2 (CLI, LSP) + WASM | JS/TS tooling |
| Ruff | ~45 | 2 (CLI, LSP) + WASM | Python linter/formatter |
| uv | ~40 | 3 (uv, uvx, uvw) | Python package manager |
| Nushell | ~39 | 1 (nu) | Shell |
| context-matters | 3 | 1 (cm-cli) | Context store |

### Flat Layout Consensus

All projects above use a flat `crates/` directory. Matklad's recommendation has become standard practice: "Even comparatively large lists are easier to understand at a glance than even small trees." Nested hierarchies create placement ambiguity and rot over time.

Some projects (Ruff, Biome) use prefixed crate names (`ruff_linter`, `biome_js_parser`) to create logical grouping within the flat namespace. Others (uv) use a project prefix on everything (`uv-resolver`, `uv-cache`).

### Internal vs. Publishable Crates

Matklad recommends `version = "0.0.0"` for internal crates with no publish intent, reserving a separate `libs/` directory for crates intended for crates.io. In practice, most projects version all crates identically using workspace inheritance and publish selectively via `publish = false` in individual Cargo.toml files.

## 2. Trait-Based Abstraction Boundaries

### The Ports and Adapters Pattern in Rust

The hexagonal architecture maps cleanly to Rust's trait system. The core crate defines **port traits** that external systems must satisfy:

```rust
// In core crate -- zero I/O dependencies
pub trait AuthorRepository: Clone + Send + Sync + 'static {
    fn create_author(
        &self,
        req: &CreateAuthorRequest,
    ) -> impl Future<Output = Result<Author, CreateAuthorError>> + Send;
}
```

Adapter crates implement these traits against concrete infrastructure:

```rust
// In store crate -- depends on sqlx
impl AuthorRepository for Sqlite {
    async fn create_author(&self, req: &CreateAuthorRequest)
        -> Result<Author, CreateAuthorError> {
        // sqlx queries here
    }
}
```

Binary crates wire everything together in `main()`:

```rust
// In cli crate -- thin orchestrator
#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let sqlite = Sqlite::new(&config.database_url).await?;
    let service = Service::new(sqlite);
    let http_server = HttpServer::new(service).await?;
    http_server.run().await
}
```

### Trait Boundary Patterns Across Projects

**Biome** uses a `Workspace` trait as the single abstraction consumed by CLI, LSP, and WASM frontends. All operations (format, lint, organize imports) go through this trait. The CLI handles file traversal; the LSP maintains per-document state. Both delegate actual work through the same `Workspace` implementation.

**Nushell** defines a `Command` trait that every built-in command, custom command, and plugin implements. The trait requires `name()`, `signature()`, and `run()` methods. Plugins communicate via process-isolated JSON-RPC but implement the same trait interface, making them indistinguishable from built-ins after registration.

**Vector** uses three component trait families: `SourceConfig` (data ingestion), `FunctionTransform`/`TaskTransform` (processing), and `VectorSink` (output). Each component type has a config trait with a `build()` method that returns async runtime tasks.

**Zed** uses trait-based abstractions for testability: `Fs` trait for file operations (with `FakeFs` for tests), `Item` trait for anything displayable in panes, `Panel` trait for dockable containers. The `Project` entity uses "store" sub-entities (`WorktreeStore`, `BufferStore`, `LspStore`) to encapsulate domain-specific state.

**Ruff** uses a `Db` trait (Salsa query boundary) for incremental computation, enabling fine-grained cache invalidation across the linter and type checker.

### Common Trait Bounds

Production port traits consistently require `Clone + Send + Sync + 'static`. This enables:
- Sharing across Tokio tasks (`Send + Sync`)
- Embedding in Axum state (`Clone + Send + Sync + 'static`)
- Arc wrapping for concurrent access

### The Service Struct Pattern

A generic service struct parameterized by its ports is the standard composition mechanism:

```rust
pub struct Service<R: Repository, M: Metrics, N: Notifier> {
    repo: R,
    metrics: M,
    notifier: N,
}
```

This avoids trait objects (`dyn`) and dynamic dispatch in the hot path while keeping the core testable with mock implementations.

## 3. Shared Core, Multiple Frontends

### The Dependency Diamond

The canonical dependency flow is unidirectional:

```
CLI binary ──┐
HTTP binary ──┤
MCP binary ──┤──→ service/orchestration ──→ core (traits + types)
LSP binary ──┤                     │
WASM target ─┘                     └──→ store adapter
```

Each binary crate depends on:
1. The core crate (for domain types)
2. The adapter crate(s) (for concrete implementations)
3. Its own interface-specific dependencies (clap for CLI, axum for HTTP, etc.)

### Thin Binary Pattern

The binary crate's `main.rs` should contain only:
1. Configuration loading
2. Adapter construction
3. Service wiring
4. Runtime launch

BurntSushi (ripgrep author) notes that "The dependencies for a library may be quite different than the dependencies for a command line application." CLI tools need argv parsers and terminal formatting; HTTP servers need web frameworks. Keeping these in separate binary crates prevents dependency contamination.

### Biome's Exemplar Pattern

Biome demonstrates the cleanest multi-frontend architecture:

```
biome_cli  ─────────┐
biome_lsp  ─────────┤──→ biome_service::Workspace trait
biome_wasm ─────────┘         │
                              ├──→ biome_js_parser
                              ├──→ biome_js_formatter
                              ├──→ biome_js_analyze
                              └──→ biome_css_*, biome_json_*, ...
```

Adding a new frontend (WASM) required zero changes to language-specific crates. Adding a new language required zero changes to frontend crates.

### Zed's Remote Architecture

Zed separates `Workspace` (UI coordinator, runs locally) from `Project` (service coordinator, can run remotely). This dual-mode architecture uses `Local` and `Remote` enum variants for major components, allowing "the same high-level code to work with both local and remote projects without knowing the difference."

## 4. Build and Release

### Workspace Inheritance (Cargo 1.64+)

All examined projects use workspace inheritance for version, edition, and dependency management:

```toml
[workspace.package]
version = "0.1.5"
edition = "2024"
license = "MIT"

[workspace.dependencies]
serde = { version = "1", features = ["derive"] }
tokio = { version = "1", features = ["macros", "rt-multi-thread"] }
```

Member crates reference these with `version.workspace = true` and `serde = { workspace = true }`. This eliminates version drift across the workspace.

### Build Automation

Two patterns dominate:

**Justfile** (simpler projects): Task runner with recipes for `check`, `build`, `test`, `fmt`. Used by context-matters and many smaller projects.

```just
check:
    cargo fmt --check
    cargo clippy --workspace -- -D warnings

test:
    cargo test --workspace
```

**cargo xtask** (larger projects): A dedicated Rust crate in the workspace that implements build automation. Matklad recommends this over shell scripts: "write all automation in Rust in a dedicated crate." Used by rust-analyzer, Zed.

### Release Tooling

Three tools handle multi-crate workspace releases:

| Tool | Approach | Best For |
|------|----------|----------|
| **release-plz** | Compares local vs. registry, generates release PRs with changelogs | Automated CI-driven releases |
| **cargo-release** | Extends `cargo publish` with validation, tagging, version bumps | Manual release workflows |
| **cargo-workspaces** | Publishes all workspace crates in dependency order | Synchronized multi-crate publishes |

A key challenge: Cargo refuses to publish crate A if crate B (which A depends on) has a new version that is not yet on the registry. Tools solve this by publishing in topological dependency order.

### Cargo Features for Multi-Binary

Two strategies for conditional compilation:

1. **required-features**: Binaries declare features they need; `cargo build` skips binaries whose features are disabled.

2. **Feature-gated dependencies**: The workspace defines optional feature groups (e.g., `server = ["axum", "tower"]`, `cli = ["clap"]`) and binary crates activate only what they need.

Vector uses 504+ lines of feature flags in its root Cargo.toml to enable conditional compilation by cloud provider (AWS, GCP, Azure) and data type (logs, metrics, traces).

### Release Profile Optimization

Production builds consistently use:

```toml
[profile.release]
lto = true          # link-time optimization
codegen-units = 1   # single codegen unit for max optimization
strip = true        # strip debug symbols
opt-level = 3       # maximum optimization
```

### Multi-Platform Distribution

Projects ship via multiple channels:
- **maturin**: Python wheels wrapping Rust binaries (Ruff, uv)
- **cargo-dist**: Multi-platform binary releases with GitHub Actions
- **wasm-pack**: WebAssembly targets (Biome, Ruff)
- **npm wrappers**: Node.js packages bundling platform-specific binaries

### Compile Time Optimization via Crate Splitting

Crates compile in parallel when they don't depend on each other. Splitting a monolithic crate into focused sub-crates enables parallel compilation and incremental rebuilds (only changed crates recompile). Feldera achieved a 12-22x speedup by splitting generated code into 1,100 crates, though this extreme approach only makes sense for codegen. For hand-written code, 30-80 well-scoped crates is the practical sweet spot for large projects.

## Sources Consulted

### Blog Posts and Guides
- [Master Hexagonal Architecture in Rust](https://www.howtocodeit.com/articles/master-hexagonal-architecture-rust) - howtocodeit.com
- [Large Rust Workspaces](https://matklad.github.io/2021/08/22/large-rust-workspaces.html) - matklad (rust-analyzer author)
- [Cutting Down Compile Times from 30 to 2 Minutes](https://www.feldera.com/blog/cutting-down-rust-compile-times-from-30-to-2-minutes-with-one-thousand-crates) - Feldera
- [Hexagonal Architecture in Rust](http://tuttlem.github.io/2025/08/31/hexagonal-architecture-in-rust.html) - Cogs and Levers (Aug 2025)
- [Structuring Rust Projects with Multiple Binaries](https://www.justanotherdot.com/posts/structuring-rust-projects-with-multiple-binaries.html) - Ryan James Spencer

### DeepWiki Architecture Analyses
- [Biome](https://deepwiki.com/biomejs/biome) - ~80 crates, Workspace trait, CLI/LSP/WASM frontends
- [Ruff](https://deepwiki.com/astral-sh/ruff) - ~45 crates, four-layer architecture, CLI/LSP/WASM
- [uv](https://deepwiki.com/astral-sh/uv) - ~40 crates, thin binary pattern, layered services
- [Nushell](https://deepwiki.com/nushell/nushell) - ~39 crates, Command trait, plugin system
- [Vector](https://deepwiki.com/vectordotdev/vector) - ~93 crates, component traits, DAG topology
- [Zed](https://deepwiki.com/zed-industries/zed/1-overview) - ~220 crates, Entity/Store pattern, remote architecture

### GitHub Discussions
- [src/main.rs and src/lib.rs pattern](https://github.com/rust-lang/api-guidelines/discussions/167) - Rust API Guidelines
- [Conditional compilation of workspace members](https://github.com/rust-lang/cargo/issues/11526)

### Cargo Documentation
- [Workspaces](https://doc.rust-lang.org/cargo/reference/workspaces.html)
- [Features](https://doc.rust-lang.org/cargo/reference/features.html)
- [RFC 2906: Workspace Deduplication](https://rust-lang.github.io/rfcs/2906-cargo-workspace-deduplicate.html)

### Release Tooling
- [release-plz](https://github.com/release-plz/release-plz)
- [cargo-release](https://github.com/crate-ci/cargo-release)

## Source Quality Assessment

**High confidence**: Workspace layout patterns are well-established with convergent evidence across 6+ major projects. Trait boundary patterns are consistently documented. Build/release tooling is mature.

**Medium confidence**: The hexagonal architecture mapping to Rust traits is well-described in blog posts but less visible in production code of the examined projects (which tend toward pragmatic layering rather than strict hex). Conference talk coverage is thin for 2025-2026 on this specific topic.

**Gaps**: Limited community discussion on Reddit/HN specifically about multi-interface (CLI + HTTP + MCP) workspace design. Most discussion centers on single-binary projects or library-only workspaces. MCP server workspace patterns are emerging (2025-2026) with limited established convention.

## Open Questions

1. **MCP + HTTP in one binary vs. separate binaries**: No clear consensus. Some projects run MCP as a stdio subprocess and HTTP as a TCP server from the same binary with feature flags. Others split them into separate binary crates. The right answer likely depends on deployment model.

2. **Trait objects vs. generics at the binary boundary**: Projects differ on whether to use `dyn Service` (dynamic dispatch, simpler wiring) or `Service<SqliteRepo, PrometheusMetrics>` (static dispatch, zero overhead). Larger projects (Vector, Nushell) lean toward trait objects for plugin flexibility. Smaller projects lean toward generics.

3. **When to split a crate**: No quantitative guidance. Matklad suggests splitting when you want parallelism or isolation. The Ruff team split `ruff_linter` when compile times degraded. Most teams split too late rather than too early.

## Actionable Takeaways

For a project like context-matters (currently 3 crates: core, store, cli) planning to add HTTP and MCP server interfaces:

1. **Keep the core crate zero-I/O**. Define `ContextStore` as a trait in core. The current store crate implements it against SQLite.

2. **Add binary crates, not features**. Create `crates/cm-http/` and keep `crates/cm-cli/` separate. Each binary depends on `cm-core` + `cm-store` and brings its own interface-specific dependencies.

3. **The thin binary pattern is correct**. Each binary's `main.rs` should construct the `SqliteStore`, wrap it in the service, and launch its interface (clap dispatch for CLI, axum router for HTTP, stdio JSON-RPC for MCP).

4. **Use workspace inheritance for everything**. Version, edition, license, and shared dependencies should all live in the root `Cargo.toml`.

5. **Justfile is fine at this scale**. Switch to `cargo xtask` only when build automation requires Rust-level logic (codegen, asset processing).

6. **release-plz for CI-driven releases**. It handles changelog generation, version bumps, and topological publish ordering automatically.
