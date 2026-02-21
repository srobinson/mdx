---
title: "GSD-2 Architecture Analysis: Multi-Provider AI Coding Agent"
date: 2026-03-18
category: research
tags: [gsd, coding-agent, architecture, multi-provider, extension-system, native-bindings, tui, mcp]
summary: "Deep technical analysis of gsd-2 (v2.28.0), a 232K LOC multi-provider AI coding agent with native Rust bindings, extension system, and structured planning."
---

# GSD-2 Architecture Analysis

## Executive Summary

GSD-2 is a production-grade AI coding agent CLI built as an npm workspace monorepo (232K LOC across TypeScript and Rust). It implements a clean four-layer architecture: `pi-ai` (provider abstraction), `pi-agent-core` (agent loop), `pi-coding-agent` (tools, extensions, session management), and `pi-tui` (terminal UI). The codebase is notable for its provider-agnostic design supporting 10+ API protocols, a sophisticated extension system with lifecycle hooks, native Rust bindings via NAPI for performance-critical operations, and a structured planning system ("GSD workflow") that enables autonomous multi-milestone execution.

## Project Metadata

- **Version**: 2.28.0
- **Language**: TypeScript (ESM), Rust (native addon)
- **Node**: >=20.6.0 (uses `--experimental-strip-types`)
- **Build**: tsc + napi-rs (Rust to N-API), npm workspaces
- **Package Manager**: npm 10.9.3
- **Total LOC**: ~232K (TS + Rust)
- **Test Files**: 230 test files (155 in the gsd extension alone)
- **License**: MIT

### Workspace Packages

| Package | Purpose |
|---------|---------|
| `@gsd/pi-ai` | Provider abstraction, streaming, model registry |
| `@gsd/pi-agent-core` | Agent loop, tool execution, event stream |
| `@gsd/pi-coding-agent` | Tools, extensions, sessions, compaction, CLI |
| `@gsd/pi-tui` | Terminal UI with differential rendering |
| `@gsd/native` | Rust N-API bindings (TypeScript wrappers) |

### Key Dependencies

- `@anthropic-ai/sdk`, `openai`, `@google/genai`, `@mistralai/mistralai`, `@aws-sdk/client-bedrock-runtime` (AI providers)
- `@modelcontextprotocol/sdk` (MCP)
- `@sinclair/typebox` (schema validation for tool parameters)
- `@mariozechner/jiti` (forked jiti for extension loading with virtual modules)
- `napi-rs` (Rust N-API bridge)
- `sql.js` (session persistence, GSD state DB)
- `proper-lockfile` (session file locking)

---

## 1. Architecture and Design Patterns

### Layer Separation

The architecture follows strict dependency direction:

```
pi-tui (UI) -> pi-coding-agent (domain) -> pi-agent-core (loop) -> pi-ai (providers)
                                         -> native (Rust bindings)
```

Each layer is a separate npm workspace package with its own build. The layers communicate through well-defined TypeScript interfaces.

### Agent Loop (`pi-agent-core/agent-loop.ts`)

The core agent loop is 705 lines of focused logic. Key design decisions:

1. **AgentMessage abstraction**: The loop operates on `AgentMessage` (a union of LLM messages + custom app messages via declaration merging). Translation to provider-specific `Message[]` happens only at the LLM call boundary via `convertToLlm()`.

2. **Two entry points**: `agentLoop()` starts a new conversation turn; `agentLoopContinue()` resumes from existing context (retries, queued messages).

3. **Nested loop structure**: An outer loop handles follow-up messages (queued after agent would stop), an inner loop handles tool calls and steering messages (user interruptions mid-run).

4. **Steering and Follow-up queues**: Users can inject messages while the agent is running. Steering messages interrupt tool execution (remaining tools are skipped with "Skipped due to queued user message"). Follow-up messages wait until the agent finishes its current work.

5. **Tool execution modes**: Sequential or parallel. Parallel mode prepares all tool calls sequentially (for validation/blocking), then executes allowed tools concurrently.

6. **Before/After hooks**: `beforeToolCall` can block execution; `afterToolCall` can modify results. These are used by the extension system for permission gating and result transformation.

7. **EventStream pattern**: The loop returns an `EventStream<AgentEvent, AgentMessage[]>` that supports both async iteration and a `.result()` promise. Events include `agent_start`, `turn_start/end`, `message_start/update/end`, `tool_execution_start/update/end`.

### Agent Class (`pi-agent-core/agent.ts`)

Wraps the loop with state management. Notable patterns:

