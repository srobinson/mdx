# Transport Matters — Session Store (buildable spec)

Author: backend-engineer/claude. Status: draft for one adversarial pass.
Grounds the charter (`CHARTER.md`) in the actual repo. Every "Open question" is
resolved into a concrete design with `file:symbol` citations. Wire-exchange
storage is PARKED: the schema leaves a clean per-turn attach point but does not
specify it.

Paths are relative to `api/src/transport_matters/` unless noted.

---

## 0. What this store is

The durable, first-class, portable asset behind the session platform (replay,
fork, share, eval, learn). Postgres. Hosting is the same app and schema pointed
at a remote `DATABASE_URL`. The store replaces the disposable SQLite "tier-2"
block index; tier-1 on disk stays as the local capture spool and forensic raw
tier.

Three things stay and are REUSED, never reimplemented:

- The transcript adapter port and the two concrete adapters: `index/adapters/base.py`
  (`TranscriptAdapter`, `SessionBinding`, `NormalizedTurn`, `TranscriptSource`),
  `index/adapters/claude.py`, `index/adapters/codex.py`.
- The live tailer: `index/tailer.py` (`TranscriptTailer`).
- Launch ownership: `cli/launch_profile.py` (`LaunchProfile`, `ClaudeLaunchProfile`,
  `CodexLaunchProfile`, `prepare_managed_session`), `cli/codex_session.py`
  (`seed_codex_session`), and the durable owned-launch facts
  `storage/session_facts.py` (`OwnedSessionFacts`, `write_owned_session_facts`).
- The tier-1 byte-faithful transcript snapshot: `storage/transcript_snapshot.py`
  (`make_transcript_snapshot_writer`), written under `<run_dir>/transcripts/<session_id>.jsonl`.

What is swapped: the SQLite storage internals (`index/db.py`, `index/schema.py`,
`index/writer.py`, `index/ingest.py`, `index/queries.py`, `index/blocks.py`,
`index/models.py`, `index/maintenance.py`, `index/rebuild.py`) are replaced by a
Postgres `session/` package. The `block`/`turn_block`/`exchange_block` content
de-dup model and the `pivot`/`diff` read surfaces retire with the wire/transcript
DIFF.

---

## 1. Architecture

### 1.1 Layer placement (import DAG)

`api/CLAUDE.md` fixes the order `ir -> adapters -> rules -> pipeline -> storage ->
breakpoint -> server`, with `index/` sitting after `storage`, importing `ir` and
`canonicalization` only, never imported by `storage` (the sink is injected at
`load_runtime()`). The new `session/` package sits in the same slot as `index/`:

- It imports `ir`, `canonicalization`, and the surviving capture sub-tree
  (`index/adapters`, `index/tailer`, `index/sessions`).
- `storage/` must never import `session/`. The write sink is injected at
  `load_runtime()` exactly as the SQLite sink is today (`index/writer.py:80`
  `IndexWriter.start` is called there; the docstring at `index/ingest.py`
  `make_index_sink` is the injection point).
- `session/` may import `storage` read helpers for tier-1 backfill (the disk
  layout and facts readers), which is a forward edge `session -> storage`, not the
  forbidden `storage -> session` back-edge.

Working assumption on package boundary (see Open question A): create a new
`session/` package and retarget `index/tailer.py` to submit to the new async
writer. Keep `index/adapters`, `index/tailer`, `index/sessions` where they are
(the launcher and tailer already import them); delete the SQLite-only modules.

### 1.2 Tier boundary after the migration

- Tier-1 (disk, KEPT): the per-run capture spool and forensic tier.
  `storage/disk_layout.py:DiskStorageLayout` roots it at
  `~/.transport-matters/workspaces/{slug}/{hash}/{run_id}/`, holding `index.jsonl`,
  `sessions.json` (`storage/session_facts.py`), `transcripts/<session_id>.jsonl`
  (the byte-faithful snapshot), and per-exchange dirs with the PARKED wire raw
  (`request.raw`, `response.raw`, `transport.json`, codex `events.jsonl`/`turn.json`).
- Postgres (the durable asset): the session/event/artifact store. Backfilled once
  from tier-1, then authoritative. A session survives after its CLI transcript file
  is GC'd because the raw records live in `event.raw`.

The transcript snapshot is the bridge: it is already byte-faithful and was proven
sufficient to rebuild tier-2 from tier-1 alone (`index/rebuild.py:replay_run`,
`backfill`). The Postgres backfill reuses that exact replay path with a Postgres
writer target.

---

## 2. Postgres schema

