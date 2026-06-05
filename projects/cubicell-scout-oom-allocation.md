# Cubicell OOM allocation scout

Scope: read only static map of the evaluation and rendering allocation path in
`docs/performance-audit` at
`60da3f7d2fe43da0f3212dc9ee6b9b57d9f79323`. The worktree was clean at the
start of the scout. Persistence queueing, serialization, workers, and storage
were excluded by the brief.

## Reuse Map

### Reused across playback frames

- `useStagedScene` creates one active transition plan cache for the mounted
  stage (`src/transport/useStagedScene.ts:127-143`). The cache explicitly
  excludes sample time from its key and retains one plan
  (`src/transport/activeTransitionPlan.ts:29-35`).
- The plan is reused while the endpoint revision identities and transition
  settings remain equal (`src/transport/activeTransitionPlan.ts:43-50`). It
  retains the two endpoint scenes, an A cell map, added, changed, colour ink,
  numeric ink, and shared edge sets, three class schedules, and the shared edge
  plan (`src/evaluation/sceneMorph.ts:38-53`,
  `src/evaluation/sceneMorph.ts:61-107`). Its bound is one active transition.
- Classification and schedule work is deliberately prepared once. Changed
  cells are classified for colour and numeric ink once
  (`src/evaluation/sceneMorph.ts:71-90`), and each motion class retains one
  cube start time map (`src/evaluation/sceneMorph.ts:244-264`).
- Within a sampled frame, added cells reuse the B cell object, unchanged common
  cells reuse the A cell object, and changed cells at their local endpoints
  reuse A or B (`src/evaluation/sceneMorph.ts:145-181`,
  `src/evaluation/sceneMorph.ts:297-305`). A changed cell without numeric ink
  also reuses its endpoint edge and face records
  (`src/evaluation/sceneMorph.ts:311-337`).
- `useStableGridLayout` retains one previous layout and reuses pose references
  whose numeric values are unchanged, after constructing the candidate layout
  (`src/scene/useStableGridLayout.ts:5-21`). Its retained size is the current
  staged cell set.
- The renderer retains one `IncrementalCubeSceneOwner` in a ref
  (`src/scene/useCubeSceneInstances.ts:17-30`). The owner retains one current
  cell entry map, resolution index, input, slot owner, and result
  (`src/scene/incrementalCubeSceneOwner.ts:62-78`). A replacement frame drops
  the previous owner state.
- Three.js mesh objects survive frame updates
  (`src/scene/InstancedPartMesh.tsx:58-87`). Their instance buffers grow to a
  power of two and never shrink while mounted
  (`src/scene/instancedMeshCapacity.ts:1-19`). This is a largest observed slot
  count high water, bounded by the largest rendered bucket during that mount.
- The selection chrome matrix cache survives frames, deletes cube IDs no
  longer in the current cells, and replaces an entry when pose or size identity
  changes (`src/scene/SelectionChromeLayer.tsx:35-48`,
  `src/scene/selectionChromeInstances.ts:109-134`). It is bounded by current
  cell IDs that have needed selection or hover chrome.
- The accepted authored scene journal survives render boundaries but is capped
  at 32 entries (`src/state/authoredSceneJournal.ts:3`,
  `src/state/authoredSceneJournal.ts:29-57`) and consumed entries are
  acknowledged in a layout effect
  (`src/state/useAcceptedAuthoredSceneChanges.ts:5-17`).

### Rebuilt during playback

- Every interior morph sample allocates a new staged scene and moment
  (`src/evaluation/sceneMorph.ts:127-228`).
- Every interior sample allocates a new B length cell array. When removals
  exist, it then allocates a second union array containing B plus the removed A
  cells (`src/evaluation/sceneMorph.ts:145-145`,
  `src/evaluation/sceneMorph.ts:217-226`).
- A transient sampled scene has new scene, cells, and usually layout identity.
  The renderer treats any of those identity changes as a full sync and calls
  `createOwnerState` (`src/scene/incrementalCubeSceneOwner.ts:111-129`).
  `createOwnerState` rebuilds the complete render resolution, per cell instance
  entries, packed instance buckets, and slot registry
  (`src/scene/incrementalCubeSceneOwner.ts:157-180`).
- The authored journal patch path cannot continue across a transient morph
  frame because it requires authored previous and next scene identity to match
  the renderer input lineage (`src/scene/incrementalCubeSceneOwner.ts:183-200`).
  Transition setting edits therefore enter the same full sync path.

## Quality Map

### Reuse, duplication, dead code, and boundaries

