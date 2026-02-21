---
title: runtime-matters road-test issue set pass-11 review
type: research
tags: [runtime-matters, linear, moe-review, docker, sandboxing]
summary: Pass-11 final consensus closed with two substantive blockers and one non-blocking ALP-2690/server.rs reconciliation.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

Reviewed the ALP-2643 road-test corrective issue set live from Linear and filesystem state. Final pane consensus closed at two substantive blockers: ALP-2695 missing from parent corrective-wave prose, and missing shared-asset rows in ALP-2650. ALP-2690/server.rs wording drift remains a non-blocking reconciliation item; ALP-2687 post-decomposition citation consistency was withdrawn as polish.

## Project Metadata

- Project: runtime-matters
- Language: Rust
- Workspace shape from fmm: 106 indexed files, 17,322 LOC under `crates/`
- Relevant crates: `rtm-core`, `rtm-cli`, `rtm-daemon`, `rtm-launchers`
- Verification surface: Linear issue graph, fmm structure, filesystem path existence, focused source snippets

## Architecture Context

Current fmm topology shows the relevant cap-pressure files:

- `crates/rtm-core/src/types.rs`: 693 LOC
- `crates/rtm-cli/tests/common/mod.rs`: 682 LOC
- `crates/rtm-daemon/src/server.rs`: 649 LOC

`crates/rtm-daemon/src/server.rs` exports `DaemonConfig` and `run_daemon`; `run_daemon` is 50 LOC. Its dependency graph shows 10 direct downstream files, matching the ALP-2695 rationale for preserving public re-exports and downstream compile behavior.

Focused source checks for ALP-2690 entry-point reconciliation:

- `crates/rtm-daemon/src/handler.rs:102-111` handles spawn RPC composition and calls `rtm_launchers::dispatch(&request.runtime)?.launch_spec(&request)?`, then `RuntimeBackends::prepare_launch(&request, launch)`.
- `crates/rtm-launchers/src/lib.rs:54-72` composes runtime env from `request.env` into `LaunchSpec.env`.
- `crates/rtm-daemon/src/docker_runtime.rs:18-43` receives the prepared `LaunchSpec` and appends Docker env args from `launch.env`.
- `crates/rtm-daemon/src/server.rs:41-48` owns `DaemonConfig::from_env()`, including `DockerPreflightConfig::from_env()`, which is ALP-2687's real server touch.

## Detailed Findings

### Finding 1: ALP-2643 and ALP-2649 omit ALP-2695 from the corrective wave

Severity: substantive planning defect, stale parent description drift.

Evidence from live Linear:

- ALP-2695 exists under execution parent ALP-2649.
- ALP-2650 authorizes ALP-2695 in `Execute:`.
- ALP-2650 required order includes ALP-2695 before ALP-2687 and ALP-2690.
- ALP-2691 includes ALP-2695 in its precondition review criteria and dependency set.
- ALP-2695 itself is shaped consistently with ALP-2692 and ALP-2693.

Mismatch:

- ALP-2643 describes the corrective wave as ALP-2684 through ALP-2690 plus ALP-2692 and ALP-2693, plus PER ALP-2691. ALP-2695 is missing.
- ALP-2649 has the same omission in `Current children`.

Required change:

- Add ALP-2695 to both parent descriptions' corrective-wave child lists so scope tracking matches the live graph and accepted gate.

### Finding 2: ALP-2650 coordination note misses shared assets for ALP-2684 and ALP-2690

Severity: substantive coordination gap.

The coordination note enumerates shared files touched by multiple corrective-wave workers but misses two overlaps:

- `crates/rtm-daemon/src/docker_runtime.rs`: ALP-2684 rewrites Docker argv composition; ALP-2690 modifies env forwarding through Docker args.
- `crates/rtm-launchers/src/lib.rs`: ALP-2684 lists launcher resolution; ALP-2690 lists env composition.

Required change:

- Add `crates/rtm-daemon/src/docker_runtime.rs (ALP-2684 argv composition; ALP-2690 append_env_args)` and `crates/rtm-launchers/src/lib.rs (ALP-2684, ALP-2690 env composition)` to the ALP-2650 coordination note.

### Non-blocking reconciliation: ALP-2690/server.rs wording drift

Severity: non-blocking wording drift.

ALP-2695 Notes and ALP-2650 coordination prose imply ALP-2690 touches `server.rs`. Focused source checks show the env path currently lives through:

