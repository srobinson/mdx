# Transport Matters — Session Store (buildable spec)

Author: backend-engineer/claude. Status: revised after review round 1.
Grounds the charter (`CHARTER.md`) in the actual repo. Every "Open question" is
resolved into a concrete design with `file:symbol` citations. Wire-exchange
storage is PARKED: the schema leaves a clean per-turn attach point but does not
specify it.

Paths are relative to `api/src/transport_matters/` unless noted.

## Round 2 changelog (resolves `review-session-store.md`)

1. Blocker (fork identity): `event` primary key is now `(session_id, seq)`;
   provider native ids are non-key per-session attributes; fork rekeying is
   provider-aware (§2, §5.3).
2. Blocker (resume unproven): the raw->JSONL resume claim is downgraded to a
   working assumption gated by mandatory provider fork fixtures (claude + codex)
   that are an acceptance gate on the fork slice; codex fork OWNS the rollout
   write (one rewritten `session_meta`) and relaunches with `prepare(write=False)`
   (§5.2, §5.4, §11.2).
3. Blocker (durable ack): a concrete `SessionWriter.submit_blocking(batch) ->
   CommitResult` seam, per-poll blocking, with backpressure / timeout /
   cancellation / shutdown and an explicit ownership rule (§3.2).
4. Major (backfill boundary): backfill no longer reuses `index/rebuild.py:replay_run`
   (it reads wire artifacts and is deleted). A transcript-only replay core is
   extracted from the existing `_replay_transcript`, depending only on kept
   modules, sequenced before the SQLite deletions (§3.4, §8).
5. Major (identity uniqueness): native-id uniqueness is scoped to
   `(owner, run_id, provider, native_session_id)`, aligned with the readback synth
   identity and the owner dimension (§2).
6. Major (artifact security): grounded finding is that codex images are inline
   base64 with NO file path; by-value capture reads INLINE record bytes only (zero
   filesystem reads, zero path-traversal surface). File-path capture is a future,
   default-off, allowlist-gated capability (§4).

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
- The live tailer: `index/tailer.py` (`TranscriptTailer`, `ingest_records`,
  `iter_complete_records`, `TailCursor`, `register_session_cursor`).
- Launch ownership: `cli/launch_profile.py` (`LaunchProfile`, `ClaudeLaunchProfile`,
  `CodexLaunchProfile`, `prepare_managed_session`, `persist_owned_session_facts`),
  `cli/codex_session.py` (`seed_codex_session`, `codex_rollout_path`,
  `build_session_meta`), and the durable owned-launch facts
  `storage/session_facts.py` (`OwnedSessionFacts`, `write_owned_session_facts`,
  `read_run_session_facts`).
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
breakpoint -> server`, with `index/` after `storage`, importing `ir` and
`canonicalization` only, never imported by `storage` (the sink is injected at
`load_runtime()`). The new `session/` package sits in the same slot:

- It imports `ir`, `canonicalization`, and the surviving capture sub-tree
  (`index/adapters`, `index/tailer`, `index/sessions`).
- `storage/` never imports `session/`. The write sink is injected at
  `load_runtime()`, exactly where `IndexWriter.start` is called today
  (`index/writer.py:80`; the live sink is built by `index/ingest.py:make_index_sink`).
- `session/` may import `storage` read helpers (`storage/session_facts.py`,
  `storage/disk_layout.py`) for tier-1 backfill: a forward edge `session ->
  storage`, not the forbidden back-edge.

Working assumption A: create a new `session/` package; retarget `index/tailer.py`
to submit to the async `SessionWriter`; keep `index/adapters`, `index/tailer`,
`index/sessions`; delete the SQLite-only `index/` modules after the transcript
core is extracted (§3.4, §8).

### 1.2 Tier boundary after the migration

- Tier-1 (disk, KEPT): the per-run capture spool and forensic tier
  (`storage/disk_layout.py:DiskStorageLayout`), rooted at
  `~/.transport-matters/workspaces/{slug}/{hash}/{run_id}/` with `index.jsonl`,
  `sessions.json`, `transcripts/<session_id>.jsonl`, and per-exchange dirs holding
  the PARKED wire raw.
- Postgres (the durable asset): the session/event/artifact store. Backfilled once
  from tier-1, then authoritative. A session survives after its CLI transcript file
  is GC'd because every raw record lives in `event.raw`.

---

## 2. Postgres schema

DDL below is the initial Alembic migration. The event primary key is
`(session_id, seq)`: provider native ids are per-session attributes, not global
keys (review finding 1).

```sql
-- ── session ────────────────────────────────────────────────────────
create table session (
    session_id         text        primary key,          -- native id (minted/claude) or synth uuid5(run_id|provider|native) (readback/codex)
    provider           text        not null,              -- anthropic | codex | ...
    cli                text,                               -- claude | codex; null until the launcher plumbs it
    run_id             text        not null,
    cwd                text        not null default '',    -- not durably recoverable from tier-1 backfill (rebuild.py:308); '' allowed
    workspace_slug     text        not null,
    workspace_hash     text        not null,
    native_session_id  text,                               -- provider native id (uniqueness guard below)
    minted             boolean     not null default false, -- TM minted via --session-id (deferred; claude=True, codex=False)
    -- resumable-state pointer (subsumes storage/session_facts.py:OwnedSessionFacts):
    source_descriptor  jsonb,                              -- TranscriptSource (file_tail | pull)
    home_dir           text,                               -- managed --home-dir; null = CLI native home
    -- platform columns:
    owner              text        not null default 'local',
    status             text        not null default 'active',  -- active | completed | archived
    title              text,
    -- fork lineage:
    parent_session_id  text        references session(session_id),
    forked_at_seq      integer,                            -- fork point in the parent; null for a root
    started_at         timestamptz not null,
    created_at         timestamptz not null default now(),
    updated_at         timestamptz not null default now(),
    constraint session_status_ck check (status in ('active','completed','archived')),
    constraint session_fork_ck   check ((parent_session_id is null) = (forked_at_seq is null))
);

