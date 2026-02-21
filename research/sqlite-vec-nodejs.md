---
title: sqlite-vec: Technical Evaluation for Node.js Vector Search
tags: [sqlite, vector-search, hnswlib, embeddings, research]
date: 2026-03-14
---

# sqlite-vec: Technical Evaluation for Node.js Vector Search

## Executive Summary

sqlite-vec is a compelling option for mdcontext-scale vector workloads (thousands to low tens-of-thousands of document sections) when the corpus stays under roughly 50,000 vectors at 1024 dimensions. At that scale brute-force search completes in well under 100ms per query, the Node.js integration is solid via `better-sqlite3`, and the single-file SQLite database eliminates the dual-artifact problem that hnswlib-node creates (`.bin` index + `.meta.bin` msgpack sidecar). The hybrid search story with FTS5 is architecturally cleaner than the current wink-bm25 + HNSW split.

The case against a replacement right now is maintenance risk. Alex Garcia confirmed in June 2025 that sponsorships have dried up and development is weekend-only. The project has been pre-v1 since its August 2024 launch with no ANN index shipped despite appearing on the roadmap since day one. For a CLI tool distributed via npm, dependency on a pre-v1 C extension with a single active maintainer carries non-trivial supply-chain and breakage risk.

**Verdict:** Do not replace hnswlib-node today. Evaluate again when sqlite-vec ships a stable v1 or when an IVF/ANN index lands and proves stable across Node.js LTS targets. The highest-ROI short-term improvement is migrating wink-bm25 to SQLite FTS5 (using the existing `better-sqlite3` dependency, no new extension required).

---

## 1. What sqlite-vec Is

### Architecture

sqlite-vec is a SQLite extension written in pure C with zero external dependencies. It ships as a loadable `.so`/`.dylib`/`.dll` that any SQLite connection can load at runtime. The core abstraction is the `vec0` virtual table module, which controls row layout, query planning, and KNN dispatch.

Vectors are not stored as raw column values. `vec0` maintains a set of shadow tables inside the same database file, grouped into fixed-size chunks keyed by partition. This design avoids loading the entire vector set into memory for every query; only relevant chunks are paged in.

The query planner detects three execution modes:
- Point lookup by primary key
- Full KNN scan (brute force over all chunks)
- Partition-scoped KNN scan (brute force within a partition)

All current search is exact brute force. There is no HNSW, IVF, or any ANN index in any released version as of March 2026.

### Storage Format

| Vector type | Storage cost | Notes |
|---|---|---|
| `float[N]` | 4 bytes per element | Standard IEEE 754 float32 |
| `int8[N]` | 1 byte per element | 4x compression over float |
| `bit[N]` | N/8 bytes | 32x compression; Hamming distance only |

### Supported Distance Metrics

```sql
create virtual table vec_sections using vec0(
  section_id integer primary key,
  embedding float[1024] distance_metric=cosine
);
```

Supported: `l2` (default), `cosine`, `hamming` (bit vectors only). Cosine and L2 use SIMD acceleration: AVX on x86_64, NEON on ARM64.

### Search Algorithm: Exact Only

