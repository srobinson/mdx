---
title: Cubicell state display branch review
type: research
tags: [cubicell, code-review, motion, state-display, pr-172]
summary: Exact head review of PR 172 and its State display and Arrival Unit contracts
status: active
created: 2026-08-15
updated: 2026-08-15
project: cubicell
confidence: high
source: https://github.com/littleorgans/cubicell/pull/172
---

# Cubicell state display branch review

## Review boundary

PR: [littleorgans/cubicell#172](https://github.com/littleorgans/cubicell/pull/172), `feat(motion): toggle State display from the strip`

- Base: `bcbdd502f832647facd42dbd3b367e138b0cc6cc`
- Reviewed head: `2bac9d171ace4a615e23a06e7261c5d6cb55abf8`
- Remote state at final review: open, ready for review, base `main`, head branch `feat/toggle-state-display`
- Diff: 23 files, 479 additions, 112 deletions

The checkout was at the reviewed head. It had uncommitted edits in `src/domain/presentableSequence.ts` and `src/panels/motion/PieceMotionPanel.tsx`. I read committed code through the pinned Git object and ran reproduction tests in an archive of that object. The committed verdict excludes the local edits.

The local delta contains import ordering and expression formatting only. `git diff --numstat` reports 5 additions and 3 deletions in `presentableSequence.ts`, plus 2 additions and 2 deletions in `PieceMotionPanel.tsx`. It resolves none of the five committed head findings and is not part of PR 172.

## Overview

The branch adds `State.hidden?: true`. Hiding preserves the authored State, pose, camera view, sequence position, and transition settings. Playback derives a shorter take and leaves the authored score unchanged.

The branch also changes transition ownership. Each State after the first owns the transition on its left, called its inbound transition. The branch names the pair an Arrival Unit. If authored order is `A, B, C`, hiding `B` removes `B` and its inbound transition from the take. `C` keeps its own inbound transition, which now plays from `A` to `C`.

The main design is coherent. A shared presentation function now supplies scene sampling, duration, camera playback, and focused loop timing. Four behavioral gaps and one hard maintainability violation remain at the reviewed head.

## Key concepts and ownership

| Concept | Owner | Contract |
| --- | --- | --- |
| Authored display state | `src/domain/workbench.ts` | `hidden?: true` is durable. Absence means shown. `isStateHidden()` is the shared read rule. |
| Display mutation | `src/domain/structureOperations.ts` | `set-state-hidden` writes or removes the flag and refuses to hide the final visible sibling. |
| Arrival Unit movement | `src/domain/stateTransition.ts` | A nonfirst State carries its inbound transition when reordered. |
| Presented take | `src/domain/presentableSequence.ts` | Filters hidden keyframes, keeps each visible destination's authored inbound transition, and maps authored gaps to presented indexes. |
| Authored history | `src/domain/authoredInverse.ts` | Creates semantic inverses for display and sequence operations. |
| Playback consumers | `src/evaluation/pieceAt.ts`, `src/state/transportSelectors.ts`, `src/domain/pieceCameraTrack.ts` | Scene sampling, duration, and camera timing use the presented score. |
| Strip and inspector | `src/panels/motion/` | The strip keeps the full authored sequence visible for editing. It labels hidden, parked, and retargeted arrivals. |
| Persistence | `structureRecordCodec.ts`, `workbenchValidation/assets.ts` | Stores canonical `true` or absence and accepts existing records without the optional field. |

The authored structure currently admits a structure whose every State is hidden. One reducer guards against creating that condition, while deletion and hydration do not establish it as a structure invariant. Finding 2 is the observable result.

## How the take path works

1. The eye button sends `set-state-hidden` through the existing document edit command.
2. Authored operation validation checks the boolean payload. Local authoring resolves the owning structure.
3. `setStateHidden()` changes only the State record. The normal authored history path records the inverse and publishes the accepted edit for persistence.
4. `presentablePieceScore()` finds the structure's State transition track and calls `presentableStateTransitionTrack()`.
5. The presentation function removes hidden keyframes. For every remaining destination, it keeps the transition at the destination's original index minus one.
6. `resolvePieceSample()`, transport duration, camera compilation, and focused gap playback consume that derived score or its shared index mapping.
7. `PieceStateStrip` still renders authored States and transitions so hidden material remains selectable and editable.

No presentation result is written into the Workbench.

## Changed area map

| Area | Files | Purpose |
| --- | --- | --- |
| Domain model and presentation | `workbench.ts`, `presentableSequence.ts`, `stateTransition.ts`, `structureOperations.ts`, `workbenchOperations.ts`, `index.ts` | Display state, Arrival Unit rules, mutation, and exports. |
| Authored transaction | `authoredInverse.ts`, `authoredOperations.ts`, `localAuthoring.ts`, `authoredOperationValidation/document.ts` | Inverse, targeting, pose revision classification, and boundary validation. |
| Playback and camera | `pieceCameraTrack.ts`, `evaluation/pieceAt.ts`, `transportSelectors.ts` | Presented scene sample, duration, and camera track. |
| Persistence and hydration | `structureRecordCodec.ts`, `workbenchValidation/assets.ts` | Encode, decode, strict validation, and repair reading. |
| Motion UI | `EyeIcon.tsx`, `StructureSliceLayer.tsx`, `PieceMotionPanel.tsx`, `PieceStateStrip.tsx`, `motion.css`, `panels.css` | Shared eye icon, strip behavior, controller wiring, and styles. |
| Contract evidence | `tests/contracts/authored-operation.contract.test.ts` | Seven authored operation tests, including the normal hide and nonfirst move paths. |
| Delivery budget | `budgets/initial-delivery.json` | Rebased size ceilings. |

## Verified findings

### 1. Major: undo loses transition settings when a move crosses the first position

Location: `src/domain/stateTransition.ts:65`

Observation: `moveKeyframe()` retains only the moved State's inbound transition. Moving a nonfirst State to index zero discards that transition because the first State has no inbound slot. The inverse in `restoreKeyframePlacementInverse()` records placement only. Moving the State back inserts `defaultTransition`.

Impact: Undo restores State order but loses authored motion settings. In the focused reproduction, a 1337 ms inbound transition returned as the 1200 ms default after moving `B` before `A` and applying the real inverse.

Basis: Direct reducer and inverse execution against the exact head archive. The changed committed test moves `B` after `C`, so it never crosses index zero.

Corroboration: Correctness review.

Caveat: Moves that stay after index zero preserve the moved State's inbound transition. The loss occurs when a move crosses the first position.

Links: [move implementation](https://github.com/littleorgans/cubicell/blob/2bac9d171ace4a615e23a06e7261c5d6cb55abf8/src/domain/stateTransition.ts#L64-L76), [placement only inverse](https://github.com/littleorgans/cubicell/blob/2bac9d171ace4a615e23a06e7261c5d6cb55abf8/src/domain/authoredInverse.ts#L293-L319)

### 2. Major: deleting the sole visible State leaves an empty take

Location: `src/domain/structureOperations.ts:414`

Observation: `setStateHidden()` refuses to hide the final visible sibling. `deleteState()` delegates to sequence removal, whose guard counts total States. Hidden siblings satisfy that guard.

Impact: Starting with visible `A` and hidden `B`, deleting `A` leaves `B` hidden. `presentablePieceScore()` returns zero keyframes. The strip has no Start State, piece sampling returns no sample, and camera compilation has no presented State.

Basis: Direct document reducer and presentation execution against the exact head archive produced `{ hidden: true, keyframes: [] }`.

Corroboration: Correctness review.

Caveat: Deleting the only total State is already blocked. The failure requires at least one hidden sibling. Hydration also validates each flag without repairing the aggregate invariant.

Links: [hide guard and delete path](https://github.com/littleorgans/cubicell/blob/2bac9d171ace4a615e23a06e7261c5d6cb55abf8/src/domain/structureOperations.ts#L393-L437), [empty presentation path](https://github.com/littleorgans/cubicell/blob/2bac9d171ace4a615e23a06e7261c5d6cb55abf8/src/domain/presentableSequence.ts#L10-L27)

### 3. Major: retargeted transitions use hidden authored endpoints in the summary and inspector

Location: `src/panels/motion/PieceMotionPanel.tsx:129`

Observation: Playback keeps the destination owned transition and retargets it across hidden States. The strip labels the visible endpoints. `stripTransitions` and `TransitionInspector` still calculate topology from authored adjacency, `sequence[index]` to `sequence[index + 1]`.

Impact: For `A, hidden B, C`, playback applies `T_C` to `A` to `C`, while the summary and inspector analyze `B` to `C`. A focused topology produced authored primary class `change` and presented primary class `arrive`. The inspector can select the wrong class, report wrong member counts, and disable controls used by playback.

Basis: Source trace through the presentation function, strip, panel, inspector, and morph applicability rules. A focused exact head contract reproduced the class disagreement.

Corroboration: Contracts and history review, correctness review, and Comment Sicko review.

Caveat: The mismatch appears when hiding retargets an arrival and changes topology or class settings. Authored and presented pairs sometimes resolve to the same class.

Links: [summary endpoint derivation](https://github.com/littleorgans/cubicell/blob/2bac9d171ace4a615e23a06e7261c5d6cb55abf8/src/panels/motion/PieceMotionPanel.tsx#L126-L147), [inspector endpoint derivation](https://github.com/littleorgans/cubicell/blob/2bac9d171ace4a615e23a06e7261c5d6cb55abf8/src/panels/motion/MotionInspector.tsx#L280-L320), [retargeted strip label](https://github.com/littleorgans/cubicell/blob/2bac9d171ace4a615e23a06e7261c5d6cb55abf8/src/panels/motion/PieceStateStrip.tsx#L226-L255)

### 4. Major: the eye button cannot be activated from the keyboard

Location: `src/panels/motion/PieceStateStrip.tsx:179`

Observation: The eye button sits inside a focusable `role="option"`. The option's `onKeyDown` handles Enter and Space for bubbled events, calls `preventDefault()`, and selects the State. The button only stops click propagation.

Impact: A keyboard user who focuses `Hide A` and presses Enter selects `A` and emits no display toggle. Space follows the same parent branch. The PR's primary action is unavailable from the keyboard.

Basis: A real Chromium contract rendered the exact committed component. It received `{ selections: ["a"], toggles: [] }`.

Corroboration: Contracts and history review and correctness review.

Caveat: Pointer activation works. The parent key handler predates this branch and may affect the conditional Update button too. This branch adds the eye button to every State card.

Links: [option key handler](https://github.com/littleorgans/cubicell/blob/2bac9d171ace4a615e23a06e7261c5d6cb55abf8/src/panels/motion/PieceStateStrip.tsx#L66-L80), [nested eye button](https://github.com/littleorgans/cubicell/blob/2bac9d171ace4a615e23a06e7261c5d6cb55abf8/src/panels/motion/PieceStateStrip.tsx#L168-L203)

### 5. Minor: `PieceStateStrip` exceeds the hard function size limit

Location: `src/panels/motion/PieceStateStrip.tsx:52`

Observation: `PieceStateStrip` spans lines 52 through 286, 235 lines inclusive. It owns keyboard routing, hide guards, visible source lookup, focus state, and two card render loops.

Impact: The function exceeds the project's approximate 150 line threshold. The concentration already contributes to separate endpoint rules in the strip and inspector. Further State display work would increase reader load in the most divergent part of the branch.

Basis: Exact line count at the reviewed head and the mandatory repository instruction supplied for this review.

Corroboration: Comment Sicko review.

Caveat: This is maintainability debt and a direct project rule violation. It does not produce a runtime failure by itself.

Links: [function start](https://github.com/littleorgans/cubicell/blob/2bac9d171ace4a615e23a06e7261c5d6cb55abf8/src/panels/motion/PieceStateStrip.tsx#L50-L55), [function end](https://github.com/littleorgans/cubicell/blob/2bac9d171ace4a615e23a06e7261c5d6cb55abf8/src/panels/motion/PieceStateStrip.tsx#L282-L286)

## DRY verdict

Fail. The branch correctly reuses `EyeIcon` and centralizes take filtering in `presentableSequence.ts`. Presented endpoint derivation remains split among `presentablePieceScore()`, `PieceStateStrip.liveSourceIndex()`, `PieceMotionPanel`, and `TransitionInspector`. Those paths disagree in finding 3.

## Improvements that earn their cost

1. Add one domain resolver for an authored Arrival Unit. Return the authored destination, visible source, retained transition, presented index, segment, and parked or hidden status. Use it in the strip, loop window, summary, and inspector.
2. Make moves through index zero lossless. The existing full sequence restore operation is a simpler inverse than placement only restoration when transition ownership changes at the first position.
3. Enforce at least one visible State at the structure sequence owner. Apply the same normalization after hide, delete, and hydration so every consumer receives a valid take.
4. Split `PieceStateStrip` while extracting the Arrival Unit display calculation. Keep keyboard handling and each card renderer below the function threshold.

## Comment hygiene

The comment pass found four deleted comment blocks and one moved block. No block required restoration. The deleted gap ownership comment contradicted the new Arrival Unit rule. The implicit endpoint comment became false because the strip now names retargeted endpoints. The moved Update comment still documents a nonobvious event boundary.

The branch adds no suppression, no encoding workaround, and no comment that claims an unenforced invariant. Comment hygiene passes.

## Verification

All reproduction commands ran in `/tmp/cubicell-pr172-correctness.Yd1F9N`, an archive of the exact reviewed head with the repository's installed dependencies linked from the checkout. SHA256 values for the eight source files used by the reproductions matched `git show` output from the pinned head. No repository source file was written.

| Command | Exact result |
| --- | --- |
| `git diff --check bcbdd502f832647facd42dbd3b367e138b0cc6cc..2bac9d171ace4a615e23a06e7261c5d6cb55abf8` | Exit 0, no output. |
| `pnpm exec vitest run tests/contracts/authored-operation.contract.test.ts` | Exit 0. One file passed, 7 tests passed. |
| `pnpm exec vitest run tests/contracts/pr172-review.contract.test.ts` | Exit 1 as expected. Restored duration was 1200 ms; expected 1337 ms. |
| `pnpm exec vitest run tests/contracts/pr172-delete-visible.contract.test.ts` | Exit 1 as expected. Received `{ hidden: true, keyframes: [] }`; expected visible `B`. |
| `pnpm exec vitest run tests/contracts/pr172-retargeted-inspector.contract.test.ts` | Exit 1 as expected. Authored class was `change`; presented class was `arrive`. |
| `pnpm exec vitest run tests/contracts/pr172-keyboard.browser.contract.test.ts` | Exit 1 as expected in Chromium. Received selection `a` and no toggle. |
| `git diff --check 2bac9d171ace4a615e23a06e7261c5d6cb55abf8 -- src/domain/presentableSequence.ts src/panels/motion/PieceMotionPanel.tsx` | Exit 0, no output. The local delta is formatting only. |

The four failing review contracts are temporary reproductions. They are absent from PR 172. Their failed assertions prove the candidate behavior at the pinned head.

## CI limits

GitHub reports one successful check named `check` from the Delivery budget workflow. `[code]smith` is skipped. No visible PR check runs the TypeScript build, lint, unit suite, or Chromium contracts. The successful budget check does not cover the four behavioral failures.

## Merge verdict

Do not merge head `2bac9d171ace4a615e23a06e7261c5d6cb55abf8`. Four Major behavioral defects remain, including keyboard inaccessibility, lossy undo, an invalid empty take, and an editor versus playback topology mismatch. The branch also violates the function size rule. The local two file delta resolves none of them.
