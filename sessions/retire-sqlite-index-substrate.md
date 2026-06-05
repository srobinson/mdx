---
title: Retire SQLite Index Substrate
type: sessions
tags: [backend, session-store, sqlite-retirement]
summary: Removed the retired SQLite index substrate and routed transcript capture through the Postgres session store.
status: active
source: backend-engineer
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

## Summary

Implemented slice 5 on branch `feat/session-5-retire-sqlite`.

Key changes:

- Removed the retired SQLite index, diff, block, rebuild, query, and raw route modules.
- Deleted the old `/api/index` router registration and tests.
- Rehomed durable run discovery into `session/backfill.py` with `iter_run_dirs`.
- Retargeted transcript tailing to `session.ingest.build_event` and `SessionWriter`.
- Registered launcher owned transcript cursors directly from runtime launch settings.
- Updated retained adapter, sink, and architecture docs to the active session store model.
- Cleaned post review stale references in `TLDR.md`, root `CLAUDE.md` via symlink, `storage/session_facts.py`, and related comments that still named deleted SQLite era paths.
- Opened PR #37 at `https://github.com/littleorgans/transport-matters/pull/37`.

## API Contract

No new public endpoint shapes were added.

Removed public surface:

```typescript
// Removed with api/v1/index_routes.py
// GET /api/index
// GET /api/index/raw
```

Active session APIs continue to use the existing session routes. Raw bytes are no longer exposed through the removed index route. A future raw fetch surface needs an explicit wire store API.

## Database Changes

No migration was added.

The deleted substrate was the legacy SQLite projection layer. The active correlated transcript store is Postgres through the existing session store path:

- `SessionWriter`
- `session.ingest.build_event`
- `session.backfill.replay_transcript_runs`
- `index.tailer.TranscriptTailer`

Tier 1 run directories remain the durable source for wire artifacts, transcript snapshots, and owned launch facts.

## Security Considerations

- Removing the old raw route reduces accidental raw byte exposure.
- Session route owner scoping is unchanged.
- Transcript cursor registration now uses the launcher owned source descriptor when present, so managed runs tail the exact recorded source path.
- Startup failure for session capture logs and disables transcript capture for that run without blocking the proxy.

## Performance Notes

- Removed the legacy SQLite single writer, rebuild gate, and query layer from runtime startup.
- Live transcript tailing now batches event writes through the Postgres session writer.
- Transcript replay is transcript only and avoids wire artifact reads.
- Snapshot writes still happen before cursor advancement, so session events never outrun the owned transcript copy.

Verification:

- `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres just ci`: 1143 passed.
- Post review rerun of the same backend CI after stale reference cleanup: 1143 passed, `EXIT=0`.
- `rg -n 'single shared SQLite|SQLite index|index\.db|content-addressed blocks|full-text search|Tier-2|tier-2|index/maintenance|index\.ingest|index\.blocks|index/(maintenance|ingest|blocks)|bind_exchange' TLDR.md CLAUDE.md PROJECT.md api/src api/tests`: no matches.
- `git grep -nE 'IndexWriter|index_db_path|make_index_sink|index\.db' -- api/src`: no matches.
- `rg -n '/api/index|api/index|/raw|raw\?' www desktop`: no live old endpoint callers. The only match was a `raw-secret` redaction assertion.
- `cd www && pnpm lint && pnpm typecheck && pnpm test`: 50 files passed, 374 tests passed.

## Open Items

- Wire versus transcript diff remains a product direction, but the old diff era substrate is gone. Reintroduce raw fetch or diff only through a new explicit wire store API.
