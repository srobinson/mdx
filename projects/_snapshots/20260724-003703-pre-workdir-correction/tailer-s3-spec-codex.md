# Transcript tailer S3 bounded retry and quarantine spec

Date: 2026-06-14
Owner: backend engineer
Scope: S3 only. S1 NUL sanitization and S2 search text budgeting are assumed shipped and are not redesigned here.

## Grounding citations

This spec is grounded in the live tree and cites files with symbols only.

- `api/src/transport_matters/index/tailer.py::TranscriptTailer.poll`
- `api/src/transport_matters/index/tailer.py::TranscriptTailer._run`
- `api/src/transport_matters/index/tailer.py::TranscriptTailer.register`
- `api/src/transport_matters/index/tailer.py::TranscriptTailer._poll_cursor`
- `api/src/transport_matters/index/tailer.py::TailCursor`
- `api/src/transport_matters/index/tailer.py::iter_complete_records`
- `api/src/transport_matters/index/tailer.py::ingest_records`
- `api/src/transport_matters/session/writer.py::SessionWriter.submit_blocking`
- `api/src/transport_matters/session/writer.py::SessionWriter._commit_batch`
- `api/src/transport_matters/session/writer.py::_notify_payload`
- `api/src/transport_matters/session/backfill.py::replay_transcript_run`
- `api/src/transport_matters/session/backfill.py::_replay_owned`
- `api/src/transport_matters/session/backfill.py::ReplayRecord`
- `api/src/transport_matters/session/ingest.py::EventBatch`
- `api/src/transport_matters/session/ingest.py::build_event_batch`
- `api/src/transport_matters/session/dao_rows.py::event_params`
- `api/src/transport_matters/session/async_dao.py::AsyncSessionDao.insert_event`
- `api/migrations/versions/0001_session_store_foundation.py::upgrade`
- `api/migrations/versions/0002_event_tier1_indexes.py::upgrade`
- `api/src/transport_matters/index/test_tailer.py::TestIterateSeam`
- `api/src/transport_matters/index/test_tailer.py::TestTailerPoll.test_cursor_state_advances_only_after_submit_success`
- `api/src/transport_matters/index/test_tailer.py::TestSnapshotTee.test_snapshot_failure_does_not_advance_and_retries_next_poll`
- `api/src/transport_matters/addon_runtime.py::load_capture_runtime`
- `api/justfile::check`
- `api/justfile::test`

## 1. Problem recap: the spin seam

`TranscriptTailer._run` calls `TranscriptTailer.poll` every 0.25 seconds. `poll` catches every exception from `TranscriptTailer._poll_cursor` and logs `tailer poll failed for session ...` before the next interval.

`TranscriptTailer._poll_cursor` reads bytes from `TailCursor.byte_offset`, parses complete JSONL records with `iter_complete_records`, writes the consumed bytes to the Tier 1 transcript snapshot, then calls `ingest_records`. `ingest_records` builds every `EventWrite`, calls the injected `submit_batch`, and only then mutates `TailCursor.seq`, `TailCursor.source_line`, `TailCursor.parent_id`, `TailCursor.parent_seq`, and `TailCursor.model`. `_poll_cursor` only advances `TailCursor.byte_offset` and `TailCursor.stat_signature` after `ingest_records` returns.

The production writer path is `addon_runtime.load_capture_runtime` → `SessionWriter.submit_blocking` → `SessionWriter._commit_batch`. `_commit_batch` writes one `EventBatch` in one transaction. A single rejected event aborts the whole batch. Because the cursor is advanced only after the full commit succeeds, a deterministic poison record makes the next poll reread the same byte window and fail again forever. The existing `TestTailerPoll.test_cursor_state_advances_only_after_submit_success` pins the desirable half of that contract for transient failures, so S3 must add a durable poison path without regressing the transient retry behavior.

## 2. Transient versus poison discrimination

A record may be quarantined only after the failing operation has been isolated to one transcript record. A failure from the first whole batch attempt is only a signal to enter isolation. It is never enough to quarantine.

