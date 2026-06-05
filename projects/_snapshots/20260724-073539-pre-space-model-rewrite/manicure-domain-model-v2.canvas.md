---
title: "Manicure Domain Model v2: Canvas Layer"
type: projects
tags: [manicure, domain-model, canvas, react-flow, visualization, real-time]
summary: Canvas layer specification for Manicure. Maps the domain model (sessions, exchanges, content blocks) to React Flow nodes and edges, with real-time SSE-driven rendering.
status: active
project: manicure
confidence: high
created: 2026-04-12
updated: 2026-04-12
parent: manicure-domain-model-v2.md
---

# Canvas Layer

## Approach

React Flow. SVG edges, HTML/CSS nodes. The dominant node-graph library for React/TypeScript with 36k stars, active maintenance, and first-class support for custom nodes, edge types, and real-time data updates via React state.

We are not building workflows. We are rendering observed wire traffic as it happens. The graph grows in real time. Nodes appear as exchanges stream in. Edges materialize as tool_use/tool_result links resolve.

## Node Types

Each custom React Flow node type maps to a domain entity.

### ExchangeNode

The primary node. One per API round-trip.

```
ExchangeNode
  id: string              # Exchange ID
  model: string           # e.g., "claude-opus-4-6", "claude-haiku-4-5"
  provider: string
  stop_reason: string     # end_turn, tool_use, max_tokens
  duration_ms: number
  usage: UsageStats       # input, output, cache_read, cache_create
  stream: boolean
  timestamp: datetime
```

Visual treatment varies by context:
- **Model**: color coding distinguishes models at a glance (opus vs haiku vs sonnet)
- **Stop reason**: `tool_use` nodes have open output ports. `end_turn` nodes are terminal. `max_tokens` nodes are truncated (warning state).
- **Cache behavior**: visual indicator when cache_read > 0 (reusing prior context) vs cache_create > 0 (warming cache)

### ContentBlockNode

Child nodes within an exchange. Each content block in the response is a distinct visual element.

```
TextBlockNode
  text: string            # Preview/truncation for canvas, full on drill-down

ThinkingBlockNode
  text: string            # Collapsible by default
  
ToolUseBlockNode
  tool_use_id: string     # Stable ID for edge linking
  tool_name: string       # e.g., "Read", "cx_recall", "fmm_list_files"
  input: object           # Summary of arguments

ToolResultBlockNode
  tool_use_id: string     # Links back to originating ToolUseBlock
  is_error: boolean
  content: string         # Preview of result
```

### SessionNode

Optional container node (React Flow supports parent/child nesting). Groups all exchanges belonging to a session. Provides aggregate stats at the session level.

```
SessionNode
  id: string
  provider_session_id: string
  started_at: datetime
  exchange_count: number
  total_usage: AggregateUsage
```

Whether sessions render as container nodes or as a separate navigation concern is a UI decision. The domain model supports both.

## Edge Types

Edges represent observed relationships. Every edge is derived from data on the wire.

### ToolUseEdge

Links a ToolUseBlockNode in exchange N's response to the corresponding ToolResultBlockNode in exchange N+1's request.

```
ToolUseEdge
  source: ToolUseBlockNode.tool_use_id
  target: ToolResultBlockNode.tool_use_id
  tool_name: string
  is_error: boolean       # Red edge if tool returned an error
```

These edges are the core visual link in the tool use loop. Three parallel tool requests in exchange N produce three edges fanning into exchange N+1.

### SequenceEdge

Links consecutive exchanges within a session by temporal order.

```
SequenceEdge
  source: ExchangeNode[N].id
  target: ExchangeNode[N+1].id
  type: "sequence"
```

Lightweight connector showing conversation flow. Visually distinct from tool use edges (dashed or muted).

### ContinuationEdge

Links an exchange with `stop_reason: tool_use` to the follow-up exchange that carries the tool results. A semantic specialization of SequenceEdge.

```
ContinuationEdge
  source: ExchangeNode[N].id       # stop_reason: tool_use
  target: ExchangeNode[N+1].id     # carries tool_result blocks
  type: "continuation"
```

## Layout Strategy

The canvas receives exchanges as a stream. Layout must be incremental (new nodes positioned without repositioning the entire graph).

### Primary axis: time flows down

New exchanges appear below existing ones. The canvas grows vertically. The viewport auto-scrolls to follow the latest exchange (with user override to freeze scrolling and explore history).

### Secondary axis: parallelism flows right

Concurrent exchanges (overlapping timestamps, e.g., haiku title gen alongside opus main exchange) are placed side by side. Detected from timestamp overlap, not inferred intent.

### Content blocks: nested within exchange

Content blocks render as child elements inside their parent exchange node. ToolUseBlocks are positioned at the output edge of the exchange. ToolResultBlocks at the input edge. Text and thinking blocks fill the body.

### Automatic vs manual layout

React Flow supports both computed and user-dragged positions. Initial placement is automatic (time-ordered vertical, parallel-horizontal). Users can drag nodes to rearrange. Positions persist for the session.

## Real-time Data Flow

```
mitmproxy addon
  → storage (disk persistence)
  → broadcast (SSE emit)
      → EventSource (/api/stream)
          → React Query cache update
              → React Flow node/edge state update
                  → Canvas re-render
```

This pipeline already exists for exchanges. The canvas layer replaces the current ExchangeList/ExchangeDetail components with React Flow nodes.

### SSE event handling

When a new exchange event arrives:

1. **Create ExchangeNode** with metadata from the event payload
2. **Create ContentBlockNodes** for each content block in the response
3. **Create edges**: scan for tool_use blocks, match against pending tool_use IDs from previous exchanges to create ToolUseEdges
4. **Position**: apply layout algorithm based on timestamp and parallelism detection
5. **Animate**: new nodes fade in or slide into position

### Streaming exchanges

For `stream: true` exchanges, the node appears when the request starts and updates progressively as the response streams in. Content blocks materialize as they arrive. The node transitions from "pending" to "complete" state.

## Interaction Model

### Default view
All exchanges in the selected session, laid out as a time-ordered graph with tool use edges.

### Click exchange node
Expands to show content blocks as child nodes. Drill-down into full request/response IR.

### Click content block
Shows full content. For ToolUseBlock: the complete input arguments. For ToolResultBlock: the full result payload. For TextBlock: the complete text. For ThinkingBlock: the full reasoning.

### Click structural reference
From the normalization layer: click a system_ref or toolset_ref badge to view the deduplicated system prompt or tool definitions.

### Hover edge
Highlights the linked tool_use and tool_result pair across exchanges.

## State Management

Following the pattern from simstudioai/sim: Zustand stores with single responsibility.

```
useCanvasStore        # React Flow nodes, edges, viewport, selection
useSessionStore       # Active session, session list, session metadata
useExchangeStore      # Exchange data (replaces current useExchanges hook)
useStreamStore        # SSE connection state, pending events
```

React Query remains the server state layer. Zustand manages UI state. React Flow manages canvas state.
