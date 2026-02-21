# mdcontext Search & Embeddings Subsystem Review

**Date:** 2026-03-13
**Scope:** `src/embeddings/`, `src/search/`, `src/summarization/`, `src/summarize/`, `src/mcp/server.ts`
**Reviewer:** AI Engineer (Opus 4.6)

---

## Executive Summary

The search and embeddings subsystems in mdcontext form a well-architected retrieval pipeline spanning keyword search (BM25), semantic vector search (HNSW), hybrid fusion (RRF), optional cross-encoder reranking, and two distinct summarization layers. The new batching and OpenAI provider changes (in the current working tree) represent meaningful improvements to token-aware batch splitting. Overall code quality is high with strong Effect-based error modeling. This review identifies 14 findings across correctness, performance, architecture, and missing coverage.

---

## 1. Embedding Provider Design

### 1.1 Abstraction Quality

The `EmbeddingProvider` interface (`src/embeddings/types.ts:20-24`) is minimal and clean:

```typescript
interface EmbeddingProvider {
  readonly name: string
  readonly dimensions: number
  embed(texts: string[], options?: EmbedOptions): Promise<EmbeddingResult>
}
```

The `EmbeddingProviderWithMetadata` extension (`types.ts:30-33`) and `hasProviderMetadata` type guard (`types.ts:39-46`) provide safe runtime narrowing without forcing all providers into a heavier interface. This is a solid discriminated extension pattern.

**Finding 1 (Minor): `embed()` returns `Promise` instead of `Effect`.**
The provider interface uses raw `Promise`, requiring the `wrapEmbedding` helper (`openai-provider.ts:404-421`) at every call site. Since the rest of the codebase is Effect-native, this creates an impedance mismatch. The OpenAI provider already throws typed errors (`ApiKeyInvalidError`, `EmbeddingError`) from within the Promise, which `wrapEmbedding` then re-catches. Making `embed()` return `Effect<EmbeddingResult, ApiKeyInvalidError | EmbeddingError>` would eliminate the wrapper and make error channels explicit.

### 1.2 Provider Constants (`src/embeddings/provider-constants.ts`)

Well organized. The `MODEL_DIMENSIONS` record, `MATRYOSHKA_MODELS` set, and `validateModelDimensions` function form a coherent validation layer. The `inferProviderFromUrl` function (`provider-constants.ts:197-213`) provides a single source of truth for URL-to-provider mapping.

**Finding 2 (Medium): `OPENAI_COMPATIBLE_SAFE_BATCH_TOKENS` is set to 250,000 tokens.**
The comment at line 21 references a "300k hard cap" but the actual OpenAI limit is 8,192 tokens per individual text input and no documented per-request aggregate token limit. The 250k value works as a practical safeguard against slow requests, but the documented justification should be updated to reflect the actual constraint (avoiding timeout on large batch requests) rather than an unverified hard cap.

### 1.3 Extensibility

Adding a new provider requires:
1. Add to `EmbeddingProvider` type in `src/config/schema.ts`
2. Add base URL to `PROVIDER_BASE_URLS` in `provider-constants.ts`
3. Add model dimensions to `MODEL_DIMENSIONS`
4. If the provider uses a non-OpenAI API: implement a new provider class (as `VoyageProvider` does)
5. Add routing in `provider-factory.ts`

The Voyage provider (`voyage-provider.ts`) demonstrates that non-OpenAI providers integrate cleanly. The factory pattern at `provider-factory.ts:135-185` handles both `ConfigService`-backed and direct configuration paths.

### 1.4 API Key Security

Effect's `Redacted<string>` type is used throughout for API key handling (`openai-provider.ts:122,166-194`). Keys are unwrapped only at the point of use (creating the OpenAI client). The `resolveApiKey` function (`openai-provider.ts:167-178`) checks env vars as fallback. This is well implemented.

---

## 2. Batching Strategy (`src/embeddings/batching.ts`)

### 2.1 Algorithm

The `batchTexts` function (`batching.ts:19-75`) implements a greedy bin-packing approach with dual constraints: max texts per batch and max tokens per batch. The algorithm is correct for the greedy single-pass strategy.

