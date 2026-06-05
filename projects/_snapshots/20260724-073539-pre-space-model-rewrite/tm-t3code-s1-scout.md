---
title: Scout findings — t3code P1 slice 1 (B-S1) Runtime skeleton + full canvas origin contract
type: projects
tags: [transport-matters, t3code, p1, slice-1, runtime, gateway, ws-proxy, scout]
summary: Build-ready recon for B-S1. Scaffold @tm/runtime as a context package, mount its stub run-lifecycle + terminal-WS router into the already-built @tm/gateway via the barrel factory, and reverse-proxy exactly five run routes from Python create_app to the Gateway per-route (never the /v1/runs* prefix). Feasible. The one hard risk — WS reverse-proxy of /v1/runs/{id}/terminal through the Starlette front door — is fully supported by deps already in the api venv (websockets 16.0 + wsproto via uvicorn[standard]); httpx>=0.28 covers the four HTTP forwards.
status: active
verdict: FEASIBLE
created: 2026-07-06
---

# Scout findings — B-S1 (Runtime skeleton + full canvas origin contract incl. WS terminal proxy)

**Verdict: FEASIBLE.** No blockers. All the wire deps exist. The single sharpest
risk (WS reverse-proxy through Python) is served by libraries already installed in
the `api/` venv. One design decision needs Stuart's call (proxy cutover vs env-gated
fallback — see §6 Open risks R1).

**One structural drift the builder must absorb up front:** the spec (§0/§1) still
talks about a *standalone Runtime server* that Python proxies to. Reality after PR
#200/slice-0: **`@tm/gateway` already exists as the Node composition-root process**
(`packages/gateway/src/main.ts`, `start` script, `buildGateway()`), and the B-S1
brief supersedes the spec: `@tm/runtime` is a **context package (router only)**, and
its router is **mounted into the Gateway** via the barrel factory exactly like
`@tm/activity`. Python reverse-proxies the five run routes **to the Gateway process**.
There is no separate standalone Runtime server in slice 1.

---

## 1. Verified entry points table (claimed → actual)

| Spec/brief claim | Actual (file + symbol) | Correction |
| --- | --- | --- |
| `packages/activity/`, `packages/common/`, `packages/gateway/` | Confirmed at **repo-root `packages/*`** (NOT `www/packages/*`) | Brief was right; note `www/packages/*` is the browser tier |
| `packages/runtime` should not exist | Confirmed absent | ✅ clean scaffold |
| activity barrel exposes router factory | `packages/activity/src/index.ts` exports `createActivityRouter` + `type ActivityRouterDeps` from `./server/activityRouter` | ✅ |
| activity router template | `packages/activity/src/server/activityRouter.ts::createActivityRouter(deps): FastifyPluginAsync` | ✅ exact |
| gateway mounts via barrel factory | `packages/gateway/src/app.ts::buildGateway` + `ContextMount {prefix, router}` + `gatewayContexts()` | ✅ exact; barrel `packages/gateway/src/index.ts` exports `buildGateway`, `ContextMount`, `GatewayOptions`, `ACTIVITY_CONTEXT_PREFIX` |
| mount contract proven with inject | `packages/gateway/src/app.test.ts` — `createFixtureContextRouter` + `app.inject()` + `fastifyApps` tracker (`testSupport/fastifyApps.ts`) | ✅ this is the slice-1 test template |
| five run routes | `api/src/transport_matters/api/v1/run_routes.py`: `create_run` `@router.post("/runs")`, `list_runs` `@router.get("/runs")`, `get_run` `@router.get("/runs/{run_id}")`, `terminate_run` `@router.post("/runs/{run_id}/terminate")`, `run_terminal_socket` `@router.websocket("/runs/{run_id}/terminal")`. Mounted `app.include_router(run_routes.router, prefix="/v1")` | ✅ terminate is **POST** not DELETE; `RUNS_ROUTE_PREFIX="/runs"` |
| exchanges stay Python | `api/.../v1/exchanges.py`: `RUN_EXCHANGES_ROUTE_PREFIX="/runs/{run_id}/exchanges"`, `run_router` routes `""`, `EXCHANGE_DETAIL_ROUTE_PATH="/{exchange_id}"`, `/{exchange_id}/turn-content`, `/{exchange_id}/pipeline_tokens`. Mounted `prefix="/v1"+RUN_EXCHANGES_ROUTE_PREFIX` | ✅ four sibling paths under `/v1/runs/{id}/exchanges` |
| meta stays Python | `api/.../v1/meta.py`: `get_run_meta` `@run_router.get("")`, mounted `prefix="/v1/runs/{run_id}/meta"` → full path `/v1/runs/{id}/meta` | ✅ |
| where proxy is wired | `api/src/transport_matters/main.py::create_app` — the `app.include_router(run_routes.router, prefix="/v1", ...)` line is the cutover point | ✅ |
| transport client symbols | `www/packages/core/src/transport.ts` (NOT `packages/core`): `createCapturedRun`→`POST /v1/runs`, `listRuns`→`GET /v1/runs`, `getRun`→`GET /v1/runs/{id}`, `terminateRun`→`POST /v1/runs/{id}/terminate`, `fetchExchange`→`GET /v1/runs/{id}/exchanges/{id}`, `fetchMeta`→`/v1/runs/{id}/meta` or `/api/meta` | ✅ all present, all **relative-path same-origin** |
| terminal socket URL builder | `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts::runTerminalSocketUrl(runId,cols,rows,location)` builds `ws(s)://{location.host}/v1/runs/{id}/terminal?cols&rows` | ✅ exact; also `terminalSocketUrl` (the bare `/api/terminal`, unrelated) |
| importGraphBoundary auto-iterates packages/* | `www/packages/shell/src/testSupport/importGraphBoundary.test.ts` — see §4; **partly** auto, partly hardcoded | ⚠️ needs a RUNTIME case added (details §4) |

---

## 2. The mount-factory contract (exact signature + copy-paste template)

A context exposes **one factory from its barrel**:
`create<Context>Router(deps): FastifyPluginAsync`. The Gateway registers the returned
plugin under a prefix; contexts type structurally against `fastify` and never import
the Gateway. This is the whole contract (`packages/AGENTS.md`, "The mount contract").

Activity's shape to mirror (`packages/activity/src/server/activityRouter.ts`):

```ts
import type { FastifyPluginAsync } from "fastify";

export interface ActivityRouterDeps { /* injected reader/subscriptions */ }

