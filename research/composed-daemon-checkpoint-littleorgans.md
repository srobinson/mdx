---
title: ALP-2817 composed daemon checkpoint review
type: research
tags: [littleorgans, alp-2817, composed-daemon, identity-gating, rust]
summary: The W3 composed daemon branch largely matches the two-phase spawn design, but runtime RPCs on the unified socket currently bypass identity authorization.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Executive Summary

Branch `nancy/ALP-2817` is structurally on track for the composed `lilod` direction: fmm is current, the shared database shape is present, and W3 session spawn uses a two phase transaction with post commit d9 append. The checkpoint blocker is identity gating for raw runtime RPCs: compose extracts peer credentials, but `RuntimeService::handle_rpc` discards the principal and dispatches runtime commands without authorization or audit.

## Project Metadata

- Language: Rust.
- Build system: Cargo workspace, Moon orchestration, root `justfile` operator surface.
- Structural index: `.fmm.db` and `.fmmrc.toml` exist. `fmm validate` passed for 334 indexed files.
- Current branch during review: `nancy/ALP-2817`.
- Branch delta against `main`: 172 files, `+4428/-3334`.
- Current status: untracked `.claude/` only in `git status --short`.

## Architecture

- `internal/session/app/src/compose.rs` owns the unified `lilod` listener, opens `LiloDb`, builds runtime and session services, extracts peer credentials once per accepted connection, and routes `LilodRpc::{Runtime, Session}` by variant.
- `internal/runtime/daemon/src/service.rs` wraps runtime daemon state and exposes `handle_rpc` plus event append and shutdown subscription.
- `internal/session/daemon/src/service.rs` builds the session service with `LiloDb`, `SqliteStore`, `IdentityClient`, lifecycle task, runtime event task, and an in process `Arc<RuntimeService>`.
- `internal/wire/` adds the internal `lilo-wire` crate for the symmetric `LilodRpc` envelope. This matches the ALP-2863 wire DCR and avoids a dependency direction conflict between runtime and session core crates.

## Key Patterns

- Shared pool: `LiloDb` is passed into runtime and session service factories. Internal stores derive their substrate pool view from the same sqlx pool.
- Two phase spawn: session spawn writes intent and Forking lifecycle first, performs the runtime side effect outside SQLite transaction scope, then inserts the session, updates lifecycle, resolves intent, and appends d9 after the commit.
- Raw runtime discriminator: runtime spawn checks for a preexisting Forking lifecycle. When absent, it treats the request as raw runtime access and does not create a session row or session intent.

## Detailed Findings

### Blocker: runtime RPCs bypass identity authorization

ALP-2817 and ALP-2863 require identity to front every RPC on `lilod.sock`, including runtime operator commands. The current implementation only satisfies the peer credential extraction part.

Evidence:

- Compose extracts peer credentials once and passes the principal to runtime dispatch: `internal/session/app/src/compose.rs:91-105`.
- Runtime service discards that principal: `pub async fn handle_rpc(&self, _principal: Principal, rpc: RuntimeRpc) -> RuntimeResponse` at `internal/runtime/daemon/src/service.rs:70-76`.
- Runtime handler dispatch then executes `RuntimeRpc::Spawn`, `Kill`, `KillByPid`, `Nudge`, `Capture`, `Status`, `Doctor`, `Events`, `Stop`, and shim RPCs without an identity check: `internal/runtime/daemon/src/handler.rs:106-180`.
- FMM glossary showed `IdentityService` is only used by `internal/identity/service/tests/factory.rs`, not by compose or runtime dispatch.
- Session RPCs do perform authorization, for comparison: shutdown gates with `Action::Daemon` at `internal/session/daemon/src/handler/dispatch.rs:91-94`, and session spawn gates inside Tx A at `internal/session/daemon/src/handler/spawn.rs:114-122`.

Impact:

- Raw `lilo runtime spawn`, `kill`, `status`, `doctor`, `events`, and `stop` can bypass the branch's own identity audit and authorization contract.
- This undercuts the substrate boundary rule from ALP-2816 as well, which says raw runtime diagnostic access remains identity gated and audited while not creating session records.

