---
title: Manicure Technical Spec
type: projects
tags: [manicure, technical-spec, ir, pipeline, mitmproxy, fastapi, react]
summary: Technical architecture for Manicure. IR schema, adapter layer, pipeline engine, storage, API surface, editor sections, build phases.
status: active
project: manicure
confidence: high
created: 2026-04-10
updated: 2026-04-10
---

# Manicure Technical Spec

See `~/.mdx/projects/manicure.md` for project definition, motivation, and scope.

## Stack

| Layer | Choice |
|---|---|
| Proxy | mitmproxy, reverse proxy mode (`--mode reverse:https://api.anthropic.com`) |
| Adapter layer | Pluggable `ProviderAdapter` ABC + registry |
| Internal IR | Pydantic models |
| Pipeline | Pure-function actions, deterministic ordering |
| Backend | FastAPI + uvicorn, embedded in mitmproxy's asyncio loop. Pydantic request/response validation, OpenAPI spec, `Depends()` for storage injection. Single process, zero IPC, shared asyncio state. |
| Storage | Adapter pattern. `StorageBackend` ABC with disk as the default implementation. Injected via FastAPI `Depends()`. |
| Frontend | Vite + React SPA. Custom schema-aware editor components over the IR. |
| Transport | HTTP + SSE |
| Bind | `localhost:8787` (reverse proxy) + `localhost:8788` (web UI) |

## Internal schema (IR)

The IR is the contract between the proxy boundary and everything inside the workbench. Adapters translate raw provider payloads into the IR on the way in, and back out on the way out. The pipeline, the editor, the persistence layer, and the rule engine all operate on the IR exclusively. Nothing inside the core touches a provider-shaped dict.

When Anthropic adds a field, the change is contained in `AnthropicAdapter`. When we add a Codex adapter, the pipeline, editor, and rules do not move.

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

### InternalResponse shape

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

V1 only writes the response IR to disk. V2 unlocks response-side rules.

### Lossless round-trip invariant

For any raw provider request `R`:

```
adapter.outbound_request(adapter.inbound_request(R)) === R
```

Byte-for-byte identical, modulo whitespace normalization. This is the adapter correctness contract. A round-trip test runs against every captured fixture in CI. If the round-trip fails for any field, the adapter is broken, not the IR. The fix is either to extend the IR or to widen `provider_data` / `provider_extras` to carry the field opaquely.

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
        """Return True if this adapter handles the given mitmproxy flow."""

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

Walks installed adapters in order, picks the first whose `matches(flow)` returns `True`. If none match, falls through to passthrough mode: captures the raw body but skips the pipeline.

V1 ships only `AnthropicAdapter`. V2 adds `OpenAIAdapter` for Codex's `/v1/responses` endpoint.

## Storage layer

```python
class StorageBackend(ABC):
    @abstractmethod
    async def append_index(self, entry: IndexEntry) -> None: ...

    @abstractmethod
    async def write_exchange(self, exchange_id: str, artifacts: ExchangeArtifacts) -> None: ...

    @abstractmethod
    async def read_index(self, limit: int, offset: int) -> list[IndexEntry]: ...

    @abstractmethod
    async def read_exchange(self, exchange_id: str) -> ExchangeArtifacts: ...

    @abstractmethod
    async def load_rules(self) -> list[Rule]: ...

    @abstractmethod
    async def save_rules(self, rules: list[Rule]) -> None: ...
```

Default implementation: `DiskStorageBackend`. Writes `index.jsonl` (append-only, line-buffered), per-exchange directories, and `rules.json`. Injected into route handlers via FastAPI `Depends(get_storage)`.

## Pipeline engine

```
adapter.inbound_request(raw)
  -> InternalRequest
  -> pipeline.apply(rules)            # deterministic, ordered, idempotent
  -> InternalRequest'                  # transformed
  -> breakpoint.maybe_pause()          # optional manual layer on top
  -> InternalRequest''                 # possibly mutated by editor
  -> adapter.outbound_request(ir'')
  -> forward to provider
```

The editor sees `InternalRequest'` (post-pipeline). Manual edits compose with the pipeline by layering on top, never by replacing it.

### Transform contract

