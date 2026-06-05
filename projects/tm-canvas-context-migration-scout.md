# Canvas Context Migration Scout

Hypothesis status: partially refuted. The inspector does not consume `/v1/sessions`,
`/v1/spaces`, or `/v1/runtime-templates`. The stream router is different:
FastAPI exposes `/v1/runs/{run_id}/stream`, and the inspector consumes it directly.

## Consumers Table

| Family | `www/packages/inspector` | `www/packages/canvas` | `www/packages/core` | `www/packages/shell` |
| --- | --- | --- | --- | --- |
| `/v1/sessions` | No consumer found. The nearest live stream consumer is `www/packages/inspector/src/hooks/useExchangeStream.ts::useExchangeStream`, which targets `/v1/runs/{run_id}/stream`. | `www/packages/canvas/src/session-canvas/api/sessionClient.ts::listSessions`, `www/packages/canvas/src/session-canvas/hooks/useSessions.ts::useSessions`, `www/packages/canvas/src/session-canvas/hooks/useLaunchSession.ts::useLaunchSession`, `www/packages/canvas/src/session-canvas/launcher/useSessionHistory.ts::useSessionHistory`, `www/packages/canvas/src/session-canvas/viewers/session-picker/SessionPickerPane.tsx::SessionPickerPane`, `www/packages/canvas/src/session-canvas/api/sessionEvents.ts::listSessionEvents`, `www/packages/canvas/src/session-canvas/api/sessionEvents.ts::sessionEventsStreamUrl`, `www/packages/canvas/src/session-canvas/stream/useSessionEventStream.ts::useSessionEventStream`, `www/packages/canvas/src/session-canvas/viewers/transcript-chat/TranscriptChatPane.tsx::TranscriptChatPane`, `www/packages/canvas/src/session-canvas/api/resourceContent.ts::loadResourceContent`, `www/packages/canvas/src/session-canvas/viewers/resource/ResourcePane.tsx::ResourcePane`. | `www/packages/core/src/queryKeys.ts::sessionsKey`, `www/packages/core/src/queryKeys.ts::launchSessionKey`, `www/packages/core/src/queryKeys.ts::sessionEventsKey`, `www/packages/core/src/queryKeys.ts::resourceContentKey`. Core supplies keys and request plumbing, not the session endpoint wrapper. | No production consumer found. Test stubs exist in `www/packages/shell/tests/e2e/canvas-persistence.spec.ts::mockSessionApi`. `www/packages/shell/src/rootShell.tsx::RootShell` only composes the canvas route. |
| `/v1/spaces` | No consumer found. | `www/packages/canvas/src/session-canvas/launcher/useCommandCenter.ts::useCommandCenter`, `www/packages/canvas/src/session-canvas/launcher/useSpaces.ts::useSpaces`. | `www/packages/core/src/transport.ts::fetchSpaces`, `www/packages/core/src/transport.ts::fetchWorktrees`, `www/packages/core/src/transport.ts::SpaceSummary`, `www/packages/core/src/transport.ts::WorktreeSummary`. | No production consumer found. |
| `/v1/runtime-templates` | No consumer found. | `www/packages/canvas/src/session-canvas/launcher/useCommandCenter.ts::useCommandCenter`, `www/packages/canvas/src/session-canvas/launcher/useRuntimeTemplates.ts::useRuntimeTemplates`. | `www/packages/core/src/transport.ts::fetchRuntimeTemplates`, `www/packages/core/src/types/runtimeTemplates.ts::RuntimeTemplateSummary`. | No production consumer found. Test stubs exist in `www/packages/shell/tests/e2e/launcher-root.spec.ts::openCanvas`, `www/packages/shell/tests/e2e/launcher-scroll.spec.ts::items`, and `www/packages/shell/tests/visual/fixtures/canvas.ts::fulfillCanvasV1Route`. |
| `/v1/stream` route family | `www/packages/inspector/src/app.tsx::BrowserAppShell`, `www/packages/inspector/src/hooks/useExchangeStream.ts::useExchangeStream`. The concrete URL is `/v1/runs/{run_id}/stream`. | No run stream consumer found. Canvas consumes the session event stream through `www/packages/canvas/src/session-canvas/api/sessionEvents.ts::sessionEventsStreamUrl`. | `www/packages/core/src/exchangeStreamEvents.ts::applyExchangeStreamEvent`, `www/packages/core/src/exchangeStreamEvents.ts::StreamSideEffects`, `www/packages/core/src/queryKeys.ts::exchangesKey`, `www/packages/core/src/queryKeys.ts::exchangeKey`. | No production consumer found. `www/packages/shell/src/rootShell.tsx::RootShell` only composes the inspector route. |

## Server Coupling Per Family

### `/v1/sessions`

