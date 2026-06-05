---
title: "Manicure: Current Breakpoint + Rules Architecture"
type: project
tags: [manicure, architecture, breakpoint, rules, pipeline, mitmproxy]
summary: Complete architectural map of manicure's request interception, rule pipeline, breakpoint state machine, API surface, and frontend component tree.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-13
updated: 2026-04-13
---

## 1. Data Flow

A request passes through six stages from the coding agent to the LLM provider and back:

```
Agent (Claude Code)
  |
  v
mitmproxy (ManicureAddon.request)
  |-- _parse_request_ir()          parse raw HTTP -> InternalRequest
  |-- _run_pipeline()              load rules, apply pipeline, bump counts
  |-- is_armed()?
  |     yes -> _handle_breakpoint() -> pause flow, emit SSE "paused", await user action
  |     no  -> rewrite request body with curated IR
  v
Provider (Anthropic API)
  |
  v
mitmproxy (ManicureAddon.response)
  |-- _parse_response_ir()         parse response -> InternalResponse
  |-- _build_req_stats()           compute request stats from curated IR
  |-- _build_pipeline_stats()      extract audit summary
  |-- _persist_exchange()          write to DiskStorage (index + artifacts)
  |-- _emit_exchange()             SSE "exchange" event to frontend
  v
Frontend (SSE pump -> React Query cache -> UI)
```

### Stage detail

**Stage 1: Request interception** (`addon.py:349-375`, `ManicureAddon.request`)
- Filters to `/v1/messages` paths only
- `get_adapter(flow)` resolves the provider adapter (Anthropic)
- `_parse_request_ir(flow, adapter)` (`addon.py:140-154`) decodes the raw body into `InternalRequest` via `adapter.parse_request()`
- Stores `ir`, `raw_req`, `adapter` in `flow.metadata`

**Stage 2: Pipeline execution** (`addon.py:157-204`, `_run_pipeline`)
- `storage.load_rules()` reads rules from disk (JSON file)
- Deserializes each dict to a `Rule` model
- Calls `pipeline.apply(rules, ir)` which returns `(curated_ir, PipelineAudit)`
- Bumps `applied_count` on every applied rule via `storage.modify_rules(_bump)` (transactional, never raises)

**Stage 3: Breakpoint gate** (`addon.py:207-247`, `_handle_breakpoint`)
- Calls `bp.pause(flow, original_ir, curated_ir, audit)` which creates a `PausedFlow` entry in the module-level `_paused` dict and returns an `asyncio.Event`
- Emits SSE `{"type": "paused", ...}` via `broadcast.emit()`
- `await event.wait()` blocks the mitmproxy request hook until the user acts
- On resume: checks `pf.dropped` (return 400 to agent) or uses `pf.mutated_ir` / `pf.curated_ir` as the final IR
- Rewrites `flow.request` body via `adapter.outbound_request(final_ir)`

**Stage 4: Provider response** (`addon.py:380-434`, `ManicureAddon.response`)
- Reads back `adapter`, `ir`, `raw_req` from `flow.metadata`
- Parses response IR and builds stats (req, res, pipeline)
- Creates `IndexEntry` and `ExchangeArtifacts`
- Persists to storage, emits SSE `"exchange"` event

**Stage 5: SSE transport** (`stream.py:14-29`)
- Single `GET /api/stream` endpoint returns `text/event-stream`
- `broadcast.py` manages a `set[asyncio.Queue[str]]` of subscribers
- `emit()` pushes JSON to all queues; stream endpoint drains them with 15s keepalive timeout

**Stage 6: Frontend hydration** (`useExchangeStream.ts:13-73`)
- `EventSource` at `/api/stream`
- `type: "paused"` -> `useUIStore.setPausedFlow()` opens the BreakpointEditor overlay
- `type: "exchange"` -> prepends to React Query `["exchanges"]` cache, auto-selects, and closes the editor if this was the forwarded flow

---

## 2. Rules System

### 2.1 Rule model (`rules.py:49-59`)

```python
class Rule(BaseModel):
    id: str              # "rule_{uuid4().hex[:12]}" auto-generated
    name: str
    enabled: bool = True
    scope: RuleScope
    action: ActionLiteral
    params: dict[str, Any]
    created_at: datetime
    applied_count: int = 0
```

