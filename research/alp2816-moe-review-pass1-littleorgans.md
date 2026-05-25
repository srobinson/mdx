---
title: ALP-2816 MoE Review Pass 1 Findings
type: research
tags: [littleorgans, alp-2816, moe-review, linear, cli, session, runtime, identity]
summary: Pass 1 found selector, identity RPC, orphan child issue, PER mirroring, and test harness gaps in the Phase 6 unified lilo CLI worker set.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Executive Summary

ALP-2816 plans Phase 6 for the unified `lilo` command surface. The current worker set is directionally sound, but pass 1 found five execution blocking review gaps before authorization.

Findings were sent on helioy-bus topic `alp2816-review-pass1` as `codex-F1` through `codex-F5`.

## Project Metadata

- Language: Rust, edition 2024.
- Build system: Cargo workspace plus Moon orchestration. Root `justfile` wraps local gates.
- Workspace version: `0.8.0`.
- Rust version: `1.95` from root workspace package metadata.
- Key dependencies: `clap`, `tokio`, `sqlx`, `serde`, `uuid`, `nix`, `lilo-im-core`, `lilo-im-store`, `lilo-session-*`, `lilo-runtime-*`.
- Navigation state: `.fmm.db` and `.fmmrc.toml` exist. `fmm validate` reported all 351 indexed files current.

## Architecture

Phase 6 spans three surfaces:

1. `crates/lilo` is the unified CLI binary. Current `Cli::run` handles only `doctor`, `daemon`, and the hidden runtime shim. All other user and operator verbs still return `not_implemented()` at `crates/lilo/src/cli/mod.rs:71-79`.
2. `internal/session/app` owns existing session CLI argument types and library functions. `RunArgs`, `SessionCreateArgs`, and related verb args are public in `internal/session/app/src/cli/cli_def.rs:22-348`. `run` and `create_session` route into `SessionRpc::Spawn` in `internal/session/app/src/cli/run.rs:15-39`.
3. `internal/runtime/app` owns existing runtime operator args and library functions. The top level runtime `Command` enum remains private in `internal/runtime/app/src/cli.rs:30-56`, but individual argument structs and `run` functions are public in modules such as `internal/runtime/app/src/cli/spawn.rs:14-82`.

The composed daemon boundary is rooted in session. The session daemon extracts peer credentials at `internal/session/daemon/src/server.rs:76-100`, then dispatches only `SessionRpc`. Session spawns persist intent and session rows in `internal/session/daemon/src/handler/spawn.rs:69-99`, with audit and pending intent in Tx A at `internal/session/daemon/src/handler/spawn.rs:101-140` and final session insert plus intent resolution in Tx B at `internal/session/daemon/src/handler/spawn.rs:145-225`. Raw runtime spawn records lifecycle through `internal/runtime/daemon/src/handler.rs:135-173` and only appends the running event for non session backed spawns via `internal/runtime/daemon/src/server/spawn.rs:161-200`.

## Key Patterns

- Existing session and runtime apps already expose useful library entrypoints, so W1 can bind existing `Args` types instead of copying Clap trees.
- The current CLI client path is socket based. `internal/session/app/src/cli/client.rs:14-17` always sends requests to a live daemon endpoint derived from environment.
- Identity audit query support already exists. `crates/lilo-im-store/src/lib.rs:14-21` exposes `query_audit`, and `crates/lilo-im-store/src/sqlite/audit.rs:34-64` exposes filters plus the sink read method.
- Existing integration fixtures are DB oriented. `tests/integration/src/lib.rs:27-37` opens a fresh `LiloDb`, but does not start a CLI binary or daemon process.

## Detailed Findings

### codex-F1: Gate review status is selector incompatible

- Linear evidence: `ALP-2897` live status is `Backlog`.
- Linear body evidence: `ALP-2897` says status stays `Backlog` until review passes.
- Workflow contract: the selector compatible gate uses `Todo` for pre approval and `Worker Done` for accepted authorization.

Risk: Nancy may fail to treat the issue as the pending gate review or may route the authorization state incorrectly.

Required change: set the pending gate status and body to `Todo` until MoE signoff. Use `Worker Done` only after the gate is accepted.

### codex-F2: W4 hides the identity daemon wire contract

- Existing daemon server evidence: `internal/session/daemon/src/server.rs:76-100` extracts peer principal, then deserializes only `SessionRpc`.
- Existing protocol evidence: `internal/session/core/src/proto/rpc.rs:16-36` has no `whoami`, `identity`, or `audit` request variants.
- Existing store evidence: `crates/lilo-im-store/src/lib.rs:14-21` already exposes audit query.
- Existing peer credential evidence: `crates/lilo-im-core/src/peer_creds.rs:12-44` extracts credentials from a Unix stream. The server side sees the caller principal.

Risk: `lilo identity whoami|audit` cannot be daemon gated by current code without adding a new request and response path. W4 says the commands are through the daemon, but does not explicitly authorize the wire shape, daemon handler tests, or response types.

