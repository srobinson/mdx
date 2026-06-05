# Scout: piece-source transport seam (baseline for slice 4 review)

Derived read-only from feat/animation-studio at fea9eaf in the animation-studio
worktree, code only, no spec input. Citations are `file:symbol`. This is the
uncontaminated baseline the slice 4 diff will be checked against.

Baseline fact that frames everything below: the branch already carries the
slice 2 snapshot domain (`AnimationAsset.pieceSnapshots`, `originPlacement`,
`domain/workbench.ts:getSnapshotStateScene`), but the transport seam has zero
snapshot wiring. The Editor transport previews exactly one piece: the attached
StructureAsset. Every clamp, duration, and resolver in this map is bound to it.

## 1. Seam symbols: readers, writers, precedence

### resolveStageSource (src/transport/stagedScene.ts:resolveStageSource)

Sole caller: `transport/stagedScene.ts:createStagedSceneReader`. Nothing else
in src calls it (searches: `rg resolveStageSource` over src). It is pure: reads
Workbench plus a StageSession picked as `{morphScrub, transport.timeMs}`.

Current precedence, stated precisely:

1. **Comparison wins first.** If `session.morphScrub` is non-null AND its
   `stateId` resolves via `domain:findState`, the result is a
   `ComparisonStageSource`. Progress is `clamp(scrub.t, 0, 1)` with non-finite
   `t` coerced to 0. The sample is
   `evaluation:resolveSceneTransitionSample` from the saved State scene
   (`domain:getStateScene`) to the live working scene
   (`domain:getWorkingScene`), through the module-local
   `editorComparisonTransition` (mode `auto`, `defaultMorphSettings`), at
   `timeMs = progress * durationMs`. A morphScrub whose stateId does NOT
   resolve falls through silently to the next rung (and
   `state/sessionReferences.ts:repairEditorSessionReferences` nulls dangling
   scrubs on workbench change, so this rung is normally self-healing).
2. **Piece second.** `evaluation/pieceAt.ts:resolveAttachedPieceSource`
   returns `{kind:"piece", asset, timeMs}` only when `transport.timeMs !==
   null` AND `domain:findAttachedStructureAsset` finds an attached structure.
   Detached scratch or a detached clock resolves nothing.
3. **Authored last.** Fallback is `{kind:"authored", scene: getWorkingScene}`.

The exclusion between rungs 1 and 2 is enforced by the store, not the
resolver (the resolver's doc comment says so): see transport writers below.
The resolver order is the tie-break if both are ever set.

### sampleStageSource (src/transport/stagedScene.ts:sampleStageSource)

Sole caller: `createStagedSceneReader`. Maps a StageSource to a StagedScene:

- `authored` → `interactive: true`, `projectionBehavior: "animated"`, clears
  the morph plan cache.
- `piece` → `evaluation/pieceAt.ts:resolvePieceSample` then
  `evaluation/pieceAt.ts:samplePieceAt`. **A null resolve silently falls back
  to the authored working scene with `source: "authored"`** and interactive
  staging. Piece frames are `interactive: false`, `projectionBehavior:
  "instant"` (`pieceAt.ts:pieceFrame`).
- `comparison` → `evaluation:sampleResolvedSceneTransition`; `interactive`
  only at `progress === 1`, projection `"instant"`.

### resolvePieceSample (src/evaluation/pieceAt.ts:resolvePieceSample)

Sole src caller: `sampleStageSource` (tests also call it directly). Signature
is structure-bound: `(workbench, asset: StructureAsset, timeMs)`. It resolves
the asset's state-transition track (`domain:findStateTransitionTrack`,
`domain:resolveStateTransitionPosition`), then resolves every endpoint through
`domain:findState` + `domain:getStateScene`, i.e. through the **workbench
state pool**, not through snapshot-pinned revisions. Static positions carry
`scoreAt` evaluation of `asset.score`; transitions sample between adjacent
states' pose revisions. Null (no track, no position, missing state or
transition) means the caller keeps its staging.

### Companion symbols with exactly one caller each

- `pieceAt.ts:resolveAttachedPieceSource` → called only by
  `resolveStageSource`.
