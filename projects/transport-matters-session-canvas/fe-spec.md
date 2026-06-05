# Transport Matters Session Canvas, frontend F1 to F2 spec

Author: frontend-engineer/codex  
Date: 2026-06-06  
Status: draft for FE architect review

## 1. Scope

This spec turns the session store into the new desktop entry surface. `transport-matters desktop` opens a full screen session canvas route. The current wire and exchange UI stays in the repository and remains reachable for development, but desktop launch no longer lands there.

Grounding:

- Authoritative charter: `/Users/alphab/.mdx/projects/transport-matters-session-canvas/CHARTER.md:8-50`, plus terminal decision at `:71-87`.
- Parked cockpit spec to reuse: `/Users/alphab/.mdx/projects/transport-matters-desktop-cockpit-spec.md:431-592`, `:721-897`, `:984-1104`.
- Layout lab charter: `/Users/alphab/.mdx/projects/transport-matters-desktop-cockpit/CHARTER.md:7-49`, `:63-90`, `:104-120`.
- Old FE review findings: `/Users/alphab/.mdx/projects/transport-matters-desktop-cockpit/review-frontend.md:5-48`.
- Shipped session API: `api/src/transport_matters/api/v1/session_routes.py:34-174`, `:177-260`.
- IR blocks: `api/src/transport_matters/ir.py:17-102`.
- Current www entry and data patterns: `www/src/main.tsx:1-23`, `www/src/app.tsx:35-116`, `www/src/api.ts:27-121`, `www/src/hooks/useExchanges.ts:170-193`, `www/src/hooks/useExchangeStream.ts:16-50`, `www/src/lib/queryKeys.ts:1-13`.

## 2. Product invariant

The session canvas is a spatial transcript workbench for one working directory. In F1 and F2, the launched agent stays interactive in the user's terminal. The canvas opens beside that terminal as observability and replay. On open, it shows the session picker and auto resolves the desktop launch run into a live transcript chat pane. Users can then pick other sessions from the same working directory, and many transcript panes can coexist on one canvas.

The layout engine remains content agnostic. It stores pane ids, rectangles, focus, z order, layout mode, and transitions. It never imports session, transcript, wire, or viewer code.

## 3. Domain model and bounded contexts

### 3.1 Domain terms

| Term | Contract | Owner |
| --- | --- | --- |
| Canvas | One screen bound to one working directory. F1 opens the current desktop working directory. The model allows many canvases later. | `session-canvas/model` |
| Workspace identity | `workspace_slug` and `workspace_hash` from the session API. Identity is path scoped by the resolved working directory. No cross checkout sharing claim. | API session store |
| Pane | One movable window on the canvas. Engine state stores `paneId`, rect, z order, focus, and lifecycle. Session canvas state stores `paneId`, `viewerId`, title, and content ref. | `www/src/engine` plus `session-canvas/model` |
| Layout manager | Pure planner that maps pane ids to rectangles and mode state. It delegates rendering to the generic engine. | `www/src/engine` plus `session-canvas/layout` |
| Viewer registry | Maps `viewerId` and `contentRef` to a React renderer. F1 viewers are `session-picker` and `transcript-chat`. | `session-canvas/viewers` |
| Viewer content contract | Viewer receives immutable pane metadata, scoped API helpers, and callbacks for focus, close, spawn, and update. Viewer never mutates engine state directly. | `session-canvas/viewers` |
| Launch context | Desktop supplies or encodes the launched run lookup fields: owner, workspace hash, cli, and optional run id. FE uses them to auto spawn the live transcript pane. | CLI desktop launch |
| Session | API `SessionSummary`, scoped by `owner=local`. | session API |
| Session event | API `SessionEventView`, ordered by `seq`. | session API |

### 3.2 Bounded contexts and module placement

Create the session canvas as a feature module. Keep generic layout code extractable.

```text
www/src/engine/
  index.ts
  types.ts
  reducers/layoutState.ts
  reducers/paneLifecycle.ts
  planners/efficientLayout.ts
  react/LayoutCanvas.tsx
  react/PaneFrame.tsx
  react/SplitHandle.tsx
  react/useCanvasViewport.ts
  perf/frameMeter.ts

www/src/session-canvas/
  SessionCanvasRoute.tsx
  route.ts
  model/canvasStore.ts
  model/paneRecords.ts
  model/spawn.ts
  layout/sessionCanvasPlanner.ts
  api/sessionClient.ts
  api/launchResolution.ts
  hooks/useSessions.ts
  hooks/useSessionEvents.ts
  hooks/useLaunchSession.ts
  stream/sessionEventReducer.ts
  stream/useSessionEventStream.ts
  stream/mapIrToChat.ts
  viewers/registry.tsx
  viewers/session-picker/SessionPickerPane.tsx
  viewers/transcript-chat/TranscriptChatPane.tsx
  viewers/transcript-chat/TranscriptMessage.tsx
  components/CanvasSurface.tsx
  components/PaneWindow.tsx
  components/CanvasCommandBar.tsx
  perf/SessionCanvasStressRoute.tsx
  perf/sessionCanvasStress.spec.ts
```

