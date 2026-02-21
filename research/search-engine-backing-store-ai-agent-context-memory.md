---
title: Search engines as backing store for AI agent context/memory systems
type: research
tags: [elasticsearch, tantivy, lancedb, sqlite, search, agent-memory, context-matters, rust, local-first]
summary: Comprehensive evaluation of Elasticsearch and alternatives for a local-first, Rust-based AI agent context store. Recommendation is SQLite + Tantivy + sqlite-vec hybrid, not Elasticsearch.
status: active
source: deep-research
confidence: high
created: 2026-03-14
updated: 2026-03-14
---

## Executive Summary

Elasticsearch is architecturally overqualified for context-matters. It excels at distributed, high-throughput search across millions of documents, but imposes 1-4GB RAM overhead, requires JVM management, and adds Docker/sidecar operational complexity that directly conflicts with the local-first constraint. For a system handling thousands to tens of thousands of context documents on developer laptops, the optimal architecture is **SQLite as the structured store + Tantivy as the embedded full-text search index + sqlite-vec for vector/semantic search**. This gives you transactional structured data, BM25-quality full-text search, and kNN semantic search with zero external processes, all in Rust.

## Detailed Findings

### 1. Elasticsearch: Powerful but Wrong-Shaped

**What ES does well for this use case:**
- Hybrid search is now first-class: ES 8.x `dense_vector` field type supports kNN search with HNSW, and queries can combine structured filters (term, range) with vector similarity in a single request via the `knn` query option
- Schema flexibility via runtime fields (schema-on-read added in 7.11) lets you query unindexed fields without reindexing
- ES 8.x supports ACORN-1 for fast filtered kNN even on large datasets
- Elastic is heavily investing in "agent memory" positioning (Agent Builder, MCP support, ES|QL for vector search)

**Why it fails the local-first constraint:**
- Minimum viable Docker allocation: 2GB heap + 2GB OS overhead = 4GB for a single node. Can technically run at 512MB heap but performance degrades severely
- Requires `vm.max_map_count=1048576` kernel tuning on Linux
- JVM startup time adds 10-30 seconds to cold starts
- A practitioner running ES for 15 req/min measured 1GB RAM and 30% CPU at idle; replacing with Rust+SQLite dropped to 8.9MB RAM and 0.004% CPU (100x and 1000x reductions respectively) [nickb.dev]
- Multi-agent concurrent writes are ES's strength (distributed by design), but this advantage is irrelevant at local scale

**Verdict:** ES is a Corvette when you need a bicycle. The operational burden alone disqualifies it for a tool that developers run alongside their IDE.

### 2. Alternative Search Engines Evaluated

