---
title: "Tier 2 shared proxy design proposal"
type: design
tags: [transport-matters, tier-2, shared-proxy, mitmproxy, captured-run, breakpoint, session-store]
summary: "Implementation-ready design for one embedded shared mitmproxy Master serving captured runs with run-scoped bindings, breakpoints, storage, and transcript ingestion."
status: proposed
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

# Tier 2 shared proxy design proposal

## Executive decision

Choose **one embedded mitmproxy `DumpMaster` inside the API process**. It owns one live listener per captured run and resolves every flow to a `ProxyRunBinding` by listen port. The API routes, breakpoint events, override state, SSE broadcaster, and addon hooks share one asyncio loop, so the live `asyncio.Event` release path works for canvas runs.

Rejected HQ3 alternative: a `mitmdump` subprocess plus IPC. It preserves process isolation, but it requires a new cross process control channel for live `HTTPFlow` pause, release, drop, re-audit, override state, token counting, and SSE. The current release path in `api/src/transport_matters/breakpoint.py::release` sets an in-memory event created by `api/src/transport_matters/breakpoint.py::pause`; a subprocess cannot receive that without redesigning the product's core control plane.

Choose **one shared Postgres pool and writer with bounded tailer dispatch** for HQ4. The commit code and database pool stay shared, but transcript polling and submit work move from one blocking tailer thread to a bounded dispatcher with per-session ordering. This keeps the pool explosion fixed while preventing one slow run from blocking all cursors.

Rejected HQ4 alternatives:

1. A single tailer thread and single `SessionWriter.submit_blocking` loop. `api/src/transport_matters/index/tailer.py::TranscriptTailer.poll` iterates all cursors and `api/src/transport_matters/session/writer.py::SessionWriter.submit_blocking` can wait up to its commit timeout. At 50 runs, one slow commit can head of line block every cursor.
2. Per-run pools and writers. This rebuilds the Tier 1 connection ceiling that Tier 2 exists to remove.

Choose **one shared proxy with supervised Master restart and binding re-registration** for HQ5. Runs remain process resident across API restart, matching the current `api/src/transport_matters/run_manager.py::RunManager.close` shutdown behavior. A crash of only the embedded Master is handled inside the running API process: the manager starts a new Master, replays active modes, drops live paused flows with a typed event, and lets clients continue if their CLI survives the transient proxy outage.

Rejected HQ5 alternative: a bounded pool of K proxies. It improves blast radius, but adds scheduler state, duplicate breakpoint surfaces, cross-proxy flow routing, and more failure modes before evidence shows one embedded Master is insufficient.

## Grounding facts

Grounding docs read first:

- `~/.mdx/projects/tm-tier2-spike-mitmproxy-modes.md`
- `~/.mdx/projects/tm-tier2-seams-and-questions.md`
- `~/.mdx/projects/tm-perf-tier2-shared-proxy-design.md`

Facts to build on:

1. mitmproxy 12.2.2 accepts runtime `master.options.update(mode=[...])` and starts or stops reverse listeners on a live `DumpMaster`. The proven demux keys are `flow.client_conn.proxy_mode.custom_listen_port` and `flow.client_conn.sockname[1]`.
2. Current captured runs spawn one `mitmdump` process per run through `api/src/transport_matters/captured_run.py::prepare_captured_run`, `api/src/transport_matters/cli/runner.py::start_prepared_proxy`, and `api/src/transport_matters/cli/launch_runtime.py::build_mitmdump_argv`.
3. Current addon identity is process local. `api/src/transport_matters/config.py::get_settings` is cached, and addon paths read `Settings.run_id`, `Settings.storage_dir`, `Settings.cwd`, and managed session fields from process environment.
4. Current breakpoint state is process global. `api/src/transport_matters/breakpoint.py::arm`, `pause`, `release`, `pause_serializer`, and `clear_all` share one mode, one paused flow map, and one serializer.
5. Canvas runs use external web runtime, so current canvas breakpoint routes and current addon state live in different processes. The embedded API design fixes this by placing routes and hooks in one process.
6. Current storage is a process global singleton through `api/src/transport_matters/storage/__init__.py::get_storage`. A shared proxy must replace this with run-bound storage.

## API contract

All new mutable routes use the existing `ApiError` shape from `api/src/transport_matters/api/v1/run_routes.py::ApiError`.

