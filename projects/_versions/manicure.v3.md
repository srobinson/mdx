---
title: Manicure
type: projects
tags: [manicure, claude-code, codex, mitmproxy, proxy, developer-tools, breakpoint, workbench, helioy, context-engineering, open-source]
summary: Provider-neutral context control plane for coding agents. mitmproxy-resident inspector, rule pipeline, and breakpoint editor for /v1/messages traffic, with an internal IR and pluggable adapters
status: active
project: manicure
confidence: high
created: 2026-04-10
updated: 2026-04-10
---

# Manicure

> **mani**fest + **cur**at**e**. Care for the cargo your coding agent carries.

## TL;DR

A provider-neutral context control plane for coding agents. Sits as a reverse proxy in front of Claude (V1) and Codex (V2), captures every `/v1/messages` exchange to disk, normalizes payloads into an internal representation, runs them through a deterministic curation pipeline, optionally pauses for manual edits in a schema-aware editor, then reserializes and forwards. Burp Repeater meets a context optimizer, with a stable internal schema so adapters can grow without rewriting the core.

## Strategic framing

Three commitments shape every other decision in this document.

1. **Product as a context control plane.** The workbench is not a passive viewer with an editor bolted on. It is a pipeline that subtracts, rewrites, and (later) adds context, with a UI that exposes the pipeline's effects. Manual breakpoint editing is one input to the pipeline among several. Curation rules are first-class from V1.

2. **Workbench as a Helioy integration surface.** The same hook point that strips tools can also retrieve relevant memory from `attention-matters`, inject `markdown-matters` snippets, or call `context-matters` for prior decisions. V1 ships zero Helioy integrations, but the architecture leaves the seam open. V2 wires them in. This is the long-term reason to build the workbench instead of a one-off mitmproxy script.

3. **Provider-neutral from day one.** Anthropic schema details are confined to an adapter. The pipeline, the editor, the persistence layer, and the rule engine all operate on an internal representation. When OpenAI's Codex CLI exposes an equivalent base URL, a second adapter slots in without touching the core. The internal schema is the contract; adapters are the translators.

## Motivation

1. **Visibility**: see exactly what Claude Code (or any client) is sending. The captured payload is the ground truth for debugging context bloat, unexpected tool inclusions, and prompt drift.
2. **Experimentation**: strip tools, shorten system prompts, drop old tool_results, then forward and observe how the model responds with less context. The fastest path to empirical context engineering.
3. **Curation**: persistent rules apply the same edit to every subsequent request. Edit once, never re-edit. The workbench remembers.
4. **Helioy hook**: every request flowing through the workbench is a chance to retrieve, augment, or annotate. The pipeline is the integration seam.
5. **Portability**: one workbench for every coding agent that exposes an HTTPS base URL. Claude today, Codex tomorrow, anything else after that.

## Quick start

Copy, paste, run. No cert install, no sudo, no system proxy settings, no TLS interception.

```bash
# 1. Install
curl -fsSL https://manicure.sh/install.sh | bash
```

```bash
# 2. Start the workbench (blocking, keep this terminal open)
manicure start
```

```bash
# 3. In another terminal, launch Claude Code pointed at the workbench
ANTHROPIC_BASE_URL=http://localhost:8123 claude
```

Open the web UI at `http://localhost:8787`. Every `/v1/messages` request from Claude Code now routes through the workbench, gets normalized to the internal schema, runs through the rule pipeline, and appears in the live log. Arm the breakpoint to pause the next request for manual editing on top of the pipeline output.

### What the install script does

Single-file shell installer, the same pattern as `rustup`, `bun`, `uv`, `ollama`, `fly`, and every other modern dev tool. The script:

1. Detects the host OS and architecture
2. Ensures a Python toolchain is available (uses `uv` if present, otherwise bootstraps it)
3. Installs `manicure` and its dependencies (mitmproxy, starlette, uvicorn) into an isolated environment
4. Symlinks the `manicure` binary into `~/.local/bin` (or the OS-appropriate location)
5. Prints next-step instructions pointing at `manicure start`

The user sees a one-liner. Everything else is hidden.