Rules:

- `www/src/engine/**` may depend on React, Framer Motion, `@use-gesture/react`, and local engine files only.
- `www/src/session-canvas/**` may import engine through `www/src/engine/index.ts` only.
- New session canvas types stay in `www/src/session-canvas/**`. Do not add them to `www/src/types.ts`, already 586 LOC.
- New files stay under 700 LOC. Functions stay under roughly 150 LOC.
- Existing over threshold test file `www/src/components/ExchangeDetail.test.tsx` is not touched by this work.
- F1 adds `framer-motion` and `@use-gesture/react` to `www/package.json`, matching the parked cockpit tech decision. No graph canvas package is added.

### 3.3 Core TypeScript contracts

```ts
export type CanvasId = string;        // workspace_hash in F1
export type PaneId = string;
export type ViewerId = "session-picker" | "transcript-chat";
export type LayoutMode = "floating" | "tiling" | "focus";

export interface CanvasModel {
  id: CanvasId;
  owner: "local";
  workspaceHash: string | null;
  cwd: string | null;
  launch: CanvasLaunchContext;
  layout: EngineLayoutState;
  panes: Record<PaneId, PaneRecord>;
}

export interface CanvasLaunchContext {
  owner: "local";
  workspaceHash: string | null;
  cli: "claude" | "codex" | string | null;
  runId: string | null;
}

export interface EngineLayoutState {
  mode: LayoutMode;
  viewport: CanvasViewport;
  nodes: Record<PaneId, PaneNode>;
  focusedPaneId: PaneId | null;
}

export interface CanvasViewport {
  panX: number;
  panY: number;
  scale: number;
}

// Engine only. No viewer id, title, session id, or content ref.
export interface PaneNode {
  paneId: PaneId;
  lifecycle: "open" | "closing" | "closed";
  rect: WorldRect;
  z: number;
  pinned: boolean;
}

// Session canvas only. Content metadata is keyed by pane id beside the engine node.
export interface PaneRecord {
  paneId: PaneId;
  viewerId: ViewerId;
  title: string;
  contentRef: PaneContentRef;
  chromeState: "default" | "loading" | "error" | "empty";
  createdAt: string;
  lastFocusedAt: string | null;
}

export type PaneContentRef =
  | { kind: "session-picker"; owner: "local" }
  | { kind: "session"; sessionId: string; owner: "local" };

export interface ViewerRegistration<TRef extends PaneContentRef = PaneContentRef> {
  id: ViewerId;
  title(ref: TRef): string;
  canRender(ref: PaneContentRef): ref is TRef;
  render(props: ViewerProps<TRef>): React.ReactNode;
}

export interface ViewerProps<TRef extends PaneContentRef> {
  pane: PaneRecord & { contentRef: TRef };
  canvas: Pick<CanvasModel, "id" | "owner" | "workspaceHash"> & {
    focusedPaneId: PaneId | null;
  };
  actions: PaneActions;
}
```

`ViewerId` is the session canvas vocabulary. The parked cockpit `transcript` pane maps to `transcript-chat`. Future cockpit viewers can register `terminal-tui`, `wire`, `file`, and `image` without changing the engine. The engine accepts only `PaneNode` and `renderPane(paneId)`. The session canvas joins `PaneNode` to `PaneRecord` outside the engine before rendering viewers.

## 4. Route and desktop entry

### 4.1 Route

Add a real app route at `/canvas`.

F1 implementation shape:

- Keep existing `App` and `BrowserAppShell` as the legacy single page UI.
- Add `SessionCanvasRoute` as a sibling entry in `www/src/main.tsx`.
- Route selection reads `window.location.pathname` before rendering:
  - `/canvas` renders `SessionCanvasRoute`.
  - `/` renders the legacy app for direct web development only.
  - `/legacy` may alias the legacy app if backend fallback support is added.
- Add production static fallback for `/canvas` if FastAPI `StaticFiles(html=True)` does not serve SPA paths. Current mounting happens at `api/src/transport_matters/main.py:123-125`, so this must be verified in F1.

### 4.2 Desktop entry

