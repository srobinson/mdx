---
title: Transport Matters — Capture & Retrieval Substrate (items 1+2)
type: spec
tags: [transport-matters, storage, sqlite, fts5, capture, transcript, wire, moe-spec]
summary: Implementation-ready spec for persisting and searching both HTTP wire payloads and CLI transcripts via a hybrid two-tier store (tier-1 per-run raw bytes, tier-2 shared SQLite derived index).
status: all phases (A-D) signed off by MoE consensus; sections 1-15 approved
source: backend-engineer (MoE author = Claude, reviewer = Codex)
confidence: high
phase: A-D all signed off; sections 1-15 approved (Claude author + Codex reviewer)
brief: ~/.mdx/projects/transport-matters-capture-substrate-BRIEF.md
ledger: ~/.mdx/projects/transport-matters-capture-substrate-LEDGER.md
created: 2026-05-31
updated: 2026-05-31
---

# Transport Matters — Capture & Retrieval Substrate

> **Phased build.** This file accumulated approved sections across four MoE phases
> (each a fresh author/reviewer pair). All four phases (A-D) are signed off by both
> panes: sections **1-15** are approved. No placeholders remain.

## Table of contents

| #   | Section                                   | Phase | Status      |
| --- | ----------------------------------------- | ----- | ----------- |
| 1   | Scope & non-goals                         | A     | **Approved**  |
| 2   | Domain model / ubiquitous language        | A     | **Approved**  |
| 3   | Tier-2 SQLite DDL + block hashing + PRAGMAs | A   | **Approved**  |
| 4   | Provider adapter port + dataclasses       | B     | **Approved**  |
| 5   | Concrete adapters (claude/codex/gemini/opencode) | B | **Approved**  |
| 6   | Single machine-level indexer (process model) | C  | **Approved**  |
| 7   | Write path                                | C     | **Approved**  |
| 8   | Read path / query API                     | C     | **Approved**  |
| 9   | Live-tail                                 | D     | **Approved** |
| 10  | Delete + GC + rebuild                     | D     | **Approved** |
| 11  | Migration / first-boot backfill           | D     | **Approved** |
| 12  | Module / file layout                      | A     | **Approved**  |
| 13  | Test plan                                 | D     | **Approved** |
| 14  | Phasing (build order)                     | D     | **Approved** |
| 15  | Open risks / escalations                  | D     | **Approved** |

---

## 1. Scope & non-goals

### 1.1 Purpose

Persist and search **two distinct, first-class capture streams of the same coding
session**, kept separate but correlated:

- **Wire payloads** (roadmap item 1): the exact bytes the proxy sent/received over the
  HTTP/websocket transport — token counts, cache markers, provider framing, the full
  additive replay, injected system reminders, real tool schemas. *Transport truth.*
