# Transport Matters B6 Curated API Feasibility Review, Codex verifier

Reviewed 2026-06-15 against `transport-matters` HEAD `16b95d7`, using fmm first and shell probes for absence checks. Scope was read only. Product context from the orchestrator: continuation is a Transport Matters concept, `transport-matters desktop` takes no passthrough resume args, and native CLI resume is off the table.

## Verdict

`review: issue should-fix` for B6 rollout sequencing. The proposed in place delete is feasible for `/api/runs` if the terminal websocket moves in the same PR. Deleting `/api/sessions` during the foundation slice is unsafe unless the same PR also migrates the active event backlog, event SSE, gap backfill, and resource content consumers. The session prefix already serves the transcript family, including list, events, streams, timeline, and resources.

Everything else is feasible without new durable infrastructure, but continuation needs real plumbing through the existing spawn and tailer path.

## Q1, blast radius of `/api/runs` and `/api/sessions`

### Current backend mount

The ASGI app mounts the existing API router under `/api` at `api/src/transport_matters/main.py:202`. The router includes `session_routes` and `run_routes` with no facade namespace at `api/src/transport_matters/api/v1/router.py:23` and `api/src/transport_matters/api/v1/router.py:27`.

### `/api/runs` production call sites

| Surface | Evidence | Consumer shape |
| --- | --- | --- |
| `POST /api/runs` | `www/src/api.ts:398-409` | `createCapturedRun` unwraps `{ run: { runId } }`. |
| `DELETE /api/runs/{id}` | `www/src/api.ts:412-419` | `deleteRun` ignores response body. |
| `GET /api/runs` | `www/src/api.ts:461-473` | `listRuns` unwraps `{ runs }`; fmm reports no production callers. |
| `WS /api/runs/{id}/terminal` | `www/src/session-canvas/viewers/terminal/terminalSocket.ts:67-75` | terminal attach URL builder. |
| Spawn and stop lifecycle | `www/src/session-canvas/model/capturedRunStore.ts:99-149` | calls `createCapturedRun` and `deleteRun`. |
| Terminal pane | `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx:40-68` | starts run then renders attached terminal. |

The current run response leaks internal fields. Backend `RunViewModel` exposes `storageDir`, `proxyPort`, `webPort`, `nativeSessionId`, `scrollbackBytes`, and `scrollbackLimitBytes` at `api/src/transport_matters/api/v1/run_routes.py:80-100`; the frontend mirror is `www/src/api.ts:429-447`.

Run migration can be one PR if it includes all four run surfaces: create, delete, optional list, and websocket terminal. `deleteRun` already discards the stop response, so changing `DELETE` to return curated `Run` has low frontend risk.

### `/api/sessions` production call sites

| Surface | Evidence | Consumer shape |
| --- | --- | --- |
| Session list | `www/src/session-canvas/api/sessionClient.ts:38-52` | `/api/sessions?...`, raw snake case `SessionSummary`. |
| Session type | `www/src/session-canvas/api/sessionClient.ts:3-23` | includes `native_session_id`, `source_descriptor`, `home_dir`, `parent_session_id`, `forked_at_seq`. |
| Picker | `www/src/session-canvas/viewers/session-picker/SessionPickerPane.tsx:7-74` | lists workspace sessions and opens a transcript pane. |
| Launch resolution | `www/src/session-canvas/hooks/useLaunchSession.ts:9-26` and `www/src/session-canvas/SessionCanvasRoute.tsx:14-28` | polls list API to auto open the live transcript. |
| Event backlog | `www/src/session-canvas/api/sessionEvents.ts:39-56` | `/api/sessions/{id}/events?...`. |
| Event SSE | `www/src/session-canvas/api/sessionEvents.ts:58-69` | `/api/sessions/{id}/events/stream?...`. |
| Gap backfill | `www/src/session-canvas/stream/useSessionEventStream.ts:42-79` | SSE callback calls `listSessionEvents` on sequence gaps. |
| Transcript UI | `www/src/session-canvas/viewers/transcript-chat/TranscriptChatPane.tsx:10-55` | combines backlog, SSE, reducer, and IR to chat projection. |
| Resource content | `www/src/session-canvas/api/resourceContent.ts:107-135` | `/api/sessions/{id}/resources/{resourceId}`. |
| Resource UI | `www/src/session-canvas/viewers/resource/ResourcePane.tsx:33-47` | DB resource pane calls `useResourceContent`. |

The backend session route family is wider than the list endpoint: list at `api/src/transport_matters/api/v1/session_routes.py:128-156`, event backlog at `159-179`, timeline at `182-213`, resource content at `216-240`, event SSE at `256-271`, and timeline SSE at `274-289`.

