# Transport Matters startup process scout

## Scope and baseline

Read only inspection of process startup at commit
`841e385ba4abd60f46dd83d6b2de0a75aa880111` on `ml/next`. The repository was
clean before inspection. No application, service, authentication flow, token
exchange, live Postgres connection, or keychain operation was run.

The governing architecture is the API first desktop model in
`docs/ARCHITECTURE.md`, with the onboarding gap recorded in `NOW.md`.

## Answer

There is no single startup seam. Policy and mechanics are distributed across
Electron, the Python CLI, FastAPI lifespan, the Python Gateway supervisor, the
Node Gateway entrypoint, background harness refresh, launch preparation, and
doctor.

On an empty desktop database, the first complete
`SpaceId + WorktreeId + CanvasId` comes from an explicit create operation.
The normal UI path is `Create new Workdir`, whose empty inventory branch
creates a Space, creates the Workdir, receives its root Canvas, and activates
the full tuple. Context resolution itself is read only and returns
`worktree_not_found` for an empty inventory.

Sources:

* `www/packages/canvas/src/workbench/spaceCommandDispatcher.ts:createWorkdirWithBootstrap`
* `api/src/transport_matters/space/worktree_mutations.py:create_workdir`
* `api/src/transport_matters/space/store_worktree_ops.py:ensure_worktree_root`
* `packages/space/src/service/SpaceContextService.ts:resolveWorkdirContext`
* `packages/space/src/domain/actingContext.ts:resolveWorkdirCandidate`

## Real startup sequence

### 1. Electron desktop main

| Order | Trigger and owner | Blocking behavior | Failure behavior | Operator visibility |
| --- | --- | --- | --- | --- |
| 1 | Module entry calls `desktop/src/main.ts:registerDesktopLifecycleFromEnv`. Channel identity is applied before mode selection. | Synchronous mode selection. | Package smoke and hosted route modes bypass managed process launch. | No startup UI yet. |
| 2 | `desktop/src/main.ts:registerAppLifecycle` creates one Python manager, one Gateway manager, and `DesktopShutdown`, then waits for Electron readiness. | Blocks managed launch until `app.whenReady()`. | Lifecycle registration errors would reject the readiness continuation. | Process log unless caught by a later managed launch boundary. |
| 3 | Packaged mode uses `desktop/src/main.ts:startBundledStandalone`. Development mode uses `desktop/src/main.ts:startAmbientOrManagedBackend`. | Packaged mode always owns bundled children. Development mode first reuses a matching live runtime, then tries stale runtime reclamation, then launches children. | Reclamation failure reaches `showBackendStartupFailure`. | Modal error and application exit. Smoke mode prints to stderr. |
| 4 | `desktop/src/main.ts:launchManagedBackend` calls `startBackendAndCreateWindow`. | Python is spawned first. Gateway is spawned immediately after. Both health waits are collected with `Promise.allSettled`. No window is created until both pass. | A synchronous Gateway spawn failure stops Python. Any readiness failure stops Gateway, then Python, and throws the first relevant failure. | `showBackendStartupFailure` shows a modal and quits. Gateway failures include recent child stdout and stderr through `desktop/src/gateway/gatewayProcess.ts:gatewayRecentOutput`. |
| 5 | `desktop/src/main.ts:startBackendAndCreateWindow` creates the first BrowserWindow only after both health endpoints respond. | Hard desktop readiness gate. | Python child exit, Gateway child exit, process error, or health failure rejects startup. | Modal and exit. |
| 6 | `desktop/src/window.ts:createHostedWindow` loads the renderer. | The hidden window appears at `ready-to-show`. | A main frame load failure displays an error box. | User visible error box. |

Python launch construction is owned by
`desktop/src/backendProcess.ts:buildBackendLaunch`. It launches the private
`_desktop-backend` command and passes `TRANSPORT_MATTERS_GATEWAY_URL`, which
makes the Electron child the external Gateway owner.