-- Native-id uniqueness scoped to the readback synth identity (run_id, provider,
-- native_session_id) PLUS owner, so two imports from different roots/tenants with
-- the same native id but distinct run_ids coexist (review finding 5; mirrors the
-- current run-scoped guard at index/schema.py:65-67 and sessions.py:22-28).
create unique index session_native_uq
    on session (owner, run_id, provider, native_session_id) where native_session_id is not null;
create index session_browse_ix on session (workspace_hash, started_at desc);
create index session_owner_ix  on session (owner, started_at desc);
create index session_parent_ix on session (parent_session_id);

-- ── event (one CLI transcript record = one row, ordered by seq, append only) ──
create table event (
    session_id       text        not null references session(session_id) on delete cascade,
    seq              integer     not null,                 -- positional order across ALL records (turn + meta)
    kind             text        not null default 'turn',  -- turn | meta (meta = codex session_meta / turn_context)
    -- provider turn identity is a per-session ATTRIBUTE, never the key (review finding 1):
    native_turn_id   text,                                 -- claude raw.uuid / ir.turn_id; codex uuid5(session_id|seq); null for meta
    parent_native_id text,                                 -- claude raw.parentUuid; null at root / linear formats
    parent_seq       integer,                              -- resolved DAG/linear parent within this session; null at root
    run_id           text        not null,
    provider         text        not null,
    cli              text        not null,
    role             text,                                 -- user|assistant|system|tool for turns; null for meta
    is_sidechain     boolean     not null default false,
    ts               timestamptz,
    model            text,
    raw              jsonb       not null,                 -- the parsed native CLI record; fork fidelity + portable resume
    ir               jsonb,                                -- NormalizedTurn serialized (parts = list[ContentBlock]); null for meta rows
    source_path      text,
    source_line      integer,
    search_text      text,                                 -- text/thinking/tool text extracted from parts at ingest
    content_tsv      tsvector generated always as (to_tsvector('english', coalesce(search_text, ''))) stored,
    created_at       timestamptz not null default now(),
    primary key (session_id, seq),
    constraint event_kind_ck check (kind in ('turn','meta'))
);

create index event_native_ix on event (session_id, native_turn_id);  -- fork remap + parent resolution
create index event_ir_gin    on event using gin (ir);                 -- eval: ir @> '{"parts":[{"type":"tool_use","name":"Bash"}]}'
create index event_fts_gin   on event using gin (content_tsv);        -- learn: content_tsv @@ websearch_to_tsquery(...)

-- ── artifact (by value, content-addressed, deduped by hash) ─────────
create table artifact (
    hash        text        primary key,                  -- blake2b-256 hex of the decoded bytes
    media_type  text,
    size_bytes  bigint      not null,
    bytes       bytea       not null,
    created_at  timestamptz not null default now()
);

