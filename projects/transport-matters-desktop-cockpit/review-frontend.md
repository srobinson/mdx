# transport-matters-desktop-cockpit: frontend review

Single pass adversarial review against `spec-frontend.md`. Prior known deltas from the prompt are excluded.

1. **[P1] Workspace identity claim is false against the actual `workspace_id` implementation**
   - Section 9.4 says workspace identity reuses `workspace_id` slug/hash and that two checkouts of one project share a remembered workspace.
   - The actual `workspace_id` hashes the fully resolved POSIX path. Two checkouts at different paths get different slugs and different hashes.
   - The launcher and layout persistence can only be path scoped unless the backend adds a different repo identity. The spec must either stop promising cross checkout sharing or define the new identity seam explicitly.
   - Evidence: `spec-frontend.md:315-317`, `api/src/transport_matters/workspace.py:45-68`.

2. **[P1] Transcript addressing is missing from `AgentHandle`, and the spec cites a non-existent timeline endpoint**
   - The chat pane and artifact provenance need the transcript timeline and pivot APIs. Section 6.1 cites `GET /api/index/timeline?stream=transcript&with_bodies=true`, but the actual route is `GET /api/index/sessions/{session_id}/timeline`.
   - Section 9.2 defines `AgentHandle` as `{ agentId, kind, baseUrl, webPort, ptyWsUrl, runId }`. That is not enough to call the transcript timeline or pivot routes, both keyed by `session_id`.
   - Add `sessionId` or a resolver from `runId` to native session id, then correct the endpoint citations and cache keys.
   - Evidence: `spec-frontend.md:203`, `spec-frontend.md:307`, `spec-frontend.md:421`, `api/src/transport_matters/api/v1/index_routes.py:108-126`, `api/src/transport_matters/api/v1/router.py:17`, `api/src/transport_matters/main.py:86`.

3. **[P1] The existing SSE reducer drops transcript live events, so chat live append is not actually covered**
   - The spec says chat live append uses the existing SSE stream, and section 8 scopes that stream through `applyExchangeStreamEvent`.
   - The backend already emits durable transcript events with `type: "transcript_turn"` after the index writer commits.
   - The frontend reducer currently handles only `paused`, `paused_tokens`, `exchange`, and `exchange_deleted`. It silently ignores `transcript_turn`, so a transcript pane would never live append through the cited path.
   - Add a typed transcript event branch, scoped transcript query keys, and tests that a committed transcript turn updates the chat pane cache.
   - Evidence: `spec-frontend.md:203`, `spec-frontend.md:264-269`, `api/src/transport_matters/index/ingest.py:347-373`, `www/src/hooks/exchangeStreamEvents.ts:281-290`.

4. **[P1] `AgentBackendProvider` misses direct global store reads outside hooks**
   - Section 8 says components and hooks can keep signatures and read scoped state from context after the provider refactor.
   - `applyExchangeStreamEvent` accepts scoped callbacks, but `applyExchangeEvent` still reads and mutates the module global `useUIStore.getState()` for forwarding state. `ExchangeDetail` also clears selection through the global store on 404.
   - With two agent panes, an event in one pane can still mutate the original singleton even if selectors inside components are replaced.
   - The refactor needs a scoped store API passed through the event context, or a store factory that removes every import of the singleton from reusable pane code.
   - Evidence: `spec-frontend.md:260-277`, `www/src/hooks/exchangeStreamEvents.ts:7-12`, `www/src/hooks/exchangeStreamEvents.ts:253-267`, `www/src/components/ExchangeDetail.tsx:195-219`.

5. **[P1] Artifact provenance conflates transcript turn ids with exchange selection ids**
   - Section 7.2 says an artifact click stores `{ agentId, turnId }`, focuses chat or wire, and sets scoped `useUIStore.selectedId` to the originating turn or exchange.
   - Existing wire UI selection is exchange based. `selectedId` is a string used to match `IndexEntry.id`, and `ExchangeDetail` calls `fetchExchange(id)`. Passing a transcript turn id into that state either fails visibility lookup or fetches `/api/exchanges/{turnId}` and clears selection on 404.
   - The repo already has a correspondence model for `exchange_id` and `turn_id`. Provenance should carry a discriminated target, or pivot a turn id to an exchange id before focusing the wire pane.
   - Evidence: `spec-frontend.md:250-256`, `www/src/stores/uiStore.ts:18-45`, `www/src/app.tsx:57-66`, `www/src/components/ExchangeDetail.tsx:209-219`, `api/src/transport_matters/index/models.py:184-191`.

6. **[P1] The cockpit renderer is not part of the desktop packaging contract**
   - Section 3 places the cockpit build at `www/dist-cockpit/` and says Electron loads it in production.
   - The desktop package script runs `electron-packager .` from `desktop/`, so a sibling `../www/dist-cockpit` directory is outside the packaged app unless an explicit copy or package root change is added.
   - The current package smoke only creates a window and writes `status: "main-window-created"`; it would not catch a missing cockpit renderer asset.
   - Add a packaging step that includes the cockpit build inside the app resources, and extend the smoke to assert the renderer file exists and loads.
   - Evidence: `spec-frontend.md:50-54`, `desktop/package.json:11-18`, `desktop/src/main.ts:189-218`.

7. **[P2] The 60fps claim remains optimistic until the stress harness moves into the slices that introduce motion**
   - Section 11 defines a scripted transition stress harness, but the slice plan puts the broad polish and performance work in F6.
   - F1 already introduces the engine MVP with FLIP, and F2 introduces multi agent layout depth, floating mode, mode switching, focus, zoom, and persistence. Those slices can pass without the frame timing proof that justifies the tech pick.
   - Move the stress harness into F1 for tiled transitions and extend it in F2 for floating mode and zoom. Otherwise the 60fps requirement is only asserted, not proved.
   - Evidence: `spec-frontend.md:327-340`, `spec-frontend.md:374-386`.