Gateway launch construction is owned by
`desktop/src/gateway/gatewayProcess.ts:buildGatewayLaunch`. The child uses the
Electron executable with `ELECTRON_RUN_AS_NODE=1`, the bundled Gateway entry,
the capture RPC URL, the selected Gateway port, and an optional database URL.
This makes the packaged path independent of `PATH` Node and preserves the
expected `node-pty` ABI.

Development hosted mode has a separate postboot liveness path.
`desktop/src/main.ts:registerHostedDesktopLifecycle` starts
`desktop/src/hostedLiveness.ts:registerHostedBackendLivenessPoll`. Three failed backend
health checks quit the application. This path does not show the managed startup
modal.

### 2. Python desktop command and Postgres preflight

The Electron Python child enters
`api/src/transport_matters/cli/desktop_cmd.py:serve_desktop_backend`.

The order is:

1. Apply the child environment.
2. Run
   `api/src/transport_matters/cli/launch_runtime.py:preflight_session_store_or_exit`.
3. Import and build FastAPI through `api/src/transport_matters/main.py:create_app`.
4. Run `api/src/transport_matters/web_runtime.py:GatewayAwareServer`.

The preflight first scaffolds settings, clears the settings cache, then calls
`api/src/transport_matters/session_store_preflight.py:prepare_session_store`.
That function resolves the database URL, opens a five second `psycopg`
connection, executes `SELECT 1`, and applies migrations.

Missing configuration, connection failure, or migration failure prints the
actionable setup text from
`api/src/transport_matters/session_store_preflight.py:session_store_setup_help`
and exits with status 2. FastAPI never starts. Electron observes the child exit,
shows the startup modal, and quits.

Captured CLI launch paths reuse
`api/src/transport_matters/cli/launch_runtime.py:preflight_session_store_or_exit`.
The bare `web_runtime` helper does not perform preflight by itself. Its callers
determine whether the hard guard ran.

### 3. FastAPI composition and lifespan

`api/src/transport_matters/main.py:create_app` performs synchronous
composition:

1. Resolve settings and configure logging.
2. Build the FastAPI application, middleware, routers, static bundles, and
   health route.
3. Call
   `api/src/transport_matters/gateway_supervisor.py:plan_gateway_supervision`.
4. Mount the run and acting context proxy against either an external Gateway
   URL or the planned child URL.
5. Mount explicit 503 stubs when no Gateway can be planned.

No process is spawned by `create_app`.

In packaged Electron, the external Gateway URL suppresses Python Gateway
supervision. In backend owned web mode, planning resolves the bundled or
workspace Gateway entry, the bundled or `PATH` Node executable, an available
port, and the child environment. A broken explicit entry raises. Missing Node
or an implicit missing entry records a degraded plan and leaves run surfaces
unavailable.

`api/src/transport_matters/main.py:lifespan` then runs this order:

1. Spawn a planned Gateway child through
   `api/src/transport_matters/gateway_supervisor.py:spawn_planned_gateway`.
2. Start
   `api/src/transport_matters/gateway_supervisor.py:watch_supervised_gateway`
   as a background task.
3. Initialize process resident app state and a pending shared proxy manager.
4. Call
   `api/src/transport_matters/main.py:_start_session_backed_services`.
5. Build the capture registry after the session pool result is known.
6. Build the active control plane grant resolver when the store is live.
7. Schedule harness refresh as a background task when the store is live.
8. Enter the MCP session manager and yield application readiness.

The Python owned Gateway watcher is not a readiness gate. It polls until health
or child exit and has no startup deadline. Spawn failure and later child exit
are logged. FastAPI remains live and the affected routes return 503.

`_start_session_backed_services` resolves Postgres again.
`api/src/transport_matters/main.py:_start_session_store` opens the pool,
applies migrations again, and starts the session event listener.

Failure policy differs by failure class:

* Missing database configuration logs a storeless degradation.
* Initial connection failure logs a storeless degradation.
* A `MigrationError` escapes and fails FastAPI lifespan.
* Other operational migration errors log a storeless degradation.
* Session event listener failure logs a degradation.
* Shared proxy startup failure logs a degradation and disables overrides.

When the desktop command ran its preflight, the second migration pass normally
returns at the schema head. The shared migrator is
`api/src/transport_matters/session/migrate.py:apply_migrations`, which uses a
Postgres advisory lock when an upgrade is required.

### 4. Node Gateway

The Node child enters `packages/gateway/src/main.ts:runGatewayProcess`.

Its order is:

1. Resolve Activity dependencies.
2. Resolve Space dependencies.
3. Resolve Runtime dependencies.
4. Build the Fastify application.
5. Install process and parent shutdown handlers.
6. Listen on the requested host and port.

With no database URL, Activity and Space log warnings and remain disabled.
With a database URL,
`packages/activity/src/gatewayDeps.ts:createActivityGatewayDeps` creates a
pool and starts `TmEventsActivityListener`. Listener startup failure closes
partial resources and fails the Gateway process. Space creates its pool in
`packages/space/src/gatewayDeps.ts:createSpaceGatewayDeps`; the first query may
be its first real connection.

Runtime uses a capture RPC client when the Python URL is present. Otherwise
`packages/gateway/src/main.ts:createDefaultRuntimeRouterDeps` logs a warning
and uses an uncaptured stub.

`packages/gateway/src/app.ts:buildGateway` mounts the ordered Activity, Runtime,
and Space contexts and waits for Fastify composition before returning. The
health route reports `ok` after this composition.

Partial startup failure is logged to stderr, resources are closed, and the
process exits with status 1. Electron treats that as a hard desktop failure.
The Python supervisor treats it as a degraded Gateway.

### 5. Harness detection, catalog, version, and authentication

Harness startup work begins only after a live session pool exists.
`api/src/transport_matters/main.py:lifespan` schedules
`api/src/transport_matters/harnesses/state_refresh.py:run_startup_refresh`
without awaiting it.

`api/src/transport_matters/harnesses/state_refresh.py:refresh_harness_state`
runs this sequence for the descriptor registry:

1. Call `api/src/transport_matters/capabilities.py:detect_harnesses` outside
   the event loop.
2. Resolve each executable and run its version command with a two second
   timeout.
3. Persist the install observation.
4. Reconcile the native connection for installed, versioned, embedded
   releases.
5. Enumerate the model catalog when the exact version and probe revision lack
   a cached snapshot.
6. Run authentication probes for each connection.

The descriptor registry currently includes Claude, Codex, and Grok.
Model commands are owned by the descriptor and probe layers. Claude uses
print mode model and effort commands. Codex uses `debug models --bundled`.
Authentication probes use Claude `auth status --json` and Codex
`login status`. Probe execution uses a five second timeout.

Missing binaries are stored as absent. A failed version command can be stored
as installed with an unknown version. Per harness and per connection failures
are logged and isolated. `run_startup_refresh` catches any final failure, so
the application stays ready and the last known evidence remains.

`api/src/transport_matters/harnesses/inventory.py:harness_inventory` performs
no live executable or authentication probes. REST and MCP inventory reads
join stored installation, enablement, channel, compatibility, model, effort,
and authentication evidence.

Launch preparation performs another live executable and version check through
`api/src/transport_matters/harnesses/compatibility_service.py:gate_launch_preparation`.
The current `COMPATIBILITY_ROLLOUT` is advisory, so compatibility and internal
gate outcomes permit launch. Missing executable resolution and disabled
harness state still fail at their owning launch boundaries.

`api/src/transport_matters/cli/claude_home.py:ClaudeSeeder` is part of managed
launch preparation. It writes a run local home, trust metadata, onboarding
metadata, and proxy settings. Existing credential metadata may be copied or
linked by the overlay path. It does not detect or perform first authentication.