Tests and mocks also hardcode these routes: `www/src/api.test.ts:125-203`, `www/src/session-canvas/api/sessionClient.test.ts:24-40`, `www/src/session-canvas/stream/useSessionEventStream.test.tsx:48-85`, `www/src/session-canvas/viewers/terminal/terminalSocket.test.ts:89-154`, and `www/tests/e2e/canvas-persistence.spec.ts:51-65`.

### Q1 conclusion

`/api/runs` can move in place because the active production blast radius is compact and centralized. `/api/sessions` should move as a session family. A PR that only adds curated session list and deletes `/api/sessions` would break TranscriptChatPane and ResourcePane. Either migrate list, events, event stream, timeline, timeline stream, and resources together, or keep a temporary compatibility alias until every session family consumer has moved.

This is the substantive issue in the proposal. The issue is sequencing; the `/v1` direction remains viable.

## Q2, continuation at the existing spawn seam

Current spawn path:

1. `POST /api/runs` enters `create_run` at `api/src/transport_matters/api/v1/run_routes.py:284-295`.
2. `_spawn_request` builds `SpawnRun` at `api/src/transport_matters/api/v1/run_routes.py:233-244`.
3. `RunManager.spawn` prepares and starts the captured run at `api/src/transport_matters/run_manager.py:237-305`.
4. `_captured_request` converts `SpawnRun` into `CapturedRunRequest` at `api/src/transport_matters/run_manager.py:389-416`.
5. `prepare_captured_run` persists owned launch facts and returns a managed session descriptor at `api/src/transport_matters/captured_run.py:155-277`.
6. The addon registers the owned transcript cursor through `_register_owned_cursor` at `api/src/transport_matters/addon_runtime.py:86-104`.
7. The tailer writes `SessionRow` through `build_session` and `SessionWriter._commit_batch` at `api/src/transport_matters/session/ingest.py:62-80` and `api/src/transport_matters/session/writer.py:107-163`.

Already present:

- The session schema has `parent_session_id` and `forked_at_seq` with the paired null check at `api/migrations/versions/0001_session_store_foundation.py:36-42`.
- `SessionBinding` has both lineage fields at `api/src/transport_matters/index/adapters/base.py:42-43`.
- `build_session` persists both fields into `SessionRow` at `api/src/transport_matters/session/ingest.py:77-78`.
- The upsert SQL inserts and preserves both values at `api/src/transport_matters/session/dao_statements.py:68-97`.

Missing:

- No request field exists. `CreateRunRequest` only has `cli`, `cwd`, `terminal`, and `oscColorReplies` at `api/src/transport_matters/api/v1/run_routes.py:70-77`; `SpawnRun` has no continuation field at `api/src/transport_matters/run_manager.py:108-127`.
- The run context passed into adapter binding has no lineage fields. `_launch_run_context` builds only run, cwd, workspace, cli, start, native id, and home at `api/src/transport_matters/addon_runtime.py:67-83`.
- `_register_owned_cursor` only adds `minted` and `source_descriptor` to the binding at `api/src/transport_matters/addon_runtime.py:96-100`.
- `register_session_cursor` rebinds and only carries `minted` and `source_descriptor` from the original binding at `api/src/transport_matters/index/tailer.py:438-469`; parent and fork values would be dropped unless this seam is extended.
- There is no continuation name in the spawn path: `absent: rg continueFromSessionId|continuationId|continuation_id|continue_from_session_id api/src/transport_matters/api/v1/run_routes.py api/src/transport_matters/run_manager.py api/src/transport_matters/captured_run_models.py api/src/transport_matters/index/adapters/base.py api/src/transport_matters/addon_runtime.py -> 0`.
- The last visible seq helper is missing. Data exists in `event.seq`, `event.kind`, and `event.is_sidechain` at `api/migrations/versions/0001_session_store_foundation.py:58-83`, but no DAO method computes the fork point today.
- If B6 requires `purpose=continuation` and `visibility=user_visible`, those columns are still absent. That remains the separate schema prereq.

Q2 conclusion: continuation can live at the existing create run seam without a new durable subsystem. The change still needs new plumbing: add `continueFromSessionId`, owner scoped parent validation, fork seq calculation, lineage fields on the spawn context or binding carry, and transcript context priming from Postgres. Native CLI resume should not be evaluated for this product path.

## Q3, `homeDir` droppable from curated Session

Code confirms `Session.homeDir` is droppable from the curated product contract.

What exists today:

- Backend `SessionSummary` exposes `home_dir` at `api/src/transport_matters/api/v1/session_routes.py:51-79`.
- Frontend `SessionSummary` declares `home_dir` at `www/src/session-canvas/api/sessionClient.ts:3-23`.
- `absent: rg '\bhome_dir\b|homeDir' www/src, excluding the session type and test utils -> 0`, so production frontend code does not read it.

Launch and tailing still use launch scoped home values:

- `Settings.agent_home_dir` is a launch setting at `api/src/transport_matters/config.py:98-102`.
- `_spawn_request` passes it into `SpawnRun` at `api/src/transport_matters/api/v1/run_routes.py:233-244`.
- `CapturedRunRequest.home_dir` flows through the captured run preparation path at `api/src/transport_matters/run_manager.py:389-416`.
- `prepare_runtime_home_overlay` creates a per run runtime home and schedules teardown at `api/src/transport_matters/captured_run_context.py:94-114`.
- The transcript binding carries a home value for current locate and snapshot operations, for example `ClaudeAdapter.bind` at `api/src/transport_matters/index/adapters/claude.py:80-97` and `ClaudeAdapter.locate` at `api/src/transport_matters/index/adapters/claude.py:99-109`.
- Backfill uses owned launch facts, not the DB session row, to reconstruct bindings at `api/src/transport_matters/session/backfill.py:132-154`.

Q3 conclusion: there is no relaunch, resume, or launch consumer of the persisted `SessionSummary.home_dir` field. The launch path has separate launch scoped home facts. Curated `Session` should drop raw `homeDir`; if provenance becomes a product need, expose structured provenance in a debug projection instead.

## Q4, `turnCount` and `inheritedTurnCount` computed at read

Data is available:

- The event table stores per session `seq`, `kind`, `role`, and `is_sidechain` at `api/migrations/versions/0001_session_store_foundation.py:58-83`.
- The primary key `(session_id, seq)` at `api/migrations/versions/0001_session_store_foundation.py:80-82` makes per session scans bounded to one session key range.
- Parent linkage lives on the session row at `api/migrations/versions/0001_session_store_foundation.py:36-42`.
- Existing child summary SQL already aggregates child event min and max by session at `api/src/transport_matters/session/dao_statements.py:202-212`.

What is absent:

- `SessionSummary` has no count fields at `api/src/transport_matters/api/v1/session_routes.py:51-79`.
- `list_sessions` does not compute counts at `api/src/transport_matters/api/v1/session_routes.py:128-156`.
- `absent: rg turnCount|inheritedTurnCount|currentTurnCount|inheritedForkTurnCount api/src www/src -> 0 relevant B6 hits`.

Q4 conclusion: compute counts in the B6 session projection query. Use one aggregate for the visible page, not an N plus 1 loop. `turnCount` can count current session visible turn events. `inheritedTurnCount` can count parent visible turn events where `seq <= forked_at_seq`. This has low latency risk at realistic session sizes because the primary key is keyed by `session_id`; add a partial `(session_id, kind, is_sidechain, seq)` index only if measured reads need it. No denormalized columns are needed for the first slice.

## Q5, canvas layout

No agent domain consumer currently needs canvas layout in B6.

Evidence:

- `absent: rg canvas-layout|canvas_layout|canvasKey|canvas_key|PersistedCanvasState api/src -> 0`.
- Canvas persistence is frontend local state. `PersistedCanvasState` is defined in `www/src/session-canvas/persistence/canvasPanePersistence.ts:36-38`.
- The canvas store persists via frontend storage keys at `www/src/session-canvas/model/canvasStore.persistence.ts:18-26` and `www/src/session-canvas/model/canvasStore.ts:288`.
- Current session pane refs use session ids and resource ids, not a backend layout noun. For transcript spawning, `spawnOrFocusTranscript` builds a `session-timeline` pane ref at `www/src/session-canvas/model/canvasStore.ts:253-262`.

Q5 conclusion: cutting canvas layout from B6 is correct for the captured agent domain. Backend layout storage can be a desktop context endpoint later, keyed by workspace and canvas id, without blocking B6.

## Recommended proposal change

Change the build order wording from:

> Migrate www run/session reads; delete `/api/runs`, `/api/sessions`.

To:

> Migrate and delete one complete route family at a time. For runs, include create, delete, list, get, and terminal websocket. For sessions, include list, single get, events, event stream, timeline, timeline stream, and resources before deleting `/api/sessions`; otherwise keep a temporary compatibility alias until the full session family is moved.

This keeps the clean single namespace direction while avoiding a broken intermediate state.
