---
title: Rust workspace justfile structure
type: playbooks
tags: [rust, cargo, just, justfile, check, fmt, clippy, workspace, conventions]
summary: Canonical recipe set and check pipeline for a Helioy Rust workspace justfile
status: active
project: helioy
related: [rust-workspace-cli-binary, rust-workspace-incremental-gates, rust-binary-workspace-cargo-dist, rust-workspace-crates-io-publishing]
confidence: high
---

# Rust workspace justfile structure

Use this when scaffolding or aligning a Rust workspace `justfile`. It defines the recipe set every Helioy Rust workspace exposes, the check pipeline, and which behaviors belong here versus in a companion playbook.

This playbook owns the shape of the file. CLI install pipeline and version stamping live together in `rust-workspace-cli-binary.md`. The incremental gate (scoping `build`/`test`/`clippy` to changed crates, the `changed-crates.sh` helper, the `clippy --fix` fingerprint trap, the `check` vs `regression` split) lives in `rust-workspace-incremental-gates.md`; recipe names appear here, full contract there. GitHub Releases plumbing lives in `rust-binary-workspace-cargo-dist.md`. crates.io publishing lives in `rust-workspace-crates-io-publishing.md`.

## Header Contract

Pin the shell and resolve the install destination through the environment.

```just
set shell := ["bash", "-cu"]

# Fall back to $HOME/.cargo/bin/<bin> if <PROJECT>_LOCAL_BIN is not set
SM_LOCAL_BIN := env("SM_LOCAL_BIN", env("HOME") / ".cargo/bin/sm")

default:
    @just --list
```

- `set shell := ["bash", "-cu"]` is required. Several recipes use bash idioms (`case`, `set -eu`); macOS `/bin/sh` will surprise.
- Use `env(...)` not `env_var_or_default(...)`. The newer form composes with `env("HOME") / ".cargo/bin/<bin>"` so the path is portable across machines.
- `default: @just --list` makes a bare `just` invocation print recipes. It is the discoverable entry point.

## Recipe Set

A Helioy Rust workspace justfile exposes these recipes. Items marked with a companion playbook defer their full contract there.

| Recipe | Purpose | Owned by |
| --- | --- | --- |
| `default` | List recipes | This playbook |
| `install` | Alias to `install-release` | [[rust-workspace-cli-binary]] |
| `build` | Build changed crates + reverse-dep closure (`--workspace` fallback) | [[rust-workspace-incremental-gates]] |
| `release-build` | `cargo build --workspace --release` | This playbook |
| `build-local` | Build the CLI bin under the `install-local` profile, sha embedded | [[rust-workspace-cli-binary]] |
| `build-install-release` | Build the CLI bin under `--release`, no sha | [[rust-workspace-cli-binary]] |
| `install-local` | Copy `build-local` output to `<PROJECT>_LOCAL_BIN`, run `--version` | [[rust-workspace-cli-binary]] |
| `install-release` | Copy `build-install-release` output to `<PROJECT>_LOCAL_BIN`, run `--version` | [[rust-workspace-cli-binary]] |
| `_install-bin src` | Shared dest resolution + copy + `"$dest" --version` | [[rust-workspace-cli-binary]] |
| `test *ARGS` | Nextest over changed crates + reverse-dep closure (`--workspace` fallback) | [[rust-workspace-incremental-gates]] |
| `test-doc` | `cargo test --workspace --doc` when the workspace has doctests | This playbook |
| `bench` | Workspace-specific benchmark entry | This playbook |
| `dist *ARGS` | `cargo dist build` or `dist build` | [[rust-binary-workspace-cargo-dist]] |
| `release *ARGS` | release-please / release-plz invocation when used | [[rust-binary-workspace-cargo-dist]] or [[rust-workspace-crates-io-publishing]] |
| `publish-dry-run` | `cargo publish --dry-run --allow-dirty -p <crate> ...` when publishing libs | [[rust-workspace-crates-io-publishing]] |
| `fmt` | `cargo fmt --all` | This playbook |
| `fmt-check` | `cargo fmt --all -- --check` | This playbook |
| `clippy` | Strict workspace: `cargo clippy --workspace --all-targets -- -D warnings` (fallback + `regression`) | This playbook |
| `clippy-fix` | `cargo clippy --fix --workspace --all-targets --allow-dirty --allow-staged -- -D warnings` | This playbook |
| `_clippy-incremental` | Read-only clippy over changed crates; `--fix` only on failure | [[rust-workspace-incremental-gates]] |
| `check-loc` | `bash scripts/check-loc-limit.sh` | This playbook |
| `check-provenance` | `bash scripts/check-provenance.sh` when the repo tracks imported provenance | This playbook |
| `check` | Fast pre-commit gate; incremental clippy (see below) | This playbook |
| `regression` | Unconditional full-workspace gate for merge / CI / audits | [[rust-workspace-incremental-gates]] |
| `<bin> *ARGS` | Convenience: `cargo run -p <bin>-cli -- {{ARGS}}` | This playbook (optional) |