DDL below is the initial Alembic migration. Types are Postgres. JSONB for
record/IR payloads, `tsvector` for FTS, GIN for JSONB containment, partial-unique
for the native-id guard, `BYTEA` for artifacts by value.

```sql
-- ── session ────────────────────────────────────────────────────────
create table session (
    session_id         text        primary key,          -- universal correlation key (resolved by the binder)
    provider           text        not null,              -- anthropic | codex | ...
    cli                text,                               -- claude | codex; null until the launcher plumbs it
    run_id             text        not null,
    cwd                text        not null,
    workspace_slug     text        not null,
    workspace_hash     text        not null,
    native_session_id  text,                               -- provider native id (partial-unique guard)
    minted             boolean     not null default false, -- TM minted via --session-id (deferred)
    -- resumable-state pointer (subsumes storage/session_facts.py:OwnedSessionFacts):
    source_descriptor  jsonb,                              -- TranscriptSource (file_tail | pull); was TEXT JSON in SQLite
    home_dir           text,                               -- managed --home-dir; null = CLI native home
    -- platform columns:
    owner              text        not null default 'local',   -- owner stub; real account later
    status             text        not null default 'active',  -- active | completed | archived
    title              text,                                   -- optional human label for browse
    -- fork lineage:
    parent_session_id  text        references session(session_id),
    forked_at_seq      integer,                            -- fork point in the parent; null for a root
    started_at         timestamptz not null,
    created_at         timestamptz not null default now(),
    updated_at         timestamptz not null default now(),
    constraint session_status_ck check (status in ('active','completed','archived')),
    constraint session_fork_ck   check ((parent_session_id is null) = (forked_at_seq is null))
);

create unique index session_native_uq
    on session (provider, native_session_id) where native_session_id is not null;
create index session_browse_ix  on session (workspace_hash, started_at desc);
create index session_owner_ix   on session (owner, started_at desc);
create index session_parent_ix  on session (parent_session_id);

-- ── event (one CLI transcript record = one row, ordered by seq, append only) ──
create table event (
    event_id     text        primary key,                 -- NormalizedTurn.turn_id, or uuid5(SESSION_NS, session_id|seq) for meta rows
    session_id   text        not null references session(session_id) on delete cascade,
    seq          integer     not null,                     -- positional order across ALL records (turn + meta)
    kind         text        not null default 'turn',      -- turn | meta (meta = codex session_meta / turn_context, etc.)
    run_id       text        not null,
    provider     text        not null,
    cli          text        not null,
    role         text,                                     -- user|assistant|system|tool for turns; null for meta
    parent_id    text,                                     -- DAG parent (claude parentUuid); null at root
    is_sidechain boolean     not null default false,
    ts           timestamptz,
    model        text,
    raw          jsonb       not null,                     -- the parsed native CLI record (RawRecord); fork fidelity + portable resume
    ir           jsonb,                                    -- NormalizedTurn serialized (parts = list[ContentBlock]); null for meta rows
    source_path  text,                                     -- tier-1 transcript source
    source_line  integer,
    search_text  text,                                     -- text/thinking/tool text extracted from parts at ingest
    content_tsv  tsvector generated always as (to_tsvector('english', coalesce(search_text, ''))) stored,
    created_at   timestamptz not null default now(),
    constraint event_seq_uq unique (session_id, seq),
    constraint event_kind_ck check (kind in ('turn','meta'))
);

create index event_replay_ix on event (session_id, seq);   -- ordered replay / fork reconstruction
create index event_ir_gin    on event using gin (ir);       -- eval: ir @> '{"parts":[{"type":"tool_use","name":"Bash"}]}'
create index event_fts_gin   on event using gin (content_tsv); -- learn: content_tsv @@ websearch_to_tsquery(...)

-- ── artifact (by value, content-addressed, deduped by hash) ─────────
create table artifact (
    hash        text        primary key,                  -- blake2b-256 hex of the bytes
    media_type  text,                                      -- e.g. image/png
    size_bytes  bigint      not null,
    bytes       bytea       not null,                      -- the value; TOAST handles large/compressed transparently
    created_at  timestamptz not null default now()
);

create table event_artifact (
    event_id      text  not null references event(event_id) on delete cascade,
    artifact_hash text  not null references artifact(hash),
    ref           jsonb,                                   -- how the event referenced it (original path / source dict) for reconstruction
    primary key (event_id, artifact_hash)
);
```

### 2.1 Why these shapes

