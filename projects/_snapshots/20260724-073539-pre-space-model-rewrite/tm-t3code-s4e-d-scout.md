---
title: Plan — t3code P1 Slice 4e-d, hard cutover + delete the Python run path
type: projects
tags: [transport-matters, t3code, p1, slice-4e-d, scout, plan, cutover, deletion]
summary: Build plan for the destructive cutover. Desktop sets TRANSPORT_MATTERS_GATEWAY_URL on the Python child so create_app mounts the per-route proxy; the unset branch mounts an explicit 503 runtime_unavailable stub (D2). Deletion set proven dead by importer evidence — 6 Python source files + 11 test files — with three relocations (require_http_origin, DEFAULT_OWNER, send_run_error_and_close) and one shared test helper move. Lifecycle-fidelity premise CONFIRMED (Python writes RUN_STARTED/EXITED via the 4e-a capture RPC; gateway needs no DATABASE_URL for lifecycle). Two decisions for Stuart: reattach/hosted mode has no gateway (runs 503 on reattach), and run-continuation + external-web-runtime surfaces die with the route.
status: active
source: scout (fable 5:2.1), first-hand on main @ 84da72c (4e-a + 4e-b merged)
confidence: high (every importer claim grepped on main; nothing assumed from earlier scouts without re-verification)
created: 2026-07-08
---

# Plan — Slice 4e-d: hard cutover + deletion

Scope: gateway becomes the only owner of run lifecycle; Python's native run
handlers are deleted; web-mode (no gateway) run routes 503 per D2. Citations are
file + symbol, all re-verified on main @ 84da72c.

---

## 1. Gate wiring — who sets `gateway_url`, and the full topology (Q1)

**Today nothing sets it.** `main.py::create_app` forks on `settings.gateway_url`
(pydantic `SettingsConfigDict(env_prefix="TRANSPORT_MATTERS_")` → env
`TRANSPORT_MATTERS_GATEWAY_URL`, matching `env_keys.GATEWAY_URL`): set → mounts
`run_proxy.create_run_proxy_mount(...)` (the five per-route forwards + WS bridge,
proven since s1); unset → mounts `run_routes.router`.

**The cutover wire:** `desktop/src/backendProcess.ts::buildBackendLaunch` — the
one place the Python child's env is built. `BackendLaunchOptions` gains
`gatewayPort: number`; the env map adds
`[ENV.GATEWAY_URL]: \`http://127.0.0.1:${options.gatewayPort}\`` (new
`ENV.GATEWAY_URL` key in `desktop/src/env.ts`, mirroring `env_keys.GATEWAY_URL`).
`main.ts::startBackendAndCreateWindow` already carries `options.gatewayPort`
(4e-b) — it flows into `backendLaunchOptions`. Env-only: no new CLI flag on
`_desktop-backend` (Settings reads the env directly).

**Resulting topology (desktop):** canvas `POST /v1/runs` (same-origin, Python
front door) → `run_proxy.RunRouteProxy.forward_http`/`forward_terminal` →
gateway `runtimeRouter` → TS `RunManager.create` → Python
`POST /v1/capture/prepare` (worktree resolution + template validation +
RUN_STARTED emission, all 4e-a) → PTY spawn → … → release with end facts →
Python emits RUN_EXITED. **Premise CONFIRMED:** lifecycle rows are written by
Python's `CaptureLeaseRegistry` through the loop-pinned `SessionWriter`
(`run_lifecycle_emitter`); the gateway needs `TRANSPORT_MATTERS_DATABASE_URL`
only for Activity (warn-disabled without it), never for run lifecycle.

**Sequencing note:** create_app mounts the proxy from env at startup regardless
of gateway liveness. The 4e-b readiness gate means the window never opens before
both children are healthy, so the canvas cannot race a cold gateway. But a
gateway that dies later hits an unhardened seam:

**MUST-FIX (new, found in this scout):** `run_proxy.RunRouteProxy.forward_http`
does not wrap connect/timeout failures — a dead gateway turns every HTTP run
route into an unhandled `httpx.ConnectError` → FastAPI 500 + traceback. The WS
leg was hardened in s1 (m5: `1011 gateway_unavailable`); the HTTP leg needs the
mirror: catch `httpx.ConnectError`/`httpx.TimeoutException` (transport errors)
→ `503 {code: "gateway_unavailable"}`. Post-cutover this is the difference
between a diagnosable degraded state and a stack-trace storm.

