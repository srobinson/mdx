# Audioface Studio: Layout and Mobile-Readiness Scout

2026-07-19 · Baseline: main @ `9faf83d9cc2fbe3fbd2c9ee98ecbea687b2e1a13` ("feat: tab the side pane with node, token, and theme editors") · Read-only pass over `apps/studio/src`. All references are file plus symbol or selector.

One correction to the brief up front: of the four named "unmounted legacy components", **TokenEditor and ThemeComposer are mounted**. They are the "Edit Token" and "Surface Feel" tabs of the side pane (`components/sequence/SequenceAudition.tsx` renders both). The truly unmounted set is `AuditionPanel`, `TokensExplorer`, `SignalInspector`, and the hooks `useStudioSession` and `useSelectedToken`.

## 1. Reuse Map

### Inventory

Mounted tree: `index.html` → `main.tsx` → `App.tsx` → `app/StudioApp.tsx` → `SequenceAudition`. Everything else hangs off that one component.

| File | Role | Size | Status |
|---|---|---|---|
| `index.html` | Shell, viewport meta, `#studioRoot` | 14 | live |
| `src/main.tsx` | Mount, imports all three stylesheets | 18 | live |
| `src/App.tsx` | Re-export shim for `StudioApp` | 1 | live |
| `src/app/StudioApp.tsx` | Renders `SequenceAudition` only | 5 | live |
| `src/app/useSequenceAudition.ts` | Surface god hook: flow drafts, selection, playhead, token/theme fan-out (`SequenceAuditionState`) | 247 | live |
| `src/app/useStudioPlayback.ts` | Engine lifecycle, `auditionToken` / `auditionTokenDefinition` / `auditionFlow` / `stopFlow` | 131 | live |
| `src/app/useStudioTheme.ts` | Theme state, `STUDIO_THEME_CONTROLS` | 80 | live |
| `src/app/useTokenEditor.ts` | Token draft state, `TOKEN_EDITOR_MACRO_CONTROLS`, layer edits | 179 | live |
| `src/app/studioTheme.ts` | `initialStudioTheme` snapshot | 14 | live |
| `src/app/useStudioSession.ts` | Legacy session hook; unmounted, but exports the live `THEME_AUDITION_INTERVAL_MS` and `shouldAuditionThemeControl` consumed by `useSequenceAudition` | 132 | mixed |
| `src/app/useSelectedToken.ts` | Selection state, used only by dead `useStudioSession` | 19 | dead |
| `components/sequence/SequenceAudition.tsx` | Surface layout: header, main column, tabbed side pane | 142 | live |
| `components/sequence/SequenceTimeline.tsx` | Ruler, lanes, draggable `EventChip` (pointer events) | 142 | live |
| `components/sequence/SequenceGraph.tsx` | Signal DAG: SVG edges plus absolutely positioned HTML node buttons (`graphPoint`, `edgePath`) | 74 | live |
| `components/sequence/SequenceNodeEditor.tsx` | Side pane "Edit Node" tab | 94 | live |
| `components/sequence/SequenceStepList.tsx` | Step buttons under the graph | 31 | live |
| `components/editor/TokenEditor.tsx` | Side pane "Edit Token" tab: macros, layer shaper, scope viz | 261 | live |
| `components/theme/ThemeComposer.tsx` | Side pane "Surface Feel" tab | 81 | live |
| `components/audition/AuditionPanel.tsx` | Old hero panel, imports `SignalInspector` | 36 | dead |
| `components/inspector/SignalInspector.tsx` | Sound anatomy panel with change highlighting | 247 | dead |
| `components/tokens/TokensExplorer.tsx` | Semantic catalog browser | 89 | dead |
| `styles/studio.css` | Global reset plus the entire OLD `.studio-canvas` layout | 591 | ~85% dead |
| `styles/sequence-audition.css` | All styling for the mounted surface | 149 | live |
| `styles/token-editor.css` | TokenEditor styling (written for the old grid) | 263 | live, stale grid-area |

Heavy lifting already lives in `@audioface/core` (`buildSequenceTimeline`, `buildSequenceGraph`, `updateSequenceStep` with delay clamping via `SEQUENCE_STEP_MAX_DELAY_MS`, `createThemeSnapshot`, fixtures). The studio is a thin view over it, which is exactly right and makes the redesign cheap.

### What survives a mobile-first redesign as-is

