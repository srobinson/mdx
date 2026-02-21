---
title: "b_style UI/UX Audit"
category: projects
tags: [b_style, gradient-editor, ui-audit, design-system]
---

# b_style Gradient Editor: UI/UX Audit

## 1. Current Architecture Summary

The app is a full-viewport gradient editor built with React, Framer Motion, and TanStack Router. The canvas (gradient preview) fills the entire screen. All controls float above it. The interaction model is **spatial and direct**: you rotate a circular dial to set angle, drag a crosshair pad to set position, drag bezier handles to shape easing curves, and pick colors through a slot-based palette.

### Component Inventory

| Component | Role | Interaction Model |
|---|---|---|
| `CanvasPreview` | Full-viewport gradient render | Passive display, animated via motion values |
| `CommandCenter` | Top toolbar: gradient type selector, tab switcher, precision slider | Click-to-select, slider drag |
| `Radius` | Circular drag dial for angle/rotation | Radial drag with snap, touch support |
| `Pad` | 2D crosshair for X/Y positioning | Click + drag on 2D plane, snapping |
| `Easing` | Cubic bezier curve editor | Drag control points on SVG canvas |
| `Pallette` | Color picker with Start/Hint/End slots | Slot selection + embedded color picker |
| `RadialControls` | Radial-specific: shape, extent, repeating | Icon button row |
| `Controls` | Options panel (smooth transitions toggle) | Simple toggle |
| `Slider` | Precision stop count slider | Radix-based track+thumb |

### Tech Stack
- **React** with hooks (all state in `SimpleRadius` root component)
- **Framer Motion** (`motion/react`) for animated transitions and motion values
- **colorjs.io** for perceptual color interpolation
- **react-best-gradient-color-picker** for the embedded color picker
- **Radix UI** slider primitive
- **Tailwind CSS** (imported but minimally used; mostly inline styles)
- **Custom CSS** with obfuscated class names (`cxwqm2n`, `w1wikcwy`, `nqt0sva`, etc.)

---

## 2. What's Working

### 2.1 The Canvas-First Model is Genuinely Novel

The full-viewport gradient preview is the centerpiece, and everything else floats over it. This is the right call. Most gradient editors (CSS Gradient, Gradient Hunt, etc.) confine the preview to a small rectangle inside a form-heavy UI. Here, the gradient IS the workspace. The user sees their output at real scale, always. This is the single most important design decision to preserve.

### 2.2 Spatial Direct Manipulation Controls

The `Radius` (circular dial), `Pad` (2D crosshair), and `Easing` (bezier handle) components share a quality that separates this from form-based editors: you manipulate the parameter through a control whose shape mirrors the parameter's geometry. Angle is a circle. Position is a plane. Easing is a curve. This is spatial correspondence, and it creates an intuitive mapping that no slider or number input can replicate.

### 2.3 Smooth Animated Transitions

The motion value architecture in `CanvasPreview` handles angle wrap-around correctly (shortest path calculation), and the `AnimatePresence` tab transitions with `backInOut` easing give the tool a polished, living feel. The 0.3s duration for property changes and 0.25s for tab switches feel appropriately snappy.

### 2.4 Perceptual Color Interpolation

Using `colorjs.io` with configurable color spaces (HSL, LUV, LCHuv) and hue interpolation modes (shorter/longer) is a genuine differentiator. Combined with the cubic bezier easing applied to the interpolation, this produces gradients that are perceptually smooth in ways CSS native gradients cannot achieve.

### 2.5 Custom Icon System

The SVG icons for radial extent variants (`closest-side`, `farthest-corner`, etc.) are well-designed. They communicate spatial concepts visually: a center dot, an edge/corner indicator, and a measurement line. The active/inactive state variants with filled vs. outlined treatment provide clear selection feedback.

---

## 3. What Needs Rethinking

### 3.1 State Architecture is Flat and Monolithic

`SimpleRadius` holds 18 `useState` calls. Every parameter lives at the top level. This creates two problems:

1. **Prop drilling**: `CommandCenter` alone receives 10 props. `CanvasPreview` receives 13. Each new feature multiplies the wiring.
2. **No serialization path**: There's no gradient model object. You can't save, load, or share a gradient because the state is scattered across independent variables.

**Recommendation**: Define a `GradientState` type that captures the full configuration. Use `useReducer` or a lightweight store (Zustand, Jotai) to manage it as a single entity. This unlocks undo/redo, presets, gradient lists, and shareable URLs.

