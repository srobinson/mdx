---
title: "Tier 2 shared-proxy: seams + hard questions (grounding research)"
type: research
tags: [transport-matters, performance, proxy, addon, captured-run, scaling, tier-2, breakpoint, session-store]
summary: "Today every captured run is its own mitmdump process; run identity is read once from process env (get_settings @lru_cache), and the breakpoint/override/counting/SSE control plane is process-global single-run state. This maps every seam a shared multi-mode proxy must convert from per-process to per-run, and the 5 design forks the proposals must each take a position on."
status: active
source: codebase-analyst
confidence: high
created: 2026-06-16
updated: 2026-06-16
depends_on: ~/.mdx/projects/tm-perf-tier2-shared-proxy-design.md, ~/.mdx/projects/tm-perf-proxy-scaling--brainstorm.md
---

# Tier 2 shared-proxy: seams + hard questions

Investigation only. No code modified. Every claim cites `file::symbol` (+ line). Paths relative to
`api/src/transport_matters/` unless noted.

**The single structural fact that frames everything:** a captured run today is one OS process
(`mitmdump`) whose run identity is read **once, from process environment**, via the `@lru_cache`'d
`config.py::get_settings` (`config.py:207`). The addon never reads anything per-flow to attribute a
request to a run (`addon_handlers.py` reads `flow.request.path/headers`, `flow.id`, `flow.metadata`,
`flow.websocket` only — **never** `flow.client_conn`/`server_conn`/listen port; grep-confirmed empty).
A shared proxy must replace *process identity* with *per-flow identity* and *per-process singletons*
with *per-run bindings*, everywhere below.

---

## 1. Flow → run attribution

**Today (one runtime per process).** The addon holds one process-global runtime:
`addon.py::TransportMattersAddon.__init__` sets `self._runtime = None`; `.load()` calls
`addon_runtime.py::load_runtime()` once (`addon.py:58-59`); `addons = [TransportMattersAddon()]`
(`addon.py:95`). Each hook passes only `self._runtime.token_counter` into the handlers — no flow→run
resolution:

- `request(flow)` → `addon_handlers.py::handle_http_request(flow, token_counter)` (`addon.py:61-65`).
- `response(flow)` → `addon_handlers.py::handle_response` (`addon.py:80-84`).
- `websocket_start/message/end(flow)` → `addon_handlers.py::log_websocket_start` /
  `handle_codex_websocket_message` / `handle_codex_websocket_end` (`addon.py:71-78`).
- `error(flow)` → reads `flow_state.py::get_request_flow_state` only (`addon.py:86-92`).

What each hook reads **from the flow**: `flow.request.path` (`addon_handlers.py:72`),
`flow.request.headers` (`:80`, auth snapshot via `counting.py::relevant_auth_headers`), `flow.id`
(logging + `flow_state` keying), `flow.metadata` (typed state, `flow_state.py::capture_request_flow_state`
stores under `transport_matters_*` keys, `:99-108`), `flow.request.set_text` (`:135`),
`flow.websocket` (`:177`), `flow.response` (`handle_response`). **Run id is NOT on the flow** — it comes
from `get_settings().run_id` (`addon_handlers.py:96`, `:210`; `pause_session.py::_flow_track_fields:210`).

**Per-flow signal for a shared addon.** Each run already gets a unique loopback `proxy_port`
(`cli/ports.py::allocate_port_pair`, bound by the run's `mitmdump --listen-port {proxy_port}`,
`cli/launch_runtime.py::build_mitmdump_argv`). The deterministic demux key is therefore **the listen
port the flow arrived on** — `flow.client_conn.sockname` (the proxy-side local socket that accepted the
client). This is **unused today** (grep-confirmed). The design's proposed mapping is
`listen_port → per-run binding`. Watch: this is the product's core correctness contract — a wrong port
→ run mapping cross-contaminates wire capture/transcript across runs.

---

## 2. Shared-core vs strictly-per-run (exhaustive from `addon_runtime.py`)

`load_runtime()` (`addon_runtime.py:260-264`) = `get_settings()` (per-process env) +
`load_capture_runtime(settings)` + `start_web_runtime(settings)` only if `web_runtime == "embedded"`.
`load_capture_runtime` (`:160-243`) builds, in order:

| Built | Symbol / line | Classification |
|---|---|---|
| `init_storage(root=settings.storage_dir)` + `DiskStorageBackend.root` | `:162-170` | **Per-run** (storage_dir is per-run) |
| `httpx.AsyncClient(base_url="https://api.anthropic.com", trust_env=False)` | `:172-176` | **Shareable** (upstream is identical for all Anthropic runs) |
| `TokenCounter(http_client)` | `:177` | **Shareable** |
| `set_counter(token_counter)` | `:178` | **Process-global singleton** — `counting.py::_counter` (`counting.py:153`). Shareable as a value, but it is a *global*, not a per-run field |
| `SessionWriter(create_async_pool(), loop=loop)` | `:189` | **Pool shareable** (one pool for all runs); writer logic shareable but is a single loop/queue (see §6) |
| `make_transcript_snapshot_writer(storage_root)` | `:196-198` | **Per-run** (closes over per-run `storage_root`) |
| `submit_events` closure (binding→`writer.submit_blocking`) | `:201-221` | Logic shareable; today bound to the one writer |
| `TranscriptTailer(build_record, submit_batch, quarantine_window, snapshot)` + `.start()` | `:223-229` | **Registry shareable** — cursors keyed by `session_id` (see §6); but `snapshot` is per-run |
| `_register_owned_cursor(...)` task | `:230-233` | **Per-run** (reads per-run `settings`: run_id/cwd/cli/owned_native_session_id/agent_home_dir, `:68-84`) |
| `start_web_runtime` (embedded only) | `:246-257` | Per-run for embedded/CLI; **None for canvas** (`web_runtime="external"`, see §7) |

Other process-global singletons set on the capture path that a shared addon must make run-aware:
`counting.py::_recent_auth` (set on **every** request, `addon_handlers.py:80`, `counting.py:161`),
`override_state.py::_store = OverrideStore()` (`override_state.py:106`; overrides already scoped by
`(run_id, track_id)` via `scope_from_params`, so the store *instance* is shareable),
`breakpoint.py` module globals (§4), `broadcast.py::_subscribers` (§4).

**Shareable across runs:** one httpx upstream client, one `TokenCounter`, one Postgres pool, one
tailer registry, one override store instance, one SSE broadcaster. **Strictly per-run:** `run_id`,
`storage_dir`/`storage_root`, `upstream`, owned-session binding (`owned_native_session_id` +
`owned_source_descriptor` + `launch_fields` + `agent_home_dir`), the snapshot writer, the
owned-cursor registration, and the per-run breakpoint arm/serialize state.

---

## 3. Run-identity transport (process env → per-run context)

**Today:** the CLI writes `TRANSPORT_MATTERS_*` env before exec'ing `mitmdump`
(`launch_environment.py::build_launch_env`), and the addon reads them once via the `@lru_cache`'d
`get_settings()` → `Settings.load()` (`config.py:207-209`, `:137-143`). The per-run env keys (exhaustive,
from the spawn-chain subagent): `STORAGE_DIR`, `WEB_PORT` (omitted for external), `WEB_RUNTIME`,
`PROXY_PORT`, `RUN_ID`, `CWD`, `CLI`, `AGENT_HOME_DIR`, `DEFAULT_CLIENT_PASSTHROUGH`,
`OWNED_NATIVE_SESSION_ID`, `OWNED_SOURCE_DESCRIPTOR`, `LAUNCH_FIELDS`, `RESUME_CONTEXT`. These map to the
`Settings` fields at `config.py:65-103` (`run_id:79`, `cwd:87`, `cli:91`, `owned_native_session_id:96`,
`owned_source_descriptor:97`, `launch_fields:98`, `agent_home_dir:103`, `storage_dir:74`).

**Read sites that must move from `get_settings()` (process env) to a per-run context object:**

- `addon_runtime.py::load_capture_runtime` `settings.storage_dir` (`:162`), and
  `_launch_run_context` reading `run_id/cwd/cli/owned_native_session_id/agent_home_dir` (`:68-84`),
  `_register_owned_cursor` reading `launch_fields/owned_source_descriptor` (`:99-103`).
- `addon_handlers.py::handle_http_request` `get_settings().run_id` (`:96`);
  `handle_codex_websocket_message` `get_settings().run_id` (`:210`);
  `_should_skip_breakpoint` `get_settings().breakpoint_skip_models` (`:62-64`).
- `pause_session.py::_flow_track_fields` `get_settings().run_id` (`:210`);
  `_run_pause` `get_settings().breakpoint_timeout_s` (`:260-262`).
- Anything resolving the run's `cwd` for project-scoped overlays (`config.py:80-87` notes
  `/api/v1/meta` falls back to `Path.cwd`).

