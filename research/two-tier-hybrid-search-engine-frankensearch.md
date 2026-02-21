---
title: "frankensearch: Two-Tier Hybrid Search Engine for Rust"
type: research
tags: [hybrid-search, rrf, two-tier, vector-search, tantivy, bm25, simd, fsvi, embedding, progressive-search, rust]
summary: "Deep architecture review of frankensearch, a 263K-line Rust workspace (12 crates) implementing progressive two-tier hybrid search: sub-ms initial results via potion-128M + BM25/RRF fusion, quality refinement via MiniLM-L6-v2 score blending. Custom FSVI binary format with f16 quantization and SIMD dot products. Used by CASS as its search engine."
status: active
source: github-researcher
confidence: high
created: 2026-04-24
updated: 2026-04-24
---

## Executive Summary

frankensearch (51 stars, by Jeffrey Emanuel / Dicklesworthstone) is a Rust workspace providing two-tier progressive hybrid search. It combines Tantivy BM25 lexical search with dual-model semantic vector search (fast: potion-128M at 256d in ~0.57ms, quality: MiniLM-L6-v2 at 384d in ~128ms), fused via Reciprocal Rank Fusion. The system delivers results in two phases: an immediate initial set (~15ms) followed by quality-refined rankings (~150ms). It uses a custom binary vector format (FSVI) with f16 quantization and SIMD dot products, memory-mapped I/O, and optional HNSW ANN acceleration. The project is the extracted search engine that CASS depends on and also ships as a standalone CLI (`fsfs`) for indexing and searching local codebases.

## Architecture

### Workspace Structure (12 Crates, 263K Lines)

| Crate | LOC | Role |
|---|---|---|
| `frankensearch-fsfs` | 90K | Standalone CLI/TUI product (`fsfs`): indexing, searching, watch mode, streaming output |
| `frankensearch-fusion` | 31K | RRF fusion, two-tier score blending, progressive search orchestration (`TwoTierSearcher`) |
| `frankensearch-ops` | 34K | Fleet observability / control-plane TUI for multi-host deployments |
| `frankensearch-core` | 28K | Shared contracts: traits, errors, config, query canonicalization/classification, telemetry types, IR eval metrics |
| `frankensearch-embed` | 16K | Embedder implementations (hash, Model2Vec/potion, FastEmbed/MiniLM), model cache/download, batch coalescing |
| `frankensearch-index` | 16K | FSVI binary format, SIMD vector search, HNSW ANN, WAL, MRL, two-tier index container |
| `frankensearch-storage` | 16K | FrankenSQLite metadata persistence, content-hash dedup, embedding job queue |
| `frankensearch-durability` | 8K | RaptorQ FEC repair/protection for index files, corruption detection |
| `frankensearch-tui` | 7K | Shared TUI framework (screens, input, themes, replay) |
| `frankensearch-lexical` | 4K | Tantivy BM25 schema, tokenizer, query parsing; includes `cass_compat` module |
| `frankensearch-rerank` | 3K | FlashRank / ONNX cross-encoder reranking |
| `frankensearch` (facade) | 1.3K | Unified re-export surface for library consumers |

### Dependency Flow

```
frankensearch-core (traits, types, errors)
  -> frankensearch-embed (embedder impls)
  -> frankensearch-index (FSVI vector store)
  -> frankensearch-lexical (Tantivy BM25)
  -> frankensearch-fusion (RRF + orchestration)
  -> frankensearch-rerank (cross-encoder)

frankensearch-fusion depends on: embed, index, optional lexical/rerank
frankensearch (facade) re-exports: core, embed, index, fusion, optional lexical/rerank/storage/durability
frankensearch-fsfs depends on: core, tui (the product binary)
```

### Data Flow: Query Path

```
Query
  -> Canonicalize (Unicode NFC, strip noise, preserve intent)
  -> Classify (identifier | short-keyword | natural-language) -> adaptive budgets
  -> Phase 1 (parallel):
       Fast Embed (potion-128M, 256d, ~0.57ms) -> Vector top-k (FSVI brute-force or ANN)
       Tantivy BM25 search (if lexical feature enabled)
  -> RRF Fusion (K=60, rank-based, model-agnostic)
  -> Emit SearchPhase::Initial (~15ms)
  -> Phase 2 (unless fast_only):
       Quality Embed (MiniLM-L6-v2, 384d, ~128ms) with timeout
       Score blend: alpha * quality + (1-alpha) * fast (alpha=0.7 default)
       Optional cross-encoder rerank (FlashRank)
  -> Emit SearchPhase::Refined or SearchPhase::RefinementFailed (~150ms)
```