Recipes specific to a project (load tests, snapshot accept, multiple bench targets) are fine. The canonical names above should not be renamed.

## Check Pipeline

Two gates with different jobs. `check` is the fast inner-loop gate a contributor runs before every push; `regression` is the unconditional full-workspace gate for merge, CI, and audits. The scoping mechanism (helper script, reverse-dep closure, the `clippy --fix` fingerprint trap) is owned by [[rust-workspace-incremental-gates]]; only the recipe surface lives here.

```just
fmt:
    cargo fmt --all

fmt-check:
    cargo fmt --all -- --check

# Strict workspace clippy. Used as the changed-crates fallback and by
# `regression`. Per-gate scoped runs go through `_clippy-incremental`.
clippy:
    cargo clippy --workspace --all-targets -- -D warnings

clippy-fix:
    cargo clippy --fix --workspace --all-targets --allow-dirty --allow-staged -- -D warnings

check-loc:
    bash scripts/check-loc-limit.sh

check-provenance:
    bash scripts/check-provenance.sh

# Fast pre-commit gate. Incremental by default: only the clippy step is
# scoped to changed crates. fmt / loc / provenance run workspace-wide
# because they are cheap and operate on raw files, not the compile graph.
check: fmt _clippy-incremental fmt-check check-loc check-provenance

# Full-workspace gate. Use before merging to main, in CI, or any time the
# scoping heuristic might miss a regression surface.
regression:
    cargo fmt --all -- --check
    bash scripts/check-loc-limit.sh
    bash scripts/check-provenance.sh
    cargo clippy --workspace --all-targets -- -D warnings
    cargo nextest run --workspace
```

`check` order, reading left to right:

1. `fmt` applies formatting.
2. `_clippy-incremental` runs **read-only** clippy over the changed crates + reverse-dep closure, falling back to `cargo clippy --fix` only when it fails. Running `--fix` unconditionally would force a full workspace recompile every invocation; see [[rust-workspace-incremental-gates]] for the fingerprint-mode rationale.
3. `fmt-check` verifies the tree is still formatted after any autofix.
4. `check-loc` enforces the per-file LOC budget.
5. `check-provenance` enforces tracked imported-repo provenance (omit if the repo does not import).

`clippy-fix` and strict `clippy` stay separate recipes. `regression` and CI call strict workspace `clippy` directly; `check` runs the scoped `_clippy-incremental` for the inner loop. Correctness never depends on the scoping heuristic, because `regression` re-checks the whole workspace.

If the workspace is not large enough to feel a full-workspace gate, keep `check` simple (`fmt clippy fmt-check check-loc`) and skip the incremental machinery; adopt [[rust-workspace-incremental-gates]] once the warm gate is slow enough that contributors skip it.

## Test Recipes

Default to `cargo nextest` when available. Forward args so individual tests can be targeted. The plain workspace shape:

```just
test *ARGS:
    cargo nextest run --workspace {{ARGS}}

test-doc:
    cargo test --workspace --doc
```

When the workspace adopts the incremental gate, `test` scopes nextest to the changed crates + reverse-dep closure with a `--workspace` fallback; see [[rust-workspace-incremental-gates]] for that shape.

Nextest does not run doctests, so add `test-doc` whenever the workspace exposes them.

Tests that contend on a global resource (a tmux server, a fixed port, a singleton daemon) must be capped in `.config/nextest.toml` or they flake under parallelism. Declare a test group with `max-threads = 1` and bind it with a filter; the cap then holds in both scoped and full runs. The full contract is in [[rust-workspace-incremental-gates]].

If nextest is not adopted in the repo, drop both to `cargo test --workspace`.

## Bench Recipes

Benches are workspace specific. Pick the shape that matches the harness.

