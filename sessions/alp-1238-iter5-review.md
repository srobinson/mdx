---
title: ALP-1238 iter5 review - doc-test assertion quality
type: sessions
tags: [review, attention-matters, doc-tests, ALP-1238]
summary: Fixed 3 tautological doc-test assertions in compose.rs and feedback.rs
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Summary

Reviewed iteration 5 of ALP-1238 (post-v0.1.15 codebase quality review). Two commits were in scope: ALP-1277 (parse_days_ago unit tests) and ALP-1278 (doc-tests for public API types). Seven files changed, 220 lines added.

## Issues Found and Fixed

**1. Tautological assertions in doc-tests (feedback.rs, compose.rs)**

Three doc-test assertions tested unsigned types against >= 0, which is always true:

- `feedback.rs`: `result.boosted >= 0` and `result.demoted >= 0` (both `usize`)
- `compose.rs`: `ctx.metrics.conscious + ctx.metrics.subconscious + ctx.metrics.novel >= 0` (all `u32`)

Fixed by replacing with meaningful checks:
- feedback.rs: changed to `> 0` since the test inputs guarantee token overlap
- compose.rs: changed to verify `included_ids.len()` equals sum of `recalled_ids` category lengths

Commit: `19d2b4f review[ALP-1238]: Replace tautological doc-test assertions with meaningful checks`

## Patterns Observed

- The recency.rs refactor (injecting `now_secs` for testability) was well executed. Clean separation of concerns.
- Doc-tests follow a consistent pattern (seeded RNG, minimal setup). Good as living documentation.
- The tautological assertion pattern is common when writing doc-tests quickly. Worth watching for in future reviews.

## Open Items

None. All quality checks pass (clippy, tests, doc-tests).
