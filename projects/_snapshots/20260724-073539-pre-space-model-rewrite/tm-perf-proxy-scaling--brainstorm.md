---
title: "TM perf: scaling 50 captured runs on the canvas (proxy + spawn brainstorm)"
type: research
tags: [transport-matters, performance, proxy, captured-run, run-manager, postgres, frontend, scaling]
summary: "Per-run mitmdump + per-process Postgres pool is the dominant cost; a shared multi-mode proxy is the big lever, with a frontend spawn semaphore and an off-loop session-store preflight as cheap immediate wins."
status: active
source: codebase-analyst
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

# Scaling 50 captured runs on the canvas

Investigation only. No code modified. All claims cite `file::symbol`.

## Executive summary

Each captured run spawns **its own `mitmdump` (Python/mitmproxy) reverse-proxy process**, and
inside that process opens **its own Postgres connection pool** (`min 1`, `max 10`). At 50 runs that
is 50 Python interpreters and **50–500 Postgres connections** against a default ceiling of 100. The
single biggest lever is collapsing the per-run proxy into **one shared multi-mode `mitmdump`** that
demuxes by listen port and shares one Postgres pool / httpx client / token counter. Two cheap wins
make 50 runs survivable before that rewrite lands: a **frontend spawn-concurrency semaphore** (today
50 panes fire 50 concurrent `POST /v1/runs` with no limit) and moving the **per-spawn synchronous
session-store preflight off the event loop** (it currently blocks the loop with a fresh
`psycopg.connect` on every spawn).

---

## 1. Per-run cost model (with numbers)

The spawn chain: `run_routes.py::create_run` → `run_manager.py::RunManager.spawn` →
`RunManager._spawn_new` → `RunManager._prepare_request` → `captured_run.py::prepare_captured_run` →
`cli/runner.py::start_prepared_proxy` (spawns `mitmdump`, blocks on `wait_for_port_ready`) → back in
`_spawn_new`, `RunManager._spawn_pty` spawns the client (Claude/Codex).

Canvas runs use **`WEB_RUNTIME_EXTERNAL`** — `run_routes.py::_spawn_request` builds `SpawnRun`
without setting `web_runtime`, and `run_manager.py::SpawnRun.web_runtime` defaults to
`WEB_RUNTIME_EXTERNAL`. Consequences, confirmed in `cli/launch_runtime.py::resolve_launch_ports`
(the `not web_required` branch) and `addon_runtime.py::load_capture_runtime`:

- **No embedded uvicorn per run.** The web port is allocated by `cli/ports.py::allocate_port_pair`
  then **discarded** (`allocated_proxy, _unused_web = allocate_port_pair()`). Only the proxy port is
  bound. So the orchestrator's "binds its own port(s)" is **1 bound port per canvas run**, not 2
  (CLI/embedded launches with `WEB_RUNTIME_EMBEDDED` do bind 2 and add a uvicorn server).
- **A Postgres pool is still opened per run regardless of web runtime.**
  `addon_runtime.py::load_capture_runtime` always builds `SessionWriter(create_async_pool())`.
  `session/pool.py::create_async_pool` reads `config.py::Settings.session_pool_min_size = 1` and
  `session_pool_max_size = 10`. So **every** `mitmdump` process holds ≥1 idle Postgres connection
  and can grow to 10 under load.

| Resource | Per canvas run | Where |
|---|---|---|
| OS processes | **2** (1 `mitmdump` + 1 client) | `start_prepared_proxy` (`sup.spawn("mitmdump", …)`) + `_spawn_new` (`_spawn_pty`) |
| Bound TCP ports | **1** (proxy listen) | `resolve_launch_ports` (`web_required=False`) |
| Postgres connections | **1 idle → 10 max** | `load_capture_runtime` + `create_async_pool` |
| RAM | `mitmdump` ≈ **80–150 MB** (Python + mitmproxy + httpx + psycopg pool + addon imports), client (Claude/Codex Node) ≈ **150–400 MB** → **~250–500 MB/run** | process pair |
| File descriptors | PTY master/slave, proxy listen + upstream sockets, mitmdump log, transcript-tailer file watch → **~15–30/run** split across `mitmdump` and the API parent | `_spawn_pty`, `start_prepared_proxy`, `addon_runtime.py` tailer |
| API-side state | 1 asyncio drain task + 1 `loop.add_reader(fd)` + 1 `TerminalFanout` + scrollback ring | `RunManager._drain_run`, `ManagedRun.terminal_output` |
| Startup CPU | fresh Python interpreter + **import of the whole `transport_matters` stack** (storage, session, index, uvicorn — see `addon_runtime.py` import list) per process, ≈ 1–3 s, then `wait_for_port_ready` | `start_prepared_proxy` |
| Per-run disk | a `runtime-home` overlay built then `rmtree`'d at teardown | `captured_run_context.py::build_captured_run_context` (`prepare_runtime_home`, `stack.callback(shutil.rmtree, …)`) |

