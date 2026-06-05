---
title: Transport Matters Drop Resource Locator Spec Review
type: research
tags: [transport-matters, captured-canvas, resources, security, review]
summary: Review of captured canvas file and URL drop spec found two implementation contract gaps around local file content shape and HTTP origin guarding.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-11
updated: 2026-06-11
---

## Executive Summary

Transport Matters plans to support dropping local files and URLs onto the captured canvas by widening existing resource pane refs rather than adding a new pane kind. The design fits the current canvas model, but the filed spec leaves two implementer traps: the local file route response shape does not match the existing resource viewer contract, and WebSocket origin guard parity is underspecified for a same origin HTTP GET.

## Project Metadata

- Project: `transport-matters`
- Areas reviewed: React canvas frontend, FastAPI backend, Electron preload
- Branch at review time: `fix/spawned-terminals`
- FMM coverage: indexed for `api/` and `www/`; `desktop/src/preload.cts` exists but is missing from the fmm index and was inspected directly.
- Verification: no repo edits; `git status --short` was clean before bus reply.

## Architecture

The existing resource pane path is DB backed. `CanvasPaneRef` currently defines a `resource` variant as `{ kind: "resource"; owner: "local"; sessionId: string; resourceId: string }` in `www/src/session-canvas/model/paneRecords.ts:59-79`, with guard validation at `www/src/session-canvas/model/paneRecords.ts:102-134`.

Viewer dispatch is registry owned. `www/src/session-canvas/viewers/registry.tsx:70-75` maps resource refs to `ResourcePane`, builds pane IDs from `sessionId:resourceId`, and titles resources from `resourceId`. Persistence stores pane refs and rebuilds pane records through `titleForRef` in `www/src/session-canvas/model/canvasStore.persistence.ts:51-61`.

`ResourcePane` currently calls `useResourceContent` using the DB ref fields at `www/src/session-canvas/viewers/resource/ResourcePane.tsx:23-29`, then passes the returned typed `ResourceContentResponse` to `resolveResourceContent` at `www/src/session-canvas/viewers/resource/ResourcePane.tsx:46-61`. `resolveResourceContent` dispatches on `kind` values such as `text`, `json`, `image`, and `binary` in `www/src/session-canvas/viewers/resource/resourceState.ts:53-76`.

Backend terminal origin protection is centralized in `terminal_bridge.origin_allowed_for_request`. The HTTP helper delegates to `origin_allowed_from_headers` in `api/src/transport_matters/api/v1/terminal_bridge.py:94-119`; that implementation rejects requests with no `Origin` header and also requires a trusted loopback host on the configured web port via `request_origin_from_headers` at `api/src/transport_matters/api/v1/terminal_bridge.py:150-160`.

## Key Patterns

- The viewer registry is the correct DRY seam for pane identity, title, and render routing. Widening `ResourceRef` there avoids a parallel image pane.
- The resource viewer contract is typed JSON, not raw HTTP bytes. Existing viewers expect frontend model objects such as `ImageContentResponse`, where the image source is either `url` or `bytesBase64`.
- Terminal and run mutation routes already treat origin guarding as a server side dependency, but current production frontend API calls generally use relative same origin paths through `apiUrl` in `www/src/api.ts:29-34`.

## Detailed Findings

### 1. Local file route response shape conflicts with resource viewer dispatch

The spec says `GET /api/local-file?path=...` returns file bytes plus media type, and that media type drives the existing viewer dispatch (`NOTES/captured-canvas/14-drop-resource-locators.md:50-58`, `NOTES/captured-canvas/14-drop-resource-locators.md:98-104`). Current frontend dispatch does not consume arbitrary bytes plus a `Content-Type` header. It consumes `ResourceContentResponse` JSON:

- `ResourcePane` expects `useResourceContent` data and calls `resolveResourceContent` (`www/src/session-canvas/viewers/resource/ResourcePane.tsx:23-29`, `www/src/session-canvas/viewers/resource/ResourcePane.tsx:46-61`).
- `resolveResourceContent` dispatches on `content.kind` (`www/src/session-canvas/viewers/resource/resourceState.ts:53-76`).
- `ImageResourceViewer` needs an `ImageContentResponse` with either `url` or `bytesBase64` (`www/src/session-canvas/viewers/resource/ImageResourceViewer.tsx:13-21`, `www/src/session-canvas/api/resourceContent.ts:53-60`).
- Text and JSON viewers also expect structured fields such as `text`, `value`, and `truncated` (`www/src/session-canvas/api/resourceContent.ts:45-51`, `www/src/session-canvas/api/resourceContent.ts:69-74`).

Actionable correction: define `/api/local-file` as a `ResourceContentResponse` compatible JSON adapter, or explicitly add a frontend byte to resource view adapter. The first option better preserves the existing viewer contract and testing surface.

### 2. HTTP GET origin guard parity needs exact same origin semantics

The spec says the local file GET is origin guarded with the same policy as the terminal WebSocket (`NOTES/captured-canvas/14-drop-resource-locators.md:98-110`). The current helper suitable for WebSocket and mutation routes rejects when `Origin` is absent (`api/src/transport_matters/api/v1/terminal_bridge.py:100-119`). That matters because the packaged UI is served from the same FastAPI app, and frontend API URLs are relative when no base URL is supplied (`www/src/api.ts:29-34`, `api/src/transport_matters/main.py:184-196`).

Actionable correction: specify and test the exact HTTP behavior for the packaged same origin app path. If the route remains `GET`, it should not merely say WebSocket parity. It needs tests that prove the intended app request succeeds and hostile origins fail.

## Dependencies

- FastAPI and Starlette provide HTTP routing, WebSocket routing, CORS middleware, and request headers.
- React, TanStack Query, and xterm drive the canvas resource and terminal panes.
- Electron preload currently exposes `transportMattersDesktop.appName`; the proposed `getPathForFile(file)` bridge would live in `desktop/src/preload.cts`.

## Relevance to Helioy

The spec follows the Helioy preference for avoiding parallel implementations: no new pane kind, no duplicate viewer, no byte persistence. The two corrections preserve that shape by aligning the new path source with the existing typed resource content contract and by making local file access as explicit as the terminal socket guard.

## Open Questions

- Should `/api/local-file` impose the same content size and truncation semantics as DB backed resources, including a `too-large` response, before it reads the whole file?
- Should URL refs be limited to image viewer v1, or should unsupported remote media types render a clear unsupported state instead of a broken image?
