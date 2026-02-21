---
title: "mdcontext — Complete Reference"
type: reference
tags: [mdcontext, mcp, cli, architecture, helioy, reference]
summary: "Synthesised reference covering mdcontext MCP server, CLI, architecture, and project status — distilled from 4 independent research documents"
status: active
created: 2026-02-21
updated: 2026-02-21
project: mdcontext
related:
  [
    mdcontext-mcp-server,
    mdcontext-cli-capabilities,
    mdcontext-architecture,
    mdcontext-linear-status,
  ]
---

# mdcontext -- Complete Reference

**Version:** 0.1.0
**Source:** `/Users/alphab/Dev/LLM/DEV/mdcontext`
**Binaries:** `mdcontext` (CLI), `mdcontext-mcp` (MCP server)
**Runtime:** Node.js 18+, ESM, TypeScript + Effect
**Project status:** Standalone Linear project canceled (48/50 issues Done). Tool is feature-complete. Active integration into Helioy ecosystem.

---

## Quick Start

### 1. Install

```bash
npm install -g mdcontext
```

### 2. Index a markdown directory

```bash
cd /path/to/markdown-docs
mdcontext index .
```

This creates `.mdcontext/` with structural indexes (documents, sections, links). Takes seconds for typical doc sets.

### 3. Search (keyword -- works immediately)

```bash
mdcontext search "authentication" --keyword
mdcontext search "setup AND docker" --keyword
```

### 4. Add semantic search (optional, requires API key)

```bash
export OPENAI_API_KEY="sk-..."
mdcontext index --embed
```

Now semantic and hybrid search work:

```bash
mdcontext search "how do I configure auth?"           # auto-selects hybrid
mdcontext search "how do I configure auth?" --mode semantic
```

### 5. Get LLM-ready context from a file

```bash
mdcontext context README.md                    # summary (default)
mdcontext context README.md --brief            # headings only
mdcontext context README.md --full             # complete content
mdcontext context README.md --section "Setup"  # specific section
```

### 6. Set up MCP server (Claude Desktop or Claude Code)

Add to MCP config (e.g., `~/.claude.json` or Claude Desktop config):

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

The MCP server uses `process.cwd()` as its root. The working directory where the MCP client spawns the process determines which markdown files are accessible.

### 7. Initialize (from MCP, first call)

Call `md_index` tool to build the structural index. Then `md_keyword_search`, `md_links`, `md_backlinks` become available. For `md_search` (semantic), embeddings must be built via CLI: `mdcontext index --embed`.

---

## MCP Server Tools (7 tools)

Server name: `mdcontext-mcp`. Transport: stdio. Capabilities: tools only (no resources, no prompts).

### Tool Reference

| Tool                | Purpose                             | Requires Index | Requires Embeddings |
| ------------------- | ----------------------------------- | :------------: | :-----------------: |
| `md_index`          | Build/rebuild structural index      |       No       |         No          |
| `md_context`        | LLM-ready summary of a file         |       No       |         No          |
| `md_structure`      | Heading hierarchy with token counts |       No       |         No          |
| `md_keyword_search` | BM25/structural search              |      Yes       |         No          |
| `md_search`         | Semantic vector search              |      Yes       |         Yes         |
| `md_links`          | Outgoing links from a file          |      Yes       |         No          |
| `md_backlinks`      | Incoming links to a file            |      Yes       |         No          |

### Tool Parameters

**md_search** (semantic search)

| Param         | Type   | Required | Default | Notes                               |
| ------------- | ------ | :------: | ------- | ----------------------------------- |
| `query`       | string |   Yes    | --      | Natural language query              |
| `limit`       | number |    No    | 5       | Max results                         |
| `path_filter` | string |    No    | --      | Glob pattern (e.g., `docs/**/*.md`) |
| `threshold`   | number |    No    | 0.35    | Similarity threshold 0-1            |

**md_context** (LLM-ready context)

| Param        | Type   | Required | Default   | Notes                                    |
| ------------ | ------ | :------: | --------- | ---------------------------------------- |
| `path`       | string |   Yes    | --        | File path (relative to root or absolute) |
| `level`      | enum   |    No    | `summary` | `full`, `summary`, or `brief`            |
| `max_tokens` | number |    No    | --        | Token budget                             |

