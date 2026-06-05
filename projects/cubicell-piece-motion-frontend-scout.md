# Editor Piece Motion — Frontend Scout

Frontend ownership brief for the Editor Piece Motion workspace. Scout only,
no repo writes. Base commit `bfcacba` (`docs: reconcile camera docs`).
Sources: `LESSONS.md`, `STUDIO.ANIMATION.md` §"Piece motion and reuse
(2026-07-15)", the two BottomDock screenshots (2026-07-16), and the live
seams (`BottomDock`, `SnapshotControls`, `StripControls`, `AssemblyControls`,
`CameraTrackControls`, `panels.css`, `src/components/ui`, `src/thumbnail`).

Author: `cubicell:general:8:1.1`.

> **Contract resolutions (2026-07-15, round 2 with backend `memories:general:8:2.1`).**
> Four shared-contract deltas resolved; they refine §4, §6, and §10.
>
> 1. **Score time — concurrent + one offset.** Evaluator stays concurrent
>    (`getScoreDurationMs` = max across tracks; no per-track phase model). Add a
>    single `StateTransitionTrack.startMs` (default 0); piece duration =
>    `max(arrivalEnd, startMs + transitionsSum)`. The default seed and the
>    Build-in preset set `startMs = arrival duration` so a piece assembles
>    **then** transitions. Rationale: pure-concurrent plays assembly and the
>    first morph simultaneously (muddy) — a live-gate risk for any multi-state
>    piece. Frontend: transport is one duration, no separate arrival region on
>    the playhead, flow copy reads "plays the piece motion" (supersedes the
>    "arrival then morphs" wording in §4).
> 2. **State lifecycle — selection = active State, not compare.** Per
>    STUDIO.PROJECT: canvas is a scratch copy of the selected State, **Update**
>    commits, a modified badge shows drift. Tile selection establishes the
>    active State; **Compare** (Saved↔Live `morphScrub`) demotes to a secondary
>    scrub. "Restore" folds into selection. Revised tile anatomy:
>    active / modified badge / Update / Compare (secondary) / Delete
>    (supersedes the §6 tile states and the §5 chip-verb list).
> 3. **Sequence identity — v1 invariant, Editor only.** Every structure State
>    appears exactly once in `stateIds` order; PieceScore transitions connect
>    adjacent States. This makes the fused strip literal (roster == sequence).
>    The **Studio** animation copy keeps repeat/subset/re-sequence (composition,
>    via `PieceSnapshot` + cues). Editor loop/return motifs use the Loop
>    transport for a full A→…→A cycle; literal mid-sequence repeats are Studio.
> 4. **Presets & revisions.** Build-in / Wavefront are typed piece preset ops,
>    Build-in first; pose-revision pool deferred to PieceSnapshot work. **Update
>    mints a new pose reference** (thumbnail re-renders) while an unchanged State
>    keeps its reference (WeakMap cache hit) — identity changes iff pose changes.
>
> **Consensus (round 3, all accepted).** (1) `startMs` is an authored
> track offset; sampling before it holds the first State; Build-in seeds it
> from assembly build duration. Frontend homes it as **one track-scoped
> "Start delay" ScrubField at the strip's leading edge** (arrival/first-tile
> boundary), always visible when the sequence exists — not a per-gap field —
> so a later cadence edit cannot strand an invisible offset. (2) Active State
> is **session state** (`activeStateId`): selecting a tile restores it into the
> working canvas; a memoized selector compares active-State pose vs
> `workingPose` for the modified badge; reload falls back to the poster State;
> Update is a no-op when equal, else installs a new `Pose` (identity iff
> content). (3) Structure owner validation enforces one keyframe per State in
> `stateIds` order; capture appends both atomically, reorder moves both via one
> structure op, last-State deletion stays blocked; repair centralized per owner.
> (5) The dead Editor `TransportTarget` path is deleted and camera authoring
> unmounted; camera domain/commands are retained for Studio, with no
> speculative Editor command left behind. Ownership split: **backend** owns
> domain, evaluation, persistence, session contracts; **frontend** owns the
> shell, thumbnails, shared inspector, accessibility, tests, and the flag.
> The combined repo plan is being drafted by `memories:general:8:2.1` and will
> supersede this scout for execution; this doc remains the frontend direction
> of record.
>
> **Sequencing.** Backend relocation does **not** block frontend: the inspector
> extraction, `StateThumbnail` primitive, and strip shell build now against a
> thin adapter behind the default-off flag, then rebind to the structure
> `PieceScore` after the domain slice. This softens the §"Key blockers" hard
> gate to a bind-order dependency.

