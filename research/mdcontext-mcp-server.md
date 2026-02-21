---
title: "mdcontext MCP Server — Tools and Capabilities"
type: research
tags: [mdcontext, mcp, helioy, tools]
summary: "Complete inventory of mdcontext MCP server tools, parameters, and initialization requirements"
status: active
created: 2026-02-21
updated: 2026-02-21
project: mdcontext
---

# mdcontext MCP Server — Tools and Capabilities

**Source file:** `/Users/alphab/Dev/LLM/DEV/mdcontext/src/mcp/server.ts` (612 LOC)
**Binary name:** `mdcontext-mcp` (registered in `package.json` bin)
**Server name:** `mdcontext-mcp`
**Version:** Dynamically read from `package.json` (currently `0.1.0`)
**SDK:** `@modelcontextprotocol/sdk` v1.25.3
**Transport:** StdioServerTransport (stdin/stdout)

---

## 1. Server Capabilities

The server declares **only** the `tools` capability:

```typescript
capabilities: {
  tools: {},
}
```

**No resources are exposed.** No prompts are exposed. The server is tools-only.

---

## 2. Initialization and Startup

### Entry Point

The MCP server runs as a standalone Node.js process via the `mdcontext-mcp` binary (`dist/mcp/server.ts`).

```typescript
const main = async () => {
  const rootPath = process.cwd()       // Uses CWD as the markdown root
  const server = createServer(rootPath)
  const transport = new StdioServerTransport()
  await server.connect(transport)

  process.on('SIGINT', async () => { await server.close(); process.exit(0) })
  process.on('SIGTERM', async () => { await server.close(); process.exit(0) })
}
```

### Index Requirements

- The server itself does **not** automatically build an index on startup.
- **You must run `md_index` (or the CLI `mdcontext index`) before search tools will work.**
- `md_search` (semantic search) additionally requires embeddings to be built first (`mdcontext index --embed`).
- `md_context` and `md_structure` work on individual files via the parser and do **not** require an index.
- `md_links` and `md_backlinks` require an index (they call `getOutgoingLinks`/`getIncomingLinks` from the indexer).
- `md_keyword_search` requires an index (it calls the `search` function from `src/search/searcher.ts`).

### Configuration for Claude Desktop

```json
{
  "mcpServers": {
    "mdcontext": {
      "command": "mdcontext-mcp",
      "args": []
    }
  }
}
```

### Configuration for Claude Code

```json
{
  "mcpServers": {
    "mdcontext": {
      "command": "mdcontext-mcp",
      "args": []
    }
  }
}
```

The server takes no command-line arguments. It uses `process.cwd()` as the root directory for all operations, meaning the working directory where the MCP client spawns the process determines which markdown files are accessible.

---

## 3. Complete Tool Inventory

The server exposes **7 tools**. Below is the full specification for each.

---

### 3.1 `md_search` — Semantic Search

**Description:** Search markdown documents by meaning using semantic search. Returns relevant sections based on natural language queries.

**Prerequisites:** Index must exist AND embeddings must be built (`mdcontext index --embed`). Requires an embedding API key (e.g., `OPENAI_API_KEY`).

**Input Schema:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | `string` | **Yes** | — | Natural language search query |
| `limit` | `number` | No | `5` | Maximum number of results |
| `path_filter` | `string` | No | — | Glob pattern to filter files (e.g., `*.md`, `docs/**/*.md`) |
| `threshold` | `number` | No | `0.35` | Minimum similarity threshold 0-1 |

**Handler:** `handleMdSearch` calls `semanticSearch()` from `src/embeddings/semantic-search.ts`.

**Output format:** Text listing with numbered results showing heading, similarity percentage, and document path.

```
Found 3 results for "authentication":

1. **Authentication Flow** (72.3% match)
   docs/auth.md

2. **Login API** (65.1% match)
   docs/api.md
```

---

### 3.2 `md_context` — LLM-Ready Context

**Description:** Get LLM-ready context from a markdown file. Provides compressed, token-efficient summaries at various detail levels.

**Prerequisites:** None (parses the file directly).

