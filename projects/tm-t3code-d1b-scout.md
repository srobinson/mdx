---
title: Plan — t3code P1 Slice D1-b, packaged gateway launch wiring (web supervisor + desktop execPath)
type: projects
tags: [transport-matters, t3code, p1, slice-d1b, scout, plan, gateway, supervisor, packaging, node, lifespan]
summary: 'Build plan for D1-b on main @ 02eef07. KEY FINDING that reshapes the brief''s crux — the "web backend" is not a process the CLI can order children around; it is uvicorn EMBEDDED inside mitmdump (addon_runtime.start_web_runtime), and `transport-matters desktop` embeds uvicorn in the CLI process itself. So the gateway supervisor cannot live in the CLI supervisor; it belongs INSIDE the backend, split across the app seam: plan at create_app (resolve entry+node, pre-allocate a loopback port, decide proxy-vs-stub mount from the planned URL) and own the child in lifespan (spawn at startup, stop FIRST in the finally chain, before run-proxy close and capture-registry close — the in-process mirror of desktopShutdownFinalizers). Every backend host (web claude/codex, `transport-matters desktop`, dev uvicorn) gets the gateway from one seam with zero per-host duplication; Electron-owned backends skip it because TRANSPORT_MATTERS_GATEWAY_URL is already set. Opt-in via a new env-gated Settings flag so tests and bare create_app never spawn processes. Node absent → no plan → the existing D2 stub + doctor guidance (Stuart''s locked hybrid). Desktop half: buildGatewayLaunch grows an execPath/ELECTRON_RUN_AS_NODE option; CLI-spawned Electrons get TRANSPORT_MATTERS_GATEWAY_ENTRY pointed at site-packages. Grace-budget nesting (gateway 8s inside mitmdump''s 5s CLI grace) is the sharpest correctness risk and gets explicit bumps.'
status: active
source: scout (fable 5:2.3), first-hand on main @ 02eef07
confidence: high
created: 2026-07-08
---

# Plan — Slice D1-b: the packaged gateway actually launches

Scope per brief: Half 1 = web mode grows a gateway supervisor so canvas runs work
from a wheel install; Half 2 = packaged desktop handoff (execPath node +
GATEWAY_ENTRY into site-packages) + doctor. Stuart's locked D1-node hybrid:
desktop → Electron's node; web → system node with degrade-to-stub when absent.
All symbols read first-hand. Citations are file + symbol.

---

## 1. First-hand map — the finding that reshapes the crux

The brief frames Half 1 as "the supervisor must spawn the gateway ... BEFORE the
proxy mounts" and asks where the supervisor lives. The launch anatomy makes the
CLI the wrong home:

- **Web mode (`transport-matters claude` / `codex`)**: the CLI is a
  `ProcessSupervisor` (cli/runner.py) over two children — mitmdump and the
  client PTY. The FastAPI backend is **embedded inside mitmdump**:
  `addon_runtime.load_runtime` → `start_web_runtime` → `create_app()` +
  in-loop uvicorn. The capture registry (`app.state.capture_registry`) lives in
  that process. A CLI-owned gateway child would sit in a *different* process
  from the capture host, and `ProcessSupervisor.terminate_all` SIGTERMs all
  children **simultaneously with one shared grace** — no ordering primitive —
  so gateway-before-capture-host teardown (the 4e-b invariant) would need new
  supervisor machinery plus bind-retry re-spawn coordination
  (`run_client_with_retry` rebuilds the invocation per attempt, and
  `prepare_captured_run` has its own second retry loop).
- **`transport-matters desktop`**: backend is uvicorn **in the CLI process**
  (cli/desktop_cmd.py::serve_desktop_backend, a daemon thread); Electron is a
  detached **hosted viewer** (`DESKTOP_ROUTE_URL`) that spawns *no* children.
  Today this host serves the D2 stub — canvas panes in the CLI-launched
  desktop cannot spawn runs at all. Any CLI-side teardown after `server.run()`
  returns is already too late: the capture registry closes inside uvicorn's
  lifespan exit.
- **Electron-owned backend** (`_desktop-backend`, app-icon launch):
  backendProcess.ts::buildBackendLaunch sets `TRANSPORT_MATTERS_GATEWAY_URL`,
  Electron spawns and orders the gateway itself
  (main.ts::desktopShutdownFinalizers). Nothing to add here.
