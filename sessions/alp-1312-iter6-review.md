---
title: ALP-1312 Iter6 Review - Storage Layer and Manifest Fixes
type: sessions
tags: [review, attention-matters, storage, schema, batch]
summary: Reviewed 4 commits touching batch manifest tracking, drain_buffer atomicity, schema constraints, and load_system regression test. All clean.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Summary

Reviewed iteration 6 of ALP-1312 (Review Remediation). Four commits across `am-core/batch.rs`, `am-store/schema.rs`, and `am-store/store.rs`. All changes are correct, well-tested, and consistent with codebase conventions.

## Changes Reviewed

1. **batch.rs - manifest under-tracking fix** (d395d8e): Extra activations for shared-token batch queries now push to `activated_ids`, fixing a drift between in-memory activation counts and persisted SQL values on restart.

2. **schema.rs - neighborhood_type CHECK constraint** (643c8a2): Schema version 7 to 8. Fresh databases get a CHECK constraint in CREATE TABLE. Existing databases get BEFORE INSERT/UPDATE triggers (SQLite cannot add CHECK via ALTER TABLE). Both enforce the same five allowed values. Test confirms invalid values are rejected.

3. **store.rs - drain_buffer atomicity** (412d0c1): Replaced blanket DELETE with ID-targeted DELETE WHERE id IN (...). Borrow lifetime of `id_params` is properly scoped to the `if` block, no conflict with `entries.into_iter()` after the block ends. At-least-once semantics for concurrent connections.

4. **store.rs - 500+ occurrence roundtrip test** (692ff1f): 10 episodes x 5 neighborhoods x 12 tokens = 600 occurrences. Validates structural equivalence, activation count fidelity, and quaternion precision through save/load cycle.

## Issues Found and Fixed

None.

## Verification

- `just check`: zero clippy warnings
- `just test`: 68 tests + 8 doctests, all passing
