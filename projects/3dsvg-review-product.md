# 3dsvg: Product and UX Review, and Comparison to Cubicell

Lens: product framing, interaction model, distribution, head to head.
Subject: `/Users/alphab/Dev/LLM/DEV/3dsvg` at `424b26e` (MIT, Renato Costa / Blueberry).
Baseline: `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`.
Read only. No files in either repo were modified.

Scale context, because it frames everything below: 3dsvg is 7,581 lines of TS/TSX
across 42 files. Cubicell is 62,943 lines. These are not peers. 3dsvg is a
single screen product with one object in it. Cubicell is a studio.

---

## What 3dsvg Is

**The promise.** "The easiest way to turn SVGs into interactive 3D." One object,
extruded, lit, animated, and then taken away as a PNG, a video, a mesh, or a
React component. The metadata in `packages/web/src/app/layout.tsx` sells the
absence of friction as hard as the capability: "100% free, no account or
subscription needed."

**Who it is for.** Two audiences share one screen, and the product never asks
which one you are.

1. A designer or marketer who wants a spinning 3D logo for a slide, a post, or a
   hero image. They arrive, tweak, hit the shutter, and leave with a file.
2. A React developer who wants `<SVG3D>` on their own site and is using the
   editor as a visual prop builder for a component they will install from npm.

The second audience is the reason the monorepo exists. The editor is not the
product so much as the configurator and the demo for the package.

**Cold open to first artifact.** This is the strongest thing in the whole
product. Landing on the site puts a floating, extruded, indigo Space Invader on a
purple backdrop, already animating. It is seeded, not empty:
`packages/web/src/components/pixel-editor.tsx` `createDefaultGrid` writes a
hardcoded 16 by 16 bitmap into the initial state, `page.tsx` opens on the `draw`
tab, and `animate` defaults to `float`. The left toolbar is open on that same
pixel grid, so the first thing a user sees is a finished looking object next to
the tool that made it. Time to first artifact is one click on the shutter.

**Information architecture.** Three edges around a full bleed canvas.

- Left: a four icon vertical toolbar plus one expanding content panel
  (`input-panel.tsx` `InputPanel`). The four tools are Draw, Text, SVG Code,
  Upload File. Each produces an SVG string. That is the whole input model.
- Right: a settings accordion behind a gear
  (`controls-panel.tsx` `ControlsPanel`), sections Object, Background, Material,
  Texture, Animation, Interaction, Lighting.
- Bottom: a camera. Not an export bar, a camera. `export-bar.tsx` `ShutterButton`
  is a physical shutter, `ViewfinderOverlay` masks the canvas to the chosen
  aspect ratio, and the Image / Video toggle sits under it like a phone.

The mental model handed to the user is therefore: *the canvas is a photo studio,
the object is the subject, and you are holding the camera.* That metaphor is
carried consistently, including a 12 frame iOS style filmstrip trimmer
(`video-trimmer.tsx` `VideoTrimmer`) and a "Photo Preview" dialog. It is the best
product decision in the codebase and it costs almost nothing structurally.

**Distribution.** The differentiator. `embed-dialog.tsx` `EmbedDialog` renders
numbered install steps and a copyable `<SVG3D>` snippet built by `generateProps`,
which emits only props that differ from defaults. `packages/engine/package.json`
publishes granular subpath exports and ships `llms.txt` inside the tarball so an
agent installing the package gets the full API reference. The README claim is
"what you see in the editor is exactly what you get with the embed." That claim
is not currently true; see Looked At And Rejected.

**What is missing, and it is a lot.** No persistence of any kind. Every value in
`page.tsx` is a `useState`, there is no URL state, no localStorage, no project
file. Refresh and the work is gone. No undo. No keyboard shortcuts anywhere. One
object only, no scene, no selection, no composition. Animation is seven hardcoded
sine functions in `packages/engine/src/controls.tsx` `LoopAnimation` with one
speed multiplier and a reverse flag. There is no timeline and no concept of time
beyond "loop forever."

There is also one unfinished edge worth naming, because it is the most
interesting file in the repo: `packages/web/src/lib/svg-rasterize.ts`
`rasterizeSvgToFilledSvg` is complete, solves the limitation the README itself
warns about (stroke only SVGs such as Lucide icons will not extrude), and is
imported by nothing. They built the fix and never wired it up.

