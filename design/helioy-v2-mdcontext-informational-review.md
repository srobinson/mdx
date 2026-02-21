# Helioy V2: Mdcontext Informational Review

Date: 2026-03-11
Status: Informational briefing
Author: Codex

## Purpose

This note is a factual synthesis of the current `mdcontext` codebase.

It focuses on:

- architecture
- methodology
- technology choices
- execution flow
- ingestion and formatting behavior
- current attachment points for future normalization or reformatting capabilities

This is intentionally informational only.

## High-Level Positioning

`mdcontext` is a token-efficiency tool for markdown corpora.

Its current product promise is clearly stated in [README.md](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/README.md):

- “Give LLMs exactly the markdown they need. Nothing more.”

The repo currently exposes two runtime surfaces:

- `mdcontext`
  CLI for indexing, search, context assembly, structure, links, duplicates, embeddings, and config

- `mdcontext-mcp`
  MCP server exposing the same core operations to external agent environments

## Technology Stack

The project is a TypeScript ESM package with `tsup` build output and `vitest` coverage.

Key technologies from [package.json](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/package.json):

- `@effect/cli`, `effect`
  runtime, command model, and service layering

- `remark-parse`, `remark-gfm`, `unified`, `unist-util-visit`
  markdown parsing and AST traversal

- `gray-matter`
  YAML frontmatter extraction

- `wink-bm25-text-search`
  keyword retrieval / BM25 index

- `hnswlib-node`
  approximate nearest-neighbor vector store

- `openai`
  cloud provider client for embeddings

- provider-specific local and remote support through custom embedding providers

- `chokidar`
  watch mode for reindexing

- `@modelcontextprotocol/sdk`
  MCP server integration

- `tiktoken`
  token estimation

The package currently requires Node 18+.

## Source Tree Structure

The repo is organized by responsibility under `src/`:

- `cli/`
  command definitions, options, help, and error handling

- `config/`
  schema, precedence, file provider, service layer

- `parser/`
  markdown parsing and section filtering

- `index/`
  filesystem discovery, ignore handling, storage, watch mode

- `search/`
  keyword, BM25, fuzzy, path matching, query parsing, hybrid retrieval, reranking

- `embeddings/`
  provider factory, vector store, semantic search, HyDE, namespace handling

- `summarize/`
  deterministic structural summarization and formatting

- `summarization/`
  LLM summarization pipeline, provider abstraction, cost handling, prompts

- `duplicates/`
  duplicate detection

- `mcp/`
  MCP server surface

This split already reflects two different operational layers:

1. deterministic markdown structure and retrieval
2. optional LLM-powered summarization over retrieved material

## Runtime Entry Points

The CLI entrypoint is [src/cli/main.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/cli/main.ts).

It defines a command tree including:

- `index`
- `search`
- `context`
- `tree`
- `links`
- `backlinks`
- `duplicates`
- `stats`
- `config`
- `embeddings`

The MCP entrypoint is [src/mcp/server.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/mcp/server.ts).

It maps the same core services into MCP tools such as:

- `md_search`
- `md_context`
- `md_structure`
- `md_keyword_search`
- `md_index`
- `md_links`
- `md_backlinks`

## Core Methodology

The current methodology is:

1. parse markdown into a structured document model
2. index documents, sections, and links
3. optionally build BM25 and vector indexes
4. retrieve at the section level
5. summarize or assemble context under a token budget

The system does not treat markdown as raw blobs.

It treats markdown as:

- heading-delimited sections
- hierarchical document structure
- extractable code/list/table signals
- link graph
- token-budgeted context source

## Parsing Model

Parsing is implemented in [src/parser/parser.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/parser/parser.ts).

The parser:

- strips YAML frontmatter using `gray-matter`
- parses markdown with `unified().use(remarkParse).use(remarkGfm)`
- extracts headings first
- turns heading-delimited spans into sections
- builds a nested heading hierarchy using heading depth
- computes per-section metadata
- extracts links and code blocks by AST walk

The current parser is extractive rather than transform-driven.

Important detail:

- it uses `processor.parse(...)`
- not a `processor.run(...)` transform pipeline

That means the current parser builds structure from source markdown, but does not currently use an AST transformation stage as part of normal ingestion.

## Sectioning Strategy

Sectioning is heading-based.

The parser:

- collects headings with line numbers
- slices content between headings
- creates section ranges with `startLine` and `endLine`
- stores both markdown content and `plainText`
- records whether sections contain code, lists, or tables

