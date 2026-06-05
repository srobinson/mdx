---
title: Control Plane Scout A, action and identity reuse map
type: projects
tags: [transport-matters, control-plane, scout, action, identity, reuse]
summary: Current action ownership is the TypeScript Runtime in the Node Gateway. Python owns capture preparation, home materialization, and Postgres. No run scoped bearer, grant resolver, MCP home entry, prompt envelope, or control_plane_actions persistence exists. The approved Python service placement conflicts with the checked in product plane architecture and must be resolved before build.
status: active
source: read only scout on main 0d88c1081f104cbd3adca771061772be256eb874
confidence: high
created: 2026-07-11
---

# Control Plane Scout A: action and identity

Evidence was read from pristine `main` at
`0d88c1081f104cbd3adca771061772be256eb874`. `git status --short` was empty
before inspection and after this report. `CONTROLPLANE.md` is approved design
and remains unimplemented.

## Reuse Map

### Launch, manage, attach, and PTY delivery

| # | Existing anchor | Current contract | Reuse direction |
| --- | --- | --- | --- |
| 1 | `packages/gateway/src/app.ts::buildGateway`, `gatewayContexts`, `ContextMount` | Gateway is a composition root. Context router factories are its complete mount contract. | Mount a control plane context through the same injected router pattern. Keep domain policy out of Gateway. |
| 2 | `packages/gateway/src/main.ts::runGatewayProcess`, `createDefaultRuntimeRouterDeps`, `closeGatewayResources` | Production creates one `RunManager`, one `NodePtyAdapter`, and one `CaptureRpcClient`, then closes Runtime before Activity. | Inject the existing manager into action services. Preserve shutdown ordering. Never create a second manager. |
| 3 | `api/src/transport_matters/api/v1/run_proxy.py::RunRouteProxy`, `create_run_proxy_mount` | Python front door forwards the run HTTP routes and terminal WebSocket to Gateway. `app.state` holds `run_proxy_mount`, not `RunManager`. | If action orchestration stays Python, extract or add a typed Gateway client rather than calling a Python run manager or attaching a terminal viewer. |
| 4 | `packages/runtime/src/service/RunManager.ts::RunManager` | Full public API is `create`, `getView`, `list`, `attach`, `detach`, `write`, `resize`, `terminate`, and `close`. Internal ownership is process resident and owner scoped. | Reuse `create`, reads, attach lifecycle, and `terminate`. Add a resultful action seam for prompt and break operations. |
| 5 | `packages/runtime/src/service/RunManager.ts::create`, `createNew`, `register` | Create preserves owner plus idempotency single flight, calls capture preparation, spawns the PTY, rolls capture back on failure, and makes capture returned identity authoritative. | Control plane launch must flow through this path with one stable idempotency key per launch intent. |
| 6 | `packages/runtime/src/server/runtimeRouter.ts::createRuntimeRouter` | Current routes are `POST /v1/runs`, `GET /v1/runs`, `GET /v1/runs/:runId`, `POST /v1/runs/:runId/terminate`, and `WS /v1/runs/:runId/terminal`. | Preserve these low level runtime adapters. New human and agent verbs should share one service above them or migrate the canvas to the new REST skin. |
| 7 | `packages/runtime/src/server/runTerminalConnection.ts::handleRunTerminalConnection` | Attach creates a viewer, replays scrollback, pumps output, sends binary input to `RunManager.write`, and reserves text frames for resize control. | Reuse its terminal protocol for viewers only. Prompt RPC must avoid attachment, replay, and viewer backpressure. |
| 8 | `packages/runtime/src/ports.ts::PtySession`, `PtyPort`; `packages/runtime/src/adapters/NodePtyAdapter.ts::NodePtySession.write` | `RunManager.write` reaches `PtySession.write`, which converts bytes to a `Buffer` and calls `node-pty` process write. | The new action method should end at this same PTY session. No alternate PTY implementation is needed. |
| 9 | `www/packages/core/src/transport.ts::createCapturedRun`, `listRuns`, `getRun`, `terminateRun` | Canvas REST clients already cover create, list, lookup, and terminate. | Put new REST clients beside these functions and wire DTOs through a new `@tm/contract` subpath. Canvas must not import server packages. |
| 10 | `www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts::runTerminalSocketUrl`, `openTerminalSocket` | xterm input is encoded to binary WebSocket frames. The Python proxy forwards those bytes to Gateway, then Runtime writes them to the PTY. | Keep this path for interactive human input and attach. Do not reuse it as the agent prompt command channel. |

