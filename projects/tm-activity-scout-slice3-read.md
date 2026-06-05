# Scout: Activity slice 3 (read surface + packaging)

Date: 2026-07-04. Mode: Scout & Plan (audit only, no design, no code).
Baseline: main at `57fac6d` (slice 2 merged). Working tree pristine except the
pre-existing `docs/ARCHITECTURE.md` edit (untouched by this scout).
Contract source: `~/.mdx/projects/tm-activity-spec.md` §5.3, §7, §7.1, §9, §10.

Slice 3 delivers: `GET /workspaces/{id}/activity` (list of RunActivity
projections), a workspace-scoped SSE stream of projection deltas (sibling to
the run SSE; Python `broadcast.py` untouched), owner-scoped auth, rollups, and
the packaging answer for the Node product-plane service inside the one-tool
install rooted at `~/.transport-matters/`.

Citations are file + symbol. All searches listed were run against the full
tree excluding `node_modules`/`dist`.

---

## Reuse Map

### 1. HTTP surface to hang the route on

**None found.** There is no Node HTTP server, router, or framework anywhere in
the TS tree, and no `packages/gateway` directory anywhere (including `www/`).

Searches: all `package.json` manifests plus `pnpm-lock.yaml` for
`fastify|express|hono|koa|ws|socket.io` (zero hits); TS sources in `packages/`,
`www/`, `desktop/src/`, `shared/` for
`createServer|.listen(|http.Server|net.Server|WebSocketServer` and
`node:http|node:https|node:net` imports (zero hits); `find -type d -name
gateway` (nothing).

What exists instead:

- `packages/activity/src/server/` holds only `pgContracts.ts` (table/column
  name constants plus `TM_EVENTS_NOTIFY_CHANNEL`, payload-type and
  `EVENT_KIND_TURN` constants) and its test. No network code.
- `packages/activity/package.json`: deps `@tm/common`, `pg`, `xstate`; scripts
  `test` and `typecheck` only. No `build`, no `bin`, no server bootstrap.
- The Gateway (composition root mounting each context's `src/server/` router,
  serving the browser bundles, reverse-proxying the frozen capture plane) is
  specified in `docs/ARCHITECTURE.md` section "Product-plane gateway", but that
  section is an **uncommitted working-tree edit**; it exists on no branch.

Slice 3 stands up the first product-plane HTTP surface. Framework choice is
open; nothing in the lockfile pre-commits one.

### 2. The slice-2 projection substrate (strong reuse; the read model exists)

The §5.3 read model is already built and populated:

- `packages/activity/src/projections/workspaceActivity.ts`:
  `WorkspaceActivityProjections` is the two-tier projection.
  `index(workspaceId)` answers the coarse tier (which runs, latest lifecycle
  status) via `WorkspaceRunsSource.runsForWorkspace`, spawning no actor.
  `run(runId)` materializes on demand, subscribes once to the actor, and keeps
  an in-memory `RunActivityProjection` cache fresh. `current(workspaceId)`
  returns the cached projections. `runActivityProjection(runId, snapshot)` is
  the pure snapshot-to-read-model derivation.
- `RunActivityProjection` (same file) carries §5.3 field for field: runId,
  workspaceId, harness, launchKind, status, sinceTs, initialPrompt,
  lastMessage, contextTokens, totalUsage, exitReason. It is camelCase; a code
  comment records the intent that slice 3's HTTP layer owns the snake_case
  wire mapping.
- `packages/activity/src/service/activityIngestion.ts`: `ActivityIngestion`
  owns materialization. Public API: `materialize(runId)`, `isMaterialized`,
  `handlers()` returning `TmEventsHandlers` for the NOTIFY listener,
  `reconcileMaterialized()`, `stats()`, `stop()`, and an
  `onMaterialize(runId, actor)` observer option, documented as the projection
  wiring hook.
- `packages/activity/src/adapters/postgresRecords.ts`:
  `PostgresActivityReader` implements both the `ActivityStore` reads
  (`readRecordsForRunAfter`, `readLifecycleForRun`) and `WorkspaceRunsSource`
  (`RUNS_BY_WORKSPACE_SQL`, one grouped row per run).
- `packages/activity/src/adapters/tmEvents.ts`: `TmEventsActivityListener`
  plus `parseTmEventsPayload`; the single listener and reconnect path.

