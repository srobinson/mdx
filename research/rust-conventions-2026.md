---
title: Rust Conventions for Agents, 2026
tags: [rust, conventions, cargo, workspace, api-design, async, errors, clippy, docs, testing, ci]
summary: Condensed operating instructions for agents working in modern Rust projects.
created: 2026-05-26
updated: 2026-05-30
---
# Rust Conventions for Agents, 2026
This file is an instruction guide, not a survey.
Use it when creating, editing, reviewing, or planning Rust code.
Prefer the project conventions in front of you when they are explicit.
Use this guide when the repo is silent, inconsistent, or newly scaffolded.
If a local `AGENTS.md`, `CLAUDE.md`, issue body, or design record conflicts
with this file, follow the local source of truth.
## Agent Rules
Validate before acting.
Read the existing crate shape before adding code.
Search before creating helpers, types, traits, modules, constants, or files.
Do not introduce duplicate paths for the same behavior.
Delete old paths during refactors unless a staged migration is explicit.
Keep public API changes deliberate and easy to review.
Keep private implementation changes boring.
Do not expand scope because a pattern looks convenient.
Run the repo's documented checks before claiming done.
If no documented checks exist, run fmt, clippy, build, tests, and docs.
Prefer stable Rust.
Avoid nightly unless the project already requires it.
Do not add dependencies casually.
Do not add traits for testability unless a second real implementation exists.
Do not hand roll async runtimes, protocol loops, or parsers when the project
already has a proven local abstraction.
Write comments only where they prevent real confusion.
## Project Shape
Use a Cargo workspace for any project likely to grow beyond one artifact.
Prefer a virtual root manifest.
The root `Cargo.toml` should usually have `[workspace]`, not `[package]`.
Keep the workspace root free of `src/` unless there is one dominant artifact.
Use `crates/` for published crates.
Use `internal/` or another clearly private directory for non-published crates.
Keep crate directories flat unless the repo has a locked target layout.
Folder names should match package names.
Use kebab case for package names.
Use the product prefix in crate names.
Common suffixes:
- `-core` for domain types and pure logic.
- `-store` for storage backends.
- `-cli` for command line surfaces.
- `-daemon` for long running processes.
- `-driver` for external process or service adapters.
- `-macros` for procedural macros.
- `-derive` for derive only procedural macros.
- `-testing` for test helpers.
Use `version = "0.0.0"` or `publish = false` for internal crates when the
project wants to prevent accidental publication.
For monorepos with public and internal crates, make publishability explicit.
## Workspace Manifest
The root manifest is the source of truth for shared metadata.
Use `[workspace.package]` for shared version, edition, license, repository,
homepage, authors, and `rust-version`.
Use `[workspace.dependencies]` for shared dependencies.
Use exact internal path dependencies when workspace packages release together.
Use `[workspace.lints]` for shared lint policy.
Every member crate should opt in with:
```toml
[lints]
workspace = true
```
Member manifests should inherit shared fields:
```toml
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true
repository.workspace = true
authors.workspace = true
```
Add `homepage.workspace = true` when the workspace defines it.
Do not repeat dependency versions in member crates when the root has them.
Use:
```toml
serde.workspace = true
thiserror.workspace = true
```
Avoid wildcard dependencies.
Avoid path dependencies that bypass workspace dependency declarations unless
there is a strong local reason.
## Edition and Toolchain
Default new Rust code to edition 2024.
Pin the contributor toolchain in `rust-toolchain.toml`.
Set `rust-version` in `[workspace.package]`.
The toolchain channel and `rust-version` should usually match.
Use resolver 3 with edition 2024 workspaces.
A typical toolchain file:
```toml
[toolchain]
channel = "1.95"
components = ["clippy", "rustfmt", "rust-src"]
```
Run `cargo msrv` or equivalent when raising MSRV matters.
Do not use new syntax unless the pinned toolchain supports it.
## Modules and Files
For new modules, prefer `foo.rs` plus `foo/` children.
Avoid new `mod.rs` files.
Accept existing `mod.rs` in old code when churn is not worth it.
Reasonable `mod.rs` exceptions:
- `tests/common/mod.rs`.
- Generated module indexes.
- Legacy areas outside the change scope.
The crate root is the public API gate.
Use private modules by default.
Promote visibility only when needed.
Use `pub(crate)` for crate internal sharing.
Use `pub(super)` for parent module helpers.
Use `pub` only for intentional public API.
Re-export named public items from `lib.rs`.
Avoid glob re-exports from crate roots.
Prefer:
```rust
pub use error::{Error, Result};
pub use store::{Store, StoreConfig};
```
Avoid:
```rust
pub use error::*;
pub use store::*;
```
Split files when they become hard to scan.
Keep new files below the repo's local line limit.
If no local limit exists, treat 700 lines as a hard stop.
Break functions before they hide separate responsibilities.
Treat 150 lines as a warning sign for a function.
Prefer cohesive modules over one type per file.
## API Design
Follow the Rust API Guidelines for public crates.
Use `snake_case` for functions, methods, modules, and variables.
Use `CamelCase` for types and traits.
Use `SCREAMING_SNAKE_CASE` for constants.
Error types should end in `Error`.
Use a crate local `Result<T>` alias when it improves readability:
```rust
pub type Result<T> = std::result::Result<T, Error>;
```
Use `as_`, `to_`, and `into_` according to Rust convention:
- `as_` borrows or views.
- `to_` clones or converts without consuming.
- `into_` consumes.
Use `From` for infallible conversions.
Use `TryFrom` for fallible conversions.
Prefer implementing `From<T>` over encouraging callers to use `Into<T>`.
Use newtypes when a primitive has domain meaning.
Use concrete argument types first.
Generalize only when a second caller needs it.
Avoid generic surfaces like `T: AsRef<str>` until they buy something real.
Avoid public type parameters that leak implementation detail.
Prefer builders when construction has several optional fields.
For simple configs, hand write a small builder or constructor.
Use derive builder crates only when the benefit is obvious.
Do not add a trait for one implementation.
A trait is justified when:
- Callers need to supply independent implementations.
- Dynamic dispatch is required.
- The abstraction is part of the public contract.
- Tests need a fake and there is also a real second implementation boundary.
## Error Handling
Use `thiserror` for library and internal library crates.
Use `anyhow` for binaries and top level application orchestration.
Use `color-eyre` only when pretty terminal reports are a product requirement.
Avoid `Box<dyn Error>` for new structured error types.
Do not use `failure` or `error-chain`.
Library errors should be matchable when callers need recovery.
Application errors should carry context.
Use `?` freely.
Add context near I/O, process, network, and serialization boundaries.
Avoid manual `match` arms that only rewrap `?`.
Use source chaining through `#[from]` where it preserves meaning.
Do not erase domain errors into strings too early.
Convert to user facing diagnostics at the CLI or API edge.
## Async
Tokio is the default runtime for server side and CLI Rust in 2026.
Use runtime agnostic code only when portability is a real requirement.
Do not hand roll an event loop when Tokio primitives fit.
Use native trait futures for static dispatch.
For public traits, prefer explicit returned futures so Clippy and callers can
see `Send` bounds:
```rust
pub trait Store {
    fn get(&self, key: &str) -> impl Future<Output = Result<Value>> + Send;
}
```
Avoid `async-trait` unless dynamic dispatch is required.
Keep `async-trait` when the code needs:
- `Box<dyn Trait>`.
- `&dyn Trait`.
- Collections of heterogeneous trait objects.
- A stable dyn safe trait surface.
If dynamic async traits are central, consider a dedicated dyn shim.
Use `JoinSet` for groups of spawned tasks.
Use cancellation tokens when cancellation is part of the design.
Be careful with `tokio::select!`; only select over cancel safe operations.
Use channels deliberately.
Prefer bounded channels unless unbounded growth is acceptable.
Keep raw `JoinHandle` and `JoinError` shapes out of high level APIs.
## Dependencies
Before adding a dependency, check:
- Is there already a local helper?
- Is the crate maintained?
- Does it pull in a large feature tree?
- Does it affect compile time materially?
- Is the API stable enough for this project?
- Are alternatives clearly worse?
Use standard crates unless the repo has chosen differently:
- Serialization: `serde`, `serde_json`.
- Errors for libraries: `thiserror`.
- Errors for applications: `anyhow`.
- Async runtime: `tokio`.
- CLI: `clap` derive.
- Logging and instrumentation: `tracing`.
- Config: `toml`, `serde`.
- SQLite: `rusqlite` or the repo's chosen async wrapper.
- Snapshots: `insta`.
- Property tests: `proptest`.
- Test fixtures: `rstest`.
- Temp files: `tempfile`.
Feature flags must be additive.
Do not make one feature silently change the meaning of another.
Use `compile_error!` for mutually exclusive features.
Document meaningful features in `Cargo.toml` or crate docs.
Avoid feature matrices the project cannot test.
## Logging and Diagnostics
Use `tracing` for new application and library instrumentation.
Use structured fields.
Prefer:
```rust
tracing::info!(session_id = %id, "session started");
```
Avoid formatting everything into the message string.
Libraries may use `tracing` without choosing a subscriber.
Binaries own subscriber setup.
Keep CLI diagnostics stable and testable.
Separate machine readable JSON output from human output.
## Lints and Formatting
Use rustfmt defaults unless the repo has a small explicit config.
Set rustfmt style edition to 2024 when the project uses a rustfmt config.
Use Clippy in CI with warnings denied.
A practical baseline:
```toml
[workspace.lints.rust]
unsafe_code = "forbid"
[workspace.lints.clippy]
pedantic = "warn"
module_name_repetitions = "allow"
missing_errors_doc = "allow"
missing_panics_doc = "allow"
must_use_candidate = "allow"
```
Use local `#[allow]` only when justified.
Prefer narrow allows over crate wide allows.
Useful individual Clippy lints:
- `needless_pass_by_value`.
- `return_self_not_must_use`.
- `unnested_or_patterns`.
- `unwrap_used` for production crates.
- `expect_used` where panics are unacceptable.
It is fine to enable useful pedantic lints incrementally.
Do not enable a lint without making the repo clean under the project gate.
## Unsafe
Default to forbidding unsafe:
```rust
#![forbid(unsafe_code)]
```
Only allow unsafe in crates that have a clear reason.
Every unsafe block must have a `SAFETY:` comment explaining the invariant.
The comment must explain why the operation is valid here.
Do not write ceremonial safety comments.
Run Miri for crates with meaningful unsafe code when feasible.
Use `unsafe extern` as required by edition 2024.
Keep FFI boundaries small.
## Testing
Use inline unit tests for private logic.
Use integration tests for public API behavior.
Use doctests for examples that users should be able to copy.
Use snapshot tests when output shape stability matters.
Use property tests for parsers, serializers, and state transitions where broad
input coverage matters.
Use `cargo nextest` when available.
Serialize tests that share a global resource (a tmux server, a fixed port, a
singleton daemon) with a nextest test group capped at `max-threads = 1` in
`.config/nextest.toml`; otherwise they flake under parallel execution.
Do not run `cargo test -p crate test_name` for integration test files unless
you have confirmed it executes the intended tests.
Prefer:
```bash
cargo test -p crate --test test_file
```
When changing CLI output, test both human and JSON surfaces if both exist.
When changing generated surfaces, update the authored source first, then
regenerate and verify the generated output.
## Documentation
Treat `cargo doc` as part of the public API surface.
Run:
```bash
cargo doc --workspace --no-deps
```
Use intra doc links for public API references.
Broken intra doc links should fail CI when practical.
Library crates should have crate level docs.
Public items should have docs when they are meant for external users.
For internal crates, document public items that are cross crate contracts.
Keep README examples synchronized with crate docs.
Do not add marketing prose where an API example is needed.
## Build and CI
The normal local proof should include:
```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo build --workspace --all-features
cargo test --workspace --all-features
cargo doc --workspace --no-deps --all-features
```
If the repo uses `just`, `xtask`, Moon, Bazel, or another operator surface,
use the repo's commands.
Do not bypass the documented gate unless diagnosing a failure.
Use GitHub Actions with `dtolnay/rust-toolchain` and `Swatinem/rust-cache`
when creating fresh CI.
Use `cargo deny` for license, advisory, and dependency policy.
Use `release-plz` for workspace crate release automation when publishing to
crates.io.
## Performance and Build Hygiene
Prefer clarity first.
Measure before optimizing.
Use release profile settings deliberately.
Reasonable release defaults:
```toml
[profile.release]
lto = true
codegen-units = 1
strip = true
```
Use `cargo build --timings` when compile time becomes a problem.
Use `cargo tree -e features --workspace` before blaming the compiler.
When a full-workspace pre-commit gate gets slow enough that contributors skip
it, keep two gates instead of one.
Scope the fast inner-loop gate (`build`, `test`, `clippy`) to the crates that
changed plus their reverse-dependency closure, computed from `cargo metadata`,
falling back to `--workspace` on any shared-config change (root `Cargo.toml`,
`rust-toolchain.toml`, `.cargo/*`).
Keep one unconditional full-workspace gate for merge, CI, and audits so
correctness never depends on the scoping heuristic.
Do not run `cargo clippy --fix` unconditionally in the inner-loop gate; it uses
a different fingerprint mode than read-only clippy and forces a full workspace
recompile every invocation. Run read-only clippy first, `--fix` only on failure.
The full mechanism (helper script, closure walk, recipe wiring, CI composition)
is in the `rust-workspace-incremental-gates` playbook.
Avoid generic bloat on hot shared APIs.
Prefer concrete types when generics do not buy flexibility.
Use `Box<dyn Trait>` when it reduces code size or hides implementation detail.
Use generics when static dispatch and inlining are important.
## Macros
Use macros sparingly.
Prefer functions and traits when they express the design clearly.
Use declarative macros for repetitive syntax, not business logic.
Use `$crate` in exported macros that reference crate items.
Procedural macros must live in a separate crate.
Name procedural macro crates with `-macros` or `-derive`.
Test procedural macros with `trybuild`.
Use `cargo expand` when debugging macro output.
Do not hide simple control flow behind macros.
## Anti Patterns
Avoid `Arc<Mutex<_>>` as a default architecture.
Avoid traits with one implementation.
Avoid premature generic argument types.
Avoid `mod.rs` for new modules.
Avoid `async-trait` unless dyn dispatch is required.
Avoid `Box<dyn Error>` for new library error design.
Avoid `unwrap` and `expect` outside tests, examples, and invariant proofs.
Avoid manual future implementations.
Avoid hand rolled retry, timeout, and cancellation code when Tokio or a local
utility already covers the case.
Avoid generated docs or schemas without an authored source of truth.
Avoid public glob re-exports.
Avoid adding a dependency to save a few obvious lines.
Avoid keeping old and new implementations alive without an approved migration
plan.
## Review Checklist
Before signing off, ask:
- Does this follow the local repo conventions?
- Did I search for an existing helper or type?
- Did I avoid duplicate implementations?
- Is the public API intentional?
- Are errors structured at library boundaries?
- Are diagnostics converted at the edge?
- Are async traits native unless dyn dispatch is required?
- Are new modules using `foo.rs + foo/`?
- Are dependencies inherited from the workspace?
- Are useful lints enabled and clean under the repo gate?
- Did I run the documented verification commands?
- Did I verify docs when public API changed?
- Did I regenerate structural or generated surfaces after file moves?
If any answer is no, fix it or state the reason explicitly.
