---
title: Runtime Matters ALP-2643 Road Test Issue Review Pass 10
type: research
tags: [runtime-matters, linear, moe-review, alp-2643, docker]
summary: Pass 10 review found three blockers that were amended and verified clean in Linear.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

Reviewed the ALP-2643 road-test corrective issue set by fetching live Linear state and using fmm for file-cap pressure checks. The issue graph and most acceptance surfaces are consistent, but three pass-10 findings reached peer-consensus in the warroom.

## Project Metadata

- Project: `runtime-matters`
- Workspace: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/runtime-matters-worktrees/nancy-ALP-2643`
- Language: Rust
- Build and verification gate named by issues: `just check && just build && just test`
- fmm indexed: yes, fmm returned 106 indexed files and 17,322 LOC

## Architecture

The ALP-2643 initiative authorizes host and Docker sandboxing work through gate issue ALP-2650 and execution parent ALP-2649. The current corrective wave includes ALP-2684 through ALP-2690, precondition refactors ALP-2692 and ALP-2693, and post execution review ALP-2691.

Key current file-cap pressure points verified with fmm:

- `crates/rtm-core/src/types.rs`: 693 LOC, addressed by ALP-2692.
- `crates/rtm-cli/tests/common/mod.rs`: 682 LOC, addressed by ALP-2693.

## Detailed Findings

### 1. Stale parent descriptions

Live Linear state shows ALP-2621, ALP-2622, and ALP-2623 are `Done` capture issues related to ALP-2643. ALP-2643 still says these captures are currently in ALP-2523 and that workers are added when promoted. ALP-2649 still says it is empty until the first capture is promoted, but live Linear shows it holds the original wave, corrective wave, and ALP-2691.

Warroom message asked for ALP-2643 and ALP-2649 parent prose to be refreshed so parent descriptions do not contradict ALP-2650 gate truth or confuse closeout and selector reasoning.

### 2. Missing doctor JSON compatibility decision

ALP-2688 intentionally removes `docker.pattern_e` and all `pattern_*` keys from `rtm doctor --format json`, and ALP-2691 expects snapshots to reflect the updated surface. The issue set does not state whether this JSON field is public wire shape, compatibility exempt because it was internal jargon, or covered by a versioned breaking-change rationale.

Warroom message asked for ALP-2688 and ALP-2691 to record the compatibility decision so PER can judge the removal rather than only ratify snapshot churn.


### 3. ALP-2689 evidence misses Pattern A attach and auth-resolved observables

Pane A identified a third substantive issue and pane B concurred. ALP-2689's expected end state requires the host tmux pane named by `$TMUX_TARGET` to attach to container stdio and show Claude's interactive UI with auth resolved through `CLAUDE_CODE_OAUTH_TOKEN`, with no browser prompt. The evidence requirements only explicitly require the container presence assertion, post-kill absence assertion, and post-stop daemon status.

Consensus recommendation: ALP-2689 and ALP-2691 should require evidence that the target tmux pane shows the interactive UI with auth resolved, and should explicitly permit multiple artifacts so the daemon foreground shell, operator spawn shell, and target tmux pane can each be captured.

### Reviewed surfaces without additional findings

- ALP-2650 `Execute:` set includes the original wave, corrective wave, precondition refactors, and ALP-2691.
- Required-order prose matched the live `blockedBy` relations for the reviewed corrective set.
- ALP-2689 manual verification is copy-paste safe, includes PATH, daemon-state, Docker build source, credential, assertion, teardown, and evidence requirements.
- ALP-2691 mirrors the worker acceptance surface, including both isolation modes, cross-wave file cap, precondition refactors, and ALP-2689 evidence format.
- Shared-asset coordination in ALP-2650 covers `docker_documentation.rs`, CLI flag areas, README, snapshots, and preflight files.
- No line-number references were found in ALP-2684 through ALP-2693 or ALP-2650 acceptance surfaces during the live read.

## Dependencies

Critical issue dependencies verified from live Linear relations:

- ALP-2689 is blocked by ALP-2684, ALP-2685, ALP-2686, ALP-2687, ALP-2690, and ALP-2693.
- ALP-2687 and ALP-2690 are blocked by ALP-2692.
- ALP-2690 is also blocked by ALP-2693.
- ALP-2691 is blocked by ALP-2688, ALP-2689, ALP-2692, and ALP-2693.

## Relevance to Helioy

This review reinforces the Helioy Linear workflow invariant that gate truth, parent descriptions, and execution-parent descriptions must remain synchronized. It also flags a recurring contract issue: snapshot updates alone are not sufficient evidence when an operator-facing JSON field is removed.

## Open Questions

- Whether the orchestrator will accept both pass-10 findings as substantive and amend Linear.
- Whether the doctor JSON compatibility decision should be framed as no compatibility promise for internal jargon or as an explicit breaking surface cleanup.

## Round 2 Verification

After orchestrator amendments, re-read ALP-2643, ALP-2649, ALP-2688, ALP-2689, and ALP-2691 from live Linear. Pane B sent clean sign-off with the exact required phrase.

Verified closures:

- ALP-2643 and ALP-2649 now describe the live two-cohort graph, ALP-2650 authority, captures closed and parentless, and close trigger.
- ALP-2688 now records the doctor JSON `pattern_*` compatibility decision and requires CHANGELOG to name removed keys. ALP-2691 mirrors this as PER criteria.
- ALP-2689 now permits multiple artifacts and requires Pattern A attach, auth-resolved UI, `docker top`, assertion exits, and post-stop daemon-status evidence. ALP-2691 mirrors the load-bearing evidence requirements.

## Out-of-band Server Decomposition Decision

After the clean pass-10 sign-off, the orchestrator asked whether to file a sibling precondition for `crates/rtm-daemon/src/server.rs`. fmm verification showed `server.rs` at 649 LOC, the largest daemon source file, with 10 downstream dependents. Pane B recommended filing the third precondition because ALP-2687 and ALP-2690 both plausibly touch server-side spawn/default composition, leaving only 51 LOC before the hard cap.

Recommended shape: create an ALP-269X pure refactor titled `Decompose rtm-daemon server.rs along natural seams`; block ALP-2687 and ALP-2690 on it; add it to ALP-2650 `Execute:` and Required order; and mirror it in ALP-2691 criteria and Dependencies. Acceptance should require `fmm ls crates/rtm-daemon/src/` to report no Rust file at or above 700 LOC, existing `pub use` from `crates/rtm-daemon/src/lib.rs` to resolve, downstream crates and tests to compile unchanged, `cargo test -p rtm-daemon`, and `just check && just build && just test`. Pane A concurred and sharpened that ALP-2687 has a definite server call-site touch around `DockerPreflightConfig::from_env()` while ALP-2690 has plausible server dispatch threading. This is a preventive planning decision and does not reopen the pass-10 clean sign-off on the three amended blockers.
