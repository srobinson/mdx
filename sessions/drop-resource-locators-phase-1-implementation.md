---
title: Drop Resource Locators Phase 1 Implementation
type: sessions
tags: [frontend, transport-matters, canvas, desktop, api]
summary: Implemented Tasks 1 through 5 for file drop resource locators across API, canvas resource refs, terminal paste handles, and desktop preload path resolution.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-11
updated: 2026-06-11
---

## Summary

Implemented the approved Phase 1 build from `NOTES/captured-canvas/14-drop-resource-locators-plan.md`, Tasks 1 through 5, on branch `fix/spawned-terminals`.

Commits:

- `96f3e54` `feat(api): read-only local-file resource content route`
- `edae3b6` `feat(canvas): widen resource refs to path/url locator sources`
- `c97a062` `feat(canvas): resource pane renders path and url locator sources`
- `1f21c67` `feat(canvas): pane-keyed paste handles and locator escaping for terminals`
- `f5112a3` `feat(desktop): expose getPathForFile on the preload bridge`

The working tree was clean after the commits.

## Architecture Decisions

- Added `GET /api/local-file` as an unguarded same-origin GET route that returns the existing `ResourceContentResponse` JSON contract. It reuses `artifact_content_response`, applies an absolute path requirement, rejects directories, and returns typed missing states for unsupported, missing, permission denied, and too large paths.
- Widened `PaneContentRef` resource refs to support three sources: DB resources, absolute local paths, and remote URLs. Dedupe identity is now the locator string for path and URL refs.
- Kept `ResourcePane` as the orchestrator and split source handling into small components so React Query hooks remain unconditional. DB and local file resources share one resolved content rendering path. URL resources synthesize an image response and render directly through `ImageResourceViewer`.
- Added a module scoped terminal paste registry keyed by pane id. `useTerminalSession` registers and deregisters the xterm `paste` handle for mounted terminal backed panes.
- Threaded pane identity through `TerminalPane`, `CapturedRunPane`, and the registry render call so drop handlers can reach the correct terminal without reaching into React internals.
- Extended the Electron preload bridge with `getPathForFile(file)`, backed by `electron.webUtils.getPathForFile`, and declared the optional browser global in `www/src/desktopBridge.d.ts`.

## Performance Notes

No performance optimization was involved. Existing lazy loading of terminal chunks remains intact. The new path content hook uses React Query with `retry: false`, matching the existing resource content behavior and avoiding delayed typed missing states.

Verification run:

- `cd api && uv run python -m pytest src/transport_matters/api/v1/test_local_file_routes.py -v`: 7 passed
- `cd api && just test`: 1316 passed
- `cd www && npx vitest run src/session-canvas/model/paneRecords.test.ts`: 6 passed
- `cd www && npx vitest run src/session-canvas/viewers/resource`: 10 files passed, 63 tests passed
- `cd www && npx vitest run src/session-canvas/viewers/terminal`: 6 files passed, 40 tests passed
- `cd desktop && pnpm test`: 7 files passed, 29 tests passed
- `cd www && npx tsc --noEmit`: passed
- `cd www && npx vitest run`: 103 files passed, 698 tests passed

## Deviations from Spec

- Task 4 also updated `www/src/session-canvas/viewers/registry.tsx` so the lazy `TerminalPane` receives the pane record and can register a paste handle for the real pane id. The plan listed terminal files but the prop thread requires the registry render site.
- Task 5 tests `desktop/src/preload.cts` through a TypeScript to CommonJS VM harness instead of directly importing the `.cts` file. Vitest cannot parse the production `import electron = require("electron")` preload form directly, and the VM harness preserves the production preload contract while allowing bridge assertions.

## Open Items

- Tasks 6 through 8 remain for canvas drop handling, preview pane drop to terminal, and full manual smoke.
- `/canvas-lab` wiring remains out of scope per the implementation plan.
