---
title: Launcher Per-Spawn Worktree Targeting (⌘K → drill-in)
type: sessions
tags: [frontend, transport-matters, launcher, worktree, canvas, command-center]
summary: ⌘K worktree rows now give → a drill-into-spawn affordance that pins each spawn to that worktree, so agents in different worktrees coexist without toggling the single global default.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-25
updated: 2026-06-25
---

## Summary

Branch `feat/launcher-worktree-spawn-target` (commit `10266cd` after a review fix
round, originally `b941bca`, off main `7e122de`).

**Problem (audit-confirmed):** In the ⌘K WORKTREE scope, selecting a worktree only
re-rooted the single global `canvasStore.defaultWorktreeId`, and every agent spawn
(`agentSpawnRows` → `addCapturedRun`) inherited that one default. Running agents in
worktree A and B at once meant toggling the global default between spawns. `→`
(advance / "enter") on a concrete worktree row was a dead no-op.

**Fix (locked decision):** Each directly-selectable worktree row now carries a dual
gesture — `↵` (run) keeps `select-worktree` (re-root / set default, the quick
convenience), `→` drills into the Agents scope **pinned to that worktree**. Spawns
from that scope thread an optional `worktreeId` all the way to the existing
`CreateRunRequest.worktree_id`, so worktree A and B spawns coexist as isolated panes
and the global default is never mutated.

## Architecture Decisions

- **`CommandRow.advance?: RowAction` + `advanceGesture(row)`** — the launcher's row
  grammar previously derived BOTH gestures' lifecycles from one `action` via
  `interactionFor`. To let `↵` and `→` diverge on a single row, a row may now declare
  an optional `advance` override; `advanceGesture` returns the action+lifecycle the
  `→` gesture drives (override if present, else the primary action's `advance`
  lifecycle — fully backward compatible). This is the reusable seam, not a worktree
  special-case.
- **`useLauncherActionInterpreter.applyGesture`** refactored from `(row, lifecycle)`
  to `(row, action, lifecycle)` so it operates on the resolved action (primary for
  `↵`, override for `→`). `selectValue` (↵/click) passes `row.action`;
  `useLauncherInputKeys` (→) passes `advanceGesture(row)`.
- **Reuse, no parallel scope.** `→` descends into the EXISTING `agents` scope with the
  worktree id carried as the nav `param`. `buildScopeRows("agents", …, param)` threads
  `param` → `buildAgentRows` → `agentSpawnRows(templates, worktreeId)`, which stamps
  `worktreeId` onto each spawn command. No new scope, no parallel spawn path, no
  backend change.
- **`addCapturedRun(provider, runtimeTemplate, worktreeId?)`** — optional per-spawn
  override that wins over `get().defaultWorktreeId` but never writes it. The existing
  ref → `CapturedRunPane` → `createCapturedRun` → POST `worktreeId` path was already in
  place; only the stamping source changed.
- **DRY net-positive.** Extracted `worktreeRowActions(spaceId, worktreeId)` (shared by
  the single-worktree Space row and the Worktree sub-scope rows, previously duplicated
  `select-worktree` literals) and `spawnCommand(harness, worktreeId?, runtimeTemplate?)`
  (deduped the native/template spawn literals).

## Review Fix Round (10266cd)

Reviewer found 3 Major + 1 Minor, all valid:

- **Missing-worktree guard (Major).** `buildSpaceRows` attached the per-spawn drill-in
  to a single-worktree Space without checking `worktree.missing`, so a missing worktree
  could spawn a POST with an unavailable `worktree_id` the backend rejects. A single
  missing worktree is now inert (disabled, "Missing" trailing, no `action`/`advance`),
  matching the Worktree sub-scope. Test added asserting no spawnable target.
- **File size (Major).** `commandModel.ts` had crept to 701 (the linter reflowed
  `advanceGesture`'s signature). Extracted the cohesive Workdir/Worktree row builders
  (`worktreeSubtitle`, `worktreeTitle`, `worktreeRowActions`, `buildSpaceRows`,
  `buildWorktreeRows`, `GROUP_WORKDIR`) into `workdirRows.ts`. commandModel.ts → 593.
  Runtime dependency is one-way (commandModel → workdirRows); workdirRows imports row
  types from commandModel as `import type` (erased, no runtime cycle).
- **Gate correction.** `just ci` is not a real recipe. The gate is `just check` +
  `just test`; both re-run green (www + api 1760).
- **Em dashes (Minor).** Removed the two em dashes introduced in the new test code
  (commandModel.test.ts describe label, canvasStore.test.ts comment). Pre-existing em
  dashes in untouched describe titles were left as-is (not in scope).

## Performance Notes

N/A — pure command-model/state wiring, no render-path or bundle impact.

## Verification

- TDD: red (9 failing) → green. New tests:
  `commandModel.test.ts` (advanceGesture grammar, worktreeId threading, worktree-row
  advance affordance, agents-scope param pinning), `canvasStore.test.ts` (A/B coexist
  with distinct panes + default untouched; default fallback when no override),
  `CanvasSurface.test.tsx` (3-arg spawn dispatch).
- Gate: `just check` (biome + `tsc -b` + ruff/mypy) and `just test` green
  (www 1068, api 1760). `commandModel.ts` at 699 LOC (under the 700 hard limit).

## Deviations from Spec

None. Implemented the locked decision as written.

## Open Items

- **Breadcrumb nicety (minor):** descending into `agents` from a worktree shows the
  generic "Agents" scope header, not "Agents in &lt;worktree&gt;". Behavior is correct;
  a scoped header/label would improve legibility. Out of the locked scope; deferred.
