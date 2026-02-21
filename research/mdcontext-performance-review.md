# mdcontext Performance Review

**Date:** 2026-03-13
**Reviewer:** performance-engineer
**Codebase:** `/Users/alphab/Dev/LLM/DEV/helioy/mdcontext`
**Commit:** main branch (post `src/embeddings/batching.ts` addition)

---

## Executive Summary

mdcontext is a well-structured markdown indexing and semantic search system. The core architecture makes sound choices: incremental change detection, HNSW for ANN search, BM25 for keyword retrieval, and RRF fusion. Several specific implementation patterns introduce measurable overhead that compounds at scale. This review identifies eight bottlenecks ranked by impact severity, with concrete remediation paths for each.

**Performance posture: Good for corpora under ~5,000 files. Degrades predictably beyond that threshold due to sequential I/O patterns and full-index JSON loads.**

---

## System Architecture Overview

```
Indexing pipeline:
  walkDirectory (recursive, sequential)
    -> hash check (incremental skip)
    -> parse (remark/unified, whole-file)
    -> save (JSON files, pretty-printed)

Search paths:
  keyword:  load JSON indexes -> linear scan OR BM25 (in-memory)
  semantic: load HNSW index (msgpack) -> kNN search -> boost -> rerank
  hybrid:   semantic + keyword in sequence -> RRF fusion

Storage backend:
  - .mdcontext/indexes/documents.json  (DocumentIndex)
  - .mdcontext/indexes/sections.json   (SectionIndex)
  - .mdcontext/indexes/links.json      (LinkIndex)
  - .mdcontext/indexes/bm25.json       (wink-bm25 export)
  - .mdcontext/embeddings/<namespace>/ (HNSW .bin + msgpack .bin)
```

---

## Bottleneck Analysis

### BOTTLENECK 1 (Critical): Sequential file reading during indexing

**Severity:** High
**File:** `src/index/indexer.ts`, lines 279-303

**Finding:**
`buildIndex` processes files in a strict serial `for` loop. For each file it performs two sequential async I/O calls: `fs.readFile` and `fs.stat`. On a 5,000-file corpus these are 10,000 serial I/O operations.

```typescript
// Current pattern - strictly sequential
for (let fileIndex = 0; fileIndex < files.length; fileIndex++) {
  const [content, stats] = yield* Effect.promise(() =>
    Promise.all([fs.readFile(filePath, 'utf-8'), fs.stat(filePath)]),
  )
  // ... process
  yield* processFile
}
```

The outer loop itself is sequential (each `yield*` awaits). Node.js's async I/O can handle many concurrent operations, but none of that concurrency is exploited here.

**Impact:** On a warm filesystem (cached), expect ~1-3ms per file for stat+read. 5,000 files = 5-15 seconds of I/O time that could be parallelized to sub-second.

**Recommendation:** Batch files into concurrent groups using `Effect.all` with concurrency limits (e.g., 50 concurrent). Use a worker pool pattern to bound memory while maximizing throughput.

---

### BOTTLENECK 2 (Critical): Full JSON index reload on every search

**Severity:** High
**File:** `src/search/searcher.ts`, lines 112-115; `src/index/storage.ts`, lines 177-87

**Finding:**
Every call to `search`, `searchContent`, and `searchWithContent` calls `loadDocumentIndex` and `loadSectionIndex`, which each do a full `fs.readFile` + `JSON.parse` on the index files. The section index in particular can be large (one entry per section across all documents).

For a corpus of 5,000 documents with an average of 10 sections each, the section index JSON is ~50,000 objects. `JSON.parse` on that is not negligible, and it happens on every MCP tool invocation.

```typescript
// Called on every search - no in-process caching
export const search = (rootPath, options) =>
  Effect.gen(function* () {
    const storage = createStorage(rootPath)
    const docIndex = yield* loadDocumentIndex(storage)
    const sectionIndex = yield* loadSectionIndex(storage)
    // ...
  })
```

`writeJsonFile` serializes with `JSON.stringify(data, null, 2)` (pretty-printed), which enlarges the file size by 30-40% and slows both write and read.

**Impact:** At 50k sections, the JSON parse alone takes ~200-400ms per search request in JavaScript. This is the dominant search latency factor for users who do not use semantic (HNSW) search.

