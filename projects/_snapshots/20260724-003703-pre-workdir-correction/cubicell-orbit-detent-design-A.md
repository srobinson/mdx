# Design A — Orientation-space orbit detents (quaternion + lattice)

Lead: Opus (8:4.2), correctness + minimal-special-cases lens. 2026-07-10.
Scope: replace the scalar-progress / fabricated-origin orbit detent machinery in `orbitDetent.ts` + the orbit branches of `cameraAuthorityRuntime.ts`. Ubiquitous language kept: `ViewPose`, orbit, detent, `CameraAuthority`.

## 0. What we are replacing and why

Locked root cause: the current model stores "where am I in an orbit" as a 1-D scalar `progress` along a `direction` plus an `originPose`. That is a *chart*, and it is only valid while motion stays collinear with `direction`. On a non-collinear mid-motion re-anchor (`getNearestOrbitDetentOrigin` → `getSignedOrbitProgress`), it collapses the live displacement to `angleTo` and re-attributes it to the new axis, fabricating an `originPose` that does not coincide with the live pose. The first `advance()` renders that fabricated origin → one-frame snap. Corners hit it because 7↔1 / 1↔3 are non-collinear (neither same nor opposite direction).

The defect is representational, not a tuning bug. The fix is to stop representing orientation as *scalar + origin* and represent it as what it actually is: **a point on SO(3)**.

## 1. Representation — the elegance thesis (validated, then sharpened)

**Orbit changes only the camera's orientation about a fixed target at a fixed distance.** From a `ViewPose`:

```
target   T = pose.target
distance d = |pose.position - pose.target|      // orbit-invariant
zoom     z = pose.zoom                            // orbit-invariant
orientation q ∈ SO(3):  forward f = normalize(T - pose.position)
                        up      u = pose.up
                        right   r = normalize(f × u)
                        q = quaternionFromBasis(r, u, -f)   // camera looks down -z
```

Inverse (render a target orientation, keeping T, d, z fixed):

```
poseFromOrientation(q, T, d, z):
  forward  = q · (0,0,-1)
  position = T - forward · d
  up       = q · (0,1,0)
  return { position, target: T, up, zoom: z }
```

This is a clean bijection between orbit state and `(q, T, d, z)`. Orbit motion is then **entirely** motion of `q`; `T, d, z` are carried untouched.

**Thesis (item 1): every motion = `slerp(q_live → q_target)`, C0 continuity is free, interruption is trivially safe.** Validated:

- *C0 free*: `slerp(a, b, 0) ≡ a` by definition. The motion's first sample is exactly the live orientation. There is no origin to fabricate and nothing to mis-measure. The entire class of snap bugs is structurally impossible.
- *Interruption trivially safe*: on a new tap, read the live orientation `q_live` (sample the in-flight slerp at `nowMs`, or read it off `currentPose`), pick a fresh `q_target`, start `slerp(q_live → q_target)`. Because the new slerp begins at the true live orientation and the target is an **absolute** canonical orientation (not `live + delta`), there is no discontinuity and no error accumulation across interrupts.

**Sharpening.** The elegant invariant is not "slerp quaternions" alone; it is the separation of two concerns that the old model fused into one scalar:

| Concern | Representation | Property it buys |
|---|---|---|
| **Which orientations are detents / which one to target** | discrete integer lattice `(i, j)` in a yaw/pitch chart | closed, commutative, drift-free, no special cases |
| **How we move and where we currently are** | unit quaternion `q` + slerp | coordinate-free, C0, interrupt-safe, roll-tolerant |

Targets are chosen in the discrete chart (exact, order-independent). Motion happens in SO(3) (continuous, origin-free). Neither half can fabricate an origin. This split is the design.

## 2. Detent set — precise definition

cubicell is a cube viewer. Home orientation `q_home` is the initial camera (`defaultCamera`: position `[0,0,5]`, target origin, up `+Y`) → front-face view. Existing step `viewOrbitStepRadians = π/4`; existing tap vocabulary = 8 directions (4 cardinal + 4 corner). The existing orbit is already **screen-space yaw/pitch** (`orbitViewPose` rotates about `up`/`right`), so the detent set that preserves feel is the yaw/pitch π/4 lattice, not the octahedral group. Justification for rejecting octahedral (cube-symmetry) detents is in §3.

**Chart.** Roll-free azimuth/elevation (turntable), anchored at `q_home`:

```
q(α, β) = q_home · Ry(α) · Rx(β)      α = yaw about world-up, β = pitch about body-right, roll ≡ 0
```

**Detent lattice L:**

```
L = { q(i·π/4, j·π/4) : i ∈ ℤ/8ℤ,  j ∈ {-2,-1,0,1,2} }
```

- `i` (yaw): 8 positions, wraps at 2π.
- `j` (pitch): clamped to `[-π/2, +π/2]`. `j = ±2` are the top/bottom face-on views.
- 8 × 5 = **40 canonical orientations**. Roll is always 0.

Anchoring at `q_home` makes the rest pose detent `(0,0)` — "tap from rest" produces integer indices, matching today.

