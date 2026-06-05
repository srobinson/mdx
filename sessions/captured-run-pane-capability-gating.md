---
title: Provider-parametric captured pane + capability-gated spawn
type: sessions
tags: [frontend, transport-matters, canvas-lab, captured-run, capabilities, codex, pane-chrome]
summary: Turned the captured Claude pane into a provider-generic captured-run pane (claude|codex) with capability-gated spawn buttons and one-line chrome polish.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

# Provider-parametric captured pane + capability-gated spawn

Branch `feat/captured-pane-gated` (off main @9d5681f), commit `9a58940`, PR #69.
Frontend-only slice in `www/`; `api/` and `desktop/` untouched.

## Summary

Three coupled deliverables landed in one PR:

1. **Provider-parametric captured pane.** `CapturedClaudePane` → `CapturedRunPane`,
   parameterized by `provider: CliName` (`claude` | `codex`), connecting to
   `/api/captured-runs/{provider}/terminal`. One component for both CLIs — not a
   codex copy. Reuses the shared `useTerminalSession` core and the
   `captured-run.*` wire frames.
2. **Capability-gated spawn.** A single `capabilitiesStore` fetches
   `GET /api/capabilities` once; the lab renders **Spawn Claude** / **Spawn Codex**
   and hides a button when that CLI reports `installed: false`.
3. **#23 chrome polish.** Single-line lab pane header (title + F/E/CLOSE), no
   kicker, no state label, no captured sub-row; `(captured)` dropped from labels.

## Architecture Decisions

- **One `captured-run` ref kind with a `provider` field**, not two kinds. One
  registry entry, distinct pane id per provider (`captured-run:claude` /
  `captured-run:codex`). This mirrors the backend's single `/captured-runs/{cli}/`
  route and the `capabilities.clis` dict keyed by `CliName`, and is the cleanest
  reading of the directive's "provider param" emphasis. The wire frame names
  (`captured-run.ready`/`.error`) were already provider-agnostic and were kept.
- **Capabilities source = a fetch-once zustand store** (`lab/capabilitiesStore.ts`)
  exposing `ensureLoaded()` (idempotent: no-op unless `status === "idle"`) and a
  `cliInstalled(state, name)` selector that defaults to `false`. So a button is
  hidden while loading and on error, not just on `installed: false` — it never
  offers a launch that would fail. The fetch itself (`fetchCapabilities`) lives in
  `www/src/api.ts` next to the other clients; types in `www/src/types.ts`.
- **Backend shape was `{ clis: { claude, codex } }`**, with a `clis` wrapper —
  the dispatch paraphrased it as flat `{ claude, codex }`. Bound to the real
  shape after reading `api/v1/capabilities.py`. `HarnessCapabilities` already in
  `types.ts` is a different concept (harness protocol flags) and was left alone.
- **`compact` is opt-in on the shared `PaneChrome`**, not a CSS hack and not a
  production change. In compact mode it omits the viewer kicker `<p>` and the
  visible state `<span>` (keeping `data-state` + the aria-label for a11y/styling).
  The lab passes `compact`; production `PaneWindow` does not, so the production
  canvas chrome is byte-for-byte unchanged. The captured pane's own header strip
  was removed entirely; its identity now lives in the window title.
- **DRY: `cliLabel(provider)` lives in the light `model/paneRecords.ts`** so the
  registry's synchronous `title()` path can use it without statically importing
  the lazy `CapturedRunPane` (which would drag the heavy xterm chunk into the main
  bundle). Verified in the build output (see below).

## Performance Notes

Bundle split preserved. Production build keeps `CapturedRunPane` as a ~1.4 kB
lazy chunk and xterm in its own shared `terminal-pane` chunk (~344 kB, gzip ~88 kB),
pulled in only when a terminal/captured pane mounts. The `paneRecords` chunk
holding `cliLabel` is 0.07 kB. No xterm in the main/registry path.

## Deviations from Spec

- The dispatch said "add the codex pane **kind**", which could read as two ref
  kinds. Implemented as one `captured-run` kind + `provider` field instead (DRY,
  matches the backend's one-route/one-dict shape). Functionally codex is fully
  spawnable; the divergence is internal modeling.
- Lab content-pane titles changed from the raw pane id (`lab-N`) to the viewer
  title (`Claude` / `Codex` / `Terminal`) so the now-single-line compact header
  carries identity. Demo card/ruler stub panes keep their pane id.

## Open Items

- **Live captured-run smoke not performed** (dispatch marked it best-effort).
  The live path exercises the TM proxy and has a known pre-existing backend
  `ConnectionRefused` issue unrelated to this frontend slice; the provider→endpoint
  wiring is covered by unit tests instead.
- Capabilities gating is lab-only by design. If production ever grows launch
  buttons, `capabilitiesStore` is the reusable source (it is not lab-coupled
  beyond its current location under `lab/`).

## Verification

- Frontend: `pnpm lint` (biome), `pnpm typecheck`, `pnpm test` (592 passed / 91
  files, incl. new provider-param pane, capability gating, capabilities store,
  registry `captured-run`, lab-store `addCapturedRun`, codex socket URL; cssColocation
  green), `pnpm build`.
- Desktop: `tsc` + build + `vitest` (28 passed).
- Backend: `cd api && just ci` — ruff + mypy + migration-smoke + 1284 pytest passed.
