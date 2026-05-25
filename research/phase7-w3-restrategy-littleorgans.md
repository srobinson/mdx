---
title: Phase 7 W3 Re strategy for littleorgans
type: research
tags: [littleorgans, phase7, w3, daemon, lilo, rust]
summary: ALP-2863 Pass 6 locks lilo-wire, SessionRpc, Service handle_rpc dispatch, compose owned IO, and two checked ALP-2859 commits.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-27
updated: 2026-05-27
---

## Executive Summary

ALP-2859 is the critical worker that merges runtime, session, and identity into one `lilod` process while landing the `~/.lilo/` cutover and R11 transaction model. ALP-2863 Pass 6 now binds W3 to two checked commits: Commit 1 for structural composition and Commit 2 for R11 behavior.

The current Commit 1 directive keeps one `lilod.sock`, adds a new internal `lilo-wire` crate with `LilodRpc::{Session(SessionRpc), Runtime(RuntimeRpc)}`, renames session `RpcRequest` to `SessionRpc`, evolves `RuntimeService` and `SessionService` into dispatch handles with `handle_rpc`, and keeps compose responsible for accept, peer credentials, wire IO, cancellation, and shutdown ordering.

## Project Metadata

- Language: Rust 2024, toolchain 1.95, Cargo resolver 3. See `Cargo.toml:1-35` and `rust-toolchain.toml:1-3`.
- Workspace: 333 indexed files, 42,057 LOC by fmm. Public crates live under `crates/`; private substrate crates live under `internal/`.
- Build surface: `just check`, `just build`, and `just test` are the operator gates. `just test` uses cargo nextest through `scripts/changed-crates.sh`; `just regression` runs the full workspace gate. See `justfile:35-53` and `justfile:138-154`.
- Current branch: `nancy/ALP-2817` at `3d78f4e`. `git status --short --branch` showed no dirty files before Commit 1 design work.
- Preserved attempt: `reference/ALP-2859-attempt-1` at `9d49e84`, 12 files, 175 insertions, 65 deletions. It is a salvage source, not the active working tree.
- Bus consensus: I filed `D` as message `049fbfd9-75a8-4d9f-a91b-227da6e8f54a`, then signed off on the peer adjusted strategy with `S` as message `578057bc-f568-4aba-840f-de2f7559bb27`.

## Architecture

### Locked design substrate

Phase 7 composes one daemon process with one SQLite pool and one Unix socket. The synthesis locks a single merged `lilod` with one Tokio runtime, one socket, one pid file, one log file, one SQLite ownership plan, and identity gating in front of every RPC (`littleorgans-monorepo-migration--synthesis.md:113-130`). R11 locks one shared `LiloDb`, no transaction across side effects, session spawn Tx A, runtime side effect, Tx B, raw runtime spawn with no session row and no intent row, d9 post commit append, and pending intent reconciliation (`littleorgans-monorepo-migration--synthesis.md:356-367`, `littleorgans-monorepo-migration--synthesis.md:488-499`).

ALP-2863 adds binding details that matter for W3: compose accepts peer credentials once, service factories consume the W2 shared pool, `lilo daemon start | stop | status` is absorbed into W3, d9 appends only after Tx B, `rtm` and `sm` remain installable during Phase 6, and W3 owns specific harness rewrites.

### Current code shape

