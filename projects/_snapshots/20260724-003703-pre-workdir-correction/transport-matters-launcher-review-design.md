---
title: PR #144 ⌘K Launcher — Design-Critical Review (Web Interface Guidelines + brief focus)
type: review
tags: [frontend, design-review, transport-matters, launcher, cmd-k, accessibility, design-tokens, pr-144]
summary: Read-only WIG + Raycast-Minimal review of feat/cmd-k-launcher @ 4f8f174 — 1 Major (subtitle AA contrast), 6 Minors, no Blockers; token discipline + contain:paint gotcha pass.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

# PR #144 — ⌘K Command Center: Design-Critical Review

**Branch/commit:** `feat/cmd-k-launcher @ 4f8f174` (this worktree, verified pristine before review).
**Scope:** diff only — `www/src/session-canvas/launcher/*`, `index.launcher.css`, `launcher.css`, `canvas.css`.
**Lens:** Vercel Web Interface Guidelines + brief focus areas 1–5. Correctness/backend logic and the deferred `→` override are out of scope (Codex owns).

## Verdict

**No Blockers. 1 Major, 6 Minors, several non-blocking observations.** The design-critical axes the brief called out — token discipline, the `contain: paint` shadow/ring gotcha, Native-always presentation, and full keyboard grammar — all **pass**. The Major and Minors are accessibility polish plus one typography nit; all fixes are launcher-local.

---

## Major

**M1 — Subtitle/empty/placeholder text fails WCAG AA contrast.** `launcher.css:185-187` (`.launcher__row-subtitle`), also `launcher.css:206-207` (`.launcher__empty`) and `launcher.css:69-71` (`::placeholder`).
`--color-txt-3` (`#707070`) on the panel `--color-surface` (`#0e0e0e`) ≈ **3.9:1**, below the AA **4.5:1** floor for normal-size text (subtitle is 11.5px, placeholder 13.5px — both well under the 18.66px large-text threshold). The subtitle carries functional metadata (recommended model · effort · vendor), so it is not decorative.
**Fix:** raise subtitles to `--color-txt-2` (`#949494` ≈ **6.4:1**), or increase size/weight. Launcher-local; no token change needed.

---

## Minor

**m1 — Combobox input has no explicit accessible name.** `CommandCenter.tsx:200-204`. `Combobox.Input` ships a placeholder but no `aria-label` / `Combobox.Label`, so the accessible name falls back to the placeholder (fragile, and empties to nothing once the user types). WIG: form controls need `<label>`/`aria-label`. **Fix:** add `aria-label="Search agents and commands"` to `Combobox.Input` (or a visually-hidden `Combobox.Label`).

**m2 — `outline: none` without a `:focus-visible` replacement.** `launcher.css:66` (`.launcher__input`), `launcher.css:97` (`.launcher__content`). The always-focused search field shows no focus ring; position is carried by the row highlight (acceptable Raycast pattern), but WIG flags `outline:none` without replacement. **Fix:** add a `:focus-visible` treatment on `.launcher__control` using the existing `--canvas-focus-ring` convention for strict AA.

**m3 — No `aria-live` for async fleet-state transitions or empty results.** `CommandCenter.tsx:209-211` (`No matches`) and the status rows in `commandModel.ts:130-168`. loading→populated/error changes and the empty state are only discoverable by arrowing into a disabled option. WIG: async updates need `aria-live="polite"`. **Fix:** wrap the status/empty message in a `role="status"`/`aria-live="polite"` region.

**m4 — Straight apostrophe in copy.** `commandModel.ts:143` — `"Couldn't load specialists"` uses `'`; WIG wants a curly `'` (`"Couldn't"`).

**m5 — `<footer>` rendered inside the listbox.** `CommandCenter.tsx:224-227`. The keyboard-hint `<footer>` is the last child of `Combobox.Content` (role=listbox), polluting the options collection for screen readers. **Fix:** move it outside `Combobox.Content`, or `aria-hidden="true"` it (the hints are redundant with actual key behavior).

**m6 — Scrim button relies on the UA default focus outline.** `launcher.css:16-25` (`.launcher__scrim`). The full-screen close button is keyboard-focusable but does not adopt `--canvas-focus-ring` like the rest of the system. Low stakes (near-invisible scrim) but inconsistent. **Fix:** apply `--canvas-focus-ring` on `:focus-visible`, or document the intentional default.

---

## Observations (non-blocking, no action required)