- The evaluation seam is centralized. Piece playback resolves one transition,
  asks the one active plan cache for a plan, then calls the shared scene
  sampler (`src/transport/useStagedScene.ts:100-116`,
  `src/evaluation/pieceAt.ts:111-125`,
  `src/evaluation/sceneTransition.ts:35-72`). I found no parallel morph
  implementation to consolidate.
- The transition inspector is already shared and presentational. It emits
  typed patches to its owner rather than owning state mutation
  (`src/panels/motion/MorphInspector.tsx:34-63`). Input coalescing therefore
  belongs at the control, command, or transition update boundary if added.
- The main boundary mismatch is between transient evaluation and the retained
  renderer. The evaluator produces a fresh immutable scene graph each sample,
  while the renderer's incremental contract recognizes authored scene journal
  lineage. The result is a complete renderer resolution and instance rebuild
  every sampled frame, despite retained slot and mesh infrastructure
  (`src/evaluation/sceneMorph.ts:217-227`,
  `src/scene/incrementalCubeSceneOwner.ts:116-180`).
- `sceneMorph.ts` is 495 lines. `sampleSceneMorph` spans lines 128 through 228,
  and the file and function remain below the repository thresholds. The issue
  is allocation ownership rather than a size threshold violation.
- The prior `Steps = 0` lead is not supported by current code. The inspector
  emits `undefined` for zero (`src/panels/motion/MorphInspector.tsx:129-140`),
  domain normalization also maps nonpositive values to `undefined`
  (`src/domain/morphSettings.ts:92-95`), and `quantizeProgress` returns its
  input unchanged for `undefined` or nonpositive steps
  (`src/evaluation/scoreAt.ts:103-109`).
- The explicit cut path is documented as dormant because the UI authors no cut
  transitions (`src/evaluation/sceneTransition.ts:55-65`). It does not
  participate in the reported auto morph loop.

### Searches run

- `rg -n "sampleSceneMorph|prepareSceneMorph|interpolateCell|mapCubeEdges|mapCubeFaces|samplePieceAt" src tests`
- `rg -n -i "auto[ -]?loop|loop.*play|play.*loop|repeat.*play|requestAnimationFrame|playback" src`
- `rg -n "TransitionPanel|Transition.*Panel|transition.*(onChange|update|change)|ScrubField|Range|slider|pointermove|onInput" src`
- `rg -n "patch-transition|apply-piece-preset|set-piece-transition-start" src`
- `rg -n "useMemo|memo|cache|cached|WeakMap|WeakSet" src/evaluation src/panels src/app src/state`
- `rg -n "new Map|new Set|\[\.\.\.|\.map\(|\.filter\(|Object\.fromEntries|new Matrix4|createTransformMatrix" src/evaluation/sceneMorph.ts src/transport/activeTransitionPlan.ts src/scene/useStableGridLayout.ts src/scene/incrementalCubeSceneOwner.ts src/scene/cubeInstances.ts`
- `rg -n "saveState|recovery-failed|pendingRecovery" src`
- `rg -n "setTransportPlaying(false)|playing: false|createTransportPauseCommand" src`
- `rg -n "debounce|throttle|startTransition|useDeferredValue|requestAnimationFrame|queueMicrotask" src/components/ui/scrub-field src/panels/motion src/transport` returned no matches.

I read the direct call paths named above plus the renderer owner, instance slot
registry, mesh capacity, grid layout, cube geometry, authored scene journal,
transport actions, and modal. I did not profile a live heap, drive the browser,
read worker implementations, or inspect persistence internals.

## Findings

### 1. Per frame allocations

Let `B` be the B endpoint cell count, `R` the removed A cell count, `C` the
changed common cell count currently inside its local glide interval, and `K`
the count of colour changing cube parts. The staged union has `B + R` cells.
There are six faces and twelve edges per cube
(`src/domain/cubeTopology.ts:11-29`).

#### Scene morph evaluator

