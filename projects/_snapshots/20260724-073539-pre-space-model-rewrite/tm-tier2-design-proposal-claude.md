---
title: "Tier 2 shared-proxy: implementation-ready design"
type: design
tags: [transport-matters, performance, proxy, mitmproxy, addon, breakpoint, session-store, scaling, tier-2]
summary: "One embedded mitmproxy Master inside the API process serving all captured runs, demuxed by listen port to a per-run binding. Replaces 50 mitmdump processes / 50 pools / per-process identity with one shared core plus cheap per-run bindings, and gives canvas runs working breakpoints for the first time."
status: proposed
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
depends_on: ~/.mdx/projects/tm-tier2-spike-mitmproxy-modes.md, ~/.mdx/projects/tm-tier2-seams-and-questions.md, ~/.mdx/projects/tm-perf-tier2-shared-proxy-design.md
---

# Tier 2 shared-proxy: implementation-ready design

Design only. No code edits. Every structural claim cites `file::symbol`. Paths relative to
`api/src/transport_matters/` unless noted. Builds on the spike (HQ1/HQ2 settled) and the seams map;
does not relitigate them.

## 0. Settled inputs (do not re-derive)

- **HQ1 = incremental register/deregister on ONE long-lived shared mitmproxy.** Spike proved
  `master.options.update(mode=[...])` adds and removes `reverse:UPSTREAM@127.0.0.1:PORT` listeners at
  runtime on a live `mitmproxy.tools.dump.DumpMaster`; untouched listeners keep serving; the update is
  async and readiness must be polled (`proxyserver.servers.is_updating` plus a listener probe).
- **HQ2 = listen-port demux.** Flow to run key is `flow.client_conn.proxy_mode.custom_listen_port`
  (primary) with `flow.client_conn.sockname[1]` as the concrete socket fallback. Both matched on every
  flow in the spike. This signal is unused in the code today (grep-confirmed in the seams map).

## 1. The three hard forks, resolved

### HQ3 (irreversible) = EMBEDDED Master in the API process

**Position: embed mitmproxy's `DumpMaster` inside the API process.** Do not run a `mitmdump`
subprocess plus a cross-process control channel.

**Why this is forced, not preferred.** The product's differentiating control plane (breakpoint
arm/release, override, re-audit, SSE) depends on two objects that cannot leave a process: the live
`mitmproxy.http.HTTPFlow` and the live `asyncio.Event` held in `breakpoint.py::PausedFlow` (`:24-26`).
Release works by `pf.event.set()` (`breakpoint.py::release:155`) waking the addon coroutine that is
`await`-ing inside `pause_session.py::_run_pause`. That wake only reaches the coroutine when the route
and the addon share an address space. This is exactly why canvas runs have **no working breakpoint
today**: a canvas run is `web_runtime="external"` (seams §7), so its `mitmdump` subprocess runs the
addon while `/api/breakpoint/*` is served by the separate API process. The two `breakpoint.py` module
states are different processes; the Event set in the API never reaches the addon in the subprocess.

A subprocess design for Tier 2 reproduces that break at scale: the API would need a brand-new IPC
channel to ship arm/release/inspect/re-audit commands into the proxy, the live flow and Event still
cannot cross the boundary, and SSE would have to be tunneled back. Embedding co-locates the addon and
the routes again, so:

- **Canvas gains working breakpoints for the first time.** This is a feature win, not only a refactor.
- The shared core (`TokenCounter`, `OverrideStore`, Postgres pool, tailer registry, SSE broadcaster)
  is shared by reference in one heap, no serialization.
- No new cross-process protocol to design, version, and secure.

**Throughput/isolation consequence and the loop-placement knob.** Embedding raises one real risk:
mitmproxy terminates and re-encrypts TLS for every connection, so 50 concurrent streamed LLM
responses are genuine single-core CPU. The mitigation is a **deployment knob, not a second
architecture**, because the control plane is written loop-agnostic from day one:

- Per-run control state (the paused registry, the override store) is guarded by `threading.Lock`,
  never `asyncio.Lock`, so it is safe to read from the addon and mutate from a route regardless of
  which loop each runs on.
- Every proxy-side wakeup goes through a stored `proxy_loop` reference:
  `proxy_loop.call_soon_threadsafe(pf.event.set)`. Every API-side SSE enqueue goes through a stored
  `api_loop` reference: `api_loop.call_soon_threadsafe(q.put_nowait, data)`.
- `call_soon_threadsafe` is valid even when both references point to the **same** loop. So the
  identical code runs in two deployment modes:
  - **Mode A (ship the cutover here): Master on the API event loop.** Simplest, zero behavior
    surprises, matches the spike exactly, canvas breakpoints work immediately.
  - **Mode B (flip the knob if load proves it): Master on a dedicated thread with its own event
    loop.** Isolates proxy TLS/parse CPU onto its own core so the latency-sensitive terminal
    WebSocket bridge and SSE on the API loop stay responsive.

Loop placement is reversible (a wiring choice in `SharedProxyManager.start`); the embedded-vs-subprocess
axis is the irreversible one, and it is embedded.

**Rejected alternatives.**
- *Subprocess + IPC control channel*: reintroduces the canvas breakpoint break, cannot pass the live
  flow/Event, requires a new protocol. Higher cost, strictly worse on the product's core feature.
- *Embedded but pinned to the API main loop with no marshaling abstraction*: works at low N, but
  bakes in single-loop coupling and makes Mode B a rewrite. The loop-agnostic primitives above cost
  almost nothing and keep the escape hatch open.

### HQ4 = ONE shared pool + ONE tailer registry, with sharded async commit dispatch

**Position: keep one shared Postgres pool, one shared `TranscriptTailer` registry, and one
`SessionWriter` loop, but replace the single blocking `submit_blocking` dispatch with a bounded async
commit queue drained by a small worker pool sharded by `session_id`.**

**Why.** The tailer is already a multi-session registry: `index/tailer.py::TranscriptTailer._cursors`
is `dict[str, TailCursor]` keyed by `session_id`, `register_session_cursor` registers idempotently and
`poll()` iterates every cursor (seams §6). One tailer holding cursors for all runs is the natural
shape; only the one-runtime-per-process accident kept it to a single run. Sharing the pool is the
entire point of Tier 2 (it removes the per-run pool ceiling). So the registry and the pool are
shared as-is.

The genuine hazard is head-of-line blocking, and it is precise: the **single tailer poll thread**
calls `session/writer.py::SessionWriter.submit_blocking`, which does
`asyncio.run_coroutine_threadsafe(self._commit_batch(batch), self._loop)` and blocks the poll thread up
to the 5s `_commit_timeout_s` (seams §6). A slow or poison session stalls polling for **all** runs.

Fix the dispatch, keep the sharing:

- The poll thread submits to a bounded per-shard `asyncio.Queue` via a fast enqueue, then moves on. It
  never blocks on a DB commit. If a shard queue is full, that **one** cursor is skipped this poll and
  retried next poll (per-run backpressure), so a backed-up session never stalls other cursors.
- N worker coroutines on the writer loop drain the shards. Shard by `hash(session_id) % N` so every
  session is pinned to one worker. This preserves the existing per-session atomic ordering (session
  upsert then ordered events in one transaction) and the existing per-session dead-lettering
  (`quarantine_window_blocking`), while letting other sessions proceed on other workers.
- Set `N <= session_pool_max_size` (`config.py:120`, default 10). At most N concurrent commits means
  at most N connections in use, so a single shared pool of size 10 with 8 workers never starves and
  needs no per-run reserve. This is the connection ceiling fix (one pool, not 50) made safe.

Failure isolation is already good (per-session dead-letter); this design keeps it and removes the
shared-thread head-of-line. **Rejected:** pure single shared writer (head-of-line at 50 runs);
per-run writer/tailer (re-creates 50 loops/threads and defeats the pooling that motivates Tier 2).