### 2.2 RuleScope (`rules.py:39-46`)

Conjunctive (AND) matching. `global: true` matches everything. Otherwise each non-null field must match or the rule is skipped. At least one field must match (`matched_any` guard).

```python
class RuleScope(BaseModel):
    global_: bool = Field(False, alias="global")
    session_id: str | None = None
    device_id: str | None = None
    account_id: str | None = None
    model: str | None = None
```

Matching logic: `matches_scope()` (`rules.py:76-98`)

### 2.3 Action types and dispatch table

Six actions, dispatched via `_DISPATCH_TABLE` (`pipeline.py:63-70`):

| Action | Params | Implementation | What it does |
|--------|--------|----------------|-------------|
| `strip_tools` | `name`, `prefix`, `regex` (all optional) | `rules.py:106-137` | Remove tools matching name/prefix/regex. Returns `{tools: N, chars: N}` |
| `strip_thinking` | (none) | `rules.py:140-160` | Remove all `ThinkingBlock` from messages. Returns `{blocks: N, chars: N}` |
| `strip_system_part` | `index: int` | `rules.py:163-176` | Remove `ir.system[index]`. Returns `{parts: 0\|1, chars: N}` |
| `truncate_system_part` | `index: int`, `max_chars: int` | `rules.py:179-200` | Truncate system part text to max_chars with ` [truncated]` suffix. Returns `{chars: N}` |
| `truncate_tool_result` | `older_than_turns: int?`, `max_chars: int?` | `rules.py:203-294` | Truncate `ToolResultBlock` content in older messages or when exceeding max_chars. Default 2000 for aged results. Returns `{blocks: N, chars: N}` |
| `rewrite_tool_description` | `name: str`, `new: str` | `rules.py:297-322` | Replace description of a named tool. Returns `{chars: delta}` |

### 2.4 Pipeline apply (`pipeline.py:86-112`)

```
1. Filter rules to [enabled AND matches_scope(rule, ir)]
2. Sort by created_at ascending (FIFO)
3. For each rule: _dispatch(rule.action, current_ir, rule.params)
4. Collect RuleAuditEntry per rule (id, name, action, removed dict)
5. Return (curated_ir, PipelineAudit{rules_applied, chars_before, chars_after})
```

All action functions are **pure**: they return `ir.model_copy(update={...})`, never mutate the input IR (frozen Pydantic models).

### 2.5 PipelineAudit (`pipeline.py:30-41`)

```python
class PipelineAudit(BaseModel):
    rules_applied: list[RuleAuditEntry]
    chars_before: int
    chars_after: int
    # @property chars_delta -> int
    # @property tokens_approx -> abs(chars_delta) // 4
```

---

## 3. State Model

### 3.1 Rules storage

Rules are persisted as a JSON array in a file managed by `DiskStorageBackend` (`storage/disk.py:216`).

- **Read path**: `storage.load_rules()` -> returns `list[dict]`
- **Write path**: `storage.modify_rules(fn)` -> atomically reads, applies `fn`, writes under lock
- `fn` is always a synchronous callable that receives `list[dict]` and returns `list[dict]`
- The lock prevents concurrent interleaving (e.g. API delete + addon bump racing)

The module-level singleton `_backend` is initialized lazily on first access via `get_storage()` (`storage/__init__.py:26-33`).

### 3.2 Breakpoint state machine (`breakpoint.py`)

Module-level globals:

```python
_mode: Literal["off", "armed_once"] = "off"
_paused: dict[str, PausedFlow] = {}
```

State transitions:

```
off --[arm()]--> armed_once
armed_once --[disarm()]--> off
armed_once --[pause()]--> (flow registered in _paused, stays armed_once)
```

Note: `pause()` does NOT disarm. The mode stays `armed_once`, meaning every intercepted request while armed will pause. The name is vestigial.

`PausedFlow` dataclass holds:
- `flow`: the mitmproxy HTTPFlow (needed to rewrite the request)
- `event`: asyncio.Event the addon awaits
- `original_ir`: pre-pipeline IR
- `curated_ir`: post-pipeline IR (updated by re-audit)
- `mutated_ir`: user-edited IR (set on release with edits)
- `dropped: bool`: user chose to drop
- `paused_at_ms`: timestamp
- `audit`: PipelineAudit snapshot

