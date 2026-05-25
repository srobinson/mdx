---
title: Rust Coding Conventions, Standards, and Code Organization (2026)
type: research
tags: [rust, conventions, cargo, workspace, error-handling, async, clippy, edition-2024, api-design, testing, ci, performance]
summary: An opinionated, current reference for how serious Rust projects should be structured, built, tested, and maintained in 2026. Covers project layout, modules, API design, async, dependencies, lints, docs, unsafe, performance, macros, edition 2024, and anti-patterns.
status: active
confidence: high
created: 2026-05-26
updated: 2026-05-26
---

## Executive Summary

The Rust of 2026 is settled where it used to be ragged. Edition 2024 (stabilised with 1.85, February 2025) brings async closures, `let` chains in `if` and `while`, RPIT capture rule changes, and `unsafe extern` blocks, and the resolver finally respects `rust-version`. Workspaces with a virtual root `Cargo.toml`, a flat `crates/` directory, and inheritance for `package`, `dependencies`, and `lints` are the universal layout. Error handling has converged on `thiserror` for libraries and `anyhow` (or `color-eyre` when the binary is human-facing) for applications, with `n0-error` and `snafu` as serious options when backtraces or context chains matter. `tokio` is the assumed runtime; native async fn in traits (stable since 1.75) replaces `async-trait` for static dispatch, and `dynosaur` (or `async-trait` still) handles the `dyn Trait` case. Clippy with `pedantic = "warn"` at workspace level and source-level `#[allow]` for the noisy ones is the contemporary baseline. Tooling normal-cases on `cargo nextest`, `insta`, `cargo deny` (which subsumes `cargo audit`), `release-plz`, and `xtask`. Anti-patterns to avoid are wholesale `Arc<Mutex<_>>`, premature trait abstractions, hand-rolled async event loops, and `mod.rs` for new modules. The biggest internal shift from 2022 to 2026 is that "stable Rust is enough" for ninety percent of production code: features that used to require nightly (async fn in traits, RPITIT, GATs, let chains) are stable, and the toolchain has moved from "frustratingly slow" to "fast with mold + sccache + nextest" by default.

---

## 1. Project and Workspace Structure

### 1.1 The default is a workspace, even for one crate

A single-crate project that is plausibly going to grow a binary, a library, integration tests, or proc macros should start as a workspace with a virtual root manifest. The cost is one extra `Cargo.toml`. The payoff is that adding `my-thing-cli` later does not require migrating the directory layout.

When a single crate is enough, the standard layout still applies:

```
my-thing/
  Cargo.toml          # [package]
  src/
    lib.rs
    main.rs           # only if a binary; otherwise omit
  tests/              # integration tests, each file a separate crate
  examples/           # runnable examples
  benches/            # criterion or divan benches
  README.md
  rust-toolchain.toml
```

When the project plausibly needs more than one crate, prefer a virtual workspace from day one:

```
my-thing/
  Cargo.toml                  # [workspace] only, no [package]
  Cargo.lock
  rust-toolchain.toml
  rustfmt.toml
  .github/workflows/ci.yml
  crates/
    my-thing-core/            # zero-I/O domain types and traits
    my-thing-store/           # database / filesystem adapter
    my-thing-cli/             # thin binary, wires adapters
    my-thing-macros/          # proc-macros (separate crate, mandatory)
  xtask/                      # custom dev tasks
  docs/
```

**Why flat.** matklad's `Large Rust Workspaces` (2021, still the canonical reference in 2026) argues that the Cargo namespace is itself flat. There is no way to write `hir::def` in `Cargo.toml`, so any hierarchical folder layout is an alternative namespace that drifts out of sync. A flat list is scannable, easy to add to, and resists organisational decay up to roughly a million lines of code. ([matklad, Large Rust Workspaces](https://matklad.github.io/2021/08/22/large-rust-workspaces.html))