The hierarchy is then flattened later by the indexer into `SectionEntry` records for retrieval and reconstruction.

This means `mdcontext` is currently section-native, not paragraph-native.

## Section Filtering and Reconstruction

The section filter layer in [src/parser/section-filter.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/parser/section-filter.ts) provides:

- hierarchical section numbering like `1`, `1.1`
- exact heading lookup
- partial heading matching
- glob-like section matching
- shallow extraction behavior
- exclusion filtering

It also contains a reconstruction path for selected sections.

That reconstruction is output-oriented:

- it rebuilds selected sections as markdown for extraction and rendering
- it does not rewrite the source file on disk

## Indexing Model

Indexing is implemented in [src/index/indexer.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/index/indexer.ts).

The indexing flow is:

1. initialize `.mdcontext`
2. load or create existing indexes
3. build ignore filter from CLI patterns and ignore files
4. walk `.md` and `.mdx` files
5. skip unchanged files using content hash and mtime
6. parse changed files
7. flatten sections
8. resolve internal links
9. persist updated indexes

Current persisted structure is JSON-based:

- `.mdcontext/config.json`
- `.mdcontext/indexes/documents.json`
- `.mdcontext/indexes/sections.json`
- `.mdcontext/indexes/links.json`

There is also a defined parsed-cache path under `.mdcontext/cache/parsed`, but in the current codebase it is created conceptually rather than being actively used as a read/write parsed representation cache.

## Document, Section, and Link Indexes

The JSON indexes store:

### Document index

- title
- path
- content hash
- modification time
- token count
- section count

### Section index

- document path
- heading
- heading level
- line ranges
- token count
- code/list/table flags

### Link index

- forward links
- backlinks
- broken links

This means the structural layer is persisted separately from any search-specific indexes.

## Retrieval Layers

There are three retrieval modes in the current implementation.

### 1. Structural / Metadata Search

Implemented in [src/search/searcher.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/search/searcher.ts).

This mode filters pre-indexed section metadata:

- heading pattern
- path pattern
- code/list/table flags
- heading level range

It does not reopen source files for simple metadata filtering.

### 2. Content Search

Also implemented in [src/search/searcher.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/search/searcher.ts).

This mode:

- groups sections by document
- reopens source files as needed
- slices section content by `startLine` / `endLine`
- evaluates boolean queries, regex, fuzzy search, or stemming
- returns line-level matches with optional before/after context

This means content search depends on the original source files, not just the stored section index.

### 3. BM25 Search

Implemented in [src/search/bm25-store.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/search/bm25-store.ts).

BM25 indexing:

- uses section-level documents
- stores heading and content
- weights headings more strongly than section body text
- persists to:
  - `.mdcontext/bm25.json`
  - `.mdcontext/bm25.meta.json`

This is a dedicated lexical retrieval layer, separate from the structural JSON indexes.

## Semantic Search

Semantic retrieval is implemented through the `embeddings/` subsystem.

Important components:

- [src/embeddings/semantic-search.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/embeddings/semantic-search.ts)
- [src/embeddings/provider-factory.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/embeddings/provider-factory.ts)
- [src/embeddings/vector-store.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/embeddings/vector-store.ts)
- [src/embeddings/hyde.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/embeddings/hyde.ts)

The embedding methodology is section-level:

- reopen source files
- reconstruct section text from line ranges
- prepend section heading
- optionally prepend parent heading
- prepend document title
- embed that composed text
- store vectors in namespaced HNSW indexes under `.mdcontext/embeddings/...`

Query-time semantic search can:

- preprocess the query
- optionally use HyDE to generate a hypothetical expansion
- embed the query
- perform HNSW nearest-neighbor search
- apply similarity thresholding
- filter by path
- boost headings and “important” document names like `README.md`

So the semantic layer is not document-level. It is section-level with heading-aware representation.

## Hybrid Search and Reranking

Hybrid retrieval is implemented in [src/search/hybrid-search.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/search/hybrid-search.ts).

Current methodology:

- run BM25 and semantic retrieval independently
- overfetch from both
- fuse rankings with Reciprocal Rank Fusion (RRF)
- optionally rerank the fused candidate set with a cross-encoder

The reranker is implemented in [src/search/cross-encoder.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/search/cross-encoder.ts).

It uses:

- `Xenova/ms-marco-MiniLM-L-6-v2`

This means mdcontext already has a three-stage retrieval story:

1. lexical / BM25
2. vector / semantic
3. optional reranking

## Summarization Layers