- **All of `src/app/`** except the two dead hooks. `useStudioPlayback`, `useStudioTheme`, `useTokenEditor`, `studioTheme` are layout-agnostic. `useSequenceAudition` survives functionally but deserves the grooming noted below.
- **`SequenceTimeline` / `EventChip`**: the drag is already pointer-event based with `setPointerCapture` and `touch-action: none`, so touch dragging works structurally. Needs target sizing and the shift hack fixed, not a rewrite.
- **`SequenceNodeEditor`, `TokenEditor`, `ThemeComposer`**: internals survive; they are already self-contained panels that can be re-hosted in a sheet or rail unchanged except for control-width CSS.
- **`SequenceGraph`**: SVG edge layer scales correctly (`viewBox` plus `vector-effect: non-scaling-stroke`); the HTML node buttons need responsive sizing work.
- **`SequenceStepList`**: fine anywhere.

## 2. Quality Map

### Why the layout breaks (the reported clip)

The side pane does not clip because it is too narrow; it clips because its content refuses to shrink and nothing stops the spill. Chain, all in `styles/sequence-audition.css` unless noted:

1. `.sequence-audition__layout` pins the side pane to `grid-template-columns: minmax(0, 1fr) minmax(280px, 0.38fr)`. The track cannot grow past its fr share, and `.sequence-audition__side` declares `min-width: 0`, so overflow is the only escape.
2. The default tab is Edit Node. `.sequence-audition__side .sequence-node-editor__fields` overrides the fields grid to `1fr 1fr`, and `1fr` means `minmax(auto, 1fr)`: each column floors at its content's intrinsic width. The Token `<select>` in `SequenceNodeEditor` has no `width: 100%` or `min-width: 0` (contrast `.theme-composer__material select`, which sets `width: 100%`), and a `<select>` never shrinks below its widest `<option>`, so the two columns floor at roughly 420 to 480px against a pane of roughly 280 to 340px.
3. `.sequence-node-editor__footer` is worse: a flex row of two badges plus Duplicate, Delete, Reset buttons whose combined min-content is roughly 500px, and flex items default to `min-width: auto`.
4. `.sequence-node-editor` itself has no `min-width: 0`, and the side pane's implicit grid column is `auto`, so the whole editor renders at intrinsic width and spills right through `.sequence-audition`'s visible overflow.
5. `.studio-root` (`styles/studio.css`) centers the `width: min(100%, 1240px)` card with `place-items: center`, so on any viewport at or below about 1300px the card's right edge sits at the viewport edge and the spill exits the screen. Hence "the side pane clips off the right edge".