Every rule action is a pure function `(InternalRequest, params) -> InternalRequest`. No I/O, no state outside its inputs. No mutation of the input object; return a new IR.

Three properties every action must satisfy:

1. **Deterministic**: same input, same params, same output. Always.
2. **Idempotent**: applying the action twice produces the same result as once.
3. **Loss-explicit**: any data the action removes is summarized in the audit trail.

### V1 rule vocabulary (six actions)

All subtractive or rewriting. No additive actions in V1; those land in V2 with the Helioy hook.

| Action | Params | Effect |
|---|---|---|
| `strip_tools` | `{ name?, prefix?, regex? }` | Remove tools matching any of the predicates. |
| `strip_thinking` | `true` | Drop every `thinking` block from the request. |
| `strip_system_part` | `{ index: N }` | Remove a specific `system[N]` part. |
| `truncate_system_part` | `{ index: N, max_chars: M }` | Truncate `system[N].text` to `M` chars with a `[truncated]` marker. |
| `truncate_tool_result` | `{ older_than_turns?: N, max_chars?: M }` | Truncate `tool_result` content blocks by age, size, or both. |
| `rewrite_tool_description` | `{ name, new: "..." }` | Replace a tool's `description` field. |

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

### Rule scoping

Five scope dimensions, in increasing specificity:

1. `global`: applies to every request
2. `model`: applies when `request.model` matches
3. `account_id`: applies when the request is from a given Claude account
4. `device_id`: applies when the request is from a given device
5. `session_id`: applies only to a single Claude Code session

Multiple scope dimensions on the same rule are AND'd. For each request, the engine collects every enabled rule whose scope matches, then applies them in deterministic order (by `created_at`).

### Audit trail

Every exchange carries a `pipeline` block:

```json
"pipeline": {
  "rules_applied": [
    {"id": "rule_01H...", "name": "Strip Linear MCP", "removed": {"tools": 37, "chars": 48231}},
    {"id": "rule_01J...", "name": "Drop thinking", "removed": {"blocks": 4, "chars": 12044}}
  ],
  "delta": {"chars": -60275, "tokens_approx": -15068}
}
```

## Directory layout

### Source

```
manicure/
  addon.py              # mitmproxy entry: request/response hooks
  ir.py                 # InternalRequest, InternalResponse Pydantic models
  adapters/
    __init__.py         # registry
    base.py             # ProviderAdapter ABC
    anthropic.py        # V1
  pipeline.py           # apply(rules, ir) -> ir', audit
  rules.py              # scope matching, action implementations
  storage/
    __init__.py         # StorageBackend ABC
    disk.py             # DiskStorageBackend (default)
  breakpoint.py         # state machine: mode, paused flow registry
  server.py             # FastAPI app, uvicorn startup from addon load()
  routes.py             # /api/* handlers
  web/                  # Vite + React build output (served as static)
    index.html
    ...
```

### Data (disk storage backend)

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

### index.jsonl schema

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
2. **Adapter registry** (`adapters/`): walks installed adapters, returns the first match.
3. **Pipeline engine** (`pipeline.py`): pure-function rule application over the IR. Returns the transformed IR plus an audit record.
4. **Rule engine** (`rules.py`): scope matching, action implementations.
5. **Storage** (`storage/`): `StorageBackend` ABC + `DiskStorageBackend`. Injected via `Depends()`.
6. **Breakpoint manager** (`breakpoint.py`): holds `{flow_id: PausedFlow}` registry, where `PausedFlow` carries the `flow`, an `asyncio.Event`, the curated IR, and `paused_at_ms`. Tracks mode (`off`, `armed_once`).
7. **HTTP server** (`server.py`): FastAPI app wrapped in `uvicorn.Server`, started from the addon's `load()` hook as a background task on the mitmproxy event loop.
8. **Web UI** (`web/`): Vite + React SPA with two tabs: live log and rules. Detail view of any exchange shows raw, post-pipeline IR, and audit trail.