- **CLI transcripts** (roadmap item 2): the harness's own record of the conversation
  (e.g. claude's `~/.claude/projects/<slug>/<uuid>.jsonl`) — clean turn boundaries, a
  stable uuid/parent DAG, tool_use/tool_result pairing, subagent markers. *Semantic /
  human truth.*

The analysis value is the **DIFF** between the two (what the harness/human believes vs
what actually hit the provider). The streams are **never collapsed** into one another.

### 1.2 In scope (this spec, all phases)

1. A **hybrid two-tier store**: tier-1 = the existing per-run directory (source of
   truth for raw bytes, largely unchanged); tier-2 = one shared, rebuildable SQLite
   index at `~/.transport-matters/index.db`.
2. A **global content-addressed `block` table** (blake2b) that dedups message/content
   bodies once across both streams and across all runs/CLIs.
3. **FTS5 (BM25) lexical search** over blocks, covering both streams with one index,
   plus structured filter columns.
4. A **provider adapter port** (the transcript-side twin of `ir.py`) and concrete
   adapters for claude, codex, gemini, opencode (Phase B).
5. A **single machine-level indexer**, write/read paths, **live-tail**, **delete+GC**,
   and **migration/backfill** (Phases C/D).

### 1.3 Non-goals (explicitly out)

- **Realtime compaction / compression** (roadmap item 3). The store models
  `request_curated_ir` already; compaction policy is a separate effort.
- **Vector / semantic search** (sqlite-vec). FTS5 lexical first. Vector is a *later
  optional slice*; this spec mentions it only as a forward hook (see §3.7).
- **UI work.** How the littleorgans cockpit renders timelines/diffs is downstream. This
  spec only guarantees the data + query surface the UI consumes (and reuse of the
  existing `broadcast.py`/`sse.py` for live-tail, Phase D).
- **Multi-machine / networked index.** Tier-2 is a single local SQLite file for a
  single-user machine. No replication, no server DB.
- **Backward compatibility.** Single-user repo. Schema changes may nuke the tier-2
  index freely (it is a pure projection of tier-1). No migration shims.

### 1.4 Hard constraints (carried from CLAUDE.md / repo conventions)

- New code files ≤ 700 LOC; functions ≤ ~150 LOC.
- Python: builtins-only typing (`list[str]`, `dict[str, Any]`, `X | None`), annotate
  all return types, `Any` requires a comment. Pydantic v2 (`ConfigDict`,
  `model_dump(mode="json")`); IR models stay `frozen=True`.
- Import DAG (no cycles): `ir → adapters → rules → pipeline → storage → breakpoint →
  server`. The new tier-2 package sits **after `storage`** (it projects storage
  artifacts) and may import `ir` and the canonicalization helpers only (see §12).
- I/O async; pure computation (hashing, canonicalization, row mapping) sync.

---

## 2. Domain model / ubiquitous language

One crisp definition per term. These names are load-bearing: tables, dataclasses, and
adapter methods all use them verbatim.

- **workspace** — a working directory, identified by `WorkspaceId{slug, hash, root}`
  (`workspace.py`). `slug` is the `/`→`-` slugified absolute cwd; `hash` is
  `blake2b(cwd, digest_size=4).hexdigest()` (8 hex). Tier-1 lives under
  `~/.transport-matters/workspaces/{slug}/{hash}/`.

- **run** — one launch of one CLI under one workspace, keyed by `run_id` (a UUID). Its
  tier-1 directory is `workspaces/{slug}/{hash}/{run_id}/` (`workspace.run_root`) and
  holds the lock, manifest, and all captured exchanges/transcript sources. `rm -rf` on
  that dir cleanly wipes a single run; corruption blast radius is one run. Multiple
  runs may share a workspace concurrently (multi-instance, commit `a8dd8ed`).

- **session** — one provider/CLI conversation thread inside a run, keyed by
  `session_id` (the **correlation key**, see below). Usually 1:1 with a run; a run may
  hold several sessions (codex resume/fork). Subagent/sidechain turns share the parent
  `session_id` and carry `is_sidechain = 1`.

- **wire_exchange** — one captured HTTP/websocket request→response round trip on the
  wire, keyed by the existing exchange id (`IndexEntry.id`). Carries transport metadata
  (model, token/char stats, stop reason, `mutated_manually`) and a pointer to its
  tier-1 raw directory. Its ordered content parts are recorded as `exchange_block`
  edges. A wire_exchange may exist **before** it is correlated to a session
  (`session_id` nullable).

- **transcript_turn** — one turn in a CLI transcript, keyed by an adapter-stable
  `turn_id` (claude `uuid`; synthesized for providers without a per-record id). Carries
  `role`, `parent_id` (the DAG link), `seq`, optional `ts`, `is_sidechain`, `model`,
  and a pointer to its tier-1 source (file + line where line-addressable). Its ordered
  content parts are recorded as `turn_block` edges. Always produced inside a bound
  session (`session_id` NOT NULL).

- **block** — a single, content-addressed unit of message/content body, shared globally
  across both streams and all runs/CLIs. Identity = `hash` = blake2b-256 over the
  **canonical form** of the part (§3.3). `kind` is the payload **shape**
  (`text | tool_use | tool_result | thinking | image | system | tool_def | unknown`) —
  *not* a role or a stream. Because the canonical form always embeds the type
  discriminator, `kind` is a pure function of `hash` (no two kinds can share a hash).
  The constant Anthropic `system`+`tools` is one block-set across every run and CLI;
  the additive wire replay collapses to repeated references to the same blocks.

- **edge** (`exchange_block` / `turn_block`) — an ordered reference from a stream entity
  to a block: `(entity_id, pos, block_id, role[, section])`. **Role**, **stream**,
  **section** (`system|tools|messages|response`), and **position** live here, on the
  edge — never on the block. This is what lets identical content authored under
  different roles/streams dedup to one block while preserving each reference's context.

- **correlation key** (`session_id`) — the universal join key between the two streams.
  Where we can **mint** it (claude, gemini: `--session-id <uuid>` we generate), the
  minted UUID is authoritative and the transcript path is known before the CLI writes a
  byte. Where we cannot (codex: read-back from the proxied frames), `session_id` is a
  deterministic synthesis over `(run_id, provider, native_session_id)`; opencode uses
  the export/session id. The `wire ↔ transcript` **pivot** = join on `session_id`,
  **sharpened** by exact block-hash intersection between `exchange_block` and
  `turn_block` (identical content → identical block → strong correspondence).

---

## 3. Tier-2 SQLite DDL + block hashing + PRAGMAs

Tier-2 is **one** SQLite database at `~/.transport-matters/index.db`
(`default_storage_root() / "index.db"`), WAL mode, a **pure rebuildable projection** of
tier-1. Any drift is repaired by nuke + replay (§10/§11, later phases).

### 3.1 Connection PRAGMAs (applied on every connection, in this order)

```sql
PRAGMA journal_mode = WAL;       -- concurrent readers + one writer; durable across crashes
PRAGMA foreign_keys = ON;        -- enforce edge→entity and edge→block integrity (load-bearing for GC)
PRAGMA busy_timeout = 5000;      -- 5s: cross-process writers wait rather than fail (multi-instance)
PRAGMA synchronous = NORMAL;     -- WAL-safe durability/throughput tradeoff for a rebuildable index
PRAGMA wal_autocheckpoint = 1000;-- bound WAL growth under bursty indexing
```

Rationale: WAL + `busy_timeout` is the single-writer discipline at the *file* level —
the "single machine-level indexer" invariant (roadmap) is realized by SQLite's own
write lock; the process model that owns writes is decided in Phase C (§6). `synchronous
= NORMAL` is acceptable precisely because tier-2 is rebuildable from tier-1.

### 3.2 Schema versioning (no migrations)

```sql
CREATE TABLE IF NOT EXISTS schema_meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
-- seeded on create:
--   ('schema_version',     '1')
--   ('block_hash_algo',    'blake2b-256')
--   ('identity_canonical', 'identity_canonical:v1')   -- semantic, provider_data-stripped (§3.3)
--   ('session_ns',         '<frozen SESSION_NS uuid>') -- read-back session_id synthesis namespace
```

On boot, if `schema_version` (or `identity_canonical`) does not match the code's expected
constant, the index is **dropped and rebuilt** from tier-1 (single-user, no-backcompat).
There are no `ALTER`-style migrations.

### 3.3 Block hashing — canonical form (the load-bearing definition)

**Identity input.** `block.hash = blake2b(identity_canonical(part).encode("utf-8"),
digest_size=32).hexdigest()` → 64 hex chars. `blake2b` is reused from `hashlib` (the
same primitive `workspace.py` uses; 32-byte digest here for a global table, vs the
4-byte workspace hash).

**Identity is SEMANTIC, not byte-exact.** Block identity exists to (a) dedup identical
content globally and (b) sharpen the wire↔transcript pivot (identical content → identical
hash across *both* streams). For (b) to hold, identity must be **stream-invariant**, so it
**strips transport-opaque fields**. Byte-exact reconstruction is **not** a block
responsibility: the exact source bytes always live in tier-1 (`wire_exchange.raw_dir`,
`transcript_turn.source_path`). The block reconstructs **semantic** (renderable) content
only.

**`identity_canonical(part)`** is field-ordered canonical JSON that **always emits `type`
first**. It follows the **same** `canonical_json` / `_canonical_fields` discipline as the
existing `canonical_block_json` (`override_audit.py:117`) — this is the reconciliation
with the production char-accounting canonicalization — with exactly **one uniform
divergence: `provider_data` (and `SystemPart.cache_hint`) are excluded from every kind.**
That divergence is what makes cross-stream dedup reliable: the Anthropic adapter folds
unknown provider siblings into `provider_data` (`_extra_provider_data`, anthropic.py:55-65),
so including it would make identical visible content hash differently across streams.

| kind          | source type (`ir.py`) | identity fields, in order (`provider_data` stripped) |
| ------------- | --------------------- | ---------------------------------------------------- |
| `text`        | `TextBlock`           | `type, text`                                         |
| `tool_use`    | `ToolUseBlock`        | `type, id, name, input`                              |
| `tool_result` | `ToolResultBlock`     | `type, tool_use_id, content[recursive], is_error`    |
| `thinking`    | `ThinkingBlock`       | `type, text`                                         |
| `image`       | `ImageBlock`          | `type, source`                                       |
| `unknown`     | `UnknownBlock`        | `type, raw`                                          |
| `system`      | `SystemPart`          | `type="system", text` (drop `cache_hint`)            |
| `tool_def`    | `ToolDef`             | `type="tool_def", name, description, input_schema`   |

> **Identity inclusions/exclusions, justified.**
> - `provider_data` / `cache_hint` **excluded** for all kinds (stream-invariance; the
>   exact bytes incl. `provider_data` remain in tier-1). If a future provider hides
>   *semantic* content in `provider_data`, that is an adapter bug — adapters must surface
>   semantic content as typed blocks, not opaque blobs.
> - `ToolUseBlock.id` / `ToolResultBlock.tool_use_id` **kept**: stable across the additive
>   wire replay and identical in the claude transcript, so they dedup within a session and
>   correctly distinguish calls across sessions.
> - `tool_def` keeps only `name/description/input_schema`, so the constant tools array
>   dedups to a fixed block-set across every run and CLI (the "constant tool-schema dedup"
>   goal, represented in the DDL as `tool_def` blocks).

Because `provider_data` is stripped uniformly, `identity_canonical` is **not**
`canonical_block_json` verbatim — it is a sibling encoder reusing the same helpers. (A
literal `canonical_block_json` reuse is therefore explicitly rejected here; see §12 for
the DRY placement of the canonical family.)

**Why `kind` is safe as a denormalized column.** `type` is the first field of
`identity_canonical` for *every* kind, so identical text under two shapes can never
collide (`{"type":"text",…}` ≠ `{"type":"thinking",…}` ≠ `{"type":"system",…}`).
`block.kind` is therefore functionally determined by `block.hash`; it is stored only for
fast filtering. **Role, stream, section, and position are never part of identity** — they
live on the edges (§3.5), which is what preserves cross-stream / cross-role dedup.

**Stored bodies.** Each block stores:
- `block.identity_canonical` = the exact `identity_canonical` string: the **hash input**
  and the **semantic reconstruction** source (parse back to a renderable part). It is
  deliberately **lossy** w.r.t. transport-opaque fields; byte-exact reconstruction is
  tier-1's job.
- `block.text` = a **clean FTS projection** (search text only): for `text|thinking|system`
  the raw string; for `tool_use` `name + " " + flattened(input)`; for `tool_result` the
  flattened text content; for `tool_def` `name + " " + description`; for `image` an empty
  string or media-type tag. Indexing `text` (not `identity_canonical`) keeps JSON envelope
  tokens out of BM25.

**Char accounting lives off the block (deliberately).** Production char accounting
(`count_chars_parts`, `override_audit.py:186`) is **occurrence-dependent** — it counts
`provider_data` and counts `system` as `len(text)` — so it is **not** a property of a
deduped, `provider_data`-stripped block, and the same content can carry different counts in
different occurrences. The authoritative production totals are therefore stored **per
exchange** on `wire_exchange.req_system_chars` / `req_tools_chars` / `req_messages_chars`
(computed by `count_chars_parts` at index time — exact reconciliation, the correct home).
The `block` table carries **no `n_chars`**. Per-occurrence char *attribution* (needed by
item-3 compaction) is deferred to an optional edge column, addable later because the index
is rebuildable.

`block.n_tokens` is a **best-effort content-level** token count of the block (nullable) —
a search/size hint only, explicitly **not** the production wire token accounting. It is a
**mutable annotation**: NULL on first insert and **back-fillable** later (Phase C), via
the conflict clause of the block write (§3.7).

**Immutability invariant (identity + search columns only).** For a given `id`, the
**identity- and search-bearing** columns — `hash`, `kind`, `identity_canonical`, `text` —
are frozen forever (a `hash` conflict means byte-identical `identity_canonical`, so these
never need to change). The **only** mutable column is `n_tokens`, a derived annotation that
may be filled when NULL or replaced by a better estimate. Because `text` never changes,
**no FTS update trigger is needed** — the INSERT/DELETE triggers (§3.6) stay sufficient.
The block write is therefore an **upsert that touches only `n_tokens`** (§3.7), never a
forbidden identity mutation.

### 3.4 Core tables

```sql
-- Global content-addressed block store -------------------------------------
CREATE TABLE block (
  id                 INTEGER PRIMARY KEY,     -- stable rowid; FTS external-content key
  hash               TEXT    NOT NULL UNIQUE, -- blake2b-256 hex of identity_canonical
  kind               TEXT    NOT NULL,        -- payload shape (functionally determined by hash)
  text               TEXT    NOT NULL DEFAULT '', -- clean FTS search projection
  identity_canonical TEXT    NOT NULL,        -- semantic hash input + semantic reconstruction (provider_data/cache_hint stripped); NOT byte-exact
  n_tokens           INTEGER,                  -- best-effort CONTENT token count; NULL unknown; NOT production wire accounting
  created_at         TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  CHECK (kind IN ('text','tool_use','tool_result','thinking','image','system','tool_def','unknown'))
);
CREATE INDEX block_kind ON block(kind);
-- Production char accounting is NOT on block (occurrence-dependent); it lives on
-- wire_exchange.req_*_chars below, computed via count_chars_parts at index time.

-- One conversation thread, the correlation anchor --------------------------
CREATE TABLE session (
  session_id        TEXT PRIMARY KEY,         -- universal correlation key AND idempotency key (see note)
  provider          TEXT NOT NULL,            -- wire provider family: anthropic|codex|gemini|opencode
  cli               TEXT,                      -- harness: claude|codex|gemini|opencode
  run_id            TEXT NOT NULL,            -- tier-1 run dir key
  cwd               TEXT NOT NULL,
  workspace_slug    TEXT NOT NULL,            -- WorkspaceId.slug
  workspace_hash    TEXT NOT NULL,            -- WorkspaceId.hash (blake2b-4)
  native_session_id TEXT,                      -- provider/CLI native id (codex thread; opencode ses_...); NULL allowed for minted
  minted            INTEGER NOT NULL DEFAULT 0,-- 1 = we minted session_id (claude/gemini); 0 = read-back
  source_descriptor TEXT,                      -- JSON: how to locate the transcript source (path / api ref)
  started_at        TEXT NOT NULL
);
-- NULL-safe secondary guard: at most one session may claim a given known native id.
-- Partial WHERE excludes the NULL native ids of minted sessions (avoids SQLite's
-- multiple-NULL UNIQUE hole that made the old table constraint non-idempotent).
CREATE UNIQUE INDEX session_native ON session(run_id, provider, native_session_id)
  WHERE native_session_id IS NOT NULL;
CREATE INDEX session_run       ON session(run_id);
CREATE INDEX session_workspace ON session(workspace_hash);
```

**`session_id` is the deterministic idempotency key (enforced by the PK, not prose).**
- **Minted** providers (claude, gemini): `session_id` = the UUID we mint via
  `--session-id`. Re-ingest with the same minted id → same PK → upsert.
- **Read-back** providers (codex; opencode by export id): `session_id =
  uuid5(SESSION_NS, f"{run_id}|{provider}|{native_session_id}")` with a fixed namespace
  constant `SESSION_NS`. The synthesis is pure, so re-ingesting the same
  `native_session_id` yields the same PK → upsert. (`SESSION_NS` is frozen in
  `index/` and bumping it is a schema-version change.)

The old `UNIQUE (run_id, provider, native_session_id)` table constraint is replaced by the
partial unique index above; idempotency now rests on the PK, which SQLite enforces with no
NULL hole.

```sql

-- Wire stream: one captured request→response round trip --------------------
CREATE TABLE wire_exchange (
  exchange_id        TEXT PRIMARY KEY,         -- existing IndexEntry.id
  session_id         TEXT,                      -- nullable: exchange may precede correlation
  run_id             TEXT NOT NULL,
  provider           TEXT NOT NULL,
  model              TEXT NOT NULL,
  ts                 TEXT NOT NULL,             -- IndexEntry.ts (ISO-8601)
  seq                INTEGER,                    -- monotonic order within session (assigned at index time)
  req_system_chars   INTEGER,                   -- from ReqStats
  req_tools_chars    INTEGER,
  req_messages_chars INTEGER,
  req_tokens         INTEGER,                   -- if counted
  res_tokens         INTEGER,
  stop_reason        TEXT,
  mutated_manually   INTEGER NOT NULL DEFAULT 0,
  raw_dir            TEXT NOT NULL,             -- tier-1 exchange dir (raw bytes via raw_path; never in tier-2)
  FOREIGN KEY (session_id) REFERENCES session(session_id) ON DELETE SET NULL
);
CREATE INDEX wire_exchange_session ON wire_exchange(session_id, seq);
CREATE INDEX wire_exchange_run     ON wire_exchange(run_id);
CREATE INDEX wire_exchange_ts      ON wire_exchange(ts);

-- Transcript stream: one harness turn --------------------------------------
CREATE TABLE transcript_turn (
  turn_id      TEXT PRIMARY KEY,               -- adapter-stable id (claude uuid; synth elsewhere)
  session_id   TEXT NOT NULL,                  -- always produced inside a bound session
  run_id       TEXT NOT NULL,
  provider     TEXT NOT NULL,
  cli          TEXT NOT NULL,
  parent_id    TEXT,                            -- DAG parent (claude parentUuid); NULL at root
  role         TEXT NOT NULL,                   -- user|assistant|system|tool
  seq          INTEGER NOT NULL,                -- positional order within session
  ts           TEXT,                            -- per-turn timestamp where available
  is_sidechain INTEGER NOT NULL DEFAULT 0,      -- subagent marker (claude isSidechain)
  model        TEXT,
  source_path  TEXT NOT NULL,                   -- tier-1 transcript source (jsonl path / export ref)
  source_line  INTEGER,                          -- line offset where line-addressable (claude/gemini jsonl)
  FOREIGN KEY (session_id) REFERENCES session(session_id) ON DELETE CASCADE
);
CREATE INDEX transcript_turn_session ON transcript_turn(session_id, seq);
CREATE INDEX transcript_turn_parent  ON transcript_turn(parent_id);
CREATE INDEX transcript_turn_run     ON transcript_turn(run_id);
```

> **Why the FK asymmetry is correct.** A `wire_exchange` is captured by the proxy
> independently and correlated to a session *later*, so its `session_id` is nullable and
> `ON DELETE SET NULL`. A `transcript_turn` is only ever emitted by an adapter under an
> already-bound session, so `session_id` is `NOT NULL` and `ON DELETE CASCADE`.

### 3.5 Edge tables (ordered block references; role/section live here)

```sql
CREATE TABLE exchange_block (
  exchange_id TEXT    NOT NULL,
  pos         INTEGER NOT NULL,                -- order within the exchange's flattened part stream
  block_id    INTEGER NOT NULL,
  role        TEXT    NOT NULL,                -- system|user|assistant|tool
  section     TEXT    NOT NULL,                -- system|tools|messages|response (which IR region)
  PRIMARY KEY (exchange_id, pos),
  FOREIGN KEY (exchange_id) REFERENCES wire_exchange(exchange_id) ON DELETE CASCADE,
  FOREIGN KEY (block_id)    REFERENCES block(id)
);
CREATE INDEX exchange_block_block ON exchange_block(block_id);

CREATE TABLE turn_block (
  turn_id  TEXT    NOT NULL,
  pos      INTEGER NOT NULL,
  block_id INTEGER NOT NULL,
  role     TEXT    NOT NULL,                   -- user|assistant|system|tool
  PRIMARY KEY (turn_id, pos),
  FOREIGN KEY (turn_id)  REFERENCES transcript_turn(turn_id) ON DELETE CASCADE,
  FOREIGN KEY (block_id) REFERENCES block(id)
);
CREATE INDEX turn_block_block ON turn_block(block_id);
```

Edges reference `block.id` (INTEGER) — compact joins and alignment with the FTS
`content_rowid`. The `block_id` FK has **no** cascade: with `foreign_keys = ON`, a block
cannot be deleted while any edge references it, so **GC** (Phase D) is a safe
mark-and-sweep: delete run-scoped rows (edges cascade away with their entity), then
`DELETE FROM block WHERE id NOT IN (SELECT block_id FROM exchange_block UNION SELECT
block_id FROM turn_block)`.

### 3.6 Full-text search (external-content FTS5 + triggers)

```sql
CREATE VIRTUAL TABLE block_fts USING fts5(
  text,
  content      = 'block',
  content_rowid= 'id',
  tokenize     = 'unicode61 remove_diacritics 2'
);

-- Incremental maintenance. Blocks are insert-or-ignore and IMMUTABLE, so only
-- INSERT and DELETE are possible; an UPDATE would violate content-addressing.
CREATE TRIGGER block_ai AFTER INSERT ON block BEGIN
  INSERT INTO block_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER block_ad AFTER DELETE ON block BEGIN
  INSERT INTO block_fts(block_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;
-- (No block_au trigger by design — see the immutability invariant in §3.3.)
```

- **Tokenizer**: `unicode61 remove_diacritics 2` — no stemming, so code identifiers and
  prose both survive intact. `porter` is rejected (it mangles identifiers). A `trigram`
  index for substring/code search is a **forward hook** (Phase C/D), not Phase A.
- **Bulk backfill / rebuild (Phase D nuke-and-replay):** load blocks with triggers
  active for correctness, or for speed bulk-insert then run
  `INSERT INTO block_fts(block_fts) VALUES('rebuild');`. The same `rebuild` command
  repairs any drift. `('integrity-check')` is available for verification.
- **GC interaction:** deleting a block fires `block_ad`, evicting its FTS row, so the
  index never holds orphans.

### 3.7 Idempotency / upsert keys (schema-level; full write path is §7)

| table             | upsert key                                  | semantics                          |
| ----------------- | ------------------------------------------- | ---------------------------------- |
| `block`           | `hash` (UNIQUE)                             | `INSERT … ON CONFLICT(hash) DO UPDATE SET n_tokens=COALESCE(excluded.n_tokens, block.n_tokens)`; identity/text columns never change; returns `id` |
| `session`         | `session_id` (PK; minted uuid or uuid5 synth) | upsert; PK enforces idempotency; partial unique index guards native id |
| `wire_exchange`   | `exchange_id` (PK)                          | upsert (re-ingest replaces row)    |
| `transcript_turn` | `turn_id` (PK)                              | upsert (re-tail replaces row)      |
| `exchange_block`  | `(exchange_id, pos)` (PK)                   | replace-on-reingest                |
| `turn_block`      | `(turn_id, pos)` (PK)                       | replace-on-reingest                |

Re-ingesting an exchange/turn deletes its edges and re-inserts them (edges are
`ON DELETE CASCADE` from their entity, so an entity replace is clean). Block **rows** are
only ever added (or have `n_tokens` back-filled on conflict via `COALESCE`); identity/text
columns are never mutated; orphans are reclaimed by GC, never by the write path.

**Forward hook (out of scope here):** a future `block_vec` table / sqlite-vec extension
would attach to `block.id` exactly like `block_fts`, requiring no change to the entity or
edge tables.

### 3.8 Verification (executable evidence)

The full §3 DDL was executed against SQLite 3.51.0 (`executescript`) and exercised. All
checks pass:

- Schema compiles; FTS5 is available and the virtual table + triggers create cleanly.
- `block_ai` populates `block_fts` on insert; `MATCH 'hello'` returns the row.
- `INSERT … ON CONFLICT(hash) DO UPDATE SET n_tokens=COALESCE(excluded.n_tokens,
  block.n_tokens)` dedups (row count unchanged on re-insert) and **back-fills `n_tokens`**
  from NULL on a later insert, without adding a row or touching identity/text columns.
- The `kind` `CHECK` rejects an out-of-enum value.
- With `foreign_keys = ON`, deleting a block still referenced by an edge raises
  `IntegrityError` (the GC safety in §3.5 holds).
- Deleting a `wire_exchange` cascades its `exchange_block` edges; the orphan-block sweep
  `DELETE FROM block WHERE id NOT IN (…edges…)` then removes the now-unreferenced block,
  and `block_ad` evicts its `block_fts` row (no orphans).
- **Session idempotency (the fixed key):** the `session_id` PK rejects a duplicate
  `session_id`; two **minted** rows with `native_session_id IS NULL` and distinct
  `session_id` both insert (no false block); the partial unique index `session_native`
  rejects two distinct `session_id`s sharing one non-null `(run_id, provider,
  native_session_id)` — closing SQLite's multiple-NULL `UNIQUE` hole.
- `INSERT INTO block_fts(block_fts) VALUES('rebuild')` succeeds.

All 11 assertions pass (`RESULT: ALL PASS`).

---

## 4. Provider adapter port + dataclasses

The adapter port is the **transcript-side twin of the wire-side `ir.py` adapters**. It
converts a CLI's native transcript records into the §2/§3 vocabulary so that both streams
land in the same tier-2 tables and, critically, **dedup against each other**.

### 4.1 Design decisions (load-bearing)

1. **ABC, not Protocol.** `api/CLAUDE.md` mandates ABC for runtime adapter dispatch
   (Protocol is reserved for shape-only contracts). A registry resolves a concrete adapter
   per `cli` and dispatches.
2. **Async/sync boundary** (the repo's IR convention). `bind()` and `locate()` perform I/O
   (mint a uuid, derive/discover a path, query a db) → **async**. `normalize()` is pure
   computation (one native record → one turn) → **sync**, exactly like wire-adapter parsing.
3. **`parts` reuse `ir.ContentBlock` verbatim.** `NormalizedTurn.parts: list[ContentBlock]`
   reuses the exact discriminated union from `ir.py`. **This is the cross-stream dedup
   enabler:** a transcript text/tool_use/tool_result/thinking/image is the *same* pydantic
   type the wire side already emits, so `identity_canonical` (§3.3) hashes identical content
   identically across both streams. Adapters import only `ir` (DAG: `index` sits after
   `storage`; imports `ir` + the canonicalization helpers — §12).
4. **Transcript turns emit only the 6 CONTENT kinds** (`text, tool_use, tool_result,
   thinking, image, unknown`). They **never** emit `system` (`SystemPart`) or `tool_def`
   (`ToolDef`) blocks — those are wire-request-only regions. `turn_block` rows therefore
   reference blocks whose `kind` is in that 6-subset; `system`/`tool_def` blocks arise only
   from `exchange_block` (the wire system/tools sections).
5. **Idempotent `turn_id`** (the `transcript_turn` PK, §3.7). Use the **native** record id
   where the provider gives a stable one (claude `uuid`, opencode message `id`, gemini
   live-session record `id`); otherwise **synthesize** `uuid5(SESSION_NS, f"{session_id}|{seq}")`
   over the deterministic record ordinal (codex `response_item`, gemini checkpoint elements).
   Re-ingest of the same source yields the same ordinal → same `turn_id` → upsert.

### 4.2 The port (`index/adapters/base.py`, NEW — Phase B)

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Annotated, Any, Literal  # Any: native records are provider-shaped JSON
from pydantic import BaseModel, ConfigDict, Field
from transport_matters.ir import ContentBlock

RawRecord = dict[str, Any]  # Any: one parsed native transcript record (jsonl line / db-row JSON)


class SessionBinding(BaseModel):
    """Result of bind(): the session_id and how it was derived. Maps 1:1 to the §3 `session` row."""
    model_config = ConfigDict(frozen=True)
    session_id: str             # universal correlation key (§2); session PK
    provider: str               # wire family: anthropic | codex | gemini | opencode
    cli: str                    # harness: claude | codex | gemini | opencode
    run_id: str
    cwd: str
    workspace_slug: str
    workspace_hash: str
    native_session_id: str | None   # provider native id; None until known for minted
    minted: bool                # True = we minted via --session-id (claude/gemini); False = read-back
    started_at: str             # ISO-8601


class FileTailSource(BaseModel):
    """Line-addressable transcript on disk (claude/codex/gemini). Live-tail = file-watch + line offset (§9)."""
    model_config = ConfigDict(frozen=True)
    kind: Literal["file_tail"] = "file_tail"
    path: str                   # absolute jsonl path → transcript_turn.source_path
    format: str                 # claude_jsonl | codex_rollout | gemini_session | gemini_checkpoint
    encoding: str = "utf-8"


class PullSource(BaseModel):
    """Non-line-addressable transcript pulled via API/export/db (opencode). Live-tail = poll (§9)."""
    model_config = ConfigDict(frozen=True)
    kind: Literal["pull"] = "pull"
    ref: str                    # session ref (opencode ses_ id) → transcript_turn.source_path stem
    mechanism: str              # opencode_export | opencode_db
    command: list[str] | None = None   # e.g. ["opencode","export","<ses_id>"]; None for direct db read


TranscriptSource = Annotated[FileTailSource | PullSource, Field(discriminator="kind")]


class RunContext(BaseModel):
    """Input to bind(): per-run facts the adapter needs."""
    model_config = ConfigDict(frozen=True)
    run_id: str
    cwd: str
    workspace_slug: str
    workspace_hash: str
    cli: str
    native_session_id: str | None = None  # read-back input: native id from proxied frames / db


class TurnContext(BaseModel):
    """Input to normalize(): the bound session + this record's position. Keeps normalize pure (no hidden counters)."""
    model_config = ConfigDict(frozen=True)
    binding: SessionBinding
    source_path: str
    source_line: int | None = None  # line offset for file_tail; None for pull
    seq: int                         # caller-assigned positional order within session
    parent_id: str | None = None     # previous emitted turn_id; used when the format has no native parent link
    model: str | None = None         # threaded model (e.g. codex turn_context.model) when not on the record
    pending_calls: dict[str, str] | None = None  # iterator-maintained (name|ordinal → minted call id); cross-record tool pairing (gemini, §5.3)


class NormalizedTurn(BaseModel):
    """One harness turn. → a §3 `transcript_turn` row; `parts` → `turn_block` edges + `block` rows."""
    model_config = ConfigDict(frozen=True)
    turn_id: str                # PK: native id, or uuid5(SESSION_NS, f"{session_id}|{seq}")
    session_id: str             # NOT NULL (a turn only exists under a bound session)
    run_id: str
    provider: str
    cli: str
    parent_id: str | None       # DAG parent (claude parentUuid); None at root
    role: str                   # user | assistant | system | tool
    seq: int
    ts: str | None              # per-turn ISO-8601 where available
    is_sidechain: bool          # subagent marker
    model: str | None
    source_path: str            # tier-1 transcript source
    source_line: int | None     # line offset where line-addressable
    parts: list[ContentBlock]   # ir.py union; each part → one block (identity_canonical) + one turn_block edge


class TranscriptAdapter(ABC):
    """Transcript-side anti-corruption layer. One concrete subclass per CLI (§5). Registered by `cli`."""
    provider: str   # class attribute
    cli: str        # class attribute

    @abstractmethod
    async def bind(self, run: RunContext) -> SessionBinding:
        """Establish session_id. MINT: uuid4(), inject via --session-id, minted=True.
        READ-BACK: session_id = uuid5(SESSION_NS, f"{run_id}|{provider}|{native_session_id}"), minted=False."""

    @abstractmethod
    async def locate(self, binding: SessionBinding) -> TranscriptSource:
        """Resolve where the transcript lives. Minted providers derive a deterministic path/glob
        (known before the CLI writes a byte); read-back providers discover it (glob by native id / db ref)."""

    @abstractmethod
    def normalize(self, record: RawRecord, ctx: TurnContext) -> NormalizedTurn | None:
        """Pure: map ONE native record to a turn. Return None to skip non-conversational records.
        Prefer native fields (id, parentUuid, role, ts); fall back to ctx (seq, parent_id, model, source_line)."""
```

**Iteration seam (out of scope here).** The loop that opens a `TranscriptSource`, reads raw
records, assigns `seq`, threads `parent_id`/`model`, and calls `normalize` per record is the
**write-path / live-tail** concern (§7/§9, Phases C/D). §4 fixes only the port + dataclasses;
the read/iterate method is named, not specified.

### 4.3 `NormalizedTurn` → §3 mapping (explicit)

| `NormalizedTurn` field | §3 destination |
| --- | --- |
| `turn_id` | `transcript_turn.turn_id` (PK) |
| `session_id`, `run_id`, `provider`, `cli`, `parent_id`, `role`, `seq`, `ts`, `is_sidechain`, `model`, `source_path`, `source_line` | identically-named `transcript_turn` columns |
| `parts[i]` | `upsert_block(part)` → `block.id`, then `turn_block(turn_id, pos=i, block_id, role)` |

`turn_block.role` = the **turn's** role for every part (a transcript turn carries one role,
unlike a wire exchange whose parts span system/tools/messages/response sections). `block.kind`
is derived from the part type by `block_kind(part)` (§3.3, §12).

## 5. Concrete adapters (claude / codex / gemini / opencode)

Grounded in real samples **inspected first-hand on 2026-05-31** (paths cited per adapter).
Each adapter declares `provider`/`cli` and implements `bind`/`locate`/`normalize`, mapping
native parts to `ir.ContentBlock`. Transport-opaque carriers (claude `thinking.signature`,
codex `encrypted_content`, gemini `thoughtSignature`, any provider-only field) attach to the
block's `provider_data` and are therefore **stripped from identity** by §3.3 — they survive
byte-exact only in tier-1. A rule shared by all four: **`normalize` returns `None`** for any
record that is not a conversation turn.

### 5.1 claude — MINT

*Sample: `~/.claude/projects/-Users-alphab-Dev-LLM-DEV-helioy-littleorgans-littleorgans/0c721f8e-…​.jsonl` (290 lines, verified).* `provider=anthropic`, `cli=claude`.

- **bind** — MINT. `session_id = str(uuid4())`, injected via `claude --session-id <uuid>`;
  `minted=True`, `native_session_id=None`. We own the uuid, so the path is known before the
  CLI writes a byte.
- **locate** — deterministic, no discovery.
  `FileTailSource(path=f"{HOME}/.claude/projects/{cwd_slug}/{session_id}.jsonl",
  format="claude_jsonl")`, where `cwd_slug` = absolute cwd with `/`→`-` (the slug seen on
  disk). The filename stem **==** the minted `session_id` (verified: filename `0c721f8e-…`
  == the in-file `sessionId`).
- **normalize** — one jsonl line. Uniform envelope:
  `{type, uuid, parentUuid, sessionId, isSidechain, userType, cwd, version, gitBranch, timestamp, message?}`.
  - **Skip** every `type` ∉ {`user`, `assistant`}. Observed non-conversational types in the
    real file: `ai-title, attachment, file-history-snapshot, last-prompt, mode,
    permission-mode, queue-operation, system`. `system` records are harness/hook metadata
    (subtypes `stop_hook_summary`, `turn_duration`; `content` usually null) — skipped in
    Phase B (a later phase may surface content-bearing hook output as a `system`-role turn;
    flagged, not designed here).
  - turn fields: `turn_id=uuid`, `parent_id=parentUuid` (None at root), `role=message.role`,
    `is_sidechain=isSidechain`, `ts=timestamp`, `model=message.model` (assistant only),
    `source_line=ctx.source_line`, `seq=ctx.seq`.
  - parts from `message.content`: `str` → `[TextBlock(text=content)]`; `list` → map each
    element by `.type`:

    | claude block | → ir part |
    | --- | --- |
    | `text` | `TextBlock(text)` |
    | `thinking` | `ThinkingBlock(text=thinking)`; `signature` → `provider_data` (stripped) |
    | `tool_use` | `ToolUseBlock(id, name, input)` |
    | `tool_result` | `ToolResultBlock(tool_use_id, content=<str→[TextBlock]; list→map text/image/unknown>, is_error=bool(is_error))` |
    | `image` | `ImageBlock(source)` |
    | other | `UnknownBlock(raw=block)` |

- **Bonus wire-pivot hooks (not in identity).** Assistant records carry `requestId`
  (`req_011C…`) and `message.id` (`msg_014…`). §8 can sharpen the wire↔transcript pivot with
  these beyond `session_id`: `requestId` ↔ the proxied request, `message.id` ↔
  `InternalResponse.id`. The indexer MAY persist them as turn provenance (a future
  `transcript_turn` column); they are never part of block identity.

### 5.2 codex — READ-BACK

*Sample: `~/.codex/sessions/2026/03/13/rollout-2026-03-13T19-27-44-019ce72a-…​.jsonl` (182 lines, verified); index `~/.codex/session_index.jsonl`.* `provider=codex`, `cli=codex`.

- **bind** — READ-BACK. Native thread uuid = `session_meta.payload.id` (also the rollout
  filename uuid; carried in the proxied codex websocket frames — how the wire side learns it).
  `native_session_id=<thread uuid>`;
  `session_id = uuid5(SESSION_NS, f"{run_id}|codex|{native_session_id}")`; `minted=False`.
  `session_meta.payload.forked_from_id` records resume/fork lineage — a forked thread is a
  distinct `session_id` under the same `run_id` (multiple sessions per run, §2).
- **locate** — discovery by glob. Rollout path is date-partitioned
  `~/.codex/sessions/YYYY/MM/DD/rollout-<ISO-start>-<thread_uuid>.jsonl`; the start timestamp
  is not independently known, so locate globs
  `~/.codex/sessions/**/rollout-*-{native_session_id}.jsonl` (the uuid suffix is unique).
  `session_index.jsonl` (`{id, thread_name, updated_at}`) enumerates threads for
  listing/freshness but stores no path. `FileTailSource(path=<resolved>, format="codex_rollout")`.
- **normalize** — one rollout line `{timestamp, type, payload}`.
  - **Process only** `type == "response_item"` (the durable conversation items). **Skip**
    `session_meta`, `turn_context`, and all `event_msg` — the last are streaming UI events
    (`agent_message, agent_reasoning, token_count, task_started/complete`), duplicative of the
    response_items and not the durable record. `turn_context.model` is threaded forward via
    `ctx.model`.
  - `response_item.payload.type` → role + parts:

    | codex `payload.type` | turn role | → ir part(s) |
    | --- | --- | --- |
    | `message` (`role∈{user,assistant,developer,system}`, `content:[{type:input_text\|output_text, text}]`) | `developer`→`system`, else `role` | each content elem → `TextBlock(text)` |
    | `function_call` (`call_id, name, arguments`) | `assistant` | `ToolUseBlock(id=call_id, name, input=json.loads(arguments))` — `arguments` is a JSON **string** |
    | `function_call_output` (`call_id, output`) | `tool` | `ToolResultBlock(tool_use_id=call_id, content=[TextBlock(text=<output as str>)], is_error=<from output if structured else False>)` |
    | `reasoning` (`summary, content, encrypted_content`) | `assistant` | `ThinkingBlock(text=<joined summary[].text or content>)`; `encrypted_content` → `provider_data` (stripped) |

  - ids: response_item has no per-record id → `turn_id = uuid5(SESSION_NS, f"{session_id}|{seq}")`;
    `parent_id=ctx.parent_id` (linear prev-turn chain); `ts=<line>.timestamp`;
    `model=ctx.model`. Turn granularity = **one turn per `response_item`** (the write path
    MAY coalesce consecutive assistant items of one step — §7); normalize maps one record.
  - `is_sidechain`: a codex subagent is a **separate forked thread/session**
    (`session_meta.source.subagent`), so within a session `is_sidechain=False` (subagent-ness
    is session-grained, like opencode; unlike claude's per-record flag).

### 5.3 gemini — MINT (two on-disk formats)

*Samples (verified first-hand): text-only live session
`~/.gemini/tmp/transport-matters/chats/session-2026-05-16T11-38-62bd3e45.jsonl`; tool-using live
session `~/.gemini/tmp/littleorgans/chats/session-2026-05-23T08-20-62ead288.jsonl` (40+ toolCalls);
`/chat save` checkpoint `…/checkpoint-refactor.json`.* `provider=gemini`, `cli=gemini`.
`gemini --session-id <uuid>` is confirmed; the live-session file is uuid-keyed and enumerated
by `--list-sessions`.

> **Two distinct formats (peer-flagged; both inspected).**
>
> **Format A — `chats/session-<ISO>-<uuid8>.jsonl` (the live/durable session;
> `--session-id`/`--resume`/`--list-sessions` store).** An **append-only event log**, *not* a
> `Content[]` array:
> - **line 1 = header**: `{sessionId, projectHash, startTime, lastUpdated, kind}`. `sessionId`
>   = the session uuid (matches `--list-sessions`; the filename `<uuid8>` = its first 8 chars).
> - **record lines** `{id, timestamp, type, content, …}`, each with a **native `id` (uuid)** →
>   `turn_id` (no synth). `type` ∈ {`user`, `gemini`, `info`}:
>   - `user`: `content` is a **list of parts** (+ a `displayContent` render to ignore).
>   - `gemini`: `content` is a **string** (final text; `""` when the turn is tool-only), plus
>     `thoughts:[{subject, description}]`, `tokens`, `model`, and — when tools ran — a
>     **top-level `toolCalls:[…]`** array (a sibling of `content`, NOT inside it; see normalize).
>   - `info`: harness/system info (line 2 of the sample) — **skip** in Phase B (like claude `system`).
> - **`$set` lines**: `{"$set":{…}}` — append-log mutations to the header. **Skip.**
>
> **Format B — `checkpoint-<tag>.json` (`/chat save` snapshot).** A `Content[]` array of
> `{role:user|model, parts:[…]}`; elements have **no id** (synthesize). Tools appear as
> `functionCall`/`functionResponse` **parts** (not a `toolCalls` array). Secondary; the
> live-tail (§9) follows Format A.

- **bind** — MINT. `session_id = str(uuid4())` via `gemini --session-id <uuid>`; `minted=True`.
- **locate** — `projectKey` = the name in `~/.gemini/projects.json` for the cwd if present,
  else `sha256(cwd)` hex (both forms observed as tmp subdir names; the dir's `.project_root`
  marker disambiguates). Glob
  `~/.gemini/tmp/{projectKey}/chats/session-*-{session_id[:8]}.jsonl`; `--list-sessions` is the
  robust enumerator. `FileTailSource(path=<resolved>, format="gemini_session")`.
  **FLAG:** the filename's minute-stamp is not independently derivable → glob by `<uuid8>`.
- **normalize** — the two formats normalize **differently**; the cross-record bridge is
  **Format B only**.
  - **Format A (live session).** Skip line 1 (feeds `bind`), every `$set` line, and `type:info`
    records (Phase B). For a `user`/`gemini` record: `turn_id=id`, `role` = `user`→user /
    `gemini`→assistant, `ts=timestamp`, `model=model` (gemini), `parent_id=ctx.parent_id`
    (linear; no native parent link). Parts, in order:
    - `thoughts:[{subject, description}]` (gemini) → one `ThinkingBlock(text=f"{subject}\n{description}")` each (prepended).
    - `content:str` → `[TextBlock(text)]` (omit when `""`); `content:list` (user) → map each part via the **content-part table** below (text/inlineData in practice).
    - `toolCalls:[{id, name, args, result, status}]` (gemini) — **intra-record, native id, NO `pending_calls`** (call and result share `toolCall.id` in one record; verified across 40+ toolCalls). Each item →
      `ToolUseBlock(id=toolCall.id, name=toolCall.name, input=toolCall.args)` **+**
      `ToolResultBlock(tool_use_id=toolCall.id, content=[TextBlock(text=json(result[].functionResponse.response))], is_error=(status != "success"))`.
  - **Format B (checkpoint `Content[]`).** Each array element = a turn; `role` = `user`→user /
    `model`→assistant; `turn_id=uuid5(SESSION_NS, f"{session_id}|{seq}")` (no native id); parts via
    the content-part table. Here tools are **cross-record**: `functionCall` in a `model` element,
    the matching `functionResponse` in the **following `user`** element (confirmed across 90+
    pairs; a `user` turn may be tool-result-only, like a claude tool_result in a user message).
    `functionCall` has no id and pure `normalize` has no lookahead, so pairing is a
    **write-path/iterator** job (§7): the iterator mints `ToolUseBlock.id = f"{call_turn_id}:{i}"`
    at the call site, records `(name, ordinal) → id` in `TurnContext.pending_calls`, and the
    following user turn's `normalize` reads `ctx.pending_calls` to set each
    `ToolResultBlock.tool_use_id`. (`functionResponse.id` MAY serve as the key instead.) `normalize`
    stays pure — it only reads the registry the iterator threads through `ctx`.

  **Content-part table** — Format B `parts[]`, and Format A `user` `content:list`
  (`functionCall`/`functionResponse` parts occur in **Format B only**; Format A tools use the
  `toolCalls` array above):

    | Gemini part key | → ir part |
    | --- | --- |
    | `text` | `TextBlock(text)` |
    | `functionCall` (`{name, args}`) — *Format B only* | `ToolUseBlock(id=<iterator-minted; see Format B>, name, input=args)` |
    | `functionResponse` (`{id, name, response}`) — *Format B only* | `ToolResultBlock(tool_use_id=<via ctx.pending_calls>, content=[TextBlock(text=json(response))], is_error=<from response>)` |
    | `thought` / `thoughtSignature` | `ThinkingBlock(text)`; `thoughtSignature` → `provider_data` (stripped) |
    | `inlineData` (`{mimeType, data}`) | `ImageBlock(source={mimeType, data})` |

### 5.4 opencode — READ-BACK (api/export/db)

*Source: `~/.local/share/opencode/opencode.db` (Drizzle schema inspected first-hand);
`opencode export <id>` JSON.* `provider=opencode`, `cli=opencode`.

- **bind** — READ-BACK. `native_session_id=<ses_… id>` (from `opencode session list` / export
  / the `session` table). `session_id = uuid5(SESSION_NS, f"{run_id}|opencode|{native_session_id}")`;
  `minted=False`.
- **locate** — `PullSource(ref=ses_id, mechanism="opencode_export",
  command=["opencode","export",ses_id])`. Not line-addressable →
  `transcript_turn.source_path = f"opencode_export:{ses_id}"`, `source_line=None`. A direct-db
  variant (`mechanism="opencode_db"`, reading `session/message/part`) yields identical output.
- **shape — two mechanisms, both verified first-hand:**
  - **export** (`opencode export <id>`): stdout begins with a human line `Exporting session:
    <id>` that **must be stripped** before the JSON. JSON =
    `{info:<session>, messages:[{info:{id, role, time:{created}, model:{providerID, modelID},
    agent, summary, sessionID}, parts:[{type, …type fields…, id, messageID, sessionID}]}]}`. The
    message header is under **`message.info`** (not spread); part fields are **top-level** in each
    part; `model` is an **object** `{providerID, modelID}`, not a string.
  - **db** (`session/message/part` tables): the same fields live in JSON blobs —
    `message.data ⊇ {role, agent, model, summary, time}` (`id` is the row column);
    `part.data = {type, …}` (`id`/`message_id`/`session_id` are columns). `part.data.type` ∈
    {`text, reasoning, tool, step-start, step-finish, patch, file`}.
  - A per-mechanism **reshape** yields one canonical record
    `{turn_id, role, model, ts, parts:[{type, …}]}` that `normalize` consumes — export:
    `info.id / info.role / info.model.modelID / info.time.created / parts`; db:
    `message.id / json(data).role / json(data).model.modelID / json(data).time.created /
    [json(p.data) for parts]`.
- **normalize** — one (reshaped) message → one turn; its parts → blocks.
  - turn (from the canonical record): `turn_id=<id>` (native message id; no synth),
    `role=<role>` (user|assistant), `model=<model.modelID>` (the object's `modelID`),
    `ts=<ISO(time.created)>`, `parent_id=ctx.parent_id` (linear), `seq=ctx.seq`.
  - parts by `part.type` (canonical, already un-nested):

    | opencode `part.type` | → ir part(s) |
    | --- | --- |
    | `text` (`{text}`) | `TextBlock(text)` |
    | `reasoning` | `ThinkingBlock(text)` |
    | `tool` (`{callID, tool, state:{input, output, status}}`) | **split** → `ToolUseBlock(id=callID, name=tool, input=state.input)` + (when `state.status`∈{`completed`,`error`}) `ToolResultBlock(tool_use_id=callID, content=[TextBlock(text=<state.output>)], is_error=(state.status=="error"))` |
    | `file` | `ImageBlock(source=<file ref>)` (attachment) |
    | `patch` | `UnknownBlock(raw=part)` (opencode-specific synthetic diff part) |
    | `step-start` / `step-finish` | **skip** (control parts) |

  - **is_sidechain / subagents:** opencode models a subagent as a **child session**
    (`session.parent_id` set), not a per-turn flag. Within a session `is_sidechain=False`; the
    parent/child relation is session-grained (the indexer MAY project a child session's turns
    with `is_sidechain=1` against the parent — a write-path policy, §7). Same shape as codex;
    differs from claude's per-record `isSidechain`.
  - **FLAG (wire correlation):** opencode is the **weakest wire↔transcript seam** — unlike
    codex (thread uuid in the proxied frames) and claude/gemini (minted uuid), the `ses_` id is
    not guaranteed to surface in proxied request metadata. Correlation falls back to `run_id` +
    exact block-hash intersection (§2 pivot sharpening) + timestamp proximity until/unless the
    proxy can capture the `ses_` id from an opencode request header.

### 5.5 Cross-adapter summary

| cli | provider | bind | session_id | transcript source | native turn id? |
| --- | --- | --- | --- | --- | --- |
| claude | anthropic | MINT uuid | minted uuid | `~/.claude/projects/<slug>/<uuid>.jsonl` (FileTail) | yes (`uuid`) |
| codex | codex | READ-BACK | `uuid5(NS, run\|codex\|thread)` | `~/.codex/sessions/**/rollout-*-<thread>.jsonl` (FileTail) | no → synth |
| gemini | gemini | MINT uuid | minted uuid | `~/.gemini/tmp/<projectKey>/chats/session-*-<uuid8>.jsonl` (FileTail) | A: yes (`id`); B: synth |
| opencode | opencode | READ-BACK | `uuid5(NS, run\|opencode\|ses_)` | `opencode export <ses_>` / db (Pull) | yes (message `id`) |

All four converge on `NormalizedTurn` whose `parts` are `ir.ContentBlock`s, so identical
content across any stream/CLI dedups to one `block` and sharpens the §2 pivot.

### 5.6 File placement (extends the §12 `index/` package, additive)

New, all ≤ 700 LOC, within the Phase-A `index/` package (no change to approved §12 text):

```
api/src/transport_matters/index/adapters/
├── __init__.py          # registry: cli → TranscriptAdapter; get_adapter(cli)
├── base.py              # §4 port: TranscriptAdapter(ABC) + SessionBinding/TranscriptSource/
│                        #   RunContext/TurnContext/NormalizedTurn  (~190 LOC)
├── claude.py            # §5.1  (~150 LOC)
├── codex.py             # §5.2  (~170 LOC)
├── gemini.py            # §5.3  (two formats)  (~200 LOC)
└── opencode.py          # §5.4  (~170 LOC)
```

## 6. Single machine-level indexer (process model)

This section decides **who owns tier-2 writes** and how the §3.1 single-writer-via-WAL
discipline is realized under the **multi-instance** reality (commit `a8dd8ed`). It picks
one process model and justifies it against the live proxy architecture.

### 6.1 The process reality (grounded, not assumed)

The capture process is a **mitmproxy addon**, and there is **one addon process per run**,
not one machine-global server:

- `TransportMattersAddon` loads once per launch (`addon.py:56-97`) and spawns an async
  FastAPI/uvicorn server in-process via `load_runtime()` (`addon_runtime.py:27-53`).
- Each launch mints a fresh `run_id` and writes tier-1 under
  `workspaces/{slug}/{hash}/{run_id}/` (`workspace.py:85-94`). Two launches in the **same
  cwd** never collide because each owns a distinct `{run_id}/` subtree (multi-instance).
- Request/response handling is **async** (`addon.py:63-86`); persistence is async
  (`storage/base.py:275-342`); pure computation (parse, override, hashing) is sync.
- There is **no** background worker, queue, or machine-global daemon today. Everything
  runs in the request path, and post-persist fan-out to the UI already happens inline via
  `emit_exchange()` → `broadcast.emit()` (`exchange_recorder.py:219-260`, `broadcast.py`).

**Consequence:** tier-2 (`~/.transport-matters/index.db`) is a **single machine-level
file written by N concurrent proxy processes** (one per live run). The roadmap's "single
machine-level indexer" therefore cannot mean a single OS process unless we introduce a
daemon. It means a **single logical writer per database**, which SQLite already provides
through its file-level write lock.

### 6.2 Decision: in-proxy writer thread, serialized across processes by WAL + busy_timeout

> **PICK (one of three).** The tier-2 writer is an **in-proxy single writer thread**, one
> per proxy process. Cross-process concurrency (N proxies → one `index.db`) is serialized
> by **WAL + `busy_timeout`** (the "direct-writes-under-`busy_timeout`" mechanism, applied
> at the file level per §3.1). A **separate daemon is rejected.**

Why this and not the other two:

- **Separate daemon — rejected.** A machine-global indexer daemon would add an
  unsupervised long-lived process to a single-user box, an IPC/socket surface, a startup
  ordering problem (proxy up before daemon = lost writes), and a new single point of
  failure (daemon down = no indexing for every run). It buys nothing here: tier-2 is a
  **rebuildable projection** of tier-1 (§3, §10/§11), so durability does not depend on the
  indexer. Over-engineering for the stated single-user, no-backcompat constraints.
- **Naive direct writes in the request handler — rejected as the owner.** Writing tier-2
  synchronously inside the async response handler would put SQLite commit latency (and
  cross-process `busy_timeout` waits) on the **wire hot path**, threatening the API p95
  budget, and would let multiple async handlers in one process race on one connection.
  WAL + `busy_timeout` is retained as the **cross-process** serializer, but it is not the
  **intra-process** owner.
- **In-proxy writer thread — chosen.** Each process runs exactly **one** writer thread
  that owns the single write connection. Async producers (the post-persist seam, the
  transcript tailer of §9) hand jobs to a thread-safe queue and return immediately. This
  gives, with the least machinery: a true single writer per process (no intra-process lock
  contention), batched transactions (WAL health), and tier-2 latency fully **off** the
  wire path. Across processes, the per-process writers contend only at SQLite's write lock,
  where `busy_timeout = 5000` makes them wait rather than fail.

This satisfies the §3.1 promise verbatim: "the single machine-level indexer invariant is
realized by SQLite's own write lock; the process model that owns writes is decided in
Phase C (§6)."

### 6.3 The writer actor (`index/writer.py`, NEW)

One dedicated OS thread per process, owning one write `Connection` (sqlite3 connections
are thread-affine, so the connection lives on this thread and nowhere else):

```python
@dataclass(frozen=True)
class IndexJob:
    """A unit of tier-2 work. Built by index/ingest.py (§7); never holds raw bytes."""
    kind: Literal["wire", "transcript"]
    payload: WireExchangeIngest | TranscriptTurnIngest   # frozen row-bundles (§7); each
                                                         #   embeds a SessionBinding (§4.2)
                                                         #   for the FK-parent session upsert

class IndexWriter:
    """Single-writer-per-process actor. Drains a bounded queue into batched transactions."""
    def __init__(self, db_path: str, batch_max: int = 64, flush_ms: int = 50) -> None: ...
    def start(self) -> None:        # spawn the writer thread; called from load_runtime()
    def submit(self, job: IndexJob) -> None:   # thread-safe, non-blocking (queue.put_nowait)
    def stop(self, drain: bool = True) -> None: # graceful: flush queue, checkpoint, close
```

- **Queue.** A bounded `queue.Queue[IndexJob]` (thread-safe; producers call
  `put_nowait`). Bound is a fixed capacity (e.g. 10_000 jobs).
- **Batching.** The thread drains up to `batch_max` jobs (or waits `flush_ms` for the
  first), opens **one** `BEGIN IMMEDIATE` transaction, applies each job inside its own
  `SAVEPOINT` (see Failure isolation), and commits once. `BEGIN IMMEDIATE` acquires the
  write lock up front so the cross-process wait is paid by `busy_timeout` at `BEGIN`, never
  as a mid-transaction `SQLITE_BUSY` on lock upgrade. Batching bounds WAL growth
  (`wal_autocheckpoint = 1000`, §3.1) and amortizes fsync.
- **Lifecycle.** `start()` is called from `load_runtime()` (`addon_runtime.py:27-53`),
  alongside the FastAPI server; `stop(drain=True)` is registered on the addon's
  shutdown/`done` hook so a clean exit flushes pending jobs and runs a final
  `wal_checkpoint(TRUNCATE)`. The write connection applies the §3.1 PRAGMAs and the §3.2
  schema-version check (drop+rebuild on mismatch) on first open.
- **Backpressure (never block the wire path).** If the queue is full, the producer does
  **not** block: it drops the job and marks the run **dirty** (a per-run flag/counter,
  surfaced in logs and metrics). Because tier-2 is rebuildable, a dropped job is repaired
  by the §10/§11 reconcile/backfill replaying that run's tier-1. Silent loss is forbidden:
  every drop is logged with `run_id` and a counter (per the "no silent caps" rule).
- **Failure isolation (per-job atomicity inside the batch).** Each job is wrapped in a
  nested transaction: `SAVEPOINT j` → apply the job's session/entity/edge statements →
  `RELEASE j` on success. If any statement raises, the writer issues `ROLLBACK TO j`
  **followed by** `RELEASE j` (the rollback alone leaves the savepoint on the stack),
  logs the failure with the entity id, and continues the batch. This guarantees a failed
  job leaves **no** partial rows: a bare `try/except` around the statements would still
  commit a job's earlier writes at the batch `COMMIT` (e.g. a `session` upsert that landed
  before the entity insert threw). Surviving jobs commit at the single `COMMIT`; tier-1
  remains the source of truth, so a rolled-back job is recovered by the §10/§11 rebuild.
  The wire path never observes a tier-2 error.

### 6.4 DAG-safe wiring (no `recorder → index` import cycle)

The import DAG (`ir → adapters → rules → pipeline → storage → breakpoint → server`, §1.4)
places `index` **after** `storage`, so `index` may import `storage` types but **`storage`
must never import `index`** (that back-edge is a cycle and is forbidden by CLAUDE.md). The
write seam, however, lives in `exchange_recorder.py`, which is in the storage layer. The
indexer is therefore wired by **dependency inversion**, not a static import:

- The recorder already emits a post-persist event to a sink it does not own
  (`emit_exchange()` → `broadcast.emit()`, `exchange_recorder.py:219-260`). We add a second
  **injected sink**: an `Optional[Callable[[IndexEntry, ExchangeArtifacts], None]]` (or a
  tiny `ExchangeSink` Protocol declared **in the storage layer**) that the recorder invokes
  at the same point (after `storage.persist_exchange()` returns,
  `exchange_recorder.py:~520`).
- At `load_runtime()`, the **index layer** constructs the `IndexWriter`, captures the
  per-run static `SessionBinding` facts (§7.2) in the closure, and registers
  `lambda entry, artifacts: writer.submit(build_wire_job(entry, artifacts, bind_exchange(entry, artifacts, run_facts)))`
  as that sink, where `bind_exchange(entry, artifacts, run_facts)` resolves this exchange's
  `SessionBinding | None` from the closure's per-run facts plus the per-exchange correlation
  id on `artifacts.request_ir.metadata` (`RequestMetadata`, `ir.py:124-132`); `IndexEntry`
  itself carries no request metadata. `build_wire_job` and `bind_exchange` live in
  `index/ingest.py` (which is allowed to import `storage`).
- Net edges: `index → storage` (types, in `ingest.py`) and a **runtime** `storage → sink`
  call through a callable the storage layer already understands. No `storage → index`
  import exists. The index **core** (`schema.py`, `blocks.py`, `models.py`) keeps its
  Phase-A purity (imports `ir` + `canonicalization` only); only `ingest.py`/`writer.py`
  touch storage and db.

The same injection feeds the transcript path: the §9 live-tail loop (Phase D) calls
`writer.submit(build_transcript_job(turn, ctx.binding))` for each `NormalizedTurn` a §5
adapter emits (the `SessionBinding` comes from `TurnContext.binding`, §7.3).

### 6.5 Idempotency and ordering (recap; full keys in §3.7, full path in §7)

- All writes are **upserts** keyed per §3.7: `block` by `hash`, `session` by `session_id`,
  `wire_exchange` by `exchange_id`, `transcript_turn` by `turn_id`, edges by their
  composite PK. Re-ingest of the same entity is therefore a no-op-or-replace, safe to run
  any number of times (live capture, re-tail, full rebuild).
- **Write ordering inside a job** respects foreign keys: upsert `session` (parent) →
  upsert the entity (`wire_exchange`/`transcript_turn`) → delete its existing edges →
  re-insert edges (each `upsert_block` first to obtain `block.id`). With
  `foreign_keys = ON`, this never dangles.
- **`seq` is defined canonically as ts-rank within a session.** The incremental writer
  assigns `seq = SELECT COALESCE(MAX(seq), -1) + 1 FROM wire_exchange WHERE session_id = ?`
  at first insert and **preserves** it on re-ingest; a full rebuild (§10/§11) recomputes it
  as `ORDER BY ts`. Live exchanges arrive in ts order under the single per-process writer,
  so the incremental and rebuilt orders agree. `transcript_turn.seq` is supplied by the
  iterator (`TurnContext.seq`, §4) from the deterministic source ordinal, so it is already
  stable across re-tail.

## 7. Write path

Two producers feed the §6 writer: the **wire** path (proxy capture) and the **transcript**
path (a §5 adapter, driven by the §9 tailer). Both follow one invariant and reuse the §3.7
upsert keys. §7 specifies the per-entity work; the iteration loop that drives the
transcript adapter is §9.

### 7.1 Invariant: tier-1 first (durable), tier-2 second (best-effort, off the hot path)

tier-1 is the source of truth; tier-2 is a rebuildable projection (§3, locked). Therefore:

1. The existing tier-1 persist runs **unchanged and first** (`storage.persist_exchange()`,
   `exchange_recorder.py:72-83`; raw bytes via `ExchangeArtifactPaths`,
   `disk_layout.py:32-44`). Its success is the durability guarantee.
2. **Only after** tier-1 success does the recorder hand the entity to the injected tier-2
   sink (§6.4), which enqueues a job. The wire path never blocks on, and never fails
   because of, tier-2.

If the process dies between (1) and the tier-2 commit, the exchange/turn is on tier-1 but
not yet in tier-2; the §10/§11 first-boot reconcile replays that run dir and the §3.7
upserts make the replay idempotent. This is the single property that makes the async,
batched, best-effort writer (§6.3) safe.

### 7.2 Wire write path (one `wire_exchange` per captured exchange)

**Trigger.** The post-persist sink fires with `(entry: IndexEntry, artifacts:
ExchangeArtifacts)` (`exchange_recorder.py:~520`). The sink resolves this exchange's
`SessionBinding | None` via `bind_exchange(entry, artifacts, run_facts)` (§6.4) and calls
`build_wire_job(entry, artifacts, binding)` (`index/ingest.py`), which maps them to a frozen
`WireExchangeIngest`; the §6 writer applies it in a batch.

**Field mapping (no recomputation of values tier-1 already computed).**

| tier-2 column (`wire_exchange`) | source | note |
| --- | --- | --- |
| `exchange_id` (PK) | `IndexEntry.id` | the existing exchange id |
| `ts`, `model`, `provider`, `run_id` | `IndexEntry` | |
| `stop_reason` | `ResStats.stop_reason` (`storage/base.py:65-74`) | |
| `mutated_manually` | `IndexEntry.mutated_manually` | |
| `req_system_chars` / `req_tools_chars` / `req_messages_chars` | `ReqStats.system_chars` / `tools_chars` / `messages_chars` (`storage/base.py:39-48`) | **reused, not recomputed** — `ReqStats` already IS the production char accounting (`count_chars_parts`), so §3.3's "computed at index time" is satisfied by reading the value the wire path already produced (DRY). |
| `req_tokens` / `res_tokens` | `ResStats.input_tokens` / `output_tokens` | cache token detail (`cache_creation_input_tokens`, `cache_read_input_tokens`) stays in tier-1 / `ResStats`; the §3.4 schema is locked and not extended here. |
| `raw_dir` | the tier-1 exchange dir (from the artifact paths) | **pointer only**; raw bytes are fetched from tier-1 on demand (§8.5), never copied into tier-2. |
| `session_id` (nullable) | `binding.session_id` when `bind_exchange(entry, artifacts, run_facts)` returns a binding, else `NULL` | the minted uuid (claude/gemini) or `synth_session_id(run_id, provider, native_session_id)` for read-back (codex, §3.4). `artifacts.request_ir.metadata` (`ir.py:124-132`) is only the correlation/native-id **input** to `bind_exchange`, never written to this column verbatim. FK `ON DELETE SET NULL`; `NULL` while uncorrelated. |

**Session row (FK parent) and its data source.** The `session` row (PK `session_id`, §3.4)
needs `cli / cwd / workspace_slug / workspace_hash / native_session_id / minted /
started_at`, none of which are on `IndexEntry` or `RequestMetadata` (`ir.py:124-132` carries
only `session_id` and opaque `provider_metadata`). The wire path therefore reuses the
**same `SessionBinding`** the transcript port already defines (§4.2, "maps 1:1 to the §3
`session` row") rather than inventing a parallel facts struct (DRY). It is assembled in two
parts:

- **Per-run static facts**, captured once when the sink is registered in `load_runtime()`
  (§6.4): `run_id`, `cwd`, `workspace_slug` / `workspace_hash` (from `WorkspaceId`,
  `workspace.py`), the launched `cli`, `started_at`, and for minted providers the
  launch-minted `session_id` with `minted=True`. These live in the sink **closure** (the
  addon has the run manifest and `WorkspaceId` in scope at `addon_runtime.py:27-53`), so
  `build_wire_job` reaches them with no `storage → index` import.
- **Per-exchange facts**: `provider` / `model` from `IndexEntry`, and the correlation id
  read from `artifacts.request_ir.metadata` (`RequestMetadata`, `ir.py:124-132`) — note
  `IndexEntry` itself carries no request metadata. For minted providers (claude/gemini) the
  closure's minted uuid is authoritative. For read-back providers (codex) the native thread
  id resolved into `RequestMetadata` (upstream at `codex/session_metadata.py:38-50`) feeds
  `session_id = synth_session_id(run_id, provider, native_session_id)`, `minted=False`.

`synth_session_id` (uuid5 over the frozen `SESSION_NS`, §3.4) is the **one shared helper**
used by **both** this wire correlation and the read-back transcript adapters (§5.2/§5.4),
which is what makes the two streams provably converge on the **same** `session_id` (the §2
pivot depends on this identity). When no `session_id` can be determined for an exchange,
**no** session row is written and `wire_exchange.session_id` stays `NULL` (`ON DELETE SET
NULL`); a later correlation upsert backfills it. The job carries an optional
`SessionBinding` (None when uncorrelated); `build_wire_job` is therefore
`build_wire_job(entry, artifacts, binding | None)`.

**Ordered `exchange_block` edges (role/section live on the edge, §3.5).** Flatten
`request_ir` and `response_ir` (`ir.py:138-176`) into one ordered part stream and assign a
single running `pos` (so `(exchange_id, pos)` is unique):

| order | source region | `section` | `role` | parts |
| --- | --- | --- | --- | --- |
| 1 | `request_ir.system: list[SystemPart]` | `system` | `system` | each `SystemPart` |
| 2 | `request_ir.tools: list[ToolDef]` | `tools` | `system` | each `ToolDef` |
| 3 | `request_ir.messages: list[Message]` | `messages` | `Message.role` | each `Message.content[i]: ContentBlock` (`ir.py:110`) |
| 4 | `response_ir.content` | `response` | `assistant` | each response `ContentBlock` |

For each part in order: `block_id = upsert_block(conn, part)` (§3.7: `INSERT … ON
CONFLICT(hash) DO UPDATE SET n_tokens = COALESCE(excluded.n_tokens, block.n_tokens)
RETURNING id`), then `INSERT INTO exchange_block(exchange_id, pos, block_id, role,
section)`. `block.kind` is derived by `block_kind(part)` (§3.3/§12). System and tool_def
blocks arise **only** here (the wire request regions), never from transcripts (§4.1.4).

**`seq`.** Assigned by the writer per §6.5 (ts-rank within session; `MAX(seq)+1`
incrementally, preserved on re-ingest).

### 7.3 Transcript write path (one `transcript_turn` per `NormalizedTurn`)

**Trigger.** The §9 tailer opens a `TranscriptSource` (§4), reads native records, threads
`TurnContext` (seq, parent_id, model, source_line, pending_calls), calls
`adapter.normalize(record, ctx)` (§4/§5), and for each non-None `NormalizedTurn` calls
`writer.submit(build_transcript_job(turn, ctx.binding))`. The `SessionBinding` is already in
hand: `adapter.bind()` produced it and the tailer threads it through `TurnContext.binding`
(§4.2), so no extra data source is needed. `build_transcript_job` (`index/ingest.py`) maps
the `(NormalizedTurn, SessionBinding)` pair to a frozen `TranscriptTurnIngest` (the binding
supplies the FK-parent `session` row; the turn supplies everything else).

**tier-1 side (source recording, minimal).** The transcript's raw bytes live at the CLI's
**native** location, and `transcript_turn.source_path` points there (claude jsonl path +
`source_line`; opencode `opencode_export:{ses_id}`; etc., per §5). The tier-1 contribution
is recording the run's **transcript source descriptor** (the `TranscriptSource` from
`adapter.locate()`: path/ref + format + `session_id`) in the run manifest, so the run dir
remains the authority for which transcript belongs to this run. The exact manifest field is
a minimal additive tier-1 change owned by §11; an optional byte-snapshot of the native file
into the run dir (for self-contained rebuild) is likewise deferred to §11. §7 does not
copy transcript bytes.

**tier-2 side (upsert, mirrors §4.3).** In one job, FK-ordered:

1. Upsert `session` (PK `session_id`) from the `SessionBinding` (§4.2 maps 1:1 to the
   `session` row) via the shared `upsert_session(conn, binding)`.
   `transcript_turn.session_id` is `NOT NULL` (a turn only exists under a bound session,
   §3.4).
2. Upsert `transcript_turn` (PK `turn_id`) with `role, parent_id, seq, ts, is_sidechain,
   model, source_path, source_line` (identically named columns, §4.3).
3. Delete then re-insert `turn_block` edges: `DELETE FROM turn_block WHERE turn_id = ?`,
   then for each `parts[i]`: `block_id = upsert_block(conn, parts[i])`; `INSERT INTO
   turn_block(turn_id, pos=i, block_id, role = turn.role)`. A transcript turn carries one
   role, so every edge takes the turn's role (§4.3).

Because `parts` are `ir.ContentBlock`s (§4.1.3), identical content across the wire and
transcript streams produces the **same `block.hash`** and dedups to one `block`, which is
what makes the §8.4 pivot/diff exact.

### 7.4 Idempotency / re-ingest (schema keys in §3.7)

- **Entities** upsert on their PK; re-ingest replaces the row. For `wire_exchange`, the
  `ON CONFLICT(exchange_id)` update preserves `seq` (§6.5).
- **Edges** are deleted and re-inserted on every entity write, so a re-ingest that changes
  part order or count cannot leave stale edges. (Entity-level cascade also removes edges if
  the entity row is deleted, but the write path uses explicit delete+reinsert and never
  deletes the entity.)
- **Blocks** are only ever inserted, or have `n_tokens` back-filled via `COALESCE` on
  conflict; identity/text columns never change (§3.3 immutability). Orphaned blocks are
  reclaimed by GC (§10), never by the write path.
- A full **rebuild** (§10/§11) is just the live write path replayed over every tier-1 run
  dir; the keys above guarantee it converges to the same tier-2 state.

### 7.5 File placement (additive to §12, all ≤ 700 LOC)

```
api/src/transport_matters/index/
├── writer.py    # §6.3 IndexWriter (thread + bounded queue + batched BEGIN IMMEDIATE with
│                #   per-job SAVEPOINT), IndexJob; load_runtime()/shutdown hooks   (~240 LOC)
├── sessions.py  # SESSION_NS (frozen) + synth_session_id(run_id, provider, native_session_id)
│                #   + upsert_session(conn, SessionBinding). Shared by the §5 read-back
│                #   adapters and the §7.2 wire correlation so both streams converge on one
│                #   session_id. (SessionBinding from index/adapters/base.py; no cycle.) (~90 LOC)
└── ingest.py    # bind_exchange(IndexEntry, ExchangeArtifacts, run_facts)->SessionBinding|None;
                 #   build_wire_job(IndexEntry, ExchangeArtifacts, SessionBinding|None)->IndexJob;
                 #   build_transcript_job(NormalizedTurn, SessionBinding)->IndexJob; the §7.2/§7.3
                 #   row mapping + edge flattening. Imports storage + ir + index. (~290 LOC)
```

The injected post-persist sink (§6.4) is registered in `addon_runtime.load_runtime()` and
closes over the per-run `SessionBinding` static facts (§7.2); the recorder seam is the
existing post-persist emission point (`exchange_recorder.py:~520`, beside `emit_exchange`).
No new import edge into `storage`.

## 8. Read path / query API

The read path is a small, pure SQL surface (`index/queries.py`) wrapped by a FastAPI
router (`api/v1/index_routes.py`, prefix `/api/index`) registered in the existing
`api/v1/router.py` (`router.py:1-18`). It delivers the four capabilities the substrate
exists for: **search**, **session timeline**, the **wire↔transcript pivot**, and the
**DIFF** that is the whole point (§1.1). Raw bytes are always served from tier-1.

### 8.1 Read connection (read-only, never blocks the writer)

Reads use a **separate, short-lived** connection opened read-only:
`connect(index_db_path(), read_only=True)` applies the §3.1 PRAGMAs plus `PRAGMA query_only
= ON`. Under WAL, readers see a consistent snapshot and never block the §6 writer thread
(nor each other); the writer never blocks readers. HTTP handlers run on the same in-process
FastAPI server (`addon_runtime.py`); each request opens (or borrows from a tiny read pool)
a read connection and closes it. No reader ever holds a write lock.

### 8.2 Two-phase search (metadata → bodies, mirrors the cm pattern)

Search is content-addressed at the **block** level (one FTS index covers both streams,
§3.6) and returns occurrences via the edges, so a hit can be traced to every
exchange/turn/run it appears in.

**Phase 1 — `search_blocks(...) -> list[BlockHit]`** (metadata + snippet, no bodies):

```sql
SELECT b.id, b.hash, b.kind, b.n_tokens,
       snippet(block_fts, 0, '[', ']', '…', 12) AS snippet,
       bm25(block_fts)                          AS rank,
       e.stream, e.entity_id, e.role, e.section, e.session_id, e.ts, e.run_id
FROM block_fts
JOIN block b ON b.id = block_fts.rowid
JOIN (  -- unified occurrence view over both edge tables
  SELECT 'wire' AS stream, eb.block_id, eb.exchange_id AS entity_id, eb.role, eb.section,
         we.session_id, we.ts, we.run_id, we.provider, NULL AS cli, 0 AS is_sidechain
  FROM exchange_block eb JOIN wire_exchange we ON we.exchange_id = eb.exchange_id
  UNION ALL
  SELECT 'transcript', tb.block_id, tb.turn_id, tb.role, NULL,
         tt.session_id, tt.ts, tt.run_id, tt.provider, tt.cli, tt.is_sidechain
  FROM turn_block tb JOIN transcript_turn tt ON tt.turn_id = tb.turn_id
) e ON e.block_id = b.id
WHERE block_fts MATCH :q
  AND (:kind     IS NULL OR b.kind     = :kind)
  AND (:stream   IS NULL OR e.stream   = :stream)
  AND (:provider IS NULL OR e.provider = :provider)
  AND (:cli      IS NULL OR e.cli      = :cli)
  AND (:role     IS NULL OR e.role     = :role)
  AND (:section  IS NULL OR e.section  = :section)
  AND (:session  IS NULL OR e.session_id = :session)
  AND (:run      IS NULL OR e.run_id   = :run)
  AND (:since    IS NULL OR e.ts >= :since)
  AND (:until    IS NULL OR e.ts <= :until)
  AND (:sidechain IS NULL OR e.is_sidechain = :sidechain)
ORDER BY rank
LIMIT :limit OFFSET :offset;
```

- **`MATCH :q`** is the FTS5 query (`unicode61`, no stemming, §3.6), so code identifiers
  and prose both match literally; BM25 orders results.
- **Structured filters** are all optional and AND-combined: `kind, stream, provider, cli,
  role, section, session_id, run_id, ts range, is_sidechain`. (`workspace_hash` is reachable
  by joining `session`; added as a filter when needed.)
- **Two result modes.** *Occurrence-centric* (default, the query above): one row per
  edge, for "where exactly does this content live." *Block-centric*: wrap in `GROUP BY b.id`
  with `COUNT(*) AS occurrences` and `GROUP_CONCAT(DISTINCT e.session_id)`, for "this
  content appears in N places across runs" (the dedup view). The mode is a query parameter.

**Phase 2 — `get_block_bodies(ids) -> list[BlockBody]`**: `SELECT id, hash, kind, text,
identity_canonical, n_tokens FROM block WHERE id IN (…)`. Callers fetch full bodies only
for the blocks they choose to expand, keeping result payloads small (the cm
`search → get` discipline). `identity_canonical` is the **semantic** reconstruction
(parse back to a renderable part); byte-exact bytes are §8.5.

### 8.3 Session timeline (reconstruct a thread from blocks)

`session_timeline(session_id, stream, with_bodies=False, seq_from=None, seq_to=None)`
reconstructs an ordered conversation for one stream:

- **wire:** `wire_exchange WHERE session_id = ? [AND seq BETWEEN ?..?] ORDER BY seq`, then
  per exchange `exchange_block ⋈ block ORDER BY pos`, grouped by `section`+`role`.
- **transcript:** `transcript_turn WHERE session_id = ? [AND seq BETWEEN ?..?] ORDER BY
  seq`, then per turn `turn_block ⋈ block ORDER BY pos`.

Two-phase by default: it returns the **entity skeleton** (exchanges/turns with metadata and
their ordered `block_id`s, no bodies) so large sessions paginate by `seq` range; pass
`with_bodies=True` to inline `block.text`/`identity_canonical`. The DAG link
(`transcript_turn.parent_id`) is returned so a caller can render the turn tree (subagent
sidechains carry `is_sidechain = 1`).

### 8.4 Wire↔transcript pivot and DIFF (the §1.1 payload)

Base correspondence is the `session_id` join; it is **sharpened** by exact block-hash
intersection (identical content → identical `block_id`, §2):

```sql
-- session_pivot(session_id): strongest wire-exchange ↔ transcript-turn correspondences
SELECT eb.exchange_id, tb.turn_id, COUNT(*) AS shared_blocks
FROM exchange_block eb
JOIN turn_block tb ON tb.block_id = eb.block_id
JOIN wire_exchange   we ON we.exchange_id = eb.exchange_id AND we.session_id = :session
JOIN transcript_turn tt ON tt.turn_id     = tb.turn_id     AND tt.session_id = :session
GROUP BY eb.exchange_id, tb.turn_id
ORDER BY shared_blocks DESC;
```

The headline analysis is the **block-set DIFF** within a session, which is literally "what
the harness believed (transcript) vs what hit the provider (wire)":

```sql
-- session_diff(session_id) -> three block-id sets
WITH wire AS (SELECT DISTINCT eb.block_id FROM exchange_block eb
              JOIN wire_exchange we ON we.exchange_id = eb.exchange_id WHERE we.session_id = :s),
     tx   AS (SELECT DISTINCT tb.block_id FROM turn_block tb
              JOIN transcript_turn tt ON tt.turn_id = tb.turn_id WHERE tt.session_id = :s)
SELECT 'wire_only'       AS bucket, block_id FROM wire WHERE block_id NOT IN (SELECT block_id FROM tx)
UNION ALL
SELECT 'transcript_only', block_id FROM tx   WHERE block_id NOT IN (SELECT block_id FROM wire)
UNION ALL
SELECT 'shared',          block_id FROM wire WHERE block_id IN (SELECT block_id FROM tx);
```

`wire_only` surfaces injected system reminders / additive replay / real tool schemas that
the transcript never recorded; `transcript_only` surfaces what the harness believed it sent
but the wire shows it did not (the analysis value of §1.1). Bodies for any bucket come from
phase-2 `get_block_bodies`.

> **opencode caveat (carried from §5.4).** When `session_id` could not be correlated for an
> opencode wire exchange, the pivot/diff fall back to `run_id` + block-hash intersection +
> ts proximity; this is the weakest seam and is flagged, not silently treated as exact.

### 8.5 Raw fetch (always from tier-1)

`exchange_raw_ref(exchange_id) -> RawRef` returns `wire_exchange.raw_dir` and resolves the
tier-1 artifact paths (`ExchangeArtifactPaths.request_raw` / `response_raw`,
`disk_layout.py:32-44`). The HTTP layer streams the file; tier-2 stores **no** raw bytes.
This complements (does not duplicate) the existing single-exchange endpoints
(`GET /api/exchanges/{id}`, `exchanges.py:160-185`): tier-2 adds **cross-run search** and
**correlation**, which the `index.jsonl`-backed endpoints cannot do.

### 8.6 Python query surface (`index/queries.py`, NEW; read-only, each fn ≤ 150 LOC)

```python
def search_blocks(conn, q: str, *, filters: SearchFilters, mode: Literal["occurrence","block"] = "occurrence",
                  limit: int = 50, offset: int = 0) -> list[BlockHit]: ...
def get_block_bodies(conn, ids: list[int]) -> list[BlockBody]: ...
def list_sessions(conn, *, filters: SessionFilters) -> list[SessionRow]: ...
def session_timeline(conn, session_id: str, *, stream: Literal["wire","transcript"],
                     with_bodies: bool = False, seq_from: int | None = None,
                     seq_to: int | None = None) -> list[TimelineEntry]: ...
def session_pivot(conn, session_id: str) -> list[Correspondence]: ...
def session_diff(conn, session_id: str) -> SessionDiff: ...
def exchange_raw_ref(conn, exchange_id: str) -> RawRef: ...
```

Row/result models (`BlockHit, BlockBody, TimelineEntry, Correspondence, SessionDiff,
RawRef, SearchFilters, SessionFilters`) are frozen pydantic, added to the §12 `models.py`
roster. All functions are pure reads (no writes), so they are safe to run concurrently
against the read connection while the writer thread commits.

### 8.7 HTTP endpoints (`api/v1/index_routes.py`, NEW; thin wrappers)

| method + path | query fn | notes |
| --- | --- | --- |
| `POST /api/index/search` | `search_blocks` + `get_block_bodies` | body = `{q, filters, mode, limit, offset, expand_ids?}`; phase-1 hits, optional phase-2 bodies for `expand_ids` |
| `POST /api/index/blocks` | `get_block_bodies` | body = `{ids}`; phase-2 bodies |
| `GET /api/index/sessions` | `list_sessions` | filter by workspace/run/provider/cli |
| `GET /api/index/sessions/{session_id}/timeline` | `session_timeline` | `?stream=&with_bodies=&seq_from=&seq_to=` |
| `GET /api/index/sessions/{session_id}/pivot` | `session_pivot` | wire↔turn correspondences |
| `GET /api/index/sessions/{session_id}/diff` | `session_diff` | the §1.1 DIFF; bodies via `/blocks` |
| `GET /api/index/exchanges/{exchange_id}/raw` | `exchange_raw_ref` | `?part=request|response`; streams tier-1 bytes |

These register alongside the existing routers in `api/v1/router.py`. Live-tail push of new
rows over `broadcast.py`/`sse.py` (`/api/stream`, `stream.py:17-39`) is **§9 (Phase D)**;
§8 is the pull/query surface only.

### 8.8 File placement (additive to §12, all ≤ 700 LOC)

```
api/src/transport_matters/
├── index/queries.py            # §8.2–8.5 pure read surface                     (~300 LOC)
└── api/v1/index_routes.py      # §8.7 FastAPI router (prefix /api/index),
                                #   registered in api/v1/router.py               (~180 LOC)
```

## 9. Live-tail

Live-tail makes newly captured wire exchanges and newly written transcript turns appear in
the UI as they happen, **reusing the existing push transport verbatim** —
`broadcast.emit()` + the `/api/stream` SSE endpoint. No new socket, no new protocol.

### 9.1 What is already live (no new machinery)

The **wire stream is already live.** Every persisted exchange fans out to the UI today via
`emit_exchange()` → `broadcast.emit()` (`exchange_recorder.py:237-260`, the post-persist seam
at `:520`), and the SSE endpoint `/api/stream` (`api/v1/stream.py:17-39`) relays each event to
subscribers from a per-subscriber `asyncio.Queue` (`broadcast.py:17-46`). This covers **codex
too**: codex wire frames arrive on the already-proxied websocket (`codex/transport.py:164-196`,
driven from `addon_handlers.py:157-252`) and emit the same `exchange` event. **Live-tail
therefore adds no watch for the wire stream of any provider.**

What is missing is the **transcript stream**: a CLI writes its transcript to its own native
file/store (claude/gemini/codex jsonl; opencode db/export), which the proxy does not author
and so never broadcasts. §9 adds exactly one thing: a **transcript tailer** that turns those
native writes into §7.3 ingest jobs, plus one new broadcast event so the UI learns a turn is
queryable. (The two streams stay first-class and separate, §1.1 — the tailer feeds
`transcript_turn`, never `wire_exchange`.)

### 9.2 The transcript tailer (`index/tailer.py`, NEW)

One **tailer thread per proxy process** (sibling to the §6 writer thread), owning the set of
active per-session cursors. It is started from `load_runtime()` (`addon_runtime.py:27-53`) and
stopped from the addon `done()` hook (`addon.py:69-71` → `close_runtime`, §6.3 lifecycle). It
never writes tier-2 directly: it produces `NormalizedTurn`s and hands them to the §6 writer via
`writer.submit(build_transcript_job(turn, ctx.binding))`.

```python
@dataclass
class TailCursor:
    """Live position in one session's transcript source. Mutable: advances as records arrive."""
    binding: SessionBinding         # §4.2; carries session_id + how to upsert the session row
    source: TranscriptSource        # §4 FileTailSource | PullSource
    adapter: TranscriptAdapter      # §5 concrete adapter (normalize)
    byte_offset: int = 0            # FileTail: last fully-consumed byte; Pull: 0 (unused)
    seq: int = 0                    # next TurnContext.seq
    parent_id: str | None = None    # last emitted turn_id (linear chain; §4)
    pending_calls: dict[str, str] = field(default_factory=dict)  # gemini Format B pairing (§5.3)
    seen_ids: set[str] = field(default_factory=set)              # Pull: message ids already normalized

class TranscriptTailer:
    def start(self) -> None: ...                         # spawn the poll-loop thread
    def register(self, cursor: TailCursor) -> None: ...  # begin tailing a bound session (thread-safe)
    def unregister(self, session_id: str) -> None: ...
    def stop(self, drain: bool = True) -> None: ...      # final pass over every cursor, then exit
```

- **Registration.** A session is tailed once `adapter.bind()` + `adapter.locate()` have produced
  a `(SessionBinding, TranscriptSource)`. For **minted** providers (claude/gemini) this happens
  at launch — the path is known before the CLI writes a byte (§5.1/§5.3), so the cursor registers
  eagerly with `byte_offset = 0`. For **read-back** providers (codex/opencode) the native id is
  unknown until the wire side observes it, so registration is **triggered by the first wire
  frame** that reveals the native session id (codex thread uuid from the proxied frames, §5.2;
  opencode `ses_` id where present, §5.4) — see §15 risk 2.
- **Poll, not inotify.** The tailer **polls** on a short fixed interval (default 250 ms file /
  2 s pull, tunable). For a single-user local tool this avoids a new dependency
  (`watchdog`/inotify/FSEvents) and per-platform watch-handle bookkeeping; latency is bounded by
  the interval, the one knob §15 flags if sub-100 ms live-tail is ever required. The poll is
  cheap: `os.stat` each FileTail path and skip cursors whose `(size, mtime)` is unchanged.

### 9.3 Per-shape watch mechanism

| source shape | provider(s) | mechanism |
| --- | --- | --- |
| `FileTailSource` | claude, gemini Format A, codex rollout | `stat` size/mtime; if grown, `seek(byte_offset)`, read appended bytes, split on `\n`, parse each **complete** (newline-terminated) JSON record, advance `byte_offset` only past consumed records — a trailing partial line is left for the next poll (§15 crash-safety). Each parsed record → `adapter.normalize(record, ctx)`; non-`None` → submit. `source_line` is the running line number. |
| `PullSource` | opencode | re-run `opencode export <ses_id>` (or read the `message`/`part` db rows, §5.4) on the poll interval; reshape to canonical records; **diff against `seen_ids`** and normalize only new messages. Pull is heavier than tail, so opencode polls on the **longer** interval and/or is **kicked** by wire activity for that `run_id`. |

The loop that reads records, assigns `seq`, threads `parent_id`/`model`/`pending_calls`, and
calls `normalize` is the §4 "iteration seam" deferred from Phase B and the §7.3 trigger. It
lives here, in the tailer, **once** — the same record-iterate function serves both live-tail
(growing file) and §11 backfill (closed file), so there is no second iteration path to drift
(DRY).

### 9.4 New rows reach the UI

The live signal is emitted by the **§6 writer thread after a successful batch `COMMIT`**, not by
the tailer — this ties the push to durability, so the moment the UI hears about a turn, a §8
query for it succeeds. Wire already emits its `exchange` event at tier-1 persist; the writer adds
**one** new event for the transcript stream (metadata only, mirroring the lightweight `exchange`
event — bodies are never pushed; the UI pulls them via §8):

```jsonc
// additive to the existing {"type":"exchange", …} / {"type":"exchange_deleted", …}
{ "type": "transcript_turn", "session_id": "...", "turn_id": "...", "run_id": "...",
  "seq": 42, "role": "assistant", "ts": "...", "is_sidechain": false,
  "cli": "claude", "provider": "anthropic" }
```

An optional second event, `{"type":"session_correlated","session_id":"...","exchange_id":"..."}`,
is emitted when a previously-`NULL` `wire_exchange.session_id` is back-filled by a later
correlation upsert (§7.2), so the UI can refresh the §8.4 pivot/diff view. Both are
forward-additive: existing `/api/stream` consumers ignore unknown `type`s.

**Thread-safety (load-bearing).** `broadcast.emit()` calls `asyncio.Queue.put_nowait`
(`broadcast.py:36-46`), which is **not** safe to call from a non-event-loop thread, and the §6
writer runs on its own OS thread. The writer therefore captures the running event loop at
`load_runtime()` and emits via `loop.call_soon_threadsafe(broadcast.emit, event)` for each
committed entity. This is the single point where tier-2's background threads touch the asyncio
world; everywhere else they speak only SQLite and `queue.Queue`.

### 9.5 File placement (additive to §12, ≤ 700 LOC)

```
api/src/transport_matters/index/
└── tailer.py   # §9.2 TranscriptTailer + TailCursor; the record-iterate seam (§4/§7.3)
                #   shared with §11 backfill.                                     (~260 LOC)
```

The `loop.call_soon_threadsafe` live-push helper is added to `index/writer.py` (§6.3), which
owns the post-commit moment; `tailer.py` only submits jobs.

## 10. Delete + GC + rebuild

Tier-2 is a rebuildable projection (§3, locked), so every destructive operation here is safe:
the worst case is "drop it and replay tier-1." This section defines run-delete, block GC, the
periodic disk reconcile, and the full rebuild. **All run on the §6 writer thread** (the single
per-process writer), as ordinary maintenance tasks drained from the same queue, so they never
race the live write path.

### 10.1 The durable run-dir enumerator (load-bearing prerequisite)

Reconcile (§10.3), rebuild (§10.4), and backfill (§11) all need to enumerate **every run that
ever captured data**, not just live ones. The run **`Manifest` is the wrong source**: it is a
per-run **liveness beacon**, written at launch and **unlinked on exit** (`launch_runtime.py:520-541`
— `manifest_path.unlink()` in the `finally`; docstring: *"a per-run liveness beacon … to tell a
live run from a stale manifest"*). So `manifest.read_all()` (`manifest.py:99`) returns only
**currently-live** runs and is blind to completed history.

The durable per-run marker is the wire index `index.jsonl` (written/rewritten by `storage/disk.py`,
persisted for the life of the run dir). A run that captured ≥ 1 exchange has one; a run that
captured none has nothing to project. The enumerator is therefore:

```python
def iter_run_dirs(workspaces_root: Path) -> Iterator[RunDir]:
    """Durable run dirs = those holding an index.jsonl. Globs {slug}/{hash}/{run_id}/index.jsonl
    (same */*/*  depth as manifest.read_all, but keyed on the DURABLE artifact)."""
    for index_path in workspaces_root.glob("*/*/*/index.jsonl"):
        yield RunDir(root=index_path.parent, run_id=index_path.parent.name)
```

`manifest.read_all()` is still used — but **only** to learn the set of **currently-live** runs,
so reconcile never evicts or disturbs an in-flight run (§10.3). It is never the backfill/reconcile
*enumerator*.

### 10.2 Run-delete (and single-exchange delete)

Deleting a run from tier-2 is keyed by `run_id` and relies on the §3.5 cascades:

```sql
DELETE FROM wire_exchange   WHERE run_id = :run;   -- cascades exchange_block edges
DELETE FROM transcript_turn WHERE run_id = :run;   -- cascades turn_block edges
DELETE FROM session         WHERE run_id = :run;   -- entities already gone
```

Order matters under `foreign_keys = ON`: delete the **entities** first (their edges cascade away,
§3.5), then the `session` rows. `block` rows are **never** touched here — blocks are global and
shared across runs; orphans are reclaimed by GC (§10.3), never by delete.

Single-exchange delete already exists on the wire side: the `{"type":"exchange_deleted","id":…}`
broadcast (`exchange_recorder.py:263-267`) and tier-1's `_reconcile_staged_deletes()`
(`storage/disk.py`). Tier-2 mirrors it with `DELETE FROM wire_exchange WHERE exchange_id = :id`
(edges cascade). Both run-delete and exchange-delete enqueue a GC pass (§10.3) afterward.

### 10.3 Block GC (mark-and-sweep)

A block is reclaimable once no edge references it. With `foreign_keys = ON` the `block_id` FK has
**no** cascade (§3.5), so a referenced block cannot be deleted — GC is a safe sweep of the
unreferenced set:

```sql
DELETE FROM block
WHERE NOT EXISTS (SELECT 1 FROM exchange_block WHERE exchange_block.block_id = block.id)
  AND NOT EXISTS (SELECT 1 FROM turn_block     WHERE turn_block.block_id     = block.id);
```

- `NOT EXISTS` (not `NOT IN`) so the planner uses the `exchange_block_block` / `turn_block_block`
  indexes (§3.5) and short-circuits — important because `block` is the largest table.
- Deleting a block fires the `block_ad` trigger (§3.6), evicting its `block_fts` row, so the FTS
  index never holds orphans.
- **Timing (cost-aware, §15).** GC is **not** run per-batch (most batches orphan nothing, and the
  sweep scans `block`). It runs (a) after a run-delete / exchange-delete batch, and (b) on an idle
  timer / at `stop(drain=True)`. The constant Anthropic system+tools block-set is referenced by
  every run, so it is correctly **never** collected while any run survives.

### 10.4 Periodic disk reconcile (tier-2 vs durable run dirs)

Out-of-band `rm -rf` on a run dir leaves tier-2 rows with no backing run; a dropped write (§6.3
backpressure) leaves a run dir under-represented in tier-2. A periodic reconcile (on first-boot,
§11, and on an idle timer) repairs both directions against the **durable** on-disk set from
`iter_run_dirs(workspaces_root)` (§10.1):

- **Orphaned tier-2 runs** — `SELECT DISTINCT run_id FROM session ∪ wire_exchange` minus the
  durable on-disk `run_id` set → run-delete (§10.2) each. Runs in the **live set**
  (`manifest.read_all()`) are skipped — they are mid-flight, not orphaned.
- **Missing / under-counted runs** — a durable `run_id` whose tier-1 `index.jsonl` entry count
  exceeds `SELECT COUNT(*) FROM wire_exchange WHERE run_id = ?` → wire replay for that run
  (§11.2), which is idempotent (§3.7).
- After reconcile, `PRAGMA wal_checkpoint(TRUNCATE)`; an occasional `VACUUM` (idle only — it takes
  an exclusive lock) reclaims file space from large deletes.

### 10.5 Rebuild from tier-1 (the safety net)

Rebuild is the projection guarantee made literal: **drop tier-2, recreate the schema, replay every
durable run dir through the §7 write path.** Invoked on (a) `schema_version` / `identity_canonical`
/ `session_ns` mismatch at boot (§3.2 — drop + rebuild, no migration), (b) an explicit
`--rebuild-index` command, or (c) reconcile finding wholesale drift.

```
0. [ensure writer quiescence — boot/offline-only by default; online needs a connection-quiescence epoch (see Concurrency)]
1. close + delete index.db (+ -wal/-shm);  apply_schema(connect(path))            (§3.2, §12 schema.py)
2. for run in iter_run_dirs(workspaces_root):                                       (§10.1 — DURABLE)
     a. wire:       replay run/index.jsonl → build_wire_job → writer.submit         (§11.2)
     b. transcript: adapter.locate(binding) → iterate full source → build_transcript_job → submit
                    (§9.3 record-iterate seam over a CLOSED file)
3. INSERT INTO block_fts(block_fts) VALUES('rebuild');   -- §3.6 bulk FTS (faster than per-row triggers)
4. wal_checkpoint(TRUNCATE);  release the rebuild lock
```

The **replay** (steps 2–4) is upsert-keyed (§3.7), idempotent, and reuses the **exact** live ingest
functions — there is no separate "rebuild path" to drift (DRY).

**Concurrency (load-bearing — destructive rebuild ≠ backfill).** Step 1 is **not** safe to run
under live capture. Deleting `index.db` (+ `-wal`/`-shm`) unlinks a file other proxy processes may
still hold open: the WAL + `busy_timeout` discipline (§3.1) coordinates writers **only within one
file**, so a live writer would keep writing to the now-orphaned inode while rebuild creates a
*different* database — silent divergence and loss. Destructive rebuild therefore **requires writer
quiescence at the _connection_ level, not just the transaction level**:

- **boot/offline-only (the default).** Destructive rebuild runs only when no other writer holds an
  open connection to `index.db`:
  - *boot* — inside `load_runtime()`, **before** this process opens its write connection or
    registers the post-persist sink (§6.4). It takes the rebuild lock
    (`~/.transport-matters/index.rebuild.lock`), re-checks `schema_version` (a concurrent booter may
    have already rebuilt → skip), rebuilds, releases, then opens. A booting process holds no writer
    yet, so it has no stale connection to strand. The §3.2 schema-mismatch trigger is this path.
  - *offline `--rebuild-index`* — refuse to run while any **live** run exists (`manifest.read_all()`
    is exactly the live-run beacon set, §10.1); take the lock so none can start mid-rebuild;
    rebuild; release.
- **online rebuild needs CONNECTION quiescence, not a `BEGIN` pause (not required now; specified so
  it is not mis-built).** Pausing writers at `BEGIN IMMEDIATE` is **insufficient**: a paused
  `IndexWriter` still holds an open sqlite3 connection to the *old* inode, which on POSIX survives
  the `unlink` in step 1, so after the lock releases it would resume writing to the **deleted** DB,
  not the rebuilt file. An online protocol must make every `IndexWriter` that observes the rebuild
  lock (via an **epoch** counter in the lock file): (1) finish or roll back its current batch and
  **re-queue** pending jobs, (2) **close** its write connection, (3) wait for the epoch to advance
  (rebuild complete), then (4) **reopen** a fresh connection — which now targets the rebuilt file —
  before accepting writes. Until that protocol is built, rebuild stays boot/offline-only.

> A residual case: a peer already running on an **incompatible prior schema** is not force-quiesced
> by a boot-time rebuild. In a single-user box a `schema_version` bump implies a restart (it ships
> with new code), so old- and new-schema writers are not expected to overlap; accepted and flagged
> here rather than engineered around.

**Backfill (§11.2) needs neither** — it never deletes the file; it upserts into the live DB and is
safe to run concurrently with live capture (the live writes and the replay converge to the same
rows). The dangerous operation is the destructive *drop*, not the *replay*.

### 10.6 File placement (additive to §12, ≤ 700 LOC)

```
api/src/transport_matters/index/
└── maintenance.py   # iter_run_dirs (§10.1), delete_run / delete_exchange (§10.2),
                     #   gc_blocks (§10.3), reconcile(workspaces_root) (§10.4),
                     #   rebuild(workspaces_root) (§10.5). Runs on the §6 writer thread;
                     #   reuses ingest.py replay (§11).                            (~300 LOC)
```

## 11. Migration / first-boot backfill

There is no schema migration (single-user, no-backcompat: §1.3, §3.2). "Migration" here means
the **first-boot backfill** that replays every existing run dir into a fresh tier-2, plus a clear
statement of what (if anything) tier-1 must change.

### 11.1 Required tier-1 change: none

Everything backfill needs is **already durable** in tier-1:

- the wire records — each run's `index.jsonl` (the `IndexEntry` rows, `storage/disk.py:92-144`),
  durable for the life of the run dir and the §10.1 enumerator;
- per-exchange `request.ir.json` / `response.ir.json` (`ExchangeArtifactPaths`,
  `disk_layout.py:32-44`), which carry the IR parts **and** `RequestMetadata.session_id`
  (`ir.py:127`) — so the correlation key is recoverable per exchange with zero new state.

The transcript native files live at the CLI's own location (`~/.claude`, `~/.codex`, `~/.gemini`,
opencode db/export), persisted independently of our run dir, and are **located by
`adapter.locate(binding)`** (§5) from a `SessionBinding` whose `session_id` (minted) or
`native_session_id` (read-back) is recovered from the durable wire artifacts above. So transcript
backfill needs no tier-1 record either.

> **The run `Manifest` must NOT be used to carry backfill state — and this supersedes §7.3.**
> The manifest is unlinked on exit (§10.1), so any descriptor written there vanishes with the run.
> **Phase D correction (supersedes the §7.3 "tier-1 side (source recording, minimal)" paragraph,
> ~lines 1186-1194):** where §7.3 (Phase C) says the transcript source descriptor is recorded
> *"in the run manifest"* and that *"the exact manifest field is a minimal additive tier-1 change
> owned by §11,"* read instead — the descriptor is **not** persisted in tier-1 at all (required
> change = none, per this section); it is recovered at backfill time (§11.2) or, optionally,
> written to a **durable** per-run `sessions.json` (below), **never** the manifest. The §7.3
> optional byte-snapshot likewise stays a deferred forward hook and is not manifest-resident. This
> is why §11 takes **zero** mandatory tier-1 change rather than "add manifest fields."

**Optional robustness enhancement (forward hook, not required).** A small **durable** per-run
`sessions.json` (written in the run dir at `adapter.bind()`/`locate()` time — a *new durable
artifact, never the ephemeral manifest*) recording each bound session's
`{session_id, provider, cli, native_session_id, minted, source, started_at}` would make transcript
discovery robust where `locate()` derivation is fragile (notably gemini's `projectKey` ambiguity,
§5.3, and the orphan case below). Backfill **prefers** it when present and **falls back** to the
recovery path above when absent. It is explicitly optional: the spec's correctness does not depend
on it, and it can be added later because tier-2 is rebuildable.

### 11.2 First-boot backfill (replay durable run dirs into tier-2)

Runs on writer start when tier-2 is empty/new, and per-run from §10.4 reconcile. It is the §7 write
path applied to historical data, enumerated by the **durable** §10.1 helper:

```
for run in iter_run_dirs(workspaces_root):                 # DURABLE: globs */*/*/index.jsonl
  if fully_indexed(run): continue                          # §10.4 count check (idempotent skip)
  WIRE:
    for entry in load_index_jsonl(run):                    # disk._ensure_index_cache → IndexEntry
      artifacts = load_ir_artifacts(run, entry)            # request.ir.json / response.ir.json
      binding   = bind_exchange(entry, artifacts, run_facts)   # §6.4/§7.2 — recovers session_id
      writer.submit(build_wire_job(entry, artifacts, binding)) # §7.2
  TRANSCRIPT:
    for binding in sessions_of(run):                       # from sessions.json if present, else
                                                           #   derived from the wire bindings above
      source = adapter.locate(binding)                     # §5 — finds the native transcript
      iterate full source (§9.3 seam, CLOSED file) → normalize → build_transcript_job → submit
```

Idempotent upserts (§3.7) make backfill safe to run repeatedly and **concurrently with live
capture** — a run that is both live and being backfilled converges to one tier-2 state. Backfill is
the **same code** as live ingest (§9.3 iterate seam, §7 jobs); only the record source differs
(closed file / `index.jsonl` vs growing file / live sink), so there is no parallel implementation
to drift (DRY). `run_facts` (cwd, slug, hash, cli) come from the run dir path
(`workspace_id`-decodable, `workspace.py`) plus the `IndexEntry` provider/model.

### 11.3 The one un-backfillable case (flagged, §15)

A session that produced a **transcript but no captured wire exchange** has no `index.jsonl` row and
no `request.ir.json`, so its `session_id`/native id cannot be recovered, and without an optional
`sessions.json` it cannot be located. Such a run is a transcript-only orphan with no wire
counterpart — outside the substrate's correlation purpose (§1.1), which is the wire↔transcript
DIFF. It is recorded as a known limitation, not silently dropped (§15 risk 3); the optional
`sessions.json` (§11.1) closes it if a use case ever needs transcript-only runs indexed.

### 11.4 Schema-version mismatch → drop + rebuild

On boot, if `schema_meta.schema_version` / `identity_canonical` / `session_ns` differ from the code
constants (§3.2), tier-2 is dropped and the §10.5 rebuild runs — which is §11.2 backfill over every
durable run dir. No `ALTER`, no shim.

## 12. Module / file layout

New package **`api/src/transport_matters/index/`** (tier-2). Sits after `storage` in the
import DAG; imports only `ir` and the canonicalization helpers. Every file ≤ 700 LOC,
functions ≤ ~150 LOC.

```
api/src/transport_matters/
├── canonicalization.py        # NEW — shared LOW-LEVEL helpers only: canonical_json,
│                              #   _canonical_fields, _json_string. (override_audit keeps
│                              #   canonical_block_json for CHAR ACCOUNTING; SEMANTIC
│                              #   identity_canonical lives in index/blocks — see note)
├── index/
│   ├── __init__.py            # public exports (apply_schema, connect, upsert_block, models)
│   ├── schema.py              # DDL constants (§3.1–3.6) + apply_schema(conn) +
│   │                          #   schema_meta seed/check + rebuild_fts(conn)   (~200 LOC)
│   ├── db.py                  # connect(path)->Connection applying PRAGMAs;
│   │                          #   index_db_path() = default_storage_root()/"index.db";
│   │                          #   transaction() context helper                  (~140 LOC)
│   ├── blocks.py              # identity_canonical(part)->str (dispatch to canonicalization.*);
│   │                          #   block_hash(canonical)->str (blake2b-256);
│   │                          #   block_kind(part)->str; block_text(part)->str;
│   │                          #   upsert_block(conn, part)->int                 (~240 LOC)
│   └── models.py              # frozen pydantic rows: BlockRow, SessionRow,
│                              #   WireExchangeRow, TranscriptTurnRow, BlockEdge  (~190 LOC)
└── index/test_*.py            # colocated unit tests (Phase A: schema apply, block dedup,
                               #   kind/hash determinism, FTS insert/delete trigger)
```

**Canonicalization placement (DRY) — two distinct encoders, shared helpers.** The
**low-level** canonical helpers `canonical_json` / `_canonical_fields` / `_json_string`
currently live in `override_audit.py`. Extract them into a new **`canonicalization.py`**
(depends only on `ir`; keeps the DAG clean) so two *separate* higher-level encoders can
share them without duplicating the JSON-canonicalization logic:

- **`override_audit.canonical_block_json`** — unchanged. **Keeps** `provider_data`; remains
  the basis for production **char accounting** (`block_chars`, `count_chars_parts`). It is
  **not** used for block identity.
- **`index/blocks.identity_canonical(part)`** — new. The **semantic identity** encoder of
  §3.3: same low-level helpers, but `provider_data` (and `SystemPart.cache_hint`)
  **stripped uniformly** for all eight kinds, plus the `system` and `tool_def` cases. It is
  a *separate* function, **never** a verbatim reuse of `canonical_block_json`.

This keeps identity (stream-invariant, lossy) and char accounting (occurrence-exact, with
`provider_data`) correctly distinct while sharing one copy of the low-level canonicalizer.
*Fallback if the extraction is deferred:* `index/blocks.py` imports only `canonical_json`
from `override_audit.py` and defines `identity_canonical` locally — it must **not** call
`canonical_block_json` (doing so would re-introduce `provider_data` into identity).

Tier-1 disk layout (`storage/disk_layout.py`, `workspace.py`) is **unchanged** in Phase
A. Tier-2 is additive.

## 13. Test plan

Tests run against a **real SQLite database** (a temp `index.db`), never a mock — the value of this
substrate is exact SQL behavior (FTS, FK cascade, partial-unique idempotency, triggers), which a
mock would hide. Fixtures use a temp `HOME` / `workspaces_root` so sample and run-dir paths resolve
hermetically. Unit tests colocate as `index/test_*.py` (§12, `api/CLAUDE.md` colocated-tests rule);
integration tests live under `tests/integration/`.

### 13.1 Unit

| area | test | asserts |
| --- | --- | --- |
| block dedup | same content under two roles/streams + once with `provider_data`, once without | one `block` row; identical `hash`; the `provider_data` variant collapses to the same block (§3.3 stream-invariant identity) |
| canonical identity | `identity_canonical(part)` for every kind | `type` emitted first; `provider_data`/`cache_hint` stripped; **differs** from `canonical_block_json` (which keeps `provider_data`) on the same part (§12) |
| kind determinism | hash → kind | `block.kind` is a pure function of `hash` (text vs thinking vs system with identical text never collide) |
| idempotent upsert | submit same exchange/turn twice | row count stable; edges replaced not duplicated; `wire_exchange.seq` preserved; `block.n_tokens` back-fills NULL→value via COALESCE without touching identity/text (§3.7) |
| session synth | `synth_session_id(run, provider, native)` | deterministic; minted vs read-back; partial unique index `session_native` rejects two ids sharing one non-null native triple, allows multiple minted NULLs (§3.4 multiple-NULL hole) |
| stream convergence | a read-back wire correlation and its transcript adapter | both compute the **same** `session_id` via the shared `synth_session_id` (§7.2 — the pivot depends on it) |
| GC mark-sweep | orphan block + referenced block | orphan deleted, referenced retained, FK blocks deleting a referenced block (`IntegrityError`), `block_ad` evicts the FTS row (§10.3) |
| FK cascade | delete entity / delete run | edges cascade; `wire_exchange.session_id` SET NULL vs `transcript_turn` CASCADE asymmetry holds (§3.4) |
| durable enumerator | run dirs with/without `index.jsonl`; a **live** manifest present | `iter_run_dirs` yields exactly the `index.jsonl`-bearing dirs and **ignores** a manifest-only (no-index) dir; `manifest.read_all` is not the enumerator (§10.1 — the peer-blocked beacon bug) |
| per-adapter normalize | **golden fixtures from the real §5 samples** (one dir per CLI) | claude jsonl line → `NormalizedTurn` (uuid/parentUuid/role/parts); codex `response_item` (message/function_call/output/reasoning); gemini Format A intra-record `toolCalls[]` **and** Format B cross-record `pending_calls` pairing; opencode export/db reshape → identical canonical record; every adapter skips non-conversational records (returns `None`) |

The golden fixtures are committed verbatim from the samples cited in §5 (claude `0c721f8e…jsonl`,
codex `rollout-…jsonl`, gemini `session-…jsonl` both formats + a `checkpoint`, opencode `export`/db),
so a normalize regression is caught against ground truth.

### 13.2 Integration

| flow | test |
| --- | --- |
| capture → index → search | drive a synthetic exchange through the writer; `search_blocks` finds its text; `get_block_bodies` returns the body; `exchange_raw_ref` resolves to the tier-1 dir (§8) |
| wire↔transcript correlation join | ingest a wire exchange and a transcript turn that **share content** under one `session_id`; `session_pivot` reports the correspondence; `session_diff` buckets `wire_only` / `transcript_only` / `shared` correctly (§8.4) |
| live-tail (file) | register a `FileTailSource` cursor on a temp jsonl; append lines; assert the tailer consumes complete records, **leaves a trailing partial line**, the writer commits, and a `{"type":"transcript_turn"}` event arrives on `/api/stream` (§9) |
| live-tail (pull) | a fake `opencode export` returning a growing message set; assert only **new** messages (by `seen_ids`) are normalized per poll (§9.3) |
| backfill / rebuild idempotence | pre-populate run dirs (`index.jsonl` + `*.ir.json`), **delete any manifest** to prove durability does not depend on it; run first-boot backfill; snapshot tier-2; run it **again**; assert byte-identical row state (§11.2) |
| run-delete + GC | index two runs sharing the constant system block; delete one run; assert its entities/edges gone, the shared block **retained**, a run-unique block GC'd, FTS consistent (§10.2/§10.3) |
| reconcile | `rm -rf` a completed run dir, then reconcile; assert the orphaned tier-2 run is evicted; add an unindexed `index.jsonl` run dir; assert it is backfilled; a run with a **present (live) manifest** is **not** evicted even if under-counted (§10.4) |
| cross-thread emit | assert the writer emits via `loop.call_soon_threadsafe` and the SSE subscriber receives the event with no "non-threadsafe" error (§9.4) |

### 13.3 Not tested here (out of scope)

Vector search (§1.3), UI rendering (§1.3), and load/perf benchmarking of FTS/GC at scale are out of
this spec; §15 risk 6 flags the perf unknowns.

## 14. Phasing (build order)

Eight slices, each independently shippable and testable. Each builds only on approved/earlier
sections; the tier-2 package is purely additive to the running proxy until slice 2 wires the sink,
and even then the wire path never depends on tier-2 success (§7.1).

| # | slice | delivers | files (§ refs) | acceptance |
| --- | --- | --- | --- | --- |
| 1 | **Core store + writer** | schema applies; block upsert/dedup; single-writer thread drains a queue | `index/{schema,db,blocks,models}.py` (§3, §12), `index/sessions.py` (§7.5), `index/writer.py` (§6.3) | §13.1 dedup / identity / kind / upsert / GC / FTS unit; §3.8 DDL exec already green |
| 2 | **Wire ingest + sink** | live wire capture populates tier-2 off the hot path | `index/ingest.py` (`bind_exchange`/`build_wire_job`, §7.2), injected post-persist sink in `load_runtime()` (§6.4) | capture → `wire_exchange` row + edges; wire-path latency unchanged (§7.1) |
| 3 | **Read / query API** | search, timeline, pivot, diff, raw over HTTP | `index/queries.py` (§8.6), `api/v1/index_routes.py` (§8.7) registered in `router.py` | §13.2 capture→index→search round-trip |
| 4 | **claude transcript + tailer** | claude transcripts indexed and live-tailed; the first end-to-end pivot/diff | `index/adapters/claude.py` (§5.1), `index/tailer.py` (§9.2), `build_transcript_job` (§7.3) | §13.2 correlation join + live-tail(file); claude golden fixtures |
| 5 | **codex adapter** | codex read-back (native id from proxied frames) + rollout file-tail | `index/adapters/codex.py` (§5.2) | codex golden fixtures; codex pivot; read-back session convergence |
| 6 | **gemini + opencode adapters** | the two harder seams: gemini two-format, opencode pull + weak correlation | `index/adapters/{gemini,opencode}.py` (§5.3/§5.4) | gemini Format A/B fixtures + `pending_calls`; opencode reshape + live-tail(pull) |
| 7 | **Live-tail completion** | `transcript_turn` + `session_correlated` events; opencode poll/kick | live-push in `writer.py` (§9.4), opencode poll path (§9.3) | §13.2 cross-thread emit + SSE delivery |
| 8 | **Delete + GC + backfill** | run/exchange delete, block GC, durable reconcile, first-boot backfill, rebuild | `index/maintenance.py` (§10), `iter_run_dirs` durable enumerator (§10.1) | §13.2 backfill idempotence, run-delete+GC, reconcile |

Critical path: **1 → 2 → 3** establishes the core capture+query loop (wire-only, already useful);
**4** adds the transcript half and the **DIFF** that is the point (§1.1); **5/6** extend coverage;
**7/8** complete liveness and lifecycle. Slices 5 and 6 are parallelizable once slice 4 lands the
tailer + transcript-job shape. Backfill (8) can land any time after slice 2 for wire-only and after
slice 4 for transcript, since it reuses those ingest paths verbatim.

## 15. Open risks / escalations

No item requires an orchestrator decision now (Phase D introduced no unresolved contested fork; the
one Phase-D block — manifest-as-enumerator — was resolved in §10.1/§11.1 by switching to the durable
`index.jsonl` enumerator). The following are implementation risks the **whole** spec leaves to the
build, each with the mitigation already chosen:

1. **Cross-thread broadcast (handled; must not regress).** `broadcast.emit` → `asyncio.Queue.put_nowait`
   is event-loop-affine; the §6 writer / §9 tailer are OS threads. Live-push **must** go through
   `loop.call_soon_threadsafe` (§9.4). A direct `emit()` from a background thread would corrupt the
   queue. Called out as a hard constraint, guarded by a §13.2 test.

2. **codex/opencode transcript tail can't start at launch.** Read-back providers learn their native
   session id only from the first wire frame (§5.2/§5.4), so the §9.2 tailer registers that session
   **after** the first exchange. Turns written before that are caught by the cursor's initial
   `byte_offset = 0` full read on registration — nothing is lost, but codex/opencode live-tail has a
   one-exchange startup lag. Acceptable; flagged.

3. **Transcript-only runs are not backfillable** (§11.3). A session with a transcript but no captured
   wire exchange has no durable wire artifact to recover its id from, and absent the optional
   `sessions.json` (§11.1) cannot be located. Outside the wire↔transcript-DIFF purpose (§1.1);
   recorded as a known limitation, closable by the optional durable `sessions.json`.

4. **opencode is the weakest correlation seam.** The `ses_` id is not guaranteed in proxied request
   metadata (§5.4), so wire↔transcript correlation falls back to `run_id` + block-hash intersection +
   ts proximity (§8.4). Diff quality degrades to "probable" rather than "exact." Escalate **only if**
   opencode becomes a primary use case — then the proxy must capture an opencode request header
   carrying the `ses_` id (a wire-capture change outside this spec).

5. **Poll latency vs a watch dependency.** §9.2 chose polling (250 ms file / 2 s pull) to avoid a
   `watchdog`/inotify dependency. If sub-100 ms transcript liveness is ever required, swap the poll
   loop for an inotify/FSEvents watcher behind the same `TailCursor` interface. One knob; no schema
   impact.

6. **Partial-record tails on crash.** A FileTail cursor advances `byte_offset` only past **complete**
   newline-terminated records (§9.3); a process death mid-write leaves a trailing partial line the next
   poll (or backfill) completes. Verified by test (§13.2), but the invariant — "never parse past the
   last `\n`" — is load-bearing and easy to get wrong.

7. **GC / VACUUM cost and timing.** `block` is the largest table; GC sweeps it (§10.3) and `VACUUM`
   takes an exclusive lock (§10.4). Both are restricted to post-delete / idle, never the hot path. FTS
   BM25 ranking and the GC `NOT EXISTS` sweep at very large block counts are **unbenchmarked** — the
   main scale unknown. If GC ever shows in latency, move it fully behind the idle timer.

8. **`seq` monotonicity across processes.** §6.5 assigns `wire_exchange.seq = MAX(seq)+1` per session
   and asserts incremental order equals the rebuild `ORDER BY ts` order under the single per-process
   writer. Two processes writing the **same** `session_id` concurrently (should not happen — a session
   belongs to one run/process) could interleave seq; a rebuild repairs it deterministically. Low risk;
   rebuild is the backstop.

9. **gemini `projectKey` ambiguity.** `locate()` must resolve the tmp subdir as either the
   `projects.json` name or `sha256(cwd)` (§5.3); `--list-sessions` is the robust enumerator and should
   be preferred over path derivation for both live-tail registration and backfill discovery. The
   optional `sessions.json` (§11.1) sidesteps it entirely when present.

10. **Deferred-but-named implementation choices.** The §8.1 read-connection pool size, the §5.1 bonus
    wire-pivot provenance columns (`requestId` / `message.id`), per-occurrence char *attribution* edge
    column (§3.3), and the vector `block_vec` table (§3.7) are forward hooks the rebuildable schema
    already accommodates, to be sized when a consumer needs them — not in this spec.

---

## Appendix A — Phase A decision log (cross-phase handoff)

Load-bearing decisions a cold Phase B/C/D pair must honor:

1. **Block identity = `blake2b-256(identity_canonical)`** — SEMANTIC dedup identity: the
   same `canonical_json` discipline as `canonical_block_json` (type-first) but
   `provider_data` / `cache_hint` **stripped uniformly for all kinds**, so wire and
   transcript representations of the same content hash equal (stream-invariant). Byte-exact
   reconstruction is **tier-1's** job, not the block's. `kind` is payload shape only,
   functionally determined by `hash`.
2. **Role, stream, section, position are EDGE metadata** (`exchange_block`/`turn_block`),
   never on `block`, never in the hash. This is what makes global cross-stream dedup work.
3. **`block.kind` enum is frozen**: `text, tool_use, tool_result, thinking, image,
   system, tool_def, unknown`. Adding a kind = a schema-version bump + rebuild.
4. **Two block body columns**: `identity_canonical` (semantic hash input + semantic
   reconstruction; lossy w.r.t. transport-opaque fields) and `text` (clean FTS
   projection). FTS5 external-content over `text`, triggers on INSERT/DELETE only (blocks
   immutable). **No `n_chars` on `block`** — production char accounting is
   occurrence-dependent and lives on `wire_exchange.req_*_chars` (via `count_chars_parts`);
   `block.n_tokens` is best-effort content size only.
5. **`session_id` is the universal correlation key**; pivot = join on `session_id`
   sharpened by shared `block_id`. Wire exchanges may precede correlation (nullable FK).
6. **tier-2 path** = `~/.transport-matters/index.db`; PRAGMAs per §3.1; single-writer
   enforced by WAL + `busy_timeout` (process owner decided in §6).
7. **Canonicalization is DRY** — one `canonicalization.py`, imported by both
   `override_audit` and `index/blocks`.
8. **`session_id` PK is the idempotency key**: minted UUID (claude/gemini) or
   `uuid5(SESSION_NS, "{run_id}|{provider}|{native_session_id}")` (read-back). A **partial
   unique index** on `(run_id, provider, native_session_id) WHERE native_session_id IS NOT
   NULL` guards double-binding without SQLite's multiple-NULL hole. No table-level
   `UNIQUE` over a nullable column.

## Appendix B — Code grounding (where each decision is anchored)

- Wire IR content parts: `api/src/transport_matters/ir.py` — `ContentBlock`
  (TextBlock/ToolUseBlock/ToolResultBlock/ThinkingBlock/ImageBlock/UnknownBlock, ll.
  19-78), `SystemPart` (l.83), `ToolDef` (l.94), `InternalRequest` (l.138),
  `InternalResponse` (l.165), `RequestMetadata.session_id` (l.127).
- Canonicalization / char accounting: `override_audit.py` — `canonical_json` (l.92),
  `canonical_block_json` (l.117), `block_chars` (l.176), `tool_chars` (l.180),
  `count_chars_parts` (l.186).
- Hashing primitive: `workspace.py` — `blake2b` via `hashlib` (`workspace_id`, l.60).
- Tier-1 layout / keys: `workspace.py` — `WorkspaceId{slug,hash,root}` (l.47),
  `run_root` = `{slug}/{hash}/{run_id}/` (l.85); `storage/disk_layout.py` exchange dir +
  artifact files; `storage/base.py` — `IndexEntry` (l.117), `ReqStats`/`ResStats`.
- Storage root: `storage_roots.py` — `default_storage_root()` = `~/.transport-matters`,
  `default_workspaces_root()` = `…/workspaces`.