| Scope | Verified allocation |
|---|---|
| Every interior frame | One `presence` map (`src/evaluation/sceneMorph.ts:137-140`). It receives entries only for added and removed cells (`src/evaluation/sceneMorph.ts:145-149`, `src/evaluation/sceneMorph.ts:207-213`), so its entry count is `added + removed`, not the complete union. |
| Every interior frame | One `B` length cell array from `map`. With removals, one additional `B + R` union array from the two spreads (`src/evaluation/sceneMorph.ts:145-182`, `src/evaluation/sceneMorph.ts:217-226`). |
| Each active changed cell | One cube object, one placement object, one size object, and three `Vec3` arrays for offset, rotation, and scale. That is six output objects or arrays before material interpolation (`src/evaluation/sceneMorph.ts:311-350`, `src/evaluation/sceneMorph.ts:489-495`). |
| Each active numeric ink cell | Twelve new edge state objects and one edge record, plus six new face state objects and one face record (`src/evaluation/sceneMorph.ts:313-337`). `mapCubeEdges` and `mapCubeFaces` also create their 12 or 6 entry arrays and tuple arrays before `Object.fromEntries` (`src/domain/cube.ts:358-373`). This is 20 retained output objects, plus about 20 short lived array or tuple containers, on top of the six base cell allocations. |
| Each active colour ink cell | Two new part maps, one edges and one faces, plus one tween object per changed nonshared part. A cell tween container is retained when either map is nonempty (`src/evaluation/sceneMorph.ts:358-409`). The frame also gains one outer `partColors` map on first use (`src/evaluation/sceneMorph.ts:162-173`). |
| Each active shared physical edge | The frame creates a tween object per member. A member without an existing cell colour container also creates one container and two maps (`src/evaluation/sceneMorph.ts:184-204`). |
| Every interior frame | A new grid, format, gap override root and three axis records, three interpolated vectors, three temporary key sets, and key arrays proportional to authored gap override keys (`src/evaluation/sceneMorph.ts:411-447`). The returned frame also has new frame, moment, and scene objects (`src/evaluation/sceneMorph.ts:217-227`). |
| Endpoint frame | One presence map, then direct reuse of endpoint scene A or B. No staged cell or grid reconstruction (`src/evaluation/sceneMorph.ts:230-241`). |

Easing functions are table entries and are reused
(`src/evaluation/scoreAt.ts:92-101`). Unchanged common cells and added endpoint
cells still occupy the new cell array, but their cell objects are reused.

#### Downstream renderer

The evaluator's cell object count understates the frame cost. Each new
transient scene identity forces `createOwnerState`, which rebuilds layout,
occupancy and edge resolution indexes, buried face sets, per cell instances,
packed buckets, and a slot registry
(`src/scene/incrementalCubeSceneOwner.ts:116-180`,
`src/domain/incrementalCubeRenderResolution.ts:98-177`).

For one isolated, fully visible staged cube, `createCubeCellInstances` can emit
six face records, twelve edge records, and twelve edge hit target records,
about 30 rendered part objects. It creates one cell transform matrix, two
matrices for each face, two for each visible edge, and two for each edge hit
target, about 61 `Matrix4` objects per cube per full sync
(`src/scene/cubeInstances.ts:109-198`). Each transform helper also creates two
`Vector3` values, one `Quaternion`, and one `Euler`
(`src/shared/three.ts:7-16`). Dense buried cubes emit fewer visible part
records, but every staged cell still participates in the rebuilt layout and
render resolution indexes. This count is derived from code, not a heap sample.

### 2. Cache behavior and edit invalidation

There is one useful memo: the active transition plan cache. Playback time never
invalidates it. Endpoint revision identity or settings inequality does
(`src/transport/activeTransitionPlan.ts:29-60`).

A distinct transition control value produces a new normalized settings object
(`src/domain/morphSettings.ts:41-74`) and a new track, asset, and Workbench
through the document operation path
(`src/domain/stateTransition.ts:71-85`,
`src/domain/structureSequenceOperations.ts:51-78`). `useStagedScene` subscribes
to the Workbench and recomputes the source and sample when it changes
(`src/transport/useStagedScene.ts:127-144`). The settings comparison then
misses, `prepareSceneMorph` runs again, and the current frame is sampled from
the new plan (`src/transport/activeTransitionPlan.ts:43-60`).

Therefore each distinct accepted control step invalidates the one entry plan
cache. It also causes a full renderer owner rebuild. Playback frames between
edits reuse the plan, but still rebuild the sampled scene and renderer owner
each frame.

### 3. Churn and retention

#### Verified churn

- Interior frame scene, moment, cell array, presence map, grid, active changed
  cells, numeric part states, colour tween maps, and tween records.
- Complete staged layout and renderer resolution reconstruction for every
  transient scene identity.
- Per cell rendered part records and matrices for every full sync.
- Every pointer move enters the command path, even when the snapped value has
  not changed. Semantic no ops are rejected before store update
  (`src/components/ui/scrub-field/ScrubField.tsx:72-85`,
  `src/state/actions/authoredReducer.ts:60-63`).

