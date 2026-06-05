# Transport Matters no DB API surface

Scope: FastAPI routes from `transport_matters.main.create_app` and `api/v1/router.py`; SPA static mount excluded. Unreachable DB degrades startup to `app.state.session_pool = None` via `main._start_session_store` and `main.lifespan`. Counts: HARD 8, SOFT 29, WRITE 0. No HTTP doctor route found.

| Route and method | Class | No DB client result | Evidence |
|---|---:|---|---|
| `GET /health` | SOFT | 200 `{status: ok}` | `main.create_app.health` |
| `GET/PATCH/DELETE /api/overrides`; `POST /api/overrides/toggle` | SOFT | Works from in memory override state; shared proxy sync may be absent, not DB. | `overrides.get_overrides`, `patch_overrides`, `delete_overrides`, `toggle_overrides` |
| `GET /api/breakpoint/status`; `GET /paused/{flow_id}`; `POST /arm`, `/disarm`, `/release/{flow_id}`, `/release-unmodified/{flow_id}`, `/re-audit/{flow_id}`, `/drop/{flow_id}` | SOFT | Works from breakpoint pause state; missing flow is 404, not DB. | `breakpoint_routes.get_status`, `get_paused_flow`, `arm_breakpoint`, `disarm_breakpoint`, `release_flow`, `release_flow_unmodified`, `re_audit_flow`, `drop_flow` |
| `GET /api/meta`; `GET /api/capabilities`; `GET /api/local-file`; `GET /api/local-file/raw`; `WS /api/terminal`; `GET /v1/runtime-templates` | SOFT | Settings, filesystem, PTY, or registry only. | `meta.get_meta`, `capabilities.get_capabilities`, `local_file_routes.local_file_content`, `local_file_raw`, `terminal.terminal_socket`, `runtime_template_routes.get_runtime_templates` |
| `POST /v1/runs` | HARD | 503 `session_store_unavailable` before spawn when preflight cannot reach DB; continuation path also 503 without pool. | `run_routes.create_run`, `_launch_fields`, `RunManager._ensure_session_store_available`, `_RUN_MANAGER_HTTP_STATUS` |
| `GET /v1/runs`; `GET /v1/runs/{run_id}`; `POST /v1/runs/{run_id}/terminate`; `WS /v1/runs/{run_id}/terminal` | SOFT | In process `RunManager`; missing run is 404 or websocket `run_not_found`. | `run_routes.list_runs`, `get_run`, `terminate_run`, `run_terminal_socket` |
| `GET /v1/runs/{run_id}/exchanges`; `GET /{exchange_id}`; `GET /{exchange_id}/turn-content`; `GET /{exchange_id}/pipeline_tokens`; `GET /v1/runs/{run_id}/meta`; `GET /v1/runs/{run_id}/stream` | SOFT | Disk run storage or broadcast stream; local missing artifacts can 404 or 500, not DB. | `exchanges.list_exchanges`, `get_exchange`, `get_turn_content`, `get_pipeline_tokens`, `meta.get_run_meta`, `stream.stream_run`, `run_storage.resolve_run_storage_or_404` |
| `GET /v1/sessions`; `GET /v1/sessions/{session_id}`; `GET /events`; `GET /timeline`; `GET /resources/{resource_id}`; `GET /events/stream`; `GET /timeline/stream` | HARD | 503 `session_store_unavailable` when pool is absent; if pool exists then dies, DB calls can 500 or close SSE. | `session_routes._session_pool`, `list_sessions`, `get_session`, `list_session_events`, `get_session_timeline`, `get_session_resource`, `stream_session_events`, `stream_session_timeline` |

WRITE: no FastAPI route uses `SessionWriter` or event ingest. Ingest is outside the APIRouter surface.
