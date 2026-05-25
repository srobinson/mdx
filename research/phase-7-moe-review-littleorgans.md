---
title: Phase 7 MoE Review Findings for littleorgans
type: research
tags: [littleorgans, moe-review, linear, phase-7, rust]
summary: MoE pass 1 found Phase 7 Linear blockers, then verify signoff passed after ALP-2862 PER mirroring was amended.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Executive Summary

ALP-2817 plans the Phase 7 composed daemon and absorbed `~/.lilo/` cutover for littleorgans. The review found the artifact is close in codebase fit, but not executable as filed because several Linear and source contracts would let Nancy either skip authorization, place tests where Cargo will not run them, couple a public crate to an internal crate, duplicate existing `lilo-paths` API, or rely on Phase 6 surfaces that are not structurally available.

## Project Metadata

- Language: Rust 2024 workspace.
- Build system: Cargo plus root `justfile`; `just check`, `just build`, and `just test` are the operator gates.
- Workspace size from fmm: 335 indexed files, 42,019 LOC.
- Structural index: `.fmm.db` exists and `fmm validate` passed for all 335 files.
- Important dependencies: `rusqlite 0.32.1`, `sqlx 0.8.3`, `tokio 1.48.0`, `clap 4.5.51`, `uuid 1.18.1`.
- Workspace root is a virtual workspace, not a crate: `Cargo.toml:1-23` has `[workspace]` members and no `[package]` section.

## Architecture Snapshot

- Published crates live under `crates/`; internal substrate crates live under `internal/`.
- Current command shell lives in `crates/lilo/`. `crates/lilo/src/cli/mod.rs:69-74` only dispatches `doctor`; every other `lilo` command returns the placeholder diagnostic.
- Current `lilo-paths` already owns shared root derivations. `crates/lilo-paths/src/lilo.rs:74-88` exposes `socket_path()`, `pid_path()`, `db_path()`, and `events_log_path()` for `~/.lilo/`.
- Current stores match the planning claim that session and identity audit storage are still `rusqlite`, while runtime storage is already `sqlx`:
  - `internal/session/store/src/sqlite.rs:11-27` uses `rusqlite::Connection`.
  - `crates/lilo-im-store/src/sqlite/audit.rs:7-8` and `:51-73` use `rusqlite` and store a path.
  - `internal/runtime/store/src/sqlite/lifecycle.rs:23-45` owns a `sqlx::SqlitePool`.
- Current service factory entry points exist:
  - `internal/runtime/daemon/src/service.rs:40-44`: `RuntimeService::build(ctx)`.
  - `internal/session/daemon/src/service.rs:41-45`: `SessionService::build(ctx)`.
  - `internal/identity/service/src/lib.rs:38-46`: async `IdentityService::build(config)`.
- `internal/session/app/src/compose.rs` and `internal/db/Cargo.toml` do not exist yet, as expected for Phase 7 work.

## Detailed Findings Sent on Bus

Topic: `alp-2817-review-pass1`.
Message id: `4c6ec01a-1c3a-4bfc-b114-16a7c3fde60c`.
Recipients: `littleorgans:general:9:2.1`, `littleorgans:helioy-tools:codebase-analyst:9:3.1`.

### F1. Gate status is not an accepted selector gate

- Linear evidence: `ALP-2863` status is `Backlog`.
- Workflow contract: the selector treats a gate review as accepted only at `Worker Done`.
- Risk: ALP-2856 execution will not be authorized by the gate as filed.
- Required change: after accepted review edits land, move `ALP-2863` to `Worker Done` before Nancy execution.

### F2. Root `tests/integration/` will not run in this workspace

- Code evidence: root `Cargo.toml:1-23` is workspace only and has no `[package]` section.
- Filesystem evidence: no root `tests/` directory exists today.
- Issue surface: ALP-2860 and ALP-2862 expect new integration tests at `tests/integration/`.
- Risk: `cargo test --workspace`, `cargo nextest run --workspace`, and the root `just test` gate will not compile or run workspace-root integration tests.
- Required change: place the integration tests under a real workspace package, or add a dedicated test-harness crate and name the exact runnable command in W4, W5, and PER.

### F3. `lilo-im-store` must not depend on internal `LiloDb`

- Code evidence: `crates/lilo-im-store/Cargo.toml:1-27` is a public crate manifest with no `publish = false`.
- Metadata evidence: `cargo metadata` reports `lilo-im-store publish=null`, while `lilo-session-store` and `lilo-runtime-store` report `publish=[]`.
- Issue surface: ALP-2858 says all three stores construct from `LiloDb` or its accessors.
- Risk: a published crate would gain a dependency on the nonpublished internal `internal/db` crate, breaking the crate boundary and likely release publishing.
- Required change: keep `LiloDb` inside internal composition code. Let `lilo-im-store` accept `sqlx` primitives or a small public trait, and have internal code pass `identity_pool()` into it.

### F4. W1 duplicates existing `LiloPaths` methods

- Code evidence: `crates/lilo-paths/src/lilo.rs:74-84` already exposes `socket_path()` for `~/.lilo/run/lilod.sock` with `LILO_SOCKET_PATH` override behavior, and `db_path()` for `~/.lilo/data/lilo.db`.
- Issue surface: ALP-2857 asks to add `lilod_socket()` and `identity_audit_db()` with the same meanings, and ALP-2859 refers to `paths.lilod_socket()`.
- Risk: duplicate path API invites drift, especially around `LILO_SOCKET_PATH`, and violates the DRY rule for shared helpers.
- Required change: reuse the existing methods, or intentionally rename them while deleting the old names. Update W1 and W3 wording accordingly.