### HQ5 = ONE embedded Master, in-process supervised restart + re-register, runs stay process-resident

**Position: one shared embedded Master (not a pool of K). Supervise it and, on death, rebuild it and
re-register every live run from the binding registry. Runs do not survive an API restart, unchanged
from today.**

**Why one, not a pool.** Given HQ3 is embedded, a "pool of K proxies" would be K `DumpMaster` objects
in the **same** process sharing the same threads, so it buys zero failure isolation; the only way a
pool isolates blast radius is as separate processes, which is the subprocess design already rejected.
A pool only earns its complexity if a single Master cannot hold the listener count, and 50 reverse
listeners is just 50 asyncio servers, well inside mitmproxy's envelope (the spike ran multiple modes on
one Master with correct per-port attribution). So one Master, plus a fast restart story.

**Restart + re-register.** The binding registry is the source of truth and lives in API-process memory
(`SharedProxyManager`), not inside the Master. So recovery is cheap and needs no process spawn: a
supervisor task watches the Master run-task; on death it marks all bindings "reconnecting", constructs
a fresh `DumpMaster` with the full mode list rebuilt from the live registry, polls readiness, and
resumes. In-flight flows at crash time error out and clients retry (LLM clients retry on connection
reset); paused flows are lost and the operator re-arms. This is strictly better isolation than today
for the API itself, because in Mode B a Master-thread death does not take down the API loop.

**Process residency.** Keep runs process-resident. The client processes are PTYs owned by
`run_manager.py::RunManager`/`ManagedRun`; an API restart kills those clients regardless, so persisting
proxy routes across an API restart would point at dead clients. No value, so out of scope. Revisit only
if the product later detaches clients from the API lifecycle.

## 2. Component model

New module `shared_proxy.py` (layer: server; may import storage/breakpoint/session per the api DAG).

- **`SharedProxyManager`** lives on `app.state.shared_proxy`, sibling to `app.state.run_manager`
  (`main.py::lifespan:144`). Owns:
  - the embedded `DumpMaster` and its run-task, plus `proxy_loop` and (Mode B) the proxy thread;
  - the **binding registry**: `by_port: dict[int, RunBinding]` and `by_run_id: dict[str, RunBinding]`
    (two indexes, one object), guarded by a `threading.Lock`;
  - the **shared core**: one `httpx.AsyncClient` upstream, one `counting.py::TokenCounter`, one
    Postgres pool (`session/pool.py::create_async_pool`), one `index/tailer.py::TranscriptTailer`
    registry, the `override_state.py::OverrideStore` instance, the `broadcast.py` broadcaster;
  - `register(binding)`, `deregister(run_id)`, `resolve(flow) -> RunBinding | None`, `release(...)`,
    and the supervisor.
- **`RunBinding`** is the per-run object that replaces per-process identity (see §5). Cheap to create
  and destroy. Holds run identity, the per-run snapshot writer, the per-run breakpoint state, the
  per-run `recent_auth`, and references to the shared core.
- **Relation to `RunManager`.** `RunManager` keeps the run lifecycle, PTY, client process, and the
  lease (`captured_run_models.py::CapturedRunLease`, held on `run_manager.py::ManagedRun.lease`). What
  changes: the lease no longer owns a `ProcessSupervisor` for `mitmdump`. It owns a registration handle;
  `lease.close()` calls `shared_proxy.deregister(run_id)` for the proxy side and still terminates the
  **client** PTY. `RunManager` and `SharedProxyManager` are siblings on `app.state`; the lease bridges
  them. The Tier-1 admission semaphore in `run_manager.py::RunManager._spawn_new_admitted` is reused
  unchanged as front-door backpressure (and can be widened, since register-a-route is far cheaper than
  spawn-a-process).

## 3. Spawn flow (ordering, failure, rollback)