## The four prerequisite gates

### Postgres

Current status: a hard gate for managed desktop and captured CLI launch, with
different behavior in direct FastAPI and Node Gateway paths.

| Path | Ruling |
| --- | --- |
| Electron managed desktop | Hard through Python preflight. Any missing URL, reachability error, or migration error exits the child. |
| Captured CLI launch | Hard through the same preflight. |
| Direct FastAPI lifespan | Missing configuration and connection errors degrade. `MigrationError` is fatal. |
| Electron owned Gateway | A configured database whose Activity listener cannot start causes Gateway exit, so desktop startup fails. |
| Python owned Gateway | Gateway failure logs and degrades run and acting context routes to 503. |
| Doctor | `session store` is a failing check for missing configuration, reachability failure, uninitialized schema, or a revision behind head. |

This gate is evaluated in multiple places. Desktop preflight migrates before
FastAPI import, FastAPI lifespan repeats migration, and the Gateway independently
opens Postgres dependencies. The migration implementation is shared, while
startup policy is scattered.

### Harness presence and version

Current status: advisory at application startup and compatibility launch
gating, with hard failure deferred to concrete launch resolution.

Application startup never waits for discovery, model enumeration, or
authentication. The first inventory request can race the background refresh
and see no fresh observations.

Doctor prints one check per managed harness:

* Installed: `ok <name>` with a version or `version unknown`.
* Missing: `warn missing <name>`.

Doctor does not compare a detected version with the embedded supported
release range. These warnings do not affect its exit status.

The actual launch path performs a fresh binary and version probe. Compatibility
decisions remain advisory under
`api/src/transport_matters/harnesses/compatibility_service.py:COMPATIBILITY_ROLLOUT`.
Selected target resolution can still reject disabled, absent, ambiguous, or
structurally invalid inventory before process spawn.

### Authentication

Current status: diagnostic background evidence exists. First authentication is
manual. Doctor has no authentication check.

The startup refresh can persist `authenticated`, `login_required`, `expired`,
or `unknown` for supported connections. Inventory surfaces that last known
diagnostic evidence. It neither authorizes nor blocks launch.

`api/src/transport_matters/credential_broker.py:CredentialBroker` implements
serialized owner credential refresh, access only minting, keychain storage, and
token exchange ports. There is no production caller under `api/src`,
`packages`, `desktop/src`, or `www/packages`. The broker is therefore merged
core without startup or launch wiring.

The manual owner bootstrap instruction is
`api/src/transport_matters/credential_broker.py:_WRITE_BACK_ERROR_MESSAGE`:

```text
CLAUDE_CONFIG_DIR=~/.claude-auth claude auth login
```

The requested doctor ruling is absent. `transport-matters doctor` checks
presence and version text only. It should call the existing authentication
probe, report login required or expired, and print the manual bootstrap command
without invoking authentication or token exchange.

### Space, Worktree, and Canvas tuple

Current status: a complete tuple is mandatory for Canvas launch. Resolution has
no seeding side effect.

`packages/space/src/ports.ts:SpaceContextRepository` exposes read snapshots.
`packages/space/src/service/SpaceContextService.ts:verifyActingContext` and
`resolveWorkdirContext` only read those snapshots.
`packages/space/src/domain/actingContext.ts:validateActingContextCandidate`
requires all three identifiers.

`www/packages/canvas/src/model/canvasIdentityOwner.ts:initializeFromLaunch`
tries an explicit URL or window locator claim, then the launch `cwd`. Empty
inventory resolution returns `worktree_not_found`, and Canvas identity
hydration becomes blocked. It creates no records.

