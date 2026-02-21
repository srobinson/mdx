---
title: "Claude-Mem Core Architecture Analysis"
category: research
tags: [claude-mem, memory, sqlite, worker, observations]
created: 2026-02-28
---

# Claude-Mem Core Architecture Analysis

Deep technical analysis of the claude-mem memory system. This document covers the full data pipeline from tool use capture through AI-powered observation extraction to persistent storage and retrieval. Conducted as competitive intelligence for attention-matters (AM).

## 1. High-Level Architecture

Claude-mem is a **hook-driven, worker-process memory system** for Claude Code. It observes tool usage from a primary Claude Code session, sends those observations to a background worker process, which spawns a **secondary Claude instance** (the "memory agent") to analyze and compress them into structured observations.

```
Claude Code Session (primary)
    |
    | [Claude Code Hooks: SessionStart, UserPromptSubmit, PostToolUse, Stop]
    v
Hook Handlers (CLI process)
    |
    | [HTTP POST to worker on localhost:37777]
    v
Worker Service (Express daemon, long-running)
    |
    +-- SessionManager (in-memory session tracking)
    +-- PendingMessageStore (SQLite work queue)
    +-- SDKAgent / GeminiAgent / OpenRouterAgent
    |       |
    |       | [Spawns Claude subprocess via @anthropic-ai/claude-agent-sdk]
    |       v
    |   Memory Agent (secondary Claude instance)
    |       |
    |       | [Receives tool use XML, emits <observation> and <summary> XML]
    |       v
    +-- ResponseProcessor (parses XML, stores atomically)
    |       |
    |       +-- SQLite (primary storage)
    |       +-- ChromaDB via MCP (vector search)
    |       +-- SSE broadcast (web UI)
    |
    +-- Context Generator (reads SQLite, renders timeline)
    +-- Search Manager (FTS5 + Chroma hybrid search)
```

## 2. SQLite Schema

### 2.1 Core Tables (Final Schema After All Migrations)

The database uses **bun:sqlite** with WAL journal mode, 256MB mmap, 10K page cache.

#### `schema_versions`

Migration tracking table.

```sql
CREATE TABLE schema_versions (
  id INTEGER PRIMARY KEY,
  version INTEGER UNIQUE NOT NULL,
  applied_at TEXT NOT NULL
);
```

#### `sdk_sessions`

Central session table. Links a user's Claude Code session (`content_session_id`) to the memory agent's session (`memory_session_id`).

```sql
CREATE TABLE sdk_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content_session_id TEXT UNIQUE NOT NULL,   -- User's observed Claude Code session
  memory_session_id TEXT UNIQUE,             -- Memory agent's session ID for resume
  project TEXT NOT NULL,
  user_prompt TEXT,
  custom_title TEXT,                         -- Agent attribution label
  started_at TEXT NOT NULL,
  started_at_epoch INTEGER NOT NULL,
  completed_at TEXT,
  completed_at_epoch INTEGER,
  status TEXT CHECK(status IN ('active', 'completed', 'failed')) NOT NULL DEFAULT 'active',
  worker_port INTEGER,
  prompt_counter INTEGER DEFAULT 0
);
```

Indexes: `content_session_id`, `memory_session_id`, `project`, `status`, `started_at_epoch DESC`.

#### `observations`

AI-extracted structured observations from tool usage.

```sql
CREATE TABLE observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  memory_session_id TEXT NOT NULL,
  project TEXT NOT NULL,
  text TEXT,                    -- Deprecated, nullable
  type TEXT NOT NULL,           -- bugfix|feature|refactor|discovery|decision|change
  title TEXT,
  subtitle TEXT,
  facts TEXT,                   -- JSON array of fact strings
  narrative TEXT,               -- Full context paragraph
  concepts TEXT,                -- JSON array: how-it-works, why-it-exists, what-changed, etc.
  files_read TEXT,              -- JSON array of file paths
  files_modified TEXT,          -- JSON array of file paths
  prompt_number INTEGER,
  discovery_tokens INTEGER DEFAULT 0,  -- Token cost to produce this observation
  content_hash TEXT,            -- SHA-256 truncated to 16 hex chars for dedup
  created_at TEXT NOT NULL,
  created_at_epoch INTEGER NOT NULL,
  FOREIGN KEY(memory_session_id) REFERENCES sdk_sessions(memory_session_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);
```

