# F1 Selector PR0 spec: panel shell

Date: 2026-07-18
Status: ready to build
Inputs: `f1-selector-ia-decision.md` (LOCKED model), `f1-selection-query-scout.md` section 4, `f1-selector-evolution.md` gap frames.
Scope: stand up the new Selector panel shell behind a flag. Additive. No inspector teardown, no verbs, no query builder.

## Reuse map

Every binding below is an existing owner. PR0 adds no parallel implementation of any of them.

| Concern | Existing owner | PR0 use |
| --- | --- | --- |
| Committed selection | `src/state/cubicellState.ts:CubicellEditorSession.selection`, `.selectionSet` | Header count and subject derivation read these two fields only |
| Deselect path | `src/editor/commands.ts:createSelectCommand(null, null)` through the `select` handler in `src/interaction/commands/selection.commands.ts:registerSelectionCommands` | CLEAR dispatches this; it clears selection and set in one command. No new clear action |
| Selected cube count | `src/domain:getSelectedCubeIds` | Subject count line where cube totals are needed |
| React dispatch | `src/panels/editorCommandContext.ts:useEditorCommandDispatch` | All panel dispatches |
| Tab primitive | `src/panels/PanelTabs.tsx:PanelTabs` | Renders SELECTION and MODIFY; same primitive the inspector tabs use |
| Session-sticky tab state | Pattern of `CubicellEditorSession.cubePanelTab` + `src/state/actions/editorActions.ts:setCubePanelTab` | New `selectorTab` field and `setSelectorTab` action, same shape. Editor session is excluded from `partialize` in `src/state/cubicellStore.ts`, so no storage version bump |
| Panel and dock chrome | `src/app/StudioShell.tsx:StudioShell` inspector slot, `src/app/DockablePanel.tsx:DockablePanel` | The flag swaps the content App passes into the existing `inspector` / `inspectorHeader` slots. No new dock machinery, panel id stays `inspector` |
| Panel mount point | `src/app/App.tsx` lines passing `inspector={<Inspector …/>}` and `inspectorHeader={<InspectorTabs/>}` | The only production wiring change |
| Feature flag pattern | `src/config/cubicellConfig.ts:seamSurfacesEnabled`, `editorPieceMotionWorkspaceEnabled` | New `selectorPanelEnabled = false`, same file, same doc-comment convention |
| MODIFY subject editors | `src/panels/CubeSection.tsx:CubeSection`, `src/panels/PartSection.tsx:FaceSection`, `:EdgeSection` | Mounted per subject, unchanged. All three are prop-free and store-connected, so they mount standalone today. Assessment below |
| PART / SET focus toggle | The edit-target `Segmented` block inside `src/panels/SelectionSection.tsx:SelectionSection` (`partEditTarget`, `setPartEditTarget`) | Extract into a shared `SelectionEditTargetToggle` component; SelectionSection and MODIFY both mount it (see step 4) |
| Keyboard catalogue | `src/editor/affordances.ts:editorCommandIds`, `editorCommandDefinitions`; `src/editor/keyboard/keymap.ts`; handler pattern of `pick-mode-cycle` in `src/interaction/commands/mode.commands.ts` | One new `selector-tab-toggle` command |
| Styling contracts | `src/panels/panels.css` classes (`cc-panel-tabs`, `cc-action-row`, `cc-panel-readout`), `src/components/ui:Button` | Header and count line reuse existing classes; new CSS only where no class exists |

### MODIFY mountability assessment (requested)

**Reuse, not placeholder.** `CubeSection`, `FaceSection`, and `EdgeSection` take no props, read the store directly, and dispatch through `useEditorCommandDispatch`. `Inspector.tsx` already mounts them one at a time per tab, which is exactly the delegation MODIFY needs. They carry both properties and operations (Snap home in CubeSection, Add neighbor in FaceSection), matching the MODIFY charter. No extraction PR is needed.

One nuance: today the rendered section follows `editor.pickMode` (the pick-next mode). MODIFY must render from `selection.kind` (the subject of what is actually selected), per the locked IA. PR0 branches on `selection.kind` and leaves `pickMode` untouched; the legacy inspector keeps its own behavior.

The only coupled piece is the PART / SET toggle, which lives inside `SelectionSection` bundled with Similar, Clear, and Delete. Mounting `SelectionSection` wholesale inside MODIFY would drag Similar and Clear into the wrong homes. Step 4 extracts the toggle as a shared component with zero behavior change to the legacy inspector.

## Build steps

### 1. Flag

`src/config/cubicellConfig.ts`: add `export const selectorPanelEnabled = false` with a doc comment naming PR0 and the live-toggle intent. Lands dark; flipping it is the manual test switch.

### 2. Session tab state

- `src/state/cubicellState.ts`: `export type SelectorTab = 'selection' | 'modify'`; add `selectorTab: SelectorTab` to `CubicellEditorSession`, initial value `'selection'`.
- `src/state/actions/types.ts` + `src/state/actions/editorActions.ts`: `setSelectorTab`, mirroring `setCubePanelTab`.
- Session only. Not persisted, not in history, not in the wire format.

### 3. Keyboard toggle command

- `src/editor/commands.ts`: add `{ kind: 'selector-tab-toggle' }` to `EditorCommand` plus `createSelectorTabToggleCommand()`.
- `src/interaction/commands/mode.commands.ts`: register the handler beside `pick-mode-cycle`; it flips `selectorTab` through the store port.
- `src/editor/affordances.ts`: add `editorCommandIds.selectorTabToggle` and its definition; bind in `src/editor/keyboard/keymap.ts`. Choose an unclaimed key; do not displace Tab (`pickModeCycle`).
- The command is valid regardless of the flag; only the panel that visualizes it is gated.

