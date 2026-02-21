---
title: ALP-1312 Review Remediation - Iteration 1 Review
type: sessions
tags: [review, attention-matters, architecture, cli, rust]
summary: Reviewed 5 commits (ALP-1315 through ALP-1318). All changes clean. No fixes needed.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Summary

Reviewed iteration 1 of ALP-1312 (Review Remediation). Five commits covering architecture review sub-issues: sync_dispatch extraction, dual-path re-export fix, constant export pollution reduction, and MCP error type preservation. All changes compile, pass clippy, and pass all 67 tests.

## Issues Found and Fixed

None. All changes are correct.

## Review Details

- **ALP-1315 (sync_dispatch.rs)**: Clean extraction of ~300 lines from main.rs. No logic changes. Import style improved (`Write as _`).
- **ALP-1316 (lib.rs dual-path)**: Modules correctly made private. `recency`/`scoring` kept `pub(crate)`. server.rs import path updated.
- **ALP-1317 (constants.rs)**: 9 constants correctly scoped down. 6 retained as pub match am-store's actual usage. Dead code annotations documented.
- **ALP-1318 (server.rs error helpers)**: Exhaustive StoreError match. Generic serde helper via `impl Display`. All 5 callsites migrated.

## Patterns Observed

- Worker correctly verified ALP-1319 through ALP-1322 as already done in v0.1.16 rather than re-implementing. Good judgment.
- Hardcoded ANSI escape codes in sync_dispatch.rs predate this iteration (ALP-1324 tracks the fix).
- `cmd_sync_discover` opens store unconditionally in dry-run (ALP-1325 tracks this).

## Open Items

None for this iteration.
