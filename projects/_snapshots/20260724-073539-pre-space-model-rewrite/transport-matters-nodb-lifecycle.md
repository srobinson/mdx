# Transport Matters no DB lifecycle

Scope: no reachable Postgres from process start.

Earliest normal launch failure: `api/src/transport_matters/cli/launch_runtime.py:preflight_session_store_or_exit`. `api/src/transport_matters/cli/start_cmd.py:run_start`, `api/src/transport_matters/cli/codex_cmd.py:run_codex`, and `api/src/transport_matters/cli/desktop_cmd.py:serve_desktop_backend` call it before proxy, web app, agent, or Electron serving. It scaffolds settings, clears settings cache, calls `api/src/transport_matters/session_store_preflight.py:check_session_store`, then exits 2 on any error. Missing config fails at `api/src/transport_matters/config.py:resolve_database_url`; configured but unreachable first touches Postgres in `check_session_store` through `psycopg.connect`.

Seam classifications:

| Seam | Classification | Result with no DB |
| --- | --- | --- |
| `config.py:resolve_database_url` | hard crash for missing config | raises `MissingDatabaseConfigError`; no socket attempt |
| `session/pool.py:connect`, `async_connect` | hard crash | caller gets connection error |
| `session/pool.py:create_pool`, `create_async_pool` | lazy | no connect until open or checkout |
| `session_store_preflight.py:check_session_store` | exception swallowed | returns operator error string |
| `cli/launch_runtime.py:preflight_session_store_or_exit` | hard crash | prints setup guidance, exits 2 |
| `addon_runtime.py:load_capture_runtime`, `_start_session_capture` | degrades cleanly at startup | storage and binding are built first; session capture failures log and return no writer or tailer |
| `main.py:lifespan`, `_start_session_store`, `addon_runtime.py:start_web_runtime` | degrades cleanly for unreachable store | direct backend serves with session pool unset and session routes unavailable; confirmed migration failure on a reachable DB raises |
| `run_manager.py:RunManager._ensure_session_store_available` | hard blocks captured pane spawn | raises `session_store_unavailable` before preparing a run |
| `session/writer.py:SessionWriter._ensure_open`, `_commit_batch` | exception swallowed by capture observer path | first transcript commit can fail without taking down proxy |
| `session/listen.py:SessionEventListener.start`, `_run` | exception swallowed | listener reconnect loop logs and continues |
| `cli/db_cmd.py:status`, `upgrade` | hard crash | exits nonzero on missing or unreachable DB |
| `cli/diagnose.py:run_doctor` | degrades cleanly | reports concise session store failure, exits 1 |
| `session/migrate.py:current_revision`, `apply_migrations`; `api/migrations/env.py:run_migrations_online` | hard crash to caller | connection or Alembic failure propagates |

Tier 1 verdict: normal `transport-matters claude` cannot write Tier 1 without Postgres from process start, because preflight exits before the run lock, manifest, proxy, and agent. If that guard is bypassed, or Postgres dies after launch, Tier 1 wire writes still can proceed through `addon_runtime.py:load_capture_runtime`, `storage/__init__.py:init_storage`, `storage/disk.py:DiskStorageBackend.persist_exchange`, and `exchange_recorder.py:persist_http_exchange`; Postgres transcript capture becomes best effort only.

Verification: `fmm validate` passed for 843 indexed files. Focused pytest passed: `cli/test_desktop.py::test_desktop_backend_server_hard_blocks_on_session_store_preflight`, `cli/test_diagnose.py::test_doctor_reports_session_store_unreachable_cleanly`, `test_run_manager_spawn_control.py::test_session_store_preflight_does_not_cache_failures`.
