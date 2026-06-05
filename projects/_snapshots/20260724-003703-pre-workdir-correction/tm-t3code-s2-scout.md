---
title: Scout report — t3code P1 Slice 2 (B-S2): Desktop lifecycle in plain TS
type: projects
tags: [transport-matters, t3code, p1, slice-2, desktop, lifecycle, scout]
summary: Build-ready scout for B-S2. Resolves the process-ownership ambiguity from code — at slice 2 DesktopBackendManager owns the EXISTING Python backend the desktop already spawns (`transport-matters _desktop-backend`), not a new @tm/gateway node process. The gateway is optional/unspawned until 4e. Maps the reuse surface, confirms the graceful-orphan bug origin (no signal handlers on Electron main + SIGTERM-only teardown with no force-kill), and gives an ordered plan bound to existing symbols.
status: active
source: scout (opus) — recon only, no source modified
confidence: high
created: 2026-07-07
updated: 2026-07-07
---

# Scout report — B-S2: Desktop lifecycle in plain TS

**Status: BUILD-READY.** The one ambiguity is resolved from code, not left open.

**One-line resolution:** At slice 2 `DesktopBackendManager` owns the **existing Python
backend** the desktop already launches (`transport-matters _desktop-backend`, a single
Python console-script process) — **not** a new `@tm/gateway` node process. Slice 2 is
pure lifecycle hardening around the *same* spawn shape; the gateway stays optional and
unspawned until the 4e cutover.

