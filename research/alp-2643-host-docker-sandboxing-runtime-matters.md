---
title: ALP-2643 Host and Docker Sandboxing Design
type: research
tags: [runtime-matters, alp-2643, sandboxing, docker, linear-planning]
summary: Peer reviewed v3 split for runtime-matters host and Docker sandboxed spawn execution, preserving Pattern A Docker tmux support and image policy while splitting Docker work into one-session workers.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

ALP-2643 introduces sandboxing as spawn isolation policy while preserving the existing runtime and target contracts. The final v3 design keeps W1, W2, and PER from v1, splits the former oversized W3 into six one-session workers, and binds Docker tmux to Pattern A: host tmux, host-side shim, detached Docker container, and host-side attach.

## Project Metadata

- Project: `runtime-matters`
- Repository path: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/runtime-matters`
- Language: Rust, workspace edition 2024
- Rust version: 1.90 from workspace metadata
- Build system: Cargo workspace plus `justfile`
- Mandatory execution gate for changes: `just check && just build && just test`
- Indexed with fmm: `.fmm.db` present in repository root
- Linear master: ALP-2643
- Execution parent: ALP-2649
- Gate review: ALP-2650
- Workers: ALP-2651, ALP-2652, W3a, W3b1, W3b2, W3c, W3d, W3e
- Post execution review: ALP-2654

## Architecture Findings

Current spawn flow is already close to the desired separation:

- Spawn contract lives in `crates/rtm-core/src/types.rs`. `SpawnRequest` currently carries session id, runtime, env, cwd, target, force, and shell resume.
- Target identity lives in `SpawnTarget` in `crates/rtm-core/src/types.rs`. It currently distinguishes tmux and headless targets.
- Runtime command composition is owned by the launcher contract. `RuntimeLauncher::launch_spec` composes argv, env, cwd, and shell resume in `crates/rtm-core/src/launcher.rs`.
- Launcher selection by runtime kind is in `rtm_launchers::dispatch` at `crates/rtm-launchers/src/lib.rs`.
- Daemon spawn handling currently composes the launch spec and launches the shim in `crates/rtm-daemon/src/handler.rs` in the `RuntimeRpc::Spawn` branch.
- Existing preflight checks happen before lifecycle insertion in `crates/rtm-daemon/src/spawn_preflight.rs`.
- Shim placement is currently selected by `SpawnTarget` in `crates/rtm-daemon/src/shim_socket.rs`.
- Lifecycle normalization remains in `ServerState`, store, events, and reconcile.

## Key Patterns

- Do not model sandboxing as a new `RuntimeKind`.
- Do not model sandboxing as a new `SpawnTarget`.
- Model sandboxing as isolation policy on `SpawnRequest`, defaulting to host.
- Keep launchers as command composers only. They should not import backend or Docker details.
- Keep backends as daemon placement mechanisms. They should not import launcher specific details.
- Keep lifecycle normalization shared in the existing daemon server, store, event, and reconcile path.
- Use policy, profile, or config language for Docker controls so W1 remains minimal: discriminator plus optional named profile.

## Detailed Findings

### Standing v1 resolutions

1. Backend seam shape: introduce one daemon owned execution backend seam for placement. Composer and lifecycle normalization already exist as separate concerns.
2. Isolation policy versus implementation: isolation is caller policy; backend is daemon implementation.
3. Isolation home: isolation is a separate policy object on `SpawnRequest`, defaulting to host.
4. Policy minimality: W1 ships only a discriminator plus optional named profile.
5. Validation seam: validate isolation at spawn entry preflight. Do not add a new validation RPC.
6. Docker shim placement: the shim stays host side and wraps Docker placement. No shim inside the container and no daemon socket mounted into the container.

### V2 Docker tmux and image policy resolutions

1. Docker target compatibility: Docker v1 supports headless and tmux. Tmux uses Pattern A. Host tmux remains the visible developer surface; the shim runs host side; the backend starts a detached Docker container; the host pane attaches to the container runtime stdio through Docker.
2. Pattern E unsupported: in-container tmux as the primary runtime multiplexer is unsupported and rejected when explicitly requested through policy, profile, or config. No heuristic image entrypoint inspection is binding.
3. Pattern D deferred: reconnecting PTY server plus thin host client is a future initiative.
4. Docker runtime pid and liveness: Docker-backed liveness uses Docker inspection or equivalent Docker API state. Typed runtime handles are deferred.
5. Lifecycle reconcile identity: Docker-backed lifecycle rows persist enough backend or isolation identity for reconcile to dispatch correctly, with host as the compatibility default for existing rows.
6. Init behavior: Docker init behavior is mandatory unless the image declares an accepted own init policy through profile or config.
7. Base image policy: rtm stays image agnostic, ships documented Dockerfile examples, and softly recommends `mcr.microsoft.com/devcontainers/base:ubuntu` as a starter base. rtm does not publish branded base images in this initiative.
8. Workspace mount: `/workspace` is the canonical default. Operator override belongs in profile or config.
9. Git and shell: starter Dockerfile examples include or inherit `git`. Interactive images must provide `/bin/sh`; `/bin/bash` is recommended where practical.
10. Credential policy: v1 does not automatically mount host credential directories. Operator credential pass-through is explicit via profile or config examples. Named credential volume management is deferred.
11. Firewall capabilities: Docker default capabilities are retained in v1. Privileged Docker execution is rejected. Capability modifications are opt in via profile or config. Aggressive capability dropping is deferred.
12. Arm64 validation: known absent arm64 image manifests fail pre-insert by default. Manifest inspection that is unreachable or authentication inaccessible also fails pre-insert by default. Operators may use an explicit escape hatch for emulation or private registry cases.
13. Non-root enforcement: Docker spawn refuses images that run as root unless profile or config explicitly allows root. Missing image user metadata is treated as root.
14. Manual detach behavior: manual detach via Docker default detach keys is disabled for Pattern A pane attach. Pane close terminates attach; container survives. Wrapped rtm re-attach is deferred.
15. Future sidecar: no credential helper, telemetry agent, reconnecting PTY server, or in-container rtm sidecar ships in ALP-2643.
16. Discouraged starters: distroless and Alpine/musl are discouraged starter images in documentation for interactive coding agents.

### Worker breakdown

#### ALP-2651: Carry isolation policy through the spawn contract

Unchanged from v1. Scope is minimal isolation policy on `SpawnRequest`, host default, existing runtime and target semantics preserved, unsupported explicit Docker rejected at spawn preflight until W3 enables Docker behavior.

Entry points:
- `crates/rtm-core/src/types.rs`
- `crates/rtm-core/src/proto.rs`
- `crates/rtm-client/src/lib.rs`
- `crates/rtm-cli/src/cli/mod.rs`
- `crates/rtm-daemon/src/spawn_preflight.rs`
- `crates/rtm-core/tests/serde_snapshots.rs`
- `crates/rtm-core/tests/wire_compat.rs`

#### ALP-2652: Preserve host spawn through an execution backend seam

Unchanged from v1. Scope is routing current host headless and tmux placement through a daemon owned backend seam without observable behavior regression.

Entry points:
- `crates/rtm-daemon/src/handler.rs`
- `crates/rtm-daemon/src/server.rs`
- `crates/rtm-daemon/src/shim_socket.rs`
- `crates/rtm-daemon/src/reconcile.rs`
- `crates/rtm-core/src/launcher.rs`
- `crates/rtm-launchers/src/lib.rs`
- `crates/rtm-launchers/tests/conformance.rs`
- `crates/rtm-cli/tests`

#### W3a: Persist Docker lifecycle identity for backend-aware reconcile

Scope:
- Persist enough backend or isolation identity in lifecycle rows for reconcile dispatch.
- Preserve host as the compatibility default for existing rows.
- Make Docker reconcile dispatch testable through a fake or mocked Docker state path without live Docker.

Entry points:
- `crates/rtm-core/src/types.rs`
- `crates/rtm-core/src/proto.rs`
- `crates/rtm-store`
- `crates/rtm-daemon/src/server.rs`
- `crates/rtm-daemon/src/reconcile.rs`
- `crates/rtm-core/tests/serde_snapshots.rs`
- `crates/rtm-core/tests/wire_compat.rs`

#### W3b1: Enforce Docker policy and profile preflight guardrails

Scope:
- Add preflight guardrails for policy, profile, and config inputs that do not require image metadata inspection.
- Reject explicit Pattern E requests, privileged execution, unsupported Docker profile inputs, and Docker daemon unavailable before lifecycle insert.
- Keep image user, architecture, manifest, registry, and metadata validation out of this worker.

Entry points:
- `crates/rtm-daemon/src/spawn_preflight.rs`
- `crates/rtm-daemon/src/handler.rs`
- `crates/rtm-core/src/types.rs`
- `crates/rtm-daemon/src/error.rs`

#### W3b2: Validate Docker image metadata at preflight

Scope:
- Validate Docker image metadata before Docker-backed lifecycle insertion.
- Enforce non-root by default.
- Enforce arm64 manifest safety by failing known absent, unreachable, or auth-inaccessible manifest checks by default unless an explicit escape hatch is active.
- Make image metadata validation testable without a live Docker daemon or registry.

Entry points:
- `crates/rtm-daemon/src/spawn_preflight.rs`
- `crates/rtm-daemon/src/handler.rs`
- `crates/rtm-core/src/types.rs`
- `crates/rtm-daemon/src/error.rs`

#### W3c: Add Docker headless execution backend

Scope:
- Enable Docker isolation for headless spawns through the daemon backend seam.
- Prove Docker-backed logs, terminal observation, kill, terminal exit detection, liveness, and cleanup.
- Populate the Docker lifecycle runtime pid from a host-visible Docker process PID and keep typed runtime handles deferred.
- Keep launchers free of Docker details.

Entry points:
- `crates/rtm-daemon/src/handler.rs`
- `crates/rtm-daemon/src/shim_socket.rs`
- `crates/rtm-daemon/src/server.rs`
- `crates/rtm-daemon/src/reconcile.rs`
- `crates/rtm-core/src/launcher.rs`
- `crates/rtm-core/src/types.rs`

#### W3d: Add Docker tmux Pattern A execution

Scope:
- Enable Docker isolation for tmux spawns through Pattern A.
- Preserve host tmux as the visible developer surface.
- Disable manual Docker detach key behavior for the Pattern A pane attach.
- Preserve host tmux behavior and keep Pattern D plus in-container sidecars out of scope.

Entry points:
- `crates/rtm-daemon/src/handler.rs`
- `crates/rtm-daemon/src/shim_socket.rs`
- `crates/rtm-daemon/src/server.rs`
- `crates/rtm-daemon/src/spawn_preflight.rs`
- `crates/rtm-platform/src/tmux.rs`

#### W3e: Document Docker isolation and surface operator readiness

Scope:
- Document Docker isolation and expose operator diagnostics.
- Recommended v1 Dockerfile authorship path is docs-only. README gives copy-pasteable recipes and vendor-image guidance, but no tracked `examples/dockerfiles/` directory.
- If Stuart chooses in-repo examples, add `examples/dockerfiles/` and validate them. If Stuart chooses vendor-only guidance, keep vendor-image links and remove copy-paste recipes.
- Update doctor or equivalent diagnostics, README, and CHANGELOG without changing runtime behavior.

Entry points:
- `crates/rtm-daemon/src/doctor.rs`
- `crates/rtm-cli/src/cli/doctor.rs`
- `README.md`
- `CHANGELOG.md`
- optional `examples/dockerfiles/` if Stuart chooses in-repo examples

#### ALP-2654: Post execution review

Unchanged from v1. Review host contract preservation, isolation policy placement, launcher/backend/lifecycle boundaries, Docker scope, Pattern A tmux behavior, Docker headless behavior, lifecycle and reconcile correctness, doctor/docs accuracy, and exclusion of K8s/SandboxClaim plus daemon/shim drift work.

## Dependencies

Execution order:

1. ALP-2651 before ALP-2652.
2. ALP-2652 before ALP-2653.
3. W3a before W3b1.
4. W3b1 before W3b2.
5. W3b2 before W3c.
6. W3c before W3d.
7. W3d before W3e.
8. W3e before ALP-2654.

Gate closure:

`Execute: ALP-2651, ALP-2652, W3a, W3b1, W3b2, W3c, W3d, W3e, ALP-2654.`

## Relevance to Helioy

This design keeps runtime-matters as a stable per host execution substrate for Helioy agents while adding a bounded path toward sandboxed execution. It preserves the caller-facing spawn model, supports the daily-driver tmux case, and contains Docker semantics inside daemon placement and profile/config policy.

## Open Questions

- Exact Rust type names for isolation policy, Docker profile/config, backend seam, and lifecycle backend identity are intentionally left to implementation.
- Pattern D reconnecting PTY support is a future initiative.
- K8s and SandboxClaim remain out of scope under ALP-2648.
- Credential volume management, first class firewall UX, aggressive capability hardening, rtm re-attach UX, and rtm injected sidecars are deferred.
