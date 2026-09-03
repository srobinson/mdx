# CPU incident root cause

Investigated 2026-09-05 12:00 to 12:15 local (05:00 to 05:15 UTC) from outside Transport Matters. Read only. Nothing killed, no config changed. One `CREATE INDEX` ran inside a transaction that was rolled back, to measure a plan.

## Verdict

Postgres CPU was consumed by the gateway's per-run activity reconcile pass. Each pass runs `RECORDS_BY_RUN_AFTER_SQL` (`packages/activity/src/adapters/postgresRecords.ts`), which has no usable index on `event.run_id` and therefore joins the entire `session` table and probes the event index once per session on every execution. A caught-up pass that returns zero rows still costs about 50,000 buffer hits and 24 ms.

The pass is doorbell driven. Every live status upsert, transcript batch, wire commit and lifecycle row fires `pg_notify` on `tm_events` (`api/src/transport_matters/session/writer.py`). `ActivityIngestion.markReconcileNeeded` turns each NOTIFY for a materialized run into `ReconcileLoop.request()`. The loop coalesces, so its ceiling is one pass per pass duration, about 40 per second per run. `LiveStatusObserver` writes a latest-wins row per response chunk as fast as the database accepts, so a streaming run keeps the doorbell ringing continuously. Seven streaming runs at roughly 40 passes per second each, 24 ms and 50k buffers per pass, is the 800 to 1200 percent Postgres CPU Stuart observed. The Python capture proxies were the writers feeding it, which is their share of the load.

## Evidence

Measured live with one codex run active (run `b5195f34`, pid 58063):

| sample | value |
| --- | --- |
| pg_stat_activity, 40 samples over 20 s | 40 of 40 active statements were `RECORDS_BY_RUN_AFTER_SQL` |
| `session.seq_scan` delta over 20 s | 1,241 (62 executions per second) |
| `event.idx_scan` delta over 20 s | 475,000 (383 probes per execution) |
| cumulative since stats began | `session.seq_scan` 21.2 million, `event.idx_scan` 6.23 billion |
| same window after the run went idle | 0 executions in 10 s and 0 in 5 s |

EXPLAIN ANALYZE of the statement with the run's current watermark (no new rows):

| plan | buffers | time |
| --- | --- | --- |
| current: Hash Right Anti Join over all 774 sessions, then `event_native_ix` probe per session (765 loops) | 50,049 shared hits | 24 ms |
| with `CREATE INDEX ON event (run_id, session_id, seq)` (rolled back) | 332 shared hits | sub-millisecond |

Postgres log at Stuart's Docker restart (04:53:25 UTC): 82 client connections terminated. Seven had a statement in flight. All seven were this statement.

The pass has no logging on success. The 619 `activity: reconcile pass failed` lines in `~/.transport-matters-preview/runtime/desktop.log` are all from the restart window (`the database system is shutting down`, `Connection terminated unexpectedly`) and cover 4 attempts per run across every materialized run, which shows how many runs a single gateway keeps materialized.

The Python side is not the loop. In the last 5,000 log lines the backend issued 319 `completed-turns` reads and 11 `conversation` reads to the gateway. The #629 resident reconciler (`delivery_resident.py`) is event driven with a 0.25 s coalescing sleep and is not the driver, although its `read_user_messages` walk (limit 1 per page, no LIMIT in the SQL, one query per fragment) is quadratic per pass and worth fixing alongside.

## What the restart did and did not do

Stuart restarted Docker at 04:53 UTC. CPU stayed high because the writers and the doorbell loop reconnected immediately (the gateway `TmEvents` listener reconnects and `handleConnected` re-requests every materialized run). CPU recovered when the agents were closed because the streaming stopped and the doorbells stopped. That matches the observation exactly.

## Desktop close cleanup: not exercised

The desktop was never closed. Electron pid 94194 (started 03:25 local) is still running with four connections to the preview backend. The preview backend (94154), its gateway (94157), the shared proxy (94158) and one live codex run remain. All `addon.py` capture proxies from the audit runs are gone, so run teardown on agent exit worked. The quit chain is `DesktopLifecycle` before-quit, then `graceThenForce` for the gateway and then the Python backend. It has not been tested by this incident and there is no evidence either way.

