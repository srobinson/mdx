---
title: Agent facing control plane, Codex architecture
type: projects
tags: [transport-matters, control-plane, design, codex]
status: proposed
source: CONTROLPLANE.md plus both scouts, main 0d88c1081f104cbd3adca771061772be256eb874
created: 2026-07-11
---

# Agent facing control plane: Codex architecture

This design was produced independently against pristine `main` at
`0d88c1081f104cbd3adca771061772be256eb874`. It binds to all existing owners in
the two scout reuse maps. It creates no second run registry, capture path, home
materializer, activity state machine, timeline projector, migrator, or session
store.

## Decision summary

Choose placement **(a): one Python service with a typed private Gateway RPC
adapter**.

`api/src/transport_matters/controlplane/::ControlPlaneService` is the sole
application service. REST and MCP call it directly. It owns principal based
authorization, grant resolution, workspace scope, observe projection,
dispatch orchestration, and durable audit.

The Node process hosts `@tm/controlplane-bridge`, a private execution adapter.
It owns mechanics that require in-process access to `RunManager`, Activity, and
the PTY: resultful injection, per-run command serialization, interrupt
settlement, watch subscriptions, coalescing, and watch delivery. It exposes no
public skin, grant policy, actor claims, audit policy, or conversation logic.

```text
MCP /mcp          REST /v1/controlplane/*
     \                  /
      ControlPlaneService, Python
       | grants, audit, timeline, authorization
       |
       | boot authenticated private RPC
       v
      @tm/controlplane-bridge, Node
       |                         |
       v                         v
  RunManager and PTY       Activity projections
       |
       v
  CaptureRpcClient -> prepare_captured_run -> seeded run home
```

This satisfies `CONTROLPLANE.md` principle 1 because both skins call one
service and contain no verb logic. The private bridge is an output adapter to
process resident capabilities, comparable to a database or PTY adapter.

### Required document amendments

1. Amend `docs/ARCHITECTURE.md::Two plane rule` with one explicit cross-plane
   application service exception. Control Plane policy lives in Python because
   its transaction boundary spans MCP auth, grants, audit, and normalized
   timeline reads. Process resident execution remains in the TypeScript product
   plane behind a private adapter.
2. Clarify `CONTROLPLANE.md::Architecture` and `::Watch` to name the private
   Gateway bridge. Python owns the verbs. Node owns subscription and PTY
   mechanics delegated by those verbs.
3. Clarify `CONTROLPLANE.md::Identity and entitlements` for Claude. The run local
   JSON MCP config lives under the materialized runtime home and is passed with
   `--mcp-config`. A project `.mcp.json` would mutate the worktree and can trigger
   project server approval. Codex continues to receive a run local
   `config.toml` entry.

The amendment keeps the approved service owner. It narrows the earlier product
plane rule and documents the live cross-process boundary already required by
the design.

## Contracts and ownership

### Python application service

New package, with each file below 700 lines:

| File and symbol | Ownership |
| --- | --- |
| `api/src/transport_matters/controlplane/service.py::ControlPlaneService` | The four verbs plus watch, authorization, fanout orchestration, and audit transaction ordering. |
| `controlplane/models.py::ControlPlanePrincipal` | Server constructed human or run principal, role, run id, and branded workspace id. |
| `controlplane/grants.py::ControlPlaneGrantStore` | Token digest lookup, create, delete, and startup cleanup over the shared Postgres pool. |
| `controlplane/audit.py::ControlPlaneAuditStore` | Pending action insert and completion update for one durable record shape. |
| `controlplane/conversation.py::project_conversation` | Text only filtering and caps over `session/timeline.py::project_timeline`. |
| `controlplane/gateway.py::GatewayControlPlanePort` | Typed private RPC client with error normalization. Extract shared HTTP mechanics from `api/v1/run_proxy.py::RunRouteProxy`; keep the public proxy unchanged. |
| `controlplane/auth.py::ControlPlaneTokenVerifier` | MCP SDK `TokenVerifier` implementation and bearer to principal resolution. |
| `controlplane/mcp.py::create_controlplane_mcp` | Tool registration only. Every tool delegates to `ControlPlaneService`. |
| `api/v1/controlplane_routes.py::router` | REST serialization only. Every route delegates to the same service. |