```ts
interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

type RunState = "RUNNING" | "TERMINATING" | "TERMINATED" | "EXITED" | "FAILED";
type CapturedRunCli = "claude" | "codex";
type ProxyModeKind = "reverse" | "regular";
type ProxyBindingState = "pending" | "active" | "draining" | "closed" | "failed";

interface ProxyBindingView {
  runId: string;
  cli: CapturedRunCli;
  proxyPort: number;
  modeKind: ProxyModeKind;
  upstream: string | null;
  state: ProxyBindingState;
  proxyGeneration: number;
  modeGeneration: number;
}

interface RunView {
  runId: string;
  workspaceId: string;
  sessionId: string | null;
  cli: CapturedRunCli;
  state: RunState;
  endReason: "explicit" | "idle-timeout" | "shutdown" | "deploy-restart" | null;
  error: string | null;
  createdAt: string;
  proxy: ProxyBindingView | null;
}
```

### Run scoped capture reads

These replace the single-run `/api/exchanges/*` dependency on process `Settings.storage_dir`.

```ts
// GET /v1/runs/{runId}/exchanges?limit=50&offset=0&trackId=...
interface ListRunExchangesResponse {
  items: IndexEntry[];
}

// GET /v1/runs/{runId}/exchanges/{exchangeId}
interface RunExchangeDetailResponse extends ExchangeDetailResponse {}

// GET /v1/runs/{runId}/exchanges/{exchangeId}/turn-content
interface RunTurnContentResponse extends TurnContentResponse {}

// GET /v1/runs/{runId}/exchanges/{exchangeId}/pipeline-tokens
interface RunPipelineTokensResponse extends PipelineTokensResponse {}
```

Validation rules:

- `runId` must identify a live or retained `ManagedRun` known to `RunManager`.
- `exchangeId` must exist in that run's storage root and its `IndexEntry.run_id` must equal `runId` when present.
- No route falls back to global `get_storage()` in shared proxy mode.

### Run scoped breakpoint routes

```ts
type BreakpointMode = "off" | "armed_once";
type BreakpointTransport = "http" | "websocket";

interface PausedFlowInfo {
  flowId: string;
  pausedAtMs: number;
  transport: BreakpointTransport;
}

interface BreakpointStatusDetail {
  runId: string;
  mode: BreakpointMode;
  pausedFlows: PausedFlowInfo[];
}

interface PausedFlowDetail extends PausedFlow {
  runId: string;
}

// GET /v1/runs/{runId}/breakpoint/status
// POST /v1/runs/{runId}/breakpoint/arm
// POST /v1/runs/{runId}/breakpoint/disarm
// GET /v1/runs/{runId}/breakpoint/paused/{flowId}
// POST /v1/runs/{runId}/breakpoint/release/{flowId}
// POST /v1/runs/{runId}/breakpoint/release-unmodified/{flowId}
// POST /v1/runs/{runId}/breakpoint/drop/{flowId}
// POST /v1/runs/{runId}/breakpoint/re-audit/{flowId}
```

Validation rules:

- The `runId` path value selects the breakpoint state. `flowId` alone is never sufficient.
- Release, drop, and re-audit must verify the paused flow belongs to `runId` before changing it.
- Mutation routes require the same Origin check pattern used by `api/src/transport_matters/api/v1/run_routes.py::create_run`.

### Run scoped overrides

Current override storage already supports `(run_id, track_id)` through `api/src/transport_matters/override_state.py::scope_from_params`. The public API should stop accepting `run_id` as a query concern and derive it from the path.

```ts
// GET /v1/runs/{runId}/overrides?trackId=...
// PATCH /v1/runs/{runId}/overrides?trackId=...
// POST /v1/runs/{runId}/overrides/toggle?trackId=...
// DELETE /v1/runs/{runId}/overrides?trackId=...
```

### Run scoped SSE

```ts
type RunEventType =
  | "connected"
  | "exchange"
  | "exchange_deleted"
  | "paused"
  | "paused_tokens"
  | "released"
  | "dropped"
  | "proxy_binding_state"
  | "proxy_restart";

interface RunEventEnvelope<T = unknown> {
  type: RunEventType;
  runId: string;
  payload: T;
  emittedAt: string;
}

// GET /v1/runs/{runId}/stream
```