### 3.2 Inline Styles Everywhere

Nearly every component uses inline `style={{}}` objects. This creates several issues:

- No hover/focus/active states possible (see: buttons without hover feedback)
- No media queries for responsive behavior
- Duplicated style patterns across components (the glassmorphic panel style appears in both `CommandCenter` and `ColorControl` verbatim)
- Mix of CSS custom properties, Tailwind classes, and inline styles creates three competing styling systems

**Recommendation**: Consolidate on a single system. Given the visual complexity and need for state-dependent theming, CSS Modules or Tailwind with a component-level abstraction layer would serve better than inline styles. The glassmorphic panel style should be a reusable component, not a copied style block.

### 3.3 Layout is Hardcoded and Fragile

- `RadialControls` has `position: absolute; top: "286px"` - a magic number tied to the `Pad` component's height
- `ColorControl` has `position: absolute; left: "-70px"; top: "-30px"` - positioned relative to its parent with magic offsets
- The `CommandCenter` wrapper uses `top: "calc(50% - 330px)"` - centered with a hardcoded offset
- `Pad` reads `document.documentElement.clientHeight` directly in render and uses 90% of viewport height

These positions will break on different screen sizes, and they prevent the layout from adapting to panels being moved, resized, or composed differently.

**Recommendation**: Replace magic numbers with a layout system. The floating panel pattern should use CSS anchor positioning or a constraint-based layout where panels declare their preferred position relative to landmarks (canvas center, viewport edges) rather than absolute pixel values.

### 3.4 No Keyboard or Accessibility Support

- The `Radius` component has proper ARIA attributes (`role="slider"`, `aria-valuemin`, `aria-valuenow`) but no keyboard handler
- `Easing` has no ARIA attributes at all
- `Pad` has no ARIA attributes
- Tab navigation doesn't work through the control panels
- No screen reader announcements for value changes
- No reduced-motion support (animations are always active)

**Recommendation**: Each spatial control needs keyboard support: arrow keys for incremental adjustment, shift+arrow for larger steps. Add `prefers-reduced-motion` media query to disable or reduce animation durations. Add live regions for value announcements.

### 3.5 Mix-Blend-Mode: Difference Creates Readability Problems

Both `CommandCenter` and `ColorControl` use `mixBlendMode: "difference"`. This makes text and icons adapt to the underlying gradient, which is clever for visibility, but produces unpredictable color inversion that can render text illegible when the gradient passes through mid-tones. A gradient with 50% gray underneath will produce near-zero contrast text.

**Recommendation**: Replace `mix-blend-mode: difference` with a frosted glass panel that has sufficient opacity to guarantee text contrast regardless of the background. The `.glassmorphism` class already defined in `styles.css` is a better foundation. Use `backdrop-filter: blur() saturate()` with a semi-opaque background that maintains WCAG AA contrast (4.5:1 minimum).

### 3.6 Tab Disabling Logic is Implicit

`CommandCenter` disables the "rotate" tab when gradient type is "radial" and the "move" tab when type is "linear". This is correct behavior, but the disabled state is communicated only through reduced opacity (0.5) and cursor change. The user receives no explanation of WHY the tab is disabled.

**Recommendation**: Add a tooltip explaining the constraint ("Radial gradients don't have a rotation angle") and visually communicate the relationship between gradient type and available tools. Consider showing all tools always, with contextually dimmed sections that activate when relevant.

### 3.7 Color Picker Integration is Heavyweight

`react-best-gradient-color-picker` is configured with nearly every feature hidden (`hidePresets`, `hideInputs`, `hideOpacity`, `hideAdvancedSliders`, `hideColorTypeBtns`, `hideGradientControls`). When you hide 6 out of 7 features, the dependency is carrying dead weight. The picker is also wrapped in a hardcoded dark background (`rgb(32, 32, 32)`) that doesn't integrate with the glassmorphic panel design.

**Recommendation**: For the rebuild, consider a purpose-built color picker that matches the spatial interaction philosophy. An HSL wheel (which the current picker provides) is the right shape, but it should be a first-class component with the same direct manipulation feel as the other spatial controls.

### 3.8 The Hint Color is Unused

