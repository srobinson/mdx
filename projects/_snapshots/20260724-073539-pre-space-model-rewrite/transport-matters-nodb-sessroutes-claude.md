---
title: www session_routes consumers (no-DB gate scope)
type: research
tags: [transport-matters, no-db, www, session-routes, session-canvas]
summary: www DOES consume session_routes, but via session-canvas/api/* (not api.ts); 3 functional surfaces, all under the /canvas route.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

# Finding: www consumes session_routes, but NOT through api.ts

**Premise correction.** The brief assumed all wire calls route through
`www/src/api.ts`. They do not. `api.ts` carries only per-run, disk-backed
reads (`fetchExchanges`/`fetchExchange`/`fetchTurnContent`/`fetchPipelineTokens`,
all `runId`-scoped). The `session_routes` cluster routes through a separate
module tree: `www/src/session-canvas/api/*` and `.../stream/*`.

## The 3 mounted consumer surfaces (all under `/canvas`)

1. **Session list / picker** — `useSessions` (`session-canvas/hooks/useSessions.ts`)
   → `listSessions` (`session-canvas/api/sessionClient.ts`) → `GET /v1/sessions`.
   UI: `viewers/session-picker/SessionPickerPane.tsx`, plus launcher
   (`hooks/useLaunchSession.ts`, `api/launchResolution.ts`).
2. **Transcript chat pane** — `viewers/transcript-chat/TranscriptChatPane.tsx`
   → `useSessionEventStream` (`stream/useSessionEventStream.ts`, SSE
   `/v1/sessions/{id}/events/stream`) + `useSessionEvents` (`hooks/useSessionEvents.ts`)
   → `sessionEvents.ts` (`GET /v1/sessions/{id}/events`).
3. **Session resource viewers** — `useResourceContent` (`hooks/useResourceContent.ts`)
   → `loadResourceContent` (`api/resourceContent.ts`) → `GET /v1/sessions/{id}/resources/{id}`.
   UI: `viewers/resource/ResourcePane.tsx` + Text/Json/Markdown/Image/Binary viewers.

## Reachability

No client router. `rootShell.tsx:RootShell` picks the route from
`window.location.pathname` via `session-canvas/route.ts:selectRootRoute`:
`/canvas`→`SessionCanvasRoute`, `/canvas-lab`→`CanvasLabRoute`, else→legacy `App`.
All session_routes consumers live inside the `session-canvas` subtree, so they
mount at **`/canvas`** (and transitively the `/canvas-lab` dev/stress lab). The
**default `/` legacy route does NOT consume session_routes** (it uses api.ts
per-run disk reads, already confirmed DB-independent).

## Not consumed by www (no gate needed)

- `GET /timeline`, `GET /timeline/stream` — zero non-test consumers.
- Bare `GET /v1/sessions/{id}` (single-session detail) — not called.
- `useLocalFileContent` → `loadLocalFileContent` → SOFT `/local-file`, **not**
  session_routes (false positive; same module, different path builder).

## Bottom line

www consumes session_routes (3 functional surfaces), all under the single
mounted `/canvas` route. One "DB required" gate at the canvas route (or at
`RootShell` ahead of the canvas fork) covers every session_routes UI surface.