`api/src/transport_matters/api/v1/session_routes.py::list_sessions`,
`api/src/transport_matters/api/v1/session_routes.py::get_session`,
`api/src/transport_matters/api/v1/session_routes.py::list_session_events`,
`api/src/transport_matters/api/v1/session_routes.py::get_session_timeline`, and
`api/src/transport_matters/api/v1/session_routes.py::get_session_resource` read from
Postgres through `api/src/transport_matters/session/async_dao.py::AsyncSessionDao`.
They do not call `api/src/transport_matters/session/writer.py::SessionWriter`.

Owner scoping is query based. `api/src/transport_matters/api/v1/session_routes.py::DEFAULT_OWNER`
defaults to `local`; route handlers pass `owner` into
`api/src/transport_matters/session/async_dao.py::get_session_for_owner`,
`api/src/transport_matters/session/async_dao.py::get_session_view_for_owner`,
`api/src/transport_matters/session/async_dao.py::list_session_views`,
`api/src/transport_matters/session/async_dao.py::get_events_for_owner`, and
`api/src/transport_matters/session/async_dao.py::get_events_with_raw_for_owner`.

The session streams
`api/src/transport_matters/api/v1/session_routes.py::stream_session_events` and
`api/src/transport_matters/api/v1/session_routes.py::stream_session_timeline` depend on
`api/src/transport_matters/session/listen.py::SessionEventHub`. The hub is fed by
`api/src/transport_matters/session/listen.py::SessionEventListener`, which owns a Postgres
`LISTEN` connection on `api/src/transport_matters/session/listen.py::NOTIFY_CHANNEL`.
That is portable to a TS `pg` client, but the contract is still Postgres
LISTEN/NOTIFY.

There is no direct mitmproxy or live flow coupling in the session route handlers.
There is indirect run exchange coupling for wire resources:
`api/src/transport_matters/session/resource_content.py::_load_wire_redirect` returns an
`api/src/transport_matters/session/resource_content_models.py::ExchangeRedirectDescriptor`,
and `api/src/transport_matters/api/v1/session_routes.py::_api_resource_content_response`
turns that into a run exchange route with
`api/src/transport_matters/api/v1/exchanges.py::exchange_detail_route`.
Canvas follows that path through
`www/packages/canvas/src/session-canvas/viewers/resource/ArkExchangeViewer.tsx::ArkExchangeViewer`
and `www/packages/core/src/transport.ts::fetchExchange`.

### `/v1/spaces`

`api/src/transport_matters/api/v1/space_routes.py::list_spaces`,
`api/src/transport_matters/api/v1/space_routes.py::get_space`,
`api/src/transport_matters/api/v1/space_routes.py::list_space_worktrees`, and
`api/src/transport_matters/api/v1/space_routes.py::list_space_canvases` read Postgres through
`api/src/transport_matters/space/store.py::SpaceStore`.

The family also owns writes:
`api/src/transport_matters/api/v1/space_routes.py::resolve_space`,
`api/src/transport_matters/api/v1/space_routes.py::patch_space`,
`api/src/transport_matters/api/v1/space_routes.py::create_canvas`, and
`api/src/transport_matters/api/v1/space_routes.py::patch_canvas`. In addition,
`api/src/transport_matters/api/v1/space_routes.py::list_space_worktrees` can write when
`refresh` is true because it calls `api/src/transport_matters/space/store.py::resolve_cwd`.

The backing store is Postgres plus filesystem and git detection.
`api/src/transport_matters/space/store.py::SpaceStore.resolve_cwd` calls
`api/src/transport_matters/space/detection.py::detect_space`, then writes `space`,
`space_git_identity`, `space_worktree`, and `canvas` rows through
`api/src/transport_matters/space/store.py::upsert_detection`,
`api/src/transport_matters/space/store.py::_claim_git_space`,
`api/src/transport_matters/space/store.py::_upsert_worktree`, and
`api/src/transport_matters/space/store.py::create_canvas`. It also writes a filesystem cache
through `api/src/transport_matters/space/store.py::_write_cache`.

Owner scoping is query based and flows into every `SpaceStore` call.

There is capture coupling. `api/src/transport_matters/api/v1/run_routes.py::_resolved_worktree`
resolves `worktreeId` through `api/src/transport_matters/space/store.py::SpaceStore.resolve_worktree`
before `api/src/transport_matters/api/v1/run_routes.py::create_run` can spawn a captured run.
`api/src/transport_matters/run_manager.py::RunManager._validate_spawn_request` and
`api/src/transport_matters/run_manager.py::RunManager._captured_request` carry `space_id` and
`worktree_id` into the captured run request. Shared proxy bindings persist those ids through
`api/src/transport_matters/shared_proxy/run_preparation.py::prepare_shared_captured_run` and
`api/src/transport_matters/shared_proxy/addon.py`.

### `/v1/runtime-templates`

