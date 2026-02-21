---
title: Docker Mount Structural Fix LOE for runtime-matters
type: research
tags: [runtime-matters, docker, mounts, claude, isolation, loe]
summary: Structural mount support for Docker isolation is Linear-scoped, while docs and optional log warnings are small enough for in-session work.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

The structural fix for `CLAUDE_CONFIG_DIR` Docker hangs requires a public mount declaration surface, Docker argv plumbing, preflight validation, and a spec decision about env value rewrite. The LOE consensus is hybrid: docs plus optional rtmd log warning are MoE-now; mount declarations plus validation are Linear-scoped.

## Project Metadata

- Language: Rust workspace.
- Build system: Cargo, `justfile`, `rust-toolchain.toml`.
- Relevant crates: `rtm-core`, `rtm-cli`, `rtm-daemon`, `rtm-client`, `rtm-launchers`.
- fmm status: `.fmm.db` present; `fmm validate` earlier in session reported 135 files indexed and current.
- Context: MoE peer consensus on 2026-05-23 under bus topic `claude-config-hang-loe`.

## Architecture

### Current spawn and Docker path

- `SpawnRequest` has no mount model today in `crates/rtm-core/src/types/spawn.rs:77-92`.
- `IsolationProfile` only carries `name: Option<String>` in `crates/rtm-core/src/isolation.rs:61-64`.
- CLI `rtm spawn` has `--env`, `--cwd`, `--image`, and no `--mount` flag in `crates/rtm-cli/src/cli/spawn.rs:14-36`.
- CLI request construction happens in `crates/rtm-cli/src/cli/spawn.rs:57-67`.
- Host and Docker env collection differ in `crates/rtm-cli/src/cli/spawn.rs:74-83`: host captures caller env, Docker starts empty, both layer explicit overrides.
- Docker argv construction has one hardcoded cwd bind mount and workdir in `crates/rtm-daemon/src/docker_argv.rs:66-83`.
- Docker env passthrough forwards every launch env as `--env KEY=VALUE` in `crates/rtm-daemon/src/docker_argv.rs:128-133`.
- Docker preflight is profile-name based, not mount-aware, in `crates/rtm-daemon/src/spawn_preflight.rs:69-102`.

## Key Patterns

- Docker isolation currently preserves a tight posture: no credential directory auto-mounting and no arbitrary host path inference.
- Explicit `--env` is caller intent, but filesystem path env values do not imply container mounts.
- The public protocol is small but high leverage. Adding a field to `SpawnRequest` is JSON-additive but still a public Rust API and capability change.
- Durable lifecycle state should stay separate from launch-only mount data. `SpawnedPayload`, lifecycle DB, and event log do not need mount fields for this fix.

## Detailed Findings

### LOE verdict

Consensus verdict: **(c) Hybrid**.

MoE-now scope:

- Extend docs with host-path env guidance.
- Optionally add a Docker-only `tracing::warn!` for known path-shaped Claude env keys with absolute values.
- Keep this warning log-only. Do not add `RuntimeEvent` or protocol warning fields.

Linear-scoped structural scope:

- Add a `MountSpec` public type.
- Add `SpawnRequest.mounts` with serde default and skip-empty behavior.
- Add a CLI flag such as `rtm spawn --mount SRC:DST[:ro]`.
- Emit Docker `--mount type=bind,src=...,dst=...[,readonly]` args.
- Add Docker preflight validation for mount sources, targets, collisions, and path-shaped env coverage.
- Add a protocol capability or protocol version update.
- Update Rust struct literal sites that construct `SpawnRequest`.
- Add core serde, CLI, daemon argv, preflight, integration, and opt-in Docker E2E tests.

### Gating design decision

The major design decision is env rewrite versus same-destination or target-path semantics.

A mount such as:

```bash
--mount /host/.claude:/home/rtm/.claude:ro
```

does not cover:

```bash
--env CLAUDE_CONFIG_DIR=/host/.claude
```

unless runtime-matters rewrites `CLAUDE_CONFIG_DIR` from the mount source prefix to the mount target prefix before passing it into the container. Without rewrite, users must set `CLAUDE_CONFIG_DIR` to the container target path, or mount the host path at the same path in the container.

Sizing depends on this choice:

- Same-destination or env-already-target-path v1: about 400 LOC across about 18 files.
- Source-to-target env rewrite v1: about 800 LOC across about 25 files.

The rewrite variant adds new policy and security surface: path canonicalization, prefix matching, overlapping mounts, target conflict resolution, and the list of env keys eligible for rewrite.

### Files likely touched

Core and protocol:

- `crates/rtm-core/src/types/spawn.rs`: add `MountSpec`, `SpawnRequest.mounts`, serde attributes, and possibly parse helpers. 60 to 140 LOC.
- `crates/rtm-core/src/lib.rs`: re-export mount type. 1 to 5 LOC.
- `crates/rtm-core/src/version.rs`: advertise mount-aware spawn with a capability or protocol bump. 10 to 25 LOC.

CLI:

- `crates/rtm-cli/src/cli/spawn.rs`: add `--mount`, parse `SRC:DST[:ro]`, attach mounts to `SpawnRequest`, and decide host-isolation CLI behavior. 50 to 100 LOC.
- `crates/rtm-cli/tests/cli_flags.rs`: help and invalid mount tests. 20 to 50 LOC.
- `crates/rtm-cli/tests/spawn_target.rs`: integration coverage for mount plus env. 50 to 100 LOC.
- `crates/rtm-cli/tests/docker_e2e.rs`: opt-in real Docker proof that mounted config path reaches runtime. 40 to 100 LOC.

Daemon:

- `crates/rtm-daemon/src/docker_argv.rs`: emit declared bind mounts and update argv tests. 60 to 120 LOC.
- `crates/rtm-daemon/src/docker_runtime.rs`: thread mounts into argv builder. 5 to 10 LOC.
- `crates/rtm-daemon/src/backend.rs`: pass request mounts into Docker launch preparation. 5 to 15 LOC.
- `crates/rtm-daemon/src/spawn_preflight.rs`: validate mount specs and path-shaped env coverage. 100 to 180 LOC.
- `crates/rtm-daemon/src/spawn_preflight/tests.rs`: 4 to 6 new preflight cases. 150 to 250 LOC.

Mechanical Rust struct literal fallout:

- `crates/rtm-client/tests/typed_helpers.rs`
- `crates/rtm-cli/examples/support/spawn.rs`
- `crates/rtm-cli/benches/spawn_latency.rs`
- `crates/rtm-daemon/src/backend.rs`
- `crates/rtm-daemon/src/docker_preflight.rs`
- `crates/rtm-daemon/src/shim_socket.rs`
- `crates/rtm-daemon/src/doctor.rs`
- `crates/rtm-launchers/src/lib.rs`
- `crates/rtm-launchers/tests/conformance.rs`
- `crates/rtm-cli/tests/spawn_target.rs`

Each is small, usually 1 to 5 LOC, unless a builder pattern is introduced.

Tests and snapshots:

- `crates/rtm-core/tests/serde_snapshots.rs`: explicit mount serde coverage. Existing no-mount snapshots need not change if `mounts` is `default` plus skip-empty.
- `crates/rtm-core/tests/wire_compat.rs`: only needs fixture changes if protocol fixtures are intentionally versioned. Old fixtures should remain readable if `mounts` defaults empty.
- CLI surface snapshots may change if help output is captured.

Docs:

- `PROJECT.md`: replace or clarify aspirational credential mount language with the actual CLI or protocol shape once designed.
- `README.md`: likely mention `--mount` only if the flag becomes supported directly.

### Protocol and schema impact

- `SpawnRequest.mounts` is additive in JSON but still a public API change.
- Rust callers with `SpawnRequest { ... }` literals need updates unless a builder/default migration is part of the work.
- A mount-aware spawn capability should be added in `crates/rtm-core/src/version.rs`.
- `SpawnedPayload` should not change.
- Durable event log should not change.
- On-disk lifecycle state should not change.
- Session-matters coordination is likely because it is a primary upstream consumer of `rtm-core`.

### Host isolation semantics

Host isolation does not need mounts because the spawned process already runs in the host filesystem namespace. Two viable semantics remain for the Linear spec:

- CLI rejects `--mount` with `--isolation host` before daemon, while direct RPC no-ops with a log warning.
- Both CLI and RPC accept host mounts as a no-op with a warning.

This is a small spec decision and does not change the LOE verdict.

## Dependencies

- Docker CLI mount syntax and bind mount semantics.
- Claude Code path-shaped environment variables, especially `CLAUDE_CONFIG_DIR`.
- `serde` compatibility for additive JSON fields.
- `rtm-core` public API consumed by upstream Helioy components.

## Relevance to Helioy

This work is a boundary-quality issue for Helioy agent execution. The correct design should make container filesystem boundaries explicit, preserve Docker isolation, and avoid silently mounting credentials or rewriting env paths without a declared policy.

## Open Questions

1. Should v1 require env values to already be container paths, or should the daemon rewrite host path env values to mount targets?
2. Should host isolation reject mount declarations, warn and no-op, or split CLI and RPC behavior?
3. Should the path-shaped Claude env key list live in `rtm-daemon` as runtime policy, or in `rtm-core` as public protocol knowledge?
4. Should operator daemon config get a real mount profile mechanism, or should v1 be CLI and request only?
5. Should mount target collisions with the existing cwd self-mount reject or follow a documented precedence rule?