There are two distinct summarization systems in the repo.

### Deterministic Structural Summarization

Implemented in:

- [src/summarize/summarizer.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/summarize/summarizer.ts)
- [src/summarize/formatters.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/summarize/formatters.ts)

This path:

- works directly from parsed `MdDocument` structures
- supports `brief`, `summary`, and `full`
- extracts “key” sentences heuristically for summaries
- keeps full text when content is already small
- computes token budgets
- truncates under budget
- supports multi-file context assembly

This is the engine behind `mdcontext context`.

### AI Summarization

Implemented in:

- [src/summarization/pipeline.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/summarization/pipeline.ts)
- [src/summarization/provider-factory.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/summarization/provider-factory.ts)
- [src/summarization/prompts.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/summarization/prompts.ts)

This path:

- formats search results
- estimates cost
- optionally requests user confirmation
- selects a summarizer provider
- runs an LLM summarization pass

This is distinct from deterministic context assembly and is currently tied to summarizing retrieved results rather than rewriting source markdown.

## Duplicate Detection

Duplicate detection is implemented in [src/duplicates/detector.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/duplicates/detector.ts).

Its current normalization behavior is limited and targeted:

- normalize whitespace
- normalize line endings
- then hash

This is currently normalization for duplicate detection, not document canonicalization.

## Ingestion Model

The current ingestion model can be summarized as:

```text
raw markdown
  -> frontmatter strip
  -> mdast parse
  -> heading / section extraction
  -> link + code extraction
  -> JSON structural indexes
  -> optional BM25 and embedding indexes
```

Important characteristic:

Many downstream paths re-slice original source files by stored line ranges instead of consuming a separately normalized canonical body.

This applies to:

- BM25 build
- semantic embedding build
- keyword content search
- context extraction

## Current Formatting / Rewrite Behavior

The current codebase has formatting- or rewrite-adjacent behavior, but not source-document normalization or source-document mutation.

What exists today:

- section selection and re-rendering for extraction
- in-memory section filtering
- deterministic token-budgeted summary formatting
- search-result formatting for LLM summarization
- duplicate normalization

What does not currently exist in the ingestion flow:

- LLM-assisted markdown normalization
- AST transform pipeline during parse
- canonical normalized body persistence
- source markdown rewrite-on-ingest
- rewrite-on-disk command integrated with indexing

## Existing Attachment Points for Future Reformatting

Based on the current codebase, the most natural conceptual attachment points for a future LLM-assisted normalization or reformatting capability are:

### 1. Pre-parse text normalization

Immediately after frontmatter extraction and before `processor.parse(...)` in [src/parser/parser.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/parser/parser.ts).

This would be the cleanest point for text-level markdown normalization before AST extraction.

### 2. Post-parse AST transformation

Immediately after mdast parse and before section extraction in [src/parser/parser.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/parser/parser.ts).

This would be the natural attach point for an AST-aware normalization pass.

### 3. Indexer-side ingest transform

Inside the per-file indexing flow after raw file read and before `parse(...)` in [src/index/indexer.ts](/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/index/indexer.ts).

This would make normalization an explicit part of ingestion.

### 4. Sidecar normalized cache

Under the currently underused parsed-cache concept in `.mdcontext/cache/parsed`.

This could support normalized persisted forms without immediately mutating the source file.

### 5. Representation-level normalization

Before BM25 build or before embedding text construction.

This would normalize what search sees without requiring a source-file rewrite.

## Reformat-on-Ingest vs Rewrite-on-Disk

From the current architecture, two future modes are already conceptually distinguishable:

### Reformat-on-ingest

- source markdown remains as-is
- normalized representation is produced during indexing
- indexes and embeddings may consume normalized content
- source repository is untouched

### Rewrite-on-disk

- source file is rewritten in place or written as a new version
- indexing then proceeds against the rewritten document

The current architecture does not yet implement either mode, but the indexer is the natural control boundary for both.

## Practical Relevance to Your Current Direction

Your current intuition about the product direction is consistent with the codebase:

- newly created docs can be guided into a known format externally through skills or authoring instructions
- the broader open-source markdown ecosystem will contain heterogeneous structures
- `mdcontext` already has the structural parser and ingestion boundary where normalization could conceptually plug in

At the moment, the codebase is strongest as:

- a structured markdown parser
- an indexer
- a retrieval system
- a token-budgeted context assembler

It is not yet a document normalization or canonicalization engine, but the ingest path is already clear enough that such a capability has obvious insertion points.
