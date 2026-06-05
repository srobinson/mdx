# Orbit-detent redesign: code primitives inventory

Facts only. Grounds orientation-space / slerp designs in what cubicell actually ships.
Scouted from HEAD `3b07878` (working tree at inventory time). Read-only.

---

## 1. ViewPose shape and orientation representation

### Type (`src/pose/viewPose.ts`)

```ts
export type ViewPose = {
  position: Vector3  // three.js
  target: Vector3
  up: Vector3
  zoom: number       // orthographic px/world-unit (canonical framing)
}
```

Snapshot twin for restore (plain tuples, not Vector3):

```ts
export type ViewPoseSnapshot = {
  position: Vec3
  target: Vec3
  up: Vec3
  zoom: number
}
```

Seed type (`src/pose/cameraState.ts`):

```ts
export type CameraState = {
  position: Vec3
  projection: ProjectionMode
  target: Vec3
  up: Vec3
  zoom: number
}
```

`createViewPoseFromCameraState` maps CameraState → ViewPose (Vector3 + normalized up).

### How orientation is represented today

**Not** a quaternion, euler, or matrix on the pose. Orientation is implicit:

| Derived quantity | Formula |
|---|---|
| Look / forward (toward target) | `normalize(target − position)` |
| Camera offset (target → eye) | `position − target`; unit form via `getViewOffsetDirection(position, target)` |
| Orbit distance | `position.distanceTo(target)` |
| Roll-ish component | residual freedom in `up` after looking at target (up is stored independently) |

Driver apply path (`applyViewPoseToCamera`): copies `position`, `up`, `zoom` (with projection conversion), then **`camera.lookAt(target)`**. Three.js `lookAt` rebuilds the camera basis from eye/target/up; the stored `up` is the up *hint*, not a free full SO(3) axis that can disagree with the look axis indefinitely.

### Quaternion derive / rebuild (feasibility — code does not do this for ViewPose today)

**Derive (possible with existing three.js):**

1. `forward = normalize(target − position)` (or opposite depending on convention)
2. Build a right-handed basis with stored `up` (same algebra as private `getViewPoseAxes`: `right = forward × up`, re-orthogonalize up = `right × forward`)
3. `Matrix4.makeBasis(right, up, ±forward)` then `Quaternion.setFromRotationMatrix`
4. Or use three's camera: set position/up, `lookAt(target)`, read `camera.quaternion`

**Rebuild ViewPose from `{ quaternion, distance, target, zoom }`:**

1. Choose a local eye offset in camera space (e.g. along −forward in view space)
2. `position = target + rotate(quaternion, localOffset) * distance` (or equivalent)
3. `up = rotate(quaternion, localUp)` (e.g. (0,1,0) in camera space)
4. Keep `zoom` and `target` as given

### Information loss / non-orientation state

| Field | In quaternion alone? | Notes |
|---|---|---|
| Look direction | yes (column of rotation) | |
| Roll (up around look) | yes, if full orientation kept | Dropped if up is re-derived from world-up only |
| Orbit distance \|position−target\| | **no** | Must carry separately |
| Target world point | **no** | Orbit keeps target fixed today; pan moves target+position |
| Zoom | **no** | Framing, not orientation |
| Projection mode | **no** | On CameraState / document, not ViewPose |
| Degenerate eye=target | undefined look | `getViewOffsetDirection` forces `(0,0,1)` |

There is **no** existing `viewPoseToQuaternion` / `viewPoseFromQuaternion` helper. Closest related math lives in `src/motion/cameraMotion.ts` (offset-direction slerp + separate up slerp), not on ViewPose itself.

---

## 2. Existing pose primitives and three.js slerp

### Pose module public surface (`src/pose/index.ts` re-exports)

| Symbol | Role | Reusable for orientation-space slerp model? |
|---|---|---|
| `ViewPose` / `cloneViewPose` | state carrier | **yes** — still the runtime pose |
| `createViewPoseFromCameraState` | seed → pose | **yes** — home / initial |
| `createViewPoseFromCamera` | live three camera → pose | yes for capture; not detent core |
| `applyViewPoseToCamera` | pose → three camera + lookAt | **yes** — write path unchanged |
| `getViewOffsetDirection` | unit eye offset | **yes** — direction half of orientation |
| `getInitialCameraOffset` | initialCamera position−target | **yes** — home offset / distance seed |
| `orbitViewPose(pose, θ, φ)` | axis-angle delta orbit | **becomes dead for detent path** if detents are absolute orientations; still used by `reduceViewPose` for any residual θ/φ command application (hold multi-command, non-detent) |
| `panViewPose` / `zoomViewPose` | pan/zoom | unrelated to orbit redesign |
| `focusViewPose` | absolute reframe with orientation vocab | **related** — already absolute orientation modes |
| `restoreViewPose` | snapshot restore | absolute pose set |
| `getViewPoseAxes` | private in viewPose.ts | used by orbit **and** pan; singularity fudge lives here |
| `getOrbitRotationAngle` / `getOrbitRotationAxis` | private | max(\|θ\|,\|φ\|) + axis blend; detent-era |