Canvas capture repeats the authority check.
`api/src/transport_matters/api/v1/capture_rpc_routes.py:_resolved_domain_request`
requires `spaceId`, `anchorWorktreeId`, `worktreeId`, and `canvasId`.
`api/src/transport_matters/api/v1/launch_resolution.py:resolve_run_canvas`
revalidates owner, Space, Worktree, anchor, and Canvas against Postgres.

Creation is explicit:

* `www/packages/canvas/src/workbench/spaceCommandDispatcher.ts:createEmptySpace`
  creates an empty Space. This alone cannot supply a launch tuple.
* `www/packages/canvas/src/workbench/spaceCommandDispatcher.ts:createWorkdirWithBootstrap`
  creates a Space when inventory is empty, then creates the Workdir, receives
  its root Canvas, and activates the tuple. It rolls the new Space back if
  Workdir creation fails.
* `api/src/transport_matters/cli/space_bootstrap.py:bootstrap_cli_space` is the
  explicit detached CLI launch composition. It reuses an unambiguous existing
  Workdir or creates a Space and Workdir, then resolves the root Canvas.
* `api/src/transport_matters/api/v1/space_routes.py:create_space` and
  `create_workdir` are the REST mutation boundaries.

The no seeding rule therefore applies to context discovery and verification.
Explicit create and explicit detached launch bootstrap are the two intentional
mutation paths.

## Doctor check inventory

`api/src/transport_matters/cli/diagnose.py:run_doctor` is one imperative
function. These are its printed checks and exit semantics:

| Check | Failure class |
| --- | --- |
| `python` | Fail below Python 3.12. |
| `mitmdump` | Fail when unresolved. |
| `addon` | Fail when the packaged addon is missing. |
| `node` | Warning when unresolved. |
| `gateway` | Fail for a broken explicit entry. Warning when no implicit entry exists. |
| `web bundle` | Warning when absent. |
| `claude`, `codex`, `grok` | Success when installed. Warning when missing. Unknown version still succeeds. |
| `storage` | Fail when the write and remove probe fails. |
| `proxy port` | Warning when the configured default is occupied. |
| `web port` | Warning when the configured default is occupied. |
| `session store` | Fail when missing, unreachable, uninitialized, or behind migration head. |
| live `runs` report | Read only unless `--reap-orphans` is explicitly supplied. API absence produces no hard failure. |

The gaps relevant to startup are authentication status, supported harness
version ruling, Gateway process health in a live desktop, startup step status,
and empty Space inventory guidance.

## Startup locations

These are the active process or policy boundaries that participate in startup:

* `desktop/src/main.ts:registerDesktopLifecycleFromEnv`
* `desktop/src/main.ts:registerAppLifecycle`
* `desktop/src/main.ts:startBundledStandalone`
* `desktop/src/main.ts:startAmbientOrManagedBackend`
* `desktop/src/main.ts:launchManagedBackend`
* `desktop/src/main.ts:startBackendAndCreateWindow`
* `desktop/src/backendProcess.ts:buildBackendLaunch`
* `desktop/src/gateway/gatewayProcess.ts:buildGatewayLaunch`
* `desktop/src/window.ts:createHostedWindow`
* `desktop/src/hostedLiveness.ts:registerHostedBackendLivenessPoll`
* `api/src/transport_matters/cli/desktop_cmd.py:serve_desktop_backend`
* `api/src/transport_matters/cli/launch_runtime.py:preflight_session_store_or_exit`
* `api/src/transport_matters/session_store_preflight.py:prepare_session_store`
* `api/src/transport_matters/main.py:create_app`
* `api/src/transport_matters/main.py:lifespan`
* `api/src/transport_matters/main.py:_start_session_backed_services`
* `api/src/transport_matters/gateway_supervisor.py:plan_gateway_supervision`
* `api/src/transport_matters/gateway_supervisor.py:spawn_planned_gateway`
* `api/src/transport_matters/gateway_supervisor.py:watch_supervised_gateway`
* `api/src/transport_matters/web_runtime.py:start_web_runtime`
* `api/src/transport_matters/gateway_supervisor.py:GatewayAwareServer.shutdown`
* `packages/gateway/src/main.ts:runGatewayProcess`
* `packages/activity/src/gatewayDeps.ts:createActivityGatewayDeps`
* `packages/space/src/gatewayDeps.ts:createSpaceGatewayDeps`
* `packages/gateway/src/app.ts:buildGateway`
* `api/src/transport_matters/harnesses/state_refresh.py:refresh_harness_state`
* `api/src/transport_matters/harnesses/state_refresh.py:run_startup_refresh`
* `api/src/transport_matters/capabilities.py:detect_harnesses`
* `api/src/transport_matters/harnesses/inventory.py:harness_inventory`
* `api/src/transport_matters/harnesses/compatibility_service.py:gate_launch_preparation`
* `api/src/transport_matters/cli/diagnose.py:run_doctor`
* `www/packages/canvas/src/model/canvasIdentityOwner.ts:initializeFromLaunch`
* `www/packages/canvas/src/workbench/spaceCommandDispatcher.ts:createWorkdirWithBootstrap`
* `api/src/transport_matters/cli/space_bootstrap.py:bootstrap_cli_space`

