# TM Rebuild Scout: Backend Control Plane and Identity

## Baseline

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
- Branch: `main`
- HEAD: `e3aaecf12905fd16d2ff142d350c49a3420932ad`
- Scope: backend control plane and identity in `api/`, with minimal UI inspection to locate logic that should belong to the API.
- Mode: read-only scout for the repo. No subagents were used. No repo files were edited.
- Pristine check before verdict: `git status --short` returned no rows.

## North Star lens

The North Star calls for an API-first product with one control plane. The director agent and command palette should be twin clients of the same verbs. The backend should own observe, launch, manage, and prompt semantics. The UI should render and request operations, not decide control-plane policy.

Current backend has valuable, working substrate for capture, sessions, runtime templates, process supervision, and space detection. It does not yet expose one coherent control-plane aggregate. Several decisions that should be backend operations still live in the canvas and launcher stores.

## Scout Reuse Map

### Carry forward

| Asset | Evidence | Reuse decision |
| --- | --- | --- |
| Live run supervision | `api/src/transport_matters/run_manager.py::RunManager`, especially `spawn`, `list`, `attach`, `detach`, `terminate`, `close` | Keep as the process adapter behind a new control-plane service. Its process lifecycle, terminal attach semantics, and idempotency handling are real substrate. |
| Captured launch preparation | `api/src/transport_matters/captured_run_context.py::build_captured_run_context`, `api/src/transport_matters/shared_proxy/run_preparation.py::prepare_shared_captured_run` | Keep as launch adapters. They already centralize proxy, run directory, runtime home, managed session, and provider invocation work. |
| Session store write path | `api/src/transport_matters/session/writer.py::SessionWriter`, `api/src/transport_matters/session/dao_async.py::AsyncSessionDao` | Keep. The writer and DAO already give parameterized Postgres writes, event artifacts, dead letters, and owner-scoped reads. |
| Live session events | `api/src/transport_matters/session/hub.py::SessionEventHub`, `api/src/transport_matters/session/listener.py::SessionEventListener` | Keep. LISTEN/NOTIFY plus catch-up is the right backend primitive for observe clients. |
| Runtime template registry | `api/src/transport_matters/runtime_registry.py::list_runtime_templates`, `api/src/transport_matters/runtime_registry.py::resolve_runtime_template`, `api/src/transport_matters/api/v1/runtime_template_routes.py::get_runtime_templates` | Keep the registry and move launch choice behind server policy. Today the API lists templates, while the UI chooses the spawnable harness. |
| Tier 1 run storage | `api/src/transport_matters/api/v1/storage_backends.py::DiskStorageBackend`, `api/src/transport_matters/api/v1/run_storage.py::run_workspace_id` | Keep as legacy run artifact storage. Do not make its path-derived workspace identity part of the new public control plane. |
| Space detection primitives | `api/src/transport_matters/space/detection.py::detect_space`, `api/src/transport_matters/space/detection.py::repo_instance_key` | Keep as detection inputs. Redraw the aggregate boundary around space, worktree, canvas, pane, run, and session. |
| Existing session read routes | `api/src/transport_matters/api/v1/session_routes.py::list_sessions`, `get_session`, `list_events`, `get_timeline`, `stream_events`, `stream_timeline` | Keep as read-side surfaces, then hang them from the same identity model as runs and canvases. |

### Redraw

