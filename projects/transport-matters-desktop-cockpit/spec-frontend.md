# Transport Matters Desktop Cockpit: Frontend Spec

Author: frontend-engineer/claude. Status: draft for peer review (frontend-engineer/codex) and orchestrator integration.
Consumes: `CHARTER.md` (this directory). Resolves the charter's "Frontend (frontend-engineer pair)" open questions into a buildable design.
Sibling specs: `spec-backend.md` (backend pair), `spec-ux.md` (ux-designer). The orchestrator reconciles the stream-contract seam and authors the unified slice plan.

Conventions: no em dashes; repo `CLAUDE.md` / `PROJECT.md` / `api/CLAUDE.md` are binding. Every reuse seam is cited as `path:Symbol`. Contract assumptions on the backend are recorded in section 16, never messaged to the backend pair.

---

## 1. Scope and the one decision that shapes everything

The deliverable is a desktop cockpit whose reusable heart is a **generic, content-agnostic layout engine**. Transport Matters content (chat, TUI, wire, artifact viewers) plugs in only at the edges. The single architectural force behind every choice below is the **engine/content boundary**: the engine knows rectangles, panes, zones, focus, and transitions, and never imports chat, wire, terminal, or any TM type.

A second force, discovered while grounding this spec in the repo, shapes the data layer: the existing `www/` app is **single-backend and global-singleton** by construction. Its API transport (`www/src/api.ts:setApiTransport`, module-global `let apiTransport`), its query cache (`www/src/lib/queryClient.ts:queryClient`, a singleton), and its UI state (`www/src/stores/uiStore.ts:useUIStore`, a global store) all assume exactly one backend. The cockpit drives **N backends at once** (one per agent). Reusing `www/` components therefore requires scoping these globals per agent. This is the central reuse refactor and is specified in section 8.

---

## 2. Architecture: four layers, one boundary

```
+---------------------------------------------------------------+
|  Electron shell (desktop/, main + preload)                    |  Node, React-free
|  spawns N backends, discovers ports, bridges to renderer      |
+----------------------------+----------------------------------+
                             | localhost HTTP/SSE/WS, IPC
+----------------------------v----------------------------------+
|  TM content layer  (cockpit renderer)                         |  imports www/ + engine
|  paneRegistry, agentManager, artifactOrchestrator,            |
|  AgentBackendProvider, launcher, chat/TUI/wire/viewer panes   |
+----------------------------+----------------------------------+
                             | engine public API only
+----------------------------v----------------------------------+
|  GENERIC LAYOUT ENGINE  (extractable, zero TM imports)        |  the littleorgans payoff
|  split tree, tiling + floating, FLIP transitions, focus/zoom, |
|  zones, event-driven spawn, persistence, viewer registry      |
+---------------------------------------------------------------+
```

The arrows down are the only permitted dependency directions. The engine depends on nothing above it. The content layer depends on the engine and on `www/`. The Electron shell depends on neither renderer layer (it loads the built renderer and talks over localhost + IPC). This mirrors the Python import DAG discipline (`api/CLAUDE.md`: `ir -> adapters -> rules -> pipeline -> storage -> server`) and is enforced the same way: by a boundary lint (section 14).

---

## 3. Repo placement and build topology

Grounded facts: there is **no root pnpm workspace**; `www/` (package `transport-matters`, no `exports`) and `desktop/` (package `transport-matters-desktop`, dep `electron@^39`) are independent pnpm projects. `desktop/src/rendererBoundary.test.ts` enforces that the Electron main bundle contains no React, no `RouteLayout`, no `createBrowserRouter`. `www/vite.config.ts` builds the existing single-page app into `../api/src/transport_matters/www`, served as static by each backend.

Charter line 184 locks the model: "ONE UI codebase, the renderer imports `www/` components; vite build for the renderer." Reading that with DRY:

1. **`www/` is the one UI codebase.** It gains a second Vite build target, the **cockpit renderer**, alongside the existing single-page app. Both share `www/src/components/*`, `www/src/hooks/*`, `www/src/api.ts`, and the design tokens. No fork, no second component library.
   - New entry: `www/cockpit.html` + `www/src/cockpit/main.tsx` (the cockpit root). Existing `www/index.html` + `www/src/main.tsx` are untouched.
   - New build config: `www/vite.cockpit.config.ts` outputs to `www/dist-cockpit/`. This output is what Electron loads; it is **not** served by any backend (the cockpit talks to many backends, so it cannot be hosted by one).
2. **The layout engine lives at `www/src/engine/`** as a self-contained module with a public barrel `www/src/engine/index.ts`. A boundary lint (section 14) forbids any import from `@/components`, `@/api`, `@/stores`, `@/hooks`, or any TM path inside `engine/`. Extraction to littleorgans later is a directory lift plus a `package.json`; the lint guarantees nothing TM-specific leaked in. The engine may depend on `react`, `framer-motion`, and `@use-gesture/react` (all generic).
3. **`desktop/` keeps its main process as-is** and is generalized from one backend to N (section 9). It loads `www/dist-cockpit/index.html` in production and the cockpit dev-server URL in development. `rendererBoundary.test.ts` continues to scope only `desktop/src/` (the main process), so the React-free invariant holds.

