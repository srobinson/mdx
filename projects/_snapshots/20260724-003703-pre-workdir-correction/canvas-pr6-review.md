# Canvas PR 6 Review — Launcher Model Split

**PR:** #212 · branch `refactor/canvas-launcher-split` · HEAD `05a59ab` (pre-PR main `23ffce8`)
**Scope audited:** Task 6 / "PR 6" slice of `docs/superpowers/plans/2026-07-05-canvas-repo-reset.md`
**Diff:** +1323/-1299 across 11 files
**Reviewer:** transport-matters:general:2:7.2 (adversarial, read-only, tree untouched)
**Date:** 2026-07-05

## Verdict: **CONDITIONAL** — 0 blockers / 1 major / 0 minors

The split is structurally faithful — every export preserved, cycle resolved, tests
split and green, no scope bleed — **except one line that changes launcher behavior**.
`commandModel.ts` (587 lines) is split into `navigation.ts` + `commandTypes.ts` +
`commandRows.ts` + `templateRows.ts` behind a 4-line `commandModel.ts` barrel. Task 6
required behavior preservation; one substantive divergence (M1) must be resolved before
that holds.

Evidence:
- `pnpm exec vitest run commandModel navigation commandRows templateRows sessionCanvasBoundary` → **72 passed** (5 files; all 6 boundary rules green).
- `pnpm --filter @tm/canvas typecheck` → exit 0 (barrel `export *` has no name collisions).

---

## Major

**M1 — Root flat-search now emits agent status rows it did not before (behavior change).**

`commandRows.ts` `buildFlatSearchRows` composes the agent rows with
`...buildAgentRows(inputs.templates, inputs.agentsStatus)`, but the pre-split
`commandModel.ts` `buildFlatSearchRows` used `...agentSpawnRows(inputs.templates)`.

`buildAgentRows(templates, status)` returns
`[...agentSpawnRows(templates), ...agentsStatusRows(status)]`, and
`agentsStatusRows` returns `[]` only for `status === "populated"`. Therefore:
- `agentsStatus === "populated"`: identical to pre-split (status rows empty). ✓
- `agentsStatus === "loading" | "error" | "empty"`: the root scope with a non-empty
  query (the Raycast-style flat search) now **additionally** renders the agent status
  rows — two "Loading specialists…" skeletons, or the "Couldn't load specialists" +
  "Retry" pair, or the empty-state row — none of which the pre-split flat search showed.

Reachable in the ordinary flow: on launcher open the runtime-templates fetch is
`loading`; a user who types immediately hits root flat-search while
`agentsStatus === "loading"`, so the skeleton rows appear. If the templates endpoint is
down, the "Retry" row persists inside cross-domain flat search.

The dedicated `agents` scope (`buildScopeRows("agents", …)` → `buildAgentRows(templates,
agentsStatus, param)`) correctly showed status rows before and after — this finding is
specifically about the `root` flat-search path.

**Not caught by tests.** `commandModel.testSupport.ts` `baseInputs` defaults
`agentsStatus: "populated"`, so the flat-search test ("a non-empty query flat-searches
agents and commands across domains", `commandRows.test.ts`) exercises only the
equivalent case. The one non-populated test uses scope `"agents"`, not root
flat-search. The divergent path is untested, which is why the suite stays green.

**Fix:** restore `...agentSpawnRows(inputs.templates)` in `buildFlatSearchRows` (it will
need `agentSpawnRows` exported/available from `templateRows.ts`). If the added status
rows are intentional, that is a deliberate behavior change that belongs outside a
behavior-preserving split and needs a flat-search test at non-populated status.

---

## Other audit points (all PASS)

### 1. Split fidelity (apart from M1) — PASS

- **Export-completeness**: every `export` from the pre-split `commandModel.ts`
  (`LAUNCHER_SCOPES`, `NavFrame` + nav helpers, `FetchStatus`, `deriveFetchStatus`,
  `LauncherCommand`/`Effect`/`RowAction`/`Lifecycle`/`Interaction`, `interactionFor`,
  `advanceGesture`, `CommandRow`, `templateSpawnHarness`, `recommendedSubtitle`,
  `buildAgentRows`, `buildCanvasRows`, `buildSettingsRows`, `buildSessionsRows`,
  `LAUNCHER_DOMAIN_COUNT`, `ScopeRowInputs`, `buildScopeRows`, `filterRows`,
  `firstSelectableValue`, `groupRows`) is present in the new files (set-diff empty).
- **Normalized logic-line diff** (pre vs the four new files, imports stripped) surfaces
  only benign changes beyond M1: `GROUP_*` promoted from module-private `const` to
  `export const` in `commandTypes.ts`, `ScopeRowInputs`/type imports restructured, and a
  `canvasGestureModifier: CanvasGestureModifier` → `ScopeRowInputs["canvasGestureModifier"]`
  annotation (same type). Row ids, labels, ordering, interaction maps
  (`SCOPE_INTERACTION`/`RUN_AND_CLOSE`/`COMMAND_INTERACTIONS`/`EFFECT_INTERACTIONS`),
  `DOMAINS` order, and command handlers are otherwise identical.

### 2. Cycle resolved — PASS

`workdirRows.ts` now imports `CommandRow` from `./commandTypes` (was `./commandModel`),
breaking the type-only `commandModel <-> workdirRows` cycle. The sibling import graph is
a DAG: `navigation` (leaf) ← `commandTypes` ← {`templateRows`, `workdirRows`};
`commandRows` aggregates {`commandTypes`, `navigation`, `templateRows`, `workdirRows`};
no source file imports the `commandModel` barrel, so no barrel cycle. No new cycle
introduced.

### 3. Test split real — PASS

`commandModel.test.ts` (previously the oversized ~719-line suite) is split into
`navigation.test.ts`, `commandRows.test.ts`, `templateRows.test.ts` (plus a shared
`commandModel.testSupport.ts` and a slim residual `commandModel.test.ts`). Test count
did not drop (pre `it()` count 53 → post 54; vitest runs 72 across the five files with
the boundary suite, 0 failures). Assertions are preserved; only import paths changed.
(Coverage gap for the M1 path noted above.)

### 4. No scope bleed + boundary — PASS

`commandModel.ts` is a thin 4-line barrel (`export *` over the four owners); all callers
(`CommandCenter.tsx`, `useLauncher*`, `useCommandCenter*`, `useRuntimeTemplates.ts`,
`useSessionHistory.ts`, `CanvasCommandDispatcher.ts`, tests) resolve unchanged through
it. The diff touches only `launcher/` files — no `components`/`workbench` behavior move,
no `api`/`stream`/`persistence` relocation (PR 7), no `session-canvas` rename (PR 8). All
six boundary rules still bite (`sessionCanvasBoundary` green).

---

## Verification note

Read-only throughout: `git show` for pre-split state, no branch switch, no temp files.
`git status` clean.