**Hidden serializer (reliability bug, not just cost):** `RunManager._prepare_request` calls
`RunManager._captured_request` **synchronously on the event loop before** the
`await asyncio.to_thread(self._prepare_run, …)`. `_captured_request` calls
`self._dependencies.check_session_store()` → `session_store_preflight.py::check_session_store`, which
does a **blocking** `psycopg.connect(...) + SELECT 1` every spawn. With 50 concurrent `create_run`
coroutines, these blocking connects run on the single loop and **stall it serially**. The
`prepare_captured_run` work that *is* threaded is then capped by the default asyncio thread pool
(`min(32, cpu+4)` workers), so the rest queue.

---

## 2. Where it breaks first at 50 runs

Ranked by which ceiling you hit soonest:

1. **Postgres connections — first hard wall.** Default `max_connections ≈ 100`. Idle (min 1) = 50
   connections from captured runs alone, plus the main API's own pool and any embedded contexts.
   The moment pools grow toward `max_size=10` under transcript write load, a few dozen active runs
   exhaust Postgres. Practical ceiling: **~15–30 concurrently active runs**, well under 50.
   (`create_async_pool`, `Settings.session_pool_max_size`.)
2. **File descriptors (macOS).** Default soft `ulimit -n` is often **256**. The API parent holds PTY
   masters + terminal websockets + log handles; 50 runs push it toward/over the soft limit.
   (`_spawn_pty`, `run_terminal`, `run_routes.py::run_terminal_socket`.)
3. **RAM.** 50 × ~300 MB ≈ **15 GB** resident — saturates a 16 GB dev machine.
4. **CPU spawn-storm + event-loop stall.** 50 simultaneous Python interpreter starts + 50 serialized
   blocking `check_session_store` connects (item 1 in §1) → multi-second UI stalls and elevated
   spawn-failure/timeout rates.

---

## 3. Shared-proxy feasibility — the big win