Rules:

- Every emitted event carries `runId`.
- Subscribers to `/v1/runs/{runId}/stream` receive only that run's events.
- The global `/api/stream` route in `api/src/transport_matters/api/v1/stream.py::stream_exchanges` is deleted or kept only as an internal development alias after frontend cutover.

## Component model

### SharedProxyManager

Location: new module package `api/src/transport_matters/shared_proxy/`.

Do not put the manager into `api/src/transport_matters/run_manager.py`. That file is already near the 700 line threshold, and shared proxy logic has separate ownership.

Responsibilities:

- Own one embedded `mitmproxy.tools.dump.DumpMaster` task.
- Own the mode list and mutate it with `master.options.update(mode=[...])` under one mode mutation lock.
- Own `bindings_by_listen_port: dict[int, ProxyRunBinding]` and `bindings_by_run_id: dict[str, ProxyRunBinding]`.
- Create `SharedProxyCore`, which contains the shared HTTP client, token counter, session writer, tailer dispatcher, and run event broker.
- Expose `register(binding_request) -> ProxyBindingLease` and `deregister(run_id)` to `RunManager`.
- Expose `resolve_flow(flow) -> ProxyRunBinding | None` to the addon.
- Track `proxy_generation` and `mode_generation` for observability and safe restart.

Lifecycle in `api/src/transport_matters/main.py::lifespan`:

1. Start `SessionEventHub` and the session store as today through `api/src/transport_matters/main.py::_start_session_store`.
2. Create `SharedProxyManager` on `app.state.shared_proxy_manager`.
3. Create `RunManager` with the shared proxy dependency. `api/src/transport_matters/api/v1/run_routes.py::create_run_manager` gains a manager argument or dependency object.
4. On shutdown, close `RunManager` first so every active run deregisters its mode, then close `SharedProxyManager`.

### ProxyRunBinding

```python
@dataclass(slots=True)
class ProxyRunBinding:
    run_id: str
    cli: Literal["claude", "codex"]
    listen_port: int
    mode_kind: Literal["reverse", "regular"]
    mode_spec: str
    upstream: str | None
    working_dir: Path
    storage_dir: Path
    storage: StorageBackend
    web_runtime: Literal["embedded", "external"]
    agent_home_dir: Path | None
    owned_native_session_id: str | None
    owned_source_descriptor: str | None
    launch_fields: dict[str, object]
    default_client_passthrough: tuple[str, ...]
    breakpoint: RunBreakpointState
    recent_auth: dict[str, str] | None
    active_flows: set[str]
    state: Literal["pending", "active", "draining", "closed", "failed"]
    proxy_generation: int
    mode_generation: int
```

Mode strings:

- Claude: `reverse:{upstream}@127.0.0.1:{listen_port}`.
- Codex: `regular@127.0.0.1:{listen_port}`.

The spike proved reverse mode mutation. The first implementation slice for Codex must add the same runtime mutation proof for `regular@127.0.0.1:{listen_port}` before Codex cutover. If regular mode mutation fails, Codex remains on the existing explicit proxy path until a Codex specific design resolves it. The shared manager should still use the same binding model.

### SharedProxyAddon

The embedded Master adds an addon object directly, not through `mitmdump -s` script loading.

Hook shape:

```python
class SharedProxyAddon:
    def __init__(self, manager: SharedProxyManager) -> None: ...

    async def request(self, flow: http.HTTPFlow) -> None:
        binding = self._resolve_or_fail(flow)
        await handle_http_request(flow, binding, self._core.token_counter)
```

`api/src/transport_matters/addon.py::TransportMattersAddon` currently stores one runtime in `self._runtime` and calls handlers with only the token counter. In Tier 2, every hook resolves a binding first and passes that binding through the handler, recorder, breakpoint, and Codex paths.

## Spawn flow

The flow keeps Tier 1 admission backpressure from `api/src/transport_matters/run_manager.py::RunManager.spawn` and `_spawn_new_admitted`.

