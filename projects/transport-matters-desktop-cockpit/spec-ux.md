# Transport Matters Desktop Cockpit UX Specification

## Summary

This spec defines the interaction model for the Transport Matters Desktop Cockpit and Layout Lab. The cockpit is a power user workbench for many live agents inside one workspace. The reusable product is the layout engine: split trees, pane focus, presets, floating mode, transition choreography, and artifact surfaces. Transport Matters content binds only at pane edges.

Core rationale:

- The charter defines the cockpit as a testbed for a generic layout engine that later lifts into littleorgans. The engine must know panes, rectangles, focus, modes, and transitions. It must not know product content. [Basis: C1]
- The user model maps workspace to canvas, agent to run, and pane to a spatial surface. This supports tmux trained power users while keeping a richer pointer surface for desktop. [Basis: C2, U1]
- The three per agent panes form a rawness gradient: transcript, terminal, wire. The gradient makes the Transport Matters thesis visible. [Basis: C4]
- Artifact handling uses wire and transcript records because provenance and arbitrary output paths matter more than folder locality. [Basis: C5, R4]
- All drag and split interactions include keyboard and single pointer alternatives. This is required for WCAG 2.2 dragging movements, keyboard access, and target size. [Basis: A1, A2]

## Decision basis

### Charter evidence

- C1: Layout engine must be generic, content agnostic, extractable, and plugged into Transport Matters only at edges. `CHARTER.md:9-16`, locked again at `CHARTER.md:106-119`.
- C2: Domain model maps workspace, agent, pane, canvas, and layout onto tmux concepts. `CHARTER.md:20-31`.
- C3: Recursive split tree, tiling and floating modes, zoom focus, FLIP transitions, and persistence are required. `CHARTER.md:35-49`.
- C4: Per agent panes are transcript, terminal, and wire, forming clean to raw evidence. `CHARTER.md:53-59`.
- C5: Viewer registry, event driven artifact spawn, dedupe to update, calm artifact zone, lifecycle, and provenance are required. `CHARTER.md:65-90`.
- C6: Launcher must show remembered workspaces with git branch, last activity, live agent count, and canvas memory. Provider choice happens inside the canvas. `CHARTER.md:94-102`.
- C7: Provisional contracts cover stream reuse, transcript append, terminal websocket, artifact events, lifecycle, and persistence. `CHARTER.md:121-137`.
- C8: The UX deliverable must cover layout interaction, transitions, launcher, artifacts, and rawness gradient. `CHARTER.md:188-196`.

### Repo evidence

- R1: Workspace identity already derives stable slug and hash from a canonical path. `api/src/transport_matters/workspace.py:45-80`.
- R2: Launch profiles already own provider specific managed session setup. `api/src/transport_matters/cli/launch_profile.py:54-216`.
- R3: Live stream infrastructure already exposes SSE updates. `api/src/transport_matters/api/v1/stream.py:20-42`.
- R4: IR and frontend types already preserve tool use, tool result, image, and unknown content blocks. `api/src/transport_matters/ir.py:25-71`; `www/src/types.ts:433-472`.
- R5: Existing list and content block components are reusable seams for transcript and wire detail surfaces. `www/src/components/ExchangeList.tsx:136-174`; `www/src/components/detail/ContentBlocks.tsx:61-98`.
- R6: Current visual foundation uses dark layers, stable agent rail colors, one accent, JetBrains Mono, and square corners. `www/src/index.css:9-122`.

### Accessibility and convention evidence

- A1: WCAG 2.2 AA is the baseline, including keyboard access, contrast, target size, dragging alternatives, focus visible, and animation controls. Sources: W3C WCAG 2.2, W3C New in WCAG 2.2, W3C Understanding Animation from Interactions.
- A2: WAI ARIA APG practices define predictable focus, composite keyboard behavior, toolbar roving focus, button activation, and modal dialog focus if a dialog is unavoidable.
- U1: tmux leader conventions support dense pane management without adding persistent chrome.
- U2: Desktop IDE and window manager conventions support project recents, command palette filtering, drag handles, split handles, snap zones, zoom focus, and restore.

## Canonical conventions

These tokens are locked across UX, frontend, and backend specs.

```ts
export type PaneKind = "transcript" | "terminal" | "wire" | "artifact";
export type LayoutMode = "tiling" | "floating";
export type ContentType = "markdown" | "image" | "code" | "json" | "text" | "unknown";

export interface ArtifactProvenance {
  session_id: string;
  turn_id: string;
}

export interface LayoutGroupNode {
  kind: "group";
  id: string;
  orientation: "row" | "column";
  children: LayoutNode[];
  sizes: number[];
  agentId?: string;
}

export interface LayoutPaneNode {
  kind: "pane";
  id: string;
  paneId: string;
}

export type LayoutNode = LayoutGroupNode | LayoutPaneNode;
```

Rules:

- Split tree uses n-ary `children[]` and `sizes[]`. `sizes.length` must equal `children.length` for every group. [Basis: C3]
- `sizes[]` stores fractions that sum to 1 after normalization. The UI may display percentages, but persistence stores fractions. [Basis: C3, R1]
- Pane kinds are only `transcript`, `terminal`, `wire`, and `artifact`. [Basis: C4]
- Layout modes are only `tiling` and `floating`. [Basis: C3]
- Artifact provenance uses `session_id` and `turn_id`. [Basis: C5]
- Content type enum is `markdown | image | code | json | text | unknown`. [Basis: C5]

## Design system

### Scene and theme

Users operate this cockpit on a desktop monitor while supervising active agents, scanning evidence, and occasionally typing into a real terminal. The ambient scene is a focused engineering room, often dim, with several streaming panes. A dark, low glare base is appropriate because it keeps terminal and wire surfaces legible while reducing fatigue during long monitoring sessions. [Basis: C4, U2, A1]

The existing product language already uses dark layers, stable agent rails, one bright accent, JetBrains Mono, and square corners. Keep that language and add cockpit specific tokens rather than replacing the app theme. [Basis: R6]

### CSS custom properties

