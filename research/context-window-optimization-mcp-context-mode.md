---
title: "Context Mode: MCP-Layer Context Window Optimization for AI Coding Agents"
type: research
tags: [competitive-analysis, context-management, mcp, context-window, fts5, bm25, session-continuity, agent-tooling]
summary: "Deep analysis of mksglu/context-mode, a 5.8k-star MCP server that reduces context window consumption by 98% through sandboxed execution, FTS5 indexing, and session event tracking across 10+ AI coding platforms."
status: active
source: github-researcher
confidence: high
created: 2026-03-24
updated: 2026-03-24
---

## Executive Summary

Context Mode (`mksglu/context-mode`) is a TypeScript MCP server that solves a specific, well-defined problem: raw tool output flooding the context window of AI coding agents. It intercepts tool calls (Bash, Read, WebFetch), routes their output through sandboxed subprocesses, indexes results into an ephemeral FTS5/BM25 knowledge base, and returns only compact summaries to the LLM's context. A separate session tracking system captures structured events from every tool call, persists them in SQLite, and rebuilds a priority-tiered XML snapshot when the conversation compacts, giving the model continuity across compaction boundaries.

Created 2026-02-23, 50 commits in one month, 5,793 stars, 371 forks. Elastic License v2. Sole author (Mert Koseoolu). Supports Claude Code, Gemini CLI, VS Code Copilot, Cursor, OpenCode, Codex CLI, Kiro, Zed, and several others via a multi-platform adapter layer.

This project is solving context window management at the tool output layer, not at the knowledge/memory layer. It is complementary to what context-matters does, not competitive.

## Architecture

### Language and Stack

- TypeScript (strict), Node.js 18+ target
- `better-sqlite3` for Node, `bun:sqlite` adapter for Bun runtime
- `@modelcontextprotocol/sdk` for MCP server registration
- `turndown` + `domino` for HTML-to-markdown conversion (web fetching)
- `zod` for input schema validation
- `esbuild` for bundling (server, CLI, and session hooks as separate bundles)
- `vitest` for testing (125+ tests across adapters, core, hooks, session)

### Module Layout

```
src/
  server.ts          MCP server entrypoint, 6 tools registered
  store.ts           ContentStore: FTS5 knowledge base, BM25 search, RRF fusion
  executor.ts        PolyglotExecutor: sandboxed subprocess runner (11 languages)
  runtime.ts         Runtime detection (Bun/Node/Python/Ruby/Go/Rust/etc.)
  security.ts        Deny-list firewall, shell-escape scanner, file path enforcement
  lifecycle.ts       Orphan process detection (ppid monitoring)
  truncate.ts        Smart truncation (head 60% + tail 40%), XML escaping
  exit-classify.ts   Non-zero exit code classification (soft vs hard failure)
  db-base.ts         SQLite base class, WAL pragma setup, Bun adapter
  session/
    db.ts            SessionDB: per-project SQLite for session events
    extract.ts       Event extraction from tool calls (13 categories)
    snapshot.ts      XML snapshot builder with priority-tiered budget allocation
  adapters/
    types.ts         HookAdapter interface (platform-agnostic contract)
    detect.ts        Platform auto-detection
    claude-code/     Claude Code adapter
    gemini-cli/      Gemini CLI adapter
    cursor/          Cursor adapter
    vscode-copilot/  VS Code Copilot adapter
    opencode/        OpenCode adapter
    ... (9 adapters total)
hooks/               Platform-specific hook scripts (mjs, pre-bundled)
skills/              Slash command definitions (ctx-doctor, ctx-stats, ctx-upgrade)
configs/             Per-platform configuration templates
```

### Data Model

Two separate SQLite databases per project:

**ContentStore** (ephemeral, per-project, path-hashed):
- `sources` table: label, chunk counts, indexed_at
- `chunks` FTS5 virtual table: title, content, source_id, content_type (porter tokenizer)
- `chunks_trigram` FTS5 virtual table: same schema, trigram tokenizer
- `vocabulary` table: extracted terms for fuzzy correction

**SessionDB** (ephemeral, per-project):
- `session_events`: id, session_id, type, category, priority (1-4), data, source_hook, data_hash
- `session_meta`: session_id, project_dir, started_at, last_event_at, event_count, compact_count
- `session_resume`: session_id, snapshot (XML), event_count, consumed flag