1. `POST /v1/runs` enters `api/src/transport_matters/api/v1/run_routes.py::create_run`.
2. `RunManager.spawn` validates CLI, cwd, idempotency key, and session store reachability.
3. A refactored preparation step builds the client launch context without starting `mitmdump`. It reuses `api/src/transport_matters/captured_run_context.py::build_captured_run_context`, runtime home planning, managed session minting, workspace lock, manifest writing, and client env construction.
4. Allocate one loopback listen port for the run. The manager owns final readiness because the port is not truly leased until mitmproxy binds it.
5. Build a pending `ProxyRunBinding`. Initialize its storage backend from `storage_dir`; do not call process global `api/src/transport_matters/storage/__init__.py::get_storage`.
6. Register the binding in `bindings_by_listen_port` before exposing the mode.
7. Mutate the mode list:
   - append the binding's `mode_spec`
   - call `master.options.update(mode=current_modes)`
   - wait for `proxyserver.servers.is_updating` to clear
   - probe `127.0.0.1:{listen_port}` until it accepts connections
8. Register the transcript cursor for the run before spawning the client. The current `api/src/transport_matters/addon_runtime.py::_register_owned_cursor` becomes `register_owned_cursor_for_binding(tailer, binding, started_at)`.
9. Mark the binding active and emit `proxy_binding_state`.
10. Spawn the client PTY with the existing client argv and env. Claude keeps `ANTHROPIC_BASE_URL=http://127.0.0.1:{listen_port}` from `api/src/transport_matters/captured_claude.py::build_claude_captured_invocation`. Codex keeps the explicit proxy env from `api/src/transport_matters/cli/codex_cmd.py::build_codex_invocation`.
11. Add the `ManagedRun` to `RunManager` and start `_drain_run` as today.

Rollback rules:

- If preparation fails before mode registration, close the resource stack and release the workspace lock.
- If mode mutation fails, remove the pending binding, restore the previous mode list, close storage resources for that binding, and release the workspace lock.
- If readiness times out, remove the mode, wait for listener close, remove the binding, and return `proxy_start_timeout` through the existing typed `RunManagerErrorCode` mapping.
- If transcript cursor registration fails, rollback the mode and fail spawn. Silent transcript loss is too dangerous in the shared architecture.
- If client PTY spawn fails after binding activation, deregister the binding, terminate any partial PTY, release the workspace lock, and return `launch_failed`.
- If `RunManager` is closed after proxy activation but before run registration, run the same deregister path.

## Teardown flow

Teardown remains owned by `api/src/transport_matters/run_manager.py::RunManager._teardown_run`, but the lease changes meaning.

Current `api/src/transport_matters/captured_run_models.py::CapturedRunLease.close` terminates a per-run supervisor. In Tier 2, the lease must close per-run resources only:

1. Mark the `ManagedRun` terminating and close viewers as today.
2. Terminate or close the client PTY as today.
3. Call `SharedProxyManager.deregister(run_id)` through the lease.
4. In `deregister`:
   - mark binding `draining`
   - disarm that run's breakpoint state
   - drop only paused flows for that run
   - remove the binding's `mode_spec` from the mode list
   - call `master.options.update(mode=current_modes)`
   - wait until the port refuses new connections
   - wait for `binding.active_flows` to drain, bounded by a configurable timeout
   - unregister the run's transcript cursor
   - flush and close per-run snapshot resources
   - remove `bindings_by_listen_port[listen_port]` and `bindings_by_run_id[run_id]`
   - mark binding `closed`
5. Never close the shared HTTP client, token counter, session writer, tailer dispatcher, event broker, or Master during per-run teardown.

The last run can leave the Master alive with an empty mode list if mitmproxy accepts it. If the implementation spike finds that an empty mode list is invalid, keep one reserved internal loopback mode owned by the manager. It must never map to a run and must reject external traffic.

## Addon flow to run resolution

Core contract: every hook resolves the run from the listen port the flow arrived on.

Algorithm:

```python
def listen_port_for_flow(flow: http.HTTPFlow) -> int | None:
    mode = getattr(flow.client_conn, "proxy_mode", None)
    custom = getattr(mode, "custom_listen_port", None)
    sockname = getattr(flow.client_conn, "sockname", None)
    sock_port = sockname[1] if sockname else None
    if custom is not None and sock_port is not None and custom != sock_port:
        raise ProxyDemuxMismatch(custom=custom, sock_port=sock_port)
    return custom or sock_port
```

Rules per hook:

- `request`: resolve binding, add `flow.id` to `binding.active_flows`, store `run_id` and `listen_port` in flow metadata, then call request handling.
- `response`: prefer flow metadata, fallback to live resolve, persist response to the binding's storage, remove `flow.id` from active flows.
- `error`: same resolution, persist diagnostics when possible, remove active flow.
- `websocket_start`: resolve binding and mark active.
- `websocket_message`: use the stored binding. Later Codex turns stay on the same websocket flow and still pause per turn.
- `websocket_end`: finalize and remove active flow.

Unmapped flow handling:

- If a hook cannot map a flow to an active binding, return HTTP 502 for HTTP flows or close the websocket with a proxy error.
- Log only flow id, listen port, proxy generation, and mode generation. Never log raw payload or auth headers.
- Increment `shared_proxy_unmapped_flow_total`.

A mismatch between `proxy_mode.custom_listen_port` and `sockname[1]` is a critical demux violation. Return 502, mark the proxy unhealthy, and fail the test gate. Cross-run contamination is worse than dropping one flow.

## Run identity replacement

`api/src/transport_matters/config.py::get_settings` remains valid for operator process configuration: database URL, CORS, trusted hosts, debug, pool sizes, and default passthrough. It no longer supplies run identity inside addon hooks.

Move these read sites to `ProxyRunBinding` or `SharedProxyCore`:

| Current site | Change |
| --- | --- |
| `api/src/transport_matters/addon_runtime.py::load_capture_runtime` | Split into `load_shared_proxy_core(settings)` and `create_binding_runtime(binding_request)`. Shared core builds HTTP client, token counter, writer, dispatcher, and event broker. Binding runtime builds storage, snapshot writer, and cursor registration data. |
| `api/src/transport_matters/addon_runtime.py::_launch_run_context` | Take `ProxyRunBinding` and `started_at`, not `Settings`. |
| `api/src/transport_matters/addon_runtime.py::_register_owned_cursor` | Register from binding fields: `run_id`, `working_dir`, `cli`, `owned_native_session_id`, `agent_home_dir`, `launch_fields`, and `owned_source_descriptor`. |
| `api/src/transport_matters/addon_handlers.py::handle_http_request` | Pass `binding.run_id` into `api/src/transport_matters/request_pipeline.py::run_pipeline`. Store binding identity in flow state. |
| `api/src/transport_matters/addon_handlers.py::handle_codex_websocket_message` | Same as HTTP, including later Codex turn replay. |
| `api/src/transport_matters/exchange_recorder.py::persist_unparsed_exchange` | Accept binding or storage plus run id. Remove `get_settings().run_id` and `get_storage()`. |
| `api/src/transport_matters/exchange_recorder.py::persist_http_exchange` | Use binding storage and binding run id. |
| `api/src/transport_matters/exchange_recorder.py::persist_http_provisional_exchange` | Use binding storage and binding run id. |
| `api/src/transport_matters/codex/exchange.py::persist_codex_provisional_exchange` | Use binding storage and binding run id. |
| `api/src/transport_matters/codex/exchange.py::_persist_codex_exchange` | Use binding storage and binding run id. |
| `api/src/transport_matters/codex/exchange.py::persist_codex_handshake_failure` | Use binding storage and binding run id. |
| `api/src/transport_matters/storage/__init__.py::get_storage` | Do not use from shared addon paths. Run scoped API routes resolve storage from `RunManager` or persisted run metadata. |
| `api/src/transport_matters/pause_session.py::_flow_track_fields` | Take binding and use `binding.run_id`. |
| `api/src/transport_matters/pause_session.py::_run_pause` | Take binding and use `binding.breakpoint_timeout_s` or shared settings copied onto binding. |
| `api/src/transport_matters/api/v1/meta.py::get_meta` | For embedded browser shells, resolve current run from the request context or run id route. For desktop canvas, use `/v1/runs/{runId}` instead of global meta for run identity. |
| `api/src/transport_matters/api/v1/exchanges.py::list_exchanges` and peers | Move to `/v1/runs/{runId}/exchanges` and resolve that run's storage. |

`RequestFlowState` in `api/src/transport_matters/flow_state.py::capture_request_flow_state` should gain `run_id` and `listen_port` fields, or a lightweight `binding_ref`. Do not store a mutable manager object in flow metadata.

## Breakpoint, override, counting, and SSE model

