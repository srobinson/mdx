---
title: SQLite FTS5 as Embedded Context Store for Rust MCP Server - Technical Evaluation
type: research
tags: [sqlite, fts5, tantivy, rust, embedded-search, wal-mode, sqlx, concurrency, mcp-server]
summary: SQLite+FTS5 is best-in-class for this workload. Tantivy is the only credible alternative but adds complexity without proportional benefit at <100k entries. The single-writer/multi-reader pool pattern is correct and well-validated. Content-sync triggers are the recommended approach. WAL pragmas are well-tuned with minor adjustments suggested.
status: active
source: deep-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Executive Summary

For a single-machine embedded context store with <100k markdown entries, keyword search, hierarchical scope filtering, and no vector search requirement, SQLite + FTS5 is the correct choice. It outperforms alternatives on operational simplicity, single-file deployment, and integration tightness with the relational data model needed for scope hierarchies. Tantivy is the only serious alternative, offering superior ranking and tokenization, but introduces a second storage layer and index-sync complexity that provides no meaningful benefit at this scale. The proposed WAL pragmas and single-writer/4-reader pool architecture align with established best practices in the Rust SQLite ecosystem.

## 1. FTS5 with porter+unicode61 vs Alternatives

### 1.1 FTS5 (Recommended)

**Strengths for this workload:**
- Atomic consistency with relational data (scope tables, metadata) within the same transaction
- Sub-10ms query latency at <100k documents (HN reports confirm sub-10ms for datasets up to 200k rows)
- Supports prefix search (`term*`), phrase search (`"exact phrase"`), boolean operators (AND/OR/NOT), column filtering
- porter stemmer handles English adequately; unicode61 tokenizer provides case-insensitive Unicode-aware tokenization with diacritics folding
- Zero operational overhead: no separate index files, no background merge processes, no second storage engine
- Prefix indexes (`prefix='2,3'`) eliminate the need for full-index scans on prefix queries

**Known limitations:**
- Porter stemmer is English-only. Non-English stemming requires the Snowball extension or custom tokenizers
- No built-in fuzzy matching (typo tolerance). Workaround: spellfix1 extension or trigram tokenizer
- BM25 ranking is basic compared to Tantivy/Lucene. Column weighting requires manual `bm25()` function calls with explicit weight parameters
- FTS5 query syntax has quirks that make programmatic query construction awkward (e.g., column filters use `:` syntax, negation uses `NOT` keyword)
- No built-in highlighting/snippeting for result display (requires `snippet()` or `highlight()` auxiliary functions)

**Confidence: HIGH.** FTS5 is battle-tested at much larger scale than 100k entries. Multiple HN commenters report years of production use with no corruption or data loss issues.

### 1.2 Tantivy (Credible Alternative, Not Recommended)

**What it offers over FTS5:**
- Superior tokenizer pipeline (stemming, stop words, n-grams, custom analyzers)
- True BM25 with configurable field boosting out of the box
- Faceted search, range queries, fuzzy matching native
- ~2x faster than Lucene in benchmarks; sub-10ms startup time
- MmapDirectory provides extremely low resident memory footprint

**Why it is not recommended for this workload:**
- Introduces a second storage layer alongside SQLite. FTS index lives in Tantivy segment files, relational data lives in SQLite. Keeping them consistent requires application-level coordination
- For <100k entries, the performance difference is unmeasurable. Both return results in single-digit milliseconds
- Tantivy segment files can grow large on real datasets; at 100k entries this is irrelevant but adds unnecessary file management
- No transactional consistency with the SQLite scope/metadata tables. A crash between writing SQLite and committing the Tantivy index creates an inconsistent state
- Adds ~5-10MB to binary size and significant API surface area

**When Tantivy would be the right call:** If the workload grows to 1M+ entries, requires typo-tolerant search, needs sophisticated relevance tuning (field boosting, custom scoring), or if the relational data model is abandoned in favor of document-oriented storage.

**Confidence: HIGH.** Tantivy is mature (quickwit-oss maintained, used by ParadeDB) but the integration complexity is disproportionate to the benefit at this scale.

### 1.3 MeiliSearch (Not Recommended)

MeiliSearch is a standalone HTTP search server, not an embeddable library. It requires a separate process, introduces network latency, and adds operational complexity (configuration, health monitoring, upgrades). Written in Rust but architecturally wrong for embedding inside a single binary MCP server. Designed for user-facing typo-tolerant search, not structured keyword search.

**Confidence: HIGH.** Architecture mismatch is definitive.

### 1.4 DuckDB FTS (Not Recommended)

DuckDB's FTS extension uses an inverted index with BM25 scoring (Okapi variant), but DuckDB is an OLAP engine optimized for analytical column-scan workloads. SQLite outperforms DuckDB by 10-500x on transactional write workloads. DuckDB does not support WAL-style concurrent read/write. It is architecturally designed for batch analytics, not for a multi-reader transactional context store.