| Area | Evidence | Redraw decision |
| --- | --- | --- |
| Control-plane aggregate | `api/src/transport_matters/api/v1/run_routes.py::create_run`, `list_runs`, `get_run`, `terminate_run`, `run_terminal_socket`; legacy breakpoint routes in `api/src/transport_matters/api/legacy_routes.py` | Replace route-level orchestration with a domain service that owns typed observe, launch, manage, and prompt operations. REST, MCP, CLI, director, and palette should call that service. |
| Prompt semantics | `api/src/transport_matters/api/v1/run_routes.py::bridge_attached_run_terminal` | Raw PTY websocket input is not a first-class prompt operation. Add a typed prompt verb with target, provenance, idempotency, auditability, and permission checks. |
| Server-side canvas projection | `api/src/transport_matters/space/models.py::Canvas`, `api/src/transport_matters/api/v1/space_routes.py::create_canvas`, `update_canvas`; UI ownership in `www/src/session-canvas/model/canvasStore.ts::useCanvasStore` | Keep Canvas as a backend concept, but move pane layout, dock, minimize, restore, attach, and close into a server projection. |
| Runtime launch choice | `www/src/session-canvas/launcher/commandModel.ts::templateSpawnHarness`; backend validation in `api/src/transport_matters/api/v1/run_routes.py::_runtime_template_ref` | Move recommendation-to-launch resolution into the backend. The UI can display recommendations, but the control plane should choose and validate launch policy. |
| Identity exposure | `api/src/transport_matters/workspace.py::workspace_id`, `api/src/transport_matters/space/store.py::resolve_cwd`, `resolve_session_cwd`, `resolve_worktree`; DTOs in `api/src/transport_matters/session_models.py::SessionView` | Retire public `workspaceId` as a first-class identity. Use Space, Worktree, Canvas, Pane, Run, and Session ids. Keep path hash only as internal legacy storage identity. |
| Migration baseline | `api/migrations/versions/0001_session_store_foundation.py::downgrade`, `api/migrations/versions/0006_spaces_foundation.py::upgrade` | Pre-release status makes a clean migration baseline preferable. 0001 is forward-only and 0006 retrofits identity into existing sessions. |
| API utility duplication | `api/src/transport_matters/api/v1/run_routes.py::ApiError`, `api/src/transport_matters/session_models.py::ApiError`, `api/src/transport_matters/api/v1/space_routes.py::ApiError` | Consolidate error and cursor helpers before expanding the route surface. Current duplication will multiply if the control plane is added incrementally. |

## Quality Map

### Control plane reality

| Verb | Current backend surface | Gap against North Star |
| --- | --- | --- |
| Observe | `api/src/transport_matters/api/v1/session_routes.py::*`, `api/src/transport_matters/api/v1/space_routes.py::list_spaces`, `list_worktrees`, `list_canvases`, `api/src/transport_matters/api/v1/run_routes.py::list_runs` | Good read substrate, but live runs are process-resident and canvas state is not a unified server projection. |
| Launch | `api/src/transport_matters/api/v1/run_routes.py::CreateRunRequest`, `create_run`, `api/src/transport_matters/run_manager.py::spawn` | Launch requires `worktreeId`, accepts runtime template and harness fields, but has no typed pane placement, no canvas intent, and no prompt payload. |
| Manage | `api/src/transport_matters/api/v1/run_routes.py::terminate_run`, `run_terminal_socket`; legacy breakpoint routes under `api/src/transport_matters/api/legacy_routes.py` | Terminate and terminal attach exist. Detach, focus, arrange, dock, minimize, interrupt, breakpoint policy, and pane lifecycle are not one typed management API. |
| Prompt | `api/src/transport_matters/api/v1/run_routes.py::bridge_attached_run_terminal` | The backend passes terminal bytes. It does not expose a typed prompt command that a director and palette can both call. |

### UI-owned control logic

- `www/src/session-canvas/launcher/commandModel.ts::templateSpawnHarness` maps runtime recommendation to a spawn harness. This is backend launch policy today living in the UI.
- `www/src/session-canvas/model/capturedRunStore.ts::useCapturedRunStore` owns spawn dedupe by pane key, close and minimize behavior, best-effort terminate, bypass permission toggle, and persisted run mapping.
- `www/src/session-canvas/model/canvasStore.ts::useCanvasStore` owns panes, docked panes, layout, viewport, expand, frame, minimize, restore, and spawn state through local persistence.
- `www/src/api.ts::createCapturedRun`, `terminateRun`, `listRuns`, `fetchSpaces`, and `fetchWorktrees` are thin clients. The logic above them should become server behavior.

### Identity model

Current identity layers are all useful in context, but they are not cleanly separated in the public model.