```css
:root {
  color-scheme: dark;

  /* Surface scale, derived from the current www dark layers. */
  --cockpit-well: oklch(0.08 0.006 250);
  --cockpit-canvas: oklch(0.11 0.006 250);
  --cockpit-surface: oklch(0.15 0.006 250);
  --cockpit-raised: oklch(0.20 0.008 250);
  --cockpit-hover: oklch(0.25 0.010 250);

  /* Text. Primary and muted meet WCAG AA on canvas. Faint is chrome only. */
  --cockpit-text: oklch(0.88 0.010 80);
  --cockpit-text-muted: oklch(0.68 0.008 250);
  --cockpit-text-faint: oklch(0.56 0.008 250);
  --cockpit-text-inverse: oklch(0.11 0.006 250);

  /* Borders and focus. */
  --cockpit-edge: oklch(0.28 0.008 250);
  --cockpit-edge-strong: oklch(0.34 0.010 250);
  --cockpit-focus: oklch(0.88 0.030 82);
  --cockpit-focus-ring: 0 0 0 2px var(--cockpit-canvas), 0 0 0 4px var(--cockpit-focus);

  /* Agent categorical rails. Preserve current role distinction. */
  --agent-rail-0: oklch(0.72 0.075 230);
  --agent-rail-1: oklch(0.76 0.085 155);
  --agent-rail-2: oklch(0.76 0.085 78);
  --agent-rail-3: oklch(0.70 0.090 300);
  --agent-rail-4: oklch(0.72 0.090 12);
  --agent-rail-5: oklch(0.72 0.080 180);

  /* Rawness gradient. */
  --rawness-transcript: oklch(0.83 0.025 160);
  --rawness-terminal: oklch(0.80 0.030 82);
  --rawness-wire: oklch(0.76 0.050 28);
  --rawness-artifact: oklch(0.82 0.035 275);

  /* Spacing scale. */
  --space-0: 0;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  /* Type. */
  --font-ui: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  --font-code: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  --type-caption: 11px;
  --type-label: 12px;
  --type-body: 13px;
  --type-body-lg: 14px;
  --type-title: 18px;
  --type-display: 26px;
  --line-tight: 1.2;
  --line-body: 1.45;
  --line-readable: 1.6;

  /* Square language, inherited from www. */
  --radius-none: 0;
  --radius-control: 0;
  --radius-pane: 0;

  /* Elevation. */
  --shadow-pane: 0 14px 34px rgb(0 0 0 / 0.32), inset 0 1px 0 rgb(255 255 255 / 0.03);
  --shadow-pane-active: 0 18px 44px rgb(0 0 0 / 0.44), 0 0 0 1px rgb(232 228 220 / 0.22);
  --shadow-float: 0 28px 90px rgb(0 0 0 / 0.52), inset 0 1px 0 rgb(255 255 255 / 0.04);

  /* Motion. */
  --ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);
  --ease-out-quint: cubic-bezier(0.22, 1, 0.36, 1);
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-feedback: 90ms;
  --duration-state: 160ms;
  --duration-layout: 280ms;
  --duration-mode: 480ms;
  --duration-artifact: 220ms;
}
```

Contrast requirements:

- Primary body text on canvas must meet at least 4.5:1. Current `#dcdcdc` on `#080808` measured at 14.6:1. [Basis: R6, A1]
- Muted text on canvas must meet at least 4.5:1 when it carries meaning. Current `#949494` on `#080808` measured at 6.6:1. [Basis: R6, A1]
- Faint labels may be decorative chrome only. Do not use faint labels as the only way to convey state. [Basis: A1]
- Focus rings must be at least 2px and contrast at least 3:1 against adjacent colors. [Basis: A1]

## Layout patterns

### Breakpoints

The desktop app supports resizing, external monitors, and constrained laptop windows. These breakpoints are content driven.

| Token | Width | Canvas behavior | Launcher behavior | Basis |
|---|---:|---|---|---|
| `bp-min` | below 840px | Show minimum size guard with workspace switcher and current focused pane only. Disable floating editing. | Single column list, search first. | A1, U2 |
| `bp-compact` | 840 to 1023px | One focused pane plus collapsible pane rail. Artifacts use bottom shelf. | Single column tiles, metadata stacked. | A1, C6 |
| `bp-workbench` | 1024 to 1279px | Two zones: focused pane and secondary rail. Split editing allowed through command bar. | Two column tiles when space permits. | C3, U2 |
| `bp-studio` | 1280 to 1599px | Default three pane agent row: transcript 34%, terminal 42%, wire 24%. Artifacts bottom shelf. | Gallery with command palette overlay. | C4, C6 |
| `bp-lab` | 1600 to 2199px | Agent rows or columns plus right artifact rail. Floating mode shows mini map. | Gallery with pinned workspaces and rich metadata. | C3, C5 |
| `bp-wall` | 2200px and up | Multi agent canvas can show two agent groups and artifact rail at once. Mini map persistent. | Gallery shows canvas thumbnails. | C3, C6 |

### Default presets

Presets are saved split tree templates. They never change pane content contracts. [Basis: C1, C3]

1. `rawness-row`, default for one agent.
   - Structure: `row(children: [transcript, terminal, wire], sizes: [0.34, 0.42, 0.24])`.
   - Rationale: clean transcript starts the scan, terminal holds action, wire sits at the raw edge. [Basis: C4, U2]
2. `agent-stack`, default for multiple agents at `bp-studio` and wider.
   - Structure: `column(children: [agentGroup...], sizes: even)`, each group uses `rawness-row`.
   - Rationale: supports comparing agents while retaining the same internal gradient. [Basis: C2, C4]
3. `terminal-command`.
   - Structure: terminal 70%, transcript and wire docked at 15% each.
   - Rationale: terminal is the single keyboard input surface in v1. [Basis: C4]
4. `wire-audit`.
   - Structure: wire 50%, transcript 30%, terminal 20%, artifacts rail visible.
   - Rationale: wire versus transcript comparison is the product. [Basis: C4]
5. `artifact-review`.
   - Structure: artifact 52%, transcript 24%, wire 24%, terminal docked.
   - Rationale: artifact provenance jump needs source context without stealing focus. [Basis: C5]
6. `focus-plus-dock`.
   - Structure: active pane 78%, dock group 22%.
   - Rationale: zoom focus is a first class layout, not an overlay. [Basis: C3]