---

## 2. Deletion set — importer evidence (Q2)

Every claim below is a fresh grep on main @ 84da72c, non-test importers unless
noted. **Relocations happen in the same commit as (or before) their deletion.**

### DELETE — Python source (6 files)

| File (key symbols) | Non-test importers found | Disposition |
| --- | --- | --- |
| `api/v1/run_routes.py` (the 5 handlers, `RunViewModel`, cursor/state helpers, `create_run_manager`, `close_run_manager`, `get_run_manager_from_app`, `_launch_fields`, `_spawn_request`, `_session_id_for_view`, `send_run_error_and_close`, `require_http_origin`, `DEFAULT_OWNER`) | `main.py` (mount + lifespan); `capture_rpc_routes.py` (`DEFAULT_OWNER`, `require_http_origin`); `space_routes.py` (`require_http_origin`) | DELETE after relocating: `require_http_origin` → new `api/v1/origin.py`; `DEFAULT_OWNER` → `api/v1/launch_resolution.py` (its importers already import that module); `send_run_error_and_close` → `api/v1/terminal_bridge.py` (the WS-helper home; the 503 stub needs it) |
| `run_manager.py` (Python `RunManager`, `RunState`, `SpawnRun`, `ManagedRun(View)`, `RunManagerError/Code`, `RunNotFoundError`, emit helpers) | `run_routes.py` (dying); `api/v1/run_storage.py` (only the `_live_run_storage` branch: `RunManager`, `RunNotFoundError`); `cli/runs_health.py` (DOCSTRING references only — no runtime import) | DELETE; `run_storage.py` drops `_live_run_storage` + the import (manifest/current-process chain covers gateway-owned runs — `prepare_captured_run` writes the manifest at prepare); `runs_health.py` docstrings reworded |
| `run_terminal.py` (Python `ScrollbackRing`/`TerminalFanout`) | `run_routes.py`, `run_manager.py`, `run_models.py` — all dying; TS parity shipped in 4b | DELETE |
| `run_models.py` | `run_manager.py` only | DELETE |
| `osc_color_responder.py` | `run_models.py`, `run_manager.py`, `run_routes.py` — all dying; byte-parity TS port live since 4e-a (`packages/runtime/src/domain/oscColorResponder.ts`) | DELETE (keep `test_osc_color_responder.py`? No — it tests the deleted module; the TS suite mirrors all its cases. DELETE) |
| `shared_proxy/run_preparation.py` (`prepare_shared_captured_run`) | `run_manager.py` only (the `WEB_RUNTIME_EXTERNAL` branch) | DELETE. **KEEP** `SharedProxyManager` + `api/v1/overrides.py` untouched (inspector overrides surface, reads `app.state.shared_proxy_manager`); the lifespan keeps starting it, but its `create_run_manager(shared_proxy_manager=…)` handoff dies. Flag: with no run producers, the shared proxy is vestigial — a cleanup slice candidate, not 4e-d scope |
| `api/v1/run_continuation.py` (`build_continuation_launch_fields`) | `run_routes.py` only; no `www/` caller (re-verified: zero `continueFromSessionId`/`idempotencyKey` hits outside api) | DELETE — this is the s4e-scout D3 disposition ("delete with the route; reintroduce on the RPC when a consumer exists"). **Needs Stuart's explicit ack** since it removes a designed-but-unconsumed API affordance (continuation + idempotency on run create) |

### KEEP — explicitly not deletable (unchanged from s4e scout, re-verified)

- `pty_session.py`, `api/v1/terminal.py`, `api/v1/terminal_bridge.py`: the plain
  canvas terminal pane (`WS /api/terminal`) and the proxy's origin/close helpers.
  4f candidate (s4e D4), untouched here.
- `supervisor*.py`: CLI launch path + mitmproxy supervision.
- `capture_rpc*.py`, `captured_run*.py`, `api/v1/launch_resolution.py`,
  `index/sessions.py`: the live capture plane.
- `api/v1/run_proxy.py`: becomes THE run path (plus the forward_http hardening).
- `api/v1/run_storage.py`: reduced (exchanges/meta still resolve via it).

### Tests (11 delete, 4 rewrite/reduce, 1 helper relocation)

