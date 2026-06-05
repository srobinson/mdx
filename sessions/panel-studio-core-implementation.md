---
title: Panel Studio Core (SPEC B slice 2) — identity header + section 01 THEMES
type: sessions
tags: [frontend, little-background-lab, spec-b, theme-studio, panel]
summary: Wired the SPEC A registry/SPEC C scene seam into ThemePanelContext, built the pinned identity header and section 01 THEMES (material chips, card actions, import/export), with happy-dom unit tests.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Summary

SPEC B slice 2 of 3 on branch `panel-studio-core` (off `main@91ebc61`). Implements the
theme studio's headline surface against the peer-approved binding spec
`NOTES/specs/spec-b-panel-studio.md`:

1. Extended `ThemePanelContext` with the SPEC A panel API (`saveDraft`,
   `duplicateTheme`, `renameTheme`, `deleteTheme`, `exportTheme`, `importTheme`,
   `accentBand`) and migrated the scene surface to zipped `{ scene, metadata }`
   pairs (`SceneEntry`), dropping the split `sceneMetadata` field. Host wiring in
   `src/main.ts mountPanel` delegates each action to the registry then re-applies.
2. `src/theme/panel/identity-header.ts` — pinned, theme-tab-only header: active
   name, community author line, dirty indicator, Save. Save is source-driven:
   curated active reveals an inline name field and forks; user/community saves in
   place. Enter commits, Esc cancels.
3. `src/theme/panel/material-chip.ts` — honest mini-pane derived entirely from the
   theme's corner/border/veil/accent over the SPEC C scene swatch (veiled toward
   `--color-canvas` via `color-mix`), accent marker via `accentCss`, glass hint,
   `aria-hidden`, neutral-gradient fallback when the scene is unregistered.
4. `src/theme/panel/sections/themes.ts` — section 01 THEMES: cards grouped
   curated / yours / community under sub-kickers, full-snapshot select, inline
   rename, duplicate (fork path), two-step delete confirm-arm, empty "yours"
   teaching copy, and inline import/export with per-cause error rendering.
5. CSS in `src/styles.css` (existing tokens only); removed the now-dead
   `.preset-card*` / `.theme-custom-note` rules the material chip replaces.
6. `src/theme/panel/panel-studio.test.ts` — 8 happy-dom units.

Gate: `pnpm test` 34 passed (26 pre-existing untouched + 8 new); `pnpm build`
green (JS 20.9 KB gzip, well under the 200 KB budget).

## Architecture Decisions

- **Scene surface migrated to zipped pairs, not kept split.** The landed SPEC A/C
  integration exposed `ctx.scenes` (flat) + `ctx.sceneMetadata` (separate); the
  binding spec sec. 1 and the orchestrator both specify
  `scenes: Array<{ scene, metadata }>`. Migrated to the zipped shape (single
  scenes surface, more DRY) and updated the one other consumer, `sections/scene.ts`,
  mechanically (field-access rename only — no behavior change, regression gate
  preserved). No existing test pinned the old shape.
- **Card-action visibility and the header fork branch key off `entry.mutable`.**
  The registry tags curated entries `mutable:false`, user/community `mutable:true`,
  so actions render exactly for local themes and the header forks exactly for
  curated, with no source re-derivation.
- **Save/fork routes through one call.** `ctx.saveDraft(name?)`; the registry owns
  the fork-vs-in-place branch. The header only decides whether to prompt (curated)
  or call `saveDraft()` bare (user).
- **`escapeHtml` added to `panel/primitives.ts`** and shared by the header and
  themes section (user-entered names/authors), rather than duplicated.
- **happy-dom via per-file pragma** (`// @vitest-environment happy-dom`) keeps the
  26 pre-existing data tests in the default node env, untouched.

## Performance Notes

Build JS 66.10 KB raw / 20.90 KB gzip; CSS 19.27 KB / 3.98 KB gzip. No runtime
perf work in this slice. Card actions reveal via opacity (kept in tab order for
keyboard/focus-within); chip/reveal transitions sit behind
`@media (prefers-reduced-motion: no-preference)`.

## Deviations from Spec

- **None on the deliverable contract.** The spec's literal `ctx.scenes` zipped shape
  is implemented (see above); the host wiring matches sec. 1.
- The `accentBand` member is wired now though its consumer (custom OKLCH slider,
  section 03) is slice 3 — deliberate per the orchestrator's deliverable (1).

## Fix Round (orchestrator review, commit `6f875a8`)

Three findings, all fixed with failing-before/passing-after tests where feasible:

1. **HIGH — live header refresh.** I had *documented* the slider-scrub-doesn't-refresh-header
   gap as an open item; the reviewer correctly called it a bug to fix. Added
   `updateIdentityHeader(host, ctx)` (targeted re-render of just `.theme-identity`)
   and wired `main.ts change()` to call it on the `rerender=false` path. A clean
   theme edited via a slider now surfaces modified + Save immediately. Lesson
   reinforced: a deliverable's edge is met by code, not a session note.
2. **HIGH — markup injection via imported ids/names.** ThemeIds are only
   string-validated, so an imported theme's quoted/bracketed id or name broke
   attributes. Added `escapeAttr` (composed on `escapeHtml`) and applied it to every
   id/name that reaches markup; replaced the string-built `[data-rename-form="…"]`
   selector with `closest(".theme-card")` traversal (no id in a selector).
3. **MEDIUM — CSS house rule.** styles.css was already >700 lines; adding to it
   violated the refactor-first rule. Moved the studio block to
   `src/theme/panel/panel.css` (imported after styles.css), reverted styles.css to
   its original 860 lines, and tokenized the flagged px/alpha into panel-local vars
   derived from existing tokens (`--chip-size: calc(var(--canvas-pane-padding) * 3)`,
   `--ring-accent`, `--ring-error`).

Gate after fixes: `pnpm test` 36 passed; `pnpm build` green.

## Open Items

- **Full reduced-motion matrix is slice 3.** Implemented the
  `prefers-reduced-motion` media query; the additional `sim.reducedMotion` DOM
  coupling (no DOM hook exists yet) is deferred per the orchestrator's out-of-scope
  list.
- **`accentBand`** is wired but its consumer (custom OKLCH slider, section 03) is slice 3.