Indexes: `memory_session_id`, `project`, `type`, `created_at_epoch DESC`, `content_hash + created_at_epoch`.

#### `session_summaries`

Structured session summaries (one or more per session).

```sql
CREATE TABLE session_summaries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  memory_session_id TEXT NOT NULL,        -- NOT UNIQUE (multiple summaries per session allowed)
  project TEXT NOT NULL,
  request TEXT,
  investigated TEXT,
  learned TEXT,
  completed TEXT,
  next_steps TEXT,
  files_read TEXT,             -- JSON array
  files_edited TEXT,           -- JSON array
  notes TEXT,
  prompt_number INTEGER,
  discovery_tokens INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  created_at_epoch INTEGER NOT NULL,
  FOREIGN KEY(memory_session_id) REFERENCES sdk_sessions(memory_session_id)
    ON DELETE CASCADE ON UPDATE CASCADE
);
```

#### `user_prompts`

User prompt tracking per session.

```sql
CREATE TABLE user_prompts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content_session_id TEXT NOT NULL,
  prompt_number INTEGER NOT NULL,
  prompt_text TEXT NOT NULL,
  created_at TEXT NOT NULL,
  created_at_epoch INTEGER NOT NULL,
  FOREIGN KEY(content_session_id) REFERENCES sdk_sessions(content_session_id) ON DELETE CASCADE
);
```

#### `pending_messages`

Persistent work queue for SDK messages (claim-confirm pattern).

```sql
CREATE TABLE pending_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_db_id INTEGER NOT NULL,
  content_session_id TEXT NOT NULL,
  message_type TEXT NOT NULL CHECK(message_type IN ('observation', 'summarize')),
  tool_name TEXT,
  tool_input TEXT,
  tool_response TEXT,
  cwd TEXT,
  last_user_message TEXT,
  last_assistant_message TEXT,
  prompt_number INTEGER,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'processed', 'failed')),
  retry_count INTEGER NOT NULL DEFAULT 0,
  created_at_epoch INTEGER NOT NULL,
  started_processing_at_epoch INTEGER,
  completed_at_epoch INTEGER,
  failed_at_epoch INTEGER,
  FOREIGN KEY (session_db_id) REFERENCES sdk_sessions(id) ON DELETE CASCADE
);
```

### 2.2 FTS5 Virtual Tables

Full-text search on observations and summaries (with sync triggers):

```sql
CREATE VIRTUAL TABLE observations_fts USING fts5(
  title, subtitle, narrative, text, facts, concepts,
  content='observations', content_rowid='id'
);

CREATE VIRTUAL TABLE session_summaries_fts USING fts5(
  request, investigated, learned, completed, next_steps, notes,
  content='session_summaries', content_rowid='id'
);

CREATE VIRTUAL TABLE user_prompts_fts USING fts5(
  prompt_text,
  content='user_prompts', content_rowid='id'
);
```

Each has INSERT/UPDATE/DELETE triggers to keep FTS in sync. FTS5 is optional -- falls back to ChromaDB if unavailable (e.g., Windows Bun builds).

### 2.3 Legacy Tables (Created But Dropped/Unused)

From earlier migration history:

- `sessions`, `memories`, `overviews`, `diagnostics`, `transcript_events` -- v1 schema, superseded by sdk_sessions/observations/session_summaries
- `streaming_sessions` -- v3, superseded by sdk_sessions
- `observation_queue` -- v4, superseded by Unix socket communication, then by pending_messages

### 2.4 Migration System

Two parallel migration systems:

1. **DatabaseManager migrations** (versions 1-7) -- old system using `schema_versions` table with sorted migration array
2. **MigrationRunner** (versions 4-23) -- new system extracted from SessionStore, column-existence-based idempotent migrations

The MigrationRunner checks actual column existence via `PRAGMA table_info()` before applying changes, making it resilient to any prior schema state.

## 3. Observation Pipeline (Data Flow)

### 3.1 Hook Capture

Claude Code fires hooks at specific lifecycle events:

| Hook Event         | Handler                  | What Happens                                                                                 |
| ------------------ | ------------------------ | -------------------------------------------------------------------------------------------- |
| `SessionStart`     | `contextHandler`         | Fetches context from worker (`GET /api/context/inject`), injects into Claude's system prompt |
| `UserPromptSubmit` | `sessionInitHandler`     | Creates/gets SDK session, saves user prompt, starts memory agent                             |
| `PostToolUse`      | `observationHandler`     | Sends tool name/input/output to worker (`POST /api/sessions/observations`)                   |
| `Stop`             | `sessionCompleteHandler` | Removes session from active map (`POST /api/sessions/complete`)                              |