---

## 1. Direction verdict: endorsed, with three collapses

The brief asks me to validate, not merely accept, "one Editor Piece Motion
workspace with piece-scoped transport, thumbnail state sequence, contextual
Build in or transition inspector, and Studio-owned camera authoring."

**I endorse the direction.** It is the correct bounded-context cut: the
**Editor authors the Piece** (its states + its motion), the **Studio authors
the Stage** (placement, camera, cues, multilane). The 2026-07-15 decision that
relocates the `StateTransitionTrack` onto the structure as a `PieceScore`
makes this boundary real in the domain, and the current `BottomDock`
straddles it in three ways that the workspace should eliminate. Validation
surfaces **three collapses**, each of which removes a surface rather than
adding one:

**Collapse 1 — Kill the `Piece motion | Scene strip` transport toggle.**
Today `BottomDock.tsx:24-30` offers a `Segmented` target
(`assembly` | `strip`) because assembly lives on the working structure and the
state-transition strip lives on a separate `AnimationAsset`
(`getActiveTransportDurationMs`, `transportSelectors.ts:15-22`, reads two
different score sources). Once `PieceScore = AssemblyTrack + StateTransitionTrack`
both live on the structure, there is exactly **one** thing the Editor can play:
the piece's motion. The toggle is an artifact of the split the decision
removes. The Editor gets **one piece timeline**, one duration source.
(Aligns with LESSONS #89: do not pose an either/or when the alternatives are
two views over one model.)

**Collapse 2 — Fuse "Saved states" + "Scene strip frames" into one thumbnail
state sequence.** `SnapshotControls` renders the state pool as a chip row
(`SnapshotControls.tsx:65-87`) and `StripControls` renders the *same* states
again as strip frames (`StripControls.tsx:176-255`). These are two text
representations of one flat state pool. The workspace shows **one** sequence:
ortho thumbnails of the piece's states in authored order. `src/thumbnail` is
built for exactly this and currently has **zero UI consumers** (see §2). The
strip *is* the state library, viewed in order. (LESSONS #89 again; and #90:
a workflow surface cannot ship as a row of domain controls.)