- `session` subsumes `OwnedSessionFacts` (`storage/session_facts.py:35`): the
  resumable-state pointer is `source_descriptor` + `home_dir` + `native_session_id`
  + `minted`. tier-1 `sessions.json` stays as the local durable copy; the row mirrors
  it. Columns map 1:1 from `index/adapters/base.py:SessionBinding` (which is the
  single canonical session contract per its docstring), promoting `source_descriptor`
  from TEXT-JSON to JSONB.
- `event` stores ONE row per CLI record (charter: "one CLI transcript record = one
  row"). `raw` is always present; `ir` is present only for conversational turns.
  This is forced by `index/adapters/base.py:TranscriptAdapter.normalize` returning
  `NormalizedTurn | None` (None = a non-conversational record such as codex
  `session_meta`/`turn_context`). The current tailer drops those records; the new
  ingest persists them as `kind='meta'` rows so the raw stream reconstructs the exact
  CLI transcript for fork (codex resume needs `turn_context.payload.model`). Render,
  eval, and FTS filter `WHERE kind='turn'`.
- `ir` mirrors `NormalizedTurn` (`index/adapters/base.py:133`): `parts` is the
  `ir.ContentBlock` union (`ir.py:68`). Storing it inline as JSONB replaces the
  `block`/`turn_block` normalize-and-edge model. The block model existed to power the
  cross-stream DIFF (identity-canonical hashing so wire and transcript content deduped
  to one block, `index/blocks.py:identity_canonical`). With the DIFF killed, inline
  IR is simpler: replay is a single-row read, eval is GIN containment, FTS is one
  generated column. TOAST compresses the JSONB; the de-dup space win does not justify
  the join cost once the DIFF is gone.
- `content_tsv` is a STORED generated tsvector over `search_text`, which ingest
  fills from the turn's text/thinking/tool text (the same text that fed
  `block.text` + `block_fts` today). This keeps text extraction in Python (the
  adapter already produced the parts) and FTS in Postgres.
- `event_ir_gin` uses default `jsonb_ops` (supports `@>` containment AND key-exists
  operators), so eval can ask both "tool X called" and "with input Y".
- Artifacts are `bytea` in-DB, deduped by `hash`. Rationale in §4.

### 2.2 Parked wire attach point (do not build)

A future `wire_exchange` table keyed by `exchange_id` attaches as a correlated
per-turn sibling: `session_id` FK plus an `(session_id, seq)` or `event_id`
correlation to `event`, with tier-1 raw pointers (`request.raw`/`response.raw`).
The `event.seq` + `event.session_id` columns are the join handle. Nothing in this
spec stores `request.ir`/`response.ir`/`request.raw`/`response.raw`/`transport.json`.

---

## 3. Ingest write path

### 3.1 Position in the system

The tailer is the seam. `index/tailer.py:TranscriptTailer` polls the CLI
transcript (one poll thread), tees a byte-faithful copy to
`transcripts/<session_id>.jsonl` (`storage/transcript_snapshot.py`), and for each
record calls the adapter. Today it builds an `IndexJob` and submits to the
SQLite `IndexWriter`. The change: submit to an async `SessionWriter` and persist
EVERY record (not just `normalize`-positive ones).

Per-record flow inside the tailer's consume loop:

1. Assign `seq` (monotonic per session across all records, so raw concat in
   `seq` order reproduces the transcript file).
2. `turn = adapter.normalize(record, ctx)` (`index/adapters/base.py:176`).
3. Compute `event_id`: `turn.turn_id` when `turn` is not None; else
   `uuid5(SESSION_NS, f"{session_id}|{seq}")` (`index/sessions.py` already owns
   `SESSION_NS` and `synth_session_id`; reuse it).
4. Capture artifacts by value (see §4): `refs = adapter.artifact_refs(record, turn)`.
5. Build `search_text` from `turn.parts` when present (text/thinking/tool text).
6. Submit one event job (raw always; ir + role + search_text only when `turn`).

The session row is upserted from the `SessionBinding` exactly where
`index/ingest.py:bind_exchange` does it today (carrying `cli`, `native_session_id`,
`source_descriptor`, `home_dir`, `minted` from the binding and the launch facts).

### 3.2 The async writer and the transaction + NOTIFY seam

Replace the thread-affine SQLite actor (`index/writer.py:IndexWriter`) with an
async writer over a psycopg3 pool (§9). One durable transaction per submitted unit:

```python
async def apply_event(conn, ev: EventRow, sess: SessionRow, artifacts: list[CapturedArtifact]):
    async with conn.transaction():                 # one durable txn
        await _upsert_session(conn, sess)          # ON CONFLICT (session_id) DO UPDATE, launch facts COALESCEd
        for a in artifacts:
            await _upsert_artifact(conn, a)         # ON CONFLICT (hash) DO NOTHING
        await _insert_event(conn, ev)              # ON CONFLICT (event_id) DO UPDATE (deterministic, idempotent)
        for a in artifacts:
            await _link_artifact(conn, ev.event_id, a.hash, a.ref)
        await conn.execute(
            "select pg_notify('tm_events', %s)", [ _notify_payload(ev) ],
        )
```

- The `NOTIFY` is enqueued inside the txn, so Postgres delivers it ON COMMIT and
  only on commit. The UI hears about a turn exactly when a query for it succeeds
  (the same durability invariant the SQLite writer enforces post-COMMIT,
  `index/writer.py:192` `_emit_events`). This honors the "emit only at the durable
  terminal seam" rule: persist the row, then signal; a rolled-back txn signals
  nothing and dangles no pointer.
- The tailer's cursor + snapshot offset advance only after the writer acks a
  durable commit, so a failed persist replays rather than skipping un-stored bytes
  (the tier-1 tee-and-advance gate from slice 8b-i carries over).

### 3.3 Idempotency / dedup key

- Event: PK `event_id` (deterministic from the native id or `uuid5(session_id|seq)`).
  `ON CONFLICT (event_id) DO UPDATE` is safe because `raw`/`ir` are deterministic
  functions of the record. `UNIQUE (session_id, seq)` guards ordering so a re-ingest
  cannot renumber. This mirrors the SQLite turn upsert keyed on `turn_id`
  (`index/ingest.py` `_TRANSCRIPT_UPSERT`).
- Session: `ON CONFLICT (session_id) DO UPDATE` with `COALESCE(session.col, excluded.col)`
  for launch-authoritative nullable facts (`cli`, `native_session_id`,
  `source_descriptor`, `home_dir`) so a later wire-side or rebuild upsert never
  clobbers a populated launch fact to NULL. `minted` is set once at bind and not
  downgraded.
- Artifact: PK `hash`, `ON CONFLICT (hash) DO NOTHING`. Identical bytes from any
  event dedup to one row.

### 3.4 Backfill reuses the replay core

`index/rebuild.py:replay_run(writer, run_dir)` and `backfill(writer,
workspaces_root, run_id)` already walk tier-1 and replay through a writer. The
Postgres backfill is the SAME traversal with the async writer target. The
per-record helper `_replay_transcript` (`index/rebuild.py:250`) re-uses
`adapter.normalize`; the only change is the job it builds (a Postgres event upsert
instead of `index/ingest.py:build_transcript_job`). No second traversal, no parallel
adapter logic.

---

## 4. Artifacts by value

### 4.1 What exists vs what is new

By-value artifact capture does NOT exist today. The codex "derived artifacts"
written by `storage/disk.py:DiskStorageBackend.write_codex_derived_artifacts`
(`events.jsonl`, `turn.json`) are wire-derived and PARKED. Generated images
currently ride inline in `ir.py:ImageBlock.source` (`dict[str, Any]`). The charter
wants the bytes copied in and content-addressed so a shared or replayed session is
self-contained (codex images written to `~/.codex.lilo/generated_images/...` travel
with the session).

### 4.2 The adapter hook

Add one method to the transcript adapter port (`index/adapters/base.py:TranscriptAdapter`),
mirroring `model_hint`:

```python
def artifact_refs(self, record: RawRecord, turn: NormalizedTurn | None) -> list[ArtifactRef]:
    """Local artifact file references this record points at (provider-specific).
    Default: [] (formats with inline-only content need no capture)."""
    return []
```

`ArtifactRef` is a frozen Pydantic model `{ path: str, media_type: str | None,
ref: dict[str, Any] }`. The codex adapter (`index/adapters/codex.py`) overrides it
to surface `generated_images` paths from the tool record; claude inherits the
default. Keeping provider specifics in the adapter (the anti-corruption layer) is
consistent with the existing design and keeps `session/ingest.py` provider-neutral.

### 4.3 Capture mechanics

At ingest, for each `ArtifactRef`:

1. Read the bytes from `ref.path` once.
2. `hash = blake2b_256_hex(bytes)` (a `session/artifacts.py:artifact_hash`, sibling
   to `index/blocks.py:block_hash` but over raw bytes, not canonical JSON; reuse the
   same blake2b-256 family already used for content identity).
