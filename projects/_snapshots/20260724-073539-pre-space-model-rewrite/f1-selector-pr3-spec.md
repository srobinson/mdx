# F1 Selector PR3 spec: retained read only query draft

> **SUPERSEDED 2026-07-19 by PR #98 (`f6e728e` on `main`): live Cube / Face / Edge spatial builders.**
>
> What from this spec **did** land in related form: `SelectionQueryDraft` (`expression`, `combine`, `against`, `authoredByVerbId`); session slots `selectionQueryDraft` / `lastSelectionQueryDraft`; pinned base on `select-query`; live resolve against current topology; draft cleared on raw/manual selection paths; zero-match preserves last valid selection (`useRetainedSelectionBuilder`).
>
> What this spec described that **did not** ship as UX: locked SELECT/FROM/WHERE readback (`selectionReadback.ts` never added), static "Read only · authored by …" footer, combine-mode + APPLY chrome, LAST QUERY button, progressive clause materialization, disabled BUILD QUERY stub pending PR5.
>
> Replacement surface: subject builders (`CubeSpatialBuilder`, `FaceSelectionBuilder`, `EdgeSelectionBuilder`) with live editable spatial controls. See `f1-selector-evolution.md` (reconciled 2026-07-19). Body below kept for provenance only; do not implement as written.

Date: 2026-07-18
Status: **SUPERSEDED** (was: ready to build). Historical build plan for a read-only draft surface.
Baseline: `main` at `1dc84debfff70768ecafb3697594b298a91b5ca4`
Inputs: `f1-selector-ia-decision.md` (LOCKED model), `f1-selection-query-scout.md`, `f1-selector-evolution.md`, and `f1-selector-evolution/pr3-read-only-selector-draft.png`.
Scope: retain the exact expression authored by a quick verb, pin its combine base, render locked query readback, expose combine modes and APPLY, and provide one slot LAST QUERY recall.

## Reuse map

Every behavior below extends an existing owner. PR3 adds no evaluator, set algebra, command bus, selection aggregate, or UI vocabulary parallel.

| Concern | Existing owner | PR3 use |
| --- | --- | --- |
| Query carrier | `src/domain/selectionQuery.ts:SelectionExpression`, `SelectionQuery`, `Predicate`, `FaceProjection`, `EdgeProjection` | The retained draft stores the exact compiled expression without translation |
| Validation and evaluation | `src/domain/selectionQuery.ts:validateSelectionExpression`, `resolveSelectionExpression` | Command validation and live scene resolution remain here |
| Attribute vocabulary | `src/domain/selectionAspects.ts:attributeAspects`, `AspectDef` | Add human labels and exact value formatting to these descriptors; the panel does not name aspects |
| Relation vocabulary | `src/domain/selectionAspects.ts:relationDefs`, `RelationDef` | Add human labels here; relation readback uses the predicate plus descriptor |
| Projection vocabulary | `src/domain/selectionQuery.ts:FaceProjection`, `EdgeProjection`; labels in `src/domain/cubeTopology.ts:cubeFaceTopology`, `cubeEdgeTopology` | Readback exhaustively formats the serialized projection and reuses topology labels |
| Scope vocabulary | `src/domain/cubeOperations.ts:CubeScope` | FROM readback exhaustively formats the existing scope union |
| Verb provenance | `src/domain/selectionVerbs.ts:SelectionVerbDef`, `selectionVerbs` | The draft stores the authoring verb id; its visible label is resolved from this registry |
| Verb compilation | `src/domain/selectionVerbs.ts:evaluateSelectionVerb`; compilers in `src/domain/selectionCompile.ts` | A quick verb dispatches the same expression it already authors |
| Combine algebra | `src/domain/selection.ts:SelectionCombineMode`, `combineSelectionSets` | The draft stores one existing mode; APPLY uses this algebra through the command handler |
| Pointer combine grammar | `src/editor/affordances.ts:getCombineModeForVerb`, `getCombineModeForModifiers` | The first verb apply keeps the established modifier behavior |
| Selection snapshot shape | `src/domain/selection.ts:CubeSelectionToggleResult`; duplicate aliases in `src/interaction/snapshot.ts:SelectionSnapshot` and `src/state/selectionAssembly.ts:AssemblySnapshot` | Consolidate one canonical `SelectionSnapshot` before adding the pinned `against` field |
| Query command | `src/editor/commands.ts:createSelectQueryCommand`, `EditorCommand` variant `select-query` | Add optional captured base and verb provenance; callers without a base keep live one shot behavior |
| Query execution | `src/interaction/commands/selection.commands.ts:registerSelectionCommands` | Validate, resolve, combine, retain active selection, and write through the existing path using one effective base |
| Atomic selection write | `src/interaction/commands/registry.ts:CommandPorts.selection.applySelectionResult`; `src/state/actions/selectionActions.ts:createSelectionActions` | Land selection, active draft, and last query in one store transaction |
| Session state | `src/state/cubicellState.ts:CubicellEditorSession`, `createInitialEditorSession` | Own active and last query slots. Both remain outside persistence and document history |
| Session actions | `src/state/actions/editorActions.ts:createEditorActions`; declarations in `src/state/actions/types.ts:CubicellStateActions` | Change active combine and recall the last query without mutating the document selection |
| Session reference repair | `src/state/sessionReferences.ts:repairEditorSessionReferences` | Reconcile captured base members against the live working scene |
| Selector surface | `src/panels/SelectorPanel.tsx:SelectionTab` | Capture the base on verb press and mount the extracted draft surface |
| UI dispatch | `src/panels/editorCommandContext.ts:useEditorCommandDispatch` | Verb apply and APPLY dispatch the existing query command |
| UI primitives | `src/components/ui:Button`; existing panel readout and action row contracts | Combine, APPLY, and LAST QUERY reuse current controls and tokens |
| Styling | `src/panels/selector-panel.css` | Add only Selector specific readback and control layout |
| Feature flag | `src/config/cubicellConfig.ts:selectorPanelEnabled` | Remains true. PR3 adds no flag or alternate panel path |

