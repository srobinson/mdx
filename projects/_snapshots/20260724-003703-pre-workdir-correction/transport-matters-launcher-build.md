---
title: Transport Matters — ⌘K Launcher Build Contract (Slice 1)
type: spec
tags: [transport-matters, launcher, cmd-k, ark-ui, design-tokens, raycast-minimal, little-background-lab]
summary: Implementation contract for the zero-chrome ⌘K command center + agent-first Agents launcher, Raycast Minimal on the existing token system, new tokens staged in index.launcher.css for clean feedback to little-background-lab.
status: active
source: orchestrator
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

# ⌘K Launcher — Build Contract (Slice 1)

Brief origin: bus brief from `transport-matters:general:1:1.1` (director), topic `cmd-k-launcher`.
Locked UX: `~/.mdx/projects/transport-matters-launcher-ui-spec.md`. Lens: `~/.mdx/projects/transport-matters-north-star.md`.
Component strategy: `~/.mdx/projects/tm-ui-component-strategy.md`. This contract supersedes the spec's
"Build order" (the RouteSwitcher→Menu pilot is DEAD) and defers the `→` override config.

## Direction (LOCKED)

**Raycast Minimal**, built ON the existing canvas token system. Quiet, monochrome, dense, fast; the
palette nearly dissolves into the dimmed canvas. The live theme is already this aesthetic
(charcoal layers, JetBrains Mono everywhere, square corners). Throwaway mockup gallery for reference:
`transport-matters/TMP/launcher-mockups/01-raycast-minimal.html`. The real build will be fully mono +
square (radius 0) because it inherits the tokens; that is intended.

## Scope — THIS slice

IN:
1. **Zero-chrome canvas** — delete the `CanvasCommandBar` button row. Resting state = no persistent
   chrome; a faint, fading first-run ⌘K hint is allowed.
2. **⌘K command center (Ark)** — global hotkeys ⌘K (root domain list), ⌘A (Agents directly), Esc
   (close); grammar ↵ enter/spawn · →/← scope nav · ⌫ back. Root domains: Agents (populated), Canvas,
   Workdir, Settings, Sessions (entries route to existing behavior; do NOT build their internals).
3. **Agents scope = the launcher** — fetch `GET /v1/runtime-templates`; agent-first rows; each row's
   subtitle = recommended target from `recommended_model.default` + `by_vendor`. Native always present.
   Four states: populated / loading (Native live immediately, specialists fill in) / empty (Native only)
   / error (Native only + retry). A list fetch NEVER blocks a spawn.
