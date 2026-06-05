---
title: P1 Implementation Spec — Cross-platform desktop + canvas, Runtime context served in plain TS, mitmproxy as a managed Python sidecar
type: projects
tags: [transport-matters, t3code, p1, desktop, canvas, runtime, gateway, launcher, cross-platform, mitmproxy, pty, node-pty]
summary: The P1 implementation spec, revised after independent review and the product-plane naming decision. Stands up the Runtime context (@tm/runtime, packages/runtime) — run lifecycle + terminal + capture bind — running as a standalone Runtime server that serves only the run lifecycle + terminal routes (create/list/get/terminate + terminal WS); exchanges/meta and the wider API stay Python; the future Gateway subsumes the standalone server at the target. Adopts t3code's desktop-lifecycle pattern (grace-then-force child kill, one shutdown coordinator, scope-like finalizer ordering) in PLAIN TS — no Effect. Cross-platform PTY via node-pty (NodePtyAdapter, incl. Windows ConPTY). mitmproxy + all live-flow capture stay Python, spawned via a clean 2-call bind/release RPC (prepare_capture -> CapturedRunSpawnSpec, release_capture(run_id) drops the CapturedRunLease). Resolves the two coupled lifecycles (TS terminal + Python capture) joined by run_id with an explicit teardown order and per-route ownership split. Absorbs and supersedes the POSIX-only launcher spec.
status: active
source: opus (author) — reviewed independently by codex; Effect->plain-TS by Stuart; naming (Runtime/Gateway) locked by Stuart via 2-agent MoE
confidence: medium-high
created: 2026-07-04
updated: 2026-07-04
---

# P1 Implementation Spec — Cross-platform desktop + canvas (Runtime context, plain TS)

**Spec phase only. No product code.** Citations are **file + symbol**, never line
numbers. This is the plan that turns the locked P1 decision into PR-sized, gated
work. It **absorbs and supersedes** the parked POSIX-only launcher spec
(`launcher-spec-desktop-relaunch.md`).

**Naming (locked, see `docs/ARCHITECTURE.md`).** Earlier drafts said "TS host / run
host." The product-plane vocabulary is now fixed:

- **Runtime** (`@tm/runtime`, `packages/runtime/`) — the bounded context that owns run
  lifecycle + terminal + capture bind. The `RunStarted`/`RunExited` producer already
  named in the doc's Target context map. This is what earlier drafts called the "TS
  host." (`@tm/host` is already taken — `www/packages/host` browser chrome — so "host"
  is retired entirely.)
- **The Runtime server** — the standalone Node process that runs `packages/runtime/`'s
  `src/server/` router in P1. This is the process `DesktopBackendManager` spawns and
  that Python reverse-proxies the run routes to.
- **Gateway** — the target product-plane origin (an app / composition root) that will
  mount many context routers, serve the browser bundles, and reverse-proxy the frozen
  capture plane. **Not built in P1.** In P1 the Runtime server serves its routes
  directly and Python is the interim front door; the Gateway subsumes the standalone
  server at the target.

**Revision history.** Independent codex review (`tm-t3code-p1-spec-review.md`) raised 1
Blocker + 3 Majors + 1 Minor, all folded in. Two decisions changed since the first
draft: (1) plain TS, not Effect (§6); (2) the run surface splits by **route**, not by
prefix (§2b). Grounding: the alignment report (`tm-t3code-alignment.md`, esp. §5, §8,
§8e), the two scouts, the launcher spec, the review, and the plane-vocab MoE
(`tm-plane-vocab-opus.md`, `tm-plane-vocab-codex.md`). Current-tree facts re-verified;
notes inline.

---

## 0. Locked scope — what P1 is, and what it is not

**P1 is** (locked by Stuart):

> Cross-platform (Windows/Linux/macOS) desktop + canvas terminal on a plain-TS
> lifecycle, with the Runtime context served standalone and mitmproxy as a managed
> Python sidecar.

Four deliverables and nothing more:

1. **The desktop lifecycle in plain TS** — adopt t3code's `DesktopLifecycle` /
   `DesktopBackendManager` / `DesktopShutdown` *shape* (grace-then-force SIGTERM ->
   bounded grace -> SIGKILL; one coordinator for every quit path; finalizers that stop
   the child before `app.quit()`), in plain TS. Fixes the active orphan bug on all
   three OSes.
2. **The Runtime context served standalone** — `@tm/runtime` (`packages/runtime/`) with
   a `src/server/` router serving the **run lifecycle + terminal routes** (`POST/GET
   /v1/runs`, `GET /v1/runs/{id}`, `POST /v1/runs/{id}/terminate`, `WS
   /v1/runs/{id}/terminal`) for **both** the desktop canvas **and** the web-served
   `/canvas`. Exchanges, meta, sessions, spaces, and the rest of the API stay Python
   (§2b).
3. **Cross-platform PTY for the canvas terminal** via t3code's `node-pty` adapter
   (`PtyAdapter` / `NodePtyAdapter`), incl. Windows ConPTY that our POSIX
   `pty_session.py` cannot provide. The concrete reusable value.
4. **mitmproxy stays Python**, spawned as a managed child behind a clean 2-call
   bind/release RPC. The one hard design task is the **two coupled lifecycles**
   (TS terminal + Python capture) and their teardown ordering (§4).

**P1 is NOT:**

