# Review — wire-store PR-1 (frozen seam)

- **PR:** #258
- **Branch:** `wire-store-pr1-frozen-seam`
- **Head:** `64a295e` (verified `64a295ecac77521794ecd38da0e7fd9890a7222d`)
- **Base:** `2e33e6e` (`origin/main` merge-base)
- **Spec:** `~/.mdx/projects/tm-http-store-spec.md` §1, §4, §8 PR-1
- **Lenses:** code-review (correctness / contracts) + code-hygiene (duplication / boundaries / sizing)
- **Tree:** pristine (`git status --porcelain` empty) at head on branch
- **CI:** 9/9 green (backend lint/test/package, frontend, frontend e2e, product-plane, desktop, desktop standalone, linux wheel gateway spawn)
- **Local proof:** `uv run pytest` on sink + deleted-path tests → **10 passed**

## Summary

PR-1 delivers the whole blessed frozen surface and nothing else. The sink module becomes an N-subscriber registry with a parallel deleted-event registry; both fan-out with per-subscriber isolation. `emit_exchange_deleted` reaches the deleted registry before the existing SSE broadcast. `addon_runtime._start_session_capture` re-registers the cursor sink through `register_exchange_sink` and teardown uses `clear_exchange_sinks`. No store, schema, observer write path, or out-of-scope capture-plane file is touched. Spec acceptance criteria for PR-1 are met. **Verdict: clean / sign-off.**

## Scope check (e)

| Path | Role |
|------|------|
| `api/src/transport_matters/storage/exchange_sink.py` | Frozen touch #1 — multi-subscriber + deleted event |
| `api/src/transport_matters/exchange_recorder.py` | Frozen touch #2 — `emit_exchange_deleted` → registry |
| `api/src/transport_matters/addon_runtime.py` | Cursor-sink registration via new API (+ clear on close) |
| `api/src/transport_matters/storage/test_exchange_sink.py` | Registry unit tests |
| `api/src/transport_matters/test_exchange_recorder_http_provisional_delete.py` | Deleted sink red→green + real delete path |
| `api/src/transport_matters/test_exchange_recorder_http_provisional_finalize.py` | API rename only |
| `api/src/transport_matters/codex/test_exchange_finalize_sink.py` | API rename only |

**7 files, +169/−54.** Forbidden surfaces absent from the diff: `ir.py`, adapters, `response_parser`, ingest, `pgContracts`, run_lifecycle, `SessionWriter`, wire store modules, migration 0008. Legacy symbols `set_exchange_sink` / `clear_exchange_sink` fully removed from the tree.

## Verification matrix

### (a) Multi-subscriber + isolation + lifecycle

| Claim | Evidence |
|-------|----------|
| Prior single-subscriber semantics preserved | `_sinks` list; one `register_exchange_sink` call at composition; `emit_to_index` still best-effort try/except (now per peer) |
| Fan-out to N | `emit_to_index` iterates `tuple(_sinks)`; test `TestExchangeSink.test_emit_fans_out_to_all_subscribers` |
| Failing peer does not starve others | Independent try/except per sink; test `test_failing_subscriber_does_not_stop_peers` (before + after around `_boom`) |
| Snapshot iteration | `tuple(_sinks)` / `tuple(_deleted_sinks)` so mid-emit mutation does not skip or double-call |
| Orphan handling | No per-subscriber unsubscribe API (by design); process lifecycle pairs register at `_start_session_capture` with bulk `clear_exchange_sinks` in `close_capture_runtime` — same pairing shape as the old single-slot clear. Tests use autouse clear fixtures. |

**Note (non-blocking):** `register_*` is append-only. The old `set_exchange_sink` was replace. Double `load_capture_runtime` / `_start_session_capture` without an intervening `close_capture_runtime` would stack cursor sinks; the prior API would have replaced. Normal process lifecycle (shared_proxy close → clear) is fine. Not a PR-1 acceptance miss; optional hardening is clear-before-register at the composition site or a tokenized unregister later.