### Data Flow: Indexing Path

```
Documents
  -> Canonicalize
  -> Embed with fast-tier model
  -> Write vectors to FSVI file (vector.fast.idx)
  -> Optionally embed with quality-tier model -> vector.quality.idx
  -> Optionally index text with Tantivy for BM25
  -> Store metadata in FrankenSQLite
```

## Key Patterns

### 1. Progressive Two-Phase Search with Graceful Degradation

The central design principle. Phase 1 delivers useful results immediately; Phase 2 improves ranking but is explicitly optional and timeout-bounded. The three-variant `SearchPhase` enum (`Initial`, `Refined`, `RefinementFailed`) gives callers a clean protocol for handling each case. If the quality model fails, crashes, or times out, the system falls back to initial results rather than erroring.

This is implemented as an async callback protocol in `TwoTierSearcher::search()`, which fires `on_phase` at most twice.

### 2. Reciprocal Rank Fusion (RRF)

`crates/frankensearch-fusion/src/rrf.rs`

Fusion is rank-based rather than score-based, which avoids the fragile problem of calibrating scores across BM25 (unbounded) and cosine similarity ([0,1]). The formula: `score(doc) = sum over sources of 1/(K + rank + 1)`, K=60 default.

Key implementation details:
- Uses `ahash::AHashMap` for accumulation (faster than std HashMap)
- Deterministic 4-level tie-breaking: RRF score desc, in_both_sources (true preferred), lexical_score desc, doc_id ascending
- Pagination-aware: uses `select_nth_unstable_by` to avoid full-sorting when only a small window is needed
- Also supports optional graph-ranked channel with weighted contribution

### 3. FSVI Binary Vector Format

`crates/frankensearch-index/src/lib.rs`

Custom binary format instead of using an off-the-shelf vector database:
- Header: magic bytes (`FSVI`), version, embedder ID, dimension, quantization mode
- Record table: doc_id_hash (u64) + doc_id offset/length + flags (tombstone bit)
- String table: concatenated UTF-8 doc IDs
- Vector slab: 64-byte aligned, f16 or f32 quantized vectors

Design rationale: mmap-friendly, zero-copy access patterns, minimal overhead. The 64-byte alignment matches cache lines for SIMD operations.

### 4. SIMD Dot Products

`crates/frankensearch-index/src/simd.rs`

Uses the `wide` crate for portable SIMD (`f32x8` lanes). Four kernel variants:
- `dot_product_f32_f32`: full precision
- `dot_product_f16_f32`: stored f16, query f32 (primary path)
- `dot_product_f16_bytes_f32`: zero-copy from raw bytes
- `dot_product_f32_bytes_f32`: zero-copy from raw bytes

All use chunks_exact(8) for the SIMD path with a scalar remainder tail. NaN-safe via total_cmp ordering.

### 5. Two-Tier Index with Alignment Mapping

`crates/frankensearch-index/src/two_tier.rs`

`TwoTierIndex` wraps a fast-tier and optional quality-tier FSVI file. When both exist, it builds a `QualityAlignment` map to translate fast-tier positions to quality-tier positions (handles mismatched doc sets, tombstones). This lets quality scoring look up the right vector even when indices were built independently or have diverged.

### 6. Matryoshka Representation Learning (MRL)

`crates/frankensearch-index/src/mrl.rs`

For MRL-trained models, initial vector scan uses only the first N dimensions (e.g., 64 of 256), then rescores the top-k candidates at full dimensionality. Break-even at ~36 vectors; 6x speedup on 10K vectors with 64-dim truncated scan.

### 7. Feature-Gated Compilation

Extensive use of Cargo feature flags to control compilation scope:
- `hash` (default): zero-dep hash embedder only
- `model2vec`: potion-128M fast tier
- `fastembed`: MiniLM quality tier
- `lexical`: Tantivy BM25
- `rerank`: FlashRank cross-encoder
- `ann`: HNSW approximate nearest neighbors
- `storage`: SQLite metadata
- `durability`: RaptorQ FEC self-healing
- Composite flags: `semantic`, `hybrid`, `persistent`, `durable`, `full`, `full-fts5`

This means library consumers pay only for what they use. The default feature set compiles with zero model downloads.

