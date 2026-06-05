---
title: Activity slice 1b run lifecycle emission
type: sessions
tags: [backend, activity, run-lifecycle, postgres, capture-plane]
summary: Implemented Python capture-plane run lifecycle emission and hardening fixes for review findings.
status: active
source: backend-engineer
confidence: high
created: 2026-07-03
updated: 2026-07-03
---

## Summary

Implemented Transport Matters Activity slice 1b on branch `feat/activity-slice-1b-emit`.

Commits:

- `c7aa41d`: initial capture-plane lifecycle emission.
- `b76139a`: review fix round for M1, M2, M3, and minor findings.

Key decisions:

- Centralized run lifecycle row construction in `transport_matters.run_lifecycle`.
- Reused the slice 1a `run_lifecycle_event` table and shared contract constants.
- Added best effort lifecycle commits to `SessionWriter` with failure counting and exception logging.
- Kept capture operation non-fatal when lifecycle construction or emission fails.
- Kept event construction and sink submission inside the guarded emission path for canvas and detached capture lifecycles.
- Deleted the dead detached lease sink surface from `prepare_captured_run` and `CapturedRunLease`.
- Retained detached `run-started` background tasks through a strong task set until completion, then drained outstanding lifecycle tasks before writer close.
- Documented detached exit `exit_code` and `error` as intentionally unavailable and therefore null.

## API Contract

No new HTTP endpoint was added.

Postgres notification contract:

```typescript
interface RunLifecycleNotifyPayload {
  type: "run_lifecycle";
  run_id: string;
  event_type: "run-started" | "run-exited";
  ts: string; // ISO 8601
}
```

Notifications are delivered on the shared `tm_events` channel after fresh inserts into `run_lifecycle_event`. Duplicate lifecycle rows are idempotent and do not emit duplicate notifications.

## Database Changes

No schema migration was added in this slice. The implementation uses the existing slice 1a table:

- `run_lifecycle_event`
- idempotency boundary: `(run_id, event_type)`
- launch kinds: `canvas`, `detached`
- event types: `run-started`, `run-exited`

Emission points:

- Canvas start: `RunManager._spawn_new_admitted` after run registration.
- Canvas exit: `RunManager._teardown_run` after final state and exit code are set.
- Detached start: capture runtime startup schedules a retained `run-started` lifecycle task when detached launch fields are present.
- Detached exit: capture runtime close drains pending lifecycle tasks, emits `run-exited` with `capture-runtime-closed`, then closes the session writer.

## Security Considerations

- All writes use existing parameterized DAO paths.
- Lifecycle notification payloads include only lifecycle metadata, not raw request or response bytes.
- Emission failures are logged and counted, but never fail or interrupt capture.
- Detached synchronous lease close no longer carries database emission hooks.

## Performance Notes

- Duplicate lifecycle rows rely on the existing idempotent insert path.
- Notifications are emitted only after inserts, avoiding noisy duplicate fanout.
- Run lifecycle row construction reuses existing workspace identity helpers.
- Background detached lifecycle tasks are bounded to lifecycle emission work and discarded on completion.
- Verified no changed file exceeds the project line thresholds.

Verification run:

- `TRANSPORT_MATTERS_TEST_DATABASE_URL=${TRANSPORT_MATTERS_TEST_DATABASE_URL:-postgresql://tm:tm@localhost:55432/postgres} api/.venv/bin/python -m pytest api/src/transport_matters/session/test_run_lifecycle_writer.py api/src/transport_matters/test_run_lifecycle_emission.py api/src/transport_matters/test_addon_runtime.py::test_detached_lifecycle_task_is_retained_until_done api/src/transport_matters/test_addon_runtime.py::test_close_capture_runtime_lifecycle_construction_failure_still_closes -q`: 9 passed.
- `TRANSPORT_MATTERS_TEST_DATABASE_URL=${TRANSPORT_MATTERS_TEST_DATABASE_URL:-postgresql://tm:tm@localhost:55432/postgres} api/.venv/bin/python -m pytest api/src/transport_matters/session/test_listen.py api/src/transport_matters/session/test_foundation.py::test_run_lifecycle_event_insert_is_idempotent api/src/transport_matters/session/test_foundation.py::test_run_lifecycle_event_insert_is_session_decoupled_and_strips_nuls api/src/transport_matters/test_run_manager.py api/src/transport_matters/test_run_manager_lifecycle.py api/src/transport_matters/cli/test_captured_run.py api/src/transport_matters/test_addon_runtime.py -q`: 54 passed.
- `api/.venv/bin/python -m ruff format ...changed files... && api/.venv/bin/python -m ruff check ...changed files...`: passed.
- `fmm generate && fmm validate`: 962 files indexed and validated.
- `just check`: passed.
- `just test`: 1805 passed in 57.77s.
- `just build`: passed at `b76139a`, including embedded inspector and canvas bundles plus Python wheel and sdist.

## Open Items

- Future Activity slices can consume `type: "run_lifecycle"` from `tm_events` and project lifecycle rows into the Activity UI.
- Listener side behavior intentionally remains outside this slice.
