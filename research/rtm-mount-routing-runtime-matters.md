---
title: Runtime Matters Mount Parser Routing Assessment
type: research
tags: [runtime-matters, rtm, mounts, orchestration, helioy-bus]
summary: runtime-matters already owns the mount wire contract and daemon validation; the remaining runtime-side work is a small parser export batch that fits MoE Local Batch.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-24
updated: 2026-05-24
---

## Executive Summary

`runtime-matters` already exposes the durable mount protocol through `lilo-rm-core::MountSpec` and `SpawnRequest.mounts`, and the daemon already validates Docker mount behavior, cwd auto-mount suppression, and host isolation tolerance. The missing reusable seam is the CLI mount parser, currently private inside `rtm-cli`; the runtime-side work is best routed as MoE Local Batch A, while the `session-matters` consumer work should remain a separate cross-repo follow-up.

## Project Metadata

- Language: Rust, workspace edition 2024, Rust version 1.90 from `Cargo.toml`.
- Build system: Cargo workspace with `rtm-core`, `rtm-client`, `rtm-daemon`, `rtm-cli`, and support crates.
- Public protocol crate: `lilo-rm-core` version 0.7.0, exported as `lilo_rm_core`.
- CLI crate: `rtm-cli`, binary `rtm`, depends on `lilo-rm-core`, `lilo-rm-client`, and `rtm-daemon`.
- fmm status: `fmm validate` reported all 143 indexed files up to date.

## Architecture

### Mount protocol and parser surface

- `MountSpec` already lives in the public protocol crate with the required shape: `source: PathBuf`, `target: PathBuf`, `read_only: bool` at `crates/rtm-core/src/types/spawn.rs:78-83`.
- `SpawnRequest.mounts` is public, defaults to empty, and omits empty vectors on serialization at `crates/rtm-core/src/types/spawn.rs:86-103`.
- `crates/rtm-core/src/types.rs` re-exports `MountSpec` and `SpawnRequest`, and `crates/rtm-core/src/lib.rs` re-exports those protocol types at crate root.
- `rtm spawn --mount` parsing is currently private to `rtm-cli` in `parse_mount_spec` at `crates/rtm-cli/src/cli/spawn.rs:91-125`.
- The parser already implements the requested grammar: `HOST:CONTAINER[:ro|:rw]`, default read only, `:ro`, `:rw`, missing separator rejection, empty source or target rejection, and unknown mode rejection.
- Host source `~` expansion is also private to `rtm-cli` in `expand_mount_source` at `crates/rtm-cli/src/cli/spawn.rs:127-139`.
- Public CLI host-isolation rejection is local to `rtm-cli` in `reject_host_mounts` at `crates/rtm-cli/src/cli/spawn.rs:84-89`.

### Daemon validation surface

- Direct RPC with host isolation tolerates mounts by warning only through `warn_host_mounts` at `crates/rtm-daemon/src/spawn_preflight.rs:113-121`, called by `check_isolation_policy` at `crates/rtm-daemon/src/spawn_preflight.rs:61-75`.
- Docker profiles call `validate_docker_mounts` at `crates/rtm-daemon/src/spawn_preflight.rs:123-131` from `check_docker_profile` at `crates/rtm-daemon/src/spawn_preflight.rs:77-111`.
- `validate_docker_mounts` canonicalizes cwd and mount sources, rejects duplicate normalized targets, validates cwd mount planning, and rejects uncovered path-shaped environment values.
- cwd auto-mount behavior is centralized in `validate_cwd_mount_plan` at `crates/rtm-daemon/src/docker_mount_plan.rs:42-64`.
- `select_cwd_cover` chooses the most specific explicit mount that covers cwd and rejects equal-precedence ambiguity at `crates/rtm-daemon/src/docker_mount_plan.rs:70-104`.
- `reject_cwd_source_descendants` rejects explicit mount sources that sit below the cwd auto-mount source at `crates/rtm-daemon/src/docker_mount_plan.rs:106-120`.

## Key Patterns

- Keep wire types and reusable parsing in `lilo-rm-core`; keep user-interface policy like `--mount` plus `--isolation host` rejection in `rtm-cli`.
- Keep daemon behavior as protocol validation, not CLI syntax validation. The daemon already accepts host isolation mounts as a direct RPC warning path and validates Docker-only semantics only under Docker isolation.
- Preserve cwd auto-mount as daemon-owned behavior. Parser exposure should not infer mounts from path-shaped environment variables or alter Docker preflight ownership.

