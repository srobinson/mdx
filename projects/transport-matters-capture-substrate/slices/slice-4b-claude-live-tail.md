# Slice 4b — claude live-tail (tailer + transcript_turn event + wiring)

**Goal:** make claude transcripts **live** — a file tailer ingests jsonl appends into tier-2
as they're written, and the writer emits a `transcript_turn` event so the UI learns a turn is
queryable. Completes slice 4 (4a landed the data + DIFF, #21).

**Depends on:** 4a (#21 — adapter port, claude adapter, `build_transcript_job`).
**Unblocks:** slice 5 (codex reuses the tailer), slice 7 (live-tail completion:
`session_correlated` event + opencode poll), slice 8 (backfill reuses the iterate seam).

## Read first (canonical spec)

§9.2 (tailer + `TailCursor`), §9.3 (FileTail iterate seam — the record-iterate fn shared with
§11 backfill), §9.4 (cross-thread `transcript_turn` event), §15 risks 1 (cross-thread emit), 2
(read-back tail startup), 6 (partial-record crash safety). 4a's claude adapter (`bind`/`locate`
→ `SessionBinding` + `FileTailSource`).

## Files (≤700 LOC; functions ≤150)

1. `index/tailer.py` (~260) — `TranscriptTailer` + `TailCursor` (§9.2): one thread per process
   (sibling to the writer), **polls** (not inotify, ~250 ms file). §9.3 FileTail iterate: stat
   size/mtime, seek `byte_offset`, read appended bytes, split on `\n`, parse **complete records
   only**, advance `byte_offset` past consumed, **leave the trailing partial**. Per record →
   `adapter.normalize(record, ctx)` → non-None → `writer.submit(build_transcript_job(turn,
   ctx.binding))`. The record-iterate fn is the ONE path also used by §11 backfill — do not
   write a second.
   - claude cursor registration: **read-back style** — registered after the first wire frame
     reveals `session_id` (4a's claude `bind`/`locate` yields `SessionBinding` + `FileTailSource`
     path). §15 risk 2 one-frame startup lag is acceptable; turns written before registration are
     caught by the cursor's initial `byte_offset = 0` full read.
2. `index/writer.py` — the `transcript_turn` live event (§9.4): after a successful batch
   `COMMIT`, emit `{type:"transcript_turn", session_id, turn_id, run_id, seq, role, ts,
   is_sidechain, cli, provider}` via `loop.call_soon_threadsafe(broadcast.emit, event)`. NEVER a
   direct `broadcast.emit` from the writer thread (§15 risk 1). `session_correlated` event +
   opencode poll = slice 7 (do NOT build here).
3. Wiring: `TranscriptTailer` started in `load_runtime()` (`addon_runtime.py:28-59`), stopped in
   the addon `done()` hook (drain). claude cursor registered on the first wire frame's
   `session_id`.

## Invariants (must not break)

- **FileTail crash-safety:** advance `byte_offset` only past the last `\n`; the trailing partial
  waits for the next poll (§9.3, §15 risk 6). Easy to get wrong — never parse past the last `\n`.
- **Cross-thread:** the `transcript_turn` event ONLY via `loop.call_soon_threadsafe` (the writer
  is an OS thread; §9.4, §15 risk 1). The writer captures the running loop at `load_runtime`.
- **Tailer = one thread per process**, sibling to the writer; poll, not inotify (§9.2).
- **One iterate path:** the record-iterate fn is shared with §11 backfill (growing-file live-tail
  AND closed-file backfill use the same fn — DRY, no second copy).
- **Push after durability:** the live signal is emitted by the WRITER after `COMMIT` (ties the
  push to durability — a §8 query for the turn succeeds the moment the UI hears about it), not by
  the tailer (§9.4).
- #17 privacy; DAG: tailer imports `index`+`storage`+`adapters`; no `storage → index`.

## Acceptance (§13.2; real temp SQLite)

- **live-tail(file):** register a `FileTailSource` cursor on a temp jsonl, append lines → tailer
  consumes complete records, **LEAVES a trailing partial line** (append a partial, assert it is
  NOT consumed until completed), the writer commits, and a `{type:"transcript_turn"}` event
  arrives on `/api/stream`.
- **cross-thread emit:** assert the writer emits via `loop.call_soon_threadsafe` and the SSE
  subscriber receives the event with no "non-threadsafe" error (§9.4).
- **shared iterate seam:** the same record-iterate fn drives a closed-file pass (a minimal
  backfill-style test, or assert the seam is single-sourced).
- **registration:** claude cursor registers on the first wire frame's `session_id`; turns written
  before registration are caught by `byte_offset = 0`.
- `just ci` green.

## Grounding (confirm current)

4a claude adapter (`bind`/`locate`, `FileTailSource`). `broadcast.emit` + `/api/stream`
(`api/v1/stream.py`). `index/writer.py` `IndexWriter` (slice 1) — add the post-commit emit.
`addon_runtime.load_runtime()`:28-59 + the addon `done()` hook (`addon.py`).

## Build order (TDD)

FileTail iterate seam (complete-record + partial-line — the core) → tailer register/poll/submit →
writer post-commit `transcript_turn` event (threadsafe) → live-tail(file) end-to-end test →
`load_runtime`/`done` wiring → cross-thread emit test → privacy/DAG.
