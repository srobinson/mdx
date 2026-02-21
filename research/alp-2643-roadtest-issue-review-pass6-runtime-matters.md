---
title: ALP-2643 Road-Test Issue Review Pass 6
type: research
tags: [runtime-matters, linear-review, docker, nancy, alp-2643]
summary: Fresh pass-6 Linear review converged on four blockers, all applied, followed by clean sign-off.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

Reviewed the current Linear state for ALP-2684 through ALP-2692, ALP-2650, and ALP-2649 under the ALP-2643 Docker sandboxing corrective wave. Pass 6 initially surfaced four conditional blockers; after orchestrator edits, ALP-2692, ALP-2691, ALP-2689, and ALP-2687 were re-read from Linear and signed off cleanly.

Final bus sign-off sent: `I sign off on the rtm Docker road-test issue set pass-6 as currently filed`.

## Project Metadata

- Project: runtime-matters
- Branch: `nancy/ALP-2643`
- Language: Rust
- Build and verification convention: `just check && just build && just test`
- fmm index: present; `fmm ls` reports 106 indexed files and top LOC below 700 in current worktree
- Current pressure point before decomposition: `crates/rtm-core/src/types.rs` is 693 LOC

## Architecture

The reviewed Linear set targets Docker isolation support across these surfaces:

- `crates/rtm-daemon/src/docker_runtime.rs`: Docker placement and `docker run` argv construction
- `crates/rtm-daemon/src/docker_preflight.rs`: Docker image and architecture checks
- `crates/rtm-daemon/src/spawn_preflight.rs`: spawn-entry validation and isolation/profile rejection strings
- `crates/rtm-cli/src/cli/`: CLI spawn and daemon commands
- `crates/rtm-core/src/types.rs`: shared request and lifecycle types, currently 693 LOC
- `examples/dockerfiles/claude.Dockerfile` and `README.md`: operator-facing Docker contract

ALP-2692 is the precondition refactor before ALP-2687 and ALP-2690 add new spawn request fields. ALP-2689 is the real-Docker validation worker and depends on ALP-2684, ALP-2685, ALP-2686, ALP-2687, and ALP-2690. ALP-2691 is the successor post execution review for the corrective wave.

## Key Patterns

- Linear remains the source of truth. Issue bodies and relations were fetched live before review and fetched again after edits landed.
- Worker issue quality is judged by observable behavior, concrete verification, stable file references, and dependency relations.
- File-cap verification must match the possible module layout, especially when a worker is explicitly authorized to split a file into natural modules.
- Copy-paste binding manual verification must make host prerequisites explicit, not rely on ambient operator state.

## Detailed Findings

### Resolved blocker 1: recursive file-cap verification for ALP-2692

Initial issue: ALP-2692 Acceptance and Verification used `wc -l crates/rtm-core/src/*.rs`, which would miss nested modules created by a natural decomposition of `types.rs`.

Resolution verified in Linear:

- ALP-2692 now uses `fmm ls crates/rtm-core/src/` as recursive Rust file listing sorted by LOC descending.
- Acceptance and Verification require top entry LOC below 700.
- The language explicitly covers new submodule files created by the split.

### Resolved blocker 2: workspace-wide cap verification for ALP-2691

Initial issue: ALP-2691's cross-wave invariant said no modified crate file exceeds the 700-line cap, but the only concrete cap command was scoped to rtm-core.

Resolution verified in Linear:

- ALP-2691 now requires `fmm ls` with no directory argument as a recursive workspace-wide indexed file check.
- The cross-wave invariant says top entry LOC below 700 catches cumulative growth across any crate the wave touches.
- Verification includes `fmm ls` top entry LOC below 700.

Local command check:

- `fmm ls crates/rtm-core/src/` runs and reports top file `crates/rtm-core/src/types.rs` at 693 LOC.
- `fmm ls` runs and reports workspace top file `crates/rtm-core/src/types.rs` at 693 LOC.

### Resolved blocker 3: ALP-2689 PATH and daemon foreground assumptions

Initial issue: ALP-2689 Binding manual verification invoked `rtm daemon start`, `rtm spawn`, and `rtm kill` as bare commands without stating how `rtm` gets onto PATH.

Resolution verified in Linear:

- ALP-2689 now has a `Preconditions:` block stating `rtm` must be on PATH.
- The binding sequence includes `cargo install --path crates/rtm-cli` before `rtm daemon start`.
- It documents `cargo run -p rtm-cli --` as the alternative form.
- It documents that `rtm daemon start` runs in the foreground and the second shell is required for the spawn sequence.
- It also states Docker daemon and Dockerfile build-source assumptions.

### Resolved blocker 4: ALP-2687 README example runnability

Initial issue: README used positional `$SESSION_ID` in `rtm spawn`, while the current CLI expects `--session-id`.

Resolution verified in Linear:

- ALP-2687 Context now identifies the positional session-id README mismatch.
- Capability says the README example is replaced with a copy-paste runnable form matching live CLI shape.
- Acceptance requires session id via `--session-id`, image via `--image`, and isolation via `--isolation`.
- Verification requires manually copy-pasting the README example as written with credentials in environment.
- `crates/rtm-cli/tests/docker_documentation.rs` must assert the `--session-id` flag form.

## Dependencies

Critical dependencies and relations observed live:

- ALP-2689 is blocked by ALP-2684, ALP-2685, ALP-2686, ALP-2687, and ALP-2690.
- ALP-2687 and ALP-2690 are blocked by ALP-2692.
- ALP-2691 is blocked by ALP-2688, ALP-2689, and ALP-2692.
- ALP-2650 Execute line includes ALP-2692, ALP-2684 through ALP-2690, and ALP-2691.
- ALP-2650 Gate close binding moves ALP-2649, ALP-2650, and ALP-2643 to Done only after ALP-2691 reaches Done and ALP-2689 manual evidence is attached.

## Relevance to Helioy

The pass-6 corrections improve Nancy execution quality. They prevent file-size regressions from hiding in nested modules or sibling crates, make the real-Docker manual proof self-contained, and ensure the operator-facing README example is runnable against the current CLI.

## Open Questions

None for pass 6. The issue set was signed off as currently filed after re-reading the updated Linear bodies.