### What `manicure start` runs

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
- Internal representation (IR) with a single Anthropic adapter, lossless round-trip invariant
- Deterministic rule pipeline with six curation actions
- Persistent rule storage scoped by `session_id`, `device_id`, `account_id`, `model`, or global
- Persistent on-disk log viewable via a web UI
- Live-updating log list via Server-Sent Events
- Request-only breakpoint: pause after pipeline, edit, release
- Schema-aware editor over the IR (not the raw Anthropic schema)
- Rules UI: list, create, enable/disable, delete, view audit trail
- Global toggle + armed-once mode for the breakpoint
- Token and character accounting, visible live during edits

**Explicit non-goals (V1)**
- A second adapter (Codex/OpenAI ships in V2)
- Any Helioy integration (V2)
- Response breakpoints (mitmproxy buffers the full SSE stream; holding it too long causes client timeouts)
- Conditional pause rules (pause-when-model-equals, pause-when-tool-present)
- Drop and canned-response button
- Retention policy or log rotation
- Diff view against the original
- Replay of historical exchanges
- JSON Schema validation (the upstream server validates)
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

A flat 147-row checkbox list is unusable. Tool grouping by prefix is mandatory, not optional. Tools at 67% of the payload also explain why `strip_tools` is the headline pipeline action.

## Internal schema (IR)

The IR is the contract between the proxy boundary and everything inside the workbench. Adapters translate raw provider payloads into the IR on the way in, and back out on the way out. The pipeline, the editor, the persistence layer, and the rule engine all operate on the IR exclusively. Nothing inside the core touches an Anthropic-shaped dict.

Why this matters: when Anthropic adds a field, the change is contained in `AnthropicAdapter`. When we add a Codex adapter, the pipeline does not move. The editor does not move. The rules do not move. The IR is the invariant, the adapters are the variants.

### InternalRequest shape

```
InternalRequest {
  model: string                    # provider-qualified name, e.g. "anthropic/claude-opus-4-6"
  provider: string                 # "anthropic" | "openai" | ...
  system: [
    {
      type: "text",
      text: string,
      cache_hint?: object,         # adapter-opaque, preserved on round-trip
      provider_data?: object       # adapter-opaque, preserved on round-trip
    }
  ]
  tools: [
    {
      name: string,
      description: string,
      input_schema: object,
      provider_data?: object
    }
  ]
  messages: [
    {
      role: "user" | "assistant" | "tool",
      content: [
        { type: "text", text },
        { type: "tool_use", id, name, input },
        { type: "tool_result", tool_use_id, content, is_error? },
        { type: "thinking", text, provider_data? },
        { type: "image", source },
        { type: "unknown", raw }     # last-resort container, never lossy
      ]
    }
  ]
  sampling: {
    max_tokens, temperature, top_p, top_k, stop_sequences
  }
  metadata: {
    session_id?, device_id?, account_id?,
    provider_metadata: object        # adapter-specific, opaque to core
  }
  stream: bool
  provider_extras: object            # catch-all for provider-only top-level fields
}
```

`session_id`, `device_id`, and `account_id` are pulled from Anthropic's `metadata.user_id` (which is itself a JSON-encoded string containing those keys). The adapter does the unpacking. The rule engine uses these fields directly for scoping.

### Lossless round-trip invariant

For any raw provider request `R`, the following must hold:

```
adapter.outbound_request(adapter.inbound_request(R)) === R
```

Byte-for-byte identical, modulo whitespace normalization. This is the adapter correctness contract. A round-trip test runs against every captured fixture in CI. If the round-trip fails for any field, the adapter is broken, not the IR. The fix is either to extend the IR or to widen `provider_data` / `provider_extras` to carry the field opaquely.

This invariant is what lets us insert the pipeline in the middle without breaking anything. A no-op pipeline is a no-op end to end.

### InternalResponse shape

Mirror image. Captures the model output side and supports response streaming reassembly without ever leaking provider-specific event names into the core.

```
InternalResponse {
  id: string
  model: string
  provider: string
  stop_reason: string | null
  usage: { input_tokens, output_tokens, cache_read_input_tokens, ... }
  content: [
    { type: "text", text },
    { type: "tool_use", id, name, input },
    { type: "thinking", text },
    { type: "unknown", raw }
  ]
  provider_extras: object
}
```