`get_settings()` being `@lru_cache` is the load-bearing assumption that breaks first under a shared
process: today the cache *is* the per-run identity. In a shared addon the cache becomes ambiguous
(one process, many runs), so identity must be threaded as a per-run binding resolved from the flow
(§1), not pulled from a process-global cache.

---

## 4. Breakpoint / pause-next-turn

**How it works today.** A module-level state machine in `breakpoint.py`:
`_mode: Literal["off","armed_once"] = "off"` (`:52`), `_paused: dict[str, PausedFlow] = {}` keyed by
`flow.id` (`:53`), `_lock` (`:54`), and `_pause_serializer: asyncio.Lock` (`:58`) that serializes **all**
pauses process-wide. `PausedFlow` (`:23-49`) holds a **live `asyncio.Event`** and a **live
`mitmproxy.http.HTTPFlow`** (non-serializable). Flow:

1. Addon HTTP hook: if `bp.is_armed()` and model not skipped → `handle_breakpoint`
   (`addon_handlers.py:124-127`). Codex websocket: same gate → `handle_websocket_breakpoint`
   (`:235-237`), so **later Codex turns** (incremental websocket frames) re-enter the pause path per
   turn (`pause_session.py::handle_websocket_breakpoint`, rewrite via
   `rewrite_codex_provisional_exchange(force_replay=True)` `:405`).
2. `pause_session.py::_run_pause` acquires the global `bp.pause_serializer()` (`:232`), calls
   `bp.pause(...)` storing the `PausedFlow`, `broadcast.emit({"type":"paused", ...})` (SSE), then
   `await asyncio.wait_for(event.wait(), timeout=settings.breakpoint_timeout_s)` (`:262`).
3. Release/drop comes from the FastAPI routes `breakpoint_routes.py`: `/arm`→`bp.arm()` (`:169-172`),
   `/release/{flow_id}`→`bp.release` (`:181-195`), `/drop`→`bp.drop`, `/re-audit`→reads `get_store()` +
   `get_counter()`. `bp.release()` sets `pf.event.set()` (`breakpoint.py:155`), unblocking the addon's
   awaiting coroutine **in the same process**.

**Is it per-run? No — it is process-global and single-run.** `_mode` is one flag; `_pause_serializer`
is one lock for the whole process; `_paused` is keyed by `flow.id` not `run_id`. The router mounts
**globally** (`api/v1/router.py:19`, `prefix="/breakpoint"`, no run scoping) and the frontend calls a
**single global URL with no run id** (`www/src/api.ts:267` `/api/breakpoint/arm`, `:276` `/release/{flowId}`).
`run_id` is only a *display field* on `PausedFlow`, sourced from `get_settings().run_id`
(`pause_session.py::_flow_track_fields:210`).