- **Subscriber model**: `subscribe(fn)` returns an unsubscribe function. The Agent emits AgentEvents to all listeners.
- **Idle tracking**: `waitForIdle()` returns a promise that resolves when the current prompt completes.
- **Queue modes**: Both steering and follow-up queues support "all" (batch) or "one-at-a-time" delivery modes.
- **Dynamic API key resolution**: `getApiKey` is called per LLM request, supporting expiring OAuth tokens.

### Streaming Architecture

The `EventStream<T, R>` class (`pi-ai/utils/event-stream.ts`) is a generic async-iterable push stream with:
- Internal queue for undelivered events
- Waiting consumer tracking
- Completion detection via `isComplete` predicate
- Final result extraction via `extractResult`

`AssistantMessageEventStream` specializes this for LLM responses, pushing granular events (text_delta, thinking_delta, toolcall_delta) as they arrive from the provider.

---

## 2. AI Provider Abstraction (`pi-ai`)

### Registry Pattern

Providers register via `registerApiProvider()` into a global `Map<string, RegisteredApiProvider>`. Each provider implements two functions:
- `stream()`: Raw streaming with provider-specific options
- `streamSimple()`: Unified interface with reasoning level abstraction

**10 registered API protocols**:
- `anthropic-messages`
- `openai-completions` (also covers xAI, Groq, Cerebras, OpenRouter, etc.)
- `openai-responses`
- `azure-openai-responses`
- `openai-codex-responses`
- `google-generative-ai`
- `google-gemini-cli`
- `google-vertex`
- `bedrock-converse-stream`
- `mistral-conversations`

### Lazy Loading

Provider SDKs are lazy-loaded on first use:
```typescript
let _AnthropicClass: typeof Anthropic | undefined;
async function getAnthropicClass(): Promise<typeof Anthropic> {
    if (!_AnthropicClass) {
        const mod = await import("@anthropic-ai/sdk");
        _AnthropicClass = mod.default;
    }
    return _AnthropicClass;
}
```

Bedrock is doubly lazy: loaded only when a Bedrock model is used, and the import path is constructed dynamically to avoid bundler tree-shaking.

### Message Normalization

`transformMessages()` handles cross-provider message compatibility:
- Thinking blocks: kept as-is for same model, converted to text for different models, redacted blocks dropped for cross-model
- Tool call IDs: normalized for API compatibility (OpenAI generates 450+ char IDs that Anthropic rejects)
- Text signatures: provider-specific metadata stripped for cross-provider replay

### Model System

Models are defined in a generated file (`models.generated.ts`) with full type information:
```typescript
interface Model<TApi extends Api> {
    id: string; name: string; api: TApi; provider: Provider;
    baseUrl: string; reasoning: boolean; input: ("text" | "image")[];
    cost: { input, output, cacheRead, cacheWrite }; // $/million tokens
    contextWindow: number; maxTokens: number;
    compat?: OpenAICompletionsCompat; // provider quirk overrides
}
```

The `compat` field is notable: it allows per-model overrides for OpenAI-compatible API quirks (reasoning effort format, max tokens field name, strict mode support, etc.).

### Stealth Mode

The Anthropic provider includes "stealth mode" that mimics Claude Code's tool naming:
```typescript
const claudeCodeVersion = "2.1.62";
const claudeCodeTools = ["Read", "Write", "Edit", "Bash", "Grep", "Glob", ...];
```

This suggests the tool sends requests that look like Claude Code to the API, likely for pricing/caching benefits.

---

## 3. Extension System

### Architecture

Extensions are TypeScript modules loaded via a forked `jiti` that supports virtual modules (for compiled Bun binary distribution). The system has three layers:

1. **Loader** (`loader.ts`): Discovers and loads extensions from paths, creates `ExtensionAPI` objects
2. **Runner** (`runner.ts`): Manages extension lifecycle, event dispatch, context creation
3. **Wrapper** (`wrapper.ts`): Wraps extension-registered tools with before/after hook interception

### Extension API Surface

Extensions receive an `ExtensionAPI` with:
- **Registration**: `registerTool()`, `registerCommand()`, `registerShortcut()`, `registerFlag()`, `registerMessageRenderer()`, `registerProvider()`
- **Event hooks**: `on(event, handler)` for 20+ lifecycle events
- **Actions**: `sendMessage()`, `sendUserMessage()`, `setModel()`, `setThinkingLevel()`, `exec()`
- **State access**: `getActiveTools()`, `getAllTools()`, `getCommands()`, `getThinkingLevel()`

### Lifecycle Events

The extension system supports:
- Agent lifecycle: `before_agent_start`, `agent_end`, `session_shutdown`
- Tool lifecycle: `tool_call` (can block), `tool_result` (can modify)
- Session: `session_before_switch`, `session_before_fork`, `session_before_compact`, `session_before_tree`
- Context: `context` (transform messages before LLM), `before_provider_request` (modify API payload)
- Input: `input` (transform/handle user input)
- Resources: `resources_discover` (register skills, prompts, themes)
- Bash: `user_bash` (intercept bash commands)