- `pieceAt.ts:samplePieceAt` → called only by `sampleStageSource`.
- `transport/stagedScene.ts:selectStagedSceneSources` → called by
  `app/useEditorCommands.ts:useEditorCommands` (store-snapshot reads).
- `transport/stagedScene.ts:createStagedSceneReader` → one instance per
  editor session, created in `useEditorCommands` and handed to
  `studios/editor/EditorStudio.tsx` as `readStagedScene`.
- `transport/stagedScene.ts:useStagedScene` → called only by
  `EditorStudio.tsx:EditorApp` (the canvas scene, moment, projection,
  interactivity, and polarity all come from this one read).

### Staged-scene consumers (output side of the seam)

1. `studios/editor/EditorStudio.tsx` — the drawn scene via `useStagedScene`.
2. `app/useEditorCommands.ts` — the framing port and the projection port both
   read through the same reader instance, so a framing answer and the drawn
   frame can never disagree (the `StagedSceneReader` doc comment states the
   contract: consumers needing several facets of one staged moment cannot
   split across two scenes).

There is exactly one reader instance and one
`transport/activeTransitionPlan.ts:createActiveTransitionPlanCache` per
session. The reader memoizes on `(workbench, morphScrub, transport.timeMs)`
identity, so repeated reads of one store state return the identical object.

## 2. The transport clock

State: `state/cubicellState.ts:TransportState` = `{loop, loopWindow, playing,
rate, timeMs}` living at `editor.transport`; `timeMs: null` means detached
(no Moment, authored staging). `detachedTransport` is the initial value; it is
session state, never persisted.

### Writers

All mutation flows through the store actions in
`state/actions/transportActions.ts:createTransportActions`, with one deliberate
exception (the authored reducer):

- `setTransportTime` — clamps to `[0,
  state/transportSelectors.ts:getPieceTransportDurationMs]`; `null` detaches
  AND stops playing; a non-null write clears `morphScrub`.
- `setTransportPlaying` / `toggleTransportPlaying` — via
  `transportActions.ts:withTransportPlaying`: starting from detached or from
  the held end restarts at 0; play is refused while duration is 0; starting
  play clears `morphScrub`.
- `setTransportRate` — clamps to `editor/commands.ts:transportRateMin..Max`.
- `setTransportLoop`, `toggleTransportLoop`, `setTransportLoopWindow`.
- `setMorphScrub` — arming a scrub writes `playing: false, timeMs: null`
  (this is the store-enforced comparison/piece exclusion; a comparison can
  never race an armed clock).
- `setSaveState` — a local blocking save state pauses playing.
- The tick: `transport/advanceTransportFrame.ts:advanceTransportFrame` reads
  the clock, computes `transport/advanceTransportTime.ts:advanceTransportTime`
  (rate-scaled delta, loop-window wrap, clamp-and-stop at duration), and
  writes back **through `setTransportTime` / `setTransportPlaying`**, not
  directly. It is driven by
  `transport/TransportFrameDriver.tsx:TransportFrameDriver` (a `useFrame`
  hook), mounted by `scene/CubeScene.tsx` only when its `transportStore` prop
  is non-null, and `studios/editor/EditorRendererBinding.tsx` passes the store
  only while `transport.playing`. So the tick exists only inside a playing
  canvas, and `transport/advanceScheduledTransportFrame.ts` reports the
  playback render producer alongside it.
- `state/actions/authoredReducer.ts` — the one direct writer outside the
  actions: authored edits pause playback (`playing: false`) unless
  `authoredReducer.ts:keepsPlaybackRunning` says otherwise (scene `edit-score`
  batches, `patch-transition`, `set-piece-transition-start`,
  `apply-piece-preset`, or the explicit `keepPlaying` option);
  `reduceViewSceneOperationState` applies the same pause. It never touches
  `timeMs`.

Command surface: `interaction/commands/transport.commands.ts` registers
transport-play/pause/scrub/loop-toggle/play-toggle/set-rate, whose port is
wired to the store actions in
`app/useSynchronousEditorCommands.ts:useSynchronousEditorCommands`. Keyboard
reaches these through `editor/keyboard/keymap.ts`. Handlers are thin; clamp,
restart, duration-zero refusal, and detach-on-null all live in the store.

