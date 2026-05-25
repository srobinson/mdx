---
title: ALP-2817 Phase 7 MoE Pass 5 Review Findings
type: research
tags: [littleorgans, linear, moe-review, phase-7, alp-2817]
summary: Pass 5 found last mile execution gaps around reconcile semantics, legacy local state, doctor warnings, commit format, and verification greps.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Executive Summary

ALP-2817 is the Phase 7 plan to compose the littleorgans daemon into one `lilod` process and finish the `~/.lilo/` cutover. Pass 5 found six substantive review findings and sent them to the orchestrator on bus topic `alp-2817-review-pass5` in message `1572a3c8-9f8f-4ac5-b120-781b2334b2cc`.

## Project Metadata

- Language: Rust 2024.
- Build system: Cargo workspace plus `just` gate surface.
- Workspace size: fmm index reports 335 files and 42,019 LOC.
- Index status: `fmm validate` passed for all 335 files on 2026-05-27.
- Root package settings: `Cargo.toml` has `[workspace.package]` version `0.8.0`, edition `2024`, rust version `1.95`.
- Relevant dependencies: `sqlx 0.8.3`, `rusqlite 0.32.1`, `tokio 1.48.0`, `clap 4.5.51`.

## Architecture

Phase 7 spans these current surfaces:

- `crates/lilo-paths/src/lilo.rs`: current `LiloPaths` exposes `socket_path`, `pid_path`, `db_path`, and `events_log_path` at lines 74 to 88. New W1 derivations are additive.
- `internal/runtime/daemon/src/reconcile.rs`: current startup reconciliation calls `reconcile_once`, which only scans `state.store().running()` at lines 180 to 201.
- `internal/session/daemon/src/reconcile.rs`: current session reconciliation leaves `Forking` and `Running` lifecycles untouched at lines 37 to 39.
- `crates/lilo/src/cli/doctor.rs`: current top level `lilo doctor` renders `DoctorStatus::empty` at lines 19 to 28, with no warnings.
- `internal/runtime/daemon/src/docker_preflight.rs` and `internal/runtime/daemon/src/reconcile.rs`: current runtime tuning env vars include `RTM_DOCKER_IMAGE`, `RTM_DOCKER_ALLOW_ROOT_IMAGE_USER`, `RTM_DOCKER_ALLOW_ARM64_MANIFEST_ESCAPE`, and `RTM_PROBE_SWEEP_INTERVAL_MS`.

## Key Patterns

- Startup reconciliation must not inherit assumptions from the old runtime daemon. Current runtime reconcile only sees `Running` rows. Phase 7 must pin semantics for `pending intent + Forking lifecycle + no session row` rather than rely on a generic pending row fixture.
- Verification that claims old user state was not touched must not assert the old state is absent. On this host, `~/.rtm`, `~/.sm`, `~/.im`, and `~/.agm` already exist. Use temporary `HOME` or before and after metadata snapshots.
- Doctor warnings must distinguish deleted legacy path env vars from still supported runtime tuning vars.
- Regex verification in issue bodies should use POSIX character classes like `[[:space:]]*` rather than escaped `\s` forms.

## Detailed Findings

### codex-F1: Crash after runtime side effect before Tx B lacks pinned reconcile semantics

Evidence:

- `internal/runtime/daemon/src/reconcile.rs:reconcile_once` scans only `state.store().running()` at lines 180 to 201.
- `internal/session/daemon/src/reconcile.rs:reconcile_lifecycles` ignores `LifecycleState::Forking` and `LifecycleState::Running` at lines 37 to 39.

Risk: a crash after Tx A and the runtime side effect but before Tx B can leave a pending intent, a Forking lifecycle, and no session row. The issues say startup reconcile either replays or aborts per fixture semantics, but do not pin this exact state.

Required amendment: add W3 policy plus W4 and PER fixtures for pending intent, Forking lifecycle, and no session row. Cover live and dead process evidence. Explicitly prevent duplicate spawn.

### codex-F2: `lilo doctor` does not warn about pre existing legacy roots

Evidence:

- `crates/lilo/src/cli/doctor.rs:DoctorCommand.run` builds `DoctorStatus::empty` at lines 19 to 28.
- Live host state has existing `~/.rtm`, `~/.sm`, `~/.im`, and `~/.agm` directories.

Risk: the operator gets no signal that old daemons or old state need manual cleanup, despite the project rule that no automatic migration is promised.

Required amendment: W4 doctor acceptance and PER mirror should warn on existing `~/.rtm`, `~/.sm`, `~/.im`, and `~/.agm` without migrating from them or using them as fallbacks. Test under a temporary `HOME`.

### codex-F3: W5 clean room smoke false fails with existing legacy roots

Evidence:

- ALP-2861 verification asserts `test ! -e ~/.rtm`, `test ! -e ~/.sm`, and `test ! -e ~/.agm`.
- This host already has those directories, plus `~/.im`.

Risk: the W5 smoke can fail on valid pre existing state. It proves absence, not that the smoke did not create or touch legacy roots.

Required amendment: set `HOME` to a temp home for the smoke or snapshot legacy root metadata before and after. Include `~/.im`. Assert no creation and no mtime or content touch.

### codex-F4: W5 commit message format remains under specified

Evidence:

- Recent Phase commit subjects use a conventional prefix and Phase marker: `0d8b0a7 feat: import session substrate (Phase 4, ALP-2814) (#5)` and `df93a04 feat: import runtime substrate (Phase 3, ALP-2813) (#4)`.
- ALP-2861 only requires references to `ALP-2817` and worker IDs.

Risk: the Phase 7 commit subject and body can drift from the observable release history format.

Required amendment: pin W5 and PER to a conventional Phase 7 subject with `ALP-2817` and PR suffix, plus a subject or body line listing `ALP-2857` through `ALP-2861`. Verify with `git log --format=%s` and `git log --format=%B` greps.

### codex-F5: W4 doctor wording can warn on supported tuning env vars

Evidence:

- `internal/runtime/daemon/src/docker_preflight.rs` currently reads `RTM_DOCKER_IMAGE` and related Docker tuning env vars.
- `internal/runtime/daemon/src/reconcile.rs:ReconcileConfig.from_env` currently reads `RTM_PROBE_SWEEP_INTERVAL_MS` at lines 25 to 37.
- ALP-2860 doctor capability says each `RTM_*`, `SM_*`, or `AGM_*` env var warns.

Risk: W4 can warn on `RTM_DOCKER_*` and `RTM_PROBE_*`, contradicting the Phase 7 gate that keeps those tuning vars functional and out of scope.

Required amendment: narrow W4 doctor wording and tests to the eight deleted legacy env vars only. Add negative checks that `RTM_DOCKER_*` and `RTM_PROBE_*` do not warn.

### codex-F6: W1 `lilo-db` grep is not robust

Evidence:

- Current root `Cargo.toml` workspace dependency lines use plain spacing, for example `lilo-runtime-app = { path = "internal/runtime/app" }`.
- A local probe showed `grep -E '^lilo-db\\s*='` fails against `lilo-db = { path = "internal/db" }`, while `grep -E '^lilo-db[[:space:]]*='` passes.

Risk: W1 acceptance can fail after correct workspace wiring.

Required amendment: replace the `lilo-db` verification grep in W1 and PER with `grep -E '^lilo-db[[:space:]]*=' Cargo.toml`.

## Dependencies

Critical dependencies for this review:

- `sqlx`: the planned shared SQLite pool and migration layer.
- `rusqlite`: currently present and slated for W4 removal after W2 migrates stores.
- `tokio`: daemon runtime and async store behavior.
- `clap`: current CLI command surface.
- `fmm`: verified current structural index and provided line referenced symbol reads.

## Relevance to Helioy

The findings protect the autonomous execution path. They reduce false failures for Nancy, prevent ambiguous replay behavior after daemon crashes, and keep the operator surface honest during the local state cutover.

## Open Questions

- The intended reconcile policy for a live orphaned process after Tx B failure still needs a design choice. The finding recommends pinning both live and dead evidence cases.
- The exact Phase 7 commit subject can be chosen by the orchestrator, but the acceptance should pin the conventional shape and worker ID proof.