### Canvas regions

- Header strip: workspace name, branch, live agent count, capture health, layout mode, current preset. Minimum height 44px. [Basis: C6, A1]
- Command bar: layout controls, preset switcher, add agent, artifact rail toggle. Uses APG toolbar roving focus. [Basis: A2]
- Canvas body: owns tiling and floating geometry. No product content imports in the engine. [Basis: C1]
- Pane chrome: title, agent rail, kind badge, live state, focus button, split controls, overflow menu. [Basis: C2, A1]
- Artifact rail or shelf: calm artifact arrivals, pin and dismiss, provenance. [Basis: C5]
- Leader overlay: transient keyboard command hint after leader key. [Basis: U1, A2]

## Interaction model

### Workspace launcher

Explore three directions:

1. Project gallery.
   - Workspace tiles with canonical path, git branch, last activity, live agent count, capture health, last layout preset, latest artifact thumbnail, and pinned state.
   - Strong for recognition and return visits. [Basis: C6, U2]
2. Command palette launcher.
   - One search input across remembered workspaces, recent paths, git branches, and create actions.
   - Strong for experts and keyboard first users. [Basis: U2, A2]
3. Spatial recents.
   - Recent workspaces arranged as remembered canvas thumbnails.
   - Strong for visual recall once thumbnails are reliable. [Basis: C6]

Recommended direction: project gallery with command palette overlay.

Rationale: the gallery teaches workspace memory and metadata, while the palette keeps expert throughput high. Spatial recents should wait until canvas thumbnails are generated from layout state rather than screenshots. [Basis: C6, U2, A1]

Create, open, remember flow:

1. Create.
   - Primary action: `Open workspace`.
   - User selects or drops a folder. The app resolves canonical path and computes workspace identity using the existing slug and hash path model. [Basis: R1]
   - Before opening, show name, path, git branch, and whether history already exists for the canonical identity.
   - If the path cannot be read, show inline error on the tile creation panel.
2. Open.
   - Selecting a remembered workspace opens the canvas immediately.
   - Provider choice is deferred to `Add agent` inside the canvas. [Basis: C6]
   - The canvas restores last layout mode, preset, pinned artifacts, and last focused pane.
3. Remember.
   - Workspace tiles sort by pinned first, live agents second, recent activity third.
   - Closing a workspace writes last layout state. Crash recovery reads the last persisted state and marks agents as ended if the backend reports no live process.
4. Empty state.
   - If no remembered workspaces exist, show one primary action, one drag target, and one concise explanation: `Open a workspace to capture live agent traffic.`
   - Do not show provider buttons on this screen. [Basis: C6]

### Layout editing

Entry points:

- Pointer: `Edit layout` button in command bar.
- Keyboard: `Ctrl+B` then `e`.
- Command palette: `Layout: edit`.

Edit mode behavior:

- Gutters expand to 10px visual handles with 24px hit zones. [Basis: A1]
- Pane headers show split controls: add row, add column, balance, move, zoom, close, save preset.
- Dragging a split handle previews final fractions with live percentage labels.
- Keyboard equivalent exists for every drag: focus handle with `Tab`, resize with arrows, resize faster with `Shift+Arrow`, balance with `B`, confirm with `Enter`, cancel with `Escape`. [Basis: A1, A2]
- Pointer equivalent for keyboard shortcuts exists in the command bar. [Basis: A1]

Split behavior:

- Add row inserts a sibling below the active pane in the nearest column oriented group.
- Add column inserts a sibling after the active pane in the nearest row oriented group.
- If the nearest group orientation differs, wrap the pane in a new group and rebalance the parent.
- New groups use n-ary `children[]` and `sizes[]`. [Basis: C3]
- Minimum pane size: 260px wide by 180px tall in tiling. If the viewport cannot satisfy minimums, collapse lowest priority panes into a dock.

### Preset switching

- Preset switcher shows current preset name, mode, and a thumbnail from split geometry.
- Switching presets animates current panes into new rectangles using FLIP.
- Content subscriptions do not remount during preset switch. A pane may change size, never identity. [Basis: C1, C7]
- Preset thumbnails show only pane kinds and agent rails, not content.
- User saved presets appear after built in presets and are scoped to workspace.

### Zoom focus

- Trigger: pane header focus button, double click pane header, `Ctrl+B` then `z`, or command palette.
- Behavior: active pane expands to focus area, other panes dock as labelled rails. Artifact rail remains available but collapsed unless the artifact pane is active.
- Restore: `Escape`, repeat zoom command, or click `Restore layout`.
- Focus management:
  - If the zoomed pane is terminal, move DOM focus into terminal after animation completes.
  - If the zoomed pane is transcript, wire, or artifact, move focus to the pane heading with `tabindex="-1"` so screen reader users hear context before controls. [Basis: A2]
- Zoom state persists only as part of the current session state. Saved presets store the underlying split tree, not transient zoom.

### Tiling and floating mode

Tiling:

- Split tree drives all rectangles.
- Panes can be resized only through split handles and layout commands.
- Z order is implicit: focus ring and active rail show the current pane.

Floating:

- Same pane identities move to saved floating rectangles.
- Panes can be dragged by header, resized by edges, and snapped to guides.
- `Tab` order follows DOM order by agent and pane kind, not visual z order, unless the user explicitly changes pane order. This keeps keyboard and screen reader order predictable. [Basis: A2]
- Floating has a mini map at `bp-lab` and wider. Compact widths use the focused pane plus rails.

Mode switch showpiece:

1. Capture old rects.
2. Compute new rects from same pane ids.
3. Freeze content layers visually, keep live streams running.
4. Animate panes with transform and opacity only.
5. Fade gutters to floating outlines or outlines to gutters.
6. Restore normal content paint and focus.

The showpiece is spatial continuity, not spectacle. It must help users understand that the same panes moved between arrangements. [Basis: C3, A1]

### Keyboard leader

Default leader: `Ctrl+B`, matching tmux convention. [Basis: U1]

Terminal pass through rule:

- `Ctrl+B` enters cockpit leader mode and is not sent to the terminal.
- `Ctrl+B` then `Ctrl+B` sends literal `Ctrl+B` to the terminal.
- Leader key is rebindable in settings because terminal users may have existing bindings. [Basis: A1, U1]