Two gaps, stated as facts:

- **No delta notification API.** `WorkspaceActivityProjections.store` is
  private and silent; nothing can observe projection changes from outside.
  The per-run emitter exists (`RunActor.subscribe` in
  `packages/activity/src/service/runActor.ts`, delegating to the XState
  actor), and `ActivityIngestion.onMaterialize` exists to wire it. The
  workspace-level change feed the SSE endpoint needs is the one missing piece
  of the substrate.
- **The seam is package-internal.** `packages/activity/src/index.ts` exports
  domain, ports, ids, and the harness registry; it exports none of
  `WorkspaceActivityProjections`, `ActivityIngestion`, `RunActor`,
  `PostgresActivityReader`, `TmEventsActivityListener`, or the telemetry. A
  server inside `src/server/` reaches them relatively; a separate gateway
  package cannot without deliberate barrel widening.

### 3. SSE / streaming primitive in the product plane

**None found** (server side). Search: `packages/` and `www/packages/` for
`EventSource|text/event-stream|ServerSentEvent|ReadableStream|sse|fanout|broadcast|subscribe(`;
hits are browser consumers, XState `.subscribe`, and one captured-header
assertion in `www/packages/inspector/src/components/detail/CodexTransportPanel.test.tsx`.

Browser-side consumers of the Python SSE (the pattern slice 4's `@tm/core`
activity hooks will follow; the wire shape slice 3 picks determines them):

- `www/packages/canvas/src/session-canvas/stream/useSessionEventStream.ts`:
  manual reconnect (`onerror` closes and reschedules), resumes from a
  `lastSeqRef` cursor in the URL, detects seq gaps and backfills via
  `listSessionEvents` before applying live events.
- `www/packages/inspector/src/hooks/useExchangeStream.ts`: relies on browser
  `EventSource` auto-reconnect and invalidates the react-query exchange cache
  on reconnect; applies frames through `applyExchangeStreamEvent` in
  `www/packages/core/src/exchangeStreamEvents.ts`.

### 4. `@tm/common` owner / identity / auth helpers

**None found.** `packages/common/src/index.ts` re-exports exactly eight
coercions from `primitives.ts` (`nonEmptyString`, `nullableString`,
`optionalInteger`, `optionalString`, `requiredInteger`, `requiredString`,
`safeInteger`, `timestampString`). Search across `packages/*/src` for
`auth|token|identity|owner|credential|bearer|apikey`: only LLM usage tokens
and record identity in `@tm/activity`, nothing auth-shaped.

### 5. Owner-scoping pattern (capture plane, reference only)

Owner: `api/src/transport_matters/api/v1/session_routes.py`. The mechanism:

- `owner` is a plain query parameter on every session read route,
  `DEFAULT_OWNER = "local"`. **No credential is minted or validated
  anywhere.** Enforcement is a SQL predicate: the routes call owner-suffixed
  DAO methods on `AsyncSessionDao`
  (`api/src/transport_matters/session/async_dao.py`), whose statements in
  `session/dao_statements.py` carry `AND owner = %(owner)s`.
- `_require_session` (session_routes.py) resolves session + owner and raises
  404 (`session_not_found`) on a cross-owner miss; not-found, never forbidden.
- Raw-byte omission: the session store holds parsed native JSON, shaped by
  Pydantic view models in `api/v1/session_models.py`
  (`SessionView`, `TranscriptEventView`, `_event_body`). Large byte payloads
  are offloaded: `get_session_resource` answers with an
  `ExchangeRedirectResponse` pointing at the exchange route instead of
  inlining bytes.
- SSE auth is the same owner query param (EventSource cannot set headers);
  resume is a `last_seq` query param, never the `Last-Event-ID` header.
- Network-level guards are global `TrustedHostMiddleware` + `CORSMiddleware`
  in `main.py` `create_app`. The origin check `require_http_origin`
  (`api/v1/terminal_bridge.py` `origin_allowed_for_request`) guards only run
  mutations and the terminal WebSocket. The run SSE `stream_run` has no
  guard of any kind.
- `DEFAULT_OWNER = "local"` is already duplicated between
  `session_routes.py` and `run_routes.py`.

### 6. Delta-stream shape to sibling (capture plane, reference only)

