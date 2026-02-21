---
title: ALP-2643 Pass 2 Signoff Findings
type: research
tags: [runtime-matters, linear, sandboxing, docker, review]
summary: Pass 2 adversarial review found unresolved Dockerfile authorship, stale canceled dependency relation, stale worker numbering, and runtime_pid over-specification before clean signoff.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

Live Linear review of ALP-2643 and its authorized worker chain found three finer-detail issues that should be corrected before clean pass 2 signoff. The execution shape is otherwise selector compatible: ALP-2650 is Worker Done, ALP-2649 is the execution parent, the `Execute:` line includes ALP-2651, ALP-2652, ALP-2657, ALP-2658, ALP-2659, ALP-2660, ALP-2661, ALP-2662, and ALP-2654, and the PER is recognizable.

## Project Metadata

- Project: runtime-matters
- Language: Rust
- Topology: fmm index reports 97 files and 14,982 LOC under `crates/`
- Relevant repo contract: `just check && just build && just test`
- Structural signal: fmm index available and used for initial orientation

## Architecture Context

The ALP-2643 initiative keeps the user-facing spawn contract stable while adding host and Docker execution behind a daemon-owned backend seam. Gate ALP-2650 binds isolation as spawn policy, keeps launch composition in `rtm-launchers`, keeps lifecycle normalization in daemon server, store, events, and reconcile, and defers Kubernetes and in-container sidecars.

Relevant live entry paths verified on disk:

- `crates/rtm-core/src/types.rs`
- `crates/rtm-core/src/proto.rs`
- `crates/rtm-client/src/lib.rs`
- `crates/rtm-cli/src/cli/mod.rs`
- `crates/rtm-daemon/src/spawn_preflight.rs`
- `crates/rtm-daemon/src/handler.rs`
- `crates/rtm-daemon/src/server.rs`
- `crates/rtm-daemon/src/shim_socket.rs`
- `crates/rtm-daemon/src/reconcile.rs`
- `crates/rtm-core/src/launcher.rs`
- `crates/rtm-launchers/src/lib.rs`
- `crates/rtm-platform/src/tmux.rs`
- `crates/rtm-daemon/src/doctor.rs`
- `README.md`
- `CHANGELOG.md`
- `justfile`

## Detailed Findings

### 1. ALP-2662 remains blocked on an unresolved operator decision

ALP-2662 is already authorized by the ALP-2650 `Execute:` line, but its body still branches on a future Stuart decision:

- `If Stuart chooses in-repo examples...`
- `If Stuart chooses vendor-only guidance...`
- `The worker should follow Stuart's selected Dockerfile authorship path...`

The gate comment also records `Outstanding operator decision: Dockerfile authorship path`. Under `helioy-tools:linear-workflows`, unresolved design calls at promotion time should be resolved in the accepted gate and restated by the worker. This also weakens single-session autonomous execution because the worker may need human input after selection.

Recommended correction: bind the Dockerfile authorship path now, likely `docs-only`, in ALP-2650 and ALP-2662. Remove the conditional branches from ALP-2662.

### 2. ALP-2652 still blocks canceled ALP-2653

Live relation data shows ALP-2652 blocks both ALP-2657 and ALP-2653. ALP-2653 is canceled and superseded by the v3 split. The accepted gate order does not include ALP-2653.

Recommended correction: remove the ALP-2652 to ALP-2653 blocks relation. The intended chain should be exactly ALP-2651 to ALP-2652 to ALP-2657 to ALP-2658 to ALP-2659 to ALP-2660 to ALP-2661 to ALP-2662 to ALP-2654.

### 3. ALP-2660 over-specifies Docker runtime_pid implementation

ALP-2660 says Docker headless lifecycle rows record `a host-visible Docker process PID in the runtime pid position`. This bakes an implementation shape into worker acceptance. It is also too narrow relative to the gate binding that Docker-backed liveness uses Docker inspection or equivalent Docker API state and should not rely on VM-internal container PIDs on macOS or Windows.