export function createActivityRouter(deps: ActivityRouterDeps): FastifyPluginAsync {
  return async (app) => {
    app.get<{ Params: ...; Querystring: ... }>("/workspaces/:workspaceId(.+)/activity", handler);
    // ...
  };
}
```

Gateway mount (`packages/gateway/src/app.ts`):

```ts
export interface ContextMount { prefix: string; router: FastifyPluginAsync; }
export interface GatewayOptions {
  activity?: ActivityRouterDeps;
  contexts?: readonly ContextMount[];
}
export async function buildGateway(options: GatewayOptions = {}): Promise<FastifyInstance> {
  const app = fastify();
  app.get("/health", async () => ({ status: "ok" }));
  for (const { prefix, router } of gatewayContexts(options)) app.register(router, { prefix });
  await app.ready();
  return app;
}
```

**Slice-1 runtime mount:** add `runtime?: RuntimeRouterDeps` to `GatewayOptions` and a
`gatewayContexts()` branch mounting `createRuntimeRouter(options.runtime)` under
`"/v1"` (define/reuse a `RUNTIME_CONTEXT_PREFIX = "/v1"`). Activity (`/v1/workspaces/…`)
and Runtime (`/v1/runs…`) share the `/v1` prefix with **no route collision** — Fastify
permits two plugins under one prefix as long as paths differ.

**Test template:** `packages/gateway/src/app.test.ts` — `fastifyApps.track(await buildGateway(...))`
then `app.inject({ method, url })`; `fastifyApps` from `testSupport/fastifyApps.ts` closes
apps in `afterEach`. Copy this for the runtime router's own `packages/runtime/src/server/runtimeRouter.test.ts`.

### WebSocket on the Gateway — the new capability

`buildGateway` currently uses a bare `fastify()` with only HTTP routes.
`WS /v1/runs/{id}/terminal` needs **`@fastify/websocket`** (NOT currently a dependency
anywhere — see §6 R2). It is registered inside a plugin scope; because the runtime
router is itself a `FastifyPluginAsync` mounted under a prefix, it can
`await app.register(fastifyWebsocket)` at the top of its own plugin body and then
declare `app.get("/runs/:id/terminal", { websocket: true }, handler)`. That keeps the
WS dependency encapsulated in `@tm/runtime` and off the Gateway's HTTP-only surface.
Pin `@fastify/websocket` **v11** (the Fastify 5 line; catalog fastify is `^5.9.0`).

---

## 3. The per-route proxy plan (4 HTTP + 1 WS)

**Golden rule (the review's blocker):** proxy **five explicit route patterns**, never
the `/v1/runs*` prefix. A prefix rule steals the siblings that MUST stay Python:
`/v1/runs/{id}/exchanges[...]` (4 routes) and `/v1/runs/{id}/meta`.

Route ownership after slice 1:

| Route | Method | Owner | Client caller |
| --- | --- | --- | --- |
| `/v1/runs` | POST | **Gateway (proxy)** | `createCapturedRun` |
| `/v1/runs` | GET | **Gateway (proxy)** | `listRuns` |
| `/v1/runs/{id}` | GET | **Gateway (proxy)** | `getRun` |
| `/v1/runs/{id}/terminate` | POST | **Gateway (proxy)** | `terminateRun` |
| `/v1/runs/{id}/terminal` | WS | **Gateway (proxy)** | `runTerminalSocketUrl` |
| `/v1/runs/{id}/exchanges`, `/{eid}`, `/{eid}/turn-content`, `/{eid}/pipeline_tokens` | GET | **Python (local)** | `fetchExchange`, `fetchTurnContent`, `fetchPipelineTokens` |
| `/v1/runs/{id}/meta` | GET | **Python (local)** | `fetchMeta(runId)` |
| `/api/meta`, `/v1/sessions`, `/v1/spaces`, `/v1/runtime-templates`, bundles | * | **Python (local)** | unchanged |

**Path-matching feasibility (confirmed no collision):** FastAPI/Starlette matches by
path segments. `GET /v1/runs/{run_id}` and `GET /v1/runs/{run_id}/meta` differ in
segment depth; `.../{run_id}/terminate` vs `.../{run_id}/exchanges` differ in the last
segment literal. Registering the five proxy routes as *explicit path templates* (not a
catch-all) leaves the exchanges/meta routers untouched. Register order does not matter
because none of the five is a prefix of a stay-Python route.

### 3a. The four HTTP forwards — `httpx` (already a dep, `httpx>=0.28`)

Add a small `api/src/transport_matters/api/v1/run_proxy.py` (or into `create_app`) with
five explicit FastAPI routes whose handlers forward to the Gateway origin
(`http://127.0.0.1:{gateway_port}`). Use a shared `httpx.AsyncClient`:
- Forward method, path, query string, request body, and the relevant request headers
  (strip hop-by-hop: `connection`, `keep-alive`, `transfer-encoding`, `upgrade`, `host`).
