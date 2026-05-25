---
title: ALP-2817 Phase 7 Review Pass 3 for littleorgans
type: research
tags: [littleorgans, linear-review, moe, rust, sqlite, daemon]
summary: Pass 3 found three execution risks in the Phase 7 Linear plan around d9 event acceptance, workspace dependency wiring, and stale binary target names.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Executive Summary

A mail directed MoE review audited ALP-2817, ALP-2863, ALP-2856, ALP-2857 through ALP-2862 against the current littleorgans monorepo. The review sent three `F` findings on topic `alp-2817-review-pass3`: missing d9 JSONL acceptance, missing `lilo-db` workspace dependency acceptance, and stale `rmd` or `smd` binary wording that misses current `rtm` and `sm` installable targets.

## Project Metadata

- Language: Rust, edition 2024.
- Build system: Cargo workspace, root `justfile`, Moon expected for CI orchestration.
- Workspace size from fmm: 335 indexed source files, 42,019 LOC.
- fmm status: `.fmm.db` exists in the repo root and was used for structural navigation.
- Current root workspace members are explicit paths in `Cargo.toml:2-23`; local workspace dependencies are centralized in `Cargo.toml:45-61`.

## Architecture

The repo is a Rust monorepo for local first `lilo`. Published crates live under `crates/`; internal substrate code lives under `internal/`. Runtime owns launch and lifecycle state, Session owns user level session records and daemon behavior, Identity owns authorization and audit.

Phase 7 plans to compose runtime and session daemon behavior into one `lilod` process, one Unix socket, and one SQLite pool under `~/.lilo/data/lilo.db`. The reviewed worker tree splits foundation, sqlx migration, compose and path cutover, integration tests and cleanup, final acceptance, and post execution review.

## Key Patterns

- Current installable per substrate app targets are `rtm` and `sm`, not daemon crate binaries named `rmd` or `smd`.
- Runtime d9 JSONL events are currently a separate append path after lifecycle state changes. The current implementation appends sequence based JSONL records and does not expose an idempotency key at the event log layer.
- Current workspace style centralizes local crate dependencies in root `[workspace.dependencies]`, then member manifests use `*.workspace = true`.

## Detailed Findings

### F1: d9 JSONL acceptance is missing from W3 and PER mirrors

Master ALP-2817 requires d9 JSONL to be the sole event cursor of record, appended after commit, idempotent by `(session_id, event_kind)`, and never commit authority. W3 and the PER mirror describe the two phase database transactions, but do not carry an explicit d9 acceptance bullet proving post commit append and idempotency across Tx B retry or replay.

Code evidence:

- `internal/runtime/daemon/src/server/spawn.rs:169-175` updates lifecycle state, builds a running event, starts the exit watcher, then appends the event.
- `internal/runtime/daemon/src/event_log.rs:168-178` assigns the next sequence number and writes the JSONL record. No idempotency key is enforced at this layer.
- `crates/lilo-rm-core/src/types/lifecycle.rs:188-204` defines event variants by kind with `session_id`, which is enough shape for the planned idempotency contract but not enforcement.

Risk: A Phase 7 implementation could satisfy the two phase database acceptance while appending duplicate d9 events or appending before Tx B commit. The master contract would be violated without a worker or PER test failing.

### F2: `lilo-db` workspace dependency acceptance is underspecified

W1 says `internal/db/` becomes a workspace member named `lilo-db`. W2, W3, and W4 require internal stores, compose code, and integration tests to depend on `LiloDb`, but no worker acceptance says to add `lilo-db = { path = "internal/db" }` to root `[workspace.dependencies]`.

Code evidence:

- `Cargo.toml:2-23` uses an explicit workspace member array.
- `Cargo.toml:45-61` centralizes local workspace dependencies for existing internal and published crates.
- `internal/runtime/store/Cargo.toml:16-24`, `internal/session/daemon/Cargo.toml:16-32`, and `internal/runtime/daemon/Cargo.toml:16-28` use workspace dependency inheritance for local crates.

Risk: Adding `internal/db/` to `members` is not enough to make `lilo-db.workspace = true` valid in member manifests. The plan can produce a Cargo wiring failure or drift into ad hoc path dependencies.

### F3: Binary deletion wording targets `rmd` and `smd`, while current installable targets are `rtm` and `sm`

W3 and W4 say per substrate `rmd` or `smd` binaries no longer exist as installable targets. Current code exposes installable app binaries `rtm` and `sm`, with distribution metadata on the app crates, while daemon crates are libraries.

Code evidence:

- `internal/runtime/app/Cargo.toml:17-22` has `dist = true` and `[[bin]] name = "rtm"`.
- `internal/session/app/Cargo.toml:12-21` has `dist = true` and `[[bin]] name = "sm"`.
- `internal/runtime/daemon/Cargo.toml:12-14` and `internal/session/daemon/Cargo.toml:12-14` define libraries, not daemon binaries.
- `internal/runtime/app/tests/common/harness.rs:355-361` starts `rtm daemon start` with `RTM_*` env vars, and `internal/runtime/app/tests/common/harness.rs:447-459` locates `CARGO_BIN_EXE_rtm` or `rtm` in target output.
- `internal/session/daemon/tests/rtmd_driver.rs:203-213` starts `rtm daemon start` with `RTM_*` env vars, and `internal/session/daemon/tests/rtmd_driver.rs:297-300` resolves `cargo_bin("rtm")`.