**Recommendation:**
1. Introduce an in-process module-level cache keyed by `(rootPath, mtime)`. Check mtime before re-parsing.
2. Switch to compact `JSON.stringify(data)` (no pretty-print) for index files. Pretty-printing is for human debugging; these files are machine-read.
3. Consider MessagePack for document/section indexes (already used for vector metadata).

---

### BOTTLENECK 3 (High): Sequential embedding file reading during `buildEmbeddings`

**Severity:** High
**File:** `src/embeddings/semantic-search.ts`, lines 454-497

**Finding:**
`buildEmbeddings` reads file contents in a serial `for` loop before batching them for the embedding API:

```typescript
for (let fileIndex = 0; fileIndex < docPaths.length; fileIndex++) {
  const fileContentResult = yield* Effect.promise(() =>
    fs.readFile(filePath, 'utf-8'),
  )
  // ...
}
```

This is the same sequential I/O problem as bottleneck 1, specific to the embedding pipeline. For a 2,000-document corpus this loop can take 2-5 seconds before the first API call is made.

**Recommendation:** Parallelize file reads using `Effect.all` with concurrency. Since the content is only needed to extract section text, consider streaming reads for very large files.

---

### BOTTLENECK 4 (High): No retry or backoff on embedding API rate limits

**Severity:** High
**File:** `src/embeddings/openai-provider.ts`, lines 225-307

**Finding:**
The `embed` method processes batches sequentially but does not implement any retry logic. When the OpenAI API returns a 429 rate limit error (or transient network errors), the entire embedding build fails immediately:

```typescript
// classifyError correctly identifies RateLimit, but no retry follows
throw new EmbeddingError({
  reason: this.classifyError(error),
  // ...
})
```

For large corpora where batches may span minutes, this means a single transient API error destroys all progress.

**Recommendation:** Implement exponential backoff with jitter for `RateLimit` and `Network` error classes. A max of 5 retries with 1s/2s/4s/8s/16s delays handles virtually all transient errors. Progress should be checkpointable so a retry does not re-embed already-processed batches.

---

### BOTTLENECK 5 (Medium): `countTokensApprox` is computationally expensive

**Severity:** Medium
**File:** `src/utils/tokens.ts`, lines 49-166

**Finding:**
The approximate token counter runs 8+ separate regex passes over the full text content of every section. This function is called:
- During indexing for every section's metadata
- During embedding batch construction (`batchTexts`) for every text

The function is 118 lines of regex and arithmetic. For a section with 5,000 characters it creates multiple intermediate arrays from `match()` calls, then discards them.

```typescript
const codeBlockMatches = text.match(/```[\s\S]*?```/g) || []
let workingText = text
for (const block of codeBlockMatches) {
  // ... replace in workingText on each block
  workingText = workingText.replace(block, '')  // O(n) string replace in a loop
}
// Similar loops for inline code, paths, punctuation
```

The repeated `string.replace` inside loops is O(n * m) where n is text length and m is match count. For code-heavy documents this is significant.

**Impact:** Estimated 10-50ms per large section. With 50,000 sections this is 500ms to 2.5 seconds of CPU time during index builds.

**Recommendation:**
1. Replace sequential `string.replace` loops with a single-pass state machine or a combined regex with groups.
2. Cache token counts in the section index (already done for `tokenCount`), but ensure the batcher reads cached counts rather than recomputing from raw text.
3. For `batchTexts`, the approximation only needs to be within 20% accurate. A simpler `text.length / 4` estimate (already used in `summarization/cost.ts`) may be sufficient for batch sizing decisions.

---

### BOTTLENECK 6 (Medium): `buildIndex` uses an O(n) array scan for broken link deduplication

**Severity:** Medium
**File:** `src/index/indexer.ts`, lines 449-455

**Finding:**

```typescript
const brokenLinks: string[] = [...linkIndex.broken]
// ...
if (!mutableDocuments[target] && !brokenLinks.includes(target)) {
  brokenLinks.push(target)  // O(n) linear scan on every check
}
```

`brokenLinks.includes(target)` is a linear array scan. For a corpus with many broken links this is O(links * broken_links) = O(n^2).

**Recommendation:** Replace `brokenLinks: string[]` with `brokenLinks: Set<string>`. The Set is converted to an array only when serializing. This makes the deduplication check O(1).

---

### BOTTLENECK 7 (Medium): Watcher triggers full re-index on any file change

