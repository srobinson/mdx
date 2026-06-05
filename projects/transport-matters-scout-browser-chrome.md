# Browser chrome: scout report and slice plan

Repo: transport-matters, baseline main 8f500b58. Mockup (design reference, agreed by owner): https://claude.ai/code/artifact/6c54e83f-ffb8-43c0-8454-bf6f85b1b5f4

Cite symbols, never line numbers. Gates verbatim: `just check`, `just test`, `pnpm --filter @tm/shell test`, desktop `just check`, `pnpm package:smoke`. Every PR carries a "Road test" section (`just dev desktop`, dev channel, Gateway 18789, devtools 18790).

## Reuse Map

Canvas (`www/packages/canvas/src`)
- Reuse: `workbench/chrome/PaneChrome.tsx` strip slot (`PaneChromeProps.strip`) and `workbench/PaneWindow.tsx` (`viewer.strip?.(ref)`); no change needed.
- Reuse: `viewers/registry.tsx` `defineViewer` browser entry; captured-run entry's `strip: RunVitalsStrip` is the registration template.
- Reuse: `workbench/controls/IconButton.tsx` + `controls.css` `.canvas-icon-button` for back/forward/reload/history/remove buttons (disabled state already styled).
- Reuse: `workbench/chrome/pane-window.css` `.canvas-pane-window__strip`, `.run-vitals-strip*` (spacing, status pill) as style precedent; `styles/tokens.css` tokens.
- Reuse: `icons/createIcon.tsx` + `icons/glyphs/*`, exported from `icons/index.ts` (add back, forward, reload, history glyphs).
- Reuse: `launcher/launcher.css` `.launcher__input` as the only text-input precedent; address field CSS is new, modeled on it.
- Reuse: `browsing/browserPaneClient.ts` `navigateBrowserPane` (add history/reload/history-list/history-remove beside it).
- Reuse: `browsing/browserPaneStore.ts` `useBrowserPaneObservation` for can_go_back / can_go_forward.
- Reuse: `browsing/presentation.ts` `placementVisibility`, `buildPlacementFrame`, `insetBounds`; `browsing/useBrowserPanePresentation.ts` `measure`/`wake`.
- Reuse: `interactions/dnd/CanvasDragSessionOverlay.tsx` layer rects and `launcher/launcher.css` panel width for per-pane intersection.
- Reuse: `engine/react/PaneFrame.tsx` `dragModeForTarget` (resize hit test) and `pane-window.css` `.canvas-pane-window__resize`.
- Remove: `workbench/chrome/BrowserPaneSubtitle.tsx` once the address field owns the URL.
- Keybindings: `keybindings/engine.ts`; typing in the address field must not trigger canvas bindings.

Contract / Gateway
- Reuse: `packages/contract/src/browsing/index.ts` `BrowserPaneObservationWire`, `BrowserPanePresentationWire`, `isPresentationWire`; `packages/contract/src/desktop/index.ts` `BrowserPanePlacement.navigation`, `BrowserPaneHostObservation`.
- Reuse: `packages/browsing/src/domain/browserPane.ts` `navigateBrowserPane` (same url bumps seq: this IS reload), `packages/browsing/src/service/BrowserPaneSessions.ts` `navigate`, `packages/browsing/src/server/browsingRouter.ts` `POST /browser-panes/:id/navigate` and `observationInput`, `projections/browserPaneView.ts`.
- Desktop: `desktop/src/app/browserPanes/BrowserPaneHost.ts` `present`, `#navigate` (seq gate), `#report`, `#observe`; `registerBrowserPaneHost.ts` `parsePlacement`.
- Python: `api/src/transport_matters/api/v1/browsing_contracts.py`, `controlplane_gateway_browsing.py` (`navigate_browser_pane` template), `browsing_proxy.py` (`register_browser_pane_forwards`, the canvas path), `browsing_mcp.py`, `browsing_routes.py`. Tool inventory tripwire: `test_controlplane_action_skins.py`.
- Director parity: `desktop/src/browserPaneProof.ts` (`mcp.call` per verb + `pollValue`); `just browser-pane-proof`.

Over 600 lines: `api/.../main.py` 671 (do not touch). Nothing else in the chain.

## Slice 1: per-pane hide gate

Today `placementVisibility` hides every browser view when `dragging || overlayOpen` (both canvas-wide). Owner wants: hide only panes whose rect intersects the covering surface.
- Launcher: the panel rect (root is a full scrim; the panel is `min(--launcher-width, 100vw - 32px)` centered). Dock and fullscreen keep the current whole-canvas behaviour if they truly cover the canvas; state the reason in the PR.
- Drag: only panes intersecting the drag overlay layers (origin/target rects `CanvasDragSessionOverlay` already computes; expose the rects from the drag session store rather than measuring DOM twice).
- Tests in `browsing/presentation.test.ts`: non-intersecting pane stays visible under launcher and under drag; intersecting pane hides. Update `docs/plans/BROWSER-PANE-PLAN.md` acceptance line.