Add a small classifier in a new module, `transport_matters.index.tailer_failures`, so exception policy stays out of `TranscriptTailer._poll_cursor`.

```python
class TailerFailureKind(StrEnum):
    DETERMINISTIC_RECORD = "deterministic_record"
    TRANSIENT = "transient"
    UNKNOWN = "unknown"

def classify_tailer_exception(exc: BaseException) -> TailerFailureKind: ...
```

Classification order matters.

1. Deterministic record candidates first:
   - `psycopg.errors.UntranslatableCharacter`
   - `psycopg.errors.ProgramLimitExceeded`
   - `psycopg.DataError` and subclasses after excluding connection pool wrappers
   - SQLSTATE class `22` data exceptions, for example invalid text representation, numeric out of range, string data right truncation, and character not in repertoire
   - SQLSTATE `54001` program limit exceeded
2. Transient retry forever:
   - `psycopg_pool.PoolTimeout`
   - `concurrent.futures.TimeoutError` from `SessionWriter.submit_blocking`
   - `asyncio.TimeoutError`
   - `psycopg.errors.ConnectionException`, `ConnectionFailure`, `AdminShutdown`, `CannotConnectNow`, `TooManyConnections`
   - SQLSTATE class `08`, SQLSTATE `53300`, `57P01`, `57P03`, `57014`, `55P03`, `40001`, `40P01`
   - broad `psycopg.OperationalError` only after the deterministic `ProgramLimitExceeded` case has been checked
3. Unknown:
   - Any other exception from submit or quarantine write.

Policy by kind:

- `TRANSIENT`: do not quarantine, do not consume the failing record, keep retrying with backoff and rate limited logs. Already committed prefix records may stay committed because event inserts are idempotent by `(session_id, seq)`.
- `DETERMINISTIC_RECORD`: eligible for bounded retry and then quarantine, but only when the same single record fails during isolated submission.
- `UNKNOWN`: no quarantine by default. Treat as transient for cursor movement and log as unknown. This avoids losing data because a new infrastructure fault looked unfamiliar.

The key safety rule is simple: a Postgres restart, pool exhaustion, lock timeout, query cancellation, or writer timeout never reaches the quarantine branch.

## 3. Retry then quarantine policy

Add a per cursor retry ledger keyed by the durable record identity:

```python
TailerPoisonKey = tuple[str, str, int, int, str]
# session_id, source_path, absolute_byte_start, absolute_byte_end, raw_sha256
```

Default constants:

```python
TAILER_POISON_RETRY_ATTEMPTS = 3
TAILER_POISON_BACKOFF_S = (0.25, 1.0, 5.0)
TAILER_FAILURE_LOG_INTERVAL_S = 60.0
TAILER_ERROR_MESSAGE_MAX_CHARS = 2048
TAILER_RAW_PREVIEW_MAX_BYTES = 4096
```

Attempt semantics:

1. Normal path submits the whole parsed batch once.
2. If the whole batch fails with a transient or unknown failure, no isolation is attempted in that poll. The cursor remains at the first unconsumed record and the next eligible poll retries.
3. If the whole batch fails with a deterministic candidate, the tailer enters isolated submission for that same byte window.
4. Isolated submission sends one prepared record at a time using the same writer seam. A single record deterministic failure increments that record's ledger entry.
5. Attempts one and two stop at the failing record, leave it unconsumed, set `next_retry_at`, and log once per rate limit window.
6. Attempt three writes the quarantine row. Only after that write succeeds may the cursor advance past the record and continue with later prepared records in the same byte window.
7. If a record succeeds during any retry, clear its ledger entry and process it normally.

Quarantine eligible after retry budget:

- Single record insert or artifact link fails with a deterministic record exception.
- The failure is reproduced while the database connection is healthy enough to run that single record transaction.

Retry forever:

- Whole batch transient failures.
- Single record transient failures.
- Quarantine table write failures.
- Unknown exception classes.

No first failure quarantine path exists. This is deliberate. The classifier narrows the failure set, and isolated submission proves record scope before S3 skips bytes.

## 4. Quarantine data model

Use a new Postgres dead letter table rather than a file under the run directory.