`run_routes.py::create_run` -> `RunManager.spawn` -> `_spawn_new` -> `_spawn_new_admitted` ->
`_prepare_request` -> `captured_run.py::prepare_captured_run`. Today `prepare_captured_run` ends in
`cli/runner.py::start_prepared_proxy` -> `sup.spawn("mitmdump", ...)` + `cli/net.py::wait_for_port_ready`.
Tier 2 replaces the spawn tail with registration on the shared proxy. Ordered steps with per-step
rollback:

1. **Admit.** Acquire the existing admission semaphore (`_spawn_new_admitted`). Rollback: release on
   any failure below.
2. **Allocate loopback port.** `cli/ports.py::allocate_port_pair` (canvas already discards the web
   port; for canvas allocate the proxy port only). Rollback: free the port.
3. **Build and register the `RunBinding` BEFORE exposing the mode.** Insert into `by_port[port]` and
   `by_run_id[run_id]` under the registry lock. Registering the binding first closes the race where the
   new listener accepts a connection before a binding exists (an unmapped flow). Rollback: remove from
   both indexes.
4. **Register the reverse (or Codex `regular`) mode.** On the proxy loop:
   `proxy_loop.call_soon_threadsafe(self._apply_modes, new_mode_list)` where the manager owns the full
   mode list and appends `reverse:{upstream}@127.0.0.1:{port}`. Wait for readiness: poll
   `proxyserver.servers.is_updating == False` then probe that the listener accepts (spike caveat:
   `options.update` is async). Mode mutations are serialized through the proxy loop (single writer)
   because each update replaces the whole list. Rollback: re-apply the mode list without this port.
5. **Register the owned-session cursor** in the shared tailer registry (per-run cursor + per-run
   snapshot writer), mirroring `addon_runtime.py::_register_owned_cursor`. Rollback: deregister the
   cursor.
6. **Spawn the client process** (PTY) with the unchanged contract
   `ANTHROPIC_BASE_URL=http://127.0.0.1:{port}` (`captured_claude.py::build_claude_captured_invocation`).
   Rollback: terminate the client PTY.

Ordering rationale: binding before mode (no unmapped flow), mode-ready before client spawn (the
client's first request must hit a live listener), cursor before client (first transcript lines are
tailed). Every rollback step is idempotent so a mid-sequence failure unwinds cleanly. Reuse the Tier-1
typed retryable-timeout semantics around step 4 readiness in place of `wait_for_port_ready`.

## 4. Teardown flow (deregister, never kill)

`RunManager.terminate` -> `_teardown_run` -> `lease.close` (today `supervisor.terminate_all()`). The
failure path `_rollback_post_prepare` runs the same `lease.close`. Tier 2 `lease.close` for the proxy
side becomes:

1. **Deregister the mode first.** Re-apply the mode list without this port (proxy loop) and wait for
   the listener to close. New connections stop immediately.
2. **Drain in-flight.** Bounded wait for flows tagged with this `run_id` to finish, then proceed. The
   client PTY is being torn down too, so in-flight requests error anyway; do not block forever.
