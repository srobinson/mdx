---
title: "Claude-Mem Search & Retrieval Analysis"
category: research
tags: [claude-mem, search, chroma, vector-search, fts5, mcp]
created: 2026-02-28
---

# Claude-Mem Search & Retrieval System

Deep analysis of claude-mem's search and retrieval architecture. Competitive intelligence for our own search systems (mdcontext, am).

## Architecture Overview

Claude-mem uses a **three-tier architecture** for search:

1. **MCP Server** (`src/servers/mcp-server.ts`) -- thin stdio MCP server exposing 7 tools
2. **Worker HTTP API** (`src/services/worker-service.ts`) -- Express server on `localhost:37777` with the actual business logic
3. **Search infrastructure** -- Strategy pattern with `SearchOrchestrator`, `ChromaSearchStrategy`, `SQLiteSearchStrategy`, `HybridSearchStrategy`

The MCP server is a thin client that proxies tool calls to the Worker HTTP API via `fetch()`. All search logic lives in the worker process. This separation means the MCP server never touches SQLite or Chroma directly.

## MCP Tools Exposed

Seven tools are exposed via the MCP server. The first is a pseudo-tool containing instructions:

### `__IMPORTANT` (Instructions pseudo-tool)

Not a real tool. Its description field contains the 3-layer workflow instructions that appear in the tool listing, forcing the LLM to read them:

```
3-LAYER WORKFLOW (ALWAYS FOLLOW):
1. search(query) -> Get index with IDs (~50-100 tokens/result)
2. timeline(anchor=ID) -> Get context around interesting results
3. get_observations([IDs]) -> Fetch full details ONLY for filtered IDs
NEVER fetch full details without filtering first. 10x token savings.
```

### `search` (Step 1)

- **Endpoint:** `GET /api/search`
- **Description:** "Step 1: Search memory. Returns index with IDs."
- **Input schema:** `additionalProperties: true` (accepts any params)
- **Parameters:** `query`, `limit`, `project`, `type` (observations|sessions|prompts), `obs_type`, `dateStart`, `dateEnd`, `offset`, `orderBy`
- **Returns:** Markdown table with IDs, timestamps, type icons, titles, token estimates (~50-100 tokens per result)

### `timeline` (Step 2)

- **Endpoint:** `GET /api/timeline`
- **Description:** "Step 2: Get context around results."
- **Parameters:** `anchor` (observation ID) OR `query` (auto-finds anchor), `depth_before`, `depth_after`, `project`
- **Returns:** Chronological timeline showing observations, sessions, and user prompts interleaved around the anchor point

### `get_observations` (Step 3)

- **Endpoint:** `POST /api/observations/batch`
- **Description:** "Step 3: Fetch full details for filtered IDs."
- **Input schema:** `{ ids: number[] }` (required)
- **Returns:** Complete observation objects with all fields (~500-1000 tokens each)

### `smart_search` (Code search)

- **Description:** Tree-sitter AST-based codebase search
- **Parameters:** `query`, `path`, `max_results`, `file_pattern`
- **Returns:** Folded structural views with token counts

### `smart_unfold` (Symbol expansion)

- **Description:** Expand a specific symbol from a file
- **Parameters:** `file_path`, `symbol_name`
- **Returns:** Full source code of the symbol

### `smart_outline` (File outline)

- **Description:** Structural outline of a file (bodies folded)
- **Parameters:** `file_path`
- **Returns:** Symbol signatures with bodies collapsed

## Progressive Disclosure (3-Layer Workflow)

The core design insight: **never fetch full details without filtering first.** This is enforced through tool design:

### Layer 1: Index (~50-100 tokens/result)

`search()` returns a compact markdown table:

```
| ID | Time | T | Title | Read |
|----|------|---|-------|------|
| #11131 | 3:48 PM | F | Added JWT authentication | ~75 |
| #10942 | 2:15 PM | B | Fixed auth token expiration | ~50 |
```

The "Read" column shows estimated tokens if you fetch the full observation. The "T" column shows type icons (emojis mapped by ModeManager).

### Layer 2: Context (timeline)

`timeline()` shows temporal context around interesting results. You can anchor by:

- Observation ID (number)
- Session ID (string, e.g., "S123")
- ISO timestamp (string)
- Query text (auto-finds best match via Chroma, uses it as anchor)