Reasons:

- Operator visibility needs counts by `run_id` and `native_session_id` without scanning every run directory.
- Session data already lives in Postgres, and `SessionWriter._commit_batch` is the current durable writer boundary.
- The raw transcript bytes are already copied into Tier 1 before ingestion. Duplicating full raw records into Postgres expands the sensitive data surface.
- A table gives de duplication, indexes, and real Postgres tests for the exact failure class.

Migration: `api/migrations/versions/0003_transcript_dead_letter.py`.

Sketch:

```sql
CREATE TABLE transcript_dead_letter (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id text NOT NULL,
    session_id text NOT NULL,
    native_session_id text,
    provider text NOT NULL,
    cli text NOT NULL,
    source_path text NOT NULL,
    source_line integer NOT NULL,
    event_seq integer NOT NULL,
    event_kind text,
    byte_start bigint NOT NULL,
    byte_end bigint NOT NULL,
    raw_size_bytes bigint NOT NULL,
    raw_sha256 text NOT NULL,
    raw_preview text,
    error_class text NOT NULL,
    error_sqlstate text,
    error_message text NOT NULL,
    attempts integer NOT NULL,
    first_failed_at timestamptz NOT NULL,
    last_failed_at timestamptz NOT NULL,
    quarantined_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT transcript_dead_letter_span_ck CHECK (byte_end > byte_start),
    CONSTRAINT transcript_dead_letter_attempts_ck CHECK (attempts > 0)
);

CREATE UNIQUE INDEX transcript_dead_letter_record_uq
ON transcript_dead_letter (session_id, source_path, byte_start, byte_end, raw_sha256);

CREATE INDEX transcript_dead_letter_run_ix
ON transcript_dead_letter (run_id, quarantined_at DESC);

CREATE INDEX transcript_dead_letter_native_ix
ON transcript_dead_letter (run_id, native_session_id, quarantined_at DESC)
WHERE native_session_id IS NOT NULL;

CREATE INDEX transcript_dead_letter_session_ix
ON transcript_dead_letter (session_id, event_seq);
```

The migration should include a reversible `downgrade` that drops the indexes and table. Existing migration `0002_event_tier1_indexes.py` already has a reversible downgrade, and S3 should follow that pattern.

Do not add a foreign key to `session`. The failed writer transaction may have rolled back the session upsert along with the rejected event. The dead letter write must not be blocked by the same failed transaction state. Store session identity as data and let future S4 read surfaces join opportunistically.

Store hash plus bounded preview, not full raw bytes. The row records `byte_start`, `byte_end`, `raw_size_bytes`, and `raw_sha256`; Tier 1 or the original `source_path` is the raw source. The preview must be UTF 8 decoded with replacement, NUL stripped with the existing `session.dao_rows.strip_decoded_nuls` helper, and capped. Error strings use the same sanitizer and cap before insert.

Add model and DAO contracts:

```python
class TranscriptDeadLetterWrite(BaseModel):
    run_id: str
    session_id: str
    native_session_id: str | None
    provider: str
    cli: str
    source_path: str
    source_line: int
    event_seq: int
    event_kind: str | None
    byte_start: int
    byte_end: int
    raw_size_bytes: int
    raw_sha256: str
    raw_preview: str | None
    error_class: str
    error_sqlstate: str | None
    error_message: str
    attempts: int
    first_failed_at: datetime
    last_failed_at: datetime

class TranscriptDeadLetterResult(BaseModel):
    inserted: bool
    run_id: str
    session_id: str
    native_session_id: str | None
    run_count: int
    native_session_count: int | None
```

Implementation ownership:

- `session.models` owns the Pydantic row and write models.
- `session.dao_statements` owns insert and count SQL.
- `session.async_dao.AsyncSessionDao` owns `insert_transcript_dead_letter`.
- `session.writer.SessionWriter` exposes `quarantine_blocking(write: TranscriptDeadLetterWrite) -> TranscriptDeadLetterResult`, mirroring `submit_blocking`.

## 5. `iter_complete_records` signature change and backfill blast radius