Key behaviors:
- **Oversized text isolation** (`batching.ts:52-59`): A single text exceeding the token budget is placed in its own batch. This prevents cascading failures while acknowledging the provider may reject it.
- **Token counting** uses `countTokensApprox` (approximate). The conservative 250k budget provides margin for estimation error.
- **Minimum 1 token** per text (`batching.ts:47`): `Math.max(1, countTokensApprox(text))` prevents zero-length texts from being counted as free.

### 2.2 Test Coverage

The tests (`batching.test.ts`) cover three scenarios: text-count splitting, token-budget splitting, and oversized text isolation. These are the primary cases.

**Finding 3 (Low): Missing edge case tests for batching.**
The following edge cases lack test coverage:
- Empty input array (should return `[]`)
- Single text that exactly equals the token budget
- `maxTextsPerBatch = 1` (every text in its own batch)
- Very large number of small texts (verifying no performance degradation)
- Input containing empty strings

### 2.3 Integration with OpenAI Provider

The `embed` method (`openai-provider.ts:225-307`) calls `batchTexts` at line 235 and processes batches sequentially with progress reporting. The `const batch = [...batchInfo.texts]` at line 246 creates a mutable copy from the readonly array, which is necessary for the OpenAI SDK's type requirements.

**Finding 4 (Medium): No concurrency control for batch processing.**
Batches are processed sequentially in a `for...of` loop (`openai-provider.ts:244-277`). For large corpora with many batches, this is conservative. There is no option for controlled parallelism (e.g., processing 2-3 batches concurrently with a semaphore). For local providers like Ollama that may benefit from concurrency, this leaves performance on the table. The sequential approach is safe for rate-limited cloud APIs.

---

## 3. Vector Search Implementation

### 3.1 HNSW Index (`src/embeddings/vector-store.ts`)

The `HnswVectorStore` class (`vector-store.ts:133-650`) wraps `hnswlib-node` with:
- **Cosine similarity** space (`vector-store.ts:214-215,576-577`)
- **Configurable HNSW parameters**: M (default 16), efConstruction (default 200) at `vector-store.ts:147-149`
- **Dynamic resizing**: `resizeIndex` doubles capacity when needed (`vector-store.ts:238-239`)
- **Namespace support**: Allows multiple embedding indices per project (`vector-store.ts:151-152,169-178`)
- **HNSW parameter mismatch detection** on load (`vector-store.ts:608-622`)

### 3.2 Similarity Metric

The HNSW index uses cosine distance internally. The conversion at `vector-store.ts:289` is correct:
```typescript
const similarity = 1 - distance
```
`hnswlib-node` returns `1 - cosine_similarity` for cosine space, so `1 - distance = cosine_similarity`.

### 3.3 Persistence

Metadata is serialized with MessagePack (`vector-store.ts:463-464`) for compact binary storage. The load path (`vector-store.ts:477-627`) supports both binary and legacy JSON formats with auto-migration. The migration is safe for concurrent access (writes binary, then deletes JSON with error swallowing).

**Finding 5 (Medium): Metadata stores full embedding vectors.**
The `VectorIndex.entries` field (`types.ts:72`) stores the full `VectorEntry` record, which includes the `embedding: readonly number[]` field (`types.ts:63`). Since the HNSW binary index already contains the vectors, storing them again in metadata doubles the storage cost. For a corpus with 10,000 512-dimensional vectors, this adds approximately 20MB of redundant data. The metadata entries are primarily used for mapping HNSW integer indices back to section IDs. The `embedding` field in metadata could be omitted during serialization.

### 3.4 Search Quality Modes

Three quality modes (`types.ts:107-117`) map to efSearch values:
- fast: 64
- balanced: 100
- thorough: 256

These values are reasonable and well documented.

**Finding 6 (Low): `search` and `searchWithStats` share duplicated logic.**
The `search` method (`vector-store.ts:256-316`) and `searchWithStats` method (`vector-store.ts:318-396`) contain nearly identical code. The only difference is that `searchWithStats` tracks below-threshold results. This could be refactored to have `search` delegate to `searchWithStats` with a flag, reducing the maintenance surface.

---

## 4. Search Ranking and Relevance

### 4.1 Heading and File Importance Boost

The heading boost (`types.ts:245-258`) adds 0.05 per matched query term in the heading. File importance boost (`types.ts:230-235`) adds 0.03 for important files (README, index, getting-started, etc.). These are applied additively to similarity scores with a `Math.min(1, ...)` cap.