The timeline interleaves observations, session summaries, and user prompts in chronological order, grouped by day, then by file within each day.

### Layer 3: Full Details (~500-1000 tokens/result)

`get_observations(ids=[...])` batch-fetches only the IDs you selected. Returns complete observation objects with:

- title, subtitle, narrative, facts[], concepts[]
- files_read[], files_modified[]
- type, prompt_number, discovery_tokens

**Token savings math:** 20 search results at 75 tokens = 1,500 tokens. Fetching all 20 at 750 tokens = 15,000 tokens. The 3-layer pattern typically means you fetch 2-5 observations instead of 20, saving 10-15x tokens.

## Chroma Integration

### Architecture

Chroma is accessed via the **chroma-mcp** Python server, spawned as a subprocess via `uvx` (from the `uv` Python package manager). Communication happens over MCP stdio protocol.

- **ChromaMcpManager** (`src/services/sync/ChromaMcpManager.ts`) -- Singleton managing the persistent MCP connection to chroma-mcp
- **ChromaSync** (`src/services/sync/ChromaSync.ts`) -- Syncs observations, summaries, and user prompts to ChromaDB

### Embedding Model

Claude-mem does **NOT** manage embeddings directly. The chroma-mcp server handles its own embedding:

- Spawned via: `uvx --python 3.13 chroma-mcp --client-type persistent --data-dir ~/.claude-mem/chroma`
- chroma-mcp uses Chroma's default embedding function (likely `all-MiniLM-L6-v2` from sentence-transformers, the Chroma default)
- No ONNX/WASM dependencies needed in the Node.js process
- Data stored in `~/.claude-mem/chroma/`

### Collection Naming

- Collections named `cm__<sanitized_project>` (e.g., `cm__claude-mem`)
- All documents for all projects land in a single collection, scoped by metadata `project` field
- Collection name sanitization: `[^a-zA-Z0-9._-]` replaced with `_`, trailing non-alphanumeric stripped

### Document Granularity

**Key design choice:** Each semantic field becomes a separate Chroma document, not one document per observation.

For observations:

- `obs_{id}_narrative` -- The narrative field
- `obs_{id}_text` -- Legacy text field
- `obs_{id}_fact_{index}` -- Each individual fact

For session summaries:

- `summary_{id}_request` -- What was requested
- `summary_{id}_investigated` -- What was investigated
- `summary_{id}_learned` -- What was learned
- `summary_{id}_completed` -- What was completed
- `summary_{id}_next_steps` -- Next steps
- `summary_{id}_notes` -- Notes

For user prompts:

- `prompt_{id}` -- Single document per prompt

**Rationale:** Granular embedding means individual facts can match semantically even if the full observation narrative is about something different.

### Metadata Stored per Document

```typescript
{
  sqlite_id: number,
  doc_type: 'observation' | 'session_summary' | 'user_prompt',
  memory_session_id: string,
  project: string,
  created_at_epoch: number,
  type: string,        // observation type (e.g., 'decision', 'bugfix')
  title: string,       // observation title
  subtitle?: string,
  concepts?: string,   // comma-separated
  files_read?: string, // comma-separated
  files_modified?: string,
  field_type?: string, // which field this doc came from
  fact_index?: number  // for fact documents
}
```

### Deduplication During Query

Multiple Chroma documents map to the same SQLite ID. `ChromaSync.queryChroma()` deduplicates by sqlite_id, keeping the first (best-ranked) distance and metadata per SQLite ID:

```typescript
for (let i = 0; i < docIds.length; i++) {
  const obsMatch = docId.match(/obs_(\d+)_/);
  // ... extract sqlite_id ...
  if (sqliteId !== null && !seen.has(sqliteId)) {
    seen.add(sqliteId);
    ids.push(sqliteId);
  }
}
```

### Backfill Strategy

On worker startup, `ChromaSync.backfillAllProjects()` runs as fire-and-forget:

1. For each project with observations in SQLite
2. Fetch all existing Chroma document IDs (metadata-only, fast)
3. Compare with SQLite IDs
4. Only sync missing documents (smart backfill, not full rebuild)
5. Batch size: 100 documents per `chroma_add_documents` call

### Modes: Local vs Remote

