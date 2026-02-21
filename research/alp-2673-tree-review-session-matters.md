---
title: ALP-2673 namespace lifecycle tree review
type: research
tags: [session-matters, linear, moe-review, namespace-lifecycle]
summary: Fresh pass over the ALP-2673 Linear tree found four conditional blockers before execution readiness.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

A fresh MoE pass reviewed the ALP-2673 namespace lifecycle Linear tree and current `session-matters` source. The tree is close to selector-compatible, but four issues should be fixed before ALP-2711 flips to Worker Done.

## Project Metadata

- Language: Rust workspace.
- Project: `session-matters`.
- Index: `.fmm.db` exists and `fmm validate` reports all 98 files indexed and current.
- Relevant crates: `sm-cli`, `sm-daemon`, `sm-core`, `sm-paths`.

## Architecture

Relevant implementation surface:

- `crates/sm-cli/src/cli/cli_def.rs`: CLI command grammar. `DeleteArgs` currently carries delete flags at verb level, while `DeleteResource` has only `Agent`.
- `crates/sm-cli/src/cli/delete.rs`: CLI delete path sends `RpcRequest::Delete` to the daemon for agent deletion.
- `crates/sm-daemon/src/handler.rs`: `DaemonState::delete` and `DaemonState::delete_one` implement the existing session termination path.
- `crates/sm-cli/src/cli/namespace_resolver.rs`: current workspace marker reader and canonical directory resolver are entangled.
- `crates/sm-core/src/namespace.rs`: `Namespace::for_create` rejects `default`; it is create-specific validation, not binding validation.

## Detailed Findings

### 1. Canceled ALP-2715 remains in structural dependency relations

Live Linear shows ALP-2715 is `Canceled`, not listed in ALP-2711 `Execute:`, and not an open child of ALP-2710. However, ALP-2712, ALP-2713, and ALP-2714 still structurally block ALP-2715, while ALP-2715 is blocked by those workers. This leaves a canceled terminal issue in the worker dependency chain.

Recommendation: remove the stale dependency edges involving ALP-2715. Keeping relation links as historical references is acceptable if they do not imply execution order.

### 2. ALP-2714 prescribes a CLI shape that would leak agent flags onto namespace delete

ALP-2714 says `DeleteResource` gains a `Namespace` variant. Current source shows `DeleteArgs` owns `--signal` and `--grace` at the delete verb level, and `DeleteResource` is just a positional enum with `Agent`.

Evidence:

- `crates/sm-cli/src/cli/cli_def.rs`: `DeleteArgs` includes `resource`, `selector`, namespace scope, `signal`, and `grace`.
- `crates/sm-cli/src/cli/cli_def.rs`: `DeleteResource` currently has only `Agent`.
- `crates/sm-cli/src/cli/delete.rs`: `delete_agent` forwards `signal` and `grace` to `DeleteRequest`.

If a worker follows the stated `DeleteResource` variant instruction, `sm delete namespace` inherits agent-only `--signal` and `--grace` options. That contradicts the ALP-2711 gate's synchronous single-mode namespace delete contract.

Recommendation: rewrite the ALP-2714 entry point guidance as behavior-level routing. It should require namespace delete to avoid agent-only flags rather than prescribe adding an enum variant.

### 3. ALP-2712 points at create-only namespace validation

ALP-2712 requires `sm config set-context default` to succeed, but its stable entry points point workers at `Namespace::for_create`. Current source shows `Namespace::for_create` rejects `default`.

Evidence:

- `crates/sm-core/src/namespace.rs`: `Namespace::for_create` calls `Namespace::new`, then returns `ReservedName` when the value is `default`.

Recommendation: point workers at slug parsing plus namespace catalog lookup, not create-only validation.

### 4. ALP-2716 PER summarizes worker acceptance instead of mirroring it

ALP-2716's review criteria cover the broad worker outcomes, but they do not mirror the worker acceptance and observable behavior bullet-for-bullet. Gaps include:

- ALP-2712: `sm config --help` lists `set-context`.
- ALP-2712: `sm config set-context default` succeeds.
- ALP-2712: repeated calls overwrite atomically.
- ALP-2712: `$SM_HOME` override with `$HOME/.sm` fallback, with no literal `~/.sm` hardcode.
- ALP-2714: explicit `sm get namespace` absence after delete.
- ALP-2714: explicit `sm get agent` absence for the deleted namespace after delete.

Recommendation: expand the PER checklist so every worker AC and observable behavior has a corresponding review assertion.

## Dependencies

- Linear tree under ALP-2673: ALP-2711 gate, ALP-2710 Backlog, ALP-2712, ALP-2713, ALP-2714, ALP-2716, and canceled ALP-2715.
- Related open doc sweep: ALP-2667.
- Existing daemon termination path: `DaemonState::delete` and `DaemonState::delete_one`.

## Relevance to Helioy

This review protects Nancy selector compatibility before autonomous execution. The highest risk is the ALP-2714 CLI shape guidance because it can silently authorize a namespace lifecycle surface that conflicts with the locked single-mode delete design.

## Peer Consensus

Peer pane `session-matters:helioy-tools:codebase-analyst:1:2.1` independently confirmed all four findings on topic `2673-tree-review-pass1`. The consensus conditional sign-off was sent to the orchestrator.

## Closure Verification

The orchestrator reported that all four changes were applied. A live Linear re-fetch verified:

- ALP-2715 has empty `blockedBy` and `blocks` relations.
- ALP-2712 now points at slug parsing plus namespace catalog lookup, explicitly not `Namespace::for_create`; `default` is accepted as a binding target.
- ALP-2714 now includes the flag-scoping caveat and AC #5 forbids namespace delete from exposing agent-only termination flags.
- ALP-2716 now mirrors worker criteria in detail, including config help, `set-context default`, repeated overwrite atomicity, `$SM_HOME` override, `$HOME/.sm` fallback, post-delete namespace and agent checks, and namespace delete help flag exclusion.

Clean sign-off sent to the orchestrator: `I sign off on ALP-2673 tree as currently filed`.

## Open Questions

- Per MoE workflow, pass 1 clean closure after edits is not the exit condition. A fresh-context pass 2 is expected if the orchestrator dispatches it.