3. **Per-run shutdown only.** Clear this run's breakpoint state (release/drop only this run's paused
   flows), deregister this run's tailer cursors (flush snapshot), drop this run's `recent_auth`.
   **Never** `breakpoint.py::clear_all` (drops every run's paused flows), **never** the shared
   `terminate_all()`, **never** close the shared httpx client / pool / tailer.
4. **Remove the binding** from `by_port` and `by_run_id` under the registry lock; free the port.
5. The **client PTY** is still terminated by the lease/`RunManager` exactly as today.

This is the inverse of spawn and isolates teardown to one run's footprint.

## 5. Run-identity replacement (process env -> per-run binding)

**Today:** the CLI writes `TRANSPORT_MATTERS_*` env (`launch_environment.py::build_launch_env`) and the
addon reads identity once via the `@lru_cache`'d `config.py::get_settings` (`:207`) ->
`Settings.load()`. The cache *is* the per-run identity. That breaks first under one shared process
(one cache, many runs). Identity must be threaded as a `RunBinding` resolved from the flow on every
hook.

`RunBinding` fields (sourced from `Settings`, seams §3): `run_id` (`config.py:79`), `storage_dir`/
`storage_root` (`:74`), `upstream`, `cwd` (`:87`), `cli` (`:91`), `owned_native_session_id` (`:96`),
`owned_source_descriptor` (`:97`), `launch_fields` (`:98`), `agent_home_dir` (`:103`),
`breakpoint_skip_models`, `breakpoint_timeout_s`, the per-run snapshot writer, per-run
`BreakpointState`, per-run `recent_auth`, and references to the shared core.

**Read sites that move from `get_settings()` to the resolved binding (move list):**

| Read site | Today | Tier 2 |
|---|---|---|
| `addon_runtime.py::load_capture_runtime` `settings.storage_dir` (`:162`) | process env | `binding.storage_dir` |
| `addon_runtime.py::_launch_run_context` run_id/cwd/cli/owned_native_session_id/agent_home_dir (`:68-84`) | process env | binding fields |
| `addon_runtime.py::_register_owned_cursor` launch_fields/owned_source_descriptor (`:99-103`) | process env | binding fields |
| `addon_handlers.py::handle_http_request` `get_settings().run_id` (`:96`) | process env | `binding.run_id` |
| `addon_handlers.py::handle_codex_websocket_message` `get_settings().run_id` (`:210`) | process env | `binding.run_id` |
| `addon_handlers.py::_should_skip_breakpoint` `get_settings().breakpoint_skip_models` (`:62-64`) | process env | `binding.breakpoint_skip_models` |
| `pause_session.py::_flow_track_fields` `get_settings().run_id` (`:210`) | process env | `binding.run_id` |
| `pause_session.py::_run_pause` `get_settings().breakpoint_timeout_s` (`:260-262`) | process env | `binding.breakpoint_timeout_s` |
| project-scoped cwd / `/api/v1/meta` `Path.cwd` fallback (`config.py:80-87`) | process cwd | `binding.cwd`, with a process-global default retained for non-run routes |

**Resolution and stability.** The addon resolves the binding by listen port at the earliest hook
(`request`, `websocket_start`) via `flow.client_conn.proxy_mode.custom_listen_port`, falling back to
`flow.client_conn.sockname[1]`. It stamps `run_id` onto `flow.metadata` (the existing typed-state
channel, `flow_state.py` already stores under `transport_matters_*` keys). Later hooks
(`response`, `websocket_message/end`, `error`) read `run_id` from metadata first and re-resolve the
binding via `by_run_id`, with port resolution as fallback. This makes a flow's attribution stable for
its whole lifetime, even if its mode is being deregistered. The hook signatures change from passing
`self._runtime.token_counter` to passing the resolved `binding` (the binding carries the shared
`token_counter` plus per-run fields), so `addon.py::TransportMattersAddon.request/response/websocket_*`
each call `resolve(flow)` first.

**`get_settings()` stays** for genuinely process-global config (DB URL, log config, pool sizes,
defaults). Only per-run identity moves to the binding.

## 6. Breakpoint / override / counting / SSE made per-run

**Breakpoint.** Move `breakpoint.py` module globals to a per-run `BreakpointState` held on the binding:
`_mode` (`:52`) -> per-run mode; `_paused` (`:53`) -> per-run `dict[flow_id, PausedFlow]`; the global
`_pause_serializer` (`:58`) -> **per-run** serializer. The per-run serializer is essential: today it is
one process-wide lock held across pause+await+pop (`breakpoint.py::pause_serializer:79-86`,
`pause_session.py::_run_pause:232`), so a single shared serializer would make one run's pause block
**every** run's outbound request. Critically, the per-run paused dict uses a `threading.Lock` (not the
current `asyncio.Lock` at `:54`), because the route layer and the addon may run on different loops
(HQ3 Mode B); release sets the Event via `proxy_loop.call_soon_threadsafe(pf.event.set)` rather than
the current direct `pf.event.set()` (`breakpoint.py::release:155`). Under Mode A that marshaling
collapses to a same-loop scheduled callback, so one code path serves both modes.

