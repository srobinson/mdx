---
title: "Manicure Domain Model v2: Build Spec"
type: projects
tags: [manicure, build-spec, architecture, cli, react-flow, session, process-management]
summary: Implementation spec for manicure v2. Process management (proxy + Claude Code), project context extraction, session model with pwd, UI improvements, React Flow canvas, view toggle.
status: active
project: manicure
confidence: high
created: 2026-04-13
updated: 2026-04-13
parent: manicure-domain-model-v2.md
---

# Build Spec

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  manicure start ~/my-project                    │
│                                                 │
│  ┌──────────┐    ┌───────────┐    ┌──────────┐ │
│  │ Claude   │───▶│ mitmproxy │───▶│ Anthropic│ │
│  │ Code     │◀───│ (proxy)   │◀───│ API      │ │
│  └──────────┘    └─────┬─────┘    └──────────┘ │
│       ▲                │                        │
│       │                │ SSE                    │
│       │                ▼                        │
│       │          ┌───────────┐                  │
│       │          │ Web UI    │                  │
│       │          │ :8788     │                  │
│       │          └───────────┘                  │
│       │                                         │
│  pwd: ~/my-project                              │
│  .claude/CLAUDE.md ◄── project context          │
│  .claude/settings.json ◄── harness config       │
└─────────────────────────────────────────────────┘
```

One proxy. One client. One canvas. `manicure start` owns everything.

## Phase 1: Process Management

### `manicure start [directory]`

Spawns two processes:

1. **mitmproxy** reverse proxy on `:8787` (existing)
2. **Claude Code** CLI pointed at the proxy, working directory set to `[directory]` (defaults to cwd)

Claude Code is spawned with `ANTHROPIC_BASE_URL=http://localhost:8787` so all API traffic routes through the proxy.

```
manicure start                     # proxy + claude in cwd
manicure start ~/my-project        # proxy + claude in specified dir
manicure start --no-claude         # proxy only (backward compat)
```

Process lifecycle:
- `manicure start` spawns both processes, prints the web UI URL
- Ctrl+C tears down both cleanly
- If Claude Code exits, the proxy stays running (session is over, user may want to review)
- If the proxy crashes, Claude Code loses its backend (acceptable failure mode)

### PTY management

Claude Code is a TUI. Spawn it with a PTY so it renders correctly in the user's terminal. The proxy runs headless. The user interacts with Claude Code directly in their terminal while the web UI runs in the browser.

### Project context extraction

On start, read from `[directory]/.claude/`:

```
ProjectContext
  working_directory: str          # Absolute path
  project_name: str               # Basename of working_directory
  claude_md: str | None           # Contents of CLAUDE.md if present
  settings: dict | None           # Parsed settings.json if present
  hooks: list[Hook] | None        # Extracted from settings
  mcp_servers: list[str] | None   # MCP server names from settings
```

This context is:
- Attached to the Session entity
- Available in the web UI for correlation ("the model loaded 106 tools because these 5 MCP servers are configured")
- Re-read on change (file watch) so mid-session config changes are captured

## Phase 2: Session Model

### Backend

New IR entity alongside the existing exchange infrastructure.

```python
class Session(BaseModel, frozen=True):
    id: str                              # Internal UUID
    provider_session_id: str | None      # From client metadata
    working_directory: str               # From spawned process
    project_name: str                    # Basename
    device_id: str | None
    account_id: str | None
    started_at: datetime
    updated_at: datetime
    exchange_count: int
    usage: AggregateUsage
    project_context: ProjectContext | None
```

### Storage

`sessions.jsonl` index alongside `exchanges/index.jsonl`. One line per session, updated on each exchange.

### API

```
GET /api/v1/sessions                    # List sessions
GET /api/v1/sessions/{id}               # Session detail + project context
GET /api/v1/sessions/{id}/exchanges     # Exchanges for a session
```

### SSE events

New event types on the existing `/api/stream`:

```
{ "type": "session_start", "session": { ... } }
{ "type": "session_update", "session": { ... } }
{ "type": "exchange", "exchange": { ... } }        # existing
```

## Phase 3: Exchange Normalization

Per the normalization spec. Implement the structure/substance split:

- Content-hash system prompts, tool definitions, conversation history
- Store structural artifacts once per unique hash
- NormalizedExchange carries refs to structural artifacts + inline substance
- Full raw exchange always available on disk (normalization is a view)

### API

```
GET /api/v1/exchanges/{id}              # Normalized exchange (substance + refs)
GET /api/v1/exchanges/{id}/raw          # Full raw request + response
GET /api/v1/artifacts/{hash}            # Structural artifact by content hash
```

## Phase 4: UI Improvements (List View)

Improve the existing list/detail view before adding the canvas.

### Session grouping

Left sidebar top level becomes session list. Click a session to see its exchanges. Session items show:
- Project name (from pwd)
- Model(s) used
- Exchange count
- Total tokens (the hero metric)
- Duration

### Exchange list (within session)

- Model name + color coding
- Token bar (input | cache | output) as the primary visual
- Stop reason badge
- Relative timestamp with absolute on hover

### Exchange detail

- Existing inspect/request/response tabs stay
- Add token breakdown visualization (cache read vs cache create vs fresh input vs output)
- Content blocks already render well, keep them

### View toggle

Header gets a view switcher: **List** | **Canvas**

Both views share the same data (React Query cache, Zustand stores). Switching is instant because the data is already loaded. The toggle controls which component renders in the main viewport.

## Phase 5: Canvas View (React Flow)

### Setup

Add `@xyflow/react` to the frontend dependencies. Create a `CanvasView` component that consumes the same exchange data as the list view.

### Node types

Per the canvas spec:

- `ExchangeNode`: primary node, color-coded by model, showing token profile and stop reason
- `TextBlockNode`: model text output
- `ThinkingBlockNode`: collapsible reasoning block
- `ToolUseBlockNode`: tool request with name and argument summary
- `ToolResultBlockNode`: tool response with result preview and error state

### Edge types

- `ToolUseEdge`: links tool_use block to tool_result block across exchanges (the core visual)
- `SequenceEdge`: temporal ordering between exchanges (muted/dashed)
- `ContinuationEdge`: tool_use stop_reason to follow-up exchange (semantic link)

### Layout

- Time flows down (vertical primary axis)
- Parallel exchanges side by side (detected from timestamp overlap)
- Content blocks nested within exchange nodes
- Auto-scroll follows latest exchange, user can freeze to explore

### Real-time updates

SSE events create new React Flow nodes and edges incrementally. No full re-layout on each exchange. New nodes animate in at the bottom of the graph.

### Interaction

- Click exchange: expand content blocks
- Click tool_use block: show full input arguments
- Click tool_result block: show full result
- Hover edge: highlight linked pair across exchanges
- Click structural ref badge: show deduplicated system prompt or tool definitions

## Phase 6: Project Context Panel

A panel (drawer or sidebar) showing the project context:

- Working directory
- CLAUDE.md contents (the instructions driving the agent)
- MCP servers configured (correlate with tool definitions on the wire)
- Hooks (correlate with system-reminder injections)
- Settings summary

This panel answers "why does the wire traffic look like this?"

## Build Order

| Phase | Depends on | Deliverable |
|-------|-----------|-------------|
| 1. Process management | existing CLI | `manicure start` spawns proxy + Claude Code |
| 2. Session model | Phase 1 | Sessions as first-class entities, API + SSE |
| 3. Normalization | Phase 2 | Structure/substance split, content hashing |
| 4. UI improvements | Phase 2 | Session grouping, token emphasis, view toggle |
| 5. Canvas | Phase 3, 4 | React Flow visualization with linked blocks |
| 6. Project context | Phase 1, 4 | Context panel correlating config to wire traffic |

Phases 3 and 4 can run in parallel once Phase 2 is complete.