Leader commands:

| Sequence | Action |
|---|---|
| `Ctrl+B z` | Toggle zoom focus. |
| `Ctrl+B h/j/k/l` | Move focus left, down, up, right by pane geometry. |
| `Ctrl+B e` | Toggle layout edit mode. |
| `Ctrl+B p` | Open preset switcher. |
| `Ctrl+B m` | Toggle tiling and floating. |
| `Ctrl+B a` | Add agent. |
| `Ctrl+B r` | Reset current preset. |
| `Ctrl+B [` | Focus transcript pane for active agent. |
| `Ctrl+B \` | Focus terminal pane for active agent. |
| `Ctrl+B ]` | Focus wire pane for active agent. |
| `Ctrl+B 1..9` | Focus agent group by visible order. |
| `Ctrl+B ?` | Open shortcut help. |

Leader overlay:

- Appears after leader key within 80ms.
- Stays visible for 1800ms or until command completes.
- Shows available keys for current context.
- Uses `role="status"` with polite announcement on first open per session only, then visual only to avoid repeated screen reader noise. [Basis: A2]

### Pointer affordances

- Pane headers are drag handles in floating mode and focus handles in tiling mode.
- Split handles appear on hover, focus, and edit mode. They are always reachable by keyboard.
- Snap zones are visible while dragging only. Zones are announced through a status region when dragging starts and when a snap target changes. [Basis: A1, A2]
- Cursor styles:
  - Split handle: `col-resize` or `row-resize`.
  - Floating drag: `grab`, then `grabbing`.
  - Disabled handle: default cursor plus disabled style, not invisible.

### Artifact arrival and provenance

Artifact rail placement:

- `bp-lab` and wider: right rail, 320px default, resizable to 240 to 520px.
- `bp-studio` and narrower: bottom shelf, 180px default, collapsible.
- Zoom mode: collapsed rail with count badge unless the active pane is an artifact.

Spawn behavior:

- New artifact creates or updates an `artifact` pane through the layout engine event API. [Basis: C5]
- Dedupe key: normalized artifact path when present. If no path exists, use a stable event id from `session_id`, `turn_id`, content type, and ordinal.
- Provenance keys shown in UI are exactly `session_id` and `turn_id`. [Basis: C5]
- Same path updates one pane. The update does not create a second pane. [Basis: C5]
- Update feedback: 220ms edge glow, timestamp change, and `Updated from turn N` microcopy.
- New arrival feedback: rail item slides 12px from rail edge and fades in. No layout focus changes. [Basis: C5, A1]
- User click on provenance selects the originating turn in transcript and wire panes, scrolls it into view, and applies a 1400ms source highlight.
- If source pane is not visible, show `Open source panes` inline action. Do not move layout without user action. [Basis: C5, A1]

Lifecycle:

- Pin keeps artifact in rail and persists it with workspace layout.
- Dismiss removes rail item from current workspace state.
- Auto retire moves unpinned artifacts to `Recent artifacts` after 30 minutes of no updates or when count exceeds 20.
- Unknown content uses a safe text shell with copy path, open external, and provenance. [Basis: C5, A1]

### Rawness gradient visual story

The gradient runs from interpreted evidence to raw transport evidence.

| Pane kind | Visual role | Surface treatment | Header label | Basis |
|---|---|---|---|---|
| `transcript` | Clean narrative | More spacing, line length capped at 75ch, calm green marker, rendered blocks. | `Transcript` | C4, A1 |
| `terminal` | Live operation | Dense monospace, stronger caret state, warm ivory marker, active input indicator. | `Terminal` | C4, U1 |
| `wire` | Raw evidence | Highest density, amber marker, byte and header affordances, visible request ids. | `Wire` | C4, R3 |
| `artifact` | Produced output | Purple marker, content type badge, provenance crumb. | `Artifact` | C5 |

Rules:

- Color never carries pane kind alone. Include label, icon shape, and `aria-label`. [Basis: A1]
- Agent rail color identifies agent consistently across all panes. [Basis: R6]
- Rawness increases by density, border texture, and metadata exposure, not by reducing readability. [Basis: C4, A1]
- Transcript, terminal, and wire headers show the same agent id and run state to support cross pane comparison. [Basis: C2, C4]

## Transition choreography

### Motion tokens

| Interaction | Duration | Easing | Properties | Basis |
|---|---:|---|---|---|
| Button press, handle grab | 90ms | `--ease-out-quart` | opacity, transform | A1 |
| Hover or focus affordance | 120ms | `--ease-out-quart` | opacity, outline, shadow | A1 |
| Split resize preview | direct | none while dragging | transform only for overlay labels | A1 |
| Preset switch | 280ms | `--ease-out-quint` | transform, opacity | C3, A1 |
| Zoom focus | 260ms | `--ease-out-quint` | transform, opacity | C3, A1 |
| Agent spawn panes | 320ms total | `--ease-out-quint` | transform, opacity, stagger 55ms | C3 |
| Artifact arrival | 220ms | `--ease-out-quart` | transform 12px, opacity | C5, A1 |
| Tiling to floating | 480ms | `--ease-out-expo` | transform, opacity, shadow | C3, A1 |
| Floating to tiling | 420ms | `--ease-out-expo` | transform, opacity, shadow | C3, A1 |

### Reduced motion

When `prefers-reduced-motion: reduce` is active:

- Layout changes use immediate rect update plus 80ms opacity crossfade.
- No scale, parallax, drift, or long travel.
- Artifact arrival uses static count badge and timestamp update.
- Focus change still receives visible outline and DOM focus update.
- User setting `Motion: minimal` is available inside app and overrides OS no preference. [Basis: A1]

### Performance requirements

- Animate transform and opacity only.
- During FLIP, live terminal and wire streams keep receiving data. Visual freeze may use a compositor layer, not a data pause. [Basis: C7]
- Do not animate width, height, top, left, grid tracks, or scroll position during layout transition.
- Use `will-change` only while an animation is scheduled, then remove it.
- Keep mode switch under 500ms and input responsive throughout. [Basis: A1]

## Component specifications

### Shared types

```ts
export interface PaneModel {
  id: string;
  kind: PaneKind;
  agentId?: string;
  title: string;
  liveState: "idle" | "starting" | "live" | "paused" | "error" | "ended";
}

