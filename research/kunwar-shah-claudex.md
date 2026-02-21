---
title: kunwar-shah/claudex — Claude Code conversation viewer with FTS5 + universal JSONL parser, transferable in pieces to history-matters
type: research
tags: [history-matters, claude-code, jsonl, sqlite, fts5, conversation-viewer, mcp, parser, session-storage]
summary: Claudex is a single-author full-stack web app that scans ~/.claude/projects, parses Claude Code JSONL with a versioned waterfall detector, indexes content into SQLite FTS5, and exposes browse/search via Fastify+React plus an MCP server. The data-model and FTS5 indexing pieces transfer cleanly to history-matters; most of the React UI and the bolted-on "structured memory" MCP feature should be skipped.
status: active
source: github-researcher
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

IMPORTANT

# kunwar-shah/claudex

## Snapshot

- **Repo**: https://github.com/kunwar-shah/claudex
- **Stars**: 85 (2026-04-27)
- **Created**: 2025-10-03 (~7 months old)
- **Latest version**: v1.3.0 (2026-02-12), MCP server release
- **Author**: Kunwar Jhamat (`Kunwar Shah`). 54/55 commits. One drive-by contributor.
- **License**: MIT
- **Primary language**: JavaScript (ESM, Node 18+)
- **Disk**: 7.0 MB. ~16K LOC including client.
- **CI**: none. `.github/` contains only `FUNDING.yml`. Single Jest test file (`server/src/utils/titleExtractor.test.js`, 107 LOC).
- **Headline grade**: **B−**.

## What it does and how

Claudex is a full-stack desktop-style web app for browsing and searching Claude Code conversation transcripts stored in `~/.claude/projects/<sanitized-cwd>/<sessionId>.jsonl`. Three surfaces over the same SQLite store:

1. **Fastify backend** (`server/src/server.js`, 100 LOC) exposes `/api/projects`, `/api/projects/:id/sessions`, `/api/projects/:id/sessions/:sid`, `/api/search`, `/api/search/index/{build,status,clear}`, `/api/export/...`.
2. **React+Vite frontend** consumes those endpoints. ProjectSelector → SessionList → ConversationThread, plus a SearchPage with FTS5 results and snippet highlighting.
3. **MCP server** (`bin/claudex-mcp.js` → `server/src/mcp/index.js`, 132 LOC) exposes 10 tools and 3 prompts (`/recall`, `/catchup`, `/history`) over the same DB so Claude Code can search its own past sessions during a live session.

The pipeline is straightforward: `FileScanner` walks the projects directory, `SessionParser` streams JSONL line-by-line through a `TemplateDetector` waterfall and a per-version `MessageParser`, `SearchIndexer` batches the results into a SQLite FTS5 virtual table, and `SearchDatabase.search` does BM25 ranking with `snippet()` highlighting. The MCP server reuses the same `SearchDatabase`, `FileScanner`, `SessionParser`, and a custom `MemoryService` for "structured memory" CRUD (a separate feature from session search, see "What does NOT transfer").

Key files (server, by load-bearing-ness):

```
server/src/
├── services/fileScanner.js          114 LOC  — projects/sessions discovery, title extraction
├── services/sessionParser.js        222 LOC  — line-by-line JSONL stream, validation, parse, token aggregation
├── services/searchDatabase.js       340 LOC  — FTS5 schema, batch insert, BM25 search, escape helper
├── services/searchIndexer.js        227 LOC  — full rebuild with progress callback, transactional bulk insert
├── services/sessionMetadataService.js 392 LOC — custom titles, tags, hide/delete/favorite (sidecar table)
├── services/memoryService.js        227 LOC  — structured memory CRUD (separate concern)
├── parsers/templateDetector.js       80 LOC  — V3-first waterfall detection
├── parsers/templateSchemas.js       238 LOC  — Zod schemas per template version
├── parsers/messageParser.js         863 LOC  ← BREACHES 700-LOC RULE
├── routes/{search,projects,export,sessionMetadata}.js  197+278+313+437 LOC
├── mcp/{index,tools,prompts,resources}.js  132+605+78+86 LOC  ← tools.js BREACHES 700-LOC RULE
└── utils/{titleExtractor,pathHelper}.js  119+44 LOC
```

