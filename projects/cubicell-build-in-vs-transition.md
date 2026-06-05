# Build In vs Transition

Working doc for the two motion panels. Every mapping verified against main `c32bb72`
plus the cut-mode branch tip `bffa6f5` (the Mode control lands in `85118e7`,
`feat(motion): author cut transitions`). Citations are file + symbol.

## The conceptual split

A piece's score holds exactly two piece tracks (`domain/score.ts` `PieceScore`):
one `AssemblyTrack` and one `StateTransitionTrack`. The BUILD IN panel edits the
first, the TRANSITION panel edits one `Transition` inside the second. They divide
time, not features.

Build In is presence from nothing into the first State. The assembly track holds a
materialized cube-id `order` plus cadence, and `applyAssemblyTrack`
(`evaluation/scoreAt.ts`) turns time into a per-cube presence value in [0, 1].
Presence multiplies pose scale (`applyMomentToLayout`) and presence 0 is absence
everywhere: no instances, no hit targets, no neighbor slots (`getMomentCells`).
There is one Build In per structure; it plays whenever the piece holds a State
statically, which in practice means before the sequence starts.

A Transition is a State-to-State scene morph. `prepareSceneMorphTopology`
(`evaluation/sceneMorph.ts`) diffs the two endpoint scenes once into entering
(added), leaving (removed), and changing (retained-but-different) classes, and
`sampleSceneMorph` schedules each class independently from its own `ClassMotion`.
Each keyframe gap owns exactly one `Transition` (`domain/score.ts`
`StateTransitionTrack`).

The handoff is the pieceAt contract (`evaluation/pieceAt.ts`
`resolveStateTransitionPosition` in `domain/stateTransition.ts`): piece times
before `startMs` hold the first State static, and the static branch of
`samplePieceAt` evaluates the score through `scoreAt`, so assembly owns that
window. From `startMs` onward, adjacent transitions run back to back on their
authored durations, and the active transition exclusively owns presence and
properties; transitions never sample the assembly track. Once at least one
transition exists, the sequence end is the piece end (`getScoreDurationMs`), so a
longer assembly cadence cannot create a hidden tail.

Note the mechanism difference behind a shared look: assembly grows cubes by
scaling presence itself, while a morph keeps presence binary
(`sampleSceneMorph` sets 0 or 1) and grows entering cubes by interpolating from a
synthesized zero-scale endpoint (`synthesizeMorphEndpoint`). Same perceptual grow,
two owners.

## BUILD IN panel controls

The panel is `ArrivalInspector` (`panels/motion/MotionInspector.tsx`) wrapping
`AssemblyControls` (`panels/AssemblyControls.tsx`). All edits are score operations
through `applyScoreOperation` (`domain/score.ts`) except the first and last.

- **Start delay ms** — `StateTransitionTrack.startMs` via `set-piece-transition-start`
  (`domain/structureOperations.ts` `setPieceTransitionStart`). Not an assembly
  field: it delays the State sequence, which is what gives the build room to play.
  Default 0, UI 0 to 10000 in steps of 100. Evaluated by
  `resolveStateTransitionPosition` and `getStateTransitionEndMs`.
- **Order** (Made/X/Y/Z/Radial/Spiral/Shell/Dice) — `AssemblyTrack.orderMode`, an
  `OrderMode` (`domain/assemblyOrder.ts`). `regenerate-assembly-order`
  materializes `track.order` through `generateAssemblyOrder`; the id list, not the
  mode, is evaluation truth. Made is creation order. X/Y/Z are axis sweeps;
  reselecting the active axis reverses direction. Radial ranks by squared
  Euclidean distance from the order origin (the selected cube, else the bounds
  center; `resolveOrderOrigin`), Shell by Chebyshev onion layer, Spiral by layer
  then angle then height (`rankFor`). Dice is `seededShuffle` with a
  fresh random seed on every selection, including reselecting Dice
  (`panels/motion/motionOptions.ts` `resolveOrderModeChange`).
- **Arrive ms** — `AssemblyCadence.arriveMs`, one cube's arrival duration.
  Default 480, UI 0 to 2000 step 20.
- **Step ms** — `AssemblyCadence.stepMs`, the nominal offset between consecutive
  starts. Default 320, UI 0 to 1200 step 20. Offsets come from
  `getAssemblyStartOffsetMs` (`domain/assemblyTiming.ts`).