export interface WorkspaceSummary {
  workspaceId: string;
  name: string;
  canonicalPath: string;
  gitBranch?: string;
  dirty?: boolean;
  lastActivityAt?: string;
  liveAgentCount: number;
  lastPreset?: string;
  pinned: boolean;
  captureHealth: "unknown" | "healthy" | "warning" | "error";
}

export interface ArtifactModel {
  id: string;
  title: string;
  contentType: ContentType;
  path?: string;
  provenance: ArtifactProvenance;
  updatedAt: string;
  pinned: boolean;
  updateCount: number;
}
```

### WorkspaceLauncher

Purpose: Open, create, and remember workspaces with rich metadata. [Basis: C6]

```ts
export interface WorkspaceLauncherProps {
  workspaces: WorkspaceSummary[];
  query: string;
  selectedWorkspaceId?: string;
  isLoading: boolean;
  error?: string;
  onQueryChange(query: string): void;
  onOpen(workspaceId: string): void;
  onCreateFromPath(path: string): void;
  onTogglePinned(workspaceId: string): void;
  onForget(workspaceId: string): void;
}
```

State matrix:

| State | Behavior |
|---|---|
| Default | Search input focused on first launch, pinned and recent workspaces visible. |
| Hover | Tile raises one surface step, branch and path remain visible. |
| Active | Pressed tile darkens for 90ms, then opens workspace. |
| Focus | 2px focus ring on tile or command, visible name announced. |
| Disabled | Open action disabled only when workspace path is unavailable. Show reason inline. |
| Loading | Skeleton rows for metadata, search remains usable. |
| Error | Inline error under affected tile or create panel. No global blocking state. |
| Empty | One primary action, drop target, and recent path search. |

Responsive behavior:

- `bp-min` and `bp-compact`: one column, metadata wraps under name.
- `bp-workbench`: two columns if each tile remains at least 360px.
- `bp-studio` and wider: gallery plus command palette overlay.

Accessibility:

- Search is labelled `Search workspaces`.
- Tiles are buttons or links with visible name matching accessible name. [Basis: A1]
- Pin is a toggle button with stable label and `aria-pressed`. [Basis: A2]
- Drop target has equivalent `Open workspace` button. [Basis: A1]

Animation:

- Tile hover 120ms.
- Open transition 220ms fade to canvas shell.
- Reduced motion uses instant route change plus focus placement.

### CanvasFrame

Purpose: Host one workspace canvas, global command bar, mode state, and status regions. [Basis: C2, C3]

```ts
export interface CanvasFrameProps {
  workspace: WorkspaceSummary;
  mode: LayoutMode;
  layout: LayoutNode;
  panes: PaneModel[];
  focusedPaneId?: string;
  isRestoring: boolean;
  error?: string;
  onModeChange(mode: LayoutMode): void;
  onLayoutChange(layout: LayoutNode): void;
  onFocusPane(paneId: string): void;
  onOpenLauncher(): void;
}
```

State matrix:

| State | Behavior |
|---|---|
| Default | Header, command bar, canvas, and status region visible. |
| Hover | Canvas chrome reveals non critical handles. Content surfaces do not shift. |
| Active | Active pane rail and focus outline show current pane. |
| Focus | Header skip target and canvas region receive visible outline. |
| Disabled | Layout commands disabled while workspace restore is incomplete. |
| Loading | Restore skeleton uses saved geometry placeholders. |
| Error | Workspace level error appears in header with retry. Existing panes remain visible if safe. |
| Empty | Empty canvas prompts `Add agent` and explains provider choice. |

Responsive behavior:

- `bp-min`: guard view with focused pane only.
- `bp-compact`: focused pane plus rail.
- `bp-studio`: default rawness row.
- `bp-lab` and `bp-wall`: multi agent and artifact rail layouts.

Accessibility:

- Canvas uses `role="application"` only while leader or layout edit mode is active. Outside those modes, prefer semantic regions. [Basis: A2]
- Status updates use one polite live region for connection, artifact, and layout confirmations.
- DOM order follows agent order and pane kind order.

Animation:

- All layout mutations use FLIP.
- Workspace restore uses opacity reveal only after first rect calculation.

### LayoutCommandBar

Purpose: Primary controls for presets, mode, edit layout, add agent, artifacts, and help. [Basis: C3, C6]

```ts
export interface LayoutCommandBarProps {
  mode: LayoutMode;
  currentPresetId: string;
  canEditLayout: boolean;
  artifactCount: number;
  liveAgentCount: number;
  onPresetOpen(): void;
  onModeToggle(): void;
  onEditToggle(): void;
  onAddAgent(): void;
  onArtifactToggle(): void;
  onHelpOpen(): void;
}
```

State matrix:

| State | Behavior |
|---|---|
| Default | One toolbar tab stop, first enabled command remembered. |
| Hover | Button surface moves to hover token, tooltip after 600ms. |
| Active | Pressed state for 90ms, action fires on pointer up or key activate. |
| Focus | Roving focus, arrow keys move within toolbar. |
| Disabled | Disabled buttons remain focusable with `aria-disabled` if explanation is useful. |
| Loading | Add agent and restore commands show spinner and keep label. |
| Error | Error badge on affected command opens details popover. |
| Empty | `Add agent` is primary when no panes exist. |

Responsive behavior:

- `bp-min`: overflow into command palette, keep workspace switcher and add agent visible.
- `bp-compact`: icon plus label for primary, icons for secondary with accessible names.
- `bp-studio` and wider: full labels.

Accessibility:

- `role="toolbar"`, labelled by workspace name. [Basis: A2]
- Arrow keys move between controls. `Home` and `End` jump first and last. [Basis: A2]
- Buttons activate with `Enter` and `Space`. [Basis: A2]

Animation:

- Toolbar affordances use 120ms opacity and shadow.
- Tooltip never covers focused control.

### PaneShell

Purpose: Content agnostic shell for transcript, terminal, wire, and artifact panes. [Basis: C1, C4]

```ts
export interface PaneShellProps {
  pane: PaneModel;
  agentRailColor?: string;
  isFocused: boolean;
  isZoomed: boolean;
  isDragging: boolean;
  isResizable: boolean;
  error?: string;
  children: React.ReactNode;
  onFocus(): void;
  onZoomToggle(): void;
  onCloseRequest(): void;
  onMoveRequest(direction: "left" | "right" | "up" | "down"): void;
  onSplitRequest(orientation: "row" | "column"): void;
}
```

State matrix:

| State | Behavior |
|---|---|
| Default | Header, kind badge, live state, agent rail, and content slot visible. |
| Hover | Header controls reveal. Pane content stays stable. |
| Active | Focused pane uses active shadow and rail intensity. |
| Focus | Header receives visible ring. Content focus is delegated to child when appropriate. |
| Disabled | Move and split controls disabled below minimum size. Reason available in tooltip. |
| Loading | Child slot shows pane specific skeleton, header remains usable. |
| Error | Header shows error badge, child slot shows recover or reconnect action. |
| Empty | Empty child slot explains missing subscription or no artifacts. |

Responsive behavior:

- `bp-min`: only one pane shell visible, others become rails.
- `bp-compact`: shell headers compact to icon, kind, title.
- `bp-studio` and wider: full metadata.

Accessibility:

- Root region labelled `Agent {agentId} {pane.kind}`.
- Header controls are real buttons.
- Close or dismiss asks for confirmation only when content would be lost from current layout. If a dialog is used, follow APG modal dialog focus return. [Basis: A2]

Animation:

- Focus shadow 120ms.
- Zoom and preset moves handled by layout engine, not shell internals.

### SplitHandle

Purpose: Resize n-ary split groups by pointer, keyboard, and single pointer alternatives. [Basis: C3, A1]

```ts
export interface SplitHandleProps {
  groupId: string;
  beforeChildId: string;
  afterChildId: string;
  orientation: "row" | "column";
  value: number;
  minBefore: number;
  minAfter: number;
  disabled?: boolean;
  onChange(value: number): void;
  onCommit(value: number): void;
  onCancel(): void;
}
```

State matrix:

| State | Behavior |
|---|---|
| Default | 1px visual gutter, 24px hit zone. |
| Hover | Gutter expands visually to 4px, hit zone unchanged. |
| Active | Resize preview labels show percentages. |
| Focus | Handle becomes visible with ring and current percentage. |
| Disabled | Gutter visible but muted. Tooltip explains minimum pane size. |
| Loading | Not applicable. Keep handle disabled during layout restore. |
| Error | If commit fails, revert to prior size and announce failure. |
| Empty | Hidden when group has fewer than two children. |

Responsive behavior:

- All breakpoints keep 24px hit zone.
- `bp-min` hides split handles and shows disabled explanation in command bar.

Accessibility:

- Use `role="separator"`, `aria-orientation`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`. [Basis: A2]
- Arrow keys resize 2%. `Shift+Arrow` resizes 10%. `Home` and `End` move to min and max.
- Pointer drag has command alternatives: `Resize left`, `Resize right`, `Balance`. [Basis: A1]

