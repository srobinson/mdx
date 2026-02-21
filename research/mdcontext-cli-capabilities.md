---
title: "mdcontext CLI — Commands, Indexing, and Search"
type: research
tags: [mdcontext, cli, indexing, search, helioy]
summary: "Complete reference of mdcontext CLI commands, indexing pipeline, search modes, and configuration"
status: active
created: 2026-02-21
updated: 2026-02-21
project: mdcontext
---

# mdcontext CLI — Commands, Indexing, and Search

**Version:** 0.1.0
**Source:** `/Users/alphab/Dev/LLM/DEV/mdcontext`
**Binary:** `mdcontext` (CLI) + `mdcontext-mcp` (MCP server)
**Runtime:** Node.js 18+, ESM, built with tsup
**Framework:** Effect (for dependency injection, error handling, config), @effect/cli (command parsing)

## Architecture Overview

mdcontext is a token-efficient markdown analysis tool for LLM consumption. It parses markdown files into structured indexes (documents, sections, links), optionally builds vector embeddings for semantic search, and outputs compressed context suitable for LLM prompts.

Key design principles:

- **80%+ token savings** over raw markdown dumps
- **Layered configuration** with precedence: CLI flags > env vars > config file > defaults
- **Effect-based** architecture with typed errors, dependency injection, and structured concurrency
- **Incremental indexing** -- unchanged files are skipped based on content hash and mtime

---

## 1. Commands

mdcontext registers **10 commands** via `@effect/cli`:

| Command      | Description                        | Has Subcommands                     |
| ------------ | ---------------------------------- | ----------------------------------- |
| `index`      | Index markdown files               | No                                  |
| `search`     | Search by meaning or structure     | No                                  |
| `context`    | Get LLM-ready summary              | No                                  |
| `tree`       | Show file tree or document outline | No                                  |
| `links`      | Show outgoing links from a file    | No                                  |
| `backlinks`  | Show incoming links to a file      | No                                  |
| `duplicates` | Detect duplicate content           | No                                  |
| `stats`      | Show index statistics              | No                                  |
| `config`     | Configuration management           | Yes (init, show, check)             |
| `embeddings` | Manage embedding namespaces        | Yes (list, switch, remove, current) |

### Global Options

| Flag              | Short | Description                             |
| ----------------- | ----- | --------------------------------------- |
| `--config <file>` | `-c`  | Custom config file path (JS, TS, JSON)  |
| `--json`          |       | Output as JSON (all commands)           |
| `--pretty`        |       | Pretty-print JSON output (all commands) |
| `--help`          | `-h`  | Show help                               |
| `--version`       | `-v`  | Show version                            |

---

## 2. `mdcontext index [path]`

Indexes markdown files for fast searching. This must be run before search, stats, backlinks, or duplicates.

**Source:** `src/cli/commands/index-cmd.ts` (480 LOC)

### Options

| Flag                     | Short | Type    | Default | Description                                                       |
| ------------------------ | ----- | ------- | ------- | ----------------------------------------------------------------- |
| `--embed`                | `-e`  | boolean | false   | Build semantic embeddings (enables AI-powered search)             |
| `--no-embed`             |       | boolean | false   | Skip the prompt to enable semantic search                         |
| `--exclude`              | `-x`  | string  |         | Additional patterns to exclude (comma-separated)                  |
| `--no-gitignore`         |       | boolean | false   | Ignore .gitignore file                                            |
| `--provider`             |       | choice  |         | Embedding provider: openai, ollama, lm-studio, openrouter, voyage |
| `--provider-model`       |       | string  |         | Model name (e.g., nomic-embed-text for Ollama)                    |
| `--provider-base-url`    |       | string  |         | Custom API base URL                                               |
| `--timeout`              | `-t`  | integer | 30000   | Embedding API timeout in milliseconds                             |
| `--watch`                | `-w`  | boolean | false   | Watch for changes and re-index automatically                      |
| `--force`                |       | boolean | false   | Rebuild from scratch, ignoring cache                              |
| `--hnsw-m`               |       | integer | 16      | HNSW M parameter (max connections per node)                       |
| `--hnsw-ef-construction` |       | integer | 200     | HNSW efConstruction parameter                                     |
| `--json`                 |       | boolean | false   | Output results as JSON                                            |
| `--pretty`               |       | boolean | false   | Pretty-print JSON output                                          |

### What `mdcontext index` Produces