## Locked mechanics

### Retention

The authored expression cannot be derived from the committed selection because resolution discards predicates, projections, scope, and verb provenance. Retention therefore lives in `CubicellEditorSession`:

- `selectionQueryDraft: SelectionQueryDraft | null`
- `lastSelectionQueryDraft: SelectionQueryDraft | null`

`SelectionQueryDraft` is a serializable domain value with exactly four fields:

- `expression: SelectionExpression`
- `combine: SelectionCombineMode`
- `against: SelectionSnapshot`
- `authoredByVerbId: SelectionVerbId | null`

Do not store a result copy. The existing selection aggregate owns the committed result. Match evidence belongs to PR4.

A quick verb keeps its PR2 behavior: it applies immediately. The successful command also retains the exact expression and captured base. Choosing another combine mode changes only `selectionQueryDraft.combine`; it does not select anything until APPLY.

A manual pick, toggle, Clear, raw marquee query, or raw layer query clears `selectionQueryDraft` and preserves `lastSelectionQueryDraft`. This produces the locked progressive clause behavior: raw selection shows no clauses, while LAST QUERY remains available. View, transport, panel, and motion focus actions preserve both slots. Resetting the editor session clears both.

### Pinned combine base

`against` is the complete selection snapshot immediately before the first verb command runs. It is copied into the command and retained draft. The pinned line displays its count as `Set N · pinned` and never reads the current result count.

`select-query` gains optional `against` and `authoredByVerbId` fields. Absence of `against` preserves the current one shot callers by using the live command context. The Selector always supplies it.

`registerSelectionCommands` computes one effective base, then uses it consistently for:

1. Cross subject combine validation.
2. `selected` and `selection-set` query scope context.
3. The left side of replace, add, subtract, and intersect.
4. Active member retention through `resolveActiveMember`.
5. The retained draft written through the aggregate port.

Reconcile a supplied snapshot through `reconcileSelection` against the live scene before these steps. Missing cubes cannot reappear through add or subtract. Replace still uses the base for contextual scopes and active member retention.