#### Verified retained structures and bounds

| Structure | Lifetime and bound |
|---|---|
| Active morph plan | One active transition (`src/transport/activeTransitionPlan.ts:29-60`). |
| Stable grid layout | One current staged layout, with pose reference reuse (`src/scene/useStableGridLayout.ts:5-21`). |
| Incremental renderer owner | One current owner state. Full sync replaces the previous state (`src/scene/useCubeSceneInstances.ts:25-30`, `src/scene/incrementalCubeSceneOwner.ts:94-108`). |
| Authored scene journal | At most 32 entries, normally acknowledged after render (`src/state/authoredSceneJournal.ts:3-57`, `src/state/useAcceptedAuthoredSceneChanges.ts:10-15`). |
| Selection matrix cache | Current cell IDs that have chrome; missing IDs are deleted (`src/scene/SelectionChromeLayer.tsx:35-48`). |
| GPU instance buffers | Largest observed bucket capacity rounded to a power of two for the mount. Capacity does not shrink (`src/scene/InstancedPartMesh.tsx:58-87`, `src/scene/instancedMeshCapacity.ts:1-19`). |

Within the inspected evaluation and rendering scope, I found no container whose
size is keyed by the cumulative frame count or transition edit count. This is
a bounded static observation. It does not establish a process memory plateau.

**UNVERIFIED:** whether sustained evaluator and renderer churn outpaces garbage
collection in the live scene, whether Three.js or the browser retains resources
outside these TypeScript owners, and whether a worker clone fails because it
cannot obtain a contiguous allocation under that pressure. The live OOM
remains authoritative. A heap allocation timeline with forced collection is
required before any leak or plateau verdict.

The authored dispatcher and durability boundary were only followed far enough
to identify synchronous update behavior. Outbox, worker, clone, and storage
retention were not investigated because another seat owns persistence.

### 4. Control event rate and rebuilds

The transition controls have no evaluation coalescing:

- Pointer scrubbing installs a raw `window.pointermove` listener. Every move
  calls `changeValue`, requests a render pulse, and invokes the transition
  callback synchronously (`src/components/ui/scrub-field/ScrubField.tsx:52-55`,
  `src/components/ui/scrub-field/ScrubField.tsx:65-95`).
- Values change once per four horizontal pixels because the control truncates
  `deltaPx / 4` to a step (`src/components/ui/scrub-field/ScrubField.tsx:32-33`,
  `src/components/ui/scrub-field/scrubValue.ts:8-16`). Repeated moves within
  the same step still dispatch, but the semantic no op is rejected. Each
  distinct value is accepted and invalidates the plan. The next stage render
  prepares it and enters the full renderer sync path.
- Arrow key and wheel events each call `changeValue` directly
  (`src/components/ui/scrub-field/ScrubField.tsx:107-125`).
- Numeric text keystrokes update only local draft text. The authored change
  occurs once on blur or Enter (`src/components/ui/scrub-field/ScrubField.tsx:57-63`,
  `src/components/ui/scrub-field/ScrubField.tsx:130-146`).
- The render scheduler combines queued invalidations into a microtask
  (`src/scene/renderScheduler.ts:17-31`), but it does not combine authored
  operations or transition plan preparations.
- History batching records only the first undo snapshot during one pointer
  scrub (`src/state/actions/historyCoordinator.ts:13-45`). It does not batch
  the state updates or evaluation work.

Full rebuilds therefore occur per distinct accepted value rather than per raw
pointer event. The application has no event to event update coalescer.
**UNVERIFIED:** whether React scheduling skips intermediate visual commits when
events arrive faster than rendering.

The inspector sends each patch through a synchronous document command
(`src/panels/motion/MotionInspector.tsx:267-283`,
`src/interaction/commands/document.commands.ts:8-21`). The authored reducer
explicitly keeps playback running for `patch-transition`
(`src/state/actions/authoredReducer.ts:292-303`). Rapid edits therefore add
accepted state updates and rebuilds while the frame driver continues.

### 5. Auto loop owner and modal behavior

The loop is driven by the Three renderer:

1. While transport is playing, `EditorRendererBinding` mounts
   `TransportFrameDriver` with the Zustand store
   (`src/studios/editor/EditorRendererBinding.tsx:24-41`).
2. `TransportFrameDriver` runs `advanceScheduledTransportFrame` from R3F
   `useFrame` and keeps the playback render producer live
   (`src/transport/TransportFrameDriver.tsx:9-24`).