**Finding 7 (Low): Heading boost uses naive term matching.**
The `calculateHeadingBoost` function (`types.ts:245-258`) splits the query on whitespace and checks substring inclusion in the heading. This means a query "API reference" would boost a heading "API unreferenced issues" because "API" is a substring. Word boundary matching would improve precision. Additionally, common stopwords ("the", "a", "how", etc.) contribute to boost scores without adding relevance signal.

### 4.2 Hybrid Search with RRF (`src/search/hybrid-search.ts`)

The `fusionRRF` function (`hybrid-search.ts:125-240`) correctly implements Reciprocal Rank Fusion with:
- Configurable weights for BM25 and semantic components
- Standard k=60 smoothing constant
- Proper handling of results appearing in both rankings

The `hybridSearch` function (`hybrid-search.ts:261-413`) auto-detects available indices and falls back gracefully. Mode detection is sound.

### 4.3 Cross-Encoder Reranking (`src/search/cross-encoder.ts`)

Uses `Xenova/ms-marco-MiniLM-L-6-v2` (22.7M params) for optional reranking. The implementation uses lazy loading with a singleton pattern and dynamic import of `@huggingface/transformers`.

**Finding 8 (Medium): No rate limiting or backpressure for local cross-encoder.**
The cross-encoder processes all candidate pairs in a single forward pass (`cross-encoder.ts:191-207`). For large `topK` values, this could cause significant memory pressure. The default `topK=20` is reasonable, but there is no validation that prevents users from setting very high values (e.g., 1000) which could OOM on constrained systems.

### 4.4 Query Preprocessing

The `preprocessQuery` function (`types.ts:297-307`) normalizes queries by lowercasing, replacing punctuation with spaces, and collapsing whitespace. This is applied before embedding unless `skipPreprocessing` is set.

**Finding 9 (Low): Unicode handling in query preprocessing.**
The regex `[^\w\s]` at `types.ts:302` uses `\w` which in JavaScript only matches `[a-zA-Z0-9_]`. Non-ASCII word characters (e.g., accented characters, CJK) are replaced with spaces. For internationalized content, this strips meaningful characters. Using Unicode property escapes (`\p{L}`) with the `u` flag would preserve international content.

---

## 5. BM25 Keyword Search (`src/search/bm25-store.ts`)

The BM25 implementation uses `wink-bm25-text-search` with field weights (heading: 2, content: 1). The tokenizer (`bm25-store.ts:53-58`) applies lowercase, splits on non-word chars, and filters tokens under 3 characters.

**Finding 10 (Low): BM25 store is recreated on every search call.**
The `bm25Search` function (`bm25-store.ts:332-346`) creates a new `BM25Store`, loads the index from disk, runs the search, and discards the store. For repeated searches within the same session (e.g., MCP server handling multiple queries), this means re-reading and re-parsing the JSON index file on every call. The hybrid search at `hybrid-search.ts:310` calls `bm25Search` which triggers a full load. Caching the loaded store across searches within the same process would improve latency.

### 5.1 Boolean Query Parser (`src/search/query-parser.ts`)

The recursive descent parser supports AND, OR, NOT, quoted phrases, and grouping. The grammar is well documented at `query-parser.ts:108-115`. Implicit AND between adjacent terms (`query-parser.ts:164`) is a practical UX choice.

### 5.2 Fuzzy Search (`src/search/fuzzy-search.ts`)

Levenshtein distance implementation at `fuzzy-search.ts:47-73` is the standard O(mn) dynamic programming approach. This is acceptable for short query terms but would be slow for long inputs. The `isFuzzyMatch` fast-path length check at `fuzzy-search.ts:84` helps.

---

## 6. Summarization Pipeline

### 6.1 Two Summarization Modules

**`src/summarize/`** provides local, deterministic document summarization. It parses markdown files, computes section token counts, and produces compressed summaries using extractive heuristics (sentence scoring based on presence of colons, capitalization, emphasis markers). No LLM calls involved. The `summarizeFile` function is used by the MCP server's `md_context` tool.

**`src/summarization/`** provides AI-powered summarization of search results. It supports CLI-based providers (Claude Code, Copilot, Aider, etc.) and API-based providers (DeepSeek, OpenAI, Anthropic). The pipeline (`src/summarization/pipeline.ts`) handles cost estimation, user consent for paid operations, and streaming.

