---
title: "b_style Unified Rebuild Plan"
category: projects
tags: [b_style, gradient-editor, rebuild, architecture, product]
---

# b_style: Unified Rebuild Plan

Synthesized from three independent audits: UI/UX, React Architecture, and Interaction Engine. All three agents converged on the same core problems and similar solutions, which gives high confidence in this plan.

## What This Is

A gradient editor with genuinely novel UX. The prototype proves five interaction principles that separate it from every existing tool:

1. **Canvas is the product.** The gradient fills the viewport. Controls float over it. Most editors confine the preview to a thumbnail.
2. **Shape mirrors parameter.** Angle is a circle. Position is a plane. Easing is a curve. The control geometry matches the parameter geometry.
3. **Immediate feedback.** Every drag updates the full canvas in real time. No preview/apply split.
4. **Progressive disclosure through spatial zones.** Tools appear contextually. Information density increases toward the center of attention.
5. **Tools, not forms.** These are instruments you hold and manipulate, not fields you type into.

## What's Worth Preserving

| Feature | Why It Matters |
|---|---|
| `useMotionValue` + `useMotionTemplate` gradient renderer | Zero React re-renders during animation. GPU-composited CSS gradients. Angle wraparound logic handles 359-to-1 correctly. |
| Bezier curve editor | Click-to-move-nearest-handle, extended range (overshoot curves), dot grid spatial reference. Production-quality interaction primitive. |
| Circular rotation dial | `atan2`-based angle from pointer position. Snap support. Touch support. Correct coordinate transform. |
| 2D crosshair position control | Snap, clamp, touch, percentage-based output. |
| colorjs.io perceptual interpolation | Configurable color spaces (HSL, LUV, LCHuv), hue interpolation modes, bezier-eased interpolation. CSS native gradients cannot match this output quality. |
| Radial extent icons | Well-designed SVG icons that communicate spatial concepts visually. |

## What Must Change

### Consensus issues (flagged by all three agents)

1. **God component.** `SimpleRadius` owns 20 `useState` calls. Blocks undo/redo, multi-layer, presets, sharing.
2. **Duplicated drag system.** Three components implement the same mousedown/mousemove/mouseup pattern with different lifecycle bugs. `Easing` uses `useState` for drag state (re-renders every frame). `Radius` uses `useRef` (correct). Listener attachment varies: conditional vs. always-on.
3. **Prop drilling.** `CanvasPreview` takes 12 props. `CommandCenter` takes 10. Growing linearly with features.
4. **Inline styles everywhere.** Three competing styling systems: Tailwind (underused), inline React styles (dominant), obfuscated CSS class names (legacy CSS-in-JS output).
5. **Hardcoded layout.** Magic pixel values (`top: 286px`, `left: -70px`, `calc(50% - 330px)`) break on different viewports.
6. **No accessibility.** Partial ARIA on Radius only. No keyboard handlers. No reduced-motion support.
7. **Half-implemented hint color.** UI slot exists, interpolation is commented out. Erodes trust.

### Additional issues

- `mix-blend-mode: difference` creates illegible text on mid-tone gradients
- Document-level listeners without cleanup guards create stale closure risks
- Viewport-coupled sizing (reading `clientHeight` at render time) breaks on resize
- 424-LOC icon file instantiated at module load
- KopaKopa branding, dead routes, console.log statements

---

## Architecture

### State: Zustand + Immer + Zundo

```typescript
interface GradientLayer {
  id: string;
  type: 'linear' | 'radial' | 'conic';
  angle: number;
  position: { x: number; y: number };
  colors: ColorStop[];
  easing: [number, number, number, number]; // cubic-bezier points
  colorSpace: ColorSpace;
  hueInterpolation: HueInterpolation;
  radial: { shape: 'circle' | 'ellipse'; extent: RadialExtent };
  repeating: boolean;
  precision: number;
  visible: boolean;
  locked: boolean;
}

interface HTMLLayer {
  id: string;
  name: string;
  gradients: GradientLayer[];
  filters: CSSFilter[];
  blendMode: string;
  opacity: number;
}

interface EditorState {
  // Document (undo-able)
  layers: HTMLLayer[];
  activeLayerId: string;
  activeGradientId: string;

  // UI (not in undo history)
  activeTool: ToolId;
  smoothTransitions: boolean;
}
```

Zustand with `temporal` middleware (zundo) gives undo/redo with zero custom code. Immer enables direct mutation syntax. Components subscribe to store slices, never receive full state as props.

### Interaction: useSpatialDrag Hook

Extract the shared drag logic from Easing/Radius/Pad into one hook:

```typescript
useSpatialDrag({
  containerRef,
  coordinateSpace: 'normalized' | 'angle' | 'percentage' | 'custom',
  onDrag: (point, delta) => void,
  onDragStart?: (point) => void,
  onDragEnd?: () => void,
  snap?: { x?: number, y?: number },
  clamp?: { min, max },
  touch?: boolean,
})
```

Implementation requirements:
- `useRef` for all transient state (no re-renders during drag)
- `PointerEvent` + `setPointerCapture` instead of document-level listeners
- Cache `getBoundingClientRect()` at drag start
- Unified mouse + touch handling

### Rendering: SVG Overlays + CSS Canvas

Stay with the current approach. SVG is correct for this element count (under 200 nodes per control). Improvements:

- **Shared `<SpatialCanvas>` wrapper** with resize observer and coordinate system
- **Layered SVG** with event delegation instead of per-component document listeners
- **Focus model** for multi-layer: one interactive overlay at a time, others ghosted
- **Memoize static elements** (dot grid, guide rings)

### Tools: Plugin Registry