3. Upsert `artifact (hash, media_type, size_bytes, bytes)` `ON CONFLICT (hash) DO NOTHING`.
4. Insert `event_artifact (event_id, artifact_hash, ref)` so replay/export resolve
   the bytes and reconstruction can rewrite the original reference.

Reading bytes at ingest (not later) matters: codex's `generated_images` are local
files that the CLI may GC; the bytes must be copied while they exist, exactly as
the transcript snapshot owns transcript bytes at read time.

### 4.4 bytea-in-DB vs external CAS

Decision: `bytea` in-DB, deduped by hash.

- The charter's first principle is "Postgres is the durable, first-class asset."
  An external filesystem CAS reintroduces a second storage tier, path resolution,
  and GC, and breaks "a session row-set is self-contained and portable."
- A session export is then a subset of rows (§6). Share = copy rows. Cross-machine
  works because the bytes travel.
- Codex images are KB-MB; dedup by hash bounds growth; Postgres TOAST stores large
  `bytea` out-of-line and compressed.
- Escape hatch for hosted scale (future, not now): an optional `storage_url`
  column could point at object storage while keeping `hash` as the address. Out of
  scope here.

---

## 5. Fork

### 5.1 Lineage model

A fork creates a new `session` row: fresh `session_id`, `owner` = current,
`status='active'`, `parent_session_id` = source, `forked_at_seq = N`. Lineage is a
recursive CTE over `parent_session_id`. The `session_fork_ck` constraint keeps
`parent_session_id` and `forked_at_seq` set together.

### 5.2 Reconstruct a CLI-resumable session

`session/fork.py` in one transaction:

1. Mint a fresh native id and compute the owned transcript source via the launch
   profile: `cli/launch_profile.py:prepare_managed_session` (claude path via
   `index/adapters/claude.py:claude_transcript_source`; codex via
   `cli/codex_session.py:seed_codex_session`).
2. Read `SELECT raw FROM event WHERE session_id = :src AND seq <= :N ORDER BY seq`.
3. Write the reconstructed transcript file at the new owned path: one
   `json.dumps(raw)` line per record, in `seq` order. Rewrite records that embed
   the old session id (codex `session_meta.payload.id`; any provider self-id) to the
   new native id. The parsed-dict raw is resume-faithful: the CLI re-parses JSONL
   line by line and does not require byte identity (whitespace/key-order are
   irrelevant to it). The byte-faithful tier-1 snapshot remains the forensic copy;
   fork uses the portable DB raw so it works after tier-1 is gone or on a hosted
   instance.
4. Copy events `1..N` into the new session under regenerated `event_id`s
   (`uuid5(SESSION_NS, new_session_id|seq)`), copying `raw`/`ir`/`kind`/`role` and
   re-linking `event_artifact` rows (artifacts dedup by `hash`, so no bytes copy).
5. Persist `sessions.json` for the new run (`storage/session_facts.py:write_owned_session_facts`)
   and the session row.
6. Relaunch via launch ownership: claude `--session-id <new>`
   (`cli/launch_profile.py:ClaudeLaunchProfile`); codex `resume <new>`
   (`CodexLaunchProfile`). The CLI loads the reconstructed transcript and resumes at
   `N+1`.

Both providers are covered (see §11.2 for the evidence that raw suffices).

---

## 6. Share / export

### 6.1 Bundle format

A self-contained `.tmsession` bundle: gzipped JSON-lines.

- Line 1: a manifest object `{ format_version, exported_at, session: <session row,
  owner stub included>, lineage: [parent stubs] }`.
- Then one line per `event` row (raw + ir + kind + edges) in `seq` order.
- Then one line per referenced `artifact` `{ hash, media_type, size_bytes,
  bytes_b64 }`.

JSON-lines streams without loading the whole session in memory and keeps large
artifact bytes off the manifest line.

### 6.2 Import and id stability

`POST /api/sessions/import` streams the bundle into one transaction:
`ON CONFLICT (session_id) DO NOTHING` for the session, `ON CONFLICT (event_id)`
and `ON CONFLICT (hash)` for events and artifacts. `session_id` and `event_id` are
stable global keys (native ids or deterministic uuid5), so re-import is idempotent
and a collision means "already present." Import re-owns the session to the
importing user: `owner` is rewritten to the local user (real account on a hosted
instance). Lineage parent stubs import as `status='archived'` placeholders if the
parent is absent, so `parent_session_id` never dangles.

### 6.3 Hosting