Current byte path:

`xterm onData` -> `openTerminalSocket` binary frame ->
`RunRouteProxy._downstream_to_upstream` ->
`handleRunTerminalConnection` -> `RunManager.write` ->
`NodePtySession.write` -> `node-pty`.

### Capture preparation, identity, and home seeding

| # | Existing anchor | Current contract | Reuse direction |
| --- | --- | --- | --- |
| 11 | `packages/runtime/src/adapters/CaptureRpcClient.ts::CaptureRpcClient` | Runtime calls Python at `/v1/capture/prepare`, `/{runId}/release`, and `/{runId}/health`. | Thread a typed, nonsecret grant choice through this port. Keep bearer material out of the TypeScript request and response when Python can mint it. |
| 12 | `api/src/transport_matters/api/v1/capture_rpc_routes.py::PrepareCaptureRequest`, `prepare_capture`, `_resolved_domain_request` | Python resolves worktree, runtime template, continuation fields, and authoritative space or worktree identity before preparation. | This is the server validation boundary for grant enabled launch. Mint from resolved facts, not caller claims. |
| 13 | `api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry.prepare_capture`, `release_capture`, `close` | Preparation is cancellation hardened, registers a lease once, emits lifecycle once, and releases once. | Grant creation and revocation must join this rollback discipline without making `CapturedRunLease.close` async. |
| 14 | `api/src/transport_matters/captured_run.py::prepare_captured_run`; `api/src/transport_matters/captured_run_models.py::CapturedRunSpawnSpec`, `CapturedRunLease` | The shared capture seam returns one spawn spec and one idempotent lease. The lease owns proxy children, manifest, workspace lock, and runtime home cleanup. | Launch must continue through this seam. A grant enabled launch should fail and release the lease if grant persistence cannot complete before the spawn spec reaches Runtime. |
| 15 | `api/src/transport_matters/captured_run_context.py::build_captured_run_context` | `prepare_launch` mints the run id, then a per run home is materialized before provider invocation is built. The overlay is attached to the lease resource stack. | Inject MCP configuration after overlay materialization and before invocation construction. Never mutate the operator source home. |
| 16 | `api/src/transport_matters/cli/runtime_home.py::plan_runtime_home`, `prepare_runtime_home`, `seed_direct_home_if_needed` | One facade handles native, manual, template, proxy only, and overlay modes for both harnesses. | Extend this public seam with a dedicated control plane client config input. Avoid parallel home preparation. |
| 17 | `api/src/transport_matters/cli/home_seeders.py::HarnessSeeder`, `seed_home_dir`; `claude_home.py::ClaudeSeeder`; `codex_home.py::CodexSeeder`; `home_io.py`, `atomic_io.py` | Claude JSON and Codex TOML are merged non destructively with atomic, restrictive writes. The atomic writer replaces an overlay symlink rather than writing through it, so merged config becomes run local while source content stays unchanged. Codex TOML helpers are private. | Add public harness specific MCP config writers behind the shared seeder facade. Reuse the atomic merge writer. Preserve unrelated config, permissions, auth, hooks, trust, and source home bytes. |
| 18 | `api/src/transport_matters/cli/launch_runtime.py::new_run_id`; `packages/runtime/src/service/RunManager.ts::register`; `api/src/transport_matters/run_lifecycle.py::build_run_lifecycle_event` | Python mints a UUID run id. Capture returned `spaceId`, `worktreeId`, and session identity win in Runtime. Lifecycle separately derives Activity `WorkspaceId` as `slug/hash`. | Reuse the run id as actor identity. Decide whether grants scope to Activity `WorkspaceId` or UUID `SpaceId` before defining schema. |

