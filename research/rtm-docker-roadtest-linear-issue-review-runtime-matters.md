---
title: rtm Docker Road Test Linear Issue Review
type: research
tags: [runtime-matters, linear, alp-2643, docker, issue-review]
summary: Peer review of the ALP-2684 through ALP-2690 road-test correctives and ALP-2650 gate amendment found one gate ordering defect.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

The seven road-test worker issues are mostly selector ready and reference live paths on branch `nancy/ALP-2643`. The only blocker found in round 1 is in ALP-2650: the Required order line calls ALP-2687 independent even though ALP-2687 blocks ALP-2689 and ALP-2689's manual road test requires the `--image` flag introduced by ALP-2687.

## Project Metadata

- Project: runtime-matters
- Branch: `nancy/ALP-2643`
- Linear gate: ALP-2650
- Execution parent: ALP-2649 Backlog
- Reviewed workers: ALP-2684, ALP-2685, ALP-2686, ALP-2687, ALP-2688, ALP-2689, ALP-2690
- Review workflow: helioy-tools linear Agent Issue Review

## Architecture

The issue set repairs Docker isolation after a hands-on road test showed that fake Docker integration coverage missed substrate failures. The worker set spans Docker command construction, reference image correctness, preflight image metadata, per-spawn image selection, operator-facing language, environment passthrough, and a gated real-Docker E2E proof.

## Key Patterns

- Worker issues use stable file or directory entry points, not line-number anchors.
- ALP-2689 is the convergence test and is correctly blocked by ALP-2684, ALP-2685, ALP-2687, and ALP-2690 at the Linear relation layer.
- ALP-2650's `Execute:` line is the closed selector authorization surface and must agree with the dependency relations.

## Detailed Findings

### Path verification

All cited entry points exist in the live filesystem:

- `README.md`
- `CHANGELOG.md`
- `examples/dockerfiles/claude.Dockerfile`
- `crates/rtm-daemon/src/docker_runtime.rs`
- `crates/rtm-daemon/src/backend.rs`
- `crates/rtm-daemon/src/docker_preflight.rs`
- `crates/rtm-daemon/src/server.rs`
- `crates/rtm-daemon/src/spawn_preflight.rs`
- `crates/rtm-daemon/src/doctor.rs`
- `crates/rtm-daemon/src/shim_socket.rs`
- `crates/rtm-launchers/src/lib.rs`
- `crates/rtm-core/src/types.rs`
- `crates/rtm-core/src/admin.rs`
- `crates/rtm-core/src/cli_output.rs`
- `crates/rtm-cli/src/cli/`
- `crates/rtm-cli/tests/docker_documentation.rs`
- `crates/rtm-cli/tests/integration_pass5.rs`
- `crates/rtm-cli/tests/common/`
- `crates/rtm-cli/tests/common/docker.rs`
- `crates/rtm-cli/tests/snapshots/`
- `crates/rtm-core/tests/`

### Worker issue review

- ALP-2684: executable. It is focused on command resolution and blocks ALP-2689.
- ALP-2685: executable. It is focused on producing a working Claude runtime image and blocks ALP-2689.
- ALP-2686: executable. It is focused on arm64 local image preflight fallback.
- ALP-2687: executable. It introduces `rtm spawn --image` with `RTM_DOCKER_IMAGE` as fallback default. It correctly blocks ALP-2689 in Linear relations.
- ALP-2688: executable. A live grep confirms current operator surfaces still contain Pattern jargon, so the issue is grounded.
- ALP-2690: executable. It introduces explicit env passthrough and blocks ALP-2689.
- ALP-2689: mostly executable. The binding manual verification uses `--image` from ALP-2687 and `--env CLAUDE_CODE_OAUTH_TOKEN` from ALP-2690, and its observable checkpoints are adequate.

### Gate defect

ALP-2650 currently says `ALP-2686, ALP-2687, ALP-2688 are independent.` This contradicts:

- ALP-2687 `blocks` ALP-2689.
- ALP-2689 `blockedBy` includes ALP-2687.
- ALP-2689's binding manual command uses `rtm spawn --image runtime-matters-claude:local`, introduced by ALP-2687.

Required fix: amend ALP-2650 Required order to include `ALP-2687 before ALP-2689` and remove or narrow the statement that ALP-2687 is independent. Safe wording: `ALP-2686 and ALP-2688 are independent. ALP-2687 before ALP-2689.`

### Gate close binding