- Copy back status, body, and response headers (strip hop-by-hop). `POST /v1/runs`
  returns 201 with a body — preserve the status code, don't hardcode 200.
- Preserve the `?owner=`, `?state=`/`?spaceId=`/`?worktreeId=`/`?cursor=`/`?limit=`
  query params (they carry the owner-scoping and pagination; `listRuns`/`createRun`
  depend on them).

Gotcha: the existing `require_http_origin` / `TrustedHostMiddleware` guards run on the
Python front door and already pass for same-origin canvas calls; the Gateway sits on
loopback behind Python, so the origin check stays authoritative at the Python edge. The
proxy must forward, not re-derive, the client's identity params (`owner`).

### 3b. The WS forward — `websockets` (already installed via `uvicorn[standard]`)

**THE risk, and it is served.** The `api/` venv already contains `websockets` 16.0 and
`wsproto` 1.2.0 (pulled by `fastapi[standard]` → `uvicorn[standard]`), plus `starlette`
1.0.0. So **no new dependency** is needed for the WS proxy.

Mechanism (recommended): a Starlette/FastAPI `@app.websocket("/v1/runs/{run_id}/terminal")`
endpoint on the Python front door that:
1. `await ws.accept()` on the downstream (browser) socket — keeping the existing origin
   check (`terminal_bridge.origin_allowed`) is optional in slice 1 but preserves parity.
2. Opens an upstream client socket to the Gateway with
   `websockets.connect(f"ws://127.0.0.1:{gateway_port}/v1/runs/{run_id}/terminal?cols=..&rows=..")`,
   forwarding the query string (`cols`/`rows`).
