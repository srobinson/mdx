# Cubicell Theory: Synthesis of Four Lenses (rev 2)

Sources, read in full:

- **L1** `cubicell-theory-signature.md` (constraints as signature)
- **L2** `cubicell-theory-capability-audit.md` (16 ALREADY, 8 KNOWN-WORK, 10 BLOCKED)
- **L3** `cubicell-theory-reach.md` (unasked-for reach, 14 ranked artefacts)
- **L4** `cubicell-theory-stickiness.md` (retention, honestly examined)
- **CHECK** read-only capability check forwarded by the merge seat
- **REV** correction pass from cubicell:general:6:5.1, both load-bearing
  claims independently verified by the merge seat on `main@ae44cbf`

Revision 2 folds seven verified corrections, restructures into four labelled
categories (principles, facts, hypotheses, roadmap), and adds the
methodological note below.

**Methodological note, stated plainly:** the four lenses worked from a shared
facts block written by the merge seat. Their convergence therefore shows a
coherent reading of one description, and is not independent corroboration.
Where this document says "all lenses agree", read "the shared framing was
internally consistent", nothing stronger.

---

## A. Durable artistic principles

Lens-derived claims that survive the fact corrections.

1. **Cubicell is a kinetic print medium and the camera is part of the
   piece.** L1: moving print with authored viewpoint. L3: states are shots,
   transport is the cut list. L4: every piece leaves as a film, viewable
   with zero context.
2. **The confinement is an aesthetic floor and the floor is the moat.** L1:
   a fingerprint recognizable from one frame. L4: the worst beginner scene
   still looks designed. L3: the piece cannot hide behind a texture. No lens
   wanted lighting, media, or recursion; L2 marks all three BLOCKED and L3
   prices them as different machines.
3. **Time is the content.** L1: a frame is one point on a meaningful path.
   L3: morph and polarity return you home with a difference.
   Return-with-a-difference is the medium's native move and the only honest
   bridge to THEORY.md.
4. **Grammar versus hero experiment (REV 6, resolving an internal
   contradiction in rev 1).** Rev 1 called burial archaeology "the piece
   only this engine can make" and then named the spinor loop the sole
   signature candidate. Resolved roles: burial, persistent ink, and lattice
   choreography are the ownable grammar, the body of work the engine alone
   supports. The spinor piece is the hero experiment, promoted to signature
   only after it teaches its rule to cold viewers and proves generative
   across several works.
5. **Retained disagreements.** D3: the persistent edge is simultaneously
   L1's density ceiling (distant cells accumulate into crosshatched texture)
   and L3's postage-stamp-to-billboard asset; the deciding cell-count
   threshold is unmeasured and cheaply measurable. D4: L1 locates stickiness
   in mastery of a finite instrument, L4 in the make-post-return loop;
   sequencing favors L4 because the loop is broken at export (facts B7, B8)
   while the mastery loop cannot compensate without circulation.

---

## B. Source facts

Each fact carries its source and sha. All verified on `main@ae44cbf`,
2026-08-02, by read-only inspection; no code was run for this synthesis.

- **B1. Rotation is engine-representable, per cube, in radians,
  unwrapped.** `CubeCell.placement.rotation: Vec3`;
  `src/shared/three.ts:createTransformMatrix` builds `new Euler(...rotation)`
  directly, and `createCubePlacement` copies values without clamp or modulo.
  0, 2π, and 4π are distinct storable values, and a morph from 0 to 4π
  genuinely turns twice (CHECK, corrected to radians by REV 2; rev 1's
  degree figures were wrong by ~57x).
- **B2. Rotation has NO product authoring surface.** `rg "rotat"` returns
  zero hits in `src/domain/cubeOperations.ts`,
  `src/editor/controlBindings.ts`, and `src/panels/CubeSection.tsx` (REV 1,
  merge-seat verified). Rotation is developer-authorable, and a user of the
  product cannot author it today.
- **B3. Polarity is authored per state and cuts discretely.** Carried on
  `Pose` via `createPoseRevision`; `sceneMorph` applies it at
  `MorphSettings.cutAt` and it is absent from the continuous morph channels
  (CHECK).
