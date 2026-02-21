---
title: Claude API Workbench
type: projects
tags: [claude-code, mitmproxy, proxy, developer-tools, breakpoint, workbench, helioy]
summary: mitmproxy-resident inspector and breakpoint editor for Claude /v1/messages traffic with schema-aware tree editing
status: active
project: claude-api-workbench
confidence: high
created: 2026-04-10
updated: 2026-04-10
---

# Claude API Workbench

## TL;DR

A mitmproxy-resident tool that captures every Claude `/v1/messages` exchange to disk, serves a live log viewer on `localhost:8787`, and optionally pauses a request so the operator can edit the JSON body in a schema-aware editor before forwarding it to Anthropic. Burp Repeater, domain-specific to the Claude API.

## Motivation

1. **Visibility**: see exactly what Claude Code (or any client) is sending. The captured payload is the ground truth for debugging context bloat, unexpected tool inclusions, and prompt drift.
2. **Experimentation**: strip tools, shorten system prompts, drop old tool_results, then forward and observe how Claude responds with less context. This is the fastest path to empirical context engineering.
3. **Foundation**: Stuart will scale this. It is the data plane for future work on automated context optimization, replay, and diffing.

## Quick start

Copy, paste, run. No cert install, no sudo, no system proxy settings, no TLS interception.

```bash
# 1. Install
curl -fsSL https://claude-workbench.dev/install.sh | bash
```

```bash
# 2. Start the workbench (blocking, keep this terminal open)
claude-workbench start
```

```bash
# 3. In another terminal, launch Claude Code pointed at the workbench
ANTHROPIC_BASE_URL=http://localhost:8123 claude
```

Open the web UI at `http://localhost:8787`. Every `/v1/messages` request from Claude Code now routes through the workbench, gets persisted to disk, and appears in the live log. Arm the breakpoint in the UI to pause the next request for editing.

### What the install script does

Single-file shell installer, the same pattern as `rustup`, `bun`, `uv`, `ollama`, `fly`, and every other modern dev tool. The script:

1. Detects the host OS and architecture
2. Ensures a Python toolchain is available (uses `uv` if present, otherwise bootstraps it)
3. Installs `claude-workbench` and its dependencies (mitmproxy, starlette, uvicorn) into an isolated environment
4. Symlinks the `claude-workbench` binary into `~/.local/bin` (or the OS-appropriate location)
5. Prints next-step instructions pointing at `claude-workbench start`

The user sees a one-liner. Everything else is hidden.

### What `claude-workbench start` runs

```bash
mitmdump \
  --mode reverse:https://api.anthropic.com \
  --listen-port 8123 \
  -s <bundled addon>
```

`--mode reverse` is what makes this work without a cert install. mitmproxy accepts plain HTTP on localhost and handles TLS only on the outbound leg to Anthropic. The client never sees a self-signed cert because there is no TLS between the client and the proxy. The bundled addon starts the starlette web UI on port 8787 as a background task on the same event loop.

## Scope (V1, locked)

**In scope**
- Capture every `/v1/messages` request and response to disk
- Persistent on-disk log viewable via a web UI
- Live-updating log list via Server-Sent Events
- Request-only breakpoint: pause before forwarding, edit, release
- Schema-aware JSON editor tuned to the `/v1/messages` body
- Global toggle + armed-once mode for the breakpoint
- Token and character accounting, visible live during edits