### Readers

1. `transport/stagedScene.ts` (`selectStagedSceneSources`, `useStagedScene`)
   — `timeMs` into the stage resolver.
2. `studios/editor/useCameraTrackFrame.ts` — `playing` + `timeMs` for camera
   replay; keys its epoch to the play-start edge; retains one frame.
3. `studios/editor/EditorRendererBinding.tsx` — `playing` gates the
   `transportStore` prop, hence the tick driver mount.
4. `app/SelectionFocusDriver.ts` — the armed edge only (`timeMs !== null`),
   deliberately not per tick, so playback never drives the camera through the
   React shell.
5. `panels/motion/PieceMotionPanel.tsx` — `playing`, `timeMs !== null`,
   `loop`, `rate` for the dock controls; owns the loop window via
   `setTransportLoopWindow` from card focus.
6. `panels/motion/usePublishedTransportTime.ts` — DOM playhead reads, rate
   bounded to `config/cubicellConfig.ts:transportPlayheadMaxHz`, exact at
   rest, on loop wrap, and on pause.
7. `transport/advanceTransportFrame.ts` / `advanceScheduledTransportFrame.ts`
   — the tick's own read.
8. `state/transportSelectors.ts:getPieceTransportDurationMs` — not a clock
   reader but the single duration source the clock is clamped against; bound
   to the attached structure, 0 when detached.

### What a second reader (a studio canvas) must and must not do

Must: treat `editor.transport` as read-only outside the store actions; read
`timeMs` per frame only inside a canvas frame loop, and through the
`usePublishedTransportTime` pattern for anything DOM-side; obtain its scene
through the resolver/sampler pair (its own reader instance and plan cache are
fine, the functions are pure) rather than re-deriving from Workbench + time.

Must not: mount a second `TransportFrameDriver` against the same store (each
mounted driver adds its own frame delta, so two drivers double the playback
rate); write `timeMs`/`playing` except through the actions; introduce its own
duration constant (the clamp in `setTransportTime`, the restart rule in
`withTransportPlaying`, and the tick all consult
`getPieceTransportDurationMs`, so a divergent duration desynchronizes clamp
and stop); create per-tick subscriptions in the React shell (the
`SelectionFocusDriver` comment records this as deliberate).

## 3. Invariants a snapshot-playback extension must preserve

Each stated as a checkable assertion at symbol level:

- **I1 Single resolver.** Every scene a canvas draws is produced by
  `resolveStageSource` → `sampleStageSource` through a `StagedSceneReader`;
  no component derives a drawable scene from Workbench plus transport time by
  any other call path.
- **I2 Total precedence order.** comparison > piece > authored is decided
  inside `resolveStageSource` and nowhere else; any new source kind appears in
  that function with an explicit position in the order, and the corresponding
  store-level exclusion writes live in `createTransportActions` (the pattern:
  arming one source detaches the other, as `setMorphScrub` and
  `setTransportTime`/`setTransportPlaying` do today).
- **I3 Clock ownership.** The only writers of `editor.transport` are the
  actions in `createTransportActions` and the enumerated pause rule in
  `authoredReducer` (`keepsPlaybackRunning`); the tick writes through the
  actions. Assert: no new `set(...{transport...})` site outside those two
  files.
- **I4 One tick per clock.** At most one `TransportFrameDriver` is mounted
  per store; mounting stays gated on `transport.playing` through a single
  canvas binding.
- **I5 Duration coherence.** `timeMs` is `null` or within `[0, D]` where D
  comes from exactly one selector; today that is
  `getPieceTransportDurationMs`. If snapshot playback needs a different D,
  the selector itself must become source-aware; the clamp
  (`setTransportTime`), restart (`withTransportPlaying`), refusal
  (`durationMs === 0`), and tick stop (`advanceTransportTime`) must all read
  the same D. Assert: no second duration function feeding any of those four.
- **I6 Detached means authored.** `timeMs === null` ⇒
  `resolveAttachedPieceSource` returns null ⇒ authored staging;
  `setTransportTime(null)` also forces `playing: false`.