**Severity:** Medium
**File:** `src/index/watcher.ts`, lines 100-116

**Finding:**
The file watcher debounces changes and then calls the full `buildIndex(resolvedRoot, options)` on every trigger. Although `buildIndex` implements change detection (hash + mtime), it must still:
- Walk the entire directory tree
- Call `fs.stat` on every file
- Load all three JSON indexes from disk

For a large corpus, this means a single file save triggers 5,000+ stat calls plus full JSON deserialization.

```typescript
const scheduleReindex = () => {
  debounceTimer = setTimeout(async () => {
    // Full re-index of entire corpus
    const result = await Effect.runPromise(buildIndex(resolvedRoot, options))
  }, debounceMs)
}
```

**Recommendation:** Track the set of changed paths from chokidar events and pass them as a `changedPaths` option to `buildIndex`. The indexer already supports per-file processing; it just needs to skip the directory walk when specific paths are provided. This reduces a watcher-triggered index from O(corpus) to O(changed_files).

---

### BOTTLENECK 8 (Low-Medium): `semanticSearch` loads the HNSW index on every call

**Severity:** Low-Medium
**File:** `src/embeddings/semantic-search.ts`, lines 752-765

**Finding:**
Each call to `semanticSearch` creates a new `HnswVectorStore` instance and calls `vectorStore.load()`, which reads the binary HNSW file from disk. The HNSW index for a 50,000-section corpus at 1536 dimensions is ~300MB of binary data.

```typescript
const vectorStore = createNamespacedVectorStore(...)
const loadResult = yield* vectorStore.load()  // Full disk read on every search
```

In an MCP server context where the server process stays alive between requests, this is a critical inefficiency. The HNSW index is immutable between embedding rebuilds.

**Recommendation:** Implement a module-level singleton cache for the loaded `HnswVectorStore`, keyed by namespace path. Invalidate the cache when `buildEmbeddings` is called. In the MCP server, this converts the 300MB disk read into an in-memory lookup for all searches after the first.

---

## Storage Layer Analysis

**Backend:** Plain JSON files (no SQLite, no database)

The storage is file-system based with four JSON files plus HNSW binary. Key properties:

| Index | Format | Loaded By | Concern |
|---|---|---|---|
| documents.json | JSON (pretty) | Every search | Full parse each call |
| sections.json | JSON (pretty) | Every search | Full parse each call |
| links.json | JSON (pretty) | Link operations | Acceptable |
| bm25.json | JSON (BM25 export) | BM25 build only | Acceptable |
| meta.bin | MessagePack | Every semantic search | Fast, but still loaded per-call |
| vectors.bin | HNSW binary | Every semantic search | 100-300MB, loaded per-call |

The JSON format works well under 10,000 sections. Beyond that, the parse overhead on each search request becomes the primary latency driver. The switch to MessagePack for vector metadata (already implemented) demonstrates awareness of this; applying the same treatment to document and section indexes would yield a 2-3x parse speedup.

---

## Caching Strategy Analysis

**Current state:** No in-process caching anywhere in the search path.

Every search operation re-reads and re-parses indexes from disk. Every embedding search re-loads the HNSW binary. The `addContextLinesToResults` function has a `fileCache` Map within a single call (good), but this does not persist between calls.

**What is cached:**
- Embedding vectors in HNSW (persistent on disk)
- BM25 index (persistent on disk, loaded once per `buildBM25Index` call)
- Cross-encoder reranker model (module-level singleton via `getReranker`)

**What should be cached:**
- Parsed `DocumentIndex` and `SectionIndex` (in-process, invalidated by mtime)
- Loaded `HnswVectorStore` instance (in-process, invalidated by `buildEmbeddings`)
- Embedding for repeated identical queries (optional, LRU with small capacity)

---

## Incremental Indexing Analysis

**Current implementation: Correct, but carries hidden overhead**

Change detection uses hash (SHA-256 truncated to 16 hex chars) + mtime. The logic is:

```typescript
if (
  !options.force &&
  existingEntry &&
  existingEntry.hash === hash &&
  existingEntry.mtime === stats.mtime.getTime()
) {
  unchangedCount++
  return
}
```

This is correct. The dual check (mtime first, then hash) avoids unnecessary hashing for truly unchanged files.