create table event_artifact (
    session_id    text    not null,
    seq           integer not null,
    artifact_hash text    not null references artifact(hash),
    ref           jsonb,                                   -- where the bytes came from in the record (for reconstruction)
    primary key (session_id, seq, artifact_hash),
    foreign key (session_id, seq) references event(session_id, seq) on delete cascade
);
```

### 2.1 Why these shapes

- `event` primary key `(session_id, seq)`. Claude normalization sets
  `turn_id = record["uuid"]` and `parent_id = record["parentUuid"]`
  (`index/adapters/claude.py:111-134`); codex derives `turn_id =
  uuid5(SESSION_NS, session_id|seq)` (`index/adapters/codex.py:82-110`). A native
  uuid is unique only within its source session, so using it as a global key
  breaks fork (a re-tailed fork would re-emit the source's uuid). `(session_id,
  seq)` is the stable, provider-neutral key; `native_turn_id` / `parent_native_id`
  are non-key attributes for the parent graph and fork remap.
- `event` stores ONE row per CLI record (charter: "one CLI transcript record = one
  row"). `raw` is always present; `ir` only for conversational turns. This is forced
  by `normalize` returning `NormalizedTurn | None` (None = a non-conversational
  record, e.g. codex `session_meta`/`turn_context`, `index/adapters/codex.py:83-86`).
  The current `ingest_records` DROPS None records (`index/tailer.py:112-114`); the
  new ingest persists them as `kind='meta'` rows so the raw stream reconstructs the
  exact CLI transcript for fork (codex resume needs `turn_context.payload.model`
  continuity). Render, eval, FTS filter `WHERE kind='turn'`.
- `ir` mirrors `NormalizedTurn` (`index/adapters/base.py:133`): `parts` is the
  `ir.ContentBlock` union (`ir.py:68`). Storing it inline as JSONB replaces the
  `block`/`turn_block` normalize-and-edge model, which existed to power the
  cross-stream DIFF (`index/blocks.py:identity_canonical`). With the DIFF killed,
  inline IR is simpler: replay is a single-row read, eval is GIN containment, FTS is
  one generated column. TOAST compresses the JSONB.
- `content_tsv` is a STORED generated tsvector over `search_text`, filled by ingest
  from the turn's text/thinking/tool text (the text that fed `block.text` +
  `block_fts` today). `event_ir_gin` uses default `jsonb_ops` so eval can ask both
  containment (`@>`) and key-exists (`?`).
- Native-id uniqueness scope: `(owner, run_id, provider, native_session_id)`
  (review finding 5).
- Artifacts are `bytea` in-DB, deduped by `hash` (§4).

### 2.2 Parked wire attach point (do not build)

A future `wire_exchange` table keyed by `exchange_id` attaches as a correlated
per-turn sibling via `(session_id, seq)`, with tier-1 raw pointers. The
`event.seq` + `event.session_id` columns are the join handle. Nothing here stores
`request.ir`/`response.ir`/`request.raw`/`response.raw`/`transport.json`.

---

## 3. Ingest write path

### 3.1 Position in the system

The tailer is the seam. `index/tailer.py:TranscriptTailer._poll_cursor`
(`tailer.py:182-213`) stat-guards the file, reads new bytes from `cursor.byte_offset`,
tees a byte-faithful copy to `transcripts/<session_id>.jsonl` BEFORE normalize
(`tailer.py:200-207`), then runs the one record->turn loop `ingest_records`
(`tailer.py:84-114`), then advances `cursor.byte_offset` and `cursor.stat_signature`
LAST (`tailer.py:210-213`). The changes:

- `ingest_records` emits an event for EVERY record (turn -> `kind='turn'` with ir;
  None -> `kind='meta'`, raw only), instead of dropping None
  (`tailer.py:112-114`). The `seq`/`parent`/`model` threading is unchanged.
- It submits through the async `SessionWriter` with a durable ack (§3.2), not the
  fire-and-forget SQLite queue (`index/writer.py:86-98`).

The `seq`/`parent`/`model` threading is the single shared loop used by both
live-tail and backfill (`tailer.py:90-96`). To keep it DRY while changing the job
target, `ingest_records` takes an injected `build_event` callback (Postgres event
builder) and emits one job per record; the SQLite `build_transcript_job`
(`index/ingest.py:347`) is retired.

### 3.2 The async writer, the durable-ack seam, and ownership (review finding 3)

Replace the SQLite OS-thread actor (`index/writer.py:IndexWriter`) with an async
`SessionWriter` over a psycopg3 `AsyncConnectionPool` (§9), running its commit
coroutine on the server event loop captured at start (the same loop the current
writer holds for `call_soon_threadsafe`, `index/writer.py:63,201`).

The tailer is a sync poll thread (`tailer.py:174-176`). It gets a thread-safe
blocking submit that returns only after the Postgres commit:

```python
# called from the tailer thread, once per cursor poll, with the poll's records:
def submit_blocking(self, batch: EventBatch) -> CommitResult:
    fut = asyncio.run_coroutine_threadsafe(self._commit_batch(batch), self._loop)
    return fut.result(timeout=self._commit_timeout_s)   # blocks this thread until commit

async def _commit_batch(self, batch) -> CommitResult:
    async with self._pool.connection() as conn, conn.transaction():
        await _upsert_session(conn, batch.session)       # COALESCE launch facts (§3.3)
        for ev in batch.events:                          # every record (turn + meta)
            await _insert_event(conn, ev)
            for art in ev.artifacts:                     # inline-decoded artifacts (§4)
                await _upsert_artifact(conn, art)
                await _link_artifact(conn, ev.session_id, ev.seq, art)
        await conn.execute("select pg_notify('tm_events', %s)", [_notify_payload(batch)])
    return CommitResult(last_seq=batch.events[-1].seq, ok=True)
