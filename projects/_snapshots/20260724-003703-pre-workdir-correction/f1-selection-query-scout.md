# Cubicell selection query scout

Date: 2026-07-17  
Repository: `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`  
Observed branch and head: `main` at `277589ddb72c41e6da07768e66e179aa3d104440`

## Verdict

- Capability status: **complete for the implemented phase 1 contract**.
- UI status: **partially surfaced**.
- The generic query language is a typed, serializable JSON object model. There is no text DSL.
- Production UI already dispatches `select-query` for Similar, structure layer selection, and structure marquee selection.
- Attribute based Similar is human reachable. Relation predicates, semantic projections, the `all` exemplar quantifier, and general query composition have no production caller.

## 1. What exists

### Carrier and algebra

`src/domain/selectionQuery.ts:SelectionQuery` and
`src/domain/selectionQuery.ts:SelectionExpression` define the carrier:

- A `SelectionExpression` is an array of queries. Queries resolve independently and union, so the array is OR.
- A query's `predicates` all have to match, so predicates within one query are AND.
- An attribute predicate's `values` are any of, so values within one predicate are OR.
- `negate` inverts one completed predicate test.
- `tolerance` is allowed only for scalar capable aspects.
- Every expression is homogeneous by subject: cube, face, or edge.
- `scope` limits candidate cubes before predicates run.
- Face and edge subjects carry a part projection.

`src/domain/selectionQuery.ts:validateSelectionExpression` is the truthful payload gate. It rejects empty expressions, mixed subjects, invalid projections, unsupported subject and predicate combinations, empty values, invalid tolerance use, and invalid relation data.

`src/domain/selectionQuery.ts:resolveSelectionExpression` is the sole public evaluator. It resolves each query, preserves deterministic scene and part order, unions results, and deduplicates through `createCubeSelectionSet`. It builds one shared occupancy index only when a relation predicate needs it.

### Queryable data

| Family | Implemented vocabulary | Evidence |
| --- | --- | --- |
| Subject | cube, face, edge | `src/domain/selectionQuery.ts:SelectionQuery` |
| Cube attributes | `size`; `cube-state` | `src/domain/selectionAspects.ts:attributeAspects` |
| Cube state fields | width, height, depth; cube visibility; all face states; all edge states | `src/domain/selectionAspects.ts:CubeStateSnapshot`, `createCubeStateSnapshot` |
| Face state | color, opacity, visibility | `src/domain/selectionAspects.ts:attributeAspects['face-state']`; source shape in `src/domain/cube.ts:CubeFaceState` |
| Edge state | color, opacity, thickness, visibility | `src/domain/selectionAspects.ts:attributeAspects['edge-state']`; source shape in `src/domain/cube.ts:CubeEdgeState` |
| Relations | face exposed, cube exposed, edge junction | `src/domain/selectionAspects.ts:relationDefs` |
| Junction classes | convex, flat seam, non manifold, concave, interior | `src/domain/exposure.ts:edgeJunctions` |
| Face projections | explicit face ids, all faces | `src/domain/selectionQuery.ts:FaceProjection` |
| Edge projections | explicit edge ids, all edges, one face perimeter, one axis parallel set | `src/domain/selectionQuery.ts:EdgeProjection`, `expandEdgeProjection` |
| Candidate scopes | single id, explicit ids, selected cube, selection set, all, axis through a coordinate, plane, even or odd axis pattern | `src/domain/cubeOperations.ts:CubeScope`, `resolveCubeScope` |

Placement is available only as scope selection. There is no placement, offset, rotation, scale, class, layer, tag, polarity, or scene projection predicate. Ids are scope inputs, not predicate values.

### Similar compiler

`src/domain/selectionCompile.ts:compileSimilarExpression` converts the active selection and selection set into a valid expression:

- Cubes compile to materialized full visible state snapshots.
- Faces compile to face id plus face state.
- Edges compile to edge id plus edge state.
- `any` unions exemplar matches.
- `all` emits conjunctive single value predicates.
- Deleted, duplicate, and cross subject exemplars are handled explicitly.

### Command entry point

`src/editor/commands.ts:createSelectQueryCommand` creates the actor neutral serializable command:

```ts
{
  kind: 'select-query',
  expression: SelectionExpression,
  combine: 'replace' | 'add' | 'subtract' | 'intersect'
}
```

`src/interaction/commands/selection.commands.ts:registerSelectionCommands` validates the payload, rejects cross subject set algebra outside replace, evaluates against the live scene and selection context, combines the result, resolves the active member, and writes the active selection plus selection set atomically through `CommandPorts.selection.applySelectionResult`.

The command is synchronous, non repeating, and reversible. `src/editor/affordances.ts:getCombineModeForModifiers` supplies one shared pointer grammar: plain replaces, Shift adds, Alt subtracts, and Shift plus Alt intersects.

## 2. Completeness

