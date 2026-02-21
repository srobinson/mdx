---
title: "context-matters: Schema and Storage Layer Specification"
type: project
tags: [context-matters, schema, sqlite, rust, sqlx, helioy]
status: draft
created: 2026-03-14
updated: 2026-03-14
---

## 1. Overview

This document specifies the complete schema and storage layer for **context-matters**, a Rust MCP server providing hierarchical, scoped context storage for the helioy ecosystem. The storage backend is SQLite with FTS5 full-text search, accessed through sqlx.

### 1.1 Design Constraints (decided, not revisited)

- SQLite + FTS5 for v1. No vector search. No Tantivy.
- Single `entries` table with materialized scope paths.
- Scope vocabulary: global, project, repo, session.
- Soft-delete via `superseded_by`.
- JSONB `meta` column for flexible metadata.
- sqlx for database access.
- WAL mode with aggressive pragmas.

### 1.2 Database File Location

The SQLite database lives at:

```
~/.context-matters/cm.db
```

The directory is created on first run if it does not exist. The WAL and SHM files (`cm.db-wal`, `cm.db-shm`) are co-located automatically by SQLite.

## 2. SQLite Pragma Configuration

Applied on every connection open, before any queries execute.

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA wal_autocheckpoint = 1000;
PRAGMA cache_size = -64000;
PRAGMA mmap_size = 268435456;
PRAGMA temp_store = MEMORY;
PRAGMA foreign_keys = ON;
PRAGMA journal_size_limit = 67108864;
```

| Pragma | Value | Rationale |
|--------|-------|-----------|
| `journal_mode` | `WAL` | Concurrent reads during writes. Required for multi-agent access. |
| `synchronous` | `NORMAL` | Safe with WAL. Avoids `FULL` fsync overhead. |
| `busy_timeout` | `5000` | 5s retry on lock contention before returning SQLITE_BUSY. |
| `wal_autocheckpoint` | `1000` | Checkpoint every 1000 pages. Prevents unbounded WAL growth. |
| `cache_size` | `-64000` | 64MB page cache (negative = KiB). |
| `mmap_size` | `268435456` | 256MB memory-mapped I/O. |
| `temp_store` | `MEMORY` | Temp tables and indexes in memory. |
| `foreign_keys` | `ON` | Enforce FK constraints. SQLite disables these by default. |
| `journal_size_limit` | `67108864` | 64MB cap on WAL file size. Prevents unbounded WAL growth under sustained write load. Multiple production reports flag uncapped WAL as a real issue. |

## 3. SQL DDL

### 3.1 Scopes Table

Defines the valid scope hierarchy. Scopes must be created top-down: creating a scope with a `parent_path` that does not exist in the `scopes` table will fail with a foreign key error.

```sql
CREATE TABLE scopes (
    path        TEXT PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('global', 'project', 'repo', 'session')),
    label       TEXT NOT NULL,
    parent_path TEXT,
    meta        TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (parent_path) REFERENCES scopes(path) ON DELETE RESTRICT ON UPDATE RESTRICT
);
```

The root scope `global` has `parent_path = NULL`. Scope paths are immutable after creation. The `ON DELETE RESTRICT` constraint prevents removing a scope that has children or entries referencing it.

### 3.2 Entries Table

The primary context store. Each entry belongs to exactly one scope.

The table retains SQLite's implicit integer `rowid` (this is not a `WITHOUT ROWID` table). FTS5 content-sync triggers require `rowid` to function.

```sql
CREATE TABLE entries (
    id              TEXT PRIMARY KEY,
    scope_path      TEXT NOT NULL,
    kind            TEXT NOT NULL,
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    meta            TEXT,
    created_by      TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    superseded_by   TEXT,
    FOREIGN KEY (scope_path) REFERENCES scopes(path) ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (superseded_by) REFERENCES entries(id) ON DELETE SET NULL ON UPDATE CASCADE
);
```

- `id`: UUID v7 as lowercase hex string (sortable by creation time).
- `scope_path`: FK to `scopes.path`. `ON DELETE RESTRICT` prevents orphaning entries.
- `kind`: one of the entry kind enum values (Section 5).
- `title`: short summary, used in search results and progressive disclosure.
- `body`: markdown content.
- `content_hash`: BLAKE3 hex digest for deduplication (Section 6).
- `meta`: JSONB for flexible metadata (tags, confidence, source, expiry).
- `created_by`: attribution string (Section 5.2).
- `superseded_by`: FK to replacement entry. `ON DELETE SET NULL` means if the superseding entry is removed, the original becomes active again.
- `updated_at`: maintained by trigger (Section 3.6). The application layer does not set this field manually.

### 3.3 Indexes

```sql
CREATE INDEX idx_entries_scope ON entries(scope_path);
CREATE INDEX idx_entries_kind ON entries(kind);
CREATE INDEX idx_entries_scope_kind ON entries(scope_path, kind);
CREATE INDEX idx_entries_updated ON entries(updated_at);
CREATE INDEX idx_entries_content_hash ON entries(content_hash);
CREATE INDEX idx_entries_superseded ON entries(superseded_by);
```

### 3.4 Entry Relations Table

Cross-references between entries. Supports relations across scope boundaries.

```sql
CREATE TABLE entry_relations (
    source_id   TEXT NOT NULL,
    target_id   TEXT NOT NULL,
    relation    TEXT NOT NULL CHECK (relation IN (
        'supersedes', 'relates_to', 'contradicts', 'elaborates', 'depends_on'
    )),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (source_id, target_id, relation),
    FOREIGN KEY (source_id) REFERENCES entries(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (target_id) REFERENCES entries(id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX idx_relations_target ON entry_relations(target_id);
```

`ON DELETE CASCADE` on both FKs: when an entry is removed, all its relations (as source or target) are removed with it. The `idx_relations_target` index supports reverse relation lookups (finding all entries that reference a given target).

### 3.5 FTS5 Virtual Table

```sql
CREATE VIRTUAL TABLE entries_fts USING fts5(
    title, body,
    content='entries',
    content_rowid='rowid',
    tokenize='porter unicode61'
);
```

FTS5 content-sync triggers keep the index in lockstep with the `entries` table:

```sql
CREATE TRIGGER entries_fts_insert AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, title, body)
    VALUES (new.rowid, new.title, new.body);
END;

CREATE TRIGGER entries_fts_delete AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, title, body)
    VALUES ('delete', old.rowid, old.title, old.body);
END;

CREATE TRIGGER entries_fts_update AFTER UPDATE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, title, body)
    VALUES ('delete', old.rowid, old.title, old.body);
    INSERT INTO entries_fts(rowid, title, body)
    VALUES (new.rowid, new.title, new.body);
