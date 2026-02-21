---
title: "Manicure Domain Model v2: Sessions, Exchanges, and the State Machine Canvas"
type: projects
tags: [manicure, domain-model, ir, session, exchange, canvas, architecture]
summary: Domain model for Manicure's next phase. Introduces Session as a first-class entity, decomposes exchanges into linkable content blocks, and defines the data contract for a real-time canvas visualization of LLM state machinery.
status: active
project: manicure
confidence: high
created: 2026-04-12
updated: 2026-04-12
---

# Manicure Domain Model v2

## Vision

Manicure sits between a coding agent (Claude Code) and the upstream LLM API. The proxy sees every state transition on the wire. The client abstracts the machinery away. The API docs describe it statically. Manicure shows it running.

The canvas renders the state machine in real time. A user opens Claude Code on the left, the canvas on the right. They type one message and watch the machinery light up: a title generation sidecar fires on a cheap model, the main exchange warms the prompt cache, tool requests fan out, results flow back, the model synthesizes its response. Every decision has a cost. Every transition is visible.

For someone learning how agents work, this is transformative. You stop seeing a chat interface and start seeing the state machine underneath.

## Observed Reality

A single user action ("What are we working on?") produces multiple API round-trips:

| # | Model | Purpose | Input | Cache Create | Cache Read | Output | Stop Reason |
|---|-------|---------|-------|-------------|------------|--------|-------------|
| 0 | haiku-4-5 | Quota check | 8 | 0 | 0 | 1 | max_tokens |
| 1 | haiku-4-5 | Title generation | 343 | 0 | 0 | 12 | end_turn |
| 2 | opus-4-6 | Main (tool use) | 4,082 | 46,736 | 0 | 263 | tool_use |
| 3 | opus-4-6 | Main (completion) | 12,547 | 0 | 46,736 | 374 | end_turn |

Observations:

- **Multiple models per session.** Haiku handles cheap sidecars. Opus handles the real work.
- **Multiple exchanges per user action.** The tool use loop (exchanges 2 and 3) and the title gen sidecar are all triggered by one keystroke.
- **Cache lifecycle is visible.** Exchange 2 warms the cache (46,736 creation). Exchange 3 reads it (46,736 read, zero creation).
- **Tool requests fan out and results flow back.** Exchange 2's response contains three parallel tool_use blocks. Exchange 3's request carries the corresponding tool_result blocks.

## Entity Hierarchy

Three levels, two observed, one derived:

```
Session (observed: explicit session_id from client)
  └── Exchange (observed: one API round-trip)
        ├── Request IR
        │     ├── SystemPart[]
        │     ├── Message[] (conversation history)
        │     ├── ToolDef[] (tool definitions)
        │     └── SamplingParams
        └── Response IR
              └── ContentBlock[] (text, thinking, tool_use, etc.)
```

**Turn** (the user's logical action) is excluded from the IR. The proxy represents the wire. A turn would require inferring client intent from heuristics (temporal proximity, model patterns, stop_reason chains), which are provider-specific and will break as client behavior evolves. The canvas already has the raw material to show relationships: tool use chains via stable IDs, parallel sidecars via overlapping timestamps. Visual grouping emerges from observed data.

## Session

A session is a conversation. Identified by `session_id` from client metadata. Created implicitly when the first exchange with a new `session_id` arrives.

```
Session
  id: str                    # Internal UUID
  provider_session_id: str   # Client-provided session_id
  device_id: str | None      # From metadata
  account_id: str | None     # From metadata
  started_at: datetime       # Timestamp of first exchange
  updated_at: datetime       # Timestamp of most recent exchange
  exchange_count: int         # Running count
  usage: AggregateUsage      # Accumulated token stats
```

A session spans multiple models. The `usage` aggregate tracks totals across all exchanges. Because each exchange in a stateless API re-sends the full conversation history, naive input token sums overcount. The meaningful cost metric is `cache_creation + cache_miss_input + output` per exchange, summed across the session.

## Exchange

One API round-trip. The atomic unit. Already modeled in the current IR as `InternalRequest` + `InternalResponse`. For the canvas, exchanges need additional metadata:

```
Exchange
  id: str                    # Internal UUID
  session_id: str            # Links to parent session
  sequence: int              # Order within session (0-indexed)
  started_at: datetime       # Request timestamp
  completed_at: datetime     # Response timestamp
  duration_ms: int           # Wall clock
  model: str                 # Model used for this specific exchange
  provider: str
  stream: bool
  stop_reason: str | None    # end_turn, tool_use, max_tokens
  usage: UsageStats          # Token profile for this exchange
  request: InternalRequest
  response: InternalResponse
```

## Content Blocks as Canvas Elements

The canvas does not just show exchanges. It decomposes them into their constituent blocks, each a visual element with typed links.

### Response blocks (model output)

Each block in the response `content` array is a canvas element:

- **TextBlock**: The model's text output. Terminal node.
- **ThinkingBlock**: Internal reasoning. Collapsible on canvas.
- **ToolUseBlock**: A tool request. Has a stable `id` (e.g., `toolu_017vB3q67q2KjciNrkcmoVm6`). Links forward to the corresponding ToolResultBlock in the next exchange.

### Request blocks (flowing back)

- **ToolResultBlock**: The tool's response. Has `tool_use_id` linking back to the originating ToolUseBlock. Carries the result content (text, images, errors).

### Link Graph

```
Exchange N (stop_reason: tool_use)
  Response:
    ├── ThinkingBlock
    ├── ToolUseBlock [id: A] ─────► Exchange N+1 Request: ToolResultBlock [tool_use_id: A]
    ├── ToolUseBlock [id: B] ─────► Exchange N+1 Request: ToolResultBlock [tool_use_id: B]
    └── ToolUseBlock [id: C] ─────► Exchange N+1 Request: ToolResultBlock [tool_use_id: C]

Exchange N+1 (stop_reason: end_turn)
  Response:
    ├── ThinkingBlock
    └── TextBlock (final answer)
```

The `tool_use.id` / `tool_result.tool_use_id` pairing is already present in the Anthropic API. The IR preserves it. The canvas renders it as directed edges.

## Parallel Streams

Within a session, exchanges may fire in parallel (title gen sidecar alongside the main conversation). The canvas represents this through temporal positioning: overlapping timestamps produce side-by-side elements rather than sequential ones.

No explicit "stream" or "channel" concept in the IR. Parallelism is visible from timestamps alone.

## Provider Mapping

The IR is provider-neutral. Each provider adapter maps to the same structures:

| Concept | Anthropic | OpenAI (future) |
|---------|-----------|-----------------|
| Session ID | `metadata.session_id` | TBD (thread_id?) |
| Tool request | `tool_use` content block with `id` | `tool_calls` array with `id` |
| Tool response | `tool_result` with `tool_use_id` | `tool` role message with `tool_call_id` |
| Thinking | `thinking` content block | `reasoning` (if exposed) |
| Cache stats | `cache_read_input_tokens`, `cache_creation_input_tokens` | Not available |

The adapter layer translates. The IR and canvas speak one language.

## What This Enables

1. **Real-time state machine visualization.** Watch the agent's decision loop as it happens.
2. **Token cost attribution.** See exactly where tokens are spent: system prompt, conversation history, tool definitions, tool results, model output.
3. **Cache behavior analysis.** Visualize prompt cache warming and reuse across a session.
4. **Educational content.** Each canvas session is a story: "I typed one message, here's the 50,000 token state machine that answered it."
5. **Debugging.** When an agent misbehaves, replay the exchange graph. See what the model saw, what it asked for, what it got back.