| Identity | Evidence | Role today | Target role |
| --- | --- | --- | --- |
| `cwd` | `api/src/transport_matters/space/store.py::resolve_cwd`, `api/src/transport_matters/main.py::_resolve_current_space`, `api/src/transport_matters/session/backfill.py::backfill_session_spaces` | Launch fact, startup default, session backfill input, and resolver key | Launch fact and diagnostic only. |
| `workspace_slug` and `workspace_hash` | `api/src/transport_matters/workspace.py::workspace_id`, `api/src/transport_matters/session_models.py::workspace_id_from_row` | Path-derived storage and DTO identity | Internal legacy storage identity. Do not expose as the control-plane target. |
| `repo_instance_key` | `api/src/transport_matters/space/detection.py::repo_instance_key`, `api/src/transport_matters/space/store.py::_claim_git_space` | Git common-dir claim key for Space | Keep internal uniqueness and race handling. |
| `space_id` | `api/src/transport_matters/space/models.py::Space`, `api/src/transport_matters/space/store.py::_claim_git_space` | Repo or plain folder aggregate | Public parent aggregate. |
| `worktree_id` | `api/src/transport_matters/space/models.py::Worktree`, `api/src/transport_matters/api/v1/run_routes.py::_resolved_worktree` | Launch target and session correlation | Canonical launch target. |
| `canvas_id` | `api/src/transport_matters/space/models.py::Canvas`, `api/src/transport_matters/api/v1/space_routes.py::create_canvas` | Server object with weak UI adoption | Public projection parent for panes and placements. |
| `session_id` and `run_id` | `api/src/transport_matters/run_manager.py::RunManager`, `api/src/transport_matters/session_models.py::SessionRow` | Live process id plus captured transcript id | Keep, but make their relationship explicit in the control-plane DTOs. |

Measured spread from production source grep excluding tests shows the churn surface: `cwd` appears in 45 files, `space_id` in 32, `worktree_id` in 21, `workspace_id` or its slug/hash forms in 19, `repo_instance_key` in 3, and `canvas_id` in 3. The direction is right, but another incremental pass will touch many seams again.

Recent history confirms active rekey churn around the same seams: `046281c feat(spaces): add identity and schema foundation (#161)`, `70f34a8 feat(spaces): detect and persist spaces (#162)`, `5fb3ce0 feat(spaces): rekey managed runs by worktree (#164)`, and `70493a4 feat(spaces): backfill session space identity (#165)`.

### Code quality and migration debt

- No production file in `api/src/transport_matters` exceeds 700 lines, but several core seams are at the threshold: `api/src/transport_matters/api/v1/run_routes.py` at 696 LOC, `api/src/transport_matters/cli/codex_cmd.py` at 675 LOC, `api/src/transport_matters/cli/desktop_cmd.py` at 652 LOC, `api/src/transport_matters/space/store.py` at 627 LOC, and `api/src/transport_matters/run_manager.py` at 617 LOC.
- Large classes or functions concentrate orchestration: `api/src/transport_matters/run_manager.py::RunManager`, `api/src/transport_matters/space/store.py::SpaceStore`, `api/src/transport_matters/api/v1/storage_backends.py::DiskStorageBackend`, `api/src/transport_matters/transcript_tailer.py::TranscriptTailer`, and `api/src/transport_matters/session/dao_async.py::AsyncSessionDao`.
- `api/src/transport_matters/api/v1/run_routes.py` mixes DTOs, validation, error mapping, runtime template resolution, space resolution, continuation fields, REST routes, and WebSocket terminal bridging.
- Route-family coupling exists: `api/src/transport_matters/api/v1/runtime_template_routes.py::get_runtime_templates` imports `ApiError` from session models, and `api/src/transport_matters/api/v1/space_routes.py` imports `require_http_origin` from run routes.
- `api/migrations/versions/0001_session_store_foundation.py::downgrade` raises a forward-only runtime error. Later migrations mostly have downgrades, but the baseline prevents true reversibility.

## Plan

### Recommended hybrid plan

1. Freeze current substrate behind adapters.
   - Keep `RunManager`, captured run preparation, shared proxy preparation, runtime registry, session writer, session DAO, event hub, and listener.
   - Treat current `/v1/runs`, `/v1/sessions`, `/v1/spaces`, and legacy breakpoint routes as compatibility adapters during the cutover.