Required change: amend W4 to explicitly add identity read RPC and response types, daemon handler tests, and the CLI client path. The handler should use server side peer credentials for `whoami` and the existing store query for `audit`.

### codex-F3: ALP-2894 is an open child outside the gate Execute set

- Linear evidence: `ALP-2894` is a live `Backlog` child of `ALP-2901`.
- Gate evidence: `ALP-2897` Execute lists `ALP-2898, ALP-2899, ALP-2900, ALP-2901, ALP-2902, ALP-2903`, omitting `ALP-2894`.
- Worker evidence: `ALP-2901` says it subsumes `ALP-2894`.

Risk: an open sub issue can survive outside the closed authorized execution set, creating selector drift or closeout ambiguity.

Required change: before authorization, close or cancel `ALP-2894` as superseded by W4, or make its terminal handling explicit in W4 closeout before W4 reaches `Worker Done`.

### codex-F4: PER does not mirror W1 through W5 acceptance

- Linear evidence: `ALP-2903` has three acceptance bullets.
- Worker evidence: W1 through W5 acceptance spans generated surface guards, no duplicated args, all session verbs, raw runtime absence from sessions, identity CLI snapshots, daemon `--wait`, bin deletion, boundary regression, and full gates.

Risk: the PER can pass without replaying every worker acceptance surface.

Required change: expand `ALP-2903` acceptance into a falsifiable W1 through W5 matrix, or explicitly require bullet by bullet replay of every worker acceptance item with exact command output.

### codex-F5: W2 and W3 ask for CLI level DB assertions without naming a usable harness

- CLI client evidence: `internal/session/app/src/cli/client.rs:14-17` sends to a live daemon socket only.
- Integration fixture evidence: `tests/integration/src/lib.rs:27-37` opens DB state only.
- Current `lilo` test evidence: `crates/lilo/tests/version.rs` is the only binary integration test in `crates/lilo/tests`.
- Existing DB contract evidence: `tests/integration/tests/session_spawn_contract.rs:91-114` proves raw runtime table separation by direct inserts, not by the `lilo` CLI path.

Risk: W2 and W3 acceptance requires row and audit assertions for `lilo run`, `lilo create session`, and raw `lilo runtime spawn`, but the issues do not name the daemon or CLI harness needed to execute those assertions before W5.

Required change: add explicit W2 and W3 test surface or harness requirements, or move row level DB and audit assertions solely to W5 boundary regression while W2 and W3 prove dispatch to `SessionRpc` and `RuntimeRpc`.

## Dependencies

- `clap`: CLI parsing and subcommand derive.
- `tokio`: async runtime, Unix sockets, process and signal handling.
- `sqlx`: SQLite persistence for identity, runtime, and session state.
- `lilo-im-core`: principal, action, audit, and peer credential contracts.
- `lilo-im-store`: audit persistence and query API.
- `lilo-session-core`: `SessionRpc`, request, and response contracts.
- `lilo-runtime-daemon`: raw runtime lifecycle and shim handling.

## Relevance to Helioy

This review protects Nancy selector correctness and the unified `lilo` CLI boundary before autonomous execution. The main reusable lesson is that command surface reviews need both Linear shape proof and current protocol proof. A worker body that names a daemon gated command should name the wire contract it must add when no current RPC exists.

## Open Questions

- Should `ALP-2894` be canceled immediately as superseded by W4, or kept as a linked historical source after W4 closes it?
- Should W2 and W3 carry their own daemon backed CLI harness, or should all row and audit proof be centralized in W5 boundary regression?
- Should the identity CLI reuse `SessionRpc` for local daemon reads, or should Phase 6 introduce a separate identity operator RPC namespace behind `lilo identity`?

## Verify Round 1

On the `VERIFY v1` request for topic `alp2816-review-pass1`, live Linear was re-read for `ALP-2903`, `ALP-2901`, `ALP-2902`, `ALP-2899`, `ALP-2900`, and `ALP-2894`.

The applied edits resolved the original content gaps in PER, W2, W3, W4, W5, and canceled `ALP-2894`. A remaining structural blocker was found: `ALP-2901` itself was also in `Canceled` state, with `canceledAt` set to `2026-05-28T19:26:55.287Z`, while `ALP-2902` still has `ALP-2901` in `blockedBy` and the Phase 6 gate still depends on W4 execution. An `E` message was sent on the bus asking the orchestrator to restore `ALP-2901` to `Backlog` and keep only `ALP-2894` canceled.

## Verify Round 2

On `VERIFY v2`, live Linear was re-read for `ALP-2904` children, `ALP-2901`, and `ALP-2894`.

Verification evidence:

- `ALP-2904` children are exactly the six Phase 6 execution issues: `ALP-2898`, `ALP-2899`, `ALP-2900`, `ALP-2901`, `ALP-2902`, and `ALP-2903`.
- All six execution children are `Backlog`.
- `ALP-2901` is restored to `Backlog` with no `canceledAt`.
- `ALP-2894` remains `Canceled` and has no parent.

A clean `V` sign-off was sent on helioy-bus topic `alp2816-review-pass1` for the Phase 6 worker set under `ALP-2816`.
