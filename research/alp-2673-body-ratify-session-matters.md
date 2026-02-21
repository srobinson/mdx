---
title: ALP-2673 Body Ratify Audit for session-matters
type: research
tags: [session-matters, linear, namespace, cli, audit]
summary: ALP-2673 is close, with conditional fixes needed for sm home binding storage, delete-current-binding semantics, and selector issue references.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

ALP-2673 defines namespace lifecycle behavior after the create and spawn primitive. The body is mostly consistent with current source and related decisions, but it leaves worker-visible ambiguity around where the user namespace context file lives, what happens when deleting the currently bound namespace, and which selector-composition worker is the landed reference.

## Project Metadata

- Language: Rust workspace.
- Indexed with fmm: yes, `.fmm.db` available.
- Source topology observed: 98 indexed files, 14,137 LOC under `crates/`.
- Verification scope: Linear issue body audit, fmm structural navigation, targeted source excerpts, and cm decision checks.

## Architecture

### Namespace CLI surface

- `crates/sm-cli/src/cli/cli_def.rs` currently exposes `CreateResource::Namespace` but `DeleteResource` only contains `Agent`.
- `crates/sm-cli/src/cli/namespace.rs` implements namespace create, get one, and list through daemon RPCs.
- No `sm config` command bucket exists in the current CLI definition. ALP-2673 can require workers to create it, but the issue body should not imply it already exists.

### Namespace validation and reserved names

- `crates/sm-core/src/namespace.rs` defines `DEFAULT_NAMESPACE`, `RESERVED_NAMESPACE_PREFIX`, `Namespace::new`, and `Namespace::for_create`.
- `Namespace::for_create` rejects `default` for namespace creation. Namespace delete will need an equivalent lifecycle guard or a shared validation path.

### Marker reader and namespace resolution

- `crates/sm-cli/src/cli/namespace_resolver.rs` contains the workspace marker reader through `resolve_namespace_dir` and `marker_path`.
- fmm dependency graph shows direct downstream dependents only in `crates/sm-cli/src/cli/run.rs` and `crates/sm-cli/src/cli/selector_scope.rs`.
- Removal appears clean because marker reading is isolated and does not carry unrelated responsibilities beyond namespace resolution and canonical directory output.

### User-scope sm state

- `crates/sm-paths/src/lib.rs` defines user-scope state under `SmPaths::from_env`: `$SM_HOME` when set, otherwise `$HOME/.sm`.
- Existing files in that directory are `sm.pid`, `sm.db`, and `smd.log`; `SmEndpoint::from_env` resolves the daemon socket to `$SM_HOME/sock` or `$HOME/.sm/sock`.
- No existing `namespace` filename collision was found.

## Key Patterns

- The repo centralizes domain behavior in `sm-core`, then consumes it from CLI and daemon surfaces. This is visible in `Selector::scoped_to_namespace` and `Namespace::for_create`.
- CLI resource grammar is still mixed. `create` is shape A (`sm create namespace`), while `delete` remains shape B (`sm delete agent ...`). ALP-2673 intentionally introduces shape A for new lifecycle verbs, but sweeping grammar harmonization remains owned by ALP-2667.
- Generated help and tool surfaces appear tied to `tools.toml` and generated files. Any new CLI surface should check those generation paths during implementation.

## Detailed Findings

### Conditional change 1: clarify binding storage against `SM_HOME`

ALP-2673 AC #5 says the current context is stored at `~/.sm/namespace`. Current user-scope path semantics are not a raw home expansion. `SmPaths::from_env` uses `$SM_HOME` first and falls back to `$HOME/.sm`, and endpoint resolution follows the same sm home convention.

Recommended body change:

- Store current context in the sm home directory as `namespace`, meaning `$SM_HOME/namespace` when `SM_HOME` is set and `$HOME/.sm/namespace` otherwise.
- State that this does not collide with current sm home files: `sm.pid`, `sm.db`, `smd.log`, or `sock`.

Relevant source:

- `crates/sm-paths/src/lib.rs` lines 15 to 23, `SmPaths::from_env`.
- `crates/sm-paths/src/lib.rs` lines 42 to 48, `SmEndpoint::from_env`.
- `crates/sm-paths/src/lib.rs` lines 101 to 104, `sm_home_dir`.

### Conditional change 2: define delete-current-binding behavior

ALP-2673 combines namespace deletion with a user-scope current namespace context. It does not define behavior when the namespace being deleted is the currently stored context. Without this, a worker must choose between clearing the file, resetting to default, leaving a stale file that future commands must reject, or making delete fail.

Recommended body change:

- Add an observable policy. The cleanest kubectl-shaped default is: deleting the current context removes the user-scope namespace file, so subsequent commands fall back to `default` unless flag or env overrides are present.
- If a different behavior is desired, state it explicitly before workers start.

Relevant issue-body sections:

- AC #1: delete removes the namespace catalog entry and cascade-terminates dependent sessions.
- AC #5: binding storage.
- AC #6: binding precedence.

### Conditional change 3: update selector-composition reference to ALP-2676

ALP-2673 says selector composition has no regressions on the bug class fixed in ALP-2672. Linear shows ALP-2672 is Done, but the implementation worker that absorbs it is ALP-2676, “Restore namespace-scoped selector composition,” in Worker Done state. Current source already exposes `Selector::scoped_to_namespace`, and CLI `scoped_selector` consumes it.

Recommended body change:

- Reference ALP-2676 in AC #10 and References, or phrase the criterion as ALP-2672/ALP-2676 selector-composition class.

Relevant source and Linear checks:

- `crates/sm-core/src/selector.rs`, `Selector::scoped_to_namespace`.
- `crates/sm-cli/src/cli/selector_scope.rs` lines 22 to 37.
- Linear ALP-2676: Worker Done, absorbs ALP-2672.
- Linear ALP-2672: Done capture/source issue.

### Verified clean points

- `sm delete namespace` is new work. Current `DeleteResource` only has `Agent`, and daemon delete currently resolves session selectors then terminates sessions.
- `sm config` does not exist today. The body states the desired verb without assuming an existing bucket.
- Workspace marker reader removal is feasible. `namespace_resolver` is isolated and imported by `run.rs` and `selector_scope.rs`.
- `default` reserved policy exists for create. Delete must add or reuse an equivalent guard.
- Cm decision `019e4b9a-caf4-7ea3-bad3-ed89bc442231` matches the body's characterization as the prior marker-resolved default-binding decision that AC #6 supersedes after marker-reader removal.
- Cm decision `019e4b9e-6e24-7700-88d6-b038d1adf5c4` matches the body's characterization of NAMESPACE and DIR column landing.


### Peer convergence update

Pane 2.1 endorsed the three original conditions and added four more. Pane 2.2 accepted all seven conditions and sent consensus to the peer and orchestrator.

Final conditional signoff set:

1. AC #5 storage path honors sm home: `$SM_HOME/namespace`, fallback `$HOME/.sm/namespace`; slug-only-line format.
2. Define delete-current-binding behavior.
3. AC #10 and references name ALP-2676 or the ALP-2672/ALP-2676 selector-composition class.
4. Resolve `sm delete namespace` grammar before promote: current `delete` is shape B while AC #9 says new lifecycle verbs are shape A.
5. Clarify that marker-reader removal preserves or relocates canonical directory resolution. `crates/sm-cli/src/cli/run.rs::resolve_spawn_location` consumes both namespace and canonical_dir from `resolve_namespace_dir`.
6. Specify cascade-terminate contract: signal and grace configurability, and synchronous versus asynchronous return behavior.
7. State no new MCP namespace lifecycle tool lands under this master; MCP remains deferred to ALP-2671.


### Final body ratify signoff

After the orchestrator applied all seven consensus changes, pane 2.2 re-fetched ALP-2673 live from Linear and verified the body includes:

1. SM_HOME/fallback binding storage plus slug-only line.
2. Delete-current-binding clears binding and falls back to default.
3. ALP-2676 references with ALP-2672 as capture.
4. `sm delete namespace` grammar resolved as `sm <verb> <noun>` syntax, scoped away from ALP-2667 sweep.
5. Marker reader removal preserving canonical-directory resolution.
6. Cascade semantics mirroring existing session-delete path: synchronous, single mode, no v1 flags.
7. MCP lifecycle tools explicitly out of scope and deferred to ALP-2671.

Final signoff sent to orchestrator: “I sign off on ALP-2673 body as currently filed”.

## Dependencies

Critical dependencies and surfaces:

- `clap`: CLI command grammar through `cli_def.rs`.
- `sm_core`: namespace types, selectors, RPC request and response types.
- `sm_store`: namespace catalog and session namespace rows.
- `sm_paths`: user-scope sm home resolution, daemon socket and storage paths.
- `sm_daemon`: namespace RPC handlers and session delete lifecycle.

## Relevance to Helioy

This issue matters because it fixes the operator lifecycle after namespace creation. It also locks the mental model for user-scope namespace context, which affects future Helioy agents, bus sessions, selectors, and multi-tenant identity boundaries.

## Open Questions

- Should `SM_NAMESPACE` env override be parsed directly by the CLI resolver or through the new config module? ALP-2673 should name only observable precedence unless implementation decomposition matters.
- Should `sm config set-context default` be allowed, given `default` is reserved from creation but usable as a namespace fallback? The body currently says reserved-name policy is honored for lifecycle verbs, not config verbs.
- Should deleting a namespace fail if a session termination fails, partially delete with reported errors, or keep namespace until all cascade termination succeeds? AC #1 says cascade-terminated as part of delete, but failure atomicity is not specified.
