---
title: Capture-substrate slice 8b-i — own the transcript (tier-1 per-session snapshot)
type: sessions
tags: [backend, transport-matters, capture-substrate, slice-8b-i, tailer, storage, dag, moe]
summary: Tee a byte-faithful copy of consumed transcript records into a tier-1 per-session snapshot at capture, via an injected DAG-safe callback; dual MoE sign-off @ 5defc92.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

## Summary

Made tier-1 a complete source of truth for the **transcript** stream. Before this slice, tier-1
held only the wire; the transcript lived only in the CLI's own file (`~/.claude/projects/...`,
`~/.codex/sessions/...`), which the CLI/user can GC — so a tier-2 rebuild lost the entire
transcript half. Fix: tee a **byte-faithful** copy of every consumed transcript record into a new
tier-1 per-session slot at capture, so a future rebuild (8c) replays TM-owned bytes regardless of
CLI retention, `--home-dir`, `source_descriptor`, or `locate`.

Branch `feat/capture-slice-8b-i-transcript-snapshot` @ `5defc92` (off main `5d53a88`), pushed to
origin. Dual MoE sign-off: author backend-engineer:3.1 (claude) + reviewer:3.2 (codex), 2 rounds.
`just ci` green **1175**. Orchestrator gates CI + opens PR; Stuart road-tests a real claude+codex
session before merge.

Key decisions:
- **storage_root IS the run dir** (`workspaces/<slug>/<hash>/<run>/`, holds `index.jsonl`), so the
  snapshot at `<run_dir>/transcripts/<session_id>.jsonl` lands under exactly what `iter_run_dirs`
  (slice 8a) enumerates for the 8c rebuild.
- **Per-session** filename = `session_id` verbatim (claude native uuid / codex synth uuid5 → safe
  filename), so a run dir hosting >1 session keeps them apart and the stem maps 1:1 back.
- **DAG seam**: the index-layer tailer must not import a storage write API. The writer is built in
  the `storage` layer and **injected** as a plain `Callable[[str,int,bytes],None]` at
  `load_runtime()` (mirrors `make_index_sink`). `index/tailer.py` imports zero `storage`.
- **Idempotence via the prefix-copy invariant**: the snapshot is a byte-faithful copy of the CLI
  file's consumed prefix, so its on-disk size IS the prefix length already owned. A re-tail (fresh
  process re-reads from offset 0) appends only `consumed[snap_size - start_offset:]` → never dupes.

## Files changed

- `storage/disk_layout.py` (+15): `transcripts_dir` property + `transcript_snapshot_path(session_id)`.
- `storage/transcript_snapshot.py` (NEW, ~70 LOC): `make_transcript_snapshot_writer(storage_root)`
  → idempotent synchronous prefix-append writer; `TranscriptSnapshotGapError`.
- `index/tailer.py` (+~15): `TranscriptTailer.__init__(..., snapshot=None)` injected writer;
  `_poll_cursor` tees `data[:consumed]` at `cursor.byte_offset` BEFORE the normalize loop; advances
  `cursor.stat_signature` LAST (after snapshot+ingest+byte_offset).
- `addon_runtime.load_runtime`: build the writer over `storage_root`, inject into the tailer ctor
  (None when no disk backend).
- Tests: `storage/test_transcript_snapshot.py` (NEW), `storage/test_disk_layout.py` (+1),
  `index/test_tailer.py` (TestSnapshotTee + 2 blocker probes),
  `tests/integration/test_transcript_snapshot_roundtrip.py` (NEW).

## Behavior / contract

Injected callback `snapshot(session_id, start_offset, consumed_bytes)`:
- Appends only bytes beyond the current snapshot size (`consumed[snap_size - start_offset:]`).
- Empty `consumed` → no-op (no file created).
- `start_offset > snap_size` (gap: file truncated / dir removed mid-run) → **raises**
  `TranscriptSnapshotGapError` (hard failure; never punches a non-prefix hole).
- Per-call `parent.mkdir(exist_ok=True)` recreates `transcripts/` on a benign fresh-start.

Tailer coupling: a snapshot raise propagates to `poll()`'s try/except; `byte_offset` AND
`stat_signature` stay un-advanced, so the next poll retries even on an unchanged CLI file. Tier-1
snapshot and tier-2 turns advance together or neither — tier-2 can never get ahead of an
un-snapshotted hole.

## Review (BLOCKER 1, codex — both parts real, fixed @ 5defc92)

1. **stat_signature ordering**: was set BEFORE snapshot+ingest, so a snapshot throw left
   `byte_offset` un-advanced but the unchanged-file stat guard short-circuited the retry. Fix: set
   it LAST, mirroring `byte_offset`.
2. **gap silent success**: the writer's gap branch logged + returned success, letting the tailer
   advance past un-snapshotted bytes (silent hole). Fix: raise (hard failure).

## Open items

- **Real-run proof is the merge gate** (Stuart): a live `transport-matters claude` AND `codex`
  session → snapshot exists, byte-matches the consumed CLI file, found by `iter_run_dirs`. The
  integration test simulates this over real temp dirs but is not a live CLI run.
- **8b-ii** (next): add `home_dir` to the descriptor + durable owned facts, and bump
  `ADAPTERS_VERSION` — which lands AFTER this slice so the resulting drop+rebuild has the snapshot
  to rebuild from (snapshot-before-schema-bump is the load-bearing order).
- **8c** (later): backfill/rebuild/reconcile replays from this snapshot.
- A true mid-run snapshot gap raises every poll (loud) but does not auto-recover the missing prefix
  (would require re-reading the CLI file from offset 0); acceptable since it only arises on external
  tampering with TM's own run dir.
