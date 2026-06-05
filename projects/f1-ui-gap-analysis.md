# F1 UI Gap Analysis: current main vs signed-off mockup

Sources: current build screenshot `localhost_5173_ (48).png`, signed-off mockup `claude.ai_code_artifact_d60f1e9d-3d8c-47bf-b332-5a8f18f95d56.png`, and current code on `main` at `333c3980e83a652313436a4cb85ea060079db280`. PR #91 is merged at this head.

## Summary

Current count: **11 done / 3 partial / 9 open**. G3 and G6 are CLOSED and count as done. G22 is DEFERRED and counts as open.

| # | Gap | Status | Current owner and evidence |
|---|---|---|---|
| G1 | Contextual right rail inspector | DONE | `src/panels/Inspector.tsx::Inspector`, `src/panels/motion/MotionFocusProvider.tsx::MotionFocusProvider` |
| G2 | First class transition cards | DONE | `src/panels/motion/PieceStateStrip.tsx::PieceStateStrip` |
| G3 | Piece absent or flat on first load | CLOSED | `src/app/ConnectedCubeScene.tsx::ConnectedCubeScene`, `src/scene/CubeScene.tsx::CubeScene` |
| G4 | Cube empty state as third inspector mode | DONE, merged into G1 | `src/panels/Inspector.tsx::Inspector` |
| G5 | Floating dock card and collapse chrome | CLOSED | `src/panels/BottomDock.tsx::BottomDock`, `src/panels/panels.css::.cc-dock-card` |
| G6 | Thumbnail renderer disposal race | CLOSED, counts as DONE | `src/components/ui/thumbnail/thumbnailService.tsx::ThumbnailServiceProvider` |
| G7 | Ticked timeline, playhead, time, and speed pill | CLOSED | `src/panels/motion/PieceMotionPanel.tsx::TransportRow`, `src/panels/panels.css::.cc-dock-playhead` |
| G8 | World X axis line across motion canvas | CLOSED | `src/app/App.tsx::App`, `src/scene/WorldAxesChrome.tsx::WorldAxesChrome` |
| G9 | MODE AUTO/CUT control | CLOSED | `src/panels/motion/MorphInspector.tsx::MorphInspector`, `src/domain/morphSettings.ts::MorphSettings` |
| G10 | BUILD IN card | DONE | `src/panels/motion/PieceStateStrip.tsx::PieceStateStrip`, `src/panels/motion/MotionInspector.tsx::ArrivalInspector` |
| G11 | State toolbar moved into inspector | DONE, merged into G1 | `src/panels/motion/MotionInspector.tsx::StateInspector` |
| G12 | Modified state affordance | DONE as Update action | `src/panels/motion/PieceStateStrip.tsx::PieceStateStrip`, `src/panels/motion/MotionInspector.tsx::StateInspector` |
| G13 | POLARITY control in dock | CLOSED | `src/panels/SceneSection.tsx::SceneSection` |
| G14 | Close motion replaced by collapse | DONE | `src/panels/BottomDock.tsx::BottomDock` |
| G15 | View pad clipped by dock | DONE | `src/app/FloatingKeypad.tsx::FloatingKeypad`, `src/app/studio-shell.css::.studio-dock` |
| G16 | CUBES labels and order | PARKED → TX | `src/panels/motion/MorphInspector.tsx::morphClassLabels` |
| G17 | ORDER behavior | PARKED → TX | `src/panels/motion/MorphInspector.tsx::MorphInspector`, `src/domain/assemblyOrder.ts::generateAssemblyOrder` |
| G18 | EASING behavior | PARKED → TX | `src/panels/motion/MorphInspector.tsx::MorphInspector`, `src/evaluation/scoreAt.ts::easingFor` |
| G19 | Start delay units | PARKED → TX | `src/panels/motion/PieceStateStrip.tsx::PieceStateStrip`, `src/panels/motion/MotionInspector.tsx::ArrivalInspector` |
| G20 | Left rail form | CLOSED | `src/panels/LeftRail.tsx::LeftRail` |
| G21 | Perspective wheel zoom update loop | DONE | `src/pose/projectionMatch.ts::hasMatchedPerspectiveFraming`, `src/camera/cameraProjectionSwap.ts::applyPerspectiveProjection` |
| G22 | Stage plan preparation cadence | DEFERRED | `src/transport/useStagedScene.ts::useStagedScene`, `src/evaluation/sceneTransition.ts::sampleSceneTransition` |
| G23 | Editor ink contrast and new cube inheritance | DONE | `src/domain/neighbors.ts::placeCubesAt`, `src/app/useSceneOperations.ts::placeCubeAtSlot` |

