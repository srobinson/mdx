---
title: "b_style React Architecture Audit"
category: projects
tags: [b_style, gradient-editor, react, architecture]
---

# b_style React Architecture Audit

## 1. Current State Assessment

### Codebase Topology

| File | LOC | Role |
|---|---|---|
| `routes/(public)/test-radius.tsx` | 223 | **God component** — all state, all wiring |
| `routes/(public)/test-radius.utils.ts` | 117 | Color math (bezier eval, color stop generation) |
| `components/easing.tsx` | 309 | Cubic bezier curve editor (SVG drag) |
| `components/radius.tsx` | 239 | Rotary dial control (angle picker) |
| `components/pad.tsx` | 217 | 2D position picker (XY drag) |
| `components/command-center.tsx` | 169 | Tab bar + gradient type selector + slider |
| `components/canvas-preview.tsx` | 126 | Full-viewport gradient renderer (motion) |
| `components/pallette.tsx` | 118 | 3-slot color picker (start/hint/end) |
| `components/color-space.tsx` | 106 | Color space + hue interpolation toggles |
| `components/radial-controls.tsx` | 104 | Radial shape/extent/repeating toggles |
| `components/controls.tsx` | 46 | Smooth transitions toggle |
| `components/ui/icons.tsx` | 424 | Inline SVG icon registry |
| `components/ui/slider.tsx` | 54 | Radix slider wrapper |

**Total app-specific code:** ~2,250 LOC across 13 source files.

### Tech Stack

- **Framework:** Vite + React 18 + TanStack Router
- **Styling:** Tailwind CSS 4 + raw CSS classes (BEM-ish hashes like `cxwqm2n`, `w1wikcwy`)
- **Animation:** Motion (framer-motion successor) for preview transitions
- **Color math:** colorjs.io for perceptual color interpolation
- **Color picker:** react-best-gradient-color-picker (third-party)
- **UI primitives:** Radix Slider
- **Monorepo:** Part of `@b/values` workspace, depends on `@b/values` package

### Architecture Pattern

**Single-page god component.** `SimpleRadius` in `test-radius.tsx` owns 20+ `useState` calls and passes everything down via props. Every component is a controlled leaf with `onXChange` callbacks that call individual setters.

```
SimpleRadius (test-radius.tsx)
├── CanvasPreview        — reads 12 props
├── CommandCenter        — reads/writes 7 state values
│   ├── ColorControl     — color space, hue interpolation
│   └── Slider           — precision/numStops
├── AnimatePresence
│   ├── Easing           — if tab === "ease"
│   ├── Radius           — if tab === "rotate"
│   ├── Pad              — if tab === "move"
│   │   └── RadialControls — nested in radial move mode
│   ├── Pallette         — if tab === "pallette"
│   └── Controls         — if tab === "options"
```

## 2. What Works Well

### Gems worth preserving

1. **Interactive controls are genuinely good.** The `Easing`, `Radius`, and `Pad` components are well-built drag interaction primitives. They handle mouse + touch, use proper coordinate transforms, support controlled/uncontrolled patterns, and feel responsive. These are reusable widgets.

2. **CanvasPreview's motion value approach.** Using `useMotionValue` + `useMotionTemplate` for smooth gradient transitions avoids re-renders entirely. The angle wraparound calculation (shortest path through 360°) is a thoughtful detail.

3. **Color stop generation.** The `generateColorStops` utility separates the color math cleanly. Perceptual interpolation via colorjs.io with easing curve application produces high quality gradients.

4. **SVG-based interaction surfaces.** Both `Easing` and `Radius` render their interactive areas as SVG, making coordinate math straightforward and resolution-independent.

5. **Tab-based tool switching with AnimatePresence.** The UX concept of swapping tools with enter/exit animations is solid.

### Patterns that scale

- Controlled component interfaces (`value` + `onChange`) on all interactive widgets
- Touch event handling alongside mouse events
- Coordinate system separation (value space vs. pixel space)

## 3. What Needs Rework

### Critical issues

**3.1 God component anti-pattern**

`SimpleRadius` manages 20 independent `useState` calls. There is no state grouping, no reducer, no store. Adding a second gradient would require duplicating every piece of state. Adding undo/redo is impossible without a centralized state model.

**3.2 Prop drilling depth**

`CommandCenter` receives 10 props. `CanvasPreview` receives 12. Every new feature adds props to both. The component interfaces are growing linearly with feature count.

**3.3 Inline styles everywhere**

Most components use inline `style={{}}` objects. `CommandCenter` alone has ~40 lines of inline CSS including commented-out alternatives. This is prototype-velocity code that creates maintenance burden and prevents theming.

**3.4 CSS class naming is opaque**

Classes like `cxwqm2n`, `w1wikcwy`, `nqt0sva` appear to be remnants of a CSS-in-JS tool's output that got committed as plain CSS. They carry no semantic meaning.

**3.5 Document-level event listeners without cleanup guards**

`Pad` registers mouse/touch listeners on `document` unconditionally in every render cycle (the effect deps include `isDragging` and axis ranges, but the listeners fire even when not dragging). `Easing` does this conditionally on `dragging` state, which is better, but `Radius` also registers unconditionally.