Point fix, if desktop must limp along before the redesign: `min-width: 0` on `.sequence-node-editor` and `minmax(0, 1fr)` columns (or `width: 100%; min-width: 0` on the fields' controls), plus `flex-wrap: wrap` on the footer. The redesign should make this class of bug impossible by policy: every fr track that hosts form controls is `minmax(0, 1fr)`, every control gets `width: 100%`.

### Mobile readiness audit

- **Viewport meta**: present and correct in `index.html`.
- **Breakpoints**: exactly one live breakpoint, `max-width: 900px` in `sequence-audition.css` (stacks the layout, shrinks lane labels). The 860px and 520px queries in `studio.css` target the dead `.studio-canvas` grid and do nothing for the mounted tree. There is no design under 900px, only a stack.
- **Fixed widths**: `.sequence-timeline__lane` label column 132px (96px under 900px); `.sequence-graph__node` fixed 86px; `.sequence-timeline__event` `max(58px, …)`. On a 390px phone the timeline rail is left with roughly 270px of usable width.
- **Touch targets**: event chips `min-height: 38px`, side tabs roughly 38px, and `.token-editor__scope-layer` is 18px tall. All below the 44px guideline. Range inputs rely on default thumbs.
- **Hover-only affordances**: the event chip `title` attribute (start time plus token id) is unreachable on touch; hover box-shadow cues degrade gracefully and are fine.
- **Timeline drag on touch**: structurally correct. `EventChip.handlePointerDown` uses `setPointerCapture` and the chip sets `touch-action: none`, so pointermove drags work on touch and do not fight page scroll. Two real defects: the `--event-shift` rule flips a chip by `translateX(-100%)` the instant `startRatio` crosses 0.82, so a chip teleports mid-drag under the user's finger; and `msPerPixel` is captured from the rail width at pointerdown, which goes stale if the viewport rotates mid-drag (minor).
- **Playback render loop**: `useSequenceAudition.play` drives the playhead with `setPlayheadMs` inside `requestAnimationFrame`, re-rendering the entire surface every frame during playback. On phones this will contend with the audio engine and drag handling. The playhead should write a CSS custom property through a ref, or live in an isolated subscriber component.
- **Viewport units**: `.studio-root` uses `min-height: 100vh`; on iOS Safari the dynamic toolbar makes this jump. Use `100dvh`.
- **SVG scaling**: edges are fine; the graph canvas is a fixed 148px tall and node buttons at percentage positions with fixed 86px width overlap badly once the canvas is under about 500px wide. The DAG needs a phone treatment (horizontal scroll, vertical relayout, or collapse).
- **Scrolling**: no sticky header, no scroll containment strategy; on phone the whole surface is one long scroll with the play button scrolled away. No `overscroll-behavior` anywhere.

### Duplication and drift

- `assertNever` is declared three times: `components/editor/TokenEditor.tsx`, `components/inspector/SignalInspector.tsx`, `src/app/useTokenEditor.ts`.
- `layerPitch` is declared twice with diverging behavior: `TokenEditor.tsx` falls back to 1200 for unfiltered noise, `SignalInspector.tsx` falls back to 0.
- `useTokenEditor.ts` declares a local `clamp`; `packages/core/src/sequence-editor.ts` has a private `clampNumber`. One exported core helper should own this.
- The 0.22 gain ceiling is a magic number in both `TokenEditor.tsx` (divide) and `useTokenEditor.ts` (multiply). The fun-pivot brainstorm demotes this exact ceiling to a House-personality rule, so it must become one named constant before it moves.
- Palette drift across stylesheets with zero CSS custom properties: cream is `#fffaf1` in `studio.css`/`token-editor.css` but `#fffbf4` in `sequence-audition.css`; the accent yellow is `#f2b83b` in `studio.css` but `#f0b429` in `sequence-audition.css`; `#25221f` and `#e34f30` are hardcoded dozens of times. A mobile-first rewrite without design tokens will re-encode this drift.
- `useSequenceAudition` re-implements the audition throttle pattern that `useStudioSession` already had, because the live surface was built beside the dead one instead of replacing it. Its return type (`SequenceAuditionState`, 24 members) is a god-object handed whole to the tree.

### Dead code and boundary issues

- **Dead styles**: in `styles/studio.css`, the `.studio-canvas` grid (including its `grid-template-areas`), `.studio-primary`, `.studio-kicker`, `.studio-copy`, `.studio-action`, `.studio-error`, `.studio-inspector*`, `.sound-anatomy*`, `.tokens-explorer*`, and both media queries all style the unmounted legacy tree. Only `:root`, `*`, `html`, `body`, `.studio-root`, and the `.theme-composer*` blocks are live. Roughly 500 of 591 lines are dead. `.studio-loading` (in `index.html`) is styled nowhere.
- **Stale grid-areas**: `token-editor.css` `.token-editor { grid-area: editor }` and `studio.css` `.theme-composer { grid-area: theme }` exist for the dead grid and are neutralized by `.sequence-audition__side .token-editor` / `.theme-composer` overrides (`grid-area: auto`) in `sequence-audition.css`. Patch-over-patch.
- **Live exports in a dead module**: `THEME_AUDITION_INTERVAL_MS` and `shouldAuditionThemeControl` live in `useStudioSession.ts` but are consumed by `useSequenceAudition.ts`. The dead hook cannot be deleted until they move.
- **Dead dependency**: `@audioface/stores` is in `apps/studio/package.json` and never imported.
- **Typography split**: `studio.css` `:root` sets Georgia serif globally; `sequence-audition.css` overrides the card to Avenir Next sans. Two design generations coexist in the cascade.

### Grooming recommendation (the five legacy modules)

- **Delete now**: `AuditionPanel`, `TokensExplorer`, `useStudioSession` (after relocating the two throttle exports, e.g. into `useStudioPlayback.ts` or a small `auditionThrottle.ts`), `useSelectedToken`, all dead `studio.css` blocks, and the `@audioface/stores` dependency. Git preserves them; unmounted React code rots silently.
- **`TokensExplorer`'s concept returns** as the library browser in the fun-pivot vision, but its internals (a category-grouped button list over `listAudiofaceTokens`) are trivially rebuildable and the future browser needs search, personalities, and user tokens anyway. Keeping the file buys nothing.
- **`SignalInspector` is the interesting one**: the sound-anatomy visualization maps directly onto the brainstorm's Coherence Report proposal. Still delete it; wire-through against `lastPlayback` no longer exists, and resurrecting it later against the coherence-report design will start from the fingerprint logic in core, not from this DOM. Note the intent in the redesign spec instead.
- **`TokenEditor` and `ThemeComposer` stay**: they are live tabs and their internals survive re-hosting.

## 3. Plan

### Architecture options for mobile-first

**Option A: Stage plus bottom sheet (recommended).**
Phone: full-bleed single column. Sticky compact header (flow select, play, later the personality preset chip). The timeline is the primary stage; the DAG collapses to an expandable strip; the step list follows. Selecting a chip, node, or step opens a bottom sheet hosting the existing three panels (Edit Node, Edit Token, Surface Feel) behind the current segmented tabs, with half and full snap points so the timeline stays visible and audible while tweaking. Desktop at 1024px and up: identical tree, the sheet docks as a right rail (today's side pane rebuilt with `minmax(0, …)` discipline).
Trade-offs: the sheet host is the one new component to build, and its drag handle must not fight chip dragging (distinct `touch-action` zones handle this). In exchange it preserves the surface's core loop, tweak while auditioning, on both form factors, and gives clean future homes: library browser as another sheet or route, randomize and mutate as stage toolbar actions, fuller token editor as growth inside the token sheet.

**Option B: Bottom tab bar shell (Stage, Sounds, Feel).**
Single column per tab, native-app navigation, simplest CSS, no overlay work. But editing moves off-stage, breaking audition-while-tweaking, which is this surface's whole point. Best kept as the eventual outer shell once the library browser lands (Stage tab, Library tab), with Option A's sheet pattern living inside the Stage tab.

**Option C: Progressive-disclosure stacked column.**
Editors expand inline under the selection, accordion style. Cheapest to ship and no new interaction primitives, but selection-jumps cause scroll thrash, the page grows unboundedly as the token editor gains layer add/remove, and desktop degrades to a narrow ribbon. Not recommended beyond a stopgap.

Recommendation: **A now, B's shell later** when the library browser arrives. Both reuse the three existing panels unchanged.

### Decisions needed (Stuart)

1. Approve the delete list (AuditionPanel, TokensExplorer, SignalInspector, useStudioSession, useSelectedToken, dead studio.css blocks, `@audioface/stores` dep).
2. Design tokens: introduce CSS custom properties (palette, radius, border, shadow, spacing) as step one of the redesign, resolving the cream and yellow drift. Recommended yes; a mobile rewrite without tokens re-encodes the drift.
3. Phone chrome: full-bleed app shell on phone, parchment card retained on desktop only. Recommended; the 1.5px border and 10px hard shadow card reads as desktop skeuomorphism at 390px.
4. Sheet implementation: hand-rolled (dvh, snap points, `touch-action` zoning) versus a headless primitive (Ark UI is already available in this workspace). Hand-rolled keeps the app dependency-light; Ark buys accessibility for free. Recommend deciding before step 3.
5. Whether the desktop point-fix (spill hotfix) ships ahead of the redesign or the redesign is the fix.

### Ordered steps

1. **Groom** (pure deletion and moves, no behavior change): delete the five dead modules and dead styles; relocate `THEME_AUDITION_INTERVAL_MS` and `shouldAuditionThemeControl`; consolidate `assertNever` and `layerPitch` into one shared module; name the 0.22 gain-ceiling constant; drop `@audioface/stores`; remove stale `grid-area` declarations and their overrides.
2. **Design tokens**: one `tokens.css` (or `:root` block) with the palette, borders, shadows, type stacks; sweep the three stylesheets onto it; unify cream and yellow.
3. **App shell**: mobile-first rewrite of `.studio-root` and `.sequence-audition` (100dvh, full-bleed under 768px, sticky header); rebuild the desktop rail with `minmax(0, 1fr)` discipline and `width: 100%` on all form controls, which permanently kills the clip bug.
4. **Bottom sheet host**: new component wrapping the existing three panels plus the tab strip; rail on desktop, sheet on phone.
5. **Stage polish**: 44px minimum touch targets (chips, tabs, scope layers); replace the `--event-shift` 0.82 teleport with clamped positioning inside the rail; phone treatment for the DAG; playhead isolation (CSS var via ref instead of per-frame state); replace the hover `title` with the sheet's own readout.
6. **Verify** per gates below at each step boundary.

### Tests and gates

- Repo gate: `pnpm run check` (tsc -b, node --test, validate) after every step; `pnpm --filter @audioface/studio build` for the app itself. The studio has no unit tests today; the pure helpers extracted in step 1 (throttle, layerPitch, clamp) are the natural first `node --test` targets and should land with the groom.
- Browser gate per step 3 onward: load at 390x844 and 1280x800 (agent-browser or CDP device emulation); assert `document.scrollingElement.scrollWidth <= window.innerWidth` on both, with each side tab active (the current bug reproduces only on the Edit Node tab, so all three must be checked); exercise a chip drag via dispatched pointer events on the touch profile and assert the step's `delayMs` changed.
- Definition of done for the redesign spec that consumes this scout: no horizontal overflow at any width from 320px up, all interactive targets at or above 44px, timeline drag verified under touch emulation, playback smooth on a throttled CPU profile.