`ControlPlaneService` receives explicit ports for grants, audit, Gateway,
timeline reads, clock, token minting, and ids. Tool and route arguments never
carry an actor or workspace entitlement.

### Node execution bridge

New package `packages/controlplane-bridge`, exported only through its
`src/index.ts`:

| File and symbol | Ownership |
| --- | --- |
| `src/service/ControlPlaneRuntimeBridge.ts::ControlPlaneRuntimeBridge` | Per-run command queues, prompt mechanics, watch maps, damping, and delivery receipts. |
| `src/ports.ts::ActivitySignalPort` | Narrow Activity reads and subscriptions consumed by the bridge. |
| `src/adapters/activitySignals.ts::ActivitySignalsAdapter` | Adapts existing Activity projections and applied records. |
| `src/server/controlPlaneBridgeRouter.ts::createControlPlaneBridgeRouter` | Private typed RPC and boot token validation. |

`packages/gateway/src/main.ts::runGatewayProcess` constructs the bridge from the
existing `RunManager` created by `createDefaultRuntimeRouterDeps` and the
existing Activity dependencies from `resolveActivityDeps`.
`packages/gateway/src/app.ts::gatewayContexts` mounts its router through the
existing `ContextMount` injection seam under `/internal/controlplane`.

The bridge route is never forwarded by
`api/src/transport_matters/api/v1/run_proxy.py::RunRouteProxy`.

### Private bridge authentication

The bridge accepts one header, `X-TM-Control-Bridge`, containing a random boot
token. Python mints the token once per backend and compares it in Node with a
constant time comparison.

* Python supervised launch: extend
  `api/src/transport_matters/gateway_supervisor.py::GatewayPlan` and
  `plan_gateway_supervision` so the plan carries the token to the Gateway child
  and retains it for `GatewayControlPlanePort`.
* Electron launch: `desktop/src/main.ts::startBackendAndCreateWindow` mints once
  and threads it through `BackendLaunchOptions` and `GatewayLaunchOptions`.
  Keep minting and environment assembly outside `desktop/src/main.ts`, which is
  already 677 lines. `desktop/src/backendProcess.ts::buildBackendLaunch` and
  `desktop/src/gateway/gatewayProcess.ts::buildGatewayLaunch` receive the same
  explicit value.

Use a dedicated `TRANSPORT_MATTERS_GATEWAY_CONTROL_TOKEN` key. Explicitly remove
it in `launch_environment.py::build_launch_env`,
`build_managed_child_env`, `managed_child_shell_env_excludes`, and
`gateway/main.ts::stubHarnessClientSpec`. Tests inspect capture `launchEnv`,
both harness client environments, nested shells, stub mode, manifests, and
logs. This protects the private routes from local agent processes that can
reach loopback.

### Human operator authentication

Origin and Host checks defend browser routing but do not authenticate a human;
a local agent can forge both headers. Electron therefore mints a separate
operator capability. Its digest reaches Python, while the raw value reaches
the sandboxed preload once through a webContents-scoped IPC handler. The preload
exchanges it for an HttpOnly, SameSite operator session cookie, then discards
it. Renderer code never sees the raw capability. Browser development requires
an explicit developer operator token.

After Canvas cutover, remove public Runtime create and terminate routes.
Terminal attach requires a short-lived, single-use, run-scoped ticket minted by
authenticated Control Plane REST and validated by the Gateway terminal route.
Read-only Runtime list and get stay internal to Python or require operator auth.
This closes bearer, audit, and raw terminal bypasses through direct loopback.

## Tension 1: service placement

### Decision

Use placement (a). Python is the sole policy service. The Gateway is an
authenticated execution adapter.

### Rationale

1. Both skins already share the Python FastAPI origin. Mounting MCP there makes
   principle 1 literal.
2. Identity, grants, audit, and normalized transcript projection share the
   Python Postgres pool and transaction model.
3. Runtime and Activity authority remain in Node. The adapter calls the
   existing in-process owners and avoids a Python state machine or run registry.