## Surviving process inventory

| item | finding |
| --- | --- |
| pid 48471, `python3 -`, 100% CPU for 2 days 10 hours | An orphaned heredoc script started from a zsh in the repo directory (stdin was `/private/tmp/zshX3lk2L`, now deleted). The stack is a nested generator doing `os.scandir` over the repo tree, which contains `node_modules` and `.worktrees`. Not Transport Matters. Safe to kill after Stuart confirms; nothing else references it. |
| pids 21327 and 58127, gateway `main.js` | Two stray gateways from earlier backends. Both hold `LISTEN tm_events` connections (four listeners total, two are these). Low load now because they have no HTTP clients, so no materialized runs. Cleanup candidates. |
| 309 `testSupport/origin` node processes | Test fixture origin servers from worktree test runs on Aug 18 to 20, all reparented to launchd, all sleeping. A test harness leak, not a runtime leak. |
| 699 helioy-bus Python processes, 373 launchd-parented node | helioy-bus `bus_server.py`, `proxy.py`, `warroom_server.py` per Claude session, accumulated since Aug 16. Not Transport Matters. |

## Recommended fixes, in order

1. Add a btree index on `event (run_id, session_id, seq)` via a store migration. This alone cuts a caught-up pass from 50k buffers to about 330 and removes the whole-session join.
2. Rate limit the reconcile pass per run. `ReconcileLoop` coalesces but has no minimum interval, so a streaming run runs it back to back. A floor of 100 to 250 ms between passes bounds the cost independent of chunk rate.
3. Rate limit `LiveStatusObserver` emission. Latest-wins per chunk with a NOTIFY per write turns every streamed byte into a database round trip and a gateway pass.
4. Bound `read_user_messages` in `conversation_scan.py`. Fetch a page, not one fragment, and add a LIMIT to `CONVERSATION_STREAM_SQL` or pass the cursor through so each fragment does not re-read the tail of the run.
5. Enable `pg_stat_statements` in `docker-compose.yml` so the next incident can be attributed without a lucky shutdown log.

## Fix (branch `fix/reconcile-pass-cost`)

- Migration `0038_event_run_ix`: index on `event (run_id, session_id, seq)`. A caught-up reconcile pass drops from 50,049 to 332 buffer hits.
- `ReconcileLoop` rests 250 ms before a follow-up pass. Requests raised during the rest coalesce into that one pass; retries keep their own backoff.
- `pg_stat_statements` installed by the migration and preloaded by compose.

Gates: `just check` green, `just test` green (API 4,778 passed), `@tm/activity`, `@tm/space` and `@tm/gateway` green against Postgres.

## SQL audit

Method: `log_statement=all` for the window 05:26 to 05:36 UTC while the full API suite, the JS Postgres suites and Stuart's live preview backend ran. 396 distinct statements captured, 391 explained with `EXPLAIN (GENERIC_PLAN)` against the preview database. Logging was reset afterwards.

Result: 32 statements sequentially scan a table that holds real rows. All but the hot one fall into three groups.

| group | statements | verdict |
| --- | --- | --- |
| test assertions and fixture resets (`SELECT ... ORDER BY` over a whole table, `DELETE ... WHERE launch_kind = 'service'`) | 18 | not production |
| data migrations and wire garbage collection (`UPDATE wire_exchange SET request_kind`, `DELETE FROM wire_blob ... NOT EXISTS`) | 7 | one-off or GC by design |
| production reads over small tables: session list, roster turn and exchange counts, lifecycle sweep, usage limit check | 6 | session (775 rows), run_lifecycle_event (847) and run_live_status (728) cost under 200 plan units per scan; not worth an index at this size |

The live capture also shows the reconcile pass pairing: the lifecycle read and the records read each appeared about 5,950 times in ten minutes with one run active, which is the pass rate the floor now bounds.

One structural note for later: `session_statements.py` builds the workspace predicate as `workspace_slug || '/' || workspace_hash = $n`, used by four roster and session statements. The concatenation defeats `session_browse_ix`. An expression index or a two-column comparison fixes it when session grows past a few thousand rows. Nothing else in the captured set needs an index.