Two parallel, non-interoperable Python SSE stacks exist:

- Run stream: `api/src/transport_matters/broadcast.py` (module-global
  `_subscribers` map, per-subscriber `asyncio.Queue` maxsize 1000,
  drop-newest-on-full with a log line, `emit` filters by run_id) feeding
  `stream_run` in `api/v1/stream.py`. Framing: `data:`-only JSON frames, a
  synthetic `{"type": "connected"}` bootstrap, `: keepalive` comment on a 15s
  timeout, no `id:`, no `retry:`, no replay; a reconnecting client silently
  loses the gap.
- Session stream: `SessionEventHub` + `SessionEventListener` in
  `api/src/transport_matters/session/listen.py` (one long-lived `LISTEN
  tm_events` connection; NOTIFY payloads are wake-ups carrying seq handles,
  never content) feeding `_stream_session_frames` in `session_routes.py`:
  DB backfill from `last_seq + 1` before going live, snapshot bootstrap on
  the timeline variant (`project_timeline_stream_envelopes`), same
  keepalive and `data:`-only framing, unconditional unsubscribe in `finally`.

The session stack is the closer analog for the workspace stream: hub keyed by
scope, store-backed catch-up, snapshot then deltas. The TS side already owns
the equivalent inputs: `TmEventsActivityListener` (wake-ups),
`PostgresActivityReader` (store reads), and the projection cache (snapshot
source).

Confirmed fact: Python's `parse_notify_payload` (session/listen.py) returns
None for any payload type other than `session_events`, so the `run_lifecycle`
NOTIFYs emitted by `SessionWriter` reach no Python surface; the TS listener is
their only consumer, exactly as the spec requires.

### 7. Rollups

Owner exists for the per-run arithmetic:
`packages/activity/src/domain/usage.ts` (`UsageTotals`, `addUsage` with the
monotonic positive-delta fold, `windowTokens` for the current-window context
rule). Per-run `totalUsage` and `contextTokens` are already on
`RunActivityProjection`. A workspace-level aggregate has **no owner** (search:
`rollup|aggregate` in `packages/`); it would be a fold over the workspace's
projections at the server edge, no new state.

### 8. Workspace identity at the route boundary

`WorkspaceId` is minted at the reader boundary as the composite
`"${slug}/${hash}"`: `workspaceId(...)` in
`packages/activity/src/adapters/postgresRecords.ts`, split back by
`workspaceIdParts(...)` on the last `/` because the slug may itself contain
slashes while the hash never does. The route `{id}` must round-trip this
composite; embedded-slash encoding in the path is a contract detail slice 3
has to fix explicitly.

### 9. Packaging (the big open question)

**No precedent found** for shipping or launching a server-side Node process in
the installed tool. Searches: `api/src/**/*.py` for `Popen|node|which("node")`
(the only Node process Python ever spawns is Electron, in
`cli/desktop_cmd.py` `spawn_detached_electron`); repo-wide for
`esbuild|tsup|"pkg"|single-executable|sea-config|electron-builder` (only
`@electron/packager` as a root devDependency, used by a dev-only smoke build).

What exists, as the surrounding facts:

- Install chain: `uv tool install transport-matters`
  (`scripts/install.sh`; local dev via root `justfile` `install-local`,
  `uv tool install --force --editable api/`). One Python wheel, hatchling,
  entry point `transport-matters = "transport_matters.cli:main"`.
- Static-asset embedding precedent: vite builds `@tm/inspector` and
  `@tm/canvas` into gitignored `api/src/transport_matters/{www,canvas}/`;
  hatch `[tool.hatch.build.targets.wheel]` `artifacts` globs embed them in the
  wheel; `main.py` `mount_frontend_bundles` serves them via `SpaStaticFiles`.
  Assets only; there is no analog for a running process.
- Runtime topology: for CLI launches the FastAPI backend runs inside the
  mitmdump process (`addon.py` `TransportMattersAddon.load` starts a uvicorn
  server task via `addon_runtime.load_runtime`); the desktop path runs a
  standalone backend as a detached hidden CLI command (`_desktop-backend` in
  `cli/__init__.py`, `run_desktop_detached` in `cli/desktop_cmd.py`, with PID
  record, log redirect, and readiness probe).