```

`_poll_cursor` reorders to gate the cursor on the commit:

1. Tee consumed bytes to tier-1 (`tailer.py:206-207`). Idempotent by snapshot file
   size (`storage/transcript_snapshot.py`), so a re-poll re-tees harmlessly.
2. `ingest_records` builds the batch and calls `submit_blocking(batch)`.
3. On `CommitResult.ok`: advance `cursor.byte_offset` and `cursor.stat_signature`.
4. On timeout/error: mark the run dirty, leave the cursor un-advanced, log, and let
   the next poll re-read and re-submit. Re-submit is safe because the event upsert is
   keyed on `(session_id, seq)` and is deterministic.

Ownership rule (mirrors the slice 8b-i "signature advances last" lesson):

- Snapshot bytes are owned at snapshot (tier-1, idempotent).
- Postgres rows are owned at commit.
- `cursor.byte_offset` + `cursor.stat_signature` advance ONLY after commit.

Backpressure: `submit_blocking` throttles the tailer thread (no further reads until
the batch commits); the pool `max_size` bounds DB concurrency (target < 80%
utilization). Timeout: `commit_timeout_s` default 5s. Cancellation/shutdown: stop
the tailer first so its final drain poll (`tailer.py:154-164`) commits synchronously,
then close the writer and pool (close order mirrors `TranscriptTailer.stop`'s
"before the writer's stop" note, `tailer.py:156-157`). NOTIFY is enqueued inside the
txn, so Postgres delivers it only on commit; the live signal is tied to durability,
the same invariant the SQLite writer enforced post-COMMIT (`index/writer.py:192`).

Alternative considered: convert the tailer consume loop to async. Rejected for now
as higher churn against the proven sync poll/snapshot logic; `submit_blocking` is
the smaller seam. Recorded as Open question A.

### 3.3 Idempotency / dedup key

- Event: PK `(session_id, seq)`. `ON CONFLICT (session_id, seq) DO UPDATE` is safe
  because `raw`/`ir` are deterministic functions of the record. Mirrors the SQLite
  turn upsert idempotency (`index/ingest.py:_TRANSCRIPT_UPSERT`).
- Session: `ON CONFLICT (session_id) DO UPDATE` with `COALESCE(session.col,
  excluded.col)` for launch-authoritative nullable facts (`cli`,
  `native_session_id`, `source_descriptor`, `home_dir`) so a later upsert never
  clobbers a populated launch fact to NULL. `minted` is set once at bind.
- Artifact: PK `hash`, `ON CONFLICT (hash) DO NOTHING`.

### 3.4 Backfill reuses a transcript-only replay core (review finding 4)

`index/rebuild.py:replay_run` (`rebuild.py:71-101`) is NOT transcript only: it reads
`index.jsonl`, reads per-exchange wire artifacts (`_read_exchange`), calls
`bind_exchange`, and submits `build_wire_job` before the transcript pass. Reusing it
would build the PARKED wire store and depend on SQLite modules this spec deletes.

The transcript-only core already exists as the private `_replay_transcript`
(`rebuild.py:250-294`): it reads `sessions.json` (`read_run_session_facts`),
reconstructs the session_id (native if minted, else `synth_session_id`), decodes the
descriptor (`decode_source_descriptor`), reads the snapshot bytes
(`layout.transcript_snapshot_path`), builds a `SessionBinding`, and drives
`ingest_records`. Its dependencies are all KEPT modules
(`storage/session_facts`, `index/adapters/base`, `index/sessions`,
`index/adapters`, `index/tailer`, `storage/disk_layout`).

Plan: lift that logic into a public `session/backfill.py:replay_transcript_run(writer,
run_dir)` that yields `(binding, record, seq, source)` (or drives the writer via
`ingest_records`) with NO wire reads, NO `bind_exchange` wire path, NO
`build_wire_job`. `backfill(writer, workspaces_root, run_id=None)` walks tier-1 run
dirs calling it. Sequence: extract the transcript core FIRST, then delete
`index/rebuild.py`, `index/ingest.py`, `index/writer.py`, and the other SQLite
modules (§8).

---

## 4. Artifacts by value (review finding 6)

### 4.1 Grounded finding: codex images are inline, not file paths

There is no generated-image FILE PATH in any codex record. Codex sends images as
inline `data:` URIs: `codex/request_parser.py:_parse_user_extra_block`
(`request_parser.py:258-262`) maps an `input_image` item to
`ImageBlock(source={"image_url": "data:image/png;base64,...", "detail": ...})`;
fixture `api/tests/fixtures/codex_response_create.json:14-16` confirms the wire
shape. Claude transcript images are also inline base64
(`source={"type":"base64","media_type":...,"data":...}`, fixture
`claude_transcript.jsonl:7`). The codex TRANSCRIPT adapter carries no images at all:
non-text content is preserved as `UnknownBlock` (`index/adapters/codex.py:138-140`),
because codex images live only in the wire request (PARKED), not the rollout.

Consequence: in the session (transcript) store, the only inline artifacts are CLAUDE
transcript image blocks. Codex generated images are a WIRE concern owned by the
parked wire store, not this one. The charter's "codex images travel with the
session" is satisfied for the transcript store by capturing claude's inline image
bytes by value; codex wire images attach later via the parked wire sibling.

### 4.2 Default capture: from inline record bytes only (no filesystem)

By-value capture reads bytes that are ALREADY in the record, never from a path:

- The adapter hook is `def inline_artifacts(self, turn: NormalizedTurn) ->
  list[InlineArtifact]` (default: scan `turn.parts` for `ImageBlock`, decode the
  base64 / `data:` payload from `ImageBlock.source`). No default authorizes any
  filesystem read.
- `InlineArtifact` is frozen Pydantic `{ media_type: str | None, data: bytes, ref:
  dict[str, Any] }` where `ref` records where in the block the bytes came from.
- At ingest: `hash = blake2b_256_hex(data)` (`session/artifacts.py:artifact_hash`,
  sibling to `index/blocks.py:block_hash` but over raw bytes); upsert `artifact`
  `ON CONFLICT (hash) DO NOTHING`; insert `event_artifact (session_id, seq,
  artifact_hash, ref)`.
- The stored `ir` replaces the inline blob with a pointer
  `{type:image, artifact_hash, media_type}`; `raw` is left untouched (it keeps the
  original inline bytes for byte-faithful fork reconstruction). Render resolves the
  pointer via `GET /api/artifacts/{hash}` (§7). This gives dedup and keeps large
  blobs out of the event hot row while preserving both render and fork.

This removes the path-traversal / exfil surface entirely (review finding 6): the
ingest path copies only bytes the record already carried.

### 4.3 Future file-path capture (specified, default OFF, not enabled)

If a provider later emits an artifact FILE PATH, capture is enabled only behind an
explicit policy, never by the default hook:

- Allowlist of safe roots: the managed codex generated-images dir under
  `cli/home_seed.py:_default_codex_home` / `codex_sessions_root` (`home_seed.py:139-166`)
  and a captured-tool-output dir. Absolute paths outside the allowlist are rejected.
- `os.path.realpath` canonicalization; reject any symlink that escapes the root.
- A max-size limit; a media-type sniff/validate; missing file is skipped and audited,
  never fails the turn.
- Every by-value capture writes an audit entry (path, hash, size, decision).

A fixture grounding the real provider field is a precondition before this path is
turned on. Today none exists, so it ships disabled (Open question D).

---

## 5. Fork

### 5.1 Lineage model

A fork creates a new `session` row: fresh `session_id`, `owner` = current,
`status='active'`, `parent_session_id` = source, `forked_at_seq = N`. Lineage is a
recursive CTE over `parent_session_id`; `session_fork_ck` keeps the pair set
together.

### 5.2 Provider-aware rekeying (review finding 1)

Because the PK is `(session_id, seq)`, copied fork rows never collide at the DB
level. The reconstructed transcript file must also produce ids unique to the new
session so a later re-tail of the fork cannot duplicate or collide with the source:

- Claude: build a deterministic old->new map `new_uuid = uuid5(new_session_id,
  old_uuid)`. For every copied record rewrite `raw.uuid` (via the map),
  `raw.parentUuid` (via the map; root stays null), `raw.sessionId = new native id`,
  and the derived `ir.turn_id` / `ir.parent_id` to match, plus the event columns
  `native_turn_id` / `parent_native_id` / `parent_seq`. A re-tailed fork then emits
  ids scoped to the new session (`index/adapters/claude.py:111-134` reads exactly
  these fields).
- Codex: keep seq-derived ids. `turn_id = uuid5(SESSION_NS, new_session_id|seq)`
  regenerates automatically when the new session is tailed
  (`index/adapters/codex.py:92-94`); only the rollout `session_meta.payload.id` is
  rewritten to the new native id (§5.4).

### 5.3 Reconstruct + relaunch

`session/fork.py`, in one transaction (all-or-nothing; not per-event savepoints):

1. Mint a fresh native id; compute the owned transcript source via the launch
   profile with `write=False` so the launch path computes the descriptor/path
   without seeding (`cli/launch_profile.py:prepare`, `prepare(..., write: bool)` at
   `launch_profile.py:88`).
2. `SELECT raw FROM event WHERE session_id=:src AND seq<=:N ORDER BY seq`.
3. Reconstruct the transcript file at the new owned path, rewriting ids per §5.2.
4. Copy events `1..N` into the new session (same `seq`), rewriting `raw`/`ir`/
   `native_turn_id`/`parent_native_id`/`parent_seq` per §5.2; re-link
   `event_artifact` (artifacts dedup by `hash`, no bytes copy).
5. Persist `sessions.json` for the new run
   (`storage/session_facts.py:write_owned_session_facts`) and the session row.
6. Relaunch: claude `--session-id <new>`; codex `resume <new>`. The launch uses
   `write=False`, so it does not re-seed the file fork already wrote.

### 5.4 Codex seed: fork owns the write (review finding 2)

`CodexLaunchProfile.prepare` normally seeds the rollout with one `session_meta`
line via `seed_codex_session` (`launch_profile.py:162-184`,
`cli/codex_session.py:74-102`). For fork, that seed must not duplicate:

- Fork OWNS the rollout write. It writes the new rollout itself: exactly ONE
  `build_session_meta(new_native_id, ...)` line (`cli/codex_session.py:55-71`) at the
  path from `codex_rollout_path(new_native_id, now, sessions_root=...)`
  (`codex_session.py:45-52`), followed by the historical `turn_context` / `response_item`
  raw rows in `seq` order.
- The fork relaunch calls the launch path with `prepare(write=False)` so
  `seed_codex_session` computes the descriptor but writes nothing
  (`codex_session.py:82,91-94`). No second `session_meta`, no discarded seed write.

Claude has no seed (`launch_profile.py:127`: `--session-id` creates the transcript),
so fork writes the reconstructed file and relaunches `--session-id <new>`; whether
claude resumes from a pre-existing file at the deterministic path is exactly what the
§11.2 fixture proves.

---

## 6. Share / export

### 6.1 Bundle format

A self-contained `.tmsession` bundle: gzipped JSON-lines.

- Line 1: manifest `{ format_version, exported_at, session: <row, owner stub>,
  lineage: [parent stubs] }`.
- Then one line per `event` row (raw + ir + kind + native attrs + artifact edges) in
  `(session_id, seq)` order.
- Then one line per referenced `artifact` `{ hash, media_type, size_bytes, bytes_b64 }`.

### 6.2 Import and id stability

`POST /api/sessions/import` streams into one transaction: `ON CONFLICT (session_id)
DO NOTHING` for the session, `ON CONFLICT (session_id, seq)` and `ON CONFLICT (hash)`
for events and artifacts. `session_id` is a stable global key (native uuid or
deterministic synth), so re-import is idempotent. Import re-owns the session to the
importing user (`owner` rewritten; native uniqueness is `(owner, run_id, provider,
native_session_id)`, so cross-tenant imports never collide, review finding 5).
Absent lineage parents import as `status='archived'` stubs so
`parent_session_id` never dangles.

### 6.3 Hosting

Upload = the same bundle POSTed to a hosted instance's `/import`. Same schema, same
app, remote `DATABASE_URL`. The `owner` column plus import re-owning is the
multi-tenant seam; per-owner Postgres RLS keyed on `owner` is the hosting-ready
privacy boundary, addable later without a schema change.

---

## 7. Read surfaces

Async handlers over the pool. New routes under `api/v1/` (a `session_routes.py`
replacing `index_routes.py`):

| Capability | Endpoint | Backed by |
| --- | --- | --- |
| Replay | `GET /api/sessions/{id}/events?from=&to=` | `event` rows ordered by `seq`, render from `ir.parts` (`kind='turn'`) |
| Replay | `GET /api/sessions` | `session` list, filters `workspace_hash`/`owner`/`provider`/`cli`/`status` |
| Eval | `POST /api/sessions/events/search` | `WHERE ir @> :filter` over `event_ir_gin` |
| Learn | `POST /api/sessions/search` | `content_tsv @@ websearch_to_tsquery('english', :q)`, `ts_rank_cd` |
| Fork | `POST /api/sessions/{id}/fork?at_seq=N` | §5 |
| Share | `GET /api/sessions/{id}/export`, `POST /api/sessions/import` | §6 |
| Artifact | `GET /api/artifacts/{hash}` | `bytea` stream with `media_type` |

Live append: the existing SSE endpoint (`api/v1/stream.py:GET /stream`, fed by the
broadcast hub) is unchanged. A single server-side listener (`session/listen.py`)
holds `LISTEN tm_events` and forwards each notification to `broadcast.emit`. The
NOTIFY payload carries only the small handle (`session_id`, `seq`, `kind`, `role`,
`ts`, `is_sidechain`, `cli`, `provider`) since Postgres caps a notification at 8000
bytes; the SSE consumer fetches the body via the replay endpoint. Decoupling the
writer from the loop also makes live append work across processes, which the
`call_soon_threadsafe` bridge (`index/writer.py:201`) could not.

Retires with the DIFF: `session_pivot`, `session_diff`, the wire `stream=wire`
timeline, the two-phase block search, and the `/pivot` + `/diff` routes
(`index/queries.py`, `api/v1/index_routes.py`).

---

## 8. Migration

Durable store: forward Alembic migrations only, no drop-and-rebuild gate.

1. Add deps `psycopg[binary,pool]`, `alembic`; add a `DATABASE_URL` setting with a
   dev default and `docker-compose.yml` (§9).
2. Stand up `session/` and the Alembic env under `api/migrations/`; the initial
   migration is the §2 DDL. `schema_meta` and its drop-rebuild boot gate
   (`index/schema.py`) do not carry over; Alembic's version table replaces them.
3. Extract the transcript-only replay core (§3.4) into `session/backfill.py`. THEN
   backfill once from tier-1 (`transcripts/<session_id>.jsonl` snapshots +
   `sessions.json`). After backfill, Postgres is authoritative.
4. Retire the SQLite tier-2 only AFTER the transcript core is extracted: delete
   `index/db.py`, `index/schema.py`, `index/writer.py`, `index/ingest.py`,
   `index/queries.py`, `index/blocks.py`, `index/models.py`, `index/maintenance.py`,
   `index/rebuild.py` and their tests; delete `~/.transport-matters/index.db`. Keep
   `index/adapters`, `index/tailer`, `index/sessions`.
5. Forensic raw boundary: tier-1 STAYS. Kept as forensic and fork source are the
   per-exchange wire raw (`request.raw`, `response.raw`, `transport.json`, codex
   `events.jsonl`/`turn.json`), `sessions.json`, and `transcripts/<session_id>.jsonl`.
   The PARKED wire store will later consume the wire raw; the snapshot is redundant
   with `event.raw` for fork but retained as the byte-faithful forensic copy and
   backfill source.

Working assumption E: one-time backfill then Postgres authoritative, SQLite tier-2
deleted in the same change (after the transcript core extraction). A staged
dual-write is an explicit extra step, not assumed.

---

## 9. Async driver, pool, config

Driver: psycopg3 (`psycopg[binary,pool]`) with `psycopg_pool.AsyncConnectionPool`.

- Dual sync + async in one library: server paths are async, but the tailer/backfill
  run on sync OS threads (`index/tailer.py` poll thread; `index/rebuild.py` sync), and
  the durable-ack seam bridges thread->loop (§3.2). psycopg3 shares one driver and SQL
  surface across both with no duplicated query layer.
- LISTEN/NOTIFY: psycopg3's `AsyncConnection.notifies()` is the clean live-append
  seam (§7). First-class JSONB adaptation, `COPY` for fast backfill, server-side
  cursors.
- asyncpg is the faster alternative; psycopg3 wins on the dual-mode requirement and
  NOTIFY ergonomics (Open question C).

Pool lifecycle: open at app startup (the `load_runtime()` wiring point where
`IndexWriter.start` is called today, `index/writer.py:80`), inject as the write sink
and read dependency, close on shutdown. Bound `max_size` (default ~10 local), target
utilization < 80%.

Config: setting `DATABASE_URL`
(`postgresql://tm:tm@localhost:5432/transport_matters` dev default). Provisioning is
not the app's job. Dev `docker-compose.yml` at repo root: a `postgres:17` service,
named volume, healthcheck. `transport-matters doctor` gains a Postgres reachability +
migration-head check.

