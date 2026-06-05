# Cubicell Direction Audit

Audit agent 1 of 4. Baseline: `main` @ `71098b4`, clean checkout, 2026-07-29.
Sources: the full repo doc set, forward declarations on `main`, the unmerged
branches `feat/typography-domain` and `feat/llm-control` (plus its worktree at
`.claude/worktree/llm-control`, ~80 uncommitted files), and named-but-unbuilt
domain vocabulary. Read-only; no builds run.

## Target Capabilities

Legend: COMMITTED = a doc says it will happen (locked, approved, or planned in
phases). PRESERVED = a route is deliberately kept open. IMPLIED = the code
reaches for it without a doc commitment at that strength.

### 1. Recursive composition: Piece, Placement, Cue, nested grids
- Source: STUDIO.ANIMATION.md ("North star": Stage → Piece → Grid → Cell →
  Placement → Piece recursion; "Recursive composition model"; "First vertical
  slice"), ARCHITECTURE.md "Scene Model Direction" ("The next architectural
  move is to separate `Grid`, `Cell`, and `CellContent`"), CUBICELL.md
  ("A cell can eventually contain another grid, which makes Cubicell recursive
  by design").
- Status: COMMITTED as direction (ARCHITECTURE names it "the next
  architectural move"); the mechanics (Cue timing, containment semantics) are
  proposal-status with recommended defaults.
- Demand: replaces the flat `CubeCell[]` document with grid/cell/content
  records, splits local ids from instance paths across selection, history,
  hit-testing, and score addressing, adds a recursive time-mapping evaluator,
  and forces the incremental instancing layer to flatten a transform chain.

### 2. Three-space studio: Browser, Editor, Animation Studio
- Source: STUDIO.PROJECT.md "Spaces and navigation (locked)", "Tabs (locked)",
  "Editor: the State lifecycle (locked)".
- Status: COMMITTED (explicitly marked locked).
- Reality on main: `src/studios/catalogData.ts` declares exactly two studios,
  `editor` and `design-system`. No Browser, no Animation Studio, no tab bar,
  no multi-asset open/rehydrate lifecycle.
- Demand: multi-document runtime with one live canvas, auto-save on tab
  switch, per-user session state, and asset routing; the current app is a
  single-document editor composition (`src/app/App.tsx`).

### 3. Animation Studio composition layer: PieceSnapshot, Placement, StageScore with CueTrack, three-way staleness merge
- Source: STUDIO.ANIMATION.md "Studio today (2026-07-14)" and "Piece motion
  and reuse (2026-07-15)", both recorded as approved by consensus, with an
  explicit wire-version bump; ANIMATION.md primitives (Cue "is a target
  primitive and is not persisted yet").
- Status: COMMITTED (consensus-approved contract changes).
- Reality on main: `src/domain/score.ts` comments "`CueTrack` arrives with
  Studio composition"; `StageTrack = CameraTrack` is the entire stage union.
  No PieceSnapshot, Placement, Cue, or VariantPatch type exists anywhere in
  `src`. `Workbench.library.animations` exists with codecs but no UI creates
  an AnimationAsset.
- Demand: new asset document shape, pose-revision reachability GC, snapshot
  provenance and the considered three-way merge (geometry/motion/roster),
  which the doc itself notes the shipped `repairStateTransitionTrack` cannot
  do.

### 4. Cinematic camera channel model
- Source: CAMERA.md (entire doc: 7-channel keyframe with `CameraFraming`
  pair, `rigTranslation`, `lock-target-height` derived lens route, placement
  target binding, `moveId` named moves), recorded as settled by consensus;
  ANIMATION.md ("the cinematic channel migration in CAMERA.md is pending").
- Status: COMMITTED.
- Reality on main: zero occurrences of `CameraFraming`, `rigTranslation`,
  `lock-target-height`, `perspectiveMagnification`, `orthographicHeight`, or
  `moveId` in `src`. The shipped `src/domain/cameraTrack.ts` is a two-channel
  (pose + projection) segment model. Migration is a wire bump and a full
  evaluator replacement.
- Demand: per-channel segments and validation, run-invariants for locked lens
  chains, placement binding (depends on capability 3's Placement existing).

### 5. Camera track playback and authoring activation (currently dark machinery)
- Source: ANIMATION.md and INTERACTIVE.md ("transport camera possession is
  shipped"); code.
- Status: IMPLIED, strongly. The possession runtime (`track` pose mode,
  `cameraTrackAuthority`, `syncCameraTrackFrame`, rearm epochs,
  projection-follow detach) is fully wired through the camera authority and
  frame writer, and the authoring surface `src/studio/CameraTrackControls.tsx`
  is exported and test-covered. But no production code mounts
  `CameraTrackControls`, and no production caller ever passes a non-null
  `cameraTrack` into `src/scene/CubeScene.tsx` (only tests do). The entire
  subsystem is unreachable by a user on main.
- Demand: an Animation Studio surface to host it (capability 2/3); until then
  it is preserved weight in the camera layer.

### 6. Hosted persistence, then live collaboration
- Source: STORAGE.md (canonical plan; phases 2 "hosted persistence", 3 "v1
  hardening", 4 "live collaboration when selected"; commit protocol, RLS,
  membership tables from first migration); STUDIO.PROJECT.md Persistence
  (decided); LESSONS.md ("every persistence and domain boundary must preserve
  a direct path to it").
- Status: hosted persistence COMMITTED (Supabase named as the provider, exact
  Postgres shape specified); live collaboration PRESERVED (explicitly
  deferred, but stable IDs, operations, revisions, membership, and state
  separation ship in V1 so adding it "does not replace the persistence
  model").
- Reality: Phase 1 (local durability) is complete on main. "The remaining
  gaps are hosted concerns: no Supabase schema, synchronization worker,
  membership policy, multiuser merge policy, or live conflict surface exists."
- Demand: a sync worker, idempotent commit RPC, checkpoint replay, conflict
  recovery UI; the local outbox and forward rebase were built to feed it.

### 7. Deterministic export pipeline
- Source: PROJECT.EXPORT.md (status: Proposed; performance takes, frozen
  `ExportJob`, integer frame-index clock, renderer boundary extraction,
  worker/process runners); ANIMATION.md ("a deterministic fixed-step export
  time source ... [is] future work", repeated); ANIMATION.KNOBS.md (fixed-step
  clock `[near]`, "the named prerequisite for honest export").
- Status: COMMITTED for fixed-step determinism and the take-then-compile
  model (multiple docs treat it as the known destination); PRESERVED for
  worker/process/remote isolation (explicitly staged, entered only on
  evidence).
- Reality: only live `MediaRecorder` capture exists
  (`src/export/streamRecorder.ts`); transport advances by wall clock.
- Demand: the renderer boundary extraction is the hard part: rendering must
  accept plain immutable data with no dependency on editor stores, DOM
  events, or live camera authority. That is an architectural seam the current
  R3F composition does not have.

### 8. Typography as a semantic geometry source
- Source: TYPOGRAPHY.md (initial proposal: `GeometrySource` replacing
  Pose-owns-cells, provenance sidecar, semantic identity, four-phase
  delivery); CUBICELL.md "Text And Words" ("Spelling words is a core use
  case"); unmerged branch `feat/typography-domain` (2 commits: a complete
  deterministic pixel-font text domain in `src/domain/typography.ts` with
  `GeometrySource`, `TextSource`, provenance, `convertTextSourceToLiteral`,
  plus an interactive `TextComposer` surface and 500+ lines of tests).
- Status: IMPLIED at implementation strength (the branch built Phase 1's
  core), COMMITTED only as product intent (the doc marks architecture "open
  for design review"; a Context Matters preference requires curves/rounded
  geometry be preserved).
- Demand: breaks the assumption that a Pose directly owns cells; introduces
  semantic (non-coordinate-derived) generated identity, which collides with
  today's coordinate-derived id + rename-map machinery.

### 9. LLM as a first-class (eventually primary) user
- Source: INTERACTIVE.md founding observation ("A human at a keyboard and an
  LLM issuing calls are the same thing"); LLMDRIVES.md (status: active
  direction; "Implementation decision" commits the next repository change to
  `src/control`); MODEL.v2.md system thesis; unmerged branch
  `feat/llm-control` (3 commits, ~8,000 lines: `src/control` service, runtime
  schemas, studio bridge server/client, MCP server + tools, browser control)
  plus its worktree with ~80 further uncommitted files extending control into
  authoring (`studioAuthor`, `studioState`, `studioStateWorkflow`,
  `studioPlayback`) and LLM showcase scenarios (soma cube, kinetic braid,
  state bloom).
- Status: COMMITTED as direction, IMPLIED at implementation strength by the
  largest single unmerged investment in the repo.
- Demand: runtime command schemas and discovery, a semantic scene read model
  the snapshot does not yet carry, per-command terminal fate for view
  commands, actor lifecycle (idempotent request ids, leases), and, hardest,
  full command coverage: neighbor placement, build visibility, grid composer
  rebuilds, preferences, and the transport clock still bypass the command
  bus, which LLMDRIVES lists as a gap.

### 10. Per-edge shaping: sharp, round, chamfer with shapeSize
- Source: the approved negative-space tooling design
  (docs/superpowers/specs/2026-07-12-negative-space-tooling-design.md, and
  the approval recorded in TYPOGRAPHY.md's Context Matters table);
  TYPOGRAPHY.md notes "The approved `treatment` and `shapeSize` fields remain
  absent"; CUBICELL.md "The Atom" lists rounding as a later property.
- Status: COMMITTED (approved decision), unbuilt: zero occurrences of
  `CubeEdgeTreatment`, `treatment`, or `shapeSize` in `src`.
- Demand: geometry variants per edge inside the instancing model, whose
  worst case (every cell a distinct shaping signature) is already named as a
  benchmark scenario.

### 11. Property tracks, modulators, order generators, fields
- Source: ANIMATION.md (Track primitive: "`PropertyTrack` for per-cube
  offsets and kinetic loops is a future kind"); ANIMATION.KNOBS.md (the
  catalog, explicitly "an orientation map for prioritization, not a
  commitment"; fields are "`[far]` first true new evaluator concept").
- Status: PropertyTrack PRESERVED (named as a future track kind in the
  contract); the wider knob catalog IMPLIED-to-aspirational.
- Demand: generalizes the `Moment` overlay beyond presence + color tweens;
  evaluator-only wins (order generators, disassembly, quantize) need no new
  document shape and are the cheapest band.

### 12. Performance surface (VJ): clip launcher, tempo, MIDI, audio
- Source: docs/superpowers/plans/2026-07-11-vj-performance.md,
  ANIMATION.KNOBS.md section 8, CUBICELL.md "Big Bet" ("performable, not only
  edited"), PRODUCT.md ("musical").
- Status: PRESERVED. The bet is core identity; the surface is all `[far]`.
- Demand: quantized cue launch and low-latency trigger routing on top of the
  transport and score model.

### 13. Seam surfaces and edit-gesture pointer claims (parked, deliberately)
- Source: ARCHITECTURE.md "Current Feature Status" (seam geometry exists,
  `seamSurfacesEnabled` is `false` in `src/config/cubicellConfig.ts`; parked
  for interaction noise); "Canvas Input Policy" names
  `src/interaction/editPointerClaim.ts` as "the infrastructure for seam drags
  and future edge scrubs".
- Status: PRESERVED. Code confirms: the suppression side (`claimEditPointer`
  subscribers in wheel zoom, pan, gesture runtime) is live, and no production
  caller ever claims the pointer.
- Demand: a redesigned seam hit model before unparking.

### 14. Asset browser forward declarations
- Source: `src/thumbnail/assetPoster.ts` exports `resolveAssetPosterState`
  and `resolveAssetThumbnailSet`; both are exported through the barrel and
  test-covered (`tests/thumbnailAssetPoster.test.ts`); no production consumer
  outside the thumbnail home. The Browser space (capability 2) is the natural
  consumer.
- Status: IMPLIED.

### 15. View-relative selection queries
- Source: CUBICELL.md "Query frame of reference": future visible-from-camera,
  occluded, silhouette, screen-region queries "must receive the current
  camera pose and projection mode", with an explicit Selector design decision
  reserved.
- Status: PRESERVED.
- Demand: the selection evaluator gains a camera context port it deliberately
  does not have today.

### 16. Extended export formats and delivery
- Source: CUBICELL.md "Export Path" (image sequence, ffmpeg video, GLB/glTF;
  Lottie ruled out); ANIMATION.KNOBS.md (SVG frame and sequence export
  `[far]`, "almost no motion tool offers it"; loop-perfect capture);
  STORAGE.md (Supabase Storage for retained binary output).
- Status: PRESERVED.

### 17. Remaining performance program
- Source: PERFORMANCE.md delivery order 3-8: GPU capacity growth, demand
  driven rendering, playback derivation, initial delivery to a 3.0 s
  committed frame, production hardening (error boundary, WebGL context loss,
  CI).
- Status: COMMITTED (canonical plan with acceptance gates; slices 0-4 landed
  via the perf/* branches).

## Load-Bearing Capability

**Recursive composition (capability 1), with the Animation Studio stack
(capabilities 2-3) as its immediate cargo.**

It is load-bearing because it invalidates the one assumption the current
architecture is most optimized around: one flat grid of coordinate-addressed
cells. The hardest-won machinery on main is built against that assumption:

- Coordinate-derived cube ids with rename-map score repair
  (`src/domain/lattice.ts`, `repairScore`) assume one namespace; recursion
  requires local ids plus instance paths, and reuse makes the same local id
  appear many times (STUDIO.ANIMATION.md "Identity and paths").
- The incremental scene owner and stable GPU slot system
  (`src/scene/incrementalCubeSceneOwner.ts` and peers), the P0 rescue that
  made one-cell edits cheap at 2,025 cells, derives from a flat cell list;
  a placement transform chain and per-piece local time invalidate its
  derivation keys.
- Evaluation is a flat `Moment` keyed by cube id
  (`src/evaluation/scoreAt.ts`); recursion needs cue time mapping and
  transform composition per placement.
- Persistence just finished restructuring around Structure/Animation assets
  and immutable pose revisions; PieceSnapshot, Placement, and the three-way
  merge change the asset document shape again (an acknowledged wire bump).

Every other major target either stands on it (Cue and CueTrack, placement
canon, the camera model's placement-bound targets in CAMERA.md, typography's
multiple live sources, which TYPOGRAPHY.md explicitly routes "through Piece
and Placement composition") or is orthogonal to it (hosted sync, export
determinism, LLM boundary). The LLM direction is the biggest investment by
line count, but it is additive at the boundary: it wraps the existing command
core rather than reshaping the document. Recursion reshapes the document,
identity, evaluation, rendering, and persistence at once. If the current
shape forecloses anything, it forecloses this.

## Doc Contradictions

1. **Camera track "shipped" versus dark.** ANIMATION.md ("The `CameraTrack`
   and its transport possession are shipped"), INTERACTIVE.md ("transport
   camera possession is shipped"), and STUDIO.ANIMATION.md ("a real camera
   track" shipped) conflict with MODEL.v2.md ("The authored data type exists;
   no runtime producer or evaluator drives it yet"). Code sides with
   MODEL.v2 for the user-facing claim: the possession runtime is wired, but
   `CameraTrackControls` is unmounted and no production caller passes a
   non-null `cameraTrack` to `CubeScene`. Three docs describe machinery as
   shipped that no user can reach. This is the largest direction risk in the
   doc set because a reader planning the Animation Studio would believe the
   camera lane already works end to end.
2. **PROJECT.EXPORT.md references `src/evaluation/cameraTrack.ts`**, which
   does not exist (evaluation contains `scoreAt`, `sceneMorph`,
   `sceneTransition`, `pieceAt`, `sharedEdgeTweens`, `index`). Stale
   reference in a Proposed doc's authority list.
3. **PERFORMANCE.md Maintainability** says `src/panels/panels.css` "is 796
   lines and exceeds the repository limit"; it is 337 lines on main. Stale in
   a doc dated canonical 2026-07-23.
4. **README.md** still opens with "React Three Fiber playground for
   experimenting with cubes", contradicting PRODUCT.md's "grid based motion
   studio". The front door undersells the committed identity.
5. **Snapshot drift, disclosed:** ARCHITECTURE.md and MODEL.v2.md pin
   themselves to `61b135a` (2026-07-23) while main is at `71098b4`; the five
   merged PRs since (#135-#139) are perf/persistence work, so no direction
   claims are invalidated, but the "current state" docs are point-in-time by
   design and already six days behind.
6. **STUDIO.PROJECT.md locked spaces versus the studio catalog.** Not a lie
   (the doc is a decision record, not a status claim), but a reader must
   cross-reference code to learn that of the three locked spaces only the
   Editor exists, and that the second registered studio is `design-system`,
   a space the product docs never mention.

## Stated Scale

Stated numbers, quoted:

- Cells: "A 4,500 cube active asset must save and restore exactly"
  (STORAGE.md performance budgets; PERFORMANCE.md gates the same figure in
  real Chromium). Render and playback gates use 250 and 2,025 cube
  scenarios; "Playback at 2,025 cells maintains p95 frame time at or below
  16.7 ms on the reference machine" (PERFORMANCE.md).
- Latency and delivery: "no main thread task above 50 ms" for persistence
  (STORAGE.md), 100 ms task ceiling at load, 2.5 s loading-indicator LCP,
  3.0 s committed frame, 350 KB gzip editor JavaScript (PERFORMANCE.md).
- Recording: the recorder "retains at most 256 MiB" (PERFORMANCE.md).
- Concurrency: "V1 supports one active writer per asset" (STORAGE.md
  Decision 9). Multiple tabs and stale devices are recovery scenarios, not
  concurrency. Roles (owner/editor/viewer) are schema-reserved; "The Editor
  role is reserved in the schema and remains unassigned in V1."

Not stated anywhere, and the absence is the finding:

- No number for projects per user, assets per project, or states per
  structure.
- No number for recursion depth, pieces per stage, or placements per piece,
  even though recursion is the north star and STUDIO.ANIMATION.md discusses
  "deeper nesting levels" only qualitatively.
- No maximum text cell count; TYPOGRAPHY.md lists "What maximum cell count
  keeps editing and capture within the existing performance contract?" as an
  open decision.
- No target for concurrent users post-collaboration; Phase 4 defers even the
  merge-algorithm decision until "observed same asset contention" exists.

The scale story is therefore: one user, one writer, one flat structure,
~2k cells interactive and ~4.5k cells durable, with every number above that
band undefined.

## Ceiling Or Bug

Three distinct patterns, worth separating because they answer "does the
architecture hit walls?" differently:

1. **Genuine ceilings hit, then removed by redesign (twice).**
   - Persistence: the 4,500 cube document (6,577,988 bytes) failed every
     localStorage quota tier silently (PERFORMANCE.md P0). The whole-document
     localStorage writer could not hold the stated target scale. The answer
     was an architecture replacement (STORAGE.md: IndexedDB, committed
     baseline plus client branches, worker projection), now complete.
   - Rendering: one cell edit resynchronized every instance (3.63 fps at
     2,025 cubes). The answer was again structural: the incremental scene
     owner, journal, and stable GPU slots.
   These were ceilings in the honest sense: the current shape could not reach
   the documented target, and incremental fixes were judged insufficient.
2. **Bugs fixed, not ceilings.** The OOM crash was traced to the commit
   projection shipping every referenced pose revision in each payload and
   fixed in #136 by roughly two orders of magnitude; the payload shape was
   wrong, the model was not. Same class: #135 (scrub gestures committing per
   event), #137 (morph topology reallocation), #138 (silent save recovery),
   #139 (eased-frame allocation churn). These are implementation defects the
   architecture absorbed without redesign.
3. **Known ceilings identified but not yet hit in anger.** GPU capacity
   recreation (adding one cube to 250 cost ~90 ms and five shader program
   recreations), the continuous render loop on a settled scene, per-frame
   `sampleSceneMorph` reconstruction, and the 1.5 MB entry bundle are all
   documented P1s with acceptance gates and no shipped fix.

The honest summary for the rebuild decision: the flat single-grid model has
already required two architecture-level rescues inside its stated 2k-4.5k
cell band, and the committed direction (recursion, typography, animation
composition) multiplies cell counts and adds transform depth on top of that
band with no stated scale target. The walls so far were hit in persistence
and rendering, not in the domain model; the domain-model wall is the one
recursion would test first, and nothing has measured it.