## (a) Information architecture

**G1. Right rail contextual inspector; dock retains the filmstrip and transport. DONE.**

`Inspector` now presents one body at a time for State, transition, Build in, or cube properties. `InspectorTabs` swaps cube tabs for the focused motion title. `MotionFocusProvider` owns ephemeral focus and the last selection precedence. `PieceMotionPanel` contains transport and the filmstrip only.

Shipped in #91: `src/panels/Inspector.tsx::Inspector`, `src/panels/Inspector.tsx::InspectorTabs`, `src/panels/motion/MotionFocusProvider.tsx::MotionFocusProvider`, `src/panels/motion/MotionInspector.tsx::StateInspector`, `src/panels/motion/MotionInspector.tsx::TransitionInspector`.

**G4. Cube empty state as the third inspector mode. DONE, merged into G1.**

Cube, face, and edge controls remain in the same right rail. With no selection, `Inspector` renders the canvas selection prompt.

Shipped in #91: `src/panels/Inspector.tsx::Inspector`.

**G11. State toolbar moved into the inspector. DONE, merged into G1.**

Move Prev/Next, Update, Compare, New from selected, Rename, and Delete now live in `StateInspector`.

Shipped in #91: `src/panels/motion/MotionInspector.tsx::StateInspector`.

Current control homes:

| Control | Current home |
|---|---|
| Rename, Compare, New from selected, Delete, Update | `src/panels/motion/MotionInspector.tsx::StateInspector` |
| Move Prev/Next | `src/panels/motion/MotionInspector.tsx::StateInspector` |
| Morph comparison slider | `src/panels/motion/MotionInspector.tsx::StateInspector` |
| Duration, Scene switch, Cubes, Order, Stagger, Easing, Steps | `src/panels/motion/MotionInspector.tsx::TransitionInspector` |
| Build in arrival controls and preset | `src/panels/motion/MotionInspector.tsx::ArrivalInspector` |
| Cube properties | `src/panels/Inspector.tsx::Inspector` |
| Play, Stop, Loop, scrubber, speed | `src/panels/motion/PieceMotionPanel.tsx::TransportRow` |
| BUILD IN, State, transition, Snapshot cards | `src/panels/motion/PieceStateStrip.tsx::PieceStateStrip` |

## (b) Canvas render state

**G3. Piece absent or flat on first load. CLOSED.**

The reported screenshot did not establish a missing render path. The cube scene remains bound through `ConnectedCubeScene` and `CubeScene`. Stuart closed this as default view legibility, with editor color contrast tracked by G23.

**G23. Editor edge and face contrast, plus new cube inheritance. DONE.**

Shipped in #93. Editor-only edge/face OKLab contrast via `edgeLightnessDelta`=0.12 on `workbenchScenePolarities` only, applied at sync when `partKind==='edge'` (sign taken from resolved lightness so both polarities and non-theme colors read; thumbnail/preview/export byte-identical). New-cube style inheritance copies face color, edge color, edge thickness, and layerMode per part id from the selected source cube via `inheritCubePartStyle`/`mapCube*`, with `placeCubesAt` taking an optional `sourceCubeId`; reveal keeps its own style, first-seed wins, no-selection falls back to defaults.

Owners: `src/domain/neighbors.ts::placeCubesAt`, `src/domain/cube.ts::inheritCubePartStyle`, `src/scene/instancedPartMeshCore.ts::syncInstancedPartMesh`, `src/theme/scenePolarity.ts::workbenchScenePolarities`.

## (c) Bottom dock chrome and structure

**G5. Dock container. CLOSED.**

The dock is an inset, rounded card with border, blur, shadow, and a top collapse grip. The signed-off PIECE MOTION title and BOTTOM DOCK pill were deliberately dropped (Stuart, 2026-07-17): the card and collapse chrome are sufficient, the labels add no value.

Shipped in #91: `src/panels/BottomDock.tsx::BottomDock`, `src/panels/panels.css::.cc-dock-card`, `src/panels/panels.css::.cc-dock-collapse`.

**G6. State card thumbnails. CLOSED.**

