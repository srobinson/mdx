---
title: Helioy Shared Schema: attention-matters vs mdcontext
tags: [sqlite, schema, attention-matters, mdcontext, helioy, architecture]
date: 2026-03-14
---

## Executive Summary

attention-matters and mdcontext solve fundamentally different storage problems. attention-matters stores a geometric memory engine's quaternion vector space in SQLite. mdcontext stores a flat-file markdown index plus binary/JSON artifact files. There is partial conceptual overlap at the "document with sections" level, but the storage primitives, access patterns, mutation rates, and coupling concerns diverge sharply enough that a shared SQLite file would be net-negative. A shared schema library (DDL-as-code) is worth considering; a shared database file is not.

---

## 1. attention-matters: Schema in Full

Source: `crates/am-store/src/schema.rs` — schema version 7 as of analysis date.

### 1.1 SQLite Configuration

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA wal_autocheckpoint = 100;  -- checkpoint every ~400KB
```

WAL mode with aggressive checkpointing is a deliberate choice driven by a concurrent-reader / single-writer daemon model (`am-server` HTTP daemon + CLI clients). The small autocheckpoint value keeps WAL files small because the daemon continuously writes activation increments.

### 1.2 Core DDL

```sql
CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS episodes (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    is_conscious INTEGER NOT NULL DEFAULT 0,
    timestamp    TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS neighborhoods (
    id                TEXT PRIMARY KEY,
    episode_id        TEXT NOT NULL REFERENCES episodes(id),
    seed_w            REAL NOT NULL,
    seed_x            REAL NOT NULL,
    seed_y            REAL NOT NULL,
    seed_z            REAL NOT NULL,
    source_text       TEXT NOT NULL DEFAULT '',
    neighborhood_type TEXT NOT NULL DEFAULT 'memory',
    epoch             INTEGER NOT NULL DEFAULT 0,
    superseded_by     TEXT
);

CREATE TABLE IF NOT EXISTS occurrences (
    id               TEXT PRIMARY KEY,
    neighborhood_id  TEXT NOT NULL REFERENCES neighborhoods(id),
    word             TEXT NOT NULL,
    pos_w            REAL NOT NULL,
    pos_x            REAL NOT NULL,
    pos_y            REAL NOT NULL,
    pos_z            REAL NOT NULL,
    phasor_theta     REAL NOT NULL,
    activation_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS conversation_buffer (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_text      TEXT NOT NULL,
    assistant_text TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_occ_word         ON occurrences(word);
CREATE INDEX IF NOT EXISTS idx_occ_neighborhood ON occurrences(neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_nbhd_episode     ON neighborhoods(episode_id);
```

### 1.3 Domain Semantics

| Table | Purpose |
|---|---|
| `metadata` | Key/value store for agent name, schema version |
| `episodes` | Temporal contexts (conversations/sessions); one is always the "conscious" episode |
| `neighborhoods` | Quaternion-seeded text chunks (~3 sentences each); the unit of memory |
| `occurrences` | Individual words within a neighborhood, positioned as quaternions in semantic space |
| `conversation_buffer` | Short-term ring buffer for in-flight conversation turns |

### 1.4 Vector Storage Model

Vectors are stored as four bare `REAL` columns (`{seed,pos}_{w,x,y,z}`) — unit quaternions in a 4D geometric space. There are no BLOB columns and no external vector files. Every vector is a row in `neighborhoods` (seed quaternion) or `occurrences` (position quaternion). The geometry IS the schema.

### 1.5 Migration Strategy

Additive `ALTER TABLE ... ADD COLUMN` migrations gated on `stored_version < N` checks inside `initialize()`. Version is stored in the `metadata` table under the key `schema_version`. The pattern is:

```rust
if stored_version < N && conn.prepare("SELECT new_col FROM table LIMIT 0").is_err() {
    conn.execute_batch("ALTER TABLE table ADD COLUMN new_col TYPE DEFAULT val;")?;
}
conn.execute_batch("INSERT OR REPLACE INTO metadata VALUES ('schema_version', N);")?;
```

This is safe but manual. There is no migration framework.

---

## 2. mdcontext: Index Structures

mdcontext uses NO SQLite. The index is a set of flat JSON files plus binary artifact files.

### 2.1 File Layout

```
<root>/.mdcontext/
  config.json
  indexes/
    documents.json      -- DocumentIndex
    sections.json       -- SectionIndex
    links.json          -- LinkIndex
  bm25.json             -- BM25 tokenized index (wink-bm25-text-search internal format)
  bm25.meta.json        -- BM25 metadata
  embeddings/
    <namespace>/        -- one dir per (provider, model, dimensions) combination
      vectors.hnsw      -- hnswlib binary index
      meta.bin          -- MessagePack-encoded VectorIndex
```

Source: `src/index/types.ts`, `src/search/bm25-store.ts`, `src/embeddings/vector-store.ts`, `src/embeddings/embedding-namespace.ts`.

### 2.2 JSON Schema (TypeScript interfaces as DDL)

#### DocumentIndex

```typescript
interface DocumentIndex {
  version: number;
  rootPath: string;
  documents: Record<string, DocumentEntry>;  // keyed by document path
}

interface DocumentEntry {
  id: string;
  path: string;
  title: string;
  mtime: number;
  hash: string;
  tokenCount: number;
  sectionCount: number;
}
```

#### SectionIndex

```typescript
interface SectionIndex {
  version: number;
  sections: Record<string, SectionEntry>;   // keyed by section id
  byHeading: Record<string, string[]>;      // heading text -> section ids
  byDocument: Record<string, string[]>;     // document path -> section ids
}

interface SectionEntry {
  id: string;
  documentId: string;
  documentPath: string;
  heading: string;
  level: HeadingLevel;                      // 1..6
  startLine: number;
  endLine: number;
  tokenCount: number;
  hasCode: boolean;
  hasList: boolean;
  hasTable: boolean;
}
```

#### LinkIndex

```typescript
interface LinkIndex {
  version: number;
  forward:  Record<string, string[]>;   // source -> targets
  backward: Record<string, string[]>;   // target -> sources (backlinks)
  broken:   string[];                   // links with no target
}
```

### 2.3 BM25 Storage

The BM25 index is managed by `wink-bm25-text-search` and serialized as `bm25.json` (engine dump) plus `bm25.meta.json` (mdcontext metadata: document count, section map, timestamps). The internal format is opaque to mdcontext — it calls `engine.exportJSON()` / `engine.importJSON()`. The section map (`Map<number, { sectionId, documentPath, heading }>`) bridges the BM25 internal integer IDs back to mdcontext section IDs.

### 2.4 HNSW / Embeddings Storage

Two files per namespace:

- `vectors.hnsw` — binary hnswlib index (native format, not portable across platforms)
- `meta.bin` — MessagePack-encoded `VectorIndex`

```typescript
interface VectorIndex {
  version: number;
  provider: string;                    // 'openai' | 'voyage' | 'ollama' | ...
  providerModel?: string;
  providerBaseURL?: string;
  dimensions: number;
  entries: Record<string, VectorEntry>;  // keyed by internal HNSW integer index
  totalCost: number;
  totalTokens: number;
  createdAt: string;
  updatedAt: string;
  hnswParams?: { m: number; efConstruction: number };
}

interface VectorEntry {
  id: string;
  sectionId: string;
  documentPath: string;
  heading: string;
  embedding: number[];                 // raw float array, NOT stored in meta.bin normally
}
```

Note: raw embedding vectors are stored inside the hnswlib binary, not in `meta.bin`. The `meta.bin` entries map HNSW integer slots to section identifiers; the hnswlib file holds the actual float arrays.

---

## 3. Concept Overlap Analysis

| Concept | attention-matters | mdcontext |
|---|---|---|
| Document | Implicit (source_text on neighborhood) | Explicit: `DocumentEntry` with path, hash, mtime |
| Section / Chunk | `Neighborhood` (3-sentence window) | `SectionEntry` (markdown heading boundary) |
| Vector per chunk | Quaternion seed (4 REALs) + occurrence positions | Float array in hnswlib binary |
| Token/word | `Occurrence` row (word + quaternion position) | Token count integer on SectionEntry |
| Activation/weight | `activation_count` on Occurrence | No analog |
| Temporal context | `Episode` | No analog |
| Index version | `metadata.schema_version` (integer) | `INDEX_VERSION = 1` constant in JSON |
| Storage engine | SQLite (rusqlite) | JSON files + hnswlib binary + MessagePack |
| Migration | Manual ALTER TABLE | Not implemented (flat files, full rewrite) |
| Concurrency model | WAL, multi-reader daemon | Single-process CLI / MCP server, no concurrent writes |
| GC / retention | Full GC pass: evict cold occurrences, VACUUM | Watcher-driven full reindex |

### Overlap is real but shallow

Both systems handle a "chunk of text with an identifier". Both have the concept of a section id that bridges search results back to a source document. That is where the overlap ends.

attention-matters chunks by sentence-window heuristics and encodes semantic position as quaternion geometry. mdcontext chunks by markdown heading hierarchy and encodes semantic position as a float embedding vector. These are different representations of different concepts even though both could be labeled "semantic chunk."

---

## 4. Case For and Against a Shared SQLite Schema

### 4.1 The Case For

If mdcontext were to migrate from flat JSON files to SQLite (a separate question from sharing with attention-matters), the following benefits would apply to mdcontext alone:

- Atomic multi-table writes (documents + sections + links in one transaction) eliminate partial-write corruption that currently requires hash checks.
- Indexed queries: `SELECT * FROM sections WHERE document_path = ?` is O(log n) vs O(n) JSON scan.
- Row-level updates: currently the entire `sections.json` is rewritten on any change; SQLite would support row-level upserts.
- `bm25.json` is an opaque engine dump that loses structure on migration; a `terms` + `postings` table would be portable and inspectable.

None of these benefits require sharing a database with attention-matters.

### 4.2 The Case Against Sharing

**Different runtime languages.** attention-matters is Rust (rusqlite). mdcontext is TypeScript (Node.js, better-sqlite3 or similar). A shared SQLite file between a Rust daemon and a Node process would require careful WAL and busy-timeout coordination. The attention-matters WAL checkpoint configuration (`wal_autocheckpoint = 100`) is tuned for its write-heavy daemon workload; mdcontext's read-heavy, write-infrequent access pattern would fight against it.

**Different owners, different schemas, different velocities.** attention-matters is at schema version 7 and mutates continuously (every conversation turn writes occurrence activation increments). mdcontext's index is write-once-on-index, read-many. Coupling their migration paths means either system's schema change blocks the other.

**Different domain semantics.** A shared `documents` table would require a discriminator column to distinguish am-episodes from mdcontext-documents. This is the classic "one table for everything" antipattern. The schema would become harder to reason about without any query performance benefit.

**Deployment concerns.** attention-matters stores its database at `~/.config/attention-matters/brain.db` (or equivalent per-agent path). mdcontext stores its index at `<root>/.mdcontext/`. These are different locations serving different consumers. Merging them would either require one system to hard-code the other's path or introduce an environment variable indirection layer.

**Existing binary artifact coupling.** mdcontext's hnswlib vectors and MessagePack blobs are already separate from the JSON index. A SQLite migration would not eliminate these binary files — `vectors.hnsw` must remain a native hnswlib binary. Any shared schema would still be a partial picture of mdcontext's storage.

### 4.3 Verdict

No case for a shared SQLite database file. Clear case for mdcontext adopting SQLite independently.

---

## 5. What a Standalone mdcontext SQLite Schema Would Look Like

If mdcontext migrated its JSON indexes to SQLite, this is the natural schema — independent of attention-matters:

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 3000;

-- Schema housekeeping
CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- Rows: ('schema_version', '1'), ('root_path', '/path/to/vault'), ('indexed_at', '<iso8601>')

-- Indexed markdown files
CREATE TABLE IF NOT EXISTS documents (
    id            TEXT PRIMARY KEY,           -- uuid or sha256 prefix
    path          TEXT NOT NULL UNIQUE,       -- relative to root_path
    title         TEXT NOT NULL DEFAULT '',
    mtime         INTEGER NOT NULL,           -- unix ms
    hash          TEXT NOT NULL,              -- SHA-256 of file content
    token_count   INTEGER NOT NULL DEFAULT 0,
    section_count INTEGER NOT NULL DEFAULT 0,
    indexed_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_doc_path  ON documents(path);
CREATE INDEX IF NOT EXISTS idx_doc_mtime ON documents(mtime);

-- Heading-bounded sections within documents
CREATE TABLE IF NOT EXISTS sections (
    id            TEXT PRIMARY KEY,
    document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    document_path TEXT NOT NULL,              -- denormalized for direct join bypass
    heading       TEXT NOT NULL DEFAULT '',
    level         INTEGER NOT NULL DEFAULT 1, -- 1..6
    start_line    INTEGER NOT NULL,
    end_line      INTEGER NOT NULL,
    token_count   INTEGER NOT NULL DEFAULT 0,
    has_code      INTEGER NOT NULL DEFAULT 0,
    has_list      INTEGER NOT NULL DEFAULT 0,
    has_table     INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sec_document  ON sections(document_id);
CREATE INDEX IF NOT EXISTS idx_sec_heading   ON sections(heading);

-- Markdown link graph
CREATE TABLE IF NOT EXISTS links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    target_path TEXT NOT NULL,
    is_broken   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_link_source ON links(source_path);
CREATE INDEX IF NOT EXISTS idx_link_target ON links(target_path);

-- Embedding namespaces (one row per (provider, model, dimensions) triple)
CREATE TABLE IF NOT EXISTS embedding_namespaces (
    namespace       TEXT PRIMARY KEY,          -- generateNamespace() output
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    dimensions      INTEGER NOT NULL,
    vector_count    INTEGER NOT NULL DEFAULT 0,
    total_cost      REAL NOT NULL DEFAULT 0.0,
    total_tokens    INTEGER NOT NULL DEFAULT 0,
    hnsw_m          INTEGER NOT NULL DEFAULT 16,
    hnsw_ef         INTEGER NOT NULL DEFAULT 200,
    is_active       INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Embedding entries: bridge HNSW integer slots to section identifiers
-- The raw float vectors remain in the hnswlib binary file.
CREATE TABLE IF NOT EXISTS embedding_entries (
    hnsw_slot       INTEGER NOT NULL,          -- internal hnswlib index
    namespace       TEXT NOT NULL REFERENCES embedding_namespaces(namespace) ON DELETE CASCADE,
    section_id      TEXT NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    document_path   TEXT NOT NULL,
    heading         TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (namespace, hnsw_slot)
);

CREATE INDEX IF NOT EXISTS idx_emb_section   ON embedding_entries(section_id);
CREATE INDEX IF NOT EXISTS idx_emb_namespace ON embedding_entries(namespace);

-- BM25 term index (replaces opaque wink-bm25 JSON dump)
-- This makes the full-text index transparent and portable.
CREATE TABLE IF NOT EXISTS bm25_terms (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    term    TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS bm25_postings (
    term_id    INTEGER NOT NULL REFERENCES bm25_terms(id) ON DELETE CASCADE,
    section_id TEXT NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    tf         REAL NOT NULL,               -- term frequency (weighted: heading=2x, body=1x)
    PRIMARY KEY (term_id, section_id)
);

-- Document-level term stats for IDF computation
CREATE TABLE IF NOT EXISTS bm25_stats (
    term_id      INTEGER PRIMARY KEY REFERENCES bm25_terms(id) ON DELETE CASCADE,
    doc_freq     INTEGER NOT NULL DEFAULT 0  -- number of sections containing this term
);
```

Note: if the BM25 engine (wink-bm25-text-search) is retained as-is, the `bm25_*` tables would not be used. They represent what a native implementation would look like. The `embedding_entries` table is a direct replacement for the `entries` record in `meta.bin`.

---

## 6. What a Shared Schema Would Look Like (Hypothetical)

If there were a genuine business requirement to merge both systems into one SQLite file, the minimum viable discriminated schema would be:

```sql
-- Shared document table with system discriminator
CREATE TABLE IF NOT EXISTS documents (
    id      TEXT PRIMARY KEY,
    system  TEXT NOT NULL CHECK (system IN ('mdcontext', 'attention-matters')),
    path    TEXT,           -- mdcontext: relative file path; am: NULL
    title   TEXT,
    hash    TEXT,
    mtime   INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Shared sections / neighborhoods
CREATE TABLE IF NOT EXISTS chunks (
    id          TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    system      TEXT NOT NULL CHECK (system IN ('mdcontext', 'attention-matters')),
    -- mdcontext fields
    heading     TEXT,
    level       INTEGER,
    start_line  INTEGER,
    end_line    INTEGER,
    -- attention-matters fields
    seed_w      REAL,
    seed_x      REAL,
    seed_y      REAL,
    seed_z      REAL,
    epoch       INTEGER,
    superseded_by TEXT,
    neighborhood_type TEXT
);
```

This is already a mess. The `chunks` table has eight nullable columns that are only meaningful to one system. A WHERE clause that fails to filter by `system` would return nonsense. Any JOIN across the two systems would be accidental data pollution. This structure has no advantage over two separate databases accessed from a shared connection pool.

---

## 7. Recommendations

### 7.1 Keep databases separate. Always.

The systems have different locations, different runtime languages, different write rates, different WAL tuning requirements, and different schema evolution velocities. There is no operational or architectural benefit to merging them.

### 7.2 mdcontext should migrate to SQLite independently

The current flat-JSON index is the primary source of performance ceiling for mdcontext. The three JSON files (`documents.json`, `sections.json`, `links.json`) are entirely rewritten on every index update. At scale (10,000+ documents), this becomes a multi-second blocking write. SQLite with WAL and row-level upserts would:

- Reduce incremental reindex from O(total docs) to O(changed docs)
- Enable `mtime`-based staleness checks with an indexed query
- Enable efficient backlink queries via the `links` table index
- Eliminate the corruption window between partial JSON writes

The `embedding_entries` table in Section 5 would replace the `entries` record in `meta.bin`, making the HNSW slot-to-section mapping queryable without loading the full MessagePack blob into memory.

### 7.3 Shared schema DDL library: worth considering

If both projects agree on a common `schema_version` table pattern and a common `metadata` key/value pattern (both already use this independently), a shared Rust or TypeScript library that encodes those conventions would reduce duplication. This is a code-sharing concern, not a database-sharing concern.

### 7.4 Integration point if needed: message bus, not shared storage

If attention-matters and mdcontext need to share data (for example, am-server could benefit from knowing which markdown files are indexed by mdcontext, or mdcontext search results could trigger am memory recall), the correct integration point is `helioy-bus`, not a shared SQLite file. Each system owns its storage; the bus carries events between them.

---

## Appendix: File Locations

| Artifact | Path |
|---|---|
| attention-matters schema | `crates/am-store/src/schema.rs` |
| attention-matters store | `crates/am-store/src/store.rs` |
| mdcontext index types | `src/index/types.ts` |
| mdcontext storage ops | `src/index/storage.ts` |
| mdcontext vector store | `src/embeddings/vector-store.ts` |
| mdcontext BM25 store | `src/search/bm25-store.ts` |
| mdcontext namespace mgmt | `src/embeddings/embedding-namespace.ts` |