Update the desktop renderer URL seam so `transport-matters desktop` opens `/canvas`.

Grounded current seam: `desktop/src/window.ts:13-15` returns `/` for the hosted renderer. F1 changes that to a route aware helper, for example:

```ts
export function rendererUrlForPort(webPort: number, route = "/canvas"): string {
  return new URL(route, `http://127.0.0.1:${webPort}`).toString();
}
```

The CLI spec owns flag reuse. FE consumes these invariants:

- Desktop `--work-dir` defines the canvas working directory.
- In F1 and F2, the Python `desktop` process stays primary in the terminal and owns the foreground interactive agent.
- Electron does not spawn or own the agent child. It opens the canvas route against the already running web backend.
- The canvas gets enough launch context to run the lookup rule below.

### 4.3 Launch context and auto resolve

F1 consumes a `CanvasLaunchContext` from query params or preload IPC. The preferred web first form is:

```http
/canvas?owner=local&workspace_hash={hash}&cli={agent}&run_id={run_id}
```

Only `owner` defaults to `local`. `workspace_hash`, `cli`, and `run_id` are optional for direct browser development, but desktop launch should provide them when available.

On open, the route starts the launched run resolver:

```http
GET /api/sessions?owner=local&workspace_hash={hash}&cli={agent}&limit=50&offset=0
```

Resolution algorithm:

1. Keep the picker pane visible immediately.
2. Poll the lookup while no matching row exists.
3. Prefer the row whose `run_id` equals launch `runId`.
4. If no `runId` is available, choose the newest active row for the same `workspace_hash` and `cli`.
5. While waiting, show a non blocking pending state in the picker: `Waiting for live {cli} session`.
6. When a row appears, spawn or focus `transcript:${session_id}`.
7. Continue normal transcript backlog and SSE handling for that pane.

The picker browses other sessions in the same working directory. Direct browser development without `workspace_hash` may show all local sessions.

## 5. Canvas surface

### 5.1 DOM transform model

The canvas uses DOM nodes, not a pixel canvas. The surface has three layers:

1. Viewport layer: fills the route, owns pointer and keyboard events.
2. World layer: a single transformed DOM element.
3. Pane layer: absolutely positioned pane windows rendered as real React components.

Transform contract:

```ts
screenX = worldX * scale + panX;
screenY = worldY * scale + panY;
worldX = (screenX - panX) / scale;
worldY = (screenY - panY) / scale;
```

`CanvasViewport` stores `panX`, `panY`, and `scale`. The world layer applies one compositor transform:

```css
transform: translate3d(var(--canvas-pan-x), var(--canvas-pan-y), 0) scale(var(--canvas-scale));
transform-origin: 0 0;
```

Gestures:

- Drag empty canvas: pan.
- Wheel with modifier or trackpad pinch: zoom around the cursor using the inverse transform above.
- Double click a pane header: focus the pane.
- Keyboard equivalents exist for pan, zoom, focus, close, and mode switching.

CSS values must come from tokens in `www/src/index.css` or the extracted `www/src/styles/tokens.css`. New canvas tokens should be named, not inlined in components.

### 5.2 Accessibility surface

- Route root uses `role="application"` only if keyboard handling would otherwise conflict with terminal style shortcuts. Otherwise use semantic regions.
- Canvas body is labelled by workspace and current mode.
- Command bar uses the APG toolbar pattern with roving focus.
- Panes are labelled regions: `aria-label="{title}, {viewer label}, {state}"`.
- Focus never disappears after spawn, close, drag, resize, layout change, or reconnect.
- `prefers-reduced-motion` replaces FLIP with an immediate rect update plus a short opacity transition.

## 6. Floating pane window system

### 6.1 Lifecycle

F1 pane lifecycle:

1. `spawnPane(ref, options)` creates a stable `paneId`.
2. Layout planner assigns a rect and z order.
3. Pane renders with `chromeState="loading"` until viewer data resolves.
4. `focusPane(paneId)` raises z, updates focus, and moves DOM focus to pane heading.
5. `movePane` and `resizePane` update world rects in floating mode.
6. `closePane` marks `closing`, plays reduced or normal exit motion, then removes the pane.

Spawn rules:

- The picker pane is mounted immediately and remains the stable browsing surface.
- Desktop launch auto resolution may spawn the live transcript pane without a picker click.
- Selecting a session uses pane id `transcript:${session_id}`.
- If that pane exists, selection focuses it and does not spawn a duplicate.
- If absent, selection spawns a `transcript-chat` pane and focuses it after FLIP completes.

### 6.2 Pane component contract

`PaneWindow` owns session canvas chrome. It composes the engine `PaneFrame`, which owns only geometry, motion, focus envelope, and pointer gesture plumbing. `PaneFrame` has no title, viewer badge, `viewerId`, `contentRef`, or session import.

```tsx
<PaneFrame node={node} focused={focused} onFocus={focusPane}>
  <PaneWindow pane={pane} onClose={closePane}>
    {viewer.render(viewerProps)}
  </PaneWindow>