Repo re-verified on `main` (includes slice 0 gateway PR #200 and slice 1 runtime PR
#231). Citations are file + symbol.

---

## 4. THE process-ownership resolution (highest-value finding)

**Question:** does `DesktopBackendManager` spawn/own (a) the existing Python backend, or
(b) a new `@tm/gateway` node process?

**Answer: (a), unambiguously.** Evidence:

1. **The desktop spawns Python today.** `desktop/src/backendProcess.ts::buildBackendLaunch`
   builds `command: "transport-matters"` with `args: ["_desktop-backend", "--work-dir",
   …, "--web-port", …, "--proxy-port", …, "--channel", …]`. `launchBackendProcess`
   spawns it via `child_process.spawn`. `transport-matters` is the Python
   console-script (the FastAPI/uvicorn front door). This is the process the Electron
   main owns.

2. **Slice 1 kept Python as the env-gated origin.** `api/src/transport_matters/main.py::create_app`:
   ```
   if settings.gateway_url:
       proxy_mount = run_proxy.create_run_proxy_mount(gateway_url=…)
       app.include_router(proxy_mount.router, prefix="/v1")
   else:
       app.include_router(run_routes.router, prefix="/v1")   # ← serves run routes LOCALLY
   ```
   `config.py::Settings.gateway_url` is env `TRANSPORT_MATTERS_GATEWAY_URL` (`env_keys.GATEWAY_URL`),
   **default `None`**. The desktop launch (`buildBackendLaunch`) does **not** set it, so
   Python serves the run routes itself. The reverse-proxy path is dormant in the desktop
   configuration.

3. **Nothing spawns the gateway.** Grep of `desktop/` and `api/` for gateway spawn/launch:
   no hit. `@tm/gateway` (`packages/gateway/src/main.ts::runGatewayProcess`) is a
   **standalone** node process started only by its own `start` script (`tsx src/main.ts`)
   and already carries its **own** SIGINT/SIGTERM handlers (`installShutdownHandlers`).
   It is a serving root that mounts the runtime + activity routers; per
   `packages/AGENTS.md` "Python remains the interim origin until the Gateway takes over."

4. **The spec's own scoping agrees.** `tm-t3code-p1-spec.md` §7 / §8-slice-2 name the
   managed child "the Runtime server," but the route cutover that moves run-serving off
   Python is **slice 4e**, explicitly after slice 2. The brief's binding is "adopt the
   NAMES, not the runtime." So `DesktopBackendManager` is the **name**; the **process** it
   manages at slice 2 is still the Python backend. Calling it "Runtime server" in slice-2
   code would be a lie about what is spawned.

**Builder guidance:** keep the `transport-matters _desktop-backend` command exactly as
today (`buildBackendLaunch`). Slice 2 changes *how the child is torn down and how signals
reach the teardown*, not *what is spawned*. The rename to a gateway/runtime process is a
future slice's concern; do not smuggle it in.

*Verify item (Q8-analogue, carry):* `transport-matters` is a Python console-script
(single process, no pnpm/tsx wrapper), so a SIGTERM to it reaches the Python signal
handler directly — Q8's tsx-wrapper hazard does **not** bite the slice-2 Python spawn.
The builder should still confirm `_desktop-backend` runs uvicorn **in-process** rather
than forking a grandchild uvicorn (if it forks, the grace-then-force SIGKILL must reach
the process group, not just the console-script pid). This is where §3's "subtree reap"
concern lands for the slice-2 shape.

---

## 1. Reuse Map

### Reuse (existing symbol the builder must build on, not replace)

| Capability | Owner (path :: symbol) | Disposition |
| --- | --- | --- |
| Spawn + own the backend child | `desktop/src/backendProcess.ts::launchBackendProcess`, `::buildBackendLaunch`, `::LaunchedBackendProcess`, `::BackendChildProcess` | **Reuse the spawn shape verbatim.** `DesktopBackendManager` wraps these; the command/env builder does not change. |
| Detect child exit | `desktop/src/backendProcess.ts::watchBackendExitBeforeReady` | Reuse to observe exit during grace and at startup. |
| Grace-then-force **semantics** (SIGTERM → poll → SIGKILL) | `api/src/transport_matters/desktop_runtime.py::stop_desktop_record` (`timeout_s=3.0`, `poll_s=0.1`, then `SIGKILL`) | **Semantic reference to port into TS.** No TS grace-then-force exists (grep confirms). `graceThenForce.ts` re-expresses this loop in TS over a `child_process` child. Note grace-budget discrepancy: this Python path uses **3s**; spec/t3code says **2s** (Q4). |
| window-all-closed darwin gate | `desktop/src/main.ts::bindHostedWindowLifecycle` (`process.platform !== "darwin"`) | **Already exists.** `DesktopLifecycle` must **consolidate/reuse** this gate, not re-declare it (DRY flag below). |
| Readiness / liveness health | `desktop/src/backendHealth.ts::waitForBackendHealth`, `::isBackendHealthy`; `desktop/src/hostedLiveness.ts` | Reuse unchanged for startup readiness; **not** part of teardown. |
| Idempotent "shutdown once" guard pattern | `packages/gateway/src/main.ts::installShutdownHandlers` (`shuttingDown` boolean; SIGINT/SIGTERM `process.once` → single async shutdown → `exit`) | **Reference pattern** for `DesktopShutdown`'s resolve-once coordinator. Not directly importable (Fastify-app close, not Electron), but the shape is the plain-TS analogue of t3code's `Deferred`. |
| Existing quit-cleanup wiring (to reshape) | `desktop/src/main.ts::bindBackendQuitCleanup`, `::registerAppLifecycle` | **Reshape/replace.** `bindBackendQuitCleanup` binds only `before-quit` and calls the SIGTERM-only `stopBackendProcess` — this is the weak path slice 2 fixes. |

### Existing infra (context, not directly reused)

- `packages/runtime/src/server/runtimeRouter.ts` — slice-1 in-memory run router (stub
  run lifecycle + echo terminal WS). Not touched by slice 2 (it is served by the
  gateway, which slice 2 does not spawn).
- `api/src/transport_matters/api/v1/run_proxy.py::forward_terminal` — slice 1 already
  built the **WS reverse-proxy** through the Python front door (the spec's sharpest
  slice-1 risk, now landed). Confirms the origin-contract split is done; irrelevant to
  slice-2 teardown.

### Similar-checked-and-rejected

- `desktop/src/packageSmoke.ts` (`child.kill?.("SIGTERM")`) — a smoke harness's
  teardown, SIGTERM-only, no grace. Not a reusable grace-then-force; do not lift.
- `packages/gateway/src/main.ts::installShutdownHandlers` — same-process app close, not
  a managed-**child** teardown. Reference for the coordinator's idempotency, not for the
  kill mechanism.

### None-found (net-new, with searches run)

- **TS grace-then-force (SIGTERM→timer→SIGKILL) over a child.** Searches:
  `grep -rn "SIGKILL|SIGTERM|SIGINT" desktop/src packages --include=*.ts` →
  only `backendProcess.ts` (SIGTERM-only), `packageSmoke.ts` (SIGTERM-only),
  `gateway/src/main.ts` (signal names for app close). **`graceThenForce.ts` is net-new.**
- **POSIX-signal handlers on the Electron main.** Search:
  `grep -rn "process.on|process.once" desktop/src --include=*.ts` → **no hits.** The
  Electron main installs **no** SIGINT/SIGTERM handler today. `DesktopLifecycle`'s signal
  registration is net-new (this is the orphan-bug root, below).

---

## 2. Quality Map

- **DRY (must-not-duplicate):** the `process.platform !== "darwin"` window-quit gate
  already lives in `main.ts::bindHostedWindowLifecycle`. `DesktopLifecycle` must own the
  single home for OS branches — fold the existing gate in, do not copy it. Likewise the
  spawn/command builder stays single-sourced in `backendProcess.ts`; `DesktopBackendManager`
  composes it.
- **Boundary:** slice 2 lives entirely in `desktop/src/` (plain TS). It touches **no**
  Python. The Python POSIX-only debt (`desktop_runtime.py::is_pid_alive`,
  `::stop_desktop_record`, `cli/desktop_cmd.py` `start_new_session=True`) is **spec §3 /
  slice-5** work — **leave it**. Note those symbols are still **live** on the CLI
  `channel stop` / `_desktop-reclaim` path (`desktopRuntime.ts::reclaimDesktopRuntime`),
  not dead; slice 2 neither uses nor retires them. `stop_desktop_record` is only a
  *semantic* reference for `graceThenForce`.
- **File size:** `desktop/src/main.ts` is ~656 lines (under the 700 hard limit, but
  large). Slice 2's extraction of the three seams into `desktop/src/app/` +
  `desktop/src/backend/` + `desktop/src/lifecycle/` **reduces** `main.ts`. Good — the
  reshape moves `registerAppLifecycle` orchestration + `bindBackendQuitCleanup` + the
  darwin gate into the named seams. Do not grow `main.ts`.
- **Grooming recommendation:** delete `bindBackendQuitCleanup` (and its SIGTERM-only
  reliance on `stopBackendProcess`) as part of the reshape — no parallel teardown path.
  `stopBackendProcess` itself either becomes the trivial happy-path inside
  `graceThenForce` or is deleted in favour of it (DRY: one kill path).

---

## 3. Verified entry points (claimed → actual)

| Brief/spec claim | Actual in tree | Drift |
| --- | --- | --- |
| `desktop/src/main.ts` — app lifecycle, window-all-closed, quit, signals | Exists. `registerAppLifecycle`, `bindBackendQuitCleanup` (before-quit only), `bindHostedWindowLifecycle` (has the darwin gate). **No signal handlers.** | Signal handling **absent** — net-new, not "reshape." |
| `desktop/src/backendProcess.ts` — spawn/own backend, kill/teardown, grace/force | Exists. `launchBackendProcess` (spawn), `stopBackendProcess` (**SIGTERM-only, no force**), `watchBackendExitBeforeReady`. | **No grace/force logic exists** — the force half is net-new. |
| `desktop/src/desktopRuntime.ts`, `backendHealth.ts` — runtime/health wiring | Both exist. `desktopRuntime.ts` = CLI status/reclaim shim (`execFileSync transport-matters channel status`). `backendHealth.ts` = readiness polling. | None. Health reused as-is; `desktopRuntime.ts` is the reclaim path, out of slice-2 teardown scope. |
| `desktop_runtime.py::is_pid_alive` / `stop_desktop_record`; `cli/desktop_cmd.py` `start_new_session=True` (POSIX-only debt) | All present. `stop_desktop_record` = full SIGTERM→3s poll→SIGKILL. `desktop_cmd.py::prepare_desktop_launch` builds the detached Electron/backend launch. | **Slice 5** retires these, not slice 2. Slice 2 ports the *semantics* of `stop_desktop_record` into TS. |
| "SharedProxyProcess / ProcessSupervisor reusable supervisor" | Python `ProcessSupervisor` is the **mitmproxy capture** supervisor (`captured_run.py`), **not** a desktop-child supervisor. No reusable TS supervisor. | Reuse claim rejected — `graceThenForce` is net-new in TS. |
| "DesktopBackendManager spawns the Runtime server" | Desktop spawns the **Python** backend; gateway/runtime node process is **unspawned**. | **Resolved in §4** — managed child = Python at slice 2. |

---

## 5. Plan (ordered, bound to the reuse map)

*No decision needed — build-ready.* Gate every step on the repo recipe.

1. **`desktop/src/lifecycle/graceThenForce.ts` (net-new).** `graceThenForce(child,
   { graceMs, signal }): Promise<void>` — send SIGTERM (or the given signal), race the
   child's `exit` (via `watchBackendExitBeforeReady`-style listener) against a
   `graceMs` timer; on timeout send SIGKILL; resolve once exited. Semantics ported from
   `desktop_runtime.py::stop_desktop_record`. **Q4:** default `graceMs` — reconcile the
   spec's 2s (t3code) against the existing Python 3s; recommend surfacing it as a named
   constant and matching the Python precedent unless a measurement says otherwise.
   *Unit-testable with a fake child (fake exit / fake ignore-SIGTERM).*

2. **`desktop/src/backend/DesktopBackendManager.ts` (net-new, wraps existing).** Owns the
   spawned child. `start()` composes `backendProcess.ts::buildBackendLaunch` +
   `launchBackendProcess` (**reuse**, unchanged command). `stop()` = `graceThenForce`
   over the owned child. Replaces `stopBackendProcess`'s SIGTERM-only kill. Idempotent
   (double-stop is a no-op).

3. **`desktop/src/app/DesktopShutdown.ts` (net-new).** Single teardown coordinator: a
   resolve-once promise / guard (pattern from `gateway/src/main.ts::installShutdownHandlers`
   `shuttingDown`). A finalizer calls `DesktopBackendManager.stop()` and **awaits it
   before** `app.quit()`, so quit never races teardown. Every quit path funnels here.

4. **`desktop/src/app/DesktopLifecycle.ts` (net-new, consolidates existing OS branch).**
   - Register `SIGINT`/`SIGTERM` **only when `process.platform !== "win32"`** →
     converge on `DesktopShutdown`. (Fixes the primary orphan path — see §6.)
   - window-all-closed quit gated on `process.platform !== "darwin"` — **fold in the
     existing gate** from `bindHostedWindowLifecycle` (DRY; do not duplicate).
   - `before-quit` → `DesktopShutdown` (replacing `bindBackendQuitCleanup`).

5. **Rewire `main.ts::registerAppLifecycle`** to compose the four seams; **delete**
   `bindBackendQuitCleanup` and collapse/remove `stopBackendProcess` so there is one
   kill path (`graceThenForce`). Keep the hosted path (`registerHostedDesktopLifecycle`)
   as-is (it attaches to a live runtime and owns no child — no orphan there).

**Tests (Vitest, `desktop/src/*.test.ts` colocated).**
- `graceThenForce`: SIGTERM sent; SIGKILL sent iff child survives grace; resolves on
  early exit without SIGKILL.
- `DesktopBackendManager`: teardown stops the child; no orphan; double-stop idempotent.
- `DesktopLifecycle`: SIGINT/SIGTERM registered iff `!== "win32"`; window-quit iff
  `!== "darwin"`; **every** path (signal, before-quit, window-all-closed) reaches
  `DesktopShutdown`; finalizer awaits backend stop before `app.quit()`.

**Gates (verbatim).** Root `just check` / `just test` → `cd desktop && just check` =
`pnpm typecheck` + `pnpm test` (Vitest). CI `desktop` job runs
`pnpm --filter transport-matters-desktop typecheck | test | build` + xvfb package smoke.
Do **not** gate on bare `tsc`/`vitest`.

---

## 6. Open risks / carries

- **Orphan-bug origin (confirmed real).** Two graceful paths leak the Python backend:
  1. **Signal paths (primary).** The Electron main installs **no** SIGINT/SIGTERM
     handler (`grep process.on|process.once desktop/src` → none). A SIGINT (Ctrl-C in the
     launching terminal) or SIGTERM to the Electron main does **not** emit Electron's
     `before-quit`, so `bindBackendQuitCleanup` never fires and the Python child is
     orphaned. This is *the* graceful orphan slice 2 fixes.
  2. **Even on `before-quit`.** `stopBackendProcess` sends **SIGTERM only, no force-kill**
     — a child that is slow to honour SIGTERM (mitmproxy flush, in-flight writes) is
     orphaned. `graceThenForce` closes this.
  (macOS window-all-closed intentionally does **not** quit — that is the darwin gate, not
  a bug. The hosted/attached path owns no child, so it cannot orphan one.)
- **Q4 (carry — do not resolve).** Does the Python `_desktop-backend` (with its mitmproxy
  capture child) flush and exit within the grace on SIGTERM, or does the SIGKILL drop
  in-flight capture writes? **Where measured:** the `graceThenForce` grace window against
  a real `transport-matters _desktop-backend` SIGTERM. Compounded by the **2s (spec) vs
  3s (existing `stop_desktop_record`) grace discrepancy** and by whether the console-script
  forks a uvicorn grandchild that needs process-group reaping. Not measured here.
- **Q5 (carry — product decision, do not decide).** Whether a **detached** run survives
  viewer close or close stops it. Today `registerHostedDesktopLifecycle` attaches to an
  already-live runtime it does **not** own, and `bindHostedWindowLifecycle` for the
  hosted path quits on window-all-closed (`quitOnWindowAllClosed: true`) — but quitting
  the viewer there does not tear down the separately-owned runtime. Flagging the seam;
  the ownership call is Stuart's.
- **Q8 (carry, slice-2-adjacent).** Supervised SIGTERM must reach the process that
  installed the handler. At slice 2 the child is the single-process Python console-script
  (no tsx/pnpm wrapper), so this is clean **unless** `_desktop-backend` forks uvicorn —
  verify. The hazard bites in earnest at 4e if the managed child becomes the tsx-wrapped
  gateway.

---

## 7. Recommended build order

`graceThenForce` → `DesktopBackendManager` → `DesktopShutdown` → `DesktopLifecycle` →
rewire `registerAppLifecycle` + delete `bindBackendQuitCleanup`/`stopBackendProcess`.
Land tests with each seam. One PR, gated on `just check` + the CI `desktop` job. Slice 2
pairs with slice 5 (SIGKILL parent-death reaping) for the full teardown matrix, but slice
2 ships independently as the graceful-path fix.