Risk: An executor could remove no meaningful installable target because `rmd` and `smd` are not the current target names. Pre existing harnesses can continue to depend on `rtm`, `RTM_*`, and per substrate daemon behavior unless the worker acceptance names the actual targets and test files.

## Dependencies

Critical dependencies and surfaces observed during review:

- `sqlx 0.8.3`: planned shared SQLite pool and migration substrate.
- `rusqlite 0.32.1`: current legacy dependency slated for removal after W2.
- `lilo-paths`: current and future path derivation authority.
- `lilo-runtime-store`, `lilo-session-store`, `lilo-im-store`: stores to migrate to shared pool semantics.
- `lilo-runtime-app` and `lilo-session-app`: current app crates carrying `rtm` and `sm` binaries.

## Relevance to Helioy

The findings protect the monorepo migration from planning drift before Nancy execution starts. They keep the local control plane contract coherent: one shared database pool, one event cursor contract, and one public binary surface.

## Open Questions

- Peer review response on topic `alp-2817-review-pass3` had not arrived when this note was written.
- If the issues are amended, a follow up pass should re fetch Linear and verify W3, W4, and PER mirrors carry the d9, `lilo-db`, and actual binary target corrections.

## Round 1 A Update

After the initial `F` list, the peer reviewer sent a convergent `A` response on the same topic. I replied with `A`, agreeing there was no need for escalation and that the conditional signoff should require four amendments:

1. Add d9 JSONL post commit append and `(session_id, event_kind)` idempotency bullets to W3, W4 integration coverage, and PER mirrors.
2. Add root `[workspace.dependencies]` wiring for `lilo-db` so downstream internal crates can use `lilo-db.workspace = true`.
3. Name the actual current installable targets, `rtm` and `sm`, and decide whether their `[[bin]]` targets are removed or their daemon subcommands are stripped during the pre Phase 6 interval.
4. Enumerate harness rewrite files and proofs, including runtime app harness, session daemon common harness, and `rtmd_driver` coverage.

Additional A evidence used:

- `internal/session/daemon/src/identity_client.rs:44-56` has `IdentityClient::connect(path, local_uid)`, which is still path and audit sink shaped.
- `internal/session/store/src/sqlite.rs:29-32` has `SqliteStore::open_in_memory()`, currently rusqlite shaped.

No follow up mail had arrived on `alp-2817-review-pass3` after a short poll.

## Round 1 S Update

A fresh bus interrupt delivered the peer `S` turn. I sent a matching conditional `S` to the orchestrator and peer. The agreed conditional signoff requires the same four amendments before acceptance:

1. W3, W4, and PER must assert d9 JSONL append after Tx B commit and idempotency by `(session_id, event_kind)`.
2. W1 and PER must require root workspace dependency declaration for `lilo-db`, enabling `lilo-db.workspace = true` downstream.
3. W3 and W4 must replace `rmd` or `smd` wording with explicit disposition for actual `rtm` and `sm` installable targets.
4. W3 must enumerate test harness rewrites and verification commands for runtime app harnesses, session daemon harnesses, `IdentityClient::connect`, and `SqliteStore::open_in_memory`.

After sending `S`, I polled topic `alp-2817-review-pass3`; no further mail had arrived.

## Verify Update

A fresh bus interrupt delivered `VERIFY v1` for the amended artifacts. I re-read live Linear for ALP-2857, ALP-2859, ALP-2860, ALP-2862, and ALP-2863. The four required Pass 3 amendments were present and mirrored:

1. d9 JSONL append after Tx B commit and idempotency by `(session_id, event_kind)` in W3, W4, PER, and gate.
2. `lilo-db = { path = "internal/db" }` root workspace dependency in W1, PER, and gate, with downstream `lilo-db.workspace = true` language.
3. `rtm` and `sm` target disposition locked to retained bins during the Phase 6 interval, with daemon launch only through `lilo daemon start`.
4. Test harness rewrite enumeration covers runtime app harness, session daemon common harness, `rtmd_driver`, `IdentityClient::connect`, and `SqliteStore::open_in_memory`.

I sent `V clean` to the orchestrator on `alp-2817-review-pass3`. A follow up poll found no unread messages on the topic.

## Peer Verify Confirmation

A subsequent bus interrupt delivered the peer `V clean` verify result. The peer independently confirmed all four Pass 3 amendments across ALP-2857, ALP-2859, ALP-2860, ALP-2862, and ALP-2863, including gate design call resolutions 18 through 21. The peer noted only a cosmetic cross-worker wording issue that is covered by the new gate design calls and not an escalation.

I replied with `V concur with peer VERIFY. No additional substantive gaps after live reread. Procedural pending remains ALP-2863 gate state Backlog → Worker Done on orchestrator acceptance.` A follow up topic poll returned no unread messages.
