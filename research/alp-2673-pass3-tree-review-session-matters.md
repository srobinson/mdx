---
title: ALP-2673 Pass 3 Tree Review for session-matters
type: research
tags: [session-matters, linear, namespace, lifecycle, moe-review]
summary: Pass 3 found one concurrency contract defect in the namespace lifecycle tree before execution.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

This review checked the live ALP-2673 namespace lifecycle Linear tree against current `session-matters` source. The issue set is mostly selector compatible and references current entry points, but it misses a load bearing concurrency contract for namespace deletion racing with binding writes and spawn insertion.

## Project Metadata

- Language: Rust, workspace edition 2024.
- Build system: Cargo workspace plus `just` recipes.
- Workspace crates: `sm-cli`, `sm-daemon`, `sm-core`, `sm-store`, `sm-driver`, `sm-paths`.
- Test command: `just test`, which runs `cargo nextest run --workspace`.
- Standard gate: `just check && just build && just test`.
- fmm index: available and used for structural navigation.

## Architecture

The reviewed lifecycle surface spans CLI, daemon RPC, and SQLite storage.

- CLI namespace lookup currently goes through `crates/sm-cli/src/cli/namespace.rs::get_one`, which sends `RpcRequest::NamespaceGet` and treats a missing `namespace` response as `unknown namespace` at lines 45 to 72.
- The binding resolver lives in `crates/sm-cli/src/cli/namespace_resolver.rs`. `resolve_namespace_dir` delegates to `resolve_namespace_dir_with_home` at lines 48 to 53.
- Current resolver behavior still reads workspace marker files in `resolve_namespace_dir_with_home` at lines 73 to 100, while also producing `canonical_dir` for `sm run`.
- `sm run` depends on both namespace and canonical directory through `resolve_spawn_location` in `crates/sm-cli/src/cli/run.rs` at lines 69 to 83.
- Selector scoping consumes the resolver in `crates/sm-cli/src/cli/selector_scope.rs::scoped_selector` at lines 22 to 37.
- Namespace storage helpers live in `crates/sm-store/src/sqlite/namespaces.rs`. `SqliteStore::namespace_exists` exists and queries the `namespaces` table.
- The schema has separate `sessions.namespace` and `namespaces.slug` columns, but no foreign key between them in `crates/sm-store/src/schema.rs` lines 1 to 55.

## Key Patterns

- Linear remains the planning source of truth. The live tree was checked via Linear, not transcript memory.
- Stable entry points are symbols or files, not line pinned worker instructions. The reviewed worker bodies mostly follow this convention.
- Current daemon operations use coarse store locking around specific reads and writes, but long running driver actions occur outside the store lock.
- Current error surface uses RPC errors with human readable messages in many CLI paths. ALP-2560 establishes that race conditions should be distinguished with typed evidence when callers need to decide whether a condition is benign.

## Detailed Findings

### Finding 1: Missing concurrency contract for namespace delete races

`ALP-2712`, `ALP-2713`, `ALP-2714`, and `ALP-2716` need an explicit contract for races between namespace deletion and operations that validate namespace existence before later side effects.

Evidence:

- `crates/sm-cli/src/cli/namespace.rs::get_one` validates catalog presence through `NamespaceGet` and then the caller can perform a later action.
- `crates/sm-daemon/src/handler.rs::spawn` normalizes the spawn request under the store lock at lines 138 to 141, releases the lock while validating and launching the runtime at lines 153 to 161, then inserts the session at lines 184 to 188.
- `crates/sm-store/src/schema.rs` lines 2 to 26 define `sessions.namespace` and `namespaces.slug` without a foreign key. A session can therefore be inserted with a namespace slug that no longer exists unless the daemon revalidates at the mutation boundary or holds a transaction across the relevant sequence.
- `ALP-2712` requires `sm config set-context foo` to validate namespace existence before writing `$SM_HOME/namespace`. If `sm delete namespace foo` runs after validation but before the file write, delete may not clear the binding and the later write can leave a dangling binding to a deleted namespace.
- `ALP-2714` requires synchronous cascade delete, but the worker does not specify how to exclude or reconcile sessions spawned into the namespace during the delete window.

