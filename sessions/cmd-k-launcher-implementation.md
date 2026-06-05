---
title: ⌘K Command Center Launcher — Implementation Record
type: sessions
tags: [frontend, transport-matters, launcher, cmd-k, ark-ui, react, design-tokens]
summary: Built the zero-chrome ⌘K command center + agent-first Agents launcher on Ark UI, threading runtimeTemplate through the captured-run spawn flow; shipped as PR #144.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

# ⌘K Command Center Launcher

Branch `feat/cmd-k-launcher` @ `3103fb5` → **PR #144**. Gates green (root `just check`,
www `check`/`test` = 923 pass/`test-e2e` = 42 pass/`build`). Roadtested live by Stuart ("works perfectly").

## Live-Test Tweaks Round 3 (`3103fb5`)

Two live-test tweaks from Stuart:

- **Escape closes the whole palette from any state.** Ark's combobox dismisses Escape via a
  document-level capture listener (closing only its own listbox), so a React wrapper
  `onKeyDownCapture` (fires at the React root, below document) lost the race. Fix: a window-level
  capture listener (`window.addEventListener("keydown", h, true)`) — window precedes document in
  the capture path — that `preventDefault` + `stopPropagation` + `close()`, gated on `open`. Added
  a test asserting Escape closes from the Agents sub-scope. See [[patterns]] (Ark Escape gotcha).
- **Removed the search-input `:focus-visible` ring** (the round-1 MINOR 6 addition on the input).
  The input is implicitly focused in the modal palette; the ring is unwanted chrome (Stuart's
  explicit Raycast-minimal call). Keyboard position stays on the active-row highlight; aria-label
  retained; scrim + listbox focus styles untouched.
- Gates: root `just check` ✓; www `just check`/`test` (923)/`test-e2e` (42)/`build` ✓.

## Post-Merge Polish — PR #145 (branch `feat/launcher-polish`)

PR #144 merged to main (squash `89e5869`). Follow-up visual polish on a fresh branch:

- **Polish (`95e8732`)**: divider → `--launcher-panel-edge` (matches panel border); tightened the
  gap to the first heading; footer — removed "TRANSPORT MATTERS", added top breathing space, made it
  full inner width, and bounded results so rows don't bleed under it.
- **Scroll regression fix (`20f04ec`)**: the footer change wrapped results in a separate inner scroll
  div, but Ark/zag scrolls `Combobox.Content` to bring the active option into view → arrowing stopped
  scrolling the highlight in and rows clipped under the footer. Fix: `Combobox.Content` is the scroll
  container again, footer is a sibling outside it inside a new `.launcher__panel` frame (all footer
  wins kept). Added `scroll-padding-block` + a `scrollIntoView({block:"nearest"})` nudge on highlight
  change (controlled highlight). New e2e regression test (3 browsers). See [[patterns]] (Ark scroll
  container gotcha). Verified the Combobox API via the ark-ui MCP before restructuring.
- **Domains-first root (`97acc42`)**: per the locked UX spec, ⌘K root no longer spills the flat agent
  list. Empty query → a DOMAINS group of five enterable domains (Agents ⌘A · Canvas · Workdir ·
  Settings ⌘, · Sessions) with a "5 domains" count + "↵ enter scope · esc close" / "TYPE TO SEARCH
  ALL" footer; agents collapsed. Any query → flat-search across all domains (Raycast model; native
  findable from cold). `buildScopeRows` gained a `query` param (root branches domains vs flat set);
  `agentSpawnRows` split from `buildAgentRows` for the flat set; Theme moved Canvas → Settings;
  `openAgents` generalized to `openScope` + ⌘, → Settings. Workdir/Sessions are thin placeholders (no
  set-cwd / transcript-browse route exists to wire). Judgment calls: wired ⌘, (spec says "later") so
  the shown accelerator isn't dead; Workdir/Sessions stay placeholders. Updated agents-at-root unit
  tests to domains-first; new 3-browser e2e (`launcher-root.spec.ts`). e2e gotcha: scope row-content
  assertions to `.launcher__row-title` — a typed query value collides with the row title under
  `getByText` on some browsers (strict-mode 2-element violation).
- Gates: root `just check` ✓; www `just check`/`test` (928)/`test-e2e` (54)/`build` ✓.

## Review Fix Round 2 (`079c295`)

GATE BLOCKER (e2e is a separate `just test-e2e` recipe, not part of `just test`, so it
slipped earlier) + one Codex Major:

- **Zero-chrome e2e readiness.** `canvas-persistence.spec` was the only e2e ref to the deleted
  `Canvas commands` toolbar (the `canvas-lab-*` specs target the still-present Lab bar). Swapped the
  toolbar wait for a zero-chrome signal (route shell + populated picker row).
