# Cubicell selection query language, proposal v0.3

Warroom `select-lang`, 2026-07-10. Lead author: Fable (8:4.1). v0.2
(unanimously signed off) integrated two full review rounds: the Opus
pre-brief and delta round, Grok's deltas, and fifteen-plus Codex
deltas. **v0.3 is a reopen**: Stuart's live test case, "select all
outer top edges on a 2x2x2", exposed a category the attribute-only
model missed, relational and topological selection. The relational
section below reshapes the model; the v0.2 attribute surface is
unchanged and its sign-offs stand for that surface. Spec only; no
code this round.

Convergence notes: Opus H1 and Codex blocker #1 flagged the same
multi-exemplar correlation defect independently; the expression batch
below is the agreed fix. Opus conceded flat-AND, phase 1 tolerance,
and `subject` naming with guards that are folded here. The reopen's
relation family and driving-case algorithm arrived via Grok's
feasibility delta and are folded pending Opus and Codex review.

Ground truth: `src/domain/selectionQuery.ts` (the 7-kind union),
`src/domain/selection.ts` (CubeSelectionSet), `src/domain/cubeOperations.ts`
(CubeScope), `src/app/useSceneOperations.ts` (the selectSimilar trigger),
MODEL.v2.md and ARCHITECTURE.md.

## Why today is immature

`CubeSelectionQuery` is seven hardcoded kinds, each one fixed equality
predicate against one source cube. No composition, no negation, no
tolerance, one exemplar only, always replaces the selection. `same-axis`
is a spatial scope wearing a query costume: it duplicates
`CubeScope.axis` inside the attribute union. And every kind hardcodes
the cube/face/edge triad, so the future ShapeUtil part-type seam has no
place to plug in.

The half-good news: the split we need already half-exists. Queries take
an optional `scope?: CubeScope`, and `CubeScope` (single, selected,
selection-set, all, axis, plane, pattern) is already the spatial
vocabulary. The language below finishes that split instead of inventing
a second one.

Opus's decomposition frames the design: the 7 kinds are secretly
orthogonal concepts. **Scope** picks candidates (`same-axis` is
only this). **Projection** states which part to emit (`same-edge` and
`same-face` filter nothing; they restate a part id across scope).
**Predicate** filters candidates. The reopen split predicates into two
families: **attribute** predicates test what a candidate is (authored
state equality), and **relation** predicates test how a candidate
relates (occupancy and adjacency derived from the scene). The language
is the product of scope, projection, and both predicate families; the
original brief's framing bias hid the relation family entirely, and
"select all outer top edges" is unexpressible without it.

## Ubiquitous language