4. A Gateway hosted service would need Python RPC for timeline and home
   materialization, then Python MCP would proxy every tool back to Node. That
   produces two application boundaries and weakens the single service rule.

### Exact reuse seams

* Composition: `packages/gateway/src/app.ts::buildGateway`, `gatewayContexts`.
* Sole run registry: `packages/runtime/src/service/RunManager.ts::RunManager`.
* Production instance: `packages/gateway/src/main.ts::createDefaultRuntimeRouterDeps`.
* Activity state: `packages/activity/src/projections/workspaceActivity.ts::WorkspaceActivityProjections`.
* Public Python proxy precedent: `api/v1/run_proxy.py::RunRouteProxy`.
* Timeline: `session/timeline.py::project_timeline`.
* Postgres: `session/pool.py`, `session/migrate.py::apply_migrations`.

Canvas launch and stop migrate to the Control Plane REST skin. The private
bridge becomes the only create and terminate caller. Terminal WebSocket attach
continues through `runTerminalConnection` and `RunRouteProxy` with the one-time
attach ticket above. Pre-release status makes removal preferable to a bypassing
compatibility path.

## Tension 2: authentication and grants

### Grant scope

Use authoritative UUID `SpaceId` as the security boundary. The existing
Activity `WorkspaceId` contains a 32 bit path hash, so it remains routing and
projection metadata. Grants store both `space_id` and `activity_workspace_id`.
Granted cwd launches must resolve a Space through
`capture_rpc_routes.py::_resolved_domain_request`; unresolved scope fails
closed. Target authorization compares `RuntimeRunView.spaceId` or the session
row's resolved Space. Activity reads begin only after that comparison.

### Tables

Use the single Alembic chain owned by
`api/src/transport_matters/session/migrate.py::apply_migrations`:

```text
0012_control_plane_grants
  run_id text primary key
  token_digest bytea unique not null
  role text check observer|director
  space_id uuid not null
  activity_workspace_id text not null
  created_at timestamptz not null

0013_control_plane_actions
  action_id uuid primary key
  dispatch_id uuid null
  actor_kind text not null
  actor_run_id text null
  space_id uuid not null
  activity_workspace_id text not null
  verb text not null
  targets jsonb not null
  request jsonb not null
  state text check pending|completed|unknown
  outcomes jsonb not null default '[]'
  created_at timestamptz not null
  completed_at timestamptz null
```

Index actions by `(space_id, created_at)`, `actor_run_id`, and
`dispatch_id`. Put migration tests in a new focused module because
`session/test_migrate.py` is already 693 lines. Grant and action SQL live in the
new Control Plane stores. They do not extend `session/dao_statements.py`,
`SessionWriter`, `SpaceStore`, transcript events, or override audit.

### Spawn transaction

1. The public Control Plane launch accepts `grant: none|observer|director`.
   Existing low level `POST /v1/runs` always uses `none`, preventing direct
   grant minting around the service.
2. `ControlPlaneService.launch` inserts a pending action row before any side
   effect, then calls the private bridge with a stable idempotency key and the
   nonsecret grant choice.
3. `RunManager.create` preserves its current idempotency and calls
   `CaptureRpcClient.prepareCapture`. Add the grant choice to the private
   `CreateManagedRunInput` and `CapturePort` request. Keep it out of
   `launchFields`.
4. `api/v1/capture_rpc_routes.py::PrepareCaptureRequest` validates the enum.
   `CaptureLeaseRegistry.prepare_capture` mints 32 random bytes before the
   synchronous prepare worker and passes a dedicated `ControlPlaneClientConfig`
   into `prepare_captured_run`.
5. `build_captured_run_context` materializes the overlay through
   `plan_runtime_home` and `prepare_runtime_home`. The config writer runs after
   materialization and before invocation construction.
6. After `prepare_captured_run` returns, the registry owns the lease. It uses
   authoritative resolved Space plus Activity identity, hashes the token with
   SHA-256, and persists before the spawn spec returns to Runtime.
7. Wrap the awaited insert and ownership transfer in explicit cancellation
   handling. A shielded rollback pops registry state, deletes any partial
   grant, closes the lease and run home, and records failure. This also covers
   `CaptureRpcClient` timeout cancellation.