**Consequence (canvas).** For canvas runs `web_runtime="external"` → the per-run `mitmdump` runs the
addon but **no embedded web** (§7). The `/api/breakpoint/*` routes are served by the *shared API*
process, whose `breakpoint.py` globals are a **different process** from each run's `mitmdump`. So
arming via the canvas UI cannot reach a run's addon today: per-run breakpoint is effectively a
CLI/embedded-only feature (web + addon co-resident in the one `mitmdump` subprocess). This matches the
prior architecture lesson ("the breakpoint/override control plane is in-process… NOT separable across
an OS-process boundary").

**What must change for a shared addon serving many runs:**
- `_mode` → per-run (e.g. `dict[run_id, mode]`); arming targets one run.
- `_pause_serializer` → **per-run** lock, else one run's pause blocks every other run's outbound
  request through the shared serializer (the global lock is held across pause+await+pop).
- Routes `/arm /disarm /status /release /drop /re-audit /paused` must carry a `run_id` and resolve the
  run's breakpoint state; `www/src/api.ts` URLs must become run-scoped.
- SSE: `broadcast.py::emit` fans every event to all subscribers; `paused`/`paused_tokens` already carry
  `run_id` (`pause_session.py::_paused_event_payload:194`) so the UI can filter, but a shared
  broadcaster mixes all runs onto one stream.
- `counting.py::_recent_auth` (`:161`) is overwritten on every request from any run
  (`addon_handlers.py:80`) — in a shared process this is cross-run contamination; the re-audit route
  (`breakpoint_routes.py::_recount_tokens`) reads `pf.auth_headers` (per-flow, safe) but other readers
  of the global `_recent_auth` would see the last request of any run.
- **Control-plane locality is the crux** (see Hard Q3): the release path relies on `pf.event.set()`
  reaching the addon's awaiting coroutine *in the same process*. A shared `mitmdump` **subprocess**
  still cannot receive arm/release from the API process without a cross-process channel; an embedded
  mitmproxy `Master` *in* the API process co-locates them again.

---

## 5. Teardown & crash recovery

**Spawn (per run).** `run_routes.py::create_run` → `run_manager.py::RunManager.spawn` → `_spawn_new` →
`_spawn_new_admitted` → `_prepare_request` → `captured_run.py::prepare_captured_run` (retries
`_BIND_RETRY_ATTEMPTS = 3`) → `cli/runner.py::start_prepared_proxy` which calls
`sup.spawn("mitmdump", argv, env=...)` (`runner.py:319`) and blocks on
`cli/net.py::wait_for_port_ready` (5s, 0.1s poll). `build_mitmdump_argv` emits
`["--mode", "reverse:{upstream}", "--listen-host","127.0.0.1","--listen-port",{proxy_port},"-s",addon]`
(+ `--set termlog_verbosity=warn` unless debug).

**Lease ownership.** `captured_run_models.py::CapturedRunLease` owns `_supervisor` (the
`ProcessSupervisor` that spawned `mitmdump`), `_workspace_lock`, and a `_resource_stack` (addon paths,
overlay tmpdirs). The lease is held on `run_manager.py::ManagedRun.lease`.

**Teardown.** `RunManager.terminate` → `_teardown_run` → `await asyncio.to_thread(run.lease.close)`;
`CapturedRunLease.close()` calls `self._supervisor.terminate_all()` (SIGTERM→grace→SIGKILL, tears down
PTYs), unlinks the manifest, releases the workspace lock, closes the resource stack. Failure path
`_rollback_post_prepare` runs the same `lease.close`. **The port is freed only when the process exits**
(no explicit release). The addon's own shutdown (`addon.py::done` → `addon_runtime.py::close_runtime` →
`close_capture_runtime`) calls `bp.clear_all()`, stops the tailer (drain), closes the writer, drains
pause-count tasks, closes the httpx client (`addon_runtime.py:267-286`).