---

## 10. Package layout and LOC budgets

New `session/` package (all files < 700 LOC, functions < ~150, builtins-only typing,
Pydantic v2, `Any` commented):

| File | Role | Budget |
| --- | --- | --- |
| `session/__init__.py` | public exports | ~40 |
| `session/pool.py` | `AsyncConnectionPool` + `DATABASE_URL` resolution | ~80 |
| `session/models.py` | frozen row models: `SessionRow`, `EventRow`, `ArtifactRow`, `InlineArtifact` | ~190 |
| `session/writer.py` | async `SessionWriter`: `submit_blocking`, `_commit_batch`, `pg_notify` (§3.2) | ~220 |
| `session/ingest.py` | record -> event (turn + meta); `search_text`; session upsert; `build_event` for `ingest_records` | ~260 |
| `session/artifacts.py` | `artifact_hash`, inline-decode capture + dedup (§4) | ~150 |
| `session/queries.py` | replay / eval / learn reads (§7) | ~300 |
| `session/fork.py` | reconstruct + provider-aware rekey + lineage + relaunch (§5) | ~260 |
| `session/export.py` | bundle export + import (§6) | ~220 |
| `session/backfill.py` | transcript-only replay core, tier-1 -> Postgres (§3.4, §8) | ~170 |
| `session/listen.py` | `LISTEN tm_events` -> `broadcast.emit` bridge (§7) | ~90 |
| `api/migrations/` | Alembic env + initial migration (§2 DDL) | ~300 |