**Collapse 3 — Evict the camera track from the piece workspace.** Camera is
**stage-owned and singular** (STUDIO.ANIMATION.md §"One lane per asset, one
camera lane": "never a per-asset lane"). Today `CameraTrackControls` is
mounted *inside* `StripControls.tsx:129`, so authoring a piece and authoring
the stage camera happen in the same surface. The Editor Piece Motion
workspace must **not** contain camera authoring; it moves to the future Studio
stage surface. In this slice we lift `CameraTrackControls` out and park it
behind the Studio boundary (§5).

Net: the workspace is **smaller** than today's dock — one timeline, one
thumbnail strip, one contextual inspector, no target toggle, no camera lane.

---

## 2. Reuse Map (symbol-anchored)

### Reuse as-is (shared primitives, no change)
- `Button`, `Label`, `ScrubField`, `Segmented`, `Switch`
  (`src/components/ui/index.ts`). Every control in the workspace is one of
  these. `ScrubField` (`scrub-field/ScrubField.tsx`) already does
  scrub-drag + precise-entry with `onScrubStart/onScrubEnd` history batching —
  the exact "direct manipulation + precise entry" the design principle asks
  for (STUDIO.ANIMATION.md §"Keep controls contextual"). Do not build new
  value editors.
- `EditorCommandProvider` / `useEditorCommandDispatch` /
  `useCameraSnapshotReader` (`editorCommandContext.ts`) — the command bridge.
  All edits stay `dispatch(createDocumentEditCommand(op))`.
- History batching: `beginHistoryBatch` / `endHistoryBatch` (used in every
  multi-op flow: `SnapshotControls.tsx:32-38`, `StripControls.tsx:76-83`).
- `motionOptions.ts` — `orderModeOptions`, `orderModeValue`,
  `resolveOrderModeChange`, `easingOptions`, `curveOptions`. The shared
  vocabulary for Order/Easing/Curve segmented controls. Reuse verbatim.
- `stateCapture.ts` — `createStateCapture(workbench)`,
  `createAnimationAppend(...)`. Capture plumbing.
- `transportRateMin/Max/Step`, the transport command creators
  (`editor/commands`) — the transport row is unchanged mechanics.

### Reuse the panel geometry (CSS, no new tokens)
- `panels.css` classes: `.cc-dock`, `.cc-dock-body`, `.cc-dock-transport`,
  `.cc-dock-playhead`, `.cc-dock-time`, `.cc-dock-assembly` (the flex-wrap
  control row used by AssemblyControls, StripControls transition editor, and
  CameraSegmentEditor alike), `.cc-dock-section-header`,
  `.cc-dock-section-copy`, `.cc-dock-section-action`, `.cc-scrub-field` +
  `.cc-scrub-field-label`. All token-driven (`--cc-space-*`, `--cc-panel-*`).
  New markup should consume these, per LESSONS #22/#40 (no bespoke button
  visuals, establish tokens first).