- **Dev harness** (scripts/local-desktop-dev-mode.sh, #243): stands up its own
  gateway and passes `GATEWAY_URL` explicitly. Must keep working unchanged.

All hosts converge on exactly two symbols: `main.py::create_app` (mount
decision) and `main.py::lifespan` (resource ordering — it already closes
`run_proxy_mount` before the capture registry). That is the seam.

## 2. Half 1 design — plan at create_app, own the child in lifespan

New module `api/src/transport_matters/gateway_supervisor.py` (root level: used
by main.py and cli/diagnose.py), split across the app seam:

### 2a. Integration point + ordering (the crux)

1. **Plan (sync, in `create_app`)**: when `settings.gateway_supervise` is true
   AND `settings.gateway_url` is unset, call
   `plan_gateway_supervision(settings) -> GatewayPlan | None`:
   resolve the entry (§2b), resolve node (§2c), pre-allocate a loopback port
   (§2d), build the child env (§2e). A `GatewayPlan` carries
   `url = http://127.0.0.1:{port}`, argv, env, cwd. `create_app` then mounts
   with `effective_gateway_url = settings.gateway_url or (plan.url if plan)`:
   plan exists → real `run_proxy` mount; no plan → the existing
   `runs_unavailable` stub, byte-for-byte the current D2/D-f1 semantics. Plan
   rides `app.state.gateway_plan`.
2. **Spawn (lifespan startup)**: if a plan is present, spawn the child
   (Popen, stdio piped to `logs/gateway.log`-style sink or inherited stderr),
   store a `GatewaySupervisedProcess` handle on `app.state`, and start a
   background watcher task: poll `GET {plan.url}/health`, log once on ready,
   log loudly (with recent output tail) if the child exits. **No hard boot
   gate**: blocking lifespan startup on gateway health would eat into the
   CLI's 5s web-ready window (`runner._wait_web_ui_ready_for_hook`) and turn a
   broken node install into a failed launch instead of a degraded one. During
   the sub-second boot window run routes answer 503 `gateway_unavailable`
   (`run_proxy.forward_http` already degrades per-request) — an
   already-handled product state, distinct from the stub's `runs_unavailable`.
3. **Teardown (lifespan finally, FIRST)**: stop the gateway — SIGTERM, wait up
   to `GATEWAY_STOP_GRACE_S = 8.0` (mirror of `DESKTOP_GATEWAY_STOP_GRACE_MS`,
   same coupling comment to the @tm/runtime budgets), SIGKILL fallback —
   **before** `run_proxy_mount.close()` and before
   `close_capture_registry(app)`. This is the in-process mirror of
   `desktopShutdownFinalizers` and satisfies the 4e-b lease-release invariant
   for every host with one ordered list, no CLI supervisor changes. Pin with a
   test the way the desktop pins finalizer order.

**Opt-in, not ambient**: new `Settings.gateway_supervise: bool = False` via
`TRANSPORT_MATTERS_GATEWAY_SUPERVISE` (env_keys addition). Writers:
`launch_environment.build_launch_env` sets it **only when
`web_runtime == "embedded"`** (pane-spawned runs are `external` and must never
spawn their own gateway), and `desktop_cmd._build_desktop_backend_env` sets it
for both desktop backend paths — the Electron-owned `_desktop-backend` child is
safe because `GATEWAY_URL` is set there and explicit gateway_url always wins
and disables supervision (preserves 4e-d and the dev harness). Tests and bare
`create_app()` never spawn anything (flag defaults off).

### 2b. Entry resolution — mirror `resolve_electron_launch` exactly

`resolve_gateway_entry(env) -> Path | None` with the same shape as
cli/desktop_viewer.py::resolve_electron_launch and
desktop gatewayProcess.ts::resolveGatewayEntry:

1. `TRANSPORT_MATTERS_GATEWAY_ENTRY` env override, stat-checked (typed error on
   a set-but-missing path — misconfiguration must be loud, matching
   `GatewayEntryNotFoundError` semantics);
2. packaged: `Path(__file__).parent / "gateway" / "main.js"` if it exists
   (D1-a artifact, verified present in the wheel `artifacts` glob);
3. workspace: walk parents to `pnpm-workspace.yaml`, join
   `packages/gateway/src/main.ts` (checkout dev);
4. none → return `None` → **degrade to stub** (web mode never hard-fails on a
   missing gateway; that is the product's D2 state), with one log line + doctor.

Packaged wins over workspace deliberately: deterministic for wheel installs,
and a checkout dev who wants live source sets the env override (soft decision,
§8). Spawn shape mirrors `buildGatewayLaunch`: `.ts` → `node --import tsx
<entry>`, else `node <entry>`, `cwd=entry.parent` (bare-specifier tsx
resolution), never a pnpm wrapper (Q8: it swallows SIGTERM).

### 2c. Node resolution (locked hybrid, web half)

`shutil.which("node")` — absent → no plan → stub + doctor line ("install
Node.js for canvas runs; runs degrade to 503 without it"). No crash anywhere.
`[node]` extra (A′) stays deferred to D1-c per the brief.

### 2d. Port — pre-allocate, accept the documented TOCTOU

The mount decision needs the URL before the child exists, so gateway-side
`port 0` + parse-the-listen-line is out (nothing to mount against). Extract a
single-port `allocate_loopback_port()` into root `loopback.py` (the existing
shared leaf) and refactor `cli/ports.py::allocate_port_pair` to delegate (DRY;
ports.py already documents accepting the allocate→bind TOCTOU window, and the
watcher task turns the rare loss into a loud log + doctor finding rather than
silence). Channel-spec `gatewayPort` stays desktop-only: web launches are
multi-instance with dynamic proxy/web ports, so a fixed 8789 would collide.

### 2e. Child env contract (verified against packages/gateway/src/main.ts)

- `TRANSPORT_MATTERS_GATEWAY_PORT` = allocated port;
- `TRANSPORT_MATTERS_CAPTURE_RPC_URL` = `loopback_http_url(settings.web_port)`
  (the embedded backend is the capture host);
- `TRANSPORT_MATTERS_DATABASE_URL` = `resolve_database_url(settings)` —
  resolved through settings.toml + channel database name, which is **better
  than the desktop today** (Electron only passes the var through when the
  operator's env happens to carry it; settings.toml-only setups get "Activity
  disabled"). Parity note for a future desktop touch, not this slice. On
  `MissingDatabaseConfigError` omit the var (launches preflight the store
  anyway, so this is dev-only).
- Add the three matching Python-side constants to `env_keys.py`
  (`GATEWAY_PORT`, `GATEWAY_ENTRY`, `CAPTURE_RPC_URL`, `GATEWAY_SUPERVISE`) —
  they exist today only in desktop/src/env.ts; the mirror comment demands both
  sides move together.

### 2f. Grace-budget nesting — the sharpest correctness risk

The gateway's 8s stop grace now nests INSIDE budgets that are all 5s today.
Unfixed, a Ctrl+C with live runs SIGKILLs the chain mid-lease-release — the
exact failure 4e-b exists to prevent:

- `addon_runtime.close_web_runtime` waits 5.0s for the uvicorn serve task;
  uvicorn's shutdown now includes lifespan-finally's ≤8s gateway stop → bump
  to 12s.
- `ProcessSupervisor.terminate_all(grace_seconds=5.0)`: mitmdump's graceful
  path now worst-cases ~12s → bump the default to 15s (§8 soft decision; the
  wait loop returns the moment children exit, so the bump only bites when a
  child genuinely hangs).
- `desktop_cmd.serve_desktop_backend` finally `thread.join(timeout=5.0)` →
  same bump.

Normal case is unaffected: with no live runs the gateway SIGTERM-exits in
milliseconds.

## 3. Half 2 — desktop packaged handoff

- **`buildGatewayLaunch` execPath option** (gatewayProcess.ts): new
  `GatewayLaunchOptions.nodeBinary?: string`; when set, `command = nodeBinary`
  and child env gains `ELECTRON_RUN_AS_NODE: "1"`. `registerAppLifecycle`'s
  `gatewayManager` launch wrapper passes `process.execPath` unconditionally —
  the desktop always has Electron's node, PATH independence is the point, and
  node-pty's N-API prebuilds make it ABI-safe (D1 scout §2b). Works for both
  the `.ts`+tsx dev entry and the packaged `.js`. Update the
  `GatewayStartupError` likely-causes copy ("Node.js not on PATH" no longer
  applies when launched by the desktop).
- **`GATEWAY_ENTRY` into site-packages**: shared
  `gateway_supervisor.packaged_gateway_entry() -> Path | None`; the CLI desktop
  launch env (the `spawn_detached_electron` env in cli/desktop_viewer.py, fed
  from run_desktop_launch/run_desktop_detached/_attach_existing_desktop) sets
  `TRANSPORT_MATTERS_GATEWAY_ENTRY` when the packaged bundle exists, so any
  Electron the CLI spawns resolves the wheel's gateway via the existing
  override branch (checked first — verified). Note the scope honestly: today
  those Electrons are hosted viewers that spawn no gateway (their canvas runs
  ride the CLI backend's Half-1 supervisor); the env makes the wheel entry win
  the moment any CLI-spawned Electron takes the spawn path, and a true
  electron-builder distributable stays D1-d territory.
- **Doctor** (cli/diagnose.py): `node` check (ok with version / warn with the
  degrade explanation), `gateway bundle` check mirroring the `web bundle`
  warn. Update the `report_runs_health` / `runs_health.RunsUnavailable` copy:
  "expected in web mode" is stale once web mode serves runs — a 503 there now
  means no node / no bundle / supervisor declined, and the hint should say so.

## 4. Leaked child (brief Q5) — stdin-EOF parent watch, in-slice

The host process self-reaps (s5a) and its graceful exit stops the gateway via
lifespan. The leak window is a SIGKILLed/crashed host — the same window s5a
closes for mitmdump. Node needs no prctl: spawn the gateway with piped stdin
and add ~15 env-gated lines to packages/gateway/src/main.ts
(`TRANSPORT_MATTERS_GATEWAY_PARENT_WATCH=1` → `process.stdin.resume()` +
`on("end"/"close") → shutdown()` reusing the installed graceful path). Kernel
closes the pipe on parent death including SIGKILL; cross-platform; the desktop
spawner (already `stdio: "pipe"`) can set the same flag and gets the fix free.
No mitmdump-style watchdog thread, no new dependency.

## 5. Touch list (~19 files)

API (Half 1): `gateway_supervisor.py` (new) + `test_gateway_supervisor.py`
(new); `main.py` (plan/mount + lifespan spawn/ordered stop); `config.py`
(Settings.gateway_supervise); `env_keys.py` (4 keys); `loopback.py`
(allocate_loopback_port) + `cli/ports.py` (delegate); `launch_environment.py`
(supervise flag, embedded only); `cli/desktop_cmd.py` (supervise flag; join
bump; GATEWAY_ENTRY into viewer env); `addon_runtime.py` (close_web_runtime
bump); `supervisor_core.py` (grace default); `cli/diagnose.py` +
`cli/runs_health.py` (checks + copy); tests: mount matrix + lifespan ordering
pin + env-writer assertions (extend test_config, test_cli_web_control_plane,
launch-env tests).

Desktop + gateway (Half 2/§4): `desktop/src/gateway/gatewayProcess.ts` +
tests (nodeBinary option, error copy); `desktop/src/main.ts` (pass
process.execPath; parent-watch flag); `packages/gateway/src/main.ts` + test
(stdin watch).

## 6. Test plan + gates

- Unit: entry-resolution matrix (override hit/miss, packaged, workspace,
  none), node-absent → no plan, mount decision (plan → proxy routes; no plan →
  stub 503 `runs_unavailable` + 1008 plain-terminal, unchanged assertions),
  lifespan ordering spy (gateway stop strictly before capture-registry close),
  child-env contract, supervise-flag writers (embedded yes / external no /
  GATEWAY_URL-set skips), buildGatewayLaunch nodeBinary, gateway stdin-watch.
- Gates: repo recipes verbatim — root `just check` + `just test` (api pytest,
  desktop vitest, packages vitest all ride them).
- Manual acceptance (the real proof, D1-a style): `just build` → `uv tool
  install` the wheel in a scratch env → `transport-matters claude` in a
  scratch dir → open canvas → spawn a run → verify it captures via the
  packaged gateway (wire artifacts + session rows) and that Ctrl+C releases
  leases with real end facts; `PATH` without node → launch succeeds, runs
  stub-degrade, `doctor` names the fix; `transport-matters desktop` → canvas
  pane spawn works (new capability); desktop execPath leg via `pnpm --filter
  transport-matters-desktop dev` on a workspace checkout; SIGKILL the mitmdump
  host → gateway self-exits (parent watch).

## 7. Blast radius / parity risks

- **Grace nesting** (§2f) — the one that corrupts data if missed; three named
  budget bumps, plus keep `close_web_runtime` > gateway grace invariant
  comment-coupled.
- **Stub semantics untouched**: mount-time branch in create_app is preserved;
  no run_proxy/runs_unavailable contract rewrite (rejected alternative: making
  gateway_url request-dynamic — cleaner in the abstract but rewrites the
  just-shipped s4f/4e-d surface for no product delta).
- **Dev harness / Electron-owned backends**: explicit `GATEWAY_URL` always
  wins and suppresses supervision — #243 and `_desktop-backend` behave
  identically before/after.
- **Multi-instance web launches**: per-instance ephemeral gateway ports; no
  shared 8789.
- **Windows**: supervisor is POSIX-signal shaped; gate spawn on `os.name ==
  "posix"` (stub otherwise) — D1-d owns the Windows leg.
- **TOCTOU port loss**: accepted per ports.py precedent; watcher + doctor make
  it diagnosable.

## 8. Stuart decisions (all soft — recommendations inline)

- **D1b-grace**: bump `terminate_all` default grace 5s → 15s (recommended;
  only bites when a child hangs) vs per-launch override plumbing.
- **D1b-gate**: no hard boot gate on gateway health in web mode (recommended;
  protects the 5s web-ready window; brief 503 window is already-handled
  product state) vs desktop-parity hard gate.
- **D1b-entry-precedence**: packaged bundle before workspace source for the
  Python resolver (recommended; env override is the dev escape hatch).
