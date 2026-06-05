---
title: "Transcript Tailer S3: bounded retry + poison quarantine"
type: projects
tags: [backend, transport-matters, tailer, session-store, postgres, quarantine, dead-letter]
summary: "Design spec for slice S3 — isolate one poison record so the tailer cannot spin forever, via per-record SAVEPOINT isolation in the writer + dead-letter table + bounded tailer backstop."
status: active
source: backend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

# Transcript Tailer S3 — bounded retry + poison quarantine

Independent design spec (expert 2 / backend-engineer). Orchestrator synthesizes; no
coordination with the other expert. READ-ONLY: this is design only, no code patches.

Scope: S3 of the transcript-tailer poison-record fix. S1 (NUL sanitizer at
`session/dao_rows.py:event_params`/`session_params` + `upsert_artifact` `media_type`) and
S2 (`session/ingest.py:_search_text` byte budget) shipped in PR #103 and are NOT respec'd
here. S3 is the structural backstop: a poison class S1/S2 do not anticipate must not be
able to spin the tailer or grow logs without bound.

Citations are file + symbol (never line numbers).

---

## 1. Problem recap — the spin seam

The live-tail loop (`index/tailer.py`):

- `TranscriptTailer._run` calls `poll` every `_DEFAULT_FILE_INTERVAL_S` (0.25s).
- `poll` iterates cursors and calls `_poll_cursor`, wrapping each in
  `try/except → _log.exception("tailer poll failed …")`. **The exception is swallowed.**
- `_poll_cursor` reads the file from `cursor.byte_offset`, calls `iter_complete_records`,
  tees consumed bytes to tier-1, then `ingest_records`. It advances `cursor.byte_offset`
  and sets `cursor.stat_signature` **only after `ingest_records` returns**. Any raise
  before those two lines leaves both un-advanced.
- `ingest_records` builds all `EventWrite`s for the window and calls `submit_batch` **once**.
- `submit_batch` (wired in `addon_runtime.py:submit_events`) calls
  `SessionWriter.submit_blocking → _commit_batch`, which inserts the whole batch **in one
  transaction with no per-record catch**.

Consequence: a single event that Postgres rejects (decoded NUL → `DataError`/
`UntranslatableCharacter`; oversize `content_tsv` → `ProgramLimitExceeded`) aborts the
whole transaction → `_poll_cursor` raises → `poll` logs and returns → `byte_offset`
unchanged → the **same byte window is re-read and re-rejected every 0.25s forever**,
re-growing `mitmdump.log` and burning CPU. Pinned today by
`index/test_tailer.py:test_cursor_state_advances_only_after_submit_success`.

S3 must let the good records in the window commit, set the one poison record aside
durably, advance the cursor past it, and never confuse a transient DB outage (Postgres
restart) for poison.

---

## 2. Transient-vs-poison discrimination (CRITICAL)

A Postgres restart, pool exhaustion, or dropped connection must **never** quarantine a
good record. Discrimination is by **psycopg `SQLSTATE`**, not by exception identity alone,
because `SQLSTATE` is the precise, version-stable signal Postgres returns. New pure module
`session/quarantine.py` (allowed by the import DAG: `session/` may import `ir` /
`canonicalization` / surviving `index/*` / storage read helpers; this module imports only
stdlib + `psycopg`).

Three buckets:

**A. POISON — deterministic, content-derived, will fail identically on every retry.**
`SQLSTATE` class in:
- `22` — data exception (includes `22P05 untranslatable_character`,
  `22021 character_not_in_repertoire`, `22001 string_data_right_truncation`). The decoded-NUL class.
- `54` — program limit exceeded (`54000`). The `content_tsv` tsvector overflow class.

Policy: **quarantine immediately** (see §3). No retry — retrying a deterministic data
rejection is exactly the spin we are killing.

**B. TRANSIENT — environmental, will succeed once the environment recovers.**
- `SQLSTATE` class in `08` (connection_exception), `53` (insufficient_resources, incl.
  `53300 too_many_connections`), `57` (operator_intervention, incl. `57P01 admin_shutdown`,
  `57P02 crash_shutdown`, **`57P03 cannot_connect_now`** — the Postgres-restart case),
  `58` (system_error), `40` (`40001 serialization_failure`, `40P01 deadlock_detected`),
  `55` (object_not_in_prerequisite_state).