### Interaction / camera layers

| Symbol | File | Role |
|---|---|---|
| `reduceViewPose` | `src/interaction/viewReducer.ts` | ViewCommand → pose; orbit case calls `orbitViewPose` |
| `OrbitDirection` `{theta, phi}` | `src/camera/orbitDetent.ts` | unit-ish direction in command delta space (components ±1 after /max-abs) |
| `OrbitDetentProgress` | same | `{ direction, originPose, progress:radians }` |
| `OrbitDetentMotion` | same | from/to progress + origin + duration |
| `getOrbitDirection` | same | command → direction |
| `createOrbitTapMotion` / `sampleOrbitDetentMotion` / `getOrbitDetentTargetPose` | same | detent timeline; samples via `getOrbitPose` → `reduceViewPose` with `dir * radians` |
| `isSameOrbitDirection` / opposite align | same | same/opposite reuse of progress |

### three.js Quaternion / slerp — already a dependency

- Package: `"three": "^0.185.1"`.
- `src/pose/viewPose.ts` imports `Vector3` only (no Quaternion there today).
- **Existing slerp usage** in `src/motion/cameraMotion.ts`:
  - `Quaternion.setFromUnitVectors(startDir, endDir)` then `slerpQuaternions(identity, rotation, t)` on the **offset direction** (`interpolateOrbitPosition`).
  - Separate independent slerp for **up** (`interpolateUp`).
  - Used when a `CameraMotionPlan` has `path: 'orbit'` (non-detent motion interpolation between two full poses).
- This is **not** a single orientation-quaternion slerp: direction and up are slerped independently, so intermediate frames can briefly have non-orthonormal look/up pairs before `lookAt` re-orthogonalizes on apply.
- Also: `Quaternion.setFromEuler` in `src/view/viewportFocus.ts` / cube instance matrices — mesh transforms, not camera detents.

### What becomes dead vs stays under a pure orientation-slerp detent model

| Likely dead or replaced | Stays |
|---|---|
| `OrbitDirection` θ/φ progress accumulation | `ViewPose` fields |
| `getOrbitPose` (dir × radians → orbitViewPose) | `cloneViewPose`, apply/create helpers |
| `getCompatibleOrbitProgress` / nearest-detent origin search along a ray in θ/φ space | `reduceViewPose` for pan/zoom/focus/reset/restore |
| `orbitViewPose` **as the detent sampler** | Possibly `orbitViewPose` still for continuous gesture mirror / non-tap paths if those keep θ/φ commands |
| Private max-angle axis blend for taps | `cameraMotion` orbit path slerp (already absolute from→to) as a pattern to align with or replace |

---

## 3. Initial / home orientation and any existing canonical sets

### Session home seed

Production composition root (`src/app/useEditorCommands.ts`):

```ts
initialCamera = createGridFramedCamera(scene, { height, width })
authority = createCameraAuthority(initialCamera)
```

`createGridFramedCamera` (`src/view/viewportFocus.ts`):

- Starts from `defaultCamera` (or same with scene projection):
  - `position: [0, 0, 5]`, `target: [0, 0, 0]`, `up: [0, 1, 0]`, `zoom: 120`, `projection: 'orthographic'`
- Keeps **seed view direction and up** (offset from defaultCamera), re-aims **target** to grid frame center, scales **distance** to fit bounds, sets **zoom** from frame.
- Comment in source: *"The camera a session should open on."*

So **home orientation** = defaultCamera look (from +Z toward origin, world Y up), not a cube-face orthographic lattice. Distance/zoom are content-dependent; direction/up are seed-default.

`createViewPoseFromCameraState(initialCamera)` is what authority stores as the initial pose baseline; orbitDetent's `getSignedOrbitProgress` measures angle of current offset direction against this initial offset direction.

### Focus orientation vocabulary (`src/pose/focusView.ts`)

```ts
type FocusViewOrientation =
  | 'initial'     // use initialCamera offset + up
  | 'preserve'    // keep current offset direction + up
  | { kind: 'direction'; direction: Vec3; up: Vec3 }  // absolute
```

Used by focus/reset commands and selection framing — **not** by numpad orbit.

### Selection-driven directional orientations (`src/view/viewportFocus.ts`)