## API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Static SPA |
| GET | `/api/exchanges` | Paginated index |
| GET | `/api/exchanges/{id}` | Full exchange: raw, post-pipeline IR, audit |
| GET | `/api/stream` | SSE: `exchange` events and `paused` events |
| POST | `/api/breakpoint/arm` | Set mode to `armed_once` |
| POST | `/api/breakpoint/disarm` | Set mode to `off` |
| POST | `/api/release/{flow_id}` | Body: mutated IR. Applies mutation and releases the flow. |
| GET | `/api/rules` | List all rules |
| POST | `/api/rules` | Create a new rule |
| PATCH | `/api/rules/{id}` | Update fields (typically `enabled`) |
| DELETE | `/api/rules/{id}` | Delete a rule |
| POST | `/api/rules/from-exchange/{id}` | Promote a manual edit to a persistent rule |

All endpoints documented via auto-generated OpenAPI spec at `/docs`.

## Event flows

**Normal request**:

```
client -> mitmproxy -> request()
         -> adapter = registry.match(flow)
         -> ir = adapter.inbound_request(raw)
         -> ir', audit = pipeline.apply(rules, ir)
         -> storage.write_request(raw, ir, ir', audit)
         -> breakpoint.is_armed() == False
         -> flow.request.set_text(adapter.outbound_request(ir'))
         -> forward to provider
         -> response()
         -> ir_resp = adapter.inbound_response(raw, content_type)
         -> storage.write_response(raw, ir_resp)
         -> server.sse_emit({type: "exchange", ...})
         -> client receives response
```

**Armed-once request**:

```
client -> mitmproxy -> request()
         -> adapter = registry.match(flow)
         -> ir = adapter.inbound_request(raw)
         -> ir', audit = pipeline.apply(rules, ir)
         -> storage.write_request(raw, ir, ir', audit)
         -> breakpoint.is_armed() == True
         -> breakpoint.disarm()
         -> evt = asyncio.Event()
         -> paused_at_ms = now_ms()
         -> paused[flow.id] = PausedFlow(flow, evt, ir', paused_at_ms)
         -> server.sse_emit({type: "paused", flow_id, ir', audit, paused_at_ms})
         -> await evt.wait()                     [flow blocked here]

[UI displays editor over ir']
[user edits IR tree]
[user clicks Forward]

POST /api/release/{flow.id}
body: mutated IR
         -> flow.request.set_text(adapter.outbound_request(mutated_ir))
         -> evt.set()
         -> forward to provider
         -> response()
         -> storage.write_response(raw, ir_resp)  (mutated_manually=true)
         -> server.sse_emit({type: "exchange", ...})
         -> client receives response
```

## Schema-aware editor sections

The editor renders the IR, not the Anthropic schema. Every section operates on `InternalRequest` fields. When a second adapter lands, the editor does not change.

### model and sampling params

Simple form controls at the top of the editor.

- `model`: dropdown (free-text override available)
- `sampling.max_tokens`: number input
- `stream`: readonly checkbox (always true in practice)
- `provider_extras` collapsed advanced row

### system

A card per part. Card header shows index, type, size, and the first line of content as a preview.

- Checkbox on the card: strip on unchecked
- Click card to expand into an inline textarea for edit
- Any part over 500 chars stays collapsed by default
- `cache_hint` markers are displayed as badges but not editable in V1

### tools

The most important section. Prefix-grouped, collapsible.

- Global bulk bar: `[all] [none] [drop all MCP]`
- One group per prefix, header shows group name, count, total size
- Group-level bulk bar: `[all] [none]`
- Inside each group, one row per tool with: checkbox, name, size, description tooltip
- Bare tools group labeled `Built-in`, shown with de-prefixed names
- Rows sorted within group by size descending
- Per-row "promote to rule" affordance

### messages

Turn-by-turn cards. Each turn header shows index, role, summary of content blocks.

Per block type:
- `text`: inline edit, character count, strip toggle
- `tool_use`: show `name` and `id`, input summary collapsed, strip toggle
- `tool_result`: size, is_error badge, actions `[edit | truncate | drop]`
- `thinking`: size, strip toggle; global bulk action to strip all thinking blocks

### advanced

Collapsed section at the bottom containing `metadata`, `provider_extras`, and unrecognized fields. Raw JSON textarea.

### audit panel

Always visible at the side of the editor:

- Rule name, what it removed, byte/token delta
- Click a rule to see the before/after for that specific transform
- A toggle to view the original (pre-pipeline) IR

