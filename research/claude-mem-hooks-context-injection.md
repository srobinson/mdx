---
title: "Claude-Mem Hooks & Context Injection Analysis"
category: research
tags: [claude-mem, hooks, context-injection, lifecycle, privacy]
created: 2026-02-28
---

# Claude-Mem Hooks & Context Injection — Complete Technical Analysis

Competitive intelligence gathered from claude-mem v10.5.2 (AGPL-3.0, by Alex Newman / @thedotmack). This documents the full hook lifecycle, context injection format, privacy system, exit code strategy, and observation capture pipeline.

## 1. Architecture Overview

Claude-mem is a Claude Code plugin that provides persistent memory across sessions. The architecture has three layers:

1. **Hook scripts** — Thin CLI handlers invoked by Claude Code at lifecycle events. Written in TypeScript, compiled to CJS/ESM bundles in `plugin/scripts/`. Executed via `node bun-runner.js` which finds and invokes Bun.
2. **Worker service** — Express HTTP server on port 37777 (configurable). Runs as a daemon process. Handles all database operations, AI-powered observation compression (via Claude Agent SDK), and context generation.
3. **SQLite database** — At `~/.claude-mem/claude-mem.db`. Stores sessions, observations, summaries, user prompts, pending message queue.

**Key insight**: Hooks never access the database directly. Every hook makes HTTP calls to the worker service. This is a clean separation — hooks are stateless edge processors, the worker owns all state.

## 2. Hook Registration — `plugin/hooks/hooks.json`

The hook configuration file registers commands for each Claude Code lifecycle event. All hooks use the same invocation pattern:

```
node "$PLUGIN_ROOT/scripts/bun-runner.js" "$PLUGIN_ROOT/scripts/worker-service.cjs" hook claude-code <event-name>
```

The `_R` variable resolves `CLAUDE_PLUGIN_ROOT` with a fallback to the marketplace install path.

### Registered Hooks

```json
{
  "Setup": [{ "command": "setup.sh", "timeout": 300 }],
  "SessionStart": [
    { "command": "smart-install.js", "timeout": 300 },
    { "command": "worker-service.cjs start", "timeout": 60 },
    { "command": "worker-service.cjs hook claude-code context", "timeout": 60 }
  ],
  "UserPromptSubmit": [
    {
      "command": "worker-service.cjs hook claude-code session-init",
      "timeout": 60
    }
  ],
  "PostToolUse": [
    {
      "matcher": "*",
      "command": "worker-service.cjs hook claude-code observation",
      "timeout": 120
    }
  ],
  "Stop": [
    {
      "command": "worker-service.cjs hook claude-code summarize",
      "timeout": 120
    },
    {
      "command": "worker-service.cjs hook claude-code session-complete",
      "timeout": 30
    }
  ]
}
```

**SessionStart** has the `matcher: "startup|clear|compact"` — it fires on session start, context clear, and compaction.

**PostToolUse** has `matcher: "*"` — it fires for every tool use.

**Stop** runs two sequential commands: first summarize, then session-complete.

There is no explicit **SessionEnd** hook registered. The Stop hook serves both summarize and session-complete purposes.

## 3. The Seven Event Handlers

Source: `src/cli/handlers/`. The handler index maps event strings to handler objects:

| Event Name         | Hook Event              | Handler                  | Purpose                                    |
| ------------------ | ----------------------- | ------------------------ | ------------------------------------------ |
| `context`          | SessionStart            | `contextHandler`         | Inject memory context into session         |
| `session-init`     | UserPromptSubmit        | `sessionInitHandler`     | Initialize/resume session, start SDK agent |
| `observation`      | PostToolUse             | `observationHandler`     | Capture tool usage for compression         |
| `summarize`        | Stop                    | `summarizeHandler`       | Generate session summary                   |
| `session-complete` | Stop                    | `sessionCompleteHandler` | Remove session from active map             |
| `user-message`     | SessionStart (parallel) | `userMessageHandler`     | Display context to user via stderr         |
| `file-edit`        | Cursor afterFileEdit    | `fileEditHandler`        | Cursor-specific file edit capture          |

