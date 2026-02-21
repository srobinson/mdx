---
title: rtm mount review pass 2 for runtime matters
type: research
tags: [runtime-matters, linear-review, docker, e2e, helioy-bus]
summary: Cold MoE pass reached final clean sign-off after Linear fixes for Docker E2E opt-in and PER teardown.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

A cold read of the `rtm spawn --mount` Linear artifact found the selector shape structurally sound, with `ALP-2794` in `Worker Done` and `ALP-2785` containing only the authorized workers plus PER. Two substantive blockers remain: the Docker E2E verification can silently skip the E2E harness, and the PER manual reproduction lacks teardown for spawned runtime state.

## Project Metadata

- Language: Rust workspace.
- Build system: Cargo plus `just` recipes.
- Primary quality gate: `just check`, `just build`, `just test` per `PROJECT.md`.
- Source branch observed: `main`, clean against origin in the checked worktree.
- fmm index: available for the repo, 135 indexed files and 18,774 LOC.

## Architecture Context

`runtime-matters` owns the per host runtime substrate. The relevant flow for this review is:

1. `rtm-cli` parses spawn flags and sends a `SpawnRequest`.
2. `rtm-daemon` performs preflight and builds Docker argv.
3. The Docker backend launches either headless foreground containers or tmux attached containers.
4. The E2E harness in `crates/rtm-cli/tests/docker_e2e.rs` starts a temp daemon, builds dynamic Docker images, spawns a runtime, verifies container state, then tears down the session and daemon.

Live source evidence:

- Dynamic base image build exists at `crates/rtm-cli/tests/docker_e2e.rs:69-80` and uses `examples/dockerfiles/claude.Dockerfile`.
- Dynamic image tags are session scoped at `crates/rtm-cli/tests/docker_e2e.rs:304-309`.
- Docker E2E opt-in is required at `crates/rtm-cli/tests/docker_e2e.rs:14-18` and `48-50`.
- Harness teardown kills the runtime and stops the daemon at `crates/rtm-cli/tests/docker_e2e.rs:43-45` and `238-251`; container cleanup is also guarded at `334-338`.

## Key Patterns

- Selector compatibility depends on the accepted gate body, not child order. `ALP-2794` has the canonical `Outcome:`, `Authorized execution parent:`, `Execute:`, and `Required order:` lines.
- Docker E2E tests use an explicit environment opt-in. A cargo command that does not set `RTM_E2E_DOCKER=1` can pass while returning early.
- Manual Docker spawn verification must pair positive cases with explicit cleanup or use the existing harness conventions.

## Detailed Findings

### Structural audit, no blocker

Live Linear state checked:

- Master: `ALP-2784`.
- Execution parent: `ALP-2785`.
- Authorized gate: `ALP-2794`, status `Worker Done`.
- Workers: `ALP-2786`, `ALP-2787`, `ALP-2788`, `ALP-2789`, `ALP-2795`, `ALP-2790`, `ALP-2791`, `ALP-2792`.
- PER: `ALP-2793`.

The `Execute:` line in `ALP-2794` matches the Backlog children. `ALP-2785` has no extra open child outside that authorization set. The required order is consistent with the live `blockedBy` graph and no cycle was found. `ALP-2795`, the mid-review addition, is present in the gate body, live relations, PER mirroring, and `ALP-2790` dependency list.

### Finding 1: ALP-2791 verification can skip the Docker E2E

`ALP-2791` currently lists:

```bash
cargo test --workspace -- --include-ignored
```

The existing Docker E2E harness returns early unless `RTM_E2E_DOCKER=1` is set. The test is not merely ignored by the Rust harness. Source evidence:

- `real_docker_spawn_lifecycle_is_opt_in` returns before exercising Docker when `opted_in()` is false at `crates/rtm-cli/tests/docker_e2e.rs:14-18`.
- `opted_in()` requires `RTM_E2E_DOCKER=1` at `crates/rtm-cli/tests/docker_e2e.rs:48-50`.
- The requested dynamic image entry point exists at `crates/rtm-cli/tests/docker_e2e.rs:69-80` and builds from `examples/dockerfiles/claude.Dockerfile`.