### paused-flow header

Shown at the top of the editor when a flow is paused:

- Short flow id (first 8 chars)
- Provider and model name
- **Elapsed timer**: `MM:SS` (or `HH:MM:SS` over an hour). Client-side, counts up from `paused_at_ms`.
- **Informational line**: `Client timeout is set by API_TIMEOUT_MS on the Claude Code side (default 10m). Raise it at launch: API_TIMEOUT_MS=3600000 claude`

### rules UI

A second tab alongside the live log:

- List view: every rule, scope chips, enable/disable toggle, applied count, delete button
- "Create rule from this exchange" affordance on every captured exchange
- Audit trail per exchange: which rules fired, what they removed, byte/token deltas

### footer

Always visible:

- Pre-pipeline size: chars and approximate tokens
- Post-pipeline size: chars and approximate tokens, plus delta percentage
- Post-edit size: chars and approximate tokens, plus delta from post-pipeline
- Buttons: `[ Forward ]`, `[ Forward Unmodified ]`, `[ Drop ]`

## Design notes

- **Pipeline ordering**: rules apply in deterministic `created_at` order. No ML, no surprises.
- **Concurrent paused flows**: the registry is a dict keyed by `flow.id`. N simultaneous pauses work. V1 UI surfaces only the most recent paused flow.
- **Shutdown**: mitmproxy `done()` hook releases every paused flow with a synthetic error response.
- **Flow ID**: use `flow.id` directly (mitmproxy UUID4).
- **Auth**: localhost bind only. Bearer token gate required before any non-loopback bind.
- **SSE vs WebSocket**: SSE is one-way server push, fits the model. Releases go over POST.
- **Retention**: not handled in V1. V1.1 adds rotation by age or count.

## Operational environment

### ANTHROPIC_BASE_URL (routing)

```bash
ANTHROPIC_BASE_URL=http://localhost:8787 claude
```

No system proxy settings, no TLS certificates, no sudo. Unset to restore direct-to-Anthropic traffic.

### API_TIMEOUT_MS (breakpoint editing window)

The Claude Code client controls its own timeout via `API_TIMEOUT_MS`. Default is 600000 (10 minutes). Maximum is 2147483647 (about 24.8 days). This directly caps how long the workbench can hold a paused request.

```bash
ANTHROPIC_BASE_URL=http://localhost:8787 API_TIMEOUT_MS=3600000 claude
```

## Defensive coding

Every section renderer must handle these variants without dropping data:

- System parts with and without `cache_hint`
- User content that is a string or a list of blocks (adapter normalizes to list-of-blocks)
- Empty `thinking` blocks (zero-length strings)
- `tool_result` content that is a string or a list of blocks
- `unknown` content blocks: always render with raw details and a strip toggle
- New top-level fields: caught by the round-trip test, surfaced in `provider_extras`

Any unknown IR top-level key falls through to the advanced raw-JSON section. The lossless round-trip invariant is the safety net.

## Build phases

Each phase is independently testable. Phase 2 is usable standalone before phase 3 lands.

1. **Persistence + IR + Anthropic adapter**: storage backend with disk default, `index.jsonl` and `exchanges/`. The IR Pydantic models, the adapter ABC, the Anthropic adapter, and the lossless round-trip test in CI.
2. **Embedded HTTP server + React SPA + SSE live log**: FastAPI + uvicorn inside the addon. Web UI shows the log list and a read-only detail view rendering the IR. No pipeline yet, no breakpoint yet. Ships a useful viewer.
3. **Pipeline engine + rule engine + rules UI**: the six V1 actions, scope matching, persistent rule storage, audit trail, rules tab in the UI. After phase 3 the workbench can curate without ever touching the breakpoint.
4. **Breakpoint mechanism + schema-aware editor**: armed-once mode, `asyncio.Event` pause, release endpoint, schema-aware editor over the IR, "promote to rule" flow, Forward and Forward Unmodified buttons.

## Related

- `~/.mdx/projects/manicure.md` (project definition)
- `/Users/alphab/.claude/scripts/capture_claude_request.py` (current addon, pre-workbench)
- `~/.mdx/projects/_versions/manicure.v3.md` (pre-split combined doc)