```just
bench:
    cargo build --release -p sm-cli
    SM_BENCH_BIN="{{ justfile_directory() }}/target/release/sm" cargo bench -p sm-cli --bench hot_path
```

When a workspace has multiple bench targets, expose one recipe per target with a `bench-<target>` name. Do not bundle unrelated benches behind a single recipe.

## Run Shortcut

Optional, but recommended for CLIs. Lets contributors drive the binary without remembering the package flag.

```just
sm *ARGS:
    cargo run -p sm-cli -- {{ARGS}}
```

Name the recipe after the installed binary, not the package.

## What Belongs Elsewhere

These pieces are documented by sibling playbooks. Reference them rather than re-deriving:

- `install`, `install-local`, `install-release`, `build-local`, `build-install-release`, the shared `_install-bin` helper, the `<PROJECT>_VERSION_INCLUDE_GIT_SHA` env var, the build-time `<PROJECT>_CLI_VERSION` stamp, clap `display_name` and `version = crate::VERSION` wiring, and the `--version` test contract: `rust-workspace-cli-binary.md`.
- `scripts/changed-crates.sh`, the `BASE_REF` override, the `build`/`test`/`_clippy-incremental` scoping branch, the `clippy --fix` fingerprint trap, the `check` vs `regression` split, the nextest test-group serialization, and CI composition with rust-cache + `moon ci`: `rust-workspace-incremental-gates.md`.
- `[profile.dist]`, cargo-dist targets, and the release-please workflow: `rust-binary-workspace-cargo-dist.md`.
- `release-plz` configuration and `CARGO_REGISTRY_TOKEN` plumbing: `rust-workspace-crates-io-publishing.md`.

## Verification Recipe

After editing a justfile, run the local gate:

```bash
just --list
just check
just build
just test
```

When the repo runs the incremental gate, also run the full gate once to confirm nothing scoped out a regression:

```bash
just regression
```

Then verify install switching against a temp destination per [[rust-workspace-cli-binary]] and confirm `--version` output shape per [[rust-workspace-cli-binary]]:

```bash
tmpdir="$(mktemp -d)"
timeout 180s env <PROJECT>_LOCAL_BIN="$tmpdir/<bin>" just install-local
"$tmpdir/<bin>" --version
timeout 300s env <PROJECT>_LOCAL_BIN="$tmpdir/<bin>" just install
"$tmpdir/<bin>" --version
```

## Guardrails

- Do not omit `set shell := ["bash", "-cu"]`. macOS `/bin/sh` will not run `_install-bin` correctly.
- Do not merge `clippy` and `clippy-fix` into one recipe. `regression` and CI need the strict-only path; `check` runs the scoped `_clippy-incremental`.
- Do not put `clippy --fix` in `check`'s direct path. It uses a different fingerprint mode than read-only clippy and forces a full workspace recompile every run, defeating the incremental gate. Run read-only first, `--fix` on failure (see [[rust-workspace-incremental-gates]]).
- Do not let `check` be the merge gate. It is the fast inner-loop accelerator; `regression` (and CI) is the unconditional full-workspace gate.
- Do not put `fmt-check` before `fmt` in `check`. `fmt` applies, `fmt-check` verifies; that apply-then-verify pair is still the contract.
- Do not hand-roll a per-recipe install helper. Use the shared `_install-bin src` so both install paths print the destination binary's `--version`.
- Do not build `--workspace --release` inside `install-local`. Build the CLI bin under the `install-local` profile per [[rust-workspace-cli-binary]].
- Do not put cargo-dist or release-please bodies in the justfile. Recipes here should be thin shims; configuration lives in `release-please-config.json`, `Cargo.toml`'s `[workspace.metadata.dist]`, and `release-plz.toml`.
- Do not rename `check-loc` to `loc`. The `check-` prefix groups it with `fmt-check` and `check-provenance` as the file-level checks in `check`.

## Good Completion Evidence

An acceptable closeout when bringing a workspace justfile to parity includes:

- `just --list` output showing the canonical recipe set.
- `just check` passing (and `just regression` passing when the incremental gate is adopted).
- A temp destination `install-local` and `install` round trip with the expected `--version` shapes from [[rust-workspace-cli-binary]].
- `cargo nextest run --workspace` (or `cargo test --workspace`) passing.
- A cm decision entry naming the playbook contract, the recipes added, and the verification results.
