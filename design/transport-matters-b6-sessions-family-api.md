---
title: Transport Matters B6 Sessions Family API
type: design
tags: [backend, api, b6, sessions]
summary: Typed contract for the curated /v1 sessions route family.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

# Transport Matters B6 Sessions Family API

## Summary

The sessions family moves from `/api/sessions` to `/v1/sessions` as one route family. The legacy `/api/sessions` alias is deleted in the same change. Responses expose product concepts only. Source provenance, native ids, raw bytes, and search internals remain server-side.

## Shared conventions

```typescript
interface ErrorEnvelope {
  code:
    | "invalid_cursor"
    | "invalid_request"
    | "session_not_found"
    | "session_store_unavailable";
  message: string;
  details?: unknown;
}

interface ListEnvelope<T> {
  items: T[];
  nextCursor: string | null;
}
```

All JSON response bodies use camelCase. Error codes remain snake_case. Foreign or non-owner session ids return `session_not_found`.

Cursor pagination uses `limit` plus `cursor`. The cursor encodes and locks the active filter set. Changing filters with a cursor returns `invalid_cursor`.

## Session models

```typescript
type SessionPurpose =
  | "user"
  | "continuation"
  | "internal_summary"
  | "internal_indexing"
  | "internal_eval"
  | "system_maintenance";

type SessionVisibility = "user_visible" | "hidden" | "diagnostic";

interface SessionLineage {
  parentSessionId: string | null;
  forkedAtSeq: number | null;
  forkedAtTurn: number | null;
}

interface Session {
  sessionId: string;
  workspaceId: string;
  title: string | null;
  status: string;
  provider: string;
  cli: string;
  createdAt: string;
  lastActivityAt: string;
  purpose: SessionPurpose;
  visibility: SessionVisibility;
  lineage: SessionLineage;
  turnCount: number;
  inheritedTurnCount: number;
  lastMessagePreview: string | null;
}
```

The `Session` response never includes `nativeSessionId`, `minted`, `sourceDescriptor`, `homeDir`, `workspaceSlug`, `workspaceHash`, `runId`, or `cwd`.

## Transcript event models

```typescript
interface TranscriptResourceRef {
  id: string;
  kind: string;
  label?: string | null;
}

interface TranscriptTextPart {
  type: "text";
  text: string;
}

interface TranscriptToolUseBody {
  kind: "tool_use";
  toolName: string | null;
  input: unknown;
}

interface TranscriptToolResultBody {
  kind: "tool_result";
  toolName: string | null;
  output: unknown;
  isError: boolean;
}

interface TranscriptUserBody {
  kind: "user";
  parts: TranscriptTextPart[];
}

interface TranscriptAssistantBody {
  kind: "assistant";
  parts: TranscriptTextPart[];
}

interface TranscriptWireInjectedBody {
  kind: "wire_injected";
  label: string;
  parts: TranscriptTextPart[];
}

type TranscriptEventBody =
  | TranscriptUserBody
  | TranscriptAssistantBody
  | TranscriptToolUseBody
  | TranscriptToolResultBody
  | TranscriptWireInjectedBody;

interface TranscriptEvent {
  seq: number;
  turnIndex: number | null;
  kind: string;
  role: string | null;
  ts: string | null;
  body: TranscriptEventBody;
  resourceRefs: TranscriptResourceRef[];
}
```

`TranscriptEvent` never includes `nativeTurnId`, `parentNativeId`, `sourcePath`, `sourceLine`, `searchText`, `createdAt`, or raw bytes. The event stream is transcript only, never wire.

## Endpoints

```typescript
// GET /v1/sessions?workspaceId=&purpose=&visibility=&includeInternal=&limit=&cursor=
type ListSessionsResponse = ListEnvelope<Session>;

// GET /v1/sessions/{id}
interface GetSessionResponse extends Session {}

// GET /v1/sessions/{id}/events?fromSeq=&limit=
interface ListTranscriptEventsResponse {
  events: TranscriptEvent[];
  nextFromSeq: number | null;
}

// GET /v1/sessions/{id}/events/stream?fromSeq=
// Server Sent Events, each data envelope is a TranscriptEvent.

type TimelineResponse = unknown; // Existing curated timeline model, with turnIndex on items.

// GET /v1/sessions/{id}/timeline?fromSeq=&limit=
// GET /v1/sessions/{id}/timeline/stream?fromSeq=
// GET /v1/sessions/{id}/resources/{rid}
```

`GET /v1/sessions` defaults to user visible history only. That excludes sessions with `visibility=hidden`, `visibility=diagnostic`, and internal purposes. `includeInternal=true` opts into internal sessions. Explicit `purpose` and `visibility` filters further narrow the result set. `purpose=continuation` is supported.

## Security considerations

All routes are owner scoped. The owner defaults to `local` for local desktop use. Non-owner ids are indistinguishable from missing ids. The server validates cursor filters, page size, and enum query values. No raw transcript bytes or local source paths are returned by the B6 sessions surface.

## Performance notes

Session list projection includes `lastActivityAt`, `turnCount`, `inheritedTurnCount`, and `lastMessagePreview` in the list query. The resume card can render without per-session event lookups.