</PaneFrame>
```

`PaneWindow` responsibilities:

- Header, title, viewer badge, status, close action, drag handle, resize handle.
- Default, hover, active, focus visible, disabled, loading, error, and empty states.
- Keyboard close, focus, move, and resize affordances.
- `role="separator"` resize handles with `aria-orientation`, `aria-valuemin`, `aria-valuemax`, and `aria-valuenow` when in tiling mode.

Viewer responsibilities:

- Data fetch and render states inside its content area.
- No direct layout mutation.
- No direct global store mutation.
- No direct `fetch` calls. Use session client hooks.

## 7. Layout manager

### 7.1 Modes

F1 ships:

- `floating`: panes live in world coordinates. Auto realign runs after spawn and close for unpinned panes.
- `focus`: one pane occupies the readable work area; other panes become keyboard reachable rails.

F2 ships:

- `tiling`: tmux like split tree with rows, columns, focus, resize handles, and presets.
- Mode transitions between `floating`, `tiling`, and `focus`.

The generic engine keeps the parked cockpit conventions: n ary split tree, opaque pane ids, pure reducers, stable `layoutId`, and boundary lint.

### 7.2 Most efficient layout planner

`planEfficientLayout(input)` is deterministic and content agnostic. It accepts pane ids, current rects, viewport size in world units, mode, focused pane id, and pinned pane ids. It returns pane rects and transition metadata.

Candidate layouts:

1. Balanced grid.
2. Single row.
3. Single column.
4. Main plus side stack, weighted toward the focused pane.
5. Focus with dock rails.

Scoring:

```ts
score = overflowPenalty
  + emptyAreaPenalty
  + aspectPenalty
  + movementPenalty
  + focusPenalty
  + overlapPenalty;
