# Face mark: the domain

Scout report, domain angle. Worktree `.claude/worktrees/mark`, branch
`feat/face-mark`, base `main` at `a708397`. Read only, nothing in the repo was
written.

## Verdicts

| Question | Verdict |
| --- | --- |
| Whose state is a mark | The Library, inside the document, referenced from `CubeFaceState` |
| The index property | Only apparently preserved. Two of its three senses survive; the one that made it safe does not |
| Second aggregate | No, conditional on three tests that must be written down now |
| Two role slots | Coherent, provided `CubeFaceState.color` is never renamed |
| Domain name | `Stencil` for the asset, `figure` for the face field. Not figure/ground as a pair |

The design carries content inside the existing atom and does not fork the
domain. It does something else that is worth naming plainly: it adds four
fields to the one part type in cubicell that has no field table owner, and in
doing so it hand writes six things the edge owner already generates.

## The structural finding that comes before the five questions

Edges and faces are not symmetric today, and the asymmetry is invisible until
something tries to extend a face.

`cubeEdgeStateOwner` (`src/domain/cubeEdgeState.ts:205`) is a field table.
Each field declares `decode`, `defaultValue`, `encode`, `inherit`, `isEncoded`,
`isValue`, `morphChannel` and `renderAttribute`, and the owner generates
`areEqual`, `distance`, `matches`, `encode`, `decode`, `inherit`,
`interpolateMorph`, `getMorphChanges` and `changedRenderAttributes` from it.
Adding a field to an edge is one table entry.

`CubeFaceState` (`src/domain/cube.ts:36`) is a plain type with three fields and
no owner. Everything the edge owner generates is hand written for faces, in
six separate places:

| Concern | Edges | Faces |
| --- | --- | --- |
| Equality | `cubeEdgeStateOwner.areEqual` | `areFaceStatesEqual` (`selectionAspects.ts:217`) |
| Selection distance | `cubeEdgeStateOwner.distance` | `faceStateDistance` (`selectionAspects.ts:98`), opacity only |
| Tolerance matching | `cubeEdgeStateOwner.matches` | inline field list (`selectionAspects.ts:131-137`) |
| Wire encode | `cubeEdgeStateOwner.encode` | positional tuple (`compactPose.ts:107-119`) |
| Wire decode and guard | `cubeEdgeStateOwner.decode` | `isCompactFace` (`compactPose.ts:184`) |
| Default comparison | `areEqual` against default | `sameFace` (`compactPose.ts:215`) |

Two consequences for this feature specifically.

**A forgotten site is a silent bug, not a type error.** The tolerance branch at
`selectionAspects.ts:133-137` spells its fields out by hand:
`candidate.color === reference.color && candidate.visible === reference.visible`
plus an opacity distance. Add a stencil to `CubeFaceState` and forget this
line, and two faces carrying different stencils compare as equal under any
tolerance query. Nothing fails. The selection language quietly starts lying.

**`createCubeEdgeStateOwner` is already generic.** Read its signature at
`cubeEdgeState.ts:58`: `<const Fields extends Record<string, AnyCubeEdgeStateField>>`.
Nothing inside it is edge specific. It is named for its first caller. A
`cubeFaceStateOwner` built from the same factory is a table of four entries and
the deletion of six hand written functions.

The honest sequencing is therefore: bring faces under the owner first, then add
the stencil as a table entry. Adding four hand written fields to a hand written
type, and only later noticing the duplication, is how this file grows a seventh
hand written site.

One thing the factory cannot do today, named up front. `areEqual` compares with
`===` per key (`cubeEdgeState.ts:110-112`). Every current field is a primitive.
A stencil reference as a string id works. An object valued field does not, and
question 3 argues the stencil should be exactly that. The field descriptor
needs an optional `equals`, which is a small addition to
`CubeEdgeStateField` (`cubeEdgeState.ts:19`) and is required rather than
optional if the value object shape is adopted.

## 1. Whose state is a stencil

**The bytes belong to the Library. The reference belongs to the face. Neither
belongs to the cube.**

The per face state owner is `CubeFaceState` at `src/domain/cube.ts:36`, held as
`CubeFaces = Record<CubeFaceId, CubeFaceState>` (`:43`) on `CubeCell` (`:52`).

The reference sits on the face because that is where the invariant lives. Two
faces of one cube can carry different stencils, so the cube cannot own it
without inventing a per face map that duplicates `CubeFaces`. The scene cannot
own it for the same reason one level up. Ownership follows the smallest thing
that can vary independently, and that is the face.