Animation:

- While dragging, resize is direct with no easing.
- On commit, neighboring chrome settles in 120ms.

### PresetSwitcher

Purpose: Switch and save layout presets without remounting pane content. [Basis: C3]

```ts
export interface PresetSwitcherProps {
  presets: Array<{ id: string; name: string; mode: LayoutMode; preview: LayoutNode; saved: boolean }>;
  currentPresetId: string;
  isOpen: boolean;
  error?: string;
  onOpenChange(open: boolean): void;
  onSelect(presetId: string): void;
  onSaveCurrent(name: string): void;
  onDelete(presetId: string): void;
}
```

State matrix:

| State | Behavior |
|---|---|
| Default | Current preset shown in command bar. |
| Hover | Preset row previews target geometry in mini thumbnail. |
| Active | Selected preset applies on click or key activation. |
| Focus | Roving focus through preset list. |
| Disabled | Delete disabled for built in presets. |
| Loading | Applying preset locks selection until FLIP starts, then unlocks. |
| Error | Failed save shows inline form error and keeps draft name. |
| Empty | If no user presets, show built in presets and save prompt. |

Responsive behavior:

- `bp-min` and `bp-compact`: full screen popover sheet inside app window.
- `bp-workbench` and wider: anchored popover under command bar.

Accessibility:

- Use button list or listbox. If listbox, implement APG keyboard behavior.
- Save form validates on submit and on blur, not on every keystroke. [Basis: A1]

Animation:

- Popover enters 160ms fade and 6px translate.
- Preset application uses layout FLIP only.

### AgentLauncher

Purpose: Add a claude or codex run inside the current workspace. [Basis: C6, R2]

```ts
export interface AgentLauncherProps {
  isOpen: boolean;
  providers: Array<{ id: "claude" | "codex"; label: string; available: boolean; reason?: string }>;
  workingDirectory: string;
  isLaunching: boolean;
  error?: string;
  onOpenChange(open: boolean): void;
  onLaunch(providerId: "claude" | "codex"): void;
}
```

State matrix:

| State | Behavior |
|---|---|
| Default | Provider choices shown with current workspace path. |
| Hover | Provider row reveals launch details. |
| Active | Launch button enters loading and closes only after first agent state event. |
| Focus | Initial focus on recommended available provider. |
| Disabled | Unavailable provider row stays visible with reason. |
| Loading | Button label stays `Launching claude` or `Launching codex`. |
| Error | Inline error with retry and copy diagnostics. |
| Empty | In empty canvas, `Add agent` is primary call to action. |

Responsive behavior:

- `bp-min` to `bp-compact`: sheet from bottom within app window.
- `bp-workbench` and wider: popover or side panel.

Accessibility:

- Provider labels must be part of accessible name. [Basis: A1]
- If implemented as dialog, focus moves inside and returns to invoking button on close. [Basis: A2]

Animation:

- Agent spawn creates placeholder pane geometry within 160ms.
- Transcript, terminal, and wire panes appear with 55ms stagger once endpoints are known.

### ArtifactRail

Purpose: Show artifact arrivals, updates, lifecycle controls, and provenance entry points. [Basis: C5]

