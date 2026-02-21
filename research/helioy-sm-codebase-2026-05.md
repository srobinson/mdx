---
title: session-matters v1 codebase review (2026-05)
type: research
tags: [session-matters, sm, smd, rust, control-plane, codebase-review, mcp, websocket, controller-conventions, helioy]
summary: A− grade for session-matters v0.1.2. Ten of twelve draft features shipped end-to-end through a unix-socket stdio MCP bridge; the WebSocket upgrade brief never bound because v1 ships no HTTP listener; no centralised SessionCondition exists yet (state set inline in four sites).
status: active
source: codebase-analyst
confidence: high
project: session-matters
created: 2026-05-18
updated: 2026-05-18
related: [berriai-litellm-agent-platform, kubernetes-sigs-agent-sandbox, helioy-controller-conventions, transport-matters-ws-upgrade-brief, session-matters-foundation-draft]
---

# session-matters v1 codebase review (2026-05)

## 1. Snapshot

Repo: `~/Dev/LLM/DEV/helioy/session-matters/`. Crate version `0.1.2` published 2026-05-17 (CHANGELOG.md:3, .release-please-manifest.json). Reviewed at HEAD `c0c62d1` (chore(main): release 0.1.2 [#4]). Five-commit history: `65a2552 batshit` → `be655b5 feat: ship session-matters v1 (#1)` → `a034dff chore(main): release 0.1.1` → `03a2402 fix: drop unsupported Windows release target` → `c0c62d1 chore(main): release 0.1.2`. So v1 landed as a single bundled PR; everything else is release-please plumbing.

Workspace layout (`Cargo.toml:1-9`): Rust 2024, resolver "3", five crates under `crates/`. Total Rust source ~4.7K LOC + ~3K LOC tests + ~1.7K LOC generated. Hand-written source files all sit comfortably under Stuart's 700 LOC limit; the two largest are `sm-daemon/src/mcp_bridge.rs` at 608 and `sm-store/src/sqlite/sessions.rs` at 533 (sessions.rs includes 263 LOC of inline tests). Daemon integration test `crates/sm-daemon/tests/handler.rs` is 683 LOC.

| Crate | LOC | Role |
|---|---|---|
| `sm-core` | 1,154 | Domain types (`Session`, `Selector`, `Mail`, `Label`), JSON-RPC envelopes, RPC request/response enum, `tools.toml` contract registry, `SmPaths`. No IO. |
| `sm-store` | 905 | `rusqlite`-backed `SqliteStore`. Sessions / mail / labels submodules. Hand-rolled additive `ALTER TABLE` migrations (sqlite/mod.rs:38). |
| `sm-driver` | 363 | `SpawnDriver` trait plus `InProcessDriver` (forkpty + waitpid + SIGCHLD). Owns the pty fd; pid registry is a `Mutex<HashMap>`. |
| `sm-daemon` | 1,915 | Long-running `smd`. Unix socket server, JSON-RPC dispatch, identity client, lifecycle reaper thread, reconcile thread, MCP-over-socket bridge, agent-config loader, polish (link / logs / wait / doctor). |
| `sm-cli` | 2,056 | The `sm` binary plus stdio MCP bridge plus per-tool CLI handlers, plus `build.rs` codegen from `tools.toml` and 14 generated schema JSON files. |

Dep stack at a glance (`Cargo.toml:17-40`): `tokio`, `serde`/`serde_json`, `clap`, `rusqlite` (bundled), `uuid` v7, `chrono`, `nix` 0.30, `thiserror`, `toml`, `indexmap`. External Helioy crates: `lilo-im-core`, `lilo-im-store`, `lilo-im-stub` (all `0.1`, published from identity-matters under the `lilo-` family per LESSONS.md:5). cargo-dist 0.31, release-please. No `axum`, no `hyper`, no `tokio-tungstenite`, no `sqlx`.

CI matrix (`.github/workflows/ci.yml`) runs `just check` (fmt + clippy + LOC limit) + `just build` + `just test --profile ci` + `just test-doc` + a `git diff --exit-code README.md` parity gate on every push to main and every PR, across ubuntu-latest and macos-latest.

## 2. Grade

**A−.** All ten v1 success criteria from the draft are covered by code paths and there are integration tests for every MCP tool and audit trail. The minus is for three observable misses: SPAWNING state is documented but never written (sessions go straight to RUNNING); the centralised `compute_session_condition()` pattern from the draft's "External validation" section was not adopted; and the WebSocket-upgrade work the transport-matters brief recommended is wholly absent because v1 ships no HTTP listener.

## 3. What actually shipped vs the draft

| Draft feature | Status | Where |
|---|---|---|
| `smd` daemon (unix socket, sqlite, MCP) | Shipped | `sm-daemon/src/server.rs:16-43` |
| Session record (UUIDv7, state, lifecycle timestamps) | Shipped, slimmer than draft | `sm-core/src/types.rs:82-99` |
| Selector grammar (id / label= / label in / workspace / role / all) | Shipped, full set | `sm-core/src/types.rs:162-193` |
| Strict-only membership | Shipped; only `Spawn` writes | `handler.rs:128-132` |
| Spawn flow with identity authorize before driver call | Shipped | `handler.rs:98-108` |
| Mail durable + nudge surface | Shipped (nudge stubs `delivered: false`) | `sm-driver/src/inprocess.rs:156-162` |
| `sm logs`, `sm link`, `sm wait`, `sm doctor` | Shipped | `sm-daemon/src/polish.rs:17-176` |
| `tools.toml` codegen (MCP schema + CLI help + SKILL + README) | Shipped | `sm-cli/build.rs:17-73` |
| Reconciliation loop, 30s cadence | Shipped | `reconcile.rs:12,54-87` |
| MCP server hosted by smd | Shipped via unix-socket `McpBridge` proxy | `mcp/server.rs:7-36`, `mcp_bridge.rs:16-31` |
| identity-matters as in-process trait | Shipped via `lilo-im-stub::StubAuthorizer` | `identity_client.rs:48-60` |
| 14 MCP tools (`agent_run` … `doctor`) | Shipped, exact names | `mcp/tools/mod.rs:1-16` |
| 50ms `sm mail check` budget | Enforced as a test | `benches/hot_path.rs:12,21-23` |
| `--detach` returns when RUNNING | Parsed and ignored ("attached mode deferred in pass 1") | `cli/run.rs:10-12` |
| SPAWNING state in the lifecycle | Defined, never written; spawn jumps to RUNNING | `types.rs:47-52`, `handler.rs:116` |
| Centralised `compute_session_condition()` | Not adopted | scattered (§7) |
| runtime-matters socket boundary | Substituted by `SpawnDriver` trait in-process; trait shape preserves the future split | `sm-driver/src/driver.rs:60-78` |
| `sm daemon start / stop / status` | Shipped (draft undecided) | `cli/daemon.rs:13-23` |
| `__smd` hidden subcommand exec-spawned by parent CLI | Shipped, not in draft | `cli_def.rs:37-38`, `cli/daemon.rs:40` |
| `agent_label` MCP tool | Shipped, not in draft list | `mcp/tools/mod.rs:6` |
| Additive sqlite migration (Pass-1 → current) | Shipped, not in draft | `sqlite/mod.rs:38-63` |

## 4. Primitives that landed

### From berriai-litellm (cm `019e34ba`)

- **Diagnose super-bundle pattern.** `sm doctor` reconciles, lists LOST sessions, and reports driver status in one call (`polish.rs:90-128`). Departure: BerriAI's `/diagnose` is HTTP; smd's is a daemon RPC.
- **Single source of truth for MCP / CLI / SKILL / README.** `tools.toml` parsed in `sm-core::tool_contracts::contract_registry()` (tool_contracts.rs:13-18) and again in `build.rs` via `include_str!` (sm-cli/src/tool_contracts.rs:9). Generated outputs span four targets (build.rs:30-72). Parity enforced in CI (`git diff --exit-code README.md`).
- **Audit log on every authorized call.** Every `DaemonState::*` mutation goes through `identity.authorize()`, which writes a `lilo_im_store` audit row via `StubAuthorizer` (identity_client.rs:48-60). Tests assert the row sequence (handler.rs:531-541). Deny path audits without mutating store (handler.rs:545-590).
- **Server-proxy WS workaround.** Not landed; no WS surface (§6).

### From kubernetes-sigs/agent-sandbox (cm `019e3784`)

- **Adoption-vs-creation three-way check (Convention 2).** Non-CRD form: `InProcessDriver::probe_session()` returns `verified: false, evidence: "session is not owned by this daemon"` when the id is not in the driver registry (`inprocess.rs:99-104`). `delete_one` surfaces the same distinction via `Option<ChildExit>` (`handler.rs:299-308`). Moral equivalent of `OwnedByThis | Unowned | OwnedByOther` in a unix-process registry.
- **Label-selector predicate (Convention 5).** SQL selector compiler in `sm-store/src/sqlite/sessions.rs:78-115`. `label:area in (auth, ui)` generates a parameterised IN clause (`query_label_in_sessions`, sessions.rs:117-140).
- **Non-destructive defaults (Convention 6).** `peek: false` marks read; `peek: true` keeps unread (handler.rs:362, sqlite/mail.rs:48-66). `mail_send` to unknown recipient errors (handler.rs:485-489). `agent_delete` default grace 5s (cli_def.rs:94).
- **Tagged JSON discriminator.** `RpcRequest` / `RpcResponse` use `#[serde(tag = "type", rename_all = "snake_case")]` (proto.rs:253, 273). Round-trip tested at proto.rs:297-366.
- **Status / condition surfaced through one verb.** `sm doctor` returns `status: "ok"|"degraded"` plus `findings` (polish.rs:115-128). Flat rather than a typed Conditions slice.

### Helioy controller-conventions doc (`helioy-controller-conventions.md`)

v1 smd ships no CRDs and no k8s watches, so conventions 1, 4, 5 do not bite. Conventions 2 (three-way ownership) and 6 (non-destructive defaults) already informed v1 design as noted above. Convention 3 (`Option<bool>`) does not appear; no opt-in-default fields exist in the v1 schema. See §8.

## 5. Primitives missing

| Primitive | Status |
|---|---|
| Centralised `compute_session_condition()` | **Oversight.** Draft's external-validation section called for this; v1 sets state inline in four sites. See §7. |
| SPAWNING state in practice | **Deferred.** Defined in the enum (types.rs:48), never assigned. Spawn jumps straight to RUNNING because `InProcessDriver::spawn` returns synchronously from forkpty (`handler.rs:116`). |
| `--detach` semantics | **Deferred.** `run.rs:10-12` prints "attached mode is deferred in pass 1; leaving session detached". Today every spawn is detached; the flag is parsed and ignored. |
| Three WS routes from the draft (`/mcp`, `/attach/:session_id`, `/logs/:session_id?follow=true`) | **Superseded.** v1 uses stdio MCP, no `/attach`, and `sm logs --follow` tails the transcript file directly from the CLI process (`sm-cli/src/cli/logs.rs:42-61`). See §6 + §10. |
| MCP Streamable HTTP transport | **Superseded.** v1 uses stdio MCP routed through a unix-socket `McpBridge` RPC; see §6. |
| `axum` / `hyper` upgrade-aware-middleware fixture | **Not applicable.** No axum, no hyper. |
| Reconciliation cadence open question | **Resolved.** Hybrid: reconcile-once on startup (`server.rs:33`) plus a 30s loop (`reconcile.rs:12`), plus on-demand reconcile inside `doctor` and `wait` (`polish.rs:98`, `polish.rs:134`). |
| Cross-machine federation | Out of scope per draft; correctly absent. |
| Web UI | Out of scope per draft; correctly absent. |
| Per-host substrate split (smd ↔ rtmd over local socket) | **Deferred.** The `SpawnDriver` trait preserves the future split shape, but v1 keeps the implementation in-process (driver.rs:60-78). The NOTES/daemon-architecture.md essay describes the eventual split as a planned next pass. |
| RBAC capabilities field | **Deferred** per draft (v2+); the `Session` struct correctly omits it (types.rs:82-99). |
| Reconcile cadence open question | Resolved as a hybrid (above). |

## 6. WebSocket upgrade pattern in practice

**Which option (A/B/C) did smd actually implement?** None of A/B/C. v1 ships **no HTTP listener at all**. A `grep` across the repo for `axum`, `hyper`, `tokio-tungstenite`, `tungstenite`, `WebSocketUpgrade`, `on_upgrade`, `streamable_http`, `SSE` returns zero hits.

The MCP transport is **stdio-over-unix-socket**:

- `sm mcp` (the user-facing process invoked by MCP clients) runs a stdin/stdout loop. Each line goes into a `McpBridgeRequest { line: String }` RPC, sent over the smd unix socket as a normal `RpcRequest::McpBridge`. The response line comes back the same way. See `sm-cli/src/mcp/server.rs:7-36` (`run_stdio_bridge`) and `sm-cli/src/mcp/transport.rs:3-10`.
- `smd` receives the `McpBridge` RPC, hands the line to `sm_daemon::mcp_bridge::handle_line` which parses it as `JsonRpcRequest`, dispatches to `initialize | ping | tools/list | tools/call`, and returns the encoded `JsonRpcResponse` line. `sm-daemon/src/mcp_bridge.rs:16-114`. The MCP protocol version advertised is `"2025-06-18"` (`sm-core/src/mcp.rs:4`).
- The unix-socket protocol is one-request-per-connection: client connects, writes JSON, half-closes, reads the response, daemon shuts the stream (`sm-daemon/src/server.rs:54-105`). No keepalive, no multiplexing.

Implications for the transport-matters brief:

- The "upgrade-aware-middleware fixture" was not built because there is no axum stack to test.
- No compression layer, no body-buffering risk visible (zero middleware).
- The `/mcp` route does not use Streamable HTTP nor SSE; the bridge is stdio piped through the unix socket.
- `sm attach <session>` does not exist as either a CLI command or an MCP tool. The CLI verb list in `Command` (cli_def.rs:16-39) has no `attach`.
- `sm logs --follow` reads the transcript file directly from the CLI process (`cli/logs.rs:42-61`), polling at 250ms. No streaming RPC; no WS.

The brief's recommendation (Option A) therefore remains pending. v1 deferred the entire HTTP-listener question rather than picking A/B/C. This is a clean deferral, but it means the brief should be updated to reflect that the WS surface is a future pass; see §10.

## 7. State machine for SessionCondition

**Centralised `compute_session_condition()` was not adopted.** State transitions are set inline at four sites:

1. **Spawn → RUNNING.** `sm-daemon/src/handler.rs:116` constructs the `Session` literal with `state: SessionState::Running`. SPAWNING is never written; the runtime is alive synchronously once `InProcessDriver::spawn` returns.
2. **Reap → TERMINATED.** `sm-daemon/src/lifecycle.rs:46-61` (`refresh_exits`) calls `store.mark_session_terminated()` for every child exit reported by `driver.reap_exited()`. The lifecycle thread polls every 200ms (lifecycle.rs:26).
3. **Delete → TERMINATED.** `sm-daemon/src/handler.rs:299-313` (`delete_one`) calls `driver.terminate()` then `store.mark_session_terminated()` itself, separately from the lifecycle reaper.
4. **Reconcile → LOST.** `sm-daemon/src/reconcile.rs:54-87` (`reconcile_once`) iterates RUNNING and SPAWNING sessions, calls `driver.probe_session()`, and calls `store.mark_session_lost()` on verification failure.

The store helpers `mark_session_terminated` (sessions.rs:161-180) and `mark_session_lost` (sessions.rs:182-198) hard-code the target state. There is no single function that takes inputs and returns a `Condition`; the question "what is this session's current condition?" is answered by reading the `state` column directly (e.g. `polish.rs:107`, `polish.rs:188-198`).

The draft (session-matters-foundation-draft.md:464-481) flagged centralising as a v1 recommendation. The cost the draft cited (one function, one trait) is still the same cost; the cost of not centralising will compound when SessionCondition gains additional axes (Ready vs Started vs Suspended; multi-input derivations; runtime-matters health probes once the daemon split lands). Recommend a Linear issue to lift the four inline sites behind one `compute_session_condition()` before v2 work begins. See §10.

## 8. Fit against helioy-controller-conventions

session-matters v1 does not ship CRDs, does not run a `kube-rs` controller, and does not watch any k8s API. The six conventions therefore do not bind to v1 code. Two observations:

- The Helioy translations of conventions 2 and 6 already informed the v1 shape (§4 above). The non-k8s expressions are the right scale for v1.
- Convention 4 (Server-Side Apply for status) will become load-bearing when smd's session records surface as a `Session` CRD in the k8s endgame. The current code stores `Session` in sqlite; promotion to a CRD with SSA-owned status fields is a future migration. The current `mark_session_*` setters write all status fields under one writer, which maps cleanly to a single SSA field owner (`session-matters/smd-status`) when the time comes.

There is one nascent controller shape worth noting. `ReconcileTask` (reconcile.rs:25-43) is structured exactly like a kube-rs controller loop: ticker + periodic full-list + per-item reconcile + condition write. The shape transfers directly if smd later watches a Session CRD; the loop body becomes "list CRDs, probe each, patch status".

## 9. Surprises

Clean wins the draft did not predict:

- **MCP-over-unix-socket bridge.** The `McpBridge` RPC variant (`proto.rs:230-237`, `proto.rs:268`) lets `sm mcp` be a 30-line stdio process while every MCP method lives in `smd`. Sidesteps the transport question for v1; one extra socket round-trip per request, one server hosting one auth context for all callers (peer creds extracted per connection, server.rs:55).
- **`__smd` hidden subcommand for daemon self-start.** `sm daemon start` re-exec-spawns the current binary with `__smd` (cli_def.rs:37, daemon.rs:39-47); `__smd` calls `sm_daemon::run_daemon` (lib.rs:25). No supervisor, no launchd, no extra binary.
- **Additive sqlite migration from a Pass-1 schema.** `sm-store/src/sqlite/mod.rs:38-63` adds columns with `ALTER TABLE ADD COLUMN` and backfills `started_at` from `created_at`. Migration test (sessions.rs:457-507) constructs the v0 schema and asserts upgrade. The "no backcompat" rule covers refactors of in-flight code; this additive migration for already-shipped binaries is the right exception.
- **`mail_stop_check` returns a JSON-shaped block decision and exits 2** (`cli/mail.rs:88-100`). The Claude Code stop-hook contract baked into the CLI. Useful for the helioy-bus migration: `stop-check-mail.sh` replaces one-for-one.
- **`HELIOY_SESSION_ID` env-var fallback in `sm link` and `sm mail send`** (`cli/link.rs:39-46`, `cli/mail.rs:122-124`). Draft hinted at this for hooks; the code makes it ergonomic for any CLI use.
- **`forkpty` rather than plain `fork`.** `InProcessDriver::spawn` uses `nix::pty::forkpty` (inprocess.rs:46) and keeps the master fd inside `SpawnHandle` (inprocess.rs:23-26). A future `sm attach` is cheap because the master fd is already there.
- **Universal MCP tool error envelope.** `tool_success` / `tool_error` (sm-core/src/mcp.rs:34-56) wrap every tool response. Consistent shape across all 14 tools without per-tool error code design.

Concerning hacks:

- **`run_stdio_bridge` reads one line, writes one line, in lockstep.** No batching, no notification handling. `notifications/*` methods are dropped (`mcp_bridge.rs:39-41`). Server-to-client progress notifications are not deliverable. Acceptable for v1.
- **`store: Mutex<SqliteStore>` taken on every RPC.** `DaemonState` acquires the lock inside every handler (`handler.rs:128-132`, `handler.rs:289-294`, others). Serialises every read under load. The 5ms RPC bench (`benches/hot_path.rs:13`) passes today; first contention point if load grows.
- **`HandlerResult::shutdown` flag threads through every handler.** Only `Shutdown` sets it true. A small leak of one concern into every return type; a control channel would be cleaner.
- **Reconcile and lifecycle threads use `std::thread::sleep` inside a tokio runtime** (reconcile.rs:29, lifecycle.rs:21-27). Works because the work is sync sqlite + sync `nix::sys::signal::kill`; inconsistent with the daemon's tokio model.
- **`stream.read_to_end` for every RPC request** (server.rs:71-75). Combined with half-close-after-write (socket.rs:17), fine for small JSON; breaks if a future RPC carries a streaming payload.

## 10. Recommended draft updates

### session-matters-foundation-draft.md

1. Replace draft §"v1 scope" entry `sm logs <selector>` (line 232) with a note that `sm logs` is read-only / one-shot today and `--follow` is a CLI-side file tail (no server streaming). Current text suggests a richer streaming surface than the code implements.
2. Replace draft §"CLI surface" `sm run --detach` description (line 354) with "detach mode is the only mode in v1; `--detach` is parsed and ignored. Attached mode is deferred." Quote replaced: `--detach returns once SPAWNING → RUNNING completes. Default is to block (terminal-attached for interactive use).`
3. Replace draft "Boundary contracts" §`session-matters → runtime-matters` block (lines 372-390) with a note that v1 substitutes a `SpawnDriver` trait in the same process; the local socket boundary lands in a later pass. Cite `crates/sm-driver/src/driver.rs:60-78` as the trait that preserves the future shape. The `RuntimeRpc::Spawn / Kill / Status` envelope types should be removed from the draft until they ship; the `SpawnDriver::{spawn, terminate, probe_session, nudge, reap_exited}` signatures are the v1 contract.
4. Strengthen draft §"External validation: agent-sandbox `computeReadyCondition` pattern" (lines 450-481). Quote retained: `Recommendation for v1. Adopt the centralised pattern from the start.` Suggested addendum: "v1 shipped without it. Four inline sites set `SessionState` directly: `handler.rs:116` (Running on spawn), `handler.rs:311` (Terminated on delete), `lifecycle.rs:57` (Terminated on reap), `reconcile.rs:79` (Lost on probe failure). Lift these behind one `compute_session_condition(session, last_event, probe) -> SessionCondition` before any new state-deriving inputs are added (orchestration-matters probes, identity-matters audit signals, tmux-pane reachability). Linear issue to file before v2 work begins."
5. Add a paragraph to draft §"v1 scope" noting the actual MCP transport choice: stdio bridge over the existing unix socket via a `McpBridge` RPC envelope, not a hosted MCP server inside smd. Cite `mcp_bridge.rs:16-31` and `server.rs:7-36`. This unblocks any future reader who reads the draft and looks for an axum server.
6. Remove draft §"Open questions for Linear planning" item 3 (line 440, socket path) — resolved at `~/.sm/sock` via `SM_HOME` env var or `$HOME/.sm/`, see `sm-core/src/paths.rs:16-22`.
7. Remove draft §"Open questions for Linear planning" item 8 (line 445, MCP tool naming) — already marked decided; the code matches the decided set plus the surprise addition `agent_label`.
8. Remove draft §"Open questions for Linear planning" item 10 (line 447, reconciliation cadence) — resolved as the hybrid noted in §5.
9. Add `agent_label` to draft §"CLI surface" tool list (line 322). It shipped as both `sm label` CLI and the `agent_label` MCP tool.

### transport-matters-ws-upgrade-brief.md

1. Add a status note at the top of the brief: "session-matters v1 (`0.1.2`, 2026-05-17) ships no HTTP listener and no WebSocket surface. The brief's Option A recommendation remains pending; v1 deferred the HTTP question entirely by routing MCP through stdio-over-unix-socket (`sm mcp` → `McpBridge` RPC → `smd`). The three WS routes the brief specified (`/mcp`, `/attach/:session_id`, `/logs/:session_id?follow=true`) are future passes."
2. Update brief §"Why this brief now" table (line 21-26) `Status` column: change all three rows from `v1` to `future pass — v1 ships stdio MCP bridge, no `/attach`, file-tail logs from CLI`. The rationale for Option A remains correct; the binding date moves out.
3. Update brief §"Concrete v1 work items if Option A holds" (line 113-119) intro: "These items remain the prescription for the pass that introduces smd's HTTP listener. They were not done in v1 because no HTTP listener was added."
4. Update brief §"Open questions" item 1 (line 123) to note that the choice still stands open; v1 did not lock the Streamable HTTP vs SSE question because v1 did not ship the route.
5. Add a fourth WS route to the brief's eventual implementation list: `/attach/:session_id` requires the runtime's pty master fd, which `InProcessDriver::SpawnHandle` already holds (`inprocess.rs:24`). The forkpty choice in v1 (rather than plain fork) is what makes a future `/attach` cheap. Worth flagging so the v2 attach work knows the substrate is already there.

## 11. Provenance

- Repository: `~/Dev/LLM/DEV/helioy/session-matters/`
- Version reviewed: `0.1.2` (CHANGELOG.md:3)
- Commit SHA: `c0c62d14b013c7787ac6246aa0176e96b8601911`
- Review date: 2026-05-18
- Related cm pointers:
  - `019e34ba-881f-7971-924f-a978599015c2` — BerriAI/litellm-agent-platform review (A−, 12 primitives)
  - `019e3784-2194-7b91-87ae-84e3b3545767` — kubernetes-sigs/agent-sandbox review (B+, 14 primitives)
- Related ~/.mdx pointers:
  - `~/.mdx/research/berriai-litellm-agent-platform.md`
  - `~/.mdx/research/kubernetes-sigs-agent-sandbox.md`
  - `~/.mdx/projects/session-matters-foundation-draft.md`
  - `~/.mdx/projects/transport-matters-ws-upgrade-brief.md`
  - `~/.mdx/projects/helioy-controller-conventions.md`
- Tooling note: fmm index exists at `session-matters/.fmm.db` but the parent-directory MCP tool resolved to `helioy/.fmm.db` (absent), so all code reads were direct Read tool calls. No claims here rely on fmm output.