### (b) Deleted event reaches every subscriber

| Claim | Evidence |
|-------|----------|
| Parallel registry | `ExchangeDeletedSink`, `_deleted_sinks`, `register_exchange_deleted_sink`, `emit_deleted` |
| Fan-out + isolation | Same `tuple` + try/except pattern; tests `test_deleted_event_reaches_subscriber`, `test_failing_deleted_subscriber_does_not_stop_peers` |
| Empty registry no-op | `test_deleted_without_sinks_is_noop` |

### (c) `emit_exchange_deleted` wiring + real deletion paths

| Claim | Evidence |
|-------|----------|
| Recorder notifies sink | `exchange_recorder.emit_exchange_deleted` calls `emit_deleted(exchange_id, run_id)` **before** SSE `broadcast.emit` (lockstep with tier-1, per §4) |
| Unit path | `test_emit_exchange_deleted_notifies_deleted_sink_registry` |
| Real HTTP delete path | `delete_http_provisional_exchange` → `emit_exchange_deleted` → registry; `test_delete_http_provisional_exchange_notifies_deleted_sink_registry` |
| Codex repair path | `codex/exchange.py` already calls `emit_exchange_deleted` after `storage.delete_exchange`; no recorder change needed there — sink fires via the shared emitter (spec: reached from Codex repair path) |

### (d) Cursor sink not dropped

| Claim | Evidence |
|-------|----------|
| Registration site | `addon_runtime._start_session_capture`: `register_exchange_sink(_make_exchange_cursor_sink(...))` when `binding_for_run_id is not None` |
| Teardown | `close_capture_runtime` → `clear_exchange_sinks()` |
| Wiring-only LOC | `addon_runtime.py` still 646/700; diff is three symbol renames/calls, no nested wrapper |

### (e) / (f)

See scope table and pristine tree above. CI 9/9 green.

## Spec §8 PR-1 acceptance

| Acceptance | Status |
|------------|--------|
| Registry fan-out with per-subscriber failure isolation | Met (code + tests) |
| Deleted event observed by a test subscriber (red before recorder touch) | Met (`test_exchange_sink` deleted suite + recorder notify tests) |
| Existing sink tests pass under new API | Met (renamed set→register / clear→clear_s; behavior coverage retained and extended) |
| No store, no schema | Met |
| Behavior identical with one subscriber | Met on the normal start/close lifecycle |

## Hygiene lens

| Signal | Finding |
|--------|---------|
| LOC | `exchange_sink.py` 76 lines; `addon_runtime.py` 646/700 (wiring only — under threshold) |
| Duplication | `emit_to_index` and `emit_deleted` share the same fan-out/isolate shape. Acceptable at this size; a private `_fanout(sinks, call, log_label)` would DRY if a third event appears. **Nit only.** |
| Dead code / parallel APIs | Old single-slot API fully removed; no dual-path residue |
| Boundaries | `storage` still does not import `session`; dependency inversion preserved |
| Import DAG | Untouched and correct for PR-1 |
| Test shape | Autouse clean fixtures; fan-out and isolation covered for both event kinds; recorder integration for deleted |

## Issues

None open against PR-1 acceptance or the frozen contract.

### Non-blocking observations (not sign-off blockers)

1. **Severity: suggestion** — `exchange_sink.register_exchange_sink` is append-only; a capture restart without `clear_exchange_sinks` stacks subscribers where `set_exchange_sink` replaced. Normal close path clears. Optional: document single-lifetime assumption or clear-before-register at composition when re-entry is possible.
2. **Severity: nit** — duplicated fan-out loops in `emit_to_index` / `emit_deleted`; extract only if a third event lands.

## Verdict

**review: clean** — frozen seam matches §1/§4/§8 PR-1; fan-out isolation, deleted event, recorder wiring, cursor-sink registration, and plane boundaries all hold; tree pristine; focused tests 10/10; CI 9/9.