The summarize handler is also called but triggered differently -- it sends `POST /api/sessions/summarize` with the last assistant message.

### 3.2 Worker Ingestion

When the worker receives an observation via HTTP:

1. **Privacy check**: Strips `<no-memory>` tags from prompts/tool data
2. **Tool filtering**: Skips configurable low-value tools (`CLAUDE_MEM_SKIP_TOOLS`)
3. **Session lookup**: `createSDKSession()` is idempotent (INSERT OR IGNORE)
4. **Queue**: `PendingMessageStore.enqueue()` persists to `pending_messages` table
5. **Generator start**: `ensureGeneratorRunning()` starts SDKAgent if not already running

### 3.3 Memory Agent Processing

The SDKAgent spawns a secondary Claude Code subprocess via `@anthropic-ai/claude-agent-sdk`:

```typescript
const queryResult = query({
  prompt: messageGenerator,   // async generator yielding messages
  options: {
    model: modelId,           // Configurable, defaults to Claude model
    cwd: OBSERVER_SESSIONS_DIR,  // Isolates observer sessions
    resume: shouldResume ? session.memorySessionId : undefined,
    disallowedTools: ['Bash', 'Read', 'Write', 'Edit', ...],  // OBSERVER ONLY
    abortController: session.abortController,
    env: isolatedEnv,  // Credentials from ~/.claude-mem/.env
  }
});
```

Key design: The memory agent has **ALL tools disabled** -- it can only observe and produce text output. It cannot read files, run commands, or interact with the codebase.

### 3.4 Prompt Construction

The memory agent receives structured prompts:

**Init prompt** (first message): System identity + observer role + recording focus + XML schema template
**Observation prompt** (per tool use):

```xml
<observed_from_primary_session>
  <what_happened>Edit</what_happened>
  <occurred_at>2026-02-28T10:00:00Z</occurred_at>
  <working_directory>/Users/dev/project</working_directory>
  <parameters>{"file_path": "src/foo.ts", "old_string": "...", "new_string": "..."}</parameters>
  <outcome>{"success": true}</outcome>
</observed_from_primary_session>
```

**Summary prompt** (end of session): Includes last assistant message, asks for structured XML summary.

### 3.5 XML Response Parsing

The memory agent responds with XML blocks that are parsed by `parseObservations()` and `parseSummary()`:

```xml
<observation>
  <type>bugfix</type>
  <title>Fix null pointer in auth middleware</title>
  <subtitle>Added guard clause for missing user object</subtitle>
  <facts>
    <fact>Auth middleware crashed when user object was null</fact>
    <fact>Added early return with 401 status</fact>
  </facts>
  <narrative>The auth middleware was crashing because...</narrative>
  <concepts>
    <concept>problem-solution</concept>
    <concept>gotcha</concept>
  </concepts>
  <files_read><file>src/middleware/auth.ts</file></files_read>
  <files_modified><file>src/middleware/auth.ts</file></files_modified>
</observation>

<summary>
  <request>Fix authentication bugs in middleware stack</request>
  <investigated>Auth middleware, session handler, JWT validation</investigated>
  <learned>Middleware chain needs null guards at every stage</learned>
  <completed>Fixed null pointer crash, added guard clauses</completed>
  <next_steps>Add integration tests for auth flow</next_steps>
  <notes>Consider refactoring to use Result type pattern</notes>
</summary>
```

The parser uses regex (`/<observation>([\s\S]*?)<\/observation>/g`) to extract blocks, then extracts individual fields. **NEVER skips observations** -- all are saved even with missing fields.

### 3.6 Atomic Storage

`processAgentResponse()` in `ResponseProcessor.ts` orchestrates:

1. Parse observations and summary from XML text
2. **Atomic transaction** via `storeObservations()`:
   - For each observation: compute content hash, check dedup window (30s), INSERT
   - Store summary if present
3. **Confirm processed**: Delete claimed messages from `pending_messages` queue
4. **Chroma sync** (fire-and-forget): Sync to vector DB
5. **SSE broadcast**: Notify web UI clients
6. **CLAUDE.md update**: Optionally update per-folder CLAUDE.md files

### 3.7 Deduplication

Content-hash deduplication prevents duplicate observations:

- Hash = SHA-256 of `(memory_session_id + title + narrative)`, truncated to 16 hex chars
- Dedup window: 30 seconds
- If identical hash exists within window, returns existing observation ID instead of inserting

## 4. Worker Service Architecture

### 4.1 Process Model

The worker runs as a **long-lived background daemon**:

- Spawned by hooks on first use (`spawnDaemon()`)
- PID file at `~/.claude-mem/worker.pid`
- Health check: `GET /api/health`
- Readiness check: `GET /api/readiness` (returns 503 until DB + search initialized)
- Version check with auto-restart on plugin update

### 4.2 Service Layer

```
WorkerService
  +-- DatabaseManager (owns SessionStore, SessionSearch, ChromaSync)
  +-- SessionManager (in-memory ActiveSession map, message iterators)
  +-- SSEBroadcaster (WebSocket-like push to web UI)
  +-- SDKAgent (Claude Agent SDK subprocess)
  +-- GeminiAgent (alternative provider)
  +-- OpenRouterAgent (alternative provider)
  +-- SearchManager (hybrid FTS5 + Chroma search)
  +-- Server (Express app with route handlers)
```

### 4.3 HTTP API Endpoints

#### Session Lifecycle

| Method | Path                         | Purpose                                      |
| ------ | ---------------------------- | -------------------------------------------- |
| POST   | `/api/sessions/init`         | Create/get session, save prompt, start agent |
| POST   | `/api/sessions/observations` | Queue tool observation                       |
| POST   | `/api/sessions/summarize`    | Queue summary request                        |
| POST   | `/api/sessions/complete`     | Remove from active map                       |

#### Search

| Method | Path                       | Purpose                                            |
| ------ | -------------------------- | -------------------------------------------------- |
| GET    | `/api/search`              | Unified search (observations + sessions + prompts) |
| GET    | `/api/search/observations` | FTS5/Chroma observation search                     |
| GET    | `/api/search/sessions`     | FTS5/Chroma session search                         |
| GET    | `/api/search/prompts`      | FTS5 prompt search                                 |
| GET    | `/api/search/by-concept`   | Filter by concept tag                              |
| GET    | `/api/search/by-file`      | Filter by file path                                |
| GET    | `/api/search/by-type`      | Filter by observation type                         |

#### Context

| Method | Path                    | Purpose                             |
| ------ | ----------------------- | ----------------------------------- |
| GET    | `/api/context/inject`   | Generate context for hook injection |
| GET    | `/api/context/recent`   | Recent summaries + observations     |
| GET    | `/api/context/timeline` | Timeline around anchor point        |
| GET    | `/api/context/preview`  | Settings preview with ANSI colors   |

#### Timeline

| Method | Path                     | Purpose                                  |
| ------ | ------------------------ | ---------------------------------------- |
| GET    | `/api/timeline`          | Unified timeline (anchor or query-based) |
| GET    | `/api/timeline/by-query` | Search + timeline around best match      |

#### Semantic Shortcuts

| Method | Path                | Purpose                   |
| ------ | ------------------- | ------------------------- |
| GET    | `/api/decisions`    | Decision observations     |
| GET    | `/api/changes`      | Change observations       |
| GET    | `/api/how-it-works` | How-it-works explanations |

#### System

| Method | Path                  | Purpose                                 |
| ------ | --------------------- | --------------------------------------- |
| GET    | `/api/health`         | Health check (always responds)          |
| GET    | `/api/readiness`      | Readiness check (503 until initialized) |
| GET    | `/api/version`        | Worker version                          |
| GET    | `/api/instructions`   | Load SKILL.md sections                  |
| POST   | `/api/admin/shutdown` | Graceful shutdown                       |
| POST   | `/api/admin/restart`  | Restart worker                          |

### 4.4 Session State Machine

```
Hook: UserPromptSubmit
  |
  v
createSDKSession() -> sdk_sessions row (status='active')
  |
  v
initializeSession() -> ActiveSession in memory
  |
  v
queueObservation() -> pending_messages row (status='pending')
  |
  v
ensureGeneratorRunning() -> startSession() -> Claude subprocess
  |
  v
claimNextMessage() -> pending_messages (status='processing')
  |
  v
Memory agent produces XML response
  |
  v
processAgentResponse() -> observations + session_summaries rows
  |
  v
confirmProcessed() -> DELETE from pending_messages
  |
  v
Hook: Stop
  |
  v
completeSession() -> remove from ActiveSession map
```