Both use WAL mode with NORMAL synchronous. Stale DBs are cleaned up on startup (content DBs > 14 days, session DBs > 7 days). PID-based temp DBs from older versions are also cleaned.

## Core Concepts

### The Problem It Solves

AI coding agents consume context window through tool output. A Playwright snapshot is 56KB. Twenty GitHub issues are 59KB. After 30 minutes of intensive tool use, 40%+ of the context window is consumed by raw tool output that the model read once and no longer needs. When the conversation compacts, the model loses track of which files it was editing, what errors it encountered, and what the user asked for.

### Mental Model

Context Mode operates at two layers:

1. **Context Saving**: Tool output stays in a subprocess. Only the model's printed summary enters context. Large outputs are indexed into FTS5 and queried on demand. The raw data never touches the context window.

2. **Session Continuity**: Every tool call generates structured events (file operations, errors, git commands, tasks, decisions). These events persist in SQLite. When the conversation compacts, a priority-budgeted XML snapshot is injected to restore the model's awareness of session state.

The key insight: context optimization should happen at the tool output layer (before data enters the window), not at the conversation layer (after it is already consumed).

## Key Features

### 6 MCP Tools

1. **ctx_execute**: Run code in sandboxed subprocess (11 languages). Optional `intent` parameter triggers auto-indexing + BM25 search when output exceeds 5KB.
2. **ctx_execute_file**: Read a file into `FILE_CONTENT` variable inside sandbox, process with user code. File content never enters context.
3. **ctx_batch_execute**: Run multiple commands, auto-index all output, search across results. Primary tool for research workflows.
4. **ctx_search**: Query the FTS5 knowledge base. Requires prior indexing. Progressive throttling (3 calls per minute before result reduction, 8 before blocking).
5. **ctx_index**: Manually index documentation/content into the knowledge base.
6. **ctx_fetch_and_index**: Fetch a URL, convert HTML to markdown, index into knowledge base.

### Hook System

Four lifecycle hooks per platform:
- **SessionStart**: Inject routing instructions, clean up stale DBs, restore session continuity
- **PreToolUse**: Intercept tool calls, enforce routing (redirect large outputs to context-mode tools)
- **PostToolUse**: Extract session events from completed tool calls
- **PreCompact**: Build and inject resume snapshot before conversation compaction

### Session Event Extraction

13 event categories extracted from tool calls:
- P1 (Critical): file operations, task state, rules (CLAUDE.md reads)
- P2 (Important): cwd changes, errors, decisions, environment, git operations
- P3 (Context): subagents, skills, MCP tool usage
- P4 (Low): intent classification, large data references

Events are deduplicated (SHA256 hash, 5-event window), FIFO-evicted at 1000 events per session, and stored with structured metadata.

### Resume Snapshot

When compaction occurs, the snapshot builder:
1. Groups all events by category
2. Renders category-specific XML sections (active_files, task_state, rules, environment, errors, etc.)
3. Assembles by priority tier with a 2048-byte budget (P1: 50%, P2: 35%, P3-P4: 15%)
4. Progressively drops lowest-priority tiers if over budget

Result: a compact XML blob that tells the model what files it was editing, what tasks are pending, what errors it hit, and what the user decided, all within 2KB.

### Multi-Layer Search

The ContentStore implements a 3-layer search cascade:

1. **Porter + BM25** (Layer 1): Standard FTS5 with porter stemming, BM25 ranking with 5:1 title-to-content weight
2. **Trigram + BM25** (Layer 2): FTS5 with trigram tokenizer for substring matching
3. **Fuzzy Correction** (Layer 3): Levenshtein distance against extracted vocabulary, re-runs RRF with corrected query
4. **RRF Fusion**: Reciprocal Rank Fusion (K=60) merges Porter and Trigram results
5. **Proximity Reranking**: Minimum span algorithm boosts results where query terms appear close together

### Security Layer

