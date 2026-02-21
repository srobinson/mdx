---
title: ALP-1127 Chat Frontend Iteration 2 Review
type: sessions
tags: [review, am-chat, frontend, sse, react]
summary: Fixed 3 issues in chat frontend - SSE parser event leak, unstable hook, missing GET auth
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Summary

Reviewed 5 commits (ALP-1135 through ALP-1139) comprising the full chat frontend scaffold: Next.js + assistant-ui project, AM runtime adapter with SSE streaming, chat thread components, memory context panel, and settings panel with first-launch flow.

Overall quality is solid. The architecture cleanly separates concerns: typed client, SSE parser, runtime adapter, and composable UI components. Design tokens are used consistently. Accessibility attributes (aria-expanded, aria-controls, role) are present throughout.

## Issues Found and Fixed

### 1. SSE parser event type leakage (sse-parser.ts)

`currentEvent` was declared outside the event block loop and only reset after processing a `data:` line. If a block set `event:` without a matching `data:` line, that event type would contaminate the next block's data interpretation. Per SSE spec, the event type resets at each double-newline boundary.

**Fix:** Added `currentEvent = ""` at the start of each `part` iteration.

### 2. Unstable adapter in useAMRuntime (am-runtime.ts)

`useAMRuntime` called `createAMAdapter(options)` on every render, creating a new adapter reference each cycle. `useLocalRuntime` would receive a different object each render, potentially causing runtime resets.

**Fix:** Added `useMemo` to stabilize the adapter reference across renders.

### 3. Missing auth on GET endpoints (am-client.ts)

The `get()` helper had no `apiKey` parameter, unlike `post()`. The GET endpoints (`amStats`, `amEpisodes`, `amExport`) sent unauthenticated requests. `amExport` returns all memory data, which should support auth.

**Fix:** Added `apiKey` parameter to `get()` and the three GET endpoint functions. `amHealth` left unauthenticated (health checks should not require auth).

## Patterns Observed

- Design token usage via CSS custom properties is consistent across all components. No hardcoded colors except the error red (#ef4444) in setup-card.tsx.
- Module-level Maps (`contextStore`, `queryStore`) for cross-component state. Grows unbounded but acceptable for a chat session lifetime.
- `useAuiState` used correctly for assistant-ui message ID access.
- The `chat-thread.tsx` file was properly deleted per commit message (fmm index is stale).

## Open Items

None. All issues resolved.
