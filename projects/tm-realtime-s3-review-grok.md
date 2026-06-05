# Adversarial review: PR #264 Slice 3 (realtime-slice3-producer-emit)

**Reviewer:** grok (`transport-matters:general:1:2.3`)  
**PR:** https://github.com/littleorgans/transport-matters/pull/264  
**Branch:** `realtime-slice3-producer-emit` @ `91ed6e8`  
**Tree:** pristine (`git status` clean; no local writes)  
**Verdict:** **CLEAN** — 0 BLOCKER / 0 MAJOR / 0 MINOR

Scope: adversarial READ-ONLY check of the live producer on the frozen capture plane against `~/.mdx/projects/tm-realtime-spec.md` §4.3–4.4 and Slice 3 plan row. No coordination with the other reviewer.

---

## 1. Frozen plane integrity — PASS

### `capture_chunk` byte identity
`response_stream.install_response_tee` appends to the buffer first, invokes `on_chunk` inside `try/except Exception` (log once per flow via `hook_failed`), then **returns the exact `chunk` object**:

```python
def capture_chunk(chunk: bytes) -> bytes:
    ...
    if on_chunk is not None:
        try:
            on_chunk(chunk)
        except Exception:
            if not hook_failed:
                hook_failed = True
                logger.exception(...)
    return chunk
```

`bytes` are immutable; the tee ignores any on_chunk return value. Client forwarding cannot be altered by the observer without changing `capture_chunk` itself.

### Isolation (not a tautology)
- `test_response_tee_isolates_observer_exceptions_and_preserves_forwarding`: raising hook still returns identity chunks, buffer intact, `restore_streamed_response` restores full body.
- Scratch mutation probes: identity assert dies if return were mutated/withheld; isolated exception path preserves return.
- Observer methods used off-tee (`observe_codex_payload`, `finish_flow`, `start_http_flow` setup) are themselves try/except and log only.

### Non-blocking emit
- Capture path: pure reframer + classifier + lock + `asyncio.run_coroutine_threadsafe` only.
- `test_observer_schedules_without_running_writer_io_on_capture_thread`: stubs `run_coroutine_threadsafe`, asserts one schedule and `writer.rows == []` after on_chunk.
- Writer I/O runs on the session loop inside `_drain` → `submit_run_live_status`.

### Tier-1 artifacts
- `test_live_tap_preserves_complete_tier1_manifest_and_bytes`: baseline tee vs live-tapped tee; same body identity; `complete_file_snapshot` equal after `DiskStorageBackend.persist_exchange`.
- `test_streamed_provisional_finalize_matches_buffered_response` still green (streamed vs buffered finalize contract).
- No `ExchangeSink` / `register_exchange_sink` / `emit_to_index` in the observer.

---

## 2. Producer correctness — PASS

### Mid-turn writes + stable generation
- HTTP: `handle_response_headers` stamps `generation=request_state.provisional_exchange_id` into `start_http_flow`.
- Codex WS: `handle_codex_websocket_message` stamps `generation=state.provisional_exchange_id`.
- `_install_tap` skips when `not generation` (identity-incomplete).
- `test_stream_writes_live_row_with_generation_then_abort_clears_it` (real DB): mid-stream `kind=generating` with `generation-db`, then `finish_flow` → `kind=None`, same generation, `closed=False`.

### Subagent exclusion (producer-side)
- `_install_tap`: `track_role == WIRE_TRACK_ROLE_SUBAGENT` → no tap, no schedule.
- Parametrized `test_observer_skips_incomplete_identity_and_subagent_tracks` covers subagent + null generation + null workspace.
- Tee still installs for Tier-1 capture when `on_chunk is None`; only live emit is skipped.

### Deferred-stop coalescing
- Non-terminal `kind=None` → `deferred_stop` slot; start/terminal → `latest` and clears deferred.
- One event-loop yield (`asyncio.sleep(0)`) before taking deferred so a following start supersedes.
- `test_deferred_stop_is_superseded_by_immediate_next_block`: stop+start while first write in flight → `["reasoning", "generating"]` (no intermediate null).
- Latest-wins under load: `test_latest_wins_slot_converges_out_of_order_deltas`.

### Abort / error terminal
- `_finish_tap` emits `LiveStatusFact(kind=None, terminal=True, provider_event="flow_abort")` when stream lacked a classifier terminal.
- Wired in finally of dedicated + shared addons: `response`, `websocket_end`, `error`.
- Terminal facts are never deferred (`fact.terminal` forces `latest`).
- Order fence: older flow abort cannot clobber newer turn (`test_late_old_generation_abort_cannot_supersede_new_turn`).
- `test_addon_error_hook_emits_abort_terminal`: error path → `["reasoning", None]` + `flow_abort`.

---

## 3. Composition / shutdown — PASS

- `LiveStatusObserver` constructed in `_start_session_capture` with same `writer`, loop, `binding_resolver` as `WireStoreObserver`; exposed on `SessionCaptureRuntime` / `CaptureRuntime` / `AddonRuntime.live_status` / `SharedProxyCore.live_status`.
- Shared subprocess: `SharedProxyAddon(..., live_status=self._core.live_status)`.
- **Storage never imports session** (grep clean). Observer is composition-level; no storage import in observer.
- `aclose`: finish remaining taps, set closed, drain `_pending` via `asyncio.gather(..., return_exceptions=True)` — same posture as wire observer.
- Shutdown order in `close_capture_runtime`: **live_status.aclose() before wire_store.aclose()** so generation-close remains final authority when both still have work.

---

## 4. Codex WS — PASS

- Handler: `if live_status is not None and not message.from_client:` before observe.
- Observer: second guard `if from_client or payload is None: return`.
- Payload via shared `codex_websocket_payload` (no reinvented decode).
- `test_codex_observer_ignores_client_frames` + `test_codex_handler_feeds_only_server_frames`.

---

## 5. Dark on consumer — PASS

PR file list is Python-only (addon/runtime/observer/tee/tests/shared_proxy). No `readLiveStatusForRun`, no live `WireCandidate` admission, no machine consumer wiring. Slice 2 fold helpers named `live-reasoning` in activity tests are unrelated fold fixtures, not consumer admission.

---

## 6. DRY / sizing — PASS

| File | LOC | Limit |
|------|-----|-------|
| `live_status_observer.py` | 357 | ≤700 |
| `live_status.py` (slice 2) | 355 | ≤700 |
| `session/writer.py` | 643 | ≤700 |
| `addon_runtime.py` | 683 | ≤700 |
| `addon_handlers.py` | 379 | ≤700 |
| `response_stream.py` | 60 | ≤700 |

Reuses: `IncrementalSseFrames`, `AnthropicLiveClassifier` / `CodexLiveClassifier`, `SessionWriter.submit_run_live_status`, `WIRE_TRACK_ROLE_SUBAGENT`, `codex_websocket_payload`, `complete_file_snapshot` / exchange test support. No parallel classifier or third reframer.

---

## Verification run (this review)

```
pytest test_response_stream.py test_live_status_observer.py \
       test_wire_store_observer.py shared_proxy/test_addon.py
→ 59 passed

pytest test_response_stream_capture.py test_private_import_boundary.py
→ 2 passed
```

DB tests used `TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres`.

---

## Finding inventory

| Sev | Count | Notes |
|-----|-------|-------|
| BLOCKER | 0 | |
| MAJOR | 0 | |
| MINOR | 0 | Spec §4.4 item 4 literally names the pre-existing finalize test "with live emit active"; that test does not install a live tap, but the new complete Tier-1 snapshot test does. Intent covered; not filed as a defect. |

**Verdict: CLEAN**