Upload = the same bundle POSTed to a hosted instance's `/import`. Same schema, same
app, remote `DATABASE_URL`. The `owner` column and import re-owning are the
multi-tenant seam; per-owner row security (Postgres RLS keyed on `owner`) is the
hosting-ready privacy boundary, enabled later without a schema change.

---

## 7. Read surfaces

The FastAPI read layer keeps the SSE plumbing and replaces the block/pivot/diff
endpoints. Handlers run async over the pool. New routes under `api/v1/` (a
`session_routes.py` replacing `index_routes.py`):

| Capability | Endpoint | Query | Backed by |
| --- | --- | --- | --- |
| Replay | `GET /api/sessions/{id}/events?from=&to=` | seq range | `event` rows ordered by `seq`, render from `ir.parts` |
| Replay | `GET /api/sessions` | `workspace_hash`, `owner`, `provider`, `cli`, `status` | `session` list, `started_at desc` |
| Eval | `POST /api/sessions/events/search` | JSONB filter body | `WHERE ir @> :filter` over `event_ir_gin` |
| Learn | `POST /api/sessions/search` | `q`, filters | `content_tsv @@ websearch_to_tsquery('english', :q)`, ranked `ts_rank_cd` |
| Fork | `POST /api/sessions/{id}/fork?at_seq=N` | - | §5 |
| Share | `GET /api/sessions/{id}/export` | - | §6 bundle |
| Share | `POST /api/sessions/import` | bundle body | §6 import |
| Artifact | `GET /api/artifacts/{hash}` | - | `bytea` stream with `media_type` |

Live append: the existing SSE endpoint (`api/v1/stream.py` `GET /stream`, fed by
the broadcast hub) is unchanged. A single server-side listener connection
(`session/listen.py`) holds `LISTEN tm_events` and forwards each notification via
the existing `broadcast.emit`, so the SSE consumer and event shape stay the same as
the current transcript-turn event (mirroring `index/ingest.py` `build_transcript_job`'s
event dict: `session_id`, `event_id`, `seq`, `role`, `ts`, `is_sidechain`, `cli`,
`provider`). Decoupling the writer from the event loop also makes live append work
across processes (any app instance NOTIFYs; the listener fans out), which the
`call_soon_threadsafe` bridge (`index/writer.py:201`) could not.

Retires with the DIFF: `session_pivot`, `session_diff`, the wire `stream=wire`
timeline, the two-phase block search, and the `/pivot` + `/diff` routes
(`index/queries.py`, `api/v1/index_routes.py`).

NOTIFY payload note: Postgres caps a notification at 8000 bytes; the payload
carries only the small render fields above. The SSE consumer fetches the body via
the replay endpoint if it needs `ir`. This keeps NOTIFY safe and the stream thin.

---

## 8. Migration

This store is durable: forward Alembic migrations only, no drop-and-rebuild gate.

1. Add deps: `psycopg[binary,pool]`, `alembic`. Add a `DATABASE_URL` setting
   (charter), with a dev default DSN and a `docker-compose.yml` (§9).
2. Stand up `session/` (§10) and the Alembic env under `api/migrations/`. The
   initial migration is the §2 DDL. `schema_meta` and its drop-rebuild boot gate
   (`index/schema.py`) do NOT carry over; Alembic's version table replaces it.
3. Backfill once from tier-1: `session/backfill.py` reuses
   `index/rebuild.py:backfill`/`replay_run` with the Postgres writer, reading
   `transcripts/<session_id>.jsonl` snapshots and `sessions.json` per run. After
   backfill, Postgres is authoritative.
4. Retire the SQLite tier-2: delete `index/db.py`, `index/schema.py`,
   `index/writer.py`, `index/ingest.py`, `index/queries.py`, `index/blocks.py`,
   `index/models.py`, `index/maintenance.py`, `index/rebuild.py` and their tests
   once `session/` covers them; delete `~/.transport-matters/index.db`. Keep
   `index/adapters`, `index/tailer`, `index/sessions`.
5. Forensic raw boundary: tier-1 STAYS. Kept as forensic and as a transcript fork
   source are the per-exchange wire raw (`request.raw`, `response.raw`,
   `transport.json`, codex `events.jsonl`/`turn.json`), `sessions.json`, and
   `transcripts/<session_id>.jsonl`. The PARKED wire store will later consume the
   wire raw; the transcript snapshot is now redundant with `event.raw` for fork but
   retained as the byte-faithful forensic copy and the backfill source.

DRY note: the launch path already writes `sessions.json`; the session row is a
mirror, not a second source. Backfill reads it; live ingest derives it from the
`SessionBinding`. One producer, one shape (`OwnedSessionFacts` /
`SessionBinding`).

