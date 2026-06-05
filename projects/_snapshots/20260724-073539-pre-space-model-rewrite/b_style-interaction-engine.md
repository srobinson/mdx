---
title: "b_style Interaction & Rendering Audit"
category: projects
tags: [b_style, gradient-editor, interaction, rendering, canvas]
---

# b_style Interaction & Rendering Audit

Audit of the gradient editor prototype at `apps/basic` within the b_values monorepo. This document covers the rendering strategy, interaction model, bezier curve editor, performance characteristics, and a proposal for a unified interaction engine in the rebuild.

## 1. Architecture Overview

The app is a TanStack Router SPA with five spatial interaction components, all rendered as overlays on a full-viewport gradient canvas. The primary route (`test-radius`) composes:

| Component | Purpose | Rendering Tech | Input Model |
|---|---|---|---|
| `CanvasPreview` | Full-viewport gradient background | CSS `background-image` via Motion `useMotionTemplate` | None (display only) |
| `Easing` | Cubic bezier curve editor | Inline SVG (280x280 viewBox) | Mouse events on SVG elements + document-level listeners |
| `Radius` | Circular rotation dial | SVG rings + CSS `transform: rotate()` via custom property | `atan2` angle calculation from mouse/touch position |
| `Pad` | 2D crosshair position control | Inline SVG (viewport-scaled) | Mouse/touch with snap and clamp |
| `RadialControls` | Radial gradient options | DOM buttons | Click only |

Supporting components (`CommandCenter`, `ColorControl`, `Pallette`, `Controls`) are standard DOM button panels with inline styles.

## 2. Rendering Layer Analysis

### 2.1 Strategy: SVG + CSS Custom Properties

The rendering layer uses a hybrid of inline SVG for interactive overlays and CSS for the gradient canvas. There is no Canvas2D or WebGL anywhere.

**SVG overlays:** Each spatial control (`Easing`, `Pad`, `Radius`) renders its own `<svg>` element with hardcoded viewBox dimensions. Guide lines, control points, and curves are SVG primitives (circle, line, path). The `Radius` component uses an additional layer of CSS transforms: a wrapper div with `transform: rotate(var(--rotation))` positions the drag handle, while SVG handles the decorative ring.

**Gradient canvas:** `CanvasPreview` uses `motion/react`'s `useMotionTemplate` to construct CSS gradient strings that interpolate motion values for angle, position, and from-angle. The `<motion.div>` receives the interpolated `backgroundImage` style. This is a clean approach: the browser's CSS gradient renderer handles all the heavy lifting, and Motion handles value interpolation at ~60fps outside React's render cycle.

**Styling:** A mix of CSS classes (obfuscated names like `cxwqm2n`, `w1wikcwy`, `nqt0sva`) in `styles.css` and extensive inline styles. The glassmorphism system in `glass.css` uses `backdrop-filter: blur() contrast()` for frosted effects but appears largely unused in the current gradient editor route.

### 2.2 Assessment

**Strengths:**
- SVG is the right choice for these overlays. The element count is low (under 200 nodes per control), and SVG gives free hit testing, CSS transitions, and resolution independence.
- The Motion template approach for gradient interpolation is genuinely clever. It avoids React re-renders for continuous value changes, keeping the gradient animation smooth.
- CSS custom properties for rotation (`--rotation`) keep the transform declarative and animatable.

