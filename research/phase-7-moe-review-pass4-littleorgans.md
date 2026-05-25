---
title: Phase 7 MoE Review Pass 4 for littleorgans
type: research
tags: [littleorgans, linear, moe-review, phase-7, code-contract]
summary: Pass 4 found three substantive gaps in ALP-2817 and later verified the amended Linear artifacts clean.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Executive Summary

The ALP-2817 Phase 7 Linear issue set was reviewed against the current littleorgans monorepo for code-contract fit, reviewability, and executable worker sequencing. The pass found three substantive, cross-pane-convergent review gaps in W3 test-harness enumeration, W4 documentation surface coverage, and ALP-2862 cross-worker traceability wording. A conditional signoff was sent on the bus pending those amendments. After the orchestrator applied the edits to ALP-2859, ALP-2860, ALP-2862, and ALP-2863, live Linear was reread and a clean verification signoff was sent.

## Project Metadata

- Language: Rust.
- Build system: Cargo workspace with root `justfile`; fmm index present at `.fmm.db`.
- Relevant packages: `lilo`, `lilo-paths`, `lilo-runtime-app`, `lilo-session-app`, `lilo-session-daemon`, `lilo-session-store`.
- Current repo state during review: clean `git status --short`.

## Architecture Context

Phase 7 plans to compose runtime, session, and identity into a single local `lilod` daemon. The issue set under review was ALP-2817 master, ALP-2863 gate, ALP-2856 backlog, ALP-2857 through ALP-2861 workers, and ALP-2862 post-execution review.

fmm orientation confirmed a 335 file, 42,019 LOC Rust workspace with the active code concentrated under `internal/` and `crates/`. Targeted outlines confirmed the named current-source surfaces used by the Linear artifacts, including `LiloPaths.events_log_path()` at `crates/lilo-paths/src/lilo.rs:86-88`, `EventLog.append_with_ts()` at `internal/runtime/daemon/src/event_log.rs:163-183`, `IdentityClient::connect()` at `internal/session/daemon/src/identity_client.rs:44-56`, and `SqliteStore::open_in_memory()` at `internal/session/store/src/sqlite.rs:29-32`.

## Detailed Findings

### codex-F1: W3 misses a second runtime-app daemon test harness

W3 enumerates runtime app daemon-launch rewrites around `internal/runtime/app/tests/common/harness.rs`, but current source has a separate Docker E2E harness in `internal/runtime/app/tests/docker_e2e.rs`. That file constructs `rtm` directly with `CARGO_BIN_EXE_rtm`, sets `RTM_SOCKET_PATH`, `RTM_DB_PATH`, and `RTM_HOME`, then calls `rtm daemon start` and `rtm daemon stop` through `RtmDaemon` at `internal/runtime/app/tests/docker_e2e.rs:293-318` and `:326-337`.

Risk: W3 can remove `rtm daemon` launch and miss this second runtime-app daemon harness until `cargo test -p lilo-runtime-app` fails late. Required change sent on the bus: add `docker_e2e.rs` `RtmEnv` / `RtmDaemon` rewrite to W3 test-harness enumeration and to the ALP-2862 W3 mirror.

### codex-F2: W4 docs sweep misses the session skill template

W4 names `internal/runtime/app/templates/SKILL.md`, but current source also has `internal/session/app/templates/SKILL.md`. The session template still exposes obsolete user-facing names: `smd` in the description at `internal/session/app/templates/SKILL.md:3`, `sm` commands throughout the tool table at `:14-35`, and `rtm daemon start` / `smd` in the workflow at `:113`.

Risk: Phase 7 can pass the W4 docs acceptance grep while leaving MCP skill and tool distribution sources on obsolete daemon names. Peer review confirmed adjacent evidence in `internal/session/app/tools/nudge.toml`, `internal/session/app/tools/mail.toml`, and `internal/session/app/tools/run.toml`; the current grep target includes tools but the pattern does not catch `smd`, `rtmd`, or `rmd`. Required change sent on the bus: add `internal/session/app/templates/SKILL.md` to W4 docs sweep, verification grep, and PER W4 mirror, and make daemon-name leakage falsifiable with a template target plus `smd|rtmd|rmd` audit grep, or explicitly defer generated and template surfaces to Phase 6.

### codex-F3: PER clause (b) names master sections that do not exist as ALP-2817 H2s

ALP-2862 clause (b) says changes may trace to master scope sections named `docs sweep` and `test-harness rewrites`, but the ALP-2817 master H2s fetched from Linear do not include those headings. The nearest master sections are broader headings such as `Path / env contract`, `R11 transaction model`, and `Acceptance`.

Risk: the post-execution reviewer can mark legitimate W3 or W4 work as scope drift because the named master section does not exist. Required change sent on the bus: rewrite clause (b) to the actual ALP-2817 H2s, or add matching master H2s for the worker-owned surfaces.

## Bus Outcome

Peer review agreed with `codex-F1` and `codex-F3`, verified `codex-F2`, and added adjacent evidence for daemon-name leakage in session app tool TOML files. I sent `A|accept:claude-F1,claude-F2|reject:none|missing:none`, then sent a conditional signoff requiring three amendments: W3 docker E2E harness enumeration, W4 template and daemon-name docs audit coverage, and ALP-2862 clause (b) traceability repair.

The orchestrator applied the edits and requested verification on ALP-2859, ALP-2860, ALP-2862, and ALP-2863. Live Linear reread confirmed: W3 now includes `internal/runtime/app/tests/docker_e2e.rs`; W4 now includes `internal/session/app/templates/SKILL.md`, template targets, and `smd|rtmd|rmd` audit grep; ALP-2862 now routes scope tracing through actual ALP-2817 H2s plus gate decisions; ALP-2863 now contains the three Pass 4 design call resolutions. I sent `V|I sign off on ALP-2817 Phase 7 master + gate + backlog + workers + PER as currently filed`.

## Dependencies

- `lilo-paths` currently contains both the new `LiloPaths` API and legacy runtime or session path helpers pending Phase 7 cleanup.
- `lilo-runtime-app` and `lilo-session-app` currently expose `rtm` and `sm` binary targets.
- `lilo-session-store` is still rusqlite-backed in current source; Phase 7 W2 owns migration to sqlx.

## Relevance to Helioy

The review reinforces two reusable planning patterns for Helioy work: enumerate every live harness that will break under a contract migration, and include generated or template source surfaces in acceptance when user-facing names are changing. Broad wording such as “any other surface” is not enough when autonomous agents need a falsifiable checklist.

## Open Questions

- Whether the orchestrator will call the ALP-2862 clause (b) mismatch substantive or cosmetic after peer reconciliation.
- Whether generated MCP outputs are intentionally deferred to Phase 6, or whether Phase 7 should update source templates only and leave generated files untouched.