**md_structure** (document outline)

| Param  | Type   | Required | Default |
| ------ | ------ | :------: | ------- |
| `path` | string |   Yes    | --      |

**md_keyword_search** (structural/keyword search)

| Param         | Type    | Required | Default | Notes                          |
| ------------- | ------- | :------: | ------- | ------------------------------ |
| `heading`     | string  |    No    | --      | Regex pattern for headings     |
| `path_filter` | string  |    No    | --      | Glob pattern for files         |
| `has_code`    | boolean |    No    | --      | Only sections with code blocks |
| `has_list`    | boolean |    No    | --      | Only sections with lists       |
| `has_table`   | boolean |    No    | --      | Only sections with tables      |
| `limit`       | number  |    No    | 20      | Max results                    |

**md_index** (build index)

| Param   | Type    | Required | Default |
| ------- | ------- | :------: | ------- |
| `path`  | string  |    No    | `.`     |
| `force` | boolean |    No    | false   |

**md_links** / **md_backlinks**

| Param  | Type   | Required |
| ------ | ------ | :------: |
| `path` | string |   Yes    |

### MCP Limitations

1. **No embedding build tool** -- MCP can search embeddings but cannot create them. Must use CLI: `mdcontext index --embed`.
2. **No content-level regex search** -- CLI `searchContent` is not exposed. Only heading-level keyword search via `md_keyword_search`.
3. **No section filtering** -- CLI `--section "Setup"` is not available in `md_context`.
4. **No watch mode** -- CLI `--watch` not exposed.
5. **No AI summarization** -- CLI `--summarize` not exposed.
6. **CWD-bound** -- Root path fixed at startup. Cannot change directories.

---

## CLI Commands (10 commands)

| Command                                      | Description                                                    |
| -------------------------------------------- | -------------------------------------------------------------- |
| `index [path]`                               | Build structural index (optionally with `--embed` for vectors) |
| `search <query> [path]`                      | Search by keyword, semantic, or hybrid                         |
| `context <files...>`                         | LLM-ready summaries with token budget control                  |
| `tree [path\|file]`                          | File tree (directory) or heading outline (file)                |
| `links <file>`                               | Outgoing links                                                 |
| `backlinks <file>`                           | Incoming links (requires index)                                |
| `duplicates [path]`                          | Detect duplicate content                                       |
| `stats [path]`                               | Index statistics                                               |
| `config <init\|show\|check>`                 | Configuration management                                       |
| `embeddings <list\|switch\|remove\|current>` | Manage embedding namespaces                                    |

### Global Flags

`--config <file>` (`-c`), `--json`, `--pretty`, `--help` (`-h`), `--version` (`-v`)

### Search Modes

Auto-detection priority:

1. `--mode <mode>` flag overrides everything
2. `--keyword` / `-k` forces keyword
3. Boolean/phrase patterns detected -> keyword
4. Regex patterns -> keyword
5. Both BM25 + embeddings exist -> hybrid (RRF fusion)
6. Embeddings only -> semantic
7. Fallback -> keyword

Key search flags: `--limit` (`-n`), `--threshold`, `--quality` (fast/balanced/thorough), `--rerank` (`-r`), `--hyde`, `--fuzzy` (`-f`), `--stem`, `--summarize` (`-s`), `--refine <term>`, `-C`/`-B`/`-A` (context lines).

---

## Architecture Essentials

### Data Model

- **MdDocument** -- root parsed representation of one `.md`/`.mdx` file
- **MdSection** -- hierarchical tree mirroring heading structure. Each section captures content between its heading and the next heading of equal/higher level
- **MdLink** -- internal/external/image links with section association
- **MdCodeBlock** -- fenced code blocks with language and section association

Document ID: `md5(relativePath).slice(0, 12)`. Section ID: `{docId}-{slugify(heading)}`. Content hash: `sha256(content).slice(0, 16)`.

### Index Storage (`.mdcontext/`)