- **Curve** (Even/Accel/Rit/Swing) — `AssemblyCadence.curve`, a `CadenceCurve`.
  Shapes start offsets only, never the per-cube easing: Even is `index * stepMs`,
  Accel front-loads and Rit back-loads against the same total span, Swing
  displaces every odd cube by a third of a step. Default linear (Even).
- **Easing** (Out/InOut/Linear/Settle) — `AssemblyTrack.easing`, an `EasingId`
  applied to each cube's own arrival progress (`easingFor` in
  `evaluation/scoreAt.ts`). Settle maps to `easeOutBack`: presence overshoots
  past 1 and settles back. Default ease-out-quart (Out).
- **Steps** — `AssemblyTrack.quantize`; 0 clears it. `quantizeProgress` snaps
  eased presence to N levels for stop-motion arrival.
- **Exit** toggle — sets or clears `AssemblyTrack.exit` with
  `defaultAssemblyExit` (departMs 360, holdMs 800, order reverse, stepMs 240).
  The exit build-out runs inside `applyAssemblyTrack`: presence is the minimum of
  the arrival term and the exit term.
- **Hold ms** — `AssemblyExit.holdMs`; departures start at build end plus hold
  (`getAssemblyBuildDurationMs` plus holdMs).
- **Depart ms** — `AssemblyExit.departMs`, one cube's departure duration.
- **Exit step** — `AssemblyExit.stepMs`, departure stagger, run through the same
  `getAssemblyStartOffsetMs`.
- **Reverse** — `AssemblyExit.order` "reverse" or "same": reverse departs in
  inverse arrival order (`departIndex = count - 1 - index`).
- **Build in preset** button — `apply-piece-preset` "build-in"
  (`domain/structureOperations.ts` `applyPiecePreset`): creation-order assembly
  with default cadence and easing, no exit or quantize, `startMs` set to exactly
  the build duration, and every transition reset to `defaultTransition`.

## TRANSITION panel controls

The panel is `TransitionInspector` (`panels/motion/MotionInspector.tsx`) hosting
the shared `MorphInspector` (`panels/motion/MorphInspector.tsx`). Edits dispatch
`patch-transition` operations that land in `patchTransition`
(`domain/stateTransition.ts`) via `applyStructureSequenceOperation`.

- **Duration ms** — `MorphSettings.durationMs` (`domain/morphSettings.ts`), the
  whole transition's span. Default 1200, UI 100 to 8000 step 50.
- **Mode** (Auto/Cut, branch only) — `Transition.mode`, a `TransitionMode`
  (`domain/score.ts`), authored as `TransitionPatch.mode`. Cut disables Cubes,
  Form, Order, Stagger, Easing, and Steps in the inspector; Duration and Scene
  switch stay live. See the cut section below.
- **Scene switch** — `MorphSettings.cutAt`, a 0 to 1 fraction, default 0.5, step
  0.05. In auto mode it is the cutover point for non-interpolated fields; in cut
  mode it locates the whole-scene swap.
- **Cubes** (Entering/Leaving/Changing) — selects which `MorphClassId`
  (arrive/depart/change) the class controls below edit. Membership comes from the
  endpoint diff in `prepareSceneMorphTopology`, shown in the hint line.
- **Form** (Grow/Slide/Drop/Turn) — `MorphSettings.arriveForm` or `departForm`, a
  `MorphForm`, default grow. Chooses the synthesized off-stage endpoint
  (`synthesizeMorphEndpoint`): grow scales from zero, turn arrives through a
  quarter rotation, drop falls in from above the bounds, slide enters along the
  axis where the cube sits farthest from center (`resolveSlideDirection`).
  Changing has no form; its endpoints are both real.
- **Order** — `ClassMotion.order`, the same `OrderMode` vocabulary as assembly,
  fed to `generateAssemblyOrder` inside `planClassMotion` to order the class's
  stagger starts, always from the class members' bounds center (no selection
  input). Enabled only with two or more members and nonzero stagger.
- **Stagger ms** — `ClassMotion.staggerMs`, default 40, UI 0 to 400 step 10.
  Unlike assembly's open-ended cadence, stagger is compressed to fit the authored
  duration: `planClassMotion` caps it so every cube keeps at least
  `morphMinCellDurationMs` (120 ms) of its own motion.