- **Local mode** (default): `--client-type persistent --data-dir ~/.claude-mem/chroma`
- **Remote mode:** `--client-type http --host HOST --port PORT` with optional SSL, tenant, database, API key
- Configured via settings: `CLAUDE_MEM_CHROMA_MODE`, `CLAUDE_MEM_CHROMA_HOST`, etc.
- Can be disabled entirely: `CLAUDE_MEM_CHROMA_ENABLED=false`

## FTS5 Search (Deprecated)

### Current Status

FTS5 is **deprecated and no longer used for search**. The code explicitly states:

```typescript
// FTS5 tables are maintained for backward compatibility but not used for search.
// Vector search (Chroma) is now the primary search mechanism.
// TODO: Remove FTS5 infrastructure in future major version (v7.0.0)
```

When text search is attempted without Chroma, SessionSearch logs a warning and returns empty results:

```typescript
logger.warn("DB", "Text search not supported - use ChromaDB for vector search");
return [];
```

### FTS5 Configuration (Historical)

Two FTS5 virtual tables were created:

**observations_fts:**

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
  title,
  subtitle,
  narrative,
  text,
  facts,
  concepts,
  content='observations',
  content_rowid='id'
);
```

**session_summaries_fts:**

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS session_summaries_fts USING fts5(
  request,
  investigated,
  learned,
  completed,
  next_steps,
  notes,
  content='session_summaries',
  content_rowid='id'
);
```

Both used content-sync triggers (INSERT/DELETE/UPDATE) to keep the FTS tables synchronized with the source tables. FTS5 is unavailable on some platforms (e.g., Bun on Windows), so creation is guarded by a runtime probe.

## Hybrid Search Strategy

The search module uses a **Strategy pattern** with three strategies:

### Strategy Selection (SearchOrchestrator)

```
PATH 1: No query text -> SQLiteSearchStrategy (filter-only)
PATH 2: Query text + Chroma available -> ChromaSearchStrategy
PATH 3: Query text + no Chroma -> Empty results (error message)
```

### ChromaSearchStrategy

The primary search path:

1. **Query Chroma** for semantically similar documents (batch size 100)
2. **Filter by recency** (90-day window hardcoded: `90 * 24 * 60 * 60 * 1000` ms)
3. **Categorize by document type** (observation, session_summary, user_prompt) based on metadata `doc_type`
4. **Hydrate from SQLite** with additional filters (obs_type, concepts, files, project)

The 90-day recency filter is notable -- it means **old observations are never returned by semantic search**, even if highly relevant. This is a design choice favoring recency over completeness.

### HybridSearchStrategy

Used for metadata-first queries (findByConcept, findByFile, findByType):

1. **SQLite metadata filter** -- Get all IDs matching the structured criteria
2. **Chroma semantic ranking** -- Query Chroma with the concept/file/type as the query text
3. **Intersection** -- Keep only IDs that passed the metadata filter, in Chroma's rank order
4. **Hydrate from SQLite** in semantic rank order

This pattern is clever: SQLite does the precision filtering (exact match on concept tags, file paths), Chroma provides the relevance ordering. Neither alone could do both.

```typescript
private intersectWithRanking(metadataIds: number[], chromaIds: number[]): number[] {
  const metadataSet = new Set(metadataIds);
  const rankedIds: number[] = [];
  for (const chromaId of chromaIds) {
    if (metadataSet.has(chromaId) && !rankedIds.includes(chromaId)) {
      rankedIds.push(chromaId);
    }
  }
  return rankedIds;
}
```

### SQLiteSearchStrategy

Fallback for filter-only queries (no query text):

- Date range filtering via `created_at_epoch`
- Project filtering
- Type filtering (with array support)
- Concept filtering via `json_each()` on JSON arrays
- File filtering via `json_each()` with LIKE patterns

### Fallback Chain

If Chroma fails during a semantic search:

- Mark `usedChroma: false`
- Fall back to SQLite filter-only (strips the query text)
- Return results with `fellBack: true` flag

## HTTP API Endpoints

All search endpoints are registered in `SearchRoutes.ts`:

### Unified Endpoints (Primary API)