- Server-side deny firewall: reads Claude Code permission policies (allow/deny/ask) and blocks denied commands
- Shell-escape scanner: detects `execSync`, `subprocess.run`, `system()`, etc. in non-shell code
- Sandboxed environment: strips 50+ dangerous environment variables (BASH_ENV, NODE_OPTIONS, LD_PRELOAD, etc.)
- File path enforcement: checks against Read deny patterns
- Chained command splitting: prevents bypass via `echo ok && sudo rm -rf /`

### Polyglot Execution

Supports 11 languages: JavaScript, TypeScript, Python, Shell, Ruby, Go, Rust (compile + run), PHP, Perl, R, Elixir. Detects available runtimes at startup. Each language gets appropriate wrappers (Go main package, PHP opening tag, Elixir BEAM path prepending).

## Data Flow

### Context Saving Flow

```
User asks question
  -> Model calls ctx_execute(language, code, intent)
  -> Code runs in isolated subprocess
  -> stdout captured, stderr captured
  -> If intent provided AND output > 5KB:
       -> Index output into FTS5 (plain text chunking)
       -> Search against intent query
       -> Return section titles + previews (not full content)
  -> Else:
       -> Return stdout directly (within 100KB soft cap)
  -> Model uses summary, calls ctx_search() for details
```

### Session Continuity Flow

```
PostToolUse hook fires after each tool call
  -> extractEvents() parses tool name/input/output
  -> 0-N SessionEvents produced (typed, categorized, prioritized)
  -> insertEvent() deduplicates + FIFO-evicts + stores in SessionDB

PreCompact hook fires before conversation compaction
  -> getEvents() retrieves all events for session
  -> buildResumeSnapshot() renders priority-tiered XML
  -> upsertResume() persists snapshot
  -> Snapshot injected into compacted context

SessionStart hook fires on new/resumed session
  -> Checks for unconsumed resume snapshot
  -> If found: injects into context, marks consumed
  -> Cleans stale content DBs if not --continue
```

### Indexing Flow

```
Content arrives (tool output, file, URL)
  -> Markdown: chunk by headings (code blocks kept intact, max 4KB per chunk)
  -> Plain text: chunk by line groups (20 lines per chunk with overlap)
  -> JSON: walk object tree, use key paths as titles
  -> Each chunk stored in both Porter FTS5 and Trigram FTS5
  -> Vocabulary extracted for fuzzy correction
  -> Dedup: same-label sources are atomically replaced (delete + insert in transaction)
```

## Unique Ideas / Novel Approaches

### Intent-Driven Search (Strongest Innovation)

The `intent` parameter on execute tools is the most interesting design choice. Instead of either dumping raw output OR blindly summarizing, the model declares what it is looking for ("failing tests", "HTTP 500 errors"), and context-mode indexes the output then searches against that intent. This gives the model a two-phase interaction with tool output: first a targeted preview, then on-demand retrieval via `ctx_search()`.

This is a form of lazy evaluation for context. The data exists indexed in SQLite, but only the relevant portions ever enter the context window.

### Priority-Budgeted Session Snapshots

The snapshot builder's approach of allocating a fixed byte budget (2KB) across priority tiers (50/35/15 split) is a practical compression strategy. Rather than trying to summarize everything, it categorizes events by importance and drops lowest-priority tiers when the budget is tight. File operations and task state survive; MCP tool usage counts do not.

### Dual FTS5 Index Architecture

Running both Porter-stemmed and trigram tokenizers in parallel, then fusing with RRF, gives better recall than either alone. Porter handles morphological variations ("configure" matches "configuration"), trigram handles substring matches and typos. The RRF constant K=60 is the standard from Cormack et al. 2009.

### Hook-Based Routing Enforcement

Rather than relying on the model to voluntarily use context-mode tools, the hook system intercepts tool calls and redirects them. PreToolUse hooks detect when Bash/Read/WebFetch would produce large output and inject context that nudges the model toward context-mode tools instead. This is soft enforcement via system instructions rather than hard blocking.

### Progressive Search Throttling

After 3 search calls in 60 seconds, results per query drop to 1. After 8 calls, search is blocked entirely with a message demanding batch queries. This prevents the common failure mode where the model calls search() in a tight loop instead of batching queries.

### No Geometric or Mathematical Context Models