**Confidence: HIGH.** Architecture mismatch is definitive.

### 1.5 sqlite-vec / sqlite-vss (Not Applicable)

sqlite-vss is deprecated in favor of sqlite-vec (pure C, no dependencies, runs anywhere). Both are vector search extensions providing KNN/ANN similarity search over embeddings. They solve a different problem (semantic/vector search) from keyword search (FTS5). Since the spec explicitly states vector search is handled by a separate system, these are not relevant. If vector search were needed in the same database, sqlite-vec could complement FTS5 without replacing it.

**Confidence: HIGH.** Different problem domain.

## 2. WAL Pragma Tuning Assessment

### Proposed Configuration

| Pragma | Proposed Value | Assessment |
|---|---|---|
| `journal_mode` | WAL | Correct. Required for concurrent read/write |
| `synchronous` | NORMAL | Correct. Safe in WAL mode, 2-3x faster writes than FULL |
| `cache_size` | 64MB (-16384 pages) | Slightly oversized but harmless. For <100k entries the db will likely be <500MB. 32MB would suffice. No downside to 64MB on a desktop/server machine |
| `mmap_size` | 256MB | Correct. Rule of thumb: set larger than expected database file size. For <100k markdown entries (estimated 50-200MB db), 256MB covers the entire file. Uses virtual address space only, not physical RAM |
| `busy_timeout` | 5000ms | Correct. Industry consensus is 3000-5000ms. Default of 0 causes immediate SQLITE_BUSY errors. 5s gives write operations adequate time to acquire locks |

### Additional Pragmas to Consider

| Pragma | Recommended Value | Rationale |
|---|---|---|
| `temp_store` | MEMORY | Keeps temporary tables/indexes in memory. Standard recommendation for performance |
| `foreign_keys` | ON | SQLite does not enforce foreign keys by default. Must be set per-connection |
| `wal_autocheckpoint` | 1000 (default) | Default is fine for this workload. Only increase if write bursts cause WAL file growth |
| `journal_size_limit` | 67108864 (64MB) | Prevents unbounded WAL file growth, which can degrade read performance. Multiple sources report WAL files growing to infinity without this |

### mmap_size Risk Note

mmap provides performance benefits by eliminating read() syscalls, but crashes the process (SIGSEGV/SIGBUS) if the underlying storage disconnects (network drives, USB). For a local-only embedded database on stable storage, this risk is negligible. If the MCP server might access databases on networked filesystems, set mmap_size to 0.

**Confidence: HIGH.** These pragmas are well-documented and consensus-backed across multiple production guides (phiresky's blog, Rails 7.1 defaults, HN discussions, Evan Schwartz's benchmarks).

## 3. FTS5 Content-Sync Triggers

### The Pattern

