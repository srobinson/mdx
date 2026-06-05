---
title: dnd-kit state in July 2026 — free-floating panel dragging, edge-docking, resizing
type: research
tags: [dnd-kit, drag-and-drop, react-19, pragmatic-drag-and-drop, react-rnd, floating-panels]
summary: dnd-kit/core v6 is feature-frozen since Dec 2024; the new @dnd-kit/react + @dnd-kit/dom rewrite (v0.5.0, June 2026) is the actively developed line, React 19-ready, and the better fit for free-floating panels with edge docking. Neither offers resizing; react-rnd/re-resizable remain the standard for that.
status: active
source: quick-research
confidence: high
created: 2026-07-11
updated: 2026-07-11
---

## Summary

For a React 19 + Vite app needing free-floating draggable panels with drop-zone edge docking and resizing: use **`@dnd-kit/react` + `@dnd-kit/dom`** (the new rewrite, v0.5.0), not legacy `@dnd-kit/core` v6. Pair it with **`react-rnd`** (or hand-rolled resize handles) for resizing, since dnd-kit has no resize primitives at all. `@dnd-kit/core` v6 still dominates downloads by sheer installed-base inertia but is functionally frozen; all new feature work, bugfixes, and React 19 support land only in the rewrite.

## Details

### 1. `@dnd-kit/core` (legacy v6) — maintained but frozen

- Latest: **6.3.1**, published **2024-12-05**. No release since.
- peerDeps: `react: >=16.8.0` — no explicit React 19 cap, works via React's own back-compat, but no dnd-kit-side React 19 testing/changes.
- Repo (`clauderic/dnd-kit`) not archived, 17.4k stars, 109 open issues, still gets commits — but all recent commits (as of 2026-07) are for the new `@dnd-kit/react`/`@dnd-kit/dom` packages, not `/core`.
- Weekly npm downloads: **16.06M** (huge installed base from years of adoption; this is not a signal of active development, just legacy usage inertia).
- Bundle size: 14.2 kB gzip (core + utilities + accessibility).

### 2. The rewrite — `@dnd-kit/react` / `@dnd-kit/dom` — active, stable-tagged, React 19 supported

- Both at **v0.5.0**, published **2026-06-11** (per GitHub Releases changesets). A `0.5.1-beta` prerelease channel was cut **2026-07-06**, and docs-fix commits landed **2026-07-06** — actively worked on within the last week as of this research.
- npm README badge literally reads "Stable release" (not "beta"/"experimental"), despite the 0.x version number.
- peerDeps: **`react: ^18.0.0 || ^19.0.0`** — explicit React 19 support.
- Architecture: layered — `@dnd-kit/abstract` (framework-agnostic core) → `@dnd-kit/dom` (DOM implementation, drag/drop manager, modifiers, plugins) → thin framework adapters: `@dnd-kit/react`, plus new `@dnd-kit/vue`, `@dnd-kit/svelte`, `@dnd-kit/solid` (all also hit 0.5.0 on 2026-06-11).
- The separate `dnd-kit/docs` GitHub repo was archived 2026-02-21 — docs appear to have been folded into the main monorepo alongside the multi-framework rewrite.
- Weekly npm downloads: `@dnd-kit/react` **720K** — real, growing adoption for a pre-1.0 package, about 1/22 of legacy core's volume but far from experimental-toy-project scale.
- No changelog/discussion language marks the rewrite abandoned; it is the maintainer's (`clauderic`) sole active focus. `future of library & maintenance` issue (#1194) exists on GitHub but its substantive answer wasn't visible in this pass (comments not fetched); the commit/release cadence itself is the stronger signal.

### 3. Free-floating panels + edge-dock zones — recommended pattern

Use the new `@dnd-kit/react` + `@dnd-kit/dom`, not legacy core, because it's where modifiers/collision work is still being fixed (see the 2026-07-06 docs-audit commit correcting several modifier/collision claims) and because it's the only line getting React 19-era attention.

Pattern:
```jsx
import {DragDropProvider} from '@dnd-kit/react';
import {useDraggable} from '@dnd-kit/react';
import {useDroppable} from '@dnd-kit/react';
import {RestrictToWindow} from '@dnd-kit/dom/modifiers';

// Free-floating panel: drag by header, persist x/y on drop
function Panel({id, position}) {
  const {ref, isDragging} = useDraggable({
    id,
    modifiers: [RestrictToWindow], // clamp to viewport like restrictToWindowEdges
  });
  return <div ref={ref} style={{transform: `translate(${position.x}px, ${position.y}px)`}}>...</div>;
}

// Edge-dock zone
function DockZone({id, edge}) {
  const {ref, isDropTarget} = useDroppable({id, accept: ['panel']});
  return <div ref={ref} className={`dock dock-${edge}`} />;
}

<DragDropProvider
  onDragEnd={(event) => {
    const {source, target} = event.operation;
    if (target) {
      // docked: snap to target.id edge
    } else {
      // free-floating: persist delta into x/y state
    }
  }}
>
  <Panel id="p1" position={pos} />
  <DockZone id="dock-left" edge="left" />
</DragDropProvider>
```

Key modifiers (imported from `@dnd-kit/dom/modifiers`, not `@dnd-kit/modifiers` — that package name was for legacy core):
- `RestrictToWindow` — viewport clamp, equivalent to legacy `restrictToWindowEdges`.
- `RestrictToElement.configure({element: () => container.current})` — restrict drag to a container; must pass a function (evaluated at drag start), not a direct ref value, or it captures `null` on first render.
- `RestrictToVerticalAxis` / `RestrictToHorizontalAxis` (from `@dnd-kit/abstract/modifiers`) — axis locking.

