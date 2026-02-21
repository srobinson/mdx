---
title: Runtime Matters ALP-2643 Road Test Issue Review Pass 8
type: research
tags: [runtime-matters, linear, issue-review, docker, nancy]
summary: Pass 8 re-verification found all three consensus blockers resolved in Linear.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

Pass 8 reviewed ALP-2684 through ALP-2692 and gate ALP-2650 against live Linear state and the `nancy/ALP-2643` filesystem. Initial pass 8 found three blockers. Re-verification after orchestrator edits found ALP-2650, ALP-2691, ALP-2693, ALP-2689, and ALP-2690 aligned, so pane B sent the clean sign-off phrase.

## Project Metadata

- Project: `runtime-matters`
- Branch: `nancy/ALP-2643`
- Language: Rust
- Workspace topology from fmm: 106 indexed files, 17,322 LOC under `crates/`
- Major crates: `rtm-cli`, `rtm-daemon`, `rtm-core`, `rtm-client`, `rtm-platform`, `rtm-store`, `rtm-paths`, `rtm-launchers`
- fmm index: present via `.fmm.db`
- File cap context: `fmm_list_files(directory="crates/rtm-core/src")` reports `crates/rtm-core/src/types.rs` at 693 LOC, making ALP-2692’s precondition refactor justified before ALP-2687 and ALP-2690 add spawn-request fields.

## Architecture

The corrective wave targets Docker isolation behavior across the public CLI, daemon placement and preflight, shared core request and admin types, launch env composition, documentation, and integration coverage.

Relevant entry points verified on disk:

- `crates/rtm-core/src/types.rs`
- `crates/rtm-core/src/lib.rs`
- `crates/rtm-core/tests/serde_snapshots.rs`
- `crates/rtm-core/tests/wire_compat.rs`
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
- `crates/rtm-daemon/src/server.rs`
- `crates/rtm-daemon/src/shim_socket.rs`
- `crates/rtm-daemon/src/doctor.rs`
- `crates/rtm-core/src/admin.rs`
- `crates/rtm-core/src/cli_output.rs`
- `CHANGELOG.md`
- `crates/rtm-cli/tests/snapshots/`

## Key Patterns

- Gate close logic must be checked against live child status, not only issue prose. Linear currently shows several ALP-2649 children still in `Worker Done`.
- Post execution review criteria need to mirror observable worker acceptance criteria precisely, including documentation-test assertions, not only user-facing behavior.
- fmm is effective for file-cap audits. The pass used indexed topology and focused directory file-size checks before filesystem verification.

## Detailed Findings

### Finding 1: ALP-2650 close trigger is false against live ALP-2649 children

ALP-2650 says that once ALP-2691 reaches `Done`, “ALP-2691 is the last open child of execution parent ALP-2649,” then ALP-2649, ALP-2650, and ALP-2643 can be transitioned to `Done`.

Live Linear state for ALP-2649 contradicts this. The child list still includes authorized original-wave children in `Worker Done`, including ALP-2651, ALP-2652, ALP-2657, ALP-2658, ALP-2659, ALP-2660, ALP-2661, ALP-2662, and ALP-2669.

Per the Linear workflow state model, `Worker Done` for a worker means implementation complete and awaiting post execution review. It is not the terminal `Done` state. The gate close binding should either:

1. Explicitly include closing the already-reviewed original-wave workers after ALP-2654, or
2. Correct the terminal-state logic so ALP-2649 is not closed while nonterminal authorized children remain.

Severity: blocker for clean sign-off, because the selector close path would mark the execution parent complete with live nonterminal children.

### Finding 2: ALP-2691 misses one ALP-2687 acceptance mirror

ALP-2687 requires `crates/rtm-cli/tests/docker_documentation.rs` to assert three README properties:

- Recommended example contains `--image`
- Env fallback semantics are explained
- The example uses the `--session-id` flag form

ALP-2691 verifies the README example is runnable and mentions `--session-id`, but its docker documentation test criterion only mirrors `--image` and env fallback. Add the `--session-id` assertion to ALP-2691’s ALP-2687 review criteria so the PER covers the full worker acceptance surface.

Severity: substantive review coverage gap, but narrow and easy to repair.


### Finding 3: `crates/rtm-cli/tests/common/mod.rs` needs precondition protection before harness growth

Pane A identified and pane B concurred with a third conditional blocker after fresh fmm verification. Workspace-wide `fmm_list_files(sort_by="loc")` reports `crates/rtm-cli/tests/common/mod.rs` at 682 LOC, with only 18 LOC of headroom below the hard 700-line cap. ALP-2689 explicitly names shared harness pieces under `crates/rtm-cli/tests/common/`, and ALP-2690’s end-to-end env regression coverage can plausibly route through the same harness.

Relying only on ALP-2691’s post-wave cross-file-cap invariant risks forcing an emergency split inside ALP-2689 or ALP-2690. This is the same failure mode ALP-2692 already prevents for `crates/rtm-core/src/types.rs`.

Recommended repair: file a precondition refactor issue for `crates/rtm-cli/tests/common/mod.rs` before ALP-2689 and any ALP-2690 harness additions, or bind ALP-2689 and ALP-2690 acceptance to refactor that harness along natural seams before adding code if the file would reach 700 LOC.

## Dependencies

Live relation checks found the intended road-test chain is mostly coherent:

- ALP-2692 blocks ALP-2687 and ALP-2690, plus ALP-2691.
- ALP-2684, ALP-2685, ALP-2686, ALP-2687, and ALP-2690 block ALP-2689.
- ALP-2688 and ALP-2689 block ALP-2691.
- ALP-2650 Execute line includes the original wave, ALP-2669, ALP-2692, ALP-2684 through ALP-2690, and ALP-2691.

The dependency concern is not the corrective-wave relation graph. It is the gate’s close trigger versus the current terminal state of older ALP-2649 children.

## Relevance to Helioy

This pass reinforces the Nancy planning invariant that Linear is the source of truth. Gate prose must be validated against the current issue graph before authorizing closeout, especially after multiple corrective waves and post execution reviews.

## Open Questions

- Should the original ALP-2651, ALP-2652, ALP-2657, ALP-2658, ALP-2659, ALP-2660, ALP-2661, ALP-2662, and ALP-2669 workers be transitioned to `Done` now that ALP-2654 is `Done`, or should the gate define a different terminal interpretation for already-reviewed `Worker Done` children?
- Should ALP-2691 also require a direct check that all reviewed worker statuses transition to `Done` after review outcome recording, to prevent this class from recurring?


## Re-verification Update

After the orchestrator applied pass-8 consensus blockers, pane B re-read live Linear for ALP-2650, ALP-2691, ALP-2693, ALP-2689, and ALP-2690, plus the ALP-2649 child list. The three blockers were resolved:

- ALP-2650 now includes ALP-2693 in Execute, Required order, and the coordination note. Its gate close binding explicitly handles original-wave `Worker Done` cleanup and corrective-wave cleanup before closing ALP-2649, ALP-2650, and ALP-2643.
- ALP-2691 now includes ALP-2693 review criteria and mirrors ALP-2687’s three `docker_documentation.rs` assertions, including the `--session-id` flag form.
- ALP-2693 is filed under ALP-2649 as a pure harness decomposition precondition and blocks ALP-2689, ALP-2690, and ALP-2691. ALP-2689 and ALP-2690 relations show the new blocker.

Clean sign-off sent on helioy-bus: `I sign off on the rtm Docker road-test issue set pass-8 as currently filed`.