3. Each frame reads transport state, advances time, writes the next time into
   the store, and stops only when tick arithmetic returns `playing: false`
   (`src/transport/advanceTransportFrame.ts:9-28`).
4. Loop arithmetic wraps at the focused loop window or full duration and
   returns `playing: true` (`src/transport/advanceTransportTime.ts:29-51`).

The persistence failure UI does not stop that chain. It reads save state and
returns an alert dialog, with no transport read or pause action
(`src/app/PersistenceStatus.tsx:5-54`). The dialog is a fixed, full viewport
overlay above the panels (`src/app/persistence-status.css:17-25`).
`EditorStudio` uses save status only as a shell data attribute before rendering
the modal as a sibling (`src/studios/editor/EditorStudio.tsx:91-114`,
`src/studios/editor/EditorStudio.tsx:166-173`). The frame driver remains
mounted because its condition is transport playing, independent of save
status.

Verified answer: the auto loop continues behind either save failure modal.
The code contains no modal appearance effect that pauses or detaches transport.

## Proposals

### 1. Give ScrubField one interaction transaction

**Defect:** `ScrubField` makes its controlled display value, staged scene
preview, and durable document edit the same synchronous callback
(`src/components/ui/scrub-field/ScrubField.tsx:45-55`,
`src/components/ui/scrub-field/ScrubField.tsx:65-125`,
`src/panels/motion/MotionInspector.tsx:267-283`).

**Why it is wrong on its own terms:** A pointer drag is one user intent.
Intermediate positions are interaction state. Treating each position as an
authored transition change gives one gesture many persistence identities.
Pointer batching suppresses repeated history snapshots, but every accepted
value still enters the authored
dispatcher (`src/state/actions/historyCoordinator.ts:13-45`,
`src/state/actions/authoredDispatcher.ts:76-103`). The cross-seat measurement
found that one Duration ArrowUp fans out to four project-scale clones. This
seat verified the synchronous dispatch path but did not repeat that heap
measurement.

Current Undo behavior is verified from the code:

- For the transition controls in `MorphInspector`, a 60-pointermove drag
  produces one history entry, not 60. The inspector passes
  `beginHistoryBatch` and `endHistoryBatch`
  (`src/panels/motion/MorphInspector.tsx:73-88`,
  `src/panels/motion/MorphInspector.tsx:112-139`). Pointer down opens the batch
  and pointer up closes it
  (`src/components/ui/scrub-field/ScrubField.tsx:65-95`). The history
  coordinator records the first accepted edit and returns the existing history
  for every later edit while the batch is active
  (`src/state/actions/historyCoordinator.ts:13-45`). One Undo therefore returns
  to the value from before the drag.
- Arrow input never calls those start or end callbacks
  (`src/components/ui/scrub-field/ScrubField.tsx:107-120`). Every accepted
  Arrow keydown, including each native held-key repeat, records another history
  entry. A single tap creates one entry. A held key creates one entry per
  accepted repeated value, so Undo walks backward through the intermediate
  values. Proposal 2 treats that as a separate correctness defect.

The three values have these owners today:

1. The displayed value is the committed `value` prop rendered by
   `ScrubField` (`src/components/ui/scrub-field/ScrubField.tsx:35-46`,
   `src/components/ui/scrub-field/ScrubField.tsx:149-159`).
2. There is no separate scene-preview owner. Each `onValueChange` immediately
   creates an authored transition patch, and `useStagedScene` then samples the
   changed Workbench (`src/panels/motion/MorphInspector.tsx:73-139`,
   `src/transport/useStagedScene.ts:126-144`).
3. The same callback is the committed edit. It reaches document history,
   outbox, and durability through the authored dispatcher
   (`src/interaction/commands/document.commands.ts:8-21`,
   `src/state/actions/authoredDispatcher.ts:76-103`).

**Minimal fix:** Replace the shared `ScrubField` callback contract with distinct
preview, commit, and cancel phases.

- On pointer down, capture the committed value. On every pointer move, update a
  local displayed value synchronously. The numeric label therefore tracks the
  pointer in the same event with no visible delay.
- Queue the latest preview value in the existing interaction intent bus. Extend
  `createIntentBus` with a keyed control frame lane, parallel to its existing
  view frame lane, and drain it from the existing `resolveFrame` owner
  (`src/interaction/bus.ts:21-60`,
  `src/interaction/interactionCore.ts:119-141`). The render scheduler continues
  to request the frame. It does not become a second state queue
  (`src/scene/renderScheduler.ts:12-64`).
