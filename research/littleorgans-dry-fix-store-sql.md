---
title: littleorgans dry fix store sql report
type: research
tags: [littleorgans, dry-fix, store-sql]
summary: Store SQL lane deduplicated shared WHERE predicates, lifecycle SQL, audit codecs, label upserts, and spawn intent status updates.
status: complete
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Completed the store SQL DRY lane after the orchestrator added `lilo-common` dependencies to the runtime and IM store crates.

## Files changed

- `crates/lilo-common/src/sql.rs`
- `crates/lilo-common/src/lib.rs`
- `internal/runtime/store/src/sqlite/lifecycle.rs`
- `internal/runtime/store/src/sqlite/lifecycle/codec.rs`
- `crates/lilo-im-store/src/sqlite/audit.rs`
- `internal/session/store/src/sqlite/labels.rs`
- `internal/session/store/src/sqlite/spawn_intents.rs`

## New shared API signatures and module

Module: `lilo_common::sql`

```rust
pub struct WhereClause;
impl WhereClause {
    pub const fn new() -> Self;
    pub fn predicate_prefix(&mut self) -> &'static str;
}
```

Consumers:

- `internal/runtime/store/src/sqlite/lifecycle.rs`
- `crates/lilo-im-store/src/sqlite/audit.rs`

## Store consolidations

- Runtime lifecycle now has one row column source, one row select builder, one insert column source, one update SQL source, shared encoded lifecycle bind order, and shared lifecycle state string mapping.
- IM audit now has one audit row column order, one placeholder order, and one encoded audit row codec for insert and read paths.
- Session labels now route pool and transaction label upserts through one executor helper.
- Session spawn intents now share status string mapping and one status update helper for resolved and aborted transitions.

## Dependencies needed but not added

None. No Cargo manifests were edited by this lane.

## Verification

Passed:

- `cargo check -p lilo-common`
- `cargo check -p lilo-runtime-store`
- `cargo check -p lilo-im-store`
- `cargo check -p lilo-session-store`

## Anything left

`fmm_file_outline` reported stale navigation data for edited files. I did not run `fmm generate` because the lane directive limited verification to crate scoped `cargo check` and prohibited edits outside the lane.