Index data is stored in `.mdcontext/` in the project root:

```
.mdcontext/
  config.json           # Index configuration metadata
  indexes/
    documents.json      # Document metadata (id, path, title, mtime, hash, tokenCount, sectionCount)
    sections.json       # Section index (id, documentId, heading, level, startLine, endLine, tokenCount, hasCode, hasList, hasTable)
    links.json          # Link graph (forward links, backward links, broken links)
  cache/
    parsed/             # Cached parsed documents
  embeddings/           # Vector embeddings (when --embed is used)
    <namespace>/        # Provider-specific embedding namespace
      vectors.bin       # HNSW vector index (hnswlib-node)
      metadata.json     # Embedding metadata (provider, model, dimensions, cost)
```

**Index version:** 1 (defined in `src/index/types.ts`)

### Indexing Pipeline

1. **File discovery:** Walks directory tree, applies ignore patterns (see section 6), filters by extension (`.md`, `.mdx`)
2. **Incremental check:** Compares file hash + mtime against existing index; skips unchanged files
3. **Parsing:** Uses remark/unified to parse markdown into AST, extracts sections (headings), code blocks, lists, tables, links
4. **Token counting:** Uses tiktoken to count tokens per section and document
5. **Storage:** Writes JSON indexes for documents, sections, and links
6. **BM25 index:** Builds a BM25 text search index (wink-bm25-text-search) for keyword search
7. **Embeddings (optional):** Calls embedding provider API, stores vectors in HNSW index (hnswlib-node)

### Embedding Providers

| Provider   | Type  | Model Default          | API Key            |
| ---------- | ----- | ---------------------- | ------------------ |
| openai     | Cloud | text-embedding-3-small | OPENAI_API_KEY     |
| ollama     | Local | nomic-embed-text       | None needed        |
| lm-studio  | Local | (loaded model)         | None needed        |
| openrouter | Cloud | (varies)               | OPENROUTER_API_KEY |
| voyage     | Cloud | (varies)               | VOYAGE_API_KEY     |

### Watch Mode

Uses chokidar to watch for file changes. Re-indexes on file create/modify/delete events.

---

## 3. `mdcontext search <query> [path]`

Search markdown content by meaning (semantic), keyword (BM25/boolean), or hybrid (both combined with RRF).

**Source:** `src/cli/commands/search.ts` (1281 LOC)

### Options

| Flag               | Short | Type    | Default  | Description                                      |
| ------------------ | ----- | ------- | -------- | ------------------------------------------------ |
| `--keyword`        | `-k`  | boolean | false    | Force keyword search                             |
| `--heading-only`   | `-H`  | boolean | false    | Search headings only                             |
| `--mode`           | `-m`  | choice  | auto     | Force mode: semantic, keyword, or hybrid         |
| `--limit`          | `-n`  | integer | 10       | Maximum results                                  |
| `--threshold`      |       | float   | 0.35     | Similarity threshold for semantic search (0-1)   |
| `-C`               |       | integer |          | Context lines before AND after each match        |
| `-B`               |       | integer |          | Context lines before each match                  |
| `-A`               |       | integer |          | Context lines after each match                   |
| `--provider`       |       | choice  |          | Embedding provider for semantic search           |
| `--timeout`        |       | integer | 30000    | Embedding API timeout                            |
| `--rerank`         | `-r`  | boolean | false    | Re-rank with cross-encoder (~90MB model)         |
| `--rerank-init`    |       | boolean | false    | Pre-download cross-encoder model                 |
| `--quality`        | `-q`  | choice  | balanced | Search quality: fast, balanced, thorough         |
| `--hyde`           |       | boolean | false    | Use HyDE query expansion                         |
| `--fuzzy`          | `-f`  | boolean | false    | Fuzzy matching for typo tolerance                |
| `--stem`           |       | boolean | false    | Word stemming (fail -> failure, failed)          |
| `--fuzzy-distance` |       | integer | 2        | Max edit distance for fuzzy matching             |
| `--refine`         |       | string  |          | Additional filter to narrow results (repeatable) |
| `--summarize`      | `-s`  | boolean | false    | Generate AI summary of results                   |
| `--yes`            | `-y`  | boolean | false    | Skip cost confirmation                           |
| `--stream`         |       | boolean | false    | Stream AI summary output                         |

### Search Modes

**Auto-detection logic (priority order):**

