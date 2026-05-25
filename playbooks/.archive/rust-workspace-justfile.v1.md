---
title: Rust workspace justfile structure
type: playbooks
tags: [rust, cargo, just, justfile, check, fmt, clippy, workspace, conventions]
summary: Canonical recipe set and check pipeline for a Helioy Rust workspace justfile
status: active
project: helioy
related: [rust-workspace-cli-binary, rust-binary-workspace-cargo-dist, rust-workspace-crates-io-publishing]
confidence: high
---

# Rust workspace justfile structure

Use this when scaffolding or aligning a Rust workspace `justfile`. It defines the recipe set every Helioy Rust workspace exposes, the check pipeline, and which behaviors belong here versus in a companion playbook.

This playbook owns the shape of the file. CLI install pipeline and version stamping live together in `rust-workspace-cli-binary.md`. GitHub Releases plumbing lives in `rust-binary-workspace-cargo-dist.md`. crates.io publishing lives in `rust-workspace-crates-io-publishing.md`.

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
| `build` | `cargo build --workspace` | This playbook |
| `release-build` | `cargo build --workspace --release` | This playbook |
| `build-local` | Build the CLI bin under the `install-local` profile, sha embedded | [[rust-workspace-cli-binary]] |
| `build-install-release` | Build the CLI bin under `--release`, no sha | [[rust-workspace-cli-binary]] |
| `install-local` | Copy `build-local` output to `<PROJECT>_LOCAL_BIN`, run `--version` | [[rust-workspace-cli-binary]] |
| `install-release` | Copy `build-install-release` output to `<PROJECT>_LOCAL_BIN`, run `--version` | [[rust-workspace-cli-binary]] |
| `_install-bin src` | Shared dest resolution + copy + `"$dest" --version` | [[rust-workspace-cli-binary]] |
| `test *ARGS` | `cargo nextest run --workspace {{ARGS}}` (or `cargo test --workspace`) | This playbook |
| `test-doc` | `cargo test --workspace --doc` when the workspace has doctests | This playbook |
| `bench` | Workspace-specific benchmark entry | This playbook |
| `dist *ARGS` | `cargo dist build` or `dist build` | [[rust-binary-workspace-cargo-dist]] |
| `release *ARGS` | release-please / release-plz invocation when used | [[rust-binary-workspace-cargo-dist]] or [[rust-workspace-crates-io-publishing]] |
| `publish-dry-run` | `cargo publish --dry-run --allow-dirty -p <crate> ...` when publishing libs | [[rust-workspace-crates-io-publishing]] |
| `fmt` | `cargo fmt --all` | This playbook |
| `fmt-check` | `cargo fmt --all -- --check` | This playbook |
| `clippy` | Strict: `cargo clippy --workspace --all-targets -- -D warnings` | This playbook |
| `clippy-fix` | `cargo clippy --fix --workspace --all-targets --allow-dirty --allow-staged -- -D warnings` | This playbook |
| `check-loc` | `bash scripts/check-loc-limit.sh` | This playbook |
| `check` | Apply-then-verify pipeline (see below) | This playbook |
| `<bin> *ARGS` | Convenience: `cargo run -p <bin>-cli -- {{ARGS}}` | This playbook (optional) |

Recipes specific to a project (load tests, snapshot accept, multiple bench targets) are fine. The canonical names above should not be renamed.

## Check Pipeline

The single pipeline a contributor runs before pushing.

```just
fmt:
    cargo fmt --all

fmt-check:
    cargo fmt --all -- --check

clippy:
    cargo clippy --workspace --all-targets -- -D warnings

clippy-fix:
    cargo clippy --fix --workspace --all-targets --allow-dirty --allow-staged -- -D warnings

check-loc:
    bash scripts/check-loc-limit.sh

check: fmt clippy-fix fmt-check check-loc clippy
```

Order is deliberate and matters.

1. `fmt` applies formatting.
2. `clippy-fix` applies clippy autofixes. May rewrite files.
3. `fmt-check` verifies the rewrites are still formatted. Catches the case where a clippy fix produced unformatted output.
4. `check-loc` enforces the per-file LOC budget before strict clippy runs to surface the cheap signal first.
5. `clippy` is the strict gate. Fails on any remaining warning that autofix could not resolve.

`clippy-fix` and strict `clippy` must stay separate recipes. CI calls strict `clippy` directly; `check` is the developer convenience that applies then verifies.

## Test Recipes

Default to `cargo nextest run --workspace` when nextest is available. Forward args so individual tests can be targeted.

```just
test *ARGS:
    cargo nextest run --workspace {{ARGS}}

test-doc:
    cargo test --workspace --doc
```

Nextest does not run doctests, so add `test-doc` whenever the workspace exposes them.

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
- Do not merge `clippy` and `clippy-fix` into one recipe. CI needs the strict-only path.
- Do not reorder the `check` recipe to put `fmt-check` before `clippy-fix`. Apply-then-verify is the contract.
- Do not hand-roll a per-recipe install helper. Use the shared `_install-bin src` so both install paths print the destination binary's `--version`.
- Do not build `--workspace --release` inside `install-local`. Build the CLI bin under the `install-local` profile per [[rust-workspace-cli-binary]].
- Do not put cargo-dist or release-please bodies in the justfile. Recipes here should be thin shims; configuration lives in `release-please-config.json`, `Cargo.toml`'s `[workspace.metadata.dist]`, and `release-plz.toml`.
- Do not rename `check-loc` to `loc`. The `check-` prefix matches the apply-then-verify naming and groups it with `fmt-check`.

## Good Completion Evidence

An acceptable closeout when bringing a workspace justfile to parity includes:

- `just --list` output showing the canonical recipe set.
- `just check` passing in apply-then-verify order.
- A temp destination `install-local` and `install` round trip with the expected `--version` shapes from [[rust-workspace-cli-binary]].
- `cargo nextest run --workspace` (or `cargo test --workspace`) passing.
- A cm decision entry naming the playbook contract, the recipes added, and the verification results.