Replace the raw record list return with parsed record envelopes that preserve byte spans.

```python
@dataclass(frozen=True)
class TranscriptRecordSpan:
    relative_start: int
    relative_end: int

@dataclass(frozen=True)
class CompleteTranscriptRecord:
    record: RawRecord
    span: TranscriptRecordSpan
    raw_bytes: bytes

def iter_complete_records(data: bytes) -> tuple[list[CompleteTranscriptRecord], int]: ...
```

Rules:

- `relative_start` and `relative_end` are byte offsets within the passed buffer.
- `relative_end` is exclusive and includes the newline delimiter, so `cursor.byte_offset + relative_end` is the safe next read position after that record.
- Malformed complete JSON lines keep current behavior: log and skip. They do not enter the DB poison path because no `RawRecord` exists. A future parse dead letter can handle malformed transcript bytes if product needs it.
- `consumed` remains the offset after the final newline, preserving the trailing partial safety contract.

Blast radius:

- `TranscriptTailer._poll_cursor` maps `absolute_start = cursor.byte_offset + parsed.span.relative_start` and `absolute_end = cursor.byte_offset + parsed.span.relative_end`.
- `record_subagent_spawn_links` receives `[parsed.record for parsed in parsed_records]`.
- `ingest_records` should be refactored into two helpers:
  - `prepare_record_writes(parsed_records, cursor, source_path, build_record)` returns prepared records and the final cursor state without mutating the live cursor.
  - `apply_prepared_state(cursor, prepared.after_state)` mutates the live cursor only after that prepared record has committed or been quarantined.
- `session.backfill._replay_owned` reads parsed envelopes from `iter_complete_records(snapshot.read_bytes())`, then passes raw records to `_started_at`, `_cwd`, `record_subagent_spawn_links`, and `iter_without_replayed_prefix_with_source_lines`.
- `ReplayRecord` should become a named dataclass rather than a bare tuple, because the tuple will gain span fields and the current shape is already too opaque.

Suggested backfill contract:

```python
@dataclass(frozen=True)
class ReplayRecord:
    binding: SessionBinding
    record: RawRecord
    source_line: int
    source: FileTailSource
    byte_start: int
    byte_end: int
    raw_sha256: str
```

Backfill behavior under quarantine:

- Backfill callers should use the same resilient ingest helper as live tailing when they write to Postgres.
- If a replayed record deterministically fails and an identical dead letter already exists, identified by the unique span and hash key, treat it as already quarantined and advance the replay cursor state.
- If no row exists, apply the same bounded retry policy, then insert a dead letter row.
- If the failure is transient, stop the replay and return an error to the caller. Do not quarantine.

## 6. Cursor advance semantics

S3 keeps the Tier 1 snapshot coupling from `TranscriptTailer._poll_cursor` and `TestSnapshotTee.test_snapshot_failure_does_not_advance_and_retries_next_poll`.

Order for each poll:

1. Read bytes from `TailCursor.byte_offset`.
2. Parse complete records and spans.
3. Write the whole consumed byte prefix to the snapshot writer, if configured.
4. Only after snapshot success, try DB ingestion.
5. Advance the live cursor one prepared record at a time after that record is either committed or quarantined.
6. Set `TailCursor.stat_signature` only when the cursor has consumed every complete record represented by that file stat.

If a prefix commits and a later record is pending retry, the cursor may advance through the committed prefix and stop at the failing record. The next poll starts at the failing record, not at the original window start. This prevents needless idempotent upserts while preserving the retry contract.

For a quarantined record:

- Write the dead letter row first.
- Then advance `TailCursor.byte_offset` to `absolute_byte_end`.
- Apply the prepared after state for that record: `seq`, `source_line`, `parent_id`, `parent_seq`, and `model` move exactly as they would have moved if the event had committed.
- The event table can have a sequence gap. The dead letter table stores `event_seq`, `event_kind`, and the source span that explains the gap.

If the quarantine write fails:

- Do not advance past the record.
- Do not clear the retry ledger.
- Leave `stat_signature` unset if the file has not been fully consumed.
- Log with the same rate limit window.
- Retry forever. A poison record is never skipped without a durable dead letter.