The "external content table" pattern uses `content=` to point FTS5 at a regular table, with AFTER INSERT/UPDATE/DELETE triggers keeping the FTS index synchronized. This avoids storing text twice (once in the content table, once in FTS5's internal storage).

### Assessment: Correct Approach with Caveats

**Why triggers are recommended:**
- Official SQLite documentation endorses this pattern
- Keeps FTS5 and content table automatically synchronized within the same transaction
- Saves storage by not duplicating text content
- Trigger-based sync is atomic: if the transaction rolls back, both the content change and the FTS update roll back

**Critical implementation detail for UPDATE triggers:**
FTS5 external content UPDATE triggers must delete the OLD row values before inserting the NEW ones. The trigger must reference OLD.column_name for the delete and NEW.column_name for the insert. If the trigger references the wrong version, FTS5 attempts to remove tokens that do not exist in the index, silently corrupting the search state. The official docs show the correct pattern:

```sql
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
```

**Alternative: Application-level sync.** Some developers skip triggers and issue the FTS INSERT/DELETE alongside each content table mutation in application code. This gives more control but moves the consistency guarantee out of the database layer. For a single-writer architecture where all writes flow through one code path, this is viable but offers no advantage over triggers while adding a class of bugs (forgetting to update the FTS table on a new write path).

**Alternative: Contentless FTS5 (`content=''`).** Stores only the inverted index, not the text. Cannot return matched text, only rowids. Useful when the text is stored elsewhere (e.g., files on disk) and you only need FTS5 for filtering. Does not support UPDATE or DELETE without explicit rowid. For a context store that needs to return entry content, contentless tables add complexity without benefit.

**The `rebuild` command** (`INSERT INTO fts(fts) VALUES('rebuild')`) reconstructs the entire FTS index from the content table. At <100k entries this completes in seconds. Useful as a recovery mechanism if the index becomes corrupted, but should not be part of normal operation.

**Confidence: HIGH.** The trigger-based content-sync pattern is the canonical approach documented by SQLite itself. No superior alternative has emerged in 2025-2026.

## 4. Concurrency Model: Single Writer + 4 Readers

### Assessment: Correct Architecture

The proposed model of one dedicated write connection plus a pool of 4 read-only connections is the established best practice for SQLite WAL mode in Rust async servers. This is validated by:

**Evan Schwartz's benchmarks (2024-2025):** Single-writer achieved ~60,061 rows/sec vs ~2,586 rows/sec with a 50-connection pool. The 20x improvement comes from eliminating lock contention at the SQLite level.

**sqlx-sqlite-conn-mgr crate:** A dedicated Rust crate implementing exactly this pattern (write pool with max_connections=1, read pool with max_connections=num_cpus, reader connections opened as read_only).

**Multiple HN threads:** Consensus recommendation across 5+ threads is to serialize writes through a single connection and use separate read connections.

### Implementation Details for sqlx

**Writer pool configuration:**
```rust
SqlitePoolOptions::new()
    .max_connections(1)
    .connect_with(
        SqliteConnectOptions::new()
            .filename(&db_path)
            .journal_mode(SqliteJournalMode::Wal)
            .busy_timeout(Duration::from_secs(5))
            .synchronous(SqliteSynchronous::Normal)
    )
```

**Reader pool configuration:**
```rust
SqlitePoolOptions::new()
    .max_connections(4)  // or num_cpus::get()
    .connect_with(
        SqliteConnectOptions::new()
            .filename(&db_path)
            .read_only(true)
            .journal_mode(SqliteJournalMode::Wal)
            .busy_timeout(Duration::from_secs(5))
    )
```

### Reader Pool Size: 4 vs num_cpus

4 readers is reasonable for an MCP server handling a handful of concurrent agent connections. The theoretical maximum is the number of CPU cores (`num_cpus::get()`), since each reader connection can execute queries on its own thread. For a workload where queries complete in single-digit milliseconds, 4 connections can handle hundreds of concurrent requests through connection reuse. Increasing to 8 or 16 provides diminishing returns unless queries are CPU-bound (e.g., complex FTS5 ranking on large result sets).

### Critical sqlx+SQLite Gotcha: Async Write Transactions

**The footgun:** If you start a write transaction (or `BEGIN IMMEDIATE`) and then `.await` inside it, the async runtime may schedule other tasks while you hold the exclusive write lock. Those tasks, if they attempt writes, will block until `busy_timeout` expires and then fail with SQLITE_BUSY.

**Mitigation strategies:**
1. Keep write transactions as short as possible. Do all preparation before beginning the transaction
2. Avoid `.await` on non-database operations inside write transactions
3. Consider using `rusqlite` with `spawn_blocking` for complex write transactions that require multiple round-trips. sqlx's async model adds overhead for SQLite's synchronous API anyway
4. For atomic read-then-write operations, ensure the read is fast (primary key lookup). Complex reads should happen on a reader connection before the write transaction begins

### Alternative: rusqlite + spawn_blocking

Multiple sources (including Evan Schwartz) suggest that for complex write transactions, `rusqlite` wrapped in `tokio::task::spawn_blocking` may be simpler and more predictable than sqlx. rusqlite provides direct access to SQLite features like custom functions, FTS5 auxiliary functions, and virtual tables without abstraction layers. The tradeoff: no compile-time query checking, and you manage the connection lifecycle manually.

For a single-writer MCP server where write paths are well-defined and limited, rusqlite is a legitimate alternative to sqlx for the write connection while keeping sqlx for the read pool.

**Confidence: HIGH.** The single-writer/multi-reader pattern is the single most well-validated SQLite concurrency architecture in the Rust ecosystem.

## 5. Additional Findings

### 5.1 FTS5 and Hierarchical Scope Filtering

FTS5 queries can be combined with regular SQL WHERE clauses when using external content tables. For hierarchical scope filtering (walking up scope ancestry), the recommended pattern is:

1. Use a recursive CTE or pre-computed ancestor table to resolve the scope hierarchy
2. Join the scope resolution with FTS5 results: `SELECT * FROM entries_fts WHERE entries_fts MATCH ? AND rowid IN (SELECT entry_id FROM scope_entries WHERE scope_id IN (...))`

This keeps the FTS5 query fast (it returns candidate rowids) and the scope filtering happens as a post-filter on the relational side. At <100k entries, this two-phase approach completes in single-digit milliseconds.

### 5.2 Turso's Tantivy Integration (Informational)

Turso (libSQL fork) shipped experimental Tantivy-based FTS in v0.5.0 (January 2026), storing Tantivy inverted index segments inside the SQLite B-tree. This provides transactional FTS with superior tokenization. However, Turso is a fork of SQLite (libSQL), not standard SQLite, and introduces its own operational model. For an embedded Rust binary using standard SQLite via rusqlite/sqlx, this is not directly applicable. Worth monitoring if the project migrates to libSQL.

### 5.3 libsqlite3-sys Version Conflicts

Using both sqlx and rusqlite in the same project can cause build failures because both link against `libsqlite3-sys`. Cargo requires exactly one version of a crate that links a native library. Pin both crates to compatible versions or use a single SQLite access layer.

## Sources Consulted

### Engineering Blog Posts
- [Evan Schwartz - Connection Pool Write Performance](https://emschwartz.me/psa-your-sqlite-connection-pool-might-be-ruining-your-write-performance/) - Definitive benchmarks on single-writer pattern
- [Evan Schwartz - Write Transactions Footgun](https://emschwartz.me/psa-write-transactions-are-a-footgun-with-sqlx-and-sqlite/) - async/await lock starvation with sqlx
- [phiresky - SQLite Performance Tuning](https://phiresky.github.io/blog/2020/sqlite-performance-tuning/) - Canonical WAL+pragma guide, 100k SELECTs/s
- [Turso - Beyond FTS5](https://turso.tech/blog/beyond-fts5) - Tantivy integration architecture

### HackerNews Discussions
- [FTS5 Production Experience](https://news.ycombinator.com/item?id=41207085) - 15M row FTS5 deployment, performance characteristics
- [FTS5 Extension Discussion](https://news.ycombinator.com/item?id=41198422) - Tokenizer limitations, non-English challenges
- [SQLite Concurrency](https://news.ycombinator.com/item?id=45781298) - busy_timeout, BEGIN IMMEDIATE, WAL best practices

### Official Documentation
- [SQLite FTS5 Extension](https://www.sqlite.org/fts5.html) - Authoritative reference for content-sync triggers, tokenizers
- [SQLite WAL Mode](https://sqlite.org/wal.html) - Concurrency model, checkpoint behavior
- [SQLite mmap](https://sqlite.org/mmap.html) - Memory-mapped I/O tradeoffs

### Rust Ecosystem
- [sqlx-sqlite-conn-mgr](https://crates.io/crates/sqlx-sqlite-conn-mgr) - Reference implementation of split reader/writer pools
- [sqlx SqliteConnectOptions](https://docs.rs/sqlx/latest/sqlx/sqlite/struct.SqliteConnectOptions.html) - Pool configuration API
- [Tantivy](https://github.com/quickwit-oss/tantivy) - Full-text search library benchmarks and architecture

## Source Quality Assessment

**High confidence areas:** WAL pragma tuning, single-writer concurrency model, FTS5 content-sync triggers. Multiple independent sources (official docs, engineering blogs with benchmarks, HN practitioner reports) converge on the same recommendations.

**Medium confidence areas:** Tantivy vs FTS5 at small scale. No direct benchmark exists comparing these two at <100k documents in a Rust context. The recommendation against Tantivy is based on architectural analysis (dual storage layer complexity) rather than measured performance.

**Gap:** No Reddit discussions found on this specific topic combination. The Rust+SQLite community discussion appears scattered across the Rust Users Forum, GitHub issues, and individual blog posts rather than concentrated on Reddit.

## Open Questions

1. **FTS5 + WAL checkpoint interaction:** Heavy FTS5 writes generate large WAL files. At what write rate does `wal_autocheckpoint=1000` become insufficient? For <100k entries with typical agent workloads (dozens of writes/minute), the default should be fine, but sustained bulk ingestion may require tuning.

2. **rusqlite vs sqlx for the write connection:** The research strongly suggests rusqlite with `spawn_blocking` may be simpler for the single-writer path. Worth prototyping both approaches.

3. **Turso/libSQL migration path:** If the project later needs cross-device sync or superior FTS, migrating to libSQL (Turso's fork) would provide Tantivy-based FTS within the SQLite transaction model. This would require replacing the SQLite driver but not the schema.

## Actionable Takeaways

1. **Proceed with SQLite + FTS5.** It is best-in-class for this workload. No alternative provides a better tradeoff at this scale.

2. **Keep the proposed WAL pragmas.** Add `temp_store=MEMORY`, `foreign_keys=ON`, and `journal_size_limit=67108864`.

3. **Keep the content-sync trigger pattern.** It is the canonical approach. Pay careful attention to the UPDATE trigger ordering (delete OLD before insert NEW).

4. **Keep the 1-writer / 4-reader pool split.** This is the most validated pattern in the Rust SQLite ecosystem. Consider marking reader connections as `read_only(true)` for defense in depth.

5. **Watch for the sqlx async write transaction footgun.** Keep write transactions short, avoid non-database `.await` inside them, and consider rusqlite+spawn_blocking for the write path if complex multi-step writes are needed.

6. **Add prefix indexes to FTS5** (`prefix='2,3'`) to accelerate prefix queries without full-index scans.