```ts
export interface ArtifactRailProps {
  artifacts: ArtifactModel[];
  selectedArtifactId?: string;
  placement: "right" | "bottom" | "collapsed";
  isLoading: boolean;
  error?: string;
  onSelect(artifactId: string): void;
  onPinToggle(artifactId: string): void;
  onDismiss(artifactId: string): void;
  onOpenProvenance(artifactId: string): void;
}
```

State matrix:

| State | Behavior |
|---|---|
| Default | Sorted by pinned, recent update, then title. |
| Hover | Item reveals pin, dismiss, provenance. |
| Active | Selected artifact opens or focuses artifact pane. |
| Focus | Item receives ring and announces content type, title, update count. |
| Disabled | Dismiss disabled for pinned items until unpinned. |
| Loading | Skeleton item with rail still sized. |
| Error | Rail level warning with retry event subscription. |
| Empty | Calm message: `Artifacts from tool results land here.` |

Responsive behavior:

- `bp-lab` and wider: right rail.
- `bp-studio` and narrower: bottom shelf.
- Zoom: collapsed badge unless artifact active.

Accessibility:

- Rail is a labelled complementary region.
- New artifact announcement is polite and includes title and content type.
- No automatic focus move on arrival. [Basis: C5, A1]

Animation:

- New item: 220ms fade and 12px translate from rail edge.
- Update: 220ms edge glow, no movement.

### ArtifactSurface

Purpose: Render artifact content through content type renderer while preserving provenance. [Basis: C5]

```ts
export interface ArtifactSurfaceProps {
  artifact: ArtifactModel;
  content?: unknown;
  isLoading: boolean;
  error?: string;
  onOpenExternal(path: string): void;
  onCopyPath(path: string): void;
  onOpenProvenance(): void;
}
```

State matrix:

| State | Behavior |
|---|---|
| Default | Header shows title, content type, path if present, provenance crumb. |
| Hover | Header controls reveal. Content does not reflow. |
| Active | User selected text or image zoom controls work inside surface. |
| Focus | Focus starts at artifact heading, then toolbar, then content. |
| Disabled | External open disabled without path. Reason visible. |
| Loading | Skeleton matched to content type. |
| Error | Safe error shell with retry, copy path, provenance. |
| Empty | `No renderable content yet`, keep provenance visible. |

Responsive behavior:

- `bp-min`: artifact opens as focused pane.
- `bp-compact`: content toolbar wraps to two rows.
- `bp-lab` and wider: can sit in rail or main canvas.

Accessibility:

- Markdown uses semantic headings and lists.
- Image requires alt text from event metadata when available. If absent, use filename and mark as generated output.
- JSON and code render with copy controls and line wrapping toggle.

Animation:

- Dedupe update preserves scroll position when possible.
- Content type change crossfades in 160ms unless reduced motion is active.

### ProvenanceButton

Purpose: Jump from artifact to originating turn across transcript and wire panes. [Basis: C5]

```ts
export interface ProvenanceButtonProps {
  provenance: ArtifactProvenance;
  label?: string;
  sourceAvailable: boolean;
  onJump(provenance: ArtifactProvenance): void;
}
```

State matrix:

| State | Behavior |
|---|---|
| Default | Shows `Turn {turn_id}` or compact source icon with accessible label. |
| Hover | Underline and source pane preview if pane is visible. |
| Active | Executes jump and announces target. |
| Focus | Visible ring and full provenance in tooltip or description. |
| Disabled | Disabled only if source no longer exists. Show copy provenance action. |
| Loading | `Finding source` text while panes resolve. |
| Error | Inline `Source unavailable` with copy ids. |
| Empty | Hidden when artifact lacks provenance, which should be rare and logged. |

Responsive behavior:

- Compact widths show short label but retain full accessible name.
- Wider widths show session and turn details in crumb.

Accessibility:

- Button name includes session id and turn id.
- Jump moves focus to source heading after scroll. [Basis: A2]

Animation:

- Source highlight lasts 1400ms with opacity pulse only.
- Reduced motion uses static outline.

### LeaderOverlay

Purpose: Teach and execute leader commands without permanent chrome. [Basis: U1]

```ts
export interface LeaderOverlayProps {
  active: boolean;
  context: "canvas" | "pane" | "layout-edit" | "terminal";
  commands: Array<{ key: string; label: string; disabled?: boolean }>;
  onCommand(key: string): void;
  onClose(): void;
}
```

State matrix:

| State | Behavior |
|---|---|
| Default | Hidden. |
| Hover | Not pointer primary, but command rows can show hover if pointer moves over overlay. |
| Active | Key command highlights for 90ms before close. |
| Focus | Overlay can receive focus from shortcut help. |
| Disabled | Disabled commands shown with reason. |
| Loading | Command row shows progress if action is async. |
| Error | Failed command message stays until next key or Escape. |
| Empty | If no context commands, show help and rebind shortcut. |

Responsive behavior:

- `bp-min`: overlay uses bottom sheet.
- `bp-compact` and wider: centered compact panel near active pane.

Accessibility:

- First invocation per session announces `Keyboard command mode` politely.
- `Escape` exits without side effects.
- Overlay never traps focus unless opened as full shortcut help. [Basis: A2]

Animation:

- 80ms fade in, 120ms fade out.
- Reduced motion uses immediate show and hide.

## Interaction patterns

### Form behavior

Forms in v1:

- Workspace path entry.
- Saved preset name.
- Optional shortcut rebinding.

Validation:

- Validate required fields on submit.
- Validate path readability after user submits or blurs path field.
- Validate preset duplicate names on submit and blur.
- Keep entered value on error.
- Error text appears directly under field and is referenced with `aria-describedby`. [Basis: A1]

### Popovers and dialogs

Prefer inline panels and popovers for command flows. Use modal dialogs only for destructive confirmation or native folder selection. [Basis: U2, A2]

If a modal dialog is used:

- Use `role="dialog"` and `aria-modal="true"`.
- Initial focus goes to dialog heading if content has explanatory text, otherwise first safe action.
- `Tab` and `Shift+Tab` stay inside dialog.
- `Escape` closes when safe.
- Focus returns to invoking control on close unless the control no longer exists. [Basis: A2]

### Toast and notification system

