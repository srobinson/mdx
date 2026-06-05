# PR 499 adversarial review

Reviewed `ec87fef70a057596f9d5d22eb1348d9ab9244fc8` against `8f500b5884900414516a2927773d864576b77147`.

Found 5 candidate findings for triage: 0 Blocker, 3 Major, 2 Minor.

## Major

### 1. `www/packages/canvas/src/browsing/presentation.ts:174` The cover model omits interaction surfaces owned by the renderer

Observation: `OVERLAY_COVER_SELECTORS` measures the launcher control and panel, plus the dock menu. It excludes the full window launcher scrim and the dock chip. During a drag, `dragCovers` also returns no cover for `none` and `hint` targets. The visible browser page remains a native child view in each excluded region.

Impact: A browser page beside the launcher panel sits above the modal scrim, so it is neither dimmed nor intercepted by the scrim and an outside click can reach the page instead of closing the command center. A pane intersecting the dock chip can cover the chip. During a pane, dock, or external file drag, crossing a visible native view can transfer input away from the Canvas renderer before Canvas receives the event needed to resolve the target and create a cover. The drag can stall, miss its drop, or reach the embedded page.

Basis: `CommandCenter` defines the scrim as the outside click dismissal surface. `useCanvasDropTargets` installs `dragover`, `dragleave`, and `drop` only on the Canvas surface. `BrowserPaneHost` adds each page through `contentView.addChildView` and exposes it through `setVisible`. The base implementation hid every native view as soon as a drag session existed.

Caveat: The PR explicitly intends panes beside the launcher panel and away from a painted drag layer to remain visible. That visual intent conflicts with the renderer's larger input ownership regions. The launcher path is source proven. Cross `WebContentsView` drag routing remains platform dependent and needs an Electron road test.

Changed code:

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/browsing/presentation.ts#L145-L150

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/browsing/presentation.ts#L172-L176

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/browsing/presentation.ts#L200-L217

Execution context:

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/dnd/useCanvasDropTargets.ts#L55-L95

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/desktop/src/app/browserPanes/BrowserPaneHost.ts#L94-L113

### 2. `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:88` Launcher cover geometry becomes stale while the launcher remains open

Observation: Launcher and dock rectangles are sampled only inside `tick`. The loop stops after the bounded settle window. Its wake sources are Canvas state, drag session state, overlay open state, and window resize. Launcher query, scope, command mode, failure, and asynchronous result changes are local launcher state and do not wake the presentation loop. No resize or mutation observer watches the measured cover elements.

Impact: After the measuring window ends, a launcher panel can grow over a browser pane while the native view remains visible above the new rows. The page can cover launcher controls and receive input. If the panel shrinks, the page can remain hidden until an unrelated subscribed event occurs.

Basis: `CommandCenter` renders content driven groups, failures, empty state, and command modes inside `.launcher__panel`. The new driver test changes the panel rectangle, then toggles the overlay off and on before asserting the second visibility state. That toggle supplies the wake missing from a real query or asynchronous result change.

Caveat: Geometry changes during roughly `LAYOUT_MOTION_MS + 100` after an existing wake are sampled correctly. Width and anchor position are relatively stable; the common risk is panel height while open.

Changed code:

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/browsing/useBrowserPanePresentation.ts#L84-L112

Test evidence:

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/browsing/useBrowserPanePresentation.test.tsx#L174-L192

### 3. `www/packages/canvas/src/browsing/presentation.ts:193` A stale dock open flag hides every browser view indefinitely

Observation: Killing the final dock entry leaves `PaneDock` mounted with local `open === true`, then its `docked.length === 0` branch returns `null`. `useDockKeybindings` continues mirroring the open state. `overlayCovers` sees an open dock with no `.canvas-dock__menu` and falls back to the full surface.

Impact: Every browser view disappears after the final dock entry is closed from the open menu. Escape can clear the invisible open state, but no visible dock control explains the disappearance.

Basis: `PaneDock.close` deliberately keeps the menu open so several entries can be cleared. The component returns `null` when the final entry is gone without resetting `open`. The new no box fallback converts that stale state into a full surface cover.

Caveat: The stale dock state also triggered the base branch's canvas wide `overlayOpen` hide gate, so the underlying defect is preexisting. This PR preserves it through the new full surface fallback and is the current changed line where the failure is applied.

Changed code:

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/browsing/presentation.ts#L190-L196

Execution context:

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/workbench/dock/PaneDock.tsx#L69-L75

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/keybindings/engine.ts#L152-L190

## Minor

### 4. `www/packages/canvas/src/browsing/presentation.ts:149` Visibility compares fractional bounds before the native host rounds them independently

Observation: `intersects` compares raw projected or measured CSS values. `BrowserPaneHost.integerBounds` later rounds `x`, `y`, `width`, and `height` separately before applying the native view bounds.

Impact: A pane and cover separated by less than one CSS pixel can be nonintersecting in Canvas, then overlap after the native view expands through independent rounding. A thin native strip can paint above launcher, dock, or drag chrome and flicker at animated edges.

Basis: The presentation intentionally handles fractional spring and transform geometry. Electron requires integer bounds, and the host rounds the native view after Canvas has already chosen visibility.

Caveat: The effect is limited to subpixel boundaries and was not confirmed in a live compositor.

Changed code:

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/browsing/presentation.ts#L145-L150

Execution context:

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/desktop/src/app/browserPanes/BrowserPaneHost.ts#L214-L221

### 5. `docs/plans/BROWSER-PANE-PLAN.md:350` The updated plan points to the wrong module and retains the superseded placement contract

Observation: The changed geometry paragraph cites `dnd/dragOverlayLayers.ts::dragOverlayLayers`, while the file landed at `interactions/dnd/dragOverlayLayers.ts`. The adjacent authoritative interface block still declares `overlayOpen` and `measureFrame`, omits `covers` and `unsettled`, and shows the old two argument `placementVisibility` signature.

Impact: A maintainer following the plan reaches an unresolvable path and implements the superseded canvas wide boolean contract instead of the landed per rect design.

Basis: The production `BrowserPanePresentationInputs` now owns `covers` and `unsettled`, and `placementVisibility` takes the placement bounds as its third argument. This PR changed the surrounding paragraph, tradeoff, and test contract to document that design.

Caveat: The interface block was already stale before this commit. Updating the adjacent design paragraph without reconciling the block creates the current internal contradiction.

Changed documentation:

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/docs/plans/BROWSER-PANE-PLAN.md#L349-L376

Production contract:

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/browsing/presentation.ts#L35-L62

https://github.com/littleorgans/transport-matters/blob/ec87fef70a057596f9d5d22eb1348d9ab9244fc8/www/packages/canvas/src/browsing/presentation.ts#L140-L150

## Verification

The complete seven file diff was reviewed at the pinned SHA. `git diff --check` reported no whitespace errors. Every changed file is below 700 lines; the new `dragOverlayLayers.ts` is 42 lines. The shared `dragOverlayLayers` derivation is DRY and feeds both the painted overlay and native visibility calculation. No repository files were written and no tests were run locally. CI owns the broad gates.