## Refactor finding

### Existing precedent

There is no reusable startup step registry in the inspected source.

Three nearby patterns are suitable precedents:

1. `api/src/transport_matters/cli/launch_profile.py:HARNESSES` maps a stable
   harness identity to one behavior owner. Its module states that a new
   harness is one profile and one registry entry.
2. `packages/gateway/src/app.ts:gatewayContexts` returns an ordered list of
   descriptors, and `packages/gateway/src/app.ts:buildGateway` applies each
   through one loop.
3. `packages/common/src/closeAll.ts:closeAll` executes an ordered resource list
   with consistent error aggregation. Gateway shutdown uses it through
   `packages/gateway/src/main.ts:closeGatewayResources`.

`api/src/transport_matters/cli/diagnose.py:run_doctor` has useful result and
hint semantics, but its checks are hard coded in one long function. It is a
consumer to replace, rather than the registry precedent.

### Proposed seam

Create one Python owned, ordered, configurable startup registry. Python is the
appropriate policy owner because Postgres preflight, migrations, harness
detection, authentication probes, inventory, launch compatibility, doctor, and
FastAPI already live there.

Use small records with this conceptual contract:

```text
StartupStep
  id
  phase
  modes
  policy
  probe
  prepare
  operator_hint

StartupOutcome
  id
  status
  detail
  operator_action
```

`modes` should cover packaged desktop, hosted web, captured launch, detached
CLI launch, and doctor. `policy` should be one of hard, degraded, advisory, or
needs setup. `probe` is read only. `prepare` performs the already authorized
launch mutation, such as an advisory locked migration. Each behavior remains
in its current domain module. The registry composes existing functions and
does not duplicate them.

Recommended order:

1. Settings and packaged resources.
2. Postgres configuration, reachability, and migration.
3. Gateway entry and Node resolution.
4. Gateway process readiness.
5. FastAPI session backed services.
6. Harness executable and version observations.
7. Authentication observations.
8. Space inventory status.
9. Model catalog refresh and other advisory background work.
10. Ready, degraded, or needs setup result.

Expose the outcomes through one backend startup status surface. Electron should
render the result and operator action. Doctor should run the same registry in
probe mode and format the same outcomes. Launch preparation should select and
recheck the relevant harness steps with hard launch policy.

The desktop currently needs Electron as Node for the bundled Gateway. Preserve
that fact as injected launch data. Move Gateway policy and readiness into the
Python registry, passing the Electron executable and bundled entry to the
backend. Then delete the parallel Electron Gateway supervisor. Electron keeps
only application lifecycle, Python child ownership, startup status display, and
window ownership.

This yields one policy seam while preserving process specific adapters.