## Detailed Findings

### Current state

1. The parser exists but is not reusable by `session-matters` because `parse_mount_spec` and `expand_mount_source` are private functions in `crates/rtm-cli/src/cli/spawn.rs:91-139`.
2. `lilo-rm-core` already owns the right public data contract through `MountSpec` and `SpawnRequest.mounts` at `crates/rtm-core/src/types/spawn.rs:78-103`.
3. CLI rejection of `--mount` with host isolation is intentionally CLI-only at `crates/rtm-cli/src/cli/spawn.rs:84-89`; direct protocol behavior remains tolerant via `warn_host_mounts` at `crates/rtm-daemon/src/spawn_preflight.rs:113-121`.
4. Runtime daemon mount validation and cwd auto-mount behavior already satisfy the runtime requirements, with concentrated logic in `spawn_preflight.rs` and `docker_mount_plan.rs`.
5. Existing tests cover CLI malformed mount values, host-isolation rejection, `~` expansion, declaration order forwarding, JSON wire round trips, Docker argv emission, and daemon preflight mount behavior. Relevant outlines: `crates/rtm-cli/tests/cli_flags.rs`, `crates/rtm-cli/tests/spawn_target.rs`, `crates/rtm-core/tests/serde_snapshots.rs`, and `crates/rtm-daemon/src/spawn_preflight/tests/mounts.rs`.

### Recommended orchestration

Recommendation: **A, MoE Local Batch on a single branch** for the runtime-matters side.

Rationale: the runtime work can be split into three ordered, bounded items in one repo and one branch, each plausibly 5 to 30 minutes, with no need for a Linear master and worker tree. This matches `~/.mdx/workflows/moe-local-batch.md` criteria: named N changes, bounded independent or naturally ordered scope, single repo and branch, no Linear ticket, and quality review per item. The `session-matters` implementation is cross-repo consumer work and should follow after the exported parser contract lands.

### Proposed item list

1. **Core parser export**
   - Target: `crates/rtm-core/src/types/spawn.rs` or a small sibling module under `crates/rtm-core/src/`.
   - Scope: move parser and host `~` expansion into `lilo-rm-core`; expose a stable function that returns `MountSpec` or a typed parse error.
   - Acceptance: `lilo-rm-core` users can parse `HOST:CONTAINER[:ro|:rw]` without depending on `rtm-cli`; behavior matches current `rtm-cli` parser.

2. **rtm-cli reuse**
   - Target: `crates/rtm-cli/src/cli/spawn.rs`.
   - Scope: replace private parser implementation with the exported core parser; leave `reject_host_mounts` in CLI because it is command-line policy.
   - Acceptance: `rtm spawn --mount` help and behavior remain unchanged, including host-isolation rejection before daemon request.

3. **Regression tests and contract checks**
   - Targets: `crates/rtm-core` tests plus existing `rtm-cli` and daemon mount tests.
   - Scope: add focused parser tests in core, keep CLI malformed value and `~` expansion coverage, preserve daemon preflight tests.
   - Acceptance commands: `fmm validate`, `cargo test -p lilo-rm-core`, `cargo test -p rtm-cli --test cli_flags --test spawn_target`, and `cargo test -p rtm-daemon spawn_preflight`.

## Dependencies

- `lilo-rm-core`: public protocol and reusable contract surface.
- `rtm-cli`: Clap parsing and CLI-only policy gate for host isolation.
- `rtm-daemon`: Docker validation, cwd mount planning, path-shaped environment preflight, and host isolation warning behavior.
- `anyhow`, `clap`, `serde`, `uuid`, `tokio`: current workspace dependencies relevant to the existing CLI and protocol shape.

## Relevance to Helioy

This keeps `runtime-matters` as the source of truth for runtime mount grammar, while allowing `session-matters` to offer `sm run --mount` without cloning parser rules. It also preserves the existing Helioy boundary: `session-matters` handles intent and CLI surface, `runtime-matters` handles runtime protocol and execution semantics.

## Open Questions

- Peer consensus was not completed in this pass because no peer reply had arrived after three inbox checks. A sign-off should wait for the Claude peer response or an orchestrator decision to proceed without it.
- The exported parser error type shape still needs an implementation decision: simple string-compatible parser error for Clap reuse, or a typed error enum if external consumers need structured diagnostics.
