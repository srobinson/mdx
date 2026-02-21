---
title: ALP-2673 Namespace Lifecycle Tree Review
type: research
tags: [session-matters, linear, alp-2673, namespace-lifecycle, moe-review]
summary: Pass 4 review found four gaps, then verified all consensus fixes landed and signed off cleanly.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

ALP-2673 defines the post-create namespace lifecycle surface for session-matters: namespace deletion, user-scope context binding, and removal of workspace marker reads. A fresh Linear and source review found the tree selector shape is intact, but ALP-2714 lacks a partial-failure contract for clearing stale bindings after delete, and ALP-2712 / ALP-2714 do not explicitly require automated regression tests for high-risk new behavior.

## Project Metadata

- Language: Rust, workspace edition 2024.
- Build system: Cargo workspace with `just` wrappers.
- Workspace crates: `sm-paths`, `sm-core`, `sm-store`, `sm-driver`, `sm-daemon`, `sm-cli`.
- External runtime dependency: `lilo-rm-client` and `lilo-rm-core` 0.6.1 through runtime-matters.
- Verification gate: `just check && just build && just test`.
- fmm: `.fmm.db` exists and indexed 98 files, 14,137 LOC.

## Architecture

- CLI commands are defined in `crates/sm-cli/src/cli/cli_def.rs`. Existing `DeleteArgs` exposes `selector`, namespace scope, `--signal`, and `--grace` at the delete verb level, which is the reason ALP-2714 correctly calls out namespace-specific flag scoping. See `DeleteArgs` at `crates/sm-cli/src/cli/cli_def.rs:122-132`.
- Existing CLI delete dispatch sends a `DeleteRequest` with scoped selector, signal, and grace to the daemon. See `delete_agent` at `crates/sm-cli/src/cli/delete.rs:15-46`.
- Daemon spawn normalizes and validates namespace existence while holding the store lock, then releases it before runtime spawn and final session insert. This creates a real delete-versus-spawn race surface that ALP-2714 correctly covers as a consistency invariant. See `DaemonState.spawn` at `crates/sm-daemon/src/handler.rs:132-193` and `normalize_spawn_request` at `crates/sm-daemon/src/spawn_request.rs:13-34`.
- Existing session termination is per-session. The cascade can reuse that path without a namespace-shaped runtime-matters contract because runtime-matters receives session IDs through `KillRequest`. See `DaemonState.delete_one` at `crates/sm-daemon/src/handler.rs:366-405` and `RtmdDriver.terminate` at `crates/sm-driver/src/rtmd.rs:152-187`.

## Key Patterns

- Linear selector-compatible shape is present: ALP-2673 master, ALP-2711 gate, ALP-2710 Backlog, workers ALP-2712 / ALP-2713 / ALP-2714, PER ALP-2716. ALP-2715 is canceled and not listed in the gate `Execute:` line.
- Gate ordering matches Linear relations: ALP-2712 blocks ALP-2713, ALP-2714, and ALP-2716; ALP-2713 and ALP-2714 block ALP-2716.
- Worker bodies are behavior-first and mostly avoid implementation prescription. The exception is not prescription, but missing observable contracts around partial failure and automated coverage.

## Detailed Findings

### Finding 1: ALP-2714 needs a partial-failure contract for binding clear

ALP-2673 and ALP-2714 require `sm delete namespace foo` to clear the user-scope binding when `foo` is currently bound. ALP-2714 does not say what happens if cascade and catalog deletion succeed, then clearing `$SM_HOME/namespace` fails because of EACCES, disk failure, or interruption.

Required issue change: add an observable invariant to ALP-2714. No successful delete should return with `$SM_HOME/namespace` still pointing at the deleted namespace. Retry behavior should be idempotent. Any clear failure should be surfaced without silently leaving stale binding state.

### Finding 2: ALP-2712 and ALP-2714 should require automated regression tests

ALP-2713 already requires tests for the precedence matrix. ALP-2712 and ALP-2714 rely on `just test` plus manual verification, but both add behavior that is easy to regress and already has natural test seams.

Suggested issue changes:

- ALP-2712: require tests proving set-context uses daemon-side catalog lookup, accepts `default`, rejects nonexistent namespaces without writing, and does not use `Namespace::for_create` semantics.
- ALP-2714: require tests proving namespace delete cascades dependent sessions and that `sm delete namespace --help` does not inherit agent-only flags like `--signal` and `--grace`.

## Dependencies

- `lilo-rm-client` / `lilo-rm-core`: runtime-matters protocol and kill path used by existing per-session termination.
- `rusqlite`: session and namespace catalog storage.
- `clap`: CLI command shape and generated help surface.
- `tokio`: async daemon and runtime driver interactions.

## Relevance to Helioy

The review protects the namespace lifecycle gate from selector drift and execution-time ambiguity before Nancy work starts. The important Helioy lesson is that cross-worker consistency contracts need both rollback semantics and testable acceptance criteria when daemon state and user-scope files are mutated together.

## Open Questions

- Which exact implementation mechanism should satisfy the binding-clear partial-failure invariant remains intentionally open for the worker.
- Whether the automated test requirement belongs in worker ACs only or also in PER criteria can be decided by the orchestrator.


## Pass 4 Round 2 Verification

After the orchestrator applied the pass 4 consensus changes, ALP-2712, ALP-2713, ALP-2714, and ALP-2716 were re-fetched live from Linear. The verified changes were present:

- ALP-2714 now has a combined partial-failure contract covering cascade termination, catalog removal, and binding clear, plus observable behavior #11 and acceptance criterion #8.
- ALP-2712 now has acceptance criterion #7 requiring automated tests for daemon-side namespace-get lookup, `default` binding success, unknown-namespace rejection, `$SM_HOME` override plus fallback, and atomic overwrite.
- ALP-2714 now has acceptance criterion #9 requiring automated tests for cascade termination, binding clear, namespace help flag scoping, reserved-name guard, and at least one partial-failure path.
- ALP-2716 now has partial-failure probes and test-coverage verification requiring the PER reviewer to read the test files.
- ALP-2712, ALP-2713, and ALP-2714 now restate the gate binding that this master ships no new MCP tools.

Clean sign-off was sent on bus topic `2673-tree-review-pass4` with the required phrase: `I sign off on ALP-2673 tree as currently filed`.
