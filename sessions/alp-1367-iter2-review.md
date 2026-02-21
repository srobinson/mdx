---
title: "ALP-1367 Iter 2 Review: SqliteContextStore fixes"
type: sessions
tags: [review, context-matters, cm-store, sqlite, ALP-1367]
summary: "Fixed nested block_on panic in supersede_entry and added update_entry validation"
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Summary

Reviewed iteration 2 of ALP-1367 (context-matters v0.1.0). Five commits adding migrations (001-003), content hash deduplication, and the full SqliteContextStore implementation (1022 lines across 15 ContextStore trait methods).

## Issues Found and Fixed

### 1. Nested block_on panic in supersede_entry (Critical)

**File:** `crates/cm-store/src/sqlite.rs`, `supersede_entry`

`supersede_entry` called `self.create_entry(new_entry)` from within its own `block_in_place` + `Handle::current().block_on()` context. Since `create_entry` also calls `block_in_place` + `block_on` internally, this creates nested blocking that panics at runtime ("Cannot start a runtime from within a runtime").

Additionally, the three mutations (insert new entry, mark old as superseded, create relation) were not wrapped in a transaction, violating the trait doc's atomicity guarantee. A failure on step 2 or 3 would leave an orphan entry.

**Fix:** Inlined the entry creation logic (validation, dedup check, INSERT) directly into `supersede_entry` and wrapped all three mutations in a sqlx transaction (`pool.begin()` / `tx.commit()`).

### 2. Missing validation in update_entry

**File:** `crates/cm-store/src/sqlite.rs`, `update_entry`

`create_entry` rejects empty title and body with `CmError::Validation`, but `update_entry` accepted `Some("")` for either field, allowing entries to reach a state that `create_entry` would have rejected.

**Fix:** Added upfront validation that rejects empty (whitespace-only) title or body when provided in the update.

## Patterns Observed

- The `block_in_place` + `Handle::current().block_on()` bridge pattern is used consistently across all 15 trait methods. It works for leaf methods but breaks when one trait method calls another (as in `supersede_entry` calling `create_entry`). Any future method that delegates to another ContextStore method will hit the same nested-blocking issue.
- Migrations and triggers are well-structured with proper guards against FTS corruption (trigger scoping, WHEN guards).
- Dedup logic correctly excludes superseded entries and self-collisions on update.
- No integration tests exist yet for the CmStore trait methods. The commit notes acknowledge this.

## Open Items

None requiring human decision. Both fixes are mechanical corrections that enforce existing documented contracts.