### Breakpoints

Replace module globals in `api/src/transport_matters/breakpoint.py` with `RunBreakpointState`:

```python
@dataclass(slots=True)
class RunBreakpointState:
    mode: Literal["off", "armed_once"] = "off"
    paused: dict[str, PausedFlow] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    pause_serializer: asyncio.Lock = field(default_factory=asyncio.Lock)
```

The serializer is per run. A paused flow from run A must not block a request from run B.

Routes resolve `RunBreakpointState` through `SharedProxyManager.binding_for_run(run_id)`. `release` still sets `pf.event.set()` in the same event loop as the addon, so canvas gains working breakpoints.

### Overrides

Keep one `OverrideStore`, but expose only run scoped routes. `api/src/transport_matters/request_pipeline.py::run_pipeline` already accepts `run_id`; the shared addon must always pass it. Track scoped overrides continue to use `track_id` from `TrackAssignment`.

### Counting and auth headers

`api/src/transport_matters/counting.py::TokenCounter` is shared. The module global counter can be removed from addon paths after the shared core owns it.

`api/src/transport_matters/counting.py::set_recent_auth` must not remain process global. Either delete it if no reader needs it, or replace it with `binding.recent_auth`. Re-audit should continue using `PausedFlow.auth_headers`, which are captured per flow.

### SSE

Replace `api/src/transport_matters/broadcast.py::emit` with a run aware broker. It may keep a global debug subscription internally, but public events are run scoped. Existing exchange events already accept `run_id` through `api/src/transport_matters/exchange_recorder.py::emit_exchange`; delete and paused token events need the same run id requirement.

Frontend URL changes:

- `www/src/api.ts::armBreakpoint` becomes `armBreakpoint(runId)` and calls `/v1/runs/{runId}/breakpoint/arm`.
- `www/src/api.ts::fetchBreakpointStatus`, `releaseFlow`, `releaseFlowUnmodified`, `dropFlow`, `reauditFlow`, and `fetchPausedFlowDetail` all take `runId`.
- `www/src/hooks/useExchangeStream.ts` subscribes to `/v1/runs/{runId}/stream`.
- Canvas panes already know `runId` from `www/src/session-canvas/model/capturedRunStore.ts`; browser shell pages read it from `/v1/runs/{runId}` or route state.

## Session store decision, HQ4

Use one `AsyncConnectionPool` and one `SessionWriter` commit implementation. Replace the single tailer poll loop with bounded dispatch.

Proposed shape:

- `SharedTailerDispatcher` owns the cursor registry currently inside `api/src/transport_matters/index/tailer.py::TranscriptTailer`.
- Each session cursor has a per-session queue and sequence guard.
- A small worker pool, default 8, polls or processes cursors. A run with a slow write backs up its own queue first.
- Workers call shared `SessionWriter.submit_blocking`, which schedules async commits on the API loop and uses the shared pool.
- Pool max remains configured by `Settings.session_pool_max_size`, currently loaded by `api/src/transport_matters/session/pool.py::create_async_pool`.
- Add per-session backoff and dead letter handling through the existing `SessionWriter.quarantine_window_blocking` path.

Ordering guarantee:

- Preserve ordering within each native session id.
- No global ordering guarantee across runs. Current storage has no such guarantee, and the product does not need one.

Backpressure:

- Bounded queue per session.
- If a queue fills, emit a run scoped warning event and slow that run's tailing. Do not block all other cursors.
- Commit concurrency is bounded by the DB pool and the worker count.

## Failure and crash model, HQ5

### Mode mutation failure

The binding stays `pending`. The manager restores the previous mode list, removes the binding, and returns a typed spawn error. No client is started.

### Unmapped flow

Return 502 and emit a run independent proxy health alert. Do not guess. A wrong binding can leak another run's wire and transcript data.

### Shared Master task crash inside a live API process

1. Mark manager unhealthy and emit `proxy_restart` to every active run.
2. Drop live paused flows with a `proxy_restarted` reason because live `HTTPFlow` objects are invalid.
3. Start a new `DumpMaster` with the current active mode list.
4. Wait for every active binding listener to pass readiness.
5. Mark manager healthy and emit `proxy_binding_state` for each restored binding.
6. If restore fails, mark affected runs failed through `RunManager` and terminate their clients.