1. `--mode <mode>` flag overrides everything
2. `--keyword` / `-k` flag forces keyword mode
3. Boolean/phrase patterns detected (AND, OR, NOT, "quoted") -> keyword mode
4. Regex patterns detected -> keyword mode
5. If hybrid is available (both BM25 + embeddings exist) -> hybrid mode
6. If embeddings exist -> semantic mode
7. Otherwise -> keyword mode

### Keyword Search

- Uses BM25 (wink-bm25-text-search) for relevance-ranked text matching
- Supports **boolean operators:** AND, OR, NOT (case-insensitive)
- Supports **quoted phrases:** `"exact phrase"` for exact matching
- Supports **grouping:** `(term1 OR term2) AND term3`
- Supports **regex patterns** on headings with `-H` flag
- Supports **fuzzy matching** (`--fuzzy`) with configurable edit distance
- Supports **stemming** (`--stem`) for morphological matching
- Operator precedence: NOT > AND > OR

**Source:** `src/search/query-parser.ts` -- recursive descent parser producing an AST with node types: term, phrase, and, or, not.

### Semantic Search

- Embeds query using the same provider as the index
- Searches HNSW vector index for nearest neighbors
- Filters by similarity threshold (default: 0.35)
- Reports below-threshold counts when 0 results found

### Hybrid Search

- **Reciprocal Rank Fusion (RRF):** Combines BM25 and semantic rankings
- Formula: `score(doc) = sum(weight / (k + rank))`, k=60
- Provides 15-30% recall improvement over single-method retrieval
- **Source:** `src/search/hybrid-search.ts`

### Advanced Search Features

| Feature           | Flag                               | Description                                                                                                                                               |
| ----------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Quality modes** | `--quality fast/balanced/thorough` | Controls HNSW efSearch parameter (64/100/256)                                                                                                             |
| **Re-ranking**    | `--rerank`                         | Cross-encoder model for 20-35% precision boost. Requires `@huggingface/transformers`                                                                      |
| **HyDE**          | `--hyde`                           | Hypothetical Document Embeddings -- generates hypothetical answer via LLM, searches with that embedding. +10-30% recall on complex queries, ~1-2s latency |
| **Refine**        | `--refine <term>`                  | Post-filter results by additional terms (checks actual section content)                                                                                   |
| **Context lines** | `-C`, `-B`, `-A`                   | grep-style context lines around matches                                                                                                                   |

### AI Summarization

When `--summarize` is passed, search results are piped to an AI provider for natural language summary:

- **CLI providers (free):** claude, copilot, cline, aider, opencode, amp
- **API providers (paid):** deepseek, anthropic, openai, gemini, qwen
- Auto-detects installed CLI tools; shows cost estimate for paid providers
- Supports streaming output (`--stream`)

---

## 4. `mdcontext context <files...>`

Get LLM-ready summaries from one or more markdown files.

**Source:** `src/cli/commands/context.ts` (285 LOC)

### Options

| Flag         | Short | Type    | Default | Description                               |
| ------------ | ----- | ------- | ------- | ----------------------------------------- |
| `--tokens`   | `-t`  | integer | 2000    | Token budget for output                   |
| `--brief`    |       | boolean | false   | Minimal output (headings only)            |
| `--full`     |       | boolean | false   | Include full content (no summarization)   |
| `--section`  | `-S`  | string  |         | Filter by section name, number, or glob   |
| `--sections` |       | boolean | false   | List available sections                   |
| `--shallow`  |       | boolean | false   | Exclude nested subsections when filtering |
| `--exclude`  | `-x`  | string  |         | Exclude sections by pattern (repeatable)  |

### Summarization Levels

| Level     | Description                            | Token Budget       |
| --------- | -------------------------------------- | ------------------ |
| `brief`   | Headings and key points only           | 100 tokens default |
| `summary` | Balanced summary (default)             | 500 tokens default |
| `full`    | Include full content, no summarization | Unlimited          |

### Section Filtering

- `--sections` lists all sections with numbers and token counts
- `--section "Setup"` extracts by heading name
- `--section "2.1"` extracts by section number
- `--section "API*"` extracts by glob pattern
- `--shallow` skips nested subsections
- `--exclude "License"` / `-x "Test*"` excludes matching sections

---

## 5. `mdcontext tree [path|file]`

Auto-detects whether the argument is a file or directory.

**Source:** `src/cli/commands/tree.ts` (128 LOC)