3. Runs a **bidirectional pump** with two tasks: downstream→upstream and
   upstream→downstream, forwarding **binary frames as bytes and text frames as text**
   (the protocol is binary PTY I/O + JSON text control frames — see `terminalSocket.ts`
   and `run_routes.py::bridge_attached_run_terminal`). `asyncio.wait(..., FIRST_COMPLETED)`
   then cancel the other, mirroring the existing bridge pattern in `run_routes.py`.
4. Propagate close: when either side closes, close the other with the same close code
   where possible (the terminal uses `SLOW_VIEWER_CLOSE_CODE` and `WS_1008` policy codes;
   pass them through).

**Gotchas to hand the builder:**
- **Frame type fidelity.** Starlette `receive()` yields either `text` or `bytes`; the
  `websockets` client `send()`/`recv()` distinguishes str vs bytes. Preserve the type
  per frame — do not coerce binary PTY output to text (it will corrupt xterm output).
- **Backpressure.** PTY output can burst. The pump should `await send` per frame (no
  unbounded queue); the existing Python bridge already relies on natural await-based
  backpressure, and the Gateway/runtime side owns the slow-viewer close.
- **Subprotocols/headers.** No subprotocol is negotiated today (`new WebSocket(target)`
  with no protocol arg). No auth header on the WS. So the upstream `connect` needs no
  extra headers beyond the query string.
- **Close-code range.** Application close codes (e.g. 1008) forward cleanly; 1006
  (abnormal) is synthesized by the browser and never sent on the wire — don't try to
  forward it.
- **No existing reverse-proxy helper in the repo** to reuse (`shared_proxy/` is the
  mitmproxy capture manager, unrelated). This is net-new but small (~1 endpoint + pump).

---

## 4. importGraphBoundary + justfile + CI changes to gate @tm/runtime

### 4a. `importGraphBoundary.test.ts` (`www/packages/shell/src/testSupport/`)