If all records in the window commit or quarantine, set `byte_offset` to the original offset plus `consumed` and set `stat_signature` to the observed file signature.

## 6b. Batch isolation

Use a split batch fallback driven by the existing writer seam, not savepoints inside `SessionWriter._commit_batch`.

Reasoning:

- The normal path remains one `EventBatch`, so the common case keeps current performance.
- `SessionWriter.submit_blocking` already provides the synchronous tailer thread to async writer bridge, timeout, session upsert, artifact writes, event writes, and notification.
- Savepoints would require expanding `_commit_batch` to know tailer byte spans and exception policy. That would mix transcript cursor policy into the generic session writer.
- Per record fallback only runs after a deterministic candidate failure, which should be rare.

Algorithm:

```text
prepare records without mutating the live cursor
try whole batch
if whole batch succeeds:
    apply final prepared state
    advance to consumed
else if failure is transient or unknown:
    record retry state, leave current failing record unconsumed, return
else:
    for prepared record in order from current cursor:
        try submit one record as its own EventBatch
        if success:
            clear ledger for that record
            apply its after state
            advance byte_offset to record.absolute_end
            continue
        classify the single record failure
        if transient or unknown:
            record retry state, stop at this record
        if deterministic:
            if retry budget remains:
                record retry state, stop at this record
            else:
                write dead letter
                apply its after state
                advance byte_offset to record.absolute_end
                continue
```

This commits the good records before and after one poison record. If a window contains several poison records, each record consumes its own retry budget and dead letter row. Good records between them still commit.

Prepared state is important. The old `ingest_records` mutates cursor state only after batch success. S3 should separate normalization from mutation so the failure path can apply the exact state transition per durable record. That preserves Codex model threading and parent tracking while allowing event sequence gaps for quarantined records.

## 7. Operator visibility

S3 should produce a minimal quarantine signal but defer full UI and run view work to S4.

Add a producer hook at the session writer boundary:

```python
class TranscriptQuarantineSignal(BaseModel):
    type: Literal["transcript_dead_letter"] = "transcript_dead_letter"
    run_id: str
    session_id: str
    native_session_id: str | None
    delta: int = 1
    run_count: int
    native_session_count: int | None
```

`SessionWriter.quarantine_blocking` inserts the dead letter row, queries `run_count` and `native_session_count`, and emits a Postgres `pg_notify` on the same channel as `_notify_payload`, using this new payload type. Existing consumers that only understand session events can ignore the new type. S4 can subscribe and surface counts by run and native session.

Also expose the signal as an optional callback on `TranscriptTailer` for unit tests and future in memory health registries:

```python
TranscriptTailer(..., quarantine_record: Callable[[TranscriptDeadLetterWrite], TranscriptDeadLetterResult] | None = None)
```

The callback is not optional in production when session capture is enabled. If it is missing and a poison record exhausts retry budget, the tailer must treat that as quarantine write unavailable and keep retrying rather than skip the record.

## 8. Bounded log growth

Replace the unconditional `poll` exception log loop with rate limited failure logging keyed by record identity where possible, else by session and exception class.

Use cursor local state:

```python
@dataclass
class TailerFailureLogState:
    first_seen_at: float
    last_logged_at: float
    suppressed_count: int = 0
```

Log rules:

- First failure for a key logs immediately at warning with session id, run id, source path, byte span when known, exception class, SQLSTATE, attempt count, and action.
- Repeated failures before `TAILER_FAILURE_LOG_INTERVAL_S` increment `suppressed_count` and do not log a traceback.
- The next permitted log includes the suppressed count.
- Transient and unknown failures log at warning without traceback after the first traceback. Deterministic isolated record failures log the first traceback, then concise warnings.
- Successful commit or successful quarantine clears the key.

`TranscriptTailer.poll` should keep a final broad catch as a last resort, but `_poll_cursor` should handle known tailer failure outcomes internally so a poison record does not produce a traceback every 0.25 seconds.

## 9. Test plan on real Postgres

