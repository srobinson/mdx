---
title: Session Store Transcript Ingest
type: sessions
tags: [backend, session-store, postgres, transcript-ingest]
summary: Implemented transcript replay, event mapping, Postgres writer, and review fixes for session-store ingest.
status: active
source: backend-engineer
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

## Summary

Implemented slice 2 on branch `feat/session-2-transcript-ingest` and opened PR #35. Initial implementation landed in commit `13a1f0d`; review fixes landed in commit `1a70b1a`.

Key decisions:

- Added `transport_matters.session.backfill.replay_transcript_run` to replay only transcript snapshots from `sessions.json` and `transcripts/<session_id>.jsonl`.
- Added `transport_matters.session.ingest` as the typed mapping layer from raw transcript records to session events.
- Added `transport_matters.session.writer.SessionWriter` for blocking sync-tail submission onto the server event loop with a Postgres transaction and `pg_notify`.
- Retargeted `TranscriptTailer` to accept an injected record builder and batch submitter while preserving the legacy SQLite `IndexJob` path for old callers.
- Retargeted `load_runtime` to feed the Postgres session writer. The old SQLite writer is no longer fed by live runtime.
- The requested `retire-map.md` path was absent, so the ingest and replay implementation followed `spec-session-store.md` plus the available review guidance.
- Review fixes thread actual `parent_seq` beside `parent_id`, recover transcript cwd during backfill, and preserve an existing non-empty `session.cwd` on upsert.

## API Contract

Internal writer contract, expressed as Python Pydantic v2 models:

```python
class EventWrite(BaseModel):
    event: EventRow
    artifacts: tuple[InlineArtifact, ...]

class EventBatch(BaseModel):
    session: SessionRow
    events: tuple[EventWrite, ...]

class CommitResult(BaseModel):
    ok: bool
    session_id: str
    committed: int
    last_seq: int | None
```

Tailer contract:

```python
def build_event(record: RawRecord, turn: NormalizedTurn | None, ctx: TurnContext) -> EventWrite

def submit_blocking(batch: EventBatch) -> CommitResult
```

`ingest_records` now threads `seq`, `parent_id`, `parent_seq`, and `model` through a local working state, builds one write per raw record, submits the batch, then advances cursor state only after the submit returns.

## Database Changes

No migration was added. The implementation uses the slice 1 session-store schema:

- `session` upserted once per batch.
- `event` upserted by `(session_id, seq)` for idempotent re-ingest.
- `artifact` upserted by content hash.
- `event_artifact` linked in the same transaction as its event.

Turn rows store raw transcript JSONB and normalized IR JSONB. Meta rows store raw JSONB with `ir = NULL`.

The session upsert now uses `COALESCE(NULLIF("session".cwd, ''), EXCLUDED.cwd)` so a replay binding with empty cwd cannot clobber a known cwd. Empty existing cwd can still be filled by a later non-empty replay binding.

## Security Considerations

- Inline artifact capture reads bytes already present in the transcript IR only. It does not read filesystem paths.
- Normalized IR replaces inline image bytes with `{type: "image", artifact_hash, media_type}` pointers.
- Raw transcript JSON remains byte faithful for fork reconstruction.
- SQL writes go through existing DAO parameterization and psycopg JSONB wrappers.
- `submit_blocking` rejects calls from the target event loop to avoid deadlock.

## Performance Notes

- Tailer backpressure is explicit. The sync tailer thread blocks until the Postgres commit returns.
- Session, event, artifact, link, and notify writes occur in one transaction per cursor poll batch.
- Pool opening is lazy. `close_runtime` stops the tailer first, then closes the writer pool.
- Event re-ingest is deterministic and idempotent through `(session_id, seq)` upsert.

## Verification

Observed green verification for final commit `1a70b1a`:

- `TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres .venv/bin/python -m pytest src/transport_matters/index/test_tailer.py src/transport_matters/session/test_ingest.py src/transport_matters/session/test_foundation.py -q`
  - `33 passed in 0.92s`
  - `EXIT=0`
- `TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres just ci`
  - `302 files already formatted`
  - `All checks passed!`
  - `Success: no issues found in 302 source files`
  - `1242 passed in 9.01s`
  - `EXIT=0`
- `fmm validate`
  - `All 478 files are indexed and up to date`
- `git diff --check`
  - no output
- GitHub PR #35 checks all passed:
  - backend lint
  - backend test
  - backend package
  - frontend

## Open Items

- Slice 5 still needs to delete the old SQLite index modules.
- Session-store read APIs are still pending future slices.
- The spec referenced `retire-map.md`, but that file was absent during this slice.
