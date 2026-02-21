---
title: Schema Design Patterns for Multi-Scope Context/Knowledge Stores
type: research
tags: [schema-design, sqlite, rust, hierarchical-data, context-engineering, agent-memory, knowledge-store]
summary: Comprehensive analysis of schema patterns for a single-SQLite context store with hierarchical scoping (global/project/repo/session), covering hierarchy models, naming, SQLite features, Rust adapter patterns, and prior art from shipping products.
status: active
source: deep-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Executive Summary

A materialized-path approach with a scope column provides the best balance of query simplicity, write performance, and flexibility for a hierarchical context store in SQLite. The schema should treat every piece of context as a typed entry (fact, decision, preference, lesson, etc.) tagged with a scope path like `global`, `global/project:helioy`, or `global/project:helioy/repo:nancyr/session:abc123`. SQLite's recursive CTEs, FTS5 for full-text search, and JSONB columns for flexible metadata make a single-file store viable for both human and agent access. In Rust, sqlx with a trait-based DAL (not a full ORM) provides the cleanest path to multi-backend support.

## 1. Hierarchical Scoping in SQL

### The Four Classical Models

| Model | Read Perf | Write Perf | SQLite Fit | Best For |
|-------|-----------|------------|------------|----------|
| **Adjacency List** (parent_id FK) | Slow for deep trees without CTE | Fast inserts | Good with recursive CTEs | Frequently changing trees |
| **Closure Table** (ancestor/descendant pairs) | Excellent reads | Complex writes (N rows per insert) | Works but table grows O(n^2) | Read-heavy, deep hierarchies |
| **Materialized Path** (path string column) | Fast with LIKE/prefix queries | Fast (single row write) | Excellent (string ops + indexes) | Fixed-depth hierarchies, scope resolution |
| **Nested Sets** (lft/rgt bounds) | Fast subtree reads | Expensive writes (rebalancing) | Poor for write workloads | Rarely-changing trees |

### Recommendation: Materialized Path

For a context store with a **fixed, shallow hierarchy** (global > project > repo > session = 4 levels max), materialized path is optimal:

- **Path format**: `global/project:helioy/repo:nancyr` using `/` as separator and `:` for key-value pairs
- **Ancestor query**: `WHERE scope_path = 'global' OR 'global/project:helioy/repo:nancyr' LIKE scope_path || '/%'`
- **Descendant query**: `WHERE scope_path LIKE 'global/project:helioy/%'`
- **Exact scope**: `WHERE scope_path = 'global/project:helioy/repo:nancyr'`
- **Index**: `CREATE INDEX idx_entries_scope ON entries(scope_path)`

The adjacency list + recursive CTE approach is viable but adds query complexity for what amounts to a 4-level enum. Closure tables are overkill for a fixed hierarchy. Materialized paths give you prefix-matching on a single indexed TEXT column.

PostgreSQL has `ltree` for native materialized path support with GiST indexes. SQLite lacks this, but LIKE-based prefix queries on an indexed TEXT column perform well for the expected cardinality (thousands to low millions of entries).

### Scope Resolution Pattern

When an agent asks "give me context for this repo," the query should walk UP the hierarchy, collecting entries from the repo scope, its parent project scope, and the global scope:

```sql
-- Collect all context visible at repo level (walks up the tree)
SELECT * FROM entries
WHERE scope_path IN ('global', 'global/project:helioy', 'global/project:helioy/repo:nancyr')
ORDER BY
  CASE scope_path
    WHEN 'global/project:helioy/repo:nancyr' THEN 0  -- most specific first
    WHEN 'global/project:helioy' THEN 1
    WHEN 'global' THEN 2
  END,
  updated_at DESC;
```

For dynamic depth, use a recursive CTE to decompose the path:

```sql
WITH RECURSIVE ancestors(path, depth) AS (
  VALUES ('global/project:helioy/repo:nancyr', 0)
  UNION ALL
  SELECT
    SUBSTR(path, 1, INSTR(RTRIM(path, REPLACE(path, '/', '')), '/') - 1),
    depth + 1
  FROM ancestors
  WHERE path LIKE '%/%'
)
SELECT e.* FROM entries e
JOIN ancestors a ON e.scope_path = a.path
ORDER BY a.depth ASC, e.updated_at DESC;
```