#### Tantivy (Recommended for full-text)
- **What it is:** Rust-native full-text search library inspired by Lucene. Embeds directly as a crate, no server process
- **Strengths:** BM25 ranking, faceted search, range queries, incremental indexing. 2x faster than Lucene in benchmarks. Runs on a Raspberry Pi at 100 req/s with negligible CPU. Documentation praised as "second to none" by practitioners
- **Weaknesses:** No native vector search (issue #815 open since 2020, still unmerged as of v0.25.0 August 2024). Schema changes require reindex (workaround: JSON fields). Limited multi-language stemming support
- **Concurrency:** Single-writer, multiple-reader model. For context-matters, this is adequate since writes are infrequent relative to reads
- **HN sentiment:** Consistently recommended over ES for small-to-medium scale. One practitioner: "as ergonomic as they get" vs ES described as "the resource hog"
- **Key fact:** Tantivy is the search library underneath Meilisearch, Quickwit, LanceDB FTS, and Turso FTS

#### Meilisearch
- **Architecture:** Rust binary, runs as HTTP server (not embeddable as a library without significant effort). Uses LMDB for storage
- **Hybrid search:** Supports vector search (Arroy store) since v1.3, with hybrid semantic+keyword search since v1.6. Embedder integrations with OpenAI, Cohere, HuggingFace
- **Storage overhead:** 6-8x larger index files than SQLite FTS5 for equivalent data
- **Limitation:** Not designed as an embedded library. The HTTP server architecture means running a sidecar process, which partly defeats the purpose of avoiding ES
- **Best for:** Developer-facing search UIs, rapid prototyping. Wrong tool for an embedded context store

#### Typesense
- **Architecture:** C++ single binary, entire index lives in RAM
- **Strengths:** Sub-50ms responses, typo tolerance, faceting, semantic search support
- **Limitation:** Server architecture (not embeddable). Dataset must fit in RAM. Less mature than ES for complex queries
- **Verdict:** Similar problem to Meilisearch. A server when you want a library

#### OpenSearch
- **What it is:** Apache 2.0 fork of ES 7.10.2, governed by Linux Foundation since Sept 2024
- **Differences from ES:** Security suite included by default, fully open source. Recent benchmarks show mixed performance vs ES 8.x (some workloads faster, some slower)
- **For this use case:** Same operational weight as ES. Solves the licensing concern but not the local-first constraint
- **Verdict:** If you needed ES, OpenSearch would be the better-licensed choice. But you do not need ES

#### Sonic
- **Architecture:** Rust-based search backend using ~30MB RAM
- **Limitation:** TCP protocol server (not an embedded library). 32-bit ID limit. Batch index rebuilds. No full-text retrieval (returns IDs only, not document content)
- **Verdict:** Too limited for a context store. Good for autocomplete, wrong for knowledge retrieval

#### ZincSearch
- **Architecture:** Go-based single binary, ES-compatible API
- **Verdict:** Lighter than ES but still a server. Not Rust. Not embeddable

### 3. Vector/Semantic Search Options

#### sqlite-vec (Recommended for vectors)
- **What it is:** Pure C SQLite extension for vector similarity search. Successor to sqlite-vss. Zero dependencies
- **Rust support:** Exposes `sqlite3_vec_init` for registration via `sqlite3_auto_extension()`. Works with `zerocopy::AsBytes` for zero-copy vector passing
- **Capabilities:** kNN search, cosine similarity, dot product. Runs anywhere SQLite runs including WASM
- **Limitation:** Brute-force scan for small collections (no HNSW). For tens of thousands of documents this is fine; for millions it would not be

#### LanceDB
- **What it is:** Embedded vector database with Rust core. Uses Lance columnar format + Apache DataFusion for queries
- **Strengths:** Full-text search via Tantivy integration, vector search, SQL filtering, hybrid search. 4MB idle RAM, ~150MB during search. Truly serverless/embedded
- **Weakness:** Adds a separate data format (Lance) alongside SQLite, increasing architectural complexity. The Rust API is production-ready but the ecosystem is Python-first
- **Consideration:** If context-matters needed to be a pure vector store, LanceDB would be the answer. But the primary data model is structured context with search as a secondary concern

#### Qdrant
- **What it is:** Rust-based vector database, HNSW-based, high performance
- **Limitation:** Client-server architecture. No true embedded mode for Rust (Python has `:memory:` mode). 400MB constant RAM usage
- **Verdict:** Wrong deployment model for local-first

### 4. SQLite FTS5: The Baseline

- BM25 ranking (same algorithm as ES and Lucene)
- Handles up to ~500K documents comfortably
- Index creation 40% faster than FTS3/FTS4
- 6-8x smaller storage than Meilisearch for equivalent data
- Zero operational overhead (same process, same file)
- **Limitations:** No semantic/vector search. No custom tokenizers beyond ICU. No fuzzy matching. No faceted search. English-centric stemming

For basic "find context about authentication" queries, FTS5 is sufficient. For "find context semantically related to this embedding," it is not.

### 5. Architecture Recommendation

**Primary architecture: SQLite + Tantivy + sqlite-vec**

```
context-matters binary (Rust)
  |
  +-- SQLite (structured data, source of truth)
  |     +-- FTS5 (basic full-text, zero cost to add)
  |     +-- sqlite-vec (vector similarity search)
  |
  +-- Tantivy (advanced full-text search index)
        - BM25 ranking
        - Faceted search
        - Range queries on metadata
```

**How it works:**
1. SQLite stores all context records with structured fields (project, repo, workspace, tags, timestamps, content)
2. FTS5 virtual table shadows the content column for basic keyword search (near-zero overhead)
3. sqlite-vec stores embeddings for semantic search (generated on write via local or remote model)
4. Tantivy maintains a parallel search index for advanced queries (faceted, ranked, filtered)
5. Writes go to SQLite first (transactional), then Tantivy index is updated asynchronously or in the same operation

**Why not just SQLite FTS5 alone?**
- No faceted search (e.g., "search for 'auth' but only in project X, grouped by repo")
- No relevance tuning beyond basic BM25
- No semantic search
- Tantivy adds maybe 5-10MB to the binary and near-zero runtime overhead for the index sizes involved

**Why not just Tantivy alone?**
- Tantivy is not a database. It stores inverted indexes, not documents. You still need a source of truth for structured queries like "give me all context for repo X sorted by last modified"
- Tantivy has no vector search support

**Why not LanceDB instead of this stack?**
- LanceDB would replace SQLite+sqlite-vec+Tantivy with a single system. Tempting. But:
  - LanceDB uses its own file format (Lance), not SQLite. This means context-matters data lives in a format that other tools in the helioy ecosystem cannot read directly
  - The Rust API, while functional, is less mature than the Python SDK
  - SQLite gives you relational queries, joins, and schema migrations that LanceDB does not
  - For a system where structured queries ("all context for workspace X") dominate and search is secondary, SQL wins

**Alternative worth monitoring: Turso**
- Turso (Rust SQLite rewrite) has experimental Tantivy integration that stores the inverted index inside the SQLite B-tree with full transactional consistency
- If Turso stabilizes this feature, it would collapse the SQLite+Tantivy stack into a single database file
- Currently behind `--experimental-index-method` flag. Not production-ready

### 6. Concurrency for Multi-Agent Access

SQLite's single-writer limitation is the most common objection. For context-matters:

- **Read-heavy workload:** Multiple agents reading context simultaneously is the primary access pattern. SQLite handles unlimited concurrent readers in WAL mode
- **Write contention:** Context writes are infrequent (humans or agents adding/updating context entries). SQLite write transactions complete in milliseconds. At the scale of a few agents on one machine, write contention is negligible
- **If write contention becomes real:** WAL mode + `busy_timeout` handles it cleanly. A writer blocks for at most a few milliseconds. This is not a database serving web traffic; it is a context store for a handful of local agents

### 7. Schema Flexibility

ES advocates cite schema flexibility as a key advantage. In practice:

- Context-matters has a known core schema (project, repo, workspace, content, tags, timestamps). This is relational data
- SQLite JSON1 extension handles semi-structured metadata fields elegantly (`json_extract`, `json_each`)
- Schema migrations in SQLite are trivial at this scale
- ES's "dynamic mapping" advantage matters when you are ingesting unknown log formats. Context-matters knows its data shape

### 8. The sqlite-memory Project (Prior Art)

The [sqliteai/sqlite-memory](https://github.com/sqliteai/sqlite-memory) project implements exactly this pattern for AI agent memory:
- SQLite base storage
- sqlite-vector for vector similarity search
- FTS5 for keyword matching
- Hybrid retrieval with configurable vector_weight and text_weight
- Markdown-aware chunking
- Content-hash change detection
- Context isolation by project/conversation

This validates the SQLite-first approach. The main difference: sqlite-memory is a C SQLite extension, while context-matters would implement this in Rust with Tantivy replacing FTS5 for richer search capabilities.

## Sources Consulted

### Elasticsearch Agent Memory
- [Elastic Labs: Agentic Memory Management](https://www.elastic.co/search-labs/blog/agentic-memory-management-elasticsearch)
- [Elastic: Context Engineering for AI Agents](https://www.elastic.co/elasticsearch/context-engineering)
- [DEV.to: Why Elasticsearch Is the Best Memory for AI Agents](https://dev.to/omkar598/why-elasticsearch-is-the-best-memory-for-ai-agents-a-deep-dive-into-agentic-architecture-137l)

### Tantivy
- [GitHub: quickwit-oss/tantivy](https://github.com/quickwit-oss/tantivy)
- [HN Discussion: Tantivy full-text search](https://news.ycombinator.com/item?id=40492834)
- [Tantivy Issue #815: Vector Search Status](https://github.com/quickwit-oss/tantivy/issues/815)
- [Tantivy Releases](https://github.com/quickwit-oss/tantivy/releases) (latest: v0.25.0, Aug 2024)

### SQLite + Search
- [nickb.dev: Replacing Elasticsearch with Rust and SQLite](https://nickb.dev/blog/replacing-elasticsearch-with-rust-and-sqlite/)
- [HN Discussion: Replacing ES with Rust+SQLite](https://news.ycombinator.com/item?id=27175284)
- [sqliteai/sqlite-memory](https://github.com/sqliteai/sqlite-memory)
- [sqlite-vec: Vector Search SQLite Extension](https://github.com/asg017/sqlite-vec)
- [SQLite FTS5 Documentation](https://www.sqlite.org/fts5.html)

### Turso/Limbo (SQLite+Tantivy Integration)
- [Turso: Beyond FTS5](https://turso.tech/blog/beyond-fts5)

### LanceDB
- [LanceDB GitHub](https://github.com/lancedb/lancedb)
- [LanceDB WikiSearch: Native FTS on 41M Wikipedia Docs](https://lancedb.com/blog/feature-full-text-search/)
- [Brian Sunter: Qdrant vs LanceDB benchmarks](https://x.com/Bsunter/status/1984579340219433386)

### Meilisearch / Typesense
- [Meilisearch: Hybrid Search](https://www.meilisearch.com/solutions/hybrid-search)
- [Meilisearch Issue #1297: Embedded Library Mode](https://github.com/meilisearch/MeiliSearch/issues/1297)
- [Typesense: Comparison with Alternatives](https://typesense.org/docs/overview/comparison-with-alternatives.html)

### OpenSearch
- [InfoWorld: OpenSearch in 2025](https://www.infoworld.com/article/3971473/opensearch-in-2025-much-more-than-an-elasticsearch-fork.html)

### AI Agent Memory Architecture
- [Google PM: Always On Memory Agent](https://venturebeat.com/orchestration/google-pm-open-sources-always-on-memory-agent-ditching-vector-databases-for)
- [PingCAP: Local-First RAG with SQLite](https://www.pingcap.com/blog/local-first-rag-using-sqlite-ai-agent-memory-openclaw/)
- [MarkTechPost: Persistent AI Agent OS with SQLite + FAISS](https://www.marktechpost.com/2026/03/04/how-to-build-an-evermem-style-persistent-ai-agent-os-with-hierarchical-memory-faiss-vector-retrieval-sqlite-storage-and-automated-memory-consolidation/)

## Source Quality Assessment

**High confidence findings:**
- Elasticsearch resource requirements (well-documented, multiple independent measurements)
- Tantivy capabilities and limitations (verified via GitHub releases, HN practitioner reports, crates.io)
- sqlite-vec and FTS5 capabilities (official documentation + practitioner benchmarks)
- LanceDB embedded architecture and memory profile (verified via independent benchmarks)

**Medium confidence findings:**
- Turso's Tantivy integration maturity (experimental flag, limited production reports)
- Tantivy vector search roadmap (issue #815 has gone years without resolution; stated "0.22+" plans did not materialize)

**Low confidence / gaps:**
- Reddit discussions on this topic are sparse to nonexistent. The community discussing these architectural choices lives on HN and GitHub issues, not Reddit
- No direct benchmarks comparing SQLite FTS5 + Tantivy + sqlite-vec as a combined stack against ES for agent memory workloads

## Open Questions

1. **Tantivy vector search timeline:** Will native vector support ever ship, or should the architecture permanently assume Tantivy handles text and sqlite-vec handles vectors?
2. **Turso stability:** Is the Tantivy-in-SQLite integration stable enough to bet on, or should context-matters maintain its own Tantivy index alongside SQLite?
3. **Embedding generation:** Should context-matters generate embeddings locally (e.g., via candle or ort crate) or delegate to an external service? This affects the sqlite-vec vs "no vectors at all" decision
4. **Index consistency:** With separate SQLite and Tantivy stores, how do you handle crash recovery where SQLite committed but Tantivy did not? Turso solves this with transactional integration, but standalone Tantivy does not

## Actionable Takeaways

1. **Do not adopt Elasticsearch.** The operational overhead is unjustifiable for local-first software at this scale. Every practitioner source confirms ES is overkill for sub-100K document collections on single machines.

2. **Keep SQLite as the source of truth.** The structured query pattern ("all context for repo X") is a relational query. SQLite handles it perfectly with zero operational cost.

3. **Add Tantivy as an embedded search index.** It gives you BM25 ranking, faceted search, and query flexibility that FTS5 cannot match, with no external process and negligible resource overhead. Use it via the `tantivy` crate directly.

4. **Add sqlite-vec for semantic search when needed.** If context-matters requires "find semantically similar context," sqlite-vec provides kNN search inside the same SQLite database. For tens of thousands of documents, brute-force kNN in sqlite-vec is fast enough.

5. **Also enable FTS5 as a zero-cost baseline.** FTS5 virtual tables are trivial to add and provide basic keyword search without the Tantivy dependency. Useful as a fallback.

6. **Monitor Turso's Tantivy integration.** If it stabilizes, migrating from SQLite + standalone Tantivy to Turso would collapse the stack into a single transactional database file with full-text search built in.

7. **Skip Meilisearch, Typesense, Qdrant, and OpenSearch.** All require running a separate server process. None can be embedded as a Rust library. They solve the wrong problem.

8. **Consider LanceDB only if the data model pivots to vector-first.** If context-matters evolves into primarily a semantic search system (embeddings as the primary retrieval mechanism), LanceDB's embedded Rust API with integrated Tantivy FTS would be a cleaner single-system answer than the SQLite+Tantivy+sqlite-vec stack. But for a structured context store with search as a secondary concern, SQLite remains the better foundation.