**Routes and frontend become run-scoped.** Today the router mounts globally
(`api/v1/router.py:19`, `prefix="/breakpoint"`) and the frontend calls a single global URL with no run
id (`www/src/api.ts:267` `/api/breakpoint/arm`, `:276` `/release/{flowId}`). Tier 2:
`/runs/{run_id}/breakpoint/{arm,disarm,status,release,drop,re-audit,paused}` resolve the run's binding
and act on its `BreakpointState`; `www/src/api.ts` URLs become run-scoped. `breakpoint_routes.py`
handlers take `run_id`, look up `shared_proxy.by_run_id[run_id]`, and operate on that state. Re-audit
(`breakpoint_routes.py::_recount_tokens`) already reads `pf.auth_headers` (per-flow, safe); its
`count_tokens` call uses the shared `TokenCounter`, and under Mode B is marshaled to the proxy loop
(`run_coroutine_threadsafe(counter.count(...), proxy_loop)`).

**Counting contamination fix.** `counting.py::_recent_auth` (`:161`) is overwritten on every request
from any run (`addon_handlers.py:80`). In one process that is cross-run contamination. Move it onto the
binding (`binding.recent_auth`). `counting.py::_counter` (`:153`, `set_counter`) stays a shared value
(the upstream client and counter are identical for all Anthropic runs, seams §2).

**Override store.** `override_state.py::_store = OverrideStore()` (`:106`) is already scoped by
`(run_id, track_id)` via `scope_from_params`, so the instance is shareable. Keep one shared store; it
is read in the addon (proxy loop) and mutated by routes (API loop), so guard access with a
`threading.Lock` (loop-agnostic). No per-run instance needed.

**SSE.** Keep one `broadcast.py` broadcaster. `emit()` (`broadcast.py:36-46`) currently does
`q.put_nowait(data)` directly on subscriber queues created by SSE routes on the API loop. When emitted
from the proxy loop (Mode B), that is cross-loop and unsafe, so route every put through
`api_loop.call_soon_threadsafe(q.put_nowait, data)`. Events already carry `run_id`
(`pause_session.py::_paused_event_payload:194`). Make the subscription run-scoped (subscribe with a
`run_id` filter, or expose `/runs/{run_id}/events`) so a canvas pane sees only its own run's events
instead of every run's stream.

**Canvas result.** Because the addon and the breakpoint routes are now in one process (HQ3), the
release Event reaches the addon coroutine, so **canvas runs get working breakpoints**, including later
Codex turns which re-enter the pause path per incremental websocket frame
(`pause_session.py::handle_websocket_breakpoint`, `rewrite_codex_provisional_exchange(force_replay=True)`).

## 7. Session store (HQ4 realized)

One shared pool, one tailer registry, one writer loop with sharded async commit dispatch (§1 HQ4).
Concretely:

- `addon_runtime.py::load_capture_runtime` splits: the shared core (httpx, `TokenCounter`,
  `create_async_pool`, `SessionWriter`, `TranscriptTailer`) is built **once** by `SharedProxyManager`
  at startup; per-run it only builds the snapshot writer and registers the owned cursor.
- `session_store_preflight.py::check_session_store` runs **once** at shared-proxy startup, not per run
  (it is already Tier-1 off-loop and cached; this makes it a single call).
- Add a cursor **deregister** path to `TranscriptTailer` (remove by `session_id`) so run teardown drops
  only its cursors; today registration is idempotent setdefault with no symmetric removal (seams §6).
- Replace `SessionWriter.submit_blocking`'s blocking `run_coroutine_threadsafe(...).result(timeout=5)`
  with a bounded per-shard `asyncio.Queue` and N worker coroutines on the writer loop, sharded by
  `session_id`, `N <= session_pool_max_size`. Per-session ordering and per-session dead-lettering are
  unchanged; cross-run head-of-line is removed; the pool is never over-subscribed.

Failure isolation: poison events still dead-letter per session; a slow session backs up only its shard
and its own tailer cursor (skipped-and-retried), not the whole tailer. Backpressure is explicit and
per-run instead of a hidden 5s stall of the single poll thread.