**Relation to cube geometry (honest):** the lattice reproduces the cube's **face views** (`β=0, i∈{0,2,4,6}`; `j=±2`) and **edge views** (odd `i` at `β=0`, or `β=±π/4`) exactly. The four "corner" detents sit at screen-diagonal orientations `q(±π/4, ±π/4)` which are *near but not exactly* the cube's body-diagonal (isometric) view — `Ry(π/4)Rx(π/4)` on a face gives forward ≈ `(−.5, −.707, −.5)`, whereas the true corner is `(−.577, −.577, −.577)`. This is **identical to today's behavior** (also screen-space), so it is feel-preserving, not a regression. Exact isometric corner detents would require a different (octahedral) detent set and a different step; that is a separate product decision, flagged out of scope.

**Pole rows (`j=±2`):** at top/bottom, yaw `i` still rotates the visible face by 45° increments (8 distinct roll-of-the-top-face orientations) — meaningful for aligning cube edges to screen, so all 8 are kept as distinct detents.

## 3. Non-commutativity — why the lattice stays closed (the rigorous part)

Screen-space yaw-then-pitch ≠ pitch-then-yaw. Naive designs that **compose quaternions to advance a detent** (`q ← q · Rtap`) inherit this: with a π/4 step, `Ry(π/4)` and `Rx(π/4)` generate a dense (effectively infinite) subgroup of SO(3), so repeated composition drifts off any finite detent set. Octahedral symmetry does not save it either: `O` is generated by 90° face turns; 45° taps do not preserve `O`. **There is no finite detent set closed under quaternion composition of π/4 taps.** This is why a compose-based design cannot avoid drift and re-quantization special cases.

**Resolution: never compose orientations to advance a detent. Advance the integer indices.**

- A tap acts on `(i, j)` by integer addition: yaw tap `i ← i±1 (mod 8)`; pitch tap `j ← clamp(j±1)`; corner tap does both.
- Integer addition is exactly commutative and the index space is closed by construction. Two taps land where the user expects and in any order (`(i+1,j)` then `(_, j+1)` = `(i+1, j+1)` = the other order).
- The quaternion is **derived once** from the target indices via `q(α,β)`; it is never fed back to advance the next detent. The rendered path between detents is a single `slerp` (unique shortest geodesic); the fact that the chart path (yaw-then-pitch) differs from the geodesic is irrelevant because only the **endpoints** are canonical and the interpolation is smooth.

So non-commutativity is dissolved: it lives only in the (discarded) intermediate path, never in the state. No drift, ever, because state is two bounded integers, not an accumulated rotation.

## 4. Tap + interrupt algorithm

State on the authority (replaces `orbitDetentProgress` / `orbitMotion` / `motion`-for-orbit):

```
orbitSlerp: { fromQ: Quaternion, toQ: Quaternion, startedAtMs, durationMs } | null
// live orientation is read from currentPose; no separate stored origin
```

Target selection from an **arbitrary** live pose (freely dragged, off-lattice, or mid-slerp):

```
targetDetent(q_live, tap):                       // tap ∈ {yaw:±1|0, pitch:±1|0}, not both zero
  (α, β) = decomposeToChart(q_live)              // project onto roll-free chart; see §5 for roll
  i* = tap.yaw   > 0 ? floor(α/(π/4)) + 1
     : tap.yaw   < 0 ? ceil (α/(π/4)) - 1 : round(α/(π/4))
  j* = tap.pitch > 0 ? floor(β/(π/4)) + 1
     : tap.pitch < 0 ? ceil (β/(π/4)) - 1 : round(β/(π/4))
  j* = clamp(j*, -2, +2)
  return q(i*·π/4, j*·π/4)
```

`floor(·)+1` / `ceil(·)-1` = "the next gridline in the tapped direction." On-lattice it is an exact ±1 step; off-lattice it snaps forward to the next gridline (travel ≤ π/4), which *re-aligns* a dragged view without a snap because the motion still slerps from the true `q_live`.

Tap handler (`applyView`, orbit branch):

```
q_live = sampleLiveOrientation(nowMs)            // in-flight slerp sample, else from currentPose
toQ    = targetDetent(q_live, tap)
orbitSlerp = { fromQ: q_live, toQ, startedAtMs: nowMs, durationMs: tapDuration }
```

`advance(nowMs)`:

```
if orbitSlerp:
  t = ease(clamp((nowMs - startedAtMs)/durationMs, 0, 1))
  q = slerp(fromQ, toQ, t)
  currentPose = poseFromOrientation(q, T, d, z)
  if t == 1: orbitSlerp = null
```

**Rapid alternation 7↔1 — proof of no snap, no compounding.** 7 = corner `(yaw+, pitch−)`, 1 = corner `(yaw+, pitch+)` (per `affordances.ts`). Start at detent `(0,0)`:

1. Tap 7 → `toQ = q(+π/4, −π/4)`; slerp from `q(0,0)`.
2. Mid-slerp tap 1: `q_live` is on the arc, `(α,β)` with `α∈(0,π/4)`, `β∈(−π/4,0)`. Target: yaw+ → `i*=1`; pitch+ → next gridline above β → `j*=0`. `toQ = q(+π/4, 0)`; slerp from the **true** `q_live`.
3. Mid-slerp tap 7: decompose again, yaw+ → `1` (or `2` if past), pitch− → next below current β. Absolute lattice target; slerp from live.

Every `fromQ` is the exact live orientation (C0, no snap). Every `toQ` is an absolute lattice orientation computed fresh from the live pose, never `live + delta` — so nothing accumulates and there is no fabricated origin. The old bug is structurally absent.

**Feel invariants (item 5) — all preserved:**

- *Tap ≈ π/4 of visual travel*: from a detent, target is exactly one index away (π/4 yaw or pitch; corner = the single geodesic between adjacent-diagonal detents). From off-lattice, ≤ π/4 (snap to gridline). ✔
- *Opposite taps cancel*: from `(0,0)`, tap right → target `(1,0)`, slerp starts; immediately tap left → `α_live` barely > 0 → ceil−1 = `0` → target `(0,0)` = home. Returns to start. ✔
- *Taps from rest repeatable/consistent*: on-lattice `floor/ceil ±1` is exact and deterministic. ✔

**Bonus special-case eliminations.** Because zoom and orientation are now orthogonal (`z` is carried through `poseFromOrientation` untouched), the entire `reanchorOrbitTrackingZoom` path and the "instant zoom re-anchors the in-flight orbit origin" coupling in `applyInstantZoomCommand` disappear — an orbit slerp in flight is simply unaffected by a zoom. Deleted with the rest of the scalar machinery: `OrbitDetentProgress`, `OrbitDetentMotion`, `getSignedOrbitProgress`, `getNearestOrbitDetentOrigin`, `getCompatibleOrbitProgress`, `getAlignedOrbitProgress`, the queued-target machinery (`getQueuedOrbitTapTarget` / `getQueuedOrbitProgress`), `completeOrbitMotion`. Replaced by: `q`-state + pure `targetDetent` + `slerp`.

## 5. Special cases I could NOT eliminate (honest ledger)

1. **Roll from free trackball drag → chart decomposition.** `cameraTrackball.ts` is a full 3-DOF trackball (`noRotate=false`, `staticMoving=false`), so a mouse drag can leave `q_live` with nonzero roll, while detents are roll-0. `decomposeToChart` must project roll out (derive α from forward's horizontal azimuth, β from `asin(forward.y)`, discard roll). **This is not a snap:** the tap slerps from the rolled `q_live` to a roll-0 `toQ`, continuously removing roll during the move. It is a *defined behavior* to document ("the first tap after a rolled drag also levels the view"), not a discontinuity. This is precisely why slerp beats chart-space (α,β) interpolation, which *would* snap the roll away on decomposition. Fully eliminable only by constraining orbit drag to turntable/roll-0 (recommended follow-up; out of scope for this slice).
2. **Yaw singularity at the poles.** At `β=±π/2` (looking straight down/up), azimuth α is ill-conditioned to extract from forward. Mitigation: derive α from the up-vector's horizontal projection, or retain the last α. Affects only *target selection* at the poles, never the motion; bounded, non-accumulating.
3. **Transient geodesic roll on corner slerps.** `slerp(q(i,j), q(i+1,j+1))` between two roll-0 orientations is the SO(3) geodesic, which can bow a few degrees off roll-0 mid-arc before returning to roll-0 at the endpoint. Bounded (≤ ~a few° at π/4), non-accumulating, cosmetic. Eliminable only by chart-space interpolation, which reintroduces the roll-snap of case 1 — a strictly worse trade. Kept and documented.
4. **Pitch clamp vs. wrap at ±π/2** (do up-taps stop at top-down, or tumble over the back?). A product decision Stuart owns, not a correctness issue. Recommend **clamp** to `[-π/2, π/2]` with top/bottom as valid pole detents (matches conventional viewers; keeps the lattice finite at 40).

## 6. Integration summary

- `CameraAuthority` contract is unchanged externally (`applyView`, `advance`, `getPose`, gesture/glide untouched — orbit is not a glide command). Gesture drag sets `q_live` via `currentPose`; the next tap's `decomposeToChart` absorbs any off-lattice/rolled result.
- New pure module (proposed `src/camera/orbitOrientation.ts`, replacing `orbitDetent.ts`): `orientationFromPose`, `poseFromOrientation`, `q(α,β)`, `decomposeToChart`, `targetDetent`. All pure, all trivially unit-testable (feed a `q_live` + tap, assert `toQ`), which the scalar model never allowed.
- Motion driver: reuse the existing ease/duration (`getViewCommandMotionDuration`) so tap timing/feel is byte-identical; only the interpolant changes from scalar-progress-on-a-fabricated-origin to `slerp(q_live → q_target)`.

**Net:** one representation (`q` + integer lattice), one motion primitive (slerp), zero fabricated origins, four documented edge behaviors none of which are snaps.