### Tool Registration

Tools use TypeBox schemas for parameter validation:
```typescript
api.registerTool({
    name: "mcp_call",
    label: "Call MCP Tool",
    description: "...",
    parameters: Type.Object({ server: Type.String(), tool: Type.String(), args: Type.Optional(Type.String()) }),
    execute: async (toolCallId, params, signal, onUpdate, ctx) => { ... }
});
```

### Discovery

Extension discovery follows a layered pattern:
1. Project-local: `cwd/.pi/extensions/` (requires explicit trust, TOFU model)
2. Global: `~/.pi/agent/extensions/`
3. Explicitly configured paths from settings

### Virtual Module System

For compiled Bun binaries, all workspace packages are pre-bundled as virtual modules:
```typescript
const VIRTUAL_MODULES = {
    "@sinclair/typebox": _bundledTypebox,
    "@gsd/pi-agent-core": _bundledPiAgentCore,
    "@gsd/pi-tui": _bundledPiTui,
    "@gsd/pi-ai": _bundledPiAi,
    "yaml": _bundledYaml,
};
```

---

## 4. Native Rust Layer

### Modules

The Rust addon (`native/crates/engine`) exposes 30+ functions via NAPI:

| Module | Operations |
|--------|-----------|
| `grep` | Regex search in files, respects gitignore |
| `glob` | File pattern matching with streaming callbacks |
| `fd` | File discovery (like fd-find) |
| `diff` | Unified diff generation via `similar` crate |
| `highlight` | Syntax highlighting via `syntect` |
| `clipboard` | System clipboard read/write via `arboard` |
| `ast` | AST operations via tree-sitter |
| `html` | HTML to Markdown conversion |
| `text` | Unicode-aware text wrapping, truncation, width calculation |
| `image` | Image processing (resize, format conversion) |
| `truncate` | Smart content truncation (head, tail, output) |
| `json_parse` | Streaming/partial JSON parsing |
| `xxhash` | Fast hashing (xxHash32) |
| `ttsr` | Tree-sitter rule compilation/checking |
| `ps` | Process management (kill tree, list descendants) |
| `stream_process` | Stream chunk processing |
| `gsd_parser` | GSD-specific file parsing (frontmatter, sections, roadmap) |
| `fs_cache` | Filesystem scan caching |
| `git` | Git operations via libgit2 |

### Build and Distribution

Cross-platform binaries via platform-specific npm packages:
```
@gsd-build/engine-darwin-arm64
@gsd-build/engine-darwin-x64
@gsd-build/engine-linux-arm64-gnu
@gsd-build/engine-linux-x64-gnu
@gsd-build/engine-win32-x64-msvc
```

Resolution order: platform npm package -> local release build -> local dev build.

### TypeScript Bridge

Each native module has a TypeScript wrapper (`packages/native/src/*/index.ts`) that:
1. Imports from the native addon
2. Provides typed interfaces
3. Handles fallbacks when native module unavailable

---

## 5. TUI Architecture (`pi-tui`)

### Rendering

The TUI uses a custom **differential rendering** engine (1200 lines in `tui.ts`):

- **Component model**: Simple `render(width: number): string[]` interface. Components return arrays of ANSI-styled strings.
- **Diff rendering**: Compares new lines with previous lines, only updates changed regions. Uses synchronized output (`CSI ?2026h/l`) to prevent flicker.
- **Overlay system**: Modal components rendered on top of base content with configurable positioning (anchor-based, percentage-based, absolute). Overlays support focus management and visibility callbacks.
- **Cursor tracking**: Tracks both logical cursor (content end) and hardware cursor (for IME positioning). Components emit `CURSOR_MARKER` (APC sequence) at the cursor position.
- **Image support**: Detects image-capable terminals, queries cell dimensions via `CSI 16 t`.

### Components

- `Box`: Container with padding and background
- `Input`: Text input with cursor, kill ring, undo stack
- `Editor`: Multi-line text editor
- `Loader`: Animated loading indicator
- `Image`: Terminal image rendering
- `CancellableLoader`: Loader with abort support

### Key Management

Uses Kitty keyboard protocol for modifier detection. Supports key release events for specific components.

---

## 6. MCP Integration

MCP integration is implemented as the `mcporter` extension (`src/resources/extensions/mcporter/`), providing lazy access to external MCP servers:

### Three-Tool Pattern

1. `mcp_servers`: Lists available MCP servers (cached after first call)
2. `mcp_discover`: Gets tool signatures for a specific server
3. `mcp_call`: Calls a tool on an MCP server