---

## 9. Async driver, pool, config

Driver: psycopg3 (`psycopg[binary,pool]`) with `psycopg_pool.AsyncConnectionPool`.

- Dual sync + async in one library. The server read/ingest paths are async
  (FastAPI), but backfill and the launch/CLI paths run on sync OS threads today
  (`index/writer.py` is a sync OS-thread actor; `index/rebuild.py` is sync). psycopg3
  lets both share one driver and one SQL surface with no duplicated query layer.
- LISTEN/NOTIFY: psycopg3's `AsyncConnection.notifies()` async generator is the
  clean live-append seam (§7).
- First-class JSONB adaptation, `COPY` for fast backfill, and server-side cursors.
- asyncpg is faster on raw throughput and is the alternative; psycopg3 wins here on
  the dual-mode requirement and the NOTIFY ergonomics. Recorded as Open question C.

Pool lifecycle: open the `AsyncConnectionPool` at app startup (the FastAPI lifespan
/ `load_runtime()` wiring point where `IndexWriter.start` is called today,
`index/writer.py:80`), inject it as the write sink and read dependency, and close it
on shutdown. Keep pool utilization < 80% (a bounded `max_size`, default ~10 local).

Config:

- Setting `DATABASE_URL` (a `pydantic-settings` field), e.g.
  `postgresql://tm:tm@localhost:5432/transport_matters`. Provisioning is not the
  app's job (charter); docker, local, or cloud is just this value.
- Dev `docker-compose.yml` at repo root: a single `postgres:17` service exposing
  5432 with the dev DSN above, a named volume, and a healthcheck. `transport-matters
  doctor` gains a Postgres reachability + migration-head check.

---

## 10. Package layout and LOC budgets

New `session/` package (all files < 700 LOC, functions < ~150, builtins-only
typing, Pydantic v2, `Any` commented):

| File | Role | Budget |
| --- | --- | --- |
| `session/__init__.py` | public exports | ~40 |
| `session/pool.py` | `AsyncConnectionPool` + `DATABASE_URL` resolution | ~80 |
| `session/models.py` | frozen row models: `SessionRow`, `EventRow`, `ArtifactRow`, `ArtifactRef` | ~180 |
| `session/writer.py` | async writer: upsert seam + `pg_notify` (§3.2) | ~200 |
| `session/ingest.py` | `NormalizedTurn`/record -> event; `search_text` extraction; session upsert | ~250 |
| `session/artifacts.py` | `artifact_hash`, by-value capture + dedup (§4) | ~150 |
| `session/queries.py` | replay / eval / learn reads (§7) | ~300 |
| `session/fork.py` | reconstruct + lineage + relaunch (§5) | ~200 |
| `session/export.py` | bundle export + import (§6) | ~220 |
| `session/backfill.py` | tier-1 -> Postgres, reuses `replay_run` (§3.4, §8) | ~150 |
| `session/listen.py` | `LISTEN tm_events` -> `broadcast.emit` bridge (§7) | ~90 |
| `api/migrations/` | Alembic env + initial migration (§2 DDL) | ~280 |

Privacy boundary: the package follows the module-privacy rule (leading `_` is
module-private; no cross-module private imports;
`test_private_import_boundary.py`). Data privacy: `event.raw` may carry user
prompts and secrets; this is the user's own local session (local-first). On
share/export the bundle carries exactly what the session holds (owner's call); the
hosting privacy seam is per-`owner` Postgres RLS (§6.3), addable without a schema
change. The existing wire redaction (`transport_redaction`, imported by
`storage/disk.py`) is a wire-side concern and stays parked.

---

## 11. Verify, do not assume

### 11.1 Does the normalized IR round-trip well enough for faithful render

Yes for render; not byte-exact, which is why raw is stored alongside.

- The IR is the canonical render interchange by construction (`ir.py:1-8`: "the
  canonical interchange format between adapters, pipeline rules, storage, and the
  breakpoint editor"). The render path already builds the UI timeline from
  `NormalizedTurn.parts` (`index/models.py:TimelineEntry`, `TimelineBlock`).
- The `ContentBlock` union covers `text`, `tool_use`, `tool_result`, `thinking`,
  `image`, and `unknown` (`ir.py:68`), every block carries `provider_data`, and
  `UnknownBlock.raw` preserves unrecognized blocks verbatim (`ir.py:61-65`). So no
  record content is dropped on the render path.
- It is NOT byte-exact: `provider_data`/`cache_hint` are selectively preserved and
  ordering is normalized. Faithful BYTE reconstruction is the job of `raw`. Storing
  both `ir` (render/eval/FTS) and `raw` (fork) on each event directly encodes this
  split, which is the charter's stated reason for storing both.

### 11.2 Does the stored raw CLI record suffice to reconstruct a resumable session

Yes for both claude and codex.

- claude: the stored `raw` IS claude's JSONL transcript record (`type`, `uuid`,
  `parentUuid`, `timestamp`, `message{role,model,content}`, `isSidechain`). Write
  the records in `seq` order to a fresh `.jsonl` at the launch-profile path and
  launch `claude --session-id <new>` (`cli/launch_profile.py:ClaudeLaunchProfile`,
  which injects `--session-id` and computes the deterministic path via
  `index/adapters/claude.py:claude_transcript_source`).
- codex: the stored `raw` IS codex's rollout (`session_meta`, `turn_context`,
  `response_item`). Reconstruct preserving the `kind='meta'` rows (so
  `turn_context.payload.model` continuity survives), rewrite `session_meta.id` to
  the new native id, and launch `codex resume <new>`
  (`cli/launch_profile.py:CodexLaunchProfile` + `cli/codex_session.py:seed_codex_session`).