**Gap:** The mtime check requires `fs.stat` for every file in the corpus, not just changed files. The directory walk also reads every directory entry. The watcher does not pass changed paths through, so every watcher-triggered re-index pays this full O(corpus) cost.

**Gap:** When a file is deleted, its entries remain in `mutableDocuments` and `mutableSections`. There is no cleanup pass for deleted files. Over time, deleted files accumulate as stale entries in all three indexes.

---

## Embedding Pipeline Analysis

**Batch sizing:** Sound design. `batchTexts` correctly handles both text-count limits (100 per batch default) and token limits (250,000 tokens per batch). Oversized individual texts are isolated rather than dropped.

**Parallelism:** Batches are processed sequentially. OpenAI's API supports concurrent requests; the pipeline could parallelize up to 3-5 concurrent batch requests without hitting rate limits on standard tier accounts.

**Incremental embedding updates:** Current behavior is all-or-nothing. If the vector store has any existing embeddings, the entire build is skipped. This means adding 100 new files to a 10,000-file corpus requires `--force` to embed the new content, which re-embeds and re-costs all existing sections.

**Recommendation:** Track which sections have been embedded (by section ID) within the vector store metadata. On `buildEmbeddings`, compute the set difference between current sections and embedded sections, and only embed the delta. This is the single highest-value improvement for operational cost.

---

## Parser Analysis

**Parsing mode:** Whole-file, not streaming.

```typescript
const tree = processor.parse(markdownContent) as Root
```

The `processor` instance is a module-level singleton (correctly shared across calls). The `remark` parser builds a complete AST in memory before any processing. For typical markdown files (under 100KB) this is entirely acceptable.

**Concern:** The `parse` function computes token counts via `countTokensApprox(content)` (full document) and then again for each section's content. This is redundant since section token counts could be derived from line ranges without re-processing the full text.

**Content splitting:** `markdownContent.split('\n')` is called inside `parse` to produce `lines`, but is also called again in `buildEmbeddings`, `buildBM25Index`, and `addContextLinesToResults` for each document. The split result is not cached across callers.

---

## Memory Management Analysis

**In-process memory:**
- `DocumentIndex` and `SectionIndex` are loaded as plain JavaScript objects on every search.
- The HNSW index for large corpora is loaded into hnswlib-node's native memory.
- For 50,000 sections at 1536 dimensions: ~300MB in the HNSW index alone.

**Large file handling:** Files are read entirely into memory before processing. There is no streaming. For typical markdown this is fine; for very large single files (100MB+) this could cause issues.

**Object allocation:** `buildIndex` pre-allocates mutable copies of all index structures at lines 257-283:

```typescript
const mutableDocuments: Record<string, DocumentEntry> = { ...docIndex.documents }
const mutableSections: Record<string, SectionEntry> = { ...sectionIndex.sections }
```

These shallow copies duplicate all keys in memory. For 50,000 sections this is ~50,000 object copies held simultaneously. A Map-based approach with in-place mutation would halve the peak memory for the index build operation.

---

## Concurrency and Async Patterns

**Effect-TS usage:** The codebase correctly uses Effect for error typing and composition. The main issue is that Effect's `gen`/`yield*` pattern makes it syntactically easy to write sequential code even when operations could be parallel.

**Current concurrency:** Within a single operation, `Promise.all([readFile, stat])` parallelizes within each file. That is the only concurrency in the hot path.

**Cross-encoder reranker:** Uses a module-level singleton (`rerankerInstance`). Model loading is deferred to first use. This is correct behavior.

**MCP server startup:** The server does not pre-load any indexes at startup. Indexes are loaded on first request. This is reasonable, but the first request after MCP server start will be noticeably slower (cold path). Pre-loading on startup would improve P99 first-request latency.

---

## Startup Time Analysis

**MCP server (`src/mcp/server.ts`):** Uses lazy initialization. No indexes are loaded at module load time. The first call to any search tool bears the full cold-path cost (JSON parse + HNSW load). With the 300ms JSON parse and ~500ms HNSW load for a large corpus, the first request may take 800ms+ while subsequent requests would be fast (if caching were implemented).

**CLI startup:** Imports are dynamic. No particular concern.

---

## Ranked Bottleneck Summary