**Verdict: feasible and the single largest lever.** mitmproxy (10+) supports **multiple `--mode`
specs in one process**, each a reverse proxy on its own listen address
(`reverse:UPSTREAM@127.0.0.1:PORT`). One long-lived `mitmdump` can therefore serve all runs: the
client contract is unchanged (each run still gets `ANTHROPIC_BASE_URL=http://127.0.0.1:{proxy_port}`
from `captured_claude.py::build_claude_captured_invocation`), and the addon demuxes by the **listen
port the flow arrived on** (available via the flow's local socket) → run id. This collapses 50 Python
processes → 1 and enables one shared Postgres pool + one httpx client + one token counter, killing
items 1, 3, 4 of §2 in one move. (Confidence: high that it removes the cost; medium that runtime
mode-list mutation is clean enough for incremental add/remove — prototype that first.)

**Seams that today assume one-proxy-per-run and must change:**

- `cli/launch_runtime.py::build_mitmdump_argv` — emits a single `--mode reverse:{upstream}` and a
  single `--listen-port`. Must emit/maintain a **multi-mode** listener set, or support a control
  channel that mutates the `mode` option list at runtime as runs come and go.
- `captured_run.py::prepare_captured_run` and `cli/runner.py::start_prepared_proxy` — spawn one
  `mitmdump` per call (`sup.spawn("mitmdump", …)`). Must become **register-a-route on a shared,
  long-lived proxy** (add a listen mode + a per-run runtime binding) instead of starting a process.
- `addon.py::TransportMattersAddon` (and `addon_handlers`) — `request`/`response`/`websocket_*`
  handlers operate on one process-global runtime (`addons = [TransportMattersAddon()]`). Must
  **resolve the per-run runtime from the flow** (listen port → run) on each event.
- `addon_runtime.py::load_runtime` / `load_capture_runtime` — build **one** runtime from **one**
  `Settings`, with one `SessionWriter`/pool/`TranscriptTailer`. Must split into a **shared core**
  (one pool, one httpx client, one `TokenCounter`, a tailer registry) + a **per-run binding**
  (`run_id`, `storage_dir`, session binding).
- `config.py::Settings` — run identity (`run_id`, `storage_dir`, `upstream`) is carried as
  **per-process env** today. Must become **per-run context** attached to the route registration, not
  the process environment.
- `run_manager.py::CapturedRunLease` / `ManagedRun.lease` (and `captured_run_models`) — the lease
  owns a `ProcessSupervisor`; teardown (`RunManager.terminate`, `RunManager._rollback_post_prepare`)
  calls `supervisor.terminate_all()`. With a shared proxy, teardown must **deregister the run's
  route** and not kill the shared process.
- `session_store_preflight.py::check_session_store` — once a shared pool exists, preflight **once at
  proxy startup**, not per-run on the event loop.

**Effort: high** (touches the proxy/addon product contract). This is the architectural item to
schedule deliberately.

---

## 4. Frontend spawn behavior + fixes

- **Trigger is per-pane, concurrent, unlimited.** `viewers/terminal/CapturedRunPane.tsx` calls
  `ensureRun(...)` inside a mount `useEffect`. Open N captured panes (saved layout, "spawn many", or
  rapid clicks) → **N simultaneous `POST /v1/runs`** via `api.ts::createCapturedRun`.
- **Dedupe is per-pane only.** `model/capturedRunStore.ts::ensureRun` dedupes via `pendingSpawns`
  keyed by pane `runKey` (guards React StrictMode double-mount). There is **no global concurrency
  cap, no batching, no retry/backoff**. A failure rejects, `CapturedRunPane`'s `.then` rejection
  handler sets `spawnError` and renders a banner (`spawnErrorMessage`); the run is not retried unless
  the pane remounts.
- **Error surfacing.** `api.ts::createCapturedRun` throws on non-2xx; `run_routes.py` maps
  `RunManagerError` codes via `_RUN_MANAGER_HTTP_STATUS` — `bind_conflict→409`,
  `session_store_unavailable→503`, `run_manager_closed→503`, `launch_failed→500`. Under a 50-wide
  stampede, `bind_conflict` (allocate→spawn TOCTOU) and 503/500 become much more likely; the only
  cushion is `_BIND_RETRY_ATTEMPTS` inside `prepare_captured_run`, which adds latency.

**Fixes (where they hook):**

1. **Client-side spawn semaphore (low effort, high reliability ROI).** Add a global in-flight limit
   (≈4–6) around the `createCapturedRun(...)` call in `capturedRunStore.ts::ensureRun` so panes
   stagger. Cuts bind races, 503 pile-ups, and the event-loop stall cascade.
2. **Bulk-spawn endpoint (medium effort).** `POST /v1/runs/batch` that runs **one** session-store
   preflight and bounded server-side concurrency, returning per-item results. Hooks: add
   `createCapturedRuns` in `www/src/api.ts`; add a batch handler beside `run_routes.py::create_run`;
   optionally `RunManager.spawn_many`. Replaces N round-trips + N preflights with one.
3. **Surface partial success.** With batching, render per-pane outcomes instead of N independent
   banners.

---

## 5. Shareable / cacheable startup work

- **Postgres pool, httpx client, `TokenCounter`** — duplicated per process today
  (`load_capture_runtime`). Inherently shared by §3; biggest steady-state saving.
- **`transport_matters` import cost** — every `mitmdump` re-imports storage/session/index/uvicorn
  (`addon_runtime.py` imports). Shared proxy pays this **once**, not 50×.
- **mitmdump resolution** — `cli/launch_runtime.py::resolve_mitmdump_executable` re-`shutil.which`es
  per run (cheap; runs inside the thread). Trivially memoizable.
- **Addon materialization** — `build_captured_run_context` does `as_file(prepared.addon_traversable)`
  per run; a no-op when the package is on-disk, a temp extract when zipped. Minor.
- **`runtime-home` overlay** — per run by design (isolated home), built then `rmtree`'d. The
  **template** is shared; the overlay copy is not. If it isn't already symlink/CoW-based, that's a
  per-run disk lever. (`captured_run_context.py`, `cli/runtime_home.py`.)
- **Session-store preflight** — see §3; one shared preflight instead of per-spawn blocking connect.

---

## 6. Ranked options — effort vs impact

| # | Option | Impact | Effort | Notes |
|---|---|---|---|---|
| 1 | **Shared multi-mode `mitmdump`** (one process, port→run demux, shared pool/client/counter) | **Very high** — kills process, pool, and import cost 50× | High | The lever. Prototype runtime mode mutation first. Seams in §3. |
| 2 | **Frontend spawn semaphore** in `capturedRunStore.ts::ensureRun` | Medium–high (reliability, error rate) | **Low** | Ship immediately; independent of §3. |
| 3 | **Move `check_session_store` off the loop + cache** (`RunManager._captured_request`) | Medium (removes serialized loop stall) | **Low** | Run inside `to_thread`, or one cached TTL preflight. |
| 4 | **Cap `session_pool_max_size` (1–2), consider PgBouncer** (`config.py`, `create_async_pool`) | Medium–high (lifts the first ceiling) | Low–Med | Stopgap until §1 removes per-process pools. |
| 5 | **Bulk-spawn endpoint** `POST /v1/runs/batch` | Medium (fewer round-trips + 1 preflight) | Medium | Hooks: `api.ts`, `run_routes.py::create_run`, `RunManager`. |
| 6 | **Pre-warmed `mitmdump` pool** | Medium (spawn latency only) | Medium | Doesn't cut steady-state count; superseded by §1. |

**Recommended sequence:** ship #2 + #3 + #4 now (days, big reliability gain under 50 runs), then
invest in #1 (the structural fix) with #5 as its natural client surface.

---

## Open questions

- Does mitmproxy permit **adding/removing reverse modes at runtime** cleanly (incremental run
  add/remove), or only at process start? Determines whether §3 is incremental or batch-restart.
- What is the actual machine `ulimit -n` in the desktop deployment (confirms §2 item 2 severity)?
- Is there an **idle reaper** actually terminating viewerless runs? `run_manager.py` tracks
  `viewerless_since` but contains no sweeper; `capturedRunStore.ts` comments reference a "backend
  idle policy" — locate it (or confirm its absence) for the reliability story at 50 runs.
