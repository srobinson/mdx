---
title: "ALP-1297 iter3 review: --all flag edge cases"
type: sessions
tags: [review, mdcontext, markdown-matters, cli]
summary: "Fixed 3 bugs in --all flag implementation: watch deadlock, silent TOML errors, missing source dirs"
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Summary

Reviewed iteration 3 of ALP-1297 (rename to markdown-matters, config rewrite). The iteration implemented `--force` and `--all` flags for `mdm index`, synced help text and MCP descriptions, and added a `generateDefaultToml` round-trip test.

## Issues Found and Fixed

**1. `--all` + `--watch` deadlock** (index-cmd.ts)
The `for` loop over `dirsToIndex` enters `Effect.async` (SIGINT handler) which never resolves, blocking at the first directory forever. Added early rejection with a clear message when both flags are combined.

**2. `readGlobalSources` swallowed TOML parse errors** (loader.ts)
A bare `catch { return [] }` meant malformed `~/.mdm/.mdm.toml` produced "No global sources registered" instead of surfacing the parse error. Removed the catch-all; caller now handles the error with a descriptive message.

**3. Non-existent source directories passed silently** (index-cmd.ts)
Sources registered in global config whose directories no longer exist were silently passed to `buildIndex`, which ran with 0 results. Added `fs.existsSync` guard with per-source warnings and bail-out when all sources are missing.

## Tests Added

3 new integration tests in `index-flags.test.ts`:
- `--all --watch rejects with clear error`
- `--all skips non-existent source directories`
- `--all surfaces malformed TOML errors`

Total: 1259 tests passing (up from 1256).

## Patterns Observed

- Integration tests shell out to `node dist/cli/main.js`, so source changes require a `tsc` build before tests reflect them.
- Static temp paths in tests (e.g., `/tmp/mdm-no-such-dir-12345`) collide across runs if a previous run created the directory. Use `fakeHome`-relative or `mkdtemp`-based paths instead.
