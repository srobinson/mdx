---
title: Scout — t3code P1 Slice 4e, route cutover + Python run-path deletion
type: projects
tags: [transport-matters, t3code, p1, slice-4e, scout, cutover, runtime, deletion]
summary: Build-ready scout for slice 4e. The proxy and WS bridge are real and proven (s1); the cutover is NOT a clean gate flip. Four landmines — gateway process ownership (nothing spawns it), pty_session.py cannot die (the plain /api/terminal canvas pane uses it), session lifecycle emission (RUN_STARTED/RUN_EXITED) lives in the dying Python RunManager, and the TS create route silently drops canvas create semantics (oscColorReplies, runtimeTemplate, bypassPermissions, worktree resolution/validation). Deletion list, worktree placement (prepare RPC), parity catalog, build + test plan, and the decisions Stuart must make.
status: active
source: scout (fable 5:2.1), reconciled against main @ 9553bdf
confidence: high (all facts read first-hand from the tree; citations file + symbol)
created: 2026-07-07
---

# Scout — Slice 4e: route cutover + delete the Python run path

Design of record: `tm-t3code-p1-spec.md` (§2b per-route table, §2c capture RPC, §4
teardown). Reconciled against `main @ 9553bdf` (slices 0–4d merged). Citations are
file + symbol, never line numbers.

**Verdict up front: 4e is not a clean gate flip.** The proxy, the WS bridge, and the
capture RPC are real and proven. But the spec's §7 deletion list is wrong in two places
against the live tree, the session store loses run lifecycle events unless emission is
re-homed, the TS create route silently drops four canvas create semantics, and nothing
anywhere spawns the gateway process. Each has a clean resolution mapped below; two need
a Stuart decision before build.

---

## 1. Actual-state map (what s1/s2/s4d already landed)

### 1a. The per-route proxy is real and proven, including the WS leg