Context Mode has no geometric approaches, no embedding-based retrieval, no vector search, no decay functions, no scope hierarchies. Everything is keyword-based (BM25 + trigram + fuzzy). There is no semantic understanding of context relationships. Events are flat (type + category + priority + data), with no graph or tree structure connecting them.

## Strengths

1. **Solves a real, measurable problem.** The benchmarks are credible: 315KB raw output becoming 5.5KB in context is genuinely useful. The before/after comparison is concrete.

2. **Multi-platform adapter architecture.** Supporting 10+ platforms through a clean adapter interface (HookAdapter with capabilities, input parsing, response formatting) is well-engineered. Each platform gets its own adapter without contaminating the core.

3. **Security implementation is thorough.** The 50+ denied environment variables, the shell-escape scanner for 7 languages, the chained command splitting to prevent bypass, the file path deny enforcement all reflect careful security thinking.

4. **Privacy-first design.** Everything local. SQLite in temp dirs. No telemetry. No cloud. DBs cleaned up on process exit. This is a strong differentiator vs. cloud-based context management.

5. **Session continuity is practical.** The event extraction covering 13 categories, the dedup/eviction strategy, and the budget-trimmed snapshot builder handle the compaction problem without requiring the model to do anything special.

6. **Test coverage is good.** 125+ tests across adapters, core server, hooks, session pipeline, security. Benchmark suite with real-world fixtures.

7. **Rapid iteration.** 50 commits, 52 releases in one month. Active maintenance, responsive to issues.

## Weaknesses / Gaps

1. **No semantic understanding of context.** BM25 is keyword-based. If the model asks "what was the authentication problem?" and the indexed content discusses "OAuth token expiration", the search may miss it. No embeddings, no semantic similarity.

2. **Ephemeral by design.** Content and session databases are tied to a single project directory and deleted aggressively (14 days for content, 7 days for sessions, immediately on fresh session without --continue). There is no persistent knowledge accumulation across projects or over time.

3. **No scope hierarchy.** Events are flat. There is no concept of nested scopes (global > project > session), no inheritance of context, no way to say "this decision applies to all sessions in this project." Everything is session-scoped.

4. **No multi-agent awareness.** Subagent events are tracked (launch/complete), but there is no shared context between agents. Each agent session has its own isolated SessionDB. No coordination, no shared knowledge base.

5. **Session snapshot is XML, not structured data.** The resume snapshot is a rendered XML string. It cannot be queried, filtered, or updated incrementally. If the model needs to know "which files was I editing?", it must parse the XML from the injected context.

6. **No context decay or relevance scoring.** All events at the same priority level are treated equally regardless of recency. A file_read from 500 events ago has the same priority as one from 5 events ago. The FIFO eviction removes the oldest lowest-priority event, but surviving events are not time-weighted.

7. **Fragile routing enforcement.** The hook system injects text instructions ("DO NOT use Bash for commands producing >20 lines") into the system prompt. This relies on the model obeying instructions, which is unreliable. There is no hard interception that prevents the model from using Bash directly.

8. **Single-author project.** 50 commits, all from one person, in one month. Elastic License v2 (not truly open source). High velocity but high bus factor.

9. **No compression or summarization of stored data.** Chunks are stored verbatim. There is no LLM-based summarization, no compression of historical events, no distillation of session knowledge over time.

10. **Content indexing is session-scoped.** When a new session starts without --continue, the content database is wiped. Documentation indexed in a previous session must be re-indexed. There is no persistent documentation knowledge base.

## Relevance to Helioy / context-matters

### Different Problem Spaces

Context Mode and context-matters solve fundamentally different problems:

- **Context Mode**: Reduces context window consumption at the tool output layer. "How do I fit more tool output into limited context?" Ephemeral, session-scoped, keyword-based.
- **context-matters**: Persistent structured knowledge store with hierarchical scopes, typed entries, and cross-session recall. "How do I remember things across conversations and projects?"

They are complementary, not competitive.

### Ideas Worth Noting

1. **Intent-driven retrieval pattern.** The `intent` parameter on execute tools is worth studying. Rather than always returning full results or always summarizing, letting the caller declare their search intent and returning targeted results is a good UX pattern. context-matters could adopt this for `cx_recall` -- let agents specify what they are looking for, not just free-text search.

