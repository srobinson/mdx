# Slice 3 Review — Read Surface + LISTEN/NOTIFY → SSE Live Stream

Reviewer: backend-engineer (build reviewer). One adversarial pass.
PR #36 `feat/session-3-read-sse` @ `58da786` (vs base `0f502ba`, 925/-3, 7 files).

Verdict: **APPROVE with 1 major.** 0 blockers, 1 major (read-path over-fetch), 3 minors. The #1 catch-up race is correct-by-construction (subscribe-first) and directly tested. `cd api && just ci` is green vs Postgres (1248 passed, no skips).

---

## Findings

### Major 1 — `get_events_for_owner` selects `e.*`, over-fetching `raw` (+ `content_tsv`) on the read/stream hot path

`session/dao.py` `_GET_EVENTS_FOR_OWNER_SQL` is `SELECT e.* FROM "event" e JOIN "session" s ...`. `e.*` pulls **every** event column including `raw` (the full transcript record JSON — which, per the slice-2 design, retains inline image **base64** payloads) and the generated `content_tsv` tsvector. Both are then discarded: `SessionEventView.from_row` does `row.model_dump(exclude={"raw"})` (`session_routes.py:86`) and `EventRow` ignores `content_tsv` (default `extra="ignore"`).

This is the sole query behind both read endpoints and the SSE stream (`_load_event_views` → `get_events_for_owner`, up to `STREAM_FETCH_LIMIT=1000` rows/page, re-fired on every NOTIFY). So every listed/streamed event transfers and deserializes a potentially multi-hundred-KB `raw` (base64 images) plus a tsvector, only to drop them. It is also inconsistent with the column discipline elsewhere in the same DAO: `get_events` uses the explicit `_EVENT_COLUMNS`, which deliberately omits `content_tsv`.

Impact: avoidable PG→app bandwidth, memory, and JSON-parse cost on the live hot path — exactly where latency matters. Correctness is fine (`raw` never reaches the client).

Suggested fix: give the read surface a projection that selects only the `SessionEventView` columns (i.e. `_EVENT_COLUMNS` minus `raw`, and never `content_tsv`) — a lightweight read row or an explicit column list in `_GET_EVENTS_FOR_OWNER_SQL`. Keep `e.*`/full `EventRow` only for callers that actually need `raw`.

### Minor 1 — events committed during a listener reconnect window are not re-delivered until the next commit

`SessionEventListener._run` reconnects after a drop (`listen.py:134-156`), and in-flight subscribers survive the drop (they live on the hub, not the listener conn — proven by `test_session_event_listener_reconnects_after_dropped_connection`). But NOTIFYs fired during the ~`reconnect_delay_s` gap (while no `LISTEN` is active) are lost. The SSE handler self-heals on the **next** commit (it reloads from `sent_seq+1`, `_load_signal_views`/`_load_event_views`), so this is only observable if no further event commits for that session. Because the stream emits keepalives across the drop, the browser `EventSource` stays connected and will not auto-reconnect, so the operator's live view silently lags reality until they refetch. Data is durable in PG — this is live-view staleness, not loss.

Suggested fix: on each successful listener (re)connect, publish a synthetic catch-up signal (`last_seq=None`) for active sessions to force a one-shot reload, or add a low-frequency safety reload in the stream loop.

### Minor 2 — startup partial-failure leaves a closed pool on `app.state`, yielding 500 instead of a clean 503

`main.py` `lifespan`: on the broad `except` (e.g. `session_listener.start()` raises after `app.state.session_pool` is already assigned), it closes the pool but does not reset `app.state.session_pool`. `_session_pool` (`session_routes.py:97`) returns the attribute when it is non-`None`, so routes then call `pool.connection()` on a **closed** pool → 500, whereas the `MissingDatabaseConfigError` branch (never assigns the pool) gives the intended 503 "session store unavailable". The hub is also set unconditionally, so SSE connects but never receives live events when the listener failed.

Suggested fix: assign `app.state.session_pool` only after both `pool.open()` and `listener.start()` succeed, and/or reset it to `None` on the except path, so degraded mode is a uniform 503.

### Minor 3 — backpressure drop path is correct but untested

`SessionEventHub.publish` drops on `QueueFull` with a warning (`listen.py:70-78`) — the right call: a bounded per-subscriber queue (`QUEUE_MAX_SIZE=1000`) prevents a slow/stuck SSE client from wedging the shared listener fan-out, and a dropped signal is recovered by the next signal's range-reload. No dedicated test exercises the QueueFull drop + recovery, and a sustained-full queue produces the same silent live-gap as Minor 1 until the next reload. Mechanism is sound; this is a coverage gap.

---

## Verified strengths (the hard checks, in the orchestrator's priority order)

