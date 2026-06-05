---
title: Tailer S3a Byte Span Plumbing
type: sessions
tags: [backend, transport-matters, tailer, transcript, provenance]
summary: Implemented S3a byte span plumbing through transcript tailing without writer persistence changes.
status: active
source: backend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

## Summary

Implemented the S3a transcript tailer slice on branch `fix/tailer-s3a-byte-spans`, commit `eacf098`, PR #104. `iter_complete_records` now returns `CompleteRecord` envelopes carrying each parsed record plus relative byte spans and non-empty line index. Live tailing and backfill replay now unwrap records where existing behavior needs raw transcript records while preserving span data for future failure isolation.

## API Contract

No public HTTP API contract changed.

Internal contract changes:

```python
@dataclass(frozen=True, slots=True)
class CompleteRecord:
    record: RawRecord
    byte_start: int
    byte_end: int
    line_index: int

def iter_complete_records(data: bytes) -> tuple[list[CompleteRecord], int]: ...

class RecordProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)
    byte_start: int
    byte_end: int

class EventWrite(BaseModel):
    event: EventRow
    artifacts: tuple[InlineArtifact, ...]
    provenance: RecordProvenance | None = None
```

`CompleteRecord.byte_start` and `byte_end` are relative to the current read buffer. The tailer adds `cursor.byte_offset` exactly once before setting `EventWrite.provenance`.

## Database Changes

No migration. No schema change. No DAO write change.

`event_params` still accepts `EventRow`, and `SessionWriter._commit_batch` still inserts `item.event`, so `EventWrite.provenance` is carried in memory only and is not persisted.

## Security Considerations

No new external input boundary. Malformed complete JSON lines remain skipped and logged, matching previous behavior. The change carries integer byte offsets only, not raw transcript excerpts.

## Performance Notes

The hot path adds one small dataclass envelope per parsed transcript line and one small Pydantic provenance model per emitted event. Raw bytes are not copied beyond the existing consumed snapshot tee. Backfill grep confirmed no production consumer outside `session/backfill.py` submits replay records to the writer today.

## Verification

Observed verification:

- Targeted tests: `8 passed in 0.05s`.
- `cd api && just check`: ruff format and lint completed, mypy reported `Success: no issues found in 350 source files`.
- `cd api && just test`: `1339 passed in 29.66s` against the repo test runner and configured Postgres test database.

## Open Items

S3b remains intentionally unimplemented: quarantine migration, writer savepoint isolation, dead letter insertion, and retry policy are outside this slice.