V1 only writes the response IR to disk. V2 unlocks response-side rules (e.g. inject memory hits, rewrite tool_use arguments).

## Adapter layer

```
adapters/
  __init__.py         # registry
  base.py             # ProviderAdapter ABC
  anthropic.py        # V1
  openai.py           # V2 (Codex)
```

### ProviderAdapter ABC

```python
class ProviderAdapter(ABC):
    name: str

    @abstractmethod
    def matches(self, flow) -> bool:
        """Return True if this adapter handles the given mitmproxy flow.
        Typically checks request path and host."""

    @abstractmethod
    def inbound_request(self, raw_body: bytes) -> InternalRequest:
        """Parse a raw provider request body into the IR."""

    @abstractmethod
    def outbound_request(self, ir: InternalRequest) -> bytes:
        """Serialize the IR back into a raw provider request body."""

    @abstractmethod
    def inbound_response(self, raw_body: bytes, content_type: str) -> InternalResponse:
        """Parse a raw provider response body (JSON or SSE) into the IR."""

    # outbound_response is V2; V1 does not mutate responses
```

### Adapter registry

A small registry holds all installed adapters. On every request, the registry walks adapters in order and picks the first one whose `matches(flow)` returns `True`. If none match, the workbench falls through to a passthrough mode that captures the raw body but skips the pipeline.

V1 ships only `AnthropicAdapter`. V2 adds `OpenAIAdapter` for Codex's `/v1/responses` endpoint. The dispatch logic does not change; only the registry list grows.

## Pipeline engine

The pipeline is what makes this a control plane and not just a viewer.

```
adapter.inbound_request(raw)
  → InternalRequest
  → pipeline.apply(rules)            # deterministic, ordered, idempotent
  → InternalRequest'                  # transformed
  → breakpoint.maybe_pause()          # optional manual layer on top
  → InternalRequest''                 # possibly mutated by editor
  → adapter.outbound_request(ir'')
  → forward to provider
```

The editor sees `InternalRequest'`, which is the post-pipeline body. Manual edits compose with the pipeline by layering on top, never by replacing it.

### Transform contract

Every rule action is a pure function `(InternalRequest, params) -> InternalRequest`. No I/O, no state outside its inputs. No mutation of the input object; return a new IR. This makes the pipeline trivially testable and trivially auditable.

Three properties every action must satisfy:

1. **Deterministic**: same input, same params, same output. Always.
2. **Idempotent**: applying the action twice produces the same result as applying it once.
3. **Loss-explicit**: any data the action removes is summarized in the audit trail (e.g. "stripped 37 tools matching prefix `mcp__plugin_helioy-tools_linear-server`").

### V1 rule vocabulary (six actions)

All subtractive or rewriting. No additive actions in V1; those land in V2 with the Helioy hook.

| Action | Params | Effect |
|---|---|---|
| `strip_tools` | `{ name?, prefix?, regex? }` | Remove tools matching any of the predicates. The headline operation. |
| `strip_thinking` | `true` | Drop every `thinking` block from the request. |
| `strip_system_part` | `{ index: N }` | Remove a specific `system[N]` part. |
| `truncate_system_part` | `{ index: N, max_chars: M }` | Truncate `system[N].text` to `M` chars with a `[truncated]` marker. |
| `truncate_tool_result` | `{ older_than_turns?: N, max_chars?: M }` | Truncate `tool_result` content blocks. Either by age (turns from end) or by size, or both. |
| `rewrite_tool_description` | `{ name, new: "..." }` | Replace a tool's `description` field. Useful for dropping the 30 KB Agent description down to its first sentence. |

This vocabulary covers the high-leverage cases visible in the real-world data: 67% tool bloat (`strip_tools`), 27.5 KB system part (`strip_system_part` / `truncate_system_part`), the Agent tool description (`rewrite_tool_description`), thinking accumulation (`strip_thinking`), and stale tool results (`truncate_tool_result`).

### Rule storage

```json
{
  "id": "rule_01H...",
  "name": "Strip Linear MCP",
  "enabled": true,
  "scope": {
    "global": false,
    "session_id": null,
    "device_id": "abc...",
    "account_id": null,
    "model": null
  },
  "action": "strip_tools",
  "params": { "prefix": "mcp__plugin_helioy-tools_linear-server" },
  "created_at": "2026-04-10T14:23:45Z",
  "applied_count": 142
}
```