### F5. Phase 6 and Phase 7 ordering contradict each other

- Linear evidence: ALP-2817 is blocked by ALP-2816, but ALP-2816 says Phase 6 planning waits until ALP-2817 post execution review passes.
- Code evidence: `crates/lilo/src/cli/mod.rs:69-74` only executes `doctor`; `tools/xtask/src/main.rs:32-39` says `xtask codegen` is deferred to Phase 6.
- Issue surface: W3 and W4 assume `lilo daemon start` and `xtask codegen` surfaces.
- Risk: Phase 7 assumes Phase 6 outcomes while Phase 6 is neither landed nor structurally before it.
- Required change: resolve ownership and ordering. Either make Phase 6 a real prerequisite and update ALP-2816, or absorb the missing `lilo daemon` and codegen work into W3 and W4.

### F6. PER summarizes instead of mirroring worker acceptance

- Issue evidence: ALP-2862 uses the generic checklist item “Each worker's acceptance criteria were met” instead of explicit W1, W2, and W5 bullets.
- Missing proof: no PER bullet explicitly falsifies W1 path derivations, internal/db workspace membership, schema table list, PRAGMA and concurrent smoke, W2 schema golden parity, W5 direct Cargo gates, fmm freshness, clean-room state check, and git-log acceptance.
- Risk: post execution review can pass without checking the full accepted worker surface.
- Required change: expand ALP-2862 to mirror worker acceptance bullet for bullet, with exact evidence expected from `Worker Done` comments.

## Checked Surfaces With No Finding

- P1 compose and factory shape: `compose.rs` is absent, but W3 frames it as new Phase 7 work. Runtime, session, and identity service factories exist at the cited entry points.
- P2 store state: the issue correctly states that `lilo-session-store` and `lilo-im-store` are `rusqlite` today and `lilo-runtime-store` is already `sqlx`.
- P3 child set and order: live Linear children under ALP-2856 are exactly ALP-2857, ALP-2858, ALP-2859, ALP-2860, ALP-2861, and ALP-2862. Relations encode W1 blocks W2, W2 blocks W3, W3 blocks W4, W4 blocks W5, and W5 blocks PER.
- P4 critical PER surfaces: deleted env behavior, PRAGMAs plus concurrent writes, two-phase spawn ordering, startup reconciliation, and `~/.lilo/` clean-room state are present in some form. The defect is lack of bullet-for-bullet mirroring.
- P6 `LiloDb` accessor shape: substrate-named accessors are viable for internal crates. The public `lilo-im-store` boundary needs clarification so the internal wrapper does not leak into a publishable crate.

## Dependencies and Runtime Contracts

- `rusqlite` remains in session and identity audit storage today, so W2 has real migration work.
- `sqlx` already backs runtime lifecycle storage, so W2 should rewire pool ownership rather than rewrite all runtime queries.
- `LILO_HOME` and `LILO_SOCKET_PATH` already exist in `lilo-paths`; legacy `RTM_*`, `SM_*`, and `AGM_HOME` references remain throughout docs, generated surfaces, and tests, giving W3 and W4 real cleanup surfaces.
- Root `xtask codegen` currently exits with a deferral message, so W4 cannot treat it as a working generator unless Phase 6 lands first or W4 owns the implementation.

## Relevance to Helioy

The review reinforces a recurring Helioy planning rule: autonomous worker issues must name executable surfaces that exist in the current head state or explicitly own their creation. Selector state, Cargo test placement, publish boundaries, and generated-surface ownership need to be proven before a gate moves to execution.

## Verify Round Finding

VERIFY v1 for Pass 1 arrived from `littleorgans:general:9:2.1` on `alp-2817-review-pass1`. Live Linear was re-read for ALP-2817, ALP-2863, ALP-2856, ALP-2857, ALP-2858, ALP-2859, ALP-2860, ALP-2862, and ALP-2861 for the W5 mirror check. An `E` response was sent because ALP-2862 still did not mirror ALP-2861 W5 acceptance exactly: ALP-2861 requires commit on `main` plus `git log -1` evidence referencing ALP-2817 and worker IDs, while ALP-2862 said only that the Phase 7 commit lands on the working branch and omitted the git-log evidence. Bus message id: `f940851e-b4d0-47ad-be2c-1df058588127`.

## Verify Round Signoff

The re-issued VERIFY for ALP-2862 amended arrived on `alp-2817-review-pass1`. Live ALP-2862 was re-read after the codex E fix. The W5 mirror now includes exit-status wording, `fmm validate` after `fmm generate`, the clean-room `LILO_HOME=$(mktemp -d)/lilo` daemon start/run/stop smoke, and `git log -1` evidence naming ALP-2817 plus worker IDs ALP-2857, ALP-2858, ALP-2859, ALP-2860, and ALP-2861. A clean V signoff was sent. Bus message id: `c388e2cc-a9d1-4352-a122-8ba7bdb91f7b`.

## Open Questions

- Peer response on the bus is still pending. No `A`, `S`, `V`, or `E` message had arrived on `alp-2817-review-pass1` after repeated polls.
- Orchestrator must decide whether Phase 6 stays before Phase 7 or whether Phase 7 absorbs the remaining `lilo daemon` and codegen surface work.
- If `lilo-im-store` is meant to stop being publishable, that is a larger package layout decision and should be explicit in the gate.