- `internal/db/src/lib.rs` exposes `LiloDb` with `open`, `open_path`, `from_pool`, and three substrate accessors over one `SqlitePool` (`internal/db/src/lib.rs:20-69`).
- W2 service factories exist but only preserve config and database handles. `RuntimeService::build` validates config and stores `DaemonConfig` plus `LiloDb`; `RuntimeService::run` calls `run_daemon_with_db` (`internal/runtime/daemon/src/service.rs:39-51`). `SessionService::build` stores `SmPaths` plus `LiloDb`; `SessionService::run` calls `run_daemon_with_db` (`internal/session/daemon/src/service.rs:40-52`).
- The W3 diff adds `RuntimeServer` and `SessionServer` dispatch wrappers. `RuntimeServer::start` builds `ServerState`, runs startup reconcile, and exposes `handle_rpc` (`internal/runtime/daemon/src/server/runner.rs:19-35`). `SessionServer::start` builds `DaemonState`, lifecycle task, and runtime event task, then exposes `handle_rpc` (`internal/session/daemon/src/server.rs:26-61`). These are dispatch handles, not servers, because compose would own the listener.
- The top level `lilo` binary already parses a `daemon` command, but `Cli::run` only executes `doctor`; all other commands return not implemented (`crates/lilo/src/cli/mod.rs:69-74`). `crates/lilo/Cargo.toml` currently depends only on `clap`, `lilo-common`, `serde`, and `serde_json` (`crates/lilo/Cargo.toml:15-20`).
- The runtime CLI still owns `rtm daemon start | stop | status` through `internal/runtime/app/src/cli/daemon.rs`. Start calls `lilo_runtime_daemon::DaemonConfig::from_env()` and `run_daemon` (`internal/runtime/app/src/cli/daemon.rs:16-29`).
- The session CLI still owns `sm daemon start | stop | status` through `internal/session/app/src/cli/daemon.rs`. Start launches the current executable with `__smd` (`internal/session/app/src/cli/daemon.rs:26-67`).

## Consensus Update

ALP-2863 was updated after the initial re strategy. The binding shape now uses a new `internal/wire` crate named `lilo-wire` for `LilodRpc`, not `lilo-rm-core`, because session core already depends on runtime core and putting the envelope in runtime core would reverse the direction.

The binding shape also keeps the W2 service names. `RuntimeService` and `SessionService` gain `handle_rpc` and own startup state setup. Compose still owns accept, peer credentials, wire IO, cancellation, and shutdown ordering. `RuntimeServer` and `SessionServer` wrappers from attempt 1 must not be reintroduced.

## Key Patterns

### One request envelope, raw typed responses

Runtime and session request enums share tags such as `spawn`, `nudge`, `capture`, `doctor`, and `mcp_bridge` (`crates/lilo-rm-core/src/proto.rs:83-125`, `internal/session/core/src/proto/rpc.rs:42-62`). A one socket compose listener cannot safely sniff unwrapped JSON to choose a substrate.

The current diff adds `RpcRequestEnvelope` only to session core (`internal/session/core/src/proto/rpc.rs:17-37`). Session clients write that envelope and read a raw `RpcResponse` (`internal/session/daemon/src/socket.rs:7-28`). Runtime clients still write raw `RuntimeRpc` and read raw `RuntimeResponse` (`crates/lilo-rm-client/src/lib.rs:269-285`). That is a half migration.

Recommended pattern: one generic request envelope shared by both clients, with raw substrate responses preserved. This keeps response handling small while making request routing explicit.

### Compose owns IO and cancellation

Rust convention guidance says to read existing crate shape, avoid duplicate paths, and generalize only when a second caller needs it (`rust-conventions-2026.md:16-31`, `rust-conventions-2026.md:151-158`). W2 created `RuntimeService` and `SessionService` facades, and the W3 diff adds `RuntimeServer` and `SessionServer` dispatch state. Keeping both layers is duplication.

Current binding: compose owns accept loops, peer credential extraction, substrate envelope decode, response write, and cancellation. `RuntimeService` and `SessionService` become the dispatch state shape with `handle_rpc`; `RuntimeServer` and `SessionServer` wrappers are discarded.

### R11 lives in the session use case, not compose

The existing session spawn use case is already in `internal/session/daemon/src/handler/spawn.rs:17-104`. It authorizes, validates, launches through the driver, builds a `Session`, and inserts the session row. Runtime spawn state changes live in `SpawnCoordinator::begin_spawn` and `record_running` (`internal/runtime/daemon/src/server/spawn.rs:28-53`, `internal/runtime/daemon/src/server/spawn.rs:143-177`). Session row insertion is a plain store method today (`internal/session/store/src/sqlite/sessions.rs:33-74`).

