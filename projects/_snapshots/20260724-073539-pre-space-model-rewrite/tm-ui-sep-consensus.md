---
title: Transport Matters www/ UI Separation — Peer Consensus Plan
type: research
tags: [transport-matters, www, design-system, separation, grooming, consensus]
summary: One Tailwind v4 @theme base + a shared api.ts/hooks spine straddle both UI layers, and canvas really does import the inspector's ExchangeDetail. Groom first, then cut; resolve ExchangeDetail before any shared-component ban.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-01
updated: 2026-07-01
---

> Stale: superseded by `~/.mdx/projects/tm-sep-proposal.md` v5.

# www/ UI separation: peer consensus

## 1. Corrected design-system reality
Two layers, one substrate. **Layer A (canvas):** `session-canvas/**`, `engine/**`, `ambient/**`, `theme/**`, `stores/themeStore`, canvas-flavoured `components/*`. **Layer B (inspector):** `app.tsx`, `routeLayout.tsx`, `stores/uiStore`, inspector hooks, `components/{ExchangeList,ExchangeDetail,editor/*,detail/*,routes/*}`. Both style with **Tailwind v4 utility classes from one `@theme` block** (`index.css`, confirmed the only `@theme`). `desktop/` is **not** a UI layer (`rendererBoundary.test.ts` enforces no renderer). **Ark UI is 2 launcher files** (`@ark-ui/react/combobox` + `/portal` via `CommandCenter`/`useLauncherRows`); it is not the canvas design system today. Whether Ark is the *target* is an open decision (3c).

## 2. Confirmed shared surface (exact paths)
"Zero shared components" is **refuted**. `www/src/components/ExchangeDetail.tsx` has two importers: `www/src/routeLayout.tsx` (B) **and** `www/src/session-canvas/viewers/resource/ProviderExchangeResourceViewer.tsx` (A). Through it, canvas transitively drags the inspector's full detail+editor stack:
- Direct: `api.ts`, `components/FullscreenOverlay`, `components/detail/{CodexTransportPanel,InspectTab,JsonView}`, `components/icons`, `hooks/{useFullscreen,useMeta}`, `lib/{exportInspect,formatting,queryKeys}`, `stores/uiStore`, `types.ts`.
- Via `InspectTab`: `detail/{CodexTimeline,ContentBlocks,ExchangeCard,atoms,mutations}`, `editor/{MessagesSection,SystemSection,ToolsSection}`, `hooks/useCollapsibleSet`, `lib/overrideTargets`.

Genuinely-neutral spine (both layers): `api.ts`, `hooks/useMeta`, `lib/queryKeys`, `types.ts`, and the `index.css` token base.

## 3. Per-debt disposition
| # | Debt | Disposition |
|---|------|-------------|
| 1 | `canvasStore`/`canvasLabStore` + 3-way route assembly (A-local) | GROOM-FIRST |
| 2 | `legacy`→`inspector` rename (`route.ts` `RootRoute`/`selectRootRoute`, `rootShell.tsx` `LegacyApp`/`routeComponents` only) | **GROOM-FIRST** (D2) |
| 3 | `useCanvasDropTargets` raw `window.transportMattersDesktop` → `desktopHost.ts` | GROOM-FIRST |
| 4 | `api.ts` god-client split | SEPARATION-SEAM (double-work) |
| 5 | dup mutation/sampling/thinking hooks (B-local, now A-reachable via #9) | GROOM-FIRST |
| 6 | `index.css` 839 LoC token+class file | SEPARATION-SEAM (double-work) |
| 7 | www test gaps | GROOM-FIRST |
| 8 | www/desktop config dup | DEFER |
| **9** | **`ExchangeDetail` cross-layer coupling** | **SEPARATION-SEAM (blocks the shared-component ban)** |

**D2:** rename is identifier-only on shell files that never relocate — cut once, de-risks the Phase-2 move-map. Not double-work. **D3 token-definition sites (4):** `index.css @theme` (66 tokens; 73 file-wide, shared base), `index.launcher.css :root` (35 `--launcher-*`, canvas), runtime `theme.applyThemeTokens` (`--color-accent`, `--accent-rgb`, `--pane-*`), and `hooks/useThemeTokens.ts` (`THEME_TOKEN_NAMES`/`useThemeTokens` names+clears those 7 runtime vars, wired via `rootShell.tsx:RootShell`). `session-canvas/canvas.css` and `launcher/launcher.css` **consume**, define nothing.

## 4. Ordered plan (hard ordering)
**Phase 1 — groom-first (each gated `just check` + `just test`):**
1. Rename `legacy`→`inspector` (`route.ts` `RootRoute`/`selectRootRoute`, `rootShell.tsx` `LegacyApp`/`routeComponents` only).
2. Route `useCanvasDropTargets` through `desktopHost.ts`.
3. Consolidate `canvasStore`/`canvasLabStore` + unify route assembly.
4. De-dup inspector mutation/sampling/thinking hooks in place.
5. Prune dead `index.css` classes (shrink only, no token partition).
6. Fill test gaps; add a boundary test pinning the `ExchangeDetail` A↔B import as the known breach.

**Phase 2 — separation (Phase 1 landed):**
1. **Resolve #9 first** (decision 5b) — before any shared-component ban.
2. Create `canvas/`, `inspector/`; keep `main.tsx`+`rootShell.tsx`+`route.ts` as routing-only shell.
3. Move Layer A / Layer B trees per §1.
4. Split `api.ts` → `canvas/api` + `inspector/api` + `shared/apiCore`; partition token substrate (`index.css @theme` + `index.launcher.css` + `applyThemeTokens`/`useThemeTokens`) into neutral base + `canvas.css`/`inspector.css`; relocate `useMeta`/`queryKeys`/`types` → `shared/`.
5. Add `canvas/CLAUDE.md` + `inspector/CLAUDE.md`.

**Hard ordering:** P1.1 before shell extraction; #9 resolved before the shared-component ban; #4/#6 partitions land **inside** Phase 2 only.

## 5. Open decisions for the human
- **(a) Token model:** shared neutral base `@theme` + layer-specific classes (recommended — the color scale is genuinely shared; duplicating violates DRY) **vs** fully separate token sets per layer.
- **(b) `ExchangeDetail` ownership:** canvas forks a lean read-only provider viewer (recommended — promoting drags the whole inspector editor subtree into "shared") **vs** promote `ExchangeDetail` to a neutral shared component.
- **(c) Ark intent:** is `canvas = Ark` the *target* (only the 2 newest launcher files use it, i.e. mid-migration) **vs** Ark is an incidental launcher-combobox convenience and canvas stays Tailwind?
