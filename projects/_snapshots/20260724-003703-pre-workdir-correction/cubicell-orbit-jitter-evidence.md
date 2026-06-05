# Evidence: numpad corner orbit jitter — command/repeat/detent layer

Fable, 2026-07-10. Phase 1 evidence only, no fixes, no code changes. Basis: main after step 5 (3b07878 + doc edits).

## Layer 1: command definition + repeat + coalesce — SYMMETRIC, not the cause

- Corner keys emit ONE two-axis orbit command, not two commands: `orbitCommands.upLeft = createOrbitViewCommand(+step, -step→…)` etc. (src/editor/affordances.ts:71-89, step = `viewOrbitStepRadians` = π/4, src/editor/commands.ts:109).
- Keymap binds `numpad1/3/7/9` to the corner command ids and `numpad2/4/6/8` to cardinals (src/editor/keyboard/keymap.ts:53-62). repeatId is `input.code` (`getKeyboardShortcutRepeatId`, keymap.ts:106-112), so every key has a distinct repeatId; corners are not special. No repeatId collision defeats coalescing.
- All orbit commands share one descriptor: `kind: 'view'`, view lane, additive arbitration, `repeat: 'discrete'` (src/interaction/commands/view.commands.ts:17-41, 87-88). No corner/cardinal difference exists anywhere in the descriptor layer.
- Repeat is a SINGLE slot: `useHeldCommandInput.start()` calls `stop()` first (src/editor/useHeldCommandInput.ts:63-66), so pressing a second key kills the first key's repeat. Held corner keys do not stack with anything; alternating keys serialize into tap, tap, tap.
- Coalescing sums axes uniformly: same-frame orbit commands fold into one `{thetaDelta, phiDelta}` sum (src/interaction/viewLane.ts:47-52). Corner and cardinal coalesce identically.

Conclusion for question 1: repeat/coalesce behavior is identical for corner and cardinal keys. The asymmetry is not here. What this layer DOES contribute: alternation means every press is a fresh discrete tap into the detent machinery below, so any per-tap re-anchor cost is paid on every press.

## Layer 2: orbit detent — NOT axis-aware; the re-anchor inversion is the jitter mechanism

How a tap becomes motion (src/camera/cameraAuthorityRuntime.ts:456-519, src/camera/orbitDetent.ts):

1. `getOrbitDirection` normalizes by the max component, so a corner tap yields direction `(±1, ±1)` (orbitDetent.ts:38-57).
2. `getCompatibleOrbitProgress` (orbitDetent.ts:59-90) keeps the running progress only when the new direction is SAME (continue) or exactly OPPOSITE (negate). Any other change — every adjacent-corner alternation — falls through to `getNearestOrbitDetentOrigin`: a full re-anchor.
3. The re-anchor inversion `getSignedOrbitProgress` (orbitDetent.ts:217-259) measures ONE scalar: the great-circle angle between the initial camera direction and the current camera direction, and attributes it entirely to progress along the NEW direction's orbit path. `getNearestOrbitDetentProgress` rounds that scalar to the nearest multiple of π/4, and the origin is fabricated by rewinding the current pose by `nearest − signed` along the new direction (orbitDetent.ts:198-215).
4. The new tap motion then runs `fromProgress: 0` from that fabricated origin (getCompatibleOrbitProgress returns `progress: 0` on re-anchor), and the first sampled frame IS the origin (`sampleOrbitDetentMotion`, orbitDetent.ts:126-144).

**The snap:** whenever `signed` is not already a detent multiple, the fabricated origin differs from the pose actually on screen by the quantization remainder (up to π/8 ≈ 22.5°), and the first frame of the new ease teleports the camera to it. That is the jitter.

**Why corners break it and cardinals do not.** `orbitViewPose` rotates by `max(|theta|,|phi|)` radians about a pose-relative tilted axis (`up·theta + right·phi`, src/pose/viewPose.ts:130-153, 279-294). Pure single-axis taps from the initial pose accumulate camera-direction angle in exact π/4 multiples, so the scalar inversion lands ON the lattice and re-anchors are lossless — cardinals stay smooth even when switching axes (4→8). Corner taps compose π/4 rotations about DIFFERENT tilted axes; the composition's camera-direction angle from initial is generically NOT a π/4 multiple (two π/4 rotations about perpendicular axes give ≈1.10 rad, vs lattice points 0.785 / 1.571). So after the second alternating corner tap, every re-anchor carries a visible remainder. Verified data point: `angle(initial→after one 7-tap) = π/4` exactly (on-lattice, first alternation clean); `angle(initial→after 7 then 1) ≈ 1.10 rad` (off-lattice by ≈0.31 rad ≈ 18°) — each subsequent press snaps by that class of remainder, then eases. Alternation never reuses the queued-target fast path either: `getQueuedOrbitTapTarget` requires `isSameOrbitDirection` (cameraAuthorityRuntime.ts:620-648).

Conclusion for questions 2-3: the coordinator's hypothesis is confirmed in refined form. Detents are not per-axis; they are scalar π/4 multiples of total camera-direction angle measured from the initial pose and assumed to lie along ONE direction's path. Diagonal (two-axis) orbits leave that one-parameter lattice because their rotations compose about differing pose-relative axes, so every oblique direction switch re-anchors with a quantization remainder that materializes as an instant snap-back at motion start. The snapping does not literally fight motion mid-glide; it strikes at each direction change, which under alternation is every press.

## Discriminating predictions (falsifiable, for whoever reproduces)

- OPPOSITE-corner alternation (7↔3, 9↔1) should be SMOOTH: direction `(1,1)` vs `(−1,−1)` takes the opposite-direction branch, no re-anchor. If it jitters too, this mechanism is not the whole story.
- Adjacent-corner alternation (7↔1, 1↔3, 3↔9, 9↔7) jitters from the SECOND press onward, not the first.
- Cardinal→corner switches (8→7) should show a milder version once the pose is off-lattice.
- HOLDING one corner key (no alternation) should be mostly smooth: same direction, progress carried, no re-anchor.

## Untouched by this investigation

The gesture/trackball layer, the frame writer, and reduced-motion paths. My layer's evidence is complete; the mechanism above suffices to explain the reported symptom pattern, including why alternating adjacent corners are worst.