Recommended correction: require lifecycle and status compatibility plus a stable runtime_pid compatible representation, while leaving the exact source or shape to the worker based on current implementation and proof.


### 4. ALP-2652 uses stale relative worker numbering

Peer review found ALP-2652 acceptance still says unsupported explicit Docker policy fails `until Worker 3`. After the v3 split, Worker 3 maps to ALP-2657, which only persists lifecycle identity and explicitly does not implement Docker spawn. The Docker rejection boundary is not lifted until ALP-2660 for headless and ALP-2661 for tmux.

Recommended correction: replace the relative `Worker 3` phrase with an absolute issue reference, such as `until the Docker headless backend lands in ALP-2660`, or with non-numbered wording that names the Docker backend worker.

## Checklist Summary

- Implementation-prescriptive language: found in ALP-2660 `runtime_pid` wording.
- Acceptance versus verification contract: no worker contradicts the mandatory `just check && just build && just test` line.
- Hand-named symbols: ALP-2660 runtime pid wording is too specific.
- Cross-worker capability gaps: ALP-2652's stale `Worker 3` wording points to the wrong post-v3 worker boundary.
- Catch-22s: ALP-2662 has a selection-time decision branch.
- Order integrity: stale ALP-2652 to ALP-2653 relation should be removed, and stale relative worker numbering should be replaced with absolute issue references.
- Execute closure: good. No unauthorized active worker found under ALP-2649.
- Single-session completability: ALP-2662 is weakened by the unresolved operator decision.
- File and symbol references: entry paths verified, no line-number anchors found.
- Invariant enforceability: mostly good, with ALP-2660 needing less prescriptive runtime_pid acceptance.
- PER recognizability: good. ALP-2654 title and label match PER conventions.
- Universal issue rules: corrections above align the tree with selector-compatible worker rules.

## Relevance to Helioy

This review protects Nancy selector execution from ambiguous worker bodies and stale dependency edges. It keeps Linear as the source of truth and prevents a worker from pausing mid-session for a design choice that should be bound before authorization.

## Open Questions

- Should the orchestrator bind ALP-2662 to the warroom recommended docs-only Dockerfile path, or does Stuart want to make a different explicit choice before execution starts?


## Final Signoff Re-Read: 2026-05-21

After the orchestrator reported the four consensus changes were applied, the live Linear artifact was re-read through MCP rather than memory. ALP-2650, ALP-2652, ALP-2653, ALP-2660, and ALP-2662 now reflect the intended corrections: stale relative worker wording is gone, ALP-2652 no longer blocks ALP-2653, ALP-2653 has no parent and no relations, Dockerfile authorship is bound in the gate and ALP-2662, and ALP-2660 runtime_pid language is relaxed.

One remaining drift blocks clean signoff: ALP-2654, the post execution review issue, still says `runtime_pid` for Docker lifecycles is populated from a host-visible Docker process PID. That contradicts the amended ALP-2650 and ALP-2660 wording. Because ALP-2654 is the review issue, this stale criterion could fail a correct implementation.

Requested correction: update ALP-2654 review criteria to require a stable host-side representation compatible with existing lifecycle and status contracts, with exact source chosen at implementation time and no reliance on VM-internal container PIDs on macOS or Windows.


## Clean Signoff: 2026-05-21

The remaining ALP-2654 drift was re-read live via MCP after the orchestrator applied the correction. ALP-2654 now matches the amended ALP-2650 and ALP-2660 runtime_pid wording: Docker lifecycles carry a stable host-side representation compatible with lifecycle and status contracts, exact source is implementation-defined, and the implementation must not rely on VM-internal container PIDs on macOS or Windows. ALP-2654 also now includes a Dockerfile authorship review criterion matching ALP-2650 and ALP-2662.

Final bus message sent: `I sign off on ALP-2643 (pass 2) as currently filed`.