Recommended pattern: keep two phase session spawn in the session daemon spawn path. Add transaction capable store helpers for Tx A and Tx B, call the runtime dispatch handle for the side effect, and leave raw runtime spawn in the runtime service with no intent and no session row.

## Detailed Findings

### 1. Routing strategy

Recommendation: keep the one socket design and fix the envelope, rather than adding a second socket.

Reasoning:

- One socket is part of the Phase 7 simplification and keeps `LILO_SOCKET_PATH` as the single daemon socket override.
- Two sockets preserve legacy wire types, but they introduce a second path contract and conflict with shim bootstrap. The runtime shim currently needs a socket path in process env; Phase 7 narrows this to `LILO_SOCKET_PATH` only.
- A session only socket with runtime tunneled through session verbs is larger than W3 because it invents a new runtime operator API inside session protocol.
- Sniffing unwrapped requests is unsafe because the runtime and session protocols overlap on request tags.

The current W3 diff should salvage newline JSON framing and `DaemonConfig::from_lilo_paths`, but replace `RpcRequestEnvelope` with a shared generic request envelope. Runtime client write logic at `crates/lilo-rm-client/src/lib.rs:273-277` must send the envelope too.

### 2. Service factory boundary

Current binding: keep `RuntimeService` and `SessionService` as the one dispatch state shape. Add `handle_rpc` to each and move start time state setup into the service construction path.

Attempt 1 introduced `RuntimeServer` and `SessionServer`, but those wrappers did not bind listeners and duplicated the W2 service names. The updated gate deletes those wrappers. Existing `run_daemon_with_db` paths can remain only as compatibility entry points while they delegate through the same service state, until obsolete substrate daemon launch paths are removed.

Better separation:

- `compose.rs`: listener, envelope, peer credentials, cancellation, shutdown ordering.
- `RuntimeService` and `SessionService`: build dispatch state from shared `LiloDb` and expose `handle_rpc`.
- Legacy `run_daemon_with_db`: temporary compatibility only, no second dispatch implementation.

### 3. Two phase session spawn placement

Recommendation: implement in `internal/session/daemon/src/handler/spawn.rs`, split into helpers if the function approaches 150 LOC.

The transaction sequence is a session use case because it creates session records and session intents. Compose should not know session table details. The runtime side effect should be a concrete call into the runtime dispatch handle, not a new trait unless a second real implementation appears.

Required store work:

- Tx A helper writes identity audit allow row, `session_spawn_intents(pending)`, and runtime lifecycle Forking in one transaction.
- Runtime side effect launches the runtime without any SQLite transaction open.
- Tx B helper inserts `session_sessions`, updates lifecycle Running, and resolves intent.
- Raw `lilo runtime spawn` remains under runtime dispatch and writes only runtime lifecycle state.

### 4. d9 JSONL deduplication

Recommendation: add an explicit dedup aware append wrapper near the runtime event log append site.

`EventLog::append` writes the JSONL row, pushes into memory, and notifies immediately (`internal/runtime/daemon/src/event_log.rs:86-107`). `append_with_ts` has the same immediate push shape (`internal/runtime/daemon/src/event_log.rs:163-183`). Runtime `record_running` calls `state.append_event(event).await?` directly after updating lifecycle (`internal/runtime/daemon/src/server/spawn.rs:169-176`).

W3 needs a post Tx B append path keyed by `(session_id, event_kind)`. This should be a small explicit API, not implicit discipline across call sites.

### 5. Test harness scope

Recommendation: keep the W3 harness rewrites in W3. Defer only new cross substrate scenario coverage to W4.

The enumerated harnesses are not procedural ceremony. They still encode old daemon and env assumptions:

- Runtime app harness creates `rtm.sock`, `rtm.sqlite`, `rtm-home`, then starts `rtm daemon start` with `RTM_SOCKET_PATH`, `RTM_DB_PATH`, and `RTM_HOME` (`internal/runtime/app/tests/common/harness.rs:59-91`, `internal/runtime/app/tests/common/harness.rs:346-372`).
- Docker e2e uses `CARGO_BIN_EXE_rtm` and sets the same old env vars (`internal/runtime/app/tests/docker_e2e.rs:293-300`, `internal/runtime/app/tests/docker_e2e.rs:309-339`).
- Session daemon rtmd harness starts `rtm daemon start` with old runtime env vars (`internal/session/daemon/tests/rtmd_driver.rs:213-234`).
- `IdentityClient::connect` still opens a `LiloDb` from a path, creating a parallel entry beside the shared pool path (`internal/session/daemon/src/identity_client.rs:46-54`).
- `SqliteStore::open_temp` already uses `LiloDb` and can be the sqlx backed test replacement (`internal/session/store/src/sqlite.rs:34-40`).

### 6. Worker decomposition

Consensus recommendation: do not split W3 into new Linear workers. The stuck state is caused by unresolved socket routing, not by an inherently bad bundle. Splitting would require gate amendments and extra review cycles.

Implementation should still be sequenced in focused commits:

1. Symmetric request envelope and client cutover.
2. Compose listener plus `lilo daemon` CLI.
3. Path and env cutover plus harness rewrites.
4. R11 session spawn transactions, raw runtime discriminator, d9 dedup, and reconciliation hooks.

The current diff starts transport and wrappers but leaves the R11 core untouched. Resolve Q1 first, then finish the natural W3 bundle.

## Dependencies

Critical dependencies and their roles:

- `sqlx`: shared async SQLite pool and transaction foundation for `LiloDb` and R11.
- `tokio`: Unix sockets, async IO, process handling, broadcast channels, and task orchestration.
- `nix`: peer credential extraction and daemon stop signals.
- `lilo-rm-core`: runtime wire types plus current newline JSON helpers used by runtime and session code.
- `lilo-rm-client`: runtime client write path that must join the request envelope if one socket remains.
- `lilo-session-core`: session RPC types and CLI protocol surface.
- `lilo-paths`: authoritative `LILO_HOME`, `LILO_SOCKET_PATH`, `lilod.sock`, pid, database, and log path derivations.

## Verification Performed

Commands run during this review:

```bash
cargo check --workspace
cargo test --workspace --no-run
```

Both completed successfully on the current uncommitted W3 diff.

The W3 landing gate should still include:

```bash
cargo test -p lilo-session-daemon -p lilo-runtime-app -p lilo-session-store -p lilo-runtime-store -p lilo-im-store
rg -n "RTM_HOME|RTM_SOCKET_PATH|RTM_DB_PATH|SM_HOME|SM_SOCKET_PATH|SM_DB_PATH|SM_NAMESPACE|AGM_HOME" crates internal docs README.md justfile
# plus the trap guarded LILO_HOME daemon smoke from ALP-2859
just check && just build && just test
fmm generate && fmm validate  # if files move or exports change
```

The env grep must allow only intentional negative tests or legacy fixture captures.

## Relevance to Helioy

This is the core local control plane merge for littleorgans. The recommendation keeps the K8s shaped mental model: `lilo` as kubectl, session as API server boundary, runtime as kubelet shaped executor, and identity as the front door authorizer. It also preserves the v1 local first constraint by avoiding transport scope and by keeping R11 in SQLite plus reconcile form.

## Open Questions

No open question in the Commit 1 Phase A design message. The updated gate resolved the envelope home as `internal/wire` and the dispatch shape as Service with `handle_rpc`.

## Bus Outcome

The W3 re strategy reached warroom consensus after both panes filed `S` sign offs. The orchestrator acknowledged consensus on topic `w3-restrategy` and is synthesizing the direction for Stuart.

## Commit 1 Phase A Update

Mail directive `w3-c1-structural` assigned this pane as engineer for ALP-2859 Commit 1. Required live checks passed before filing D:

```bash
git log -1 --oneline
# 3d78f4e nancy[ALP-2862]: Drop unused store constructor aliases

git status --short --branch
# ## nancy/ALP-2817

fmm validate
# All 333 files are indexed and up to date

cargo check --workspace
# Finished dev profile successfully
```