Current identity status: **none** for the approved bearer and entitlement model.
TM mints a run UUID and managed harness session ids, but no run scoped bearer,
token digest, grant record, or request principal exists.

Current home status: the per run home and merge machinery exist. No `.mcp.json`
writer, MCP server entry, Codex `mcp_servers` writer, or Authorization header
injection exists.

### Audit and persistence

| # | Existing anchor | Current contract | Reuse direction |
| --- | --- | --- | --- |
| 19 | `api/src/transport_matters/session/migrate.py::apply_migrations`, `migration_head`; `api/migrations/versions/0011_run_live_status_asked.py` | Alembic is the single schema owner, guarded by a Postgres advisory lock. Revisions are sequential, raw DDL lives under `api/migrations/versions`, and runtime auto migrates. | Add the next revision for grants and `control_plane_actions`. Never create either table lazily from MCP startup. |
| 20 | `api/src/transport_matters/session/dao_statements.py`; `session/async_dao.py::AsyncSessionDao`; `space/store.py::SpaceStore`; `session/writer.py::SessionWriter`; `override_audit.py::OverrideAudit` | Session SQL is centralized, Space owns its own store, lifecycle persistence uses typed contracts plus append rows, and override audit is an in memory request audit rather than an action log. No existing durable action audit matches the spec. | Reuse the pool, transaction, JSONB, row model, and migration conventions. Persistence ownership depends on the service placement decision: a new context adapter if product plane, or dedicated control plane store if Python. Do not overload transcript events, lifecycle rows, `SpaceStore`, or override audit. |

Searches proving absent surfaces, all returned no matches:

```text
rg -n --glob '*.py' --glob '*.ts' --glob '*.tsx' \
  'control_plane_actions|control_plane_grants|run.scoped bearer|run_scoped bearer' \
  api/src packages www desktop

rg -n --glob '*.py' --glob '*.ts' --glob '*.tsx' \
  'mcpServers|mcp_servers|\.mcp\.json' api/src packages www desktop

rg -n --glob '*.py' --glob '*.ts' --glob '*.tsx' \
  'dispatch_id|\[tm from|\[tm watch\]|mode: nudge|mode: interrupt' \
  api/src packages www desktop

rg -n --glob '*.py' --glob '*.ts' --glob '*.tsx' \
  'token_urlsafe|secrets\.token|HTTPBearer|OAuth2PasswordBearer' \
  api/src packages www desktop
```

Prompt status: **none** for semantic nudge, interrupt, settle, sender envelope,
dispatch, or per target receipt. The only current input primitive is raw PTY
write. `RunManager.terminate` kills the process and releases capture, so it is
not the approved interrupt operation.

## Quality Map

