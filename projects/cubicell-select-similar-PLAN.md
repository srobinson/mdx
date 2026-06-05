# Cubicell selection query language: phase 1 implementation plan

Nine work slices, sequenced by dependency, each buildable and
reviewable as its own PR. Vocabulary lives in
[cubicell-select-similar-DIGEST.md](cubicell-select-similar-DIGEST.md)
(the naming source of truth). Full rationale, invariants, and ledgers
live in [cubicell-select-similar-lang.md](cubicell-select-similar-lang.md)
(canonical v0.3; line refs are against that revision; do not modify
it). Every slice is spec-complete: pick one up cold, build it, judge
it by its acceptance list.

Cross-cutting rules for every slice: no exceptions to the repo barrel
discipline (domain exports through `src/domain/index.ts`); commands
register through descriptors, zero switch edits; equivalence tests
compare set membership by `getCubeSelectionKey` plus the active
member, never `items[]` order; new files stay under the 700-line
threshold.

Dependency graph:

```text
A ─┬─ B ──────────────┐
   ├─ C ─┬─ G ─┬─ H ── I
   ├─ D ─┘     │
   ├─ F1 ─ F2 ─┘
E ─────────┘
```

(E is independent of A; F2 needs A, E, F1; H needs B, D, G, F2.)

## Slice A: the carrier and the attribute core

**Scope.** The language's types and the pure resolvers, attribute
family only. In `src/domain/selectionQuery.ts` (extending the file,
legacy union untouched): `SelectionSubject`, `AttributePredicate`
(discriminated by aspect: size, face-state, edge-state, cube-state,
typed `values[]`, `negate?`, `tolerance?`), `SelectionQuery`
(discriminated by subject; face/edge carry `part: { kind: 'ids' }` or
`{ kind: 'all' }` for now), `SelectionExpression`, the aspect
descriptor table (`AspectDef`: `read`, `match`, `supportedSubjects`,
scalar capability with a distance function; `cube-state` matcher is a
fold over an explicit opt-in component list, not `areCubeStatesEqual`),
`resolveSelectionQuery` and `resolveSelectionExpression` (union +
dedupe in domain). Candidates: the cell for cube queries, each
`(cell, partId)` pair for face/edge. Matching: any-of across a
predicate's values, AND across predicates, negate after the test;
absent tolerance means exact; tolerance on a non-scalar aspect and an
empty `values` are construction errors surfaced to `canRun` later.

**File homes.** `src/domain/selectionQuery.ts`, exports added to
`src/domain/index.ts`, tests in `tests/`.

**Acceptance.**
- Determinism: same scene/expression/context resolves the identical
  set twice; subjects emit in scene cell order, parts in declaration
  order.
- Any-of within one predicate; AND across predicates; negate.
- Tolerance: size max-abs per dimension; absent means exact
  (fixture: two sizes differing by 0.0005 match only with tolerance).
- cube-state fold equals `areCubeStatesEqual` behavior on identical
  fixtures (behavior-preserving).
- Homogeneous output by construction (type-level; no runtime test
  needed beyond compilation).

**Depends on.** Nothing.

**Reference.** Canonical "The model (phase 1 types)" (lines 89-258)
and "Resolution semantics" (433-538).

## Slice B: legacy compile and the equivalence gate

**Scope.** `compileLegacyQuery(legacy): SelectionExpression` mapping
all 7 kinds per the proof table (`same-axis` becomes scope
`{kind:'axis'}`; `same-edge`/`same-face` become pure projections with
zero predicates). The existing `resolveSelectionQuery(legacy)` becomes
compile + new resolver internally; its signature and callers do not
change in this slice. Legacy compiles carry no tolerance.

**File homes.** `src/domain/selectionQuery.ts`, tests in `tests/`.

**Acceptance.** For each of the 7 kinds over representative scenes
(mixed sizes, states, a hole, an axis line): old resolver output and
new resolve-of-compile produce identical set membership by
`getCubeSelectionKey`. This is the acceptance gate the strangler
stands on; it must be exhaustive over kinds, not sampled.

**Depends on.** A.

**Reference.** "Proof: the 7 legacy kinds compile" (408-432) and
"Strangler migration" step 1 (660-680).

## Slice C: combine algebra and active-member retention

**Scope.** Pure set helpers next to the selection model:
`combineSelectionSets(base, incoming, mode)` over
`getCubeSelectionKey` (replace, add = idempotent union, subtract,
intersect; add is NOT `toggleSelectionInSet`, which is XOR), and
`resolveActiveMember(combined, priorActive, scene)`: retain the prior
active member when it survives the combined result, else first member
in scene order.

**File homes.** `src/domain/selection.ts` (or a sibling
`selectionCombine.ts` if selection.ts nears the size threshold),
exports through the domain barrel, tests in `tests/`.

**Acceptance.**
- All four modes over disjoint, overlapping, and identical sets.
- Empty-base edges: intersect/subtract from empty is empty, add to
  empty is the incoming set.
- Active retention: survives when present; falls back to scene order
  when absent; covers all four modes.

**Depends on.** A (types only).

