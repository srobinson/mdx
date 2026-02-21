---
title: ALP-1118 Warroom v2 — Iteration 1 Code Review
type: sessions
tags: [review, helioy-bus, shell, sqlite, tmux]
summary: Two correctness bugs found and fixed in identity resolution regex and SQLite migration for profile column
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

Reviewed iteration 1 of ALP-1118 (Warroom v2: dual-mode agent spawning with unified identity model). Five commits covering resolve-identity.sh, warroom.sh, bus-register/unregister/check-mail hooks, bus_server.py, and comprehensive tests. All 54 tests (31 Python + 23 shell) passed before the review. Two correctness bugs found and fixed.

## Issues Found and Fixed

### 1. Identity regex rejects named tmux sessions (`resolve-identity.sh`)

**File:** `plugin/hooks/lib/resolve-identity.sh`, line 17  
**Before:** `_IDENTITY_PATTERN='^[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+:[0-9]+:[0-9]+\.[0-9]+$'`  
**After:** `_IDENTITY_PATTERN='^[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+:[0-9]+\.[0-9]+$'`

`warroom.sh` uses `#{session_name}` to build pane titles. tmux session names can be any alphanumeric string — unnamed sessions get numeric names (0, 1, 2) but named sessions (e.g., `-s work`, `-s helioy`) produce alphabetic names. The old regex required `[0-9]+` for the session field, causing silent fallback to basename identity for any user with named sessions. The window.pane suffix `:[0-9]+\.[0-9]+$` remains as the structural anchor.

### 2. Missing `profile` column migration (`server/bus_server.py`)

**File:** `server/bus_server.py`, `_init_db()`, after line 63  
**Added:** `ALTER TABLE agents ADD COLUMN profile TEXT` migration

The `bus-register.sh` shell hook runs at SessionStart and creates the agents table without the `profile TEXT` column (the shell hook predates the column). When the MCP server subsequently calls `_init_db()` via `db()`, `CREATE TABLE IF NOT EXISTS` is a no-op (table exists), and there was no migration for profile. Any `register_agent` call passing `profile=...` would crash: `OperationalError: table agents has no column named profile`.

## Patterns Observed

- The shell hook creates the DB schema independently of the Python server. Any new column added to bus_server.py's schema MUST have a corresponding `ALTER TABLE ... ADD COLUMN` migration, or it will be missing on databases initialized by the hook.
- The `#{session_name}` vs `#{session_id}` distinction in tmux: `session_name` is user-visible (can be any string), `session_id` is `$N` (not numeric either). Neither guarantees digits. Structural validation should not assume numeric session identifiers.

## Open Items

None. Both fixes are self-contained. 57 tests pass (32 Python + 25 shell).