- Publish at most one transient scene preview per rendered frame into a
  session-only control preview read by the existing stage adapter. The stage is
  at most one display frame behind the pointer. There is no debounce, interval,
  or extra animation duration.
- On pointer up, flush the exact final pointer value, clear the transient
  preview, and dispatch one authored operation. History and persistence are
  touched exactly once.
- On pointer cancel or Escape, discard the pending frame value, clear the
  transient preview, restore the captured value in the label immediately, and
  dispatch no authored operation.

Reuse the existing history batch as the single authored gesture boundary.
Pointer down begins it, pointer up dispatches the one final authored operation
and then ends it, and cancellation ends it without an operation. The
persistence queue receives the same single operation that history records.
There is no independent persistence collapser, debounce, or delayed queue in
this proposal. If the boundary is renamed to an authored gesture transaction,
refactor `createHistoryCoordinator`; do not leave the old batch and a new
transaction owner in parallel.

The existing active-drag Escape machinery does not currently reach
`ScrubField`. `createPanelDragCapabilityModel` owns one registered cancel
handler, and `PanelDragCapabilityRoot` supplies the DnD handler
(`src/studios/editor/usePanelDragCapability.ts:65-79`,
`src/capabilities/panel-drag/PanelDragCapabilityRoot.tsx:41-49`).
`KeyboardShortcuts` already gives that owner first refusal on Escape
(`src/editor/keyboard/KeyboardShortcuts.tsx:20-27`). Extract that existing
singleton into a composition-level active interaction cancellation owner.
Panel DnD, panel resize, and `ScrubField` claim it only for their active
gesture. Preserve the existing rejection of a second simultaneous owner. This
reuses the Escape route rather than adding another document listener.

The keyboard rule is one commit per physical key hold. The initial Arrow
keydown and native repeat keydowns update the local display immediately and
queue frame previews. The matching keyup commits the final value once. Window
blur commits the visible final value, while Escape cancels and restores the
captured value. Native repeat and keyup provide the boundary, so no repeat
window or timer is needed. A single key tap is therefore one commit, and a held
key remains one undo step.

Wheel input has no reliable release event. Keep it discrete: fold wheel deltas
already received before the next intent-bus drain and commit that aggregate
once in that frame. This bounds wheel commits to the display cadence without a
debounce.

This contract belongs to every drag-to-change `ScrubField`, not only transition
duration. The pinned tree has 22 `ScrubField` call sites and one shared
implementation. No parallel durable numeric drag component was found. The two
range inputs are already transient transport or comparison controls
(`src/panels/motion/TransportPlayhead.tsx:102-119`,
`src/panels/motion/MotionInspector.tsx:219-233`). Panel resize already
demonstrates the correct preview-then-commit transaction and should supply the
gesture pattern (`src/app/panelResize.ts:72-112`).

Move the existing `scrubPixelsPerStep` and `scrubClickToleranceDx` values from
the component into `src/config/cubicellConfig.ts`. Frame cadence comes from the
renderer, and keyboard cadence comes from native repeat. No new hardcoded feel
constant is required (`src/components/ui/scrub-field/ScrubField.tsx:32-33`,
`src/config/cubicellConfig.ts:48-80`).

**Elegant fix:** Add one `ControlGesture` port to the existing command
infrastructure with `begin`, keyed `preview`, `commit`, and `cancel`. The intent
bus retains only the latest preview per control until `resolveFrame`.
Session-owned preview operations are applied by the sole Workbench-to-stage
adapter, while commit invokes the current authored command once. `ScrubField`
then owns only local display and gesture events. Pointer, keyboard, wheel, and
text entry share one semantic lifecycle. The current `morphScrub` field should
not be reused directly because it means saved-state comparison and deliberately
stops playback (`src/state/actions/transportActions.ts:35-60`). Refactor the
session staging seam to host both comparison and control preview without
duplicating `useStagedScene`.

**Blast radius:** All 22 `ScrubField` callers migrate to the new phase contract.
Authored controls gain one undo and persistence event per gesture. Session and
preference controls gain the same displayed/previewed/committed semantics.
`MotionInspector`, the editor command lane classification, the interaction bus,
the editor session type, and `useStagedScene` change. The visible value remains
live on every input event, the canvas follows on the next available frame, and
release settles the exact final value with no added visual lag.

**Recommendation:** Ship the elegant fix. The shared transaction removes the
highest fan-out work before it reaches evaluation or persistence, fixes
keyboard history at the same boundary, and prevents a transition-only
exception from becoming a second input system.