---

## Worth Leveraging (ranked, highest value first)

| Idea | 3dsvg owner (path + symbol) | Gap it fills in cubicell | Cubicell landing site (path + symbol) | Effort |
|---|---|---|---|---|
| **Record exactly N loops, auto stop.** Pick 1x, 2x, or 3x before recording; the recorder computes the cycle length and stops itself, so the file loops seamlessly with no trimming. | `packages/web/src/components/export-bar.tsx` `getCycleDuration`, `ExportModal.startRecording(autoStopMs)` | `R` records the live canvas until you press `R` again. Every loop needs manual trimming in another tool, and the loop point is never exact. Cubicell is strictly better positioned here than 3dsvg is: it already knows the authored duration, so the capture can be frame exact rather than inferred from a sine period. | `src/export/streamRecorder.ts` `createRecordingController`, armed through `src/interaction/commands/capture.commands.ts` `registerCaptureCommands`, duration from `src/state/transportSelectors.ts` `getPieceTransportDurationMs` | S |
| **Occupancy from an image.** Threshold any SVG or raster down to a gridSize by gridSize boolean field, then build geometry from the filled cells. | `packages/web/src/lib/svg-rasterize.ts` `rasterizeSvgToFilledSvg`; inverse tracer in `pixel-editor.tsx` `pixelsToSvg` | Cubicell has no import path from external artwork into lattice occupancy. Everything is placed by hand or by grid composition. Two of CUBICELL.md's own stress tests ("Spell `CUBICELL` from cubes", "Collapse a cube grid into a flat icon") are exactly this operation. A logo dropped on a slice becomes a filled layer. Take the idea, not the file: 3dsvg never wired theirs up, so it is unproven code. | `src/domain/sliceMap.ts` and `src/domain/structureOperations.ts` for the occupancy write, surfaced from `src/components/grid-composer/GridComposer.tsx` | M |
| **A format chooser that recommends instead of enumerating.** Two formats presented as cards with plain language ("Looks like the editor", "Geometry only, opens in any slicer"), one marked Recommended, the niche formats folded behind an "Other formats" disclosure. | `packages/web/src/components/download-dialog.tsx` `PRIMARY_FORMATS`, `SECONDARY_FORMATS`, `FormatCard` | `EXPORT.md` correctly enumerates fifteen candidate output formats. That table is engineering truth and would be a hostile picker. When the deterministic exporter lands, this is the shape that keeps it usable: PNG sequence is the master, WebM is the convenience output, everything else is disclosed. | A new export dialog fed by `PROJECT.EXPORT.md`'s `ExportJob`; nearest existing home is the dock beside `src/capabilities/recording/RecordingIndicator.tsx` | M |
| **Preview cheap, commit expensive.** The shutter renders a 720px preview into a dialog; the full resolution render only happens when the user presses Download. | `packages/web/src/components/export-bar.tsx` `handleImageCapture` versus `handleImageDownload` | Cubicell has no still exporter in production at all, and `EXPORT.md` notes the offscreen precedent already exists. The missing piece is the product step, not the renderer. Preview then commit is what makes a resolution independent exporter feel instant instead of feeling like a render queue. | `src/thumbnail/thumbnailRenderer.ts` for the offscreen render, promoted out of `src/control/canvasStillCapture.ts` (currently development only) | M |
| **Viewfinder: choose the frame before capture, not the crop after.** A mask dims everything outside the target aspect while you compose, so the aspect decision is made against the live scene. | `packages/web/src/components/export-bar.tsx` `ViewfinderOverlay` | `EXPORT.md` names aspect policy as an unresolved product decision and correctly says "Dimensions alone cannot choose the artistically correct rule." A viewfinder dissolves the question: the user reframes the camera inside the target rectangle rather than picking contain, fill, or reframe blind. | A chrome layer sibling to `src/scene/AxisHintChrome.tsx`, framing math from `src/view/interactionFraming.ts` | M |
| **Delayed loader over batched work.** Geometry is extruded in batches that yield to the main thread and report numeric progress; the UI suppresses the spinner for 800ms so short operations never flash. | `packages/engine/src/scene.tsx` `useExtrudedGeometry`; `packages/web/src/components/svg-to-3d-canvas.tsx` `handleLoadingChange` | `src/app/startupIndicator.ts` `setStartupIndicatorPhase` handles cold start well, but in session heavy work (large grid rebuild, project hydration, asset decode) has no equivalent, so the app either stalls silently or would flash. | `src/shared/taskYield.ts` already exists for the yielding half; the progress and suppression half belongs beside `src/scene/renderScheduler.ts` | S |
| **Seed the first run with something that does something.** The editor opens with a drawn object already floating, so the first interaction is a change rather than a creation. | `packages/web/src/components/pixel-editor.tsx` `createDefaultGrid` | Cubicell opens on `1 x 1 x 1` with `activeStateId: null` and a detached transport, so there is one cube and nothing for Play to advance through. The cubicell version is not a mascot, it is a seeded score: one cube and one captured second State, so Play immediately demonstrates what the product is for. | `src/config/cubicellConfig.ts` `initialWorkbenchGridPreset`, `src/state/cubicellState.ts` `createInitialWorkbench` and `createInitialEditorSession` | S |
| **Serialize by diffing against defaults.** The embed snippet emits only props that differ from the component defaults, which is why it stays short enough for a human to read and paste. | `packages/web/src/components/embed-dialog.tsx` `generateProps` | `EXPORT.md` already proposes a scene data module, a player module, and a standalone HTML export. The transferable technique is the diff: a full cubicell project snapshot is unreadable, a snapshot expressed as deviations from defaults is reviewable and diffable. Note the trap in the next section: the diff must run against the *player's* defaults, from one shared table. | `src/domain/project.ts` plus a snapshot serializer, consumed by the player boundary `EXPORT.md` describes | L |