1. **Connect-time catch-up race — correct by construction and tested.** `_event_stream` subscribes to the hub FIRST (`session_routes.py:184`), THEN reads the backlog (`:187`), THEN enters the live loop, deduping by `view.seq > sent_seq` (`:188/:200`) and short-circuiting stale signals (`_load_signal_views` `signal.last_seq <= sent_seq → return`, `:217`). Because subscribe precedes the backlog snapshot, any event committed at/after the snapshot both lands in a later backlog page or fires a NOTIFY that the live loop reloads — no gap window; duplicates are dropped by the seq guard. `test_session_event_stream_backlog_then_live_dedups_race` waits for `subscriber_count==1`, commits seq 1 post-subscribe, double-publishes, and asserts frames `[0,1]` with no third frame (exactly-once). The stream also holds **no** pool connection while idle (one per page/signal), so many SSE clients cannot exhaust the pool — only the single listener conn is long-lived.
2. **Listener lifecycle.** One dedicated long-lived autocommit conn (`_listen_forever`), reconnect-on-drop (`_run` loop, new backend pid asserted), released on shutdown (`aclose` cancels the task; `finally` closes the conn). In-flight subscribers survive a drop (hub-owned queues) and resume post-reconnect. Tests: reconnect (`test_..._reconnects_after_dropped_connection`), close-releases-conn (`test_..._close_releases_connection`), and full-app lifespan releasing the backend pid (`test_app_lifespan_releases_session_listener_connection`, asserts the pid leaves `pg_stat_activity`).
3. **NOTIFY payload is id-only.** `parse_notify_payload` reads only `{type, session_id, first_seq, last_seq}` (`listen.py:167-186`); the SSE side loads event bodies from PG by seq. No fat payload, far under 8000 bytes (`test_writer_notify_payload_is_small_session_range_handle`). Slice-2 `session/writer.py` is **unmodified** (0 diff lines); channels match (`tm_events`).
4. **Owner scoping lives in the DAO.** `get_session_for_owner` (`WHERE owner`), `list_sessions` (`WHERE owner` + optional filters), `get_events_for_owner` (`JOIN session ... WHERE s.owner`) — all parameterized (`%(...)s`), no string concat. List + events + stream all gate on owner (`list_sessions`, `_require_session`, `_load_event_views`). `test_session_routes_are_owner_scoped_and_omit_raw` proves cross-owner reads are hidden and `raw` is omitted from the view.
5. **Backpressure.** Bounded per-subscriber queue + drop-on-full (no listener wedge); subscriber cleanup on disconnect (`finally: subscription.close()` → `hub.unsubscribe`, `session_routes.py:207`), so a disconnected client leaks no subscription.

Standing gates: import DAG clean (server/`api` and `session` import downward only; no `index`/`storage` → `session` back-edge); LOC under 700 (dao 466, routes 260, listen 199); functions well under 150; Pydantic v2 frozen view models; `test_private_import_boundary.py` passes.

## Verification evidence (run vs Postgres `localhost:55432`)

- `ruff format --check` → OK; `ruff check src/` → All checks passed.
- `mypy src/` → Success, no issues in 306 source files.
- `pytest` (full suite) → **1248 passed in 11.16s** (+6 new tests), no skips. CI `ci.yml` retains the `postgres:17` service + `TRANSPORT_MATTERS_TEST_DATABASE_URL`; session/route/listen tests hard-require PG (no skip-guard).

---

## Fix verification @ `a0fcc91` — major + all 3 minors RESOLVED

Engineer pushed fixes; verified the four deltas vs this review. No regression to the catch-up race or listener lifecycle.

- **Major 1 RESOLVED.** `_GET_EVENTS_FOR_OWNER_SQL` now selects an explicit `_EVENT_READ_COLUMNS` list (`e.<col>` minus `raw`, and no `e.*` so no `content_tsv`); new lightweight `EventReadRow` model (no `raw` field) + `_event_read`; `get_events_for_owner` returns `list[EventReadRow]`. `test_get_events_for_owner_returns_lightweight_read_rows` inserts a 200 KB `raw` and asserts `not hasattr(row, "raw")` while `ir` is intact — proving `raw`/`content_tsv` are no longer fetched on the read/stream path.
- **Minor 1 RESOLVED.** `SessionEventHub.publish_catch_up()` pushes a `last_seq=None` signal per active subscriber, called right after `LISTEN` re-arms in `_listen_forever`; `_load_signal_views` treats `last_seq=None` as a full reload from `sent_seq+1`. `test_session_event_stream_catches_up_after_listener_reconnect_gap` terminates the backend, commits an event **in the reconnect gap** (NOTIFY lost), and asserts the stream delivers it after reconnect with no further commit. (The original race test is unaffected — it runs no listener, so the catch-up is a no-op there: no regression.)
- **Minor 2 RESOLVED.** `lifespan` initializes `app.state.session_pool/listener = None`, assigns them only after `pool.open()` + `listener.start()` both succeed, and resets to `None` on the except path. `test_lifespan_listener_start_failure_keeps_routes_unavailable` injects a failing listener and asserts `app.state.session_pool is None` and `GET /api/sessions` → 503 (not 500).
- **Minor 3 RESOLVED.** `test_session_event_hub_queue_full_drop_recovers_on_next_signal` (`queue_max_size=1`) proves drop-on-`QueueFull`, recovery on the next signal, and the warning log.
- **CI green @ `a0fcc91`** vs PG: `ruff format` OK, `ruff check` passed, `mypy src/` clean (306 files), `pytest` **1252 passed** (+4 regression tests), no skips. Scope tight — projection columns, catch-up hook, lifespan ordering, tests; no unrelated changes.

**Slice 3: APPROVED.**
