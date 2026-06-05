# Orbit detents in orientation space — proposal B (domain + feel)

Fable, 2026-07-10. Independent of proposal A. Lens: what the detents should BE for a cube viewer and what tapping should FEEL like. Assumes the agreed mechanics: motion = slerp from the live orientation to a target orientation, continuity free, no fabricated origins.

## 1. What the detents are: the 26 principal views, exactly

Cubicell is a cube viewer. The orientations a user actually wants to rest on are the cube's own symmetry views:

- **6 face-on** views (front, back, left, right, top, bottom): direction along ±axis.
- **12 edge-on** views: direction along (±1,±1,0) and permutations, elevation or azimuth 45°.
- **8 corner-on** views: direction along (±1,±1,±1), the three-face isometric. Azimuth 45°, elevation atan(1/√2) ≈ **35.264°**, not 45°.

That last number is the heart of this proposal. The current π/4 screen-lattice can never rest on a true corner view; it stops ~10° above it, where the three faces are visibly unequal. A cube viewer that cannot land the isometric is broken at the identity level: the 3-face corner view is the single most recognizable cube orientation (every CAD ViewCube leads with it). So the detent set is the **26 principal views, at their exact directions**, and the uniform lattice is explicitly rejected.

Not the 24-element rotation group: that group enumerates full orientations including roll, and no user of this tool wants rolled resting states. Detents are (view direction, canonical up) pairs where up is the no-roll sky-up frame; only the two pole views (top, bottom) need an explicit up policy (section 5). Roll stays out of the detent vocabulary entirely.

The home view anchors the set for free: `defaultCamera` is dead-on front (position (0,0,5), up +Y), which IS a member. Every session starts on a detent.

## 2. What taps traverse: three ring families on the view sphere

Map the numpad as a compass rose over the view sphere (screen-relative, matching the current relative-orbit identity — 4/6 azimuth, 8/2 elevation, corners diagonal). Taps move along great-circle rings through the canonical views:

**Horizontal rings (4/6).** The equator through 4 faces and 4 vertical edges: F, E, F, E… eight stops, uniform 45°, closes in 8 taps. Two taps = next face. This is exactly today's cadence; it survives unchanged.

**Vertical rings (8/2).** The meridian through front, front-top edge, top, back-top edge, back, and down the other side: eight stops, uniform 45°, closes in 8 taps. Also today's cadence.

**Diagonal rings (7/9/1/3).** The great circle leaving a face view in the screen-diagonal direction passes exactly through the symmetry views. Leaving front (0,0,1) toward up-right: front face → corner (1,1,1)/√3 at arc 54.74° → right-top edge (1,1,0)/√2 at 90° → corner (1,1,-1)/√3 at 125.26° → back face at 180° → and mirrored home. Eight stops — 2 faces, 2 edges, 4 corners — closing in 8 taps, with **non-uniform arcs alternating 54.7° and 35.3°**. The non-uniformity is not a defect to smooth away; it is the price of resting on true symmetry views, and it is invisible if the beat is constant (section 3).

So: **a corner tap from a face view lands corner-on in one tap.** That is the single feel headline. Today a corner tap lands nowhere nameable; in this model every tap, in every direction, from every resting view, lands on a view with a name.

**The general rule (generates the whole graph).** From the current canonical view, a tap selects the adjacent canonical view whose direction from here best matches the tap's screen-space direction (max dot product against the requested tangent); ties resolve to the higher-symmetry cell (face beats edge beats corner). "Adjacent" is adjacency on the cube's cell complex — the 26 views are the facelets of the ViewCube, and neighbors are touching cells. This rule reproduces the three ring families above from any starting point and answers the awkward cases mechanically, e.g.:

- From corner (1,1,1), tap 9 again: continues over the corner to the right-top edge (the diagonal ring, as above).
- From corner (1,1,1), tap 4 (left): back toward the front-top edge or front face depending on exact screen tangents; the resolver picks the adjacent cell, never a skew non-view.
- Alternating 7↔1 or 1↔3 — the jitter reproducer — oscillates between two fixed adjacent canonical views. Two orientations, one slerp between them, deterministic every press. Jitter is impossible by construction, not merely damped.

The adjacency graph should be precomputed and unit-tested as a table (26 nodes × 8 directions), not resolved geometrically at runtime; the geometric rule is the generator and the tiebreak documentation.

## 3. Cadence: constant beat, not constant speed