### 8. Async Runtime: asupersync (Not Tokio)

The entire workspace uses `asupersync`, the author's own structured concurrency runtime with capability contexts (`Cx`). All async functions take `&Cx` as their first parameter, which provides cancellation, timeouts, and scoped task lifetimes. This avoids hard-coupling to Tokio.

### 9. Write-Ahead Log (WAL) for Vector Updates

`crates/frankensearch-index/src/wal.rs`

New vectors are buffered in a WAL before being compacted into the main FSVI file. During search, WAL entries are merged into results on the fly (ANN path merges WAL entries post-search with re-sort). Handles NaN-scored WAL entries by filtering them at search time.

### 10. IR Quality Evaluation

`crates/frankensearch-core/src/metrics_eval.rs`

Built-in IR metrics: nDCG@K, MRR, Recall@K, MAP@K. Includes bootstrap confidence intervals and cross-run stability verification. This is used in the benchmark harness for evidence-driven tuning.

## Relationship to CASS

frankensearch is **the search engine that CASS uses**. The relationship is direct:

1. **frankensearch-lexical has a `cass_compat` module** (`crates/frankensearch-lexical/src/cass_compat.rs`): provides a full CASS-compatible Tantivy schema (v7), custom CassTokenizer (CJK bigrams, hyphen-joined tokens, edge n-grams), and query building functions. This is the most heavily optimized module in the lexical crate.

2. **CASS's Cargo.toml references `frankensearch`** as a dependency (confirmed in the CASS review: `frankensearch` appears in `key dependencies` and CASS uses `frankensearch` for its Tantivy schema, field types, tokenizer registration, query building, vector index, and RRF fusion).

3. **Extraction history**: frankensearch was extracted from CASS as a reusable library. The `cass_compat` module preserves backward compatibility with CASS's Tantivy index format so existing CASS indexes remain readable. The recent git history shows active optimization of `cass_compat` (custom tokenizer replacing regex, parallel doc batching, prefix field optimization).

4. **Shared sibling crates**: Both projects use the same franken-* ecosystem (frankensqlite, ftui, asupersync, franken_agent_detection).

5. **fsfs as standalone product**: frankensearch also ships `fsfs`, a standalone CLI for indexing and searching local codebases. This makes the search engine usable independently of CASS, for any local file search use case.

## Relevance to Helioy

### Direct Applicability

1. **attention-matters**: AM's retrieval layer currently uses cosine similarity on S3 hypersphere embeddings. frankensearch's two-tier approach is directly relevant: a fast initial retrieval pass (which AM already does) followed by quality refinement is exactly the progressive delivery pattern. The RRF fusion of lexical + semantic signals could improve AM's recall.

2. **context-matters**: CM stores structured context entries and retrieves them via `cx_recall`. Adding hybrid search (BM25 for exact keyword matches + semantic for intent) would improve retrieval quality. The FSVI format and f16 quantization pattern could inform a lighter-weight embedding store for CM entries.

3. **markdown-matters**: MDM already does markdown indexing and search. frankensearch's Tantivy integration with edge n-grams, title boost, and hybrid fusion would be a direct upgrade path. The `cass_compat` tokenizer (CJK support, hyphen-joined tokens) solves real problems for code-adjacent markdown.

4. **fmm (frontmatter-matters)**: Code structural intelligence could benefit from semantic search over symbol names and documentation. The MRL pattern (truncated scan + rescore) is useful for keeping search fast in large codebases.

### Patterns Worth Adopting

| Pattern | Where in Helioy |
|---|---|
| Progressive two-phase search with graceful degradation | AM recall, CM recall |
| RRF fusion of lexical + semantic signals | Any retrieval path that currently uses only one signal |
| f16 quantization + SIMD for vector operations | AM's hypersphere operations, any embedding-heavy path |
| Feature-gated compilation for optional capabilities | All Rust crates (already used in some) |
| WAL for incremental vector updates | AM's persistence layer (currently batch writes) |
| MRL truncated scan for large index search | AM at scale |

### Anti-Patterns to Avoid

- The codebase is 263K lines for what is fundamentally a search library. Much of this is operational infrastructure (ops TUI, control plane, telemetry transport, fleet management, durability) that goes beyond what Helioy components need. Extract patterns, not volume.
- `asupersync` as a custom runtime is a coupling risk. Helioy should continue using Tokio for async runtime.
- The FSVI format is bespoke. For Helioy's vector storage needs, using an established format or in-memory approach may be more pragmatic unless FSVI's specific properties (mmap, f16, 64-byte alignment) are needed.