4. **↵ spawns with the RECOMMENDED target** — thread the template name through the existing spawn flow.
   Absent/Native → send no template (today's behavior, byte-for-byte).
5. **Re-home orphaned bar functions** — Reset view, Focus picker, Go-to-Lab, Theme become ⌘K
   command-center entries calling the EXISTING handlers (no new internals). Zero-chrome must not regress them.

DEFERRED (do NOT build): the `→` override config that changes model/effort/vendor/harness (eval path;
needs launch-side flag injection + `CreateRunRequest` extension — the NEXT layer). `→` may be omitted or
show the recommended target read-only. Also out: Canvas/Settings/Workdir/Sessions internals; voice/director.

## Design tokens (Stuart's directive)

- **Reuse first** via `var()`: charcoal layers (`--color-well/-surface/-raised/-hover`), edges
  (`--color-edge*`), text ramp (`--color-txt*`, `--color-label`), `--color-accent`/`--accent-rgb`,
  `--radius-*`/`--pane-radius` (currently 0), `--pane-shadow`, `--canvas-focus-ring`, `--pane-blur`,
  `--transition`, `--font-mono`, `--canvas-gap`.
- **Focused-row accent rail** maps onto `--color-agent-rail-0..5` so an agent's color is consistent
  between its launcher row and its spawned pane.
- **New tokens are sanctioned** (create what the design needs — do not be restricted). ALL new tokens go
  in a NEW `www/src/index.launcher.css` (`:root` block), imported in `www/src/main.tsx` right after
  `import "./index.css"`. Conventions (mirror LBL `src/styles.css`): `--launcher-*` prefix, grouped by
  function with section comments, `--X` + `--X-rgb` channel-triple pairs for any alpha composite.
- **Feed-back to little-background-lab is STAGE-ONLY this slice.** Keep `index.launcher.css` portable:
  a labeled `:root` block that lifts straight into LBL `src/styles.css`, plus brief inline comments.
  Do NOT bus-notify LBL and do NOT open an LBL PR — Stuart ports upstream himself. Keep launcher tokens
  STATIC (not themeable axes) so the upstream port is a clean copy with no `theme.ts`/`theme-panel.ts` wiring.
- **Gotchas:** `contain: paint` clips outer shadows/focus rings; dark-only palette (compose over any
  scene); avoid per-pane `backdrop-filter` at scale; reuse the focus-ring convention
  `rgb(var(--accent-rgb) / 0.72)`.

## Reconnaissance (firsthand, verified on main)

- **Delete target:** `www/src/session-canvas/components/CanvasCommandBar.tsx`, mounted in
  `CanvasSurface.tsx` as 2nd child of `<main class="canvas-route-shell">`; styles inline in `canvas.css`.
- **RouteSwitcher** is a segmented toggle (Canvas↔Lab via full-page reload), NOT a menu. Go-to-Lab becomes
  a Canvas-domain entry calling its `navigateToRoute`.
- **Spawn flow (8 hops, additive `runtimeTemplate`):** `api.ts createCapturedRun(harness, cwd?, oscColorReplies=true)`
  → `capturedRunStore.ensureRun` → `CapturedRunPane` → `viewers/registry.tsx` → `model/paneRecords.ts`
  (captured-run ref union + type guard + contract test) → `model/spawn.ts createCapturedRunRef` →
  `canvasStore.addCapturedRun` → `CanvasSurface onSpawnCapturedRun`. Constant
  `CAPTURED_RUN_PROVIDERS = ["claude","codex"]` in CanvasCommandBar.tsx (relocate). Absent field → NATIVE.
- **Endpoint LIVE:** `GET /v1/runtime-templates` (`api/.../api/v1/runtime_template_routes.py`) →
  `{items:[{name, vendors, required_capabilities, recommended_model:{default:{harness,vendor},
  by_vendor:{[vendor]:{model,effort}}}|null}]}`. Add `fetchRuntimeTemplates()` in `www/src/api.ts`.
- **Hotkeys:** no ⌘K/⌘A today; add a renderer-level keydown dispatcher in session-canvas (NOT Electron
  `globalShortcut`). Existing listeners: Lab Tab-to-hide-chrome, Dock Escape.
- **Ark not installed.** `pnpm install @ark-ui/react` (pin with its `@zag-js/*`; don't bump zag alone).

## Tech approach

- Ark UI headless (`combobox`/`listbox`/`menu`) styled via `data-scope`/`data-part`/`data-state` in
  vanilla CSS; ONE thin local wrapper per Ark component owning the `.css`. Use the **ark-ui MCP**
  (`list_components`/`get_component_props`/`list_examples`/`get_example`/`styling_guide`) for accurate API.
- **pnpm** only. **No "v2"/version-suffixed naming** anywhere (Stuart hard rule). Files ≤700 LOC,
  functions ≤~150. DRY: search before adding.

## Build order

1. Worktree off latest main; `pnpm install @ark-ui/react`; create `index.launcher.css` + import.
2. Ark wrapper(s) + the command-center shell (⌘K root + grammar + hotkey dispatcher), zero-chrome canvas
   (delete CanvasCommandBar, re-home its functions as entries).
3. Agents scope: `fetchRuntimeTemplates`, agent-first rows + 4 states, Native-always invariant.
4. Thread `runtimeTemplate` end-to-end; ↵ spawns with recommended target.

## Gates + verification (non-negotiable)

- Repo recipes VERBATIM: root `just check`, plus `www` `just check` (format+lint+typecheck), `www just test`,
  `www just build`. No bare tsc/pytest.
- **run/verify**: actually spawn an agent from the palette and confirm a captured-run pane appears
  (Native path and, if a template exists, the recommended-target path).
- MoE: frontend engineer + independent reviewer + design-critical eye; review loop; surface only
  dual-clean + gate-green + beautiful.

## Deliverable

Gate-green, review-clean, BEAUTIFUL PR (pull-request skill, conventional title). Report to
`transport-matters:general:1:1.1` at the early design gut-check (done) and at PR time. Human holds the
merge gate + roadtest. New launcher tokens staged in `index.launcher.css` + documented (STAGE-ONLY:
no LBL notify, no LBL PR — Stuart ports upstream himself).