- `psycopg_pool.PoolTimeout`, `concurrent.futures.TimeoutError` (the `submit_blocking`
  commit timeout), `psycopg.OperationalError`/`InterfaceError` **with `sqlstate is None`**
  (connection died mid-flight before a state was returned).
- **Any non-`psycopg` exception** (e.g. a bare `RuntimeError`, a `KeyError` from a code
  bug, or the mock in the pinning test). A code bug must surface by retrying + alerting,
  never by silently dead-lettering data.

Policy: **retry forever** (never quarantine), bounded only by log rate-limiting (§8). When
the environment recovers the same window commits cleanly — safe because `INSERT_EVENT_SQL`
is an **idempotent upsert** (`ON CONFLICT (session_id, seq) DO UPDATE`), so a re-tail of an
already-committed window is a no-op, not a `unique_violation`.

**C. OTHER psycopg error — has a `SQLSTATE`, not in A or B (e.g. a novel data class, or a
constraint violation in class `23`).** Treated as transient at the writer (re-raised) and
bounded by the **tailer backstop** (§3, §6). This conservative default means the writer
quarantines **only** known-deterministic data classes; everything genuinely ambiguous is
retried and only force-quarantined after a bounded number of identical-window failures, so
we never silently drop a record on a class we have not understood.

`session/quarantine.py` surface:

```python
POISON_SQLSTATE_CLASSES: frozenset[str] = frozenset({"22", "54"})
TRANSIENT_SQLSTATE_CLASSES: frozenset[str] = frozenset({"08", "53", "57", "58", "40", "55"})

def classify(exc: BaseException) -> Literal["poison", "transient", "other"]:
    """Pure. POISON → isolate+quarantine in-txn. TRANSIENT → retry forever.
    OTHER → re-raise; tailer backstop bounds it."""
```

`23505 unique_violation` is intentionally NOT poison: it cannot occur on the happy path
(`INSERT_EVENT_SQL` upserts) and on re-tail it is a benign duplicate. If it ever surfaces
it lands in OTHER → retried, never quarantined.

---

## 3. Retry-then-quarantine policy

There is no "retry N times then quarantine" tier for known poison, and that is deliberate:
SAVEPOINT isolation (§6b) gives a **definitive per-record verdict on the first attempt** —
if the good records around a rejected one commit, the connection is healthy and the
rejected record is provably the problem. A counter would only re-grow logs/CPU on a
deterministic failure.

| Bucket | Attempts before quarantine | Backoff | Action |
| --- | --- | --- | --- |
| POISON (§2A) | 0 (immediate) | — | isolate via SAVEPOINT, write dead-letter in same txn, advance |
| TRANSIENT (§2B) | ∞ (never quarantine) | natural 0.25s poll cadence | re-raise, no advance, retry next poll, rate-limited log |
| OTHER (§2C) | `QUARANTINE_MAX_ATTEMPTS` (default 5) on the **same byte window** | poll cadence | after the cap, force whole-window quarantine + advance (tailer backstop, §6) |

`QUARANTINE_MAX_ATTEMPTS` lives in `session/quarantine.py`. The OTHER backstop exists for
the rare failure the writer cannot attribute to one record (session-upsert-level poison,
or a commit-time rejection). It guarantees the spin is bounded for unforeseen-unforeseen
classes while keeping false-quarantine impossible for transient outages (those are bucket B
and never increment the counter).

---

## 4. Quarantine data model

**Decision: a new `event_dead_letter` table (forward migration `0003`).** Rejected, not a
file under the run dir.

Justification:
- The store is the operator read surface; a table is queryable for §7 counts via plain SQL
  joins (`GROUP BY run_id, native_session_id`) with no new file-scan path.
- It is poison-safe by construction: raw bytes go in a **`bytea`** column (NUL-safe, no
  text decoding) and there is **no `content_tsv`/`tsvector`** column, so the same bytes
  that broke `event` cannot break `event_dead_letter`. The only text column,
  `error_message`, is routed through the S1 `strip_decoded_nuls` helper before binding.