---

## Cubicell Already Does This Better

**Durability.** 3dsvg has none. Cubicell has an IndexedDB commit path with an
outbox, ordered queue, recovery, per record codecs, and forward rebase
(`src/persistence/indexedDbCommit.ts`, `src/persistence/orderedCommitQueue.ts`,
`src/state/projectDurability.ts`). 3dsvg loses everything on refresh and does not
even keep state in the URL. There is nothing to learn here except what not to do.

**Time.** 3dsvg's "animation" is a switch statement over seven trigonometric
expressions (`packages/engine/src/controls.tsx` `LoopAnimation`). No keyframes,
no per part motion, no sequencing. Cubicell has authored States, transitions, a
score clock, morph evaluation, and camera track possession
(`src/domain/score.ts`, `src/evaluation/scoreAt.ts`,
`src/camera/cameraTrackAuthority.ts`, `src/panels/motion/MotionInspector.tsx`).
The gap is categorical.

**One vocabulary for every actor.** 3dsvg has zero keyboard shortcuts. Every
action is a mouse gesture on a panel, which also means no scripting surface and
no LLM surface. Cubicell routes keyboard, keypad, panels, transport, and capture
through one registry (`src/interaction/commands/registry.ts`,
`src/editor/keyboard/keymap.ts`) with hold promotion and repeat, and exposes it
read only over MCP. `INTERACTIVE.md`'s founding observation, that a human and an
LLM are the same kind of actor, has no counterpart in 3dsvg.

**Selection as a product surface.** 3dsvg has one object and therefore no
selection model. Cubicell treats selection as a first class subject with queries,
verbs, builders, and a dedicated panel (`src/domain/selectionQuery.ts`,
`src/domain/selectionVerbs.ts`, `src/panels/SelectorPanel.tsx`).

**Panel architecture.** 3dsvg's `page.tsx` juggles a `topPanel` state variable
between `"toolbar"` and `"settings"` purely to swap `z-index` between two
overlapping floating panels. That is a workaround for panels that were never
given a layout. Cubicell has real docking with persisted layout, drag between
edges, resize, and a clean canvas toggle that deliberately preserves the
reconciliation slot so the WebGL context never tears down
(`src/app/StudioShell.tsx` `StudioShell`, `src/app/DockablePanel.tsx`).