**What changes for a shared proxy.** Teardown must **deregister the run's route** (its listen mode +
per-run binding) and run only the *per-run* shutdown (clear that run's breakpoint state, deregister its
tailer cursors, flush its snapshot) — **never** `terminate_all()` the shared process or `bp.clear_all()`
(which drops every run's paused flows) or close the shared httpx/pool.

**Crash recovery: none today.** Subagent-confirmed: there is **no supervised restart** of a dead
`mitmdump`; if it dies, `RunManager._drain_run` sees PTY EOF and tears the run down as `failed`. The
`viewerless_since` field exists on `ManagedRun` but **no sweeper/reaper** consumes it (the
`idle-timeout` reason literal is never triggered). Runs are **process-resident** — they do not survive
an API restart. For a shared proxy this is the blast-radius problem (Hard Q5): one process is now a
single point of failure for all runs, and re-registering N live runs after a crash has no existing
machinery.

---

## 6. Transcript tailer & session writer

**Tailer is already a registry, keyed by `session_id`.** `index/tailer.py::TranscriptTailer` holds
`_cursors: dict[str, TailCursor]`; `register_session_cursor` wraps a `SessionBinding` (carrying
`run_id`/`session_id`/`provider`/`cli`) in a `TailCursor` and `register()`s it idempotently
(`_cursors.setdefault(binding.session_id, cursor)`); `poll()` iterates all cursors. **One tailer
instance can already hold cursors for many runs/sessions** — only one tailer is built per process today
because there is only one runtime per process (`addon_runtime.py:223-229`).

**Writer is a single loop + thread bridge.** `session/writer.py::SessionWriter` owns one
`AsyncConnectionPool` and one `_loop`. The tailer **thread** submits via
`submit_blocking` → `asyncio.run_coroutine_threadsafe(self._commit_batch(batch), self._loop)` with a
5s `_commit_timeout_s`. Ordering is **per-session atomic** (session upsert then ordered events in one
transaction); **no global cross-session ordering**. Backpressure is implicit (the tailer poll thread
blocks up to 5s per submit; there is no bounded queue). `aclose()` closes the pool but does not
explicitly drain in-flight futures. Pool sizing: `create_async_pool` reads
`Settings.session_pool_min_size = 0` / `session_pool_max_size = 10` (`config.py:119-120`); one pool per
writer.

**Implications of ONE shared SessionWriter/pool/tailer for all 50 runs:**
- **Ordering:** unchanged per-session; fine (each run's session is independent).
- **Backpressure (head-of-line):** the tailer is **single-threaded** — a slow run hitting the 5s
  `submit_blocking` timeout stalls polling for *all* runs. This is the sharpest shared-resource hazard.
- **Failure isolation:** poison events dead-letter per session (`quarantine_window_blocking`), so one
  run's bad write does **not** kill the writer — good. But the **event loop is shared**: if it dies,
  every run's writes fail. A shared pool of `max_size=10` also means 50 runs contend for 10 connections
  with no per-run reserve.
- Design choice: single shared writer/tailer (simplest, accept head-of-line) vs per-run tailer/writer
  on a shared pool vs thread-pool dispatch to de-multiplex slow runs (Hard Q4).

---

## 7. Web runtime

**Confirmed: canvas runs use `WEB_RUNTIME_EXTERNAL`.** `run_routes.py::_spawn_request` builds `SpawnRun`
without `web_runtime`; `run_manager.py::SpawnRun.web_runtime` defaults to `WEB_RUNTIME_EXTERNAL`
(`captured_run_models.py`). `cli/launch_runtime.py::resolve_launch_ports` takes the `not web_required`
branch: `proxy_port, _unused_web = allocate_port_pair()` then returns `(proxy_port, None, …, False)` —
the web port is allocated then **discarded**, so a canvas run binds **exactly one TCP port** (the proxy).
`addon_runtime.py::load_runtime` builds `web = None` because `web_runtime != "embedded"` (`:263`). So the
shared proxy needs only the **reverse-proxy + capture** path; no embedded uvicorn per run.

**Cases that complicate a shared proxy:** the **embedded/CLI** launch (`web_runtime="embedded"`) does
run a per-run uvicorn (`start_web_runtime`, `addon_runtime.py:246-257`) and co-resident breakpoint
routes — this is the path where breakpoint actually works today. A shared multi-mode proxy is a clean
fit for the canvas/external path; the embedded path keeps its own one-process model (or the shared
proxy must grow the control surface the embedded web provides — see Hard Q3).

---

## Top 5 hard design questions (the genuine forks)

**HQ1 — Can mitmproxy mutate reverse `mode` entries at runtime, or only at process start?**
(The design's de-risk-first spike.) If runtime add/remove works → incremental per-run register/deregister
on one long-lived proxy. If start-time only → fall back to a **bounded pool** of K multi-mode proxies
(batch modes) or restart-with-debounce. This gates whether Tier 2 is "one proxy" or "a small pool" and
must be answered by a half-day spike before any refactor.

**HQ2 — What is the airtight flow→run key, and what carries run identity?**
`flow.client_conn.sockname` (listen port) is the proposed key but is **unproven and entirely unused
today** (§1); alternatives are per-run upstream host or an injected per-run header. Whatever is chosen
becomes the product's core correctness contract — a single mis-attribution cross-contaminates wire +
transcript across runs. Coupled to it: identity moves from the `@lru_cache get_settings()` process
singleton to a per-run binding object resolved on every hook (§3).

**HQ3 — Embedded mitmproxy `Master` in the API process vs `mitmdump` subprocess + IPC.**
The whole interactive control plane (breakpoint arm/release via live `asyncio.Event` + live flow,
override store, token counter, SSE) is process-global and depends on the routes and the addon sharing a
process/loop (§4). An **embedded Master** in the API process re-co-locates them (control plane "just
works", but now one event loop serves the API + the shared proxy + all runs — a throughput/isolation
risk). A **subprocess** keeps proxy CPU off the API loop but requires a brand-new **cross-process
control channel** for arm/release/inspect that does not exist today. This fork decides the breakpoint
redesign and is, in my read, the hardest because it is irreversible and touches the product's
differentiating feature.

**HQ4 — Shared SessionWriter/pool/tailer vs per-run isolation.**
One tailer thread + one writer loop + a 10-connection pool means a slow/poison run can head-of-line
block all 50 (§6). Fork: accept the single shared writer (simplest, cross-run head-of-line) vs per-run
tailer/writer over a shared pool vs thread-pool dispatch. Determines failure isolation and tail latency
at 50 runs.

**HQ5 — One shared proxy (single point of failure) vs a bounded pool, and process-residency.**
There is **no supervised restart and no re-register machinery** today, and runs die on API restart (§5).
One proxy collapses cost maximally but means a crash takes down all runs; a bounded pool of K
multi-mode proxies (~6-7 runs each) trades some savings for blast-radius isolation. Also forces a
decision on whether runs must survive an API/proxy restart (re-register all live runs) or remain
process-resident as today.