- **Directory:** Lists all markdown files in the directory
- **File:** Shows document outline (heading hierarchy with token counts per section)

---

## 6. `mdcontext links <file>` / `mdcontext backlinks <file>`

**Source:** `src/cli/commands/links.ts` (52 LOC), `src/cli/commands/backlinks.ts` (54 LOC)

| Command            | Description                | Options                               |
| ------------------ | -------------------------- | ------------------------------------- |
| `links <file>`     | Outgoing links from a file | `--root` / `-r`, `--json`, `--pretty` |
| `backlinks <file>` | Incoming links to a file   | `--root` / `-r`, `--json`, `--pretty` |

Backlinks requires the index to exist (reads the link graph from `.mdcontext/indexes/links.json`).

---

## 7. `mdcontext duplicates [path]`

Detect duplicate content in markdown files.

**Source:** `src/cli/commands/duplicates.ts` (122 LOC)

### Options

| Flag           | Short | Type    | Default | Description                                |
| -------------- | ----- | ------- | ------- | ------------------------------------------ |
| `--min-length` |       | integer | 50      | Minimum content length (chars) to consider |
| `--path`       | `-p`  | string  |         | Filter by document path pattern (glob)     |

Reports duplicate groups with exact match or similarity percentage.

---

## 8. `mdcontext stats [path]`

Show index statistics.

**Source:** `src/cli/commands/stats.ts` (149 LOC)

Reports:

- Document count, total tokens, avg tokens per doc
- Token distribution (min, median, max)
- Section count by heading level (h1, h2, h3, etc.)
- Embedding stats (vector count, provider, model, dimensions, cost)

---

## 9. `mdcontext config <command>`

Configuration management with three subcommands.

**Source:** `src/cli/commands/config-cmd.ts` (642 LOC)

### Subcommands

#### `config init`

Creates a starter config file in the current directory.

| Flag       | Short | Type    | Default | Description               |
| ---------- | ----- | ------- | ------- | ------------------------- |
| `--format` | `-f`  | choice  | js      | Config format: js or json |
| `--force`  |       | boolean | false   | Overwrite existing config |

- JS format includes JSDoc type annotations for IDE autocompletion
- JSON format includes `$schema` for validation

#### `config show`

Displays the location of the active config file. Searches for these files in order:

1. `mdcontext.config.ts`
2. `mdcontext.config.js`
3. `mdcontext.config.mjs`
4. `mdcontext.config.json`
5. `.mdcontextrc`
6. `.mdcontextrc.json`

#### `config check`

Validates and shows effective configuration with source annotations (default / file / env).

Displays every config key with its effective value and where it came from:

- `(default)` -- built-in default
- `(from config file)` -- from config file
- `(from environment)` -- from `MDCONTEXT_*` environment variable

---

## 10. `mdcontext embeddings <command>`

Manage embedding namespaces (multiple providers/models can coexist).

**Source:** `src/cli/commands/embeddings.ts` (529 LOC)

### Subcommands

| Subcommand                  | Description                                                       |
| --------------------------- | ----------------------------------------------------------------- |
| `list [path]`               | List all embedding namespaces (interactive picker in TTY)         |
| `current [path]`            | Show active namespace (provider, model, dimensions)               |
| `switch [namespace] [path]` | Switch to a different namespace (fuzzy match, interactive picker) |
| `remove <namespace> [path]` | Remove a namespace (`--force` / `-f` to remove active)            |

Namespace format: `<provider>/<model>` (e.g., `openai/text-embedding-3-small`)

Switching namespaces is instant -- no rebuild required. Each namespace stores its own HNSW index separately.

---

## 11. Configuration System

### Config Schema

**Source:** `src/config/schema.ts` (603 LOC)

The full config schema has 7 top-level sections:

#### `index`

| Key               | Type     | Default                                     | Description                   |
| ----------------- | -------- | ------------------------------------------- | ----------------------------- |
| `maxDepth`        | number   | 10                                          | Max directory traversal depth |
| `excludePatterns` | string[] | `['node_modules', '.git', 'dist', 'build']` | Glob patterns to exclude      |
| `fileExtensions`  | string[] | `['.md', '.mdx']`                           | File extensions to index      |
| `followSymlinks`  | boolean  | false                                       | Follow symbolic links         |
| `indexDir`        | string   | `.mdcontext`                                | Index storage directory       |

#### `search`