```

Tie breakers:

1. Preserve focused pane size.
2. Preserve creation order.
3. Prefer fewer rows for two or three panes.
4. Prefer balanced grid for four or more panes.

Spawn algorithm:

- Add new pane after the focused pane in logical order, or after picker when no transcript pane is focused.
- Keep pinned panes at their manual rects.
- Score only unpinned panes against available world bounds.
- Apply the winning plan to unpinned panes.
- Focus the new pane after transition completion.

Close algorithm:

- Remove the closing pane from scoring after its exit animation starts.
- Compact unpinned panes with the same planner.
- Focus the nearest pane by rect center. If none exists, focus the picker.

Tiling algorithm for F2:

- Store n ary split nodes with `children[]` and `sizes[]` fractions.
- Spawn into the focused leaf. Use the axis with more available space. If the parent has that axis, insert a sibling. Otherwise wrap the leaf in a new split.
- Close prunes the leaf, normalizes sibling sizes, and collapses single child splits.
- Presets call pure reducers, never remount viewer content.

### 7.3 FLIP transition system

Every pane has stable `layoutId={paneId}`. Transition sequence:

1. Measure current rects.
2. Compute next rects.
3. Apply next state.
4. Invert using the measured delta.
5. Play transform and opacity only.
6. Clear `will-change` after completion.

Performance rules from the parked spec stay binding:

- Never animate width, height, top, left, grid tracks, or scroll position.
- Viewer content is memoized by `paneId` and does not re render on layout only changes.
- Live stream appends update transcript content state, not engine state.
- Pan and zoom mutate one world layer transform.
- Size dependent work runs after `onLayoutAnimationComplete`.

### 7.4 60fps proof

The stress harness moves into F1.

F1 stress route:

- Route: `/canvas?stress=1`.
- Synthetic viewers render stable memoized content with the same chrome and layout wrappers as production panes.
- Test drives spawn, close, focus, drag, resize, pan, and zoom across 1, 2, 4, 8, 16, and 30 panes.
- `FrameMeter` records `requestAnimationFrame` deltas during each transition.
- Local pass target: p95 frame delta at or below one 60fps frame for normal motion on target hardware.
- CI pass target: bounded regression threshold, plus no layout thrash warnings from the harness.

F2 extends the same harness for tiling preset switches and `floating` to `tiling` mode switches. A slice cannot pass if it introduces motion without updating the harness.

## 8. Viewer registry

### 8.1 Registry contract

`viewerRegistry` is content agnostic and local to the session canvas feature in F1. It follows the parked cockpit seam so future artifact viewers can move beside it.

```ts
export function registerViewer(viewer: ViewerRegistration): void;
export function resolveViewer(ref: PaneContentRef): ViewerRegistration;
```

F1 viewers:

- `session-picker`: renders a session list and spawns transcript panes.
- `transcript-chat`: renders backlog and live events for one session.

F2 viewers:

- No new content viewer required. F2 hardens layout, focus, and pane shell. It leaves TUI, wire, file, and image as F3 seams.

Future seam:

- Add `ContentRef = { uri; mime; inlineText?; provenance? }` for file and image viewers.
- Add provenance keys exactly as `session_id` and `turn_id`.
- Reuse parked artifact policy: dedupe to update, no focus theft, artifact zone, pin, dismiss, auto retire.

## 9. Session picker pane

### 9.1 API contract

Call:

```http
GET /api/sessions?owner=local&workspace_hash={hash}&limit=50&offset=0
```

Available filters:

- `workspace_hash`
- `provider`
- `cli`
- `status=active|completed|archived`
- `limit`, max 500
- `offset`

Response fields:

```ts
export interface SessionSummary {
  session_id: string;
  provider: string;
  cli: string | null;
  run_id: string;
  cwd: string;
  workspace_slug: string;
  workspace_hash: string;
  native_session_id: string | null;
  minted: boolean;
  source_descriptor: Record<string, unknown> | null;
  home_dir: string | null;
  owner: string;
  status: string;
  title: string | null;
  parent_session_id: string | null;
  forked_at_seq: number | null;
  started_at: string;
  created_at: string | null;
  updated_at: string | null;
}
```

Grounding: `api/src/transport_matters/api/v1/session_routes.py:34-59`, `:111-133`.

### 9.2 Data hooks and launched run resolver

```ts
sessionsKey({ owner, workspaceHash, filters });
useSessions({ owner: "local", workspaceHash, status, provider, cli });
launchSessionKey({ owner, workspaceHash, cli, runId });
useLaunchSession({ owner: "local", workspaceHash, cli, runId });
```

Rules:

- Use TanStack Query.
- Use the central API transport pattern from `www/src/api.ts:27-57`.
- Add session query keys to `www/src/lib/queryKeys.ts`. Keep one query key registry.
- Server data stays in Query cache. UI state stays in the canvas store.
- `useLaunchSession` is a narrow polling hook over `GET /api/sessions?owner=local&workspace_hash={hash}&cli={agent}`.
- `useLaunchSession` returns `{ status: "pending" | "resolved" | "unavailable"; session?: SessionSummary }`.
- Pending is expected during startup because the transcript row can appear after the canvas route renders.
- When resolved, the route calls the same `spawnOrFocusTranscript(session)` path used by the picker.

### 9.3 UI states

Default:

- List sessions newest first, matching DAO ordering.
- Row content: title fallback, provider, cli, status, cwd, started time, and native session id when available.
- In desktop launch, filter to the canvas `workspace_hash`.
- In direct browser development without launch context, list all local sessions and label their workspace.
- Mark the auto resolved launch session as live when present.

Loading:

- Show skeleton rows inside a stable pane height.

Error:

- Inline error with retry. No global route failure.

Empty:

- Show a concise message and a `Refresh` action. If launch resolution is pending, show `Waiting for live {cli} session`. Do not invent sessions.

Interaction:

- Keyboard arrows move active row.
- Enter spawns or focuses the transcript pane.
- Pointer click does the same.
- Existing transcript pane for the session focuses rather than duplicating.

## 10. Transcript chat pane

### 10.1 Backlog API contract

Call:

```http
GET /api/sessions/{session_id}/events?owner=local&from_seq=0&limit=500
```

Supported params:

- `owner`, default `local`.
- `from_seq`, inclusive.
- `to_seq`, inclusive when supplied.
- `limit`, max 1000.

Response:

```ts
export interface SessionEventListResponse {
  events: SessionEventView[];
  next_from_seq: number | null;
}

