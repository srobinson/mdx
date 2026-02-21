---
title: Docker bind mount options in runtime-matters
type: research
tags: [runtime-matters, docker, isolation, cli, helioy]
summary: Docker argv is built in rtm-daemon, profile suffixes are named switches only, and no current one line change lets callers pass arbitrary bind mounts.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

`runtime-matters` is a Rust workspace that runs local agent sessions through a daemon, CLI, launchers, and lifecycle store. The Docker path already has a fixed cwd bind mount, but no per spawn bind mount contract; the smallest experiment is a daemon env hook, while the correct product API is an `IsolationProfile` mount payload plus CLI syntax.

Full task deliverable: `~/.mdx/projects/rtm-mount-analysis--codex.md`.

## Project Metadata

- Language: Rust 2024 workspace with 8 crates and 135 fmm indexed files.
- Build system: Cargo workspace and `justfile`; root package metadata uses Rust 1.90 (Cargo.toml:1-22).
- Core dependencies: `clap`, `tokio`, `serde`, `serde_json`, `uuid`, `sqlx`, `tracing`, `anyhow`, `thiserror` (Cargo.toml:24-53).
- Relevant crates: `rtm-cli`, `rtm-core`, `rtm-daemon`, `rtm-launchers`, and `rtm-platform` (Cargo.toml:1-11).
- fmm status: `.fmm.db` exists and `fmm validate` reported all 135 files indexed and current.

## Architecture

Spawn handling starts in `RuntimeRpc::Spawn`: preflight, launcher dispatch, backend prepare, launch storage, backend spawn, and lifecycle recording (crates/rtm-daemon/src/handler.rs:103-138). Runtime launchers produce command, env, cwd, and shell resume into `LaunchSpec`; default cwd is the request cwd (crates/rtm-core/src/launcher.rs:64-92). The Docker backend wraps the launch by passing session id, Docker profile, image, launch spec, and target into Docker argv generation (crates/rtm-daemon/src/backend.rs:77-88).

Docker argv is assembled in `crates/rtm-daemon/src/docker_argv.rs`. `docker_run_base_argv` adds `docker run`, name, label, a fixed cwd bind mount, and workdir (crates/rtm-daemon/src/docker_argv.rs:66-89). `docker_run_argv` then adds `--init` unless profile is `own-init`, appends explicit env values, and finally pushes the image (crates/rtm-daemon/src/docker_argv.rs:48-64). Runtime command args are appended after the image (crates/rtm-daemon/src/docker_argv.rs:14-46).

## Key Patterns

- Docker isolation policy is the wire envelope. `IsolationPolicy` is serde tagged with `type` and `payload`; `Docker` carries `IsolationProfile` (crates/rtm-core/src/isolation.rs:7-13).
- Profile suffixes are currently named switches. `docker:PROFILE` only sets `IsolationProfile.name` (crates/rtm-core/src/isolation.rs:48-58).
- Unknown Docker profiles are rejected before lifecycle insert; accepted names are `default`, `own-init`, `allow-root`, and `arm64-manifest-escape` plus no name (crates/rtm-daemon/src/spawn_preflight.rs:69-102).
- Docker options must precede the image, since the image is pushed before runtime command args (crates/rtm-daemon/src/docker_argv.rs:56-63, crates/rtm-daemon/src/docker_argv.rs:32-33).

## Detailed Findings

### Current Docker mount surface

There is exactly one current bind mount in code: `--mount type=bind,src={cwd},dst={cwd}` (crates/rtm-daemon/src/docker_argv.rs:80-83). `SpawnRequest` has no mount field (crates/rtm-core/src/types/spawn.rs:77-92). `SpawnArgs` has no mount field; it exposes `--isolation host|docker[:PROFILE]`, `--image`, `--cwd`, and `--env` (crates/rtm-cli/src/cli/spawn.rs:14-36).

### Docker profile behavior

Plain `docker` parses as `Docker(IsolationProfile::default())`; `docker:foo` parses to `name: Some("foo")` (crates/rtm-core/src/isolation.rs:36-58). The only argv side effect is `own-init` suppressing `--init` (crates/rtm-daemon/src/docker_argv.rs:56-60). `allow-root` and `arm64-manifest-escape` are preflight escape hatches (crates/rtm-daemon/src/spawn_preflight.rs:150-161).

### No implemented profile mount config

`DaemonConfig` contains endpoint, shim path, log root, store, reconcile, and Docker preflight config (crates/rtm-daemon/src/server/config.rs:11-18). Docker preflight env has only image, root user allowance, and arm64 manifest allowance (crates/rtm-daemon/src/docker_preflight.rs:8-29). Docs show an example operator profile fragment with `mounts`, but no corresponding implementation exists in the core or daemon types (PROJECT.md:174-185, crates/rtm-core/src/isolation.rs:60-63, crates/rtm-core/src/types/spawn.rs:77-92).

### Recommended implementation shape

No correct one line patch lets a caller pass arbitrary `HOST:CONTAINER` mounts. The smallest experiment is a daemon env hook, such as `RTM_DOCKER_MOUNTS`, parsed in `docker_run_argv` before the image push (crates/rtm-daemon/src/docker_argv.rs:56-63). The durable product shape is to add a `mounts` payload to `IsolationProfile`, parse CLI `--mount` values into it, and render each as Docker `--mount` before the image (crates/rtm-core/src/isolation.rs:7-13, crates/rtm-cli/src/cli/spawn.rs:38-72, crates/rtm-daemon/src/docker_argv.rs:56-63).

## Dependencies

- `clap` provides CLI argument derive for `SpawnArgs` (crates/rtm-cli/src/cli/spawn.rs:14-36).
- `serde` shapes the `IsolationPolicy` and `SpawnRequest` wire contract (crates/rtm-core/src/isolation.rs:7-13, crates/rtm-core/src/types/spawn.rs:77-92).
- Docker CLI is invoked by argv construction and runtime liveness checks, with Docker binary discovery in `docker_runtime` (crates/rtm-daemon/src/docker_runtime.rs:12-37, crates/rtm-daemon/src/docker_runtime.rs:46-62).
- `uuid` ties Docker container names and lifecycle session ids together (crates/rtm-daemon/src/docker_argv.rs:7-12).

## Relevance to Helioy

The mount decision is a boundary decision for Helioy agent credential flow. A daemon env hook is useful for a private local experiment, but a per spawn profile payload preserves explicit caller control and avoids leaking credential mounts across every Docker spawn (PROJECT.md:174-177, crates/rtm-core/src/types/spawn.rs:77-92).

## Open Questions

1. Should runtime Docker workdir be the caller cwd path or `/workspace`? Code mounts cwd to cwd, while docs and doctor advertise `/workspace` (crates/rtm-daemon/src/docker_argv.rs:80-83, PROJECT.md:127-129, crates/rtm-daemon/src/doctor.rs:88-91).
2. Should credential mounts target `/home/rtm/.claude`, `/root/.claude`, or image declared home? The image contract requires non root by default (PROJECT.md:142-145).
3. Should mount parsing use Docker `--mount` only, or also support `-v` shorthand? Current code uses `--mount` for the cwd bind mount (crates/rtm-daemon/src/docker_argv.rs:80-83).