- spawn RPC dispatcher: `crates/rtm-daemon/src/handler.rs`
- runtime env composition: `crates/rtm-launchers/src/lib.rs`
- Docker env args: `crates/rtm-daemon/src/docker_runtime.rs`
- host shim handoff: `crates/rtm-daemon/src/shim_socket.rs`

`server.rs` owns `DaemonConfig::from_env()` and is a valid ALP-2687 touch, but not a necessary ALP-2690 touch from current source. ALP-2695 remains justified by ALP-2687's `server.rs` pressure plus cap pressure and downstream public surface preservation.

Recommended opportunistic cleanup:

- Remove ALP-2690 as a `server.rs` pressure source from ALP-2695 Notes and ALP-2650 coordination prose.
- If the dispatcher pass-through seam needs naming, use `crates/rtm-daemon/src/handler.rs`, not `server.rs`.

Withdrawn or non-blocking items:

- ALP-2687 post-decomposition citation annotation for `server.rs` was withdrawn as polish, not a blocker.
- ALP-2650 Required-order edge density is out of scope; blanket-edge enumeration is a deliberate planning-view convention, not a defect.

## Checks Performed

- Fetched ALP-2684 through ALP-2690, ALP-2691, ALP-2692, ALP-2693, ALP-2695, ALP-2650, ALP-2643, and ALP-2649 from Linear with relations.
- Ran `fmm_list_files` across the workspace and target directories.
- Ran `fmm_file_outline` and `fmm_dependency_graph` on `crates/rtm-daemon/src/server.rs`.
- Verified cited filesystem paths exist, including Docker runtime, daemon preflight, CLI tests, README, Dockerfile, `types.rs`, `server.rs`, and `tests/common` paths.
- Read focused snippets in `handler.rs`, `rtm-launchers/src/lib.rs`, `docker_runtime.rs`, and `server.rs` to resolve the ALP-2690/server.rs reconciliation.

## Final Sign-off

I sign off conditional on the following changes:

1. ALP-2643 Scope and ALP-2649 Current children: add ALP-2695 to the corrective-wave list next to ALP-2692 and ALP-2693.
2. ALP-2650 Coordination note: add `crates/rtm-daemon/src/docker_runtime.rs (ALP-2684 argv composition; ALP-2690 append_env_args)` and `crates/rtm-launchers/src/lib.rs (ALP-2684, ALP-2690 env composition)` as shared-asset rows.

Non-blocking reconciliation: resolve ALP-2690/server.rs wording drift opportunistically by removing ALP-2690 as a server.rs pressure source from ALP-2695 Notes and ALP-2650's server.rs coordination row, or naming `handler.rs` if the dispatcher seam needs explicit citation.

## Open Questions

None. Pass-11 final consensus closed at two substantive blockers plus one non-blocking reconciliation item.

## Final Re-read After Orchestrator Amendments

Re-read ALP-2643, ALP-2649, ALP-2650, ALP-2687, ALP-2691, and ALP-2695 live from Linear after orchestrator amendments.

Verified closed:

1. ALP-2643 and ALP-2649 include ALP-2695 in the corrective-wave lists.
2. ALP-2650 coordination note includes `crates/rtm-daemon/src/docker_runtime.rs` for ALP-2684/ALP-2690 and `crates/rtm-launchers/src/lib.rs` for ALP-2684/ALP-2690.
3. ALP-2687 annotates `server.rs` references as post-decomposition layout per ALP-2695.
4. ALP-2695 and ALP-2650 remove ALP-2690 as a server.rs pressure source and describe the env path as `handler.rs` to launchers to `docker_runtime.rs`.
5. ALP-2691 dependency prose says ALP-2690 is blocked by ALP-2692 and ALP-2693, not ALP-2695. ALP-2695 relations block ALP-2687 and ALP-2691 only.

Final sign-off sent: `I sign off on the rtm Docker road-test issue set pass-11 as currently filed`.

## Peer Clean Re-verification

Pane A independently re-fetched ALP-2643, ALP-2649, ALP-2650, ALP-2687, ALP-2690, ALP-2691, and ALP-2695 live from Linear and confirmed the same closure points, including ALP-2695 insertion, ALP-2650 shared-asset rows, ALP-2687 post-decomposition annotations, ALP-2695/ALP-2690 graph correction, ALP-2691 dependency prose, and pass-11 defect curve provenance.

Pane B acknowledged and concurred. Both panes now sign off clean on the amended issue set.
