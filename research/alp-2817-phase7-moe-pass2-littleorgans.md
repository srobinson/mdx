---
title: ALP-2817 Phase 7 MoE Pass 2 Review Findings
type: research
tags: [littleorgans, linear-review, moe, phase-7, alp-2817, composed-daemon]
summary: Pass 2 found five substantive execution readiness defects in the Phase 7 Linear artifact and sent them to the MoE bus thread.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Executive Summary

The ALP-2817 Phase 7 issue set is a Rust monorepo gate for composing runtime, session, and identity into one `lilod` process while cutting local state over to `~/.lilo/`. Pass 2 found five substantive defects: accepted gate status mismatch, unsafe daemon smoke commands, incomplete clean-room preconditions, premature publish dry-run proof, and brittle SQLite PRAGMA wording.

Findings were sent on helioy-bus topic `alp-2817-review-pass2` to the orchestrator and peer reviewer using the requested `F` protocol.

## Project Metadata

- Language: Rust 2024.
- Workspace: 335 indexed files, 42,019 LOC by fmm.
- Topology: `internal/` holds 274 files and 33,072 LOC; `crates/` holds 60 files and 8,902 LOC; `tools/` holds one file.
- fmm state: `.fmm.db` and `.fmmrc.toml` are present at repo root.
- Build surface: root `justfile`, Cargo workspace, `fmm generate && fmm validate` for structural index refresh.
- Current key dependencies: `sqlx = 0.8.3`, `rusqlite = 0.32.1`, `tokio = 1.48.0`, `clap = 4.5.51` in `Cargo.toml`.

## Architecture Context

Phase 7 targets one composed daemon behind `lilod.sock`. The current tree still has split substrate implementations:

- Top level `crates/lilo` currently dispatches only `doctor`; other commands return `not yet implemented` through `Cli::run` at `crates/lilo/src/cli/mod.rs:69-74` and `Command::not_implemented` at `crates/lilo/src/cli/mod.rs:122-124`.
- Current session daemon lifecycle logic lives in `internal/session/app/src/cli/daemon.rs`. `start` spawns the internal daemon and waits for readiness at `internal/session/app/src/cli/daemon.rs:26-67`; `stop` is the only cleanup path at `internal/session/app/src/cli/daemon.rs:69-102`.
- `LiloHome::from_env` reads `LILO_HOME` per process at `crates/lilo-paths/src/lilo.rs:18-25`. Socket, pid, and db derivations are under `LiloPaths` at `crates/lilo-paths/src/lilo.rs:74-84`.
- Agent config resolution currently fails missing named configs through `resolve_agent_config_with_home` at `internal/session/daemon/src/agent_config.rs:30-36`, with the legacy `.agm/<name>/agent.toml` shape at `internal/session/daemon/src/agent_config.rs:54-59`.
- Runtime store already uses sqlx and WAL setup through `SqliteConnectOptions` at `internal/runtime/store/src/sqlite/lifecycle.rs:34-43`; current SQL migrations use `0001_lifecycle.sql` style filenames under `internal/runtime/store/migrations/`.

## Detailed Findings

### codex-F1: Gate body says ready, Linear status still Backlog

Evidence:

- Live Linear ALP-2863 body begins with `Outcome: Ready for execution`, `Authorized execution parent: ALP-2856`, and the correct `Execute:` set.
- Live Linear ALP-2863 status returned `Backlog`, status type `backlog`.
- The Linear workflow contract says an accepted gate review issue terminates at `Worker Done`; the status is part of selector compatibility.

Risk: Nancy can treat the gate as unaccepted, so W1 through W5 and PER may not become executable even though the body is ready.

Required change sent on bus: Set ALP-2863 to `Worker Done` after acceptance, or make the body and status consistently unaccepted.

### codex-F2: Daemon smoke commands are not teardown safe

Evidence:

- Current cleanup path is explicit `stop` logic in `internal/session/app/src/cli/daemon.rs:69-102`.
- W3 verification uses `cargo run -p lilo -- daemon start &`, then status, then stop, with no trap.
- W5 verification gives only `LILO_HOME=$(mktemp -d)/lilo lilo daemon start  # then run + stop`.

Risk: If status or run fails under `set -e` or a CI wrapper, the stop path may never run. A backgrounded daemon, pid file, socket, or temp state can survive the verification.

Required change sent on bus: Replace the smoke with exported temp `LILO_HOME`, explicit start/status/run/stop commands, and trap cleanup that always stops and proves no pid, socket, or process remains.

### codex-F3: W5 clean-room smoke has incomplete env and agent config preconditions

Evidence:

- `LiloHome::from_env` reads `LILO_HOME` per process at `crates/lilo-paths/src/lilo.rs:18-25`.
- A one-line `LILO_HOME=... command` assignment does not apply to subsequent `lilo run` or `lilo daemon stop` commands.
- The current resolver errors on missing named configs at `internal/session/daemon/src/agent_config.rs:30-36`, with a test proving the structured missing config error at `internal/session/daemon/src/agent_config.rs:260-267`.

Risk: The clean-room smoke can start against a temp home, then run or stop against the operator default home. It also claims a trivial agent config without creating or passing one.

Required change sent on bus: Spell out `tmp=$(mktemp -d)`, export `LILO_HOME` for all commands, create or pass the trivial agent config, run against that same environment, then stop against that same environment.

### codex-F4: PER publish dry-run depends on registry ordering, not W2 correctness

Evidence:

- PER W2 mirror requires `cargo publish --dry-run -p lilo-im-store`.
- Current `crates/lilo-im-store/Cargo.toml` depends on `lilo-im-core.workspace`.
- Live command proof on 2026-05-27: `cargo publish --dry-run -p lilo-im-store --allow-dirty` failed because crates.io has no `lilo-im-core ^0.8.0`; candidate versions were `0.1.1`, `0.1.0`, and `0.0.0`.

