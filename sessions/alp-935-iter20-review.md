---
title: ALP-935 Iteration 20 Review - Migration fixes + secret scrub
type: sessions
tags: [review, supabase, migrations, security, echoecho]
summary: Fixed misplaced SET search_path in migration 005; scrubbed leaked Mapbox sk. token from git history via rebase
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Iteration 20 applied 6 Supabase migrations to staging. Changes: renamed migration files to avoid duplicate version keys, added `SET search_path TO public, extensions` for PostGIS resolution, updated config.toml for CLI v2.72+ and PG 17.

## Issues Found and Fixed

1. **Migration 005 (`20260309080005_match_route_rpc.sql`)**: `SET search_path TO public, extensions` was inserted inside the dependency comment block, splitting it mid-list. Moved to after the comment block.

2. **Leaked Mapbox secret token in README.md** (orchestrator directive): Commit 4735c16 contained the actual `sk.eyJ...` download token in a code example. Rebased and amended that commit to replace with placeholder. Remote branch was already deleted by orchestrator; pushed fresh branch with clean history.

## Patterns Observed

- Migrations 002, 003, 006 correctly omit `search_path` (no PostGIS references).
- Down scripts retain old naming convention. Acceptable since they are manual rollback scripts.
- All quality gates pass: typecheck, lint, 25/25 tests.

## Open Items

None.