## Session storage and data model

This is the load-bearing question for history-matters. Claudex does not store conversation content; it indexes content that already exists on disk under Anthropic's directory layout.

### What lives on disk (read-only, not owned by claudex)

- **Root**: `~/.claude/projects/` (configurable via `PROJECT_ROOT` env or `--project-root` flag, with `~` expansion in `server/src/utils/pathHelper.js:9-28`).
- **Per-project**: a directory per Claude Code working directory. The directory name is the absolute CWD with `/` replaced by `-` (e.g. `/home/boss/claude-chats` → `-home-boss-claude-chats`). `bin/claudex-mcp.js` exploits this in reverse: `process.cwd().replace(/\//g, '-')` derives the project ID for current-project default in `server/src/mcp/index.js:32-37`.
- **Per-session**: one `<sessionId>.jsonl` file per session. Session ID is the file basename with `.jsonl` stripped (`fileScanner.js:46`).
- **Per-message**: one JSON object per non-empty line. Schema varies by Claude Code version.

Claudex never writes to these files. `SessionMetadataService` documents this explicitly: "SAFETY: This service NEVER modifies Claude Code JSONL files. All custom data is stored in separate session_metadata table. 100% reversible — delete table to restore original behavior." (`server/src/services/sessionMetadataService.js:5-9`). This is the right doctrine for history-matters: read the upstream files, write a sidecar.

### What claudex owns (sidecar SQLite)

A single SQLite file at `server/data/search.db`, with WAL mode enabled and a 5-second busy timeout for concurrent reads from the MCP process (`searchDatabase.js:27-31`, `mcp/index.js:57`). Three tables:

1. **`messages_fts`** — FTS5 virtual table with eleven columns: `project_id, project_name, session_id, session_title, message_id, role, content, timestamp, file_path, line_number, template` (`searchDatabase.js:43-58`). Note: every column is indexed by FTS5, so a plain MATCH covers metadata too. There are no foreign-key constraints (FTS5 virtual tables can't have them), no separate sessions table, no projects table. Sessions and projects are derived on every read by re-scanning the filesystem (`fileScanner.scanProjects`/`scanSessions`).

2. **`session_metadata`** — composite-PK table on `(session_id, project_id)` carrying user-curated state: `custom_title, original_title, is_hidden, is_deleted, is_favorited, tags (JSON string), notes, created_at, updated_at` (`searchDatabase.js:74-90`). Tags are stored as JSON-encoded text; index on `tags` exists but does substring scan only.

3. **`project_memories`** — separate "structured memory" table with `(project_id, namespace, memory_type, key)` UNIQUE, `value JSON, metadata JSON, priority 1-10, confidence 0-1, ttl_hours, expires_at` (`memoryService.js:23-58`). This is the v1.3 MCP feature; it is unrelated to session search.

### Schema migration approach

Inline `ALTER TABLE ... ADD COLUMN` wrapped in `try/catch` for "duplicate column name" (`searchDatabase.js:92-111`). No migration framework, no version table. Two migrations live in source: `is_deleted` and `is_favorited` columns on `session_metadata`. Honest but won't scale past 5-10 migrations.

### Parsing the JSONL

The parsing layer is the most thoughtful part of the codebase and the part history-matters most needs.

**Template detector waterfall** (`templateDetector.js:11-54`). V3 is intentionally the superset and runs first. It matches a message if any of: `role` field present without `type` (Claude Code 2.0+), `type === 'file-history-snapshot'`, summary-only-with-leafUuid, V1-style `(uuid + sessionId + type + timestamp)`, or unknown roles. The legacy V2-mixed entry is dead code (`detect: () => false`, line 6) — V3 absorbed it. The V1 detector remains as a documented fallback.

**Zod schemas** (`templateSchemas.js`). One schema per detected version plus a `V3UniversalMessageSchema` that is `z.union([V1, V2New, FileSnapshot, V2MixedSummary, passthrough fallback])` (`templateSchemas.js:91-104`). The passthrough fallback is the right default when the upstream format keeps drifting. `safeParse` tries V3, then V1, then V2New (`templateSchemas.js:176-217`).

**Stream parsing** (`sessionParser.js:18-112`). Reads JSONL with `readline.createInterface({ crlfDelay: Infinity })` over a `fs.createReadStream`. Per line: `JSON.parse` → `validateMessage` (logs warnings on schema breaks but does not skip) → `messageParser.parseMessage` → push with `lineNumber`. Validation stats are returned alongside the parsed messages, which is a nice debugging affordance for "did Claude Code change their format?" detection.

**Message normalization** (`messageParser.js`, 863 LOC). Each template gets its own parser method that produces a uniform shape:

```js
{
  id, role, content, contentKind,            // contentKind ∈ {text, markdown, diff, json}
  timestamp,
  toolsUsed: [{ id, name, details, type }],
  actions: ['Used tool: Edit', ...],
  metadata: { sessionId, cwd, version, parentUuid, requestId, gitBranch, ... },
  raw: <original message>                    // preserved for re-processing
}
```

The breakdown into text/tool_use/thinking blocks (`parseClaudeAssistantMessage`, `messageParser.js:284-338`) correctly handles Anthropic's content-blocks shape and is reusable. The 863 LOC is mostly switch-cased per template and per content-block type. Helioy's 700-LOC rule says split this by template into separate files.

### Title extraction

`utils/titleExtractor.js` (119 LOC, has tests). Strips IDE noise tags (`<ide_opened_file>`, `<system-reminder>`, `<environment_details>`, etc.) before truncating to 80 chars. The tag list at `titleExtractor.js:26` is empirically curated and is the kind of thing history-matters would otherwise rediscover painfully. Worth lifting verbatim.

### Token usage aggregation

`sessionParser.js:143-183` walks parsed messages, sums `usage.{input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens, cache_creation.ephemeral_5m_input_tokens, ephemeral_1h_input_tokens}`, computes a `cacheHitRate`. Output joins the response object as `stats.tokens`. This is small, well-isolated, and worth taking.

## Browse and search UX

### Discovery surfaces

- **Web UI** at http://localhost:3000 (dev) or :3400 (prod-served-from-server). Full SPA: ProjectSelector dropdown → SessionList → ConversationThread.
- **REST API** documented in README.
- **MCP tools** for in-session retrieval from Claude Code itself.
- **No CLI search** beyond starting the server. `claudex` runs the web app; there is no `claudex search "query"` subcommand. `bin/claude-viewer.js:223-251` only handles `--help`, `--version`, `--port`, `--project-root`, and the `mcp` subcommand.
- **No TUI**.

### Query model

- **Engine**: SQLite FTS5 with porter-stemmer-disabled default tokenizer. BM25 ranking (`searchDatabase.js:166`). The `bm25()` score is negative; Claudex flips it with `Math.abs` for display (`searchDatabase.js:226`).
- **Snippets**: `snippet(messages_fts, 6, '<mark>', '</mark>', '...', 64)` then `<mark>...</mark>` is rewritten to markdown bold for client rendering (`searchDatabase.js:161, 224`). Column 6 is `content`, 64 is the max snippet length.
- **Filters in API**: `projectId`, `role`, `from`, `to` (date range, applied with `datetime(timestamp) >= datetime(?)` so SQLite parses ISO strings), `limit`, `offset` (`searchDatabase.js:149-198`).
- **FTS5 escape**: terms matching `^[A-Z_][A-Z0-9_-]*$` get wrapped in double quotes to avoid being misread as column names like `FROM` or `SELECT` (`searchDatabase.js:316-329`). This is a real FTS5 footgun and the fix is correct.

### Index lifecycle

- **Build is manual.** `POST /api/search/index/build` triggers a full rebuild that clears the index, walks all sessions, parses each one, and bulk-inserts in 500-message batches inside one transaction (`searchIndexer.js:19-152`). Reported "121x faster async search index rebuild" in v1.1.0 changelog comes from this batched-transactional path.
- **Progress callback** is wired through to a server-side state object polled by the UI (`routes/search.js:80-130`). Rebuild is async (server returns 202 immediately, status endpoint reports progress).
- **Per-session incremental update** exists (`searchIndexer.js:166-211`) but is not wired to a file watcher. There is no chokidar, no inotify, no `WebSocket live updates` (the README explicitly lists this as TODO). The index goes stale until the user clicks Rebuild.
- **No update detection.** No mtime comparison on rebuild. It always does a full clear + re-walk.

### Performance characteristics

- WAL mode + 10MB cache + memory-mapped I/O + temp-store-memory pragmas (`searchDatabase.js:27-31`).
- BATCH_SIZE = 500 messages per insert (`searchIndexer.js:36`).
- One transaction wraps the entire rebuild (`searchIndexer.js:28, 127`). Rollback on error.
- Project-list endpoint re-parses every session for token stats with a 5-minute in-memory cache (`routes/projects.js:6-28, 222-269`). This is the performance hot spot in the codebase: `/api/projects/:id/token-stats` parses every JSONL on every cache-cold request.

## Engineering signals

- **Code quality**: mid-tier. The parser layer is thoughtful (Zod schemas, V3 superset, validation stats reported back). The route and component layers are journeyman. The frontend has obvious slop: `TremorProjectView-old.jsx` (881 LOC) sits next to `TremorProjectView.jsx` (899 LOC). `SettingsModal.jsx` is 1307 LOC. `messageParser.js` is 863 LOC.
- **Tests**: one test file (`utils/titleExtractor.test.js`). No integration tests for the parser, no FTS5 tests, no MCP tests. `npm test` is wired but only runs that one file. The README brags about `test-search.sh` which is a curl script, not a test. `test-parser.js` in `server/` is a smoke script, not a unit test.
- **Helioy 700-LOC rule violations**: 4 files. `messageParser.js` (863), `client/SettingsModal.jsx` (1307), `client/TremorProjectView.jsx` (899) and its `-old` shadow (881). Plus `mcp/tools.js` at 605 is approaching the limit and contains 10 tool definitions stuffed into one file.
- **Error handling**: `try/catch` per route with `reply.code(500)` and a forwarded `error.message`. Validation failures produce `console.warn` instead of skipping or failing. Session-parse errors during indexing are swallowed and logged (`searchIndexer.js:109-112`). Reasonable for a viewer; not robust enough for an automated pipeline.
- **Deps**: server has 9 runtime deps, all known: `fastify`, `@fastify/cors`, `@fastify/static`, `sqlite3`, `zod`, `dotenv`, `date-fns`, `ndjson`, `@modelcontextprotocol/sdk`. No bespoke parsers, no exotic libs.
- **Dev process**: `.clauderc` (lines 1-15) explicitly bans Claude co-author lines on commits. Single primary author, 54/55 commits. No CI. No PR template. Releases are tagged but not signed.
- **Security smells**: low. SQL is parameterized everywhere. The express read-only Docker mount of `~/.claude/projects` is the right default. JSON content from JSONL is not eval'd. The `extractMetadata` fallback in `messageParser.js:229-238` does an `Object.keys` walk that whitelists known fields, not blacklists, which is the safer direction.

## What transfers to history-matters

Concrete primitives worth lifting, ranked by load-bearing-ness:

1. **The directory-name reverse trick.** Claude Code stores projects as `~/.claude/projects/<cwd-with-slashes-replaced-by-dashes>`. Claudex inverts this on the MCP side to auto-default to the current project: `process.cwd().replace(/\//g, '-')` at `server/src/mcp/index.js:32-37`. history-matters' MCP layer needs this exact transform to default to "the project I'm in." Two lines, copy verbatim. **High value.**

2. **Sidecar SQLite + FTS5 schema with BM25 + snippet highlighting.** `searchDatabase.js:43-58` is a 15-line FTS5 virtual table declaration that gives full-text search across content and metadata in one query. The BM25 ordering and `snippet()` call (lines 161, 195, 226) cover the entire UX of "show me where this matched." history-matters should adopt this verbatim. WAL + busy-timeout dual-process pattern (`searchDatabase.js:27-31`, `mcp/index.js:57`) lets the MCP server and a separate web/TUI process share one DB safely. **High value.**

3. **JSONL stream parser with validation-stats-as-output.** `sessionParser.js:18-112` reads with `readline.createInterface({ crlfDelay: Infinity })`, validates each line against Zod, and returns validation stats alongside parsed messages. The "log-but-don't-fail" stance on schema drift (`sessionParser.js:62-67`) plus the `passthrough` fallback in `templateSchemas.js:91-104` means Claude Code template changes degrade rather than break. history-matters needs this exact resilience because Anthropic ships JSONL format changes without warning. **High value.**

4. **V3 superset + Zod union schemas.** `templateDetector.js:11-54` and `templateSchemas.js:91-104`. One detector tries the universal schema first, falls back to per-version. New templates get added as union members. Cleaner than a switch-on-version. Take this pattern, but rename "claude-code-v3" because in 6 months there will be a v4. **High value.**

5. **Title extraction with curated tag-stripping.** `utils/titleExtractor.js:26` lists exactly the IDE-noise tags that need to be stripped before showing a session title to a human. This list was earned through user complaints (commit `2cfb205`, "Strip XML tags from session titles"). Lift the file as-is including its test. **Medium-high value.**

6. **Token usage aggregator.** `sessionParser.js:143-183`. Small, isolated, knows the exact `usage.cache_creation.ephemeral_{5m,1h}_input_tokens` field paths Anthropic ships. **Medium value.**

7. **Sidecar metadata table for tags/hidden/favorited/notes.** `sessionMetadataService.js` plus the `session_metadata` table. The "100% reversible, never write to JSONL" doctrine (`sessionMetadataService.js:5-9`) is correct. The schema is reasonable. The composite-PK on `(session_id, project_id)` is the right grain. **Medium value.**

8. **Batched-transactional rebuild with progress callback.** `searchIndexer.js:19-152`. 500-row batch INSERT inside one transaction is the difference between minutes and hours on a large `~/.claude/projects`. Progress callback lets a TUI show meaningful progress. **Medium value.**

9. **MCP server pattern: redirect console.log to stderr.** `bin/claudex-mcp.js → server/src/mcp/index.js:5-6` redirects `console.log` to `console.error` because services internally use `console.log` and that would corrupt the JSON-RPC stdout. Tiny but load-bearing for any MCP server that wraps existing libraries. **Medium value.**

10. **Lazy services with shared SQLite.** `mcp/index.js:42-71` initializes `searchDb`, `metadataService`, `memoryService`, `fileScanner`, `sessionParser` once on first tool call and shares the DB connection. WAL + busy_timeout means the same DB file works for the MCP server and a separate web/TUI process. **Medium value.**

## What does NOT transfer

1. **The structured memory MCP feature (`MemoryService`, `project_memories` table, `store_memory`/`recall_memory`/`list_memories`/`delete_memory` tools).** This is a v1.3 add-on that competes with the Helioy `cm` (context-matters) primitive. Helioy already has a structured context store, and it is materially better than this `(namespace, memory_type, key) UNIQUE` shape. Skip. history-matters is a session browser, not a memory store.

2. **The 10 MCP tools and 3 prompts as a whole.** The MCP-tool framing is "give Claude Code persistent memory across sessions" (README:151-157). That is the cm + am job in Helioy. history-matters' MCP layer should expose two tools: search and get-session. `tools.js` has 605 LOC encoding ten of them, most of which are either over-specific (`get_session_summary` vs `get_session`) or duplicate cm. **Skip the bundle**; lift only `search_conversations` and `get_session` semantics.

3. **The React+Vite web UI.** 6 client subdirs, ~6K LOC, includes `SettingsModal.jsx` at 1307 lines and a `TremorProjectView-old.jsx` shadow file. history-matters' first surface should be a TUI or a minimal Tauri/Electron view; building a Tremor-charts dashboard with 10 themes and 29 fonts is yak-shaving for a session browser. The screenshots in `screenshots/v1.2.0/` (theme selector, font preview) are not the goal of history-matters.

4. **The system-checker (`scripts/check-system.mjs`).** Cute CLI flag-parser around port-availability and dep-presence checks. Helioy already has a different installer story; this script does not transfer.

5. **`.clauderc` ban on co-author lines.** Single-author repo posture. Helioy commits are the user's own choice; not a portable pattern.

6. **The "auto-fix" install path.** `npm run check:fix` invokes `npm install` in two subdirs and writes a `.env`. Not how Helioy components are installed.

7. **The export feature (JSON/HTML/TXT).** `server/src/routes/export.js` (313 LOC) plus `services/projectExporter.js` (168 LOC). Three output formats. history-matters does not need export; the underlying JSONL is already on disk and can be `cat`'d. If exporting is ever needed, write 30 lines, not 480.

8. **The dual-package monorepo structure** with separate `server/` and `client/` workspaces. Adds ceremony without payoff for a single deployable. Pick one tree.

9. **The `is_deleted` soft-delete column on `session_metadata`.** Sessions don't get deleted; the JSONL on disk is the truth. A "hide" flag is enough. Soft-delete invites "where did my session go?" support requests with no actual benefit.

## Grade

**B−.**

Calibrated:
- DeepDiagram (C): demo-quality, not a packaging exemplar.
- **claudex (B−)**: thoughtful parser layer, sound FTS5 schema, useful sidecar pattern. Loses ground on tests (one file), file-size discipline (four 700+ files), 1307-LOC SettingsModal and a `-old.jsx` shadow file in the tree, MCP feature creep into structured-memory, and zero CI. The parser/schema/FTS5 trio is genuinely good; the rest is journeyman.
- graphify (B): packaging-driven velocity, similar quality of substance.
- superpowers (B+): version-stamp tooling and per-platform care.
- notebooklm-py (A−): the actual installer pattern Helioy should study.

Claudex's contribution to history-matters is concentrated in three modules: `templateDetector.js + templateSchemas.js`, `sessionParser.js + messageParser.js (after splitting)`, and `searchDatabase.js + searchIndexer.js`. Those nine modules total roughly 2200 LOC and answer 80% of the data-model and indexing questions for history-matters. Everything else in the repo is either over-built (the React UI, the Tremor charts, the theme system) or off-mission (the structured memory feature).

## Sources consulted

- `README.md`
- `package.json`, `server/package.json`, `client/package.json`
- `bin/claude-viewer.js`, `bin/claudex-mcp.js`
- `server/src/server.js`
- `server/src/services/{fileScanner,sessionParser,searchDatabase,searchIndexer,memoryService,sessionMetadataService}.js`
- `server/src/parsers/{templateDetector,templateSchemas,messageParser}.js`
- `server/src/routes/{search,projects,export,sessionMetadata}.js`
- `server/src/utils/{pathHelper,titleExtractor,titleExtractor.test}.js`
- `server/src/mcp/{index,tools,prompts,resources}.js`
- `client/src/components/SearchPage.jsx` (header)
- `.clauderc`, `install.sh`, `Dockerfile`, `.github/`
- `git log --oneline` and `git shortlog`

## Open questions

- How does claudex handle Claude Code's per-session resume/branch model when the same session UUID gets multiple JSONL chunks? The detector treats one file = one session, which may miss this case.
- Does the MCP server's WAL+busy_timeout actually hold up under simultaneous web-UI rebuilds and MCP queries on a 10K-message DB? Not load-tested in this repo.
- The `passthrough` fallback in `V3UniversalMessageSchema` accepts any object as a "message" — does it leak garbage into FTS5 when an unrelated JSONL file ends up in `~/.claude/projects/`?
- The MCP server hard-codes the DB path to `server/data/search.db` relative to the package install (`mcp/index.js:50-51`). What happens when the user has installed claudex globally via npm and the server's `data/` directory is in `node_modules` and gets blown away on update? Likely re-indexes silently. Not a problem history-matters should inherit.
