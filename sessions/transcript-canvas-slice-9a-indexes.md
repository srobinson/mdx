---
title: Transcript Canvas Slice 9A Event Indexes
type: sessions
tags: [backend, transport-matters, transcript-canvas, postgres, alembic, indexes, ci]
summary: Added tier one event JSONB and expression indexes plus an explicit migration smoke gate.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented Slice 9A on branch `feat/transcript-canvas-slice-9a-indexes` at commit `6e7e7d3329814070d9ce35747e97ca6b1565a8c6`.

PR: https://github.com/littleorgans/transport-matters/pull/59

Key decisions:

1. Added only index changes for the existing `event` table.
2. Skipped `event_session_seq_ix` because `event_pkey` already covers `(session_id, seq)`.
3. Did not duplicate `event_ir_gin` or `event_fts_gin`, which already exist in the foundation migration.
4. Did not add resource tables, projection columns, timeline endpoints, or search endpoints.
5. Added an explicit migration smoke gate after manual up and down verification showed the automated migration coverage was too implicit.

## API Contract

No API contract changed in this slice. No endpoints, request schemas, response schemas, or error formats were added.

## Database Changes

Added Alembic revision `0002_event_tier1_indexes`, chained after `0001_session_store`.

Upgrade creates:

1. `event_raw_gin` on `"event" USING gin (raw jsonb_path_ops)`.
2. `event_session_raw_type_expr_ix` on `(session_id, (raw->>'type'), (raw->>'subtype'), seq)`.
3. `event_session_attachment_type_expr_ix` on `(session_id, ((raw->'attachment'->>'type')), seq)` with `WHERE raw ? 'attachment'`.

Downgrade drops those three indexes in reverse order.

Added migration smoke coverage in `api/src/transport_matters/session/test_migrate.py`:

1. Reset a throwaway Postgres database to an unmigrated state.
2. Apply migrations to head.
3. Assert tier one indexes exist.
4. Assert foundation `event_ir_gin` and `event_fts_gin` still exist.
5. Assert redundant `event_session_seq_ix` does not exist because the primary key covers `(session_id, seq)`.
6. Downgrade one revision.
7. Assert the tier one indexes were removed while foundation indexes remain.
8. Apply migrations to head again.

## Security Considerations

The change only adds Postgres indexes and test or CI gating. It does not touch authentication, authorization, raw byte exposure, or the wire request and response path.

## Performance Notes

The added indexes support first pass transcript canvas reads over existing `event.raw` rows:

1. JSONB containment and path shape queries use `event_raw_gin` with `jsonb_path_ops`.
2. Native record filtering can use the session scoped type and subtype expression index.
3. Attachment filtering can use the partial attachment type expression index without indexing every row.
4. Existing foundation indexes continue to cover `event.ir` and full text search.

Added automation:

1. `cd api && just migration-smoke` runs the migration smoke test directly.
2. `cd api && just ci` runs `migration-smoke` explicitly before the full pytest suite.
3. GitHub backend CI and release backend gates run the migration smoke before coverage pytest.

Verified on real Postgres:

1. Alembic `upgrade head` created the three new indexes, kept `event_ir_gin` and `event_fts_gin`, and confirmed no redundant `event_session_seq_ix`.
2. Alembic `downgrade -1` removed only the three new indexes.
3. `cd api && uv run ruff format --check migrations && uv run ruff check migrations` passed.
4. `cd api && just migration-smoke` passed with six tests.
5. `cd api && just ci` passed with 1237 tests.

## Open Items

No open items for Slice 9A. Deferred spec work remains outside this PR: resource tables, projection cache columns, timeline endpoint, and search endpoint.