APPLY dispatches `createSelectQueryCommand` with the active draft expression, combine mode, captured `against`, and verb id. It never compiles, evaluates, or writes selection in the component. Repeated APPLY therefore resolves against current scene topology while combining against the same captured set. Refinement cannot self feed on its preceding result.

### LAST QUERY

PR3 stores one slot, not a list. A successful query with predicates or a part projection replaces `lastSelectionQueryDraft`. Invalid or rejected commands do not. Raw scope only queries do not.

LAST QUERY copies the last slot into the active slot and leaves the committed selection untouched. It does not apply automatically and does not capture the current manual selection as a new base. APPLY is the only replay action. The recalled draft keeps the original pinned base and combine mode.

Changing the active combine mode does not change LAST QUERY. A successful APPLY updates both slots to the applied draft. Recent query history and replay lists remain PR4 scope.

### Progressive readback

Add `selectionExpressionHasReadback` beside the carrier. It returns true when at least one query has a predicate or a `part` projection. Scope alone does not materialize readback. This makes a raw cube ids expression from marquee or layer selection clause free, while Along axis remains visible because its semantic projection carries query meaning without a predicate.

Add a pure `formatSelectionExpressionReadback` in new `src/domain/selectionReadback.ts`. It accepts only the expression and returns ordered structured rows. The React component renders rows and owns no query wording.

The row grammar is exhaustive:

- First branch: `SELECT`, then `FROM`, then zero or more `WHERE` and `AND` rows.
- Later expression branches begin with `OR`, followed by their own `FROM`, `WHERE`, and `AND` rows. No branch is flattened into another.
- A projection is the first condition. Predicates follow in serialized order.
- Default or `all` scope reads `ALL CUBES`. Id, single, selected, selection set, axis, plane, and pattern scopes include their exact serialized values.
- Face and edge ids use `cubeFaceTopology` and `cubeEdgeTopology` labels. Face perimeter and axis parallel preserve their semantic kind and value.
- Attribute names and value formatting come from `attributeAspects`. Multiple values read as `ANY OF`; `negate` and `tolerance` remain explicit.
- Relation names come from `relationDefs`. Junction classes, negation, and every serialized value remain explicit.
- Cube state formatting is deterministic and complete: visibility and size, then face and edge states grouped by identical state with every member id listed. It never falls back to object stringification or raw JSON.

Add display metadata to the descriptor owners rather than a UI label map:

- `AspectDef.label` and `AspectDef.formatValue` for size, cube state, face state, and edge state.
- `RelationDef.label` for exposed and junction relations.
- A domain subject descriptor for cube, face, and edge labels. Refactor `SelectorPanel.tsx` to consume it instead of extending its local subject maps.
- `selectionCombineModes` and labels beside `SelectionCombineMode`; derive the union from the ordered constant.

The author footer resolves `authoredByVerbId` through `selectionVerbs` and reads `Read only · authored by <verb label>`. No formatter or component contains verb specific prose.

## Build steps

### 1. Canonical selection snapshot and draft types

- `src/domain/selection.ts`: introduce canonical `SelectionSnapshot`; make `CubeSelectionToggleResult` an alias or migrate it. Replace the structurally identical interaction and assembly declarations.
- `src/domain/selectionQuery.ts`: add `SelectionQueryDraft`, `SelectionVerbId` linkage, `selectionExpressionHasReadback`, and a shared combine compatibility function used by both command validation and UI mode disabling.
- `src/domain/index.ts`: export only the public snapshot, draft, combine metadata, progressive check, readback types, and formatter.

Do the type consolidation before adding `against`. A fourth `{ selection, selectionSet }` declaration violates the repository DRY contract.

### 2. Descriptor driven readback

- `src/domain/selectionAspects.ts`: add labels and exact value formatters to existing descriptors.
- New `src/domain/selectionReadback.ts`: own the exhaustive scope, projection, predicate, expression branch, and row formatting.
- `src/domain/selectionVerbs.ts`: make verb ids a closed `SelectionVerbId` vocabulary and expose lookup by id for the provenance footer.

The formatter stays pure and has no React, state, command, or CSS dependency.