New dependencies added to `www/package.json`: `framer-motion` (FLIP and shared-layout transitions), `@xterm/xterm` + `@xterm/addon-fit` + `@xterm/addon-webgl` (TUI pane), `@use-gesture/react` (pointer gestures for the floating canvas), and a markdown renderer for the viewer registry (`react-markdown` + `remark-gfm`). React 19, Tailwind v4, TanStack Query v5, Zustand v5, and `@tanstack/react-virtual` are already present and reused.

Rejected alternative: a separate top-level `cockpit/` package importing `www` as an external workspace dependency. It would require adding a root workspace plus an `exports` map to `www` and would split the "one UI codebase." The within-`www` second build is DRYer and matches the locked decision. The eventual engine extraction (its own package) is the only piece that graduates out, and the boundary lint keeps it extraction-ready today.

---

## 4. The layout engine (the reusable heart)

### 4.1 Tech pick and justification

**Decision: a custom recursive split-tree core plus Framer Motion for FLIP/shared-layout transitions, plus `@use-gesture/react` for floating-canvas pointer gestures.**

Rejected, with reasons grounded in the perf requirement (a live xterm plus multiple streaming panes, scaling 3 to 30 panes):

- **react-flow (`@xyflow/react`)** models a node-edge graph on a pan/zoom canvas. It gives free-floating spatial placement well but has no recursive split-tree or tiling model, so the charter's primitive ("the same content renders as different layouts") would have to be rebuilt on top of it. Its node store and edge machinery are dead weight for a window manager, and node re-render behavior under continuous byte streams is an avoidable risk.
- **tldraw** is a whiteboard/shape editor with an infinite canvas. Embedding a live interactive xterm and streaming DOM inside shapes fights the tool's shape-centric, partly canvas-rendered model. It is heavyweight and opinionated for what is fundamentally rectangle management.
- **Custom split tree** is a small, well-understood data structure. Tiling is a pure function from tree to rectangles. The floating canvas is absolute positioning under one pan/zoom transform. Both are cheap and fully under our control, which is exactly what a perf-critical, extractable engine needs.

Framer Motion supplies the FLIP/shared-layout primitive the charter demands as a hard requirement (`layout` prop, `layoutId` shared-element animation: measure old rect, measure new rect, invert, play). It animates compositor-friendly transforms, which is what keeps 30 panes at 60fps. The perf rule that makes this safe is in 4.6: animate the **pane wrapper transform only**, never re-lay-out pane content during the animation.

### 4.2 Data model (generic, zero TM types)

```ts
type Axis = "row" | "col";
type NodeId = string;
type PaneId = string;

interface SplitNode {
  kind: "split";
  id: NodeId;
  axis: Axis;
  children: LayoutNode[];
  sizes: number[];        // fractions, sum to 1, length === children.length
  groupTag?: string;      // opaque; consumer may tag a subtree (e.g. an agent group)
}
interface LeafNode { kind: "leaf"; id: NodeId; paneId: PaneId; }
type LayoutNode = SplitNode | LeafNode;

interface FloatingRect { x: number; y: number; w: number; h: number; }
interface PaneMeta {
  id: PaneId;
  zone?: string;          // named zone, e.g. "artifacts"; engine has no opinion on names
  minimized?: boolean;
  pinned?: boolean;
  floating?: FloatingRect; // position in floating mode
  z?: number;              // stacking order in floating mode
}

interface Viewport { panX: number; panY: number; scale: number; } // floating mode only

interface LayoutState {
  mode: "tiled" | "floating";
  tree: LayoutNode;
  panes: Record<PaneId, PaneMeta>;
  focusedPaneId: PaneId | null;
  zoomedPaneId: PaneId | null;
  viewport: Viewport;
}
```

The engine stores `paneId` and geometry only. Pane **content** is supplied by the consumer through a render prop, so no content type ever enters the engine.

### 4.3 Public API

The core is framework-agnostic pure reducers over `LayoutState` (no React, no TM), wrapped by thin React bindings. Commands:

```ts
// structure
splitPane(target: PaneId, axis: Axis, newPaneId: PaneId, ratio?: number): void
closePane(id: PaneId): void
resizeSplit(node: NodeId, sizes: number[]): void
// focus / zoom
focusPane(id: PaneId): void
clearFocus(): void
zoomPane(id: PaneId): void
restoreZoom(): void
// modes
setMode(mode: "tiled" | "floating"): void
// floating
moveFloating(id: PaneId, rect: FloatingRect): void
bringToFront(id: PaneId): void
setViewport(v: Partial<Viewport>): void
minimize(id: PaneId): void
restore(id: PaneId): void
// event-driven spawn (consumed by the TM artifact orchestrator)
spawnPane(opts: { paneId: PaneId; place: "tile-with" | "floating" | "zone"; anchor?: PaneId; zone?: string }): void
updatePaneMeta(id: PaneId, patch: Partial<PaneMeta>): void
// presets
applyPreset(preset: PresetSpec): void
// persistence
serialize(): SerializedLayout
hydrate(s: SerializedLayout): void
```