The bytes cannot sit on the face, for a reason the codebase already
demonstrates. `applyCubeOperation` (`src/domain/cubeOperations.ts:352`) fans a
`set-face-state` patch across a selection set, and `inheritCubeStyle`
(`cube.ts:116`) copies face colour into every newly grown cube. Both copy face
state by value. Inline stencil bytes would be duplicated per face per cube per
captured State, and `PoseRevision` is immutable content, so every capture
freezes another copy.

**Do not invent a registry. Three of them already exist in some form.**

- `Library` (`src/domain/workbench.ts:57`) already holds `animations`, `states`
  and `structures`, inside `Workbench` (`:63`), which the vocabulary at
  `MODEL.v2.md:426` names as the authoring aggregate. A fourth roster belongs
  here.
- `ProjectAssetKind` (`src/domain/project.ts:4`) is `"animation" | "structure"`,
  and `ProjectAssetReference` (`:6`) is already the id, kind and revision triple
  that a manifest entry takes.
- `STORAGE.md:463` already routes "imported fonts, textures, and reference
  media" to object storage, and `:114` classes them as binary output. `:469`
  already specifies that "Postgres metadata records Project ownership, media
  type, byte length, content hash, and lifecycle".

`TYPOGRAPHY.md` also already anticipates a "font asset" feeding shaped glyph
runs. A stencil is a font asset with one glyph. The precedent to reuse is the
font, not a new mechanism.

So the layering the repo already implies: **the Library entry is the aggregate
local anchor and the bytes are a content addressed cache.** The document owns
identity, name and lifecycle. Object storage owns bytes keyed by hash. Absence
of bytes is then a loading state rather than a domain inconsistency, which is
the distinction that makes question 2 answerable.

## 2. The index property

This is the question the design gets wrong, and it gets it wrong in an
interesting way.

Face colour persists as `cubePartColors.indexOf(face.color)`
(`compactPose.ts:114`) into a vocabulary declared append only:
"Appended, never reordered: the compact pose codec stores a part's color as its
index here" (`cubeEdgeState.ts:5`). That gives three distinct properties, which
are usually discussed as one.

1. **Re themeable.** The document records intent, and
   `resolveCubePartColor` (`src/theme/scenePolarity.ts:38`) decides appearance
   at render time from `ScenePolarityConfig`. Appearance is never persisted.
2. **Forward compatible.** Appending `accent` at index 3 invalidated no
   document, because older documents only reference 0 through 2.
3. **Total.** Every index in a closed vocabulary resolves. There is no absent
   member. Commit `a708397` made this exhaustive on purpose.

Against a registry reference:

**Property 1 survives, and survives more strongly than it looks.** A stencil
carries coverage and contributes no colour at all. Both regions resolve through
`CubePartColor` roles and the polarity rails. The rule "import form only, never
appearance" is exactly this property, restated.

**Property 2 survives, by a different mechanism.** The enum is forward
compatible because it is closed and append only. A registry is forward
compatible because it is open and entries are independent. Same outcome, and
worth noting that the mechanisms are not interchangeable.

**Property 3 does not survive, and property 3 is the one that made the other
two safe.** `cubePartColors[2]` always resolves. `library.stencils["abc"]` may
not. A closed vocabulary has no absent members by construction. An open
registry has absence as a permanent possibility.

So the answer to the question as posed: **only apparently preserved.** The
reference has the same syntax as the index, an opaque token resolved at render
time, with none of the guarantee. The enum's real property was never
index-ness. Index-ness is the implementation. The property was totality over a
closed vocabulary, and an unbounded registry cannot have it.

### What happens when the entry is gone

The repo rule is real and I confirmed it: `LESSONS.md:121` says
"When a persisted shape changes, the Reset button is the migration path", and
`STORAGE.md:154` scopes that to pre release, with "Durable migrations become
mandatory once external Project data exists".

**That rule does not cover this risk.** It governs schema change. A dangling
stencil reference is a content absence under an unchanged schema, so no version
bump is triggered and no reset occurs. Invoking the no migrations rule here
answers a question that was not asked.

What the codebase does with references that can vanish today:

- `repairEditorSessionReferences` (`src/state/sessionReferences.ts:18`) repairs
  session references to a valid fallback after every mutation, history move and
  rehydrate. That is view state, where falling back to null or to the poster
  State is harmless.
- For document content, `tests/assetStateInvariants.test.ts:295` fixes the
  posture as "one authoritative Score spans sibling poses and tolerates absent
  ids". Tolerance is correct for a score that indexes cubes which may be gone.

Applied to a stencil, tolerate means the face silently drops to a plain
coloured face. That is silent loss of authored artwork, and it is the one
outcome that must not be chosen by default.

### Recommendation

Three changes make the reference as safe as the enum, without pretending it is
one.