| Severity | Confidence | Finding | Required response |
| --- | --- | --- | --- |
| P1 | 100 | Service placement is contradictory. `CONTROLPLANE.md` assigns the new domain and MCP app to Python. `docs/ARCHITECTURE.md` says new Comms and orchestration contexts live in TypeScript and do not extend Python. Live action ownership already follows the latter. | Resolve the documents before build. Preferred shape is a product plane context injected with Runtime and Activity ports, with Python retaining capture, home, and Postgres responsibilities. If Python remains the service owner, define a typed Gateway action client and formally amend the architecture. |
| P1 | 100 | `runtimeRouter.ownerFromQuery` accepts caller supplied owner, and `RunManager.lookup` authorizes by matching that string. | Treat owner as a compatibility partition only. Resolve bearer to actor, owner, and grant scope before service entry. Tool arguments never establish identity. |
| P1 | 100 | `RunManager.write` returns `void` and deliberately drops missing, ended, wrong owner, or empty writes. The terminal WebSocket also creates viewer state. | Add a separate resultful, owner scoped Runtime action operation. It must own envelope construction, harness break bytes, settle timing, write, and delivery outcome. |
| P1 | 100 | No typed grant path crosses create, capture RPC, captured request, and runtime home. Generic `launchFields` enters environment, shared proxy bindings, and `SessionBinding`. | Add a dedicated non metadata carrier. Keep the raw bearer only in the per run home. Persist a digest or lookup key. Fail granted launch closed when capture RPC is unavailable. |
| P1 | 100 | Grant scope identity is ambiguous. Runtime uses UUID `spaceId` and `worktreeId`; Activity `WorkspaceId` is a `slug/hash` pair; the design says `workspace_id`. | Choose the aggregate and field name before migration. Do not infer equivalence. |
| P1 | 100 | Launch with a grant must be atomic across capture preparation, home injection, grant persistence, PTY spawn, and rollback. Current seams have no pre spawn async grant hook. | Mint the token before home injection, persist the token binding after capture returns authoritative facts and before Runtime receives the spawn spec, then release capture if persistence fails. Revoke on run release or explicit revocation. |
| P1 | 100 | Server launch cannot currently make a pane appear on Canvas. Pane identity and run mapping are browser local in `capturedRunStore`, keyed by `runKey`; reconciliation only prunes stale local mappings. | Define a server to Canvas adoption, reconciliation, or persisted layout event. A `RunManager` entry alone satisfies launch but not pane creation. |
| P2 | 100 | Persistence placement can violate either design. `AsyncSessionDao` is the transcript store boundary, while `CONTROLPLANE.md` currently declares a Python domain and `docs/ARCHITECTURE.md` declares a product context. | Bind DAO placement to the service placement decision. Keep action SQL with its owning context while reusing the one Alembic and Postgres substrate. |
| P2 | 100 | Several nearby files are near the hard 700 line threshold: `session/test_migrate.py` 693, `space/store.py` 627, `session/writer.py` 644, `session/dao_statements.py` 600, `RunManager.ts` 538, `home_overlay.py` 532. | Do not extend `test_migrate.py` or `SpaceStore`. Put migration proof in a new focused test module. Prefer a control plane persistence adapter over inflating unrelated owners. Keep new files under 700 lines and functions under about 150. |

Additional constraints from history and comments:

- PR #242, commit `915860f`, deliberately deleted Python `run_manager.py`,
  `run_routes.py`, `run_terminal.py`, and related paths. Do not restore them.
- PR #245, commit `7241fff`, made plain terminals identity free, socket scoped
  shells. They are not action targets.
- PR #246, commit `81cca42`, established owner scoped create idempotency and
  lineage metadata in `launchFields`.
- PRs #247 and #249 made the embedded Gateway bundle part of product proof.
  Any Gateway action adapter needs source tests and packaged wheel coverage.
- `CaptureLeaseRegistry` and `CapturedRunLease` have exact cancellation,
  registration, and release ordering. Grant lifecycle must preserve it.
- Home writers must merge and write atomically. Cross module imports of private
  Codex TOML helpers violate `api/CLAUDE.md`.

## Plan

### Decisions needed before implementation

1. **Service owner.** Reconcile approved Python placement with the product plane
   rule. Recommended: `@tm/controlplane` owns action orchestration and is mounted
   by Gateway; Python exposes capture, home seed, grant persistence, and recall
   ports. Alternate: retain Python service and add a typed private Gateway
   action adapter. Either choice keeps one `RunManager`.
2. **Grant scope.** Choose Activity `WorkspaceId` (`slug/hash`) or UUID
   `SpaceId`. Use the same identifier in token resolution, every entitlement
   query, activity reads, launch, and audit.
