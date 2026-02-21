---
title: RTM Docker Road Test Issue Review Pass 2 Consensus
type: research
tags: [runtime-matters, linear, docker, issue-review, alp-2643, consensus]
summary: Pane B validated pane A's pass-2 findings and expanded conditional signoff to include ALP-2654 terminality, profile jargon, error category, image reference, env precedence, coordination, and manual verification gaps.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

After receiving pane A's round 1 review, pane B rechecked live Linear state and source structure. The expanded consensus is that the issue set is not ready as filed: ALP-2654 is already Done, so the gate close binding cannot bind terminality, and several worker contracts need tighter observable behavior before Nancy execution.

## Project Metadata

- Project: runtime-matters
- Branch: `nancy/ALP-2643`
- Gate: ALP-2650
- Post execution review: ALP-2654
- Workers: ALP-2684, ALP-2685, ALP-2686, ALP-2687, ALP-2688, ALP-2689, ALP-2690
- Review topic: `alp-2643-roadtest-issue-review-pass2`

## Architecture

The reviewed surface keeps isolation policy on `SpawnRequest` and Docker placement in daemon code. Relevant verified paths:

- `crates/rtm-core/src/types.rs`: spawn request and isolation policy data shape.
- `crates/rtm-cli/src/cli/mod.rs`: spawn CLI entry point.
- `crates/rtm-daemon/src/spawn_preflight.rs`: Docker profile validation, including current `pattern-e` and `tmux-primary` handling.
- `crates/rtm-daemon/src/docker_preflight.rs`: Docker image resolution and metadata preflight.
- `crates/rtm-daemon/src/error.rs`: typed daemon error surface.

## Detailed Findings

### ALP-2654 terminality binding is currently non-binding

Live Linear state shows ALP-2654 is already `Done` with `completedAt: 2026-05-21T09:36:05.827Z`. The road-test corrective issues were created later at about 14:20 UTC and ALP-2650's gate close binding was updated at 14:44 UTC. The binding says ALP-2654 cannot reach Done until ALP-2689 manual evidence exists, but ALP-2654 has already reached Done.

Recommended repair: either reopen ALP-2654 to the appropriate review state or file a successor PER issue blocked by ALP-2689 and include that issue in ALP-2650 Execute and Required order.

### ALP-2688 must remove or alias `docker:pattern-e`

Source confirms `crates/rtm-daemon/src/spawn_preflight.rs` accepts `Some("pattern-e") | Some("tmux-primary")` and returns an unsupported message containing `Pattern E`. If ALP-2688 only changes message wording, the operator-facing profile string still leaks planning jargon.

Recommended repair: bind `pattern-e` removal or compatibility alias behavior explicitly, with `tmux-primary` as the operator-facing spelling.

### ALP-2687 needs a named missing-image error category

ALP-2687 says missing image source returns a typed error, but does not bind a specific category. ALP-2686 already distinguishes `DockerImageUnavailable` and `DockerImageMetadataUnavailable`; the missing configuration case should stay separate.

Recommended repair: bind a category such as `DockerImageNotConfigured` for neither flag nor daemon env.

### ALP-2687 should accept any valid Docker image reference

The issue currently says `NAME[:TAG]`, which is too narrow for registry names and digest-pinned images. The CLI design should stay as `--image`, not packed into `--isolation`, because image references already use colons and `docker[:PROFILE]` is reserved for policy profiles.

Recommended repair: replace `NAME[:TAG]` with `IMAGE_REF`, defined as any valid Docker image reference, and add acceptance for registry and digest examples.

### ALP-2690 needs duplicate and empty env semantics

The repeated `--env` flag needs deterministic behavior for collisions and empty values. Docker precedent is last wins, and empty string should be distinct from unset.

Recommended repair: bind last wins across repeated keys; `KEY=` forwards an empty value; `--env KEY` with missing caller env is a typed preflight error.

### ALP-2650 coordination note is incomplete

ALP-2688 also touches `crates/rtm-cli/tests/docker_documentation.rs`, and snapshot fixtures are co-touched by ALP-2687, ALP-2690, and ALP-2688. Add a coordination note for CLI help snapshots and doctor snapshots.

### ALP-2689 manual verification needs clearer placeholders

Pane B's original finding remains: capture `SESSION_ID=$(uuidgen)` and reuse it for `rtm kill "$SESSION_ID"`. Pane A's extension is also valid: document `<TMUX_TARGET>` shape as `session:window.pane`, for example `2:3.1`.

### ALP-2686 must block ALP-2689

Pane B's original finding remains: ALP-2689 builds and uses a local-only image, so on arm64 hosts it depends on ALP-2686's local image metadata fallback.

## Relevance to Helioy

These repairs keep the Nancy selector, gate, and PER semantics coherent. The most important issue is temporal: a gate cannot bind a terminal state that already happened.

## Open Questions

- Prefer reopening ALP-2654 or creating a successor PER issue? A successor issue is cleaner if historical review evidence should remain immutable.
- Should `pattern-e` be rejected as an unrecognized legacy spelling or retained only as an internal compatibility alias hidden from docs and examples?

## Final Re-Verification After Orchestrator Edits

Re-read live Linear state after the orchestrator applied the eight pass-2 amendments. Verified current state for ALP-2650, ALP-2686, ALP-2687, ALP-2688, ALP-2689, ALP-2690, and ALP-2691.

Clean signoff conditions are satisfied:

- ALP-2691 exists under ALP-2649, is labeled `Post Execution Review`, and is blocked by ALP-2689.
- ALP-2650 retargets the gate close binding from ALP-2654 to ALP-2691 and records why ALP-2654 cannot bind the corrective wave.
- ALP-2686 blocks ALP-2689, and ALP-2650 requires ALP-2686 before ALP-2689.
- ALP-2687 preserves `--image`, accepts valid OCI image references, keeps `--isolation docker[:PROFILE]` reserved for profiles, and binds a distinct missing-image-source category.
- ALP-2688 includes `docker:pattern-e` in removal scope.
- ALP-2689 manual verification captures `SESSION_ID`, reuses it for kill, and documents `<TMUX_TARGET>` shape.
- ALP-2690 binds last-wins duplicate env semantics and empty string distinct from unset.
- ALP-2650 coordination note covers shared docs, CLI help, snapshots, typed errors, and admin types.

Final bus signoff sent: "I sign off on the rtm Docker road-test issue set pass-2 as currently filed".