**Accessibility.** Cubicell requires accessible names, roles, and focus, wires
`role="tabpanel"` to its tab groups, and puts `aria-live` on the recording
indicator. 3dsvg sets `userScalable: false` and `maximumScale: 1` in
`packages/web/src/app/layout.tsx`, which blocks pinch zoom for low vision users,
and reaches for native `<select>` and unlabeled `<input type="color">` throughout
`controls-panel.tsx`.

**Thinking about output.** `EXPORT.md` separates world extent, camera framing,
CSS size, drawing buffer, and export dimensions, and is honest that the current
recorder conflates them. 3dsvg conflates them too but does not know it: PNG
export resizes the live canvas in place and re renders
(`svg-to-3d-canvas.tsx` `DownloadCapture`), and video records whatever size the
browser window happens to be. Cubicell's unbuilt export is better specified than
3dsvg's shipped one.

**Where the comparison misleads.** These products do not overlap much. 3dsvg
extrudes a single 2D path into a lit 3D object and hands you a file or a
component. Cubicell composes a lattice of cubes over time and shows it through
pose. 3dsvg has no scene, no time, no selection, no persistence, and does not
want them. Cubicell has no single object shortcut, no material library, and no
distribution story, and mostly should not want the first two.

The comparison is only fair in three places, and those are exactly the three
places worth mining: **capture** (both record a live canvas at 60fps with
MediaRecorder and both know it is the wrong long term answer), **first run**
(both must convert a cold visitor into someone who has made something), and
**delivery** (3dsvg has shipped the embed that cubicell's own `EXPORT.md` has
only specified). Everywhere else, borrowing from 3dsvg would mean borrowing down.

---

## Looked At And Rejected

| Rejected | Why it is wrong shaped for cubicell |
|---|---|
| **"What you see is what you embed", as implemented.** | The claim is false in the shipped code. `embed-dialog.tsx` `generateProps` diffs each prop against the *web editor's* defaults, but the snippet is consumed by the engine, whose defaults differ. `defaultLightSettings` in `svg-to-3d-canvas.tsx` is `{2, 2, 4}`; `defaultProps.lightPosition` in `packages/engine/src/types.ts` is `[5, 8, 5]`. A user who never opens the Lighting section gets a snippet with no `lightPosition`, so the embed is lit from a different direction than the editor they just used. The same bug drops `background` (the editor hardcodes `#0a0a0a`), drops the coloured backdrop plane entirely (it is a web only child inside `SVGTo3DCanvas`, not a prop), and drops `scrollZoom` (editor hardcodes it on, engine default is off). The idea is right and worth building; this two tables of defaults shape guarantees drift. If cubicell ships a snapshot, one serializer and one defaults table must be shared by editor and player. |
| **Duplicating the motion model in the recorder.** | `export-bar.tsx` `getCycleDuration` hardcodes the periods that `packages/engine/src/controls.tsx` `LoopAnimation` implements. Change a coefficient in the engine and the recorder silently records the wrong length, with no test and no type to catch it. Cubicell must take the auto stop idea while reading duration from the score, never from a second copy of the timing. |
| **Blob and data URLs leaking into exported code.** | `controls-panel.tsx` `TexturePresetPicker` passes the output of `preset.generate()` (a 512px `canvas.toDataURL`) directly as the texture, and uploaded textures become `URL.createObjectURL` blobs. `EmbedDialog` then writes whichever one is active into the snippet the user copies. The blob URL is dead the moment the tab closes; the data URL is a few hundred KB of base64 pasted into someone's source file. Asset identity has to be resolved before a snapshot can reference it. Cubicell already has the right machinery in `src/persistence/payloadStore.ts` and `src/domain/payloadAsset.ts`. Do not copy the shortcut. |
| **Visual choices behind a text dropdown.** | `DESIGN.md` specified a grid of visual tiles for the ten material presets. What shipped in `controls-panel.tsx` is a native `<select>` listing the words "Chrome", "Clay", "Holo". In a visual tool that forces the user to try each one blind, one at a time. Cubicell's `src/components/ui/segmented/Segmented.tsx` and `src/components/ui/light-direction-picker/LightDirectionPicker.tsx` are already the better idiom. Do not regress toward dropdowns for choices with a look. |
| **The single open right side accordion as an IA.** | `ControlsPanel`'s `toggleSection` closes the previously open section, so comparing Material against Lighting means losing one of them. `DESIGN.md`'s own user flow diagram specifies the opposite behaviour ("New section expands, others stay as-is"), so this is drift, not a decision. Cubicell's tabbed rail plus dockable, resizable, reorderable panels is strictly more capable; swapping it for an accordion would be a downgrade dressed as simplification. |
| **`userScalable: false`.** | `packages/web/src/app/layout.tsx` disables pinch zoom to stop the page reflowing under a full bleed WebGL canvas. It also stops a low vision user zooming the UI. Cubicell's accessibility contract in `PRODUCT.md` forbids this trade. Solve canvas gesture capture at the canvas, where `SmoothControls` in `packages/engine/src/controls.tsx` already does most of the work with pointer capture and non passive wheel and touch handlers, rather than at the document. |
| **Window level drag and drop.** | `page.tsx` attaches `dragenter`/`drop` to `window` with a `dragCounterRef` and shows one full screen overlay. Correct for a product with exactly one drop target. In cubicell a dropped asset must resolve to a cell, a face, or a slice, so the drop target is spatial and the overlay is the wrong affordance. |
| **In app feedback widget as shipped.** | `packages/web/src/components/freedback/index.tsx` `collectMetadata` calls `https://ipapi.co/json/` on open to attach the user's city and country to feedback. Sensible product instinct, wrong default: a creative tool should not make a third party geolocation request as a side effect of someone clicking a chat bubble. Revisit the idea at launch, not the implementation. |