Recommended condition:

1. Add runtime authorization before runtime dispatch, either in compose or in `RuntimeService::handle_rpc`.
2. Map each `RuntimeRpc` to an `Action` and `ResourceSpec`. Examples: spawn to `Action::Spawn`, kill and kill by pid to `Action::Kill`, status and events to `Action::List` or `Action::Read`, doctor to `Action::Doctor`, stop to `Action::Daemon`.
3. Treat shim `ShimLaunch`, `ShimReady`, and `ShimExit` with an explicit local only policy. Avoid leaving them as an accidental bypass.
4. Add tests covering non local denial and audit rows for raw runtime operator calls.

### Clean signal: W3 two phase session spawn shape is present

Evidence:

- Tx A begins, audits, inserts pending spawn intent, and writes Forking lifecycle at `internal/session/daemon/src/handler/spawn.rs:100-143`.
- Runtime side effect happens after Tx A and before Tx B at `internal/session/daemon/src/handler/spawn.rs:68-85`.
- Tx B inserts session, updates lifecycle, resolves intent, and commits at `internal/session/daemon/src/handler/spawn.rs:184-208`.
- Runtime event append is after Tx B commit at `internal/session/daemon/src/handler/spawn.rs:210-213`.
- Runtime raw spawn discriminator lives at `internal/runtime/daemon/src/server/spawn.rs:39-56`; session backed calls suppress runtime d9 append at `internal/runtime/daemon/src/handler.rs:129-130` plus `internal/runtime/daemon/src/server/spawn.rs:194-198`.

### Clean signal: path and env cutover is mostly aligned for product reads

A direct grep found no product code reads of the deleted legacy env vars via `std::env::var`, `std::env::var_os`, or `env_path(...)` for `RTM_HOME`, `RTM_SOCKET_PATH`, `RTM_DB_PATH`, `SM_HOME`, `SM_SOCKET_PATH`, `SM_DB_PATH`, `SM_NAMESPACE`, `AGM_HOME`, or `LILO_DB_PATH`. The remaining legacy string literals are constants, negative tests, runtime tuning vars that are explicitly out of scope, or test fixture env names.

### Deferred surfaces that should not block this checkpoint

- `rusqlite` remains in root workspace dependencies. ALP-2860 W4 owns removal.
- `lilo-paths` still exports legacy path types. ALP-2860 W4 owns deletion.
- `rtm` and `sm` bins remain declared. ALP-2863 says they remain installable until Phase 6.
- `rtmd` copy still appears in runtime app error output. W4 owns daemon name leakage sweeps across docs and app surfaces.

## Dependencies

Critical crates and roles:

- `lilo-db`: shared sqlx `SqlitePool` and unified migrations.
- `lilo-wire`: internal request envelope for routing session and runtime RPCs over one socket.
- `lilo-im-core`, `lilo-im-store`, `lilo-im-stub`: identity actions, principals, audit sink, and stub authorization.
- `lilo-runtime-daemon`: runtime substrate service, lifecycle store integration, event log.
- `lilo-session-daemon`: session API server behavior, identity client use, session store, spawn intent flow.
- `tokio-util`: `CancellationToken` in compose.

## Relevance to Helioy

The finding affects the core Helioy local control plane model. The composed daemon can only be a safe control plane boundary if the unified socket enforces identity consistently for both session backed user flows and raw runtime diagnostic operator flows.

## Open Questions

- Should runtime authorization live in compose as a cross substrate chokepoint, or in `RuntimeService` so runtime policy stays near runtime dispatch? The ALP-2863 DCR allows either shape if peer credential extraction stays once at compose.
- Which `Action` should cover runtime `Status` and `Events`: `List`, `Read`, or a new runtime scoped action? Prefer reusing existing actions unless the policy semantics differ.
- Should shim RPCs be hidden behind a local same UID check only, or should they also record audit rows? The current code needs an explicit policy either way.
- Peer response on topic `alp-2817-checkpoint-signoff` was still pending when this note was written.