### 3. Extend the existing query command

- `src/editor/commands.ts:EditorCommand`, `createSelectQueryCommand`: accept an options object with optional `against` and `authoredByVerbId`; structured clone every retained value.
- `src/interaction/commands/selection.commands.ts:registerSelectionCommands`: derive the effective base once, share combine compatibility validation, resolve and combine from that base, construct a draft only when `selectionExpressionHasReadback` is true, and call the aggregate port once.
- `src/interaction/commands/registry.ts:CommandPorts.selection.applySelectionResult`: add the active draft argument.
- `src/app/useSynchronousEditorCommands.ts:useSynchronousEditorCommands`: thread the extended store action through the same port.

No new command kind is needed.

### 4. Session lifecycle

- `src/state/cubicellState.ts:CubicellEditorSession`, `createInitialEditorSession`: add both null slots.
- `src/state/actions/types.ts:CubicellStateActions`: extend `applySelectionResult`; add `setSelectionQueryCombine` and `recallLastSelectionQuery`.
- `src/state/actions/selectionActions.ts:createSelectionActions`: atomically land query selection and draft. A nonnull draft also becomes LAST QUERY. All ordinary selection writes clear only the active slot.
- `src/state/actions/editorActions.ts:createEditorActions`: update active combine without changing LAST QUERY; recall clones LAST QUERY into the active slot.
- `src/state/selectionCommit.ts:editorFromSnapshot` and other selection restoration seams: clear the active slot whenever a nonquery path replaces the committed selection. Preserve LAST QUERY.
- `src/state/sessionReferences.ts:repairEditorSessionReferences`: reconcile both captured bases against `getWorkingScene(workbench)` while preserving the exact expressions.

The editor session remains excluded from `src/state/cubicellStore.ts:partialize`. No storage version, wire schema, document history, or migration changes.

### 5. Selector draft surface

Create `src/panels/SelectorQueryDraft.tsx` with one connected `SelectorQueryDraft` component:

- LAST QUERY button, always present and disabled with no last slot.
- With no active draft, render only LAST QUERY. Do not mount readback, pinned base, combine, or APPLY DOM.
- Locked readback with accessible label `Query readback` and the formatter rows.
- Static `Read only` provenance footer. No input, contenteditable element, selector, disclosure, or clause button.
- `Combine base · Set N · pinned` from `draft.against`.
- Four existing Button controls for replace, add, subtract, and intersect. Selected mode uses `aria-pressed`. Shared domain compatibility disables invalid cross subject modes.
- APPLY dispatch through `useEditorCommandDispatch` with the active draft payload.

`src/panels/SelectorPanel.tsx:SelectionTab` remains the quick verb owner. On press it captures the live selection snapshot, derives the existing modifier combine mode, and dispatches one extended `select-query` command with the verb id. Mount `SelectorQueryDraft` below the verb row. A raw selection with no active draft renders no readback block.

Keep the disabled BUILD QUERY stub. Editing remains PR5.

### 6. Selector styling

Extend only `src/panels/selector-panel.css` with readback rows, query branch separation, provenance, pinned base, combine group, and APPLY layout. Reuse existing spacing, border, label, control, foreground, and selection accent tokens. Rows must wrap at the current right rail width without horizontal scrolling.

Do not edit `src/panels/panels.css`.

## Tests

### Domain readback

New `tests/selectionReadback.test.ts`:

1. Raw cube ids scope returns no progressive readback; any predicate or face or edge projection does.
2. The canonical `outerTopEdges` fixture formats `SELECT EDGES`, `FROM ALL CUBES`, `WHERE FACE PERIMETER TOP`, and `AND JUNCTION IS CONVEX` in order.
3. Every scope and projection variant includes its exact value.
4. Attribute readback covers one and many values, negate, tolerance, size, face state, edge state, and complete deterministic cube state.
5. Relation readback covers exposed, negated exposed, and all junction classes.
6. Multi query expressions retain branch order with explicit OR rows.
7. Formatter output contains no object coercion and no verb label literals.

### Command and pinned base