- Evidence the raw stream is complete and resumable: the tier-1 snapshot is already
  byte-faithful (`storage/transcript_snapshot.py`) and slice 8c proved tier-2 fully
  rebuildable from it alone (`index/rebuild.py:replay_run`, merged PR #32). Storing
  every record's `raw` in `event` (turn + meta) gives Postgres the same completeness
  the snapshot has, minus byte identity, which the CLI does not require to resume.
- The one nuance, recorded in the design: persisting `normalize`-None records as
  `kind='meta'` rows is mandatory for codex; turn-only storage would silently drop
  `turn_context`/`session_meta` and break codex resume.

---

## 12. Invariants checklist

- Import DAG: `session/` after `storage`, imports `ir` + `canonicalization` + the
  capture sub-tree; `storage` never imports `session`; sink injected at
  `load_runtime()`. No cycle.
- LOC: every new file < 700, every function < ~150 (§10 budgets).
- Typing: builtins-only (`list`, `dict`, `X | None`); every `Any` commented.
- Pydantic v2: `model_config = ConfigDict(frozen=True)` row models;
  `model_dump(mode="json")` for JSONB writes.
- IR frozen: unchanged; `ir.py` keeps importing nothing internal. The new
  `artifact_refs` hook lives on the adapter port, not on the IR.
- AST privacy: module-private `_` names; no cross-module private imports
  (`test_private_import_boundary.py`).
- Postgres-idiomatic: JSONB, GIN, `tsvector`, LISTEN/NOTIFY, Alembic.
- Durable store: forward migrations, no drop-rebuild.
- Hosting ready: `DATABASE_URL`, `owner` column, portable bundle.
- Wire exchanges: parked, left as a clean per-turn sibling attach point (§2.2).
- No em dashes.

---

## Open questions for orchestrator

- A. Package boundary. Working assumption: new `session/` package; retarget
  `index/tailer.py` to the async `SessionWriter`; keep `index/adapters`,
  `index/tailer`, `index/sessions`; delete the SQLite-only `index/` modules.
  Alternative: rename the surviving sub-tree to `capture/` and fold storage into
  `session/` for a cleaner name, at the cost of more import churn in the launcher
  and tailer. Recommend the lower-churn assumption.
- B. FTS config. Working assumption: `to_tsvector('english', ...)` for natural
  language Learn/browse. The retiring SQLite FTS used `unicode61` (no stemming);
  `'simple'` would match it more conservatively but loses stemming. Code-identifier
  exact match is served by the eval JSONB path, so `'english'` is preferred.
- C. Async driver. Working assumption: psycopg3 for dual sync/async + NOTIFY
  ergonomics. asyncpg is the faster alternative if the backfill/CLI sync paths are
  dropped in favor of a fully async ingest.
- D. Artifact reference discovery. Working assumption: an `artifact_refs` hook on
  the adapter port, codex-only override surfacing `generated_images` paths. Needs
  confirmation of the exact codex tool-record field that carries the image path
  (the codex adapter `normalize` and `ir.py:ImageBlock.source` shape) before the
  codex override is written.
- E. Migration cutover. Working assumption: one-time backfill then Postgres
  authoritative, SQLite tier-2 deleted in the same change. If a staged dual-write
  is wanted for safety, that is an explicit extra step; not assumed here.
