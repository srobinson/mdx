# Selector pick mode scout

Date: 2026-07-18  
Repository: `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`  
Branch: `main`  
HEAD: `baa039a73c7414ec9bc4435cf7b15038e24f4202`  
Verdict: **MATCH**

## Executive answer

1. Plain Tab changes the interpretation of the next canvas pick and immediately restates the current committed selection in the new subject vocabulary when a valid conversion exists.
2. A selected cube becomes six live faces through the pick mode conversion path. It requires no second canvas pick and does not rerun a selector query.
3. This behavior satisfies the Selector reachability requirement. A cube canvas pick can pivot to the face subject with one Tab press, then to the edge subject with a second Tab press. Face and edge verbs therefore become reachable from a cube selection.

## Exact Tab trace

1. `tab` maps to `pickModeCycle` in `src/editor/keyboard/keymap.ts:30-43`.
2. Plain Tab is globally owned by the cycle, including editable focus, and dispatches the resolved command through the held command input in `src/editor/keyboard/KeyboardShortcuts.tsx:19-42`.
3. The command descriptor calls `ports.mode.cyclePickMode()` in `src/interaction/commands/mode.commands.ts:40-61`.
4. The application port is bound to the store action in `src/app/useSynchronousEditorCommands.ts:81-88`.
5. `cyclePickMode` computes the next mode and calls `applyPickMode` in `src/state/actions/editorActions.ts:52-57`. The order is cube, face, edge in `src/editor/commands.ts:412-416`.
6. `applyPickMode` calls `convertSelectionToPickMode` with the committed `selection` and `selectionSet`, then commits the converted values alongside `pickMode` in `src/state/selectionCommit.ts:121-148`.
7. The converter expands a cube to all `cubeFaceIds` or `cubeEdgeIds`, expands a face to its perimeter edges, and deduplicates the result in `src/domain/selection.ts:229-303`.

For a single selected cube, the first Tab follows `cube -> face`, maps the cube across `cubeFaceIds`, and commits one active face plus a six item face selection set. The second Tab follows `face -> edge`; the six faces contribute their perimeter edges and set deduplication yields the cube's twelve unique edges. The third Tab follows `edge -> cube`, promotes every edge to its owner, and deduplicates the set back to one cube.

## Conversion matrix

| Current subject | Target subject | Committed result |
| --- | --- | --- |
| cube | face | Six faces per cube |
| cube | edge | Twelve edges per cube |
| face | edge | Four perimeter edges per face, deduplicated across the set |
| face or edge | cube | Owning cubes, deduplicated |
| edge | face | No conversion because one edge borders two faces |
| empty or same subject | any | Mode changes; selection remains unchanged |

The edge to face ambiguity is explicit in `src/domain/selection.ts:229-235` and covered at `tests/domain.test.ts:754-760`. It does not block the normal cycle. Edge cycles to cube, then cube cycles to face.

## Why the next click also changes

`pickMode` also controls canvas hit interpretation. A face hit selects its owner in cube mode, itself in face mode, or its perimeter edges in edge mode at `src/scene/CubeScene.tsx:287-307`. Dedicated edge hit targets are present only in edge mode at `src/scene/CubeScene.tsx:452-460`. Selection commits synchronize the mode to the resulting subject at `src/state/actions/selectionActions.ts:28-36`, `47-55`, and `68-81`.

This is a dual purpose mechanism:

* mode changes convert the current committed subject when a valid conversion exists;
* the resulting mode determines what the next canvas hit selects.

The live cube to six faces transition comes from the first responsibility. The scene click code is not involved in that transition.

## Selector verb reachability

The current behavior provides the required path:

1. Pick a cube on the canvas.
2. Press Tab once. The committed subject becomes six faces, so face input verbs are available.
3. Press Tab again. The committed subject becomes twelve edges, so edge input verbs are available.

Selector verbs can then perform their own subject transformations. For example, Outer Perimeter compiles and dispatches a `select-query` from a face selection, then commits six edge results for the tested slab at `tests/selectorPanel.test.tsx:486-509`. That query transformation is separate from pick mode conversion.

The only design caveat is terminology. `pickMode` sounds limited to future clicks, while the implementation also converts the live committed selection. A new Selector surface should expose the control as a subject pivot or selection level while preserving the canvas pick consequence.

## Verification

Root checkout verification:

```text
pnpm exec vitest run tests/domain.test.ts tests/state.test.ts tests/keyboard.test.ts tests/interaction.command.test.ts tests/selectionUndo.test.ts tests/selectorPanel.test.tsx --exclude '.claude/**'

Test Files  6 passed (6)
Tests       167 passed (167)
```

The first run lacked the explicit exclusion and also discovered stale suites inside `.claude` worktrees. Those unrelated failures were discarded. The root checkout command above isolates the named evidence and passes.

Direct test coverage confirms:

* cube to six faces and cube to twelve edges in `tests/domain.test.ts:701-714`;
* deduplicated face perimeter conversion and part promotion in `tests/domain.test.ts:716-751`;
* committed store conversion to twelve edges in `tests/state.test.ts:388-424`;
* face to four committed perimeter edges in `tests/state.test.ts:435-450`;
* plain Tab command dispatch and cycle behavior in `tests/keyboard.test.ts:281-293`.