- DELETE: `api/v1/test_run_routes{,_launch,_list_filters,_terminal,_support}.py`
  (5), `test_run_manager{,_lifecycle,_spaces,_shared_proxy,_spawn_control}.py`
  (5), `test_run_models.py` (1). `test_osc_color_responder.py` (mirrored in TS).
- RELOCATE first: `test_run_manager.py` exports shared fixtures consumed by
  SURVIVING suites — `resolved_worktree` is imported by
  `api/v1/test_capture_rpc_routes.py`, `api/v1/test_meta.py`,
  `space/test_models.py`; the fuller harness (`PreparedRunHarness`, `PtyHarness`,
  `make_manager`, `patch_pty_teardown`, `spawn_run`) by
  `test_cli_web_control_plane.py` and
  `api/v1/test_exchanges_live_run_storage.py`. Move `resolved_worktree` to a
  shared test-support home (`space/testing.py`, precedent: `session/testing.py`);
  the RunManager-shaped harness dies with its consumers below.
- REWRITE: `api/v1/test_exchanges_live_run_storage.py` (it proves the dying
  `_live_run_storage` branch) → replace with a manifest-path test: exchanges +
  meta resolve an RPC-prepared run with NO `app.state.run_manager`.
  `test_run_lifecycle_emission.py`: the canvas leg currently drives the Python
  RunManager; re-target it to `CaptureLeaseRegistry` (same DB assertion —
  RUN_STARTED/EXITED rows with CANVAS kind — through the surviving emitter).
  `test_cli_web_control_plane.py`: its
  `test_embedded_run_breakpoint_pause_release_uses_per_run_path_after_cutover`
  spawns an embedded run via the Python RunManager only to obtain a live
  per-run breakpoint path; re-fixture that run through the capture registry
  (identical prepare path) so the breakpoint plane stays proven for
  gateway-owned runs. `test_run_storage.py`: drop the live-branch cases.

---

## 3. Web-mode degradation — the explicit 503 seam (Q3, D2)

New `api/v1/runs_unavailable.py`: a five-route stub mounted by `create_app`'s
else-branch (never both):

- The four HTTP routes (`POST /runs`, `GET /runs`, `GET /runs/{id}`,
  `POST /runs/{id}/terminate`) → `raise_api_error(503, "runtime_unavailable",
  "run lifecycle requires the Transport Matters gateway; none is configured")`.
- `WS /runs/{id}/terminal` → accept, then `send_run_error_and_close(code=
  "runtime_unavailable", …)` (helper relocated to `terminal_bridge`), mirroring
  the existing run-WS error close shape so the canvas socket path fails cleanly.
- Exchanges/meta siblings are separate routers and stay served — the stub
  registers exactly the five patterns, same golden rule as the proxy.

This keeps `transport-matters claude` (web mode, no gateway) fully functional
for capture/inspection/history with a diagnosable 503 on run spawn, per D2.

**Doctor:** `cli/runs_health.py::fetch_runs` raises on non-success HTTP (only
connect/timeout return `None`) — post-cutover a web-mode doctor run would crash
on the 503. Teach `fetch_runs`/`report_runs_health` to treat
`503 runtime_unavailable` as "run lifecycle not served here" (report line, not
a crash); `reap_run` same. Docstring references to
`run_routes.RunViewModel`/`run_manager.RunState` reworded to the wire contract.

## 4. Reattach/hosted mode (Q4) — decision for Stuart

Hosted/reattach (`registerHostedDesktopLifecycle`, `liveRuntimeRouteUrl` hit, or
`ENV.DESKTOP_ROUTE_URL`) spawns NO children (4e-b §8), so a reattached backend
has no gateway: its run routes 503 (gate unset) — and in the stale case where a
recorded backend once had `gateway_url` set but its gateway died with the old
desktop, the proxy answers `gateway_unavailable` (503 after the §1 hardening).
**D-d1 (Stuart):** accept degraded runs on reattach for 4e-d (recommended —
viewing, sessions, exchanges, plain terminal pane all still work; a fresh
desktop launch restores runs), or scope reattach-spawns-gateway now (it drags
port reclaim + the runtime-status record into the slice). Recommendation:
accept + document in doctor output; revisit with the hosted-mode rethink.

## 5. Touch list (file + symbol) and test plan (Q5)