## 2. Schema Design: Concrete Proposal

### Core Tables

```sql
-- The primary context store
CREATE TABLE entries (
  id          TEXT PRIMARY KEY,  -- UUID as hex string (16 bytes as BLOB if perf-critical)
  scope_path  TEXT NOT NULL,     -- 'global/project:helioy/repo:nancyr'
  kind        TEXT NOT NULL,     -- 'fact', 'decision', 'preference', 'lesson', 'reference', 'feedback'
  title       TEXT NOT NULL,
  body        TEXT NOT NULL,     -- markdown content
  meta        TEXT,              -- JSONB for flexible metadata (tags, confidence, source, etc.)
  created_by  TEXT NOT NULL,     -- 'human:stuart' or 'agent:claude-code' or 'agent:nancyr'
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  superseded_by TEXT,            -- soft-delete: points to replacement entry ID
  FOREIGN KEY (superseded_by) REFERENCES entries(id)
);

CREATE INDEX idx_entries_scope ON entries(scope_path);
CREATE INDEX idx_entries_kind ON entries(kind);
CREATE INDEX idx_entries_scope_kind ON entries(scope_path, kind);
CREATE INDEX idx_entries_updated ON entries(updated_at);

-- Full-text search
CREATE VIRTUAL TABLE entries_fts USING fts5(
  title, body,
  content='entries',
  content_rowid='rowid',
  tokenize='porter unicode61'
);

-- FTS sync triggers
CREATE TRIGGER entries_ai AFTER INSERT ON entries BEGIN
  INSERT INTO entries_fts(rowid, title, body) VALUES (new.rowid, new.title, new.body);
END;
CREATE TRIGGER entries_ad AFTER DELETE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, title, body) VALUES('delete', old.rowid, old.title, old.body);
END;
CREATE TRIGGER entries_au AFTER UPDATE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, title, body) VALUES('delete', old.rowid, old.title, old.body);
  INSERT INTO entries_fts(rowid, title, body) VALUES (new.rowid, new.title, new.body);
END;

-- Scope definitions (optional, for validation and metadata)
CREATE TABLE scopes (
  path        TEXT PRIMARY KEY,  -- 'global/project:helioy'
  kind        TEXT NOT NULL,     -- 'global', 'project', 'repo', 'session'
  label       TEXT NOT NULL,     -- human-readable: 'Helioy', 'nancyr', etc.
  parent_path TEXT,              -- FK to parent scope
  meta        TEXT,              -- JSONB: description, owner, etc.
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY (parent_path) REFERENCES scopes(path)
);

-- Relations between entries (optional, for cross-referencing)
CREATE TABLE entry_relations (
  source_id   TEXT NOT NULL,
  target_id   TEXT NOT NULL,
  relation    TEXT NOT NULL,     -- 'supersedes', 'relates_to', 'contradicts', 'elaborates'
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  PRIMARY KEY (source_id, target_id, relation),
  FOREIGN KEY (source_id) REFERENCES entries(id),
  FOREIGN KEY (target_id) REFERENCES entries(id)
);
```

### Design Rationale

**Why a single `entries` table instead of separate tables per scope level?**
Agent Recall, hmem, and Engram all converge on a single primary table with scope/namespace columns rather than table-per-scope. This avoids UNION queries, simplifies migrations, and keeps the query interface uniform.

**Why TEXT for dates instead of INTEGER epoch?**
ISO 8601 strings are human-readable in direct DB inspection, sort correctly as strings, and SQLite's date functions work on both. The performance difference is negligible at the expected scale.

**Why JSONB `meta` column?**
Following the Notion and Obsidian Dataview pattern: structured core columns for queryable dimensions (scope, kind, timestamps), flexible JSON for everything else (tags, confidence levels, source URLs, custom fields). SQLite 3.45+ supports JSONB for efficient binary storage while still allowing `json_extract()` queries.

