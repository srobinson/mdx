---
title: ALP-2813 Phase 3 Review Pass 1
type: research
tags: [littleorgans, linear, review, moe, phase-3, runtime]
summary: Fresh review of the ALP-2813 Phase 3 worker tree found code contract and verification defects before runtime import execution.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-26
updated: 2026-05-26
---

## Executive Summary

A live MoE review was requested on bus topic `alp2813-review-pass1` for the ALP-2813 Phase 3 runtime import tree. The audit found six substantive blockers across current monorepo API facts, runtime source shape, copy paste verification, and Linear relation drift.

## Project Metadata

- Language: Rust, edition 2024.
- Build system: Cargo workspace, Moon orchestration, Just operator surface.
- Active repo: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`.
- Source reference repo: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/runtime-matters` at `dad5f09c058ef2269de86b7925540b7a3d11bf9c`.
- Index state: `fmm validate` was green in both repos.

## Architecture

ALP-2813 imports runtime into the monorepo through five workers under ALP-2830 plus ALP-2840 post execution review. The target structure keeps published crates under `crates/` and internal runtime roles under `internal/runtime/{app,daemon,launchers,platform,store}`. Phase 3 does not wire the unified `lilo` runtime command surface or daemon composition.

## Key Patterns

- Use fmm first for structural checks, then narrow shell probes for command behavior.
- For Linear worker trees, accepted gate order must match live relation graph, not only issue prose.
- Verification commands must prove the intended property directly. Decorative grep, jq, or fmm checks create false confidence.

## Detailed Findings

### C1: W1 names a non existent Phase 1 public symbol

ALP-2831 says the existing `lilo-paths` public API includes `LILO_HOME`. Current source exposes `LiloHome`, `LiloPaths`, `DaemonEndpoint`, and `LiloPathError`; the `LILO_HOME` string exists only through private `LILO_HOME_ENV` at `crates/lilo-paths/src/lib.rs:9`. Verified symbols:

- `crates/lilo-paths/src/lib.rs:14` `pub struct LiloHome`.
- `crates/lilo-paths/src/lib.rs:42` `pub struct LiloPaths`.
- `crates/lilo-paths/src/lib.rs:94` `pub struct DaemonEndpoint`.
- `crates/lilo-paths/src/lib.rs:117` `pub enum LiloPathError`.
- `fmm_lookup_export(LILO_HOME)` returned missing.

Risk: W1 acceptance asks the worker to preserve and prove a public API item that does not exist.

Required change: replace `LILO_HOME` with the current public symbol, likely `LiloPathError`, or explicitly authorize adding a new public constant if that is desired.

### C2: RuntimeService factory conflicts with clean import rule

ALP-2832 requires `RuntimeService::build(...)`. Runtime source currently does not define `RuntimeService`. `runtime-matters/crates/rtm-daemon/src/lib.rs:9-29` exports modules plus `ReconcileConfig`, `DaemonConfig`, and `run_daemon`; fmm export search found no `RuntimeService`.

ALP-2840 also says imported source should not be rewritten beyond dependency rewires and Cargo workspace inheritance. That conflicts with a required new daemon factory.

Risk: the worker must add a factory to pass W2, but PER can reject the same change as an unauthorized source rewrite.

Required change: declare the `RuntimeService` adapter as an allowed W2 source change and mirror that carveout in ALP-2840, or move the factory to the phase that owns it.

### C3: W5 all package jq check is invalid

ALP-2839 uses this jq shape:

```bash
([.packages[].name] - ["lilo-rm-core", ...]) | (length < [.packages[].name] | length)
```

After the first pipe, `.` is an array, so `.packages[]` errors with `Cannot index array with string "packages"`. The expression also proves only that at least one target package exists if repaired mechanically.

Risk: W5 cannot prove all seven runtime packages are present.

Required change: use a missing set assertion such as:

```bash
(["lilo-rm-core","lilo-rm-client","lilo-runtime-platform","lilo-runtime-launchers","lilo-runtime-store","lilo-runtime-daemon","lilo-runtime-app"] - [.packages[].name]) | length == 0
```

### C4: W5 fmm crate root loop cannot pass with grouped output

ALP-2839 loops over crate roots and greps them in `fmm list-files --group-by=subdir`. Current fmm grouped output at the littleorgans root emits top level buckets: `crates/`, `internal/`, and `tools/`. It does not emit `crates/lilo-rm-core` or `internal/runtime/...` in that mode.

Risk: the fmm indexing proof fails even when the index is correct.

Required change: check each path directly, for example:

```bash
fmm list-files "$p" --limit 1 | grep -F "$p"
```

### C5: W1 grep commands target a directory without recursion

ALP-2831 verification includes commands like:

```bash
grep -F 'RTM_SOCKET_PATH' crates/lilo-paths/src/
```

BSD and GNU grep treat a directory operand without `-r` as an error.

Risk: the W1 public API proof fails regardless of implementation.

Required change: use recursive grep or specific source files:

```bash
grep -rF 'RTM_SOCKET_PATH' crates/lilo-paths/src/
```

### C6: Linear blocker graph still contains canceled worker relations

The accepted ALP-2841 gate order is:

```text
ALP-2831 -> ALP-2832 -> ALP-2833 -> ALP-2842 -> ALP-2839 -> ALP-2840
```

Live Linear relations still connect active workers to canceled ALP-2834 through ALP-2838. Most importantly, ALP-2839 is blocked by canceled ALP-2838. Active ALP-2831, ALP-2832, and ALP-2833 also still block canceled workers.

Risk: the active blocker graph no longer matches the accepted gate and can confuse selector or closure reasoning.

Required change: remove stale block and blockedBy relations between active workers and canceled ALP-2834 through ALP-2838.

## Dependencies

Critical dependencies reviewed:

- `clap`, `serde`, `serde_json`, `tokio`, `thiserror`, `uuid`, `rusqlite`, `sqlx`, and Moon through issue acceptance criteria.
- fmm local indexes for both monorepo and runtime source.
- Linear issue relations and issue descriptions for ALP-2813, ALP-2830, ALP-2831, ALP-2832, ALP-2833, ALP-2839, ALP-2840, ALP-2841, ALP-2842, and canceled ALP-2834 through ALP-2838.

## Relevance to Helioy

This pass reinforces that imported source plus newly required factory APIs need explicit permission in worker and PER text. It also shows that verification snippets should be exercised as shell, not only read as intent.

## Open Questions

- Should `RuntimeService::build` land in Phase 3 as a small adapter, or should Phase 3 remain a pure source import and defer the factory to Phase 7?
- Should `lilo-paths` expose a public `LILO_HOME` constant, or should issue text use the existing `LiloPathError` public symbol?