Stored in `~/.claude/logs/proxy/rules.json`. Single file, atomic writes. No database in V1.

### Rule scoping

Five scope dimensions, in increasing specificity:

1. `global`: applies to every request
2. `model`: applies when `request.model` matches
3. `account_id`: applies when the request is from a given Claude account
4. `device_id`: applies when the request is from a given device
5. `session_id`: applies only to a single Claude Code session

Multiple scope dimensions on the same rule are AND'd. For each request, the engine collects every enabled rule whose scope matches, then applies them in deterministic order (by `created_at`).

The scoping data comes from the IR's `metadata` block, which the Anthropic adapter populates by unpacking `metadata.user_id`. The pipeline never reaches into provider-shaped data.

### Rule UI

A second tab in the web UI alongside the live log:

- List view: every rule, scope chips, enable/disable toggle, applied count, delete button
- "Create rule from this exchange" affordance on every captured exchange. Pre-fills the action and params from what the operator just stripped manually in the editor. Promotes a one-off edit to a persistent rule with one click.
- Audit trail per exchange: which rules fired, what they removed, byte/token deltas

### Audit trail

Every exchange's `index.jsonl` line carries a `pipeline` block:

```json
"pipeline": {
  "rules_applied": [
    {"id": "rule_01H...", "name": "Strip Linear MCP", "removed": {"tools": 37, "chars": 48231}},
    {"id": "rule_01J...", "name": "Drop thinking", "removed": {"blocks": 4, "chars": 12044}}
  ],
  "delta": {"chars": -60275, "tokens_approx": -15068}
}
```

This makes the workbench's effect on every request quantifiable and reviewable.

## Stack (locked)

| Layer | Choice | Rationale |
|---|---|---|
| Proxy | mitmproxy, **reverse proxy mode** (`--mode reverse:https://api.anthropic.com`) | No TLS between the client and the proxy. No root CA install. Reverse proxy is what makes the install one line. |
| Adapter layer | Pluggable `ProviderAdapter` ABC + registry | Provider-specific JSON shapes are confined here. Core operates on IR only. |
| Internal IR | Plain Python dataclasses, no validation library in V1 | The lossless round-trip test in CI is the validator. |
| Pipeline | Pure-function actions, deterministic ordering | Trivially testable, trivially auditable. Rules are data, not code. |
| Backend | starlette + uvicorn | Runs inside mitmproxy's asyncio loop. Scales. One process, zero IPC, shared asyncio state. |
| Persistence | Append-only `index.jsonl` + per-exchange directories + `rules.json` | Safe concurrent writes, cheap tail for SSE, lazy-loaded detail. |
| Frontend | Vanilla JS SPA | No framework. Custom schema-aware editor over the IR, no generic JSON tree library. |
| Transport | HTTP + SSE | One-way server push for live log and paused-flow events. POST for mutation + release. No WebSocket in V1. |
| Bind | `localhost:8123` (reverse proxy) + `localhost:8787` (web UI) | Two distinct ports on localhost. Both bind to loopback only; no auth in V1. |

### Why not a generic JSON tree editor

`vanilla-jsoneditor` was the community-consensus pick in research. It would have worked. The custom editor is a better fit because:

1. The IR is small and stable. Five top-level fields account for 99% of what anyone would edit.
2. The operations that matter (strip tool, strip system part, truncate tool_result, edit last user message) are domain-specific and benefit from dedicated UI over generic key/value editing.
3. Schema-aware rendering shows what you care about at a glance. A generic tree makes you hunt through `messages[4].content[2].text`.
4. Bundle size: under 20 KB of vanilla JS vs 300-500 KB.
5. The editor renders the IR, not the Anthropic schema. The same editor works for every adapter.

Fallback: any IR field the editor does not recognize renders as a raw JSON textarea. Nothing gets silently dropped.

## Directory layout

### Scripts

