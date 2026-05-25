---
title: ALP 2816 Pass 2 Review Findings for littleorgans
type: research
tags: [littleorgans, alp2816, phase6, cli, review]
summary: Pass 2 review found two W5 acceptance blockers around safe daemon smoke teardown and clean room run preconditions.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Executive Summary

This read only review checked the Phase 6 unified `lilo` worker set against live Linear and current source on `fix/shim-orphan-lifecycle`. The worker set is broadly aligned, and the CLI file size surface is acceptable if the planned dispatch modules are used. Two substantive blockers remain in ALP 2902 W5: the clean room smoke is underspecified for safe teardown, and the literal `lilo run claude` command is missing required clean room preconditions.

## Project Metadata

Language: Rust.

Build system: Cargo workspace with Moon and root `justfile` gates.

Navigation state: `.fmm.db` and `.fmmrc.toml` are present. `fmm validate` passed on branch `fix/shim-orphan-lifecycle`.

Current branch during review: `fix/shim-orphan-lifecycle`, clean worktree.

## Architecture Context

`crates/lilo/src/cli/mod.rs` is the current unified CLI dispatch entry point. It defines the `lilo` command, global output and config flags, the public help template, and a macro generated `Command` enum. Today only `doctor`, `daemon`, and the hidden runtime shim execute real paths. Other verbs still return `not_implemented()` through the fallback at `crates/lilo/src/cli/mod.rs:71-79`.

Current CLI file sizes are below the hard cap:

| File | Lines |
| --- | ---: |
| `crates/lilo/src/cli/mod.rs` | 247 |
| `crates/lilo/src/cli/daemon.rs` | 153 |
| `crates/lilo/src/cli/doctor.rs` | 277 |

The session CLI already carries the detailed `Args` surfaces in `internal/session/app/src/cli/cli_def.rs` with 348 lines. Runtime app CLI dispatch is smaller at `internal/runtime/app/src/cli.rs` with 87 lines. W1, W2, W3, and W4 already name per verb or per namespace modules, so the file cap does not require a new blocker if executors follow the written decomposition.

## Detailed Findings

### C1. W5 clean room smoke needs safe foreground daemon handling

Evidence:

1. `lilo daemon start` currently awaits the compose daemon in the foreground at `crates/lilo/src/cli/daemon.rs:29-37`.
2. `stop` performs shutdown, escalation, stale socket and pid cleanup at `crates/lilo/src/cli/daemon.rs:43-77`.
3. ALP 2902 W5 names the sequence as isolated `HOME` and `LILO_HOME`, `lilo daemon start`, wait ready, `lilo run claude`, `lilo daemon stop`, then clean teardown. It does not require background start or a trap that runs on intermediate failure.
4. ALP 2862 W5 precedent explicitly required trap guarded teardown, socket and pid checks, tmpdir cleanup, and HOME isolation.

Risk: a smoke script can hang at daemon start, or leave `lilod`, socket, pid, or tmpdir artifacts if readiness or `lilo run` fails under `set -e`.

Required change sent on the bus: specify the smoke as a shell block with isolated `HOME` and `LILO_HOME`, background daemon start, readiness via `lilo daemon status --wait`, and a trap that always stops `lilod` and removes or verifies socket, pid, and tmpdir cleanup.

### C2. W5 clean room smoke does not name required `lilo run` preconditions

Evidence:

1. Current session run grammar requires positional runtime and `--role`, with optional `--agent-config`, at `internal/session/app/src/cli/cli_def.rs:85-98`.
2. Probe command: `cargo run -q -p lilo-session-app -- run claude --detach` exited 2 and printed `--role <ROLE>` as required.
3. Named agent configs resolve under `LILO_HOME` via `internal/session/daemon/src/agent_config.rs:52-65`.
4. The `claude` launcher is resolved through PATH lookup in `internal/runtime/launchers/src/lib.rs:124-142`. There is no runtime stub path in production.
5. ALP 2902 says the smoke uses the `claude` launcher and names the literal command `lilo run claude`, but it does not name `--role`, a seeded named agent config, or how an offline clean room provides the `claude` executable.

Risk: W5 can fail before exercising session lifecycle semantics, either at clap parsing, agent config resolution, or runtime process launch.

Required change sent on the bus: make W5 name the full run command and preconditions: role, seeded named agent config under `$LILO_HOME/config/session/agents/<name>/agent.toml`, and a real or PATH seeded `claude` launcher. If the intended fix is to change the run grammar, the worker should say that explicitly.

## Verification Performed

1. `fmm validate`, passed.
2. `git status --short --branch`, clean on `fix/shim-orphan-lifecycle`.
3. `cargo run -q -p lilo-session-app -- run claude --detach`, exited 2 with the expected clap error proving `--role` is required today.
4. FMM structural reads for `crates/lilo/src/cli`, `internal/session/app/src/cli`, `internal/runtime/app/src`, `tools/xtask/src/main.rs`, and targeted symbols in run, agent config, and launcher paths.
5. Live Linear fetched for ALP 2816, ALP 2897, ALP 2904, ALP 2898, ALP 2899, ALP 2900, ALP 2901, ALP 2902, ALP 2903, ALP 2862, ALP 2863, and ALP 2894.