The implemented carrier, evaluator, validation gate, Similar compiler, command descriptor, combine modes, atomic write, and current integrations are covered and passing.

Verification run from the observed head:

```text
pnpm exec vitest run \
  tests/domain.test.ts \
  tests/selectionQuery.test.ts \
  tests/selectionQuery.relations.test.ts \
  tests/selectionQuery.similar.test.ts \
  tests/selectQuery.command.test.ts \
  tests/selectSimilar.command.test.tsx \
  tests/selectSimilar.modifiers.test.tsx \
  tests/structureSection.test.tsx \
  tests/selectionUndo.test.ts

Test Files  9 passed (9)
Tests       186 passed (186)
```

```text
pnpm exec tsc -b --pretty false --force
exit 0
```

Coverage map:

| Test file | Coverage |
| --- | --- |
| `tests/selectionQuery.test.ts` | Determinism, id and contextual scopes, attribute matching, AND, OR, negate, tolerance, correlation, cube state, union, dedupe, total empty behavior, semantic projections |
| `tests/selectionQuery.relations.test.ts` | Canonical outer top edge fixture, face and cube exposure, every edge junction class, negation, multiplicity, shared occupancy index, relation validation |
| `tests/selectionQuery.similar.test.ts` | Cube, face, and edge exemplar compilation; any and all; correlation; deleted, duplicate, and mixed exemplars |
| `tests/selectQuery.command.test.ts` | All combine modes, active member rules, empty results, selected scope, cross subject rejection, invalid payloads, atomic aggregate port |
| `tests/selectSimilar.command.test.tsx` | End to end Similar compilation and dispatch from `useSceneOperations` |
| `tests/selectSimilar.modifiers.test.tsx` | Shared modifier grammar and Similar button dispatch |
| `tests/structureSection.test.tsx` | Plane and id scoped query dispatch from layer and marquee selection |
| `tests/selectionUndo.test.ts` | Reversibility registration for set yielding query commands |
| `tests/domain.test.ts` | Additional direct evaluator coverage in established domain fixtures |

No TODO or FIXME appears in the carrier, evaluator, compiler, or command handler.

The following are bounded language limits, not unfinished branches in the evaluator:

- The aspect registry comments name a future ShapeUtil registration seam.
- Visibility is queryable through `cube-state`, while a standalone visibility aspect remains pending.
- The carrier is a flat union of conjunctive queries. It has no arbitrary nested boolean tree.
- Literal id predicates, saved expressions, named selection sets, and scene reactive expressions do not exist.

The material completeness gap is in exposure: production code never constructs a relation predicate or semantic projection. The `all` quantifier is implemented but the UI always calls `compileSimilarExpression` with its default `any`.

## 3. Current callers

### Production callers

1. **Similar in the Inspector**

   `src/panels/SelectionSection.tsx:SelectionSection` renders the Similar button and derives the combine mode from pointer modifiers. `src/panels/Inspector.tsx:Inspector` owns that section. `src/app/App.tsx:App` passes `useSceneOperations.selectSimilar`, which calls `src/domain/selectionCompile.ts:compileSimilarExpression` and dispatches `src/editor/commands.ts:createSelectQueryCommand`.

2. **Structure marquee selection**

   `src/panels/StructureSection.tsx:commitMarquee` emits one cube query with no predicates and an explicit ids scope. It uses the same combine modifier mapping.

3. **Structure layer selection**

   `src/panels/StructureSection.tsx:selectLayer` emits one cube query with no predicates and a plane scope. It uses the same combine modifier mapping.

4. **Generic command execution**

   `src/interaction/commands/selection.commands.ts:registerSelectionCommands` is the only production caller of the evaluator. `src/app/useSynchronousEditorCommands.ts:useSynchronousEditorCommands` supplies the live command context and store ports.

### Dormant capability

- No production caller constructs `face-exposed`, `cube-exposed`, or `edge-junction`.
- No production caller constructs `face-perimeter` or `axis-parallel`.
- No production caller invokes `compileSimilarExpression` with `all`.
- No editor session state retains the last expression or a query draft.
- No generic query readback, chip editor, raw object editor, saved query surface, or command palette exists.

The capability therefore has real UI callers, while its distinctive relation, projection, and composition power remains unavailable to a human.

## 4. Surfacing reuse map