### Reuse the shared inspector (the plan's load-bearing reuse)
- The **morph inspector is one component used at two levels** (plan
  §"Editor authors the piece, Studio authors the stage"). It already exists as
  `TransitionControls` (`StripControls.tsx:257-362`): Duration, Scene switch,
  Cubes (morph class), Order, Stagger, Easing, Steps, over `MorphSettings` /
  `ClassMotion`. **Extract it** to a shared `MorphInspector` so the Editor
  (piece default) and the Studio (animation's own copy) render the identical
  component (§5). `MotionSegment` (`StripControls.tsx:364-388`) is its private
  helper and travels with it.

### Reuse the thumbnail engine (built, currently orphaned)
- `src/thumbnail/*` is a complete ortho-thumbnail pipeline with **no `.tsx`
  consumer anywhere** (grep for `resolveAssetThumbnail|OrthographicThumbnail|
  StateThumbnail|thumbnailCache` in `*.tsx` returns nothing). Contract:
  - `createStateThumbnailCache(...)` → `StateThumbnailCache`
    (`thumbnailCache.ts:20`).
  - `cache.get(pose): Promise<OrthographicThumbnailSet>` where
    `OrthographicThumbnailSet = Record<'x'|'y'|'z', Blob>`
    (`thumbnailCache.ts:4,12`). Poses are `WeakMap`-cached, so repeated calls
    for a stable `State.pose` are free.
  - `resolveAssetPosterState(workbench, asset)` (`assetPoster.ts:20`) already
    knows structure-poster vs animation-first-keyframe resolution.
  - This is a **new frontend surface with backend already done**: a small
    async `StateThumbnail` component (blob → `URL.createObjectURL`, revoke on
    unmount, `<img>` with an `axis` prop, skeleton while pending) is the only
    new render primitive the slice needs. It belongs under
    `src/components/ui/thumbnail` per LESSONS #41.

### Do NOT reuse (replace)
- The chip-row shape in `SnapshotControls` `StateChip`
  (`SnapshotControls.tsx:125-224`) — six buttons per state
  (Compare/Rename/Update/Restore/Add to strip/Delete). This is a generated
  control row, the exact anti-pattern of LESSONS #58 and #90. Its *verbs* are
  reused; its *layout* is replaced by a thumbnail tile with hover/selected
  affordances and overflow-menu secondary actions (§4, §6).

---

## 3. Quality Map

Rated against Cubicell's own bars (LESSONS: slick/minimal by default #25;
tokens-first #22; no domain-control rows #90; discoverable first-use #90).

| Surface | Symbol | Bar | Verdict |
|---|---|---|---|
| Transport row | `BottomDock.tsx:51-126` | Good | **Keep.** Clean, token-driven, wraps as a unit (`.cc-dock-transport` `flex 1 1 320px`). Only change: drop the target `Segmented`. |
| Target toggle | `BottomDock.tsx:24-30,55-64` | Simplicity | **Remove** (Collapse 1). |
| Saved-states chips | `SnapshotControls.tsx:125-224` | #58/#90 | **Fails.** Row of 6 domain buttons per state, no thumbnail, no primary action, rename hidden behind double-click *and* a Rename button (redundant). Replace with thumbnail tiles. |
| Strip frames | `StripControls.tsx:176-255` | #89 | **Fails as separate surface.** Duplicates the state pool as text with Earlier/Later/Remove. Fold into the one thumbnail sequence (reorder = drag; remove = tile action). |
| Transition inspector | `StripControls.tsx:257-362` | Good | **Keep + extract.** Semantic controls (Duration, Scene switch, class-scoped Order/Stagger/Easing/Steps) over `.cc-dock-assembly`. This is the model to generalize, not replace. |
| Assembly controls | `AssemblyControls.tsx:42-215` | Good | **Keep.** Order/Arrive/Step/Curve/Easing/Steps/Exit, all `ScrubField`+`Segmented`+`Switch`. Becomes the arrival ("Build in") face of the contextual inspector. |
| Camera controls | `CameraTrackControls.tsx` | Boundary | **Correct component, wrong context.** Well-built (keyframe list, segment editor, orbit actions). Move whole to Studio (Collapse 3), unchanged. |
| Morph comparison | `SnapshotControls.tsx:88-120` | Good | **Keep** as the per-tile compare scrub (Saved↔Live). Already a clean two-anchor scrub. |
| First-use hint | `stateWorkflowHint` `:226`, `stripWorkflowHint` `:390` | #90 | **Keep the pattern, merge the copy.** With one strip there is one hint ladder, not two. |

Overall: the *controls* are high quality; the *information architecture* is
not. Two surfaces (Saved states, Scene strip) present one state pool, a target
toggle exposes a domain split that is being removed, and camera authoring sits
inside the piece surface. The workspace is an IA consolidation, not a
control rewrite.

---

## 4. Proposed panel hierarchy & first-use flow

The workspace stays the **bottom dock** (canvas dominant; timeline expands
from the bottom — STUDIO.ANIMATION.md §"Keep the canvas dominant"). It is
piece-scoped: it authors whatever structure is on the working bench.

```
BottomDock  (Editor Piece Motion workspace)
├─ Transport row              [Play] [Stop] [Loop] ══playhead══ 0.0s/2.4s  Speed×
│                              (no target toggle; one piece duration)
├─ State sequence  ────────────────────────────────────────────────────────
│   ▢1 Base   ▸ ▢2 Open   ▸ ▢3 Bloom        [+ Capture]
│   └ thumbnails in authored order; ▸ = transition gap (selectable);
│     tile = select-to-compare; drag to reorder; tile ⋯ = Update/Restore/Delete
├─ Contextual inspector  (one slot, driven by selection)
│   • gap selected      → MorphInspector   (Duration, Scene switch, Cubes,
│                                            Order, Stagger, Easing, Steps)
│   • arrival selected  → AssemblyInspector (Build in: Order, Arrive, Step,
│                                            Curve, Easing, Steps, Exit)
│   • nothing selected  → first-use hint ladder
└─ [Close motion]
```

Camera, placement, cues, multilane: **not here** — Studio.

### First-use flow (the shortest successful sequence, made visible — LESSONS #90)
1. Empty piece → strip shows a single ghost tile + primary **Capture current**
   and the hint "Capture the current scene before you change it."
2. One state → hint "Edit the scene, then capture again to build motion."
3. Edit scene, **Capture** → second tile appears; the **gap between them auto-
   selects**, opening the MorphInspector so the user lands on the thing they
   just created (not an empty editor).
4. **Play** plays the piece motion (arrival, then state morphs).
5. Selecting a tile scrubs Saved↔Live compare; selecting a gap edits its morph.
6. "Build in" is a one-click **preset** on the arrival inspector (plan step 8;
   Build-in / Wavefront) so a fresh piece looks good without hand-tuning.

This is the plan's first user story minus the recursion/placement steps, which
are Studio.

---

## 5. Component extraction / removal map

| Action | Symbol | Destination |
|---|---|---|
| **Extract** shared morph inspector | `TransitionControls` + `MotionSegment` (`StripControls.tsx:257-388`) | `src/panels/MorphInspector.tsx` (or `src/panels/motion/`); consumed by Editor piece default **and** Studio animation copy (plan requires one shared component). |
| **New** async thumbnail primitive | — | `src/components/ui/thumbnail/StateThumbnail.tsx` (blob→objectURL, revoke, skeleton, `axis` prop). Wraps `StateThumbnailCache.get`. |
| **New** state-sequence strip | replaces `SnapshotControls` list + `StripControls` frames | `src/panels/PieceStateStrip.tsx` — thumbnail tiles + gap selectors + capture + reorder-drag. |
| **New** contextual inspector switch | replaces `BottomDock.tsx:128-132` target branch | Drives MorphInspector (gap) vs AssemblyInspector (arrival) off selection, not off a transport target. |
| **Rename/keep** assembly inspector | `AssemblyControls` (`AssemblyControls.tsx`) | Keep as-is; it is the arrival/"Build in" face. Add the preset action. |
| **Move** camera authoring | `CameraTrackControls` (`CameraTrackControls.tsx`) + `cameraCapture.ts` | Out of `StripControls`; park under the future Studio stage surface. Unmount from the Editor dock. Do **not** delete (LESSONS #33: preserve the command bridge). |
| **Remove** target toggle | `transportTargetOptions`, `createTransportTargetCommand` usage in dock (`BottomDock.tsx:24-30,55-64`) | Delete from the Editor dock. Keep the transport command surface for Studio's future multi-lane needs. |
| **Retire** duplicate hint fns | `stateWorkflowHint` `:226`, `stripWorkflowHint` `:390` | Merge into one piece-scoped hint ladder. |

**700-line watch (LESSONS #81/#87):** `StripControls.tsx` is 398 lines and is
being split (inspector extracted, frames folded into the strip). Do the split
in the same branch, `wc -l` before PR. `StructureSection.tsx` (558) is
untouched by this work.

---

## 6. Complete interaction states

**State tile**
- *default*: thumbnail + name; subtle border.
- *hover*: reveal ⋯ overflow (Update/Restore/Delete) and a drag handle; border
  `--cc-label-fg` (mirrors `.cc-slice-cell[data-hovered]`).
- *selected (comparing)*: solid accent border; opens the Saved↔Live compare
  scrub (`morphScrub`); `aria-pressed=true`.
- *renaming*: inline text input (reuse `.cc-snapshot-rename`,
  `SnapshotControls.tsx:154-165`); Enter commits, Escape cancels, blur commits.
- *dragging*: lifted; drop targets are inter-tile gaps; commits a
  `move-keyframe`-equivalent reorder.
- *poster*: first tile carries an implicit poster marker (structure poster
  state).

**Gap (transition) marker** between tiles
- *default*: thin connector `▸`.
- *hover*: thickens.
- *selected*: solid; opens MorphInspector; only one gap or tile selected at a
  time (single contextual slot).

**Capture button**: idle → (optional) pending while thumbnail renders → new
tile animates in; on first capture it is the primary `variant="solid"` action.

**Transport**: Play/Pause disabled when `durationMs===0`
(`BottomDock.tsx:66-67`); Stop disabled when `timeMs===null`; Loop is
`aria-pressed`.

**Empty / edge**: empty piece → single ghost tile + primary Capture. One state
→ Capture again prompt, no gaps yet. Deleting the selected tile → clear the
contextual slot (do not leave a dead inspector; mirror
`StructureSection.tsx:216-224`'s stale-selection drop).

**Thumbnail failure**: `cache.get` rejects → tile falls back to the text name
chip (never blocks authoring).

---

## 7. Responsive behavior

- Dock body already `flex-wrap` with `min-height:140px`
  (`.cc-dock-body`, `panels.css:334-347`). Keep.
- Transport row wraps as one unit (`flex:1 1 320px`), playhead grows to fill
  (`.cc-dock-playhead flex:1`). Keep.
- **State strip** is the new wide axis: it must scroll **inside its own**
  `overflow-x:auto` container, never widen the dock (LESSONS #34: floating/
  segmented controls size to content, never a full-width bar unless asked).
  Thumbnails fixed ~48–64px; the strip is a horizontal scroller with the
  selected tile kept in view (reuse the `scrollIntoView({block:'nearest'})`
  pattern from `StructureSection.tsx:198-208`).
- Contextual inspector uses `.cc-dock-assembly` flex-wrap; controls reflow to
  new rows on narrow docks, as AssemblyControls does today.
- Dock is draggable/dockable already via `StudioShell` + `DockablePanel`; the
  workspace inherits that, no new layout logic.

---

## 8. Accessibility

- Reuse existing landmark pattern: `<section aria-labelledby=...>` with a
  `Label id=...` heading (`SnapshotControls.tsx:42-48`,
  `CameraTrackControls.tsx:120-125`).
- State strip is a **listbox** semantics: tiles are options
  (`role="option"` / `aria-selected`), the strip `role="listbox"
  aria-label="Piece states"`. Gap markers are buttons with
  `aria-label="Edit transition N: A to B"` (today's pattern,
  `StripControls.tsx:196-204`).
- Every icon-only control keeps an `aria-label` (thumbnail tile:
  `aria-label="Compare {name} with live scene"`, matching
  `SnapshotControls.tsx:168`).
- Selected tile/gap must be reachable and operable by keyboard: arrow-key
  roving tabindex across the listbox; Enter selects; the contextual inspector
  is standard focusable controls.
- Focus-visible: inherit `--cc-outline-width`/`--cc-outline-offset` (already on
  `.cc-panel-tab:focus-visible`).
- Reduced motion: thumbnail tile-in and any strip animation must honor OS
  reduced-motion **at the interface boundary**, and must **not** alter the
  authored piece motion or its preview (LESSONS #92 — accessibility policy
  stays at the app/interface layer, never in track data).
- Color independence: selection is a border/accent, not opacity or thumbnail
  content change (LESSONS #43/#47 — selection chrome is editor UI with its own
  accent token).

---

## 9. Frontend tests & gates

- **Component tests** (Vitest + Testing Library, the repo's pattern):
  - Capture appends a tile; the new gap auto-selects and the MorphInspector
    mounts (proves first-use flow, not just wiring — LESSONS #90).
  - Selecting a gap renders MorphInspector; selecting arrival renders
    AssemblyInspector; deleting the selected tile clears the slot.
  - `StateThumbnail` resolves a blob to an `<img>`, shows skeleton while
    pending, revokes the object URL on unmount (assert no leak), falls back to
    text on reject.
  - MorphInspector renders identically from an Editor piece default and a
    Studio animation copy (one-component proof).
- **Discoverability gate**: the empty and one-state hints render the shortest
  successful next action (assert copy + primary button presence).
- **Live hands-on gate (mandatory, not deferrable)**: this workspace changes
  canvas-adjacent authoring; per LESSONS #61/#84/#85 and the
  `live-ux-gate-before-merge` memory, Stuart must drive it in a dev server
  before merge. Ship behind a config flag, default off, until that pass. Do
  **not** trust green component tests as sufficient (seam layer #65 was green
  through three reviews and broke live).
- **Build gate**: verify with `npx tsc -b --force` (what `pnpm build` runs),
  **not** root `tsc --noEmit`, which checks nothing (LESSONS #87). Gate on
  exit code, not piped grep (LESSONS #60).
- **Size gate**: `wc -l` every touched panel file before PR; split
  `StripControls` in-branch (LESSONS #81).

---

## 10. Exact backend contracts I need

The frontend cannot land until the domain provides these. All are the
`PieceScore` relocation the 2026-07-15 decision approved (version bump +
reset; no migration — LESSONS #66, `no-migrations-single-user`).

1. **`PieceScore` on the structure.** `StructureAsset` (`workbench.ts:33-41`)
   gains a `PieceScore = { assembly: AssemblyTrack; transitions?:
   StateTransitionTrack }` (at most one of each), replacing today's
   `score: AssemblyScore`. The Editor authors both tracks against the working
   structure. Give me: a selector `getPieceScore(workbench): PieceScore` and
   its `AssemblyTrack` + `StateTransitionTrack` accessors, mirroring today's
   `getWorkingScore` / `getStateTransitionTrack`.

2. **Piece-scoped transport duration.** One `getPieceDurationMs(workbench)`
   that sums arrival + state-transition motion, replacing the branch in
   `getActiveTransportDurationMs` (`transportSelectors.ts:15-22`). The Editor
   dock reads exactly one duration; no `TransportTarget`.

3. **State-transition edit ops addressed to the structure**, not to an
   `animationAssetId`. Today `patch-transition` / `move-keyframe` /
   `remove-keyframe` carry `animationAssetId` (`StripControls.tsx:94-101,
   213-245`). I need the same ops keyed by the structure (or working piece),
   since the strip now lives on the structure. Preserve the namespace rule:
   a structure `PieceScore` addresses that structure's state ids
   (STUDIO.ANIMATION.md §"Piece motion lives on the structure").

4. **Build-in / Wavefront presets.** A `seedPieceMotion(kind)` op that
   populates the `StateTransitionTrack` (and arrival cadence) from a named
   preset (plan step 8: "seeded from a preset so the piece looks good without
   hand-tuning"). I render it as a one-click action on the arrival inspector.

5. **Thumbnail render port already satisfied.** `StateThumbnailCache`
   (`thumbnailCache.ts`) is complete; I only need a store-provided cache
   instance (created once with the render backend) exposed to the panel layer,
   plus confirmation that `State.pose` identity is stable across renders so the
   `WeakMap` cache hits.

Out of scope for this workspace (Studio owns them): camera lane authoring,
Placement, Cue, multilane, `PieceSnapshot`, pose-revision pool, and the
three-way staleness merge (STUDIO.ANIMATION.md §"Reuse", §"Staleness").
`CameraTrackControls` moves there intact.

---

## Key blockers

- **Backend `PieceScore` relocation (contracts 1–4) must land first.** The
  frontend IA is blocked on the structure owning the state-transition track;
  until then the strip has no single home to bind to.
- **Live UX gate is mandatory and flag-gated.** Ship default-off until Stuart
  drives it (memory `live-ux-gate-before-merge`).

Everything else (thumbnail primitive, inspector extraction, strip, IA
collapses) is frontend-ownable and ready to spec into slices once the
contracts are agreed.