Per-tap duration stays fixed (`cameraOrbitDetentMotionDurationMs`, the existing beat) regardless of arc length. A tap is a musical beat; 54.7° and 35.3° steps at the same beat feel identical, whereas constant angular velocity would make diagonal traversal audibly stutter (long-short-short-long). Keep easeOutQuart. Held keys keep discrete repeat at the existing repeat interval — hold = a drumroll of taps, each landing on a named view, never a continuous glide that blurs past them. All three constants remain in config/motion, not inline (repo rule: feel numbers live in knobs).

Invariants worth asserting in tests: every ring closes in exactly 8 taps; 8 taps of any single key returns to the start view bit-exactly; tap then opposite tap returns to the start view; every intermediate resting state is one of the 26.

## 4. Re-align after free drag: forward-only, one motion

After a mouse orbit leaves the camera at an arbitrary orientation, the first tap must do exactly one thing: **slerp to the nearest canonical view in the tap's direction.** Concretely: among canonical views within a forward cone of the tap's screen direction, take the nearest by arc; that view is the tap's target, and the tap is "spent" on the correction.

- Never snap-then-step (two motions per press reads as a stutter — the exact insult we are removing).
- Never step-then-snap (lands past where the finger pointed).
- **Never move backward against the tap direction.** The old model's snap-back was the jitter; forward-only is the law. If the nearest canonical view lies slightly behind the tap direction, the tap goes to the next one ahead instead.
- Within a small ε of a canonical view (call it rested), taps step the graph normally. ε is a config knob.

Feel result: after a drag, the first tap "catches" the nearest resting point ahead of your thumb, like a ratchet engaging. Second and subsequent taps are pure graph steps.

## 5. Up vector and pole transits

Detents carry no roll: canonical up is the no-roll sky-up frame for all 24 non-pole views. The two pole views canonicalize up to the nearest grid axis at arrival (a grid editor's top view should align with the grid), choosing among the four axis-aligned ups by minimum twist from the approach. Leaving a pole, the tap's direction disambiguates which meridian to descend. During any slerp the horizon must stay level: interpolate the view direction along the great circle and derive up per frame from the no-roll frame; only a pole transit (vertical ring passing over the top) holds its travel plane fixed through the pole instead, so walking over the top does not spin the world.

## 6. Guardrails for the math design (where technically-closed goes feel-wrong)

1. **Corner detents must be exact (±1,±1,±1) views.** Any uniform-angle lattice in orientation space puts "corners" at 45° elevation, ~10° off isometric. Non-uniform arcs are mandatory; reject designs that trade view correctness for step uniformity.
2. **No free SO(3) slerp between detents.** Quaternion slerp between two no-roll orientations generically rolls the horizon mid-flight. Interpolate the view direction on the sphere and re-derive up per frame. Level horizon throughout is non-negotiable except pole transits.
3. **Constant beat, not constant angular velocity** (section 3). A speed-uniform design makes the diagonal ring feel arrhythmic.
4. **Forward-only re-align** (section 4). Any design that can move the camera opposite the pressed direction, however briefly and however small, reintroduces the perceived jitter.
5. **Every resting state must have a name.** If a proposed detent cannot be called "front", "top-right edge", or "front-top-right corner", it is not a detent for this product. This kills clever intermediate stops (e.g. 22.5° sub-steps) unless the domain grows vocabulary for them.
6. **Pole up must be grid-aligned**, not approach-frozen; approach-frozen up makes top view a different orientation every visit, which breaks the "canonical view" promise for screenshots and grid editing.

## 7. Ownership seams (MODEL.v2 alignment)

The canonical view set and the adjacency table are **view policy** (they are statements about what a cube viewer is): they belong beside `viewportFocus`/`selectionFocus` in `src/view`, exported as data. The traversal, slerp, re-align cone, and beat are **camera adapter mechanics** in `src/camera`, consuming that data. Commands stay serializable orbit intents; the descriptor layer is untouched (evidence pass showed it symmetric). Feel constants (beat, repeat interval, rest ε, forward cone) live in `cubicellConfig`. This keeps the detent vocabulary reusable by any actor — an LLM dispatching "go to front-top-right corner" is the same actor thesis, one step closer.

## 8. Acceptance feel tests

- From front, tap 9: camera rests on exact (1,1,1)/√3 isometric, horizon level, one eased motion.
- Alternate 7↔1 twenty times fast: two fixed orientations, zero drift, no intermediate snap, every landing named.
- Tap 6 eight times from any face: full equator lap, returns bit-exact, F-E-F-E cadence at constant beat.
- Mouse-drag to a random orientation, tap any direction: exactly one forward motion to a named view.
- Tap 8 three times from front: front → front-top edge → top with grid-aligned up; continue over pole without world spin.