Required change proposed on the bus:

1. Add an explicit concurrency contract to ALP-2712, ALP-2713, ALP-2714, and ALP-2716 for delete racing with `set-context` and `sm run`.
2. Require daemon side atomicity or revalidation at the mutation boundary.
3. Add PER race probes for both cases:
   - delete racing with binding write must not leave `$SM_HOME/namespace` pointing at the deleted namespace.
   - delete racing with spawn must not leave a running or persisted session in the deleted namespace after delete returns.

### Checks that passed

- `ALP-2712` stable entry points exist. `namespace.rs::get_one` is a real catalog lookup caller, `NamespaceGetRequest` exists in `sm-core`, and `sm-store/src/sqlite/namespaces.rs` has `namespace_exists`.
- `ALP-2713` stable entry points exist. `resolve_namespace_dir`, `resolve_spawn_location`, `scoped_selector`, and `SmPaths` are current source seams.
- `ALP-2714` stable entry points exist. `DeleteArgs` currently puts agent termination flags at the verb level and `DeleteResource` currently only has `Agent`, matching the worker warning that namespace delete must avoid inheriting agent flags.
- `ALP-2715` is canceled, has no parent, and has no `blockedBy` or `blocks` relations. It is out of the executable tree.
- `ALP-2711` authorizes `ALP-2712`, `ALP-2713`, `ALP-2714`, and `ALP-2716`. The structural relations match that order: `ALP-2712` blocks `ALP-2713`, `ALP-2714`, and `ALP-2716`; `ALP-2713` and `ALP-2714` block `ALP-2716`.
- `ALP-2716` is blocked by all three workers and has the Post Execution Review label.
- Test preconditions are visible: `just test` maps to `cargo nextest run --workspace`. The PER already requires isolated `SM_HOME=$(mktemp -d)` and cleanup discipline.

## Dependencies

Critical dependencies observed in this review:

- `clap` for CLI grammar and generated help.
- `tokio` for async daemon and CLI flows.
- `rusqlite` with bundled SQLite for local store.
- `lilo-rm-client` and `lilo-rm-core` for runtime management.
- `uuid`, `chrono`, `serde`, `serde_json`, `thiserror`, and `anyhow` for wire types, persistence, and error handling.

## Relevance to Helioy

This is a Nancy planning quality issue. If the concurrency contract is not encoded before execution, separate workers can each satisfy their local acceptance criteria while leaving a cross worker race that only appears in road testing. The fix belongs in Linear issue bodies before Nancy starts implementation, not as ad hoc worker discretion.

## Open Questions

- Which implementation contract should the planner choose: daemon side transaction and locking around delete plus spawn insertion, namespace state tombstones, or post launch revalidation with termination of the just spawned runtime on failure?
- Should `sm config set-context` be a daemon mediated mutation rather than a client side validate then local write sequence, so catalog validation and binding policy can be made race safe in one place?

## Pass 3 Closure Update

On 2026-05-22, the orchestrator reported that all three consensus changes were applied. I re-fetched `ALP-2712`, `ALP-2713`, `ALP-2714`, and `ALP-2716` live and verified:

- `ALP-2712`, `ALP-2713`, `ALP-2714`, and `ALP-2716` now encode the concurrency contract. The invariant is no silent corruption: delete racing with bind or spawn must resolve through atomic success or a clear race error.
- `ALP-2714` now names actual current agent-only flags `--signal` and `--grace` instead of absent kubectl-shaped flags. `ALP-2716` mirrors the same flag wording.
- `ALP-2716` now includes daemon-state preconditions: daemon running for happy-path probes, daemon stopped or unreachable for daemon-unreachable probes, and `ALP-2713` explicitly daemon independent.

Final bus sign-off sent on topic `2673-tree-review-pass3`: `I sign off on ALP-2673 tree as currently filed`.