**Input Schema:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | `string` | **Yes** | — | Path to the markdown file |
| `level` | `string` (enum: `full`, `summary`, `brief`) | No | `summary` | Compression level |
| `max_tokens` | `number` | No | — | Maximum tokens to include in output |

**Handler:** `handleMdContext` calls `summarizeFile()` then `formatSummary()` from `src/summarize/summarizer.ts`.

**Path resolution:** Relative paths are resolved against `rootPath` (CWD). Absolute paths are used as-is.

---

### 3.3 `md_structure` — Document Outline

**Description:** Get the structure/outline of a markdown file. Shows heading hierarchy with token counts.

**Prerequisites:** None (parses the file directly).

**Input Schema:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | `string` | **Yes** | — | Path to the markdown file |

**Handler:** `handleMdStructure` calls `parseFile()` from `src/parser/parser.ts` and formats the heading tree.

**Output format:** Indented heading tree with metadata annotations and token counts:

```
# Document Title
Path: docs/guide.md
Total tokens: 2500

# Introduction (150 tokens)
  ## Getting Started [code] (400 tokens)
    ### Prerequisites [list] (120 tokens)
  ## Configuration [table] (300 tokens)
```

---

### 3.4 `md_keyword_search` — Keyword/Structural Search

**Description:** Search markdown documents by keyword search (headings, code blocks, lists, tables).

**Prerequisites:** Index must exist.

**Input Schema:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `heading` | `string` | No | — | Filter by heading pattern (regex) |
| `path_filter` | `string` | No | — | Glob pattern to filter files |
| `has_code` | `boolean` | No | — | Only sections with code blocks |
| `has_list` | `boolean` | No | — | Only sections with lists |
| `has_table` | `boolean` | No | — | Only sections with tables |
| `limit` | `number` | No | `20` | Maximum results |

**Note:** No parameters are required. All parameters are optional filters. At least one filter should be provided for meaningful results.

**Handler:** `handleMdKeywordSearch` calls `search()` from `src/search/searcher.ts`.

**Output format:** Numbered list with heading, metadata tags, document path, and token count:

```
Found 5 sections:

1. **API Authentication** [code]
   docs/api.md (350 tokens)

2. **Database Setup** [code, table]
   docs/setup.md (200 tokens)
```

---

### 3.5 `md_index` — Build/Rebuild Index

**Description:** Build or rebuild the index for a directory. Required before using search tools.

**Prerequisites:** None.

**Input Schema:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | `string` | No | `.` | Directory to index |
| `force` | `boolean` | No | `false` | Force full rebuild |

**Handler:** `handleMdIndex` calls `buildIndex()` from `src/index/indexer.ts`.

**Output format:** Summary of indexed items:

```
Indexed 42 documents, 156 sections, 89 links in 1250ms
```

**Important:** This tool builds the structural index only (documents, sections, links). It does **not** build embeddings for semantic search. Embeddings must be built separately via the CLI (`mdcontext index --embed`). The MCP server has no tool to build embeddings.

---

### 3.6 `md_links` — Outgoing Links

**Description:** Get outgoing links from a markdown file. Shows what files this document references/links to.

**Prerequisites:** Index must exist.

**Input Schema:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | `string` | **Yes** | — | Path to the markdown file |

**Handler:** `handleMdLinks` calls `getOutgoingLinks()` from `src/index/indexer.ts`.

**Output format:**

```
Outgoing links from README.md:

  -> docs/api.md
  -> docs/setup.md
  -> CONTRIBUTING.md

Total: 3 links
```

---

### 3.7 `md_backlinks` — Incoming Links

**Description:** Get incoming links to a markdown file. Shows what files reference/link to this document.

**Prerequisites:** Index must exist.

**Input Schema:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | `string` | **Yes** | — | Path to the markdown file |

**Handler:** `handleMdBacklinks` calls `getIncomingLinks()` from `src/index/indexer.ts`.

**Output format:**

```
Incoming links to docs/api.md:

  <- README.md
  <- docs/guide.md

Total: 2 backlinks
```

---

## 4. Tool Dependency Map