| Rank | Bottleneck | Impact | Effort |
|---|---|---|---|
| 1 | No in-process index cache (JSON reloaded per search) | High | Medium |
| 2 | Sequential file I/O during indexing (no parallelism) | High | Medium |
| 3 | HNSW store reloaded on every semantic search | High | Low |
| 4 | No incremental embedding updates (delta embed) | High | High |
| 5 | No retry/backoff on embedding API rate limits | High | Low |
| 6 | Sequential file reads during `buildEmbeddings` | Medium | Medium |
| 7 | Watcher triggers full re-index instead of delta | Medium | Medium |
| 8 | Broken link deduplication O(n) array scan | Low | Trivial |

---

## Recommendations by Priority

### Immediate (< 1 day effort)

1. **Fix broken link deduplication:** Replace `brokenLinks: string[]` with `Set<string>` in `buildIndex`. One-line change, eliminates O(n^2) worst case.

2. **Switch index JSON to compact format:** Change `JSON.stringify(data, null, 2)` to `JSON.stringify(data)` in `writeJsonFile`. Reduces file size ~35%, speeds both read and write. Does not affect correctness.

3. **Add retry with backoff for `RateLimit` errors:** In `OpenAIProvider.embed`, wrap the batch loop with a retry that detects `RateLimit` classification and sleeps with exponential backoff before retrying. Prevents full corpus embedding failures from transient API errors.

### Short-term (1-3 days effort)

4. **Add module-level HNSW singleton cache:** In `semanticSearch` and `hybridSearch`, maintain a module-level `Map<string, HnswVectorStore>` keyed by namespace path. Load once, reuse for all subsequent searches. Invalidate when `buildEmbeddings` completes. This alone will reduce P50 semantic search latency by 500ms+ on large corpora.

5. **Add module-level index cache for JSON indexes:** In `loadDocumentIndex` / `loadSectionIndex`, add a module-level cache with mtime-based invalidation. Before parsing, stat the file; if mtime matches cached mtime, return cached object. This reduces search latency from ~300ms to ~1ms for repeated queries.

6. **Parallelize file I/O in `buildIndex`:** Replace the serial `for` loop with `Effect.all` using a concurrency limit of 50. Group files into batches of 50, process each batch concurrently, collect results. This should reduce 10,000-file indexing time by 10-20x.

### Medium-term (1-2 weeks effort)

7. **Implement delta embedding:** In `buildEmbeddings`, read existing vector store entries to get a Set of already-embedded section IDs. Compute the difference against current sections. Only embed new/changed sections. This eliminates the `--force` requirement for corpus growth and dramatically reduces operational embedding costs.

8. **Implement targeted watcher re-index:** Pass changed file paths from chokidar to `buildIndex`. Add a `changedPaths?: string[]` option to `IndexOptions` that, when present, skips the directory walk and processes only the specified files. The broken-link detection pass would still need a full scan, but that is fast compared to per-file I/O.

9. **Parallelize `buildEmbeddings` file reads:** Apply the same concurrent I/O pattern as recommendation 6 to the file reading loop in `buildEmbeddings`.

---

## Performance Targets (Recommended)

| Metric | Current (est.) | Target |
|---|---|---|
| Index build, 5,000 files (cold) | 15-45s | 3-8s |
| Index build, 5,000 files (incremental, 10 changed) | 8-15s | 0.5-1s |
| Keyword search latency (P50) | 200-400ms | 5-20ms |
| Semantic search latency (P50, warm) | 600-900ms | 50-100ms |
| Semantic search latency (P50, cold) | 600-900ms | 600-900ms (acceptable) |
| Embedding build, 5,000 sections (no cache) | 45-90s | 30-60s |
| Embedding build, 5,000 sections (100 new) | 45-90s (force) | 3-8s (delta) |
| Peak RSS during index build, 50k sections | 1-2GB | 400-600MB |

---

## Monitoring Recommendations

The existing `onProgress` callbacks and `duration` fields in results are a good foundation. Additional instrumentation to add:

1. Per-phase timing in `buildIndex`: walk, hash-check, parse, save phases separately.
2. Cache hit/miss counters for the index cache (once implemented).
3. HNSW search latency separate from total semantic search latency.
4. Embedding API latency per batch, total batches, retry count.
5. Index file sizes and parse times logged at debug level.

---

*Analysis based on static code review using fmm structural navigation. No load tests were executed. Estimates are based on JavaScript engine characteristics and typical filesystem performance on macOS/Linux.*