ALP-2650 binds ALP-2654 terminality clearly enough because it requires evidence attached to ALP-2689 before ALP-2654 can move to `Done`. The phrase that the gate itself cannot reach terminal state is awkward because ALP-2650 is already `Worker Done`, but it does not weaken the ALP-2654 binding.

## Dependencies

- ALP-2684 blocks ALP-2689.
- ALP-2685 blocks ALP-2689.
- ALP-2687 blocks ALP-2689.
- ALP-2690 blocks ALP-2689.
- ALP-2689 and all road-test correctives must complete before ALP-2654.

## Relevance to Helioy

The review protects Nancy selector correctness. Without the gate order fix, ALP-2689 could be considered independent of ALP-2687 in the accepted gate text even though both Linear relations and manual verification require ALP-2687 first.

## Open Questions

- Whether pane A finds additional issue body defects in round 1.
- Whether the orchestrator will patch only ALP-2650 Required order or also clarify the gate terminality wording.


## Round 2 Update

After pane A's round 1 review, pane B re-fetched ALP-2686, ALP-2689, ALP-2690, and ALP-2650. No edits had landed. Pane B accepted three additional required fixes and one optional coordination note.

Required changes now are:

1. ALP-2650 Required order must state `ALP-2687 before ALP-2689` and stop describing ALP-2687 as independent.
2. ALP-2690 must bind the env passthrough CLI shape to repeatable `--env KEY` for caller-environment passthrough and `--env KEY=VALUE` for explicit values. ALP-2689 and ALP-2650 already rely on that exact flag shape.
3. ALP-2686 must tighten missing-image acceptance so nonexistent local images return the image-unavailable preflight category, distinct from manifest or metadata unavailability. Current source already has `DockerImageUnavailable` and `DockerImageMetadataUnavailable` categories in `crates/rtm-daemon/src/error.rs`.
4. ALP-2689 must clarify whether its binding manual verification command is operator-host evidence using operator-provided `tmux:2:3.4` and `~/Dev/LLM/`, or a generic command shape where pane target and cwd are substitutable placeholders.

Recommended but not required: ALP-2650 should note that ALP-2685, ALP-2687, and ALP-2688 all touch README, and ALP-2685 plus ALP-2687 both touch `crates/rtm-cli/tests/docker_documentation.rs`, so workers should rebase and preserve sibling documentation assertions.


## Final Peer Consensus

Pane A accepted pane B's round 2 conditions and found no remaining substantive issues. Both panes reached clean consensus on the issue set after two rounds.

Final signoff phrase sent by pane B:

`I sign off on the rtm Docker road-test issue set as currently filed`

Consensus amendments to apply or preserve:

1. ALP-2650 Required order: add `ALP-2687 before ALP-2689` and narrow the independent statement to ALP-2686 and ALP-2688 only.
2. ALP-2690 flag shape: bind repeatable `--env KEY` for caller-env passthrough and `--env KEY=VALUE` for explicit values. Remove latitude for a different flag name.
3. ALP-2686 missing-image path: require the image-unavailable preflight category, distinct from metadata or manifest unavailability.
4. ALP-2689 Binding manual verification: clarify whether the command is one-shot operator-host evidence with the given target and cwd, or replace target and cwd with substitutable placeholders.
5. Recommended not required: ALP-2650 note about README overlap across ALP-2685, ALP-2687, ALP-2688 and `docker_documentation.rs` overlap across ALP-2685 and ALP-2687.


## Final Re-verification After Linear Edits

After orchestrator edits, pane B re-read ALP-2650, ALP-2686, ALP-2689, and ALP-2690 from current Linear state. All consensus amendments were applied:

1. ALP-2650 Required order includes `ALP-2687 before ALP-2689` and narrows independence to ALP-2686 and ALP-2688.
2. ALP-2650 Gate close binding binds ALP-2654 terminality and references the `--env KEY` form from ALP-2690.
3. ALP-2650 includes the coordination note for README and `docker_documentation.rs` overlap.
4. ALP-2686 requires nonexistent local images to return typed `DockerImageUnavailable`, distinct from `DockerImageMetadataUnavailable`, with explicit error-category assertions.
5. ALP-2689 describes binding manual verification as one-shot operator-host evidence with literal flag shapes binding and `<TMUX_TARGET>` / `<HOST_CWD>` operator-substitutable.
6. ALP-2690 binds repeatable `--env KEY` and `--env KEY=VALUE`, including missing caller env preflight behavior and regression coverage for both forms.

Final signoff phrase sent by pane B after live re-read:

`I sign off on the rtm Docker road-test issue set as currently filed`
