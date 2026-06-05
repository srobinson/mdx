---
title: Mail protocol v1 issue review pass 3 for littleorgans
type: research
tags: [littleorgans, mail-protocol, linear-review, moe-review, session]
summary: 'Pass 3 found three issue set gaps: notify Nudge audit proof, green workspace boundaries, and explicit db migration ownership.'
status: active
source: codebase-analyst
confidence: high
created: 2026-06-01
updated: 2026-06-01
---

## Executive Summary

The pass 3 MoE review checked Linear ALP-2906 through ALP-2915 against the signed mail protocol spec and live source. Three substantive blockers remain before clean sign off: the notify wake path must prove Nudge authorization and audit, the worker sequence must keep the workspace build green at each boundary, and W2 must own the actual SQLite migration mechanism in `internal/db`.

## Project Metadata

- Language: Rust.
- Build and test surface: root `just check && just build && just test`; targeted crates named in workers include `lilo-session-core`, `lilo-session-store`, `lilo-session-daemon`, and now should include `lilo-db` for schema migration proof.
- Navigation: `.fmm.db` is present. `fmm validate` on 2026-06-01 reported all 373 files indexed and current.
- Schema mechanism: `internal/db/src/lib.rs:LiloDb.open_path` runs `sqlx::migrate!("./migrations")` at lines 46 to 49.

## Architecture

The current mail implementation is still the old single table model:

- Core wire model: `internal/session/core/src/proto/messaging.rs` exposes `MailSendRequest { from, to, content }` at lines 7 to 11 and `MailReadRequest { selector, peek }` at lines 21 to 24.
- Core row model: `internal/session/core/src/mail.rs` defines `Mail` with `sender_id`, `recipient_id`, `content`, `sent_at`, and `read_at` at lines 41 to 48.
- Store: `internal/session/store/src/sqlite/mail.rs` inserts, counts, reads, and updates `session_mail` at lines 24 to 93.
- Daemon: `internal/session/daemon/src/handler/messaging.rs` authorizes mail send, mail read, and nudge through `IdentityClient` before store or runtime side effects at lines 131 to 167 and 190 to 200.
- Runtime seam: `internal/session/driver/src/port.rs` already exposes `RuntimePort::nudge`, `status`, and `poll_events` at lines 40 to 49.
- Event ingestion today is runtime scoped: `internal/session/daemon/src/events.rs:handle_batch` consumes `RuntimePort::poll_events` batches and persists runtime lifecycle state at lines 76 to 110.

## Key Patterns

- Authorization is side effectful. `IdentityClient.authorize_with_stub` delegates to the authorizer at `internal/identity/service/src/client.rs:91-100`; `StubAuthorizer.authorize` records the audit row before returning allow or deny at `crates/lilo-im-stub/src/lib.rs:43-61`.
- Audit rows carry actor, action, resource, decision, timestamp, and outcome fields through `crates/lilo-im-core/src/audit.rs:40-52` and are persisted by `crates/lilo-im-store/src/sqlite/audit.rs:219-243`.
- Store transactions already exist inside the sqlite store, including mail read marking at `internal/session/store/src/sqlite/mail.rs:58-67`, namespace cleanup at `internal/session/store/src/sqlite/namespaces.rs:79-95`, and runtime event cursor persistence at `internal/session/store/src/sqlite/events.rs:28-33`.

## Detailed Findings

### P3-1: Notify wake Nudge authorization and audit is not falsifiable

Spec §5 states that notify composes mail with a wake, and that authorization is per recipient: persistence requires `MailSend`; the wake additionally requires `Nudge` (`~/.mdx/projects/littleorgans-mail-protocol--spec.md:231-235`). Current explicit nudge code follows that rule: `internal/session/daemon/src/handler/messaging.rs:nudge_one` authorizes `Action::Nudge` before calling `runtime.nudge` at lines 190 to 200.