**Finding 11 (Architecture): Two distinct summarization concerns with overlapping names.**
The `src/summarize/` module handles document compression (extractive summarization for context windows). The `src/summarization/` module handles AI-generated summaries of search results (abstractive summarization via LLM). Both are valid and serve different purposes. The naming creates potential confusion: `summarize/summarizer.ts` vs `summarization/pipeline.ts`. The MCP server imports from `src/summarize/summarizer.js` (line 34) for the `md_context` tool. Consider renaming `src/summarize/` to something like `src/context-compression/` or documenting the distinction more prominently.

### 6.2 Extractive Summarizer Quality (`src/summarize/summarizer.ts`)

The sentence scoring heuristic (`summarizer.ts:149-162`) uses four signals:
- Colon presence (definitions): +2
- Capital letter start: +1
- Medium length (50-200 chars): +1
- Emphasis/code markers: +1

This is a reasonable extractive approach for documentation. The orphan rescue algorithm during truncation (`summarizer.ts:329-356`) is a thoughtful addition that preserves child sections even when parent sections are too large to include.

---

## 7. MCP Server Tools (`src/mcp/server.ts`)

### 7.1 Exposed Tools

Seven tools are registered:

| Tool | Function | Search Type |
|------|----------|-------------|
| `md_search` | Semantic search | Vector (HNSW) |
| `md_keyword_search` | Keyword search | Metadata filtering |
| `md_context` | Document context | Extractive summarization |
| `md_structure` | File outline | Parser |
| `md_index` | Build/rebuild index | Indexing |
| `md_links` | Outgoing links | Graph |
| `md_backlinks` | Incoming links | Graph |

**Finding 12 (Medium): MCP server does not expose hybrid search or content search.**
The `md_search` tool (`server.ts:44-72`) only uses `semanticSearch`. The `md_keyword_search` tool (`server.ts:114-147`) uses heading/metadata filtering via `search()`, not `searchContent()` or BM25. The hybrid search capability (`hybrid-search.ts`) and the content search with boolean operators (`searcher.ts:212-488`) are only available via CLI, not MCP. AI agents cannot access the most capable search mode (hybrid with RRF) through the MCP interface.

**Finding 13 (Medium): MCP `md_search` swallows typed errors into string messages.**
The error handling at `server.ts:222-224` uses `Effect.catchAll` to convert all errors into `[{ error: e.message }]`. This loses the structured error information (e.g., `DimensionMismatchError` with its `corpusDimensions`, `providerDimensions` fields). The MCP protocol supports structured error responses. Preserving error types would allow AI agents to take corrective action (e.g., rebuilding embeddings when dimensions mismatch).

---

## 8. Performance Considerations

### 8.1 Caching

- **File content cache** in `addContextLinesToResults` (`semantic-search.ts:601`): Per-query `Map<string, string>` avoids re-reading files within a single search. Discarded after the search completes.
- **BM25 index**: No cross-query caching. Re-loaded from disk on every search call.
- **HNSW index**: Loaded once per search call via `vectorStore.load()`. No process-level cache.
- **Cross-encoder model**: Singleton with lazy loading. Persists across queries.

### 8.2 Memory Usage

**Finding 14 (Medium): No memory management for large HNSW indices.**
The HNSW index stores all vectors in memory after `load()`. For large corpora (100k+ sections with 512-dimensional vectors), this could consume 200MB+. The `ensureIndex` method initializes with space for 10,000 items and doubles on resize. There is no mechanism to cap memory usage or use memory-mapped files. For the intended use case (project-level documentation), this is unlikely to be a problem. For very large knowledge bases, this could become an issue.

### 8.3 Lazy Loading

The OpenAI client is instantiated in the `OpenAIProvider` constructor. The HNSW index is loaded on-demand. The cross-encoder model loads on first use. These are appropriate lazy loading patterns.

---

## 9. API Rate Limiting and Retry Logic

The OpenAI SDK client is configured with `maxRetries: 2` at `openai-provider.ts:130`. The SDK handles retries internally with exponential backoff for 429 and 5xx responses. This is the correct approach for the OpenAI client.

The error classification at `openai-provider.ts:314-373` properly distinguishes RateLimit, QuotaExceeded, Network, ModelError, and Unknown categories. Authentication errors are caught separately at `openai-provider.ts:280-285` and converted to `ApiKeyInvalidError`.