Modifiers can be set globally on `DragDropProvider` or per-draggable (per-draggable overrides global).

Legacy `@dnd-kit/core` uses the older pattern instead — `DndContext` + `useDraggable` + `onDragEnd` delta + `CSS.Translate.toString(transform)` + modifiers from the separate `@dnd-kit/modifiers` package (`restrictToWindowEdges`, `restrictToParentElement`). This still works and is well documented, but is the frozen line.

### 4. Resizing — not offered by either; hand-roll or use a separate lib

- Neither `@dnd-kit/core` nor the new `@dnd-kit/react`/`@dnd-kit/dom` has any resize primitives — confirmed via package descriptions/keywords (drag-and-drop only, no "resize" keyword anywhere).
- What people actually use for resizable *floating* panels in 2025/2026:
  - **`react-rnd`** (10.5.3, published 2026-03-10, 1.16M weekly downloads) — combines drag + resize in one component (wraps `react-draggable` + `react-resizable` internally). This is the closest ready-made match to "free-floating panel that both drags and resizes," and is actively maintained.
  - **`re-resizable`** (6.11.2, published 2025-02-24 — slower-moving but mature/stable; it's the resize engine `react-rnd` is built on) — resize-only, pair with your own drag logic (e.g. dnd-kit) if you want drag and resize handled by separate, composable systems.
  - **`react-resizable-panels`** (4.12.1, published 2026-07-03, very active) — NOT for this use case; it's for adjacent split-pane/sortable layouts (like VS Code panel groups), not independently-positioned floating windows.
  - Hand-rolled resize handles (pointer-events on corner/edge divs, updating width/height state) remain common and are trivial to combine with dnd-kit's drag handling since dnd-kit only owns the `transform`/position, leaving size as a separate concern.
- Practical recommendation: if panels need both free drag AND resize, `react-rnd` alone may be simpler than composing dnd-kit + a resize lib, unless you specifically need dnd-kit's collision detection / drop-zone system for the edge-docking behavior — in which case, use dnd-kit for drag+dock, and layer `re-resizable` or hand-rolled handles on top for resize, since the two concerns don't conflict (resize doesn't need drag-and-drop semantics).

### 5. Community sentiment 2026 / bundle size

- **dnd-kit remains the default recommendation** for most React drag-and-drop in 2026 per current comparison write-ups (Puck's "Top 5 Drag-and-Drop Libraries for React in 2026", PkgPulse guides): small, accessible, framework-agnostic, best docs/ecosystem for typical cases.
- **Pragmatic drag-and-drop (Atlassian)** is the pick specifically for extreme scale (thousands of items), file drag targets, or external drag sources, where you're willing to hand-roll collision detection and drop indicators yourself for lower overhead. It has NOT displaced dnd-kit as the default; it's positioned as the choice for Jira/Trello-scale performance needs.
- `@atlaskit/pragmatic-drag-and-drop` npm: latest **2.0.1**, published **2026-06-17**; repo pushed **2026-07-10**, 12.7k stars, very active. Weekly downloads: 1.07M.
- Bundle size: dnd-kit core+utilities+accessibility ≈ **14.2 kB gzip**. Pragmatic DnD's top-level meta-package is nearly empty (164 B gzip) because it re-exports from granular subpaths (e.g. `@atlaskit/pragmatic-drag-and-drop/element/adapter`); Pragmatic's actual per-feature adapters are commonly cited elsewhere as coming in smaller than dnd-kit for equivalent functionality, consistent with its "core is ~4.7 kB, opt-in the rest" design philosophy — this research did not get a clean bundlephobia read on the specific adapter subpath (rate-limited), so treat the "Pragmatic wins on bundle size" claim as directionally right per community consensus rather than independently re-verified here.
- No signal found that dnd-kit is being abandoned. The opposite: multi-framework expansion (Vue/Svelte/Solid packages, all hit 0.5.0 same day) and weekly commits indicate the rewrite is the maintainer's active investment, not a dead branch.

## Sources

- npm registry (`npm view`) for `@dnd-kit/core`, `@dnd-kit/react`, `@dnd-kit/dom`, `@atlaskit/pragmatic-drag-and-drop`, `react-rnd`, `re-resizable`, `react-resizable-panels`
- GitHub API: `clauderic/dnd-kit` repo metadata, releases, recent commits; `atlassian/pragmatic-drag-and-drop` repo metadata
- https://dndkit.com/react/guides/modifiers/
- https://dndkit.com/react/guides/migration/
- https://dndkit.com/react/quickstart/
- https://puckeditor.com/blog/top-5-drag-and-drop-libraries-for-react (2026)
- https://www.pkgpulse.com/guides/dnd-kit-vs-react-beautiful-dnd-vs-pragmatic-drag-drop-2026
- npmjs.org downloads API (weekly points, 2026-07-04 to 2026-07-10)
- bundlephobia API (partial, rate-limited during this session)

## Open Questions

- Did not fetch full comment thread on GitHub issue #1194 (`future of library & maintenance`) — would give a direct maintainer statement on core v6's long-term status if needed.
- Did not get a clean bundlephobia read on `@atlaskit/pragmatic-drag-and-drop/element/adapter` specifically (429 rate limit); the "Pragmatic is smaller" claim rests on community consensus, not a fresh independent measurement.
- Did not verify whether `@dnd-kit/react`'s sortable/dock-zone collision detection has known issues at panel-count scales relevant to this app (likely irrelevant for a small number of floating panels).