Two mechanisms coexist; the builder must touch **both**:
- **Auto-iterated** (`rootPackageExports()` via `readdirSync(ROOT_PACKAGES)`): the
  single-barrel check already covers any new `packages/*` dir — `packages/runtime`
  auto-enrolls and will **fail** unless its `package.json` declares
  `"exports": { ".": "./src/index.ts" }`. The vacuous-guard
  `arrayContaining(["activity","common","gateway"])` still passes (it's a subset check);
  optionally add `"runtime"` to make the guard assert it.
- **Hardcoded per-package** (needs a new RUNTIME case, mirror GATEWAY): add
  `RUNTIME_SRC` + `RUNTIME_ENTRYPOINT` consts; a
  `packageInternalViolations(RUNTIME_SRC, RUNTIME_ENTRYPOINT)` test ("zero external
  imports into runtime internals"); add `@tm/runtime` to the "resolves the entrypoints"
  list and `@tm/runtime/app` / `@tm/runtime/src/...` to the "fails closed for deep
  imports" list.

### 4b. Root `justfile`

- `check:` add `pnpm --filter @tm/runtime typecheck` (alongside the common/activity/gateway lines).
- `test:` add `pnpm --filter @tm/runtime test` (alongside `pnpm --filter @tm/gateway test`).
- `pnpm lint:product-plane` already globs the whole `packages/` dir via biome
  (`package.json`: `biome check ... ../../../packages`) — auto-covers runtime, no change.

### 4c. `.github/workflows/ci.yml` (the `product-plane` job)

The job enumerates packages **explicitly** (not globbed):
- typecheck step (~L183): add `pnpm --filter @tm/runtime typecheck`.
- test step (~L195): add `pnpm --filter @tm/runtime test`.
(The lint step is `pnpm lint:product-plane`, already dir-globbed — no change.)

### 4d. `pnpm-workspace.yaml`

`packages/*` glob already includes `packages/runtime` — no workspace change. Add
`@fastify/websocket: ^11.x` to the `catalog:` block (sibling of `fastify: ^5.9.0`) and
reference it as `catalog:` in the runtime `package.json`.

### 4e. `@tm/runtime` package scaffolding (mirror activity/gateway)

`packages/runtime/package.json`:
```json
{
  "name": "@tm/runtime", "private": true, "version": "0.1.0", "type": "module",
  "exports": { ".": "./src/index.ts" },
  "scripts": { "test": "vitest run", "typecheck": "tsc -p tsconfig.json --noEmit" },
  "dependencies": { "@tm/common": "workspace:*", "fastify": "catalog:", "@fastify/websocket": "catalog:" },
  "devDependencies": { "@types/node": "catalog:", "vitest": "catalog:" }
}
```
`packages/runtime/tsconfig.json`: copy `packages/gateway/tsconfig.json` verbatim
(extends `tsconfig.base.json` + `tsconfig.bundler.json`, `lib:["ES2023"]`, `types:["node"]`,
`include:["src"]`). Gateway's `package.json` gains `"@tm/runtime": "workspace:*"`.

Canonical context shape (per `packages/AGENTS.md` / `docs/ARCHITECTURE.md`): single
barrel `src/index.ts`; `src/server/runtimeRouter.ts` (the factory). Slice 1 is stub, so
`domain/`/`service/`/`ports.ts`/`adapters/`/`events.ts` can be minimal or deferred to
later slices — do NOT over-scaffold empty dirs beyond what the router needs.

---

## 5. Canvas origin contract — how each call resolves to the right owner

**The single load-bearing fact:** production canvas/desktop uses **relative same-origin
paths**. The default `apiTransport` (`transport.ts::createApiTransport()` with no
`baseUrl`) returns the path unchanged; `setApiTransport` is called **only in tests**
(verified: zero non-test callers across `www/`). The terminal WS URL is built from
`location.host` (`runTerminalSocketUrl`). So **Python is the one origin in both modes**:
- **Desktop (loopback):** Electron loads `http://127.0.0.1:{webPort}/canvas`
  (`desktop/src/main.ts::rendererUrlForPort`, confirmed `.../canvas`). `location.host` =
  the Python backend's loopback port. All relative `/v1/...` + the WS resolve to Python.
- **Web (`/canvas`):** Python serves the canvas bundle at `/canvas`
  (`main.py::mount_frontend_bundles`). Same origin; same relative resolution.

Per-call resolution across the split (client is oblivious; Python routes it):

| Call (transport.ts / terminalSocket.ts) | URL | Resolves to |
| --- | --- | --- |
| `createCapturedRun` | `POST /v1/runs` | Python front door → **proxy → Gateway** |
| `listRuns` | `GET /v1/runs?…` | Python → **proxy → Gateway** |
| `getRun` | `GET /v1/runs/{id}` | Python → **proxy → Gateway** |
| `terminateRun` | `POST /v1/runs/{id}/terminate` | Python → **proxy → Gateway** |
| terminal WS | `ws(s)://host/v1/runs/{id}/terminal` | Python → **WS proxy → Gateway** |
| `fetchExchange`/`fetchTurnContent`/`fetchPipelineTokens` | `GET /v1/runs/{id}/exchanges/…` | **Python local** (unchanged) |
| `fetchMeta(runId)` | `GET /v1/runs/{id}/meta` | **Python local** (unchanged) |
| `fetchMeta()` | `GET /api/meta` | **Python local** (unchanged) |

**Owner scoping** rides the `?owner=` query param (default `local`) on the run routes;
the proxy must forward it verbatim so the Gateway stub keys its stub list/get by owner
the same way. No cookie/session auth is involved.

**Acceptance (slice 1):** a test that drives all eight rows across the split — run
routes reaching a Gateway stub, exchanges/meta staying Python — **including the WS
proxy**. Suggested harness: boot `buildGateway({runtime})` on `app.listen({host:"127.0.0.1",port:0})`,
point Python's proxy target at that address, drive Python via `httpx.AsyncClient` /
`starlette.testclient.TestClient` (which supports `.websocket_connect` for the WS leg).

---

## 6. Open risks / anything that could block the builder

**R1 (design decision — needs Stuart, does NOT block scaffolding).** The brief says
"wire `create_app` to reverse-proxy the five routes." Taken literally that **replaces
working Python run-serving with a Gateway stub**, so captured runs are non-functional
from slice 1 until slice 4c reintroduces real PTY. Two shapes:
  (a) **Hard cutover** — remove `app.include_router(run_routes.router,...)`, register the
      five proxy routes. Cleanest DRY (no parallel impl), but a real feature regression
      on whatever branch this lands until slice 4. Acceptable only if all of P1 merges as
      one unit (long-lived branch), not slice-by-slice to main.
  (b) **Env-gated proxy** — proxy to the Gateway when a `TRANSPORT_MATTERS_GATEWAY_URL`
      (or port) is configured, else keep serving `run_routes.router` locally. Preserves
      production through the P1 build; the local path is deleted at slice 4e (spec §7
      already schedules that deletion). Mild transitional duplication, explicitly staged.
  **Recommendation: (b)** — it satisfies "wire the proxy," proves the full contract via
  the slice-1 test with the env set, and avoids a multi-slice product regression. Flag to
  Stuart before the builder commits to (a).

**R2 (dependency add).** `@fastify/websocket` is **not present anywhere** (grep-verified
across all `package.json` + `pnpm-workspace.yaml`). Add to the catalog (`^11` for the
Fastify 5 line) and to the runtime package. `node-pty` correctly **not** needed this slice.

**R3 (WS proxy correctness).** Frame-type fidelity (bytes vs text per frame) and
close-code propagation are the two ways a naive pump corrupts the terminal. Deps are all
present (`websockets` 16.0, `wsproto`); the pattern mirrors the existing
`run_routes.py::bridge_attached_run_terminal` two-task `asyncio.wait` loop. Not a blocker,
but the highest-attention code in the slice — cover it with the origin-contract WS test.

**R4 (shared `/v1` prefix).** Activity and Runtime both mount under `/v1`. Verified no
route collision (`/v1/workspaces/*` vs `/v1/runs/*`). If the builder instead gives Runtime
its own prefix, the canvas relative paths (`/v1/runs`) would break — Runtime MUST mount at
`/v1`.

**R5 (Gateway HTTP-only today).** `buildGateway` has never served a WS route. Registering
`@fastify/websocket` inside the runtime plugin scope is the encapsulated fix; verify the
port-ful `app.listen` test path (not just `inject`) actually upgrades — `fastify.inject`
does NOT exercise WS, so the WS leg needs a real-socket test (see §5 harness).

**Non-issues (verified clean):** `packages/runtime` absent; tsconfig base files exist;
Fastify pinned `^5.9.0`; `httpx>=0.28` present for HTTP forwards; single-barrel boundary
auto-covers the new package for the barrel check; lint globs `packages/` automatically.

---

## 7. Recommended build order

1. **Scaffold `@tm/runtime`** as a context package: `package.json` (exports single
   barrel), `tsconfig.json` (copy gateway's), `src/index.ts`, `src/server/runtimeRouter.ts`
   with `createRuntimeRouter(deps): FastifyPluginAsync`. Add `@fastify/websocket ^11` to
   catalog. Register `@fastify/websocket` inside the runtime plugin scope.
2. **Stub run lifecycle in the router:** `GET /runs` (list), `GET /runs/{id}` (get) over
   an injected in-memory stub store; `POST /runs` / `POST /runs/{id}/terminate` returning
   stub views shaped to `transport.ts`'s `RunView` (`runId/spaceId/worktreeId/sessionId/
   harness/state/createdAt`); `GET /runs/{id}/terminal` `{websocket:true}` echoing a
   `run.terminal.ready` JSON frame + byte echo. Write `runtimeRouter.test.ts` with
   `fastify.inject` (HTTP) + a real-socket WS test.
3. **Mount into Gateway:** extend `GatewayOptions` with `runtime?`, add the
   `gatewayContexts()` branch under `/v1`, `RUNTIME_CONTEXT_PREFIX`. Extend
   `packages/gateway/src/app.test.ts` to prove the runtime router mounts (mirror the
   activity mount test). Wire `runGatewayProcess`/`main.ts` to build with runtime deps.
4. **Python per-route proxy:** `run_proxy.py` — five explicit routes (4 httpx HTTP
   forwards + 1 websockets WS pump) targeting the Gateway origin; env-gated per R1(b).
   Strip hop-by-hop headers; preserve status/query/owner; per-frame type fidelity on WS.
5. **Origin-contract acceptance test (Python side):** boot Gateway on a loopback port,
   point Python's proxy at it, drive all eight canvas calls across the split incl. the WS
   leg via `TestClient.websocket_connect`. This is the slice's acceptance gate.
6. **Gate wiring:** `justfile` `check`/`test` + CI `product-plane` typecheck/test steps +
   importGraphBoundary RUNTIME case. Run `just check` + `just test` (verbatim) green.

Dependencies: 1→2→3 (TS) can proceed in parallel with 4 (Python) once the stub's wire
shape is fixed; 5 needs both; 6 last. Keep the runtime scaffold minimal — no empty
domain/service/adapters dirs beyond what the stub router imports.