| Key                  | Type    | Default | Description                                   |
| -------------------- | ------- | ------- | --------------------------------------------- |
| `defaultLimit`       | number  | 10      | Default result count                          |
| `maxLimit`           | number  | 100     | Maximum result count                          |
| `minSimilarity`      | number  | 0.35    | Minimum similarity threshold                  |
| `includeSnippets`    | boolean | true    | Include content snippets                      |
| `snippetLength`      | number  | 200     | Max snippet length (chars)                    |
| `autoIndexThreshold` | number  | 10      | Auto-create semantic index if under N seconds |

#### `embeddings`

| Key                  | Type    | Default                  | Description                    |
| -------------------- | ------- | ------------------------ | ------------------------------ |
| `provider`           | literal | `openai`                 | Embedding provider             |
| `baseURL`            | string? | (provider default)       | Custom API base URL            |
| `model`              | string  | `text-embedding-3-small` | Embedding model                |
| `dimensions`         | number  | 512                      | Vector dimensions              |
| `batchSize`          | number  | 100                      | API call batch size            |
| `maxRetries`         | number  | 3                        | Max retries for failed calls   |
| `retryDelayMs`       | number  | 1000                     | Retry delay (ms)               |
| `timeoutMs`          | number  | 30000                    | Request timeout (ms)           |
| `apiKey`             | string? |                          | API key (usually from env)     |
| `hnswM`              | number  | 16                       | HNSW max connections per node  |
| `hnswEfConstruction` | number  | 200                      | HNSW construction search width |

#### `summarization`

| Key                  | Type   | Default | Description                    |
| -------------------- | ------ | ------- | ------------------------------ |
| `briefTokenBudget`   | number | 100     | Token budget for brief level   |
| `summaryTokenBudget` | number | 500     | Token budget for summary level |
| `compressionRatio`   | number | 0.3     | Target compression ratio       |
| `minSectionTokens`   | number | 20      | Minimum tokens per section     |
| `maxTopics`          | number | 10      | Max topics to extract          |
| `minPartialBudget`   | number | 50      | Min budget for partial content |

#### `aiSummarization`

| Key        | Type    | Default  | Description                     |
| ---------- | ------- | -------- | ------------------------------- |
| `mode`     | literal | `cli`    | Mode: cli (free) or api (paid)  |
| `provider` | literal | `claude` | Provider name                   |
| `model`    | string? |          | Model name (API providers only) |
| `stream`   | boolean | false    | Enable streaming output         |
| `baseURL`  | string? |          | Custom API base URL             |
| `apiKey`   | string? |          | API key                         |

#### `output`

| Key          | Type    | Default | Description           |
| ------------ | ------- | ------- | --------------------- |
| `format`     | literal | `text`  | Default output format |
| `color`      | boolean | true    | Terminal colors       |
| `prettyJson` | boolean | true    | Pretty-print JSON     |
| `verbose`    | boolean | false   | Verbose output        |
| `debug`      | boolean | false   | Debug information     |

#### `paths`

| Key          | Type    | Default            | Description             |
| ------------ | ------- | ------------------ | ----------------------- |
| `root`       | string? | cwd                | Root directory          |
| `configFile` | string? | (auto-detected)    | Custom config file path |
| `cacheDir`   | string  | `.mdcontext/cache` | Cache directory         |

### Configuration Precedence

From highest to lowest priority:

1. **CLI flags** (e.g., `--limit 5`)
2. **Environment variables** (e.g., `MDCONTEXT_SEARCH_DEFAULTLIMIT=5`)
3. **Config file** (`mdcontext.config.js` / `.mdcontextrc`)
4. **Built-in defaults**

### Config File Formats

Searched in order:

1. `mdcontext.config.ts` (requires TS loader)
2. `mdcontext.config.js` (ESM, JSDoc types recommended)
3. `mdcontext.config.mjs`
4. `mdcontext.config.json`
5. `.mdcontextrc` (JSON)
6. `.mdcontextrc.json`

JS/TS files are loaded via dynamic import. JSON files are loaded synchronously.

### Environment Variables

All config keys can be set via `MDCONTEXT_` prefix:

- `MDCONTEXT_INDEX_MAXDEPTH=5`
- `MDCONTEXT_SEARCH_DEFAULTLIMIT=20`
- `MDCONTEXT_EMBEDDINGS_PROVIDER=ollama`
- `MDCONTEXT_AISUMMARIZATION_MODE=api`
- `MDCONTEXT_AISUMMARIZATION_PROVIDER=deepseek`