`Pallette` accepts `hintColor` and renders a "Hint" slot, but `test-radius.utils.ts` shows the hint color integration is commented out. The three-stop interpolation (start-hint-end) is partially implemented but disabled. This creates a confusing UI: the user can select and change the hint color, but it has no effect on the output.

**Recommendation**: Either complete the three-point interpolation or remove the hint slot. Half-implemented features erode trust.

### 3.9 Commented-Out Code Creates Design Debt

Across the codebase, roughly 30% of lines are commented out: preset buttons in `Easing`, circle/ellipse toggle in `RadialControls`, background size experiments in `CanvasPreview`, alternative icon choices. This is prototype archaeology. It records decisions but clutters the codebase.

**Recommendation**: For the rebuild, capture the design intent of commented-out features in the design system documentation rather than in dead code. The preset system for easing curves, for example, is a good feature that should be designed properly rather than preserved as commented JSX.

---

## 4. Scalable Design System Proposal

### 4.1 Component Hierarchy

```
GradientWorkspace
  Canvas (full viewport, renders all layers)
  ToolSurface (floating layer above canvas)
    CommandBar (top: gradient type, mode switches)
    ControlPanel (center: active spatial control)
    PropertyBar (side: context-dependent property controls)
    ColorDock (bottom or side: color management)
  LayerPanel (expandable: gradient list, HTML layers)
```

### 4.2 Design Tokens

```css
/* Surfaces */
--surface-glass-bg: hsl(0 0% 0% / 0.15);
--surface-glass-blur: 16px;
--surface-glass-border: hsl(0 0% 100% / 0.12);
--surface-glass-shadow: 0 4px 24px hsl(0 0% 0% / 0.2);

/* Spatial controls */
--control-radius: 300px;     /* default spatial control size */
--control-handle-size: 24px;
--control-handle-active: 28px;
--control-guide-color: hsl(0 0% 100% / 0.3);
--control-guide-dash: 4 4;

/* Interaction */
--transition-fast: 150ms;
--transition-medium: 250ms;
--transition-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
--transition-ease: cubic-bezier(0.4, 0, 0.2, 1);

/* Typography */
--font-mono: 'SF Mono', 'Fira Code', monospace;
--font-label: system-ui, -apple-system, sans-serif;
--label-size: 11px;
--value-size: 14px;
```

### 4.3 Panel System

Every floating panel should be an instance of a `FloatingPanel` component:

```typescript
interface FloatingPanel {
  id: string;
  position: 'top' | 'center' | 'left' | 'right' | 'bottom';
  anchor: 'viewport' | 'canvas' | 'cursor';
  draggable: boolean;
  resizable: boolean;
  collapsible: boolean;
  glassmorphic: boolean;
}
```

This eliminates the hardcoded absolute positioning. Panels declare their intent (`position: 'top'`, `anchor: 'viewport'`), and a layout manager resolves actual pixel positions. This enables draggable panel rearrangement and persistent layout preferences.

### 4.4 Spatial Control Protocol

All spatial controls (`Radius`, `Pad`, `Easing`, and future controls like a color wheel) should implement a common interface:

```typescript
interface SpatialControl<T> {
  value: T;
  onChange: (value: T) => void;
  size: number;                    // viewport-relative sizing
  snapIncrement?: number;
  keyboard: boolean;               // keyboard navigation enabled
  ariaLabel: string;
  guides: 'dots' | 'grid' | 'rings' | 'none';
}
```

This formalizes the shared patterns: SVG canvas, guide rendering, drag handling, touch support, value display, and accessibility attributes. The current `Radius`, `Pad`, and `Easing` already share ~70% of their interaction logic (mousedown/mousemove/mouseup with coordinate conversion). Extract that into a `useSpatialDrag` hook.

### 4.5 Gradient Model

```typescript
interface GradientLayer {
  id: string;
  type: 'linear' | 'radial' | 'conic';
  colors: ColorStop[];
  easing: CubicBezierPoints;
  colorSpace: ColorSpace;
  hueInterpolation: HueInterpolation;

  // Type-specific parameters
  linear?: { angle: number };
  radial?: { x: number; y: number; shape: 'circle' | 'ellipse'; extent: RadialExtent };
  conic?: { x: number; y: number; fromAngle: number };

  repeating: boolean;
  precision: number;  // stop count
  visible: boolean;
  locked: boolean;
}

interface GradientDocument {
  layers: GradientLayer[];
  width: number;
  height: number;
  background: string;
}
```