- Not a port of the capture pipeline. mitmproxy, addon, Codex transport, breakpoint
  flow-hold, response streaming, exchange recording, IR/normalization — all stay Python
  (report §8a: ~10,880 LOC, ~25% of API source). Horizon (b), out of scope.
- Not the **Gateway**. In P1 the Runtime server serves its own routes and Python is the
  interim front door; the Gateway is a target concept only.
- Not a port of run orchestration or the multi-viewer fan-out **by default**. Our
  `RunManager` behaviour, `ScrollbackRing`, `TerminalFanout`, and resume-from-seq are
  richer than t3code's single-`history` model and are re-ported, not lifted (§5). They
  move only because the PTY transport moving to TS drags the terminal half with it.
- Not the exchanges/meta artifact routes, the Postgres session store, the read/stream
  session API, or Tier-1 storage. Those stay Python in P1.
- **Not an Effect adoption.** Deliberately deferred; see §6.

---

## 1. The topology P1 lands

Before (today): **one Python process** (FastAPI + uvicorn) owns everything — desktop
lifecycle, the full `/v1` surface, `RunManager`, the PTY spawn, and it starts the
mitmproxy proxy in-process via `prepare_captured_run`. Electron is a thin viewer.

After (P1):

```
  ┌─────────────────────────── Electron main (thin, plain TS) ──────────────────┐
  │  DesktopLifecycle    ── OS-branched signals, window-quit semantics            │
  │  DesktopShutdown     ── one coordinator (AbortController/Promise) for every    │
  │                         quit path; finalizers stop the child before app.quit() │
  │  DesktopBackendManager ── spawns + owns the RUNTIME SERVER: SIGTERM, 2s, SIGKILL│
  └───────────────┬─────────────────────────────────────────────────────────────┘
                  │ spawns + owns
                  ▼
  ┌──────── RUNTIME SERVER (packages/runtime, standalone in P1) ──────────────────┐
  │  HTTP: POST/GET /v1/runs, GET /v1/runs/{id}, POST /v1/runs/{id}/terminate       │
  │  WS:   /v1/runs/{id}/terminal                                                   │
  │  RunManager (re-ported): run state machine, attach/detach/list/terminate        │
  │  Terminal transport (re-ported): ScrollbackRing, TerminalFanout, resume-seq     │
  │  PtyAdapter / NodePtyAdapter (node-pty)  ── cross-platform PTY incl. ConPTY      │
  │  (at the target: this router is mounted by the GATEWAY, not run standalone)      │
  └───────────────┬───────────────────────────────────────┬─────────────────────┘
                  │ 2-call capture RPC (Runtime → Python)  │ (breakpoint RPC deferred, §2d)
                  ▼                                        ▼
  ┌─────────────── Python (front door + capture sidecar) ─────────────────────────┐
  │  Serves EVERYTHING ELSE: /v1/runs/{id}/exchanges, /v1/runs/{id}/meta,           │
  │    /v1/sessions, /v1/spaces, /v1/runtime-templates, /api/meta, the bundles      │
  │  Reverse-proxies ONLY the 5 moved run routes to the Runtime server (§2b)        │
  │  Capture: prepare_capture(req)->CapturedRunSpawnSpec  release_capture(run_id)    │
  │  CapturedRunLease {_supervisor(mitmproxy), _workspace_lock, _resource_stack}     │
  │  addon, Codex transport, breakpoint flow-hold, response stream, recorder         │
  │  Postgres session store + Tier-1 disk  ── the durable Python↔TS boundary         │
  └──────────────────────────────────────────────────────────────────────────────┘
```

The clean process boundary between TS and Python is **Postgres + Tier-1 disk** (already
serialized) plus **one RPC channel** (capture bind/release, §2c). The breakpoint plane
stays entirely Python in P1 (§2d).

---

## 2. Central design resolution — the four seams

### 2a. The desktop-lifecycle seam (plain TS, pattern adopted)

Adopt t3code's three seams **as plain TS** (keep the names, drop Effect):

