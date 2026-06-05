# Slice 3 arrival scout: reuse map and seam verdict

Read-only scout of worktree `.claude/worktrees/transitions-ux`, branch `slice/transition-panel @ 2b7188d5`.
Prior inputs read: `cubicell-brainstorm-transitions-shape.md`, `cubicell-scout-transitions-domain.md`,
`cubicell-scout-transitions-authoring.md`. All citations verified against this branch, which has moved
past those docs' `main @ ae44cbf` baseline (the class-applicability inspector work landed since).

## 1. Where arrival form lives

**Owning symbol: `domain/morphSettings.ts:MorphSettings`, in the domain (authored, persisted).**
Form rides where timing already rides: inside `Transition.settings`, per gap, per class. The evaluator
consumes it; it never owns it.

The precise gap, confirmed on this branch: `evaluation/sceneMorph.ts:sampleSceneMorph` schedules added
cells fully (staggered start via `planClassMotion`, eased ramp via `easingFor`, quantize via
`quantizeProgress`) and then returns the added cell **unchanged**, writing only `Moment.presence`.
`evaluation/scoreAt.ts:applyMomentToLayout` consumes presence as a scale multiplier and nothing else.
So arrival FORM is a constant hardcoded in the evaluator; every timing control upstream of it works.
Departure is the mirror: removed cells are appended verbatim with `1 - departEase`. The brainstorm's
correction stands verbatim in current code: this is "promote one hardcoded manner to an authorable
channel", not "add a transition where none exists".

Placement inside the type: a new optional field family on `MorphSettings`, **not** inside
`domain/morphSettings.ts:ClassMotion`. `ClassMotion` is pure timing (easing, order, staggerMs,
quantize) and the branch just built `panels/motion/MorphInspector.tsx:classMotionApplicability`
around exactly that purity; mixing an effect variant into it would break the timing/form separation
the stored note warns about, and would force `glide` to carry a field it cannot honor.

Vocabulary: all named constraints confirmed live (`frameId` in `domain/scene.ts`; `glide` claimed
three ways by `MorphClassId`, `camera/cameraGlideCommand.ts`, and `state/preferencePort.ts`;
`arrangement` on `SceneMorphTopology.arrangement` and `Moment.arrangementOffset`; `cut` on
`TransitionMode` and `PoseSegment.cutAt`). `form`/`Form` and `manner` have **zero** occurrences in
`src/domain` (grep `Form\b|manner|Manner`). Either is free; `form` reads best beside the existing
field grammar (`arriveForm`, `departForm` sort correctly under the alphabetical-members convention).

## 2. The CameraOrbitArc claim: tested, and it is a false analogy for arrival

The stored claim: `CameraOrbitArc` "supplies the proven route model" because it solves "travel from
A to B along a chosen path rather than straight interpolation, landing exactly on B".

What the arc machinery actually is (`domain/cameraTrack.ts`): a signed unbounded datum
(`sweepRadians`), an endpoint-congruence check (`isCameraOrbitArcEndpointCompatible` verifies the
authored arc actually rotates A's view direction onto B's), and derive-on-reject
(`resolveCameraOrbitArc` falls back to `deriveShortestCameraOrbitArc`). The load-bearing invariant is
**"authored route data is a preference; endpoints are the authority"** — and it only means anything
because both endpoints exist independently of the authored datum and can contradict it.

Arrival has one endpoint. The cell exists only in scene B; the "from" is not an authority the
authored form can disagree with — the "from" IS the authored datum. Any synthesized origin
interpolated toward B lands exactly on B by construction (`sampleSceneMorph`'s `endpointFrame`
already snaps terminals, and `interpolateCell` returns `after` at progress 1). There is nothing to
congruence-check and nothing to derive on rejection beyond ordinary optional-field defaulting
("no form authored → today's behavior"), which is not a route model, it is a default.

So: **false analogy for arrival.** What genuinely transfers is one level down and already noted in
the brainstorm — the trio is real precedent for a future glide `turn`/sweep channel, where both
endpoint rotations do exist and congruence mod 2π is a real question. That is the brainstorm's
instances two/three, not this slice. Nobody needs to route arrival through camera code.

## 3. What exists that this binds to (never reinvents)

- **Timing machinery, untouched.** `domain/assemblyOrder.ts:OrderMode` (creation/sweep/radial/
  shell/spiral/random; UI labels Made/X/Y/Z/Radial/Spiral/Shell/Dice in
  `panels/motion/motionOptions.ts:orderModeOptions`), `sceneMorph.ts:planClassMotion`,
  `classProgress`, `easingFor`, `quantizeProgress`. Form is consumed at the same per-cell
  `classProgress` the ramp already uses, so every form composes with Order/Stagger/Easing/Steps
  for free. No timing code changes.