This keeps token usage near-zero until the agent needs MCP tools. The extension shells out to a globally installed `mcporter` CLI rather than implementing the MCP client protocol directly.

### Tool Discovery

Reads configuration from Claude Desktop, Cursor, VS Code, and mcporter config files. Server details and tool schemas are cached after first discovery.

---

## 7. GSD Extension: Autonomous Planning System

The `gsd` extension (`src/resources/extensions/gsd/`) is the largest component (~100 files, 155 tests). It implements structured project execution:

### Architecture

- **State machine**: Reads `.gsd/` directory state from disk after each agent turn. Determines next action (plan, execute, verify, complete).
- **Auto mode**: `gsd auto` loops fresh sessions until milestone complete. Each "unit" (plan slice, execute task, complete slice) gets a fresh session.
- **Milestones**: Multi-milestone execution with parallel orchestration support via git worktrees.
- **Verification gates**: Post-execution verification with evidence capture.
- **Crash recovery**: Lock files, runtime records, session forensics.
- **Model routing**: Complexity-based model selection with routing history.
- **Budget management**: Token budget tracking with alert levels and enforcement.
- **Worktree isolation**: Git worktree management for parallel milestone execution.

### File-Based State

All state lives in `.gsd/` directory files:
- Milestone files, slice files, task files
- Roadmap, continue.md, summary files
- Activity logs, verification evidence
- GSD database (SQLite via sql.js)

### Prompts

System prompt injection via `before_agent_start` hook. Loads workflow prompts, agent instructions, preferences, and skill discovery data.

---

## 8. Session Management

### JSONL Persistence

Sessions are stored as JSONL files (one JSON line per entry). Entry types:
- `message`: User, assistant, or tool result messages
- `compaction`: Summarization markers
- `branch_summary`: Branch point summaries
- `custom_message`: Extension-injected context
- `model_change`, `thinking_level_change`: Configuration changes
- `label`: User bookmarks
- `session_info`: Display names

### Compaction

When context grows large, `compact()`:
1. Extracts file operations from message history
2. Serializes conversation for summarization
3. Calls the LLM with a summarization system prompt
4. Replaces old messages with a compaction entry containing the summary

### Tree Navigation

Sessions support branching (fork from any entry) and tree navigation. Branch summaries preserve context across branches.

---

## 9. Code Quality

### Testing

- 230 test files total, 155 in the GSD extension
- Tests use Node.js built-in test runner (`node --test`)
- Coverage target: 40% statements, 40% lines (via c8)
- Integration tests for pack/install, e2e smoke
- Test infrastructure includes custom TypeScript resolution hooks

### TypeScript Patterns

- Strict ESM throughout (`.js` extensions in imports)
- TypeBox for runtime schema validation
- Declaration merging for extensible message types
- Discriminated unions for events (`type` field)
- Lazy imports for expensive SDKs

### Error Handling

- Agent loop converts all errors to graceful error messages (no unhandled rejections)
- Extension errors are caught and reported via `emitError()` without crashing the agent
- Tool execution errors are wrapped in error tool results
- Provider errors include retry-after headers, backoff logic

---

## 10. What Stands Out

### 1. EventStream Pattern
The `EventStream<T, R>` class is elegant. It combines push-based event delivery with async iteration and a final result promise. The agent loop, provider streaming, and tool execution all use the same pattern.

### 2. Steering and Follow-Up Queues
The ability to inject messages mid-execution (steering) or post-completion (follow-up) with configurable delivery modes is a sophisticated control mechanism for interactive agents.

### 3. Provider Compatibility Layer
The `compat` field on models that allows per-model overrides for API quirks is a pragmatic solution to the reality that "OpenAI-compatible" APIs are not actually compatible.

### 4. Extension System with Virtual Modules
The dual-mode extension loading (jiti aliases for Node.js dev, virtual modules for Bun binary) solves a real distribution problem. Extensions can use workspace packages regardless of how the agent is installed.

### 5. Hashline Edit Tool
A novel editing approach where files are read with `LINE#HASH` prefixes, and edits reference lines by hash anchors. This provides resilience against line number shifts between read and edit operations.

### 6. Differential TUI Rendering
The custom TUI renderer with synchronized output, overlay compositing, and cursor marker extraction is a complete terminal rendering solution. No dependency on Ink or blessed.

### 7. Auto Mode State Machine
The file-based state machine for autonomous execution is well-designed. Each unit gets a fresh session (avoiding context pollution), with crash recovery and budget management.

### 8. Native Rust Bridge
Moving grep, glob, diff, text wrapping, and image processing to Rust provides measurable performance gains. The three-tier loading (npm package, release build, dev build) makes development ergonomic.