| Endpoint            | Method | Description                                        |
| ------------------- | ------ | -------------------------------------------------- |
| `/api/search`       | GET    | Unified search (observations + sessions + prompts) |
| `/api/timeline`     | GET    | Timeline around anchor or query                    |
| `/api/decisions`    | GET    | Semantic shortcut for decision-type observations   |
| `/api/changes`      | GET    | Semantic shortcut for change-related observations  |
| `/api/how-it-works` | GET    | Semantic shortcut for architecture explanations    |

### Backward Compatibility Endpoints

| Endpoint                   | Method | Description                   |
| -------------------------- | ------ | ----------------------------- |
| `/api/search/observations` | GET    | Search observations only      |
| `/api/search/sessions`     | GET    | Search session summaries only |
| `/api/search/prompts`      | GET    | Search user prompts only      |
| `/api/search/by-concept`   | GET    | Find by concept tag           |
| `/api/search/by-file`      | GET    | Find by file path             |
| `/api/search/by-type`      | GET    | Find by observation type      |

### Context Endpoints

| Endpoint                | Method | Description                                                    |
| ----------------------- | ------ | -------------------------------------------------------------- |
| `/api/context/recent`   | GET    | Recent session context (summaries + observations)              |
| `/api/context/timeline` | GET    | Timeline around anchor point                                   |
| `/api/context/preview`  | GET    | Context preview for settings modal                             |
| `/api/context/inject`   | GET    | Context injection for hooks (supports multi-project worktrees) |

### Batch Fetch

| Endpoint                  | Method | Description                          |
| ------------------------- | ------ | ------------------------------------ |
| `/api/observations/batch` | POST   | Batch fetch observations by ID array |

## Search Skill (Natural Language Interface)

`plugin/skills/mem-search/SKILL.md` provides the natural language interface. Key details:

### Trigger Phrases

- "Did we already fix this?"
- "How did we solve X last time?"
- "What happened last week?"

### Instruction Sections

The skill file has 4 sections extractable via `/api/instructions?topic=`:

- `workflow` -- The 3-layer workflow
- `search_params` -- Parameter reference
- `examples` -- Usage examples
- `all` -- Full content

### Token Budget Framing

The skill explicitly frames the token economics:

- Search index: ~50-100 tokens per result
- Full observation: ~500-1000 tokens each
- Batch fetch: 1 HTTP request vs N individual requests
- 10x token savings by filtering before fetching

## SDK Exports

`src/sdk/index.ts` exports:

- `parser.ts` -- XML parser for `<observation>` and `<summary>` blocks from Claude responses
- `prompts.ts` -- Prompt builders for init, observation, summary, and continuation prompts

### ParsedObservation Schema

```typescript
interface ParsedObservation {
  type: string; // decision | bugfix | feature | refactor | discovery | change
  title: string | null;
  subtitle: string | null;
  facts: string[];
  narrative: string | null;
  concepts: string[];
  files_read: string[];
  files_modified: string[];
}
```

### ParsedSummary Schema

```typescript
interface ParsedSummary {
  request: string | null;
  investigated: string | null;
  learned: string | null;
  completed: string | null;
  next_steps: string | null;
  notes: string | null;
}
```

## Data Flow: Observation to Searchable

1. Claude Code hook captures tool use events
2. SDK Agent processes events, Claude generates `<observation>` XML
3. Parser extracts structured observation from XML
4. **SQLite:** Observation stored in `observations` table (immediate)
5. **FTS5:** Triggers auto-populate `observations_fts` (if FTS5 available, deprecated)
6. **Chroma:** `ChromaSync.syncObservation()` creates granular documents (narrative, text, individual facts)
7. chroma-mcp embeds the documents using its built-in embedding model
8. Observation is now searchable via both vector (Chroma) and structured (SQLite) queries

## Key Design Decisions and Trade-offs

### Good Ideas (for our consideration)

1. **Progressive disclosure** -- The 3-layer pattern is genuinely effective for token savings. We should consider something similar for `am_query` results.

2. **Granular document embedding** -- Embedding individual facts separately means each fact can match independently. More precision than embedding the whole observation as one blob.

3. **Hybrid search pattern** -- Metadata filter (SQLite) for precision + vector search (Chroma) for relevance ordering. Neither alone does both well.

4. **Pseudo-tool for instructions** -- The `__IMPORTANT` tool with workflow instructions in its description is a clever hack to force LLMs to read the workflow before using tools.