Presets are generic. `PresetSpec` is one of: `{ kind: "even" }`, `{ kind: "main"; axis: Axis; mainPaneId: PaneId }`, `{ kind: "grid"; cols: number }`, or `{ kind: "group"; partition: (paneId: PaneId) => string }`. "Group by agent" is expressed by the consumer passing a partition function `paneId => agentIdOf(paneId)`; the engine never learns what an agent is.

### 4.4 Rendering surface

```tsx
<LayoutCanvas
  renderPane={(paneId) => ReactNode}     // content; consumer-owned
  renderChrome={(paneId) => ReactNode}   // optional pane header/controls
/>
```

`LayoutCanvas` computes rectangles from `LayoutState` (tiling: walk the tree allocating fractions; floating: read `PaneMeta.floating` under the viewport transform) and renders each pane as a Framer Motion `motion.div` with a stable `layoutId={paneId}`. Tree changes, mode switches, focus toggles, and spawns all animate by FLIP automatically because `layoutId` is stable across states.

### 4.5 Modes, focus, zoom, persistence

- **Tiled mode**: tmux-style rows and columns from the split tree. Drag a split gutter to `resizeSplit`. Presets `even`, `main`, `grid`, `group`.
- **Floating mode**: a free canvas. Panes are absolutely positioned (`PaneMeta.floating`), draggable and resizable via `@use-gesture/react`, stacked by `z`. Background drag pans the viewport; wheel/pinch zooms (`setViewport`).
- **Mode switch is the showpiece**: same `layoutId` per pane, so panes fly between their tile cell and their floating rectangle in one shared-layout animation.
- **Focus / zoom**: `zoomPane` animates the target's `layoutId` to the full canvas rectangle while the rest dim and recede; `restoreZoom` reverses it. `focusPane` only sets `focusedPaneId` (a ring and input priority), no geometry change.
- **Persistence**: `serialize()` returns a plain JSON `SerializedLayout` (tree, panes, mode, viewport, focus). The consumer persists it per workspace (section 9.4). The engine itself never touches storage.

### 4.6 Performance rules (the 60fps guarantee)

1. Animate `transform` and `opacity` only. Never animate width/height/top/left of content.
2. Pane content lives inside the animated wrapper and is **not** re-laid-out during a transition. xterm refit and any size-dependent reflow run once on `onLayoutAnimationComplete`.
3. `React.memo` every pane content component and pass a stable `paneId`; a layout change must re-render wrappers, not content.
4. Set `will-change: transform` on panes only while a transition is in flight, then clear it.
5. Streaming content (xterm, live append) writes into its own subtree via refs and imperative APIs, so byte arrival never triggers a layout React render.
6. Floating-canvas pan/zoom mutates one transform on the canvas layer, not per-pane styles.

---

## 5. Pane shell (premium feel)

The shell is generic chrome rendered by the engine via `renderChrome`, but the controls it exposes are content-neutral. Each pane shell provides: a title region (consumer-supplied label and provenance affordance), a focus ring, and controls for split, zoom, minimize, close, and (floating mode) drag handle and resize edges. Z-order and drag/resize are engine commands (section 4.3).

The shell must implement the eight interaction states for every control: default, hover, active, focus-visible, disabled, loading, error, empty. Concretely:

- **Pane container**: default, focused (ring + raised elevation via `--color-raised`), dragging (elevated shadow, `will-change`), minimized (collapsed to a dock chip), error (a pane-level error boundary surface), empty (placeholder when content has nothing yet).
- **Controls** (split/zoom/minimize/close, gutters, drag handles): full hover/active/focus-visible/disabled coverage, keyboard operable.

Premium feel is delivered by the FLIP transitions (section 4), spring easing on focus/zoom, and consistent elevation tokens. No bespoke shadows or radii: the design language is square (token radius is 0) and elevation comes from `--color-raised`/`--color-hover` plus the chiaroscuro tokens (`--shadow-rgb`, `--highlight-rgb`) defined in `www/src/index.css`.

---

## 6. TM content panes (the rawness gradient)

Three agent panes form the clean to raw gradient that makes the TM thesis spatial: chat (clean transcript) to TUI (raw interactive) to wire (rawest bytes). Each pane is registered in the `paneRegistry` (section 7.1) keyed by a content kind and rendered through `LayoutCanvas.renderPane`. All three are scoped to one agent's backend via `AgentBackendProvider` (section 8).

### 6.1 Chat pane (transcript IR, premium render, read-only v1)

