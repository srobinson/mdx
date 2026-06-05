# Cubicell selection query language: the digest

One page. The full record with every argument and ledger is
[cubicell-select-similar-lang.md](cubicell-select-similar-lang.md)
(v0.3, canonical). The implementation slices are
[cubicell-select-similar-PLAN.md](cubicell-select-similar-PLAN.md).
This page is the single source of naming truth; the plan and the
canonical doc use these words.

## What it is

A serializable query language that replaces the hardcoded 7-kind
"select similar". Any actor (key press, palette, LLM) dispatches the
same JSON payload; a pure domain resolver turns it into a selection
set; the command layer combines that set with the current selection.

## The vocabulary (source of naming truth)

| Term | Meaning |
| --- | --- |
| **Subject** | What a query yields: `cube`, `face`, or `edge`. One query, one subject kind. |
| **Scope** | Which cells compete. Reuses `CubeScope` (all, axis, plane, pattern, selected, selection-set). |
| **Projection** | Which parts a face/edge query emits per cell: literal `ids`, `all`, `face-perimeter(faceId)`, `axis-parallel(axis)`. Local topology, expanded at resolve. |
| **Predicate** | One testable condition per candidate. Two families below. |
| **Attribute predicate** | Tests owned authored state (size, face-state, edge-state, cube-state) against typed values **materialized at compile** from exemplars. Optional negate; tolerance on scalar aspects, absent means exact. |
| **Relation predicate** | Tests scene topology, **asserted, no exemplar**: `face-exposed`, `cube-exposed`, `edge-junction` (mask classes: convex, flat-seam, non-manifold, concave, interior). Re-derives every resolve. |
| **Aspect** | A comparable property behind a descriptor (read + match + supportedSubjects + scalar capability). The future ShapeUtil registration seam. |
| **Exemplar** | A selection the compile step reads values from. Plural. The resolver never sees one. |
| **Query** | subject + scope + projection + predicates (AND, per-leaf negate). Plain data. |
| **Selection expression** | `SelectionQuery[]`: queries resolve independently and union. The serializable OR (DNF). |
| **CombineMode** | How the resolved set meets the current selection: replace, add, subtract, intersect. Lives on the command, never in the query. |

Reserved words: **Criterion** = the phase 2 boolean tree over
predicates. **Silhouette** = the future view-dependent relation.
**SavedExpression / NamedSelection / LiveExpression** = the phase 2
persistence nouns.

## The five load-bearing rules

1. **DNF carrier.** AND inside a query, union across the expression.
   Full AND/OR/NOT expressiveness with no tree walker; multi-exemplar
   compiles one query per distinct exemplar part (correlation
   preserved).
2. **Resolve is pure; combine is not resolution.** `resolve(scene,
   expression, context)` is deterministic; combine modes apply in the
   command handler through one atomic selection write. Cross-subject
   add/subtract/intersect are truthfully rejected.
3. **Two predicate families by what they read.** Attribute reads the
   candidate's own state (values frozen at compile). Relation reads
   the neighborhood (never frozen; "outer" stays true after an
   extrude). Occupancy is structural: hidden spacer cells count as
   occupied.
4. **Translation invariance splits scope from predicate.** A condition
   that changes truth when the assembly translates is a coordinate
   test and belongs to scope; translation-invariant conditions
   (exposure, junctions) are relation predicates.
5. **Strangler, not rewrite.** All 7 legacy kinds compile onto the
   language with proven equivalence (identical set keys, identical
   active member); the legacy union is deleted at the end.

## The worked example

"Select all outer top edges" on a solid 2x2x2:

```ts
[{
  subject: 'edge',
  scope: { kind: 'all' },
  part: { kind: 'face-perimeter', faceId: 'top' },
  predicates: [{ kind: 'relation', relation: 'edge-junction', junctions: ['convex'] }],
}]
```

The projection emits 4 top-ring edges on each of 8 cells (32
candidates); the junction masks split 8 convex, 16 flat-seam, 8
interior; the query resolves exactly the 8 outer perimeter edge
parts and excludes the internal roof seams. This case is the phase 1
acceptance bar.

## Status

v0.3 signed off unanimously (Codex, Grok, Opus; orchestrator rulings
folded). Spec complete, no code written. Phase 1 is a strangler PR
series; see the plan.