In-flight HTTP requests and websocket frames are not guaranteed to survive Master restart. The run may survive if the CLI process remains alive and retries or sends a later turn.

### API process restart

Tier 2 does not make runs survive API restart. Current runs are process resident, and `api/src/transport_matters/main.py::lifespan` closes `RunManager` on shutdown. Surviving API restart would require external PTY ownership, durable run registry, and client reattach semantics. That belongs in a separate lifecycle design.

### Database outage

Run spawn keeps the existing session store preflight behavior from `api/src/transport_matters/run_manager.py::RunManager._prepare_request`. Existing active runs continue proxying if the session store fails after spawn, but tailer queues apply backpressure and emit run scoped warnings. If a queue exceeds its hard limit, mark transcript capture degraded for that run and surface it in `RunView.proxy` or a sibling health field.

### Event loop saturation

Embedding mitmproxy in the API process creates one event loop for routes, proxy hooks, pause events, and DB scheduling. Guardrails:

- No blocking disk or subprocess calls in mitmproxy hooks.
- Token counting remains async and timeout bounded.
- Tailer work uses worker dispatch.
- Mode mutation is serialized and rare.
- Add loop lag metrics and a health route field before load testing.

## Migration plan

Each slice is independently reviewable. Behavior preserving slices come first. The final cutover deletes the per-run `mitmdump` process path for API managed captured runs.

1. **Binding context refactor.** Introduce `ProxyRunBinding` and pass run id and storage explicitly through handlers, recorders, pause, and Codex exchange code while still running one `mitmdump` process per run. Tests assert current behavior is unchanged. This removes most `get_settings().run_id` usage from addon paths.
2. **Run scoped storage reads.** Move exchange and breakpoint API reads to `/v1/runs/{runId}/...` and resolve storage from run metadata. Keep old routes only inside the same commit if needed for frontend migration, then delete them before slice completion.
3. **Run scoped breakpoint state.** Replace global breakpoint state with `RunBreakpointState`. With one run per process this is behavior preserving, but it proves route and handler signatures.
4. **Run event broker.** Replace global SSE broadcast with run scoped broker and migrate frontend URLs in `www/src/api.ts` and `www/src/hooks/useExchangeStream.ts`.
5. **Tailer dispatcher.** Replace the single tailer thread with shared pool plus bounded dispatch. Keep one process per run until this proves 50 cursor behavior.
6. **Embedded Master manager.** Add `SharedProxyManager` and an embedded `DumpMaster` behind tests. Prove runtime add, remove, empty mode behavior, and Codex `regular@127.0.0.1:{port}` mutation.
7. **Addon demux.** Add `SharedProxyAddon` and flow resolution by listen port. Tests create two bindings and prove request, response, websocket, breakpoint, and storage writes cannot cross runs.
8. **RunManager integration.** Change `prepare_captured_run` for API managed runs so it registers a shared proxy binding instead of calling `api/src/transport_matters/cli/runner.py::start_prepared_proxy`. Keep Tier 1 admission. Rollback tests cover every failure point.
9. **Cutover delete.** Remove the per-run `mitmdump` supervisor ownership from API managed captured runs. `CapturedRunLease.close` no longer calls `ProcessSupervisor.terminate_all` for proxy processes. Delete dead tests and dead helpers rather than leaving parallel implementations.
10. **Load and road test.** Run 50 captured runs with mixed Claude and Codex, per-run breakpoint pause and release, transcript ingestion, and teardown churn.

Standalone CLI embedded launch can move onto the same manager in a later cutover if the product still needs that path. This proposal's no-parallel rule applies to API managed captured runs, which are the 50 run scaling target.

## Test strategy

### Unit and integration tests