PR #91 replaced eager renderer creation with an idle deferred lazy backend in `ThumbnailServiceProvider` and added Strict Mode coverage. The original disposal race was development only and is not reachable through current production unmount and remount paths. No further patch is needed.

Production smoke on `main@333c398`: `pnpm build` passed; the first State rendered a complete 256×256 blob thumbnail at 96×96, rendered again after a real Motion collapse and reopen, with zero fallback or loading nodes and an empty browser console and page error log.

Owner: `src/components/ui/thumbnail/thumbnailService.tsx::ThumbnailServiceProvider`, `src/thumbnail/thumbnailRenderer.ts::createOrthographicThumbnailRenderer`, `src/components/ui/thumbnail/StateThumbnail.tsx::StateThumbnail`.

**G2. Transitions as first class cards. DONE.**

Each gap is now a selectable card with transition title, order, easing, and duration. Selection binds the right rail to that exact transition.

Shipped in #91: `src/panels/motion/PieceStateStrip.tsx::PieceStateStrip`, `src/panels/motion/PieceMotionPanel.tsx::PieceMotionPanel`.

**G12. Modified state affordance. DONE as Update action.**

The earlier text badge was replaced by a direct Update button on the modified State card. The same action also appears in the State inspector. This is the shipped interaction decision rather than a literal copy of the mockup pill.

Shipped in #91: `src/panels/motion/PieceStateStrip.tsx::PieceStateStrip`, `src/panels/motion/MotionInspector.tsx::StateInspector`, `src/panels/panels.css::.cc-state-tile-update`.

**G10. BUILD IN as a card. DONE.**

BUILD IN is the leading filmstrip card, with the dot grid glyph and formatted delay. Selecting it opens the assembly and preset controls in the right rail.

Shipped in #91: `src/panels/motion/PieceStateStrip.tsx::PieceStateStrip`, `src/panels/motion/MotionInspector.tsx::ArrivalInspector`.

**G19. Start delay units. PARKED → TX.**

The BUILD IN card displays seconds through `formatSecondsLabel`. The inspector still exposes `Start delay ms` and edits the raw millisecond value.

Shipped in #91: `src/panels/motion/PieceStateStrip.tsx::PieceStateStrip`. Remaining owner: `src/panels/motion/MotionInspector.tsx::ArrivalInspector`.

**G13. POLARITY pill. CLOSED.**

Polarity stays in the SCENE rail; no dock pill (Stuart, 2026-07-17). The rail location is sufficient.

Owner: `src/panels/SceneSection.tsx::SceneSection`.

**G14. Close motion button. DONE.**

The floating Close motion button is gone. The open card collapses through its grip, and the closed state renders a horizontal Motion tab backed by persisted `panelLayout.dockOpen`.

Shipped in #91: `src/panels/BottomDock.tsx::BottomDock`, `src/state/cubicellState.ts::PanelLayout`.

## (d) Scrubber and timeline

**G7. Scrubber and timeline. CLOSED.**

The browser blue range style is gone. The transport has a hairline track, vertical playhead, formatted elapsed and total time, a focused segment window, and a compact formatted speed control. The mockup's leading build-in tick dots were deliberately dropped (Stuart, 2026-07-17).

Shipped in #91: `src/panels/motion/PieceMotionPanel.tsx::TransportRow`, `src/panels/panels.css::.cc-dock-playhead`, `src/panels/panels.css::.cc-dock-time`.

## (e) Stray artifacts and bugs

**G8. Full width red orange axis line. CLOSED.**

The world X axis line rendering across the motion canvas is not a gap (Stuart, 2026-07-17); it stays as-is, no suppression or restyle in the motion workspace.

Owners: `src/app/App.tsx::App`, `src/scene/WorldAxesChrome.tsx::WorldAxesChrome`.

**G15. View pad clipped by the dock. DONE.**

The dock now reserves a right gutter sized for the keypad, so its home position remains visible beside the expanded dock.

Shipped in #91: `src/app/studio-shell.css::.studio-dock`, `src/app/FloatingKeypad.tsx::FloatingKeypad`.

## (f) Missing or diverging controls

**G9. MODE AUTO/CUT. CLOSED (documented).**