```
Tool                 Requires Index?   Requires Embeddings?   Works Standalone?
─────────────────────────────────────────────────────────────────────────────────
md_index             No                No                     Yes (creates index)
md_context           No                No                     Yes (file parser)
md_structure         No                No                     Yes (file parser)
md_keyword_search    Yes               No                     No
md_search            Yes               Yes                    No
md_links             Yes               No                     No
md_backlinks         Yes               No                     No
```

Recommended initialization sequence:
1. Call `md_index` to build the structural index
2. Build embeddings via CLI: `mdcontext index --embed` (no MCP tool for this)
3. Then `md_search` becomes available

---

## 5. Error Handling

All tool handlers use Effect's `catchAll` at the MCP boundary layer to convert typed errors into `{ content: [{ type: 'text', text: 'Error: ...' }], isError: true }` responses. This is intentional -- MCP protocol requires JSON error responses.

Error types that can surface through MCP tools:

| Error | Code | Relevant Tools |
|-------|------|----------------|
| `IndexNotFoundError` | E400 | md_search, md_keyword_search, md_links, md_backlinks, md_index |
| `EmbeddingsNotFoundError` | E501 | md_search |
| `FileReadError` | E100 | md_context, md_structure |
| `ParseError` | E200 | md_context, md_structure |
| `ApiKeyMissingError` | E300 | md_search |
| `EmbeddingError` | E310-E319 | md_search |
| `DimensionMismatchError` | E601 | md_search |

---

## 6. Index Storage

Index files are stored in `.mdcontext/` relative to the root path:

```
.mdcontext/
  config.json           # Index configuration
  indexes/
    documents.json      # Document metadata (DocumentIndex)
    sections.json       # Section index (SectionIndex)
    links.json          # Link graph (LinkIndex)
  cache/
    parsed/             # Cached parsed documents
  embeddings/
    {namespace}/        # Namespaced vector stores per provider/model/dimensions
      vectors.bin       # HNSW vector index
      metadata.json     # Provider metadata
  active-provider.json  # Which embedding namespace is active
```

Index version: `1` (from `INDEX_VERSION` constant in `src/index/types.ts`).

---

## 7. Key Architecture Details

- **Runtime:** Effect-TS for all async operations, error handling, and configuration.
- **Parser:** Uses `remark` + `remark-gfm` for markdown parsing (unified ecosystem).
- **Token counting:** Uses `tiktoken` for accurate GPT-compatible token counting.
- **Vector search:** HNSW algorithm via `hnswlib-node` for fast approximate nearest neighbor search.
- **Embedding providers:** OpenAI (default), Ollama, LM Studio, OpenRouter, Voyage.
- **Keyword search:** BM25 via `wink-bm25-text-search` + regex heading/metadata filters.
- **No state between calls:** Each tool handler resolves paths and loads indexes fresh. No in-memory caching across MCP calls.

---

## 8. Exposed Resources and Prompts

**Resources:** None. The server does not expose any MCP resources.

**Prompts:** None. The server does not expose any MCP prompts.

The server is purely tools-based. All 7 tools are listed in the `ListToolsRequestSchema` handler and dispatched via the `CallToolRequestSchema` handler using a switch statement on the tool name.

---

## 9. Limitations and Gaps

1. **No embedding build tool:** The MCP server can search embeddings but cannot build them. Embedding creation requires the CLI (`mdcontext index --embed`), which involves interactive cost confirmation, provider selection, and progress reporting that doesn't map well to MCP's request/response model.

2. **No watch mode:** The CLI supports `mdcontext index --watch` for file watching, but this is not exposed via MCP.

3. **No AI summarization:** The CLI supports `--summarize` for AI-powered search result summaries, but this is not exposed via MCP.

4. **No content search:** The CLI's content-level regex search (`searchContent`) is not exposed. Only heading-level keyword search is available via `md_keyword_search`.

5. **No section filtering:** The CLI supports `--section "Setup"` for extracting specific sections, but `md_context` does not expose this parameter.

6. **CWD-bound:** The root path is fixed to `process.cwd()` at startup. There is no way to change the root directory after the server starts.