**Weaknesses:**
- Each component creates its own SVG coordinate system with independent size constants (`SIZE = 280`, `SIZE = Math.round(viewportSize * 0.9)`). No shared spatial abstraction.
- The `Pad` component reads `document.documentElement.clientHeight` at render time to compute its size. This breaks on resize and is a layout thrashing risk.
- SVG elements use `overflow: visible` to allow control points to extend beyond the viewBox (the easing editor's extended range mode), which creates invisible hit areas outside the visual bounds.

## 3. Interaction Model Audit

### 3.1 Drag System

All three spatial controls implement the same drag pattern independently:

1. **Mouse down** on the component or a specific handle sets a dragging flag (either React state or a ref).
2. **Document-level** `mousemove` and `mouseup` listeners track the drag and release.
3. **Coordinate transform** converts `clientX`/`clientY` to the component's local coordinate space using `getBoundingClientRect()`.
4. **Value transform** maps local coordinates to the domain value (angle, normalized 0-1, percentage).

This pattern is duplicated three times with subtle variations:

| Behavior | Easing | Radius | Pad |
|---|---|---|---|
| Dragging state | `useState` | `useRef` | `useState` |
| Listener attachment | Conditional (only when dragging) | Always attached | Always attached |
| Touch support | No | Yes | Yes |
| Snap support | No | Yes (configurable) | Yes (configurable) |
| Click-to-move | Yes (nearest handle) | Yes (container click) | Yes |
| Extended range | Yes (beyond 0-1) | No (clamped) | No (clamped) |

### 3.2 Specific Issues

**Easing component:**
- Uses `useState` for dragging, which means every mouse move triggers a React re-render to check the `dragging` dependency. The `Radius` component correctly uses `useRef` instead.
- The effect dependency array `[dragging, p]` means listeners are torn down and re-attached on every control point change during a drag. This creates a brief window where no listener is active, which can cause dropped frames or lost drags on fast movements.
- The `handleCanvasMouseDown` uses `setTimeout(() => setDragging(targetHandle), 0)` to transition from click-to-move to drag mode. This creates a single frame where the user has clicked, the point has moved, but dragging is not active. A rapid click-and-drag can miss the transition.
- No touch support at all.

**Radius component:**
- Uses `useRef` for dragging state, avoiding re-renders during drag. This is the correct approach.
- Listeners are always attached regardless of drag state, which means `handleMouseMove` fires on every mouse movement across the document. The early return (`if (!isDragging.current) return`) is cheap, but this is wasted work when no drag is active.
- The effect dependency `[value]` causes listener re-attachment on every value change. This means during a drag, listeners are torn down and re-created on every angle snap.

**Pad component:**
- Same always-attached listener pattern as Radius.
- Touch support is present with `passive: false` to enable `preventDefault()` on touchmove.
- The `document.documentElement.clientHeight` call happens at render time outside `useEffect`, creating a layout read on every render.

### 3.3 Animation and Transitions

- `CanvasPreview` uses Motion's `animate()` to tween between gradient states with 0.3s easeOut transitions. The angle animation includes shortest-path logic for wrap-around (crossing 0/360 boundary). This is well implemented.
- Tab switching uses `AnimatePresence` with `mode="wait"` and a scale+opacity transition. The `zoom` property in the initial/exit states (`zoom: 0`) is non-standard and may not work consistently across browsers. `scale` would be more reliable.
- The easing editor's SVG path has a CSS transition class (`svg.transitioning path`) for smooth preset animations, though presets are currently commented out.

## 4. Bezier Curve Editor Deep Dive

The `Easing` component is the standout feature. It renders a cubic bezier curve with two draggable control points, dotted guide lines connecting each point to its anchor (0,0 and 1,1), and a real-time curve path.

### 4.1 Implementation

- **Coordinate system:** A 280x280 SVG viewBox maps to normalized 0-1 bezier space. `toSVG()` and `fromSVG()` handle the transform, with Y-axis inversion (SVG Y increases downward, bezier Y increases upward).
- **Extended range:** The `allowExtendedRange` prop permits control points outside 0-1 (up to -1 to 2), enabling overshoot curves (bounce, elastic). This is a strong design choice.
- **Handle selection:** Clicking anywhere on the canvas moves the nearest handle (determined by distance to start anchor vs end anchor). This avoids the "which handle did I mean" problem that plagues many bezier editors.
- **Curve rendering:** A single SVG `<path>` element with a `C` (cubic bezier) command. Updates on every control point change.
- **Value output:** The parent receives both the control points array and a formatted `cubic-bezier()` string. The string is copiable to clipboard via click.

### 4.2 What Works Well

- The dot grid background provides spatial reference without visual clutter.
- The click-to-move-nearest-handle behavior is intuitive for rapid curve shaping.
- Extended range support enables the full CSS timing function space.
- The control point visual feedback (size change + color change when dragging) is clear.

### 4.3 Improvement Opportunities

**Snapping:** No grid snap or value snap exists. Adding optional snap-to-grid (e.g., 0.05 increments) with a modifier key override (shift for fine control) would improve precision.

**Presets:** The preset system is commented out but the data structure is sound. Reintroducing it with animated transitions between presets would be valuable. Consider a preset strip below the editor rather than separate buttons.

**Animation preview:** The bezier curve defines a timing function, but there is no visual preview of what that timing looks like in motion. A small animation preview (a dot moving along a line, or a bar filling) driven by the current curve would make the editor dramatically more useful.

**Keyboard input:** No keyboard support exists. Arrow keys for fine-tuning the active control point, tab to switch between points, and number input for exact values would improve accessibility and precision.

**Curve visualization:** The current 5px white stroke is effective but could benefit from a velocity visualization. Drawing the curve with varying thickness or color based on the derivative at each point would communicate the acceleration profile.

## 5. Performance Assessment

### 5.1 Current State

For the current single-gradient, single-overlay configuration, performance should hold at 60fps on any modern device. The rendering workload is minimal:

- SVG overlay: fewer than 20 elements, no filters, no complex clipping
- Gradient canvas: a single CSS gradient rendered by the browser's compositor
- Motion animations: spring/tween values updated outside React's render cycle
- React re-renders: only on state changes (drag start/stop, value snaps)

### 5.2 What Would Break

**Multiple layers/gradients:** The current architecture assumes a single gradient and a single active overlay. Scaling to multiple gradient layers would require:
- Multiple `CanvasPreview` instances stacked with CSS compositing. Each additional gradient layer adds a composite operation. Beyond ~8 layers with complex gradients, the compositor will drop frames.
- Multiple overlay instances competing for document-level mouse/touch events. The current model of each component attaching its own document listeners would create event handler conflicts and race conditions.

**Many color stops:** The `generateColorStops` utility creates a `Color` instance and runs `.range().toString()` for every stop on every change. With `numStops` at 20 and rapid easing curve changes, this runs 20 color interpolations per frame. The `colorjs.io` library is not optimized for hot-path usage. Pre-computing the color range and sampling it would be significantly faster.

**Rapid drag events:** The `Easing` component's use of `useState` for dragging state means React schedules a re-render on every mousemove during drag. Each re-render rebuilds the SVG path string, the dot grid, and all control point positions. The dot grid (144 circles) is recreated from scratch on every render with no memoization.

### 5.3 Quick Wins

1. Memoize the dot grid in `Easing` (it never changes).
2. Switch `Easing` dragging state from `useState` to `useRef`.
3. Conditionally attach document listeners only during active drags (all three components).
4. Cache the `getBoundingClientRect()` call at drag start rather than reading it on every mousemove.
5. Move `Pad`'s viewport size calculation into a resize observer or effect.

## 6. Interaction Engine Proposal

For the rebuild, the three interaction components should share a unified drag/gesture system rather than each implementing its own.

### 6.1 Unified Drag System

```
useSpatialDrag(options: {
  containerRef: RefObject<HTMLElement>
  onDragStart?: (point: LocalPoint) => void
  onDrag: (point: LocalPoint, delta: LocalPoint) => void
  onDragEnd?: () => void
  coordinateSpace: CoordinateSpace  // normalized, pixel, angle, custom
  snap?: { x?: number, y?: number }
  clamp?: { minX?: number, maxX?: number, minY?: number, maxY?: number }
  touch?: boolean  // default true
  cursor?: { idle: string, active: string }
})
```

This hook would:
- Manage all listener lifecycle (attach on drag start, detach on drag end)
- Cache `getBoundingClientRect()` at drag start
- Handle coordinate transforms based on the declared space
- Apply snapping and clamping
- Support both mouse and touch with a unified `PointerEvent` API
- Track drag velocity for momentum-based interactions
- Use `useRef` for all transient state (no re-renders during drag)

The three components become thin wrappers: `Easing` calls `useSpatialDrag` with `coordinateSpace: "normalized"`, `Radius` with `coordinateSpace: "angle"`, and `Pad` with `coordinateSpace: "percentage"`.

### 6.2 Overlay Rendering Strategy

**Recommendation: Stay with SVG.** The element count is low, hit testing is free, and CSS transitions work natively. Canvas2D would only make sense if overlay complexity grows to hundreds of interactive elements (unlikely for a gradient editor).

Improvements for the rebuild:
- **Shared viewport context.** A `<SpatialCanvas>` wrapper component that establishes a coordinate system, handles resize observation, and provides the container ref. All overlay components render inside this shared space.
- **Layered SVG.** One SVG element per interaction layer, rather than one per component. This prevents z-index conflicts and allows a single event delegation root.
- **Pointer capture.** Use `element.setPointerCapture()` instead of document-level listeners. This is the modern standard, handles both mouse and touch, and prevents events from leaking to other components.

### 6.3 Animation Timeline Integration

The current Motion-based gradient interpolation is effective for smooth transitions. For timeline integration:

- Extend the easing curve editor to output keyframe sequences, not just single bezier functions.
- Add a timeline scrubber that drives the gradient state at arbitrary points.
- Use Motion's `useTransform` to map a scrubber position to all gradient parameters simultaneously.
- This enables preview of gradient animations before export.

### 6.4 Multi-Layer Overlay Management

When multiple gradients need simultaneous overlays:

1. **Focus model.** Only one overlay is interactive at a time. Others render in a reduced/ghosted state. Tab or click to switch focus.
2. **Event delegation.** A single pointer event handler at the canvas root dispatches to the focused overlay. No per-component document listeners.
3. **Render priority.** The focused overlay renders above all others. Non-focused overlays use reduced opacity and simplified geometry (hide guide lines, shrink handles).
4. **State isolation.** Each gradient layer owns its state (angle, position, easing, colors). The overlay system receives the focused layer's state as props.

This avoids z-index chaos because only one overlay is ever "live" at a time.

## 7. Summary

The prototype demonstrates strong spatial interaction instincts. The bezier editor, circular dial, and 2D pad are the right primitives for a gradient editor. The Motion-based gradient canvas is a clean architecture choice.

The primary technical debt is the duplicated drag system across three components, each with slightly different (and sometimes incorrect) lifecycle management. The rebuild should extract a `useSpatialDrag` hook, adopt `PointerEvent` with capture, and establish a shared spatial coordinate system.

Performance is fine for the current scope but would degrade with multiple layers due to document-level listener conflicts and unoptimized color interpolation. The fixes are straightforward: memoization, ref-based drag state, and a focus model for multi-layer editing.