Unknown event types return a no-op handler (exit 0, suppress output) instead of throwing — prevents breakage when Claude Code adds new events.

## 4. Hook Execution Pipeline

### 4.1 Entry Point — `hookCommand()` in `src/cli/hook-command.ts`

Every hook invocation follows this flow:

```
1. Suppress stderr (Claude Code shows stderr as error UI)
2. Get platform adapter (claude-code, cursor, or raw)
3. Read JSON from stdin (self-delimiting parser, not EOF-dependent)
4. Normalize input through adapter
5. Get event handler
6. Execute handler
7. Format output through adapter
8. console.log(JSON.stringify(output))
9. process.exit(exitCode)
```

**Stderr suppression** is critical: `process.stderr.write = (() => true)`. Claude Code interprets stderr differently based on exit code. All diagnostics go to log files via the logger.

### 4.2 stdin Reading — `src/cli/stdin-reader.ts`

Problem: Claude Code doesn't close stdin after writing hook input, so `stdin.on('end')` never fires.

Solution: JSON is self-delimiting. The reader attempts `JSON.parse()` after each data chunk. Once valid JSON is detected, it resolves immediately without waiting for EOF.

Key details:

- 30-second safety timeout for malformed input
- 50ms parse delay between chunks for multi-chunk delivery
- Returns `undefined` (not error) if stdin is unavailable (Bun EINVAL bug)
- Returns `undefined` for TTY (interactive) stdin

### 4.3 Platform Adapters — `src/cli/adapters/`

Three adapters normalize different input formats:

**claude-code adapter** (`claude-code.ts`):

```typescript
normalizeInput(raw) {
  return {
    sessionId: r.session_id ?? r.id ?? r.sessionId,
    cwd: r.cwd ?? process.cwd(),
    prompt: r.prompt,
    toolName: r.tool_name,
    toolInput: r.tool_input,
    toolResponse: r.tool_response,
    transcriptPath: r.transcript_path,
  };
}
```

Output formatting has a critical distinction:

- If `hookSpecificOutput` is present, return `{ hookSpecificOutput, systemMessage? }` — used by SessionStart context injection
- Otherwise, return `{ continue: true, suppressOutput: true }` — standard response

**cursor adapter** maps different field names: `conversation_id`, `workspace_roots[0]`, `result_json` (not `tool_response`), shell commands as `command`/`output` mapped to Bash tool.

## 5. Lifecycle Flow — Session Start to Session End

### Phase 1: Session Start

**Hook 1: smart-install.js** (timeout: 300s)

- Checks if Bun and uv (Python package manager for Chroma) are installed
- Auto-installs missing dependencies
- All output to stderr via `console.error` (not captured by Claude Code)

**Hook 2: worker-service.cjs start** (timeout: 60s)

- Checks worker health via `GET /api/health`
- If not healthy, spawns worker daemon
- Worker listens on port 37777 (configurable via `CLAUDE_MEM_WORKER_PORT`)
- Version mismatch detection between plugin and running worker

**Hook 3: context handler** (timeout: 60s)

- Calls `ensureWorkerRunning()` — quick health check, returns false if unavailable
- Gets project context with worktree detection (parent + worktree combined)
- Fetches context from `GET /api/context/inject?projects=<project1>,<project2>`
- Optionally fetches colored version for terminal display (`&colors=true`)
- Returns `hookSpecificOutput` with `hookEventName: 'SessionStart'` and `additionalContext`

### Phase 2: User Prompt Submit

**Handler: session-init** (timeout: 60s)

- Validates session ID exists (Codex CLI may not provide one)
- Checks project exclusion list (glob-based: `~/kunden/*,/tmp/*`)
- Handles image-only prompts with `[media prompt]` placeholder
- Calls `POST /api/sessions/init` with `{ contentSessionId, project, prompt }`
- Worker performs privacy check (strips `<private>` tags)
- If prompt is entirely private, skips with reason
- If context already injected for this session, skips SDK agent re-init
- For Claude Code only (not Cursor): initializes SDK agent via `POST /sessions/{sessionDbId}/init`
- Strips leading `/` from commands for cleaner observation semantics