- `api/src/transport_matters/shared_proxy/test_manager.py`: runtime mode add, remove, readiness polling, rollback, restart, empty mode or reserved mode behavior.
- `api/src/transport_matters/shared_proxy/test_demux.py`: primary demux by `proxy_mode.custom_listen_port`, fallback to `sockname[1]`, mismatch fails closed, unmapped flow returns 502.
- `api/src/transport_matters/test_addon_runtime.py`: shared core builds one HTTP client, token counter, writer, and dispatcher; binding registration creates per-run storage and cursor data.
- `api/src/transport_matters/api/v1/test_breakpoint.py`: two run ids can arm independently; releasing run A cannot release run B; canvas style API route unblocks addon pause in process.
- `api/src/transport_matters/api/v1/test_run_routes.py` and `test_run_routes_launch.py`: spawn rollback for mode mutation failure, readiness timeout, cursor registration failure, PTY spawn failure, and idempotency.
- `api/src/transport_matters/index/test_tailer.py`: one slow cursor does not delay another cursor beyond the dispatcher budget.
- `api/src/transport_matters/session/test_ingest.py`: per-session ordering remains stable under concurrent dispatcher workers.
- `www/src/api.test.ts`: all breakpoint and exchange routes include run id.
- `www/src/hooks/useExchangeStream.source.test.tsx`: EventSource opens `/v1/runs/{runId}/stream`.

### Contract tests

- Demux correctness is the core contract: two active bindings, same provider, same model, simultaneous requests, distinct storage roots, distinct run ids, no event leakage.
- Breakpoint contract: two runs armed; first outbound request for each pauses independently; release for run A only unblocks run A.
- Codex websocket contract: later incremental turn pauses on the same binding and persists to the same run.
- Mode mutation readiness: a route is considered active only after the listener accepts a probe; deregister is complete only after the listener refuses new connections.

### Load tests

- 50 run spawn burst through `POST /v1/runs` with Tier 1 admission enabled.
- 50 active run steady state with one shared Master, one session pool, and dispatcher workers.
- 50 run teardown churn while new runs spawn.
- One poisoned transcript cursor and 49 healthy cursors. Healthy cursors must continue within the target polling interval.
- Shared Master restart with 10 active bindings. New listeners must recover or affected runs must fail with typed errors.

### Gates

Use repo recipes, not hand rolled equivalents:

```bash
cd api && just check && just test
just www check && just www test && just www build
```

Add focused inner-loop commands as needed, but they do not replace the gates.

## Security considerations

- Listeners bind only to `127.0.0.1`.
- Trusted Host and explicit CORS remain from `api/src/transport_matters/main.py::create_app`.
- Mutating run routes require Origin validation.
- Run id path values are authorization boundaries inside the local app. Every flow mutation verifies both `runId` and `flowId`.
- Unmapped flow errors include no raw payload, no headers, and no auth material.
- Auth headers stay per flow or per binding. The current process global recent auth cache must be removed or scoped.
- The mode registry is the critical isolation primitive. Register binding before listener exposure; remove listener before deleting binding.
- Never reuse a listen port until deregister has observed listener close and binding removal.

## Performance notes

Expected improvements:

- One mitmproxy interpreter instead of one per run.
- One shared Postgres pool instead of one pool per active proxy process.
- Spawn path pays mode mutation and readiness, not process import and proxy boot.

Targets:

- Flow binding lookup: O(1), no I/O.
- Mode mutation readiness: measured and emitted per registration.
- API loop lag: measured under 50 run load.
- Writer pool utilization under 80 percent at p95 load.
- No global breakpoint serializer across runs.

Implementation notes:

- The mode mutation lock is held only around mode list update and readiness bookkeeping, never around live flow handling.
- Tailer dispatcher worker count and DB pool max are separate knobs.
- Token counting uses the shared HTTP client and must retain existing timeouts.

## Risks and open questions

1. **Codex regular mode mutation.** Reverse mode mutation is proven. `regular@127.0.0.1:{port}` must be proven before Codex cutover.
2. **Empty mode list.** The spike did not prove `mode=[]`. Either prove it or keep an internal reserved mode.
3. **Event loop contention.** Embedding the Master can affect API latency. Mitigate with metrics, no blocking hooks, and load tests.
4. **Direct CLI embedded path.** API managed captured runs are the scaling target. Moving standalone `transport-matters claude/codex` onto the shared manager needs a separate cutover if that path remains active.
5. **Master crash semantics.** Active in-flight flows cannot be guaranteed across Master restart. The design preserves run processes when possible, not individual wire exchanges.
6. **Storage route migration.** Frontend code currently assumes global exchange routes. The run scoped API migration must be completed in the same slice that removes global storage in shared mode.
7. **File size pressure.** `api/src/transport_matters/run_manager.py` is close to the project limit. Shared proxy implementation must live in new modules or refactor existing code before adding significant lines.