There is no application-level rate limiter or token bucket for controlling request frequency to external APIs. For batch embedding of large corpora, the sequential batch processing serves as implicit rate limiting. This is adequate given the SDK's built-in retry logic.

---

## 10. HyDE Implementation (`src/embeddings/hyde.ts`)

The HyDE (Hypothetical Document Embeddings) implementation is clean. The `shouldUseHyde` function (`hyde.ts:235-264`) provides heuristic detection for queries that would benefit from expansion. The `generateHypotheticalDocument` function (`hyde.ts:110-180`) generates a hypothetical document passage using an LLM, which is then embedded for similarity search.

The LLM pricing data at `hyde.ts:85-90` is hardcoded, unlike the embedding pricing which is loaded from `pricing.json`. This is a minor inconsistency.

---

## Findings Summary

| # | Severity | Area | Finding |
|---|----------|------|---------|
| 1 | Minor | Provider interface | `embed()` returns Promise instead of Effect |
| 2 | Medium | Batching | OPENAI_COMPATIBLE_SAFE_BATCH_TOKENS documentation references unverified hard cap |
| 3 | Low | Batching tests | Missing edge case tests (empty input, exact boundary, single-item batches) |
| 4 | Medium | Batch processing | No option for concurrent batch processing |
| 5 | Medium | Vector store | Metadata stores redundant embedding vectors |
| 6 | Low | Vector store | search and searchWithStats contain duplicated logic |
| 7 | Low | Ranking | Heading boost uses naive substring matching without word boundaries |
| 8 | Medium | Cross-encoder | No validation cap on topK to prevent memory pressure |
| 9 | Low | Query preprocessing | Unicode non-ASCII characters stripped by \w regex |
| 10 | Low | BM25 | Store recreated and re-loaded from disk on every search call |
| 11 | Architecture | Summarization | Two modules with overlapping naming (summarize vs summarization) |
| 12 | Medium | MCP server | Hybrid search and content search not exposed via MCP tools |
| 13 | Medium | MCP server | Typed errors flattened to strings, losing structured error data |
| 14 | Medium | Memory | No memory management for large HNSW indices |

---

## File Reference Index

| File | Lines | Purpose |
|------|-------|---------|
| `src/embeddings/types.ts` | 360 | Core types: EmbeddingProvider, VectorEntry, SemanticSearchOptions, query preprocessing, heading boost |
| `src/embeddings/openai-provider.ts` | 422 | OpenAI-compatible embedding provider with batching and error classification |
| `src/embeddings/batching.ts` | 75 | Token-aware batch splitting for embedding API calls |
| `src/embeddings/provider-constants.ts` | 213 | Model dimensions, Matryoshka support, provider URLs, port detection |
| `src/embeddings/provider-factory.ts` | 226 | Factory for creating providers from config or direct parameters |
| `src/embeddings/vector-store.ts` | 709 | HNSW vector store with namespaced persistence |
| `src/embeddings/semantic-search.ts` | 1271 | Semantic search orchestration: embedding, vector search, context lines |
| `src/embeddings/hyde.ts` | 265 | HyDE query expansion via LLM-generated hypothetical documents |
| `src/embeddings/voyage-provider.ts` | ~250 | Voyage AI native provider |
| `src/embeddings/provider-errors.ts` | ~400 | Provider-specific error detection and user-friendly messages |
| `src/search/hybrid-search.ts` | 449 | RRF fusion of semantic + BM25 results with optional reranking |
| `src/search/searcher.ts` | 725 | Keyword search, content search with boolean operators, context generation |
| `src/search/bm25-store.ts` | 367 | BM25 index using wink-bm25-text-search |
| `src/search/query-parser.ts` | 320 | Boolean query parser (AND, OR, NOT, phrases, grouping) |
| `src/search/fuzzy-search.ts` | 273 | Stemming (Porter) and Levenshtein fuzzy matching |
| `src/search/cross-encoder.ts` | 407 | Cross-encoder reranking with Xenova/ms-marco-MiniLM |
| `src/search/path-matcher.ts` | 34 | Glob-like path matching utility |
| `src/summarize/summarizer.ts` | 598 | Extractive document summarization with token budgets |
| `src/summarization/pipeline.ts` | 232 | AI-powered search result summarization pipeline |
| `src/summarization/types.ts` | 185 | Summarization module types (CLI and API providers) |
| `src/mcp/server.ts` | 613 | MCP server exposing 7 tools for AI agent integration |
