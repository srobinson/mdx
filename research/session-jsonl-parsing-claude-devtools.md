---
title: Claude Code Session JSONL Parsing Pipeline
type: research
tags: [claude-code, session-parsing, jsonl, electron, history-matters]
summary: Reverse-engineered JSONL schema and parsing pipeline from matt1398/claude-devtools, an Electron app that reads and visualizes Claude Code session data.
status: active
source: github-researcher
confidence: high
created: 2026-04-24
updated: 2026-04-24
---

## Executive Summary

claude-devtools is an Electron desktop app that reads, parses, and visualizes Claude Code session JSONL files from `~/.claude/projects/`. It provides the most complete open source reverse engineering of the Claude Code session format available. The parsing pipeline is streaming, handles subagent resolution across two directory layouts, and classifies messages into visualization-ready chunks.

Repository: https://github.com/matt1398/claude-devtools

## JSONL File Layout

Session files live at `~/.claude/projects/{encoded-path}/{session-uuid}.jsonl`.

The encoded path replaces `/` with `-`. Example:
- Real path: `/Users/stuart/Dev/helioy`
- Encoded: `-Users-stuart-Dev-helioy`

**Path encoding is lossy** for paths containing literal dashes. The codebase falls back to reading the `cwd` field from the first JSONL entry for accurate path resolution.

Subagent files follow two structures:
- **New**: `{session-uuid}/agent_{agent-uuid}.jsonl` (subdirectory)
- **Legacy**: `agent_{agent-uuid}.jsonl` (same directory as parent)
- Linking: subagent entries have `isSidechain: true` and `sessionId` pointing to parent.

## JSONL Entry Schema

Each line is a JSON object. Six entry types via `type` discriminator:

| Type | Purpose |
|------|---------|
| `user` | User messages AND tool results (dual purpose) |
| `assistant` | AI responses with content blocks |
| `system` | Turn duration metadata, init events |
| `summary` | Conversation summaries |
| `file-history-snapshot` | File backup snapshots |
| `queue-operation` | Queue management events |

### The isMeta Hinge

`UserEntry` serves two roles:
- `isMeta: false` + content is string = real user input (chunk starter)
- `isMeta: true` + content is array with `tool_result` blocks = internal tool result flow

This is the single most important parsing distinction.

### Content Block Types

- `TextContent`: `{ type: 'text', text: string }`
- `ThinkingContent`: `{ type: 'thinking', thinking: string, signature: string }`
- `ToolUseContent`: `{ type: 'tool_use', id: string, name: string, input: Record<string, unknown> }`
- `ToolResultContent`: `{ type: 'tool_result', tool_use_id: string, content: string | ContentBlock[], is_error?: boolean }`
- `ImageContent`: `{ type: 'image', source: { type: 'base64', media_type: string, data: string } }`

### Key Fields Per Entry

- `uuid`: unique message ID
- `parentUuid`: threading (parent message)
- `requestId`: groups streaming entries from a single API response
- `cwd`: working directory
- `gitBranch`: current branch
- `isSidechain`: true for subagent messages
- `sessionId`: links subagent to parent session
- `userType`: user type classification
- `agentId`: agent identifier for subagent entries

Assistant entries additionally carry:
- `usage`: `{ input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens }`
- `model`: model identifier (e.g. `claude-sonnet-4-20250514`)

## Parsing Pipeline

### 1. Streaming File Read

Line-by-line via `readline.createInterface`. Never materializes entire file. Each non-empty line parsed with `JSON.parse` then typed via `parseChatHistoryEntry()`.

### 2. Entry to ParsedMessage

`parseChatHistoryEntry()` extracts all fields, calls `extractToolCalls()` and `extractToolResults()` on content blocks, converts timestamps.

### 3. Streaming Deduplication

`deduplicateByRequestId()`: Claude Code writes multiple JSONL entries per API response with incrementally increasing `output_tokens`. Only the last entry per `requestId` is kept. Without this, token counts are wildly inflated.

### 4. Message Classification

Five categories:

| Category | Criteria |
|----------|----------|
| `hardNoise` | system/summary/file-history-snapshot/queue-operation; synthetic assistant (`model='<synthetic>'`); user messages with only `<system-reminder>` or `<local-command-caveat>` tags; interruptions |
| `compact` | `isCompactSummary === true` |
| `system` | User entries starting with `<local-command-stdout>` or `<local-command-stderr>` |
| `user` | `type='user'`, `isMeta!==true`, not teammate, has text/image content, no system output tags |
| `ai` | Everything else (assistant messages + internal tool result messages) |

XML tags filtered: `<local-command-stdout>`, `<local-command-stderr>`, `<local-command-caveat>`, `<system-reminder>`, `<command-name>`, `<command-args>`, `<teammate-message>`.

### 5. Chunk Building

