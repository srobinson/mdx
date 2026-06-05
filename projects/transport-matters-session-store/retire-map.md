# Retire diff-era capture substrate — removal map

Forward removal on top of HEAD (NOT a history rewrite). `v0.3.0` tags the full
substrate for recovery. The dead/reused boundary runs THROUGH files, so this is a
code refactor, not a commit-level cherry-pick/revert. Primarily executed in
slice 5; the replay-core extraction (item under SEQUENCING) is pulled forward into
slice 2.

## Sequencing (hard rule)

1. Extract the transcript-only replay core: lift `index/rebuild.py:_replay_transcript`
   (+ `iter_complete_records` reuse) into `session/backfill.py:replay_transcript_run`
   yielding `(binding, record, seq, source)` from `sessions.json` +
   `transcripts/<session_id>.jsonl`, with NO wire reads. `rebuild.py:replay_run` is
   wire-coupled and cannot be reused.
2. Add `session/ingest.py:build_event` (the field mapping from
   `index/ingest.py:build_transcript_job`).
3. Retarget `tailer.ingest_records` + `addon_runtime` (load_runtime) to the event
   builder / `SessionWriter`.
4. THEN delete the SQLite modules.

## DELETE (whole files; dead SQLite/block/diff machinery)

`index/blocks.py`, `index/db.py`, `index/schema.py`, `index/writer.py`,
`index/queries.py`, `index/models.py`, `index/rebuild.py` (after extraction),
`index/maintenance.py`, `api/v1/index_routes.py`, and `index/ingest.py` (after
`build_event` extraction).

Tests deleted with their module: `test_blocks.py`, `test_queries.py`,
`test_models.py`, `test_schema.py`, `test_writer.py`, `test_maintenance.py`,
`test_rebuild.py`, `test_boot_replay.py`, `test_transcript.py`, `test_ingest.py`,
`api/v1/test_index_routes.py`.

## KEEP AS-IS (reused by the session store)

`index/adapters/{base,claude,codex,__init__}.py`,
`storage/{transcript_snapshot,session_facts}.py`,
`cli/{launch_profile,codex_session,home_seed,start_cmd,launch_runtime}.py`,
`canonicalization.py`. Tests: `adapters/test_*`, `storage/test_*`, the launch
`cli/test_*`.

## TRIM (intermingled; cut dead, keep reused)

- `index/tailer.py`: KEEP `iter_complete_records`, `TailCursor`,
  `TranscriptTailer`, `register_session_cursor`. CUT the `build_transcript_job`
  import + submit call; stop dropping None records (emit `kind='meta'`).
- `index/ingest.py`: extract `build_transcript_job`'s mapping -> `session/ingest.py:build_event`,
  then delete the file (cut all wire/block/run-facts/sink symbols).
- `index/sessions.py`: KEEP `SESSION_NS` + `synth_session_id`; CUT `upsert_session`.
- `index/rebuild.py`: extract `_replay_transcript` (+ `iter_complete_records` reuse)
  -> `session/backfill.py`, then delete (cut the wire pass + SQLite
  reconcile/rebuild/gate).
- `addon_runtime.py` (load_runtime): KEEP tailer/snapshot/cursor wiring; CUT
  `IndexWriter`, `rebuild_if_stale`, `make_index_sink`, `index_db_path`; inject
  `SessionWriter` + pool.

Tests to trim: `index/test_sessions.py` (keep synth, drop `upsert_session`);
`index/test_tailer.py` (retarget submit assertions off `build_transcript_job` to
the event builder); `index/test_replay_support.py` (keep transcript-replay
support, drop wire-replay support).

## api/CLAUDE.md import-DAG updates

- Rewrite the `index/` paragraph for the new `session/` package: imports `ir` +
  `canonicalization` + the surviving `index/{adapters,tailer,sessions}`; may import
  `storage` read helpers; `storage` never imports `session`; sink injected at
  `load_runtime()`.
- Drop the dead `index (block identity)` clause from the `canonicalization` layer-1
  line.
- `test_private_import_boundary.py` must pass after the cuts.

## Orchestrator decisions (the 4 flagged calls, all the safe option)

1. `canonicalization.py` STAYS (`override_audit` char accounting uses it); delete
   only the block-identity consumer; trim the CLAUDE.md docstring reference.
2. `index/sessions.py` becomes a thin synth-only module (`synth_session_id` +
   `SESSION_NS` live; `upsert_session` dies).
3. The `index_routes.py` `/raw` endpoint dies with the file (it depends on the dead
   `exchange_raw_ref` / wire `raw_dir`; raw fetch is a parked-wire concern).
   FLAG: ensure no live UI affordance silently 404s on `/raw`; re-provide later
   with the wire store.
4. `maintenance.py` goes entirely; re-home its one useful piece (the ~10-line
   tier-1 run-dir glob `iter_run_dirs`) into `session/backfill.py`.