Use the repository recipes from `api/justfile`: from `api/`, run `just check && just test`. The real proof must include Postgres tests, not hand built pytest substitutes.

Focused tests to add before the full gate:

1. Parser spans in `index/test_tailer.py::TestIterateSeam`
   - Complete records include exact relative byte spans and raw bytes.
   - Trailing partial bytes remain unconsumed.
   - Existing malformed complete line skip behavior remains.
   - Closed file backfill still consumes all newline terminated records.
2. Live tail poison quarantine in `index/test_tailer.py::TestTailerPoll`
   - A deterministic single record failure retries twice, then writes one dead letter on the third attempt.
   - Cursor advances past the quarantined record only after the dead letter callback succeeds.
   - Good records before and after the poison persist.
   - `seq` and `source_line` advance through the quarantine, leaving a documented event sequence gap.
3. Transient safety in `index/test_tailer.py::TestTailerPoll`
   - A simulated `psycopg_pool.PoolTimeout` or writer `FutureTimeoutError` never calls the dead letter callback.
   - The failing record stays unconsumed until a later success.
4. Quarantine write failure in `index/test_tailer.py::TestTailerPoll`
   - After retry budget exhaustion, a dead letter callback exception leaves `byte_offset` at the poison record and retries without unbounded logs.
5. Real Postgres writer tests in `session/test_ingest.py` or a new `session/test_dead_letter.py`
   - `SessionWriter.quarantine_blocking` inserts a row and returns counts.
   - Duplicate span plus hash is idempotent.
   - Error strings and previews with decoded NULs are sanitized before insert.
   - The migration creates and drops the table in the migration smoke path.
6. Deterministic insert rejection on real Postgres
   - Use an event payload that reaches `AsyncSessionDao.insert_event` with a deterministic failure class. A test can monkeypatch the DAO insert to raise `psycopg.errors.UntranslatableCharacter` for tailer isolation, then separately prove the dead letter table on real Postgres.
   - For `ProgramLimitExceeded`, keep S2's oversized search text regression as the proof that the original class is covered by the search budget. S3 only needs classifier coverage for the exception class.
7. Backfill and replay
   - `session.backfill._replay_owned` returns `ReplayRecord` objects with spans.
   - A replay writer using the shared resilient ingest helper skips an already quarantined span by hash.
   - A transient replay failure returns an error and does not insert a dead letter.
8. Log rate limit
   - Repeated poll failures under the same key emit one immediate log and one later summary with suppressed count. No traceback loop.

Required final gate:

```bash
cd api
just check && just test
```

## 10. Slice and PR breakdown

S3 is large enough to split cleanly. Recommended sub slices:

1. Span preparation PR
   - Change `iter_complete_records` to return `CompleteTranscriptRecord` envelopes.
   - Convert `ReplayRecord` from tuple to dataclass and update backfill tests.
   - No retry or quarantine behavior yet.
   - Gate: `cd api && just check && just test`.
2. Dead letter storage PR
   - Add migration `0003_transcript_dead_letter.py`.
   - Add Pydantic models, DAO SQL, `AsyncSessionDao.insert_transcript_dead_letter`, and `SessionWriter.quarantine_blocking`.
   - Add real Postgres tests and migration smoke coverage.
   - Gate: `cd api && just check && just test`.
3. Tailer resilience PR
   - Add exception classifier, retry ledger, isolated submission fallback, cursor advance rules, and rate limited logs.
   - Wire production `quarantine_record` in `addon_runtime.load_capture_runtime`.
   - Add live tailer tests for poison, transient, quarantine write failure, good records around poison, and log rate limit.
   - Gate: `cd api && just check && just test`.
4. Optional small producer signal PR if not included in storage PR
   - Add the `transcript_dead_letter` NOTIFY payload and callback proof.
   - Keep API and UI read surfaces deferred to S4.
   - Gate: `cd api && just check && just test`.

If implementation bandwidth favors one PR, keep the same internal order inside the PR. Do not merge tailer cursor changes before span tests and dead letter storage are green, because cursor movement depends on a durable quarantine sink.
