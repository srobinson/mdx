---
title: RTM Docker road-test issue review pass 4
type: research
tags: [runtime-matters, linear, docker, issue-review, nancy]
summary: Pass-4 live re-review signed off clean after Linear applied the three consensus edits and added ALP-2692 as a types.rs decomposition precondition.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

Reviewed the current Linear state for the ALP-2643 Docker road-test corrective wave under execution parent ALP-2649. Round 1 initially found no blockers, then peer review surfaced three valid conditional sign-off items: lowercase manual session IDs for Docker container observation, two missing coordination note co-touch entries, and an explicit parent closure trigger.

## Project Metadata

- Project: runtime-matters
- Branch: `nancy/ALP-2643`
- Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/runtime-matters-worktrees/nancy-ALP-2643`
- Build system: Rust workspace with `just check && just build && just test` as the standard gate
- fmm: `.fmm.db` exists in the worktree
- Linear scope: ALP-2643 master, ALP-2649 execution parent, ALP-2650 accepted gate

## Architecture

The reviewed work concerns Docker isolation in runtime-matters. Relevant source seams verified through fmm and filesystem checks include:

- `crates/rtm-daemon/src/docker_runtime.rs`: Docker run argv, container naming, env argument forwarding, kill, and liveness helpers.
- `crates/rtm-daemon/src/docker_preflight.rs`: Docker image configuration and metadata preflight.
- `crates/rtm-daemon/src/spawn_preflight.rs`: spawn entry preflight guardrails.
- `crates/rtm-cli/src/cli/mod.rs`: CLI spawn command entry point.
- `crates/rtm-core/src/types.rs`: spawn request types.
- `crates/rtm-launchers/src/lib.rs`: launch env composition.
- `README.md`, `CHANGELOG.md`, `examples/dockerfiles/claude.Dockerfile`, and `crates/rtm-cli/tests/docker_documentation.rs`: operator documentation and contract tests.

## Key Patterns

- Linear is treated as the source of truth. The review fetched live issues and relations for ALP-2684 through ALP-2691 plus ALP-2650, ALP-2649, and ALP-2643.
- The accepted gate uses a closed `Execute:` set and structural `blockedBy` relations for execution order.
- The corrective wave uses a successor post execution review, ALP-2691, instead of reusing terminal ALP-2654.
- Manual verification is bound to ALP-2689 and terminal review is bound to ALP-2691.

## Detailed Findings

### Linear state reviewed

Fetched from Linear with relations:

- ALP-2684: Resolve Docker spawn command without injecting host launcher path.
- ALP-2685: Reference Dockerfile produces a working runtime image.
- ALP-2686: arm64 preflight accepts local-only images.
- ALP-2687: `rtm spawn --image` flag, with `RTM_DOCKER_IMAGE` fallback default.
- ALP-2688: Remove internal Pattern jargon from operator-facing surfaces.
- ALP-2689: Real-Docker end-to-end integration test.
- ALP-2690: `rtm spawn` env passthrough for runtime process.
- ALP-2691: Post execution review for the ALP-2643 road-test correctives.
- ALP-2650: Gate review and execution readiness.
- ALP-2649: Backlog execution parent.
- ALP-2643: master parent.

Comments were fetched for ALP-2684 through ALP-2691 and ALP-2650. The worker and PER issues had no comments. ALP-2650 comments were historical provenance only.

### Inter-issue consistency

The current dependency graph matches the gate order:

- ALP-2684, ALP-2685, ALP-2686, ALP-2687, and ALP-2690 block ALP-2689.
- ALP-2688 and ALP-2689 block ALP-2691.
- ALP-2688 remains independent of ALP-2689 while still blocking the post execution review.

ALP-2650's gate close binding explicitly prevents ALP-2643 from reaching `Done` until ALP-2691 reaches `Done`, with ALP-2689 manual evidence attached.

### ALP-2689 manual verification audit

The manual sequence relies only on surfaces introduced by the corrective wave:

- `--image runtime-matters-claude:local` from ALP-2687.
- `--env CLAUDE_CODE_OAUTH_TOKEN` from ALP-2690.
- local image support from ALP-2686.
- container resolvable command and working image from ALP-2684 and ALP-2685.

The container name expectation was checked against `crates/rtm-daemon/src/docker_runtime.rs:container_name`, which formats names as `rtm-<session_id>`. That matches ALP-2689's `CONTAINER="rtm-$SESSION_ID"` checkpoint.

### Path and size verification

All cited paths checked locally on `nancy/ALP-2643` exist. Major cited file sizes checked with `wc -l`:

- `crates/rtm-core/src/types.rs`: 693 lines.
- `crates/rtm-daemon/src/server.rs`: 649 lines.
- `crates/rtm-core/src/cli_output.rs`: 389 lines.
- `crates/rtm-daemon/src/docker_runtime.rs`: 326 lines.
- `crates/rtm-daemon/src/shim_socket.rs`: 319 lines.
- `crates/rtm-daemon/src/error.rs`: 288 lines.
- `crates/rtm-daemon/src/docker_preflight.rs`: 235 lines.
- `crates/rtm-core/src/admin.rs`: 228 lines.
- `crates/rtm-daemon/src/spawn_preflight.rs`: 155 lines.
- `crates/rtm-daemon/src/doctor.rs`: 146 lines.
- `crates/rtm-launchers/src/lib.rs`: 108 lines.
- `crates/rtm-cli/tests/docker_documentation.rs`: 92 lines.

No checked cited source file exceeds the 700 line threshold before the workers run. `crates/rtm-core/src/types.rs` is close enough that workers touching it should remain careful.

## Dependencies

Critical code and tool dependencies surfaced by the review:

- Docker CLI and Docker daemon for ALP-2689 real E2E and manual verification.
- `just check && just build && just test` as the repository verification gate.
- fmm structural index for source shape and symbol checks.
- Linear relations for execution ordering and selector compatibility.

## Relevance to Helioy

This review reinforces the Helioy Nancy workflow requirement that gate prose, Linear relations, and post execution review terminality all agree before autonomous execution. It also validates the current selector compatible shape for a corrective wave appended to an already reviewed execution chain.

## Round 2 Consensus Update

After pane A replied, I rechecked live ALP-2689, live ALP-2650, local `uuidgen`, and `crates/rtm-daemon/src/docker_runtime.rs:container_name`. I retracted the clean sign-off and aligned with conditional sign-off on three changes:

1. ALP-2689 Binding manual verification should use `SESSION_ID="$(uuidgen | tr '[:upper:]' '[:lower:]')"` so `CONTAINER="rtm-$SESSION_ID"` matches daemon container naming on macOS and Linux.
2. ALP-2650 Coordination note should add `crates/rtm-daemon/src/docker_preflight.rs` for ALP-2686 and ALP-2687, plus `crates/rtm-daemon/src/spawn_preflight.rs` for ALP-2686 and ALP-2688.
3. ALP-2650 Gate close binding should state the explicit manual closure trigger for ALP-2649, ALP-2650, and ALP-2643 after ALP-2691 reaches `Done`.

## Consensus Result

Round 2 reached peer consensus. Both panes signed off conditional on the same three edits: lowercase ALP-2689 manual `SESSION_ID`, add the two ALP-2650 coordination note co-touch entries, and make the ALP-2650 parent closure trigger explicit. The issue set has no further blockers from pane B after those edits land.


## Final Re-verification After Orchestrator Edits

After the orchestrator applied the pass-4 consensus blockers, I re-read ALP-2689, ALP-2650, ALP-2691, ALP-2687, ALP-2690, and new ALP-2692 from live Linear state. I sent the clean sign-off phrase: `I sign off on the rtm Docker road-test issue set pass-4 as currently filed`.

Verified final state:

1. ALP-2689 lowercases `SESSION_ID` with `uuidgen | tr '[:upper:]' '[:lower:]'` and explains the macOS uuidgen versus Rust `Uuid::Display` mismatch.
2. ALP-2650 includes the missing co-touch entries for `crates/rtm-daemon/src/docker_preflight.rs` and `crates/rtm-daemon/src/spawn_preflight.rs`.
3. ALP-2650 states the explicit closure trigger from ALP-2691 `Done` through ALP-2649, ALP-2650, and ALP-2643.
4. ALP-2692 is in the Execute list, blocks ALP-2687 and ALP-2690, and blocks ALP-2691. ALP-2687 and ALP-2690 both show `blockedBy: ALP-2692`.
5. ALP-2691 includes ALP-2692 review criteria, the full transitive blocker set, and a cross-wave file-cap invariant.
6. ALP-2692 cited paths exist locally. fmm reports `crates/rtm-core/src/types.rs` at 693 LOC with visible seams for a one-session precondition refactor.

## Open Questions

None. Pass-4 is clean after the applied edits and ALP-2692 incorporation.