Risk: The PER can fail before release-plz publishes sibling crates, for registry state rather than W2 implementation correctness.

Required change sent on bus: Move publish dry-run proof to the release phase after dependencies exist, or use `cargo package -p lilo-im-store` plus manifest and public API checks in PER.

### codex-F5: PRAGMA synchronous wording is brittle

Evidence:

- macOS sqlite3 proof: after `PRAGMA synchronous=NORMAL`, `PRAGMA synchronous` returns `1`.
- W1 and PER wording ask for `synchronous=NORMAL`.
- Current runtime sqlx setup already uses SQLite pragmas at `internal/runtime/store/src/sqlite/lifecycle.rs:34-43`.

Risk: A string assertion against `NORMAL` can fail across SQLite/sqlx return shapes even when the database is configured correctly.

Required change sent on bus: Require normalized PRAGMA proof: case-normalized `journal_mode=wal`, `busy_timeout=5000`, and `synchronous` numeric `1` or mapped to `NORMAL`.

## Negative Checks

- Gate body keyword ordering looked selector safe: the first `Outcome:`, `Authorized execution parent:`, and `Execute:` occurrences are the canonical header lines.
- Linear dependency chain looked correct from live relations: W1 blocks W2, W2 blocks W3, W3 blocks W4, W4 blocks W5, W5 blocks PER.
- Current line counts do not indicate immediate 700 LOC pressure on the probed files: `crates/lilo/src/cli/doctor.rs` is 86 LOC, `crates/lilo-paths/src/lilo.rs` is 317 LOC, `internal/session/store/src/lib.rs` is 10 LOC, and `internal/identity/service/src/lib.rs` is 96 LOC. The largest nearby touched files are still below the cap: `internal/session/app/src/cli/namespace_resolver.rs` at 417 LOC, `internal/runtime/store/src/sqlite/lifecycle.rs` at 363 LOC, and `crates/lilo-im-store/src/sqlite/audit.rs` at 333 LOC.
- Existing sqlx migration filenames use the simple `<version>_<name>.sql` form, for example `internal/runtime/store/migrations/0001_lifecycle.sql`.

## Dependencies

Critical dependencies for the reviewed surface:

- `sqlx`: target migration substrate for unified SQLite state and migration macros.
- `rusqlite`: still present and intentionally removed by Phase 7 after store migration.
- `tokio`: async runtime for daemon composition and store access.
- `clap`: CLI command surface.
- `nix`: signal and process handling for daemon lifecycle.

## Relevance to Helioy

This pass reinforces three Helioy workflow rules: accepted Linear gates must align body and status, smoke commands must include unconditional cleanup, and registry-dependent proofs belong in release workflows rather than pre-release execution reviews.

## Open Questions

- Whether the orchestrator will apply all five findings or reject any as already covered by unpublished edits.
- Whether `lilo daemon start` should daemonize and return or run foreground compose directly. The current verification text implies both shapes in different places; the issue set needs one explicit contract.
- Whether PER should retain any publish-style proof before release, possibly `cargo package`, or defer all publish verification to release-plz.

## Bus Reconciliation Update

After peer findings arrived on topic `alp-2817-review-pass2`, I sent an `A` message accepting `claude-F1`, `claude-F2`, and `claude-F3`, rejecting `claude-F4` because the PER cross-worker rule already allows traceability to gate binding decisions, and marking `codex-F1` plus `codex-F5` as missing from the peer list.

I then sent conditional signoff covering four required edits: gate status consistency, teardown-safe daemon smoke with exported temp `LILO_HOME` and seeded agent config, relocation or replacement of registry-resolving publish dry-run proof, and normalized PRAGMA assertions. No further inbox replies were present when polled after the signoff.

## Peer Agreement Update

The peer sent an `A` message after my conditional signoff. They accepted `codex-F2`, `codex-F3`, `codex-F4`, and `codex-F5`; partially accepted `codex-F1` as a verified gate-status conflict whose fix is orchestrator-procedural rather than a worker-body edit; and withdrew `claude-F4` after agreeing that PER clause (a) already covers gate-body binding decisions. No additional bus reply was sent because I had already sent the single allowed `A` and `S` messages for the round.

## Peer Conditional Signoff Update

The peer sent `S|conditional sign-off` convergent with my conditional signoff. They summarized the round as five unique substantive findings across both reviewers: three convergent, two codex-only, with `claude-F4` withdrawn. No reply was sent because the protocol allows one `A` and one `S` per round, both already sent from this pane. The thread is now waiting on orchestrator reconciliation.

## Verify Round Update

The orchestrator sent `VERIFY v1` after applying the consensus edits to ALP-2857, ALP-2858, ALP-2859, ALP-2861, ALP-2862, and ALP-2863. I re-read all six live Linear artifacts. The amendments now carry the normalized PRAGMA assertion shape, package/no-verify replacement for the publish dry-run proof, trap-guarded daemon smoke wording, seeded clean-room agent config, teardown evidence mirrors, and the three new MoE Pass 2 design-call resolutions in ALP-2863. I sent `V|I sign off on ALP-2857, ALP-2858, ALP-2859, ALP-2861, ALP-2862, ALP-2863 as currently filed` on topic `alp-2817-review-pass2`.

## Peer Verify Signoff Update

The peer sent `V|clean` on topic `alp-2817-review-pass2`. They independently rechecked all four reconciliations across the amended artifacts, confirmed the selector keyword first-occurrence rule remains intact in ALP-2863, confirmed the W1 through PER relation chain still holds, and noted codex-F1 remains an orchestrator status action. No bus reply was sent because this pane had already sent its own clean `V` signoff and the peer message was informational convergence.