1. **Content address the id.** `STORAGE.md:469` already specifies a content
   hash for binary objects. If the reference is the hash rather than a mint time
   UUID, a lost entry re binds automatically when the user re imports the same
   file, because the identity is derived from the bytes. A UUID reference can
   never re bind. This does not prevent absence and it converts absence from
   permanent to recoverable.
2. **Keep the roster inside the document.** A `stencils` roster on `Library`
   makes the reference intra aggregate, so `Workbench` as aggregate root can
   enforce that no face references an id the Library lacks. A reference into a
   side store is cross aggregate and only ever repairable after the fact.
3. **Make absence explicit.** An unresolved stencil must render as a declared
   unresolved state and must be visible in the panel, never as a silent fall
   back to a plain face. The face keeps its ground colour either way, so the
   difference is entirely in whether the user is told.

## 3. Aggregate boundary

`Workbench` is the aggregate root (`MODEL.v2.md:426`, `workbench.ts:63`). With
the roster inside `Library`, the stencil reference is intra aggregate and the
boundary holds.

### Invariants that must hold

1. Every `CubeFaceState` stencil reference resolves to a Library entry in the
   same document. Expressible once the roster is in `Library`. Not expressible
   today.
2. A stencil entry is immutable once referenced by any captured State, because
   `PoseRevision` is immutable content (`src/domain/project.ts:21`). Content
   addressing gives this for free, since editing the bytes mints a new id.
3. A face carries a figure role if and only if it carries a stencil.
4. Deleting a Library stencil either cascades to every referencing face or
   refuses. Today nothing can express either.

### The one the current model cannot express

Invariant 3 is the real gap, and it is a shape problem rather than a missing
check. The proposal adds four independent fields to `CubeFaceState`. Three of
them are meaningless when the fourth is absent. `CubeFaceState` has no way to
say "these fields are only meaningful together", and every generated behaviour
would treat them as independent: `inherit` per field, `interpolateMorph` per
field, tolerance matching per field.

The fix is to carry them as one optional value object rather than four fields:

```
mark?: { stencilId; figure; polarity? }
```

Presence is then one decision, invariant 3 becomes structural, and the four
way inconsistent state is unrepresentable. The cost is the `equals` addition to
the field descriptor noted above, because the owner compares with `===`.

### Is there a second aggregate

**No, on three conditions.** A stencil is an entity in the Library and a value
everywhere it is used, which is exactly how `TYPOGRAPHY.md` already treats a
font. It has no placement, no geometry of its own, no score and no presence in
the scene. The owner's objection to text as a peer primitive does not apply.

The three conditions are the test, and they should be written down now because
each will come under pressure:

1. `selectionSubjects` stays `["cube", "face", "edge"]`
   (`src/domain/selectionAspects.ts:24`). The moment a figure region is
   independently selectable, a face is a container of parts.
2. No command targets a region. `set-face-state` with
   `patch: Partial<CubeFaceState>` (`cubeOperations.ts:136-140`) stays the only
   route, and it already carries a new field with no new command kind. This is
   the strongest existing evidence that the design fits inside the atom.
3. A stencil never acquires its own score, transition or placement. The moment
   a figure animates independently of its face, cubicell has two atoms and
   every capability gets built twice.

### One boundary the proposal crosses without saying so

The polarity pin is a second polarity authority. Polarity is scene level today:
`Pose.polarity`, encoded as a single `p: 0 | 1` for the whole pose
(`compactPose.ts:43,54`), and the render path resolves one `ScenePolarityConfig`
per mesh in `createColorWriteContext`
(`src/scene/instancedPartMeshCore.ts:365`). A per face pin means one cube can
contain two polarities and the workbench and artifact configs no longer differ
by a single scene level switch. It is the weakest of the four proposed fields
and it is separable from the rest. Recommend deferring it until a real mark
demonstrably needs it.

## 4. Two role slots

**Coherent, and it is honest reuse rather than overload, with one naming
condition.**

`CubePartColor` (`cubeEdgeState.ts:6`) is a role vocabulary of four members, and
`resolveCubePartColor` (`scenePolarity.ts:38`) is total over it and indifferent
to which part asks. Using it twice on one part is the vocabulary working as
designed. Nothing about it assumes one use per part.

The framing matters more than the mechanism. "A face has two colours" is
incoherent, and the incoherence shows up immediately in the existing code:
`inheritCubeStyle` (`cube.ts:116`) copies `face.color` into a newly grown cube,
and the tolerance matcher (`selectionAspects.ts:135`) compares
`candidate.color === reference.color`. Both need to know which of the two is
*the* face colour.

"A face has a colour, and optionally a stencil that partitions it, and the
covered region takes a second role" is coherent, and it keeps every existing
behaviour correct without touching it. `color` remains the field it is today
and is the uncovered region. The new field names only the covered region.