sqlite-vec performs exhaustive KNN. Every query visits every chunk unless filtered by partition key. The ANN roadmap (issue #25) planned IVF as Phase 1 and DiskANN as Phase 2. HNSW was explicitly ruled out as too complex within relational constraints. Neither IVF nor DiskANN has shipped as of March 2026.

---

## 2. Performance Benchmarks

### Official Benchmarks (Alex Garcia, M1 Mac Mini, 8 GB RAM)

| Vectors | Dims | Float query | Bit query |
|---|---|---|---|
| 100,000 | 3072 | 214 ms | 11 ms |
| 100,000 | 1536 | 105 ms | — |
| 100,000 | 1024 | ~75 ms | — |
| 500,000 | 960 | 41 ms (static mode) | — |
| 1,000,000 | 128 | 17 ms | — |
| 1,000,000 | 3072 | 8,520 ms | 124 ms |

"Static mode" pre-loads vectors into memory rather than paging from disk.

### mdcontext-Scale Projection

A typical mdcontext corpus: 500 to 30,000 sections at 512 to 1024 dimensions.

| Corpus | Dims | Estimated query time |
|---|---|---|
| 5,000 sections | 1024 | ~4 ms |
| 20,000 sections | 1024 | ~15 ms |
| 50,000 sections | 1024 | ~40 ms |
| 100,000 sections | 1024 | ~75 ms |

For personal knowledge bases and project documentation (the vast majority of mdcontext deployments), sqlite-vec brute force is adequately fast. The HNSW advantage that hnswlib-node provides does not apply meaningfully below 50,000 vectors.

### Third-Party Comparison (100k vectors, 384 dims)

| System | Query time | Notes |
|---|---|---|
| sqlite-vec | 67.84 ms | Brute force |
| sqlite-vector (different project) | 56.65 ms | Optimized C |
| vectorlite (HNSW-backed) | ~1-2 ms | Approximate, higher setup complexity |

---

## 3. Node.js / TypeScript Integration

### Available Packages

| Package | Notes |
|---|---|
| `sqlite-vec` (official) | Prebuilt native `.node` extension; works with `better-sqlite3`, `node-sqlite3`, `node:sqlite` (Node 23.5+), bun, Deno |
| `@dao-xyz/sqlite3-vec` | Wraps sqlite-vec; WASM fallback available (in-memory only) |

### API Surface

```typescript
import * as sqliteVec from 'sqlite-vec'
import Database from 'better-sqlite3'

const db = new Database('.mdcontext/index.db')
sqliteVec.load(db)
```

After loading, all `vec_*` SQL functions and the `vec0` virtual table are available.

### KNN Query Pattern

```sql
create virtual table vec_sections using vec0(
  section_id text primary key,
  embedding float[1024] distance_metric=cosine
);

-- Insert (embedding bound as Float32Array.buffer, NOT number[])
insert into vec_sections(section_id, embedding) values (?, ?);

-- KNN search
with knn as (
  select section_id, distance
  from vec_sections
  where embedding match ?
    and k = 20
)
select s.*, knn.distance
from sections s
join knn on s.id = knn.section_id
order by knn.distance;
```

**Critical binding contract:** vectors must be passed as `Float32Array.buffer`, not as `number[]`. This will silently fail or throw if ignored.

### Metadata Filtering (v0.1.6+)

```sql
create virtual table vec_sections using vec0(
  section_id text primary key,
  embedding float[1024] distance_metric=cosine,
  document_path text
);

select section_id, distance
from vec_sections
where embedding match ?
  and k = 20
  and document_path = '/path/to/file.md';
```

Supported operators: `=`, `!=`, `>`, `>=`, `<`, `<=`, `IN(...)` (text/integer only). No LIKE, GLOB, REGEXP, or NULL. Filters are post-computation, not pre-filter: they do not reduce distance calculations.

---

## 4. sqlite-vec vs FTS5 for Hybrid Search

### Composition

sqlite-vec and FTS5 coexist in the same database file. The canonical hybrid pattern:

```sql
with fts_results as (
  select rowid, rank
  from sections_fts
  where sections_fts match :query
  limit 50
),
vec_results as (
  select section_id, distance
  from vec_sections
  where embedding match :query_vec
    and k = 50
),
rrf as (
  select
    coalesce(f.rowid, v.section_id) as id,
    coalesce(1.0 / (60 + row_number() over (order by f.rank)), 0) +
    coalesce(1.0 / (60 + row_number() over (order by v.distance)), 0) as score
  from fts_results f
  full outer join vec_results v on f.rowid = v.section_id
)
select s.*, rrf.score
from rrf
join sections s on s.id = rrf.id
order by rrf.score desc
limit :k;
```

Requires SQLite 3.39+ for `FULL OUTER JOIN`.

### Current vs SQLite-Native Architecture

| Concern | Current (hnswlib + wink-bm25) | sqlite-vec + FTS5 |
|---|---|---|
| Artifact count | 4+ files per namespace | 1 file |
| Atomic ingestion | No (two independent writes) | Yes (SQLite transaction) |
| Hybrid fusion | JavaScript RRF | SQL CTE |
| Delta updates | ID-based skip logic in JS | `INSERT OR IGNORE` + `DELETE` |
| Crash recovery | Manual consistency check | SQLite WAL journal |
| BM25 quality | wink-bm25-text-search (adequate) | FTS5 BM25 (better) |
| Portability | hnswlib-node native binary | sqlite-vec native binary |

---

## 5. Limitations

| Limitation | Severity |
|---|---|
| No ANN index (exact only) | Low at mdcontext scale; revisit at 100k+ vectors |
| No UPSERT | Low; delete-then-insert is workable |
| Metadata filters are post-scan, not pre-filter | Low for small corpora |
| NULL values unsupported in metadata columns | Low; avoid nullable metadata fields |
| No LIKE/GLOB in metadata filters | Low; path matching requires post-join |
| Pre-v1, breaking changes expected | Medium; shadow table schema could change |
| Single maintainer, weekend-only | Medium; supply-chain risk for npm distribution |

---

## 6. Production Readiness

### Maintenance Status (as of March 2026)

- Last stable release: v0.1.6 (November 2024). v0.1.7-alpha stalled.
- June 2025: Alex Garcia confirmed development is weekend-only after sponsorships dried up (issue #226).
- Single dominant maintainer. Community forks exist but none have taken over active development.
- 7,200 GitHub stars, 76 releases. High community interest, uncertain financial sustainability.

Garcia previously built `sqlite-vss` (Faiss-backed), then deprecated it in favor of sqlite-vec. That deprecation was clean, but it demonstrates the pattern.

### npm Distribution

The `sqlite-vec` npm package ships prebuilt binaries as optional dependencies (darwin-arm64, darwin-x64, linux-x64, linux-arm64, win32-x64). Platforms without a prebuilt binary fall back to compilation requiring a C toolchain. This is the same class of risk as the current `hnswlib-node` postinstall rebuild.

### Ecosystem Integrations

Integrated by: LangChain Python, Microsoft Semantic Kernel, LlamaIndex, Datasette, Turso. The Python ecosystem has more mature wrappers; the Node.js story is functional but lower-level.

---

## 7. Recommendation

### Do Not Replace hnswlib-node Today

Three reasons:

1. **Pre-v1 with stalled development.** A confirmed maintenance slowdown, no ANN index shipped after 18+ months on the roadmap, and weekend-only development from a single maintainer represent real supply-chain risk for a distributed npm package.

2. **hnswlib-node is not the actual problem.** The complexity in mdcontext comes from maintaining two separate artifact sets (HNSW binary + BM25 JSON), not from hnswlib-node itself. That is the problem worth solving.

3. **The performance case does not apply at mdcontext scale.** At under 30,000 sections, brute-force is fast enough. So is HNSW. The difference is marginal in either direction.

### When to Revisit

- sqlite-vec ships a stable v1 with a public API stability commitment
- An IVF or ANN index lands and has been stable for 3+ months across Node.js LTS targets
- A second active maintainer joins or a well-funded organization forks
- mdcontext corpus sizes regularly exceed 50,000 sections

### Recommended Short-Term Improvement

Migrate `wink-bm25-text-search` to **SQLite FTS5**. FTS5 is built into SQLite (no additional extension), has been in the SQLite core since 3.9.0 (2015), and is maintained by the SQLite core team indefinitely. This migration:
- Eliminates `bm25.json` and `bm25.meta.json` sidecar files
- Gives better BM25 scoring and Unicode tokenization than wink-bm25
- Uses the same `better-sqlite3` dependency already present
- Enables atomic ingestion transactions across keyword and structural indexes
- Does not require depending on any pre-v1 C extension

Keep hnswlib-node for vector search. Migrate BM25 to FTS5. Consolidate structural indexes (documents, sections, links) to SQLite. This achieves most of the architectural benefit without sqlite-vec's maintenance risk.

---

## Sources

- [asg017/sqlite-vec GitHub](https://github.com/asg017/sqlite-vec)
- [sqlite-vec v0.1.0 stable release post](https://alexgarcia.xyz/blog/2024/sqlite-vec-stable-release/index.html)
- [sqlite-vec metadata filtering release](https://alexgarcia.xyz/blog/2024/sqlite-vec-metadata-release/index.html)
- [sqlite-vec hybrid search with FTS5](https://alexgarcia.xyz/blog/2024/sqlite-vec-hybrid-search/index.html)
- [sqlite-vec Node.js integration guide](https://alexgarcia.xyz/sqlite-vec/js.html)
- [sqlite-vec ANN tracking issue #25](https://github.com/asg017/sqlite-vec/issues/25)
- [sqlite-vec UPSERT issue #127](https://github.com/asg017/sqlite-vec/issues/127)
- [sqlite-vec maintenance concern issue #226](https://github.com/asg017/sqlite-vec/issues/226)
- [sqlite-vec performance issue #186](https://github.com/asg017/sqlite-vec/issues/186)
- [The State of Vector Search in SQLite (Marco Bambini)](https://marcobambini.substack.com/p/the-state-of-vector-search-in-sqlite)
- [vectorlite HNSW-backed SQLite extension](https://github.com/1yefuwang1/vectorlite)
- [Simon Willison on sqlite-vec](https://simonwillison.net/2024/May/3/sqlite-vec/)
- [Simon Willison on sqlite-vec hybrid search](https://simonwillison.net/2024/Oct/4/hybrid-full-text-search-and-vector-search-with-sqlite/)