- **I7 Fail-open staging, fail-closed interaction.** A null
  `resolvePieceSample` falls back to the authored scene, never throws; every
  piece frame is `interactive: false` with `projectionBehavior: "instant"`.
- **I8 Snapshot pin resolution.** Any snapshot-side sampler resolves scenes
  through the snapshot's pinned revisions
  (`domain/workbench.ts:getSnapshotStateScene`), never through
  `findState`/`getStateScene` on the workbench state pool; snapshot-local
  state ids are not in that pool by the slice 2 namespace invariant, so a
  `findState` path would null out and mask itself via I7's fallback.
- **I9 Reader coherence.** Consumers needing several facets of one staged
  moment read them from one `StagedScene` object returned by one reader call;
  framing and drawing share a reader instance per session.
- **I10 Pause-list completeness.** If snapshot-score edits arrive, every
  operation kind that should survive playback appears in
  `keepsPlaybackRunning` explicitly; an edit kind absent from the list pauses
  playback by default (fail-safe direction is pause, not stale staging).
- **I11 Bounded DOM reads.** DOM-side playhead consumers go through
  `usePublishedTransportTime` (or an equivalent bounded publisher), never a
  raw per-tick store subscription in the shell.

## 4. Predicted seam risks for the builder, ranked

1. **A second clock or a second tick.** The most plausible defect: the studio
   canvas gets its own transport-like state or mounts its own
   `TransportFrameDriver` while the editor's clock still exists. Either two
   clocks with no precedence rule (the classic invisible-in-diff defect) or a
   double-advancing single clock. The seam supports exactly one clock today;
   a studio clock is only acceptable as a new owned state with an explicit
   exclusion write against `editor.transport`, mirroring the
   morphScrub/transport pattern.
2. **Duration fork.** `getPieceTransportDurationMs` is attached-structure
   bound and returns 0 for detached scratch, so play is refused and
   `setTransportTime` clamps to 0. A builder who feeds snapshot playback
   through the existing actions without making the duration selector
   source-aware gets a clock that silently clamps to the wrong piece's
   duration, or refuses to play at all in the studio. Breaks I5 without any
   visible diff to the actions.
3. **Resolver bypass.** Sampling the snapshot score directly in the studio
   component (new sampler call in the canvas) instead of adding a source kind
   to `StageSource` inside `resolveStageSource`. Produces an unenumerated
   consumer outside the precedence order, the interactive/projection
   contract, and the plan cache. Breaks I1/I2/I9.
4. **Wrong state resolution for snapshots.** Reusing `resolvePieceSample`
   verbatim: its `findState`/`getStateScene` endpoint resolution reaches the
   workbench pool, and snapshot-local ids miss by design, so the I7 fallback
   renders the authored scene and the failure looks like "playback shows the
   wrong thing sometimes" rather than an error. The fallback that protects
   the editor masks breakage in the studio. Breaks I8.
5. **Comparison exclusion leak.** If the studio shares `editor.transport`, an
   editor-side `setMorphScrub` detaches it (`playing: false, timeMs: null`),
   silently stopping studio playback; conversely a studio play clears an
   editor scrub. Cross-studio session coupling with no rule recorded.
6. **Pause-list drift.** Snapshot-editing operation kinds absent from
   `keepsPlaybackRunning` stop playback on every edit (annoying but safe), or
   get added wholesale (stale staging during structural edits). Breaks I10 in
   the unsafe direction if added too broadly.

Consumers mapped: 24 owning symbols (5 seam-function call sites, 9 transport
actions, 2 authored-reducer pause sites, 8 transport/staged readers). Searches
run for absences: `rg` over src for `resolveStageSource`, `sampleStageSource`,
`resolvePieceSample`, `resolveAttachedPieceSource`, `samplePieceAt`,
`TransportFrameDriver`, `editor.transport`, `TransportState`,
`getPieceTransportDurationMs`, `morphScrub` — no callers exist beyond those
named above; no snapshot-side transport, sampler, or duration symbol exists
on this branch (none found).