## Slice 2: 7b chrome strip + resize corner A

1. Contract: `BrowserPaneObservationWire`/`BrowserPanePresentationWire` gain `can_go_back`, `can_go_forward`; desktop `BrowserPanePlacement.navigation` becomes `{kind:"url", url, seq} | {kind:"history", delta: -1 | 1, seq}` (declarative, seq-gated; a replayed frame never re-navigates).
2. Browsing: domain `historyBrowserPane` + event; `reload` = `navigateBrowserPane` to the page shown (`pane.observed.observedUrl`, else `pane.url`; owner decision, review finding 5) via a service method; history is a single-step intent `{kind:"history", delta}` (owner decision, KISS: at most one step per seq advance, two clicks folded into one frame collapse to one step, accepted); routes `POST /browser-panes/:id/history` `{delta}` and `/reload`; `observationInput` reads the two booleans; projection defaults false when unobserved.
3. Desktop: `BrowserPaneHost.#navigate` handles history via `webContents.navigationHistory.goBack/goForward`; `#report` adds the booleans; add `did-navigate-in-page` listener.
4. Python: contracts, gateway fronts, proxy forwards, MCP tools `browser_history`, `browser_reload`, REST routes; update the tool inventory test.
5. Canvas: `workbench/chrome/BrowserChromeStrip.tsx` (IconButton x3 + address input, Enter navigates, Esc restores, degraded pill from `run-vitals-strip__status` shape only when state != composited); register as `strip` on browser viewer; delete `BrowserPaneSubtitle`; glyphs; client verbs; `buildPlacementFrame` emits the intent from the ref (ref carries history intent from the wire).
6. Resize corner A: move the resize hit area outside the native rect, onto the pane frame's border ring plus a few px beyond (`dragModeForTarget` accepts it); chevron paints on the border ring. No padding on the body. Verify the grab works on a composited browser pane.
7. Director: `browserPaneProof.ts` calls `browser_history`/`browser_reload`, polls `can_go_back`.

## Slice 3: 7c history

- Gateway-owned `BrowserHistory` in `packages/browsing` (url, title, last_visited, visit_count, capped), appended when an observation reports a finished navigation; persisted as one JSON file under the channel home (find how Gateway resolves TRANSPORT_MATTERS_HOME / channel today; reuse that path). Verbs `GET /browser-history`, `DELETE /browser-history/:id`; Python fronts/proxy/MCP `browser_history_list`, `browser_history_remove`; director parity.
- Canvas: history toggle IconButton after the address field. Open, the list renders INSIDE the strip (in flow, full width, rows: url, title, 28px ✕ IconButton). The reservation shrinks and `insetBounds` moves the native view down; ensure the presentation driver wakes on strip growth (ResizeObserver on the reservation is the general fix). Click row navigates, ✕ removes, Esc/button closes. No overlay over the page, ever.
- Persist-then-reload test for the file store.

## Slice 3 spec (owner approved 2026-08-28)

Baseline main 104bfb4e (slices 1 and 2 merged).

- Record intent, not observation. An entry is written only when a URL is deliberately requested: address field Enter, history row click, palette open, MCP `browser_open` / `browser_navigate`. Hook is one line each in `BrowserPaneSessions.open` and `.navigate`. Back, Forward, Reload never write. In-page pushState, redirects, link clicks inside the page are observations and never write. Opens whose origin is the bridge `open-request` (target=_blank) are excluded; user and agent opens are included.
- Entry: `url` (desired URL as requested, normalised: scheme lowercased, trailing slash and fragment dropped), `title` (from the first observation after that navigation seq), `last_visited`, `visit_count`. Re-requesting an existing URL bumps count and time. Cap 100, ordered by `last_visited` desc. Remove deletes the entry.
- Storage: one JSON file in the channel home, written through by the Gateway on every change, loaded at startup, persist-then-reload test. Find how the Gateway resolves the channel home today and reuse it.
- Verbs: `GET /browser-history`, `DELETE /browser-history/:id` on the Gateway and the canvas proxy; Python fronts, MCP `browser_history_list` / `browser_history_remove`, REST (`GET /browser-history` plus command-style `POST /browser-history/remove`, consistent with the other browser routes on that skin; owner decision at review), tool inventory test, director parity in browserPaneProof.
- Canvas: history toggle IconButton after the address field; open, the list renders inside the strip in flow, full width rows (url, title, 28px ✕ IconButton), the reservation shrinks and the native view moves down (presentation driver must wake on strip growth; ResizeObserver on the reservation). Row click navigates, ✕ removes, Esc or the button closes. No overlay over the page. Design: mockup section "History open".
