---
title: "mdcontext Architecture — Data Model, Indexing, and Search"
type: design
tags: [mdcontext, architecture, embeddings, indexing, helioy]
summary: "Internal architecture of mdcontext: document model, index structure, embedding pipeline, and search algorithms"
status: active
created: 2026-02-21
updated: 2026-02-21
project: mdcontext
---

# mdcontext Architecture

**Source:** `/Users/alphab/Dev/LLM/DEV/mdcontext`

mdcontext is a token-efficient markdown analysis tool that extracts structure from markdown documentation and provides semantic and keyword search for LLM consumption. It achieves ~84% token reduction compared to raw markdown dumps.

---

## 1. Technology Stack

| Layer                  | Technology                                                                               |
| ---------------------- | ---------------------------------------------------------------------------------------- |
| Language               | TypeScript (ESM, Node.js 18+)                                                            |
| Effect System          | [Effect](https://effect.website/) for typed errors, generators, and composable pipelines |
| Parser                 | unified/remark + remark-gfm (GFM tables, task lists)                                     |
| Frontmatter            | gray-matter                                                                              |
| Token Counting         | tiktoken (cl100k_base) with fast heuristic approximation                                 |
| Vector Search          | hnswlib-node (HNSW algorithm, cosine distance)                                           |
| Keyword Search         | wink-bm25-text-search                                                                    |
| Embedding API          | OpenAI SDK (supports OpenAI, Ollama, LM Studio, OpenRouter, Voyage)                      |
| Re-ranking             | @huggingface/transformers (Xenova/ms-marco-MiniLM-L-6-v2, optional)                      |
| Metadata Serialization | MessagePack (@msgpack/msgpack) for vector metadata                                       |
| CLI Framework          | @effect/cli                                                                              |
| MCP Integration        | @modelcontextprotocol/sdk                                                                |
| Build                  | tsup (ESM output)                                                                        |
| Test                   | Vitest                                                                                   |

---

## 2. Core Data Model

Defined in `src/core/types.ts`. All types are `readonly` -- immutable by convention.

### 2.1 MdDocument

The root parsed representation of a single markdown file.

```typescript
interface MdDocument {
  readonly id: string; // MD5 hash of relative path (12 chars)
  readonly path: string; // Relative to index root
  readonly title: string; // First H1, frontmatter title, or filename
  readonly frontmatter: Record<string, unknown>;
  readonly sections: readonly MdSection[]; // Hierarchical section tree
  readonly links: readonly MdLink[]; // All links (internal, external, image)
  readonly codeBlocks: readonly MdCodeBlock[];
  readonly metadata: DocumentMetadata;
}

interface DocumentMetadata {
  readonly wordCount: number;
  readonly tokenCount: number; // Approximate token count (heuristic)
  readonly headingCount: number;
  readonly linkCount: number;
  readonly codeBlockCount: number;
  readonly lastModified: Date;
  readonly indexedAt: Date;
}
```

### 2.2 MdSection

Sections form a tree mirroring heading hierarchy. Each section captures content between its heading and the next heading of equal or higher level.

```typescript
interface MdSection {
  readonly id: string; // "{docId}-{slugified-heading}"
  readonly heading: string;
  readonly level: 1 | 2 | 3 | 4 | 5 | 6;
  readonly content: string; // Raw markdown (heading line through end of section)
  readonly plainText: string; // Text-only extraction for embedding
  readonly startLine: number; // 1-based
  readonly endLine: number;
  readonly children: readonly MdSection[]; // Nested subsections
  readonly metadata: SectionMetadata;
}

interface SectionMetadata {
  readonly wordCount: number;
  readonly tokenCount: number;
  readonly hasCode: boolean;
  readonly hasList: boolean;
  readonly hasTable: boolean;
}
```

**Section hierarchy construction** (`parser.ts:buildSectionHierarchy`): Uses a stack-based algorithm. For each raw section, pops the stack until finding a parent with a strictly lower heading level. If the stack is empty, the section becomes a root. Otherwise, it is appended as a child of the top-of-stack section.

### 2.3 MdLink

```typescript
type LinkType = "internal" | "external" | "image";

interface MdLink {
  readonly type: LinkType;
  readonly href: string;
  readonly text: string;
  readonly sectionId: string; // Which section contains this link
  readonly line: number;
}
```

Internal link classification: anything that is not `http://`, `https://`, or `mailto:` and either starts with `#`, ends in `.md`, or contains `.md#`.

### 2.4 MdCodeBlock

```typescript
interface MdCodeBlock {
  readonly language: string | null;
  readonly content: string;
  readonly sectionId: string;
  readonly startLine: number;
  readonly endLine: number;
}
```

---

## 3. Parsing Pipeline

**File:** `src/parser/parser.ts`

### 3.1 Data Flow

```
Markdown File
    |
    v
gray-matter  -->  Extract YAML frontmatter (graceful: malformed YAML logs warning, treats entire content as markdown)
    |
    v
unified().use(remarkParse).use(remarkGfm).parse()  -->  MDAST (Markdown Abstract Syntax Tree)
    |
    +---> extractRawSections(tree)     -- Two-pass: collect headings, then slice content nodes between them
    |       |
    |       v
    |     buildSectionHierarchy()      -- Stack-based nesting into MdSection tree
    |
    +---> extractLinks(tree, docId)    -- visit() walker, tracks current section for sectionId
    |
    +---> extractCodeBlocks(tree, docId)
    |
    v
MdDocument  (fully parsed, in-memory representation)
```

### 3.2 ID Generation

- **Document ID:** `md5(relativePath).slice(0, 12)` -- deterministic, 12-char hex string
- **Section ID:** `"{docId}-{slugify(heading)}"` -- heading slugified (lowercase, remove non-word, collapse hyphens)
- **Content hash:** `sha256(content).slice(0, 16)` -- used for change detection during indexing

### 3.3 Token Counting

**File:** `src/utils/tokens.ts`

Two modes:

1. **Exact (`countTokens`):** Lazy-loads tiktoken with `cl100k_base` encoding (GPT-4/Claude compatible). Effect-based, async.
2. **Approximate (`countTokensApprox`):** Synchronous heuristic used during indexing. Calibrated against cl100k_base with specific handling for:
   - Prose: ~3.5 chars/token
   - Code blocks: ~2.5 chars/token + fixed overhead per block
   - Inline code: ~2.5 chars/token + 2 tokens per backtick pair
   - Paths: ~3.0 chars/token (slashes tokenize separately)
   - CJK characters: ~1.2 tokens/char
   - Emojis: ~2.5 tokens/emoji
   - Applies a **10% safety margin** to ensure budget compliance

---

## 4. Index Structure

### 4.1 Directory Layout

```
.mdcontext/                              (INDEX_DIR constant)
  config.json                            -- IndexConfig: version, rootPath, include/exclude globs, timestamps
  indexes/
    documents.json                       -- DocumentIndex: all document metadata
    sections.json                        -- SectionIndex: all sections with lookup tables
    links.json                           -- LinkIndex: forward links, backlinks, broken links
  bm25.json                              -- Serialized wink-bm25 engine state
  bm25.meta.json                         -- BM25 metadata (count, version, timestamp)
  active-provider.json                   -- ActiveProvider: which embedding namespace is current
  embeddings/                            -- Namespaced embedding storage
    openai_text-embedding-3-small_512/   -- Format: {provider}_{model}_{dimensions}
      vectors.bin                        -- HNSW index binary (hnswlib format)
      vectors.meta.bin                   -- MessagePack-encoded VectorIndex metadata
    voyage_voyage-3_5-lite_1024/
      vectors.bin
      vectors.meta.bin
  cache/
    parsed/                              -- Cached parsed documents
```

**Legacy layout** (pre-namespacing): `vectors.bin` and `vectors.meta.bin` directly in `.mdcontext/`. Migration is handled automatically.

### 4.2 DocumentIndex

**File:** `.mdcontext/indexes/documents.json`

```typescript
interface DocumentIndex {
  readonly version: number; // INDEX_VERSION = 1
  readonly rootPath: string; // Absolute path to indexed directory
  readonly documents: Record<string, DocumentEntry>; // Keyed by relative path
}

interface DocumentEntry {
  readonly id: string; // MD5 hash of path
  readonly path: string; // Relative path (same as key)
  readonly title: string;
  readonly mtime: number; // File modification time (ms since epoch)
  readonly hash: string; // SHA-256 content hash (16-char prefix)
  readonly tokenCount: number;
  readonly sectionCount: number;
}
```

### 4.3 SectionIndex

**File:** `.mdcontext/indexes/sections.json`

```typescript
interface SectionIndex {
  readonly version: number;
  readonly sections: Record<string, SectionEntry>; // Keyed by section ID
  readonly byHeading: Record<string, readonly string[]>; // heading (lowercase) -> section IDs
  readonly byDocument: Record<string, readonly string[]>; // document ID -> section IDs
}

interface SectionEntry {
  readonly id: string;
  readonly documentId: string;
  readonly documentPath: string;
  readonly heading: string;
  readonly level: number;
  readonly startLine: number;
  readonly endLine: number;
  readonly tokenCount: number;
  readonly hasCode: boolean;
  readonly hasList: boolean;
  readonly hasTable: boolean;
}
```

The `byHeading` and `byDocument` maps enable efficient lookups without scanning all sections.

### 4.4 LinkIndex

**File:** `.mdcontext/indexes/links.json`

```typescript
interface LinkIndex {
  readonly version: number;
  readonly forward: Record<string, readonly string[]>; // source path -> target paths
  readonly backward: Record<string, readonly string[]>; // target path -> source paths
  readonly broken: readonly string[]; // links to non-existent docs
}
```

Link resolution (`indexer.ts:resolveInternalLink`):

- `#fragment` links resolve to self
- HTTP/HTTPS links are classified as external (not stored in link index)
- Relative paths are resolved against the source file's directory
- Links resolving outside rootPath are discarded

---

## 5. Indexing Pipeline

**File:** `src/index/indexer.ts`

### 5.1 buildIndex() Data Flow

```
buildIndex(rootPath, options)
    |
    v
1. initializeIndex(storage)          -- mkdir .mdcontext/, .mdcontext/indexes/, .mdcontext/cache/parsed/
    |                                    Create default config.json if absent
    v
2. Load existing indexes              -- Or create empty ones if force=true or missing
    |
    v
3. createIgnoreFilter()               -- Merges: CLI patterns > .mdcontextignore > .gitignore > defaults
    |
    v
4. walkDirectory(rootPath, filter)    -- Recursive directory walk
    |                                    Skips: hidden dirs (.), pattern-excluded, non-.md/.mdx files
    v
5. For each markdown file:
    |
    +-- Read file content + stat
    |
    +-- computeHash(content)           -- SHA-256, 16-char prefix
    |
    +-- Skip if hash+mtime unchanged   -- Incremental indexing
    |
    +-- parse(content, {path, lastModified})
    |     |
    |     v
    |   MdDocument
    |
    +-- Clean up old sections/links for this doc (if re-indexing)
    |
    +-- Update DocumentEntry (id, path, title, mtime, hash, tokenCount, sectionCount)
    |
    +-- flattenSections() -> SectionEntry[]   -- Recursively flattens section tree
    |     |
    |     +-- Populate sections, byHeading, byDocument maps
    |
    +-- Process internal links
    |     |
    |     +-- resolveInternalLink() for each
    |     +-- Build forward and backward link maps
    |
    +-- Collect non-fatal errors (file processing continues on error)
    |
    v
6. Check for broken links             -- Forward targets that are not in documents
    |
    v
7. Save all three indexes             -- documents.json, sections.json, links.json
    |
    v
IndexResult { documentsIndexed, sectionsIndexed, linksIndexed, duration, errors, skipped }
```

### 5.2 Incremental Indexing

Change detection uses **hash + mtime**: a file is skipped if both its SHA-256 content hash and filesystem modification time match the stored entry. This avoids re-parsing unchanged files while still detecting content changes from outside the tool.

### 5.3 BM25 Index Building

**File:** `src/index/indexer.ts:buildBM25Index` and `src/search/bm25-store.ts`

After structural indexing, a BM25 keyword index can be built:

1. Groups sections by document (skipping sections < 10 tokens)
2. Reads file content, extracts section text by line range
3. Feeds `{ heading, content }` pairs to `wink-bm25-text-search`
4. BM25 engine configured with `fldWeights: { heading: 2, content: 1 }` (headings weighted 2x)
5. Tokenizer: lowercase, split on non-word chars, filter tokens < 3 chars
6. Consolidates and saves to `.mdcontext/bm25.json` + `.mdcontext/bm25.meta.json`

---

## 6. Embedding Pipeline

**File:** `src/embeddings/semantic-search.ts`

### 6.1 Embedding Text Generation

For each section, the text sent to the embedding model is structured as:

```
# {section heading}
Parent section: {parent heading}    (if nested)
Document: {document title}

{section content from startLine to endLine}
```

This format provides hierarchical context to the embedding, improving retrieval relevance for sections that reference concepts defined in parent sections.

### 6.2 buildEmbeddings() Flow

```
buildEmbeddings(rootPath, options)
    |
    v
1. Load DocumentIndex + SectionIndex
    |
    v
2. Create/configure embedding provider
    |   Priority: explicit provider > providerConfig > default (openai)
    |   Provider factory creates OpenAI-compatible client with appropriate baseURL
    v
3. Create namespaced vector store
    |   Namespace = "{provider}_{model}_{dimensions}"
    |   e.g., "openai_text-embedding-3-small_512"
    v
4. Check existing embeddings (skip if not force and vectors exist)
    |
    v
5. Group sections by document, skip sections < 10 tokens
    |
    v
6. For each document:
    |   Read file content
    |   For each section: generateEmbeddingText()
    v
7. Batch embed all texts via provider.embed()
    |   Batched at 100 texts per API call (configurable)
    |   Reports batch progress via callbacks
    v
8. Create VectorEntry[] and add to vector store
    |
    v
9. Save HNSW index (vectors.bin) + metadata (vectors.meta.bin)
    |
    v
10. Write active-provider.json
    |
    v
BuildEmbeddingsResult { sectionsEmbedded, tokensUsed, cost, duration }
```

### 6.3 Embedding Providers

All providers implement the `EmbeddingProvider` interface:

```typescript
interface EmbeddingProvider {
  readonly name: string;
  readonly dimensions: number;
  embed(texts: string[], options?: EmbedOptions): Promise<EmbeddingResult>;
}
```

| Provider   | Implementation                       | Base URL                       | API Key Env          |
| ---------- | ------------------------------------ | ------------------------------ | -------------------- |
| OpenAI     | `OpenAIProvider` (OpenAI SDK)        | SDK default                    | `OPENAI_API_KEY`     |
| Ollama     | `OpenAIProvider` with custom baseURL | `http://localhost:11434/v1`    | N/A (local)          |
| LM Studio  | `OpenAIProvider` with custom baseURL | `http://localhost:1234/v1`     | N/A (local)          |
| OpenRouter | `OpenAIProvider` with custom baseURL | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| Voyage     | `VoyageProvider` (native API)        | `https://api.voyageai.com/v1`  | `VOYAGE_API_KEY`     |

**Default model:** `text-embedding-3-small` at **512 dimensions** (Matryoshka reduced from native 1536).

Matryoshka Representation Learning (MRL) allows dimension reduction without retraining. Only `text-embedding-3-small` and `text-embedding-3-large` support this. Research showed 512 is the optimal balance of speed/accuracy.

### 6.4 Embedding Namespace System

**File:** `src/embeddings/embedding-namespace.ts`

Supports multiple embedding providers/models side-by-side:

```
.mdcontext/
  embeddings/
    openai_text-embedding-3-small_512/    -- Each provider/model/dimensions gets its own directory
      vectors.bin
      vectors.meta.bin
    voyage_voyage-3_5-lite_1024/
      vectors.bin
      vectors.meta.bin
  active-provider.json                    -- Points to current active namespace
```

**ActiveProvider:**

```typescript
interface ActiveProvider {
  readonly namespace: string; // e.g., "openai_text-embedding-3-small_512"
  readonly provider: string; // e.g., "openai"
  readonly model: string; // e.g., "text-embedding-3-small"
  readonly dimensions: number; // e.g., 512
  readonly activatedAt: string;
}
```

Auto-detection: If no `active-provider.json` exists, the system lists available namespaces and auto-activates the most recently updated one.

---

## 7. Vector Store (HNSW)

**File:** `src/embeddings/vector-store.ts`

### 7.1 Implementation

Uses `hnswlib-node` with **cosine distance** metric. The `HnswVectorStore` class wraps the native HNSW index.

**Default HNSW Parameters:**

- `M = 16` (max connections per node)
- `efConstruction = 200` (construction-time search width)
- Initial capacity: 10,000 elements (auto-doubles on overflow)

### 7.2 Storage Format

Two files per namespace:

1. **`vectors.bin`** -- Native hnswlib binary format (written by `index.writeIndex()`)
2. **`vectors.meta.bin`** -- MessagePack-encoded `VectorIndex`:

```typescript
interface VectorIndex {
  readonly version: number;
  readonly provider: string;
  readonly providerModel?: string;
  readonly providerBaseURL?: string;
  readonly dimensions: number;
  readonly entries: Record<string, VectorEntry>; // Index position -> entry
  readonly totalCost: number;
  readonly totalTokens: number;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly hnswParams?: HnswIndexParams;
}

interface VectorEntry {
  readonly id: string; // Section ID
  readonly sectionId: string;
  readonly documentPath: string;
  readonly heading: string;
  readonly embedding: readonly number[]; // The actual vector
}
```

Metadata was migrated from JSON to MessagePack for size efficiency. Legacy JSON metadata is auto-migrated on load.

### 7.3 Similarity Computation

hnswlib stores **cosine distance** (1 - cosine_similarity). The vector store converts this back:

```typescript
const similarity = 1 - distance;
```

Results are filtered by threshold, then sorted by similarity descending.

---

## 8. Search Architecture

mdcontext provides three search modes, automatically selected based on available indexes.

### 8.1 Keyword Search

**File:** `src/search/searcher.ts`

Regex-based content search across indexed sections. Supports:

- Heading pattern matching (regex)
- Content search with boolean operators (AND, OR, NOT) via `query-parser.ts`
- Fuzzy matching with configurable edit distance via `fuzzy-search.ts`
- Word stemming
- Path glob filtering via `path-matcher.ts`
- Structural filters: `hasCode`, `hasList`, `hasTable`, heading level range
- Context lines (like grep `-B`/`-A`/`-C`)

### 8.2 Semantic Search

**File:** `src/embeddings/semantic-search.ts`

```
Query
  |
  +-- preprocessQuery()         -- Lowercase, strip punctuation, collapse spaces
  |     (skippable with skipPreprocessing: true)
  |
  +-- [Optional] HyDE           -- Generate hypothetical document via LLM, embed that instead
  |
  v
provider.embed([query])         -- Get query embedding vector
  |
  v
vectorStore.search(queryVector, limit*2, threshold, {efSearch})
  |                                                    ^
  |                              Quality modes: fast=64, balanced=100, thorough=256
  v
Apply path filter (if pathPattern specified)
  |
  v
Apply ranking boost:
  +-- calculateHeadingBoost()    -- 5% per query term found in heading
  +-- calculateFileImportanceBoost()  -- 3% for README, index, getting-started, etc.
  |
  v
Sort by boosted similarity, limit results
  |
  v
[Optional] Load context lines from source files
  |
  v
SemanticSearchResult[]
```

**Default threshold:** 0.35 (35% similarity). Configurable via `--threshold`.

### 8.3 Hybrid Search (RRF)

**File:** `src/search/hybrid-search.ts`

Combines BM25 keyword search with semantic vector search using **Reciprocal Rank Fusion (RRF)**.

RRF Formula: `score(doc) = sum( weight / (k + rank) )` where `k = 60` (standard smoothing constant).

```
hybridSearch(rootPath, query, options)
    |
    +---> semanticSearch()     -- Get semantic results (limit * 2)
    |
    +---> bm25Search()         -- Get keyword results (limit * 2)
    |
    v
fusionRRF(semanticResults, keywordResults, {bm25Weight, semanticWeight, rrfK, limit})
    |
    |   For each result from either source:
    |     Accumulate RRF score contributions
    |     Track which sources contributed (semantic, keyword, or both)
    |
    v
[Optional] Cross-encoder re-ranking
    |   Uses Xenova/ms-marco-MiniLM-L-6-v2 (22.7M params)
    |   Re-ranks top 20 candidates -> returns top N
    |   20-35% precision improvement
    v
HybridSearchResult[] with { score, similarity?, bm25Score?, sources, rerankerScore? }
```

**Mode auto-detection priority:**

1. Explicit `--mode` flag
2. `hybrid` if both BM25 and embeddings exist
3. `semantic` if only embeddings exist
4. `keyword` if only BM25 exists

### 8.4 HyDE (Hypothetical Document Embeddings)

**File:** `src/embeddings/hyde.ts`

For complex queries, HyDE generates a hypothetical document that would answer the query using an LLM, then embeds that document for search. This bridges the semantic gap between short queries and detailed documentation.

- Model: `gpt-4o-mini` (default), temperature 0.3, max 256 tokens
- Best for: "how to" queries, complex questions, ambiguous searches
- Improvement: 10-30% better recall on complex queries
- Detection heuristic (`shouldUseHyde`): questions, procedural queries, 6+ word queries

### 8.5 Cross-Encoder Re-ranking

**File:** `src/search/cross-encoder.ts`

Optional second-stage re-ranking using a cross-encoder that processes query-document pairs together:

- Model: `Xenova/ms-marco-MiniLM-L-6-v2` (~90MB download on first use)
- Requires `@huggingface/transformers` (optional dependency)
- Processes top-20 candidates, returns top-N
- 2-5ms per query-document pair
- Singleton pattern with lazy loading

---

## 9. Context Generation & Summarization

### 9.1 Context Generation

**File:** `src/search/searcher.ts:getContext`

Generates LLM-ready summaries from indexed documents:

```typescript
interface DocumentContext {
  readonly path: string;
  readonly title: string;
  readonly totalTokens: number;
  readonly includedTokens: number;
  readonly sections: readonly SectionContext[];
}
```

Supports token budget constraints -- sections are included until the budget is exhausted. Three compression levels: `brief`, `summary`, `full`.

### 9.2 Section Filtering

**File:** `src/parser/section-filter.ts`

Allows extracting specific sections by name, number, or glob pattern:

- `--section "Setup"` -- exact name match
- `--section "2.1"` -- section number
- `--section "API*"` -- glob pattern
- `--shallow` -- top-level only (no nested subsections)

### 9.3 Document Summarization

**File:** `src/summarize/summarizer.ts`

Hierarchical compression with extractive summarization:

- Extracts key sentences (first sentence, keyword-containing sentences, concluding sentence)
- Preserves structural markers (headings, list starts, code block presence)
- Token budget enforcement with truncation tracking
- Multi-document context assembly (`assembleContext`) with proportional budget allocation

---

## 10. Error Architecture

**File:** `src/errors/index.ts`

All errors use Effect's `Data.TaggedError` pattern with a unique `_tag` discriminant for type-safe error handling:

| Category    | Error Types                                                             | Codes     |
| ----------- | ----------------------------------------------------------------------- | --------- |
| File System | FileReadError, FileWriteError, DirectoryCreateError, DirectoryWalkError | E100-E103 |
| Parsing     | ParseError                                                              | E200      |
| API/Auth    | ApiKeyMissingError, ApiKeyInvalidError                                  | E300-E301 |
| Embeddings  | EmbeddingError (RateLimit, QuotaExceeded, Network, ModelError)          | E310-E319 |
| Index       | IndexNotFoundError, IndexCorruptedError, IndexBuildError                | E400-E402 |
| Search      | DocumentNotFoundError, EmbeddingsNotFoundError, DimensionMismatchError  | E500-E601 |
| Config      | ConfigError                                                             | E700      |
| CLI         | CliValidationError                                                      | E900      |

Convention: `message` fields contain technical details; user-friendly messages are generated at the CLI boundary by `src/cli/error-handler.ts`.

---

## 11. MCP Server

**File:** `src/mcp/server.ts`

Exposes three tools for Claude Desktop / Claude Code integration:

| Tool           | Description                                                                |
| -------------- | -------------------------------------------------------------------------- |
| `md_search`    | Semantic search across indexed docs (query, limit, path_filter, threshold) |
| `md_context`   | Get LLM-ready summary for a file (path, level, max_tokens)                 |
| `md_structure` | Get document outline (path)                                                |

Runs via `mdcontext-mcp` binary using stdio transport.

---

## 12. Configuration System

**File:** `src/config/schema.ts`, `src/config/precedence.ts`

Layered configuration with strict precedence:

```
CLI flags  >  Environment variables  >  Config file (mdcontext.config.js)  >  Defaults
```

Configuration file supports ESM default export:

```javascript
export default {
  index: { excludePatterns: ["node_modules", ".git", "dist"] },
  search: { defaultLimit: 20 },
  embeddings: {
    provider: "openai",
    model: "text-embedding-3-small",
    dimensions: 512,
  },
};
```

---

## 13. Key Design Decisions

1. **Section-level embedding granularity** -- Sections provide optimal granularity for retrieval. Very short sections (< 10 tokens) are skipped. Document-level embedding was rejected as too coarse.

2. **512-dimension Matryoshka reduction** -- OpenAI's text-embedding-3-small supports dimension reduction via MRL. 512 dimensions provide the optimal speed/accuracy balance per research benchmarks.

3. **MessagePack for vector metadata** -- Replaced JSON serialization for metadata files to reduce disk size and improve load times. Legacy JSON files are auto-migrated.

4. **HNSW over FAISS** -- hnswlib-node was chosen for its pure-Node.js compatibility (no native FAISS binaries required), good performance characteristics, and cosine distance support.

5. **Namespace-based multi-provider support** -- Allows switching between embedding providers without rebuilding. Each provider/model/dimensions combination gets its own directory.

6. **Incremental indexing** -- SHA-256 content hash + mtime comparison avoids re-parsing unchanged files, making re-indexing fast for large documentation sets.

7. **Effect-TS for error handling** -- All core operations return `Effect.Effect<A, E>` with typed errors. This enables exhaustive error handling and composable pipelines without try/catch.

8. **BM25 heading boost** -- BM25 field weights give headings 2x the weight of content, improving retrieval for navigation-style queries.

9. **RRF for hybrid search** -- Reciprocal Rank Fusion combines semantic and keyword results without requiring score normalization between methods.

---

## 14. File Map (Key Source Files)

```
src/
  core/
    types.ts                    -- MdDocument, MdSection, MdLink, MdCodeBlock
  parser/
    parser.ts                   -- Markdown -> MdDocument (remark/unified)
    section-filter.ts           -- Section extraction by name/number/glob
  index/
    indexer.ts                  -- buildIndex(), buildBM25Index(), link queries
    storage.ts                  -- JSON read/write, hash computation, IndexStorage
    types.ts                    -- DocumentIndex, SectionIndex, LinkIndex, paths
    ignore-patterns.ts          -- .gitignore + .mdcontextignore + CLI patterns
    watcher.ts                  -- chokidar-based file watching
  embeddings/
    semantic-search.ts          -- buildEmbeddings(), semanticSearch(), cost estimation
    vector-store.ts             -- HnswVectorStore (hnswlib-node wrapper)
    openai-provider.ts          -- OpenAI-compatible embedding provider
    voyage-provider.ts          -- Voyage AI native provider
    provider-factory.ts         -- Provider creation from config
    provider-constants.ts       -- Model dimensions, Matryoshka support, base URLs
    embedding-namespace.ts      -- Multi-provider namespace management
    hyde.ts                     -- HyDE query expansion
    types.ts                    -- EmbeddingProvider, VectorEntry, VectorIndex, search types
  search/
    hybrid-search.ts            -- RRF-based hybrid search
    bm25-store.ts               -- wink-bm25-text-search wrapper
    searcher.ts                 -- Keyword search, context generation
    cross-encoder.ts            -- Cross-encoder re-ranking (HuggingFace)
    query-parser.ts             -- Boolean query parsing (AND, OR, NOT)
    fuzzy-search.ts             -- Edit-distance fuzzy matching
    path-matcher.ts             -- Glob-style path filtering
  summarize/
    summarizer.ts               -- Hierarchical summarization, context assembly
    formatters.ts               -- Output formatting
  summarization/
    pipeline.ts                 -- AI summarization pipeline (CLI/API providers)
    cost.ts                     -- LLM cost estimation
    prompts.ts                  -- Summarization prompt templates
  config/
    schema.ts                   -- Configuration schema + defaults
    precedence.ts               -- Config resolution (CLI > env > file > defaults)
    service.ts                  -- Effect service for config access
  errors/
    index.ts                    -- All TaggedError types (E100-E900)
  cli/
    main.ts                     -- CLI entry point
    commands/                   -- Individual command implementations
  mcp/
    server.ts                   -- MCP server (md_search, md_context, md_structure)
  utils/
    tokens.ts                   -- Token counting (tiktoken + heuristic)
```
