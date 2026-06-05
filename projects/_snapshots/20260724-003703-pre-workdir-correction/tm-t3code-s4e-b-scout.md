---
title: Plan — t3code P1 Slice 4e-b, desktop spawns the gateway as a second managed child
type: projects
tags: [transport-matters, t3code, p1, slice-4e-b, scout, plan, desktop, gateway, shutdown-ordering]
summary: Build plan for 4e-b. Desktop spawns @tm/gateway as a second managed child beside the Python backend, gateway pointed at Python's capture RPC, gateway-before-Python shutdown ordering enforced by DesktopShutdown finalizer position and pinned by test. No cutover, no deletion; both run paths stay live. DRY via a generic child manager over the existing DesktopBackendManager seam, a gatewayProcess.ts mirroring backendProcess.ts, a gatewayPort per channel spec, and a healthUrl-generalized readiness probe. Q8-safe spawn shape (node directly on the entry, never a pnpm/tsx wrapper); packaged-node resolution explicitly deferred to the D1 pole.
status: active
source: scout (fable 5:2.1), reconciled against main @ ce294eb (4e-a merged)
confidence: high (all symbols read first-hand on main)
created: 2026-07-08
---

# Plan — Slice 4e-b: dual managed children (Python backend + gateway)

Scope per brief: desktop spawns **both** children; gateway reaches Python's capture
RPC; shutdown tears the gateway down **before** Python. No canvas cutover (Python's
`TRANSPORT_MATTERS_GATEWAY_URL` stays unset; `run_routes.router` keeps serving), no
deletion. Citations are file + symbol.

---

## 1. Current state — where the Python child is spawned and supervised

One managed child today, owned end to end by four seams:

- **Launch shape.** `desktop/src/backendProcess.ts::buildBackendLaunch` builds
  `{command: "transport-matters", args: [_desktop-backend, --work-dir, --web-port,
  --proxy-port, --channel], cwd: workspaceDir, env}` from `BackendLaunchOptions
  {env?, proxyPort, webPort, workspaceDir}`; `launchBackendProcess` spawns it with
  `stdio: "pipe"`. Env written: `ENV.CHANNEL/CWD/PROXY_PORT/WEB_PORT`
  (`desktop/src/env.ts::ENV`, mirror of `api .../env_keys.py`).
- **Supervision.** `desktop/src/backend/DesktopBackendManager.ts::DesktopBackendManager`
  — single-start guard, exit-clears-ownership, memoized `stop()` via
  `lifecycle/graceThenForce.ts::graceThenForce` (SIGTERM → 2s
  `DESKTOP_BACKEND_STOP_GRACE_MS` → SIGKILL). The launcher is already an injected
  dependency (`dependencies.launchBackend`), which is the reuse hook this slice needs.
- **Readiness.** `main.ts::waitForLaunchedBackend` races
  `backendHealth.ts::waitForBackendHealth({webPort})` (polls
  `backendHealthUrl(webPort)` = `http://127.0.0.1:{port}/health`, 15s budget) against
  `backendProcess.ts::watchBackendExitBeforeReady` (fail fast on early exit).
  `startBackendAndCreateWindow` stops the child and rethrows on readiness failure;
  `showBackendStartupFailure` shows the dialog and quits.
- **Shutdown.** `main.ts::registerAppLifecycle` constructs
  `DesktopShutdown({appSource: app, finalizers: [() => backendManager.stop()]})`;
  `app/DesktopShutdown.ts::DesktopShutdown.#runShutdown` awaits finalizers
  **sequentially in array order** (each error logged, never aborting the chain), then
  allows quit. `DesktopLifecycle.registerShutdownHooks` funnels every quit path in.
- **Ports.** `main.ts::resolveBackendStartupOptions`: env pin (`ENV.PROXY_PORT`/
  `ENV.WEB_PORT`) > live-runtime ports (`desktopRuntime.ts::liveRuntimePorts`) >
  channel spec defaults (`channel-specs.json`: stable 8787/8788, preview 8797/8798).
- **Hosted/reattach mode** (`liveRuntimeRouteUrl` hit, or `ENV.DESKTOP_ROUTE_URL`):
  the desktop attaches to an existing backend and spawns **nothing**. This mode gets
  no gateway in 4e-b either (attach-only semantics preserved; consequence flagged in §8).

**Gateway process contract** (`packages/gateway/src/main.ts::runGatewayProcess`,
re-verified): binds `127.0.0.1`, port from `TRANSPORT_MATTERS_GATEWAY_PORT` (else
ephemeral), capture via `TRANSPORT_MATTERS_CAPTURE_RPC_URL` (else warns + stub,
runs spawn UNCAPTURED), Activity via `TRANSPORT_MATTERS_DATABASE_URL` (else warns +
disabled), `GET /health` served by `app.ts::buildGateway`, graceful SIGINT/SIGTERM →
`closeGatewayResources` (`app.close()` → `runManager.close()` → activity close) —
`RunManager.close` terminates every PTY and calls `releaseCapture` per run (4e-a
sends real end facts).

