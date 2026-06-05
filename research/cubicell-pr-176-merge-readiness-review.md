---
title: Cubicell PR 176 merge readiness review
type: research
tags:
  - cubicell
  - code-review
  - motion
  - state-composer
summary: Exact commit review of PR 176 and the verified local repair candidate that resolves every retained finding.
status: complete
created: 2026-08-16
updated: 2026-08-16
---

# Cubicell PR 176 merge readiness review

## Decision

Withhold merge approval at `242d2e6476f81c3e0954b158a782c439b9380de5`.

The implementation is compact and largely well factored. Two reproduced correctness defects block approval. Four smaller findings should also be corrected while this focused surface is open.

## Boundary

| Item | Value |
| --- | --- |
| Pull request | [PR 176](https://github.com/littleorgans/cubicell/pull/176) |
| Base | `a7623e018fe04677000283b929042c188ad779c7` |
| Head | `242d2e6476f81c3e0954b158a782c439b9380de5` |
| Delta | 27 files, 809 insertions, 329 deletions |
| Repository state | Pristine before and after review |
| GitHub state | Open, mergeable, clean, exact head checks green |

## Local repair candidate

The working tree now contains focused repairs for every retained finding. The remote pull request still points to the reviewed head, so its merge decision remains unchanged until these edits are committed, pushed, and checked by CI.

The local candidate is ready to commit:

- Stale State creation placements reconcile to the final endpoint and retain the composer.
- The first empty State preserves the detached working pose and passes semantic inverse restoration.
- Authored operations use schema 6. The durable outbox carrier uses schema 5. Previous versions are rejected.
- The Current scene preview follows camera changes and supplies the same view used by creation.
- Successful keyboard creation focuses the selected State option.
- Seed previews are decorative inside their labelled buttons.
- Stale explanatory comments were removed.

Local verification passed on 2026-08-16:

| Check | Result |
| --- | --- |
| `git diff --check` | Passed |
| `pnpm exec oxfmt --check .` | Passed, 671 files |
| `pnpm exec oxlint .` | Passed |
| `pnpm test` | Passed, 7 files and 25 cases |
| `pnpm test:browser` | Passed, 3 files and 4 Chromium cases |
| `pnpm check:budget` | Passed |
| Runtime dependency cycles | None |
| Motion structural duplicate clusters | None at the review threshold |
| Live Chromium | Preview refresh, keyboard focus, stale placement recovery, permanent Add State endpoint, and compact layout passed without page or console errors |

## Merge blockers

### 1. Undo can leave an invalid creation placement that fails silently

Severity: high.

The focus controller invalidates stale transition gaps only. A `state-create` focus can retain an `afterKeyframeId` after undo removes that keyframe. The composer then dispatches an operation that the domain rejects, selects the minted State ID, and closes as though creation succeeded.

Reproduced in Chromium:

1. Create three States and open `New` after the selected middle State.
2. Undo until that source State disappears while the composer remains open.
3. The placement control has no selected option. The marker points after a different State.
4. Activate `Current scene`.
5. The composer closes. The timeline count does not change. No error is shown.

Sources:

- [`motionFocusController.ts:43`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/panels/motion/motionFocusController.ts#L43-L46)
- [`PieceStateStrip.tsx:74`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/panels/motion/PieceStateStrip.tsx#L74-L76)
- [`MotionInspector.tsx:198`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/panels/motion/MotionInspector.tsx#L198-L217)

Smallest correction: normalize `state-create` focus when its referenced keyframe disappears. Derive the marker from `placement.afterKeyframeId`. Leave creation mode only after the document operation applies. Add a browser regression for undo while the composer is open.

### 2. The first empty State operation is not invertible

Severity: medium, merge blocking contract violation.

Detached `create-empty-state` replaces `workingPose` with the empty pose. Its derived inverse deletes the newly created Structure. That inverse keeps the empty working pose, so the original detached scene is lost.

Executable proof applied the new operation, derived its real inverse, applied that inverse, and compared the restored `workingPose.cells` with the original. The assertion failed with `[]` received and the original cube expected.

Current session undo remains healthy because it restores a Workbench snapshot. The authored operation contract still promises an inverse and persists it.

Sources:

- [`structureOperations.ts:235`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/domain/structureOperations.ts#L235-L249)
- [`authoredInverse.ts:41`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/domain/authoredInverse.ts#L41-L47)

Smallest correction: preserve the detached working pose during Structure creation, then let the existing `restore-state` operation load the new empty State. Add a semantic inverse assertion beside the authored operation contract.

## Additional findings

### 3. Schema version 5 names incompatible authored operation shapes

Severity: medium.

This change adds `create-empty-state` and makes `placement` required for two existing operation kinds. `authoredOperationSchemaVersion` remains 5. A stored prechange version 5 operation and a new version 5 operation now have incompatible bodies.

Repository history bumped this constant when document operation kinds changed. Commit `49dcd1a86` moved authored operations from 4 to 5 and the durable outbox carrier from 3 to 4. The same protocol discipline applies here.

Sources:

- [`authoredOperations.ts:6`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/domain/authoredOperations.ts#L6)
- [`outboxCommitRecordCodec.ts:6`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/persistence/recordCodecs/outboxCommitRecordCodec.ts#L6)
- [`document.ts:36`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/state/authoredOperationValidation/document.ts#L36-L73)

Smallest correction: bump the authored operation version to 6 and the outbox carrier version to 5. No migration or compatibility reader is needed during pre release development.

### 4. The Current scene preview stops tracking the camera

Severity: medium.

The composer reads the camera snapshot during React render. Camera rotation does not rerender this component. The preview can therefore show an old view while activation captures the new view.

Chromium proof kept the composer open and activated `Rotate right`. The canvas SHA 256 changed from `76b961e0...4946` to `1b821e9f...767c`. The Current scene image source remained identical. The create handler reads the camera again, so the resulting State uses a view different from the preview.

Source: [`MotionInspector.tsx:187`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/panels/motion/MotionInspector.tsx#L187-L204)

Smallest correction: subscribe the preview to the owned camera state, or freeze the preview and capture to one explicit snapshot when the composer opens. Add a browser case that rotates the camera with the composer open.

### 5. Successful keyboard creation loses focus

Severity: medium accessibility defect.

The composer correctly focuses its first seed. Activating that button with Enter replaces the composer with the State inspector and removes the focused node. `document.activeElement` becomes `BODY`.

Smallest correction: move focus to the new State card or the first applicable State inspector control after successful creation. Cover the full open, activate, return sequence in Chromium.

Source: [`MotionInspector.tsx:194`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/panels/motion/MotionInspector.tsx#L194-L216)

### 6. Seed thumbnails duplicate accessible button names

Severity: low accessibility defect.

Chromium exposes `Current scene Current scene`, `State 8 State 8`, and `Empty Empty`. Each image alternative repeats the visible button label.

Smallest correction: mark the preview wrapper decorative in this button context, while preserving informative alternatives in standalone thumbnail contexts.

Source: [`MotionInspector.tsx:287`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/panels/motion/MotionInspector.tsx#L287-L291)

## Cleanliness and DRY assessment

Positive evidence:

- No runtime dependency cycles.
- No structural duplicate cluster in `src/panels/motion` at the review threshold.
- The State creation factories share one field builder and one domain `createState` path.
- The old append helper is absent from source callers.
- Every changed file is below 700 lines. The largest changed file is 618 lines.
- Changed functions stay below the 150 line threshold. `PieceMotionPanel` is the largest at 144 lines.
- No lint, TypeScript, or formatter suppression was added.
- `git diff --check`, format, lint, governance, tests, build, and delivery budgets pass.

Comment cleanup remains. Three State factory comments are false or stale at [`stateCapture.ts:16`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/panels/stateCapture.ts#L16-L16), [`stateCapture.ts:32`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/panels/stateCapture.ts#L32-L32), and [`stateCapture.ts:62`](https://github.com/littleorgans/cubicell/blob/242d2e6476f81c3e0954b158a782c439b9380de5/src/panels/stateCapture.ts#L62-L62). Deletion is the smallest correction. Five additional changed comments narrate visible code and can also be removed.

The proposed CSS token finding was rejected. The stylesheet already owns exact pixel geometry for component dimensions. The candidate showed no current defect and no duplicated semantic constant.

## Verification record

| Check | Result |
| --- | --- |
| `git diff --check` | Passed |
| `pnpm exec oxfmt --check .` | Passed, 670 files |
| `pnpm exec oxlint .` | Passed |
| `pnpm test` | Passed, 7 files and 25 cases |
| `pnpm test:browser` | Passed locally, 2 files and 3 Chromium cases |
| `pnpm test:governance` | Passed |
| `pnpm build` | Passed |
| `pnpm check:budget` | Passed |
| Exact head GitHub check | Passed |
| Live Chromium | Core flows passed at 874 by 652 and 720 by 600. No document overflow. Browser hooks captured no page or console errors. Four findings reproduced. |
| Direct inverse proof | Failed as expected, confirming finding 2 |

Existing tests and CI are green. They do not cover the reproduced focus, inverse, camera preview, or keyboard focus paths.

The Vite development server logged repeated `ResizeObserver loop completed with undelivered notifications` messages during compact viewport work. No base branch comparison was run for that signal, so this review leaves it unclassified.

## Review method

The review pinned the exact head and base, surveyed ownership before inspection, used independent domain, frontend, and comment lenses, then verified every retained finding in current source or live Chromium. Historical review context supplied regression questions only. All current claims were refreshed against this head.

The repository was not edited.