Four chunk types built from classified messages:
- **UserChunk**: one per real user message
- **AIChunk**: groups consecutive AI messages until next user/system/compact boundary; attaches subagent processes and tool executions
- **SystemChunk**: one per command output message
- **CompactChunk**: marks compaction boundaries

UserChunks and AIChunks are independent, not paired.

### 6. Subagent Resolution

1. List subagent files from both directory structures
2. Parse each subagent JSONL
3. Filter warmup subagents (first user message is "Warmup")
4. Link to parent Task calls via `tool_use_id`
5. Detect parallel execution (100ms overlap threshold)
6. Propagate team metadata through continuation files

## Session Metadata (Single-Pass)

`analyzeSessionFileMetadata()` extracts in one streaming pass:
- First user message text (skipping noise)
- Message count (user + first main-thread AI response)
- Ongoing detection via activity tracking (thinking, tool_use, text_output, interruption, exit_plan_mode)
- Git branch from first entry with `gitBranch`
- Context consumption with compaction-aware multi-phase token tracking
- Stale session detection: ongoing + no file modification in 5+ minutes = dead

## Architecture

Four service domains in `src/main/services/`:

- **Discovery**: `ProjectScanner`, `SubagentLocator`, `SubagentResolver`, `SessionSearcher`, `WorktreeGrouper`, `ProjectPathResolver`
- **Parsing**: `SessionParser`, `MessageClassifier`, `ClaudeMdReader`, `GitIdentityResolver`, `AgentConfigReader`
- **Analysis**: `ChunkBuilder`, `ChunkFactory`, `ConversationGroupBuilder`, `SemanticStepExtractor`, `ToolExecutionBuilder`, `SubagentDetailBuilder`, `ProcessLinker`
- **Infrastructure**: `FileWatcher`, `ConfigManager`, `HttpServer`, `NotificationManager`, `SshConnectionManager`, `FileSystemProvider`

Notable patterns:
- `FileSystemProvider` abstraction with local + SSH implementations
- Cursor-based pagination with base64 timestamp+sessionId composite keys
- Dual API surface: Electron IPC + Fastify HTTP

## Code Quality

**Strengths**: Clean discriminated union types with exhaustive guards. Streaming I/O throughout. Well-decomposed services. Comprehensive path validation blocking sensitive files. 45 test files.

**Weaknesses**: `ProjectScanner` is 1436 lines (needs splitting). Duplicated ongoing-detection logic. HTTP routes all return 200 (no error status codes). `costUsd` is always 0 (dead code). `--no-frozen-lockfile` in CI. No tests for deduplication, subagent resolution, or conversation grouping.

## Security

- Path validation blocks SSH keys, AWS/GCP/Azure creds, .env, private keys, Docker configs
- Symlink escape prevention via `realpathSync.native()`
- Session IDs validated against `^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$`
- No hardcoded secrets
- CSP via proper `contextBridge` usage
- Concern: `JSON.parse` without line-length limits on JSONL (OOM vector with adversarial files)

## Key Source Files

| What | Path |
|------|------|
| JSONL entry types | `src/main/types/jsonl.ts` |
| ParsedMessage types | `src/main/types/messages.ts` |
| Chunk types | `src/main/types/chunks.ts` |
| Domain types | `src/main/types/domain.ts` |
| JSONL parsing + metrics | `src/main/utils/jsonl.ts` |
| Tool extraction | `src/main/utils/toolExtraction.ts` |
| Content sanitization | `src/shared/utils/contentSanitizer.ts` |
| Message tags | `src/main/constants/messageTags.ts` |
| Session parser | `src/main/services/parsing/SessionParser.ts` |
| Message classification | `src/main/services/parsing/MessageClassifier.ts` |
| Session state detection | `src/main/utils/sessionStateDetection.ts` |
| Metadata extraction | `src/main/utils/metadataExtraction.ts` |
| Path encoding/decoding | `src/main/utils/pathDecoder.ts` |
| Chunk building | `src/main/services/analysis/ChunkBuilder.ts` |
| Conversation grouping | `src/main/services/analysis/ConversationGroupBuilder.ts` |
| Subagent resolution | `src/main/services/discovery/SubagentResolver.ts` |
| Project discovery | `src/main/services/discovery/ProjectScanner.ts` |

## Relevance to Helioy

**history-matters** (WIP): This parsing pipeline covers the exact problem space. The JSONL schema, streaming dedup, message classification taxonomy, and subagent resolution are directly portable. The `SemanticStepExtractor` and `ConversationGroupBuilder` are relevant to surfacing hidden knowledge from past sessions.

**manicure**: Different approach (live proxy vs. post-hoc JSONL reading). Not directly applicable, but the JSONL schema documentation is useful reference for understanding what Claude Code persists vs. what flows through the API.

## What the Parser Does NOT Handle

- Cost calculation (field exists but always 0)
- Conversation branching (tracks parentUuid but renders flat)
- Image rendering (base64 preserved but not displayed)
- Cross-session search (searches within project, not across)