- **`sceneMorph.ts:interpolateCell` is the general A→B interpolator** (offset, rotation, scale,
  size, face opacity). Arrival form = synthesize the missing endpoint (a ghost of the arriving cell
  with the form's offset/scale/opacity applied) and interpolate ghost→cell. Fade falls out of the
  existing opacity lerp; drop-in falls out of the offset lerp; the current scale-pop is exactly
  `lerp(0, scale, p)` = `scale * p`, so the default form reproduces today's frame bit-for-bit.
- **Presence stays the sole absence gate.** `scoreAt.ts:getMomentCells` ("presence zero is absence
  everywhere") and `applyMomentToLayout` need not change: the default form keeps today's eased
  presence ramp; positional forms write gate-only presence (0 before the cell's staggered start,
  1 after) and carry appearance in the interpolated cell. This also protects the other
  `applyMomentToLayout` consumer, the assembly track, from any blast.
- **Authoring path, complete on this branch.** `panels/motion/MotionInspector.tsx:TransitionInspector`
  already computes per-gap topology, resolves the primary class
  (`sceneMorph.ts:resolvePrimaryMorphClass`), and dispatches `patch-transition`;
  `MorphInspector.tsx:classMotionApplicability` is the established pattern for "this control is
  inert for this class" — a form control is arrive/depart-applicable, glide-disabled, exactly that
  machinery. `panels/SegmentedField.tsx:SegmentedField` + an options table in `motionOptions.ts` is
  the preset front door; a parametric detail scrub appearing only for parametric forms matches the
  progressive-detail note and the existing disabled-control convention.
- **Wire and validation, one edit each.** `state/scoreValidation.ts:isMorphSettings` key list plus
  one `isMorphForm` guard; `domain/morphSettings.ts:patchMorphSettings` normalization following the
  existing omit-undefined convention (`normalizeQuantize` precedent); `authoredInverse` passes
  settings by reference, so undo costs nothing.
- **`domain/selectionQuery.ts:SelectionExpression` exists and is healthy** — but it belongs to the
  subject-scoped route language (brainstorm candidate B), whose own §8 evidence test (do real
  projects ever want two distinct manners among added cells?) is still unanswered. Slice 3 needs
  per-class uniform form only; the language stays parked.
- **Other path/curve/route code: none found.** Searches: grep
  `arc|spline|bezier|curve|route|trajectory|waypoint` across `src/**/*.ts{,x}`. Hits resolve to
  `CameraOrbitArc` (the only geometric route model), `score.ts:CadenceCurve` (stagger timing
  distribution, not form), studios URL routing (`studios/catalog.ts:beginRouteLoad`), and panel
  scroll panning. Nothing else models travel.

## 4. What is NEW, minimally

**One concept: `MorphForm`** — a small closed discriminated union (default `grow`, plus e.g. `fade`
and an offset variant), stored as optional per-class fields on `MorphSettings`, consumed in
`sampleSceneMorph`'s added and removed branches by synthesizing the ghost endpoint and reusing the
existing interpolation. Everything else is one edit to an existing surface: one guard, one patch
branch, one options table, one gated control. Departure is the same concept reversed (ghost target),
not a second concept. It becomes several concepts only if subject scoping or a channel bag rides
along; both stay parked behind the brainstorm's own unanswered evidence tests.

## 5. Seam verdict

**`feasible: MorphSettings gains an optional per-class MorphForm (one new closed union); sampleSceneMorph consumes it by synthesizing the missing endpoint and reusing existing cell interpolation; presence stays the sole absence gate; scoreAt and the Moment contract are untouched.`**

The default-form-equals-today equivalence (`lerp(0, s, p) === s * p`) is the migration-free proof the
brainstorm demanded, and the whole change lands inside the settings-keyed phase that
`transport/activeTransitionPlan.ts:createActiveTransitionPlanCache` already re-runs on every edit —
no cache split, no phase smuggling, no new track kind.

## 6. Quality map

| Finding | Fact | Disposition |
| --- | --- | --- |
| Vec3 helper triplication | `sceneMorph.ts:lerpVec3`/`isSameVec3`, `gridLayout.ts:isSameVec3`, and `cameraTrack.ts:lerpVec3Into`/`sameVec3` are private copies; `shared/math` holds only scalar `lerp`/`clamp`. | **During.** Form work edits `sampleSceneMorph`'s branches anyway; lift exact-compare `isSameVec3` and `lerpVec3` to `shared/math` then. Leave `cameraTrack`'s variants: `lerpVec3Into` is the allocation-free per-frame pattern and `sameVec3` is epsilon-based — different semantics, not duplication. |
| Duplicate topology computation | `MotionInspector.tsx:TransitionInspector` runs `prepareSceneMorphTopology` in a `useMemo` in parallel with `createActiveTransitionPlanCache` for the same endpoint pair. | **Defer.** Pure and cheap; two owners is a coherence smell, not a bug. Unify only if a form preview needs plan-level data in the inspector. |
| Dormant `TransitionMode` "cut" | Deliberate, documented in `domain/score.ts` ("never drop it as an oversight"); still no editor control. | **Decide during design.** The form surface is the natural moment to surface or explicitly park `mode`; do not let a third design round leave it undocumented on the new control. |
| Mid-flight occupancy nomination | `interpolateCell` assigns `after.placement.coord` from the first frame; occupancy is coord-keyed, burial only geometry-gated (`domain/exposure.ts:isFaceBuried`). | **During, as constraint.** Offset-based forms move cells through occupied space; keep forms offset-only (never coord-authored) so nomination stays a non-issue, and say so in the spec. |
| Aliased default settings | `stateTransition.ts:defaultTransition` shares `defaultMorphSettings` by reference across all default transitions. | **Defer.** Safe because `patchMorphSettings` is immutable; new optional fields must keep the omit-undefined convention so the shared default stays field-free. |

## Searches run

`grep -rE "arc|spline|bezier|curve|route|trajectory|waypoint"`, `grep -rn "lerpVec3|isSameVec3|sameVec3"`,
`grep -rn "glide"`, `grep -rn "Form\b|manner|Manner" src/domain`, `grep -rn "route|Route"` (URL routing
only), plus full reads of `morphSettings.ts`, `sceneMorph.ts`, `scoreAt.ts`, `cameraTrack.ts`,
`score.ts`, `stateTransition.ts`, `scoreValidation.ts`, `assemblyOrder.ts`, `motionOptions.ts`,
`MorphInspector.tsx`, `activeTransitionPlan.ts`, and `TransitionInspector` in `MotionInspector.tsx`.
No fmm index exists in this worktree and generating one would write to it, so navigation was
grep/read under the read-only constraint.