### 4.5 Error Recovery

The system has multiple self-healing mechanisms:

1. **Claim-confirm pattern**: Messages stay in DB until confirmed processed. If worker crashes, they're recovered on restart.
2. **Stale processing reset**: Messages in 'processing' state for >60s are reset to 'pending' by `claimNextMessage()`.
3. **Crash recovery**: After generator crash, `startGeneratorWithProvider()` restarts with exponential backoff (1s, 2s, 4s) up to 3 consecutive restarts.
4. **Stale session reaper**: Every 2 minutes, reaps sessions older than 6 hours with no activity.
5. **Orphan process reaper**: Every 5 minutes, kills zombie Claude subprocesses not associated with active sessions.
6. **Provider fallback**: On SDK resume failure, falls back to Gemini then OpenRouter.

## 5. Context Generation (Retrieval)

### 5.1 Context Injection Flow

When Claude Code starts a session, the `SessionStart` hook fetches context:

```
Hook: SessionStart
  -> GET /api/context/inject?projects=myproject
  -> ContextBuilder.generateContext()
     -> queryObservations() (SQLite, filtered by type + concept)
     -> querySummaries() (SQLite, recent N)
     -> buildTimeline() (merge + sort chronologically)
     -> renderTimeline() (markdown or ANSI-colored)
  -> Returns formatted text injected into Claude's system prompt
```

### 5.2 Context Configuration

Controlled via `ContextConfig`:

- `totalObservationCount`: How many observations to include
- `fullObservationCount`: How many get full narrative vs. title-only
- `sessionCount`: How many session summaries to include
- `observationTypes`: Filter set (bugfix, feature, refactor, discovery, decision, change)
- `observationConcepts`: Filter set (how-it-works, why-it-exists, what-changed, problem-solution, gotcha, pattern, trade-off)
- `fullObservationField`: Show 'narrative' or 'facts' for full observations
- `showLastSummary`, `showLastMessage`: Toggle sections

### 5.3 Token Economics

The system tracks **discovery tokens** (cost to produce an observation via the memory agent) vs. **read tokens** (cost to include in context). This measures ROI:

```
savings = discoveryTokens - readTokens
savingsPercent = (savings / discoveryTokens) * 100
```

Token estimation: `Math.ceil(charCount / 4)` (CHARS_PER_TOKEN_ESTIMATE = 4).

## 6. Search Architecture

### 6.1 Dual Search Strategy

Search uses a hybrid approach:

1. **SQLite FTS5**: Full-text search with BM25 ranking on observations, summaries, and prompts
2. **ChromaDB via MCP**: Semantic vector search using embeddings

FTS5 queries use content-synced virtual tables with triggers. ChromaDB is accessed via a child MCP process (`chroma-mcp` over stdio).

### 6.2 ChromaDB Sync

Each project gets a Chroma collection named `cm__<sanitized_project>`. Documents are synced fire-and-forget after each observation/summary store:

- `syncObservation()`: Embeds title + subtitle + narrative + facts
- `syncSummary()`: Embeds request + investigated + learned + completed + next_steps
- `syncUserPrompt()`: Embeds prompt text

Backfill on startup: `backfillAllProjects()` checks SQLite vs Chroma counts and syncs any missing documents.

### 6.3 Search Endpoints

The `SearchManager` provides unified search across:

- Observations (FTS5 + Chroma hybrid)
- Session summaries
- User prompts
- By concept, by file, by type (structured queries)
- Timeline around anchor point

## 7. Mode System

The observation extraction is configurable via a **mode system** (`ModeManager`):

```typescript
interface ModeConfig {
  name: string;
  description: string;
  observation_types: ObservationType[]; // {id, label, description, emoji}
  observation_concepts: ObservationConcept[]; // {id, label, description}
  prompts: ModePrompts; // All prompt templates, XML placeholders, headers
}
```

Modes control:

- Which observation types are valid
- Which concept categories to use
- All prompt text (system identity, observer role, recording focus, XML format examples)
- Language instructions (for localized modes)

Default mode: "code" with types `bugfix|feature|refactor|discovery|decision|change` and concepts `how-it-works|why-it-exists|what-changed|problem-solution|gotcha|pattern|trade-off`.

## 8. Multi-Provider Support

Three AI providers for the memory agent:

| Provider         | Agent             | How It Works                                                                 |
| ---------------- | ----------------- | ---------------------------------------------------------------------------- |
| Claude (default) | `SDKAgent`        | Spawns Claude Code subprocess via `@anthropic-ai/claude-agent-sdk` `query()` |
| Gemini           | `GeminiAgent`     | Direct API call to Gemini models                                             |
| OpenRouter       | `OpenRouterAgent` | API call via OpenRouter proxy                                                |

All providers share:

- `ResponseProcessor` for parsing and storage
- `conversationHistory` on `ActiveSession` for cross-provider context
- Same XML prompt format
- Same observation/summary parsing

Provider selection is via settings (`CLAUDE_MEM_PROVIDER`). Fallback chain: Claude -> Gemini -> OpenRouter.

## 9. Key Architectural Patterns

### 9.1 Dual Session ID Design

Two separate session IDs thread through the system:

- `content_session_id`: The user's Claude Code session being observed
- `memory_session_id`: The memory agent's own session (for resume)

**CRITICAL**: These must NEVER be equal. Using `content_session_id` for resume would inject memory messages into the user's transcript.

### 9.2 Claim-Confirm Queue Pattern

The `PendingMessageStore` implements a persistent work queue:

1. `enqueue()`: INSERT with status='pending'
2. `claimNextMessage()`: Atomically marks as 'processing' (with self-healing stale reset)
3. `confirmProcessed()`: DELETE after successful storage

This replaced the earlier observation_queue table and provides crash recovery.

### 9.3 Idempotent Session Creation

`createSDKSession()` uses INSERT OR IGNORE pattern:

