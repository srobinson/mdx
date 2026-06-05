---
title: cubicell colour system, visual-designer brainstorm
type: design
tags: [visual-design, cubicell, colour, oklab, contrast]
summary: Colour enters as chroma and hue at fixed lightness; the sRGB gamut itself splits the wheel into a dark-ink half and a light-paper half, so hue becomes a second signal of polarity instead of a competitor to it.
status: active
source: visual-designer
confidence: high
created: 2026-08-05
updated: 2026-08-05
---

# Thesis

Lightness is the authoring channel. It already answers "is this cube black or white", so it cannot also answer "which
way does this face point". That is why #160/#162 failed, and any scheme spending L on modelling fails the same way. The
fix is to move every new signal off L entirely.

That leaves hue and chroma, and they are **free**: two colours at equal L measure a WCAG contrast ratio of **1.0:1**
against each other (measured with the repo's own matrices from `src/scene/colorSpace.ts`). A hue difference cannot be
misread as a lightness difference, because there is none. The ambiguity the owner rejected is arithmetically impossible
in this channel.

**The gamut then hands us the design.** sRGB chroma capacity at a given L is violently asymmetric:

```
 max chroma      h25    h80   h145   h200   h265   h320
 L=0.12 (black) 0.060  0.037  0.050  0.027  0.092  0.071
 L=0.22         0.093  0.049  0.073  0.039  0.154  0.110
 L=0.93         0.035  0.065  0.129  0.088  0.033  0.055
 L=1.00 (white) 0.000  0.000  0.000  0.000  0.000  0.000
```

Dark ink holds real colour only toward blue/violet/crimson, light paper only toward green/cyan/lemon. The families are
pushed onto **opposite halves of the wheel by physics**, not taste, so hue becomes a *redundant* encoding of polarity: a
tinted dark cube is deep blue, a tinted light cube pale green, and the two-tone composition is reinforced. Two
consequences:

1. **Constant-chroma hue rails do not exist.** C=0.11 is in gamut at h264 and clips at h25, h80, h145, h200, h320.
   Clipping silently mutates L, reintroducing the exact ambiguity we are avoiding. Every scheme below parameterises
   chroma as `t x cusp(L, h)`, t in 0..1, `cusp` being a binary search for max in-gamut chroma. The authored knob is
   *saturation intent*, never absolute C.
2. **Colour costs a one-time L concession at the poles and nothing after.** White (L=1.0) has exactly zero chroma
   capacity; #050505 measures L=0.115 and has very little. Tinting requires 0.115 -> 0.22 and 1.0 -> 0.93, dropping
   absolute contrast 20.4:1 -> 14.3:1 worst case. Paid once, only by cubes that opt in, and 14.3:1 is still four times
   the AA threshold.

# Named Schemes

## 0. Gamut Rails (the substrate every scheme sits on)

Not a look, the shared primitive: two rails, each a fixed L with a bounded hue arc and cusp-normalised chroma.

```
INK RAIL    L=0.22, t=0.75          PAPER RAIL  L=0.93, t=0.75
  h264  C=0.117  #01104f              h110  C=0.152  #eef16e
  h290  C=0.096  #1c0c43              h145  C=0.097  #c0fac0
  h320  C=0.082  #2a0932              h175  C=0.078  #b0fae5
  h350  C=0.072  #31081f              h200  C=0.066  #b4f6f9
  h25   C=0.070  #340909              h80   C=0.049  #f9e5c4
```

Uncoloured cubes keep #050505 / #ffffff untouched; t=0 lands on #1b1b1b / #e8e8e8, so the rail is entered explicitly.
Hues 55-70 are absent by design: `themeColorTokens.selectionAccent` #e87d0d measures L=0.696 h~60 and selection chrome
must stay the only orange in frame. The gamut is narrow there anyway, so this costs nothing.

## 1. Axis Wash. Geometry input: world coord along one axis

Hue sweeps the family arc across the composition's extent; L and t constant. Normalise `pose.renderPosition[axis]` over
the scene bounding extent, map onto the rail arc.

```
ink   arc h264 -> h350   #01104f ... #31081f      paper arc h200 -> h110   #b4f6f9 ... #eef16e
```

Three knobs (axis, arc start, arc sweep) restyle a thousand cubes coherently. The product thesis executed literally, and
the scheme to show the owner first for *range*.

## 2. Enclosure Chroma. Geometry input: occupied-neighbour count

Ambient occlusion reborn in the channel that can afford it. Chroma is the one perceptual quantity with a natural
ordering that never touches L. Exposed shell reads near-neutral, crevices and pockets saturate: the information #162
carried, none of its ambiguity.

```
t (burial 0..1)   0        0.25      0.5       0.75      1
ink   h264      #1b1b1b  #111a2d  #07173e  #01104f  #000061
paper h145      #e8e8e8  #dbeedb  #cef4ce  #c0fac0  #b0ffb2
```

Both polarities survive untouched: chroma adds to whatever L the face holds, so the treatment is polarity-agnostic by
construction rather than by a second tuned table.

## 3. Facet Hue. Geometry input: face orientation

Direct replacement for the rejected mechanism. Same call site, same shape, hue degrees instead of L delta, chroma
cusp-normalised per hue so nothing clips.

```
base h264, ink, t=0.72
top 0deg   front +18   right +34   left -22   back +52   bottom -40
 #01114d    #170e45     #210c3d    #071d2b    #280a33     #081e25
```

**Honest position: this gives facet separation, not modelling.** Hue has no perceptual ordering the eye reads as
"further from the light". Adjacent faces become distinguishable and the cube reads as a solid rather than a silhouette,
but nobody will perceive it as lit. If the owner wanted lighting, nothing respecting the L constraint can deliver it. If
he wanted *form legibility*, this delivers it at 1.0:1.

## 4. Axis Ink. Geometry input: edge axis

Colour lives only on edges; the face field stays absolute #050505 / #ffffff. `CubeEdgeInstance.axis` is already on the
instance and the edge path already branches in `createColorWriteContext`.

```
L=0.30, t=0.75    x h25 C=0.093 #531514    y h145 C=0.072 #123715    z h265 C=0.156 #061e7a
```

Cheapest and safest thing here: the op-art field is untouched by definition and the wireframe carries the whole palette.
**Ship this first as the proof, then Axis Wash for range.**

## 5. Field Tint. Geometry input: none, one global knob

Cheapest way to colour the product without touching a cube. `themeColorTokens.workbench` #464646 measures L=0.394;
hold that L, add trace chroma at h264/h145: `C=0.008 -> #44464b / #434743`, ceiling `C=0.030 -> #3e4657 / #3c4b3c`.
Hard rule: field chroma never exceeds cube chroma, or cubes read as cut-outs on a coloured board.

# Contrast Preservation

The two-tone identity is defended by arithmetic rather than by restraint.

```
neutral #050505 vs #ffffff                20.4:1  today      ink h264 vs #ffffff (mixed)   17.7:1
ink h264 vs paper h145                    14.8:1             #050505 vs paper h145 (mixed) 17.1:1
worst pair across the full 5x5 rail grid  14.3:1  <- the guarantee
within ink or paper family, any two hues   1.0:1  <- the point
```

Black and white cubes coexist with coloured ones because they sit on the same rails, at the extreme end. A tinted dark
cube and a pure black cube are both unambiguously *dark*; they differ by hue, which is 1.0:1 and cannot read as a value
step. Mixed pairs measure 17:1, above the all-coloured worst case, so mixing is the *safe* configuration. Both
polarities survive because every scheme keys chroma to the face's already-resolved colour, as
`shiftLightnessForContrast` does today for its flip direction. Regression guard worth writing: cross-family ratio >=
12:1 and within-family <= 1.15:1 across the rail grid. That would have failed #160 on landing.

# Reuse

- `src/scene/instancedPartMeshCore.ts` -> `resolveInstanceColor` (line 400). **The single seam.** Colour is CPU-resolved
  per instance into `instanceColor` via `setColorAt`, so every scheme here is a pure function at this one call site. No
  shader work, no new draw calls, instancing untouched. Sibling `createColorWriteContext` already branches on `partKind`
  (edge/face/slot): scheme selection and the resolved rail hoist there, exactly as `edgeLightnessDelta` and `slotColor`
  do today. And `applyInstanceOpacity` in the same file is the proven template for the *time* half (`onBeforeCompile` +
  `InstancedBufferAttribute` + varying).
- `src/scene/colorSpace.ts` (103 lines) -> `setLinearSrgbToOklab`, `setOklabToLinearSrgb`, module-private today. Export
  them, or add a sibling `shiftChromaTowardHue(target, hue, t)` beside `shiftLightnessForContrast` reusing the
  `oklabFrom`/`oklabTo` scratch to keep the per-frame path allocation-free. Cusp search is ~20 iterations: hoist per
  rail, never per instance. `resolveLerpedPartColor` already interpolates in OKLab, so tints morph-tween **for free**.
- `src/theme/scenePolarity.ts` -> `cubeFaceLightnessDeltaById`, the slot Facet Hue replaces one-for-one.
  `ScenePolarityConfig.edgeLightnessDelta` is the knob shape to copy, including its "workbench family only, artifacts
  stay authored" discipline.
- `src/theme/themeTokens.ts` -> `themeColorTokens`, where the pole concession lands. `workbenchBlack` #262626 measures
  L=0.269 and `workbenchWhite` #d8d8d8 measures L=0.882, so **the workbench already lives at very nearly the tinted
  rails** and edit mode can carry full chroma today at zero contrast cost.
- `src/domain/exposure.ts` -> `isFaceBuried`, `getBuriedCubeIds`; `src/domain/neighbors.ts` -> `createOccupancyIndex`,
  `getCubeNeighborSlots`. Enclosure Chroma's input, already computed per frame: `src/scene/cubeInstances.ts:138` reads
  `context.buriedFaces`. Burial *depth* is not computed and is the one genuinely new domain quantity on this page.
- `src/scene/cubeInstances.ts` -> `CubeFaceInstance.matrix` (world position in elements 12/13/14),
  `CubeEdgeInstance.axis`. Every geometry key except burial depth is already on the instance.
- `src/domain/cubeEdgeState.ts` -> `cubePartColors`, `cubeEdgeStateOwner.color`. Colour identity is an index into a
  3-value union, encoded positionally: the extension point if colour becomes authored, and a version bump and reset.
- **none found**: a scene-level procedural colour module. `rg -i "gradient|ramp|hue|chroma|palette"` across `src/` hits
  only `colorSpace.ts`, `scenePolarity.ts` and unrelated CSS. New code; `colorSpace.ts` is its natural home.

# What I Would NOT Build And Why

- **Any per-face lightness ramp, including a subtler one.** The objection is structural, not a matter of degree.
  `cubeFaceLightnessDeltaById` on main should be revisited here, not left as a rejected mechanism nothing replaced.
- **Free per-face RGB picking.** Destroys the two-tone reading, invalidates the positional colour encoding, turns every
  composition into an authoring chore. The exception still matters: see Q1.
- **Time-varying colour on the CPU path.** Colour writes today are sparse and patch-driven (`patchInstancedPartMesh`
  writes only dirty slots); a per-frame colour function rewrites every instance every frame plus a full buffer upload.
  The "time" half is a shader-side job or a regression. **Measure before adopting.**
- **Chroma on faces and edges simultaneously in v1.** Two surfaces changing at once makes the live judgment impossible
  to attribute. One surface at a time.

# Open Questions For The Owner

1. **Does the swatch survive at all?** "Colour is a function of coord and time" is right for the field and I endorse it.
   But no procedural system can say "this one cube is red", and every editor eventually needs that exception. Proposal:
   the function owns the field, a rare per-cube override owns the exception. Or hold the line?
2. **Is the pole concession acceptable?** Colour requires 0.115 -> 0.22 and 1.0 -> 0.93, dropping absolute contrast
   20.4:1 -> 14.3:1 for tinted cubes only. If pure #050505/#ffffff is inviolable then Axis Ink and Field Tint are the
   whole menu and faces stay neutral. This gates everything else here.
3. **Range or form?** Axis Wash answers "more than black and white cubes". Enclosure Chroma answers "a cube should read
   as a solid". They compose, but the first live test should isolate one.
4. **Workbench first?** Its tokens already sit at L=0.269/0.882, near the rails, so colour could ship to edit mode at
   full strength while artifacts stay pure, matching the `edgeLightnessDelta` split. Lower risk, but then the owner sees
   colour in a surface the audience never does.
5. **Does the editor UI take the rails too?** Panels and chrome on the same two-rail system would make the interface
   look like the thing it edits. Out of scope here, worth a decision.

## Consensus Round

**A = concession.** Pure #050505/#ffffff stay inviolable *as roles*; the concession is paid only by a new
opt-in role. My first draft conflated "tint a black cube" with "author a coloured cube", which ux-designer
gets right: an accent is its own role at its own pinned L, so no existing part is ever transformed. Note the
harder fact underneath this fork: **the poles are already violated on main**. `cubeFaceLightnessDeltaById`
is read unconditionally at `instancedPartMeshCore.ts:407`, while the edge delta comes from
`context.edgeLightnessDelta` (workbench-only). Faces are therefore shifted in artifact and thumbnail paths
too, so exports do not show authored black and white today. "Inviolable" is a position the codebase does
not currently hold, and restoring it is F.

**B = faces.** Changed from my report. Two arguments beat mine. ux-designer's identity argument is correct
and I was measuring the wrong risk: I called edges-first "safest" on code blast radius, when the thing the
owner rejected #160 over was identity, not code. Worse, my own scheme fails on its own terms:
`defaultCubeEdgeThickness` is 0.014 of a unit cube, so Axis Ink paints hue onto hairlines and delivers
almost no perceptible colour. Colour needs area. Faces are the area.

**C = enum.** The wire decides this. Face colour encodes as `cubePartColors.indexOf` in
`compactPose.ts:encodeCell`, `PartColorTween` carries labels not hex, `ScenePartColors` is keyed
black|white, and three validators delegate to `isCubePartColor`. Freeform breaks all four, and
frontend-engineer's own report concedes it needs "a new compact value shape or a pose palette table" at
line 71 while recommending sRGB literals at line 79. Enum also buys coherence for free: role scarcity is
what keeps a thousand cubes from becoming confetti.

**D = authorship.** Changed from my report. Authorship owns which parts carry a role; a function may
modulate only what the role resolves to. Axis Wash survives intact as accent-hue-drift-along-X, losing its
primacy rather than its mechanism. I had the split backwards (function owns the field, swatch is the
exception); ux-designer has it the right way round.

**E. Ranking by product value:** Accent Role > Enclosure Chroma > Axis Wash (as role modulation) > Field
Tint > Facet Hue > Axis Ink. Facet Hue drops because it is the rejected mechanism's descendant and answers
a question the owner did not ask (form legibility, not range). Axis Ink drops for the coverage reason above.

**First slice: Accent Role.** A cube the owner chose is now coloured, and one hue scrub restyles every one
of them at once.

**F. Ride-along: scope the face lightness delta to the workbench family, the rule the edge delta already
follows.** One rule for two deltas instead of two rules, roughly three lines at the `resolveInstanceColor`
call site plus config. This is a precondition, not a nicety: authored colour that does not survive export is
not authored colour. I partially reject the scout's "defer until the form-vs-colour decision" — this round
is that decision, and all four reports agree lightness must not carry form, so the deferral condition is
discharged. It is also not a revert: #160's look stays where the owner sees it, on the workbench.
Bundle if cheap: derive `partColorOptions` from `cubePartColors` (~10 lines), since adding a role otherwise
requires a hand-sync that has no compiler guard. **Defer:** unifying face colour onto the
`cubeEdgeStateOwner` field-owner pattern (touches encode, morph, and render-impact together, rewrite-shaped)
and the `themeTokens.ts` / `tokens.css` hex duplication (orthogonal to authoring, needs a generator call).

**Changed:** B and D, both against my own schemes.

**Still rejected:** ux-designer's claim that a coord function "erases authorial intent exactly as
orientation-driven lightness did". I accept the conclusion and reject the equivalence. #160 failed by
*ambiguity*: an overloaded channel produced mid-greys that could not be read back to an authored value. A
coord function fails by *loss of control*, which is a different defect with a different fix. The distinction
is load-bearing, because the equivalence would condemn Enclosure Chroma by association, and Enclosure Chroma
is the one scheme that recovers the #162 signal without touching L or authorship. Kill coord-as-primary on
its own merits, not by inheriting #160's verdict.