- **Reload re-fit is non-deterministic to pixel-match.** Reload hydration runs a non-persisted,
  browser-dependent canvas auto-fit (translate + small zoom; viewport isn't in the persisted shape),
  so the cross-reload `boundingBox` pixel-match flaked at the tolerance boundary (~12px Chromium,
  ~24px WebKit). Replaced it with a fit-agnostic on-screen render check (pane substantial + centre
  on-screen); exact arrangement persistence stays proven by `storedPaneRects toEqual`. Added
  `test.use({ reducedMotion: "reduce" })` for settled, unanimated transforms (also removes a
  minimize→dock race). Behavioral intent unchanged.
- **Hook under cap.** Split `useCommandCenter` (164 LOC) → extracted row derivation + collection +
  highlight + status into `useLauncherRows`; main hook ~120 LOC. No behavior change; render
  untouched (return shape identical).
- Gates: root `just check` ✓; www `just check`/`test` (922) /`test-e2e` (42, green across 3
  consecutive full-suite runs)/`build` ✓.

## Review Fix Round (`52796fc`)

Both reviewers passed PR #144 with no Blockers; applied 4 Major + 6 Minor:

- **Vendor-precedence spawn.** `templateSpawnHarness` now derives the native harness
  from `recommended_model.default.vendor` BEFORE iterating `vendors[]`, so a template
  with `default.vendor: openai` + `vendors: [anthropic, openai]` spawns codex (the
  advertised target) instead of vendors[0]. Fail-before/pass-after tests added.
- **⌘A yields to Select-All.** `useLauncherHotkeys` skips the Agents accelerator when an
  editable element is focused and the palette is closed. Extracted a shared
  `isEditableTarget` (`lib/domFocus.ts`) covering input/textarea/select/contenteditable/
  `[role=textbox]`; refactored `useRouteHotkeys` to reuse it (DRY). New hotkey test file.
- **Thin-wrapper discipline.** Lifted all non-render concerns out of `CommandCenter.tsx`
  into `useCommandCenter.ts` (mirrors useRuntimeTemplates/useLauncherHotkeys). Render is
  now ~75 LOC of Ark composition; behaviour identical, existing tests green.
- **AA contrast.** Subtitle/empty/placeholder functional text `--color-txt-3` (≈3.9:1) →
  `--color-txt-2` (≈6.4:1).
- **a11y polish.** `Combobox.Input` `aria-label`; visually-hidden `role=status`/`aria-live`
  region announces the async fleet fetch (loading→error); footer `aria-hidden` (out of the
  listbox options tree); `:focus-visible` `--canvas-focus-ring` on input/content/scrim;
  curly apostrophe in the specialist-load error copy.

## Summary

Replaced the always-visible canvas command bar with a keyboard-first **⌘K command center**
(Raycast Minimal, built on the existing canvas token system — fully mono, square corners).
Five deliverables: zero-chrome canvas, Ark command center, agent-first Agents launcher with
four states, additive `runtimeTemplate` threading, and staged `--launcher-*` design tokens.

## Architecture Decisions

- **One Ark Combobox as the single primitive.** `CommandCenter.tsx` is the only place Ark is
  composed and owns `launcher.css` (vanilla CSS via `data-part`/`data-state`). Floating
  positioner anchored flush under the input (`sameWidth`, `gutter: 0`) — seamless because the
  whole theme is `radius: 0`.
- **Pure model split.** `commandModel.ts` holds all row/scope/action logic as deterministic
  functions (no React) → fully unit-testable (four Agents states, harness derivation, filter,
  group). The component layers scope state + the keyboard grammar on top.
- **Renderer-level hotkeys**, not Electron `globalShortcut`: `useLauncherHotkeys` (⌘K toggle
  root, ⌘A → Agents only while closed so it never hijacks select-all, Esc owned by the palette
  to scope propagation away from canvas listeners). Grammar (↵/→/←/⌫) on the input's keydown.
- **Leaf-command dispatcher.** The command center handles scope nav internally and dispatches
  only leaf `LauncherCommand`s out via `onCommand`; `CanvasSurface` binds each to the SAME
  existing handler the deleted bar used (`addCapturedRun`, `resetViewport`, `focusPane`,
  `navigateToRoute`, `cycleTheme`) — zero-chrome regresses nothing.
- **Additive threading.** `runtimeTemplate?` flows through all 8 captured-run hops, persisted on
  the pane ref so detach/restore re-attaches under the same template. Absent → omitted from the
  POST body → NATIVE byte-for-byte.
- **DRY reuse:** `lib/agentPalette.agentRailStyle` for per-row rails (agent colour matches its
  spawned pane); `cycleTheme` lifted into the theme store (shared with Lab's ThemeCycleButton);
  `CAPTURED_RUN_PROVIDERS` relocated to `paneRecords`; `navigateToRoute` exported from
  RouteSwitcher.

## Performance Notes

- Ark UI + zag adds weight to the (already lazy) canvas-route chunk; initial `index` chunk stays
  ~58 kB gz. Fetch is **lazy on first palette open** (`enabled = hasOpened`) so a never-opened
  command center never hits `/v1/runtime-templates` and never blocks a spawn.
- Follow-up option: lazy-load the Ark palette body behind the lightweight hotkey shell to keep
  Ark out of the canvas route's first paint entirely (⌘K must stay instant, so the dispatcher
  must remain eager). Not needed for slice 1.

## Deviations from Spec

- **None functional.** The build contract superseded the spec's RouteSwitcher→Menu pilot (dead)
  and deferred the `→` override config — both honored. Workdir/Settings/Sessions are wired in as
  quiet deferred placeholders (spec allows "wiring without internals").
- Early-checkpoint screenshot was **replaced by Stuart's direct live roadtest** (stronger
  evidence; also satisfies the "spawn from the palette" run/verify).

## Open Items

- The `→` override config (model/effort/vendor/harness eval path) — the NEXT layer; needs the
  `CreateRunRequest` managed-launch field extension.
- Templates recommending `opencode`/`pi` render as **disabled** rows (captured-run flow only
  spawns claude/codex per the backend allowlist) — revisit when those harnesses become spawnable.
- `--launcher-*` tokens are staged in `index.launcher.css` for the little-background-lab upstream
  port (stage-only this slice — Stuart ports upstream himself; no LBL notify/PR).