| Term | Meaning | Exists today as |
| --- | --- | --- |
| **Subject** | The kind of thing a query yields: `cube`, `face`, or `edge`. One query yields exactly one subject kind. | `CubeSelectionKind` |
| **Scope** | The candidate pool, spatial and structural. Narrows *which cells are considered*. | `CubeScope` (reused; see purity note) |
| **Projection** | Which part(s) a face or edge query emits per matching cube: literal ids, `all`, or a semantic derivation such as `face-perimeter` (a face's four bounding edges). | the `edgeId`/`faceId` fields |
| **Aspect** | A comparable property of a subject, defined by an aspect descriptor (read + match). The unit the ShapeUtil seam will register. | implicit in the 7 kinds |
| **Predicate** | One testable condition on a candidate. Two families: attribute and relation. | implicit, one per kind |
| **Attribute predicate** | Tests authored state equality against typed reference values, with optional negation and tolerance. | the `same-*` kinds |
| **Relation predicate** | Tests topological adjacency and occupancy derived from the scene: exposure, enclosure, laterality. No exemplar values. | missing (the reopen gap) |
| **Exemplar** | A selection the *compile step* reads reference values from. Plural. The resolver never sees one. | the single `cubeId` field |
| **Query** | Subject + scope + projection + predicates. Pure, serializable data. | `CubeSelectionQuery` |
| **Selection expression** | An ordered list of queries, resolved and unioned. The serializable OR. | missing |
| **CombineMode** | How the resolved set meets the current selection: `replace`, `add`, `subtract`, `intersect`. Lives on the *command*, never inside the query. | missing (always replace) |

"Similar" stays the user-facing verb for exemplar-fed queries. "Select
similar" compiles a selection expression; it stops being a special
mechanism.

Two invariant-level separations:

1. **Scope vs predicate.** Scope answers "which cells compete";
   predicates answer "which candidates win". `same-axis` migrates out
   of the query union into scope. Scope never tests aspects. Attribute
   predicates never test coordinates or occupancy. Relation predicates
   may test topological adjacency and occupancy derived from the scene
   graph and the topology tables; they never test raw world-space
   coordinates or camera rays (rewritten in the reopen; the old ban
   "predicates never test coordinates" was aimed at raw-coordinate
   testing, which remains scope's job, and accidentally outlawed the
   relation family).
2. **Resolve vs combine.** Resolution is a pure scene-to-set function.
   Combining with the current selection is a selection-context concern
   and belongs to the dispatching command.

## The model (phase 1 types)

Discriminated by subject so projection is required exactly where it is
meaningful, and by aspect so values are typed (Grok T1/T2; Codex typed
operands). No `unknown[]`, no phantom `CubePartId`.

```ts
type AttributePredicate =
  | { kind: 'attribute'; aspect: 'size'; values: CubeSize[]; negate?: boolean; tolerance?: number }
  | { kind: 'attribute'; aspect: 'face-state'; values: CubeFaceState[]; negate?: boolean; tolerance?: number }
  | { kind: 'attribute'; aspect: 'edge-state'; values: CubeEdgeState[]; negate?: boolean; tolerance?: number }
  | { kind: 'attribute'; aspect: 'cube-state'; values: CubeStateSnapshot[]; negate?: boolean; tolerance?: number }

// CubeStateSnapshot picks exactly the fields areCubeStatesEqual already
// compares: visible, size, all edge states, all face states. Authored
// visible state only; placement and evaluated score are excluded.

// Relation predicates carry no exemplar values; they evaluate against
// structural occupancy at resolve time (the reopen family).
type EdgeJunction =
  | 'convex'       // only the owner quadrant occupied: an outer crease
  | 'flat-seam'    // two adjacent quadrants: a seam in a flat surface
  | 'non-manifold' // two diagonal quadrants: corner-touching cells
  | 'concave'      // three quadrants: an inside corner
  | 'interior'     // all four: fully enclosed

// Occupancy is structural in phase 1: hidden spacer cells count as
// occupied (the neighbors.ts ghost contract). See the occupancy
// ruling in the relational section.
type RelationPredicate =
  | { kind: 'relation'; relation: 'face-exposed'; negate?: boolean }
  | { kind: 'relation'; relation: 'cube-exposed'; negate?: boolean }
  | { kind: 'relation'; relation: 'edge-junction'; junctions: EdgeJunction[]; negate?: boolean }

type Predicate = AttributePredicate | RelationPredicate

// Projection: literal ids, everything, or a semantic derivation that
// expands from the topology tables.
type FaceProjection =
  | { kind: 'ids'; ids: CubeFaceId[] }
  | { kind: 'all' }
type EdgeProjection =
  | { kind: 'ids'; ids: CubeEdgeId[] }
  | { kind: 'all' }
  | { kind: 'face-perimeter'; faceId: CubeFaceId } // getCubeFaceEdgeIds, exists today
  | { kind: 'axis-parallel'; axis: AxisIndex }     // cubeEdgeTopology.axis filter

type SelectionQuery =
  | { subject: 'cube'; scope?: CubeScope; predicates: Predicate[] }
  | { subject: 'face'; scope?: CubeScope; part: FaceProjection; predicates: Predicate[] }
  | { subject: 'edge'; scope?: CubeScope; part: EdgeProjection; predicates: Predicate[] }

// The serializable OR: queries resolve independently and union.
type SelectionExpression = SelectionQuery[]

type SelectByQueryCommand = {
  kind: 'select-query'
  expression: SelectionExpression
  combine: 'replace' | 'add' | 'subtract' | 'intersect'
}
```

`axis-parallel` is phase 1 by orchestrator ruling: scene-free,
near-zero cost over the existing `cubeEdgeTopology.axis`, and it
traces to a real directional-selection op ("all vertical edges"). All
semantic projections are **local-topology descriptors** (Codex):
`face-perimeter('top')` means the cube's own top in its local frame;
`CubePlacement.rotation` can diverge local from world-up, and
world-facing or camera-facing projections are future view relations,
out of this model.

Rules the types cannot carry:

- An **attribute** predicate carries at least one value; compile
  rejects empty. This closes the negate-after-empty hazard (an empty
  any-of matches nothing, so its negation would select the universe).
  Codex blocker, folded.
- An `edge-junction` predicate carries at least one junction class;
  `canRun` rejects empty (same hazard, relation form).
- Relation predicates are subject-checked: `face-exposed` evaluates
  face candidates only, `cube-exposed` cubes only, `edge-junction`
  edges only. The relation descriptor declares its subject exactly as
  aspect descriptors declare `supportedSubjects`.
- A `{ kind: 'ids' }` projection with an empty list is invalid.
  `{ kind: 'all' }` and the semantic forms stay in the carrier (a
  saved expression and a refinement chip keep the intent "top
  perimeter", never a bare id list) and expand deterministically at
  resolve through the pure topology tables, in declaration order (the
  deterministic enumeration Codex asked for). Opus's alternative,
  compile-time expansion to literal ids, was overruled for provenance;
  the expansion is scene-free either way so nothing else changes.
- Face and edge attribute predicates read the candidate's value **at
  the candidate's own part**, so part and state stay correlated within
  one query (Codex correlation requirement; see composition).

**Composition: the expression is disjunctive normal form.** Within a
query, predicates AND and each may negate. Across queries in an
expression, results union (OR). This carrier is fully expressive for
propositional composition over predicates: De Morgan lowers any NOT of a
conjunction or disjunction into per-predicate negations and additional
queries. Codex's blocker demanded AND/OR/NOT with serialization,
saving, and provenance; the expression form delivers all three with a
flat carrier and no tree walker, and Codex's constructive
`any([all([...]), all([...])])` shape is isomorphic to it (an any of
alls is exactly this DNF). Opus conceded the tree (C1) with the
reframe that each query is one DNF product term, plus one honest phase
consequence, folded: an OR-composed selection is only serializable as
an expression, so phase 2 saved definitions persist expressions, never
single queries. A nested authoring tree, if a real need appears,
becomes phase 2 sugar that compiles down to this same normal form.

**Exemplar quantifier (Codex round 3 blocker, folded).** "Similar to
ALL of these" is an explicit mission gap and any-of alone cannot
express it. `compileSimilarExpression` takes a quantifier, `any`
(smart default) or `all`, and the carrier stays unchanged: `any`
compiles to the DNF union above; `all` compiles to one query whose
predicate list holds one single-value predicate per materialized
exemplar value (AND). Under exact matching, conflicting equality
references make `all` provably empty, which is the defined and correct
result; `all` becomes discriminating precisely when tolerance is in
play (within epsilon of every exemplar). The quantifier is compile
vocabulary, so LLM actors reach both today; a key or chip surface for
`all` waits for the authoring round.

**Correlation under multi-exemplar (the Codex unsoundness, fixed).**
Exemplars (top face, opacity 0.5) and (left face, opacity 1) must not
match a cube whose top face has opacity 1. One flat query with any-of
parts and any-of values would. The compile therefore emits **one query
per distinct exemplar part**, each carrying only that part's state
values, and the expression unions them. Correlation is preserved per
query; the union expresses "like either".

**Materialized values (Opus, confirmed by Grok).** The compile step
reads reference values out of the exemplars into typed predicate
values. This requires the scene, so the signature is
`compileSimilarExpression(scene, selection, selectionSet?, quantifier?)`
(Codex contract delta). The references are typed snapshots of aspect
values, never live scene pointers and never opaque blobs (Grok). A
stored expression survives exemplar deletion; the resolver never
dereferences an exemplar.

**The aspect table is the compile target (Grok T3).**

```ts
type AspectDef<V> = {
  id: AspectId
  read: (cell: CubeCell, partId?: CubeFaceId | CubeEdgeId) => V
  match: (candidate: V, reference: V, tolerance?: number) => boolean
}
```

Phase 1 hardcodes the four aspects in a domain table. Tolerance is a
declared capability of the descriptor (Opus C2 guards, folded): a
scalar-capable aspect carries a distance function, and a `tolerance`
on a non-scalar aspect is a compile error, never a silent no-op. The
`match` function owns the semantics: `size` compares componentwise
with max-abs distance; opacity and thickness fields compare within the
given epsilon; colors and booleans compare exactly. The predicate only
carries the optional number.

**Absent tolerance means exact match.** The existing `are*Equal`
helpers are exact, so legacy compiles emit no tolerance and the
zero-behavior-change claim survives (Codex equivalence delta). The
re-pointed select-similar trigger also starts exact; opting the
similar compiler into the domain epsilon constant (about 1e-3) is a
deliberate, separately shipped behavior change, and the threshold UI
is phase 2 (Blender ships the slider, we ship the constant first).
ShapeUtil registration is a comment seam only: registration without a
second part type is vocabulary without a customer.

## Relational selection (the reopen)

Stuart's driving test case: on a solid 2x2x2, **select all outer top
edges**. The structural top perimeter of the assembly: the eight
perimeter edge parts, excluding the internal roof seams where cells
meet ("silhouette" is reserved for the future view-dependent
relation, per Codex). Three
conditions compose it: top-facing (a semantic **projection**, the
face perimeter), outer (a **relation predicate**, the reopen's new
family), across cells in scope. v0.2 could express only the scope.

**Where exposure lives (Opus ruling, Grok and Codex concurring).**
Exposure is a per-candidate filter at part granularity, so it is a
predicate. Scope cannot carry it: scope is cube-granular and
pre-projection, and a cell can hold exposed and enclosed parts at
once. Projection cannot carry it: projection states which parts,
exposure states whether they qualify. The predicate axis splits by
what a predicate *reads*: attribute predicates read the candidate's
owned authored state (exemplar-materialized); relation predicates
read the candidate's scene neighborhood (literal-asserted, no
exemplar). Opus's crisp boundary test, folded: a condition whose
truth changes when the whole assembly translates in the lattice is a
coordinate test and belongs to scope; a translation-invariant
condition (connectivity, shape) is lawfully a relation predicate.
Exposure is translation-invariant.

**Relation semantics (precise, Codex).**

- `face-exposed`: no occupied cell across the candidate face
  (`getNeighborCoord`, one occupancy lookup).
- `cube-exposed`: at least one exposed face.
- `edge-junction`: classify the four-quadrant occupancy mask around
  the edge line. From `cubeEdgeTopology`, an edge has
  `lockedAxes: [a0, a1]` and `signs: [s0, s1]`; the four cells that
  share the physical edge line are the owner, owner+s0 on a0,
  owner+s1 on a1, and the diagonal. The mask classifies as
  **convex** (owner only: an outer crease), **flat-seam** (two
  adjacent quadrants: a seam inside a flat surface), **non-manifold**
  (two diagonal quadrants: corner-touching cells), **concave** (three:
  an inside corner), or **interior** (all four). "Outer" is
  `junctions: ['convex']`. Convex is defined by the owner-only mask
  exactly, never by face exposure: convex implies both incident faces
  are exposed, but the converse fails (a non-manifold mask, owner
  plus diagonal, also leaves both incident faces exposed). A coarse
  not-fully-enclosed test (fewer than four quadrants) fails the
  driving case because flat seams pass it; the orchestrator ruled the
  full classifier into phase 1 on exactly that ground. Grok's earlier
  `edge-lateral-exposed` is absorbed: it under-constrains at
  `scope: all` (a bottom cell's top-front edge has an exposed lateral
  face but sits mid-facade), while the mask constrains the whole
  quadrant neighborhood.

**Occupancy policy (refereed, then corrected).** Phase 1 is
**structural only**: hidden spacer cells count as occupied, matching
the `neighbors.ts` ghost contract its tests pin, so hiding a cube
does not expose its neighbors and relation truth is independent of
rendering and pointer input (Codex). The pen first ruled a
`structural | visible` knob to serve Opus's real second intent,
"select what I can see", with hidden cells as empty; Codex then
showed the knob is unsound as drafted: under a visible policy a
hidden candidate's own quadrant reads empty, and the junction
classifier has no zero-owner state. So the visible policy is phase 2
with its semantics defined up front: hidden cells' own parts are not
candidates at all (they neither render nor take pointer input), and
hidden neighbors read as empty. One enum field, same index, added
only with those rules and their fixtures.

**The worked example, compiled end to end.**

```ts
// "select all outer top edges", one query, replace combine
[{
  subject: 'edge',
  scope: { kind: 'all' },
  part: { kind: 'face-perimeter', faceId: 'top' },
  predicates: [{
    kind: 'relation',
    relation: 'edge-junction',
    junctions: ['convex'],
  }],
}]
```

Resolution on the solid 2x2x2, verified against the live
`cubeEdgeTopology` signs (Codex): the projection emits 4 top-ring
edge parts on each of the 8 cells, 32 candidates; the masks split 8
convex, 16 flat-seam, 8 interior; the query resolves exactly the 8
outer top edge parts. The flat-seam exclusion is pinned as a test.

**Part identity multiplicity (Codex).** The subject stays authored
cube-edge parts; the classifier describes one structural edge
location that several cells' parts may share. A flat seam carries two
coincident member parts, a concave junction three, a non-manifold
contact two. Results are not deduped to an assembly-edge key; an
assembly-edge subject is future vocabulary if a need lands.

**Domain home and cost.** One shared occupancy index
(`Map`/`Set` over `getGridCoordKey`) is built once per expression
resolution and shared by every relation predicate; `neighbors.ts`
refactors its private `getOccupiedCoordKeys` onto it (DRY, and
`getSceneShadowShell` reuses it). `getNeighborCubeId` is unsuitable
for exposure: it returns a would-be slot id for empty space and does
linear finds (verified; the orchestrator's brief overstated it).
Exposure and the junction classifier live in a new
`src/domain/exposure.ts` (Opus cohesion ruling: `neighbors.ts` stays
about growth and slots); semantic projection expansion lives in
`cubeTopology.ts` beside `getCubeFaceEdgeIds`. Cost: O(cells) to
index, one lookup per face test, four per edge test; the full-scene
worst case (2025 cells, 12 edges each, about 24k candidates, under
100k constant-time lookups) is trivial for one-shot resolve. Live
re-resolve at scrub rate remains the phase 2 cost story.

**Contract consequences (Opus).** Relation predicates are the
literal-value customer v0.2 reserved: asserted, never materialized
from an exemplar. Purity statements scope by family (Codex): attribute
matching is scene-independent because values are materialized;
relation matching reads the scene and is pure over it.
Self-containedness is redefined as **no selection-context
dependence**: a self-contained saved expression with a relation
predicate is durable and naturally re-derives against the current
scene, which is exactly what "outer" should mean after an extrude.
Materializing exposure into booleans at compile is the named
nightmare (Grok): a saved "outer shell" that stopped being outer.

**Authoring (my lane).** No inference from a single edge tap: every
edge borders two faces, so a tapped edge yields two candidate
perimeters and the surface must offer the choice (Codex). The clean
one-gesture path: select a face, invoke "select perimeter" or
"select outer perimeter"; the compile helper fills
`face-perimeter(faceId)` plus the convex junction predicate. Edge
taps keep today's literal same-edge compile. The palette and chip
surface for relations is the phase 1.5 authoring round; the
expression is the phase 1 deliverable.

**Acceptance matrix (Codex, pinned as fixtures).**

- 1x1x1: 6 exposed faces, 12 convex edges.
- 2x2x2 `face-perimeter('top')` at `scope: all`: 32 candidates, 8
  convex, 16 flat-seam, 8 interior.
- Handcrafted step and corner scenes: concave (three quadrants) and
  diagonal non-manifold (two diagonal quadrants) masks.
- Hidden spacer: relation truth unchanged when a cube hides
  (structural occupancy); the visible-policy variant of this fixture
  ships with the phase 2 policy.
- Negative-coordinate symmetry: every case re-asserted under a
  translated assembly (the translation-invariance law, executable).
- All cases assert authored part multiplicity, never deduped
  structural identity.

## Proof: the 7 legacy kinds compile

| Legacy kind | Compiled expression |
| --- | --- |
| `same-edge` | one query: subject `edge`, part `{ids: [edgeId]}`, predicates `[]` |
| `same-face` | one query: subject `face`, part `{ids: [faceId]}`, predicates `[]` |
| `same-edge-state` | one query: subject `edge`, part `{ids: [edgeId]}`, predicates `[edge-state]` |
| `same-face-state` | one query: subject `face`, part `{ids: [faceId]}`, predicates `[face-state]` |
| `same-size` | one query: subject `cube`, predicates `[size]` |
| `same-cube-state` | one query: subject `cube`, predicates `[cube-state]` |
| `same-axis` | one query: subject `cube`, scope `{kind:'axis'}`, predicates `[]` |

`cube-state` stays one named composite aspect in phase 1, but its
matcher is implemented as a fold over an **explicit ordered component
list** of aspect descriptors rather than a call to the hardcoded
`areCubeStatesEqual` (Opus OQ3 ruling, bounded by Codex's composite
safety delta): a blind fold over everything registered would include
the composite itself and would silently change saved-expression
semantics whenever a future ShapeUtil registers an aspect. Components
therefore participate by an opt-in flag (composites excluded), so a
new part type joins the composite deliberately, never by side effect.
Behavior-preserving today, one chip in presentation, descriptor fold
in implementation. A separate `visibility` aspect is deferred since
the composite covers legacy behavior (Grok).

## Resolution semantics

```
resolveSelectionExpression(scene, expression, context): CubeSelectionSet
```

*(Amended at slice H, 2026-07-10: resolution is expression-only. The
per-query resolver is the internal `resolveQueryItems`; a single query
is a one-element expression. The `resolveSelectionQuery` name was the
legacy shim's and is retired with the union, not resurrected.)*

The expression resolver unions and dedupes member results in domain, so
the command layer never reimplements set logic (Grok).

1. Scope resolves to candidate cells via the existing
   `resolveCubeScope`. Empty scope, empty result.
2. For a cube query the candidate is the cell; for face and edge
   queries the candidate is each `(cell, partId)` pair the projection
   emits (semantic projections expand here, through the pure topology
   tables), and predicates evaluate per pair (Codex
   candidate-semantics delta, so a multi-part query stays unambiguous
   as a direct LLM payload). An attribute predicate matches when the
   candidate's aspect value matches **any** of the predicate's values,
   per the aspect's `match`. A relation predicate matches per its
   scene-topology evaluator against one shared occupancy index, built
   once per expression resolution (Codex). Predicates AND; `negate`
   inverts one predicate after its own test.
3. Subjects emit in scene cell order, parts in declaration order.
   Results feed `createCubeSelectionSet`, which dedupes by
   `getCubeSelectionKey`.

**Purity, stated honestly and scoped by family (Grok T4, Codex, Opus
H2).** Attribute matching is scene-independent because values are
materialized; relation matching reads the scene and is pure over it.
The *scope* kinds `selected` and `selection-set` read the selection
context, exactly as `resolveCubeScope` does today, so the resolver
keeps its `context` parameter and the doc claims scene-plus-context
determinism, no more; the earlier claim of scene-only purity is
withdrawn. Opus's sharper term is adopted with the reopen's
correction: a query is **self-contained** exactly when it carries no
selection-context dependence, which means attribute values
materialized and scope not `selected` or `selection-set`. Relation
predicates never break self-containedness; they read the scene by
design and re-derive on every resolve, which is the correct meaning
of "outer" after the solid changes. Self-containedness is the
property phase 2 saved definitions require, achieved by also
materializing those two scope kinds into an id-list scope at save
time. Phase 1's transient dispatch keeps context-dependent scope,
matching today.

Invariants:

1. **Determinism.** Same scene, expression, context: same set, same
   order. Pure, total, never throws. A predicate whose values cannot be
   read (deleted exemplar at compile time) is rejected at compile;
   resolve itself has no failure mode beyond the empty set.
2. **Homogeneous subject by construction.** The discriminated query
   type makes mixed output unrepresentable; an expression's queries
   must share one subject (compile-checked), preserving the set
   invariant `toggleSelectionInSet` already enforces.
3. **Serializable data.** Expression and command are plain JSON
   (INTERACTIVE.md invariant 4). An LLM actor dispatches the identical
   payload a key press does; no DSL.
4. **Combine applies outside resolve**, in the command handler
   (Slice B: through the executor, never a direct store write).
5. **Cross-subject combine is truthfully rejected (settled).**
   `replace` may switch subjects freely; silent kind mixing stays
   unrepresentable either way. `add`, `subtract`, and `intersect`
   against a selection of a different kind return the synchronous
   lane's truthful `rejected` answer. Rationale: a degrade-to-replace
   would destroy a selection under an Alt-tap that promised
   subtraction; auto-convert is lossy today
   (`convertSelectionToPickMode` returns null for edge to face); and
   the `toggleSelectionInSet` restart is a click-toggle policy that
   does not authorize rewriting an explicit combine mode (Codex).
   Ruled by Fable and Codex, orchestrator concurring: an explicit
   destructive operation fails loud. Opus's replace-by-precedent and
   Grok's degrade were overruled. Convert-on-combine is a separate
   phase 2 feature under any ruling.
6. **The whole expression validates before resolve (Codex round 4).**
   Predicates are type-independent of subject, so a direct payload can
   pair a face query with an `edge-state` predicate. Each aspect
   descriptor declares `supportedSubjects` alongside its tolerance
   capability, and the select-query descriptor's `canRun` validates
   the full expression (subjects shared, parts nonempty and
   subject-typed, attribute values nonempty, junction lists nonempty,
   aspects and relations supported for the subject, tolerance only
   where scalar), returning the truthful rejection before resolve
   runs. Compile helpers produce valid expressions by construction;
   `canRun` guards the actors that build payloads by hand.

**Active member (equivalence blocker, Grok B1 and Codex, folded).**
Today `selectSimilar` keeps the exemplar as the active selection
(`createSelectCommand(selection, nextSelectionSet)`); v0's
first-match rule was a silent UX change. Corrected rule: the resolver
returns only an ordered set; the *combine* step retains the current
active member when it survives in the combined result, and falls back
to the first member in scene order otherwise. The same retention rule
covers all four combine modes. Equivalence tests pin this.

**Atomicity (Codex, corrected round 3).** One command payload is not
enough: `createSelectCommand(selection, selectionSet)` is a single
payload whose registered handler still calls `setSelection` then
`setSelectionSet`, and `setSelection` clears the set, so a transient
empty set is observable today. The proposal therefore requires a
single selection aggregate port (`applySelectionResult(active, set)`
or equivalent) backed by one store transaction; the select-query
handler computes one combined result in domain and issues exactly one
write through that port.

## Command surface and placement

- **Domain** (`src/domain/selectionQuery.ts`, same home): the query
  and expression types, the aspect table, both resolvers,
  `compileSimilarExpression(scene, selection, selectionSet?, quantifier?)`,
  `compileLegacyQuery`, and `combineSelectionSets(base, incoming, mode)`
  next to `selection.ts` (about 30 lines of pure helpers on
  `getCubeSelectionKey`). One correctness trap, named by Opus (H3):
  combine `add` is a union and is idempotent; the existing
  `toggleSelectionInSet` is an XOR toggle. They are different
  operations with different callers; do not reuse toggle for add. Both
  may share a low-level union helper.
- **Interaction** (`src/interaction/commands/selection.commands.ts`):
  a `select-query` kind descriptor (target: selection, synchronous
  lane, non-reversible under the session stance). Its `run` resolves,
  combines, and writes the aggregate atomically. Proven seam: one
  registration file, zero switches.
- **Editor affordances**: bindings for the select-similar key with
  combine-mode modifiers.
- **App**: `useSceneOperations.selectSimilar` shrinks to compile +
  dispatch.

## Authoring ergonomics (how it feels)

The canvas is the control; the language must stay one-tap first.

- **One key survives.** "Select similar" compiles the smart default
  expression from the active selection *and the selection set*, so
  multi-exemplar costs the user nothing: shift-click two cubes, tap
  similar, get everything like either.
- **Combine modifiers.** Plain tap replaces, Shift adds, Alt
  subtracts, Shift+Alt intersects. Matches DCC muscle memory and the
  existing shift-click toggle convention. A rejected cross-subject
  combine surfaces as the command's truthful rejection, same as any
  other rejected synchronous command.
- **Refinement chips (phase 1.5).** After a query select, a transient
  HUD shows the compiled predicates as chips: `[face: top]` `[state]`
  `[scope: all]`. Toggling a chip re-resolves. The expression draft
  lives in editor session state and any non-query action discards it.
  Refinement happens on the canvas, never in a form. Deferred behind
  the mechanical core: real UI cost (Grok).
- **LLM actor.** Speaks the serialized `select-query` payload directly.
  Same surface, no privilege (the MODEL.v2 thesis).

Every phase 1 feature traces to an authoring need:

- **Combine modes**: "all black faces except the top plane" is select
  similar, then subtract with a plane scope. Core sculpting workflow.
- **Multi-exemplar**: "everything like either of these two."
- **Negate**: "every cube that does NOT share this state" for
  invert-and-fix passes. Model-level in phase 1; a binding can wait.
- **Tolerance**: opacity and size are analog-scrubbed floats; exact
  equality lies the moment a drag ends at 0.4999. Comparator-owned,
  scalar fields only, default epsilon, no slider. Decided for phase 1
  (Fable, Grok, Codex; Opus deferral overruled, may appeal).

## Phase line

**Phase 1 (one strangler PR series, Grok's ship list):**

1. Discriminated query and expression types, aspect table, both
   resolvers, in domain.
2. `compileLegacyQuery` for all 7 kinds; equivalence tests (including
   active-member retention); legacy union deleted at the end.
3. `compileSimilarExpression` in domain.
4. `select-query` descriptor with combine algebra and atomic write.
5. Re-point `selectSimilar` to compile + dispatch, `replace`.
6. Combine-mode key modifiers (may trail as a follow-up PR).
7. Relation predicate family: `face-exposed`, `cube-exposed`, and the
   `edge-junction` mask classifier (orchestrator ruling: the driving
   test is the acceptance bar for this reopen; a phase 1 that cannot
   compile it defeats the reframe).
8. Shared occupancy index in domain (`neighbors.ts` refactored onto
   it) and `src/domain/exposure.ts` derivations.
9. Semantic projections `face-perimeter`, `axis-parallel`
   (orchestrator ruling: free and genuinely used), and `all`,
   expanded at resolve via `cubeTopology.ts`.
10. The acceptance matrix fixtures, the 2x2x2 outer-top-edges worked
    example pinned end to end, flat-seam exclusion asserted.

Model-present but UI-deferred: negate, tolerance epsilon, relation
predicates beyond the face-gesture compile (palette and chips are the
authoring round).

**Phase 2 (each needs a demonstrated need before build):**

- Nested authoring trees compiling to the expression normal form.
- Persistence, with three distinct nouns (Codex naming, folded).
  **SavedExpression**: a persisted definition, made durable by
  self-containedness (materialize `selected` and `selection-set`
  scopes to id lists at save time). **NamedSelection**: a frozen
  member snapshot, the explicitly requested named-selection concept,
  whose stored ids must repair or prune across `resizeGridScene`
  renames (the `repairScore` parallel). **LiveExpression**: a
  persisted definition plus a reactive binding. Persistence home
  (document vs preferences) is decided then.
- Live/reactive expressions. This is a hard boundary, and Codex's
  costing stands: candidate count times predicate count times value
  count, with face and edge subjects expanding 2025 cells to as many
  as 36450 parts, invalidated at pointer-scrub input rate. Needs
  dependency invalidation, transaction-boundary re-resolution,
  gesture-pinned edit targets, one-shot combine semantics, a rule that
  live expressions cannot feed on live selection (cycle), and the id
  repair above.
- Threshold UI for tolerance (Blender precedent).
- Literal-valued predicates and any text DSL surface.
- ShapeUtil-contributed aspect descriptors (seam designed now,
  registration later).
- Cross-subject convert-on-combine.
- A separate `visibility` aspect, if chips desugar `cube-state`.
- The `visible` occupancy policy, with hidden-owner candidates
  excluded by definition (the phase 1 soundness hole, closed by
  specification before it ships).
- Connectivity and flood selection (select-linked, connected
  components, boundary-loop traversal): a distinct relational family
  over graph reachability, named separately so it never conflates
  with exposure (Opus).
- View-dependent relations: camera silhouette, world-facing
  projections under `CubePlacement.rotation` divergence (Codex
  reserves "silhouette" for this).

## Strangler migration (no rip-and-replace)

1. **Introduce beside.** New types and resolvers land in
   `src/domain/selectionQuery.ts`. The legacy union stays; a
   `compileLegacyQuery(legacy): SelectionExpression` maps all 7 kinds.
   Legacy `resolveSelectionQuery` becomes compile + new resolver. The
   equivalence obligation, stated precisely (Opus): for each legacy
   kind over representative scene and context, old resolve and new
   resolve-of-compile produce identical set membership by
   `getCubeSelectionKey` and an identical active member; `items[]`
   order is set-semantic and may differ. Legacy compiles carry no
   tolerance, so matching stays exact. This is the acceptance gate
   between steps 1 and 2.
2. **Re-point the trigger.** `selectSimilar` dispatches `select-query`
   through the executor with `combine: 'replace'`. Zero UX change.
3. **Grow.** Modifiers, multi-exemplar, negate, tolerance. Each is
   additive on the shipped core.
4. **Delete.** When no caller constructs a legacy kind, the union and
   the shims go. A PR that leaves both paths alive past this point is
   incomplete (DRY rule).

## Prior art (corrected by Codex)

- **AutoCAD**: QSELECT is one property predicate per invocation, with
  repeated narrowing; FILTER holds saved boolean filters; SELECTSIMILAR
  takes one or more samples and adds matches. The earlier claim that
  QSELECT validates a flat-only language is withdrawn; what the family
  does validate is any-of union over multiple samples plus additive
  combine, which is exactly the phase 1 expression form.
- **Blender Select Similar**: property plus equal/greater/less and a
  threshold slider; precedent for comparator-owned tolerance. Blender
  keeps the relational selections **separate** from Select Similar,
  as their own operations: Non-Manifold and Faces by Sides under
  Select All by Trait, Boundary Loop under Select Loops, Select Sharp
  Edges standalone. Precedent for relation predicates as their own
  family, not attribute aspects.
- **Maya**: distinguishes exterior and interior border edge selection
  from connected border paths; precedent for the exposure vs
  connectivity family split.
- **Houdini Group**: combines a base scope with unshared-edge,
  boundary, normal, and edge-angle criteria; the closest prior art to
  scope plus relation predicates in one query, with connectivity
  traversal layered later.
- **Illustrator**: Same menu, single-aspect, replace-only; the floor we
  are leaving.
- **tldraw**: reactive StoreQueries kept separate from selected ids;
  precedent for phase 2's live-vs-selection separation.

## Vocabulary note: Predicate vs Criterion

The mission brief names both. This spec reserves **Predicate** for the
atomic leaf carried in a query's `predicates` list, in either family:
a typed attribute comparison or a relation test. **Criterion** names
the recursive boolean composition over predicates, which in phase 1
exists only as the flat AND list plus the expression union, and which
phase 2's authoring tree would inhabit (Codex ubiquitous-language
delta, folded; relation leaf admitted per Grok's v0.3 nit).

## Decision state

**Settled by consensus:**

- `subject` naming (Opus conceded; Grok and Codex concurred).
- Flat DNF expression carrier; no tree in phase 1. Opus conceded (C1),
  Codex confirmed the expression satisfies AND/OR/NOT conditional on
  the exemplar quantifier, which is folded.
- Tolerance in phase 1 with Opus's guards: descriptor capability,
  compile error on non-scalar, absent means exact, legacy compiles
  exact, epsilon opt-in shipped separately.
- Any-of within a predicate is closed as the only coherent semantics
  for single-valued aspects (Opus OQ1 category argument); "similar to
  all" is served by the compile quantifier.
- `cube-state`: composite presentation, descriptor fold over an
  explicit opt-in component list.
- Undoability: non-reversible, session stance, rides any future
  Selection history decision uniformly.
- Compile helpers live in domain; combine algebra lives in domain;
  selection writes go through one atomic aggregate port.
- Query draft home (phase 1.5): editor session slice, transient,
  invalidated by any selection mutation not routed through
  select-query.

- Cross-subject `add`/`subtract`/`intersect`: truthful reject.
  Settled by the orchestrator's concurrence with Fable and Codex;
  Opus's replace-by-precedent and Grok's degrade overruled. This
  satisfies Codex's sign-off condition.

**Minor open detail:** which state fields are tolerance-capable
beyond opacity and thickness, and the epsilon constant's value. Owned
by the phase 1 implementer; descriptor-internal either way.

**Sign-off state: UNANIMOUS on v0.3 as filed.** The v0.2 attribute
surface was unanimously signed off and is unchanged. The reopen's
additions (relation predicate family, semantic projections, the
invariant 4 rewrite, the worked example and acceptance matrix) were
re-reviewed and signed off by Codex (final consistency scan passed),
Grok (contract spine verified, lateral-exposed overrule accepted),
and Opus (contract and layering verified against the code and its
own geometry; both of its overruled calls accepted with rationale,
resolve-time expansion called the better design). Orchestrator
rulings folded: edge-junction classifier phase 1, flat-seam exclusion
pinned as a test, axis-parallel phase 1. Ready for the phase 1
strangler greenlight.

**Implementer notes (Opus, non-blocking):**

1. Make active-member retention a pure domain helper
   (`resolveActiveMember(combined, priorActive, scene)`) rather than
   inline handler logic; it references scene order and sits on the
   equivalence-test path.
2. `combineSelectionSets` empty-base edges are plain set algebra
   (intersect or subtract from empty is empty; add to empty is the
   incoming set); no special cases, just pin them in tests.

## Deltas ledger

**Opus pre-brief and delta round, folded:** three-concept
decomposition (scope, projection, predicate); materialized values;
query is data, resolver is code; aspect descriptor registry as the
ShapeUtil seam; combine at the command layer (Slice B); purity and
determinism mandate; homogeneity; no text DSL; strangler stages; C1
concession with the product-term reframe and the saved-OR phase
consequence; C2 tolerance guards (capability flag, compile error,
default exact); C3 subject; OQ rulings (any-of closed, draft home,
cube-state fold, undoability, compile home); H1 batch return type
(the expression); H2 self-containedness; H3 combineSelectionSets and
the add-is-not-toggle trap; the migration equivalence obligation;
part typing by subject.

**Opus positions overruled:** phase 1 tree (conceded); tolerance
deferral (conceded); cross-subject replace-by-precedent (reject
settled by orchestrator concurrence; Opus accepted without appeal).

**Grok deltas, folded:** T1 typed predicate discrimination; T2
subject-discriminated query with required part; T3 aspect table as
engine, ShapeUtil as comment seam; T4 purity restated honestly
(option A); B1 active-member retention; the expression resolver in
domain; combine algebra as domain helpers; tolerance constraints;
typed snapshot clarification; phase ship list; chips deferred;
visibility aspect deferred; open-question votes.

**Grok deltas, overruled:** cross-subject degrade-to-replace
(escalated with the reject ruling).

**Codex deltas, folded:** correlation unsoundness (fixed by
per-exemplar-part query emission; converged with Opus H1);
serialization and provenance demands (met by the expression form,
confirmed); compile needs scene (signature amended); typed operands;
empty-values rejection and the negate-after-empty hazard; scope purity
flag; homogeneity by construction; truthful cross-subject rejection
(and its click-toggle-policy argument); active-member equivalence
blocker; atomic aggregate port (round 3 correction: one payload is not
one write); candidate defined as the cell-part pair; part enumeration
determinism; part-state correlation; size tolerance as max-abs;
cube-state as authored visible state; composite safety (opt-in
component list); exemplar quantifier (any/all); expression validation
in `canRun` with `supportedSubjects`; Predicate/Criterion vocabulary
split; SavedExpression / NamedSelection / LiveExpression nouns; prior
art corrections; live-expression cost inventory.

**Codex sign-off (v0.2 surface):** confirmed; its condition (truthful
rejection for cross-subject algebraic combines) is the settled ruling
per the orchestrator's concurrence.

## Reopen ledger (v0.3)

**Driving test case (Stuart, via orchestrator):** "select all outer
top edges" on a 2x2x2; unexpressible in v0.2; now the phase 1
acceptance bar, compiled end to end in the relational section.

**Opus reopen deltas, folded:** exposure is a relational predicate
family (not a scope kind, not a fourth axis; predicate families split
by what they read); invariant 4 rewrite with the translation-invariance
law; relation predicates as the literal-value customer;
self-containedness redefined as no selection-context dependence, with
relation predicates live-by-nature; `exposure.ts` as the domain home
(cohesion); connectivity named as a distinct future family.

**Opus reopen deltas, overruled:** compile-time projection expansion
(resolve-time expansion keeps intent in the carrier; provenance);
`visible` occupancy default (structural is the pinned domain
contract); `outer`/`exposed` as the edge vocabulary (subsumed by the
junction classifier: outer = convex, exposed = not interior).

**Grok reopen deltas, folded:** relation-vs-scope-vs-projection table;
predicate family type shape; the 4-quadrant neighborhood generation
from `cubeEdgeTopology.lockedAxes` and `signs`; shared occupancy index
and cost bounds; semantic projection types; the named nightmares
(exposure in scope, materialized exposure, one mode for all intents);
hidden-as-solid default.

**Grok reopen deltas, overruled or absorbed:** `edge-lateral-exposed`
(under-constrains at `scope: all`; a bottom cell's mid-facade top edge
passes it; absorbed by the convex mask class); `hiddenAs`
per-predicate knob (unsound under a hidden owner; structural-only in
phase 1).

**Codex reopen deltas, folded:** the junction-classifier blocker (a
count-based exterior test wrongly selects flat seams; five-class mask
ruled phase 1 by the orchestrator); the verified 8/16/32 worked proof;
part-identity multiplicity (no assembly-edge dedupe); structural
occupancy as the spacer contract; `getNeighborCubeId` unsuitability;
semantic projections as local-topology descriptors; no ring inference
from one edge tap; consistency sweep (family-scoped value rules,
purity claims, and validation; shared index per resolution); the
occupancy-knob soundness hole (zero-owner state); projection lifecycle
(resolve-time expansion through the public type); acceptance matrix;
relational prior art (Blender traits, Maya borders, Houdini groups);
`axis-parallel` inclusion (orchestrator concurred); "silhouette"
reserved for view-dependent relations.

**Orchestrator reopen rulings:** edge-junction classifier in phase 1;
flat-seam exclusion pinned as a test; axis-parallel in phase 1;
reopen framing (relational selection was the real maturity gap).