`api/v1/run_proxy.py` (s1, PR #231) is a complete per-route reverse proxy:

- `create_run_proxy_mount(gateway_url, settings)` returns a `RunProxyMount` whose
  router registers **exactly the five route patterns** (never a `/v1/runs*` prefix), so
  the sibling `/{id}/exchanges` and `/{id}/meta` stay Python-served. Verified in the
  s1 review ("GOLDEN RULE" check): the `GET /runs/{run_id}` pattern is `$`-anchored and
  does not shadow the siblings.
- The WS proxy (`RunRouteProxy.forward_terminal` + `_bridge_websockets`) is a real
  upgrade + bidirectional byte pump: frame fidelity both directions (bytes/text),
  FIRST_COMPLETED + cancel/gather teardown, application close-code propagation
  (`_wire_close_code`, 1005/1006 coerced to 1000), connect-failure → clean 1011
  `gateway_unavailable` close, duplicate-header preservation (`_forward_headers` via
  `multi_items()`), decoded-body header fixup (`_DECODED_RESPONSE_HEADERS`).
- s1's acceptance (`test_run_proxy.py`) drove the full canvas origin contract across
  the split against a real gateway subprocess: create/list/get/terminate, terminal WS
  bytes + text, close-code propagation (`run_not_found` → 1008), and exchanges/meta
  still answering from Python. **The sharpest spec risk (§2b WS proxy) is retired.**
- Front-door origin trust is owned by the proxy: `RunRouteProxy.require_http_origin` /
  `forward_terminal`'s `terminal_bridge.origin_allowed` check, mirroring what
  `run_routes.require_http_origin` does today. The gateway itself binds `127.0.0.1`
  (`packages/gateway/src/main.ts::runGatewayProcess`) and does no origin gating —
  correct division; the front door stays the trust boundary.

### 1b. The gate: `settings.gateway_url`, an either/or mount at create_app time

`main.py::create_app`: if `settings.gateway_url` (env `TRANSPORT_MATTERS_GATEWAY_URL`,
`env_keys.GATEWAY_URL`) is set, the five proxy routes mount and
`app.state.run_proxy_mount` is registered for lifespan close; **else
`run_routes.router` mounts locally**. It is a mount-time fork, not a per-request flag.

Two things the gate does NOT yet do:

- `main.py::lifespan` still builds the Python `RunManager` unconditionally
  (`run_routes.create_run_manager(...)`) and starts the `SharedProxyManager`, even in
  proxy mode. In proxy mode that Python RunManager is an empty vestige (runs live in
  TS); it exists only because the lifespan is unconditional.
- Nothing sets `gateway_url` in any real launch path (see 1c).

### 1c. Nothing spawns the gateway — the biggest open wiring

- The gateway process is `packages/gateway/src/main.ts::runGatewayProcess` (`@tm/gateway`,
  the serving root that mounts `createRuntimeRouter` + Activity). It reads
  `TRANSPORT_MATTERS_GATEWAY_PORT` (default port 0 = ephemeral, prints
  "gateway listening at …"), `TRANSPORT_MATTERS_CAPTURE_RPC_URL` (unset → warns and
  falls back to `StubCaptureAdapter`, runs spawn **uncaptured**), and
  `TRANSPORT_MATTERS_DATABASE_URL` (unset → Activity disabled).
- The desktop does NOT spawn it. `desktop/src/backend/DesktopBackendManager.ts` +
  `backendProcess.ts::buildBackendLaunch` spawn `transport-matters _desktop-backend`
  — the **Python** backend (`cli/desktop_cmd.py::run_desktop_backend_server`). The s2
  scout resolved this explicitly: "managed child = Python at slice 2; the gateway is
  optional/unspawned until 4e." 4e is where that bill comes due.
- No dev recipe, shell composer config, or CLI path references the gateway either
  (justfile only runs its tests/typecheck). Today the proxied topology only exists
  when an operator hand-starts the gateway and hand-exports two env vars.

### 1d. What s4d landed (relevant to 4e)

- `RunManager.create` (TS) calls the **real** capture RPC first
  (`CaptureRpcClient` → Python `POST /v1/capture/prepare`,
  `api/v1/capture_rpc_routes.py::prepare_capture` →
  `capture_rpc.py::CaptureLeaseRegistry`), spawns the PTY from `spec.client`
  (argv/env/cwd), rolls back with idempotent `releaseCapture` on failure, and
  propagates upstream RPC status through `RunManagerError.upstreamStatus`
  (`runtimeRouter.ts::replyRunManagerError` prefers it) — so Python-side 409/503/404
  error codes already flow back to the canvas intact.
- `CaptureHealthMonitor` polls `capture_health`; capture death settles the run with
  `endReason: "capture-lost"` (`domain/runtimeRun.ts::RuntimeRunEndReason`).
- Teardown ordering (§4) is in: PTY exit → fanout drain → `releaseCapture`.

---

## 2. The precise cutover mechanism (recommendation)

The gate flip has three parts, and only one of them is the env var.

**(i) Spawn + wire the gateway in the desktop launch path.** Recommended shape,
consistent with spec §2a and the s2 seams: Electron owns a second managed child.
`desktop/src/main.ts` starts the gateway via a second `DesktopBackendManager`-shaped
spawn (a `GatewayProcessManager` or a second `start()` on a generalized manager),
sequenced:

1. Pick the Python web port as today (`backendProcess.ts` already fixes `--web-port`).
2. Spawn the gateway with `TRANSPORT_MATTERS_CAPTURE_RPC_URL=http://127.0.0.1:{webPort}`
   and either a pre-picked `TRANSPORT_MATTERS_GATEWAY_PORT` or parse the
   "gateway listening at" line (pre-picked port is simpler and matches how the Python
   ports are already handled).
3. Spawn Python `_desktop-backend` with `TRANSPORT_MATTERS_GATEWAY_URL=http://127.0.0.1:{gatewayPort}`
   in `buildBackendLaunch`'s env.
4. `DesktopShutdown` finalizer order: stop the gateway (which `RunManager.close()`s →
   PTYs die → `releaseCapture` calls drain into Python) **before** stopping Python
   (capture leases + session store must outlive the runtime per §4).

**(ii) Remove the Python fallback mount.** `create_app` stops mounting
`run_routes.router` when `gateway_url` is unset. Recommended semantics: mount the
proxy when configured; when NOT configured, mount a tiny 503 `runtime_unavailable`
stub for the five routes (or simply let them 404 — see Decision D2). Either way the
Python serving implementation is deleted, not gated: no parallel path survives, which
is the DRY requirement. The env var stops meaning "which implementation" and starts
meaning "where is the runtime".

**(iii) Web/dev mode.** `transport-matters claude` / dev uvicorn serve `/canvas` with
no Electron and today get working runs from the in-process Python path. Post-deletion
they need a gateway too. Nothing in P1 scope packages node+gateway into the Python
tool (node-pty native prebuilds make bundling into the wheel genuinely ugly). Honest
options are in Decision D1 — this is the one product-facing regression risk and it
needs Stuart's call before build.

---

## 3. Deletion list (with reachability proof) — and the keep list

Dependency facts below are from the fmm graph on main @ 9553bdf, non-test importers only.

### DELETE outright (unreachable once the five routes stop being Python-served)

| File / symbol | Proof of deadness | Caveat to re-home first |
| --- | --- | --- |
| `api/v1/run_routes.py` (whole file: the 5 handlers, `CreateRunRequest`, `RunViewModel`, `ListRunsResponse`, cursor/state helpers, `create_run_manager`/`close_run_manager`/`get_run_manager_from_app`, `_resolved_worktree`, `_launch_fields`) | Only non-test importers: `capture_rpc_routes.py` and `space_routes.py`, both importing **only `require_http_origin`**; plus `main.py` (mount + lifespan) | **Re-home `require_http_origin`** (a 4-line wrapper over `terminal_bridge.origin_allowed_for_request`) to a shared spot — `api/v1/origin.py` or `errors.py`. **Re-home worktree resolution + continuation/idempotency semantics** (§4 below) before deleting. |
| `run_manager.py` (`RunManager`, `ManagedRun`, `SpawnRun`, lifecycle emission, idempotency registry) | Non-test importers: `run_routes.py` (dying) and `api/v1/run_storage.py` (only for `RunManager`/`RunNotFoundError` in its `_live_run_storage` branch) | **Re-home run lifecycle emission** (landmine L3, §4). `run_storage.py` drops its `_live_run_storage` branch and the import (see keep list). |
| `run_terminal.py` (Python `ScrollbackRing`, `TerminalFanout`) | Importers: `run_routes.py`, `run_manager.py`, `run_models.py` — all dying. TS parity landed in 4b. | none |
| `run_models.py` | Sole non-test importer: `run_manager.py` | none |
| `osc_color_responder.py` | Importers: `run_manager.py`, `run_models.py` — both dying | **Behavior, not code, must survive**: parity gap P4 (§5). Port the pure responder to TS or Stuart explicitly drops the behavior. |
| `api/v1/run_continuation.py` | Sole importer: `run_routes.py`. No frontend caller exists (no `continueFromSessionId` / `idempotencyKey` anywhere under `www/`) | Decision D3: port continuation into the prepare RPC or delete the feature. If ported, this module's `build_continuation_launch_fields` moves rather than dies. |
| Python tests: `api/v1/test_run_routes*.py` (5 files), `test_run_manager*.py` (5 files), `test_run_lifecycle_emission.py`, `test_run_models.py`, `test_run_terminal*` colocated tests | test the deleted surface | Port any contract-level assertions worth keeping into the proxy/RPC acceptance tests. |

### KEEP — explicitly NOT deletable (the spec's §7 list is wrong on two of these)

| Surface | Why it stays |
| --- | --- |
| **`pty_session.py` — STAYS (spec conflict).** | Spec §7 says "delete `pty_session.py::spawn_pty_process`… replaced by `NodePtyAdapter`". False against the tree: `api/v1/terminal.py` (the **plain canvas terminal pane**, WS `/api/terminal`, mounted via `api/v1/router.py`) uses `spawn_pty_process`, `TerminalPty`, `prepare_terminal_child`, `set_winsize`, `terminate_terminal_pty`, `write_all`, … — most of the module. The canvas calls it from `terminalSocket.ts::terminalSocketUrl` (`TerminalPane.tsx`). Deleting pty_session kills a live product surface that is NOT one of the five moved routes. See Decision D4. |
| `api/v1/terminal.py` + `api/v1/terminal_bridge.py` | The plain pane above; `terminal_bridge` is additionally imported by `run_proxy.py` (origin checks + `close_websocket_if_connected`) and supplies the size constants. |
| `supervisor.py`, `supervisor_core.py`, `supervisor_pty.py`, `supervisor_pty_process.py`, `supervisor_models.py` | Spec §7 lists `supervisor_pty*.py` for deletion, but `ProcessSupervisor` is load-bearing for the **CLI launch path** (`cli/runner.py` — `transport-matters claude` in the user's terminal) and for **mitmproxy supervision** (`captured_run.py::prepare_captured_run`), both explicitly staying Python in P1. `supervisor_core` imports `supervisor_pty_process` imports `supervisor_pty` — the chain is alive through `supervisor.py`'s import surface. Do not touch in 4e. |
| `capture_rpc_routes.py`, `capture_rpc.py`, `captured_run.py`, `captured_run_models.py`, `shared_proxy/*` | The capture seam TS calls. Note: `SharedProxyManager` startup in `lifespan` stays (capture prepare consumes it via the registry), but the handoff into `run_routes.create_run_manager` goes away. |
| `api/v1/run_storage.py` (reduced) | `exchanges.py` + `meta.py` resolve run storage through `resolve_run_storage_or_404`. Its `_live_run_storage` branch (reads `app.state.run_manager`) dies; the `_current_process_run_storage` + `_manifest_run_storage` chain covers TS-owned runs because `prepare_captured_run` writes the run manifest at prepare time. **Needs a test** proving exchanges/meta resolve for an RPC-prepared run with no `app.state.run_manager`. |
| `run_lifecycle.py`, `session/writer.py`, `index/sessions.py::synth_session_id` | Session store plane. `run_lifecycle` has live importers (`captured_run.py`, `addon_runtime.py`, `session/writer.py`); emission gets re-homed onto the capture seam (§4). |
| `runtime_registry.py`, `runtime_templates.py` | `runtime_template_routes.py` (stays Python) also imports them. |
| `api/v1/space_routes.py`, `exchanges.py`, `meta.py`, sessions/stream/desktop_runtime routers | Untouched; only their `require_http_origin` import re-points. |

**`main.py` changes:** `lifespan` drops `run_routes.create_run_manager` /
`close_run_manager` and the `shared_proxy_manager` handoff into it (the manager itself
still starts, for capture prepare); `create_app` drops the `run_routes.router` branch
per §2(ii).

---

## 4. Worktree resolution placement + the three re-homings

### §2B worktree resolution → the Python prepare RPC (recommended; matches the s4d scout's recommendation)

Current truth: `SpaceStore.resolve_worktree` has exactly one caller,
`run_routes._resolved_worktree` (validates + 404 `worktree_not_found` / 409
`worktree_unavailable` / 503 `session_store_unavailable`, and produces the cwd).
The TS side (`RunManager.create`) already forwards `worktreeId` into
`prepareCapture`; `PrepareCaptureRequest` already carries `worktreeId` + `directory`;
but nothing resolves `worktreeId → cwd`, so a canvas create through the proxy today
runs in the Python process's cwd — the deferred gap.

Land it in `capture_rpc_routes.prepare_capture` (or a helper it calls): when
`directory` is absent and `worktreeId` present, resolve via `SpaceStore` (the route has
`request.app.state` → session pool), reusing the exact error codes from
`_resolved_worktree` (move that helper, don't rewrite it). Error propagation to the
canvas already works: `RunManagerError.upstreamStatus` passthrough (s4d) carries the
404/409/503 + code straight through TS create → proxy → canvas, which uses
detail-aware errors (`transport.ts::createCapturedRun`).

**Also extend the prepare response**: `capture_rpc.py::capture_spawn_spec_payload`
returns no resolved identity today. Add resolved `spaceId`/`worktreeId` so
`RunManager.register` stops stamping `DEFAULT_SPACE_ID = "stub-space"` /
`"stub-worktree"` into views the canvas persists (`RuntimeRunView.spaceId/worktreeId`
must carry real identity post-cutover — the canvas store and list filters key on them).

Do NOT put resolution in `run_proxy.py`: the proxy is deliberately dumb (headers +
bytes), and worktree semantics there would recreate a second lifecycle brain at the
front door.

### L3 — run lifecycle session events must re-home (silent data loss otherwise)

Python `RunManager._emit_run_started` / `_emit_run_exited` emit
`RUN_STARTED`/`RUN_EXITED` rows (`build_run_lifecycle_event`, `LaunchKind.CANVAS`,
space/worktree ids, exit reason/code/error) through
`SessionWriter.submit_run_lifecycle_event` (wired in `run_routes.create_run_manager`).
Delete `run_manager.py` without re-homing and canvas runs stop appearing in the
session store's run lifecycle history — a silent regression no route test catches.

Recommended re-homing: the capture seam. `CaptureLeaseRegistry.prepare_capture` emits
RUN_STARTED after the lease registers; `release_capture` emits RUN_EXITED. That
requires `release_capture` to learn the end facts TS knows: extend the release RPC
body with `endReason` (`explicit | natural-exit → "explicit"/exit mapping | capture-lost | shutdown`),
`exitCode`, `error` (all optional; absent on the self-release path). Alternative: a
TS-side emitter through a new RPC — worse (third call, and Python already owns the
writer). Alignment detail: today's Python emits started when the PTY actually spawns
(post-attach, `start_on_attach`); prepare-time emission is slightly earlier. The
TS create rollback (`releaseCapture` on PTY-spawn failure) closes the gap: a failed
spawn produces STARTED+EXITED(error) rather than a phantom RUNNING.

### `require_http_origin` re-home

Trivial but ordering-critical: move it out of `run_routes.py` (to `api/v1/origin.py`
or `errors.py`) and re-point `capture_rpc_routes.py` + `space_routes.py` before the
file is deleted.

---

## 5. Parity gap catalog (Python front door vs TS runtime, canvas-observable)

| # | Gap | Facts | Disposition |
| --- | --- | --- | --- |
| P1 | **Create body semantics silently dropped.** Canvas sends `oscColorReplies` (always), `runtimeTemplate?`, `bypassPermissions` (always) (`transport.ts::createCapturedRun`). `runtimeRouter.ts::CreateRunBody` accepts only `cwd/harness/spaceId/terminal/worktreeId` — the rest are ignored, so a template or bypass-permissions launch through the proxy silently launches native/non-bypass. | `PrepareCaptureRequest` already has `runtimeTemplate`, `bypassPermissions`, `launchFields` fields — the Python side is ready. | **Must-fix in 4e:** TS create body + `CreateManagedRunInput` + `prepareCapture` input grow `runtimeTemplate`/`bypassPermissions` (pure passthrough to the RPC; validation stays Python — `_runtime_template_ref`'s 400 moves behind the RPC). |
| P2 | **`idempotencyKey` + `continueFromSessionId`.** Python create dedupes via `RunManager._runs_by_idempotency_key` and builds continuation launch fields (`_launch_fields` → `run_continuation.py`). TS has neither. No `www/` caller exists today for either param. | Caller-less surface, designed-not-consumed. | Decision D3: port (idempotency dedupe belongs TS-side in `RunManager.create`; continuation resolution belongs in the prepare RPC) or delete explicitly. Deleting is defensible for 4e scope; do not half-port. |
| P3 | **`endReason: "capture-lost"`** exists in TS (`RuntimeRunEndReason`) but not in the canvas type (`transport.ts::RunEndReason`). | s4d deferred the canvas type touch to 4e by design. | **Must-fix in 4e:** add `"capture-lost"` to `RunEndReason` + whatever `capturedRunStore.ts` surfaces for end states. The only canvas-side code change strictly required. |
| P4 | **OSC color replies.** `osc_color_responder.py` (pure regex answerer for OSC 10/11 color queries) runs in the Python PTY bridge when `oscColorReplies` (default true). No counterpart under `packages/runtime/` — harnesses querying terminal colors get silence post-cutover. | Module is pure and small. | Port as a pure TS domain module wired into the PTY data path (honors P1's flag), or Stuart accepts the behavior drop. Recommend port — it is real terminal-faithfulness behavior the canvas flag advertises. |
| P5 | **Codex `sessionId` synthesis.** Python `_session_id_for_view`: codex views get `synth_session_id(run_id, "codex", native)`; TS `register` uses `nativeSessionId ?? runId`, and codex prepares with `defer_session_ownership` (no managedSession at prepare) → TS codex views show `runId` as sessionId forever. | Canvas correlates run ↔ transcript session via this id. | Fix in 4e (small): either the prepare response's `managedSession` grows the synthesized id server-side, or TS adopts the synth rule. Server-side is better — keeps synthesis single-sourced in Python (`index/sessions.py`). |
| P6 | **Spawn timing.** Python `SpawnRun.start_on_attach=True` defers harness spawn to first viewer attach (first paint at the right size); TS spawns at create with default 80×24 and resizes on attach. | Cosmetic-to-minor (prompt may render at wrong width before resize). | Note in the build brief; acceptable drift for 4e, do not silently regress further. |
| P7 | **List cursor + ordering.** Python: opaque cursor bound to its filters (`_cursor_filter_key`), state alias STARTING→RUNNING, 400 on bad state. TS: integer offset cursor, filters unbound, insertion order. Canvas `listRuns` never reads `nextCursor` and never paginates. | s1 review already normalized limits/validation (M1/L1/L2 fixed). | Accept TS semantics as the contract; no canvas impact. Document, don't build. |
| P8 | **Owner scoping** identical defaults (`DEFAULT_OWNER = DEFAULT_RUNTIME_OWNER = "local"`, query-param owner on both, WS owner fixed in s1 m2). | — | No action. |

---

## 6. File-by-file build plan

Ordered so every commit is green (`just check` + `just test`, verbatim, both from root;
Python suite via `cd api && just test` runs inside them).

**Step 1 — re-homings (Python, no behavior change yet)**
- `api/v1/origin.py` (new): `require_http_origin`; re-point `capture_rpc_routes.py`,
  `space_routes.py`; `run_routes.py` imports it too (transitional, dies in step 4).
- Move `_resolved_worktree` (+ its error codes) out of `run_routes.py` into the capture
  plane (e.g. `api/v1/worktree_resolution.py` or into `capture_rpc_routes.py`).

**Step 2 — capture seam grows the cutover duties (Python)**
- `capture_rpc_routes.prepare_capture`: resolve `worktreeId → directory` when directory
  absent (step-1 helper); wire session pool access.
- `capture_rpc.py`: `capture_spawn_spec_payload` returns resolved `spaceId`/`worktreeId`
  (+ P5 synthesized session id in `managedSession`); `CaptureLeaseRegistry` gains
  lifecycle emission (RUN_STARTED on prepare, RUN_EXITED on release) fed by a
  `SessionWriter` injected from `lifespan`; `release_capture` route + registry accept
  optional `endReason`/`exitCode`/`error`.
- Tests: prepare resolves/404s/409s worktrees; release emits EXITED; emission failures
  don't fail the RPC (mirror `_emit_lifecycle_event`'s swallow-and-count).

**Step 3 — TS runtime parity (packages/runtime, packages/gateway)**
- `runtimeRouter.ts` + `RunManager.ts` + `CaptureRpcClient.ts`: create body carries
  `runtimeTemplate`/`bypassPermissions` (+ `oscColorReplies`) through to prepare;
  release sends end facts; views adopt resolved identity from the prepare response
  (drop `DEFAULT_SPACE_ID`/`DEFAULT_WORKTREE_ID` stamps for resolved runs).
- P4: port `osc_color_responder` as a pure domain module in the PTY data path (or D-item).
- Tests: router create passthrough; view identity; capture-lost end facts on release.

**Step 4 — the cutover + deletion (Python, desktop, canvas)**
- `desktop/`: spawn the gateway as a second managed child (env wiring per §2(i));
  `DesktopShutdown` finalizer order gateway-before-Python; readiness + crash surface
  mirroring `watchBackendExitBeforeReady`.
- `main.py`: `create_app` — proxy mount when `gateway_url` set, 503/absent otherwise
  (per D2); `lifespan` — drop Python RunManager creation/close, keep SharedProxyManager
  + capture registry + SessionWriter injection.
- Delete: `api/v1/run_routes.py`, `run_manager.py`, `run_terminal.py`, `run_models.py`,
  `osc_color_responder.py` (post-port), `api/v1/run_continuation.py` (per D3), the 12+
  test files listed in §3; reduce `api/v1/run_storage.py` (drop `_live_run_storage` +
  `run_manager` import).
- `www/packages/core/src/transport.ts`: `RunEndReason` + `"capture-lost"` (P3);
  `capturedRunStore.ts` end-state surface if it enumerates reasons.

**Step 5 — acceptance**
- Extend `test_run_proxy.py` acceptance to the REAL gateway topology (not the echo
  stub): create → attach → bytes → terminate across proxy + RPC, exchanges/meta 200
  from Python for the same run (proves the `run_storage` manifest path), plain
  `/api/terminal` pane still serves (proves the pty_session keep), sessions/spaces
  routers unaffected.
- Frontend: full `pnpm --filter @tm/shell test` (structural change rule) + canvas type
  gates via `just check`.

---

## 7. Test plan (what proves the cutover)

1. **Origin contract, real topology** (extends s1's proven harness): all seven canvas
   calls (`createCapturedRun`, `listRuns`, `getRun`, `terminateRun`, terminal WS,
   `fetchExchange`, `fetchMeta`) against Python-front-door + real gateway + real RPC.
2. **Deletion safety**: exchanges/meta resolve an RPC-prepared run via manifest with no
   `app.state.run_manager`; `space_routes`/`capture_rpc_routes` import the re-homed
   origin guard; `/api/terminal` pane WS round-trips (pty_session alive); grep-level
   guard that nothing imports the deleted modules (the private-import boundary test
   plus fmm/CI import graph already fail on dangling imports).
3. **Lifecycle emission**: session store receives RUN_STARTED/RUN_EXITED for a
   TS-owned run incl. capture-lost end reason; emission failure does not break
   create/release.
4. **Create semantics passthrough**: runtimeTemplate/bypassPermissions/worktree
   resolution errors (404/409/503 + codes) observable from the canvas transport call.
5. **Desktop lifecycle**: gateway child spawn/teardown order under `DesktopShutdown`
   (unit-level, like `DesktopBackendManager.test.ts`); no orphaned gateway after quit.
6. **Unwired mode**: `gateway_url` unset → the five routes answer 503
   `runtime_unavailable` (per D2), exchanges/meta/sessions/spaces unaffected.

---

## 8. Decisions needed (orchestrator + Stuart) — before build starts

- **D1 — Web/dev mode run story (user-facing).** Post-deletion, `/canvas` served
  without the desktop has no run path unless a gateway runs. Options:
  (a) desktop-only runs in P1 — web `/canvas` degrades to 503 on spawn (viewing
  history, sessions, exchanges all still work); (b) Python spawns the gateway when
  node is on PATH (works for dev; packaging the built gateway JS + node-pty prebuilds
  into the wheel is real work and platform-fragile); (c) dev-only recipe (justfile
  target exporting the two env vars) + documented manual start.
  **Recommendation: (a)+(c)** for 4e — hard cutover, desktop fully wired, dev recipe
  for web work, wheel-packaging deferred deliberately (it is horizon-b Gateway work
  anyway). This is a product regression for web-mode run spawning; Stuart must own it.
- **D2 — Unwired-gate behavior.** 503 `runtime_unavailable` stub (recommended —
  diagnosable, doctor-friendly) vs bare 404s. Either is DRY-clean; pick one.
- **D3 — Continuation + idempotency surface (P2).** Caller-less today. Delete with the
  route (recommended for 4e; reintroduce on the RPC when a consumer exists) or port
  now (idempotency dedupe in TS RunManager + continuation fields in prepare RPC).
- **D4 — The plain terminal pane keeps `pty_session.py` alive (spec §7 conflict).**
  4e cannot deliver the spec's "delete pty_session.py" without also moving
  `/api/terminal` (a sixth route move, its own origin-contract change, not in the
  locked five). **Recommendation:** keep pane + pty_session in 4e, propose a small 4f
  ("plain terminal route on the runtime, delete pty_session/terminal_bridge PTY half")
  so the POSIX-only pane debt gets a named home instead of dying silently in spec
  fiction. Needs Stuart's ack because it amends the spec's deletion promise.
- **D5 — OSC responder (P4).** Port to TS (recommended) or accept behavior drop.

**Risk register for the slice:** the desktop two-child startup sequencing (readiness,
port races, teardown order) is the largest new correctness surface; session lifecycle
re-homing is the silent-regression risk (test #3 is the guard); everything else is
mechanical deletion behind an already-proven proxy.