- **Micro-geometry literals inlined** rather than tokenized: control gap `10px` (`launcher.css:41`), `calc(100vw - 32px)` (`:31`), rail inset `6px` (`:143`), brand tracking `0.1em` (`:227`), hint offsets `right:18px`/`bottom:16px` (`:236-237`). Acceptable — these are one-off layout values; crucially **zero hardcoded colors/radii/shadows** exist in `launcher.css`.
- **Command titles use sentence case** ("Reset view", "Cycle theme") vs WIG's Title Case default. Internally consistent and defensible for the quiet Raycast aesthetic — flagging only for awareness.
- **Square corners via omission**: `launcher.css` sets no `border-radius`, inheriting `0`. Correct (border-radius is not inherited, and `--radius-*` are all `0`), just not an explicit `var(--radius-*)` reference.
- **Possible dead `.canvas-command-bar` CSS** now that `CanvasCommandBar.tsx` is deleted (`canvas.css:63+`). Pre-existing styles + hygiene/correctness — out of this review's lane (Codex), noted only for completeness.

---

## Strong passes (evidence)

**Focus 1 — Token discipline (clean).** Zero hardcoded colors/radii/shadows in `launcher.css`; every value goes through `var()`. All new tokens are `--launcher-*`, live only in `index.launcher.css`, are grouped with section comments, and pair `--X`/`--X-rgb` for alpha composites (`--launcher-scrim`/`-scrim-rgb`, `--launcher-panel-shadow`/`--launcher-shadow-rgb`, `--launcher-kbd-bg`/`-kbd-bg-rgb`, `--launcher-footer-bg`/`-footer-bg-rgb`). Values are STATIC (no theme-axis refs) and the `:root` block is documented as a verbatim LBL upstream port. All ~15 reused refs (`--color-surface`, `--color-edge-strong/subtle/edge`, `--color-txt/-2/-3`, `--color-label`, `--color-accent`, `--accent-rgb`, `--color-sage`, `--color-amber`, `--color-well`, `--transition`, `--font-mono`, `--color-agent-rail-*`) resolve to real `index.css` definitions — no broken `var()`.

**Focus 2 — Theming correctness (clean).** Square (radius 0); JetBrains Mono via `--font-mono`; dark-only scrim (`rgb(4 4 4 / 0.58)`) over an opaque `--color-surface` panel composes over any scene. **`contain: paint` gotcha avoided:** `Combobox.Content` is portaled to `<body>`; the non-portaled search bar's host `.canvas-route-shell` sets no `transform`/`filter`/`will-change`/`contain`, so it is not a fixed-positioning containing block and its `overflow:hidden` does not clip the launcher; the only `contain: layout paint` (`.canvas-pane-window`) and the `will-change: transform` (`.canvas-world`) are sibling subtrees, not ancestors. Panel shadow/ring are not clipped.

**Focus 3 — a11y core (strong).** Ark Combobox parts preserved → role=combobox/listbox/option, `aria-expanded`, `aria-activedescendant` intact. Focus save/restore on open/close via `restoreFocusRef` (`CommandCenter.tsx:48-74`); `autoFocus` justified (user-invoked palette); scrim has `aria-label`; decorative `⌘` prompt and the first-run hint are `aria-hidden`; `@media (prefers-reduced-motion: reduce)` disables all animations/transitions (`launcher.css:294-303`).

**Focus 4 — Four states + Native-always (clean).** Native rows render first off the synchronous model and the specialist fetch never gates a spawn (`useRuntimeTemplates` only fills specialist rows). loading → `"Loading specialists…"` (correct ellipsis) skeleton rows; error → status row + actionable `"Retry"` (includes next step), native still present; empty → `"Install a fleet to add specialists"` + native; populated → recommended-target subtitles. Zero-chrome resting (command bar deleted); first-run hint is faint/fading (`0→.85→.85→0`), JS unmount at 6.5s clears the 6s fade, `localStorage` seen-flag so it never returns, `pointer-events:none`, `aria-hidden`.

**Focus 5 — Raycast Minimal craft (strong).** Clear 3-tier hierarchy (uppercase tracked group labels → titles → subtitles); dense rows (40px) / input (52px); focused-row rail reuses the `--color-agent-rail-*` ramp via `agentPalette` (`--agent-rail`/`--agent-rail-rgb`) with a `scaleY` rail + warm accent wash; agent color is shared between launcher row and spawned pane. (Subtitle legibility is the M1 contrast miss.)

**Keyboard grammar (complete).** ⌘K toggle (`useLauncherHotkeys`), ⌘A → Agents (closed-only, won't hijack select-all), Esc close, ↑/↓ nav (Ark), ↵ run/enter-scope, → enter scope (caret-at-end guard), ←/⌫ back to root.