Use an in app event log, not stacking toast noise, because live agents can generate frequent events. [Basis: C5, A1]

- Critical errors: inline on affected pane or command.
- Recoverable background events: status region plus event log entry.
- Artifact arrivals: artifact rail item, polite announcement, no focus change.
- Agent started or ended: header status and event log.
- Breakpoint or paused transport events: wire pane and header status.

### Loading and skeleton states

- Workspace restore skeleton uses saved geometry if available.
- Agent launch skeleton creates the three pane shells before content is connected.
- Terminal connecting state shows endpoint status and retry.
- Transcript and wire loading states keep prior content visible during reconnect.
- Artifact loading state is content type aware.

### Error handling

- Pane subscription error stays local to that pane.
- Agent process crash marks all panes for that agent with ended state and keeps scrollback. [Basis: C7]
- Layout persistence error shows header warning and local retry. The user can continue working in memory.
- Artifact render error shows safe source shell, not blank space.

## Accessibility requirements

Baseline: WCAG 2.2 AA plus APG keyboard conventions. [Basis: A1, A2]

Keyboard:

- All functionality reachable by keyboard.
- Leader commands have pointer equivalents.
- Drag, split, and resize have keyboard and single pointer alternatives.
- `Tab` order follows DOM order by workspace, command bar, agent group, pane kind, artifact rail.
- No positive `tabindex` values.

Focus:

- Focus ring visible on every interactive element.
- Focus never disappears after pane close, preset switch, mode switch, or artifact jump.
- Focus returns to invoker after popover or dialog close.
- During FLIP, logical focus remains on the same pane id or moves only by explicit user action.

Screen reader:

- Regions labelled: launcher, command bar, canvas, agent group, pane, artifact rail, event log.
- Pane labels include agent id, pane kind, and live state.
- Live updates use polite announcements except explicit errors, which may use assertive only when user action is blocked.
- Artifact provenance button names include session id and turn id.

Pointer and touch:

- Minimum interactive target is 24 by 24 CSS px, with 32 by 32 preferred for cockpit chrome.
- Split handles keep a 24px hit zone even if visual gutter is thinner.
- Hover only reveals shortcuts. It never gates required actions.

Motion:

- Respect `prefers-reduced-motion`.
- App setting can force minimal motion.
- No bounce, elastic, flashing, or endless decorative animation.

Color:

- Text contrast meets WCAG AA.
- State never relies on color alone.
- Agent color is paired with text label and structural position.

Terminal:

- Terminal receives keystrokes except the configured leader sequence.
- Shortcut help documents how to send literal leader to terminal.
- Terminal reconnect preserves scrollback when backend supports replay. [Basis: C7]

## Implementation roadmap

1. Design tokens.
   - Add cockpit CSS custom properties beside existing `www/src/index.css` tokens.
   - Acceptance: contrast checks for text tokens and focus token pass WCAG AA.
2. Layout primitives.
   - Implement `LayoutNode`, rect solver, size normalization, min size collapse, and FLIP measurement.
   - Acceptance: tests prove n-ary `children[]` and `sizes[]`, no binary shape.
3. Pane shell and command bar.
   - Build content agnostic `PaneShell`, `SplitHandle`, `LayoutCommandBar`, and `LeaderOverlay`.
   - Acceptance: no Transport Matters content imports inside layout engine primitives.
4. Launcher.
   - Build project gallery with command palette overlay and workspace metadata.
   - Acceptance: create/open/remember flow uses canonical workspace identity and defers provider choice.
5. Presets and modes.
   - Implement built in presets, saved presets, zoom focus, and tiling to floating transition.
   - Acceptance: pane ids persist across preset and mode changes.
6. Pane bindings.
   - Bind transcript, terminal, wire, and artifact panes through shell slots.
   - Acceptance: transcript and wire reuse existing seams where practical, terminal keeps input surface isolated.
7. Artifact rail and surface.
   - Implement artifact spawn, dedupe to update, lifecycle, and provenance jump.
   - Acceptance: same path updates one artifact pane and does not change focus.
8. Accessibility audit.
   - Keyboard only path: open workspace, add agent, switch preset, resize split, zoom, open artifact, jump provenance.
   - Screen reader pass: labelled regions, status updates, focus restoration.
9. Performance validation.
   - Verify mode switch stays below 500ms and does not pause live streams.
   - Verify layout animation uses transform and opacity only.
10. Slice 1 fit.
   - Launcher to open workspace to add one agent to one live pane in generic shell.
   - Keep later panes and artifact rail behind progressive slices if needed.

## Open questions for orchestrator

1. Artifact event delivery surface.
   - Working assumption: UI consumes a workspace level event bus that includes artifact events derived from transcript and wire records.
2. Floating persistence.
   - Working assumption: persist last tiling split tree and last floating rect map separately per workspace and preset.
3. Shortcut leader default.
   - Working assumption: default `Ctrl+B`, with literal send through `Ctrl+B Ctrl+B` and rebindable setting.
4. Canvas thumbnails in launcher.
   - Working assumption: v1 thumbnail is generated from layout geometry and pane kinds, not a screenshot.
5. Artifact auto retire threshold.
   - Working assumption: unpinned artifacts retire after 30 minutes without update or when unpinned count exceeds 20.
6. Dialog usage.
   - Working assumption: destructive actions use inline confirmation unless native folder selection or serious data loss requires a modal dialog.
7. Minimum supported window size.
   - Working assumption: below 840px, app remains readable through a focused pane guard rather than full layout editing.

## Sources

- Charter: `/Users/alphab/.mdx/projects/transport-matters-desktop-cockpit/CHARTER.md`.
- Repo seams verified with `fmm validate`, `fmm outline`, and line numbered reads on 2026-06-06.
- W3C WCAG 2.2: https://www.w3.org/TR/WCAG22/
- W3C New in WCAG 2.2: https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- W3C Understanding Animation from Interactions: https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html
- WAI ARIA APG keyboard interface: https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/
- WAI ARIA APG toolbar pattern: https://www.w3.org/WAI/ARIA/apg/patterns/toolbar/
- WAI ARIA APG button pattern: https://www.w3.org/WAI/ARIA/apg/patterns/button/
- WAI ARIA APG modal dialog pattern: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