```
~/.claude/scripts/claude-proxy/
  addon.py              # mitmproxy entry: request/response hooks
  ir.py                 # InternalRequest, InternalResponse dataclasses
  adapters/
    __init__.py         # registry
    base.py             # ProviderAdapter ABC
    anthropic.py        # V1
  pipeline.py           # apply(rules, ir) -> ir', audit
  rules.py              # storage, scope matching, action implementations
  persistence.py        # index.jsonl writer, exchange dir writer
  breakpoint.py         # state machine: mode, paused flow registry
  server.py             # starlette app, uvicorn startup from addon load()
  routes.py             # /api/* handlers, static mount
  web/
    index.html
    app.js
    app.css
```

### Logs and rules

```
~/.claude/logs/proxy/
  index.jsonl                      # append-only, one line per exchange
  rules.json                       # all curation rules, single file
  exchanges/
    {iso_ts}-{flow_id}/
      request.raw                  # raw provider body
      request.ir.json              # post-adapter, pre-pipeline IR
      request.curated.ir.json      # post-pipeline IR (the body actually sent)
      response.raw                 # raw provider body (SSE or JSON)
      response.ir.json             # post-adapter IR
```

`index.jsonl` schema, one line per exchange:

```json
{
  "id": "<mitmproxy flow.id>",
  "ts": "<iso8601>",
  "provider": "anthropic",
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
  "pipeline": {
    "rules_applied": [
      {"id": "rule_01H...", "name": "Strip Linear MCP", "removed": {"tools": 37, "chars": 48231}}
    ],
    "delta": {"chars": -48231, "tokens_approx": -12057}
  },
  "res": {
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 59177, "output_tokens": 892, "cache_read_input_tokens": 0},
    "text_chars": 3456,
    "tool_calls": [{"name": "Read", "id": "toolu_..."}]
  },
  "mutated_manually": false
}
```

## Components

1. **Capture addon** (`addon.py`): mitmproxy `request()` and `response()` hooks. Dispatches to the adapter registry, runs the pipeline, consults breakpoint state, awaits the release event when paused. Registers a `done()` hook to release any still-paused flows at shutdown with an error response.
2. **Adapter registry** (`adapters/`): walks installed adapters, returns the first match. Provider-shaped JSON ends here.
3. **Pipeline engine** (`pipeline.py`): pure-function rule application over the IR. Returns the transformed IR plus an audit record.
4. **Rule engine** (`rules.py`): storage, scope matching, action implementations. The actions are the only code that knows what `strip_tools` means.
5. **Persistence** (`persistence.py`): atomic append to `index.jsonl` (one write per exchange, line-buffered). Per-exchange directory creation. Schema-versioned. Writes both raw and IR forms of every exchange.
6. **Breakpoint manager** (`breakpoint.py`): holds `{flow_id: PausedFlow}` registry, where `PausedFlow` carries the `flow`, an `asyncio.Event`, the curated IR, and `paused_at_ms`. Tracks mode (`off`, `armed_once`).
7. **HTTP server** (`server.py`): starlette app wrapped in `uvicorn.Server`, started from the addon's `load()` hook as a background task on the mitmproxy event loop.
8. **Web UI** (`web/`): single-page app with two tabs: live log and rules. Detail view of any exchange shows raw, post-pipeline IR, and audit trail.

## API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Static SPA |
| GET | `/api/exchanges` | Paginated index (reads tail of `index.jsonl`) |
| GET | `/api/exchanges/{id}` | Full exchange: raw, post-pipeline IR, audit |
| GET | `/api/stream` | SSE: `exchange` events (new log entries) and `paused` events (flow waiting for release) |
| POST | `/api/breakpoint/arm` | Set mode to `armed_once` |
| POST | `/api/breakpoint/disarm` | Set mode to `off` |
| POST | `/api/release/{flow_id}` | Body: mutated IR. Applies mutation and releases the flow. |
| GET | `/api/rules` | List all rules |
| POST | `/api/rules` | Create a new rule |
| PATCH | `/api/rules/{id}` | Update fields (typically `enabled`) |
| DELETE | `/api/rules/{id}` | Delete a rule |
| POST | `/api/rules/from-exchange/{id}` | Promote a manual edit on an exchange to a persistent rule |

## Event flows

**Normal request**:

```
client → mitmproxy → request()
         → adapter = registry.match(flow)
         → ir = adapter.inbound_request(raw)
         → ir', audit = pipeline.apply(rules, ir)
         → persistence.write_request(raw, ir, ir', audit)
         → breakpoint.is_armed() == False
         → flow.request.set_text(adapter.outbound_request(ir'))
         → forward to provider
         → response()
         → ir_resp = adapter.inbound_response(raw, content_type)
         → persistence.write_response(raw, ir_resp)
         → server.sse_emit({type: "exchange", ...})
         → client receives response
```

**Armed-once request**:

```
client → mitmproxy → request()
         → adapter = registry.match(flow)
         → ir = adapter.inbound_request(raw)
         → ir', audit = pipeline.apply(rules, ir)
         → persistence.write_request(raw, ir, ir', audit)
         → breakpoint.is_armed() == True
         → breakpoint.disarm()
         → evt = asyncio.Event()
         → paused_at_ms = now_ms()
         → paused[flow.id] = PausedFlow(flow, evt, ir', paused_at_ms)
         → server.sse_emit({type: "paused", flow_id, ir', audit, paused_at_ms})
         → await evt.wait()                     [flow blocked here]

[UI displays editor over ir']
[user edits IR tree]
[user clicks Forward]

POST /api/release/{flow.id}
body: mutated IR
         → flow.request.set_text(adapter.outbound_request(mutated_ir))
         → evt.set()
         → forward to provider
         → response()
         → persistence.write_response(raw, ir_resp)  (mutated_manually=true)
         → server.sse_emit({type: "exchange", ...})
         → client receives response
```

The pipeline runs *before* the breakpoint check. The editor always shows post-pipeline state. Manual edits layer on top of curation, never around it.

## Schema-aware editor sections

The editor renders the IR, not the Anthropic schema. Every section below operates on `InternalRequest` fields. When a second adapter lands, the editor does not change.

### model and sampling params

Simple form controls at the top of the editor.

- `model`: dropdown (free-text override available)
- `sampling.max_tokens`: number input
- `stream`: readonly checkbox (always true in practice)
- `messages` advanced row toggles (collapsed)
- `provider_extras` collapsed advanced row

### system

A card per part. Card header shows index, type, size, and the first line of content as a preview.

- Checkbox on the card: strip on unchecked
- Click card to expand into an inline textarea for edit
- Any part over 500 chars stays collapsed by default
- `cache_hint` markers are displayed as badges but not editable in V1

### tools

The most important section of the workbench. Prefix-grouped, collapsible.

- Global bulk bar: `[all] [none] [drop all MCP]`
- One group per prefix, header shows group name, count, total size
- Group-level bulk bar: `[all] [none]`
- Inside each group, one row per tool with: checkbox, name, size, description tooltip
- Bare tools group labeled `Built-in`, shown with de-prefixed names
- Rows sorted within group by size descending (biggest, most strippable tools at the top)
- Per-row "promote to rule" affordance: turns the manual strip into a `strip_tools` rule

### messages

Turn-by-turn cards. Each turn header shows index, role, summary of content blocks.

Inside a turn, iterate `content` blocks (always a list). Per block type:

- `text`: inline edit, character count, strip toggle
- `tool_use`: show `name` and `id`, input summary in a collapsed `<details>`, strip toggle
- `tool_result`: show size, is_error badge, actions `[edit | truncate | drop]`
- `thinking`: size, strip toggle; a global bulk action exists to strip all thinking blocks at once

System-reminders inside user text blocks are treated as plain text in V1. A later revision can parse `<system-reminder>…</system-reminder>` markers and offer per-reminder toggles.

### advanced

Collapsed section at the bottom containing `metadata`, `provider_extras`, and anything else not recognized. Raw JSON textarea.

### audit panel

Always visible at the side of the editor. Shows the rules that fired during pipeline application:

- Rule name, what it removed, byte/token delta
- Click a rule to see the before/after for that specific transform
- A toggle to view the original (pre-pipeline) IR

This is the feedback loop that makes the curation pipeline trustworthy.

### paused-flow header

Shown at the top of the editor whenever a flow is paused. Contains:

- Short flow id (first 8 chars of `flow.id`)
- Provider and model name
- **Elapsed timer**: time since the flow was paused. Format `MM:SS`, or `HH:MM:SS` when over an hour. Computed client-side as `now() - paused_at_ms` using the `paused_at_ms` from the SSE event, refreshed every second from a local `setInterval`. Counts up, never down. The workbench does not know the client's timeout and does not try to guess it.
- **Informational line** next to the timer, always visible: `Client timeout is set by API_TIMEOUT_MS on the Claude Code side (default 10m). Raise it at launch: API_TIMEOUT_MS=3600000 claude`. Pure guidance so the operator knows how to give themselves a longer editing window before arming the next breakpoint.

### footer

Always visible. Shows:

- Pre-pipeline size: chars and approximate tokens
- Post-pipeline size: chars and approximate tokens, plus delta percentage
- Post-edit size: chars and approximate tokens, plus delta from post-pipeline
- Buttons: `[ Forward ]`, `[ Forward Unmodified ]`, `[ Drop ]`

The cumulative delta (original → curated → edited) is the live signal that makes this feel like a workbench.

## Design notes worth locking

- **Pipeline ordering**: rules apply in deterministic `created_at` order. Same exchange + same rule set always produces the same output. No ML, no surprises.
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

The IR is small but has variants. Every section renderer must handle these without dropping data:

- System parts with and without `cache_hint`
- User content that is a string or a list of blocks (the adapter normalizes to list-of-blocks; the editor sees only lists)
- Empty `thinking` blocks (zero-length strings)
- `tool_result` content that is a string or a list of blocks
- `unknown` content blocks: always render with a raw `<details>` and a strip toggle
- New top-level fields added by Anthropic in the future: caught by the round-trip test, surfaced in `provider_extras`

Any unknown IR top-level key falls through to the advanced raw-JSON section. Any unknown content block type renders with a `<details>` showing its raw JSON and a strip toggle. The lossless round-trip invariant is the safety net behind all of this.

## Distribution and licensing

### License

Apache 2.0. The license sends a clear infrastructure signal (patent grant, enterprise-friendly), matches the dev tools the workbench imitates (`uv`, `bun`, `mitmproxy`), and gives the project room to grow without painful relicensing later. Permissive enough to encourage forks; explicit enough to protect contributors.

### Repository

Public on GitHub from day one. Repo name: `manicure`. Owner is the operator's personal account at launch; promote to a dedicated org if traction justifies. Standard OSS metadata files: `LICENSE`, `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`. Distribution channels: pypi (`pip install manicure`), the curl-pipe install script at `manicure.sh`, and Homebrew tap once V1 is stable. CI runs the lossless round-trip test against a fixture corpus of real captured payloads.

### Maintenance stance

Maintain conditional on traction. The bar is whether the project crosses a meaningful adoption threshold: GitHub stars, install counts, organic issue/PR flow, and most importantly whether anyone is using it as critical infrastructure. Below the threshold, archive with a clear note that forks are welcome. Above the threshold, treat as a long-running project with proper release cadence and roadmap.

The architecture is designed to lower the maintenance cost in either direction. Adapters are isolated. Rules are data. The IR is the contract. A drive-by contributor can add an adapter or a rule action without learning the rest of the system.

### Launch

A coordinated launch is part of V1, not an afterthought:

- Demo gif, 60 seconds, showing the live log fill, the editor stripping 100 KB of MCP tools, and the post-strip request succeeding
- Blog post on a personal domain explaining the motivation, the IR, and the curation pipeline
- Hacker News submission timed to a weekday morning Pacific time
- X / Reddit (`r/LocalLLaMA`, `r/ClaudeAI`) cross-posts pointing to the blog post
- Direct outreach to a small number of practitioners building on Claude Code

### Naming

**Manicure.** Five reinforcing layers, every reading points at the product:

1. **Portmanteau**: **mani**fest + **cur**at**e**. The two words that describe what the pipeline does, contracted into one. The aviation term "manifest" already lives in the surrounding vocabulary stack (preflight, flight log, hold short, clearance). The verb "curate" already names the rule engine.
2. **Wordplay**: contains *cure*. The workbench is the cure for context bloat.
3. **Etymology**: Latin *manus + cura* = hand + care. Literally "hand-care", which is exactly what the breakpoint editor is — the human-in-the-loop seam on top of the automated pipeline.
4. **Surface metaphor**: a manicure trims back overgrowth while preserving and shaping what remains. Loss-explicit, never destructive. Matches the V1 transform contract.
5. **Distinctiveness**: zero collision in the dev-tool space. Searchable, ownable, screenshot-friendly.

