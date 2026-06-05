# Transport Matters Product Plane Vocabulary

## Recommendation

Recommendation: **unify-as-control-center**.

Use one product plane front door: **Control Center Gateway**. P1's "TS host" is the
first implementation slice of that gateway plus the Runtime context. Retire "TS
host" and "run host" as durable names after P1.

Control Center is the product surface. Control Center Gateway is the serving
process. Runtime is the bounded context that owns run lifecycle and terminal
attachment.

## 1. Verified State

"Control Center serving" is aspirational today. The phrase appears in
`docs/ARCHITECTURE.md::Two plane rule`, where TypeScript owns the product plane
and new contexts. Source search for `Control Center`, `control-center`, and
`controlCenter` finds no package, module, route, or API surface. The lower case
command center references are canvas launcher vocabulary, such as
`www/packages/canvas/src/session-canvas/launcher/commandModel.ts::command-center model`;
they are not the serving topology.

Today Python is the public origin. `api/src/transport_matters/main.py::create_app`
mounts `/api`, the run router, exchanges, run meta, stream, sessions, spaces, and
runtime templates. `api/src/transport_matters/main.py::mount_frontend_bundles`
serves the canvas bundle at `/canvas` and `/canvas-lab`, then serves the inspector
bundle at `/`. `CLAUDE.md::WWW workspace naming` describes the same built bundle
layout: inspector under `api/src/transport_matters/www/`, canvas under
`api/src/transport_matters/canvas/`.

The current run surface is Python. `api/src/transport_matters/api/v1/run_routes.py`
defines `create_run`, `list_runs`, `get_run`, `terminate_run`, and
`run_terminal_socket`. The implementation delegates to
`api/src/transport_matters/run_manager.py::RunManager`, especially
`RunManager._prepare_request`, `RunManager._start_run_terminal`, and
`RunManager._teardown_run`.

The run prefix has capture routes beside it. `api/src/transport_matters/api/v1/exchanges.py::RUN_EXCHANGES_ROUTE_PREFIX`
owns `/runs/{run_id}/exchanges`, and
`api/src/transport_matters/api/v1/meta.py::get_run_meta` owns
`/v1/runs/{run_id}/meta`. `api/src/transport_matters/api/v1/stream.py::stream_run`
owns `/v1/runs/{run_id}/stream` for live inspector events.

Existing `@tm/host` is already taken. `www/packages/host/package.json::name` is
`@tm/host`, and `www/packages/host/src/index.ts` exports browser chrome such as
`mountWindowChrome`, `ChannelBadge`, and `WindowDragRegion`. A new product plane
server named "host" would collide with the current workspace language.

## 2. Product Plane Serving Topology

Target topology:

```text
Browser or Electron renderer
  |
  | HTTP, WS, static assets, one origin
  v
Control Center Gateway, Node, package @tm/control-center
  | serves /, /canvas, /canvas-lab
  | mounts product context routers
  |   @tm/runtime/server: run lifecycle, terminal WS
  |   @tm/activity/server: activity reads and SSE
  |   future @tm/comms/server
  |   future @tm/recall/server
  |
  | proxies frozen capture plane routes
  v
Python capture plane
  | mitmproxy, Tier 1 writes, frozen Inspector API
  | exchanges, run meta, run stream, breakpoint, overrides
  | session writes while SessionWriter remains Python
  v
Postgres session store
  ^
  | product contexts read facts from Postgres
  |
@tm/activity, @tm/runtime, future product contexts
```

There should be one product plane serving gateway, not one public process per
context. Contexts can own routers and WebSocket handlers, but the operator sees one
origin. This preserves the frontend's current relative URL model:
`www/packages/core/src/transport.ts::requestApiJson` sends relative HTTP paths, and
`www/packages/canvas/src/session-canvas/viewers/terminal/terminalSocket.ts::runTerminalSocketUrl`
builds a same origin WebSocket URL from `window.location`.

P1 run routes live in Runtime, mounted by Control Center Gateway:

- `POST /v1/runs`
- `GET /v1/runs`
- `GET /v1/runs/{run_id}`
- `POST /v1/runs/{run_id}/terminate`
- `WS /v1/runs/{run_id}/terminal`

The Python capture plane keeps exchanges, run meta, run stream, breakpoint,
overrides, local file reads, and any Inspector API that still reads live mitmproxy
state. The scout supports that split: `tm-canvas-context-migration-scout.md::Verdict Table`
marks runtime templates clean, sessions and spaces coupled, and
`/v1/runs/{run_id}/stream` coupled to live proxy and inspector state.

P1 may keep Python as the temporary origin and reverse proxy the five Runtime
routes to the product plane server, as described in
`tm-t3code-p1-spec.md::serving-host seam`. Treat that as migration order,
not final vocabulary. The target front door is Control Center Gateway. In the
target, Control Center Gateway serves the canvas and inspector bundles and proxies
frozen capture routes to Python.

## 3. Ubiquitous Language

**Control Center**

The product surface for operating Transport Matters. It includes Canvas, Inspector,
Activity views, and future Comms and Recall surfaces. Runtime owns run lifecycle.
Python owns capture components. Control Center is the user facing place where those
contexts meet.

**Control Center Gateway**