- **Easing** — `ClassMotion.easing` per class; defaults ease-out-quart for
  arrive and depart, ease-in-out-quart for change (`defaultMorphSettings`).
- **Steps** — `ClassMotion.quantize`, same `quantizeProgress` snapping, applied
  to that class's eased progress.

## Why the panels overlap yet differ

Order, easing, and steps appear in both because both tracks are the same
choreography idea, staggered per-cube progress, and they literally share the
evaluators: `generateAssemblyOrder`, `easingFor`, `quantizeProgress`. What differs
is the owner and the time budget. Assembly acts on presence for every cube in the
scene and its duration is derived, count times step plus arrive, so cadence
(arrive + step + curve) is the authoring surface. A transition acts on one diff
class inside a fixed authored duration, so it exposes duration + stagger and
compresses stagger to fit rather than letting the span grow.

## Cut

On main `c32bb72`, `mode: "cut"` is a working, tested capability with no Editor
control (the NOTE on `TransitionMode` in `domain/score.ts`); nothing authors it,
so it only runs from persisted or programmatic data. Branch `85118e7` adds the
Mode segmented control and rewires `onTransitionChange` to emit `TransitionPatch`
(mode and/or settings) end to end.

What auto does today: `resolveTransitionKind` (`domain/stateTransition.ts`)
returns morph for auto, always. The transition realizes the complete destination
inside its duration. cutAt then governs discrete cutover at two levels in
`sampleSceneMorph`. Per cube, entering and changing cells swap their
non-interpolated fields (visibility, grid coord, discrete edge and face state)
when that cell's class-local progress crosses cutAt, so staggered cubes cut at
different wall times. Per scene, `globalCut` (global progress at or past cutAt)
selects frameId, polarity, and projection, and flips the grid interpolation
endpoint check. Leaving cubes are insensitive to cutAt in practice: both their
interpolation endpoints derive from the same a-side cell.

What cut does: `sampleSceneTransition` (`evaluation/sceneTransition.ts`) returns
scene a wholesale until `cutAt * durationMs`, then scene b, with a null moment.
Zero duration shows b immediately. Nothing tweens across a cut, no presence, no
color tweens, no arrangement lerp; that is why the class controls disable.

What still tweens across the auto cutover: offset, rotation, scale, size, gap
widths and arrangement offset, part colors (as `PartColorTween` overlays), and
numeric ink such as opacity and thickness (`interpolateCell` with
`materialProgress` clamped so settle overshoot stays inside authored endpoints).
What never tweens in any mode: visibility, grid coord, frameId, polarity,
projection; those are always discrete selections.

Interaction with the exit build-out and reverse: none, structurally. Exit lives
on the assembly track and only evaluates in the static hold before `startMs`;
transitions, cut or auto, never sample it. The one visible coupling is the
handoff itself, question 1 below.

## Open questions

1. If `startMs` is set past build end plus hold, the exit build-out departs cubes
   during the hold, and at `startMs` the first transition takes ownership with
   full presence: departed cubes reappear instantly. Is a partially played exit
   before a State sequence a supported composition, or should exit and start
   delay be coupled or gated in the UI?
2. `AssemblyExit.curve` exists in the domain and is honoured by
   `getAssemblyStartOffsetMs`, but `AssemblyExitFields` exposes no curve control
   while the entry cadence has one. Intended asymmetry or a missing control?
3. In auto mode one cutAt value is compared against two clocks: class-local
   progress per cube and global progress for scene-level fields. Cubes late in a
   stagger order cut after the frameId/polarity/projection swap. Is the staggered
   discrete cutover intended, and should the scene-level swap align to any cell?
4. On the branch the "Scene switch" label keeps one name for two semantics:
   auto's non-interpolated cutover point versus cut's whole-scene swap point.
   Should the label or copy change with mode?
5. The Build In preset silently resets every authored transition to
   `defaultTransition` (`applyPiecePreset`). It is undoable, but is a full
   sequence reset the intended scope for a button labelled as a build-in preset?
6. The UI floors duration at 100 ms while the domain accepts 0
   (`normalizeNonnegative`) and both evaluators special-case zero. A persisted
   zero-duration transition renders but cannot be re-authored below 100. Should
   the floor live in one place?