END;
```

### 3.6 Timestamp Trigger

The `updated_at` column is maintained automatically. This follows the same trigger-based pattern as the FTS sync triggers, keeping timestamp management out of application code.

```sql
CREATE TRIGGER entries_updated_at AFTER UPDATE ON entries BEGIN
    UPDATE entries SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE id = new.id;
END;
```

This trigger relies on SQLite's default `recursive_triggers = OFF`. Do not enable recursive triggers.

## 4. Scope Path Format

### 4.1 Syntax

Scope paths use `/` as the hierarchy separator and `:` to bind a scope kind to its identifier:

```
global
global/project:<project-id>
global/project:<project-id>/repo:<repo-id>
global/project:<project-id>/repo:<repo-id>/session:<session-id>
```

Identifiers are lowercase alphanumeric with hyphens. No spaces, no uppercase, no special characters beyond `-`.

### 4.2 Validation Rules

1. Every path starts with `global`.
2. Each segment after `global` has the form `<kind>:<identifier>`.
3. Kinds must appear in hierarchical order: global < project < repo < session. Each kind may appear at most once. Intermediate levels may be omitted.
4. Identifiers match the regex `[a-z0-9][a-z0-9-]*[a-z0-9]` (min 2 chars) or `[a-z0-9]` (single char).
5. Maximum path length: 256 bytes.

### 4.3 Examples

| Scope | Path |
|-------|------|
| Everything | `global` |
| Helioy project | `global/project:helioy` |
| nancyr repo within helioy | `global/project:helioy/repo:nancyr` |
| A coding session | `global/project:helioy/repo:nancyr/session:abc123` |
| Project-level session (no repo) | `global/project:helioy/session:deploy-review` |

### 4.4 Rust Type

```rust
/// A validated, immutable scope path.
///
/// Invariants enforced at construction:
/// - Starts with "global"
/// - Each segment after global is `kind:identifier`
/// - Kinds appear in hierarchical order (global < project < repo < session)
/// - Identifiers match `[a-z0-9][a-z0-9-]*[a-z0-9]`
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ScopePath(String);

impl ScopePath {
    /// Parse and validate a scope path string.
    pub fn parse(input: &str) -> Result<Self, ScopePathError>;

    /// Return the raw string.
    pub fn as_str(&self) -> &str;