### 2. Make keyboard scrubbing one undoable gesture

**Defect:** Arrow scrubbing calls `onValueChange` on every keydown and repeat
without invoking the history batch callbacks, so a held key creates an undo
entry for every accepted intermediate value
(`src/components/ui/scrub-field/ScrubField.tsx:107-120`,
`src/state/actions/historyCoordinator.ts:26-45`).

**Why it is wrong on its own terms:** After one continuous held-key gesture,
Undo should return to the value visible before the hold. Current Undo steps
through every repeated midpoint. This is a user-visible correctness defect
independent of the OOM crash.

**Minimal fix:** Reuse the existing `onScrubStart` and `onScrubEnd` boundary.
The first handled Arrow keydown begins the batch. Native repeat keydowns remain
inside it. The matching keyup ends it. Window blur ends the active batch so a
lost keyup cannot leave history batching armed. This makes the current
per-repeat authored edits collapse into one history entry without adding a
second history mechanism.

**Elegant fix:** Resolve the defect through Proposal 1. Keydown starts the
shared control gesture, initial and repeat keydowns update the live label and
frame preview, and matching keyup sends one final authored operation through
the same history transaction used by pointer release. Window blur commits the
visible final value. Escape cancels and restores the captured value. No
key-repeat timeout or debounce is introduced.

**Blast radius:** `ScrubField` gains keyup, blur, and active-key lifecycle
coverage. Existing callers keep one history boundary. A single Arrow tap
remains one undo step. A held Arrow becomes one undo step and one durable edit
under the elegant path. The displayed value still changes on every native
repeat and the canvas follows at most one rendered frame later.

**Recommendation:** Ship the elegant fix with Proposal 1. The minimal fix
repairs Undo but leaves repeated authored writes, plan invalidations, and
persistence work in place.

### 3. Split endpoint topology from the active settings schedule

**Defect:** The one-entry active transition cache keys the complete morph plan
by endpoint revisions and settings, so every distinct control preview discards
endpoint classification and shared-edge planning that the edit cannot change
(`src/transport/activeTransitionPlan.ts:29-60`,
`src/evaluation/sceneMorph.ts:61-107`).

**Why it is wrong on its own terms:** Added, removed, changed, ink, and shared
edge membership are endpoint facts. Duration, easing, quantization, cut, order,
and stagger are scheduling facts. Reclassifying endpoint topology after a
duration step violates that boundary even when memory is plentiful.

**Minimal fix:** Refactor `prepareSceneMorph` into:

1. `prepareSceneMorphTopology(a, b)`, which owns endpoint maps, membership sets,
   ink classification, and shared-edge claims.
2. `prepareSceneMorphSchedule(topology, settings)`, which owns the three class
   motions and their start maps.

Keep the existing cache owner and its one-entry bound. The topology key is the
ordered `(fromRevision, toRevision)` tuple. It retains exactly one active
endpoint pair. The schedule key is that active pair plus normalized morph
settings, and it retains exactly one current schedule. Sample time remains
excluded. A settings edit replaces only the schedule. An endpoint revision
change replaces both. A cut or inactive stage clears both. There is no LRU and
no second cache.

**Elegant fix:** Make the topology and schedule explicit immutable inputs to
one `ActiveSceneMorphRuntime`. The runtime owns the single active pair,
replans the cheap schedule on preview, and exposes the same sampled result
contract. This makes the cache bound part of the type instead of a closure
convention.

**Blast radius:** `SceneMorphPlan`, `prepareSceneMorph`, its direct tests, and
`createActiveTransitionPlanCache` change. Callers keep one plan-cache instance
and the sample API can remain stable. Users see identical timing and easing.
Rapid control previews stop rescanning every cell and shared edge.

**Recommendation:** Ship the minimal fix with the ScrubField transaction. It is
small, has a precise one-entry bound, and removes endpoint work from every
frame-coalesced settings preview.

### 4. Retain render slots across transient morph frames

**Defect:** Every interior morph sample creates a new scene graph, and the
incremental renderer interprets that transient identity as a reason to recreate
its complete owner, indexes, packed instances, and slot registry
(`src/evaluation/sceneMorph.ts:127-227`,
`src/scene/incrementalCubeSceneOwner.ts:111-180`).

**Why it is wrong on its own terms:** The incremental renderer already owns
stable keyed slots. A sampled frame from the same active endpoint pair changes
presentation values, not renderer ownership. Replacing the slot owner on each
frame defeats its identity contract independently of an OOM.