3. **Token storage.** Store a one way digest or lookup key with `run_id`, role,
   owner, and chosen scope. Keep the raw bearer only in the seeded per run home.
   Deletion revokes immediately.
4. **Prompt interrupt policy.** Capture real Claude and Codex PTY behavior and
   lock break bytes plus settle timing per harness. No implementation currently
   defines Codex or Claude control plane interrupt behavior.
5. **First prompt semantics.** Decide whether launch sends `first_prompt` through
   the resultful PTY action after readiness or adds a harness argv field. Current
   create and capture contracts carry neither.
6. **Launch identity input.** Decide whether the public verb uses Activity
   `WorkspaceId` derived from canonical workdir or resolves workdir to Space or
   Worktree at capture RPC. The chosen grant scope must be authoritative before
   token minting.
7. **Canvas appearance.** Define how a server launched run creates or reconciles
   the browser local `runKey` and pane record. Existing run creation has no path
   into `capturedRunStore`.
8. **Audit durability.** Decide whether action persistence failure blocks the
   side effect. The principle that every action is persisted favors fail closed
   before dispatch, then one completed row after fan out outcomes are collected.
9. **REST cutover.** Decide whether existing canvas `/v1/runs` calls become
   low level Runtime only and canvas launch or stop migrates to the new REST
   verbs so human actions receive the same entitlement and audit treatment.

### Build steps bound to the reuse map

1. Resolve decisions 1 and 2, then update `CONTROLPLANE.md` and
   `docs/ARCHITECTURE.md` together.
2. Create the one control plane service with explicit ports for Runtime actions,
   Activity reads, normalized conversation reads, grant lookup, action audit,
   clock, token minting, and id generation. Mount through anchor 1.
3. Add a Runtime action method beside anchor 4. It returns a typed outcome,
   preserves owner hiding, distinguishes interrupt from terminate, and writes
   through anchor 8. Add a narrow Gateway adapter only if the service is
   outside the Gateway process.
4. Thread the nonsecret grant choice through anchors 5, 11, and 12. Python mints
   the bearer, injects its MCP entry through anchors 15 through 17, persists the
   hashed binding before returning the spawn spec, and releases anchor 14 on
   failure. Granted launch rejects `StubCaptureAdapter`. Prove the source home
   remains byte unchanged.
5. Add the next Alembic revision through anchor 19 for grant lookup and
   `control_plane_actions`. Put typed storage with the decided service owner,
   reusing transactions and JSONB from anchor 20. Add a new focused migration
   test file so `session/test_migrate.py` stays below the threshold.
6. Implement one authorization boundary: bearer -> run id -> active grant ->
   owner and scope principal. MCP resolves it before tool dispatch. REST injects
   an explicit human principal. Service methods accept principals, never actor
   claims.
7. Implement prompt fan out over the resultful Runtime action. Add the sender
   envelope once in the service, one `dispatch_id` per call, stable target
   ordering, partial receipts, and one append only action record.
8. Implement launch and manage over anchors 5 and 6. Reuse existing idempotency,
   capture rollback, terminate, and structured Gateway failure mapping. Resolve
   workdir into the chosen authoritative grant identity and emit the Canvas
   reconciliation event.
9. Add thin REST and MCP adapters. Add Canvas clients beside anchor 9 and keep
   Canvas behind contract DTOs. Never import Runtime or service internals into
   the browser.
10. Prove the end to end loop required by `CONTROLPLANE.md`: granted spawn,
    authenticated summary, prompt peer, receipt, audit row, revoke, and denied
    retry. Cover both harness home formats, prompt interrupt behavior, gateway
    absence, rollback, partial fan out, and packaged Gateway bundle.
11. Run repository gates verbatim: `just check` and `just test`. Run the focused
    control plane, Runtime, capture RPC, home seeding, migration, and packaged
    wheel tests during the inner loop.