```
.mdcontext/
  config.json                     -- Index config metadata
  indexes/
    documents.json                -- DocumentIndex (id, path, title, mtime, hash, tokens)
    sections.json                 -- SectionIndex (id, heading, level, lines, tokens, flags)
    links.json                    -- LinkIndex (forward, backward, broken links)
  bm25.json + bm25.meta.json     -- Serialized BM25 engine
  active-provider.json            -- Active embedding namespace
  embeddings/
    {provider}_{model}_{dims}/    -- Per-namespace storage
      vectors.bin                 -- HNSW binary index
      vectors.meta.bin            -- MessagePack metadata
  cache/parsed/                   -- Parsed document cache
```

### Indexing Pipeline

1. Walk directory (respects `.mdcontextignore`, `.gitignore`, config excludes)
2. Incremental check: skip if SHA-256 hash + mtime unchanged
3. Parse with remark/unified -> MdDocument
4. Count tokens with tiktoken heuristic (~3.5 chars/token for prose, ~2.5 for code)
5. Store document/section/link indexes as JSON
6. Build BM25 index (headings weighted 2x)
7. Optional: build HNSW embeddings via provider API

### Embedding Pipeline

- **Default:** OpenAI `text-embedding-3-small` at 512 dimensions (Matryoshka reduced)
- **Providers:** OpenAI, Ollama, LM Studio, OpenRouter, Voyage
- **Granularity:** Section-level (sections < 10 tokens skipped)
- **Embedding text format:** `# {heading}\nParent section: {parent}\nDocument: {title}\n\n{content}`
- **Batch size:** 100 texts per API call
- **Storage:** HNSW index (hnswlib-node, cosine distance), M=16, efConstruction=200
- **Namespaces:** Multiple providers coexist. Switching is instant (no rebuild).

### Search Algorithms

| Mode     | Engine                       | Notes                                                                |
| -------- | ---------------------------- | -------------------------------------------------------------------- |
| Keyword  | BM25 (wink-bm25-text-search) | Boolean AND/OR/NOT, quoted phrases, regex headings, fuzzy, stemming  |
| Semantic | HNSW nearest-neighbor        | Query embedding -> cosine similarity, heading/file importance boosts |
| Hybrid   | RRF fusion                   | `score = sum(weight / (60 + rank))`, 15-30% recall improvement       |

Advanced: HyDE (hypothetical document embedding, +10-30% recall on complex queries), cross-encoder re-ranking (Xenova/ms-marco-MiniLM-L-6-v2, +20-35% precision).

### Error System

Effect-TS tagged errors (E100-E900). MCP boundary converts to `{ isError: true, content: [{type: 'text', text: '...'}] }`. Key errors: `IndexNotFoundError` (E400), `EmbeddingsNotFoundError` (E501), `FileReadError` (E100), `ApiKeyMissingError` (E300).

---

## Configuration

### Precedence (highest to lowest)

1. CLI flags
2. Environment variables (`MDCONTEXT_*` prefix)
3. Config file (`mdcontext.config.js`, `.mdcontextrc`, etc.)
4. Built-in defaults

### Key Config Sections

| Section         | Key Settings                                                                                                |
| --------------- | ----------------------------------------------------------------------------------------------------------- |
| `index`         | `excludePatterns` (default: node_modules, .git, dist, build), `fileExtensions` (.md, .mdx), `maxDepth` (10) |
| `search`        | `defaultLimit` (10), `minSimilarity` (0.35), `snippetLength` (200)                                          |
| `embeddings`    | `provider` (openai), `model` (text-embedding-3-small), `dimensions` (512), `batchSize` (100)                |
| `summarization` | `briefTokenBudget` (100), `summaryTokenBudget` (500), `compressionRatio` (0.3)                              |

### Ignore Patterns (precedence)

1. CLI `--exclude`
2. `MDCONTEXT_INDEX_EXCLUDEPATTERNS` env var
3. Config `index.excludePatterns`
4. `.mdcontextignore` (gitignore syntax)
5. `.gitignore`
6. Built-in defaults

---

## Helioy Ecosystem Role

mdcontext is one of three individually-releasable libraries in the Helioy ecosystem:

| Library                       | Purpose                                                    | Language            |
| ----------------------------- | ---------------------------------------------------------- | ------------------- |
| **attention-matters (am)**    | Geometric memory engine (S3 manifold, SLERP drift)         | Rust                |
| **fmm (Frontmatter Matters)** | Code structural intelligence, auto-generated file metadata | Rust + npm          |
| **mdcontext**                 | Token-efficient markdown analysis, hybrid search           | TypeScript + Effect |

### How They Compose

```
fmm generates structural metadata for code files
    -> mdcontext indexes markdown documentation (including fmm output)
        -> attention-matters provides episodic memory across sessions
            -> nancyr orchestrates agents using all three
```

### mdcontext Strategy Within Helioy

- **mdcontext stays general-purpose open source** -- works on any markdown, zero conventions required.
- **Helioy-specific features live in a separate adapter layer** (ALP-637, Backlog):
  - Frontmatter-aware search filtering (tags, type, status, project)
  - Tag-based search/aggregation
  - `_versions/` directory handling
  - Integration with attention-matters (ingest indexed docs into AM)
- The adapter layer depends on mdcontext having an npm package with MCP serve command.

### ~/.mdx Knowledge Base

The centralized markdown doc store indexed by mdcontext in the Helioy ecosystem:

```
~/.mdx/
  research/        # Research findings
  decisions/       # ADRs
  design/          # Architecture docs, RFCs
  sessions/        # Session summaries
  projects/        # Per-project context
  retrospectives/  # Post-mortems
  reference/       # Stable reference material (this file lives here)
```

Each category has a `_versions/` subdirectory. Filenames are kebab-case slugs. Frontmatter dates are auto-managed by the helioy:knowledge-base skill.

---

## For Helioy Plugin (helioy:knowledge-base SKILL.md Body)

A knowledge-base skill that uses mdcontext MCP tools should include:

### Tool Availability Check

```
Before using search tools, verify index exists by calling md_structure on a known file.
If it fails with IndexNotFoundError, call md_index first.

For semantic search (md_search), embeddings must exist.
If md_search returns EmbeddingsNotFoundError, inform the user to run:
  mdcontext index --embed
from the ~/.mdx directory.
```

### Recommended Tool Usage Patterns

```
## Reading a document
1. md_structure {path} -- get outline and token counts
2. md_context {path, level: "summary"} -- get compressed summary
3. md_context {path, level: "full"} -- only if summary insufficient

## Finding documents by topic
1. md_keyword_search {heading: "pattern"} -- fast, structural
2. md_search {query: "natural language question"} -- semantic (needs embeddings)

## Understanding document relationships
1. md_links {path} -- what does this doc reference?
2. md_backlinks {path} -- what references this doc?

## Indexing after changes
1. md_index {} -- rebuilds structural index (incremental, fast)
   Note: does NOT rebuild embeddings
```

### Frontmatter Conventions (for adapter layer)

```
Every ~/.mdx document MUST have frontmatter with at minimum:
  title, type, tags, summary, status, created, updated, project

Types: research, design, decisions, sessions, projects, retrospectives, reference
Status: draft, active, archived
Tags: lowercase, kebab-case

The skill auto-manages created/updated dates.
Versioning: before overwriting, copy to _versions/{slug}.v{N}.md
```

### MCP Server Root Path

```
The mdcontext MCP server uses process.cwd() as root.
For ~/.mdx knowledge base access, the MCP config must ensure
the server spawns with cwd set to ~/.mdx (or equivalent expansion).

Example Claude Code config:
{
  "mcpServers": {
    "mdcontext": {
      "command": "mdcontext-mcp",
      "args": [],
      "cwd": "/Users/<username>/.mdx"
    }
  }
}
```

---

## Gaps, Contradictions, and Open Questions

### Contradictions Found Across Source Documents

1. **MCP tool count in architecture doc is wrong.** The architecture doc (Section 11) states the MCP server exposes "three tools" (`md_search`, `md_context`, `md_structure`). The MCP server doc and CLI doc both correctly state **7 tools**. The architecture doc was likely written earlier and not updated after the 4 additional tools were added.