- **`DesktopBackendManager`** — the managed child is the **Runtime server** (§2b),
  spawned with Node `child_process.spawn`. On teardown: SIGTERM, wait a bounded grace
  (2s, matching upstream's `forceKillAfter`), then SIGKILL. A small
  `graceThenForce(child, signal, graceMs)` helper is the whole mechanism.
- **`DesktopLifecycle`** — the OS-branch home (report §4.1a): register `SIGINT`/
  `SIGTERM` only when `platform !== "win32"`; gate window-all-closed quit on
  `!== "darwin"`. Where §3's cross-platform branches live.
- **`DesktopShutdown`** — a single teardown coordinator (a resolved-once Promise /
  `AbortController`, the plain-TS analogue of t3code's `Deferred`) that every quit path
  funnels through. A top-level finalizer stops the Runtime server **before**
  `electronApp.quit()` so quit never races the teardown.

Effort M, risk M. This replaces `desktop/src/main.ts::registerAppLifecycle` +
`bindBackendQuitCleanup` + the Python launcher (`cli/desktop_cmd.py`,
`desktop_runtime.py` teardown), and dissolves most of the cross-language desktop DRY
(report §4.5): the served process is TS, so env/command/runtime-status shapes stop
hand-mirroring Python. `desktop/src/backendProcess.ts::launchBackendProcess` and
`desktop/src/main.ts::registerAppLifecycle` are the plain-TS seams being reshaped.

### 2b. The serving seam (THE crux — route ownership, corrected by review)

The report's §8e and the P1 decision restate a tension: "a TS host serves /runs" **and**
"our RunManager stays ours." Those cannot both be literal, because today `RunManager`
**is** what serves the run routes and terminal WS from the Python FastAPI app. Something
must serve those routes from TS, or the PTY cannot move to `node-pty`. In P1 that
something is the **Runtime server**; "RunManager stays ours" is honoured as behaviour
ownership — the run lifecycle semantics and the multi-viewer resume-from-seq contract
are re-ported, not lifted (§5), and `captured_run.py` literally stays Python.

**The review's blocker correction:** `/v1/runs*` is **not** a single surface. The Python
app (`main.py::create_app`) mounts three routers under it — `run_routes.router`,
`exchanges.run_router`, `meta.run_router` — so the prefix owns **more than run
lifecycle**:

- `api/v1/exchanges.py::RUN_EXCHANGES_ROUTE_PREFIX` = `/runs/{run_id}/exchanges`
  (artifact bytes), consumed by `www/packages/core/src/transport.ts::fetchExchange`,
  `fetchTurnContent`, `fetchPipelineTokens`.
- `api/v1/meta.py::get_run_meta` at `/v1/runs/{run_id}/meta`, consumed by
  `transport.ts::fetchMeta`.

A blind "reverse-proxy the whole `/v1/runs*` prefix" would **steal exchange and meta
routes from Python**, which are pure capture-artifact reads. And "serve the canvas
bundle from TS" would strand `/api/meta`, `/v1/sessions`, `/v1/spaces`,
`/v1/runtime-templates` unless the server also proxied the whole Python API.

**Resolution — split by route, and keep Python as the origin front door.**

| Route | Owner in P1 | Why |
| --- | --- | --- |
| `POST /v1/runs` (create), `GET /v1/runs` (list), `GET /v1/runs/{id}` (get) | **Runtime** | run lifecycle state — the run manager owns it |
| `POST /v1/runs/{id}/terminate` (`run_routes.py::terminate_run`) | **Runtime** | run lifecycle — kills the PTY + releases capture (§4) |
| `WS /v1/runs/{id}/terminal` (`run_routes.py::run_terminal_socket`) | **Runtime** | PTY transport via `node-pty`; the whole point of the move |
| `GET /v1/runs/{id}/exchanges…` (`exchanges.py`) | **Python** | capture artifact reads; no PTY coupling |
| `GET /v1/runs/{id}/meta` (`meta.py::get_run_meta`) | **Python** | capture metadata; no PTY coupling |
| `/v1/sessions`, `/v1/spaces`, `/v1/runtime-templates`, `/api/meta`, the bundles, everything else | **Python** | unchanged; out of P1 scope |

**Front-door model:** the **Python app stays the origin** the canvas bundle loads from,
in **both** desktop (loopback) and web (`/canvas`) modes. It reverse-proxies **only the
five moved run routes** to the Runtime server and serves everything else locally. This
keeps the canvas same-origin contract (`transport.ts` relative paths,
`terminalSocket.ts::runTerminalSocketUrl`) **unchanged** and localizes the serving
change to five explicitly-named routes. A prefix proxy is wrong (it captures
exchanges/meta); the proxy is **per-route**.

**The five moved routes are exactly `run_routes.router`'s whole surface** (verified):
`POST /v1/runs`, `GET /v1/runs`, `GET /v1/runs/{id}`, `POST /v1/runs/{id}/terminate`,
`WS /v1/runs/{id}/terminal`. The exchanges and meta routes are **sibling paths under the
same `/v1/runs/{id}/`** but belong to *separate* routers and stay Python — which is
exactly why the proxy must match the five **route patterns**, not the `/v1/runs*` prefix
(a prefix rule cannot distinguish `/{id}/terminal` from its `/{id}/exchanges` sibling).

**WebSocket-proxy risk (slice-1 critical path).** Four of the five moved routes are
ordinary HTTP forwards; the fifth, `WS /v1/runs/{id}/terminal`, is a **WebSocket**. The
front door must proxy a **WS upgrade + bidirectional byte pump** to the Runtime server,
materially harder than an HTTP forward. Pointing
`terminalSocket.ts::runTerminalSocketUrl` at the Runtime server's own origin would break
the same-origin contract (the URL is built from `location.host`). So the WS reverse-proxy
through the Python front door is **required**, and it is the sharpest implementation risk
in this seam. Prove it in slice 1, not slice 4.

**At the target:** the Gateway becomes the origin and reverse-proxies the *capture reads*
(exchanges, meta, stream, breakpoint) to Python — the mirror image of P1's interim front
door. The arrow flips once; the same-origin surface contract never changes.

**Consequence for slice 1 (review's requirement):** slice 1 must prove the **full canvas
origin contract** across the split — every route the canvas bundle calls
(`createCapturedRun`, `listRuns`, `getRun`, `terminateRun`, the terminal WS, **and**
`fetchExchange`/`fetchMeta`) resolves correctly with the run routes proxied to the
Runtime server and the rest served by Python — not merely a stubbed `/v1/runs`. The WS
proxy is part of this acceptance.

### 2c. The capture RPC seam (2-call bind/release — verified clean)

Verified in `captured_run.py::prepare_captured_run` (confirmed by the reviewer): it
allocates proxy/web ports, writes the run manifest, starts the mitmproxy proxy under a
Python `ProcessSupervisor`, and returns `tuple[CapturedRunSpawnSpec, CapturedRunLease]`:

- **`CapturedRunSpawnSpec`** (`captured_run_models.py::CapturedRunSpawnSpec`) = a
  **serializable launch envelope**: `client`, `launch_env`, `proxy_port`/`web_port`,
  `storage_dir`, `mitmdump_log`, `managed_session`, `harness`. The PTY-spawned agent
  needs only `client` + `launch_env` — plain strings that cross a process boundary.
- **`CapturedRunLease`** = a **live Python handle**; `CapturedRunLease.close` (verified)
  **idempotently** terminates the supervisor, releases the workspace lock, removes the
  manifest, and closes the resource stack. It stays in Python, keyed by `run_id`.

**The RPC contract (new):**

| RPC | Direction | Request | Response / effect |
| --- | --- | --- | --- |
| `prepare_capture` | Runtime → Python | run request (workspace, harness, channel, managed_session flag) | starts mitmproxy, allocates ports, writes manifest, holds the `CapturedRunLease` keyed by `run_id`; returns the serializable `CapturedRunSpawnSpec` |
| `release_capture` | Runtime → Python | `run_id` | calls `CapturedRunLease.close` (already idempotent) and drops the registry entry |
| `capture_health` (optional) | Runtime → Python | `run_id` | liveness of the proxy child, for Runtime's run state |

Transport: a small loopback HTTP/JSON RPC (Q2). The envelope is already serializable and
`CapturedRunLease.close` already idempotent, so the seam is genuinely clean — the only
new code is the RPC wrapper + a `run_id`->lease registry, not new lifecycle logic.

**Ownership rule:** the `CapturedRunLease` is authoritative for "is capture alive";
Runtime is authoritative for "is the terminal/PTY alive." Neither owns the other; they
are joined only by `run_id` and the teardown ordering in §4.

### 2d. The breakpoint control plane (stays Python in P1)

The breakpoint pause holds a **live mitmproxy flow in-process** (`pause_session.py`,
`breakpoint.py::handle_breakpoint`): an `asyncio.Event` / live `HTTPFlow` that does not
cross a process boundary. The breakpoint UI is inspector-driven, and the inspector is
served by Python and stays Python. **P1 does not move or proxy the breakpoint plane.** If
a future canvas affordance needs run-scoped arm/release, add a third RPC on the §2c
channel. Called out so the seam is designed, not discovered (report §8d).

---

## 3. Cross-platform teardown (the correctness core) — with a named seam

The launcher spec's central insight survives, re-homed onto the Python **capture child**
managed by the Runtime server's `graceThenForce`:

**Graceful paths** (before-quit, window-all-closed, non-Windows signals, fatal startup)
funnel through `DesktopShutdown` and get grace-then-force from the §2a helper (2s grace).
Common case, all three OSes.

**The hard case is Electron/Runtime-server SIGKILL**, when no graceful path fires. What
reaps the child then is OS-level parent-death behaviour (report §5b, verified):

| OS | Parent-death reaping | P1 mechanism + owner |
| --- | --- | --- |
| **Windows** | **Job Objects** (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) reap the child tree on owner-handle close | the spawning parent owns the Job (§ seam below) |
| **Linux** | **`PR_SET_PDEATHSIG`** signals the child on parent death | **Python sidecar self-installs** it (ctypes) with a getppid guard |
| **macOS** | **Neither** — orphans reparent to `launchd` | **Python sidecar watchdog** (stdin-EOF + `getppid()==1` poll) |

**The named seam (review's Major — the part the first draft asserted without defining):**

- **Linux + macOS are handled entirely inside the Python sidecar bootstrap**, because
  the sidecar *is* the child and can act on itself. A new
  `capture/self_reap.py::install_parent_death_reaping()` runs first in the sidecar
  entrypoint: on Linux, `ctypes` `libc.prctl(PR_SET_PDEATHSIG, SIGTERM)` **then**
  re-check `os.getppid()` — if it is already `1`, exit immediately; on macOS, start the
  watchdog thread. No Node involvement.
- **Windows needs a Job Object owned by the spawning parent.** Two parent→child edges
  exist: (i) the Runtime server spawns the **PTY agent**, and (ii) Python's
  `prepare_capture` spawns the **mitmproxy** child. Each spawner owns a Job over its own
  child tree: `packages/runtime/src/adapters/platform/JobObject.ts` for the PTY agent,
  and the Python sidecar's own Job for mitmproxy (Python owns what Python spawns). A new
  `host/`-style native binding is **not** a single owner — ownership follows the spawn
  edge. This corrects the first draft's implicit "the TS host owns the Job" (it only owns
  the Job over the process *it* spawned). Requires a Win32 native binding
  (`CreateJobObject`/`SetInformationJobObject`/`AssignProcessToJobObject`) — **Q7** picks
  it (N-API addon vs prebuilt helper vs existing npm shim).
- **Subtree reap on graceful shutdown:** the Python sidecar stays a process-group leader
  (`os.setsid` on POSIX) so it can `killpg` its own subtree — asgi workers **and** the
  `mitmdump` child — on shutdown; on Windows its Job Object is that reaper. This closes
  the launcher spec's §5d POSIX-only debt.

**POSIX-only debt to retire** (verified symbols): `desktop_runtime.py::is_pid_alive`
(`os.kill(pid,0)`), `desktop_runtime.py::stop_desktop_record` (`os.kill`),
`cli/desktop_cmd.py` `start_new_session=True`, and `pty_session.py::spawn_pty_process`
(POSIX PTY, `setsid`, `TIOCSCTTY`, `killpg`). Much **collapses** because the desktop
launcher is what `DesktopBackendManager` replaces and `pty_session.py` is replaced by
`NodePtyAdapter`.

---

## 4. The two coupled lifecycles + teardown ordering (the one hard design task)

Two lifecycles joined by `run_id`:

- **TS terminal lifecycle** (Runtime): PTY (`node-pty`) spawn → attached viewers → PTY
  exit.
- **Python capture lifecycle**: `prepare_capture` (mitmproxy up) → `release_capture`
  (`CapturedRunLease.close`, idempotent).

Ordering and authority rules:

1. **Spawn order: capture before PTY.** `POST /v1/runs` → Runtime calls
   `prepare_capture(req)` → receives `CapturedRunSpawnSpec` → spawns the PTY agent with
   `spec.client` + `spec.launch_env` (which point the agent at the proxy). The proxy must
   be up before the agent's first request, so capture binds first. If `prepare_capture`
   fails, no PTY is spawned and the run is rejected.
2. **Normal end: PTY exit → release capture.** When the `node-pty` child exits, Runtime
   is authoritative for "run ended": it tears down the terminal (drain fan-out, close
   attachments), **then** calls `release_capture(run_id)` so mitmproxy stops **after** the
   last byte is captured. Never release capture while the PTY still lives.
3. **Explicit terminate (`POST /v1/runs/{id}/terminate`): symmetric.** Runtime kills the
   PTY (grace-then-force), waits exit, then `release_capture`. Same order as (2).
   *(Route corrected per review: `POST …/terminate`, matching `run_routes.py::terminate_run`
   / `transport.ts::terminateRun` / `capturedRunStore.ts::stopRun` — not `DELETE`.)*
4. **Capture dies first (mitmproxy crash):** `capture_health` / an RPC error surfaces;
   Runtime marks the run degraded and tears down the PTY (the agent is now proxyless).
   Then `release_capture` is idempotent cleanup.
5. **Runtime-server SIGKILL:** §3 mechanisms. The Python sidecar's self-reaping path
   reaps mitmproxy — its own child — and `CapturedRunLease.close` runs from the sidecar's
   own shutdown, not from a `release_capture` call that will never arrive.
   `release_capture` is idempotent so the two paths never conflict.

**Authority summary:** **Runtime authoritatively ends the run** whenever it is alive (2,
3, 4); the **Python sidecar self-releases** only when Runtime is gone (5). Idempotent
`release_capture` / `CapturedRunLease.close` makes both safe. This answers the
checkpoint's "who authoritatively ends the run": **Runtime when alive, sidecar
self-release on Runtime death.**

---

## 5. What stays ours vs what ports (verified against t3code)

| Ours today (Python) | P1 disposition | t3code reuse |
| --- | --- | --- |
| `pty_session.py::spawn_pty_process`, `supervisor_pty*.py` | **Port to TS (Runtime)** | `PtyAdapter` + `NodePtyAdapter` (+ `BunPtyAdapter`) — pluggable PTY over `node-pty`, incl. Windows ConPTY. **Primary reuse target.** |
| `run_terminal.py::ScrollbackRing` + `TerminalFanout` (seq'd byte-capped ring, multi-attach fan-out, per-attachment queues, resume-from-seq) | **Re-port, preserve behaviour** | t3code has only `TerminalSessionState.history: string` + `attachStream`. Our multi-viewer resume-from-seq is **richer** — re-port, do not lift. |
| `run_manager.py::RunManager` (`_prepare_request`, `_start_run_terminal`, `_teardown_run`) | **Re-port into Runtime** | `apps/server/src/terminal/Manager.ts::TerminalManager` — reference design only. |
| WS `run_terminal_socket` + `www/packages/core/src/transport.ts` run types | **Re-express in Runtime** | `packages/contracts/src/terminal.ts` (`TerminalOpenInput`/`AttachInput`/`WriteInput`/`ResizeInput`/`AttachStreamEvent`/`SessionSnapshot`) — schema-validated wire protocol shape. |
| xterm in `SessionCanvasRoute.tsx`, `CapturedRunPane.tsx`, `capturedRunStore.ts` | **Stays** (frontend already TS) | same `@xterm/xterm`; renderer unchanged; store points at the same relative routes. |
| `captured_run.py::prepare_captured_run` + `CapturedRunLease` | **Stays Python** | none — mitmproxy-bound; exposed via §2c RPC. |
| exchanges/meta routes, mitmproxy, addon, Codex transport, breakpoint, response stream, recorder, IR/normalization, session store, Tier-1 storage | **Stays Python** | none — out of P1 scope. |

**Reuse-claim verdict (report §8e, confirmed by review):** t3code's "battle-tested"
value is **real for** cross-platform PTY transport (`node-pty`, incl. ConPTY), resize,
the terminal wire contract, and xterm. It is **not** a gift for run orchestration or our
multi-attach seq-resume fan-out — those we re-port and own.

*Carry as a port task, not reuse:* whether t3code's `TerminalManager` supports
multi-viewer resume-from-sequence. Its `history: string` + `attachStream` reads as
single-history replay. Treat parity as a port task.

---

## 6. Effect — decision: NOT for P1 (plain TS)

**Decision (Stuart, on the independent review):** do **not** adopt Effect for P1.
Implement the lifecycle and the Runtime server in plain TS.

Rationale (verified + review-backed):

- **Effect is net-new to the entire org.** No package declares `"effect"`/`@effect`; the
  Activity package uses **`xstate`**. Adopting Effect would introduce a new runtime
  paradigm, dependency, and convention for a first slice that does not need it.
- **Effect solves none of P1's hard risks.** The load-bearing risks are route ownership
  (§2b), native parent-death reaping (§3), capture RPC semantics (§2c/§4), and terminal
  parity (§5). Effect's value is expressing scope finalizers cleanly — and the plain-TS
  `graceThenForce` + single `DesktopShutdown` coordinator + finalizer ordering already
  express that at lower fidelity, zero new paradigm cost.
- **We keep the pattern, not the runtime.** Report §4.4: "adopt the names, not the
  Effect." `DesktopLifecycle` / `DesktopBackendManager` / `DesktopShutdown` remain seam
  names; their bodies are plain TS. `docs/ARCHITECTURE.md`'s "Effect boundary" note
  already reserves "a future Effect shell behind `ports.ts`" — consistent with deferring.

Effect remains a *possible future strategic bet* (horizon-b), explicitly **out of P1**.

---

## 7. Files — added / modified / deleted (by file + symbol)

Package placement follows `docs/ARCHITECTURE.md`: **Runtime is a context package**
(`packages/runtime/`, canonical `domain/service/ports/adapters/server/events/index`
shape); the desktop lifecycle is plain TS in `desktop/`; the **Gateway is a target
concept, not built in P1** (the Runtime server runs standalone). The flat `host/src/*`
layout the first draft sketched is **retired** — mapped into the canonical shape below
(both plane-vocab reviewers converged on this mapping).

**Added — `@tm/runtime` (`packages/runtime/src/`)**
- `server/` — the router: the five run routes + terminal WS (the standalone Runtime
  server binds a loopback port here; the Gateway mounts this router at the target).
- `service/RunManager.ts` — re-ported run state machine: `spawn`/`attach`/`detach`/
  `terminate`/`list`. Drives `PtyPort`, calls the capture RPC.
- `service/TerminalFanout.ts` — multi-viewer attach orchestration.
- `domain/terminal/ScrollbackRing.ts` — pure byte-capped seq ring (no IO).
- `ports.ts` — `PtyPort`, `CapturePort` (bind/release), `LifecycleSink`, `Clock`.
- `adapters/NodePtyAdapter.ts` — `node-pty` `PtyPort` impl, cross-platform incl. ConPTY.
- `adapters/CaptureRpcClient.ts` — `CapturePort` impl: `prepareCapture`/`releaseCapture`/
  `captureHealth` over the §2c transport.
- `adapters/platform/JobObject.ts` — Windows Job over the PTY agent Runtime spawns (§3).
- `events.ts` — `RunStarted`, `RunExited` (Runtime is the producer).
- `index.ts` — the sole import surface.

**Added — terminal wire contract (shared home)**
- The schema-validated terminal wire types (shape from t3code
  `packages/contracts/src/terminal.ts`) cross into the canvas browser package, so per the
  magic-string rule they are single-sourced in a shared package (`packages/contracts` or
  `@tm/common`), **plain-TS validation (e.g. `zod`), not Effect Schema**.

**Added — desktop lifecycle (plain TS, `desktop/src/`)**
- `app/DesktopLifecycle.ts` — OS-branched signal/quit wiring.
- `backend/DesktopBackendManager.ts` — spawns + owns the Runtime server;
  `graceThenForce`.
- `app/DesktopShutdown.ts` — single teardown coordinator + finalizer that stops the
  Runtime server before `electronApp.quit()`.
- `lifecycle/graceThenForce.ts` — the SIGTERM→grace→SIGKILL helper.

**Added — Python capture sidecar RPC + self-reaping**
- `api/src/transport_matters/capture/rpc.py` — `prepare_capture` / `release_capture` /
  `capture_health` wrapping `prepare_captured_run` + `CapturedRunLease.close`; a
  `run_id`->lease registry.
- `api/src/transport_matters/capture/self_reap.py` — `install_parent_death_reaping()`:
  Linux `prctl(PR_SET_PDEATHSIG)` + getppid guard, macOS watchdog; Python's own Windows
  Job over the mitmproxy child. Runs first in the sidecar entrypoint.

**Modified (Python)**
- `main.py::create_app` — reverse-proxy the **five moved run routes** to the Runtime
  server; keep `exchanges.run_router`, `meta.run_router`, and the rest local. Do **not**
  proxy the `/v1/runs*` prefix.
- `captured_run.py::prepare_captured_run` — unchanged core; now invoked by
  `capture/rpc.py`; its lease held in the RPC registry rather than by the Python
  `RunManager`.
- `run_manager.py` / `api/v1/run_routes.py::run_terminal_socket`, `terminate_run`,
  `create_run`, `bridge_attached_run_terminal` — the lifecycle+terminal serving moves to
  Runtime (slice 4e); deleted or reduced to the proxy target.
- `desktop_runtime.py::is_pid_alive` / `stop_desktop_record` — retire or OS-branch.

**Deleted (Python — replaced)**
- The desktop launcher surface `cli/desktop_cmd.py` — replaced by `DesktopBackendManager`
  (report §8a: "PORTABLE (easy), zero mitmproxy"). Exact symbol list finalized in slice 2.
- `pty_session.py::spawn_pty_process` + `supervisor_pty*.py` — replaced by
  `NodePtyAdapter` in slice 4e.

*(DRY rule: delete the old path completely, no parallel implementations, per §8.)*

---

## 8. PR-slice plan (dependency-ordered, each gated on the repo recipe)

Each slice is independently shippable and gated on `just check` + `just test` (verbatim;
never bare `tsc`/`pytest`/`vitest`).

1. **`@tm/runtime` skeleton + full origin contract (spine).** Scaffold
   `packages/runtime/` in the canonical shape with a standalone `server/` binding a
   loopback HTTP+WS server serving a **stub** run lifecycle (list/get, no PTY). Wire
   Python's `create_app` to reverse-proxy the five moved routes to it and keep
   exchanges/meta/sessions/etc. local. **Acceptance: prove the full canvas origin
   contract** — `createCapturedRun`, `listRuns`, `getRun`, `terminateRun`, the terminal
   WS **and** `fetchExchange`/`fetchMeta` all resolve across the split, incl. the WS
   proxy, in both desktop and web modes. *No real run behaviour yet.*
2. **Desktop lifecycle in plain TS.** `DesktopLifecycle` / `DesktopBackendManager`
   (`graceThenForce` 2s) / `DesktopShutdown` own the Runtime-server process; OS-branched
   signal/quit wiring. Fixes the orphan bug for the server itself (graceful paths).
   *Correctness pair with slice 5.*
3. **Capture RPC seam.** `prepare_capture` / `release_capture` / `capture_health` in
   Python (`capture/rpc.py`) wrapping `prepare_captured_run` + idempotent
   `CapturedRunLease.close`; `CaptureRpcClient` (`CapturePort` impl) in Runtime. Tested
   both sides with a fake caller. *No PTY yet.*
4. **PTY + terminal transport (decomposed — review's Major).**
   - **4a. PTY adapter + wire contract.** `NodePtyAdapter` + the shared `terminalContract`;
     spawn a plain shell, prove PTY spawn/write/resize/onData/onExit + xterm round-trip
     cross-platform. No runs, no capture.
   - **4b. Scrollback + fanout parity.** `ScrollbackRing` + `TerminalFanout` with
     multi-viewer resume-from-seq, against the parity suite (§9). No serving yet.
   - **4c. Create + attach over FAKE capture.** Real `POST /v1/runs` +
     `WS /v1/runs/{id}/terminal` on the Runtime server spawn a PTY agent from a **stubbed**
     envelope (no mitmproxy); full terminal lifecycle, `terminate` path.
   - **4d. Capture RPC integration.** Swap the stub for the real slice-3 RPC; the
     two-lifecycle ordering (§4) lands here.
   - **4e. Route cutover + delete Python.** Move the five routes authoritatively to the
     Runtime server behind the proxy; delete `pty_session.py` + the Python run-serving
     symbols. The DRY "delete the old path" slice.
5. **Cross-platform SIGKILL reaping.** `capture/self_reap.py` (Linux `PR_SET_PDEATHSIG` +
   getppid guard, macOS watchdog, Python's Windows Job over mitmproxy) +
   `packages/runtime/src/adapters/platform/JobObject.ts` (Windows Job over the PTY agent;
   binding per Q7). Retire the POSIX-only launcher debt (§3). *Correctness pair with
   slice 2; the teardown matrix (§9) is its acceptance test.*

Dependency order: 1 → 2 → 3 → 4a → 4b → 4c → 4d → 4e, with 5 after 4d. Slices 2 + 5 are
the coupled correctness pair for teardown; 4d + 4e the coupled cutover pair.

---

## 9. Tests & gates

**Gates (repo recipes, verbatim).** Root `justfile`: `just check`, `just test`. Every
slice passes both. Tests use **Vitest** (not `@effect/vitest` — no Effect).

**New Runtime tests (Vitest, `packages/runtime`)**
- `DesktopBackendManager` / `graceThenForce`: SIGTERM then SIGKILL after the grace;
  teardown stops the Runtime server; no orphan.
- `DesktopLifecycle`: signal registration only when `!== "win32"`; window-quit only
  `!== "darwin"`; all paths converge on `DesktopShutdown`.
- `NodePtyAdapter` (4a): spawn/write/resize/onData/onExit round-trip.
- `ScrollbackRing` / `TerminalFanout` (4b): byte-cap eviction; **multi-viewer
  resume-from-seq** (two attachments, one joins late at a seq cursor, gets the correct
  backlog).
- `CaptureRpcClient` (3): `prepareCapture` returns the envelope; `releaseCapture`
  idempotent; `captureHealth` surfaces a dead proxy.
- **Origin-contract test (slice 1):** all canvas-called routes resolve across the proxy
  split (run routes → Runtime server; exchanges/meta → Python), incl. the WS proxy.

**New Python tests (`cd api && just test`)**
- `capture/rpc.py`: `prepare_capture` starts a proxy + registers a lease by `run_id`;
  `release_capture` calls `CapturedRunLease.close`, idempotent; `capture_health` reflects
  a killed proxy.
- `capture/self_reap.py`: Linux `PR_SET_PDEATHSIG` install + getppid==1 early-exit guard
  (ctypes, `@skipif` off-Linux); macOS watchdog fires on simulated stdin EOF and
  `getppid()==1`; graceful `killpg` reaps a real child tree.
- `main.py` proxy: the five run routes proxy to the Runtime server; exchanges/meta stay
  local.

**Teardown matrix (acceptance test for the correctness core).** For each {foreground,
detached} × {window close, Runtime-server SIGKILL, PTY exit, capture crash,
`POST …/terminate`} on each OS in CI reach: launch, apply teardown, assert **no surviving
`node-pty` agent, no surviving mitmproxy/`mitmdump`, no orphaned Runtime server**. The §4
+ §3 acceptance test (scripted harness, partly manual given Electron E2E weight).
Windows/Linux reap by construction, macOS by watchdog.

---

## 10. Open questions & risks

1. **Q1 — RESOLVED (was the blocker).** Web `/canvas` serving: Python stays the origin
   front door and reverse-proxies **only the five moved run routes** to the Runtime
   server; exchanges/meta/sessions/spaces/bundle stay Python. Per-route, never the
   `/v1/runs*` prefix. Slice 1 proves the full origin contract.
2. **Q2 — Capture RPC transport.** Loopback HTTP/JSON (independently testable) vs stdio
   JSON-RPC over the managed-child pipe. Recommend loopback HTTP; revisit if port
   pressure appears.
3. **Q3 — RESOLVED.** Effect vs plain TS → **plain TS** (§6). Not revisited in P1.
4. **Q4 — Grace budget.** Upstream uses 2s. Confirm the Python capture sidecar flushes
   and exits within the grace on SIGTERM, or force-kill drops in-flight capture writes.
   Not yet measured.
5. **Q5 — Detached-run ownership (report §9.1).** Should a detached run survive viewer
   close, or should close stop it? Confirm before slice 2.
6. **Q6 — RESOLVED (naming).** The run host is the **Runtime** context, `packages/runtime/`
   (`@tm/runtime`), canonical context shape — not a top-level `host/` (`@tm/host` is
   taken) and not `desktop/src/host/`. In P1 the Runtime server runs standalone; the
   **Gateway** (a separate composition-root app, `packages/gateway`, per
   `docs/ARCHITECTURE.md`) subsumes it at the target and is **not built in P1**.
7. **Q7 — Windows Job Object binding (from §3).** N-API native addon vs bundled helper
   exe vs an existing npm shim for `CreateJobObject`/`AssignProcessToJobObject`. A real
   dependency + packaging decision; blocks slice 5 on Windows. Recommend surveying
   existing npm bindings before writing a native addon.
8. **Q8 — Supervised process entry must forward SIGTERM (empirical, PR #200 review).**
   Gateway `start` runs `tsx src/main.ts` (via pnpm). A supervised `kill -TERM
   <tsx-wrapper pid>` kills the wrapper (143) **without forwarding** to the node
   child, so `main.ts`'s graceful SIGINT/SIGTERM handler (`await app.close()`)
   never runs on that path. Verified: interactive Ctrl-C (SIGINT to the process
   group) and single-process `node --import tsx` + SIGTERM both reach the handler
   → exit 0 + socket released. Slice-2 implication: `DesktopBackendManager`'s spawn
   shape must deliver the signal to the process that installed the handler — exec
   into node (no wrapper), a signal-forwarding launcher, or spawn `node --import
   tsx` directly — and Q4's grace budget must be measured against the real spawn
   shape, not the tsx-wrapper shape. cm `019f2df2`.

**Risk register:** (i) two-lifecycle teardown ordering (§4) — the sharpest new correctness
surface; (ii) preserving multi-viewer resume-from-seq (real product behaviour absent from
t3code); (iii) the per-route serving split (§2b) touching both origins, **including the
WebSocket reverse-proxy of `/v1/runs/{id}/terminal` through the Python front door — the
sharpest slice-1 risk**; (iv) Windows Job Object binding (Q7) heavier than expected; (v)
`graceThenForce` grace dropping capture writes (Q4); (vi) supervised SIGTERM not
reaching the graceful handler through the tsx/pnpm wrapper (Q8) — a slice-2
process-entry constraint. None are showstoppers.

---

## 11. Sequencing note — worktree, Activity

The checkpoint's worktree caveat ("branch from a ref where the Effect scaffolding is
committed") rested on the premise that Activity introduced Effect. **Verified false:**
Activity uses `xstate`, and no Effect exists in the tree. With the plain-TS decision
(§6), P1 introduces **no** new runtime paradigm — `packages/runtime/` + `desktop/` are
plain TS + Vitest like the rest of the stack.

Consequences:
- The worktree can branch from **any current ref**. No scaffolding to wait for. The
  checkpoint's sequencing constraint is **removed**.
- P1 is disjoint from the Activity WIP (Activity = Postgres event reads; P1 = desktop
  lifecycle + Runtime). Parallel worktrees are safe.
- `packages/runtime/` and `packages/activity/` are siblings under the same context-package
  rule; the shared terminal wire contract wants a `packages/contracts` / `@tm/common`
  home, which the Activity-topology question (report §9.5) also touches.

---

*Author: opus. Independently reviewed by codex (`tm-t3code-p1-spec-review.md`): 1 Blocker
+ 3 Majors + 1 Minor, all folded in. Effect→plain-TS by Stuart; Runtime/Gateway naming
locked by Stuart via a 2-agent MoE (`tm-plane-vocab-{opus,codex}.md`). Proposal only; no
product code committed. All current-tree facts re-verified.*