`api/src/transport_matters/api/v1/runtime_template_routes.py::get_runtime_templates`
is a read only browse endpoint. It calls
`api/src/transport_matters/runtime_registry.py::list_runtime_templates` with `os.environ`.

The backing store is filesystem registry discovery, not Postgres and not in memory.
`api/src/transport_matters/runtime_registry.py::runtime_template_roots` searches
`~/.agent-runtimes/runtimes` and `~/.transport-matters/runtimes`, and
`api/src/transport_matters/runtime_registry.py::_list_runtime_templates_in_root` reads
`capabilities.json` when a sibling `runtime.toml` exists. The response shape comes from
`api/src/transport_matters/runtime_templates.py::RuntimeTemplateSummary`.

There is launch contract coupling, but not browse route coupling.
`api/src/transport_matters/api/v1/run_routes.py::_runtime_template_ref` still resolves a selected
template through `api/src/transport_matters/runtime_registry.py::resolve_runtime_template` when
`POST /v1/runs` launches a captured run.

### `/v1/stream` Route Family

There is no literal `/v1/stream` endpoint in this tree. `api/src/transport_matters/main.py`
mounts `api/src/transport_matters/api/v1/stream.py::router` under `/v1`, and that router exposes
`api/src/transport_matters/api/v1/stream.py::stream_run` at `/v1/runs/{run_id}/stream`.

The backing store is an in process broadcaster, not Postgres.
`api/src/transport_matters/api/v1/stream.py::stream_run` subscribes through
`api/src/transport_matters/broadcast.py::subscribe`. Publishers include
`api/src/transport_matters/exchange_recorder.py::emit_exchange`,
`api/src/transport_matters/exchange_recorder.py::emit_exchange_deleted`,
`api/src/transport_matters/pause_session.py::_run_pause`, and
`api/src/transport_matters/pause_session.py::_count_tokens_and_emit`.

This is live inspector traffic. The publishers are fed by the proxy, breakpoint, and exchange
recording path around mitmproxy HTTP flows and Codex websocket capture.

## Write Path Notes

`/v1/sessions` is route read only, but the session aggregate is Python owned.
`api/src/transport_matters/session/writer.py::SessionWriter._commit_batch` commits transcript
events, artifacts, dead letters, and session rows through
`api/src/transport_matters/session/async_dao.py::AsyncSessionDao`, then emits
`pg_notify` on `api/src/transport_matters/session/listen.py::NOTIFY_CHANNEL`.
`api/src/transport_matters/session/writer.py::SessionWriter._commit_run_lifecycle_event` does the
same for run lifecycle facts. A TS read API could consume Postgres directly, but session writes
should remain Python unless the transcript tailer and capture writer move too.

`/v1/spaces` has real route writes through `api/src/transport_matters/space/store.py::SpaceStore`.
Moving it to TS means porting the Postgres store, filesystem and git detection, cache writes, and
origin guarded mutation routes. Python run launch still needs resolved worktree facts for captured
runs unless `/v1/runs` also moves or calls the TS host.

`/v1/runtime-templates` has no write route. The browse endpoint can move independently if the TS
host reads the same runtime registry roots and preserves the same schema. Python run launch still
resolves the selected template at launch time.

`/v1/runs/{run_id}/stream` is a live in process event pipe. Moving only the HTTP endpoint to TS
would require a bridge from Python `broadcast.emit` to the TS process, or moving proxy,
breakpoint, and exchange recording ownership with it.

## Verdict Table

| Family | Verdict | Blocker | Effort |
| --- | --- | --- | --- |
| `/v1/sessions` | COUPLED | Canvas only on the frontend, but wholesale ownership is coupled to Python `SessionWriter`, Postgres LISTEN/NOTIFY, and wire resource redirects into run exchange detail. | Medium for TS read endpoints over the same Postgres schema. High for owning session writes or resource correlation. |
| `/v1/spaces` | COUPLED | Canvas only on the frontend, but the route family owns writes and Python run launch resolves worktrees through `SpaceStore`. | Medium. Port `SpaceStore`, `detect_space`, cache writes, and keep `/v1/runs` resolution against the same source of truth. |
| `/v1/runtime-templates` | CLEAN | No inspector consumer, no Postgres, no live flow state. The only shared constraint is the registry schema also used by run launch. | Low. Reimplement registry browse in TS against the same roots and response model. |
| `/v1/runs/{run_id}/stream` | COUPLED | Inspector consumer plus Python in process broadcast from proxy, breakpoint, and exchange recorder. This is not a Canvas bounded context. | High unless a Python to TS event bridge is introduced. |

Summary: `/v1/runtime-templates` is clean. `/v1/sessions` and `/v1/spaces` are Canvas facing but
not clean for wholesale migration. `/v1/runs/{run_id}/stream` belongs with the live inspector and
proxy path.