## Bus Reply Sent

Sent on topic `alp2816-review-pass2` to `littleorgans:general:5:1.2`:

```text
F|C1|ALP-2902|12 verification-leaks-daemon/tmpdir|crates/lilo/src/cli/daemon.rs:29-37 shows `daemon start` awaits `run_from_env()` in foreground; ALP-2902 names start/wait/run/stop but not backgrounding or trap-guarded unconditional teardown|the clean-room smoke can hang or leak lilod/socket/pid/tmpdir if an intermediate step fails|Specify the smoke as a shell block with isolated HOME+LILO_HOME, background daemon start, readiness via `daemon status --wait`, and a trap that always stops lilod and removes/verifies socket/pid/tmpdir.
F|C2|ALP-2902|7 implicit-preconditions|command proof: `cargo run -q -p lilo-session-app -- run claude --detach` exits 2 because `--role` is required; internal/session/app/src/cli/cli_def.rs:85-98 defines required runtime/role plus optional agent-config; internal/session/daemon/src/agent_config.rs:52-65 resolves named configs under LILO_HOME; internal/runtime/launchers/src/lib.rs:124-142 relies on PATH `claude` with no stub|the literal `lilo run claude` smoke is not copy-paste runnable offline in a clean room and may fail before proving lifecycle semantics|Make W5 name the full run command and preconditions: role, seeded named agent config under `$LILO_HOME/config/session/agents/<name>/agent.toml`, and a real or PATH-seeded `claude` launcher, or explicitly authorize a run-grammar change.
```

## Open Questions

1. Await orchestrator or peer follow up for the Round 1 `A` reconciliation message.
2. Await any VERIFY message after orchestrator edits.

## Follow Up: Peer Reconciliation and Conditional Signoff

Received peer F from `littleorgans:helioy-tools:codebase-analyst:5:3.1` on topic `alp2816-review-pass2`. Peer findings matched this pane's findings:

1. Peer `F1` matched `C2`: W5's `lilo run claude` smoke is non hermetic without a PATH resolvable `claude` launcher, valid seeded agent config, role, and credentials or an authorized stub setup.
2. Peer `F2` matched `C1`: W5's smoke lacks trap guarded unconditional daemon teardown.
3. Peer independently marked file size and Linear graph shape clean.

Sent reconciliation:

```text
A|accept:F1,F2,C1,C2|reject:none|missing:none
F1 and C2 are the same precondition blocker. F2 and C1 are the same teardown blocker. File-size-cap clean.
```

Sent conditional signoff:

```text
S|I sign off conditional on the following changes: 1. C1/F2: ALP-2902 W5 smoke requires background daemon start plus EXIT trap teardown that stops lilod and verifies no socket/pid/tmpdir leak on any mid-smoke failure. 2. C2/F1: ALP-2902 W5 names the full clean-room run command plus role, valid `$LILO_HOME/config/session/agents/<name>/agent.toml`, and real or PATH-seeded `claude` launcher preconditions.
```

No unread follow up remained on the topic immediately after the conditional signoff.

## Verify Round

Received `VERIFY v1` from `littleorgans:general:5:1.2` for ALP 2902, ALP 2903, and ALP 2897.

Live Linear re-read confirmed:

1. ALP 2902 now binds W5 smoke hermeticity in both `Binding decisions from the gate` and acceptance. It requires isolated `HOME` and `LILO_HOME`, PATH-seeded `which` resolvable `claude` stub, valid seeded agent config, backgrounded daemon start, readiness via `lilo daemon status --wait`, full `lilo run claude --role <role>` grammar, Running plus `lilo get session` visibility, daemon stop, unconditional EXIT trap, and no orphan `lilod`/socket/pid/tmpdir even on mid-smoke failure.
2. ALP 2903 W5 mirror now matches the hermetic smoke and trap guarded teardown requirements.
3. ALP 2897 now includes `Design call resolution: Pass-2 W5 smoke hermeticity`, binding the real end-to-end smoke through a PATH-stubbed `claude`, valid agent config, no product stub launcher, and trap guarded teardown.

Sent clean verify signoff:

```text
V|I sign off on Phase 6 worker set under ALP-2816 as currently filed
```

## Peer Verify Receipt

Received peer `V` from `littleorgans:helioy-tools:codebase-analyst:5:3.1`.

Peer independently confirmed live Linear edits resolved both consensus findings:

1. F1/C2 precondition resolved: W5 now seeds a `which` resolvable `claude` PATH stub, valid `$LILO_HOME/config/session/agents/claude/agent.toml`, and no product stub launcher.
2. F2/C1 teardown resolved: W5 now requires unconditional EXIT trap teardown and no orphan `lilod`/socket/pid/tmpdir even on mid-smoke failure.
3. New grammar citation verified: `lilo run claude --role <role>` matches current `SessionCreateArgs` grammar.
4. PER mirror and gate design call resolution are consistent, selector keywords remain parse safe, and file size cap remains clean.

No reply was required from this pane because this was the peer's verify signoff and this pane had already sent its own `V` to the orchestrator.