**Why virtual root.** Putting the "main" crate at the workspace root forces every `cargo` invocation to clarify which crate it targets, pollutes the root with `src/`, and creates an asymmetry between the headline crate and the rest. Virtual roots treat all members equally and let you scope commands with `-p` cleanly. ([Cargo Book, Workspaces](https://doc.rust-lang.org/cargo/reference/workspaces.html))

**Counter-arguments.** Bevy uses a nested `crates/` layout with a top-level facade crate that re-exports the rest, which works for an end-user-facing library. Some embedded projects keep `src/` at the root because the firmware is the only output. Both are reasonable when you actually have a single dominant artifact.

### 1.2 Workspace member naming

Use kebab-case with the project as a prefix: `my-thing-core`, `my-thing-cli`, `my-thing-macros`, `my-thing-derive`. The crate name becomes the import name with dashes turned into underscores. Suffixes are loose but conventional:

| Suffix       | Meaning                                                |
| ------------ | ------------------------------------------------------ |
| `-core`      | Domain types and traits with zero I/O                  |
| `-store`     | A storage adapter (sqlite, postgres, in-memory)        |
| `-cli`       | Thin binary that exposes the system as a command line  |
| `-server`    | HTTP / gRPC / MCP server binary                        |
| `-macros`    | Procedural macros (must be its own crate)              |
| `-derive`    | Derive-only proc macros (alternative to `-macros`)     |
| `-codegen`   | Build-time code generation crate                       |
| `-types`     | Wire types shared across server and client             |
| `-testing`   | Test helpers, only used as a `dev-dependency`          |

The `name = "..."` field is what `Cargo` and `crates.io` see. The folder name should match for navigation. Setting `version = "0.0.0"` on internal-only workspace crates signals that they are not meant for publication and avoids accidental publish. ([users.rust-lang.org, naming conventions](https://users.rust-lang.org/t/naming-conventions-for-cargo-workspaces/65369))

Real exemplars: `rust-analyzer/crates/`, `ruff/crates/`, `uv/crates/`, `vector/lib/`, `zed/crates/`, `nushell/crates/` all use this shape.

### 1.3 Workspace inheritance

Since Cargo 1.64 (workspace package/dependencies inheritance) and 1.74 (workspace lints), the root manifest is the source of truth for shared metadata. The canonical pattern:

```toml
# root Cargo.toml
[workspace]
resolver = "3"
members  = ["crates/*", "xtask"]

[workspace.package]
edition       = "2024"
rust-version  = "1.85"
license       = "MIT OR Apache-2.0"
repository    = "https://github.com/me/my-thing"
authors       = ["..."]
version       = "0.4.2"

[workspace.dependencies]
serde       = { version = "1", features = ["derive"] }
tokio       = { version = "1.40", features = ["macros", "rt-multi-thread"] }
thiserror   = "1.0"
anyhow      = "1.0"
tracing     = "0.1"

# Internal crates declared once, referenced from members
my-thing-core  = { path = "crates/my-thing-core", version = "=0.4.2" }
my-thing-store = { path = "crates/my-thing-store", version = "=0.4.2" }

[workspace.lints.rust]
unsafe_code               = "forbid"   # remove for crates that need it
unreachable_pub           = "warn"
missing_docs              = "warn"     # for libraries
rust_2018_idioms          = { level = "warn", priority = -1 }
unused_lifetimes          = "warn"

[workspace.lints.clippy]
pedantic                  = { level = "warn", priority = -1 }
nursery                   = { level = "warn", priority = -1 }
cargo                     = { level = "warn", priority = -1 }
# pedantic noise that almost always fires for no good reason
module_name_repetitions   = "allow"
missing_errors_doc        = "allow"
missing_panics_doc        = "allow"

[profile.release]
lto             = "thin"
codegen-units   = 1
strip           = "symbols"
```

Member crates inherit by setting `workspace = true`:

```toml
# crates/my-thing-core/Cargo.toml
[package]
name        = "my-thing-core"
edition.workspace      = true
rust-version.workspace = true
license.workspace      = true
repository.workspace   = true
version.workspace      = true

[dependencies]
serde     = { workspace = true }
thiserror = { workspace = true }

[lints]
workspace = true
```

The `priority = -1` on grouped lints (`pedantic`, `cargo`, etc.) is the standard escape hatch: groups are applied first, then individual lints override. Without it, individual lint overrides are ambiguous and Cargo rejects the manifest. ([Cargo Book, Lints](https://doc.rust-lang.org/cargo/reference/lints.html), [Rust Project Primer, Lints](https://rustprojectprimer.com/checks/lints.html))

**Limitation worth knowing.** `[lints]` applies uniformly across `lib.rs`, `tests/`, `examples/`, and `benches/`. There is no Cargo-level way to relax (say) `unwrap_used` in tests. Use `#![cfg_attr(test, allow(clippy::unwrap_used))]` at the test module level, or scope `#![allow(...)]` inside `tests/`.

### 1.4 `rust-toolchain.toml`

Pin the toolchain in the repo. Rust ships every six weeks and the friction of "what version did you build with" compounds across contributors.

```toml
# rust-toolchain.toml
[toolchain]
channel    = "1.85"
components = ["rustfmt", "clippy", "rust-src"]
profile    = "minimal"
```

`rust-version` in `[package]` is for downstream consumers (it tells Cargo's MSRV-aware resolver which dependency versions are compatible). `rust-toolchain.toml` is for contributors and CI. The two should usually match. Pinning to a specific minor (`1.85`) instead of `stable` is the right default for shared projects: it makes CI reproducible and surfaces toolchain upgrades as explicit PRs. ([Swatinem, Should I pin my Rust toolchain](https://swatinem.de/blog/rust-toolchain/), [Cargo Book, rust-version](https://doc.rust-lang.org/cargo/reference/manifest.html#the-rust-version-field))

`cargo-msrv` finds the actual MSRV by binary-searching `cargo check` against toolchain versions. Run it whenever you raise dependencies or touch a syntactic feature. ([cargo-msrv](https://crates.io/crates/cargo-msrv))

### 1.5 The `xtask` pattern

`xtask` is a workspace member binary that owns project-specific dev commands. Add a `.cargo/config.toml` alias and `cargo xtask <task>` works from anywhere in the workspace.

```toml
# .cargo/config.toml
[alias]
xtask = "run --quiet --package xtask --"
```

Use it for: code generation, schema regeneration, release pre-flight, integration test orchestration, dist packaging. The win over shell scripts: Rust, type-checked, cross-platform, available everywhere the toolchain is. The win over `cargo-make` and `just`: zero extra tools to install. `cargo` itself uses xtask. ([matklad, cargo-xtask](https://github.com/matklad/cargo-xtask), [rust-analyzer xtask](https://rust-lang.github.io/rust-analyzer/xtask/index.html))

### 1.6 Where `examples/`, `tests/`, and integration tests live

- `examples/` is for runnable executables that demonstrate library usage. Each `examples/foo.rs` becomes `cargo run --example foo`. Examples are doc-checked by `cargo build --examples`.
- `tests/` integration tests are top-level binaries that link against your library as an external user would. They cannot see `pub(crate)`. They are the right place for end-to-end tests that exercise the public API.
- `#[cfg(test)] mod tests` at the bottom of source files is for unit tests that need access to private items. Inline tests live next to the code they cover.

A common 2026 pattern is to keep `mod tests` per file for unit tests, `tests/` for end-to-end integration tests, and `examples/` for "this is how a user calls the library" walkthroughs.

---

## 2. Module and File Organisation

### 2.1 `foo.rs + foo/` beats `foo/mod.rs`

Since Rust 1.30 (Rust 2018), a module `foo` with children can live in `foo.rs` with submodules in `foo/`. This is the recommended style for new code.

Why: with `mod.rs` everywhere, every file you open in a fuzzy finder is called `mod.rs` and you have to read the path to know which module it is. With `foo.rs + foo/`, the file you open is `foo.rs` and the directory next to it holds the children. Editor tabs are readable.

When `mod.rs` still makes sense: hand-curated `tests/common/mod.rs` (where the directory layout signals "shared test helper"), generated index files in build-time codegen, and pre-existing large codebases where the churn cost is not worth the rename. ([Rust Forum, mod.rs vs name.rs](https://users.rust-lang.org/t/module-mod-rs-or-module-rs/122653))

matklad's variant: prefix module files with an underscore (`_regex.rs`) so they sort to the top and have unique fuzzy-findable names. This is a minority taste; most production codebases just use `foo.rs`. ([matklad, Notes on Module System](https://matklad.github.io/2021/11/27/notes-on-module-system.html))

### 2.2 Visibility discipline

Default everything to private. Promote to `pub(crate)` when a sibling module needs it. Promote to `pub` only when it is part of your stable API contract.

The four levels in practice:

| Modifier         | Use for                                              |
| ---------------- | ---------------------------------------------------- |
| `pub`            | API surface intended for downstream callers          |
| `pub(crate)`     | Used by other modules in this crate, never published |
| `pub(super)`     | Used by the parent module only, internal helper      |
| `pub(in path)`   | Rare, when you want a precise sub-tree exposure      |

There are two interpretive schools, both valid. The "promote on demand" school keeps everything private until a sibling needs it and only then raises visibility. The "open by default within crate" school uses `pub` liberally inside private modules because crate boundaries already gate the public API. Kobzol's April 2025 post argues the second interpretation removes a lot of `pub(crate)` noise without weakening the actual API contract, as long as the crate root carefully chooses what to `pub use`. ([Kobzol, Two ways of interpreting visibility](https://kobzol.github.io/rust/2025/04/23/two-ways-of-interpreting-visibility-in-rust.html))

Either way, the rule is: the crate root (`lib.rs`) is the authoritative API surface. Anything not `pub use`d from there is implementation detail, regardless of internal visibility.

### 2.3 Re-export and facade patterns

A 2026 library crate typically has a structure like:

```rust
// lib.rs
//! High-level docs here.

mod config;
mod error;
mod store;
mod transport;

pub use config::{Config, ConfigBuilder};
pub use error::{Error, Result};
pub use store::{Store, Entry};
// transport stays internal
```

This pattern is the Facade: callers see a flat, curated API at the crate root while the internal module tree stays free to refactor. The doc index lists exactly your public surface, not the file layout.

Avoid `pub use mod_name::*;` glob re-exports in your crate root. They turn refactors into compatibility breakage and make `cargo doc` output noisy. Re-export named items.

For very large crates, expose a `prelude` module: `use my_thing::prelude::*;` brings traits and common types into scope without forcing users to find each import. Reserve preludes for crates where ergonomic use requires several traits in scope at once (database drivers, async I/O libraries, embedded HALs).

### 2.4 File and function length

The community converged on soft limits in the 700–1000 line range for a file, with the underlying rule being "if you have to scroll for five seconds, split it". Functions over ~150 lines almost always hide duplication.

Splitting heuristics:

- A `struct` and all its `impl` blocks belong in one file unless the file has crossed the threshold.
- A trait and its blanket impls belong in one file.
- A monster `match` over an enum is fine in one place. Splitting the arms across files breaks the exhaustiveness intuition.

Helioy convention (per `~/.claude/CLAUDE.md`): hard limit of 700 lines for new files, refactor before adding. This is stricter than community norm and the reasoning is leverage: shorter files take less context to read, and the limit forces decomposition decisions while the design is still soft.

### 2.5 One type per file or cohesive module

Rust does not have Java-style "one public class per file". The cohesive-module rule wins: a `parser.rs` containing `Parser`, `ParseError`, `ParserState`, and a few free functions is easier to read than four files that share intimate knowledge of each other. Split when the file gets long, or when one of the types has a clearly separate concern.

---

## 3. API Design Conventions

### 3.1 The Rust API Guidelines remain authoritative

The `rust-lang.github.io/api-guidelines` checklist is still the contract every public library is judged against. It has not been substantively revised in years and a few items are dated, but the core (`C-NEWTYPE`, `C-CUSTOM-TYPE`, `C-OBJECT`, `C-COMMON-TRAITS`, `C-CONV-TRAITS`, `C-COLLECT`, `C-DEBUG`, `C-FAILURE`) is still the reference. ([Rust API Guidelines](https://rust-lang.github.io/api-guidelines/))

What is dated:

- `C-OBJECT` (object-safety) needs updating for async fn in traits, which are not object-safe by default. ([Rust Blog, async fn in traits](https://blog.rust-lang.org/2023/12/21/async-fn-rpit-in-traits/))
- Error handling guidance pre-dates `thiserror` and `anyhow` as community defaults.
- No discussion of edition 2024 features.

What is still right: naming (`snake_case`, `CamelCase`, `SCREAMING_SNAKE`), conversion conventions (`as_`, `to_`, `into_`), trait implementation defaults, iterator conventions, debugging output requirements.

### 3.2 Naming

| Item                         | Convention                                       |
| ---------------------------- | ------------------------------------------------ |
| Crates                       | `kebab-case`                                     |
| Modules                      | `snake_case`, short, noun                        |
| Types, traits, enum variants | `CamelCase`                                      |
| Functions, methods, variables| `snake_case`                                     |
| Constants, statics           | `SCREAMING_SNAKE_CASE`                           |
| Lifetimes                    | `'a`, `'b`, or `'descriptive`                    |
| Type parameters              | Single uppercase letter, or descriptive `CamelCase` |
| Errors                       | Type ends in `Error`; module re-exports as `Error` |
| Builders                     | Type ends in `Builder`                           |
| Result alias                 | `pub type Result<T> = std::result::Result<T, Error>;` |

Conversion methods follow Rust's three-tier convention:

- `as_<T>(&self) -> &T`: cheap reference conversion, no allocation
- `to_<T>(&self) -> T`: converts, may allocate, original kept
- `into_<T>(self) -> T`: consumes self, transfers ownership

### 3.3 Builders

The 2026 picture has three patterns:

1. **`Default + struct update`** for option bags with a handful of fields.

   ```rust
   let config = Config { timeout: Duration::from_secs(5), ..Config::default() };
   ```

2. **Hand-rolled builder** when construction has side effects, fluent ergonomics matter, or required-vs-optional needs to be enforced.

   ```rust
   Server::builder()
       .bind("0.0.0.0:8080")
       .with_state(state)
       .build()
       .await?;
   ```

3. **`bon` derive macro** for the typestate builder pattern when you want compile-time guarantees that required fields are set. `bon` (≈3k stars as of 2026) has overtaken the older `derive_builder` and `typed-builder` crates because it ergonomically supports default values, into-conversions, and async builders. ([bon](https://github.com/elastio/bon))

The hand-rolled approach is the right default. Reach for `bon` when the type has 5+ optional fields or when "forgot to set a required field" is a real failure mode.

Avoid: the older "consuming builder where every method returns `Self`" pattern when many fields are optional. It produces unreadable build chains and forces line-wrapping decisions. The non-consuming `&mut self` variant is friendlier.

### 3.4 `From` / `TryFrom` / `Into`

The rule: implement `From` (or `TryFrom`) and get `Into` for free via the blanket impl. Never implement `Into` directly except in the rare cases where the orphan rule blocks `From`.

Use `From` when conversion is total and obvious (`String::from("hello")`). Use `TryFrom` when conversion can fail (parsing, narrowing).

A common idiom: implement `From<Inner>` for newtypes so callers can write `MyId::from(uuid)` and let `?` handle error conversion in your `Error` enum.

### 3.5 Error design in 2026

The consensus is two-layered:

- **Libraries** use `thiserror` to define a structured error enum that callers can `match` against.
- **Applications** use `anyhow` (or `color-eyre` for nice terminal output) to compose errors without ceremony.

Internal crates that are libraries-to-your-own-application sit on the library side: define a real error type. The application's `main.rs` aggregates everything with `anyhow::Result`.

```rust
// in a library crate
#[derive(Debug, thiserror::Error)]
pub enum StoreError {
    #[error("entry {0} not found")]
    NotFound(String),
    #[error("database error")]
    Db(#[from] sqlx::Error),
    #[error("invalid input: {0}")]
    Invalid(String),
}

pub type Result<T> = std::result::Result<T, StoreError>;
```

```rust
// in a binary crate
use anyhow::{Context, Result};

fn run() -> Result<()> {
    let cfg = load_config().context("loading config")?;
    let store = open_store(&cfg).context("opening store")?;
    Ok(())
}
```

**The `snafu` and `n0-error` minority view.** For large applications where every error needs explicit context with location data and full backtraces across async boundaries, `thiserror` plus `anyhow` is insufficient. GreptimeDB famously moved to `snafu` because they wanted error sites tagged with `Location` and consistent context attachment. ([GreptimeDB, Error Handling for Large Rust Projects](https://medium.com/@greptime/error-handling-for-large-rust-projects-a-deep-dive-into-5e10ee4cbc96)) Iroh wrote their own `n0-error` crate after concluding nothing in the ecosystem gave them call-site location data across the full error stack. ([Iroh, Trying to get error backtraces in rust libraries right](https://www.iroh.computer/blog/error-handling-in-iroh))

Pragmatic rule: start with `thiserror` + `anyhow`. Move to `snafu` or a custom error type if you find yourself adding `.with_context(|| format!("at {}:{}", file!(), line!()))` everywhere.

**`?` etiquette.** Use it freely. The performance cost is zero. The clarity cost of writing `match` arms instead is high. The only time to avoid `?` is in `main`-like top-level functions where you want to convert errors to user-facing messages with explicit context.

**`Box<dyn Error>` vs enum.** For libraries: enum, every time. For prototypes and main functions: `Box<dyn Error>` or `anyhow::Error` is fine. Mixing the two is what `anyhow::Error` exists for.

### 3.6 Newtypes

Newtypes earn their keep when:

- The inner type is structurally identical to other things (a `UserId` and `OrderId` are both `Uuid`).
- The type has invariants the public API should enforce (`Url`, `EmailAddress`).
- The type carries units (`Bytes(u64)`, `Milliseconds(u64)`).

Newtypes do not earn their keep when:

- They wrap a primitive but expose every method via `Deref` (you have not added safety, you have added a name).
- They are introduced "just in case" with no current consumer.

The Microsoft Rust training pattern: implement `Deref` only when the newtype is conceptually a smart pointer (think `Arc`, `String`). For type-safety newtypes, implement specific methods or `as_inner`/`into_inner` accessors, not `Deref`. ([Microsoft RustTraining, Newtype Pattern](https://microsoft.github.io/RustTraining/rust-patterns-book/ch03-the-newtype-and-type-state-patterns.html))

### 3.7 `impl Trait` in modern positions

| Position                | Status              | Use when                                    |
| ----------------------- | ------------------- | ------------------------------------------- |
| Argument                | Stable since forever | You want generic-like API without naming the type |
| Return                  | Stable              | Returning an iterator, closure, or future   |
| Type alias              | Stable (TAIT) since 1.79 | Naming an opaque type in a module signature |
| Associated type (RPITIT)| Stable since 1.75   | Trait methods that return iterators / futures |
| Trait method arguments  | Stable (RPITIT extension) | Same as RPIT, but in trait position |

A subtle 2024-edition change: in return position, `impl Trait` now captures all in-scope generic parameters by default. Before 2024, it only captured types. The new `use<...>` bound lets you opt out:

```rust
fn parse<'a>(input: &'a str) -> impl Iterator<Item = Token> + use<> { ... }
//                                                            ^^^^^^ capture nothing
```

This matters for library authors who were relying on the old narrow capture rules. The fix is usually adding `use<...>` to existing return-position `impl Trait`. ([Rust Blog, Changes to impl Trait in Rust 2024](https://blog.rust-lang.org/2024/09/05/impl-trait-capture-rules/))

---

## 4. Async and Runtime Conventions

### 4.1 Tokio is the default

`tokio` is the assumed runtime in 2026. `async-std` is effectively dead (no significant releases since 2022, last commit on the master branch in early 2024). `smol` exists for niche embedded and single-threaded use cases. `glommio` is for thread-per-core io_uring workloads, mostly used by ScyllaDB and a handful of database adjacent crates.

For a library, the choice is binary: depend on `tokio` and target the ecosystem, or stay runtime-agnostic with `futures` traits and let callers pick. Runtime-agnostic libraries pay a real ergonomic cost (no `tokio::time::sleep`, no `tokio::net`) and the user base is small. Unless you are writing protocol code that genuinely should be runtime-free, depend on `tokio`.

For an application, default to `tokio` with `features = ["macros", "rt-multi-thread"]`.

### 4.2 Sans-IO for protocols

The exception to "depend on tokio" is protocol implementations. The sans-IO pattern decouples protocol state machines from any I/O runtime. Examples: `quinn` (QUIC), `str0m` (WebRTC), `snownet` (Firezone). A sans-IO library exposes `handle_input`, `poll_transmit`, `handle_timeout`, `poll_timeout` style methods and leaves socket and timer management to the caller.

The reasons to do this: testability without mocking, portability to embedded and WASM, composability of multiple protocol layers, and freedom from the function-colouring problem. The cost is that callers must write the I/O loop themselves. ([Firezone, Sans-IO pattern in Rust](https://www.firezone.dev/blog/sans-io))

### 4.3 Native async fn in traits replaces `async-trait` for most uses

Async fn in traits stabilised in Rust 1.75 (December 2023). The macro `async-trait` is no longer needed for static dispatch.

```rust
// 2024 idiomatic
trait Store {
    async fn get(&self, key: &str) -> Result<Vec<u8>, StoreError>;
    async fn put(&self, key: &str, value: &[u8]) -> Result<(), StoreError>;
}
```

The catch: traits with async methods are not object-safe. You cannot have `Box<dyn Store>` with the trait above. Options:

1. Keep `async-trait` for the trait if you need `dyn`.
2. Use `dynosaur` (Rust Project's official answer, proc macro that derives a `dyn`-safe shim trait).
3. Define `BoxStore` manually using `Pin<Box<dyn Future>>` returns.
4. Reconsider whether you actually need dynamic dispatch. Often the static-dispatch generic version is fine.

A 2025 survey reported that 78% of teams still used the `async-trait` macro or manual `Pin<Box<dyn Future>>` patterns, mostly because `dyn` dispatch is convenient and `dynosaur` is new. The migration is slow but steady. ([Niko Matsakis, Dyn async traits part 10](https://smallcultfollowing.com/babysteps/blog/2025/03/24/box-box-box/), [Medium, Rust Async Traits: What Finally Works Now](https://medium.com/@ashusk_1790/rust-async-traits-what-finally-works-now-7b7f46529718))

### 4.4 Structured concurrency: `JoinSet`, `select!`, cancellation tokens

The 2026 pattern for spawning N tasks and awaiting them all (with cancellation propagating on drop) is `tokio::task::JoinSet`:

```rust
let mut set = JoinSet::new();
for url in urls {
    set.spawn(fetch(url));
}
while let Some(res) = set.join_next().await {
    match res {
        Ok(Ok(body)) => process(body),
        Ok(Err(e))   => tracing::warn!(error = %e, "fetch failed"),
        Err(join)    => tracing::error!(error = ?join, "task panicked"),
    }
}
// Dropping set here aborts any still-running tasks.
```

`JoinSet` is the right answer for fan-out workloads. `tokio::select!` is for "first one wins" choices. `tokio_util::sync::CancellationToken` is the right answer when child tasks need to listen for a cancellation signal without being aborted unconditionally.

**Cancellation safety.** A future is cancel-safe if dropping it mid-poll leaves no partial state visible to other tasks. `tokio::select!` requires cancel-safe branches. Operations on a `tokio::sync::mpsc::Receiver` are cancel-safe; `tokio::time::sleep` is cancel-safe; reading from a stream that buffers internally usually is not. The `tokio::select!` documentation lists the safe primitives. When in doubt, wrap state mutation in a guard pattern that only commits after the await point completes.

### 4.5 Channels

Tokio's `tokio::sync::mpsc` is the right default for async channels. It is mature, well-documented, and integrates naturally with the runtime.

- `tokio::sync::mpsc` for async producer / async consumer
- `tokio::sync::broadcast` for one-to-many fanout
- `tokio::sync::oneshot` for single value send/await
- `crossbeam_channel` for sync-only code (threads, no runtime)
- `flume` for unified sync+async API, lightweight, but in "casual maintenance" mode in 2025
- `kanal` and `crossfire` for high-throughput specialised workloads where benchmarks justify the dependency

Benchmark differences are real (`kanal` and `crossfire` often beat `tokio::sync::mpsc` by 2-5x on contended throughput) but only matter for hot paths. Pick `tokio::sync::mpsc` first and only swap when profiling proves the channel is the bottleneck. ([rust-channel-benchmarks](https://github.com/fereidani/rust-channel-benchmarks))

### 4.6 What to teach vs hide

Things that should not leak into application-level code:

- `Pin`, `Box::pin`, `Pin<Box<dyn Future>>` in API signatures. If you find yourself writing these, you probably want `async-trait` or `dynosaur`.
- Manual `Future` impls. Use `async fn` or `async move {}` blocks.
- `tokio::task::block_in_place` outside of well-considered cases. It is a footgun on the multi-threaded runtime and forbidden on the current-thread runtime.

Things every async Rust author needs to internalise:

- `Send` and `'static` propagation on spawned tasks.
- The shape of `Result<T, JoinError>` from `JoinHandle::await`.
- That `?` on an `async fn` exits the future, not the surrounding `tokio::select!` arm.
- That `.await` is a yield point and held locks across await are a deadlock waiting to happen.

---

## 5. Dependency Hygiene

### 5.1 Picking a dependency

The 2026 checklist:

1. **Is it actively maintained?** A repo with no commits for 12+ months is a yellow flag. Look at issue triage cadence, not just commits.
2. **What does it pull in?** Run `cargo tree -e features --workspace` and look at the depth. A "small" CLI argument parser that adds 40 crates is not small.
3. **What is the compile-time cost?** `cargo build --timings` shows which crates dominate. `serde`, `tokio`, `hyper` are expected. Anything else over 5 seconds deserves scrutiny.
4. **Is the API stable?** A 0.x crate with a 12-month release cadence is acceptable. A 0.x crate that breaks API every quarter is not.
5. **Are alternatives obviously worse?** `reqwest` over hand-rolling `hyper` is obvious. `failure` over `thiserror` is obvious in the other direction.

Audit tools:

- `cargo-machete` finds dependencies declared in `Cargo.toml` but unused in source. Fast, stable-compatible, runs in CI without nightly. ([cargo-machete](https://github.com/bnjbvr/cargo-machete))
- `cargo-udeps` does the same job more thoroughly but requires nightly. Use it monthly, not on every PR.
- `cargo-bloat` shows which crates contribute the most binary size. Useful for CLI tools where binary size matters.
- `cargo-shear` is a newer, faster machete alternative.

### 5.2 Feature flag design

Features must be additive. Enabling a feature should never break code that worked without it.

```toml
[features]
default = ["native-tls"]
native-tls = ["dep:openssl"]
rustls = ["dep:rustls"]
# Bad: turning on "rustls" should not silently replace "native-tls"
```

The fix is to make TLS selection orthogonal or to gate the conflicting paths with `compile_error!`:

```rust
#[cfg(all(feature = "native-tls", feature = "rustls"))]
compile_error!("features `native-tls` and `rustls` are mutually exclusive");
```

Other principles:

- Default features should make the crate "just work" for the 80% case.
- Each feature should be documented in `Cargo.toml` and the crate docs.
- Avoid more than a handful of independent features. Combinatorial explosion in CI testing is real.
- Use `dep:` syntax (Cargo 1.60+) to make optional dependencies not implicitly create features.

The Slint blog has the canonical warning about adding new default features after 1.0: it is a semver-major change because callers with `default-features = false` and an explicit feature list will silently lose functionality. ([Slint, Adding default cargo features](https://slint.dev/blog/rust-adding-default-cargo-feature/))

### 5.3 Standard dependency selections (2026)

| Job                        | Default                | Notes                                      |
| -------------------------- | ---------------------- | ------------------------------------------ |
| Serialisation              | `serde` + `serde_json` | Alternatives: `miniserde` (small), `rkyv` (zero-copy), `borsh` (binary) |
| Async runtime              | `tokio`                | `smol`, `glommio` for niches               |
| HTTP server                | `axum`                 | `actix-web` still used; `axum` won the mindshare |
| HTTP client (async)        | `reqwest`              | `ureq` for sync, `hyper` direct for low-level |
| CLI parsing                | `clap` (derive)        | `bpaf` for parser combinators, `argh` for minimal |
| Logging                    | `tracing` + `tracing-subscriber` | `log` for libraries that must support the lowest common denominator |
| Errors (lib)               | `thiserror`            | `snafu` for context-heavy, `n0-error` for cross-stack backtraces |
| Errors (bin)               | `anyhow`               | `color-eyre` for human-facing errors with pretty output |
| Testing runner             | `cargo nextest`        | 2-3x faster than `cargo test`              |
| Snapshot testing           | `insta`                | Best-in-class                               |
| Property-based testing     | `proptest`             | `quickcheck` exists, `proptest` is the default |
| Parameterised testing      | `rstest`               | Native `#[test]` with fixtures and tables  |
| Benchmarking               | `criterion` or `divan` | `divan` is newer and simpler, `criterion` is established |
| Database (Postgres/SQLite) | `sqlx`                 | `rusqlite` for embedded sync SQLite        |
| UUIDs                      | `uuid`                 | `uuid7` for sortable IDs                   |
| Time                       | `jiff` or `chrono`     | `jiff` is the modern choice; `chrono` for ecosystem compatibility |
| Pinning collections        | `indexmap`             | Order-preserving HashMap                   |

`serde` is the universal serialisation choice and there is no real reason to pick alternatives unless you have a specific constraint:

- `miniserde` for ultra-small binary size, JSON only, slower runtime
- `rkyv` for zero-copy deserialisation when your data is bytes-on-disk or wire format you control
- `borsh` for cross-language binary protocols (its origin is the NEAR blockchain)

For HTTP clients, `reqwest` is the default. `ureq` is the right choice for sync code in CLIs and small binaries where you do not want the `tokio` dependency. `hyper` directly is only justified when you are building protocol middleware. ([LogRocket, How to choose the right Rust HTTP client](https://blog.logrocket.com/best-rust-http-client/))

### 5.4 `clap` derive vs builder

Use derive for 95% of CLIs. The struct is the documentation.

```rust
#[derive(clap::Parser)]
#[command(version, about, long_about = None)]
struct Cli {
    /// Path to the config file
    #[arg(short, long, default_value = "config.toml")]
    config: PathBuf,

    #[command(subcommand)]
    command: Command,
}

#[derive(clap::Subcommand)]
enum Command {
    Start { #[arg(short, long)] port: u16 },
    Stop,
}
```

Use the builder when you need runtime-constructed CLIs (plugin-loaded subcommands, dynamic argument lists) or when you need access to argument origin data (which-arg-set-this, position-in-argv).

`bpaf` is the niche alternative for parser-combinator style CLIs and is well-loved by people who hate macros. `argh` is for very small binaries where compile time of `clap` matters. ([Kevin K, CLI Structure in Rust](https://kbknapp.dev/cli-structure-04/))

### 5.5 `tracing` is the logging default

`tracing` replaced `log` as the de-facto application-level logging crate around 2022, and the gap has only widened. The reasons:

- Structured fields (`tracing::info!(user_id = %id, "logged in")`) instead of fmt-only strings.
- Spans give you free correlation across async tasks.
- `tracing-subscriber` ships JSON, OpenTelemetry, and per-module filters out of the box.

For libraries: a contested question in 2024 has settled on "use `tracing`". The `log` facade is the lowest common denominator but `tracing` libraries can emit to `log` consumers via `tracing-log`, while the reverse does not preserve structure. New libraries should use `tracing`. Established libraries on `log` can stay there. ([tracing](https://docs.rs/tracing), [Shuttle, Logging in Rust (2025)](https://www.shuttle.dev/blog/2023/09/20/logging-in-rust))

---

## 6. Lints, Formatting, CI

### 6.1 Rustfmt

Use defaults. `rustfmt.toml` should be empty or near-empty for any new project. The two settings most teams add are:

```toml
# rustfmt.toml
edition = "2024"
style_edition = "2024"
```

Nightly options exist (`group_imports`, `imports_granularity`, `wrap_comments`) and are useful, but they only run with `+nightly` and require contributors to install nightly. The pain is rarely worth it. Pick defaults, format on save, move on.

The Rust 2024 edition introduces rustfmt "style editions" that let formatting evolve independently from the language edition. Set `style_edition = "2024"` to opt into the latest formatting style. ([Rust 1.85 release notes](https://blog.rust-lang.org/2025/02/20/Rust-1.85.0/))

### 6.2 Clippy lint groups

The four groups worth knowing:

- **`correctness`**: denied by default, never disable, these catch bugs.
- **`suspicious`**: warned by default, almost always real issues.
- **`style`** and **`complexity`**: warned by default, idiomatic Rust nudges.
- **`perf`**: warned by default, performance heuristics.
- **`pedantic`**: opinionated, opt-in, worth enabling with `#[allow]` for the noisy ones.
- **`nursery`**: experimental, cherry-pick instead of enabling wholesale.
- **`cargo`**: manifest-level lints (`multiple_crate_versions`, `wildcard_dependencies`), opt-in.

The 2026 recommended workspace baseline:

```toml
[workspace.lints.clippy]
pedantic                = { level = "warn", priority = -1 }
cargo                   = { level = "warn", priority = -1 }

# pedantic noise that almost never indicates a real issue
module_name_repetitions = "allow"
missing_errors_doc      = "allow"
missing_panics_doc      = "allow"
must_use_candidate      = "allow"
cast_precision_loss     = "allow"
similar_names           = "allow"

# upgrade to deny where appropriate
unwrap_used             = "warn"   # deny in production crates
expect_used             = "warn"
panic                   = "warn"
unimplemented           = "warn"
todo                    = "warn"
```

Nursery should be cherry-picked. The whole group has a high false-positive rate and includes lints that are still being trialed.

`#[allow(clippy::...)]` should be local and justified with a comment. Crate-level `#![allow(...)]` lists in `lib.rs` are a smell unless the lint is genuinely wrong for the crate's purpose. ([Clippy Lints](https://rust-lang.github.io/rust-clippy/master/index.html), [Rust Project Primer, Lints](https://rustprojectprimer.com/checks/lints.html))

### 6.3 Crate-level `#![warn(...)]`

Even with workspace lints, set crate-level lints in `lib.rs` for cases where the workspace default needs adjusting:

```rust
// lib.rs
#![warn(missing_docs)]                    // libraries only
#![warn(unreachable_pub)]
#![warn(rust_2018_idioms)]
#![warn(rust_2024_compatibility)]
#![deny(unsafe_op_in_unsafe_fn)]
// for app crates that should never go unsafe:
#![forbid(unsafe_code)]
```

`unsafe_op_in_unsafe_fn` becomes a hard warning by default in edition 2024 and the recommendation is to `deny` it. It forces explicit `unsafe { ... }` blocks even inside `unsafe fn`, which makes the dangerous operations visible. ([Rust Edition Guide, unsafe_op_in_unsafe_fn](https://doc.rust-lang.org/edition-guide/rust-2024/unsafe-op-in-unsafe-fn.html))

### 6.4 CI: deny warnings in CI, warn locally

Local development with `deny(warnings)` is hostile. New code in progress always has unused imports and `todo!()` placeholders. Set CI to fail on warnings via `RUSTFLAGS="-D warnings"`. Locally, run with the default lint levels and let the developer decide when to fix.

```yaml
# .github/workflows/ci.yml fragment
- name: Clippy
  run: cargo clippy --all-targets --all-features -- -D warnings
```

### 6.5 Standard CI shape

A typical 2026 Rust CI uses GitHub Actions with `dtolnay/rust-toolchain` (the modern replacement for the deprecated `actions-rs` family) and `Swatinem/rust-cache` for caching.

```yaml
name: ci
on:
  push: { branches: [main] }
  pull_request:
jobs:
  fmt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with: { components: rustfmt }
      - run: cargo fmt --all -- --check

  clippy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with: { components: clippy }
      - uses: Swatinem/rust-cache@v2
      - run: cargo clippy --workspace --all-targets --all-features -- -D warnings

  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: Swatinem/rust-cache@v2
      - uses: taiki-e/install-action@nextest
      - run: cargo nextest run --workspace --all-features

  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: Swatinem/rust-cache@v2
      - run: cargo doc --workspace --no-deps --all-features
        env:
          RUSTDOCFLAGS: -D warnings

  deny:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: EmbarkStudios/cargo-deny-action@v2

  msrv:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@1.85   # match rust-version in Cargo.toml
      - uses: Swatinem/rust-cache@v2
      - run: cargo check --workspace --all-features
```

`cargo-deny` subsumes `cargo-audit`: it checks RustSec advisories plus license policy plus duplicate-version policy plus source whitelist. Prefer `cargo-deny` and skip `cargo-audit` in CI. ([cargo-deny issue 386](https://github.com/EmbarkStudios/cargo-deny/issues/386))

For release engineering, `release-plz` is the 2026 winner: it watches conventional commits, opens a PR with version bumps and changelogs, and on merge handles `cargo publish` ordering across workspace members. ([release-plz](https://release-plz.dev/))

---

## 7. Documentation

### 7.1 `cargo doc` is part of the test surface

Doctests run with `cargo test --doc`. They are the most underrated form of testing in Rust because they double as the user-visible example. The corollary: write doc examples that compile and assert real behaviour.

```rust
/// Parses a configuration from a TOML string.
///
/// # Examples
///
/// ```
/// use my_thing::Config;
/// let cfg: Config = my_thing::parse("name = \"web\"").unwrap();
/// assert_eq!(cfg.name, "web");
/// ```
pub fn parse(input: &str) -> Result<Config> { ... }
```

The directives:

- `ignore`: do not compile or run. Use sparingly, prefer `no_run`.
- `no_run`: compile but do not execute. Use for examples that need network or filesystem.
- `compile_fail`: assert that the code does NOT compile. Useful for type-safety demos.
- `should_panic`: assert that the code panics at runtime.

### 7.2 README and `lib.rs` synchronisation

The pattern:

```rust
// lib.rs
#![doc = include_str!("../README.md")]
```

Caveats: relative paths in the README (images, doc links) need to resolve in both GitHub and docs.rs. Use absolute URLs to a stable location, not relative paths. Intra-doc links in the README need careful handling because the resolution rules differ. Linebender's post covers the gotchas in detail. ([Linebender, doc include](https://linebender.org/blog/doc-include/))

The alternative is `cargo-rdme` (or the older `cargo-readme`), which extracts doc comments from `lib.rs` and writes them into `README.md` at release time. This keeps the rustdoc-side authoritative.

Pick one direction and stick to it. Bidirectional sync is unsustainable.

### 7.3 docs.rs metadata

```toml
[package.metadata.docs.rs]
all-features = true
rustdoc-args = ["--cfg", "docsrs"]
```

Then guard doc-only annotations:

```rust
#[cfg_attr(docsrs, doc(cfg(feature = "tokio")))]
pub mod tokio_helpers { ... }
```

This makes docs.rs annotate optional API surfaces with the feature flag they require. The `docsrs` cfg is the standard signal that the build is for docs.rs specifically.

### 7.4 Intra-doc links

Use them everywhere:

```rust
/// Returns the underlying [`Store`].
///
/// See also [`Store::open`] and the [`config`] module.
pub fn store(&self) -> &Store { ... }
```

The compiler verifies these. Broken links become CI failures. This is the cheapest way to keep documentation honest.

### 7.5 `#![deny(missing_docs)]` for libraries

Set it. Initial cost is high. Ongoing cost is small. Library users will thank you. For internal-only crates, downgrade to `warn` and document the public API only.

---

## 8. Unsafe, FFI, Soundness

### 8.1 Default: forbid unsafe

For application crates and most library crates:

```rust
#![forbid(unsafe_code)]
```

`forbid` is stronger than `deny`: it cannot be overridden by `#[allow]` deeper in the crate. This is the strongest possible signal that the crate is safe.

For crates that need unsafe (FFI, low-level primitives, performance-critical paths), drop to:

```rust
#![deny(unsafe_op_in_unsafe_fn)]
```

This requires explicit `unsafe { ... }` blocks even inside `unsafe fn`, making each dangerous operation visible. It is on by default in edition 2024. ([Rust Edition Guide, unsafe_op_in_unsafe_fn](https://doc.rust-lang.org/edition-guide/rust-2024/unsafe-op-in-unsafe-fn.html))

### 8.2 Documenting unsafe

Every `unsafe` block needs a `// SAFETY:` comment. Every `unsafe fn` needs a `# Safety` section in its rustdoc. This is mechanical and unskippable.

```rust
/// Reads `len` bytes from `ptr`.
///
/// # Safety
///
/// `ptr` must be valid for reads of `len` bytes and properly aligned.
/// The memory must not be mutated for the duration of the read.
pub unsafe fn read_bytes(ptr: *const u8, len: usize) -> Vec<u8> {
    // SAFETY: caller guarantees ptr is valid and aligned for `len` bytes.
    unsafe { std::slice::from_raw_parts(ptr, len).to_vec() }
}
```

Clippy lints `undocumented_unsafe_blocks` (in `restriction`, opt-in) and `missing_safety_doc` (in `style`, default) enforce these.

### 8.3 Miri in CI

For crates with any `unsafe`, run `cargo miri test` in CI on a weekly schedule. Miri catches undefined behaviour that the compiler misses: out-of-bounds reads, use-after-free, uninitialised memory, data races. It is slow (5-10x test runtime) and does not support all syscalls, but it catches real bugs.

```yaml
miri:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: dtolnay/rust-toolchain@nightly
      with: { components: miri }
    - run: cargo miri setup
    - run: cargo miri nextest run --workspace
```

### 8.4 FFI tools

The 2026 picture:

| Target            | Tool                | Notes                                   |
| ----------------- | ------------------- | --------------------------------------- |
| C ABI             | `cbindgen`          | Generates C headers from Rust public API |
| C++ interop       | `cxx`               | Type-safe Rust ↔ C++ bindings           |
| Python            | `pyo3` + `maturin`  | The canonical Rust ↔ Python pipeline   |
| Node.js           | `napi-rs`           | N-API native modules                    |
| WebAssembly (web) | `wasm-bindgen`      | DOM and JS interop                      |
| Multi-language    | `uniffi`            | Mozilla project, generates Swift/Kotlin/Python/Ruby bindings from a UDL |

`pyo3` is mature and production-ready. `napi-rs` powers significant Node.js native modules in 2026 (Next.js's `swc` integration uses it). `uniffi` is the right answer when you need to ship the same Rust core to both iOS and Android. ([pyo3](https://docs.rs/pyo3), [uniffi-rs](https://github.com/mozilla/uniffi-rs))

---

## 9. Performance and Build Hygiene

### 9.1 Release profile defaults

The community baseline `release` profile:

```toml
[profile.release]
lto             = "thin"
codegen-units   = 1
strip           = "symbols"
panic           = "unwind"   # leave "unwind" unless you measured "abort" helps
```

`lto = "thin"` gives most of the optimisation benefit at a fraction of the compile cost compared to `lto = "fat"`. `codegen-units = 1` trades parallel compilation for global optimisation. `strip = "symbols"` removes debug symbols from the final binary.

For absolute maximum performance:

```toml
[profile.release]
lto             = "fat"
codegen-units   = 1
panic           = "abort"     # smaller binary, no unwinding cost
strip           = "symbols"
```

`panic = "abort"` removes unwinding tables and can reduce binary size by 5-10%, but only if you genuinely never catch panics. ([Rust Performance Book, Build Configuration](https://nnethercote.github.io/perf-book/build-configuration.html))

### 9.2 Profile-guided optimisation (PGO)

PGO buys 5-15% runtime improvement on CPU-bound code. The workflow:

1. Build with instrumentation: `cargo pgo build`.
2. Run on representative workloads.
3. Build again with the profile: `cargo pgo optimize build`.

The cost is workflow complexity. PGO is worth it for shipping CLI tools and servers where milliseconds matter (`ripgrep`, `bat`, internal services at scale). It is not worth it for most library code or for tools where build reproducibility trumps the last 10%. ([cargo-pgo](https://github.com/Kobzol/cargo-pgo), [Rust Academy, LTO and PGO](https://rust-academy.com/rust-lto-and-pgo/))

### 9.3 Build-time hygiene

The 2026 recipe for fast iterative builds:

1. **mold linker** on Linux, **lld** on macOS. Linking dominates incremental rebuild time and `mold` is dramatically faster than the default ld.

   ```toml
   # .cargo/config.toml
   [target.x86_64-unknown-linux-gnu]
   linker = "clang"
   rustflags = ["-C", "link-arg=-fuse-ld=mold"]
   ```

2. **sccache** for shared build caches across CI runs and local clones.

   ```toml
   [build]
   rustc-wrapper = "sccache"
   ```

3. **cargo nextest** for tests. 2-3x faster than `cargo test` due to process-per-test parallelism.

4. **Incremental compilation** stays on for dev (`incremental = true`), off for release (default).

5. **Avoid generic bloat.** Generic functions instantiate per type parameter. A heavily generic crate compiled in a downstream binary can dominate compile time. Use `impl Trait` over `Box<dyn Trait>` where possible, but prefer concrete types when the generic surface is large.

([mold](https://github.com/rui314/mold), [sccache](https://github.com/mozilla/sccache), [Optimizing Rust CI/CD](https://www.somethingsblog.com/2025/05/26/turbocharge-your-rust-projects-faster-ci-cd-pipelines-and-builds/))

### 9.4 `Box<dyn Trait>` vs generics

Generics are free at runtime, expensive at compile time. `Box<dyn Trait>` is the opposite. The trade-off:

- Use generics for hot-path code that is called from a few sites.
- Use `Box<dyn Trait>` (or `Arc<dyn Trait>`) when there are many call sites or when the call sites are themselves generic (and would force monomorphisation explosion).

A library that exposes both a generic and a `dyn` variant of an API (often `fn foo<T: Trait>(t: T)` and `fn foo_dyn(t: &dyn Trait)`) gives callers the choice. The `tracing` ecosystem does this.

---

## 10. Macros and Metaprogramming

### 10.1 When to reach for a macro

Decision tree:

- Can a regular function do it? Use a function.
- Need a different number of arguments at each call site? `macro_rules!`.
- Need to inspect or generate Rust syntax (struct fields, enum variants, attributes)? Procedural macro.
- Need to generate code based on external data (a schema file, a service definition)? Build script (`build.rs`) with `quote` for token generation.

The bar for proc macros is high because they:

- Force a separate crate (proc macros cannot be defined in the crate that uses them).
- Slow down compilation (each invocation runs the macro).
- Make IDE support worse (rust-analyzer expands them but with caveats).
- Make errors confusing for users.

That said, derive macros (`#[derive(Serialize, Deserialize)]`) are the most loved feature of the language for a reason. Use them generously when consuming, write them sparingly when producing.

### 10.2 Proc macro crate conventions

If your crate `my-thing` has procedural macros, put them in a sibling `my-thing-macros` crate that `my-thing` re-exports:

```toml
# crates/my-thing-macros/Cargo.toml
[package]
name = "my-thing-macros"
edition.workspace = true

[lib]
proc-macro = true

[dependencies]
proc-macro2 = "1"
quote       = "1"
syn         = { version = "2", features = ["full", "extra-traits"] }
```

```rust
// crates/my-thing/src/lib.rs
pub use my_thing_macros::MyDerive;
```

This pattern hides the proc-macro crate from users. They depend on `my-thing` and get the macro through the re-export. The split keeps the proc-macro compilation contained.

Naming: `-macros` for general-purpose macros, `-derive` for derive-only macros. Both conventions are common.

### 10.3 Testing proc macros with `trybuild`

`trybuild` runs the proc macro against test files in `tests/ui/` and asserts the compile output. Use it for both success and failure cases.

```rust
// tests/expand.rs
#[test]
fn ui() {
    let t = trybuild::TestCases::new();
    t.pass("tests/ui/basic.rs");
    t.compile_fail("tests/ui/missing_field.rs");
}
```

Each `tests/ui/foo.rs` has a `tests/ui/foo.stderr` counterpart for compile-fail cases. Run with `cargo test`; regenerate stderr with `TRYBUILD=overwrite cargo test`.

Pair with `cargo expand` (subcommand of `cargo-expand`) for debugging: it shows the post-macro-expansion source. ([Ferrous Systems, Testing proc macros](https://ferrous-systems.com/blog/testing-proc-macros/))

### 10.4 Declarative macro hygiene

`macro_rules!` is hygienic for identifiers but not for paths. Always reference types and traits by absolute path:

```rust
macro_rules! make_error {
    ($msg:expr) => {
        ::std::result::Result::Err(::std::format!($msg))
    };
}
```

Use `$crate` for items defined in the same crate as the macro: `$crate::error::MyError`. This makes the macro work regardless of where the caller imported it.

Document macros with `#[macro_export]` and write doc examples that show invocation, not the internals.

---

## 11. Edition 2024 and the Language Frontier

### 11.1 What changed in edition 2024

Stable since Rust 1.85 (February 2025). The edition you should default to for new code in 2026.

| Change                              | Impact                                          |
| ----------------------------------- | ----------------------------------------------- |
| `let` chains in `if`/`while`        | `if let Some(x) = a && let Some(y) = b { ... }` finally legal |
| Async closures (`async \|\| {}`)    | Closures that return futures, can capture across await |
| Never type fallback                 | `!` no longer falls back to `()`; explicit annotations sometimes required |
| `unsafe extern` blocks              | `extern "C" { ... }` blocks now require `unsafe` keyword |
| RPIT capture rule changes           | Return-position `impl Trait` captures all in-scope generics by default |
| `gen` keyword reserved              | Generator blocks coming in a future release    |
| `expr` macro fragment broader       | Matches `const` and `_` expressions            |
| `missing_fragment_specifier`        | Hard error, was previously a warning           |
| `tail_expr_drop_order`              | Temporaries dropped before `else` branch evaluation |
| New rustfmt "style edition"         | Formatting can evolve independently of language edition |
| MSRV-aware resolver default         | Cargo prefers dependency versions compatible with your `rust-version` |

([Rust 2024 Edition Guide](https://doc.rust-lang.org/edition-guide/rust-2024/index.html), [Rust 1.85 release notes](https://blog.rust-lang.org/2025/02/20/Rust-1.85.0/))

### 11.2 What is now idiomatic that was not before

**`let` chains** simplify the common nested `if let` pattern:

```rust
// Before edition 2024
if let Some(user) = lookup(name) {
    if let Some(perm) = user.permissions.get(action) {
        if perm.allow {
            // ...
        }
    }
}

// Edition 2024
if let Some(user) = lookup(name)
    && let Some(perm) = user.permissions.get(action)
    && perm.allow
{
    // ...
}
```

This change alone simplifies a large fraction of guard-clause code. ([Rust Edition Guide, let chains](https://doc.rust-lang.org/edition-guide/rust-2024/let-chains.html))

**`let-else`** has been stable since 1.65 and is now the idiomatic way to bind-or-return:

```rust
let Some(user) = lookup(name) else {
    return Err(Error::NotFound);
};
// user is in scope here
```

Use it instead of `match` for one-success-one-failure shapes.

**Async closures**:

```rust
let process = async |item: Item| -> Result<()> {
    let parsed = parse(&item).await?;
    store.put(parsed).await
};

for item in items {
    process(item).await?;
}
```

Before 1.85, this required `move ||` wrapping an `async` block, which made captures painful. ([InfoWorld, Rust 1.85 async closures](https://www.infoworld.com/article/3835168/rust-1-85-arrives-with-long-awaited-async-closures.html))

**Async fn in traits** (stable since 1.75, idiomatic since 2024) replaces `#[async_trait]` for static dispatch.

**RPITIT** (return-position impl Trait in traits, stable since 1.75) lets traits return concrete-but-opaque types:

```rust
trait Source {
    fn items(&self) -> impl Iterator<Item = Item>;
}
```

### 11.3 What is still nightly but widely used

- **Specialization-lite via inherent associated types.** Not stable, but `min_specialization` is increasingly used in serious crates that gate on `nightly` features.
- **`#[diagnostic::on_unimplemented]`** for custom error messages on trait bounds. Partially stable, full version still nightly.
- **GATs with where-clauses on associated types.** Stable since 1.65, the headline feature for lending iterators and async traits.
- **Async iterators (`AsyncIterator`).** Not stable. The community still uses `futures::Stream`.

### 11.4 RFCs in flight worth tracking

- **`gen` blocks** for generator functions. Should land in a 2025-2026 release.
- **Coroutines** (more general than generators). Long horizon.
- **`Try` trait stabilisation** for user-defined `?` types. In progress.
- **`Pin` ergonomics**. Several proposals in flight (`pin!` macro stable since 1.68, more coming).

Watch the Rust blog's monthly project goals updates for the canonical status. ([Rust Blog, Project Goals](https://blog.rust-lang.org/))

---

## 12. KISS, Simplicity, Anti-Patterns

### 12.1 The cargo-cult patterns to avoid

**Reaching for `Arc<Mutex<T>>` by default.** This is the most common anti-pattern in tutorial-driven Rust. It is the right answer when:

- You have multiple threads that each need to read and write shared mutable state.
- The contention is low (writes are rare or short).

It is the wrong answer when:

- Only one task ever writes. Use `Arc<T>` (immutable) plus a channel to deliver updates, or `arc-swap` for hot-swappable shared state.
- You want concurrent reads with rare writes. Use `RwLock`, ideally `parking_lot::RwLock` or `tokio::sync::RwLock`.
- The data is per-task state. Use task-local storage, not shared state.
- The lock is held across `.await`. This is a deadlock magnet. Refactor.

Markaicode's 2025 post on this is worth reading. The TL;DR: profile before reaching for shared mutability, prefer message passing, use atomic primitives for counters, use `DashMap` for sharded concurrent maps. ([Markaicode, Avoid the Arc<Mutex<T>> Pit](https://markaicode.com/rust-memory-management-2025/), [Medium, We Used Arc<Mutex> Everywhere](https://codingplainenglish.medium.com/we-used-arc-mutex-everywhere-and-killed-our-performance-782e00a6972d))

**Over-trait-ing.** Defining a trait for everything "for testability" is the Java-Rust trap. A trait is justified when:

- There are two or more concrete implementations.
- The boundary is a true protocol (storage backend, transport, codec).
- Dependency inversion is genuinely useful (the consumer should not know the producer's concrete type).

A trait with one impl and one consumer is dead weight. Inline the methods on the struct. Add the trait when the second impl arrives.

**Premature generics.** Functions written with `<T: AsRef<str>>` and `<I: IntoIterator<Item = ...>>` everywhere produce slow compiles and unreadable error messages. The 2026 rule: start with concrete types (`&str`, `&[T]`), generalise when the second caller wants a different type. Cargo cult generics are easy to write and hard to read.

**Trait method explosion.** A trait with twelve methods asks each implementor to think about all twelve. A trait with two methods that compose well is reusable. The `Future` trait is one method (`poll`). The `Iterator` trait is one method (`next`). Imitate.

**Newtype overuse.** A newtype for every single domain concept (`UserName(String)`, `Email(String)`, `City(String)`, `Country(String)`) is a tax on every conversion. Use newtypes where there is an actual invariant or where confusion is likely (a function taking `(UserId, OrderId)` instead of `(Uuid, Uuid)` prevents real bugs).

**Type-state pattern overuse.** Type-state is brilliant when:

- The state machine has 2-4 states.
- The wrong transitions are common bugs.
- The states do not need to be persisted or serialised across boundaries.

It is overkill when:

- The states need to be serialised (you cannot serialise a `Order<Paid>`; you have to serialise to an enum and parse back).
- The state machine has 10+ states with complex transitions.
- The team is small and the bikeshedding cost of "should this be a state or a flag" outweighs the safety win.

Use enums as the default representation. Promote to type-state when the cost of a wrong transition is high (financial transactions, state machines that drive hardware). ([corrode, Make Illegal States Unrepresentable](https://corrode.dev/blog/illegal-state/))

**"Make invalid states unrepresentable" applied to every domain object.** The principle is sound. The application to every field is exhausting and over-engineered. Pick the invariants that matter, encode them, let the rest be plain data with validation at the boundary.

### 12.2 What concrete-first looks like

A 2026 best-practice flow:

1. Write the concrete struct and its methods. No traits.
2. Use it.
3. When a second use case appears that needs a different impl, extract the trait.
4. When a third appears, refine the trait.

The cost of inlining a struct's methods into the call sites is small. The cost of having a sprawling trait hierarchy with one impl is large. Inversion is cheap; abstraction without consumers is expensive.

### 12.3 Sans-IO, applied judiciously

The sans-IO pattern (decoupling protocol from transport) is brilliant for protocol implementations. It is overkill for application code where the protocol is HTTP and the transport is "axum routes". Reach for sans-IO when you are implementing a protocol from scratch. Not when you are wiring `axum` to `sqlx`.

---

## Curated Reading List

In rough order of importance.

1. [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/). Still the contract every public crate is judged against.
2. [Rust Edition Guide 2024](https://doc.rust-lang.org/edition-guide/rust-2024/index.html). Authoritative reference for what changed in the latest edition.
3. [Rust Blog 1.85 announcement](https://blog.rust-lang.org/2025/02/20/Rust-1.85.0/). The big one. Edition 2024, async closures, MSRV-aware resolver.
4. [matklad, Large Rust Workspaces](https://matklad.github.io/2021/08/22/large-rust-workspaces.html). The canonical reference for flat workspace layout, virtual manifests, crate naming.
5. [matklad, Notes on Module System](https://matklad.github.io/2021/11/27/notes-on-module-system.html). Module organisation philosophy.
6. [Rust Project Primer](https://rustprojectprimer.com/). Best curated reference for project structure, lints, CI, dependency management. Living document.
7. [Cargo Book](https://doc.rust-lang.org/cargo/). Authoritative reference for everything `Cargo.toml` and workspace.
8. [Niko Matsakis, Dyn async traits series](https://smallcultfollowing.com/babysteps/series/dyn-async-traits/). The definitive explanation of the trade-offs around async fn in traits.
9. [Firezone, Sans-IO pattern in Rust](https://www.firezone.dev/blog/sans-io). Best contemporary explanation of the pattern.
10. [Iroh, Trying to get error backtraces in Rust libraries right](https://www.iroh.computer/blog/error-handling-in-iroh). Why thiserror + anyhow is sometimes not enough, and what to do about it.
11. [corrode blog](https://corrode.dev/blog/). Consistently high-signal Rust posts. "Make Illegal States Unrepresentable", "Defensive Programming Patterns", "Rust Hashmap Performance".
12. [Effective Rust](https://effective-rust.com/). Item-by-item style guide modeled on Scott Meyers's "Effective C++". Worth reading end to end.
13. [The Rust Performance Book](https://nnethercote.github.io/perf-book/). Build profiles, profile-guided optimisation, profiling tools.
14. [tokio.rs/tokio/tutorial](https://tokio.rs/tokio/tutorial). Still the canonical Tokio onboarding path.
15. [axum docs](https://docs.rs/axum). Idiomatic axum patterns, including state, extractors, middleware.
16. [Cargo Book, Lints](https://doc.rust-lang.org/cargo/reference/lints.html). Workspace lints, inheritance, priority.
17. [clippy lints index](https://rust-lang.github.io/rust-clippy/master/index.html). Searchable list of every clippy lint with examples.
18. [release-plz](https://release-plz.dev/). The 2026 winner for Rust release engineering.
19. [Kobzol, Two ways of interpreting visibility in Rust](https://kobzol.github.io/rust/2025/04/23/two-ways-of-interpreting-visibility-in-rust.html). Why `pub` versus `pub(crate)` is more nuanced than it looks.
20. [This Week in Rust](https://this-week-in-rust.org/). Weekly community pulse. Skim the "Crates of the Week" and "Updates from the Rust Project" sections.

---

## What to Skip

Patterns that still show up in older blog posts but should be retired:

- **`mod.rs` everywhere.** Use `foo.rs + foo/` for new modules.
- **`#[async_trait]` for every trait with async methods.** Use native async fn for static dispatch; reach for `async-trait` or `dynosaur` only when you need `dyn Trait`.
- **`error-chain` and `failure`.** Dead. Use `thiserror` + `anyhow`.
- **`structopt`.** Merged into `clap` v3. Use `clap` derive directly.
- **`actions-rs/*` GitHub Actions.** Unmaintained since 2022. Use `dtolnay/rust-toolchain`, `Swatinem/rust-cache`, and `taiki-e/install-action`.
- **`async-std`.** No longer maintained. Use `tokio` (or `smol` for niche cases).
- **`cargo audit` in CI.** Subsumed by `cargo deny`. Run one, not both.
- **`cargo make` and `just` for project-wide tasks.** `xtask` solves this with no extra tool installation.
- **Putting the main crate at the workspace root.** Use a virtual root.
- **Writing one-impl traits "for testability".** Inline the struct; add the trait when the second impl arrives. Use `mockall` or hand-rolled fakes once it does.
- **Hand-rolling `Pin<Box<dyn Future>>` returns.** Use `async fn` in traits if possible; otherwise `async-trait` or `dynosaur`.
- **`Box<dyn Error>` for new error types.** Use `thiserror` for libraries.
- **`std::sync::Mutex` in async code.** It can deadlock when held across `.await`. Use `tokio::sync::Mutex` or `parking_lot::Mutex` with care (the latter is sync but does not poison on panic).
- **`Vec<u8>` for binary IDs that are always 16 bytes.** Use `[u8; 16]` or a newtype around it.
- **Storing `Arc<String>` for shared strings.** Use `Arc<str>` or `compact_str::CompactString`.
- **Manual `Future` impls in 2026.** Almost never necessary. `async fn` covers it.

---

## Quick-Start Scaffold (Day-One 2026 Rust Workspace)

```
my-thing/
  .cargo/config.toml
  .github/workflows/ci.yml
  Cargo.toml
  Cargo.lock
  README.md
  rust-toolchain.toml
  rustfmt.toml
  deny.toml
  crates/
    my-thing-core/
      Cargo.toml
      src/lib.rs
    my-thing-cli/
      Cargo.toml
      src/main.rs
  xtask/
    Cargo.toml
    src/main.rs
```

### `Cargo.toml` (workspace root)

```toml
[workspace]
resolver = "3"
members  = ["crates/*", "xtask"]

[workspace.package]
edition       = "2024"
rust-version  = "1.85"
license       = "MIT OR Apache-2.0"
repository    = "https://github.com/you/my-thing"
authors       = ["You <you@example.com>"]
version       = "0.1.0"

[workspace.dependencies]
anyhow      = "1"
clap        = { version = "4", features = ["derive"] }
serde       = { version = "1", features = ["derive"] }
serde_json  = "1"
thiserror   = "1"
tokio       = { version = "1.40", features = ["macros", "rt-multi-thread"] }
tracing     = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
my-thing-core = { path = "crates/my-thing-core", version = "=0.1.0" }

[workspace.lints.rust]
unsafe_code      = "forbid"
unreachable_pub  = "warn"
missing_docs     = "warn"
rust_2018_idioms = { level = "warn", priority = -1 }

[workspace.lints.clippy]
pedantic                = { level = "warn", priority = -1 }
cargo                   = { level = "warn", priority = -1 }
module_name_repetitions = "allow"
missing_errors_doc      = "allow"
missing_panics_doc      = "allow"
must_use_candidate      = "allow"
unwrap_used             = "warn"
expect_used             = "warn"
panic                   = "warn"

[profile.release]
lto             = "thin"
codegen-units   = 1
strip           = "symbols"
```

### `rust-toolchain.toml`

```toml
[toolchain]
channel    = "1.85"
components = ["rustfmt", "clippy", "rust-src"]
profile    = "minimal"
```

### `rustfmt.toml`

```toml
edition       = "2024"
style_edition = "2024"
```

### `.cargo/config.toml`

```toml
[alias]
xtask = "run --quiet --package xtask --"

[target.x86_64-unknown-linux-gnu]
linker    = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=mold"]
```

### `deny.toml`

```toml
[advisories]
yanked  = "deny"
unmaintained = "warn"

[bans]
multiple-versions = "warn"
wildcards         = "deny"

[licenses]
allow = ["MIT", "Apache-2.0", "Apache-2.0 WITH LLVM-exception", "BSD-3-Clause", "ISC", "Unicode-3.0", "Zlib"]
confidence-threshold = 0.9
```

### `crates/my-thing-core/Cargo.toml`

```toml
[package]
name                   = "my-thing-core"
edition.workspace      = true
rust-version.workspace = true
license.workspace      = true
repository.workspace   = true
version.workspace      = true

[dependencies]
serde     = { workspace = true }
thiserror = { workspace = true }
tracing   = { workspace = true }

[lints]
workspace = true
```

### `crates/my-thing-core/src/lib.rs`

```rust
//! Domain types and traits for my-thing.
//!
//! This crate has zero I/O. All side effects happen in adapter crates.

#![doc = include_str!("../../../README.md")]

mod config;
mod error;

pub use config::{Config, ConfigBuilder};
pub use error::{Error, Result};
```

### `crates/my-thing-cli/Cargo.toml`

```toml
[package]
name                   = "my-thing-cli"
edition.workspace      = true
rust-version.workspace = true
license.workspace      = true
version.workspace      = true

[[bin]]
name = "my-thing"
path = "src/main.rs"

[dependencies]
anyhow             = { workspace = true }
clap               = { workspace = true }
my-thing-core      = { workspace = true }
tokio              = { workspace = true }
tracing            = { workspace = true }
tracing-subscriber = { workspace = true }

[lints]
workspace = true
```

### `crates/my-thing-cli/src/main.rs`

```rust
use anyhow::{Context, Result};
use clap::Parser;

#[derive(Parser)]
#[command(version, about)]
struct Cli {
    /// Configuration file path
    #[arg(short, long, default_value = "config.toml")]
    config: std::path::PathBuf,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let cli = Cli::parse();
    let cfg = my_thing_core::Config::load(&cli.config)
        .with_context(|| format!("loading config from {}", cli.config.display()))?;

    tracing::info!(?cfg, "started");
    Ok(())
}
```

### `xtask/Cargo.toml`

```toml
[package]
name              = "xtask"
edition.workspace = true
version           = "0.0.0"
publish           = false

[dependencies]
anyhow = { workspace = true }
clap   = { workspace = true }
```

### `xtask/src/main.rs`

```rust
use anyhow::Result;
use clap::{Parser, Subcommand};

#[derive(Parser)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Run all CI checks locally.
    Ci,
    /// Format, lint, test.
    Check,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.cmd {
        Cmd::Ci    => ci(),
        Cmd::Check => check(),
    }
}

fn ci() -> Result<()> {
    sh("cargo fmt --all -- --check")?;
    sh("cargo clippy --workspace --all-targets --all-features -- -D warnings")?;
    sh("cargo nextest run --workspace --all-features")?;
    sh("cargo doc --workspace --no-deps --all-features")?;
    Ok(())
}

fn check() -> Result<()> {
    sh("cargo fmt --all")?;
    sh("cargo clippy --workspace --all-targets --all-features")?;
    sh("cargo nextest run --workspace")?;
    Ok(())
}

fn sh(cmd: &str) -> Result<()> {
    let status = std::process::Command::new("sh")
        .arg("-c")
        .arg(cmd)
        .status()?;
    anyhow::ensure!(status.success(), "command failed: {cmd}");
    Ok(())
}
```

### `.github/workflows/ci.yml`

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  fmt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with: { components: rustfmt }
      - run: cargo fmt --all -- --check
  clippy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with: { components: clippy }
      - uses: Swatinem/rust-cache@v2
      - run: cargo clippy --workspace --all-targets --all-features -- -D warnings
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: Swatinem/rust-cache@v2
      - uses: taiki-e/install-action@nextest
      - run: cargo nextest run --workspace --all-features
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: Swatinem/rust-cache@v2
      - run: cargo doc --workspace --no-deps --all-features
        env:
          RUSTDOCFLAGS: -D warnings
  deny:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: EmbarkStudios/cargo-deny-action@v2
```

This scaffold gives you, on day one: a virtual workspace, two crates plus an xtask, modern edition 2024, MSRV-aware resolver, workspace inheritance for everything, pedantic clippy with a sensible allow list, `forbid(unsafe_code)` by default, README-as-docs, mold linker, sccache-ready (set `RUSTC_WRAPPER=sccache` if installed), cargo-deny supply chain check, and a CI matrix that runs the full check suite on every push.

---

## Source Quality Assessment

Confidence: high for the established conventions (workspace structure, error handling, async traits, edition 2024 changes, clippy patterns) because the community has converged and the documentation is consistent. Medium for the bleeding-edge picks (divan vs criterion, kanal vs flume, async fn in traits dynamic dispatch story) because the picture is still moving. Low for any specific dependency version recommendations because they will drift; treat the dependency table as a snapshot, not a contract.

Primary sources consulted:

- Rust Blog official announcements (1.85, edition 2024, project goals)
- Rust Edition Guide (authoritative for what changed)
- Cargo Book (workspace, lints, profiles)
- Rust API Guidelines (still the standard)
- matklad's blog (workspace organisation, module system)
- Niko Matsakis's "baby steps" blog (async traits, dyn dispatch)
- corrode.dev (state encoding, defensive programming)
- Rust Project Primer (lints, CI)
- Iroh blog (error backtraces, async challenges)
- Firezone blog (sans-IO pattern)
- Rust Performance Book (build configuration, PGO, LTO)
- Tokio docs (structured concurrency, JoinSet)
- LogRocket and Leapcell blogs (cross-comparison content, generally high quality)

Gaps to flag:

- The async fn in traits dyn dispatch story is genuinely unsettled. `dynosaur` is the official answer but adoption is early.
- Type-state pattern guidance is more matter of taste than community consensus. The advice here leans pragmatic.
- The Bevy and `embedded-hal` worlds have somewhat different conventions (large monorepos with their own structural patterns, no_std constraints). This document targets server-side and CLI Rust.

## Open Questions

- How will `gen` blocks and stabilised generators reshape iterator code in late 2026 / 2027?
- Will `dynosaur` see broad adoption, or will the community settle for "keep `async-trait` for `dyn`"?
- Will the `let`-chain stabilisation produce a corresponding `if let && else` pattern that lets you bind in the success branch and have an explicit failure branch?
- Will `n0-error` or a similar location-aware error crate displace `thiserror` + `anyhow` for large applications, or stay niche?
- The serialisation ecosystem (serde vs rkyv vs borsh) is bifurcating between human-readable and binary use cases. Will a unified successor emerge?

## Actionable Takeaways

For a new Rust project in 2026:

1. Start with the quick-start scaffold above. Adjust the dependency list to taste.
2. Pin to Rust 1.85 (or whatever is current) via `rust-toolchain.toml`.
3. Use edition 2024 unconditionally.
4. `forbid(unsafe_code)` by default.
5. `thiserror` for library crates, `anyhow` for `main`.
6. `tokio` runtime unless you have a specific reason.
7. `tracing` for logging.
8. `cargo nextest` for tests.
9. `cargo deny` for supply chain.
10. `xtask` for project-specific commands.
11. Lint with pedantic clippy at workspace level, allow the noisy ones.
12. Document with `include_str!("../README.md")` and intra-doc links.

For an existing project upgrading to 2026 conventions:

1. Run `cargo fix --edition --edition-idioms` to migrate to edition 2024.
2. Move per-crate lints into a workspace `[workspace.lints]` block.
3. Replace `actions-rs/*` CI actions with `dtolnay/rust-toolchain` and `Swatinem/rust-cache`.
4. Replace `cargo audit` in CI with `cargo deny`.
5. Replace `async-trait` invocations on static-dispatch traits with native `async fn`.
6. Audit `Arc<Mutex<...>>` usage; replace with channels, `arc-swap`, or `DashMap` where it makes sense.
7. Convert `mod.rs` files to `foo.rs + foo/` opportunistically (not as churn for its own sake).
8. Add `rust-toolchain.toml` if not present.
9. Set `rust-version` in `[workspace.package]` and run `cargo-msrv verify`.
10. Consider switching the test runner to `cargo nextest`.