**3.6 Stale closure risk in drag handlers**

`Pad.handleMouseMove` captures `isDragging`, `minX`, `maxX`, etc. in the effect closure. The effect re-subscribes when deps change, but there is a frame where the old handler could fire with stale values.

**3.7 No error boundaries**

Zero error boundaries. A bad color string from the picker or a NaN in the bezier evaluation would crash the entire app.

**3.8 Leftover scaffolding**

- `lib/profile.ts` contains "KopaKopa" branding from another project
- `routes/(public)/index.tsx` references deleted routes (timeline, journey-map, test-growth)
- Large blocks of commented-out code in `Easing`, `CanvasPreview`, `Radius`, `CommandCenter`
- `console.log(hueInterpolation)` left in `ColorControl`

**3.9 Viewport-coupled sizing**

`Pad` calls `document.documentElement.clientHeight` directly in render to compute `SIZE`. This creates layout dependency on window dimensions without any resize handling, and breaks SSR.

**3.10 Icon system is a static JSX object**

`Icon` is a Record of inline SVG JSX elements (424 LOC). They are instantiated at module load time, not on demand. Some use `stroke-width` (HTML attribute) instead of `strokeWidth` (React prop), mixing conventions.

## 4. Proposed Architecture for Rebuild

### 4.1 State Architecture: Zustand Store with Immer

Replace the 20 `useState` calls with a single Zustand store. Zustand provides the right tradeoffs for this app: minimal boilerplate, middleware for undo/redo, subscriptions for selective re-renders.

```typescript
// store/gradient-store.ts
interface GradientLayer {
  id: string;
  type: 'linear' | 'radial' | 'conic';
  angle: number;
  colors: ColorStop[];
  easing: EasingCurve;
  position: { x: number; y: number };
  radial: { shape: 'circle' | 'ellipse'; extent: RadialExtent };
  repeating: boolean;
}

interface EditorState {
  // Document model
  layers: GradientLayer[];
  activeLayerId: string;

  // UI state (not in undo history)
  activeTool: ToolId;
  colorSpace: ColorSpace;
  hueInterpolation: HueInterpolation;
  smoothTransitions: boolean;
  numStops: number;

  // Derived
  activeLayer: () => GradientLayer;
  cssOutput: () => string;
}
```

Use Zustand's `temporal` middleware (from `zundo`) for undo/redo with zero custom code:

```typescript
import { temporal } from 'zundo';

const useEditorStore = create<EditorState>()(
  temporal(
    immer((set) => ({
      // actions mutate via immer
      setAngle: (angle: number) => set(s => { s.layers[s.activeLayerIndex].angle = angle }),
      addLayer: () => set(s => { s.layers.push(createDefaultLayer()) }),
    })),
    { limit: 100 }  // 100-step undo history
  )
);
```

### 4.2 Component Architecture

```
<EditorShell>                          // Layout frame, hotkey provider
├── <GradientCanvas />                 // Full-viewport preview, reads store directly
├── <Toolbar position="left">          // Vertical tool palette
│   └── <ToolButton />×N              // Each tool registers via plugin system
├── <LayerPanel position="right">      // Layer list, add/remove/reorder
│   └── <LayerItem />×N
├── <ToolSurface>                      // AnimatePresence wrapper
│   └── <ActiveTool />                 // Rendered from tool registry
└── <CommandBar position="top">        // Gradient type, precision, color space
    └── <PropertyControls />
```

Key principle: **components subscribe to store slices, never receive full state as props.**

```typescript
// Instead of <CanvasPreview angle={angle} radialX={radialX} ... 12 more props>
function GradientCanvas() {
  const layer = useEditorStore(s => s.activeLayer());
  const smoothTransitions = useEditorStore(s => s.smoothTransitions);
  // render with layer data directly
}
```

### 4.3 Tool Plugin System

Tools should be self-registering units. Each tool declares its own UI, what state it reads/writes, and when it is available:

```typescript
// tools/easing-tool.ts
export const easingTool: ToolDefinition = {
  id: 'easing',
  label: 'Easing',
  icon: 'ease',
  available: (state) => true,  // always available
  component: lazy(() => import('./EasingEditor')),
  panel: 'center',  // rendered in main tool surface
};

// tools/rotation-tool.ts
export const rotationTool: ToolDefinition = {
  id: 'rotation',
  label: 'Rotate',
  icon: 'rotate',
  available: (state) => state.activeLayer().type !== 'radial',
  component: lazy(() => import('./RotationEditor')),
  panel: 'center',
};
```

A `ToolRegistry` collects all tools at startup. The toolbar renders from the registry. Tool availability is reactive (disabling "rotate" for radial gradients happens automatically).

### 4.4 Drag Interaction Abstraction

The three drag-capable components (`Easing`, `Radius`, `Pad`) share 80% of their pointer handling logic. Extract a `useDrag` hook:

```typescript
function useDrag<T>(options: {
  containerRef: RefObject<HTMLElement>;
  onMove: (position: { clientX: number; clientY: number }) => T;
  onStart?: () => void;
  onEnd?: () => void;
}) {
  // Registers document-level listeners only while dragging
  // Handles mouse + touch + pointer events
  // Returns { isDragging, handlers: { onPointerDown } }
}
```

This eliminates the duplicated `document.addEventListener` / `removeEventListener` boilerplate across all three components and fixes the unconditional-listener bugs.

### 4.5 Layer Model

For multiple gradients and HTML layers:

```typescript
interface Document {
  layers: HTMLLayer[];       // Each HTML layer can have multiple gradients
}

interface HTMLLayer {
  id: string;
  name: string;
  gradients: GradientLayer[];  // Stacked gradients on one element
  filters: CSSFilter[];        // blur, contrast, etc.
  blendMode: string;
  opacity: number;
}
```

CSS output becomes a composition of all layers:

```css
.layer-0 { background-image: linear-gradient(...), radial-gradient(...); }
.layer-1 { background-image: conic-gradient(...); mix-blend-mode: overlay; }
```

### 4.6 Serialization

The store's document model is the serialization format. Use a versioned JSON schema:

```typescript
interface SavedDocument {
  version: 1;
  layers: HTMLLayer[];
  settings: { colorSpace: string; numStops: number; };
}
```

Export targets: raw CSS, Tailwind classes, CSS custom properties, SVG, PNG (via html2canvas or similar).

### 4.7 Panel System

For draggable/dockable panels, use a lightweight approach rather than a full windowing library:

```typescript
interface PanelDefinition {
  id: string;
  title: string;
  defaultPosition: 'left' | 'right' | 'bottom' | 'floating';
  component: React.ComponentType;
  minWidth?: number;
}
```

Start with fixed positions + a "detach to floating" capability. Full drag-and-dock (like VS Code) is scope creep for v1. A library like `react-resizable-panels` from BuilderIO handles the split-pane layout without custom drag math.

## 5. Tech Stack Recommendations

### Keep

| What | Why |
|---|---|
| **Vite** | Fast, proven, good plugin ecosystem |
| **TanStack Router** | Already wired, file-based routing works |
| **Motion** | CanvasPreview's motion template pattern is excellent |
| **colorjs.io** | Best-in-class perceptual color library |
| **Radix primitives** | Accessible, unstyled, composable |

### Add

| What | Why |
|---|---|
| **Zustand + Immer + Zundo** | Centralized state, undo/redo, selective subscriptions, ~3KB |
| **Tailwind CSS 4** | Already present but underused; replace all inline styles |
| **Lucide React** | Replace the hand-rolled SVG icon object with tree-shakeable icons |
| **react-resizable-panels** | Panel layout without custom drag math |
| **Vitest** | Unit tests for color math, store logic, hook behavior |

### Replace

| What | With | Why |
|---|---|---|
| **react-best-gradient-color-picker** | Custom color picker or `@uiw/react-color` | Current picker is visually heavy, hides too many features behind flags, and the `handleChange(next: any)` normalization in Pallette suggests unreliable output types |

### Remove

| What | Why |
|---|---|
| `lib/profile.ts` | Unrelated KopaKopa branding |
| `routes/(public)/index.tsx` experiment grid | Dead links to deleted routes |
| `glass.css` | Unused glassmorphism experiment |

## 6. Migration Path

### Phase 1: State extraction (foundation)

1. Define the `GradientLayer` and `EditorState` types
2. Create the Zustand store with all current state
3. Refactor `SimpleRadius` to read from store instead of 20 `useState` calls
4. Wire undo/redo via zundo

### Phase 2: Component restructuring

1. Extract `useDrag` hook, refactor `Easing`, `Radius`, `Pad`
2. Replace inline styles with Tailwind classes
3. Create `EditorShell` layout component
4. Move tool rendering to plugin registry pattern
5. Add error boundaries around each tool and the canvas

### Phase 3: Multi-layer support

1. Implement `HTMLLayer` model
2. Build layer panel (add/remove/reorder/visibility)
3. Update `GradientCanvas` to composite multiple layers
4. CSS output generation for multi-layer stacks

### Phase 4: Panel system + export

1. Implement panel positions with react-resizable-panels
2. Add floating panel detach capability
3. Build export panel (CSS, Tailwind, SVG, PNG)
4. Add serialization (save/load documents)

## 7. Summary

The prototype demonstrates strong UX instincts. The interactive controls (bezier editor, rotary dial, XY pad) are production-quality interaction primitives that need only minor cleanup. The motion-based gradient preview is a genuinely clever use of motion values for smooth, re-render-free transitions.

The structural problems are typical of rapid prototyping: all state in one component, prop drilling, inline styles, no error handling. These are straightforward to fix.

The rebuild should focus on three pillars: a Zustand store as the single source of truth (enabling undo/redo and multi-layer support), a tool plugin registry (enabling extensibility without growing the god component), and a `useDrag` abstraction (eliminating the duplicated pointer handling code). Everything else is incremental improvement on a solid foundation.
