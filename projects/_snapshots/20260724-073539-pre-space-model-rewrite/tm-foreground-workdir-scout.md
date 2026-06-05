# Transport Matters foreground workdir reuse scout

Root cause: live meta cwd blind spot. The #180 workdir switch compares the requested workdir with `DesktopRuntimeStatus.cwd`, but the live runtime discovery path still fills that field from the desktop record. A healthy backend can therefore be reused from a stale record even when `/api/meta` says the live backend serves a different cwd.

## Reuse Map

- CLI foreground entry: `api/src/transport_matters/cli/__init__.py+desktop` dispatches `--foreground` to `api/src/transport_matters/cli/desktop_cmd.py+run_desktop_launch` and passes `work_dir`, `web_port`, `storage_dir`, and `force_restart`.
- Foreground reuse branch: `api/src/transport_matters/cli/desktop_cmd.py+run_desktop_launch` calls `api/src/transport_matters/cli/desktop_recovery.py+prepare_desktop_runtime_for_launch_or_exit`. When that returns a status, `api/src/transport_matters/cli/desktop_cmd.py+_attach_existing_desktop` opens the existing backend and returns.
- Detached reuse branch: `api/src/transport_matters/cli/desktop_cmd.py+run_desktop_detached` calls the same `prepare_desktop_runtime_for_launch_or_exit` helper before it launches a new `_desktop-backend` process and writes `DesktopRuntimeRecord`.
- Existing #180 logic to reuse: `api/src/transport_matters/cli/desktop_recovery.py+prepare_desktop_runtime_for_launch_or_exit` owns the workdir aware live branch. It calls `api/src/transport_matters/cli/desktop_recovery.py+_serves_requested_work_dir` and recovers through `api/src/transport_matters/cli/desktop_recovery.py+recover_desktop_runtime_or_exit` when the recorded live runtime serves another workdir.
- Existing #180 Electron side logic: `desktop/src/main.ts+runtimeServesWorkspace` gates direct Electron reuse, and `desktop/src/desktopRuntime.ts+reclaimDesktopRuntime` calls `_desktop-reclaim`, which routes back to the Python `prepare_desktop_runtime_for_launch_or_exit` seam.
- Discovery gap: `api/src/transport_matters/desktop_runtime.py+discover_desktop_runtime` proves the pid is alive and `/health` responds, then `api/src/transport_matters/desktop_runtime.py+_read_runtime_meta_channel` reads only `/api/meta.channel`. It returns a live status through `api/src/transport_matters/desktop_runtime.py+_status_from_record`, whose `cwd` comes from `DesktopRuntimeRecord.cwd`.
- Live truth source: `api/src/transport_matters/api/v1/meta.py+get_meta` returns the backend cwd from settings, with `TRANSPORT_MATTERS_CWD` winning over process cwd. The reported evidence, `GET /api/meta` returning the old `transport-matters` cwd, is the value the reuse decision does not currently compare.

## Quality Map

- Covered: `api/src/transport_matters/cli/test_desktop_idempotent.py+test_run_desktop_launch_reclaims_live_different_workdir_before_serving` proves foreground launch reclaims a live runtime when the desktop record cwd differs from the requested cwd.
- Covered: `api/src/transport_matters/cli/test_desktop_idempotent.py+test_run_desktop_detached_reclaims_live_different_workdir_before_start` proves the same record based mismatch for detached launch.
- Covered: `desktop/src/main.reclaim.test.ts` includes the Electron direct relaunch case where `desktop/src/main.ts+runtimeServesWorkspace` rejects a live status for another cwd before spawning.
- Missing: no test makes the desktop record cwd match the requested workdir while the live `/api/meta.cwd` reports another workdir. That is the foreground reuse failure mode from the bug report.
- Missing: `api/src/transport_matters/desktop_runtime.py+_read_runtime_meta_channel` cannot expose a live cwd because it parses only `channel`; the shared #180 compare has no live backend cwd to use.
- Verification run during scout: `cd api && uv run python -m pytest src/transport_matters/cli/test_desktop_idempotent.py::test_run_desktop_launch_reclaims_live_different_workdir_before_serving src/transport_matters/cli/test_desktop_idempotent.py::test_run_desktop_detached_reclaims_live_different_workdir_before_start -q` returned `2 passed`.
- Verification run during scout: `cd desktop && pnpm vitest run src/main.reclaim.test.ts` returned `1 passed` file and `2 passed` tests.
- Required final gates after a fix: `just check` and `just test` from the repo root.

## Plan

1. Replace `api/src/transport_matters/desktop_runtime.py+_read_runtime_meta_channel` with a small live meta reader that returns both channel and cwd from `/api/meta`, while preserving the current tolerant failure behavior.
2. In `api/src/transport_matters/desktop_runtime.py+discover_desktop_runtime`, after health is live, validate the live meta channel as today and carry the live meta cwd into the returned `DesktopRuntimeStatus` when present. This lets the existing #180 seam, `api/src/transport_matters/cli/desktop_recovery.py+prepare_desktop_runtime_for_launch_or_exit`, compare requested cwd through `api/src/transport_matters/cli/desktop_recovery.py+_serves_requested_work_dir` without adding a second foreground specific branch.
3. Add a focused foreground regression in `api/src/transport_matters/cli/test_desktop_idempotent.py`: record cwd equals the requested workdir, live meta cwd equals the old workdir, `api/src/transport_matters/cli/desktop_cmd.py+run_desktop_launch` must recover and serve a new plan for the requested workdir instead of calling `_attach_existing_desktop`.
4. Add or adjust a discovery level test in `api/src/transport_matters/cli/test_desktop_runtime.py` so live status cwd follows `/api/meta.cwd` when available. This protects both CLI foreground and Electron direct status readers because `desktop/src/desktopRuntime.ts+readDesktopRuntimeStatus` consumes the JSON emitted from the Python status seam.
5. Leave `desktop/src/main.ts+runtimeServesWorkspace` as the single Electron side workdir gate. Do not add an Electron HTTP probe or a second compare path.
6. Run `just check` and `just test` from the repo root before signoff.