    /// Return all ancestor paths, from most specific to least.
    /// Example: "global/project:helioy/repo:nancyr" returns
    /// ["global/project:helioy/repo:nancyr", "global/project:helioy", "global"]
    pub fn ancestors(&self) -> Vec<&str>;

    /// Return the scope kind of the deepest segment.
    pub fn leaf_kind(&self) -> ScopeKind;
}
```

## 5. Entry Kind Enum

### 5.1 Kinds

| Kind | Description |
|------|-------------|
| `fact` | A verified piece of information. "nancyr uses tokio 1.x." |
| `decision` | An architectural or design choice with rationale. "We chose sqlx over diesel because..." |
| `preference` | A user or project preference. "Stuart prefers explicit error types over anyhow in libraries." |
| `lesson` | Something learned from experience. "FTS5 triggers must reference rowid, not the TEXT primary key." |
| `reference` | A pointer to external material. URL, doc path, or citation. |
| `feedback` | A user correction or clarification. Highest-priority recall signal. |
| `pattern` | A recurring code or process pattern worth remembering. |
| `observation` | A general-purpose note that does not fit other categories. |

### 5.2 Created-By Attribution

The `created_by` field uses the format `<source-type>:<identifier>`:

- `human:stuart`
- `agent:claude-code`
- `agent:nancyr`
- `system:consolidation` (for entries created by periodic cleanup)

### 5.3 Rust Types

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, sqlx::Type)]
#[sqlx(type_name = "TEXT", rename_all = "snake_case")]
pub enum EntryKind {
    Fact,
    Decision,
    Preference,
    Lesson,
    Reference,
    Feedback,
    Pattern,
    Observation,
}

/// Structured metadata stored in the JSONB `meta` column.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntryMeta {
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tags: Vec<String>,

    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub confidence: Option<Confidence>,

    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub source: Option<String>,

    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub expires_at: Option<String>,

    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub priority: Option<i32>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Confidence {
    High,
    Medium,
    Low,
}
```

## 6. Content Hash Deduplication

### 6.1 Algorithm

BLAKE3 over the concatenation of three fields, separated by null bytes:

```
BLAKE3(scope_path + \0 + kind + \0 + body)
```

The `title` is excluded. Two entries with the same scope, kind, and body but different titles are considered duplicates (the title is a display label, not semantic content).

### 6.2 Behavior

On insert, compute the content hash and query:

```sql
SELECT id FROM entries
WHERE content_hash = ?
AND superseded_by IS NULL
LIMIT 1;
```

If a match exists, the insert is rejected with a `DuplicateContent` error. The caller decides whether to update the existing entry or skip.

### 6.3 Hash Storage

The `content_hash` column stores the lowercase hex-encoded BLAKE3 digest (64 characters). Indexed via `idx_entries_content_hash`.

### 6.4 Superseded Entries and Deduplication

A superseded entry's content hash is no longer considered for deduplication. This allows re-inserting content that matches a previously superseded entry. The dedup query filters on `superseded_by IS NULL` to achieve this.

### 6.5 Entry Expiry

The `EntryMeta.expires_at` field is stored but not enforced by the storage layer. Expiry semantics (whether expired entries are excluded from results, how cleanup works) are defined in the MCP tool layer specification. The storage layer treats `expires_at` as opaque metadata.

## 7. Concurrency Model

### 7.1 Architecture

Two separate connection pools: one for writes (single connection), one for reads (multiple connections).

- **Write pool**: 1 connection. SQLite permits one writer at a time. Serializing writes through a single connection avoids SQLITE_BUSY on the write path entirely.
- **Read pool**: up to 4 connections. WAL mode allows concurrent reads that do not block the writer.

### 7.2 sqlx Pool Configuration

```rust
use sqlx::sqlite::{SqliteConnectOptions, SqlitePoolOptions, SqliteJournalMode, SqliteSynchronous};

fn base_opts(db_path: &str) -> SqliteConnectOptions {
    db_path.parse::<SqliteConnectOptions>()
        .expect("valid db path")
        .journal_mode(SqliteJournalMode::Wal)
        .synchronous(SqliteSynchronous::Normal)
        .busy_timeout(std::time::Duration::from_secs(5))
        .pragma("wal_autocheckpoint", "1000")
        .pragma("cache_size", "-64000")
        .pragma("mmap_size", "268435456")
        .pragma("temp_store", "memory")
        .pragma("journal_size_limit", "67108864")
        .foreign_keys(true)
        .create_if_missing(true)
}

/// Build the write and read pools.
///
/// Clone ordering matters: the write pool clones `base_opts` first,
/// then the read pool clones with `read_only(true)`. This ensures
/// the write pool retains full privileges.
pub async fn create_pools(db_path: &str) -> Result<(SqlitePool, SqlitePool)> {
    let opts = base_opts(db_path);

    let write_pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect_with(opts.clone())
        .await?;

    let read_pool = SqlitePoolOptions::new()
        .max_connections(4)
        .connect_with(opts.read_only(true))
        .await?;

    Ok((write_pool, read_pool))
}
```

