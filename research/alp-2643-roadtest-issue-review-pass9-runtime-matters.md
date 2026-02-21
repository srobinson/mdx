---
title: ALP-2643 Road-Test Issue Review Pass 9
type: research
tags: [runtime-matters, linear, moe-review, docker, nancy]
summary: Pass 9 found three issue-specification defects; round-2 live re-read confirmed all were closed.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

Pass 9 reviewed the ALP-2643 road-test corrective Linear issue set, including ALP-2684 through ALP-2693 and ALP-2650. The issue graph, selector authorization, file paths, file-cap preconditions, and most PER mirroring were consistent, but peer consensus found three issue-specification defects: ALP-2689 daemon-state contention, ALP-2691 evidence ambiguity, and stale ALP-2689 blocker prose.

## Project Metadata

- Language: Rust workspace
- Project: `runtime-matters`
- Branch: `nancy/ALP-2643`
- Build gate referenced by issues: `just check && just build && just test`
- Structural index: `.fmm.db` present

## Architecture and Review Scope

- Master parent: `ALP-2643`
- Gate review: `ALP-2650`, status `Worker Done`
- Authorized execution parent: `ALP-2649`
- Corrective wave: `ALP-2684` through `ALP-2690`, plus precondition refactors `ALP-2692` and `ALP-2693`
- Post execution review: `ALP-2691`

Live Linear checks found:

- `ALP-2649` children match the `ALP-2650` Execute line.
- `ALP-2643` has only `ALP-2649` Backlog and `ALP-2650` gate as direct children.
- `Required order:` prose in `ALP-2650` matches live `blockedBy` relations for the reviewed corrective wave.
- `ALP-2691` criteria mirror worker acceptance surfaces and include both precondition refactors plus the cross-wave file-cap invariant.

## Detailed Findings

### Finding 1: ALP-2689 manual verification omits existing daemon-state guard

ALP-2689's binding manual verification starts `rtm daemon start` in the foreground, but does not state a precondition that no daemon is already running and does not provide a cleanup or isolation step before start.

Current source makes this unsafe as a copy-paste sequence:

- `crates/rtm-daemon/src/server.rs:81-84` computes the socket path, calls `socket::prepare_socket`, then binds the Unix listener.
- `crates/rtm-daemon/src/socket.rs:18-27` implements `prepare_socket` by creating the socket parent and calling `remove_socket_file`.
- `crates/rtm-daemon/src/socket.rs:29-35` removes the socket file if present.

If another `rtmd` is already running, the new foreground start can unlink the existing daemon's socket path before binding its own listener. The manual sequence can then prove the new daemon while leaving the previous daemon process dirty or unreachable, which violates the teardown discipline that ALP-2689 is meant to enforce.

Recommended issue change:

1. Add a copy-paste safe guard before `rtm daemon start`, for example run `rtm daemon status` and `rtm daemon stop` if already running.
2. Alternatively require an isolated RTM home or socket path for the manual verification sequence.
3. Mirror this requirement in ALP-2691's ALP-2689 review criteria so the PER checks the evidence.


### Finding 2: ALP-2691 evidence criterion is too ambiguous for PER-time verification

ALP-2691 says to confirm ALP-2689 binding manual verification evidence as a capture-pane snapshot or terminal recording attached to ALP-2689. ALP-2689 says the same artifact shape in Notes. The artifact type alone is insufficient because a pane snapshot can show a final terminal state without preserving each command's output or exit-status-meaningful assertions.

Recommended issue change:

1. Enumerate the evidence contents the reviewer must see: binding-sequence commands with visible output, container presence assertion exiting zero with the container name printed, `docker top "$CONTAINER"` showing the claude process running as a non-root image user, the negated post-kill absence assertion exiting zero, and post-stop `rtm daemon status` confirming the socket is gone.
2. Prefer transcript-shaped evidence, such as `script(1)` output or a full `tmux capture-pane -p` after the sequence completes.
3. Mirror the same enumeration into ALP-2689 if symmetry is preferred.

### Finding 3: ALP-2689 Notes blocker enumeration is stale

