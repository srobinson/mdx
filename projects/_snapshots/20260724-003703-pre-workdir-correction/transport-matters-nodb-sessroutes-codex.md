# Transport Matters no DB session route consumers

Scope: www React frontend only. Verified with `fmm_list_files`, `fmm_file_outline`, `fmm_read_symbol`, `fmm_dependency_graph`, and exact `rg` endpoint and caller searches.

## API functions that hit session routes

- `www/src/session-canvas/api/sessionClient.ts:listSessions` builds `GET /v1/sessions` through `sessionsPath`, then `www/src/api.ts:requestApiJson`.
- `www/src/session-canvas/api/sessionEvents.ts:listSessionEvents` builds `GET /v1/sessions/{id}/events` through `sessionEventsPath`.
- `www/src/session-canvas/api/sessionEvents.ts:sessionEventsStreamUrl` builds `GET /v1/sessions/{id}/events/stream` through `apiUrl`.
- `www/src/session-canvas/api/resourceContent.ts:loadResourceContent` builds `GET /v1/sessions/{id}/resources/{id}` through `resourceContentPath`.

No www source builds or calls bare `GET /v1/sessions/{id}`, `GET /timeline`, or `GET /timeline/stream`.

## Mounted or reachable consumers

1. `www/src/session-canvas/viewers/session-picker/SessionPickerPane:SessionPickerPane` uses `useSessions`, so it calls `GET /v1/sessions`. It is mounted by default on `/canvas`: `canvasStore.ts:createInitialCanvasModel` seeds the `session-picker`, `registry.ts:renderPaneContent` renders it, and `rootShell.tsx:RootShell` reaches it through `selectRootRoute`.
2. `www/src/session-canvas/hooks/useLaunchSession.ts:useLaunchSession` calls `listSessions`, so it calls `GET /v1/sessions` when `/canvas` launch params include workspace and harness. Mounted by `SessionCanvasRoute`.
3. `www/src/session-canvas/viewers/transcript-chat/TranscriptChatPane:TranscriptChatPane` uses `useSessionEvents` and `useSessionEventStream`, so it calls `GET /events` and `GET /events/stream`. It is reachable from the mounted session picker or launch resolution through `canvasStore.ts:spawnOrFocusTranscript`.
4. `www/src/session-canvas/viewers/resource/ResourcePane:DbResourcePane` uses `useResourceContent`, so it calls `GET /resources/{id}` for database resource pane refs. The registry can mount it, but current visible creation paths found in www create local file or URL refs, not database resource refs.

Bottom line: www does consume session_routes today. Three real mounted or reachable DB backed surfaces need a DB connection gate: session picker and launch lookup, transcript chat, and database resource panes. Disk backed per run exchange reads in `www/src/api.ts:fetchExchanges`, `fetchExchange`, `fetchTurnContent`, and `fetchPipelineTokens` are separate `/v1/runs/{id}/exchanges` paths.