## 8. Migration Strategy

### 8.1 Framework

sqlx's built-in migration system with embedded migrations compiled into the binary.

```rust
sqlx::migrate!("./migrations").run(&write_pool).await?;
```

### 8.2 Directory Structure

```
migrations/
  001_initial_schema.sql
  002_fts5_setup.sql
  003_triggers.sql
```

Migration filenames use sequential numbering (001, 002, ...), not timestamps. Sequential numbers are deterministic across environments and easier to reason about during development. Each migration is a single `.sql` file. sqlx tracks applied migrations and skips already-executed files.

### 8.3 Initial Migrations

**`001_initial_schema.sql`**: Creates `scopes`, `entries`, `entry_relations` tables with all indexes and FK constraints.

**`002_fts5_setup.sql`**: Creates `entries_fts` virtual table.

**`003_triggers.sql`**: Creates FTS sync triggers (`entries_fts_insert`, `entries_fts_delete`, `entries_fts_update`) and the `entries_updated_at` trigger.

### 8.4 Embedded vs Runtime

Migrations are embedded at compile time via `sqlx::migrate!()`. This eliminates the need to ship migration files alongside the binary and guarantees the migration set matches the compiled code.

## 9. Acceptance Criteria

### 9.1 Schema Verification

1. All tables (`scopes`, `entries`, `entry_relations`, `entries_fts`) exist after migration.
2. All indexes exist and are used by the query planner (verified via `EXPLAIN QUERY PLAN`).
3. `PRAGMA foreign_keys` returns `1` on every connection.
4. `PRAGMA journal_mode` returns `wal` on every connection.

### 9.2 Scope Path Validation

5. `ScopePath::parse("global")` succeeds.
5b. `ScopePath::parse("global/project:helioy/session:deploy-review")` succeeds (skipped hierarchy level).
6. `ScopePath::parse("global/project:helioy/repo:nancyr")` succeeds.
7. `ScopePath::parse("project:helioy")` fails (missing `global` root).
8. `ScopePath::parse("global/workspace:foo")` fails (invalid kind).
9. `ScopePath::parse("")` fails (empty string).
10. `ancestors()` for `global/project:helioy/repo:nancyr` returns `["global/project:helioy/repo:nancyr", "global/project:helioy", "global"]`.

### 9.3 Entry CRUD

11. Inserting an entry with a valid scope path succeeds and returns the entry with a generated `id`.
12. Inserting an entry with an invalid scope path (no matching `scopes` row) fails with a FK error.
13. Querying entries by scope path returns only entries at that exact scope.
14. Querying with scope resolution (ancestors) returns entries from the target scope and all ancestor scopes, ordered most-specific-first.
15. Superseding an entry sets `superseded_by` on the old entry and creates the new entry.
16. Querying active entries excludes those with non-null `superseded_by`.

### 9.4 Deduplication

17. Inserting two entries with identical `scope_path + kind + body` (same content hash) fails on the second insert.
18. After superseding an entry, inserting a new entry with the same content hash as the superseded entry succeeds.

### 9.5 FTS5

19. Inserting an entry and searching for a word in its title via `entries_fts MATCH` returns the entry.
20. Updating an entry's body and searching for the new content returns the entry; searching for the old content does not.
21. Deleting an entry removes it from FTS results.

### 9.6 Concurrency

22. A read query executes while a write transaction is in progress (WAL concurrency).
23. Two concurrent write attempts serialize correctly (one waits on busy_timeout, then succeeds).

### 9.7 Triggers

24. Updating an entry's `body` automatically updates `updated_at` to the current timestamp (verified by comparing before/after values).
25. The `updated_at` trigger fires independently of FTS triggers (both execute on UPDATE).

### 9.8 FK Cascades

26. Attempting to delete a scope that has entries referencing it fails with `FOREIGN KEY constraint failed`.
27. Deleting an entry that is referenced as `superseded_by` by another entry sets that other entry's `superseded_by` to NULL.
28. Deleting an entry removes all rows in `entry_relations` where it appears as `source_id` or `target_id`.
