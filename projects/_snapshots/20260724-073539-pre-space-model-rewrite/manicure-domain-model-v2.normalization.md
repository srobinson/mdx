---
title: "Manicure Domain Model v2: Exchange Normalization"
type: projects
tags: [manicure, domain-model, normalization, ir, performance]
summary: Normalization strategy for manicure exchanges. Separates stable scaffolding (system prompts, tool definitions) from per-exchange substance (user content, model output, tool interactions, token profile). Deduplicates via content hashing.
status: active
project: manicure
confidence: high
created: 2026-04-12
updated: 2026-04-12
parent: manicure-domain-model-v2.md
---

# Exchange Normalization

## Problem

A single exchange request from Claude Code carries tens of thousands of tokens of scaffolding: system prompts, CLAUDE.md instructions, MCP server instructions, skill definitions, tool schemas. The actual user content may be five words.

From the observed data, exchange 3 of a simple "What are we working on?" session:

| Component | Approximate Scale |
|-----------|------------------|
| System prompt blocks (CLAUDE.md, skills, MCP instructions) | ~40,000+ tokens |
| Tool definitions array | thousands of tokens |
| System-reminder blocks injected into messages | thousands of tokens |
| Actual user message | 6 words |
| Sampling params | trivial |

This scaffolding is largely **identical across exchanges within a session**. The API's own prompt cache confirms this: 46,736 tokens created in exchange 2, 46,736 tokens read from cache in exchange 3. The API already knows this content is the same.

The normalization layer does the same thing at the IR level.

## Principle

Separate **structure** from **substance**.

- **Structure**: content that is stable across exchanges within a session. Store once, reference by content hash.
- **Substance**: content that is unique to this exchange. Store inline. This is what the canvas renders.

## Structural Components (deduplicated)

These are extracted from the exchange, hashed, and stored as shared artifacts. The exchange holds a reference (hash + summary metadata), not the full content.

### System Prompt

The `system` array from the request. Typically stable for the entire session.

```
SystemPromptRef
  hash: str              # Content hash of the full system array
  block_count: int       # Number of SystemPart blocks
  total_chars: int       # Approximate size
  cache_hint: bool       # Whether cache hints are present
```

### Tool Definitions

The `tools` array from the request. Stable within a session unless the tool set changes (e.g., MCP server reconnects, lazy tool activation).

```
ToolSetRef
  hash: str              # Content hash of the full tools array
  count: int             # Number of tool definitions
  names: list[str]       # Tool names for quick reference
```

### Conversation History

Messages prior to the current turn. Each exchange in a stateless API re-sends the full history. The new content is the last message(s).

```
HistoryRef
  hash: str              # Content hash of messages[:-1] (all but last)
  message_count: int     # Number of prior messages
  total_chars: int       # Approximate size
```

## Substance (inline per exchange)

What the canvas cares about. What makes this exchange unique.

### On the request side

- **New user content**: the last message in the messages array (the actual user input for this turn)
- **Sampling params**: max_tokens, temperature, etc.
- **Metadata**: session_id, device_id, model, provider, stream flag
- **Provider extras**: thinking config, context management directives, output format constraints

### On the response side

- **Content blocks**: text, thinking, tool_use (each a canvas element)
- **Usage stats**: the full token profile (input, output, cache read, cache create)
- **Stop reason**: end_turn, tool_use, max_tokens
- **Timing**: duration, started_at, completed_at

## Normalized Exchange

```
NormalizedExchange
  # Identity
  id: str
  session_id: str
  sequence: int

  # Timing
  started_at: datetime
  completed_at: datetime
  duration_ms: int

  # Model
  model: str
  provider: str
  stream: bool

  # Structural references (deduplicated)
  system_ref: SystemPromptRef
  toolset_ref: ToolSetRef
  history_ref: HistoryRef

  # Substance: request
  new_content: list[ContentBlock]     # The actual new user message(s)
  sampling: SamplingParams
  metadata: RequestMetadata
  provider_extras: dict

  # Substance: response
  response_content: list[ContentBlock] # text, thinking, tool_use blocks
  stop_reason: str | None
  usage: UsageStats
  response_provider_extras: dict
```

## Deduplication Strategy

Content hashing using a fast hash (xxhash or similar) over the serialized JSON of each structural component.

```
First exchange in session:
  system_ref.hash = xxh64(serialize(system)) → store full content
  toolset_ref.hash = xxh64(serialize(tools)) → store full content
  history_ref.hash = xxh64(serialize([])) → empty, trivial

Second exchange in session:
  system_ref.hash = same → reference existing
  toolset_ref.hash = same → reference existing
  history_ref.hash = xxh64(serialize(messages[:-1])) → store full content

Third exchange in session:
  system_ref.hash = same → reference existing
  toolset_ref.hash = same → reference existing
  history_ref.hash = new (history grew) → store full content
```

The system prompt and tool set are stored once per session (typically). Conversation history grows but is only stored when the hash changes, which is every exchange (since history grows). The key win is system + tools, which dominate the token count.

## Drill-down

The canvas shows substance by default. When a user clicks into structural detail:

- Click system_ref → retrieve full system prompt blocks
- Click toolset_ref → retrieve full tool definitions with schemas
- Click history_ref → retrieve prior conversation messages

The full raw exchange (request + response) is always available on disk via the existing storage backend. Normalization is a **view**, not a lossy transformation.

## Relationship to Prompt Cache

The normalization mirrors what the API's prompt cache already tells us:

| Cache signal | Normalization equivalent |
|-------------|------------------------|
| `cache_creation_input_tokens` | First time a structural hash is seen |
| `cache_read_input_tokens` | Structural hash matches a previous exchange |
| `input_tokens` (non-cached) | Substance tokens (new content) |

This symmetry means the normalized view can show: "these 46,736 tokens are the same system prompt and tools as last time" directly on the canvas, backed by both the content hash and the cache stats.