**The condition: do not rename `color` to `ground`.** A rename converts a
compatible extension into a breaking change across
`inheritCubeStyle`, `areFaceStatesEqual`, `faceStateDistance`, the tolerance
branch, `CompactFace`, `sameFace`, `faceColorBinding`
(`src/editor/controlBindings.ts:364`) and `partColorOptions`, and it buys
symmetry in a document rather than correctness in the model.

## 5. Ubiquitous language

"Mark" is brand vocabulary. Cubicell's own register is fabrication: workbench,
lattice, cell, part, face, edge, cut, capture. Library assets are shape words:
`StructureAsset`, `AnimationAsset`.

Two collisions I checked rather than assumed:

- **"ground" is already taken, and taken by the most confusable thing
  possible.** `FloorGridChrome.tsx:17` calls the floor "the ground grid" and
  `WorldAxesChrome.tsx:17` calls its plane "the ground plane". In a 3D editor,
  a face property named `ground` and a floor named the ground is a genuine
  ambiguity. **Do not adopt figure and ground as a pair.**
- **"form" is mildly taken.** `MorphInspector.tsx:141` labels a control
  "Morph form". A UI carrying both a morph form and a face form is confusing,
  and `useSnapSize.ts:25` uses `form` for panel form factor.

Recommendation, with the reasoning so it can be overruled cheaply:

- **The asset is a `Stencil`.** A stencil is definitionally form without
  appearance: cut once, painted any colour. The name carries the rule that the
  brief states in prose, so a future contributor cannot import appearance
  without contradicting the noun. `StencilAsset` sits beside `StructureAsset`
  and `AnimationAsset`, `ProjectAssetKind` gains `"stencil"`, and the command is
  `set-face-state` with a stencil in the patch. The one caveat: "stencil" is
  also a WebGL buffer, though the domain layer never touches it and there is
  currently no stencil buffer use anywhere in `src`.
- **The face field is `figure`.** No collision, and it names only the covered
  region, which is exactly the scope of the new field. `color` keeps its name
  and its meaning.

Runner up if `Stencil` is rejected: `Form`, accepting the "Morph form"
collision. I would not recommend `Mark`, because it reads as brand asset
management rather than as a cubicell primitive, and it invites the appearance
import the rule forbids.

## The four proposals, assessed

| Proposal | Assessment |
| --- | --- |
| Reference on `CubeFaceState`, not inline bytes | Correct, and required. Value copying at `cubeOperations.ts:352` and `cube.ts:116` makes inline bytes untenable |
| Registry the face references | Correct in shape. Put it in `Library`, not a side store, and content address the id |
| Two role slots on the existing `CubePartColor` | Correct, provided `color` is not renamed and the fields become one optional value object |
| Polarity pin | Weakest. Creates a second polarity authority against a scene level `Pose.polarity`. Separable, and should be deferred |
| Render packs the resolved colour into an instance attribute | Consistent with the render path. CPU side resolution through `ScenePolarityConfig` is what preserves the re themeable property |
| Authoring as four enum rows on `set-face-state` | **Partly wrong.** See below |

The authoring claim does not survive contact with the binding vocabulary.
`ControlValueSchema` (`src/editor/controlBindings.ts:31`) has exactly three
kinds, and `enum` carries a **static** `options` array fixed on the binding
object. `ControlBindingContext` (`:36`) carries scene, selection, selection set,
edit target, resize anchor and visibility analysis, and **no library**. So:

- The figure role fits, as a static enum over `partColorOptions`, exactly like
  `faceColorBinding` (`:364`).
- A polarity pin would fit, if adopted.
- **The stencil reference does not fit.** Its options come from the document's
  Library, which a binding cannot see and cannot express. It needs either a new
  dynamic options schema kind or an authoring path outside the binding
  vocabulary, and adding the library to `ControlBindingContext` widens a context
  every binding shares.

Three rows, not four, and the fourth is the one the feature is actually about.

## What I did not establish

- Whether the owner wants a stencil to be shareable across Projects. It changes
  whether the Library roster or the object store is the primary home, and
  question 2's recommendation assumes document local.
- Whether a stencil should be morphable stencil to stencil. `CubeEdgeStateMorphChannel`
  (`cubeEdgeState.ts:17`) offers `color-tween`, `discrete-cut` and
  `numeric-lerp`, and there is no coverage crossfade channel. `discrete-cut`
  costs nothing and should be the stated default rather than an omission
  discovered later.
- Whether `assets/marks/*.svg` staying untracked (`git status` shows `?? assets/`)
  is deliberate staging or an oversight. It affects nothing in this analysis.