**Explicit non-goals**
- Response breakpoints (mitmproxy buffers the full SSE stream; holding it too long causes client timeouts)
- Filter rules (pause-when-model-equals, pause-when-tool-present)
- Drop and canned-response button
- Retention policy or log rotation
- Diff view against the original
- Replay of historical exchanges
- JSON Schema validation (Anthropic's server validates)
- Auth (localhost bind is the only guard)

## Real-world data

A single capture from a routine Claude Code session produced this breakdown. Every design decision below is anchored to these numbers.

| Section | Size | Count | Note |
|---|---|---|---|
| **tools** | **192 KB (67%)** | 147 | Dominates the payload. The `Agent` tool alone is 30 KB of description. |
| system | 28 KB | 3 parts | Part `[2]` alone is 27.5 KB. Parts `[0]` and `[1]` are under 100 chars. |
| messages | 17 KB | 5 turns | `messages[0]` has 5 text blocks, 4 of which are `<system-reminder>` injections. |
| metadata, thinking, output_config, max_tokens, model, stream | < 1 KB combined | — | Rarely edited. |
| **total** | **285 KB** | | Approx 71k tokens. |

**Tool prefix distribution** (147 tools):

```
mcp__plugin_helioy-tools_linear-server    37
<bare>                                    29    (Read, Edit, Bash, Agent, ...)
mcp__plugin_helioy-tools_supabase         29
mcp__plugin_helioy-tools_am               12
mcp__plugin_helioy-bus_helioy-warroom      9
mcp__plugin_helioy-tools_cm                9
mcp__plugin_helioy-tools_fmm               8
mcp__plugin_helioy-bus_helioy-bus          7
mcp__plugin_helioy-tools_mdm               7
```

A flat 147-row checkbox list is unusable. Tool grouping by prefix is mandatory, not optional.

## Stack (locked)

| Layer | Choice | Rationale |
|---|---|---|
| Proxy | mitmproxy, **reverse proxy mode** (`--mode reverse:https://api.anthropic.com`) | No TLS between the client and the proxy. No root CA install. mitmproxy is a plain HTTP server on localhost; Claude Code opts in via `ANTHROPIC_BASE_URL`. Addon API, async hooks, and breakpoint mechanism are identical to regular mode. |
| Backend | starlette + uvicorn | Runs inside mitmproxy's asyncio loop. Scales. One process, zero IPC, shared asyncio state. |
| Persistence | append-only `index.jsonl` + per-exchange directories | Safe concurrent writes, cheap tail for SSE, lazy-loaded detail. |
| Frontend | Vanilla JS SPA | No framework. Custom schema-aware editor, no generic JSON tree library. |
| Transport | HTTP + SSE | One-way server push for live log and paused-flow events. POST for mutation + release. No WebSocket in V1. |
| Bind | `localhost:8123` (reverse proxy) + `localhost:8787` (web UI) | Two distinct ports on localhost. Reverse proxy is what Claude Code connects to. Web UI is what the operator opens in a browser. Both bind to loopback only; no auth in V1. |

### Why not a generic JSON tree editor

`vanilla-jsoneditor` was the community-consensus pick in research. It would have worked. The custom editor is a better fit because:

1. The `/v1/messages` schema is small and stable. Five top-level fields account for 99% of what anyone would edit.
2. The operations that matter (strip tool, strip system part, truncate tool_result, edit last user message) are domain-specific and benefit from dedicated UI over generic key/value editing.
3. Schema-aware rendering shows what you care about at a glance. A generic tree makes you hunt through `messages[4].content[2].text`.
4. Bundle size: under 20 KB of vanilla JS vs 300-500 KB.

Fallback: any top-level field the editor does not recognize renders as a raw JSON textarea. Nothing gets silently dropped.

## Directory layout

### Scripts

```
~/.claude/scripts/claude-proxy/
  addon.py              # mitmproxy entry: request/response hooks
  persistence.py        # index.jsonl writer, exchange dir writer
  breakpoint.py         # state machine: mode, paused flow registry
  server.py             # starlette app, uvicorn startup from addon load()
  routes.py             # /api/* handlers, static mount
  web/
    index.html
    app.js
    app.css
```

### Logs

```
~/.claude/logs/proxy/
  index.jsonl                      # append-only, one line per exchange
  exchanges/
    {iso_ts}-{flow_id}/
      request.json                 # parsed
      request.raw                  # raw body
      response.json                # parsed, SSE reassembled when applicable
      response.raw                 # raw body (SSE stream or JSON)
```

`index.jsonl` schema, one line per exchange:

```json
{
  "id": "<mitmproxy flow.id>",
  "ts": "<iso8601>",
  "model": "claude-opus-4-6",
  "path": "exchanges/2026-04-10T14-23-45-abc123/",
  "req": {
    "system_parts": 3,
    "system_chars": 28248,
    "tools_count": 147,
    "tools_chars": 192435,
    "messages_count": 5,
    "messages_chars": 17232,
    "total_chars": 285115
  },
  "res": {
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 71234, "output_tokens": 892, "cache_read_input_tokens": 0},
    "text_chars": 3456,
    "tool_calls": [{"name": "Read", "id": "toolu_..."}]
  },
  "mutated": false
}
```

## Components

1. **Capture addon** (`addon.py`): mitmproxy `request()` and `response()` hooks. Writes to persistence. Consults breakpoint state. Awaits the release event when paused. Registers a `done()` hook to release any still-paused flows at shutdown with an error response.
2. **Persistence** (`persistence.py`): atomic append to `index.jsonl` (one write per exchange, line-buffered). Per-exchange directory creation. Schema-versioned.
3. **Breakpoint manager** (`breakpoint.py`): holds `{flow_id: PausedFlow}` registry, where `PausedFlow` carries the `flow`, an `asyncio.Event`, and `paused_at_ms` (epoch millisecond timestamp recorded when the flow was registered, used by the UI to render an elapsed timer). Tracks mode (`off`, `armed_once`). Exposes `arm()`, `disarm()`, `is_armed()`, `register_flow(flow)`, `release(flow_id, mutated_body)`.
4. **HTTP server** (`server.py`): starlette app wrapped in `uvicorn.Server`, started from the addon's `load()` hook as a background task on the mitmproxy event loop. Zero IPC with the addon; shared asyncio state via module-level references.
5. **Web UI** (`web/`): single-page app, split view. Left rail: live list of exchanges. Right pane: detail view of the selected exchange, or the schema-aware editor when a flow is paused.

## API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Static SPA |
| GET | `/api/exchanges` | Paginated index (reads tail of `index.jsonl`) |
| GET | `/api/exchanges/{id}` | Full request + response from the exchange directory |
| GET | `/api/stream` | SSE: `exchange` events (new log entries) and `paused` events (flow waiting for release) |
| POST | `/api/breakpoint/arm` | Set mode to `armed_once` |
| POST | `/api/breakpoint/disarm` | Set mode to `off` |
| POST | `/api/release/{flow_id}` | Body: mutated request JSON. Applies mutation and releases the flow. |

## Event flows

**Normal request**:

```
client → mitmproxy → request()
         → persistence.write_request()
         → breakpoint.is_armed() == False
         → forward to Anthropic
         → response()
         → persistence.write_response()
         → server.sse_emit({type: "exchange", ...})
         → client receives response
```

**Armed-once request**:

```
client → mitmproxy → request()
         → persistence.write_request()
         → breakpoint.is_armed() == True
         → breakpoint.disarm()
         → evt = asyncio.Event()
         → paused_at_ms = now_ms()
         → paused[flow.id] = PausedFlow(flow, evt, paused_at_ms)
         → server.sse_emit({type: "paused", flow_id, body, index_line, paused_at_ms})
         → await evt.wait()                     [flow blocked here]

[UI displays editor]
[user edits tree]
[user clicks Forward]

POST /api/release/{flow.id}
body: mutated request JSON
         → flow.request.set_text(json.dumps(mutated))
         → evt.set()
         → forward to Anthropic
         → response()
         → persistence.write_response()  (mutated=true)
         → server.sse_emit({type: "exchange", ...})
         → client receives response
```

## Schema-aware editor sections

### model and sampling params

Simple form controls at the top of the editor.

- `model`: dropdown (free-text override available)
- `max_tokens`: number input
- `stream`: readonly checkbox (always true in practice)
- `thinking`: collapsed advanced row
- `output_config`: collapsed advanced row

### system

A card per part. Card header shows index, type, size, and the first line of content as a preview.

- Checkbox on the card: strip on unchecked
- Click card to expand into an inline textarea for edit
- Any part over 500 chars stays collapsed by default
- `cache_control` markers are displayed as badges but not editable in V1

### tools

The most important section of the workbench. Prefix-grouped, collapsible.

- Global bulk bar: `[all] [none] [drop all MCP]`
- One group per prefix, header shows group name, count, total size
- Group-level bulk bar: `[all] [none]`
- Inside each group, one row per tool with: checkbox, name, size, description tooltip
- Bare tools group labeled `Built-in`, shown with de-prefixed names
- Rows sorted within group by size descending (biggest, most strippable tools at the top)

### messages

Turn-by-turn cards. Each turn header shows index, role, summary of content blocks.

Inside a turn, iterate `content` blocks (always a list). Per block type:

- `text`: inline edit, character count, strip toggle
- `tool_use`: show `name` and `id`, input summary in a collapsed `<details>`, strip toggle
- `tool_result`: show size, is_error badge, actions `[edit | truncate | drop]`
- `thinking`: size, strip toggle; a global bulk action exists to strip all thinking blocks at once

System-reminders inside user text blocks are treated as plain text in V1. A later revision can parse `<system-reminder>…</system-reminder>` markers and offer per-reminder toggles.

### advanced

Collapsed section at the bottom containing `metadata`, anything else not recognized. Raw JSON textarea.

### paused-flow header

Shown at the top of the editor whenever a flow is paused. Contains:

- Short flow id (first 8 chars of `flow.id`)
- Model name
- **Elapsed timer**: time since the flow was paused. Format `MM:SS`, or `HH:MM:SS` when over an hour. Computed client-side as `now() - paused_at_ms` using the `paused_at_ms` from the SSE event, refreshed every second from a local `setInterval`. Counts up, never down. The workbench does not know the client's timeout and does not try to guess it.
- **Informational line** next to the timer, always visible: `Client timeout is set by API_TIMEOUT_MS on the Claude Code side (default 10m). Raise it at launch: API_TIMEOUT_MS=3600000 claude`. This is pure guidance so the operator knows how to give themselves a longer editing window before arming the next breakpoint.

### footer

Always visible. Shows:

- Original size: chars and approximate tokens
- Mutated size: chars and approximate tokens, plus delta percentage
- Buttons: `[ Forward ]`, `[ Forward Unmodified ]`, `[ Drop ]`

The live token delta is the feedback loop that makes this feel like a workbench.

## Design notes worth locking

- **Concurrent paused flows**: the registry is a dict keyed by `flow.id`. N simultaneous pauses work. V1 UI surfaces only the most recent paused flow; the backend does not limit.
- **Shutdown**: mitmproxy `done()` hook walks the paused registry and releases every flow with a synthetic error response so clients do not hang.
- **Flow ID**: use `flow.id` directly. mitmproxy gives a UUID4 string per flow.
- **Auth**: localhost bind only. If this ever binds to a non-loopback address, add a bearer token gate first.
- **SSE vs WebSocket**: SSE is one-way server push, which fits the model. Releases go over POST. Upgrade to WebSocket only if bidirectional traffic volume justifies it.
- **Retention**: not handled in V1. Logs grow. V1.1 adds rotation by age or count.
- **Console prints**: the existing stdout prints from the current addon stay for now. The web UI is the primary read surface; terminal output is a fallback for when the UI is not running.

## Operational environment

### ANTHROPIC_BASE_URL (routing)

The workbench intercepts Claude Code traffic via `ANTHROPIC_BASE_URL`. Claude Code honors this env var and sends `/v1/messages` to whatever host it names. Point it at the workbench's reverse-proxy port and every request flows through:

```bash
ANTHROPIC_BASE_URL=http://localhost:8123 claude
```

No system proxy settings, no TLS certificates, no sudo. Unset the env var or close the terminal session to restore direct-to-Anthropic traffic.

### API_TIMEOUT_MS (breakpoint editing window)

The workbench does not control the client timeout. The Claude Code client does, via the `API_TIMEOUT_MS` environment variable. Default is 600000 (10 minutes). Maximum is 2147483647 (about 24.8 days). Values above the maximum overflow the underlying timer and cause requests to fail immediately. Reference: https://code.claude.com/docs/en/env-vars

This directly caps how long the workbench can hold a paused request before the client gives up on its side of the socket. Ten minutes is the outer edge of a default editing session. Raise it at launch when you expect to spend longer at the breakpoint. Combine with `ANTHROPIC_BASE_URL` on the same command line:

```bash
ANTHROPIC_BASE_URL=http://localhost:8123 API_TIMEOUT_MS=3600000 claude
```

The paused-flow header in the UI surfaces this incantation as a one-line reminder next to the elapsed timer. It is informational only. The workbench has no knowledge of the client's configured value and does not attempt to display a countdown or a deadline. The operator is responsible for setting `API_TIMEOUT_MS` to match the editing envelope they need.

### V2 unlock: response breakpoints

Response breakpoints were deferred in V1 because holding the full SSE stream risks client timeout. With `API_TIMEOUT_MS` raised on the client, that constraint relaxes. Response breakpoints become viable in V2 given:

- The operator remembers to raise `API_TIMEOUT_MS` at launch
- SSE stream buffering that mitmproxy already handles by default
- Keepalive considerations still to verify before shipping

## Defensive coding

The schema is small but has variants. Every section renderer must handle these without dropping data:

- System parts with and without `cache_control`
- User content that is a string or a list of blocks
- Empty `thinking` blocks (zero-length strings)
- `tool_result` content that is a string or a list of blocks
- New top-level fields added by Anthropic in the future

Any unknown top-level key falls through to the advanced raw-JSON section. Any unknown content block type renders with a `<details>` showing its raw JSON and a strip toggle.

## Build phases

Each phase is independently testable. Phase 2 is usable standalone before phase 3 lands.

1. **Persistence layer**: `~/.claude/logs/proxy/` with `index.jsonl` and `exchanges/{flow_id}/`. Drop the `/tmp/*` writes from the current addon. Extend the capture to cover response raw bodies.
2. **Embedded HTTP server + static page + SSE live log**: starlette + uvicorn inside the addon. Web UI shows the log list and a read-only detail view. No breakpoint yet. Phase 2 ships a useful viewer.
3. **Breakpoint mechanism**: armed-once mode, `asyncio.Event` pause, release endpoint, schema-aware editor in the UI, Forward and Forward Unmodified buttons.

## Deferred to V2 and beyond

- Response breakpoints with careful client-timeout handling
- Filter rules for conditional pausing
- Drop button with canned response
- Log rotation and retention
- Diff view against the original payload inside the editor
- Per-tool truncate-description bulk action
- Parsed `<system-reminder>` handling with per-reminder toggles
- Saved mutation recipes, applicable to new flows with one click
- Replay: re-send a historical exchange, optionally with edits
- Cross-exchange search across `index.jsonl`

## Related

- `/Users/alphab/.claude/scripts/capture_claude_request.py` (current addon, pre-workbench)
- CLAUDE.md Helioy ecosystem row: this project slots alongside helioy-bus and fmm as tooling infrastructure