- We do not duplicate the full poison bytes. Tier-1 already tees the consumed window to the
  per-session snapshot **before** normalize (`_poll_cursor`'s `_snapshot_writer` call), so
  the byte span `(byte_start, byte_end)` is a durable pointer into tier-1 for byte-exact
  recovery. The table stores a **bounded** `raw_excerpt` (capped re-serialization of the
  parsed record) for self-contained triage when no disk backend is present, plus
  `raw_sha256` + `raw_byte_len` for integrity. This bounds table growth (§8).

We do NOT store the full original line bytes inline for the oversize class (could be >1 MB);
the cap + tier-1 pointer covers full-fidelity recovery without unbounded `bytea` growth.

Migration `0003_event_dead_letter.py` (`down_revision = "0002_event_tier1_indexes"`;
`downgrade` raises, matching the session-store precedent in `0001`):

```sql
CREATE TABLE event_dead_letter (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id      text NOT NULL,            -- NO FK: a dead-letter must always be writable,
    seq             integer,                  --   even if the session row itself failed (§6b edge)
    scope           text NOT NULL DEFAULT 'record',  -- 'record' | 'window'
    run_id          text NOT NULL,
    native_session_id text,
    provider        text,
    source_path     text,
    source_line     integer,
    byte_start      bigint NOT NULL,          -- absolute offset into the tier-1 transcript snapshot
    byte_end        bigint NOT NULL,
    error_sqlstate  text,                     -- '22P05', '54000', …
    error_class     text,                     -- psycopg exception class name
    error_message   text,                     -- S1-sanitized (strip_decoded_nuls) before bind
    raw_excerpt     bytea,                    -- capped json.dumps(event.raw) bytes; bytea = NUL-safe
    raw_sha256      text,
    raw_byte_len    bigint,
    attempts        integer NOT NULL DEFAULT 1,
    first_failed_at timestamptz NOT NULL DEFAULT now(),
    quarantined_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT event_dead_letter_scope_ck CHECK (scope IN ('record', 'window'))
);

-- Idempotent re-quarantine across a re-tail (cursor restarts at byte_offset 0 on API restart;
-- runs are process-resident per the project mental model). Keyed by span, not seq, so a
-- whole-window ('window') quarantine dedupes too.
CREATE UNIQUE INDEX event_dead_letter_span_uq
    ON event_dead_letter (session_id, byte_start, byte_end);

CREATE INDEX event_dead_letter_run_ix ON event_dead_letter (run_id, native_session_id);
```

`INSERT_DEAD_LETTER_SQL` uses `ON CONFLICT (session_id, byte_start, byte_end) DO NOTHING`
so re-tail never errors and never double-counts. New `dao_statements.INSERT_DEAD_LETTER_SQL`
+ `dao_rows.dead_letter_params(...)` (sanitizing `error_message`), wired into both
`SessionDao` and `AsyncSessionDao` via a new `insert_dead_letter(row)` method (the async one
is the path the writer uses; the sync one keeps the DAO pair symmetric and testable).

---

## 5. `iter_complete_records` signature change + blast radius

Today: `iter_complete_records(data: bytes) -> tuple[list[RawRecord], int]` (records,
consumed). It must carry per-record byte spans so a rejected record can be located in the
window and pointed into tier-1.

New return type — a frozen `CompleteRecord` (defined in `index/tailer.py`, re-exported from
`index/__init__`):

```python
@dataclass(frozen=True, slots=True)
class CompleteRecord:
    record: RawRecord       # the parsed dict (json.loads)
    byte_start: int         # offset within THIS buffer (relative to the read, i.e. to cursor.byte_offset)
    byte_end: int           # exclusive; byte_end - byte_start == raw line length incl. trailing '\n'
    line_index: int         # 0-based index among non-empty lines in this buffer

def iter_complete_records(data: bytes) -> tuple[list[CompleteRecord], int]:
    ...  # consumed (offset past last '\n') unchanged; malformed complete lines still skipped, not fatal
```

Spans are **relative to the buffer** (the buffer begins at `cursor.byte_offset`). The
consumer computes the absolute span as `cursor.byte_offset + byte_start`. Documented on the
function so callers do not double-add.

**Blast radius (3 call sites + 1 re-export + tests):**

1. `index/tailer.py:_poll_cursor` — `records, consumed = iter_complete_records(data)`
   becomes `complete, consumed = …`; the `if records:` guard becomes `if complete:`;
   `record_subagent_spawn_links(records=…)` and `ingest_records(records, …)` receive
   `[cr.record for cr in complete]` **plus** the spans (see below). Minor.
2. `session/backfill.py:_replay_owned` — two call sites (`snapshot.read_bytes()` and child
   `child_path.read_bytes()`). Both currently `records, _ = iter_complete_records(...)` then
   iterate `records`. Change to iterate `complete`, using `cr.record`. The `enumerate(records)`
   that assigns replay `seq` becomes `enumerate(complete)` using `cr.record`. **Backfill
   behavior is unchanged** — it is a parse-only path today (`_replay_owned` yields
   `ReplayRecord` tuples; `grep` confirms no production consumer submits them to the writer).
3. `index/__init__` re-export list — add `CompleteRecord`.
4. Tests: `index/test_tailer.py:TestIterateSeam` (4 tests assert the
   `(records, consumed)` tuple shape) update to the new element type;
   `session/test_ingest.py` / `session/test_subagents.py` replay tests use `cr.record`.

**Carrying the span to the writer (no hot-path byte bloat):** `ingest_records` builds each
`EventWrite` via `build_event` and then attaches a cheap **provenance** (ints only):

```python
# session/ingest.py — new frozen model
class RecordProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)
    byte_start: int          # absolute (into the tier-1 snapshot)
    byte_end: int

class EventWrite(BaseModel):                 # add one optional, non-persisted field
    ...
    provenance: RecordProvenance | None = None
```

`ingest_records` gains the spans alongside records (signature: accept
`records: Iterable[CompleteRecord]`, or a parallel `spans` arg — prefer
`Iterable[CompleteRecord]` to keep one object per record), and sets
`write = build_event(cr.record, turn, ctx).model_copy(update={"provenance":
RecordProvenance(byte_start=cursor.byte_offset + cr.byte_start, byte_end=cursor.byte_offset
+ cr.byte_end)})`. `provenance` is **not** persisted by `event_params` (it reads `EventRow`,
not `EventWrite`), so the happy-path DAO is untouched. Only ints travel on the hot path; the
dead-letter `raw_excerpt` is re-serialized from `event.raw` **inside the writer** only for
records that actually fail.

`TurnContext` (in `index/adapters/base.py`) is intentionally NOT given byte fields —
adapters must not see byte offsets.

How backfill behaves under quarantine: when/if a future slice wires replay to the writer,
it MUST reuse the same `_commit_batch` (so it inherits SAVEPOINT isolation + dead-lettering
for free) — do not build a second replay-only commit path. Replay has no persistent poll
loop, so it cannot spin; a poison record there is isolated, the rest of the snapshot
replays, and the pass completes. `ReplayRecord` should gain the optional span so a future
writer path can populate `byte_start/byte_end`; until then it is carried and ignored.

---

## 6. Cursor advance semantics

The advance contract is unchanged in spirit (advance only after durability) and is made
**atomic** with quarantine:

- **Happy path / per-record poison (common):** `ingest_records` returns normally.
  `_commit_batch` committed the good events **and** their dead-letter rows in one
  transaction (§6b). `_poll_cursor` advances `byte_offset += consumed` and sets
  `stat_signature` exactly as today, and resets `cursor.quarantine_attempts = 0`. Because
  the dead-letter write is in the **same transaction** as the good commit, "advance only
  after the quarantine write succeeds" is satisfied for free — there is no window where good
  rows are durable but the quarantine is not.
- **Transient (§2B):** `submit_blocking` raises. `_poll_cursor` re-raises (classified
  transient). No advance. Next poll re-reads the same window and retries. Rate-limited log.
- **OTHER unattributable (§2C) backstop:** `_poll_cursor` wraps `ingest_records`:

```python
try:
    ingest_records(complete, cursor, source.path, build_record=..., submit_batch=...)
except BaseException as exc:
    kind = classify(exc)
    if kind == "transient":
        cursor.quarantine_attempts = 0
        raise                                   # bubble to poll(): rate-limited log, no advance
    cursor.quarantine_attempts += 1             # 'poison' never reaches here (writer handled it); only 'other'
    if cursor.quarantine_attempts < QUARANTINE_MAX_ATTEMPTS:
        raise                                   # retry the same window a few more times
    if not self._quarantine_window(cursor, data, consumed, exc):
        raise                                   # quarantine write failed (transient) → no advance, retry
    cursor.quarantine_attempts = 0
    # fall through to the advance below
# advance byte_offset + stat_signature (and the tier-1 tee already happened pre-normalize)
```

**Behavior if the quarantine write fails:** the per-record dead-letter is in the good
commit's transaction, so its failure aborts that transaction → `submit_blocking` raises →
no advance → retry (no split-brain). The window-level `_quarantine_window` returns
`False`/raises on a transient failure → `_poll_cursor` does not advance → retry. Either way
the cursor never advances past data that was neither committed nor durably quarantined.

`_quarantine_window` submits a single `scope='window'` dead-letter (seq NULL, span =
`cursor.byte_offset .. cursor.byte_offset + consumed`, `raw_excerpt` = capped
`data[:consumed]`) through a new `SessionWriter.quarantine_window_blocking(...)` →
`AsyncSessionDao.insert_dead_letter`. It returns `True` only on a committed write.

### 6b. Batch isolation — commit the good records around the one poison

`_commit_batch` is one transaction for the whole poll. **Use a per-record `SAVEPOINT`**
(`async with conn.transaction():` nested inside the outer `conn.transaction()`), commit the
good records, and write the dead-letter rows in the same outer transaction:

```python
async def _commit_batch(self, batch: EventBatch) -> CommitResult:
    await self._ensure_open()
    rejected: list[tuple[EventWrite, psycopg.Error]] = []
    async with self._pool.connection() as conn, conn.transaction():       # outer txn
        dao = AsyncSessionDao(conn)
        try:
            await dao.upsert_session(batch.session)
        except psycopg.Error as exc:
            if classify(exc) == "poison":
                # session row itself is poison → S1 should prevent this; quarantine ALL events
                # (events FK to session, so none can land) and return ok with quarantined=N.
                for item in batch.events:
                    await dao.insert_dead_letter(dead_letter_params(item, exc, scope="record"))
                return CommitResult(ok=True, session_id=batch.session.session_id,
                                    committed=0, quarantined=len(batch.events))
            raise                                                          # transient/other → abort, retry
        for item in batch.events:
            try:
                async with conn.transaction():                            # per-record SAVEPOINT
                    await dao.insert_event(item.event)
                    for artifact in item.artifacts:
                        row = await dao.upsert_artifact(artifact.data, media_type=artifact.media_type)
                        await dao.link_artifact(item.event.session_id, item.event.seq, row.hash, artifact.ref)
            except psycopg.Error as exc:
                if classify(exc) == "poison":
                    rejected.append((item, exc))                          # savepoint rolled back; txn still alive
                    continue
                raise                                                     # transient/other → abort whole batch
        for item, exc in rejected:
            await dao.insert_dead_letter(dead_letter_params(item, exc, scope="record"))
        await conn.execute("SELECT pg_notify(%s, %s)", (self._notify_channel, _notify_payload(batch)))
    committed = len(batch.events) - len(rejected)
    return CommitResult(ok=True, session_id=batch.session.session_id,
                        committed=committed, quarantined=len(rejected),
                        last_seq=batch.events[-1].event.seq if batch.events else None)
```

Why SAVEPOINT over "resubmit minus poison" or "split into singletons":
- A nested `conn.transaction()` is a `SAVEPOINT`; on a poison raise it rolls back to the
  savepoint and leaves the **outer** transaction usable, so good records commit and the
  dead-letter rows are written in the **same** transaction → one round-trip, atomic.
- "Resubmit minus poison" needs ≥2 round-trips and a second build of the batch; "split into
  N singletons" loses the all-good-records-together atomicity and multiplies round-trips.
- Note vs. the known anti-pattern: per-record savepoints here give per-**record** isolation,
  which is exactly the goal (isolate one poison record). We are NOT claiming the batch is
  atomic as a unit — the contract S3 wants is "every healthy record in the window commits,
  every poison record is set aside," and SAVEPOINTs deliver precisely that. The genuinely
  all-or-nothing step (good events + their dead-letters + notify) is still one transaction.

`CommitResult` (in `session/writer.py`) gains `quarantined: int = 0`. `submit_blocking` is
unchanged structurally. `addon_runtime.py:submit_events` keeps its `if not result.ok:`
guard (still only false on a path that raises today) and additionally feeds
`result.quarantined` to the visibility hook (§7).

dropped-record consequence: a quarantined record leaves a **seq gap** and does not extend
the `parent_id`/`parent_seq` chain (`ingest_records` pre-assigns seq for every record,
including the one that later fails to insert). A seq gap and a one-link chain break for a
rare poison record is the correct trade vs. an infinite spin; the dead-letter row + tier-1
span preserve everything needed to repair later.

---

## 7. Operator visibility (minimal; defer full S4)

Two cheap producers, no new read endpoint (that is S4 on `RunViewModel`/`SessionSummary`):

1. **`CommitResult.quarantined`** already flows back per commit. `addon_runtime.py:
   submit_events` accumulates a per-process counter and emits a single structured log line
   per quarantine event:
   `logger.warning("quarantined %d record(s) run=%s session=%s sqlstate=%s", …)`.
2. **The table is the queryable truth.** Counts per run / native session are a one-liner:
   `SELECT run_id, native_session_id, count(*) FROM event_dead_letter GROUP BY 1, 2`.
   S4 surfaces this on the run/session view models.

No new metric infra in S3; the counter + table are enough for an operator to answer "did
anything get quarantined?" via `transport-matters doctor` or a direct query.

---

## 8. Bounded log growth

The unconditional `_log.exception("tailer poll failed …")` in `TranscriptTailer.poll` is the
log-growth vector (fires every 0.25s on a stuck transient window). Add a per-cursor rate
limiter:

- Add to `TailCursor`: `last_fail_log_monotonic: float | None = None`,
  `suppressed_fail_count: int = 0`, plus the `quarantine_attempts: int = 0` field from §6.
- In `poll`'s except branch: log at full detail the **first** failure for a given
  `cursor.byte_offset`, then suppress further logs for `_FAIL_LOG_INTERVAL_S` (e.g. 30s),
  incrementing `suppressed_fail_count`. On the next emit (interval elapsed) or when the
  cursor finally advances, log a one-line summary including `suppressed_fail_count` and
  reset it. Use `time.monotonic()`.
- The dead-letter `raw_excerpt` is capped (`DEAD_LETTER_RAW_MAX_BYTES`, e.g. 64 KiB) with
  `raw_sha256` + `raw_byte_len` recording the true size, so the oversize poison class cannot
  bloat the table; full bytes remain recoverable via the tier-1 span.

---

## 9. Test plan — REAL Postgres via the repo gate

Gate (verbatim, from `api/`): `just check && just test`. Tests hit real Postgres
(`TEST_DATABASE_URL`); they must be failing-before / passing-after. Note: an unset
`TEST_DATABASE_URL` makes PG tests **error, not skip** — a green run means the summary line
shows passed, not that errors were masked (check the runner's own summary, not a piped tail).

New tests (writer-level in `session/`, tailer-level in `index/test_tailer.py`):

1. **Poison isolated, good records commit, cursor advances (real PG).** Build a batch of 3
   events where the middle event carries a `search_text` that exceeds the tsvector limit
   with `_cap_search_text` monkeypatched off → real `ProgramLimitExceeded` (54000). Assert:
   events 0 and 2 are present in `event`; event 1 is absent; one `event_dead_letter` row
   with `error_sqlstate='54000'`, correct `(byte_start, byte_end)`; `CommitResult.quarantined
   == 1`; the tailer advanced `byte_offset` past the window.
2. **Decoded-NUL poison (real PG).** Same shape using a record whose `raw`/text carries a NUL
   with `strip_decoded_nuls` patched off → `DataError`/`UntranslatableCharacter` (class 22) →
   quarantined; neighbours commit.
3. **Transient does NOT quarantine.** Inject `psycopg.OperationalError(sqlstate=None)` (or
   `57P03`) for the batch once, then succeed: assert first `submit_blocking` raises, cursor
   does NOT advance, `event_dead_letter` is empty; second poll commits cleanly. Also assert a
   bare `RuntimeError` (the existing pinning mock) is treated transient (no quarantine, no
   advance) → `test_cursor_state_advances_only_after_submit_success` still passes unchanged.
4. **Quarantine-write-failure → no advance.** Force `insert_dead_letter` to raise a transient
   error: assert the whole transaction aborts, good rows are NOT visible, cursor does not
   advance, next poll retries.
5. **Backstop (OTHER).** Make `submit_blocking` raise a non-transient, unattributable error
   `QUARANTINE_MAX_ATTEMPTS` times on the same window: assert no advance for the first K-1,
   then a `scope='window'` dead-letter row + advance on the Kth; counter resets.
6. **Log rate-limit.** Drive repeated transient failures on one window across many polls;
   with `caplog`, assert the failure log fires at most once per `_FAIL_LOG_INTERVAL_S`, with
   a suppressed-count summary, not once per 0.25s poll.
7. **Backfill / replay seam.** `iter_complete_records` returns `CompleteRecord` with correct
   `byte_start/byte_end/line_index` over a fixture buffer (extend `TestIterateSeam`);
   `_replay_owned` still yields the same records/seqs via `cr.record`
   (`session/test_ingest.py`, `session/test_subagents.py` green).
8. **Idempotent re-quarantine.** Quarantine the same poison span twice (simulate re-tail):
   assert exactly one `event_dead_letter` row (the `ON CONFLICT … DO NOTHING` on the span
   unique index holds).

---

## 10. Slice / PR breakdown

Two PRs. Split at the byte-span plumbing seam so the risky behavioral change lands on a
green, already-merged signature change.

**S3a — byte-span plumbing prep (no behavior change).**
- `iter_complete_records` → `CompleteRecord` + relative spans; update `_poll_cursor`,
  `_replay_owned` (×2), `index/__init__` re-export.
- `RecordProvenance` + `EventWrite.provenance`; `ingest_records` accepts `CompleteRecord`s
  and sets absolute provenance.
- Update `TestIterateSeam` + replay tests. Spans carried but unused → low blast radius,
  mergeable alone, unblocks S3b.

**S3b — quarantine (the durability fix).**
- Migration `0003_event_dead_letter` + `INSERT_DEAD_LETTER_SQL` + `dead_letter_params`
  (NUL-sanitized `error_message`) + `insert_dead_letter` on both DAOs.
- `session/quarantine.py` (`classify`, `POISON_*`/`TRANSIENT_*` classes,
  `QUARANTINE_MAX_ATTEMPTS`, `DEAD_LETTER_RAW_MAX_BYTES`).
- `_commit_batch` SAVEPOINT isolation + in-txn dead-letter; `CommitResult.quarantined`.
- `_poll_cursor` backstop + `_quarantine_window` + `SessionWriter.quarantine_window_blocking`;
  `TailCursor` fail-tracking fields; `poll` log rate-limit.
- `addon_runtime.py:submit_events` visibility hook.
- Full §9 suite on real PG.

Seams named: `index/tailer.py` (`iter_complete_records`, `CompleteRecord`, `_poll_cursor`,
`TailCursor`); `session/ingest.py` (`RecordProvenance`, `EventWrite`, `ingest_records`);
`session/writer.py` (`_commit_batch`, `CommitResult`, `quarantine_window_blocking`);
`session/quarantine.py` (new); `session/dao_statements.py` + `session/dao_rows.py` +
`session/dao.py`/`session/async_dao.py` (`insert_dead_letter`); `api/migrations/versions/
0003_event_dead_letter.py`; `addon_runtime.py` (`submit_events`).

---

## Open items / risks

- **Session-row poison** (poison in `source_descriptor`/`title`) is covered by S1; §6b adds a
  belt-and-suspenders quarantine-all-events path if it ever recurs. Worth one explicit test
  if cheap; otherwise documented.
- **Seq gap / chain break** for a quarantined record is accepted (correctness trade); the
  dead-letter + tier-1 span allow a future repair tool to backfill the gap.
- **`raw_excerpt` cap** (64 KiB default) is a judgment call; the tier-1 span is the
  full-fidelity recovery path, so the cap only affects in-table triage convenience.
- **Tier-1 absence** (no disk backend → `_snapshot_writer is None`): the span pointer is
  dangling, but `raw_excerpt` keeps the dead-letter self-contained for triage. Acceptable.