Reframed by the scout (`~/.mdx/projects/f1-g9-cut-scout.md`). "Cut" is two things: (1) a working, tested forced-cut mode (`Transition.mode === 'cut'`, whole-scene swap at `cutAt × duration` in `sampleSceneTransition`) with NO Editor control, and (2) the `cutAt` scalar, which the "Scene switch" scrub edits and which every AUTO morph relies on to time non-interpolatable fields (visibility, frameId, polarity, projection, grid mode). The authored `TransitionMode = 'auto' | 'cut'` model exists; only its control is missing, so the old "no authored model" claim was stale.

Decision (Stuart, 2026-07-17): the forced-cut mode is not a wanted product feature but is a deliberate tested capability, so it is neither deleted nor flagged. A NOTE comment marks it as intentional-and-unsurfaced at `src/domain/score.ts::TransitionMode` and the `sampleSceneTransition` cut branch. The `cutAt` / Scene-switch scrub stays (auto-morph timing).

Owners: `src/domain/score.ts::TransitionMode`, `src/evaluation/sceneTransition.ts::sampleSceneTransition`, `src/panels/motion/MorphInspector.tsx::MorphInspector`.

**TX. Transform / transition control cluster. PARKED (hands-on).**

Owner decision (Stuart, 2026-07-17): the transition/transform controls are suspected non-functional. Most produce no visible effect in playback, so they will not be edited blind. They are parked as one item pending a hands-on iteration session between Stuart and fable to reproduce, diagnose, and fix each control against live playback. Subsumes G16 (labels/order), G17 (ORDER), G18 (EASING), G19 (start-delay units), and the broader runtime audit of duration, scene switch, cube class, order, stagger, easing, steps, and start delay.

**G16. CUBES class labels. PARKED → TX.**

The inspector still presents Entering, Leaving, Moving in that order, with helper copy. The signed-off labels ENTER, MOVE, LEAVE remain unapplied.

Owner: `src/panels/motion/MorphInspector.tsx::morphClassLabels`.

**G17. ORDER behavior. PARKED → TX.**

The segmented control patches class motion order, and evaluation has order generation. Stuart's live observation that the choices do not visibly change playback remains unresolved and requires a focused runtime trace before closure.

Owners: `src/panels/motion/MorphInspector.tsx::MorphInspector`, `src/domain/assemblyOrder.ts::generateAssemblyOrder`, `src/evaluation/sceneMorph.ts::prepareSceneMorph`.

**G18. EASING behavior. PARKED → TX.**

The segmented control patches class easing, and evaluation resolves easing functions. Stuart's live observation that the choices do not visibly change playback remains unresolved and requires the same runtime trace.

Owners: `src/panels/motion/MorphInspector.tsx::MorphInspector`, `src/evaluation/scoreAt.ts::easingFor`, `src/evaluation/sceneMorph.ts::sampleSceneMorph`.

The separate runtime behavior audit still covers duration, scene switch, cube class, order, stagger, easing, steps, and start delay.

## (g) Adjacent, likely out of F1 scope

**G20. Left rail form. CLOSED.**

The rail stays a dockable tabbed card (Stuart, 2026-07-17); the full-height STRUCT treatment is dropped.

Owners: `src/panels/LeftRail.tsx::LeftRail`, `src/panels/StructureSection.tsx::StructureSection`.

## (h) Runtime crash

**G21. Perspective wheel zoom update loop. DONE.**

Current `hasMatchedPerspectiveFraming` gates only on assigned FOV and excludes pose derived perspective zoom. `applyPerspectiveProjection` therefore accepts a wheel zoomed camera without rebuilding it. The regression is covered by `tests/cameraProjectionSwap.test.ts::a camera built from a wheel-zoomed pose never triggers a rebuild`.

Fixed before #91 in `src/pose/projectionMatch.ts::hasMatchedPerspectiveFraming` and `src/camera/cameraProjectionSwap.ts::applyPerspectiveProjection`.

## (i) Deferred tech debt

**G22. Stage plan preparation cadence. DEFERRED.**

The comparison plan still keys on a per tick source object, and piece playback can still reach `sampleSceneTransition` without a prepared plan. This remains post merge performance work.

Owners: `src/transport/useStagedScene.ts::useStagedScene`, `src/evaluation/sceneTransition.ts::sampleSceneTransition`, `src/evaluation/sceneMorph.ts::prepareSceneMorph`.

## Suggested attack order

1. TX (parked): Stuart + fable hands-on session to diagnose and fix the transform/transition controls (G16-G19 and the broader runtime audit) against live playback.
2. Address deferred G22 (independent perf; tx-linked=no) when scheduled.