**Why `superseded_by` instead of DELETE?**
Context engineering literature (OpenAI, Redis, Google) consistently recommends append-only or soft-delete patterns for agent memory. Hard deletes lose provenance. Agent Recall uses "bitemporal history" for the same reason.

### Meta Column Schema Convention

```json
{
  "tags": ["architecture", "decision"],
  "confidence": "high",
  "source": "https://github.com/issue/123",
  "expires_at": "2026-06-01T00:00:00Z",
  "priority": 1
}
```

Query example:
```sql
SELECT * FROM entries
WHERE scope_path LIKE 'global/project:helioy%'
AND json_extract(meta, '$.confidence') = 'high'
AND json_extract(meta, '$.tags') LIKE '%architecture%';
```

## 3. Vocabulary and Taxonomy

### What Existing Tools Use

| Tool | Top Level | Mid Level | Work Level | Temporal |
|------|-----------|-----------|------------|----------|
| **Linear** | Workspace | Team | Issue | Cycle/Sprint |
| **Notion** | Workspace | Page (nested) | Block | - |
| **VS Code** | Workspace | Folder | File | - |
| **GitHub** | Organization | Repository | Issue/PR | - |
| **Terraform** | Organization | Workspace | Resource | - |
| **Eclipse/Nx** | Workspace | Project | File/Scope | - |

### Emerging Agent Memory Vocabulary

| Tool | Scope Terms | Notes |
|------|------------|-------|
| **hmem** | Agent (file-level isolation) | No multi-scope within a single agent |
| **Agent Recall** | Organization > Project > Entity | Scope chains with inheritance |
| **Engram** | User > Space > Memory | API key scoping + space partitioning |
| **OpenContext** | Global library (flat) | No hierarchy within the store |
| **Claude Code** | Global > Project > Session | Three tiers via CLAUDE.md + .claude/ |
| **Amazon Bedrock AgentCore** | Namespace (hierarchical paths) | Filesystem-like path scoping |

### Recommended Vocabulary

For this system, use terms that match the mental model of developers who work across multiple projects:

| Scope Level | Term | Rationale |
|-------------|------|-----------|
| 0 | **global** | Universal across all projects. Matches Claude Code, Terraform, CSS. |
| 1 | **project** | A logical grouping of related repos/workspaces. Matches Linear, Notion, Nx. |
| 2 | **repo** | A single codebase or workspace. Matches GitHub's primary unit. "Workspace" is overloaded (VS Code, Notion, Linear all mean different things). |
| 3 | **session** | A temporal context (conversation, task, sprint). Naturally ephemeral. |

Avoid "workspace" as a scope level. It means too many different things across tools. "Repo" is unambiguous and maps directly to a filesystem path or Git remote.

Avoid "namespace." It is a mechanism (how scoping works), not a scope level (what level of the hierarchy). Use it internally in documentation about the system, not as user-facing vocabulary.

## 4. SQLite-Specific Considerations

### WAL Mode (Write-Ahead Logging)

Required for concurrent access from multiple agents. Configuration:

```sql
PRAGMA journal_mode = WAL;           -- enables concurrent reads during writes
PRAGMA synchronous = NORMAL;         -- safe with WAL, better performance than FULL
PRAGMA busy_timeout = 5000;          -- 5s retry on lock contention
PRAGMA wal_autocheckpoint = 1000;    -- checkpoint every 1000 pages
PRAGMA cache_size = -64000;          -- 64MB page cache
PRAGMA mmap_size = 268435456;        -- 256MB memory-mapped I/O
PRAGMA temp_store = MEMORY;          -- temp tables in memory
```

**Concurrency limits**: SQLite allows one writer at a time. With WAL, readers do not block the writer and the writer does not block readers. For multiple agents writing simultaneously, expect lock contention above 3-5 concurrent writers (benchmarked at 15k inserts/s with 3 writers, degrading to 9.7k at 100 writers).

**Mitigation**: Use a write-through queue or serialize writes through a single connection for the write path, while allowing multiple read connections. This matches the typical agent pattern where reads are far more frequent than writes.

### FTS5

The `porter unicode61` tokenizer handles English stemming and Unicode normalization. For multi-language support, consider `unicode61` alone.