---

## Open Questions For Stuart

1. **Does cubicell want a fast lane?** 3dsvg's entire advantage is that a
   stranger produces a shareable artifact in about ten seconds with no account
   and no file. Cubicell's cold open is honest but slow: one cube, an inspector
   reading "Select a cube on the canvas", and no score to play. Is "visitor
   leaves with a video in under
   a minute" a goal, or is cubicell deliberately a tool you commit to? The answer
   decides whether the seeded first run row above is worth building.

2. **Is the embed a product or a demo?** For 3dsvg the npm package is the
   product and the editor is its configurator. `EXPORT.md` proposes the mirror
   image: a player module extracted from the editor. If a `@cubicell/player`
   ever ships, it changes the renderer boundary requirement from "nice
   architecture" to "the load bearing contract", and it changes who cubicell is
   for. Worth deciding before the exporter work starts, because both want the
   same immutable project snapshot.

3. **Occupancy from an image: which direction?** Rasterizing a logo into filled
   cells is directly useful and matches two stated stress tests. But CUBICELL.md
   also says "the confinement is the product" and warns against Blender lite. Is
   importing external artwork into the lattice a legitimate creation path, or is
   it the first crack in the confinement?

4. **Auto stop capture: score pass or wall clock?** Cubicell knows the exact
   authored duration, which is strictly better information than 3dsvg's inferred
   sine period. But `MediaRecorder` on a live canvas cannot promise frame exact
   boundaries regardless. Is a "record one score pass" button worth shipping
   against the current recorder, or does it only make sense once the deterministic
   `ExportJob` exists and can drive a fixed clock?

5. **Where does capture live in the IA?** Today it is a keypress (`R`) and a
   status readout. 3dsvg made capture the largest, most physical control on the
   screen, and that single decision defines what the product feels like it is
   for. Cubicell has three edges already spoken for (rail, inspector, motion
   dock). If capture becomes a real surface with format, dimensions, and aspect,
   which edge loses, or does it become a modal?

6. **Was the DESIGN.md drift deliberate?** 3dsvg's `DESIGN.md` is a careful 25KB
   spec with wireframes, motion timings, and open questions. The shipped
   `controls-panel.tsx` contradicts it in at least three places (single open
   sections, `<select>` instead of material tiles, and the file was never renamed
   to `settings-panel.tsx`). Combined with the fully written but never imported
   `svg-rasterize.ts`, the pattern reads as design documents that stop being
   consulted once code starts. Cubicell's docs are far larger and far more
   load bearing. Worth confirming there is a mechanism that keeps them true,
   because this is what the failure mode looks like from the outside.

---

*Read only review. No branches, no commits, no installs. This file is the only
artifact created.*