Privacy boundary: module-privacy rule (leading `_` module-private; no cross-module
private imports, `test_private_import_boundary.py`). Data privacy: `event.raw` may
carry user prompts/secrets; this is the user's own local session. On share/export the
bundle carries exactly what the session holds; the hosting privacy seam is per-`owner`
RLS (§6.3). Wire redaction (`transport_redaction`) stays a parked wire concern.

---

## 11. Verify, do not assume

### 11.1 Does the normalized IR round-trip well enough for faithful render

Yes for render; not byte-exact, which is why raw is stored alongside.

- The IR is the canonical render interchange by construction (`ir.py:1-8`); the UI
  timeline already renders from `NormalizedTurn.parts` (`index/models.py:TimelineEntry`).
- The `ContentBlock` union covers `text`, `tool_use`, `tool_result`, `thinking`,
  `image`, `unknown` (`ir.py:68`); every block carries `provider_data`, and
  `UnknownBlock.raw` preserves unrecognized blocks verbatim (`ir.py:61-65`), so no
  record content is dropped on the render path.
- It is NOT byte-exact (selective `provider_data`, normalized ordering). Faithful BYTE
  reconstruction is `raw`'s job. Storing both `ir` and `raw` per event encodes this
  split, the charter's stated reason for storing both. (The inline-image pointer in
  `ir`, §4.2, is render-resolved via the artifact endpoint; `raw` keeps the original
  bytes.)