- **B4. Only theme-keyed part colors invert.** `resolveCubePartColor` maps
  "theme" to `polarity.contrast`; explicit black and white keys are never
  swapped (CHECK).
- **B5. Signed sweep has an existing precedent.**
  `src/domain/cameraTrack.ts` carries `normal` plus `sweepRadians`,
  separating the path swept from the endpoint pose (REV 7).
- **B6. Morph between equivalent endpoints cannot encode a turn.** Because
  interpolation reads endpoint values, equal poses produce zero delta; a
  turn survives only while values happen to be stored unwrapped. Any Turn
  authoring surface must therefore preserve signed sweep separately from
  endpoint pose, reusing the B5 precedent rather than inventing a parallel
  representation (REV 7).
- **B7. Export has two realtime paths, and the deficiency is that both are
  realtime.** `src/export/streamRecorder.ts` supports
  `canvas.captureStream(60)` and `getDisplayMedia()`, sharing one bounded
  MediaRecorder pipeline (REV 3, correcting rev 1's "only a tab grab").
  There is no deterministic fixed-step export, no exact frame sampling, and
  no immutable export job; PROJECT.EXPORT.md specifies these and is status
  Proposed.
- **B8. The finished piece carries no route back.** No attribution, link,
  or reentry path on any export (L4, from `streamRecorder.ts` and
  STORAGE.md's single-user localStorage model).
- **B9. Audit shape.** Sixteen capabilities executable today and unused as
  art, eight with a known path, ten blocked by the model, including engine
  phase, exchange antisymmetry, recursion content, and media interiors
  (L2).

Resolution of D1 (spinor buildability), restated against these facts as
three tiers: **engine-representable** yes (B1, B3); **developer-authorable**
yes, by hand-editing states at dev level (B1, B3, B4); **product-authorable**
no (B2, B6). L2's BLOCKED verdict was about engine-carried phase and stands;
L1/L3's "authorable today" was true only at the developer tier and rev 1
overstated it as cost A.

---

## C. Creative hypotheses

Each hypothesis carries its validation test. None is a fact.

- **C1. The relative-phase spinor piece (REV 4, replacing rev 1's
  design).** Rev 1 had a structure rotate one full turn and arrive with
  polarity flipped by an authored cut. REV 4's critique is decisive on both
  physics and craft grounds: a lone global phase is unobservable in
  principle, and flipping polarity at the endpoint encodes the idea by
  fiat, a color-flip gimmick with a physics title. The honest version is
  relational: the piece splits into two branches, one branch takes one
  extra full turn (2π of additional signed sweep), they recombine, and the
  disagreement is shown as cancellation or figure-ground inversion; a
  second turn restores agreement. The phase becomes visible only in the
  reunion, which is both the correct physics (only relative phase is
  observable) and the better image (the drama is between the branches, and
  the authored inversion now depicts a measured difference rather than
  asserting one).
  *Craft requirements carried over from rev 1:* the rotating structure must
  be visibly asymmetric or the turn is uncountable (a bare cube returns to
  visual identity every quarter turn; Behiel's transcript plants a flag for
  exactly this reason); parts must be theme-keyed (B4) or an inversion
  reads as a bug; user-facing language says "one full turn", never
  radians (REV 2).
  *Dropped claim (REV 5):* rev 1 said the two-turn loop is "seamless by
  construction". Wrong layer: topology gives contractibility, and export
  continuity comes only from matching authored endpoints. Seam quality is
  craft, unclaimable for free.
  *Validation test:* a cold viewer, two silent watches, no labels, can
  state the rule ("the branch that turned once disagrees, turning again
  restores agreement" in any wording). Fails that, it is a demo and no
  title rescues it.
- **C2. Burial archaeology shorts.** Dense assembly excavates itself on the
  transport, camera owning each reveal (L3's single best; L2 ALREADY rows
  for visibility, `isFaceBuried`, reveal). *Validation:* the piece reads as
  choreography to a viewer who does not know burial is an editor
  optimization, and cannot be reproduced in a generic cube editor.
- **C3. The four-state trailer loop.** Three to five states, locked
  cameras, cuts and morphs as the edit, one interior reveal, a 15-second
  silent loop that is also the product's trailer (L3 items 4, 5; L4's
  film-shaped artefact). *Validation:* postable as-is, and a newcomer who
  watches it can name the tool's look.
- **C4. Seam typography.** Hand-built glyphs whose strokes are
  junction-surviving edges, shared as structure templates (L3 item 3;
  answers L4's anonymous-first-session leak). *Validation:* a newcomer
  reaches a personally owned artifact, their word, in one session.
- **C5. Selection-query stage lights.** Queries pulse part sets on the
  beat; predicates become pads (L3 item 6; L2 selection-as-targeting).
  *Validation:* a live take where the performer never touches a mesh, only
  queries.
- **C6. The density ceiling number.** One authored scene, camera retreating
  object to pattern to texture, per polarity; record where legibility dies.
  *Validation:* a stated cell count that future scale pieces compose
  against, settling A5/D3.

---

## D. Roadmap priorities

Two orderings, per REV. Rev 1 ranked export fifth while calling it the gate,
which is exactly the confusion two orderings prevent. Cost scale is L3's
(A author-only, B tiny glue, C small product surface, D subsystem).

### D-i. By payoff over cost (cheapest and highest first)

1. **Trailer loop (C3).** Cost A, product-authorable today. First finished
   piece, gallery seed, test article for the export path.
2. **Burial archaeology short (C2).** Cost A to B. The ownable grammar's
   flagship (A4).
3. **Relative-phase spinor piece (C1).** Cost B at the developer tier:
   engine-feasible and developer-authorable today (B1, B3), with no product
   surface (B2). Rev 1's cost A was wrong. Highest thesis density on the
   list; run it as the hero experiment it is.
4. **Seam typography starter glyphs (C4).** Cost A per glyph, B for the
   template library.
5. **Density ceiling measurement (C6).** Cost A and an afternoon; converts
   the signature constraint from folklore into a composition number.
6. **Cut-vs-morph as inspector control.** Cost per L2 KNOWN-WORK: panel and
   command only. Unlocks authored path-dependence for non-developers.
7. **Turn command surface.** Cost C: command, control surface, and signed
   sweep preserved separately from endpoint pose, reusing the
   `sweepRadians` precedent (B5, B6). Converts the spinor genre from
   developer-only to product vocabulary.
8. **Deterministic export (PROJECT.EXPORT.md).** Cost C toward D, the
   largest item, and the highest structural payoff (B7, B8, A5/D4).
9. **Selection-query stage lights (C5).** Cost B to C.

### D-ii. By sequencing (what unblocks what)

1. **Trailer loop and density measurement first.** Both cost A, both feed
   everything: one produces the first artefact and the other the
   composition limit every later piece obeys.
2. **Deterministic export starts early, in the proposal's own order:**
   performance take, then fixed-step export in-process, before any
   isolation topology (B7). Every artefact in this program terminates in
   this exit; each piece shipped before it exists leaves softer and more
   anonymous than the medium (L4). Its cost puts it eighth by ratio; its
   position in sequence is second.
3. **The spinor experiment runs in parallel at the developer tier** (C1
   needs no product surface to be validated). Its outcome gates item 4.
4. **Turn surface only if C1 validates.** Building product vocabulary for
   a genre whose hero piece failed its cold-viewer test would be spending
   C-level cost on an unproven hypothesis (A4).
5. **Typography, cut-vs-morph inspector, stage lights follow demand**, in
   whichever order the first shipped pieces expose as the binding gap.

---

## Verdict

The machine is finished enough for its first real art and nobody has made it
yet; B9's sixteen unused capabilities remain the review's sharpest finding.
The corrected picture is more honest and slightly harder than rev 1: the
grammar (burial, ink, choreography) is product-authorable today, while the
hero experiment needs a developer's hands (B2) and a relational design (C1)
to be more than a color flip. The export exit is still the structural debt,
now precisely diagnosed: two realtime capture paths and no deterministic
frame sampling (B7). Sequencing, then: make the grammar pieces now, start
the exporter now, validate the spinor experiment at the developer tier, and
let its result decide whether the product grows a Turn vocabulary.