The Node serving process and package that provides the product plane origin. It
serves browser assets, mounts product context routers, owns same origin HTTP and
WebSocket serving, owns product plane process lifecycle, and proxies frozen capture
plane APIs to Python. This is what `docs/ARCHITECTURE.md::Two plane rule` should
mean by "Control Center serving".

**Runtime**

The bounded product context that owns managed run lifecycle and terminal
attachment. It is the concrete home for the P1 route set and terminal transport.
The name is already in the architecture: `docs/ARCHITECTURE.md::Target context map`
names Runtime as the producer of RunStarted and RunExited lifecycle facts. Runtime
owns `RunManager`, PTY adapter, terminal fanout, run view projection, capture RPC
client, and lifecycle fact emission.

**Terminal**

A Runtime capability. Do not make "Terminal Host" a product context. Terminal
serving is one endpoint family under Runtime.

**Activity**

The downstream interpreter of run status, overview, and usage. It consumes Runtime
facts and transcript records. It never owns run lifecycle. This matches
`docs/ARCHITECTURE.md::Target context map` and
`packages/activity/src/domain/runActivityMachine.ts::runActivityMachine`.

**Canvas**

A browser surface under Control Center. It creates and attaches to Runtime runs
through `www/packages/core/src/transport.ts::createCapturedRun`,
`www/packages/core/src/transport.ts::terminateRun`, and
`www/packages/canvas/src/session-canvas/viewers/terminal/CapturedRunPane.tsx::AttachedRunTerminal`.

**Inspector**

A browser surface under Control Center. It remains capture plane backed while it
depends on exchanges, live run stream, breakpoint, overrides, and wire artifacts.
Examples are `www/packages/inspector/src/hooks/useExchangeStream.ts::useExchangeStream`
and `www/packages/inspector/src/components/ExchangeDetail.tsx::fetchExchange`.

## 4. Package Topology

Use repo root `packages/*` for product plane Node service packages, per
`docs/ARCHITECTURE.md::Product package placement` and `packages/AGENTS.md::Context packages`.
Keep browser packages under `www/packages/*`.

Control Center Gateway:

```text
packages/control-center/
  package.json       name @tm/control-center
  src/index.ts       public start and config surface
  src/domain/        route ids, origin contract, process invariants
  src/events.ts      gateway lifecycle facts if needed
  src/ports.ts       CapturePlaneProxy, StaticAssetProvider, ProductRouter
  src/service/       boot orchestration, lifecycle coordination
  src/adapters/      Python proxy, static bundle resolver, platform process hooks
  src/projections/   health and mounted route summaries
  src/server/        HTTP server, WS upgrade handling, router composition
  fixtures/          origin contract fixtures
```

Runtime:

```text
packages/runtime/
  package.json       name @tm/runtime
  src/index.ts       public runtime API and types
  src/domain/        run state, terminal frame invariants, ids
  src/events.ts      RunStarted, RunExited
  src/service/       RunManager, attach, detach, terminate
  src/ports.ts       PtyAdapter, CaptureLeaseClient, LifecycleSink, Clock
  src/adapters/      NodePtyAdapter, CaptureRpcClient, Postgres lifecycle sink
  src/projections/   RunView and list filters
  src/server/        five run routes plus terminal WS
  fixtures/          terminal and lifecycle parity corpus
```

Map the P1 draft files accordingly:

- `tm-t3code-p1-spec.md::host/src/RunHttpServer.ts` becomes
  `packages/control-center/src/server/createControlCenterServer.ts` plus
  `packages/runtime/src/server/runRoutes.ts`.
- `tm-t3code-p1-spec.md::host/src/RunManager.ts` becomes
  `packages/runtime/src/service/runManager.ts`.
- `tm-t3code-p1-spec.md::host/src/terminal/PtyAdapter.ts` and
  `NodePtyAdapter.ts` become Runtime adapters.
- `tm-t3code-p1-spec.md::host/src/capture/CaptureRpcClient.ts` becomes a Runtime
  adapter because Runtime consumes capture leases.
- `tm-t3code-p1-spec.md::host/src/platform/JobObject.ts` belongs in Control
  Center Gateway if it owns the Python sidecar process, and in Runtime only for
  PTY child ownership.

Do not add a new top level `host/` package. It violates the package placement rule
and conflicts with existing `@tm/host` browser chrome vocabulary.

## 5. Open Questions

1. Should sessions and spaces move behind product plane routers early, or should
   Control Center Gateway proxy them until their write ownership is redesigned?
   The scout says both are coupled today.
2. Should runtime templates move early? The scout marks `/v1/runtime-templates`
   clean, so it is a good first non Runtime route to move into the product plane
   after P1.
3. Should existing `www/packages/host` eventually rename to `@tm/chrome` or
   `@tm/window-chrome`? Recommended eventually, but not required if the server
   process uses Gateway language.

## Final Position

P1 should slot into Control Center serving, not create a separate durable run host.
The right model is one Control Center Gateway process and a Runtime context mounted
inside it. The gateway becomes the product plane origin, serves Canvas and Inspector,
and proxies frozen capture plane APIs to Python. Runtime owns the five moved run
routes, terminal WebSocket, PTY, and run lifecycle facts.

The other reviewer may prefer `distinct-run-host` because P1 only moves five routes
and can keep Python as the origin during the first slice. That is a reasonable
migration reading. I reject it as durable vocabulary because it bakes a temporary
route split into the architecture, collides with existing `@tm/host`, and leaves
Control Center serving undefined.