- Supervised-child precedent (closest model for a Node sidecar):
  `SharedProxyManager` / `SharedProxyProcess`
  (`api/src/transport_matters/shared_proxy/manager.py`, `process.py`): a
  long-lived backend-owned subprocess spawned through `ProcessSupervisor`
  (`supervisor_core.py`), with PID record, reap-on-restart, readiness wait,
  and a monitor loop, created and closed in `main.py` `lifespan`.
- Electron is not in the wheel; `resolve_electron_launch` finds it only from a
  repo checkout or env overrides, so `transport-matters desktop` already does
  not work from a plain PyPI install. The spec's premise holds (users run Node
  CLIs by definition) but no delivery, launch, or supervision mechanism for a
  Node service exists.
- Registration seams if one is built: `doctor` checks in `cli/diagnose.py`
  `run_doctor`; dev loop `Procfile`; wheel `artifacts` globs; CI
  `product-plane` job (its comment already reserves the lane: "Slice 3 and
  future product contexts land here too").

### 10. Gates

- Repo recipes: root `justfile` `check` (typecheck fan including
  `pnpm --filter @tm/common typecheck` and `@tm/activity typecheck`) and
  `test` (serial: desktop, shell, `@tm/common`, `@tm/activity`, api);
  `test-affected` for changed-package runs.
- CI: `.github/workflows/ci.yml` job `product-plane`: postgres:17 service,
  pnpm typecheck + test for common and activity, integration gated by
  `TRANSPORT_MATTERS_TEST_DATABASE_URL`.
- Integration-test pattern to reuse:
  `packages/activity/src/pgIntegration.test.ts`: env-gated
  `describe.skipIf`, fail-closed reachability check (set-but-unreachable
  throws; cannot green by skipping), throwaway database built from the
  `pgContracts.ts` DDL constants.
- Boundary: `www/packages/shell/src/testSupport/importGraphBoundary.test.ts`
  auto-covers new files under `packages/activity/src/server/` (external deep
  imports fail closed; single-barrel `exports` enforced over every
  `packages/*` directory). A new `packages/gateway` gets the single-barrel and
  resolution checks automatically but needs its own
  `packageInternalViolations` reach-in assertion, which is hardcoded per
  package (activity, common) today.

---

## Quality Map

- **Third SSE stack (parallel-implementation risk, highest).** Python already
  carries two non-interoperable SSE stacks (`broadcast.py` vs
  `SessionEventHub`). The TS surface necessarily adds a third; the spec
  sanctions the sibling. The avoidable failure is a third framing dialect.
  Both existing stacks agree on `data:`-only frames, `: keepalive` at 15s, and
  query-param scoping; the two www consumer hooks already hand-roll two
  different reconnect strategies, and the wire shape slice 3 picks decides
  whether slice 4 adds a third.
- **Cross-plane literal duplication.** `DEFAULT_OWNER = "local"` exists twice
  in Python (`session_routes.py`, `run_routes.py`); a TS owner-scoped surface
  adds a third copy. Under the magic-string rule
  (`docs/ARCHITECTURE.md`, "Identifiers and literals standard") this is a
  cross-plane constant candidate, same treatment as `tm_events` got in slice
  1a (`pgContracts.ts` with a Python conformance test). The keepalive interval
  is the same class if the framing is mirrored.
- **Export-surface pressure.** The projection seam is package-internal by
  design. A server inside `src/server/` keeps it that way and is
  boundary-covered for free. A gateway package forces deliberate widening of
  `packages/activity/src/index.ts` plus a new reach-in assertion in
  `importGraphBoundary.test.ts`. Whichever home is chosen, the snake_case wire
  mapping should have exactly one owner at the server edge (the intent already
  recorded in `workspaceActivity.ts`).
- **Standard-on-uncommitted-doc drift.** The gateway standard slice 3 would
  build against lives only in the dirty `docs/ARCHITECTURE.md` working tree.
  Review would cite a standard that is on no branch. Landing that edit is a
  precondition for a clean slice 3 PR.
- **Auth posture honesty.** "Same auth posture as existing session read
  surfaces" means: unauthenticated `owner` namespacing plus
  TrustedHost/CORS/localhost deployment assumptions, with 404 on cross-owner.
  The Node service must sit behind the same posture (loopback bind, trusted
  hosts) or it silently weakens the deployment story. Pre-existing, adjacent,
  out of scope: the Python run SSE (`stream_run`) has no guard at all.
- **Dead code / sizing.** None found in `@tm/activity`; every file is well
  under the 700-line ceiling (largest is `postgresRecords.ts` at roughly 400
  lines), so no refactor-before-add trigger fires. The repo-wide dupe debt (26
  clusters, C grade) is tracked in `NOW.md` as its own groom-as-you-touch
  track, not slice 3 scope.

---

## Plan

**Decision needed (PRIMARY, packaging):** how a Node product-plane service is
delivered, launched, and supervised inside the uv-tool wheel install. Zero
precedent exists. The evidence names three candidate postures without
designing them: (a) wheel-embedded built JS launched as a supervised child on
the `SharedProxyProcess`/`ProcessSupervisor` model; (b) a detached hidden CLI
subcommand on the `_desktop-backend` model; (c) dev-mode only for v1 (repo
checkout + `Procfile` line), leaning on spec §7's note that packaging is "not
a blocker for the dev-mode slices". Stuart picks the posture; everything in
step 6 binds to it.

**Decision needed (secondary, server home):** `src/server/` inside
`@tm/activity` (canonical context shape, boundary-covered automatically, seam
stays internal) versus standing up `packages/gateway` now (the direction in
the uncommitted ARCHITECTURE.md edit; requires barrel widening plus a
boundary-test extension). The HTTP framework choice rides this decision; the
lockfile pre-commits nothing.

Ordered steps, each bound to the reuse map above:

1. Land the `docs/ARCHITECTURE.md` gateway section (currently uncommitted) so
   the slice builds against a committed standard.
2. Resolve the two decisions above.
3. `GET /workspaces/{id}/activity`: serve from
   `WorkspaceActivityProjections.index/run/current`; one snake_case mapper at
   the server edge; fix the `{id}` round-trip for the `"${slug}/${hash}"`
   composite (`workspaceIdParts`).
4. Delta seam: add the missing subscription API on
   `WorkspaceActivityProjections` (wiring hooks already exist:
   `ActivityIngestion.onMaterialize` + `RunActor.subscribe`); SSE endpoint
   mirrors the `SessionEventHub` semantics (snapshot bootstrap from the
   projection cache, then deltas; keepalive and framing parity with the
   existing stacks), leaving `broadcast.py` untouched.
5. Rollups: fold `UsageTotals` with `addUsage` over the workspace's
   projections at the server edge; no new persisted state (spec §7 defers
   rollup persistence to the ledger phase).
6. Owner scoping: mirror the `session_routes.py` owner-param + store-predicate
   pattern; single-source the `"local"` owner constant cross-plane per the
   magic-string rule, with a conformance test on the slice-1a model.
7. Doctor: expose `ActivityIngestion.stats()` /
   `ActivityTelemetry.snapshot()` through whatever transport the packaging
   decision yields (spec §8 names the doctor section; the seam exists in
   `packages/activity/src/telemetry.ts`).
8. Tests and gates, verbatim: vitest unit + a `pgIntegration.test.ts`-pattern
   env-gated integration suite for the server; owner-scope contract tests
   (spec §9); boundary-test additions only if the gateway package is chosen;
   `just check`, `just test`, and the CI `product-plane` job green.

---

## Addendum: alignment with the Runtime (T3) track, 2026-07-04

Cross-checked over the bus with the agent building the TS Runtime server
(P1 spec: `~/.mdx/projects/tm-t3code-p1-spec.md`, node-pty run lifecycle +
terminal, mitmproxy kept as a managed Python capture sidecar). Outcomes:

- **Server home precedent:** Runtime P1 serves from its own context
  (`packages/runtime/src/server/`, a standalone loopback HTTP+WS server).
  `packages/gateway` is target-only and is not built in P1; the Gateway
  subsumes the standalone Runtime server later. This matches this scout's
  secondary decision framing and points Activity slice 3 at the same shape:
  serve from `packages/activity/src/server/`.
- **Framework is unchosen on both tracks.** Runtime P1 deliberately leaves the
  HTTP/WS stack an open slice-1 decision. Joint blocker: one stack must be
  picked once, for both contexts, so Activity mounts a router rather than a
  second dialect. Escalated to Stuart by the Runtime agent.
- **Packaging gap confirmed from their side.** Runtime P1 specifies only the
  Electron path (a plain-TS DesktopBackendManager spawns and owns the Runtime
  server, graceThenForce SIGTERM + 2s + SIGKILL). Delivery/launch/supervision
  of the Node service in the non-Electron uv-tool wheel is unresolved there
  too and is now flagged as a joint decision; this scout's candidate postures
  stand as the option set.
- **Conventions:** Runtime adopts owner-param scoping and the SSE framing
  parity described above (mirror, never fork); agrees `DEFAULT_OWNER "local"`
  is a cross-plane-constant candidate.
- **Lifecycle contract frozen:** Runtime P1 makes the Runtime context the
  RunStarted/RunExited producer (`packages/runtime/src/events.ts`) and moves
  the Python write sites (`RunManager._teardown_run`,
  `CapturedRunLease.close`, launch registration) into TS as the port lands.
  Both tracks treat `pgContracts.ts` `RUN_LIFECYCLE_EVENT_*` plus the
  `run_lifecycle` NOTIFY on `tm_events` as a frozen cross-plane contract
  during the port, versioned deliberately if it must move. Activity ingestion
  is unaffected while that holds.

### Consensus package (agreed between the two tracks)

**Verdict 2026-07-04: Stuart blessed all three.** Fastify + thin Gateway-now +
dev-mode-only v1 supervision (SharedProxyProcess model at the wheel
milestone). Activity slice 3 binds to Fastify and the Gateway-mount model,
exposing a router/context factory from the barrel, never internals. The
ARCHITECTURE.md "Product-plane gateway" section is committed (`b412646` on
branch `docs/product-plane-gateway`, landing to main via PR), so the
standard-on-no-branch drift item is resolved. The two gating costs and the
resume-per-stream SSE nuance below carry into the Phase 3 Linear
decomposition, where the Gateway lands as a shared slice-0 prereq ahead of
Runtime slice 1. The decision lines in the Plan above are settled by this
verdict.

The agreed positions, as taken to Stuart:

1. **Thin `packages/gateway` now.** Two concurrent standalone context servers
   would recreate the second-dialect and second-supervision problem this
   scout flagged and break "one origin, many routers". The Gateway is a
   composition root owning no domain; Runtime and Activity keep
   `src/server/` and each export a mountable router factory through their
   barrel. The barrel widening stays minimal (a factory, never the internal
   seam); whether the factory takes a pg handle or builds its own adapters is
   a slice-1 design item. This revises Runtime P1's "Gateway not built in
   P1". Named costs: `importGraphBoundary.test.ts` needs a dedicated gateway
   no-reach-in assertion (the check is hardcoded per package), and both the
   `justfile` recipes and the CI `product-plane` job enumerate packages by
   explicit pnpm filter, so gateway must be added to both or it ships
   ungated. Python remains the interim front door, reverse-proxying
   product-plane routes to the one Gateway.
2. **Fastify**, one stack for both contexts: plugin/prefix encapsulation fits
   the mount-many-routers shape, `@fastify/websocket` covers the terminal
   stream, raw-reply SSE covers the workspace stream, and `inject()` gives
   port-less route tests in the repo's env-gated testing norm. Caveat per the
   spec's own discipline (the XState precedent, tm-activity-spec §4): pin the
   current major and verify against current docs at slice start.
3. **Wheel supervision: dev-mode-only v1** for the Gateway process, consistent
   with Electron already being checkout-only and spec §7's dev-mode sanction.
   Desktop mode: DesktopBackendManager spawns the Gateway (P1 mechanism
   unchanged). At the future wheel milestone: embed built Gateway JS via the
   existing hatch `artifacts` glob and supervise as a Python-owned child on
   the `SharedProxyProcess`/`ProcessSupervisor` model (posture a). Posture b
   (detached `_desktop-backend`-style subcommand) rejected: detached with PID
   record but unsupervised, wrong for a long-lived service.
4. **Dialect nuance:** the shared SSE dialect specifies framing and auth
   (`data:`-only, `: keepalive` 15s, owner param); resume semantics stay per
   stream. `last_seq` resume belongs to durable seq'd session rows; the
   workspace stream resumes by snapshot-then-deltas on reconnect because
   projections are in-memory with no replayable cursor.