### 3.3 Pipeline audit computation

Computed by `pipeline.apply()`:
1. `chars_before = _count_chars(ir)` (sum of system text, tool defs as JSON, message block JSON)
2. Run all matching rules, collect removals
3. `chars_after = _count_chars(curated_ir)`
4. `chars_delta` and `tokens_approx` are derived properties

### 3.4 reauditFlow end-to-end

**Frontend** (`BreakpointEditor.tsx:44-55`):
1. User toggles a rule in the left panel, or clicks re-audit
2. Auto-trigger: `useEffect` watches `rules.map(r => r.id + ":" + r.enabled)` as a string key; fires `handleReaudit()` on change
3. Calls `reauditFlow(pausedFlow.flow_id)` -> `POST /api/breakpoint/re-audit/{flow_id}`

**Backend** (`breakpoint_routes.py:109-131`):
1. Looks up `PausedFlow` in `_paused` dict
2. Loads fresh rules from storage
3. Calls `pipeline_apply(rules, pf.original_ir)` (re-runs against the **original** pre-pipeline IR)
4. Updates `pf.curated_ir` and `pf.audit` **in place** on the PausedFlow
5. Returns `{audit, curated_ir}`

**Frontend** (on success):
1. `setAudit(result.audit)` updates the AuditPanel sidebar
2. `setEditedIr(result.curated_ir)` resets the editor to the new pipeline output

---

## 4. Frontend Component Tree

```
App (app.tsx:12-126)
  |-- useExchanges()           fetches exchange list via React Query
  |-- useExchangeStream()      SSE pump, pushes to cache + Zustand
  |-- useRules()               rules CRUD via React Query mutations
  |-- useBreakpoint()          arm/disarm + hydrate pausedFlow on refresh
  |-- useUIStore               Zustand: selectedId, activeTab, pausedFlow, forwardingFlowId
  |
  +-- <aside> Left Panel
  |     +-- Header: Arm/Disarm button, Live indicator
  |     +-- Tab bar: "log" | "rules"
  |     +-- Tab content:
  |           log  -> ExchangeList (exchanges, selectedId, onSelect)
  |           rules -> RulesList (rules, onToggle, onDelete)
  |                    CreateRuleForm (onCreated)
  |
  +-- <main> Right Panel
        |-- pausedFlow != null?
        |     yes -> BreakpointEditor
        |     no  -> selectedId? -> ExchangeDetail : placeholder
        |
        +-- BreakpointEditor (pausedFlow, onResolved)
              |-- owns: editedIr (useState, deep clone of pausedFlow.ir)
              |-- owns: audit, loading, reauditing, error
              |-- useRules() for auto-reaudit on toggle
              |
              +-- PausedHeader (flowId, pausedAtMs)
              +-- EditorActions (originalIr, pipelineAudit, editedIr, provider, model,
              |                   onForward, onForwardUnmodified, onDrop, loading)
              |     |-- Row 1: Drop / Pass Through / Forward buttons
              |     +-- Row 2: provider/model + chars count + delta%
              |
              +-- Scrollable editor area:
              |     +-- SamplingSection (sampling, onChange)
              |     +-- MessagesSection (messages, onChange)
              |     +-- SystemSection (parts, onChange)
              |     +-- ToolsSection (tools, onChange)
              |
              +-- Sidebar:
                    +-- AuditPanel (audit, onDisableRule)
```

### State ownership

| State | Location | Persistence |
|-------|----------|-------------|
| `selectedId`, `activeTab` | Zustand (persisted to localStorage `"manicure-ui"`) | Survives page reload |
| `pausedFlow` | Zustand (not persisted) | Re-hydrated from API on refresh via `useBreakpoint` |
| `forwardingFlowId` | Zustand (not persisted) | Lost on refresh |
| `editedIr` | BreakpointEditor local state | Lost when editor unmounts |
| `rules` | React Query cache `["rules"]` | Refetched on mount |
| `exchanges` | React Query cache `["exchanges"]` | SSE pump + initial fetch |