**Reference.** "Command surface and placement" domain bullet
(539-560) and the active-member and atomicity passages (513-538).

## Slice D: the similar compiler

**Scope.** `compileSimilarExpression(scene, selection, selectionSet?,
quantifier?)` in domain. Reads exemplars (active selection plus set),
materializes typed values, emits one query per distinct exemplar part
(correlation), unions via the expression. Quantifier `any` (default)
is that union; `all` emits one query with one single-value predicate
per materialized exemplar value. Deleted exemplars contribute nothing;
zero usable exemplars compile to an empty expression. The current
app-layer `createSelectSimilarQuery` logic moves down here (do not
duplicate it; the app copy dies in slice H).

**File homes.** `src/domain/selectionQuery.ts`, tests in `tests/`.

**Acceptance.**
- Correlation fixture: exemplars (top face, opacity 0.5) and (left
  face, opacity 1) do NOT select a cube whose top has opacity 1.
- Multi-exemplar cube case: two differently sized cubes select the
  union of both size matches (any-of).
- `all` quantifier: conflicting exact references resolve empty;
  agreeing references resolve the intersection semantics.
- Single-CUBE compile equals today's `createSelectSimilarQuery`
  (same-cube-state) through the resolver (ties into slice B's gate).
  Single FACE/EDGE compiles STATE-AWARE (face-state / edge-state), a
  deliberate blessed product change (Stuart, 2026-07-10, Option B); it
  does NOT equal legacy same-face / same-edge. Assert the new
  state-aware output with exact keys. Stateless "all top faces" is a
  zero-predicate projection query (F1), not this slice.

**Depends on.** A.

**Reference.** "Exemplar quantifier" and "Correlation under
multi-exemplar" (the model section, 89-258).

## Slice E: occupancy index and exposure derivations

**Scope.** Independent domain track, no query-language dependency.
A shared structural occupancy index (coord-key set/map built once per
consumer pass); refactor `neighbors.ts`'s private
`getOccupiedCoordKeys` onto it so the shadow shell and exposure share
one primitive (`getNeighborCubeId` is unsuitable: would-be slot ids,
linear finds). New `src/domain/exposure.ts`: `isFaceExposed(index,
cell, faceId)` (one lookup across `getNeighborCoord`),
`isCubeExposed` (any face), `classifyEdgeJunction(index, cell,
edgeId)` returning convex | flat-seam | non-manifold | concave |
interior from the four-quadrant mask (owner, +sign on each locked
axis, diagonal, via `cubeEdgeTopology.lockedAxes`/`signs`). Occupancy
is structural: hidden cells count as occupied.

**File homes.** `src/domain/exposure.ts` (new),
`src/domain/neighbors.ts` (refactor onto the shared index), domain
barrel, tests in `tests/`.

**Acceptance (the matrix core).**
- 1x1x1: 6 exposed faces, 12 convex edges.
- 2x2x2, all cells' top-perimeter edges: masks split 8 convex, 16
  flat-seam, 8 interior.
- Handcrafted step scene: concave (three quadrants) classified.
- Handcrafted diagonal contact: non-manifold (owner + diagonal), and
  it is NOT convex despite both incident faces being exposed.
- Hidden spacer: classifications unchanged when a cube's `visible`
  flips (structural contract).
- Translation invariance: every fixture re-asserted with the whole
  assembly translated to negative coordinates.
- `getSceneShadowShell` behavior unchanged after the index refactor
  (existing `tests/neighbors.test.ts` stays green).

**Depends on.** Nothing (parallel with A-D).

**Reference.** "Relational selection (the reopen)": relation
semantics, occupancy ruling, domain home and cost (259-407).

## Slice F1: semantic projections

**Scope.** Extend the projection unions in the carrier:
`face-perimeter(faceId)` (expands via `getCubeFaceEdgeIds`),
`axis-parallel(axis)` (filter on `cubeEdgeTopology.axis`), `all`
(declaration order). Expansion happens at resolve through the pure
topology tables; the carrier keeps the semantic intent. Projections
are local-topology descriptors (a rotated cube's `top` is its local
top). Expansion helpers live beside the tables.

**File homes.** `src/domain/cubeTopology.ts` (expansion helpers),
`src/domain/selectionQuery.ts` (union members + resolve wiring),
tests in `tests/`.

**Acceptance.**
- `face-perimeter('top')` emits exactly `getCubeFaceEdgeIds('top')`
  per cell, in declaration order.
- `axis-parallel` emits exactly the four edges of that axis per cell.
- `all` equals the full id list in declaration order.
- Empty `ids` list rejected at validation.

**Depends on.** A.

**Reference.** Model section projection types and the projection
rules (89-258).

## Slice F2: relation predicates and the canonical fixture

**Scope.** Extend `Predicate` with the relation family
(`face-exposed`, `cube-exposed`, `edge-junction` with nonempty
`junctions[]`, all with `negate?`), dispatching to `exposure.ts`
against one shared occupancy index built once per expression
resolution. Relation descriptors declare their subject; validation
rules (subject compatibility, nonempty junctions) join the same
descriptor-driven checks as aspects.

**File homes.** `src/domain/selectionQuery.ts`, tests in `tests/`.

**Acceptance.**
- THE canonical fixture, end to end through
  `resolveSelectionExpression`: 2x2x2, subject edge, scope all,
  `face-perimeter('top')`, `edge-junction ['convex']` resolves
  exactly the 8 outer top edge parts; the 16 flat-seam and 8 interior
  candidates are excluded. Assert exact selection keys.
- `face-exposed` on the 2x2x2: 24 exposed face parts (each cell's 3
  outward faces).
- Negated relation: `edge-junction ['convex']` negated selects the
  24 non-convex candidates of the same projection.
- Part multiplicity asserted as authored parts (a flat seam carries
  two coincident members; no assembly-edge dedupe).
- One occupancy index per expression resolution (structural: assert
  by construction or instrumentation, not wall clock).

**Depends on.** A, E, F1.

**Reference.** "Relational selection (the reopen)", worked example
and acceptance matrix (259-407).

## Slice G: the select-query command

**Scope.** A `select-query` kind descriptor in the registry: payload
`{ expression, combine }`. `canRun` validates the whole expression
from the descriptor tables (subjects shared across queries, parts
nonempty and subject-typed, attribute values nonempty, junction lists
nonempty, aspects and relations supported for the subject, tolerance
only where scalar) and truthfully rejects cross-subject add, subtract,
and intersect against the current selection. `run` resolves, combines
via slice C, resolves the active member, and writes through a single
atomic selection aggregate port (`applySelectionResult(active, set)`
or equivalent, one store transaction; the current setSelection then
setSelectionSet pair observably flashes an empty set and must not be
the path).

**File homes.**
`src/interaction/commands/selection.commands.ts` (descriptor),
`src/editor/commands.ts` (payload type),
`src/state/cubicellStore.ts` (the aggregate port), tests in `tests/`.

**Acceptance.**
- Dispatch through the executor applies each combine mode correctly
  (uses slice C fixtures end to end).
- Cross-subject add/subtract/intersect return the truthful rejected
  answer; replace switches subjects.
- Invalid payloads (mismatched subjects, empty values, empty
  junctions, tolerance on non-scalar) reject in `canRun`, before
  resolve.
- No transient empty selection set across the write (atomicity).
- Adding the command touched one registration file and zero switches.

**Depends on.** A, C (F2 optional at land time: validation is
descriptor-driven, so relation support arrives with F2's tables and
needs no edit here).

**Reference.** "Command surface and placement" (539-560), invariants
5 and 6 and the atomicity passage (433-538).

## Slice H: re-point select-similar and delete the legacy union

**Scope.** `useSceneOperations.selectSimilar` shrinks to
`compileSimilarExpression` + dispatch `select-query` with
`combine: 'replace'`; the app-layer `createSelectSimilarQuery` dies.
Then the strangler completes: delete the legacy `CubeSelectionQuery`
union and the compile shims once no caller constructs a legacy kind
(`compileLegacyQuery` and its tests go too; equivalence has served
its gate purpose). A PR that leaves both paths alive is incomplete.

**File homes.** `src/app/useSceneOperations.ts`,
`src/domain/selectionQuery.ts` (deletions), domain barrel, tests.

**Acceptance.**
- Scoped UX change (Stuart, 2026-07-10, Option B): CUBE taps behave
  identically on the slice B scenes (asserted through the command
  path); FACE/EDGE taps GAIN state matching (blessed change from
  legacy same-face / same-edge). Pin the new face/edge output with
  exact keys and call out the blessed change in the PR body.
- Active member stays the exemplar when it survives (legacy parity).
- `grep` proves no `same-edge|same-face|same-.*-state|same-size|same-axis`
  constructors remain outside tests-of-record.
- Full suite green with the legacy union gone.

**Depends on.** B, D, G (and F2 if landed; H is the last mechanical
slice either way).

**Reference.** "Strangler migration" steps 2-4 (660-680).

## Slice I: combine-mode key modifiers (trailing)

**Scope.** Affordance bindings: plain tap replaces, Shift adds, Alt
subtracts, Shift+Alt intersects, all compiling to the same
`select-query` dispatch with the combine field set. Feel constants,
if any, go to config, not hardcoded.

**File homes.** `src/editor/affordances.ts`,
`src/editor/keyboard/keymap.ts`, tests as the existing keymap tests
do.

**Acceptance.** Each modifier dispatches the right combine mode; a
rejected cross-subject combine surfaces as the command's rejection
with the selection untouched.

**Depends on.** G, H.

**Reference.** "Authoring ergonomics" (561-594).

## Out of scope for phase 1 (do not build)

Refinement chips and the query draft; boolean trees; SavedExpression,
NamedSelection, LiveExpression; tolerance threshold UI (the epsilon
stays a domain constant, opt-in and unshipped by default); the
`visible` occupancy policy; connectivity/flood selection; view
dependent silhouette; ShapeUtil aspect registration (comment seam
only). See canonical "Phase line" (595-659).