2. **Priority-budgeted snapshots.** The P1/P2/P3 budget allocation with progressive tier dropping is a practical approach to fitting context into a byte budget. attention-matters could use a similar strategy when deciding what to include in recall results.

3. **Event extraction from tool calls.** The 13-category event extraction from PostToolUse hooks is a useful taxonomy of "things worth remembering" during a coding session. context-matters could auto-capture similar signals rather than requiring explicit `cx_store` calls.

4. **Deduplication via content hashing.** The SHA256-based dedup with a sliding window is a simple, effective pattern that context-matters should adopt (or already has) for preventing duplicate entries.

5. **BM25 + Trigram + Fuzzy cascade.** The multi-layer search with RRF fusion is a solid approach for keyword search without embeddings. If context-matters ever adds full-text search as a complement to structured queries, this is the right architecture.

6. **Session continuity across compaction.** The problem of "model forgets state after compaction" is real and painful. Context Mode's approach of injecting a structured snapshot is one solution. Helioy's approach of external structured storage (cx_recall) that the model can query at any time is arguably better because it does not depend on a hook firing at exactly the right moment.

### What Context Mode Lacks That Helioy Has

- **Hierarchical scope model** (global > project > repo > session). Context Mode is flat.
- **Typed entries** (fact, decision, preference, lesson, feedback). Context Mode events are typed but not semantically classified.
- **Geometric memory** (attention-matters). Context Mode has zero mathematical sophistication in its retrieval.
- **Cross-session persistence**. Context Mode is ephemeral by design.
- **Multi-agent coordination** (helioy-bus). Context Mode tracks subagents but does not share context between them.
- **Semantic search/embeddings**. Context Mode is purely keyword-based.

### What Context Mode Has That Helioy Should Consider

- **Tool output sandboxing.** Keeping raw tool output out of the context window is valuable and orthogonal to context-matters. This could be implemented as a separate Helioy component.
- **Automatic event capture from hooks.** Rather than requiring the agent to explicitly call `cx_store`, automatically extracting events from tool calls reduces the friction of context capture.
- **Progressive search throttling.** Preventing search-in-a-loop is a good defensive pattern that context-matters tools could adopt.

## Sources Consulted

- `src/server.ts` (1000+ lines): Full MCP tool registration, intent search, smart snippet extraction
- `src/store.ts` (950+ lines): ContentStore, FTS5 schema, BM25/trigram/fuzzy search, RRF, proximity reranking
- `src/executor.ts` (484 lines): PolyglotExecutor, sandboxed subprocess management, 11 language support
- `src/runtime.ts` (293 lines): Runtime detection, command building
- `src/security.ts` (557 lines): Deny firewall, shell-escape scanner, file path enforcement
- `src/session/db.ts` (461 lines): SessionDB, event storage, dedup, FIFO eviction, resume management
- `src/session/extract.ts` (648 lines): 13-category event extraction from tool calls and user messages
- `src/session/snapshot.ts` (404 lines): Priority-tiered XML snapshot builder
- `src/truncate.ts` (177 lines): Smart truncation, XML escaping, byte-safe capping
- `src/db-base.ts` (262 lines): SQLite base class, WAL setup, Bun adapter
- `src/lifecycle.ts` (79 lines): Parent process death detection
- `src/exit-classify.ts` (34 lines): Exit code classification
- `src/adapters/types.ts` (318 lines): HookAdapter interface, platform capabilities
- `CLAUDE.md`: Tool selection rules and routing instructions
- `BENCHMARK.md`: Quantitative benchmark results (376KB -> 16.5KB, 96% savings)
- `package.json`: Dependencies, build scripts, version 1.0.52
- `llms.txt`: Architecture overview for LLM consumption

## Open Questions

1. How does performance degrade with large FTS5 indices? The benchmarks show small datasets (< 400KB). What happens with 10MB+ of indexed content?
2. Does the routing enforcement actually work in practice? The hook-based instruction injection depends on model compliance.
3. What is the false positive rate on the session event extraction? Some of the regex patterns (decision detection, role detection) seem prone to false triggers.
4. How does this interact with other context-saving tools (Context7, Playwright MCP) that also try to manage output size?
