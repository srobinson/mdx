---
title: B6 Continuation API Implementation
type: sessions
tags: [backend, transport-matters, b6, continuation, api]
summary: Implemented owner scoped continuation launch, lineage binding, idempotent run spawn, and thin resume context for B6.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented the final B6 continuation slice in PR #127 on `feat/b6-continuation`.

Key decisions:

- Continuation stays on `POST /v1/runs` as `continueFromSessionId` plus `idempotencyKey`.
- Parent session validation is owner scoped and returns `session_not_found` for missing or foreign sessions.
- Continuation metadata rides the generic `launch_fields` carrier so Slice 4 `runtime_template` can use the same path.
- Idempotency is process local, matching the process resident run manager.
- Resume context is deliberately thin and Postgres sourced.

## API Contract

```typescript
interface CreateRunRequest {
  cli: "claude" | "codex";
  cwd?: string;
  terminal?: { cols: number; rows: number };
  oscColorReplies?: boolean;
  continueFromSessionId?: string;
  idempotencyKey?: string;
}

interface CreateRunResponse {
  run: Run;
}

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

Continuation semantics:

- `POST /v1/runs?owner=local` validates `continueFromSessionId` under the supplied owner.
- `idempotencyKey` is required when `continueFromSessionId` is present.
- Same idempotency key returns the existing run without re preparing or re minting.
- Distinct idempotency keys can intentionally fork the same parent at the same point.

Launch fields carried:

```json
{
  "continue_from_session_id": "<parent session id>",
  "parent_session_id": "<parent session id>",
  "forked_at_seq": 123,
  "session_purpose": "continuation",
  "resume_context": {
    "firstUserPrompt": "...",
    "lastAgentMessage": "...",
    "transcriptRef": "<parent session id>"
  }
}
```

## Database Changes

No migration was required.

Runtime reads added through `AsyncSessionDao`:

- first visible turn for an owner and optional role
- latest visible turn for an owner and optional role

The existing session upsert COALESCE guards preserve `session_purpose`, `parent_session_id`, and `forked_at_seq` across transcript re polls. A regression test verifies a continuation session is not reset to `user` on re poll.

## Security Considerations

- Parent session lookup is owner scoped. Foreign sessions are indistinguishable from missing sessions.
- Continuation requires an explicit idempotency key, preventing retry induced duplicate child minting.
- Resume context contains only text snippets plus the durable parent Postgres `sessionId`. It never includes local transcript paths.
- `TRANSPORT_MATTERS_RESUME_CONTEXT` reaches the managed child process but is excluded from managed shell environments.
- Public run responses continue to omit internal ports, storage paths, native ids, viewer state, and dead letter counts.

## Performance Notes

Continuation spawn adds bounded indexed Postgres reads at launch time:

- parent session existence
- latest visible parent turn for `forked_at_seq`
- first user turn for context
- latest assistant turn for context

These are one time spawn reads, not per event or per list item. Idempotency returns cached process resident runs without repeating prepare or PTY spawn.

Verification completed:

- `cd api && just check`
- `cd api && just test`
- focused continuation and launch carrier pytest slice with Postgres configured

## Open Items

- Future Slice 4 should attach `runtime_template` to `CreateRunRequest` using the same generic launch field carrier.
- The current resume context is intentionally thin. AI summaries and search on demand remain future product work.
- Frontend resume UX wiring is not part of this backend slice.