I read live ALP-2863 and ALP-2859 bodies, confirmed no Linear comments on either issue, checked fmm outlines for the service, server, RPC, and CLI seams, and inspected the three salvage pieces from `reference/ALP-2859-attempt-1` at `9d49e84`:

- `DaemonConfig::from_lilo_paths(&LiloPaths)` in `internal/runtime/daemon/src/server/config.rs`.
- Newline JSON migration in `internal/session/daemon/src/socket.rs`.
- `internal/session/app/Cargo.toml` additions for `lilo-paths`, `lilo-db`, and `lilo-runtime-daemon`.

Phase A design was filed on bus topic `w3-c1-structural` as message `20186602-7b2f-44ff-a1bd-d3a6f6d9e47e`. The orchestrator milestone ack was sent as `a8170f33-6eac-404a-874e-c286ce0d0e3e`. Implementation is waiting for reviewer Phase A `S` or `B`.

## Commit 1 Phase A Block and Revised D

Reviewer blocked the first Phase A D with one valid omission. The original path list did not explicitly include deletion of the existing per substrate daemon surfaces. I validated the block with fmm:

- `internal/runtime/app/src/cli/daemon.rs:8-29` defines `DaemonCommand` and still calls the runtime daemon path.
- `internal/runtime/app/src/cli.rs:7-36` registers the runtime `daemon` module and `Command::Daemon` variant.
- `internal/session/app/src/cli/daemon.rs:13-102` still implements `sm daemon start`, `stop`, and `status` behavior.
- `internal/session/app/src/cli/cli_def.rs:28-75` registers `Command::Daemon`, `Command::InternalDaemon`, `DaemonArgs`, and `DaemonAction`.
- `internal/session/app/src/lib.rs:19-43` routes `Command::Daemon` and `Command::InternalDaemon`.
- `internal/runtime/app/src/cli/output.rs:82-93` and `247-258` still name `rtm daemon start` in missing daemon copy and its test.

Revised Phase A D was filed as bus message `3dd223dc-5bd3-4b94-91ed-de7d8f9a9338`, superseding `20186602-7b2f-44ff-a1bd-d3a6f6d9e47e`. The revised D adds deletion of `internal/runtime/app/src/cli/daemon.rs` and `internal/session/app/src/cli/daemon.rs`, clap and router scrubs, removal of hidden `__smd`, copy updates to `lilo daemon start`, and a falsifiable grep:

```bash
git grep -nE 'DaemonCommand|__smd|"rtm daemon"|"sm daemon"' internal/{session,runtime}/app/ crates/
```

The orchestrator milestone ack for the revised D was `cd6cc367-2a3d-4887-be3f-3522ad3ac4e0`. A follow up inbox poll for `w3-c1-structural` returned no new messages, so Phase A is waiting for reviewer sign off or another block.

## Commit 1 Phase A Cleared, Implementation Reassigned

A fresh inbox check received reviewer sign off:

```text
S|A|I sign off on the proposed W3 Commit-1 structural refactor as filed
```

The orchestrator then declared Phase A clear and instructed implementation on `nancy/ALP-2817`, with no push until Commit 2 lands. This pane is constrained by codebase analyst read only policy, so I did not modify the target codebase. I sent exception message `cf477fde-d429-4779-8c5c-dcde74deb51f` on `w3-c1-structural`, stating that Commit 1 implementation must move to an edit authorized engineer pane. A follow up topic poll returned no new messages.

## Commit 1 Engineer Role Reassignment

A fresh double inbox check for two `you have mail!` nudges returned two messages, then an empty second poll. Reviewer pane 9:6.1 routed my exception to the orchestrator and confirmed both 9:6.1 and 9:6.2 are `helioy-tools:codebase-analyst`, so Commit 1 implementation is incompatible with either pane's read only role. The orchestrator acknowledged the exception, released this pane from the engineer role, and is spawning a write authorized `helioy-tools:backend-engineer` pane on Codex runtime.

No further D is required from this pane. The Phase A sign off on D2 `3dd223dc-5bd3-4b94-91ed-de7d8f9a9338` carries forward to the new engineer pane. This pane remains available only as read only second pair of eyes for Phase B review.