This changes review behavior because the issue can pass its filed verification without testing the mount E2E at all. Suggested Linear change: make the verification explicit, for example:

```bash
RTM_E2E_DOCKER=1 cargo test -p rtm-cli --test docker_e2e -- --nocapture
```

Also state the Docker daemon precondition in the issue body.

### Finding 2: ALP-2793 manual reproduction lacks teardown

`ALP-2793` asks the reviewer to reproduce the original bug against `runtime-matters-claude:local`, including a positive spawn that renders Claude output. The acceptance and verification text do not require killing the spawned session, confirming the container is gone, or stopping a daemon started for the reproduction.

The existing harness shows the project convention:

- Kill runtime and wait for container absence at `crates/rtm-cli/tests/docker_e2e.rs:43-44`.
- Stop daemon and wait for socket removal at `crates/rtm-cli/tests/docker_e2e.rs:238-251`.
- Force remove the named container on drop at `crates/rtm-cli/tests/docker_e2e.rs:334-338`.

This changes review behavior because the PER can leave operator state dirty after a successful positive case. Suggested Linear change: add explicit teardown to the PER cross-worker acceptance and verification. At minimum, require `rtm kill` for the spawned session, a container absence check, and daemon stop when the reviewer starts a dedicated daemon for reproduction. Alternatively, route the reproduction through the Docker E2E harness.

## Dependencies

Critical dependencies and tools surfaced during the review:

- Docker CLI and daemon for `crates/rtm-cli/tests/docker_e2e.rs`.
- `RTM_E2E_DOCKER=1` environment opt-in for real Docker E2E execution.
- Cargo integration test binary path via `CARGO_BIN_EXE_rtm`, used by `RtmEnv.rtm_command` at `crates/rtm-cli/tests/docker_e2e.rs:205-212`.
- `examples/dockerfiles/claude.Dockerfile`, which the harness builds as the base image.

## Relevance to Helioy

This artifact gates a runtime protocol and CLI extension that will affect `session-matters` consumers. The main Helioy risk is false confidence: selector shape is ready, but E2E and PER verification must actually exercise Docker and must not leave local runtime state dirty on Stuart's macOS host.

## Peer Consensus Update

Peer pane `runtime-matters:helioy-tools:codebase-analyst:3:3.1` converged on both findings with no additional substantive blockers. Consensus conditional sign-off is:

1. `ALP-2791` verification must set `RTM_E2E_DOCKER=1` or use an equivalent command that exercises the Docker E2E harness body.
2. `ALP-2793` manual reproduction must include teardown, or route the reproduction through the existing harness guard pattern.

A convergence reply was sent to the peer and CC'd to orchestrator `runtime-matters:general:3:2.1` on bus topic `rtm-mount-review-pass2`.

## Final Sign-off Update

Orchestrator applied both consensus changes and requested final re-read through Linear MCP. Live Linear verification confirmed:

- `ALP-2791` now names the `RTM_E2E_DOCKER` opt-in guard, gates acceptance on it, and verifies with `RTM_E2E_DOCKER=1 cargo test -p rtm-cli --test docker_e2e -- --nocapture` plus a Docker daemon precondition.
- `ALP-2793` now includes a `Manual reproduction teardown` subsection requiring `rtm kill <session-id>`, container absence verification, and daemon stop when the daemon was started solely for reproduction. PER cannot mark cross-worker acceptance pass until teardown completes cleanly.
- `ALP-2794` remains `Worker Done`; the `Execute:` set remains `ALP-2786`, `ALP-2787`, `ALP-2788`, `ALP-2789`, `ALP-2795`, `ALP-2790`, `ALP-2791`, `ALP-2792`, `ALP-2793`; Backlog has no unauthorized extra child.

Final bus sign-off sent on topic `rtm-mount-review-pass2`:

`I sign off on the artifact as currently filed`

## Open Questions

None for this pass.