### Migration slices

1. Extract doctor outcomes without changing behavior. Reuse
   `check_session_store`, `detect_harnesses`, Gateway resolvers, and storage or
   port probes.
2. Add authentication and Space inventory probe steps. Authentication reports
   the existing manual bootstrap command. Empty inventory returns
   `needs_setup` and performs no create.
3. Route desktop preflight and FastAPI lifespan through the same registry.
   Pass the prepared database result into session service startup so migration
   runs once per process boot.
4. Publish structured startup status and make Electron consume it.
5. Move bundled Gateway ownership behind the Python adapter, then remove
   `desktop/src/gateway/gatewayProcess.ts` and mirrored Gateway policy.
6. Route selected harness launch preparation through the same step owner.
7. Delete replaced imperative doctor and duplicated startup branches in the
   same changes that adopt the registry.

## Defect and risk map

### Duplicated authority

* Electron and Python both resolve, spawn, watch, and stop Gateway children.
  Their failure policy differs.
* Electron and Python both resolve a database URL for their Gateway path.
* Desktop preflight and FastAPI lifespan both apply migrations.
* Harness facts are checked by background refresh, doctor, and launch
  preparation with different ruling semantics.
* Gateway stop grace and child ownership exist in separate language runtimes.

### Dead or disconnected work

* `api/src/transport_matters/credential_broker.py:CredentialBroker` has no
  production composition root.
* Doctor has no authentication ruling despite the probe and manual recovery
  command already existing.
* `api/src/transport_matters/cli/claude_home.py:ClaudeSeeder` marks a run local
  Claude home as onboarded without proving owner authentication. The flag is a
  harness setup fact, so product onboarding must not infer auth from it.
* `NOW.md` records the visible first run onboarding as unbuilt.

### Ordering hazards

* Electron launches Python before Gateway, then waits for both. Python is
  configured for an external Gateway and can report health independently.
  The aggregate desktop gate currently prevents early window creation.
* Python owned Gateway spawn occurs before session store startup and migration.
  Gateway and Python can touch the same database during separate startup
  phases.
* Harness refresh starts after the session pool and is never awaited. Early
  inventory reads can observe stale or absent evidence.
* An empty Space inventory blocks Canvas identity with
  `worktree_not_found`. Startup provides no structured `needs_setup` state.
* Creating an empty Space still leaves Canvas launch blocked until a Workdir
  and its root Canvas exist.
* Direct FastAPI, Python supervised Gateway, and Electron managed desktop
  assign different fatality to equivalent Postgres or Gateway failures.

### User visibility gaps

* Managed Electron child failure is visible through one modal, with good
  Gateway recent output.
* Python degraded services are logs plus later 503 responses.
* Background harness and auth failures are logs plus stored inventory
  diagnostics after refresh.
* Hosted backend liveness loss quits the desktop without the managed startup
  explanation.
* Empty Space inventory has launcher commands, but no process level startup
  result explaining the required full tuple.

## Shutdown

Current desktop order is correct: Gateway stops before Python so run lease
release RPCs reach a live backend. Ownership is duplicated between
`desktop/src/main.ts:desktopShutdownFinalizers`,
`api/src/transport_matters/gateway_supervisor.py:GatewayAwareServer.shutdown`, and
Node `packages/gateway/src/main.ts:closeGatewayResources`. The startup authority
should own reverse order teardown through the same resource registry, following
`packages/common/src/closeAll.ts:closeAll`, with Electron retaining only its
owned Python process finalizer.

## Recommended ruling

Adopt a single Python startup registry as the source of ordering, fatality,
status, and operator guidance. Keep behavior inside existing domain functions.
Represent an empty Space inventory as `needs_setup`, and create the first Space
only through the existing explicit UI or detached CLI composition. Add the
missing doctor authentication verdict immediately, using the existing probe
and manual login instruction, without wiring live authentication into doctor.