Reuse: `www/src/components/detail/ContentBlocks.tsx:ContentBlockRow` renders a single IR block (text, tool_use, tool_result, thinking, image, unknown). `www/src/components/editor/MessagesSection.tsx` and `www/src/components/detail/InspectTab.tsx:ResponseCard` already compose `ContentBlockRow` for request and response. The chat pane composes these into a turn-grouped, conversational read-only transcript and drops the editor affordances.

Data source and the IR-JSON gap: the index timeline (`api/.../api/v1/index_routes.py` `GET /api/index/timeline?stream=transcript&with_bodies=true`) returns `TimelineEntry` with `TimelineBlock` carrying only `kind` plus a `text` FTS projection, not the full `ContentBlock` union. Full IR (including `ToolUseBlock.input`) is exposed today only on the wire path via `GET /api/exchanges/{id}` (`ExchangeDetailResponse`). For v1 the chat pane therefore renders from the **wire exchange IR** (clean-filtered to hide system reminders and tool schemas, which is the transcript-versus-wire distinction the product is built on), reusing the same components `www/` already uses. Live append uses the existing SSE stream (section 8). Whether the backend instead exposes a full-IR transcript timeline endpoint is open question OQ-3.

States: empty (no turns yet), loading (initial fetch), streaming (live append indicator), error (fetch or stream failure), plus per-block expand/collapse already handled by `ContentBlockRow`.

### 6.2 TUI pane (xterm over the per-agent pty websocket)

This is the one pane that depends on the new backend capability (the per-agent bidirectional localhost websocket). It is the single keyboard input surface in v1.

Stack: `@xterm/xterm` with `@xterm/addon-fit` and `@xterm/addon-webgl` (fall back to a canvas renderer when WebGL is unavailable). Lifecycle:

- Mount: create `Terminal`, `open()` into the pane DOM, load fit + webgl addons, `fit()`.
- Attach: open a websocket to the agent's pty endpoint. On open the server replays attach-time scrollback (provisional contract); the client writes incoming bytes with `term.write()`.
- Input: `term.onData` sends keystrokes to the server. Other panes never send input in v1.
- Resize: on layout change, `FitAddon.proposeDimensions()` then `term.resize(cols, rows)` and send a `resize(cols, rows)` message. Resize is debounced to `onLayoutAnimationComplete` so transitions stay at 60fps (section 4.6 rule 2).
- Reconnect and replay: on non-user-initiated close, reconnect with exponential backoff. On reconnect the client `term.reset()` then applies the server's attach replay so scrollback is restored without double-render. Exact replay framing and de-dup semantics are open question OQ-1.

States: connecting, connected, reconnecting (with a non-modal banner), error (handshake or fatal close), closed (process exited, show exit code if delivered), empty (attached, no output yet).

### 6.3 Wire pane (embed existing wire UI)

Reuse: `www/src/components/ExchangeList.tsx:ExchangeList` (virtualized exchange tree), `www/src/components/ExchangeDetail.tsx:ExchangeDetail` (inspect/request/response/transport tabs), and optionally `www/src/components/editor/BreakpointEditor.tsx:BreakpointEditor` with `www/src/components/ArmToggle.tsx:ArmToggle`. These currently mount inside `RouteLayout`/`InterceptRoute` and read from the global `useUIStore` plus the module-global API transport. The decoupling that makes them embeddable per agent in a floating pane is section 8; once a pane is wrapped in `AgentBackendProvider`, these components render unchanged.

States: empty (no exchanges captured yet), loading, live (stream connected), paused (breakpoint armed and holding, when breakpoint reuse is enabled), error. Breakpoint editing is reused as-is but is optional for v1; the read-only wire stream is the v1 requirement.

---

## 7. Viewer registry and artifact orchestration

### 7.1 Viewer registry (generic, reusable, engine-adjacent)

A content-type to renderer map, generic and extractable (it ships to littleorgans with the engine). It lives next to the engine and imports no TM types.

```ts
interface ViewerContext { ref: ContentRef; }   // ContentRef = { uri: string; mime?: string; inlineText?: string }
interface Viewer { id: string; canRender(ref: ContentRef): boolean; render(ctx: ViewerContext): ReactNode; }
registerViewer(v: Viewer): void
resolveViewer(ref: ContentRef): Viewer | null
```

v1 viewers: markdown (`react-markdown` + `remark-gfm`) for `.md`, and an image viewer for image mime types. The registry is open by design; later code/diff, csv/table, and html viewers register the same way. The `paneRegistry` (TM layer) maps the engine's pane kinds (chat, tui, wire, viewer) to their renderers; for viewer panes it delegates to `resolveViewer`.

### 7.2 Artifact orchestration (TM layer) and the spawn policy

The engine stays pure: it receives "spawn or update a pane in a zone." A TM `artifactOrchestrator` decides when, derived from wire/transcript tool records.

