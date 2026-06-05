---
title: Transcript Canvas Timeline Stream API Contract
type: design
tags: [backend, transport-matters, transcript-canvas, api-contract]
summary: API contract for slice 2 shared live timeline projection stream.
status: active
source: backend-engineer
confidence: high
created: 2026-06-08
updated: 2026-06-08
---

# Transcript Canvas Timeline Stream API Contract

```typescript
// Existing slice 1 types are reused: TimelineItem, ResourceSummary,
// SubagentSummary, SessionHeader. All fields serialize with camelCase aliases.

type TimelineStreamEvent =
  | { kind: "timeline-item"; item: TimelineItem; resources: Record<string, ResourceSummary> }
  | { kind: "subagent-updated"; subagent: SubagentSummary }
  | { kind: "resource-updated"; resource: ResourceSummary }
  | { kind: "session-updated"; session: SessionHeader };

interface TimelineStreamEnvelope {
  id: string;
  revision: number;
  emittedAt: string; // ISO 8601 UTC
  event: TimelineStreamEvent;
}

// GET /api/sessions/{sessionId}/timeline/stream?owner=local&lastSeq=-1
// Response: text/event-stream, each SSE data frame is TimelineStreamEnvelope JSON.
// Stable ids:
// timeline item: timeline:<sessionId>:<seq>
// resource update: resource:<sessionId>:<resourceId>
// subagent update: subagent:<parentSessionId>:<subagentId>
// session update: session:<sessionId>
```

Security: endpoint is owner scoped by the existing session DAO owner filters and returns 404 for non owners. Raw event bytes are not included.
