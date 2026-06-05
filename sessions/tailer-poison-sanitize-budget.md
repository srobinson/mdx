---
title: Tailer Poison Sanitizer and Search Text Budget
type: sessions
tags: [backend, transport-matters, tailer, postgres, session-store]
summary: Added decoded NUL sanitization across session store insert seams and a 256 KiB search_text budget before Postgres insert.
status: active
source: backend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

## Summary

Implemented PR #103 on branch `fix/tailer-poison-sanitize-budget` for the transcript tailer poison-record spin.

Key decisions:

- Added one recursive `strip_decoded_nuls()` helper in `api/src/transport_matters/session/dao_rows.py`.
- The helper removes decoded `\x00` by replacing it with an empty string.
- Applied the helper to session parameter assembly and event parameter assembly before psycopg adaptation.
- Added the same helper to artifact `media_type` binding in both `SessionDao.upsert_artifact()` and `AsyncSessionDao.upsert_artifact()` after review found this text column bypassed event params.
- Added `SEARCH_TEXT_MAX_BYTES = 262_144` in `api/src/transport_matters/session/ingest.py`.
- Capped derived `search_text` on a UTF-8 character boundary and appended `\n[search_text truncated]` when truncation occurs.
- Left large `raw`, `ir`, and artifact bytes untouched except for decoded NUL removal required for Postgres text and JSONB compatibility.

## API Contract

No public API endpoints changed.

Persistence behavior changed at the session store boundary:

```typescript
interface SessionStorePoisonHandling {
  decodedNulPolicy: "remove"; // "\x00" becomes ""
  sanitizedTextColumns: [
    "session.title",
    "session.source_descriptor nested strings",
    "event text params",
    "event.raw nested strings",
    "event.ir nested strings",
    "artifact.media_type"
  ];
  searchTextMaxBytes: 262144;
  searchTextTruncationMarker: "\n[search_text truncated]";
  largeRawIrAndArtifactBytePolicy: "preserve";
}
```

## Database Changes

No schema migration was added.

The existing `event.content_tsv` generated column remains unchanged. The ingest layer now bounds `event.search_text` before insert so `to_tsvector('english', coalesce(search_text, ''))` does not receive oversized derived text.

The existing `artifact.media_type` text column remains unchanged. Its DAO insert parameter is now sanitized before binding.

## Security Considerations

- Input is sanitized at database parameter boundaries, not at read time.
- Sanitization covers sync and async DAOs for session rows, event rows, and artifacts.
- The sanitizer recurses through strings, dicts, lists, and tuples, including nested JSON values and string keys.
- The implementation avoids SQL string construction and keeps existing parameterized queries.

## Performance Notes

- Sanitization is linear in the size of the session, event, or media type payload being persisted.
- `search_text` is capped to 256 KiB before insert, reducing generated tsvector work for large transcript payloads.
- Large `raw`, `ir`, and artifact payloads remain available for later inspection.

Verification:

- Initial TDD fail-before: targeted tests failed with missing sanitizer, Postgres decoded NUL errors, and `ProgramLimitExceeded` for oversized tsvector input.
- Initial targeted pass: 5 targeted tests passed after implementation.
- Initial gates: `cd api && just check` exit 0, `cd api && just test` 1337 passed, exit 0.
- Fix round fail-before: artifact media type tests failed in sync and async DAOs with `psycopg.DataError: PostgreSQL text fields cannot contain NUL (0x00) bytes`.
- Fix round targeted pass: 2 artifact media type tests passed.
- Fix round gates: `cd api && just check` exit 0, `cd api && just test` 1339 passed, exit 0.

Commits:

- `68c6f16` initial sanitizer and budget implementation.
- `8463a14` artifact media type sanitizer fix round.

## Open Items

- S3 bounded retry and poison quarantine remains separate work in the tailer loop.
- S4 tailer health fields on the run view remain later work.
