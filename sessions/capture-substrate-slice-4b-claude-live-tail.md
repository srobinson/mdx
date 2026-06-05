---
title: Capture Substrate Slice 4b — Claude Live-Tail
type: sessions
tags: [backend, capture-substrate, sqlite, tier-2, slice-4b, transport-matters, moe, tailer, live-tail, sse]
summary: The file tailer (crash-safe iterate seam) + the post-COMMIT transcript_turn SSE event + load_runtime wiring; dual MoE sign-off (zero blockers) at 7e6b462.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

# Capture Substrate Slice 4b — Claude Live-Tail

Warroom MoE. Author = backend-engineer (`:3.1`); reviewer = Codex (`:3.2`); orchestrator = `:2.1`.
Branch `feat/capture-slice-4b-claude-live-tail`, tip **7e6b462**, off main (4a merged @ #21). Dual
clean sign-off, **zero blockers** (second consecutive). Completes slice 4.

## Summary / decisions (for slice 5 + 7 + 8)

- **`index/tailer.py`** — `TranscriptTailer` (one poll thread per process, sibling to the writer;
  polls `os.stat` size/mtime on a ~250ms interval, NOT inotify) owning per-session `TailCursor`s.
- **`iter_complete_records(data: bytes) -> (records, consumed)`** is the **ONE record-iterate
  seam** — shared with §11 backfill (closed file) so there's no second path. It advances `consumed`
  only to **just past the last `\n`**; bytes after it (a half-written trailing line) are NOT
  consumed and wait for the next poll (§15 risk-6 crash-safety). Malformed complete lines are
  skipped, not fatal. **Slice 8 backfill calls this same fn.**
- **Poll loop:** per FileTail cursor, stat → if grown, `seek(byte_offset)` + read + iterate →
  per record `adapter.normalize(ctx)` → non-None → `writer.submit(build_transcript_job(turn,
  binding))`. `cursor.seq` = `source_line` = record ordinal (deterministic; re-tail/backfill
  reproduce it). PullSource (opencode) polling is slice 7 (the `isinstance(source, FileTailSource)`
  guard returns early).
- **Registration (read-back, §15 risk 2):** `register_session_cursor(tailer, adapter, binding)`
  (async — `await adapter.locate`) registers a cursor with `byte_offset=0`, so turns written
  before the first wire frame revealed the session_id are caught on the first poll's full read.
  Triggered by `make_index_sink`'s injected `on_binding` callback (load_runtime owns it → ingest
  never imports the tailer, no cycle). `_PROVIDER_CLI = {"anthropic": "claude"}` maps the wire
  provider to the harness cli; codex/gemini/opencode join in slices 5/6.
- **Live event (§9.4):** the **writer** emits, post-COMMIT, each applied `IndexJob.event` via
  `loop.call_soon_threadsafe(broadcast.emit, event)` — the ONLY safe cross-thread bridge (the
  writer is an OS thread; `broadcast.emit` is loop-affine; §15 risk 1). `IndexJob.event` is set by
  `build_transcript_job` = `{type:"transcript_turn", session_id, turn_id, run_id, seq, role, ts,
  is_sidechain, cli, provider}`. Push AFTER COMMIT ties the signal to durability. `IndexWriter`
  takes optional `loop`/`emit` (None in tests → no push); load_runtime binds them to `broadcast.emit`.
- **Wiring + shutdown:** `load_runtime` captures the loop (`_running_loop()`, guarded — returns
  None outside a loop, degraded push), starts the tailer, registers the sink with `on_binding`.
  `close_runtime` stops the **tailer first** (its final drain submits last turns) THEN the writer,
  both off the event loop via `run_in_executor` (they join background threads). `AddonRuntime` gains
  `index_tailer: TranscriptTailer | None`.

## Tests

8 tests vs real temp SQLite + a real asyncio loop: the iterate seam (complete-only + trailing
partial + malformed-skip + closed-file backfill), tailer poll/register/unregister,
`register_session_cursor` (locate + byte_offset=0), and the live `transcript_turn` event
end-to-end (writer thread → `call_soon_threadsafe` → broadcast SSE subscriber, no non-threadsafe
error, seq/turn_id/session_id intact).

## Open Items

- Slice 5 (codex): reuse the §4 port + the tailer's iterate seam + `register_session_cursor`;
  codex `bind` does read-back SYNTH (the synth happens outside the adapter — in ingest/the
  registrar — since adapters import ir only). Add `_PROVIDER_CLI["codex"]`.
- Slice 7: `session_correlated` event (when a NULL `wire_exchange.session_id` is back-filled) +
  opencode PullSource poll path (the `_poll_cursor` PullSource branch).
- Slice 8: backfill calls `iter_complete_records` on closed run-dir files (the shared seam).