ALP-2912 says notify persists mail and then fires a nudge through `RuntimePort`; its acceptance checks persistence, wake targeting, and warning behaviour, but does not require the additional `Nudge` authorization or audit row. ALP-2914 repeats the W5 behaviour checks without an audit proof.

Required issue edit:

- Add an ALP-2912 constraint and acceptance check that notify wake uses the Identity port with `Action::Nudge` per persisted recipient before calling `RuntimePort::nudge`.
- Add an ALP-2914 W5 or cross cutting PER check that the notify wake path records the Nudge audit row with actor, action, recipient resource, decision, timestamp, and outcome.

### P3-2: W1 and W2 can break the workspace before W4 repairs consumers

ALP-2908 removes `from` from `MailSendRequest`, but current consumers still construct or read it in several places:

- `internal/session/app/src/cli/mail.rs:25-30`
- `internal/session/daemon/src/mcp_tools/mail.rs:25-29`
- `internal/session/daemon/src/handler/messaging.rs:22-30`
- `internal/session/daemon/tests/handler_messaging.rs:30-34` and `105-114`
- `internal/session/app/tests/mcp_protocol_test/mail.rs:16-25`

ALP-2908 currently declares daemon and CLI behaviour out of scope, while its verification still includes the full workspace gate. W4 owns derived sender semantics, but it is blocked by W1, W2, and W3. That creates a worker boundary where W1 can remove the type field before W4 updates the semantic consumers. W2 has a similar risk: replacing `session_mail` changes store contracts before the daemon worker lands.

Required issue edit:

- Amend the gate or workers so each intermediate worker can pass `just check && just build && just test` before the next worker starts.
- Preferred: W1 owns the mechanical workspace compile and test migration for direct `MailSendRequest` consumers, while W4 still owns derived sender semantics. W2 owns mechanical store consumer updates needed after the schema split.
- Alternative: bundle the breaking core and store changes with their daemon consumer changes. Do not leave an implicit wave end repair while each worker claims the full workspace gate.

### P3-3: ALP-2909 omits the actual migration mechanism and fresh database proof

The SQLite schema is not embedded in `internal/session/store`. It is applied by `sqlx::migrate!("./migrations")` in `internal/db/src/lib.rs:LiloDb.open_path` at lines 46 to 49. The live migration file `internal/db/migrations/0001_unified_schema.sql` still creates `session_mail`. The fresh database schema test `internal/db/src/lib.rs:open_creates_unified_schema_tables` asserts that `session_mail` exists at lines 112 to 128.

ALP-2909 is titled as migration work, but its entry points only name `internal/session/store/src/sqlite/mail.rs` and `internal/session/store/src/sqlite/namespaces.rs`. Its targeted verification names `cargo test -p lilo-session-store`, which does not exercise the `lilo-db` schema table test.

Required issue edit:

- Add `internal/db/migrations/0001_unified_schema.sql` and `internal/db/src/lib.rs:open_creates_unified_schema_tables` to ALP-2909 entry points.
- Add acceptance that a fresh `LiloDb::open_path` database has `messages` plus `message_deliveries`, and no `session_mail`.
- Add `cargo test -p lilo-db` to ALP-2909 verification.

## Dependencies

- `sqlx` supplies the SQLite migration and transaction mechanism.
- `lilo-im-core`, `lilo-im-stub`, and `lilo-im-store` provide authorization, audit row shape, and audit persistence.
- `lilo-session-driver` provides the existing `RuntimePort` seam that W3 and W5 should reuse.

## Relevance to Helioy

This review protects the Linear to Nancy workflow contract: every worker must be selectable and independently verifiable. It also keeps the mail protocol aligned with the local first trust model, where v1 authorization is uid coarse but every allow and deny decision still leaves an audit record.

## Open Questions

- Whether the orchestrator wants to preserve full workspace `just` at every intermediate worker boundary, or explicitly approve a different gate for W1 through W3.
- Whether wake attempt events from spec §5 should be added to W5 now or deferred by a gate design call. This pass only filed the Nudge authorization and audit proof for notify wake.