### Phase 3: Post Tool Use

**Handler: observation** (timeout: 120s)

- Fires for EVERY tool use (matcher: `*`)
- Validates `toolName` and `cwd` exist
- Checks project exclusion
- Sends to `POST /api/sessions/observations` with full tool data:
  ```json
  {
    "contentSessionId": "session-id",
    "tool_name": "Read",
    "tool_input": { "file_path": "/path/to/file" },
    "tool_response": { "content": "file contents..." },
    "cwd": "/project/root"
  }
  ```
- Worker queues this for SDK agent compression (async, non-blocking)
- **No filtering at hook layer** — ALL tool outputs are captured
- Privacy tag stripping happens at the worker layer (edge processing)

### Phase 4: Stop / Summary

**Handler 1: summarize** (timeout: 120s, uses 5-minute fetch timeout)

- Reads transcript from `transcript_path` (provided by Claude Code in Stop hook)
- Extracts last assistant message from JSONL transcript (scans backwards)
- Strips `<system-reminder>` tags from assistant message
- Sends to `POST /api/sessions/summarize` with `{ contentSessionId, last_assistant_message }`
- Worker uses SDK agent to generate structured summary (request, investigated, learned, completed, next_steps, notes)

**Handler 2: session-complete** (timeout: 30s)

- Calls `POST /api/sessions/complete` with `{ contentSessionId }`
- Removes session from active sessions map
- Enables orphan reaper to clean up subprocess (fixes #842)

## 6. Context Injection — What Gets Included

### 6.1 The Injection Mechanism

Context is injected via Claude Code's `hookSpecificOutput` protocol:

```typescript
return {
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: contextMarkdown, // <-- injected into session
  },
  systemMessage: terminalOutput, // <-- shown to user (optional)
};
```

The `additionalContext` string is injected by Claude Code into the conversation context. The `systemMessage` is displayed to the user in the terminal.

### 6.2 Context Generation Pipeline

Source: `src/services/context/ContextBuilder.ts` and related modules.

The context builder orchestrates:

1. **Load config** — from `~/.claude-mem/settings.json` (observation counts, token display, type filters)
2. **Initialize SQLite** — direct database access (worker-side)
3. **Query observations** — filtered by project, type, and concept; ordered by `created_at_epoch DESC`
4. **Query summaries** — recent session summaries for the project
5. **Build timeline** — interleaves observations and summaries chronologically
6. **Render output** — markdown (for Claude) or ANSI-colored (for terminal)

### 6.3 Context Format (Markdown, Injected into Claude)

```markdown
# [project-name] recent context, 2026-02-28 3:30pm EST

**Legend:** session-request | exploration | implementation | debugging | decision | review

**Column Key**:

- **Read**: Tokens to read this observation (cost to learn it now)
- **Work**: Tokens spent on work that produced this record

**Context Index:** This semantic index (titles, types, files, tokens) is usually sufficient...
When you need implementation details, rationale, or debugging context:

- Fetch by ID: get_observations([IDs]) for observations visible in this index
- Search history: Use the mem-search skill for past decisions, bugs, and deeper research
- Trust this index over re-reading code for past decisions and learnings

**Context Economics**:

- Loading: 50 observations (2,450 tokens to read)
- Work investment: 125,000 tokens spent on research, building, and decisions
- Your savings: 122,550 tokens (98% reduction from reuse)

### Feb 27, 2026

**src/utils/tag-stripping.ts**
| ID | Time | T | Title | Read | Work |
|----|------|---|-------|------|------|
| #1234 | 3:30 PM | exploration | Tag Stripping Implementation Analysis | ~250 | 1,200 |
| #1235 | " | implementation | Added ReDoS Protection | ~180 | 800 |

**#1236** 4:15 PM implementation **Context Builder Refactored**
[Full narrative for most recent observations]
Read: ~320, Work: 1,500

**#S45** Session started (Feb 27, 3:00 PM)

**Investigated**: How context injection works in claude-mem hooks
**Learned**: Privacy tags stripped at edge before storage
**Completed**: Full hook system documentation
**Next Steps**: Implement similar system in helioy-plugins

---

**Previously**
A: [Last assistant message from prior session transcript]

Access 125k tokens of past research & decisions for just 2,450t. Use the claude-mem skill to access memories by ID.
```

### 6.4 Key Context Features

- **Token economics** — shows read cost vs. work investment (compression ratio)
- **Timeline grouping** — by date, then by file within each date
- **Ditto marks** — repeated times show `"` instead of the same timestamp
- **Full observation expansion** — most recent N observations show full narrative/facts
- **Session summaries** — interleaved in timeline with request/investigated/learned/completed/next_steps
- **Previously section** — extracts last assistant message from prior session's JSONL transcript
- **Configurable** — observation count, full count, type filters, concept filters, all via settings.json

### 6.5 Worktree Support

When running in a git worktree, the context handler detects the parent repo and queries BOTH parent and worktree observations, interleaved chronologically. This ensures continuity when branching into worktrees.

```typescript
const context = getProjectContext(cwd);
// context.allProjects = ['parent-repo', 'worktree-name']
const projectsParam = context.allProjects.join(",");
```

## 7. Privacy Tags — `<private>` System

Source: `src/utils/tag-stripping.ts`

### 7.1 Dual Tag System

Two XML-like tags control what gets stored:

1. **`<private>content</private>`** — User-level privacy control. Users wrap sensitive content to prevent storage.
2. **`<claude-mem-context>content</claude-mem-context>`** — System-level tag for auto-injected observations. Prevents recursive storage when context injection is active.

### 7.2 Stripping Implementation

```typescript
function stripTagsInternal(content: string): string {
  return content
    .replace(/<claude-mem-context>[\s\S]*?<\/claude-mem-context>/g, "")
    .replace(/<private>[\s\S]*?<\/private>/g, "")
    .trim();
}
```

Two public functions wrap this:

- `stripMemoryTagsFromJson(content)` — for tool inputs/responses
- `stripMemoryTagsFromPrompt(content)` — for user prompts

### 7.3 ReDoS Protection

A tag count limit (MAX_TAG_COUNT = 100) protects against malicious input with many nested/unclosed tags that could cause catastrophic regex backtracking. Tags are counted before processing; exceeding the limit logs a warning but still processes.

### 7.4 Edge Processing Pattern

Privacy stripping happens at the **hook layer** (before data reaches the worker/storage):

- The `session-init` handler sends raw prompts to the worker
- The worker's `/api/sessions/init` endpoint performs the privacy check
- If prompt is entirely `<private>`, session init is skipped with `{ skipped: true, reason: 'private' }`
- Observation data is sent to worker which strips tags before storage

### 7.5 CLAUDE.md Tag Usage

The `<claude-mem-context>` tag is also used in auto-generated CLAUDE.md files placed in subdirectories. The `replaceTaggedContent()` function in `claude-md-utils.ts` preserves user content outside tags while replacing only the tagged section:

```typescript
// Three cases:
// 1. No existing content → wrap in tags
// 2. Has existing tags → replace only tagged section
// 3. No tags → append tagged content at end
```

## 8. Exit Code Strategy

Source: `src/shared/hook-constants.ts`

```typescript
export const HOOK_EXIT_CODES = {
  SUCCESS: 0, // Success. stdout added to context.
  FAILURE: 1, // Non-blocking. stderr shown in verbose mode.
  BLOCKING_ERROR: 2, // Blocking. stderr fed to Claude for processing.
  USER_MESSAGE_ONLY: 3, // stderr shown to user, not injected into context.
};
```

### Exit Code Behavior per Claude Code docs:

- **Exit 0**: Success. For SessionStart/UserPromptSubmit, stdout is added to context.
- **Exit 2**: Blocking error. For SessionStart, stderr is shown to user only (not to Claude).
- **Other non-zero**: stderr shown in verbose mode only.

### Error Classification

The `isWorkerUnavailableError()` function in `hook-command.ts` classifies errors:

**Exit 0 (graceful degradation)** — worker unavailable:

- Transport failures: ECONNREFUSED, ECONNRESET, EPIPE, ETIMEDOUT, fetch failed
- Timeout errors
- HTTP 5xx server errors
- HTTP 429 rate limiting

**Exit 2 (blocking error)** — handler/client bug:

- HTTP 4xx client errors (bad request, validation error)
- Programming errors (TypeError, ReferenceError, SyntaxError)
- All other unexpected errors

### Philosophy

Worker/hook errors exit with code 0 to prevent Windows Terminal tab accumulation. The wrapper/plugin layer handles restart logic. ERROR-level logging is maintained for diagnostics via log files.

## 9. PostToolUse Observation Capture

### 9.1 What Gets Captured

**Everything.** The PostToolUse handler has `matcher: "*"` and no tool-name filtering at the hook layer. Every tool use generates an observation POST to the worker:

```json
{
  "contentSessionId": "session-uuid",
  "tool_name": "Read",
  "tool_input": { "file_path": "/path/to/file" },
  "tool_response": { "content": "..." },
  "cwd": "/project/root"
}
```

### 9.2 Filtering and Compression

Filtering happens at the **worker layer**, not the hook:

1. Worker receives raw observation via `POST /api/sessions/observations`
2. Worker strips `<private>` and `<claude-mem-context>` tags from tool_input and tool_response
3. Worker queues observation as a `PendingMessage` for the SDK agent
4. SDK agent (Claude or Gemini) processes pending queue asynchronously
5. Agent produces structured XML observations with type, title, subtitle, facts, narrative, concepts, files

### 9.3 SDK Agent Observation Format

The agent receives observations in XML format:

```xml
<observed_from_primary_session>
  <what_happened>Read</what_happened>
  <occurred_at>2026-02-28T15:30:00.000Z</occurred_at>
  <working_directory>/Users/dev/project</working_directory>
  <parameters>{"file_path": "/path/to/file"}</parameters>
  <outcome>{"content": "file contents..."}</outcome>
</observed_from_primary_session>
```

And produces compressed observations:

```xml
<observation>
  <type>exploration</type>
  <title>Tag Stripping Implementation Analysis</title>
  <subtitle>Dual-tag system for privacy control</subtitle>
  <facts>
    <fact>Two tags: private (user) and claude-mem-context (system)</fact>
    <fact>ReDoS protection with 100-tag limit</fact>
  </facts>
  <narrative>Analyzed the tag stripping implementation...</narrative>
  <concepts><concept>privacy</concept><concept>security</concept></concepts>
  <files_read><file>src/utils/tag-stripping.ts</file></files_read>
  <files_modified></files_modified>
</observation>
```

### 9.4 Observation Types (Mode-Dependent)

Types are defined per "mode" (e.g., code mode, research mode). The SDK agent must classify each observation. Invalid types fall back to the first type in the mode's list.

### 9.5 Pending Queue

Observations are queued in a persistent SQLite table (`pending_messages`) with claim-confirm semantics:

- Hook POSTs observation to worker
- Worker inserts into pending queue with timestamp
- SDK agent claims messages from queue
- On successful compression, messages are confirmed (deleted from queue)
- Failed messages remain in queue for retry

## 10. Bun Runner — The Bootstrap Layer

Source: `plugin/scripts/bun-runner.js`

Every hook command is invoked through `node bun-runner.js <script> [args...]`. This solves:

1. **Fresh install problem** — Bun may not be in PATH yet after smart-install
2. **Linux stdin EINVAL bug** — Bun's libuv crashes on fstat() of piped stdin from Claude Code. The runner buffers stdin in Node.js and writes it to a fresh pipe.
3. **Plugin disable check** — Early exit if plugin is disabled in Claude Code settings
4. **Broken path fix** — When `CLAUDE_PLUGIN_ROOT` is empty, script paths resolve to `/scripts/...`. The runner self-resolves its own location as fallback.

```javascript
// stdin buffering fix for Linux
const stdinData = await collectStdin(); // Buffer in Node.js
const child = spawn(bunPath, args, {
  stdio: [stdinData ? "pipe" : "ignore", "inherit", "inherit"],
});
if (stdinData && child.stdin) {
  child.stdin.write(stdinData);
  child.stdin.end();
}
```

## 11. Worker Wrapper

Source: `plugin/scripts/worker-wrapper.cjs` (minified)

The worker runs under a wrapper process that:

- Spawns the actual worker-service.cjs as a child with IPC channel
- Listens for `restart` and `shutdown` messages from the child
- Handles SIGTERM/SIGINT for graceful shutdown
- On unexpected child exit, wrapper also exits (hooks will restart if needed)
- Windows-specific: uses `taskkill /PID /T /F` for process tree cleanup

## 12. CLAUDE.md Subdirectory Updates

Beyond session context injection, claude-mem also writes `CLAUDE.md` files to subdirectories containing observed files. This uses `<claude-mem-context>` tags to wrap auto-generated content:

- Triggered after observations are processed
- Fetches timeline from worker API filtered by folder
- Formats as date-grouped table (same format as context injection)
- Writes atomically (temp file + rename)
- Skips project root (user-managed), `.git`, `node_modules`, `build`, `res`, `__pycache__`
- Skips folders where CLAUDE.md was read/modified in the same observation (race condition fix #859)
- Configurable exclusion list via `CLAUDE_MEM_FOLDER_MD_EXCLUDE` setting

## 13. Smart Install

Source: `plugin/scripts/smart-install.js` (5.8KB)

Runs as first SessionStart hook (timeout 300s):

- Auto-installs Bun if missing
- Auto-installs uv (Python package manager) for Chroma vector embeddings
- All status messages to stderr (not captured by Claude Code)
- Checks `needsInstall()` before running npm install

## 14. Key Differences from Helioy-Plugins

| Aspect             | claude-mem                              | helioy-plugins                        |
| ------------------ | --------------------------------------- | ------------------------------------- |
| Runtime            | Bun (via Node.js shim)                  | Node.js native                        |
| Worker model       | Persistent daemon (port 37777)          | MCP servers (stdio)                   |
| Memory engine      | SQLite + Chroma + SDK agent compression | Geometric memory (am-core)            |
| Hook communication | HTTP to localhost worker                | Direct MCP tool calls                 |
| Context injection  | hookSpecificOutput protocol             | system-reminder / CLAUDE.md           |
| Privacy            | `<private>` tag stripping               | Not implemented yet                   |
| Build              | esbuild bundles                         | TypeScript compiled                   |
| Observation model  | Every tool use captured, AI-compressed  | Selective buffering + salient marking |

## 15. Lessons for Helioy-Plugins

### What to adopt:

1. **hookSpecificOutput protocol** for SessionStart context injection — this is the official Claude Code way to inject context
2. **Self-delimiting JSON stdin reader** — Claude Code doesn't close stdin, must parse incrementally
3. **Exit code 0 for graceful degradation** — never block the user for memory system failures
4. **Stderr suppression in hooks** — Claude Code interprets stderr as errors
5. **Platform adapter pattern** — clean separation for multi-IDE support
6. **Edge processing for privacy** — filter at hook layer before storage
7. **Worktree detection** for combined project context

### What to avoid:

1. **Bun dependency** — adds massive bootstrap complexity (bun-runner.js, smart-install.js, Linux stdin bug workarounds)
2. **HTTP to localhost daemon** — adds latency and failure modes. MCP stdio is more reliable.
3. **Monolithic worker service** — 47K lines in worker-service.ts even after refactoring. Keep domain services independent.
4. **Subdirectory CLAUDE.md files** — creates filesystem pollution, race conditions with active files, needs extensive exclusion logic
5. **SDK agent for every observation** — expensive (Claude API calls for compression). Geometric memory with local scoring is more efficient.

### Key protocol details for implementation:

- `hookSpecificOutput.hookEventName` must be `'SessionStart'` for context injection
- `hookSpecificOutput.additionalContext` is the injected text (markdown works well)
- `systemMessage` is shown to user in terminal (optional)
- `{ continue: true, suppressOutput: true }` is the standard non-context response
- stdin is JSON with fields: `session_id`, `cwd`, `prompt`, `tool_name`, `tool_input`, `tool_response`, `transcript_path`
- SessionStart hooks may receive no stdin — handle undefined gracefully
