# Canvas PR 1 Review — Workbench Boundary and Pane Identity

**PR:** #207 · branch `refactor/canvas-workbench-boundary` · HEAD `b2d7de7`
**Scope audited:** Tasks 0, 1, 2 (PR 1 slice) of `docs/superpowers/plans/2026-07-05-canvas-repo-reset.md`
**Diff:** +456/-207 across 17 files
**Reviewer:** transport-matters:general:2:7.2 (adversarial, read-only)
**Date:** 2026-07-05

## Verdict: **PASS** — 0 blockers / 0 majors / 0 minors

Behavior-preserving. Every claim below was verified first-hand (tests run, boundary
guards probed with injected violations, typecheck executed, grep sweeps). Nothing
reaches beyond Tasks 0/1/2; no PR 2 (lab), PR 3 (store split), or PR 4 (dnd) bleed.

Evidence of green: `pnpm exec vitest run` over `sessionCanvasBoundary`,
`paneIdentity`, `paneRecords`, `canvasStore`, `registry` → **58 passed**.
`pnpm --filter @tm/canvas typecheck` → exit 0.

---

## Audit findings (five points, hardest first)

### 1. Boundary test enforces exactly two rules, both non-vacuous — PASS

`sessionCanvasBoundary.test.ts` asserts exactly `model !-> viewers` and
`persistence !-> viewers` via `boundaryViolations(fromRoot, VIEWERS_ROOT)`, reusing
`sourceFiles`/`importSpecifiers`/`resolveLocalSpecifier`/`isInside`/`relativeTo` from
`shell/src/testSupport/importGraph.ts`. No allow-list, no per-file exception, no
watered-down escape hatch.

- `CANVAS_SRC` (the resolver `srcRoot`) computes to `canvas/src`, matching
  `labBoundary.test.ts`'s `SRC_ROOT`. Alias forms (`session-canvas/...`, `@/`,
  `@tm/`) resolve correctly, so violations are caught regardless of import style.
- **Empirically proven to fail on a reintroduced violation.** Injected a throwaway
  `model/__probe_violation__.ts` importing `../viewers/registry`; the model rule
  failed with `session-canvas/model/__probe_violation__.ts:1: ../viewers/registry ->
  session-canvas/viewers/registry.tsx`. Same probe under `persistence/` failed the
  persistence rule identically. Both probes removed; tree clean.
- **`persistence !-> viewers` is a live guard, not vacuous.** `session-canvas/persistence`
  holds 7 real source files (`canvasPanePersistence.ts`, `canvasCacheStorage.ts`,
  `storageKeys.ts`, etc.) that the rule actually scans; it is wired, not merely
  `expect(true)`. Slightly stronger than the brief's "currently vacuous" assumption.
- `model` rule is non-vacuous: 22 model source files scanned, zero viewer targets.

### 2. Pane-identity output byte-identical — PASS

`model/paneIdentity.ts` reproduces every pre-move `registry.tsx` closure exactly:
`PICKER_PANE_ID`="session-picker"; prefixes `transcript:`/`subagent:`/`resource:`/
`exchange:` unchanged; `paneIdForRef`, `titleForRef`, `viewerIdForRef`,
`resourceRefTitle` logic identical (verified case-by-case against the diff).

Pinned in three places, giving full coverage plus a drift guard:
- `paneIdentity.test.ts` pins pane ids, titles, and viewer ids per kind (picker,
  transcript, subagent, resource db-ref, exchange, terminal, captured-run incl.
  same-provider distinct keys).
- `paneRecords.test.ts` pins the resource **locator** variant omitted above:
  `resource:path:/tmp/shot.png`, `resource:url:https://x.test/a/cat.png`, titles
  `shot.png`/`cat.png` (`locatorTail`).
- `viewers/registry.test.ts` "keeps registry identity aligned with the model" asserts,
  for every registered ref, `viewer.id === viewerIdForRef(ref)` **and**
  `viewer.paneId(ref) === paneIdForRef(ref)` **and** `viewer.title(ref) ===
  titleForRef(ref)`. This is the plan-mandated single-source-of-truth cross-check,
  extended to all three functions — the standalone switches cannot silently drift
  from the registry.

### 3. DRY — PASS

`paneIdentity.ts` imports `harnessLabel` and `locatorTail` from `./paneRecords` and
consumes them (`harnessLabel` in the captured-run title, `locatorTail` in
`resourceRefTitle`). Not re-declared, not copy-pasted. `paneRecords.ts` was not
modified — the helpers were already exported.

### 4. Import repoint completeness — PASS

- All `model -> viewers` imports removed. Grep of `model/**` for `viewers/` → none;
  the model boundary probe corroborates.
- Consumers repointed to `model/paneIdentity`: `canvasStore.ts`
  (`PICKER_PANE_ID`, `paneIdForRef`, `titleForRef`), `spawn.ts` (`paneIdForRef`,
  `viewerIdForRef`), `canvasStore.persistence.ts` (`titleForRef`),
  `components/PaneDock.tsx` (`titleForRef`).
- `components/CanvasSurface.tsx` correctly split: `PICKER_PANE_ID` from
  `model/paneIdentity`; `bodyDragForRef` + `renderPaneContent` stay on
  `viewers/registry`.
- `registry.tsx` keep-list intact: `defineViewer`, `registry`, `resolveViewer`,
  `bodyDragForRef`, `renderPaneContent`, `PaneShell` (and dead-but-retained
  `registerViewer`, per plan). It now consumes `paneIdForRef`/`titleForRef`/
  `resourceRefTitle` from the model; each registration wires `paneId: paneIdForRef`,
  `title: titleForRef`.
- Lab files (`lab/CanvasLabRoute.tsx`, `lab/canvasLabStore.ts`,
  `lab/canvasLabStore.persistence.test.ts`) touched **only** to repoint the moved
  imports. This is mandatory to keep the tree compiling in PR 1 (the lab is deleted
  in PR 2), not a scope breach.
- Zero stale imports of any moved symbol from `viewers/registry` anywhere in
  `canvas/src`.

### 5. OWNERSHIP.md (Task 0) present and docs-only — PASS

80-line markdown. `git diff --check` clean (no whitespace/conflict markers). Covers
all required content: definitions of workbench/model/viewers/interactions/launcher/
infrastructure, allowed + forbidden dependency direction, pane identity as model
vocabulary (`model/paneIdentity.ts`), registry renders content only, and the single
`/canvas` route with no lab surface. Documents the full forbidden set (incl.
`model -> React`/`Zustand`) even though the test enforces only the two PR-1-greenable
rules — consistent with the plan.

---

## Notes considered and dismissed (not findings)

- **Switches lack a throwing `default`** where old `resolveViewer` threw on unknown
  kinds. Not reachable: `persistence/canvasPanePersistence.ts` `readContentRefs`
  filters persisted refs through `isPaneContentRef` before any identity call
  (`paneRecordsFromRefs` -> `titleForRef`/`createPaneRecord`), so only valid in-union
  kinds hit the switches; TS exhaustiveness covers compile time. Behavior is
  preserved for every ref that can actually occur.
- **Lab files in the diff** — mandatory import repoints, addressed in point 4.

## Scope confirmation

All 17 changed files map to Tasks 0/1/2: OWNERSHIP.md; sessionCanvasBoundary.test.ts;
paneIdentity.ts + .test.ts; registry.tsx + registry.test.ts; canvasStore.ts/.test.ts/
.persistence.ts; spawn.ts; paneRecords.test.ts; CanvasSurface.tsx; PaneDock.tsx;
PlaceholderPane.test.tsx; three lab repoints. No store split, no lab retirement, no
dnd seam.
