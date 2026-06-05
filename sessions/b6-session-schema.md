---
title: B6 Session Schema Implementation
type: sessions
tags: [backend, transport-matters, b6, session-schema, postgres]
summary: Added purpose and visibility classification to Postgres sessions, then fixed reupsert preservation for continuation and internal sessions.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary
Implemented B6 step 1 on branch `feat/b6-session-schema`, opened as PR #122. Initial commit `a0eab89` added first class session classification for user, continuation, internal, diagnostic, and maintenance sessions. Follow up commit `c9eb053` fixed the review blocker by preserving non default classification across later tailer reupserts.

Key decisions:

- Keep classification values colocated with the session model as `SessionPurpose`, `SessionVisibility`, `SESSION_PURPOSE_VALUES`, `SESSION_VISIBILITY_VALUES`, and `USER_HISTORY_PURPOSE_VALUES`.
- Thread optional classification through `build_session()` and `build_event_batch()` so writer callers can opt into hidden or diagnostic internal sessions without changing endpoint behavior.
- Preserve existing `session_purpose` and `session_visibility` in `UPSERT_SESSION_SQL` with `COALESCE("session".col, EXCLUDED.col)`, matching lineage fields like `parent_session_id` and `forked_at_seq`.
- Keep the migration raw `op.execute` style and reversible through `downgrade()`.

## API Contract
No public endpoint behavior changed in this slice. Existing session read routes continue to return current shapes and owner scoped results.

Internal Python contract added:

```python
class SessionPurpose(StrEnum):
    USER = "user"
    CONTINUATION = "continuation"
    INTERNAL_SUMMARY = "internal_summary"
    INTERNAL_INDEXING = "internal_indexing"
    INTERNAL_EVAL = "internal_eval"
    SYSTEM_MAINTENANCE = "system_maintenance"

class SessionVisibility(StrEnum):
    USER_VISIBLE = "user_visible"
    HIDDEN = "hidden"
    DIAGNOSTIC = "diagnostic"
```

`build_event_batch()` accepts optional `session_purpose` and `session_visibility` keyword arguments. Defaults remain `user` and `user_visible`.

## Database Changes
Added Alembic migration `api/migrations/versions/0004_session_purpose_visibility.py`:

- Adds `session.session_purpose text NOT NULL DEFAULT 'user'`.
- Adds `session.session_visibility text NOT NULL DEFAULT 'user_visible'`.
- Adds `session_purpose_ck` for `user`, `continuation`, `internal_summary`, `internal_indexing`, `internal_eval`, `system_maintenance`.
- Adds `session_visibility_ck` for `user_visible`, `hidden`, `diagnostic`.
- `downgrade()` drops both constraints and both columns.

DAO updates:

- `SESSION_COLUMN_NAMES` includes both fields.
- `UPSERT_SESSION_SQL` inserts both fields and preserves existing classification on conflict.
- `SessionRow` and `ChildSessionRow` validation includes both fields.

## Security Considerations
The slice preserves owner scoped read behavior and does not add public filters or bypasses. The check constraints enforce classification integrity at the database boundary, including raw SQL callers. Hidden and diagnostic sessions are persisted but not surfaced through new API behavior in this PR.

## Performance Notes
The migration adds two small text columns with defaults and check constraints. No new query filters or indexes were added because this slice does not implement curated session listing yet. Existing owner scoped reads remain unchanged.

Verification observed:

- Initial fail first focused test run failed before implementation because `SessionPurpose` did not exist.
- Initial focused classification tests: `3 passed`.
- Initial session test trio: `34 passed`.
- Review blocker fail first: `test_session_upsert_preserves_existing_classification` failed with continuation overwritten to `user`.
- Review blocker focused pass: `test_session_upsert_preserves_existing_classification` passed.
- `cd api && just test src/transport_matters/session/test_foundation.py -q`: `18 passed`.
- Root `just check`: green, with existing www `!important` warnings only.
- Root `just test`: green, including desktop `29 passed`, www `887 passed`, api `1418 passed`.

## Open Items
- Reviewer should re confirm PR #122 after commit `c9eb053`.
- B6 step 3 should consume the exported classification constants for curated session filters.
- Continuation wiring should pass `session_purpose=SessionPurpose.CONTINUATION` and `session_visibility=SessionVisibility.USER_VISIBLE` when it creates child sessions.
- Future diagnostic or internal session APIs should preserve owner scoping and explicit include or visibility filters.