2. **BM25 storage location.** The MCP server doc shows `bm25.json` and `bm25.meta.json` as absent from the directory layout (not listed). The architecture doc shows them at `.mdcontext/bm25.json`. The CLI doc does not mention them in the directory layout either. Actual storage location is `.mdcontext/bm25.json` + `.mdcontext/bm25.meta.json` per the architecture doc.

3. **Vector metadata format.** The MCP server doc says `metadata.json` (JSON) for embedding metadata. The architecture doc says `vectors.meta.bin` (MessagePack). The architecture doc is correct -- metadata was migrated from JSON to MessagePack. The MCP server doc is stale.

4. **Mode auto-detection order.** The CLI doc lists hybrid detection at position 5 ("if hybrid available -> hybrid"). The architecture doc lists it at position 2 ("hybrid if both exist"). These describe the same logic from different angles but the numbering differs. The CLI doc's ordering is more complete (includes boolean/regex pattern detection steps).

### Gaps

1. **No MCP tool for building embeddings.** This is the single largest gap for agent workflows. An agent cannot bootstrap full semantic search without human intervention at the CLI. The MCP server's `md_index` only builds structural indexes.

2. **No MCP tool for content-level search.** The CLI's `searchContent` regex search across section bodies is not exposed via MCP. Only heading-level keyword search is available.

3. **No MCP section filtering.** The CLI's `--section "Setup"` extraction is not available through `md_context`. An agent must read the full summary then parse it.

4. **Helioy adapter layer (ALP-637) is Backlog.** No frontmatter-aware search, no tag filtering, no `_versions/` handling via MCP yet. Blocked on mdcontext npm package having MCP serve command.

5. **Search & Embeddings Roadmap milestones show 0% progress** in Linear, but the architecture doc shows all 4 phases are implemented (hybrid search, Ollama provider, cross-encoder re-ranking, HyDE). The Linear milestones are stale and don't reflect actual completion.

6. **npm package name undocumented.** The package is not yet published to npm. ALP-654 mentions documenting package naming but is Backlog.

### Open Questions

1. **How should the MCP server handle `~/.mdx` vs project-local markdown?** Currently CWD-bound. Could there be multiple mdcontext MCP server instances (one for `~/.mdx`, one per project)?

2. **Will the Helioy adapter be a separate npm package or a mode within mdcontext?** ALP-637 describes it as an "adapter layer" but does not specify packaging.

3. **Embedding build via MCP** -- is there a plan to add an `md_embed` tool? The architecture doc notes that embedding creation involves interactive cost confirmation, but this could be simplified for MCP with a `--yes` equivalent parameter.

4. **KG validation (ALP-241)** -- all 11 sub-issues remain in Backlog despite the parent being In Progress. Is this still a priority given the standalone project was canceled?

---

## Key Dependencies

| Package                       | Purpose                                  |
| ----------------------------- | ---------------------------------------- |
| effect / @effect/cli          | Core framework, CLI, typed errors        |
| remark / unified / remark-gfm | Markdown parsing                         |
| tiktoken                      | Token counting (cl100k_base)             |
| hnswlib-node                  | HNSW vector search (cosine distance)     |
| wink-bm25-text-search         | BM25 keyword search                      |
| openai                        | Embedding API client                     |
| gray-matter                   | YAML frontmatter parsing                 |
| @modelcontextprotocol/sdk     | MCP server (v1.25.3)                     |
| @msgpack/msgpack              | Binary serialization for vector metadata |
| ignore                        | .gitignore-compatible pattern matching   |
| chokidar                      | File watching                            |
| @huggingface/transformers     | Cross-encoder re-ranking (optional)      |

---

## Source Documents

This reference was synthesised from:

1. `~/.mdx/research/mdcontext-mcp-server.md` -- MCP server tools, parameters, initialization
2. `~/.mdx/research/mdcontext-cli-capabilities.md` -- CLI commands, indexing, search, configuration
3. `~/.mdx/design/mdcontext-architecture.md` -- Data model, indexing pipeline, search algorithms
4. `~/.mdx/projects/mdcontext-linear-status.md` -- Linear project status, milestones, cross-project issues