| Concern | Existing owner | Reuse |
| --- | --- | --- |
| Committed selection | `src/state/cubicellState.ts:CubicellEditorSession.selection`, `.selectionSet` | Continue using the existing Selection aggregate and editor session fields |
| Atomic selection write | `src/state/actions/selectionActions.ts:createSelectionActions.applySelectionResult` | Every query result lands through this one transaction |
| Query evaluation and validation | `src/domain/selectionQuery.ts:resolveSelectionExpression`, `validateSelectionExpression` | UI compiles payloads and dispatches; it does not evaluate or write selection itself |
| Exemplar compilation | `src/domain/selectionCompile.ts:compileSimilarExpression` | Add named compilers beside this existing compiler instead of constructing payloads independently in components |
| Query command | `src/editor/commands.ts:createSelectQueryCommand` | All actors keep one serializable payload |
| Command handler | `src/interaction/commands/selection.commands.ts:registerSelectionCommands` | Preserve validation, combine algebra, active member resolution, reversibility, and atomic write |
| React dispatch | `src/panels/editorCommandContext.ts:useEditorCommandDispatch`, `src/panels/EditorCommandProvider.tsx:EditorCommandProvider` | New UI dispatches through the existing provider |
| App command execution | `src/app/useEditorCommands.ts:useEditorCommands`, `src/app/useSynchronousEditorCommands.ts:useSynchronousEditorCommands` | No parallel event bus or selection service |
| Human entry point | `src/panels/SelectionSection.tsx:SelectionSection` inside `src/panels/Inspector.tsx:Inspector` | Contextual selection verbs belong beside Similar |
| Existing structured selection | `src/panels/StructureSection.tsx:StructureSection` | Keep plane and marquee selection on the same query command |
| Combine grammar | `src/editor/affordances.ts:getCombineModeForModifiers` | Apply to every new pointer invoked query verb |
| Keyboard catalogue | `src/editor/affordances.ts:editorCommandIds`, `editorCommandDefinitions`; `src/editor/keyboard/keymap.ts` | Extend only for selected named verbs. Dynamic expressions still compile from live context before dispatch |
| Transient draft home | `src/state/cubicellState.ts:CubicellEditorSession` | A draft belongs beside selection and pick mode. It should not enter Workbench, document history, or persistence |

The current domain barrel exports the query types and evaluator, but only the descriptor types. A descriptor driven editor should expose the existing `attributeAspects` and `relationDefs` metadata through the domain boundary, or add UI safe metadata to those descriptors. Re declaring aspect, relation, projection, or junction vocabularies in UI code would violate the existing single source of truth.

## 5. PR sized surfacing plan

### PR 1: Outer perimeter vertical slice

- Add a named compiler beside `compileSimilarExpression` for the canonical face exemplar to outer perimeter expression: edge subject, face perimeter projection, convex edge junction relation.
- Invoke it from the existing selection operations path.
- Add one contextual button beside Similar in `SelectionSection`.
- Use `getCombineModeForModifiers` and `createSelectQueryCommand` unchanged.
- Prove the canonical solid 2 by 2 by 2 result through compiler, command, and component tests.

This is the smallest slice that makes the already tested relation and semantic projection capability human reachable.

### PR 2: Complete the named verb layer

- Add shared compilers for Exposed faces, Shell, Interior, Along axis, Outer edges, and conditional Similar to all.
- Keep payload construction in domain compilers. Components receive intent functions or definitions, never duplicate query objects.
- Render only verbs valid for the active subject in `SelectionSection`.
- Reuse the existing modifier combine grammar for every button.
- Add focused compiler and dispatch tests for every verb and every subject transition.

### PR 3: Retain a query draft and pin its combine base

- Add an optional serializable `against: { selection, selectionSet }` to the existing `select-query` command. When absent, preserve current one shot behavior.
- Thread the effective base through validation of cross subject combine, resolution context, combine base, and active member retention in `registerSelectionCommands`.
- Add transient query draft state to `CubicellEditorSession`: expression, combine, captured base, provenance needed for any or all recompilation, and last applied result.
- Extend the existing selection command port and store action so a query result and its draft metadata land atomically. Manual selection writes clear the draft. View and transport commands leave it intact.
- Add command, store, invalidation, and resummon tests. Do not persist or history record the draft.

Pinned base is required before editable re dispatch. Combining against the result of the preceding query would self feed and make refinement order dependent.

### PR 4: Query readback strip

- Mount one query readback component inside the existing `EditorCommandProvider` composition so it consumes the current draft and existing dispatch.
- Render subject, scope, projection, predicate, combine, and result count from the exact serialized payload.
- Use existing Button, Segmented, action row, and floating panel styling contracts.
- Support dismiss and Last query first. The committed selection remains when the draft closes.
- Test lifecycle, external selection invalidation, subject flips, view and transport survival, and accurate readback of multi term expressions.

### PR 5: Incremental refinement controls

- Expose the existing descriptor metadata through the domain barrel. Do not recreate vocabulary in the panel.
- Add family aware predicate editing: negate, scalar tolerance where the descriptor permits it, junction classes, and materialized state summaries.
- Add typed projection editing and scope cycling over all, selected, and selection set first.
- Add the any or all control by recompiling from retained provenance.
- Re dispatch through `createSelectQueryCommand` with the captured base on every edit.
- Gate spatial scope pickers, saved expressions, live expressions, and a general palette on demonstrated demand.

Each slice preserves one evaluator, one command payload, one combine grammar, one selection aggregate, and one atomic write path.