**Desktop (3):** `env.ts` (+`ENV.GATEWAY_URL`); `backendProcess.ts`
(`BackendLaunchOptions.gatewayPort`, `buildBackendLaunch` env);
`main.ts::startBackendAndCreateWindow` (thread `gatewayPort` into
`backendLaunchOptions`) + `main.test.ts`/`backendProcess.test.ts` cases
(env asserted, launch shape).

**Python (modify 7):** `main.py` (else-branch mounts the stub; lifespan drops
`run_routes.create_run_manager`/`close_run_manager` + the `run_manager` state;
SharedProxyManager start stays); `api/v1/run_proxy.py` (forward_http transport
errors → 503 `gateway_unavailable`); new `api/v1/origin.py`
(`require_http_origin`); `api/v1/launch_resolution.py` (+`DEFAULT_OWNER`);
`api/v1/terminal_bridge.py` (+`send_run_error_and_close`);
`api/v1/capture_rpc_routes.py` + `api/v1/space_routes.py` (import re-points);
`api/v1/run_storage.py` (drop `_live_run_storage`); `cli/runs_health.py`
(503 handling + docstrings); new `api/v1/runs_unavailable.py`; new
`space/testing.py` (relocated `resolved_worktree`).

**Python (delete 7 source + 12 test files):** per §2.

**Test plan:**
1. **Proxied end-to-end (the live path):** extend `test_run_proxy.py`'s
   acceptance to the real-gateway topology if feasible in CI (create → attach →
   bytes → terminate through proxy + capture RPC), else the existing
   stub-gateway origin contract + the 4e-a RPC suites remain the split proof;
   plus a new lifecycle-fidelity integration: RUN_STARTED/EXITED rows land for a
   proxied run (re-targeted `test_run_lifecycle_emission.py` canvas leg).
2. **Deleted path gone:** import-boundary suite passes with the files removed
   (any dangling import fails collection); `create_app` with `gateway_url` set
   registers exactly the five proxy routes; grep-level CI guard unnecessary —
   module deletion + green collection is the proof.
3. **Web-mode 503 (D2):** `gateway_url` unset → the four HTTP routes 503 with
   `runtime_unavailable`, WS terminal closes with the error frame, and
   exchanges/meta/sessions/spaces still 200 (golden-rule assertion).
4. **Dead-gateway hardening:** proxy forward_http against a closed port → 503
   `gateway_unavailable` (no traceback); WS already covered (s1 m6).
5. **Storage seam:** exchanges/meta resolve a registry-prepared run via manifest
   with no `app.state.run_manager` (rewritten live-storage test).
6. **Doctor:** runs-health against a 503 backend reports degraded, exit clean.
7. **Desktop:** buildBackendLaunch env carries `TRANSPORT_MATTERS_GATEWAY_URL`
   with the resolved gateway port.
8. Gates verbatim: `just check`, `just test`; plus `pnpm --filter @tm/shell test`
   discipline is covered by `just test` (frontend suites run inside it).

## 6. Blast radius / parity risks

- **External web runtime dies for canvas runs** (`settings.web_runtime =
  "external"`): the Python RunManager's shared-proxy branch was its only server;
  the capture registry already rejects external (`web_runtime_unsupported`,
  deliberate s4c/s4d scoping). Post-deletion that config serves capture for CLI
  flows but cannot spawn canvas runs. Known limitation to record in the PR —
  part of D-d2 below.
- **Continuation/idempotency API removal** (D-d2, with the external-runtime
  note): both are designed-but-unconsumed surfaces deleted with the route.
  Stuart ack requested; reintroduction path documented (prepare RPC fields).
- **Breakpoint plane for gateway-owned runs**: unchanged by construction (the
  per-run prepare path is identical between the old embedded branch and the
  registry), and the re-fixtured control-plane test keeps it proven.
- **Doctor and any external `/v1/runs` consumer** sees the gateway's wire
  shapes everywhere now (integer cursor, TS error envelope `{error, message}`);
  canvas parity was closed in 4e-a; runs_health reads `items` only — compatible.
- **Ordering**: no new ordering risk; the 4e-b shutdown invariant already
  assumed the gateway owns runs.

## 7. Decisions for Stuart

- **D-d1** — reattach/hosted mode ships with 503 runs (recommended) vs
  reattach-spawns-gateway in-slice (§4).
- **D-d2** — deletion of the unconsumed run-continuation + idempotency create
  surface, and the external-web-runtime canvas-run mode, with the route
  (recommended; both have documented reintroduction paths on the RPC seam).
