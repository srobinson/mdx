# Orbit detent redesign — CONSENSUS spec (designers Opus + Fable agreed)

Synthesized by orchestrator (8:3.1) from design-A (Opus), design-B (Fable), and the primitives inventory (grok), 2026-07-10. Basis: main at 3b07878. This is the buildable spec; grok validates feasibility, Codex validates correctness, then Stuart approves before build.

## The one-line design

Replace the scalar-progress / fabricated-origin orbit model with: **detents = the 26 exact principal cube views arranged on a clamped integer lattice (k,b) of 40 orientations (poles are an 8-variant oriented family); taps act by closed-form index arithmetic (azimuth cyclic, elevation saturating — absolute targets, never composed); forward-only re-align; motion = S²-geodesic slerp of the view direction + a scalar roll eased to 0; constant beat, existing easeOutQuart.** All fabricated-origin machinery deleted.

*(Revision 2, post-falsification: Codex's exhaustive prototype LOCKED the motion layer and refuted the emergent max-dot traversal + single-canonical-pole model; the traversal and pole sections below are the redesigned, provable replacements. The motion interpolant and detent-set sections are unchanged and locked.)*

## Agreed points (both designers, locked)

1. **State** = the live orientation, read from `currentPose` each tap. No stored origin, no scalar progress.
2. **Motion = slerp(live → absolute target).** C0 continuity is free (`slerp(a,b,0)≡a`); interruption is trivially safe (re-slerp from the true live orientation to a fresh absolute target). The entire snap-bug class is structurally impossible.
3. **Target is ABSOLUTE, chosen from a finite INDEXED set** — never `live + delta`, never by composing rotations. (This is what dissolves non-commutativity and drift; it is set-independent, which is why the 26-view set is exactly as closed/drift-free as any lattice.)
4. **Delete (no parallel implementations left behind — DRY):**
   - Whole `orbitDetent.ts` module: `OrbitDetentProgress`, `OrbitDetentMotion`, `getSignedOrbitProgress`, `getNearestOrbitDetentOrigin`, `getCompatibleOrbitProgress`, `getAlignedOrbitProgress`, queued-target machinery, `completeOrbitMotion`.
   - The `reanchorOrbitTrackingZoom` coupling in `cameraAuthorityRuntime` — orientation and zoom are now orthogonal.
   - **The now-orphaned orbit path in `cameraMotion.ts`** (orbit was its sole consumer, verified: `getViewCommandMotionPath` returns `'orbit'` only for `kind==='orbit'`, and `interpolateOrbitPosition` is reachable only via `path==='orbit'`): delete `interpolateOrbitPosition`, `canUseOrbitInterpolation`, `orbitInterpolationEpsilon`, the `path==='orbit'` branch in `interpolateViewPose`, the `'orbit'` member of `CameraMotionPath` (union collapses → the `path` field and `getViewCommandMotionPath` go vestigial and are removed). The new orbit sampler does NOT route around `getCameraMotionPose`; it replaces the orbit path outright.
   - **Survives** (still used by non-orbit linear motions — focus/reset/restore/pan/zoom): `getCameraMotionPose`, `interpolateViewPose`, `interpolateLinearPosition`, `interpolateUp`, `CameraMotionPlan` (as linear-only). The new orbit sampler must not reuse `interpolateUp` (independent dir/up slerp can go non-orthonormal); that is a "don't reuse", not a reason to keep a dead orbit twin.
   - Acceptance gate: after the slice, `grep` finds zero references to the deleted symbols and no second orbit interpolator anywhere.
5. **Cadence**: constant beat (fixed per-tap duration regardless of arc length) so non-uniform cube arcs feel identical; keep `easeOutQuart`; reuse the existing tap-duration knob. Held keys = discrete drumroll of taps, each landing on a named view.

## Detent set (fork 2 resolved → 26 exact cube views)

- **6 face-on** (±X,±Y,±Z), **12 edge-on** ((±1,±1,0) perms, 45°), **8 corner-on** ((±1,±1,±1)/√3, isometric, elevation atan(1/√2) ≈ **35.264°**).
- Home `defaultCamera` (front face, +Y up) is a member → every session starts on a detent.
- No roll in the detent vocabulary: detents are (direction, canonical no-roll up). Pole views (top/bottom) canonicalize up to the nearest grid axis.
- **Why not the π/4 lattice**: it rests ~10° above the isometric on skew, unnameable orientations. For a cube viewer the isometric corner is the identity. Verified: the screen-diagonal great circle from a face passes exactly through (1,1,1)/√3 at 54.74°, edge at 90°, corner at 125.26° — one corner tap lands dead-on. Cube geometry is inherently non-uniform (54.74° face→corner vs 35.26° corner→edge); there is no uniform hybrid, and constant beat makes the non-uniformity invisible.

## Traversal (revised): the clamped (k, b) lattice — A's algebra on B's geometry

The emergent max-dot generator is REPLACED by closed-form index arithmetic. Codex's prototype falsified the emergent graph (188/208 closure failures, 124/208 inverse failures, pole oscillation); the root cause was generating adjacency from tangent geometry on an irregular sphere. The fix is structural: put the exact views on an integer chart and let taps act on indices.

**State: (k, b).** `k ∈ ℤ/8ℤ` is the azimuth slot (45° each). `b ∈ {−2,−1,0,+1,+2}` is the band:

| b | Band | Nodes | Elevation (exact cube views) |
|---|---|---|---|
| 0 | Equator Q | 8: faces (even k), edges (odd k) | 0° |
| ±1 | Upper/lower U± | 8: edges (even k, ±45°), **corners (odd k, ±35.264°)** | non-uniform, exact |
| ±2 | Poles T± | 8 up-variants indexed by k | ±90°, direction ±Y |

40 orientations over 26 view directions. Fork 2's outcome is intact: the odd-k U-band nodes are the true isometrics, and elevation values are the exact cube-view values — the lattice is integer in STRUCTURE, non-uniform in ANGLE, which the constant beat absorbs.

**Taps are numpad-true index deltas** (from `affordances.ts` command geometry: θ left-positive, φ up-positive): `Δk ∈ {−1,0,+1}` cyclic, `Δb ∈ {−1,0,+1}` **saturating at ±2**. Corners do both. **At a pole the entire toward-pole HALF of the keypad fully clamps to a no-op** — at T+ keys 7/8/9 freeze *both* components (you cannot orbit higher than straight-down), at T− keys 1/2/3 freeze. Only the pure-horizontal keys 4/6 act at a pole: they spin the up-variant in place (Δk±1, a 45° yaw of the top/bottom view — pole rows from design A, useful for grid-to-screen alignment). The away-from-pole keys descend: at T+, key 2 goes down meridian k, keys 1/3 descend diagonally to the adjacent U-band node k∓1. (Do NOT let 7/9 spin the up-variant at the pole: that would move without a valid inverse — 9 would go k+1 but its opposite 1 descends, not returns — reopening the exact inverse hole the full-clamp closes; see invariant 3.) The rendered path between any two nodes remains the locked motion layer (dir-slerp + roll→0); only endpoints come from the lattice.

**Why this is provable where max-dot was not**: taps are translations on a product of a cyclic group and a saturated chain. Every property below is a two-line group-theory fact or a finite enumeration, and the full 40×8 transition table is generated by the formula and frozen as a snapshot test. The corner-surplus-tiebreak problem disappears — every key has a defined action at every node by construction.

## Selector (final: gate on direction only; on-node = roll-aware index remap; off-node = alignment argmax)

Two falsification rounds shaped this. Round 1 (roll sweep): fixed world-space (k,b) deltas break screen-space forward-only past 90° roll (front + 180° roll, key 8 → exactly backward). Round 2: NO free direction-alignment selector can reproduce the index topology at the gate — pole spins are pure up-variant changes with ZERO direction arc (invisible to a direction selector), diagonal-into-pole loses the tap's horizontal component, and in-band isometric-horizontal moves lose to better-aligned equator nodes (80/272 primary losses, not tiebreakable). Conclusion: on-node behavior must BE index arithmetic — made roll-aware by remapping the KEY, not by geometric search. Geometric search is reserved for genuinely off-node poses, where it need not and does not equal index.

**Key → screen tangent.** Screen coords: x right, y up. `s(8)=(0,+1)`, `s(2)=(0,−1)`, `s(6)=(+1,0)`, `s(4)=(−1,0)`, `s(9)=(+1,+1)/√2`, `s(7)=(−1,+1)/√2`, `s(3)=(+1,−1)/√2`, `s(1)=(−1,−1)/√2`. From the live pose build the orthonormal camera frame as `getViewPoseAxes` does (forward `f`, right `r = normalize(f×u_live)`, true up `u = r×f`, LIVE up, roll included); the pressed world tangent is `τ = normalize(σx·s_x·r + σy·s_y·u)` with σx, σy pinned by code assertions (level front + key 8 → front-top edge; level front + key 6 → Regime 1's Δk target).

**Gate: DIRECTION only.** On-node iff the live view direction is within ε_dir of a canonical node direction (config knob). Roll does NOT gate — any roll on-node is handled by the remap below. (Pole nodes: on-node means direction within ε_dir of ±Y; the live up picks the nearest of the 8 variants as the current node.)

**ON-NODE — roll-aware index delta (the steady state, any roll):**

1. Build the node's LEVEL chart rose: the 8 tangents `c(key) = normalize(σx·s_x·r_n + σy·s_y·u_n)` from the node's canonical frame (r_n, u_n at roll 0).
2. Remap the pressed key to `key' = argmax_key dot(c(key), τ)` — the chart-rose direction nearest the pressed tangent. Since the rose is 45°-spaced, the winner is within 22.5° of τ; exact-boundary ties (at 22.5°) resolve to the smaller roll-rotation (equivalently: `key' = rotate(key, round(ρ/45°))` where ρ is the live roll — the remap is literally a rotation of the numpad rose by the quantized roll).
3. Apply the NODE's index row for `key'` — including its clamps, pole spins, and diagonal-descents, verbatim from the 40×8 table. The remapped key indexes the row; the pressed key never touches the table directly.
4. Motion layer (locked) slerps direction (zero arc for pole spins — pure roll/up ease) and eases roll to the target's canonical up.

**OFF-NODE — geometric forward re-align (the transient after a big drag):**

1. `p = −f`; for each node direction `p_n` (40 orientations; both poles carry their 8 variants), geodesic initial tangent `T_n = normalize(p_n − (p_n·p)·p)`; exclude the antipode and arcs > π−δ (the current-node exclusion is vacuous off-node).
2. Rank by `align_n = dot(T_n, τ)` descending (alignment-first — arc-first would pick flanking 45° edges over the corner on diagonal keys).
3. Tiebreaks among `align` within ε of max: nearest arc, then higher symmetry (face > edge > corner), then pole variants by minimum up-twist from the parallel-transported live up, then id.
4. Forward-only is automatic: nodes surround live, so `max align_n > 0` at any roll; no cone knob, no dead taps, never backward.
5. Motion layer slerps to the node, easing roll to its canonical up.

**Properties (Codex re-verifies):**

- (a) **Roll-aware nearest-of-8 is forward-only for all rolls** — but with TWO distinct metrics Codex must not conflate:
  - *Rose-remap alignment* `dot(c(key'), τ)`: within 22.5° of the pressed tangent (≥ cos 22.5° ≈ 0.924) whenever the row moves — this bounds which KEY is chosen.
  - *Motion-heading alignment* `dot(T_target, τ)` (the round-1 forward-only metric): guaranteed only `> 0` (never backward) on-node, NOT ≥ 0.92. The index topology deliberately moves up to ~35° off the press: a corner's in-band horizontal move (key 6 from (1,1,1) → edge (1,1,0)) heads at dot ≈ **0.865** (30°); diagonal-descent-at-pole is similar. These are correct, not regressions.
  - **On-node re-run assertion: 0 backward via `dot(T_target, τ) > 0`; do NOT floor the on-node motion heading at 0.92** (that floor is only the rose-remap and the OFF-node argmax, which IS heading-maximizing). Toward-pole remaps hit the clamp row = truthful no-op, never backward.
- (b) **Zero roll discontinuity on-node**: at roll 0 the remap is the identity (`round(0/45°)=0`), so on-node behavior IS the level index delta; the 80 former mismatches are gone by construction because on-node never consults alignment. The remap is piecewise-constant in roll with switches at 22.5° boundaries — a key REMAP, not a target jump mid-motion (selection happens only at tap time).
- (c) **Off-node heals in one tap**: the argmax lands a canonical node and de-rolls, so the next tap is on-node index arithmetic.
- (d) **The only regime boundary is direction on/off-node** (ε_dir): an honest geometric transition between "step the lattice" and "catch the nearest forward node", with no pole-spin or in-band pathology on either side. Discrete invariants (totality 320/320, moving-inverse 272/272, closure 80/80, alternation law) are properties of the index table and hold for every on-node tap at every roll.

## Motion interpolant (fork 1 resolved)

- **Forward direction**: S²-geodesic slerp from live forward to target forward.
- **Roll**: a SCALAR about the forward axis, `roll(t) = lerp(roll_live, 0, ease(t))`. NOT `cameraMotion.ts`'s independent up-slerp (which can go non-orthonormal pre-lookAt). The scalar form keeps every intermediate frame orthonormal and makes level-hold exact.
- Consequences: level start ⇒ roll channel is 0 for the whole arc ⇒ horizon stays level throughout (removes Opus edge #3, the mid-arc bow). Rolled 3-DOF trackball drag ⇒ roll starts at roll_live (C0, no snap) and eases to 0 (continuous de-roll; B's per-frame no-roll derivation would have snapped it on frame 1).

## Pole model (revised): clamp + oriented family

Codex proved a single canonical no-roll pole up cannot simultaneously give spin-free transit, a named endpoint, and same-key continuation (179.8° up-flip leaving top). Resolution — BOTH halves, each doing one job:

- **Clamp (no through-pole)**: vertical taps saturate at b=±2. This kills the through-pole spin AND the 8-key pole oscillation in one move, and matches conventional viewers. "The vertical ring closes in 8" is dropped; the meridian is a bounded chain that clamps at the poles.
- **Oriented family (8 up-variants per pole)**: T±_k carries the arrival meridian in its index; its up is the no-spin continuation of meridian k. Arriving via 8 on meridian k lands exactly T_k (no reorientation); leaving via 2 descends the SAME meridian k deterministically. Inverse holds at the pole, the endpoint is named ("top, front down-screen" = T_0; "top, front-right-edge down-screen" = T_1; …), and the up-flip is eliminated because pole orientation is part of the node, not a canonicalization.
- **At a pole, only the pure-horizontal keys 4/6** spin the family (k ± 1): eight 45° in-place yaws of the top/bottom view. Deliberate feature (grid-to-screen alignment), deterministic, cyclic, and the bounded limit of vertical-plus-horizontal alternations (see invariants). The toward-pole half (7/8/9 at T+, 1/2/3 at T−) fully clamps to a no-op — you cannot orbit past straight-down — which is exactly what keeps the inverse law hole-free at the pole; the away-from-pole keys (2, and the 1/3 diagonals at T+) descend and invert cleanly.
- The no-roll frame degeneracy at β≈±90° now only concerns the motion interpolant approaching a pole node whose orientation is fully specified by k — the interpolant has a concrete target frame, no ambiguity. (The old `getViewPoseAxes` right-collapse fudge becomes unreachable on the tap path.)

## Ownership seams (MODEL.v2)

- **View policy (`src/view`)**: the 26 canonical views, the (k,b) lattice with its 40 named orientations, and the formula-generated 40×8 transition table, exported as data (beside `viewportFocus`/`selectionFocus`). These are statements about what a cube viewer is → reusable by any actor (an LLM dispatching "go to front-top-right corner" is the same thesis).
- **Camera mechanics (`src/camera`)**: table traversal, direction slerp + roll lerp, re-align cone, beat. New pure module (proposed `orbitOrientation.ts`) replacing `orbitDetent.ts`: `orientationFromPose`, `poseFromOrientation`, `decomposeToDirectionRoll`, `selectTargetView`, the slerp sampler. All pure, all unit-testable (feed live pose + tap, assert target).
- **Commands/keymap**: unchanged (serializable orbit intents; descriptor layer symmetric).
- **Feel constants (`cubicellConfig`)**: beat duration, repeat interval, re-align ε, forward cone half-angle.
- `CameraAuthority` external contract unchanged (`applyView`, `advance`, `getPose`; gesture/glide untouched).

## Required invariant set (revised: kept / restated / dropped)

**Kept (must hold, machine-checkable — Codex re-verifies):**

1. C0, no-snap, forward-only, continuous de-roll — LOCKED by the verified motion layer; not revisited.
2. Determinism + named endpoint: every (node, key) pair has exactly one target, every node has a name (the 40-entry table is a total function).
3. **Inverse law**: whenever a tap MOVES, the numpad-opposite key (4↔6, 8↔2, 7↔3, 9↔1) returns to the source, from EVERY node — the ONLY exemptions are no-op taps (a tap that does not move has nothing to invert). Proof: taps are translations on ℤ/8ℤ × saturated chain and the opposite key negates both deltas, which cancel exactly wherever neither is saturated. The only saturating moves are made no-ops by the full-clamp rule (toward-pole half: 7/8/9 at T+, 1/2/3 at T−), so there are **no partial-clamp moves and therefore no genuine inverse violations**. At the pole every non-no-op tap still inverts: 2→U_k inverts via 8→T_k; 1→U_{k−1} via 9→T_k; 3→U_{k+1} via 7→T_k; 4/6 spins invert each other. This is strictly cleaner than the pre-falsification wording (which let 9 spin at the pole and had to log 7↔3 / 9↔1 as pole exceptions): the full-clamp removes the exceptions rather than enumerating them.
   **Final wording (roll-complete, Codex-verified)**: the inverse law is stated over EFFECTIVE (screen-relative) keys — the opposite effective key returns to the source from every unclamped node at every roll (6800/6800). At roll 0, effective == physical, so the physical numpad-opposite undoes (272/272) — the steady state where essentially all tapping happens. Across a de-rolling FIRST tap after a rolled 3-DOF mouse drag, physical-key undo cannot hold and is not supposed to: the intentional de-roll changes the physical-key→world frame between the two taps, which is inherent to ANY screen-relative control that levels the horizon — the only ways to "fix" it are sacrificing de-roll (rolled detents, unnameable views) or screen-relativity (world-fixed keys, the measured backward-motion class), both rejected. Documented intended behavior, not a snap: C0 and forward-only hold throughout, keyboard detents are roll-0 by construction, and a rolled orientation is deliberately not keyboard-restorable (pose restoration is the focus-restore vocabulary's job, not the orbit keys').
4. **Horizontal closure per band**: 8 taps of 4 or 6 return bit-exact on Q, on U± (edge/corner zigzag ring), and at either pole (8 in-place spins).
5. **Alternation law** (replaces the universal "≤2 views" — see pushback below), three cases, all bounded and wander-free:
   - (a) **Inverse pairs** (4↔6, 8↔2, 7↔3, 9↔1): exact 2-cycles everywhere unclamped — the rock.
   - (b) **Vertical-sharing mixed pairs** (e.g. 4↔8): finite monotone staircase that saturates at the pole; limit set = the pole spin, ONE view direction. No more "7 views wandering around the top".
   - (c) **Horizontal-sharing diagonal pairs** (7↔1, 9↔3 — the original repro): deterministic 45° azimuth crawl with a one-band elevation bob, bounded to 2 adjacent bands, every stop named. Coherent by command geometry: 7 and 1 SHARE the left component (both +θ in `affordances.ts`), so their alternation crawls left; it cannot 2-cycle unless the keymap itself changes.

**Dropped as over-specified (refuted by prototype and/or semantics):**

- Global 8-tap closure for every key (vertical keys clamp; diagonal keys rise then spin — a held 9 reaching the top and spinning in place is coherent Google-Earth behavior, and a held "up" key must never descend, which kills any through-apex ring).
- Through-pole continuation of vertical taps.
- "Any two-key alternation visits ≤2 views" in universal form → replaced by 5(a-c).

**Pushback recorded (for the coordinator/Stuart, not a blocker):** the prototype's observed 7↔1 2-cycle was an artifact of tangent-frame holonomy in the max-dot generator, not a property users asked for; numpad command geometry says 7↔1 crawls. If Stuart specifically wants 7↔1 to rock in place, that is a keymap-semantics decision (redefining diagonal opposition), not a traversal-table property — isolate it as such.

## Acceptance (feel + correctness, revised)

- From front, tap 9 → rests on exact (1,1,1)/√3 isometric, horizon level, one eased motion.
- Alternate 7↔3 or 9↔1 (inverse pairs) twenty times fast → two fixed named views, zero drift, zero snap. Alternate 7↔1 → smooth deterministic leftward crawl, named at every stop, zero snap. Alternate 4↔8 → staircase to the top, then bounded pole spin, zero snap.
- Tap 6 eight times from any node → full band lap (or full pole spin), returns bit-exact, constant beat.
- Mouse-drag to a random rolled orientation, tap any direction → exactly one forward motion to a named node, roll eased to 0, never moving opposite the press.
- Tap 8 repeatedly from front → front, front-top edge, top (T_0), then clamped no-ops; tap 2 from T_k descends meridian k with no up-flip.
- Tap then numpad-opposite tap returns to start from every node where the first tap MOVED; the only non-returning cases are no-op taps (toward-pole half at a pole), which are asserted to be no-ops rather than treated as inverse exceptions (320-transition snapshot test).
- The 40×8 transition table is formula-generated, frozen as a snapshot artifact, and exhaustively re-verified by Codex's prototype harness.

## Open for Stuart (approval, not a designer split)

The designers fully agree. The one user-visible FEEL change to bless: a corner tap now lands the **true isometric (35.26°, non-uniform arcs, constant beat)** instead of today's screen-diagonal 45° stop. This is the point of the redesign, but it changes what the corner keys feel like.