This model is serializable (JSON-safe), supports multiple layers, and separates concerns clearly. Each layer can be independently toggled, locked, or reordered.

---

## 5. Interaction Design Principles

### 5.1 The Canvas is the Product

The gradient preview should never be smaller than the viewport. Standard editors treat the preview as a secondary artifact of form inputs. This tool inverts that hierarchy: the gradient IS the interface, and controls are ephemeral tools that appear when needed and disappear when not.

**Principle**: Controls serve the canvas. The canvas never serves the controls.

### 5.2 Shape Mirrors Parameter

Angle is controlled by a circle. Position is controlled by a plane. Easing is controlled by a curve. Color is controlled by a wheel. Every parameter should be manipulated through a control whose geometry matches the parameter's mathematical shape. This is why sliders and number inputs feel wrong for spatial parameters.

**Principle**: The shape of the control should be the shape of the parameter space.

### 5.3 Immediate Feedback, Always

Every drag, every click, every parameter change should update the full-viewport canvas in real-time. The 0.3s spring animation on property changes provides satisfying response without lag. Never batch updates. Never show a "preview" separate from the output.

**Principle**: The feedback loop is zero-length. Input and output are the same surface.

### 5.4 Progressive Disclosure Through Spatial Zones

The current tab system already does this partially: "move" shows the pad, "rotate" shows the dial, "ease" shows the curve editor. Scale this principle: controls appear in spatial zones around the canvas. The top zone holds mode selection. The center holds the active spatial control. Side zones hold context-dependent properties. Bottom zone holds color management.

**Principle**: Information density increases toward the center of attention.

### 5.5 Tools, Not Forms

The bezier editor is a tool. The rotation dial is a tool. These are instruments, not form fields. They should feel like holding a physical tool: immediate response to pressure, position, and gesture. The `useSpatialDrag` pattern captures this: pointer down begins manipulation, pointer move adjusts, pointer up commits.

**Principle**: Design instruments, not forms.

---

## 6. Priority Actions for the Rebuild

| Priority | Action | Impact |
|---|---|---|
| P0 | Define `GradientLayer` model type | Unlocks serialization, undo/redo, multi-layer |
| P0 | Extract `FloatingPanel` component | Eliminates magic positioning, enables draggable panels |
| P0 | Extract `useSpatialDrag` hook | Deduplicates 70% of interaction code across Radius/Pad/Easing |
| P1 | Replace inline styles with design tokens | Consistency, theming, dark mode |
| P1 | Add keyboard support to spatial controls | Accessibility baseline |
| P1 | Replace mix-blend-mode with proper glass panels | Text readability guarantee |
| P1 | Remove or complete hint color feature | Clean up half-implemented state |
| P2 | Build purpose-built color wheel | Remove heavyweight dependency |
| P2 | Add preset system for easing curves | Restore commented-out feature properly |
| P2 | Implement gradient layer list | Multi-gradient composition |
| P3 | Add URL serialization for sharing | Depends on GradientLayer model |
| P3 | Add export (CSS, SVG, PNG) | Depends on GradientLayer model |

---

## 7. Technical Notes

### CSS Architecture Observation

The codebase has three styling systems running simultaneously:
1. **Tailwind CSS** (imported in `styles.css`, used sporadically in `Slider`)
2. **Inline React styles** (dominant pattern across all components)
3. **Custom CSS classes** with obfuscated names (`cxwqm2n`, `bhq6oe8`, `nqt0sva`)

The obfuscated class names suggest these were generated by a CSS-in-JS tool at some point and then extracted into plain CSS. They should be renamed to semantic names in the rebuild.

### Animation Architecture Observation

The `CanvasPreview` component uses Framer Motion's `useMotionValue` + `useMotionTemplate` to create GPU-accelerated gradient transitions. This is the right approach: the gradient string is assembled from motion values, so intermediate frames are computed by the animation engine rather than triggering React re-renders. Preserve this architecture.

### Color Engine Observation

The `colorjs.io` integration with cubic bezier easing applied to the interpolation parameter produces results that CSS native gradients cannot match. The `generateColorStops` function creates discrete stops that approximate a continuously-eased gradient. The `numStops` slider (2-20) controls the fidelity of this approximation. At 10+ stops, the result is visually indistinguishable from a continuous gradient. This is a genuine technical advantage worth marketing.