- `createDirectionalOrientation`: world direction from part local axis via cell matrix.
- `createCameraUp(direction)`: world Y unless `|dir·Y| ≥ 0.95`, then `(0,0,±1)` (pole-adjacent up pick).
- Produces one-off `FocusViewOrientation` for face/edge focus — **not** a static table of 6/24/26 views.

### Scene chrome (not camera presets)

- `WorldAxesChrome`: draws world X/Z ground lines only (visualization).
- `AxisHintChrome`: selection axis hints on cubes — not view presets.

### What does **not** exist

- No exported array/table of canonical orbit detents (cube faces, 45° lattice, icosahedron, etc.).
- No "front/right/top/iso" named camera bookmarks in pose or editor command IDs beyond the 8 θ/φ step commands in `src/editor/affordances.ts`.
- Numpad/keypad map only to those 8 relative orbit commands (`src/editor/keyboard/keymap.ts`, `viewControlDefinitions.ts`).

**Reusable orientation sources if designers want "don't invent":**

1. `defaultCamera` / `createGridFramedCamera` seed direction+up → session home.
2. `FocusViewOrientation` absolute `{direction, up}` shape → already the absolute orientation payload for focus.
3. `createCameraUp` pole-adjacent up policy → existing near-pole up rule for absolute directions.
4. World axes basis (X/Y/Z) implicit in domain/cube geometry — no camera preset list, but cube face normals exist via `createCubeFacePlanes` for selection focus.

---

## 4. Non-commutativity and singularities in current primitives

### `orbitViewPose` (axis-angle, relative)

- Single rotation: `angle = max(|θ|, |φ|)`, `axis = normalize(viewUp·θ + viewRight·φ)`.
- **Non-commutative** with sequential application: two corner steps ≠ one combined step; order of θ then φ ≠ blended axis (current code never does sequential euler; it always blends).
- Corner vs cardinal: same `angle` magnitude (π/4 step) but different axis; net principal-axis travel is smaller on corners than two sequential cardinals.
- `_initial` parameter unused — no home-relative correction inside orbit.

### `getViewPoseAxes` singularity fudge (`viewPose.ts:296-318`)

```
forward = normalize(target − position)   // default (0,0,−1) if zero
up_in   = normalize(pose.up)             // default (0,1,0) if zero
right   = forward × up_in
if right ≈ 0: right = (1, 0, 0)           // ← hard fudge
up_out  = normalize(right × forward)
```

When look ∥ stored up (near world poles if up stays Y), right collapses and is forced to world X. **Axis for subsequent orbit/pan jumps discontinuously.** No phi clamp; the fudge is basis repair, not elevation limit.

### Detent layer (`orbitDetent.ts`)

- Direction from command: `component / max(|θ|,|φ|)` → corners get `{θ:±1, φ:±1}` (vector length √2, not unit).
- Progress is a **scalar along that direction ray**, not an absolute orientation.
- Same direction continues progress; opposite flips sign of progress; any other direction → `getAlignedOrbitProgress` returns null → **new origin** via `getNearestOrbitDetentOrigin` (search along ±direction from initial offset angle).
- Sampling always: `reduceViewPose(origin, {θ: dir.θ·r, φ: dir.φ·r})` — re-applies relative orbit from a frozen origin each frame (path is the orbitViewPose trajectory, not independent of origin).

### What a quaternion / orientation-space model must handle that current code fudges

| Current fudge / gap | Quaternion model must decide |
|---|---|
| `right=(1,0,0)` when forward∥up | Continuous orientation (no axis rebuild mid-slerp); still need a policy when *defining* a target orientation with ambiguous up |
| Up stored separately from look | Full quaternion includes roll; or separate look-dir + up with re-orthonormalize at end (current `lookAt` apply path) |
| Detent progress = scalar along θ/φ ray | Detents = discrete orientations; motion = slerp(current → target); no "progress along direction" scalar unless reintroduced for queueing multi-taps |
| Home measured as angle of offset dirs only (`getSignedOrbitProgress`) | Full orientation distance may include roll; current metric ignores up mismatch |
| Independent direction/up slerps in `cameraMotion` | True orientation slerp keeps orthonormal intermediate frames |
| No elevation clamp | Design may still want soft limits or free SO(3)/S² — code does not impose either today |

---

## 5. Blast radius: who constructs / consumes orbit motions

### Construction path (keypad/keyboard → motion)