export interface SessionEventView {
  session_id: string;
  seq: number;
  kind: "turn" | "meta";
  native_turn_id: string | null;
  parent_native_id: string | null;
  parent_seq: number | null;
  run_id: string;
  provider: string;
  cli: string;
  role: string | null;
  is_sidechain: boolean;
  ts: string | null;
  model: string | null;
  ir: Record<string, unknown> | null;
  source_path: string | null;
  source_line: number | null;
  search_text: string | null;
  created_at: string | null;
}
```

`raw` is omitted by the API. Do not add a raw byte fetch to this route.

Grounding: `api/src/transport_matters/api/v1/session_routes.py:62-94`, `:136-156`.

### 10.2 Backlog loading

Use an infinite query:

```ts
sessionEventsKey({ owner: "local", sessionId });
```

Algorithm:

1. Fetch from `from_seq=0`.
2. Append pages ordered by ascending `seq`.
3. Continue while `next_from_seq` is non null.
4. Store derived display state keyed by `${session_id}:${seq}`.
5. Do not key transcript state by array index, title, run id, or native turn id.

### 10.3 Live append SSE

Endpoint:

```http
GET /api/sessions/{session_id}/events/stream?owner=local&last_seq={highestSeq}
```

SSE behavior from source:

- Backend subscribes before it loads catchup events.
- Backend sends persisted events from `last_seq + 1`.
- Backend only yields events with `seq > sent_seq`.
- Backend sends keepalive comments when idle.
- Frames are `data: {SessionEventView JSON}` with no SSE `id` field.

Grounding: `api/src/transport_matters/api/v1/session_routes.py:159-174`, `:177-207`, `:210-221`, `:259-260`.

Frontend stream algorithm:

1. Open EventSource after the first backlog page resolves, using highest known `seq`, or `-1` when none exists.
2. Parse only `message` data frames. Ignore comment keepalives.
3. Validate `session_id` matches the pane session.
4. Drop any event with `seq <= highestSeqBySession[session_id]`.
5. If `seq === highestSeq + 1`, append to cache and advance cursor.
6. If `seq > highestSeq + 1`, fetch `GET /events?from_seq={highestSeq + 1}&to_seq={seq - 1}`, merge missing events, then append the live event.
7. On `error`, set stream state to reconnecting and call `es.close()` before any reconnect attempt.
8. Construct a fresh EventSource with `?last_seq={highestSeqBySession[session_id]}`. Do not rely on native EventSource retry, because the server emits no `id:` field and native retry would reuse the original stale cursor.
9. On reconnect open, the backend catchup frames are the catchup signal. Clear reconnecting after the first data frame or after a successful backfill GET.
10. On pane close, close only that pane's EventSource.

Do not reuse `www/src/hooks/exchangeStreamEvents.ts`. It handles exchange stream events and still depends on exchange era state. The transcript stream needs a new reducer scoped by `session_id` and `seq`.

### 10.4 IR to chat mapping

Persisted `event.ir` is a `NormalizedTurn` JSON dump, not an `InternalRequest` or `InternalResponse` envelope. Grounding: `build_event` stores `_turn_ir(turn)` on turn events at `api/src/transport_matters/session/ingest.py:75`, `:92`; `_turn_ir` calls `turn.model_dump(mode="json")` at `:122-141`; `NormalizedTurn` defines `role` and `parts` at `api/src/transport_matters/index/adapters/base.py:134-152`. `EventKind` is exactly `turn | meta` at `api/src/transport_matters/session/models.py:16-18`; meta events set `ir=None` at `api/src/transport_matters/session/ingest.py:101-119`.

Turn parts use the `api/src/transport_matters/ir.py` content block union:

- `text`: render markdown safe text, with copy action.
- `tool_use`: render tool name, id, and collapsed JSON input.
- `tool_result`: render success or error, nested text, image, or unknown blocks.
- `thinking`: render collapsed reasoning preview by default.
- `image`: render safe placeholder in F1, future image viewer seam in F3.
- `unknown`: render collapsed JSON shell and preserve provider data.
- redacted image artifact: `{ type: "image", artifact_hash, media_type }` from `session/ingest.py:131-139`; render an image artifact placeholder in F1 and keep `artifact_hash` as the F3 image viewer fetch seam.

Role handling uses the single `event.role` for all parts in that event:

- `user`: left or operator lane.
- `assistant`: right or agent lane.
- `system` and `developer`: system lane.
- `tool`: tool lane, visually tied to surrounding tool use when `tool_use_id` exists.
- null or unknown role: metadata lane with the raw role label.

Extractor contract:

```ts
export function mapSessionEventToChatItems(event: SessionEventView): ChatItem[];
```

Mapping order:

1. Branch on `event.kind` first.
2. `kind === "meta"`: render a metadata or system lane item with `seq`, `native_turn_id`, `ts`, `model`, `source_path`, and `source_line`. Do not expect `event.ir`.
3. `kind === "turn"`: require `event.ir.parts` to be an array. Render those parts under `event.role`.
4. Within `parts`, dispatch by `part.type`. Handle both the normal `image` block with `source` and the artifact redacted image block with `artifact_hash`.
5. If a turn has no renderable parts, render `search_text` when present. Otherwise render a compact metadata item with `kind`, `seq`, and source path.
6. Unknown `kind` values render as metadata items and do not crash the pane.

Do not branch on `ir.content`, `ir.messages`, `ir.system`, or `InternalResponse`. Those are wire request or response envelope shapes, not the persisted session event IR.

Reuse:

- Reuse block rendering helpers from `www/src/components/detail/ContentBlocks.tsx:21-98` where possible.
- If `ContentBlockRow` chrome is too exchange centric, extract pure block summary and block body helpers before composing the transcript chat. Do not copy the rendering logic.

### 10.5 Transcript UI states

- Loading: stable skeleton grouped by expected chat lanes.
- Empty: no events message with session id and refresh action.
- Streaming: live badge from EventSource state and highest `seq`.
- Reconnecting: inline status, keep rendered backlog visible.
- Error: inline retry for backlog or stream, no pane close.
- Sidechain: mark events with `is_sidechain` visually and in accessible labels.
- Source: show `source_path:source_line` when present as provenance metadata, no raw path fetch.

## 11. Reconcile parked cockpit spec and old findings

### 11.1 Parked cockpit decisions reused

- Generic layout engine and content edge boundary from the parked spec remain binding.
- Recursive n ary split tree, stable pane ids, render prop content surface, FLIP, and transform only animation remain binding.
- Engine placement at `www/src/engine/**` plus boundary lint remains binding.
- Viewer registry and artifact policy stay as F3 seams.
- Design specs under `~/.mdx/design/transport-matters-desktop-cockpit-ux-spec.md` and `~/.mdx/design/transport-matters-desktop-cockpit-spec-ux.md` stay the accessibility, keyboard, motion, and token reference.

### 11.2 Parked cockpit decisions adapted

- The old rawness row of transcript, terminal, and wire is future cockpit scope. Session canvas F1 starts with the picker plus the auto resolved launch transcript pane because the session store is now the shipped data source.
- The old `transcript` pane kind becomes viewer `transcript-chat` in this route.
- The terminal stays interactive in the user's terminal for F1 and F2. Real TUI, wire, file, and image viewers are seams, not F1 or F2 deliverables.
- Layout persistence remains a model seam. F1 can keep state in memory. F2 may persist pane layout behind a small storage adapter if the CLI and desktop specs expose the location.

### 11.3 Old frontend findings status

| Finding | Status in session canvas |
| --- | --- |
| #1 Workspace identity false | Resolved by using path scoped `workspace_hash` from sessions. No cross checkout sharing claim. |
| #2 Missing transcript addressing | Resolved. Every transcript pane is keyed by `session_id`; API calls and cache keys use `session_id`. |
| #3 SSE reducer drops transcript live events | Resolved by a new `useSessionEventStream` and reducer. Legacy exchange reducer remains untouched for the legacy UI. |
| #4 Singleton store reads | Moot for transcript F1 because transcript code does not use exchange store. Still binding if F3 reuses wire components. |
| #5 Artifact provenance conflates ids | Deferred to F3. Spec preserves `session_id` plus `turn_id` provenance and pivot requirement before wire selection. |
| #6 Cockpit renderer packaging | Still relevant. F1 must prove desktop opens `/canvas`, not only that a window exists. |
| #7 60fps claim unproved | Resolved by moving the stress harness into F1 and extending it in F2. |

## 12. F1, F2, and F3 plus seams

### F1: session canvas minimum credible loop

Build:

- `/canvas` route and desktop entry update.
- DOM canvas surface with pan, zoom, focus, and floating pane windows.
- `www/src/engine/**` minimal reducers, `LayoutCanvas`, `PaneFrame`, boundary lint.
- `session-picker` viewer using `GET /api/sessions?owner=local`.
- `transcript-chat` viewer using backlog GET and session SSE stream.
- Launched run resolver using `GET /api/sessions?owner=local&workspace_hash={hash}&cli={agent}` with run id preference.
- New session event reducer scoped by `session_id` and `seq`.
- Spawn or focus transcript pane on launch resolution and picker selection.
- F1 stress harness for floating pane motion.
- Tests for route selection, launch resolution, picker states, transcript reducer, IR mapping, dedup, reconnect cursor, and spawn or focus behavior.

Acceptance:

- `transport-matters desktop` opens `/canvas`.
- Picker is visible immediately.
- The launched run auto resolves to a live transcript pane when its session row exists.
- If the row has not appeared yet, the picker shows a pending state until lookup resolves.
- Selecting a real session spawns a transcript pane.
- Transcript pane renders backlog and appends live events without duplicates.
- The agent remains interactive in the user's terminal for F1 and F2. The canvas does not spawn or embed a terminal pane.
- Legacy UI code remains present and direct development access still works.
- Stress harness proves initial pane motion target before signoff.
- Gate: `cd www && pnpm lint && pnpm typecheck && pnpm test` plus the F1 stress command. If backend static fallback changes, also run the focused API or desktop smoke covering `/canvas`.

### F2: layout manager hardening

Build:

- Tmux like tiling mode with split tree, resize handles, presets, and focus mode.
- Mode switch transitions between floating, tiling, and focus.
- Deterministic efficient layout planner for spawn and close.
- Keyboard leader or command bar shortcuts for focus, close, resize, mode switch, reset, and picker focus.
- Optional local layout persistence adapter if the desktop spec exposes a stable location.
- Stress harness extension for tiling, focus, and mode switches.
- Accessibility pass for resize handles, roving toolbar focus, focus return, and reduced motion.

Acceptance:

- Spawn and close realign panes deterministically in floating and tiling modes.
- Mode switch preserves pane identity and stream subscriptions.
- Keyboard only user can open picker, select session, focus transcript, resize, zoom, close, and return focus.
- Stress harness covers floating, tiling, focus, and mode switches.
- Gate remains `cd www && pnpm lint && pnpm typecheck && pnpm test` plus stress harness.

### F3 plus seams, design now, do not build

- Multi canvas and working directory switching.
- Layout persistence across desktop launches.
- Real TUI viewer with xterm and PTY websocket.
- Wire viewer reusing exchange UI after store de singletonization.
- File and image viewers via registry.
- Artifact auto spawn from transcript and wire tool records.
- Provenance jump from artifacts to transcript seq and wire exchange after pivot.
- Fork, share, eval, and multi operator features.

## 13. Verification plan

F1 tests:

- `SessionCanvasRoute.test.tsx`: `/canvas` route renders canvas, `/` still renders legacy app.
- `sessionClient.test.ts`: session list and event params, error handling, no direct fetch.
- `launchResolution.test.ts`: workspace plus cli lookup, run id preference, pending state, fallback to newest active when run id is absent.
- `sessionEventReducer.test.ts`: append, dedup by seq, gap backfill request, wrong session drop.
- `mapIrToChat.test.ts`: `turn` renders `ir.parts`, `meta` ignores null `ir`, all content block types, artifact redacted image blocks, role lanes, and unknown roles.
- `SessionPickerPane.test.tsx`: loading, error, empty, default, keyboard select, duplicate focus.
- `TranscriptChatPane.test.tsx`: backlog render, streaming append, reconnect state.
- `sessionCanvasStress.spec.ts`: frame meter route with synthetic panes.

F2 tests:

- `efficientLayout.test.ts`: candidate scoring, tie breakers, spawn, close, pinned panes.
- `layoutState.test.ts`: split insert, close prune, normalize, focus mode, reduced motion branch.
- `PaneWindow.a11y.test.tsx`: labels, focus return, resize separator semantics.
- `sessionCanvasStress.spec.ts`: mode switching, tiling resize, focus transitions.

Manual proof before done:

1. Start the app locally.
2. Open `/canvas`.
3. Confirm picker is visible.
4. Confirm launched run lookup is pending or resolved.
5. Confirm resolved launched run opens a transcript pane automatically.
6. Select another existing session from the picker.
7. Confirm transcript backlog.
8. Trigger or simulate a new session event.
9. Confirm live append advances seq once.
10. Run the frontend gate.
11. Run the stress harness and record frame summary.

## 14. Open questions for orchestrator

1. Should `/canvas` require a backend static fallback, or may F1 use a hash route if production direct path fails? Working assumption: ship real `/canvas` and include the small fallback or desktop hosted route update needed to load it.
2. What is the final transport for `CanvasLaunchContext`, query params or preload IPC? Working assumption: support query params first because the route is web first, and keep a small adapter so preload can provide the same object later.
3. Should layout state persist in F2 or wait for the desktop persistence spec? Working assumption: F2 defines a storage adapter interface and keeps persistence behind it unless the CLI or desktop spec has landed.
4. Should transcript chat render `thinking` expanded by default? Working assumption: collapsed by default, with per block expansion remembered per `session_id:seq:blockKey` in UI state only.
5. Should F1 support multiple concurrent SSE streams, one per transcript pane? Working assumption: yes. Each transcript pane owns one EventSource and closes it with the pane. If this proves heavy, F2 can consolidate streams by session id.