---

## 2. Dual-child design (DRY: one supervisor seam, two children)

### 2a. Generalize the child manager, do not fork it

`DesktopBackendManager` contains zero Python-specific logic except its default
launcher and the `BackendLaunchOptions` type on `start()`. Make it generic:

- `DesktopBackendManager<TOptions = BackendLaunchOptions>` with
  `launchBackend?: (options: TOptions) => LaunchedBackendProcess` and
  `start(options: TOptions)`. Behavior (single-start, stop memo, graceThenForce,
  exit-clears-ownership) unchanged; existing construction sites compile as-is via the
  default type parameter. No second manager class, no copied lifecycle code.
- `registerAppLifecycle` instantiates two: `backendManager` (as today) and
  `gatewayManager = new DesktopBackendManager({launchBackend: launchGatewayProcess})`.

### 2b. New `desktop/src/gateway/gatewayProcess.ts` (mirrors backendProcess.ts)

- `GatewayLaunchOptions {env?, gatewayPort, captureRpcUrl, workspaceDir}`.
- `buildGatewayLaunch(options)` → `{command, args, cwd, env}` with env:
  `TRANSPORT_MATTERS_GATEWAY_PORT={gatewayPort}`,
  `TRANSPORT_MATTERS_CAPTURE_RPC_URL={captureRpcUrl}`, plus the inherited env spread
  (which carries `TRANSPORT_MATTERS_DATABASE_URL` through when the operator has it —
  Activity stays warn-disabled otherwise, acceptable in 4e-b since nothing consumes
  the gateway yet).
- `launchGatewayProcess(options, spawn?)` → `LaunchedBackendProcess` (reuses the
  existing `BackendChildProcess`/`LaunchedBackendProcess` types and
  `watchBackendExitBeforeReady` unchanged — they are child-shape-agnostic).

`captureRpcUrl = http://127.0.0.1:{webPort}` (origin only): verified
`CaptureRpcClient.request` builds `${basePath}/v1/capture/...` and sends
`origin: baseUrl.origin`; Python's `require_http_origin` →
`terminal_bridge.origin_allowed_from_headers` accepts it because fetch's Host header
(`127.0.0.1:{webPort}`) is a `_TERMINAL_LOOPBACK_HOSTS` member on
`settings.web_port` and origin == request-origin. No trust-config change needed.

### 2c. Spawn shape (Q8-safe) and entry resolution

Spec Q8 (verified empirically in the spec, cm 019f2df2): a pnpm/tsx **wrapper
swallows SIGTERM** — the graceful handler in `runGatewayProcess` would never run and
every quit would be a 2s-grace SIGKILL with leaked run teardown. So the desktop must
deliver SIGTERM to the node process that installed the handler:

- **Dev (this slice's target per brief):** spawn system `node` from PATH with
  `args: ["--import", "tsx", <gatewayEntry>]`, `cwd: <repo>/packages/gateway` (tsx is
  a gateway devDependency; cwd-anchored resolution finds it). System node matches the
  pnpm-installed `node-pty` prebuild ABI.
- **Entry resolution:** a named `resolveGatewayEntry(env)` — env override
  `TRANSPORT_MATTERS_GATEWAY_ENTRY` first, else walk up from `moduleDir`
  (`desktop/dist`) to the workspace root by `pnpm-workspace.yaml` marker and join
  `packages/gateway/src/main.ts`. Do NOT hardcode a `join(moduleDir, "..", "..")`
  depth (the depth-relative-join class broke main after PR8; and `process.cwd()` is
  the USER's workspace in real launches, never the repo — unusable as an anchor).
- **Packaged app:** explicitly deferred, flagged as the D1-adjacent pole (§8). Note
  for that decision: `ELECTRON_RUN_AS_NODE=1` + `process.execPath` avoids shipping a
  node binary but runs Electron's Node ABI — the gateway's `node-pty` prebuilds are
  system-node ABI, so that route requires an electron-rebuild of node-pty. Ship-a-node
  vs electron-rebuild is D1's call, not 4e-b's.

### 2d. Ports

Add `gatewayPort` to `channel-specs.json` (stable **8789**, preview **8799** — the
free slots beside proxy/web). Both parsers are additive-tolerant:
`desktop/src/env.ts::normalizeChannelSpec` gains `gatewayPort: requirePort(...)`;
Python `channel.py::_build_channel_spec` picks named keys and ignores extras — add
`gateway_port` there too (one mirror rule, `env.ts` docstring already binds the two
files). Env pin `ENV.GATEWAY_PORT` (`TRANSPORT_MATTERS_GATEWAY_PORT`, the exact key
the gateway already reads) joins `resolveBackendStartupOptions`'s pin>spec chain.
Never port 0: a deterministic port keeps the launch contract declarative (no stdout
parsing) and gives 4e-d a stable `TRANSPORT_MATTERS_GATEWAY_URL` target.

---

## 3. Startup sequence

In `registerAppLifecycle` (fresh-spawn branch only):

1. Resolve `startupOptions` as today + `gatewayPort` (pin > channel spec).
2. Spawn **both** children (order-independent: the gateway needs only the webPort
   VALUE for `captureRpcUrl`, not a live Python; its capture calls happen at run
   create, long after Python is healthy).
3. Readiness: extend the existing race to both children —
   `waitForBackendHealth` generalized to accept a `healthUrl` (today it derives one
   from `webPort`; add the parameter rather than a second poller — DRY) and awaited
   for `http://127.0.0.1:{gatewayPort}/health` alongside the Python probe, each raced
   against its own `watchBackendExitBeforeReady`.
4. On either readiness failure: stop BOTH managers (gateway first, same invariant),
   then `showBackendStartupFailure` as today.
5. Window creation stays gated exactly as today on Python health (the canvas is
   served by Python and runs still live there in 4e-b); the gateway gate runs in the
   same `Promise.all` so a broken gateway fails the launch loudly instead of shipping
   a silently-degraded topology (decision D-b1, §8).

Hosted/reattach and `DESKTOP_ROUTE_URL` branches are untouched (no children spawned
there today; no gateway either).

---

## 4. Shutdown ordering invariant (the correctness core)

**Invariant: gateway stops before Python.** The gateway owns runs; its graceful
teardown (`runGatewayProcess::installShutdownHandlers` → `closeGatewayResources` →
`RunManager.close`) terminates PTYs and calls `releaseCapture(runId, facts)` against
Python's `/v1/capture/{id}/release`. Python must still be alive to close the
mitmproxy leases with the gateway's real end facts and emit the RUN_EXITED rows
(4e-a's `CaptureLeaseRegistry.release_capture`).

**Where it lives:** the `DesktopShutdown` finalizer array in `registerAppLifecycle`:

```ts
finalizers: [() => gatewayManager.stop(), () => backendManager.stop()]
```

`DesktopShutdown.#runShutdown` awaits finalizers sequentially in array order and a
finalizer error logs-and-continues, so ordering is enforced by construction: the
gateway's full graceThenForce (SIGTERM → graceful release → exit, or 2s → SIGKILL)
completes before Python's SIGTERM is ever sent. Every quit path funnels through this
one coordinator (`DesktopLifecycle.registerShutdownHooks`), so there is no second
ordering to keep consistent.

**Failure mode if inverted (Python first):**
- The gateway's `releaseCapture` calls hit a dead socket → `CaptureRpcError
  capture_rpc_unavailable` per run (fails fast on refusal; bounded by
  `DEFAULT_RELEASE_CAPTURE_TIMEOUT_MS`=5s if hung instead) → quit latency and error
  noise scale with live runs.
- End-fact fidelity is lost: Python's lifespan `registry.close()` already emitted
  RUN_EXITED with a generic `shutdown` reason for every still-held lease; the
  gateway's real endReason/exitCode never lands.
- If Python needed the SIGKILL half of its grace, `registry.close()` never ran and
  the mitmproxy children leak outright (nothing reaps them until slice 5's
  self-reaping lands).

**Enforcement tests:** see §6 — an ordering test with fake children that records the
interleaving and asserts the gateway child's exit resolves before the Python child's
kill is issued, plus an inversion-style regression (finalizer order is data, so the
test pins the data).

---

## 5. Health/readiness answer (brief Q4)

- Desktop gates "ready" on **both**: Python health (unchanged — the window URL
  `rendererUrlForPort(webPort)` is Python-served, and the canvas load path expects
  only Python in 4e-b) **and** gateway health (`GET /health` already exists on
  `buildGateway`). Rationale: the slice's deliverable IS the dual-child topology;
  a warn-only gateway would make 4e-d's flip land on machines where the gateway
  never actually worked. Flagged as decision D-b1 since it hard-couples desktop
  startup to a working local node toolchain.
- The hosted liveness poll (`hostedLiveness.ts`) stays Python-only: it decides
  "backend gone → quit", and Python remains the origin.

---

## 6. Touch list (file + symbol) — 10 files + 2 spec JSON edits

| File | Change |
| --- | --- |
| `desktop/src/backend/DesktopBackendManager.ts` | generic `DesktopBackendManager<TOptions = BackendLaunchOptions>`; `start(options: TOptions)`; dependency `launchBackend?: (options: TOptions) => LaunchedBackendProcess` |
| `desktop/src/gateway/gatewayProcess.ts` (new) | `GatewayLaunchOptions`, `buildGatewayLaunch`, `launchGatewayProcess`, `resolveGatewayEntry` (env override + workspace-root marker walk) |
| `desktop/src/env.ts` | `ENV.GATEWAY_PORT`; `DesktopChannelSpec.gatewayPort`; `normalizeChannelSpec` requirePort |
| `api/src/transport_matters/channel-specs.json` | `gatewayPort`: stable 8789, preview 8799 |
| `api/src/transport_matters/channel.py` | `ChannelSpec.gateway_port` + `_build_channel_spec` (mirror rule) |
| `desktop/src/backendHealth.ts` | `waitForBackendHealth` accepts `healthUrl` (derive-from-webPort stays the default; one poller, two callers) |
| `desktop/src/main.ts` | `resolveBackendStartupOptions` + `BackendStartupOptions` gain `gatewayPort`; `startBackendAndCreateWindow` (or a sibling `startManagedChildrenAndCreateWindow`) spawns both + dual readiness race + stop-both-on-failure; `registerAppLifecycle` builds `gatewayManager` and the ordered finalizer array |
| `desktop/src/main.test.ts` | dual-spawn, dual-readiness, failure-stops-both, ordering cases |
| `desktop/src/gateway/gatewayProcess.test.ts` (new) | launch-shape + entry-resolution cases |
| `desktop/src/backend/DesktopBackendManager.test.ts` | generic-manager case (second options shape) |
| `desktop/src/env.test.ts`, `api .../test_channel*.py` | gatewayPort parsing both sides |

No Python runtime-behavior changes (channel.py parse only). No canvas changes. No
`main.py`/proxy changes (gate stays off).

## 7. Test plan (what proves it)

1. **Ordering (the invariant):** `registerAppLifecycle`-level (or extracted
   composition) test with two fake children recording an event log; trigger
   `DesktopShutdown.requestQuit()`; assert log is
   `[gateway.SIGTERM, gateway.exit, python.SIGTERM, python.exit]` — the Python kill
   must not be issued until the gateway stop resolved. Second case: gateway stop
   rejects → Python stop still runs (DesktopShutdown log-and-continue), quit proceeds.
2. **Dual supervision:** both children spawn with the expected launch shapes
   (`buildGatewayLaunch` env asserts GATEWAY_PORT/CAPTURE_RPC_URL exactly;
   CAPTURE_RPC_URL == `http://127.0.0.1:{webPort}`); readiness gates on both health
   URLs; a gateway that exits pre-ready fails startup, stops the Python child too,
   and surfaces `showBackendStartupFailure`.
3. **Entry resolution:** env override wins; marker-walk finds
   `packages/gateway/src/main.ts` from a fake tree; missing entry → typed error
   (not a bad spawn).
4. **Ports:** channel-spec gatewayPort parsed (TS + Python); `ENV.GATEWAY_PORT` pin
   wins over spec; invalid pin throws (reuse `resolvePort`).
5. **Manual/dev verification (verify skill):** `pnpm --dir desktop dev` in a scratch
   workspace → assert two children in the process tree, gateway `/health` 200 on
   8789, quit → gateway exits before Python (log timestamps), no orphans.
6. Gates verbatim: `just check`, `just test` (desktop suite runs inside).

## 8. Risks / decisions for orchestrator + Stuart

- **D-b1 — readiness hard-gate on gateway health** (recommended, §5). Alternative:
  warn-only in 4e-b, hard-gate at 4e-d. Costs: hard-gate couples desktop startup to
  a working node+tsx toolchain on the dev machine; warn-only risks a silently absent
  gateway. My recommendation stands: hard-gate, loud failure dialog.
- **D-b2 — packaged-app node/entry resolution is deferred** (D1 pole). 4e-b ships
  the dev/local shape (`node --import tsx` + workspace sources). The
  `TRANSPORT_MATTERS_GATEWAY_ENTRY` override is the seam a packaged build will fill.
  ABI note recorded in §2c (ELECTRON_RUN_AS_NODE vs node-pty prebuilds).
- **Hosted/reattach mode spawns no gateway** (unchanged behavior). Post-4e-d this
  means a reattached CLI-spawned backend has no run path unless that Python spawns
  its own gateway or reattach is rethought — a 4e-d planning input, not a 4e-b task.
- **DATABASE_URL passthrough only:** gateway Activity stays disabled unless the
  operator env carries it; harmless now, needs a real answer when the canvas
  consumes Activity through the gateway.
- **Q8 regression risk:** any future "simplify to `pnpm --filter @tm/gateway start`"
  reintroduces the SIGTERM-swallowing wrapper; the ordering test (7.1) fails on the
  symptom (no graceful exit inside grace), and §2c documents why.
- **Parity risk — none to the run path:** both run paths stay live; the only shared
  surface touched is `waitForBackendHealth`'s signature (default-compatible).
