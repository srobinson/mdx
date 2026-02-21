---
title: ALP-1312 iter5 review - batch manifest activation drift
type: sessions
tags: [review, attention-matters, persistence, batch-query]
summary: Fixed batch query manifest under-tracking shared-token activations; all other iter5 changes clean
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Summary

Reviewed iteration 5 of ALP-1312 (attention-matters review remediation). Five commits covering: save_system audit (ALP-1348), token_count optimization (ALP-1352), unused parameter removal (ALP-1354), and quaternion doctests (ALP-1355).

## Issues Found and Fixed

**1. Batch query manifest under-tracks shared-token activations** (batch.rs)

When a token appears in N batch queries, `batch_query` correctly calls `occ.activate()` N times (once from `activate_word`, plus N-1 extra). However, only the first activation's occurrence IDs were pushed into `activated_ids` for the manifest. `persist_manifest` then called `batch_increment_activation` with too few entries, causing SQLite to have `activation_count = original + 1` while in-memory had `original + N`. On server restart, activation counts would regress.

Fix: push each extra activation's ID into `activated_ids` inside the extra loop, matching the number of in-memory increments.

## Patterns Observed

- The incremental persistence design (QueryManifest + persist_manifest) is well structured but requires discipline: every in-memory mutation must have a corresponding manifest entry. This class of bug (forgetting to track a mutation) is the primary risk surface for the approach.
- The `batch_set_activation_counts` (absolute write) pattern used for demote is inherently safer than the `batch_increment_activation` (relative increment) pattern, since absolute writes are idempotent and don't accumulate drift.

## Open Items

None. All quality checks pass (378 tests, 8 doctests, zero clippy warnings).
