---
title: tldraw as rendering engine for manicure Trace/Topology view
type: research
tags: [manicure, tldraw, canvas, diagram, topology, licensing, react]
summary: tldraw technically fits the read-only diagram use case, but its non-OSS license and ~12MB unpacked bundle make it the wrong tool for manicure; React Flow is the recommended alternative.
status: active
source: github-researcher
confidence: high
created: 2026-04-17
updated: 2026-04-17
---

## Verdict

**Don't use tldraw.** It is not open source in any meaningful sense (prohibits Production use without a paid License Key), ships a runtime watermark enforcer, and is massively over-scoped for a read-only topology view. Use **React Flow** (MIT) instead.

## What tldraw gives us

- **Custom shapes** via `ShapeUtil` / `BaseBoxShapeUtil` subclasses with a `component(shape)` React method — clean API, proven by 40+ built-in shape utils (`packages/tldraw/src/lib/shapes/*`).
- **Programmatic shape creation**: `editor.createShape(...)`, `editor.createShapes([...])` (`packages/editor/src/lib/editor/Editor.ts:8284`). Nothing about the API forces user-drawn input.
- **Hide chrome**: `<Tldraw hideUi />` removes the toolbar/menus; `ui-components-hidden` and `custom-ui` examples confirm you can strip it to bare canvas.
- **Readonly mode**: `editor.updateInstanceState({ isReadonly: true })` gates editing (`Editor.ts:10278`).
- **Camera control**: `cameraOptions` + `zoomToBounds` give you pan/zoom-only behavior.
- **Mature rendering**: DOM-based, handles 10k+ shapes examples (`use-cases/many-shapes`), embeddable HTML/SVG inside shapes.

## What fights us

- **License is the killer**. `LICENSE.md` explicitly forbids Production Environments without a commercial agreement. `@tldraw/editor` ships `LicenseProvider`, `Watermark.tsx`, and a `useLicenseManagerState` hook that watermark unlicensed deployments. The license text: *"Not to disable, change, or interfere with the Software's License Key enforcement"* and *"Not to use the Software in Production Environments"* (paid seat required). Manicure is a shipped developer tool, so this applies.
- **Bundle weight is wildly disproportionate**. `tldraw@4.5.9` unpacked = **11.94 MB**; `@tldraw/editor` alone = **7.43 MB**. Hard dependencies include the entire Tiptap/ProseMirror stack (`@tiptap/core`, `@tiptap/pm`, `@tiptap/react`, `@tiptap/starter-kit`, plus four extensions), `radix-ui`, `idb`, `lz-string`, `hotkeys-js`. For a diagram with zero rich-text or persistence needs, this is absurd.
- **No auto-layout in-box**. You would pair with dagre/elk. Doable (nothing in the API prevents you pre-computing `x,y` before `createShapes`), but tldraw doesn't help — and its coordinate system, arrow-binding primitives, and handle system are all designed around user-drawn graphs, not DAG layouts.
- **Edges are "arrow shapes" with bindings**, not first-class graph edges. You can fake it, but every other React-native diagram lib gives you edges for free.
- **Peer deps on React 18/19 only**, plus its own CSS. Not a blocker but another surface.

## Alternatives comparison

| Lib | License | Fit for read-only topology | Bundle | Notes |
|---|---|---|---|---|
| **React Flow (`@xyflow/react`)** | MIT | Excellent — literally built for node/edge diagrams with React components per node | ~100-200KB gz | First-class `nodeTypes`, `edgeTypes`, `panOnScroll`, `nodesDraggable={false}`, `elementsSelectable={false}`, `zoomOnDoubleClick={false}`. Pairs cleanly with `dagre` / `elkjs`. |
| **Cytoscape.js (+ react-cytoscapejs)** | MIT | Strong — has `dagre`, `elk`, `cose-bilkent` layouts built in | ~300KB gz | Canvas not SVG/DOM; custom node rendering requires popper overlays for React components. Heavier integration. |
| **D3 + SVG (custom)** | BSD-3 / ISC | Full control, most work | tiny | Right answer if the diagram is one-off and you want zero abstraction tax. Highest code burden. |
| **Excalidraw** | MIT (library) | Poor fit | heavy | Also whiteboard-shaped; same "forcing a drawing tool into a diagram" problem as tldraw, but at least MIT. |
| **tldraw** | Proprietary (paid prod license) | Works but over-scoped | ~12MB unpacked | Watermark + license-key enforcement. Disqualified by license for manicure. |

## Recommendation

**Build the Trace/Topology view on React Flow.**

- MIT license, zero legal ambiguity.
- `nodesDraggable={false} nodesConnectable={false} elementsSelectable={true} panOnDrag zoomOnScroll` gives the exact "pan/zoom/click-to-focus but no editing" posture you described.
- Custom node components are plain React — drop in `<ExchangeNode exchange={...} />`, `<OverlayBadge rule={...} />` directly.
- Pair with `dagre` (or `elkjs` if you need layered DAG with port routing) for layout, compute positions once per session load, pass `{ nodes, edges }` in.
- Bundle cost matches the feature's actual complexity.

If you still want a quick tldraw spike for aesthetic reasons, keep it to `localhost`-only manicure dev builds (permitted under the Development Environment clause) and do **not** ship it in a released binary — but this path is a dead end because you'd then have to rewrite before release anyway.

## Sources consulted

- `/tmp/gh-research/tldraw-tldraw/LICENSE.md` (the decisive document)
- `packages/tldraw/package.json`, `packages/editor/package.json`
- `packages/tldraw/src/lib/Tldraw.tsx` — `hideUi` prop
- `packages/tldraw/src/lib/ui/hooks/useReadonly.ts`
- `packages/editor/src/lib/editor/Editor.ts` — `createShape`, `createShapes`, `isReadonly`
- `packages/editor/src/lib/license/{LicenseProvider.tsx,Watermark.tsx,useLicenseManagerState.ts}`
- `apps/examples/src/examples/ui/{hide-ui,custom-ui,ui-components-hidden}`
- `apps/examples/src/examples/use-cases/{many-shapes,timeline-scrubber,slides}`
- npm registry metadata for `tldraw@4.5.9` and `@tldraw/editor@4.5.9` (unpacked sizes, deps)

## Open questions

- Exact minified+gzipped bundle size for a `hideUi` + single custom shape build would need a Vite `build --report` to pin down. The unpacked sizes above are upper bounds; tree-shaking helps, but the Tiptap peer dependencies are transitively reachable from the main `Tldraw` component and unlikely to drop out.
- React Flow's Pro edition has nicer layered layout helpers; confirm the MIT `@xyflow/react` core is sufficient for manicure's scale (likely yes at session sizes < 1000 exchanges).