### 4. Extract `SelectionEditTargetToggle`

New small component in `src/panels/` owning the existing edit-target `Segmented` (reads `partEditTarget`, `selectionSet`; calls `setPartEditTarget`). `SelectionSection` renders it in place of its inline block, byte-for-byte identical UI. MODIFY mounts the same component. This is the one refactor PR0 performs, and it removes the only obstacle to clean reuse.

### 5. SelectorPanel

New `src/panels/SelectorPanel.tsx` exporting two components, mirroring the `Inspector` / `InspectorTabs` split so both StudioShell slots are served:

- **`SelectorPanelHeader`** (goes in the `inspectorHeader` slot, outside the scroll body):
  - Persistent readout `Set N`. N = `selectionSet?.items.length ?? (selection ? 1 : 0)`.
  - CLEAR button: dispatches `createSelectCommand(null, null)`; disabled at N = 0 (matches `state-empty-selection.png`).
  - `PanelTabs` with `['selection', 'modify']`, value `editor.selectorTab`, `onTabChange` calling `setSelectorTab`.
  - No SIMILAR, no DELETE in the header (locked IA: DELETE lives in MODIFY, SIMILAR in SELECTION from PR1).
- **`SelectorPanel`** (goes in the `inspector` slot): renders the active tab body.
  - **SELECTION tab (pre-clause state only):** count line, subject-worded: `"N cubes"` / `"N faces"` / `"N edges"` from `selection.kind`, or the empty copy `"Nothing selected — pick on the canvas or build a query."` Below it a disabled `BUILD QUERY` stub button (existing `Button`, `disabled`). No verbs, no clauses, no query builder.
  - **MODIFY tab:** polymorphic on `selection.kind`:
    - subject label line `MODIFY · CUBES` / `· FACES` / `· EDGES`;
    - `SelectionEditTargetToggle`;
    - `CubeSection` | `FaceSection` | `EdgeSection` per subject, unchanged;
    - empty selection renders `"Nothing selected"` and nothing else.

Component sizes stay small; the file should land well under 300 lines. Hard cap 700 per repo rule.

### 6. Empty-state tab defaults

Inside `SelectorPanel`, two rules only, then never touch the tab again (locked IA: selecting must never yank the user):

- On mount with `selection === null`: `setSelectorTab('selection')`.
- On the transition `selection: null -> non-null` while mounted: `setSelectorTab('modify')`.
- Every other change (subject flips, set growth, tab clicks, non-null to non-null) leaves `selectorTab` alone. Implement as one effect keyed on a `hadSelection` ref; no new state.

### 7. Flag wiring in App

`src/app/App.tsx`:

```tsx
inspector={selectorPanelEnabled ? <SelectorPanel /> : <Inspector onSelectSimilar={selectSimilar} />}
inspectorHeader={selectorPanelEnabled ? <SelectorPanelHeader /> : <InspectorTabs />}
```

`DockablePanel` `widthKey` for the inspector entry follows `selectorTab` when the flag is on (today it is `pickMode`); thread it from `StudioShell`'s existing prop or leave `pickMode` if threading touches more than it saves. Recommend leaving `pickMode` in PR0: width memory per tab is polish, not shell.

Nothing else in the legacy inspector path changes. `Inspector.tsx`, `SelectionSection.tsx` (minus the extraction), pick-mode tabs, and all existing tests stay as they are.

## Tests

New `tests/selectorPanel.test.tsx` (pattern: `tests/pieceMotionPanel.test.tsx`, which already mounts panel components against the store and command provider):

1. **Header count:** `Set 0` empty; `Set 1` single selection; `Set N` with a selection set.
2. **CLEAR:** dispatches the `select` command with null selection and null set; store ends with both cleared; disabled at `Set 0`.
3. **Tab switching and stickiness:** clicking MODIFY sets `selectorTab`; a subsequent selection change does not flip it back.
4. **Empty-state defaults:** mount with empty selection lands on SELECTION; a pick from empty lands on MODIFY; a pick while non-empty leaves the current tab.
5. **Keyboard toggle:** `selector-tab-toggle` command flips the tab both ways.
6. **SELECTION tab:** empty copy exact string; `"3 cubes"` wording with a 3-cube set; BUILD QUERY present and disabled.
7. **MODIFY polymorphism:** cube selection renders CubeSection content, face renders FaceSection, edge renders EdgeSection; subject label matches; empty selection renders the empty line.
8. **Edit-target toggle extraction:** existing `SelectionSection` behavior unchanged (existing suites must stay green) and the shared toggle works inside MODIFY.
9. **Flag off:** App renders the legacy `Inspector` / `InspectorTabs`; no Selector DOM present.

## Verification gate

From repo root, all must pass before the PR is complete:

```text
pnpm exec vitest run          # full suite, including the new selectorPanel tests
pnpm exec tsc -b --pretty false --force
```

- Flag-off is the shipping state; the default build must be pixel-identical to main (existing panel and inspector suites are the proxy, plus a manual flag-off smoke).
- Flag-on manual check before merge: flip `selectorPanelEnabled`, run the app, confirm header count tracks canvas picks live, CLEAR deselects, tabs stick, and MODIFY edits a cube, a face, and an edge through the reused sections. Per the live-UX-gate lesson, the PR merges flag-off; the live gate governs the later flip, not this landing.
- Grep gate: no new file re-declares selection state, combine grammar, or subject vocabulary; the only new store field is `selectorTab`.

## Out of scope (deferred by design)

- Verbs, clause readback, query builder, results tools: PR1+ per `f1-selector-evolution.md`, built inside the SELECTION tab of this shell.
- Inspector teardown and DELETE relocation into MODIFY: later migration PRs.
- `widthKey` per selector tab, panel width polish.
