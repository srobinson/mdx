---
title: ALP-1279 Iteration 15 Review - Security Fixes
type: sessions
tags: [review, mdcontext, security, redos, path-traversal]
summary: Fixed symlinked root bypass in resolveAndValidatePath and wildcard alternation gap in ReDoS heuristic
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Summary

Reviewed 5 commits implementing security hardening for mdcontext: vector metadata schema validation (ALP-1200), config traversal restriction (ALP-1198), catastrophic backtracking detection (ALP-1196), MCP path traversal with realpath (ALP-1195), and Windows path.join fix. Found and fixed 2 issues.

## Issues Found and Fixed

### 1. Symlinked workspace root bypass in resolveAndValidatePath

**File:** `src/mcp/server.ts` (line ~247)
**Severity:** Medium (security)

`resolveAndValidatePath` canonicalized the target path via `fs.realpath` but compared it against the non-canonical root (`path.resolve` only). If the workspace root is behind a symlink, the canonical target path lives under the symlink target directory, which never matches the symlink source prefix. Every valid path would be rejected.

**Fix:** Also canonicalize `normalizedRoot` via `fs.realpath` before the containment check.

### 2. Wildcard alternation not detected by isCatastrophicPattern

**File:** `src/search/searcher.ts` (line ~77)
**Severity:** Low (ReDoS gap)

The JSDoc claimed coverage of `(.|\\s)+` but the overlap detection stripped non-alphanumeric characters from branches before comparing. Since `.` is non-alphanumeric, it was removed, leaving an empty set with no intersection. The regex wildcard `.` matches any character, so any alternation containing `.` under a quantifier has overlap by definition.

**Fix:** Added early return when any branch contains `.`. Updated JSDoc to accurately describe the three detection shapes. Added tests in both `searcher.test.ts` and `server.test.ts`.

## Patterns Observed

- The iteration's code quality was high overall. Both issues were subtle edge cases in newly added security logic, not structural problems.
- The Effect Schema validation pattern in vector-store.ts uses `as unknown as VectorIndex` to bridge the schema output type to the readonly interface. This is acceptable but worth noting as a convention.

## Open Items

None. All 1276 tests pass, typecheck clean.