5. **Project-scoped vector search** -- Including `project` in the Chroma where clause prevents larger projects from dominating top-N results.

### Limitations and Concerns

1. **90-day recency filter** -- Hardcoded, drops all older results from semantic search. No way to search historical data semantically. This is a significant limitation for long-running projects.

2. **FTS5 fully deprecated** -- Without Chroma, there's no text search at all (returns empty results). This creates a hard dependency on Python/uvx being installed.

3. **No score/distance exposure** -- Chroma distances are queried but never exposed to the user or used for re-ranking. The deduplication keeps the "first" (best) distance but throws it away.

4. **No cross-project search** -- Each query is scoped to a single project. No way to search across all projects at once (the `project` metadata filter is applied at the Chroma level).

5. **Embedding model opacity** -- Since chroma-mcp handles embedding, claude-mem has no control over or visibility into which model is used. No ability to upgrade or customize.

6. **Batch size hardcoded** -- Chroma query always fetches 100 results. For very large databases, this may miss relevant older results that fall outside the top 100.

7. **No re-ranking** -- Results go Chroma rank -> recency filter -> hydrate. No secondary ranking pass (e.g., cross-encoder re-ranking or BM25 fusion).

## Comparison with Our Systems

### vs attention-matters (am)

| Aspect        | claude-mem                              | am                                      |
| ------------- | --------------------------------------- | --------------------------------------- |
| Memory model  | Observations (structured XML)           | Episodes (exchange pairs)               |
| Embedding     | Chroma default (MiniLM?) via subprocess | None (quaternion geometry)              |
| Search        | Vector + metadata intersection          | Geometric compose scoring               |
| Recency       | Hard 90-day cutoff                      | Decay-weighted (continuous)             |
| Cross-project | No (project-scoped)                     | Yes (unified brain.db)                  |
| Token savings | Progressive disclosure (3-layer)        | Budget-aware composition (`max_tokens`) |
| Dependencies  | Python (uvx + chroma-mcp)               | Pure Rust (zero deps)                   |

### vs mdcontext

| Aspect       | claude-mem                    | mdcontext                   |
| ------------ | ----------------------------- | --------------------------- |
| Content type | Session observations          | Markdown documents          |
| Search       | Chroma vector + SQLite filter | BM25 + heading structure    |
| Embedding    | chroma-mcp default            | N/A (keyword search)        |
| Structure    | Flat (observations table)     | Hierarchical (heading tree) |

## Key Files Reference

| File                                                            | Purpose                                          |
| --------------------------------------------------------------- | ------------------------------------------------ |
| `src/servers/mcp-server.ts`                                     | MCP tool definitions, proxy to Worker API        |
| `src/services/worker-service.ts`                                | Worker process orchestrator                      |
| `src/services/worker/SearchManager.ts`                          | Search orchestration and tool handlers           |
| `src/services/worker/search/SearchOrchestrator.ts`              | Strategy selection and coordination              |
| `src/services/worker/search/strategies/ChromaSearchStrategy.ts` | Vector search via Chroma                         |
| `src/services/worker/search/strategies/HybridSearchStrategy.ts` | Metadata filter + semantic ranking               |
| `src/services/worker/search/strategies/SQLiteSearchStrategy.ts` | Filter-only SQLite queries                       |
| `src/services/sync/ChromaSync.ts`                               | Chroma sync (document creation, backfill, query) |
| `src/services/sync/ChromaMcpManager.ts`                         | MCP connection to chroma-mcp subprocess          |
| `src/services/sqlite/SessionSearch.ts`                          | SQLite filter queries, FTS5 setup (deprecated)   |
| `src/services/sqlite/types.ts`                                  | Database entity types and search interfaces      |
| `src/services/worker/FormattingService.ts`                      | Table formatting for search results              |
| `src/services/worker/TimelineService.ts`                        | Timeline building and filtering                  |
| `src/services/worker/http/routes/SearchRoutes.ts`               | HTTP route handlers for search API               |
| `src/sdk/parser.ts`                                             | XML parser for observation/summary blocks        |
| `src/sdk/prompts.ts`                                            | Prompt builders for SDK agent                    |
| `plugin/skills/mem-search/SKILL.md`                             | Natural language search skill definition         |
