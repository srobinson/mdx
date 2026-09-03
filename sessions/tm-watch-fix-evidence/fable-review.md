# Fable review: watch framing and feed lifecycle

Reviewer: Native Claude (Fable 5.1), read-only, 2026-09-08.
Scope: uncommitted diff on `fix/support-derivation-causes` against `0c6a5755`, plus the three untracked files.
Focused reproduction: `test_sse.py`, `test_watch_stream_failures.py`, `test_activity_stream_framing.py`, `test_watch_corrections.py`, `test_run_proxy_controlplane_observation.py`: 47 passed.

## Verdict

Approve with two minor fixes. The incident is closed at every layer I traced: the Activity parser is uncapped and strict, framing and schema failures reach `ControlPlaneError` as `control_plane_unavailable` with the original message, transient read errors retry inside the registration deadline and surface their cause on expiry, readiness is cleared on Activity disconnect while `initialized` and `completed_positions` survive, shutdown and task death wake every waiter, and a cancelled waiter cancels only its own `Event.wait` future. No caller of the decoder outside Activity changes behaviour: `iter_sse_data_objects` and the default `IncrementalSseFrames()` in `live_status_observer` keep the tolerant policy. No leftover reference to `activity_ready` or `wire_ready` remains.

## Findings

### F1 (Minor, confirmed): `finish()` misses a tail shorter than the `data:` prefix

`sse.py` `IncrementalSseFrames.finish` checks `self._tail.startswith(b"data:")`. A clean upstream EOF that lands inside the first four bytes of a data line leaves a tail such as `b"dat"` and `finish()` returns silently.

Reproduction:

```python
p = IncrementalSseFrames(max_tail_bytes=None, strict=True)
list(p.feed(b'data: {"type":"snapshot","items":[]}\n\ndat'))
p.finish()   # no SseFrameError; tail is b'dat'
```

Impact is low. In `stream_workspace_activity` a transport reset raises `httpx.RequestError` before `finish()` runs, so only a clean EOF mid-line hits this. Suggested check: `if self._strict and self._tail and not self._tail.startswith((b":", b"event:", b"id:", b"retry:"))` or simply any non-empty tail, since a strict object stream has nothing legitimate to leave unterminated.

### F2 (Minor): post-wait drop reports "did not become ready" for a feed that was ready

`watch.py` `_watch_serialized` calls `feed.readiness.wait(...)`, then re-acquires `_registry_lock` and calls `require_ready()` twice more (before the audit write and at commit). A transient Activity drop in either window raises `GatewayUnavailableError("watch event sources did not become ready: <cause>")` immediately, without re-waiting inside the remaining deadline.

Reproduction (state machine only):

```python
r = WatchFeedReadiness(); r.source_ready("activity"); r.source_ready("wire")
await r.wait(timeout_s=0.01)
r.retry("activity", GatewayUnavailableError("connection reset"))
r.require_ready()  # -> "watch event sources did not become ready: connection reset"
```

Failing fast at commit is a defensible choice and the design names it. The message is wrong for that path. Either re-enter `wait()` with the remaining budget, or word the commit-time error as "watch event sources dropped during registration: <cause>".

### F3 (Caveat, design consequence): a failed feed with retained watchers is a zombie

`fail()` is terminal. When the Activity task ends on `GatewayResponseError` (any 4xx from the gateway, a schema failure, or a strict framing failure) while watchers exist, the feed stays in `_feeds` with a dead Activity task. Existing watchers receive no `state_changed`, `needs_you` or `run_started` facts, and the watcher-ended cleanup in `_record_activity_delta` never fires because no terminal delta arrives. Only an explicit `unwatch` or engine close releases the feed. Before this change the loop reconnected forever on any exception, which at least converged after gateway repair.

`test_failed_connected_feed_rejects_later_registration` pins this shape (`is_watching("run-watcher")` stays true). The design accepts it. Two things to verify before relying on it: which 4xx codes the gateway's activity stream route can answer transiently around a restart or grant re-registration (a transient 403 or 404 now kills the feed for the life of its watchers), and whether the operator has any signal that a live watcher is attached to a failed feed beyond the `logger.warning` line.

### F4 (Caveat): one registration can leave two audit rows

`test_shutdown_serializes_after_a_suspended_watch_registration` now expects `actions[-1]` to be `gateway_failed`. The registration wrote `subscribed` before the audit window, then `gateway_failed` after it. A reader of the audit trail must take the latest row for a `(actor, target, verb)`. This is the known audit-before-effect shape already recorded as open; the correcting row is an improvement over the previous silent success, and the test only pins the last row, so it is stated here rather than raised.

### F5 (Caveat): `busy_gateway` message now carries the gateway URL

`service.py` `watch` switched from a fixed string to `str(exc)`. `gateway_unavailable_error` formats `gateway unreachable at {gateway_url}: {exc}`, so a watch principal now sees the loopback URL in `busy_gateway`. `service.py` line 199 already exposes the same string for another operation and the loopback URL is not a secret, so this is consistent rather than new. Two side notes: "unreachable" is the wrong verb for a mid-stream `ReadError`, and line 581 still uses the fixed message, so the service is inconsistent about which operations name a cause.

### F6 (DRY, minor)

- `GatewayUnavailableError("watch event sources stopped during registration")` is constructed at two sites in `watch.py`; a single helper or constant would keep the public message in one place.
- `GatewayResponseError(502, ..., code=CONTROL_PLANE_UNAVAILABLE_CODE)` is built twice in `watch.py` with near identical messages; same remedy.

## Checked and clean

- Concurrency: `_transition` swaps the `asyncio.Event` before setting the old one, so a waiter that re-reads `self._changed` after waking never waits on a stale event. Cancelling a registration inside `wait()` propagates `CancelledError` through `asyncio.timeout` untouched and the `finally` still decrements `pending_registrations`.
- Timeout race: if the deadline cancels the wait in the same tick as the Ready transition, `require_ready()` re-reads the state and returns cleanly.
- Cause preservation: `fail()` keeps the first cause; `_feed_task_done` on a task that already called `fail()` is a no-op, so the 502 fallback never overwrites the original error. `retry()` after `fail()` is ignored.
- `retry()` from Ready keeps the wire source marked ready, so an Activity reconnect alone restores Ready; wire never re-signals and does not need to.
- Baseline and cursors: `_apply_activity_snapshot` on a reconnect (`initialized` set) records deltas and keeps `completed_positions` by identity; `test_reconnect_registration_waits_for_snapshot_and_preserves_baseline` proves it for both a raised drop and a clean stream end.
- Teardown: `_stop_feed` pops the feed before cancelling tasks, and `aclose` sets `_closed` before failing feeds, so `_feed_task_done` never marks a current feed failed on cancellation. Pending registrations decrement under the lock and `_stop_unused_feeds` releases the feed once no watcher holds it.
- Decoder compatibility: non-strict `_sse_data_object` still decodes with `errors="replace"` and returns `None` on bad JSON or a non-object; the added `UnicodeDecodeError` catch cannot fire on that path. `_over_limit` only raises under `strict`, and Activity passes `max_tail_bytes=None`, so no cap applies there.
- Reads boundary: schema failures raise inside the loop and bypass the new `except SseFrameError`; `finish()` runs inside the `try`, so a strict framing failure at EOF is typed; `upstream.aclose()` runs on every path and the framing test asserts it.
- Test support: `FakeGateway.frames` accepting `Exception | None` and `stream_errors` are used only by the new suite; `_engine(start_timeout_s=...)` keeps the default.
