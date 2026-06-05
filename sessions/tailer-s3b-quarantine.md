---
title: Tailer S3b Quarantine Durability
type: sessions
tags: [backend, transport-matters, tailer, postgres, quarantine]
summary: Implemented durable dead letter quarantine for poison transcript records and completed PR 105 review fixes.
status: active
source: backend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

## Summary

Implemented S3b transcript tailer quarantine durability on branch `fix/tailer-s3b-quarantine`, then completed the PR #105 review fix round.

Key decisions and fixes:

- Poison persistence failures are isolated with Postgres savepoints so healthy records in the same batch can still commit.
- Poison records are inserted into `event_dead_letter` in the same outer transaction as the surviving event writes.
- Record scoped dead letters now use the authoritative `batch.session.native_session_id` instead of re deriving native identity from raw event JSON.
- Whole window quarantine is a tailer backstop after `QUARANTINE_MAX_ATTEMPTS = 5` non transient failures.
- Tailer poll failure logs are rate limited to avoid log storms during repeated poison windows or storage outages.
- Added coverage that a post loop `insert_dead_letter` failure aborts the whole writer transaction, leaves good records invisible, and keeps the tailer cursor unadvanced.

Published commits:

- `6fbd931` initial S3b quarantine implementation and PR #105.
- `c259be0` PR #105 focused review fixes, pushed to `fix/tailer-s3b-quarantine`.

## API Contract

No public HTTP or WebSocket API contract changed.

Internal write contract additions:

```typescript
type DeadLetterScope = "record" | "window";

interface DeadLetterWrite {
  sessionId: string;
  seq?: number;
  scope: DeadLetterScope;
  runId: string;
  nativeSessionId?: string;
  provider?: string;
  cli?: string;
  sourcePath?: string;
  sourceLine?: number;
  eventKind?: string;
  byteStart: number;
  byteEnd: number;
  errorSqlstate?: string;
  errorClass?: string;
  errorMessage?: string;
  rawExcerpt?: Uint8Array;
  attempts: number;
}

interface CommitResult {
  ok: boolean;
  sessionId: string;
  committed: number;
  quarantined: number;
  quarantineSqlstates: Array<string | null>;
  lastSeq?: number;
}
```

## Database Changes

Added migration `api/migrations/versions/0003_event_dead_letter.py` in the initial implementation.

Schema highlights:

- `event_dead_letter` table with no foreign key to `session`, so poison session rows cannot block quarantine.
- `raw_excerpt bytea`, `raw_sha256 text`, and `raw_byte_len bigint` for bounded raw diagnostics.
- Unique span index on `(session_id, byte_start, byte_end)` for idempotent inserts.
- Run lookup index on `(run_id, native_session_id)`.
- Reversible downgrade drops the run index, span index, and table.

DAO changes:

- Added `INSERT_DEAD_LETTER_SQL`.
- Added sync and async `insert_dead_letter` methods.
- Added `dead_letter_params` with excerpt capping at 65536 bytes and full raw hash metadata.

## Security Considerations

- Database writes remain parameterized.
- Raw transcript diagnostics are capped before insertion.
- Error messages are stripped of decoded NUL bytes before persistence.
- No raw fetch API was added.
- Quarantine has no session foreign key by design, which prevents poison session rows from blocking forensic durability.

## Performance Notes

- Savepoints isolate poison records without retrying a full batch.
- Transient storage failures keep cursor state unchanged and retry later.
- Poll failure logging is rate limited with suppression summaries.
- Dead letter rows use bounded raw excerpts to keep inserts and indexes small.
- The oversized `content_tsv` poison regression uses real Postgres SQLSTATE 54000 by disabling `_cap_search_text` only inside the test.

Verification:

- `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres uv run pytest src/transport_matters/session/test_ingest.py::test_tailer_quarantines_program_limit_poison_and_advances src/transport_matters/session/test_ingest.py::test_tailer_dead_letter_failure_aborts_batch_and_holds_cursor`, 2 passed
- `cd api && just check`, passed
- `cd api && just test`, 1347 passed
- `cd api && just migration-smoke`, 6 passed before the review fix round on commit `6fbd931`

## Open Items

- The dead letter table is write only for now. A future operator surface can expose owner scoped quarantine diagnostics.
- Retention policy for old dead letter rows is not implemented in this slice.