---

## 5. API Surface

All routes are mounted under `/api` (`main.py:84`).

### 5.1 Exchanges (`/api/exchanges`)

| Method | Path | Request | Response | Handler |
|--------|------|---------|----------|---------|
| `GET` | `/api/exchanges` | `?limit=50&offset=0` | `IndexEntry[]` | `exchanges.py:15-20` |
| `GET` | `/api/exchanges/{id}` | - | `{entry, request_ir, request_curated_ir, response_ir}` | `exchanges.py:23-49` |

### 5.2 Rules CRUD (`/api/rules`)

| Method | Path | Request | Response | Handler |
|--------|------|---------|----------|---------|
| `GET` | `/api/rules` | - | `Rule[]` | `rules.py:16-21` |
| `POST` | `/api/rules` | `{name, scope, action, params, enabled?}` | `Rule` (201) | `rules.py:24-39` |
| `PATCH` | `/api/rules/{id}` | `{name?, enabled?, params?}` | `Rule` | `rules.py:42-72` |
| `DELETE` | `/api/rules/{id}` | - | 204 | `rules.py:75-87` |

### 5.3 Breakpoint (`/api/breakpoint`)

| Method | Path | Request | Response | Handler |
|--------|------|---------|----------|---------|
| `GET` | `/api/breakpoint/status` | - | `{mode, paused_flows: [{flow_id, paused_at_ms}]}` | `breakpoint_routes.py:45-53` |
| `GET` | `/api/breakpoint/paused/{flow_id}` | - | `{flow_id, ir, audit, paused_at_ms}` | `breakpoint_routes.py:56-73` |
| `POST` | `/api/breakpoint/arm` | - | `{mode: "armed_once"}` | `breakpoint_routes.py:76-79` |
| `POST` | `/api/breakpoint/disarm` | - | `{mode: "off"}` | `breakpoint_routes.py:82-85` |
| `POST` | `/api/breakpoint/release/{flow_id}` | `InternalRequest` body | `{status: "released"}` | `breakpoint_routes.py:88-93` |
| `POST` | `/api/breakpoint/release-unmodified/{flow_id}` | - | `{status: "released"}` | `breakpoint_routes.py:96-101` |
| `POST` | `/api/breakpoint/re-audit/{flow_id}` | - | `{audit: PipelineAudit, curated_ir: InternalRequest}` | `breakpoint_routes.py:109-131` |
| `POST` | `/api/breakpoint/drop/{flow_id}` | - | `{status: "dropped"}` | `breakpoint_routes.py:134-139` |

### 5.4 SSE Stream (`/api/stream`)

| Method | Path | Response | Handler |
|--------|------|----------|---------|
| `GET` | `/api/stream` | `text/event-stream` | `stream.py:14-29` |

Event types:
- `{"type": "connected"}` on initial connection
- `{"type": "paused", "flow_id", "ir", "audit", "paused_at_ms"}` when a flow is paused at breakpoint
- `{"type": "exchange", "id", "ts", "provider", "model", "req", "res", "pipeline", "mutated_manually"}` when a response completes

### 5.5 Health

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/health` | `{status: "ok"}` |

---

## 6. Ephemeral State

**Everything is ephemeral.** Confirmed:

- **Rules**: stored in a JSON file on disk (`DiskStorageBackend`), but this is a local working directory that gets wiped between proxy sessions. The `_backend` singleton is lazily initialized per process. No database.
- **Exchanges**: written to disk under `exchanges/{ts_slug}-{id[:8]}/` as individual JSON files (raw bodies, IR models). Local to the storage dir.
- **Breakpoint state**: module-level dict `_paused` and mode `_mode` in `breakpoint.py`. Pure in-memory, lost on process restart. `clear_all()` is called at addon shutdown.
- **SSE subscribers**: module-level `set[asyncio.Queue]` in `broadcast.py`. In-memory only.
- **Frontend state**: Zustand store with partial `persist` middleware. Only `selectedId` and `activeTab` survive page reload (localStorage key `"manicure-ui"`). `pausedFlow` and `forwardingFlowId` are transient.

There is no database, no external state service, no cross-session persistence by design.