FTS5 performance at scale: HN reports confirm production deployments handling millions of documents with sub-millisecond search latency. ZeroClaw benchmarks show 0.3ms FTS5 search on Raspberry Pi Zero 2 W.

Combined FTS5 + scope filtering:

```sql
SELECT e.* FROM entries e
JOIN entries_fts f ON e.rowid = f.rowid
WHERE entries_fts MATCH 'architecture decision'
AND e.scope_path LIKE 'global/project:helioy%'
ORDER BY f.rank;
```

### JSONB

SQLite 3.45+ (January 2024) stores JSON in binary format as BLOB, reducing parse overhead for `json_extract()`. The `serde-sqlite-jsonb` Rust crate provides Serde integration for direct serialization/deserialization.

Use `STRICT` tables (SQLite 3.37+) if you want to enforce column types, though this prevents the TEXT-as-any-type flexibility that SQLite traditionally offers.

### Size Considerations

A context store with 100,000 entries averaging 500 bytes each = ~50MB. With FTS5 index, roughly double that. Well within single-file SQLite limits (281 TB theoretical, practical limit around 1TB before tooling struggles).

## 5. Adapter Patterns for Rust

### Recommended: sqlx with Trait-Based DAL

sqlx provides the best balance for this use case:
- Async-native (agents are async)
- Compile-time SQL verification via `query!` macro
- Supports SQLite, PostgreSQL, MySQL, MSSQL
- No ORM overhead; you write SQL directly
- Migration support built-in