## 8. Failure / crash model (HQ5 realized)

- **Master death:** the supervisor rebuilds a fresh `DumpMaster` from the live binding registry's full
  mode list and re-registers all runs (no process spawn; registry is in API memory). In-flight flows
  error and clients retry; paused flows are lost and the operator re-arms.
- **One-run failure:** a bad write dead-letters (per session); a bad flow is killed (unmapped handling,
  §9); neither touches other runs or the shared core.
- **API restart:** runs do not survive (process-resident, as today); client PTYs die with the API, so
  route persistence would be pointless.
- **Mode B isolation bonus:** a proxy-thread/loop death does not take down the API loop; the API can
  observe and rebuild.

## 9. Addon flow->run resolution per hook and unmapped flows

Each hook resolves the binding (§5): `request`/`websocket_start` by listen port then stamp `run_id` on
`flow.metadata`; `response`/`websocket_message`/`websocket_end`/`error` by `run_id` from metadata then
`by_run_id`, port as fallback.

**Unmapped flow (fail safe, never guess).** If a flow arrives on a port with no binding (race window
during deregister, or a stale socket), the addon must **not** fall through to any default or
last-seen binding; that is the cross-contamination failure the whole demux contract exists to prevent.
Kill the flow (`flow.kill()`) or return 503, increment an `unmapped_flow` metric, and log with the
port. Spawn registers the binding before the mode (§3) and teardown removes the mode before the binding
(§4), so the only unmapped flows are genuinely orphaned and are correctly refused.

## 10. Migration plan (ordered, independently shippable, delete at cutover)

Behavior-preserving refactors first; the cutover deletes the per-run-process path with no parallel
implementations (DRY).

1. **Slice A: shared-core / per-run-binding split.** Factor `addon_runtime.py::load_capture_runtime`
   into `SharedCore` + `RunBinding`; route identity through the binding instead of `get_settings()`.
   Still one `mitmdump` per run, so behavior is unchanged and existing tests cover it. De-risks the
   identity move in isolation.
2. **Slice B: addon demux resolution.** `TransportMattersAddon` resolves the binding from the listen
   port and stamps/reads `run_id` on `flow.metadata`. Unit-test two bindings on two ports in one addon
   instance with synthetic flows (still subprocess per run in production; the test proves demux).
3. **Slice C: per-run control state.** Move `breakpoint.py` globals to per-run `BreakpointState`, move
   `counting.py::_recent_auth` onto the binding, switch the paused dict to `threading.Lock` plus
   marshaled `event.set`, make routes (`breakpoint_routes.py`) and `www/src/api.ts` run-scoped. Under
   subprocess-per-run, per-run equals per-process, so behavior is preserved and CLI/embedded breakpoint
   still works. Shippable.
4. **Slice D (cutover): `SharedProxyManager` + embedded Master.** Mount on `app.state.shared_proxy`
   (`main.py::lifespan`), Mode A (API loop). `prepare_captured_run` calls `shared_proxy.register` and
   teardown calls `deregister` instead of `sup.spawn`/`terminate_all`. Wire cross-loop release and SSE.
   Add the supervisor + re-register. **Canvas breakpoints start working here.** Irreversible step;
   adversarial review + real load test gate the merge.
5. **Slice E: sharded session-store dispatch.** Replace `SessionWriter.submit_blocking` blocking
   dispatch with the per-shard queue + worker pool; preflight once; add cursor deregister. Independent
   of D's topology but its payoff lands once many runs share one writer (after D).
