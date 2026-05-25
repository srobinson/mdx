---
title: Identity Authorization DRY Refactor Review for littleorgans
type: research
tags: [littleorgans, rust, identity, authorization, audit, review]
summary: Verified the ALP 2817 identity authorization refactor centralizes the v1 local principal decision and preserves audit behavior.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Executive Summary

The review covered a focused DRY refactor of the v1 identity authorization decision in the ALP 2817 worktree. The live files centralize the local uid allow rule and denial reasons in `AuditDecision::evaluate_local`, with stub and transaction paths consuming that decision without rechecking the principal.

No correctness issues were found. The full required gate, `just check && just build && just test`, passed with 555 tests run, 555 passed, and 0 skipped.

## Project Metadata

- Language: Rust
- Build system: Cargo workspace, Just command surface
- Test runner: cargo nextest through `just test`
- Indexed navigation: fmm was available and reported 342 files with 43,937 LOC
- Reviewed branch state: `nancy/ALP-2817`, ahead of `origin/nancy/ALP-2817` by 1 commit, with the reviewed refactor present as live worktree changes
- Key crates and modules: `crates/lilo-im-core`, `crates/lilo-im-stub`, `internal/identity/service`, `crates/lilo-im-store`, `internal/db`

## Architecture

Identity authorization now has one production decision home:

- `crates/lilo-im-core/src/audit.rs:26-35` defines `AuditDecision::evaluate_local(&Principal, u32) -> AuditDecision`.
- `crates/lilo-im-stub/src/lib.rs:49-60` calls `evaluate_local`, records the decision, then maps allow to `Authorized` and deny to `AuthzError::UnknownPrincipal`.
- `internal/identity/service/src/client.rs:70-84` calls `evaluate_local`, builds an `AuditRow`, records through the provided SQL connection, then maps the same decision to `Result<()>`.

Data flow for authorization is now:

1. Caller supplies principal, action, and resource.
2. `AuditDecision::evaluate_local` returns `Allow` or `Deny { reason }`.
3. The consumer records that decision in an audit row.
4. The consumer derives the authorization result from the recorded decision.

## Key Patterns

- Shared policy logic lives in `lilo-im-core`, not in each consumer.
- Audit recording happens before deny errors return, preserving denial audit visibility.
- The transaction path keeps audit atomic by recording through the caller supplied `&mut SqliteConnection`.
- Tests pin both the shared policy contract and parity between stub and transaction consumers.

## Detailed Findings

### Single production home

`AuditDecision::evaluate_local` contains the only production local uid predicate and both stable denial reasons:

- `crates/lilo-im-core/src/audit.rs:28` allows `Principal::Local(uid)` only when the uid equals `local_uid`.
- `crates/lilo-im-core/src/audit.rs:29-31` returns `Deny { reason: "non-local uid" }` for other local principals.
- `crates/lilo-im-core/src/audit.rs:32-34` returns `Deny { reason: "unknown principal" }` for unknown principals.

Live grep found no surviving `Principal::Local`, reason string, `audit_decision`, or `denial_reason()` duplicate in `crates/lilo-im-stub/src/lib.rs` or `internal/identity/service/src/client.rs`. String occurrences elsewhere are tests, snapshots, or the `AuthzError::UnknownPrincipal` display string, not duplicate policy implementations.

### No second predicate in consumers

The stub path computes one decision and reuses it:

- `crates/lilo-im-stub/src/lib.rs:49` calls `AuditDecision::evaluate_local`.
- `crates/lilo-im-stub/src/lib.rs:50` records `decision.clone()`.
- `crates/lilo-im-stub/src/lib.rs:52-60` derives the result from `decision`, with no second uid predicate.

The transaction path follows the same shape:

- `internal/identity/service/src/client.rs:70` calls `AuditDecision::evaluate_local`.
- `internal/identity/service/src/client.rs:71-76` builds an `AuditRow` from the same decision.
- `internal/identity/service/src/client.rs:80-84` maps that decision to success or `AuthzError::UnknownPrincipal`, with no second principal check.

### Behavior preserved

The shared helper can only produce `Allow` or `Deny` for the current principal variants, as shown by `crates/lilo-im-core/src/audit.rs:27-35`. It never constructs `AuditDecision::Error`.

The stub authorized payload remains unchanged:

- `crates/lilo-im-stub/src/lib.rs:53-56` returns the cloned principal, role `admin`, and an empty capabilities vector.
- `crates/lilo-im-stub/src/lib.rs:58-60` returns `AuthzError::UnknownPrincipal` for every deny.
- `internal/identity/service/src/client.rs:82-84` also returns `AuthzError::UnknownPrincipal` for every deny.

### Transaction semantics preserved

The in transaction path still records through the supplied connection:

- `internal/identity/service/src/client.rs:63-69` accepts `conn: &mut SqliteConnection`.
- `internal/identity/service/src/client.rs:77-79` calls `record_audit_in_tx(conn, &row)`, not the sink.

That preserves Tx A atomicity for audit writes.

### Test adequacy

Core unit tests pin the complete shared decision contract:

- `crates/lilo-im-core/src/audit.rs:97-100` pins allow for the matching local uid.
- `crates/lilo-im-core/src/audit.rs:103-111` pins the non local denial reason.
- `crates/lilo-im-core/src/audit.rs:114-126` pins the unknown principal denial reason.

The parity test is meaningful rather than tautological:

- `internal/identity/service/tests/factory.rs:63-67` exercises the stub path through `IdentityClient::authorize` and asserts denial.
- `internal/identity/service/tests/factory.rs:71-83` exercises `IdentityClient::authorize_in_tx` through a real acquired identity connection and asserts denial.
- `internal/identity/service/tests/factory.rs:86-97` queries persisted audit rows, asserts exactly two rows, and checks both rows carry the identical non local deny decision and reason.

### DRY and line limits

Touched files are comfortably within limits:

- `crates/lilo-im-core/src/audit.rs`: 127 lines
- `crates/lilo-im-stub/src/lib.rs`: 62 lines
- `internal/identity/service/src/client.rs`: 101 lines
- `internal/identity/service/tests/factory.rs`: 99 lines

The largest reviewed function is the 49 line parity test, below the 150 line function threshold.

### Gate proof

Command run from the worktree root:

```bash
CARGO_TERM_COLOR=never just check && CARGO_TERM_COLOR=never just build && CARGO_TERM_COLOR=never just test
```

Result: green. `just test` ran 555 tests across 80 binaries: 555 passed, 0 skipped.

## Dependencies

- `lilo_im_core`: shared authorization types, principals, audit rows, and the new decision helper.
- `lilo_im_stub`: current authorizer implementation that records audit rows and maps decisions to auth results.
- `lilo_im_store`: SQLite audit persistence and transaction audit helper.
- `lilo_db`: shared database and identity pool access.
- `sqlx`: SQLite connection and transaction plumbing.
- `tokio`: async test runtime for identity service tests.

## Relevance to Helioy

This refactor reinforces the monorepo boundary rule for local first control plane logic. Shared identity policy belongs in the core crate, while stub and service consumers own recording and result mapping. The pattern is useful for later authorization expansion because the business decision can evolve in one place without replaying drift across the daemon and service paths.

## Open Questions

None for this review. The only visible caveat is that string occurrences remain in tests and snapshots by design, which is acceptable because they assert the contract rather than implement policy.