2. Define the control-plane domain model before adding endpoints.
   - Canonical ids: `spaceId`, `worktreeId`, `canvasId`, `paneId`, `runId`, `sessionId`, `operationId`.
   - Canonical target: Worktree for launch, Canvas and Pane for placement, Run and Session for execution and history.
   - `cwd`, `workspace_slug`, and `workspace_hash` remain internal storage facts.

3. Add a typed API contract for the shared control plane.

```typescript
interface ControlPlaneTarget {
  worktreeId: string;
  canvasId?: string;
  paneId?: string;
}

type ControlPlaneVerb = "observe" | "launch" | "manage" | "prompt";

type HarnessName = "claude" | "codex";

interface LaunchRunRequest {
  target: ControlPlaneTarget;
  harness?: HarnessName;
  runtimeTemplate?: { name: string; source?: string };
  continueFromSessionId?: string;
  idempotencyKey?: string;
  bypassPermissions?: boolean;
  initialPrompt?: PromptCommand;
}

interface PromptCommand {
  target: { runId?: string; paneId?: string };
  text: string;
  idempotencyKey?: string;
  source: "palette" | "director" | "api";
}

interface ManageCommand {
  target: { runId?: string; paneId?: string; canvasId?: string };
  action: "terminate" | "interrupt" | "detach" | "attach" | "focus" | "dock" | "undock" | "minimize" | "restore" | "arrange";
  idempotencyKey?: string;
  payload?: unknown;
}

interface ControlPlaneOperation {
  operationId: string;
  verb: ControlPlaneVerb;
  state: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  runId?: string;
  sessionId?: string;
  target?: ControlPlaneTarget;
  createdAt: string;
  updatedAt: string;
}

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

4. Implement `ControlPlaneService` as the single backend owner.
   - REST `/v1/control-plane/*`, MCP director tools, CLI helpers, and palette calls all invoke this service.
   - The service delegates process work to `RunManager`, launch prep to captured-run adapters, template lookup to `runtime_registry`, and history to session DAO.
   - The service owns idempotency, target validation, permission checks, audit events, and error shape.

5. Move canvas and pane state server side.
   - Add pane projection tables or a JSONB projection with versioned updates.
   - `Canvas.layout` can be the seed, but pane lifecycle needs explicit server semantics.
   - UI store becomes a cache of server state and optimistic operations, not the source of truth.

6. Clean identity in one migration pass.
   - Squash or replace the migration baseline while pre-release permits it.
   - Make `worktree_id` required for new runs and sessions.
   - Backfill old sessions once, then delete dual-path workspace identity from public DTOs.
   - Keep Tier 1 path-derived storage mapping in an adapter.

7. Delete duplicated route utilities.
   - Centralize `ApiError`, cursor codec, response payload helpers, origin checks, and app-state dependency helpers under an API support module before expanding routes.

8. Retire UI-only orchestration.
   - Delete or shrink `templateSpawnHarness`, captured-run pane dedupe, local run mapping, and local pane lifecycle logic once the server projection exists.

### Verification gates

- Unit tests for identity target validation: missing worktree, archived worktree, wrong-space canvas, missing pane, and stale run.
- API contract tests for observe, launch, manage, and prompt using one error format.
- Integration tests for director and palette invoking the same service path.
- WebSocket tests for attach, detach, reconnect, scrollback, heartbeat, and terminal ordering.
- Migration tests with downgrade or an explicit pre-release baseline replacement proof.
- UI smoke that proves canvas reload gets layout, panes, run mapping, and session correlation from the backend.
- Pristine-tree proof after scout or review runs.

## Iterate versus rebuild

Pure iterate would preserve too much accidental route and UI ownership. It would require changing `run_routes`, `space_routes`, session DTOs, migrations, UI stores, and runtime-template launch semantics in place while those files are already close to the project size threshold.

Full rebuild would waste stable and tested substrate. Capture, shared proxy setup, runtime home planning, runtime templates, session store, event streaming, and live process supervision are real assets.

Hybrid has the best risk profile: rebuild the control-plane and identity aggregate, reuse the capture, runtime, session, and process adapters.

## Verdict

Verdict: hybrid.

Single decisive evidence: the backend already has strong capture, session, runtime, and process primitives, while the North Star control plane is still split across route handlers and UI stores, with identity churn spread across cwd, workspace hash, space, worktree, canvas, run, and session seams.