6. **Slice F: delete the old path.** Remove `cli/runner.py::start_prepared_proxy` per-run spawn,
   per-run pool creation, and the per-run usage of `cli/launch_runtime.py::build_mitmdump_argv`
   (repurpose only for the single Master's initial args). Drop the `ProcessSupervisor` for `mitmdump`
   from `CapturedRunLease` (keep it for the client PTY). No parallel implementations remain.

Mode B (dedicated proxy thread/loop) is a post-cutover knob flip in `SharedProxyManager.start`, gated
on the load test, requiring no code change beyond wiring because the control plane is already
loop-agnostic.

## 11. Test strategy

- **Demux correctness (the core contract).** Unit-feed synthetic flows with distinct
  `client_conn.proxy_mode.custom_listen_port` / `sockname[1]` into one addon holding N bindings; assert
  each flow's capture, transcript, and breakpoint route to the right `run_id`; assert an unmapped-port
  flow is killed/503'd and **never** attributed. Property test: no cross-attribution under interleaving.
- **Mode-mutation readiness (in-repo regression of the spike).** Start an embedded Master, register a
  mode, poll `proxyserver.servers.is_updating` then probe accept; deregister and confirm refused;
  assert untouched listeners keep serving. Add a **churn** test: many rapid concurrent register/
  deregister cycles (each rewrites the whole mode list) to prove serialized mode mutation drops no
  listener.
- **Per-run breakpoint.** Two runs; arm only run A; drive a request through A (pauses) and B (passes);
  release A via its run-scoped route and assert the cross-loop Event wakes A; assert B never paused and
  A's pause never delayed B (proves the per-run serializer). End-to-end canvas breakpoint via the
  embedded path.
- **50-run load.** Register 50 bindings, drive concurrent streamed traffic; assert zero cross-run
  contamination, p95 register latency, terminal-WS echo latency under proxy load (the Mode A vs Mode B
  decision metric), session writer with no head-of-line (one slow/poison session does not stall
  others), and pool usage `<= max_size`.
- **Restart / re-register.** Kill the Master run-task; assert the supervisor rebuilds and re-registers
  all live bindings from the registry; in-flight errors; new requests succeed.
- **Teardown isolation.** Deregister run A while run B is active; assert B's flows, breakpoint state,
  and cursors are untouched, the port is freed, and the shared core is intact.

## 12. Risks and open questions I cannot close here

- **Codex (explicit-proxy) coexistence in one Master.** The spike proved runtime mutation for
  `reverse:` modes (Claude). Codex launches an explicit HTTPS proxy
  (`codex/transport.py::is_codex_websocket_flow` / `is_codex_http_responses_flow`; CLAUDE.md: "Codex
  through an explicit HTTPS proxy"). The plan is a `regular@127.0.0.1:{port}` mode per Codex run
  alongside Claude reverse modes, demuxed by the same listen port. **Open:** confirm runtime
  `options.update` add/remove works for `regular`/upstream modes as it does for reverse, and that
  `flow.client_conn.proxy_mode.custom_listen_port` is populated for explicit-proxy flows. Needs a short
  Codex-mode spike before Slice D.
- **Single-core saturation under 50 concurrent TLS-terminated streams.** Drives the Mode A vs Mode B
  call; only the load test can close it. Mitigation regardless: offload any blocking work in addon
  hooks (disk writes via `asyncio.to_thread`; DB writes already thread-bridged; token counting already
  async httpx) so neither loop blocks.
- **`options.update` under high churn.** 50 rapid spawns each rewrite the whole mode list. The design
  serializes mutations through the proxy loop, but whether very rapid churn ever transiently drops a
  listener is unverified; the churn test above is the gate. A coalescing/debounce of mode updates is a
  fallback if churn shows races.
- **Readiness without a deterministic ack.** `is_updating` plus a probe is the spike's recipe; there is
  no explicit "listener ready" callback. If probes prove flaky under load, an explicit control
  acknowledgement may be needed.
- **Shared CA / confdir across upstreams.** Today each `mitmdump` has its own confdir
  (`cli/launch_runtime.py`). One shared Master needs one confdir/CA covering both Anthropic and ChatGPT
  upstreams. Reverse modes per port make this clean, but confirm cert generation for differing upstream
  hosts within one Master.
- **fd ceiling concentrates on the API process.** All listeners, client PTYs, and sockets now live in
  one process. Orthogonal but newly concentrated; raise `ulimit` for the API parent.
