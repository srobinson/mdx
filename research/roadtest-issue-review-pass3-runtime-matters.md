---
title: Runtime Matters road-test issue review pass 3
type: research
tags: [runtime-matters, linear, docker, issue-review, alp-2643]
summary: Fresh pass-3 review found conditional changes in ALP-2685, ALP-2689, and ALP-2691 before the road-test issue set is clean.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

Reviewed the current Linear state for ALP-2684 through ALP-2691 and ALP-2650 against the Nancy issue rules, gate binding, and live branch paths on `nancy/ALP-2643`. The set is close, but pass 3 should not sign off cleanly yet because ALP-2685 omits the required build gate, ALP-2689's binding manual command is not safely copy-pasteable, and ALP-2691 does not fully mirror several corrective acceptances.

## Project Metadata

- Language: Rust workspace.
- Build system: `just` wrapper over Rust checks, builds, and tests.
- Branch reviewed: `nancy/ALP-2643`.
- fmm index: available, 106 indexed files, 17,322 LOC under `crates/`.
- Relevant modules confirmed present on branch:
  - `crates/rtm-daemon/src/docker_runtime.rs`
  - `crates/rtm-daemon/src/docker_preflight.rs`
  - `crates/rtm-daemon/src/spawn_preflight.rs`
  - `crates/rtm-daemon/src/error.rs`
  - `crates/rtm-cli/src/cli/`
  - `crates/rtm-core/src/types.rs`
  - `examples/dockerfiles/claude.Dockerfile`
  - `crates/rtm-cli/tests/docker_documentation.rs`

## Architecture

The corrective wave sits under master ALP-2643 with gate ALP-2650 and execution parent ALP-2649. Docker behavior spans CLI spawn parsing, core spawn request serialization, daemon preflight, daemon Docker runtime placement, launch environment composition, and documentation or snapshot surfaces.

Dependency review from live Linear:

- ALP-2684, ALP-2685, ALP-2686, ALP-2687, and ALP-2690 block ALP-2689.
- ALP-2689 blocks ALP-2691.
- ALP-2688 is independent of ALP-2689 but listed before ALP-2691 in the gate prose.
- ALP-2650 `Execute:` includes the original completed chain and the corrective wave through ALP-2691.

## Key Patterns

- Linear is the planning source of truth. All reviewed issues were fetched live with relations.
- Worker issues should encode capability and observable acceptance, not implementation body details.
- Gate close binding must point to a non-terminal post execution review target. ALP-2650 now binds ALP-2691, while ALP-2654 is already `Done`.
- Manual verification snippets must be literal enough for a worker to execute without shell ambiguity.

## Detailed Findings

### 1. ALP-2685 misses the mandatory build gate

ALP-2685 verification currently says `just check && just test`, while this repo's invariant and the other workers use `just check && just build && just test`. This is an execution readiness defect because a Dockerfile or documentation worker can still break the binary build while passing check and tests in some configurations.

Required change: update ALP-2685 verification to include `just build` in the full gate.

### 2. ALP-2689 binding manual verification is not safely copy-pasteable

The ALP-2689 command block uses angle placeholders directly in shell arguments:

- `--target tmux:<TMUX_TARGET>`
- `--cwd <HOST_CWD>`

The issue text says the values are operator-substitutable, but the review brief explicitly asks whether the literal command can be executed as written. The current block is unsafe because `<HOST_CWD>` is shell redirection syntax if copied literally, and the target or cwd values are not quoted. The expected end state also references `docker exec <container> ps -ef` without giving a concrete way to derive the container variable.

Required change: bind variables before the command and use quoted expansions, for example `TMUX_TARGET=...`, `HOST_CWD=...`, `CONTAINER=...`, then `--target "tmux:$TMUX_TARGET"`, `--cwd "$HOST_CWD"`, and `docker exec "$CONTAINER" ps -ef`.

### 3. ALP-2691 review criteria do not fully mirror the worker acceptances

ALP-2691 is the gate close binding target, so it must cover every acceptance that proves the corrective wave is done. Current criteria omit or compress several checks:

- ALP-2687: review criteria cover OCI reference forms, env fallback, missing image category, and isolation namespace, but omit the README recommended `--image` example and `docker_documentation.rs` assertion required by ALP-2687.
- ALP-2690: review criteria cover env forms, duplicate, empty, and docker inspect, but omit the missing `--env KEY` typed preflight error and host isolation propagation required by ALP-2690.
- ALP-2686: review criteria should explicitly include the nonexistent local image path returning `DockerImageUnavailable`, separate from registry metadata failures, not only category separability.

Required change: expand ALP-2691 review criteria so each corrective's unique acceptance is explicitly reviewed before ALP-2691 can move to `Done`.

## Dependencies

Critical dependencies and surfaces:

- `clap`: CLI flag contract for `rtm spawn`.
- `serde`: wire shape and snapshot stability for `SpawnRequest` and admin diagnostics.
- Docker CLI and daemon: real Docker E2E and manual binding verification.
- tmux: manual Docker tmux attach verification.
- Linear relations: selector authority and gate close binding.

## Relevance to Helioy

The review reinforces Helioy's Nancy execution contract: accepted gates must enumerate authorized work, worker verification must include the full repo gate, and post execution reviews must be terminal proof targets rather than broad summaries. The ALP-2689 placeholder issue is a reusable pattern: operator manuals should avoid angle placeholder syntax inside shell blocks unless the line cannot be copied.

## Open Questions

- Whether pane A finds additional state drift in comments or older worker relations not covered here.
- Whether the gate should encode ALP-2688 before ALP-2691 structurally, or whether prose order is sufficient for an independent surface cleanup.