ALP-2689 Notes says the issue is blocked by five issues: ALP-2684, ALP-2685, ALP-2686, ALP-2687, and ALP-2690. The live `blockedBy` graph has six entries because ALP-2693 also blocks ALP-2689. ALP-2693 is the harness decomposition precondition for `crates/rtm-cli/tests/common/`, which ALP-2689 names as an entry point.

Recommended issue change: update ALP-2689 Notes to add ALP-2693 and change "all five" to "all six" so dependency prose tracks the live Linear graph.

## File and Path Verification

All cited issue entry-point paths checked during the review existed on `nancy/ALP-2643`, including:

- `crates/rtm-daemon/src/docker_runtime.rs`
- `crates/rtm-daemon/src/backend.rs`
- `crates/rtm-launchers/src/lib.rs`
- `examples/dockerfiles/claude.Dockerfile`
- `README.md`
- `crates/rtm-cli/tests/docker_documentation.rs`
- `crates/rtm-daemon/src/docker_preflight.rs`
- `crates/rtm-daemon/src/spawn_preflight.rs`
- `crates/rtm-daemon/src/error.rs`
- `crates/rtm-cli/src/cli/`
- `crates/rtm-core/src/types.rs`
- `crates/rtm-daemon/src/server.rs`
- `crates/rtm-daemon/src/doctor.rs`
- `crates/rtm-core/src/admin.rs`
- `crates/rtm-core/src/cli_output.rs`
- `crates/rtm-cli/tests/snapshots/`
- `CHANGELOG.md`
- `crates/rtm-daemon/src/shim_socket.rs`
- `crates/rtm-core/src/lib.rs`
- `crates/rtm-core/tests/serde_snapshots.rs`
- `crates/rtm-core/tests/wire_compat.rs`
- `crates/rtm-cli/tests/common/mod.rs`
- `crates/rtm-cli/tests/common/`
- `crates/rtm-cli/tests/`

## File-Cap Evidence

`fmm_list_files` and shell line-count checks agree that the two cap-pressure files are below but close to the 700 LOC limit:

- `crates/rtm-core/src/types.rs`: 693 LOC
- `crates/rtm-cli/tests/common/mod.rs`: 682 LOC

The precondition refactors `ALP-2692` and `ALP-2693` are therefore justified before workers add fields or harness coverage.

## Dependencies

Critical live dependency graph shape verified from Linear relations:

- `ALP-2684`, `ALP-2685`, `ALP-2686`, `ALP-2687`, `ALP-2690`, and `ALP-2693` block `ALP-2689`.
- `ALP-2692` blocks `ALP-2687`, `ALP-2690`, and `ALP-2691`.
- `ALP-2693` blocks `ALP-2690`, `ALP-2689`, and `ALP-2691`.
- `ALP-2688` blocks `ALP-2691` and is independent of `ALP-2689`.
- `ALP-2689` blocks `ALP-2691`.

## Relevance to Helioy

This pass reinforces a recurring Helioy planning rule: manual verification must be safe against pre-existing local runtime state, not just successful on a clean host. For daemon-backed tools, evidence sequences should either cleanly stop existing daemons first or run against an explicitly isolated socket or home.

## Open Questions

- Should the standard manual verification template for `runtime-matters` include an isolated `RTM_HOME` or socket path by default to avoid cross-session daemon contention?


## Round 2 Re-verification

After orchestrator amendments, ALP-2689 and ALP-2691 were re-read live via Linear MCP on 2026-05-22 Bangkok time. The three pass-9 consensus blockers were closed:

1. ALP-2689 now states the no-prior-daemon precondition, explains the `prepare_socket` socket-unlink hazard, and includes `rtm daemon status` plus conditional `rtm daemon stop` before `rtm daemon start`. ALP-2691 mirrors daemon start with prior-instance guard and the explicit daemon-state precondition.
2. ALP-2689 and ALP-2691 now enumerate required evidence artifact content, including command output or exit status, presence assertion, post-kill negated assertion, and post-stop `rtm daemon status` socket-gone confirmation.
3. ALP-2689 Notes now lists ALP-2693 and says all six blockers must land.

Final bus signoff sent: `I sign off on the rtm Docker road-test issue set pass-9 as currently filed`.