**Trait-based abstraction pattern** (from Colliery.io's dual-backend guide):

```rust
// Core trait defining storage operations
#[async_trait]
pub trait ContextStore: Send + Sync {
    async fn get_entry(&self, id: &str) -> Result<Entry>;
    async fn list_entries(&self, scope: &ScopePath, filter: &EntryFilter) -> Result<Vec<Entry>>;
    async fn resolve_context(&self, scope: &ScopePath) -> Result<Vec<Entry>>; // walks up hierarchy
    async fn upsert_entry(&self, entry: &NewEntry) -> Result<Entry>;
    async fn search(&self, query: &str, scope: Option<&ScopePath>) -> Result<Vec<Entry>>;
    async fn supersede(&self, old_id: &str, new_entry: &NewEntry) -> Result<Entry>;
}

// SQLite implementation
pub struct SqliteContextStore {
    pool: SqlitePool,
}

#[async_trait]
impl ContextStore for SqliteContextStore {
    async fn resolve_context(&self, scope: &ScopePath) -> Result<Vec<Entry>> {
        let ancestors = scope.ancestors(); // ["global/project:x/repo:y", "global/project:x", "global"]
        sqlx::query_as!(Entry,
            "SELECT * FROM entries WHERE scope_path IN (?, ?, ?) AND superseded_by IS NULL
             ORDER BY CASE scope_path WHEN ? THEN 0 WHEN ? THEN 1 WHEN ? THEN 2 END",
            ancestors[0], ancestors[1], ancestors[2],
            ancestors[0], ancestors[1], ancestors[2]
        )
        .fetch_all(&self.pool)
        .await
    }
}

// Future PostgreSQL implementation
pub struct PgContextStore {
    pool: PgPool,
}
```

**Feature flag selection** (compile-time backend choice):

```toml
[features]
default = ["sqlite"]
sqlite = ["sqlx/sqlite"]
postgres = ["sqlx/postgres"]
```

### Why Not Diesel or SeaORM

- **Diesel**: Synchronous by default. The `diesel-async` crate exists but is an afterthought. Diesel's type-level SQL DSL is powerful but adds significant compile-time complexity. Its compile-time schema validation requires a running database, which conflicts with the "single SQLite file" portability goal during CI.
- **SeaORM**: Built on sqlx but adds ActiveRecord-style ORM abstractions that are unnecessary for a domain-specific store with known query patterns. The additional abstraction layer means more dependencies and slower compile times without proportional benefit.
- **rusqlite**: Synchronous only. Optimal for embedded single-threaded use but requires `spawn_blocking` wrappers for async contexts. Consider it if async is not a hard requirement.

### libSQL/Turso Migration Path

libSQL is a fork of SQLite that adds native vector search (`FLOAT32` columns with ANN indexing), async I/O, and multi-writer support. It maintains 100% backward compatibility with the SQLite file format.

Migration path:
1. Start with standard SQLite via sqlx
2. If vector search becomes needed, swap to libsql-client (Rust SDK available)
3. If distributed/replicated storage becomes needed, move to Turso (hosted libSQL)

The `libsql` Rust crate provides a compatible API surface, so the trait-based DAL insulates calling code from the swap.

## 6. Prior Art: What Ships in Production

### Notion's Block Model
- Everything is a block with a uniform schema
- Parent pointer (adjacency list) for hierarchy
- Permission walks UP the tree via recursive traversal
- Sharded PostgreSQL (96 servers, workspace-ID-based sharding)
- 200+ billion block rows
- Key lesson: uniform schema + parent pointer works at massive scale, but permission traversal is expensive

### Linear's Workspace Model
- Workspace > Team > Issue (3 levels, fixed)
- Team ID forms issue identifier prefix (`ENG-123`)
- Projects span teams (cross-cutting concern, not a scope level)
- GraphQL API with strong typing
- Key lesson: keeping the hierarchy shallow (3 levels) keeps queries simple

### Obsidian Dataview
- Three metadata sources: YAML frontmatter, inline `Key:: Value`, implicit (tags, dates)
- Indexes metadata at vault startup, queries against the index
- Key lesson: support multiple ways to attach metadata to the same entity

### Agent Recall (SQLite knowledge graph for AI agents)
- Scoped entities with organization > project inheritance
- Bitemporal history (never deletes, archives)
- Keyword search over structured scoped facts (not vector/semantic)
- 9 MCP tools for proactive fact capture
- Key lesson: structured scoped facts outperform fuzzy semantic recall for deterministic agent behavior

### hmem (hierarchical memory for coding agents)
- 5-depth hierarchy within a single agent's memory
- Dot-path addressing (`L0003.2.1`)
- Lazy loading: L1 overview costs ~20 tokens vs 3-8k for flat file
- Auto-timestamped with time-range queries
- Key lesson: hierarchical retrieval with lazy loading reduces token consumption by 100-400x

### Engram (persistent memory with vector search)
- Migrated from SQLite to libsql for native vector search
- FLOAT32(384) embeddings with ANN indexing
- Hybrid retrieval: static facts + semantic matches + high-importance + recent
- FSRS-6 spaced repetition for relevance scoring
- API-key-scoped memory per agent, space partitioning within user
- Key lesson: start with FTS5, add vector search only when semantic recall becomes a requirement

## Sources Consulted

### HackerNews Discussions
- [hmem: Persistent hierarchical memory for AI coding agents (MCP)](https://news.ycombinator.com/item?id=47103237)
- [Agent Recall: Open-source, local memory for AI agents (SQLite/MCP)](https://news.ycombinator.com/item?id=47165499)
- [Engram: open-source persistent memory for AI agents (Bun/SQLite)](https://news.ycombinator.com/item?id=47307497)
- [A hackable AI assistant using a single SQLite table and cron jobs](https://news.ycombinator.com/item?id=43681287)
- [Closure table vs adjacency list discussion](https://news.ycombinator.com/item?id=13128295)
- [Notion data model discussion](https://news.ycombinator.com/item?id=27200177)

### Technical Articles and Documentation
- [SQLite FTS5 Extension](https://www.sqlite.org/fts5.html)
- [SQLite JSONB format](https://sqlite.org/jsonb.html)
- [SQLite WITH RECURSIVE (CTEs)](https://sqlite.org/lang_with.html)
- [Materialized paths as trees](https://sqlfordevs.com/tree-as-materialized-path)
- [High-performance Rust with SQLite (15k inserts/s benchmarks)](https://kerkour.com/high-performance-rust-with-sqlite)
- [Flexible database support in Rust with Diesel (dual-backend pattern)](https://colliery.io/blog/dual_backends/)
- [ZeroClaw hybrid memory: SQLite Vector + FTS5](https://zeroclaws.io/blog/zeroclaw-hybrid-memory-sqlite-vector-fts5/)

### Product Documentation
- [Notion data model blog post](https://www.notion.com/blog/data-model-behind-notion)
- [Linear conceptual model](https://linear.app/docs/conceptual-model)
- [Obsidian Dataview metadata](https://blacksmithgu.github.io/obsidian-dataview/annotation/add-metadata/)
- [libSQL/Turso documentation](https://docs.turso.tech/libsql)
- [OpenContext GitHub](https://github.com/0xranx/OpenContext)

### GitHub Repositories
- [hmem](https://github.com/Bumblebiber/hmem) -- hierarchical memory MCP server
- [simple-graph](https://github.com/dpapathanasiou/simple-graph) -- graph DB in SQLite
- [serde-sqlite-jsonb](https://github.com/lovasoa/serde-sqlite-jsonb) -- Rust Serde for SQLite JSONB
- [AgentDB](https://lib.rs/crates/agentdb) -- unified DB abstraction for Rust

### Industry Sources
- [Redis: AI agent memory architecture](https://redis.io/blog/ai-agent-memory-stateful-systems/)
- [OpenAI: Context personalization with Agents SDK](https://cookbook.openai.com/examples/agents_sdk/context_personalization)
- [Amazon Bedrock AgentCore Memory](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-memory-building-context-aware-agents/)

## Source Quality Assessment

**High confidence** on:
- SQLite feature capabilities (FTS5, JSONB, WAL) -- verified against official docs
- Hierarchy model tradeoffs -- well-established CS literature, confirmed by HN practitioners
- Rust ORM comparison -- multiple independent comparisons, all 2025-2026

**Medium confidence** on:
- Agent Recall and hmem schema details -- extracted from HN posts and READMEs, actual SQL DDL not publicly documented
- AgentDB trait interface -- docs.rs page is sparse; would need source code review

**Low confidence** on:
- Optimal concurrency numbers for multi-agent write scenarios -- benchmarks are from single-machine setups, real-world agent patterns may differ

## Open Questions

1. **Vector search integration**: When (if ever) should vector embeddings be added? Engram's migration from SQLite to libsql suggests this is a "later" concern. FTS5 with BM25 scoring may be sufficient for structured knowledge retrieval.

2. **Conflict resolution**: When two agents write contradictory facts at the same scope, how should conflicts be resolved? Agent Recall uses bitemporal history but leaves resolution to the reading agent. HN commenters flagged this as an unsolved problem.

3. **Garbage collection for session-scoped entries**: Sessions are ephemeral. Should session entries be auto-pruned after N days? hmem uses access-count-based surfacing (LRU-like) rather than deletion.

4. **Cross-scope references**: An entry at repo scope might reference a decision at project scope. The `entry_relations` table handles this, but should scope boundaries constrain what can be related?

5. **Schema evolution**: How to handle migrations when the entries table schema changes? sqlx has built-in migration support. The JSONB `meta` column provides a pressure valve for adding fields without migrations.

## Actionable Takeaways

1. **Start with the materialized-path schema** proposed in Section 2. It handles the 4-level hierarchy without requiring closure tables or complex recursive queries for the common case.

2. **Use sqlx directly** (not SeaORM or Diesel) with a `ContextStore` trait. This gives compile-time SQL verification, async support, and a clean path to PostgreSQL or libSQL later.

3. **Configure SQLite pragmas aggressively**: WAL mode, busy_timeout, mmap, cache_size. The benchmarks confirm these make a 5-10x difference.

4. **Design for append-only with soft supersession** (`superseded_by` column). Every agent memory system that has shipped in production uses some form of this pattern.

5. **Use the vocabulary**: global, project, repo, session. Avoid "workspace" and "namespace" as scope level names.

6. **Add FTS5 from day one** with porter stemming. The setup cost is minimal (3 triggers + 1 virtual table) and the search capability is immediately useful for both human and agent consumers.

7. **Defer vector search** until FTS5 proves insufficient. The migration path to libsql is well-documented and backward-compatible.