**Identity surfaces (locked at spec time)**:

| Surface | Slug | Notes |
|---|---|---|
| pypi | `manicure` | Clean, no prior package |
| crates.io | `manicure` | Reserved for any future Rust port |
| Domain | `manicure.sh` | Available (RDAP-verified); the `.sh` TLD reads as "shell", matching the curl-pipe install vector. Dev-tool pattern: `bun.sh`, `fly.sh` |
| GitHub | `<owner>/manicure` | Org name `manicure` is squatted by an inactive 2017 user account; repo on a personal/org account is fine |
| CLI binary | `manicure` | Installed by the curl-pipe script |

**Backup domains** (RDAP-verified available at spec time): `manicure.tools`, `manicure.app`, `manicure.run`. Note: `manicure.dev` is **taken** (registered 2023-07-19, active hold); do not use.

**Soft collisions documented**: an abandoned npm package `manicure` (S3 thumbnail glue, last touched 2022) — irrelevant since the tool ships via pypi, not npm. The github user `manicure` is an inactive 2017 squat — accept that the bare org name is unavailable and use the repo name on a different account.

**Tagline candidates**:
- "Manicure your prompts."
- "Care for the cargo your coding agent carries."
- "Manifest curate."

## Build phases

Each phase is independently testable. Phase 2 is usable standalone before phase 3 lands.

1. **Persistence + IR + Anthropic adapter**: `~/.claude/logs/proxy/` with `index.jsonl` and `exchanges/{flow_id}/`. The IR dataclasses, the adapter ABC, the Anthropic adapter, and the lossless round-trip test in CI. Drop the `/tmp/*` writes from the current addon.
2. **Embedded HTTP server + static page + SSE live log**: starlette + uvicorn inside the addon. Web UI shows the log list and a read-only detail view rendering the IR. No pipeline yet, no breakpoint yet. Phase 2 ships a useful viewer.
3. **Pipeline engine + rule engine + rules UI**: the six V1 actions, scope matching, persistent rule storage, audit trail, rules tab in the UI. After phase 3 the workbench can curate without ever touching the breakpoint.
4. **Breakpoint mechanism + schema-aware editor**: armed-once mode, `asyncio.Event` pause, release endpoint, schema-aware editor over the IR, "promote to rule" flow, Forward and Forward Unmodified buttons.

## Deferred to V2 and beyond

- **OpenAI / Codex adapter**: slot in alongside `AnthropicAdapter`, reuse the entire pipeline and editor unchanged
- **Helioy integration hooks**: additive pipeline actions calling `attention-matters`, `markdown-matters`, `context-matters` for retrieval and augmentation
- **Response breakpoints** with careful client-timeout handling
- **Response-side rules** (rewrite tool_use args, inject memory hits)
- **Filter rules** for conditional pausing (pause-when-model-equals, pause-when-tool-present)
- **Drop button** with canned response
- **Log rotation and retention**
- **Diff view** against the original payload inside the editor
- **Replay**: re-send a historical exchange, optionally with edits
- **Cross-exchange search** across `index.jsonl`
- **Template substitution**: parameterized rules (e.g. inject the current git branch into a system part)
- **Parsed `<system-reminder>` handling** with per-reminder toggles
- **Saved mutation recipes** beyond simple rules: multi-step workflows applied with one click

## Related

- `/Users/alphab/.claude/scripts/capture_claude_request.py` (current addon, pre-workbench)
- `~/.mdx/projects/_versions/manicure.v1.md` (earlier spec, pre-IR architecture)
- `~/.mdx/projects/_versions/manicure.v2.md` (this spec, V2 — IR + adapters + pipeline, pre-rename from `claude-api-workbench`)
- CLAUDE.md Helioy ecosystem row: this project slots alongside `helioy-bus` and `fmm` as tooling infrastructure, with V2 hooks into `attention-matters`, `markdown-matters`, and `context-matters`