- First call: Creates new row, returns ID
- Subsequent calls: Returns existing ID
- Never modifies `memory_session_id` (that's set by SDKAgent on first response)

### 9.4 Content-Hash Deduplication

Observations are deduplicated within a 30-second window using SHA-256 hashes of `(memory_session_id + title + narrative)`, preventing duplicate storage from crash recovery reprocessing.

### 9.5 Fire-and-Forget Chroma Sync

Chroma sync is always async and non-blocking. Failures are logged but never prevent observation storage. This keeps the critical path (SQLite storage) fast and reliable.

## 10. Comparison with Attention-Matters (AM)

| Aspect               | Claude-Mem                                   | Attention-Matters                              |
| -------------------- | -------------------------------------------- | ---------------------------------------------- |
| **Storage**          | SQLite + ChromaDB                            | SQLite (am-store)                              |
| **Memory model**     | Flat observations + summaries                | Geometric neighborhoods on hypersphere         |
| **Recall**           | FTS5 text search + Chroma embeddings         | DAE cosine similarity + SLERP interpolation    |
| **Compression**      | AI-extracted structured XML                  | Epoch-based Jaccard overlap penalty            |
| **Contradiction**    | None (append-only)                           | Epoch-based supersession with Jaccard grouping |
| **Association**      | Concept tags + file paths                    | Golden-angle phasors + Kuramoto coupling       |
| **Context budget**   | Fixed observation count + token estimation   | Token-budget-aware composition                 |
| **AI processing**    | Spawns Claude subprocess per session         | None (pure math, O(1) lookups)                 |
| **Cost model**       | High (secondary Claude instance per session) | Zero marginal cost (no AI for recall)          |
| **Deduplication**    | Content hash within 30s window               | Structural (neighborhood geometry)             |
| **Hook integration** | Claude Code hooks only                       | MCP server (any client)                        |

### 10.1 Key Differences

**Claude-mem's strengths**:

- Rich structured extraction (title, subtitle, narrative, facts, concepts, files)
- FTS5 + vector search hybrid for retrieval
- Mode system for customizable observation schemas
- Multi-provider fallback (Claude, Gemini, OpenRouter)
- Web UI with SSE real-time updates
- Token economics tracking (ROI of memory)

**AM's advantages**:

- Zero marginal cost for recall (no AI subprocess needed)
- Geometric contradiction handling (epoch-based supersession)
- Mathematical associations (not just keyword matching)
- Client-agnostic (MCP server, not hook-dependent)
- Compositional context budgeting (fits best context into N tokens)
- No XML parsing fragility

### 10.2 Architecture Lessons for AM

1. **Persistent work queue**: Claude-mem's claim-confirm pattern with self-healing stale recovery is robust. AM should consider similar durability for ingest operations.

2. **Content-hash deduplication**: Simple and effective. AM's Jaccard overlap approach is more sophisticated but the time-windowed hash is a good belt-and-suspenders defense.

3. **Structured observation schema**: The type/title/subtitle/narrative/facts/concepts/files structure is well-designed for retrieval. AM neighborhoods could benefit from similar structured metadata.

4. **Discovery tokens tracking**: Measuring the cost to produce vs. cost to consume context is valuable for demonstrating ROI. AM should track this.

5. **FTS5 integration**: Having full-text search as a fallback when vector search is unavailable is pragmatic. AM currently relies purely on geometric similarity.

6. **Worker process isolation**: Running the memory agent as a separate daemon process with health checks, PID files, and graceful shutdown is production-grade infrastructure.

## 11. File Map

| Path                                               | Purpose                                         |
| -------------------------------------------------- | ----------------------------------------------- |
| `src/services/sqlite/Database.ts`                  | Database initialization, bun:sqlite config      |
| `src/services/sqlite/migrations.ts`                | Schema migrations 1-7 (old system)              |
| `src/services/sqlite/migrations/runner.ts`         | Schema migrations 4-23 (new system)             |
| `src/services/sqlite/SessionStore.ts`              | Legacy CRUD operations (deprecated, still used) |
| `src/services/sqlite/observations/store.ts`        | Observation storage with content-hash dedup     |
| `src/services/sqlite/observations/get.ts`          | Observation retrieval by ID, session            |
| `src/services/sqlite/observations/recent.ts`       | Recent observation queries                      |
| `src/services/sqlite/observations/files.ts`        | File aggregation per session                    |
| `src/services/sqlite/sessions/create.ts`           | Idempotent session creation                     |
| `src/services/sqlite/sessions/get.ts`              | Session retrieval queries                       |
| `src/services/sqlite/summaries/store.ts`           | Summary storage                                 |
| `src/services/sqlite/summaries/get.ts`             | Summary retrieval                               |
| `src/services/sqlite/summaries/recent.ts`          | Recent summary queries                          |
| `src/services/sqlite/PendingMessageStore.ts`       | Persistent work queue (claim-confirm)           |
| `src/services/sqlite/transactions.ts`              | Atomic observation+summary+completion           |
| `src/services/sqlite/types.ts`                     | All database row/input types                    |
| `src/services/worker-service.ts`                   | Worker daemon orchestrator                      |
| `src/services/worker-types.ts`                     | ActiveSession, PendingMessage types             |
| `src/services/worker/SDKAgent.ts`                  | Claude Agent SDK integration                    |
| `src/services/worker/GeminiAgent.ts`               | Gemini API integration                          |
| `src/services/worker/OpenRouterAgent.ts`           | OpenRouter API integration                      |
| `src/services/worker/agents/ResponseProcessor.ts`  | Shared response parsing + storage               |
| `src/services/worker/SessionManager.ts`            | In-memory session state management              |
| `src/services/worker/DatabaseManager.ts`           | Database service coordinator                    |
| `src/services/worker/SearchManager.ts`             | Hybrid FTS5 + Chroma search                     |
| `src/services/worker/http/routes/SessionRoutes.ts` | Session lifecycle HTTP API                      |
| `src/services/worker/http/routes/SearchRoutes.ts`  | Search HTTP API                                 |
| `src/services/worker/http/routes/DataRoutes.ts`    | Data/stats HTTP API                             |
| `src/services/server/Server.ts`                    | Express app setup + core routes                 |
| `src/services/context/ContextBuilder.ts`           | Context generation orchestrator                 |
| `src/services/context/ObservationCompiler.ts`      | Data queries for context                        |
| `src/services/context/TokenCalculator.ts`          | Token economics calculation                     |
| `src/services/sync/ChromaSync.ts`                  | ChromaDB synchronization                        |
| `src/services/sync/ChromaMcpManager.ts`            | MCP client for chroma-mcp                       |
| `src/sdk/prompts.ts`                               | Prompt templates for memory agent               |
| `src/sdk/parser.ts`                                | XML observation/summary parser                  |
| `src/cli/handlers/observation.ts`                  | PostToolUse hook handler                        |
| `src/cli/handlers/session-init.ts`                 | UserPromptSubmit hook handler                   |
| `src/cli/handlers/session-complete.ts`             | Stop hook handler                               |
| `src/cli/handlers/context.ts`                      | SessionStart hook handler                       |
| `src/constants/observation-metadata.ts`            | Default observation types/concepts              |
| `src/services/domain/types.ts`                     | ModeConfig interface                            |