## Dependencies

| Dependency | Version | Role |
|---|---|---|
| tantivy | 0.25.0 | BM25 full-text search |
| fastembed | 5.11.0 | ONNX Runtime wrapper for MiniLM-L6-v2 embedding |
| safetensors | 0.7.0 | Static token embedding matrix loading (Model2Vec) |
| tokenizers | 0.22.2 | HuggingFace BPE tokenizer for potion-128M |
| hnsw_rs | 0.3 | HNSW approximate nearest neighbor index |
| half | 2.4 | f16 type for vector quantization |
| wide | 1.1.1 | Portable SIMD (f32x8) |
| memmap2 | 0.9 | Memory-mapped file I/O for FSVI |
| ort | 2.0.0-rc.11 | ONNX Runtime for cross-encoder reranking |
| rayon | 1.10 | Data parallelism for CPU-bound vector ops |
| asupersync | 0.3.1 | Author's structured concurrency runtime (not Tokio) |
| ahash | 0.8 | Fast non-cryptographic hashing for hot-path maps |
| crc32fast | 1 | Index integrity checksums |
| ftui-* | 0.2.1 | Author's Ratatui fork for TUI rendering |

## Performance Reference

| Operation | Typical Latency |
|---|---|
| Hash embedding (FNV-1a, 256d) | ~11 us |
| Fast model embedding (potion-128M, 256d) | ~0.57 ms |
| Quality model embedding (MiniLM-L6-v2, 384d) | ~128 ms |
| Vector search (10K docs, top-10, brute-force) | ~2 ms |
| RRF fusion (500 + 500 candidates) | ~1 ms |
| Phase 1 initial delivery | < 15 ms target |
| Phase 2 refined delivery | ~150 ms target |

## Sources Consulted

- `README.md` (32K, comprehensive)
- `docs/architecture/overview.md` (contributor architecture map)
- `Cargo.toml` (workspace config, 12 crates)
- `crates/frankensearch-core/src/lib.rs` (trait/type surface)
- `crates/frankensearch-core/src/traits.rs` (Embedder, LexicalSearch, Reranker contracts)
- `crates/frankensearch-core/src/config.rs` (TwoTierConfig)
- `crates/frankensearch-index/src/lib.rs` (FSVI format spec)
- `crates/frankensearch-index/src/two_tier.rs` (TwoTierIndex, 1990 lines)
- `crates/frankensearch-index/src/simd.rs` (SIMD dot product kernels)
- `crates/frankensearch-index/src/mrl.rs` (Matryoshka search)
- `crates/frankensearch-fusion/src/rrf.rs` (RRF implementation, 1141 lines)
- `crates/frankensearch-fusion/src/blend.rs` (two-tier score blending)
- `crates/frankensearch-fusion/src/searcher.rs` (TwoTierSearcher orchestrator)
- `crates/frankensearch-embed/src/lib.rs` (embedder stack)
- `crates/frankensearch-embed/src/model2vec_embedder.rs` (potion-128M loader)
- `crates/frankensearch-lexical/src/lib.rs` (Tantivy BM25 integration)
- `crates/frankensearch-lexical/src/cass_compat.rs` (CASS schema compatibility)
- `frankensearch/src/lib.rs` (facade crate, re-exports)
- `crates/frankensearch-fsfs/src/main.rs` (CLI entry point)
- Git log (50 recent commits)

## Open Questions

1. **Query expansion (PRF)**: The `TwoTierSearcher` references `prf_expand` (pseudo-relevance feedback) but this was not deeply reviewed. Could be relevant for Helioy retrieval quality.
2. **Federated search**: The facade exports `FederatedSearcher` and `FederatedFusion` for multi-index search. Not explored in depth. Could be relevant if Helioy components maintain separate indices.
3. **Conformal calibration**: The searcher includes `ConformalSearchCalibration` and `AdaptiveConformalState` for runtime score calibration. Advanced pattern worth understanding for production search quality.
4. **Circuit breaker**: Quality-tier search has a circuit breaker (`CircuitBreaker`) that can trip if quality refinement fails too often. Good operational pattern.
5. **asupersync internals**: The author's custom async runtime. Not evaluated for correctness or maturity vs Tokio.