8. Release pops registry state first, making auth fail immediately. An
   exception-safe cleanup always attempts lease close, grant delete, and exit
   lifecycle emission, aggregating errors so one failure cannot skip the other
   owners. Orphan grant cleanup remains a startup backstop.

`StubCaptureAdapter` rejects every granted launch. A granted launch requires
real capture and durable grant persistence.

### Run local MCP config

The raw token exists only in the materialized run home:

* Claude: write `transport-matters.mcp.json` under `runtime_home_dir` with an
  HTTP server entry and static `Authorization: Bearer <token>` header. Add its
  path through `captured_claude.py::build_claude_captured_invocation` using
  `--mcp-config`.
* Codex: extend `cli/codex_home.py::CodexSeeder` through a public seeder method
  to merge `[mcp_servers.transport_matters]`, `url`, and a static
  `http_headers = { Authorization = "Bearer <token>" }` into the run local
  `config.toml`.

Both writers reuse `home_io.py` and `atomic_io.py`, preserve unrelated config,
keep restrictive permissions, and leave the source home and worktree byte
unchanged. Current official clients support static headers for these remote
HTTP entries: [Claude Code MCP](https://docs.anthropic.com/en/docs/claude-code/mcp)
and [Codex configuration](https://developers.openai.com/codex/codex-manual.md).

### MCP SDK binding and instant revoke

Pin the stable SDK line, `mcp>=1.28,<2`. Construct `FastMCP` with:

* `token_verifier=ControlPlaneTokenVerifier(grants, capture_registry)`
* `AuthSettings(required_scopes=["controlplane"], ...)`
* `streamable_http_path="/"`

`verify_token` hashes the bearer, performs a fresh Postgres lookup, confirms
the capture lease and authoritative Gateway `RunManager` run are both live, and returns an SDK
`AccessToken` with `client_id=run_id`, `subject=run_id`, generic
`controlplane` scope, role scope, `space_id`, and `activity_workspace_id` claims. It returns the
digest in the SDK token field so the raw secret does not move beyond the auth
middleware.

MCP tools read `get_access_token()` from the SDK auth context and construct the
principal from verified fields. Every request rechecks the row. There is no
grant cache. Explicit revoke deletes the row, so the next HTTP request fails.
Run release or Gateway loss fails the next request immediately. Supervised
Gateway exit also closes affected capture leases and grants instead of only
logging. Startup deletes remaining orphans.

The official stable SDK exposes `TokenVerifier`, `AccessToken`,
`AuthSettings`, and `get_access_token()` for this binding:
[MCP Python SDK v1.x](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x).

### Mount order

`api/src/transport_matters/main.py::create_app` mounts the MCP ASGI app at
`/mcp` before `mount_frontend_bundles(app)`. Setting the inner Streamable HTTP
path to `/` prevents `/mcp/mcp`. The explicit mount precedes the `/` SPA
catch-all, matching Starlette registration order.

`main.py::lifespan` enters the MCP session manager context after migrations,
the Postgres pool, capture registry, grant store, audit store, and service are
ready. Mounted subapplication lifespan behavior is not assumed.

REST creates `HumanPrincipal` only after operator capability verification. MCP
creates a run principal through the verifier. Service methods accept only
principals.

## Summary observe primitive

Include in v1 as `conversation(run_id, shape="summary")`; it gives a cheap single run read without another verb or projection.
Reuse `controlplane/conversation.py::project_conversation`: after its `MessageItem`, genuine user or assistant, and injected content filters,
select the first genuine user turn plus the last four messages regardless of role, deduplicate overlap, then apply existing per message and total hard caps,
tail truncation, and `truncated`. The initial prompt is the first user turn after stripping injected content.

## Tension 3: watch

### Placement

Subscriptions and damping live in
`packages/controlplane-bridge/src/service/ControlPlaneRuntimeBridge.ts` beside
the live `RunManager` reference. Python authorizes and audits `watch` and
`unwatch`, then registers the resolved subscription through the private port.

One refcounted Activity subscription exists per `(owner, workspace_id)`. Each
watcher record contains watcher run id, target workspace or run id, event mask,
last flush time, coalescing buffer, and timer. All state is process resident and
dies with the Gateway.

### Signal sources

Reuse Activity as the sole state interpreter:

* `state_changed`: edge from
  `WorkspaceActivityProjections.subscribeWorkspaceActivity` when `status`
  changes.
* `needs_you`: false to true edge on `needsYou`, covering both asked and gated.
* `turn_completed`: applied `ActivityRecord.kind == "turn-end"` from
  `ActivityIngestion.reconcile` after `activityRecordToEvent` is sent to the
  run actor.

Add one narrow Activity output,
`ActivityIngestion.subscribeAppliedRecord`, rather than parsing Postgres twice.
Add `completedTurns` to `RunActivityContext`, incremented only when
`eventStream(event) == "record"` for a new assistant turn end. Current main
reserves `needs-you-gated` without deriving it, so S5 depends on the upstream
agent-state gate fact and reduction. No PTY heuristic may synthesize gated.

Registration reuses `activityRouter.ts::createActivityRouter` ordering:
subscribe first, buffer, await settled snapshot materialization, record per-run
cursors, install the watcher, then release only buffered facts newer than the
baseline. Historical replay and intermediate catch-up states cannot wake a new
watcher.

### Cross-process event path

The hot path stays entirely in Node:

```text
Postgres NOTIFY tm_events
  -> TmEventsActivityListener
  -> ActivityIngestion reconcile
  -> WorkspaceActivityProjections or applied record signal
  -> ControlPlaneRuntimeBridge coalescer
  -> RunManager resultful PTY injection
  -> watcher harness
```

Python participates only when a caller registers or removes a watch. This
avoids a Gateway to Python to Gateway loop for every event.

### Damping and envelope

Use a three second minimum interval per watcher. The buffer is keyed by event
kind and target run id, retaining the latest fact. A flush orders facts by
first observation and emits one line:

```text
[tm watch] researcher (a1b2) finished turn 14; builder (c3d4) -> needs_you
```

The line contains references only. It ends with carriage return so the harness
receives a queued prompt. Delivery uses the same resultful PTY action as prompt
in nudge mode. A missing or ended watcher removes its subscription.

The envelope grammar is defined once in the Control Plane contract and mirrored
in Python and TypeScript with the existing `test_type_mirrors.py` pattern.
Registration and removal are durable audited actions. Coalesced notification
delivery is operational output of the subscription rather than a new caller
action.

## Tension 4: prompt receipt

### Resultful PTY contract

Keep `RunManager.write` for best effort terminal WebSocket input. Add a separate
`RunManager.inject` used only by the private bridge:

```text
inject(runId, bytes) -> delivered | failed(reason)
```

Change the lower port to `PtySession.tryWrite(data): boolean`.
`NodePtySession.tryWrite` owns the disposed or exited check, native write, and
terminal-gone handling as one operation. `RunManager.write` ignores the result
for terminal compatibility; `inject` returns it. It never attaches a viewer or touches
scrollback or fanout backpressure.

`delivered` has a precise meaning: the bridge found a live target, serialized
the action behind earlier injections for that run, completed interrupt
settlement when requested, and `PtySession.tryWrite` accepted
the complete prompt plus Enter. It does not claim that the model accepted or
answered the prompt. This is the strongest truthful receipt available from a
PTY.

Failure reasons are `run_not_found`, `run_ended`, `interrupt_timeout`, and
`write_failed`. Python maps Gateway absence to `busy_gateway` and returns one
receipt per unique target in caller order. Partial failure never raises the
whole fanout.

### Envelope and fanout

`ControlPlaneService.prompt` creates one `dispatch_id`, inserts one pending
audit row, renders one sender prefix, and calls the bridge once with all
targets. The prefix is sanitized to one line:

```text
[tm from a1b2 «Director»]
```

The bridge runs targets concurrently and serializes commands per target.
Prompt encoding normalizes CRLF, rejects NUL, ESC, DEL, and unsupported C0
bytes, then uses harness-proven bracketed paste around prefix plus newline plus
text, followed by one carriage return. A harness without verified multiline
paste support fails before writing. The service completes the audit row with every receipt. A failed
completion update leaves the already durable row in `pending`; startup recovery
marks old pending rows `unknown` instead of inventing outcomes.

### Nudge and interrupt mechanics

* `nudge`: write the complete prompt immediately. Busy harnesses queue it for
  the next turn.
* `interrupt`: first await a settled Activity snapshot and capture its revision.
  Idle targets skip the break. Active or needs-you targets receive `ESC`
  (`0x1b`). The bridge accepts only a turn end or idle fact whose causal
  revision is newer than the pre-ESC fence, up to two seconds. A timeout leaves
  the prompt unwritten.
* `manage.interrupt`: the same path ends after the settled `ESC`; it writes no
  prompt.

Both supported harness policies use `ESC`. Keep the mapping keyed by
`RuntimeHarness` and prove it with real Claude Code and Codex PTY integration
tests. Avoid `SIGINT` and Ctrl+C because those can terminate the Codex process
instead of only the active turn.

Event based settlement replaces a blind sleep. The two second value is a safety
bound, not a fixed delay. A confirmed transition releases immediately.

## Tension 5: launch to Canvas pane

Capture RPC emits `RUN_STARTED` before Runtime registration, so the Activity
frame is a trigger rather than proof that `getRun` can already succeed. Canvas
already consumes that stream; reconciliation must tolerate this ordering.

### Decision

Extend `capturedRunStore` reconciliation from prune only to adopt and prune.

1. `ControlPlaneService.launch` calls the private bridge, which reuses
   `RunManager.create` and returns a `RunView`. Add optional `name`, canonical
   `workspaceId`, `launchKind`, and `launchIntentId` to the view. Capture returns
   the first two from authoritative preparation; Runtime records the idempotency
   key as launch intent.
2. The launch response completes after RunManager registration. The existing
   lifecycle emission causes a workspace Activity frame with
   `launch_kind=canvas`.
3. `SessionCanvasRoute` treats a new canvas Activity run id as a trigger and
   retries `getRun(runId)` with a bounded backoff until registration is visible.
4. Add `capturedRunStore.adoptRun(view)`. It checks mappings by `runId` and
   `launchIntentId`. Local pending intents suppress adoption until their create
   response records the original run key. Otherwise it creates
   a deterministic adoption key `${harness}:${runId}` when absent, and stores
   `{provider, runId}` before creating a pane.
5. Add `CanvasStoreActions.adoptCapturedRun`. Refactor
   `model/spawn.ts::createCapturedRunRef` to accept an injected run key and
   reuse `spawnPane`, label counters, pane records, layout, focus, and dock
   behavior. The new pane's `ensureRun` sees the adopted mapping and attaches to
   the existing run without a second POST.
6. Initial route mount paginates all Run views and adopts only matching
   `workspaceId` plus `launchKind == "canvas"`, then prunes stale mappings.
   Live triggers use the same coalesced, intent-aware path.

This works for an active browser and heals reloads. Browser local layout stays
browser local. The server publishes run identity and intent; the browser owns
where the pane is placed.

## Audit ordering and errors

Every public operation follows one ordering:

1. Resolve the server-owned principal.
2. Authorize role, target, and canonical workspace.
3. Insert a pending action row. Failure stops the operation.
4. Perform the read or side effect.
5. Complete the row with ordered outcomes.

Observe actions may store request and bounded response metrics rather than full
conversation content. Prompt stores the approved text field. Launch stores the
resolved workdir, harness, name, grant choice, and resulting run id.

Domain errors are `not_found`, `forbidden`, `busy_gateway`, and
`delivery_failed`. MCP returns a structured normal tool result with an error
code so agents can branch without parsing a stack trace. REST maps the same
domain result to HTTP while preserving the code. Skin modules contain only
conversion.

## Refined seven slice plan

The seven slices retain their count. The read-only bridge foundation moves to
S2, prompt precedes watch, and Canvas adoption ships with launch.

### Precondition, documentation gate

Amend `CONTROLPLANE.md` and `docs/ARCHITECTURE.md` together with the placement,
Claude config, workspace scope, and private bridge decisions above. This gate
precedes implementation and is not an eighth code slice.

### S1: identity, grants, and seeded MCP config

* Migration `0012_control_plane_grants` and dedicated store.
* Stable MCP SDK dependency pin.
* Token verifier with active lease and authoritative Runtime liveness checks.
* Operator capability contract and removal plan for public Runtime mutations.
* Dedicated grant choice across private create, CapturePort, capture RPC, and
  `prepare_captured_run`.
* Claude run local `--mcp-config` and Codex `config.toml` static headers.
* Release revoke, explicit revoke, startup orphan cleanup, and closed Stub
  behavior.

Gate: both harness configs parse, source homes and worktree remain byte
unchanged, persistence failure closes the lease before PTY spawn, and delete
revokes the next request.

### S2: service core, observe, and audit

* `ControlPlaneService`, principals, ports, and error vocabulary.
* Migration `0013_control_plane_actions` and pending to completed audit flow.
* `conversation` projects each run session separately through `project_timeline`
  with cumulative `turn_index_offset`, then merges sessions in stable order.
  This preserves cursor continuity when a harness rotates session and seq.
* New run-scoped DAO query for events and last turn time.
* Roster and summary join the private Gateway Runtime and Activity snapshot with
  session data. Activity remains the only state derivation.
* Read-only `@tm/controlplane-bridge`, private router, boot auth, Gateway
  composition, and secret stripping land here so the production port exists.

Gate: Claude and Codex timeline fixtures produce the same text contract;
forbidden workspace targets never reach a port; audit failure blocks effects.

### S3: twin skins

* Thin REST under `/v1/controlplane`.
* FastMCP Streamable HTTP mounted at `/mcp` before the SPA catch-all.
* SDK verifier binding, lifespan session manager, and structured tool results.
* Observe tools only. Later slices register each action tool with its real port.

Gate: contract tests prove both skins call the same fake service, `/mcp` is not
swallowed by the SPA, and revoked tokens fail on the next request.

### S4: private bridge, resultful prompt, and manage

* Extend the S2 bridge with action contracts.
* `PtySession.tryWrite`, `RunManager.inject`, per-run queues, prompt fanout, causal ESC
  settlement, `stop`, and break only `interrupt`.
* Remove public Runtime create and terminate; add authenticated attach tickets.

Gate: missing, ended, throwing, concurrent, partial fanout, idle interrupt, and
timeout cases produce exact receipts. Packaged Gateway bundle includes the new
package and native PTY prebuild proof remains green.

### S5: watch

* Gated agent-state prerequisite, Activity applied-record output, deterministic
  completed turn count, replay baseline, and causal revisions.
* Refcounted workspace subscriptions, run target filters, three second
  coalescing, and shared envelope contract.
* Resultful PTY nudge delivery and watcher cleanup.

Gate: five simultaneous completions produce one line, state and needs-you edges
dedupe, content never rides push, timers die at shutdown, and Gateway restart
clears every subscription.

### S6: launch and Canvas adoption

* Service launch through private `RunManager.create`, with stable idempotency.
* Process resident name, workspace, launch kind, and launch intent.
* Canvas launch and stop migrate to the Control Plane REST client beside
  `www/packages/core/src/transport.ts`.
* Intent-aware adopt and prune reconciliation, bounded registration retry, and
  paginated reload adoption in `capturedRunStore` and `SessionCanvasRoute`.

Gate: an agent launch opens one pane in an active browser, reload re-adopts it,
the Activity echo does not duplicate a UI launch, and close stops the adopted
run through the audited REST verb.

### S7: end to end and packaged proof

* Real loop: spawn director grant, call summary, launch observer, browser adopts
  pane, prompt peer, receive watch nudge, inspect conversation, verify receipt
  and audit, revoke, then prove denial.
* Error taxonomy, pending audit recovery, Gateway outage, restart, and cleanup.
* Source tests, Python package tests, Gateway bundle tests, wheel contents, and
  desktop launch coverage.

Gate: focused tests, then observed `just check` and `just test` exit zero.

## Hygiene constraints

* Reuse `RunManager`, `prepare_captured_run`, `project_timeline`, home seeders,
  Activity projections, the shared Postgres pool, and Alembic.
* Keep `session/test_migrate.py` at 693 lines by adding a focused test file.
* Keep audit and grant SQL out of `session/dao_statements.py` at 600 lines and
  `session/writer.py` at 644 lines.
* Keep Control Plane persistence out of `SpaceStore` at 627 lines.
* Keep new modules below 700 lines and functions near 150 lines.
* `desktop/src/main.ts` is 677 lines. Thread boot auth through extracted launch
  configuration rather than extending this composition file materially.
* Add subprocess import tests for the new neutral Python package.
* Add package boundary tests for `@tm/controlplane-bridge`; consumers import
  only its index.
* Mirror every cross-language literal and DTO with the existing contract test
  pattern.

## Defect pressure test

Only findings at confidence 80 or above survive:

| Confidence | Failure if omitted | Design control |
| --- | --- | --- |
| 100 | Two application services drift across REST and MCP. | Both skins invoke the sole Python `ControlPlaneService`; Node is a private output adapter. |
| 100 | Local agents forge human or Gateway authority. | Separate operator and bridge capabilities, removed public mutations, attach tickets, constant time validation. |
| 100 | A 32 bit Activity hash becomes a security principal. | UUID Space is the authorization boundary; Activity id is routing metadata. |
| 100 | Granted harness starts with an unresolvable token. | Grant persists while Python owns the prepared lease and before the spawn spec returns. Failure closes the lease. |
| 100 | Cancellation or cleanup strands lease, grant, or home. | Shielded prepare rollback and exception-safe aggregate release attempt every owner. |
| 100 | Revoke leaves a dead actor token usable. | Fresh grant, capture, and Runtime liveness checks on every request, no cache. |
| 100 | PTY reports success after exit or splits prompt text. | Resultful `tryWrite`, per-run queues, control filtering, and harness-proven multiline paste. |
| 100 | Replay wakes watchers or settles an interrupt. | Settled baselines, signal cursors, and a post-ESC causal fence. |
| 100 | Gated approval waits never reach `needs_you`. | S5 requires the reserved gated agent-state fact before watch ships. |
| 100 | Python reimplements Activity status. | Roster and watch consume the existing Activity projection and applied record output. |
| 100 | Launch trigger races registration or duplicates a pending UI launch. | Bounded get retry, launch intent correlation, workspace and launch kind filtering. |
| 100 | Side effect occurs without an audit record. | Pending insert is the admission gate; completion enriches the durable row. |
| 100 | SPA catch-all serves HTML at `/mcp`. | Mount MCP before `mount_frontend_bundles`, with inner path `/`. |
| 100 | Secret leaks through launch metadata or source homes. | Raw token exists only in the run local MCP config; dedicated carrier, atomic merge, byte preservation tests. |

## Verification matrix

Focused proof required before repository gates:

| Area | Proof |
| --- | --- |
| Grants | Mint, digest lookup, active lease, explicit revoke, release revoke, restart cleanup, persistence rollback. |
| Homes | Claude JSON and Codex TOML parse, static header present, restrictive mode, source home and worktree unchanged. |
| MCP | TokenVerifier called per request, role and scope principal, mount path, session manager lifecycle, revoked live session denied. |
| Observe | Both harness timelines, tool and system stripping, cursor, per-message cap, total cap, roster state from Activity. |
| Prompt | Real PTY nudge for both harnesses, ESC interrupt for both, Activity settlement, timeout, ordered partial receipts, per-run serialization. |
| Watch | State edge, needs-you edge, turn completion count, target filters, three second damping, five-event coalescing, watcher exit cleanup. |
| Canvas | Live adoption, reload adoption, no duplicate UI echo, stale prune, close and dock behavior. |
| Audit | Admission failure, pending recovery, fanout outcome ordering, dispatch indexes, human and MCP actor shapes. |
| Packaging | Gateway bundle, wheel contents, desktop dual launch secret, supervised launch secret, no secret logging. |

Final gates are `just check` and `just test`, with their real summaries and exit
codes observed before completion.