```
keymap / CubeKeypad
  → editorCommandIds.viewOrbit*
  → affordances.orbitCommands (createOrbitViewCommand(θ, φ) with ±π/4)
  → EditorCommand { kind:'view', command: ViewCommand orbit }
  → intent bus / view lane (coalesce: sums θ/φ on existing orbit)
  → CameraAuthority.applyView / applyHold
  → cameraAuthorityRuntime.applyCoalescedView
       if single additive orbit and no absolute:
         getOrbitDirection → createOrbitTapMotion  → OrbitDetentMotion
         restingPose = getOrbitDetentTargetPose(motion)
         state.orbitMotion = motion
         also creates CameraMotionPlan from→to for some paths; orbit sample prefers sampleOrbitDetentMotion
       else:
         reduceViewPose(resting, command)  // direct orbitViewPose
         clearOrbitTracking
  → advance(): sampleOrbitDetentMotion or getCameraMotionPose → currentPose
  → CameraDriver applies pose to three camera
```

### Files that **own** orbit-detent state / sampling

| File | LOC (approx) | Coupling |
|---|---|---|
| `src/camera/orbitDetent.ts` | ~295 | Entire detent model; only imported by `cameraAuthorityRuntime.ts` |
| `src/camera/cameraAuthorityRuntime.ts` | ~650 | State: `orbitDetentProgress`, `orbitMotion`; create/sample/clear/queue same-direction taps; ~15 call sites |
| `src/interaction/viewReducer.ts` | ~60 | `orbit` case → `orbitViewPose` |
| `src/pose/viewPose.ts` | orbit helpers ~50 lines | `orbitViewPose` + private axis helpers |
| `src/motion/cameraMotion.ts` | orbit path ~50 lines | Duration/path tags for orbit commands; from→to slerp used when non-detent motion plan path is `'orbit'` |
| `src/editor/commands.ts` | types + `viewOrbitStepRadians` + `createOrbitViewCommand` | Command vocabulary |
| `src/editor/affordances.ts` | 8 orbit definitions | Fixed ±π/4 deltas |
| `src/editor/keyboard/keymap.ts` + controls | key bindings | Unchanged if command IDs stay |

### Production importers of orbitDetent symbols

**Only** `src/camera/cameraAuthorityRuntime.ts`. No other production file imports `orbitDetent` directly.

### Tests (assertion surface)

- `tests/interaction.authority.test.ts` — heavy orbit/detent coverage (dozens of orbit mentions).
- `tests/view.test.ts` — `reduceViewPose` focus/restore, not detent.
- Path-only imports elsewhere unchanged by detent semantics.

### Redesign delete vs add (structural, not a recommendation)

| Delete / replace | Add (if orientation-space design is chosen) |
|---|---|
| `OrbitDirection` θ/φ ray model | Canonical orientation set (data) + nearest-target picker |
| Progress scalar + originPose ray marching | Live orientation → target orientation slerp sampler |
| `getOrbitPose` / dir×radians | `orientationFromViewPose` / `viewPoseFromOrientation` (distance, target, zoom preserved) |
| Possibly `orbitViewPose` for tap path only | Reuse or replace `cameraMotion.interpolateOrbitPosition` + `interpolateUp` with one quaternion slerp |
| Same/opposite direction queue rules | Queue rules in orientation space (next canonical along a graph, or repeated slerp to further targets) |

| Keep as-is unless design expands scope |
|---|
| ViewCommand `orbit` shape (unless commands become "snap to orientation N") |
| Affordance command IDs / keymap |
| `CameraAuthority` port interface |
| Pan/zoom/focus/morph/gesture paths |
| Barrel guards, interaction headless core |

### Dual motion systems today (fact)

Authority can drive pose from:

1. **Orbit detent sampler** (`sampleOrbitDetentMotion` → reduceViewPose from origin), and/or  
2. **CameraMotionPlan** (`getCameraMotionPose` → linear or orbit-path slerp between two poses).

Orbit taps set both resting target via detent and motion bookkeeping in authority. A redesign that makes "motion = slerp(live → target orientation)" collides with or absorbs both of these paths; they are not one abstraction today.

---

## Quick reference: numeric step (unchanged fact)

`viewOrbitStepRadians = Math.PI / 4`. Cardinals: one of θ,φ = ±step. Corners: both = ±step in one command.

---

## File index for designers

| Path | Why it matters |
|---|---|
| `src/pose/viewPose.ts` | ViewPose, orbitViewPose, axes singularity |
| `src/pose/focusView.ts` | Absolute orientation vocabulary |
| `src/pose/cameraState.ts` | defaultCamera home seed |
| `src/view/viewportFocus.ts` | createGridFramedCamera, createCameraUp |
| `src/camera/orbitDetent.ts` | Current detent model (sole producer API) |
| `src/camera/cameraAuthorityRuntime.ts` | Sole consumer; state machine |
| `src/interaction/viewReducer.ts` | Command → pose |
| `src/motion/cameraMotion.ts` | Existing Quaternion slerp (split dir/up) |
| `src/editor/affordances.ts` | Command deltas |
| `tests/interaction.authority.test.ts` | Behavior contract for any rewrite |
