---
title: Store SQL DRY Fix Implementation
type: sessions
tags: [backend, littleorgans, sql, dry]
summary: Deduplicated store SQL predicate, lifecycle, audit, label, and spawn intent helpers across the store SQL lane.
status: active
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Implemented the `store-sql` DRY lane for ALP-2817. Added a shared SQL predicate prefix helper in `lilo-common`, consumed it from runtime lifecycle and IM audit queries, and removed local duplicate `push_where` helpers. Consolidated runtime lifecycle column lists, row query construction, bind order, and lifecycle state string mapping. Consolidated IM audit encoded row handling for insert and read paths. Added local helpers for session label upserts and spawn intent status updates.

## API Contract

No HTTP or RPC API contract changed.

New Rust helper API:

```rust
pub struct WhereClause;
impl WhereClause {
    pub const fn new() -> Self;
    pub fn predicate_prefix(&mut self) -> &'static str;
}
```

Module path: `lilo_common::sql::WhereClause`.

## Database Changes

No schema or migration changes. SQL statement construction was refactored only.

## Security Considerations

All changed SQL paths keep parameterized binds. The shared `WhereClause` helper emits only static SQL separator tokens and never accepts untrusted input.

## Performance Notes

Query plans are unchanged. The refactor removes string and bind order duplication without adding runtime allocation to static predicate separator handling.

Verification passed:

- `cargo check -p lilo-common`
- `cargo check -p lilo-runtime-store`
- `cargo check -p lilo-im-store`
- `cargo check -p lilo-session-store`

## Open Items

`fmm_file_outline` reported stale navigation data for edited files. I did not regenerate `.fmm.db` because the squad lane restricted verification to crate scoped `cargo check` and prohibited edits outside the assigned lane.