```typescript
interface ToolDefinition {
  id: string;
  label: string;
  icon: string;
  available: (state: EditorState) => boolean;
  component: React.LazyExoticComponent<React.ComponentType>;
  panel: 'center' | 'side' | 'bottom';
}
```

Each tool self-declares its component, icon, and availability predicate. The toolbar renders from the registry. Tool availability is reactive (e.g., "rotate" disables for radial gradients automatically).

### Panels: Declarative Layout

```typescript
interface FloatingPanel {
  id: string;
  position: 'top' | 'center' | 'left' | 'right' | 'bottom';
  anchor: 'viewport' | 'canvas';
  draggable: boolean;
  collapsible: boolean;
}
```

Replace magic pixel positioning with declarative layout. Start with fixed positions + "detach to floating" capability. Use `react-resizable-panels` for split-pane layout. Full drag-and-dock is scope creep for v1.

### Design Tokens

```css
--surface-glass-bg: hsl(0 0% 0% / 0.15);
--surface-glass-blur: 16px;
--surface-glass-border: hsl(0 0% 100% / 0.12);
--control-handle-size: 24px;
--control-guide-color: hsl(0 0% 100% / 0.3);
--transition-fast: 150ms;
--transition-medium: 250ms;
--font-mono: 'SF Mono', 'Fira Code', monospace;
--label-size: 11px;
```

Replace `mix-blend-mode: difference` with proper frosted glass panels that guarantee WCAG AA contrast regardless of background gradient.

---

## Component Tree

```
<EditorShell>
  <GradientCanvas />                    // full viewport, composites all layers
  <ToolSurface>                         // floating layer above canvas
    <CommandBar position="top" />       // gradient type, tool tabs, precision
    <ActiveTool position="center" />    // rendered from tool registry via AnimatePresence
    <PropertyBar position="side" />     // context-dependent properties
    <ColorDock position="bottom" />     // color management
  </ToolSurface>
  <LayerPanel position="right" />       // gradient list, HTML layers
</EditorShell>
```

---

## Tech Stack

### Keep
| What | Why |
|---|---|
| Vite | Fast, proven |
| TanStack Router | Already wired, file-based routing |
| Motion (framer-motion) | CanvasPreview's motion template pattern is the right architecture |
| colorjs.io | Best perceptual color library available |
| Radix primitives | Accessible, unstyled, composable |

### Add
| What | Why |
|---|---|
| Zustand + Immer + Zundo | Centralized state, undo/redo, selective subscriptions (~3KB) |
| Tailwind CSS 4 | Already present but underused; replace all inline styles |
| Lucide React | Replace 424-LOC hand-rolled icon file |
| react-resizable-panels | Panel layout without custom drag math |
| Vitest | Unit tests for color math, store logic, hook behavior |

### Replace
| What | With | Why |
|---|---|---|
| react-best-gradient-color-picker | Purpose-built or `@uiw/react-color` | Current picker hides 6/7 features behind flags, carries dead weight |

### Remove
| What | Why |
|---|---|
| KopaKopa branding (`lib/profile.ts`) | Unrelated |
| Dead routes (timeline, journey-map, test-growth) | Already deleted from git |
| `glass.css` | Unused experiment |
| Obfuscated CSS classes | Replace with semantic Tailwind |

---

## Phased Migration

### Phase 1: Foundation (state + drag)
1. Define `GradientLayer`, `HTMLLayer`, `EditorState` types
2. Create Zustand store with all current state
3. Refactor `SimpleRadius` to read from store
4. Extract `useSpatialDrag` hook
5. Refactor Easing, Radius, Pad to use the hook
6. Wire undo/redo via zundo
7. Add error boundaries

### Phase 2: Component restructuring
1. Create `EditorShell` layout component
2. Replace inline styles with Tailwind + design tokens
3. Build tool plugin registry
4. Replace `mix-blend-mode: difference` with glass panels
5. Add keyboard support to spatial controls
6. Complete or remove hint color feature
7. Replace icon system with Lucide

### Phase 3: Multi-layer
1. Implement `HTMLLayer` model in store
2. Build layer panel (add/remove/reorder/visibility/lock)
3. Update `GradientCanvas` to composite multiple layers
4. Implement focus model for overlay management
5. CSS output generation for multi-layer stacks

### Phase 4: Panels + export
1. Implement panel layout with react-resizable-panels
2. Add floating panel detach capability
3. Build export panel (CSS, Tailwind classes, CSS custom properties, SVG, PNG)
4. Add serialization (save/load documents)
5. URL serialization for sharing

### Phase 5: Polish
1. Easing presets with animated transitions
2. Animation preview for timing functions
3. Snap-to-grid with modifier key override
4. Purpose-built color wheel matching the spatial interaction philosophy
5. `prefers-reduced-motion` support
6. Responsive layout for different screen sizes

---

## Competitive Position

This tool's differentiator is the spatial interaction model. Every existing gradient editor (CSS Gradient, Gradient Hunt, WebGradients, Grabient) uses form-based UIs: dropdowns for type, number inputs for angle, sliders for position. b_style inverts this hierarchy. The gradient IS the interface. Parameters are manipulated through controls whose geometry matches the parameter space.

The perceptual color interpolation via colorjs.io with bezier-eased sampling is a technical advantage that produces visually superior gradients. At 10+ stops, the output is indistinguishable from a continuous gradient while being pure CSS.

Combined with multi-layer composition, HTML layer support, and export capabilities, this positions b_style as a professional gradient design tool rather than a utility.

---

## Source Audits

- [UI/UX Audit](b_style-ui-audit.md) - interaction principles, design system, priority actions
- [React Architecture](b_style-react-architecture.md) - component structure, state, migration path
- [Interaction Engine](b_style-interaction-engine.md) - rendering, drag system, bezier editor, performance