Source of artifact events: the charter's provisional contract is that the backend derives and delivers `(path, type, content?, agent_id, turn_id)` events. The frontend consumes that contract and does not re-derive when the backend provides it. Delivery channel and schema are open question OQ-2. Fallback if the backend defers: the orchestrator derives events client-side from the wire SSE stream, reading `ToolUseBlock.input` (path and file content for Write/Edit) and image-generation result paths from the full exchange IR that `GET /api/exchanges/{id}` already exposes. The index timeline cannot back this fallback because it omits `tool_use.input` (the IR-JSON gap). This dependency is recorded in OQ-2 and OQ-3.

Spawn policy (the orchestrator implements all of it against the engine API):

- **dedupe-to-update**: a `Map<path, paneId>`. The same path calls `updatePaneMeta` plus a content refresh on the existing viewer pane (a live render of a doc being authored), never `spawnPane` again.
- **type filter**: only types with a registered viewer and on an allowlist (md, image in v1) spawn. Temp and build noise is ignored.
- **no focus theft**: artifacts spawn with `place: "zone", zone: "artifacts"` into a calm artifacts dock and animate in (section 4); they never call `focusPane`.
- **lifecycle**: pin, dismiss, auto-retire (a capped, least-recently-updated dock). Persisted per workspace.
- **provenance link**: each artifact pane stores `{ agentId, turnId }`. Clicking it focuses the originating agent's chat or wire pane (`focusPane`) and sets that pane's scoped `useUIStore.selectedId` to the originating turn or exchange, scrolling it into view. This is the TM superpower a filesystem watcher could not provide; it works because detection is sourced from attributed tool records, not the filesystem.

---

## 8. Data layer and multi-agent scoping (the core reuse refactor)

Problem (grounded): `www/` is single-backend. `www/src/api.ts` holds a module-global `let apiTransport = createApiTransport()` with `setApiTransport`/`resetApiTransport`. `www/src/lib/queryClient.ts` exports a singleton `queryClient`. `www/src/stores/uiStore.ts:useUIStore` is a global store. The cockpit shows many agents at once, each a separate backend on its own `web_port`.

Solution: an **`AgentBackendProvider`** React context that scopes the data layer to one agent. It supplies:

- a scoped API transport built from that agent's base URL (`http://127.0.0.1:{web_port}`), replacing reads of the module global;
- a scoped `QueryClient` instance (one per agent) so caches never collide, wrapped in its own `QueryClientProvider`;
- a scoped SSE connection (`www/src/hooks/useExchangeStream.ts` opened against that agent's `/api/stream`), feeding that agent's query cache via `applyExchangeStreamEvent`;
- a scoped `useUIStore` instance (selection, expansion, arm state) so each agent pane has independent selection.

The DRY refactor in `www/` (shared by both the existing single-page app and the cockpit, no fork):

1. Replace the module-global transport read with a `useAgentBackend()` hook that returns the scoped transport. In the existing single-page app, one `AgentBackendProvider` wraps the root with the current backend, so behavior is unchanged. In the cockpit, one provider wraps each agent's panes.
2. Convert the singleton `queryClient` and global `useUIStore` to provider-scoped instances created inside `AgentBackendProvider`. The single-page app wraps once at the root; the cockpit wraps per agent.
3. Components (`ExchangeList`, `ExchangeDetail`, `ContentBlockRow`, `BreakpointEditor`, and the hooks `useExchanges`, `useMeta`, `useTurnContent`, `useBreakpoint`, `useOverrides`) keep their signatures and read state from context. No component is forked.

This refactor is the work the charter labels "wire pane: decoupling needed," generalized so all three reused panes are multi-instance safe. It is scoped to the smallest change that removes the singletons.

Cross-origin: the cockpit renderer origin (file:// resolves to a null origin, or a custom app scheme in production) must be permitted by each backend's `CORSMiddleware` (`api/.../main.py` `allow_origins=settings.cors_origins`). This is open question OQ-5.

---

## 9. Electron shell (build on `desktop/`, do not reimplement)

The existing `desktop/` app is a working main process: `desktop/src/main.ts` (lifecycle, backend orchestration), `desktop/src/window.ts` (hardened window: contextIsolation true, sandbox true, nodeIntegration false, navigation guard, external-link handler), `desktop/src/preload.ts` (contextBridge stub), `desktop/src/backendProcess.ts` (spawns `transport-matters <client> <dir> --web-port --proxy-port`, SIGTERM cleanup), `desktop/src/backendHealth.ts` (polls `/health`), `desktop/src/env.ts`. The React-free boundary is enforced by `desktop/src/rendererBoundary.test.ts`. All of this is reused.

### 9.1 From one backend to N

Generalize `backendProcess.ts` from a single child to a keyed registry of children, one per agent. Each spawn allocates its own ports (the backend already allocates a unique `proxy_port`/`web_port` pair per run and writes a manifest; see `api/.../cli/instances.py` and the manifest layout under `~/.transport-matters/workspaces/{slug}/{hash}/{run}/`). The shell preserves the per-run isolation invariant by spawning one `transport-matters claude/codex --work-dir` subprocess per agent (charter locked decision 6), never collapsing them.

### 9.2 IPC surface (preload bridge)

The renderer cannot spawn processes, so the preload exposes a minimal, typed bridge (replacing the current stub):

```ts
window.cockpit = {
  listWorkspaces(): Promise<WorkspaceCard[]>;            // persisted launcher metadata
  openWorkspace(workDir: string): Promise<WorkspaceId>;  // canonical slug/hash via the CLI seam
  spawnAgent(workspace: WorkspaceId, kind: "claude" | "codex"): Promise<AgentHandle>;
  stopAgent(agentId: string): Promise<void>;
  onAgentEvent(cb: (e: AgentLifecycleEvent) => void): Unsubscribe; // started, exited, crashed
  loadLayout(workspace: WorkspaceId): Promise<SerializedLayout | null>;
  saveLayout(workspace: WorkspaceId, layout: SerializedLayout): Promise<void>;
};
```

`AgentHandle` carries what the renderer needs to address a backend: `{ agentId, kind, baseUrl, webPort, ptyWsUrl, runId }`. The main process learns ports deterministically from the spawn itself (preferred over scanning manifests), with the manifest/`list --json` surface as a fallback discovery path. Whether ports come from the spawn handshake or the manifest, and the exact `ptyWsUrl` shape, are open question OQ-4.

### 9.3 Screen flow and single-instance

- Add `app.requestSingleInstanceLock()` (currently missing) so one cockpit instance owns the workspace registry; a second launch focuses the existing window.
- Screen 1 (launcher) and the canvas are both renderer-side React routes inside the cockpit build. Provider choice (claude or codex) lives on the canvas at "spin up an agent," not on screen 1 (charter screen flow).
- "Spin up an agent" calls `window.cockpit.spawnAgent`, receives an `AgentHandle`, registers it in the renderer `agentManager`, and asks the engine to `spawnPane` the agent's first pane with a slick transition.

### 9.4 Persistence

Workspace records (for the launcher) and per-workspace layouts persist through the IPC bridge (`loadLayout`/`saveLayout`, `listWorkspaces`). Location is provisionally a desktop config under `~/.transport-matters/` (charter), confirmed by the backend pair as open question OQ-6. Workspace identity reuses the canonical-path slug/hash (`api/.../workspace.py:workspace_id`, blake2b of the resolved POSIX path), so two checkouts of one project share a workspace and its remembered layout (DRY with the capture substrate).

---

## 10. Launcher (frontend obligations)

The launcher is a creative, remembered-workspace surface, not a directory picker (charter screen 1). The frontend renders persisted `WorkspaceCard`s with metadata (git branch, last activity, live agent count, optional canvas thumbnail), supports create (drag a folder or pick a directory), open, and remember. The concrete visual direction (project-gallery cards, command-palette finder, or spatial recents) is the ux-designer's recommendation in `spec-ux.md`; this spec commits to the data shape (`WorkspaceCard`), the IPC calls, and the eight states (empty: no workspaces yet; loading; populated; hover/focus on cards; error; the create flow's in-progress and error states).

---

## 11. Performance plan

Targets adapted for an Electron renderer that loads a local bundle and connects to localhost (network-bound web metrics like FCP/TTI are less meaningful from file://, so they are reframed as boot and interaction budgets):

| Concern | Budget | How |
| --- | --- | --- |
| Layout transitions | sustained 60fps with up to ~30 panes | transform/opacity only, content not re-laid-out mid-transition (4.6) |
| Streaming (xterm + live append) | no dropped frames during byte storms | WebGL renderer, imperative writes, content isolated from layout renders (4.6 rules 3, 5) |
| Layout shift | CLS ~0 | panes are absolutely positioned; no reflow on data arrival |
| Launcher initial JS | < 200KB gzipped | code-split: xterm, webgl, framer features, and viewers load lazily on canvas open, not at launcher |
| Canvas first interactive | < 2s after openWorkspace | lazy pane content, suspense boundaries per pane |
| Memory at 30 panes | bounded | virtualized lists already in `ExchangeList`; artifact dock capped and auto-retired |

Measurement: the Chromium DevTools Performance panel (the renderer is Chromium), plus a scripted transition-stress harness (spawn N synthetic panes, drive mode switches and zooms, assert frame timing). Lighthouse runs against the renderer served over a dev http origin during CI for a score signal, acknowledging file:// is not a Lighthouse target in production.

---

## 12. Accessibility

WCAG AA. Keyboard model is tmux-like and pointer-complete (the ux spec choreographs the exact bindings):

- A leader-key command mode for split, focus movement (directional), zoom toggle, mode switch, preset apply, and close, mirroring tmux muscle memory.
- Pointer affordances for every keyboard action (drag gutters, drag/resize floating panes, click controls).
- Focus management: the engine owns a single `focusedPaneId`; focus is visible (a ring using accent tokens) and roving; spawning an artifact never moves focus. The TUI pane captures keys only when focused.
- Semantic structure: panes are landmarks with accessible names (the consumer-supplied label plus agent and kind), controls are real buttons with `aria-label`, the artifacts dock is a labeled region, and live regions announce agent lifecycle and reconnect state.
- Screen reader pass on the launcher, canvas navigation, and pane controls before sign-off.

---

## 13. Styling and design tokens

Reuse the existing token system in `www/src/index.css` (CSS custom properties: charcoal canvas layers `--color-well/canvas/surface/raised/hover`, edges, text tiers, categorical accents sage/rose/lavender/sky/amber/teal, six agent-rail colors `--color-agent-rail-0..5`, accent, JetBrains Mono `--font-sans`/`--font-mono`, square radius 0, chiaroscuro `--shadow-rgb`/`--highlight-rgb`). The six agent-rail colors map directly to per-agent pane accenting in the cockpit, which is a ready-made affordance for distinguishing agents at scale.

DRY refactor: extract the `@theme` token block from `www/src/index.css` into `www/src/styles/tokens.css` and import it from both the single-page app and the cockpit entry, so tokens are defined once. No hardcoded colors, sizes, or radii in cockpit components; everything is a Tailwind utility bound to a token or a `var(--color-*)`. The engine, being content-agnostic and extractable, ships with neutral default tokens and reads consumer-provided CSS variables for theming, so littleorgans can restyle it without code changes.

---

## 14. Repo invariants compliance

- **LOC**: every new file <= 700 lines, every function <= ~150. The engine and the TM layer are decomposed accordingly (core reducers, react bindings, canvas, gestures, registry, orchestrator, agent manager, per-pane modules as separate files).
- **Engine/content boundary as a lint**: an ESLint `no-restricted-imports` rule on `www/src/engine/**` forbids importing `@/components`, `@/api`, `@/stores`, `@/hooks`, and any TM path. This is the TypeScript analogue of the Python AST privacy boundary (`api/.../test_private_import_boundary.py`) and is the mechanical guarantee of extractability. CI fails on violation.
- **Typing**: TypeScript strict mode, no `any` in props or state; engine public types are exported from `www/src/engine/index.ts`.
- **Dependency direction**: enforced by the same lint plus a content-layer rule that the TM layer imports the engine only through its barrel, never deep paths.
- **Build gate**: `cd api && just ci` remains the Python gate; the frontend adds `pnpm -C www lint && pnpm -C www typecheck && pnpm -C www test && pnpm -C www build:cockpit` to the slice acceptance gates.

---

## 15. Proposed frontend slice sequence (input for the orchestrator's unified plan)

The orchestrator authors the binding plan (charter deliverable 4). This is the recommended frontend ordering, capture-substrate style (files, reuse, acceptance gate, LOC budget). Slice 1 is the thinnest end-to-end loop and deliberately avoids the new pty-ws so it ships on existing backend capability.

- **F1. Thinnest loop: launcher to one wire pane.** Engine MVP (split tree, tiled mode, one preset, `LayoutCanvas` with FLIP), `AgentBackendProvider` (scoped transport + QueryClient + SSE + uiStore), wire pane reusing `ExchangeList`/`ExchangeDetail`, Electron shell generalized to spawn one agent and bridge its ports, single-instance lock, launcher with create/open/remember.
  - Reuse: `desktop/src/*`, `www/src/components/ExchangeList.tsx`, `ExchangeDetail.tsx`, `useExchangeStream`, `api.ts`, `workspace_id`.
  - Gate: launch the cockpit, open a workspace, spin one claude agent, see its live wire pane in the engine shell; `pnpm` lint/typecheck/test/build green; boundary lint green.
  - Budget: ~700 engine + ~500 content + ~300 shell, across multiple files each <= 700.
- **F2. Multi-agent and layout depth.** N agents per workspace, floating mode plus the mode-switch showpiece, focus/zoom, presets (even/main/grid/group-by-agent), layout persistence via IPC, per-agent rail coloring.
- **F3. TUI pane.** xterm + fit + webgl, attach the pty-ws, resize, reconnect + replay. Depends on the backend pty-ws slice (OQ-1, OQ-4).
- **F4. Chat pane.** Turn-grouped read-only transcript reusing `ContentBlockRow`, live append; sourced per OQ-3 resolution.
- **F5. Viewer registry and artifact orchestration.** Generic registry + md/image viewers, artifact orchestrator with the full spawn policy and provenance. Depends on the artifact-event contract (OQ-2).
- **F6. Polish and a11y.** Eight-state coverage audit, keyboard model, transition choreography per the ux spec, performance harness.

---

## 16. Open questions for the orchestrator (contract assumptions, not messaged to backend)

- **OQ-1 pty-ws framing.** The TUI pane assumes a localhost websocket where server-to-client is raw PTY output bytes (binary frames) with attach-time scrollback replay, and client-to-server is keystroke bytes plus a `resize(cols, rows)` control message. Assumed: binary frames for output, a small JSON envelope for control (resize). Need confirmation of frame encoding (binary vs base64-in-JSON), the resize message schema, the attach replay format, reconnect token, and whether replay is full scrollback (so the client `term.reset()`s) or incremental.
- **OQ-2 artifact-event delivery.** The orchestrator assumes the backend derives `(path, type, content?, agent_id, turn_id)` events and delivers them, preferably over the existing `/api/stream` SSE as a typed event. Need: the channel (existing SSE vs new), the event schema, whether `content` is inlined or fetched, and confirmation that derivation is backend-side. If deferred to the frontend, confirm the fallback reads full exchange IR (`ToolUseBlock.input`) from `GET /api/exchanges/{id}` and the wire SSE.
- **OQ-3 transcript IR JSON for the chat pane.** The index timeline returns only `kind` + `text` projection, not the full `ContentBlock` union. v1 chat sources from wire exchange IR. Confirm either (a) chat v1 sources from the wire path, or (b) the backend adds a full-IR transcript timeline endpoint and its shape.
- **OQ-4 multi-agent discovery and addressing.** The renderer needs each agent's `{ baseUrl, webPort, ptyWsUrl, runId, kind }`. Assumed the main process learns ports from the spawn handshake (deterministic) with `transport-matters list --json` / manifests as fallback. Confirm the source of truth and the exact `ptyWsUrl` (for example `ws://127.0.0.1:{webPort}/pty` vs a dedicated port).
- **OQ-5 CORS / renderer origin.** The cockpit renderer origin (file:// null origin, or a custom app scheme in production) must be in each backend's `settings.cors_origins`. Confirm the allowed origin so cross-origin fetch and SSE from N backends succeed.
- **OQ-6 persistence store.** Confirm the location and schema for workspace records and per-workspace layouts (provisionally desktop config under `~/.transport-matters/`), and that workspace identity reuses `workspace_id` slug/hash.
- **OQ-7 backend topology dependency.** The renderer addressing model assumes one subprocess per agent (charter locked decision 6). If the backend chooses a session-manager daemon instead, the IPC `spawnAgent`/discovery contract (section 9.2) changes; flag the dependency.

---

## 17. Reuse seam citation index

| Concern | Seam (`path:Symbol`) | Use |
| --- | --- | --- |
| Wire list | `www/src/components/ExchangeList.tsx:ExchangeList` | wire pane (F1) |
| Wire detail | `www/src/components/ExchangeDetail.tsx:ExchangeDetail` | wire pane (F1) |
| Block render | `www/src/components/detail/ContentBlocks.tsx:ContentBlockRow` | chat + wire (F4) |
| Response card | `www/src/components/detail/InspectTab.tsx:ResponseCard` | chat pane (F4) |
| Request messages | `www/src/components/editor/MessagesSection.tsx` | chat pane composition |
| Breakpoint editor | `www/src/components/editor/BreakpointEditor.tsx:BreakpointEditor`, `www/src/components/ArmToggle.tsx:ArmToggle` | optional wire editing |
| API transport | `www/src/api.ts:createApiTransport` / `setApiTransport` | scoped per agent (section 8) |
| Query cache | `www/src/lib/queryClient.ts:queryClient` | scoped per agent (section 8) |
| UI store | `www/src/stores/uiStore.ts:useUIStore` | scoped per agent (section 8) |
| SSE stream | `www/src/hooks/useExchangeStream.ts`, `exchangeStreamEvents.ts:applyExchangeStreamEvent` | per-agent live append |
| Data hooks | `www/src/hooks/{useExchanges,useMeta,useTurnContent,useBreakpoint,useOverrides}.ts` | per-agent panes |
| Tokens | `www/src/index.css` (extract to `www/src/styles/tokens.css`) | shared styling (section 13) |
| Atmosphere | `www/src/components/routes/RouteAtmosphere.tsx:RouteAtmosphere` | launcher/empty backdrops |
| Electron main | `desktop/src/main.ts`, `window.ts`, `preload.ts`, `backendProcess.ts`, `backendHealth.ts`, `env.ts` | shell generalized to N (section 9) |
| Boundary test | `desktop/src/rendererBoundary.test.ts` | keeps main React-free |
| Index timeline | `api/.../api/v1/index_routes.py` `GET /api/index/timeline` | transcript projection (OQ-3) |
| Exchange detail | `api/.../api/v1/exchanges.py` `GET /api/exchanges/{id}` | full IR for chat + artifacts |
| Capture SSE | `api/.../api/v1/stream.py:stream_exchanges`, `broadcast.py` | live wire + artifact events |
| Workspace id | `api/.../workspace.py:workspace_id` | workspace identity reuse |
| Run discovery | `api/.../cli/instances.py:list_instances` (+ manifests) | fallback agent discovery |
| Launch core | `api/.../cli/launch_profile.py:prepare_managed_session` and `Claude/CodexLaunchProfile` | per-agent spawn (via CLI) |

End of frontend spec.