Provider-specific API keys:

- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `DEEPSEEK_API_KEY`

---

## 12. Ignore Patterns (.mdcontextignore)

**Source:** `src/index/ignore-patterns.ts` (305 LOC)

mdcontext honors ignore files using the `ignore` npm package (same algorithm as `.gitignore`).

### Precedence (highest to lowest)

1. CLI `--exclude` flag
2. `MDCONTEXT_INDEX_EXCLUDEPATTERNS` env var
3. Config file `index.excludePatterns`
4. `.mdcontextignore` file (project root)
5. `.gitignore` file (project root)
6. Built-in defaults: `['node_modules', '.git', 'dist', 'build']`

### .mdcontextignore Format

Same syntax as `.gitignore`:

- One pattern per line
- Lines starting with `#` are comments
- Empty lines are ignored
- Standard glob patterns supported
- Negation with `!` prefix

### Disabling

- `--no-gitignore` flag skips `.gitignore` loading
- The `honorMdcontextignore` option can be set to false programmatically

---

## 13. MCP Integration

**Source:** `src/mcp/server.ts` (612 LOC)
**Binary:** `mdcontext-mcp`

Exposes 7 MCP tools for Claude Desktop / Claude Code integration:

| Tool                | Description                                                                |
| ------------------- | -------------------------------------------------------------------------- |
| `md_search`         | Semantic search with query, limit, path_filter, threshold params           |
| `md_context`        | Get LLM-ready summary (path, level: full/summary/brief, max_tokens)        |
| `md_structure`      | Get heading hierarchy/outline for a file                                   |
| `md_keyword_search` | Keyword search with heading pattern, has_code, has_list, has_table filters |
| `md_index`          | Build/rebuild index (path, force)                                          |
| `md_links`          | Outgoing links from a file                                                 |
| `md_backlinks`      | Incoming links to a file                                                   |

### Setup

Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

---

## 14. Setup / Init

There is no standalone `init` or `setup` command at the top level. The initialization workflow is:

1. **Install:** `npm install -g mdcontext`
2. **Index:** `mdcontext index [path]` -- creates `.mdcontext/` directory with structural indexes
3. **Embed (optional):** `mdcontext index --embed` -- adds semantic embeddings
4. **Config (optional):** `mdcontext config init` -- creates `mdcontext.config.js` in cwd

The `config init` subcommand is the closest thing to a project setup command. It generates a fully-documented config file with all default values.

---

## 15. Argv Preprocessing

**Source:** `src/cli/argv-preprocessor.ts` (202 LOC)

Effect CLI requires flags before positional args, but mdcontext allows flexible positioning:

```bash
# Both work:
mdcontext search "query" --limit 5
mdcontext search --limit 5 "query"
```

The preprocessor reorders argv so flags come before positionals. It also validates flags against per-command schemas and provides typo suggestions via Levenshtein distance.

---

## 16. Error Handling

**Source:** `src/cli/error-handler.ts`, `src/errors/index.ts`

Uses Effect's tagged error system with distinct error types:

- `FileReadError`, `FileWriteError`, `DirectoryCreateError`, `DirectoryWalkError`
- `ParseError`, `IndexCorruptedError`, `IndexNotFoundError`
- `ApiKeyMissingError`, `ApiKeyInvalidError`, `EmbeddingError`
- `ConfigError`, `CliValidationError`
- `VectorStoreError`, `RerankerError`

The CLI catches all errors at the boundary and formats them as user-friendly messages with suggestions.

---

## 17. Key Dependencies

| Package                   | Purpose                                  |
| ------------------------- | ---------------------------------------- |
| effect / @effect/cli      | Core framework, CLI parsing              |
| remark / unified          | Markdown parsing                         |
| tiktoken                  | Token counting                           |
| hnswlib-node              | Vector similarity search (HNSW)          |
| wink-bm25-text-search     | BM25 keyword search                      |
| openai                    | OpenAI API client (embeddings)           |
| ignore                    | .gitignore-compatible pattern matching   |
| gray-matter               | YAML frontmatter parsing                 |
| chokidar                  | File watching                            |
| stemmer                   | Porter stemming for search               |
| @clack/prompts            | Interactive prompts (embeddings command) |
| @modelcontextprotocol/sdk | MCP server implementation                |
| @msgpack/msgpack          | Binary serialization                     |