Extend `tests/selectQuery.command.test.ts`:

1. An omitted base preserves current one shot behavior.
2. A supplied base different from live selection owns contextual resolution, combine algebra, and active member retention.
3. Add, subtract, and intersect validate against the pinned subject. Cross subject modes reject before any write.
4. Deleted base members are reconciled and cannot reappear.
5. A readback eligible query calls the aggregate port once with selection and draft metadata. A raw scope only query passes a null active draft.
6. Rejected commands change neither selection nor query metadata.
7. Command creation clones expression and base inputs.

### Session lifecycle

New `tests/selectionQueryDraft.state.test.ts`:

1. Both slots initialize null and remain absent from the persisted slice.
2. Query selection, active draft, and last query arrive in one store emission.
3. Changing combine updates only the active draft.
4. A successful reapply updates LAST QUERY.
5. Manual select, toggle, Clear, raw query, pick mode conversion, and selection undo clear active readback and preserve LAST QUERY.
6. View, transport, tab, and motion actions preserve both slots.
7. Recall restores a cloned active draft without changing selection.
8. Session reset clears both; reference repair removes dead members from each pinned base.

### Selector UI

New `tests/selectorQueryDraft.test.tsx`:

1. Manual and raw marquee selections show the verb row and no `Query readback` region.
2. A verb applies immediately, captures the preapply set, and reveals the exact formatted expression and author label.
3. The header count follows the result while the pinned base count remains unchanged.
4. Same subject drafts enable all combine modes. Subject changing drafts leave only replace enabled.
5. Changing combine does not dispatch. APPLY dispatches the stored expression and original base through `createSelectQueryCommand`.
6. Repeated APPLY proves the result does not become the next base.
7. LAST QUERY is disabled initially, survives a manual pick, recalls without applying, and retains its original base.
8. Readback exposes no editable control and remains keyboard readable.

`tests/selectorPanel.test.tsx` is already 694 lines. Do not append PR3 coverage to it. Keep required command expectation edits count neutral and put the new behavior in the focused file above.

## Verification gate

All gates must pass from the repository root:

```text
pnpm lint
pnpm exec vitest run tests/selectionReadback.test.ts tests/selectQuery.command.test.ts tests/selectionQueryDraft.state.test.ts tests/selectorQueryDraft.test.tsx tests/selectorPanel.test.tsx
pnpm exec tsc -b --pretty false --force
pnpm test
pnpm build
git diff --check
```

Structural gates:

- `wc -l` proves every new or touched file is at most 700 lines. `SelectorPanel.tsx` remains orchestration sized; the draft surface stays extracted.
- Grep proves one `SelectionExpression` evaluator, one combine algebra, one `SelectionSnapshot` declaration, one query command path, and no UI aspect, relation, projection, scope, verb, or combine label maps.
- `selectorPanelEnabled` remains true.
- No persisted or wire type contains either draft slot.

Required live check before merge:

1. A raw canvas pick shows verbs and no clauses.
2. A quick verb applies immediately and reveals its exact locked readback.
3. A same subject query changed to add, subtract, and intersect reapplies against the displayed pinned set.
4. A subject changing query disables invalid combine modes.
5. A manual pick removes active readback; LAST QUERY restores it without changing the pick; APPLY then replays from the original base.
6. TAB pick mode cycling, MODIFY, Structure, State, transition, and camera controls remain unchanged.

## Out of scope

- Clause, scope, projection, predicate, tolerance, negate, or exemplar editing. PR5 owns editing.
- `+ CONDITION`, MATCH EXEMPLARS Any or All, typed pickers, blank query construction, text DSL, and raw JSON.
- Match count, match preview, SHOW ONLY, FOCUS, and recent query lists. PR4 owns result evidence and multi query history.
- Saved queries, persistence, wire encoding, document history, and live reactive queries.
- Inspector teardown, property editor movement, DELETE relocation, or motion inspector changes.
- Visible pick mode chrome or changes to TAB behavior.
- `panels.css`, panel docking, width memory, or shell layout changes.
- A second evaluator, combine implementation, selection aggregate, command kind, or query state service.