**Minimal fix:** Add an unjournaled transient full-sync branch inside the
existing `IncrementalCubeSceneOwner`. When the authored journal sequence is
unchanged but the staged input identity changes, update the current render
resolution with its existing full-scene update path, rederive the union of old
and new cell IDs, and apply those cell instances through the existing slot
owner (`src/domain/incrementalCubeRenderResolution.ts:98-129`,
`src/scene/cubeInstanceSlots.ts:104-125`). Preserve the slot registry and
instanced mesh capacities. A journal gap still creates a fresh owner because
its lineage is unknown. This removes owner and slot replacement, though it
still performs full cell and resolution work per transient frame.

**Elegant fix:** Let the active morph runtime allocate the union of endpoint
slots once when the ordered endpoint key changes. Each frame should emit
presence, transform, material, and discrete-cut channels directly into those
retained slots. Added and removed cells already belong to the union, so
interior frames overwrite matrices, colors, and opacity without constructing a
new `CubicellScene`, cell graph, layout index, or slot registry. Reuse
`SceneMorphPlan` classification, shared-edge planning,
`CubeInstanceSlotOwner`, and the existing instanced mesh buffers. Authored
scenes remain immutable.

The right runtime bound is one active ordered endpoint pair and its union
slots. Starting another transition replaces it. Reaching an authored endpoint
or leaving staged playback releases it. There is no frame-counted retention
and no multi-transition cache.

**Blast radius:** The minimal path is confined to
`incrementalCubeSceneOwner`, its render metrics, and owner tests. The elegant
path changes the evaluation-to-renderer contract, `useStagedScene`,
`CubeScene`, and instance update tests. The frame shown at each transport time
is unchanged. Work is removed from the same frame rather than deferred, so
there is no input or animation lag.

**Recommendation:** Use the minimal slot-retention fix as an immediate
containment, then implement the elegant runtime. The minimal change removes a
large owner allocation with existing primitives. The runtime is required to
remove the dominant per-cell and per-part frame churn.

### 5. Pause transport when persistence blocks the editor

**Defect:** A persistence failure mounts a blocking alert dialog while the
renderer continues advancing a looping transport behind it
(`src/app/PersistenceStatus.tsx:5-54`,
`src/studios/editor/EditorRendererBinding.tsx:24-41`).

**Why it is wrong on its own terms:** A modal that blocks recovery decisions
should freeze hidden session progress. Continuing playback changes the
playhead while the user cannot interact with the stage and makes retry or
recovery return to an unseen time.

**Minimal fix:** At the `EditorApp` composition boundary, where save status and
transport controls are both available, call the existing
`setTransportPlaying(false)` action when status first enters `failed` or
`recovery-failed`. The final visible frame remains on screen and the playback
producer releases through its current unmount path
(`src/studios/editor/EditorStudio.tsx:72-117`,
`src/transport/TransportFrameDriver.tsx:17-24`). Keep this policy out of the
persistence queue and out of the presentational dialog.

**Elegant fix:** Derive one editor blocking policy at the composition root and
use it to gate interaction, transport liveness, and modal presentation. The
policy should invoke existing owners rather than teach persistence about
renderer state.

**Blast radius:** `EditorStudio` gains one blocking-state policy and a focused
test. No persistence queue contract changes. When the modal appears, users see
the stage and playhead freeze immediately. Retry does not resume automatically;
the user explicitly presses Play.

**Recommendation:** Ship the minimal fix. It is a low-cost safety backstop for
the crash path, while the first three proposals remove the work that leads to
the failure.

### Ranked order

Scores use 1 to 5 scales. Crash impact and confidence increase the score; cost
increases from 1 for the smallest change to 5 for the largest. The final value
is `(crash impact × confidence) / cost`.

| Rank | Proposal | Impact | Confidence | Cost | Score |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | Shared ScrubField interaction transaction | 5 | 5 | 3 | 8.33 |
| 2 | Split endpoint topology from settings schedule | 3 | 5 | 2 | 7.50 |
| 3 | Retain render slots across transient morph frames | 5 | 5 | 4 | 6.25 |
| 4 | Make keyboard scrubbing one undoable gesture | 2 | 5 | 2 | 5.00 |
| 5 | Pause transport for a blocking persistence modal | 1 | 4 | 1 | 4.00 |

Ship the shared ScrubField interaction transaction first. It removes raw input
fan-out before the evaluator and persistence boundary, fixes keyboard history,
and establishes the preview contract required by the cache and renderer work.
Persistence queue changes are intentionally excluded because that queue belongs
to the other seat.