### 11.2 Does the stored raw CLI record suffice to reconstruct a resumable session

Working assumption: yes for both claude and codex. Per the charter this must be
PROVEN, not asserted (review finding 2). The proof is a mandatory acceptance gate on
the fork slice, not a claim in this spec.

- What the repo already proves: the tier-1 snapshot is byte-faithful
  (`storage/transcript_snapshot.py`) and slice 8c rebuilt tier-2 from it alone
  (`index/rebuild.py:replay_run`, PR #32). That proves the captured record STREAM is
  complete, not that a Postgres JSONB round-trip reserializes to a CLI-acceptable file.
- Required fixtures (the gate):
  - Claude fork fixture: take stored `event.raw` rows 1..N, apply §5.2 rekeying,
    write a `.jsonl` at the launch-profile path, launch `claude --session-id <new>`,
    assert claude accepts the reconstructed transcript and appends at N+1. This also
    settles whether claude resumes from a pre-existing file at the deterministic path
    (`launch_profile.py:127`).
  - Codex fork fixture: reconstruct the rollout per §5.4 (one rewritten
    `session_meta` + historical rows), launch `codex resume <new>` with
    `prepare(write=False)`, assert codex resumes and appends with no duplicate
    `session_meta`.
- Evidence the fields suffice: claude `raw` carries `uuid`/`parentUuid`/`sessionId`/
  `message`/`isSidechain`/`timestamp` (`index/adapters/claude.py:111-134`); codex
  `raw` carries `session_meta`/`turn_context`/`response_item` with
  `turn_context.payload.model` (`index/adapters/codex.py:82-110`,
  `cli/codex_session.py:55-71`). Persisting every record (turn + `kind='meta'`) keeps
  the model-continuity records codex needs. The fixtures convert this from plausible
  to proven before the fork slice merges.

---

## 12. Invariants checklist

- Import DAG: `session/` after `storage`, imports `ir` + `canonicalization` + the
  capture sub-tree; `storage` never imports `session`; sink injected at
  `load_runtime()`. No cycle.
- LOC: every new file < 700, every function < ~150 (§10).
- Typing: builtins-only; every `Any` commented.
- Pydantic v2: frozen row models; `model_dump(mode="json")` for JSONB writes.
- IR frozen: unchanged; the inline-artifact hook lives on the adapter port, not the IR.
- AST privacy: module-private `_` names; no cross-module private imports.
- Postgres-idiomatic: JSONB, GIN, `tsvector`, LISTEN/NOTIFY, Alembic.
- Durable store: forward migrations, no drop-rebuild.
- Hosting ready: `DATABASE_URL`, `owner` column, portable bundle.
- Wire exchanges: parked, clean per-turn sibling attach point (§2.2).
- No em dashes.

---

## Open questions for orchestrator

- A. Durable-ack seam shape. Working assumption: keep the sync tailer thread and add
   `SessionWriter.submit_blocking(batch) -> CommitResult` (§3.2). Alternative: convert
   the tailer consume loop to async. Recommend the lower-churn blocking seam.
- B. FTS config. Working assumption: `to_tsvector('english', ...)` for natural-language
   Learn/browse; the retiring SQLite FTS used `unicode61` (no stemming). `'simple'`
   matches it more conservatively but loses stemming; the eval JSONB path serves exact
   identifier match, so `'english'` is preferred.
- C. Async driver. Working assumption: psycopg3 for dual sync/async + NOTIFY
   ergonomics. asyncpg is the faster alternative if the sync paths go fully async.
- D. Artifact capture scope. Working assumption: capture inline record bytes only;
   file-path capture is specified but default OFF (§4.3). Grounded finding: no provider
   emits an image FILE PATH today (codex inline base64, `request_parser.py:258-262`).
   Enabling file-path capture requires a fixture grounding the real field first.
- E. Migration cutover. Working assumption: one-time transcript-only backfill, then
   Postgres authoritative, SQLite tier-2 deleted after the transcript core extraction.
   A staged dual-write is an explicit extra step, not assumed.
- F. Fork resume proof location. Working assumption: the claude + codex fork fixtures
   (§11.2) are an acceptance gate on the fork slice and run the real CLIs. If real-CLI
   fixtures are too heavy for CI, an alternative is a parser-level acceptance test plus
   a manual road-test sign-off; flagging because the charter asked for a real proof.
