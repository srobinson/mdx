---
title: Cubicell test recovery assessment
type: research
tags: [tests, recovery, vitest, architecture]
summary: Staged recovery plan for Cubicell's deleted Vitest suite without creating a second test system
status: active
created: 2026-08-14
updated: 2026-08-14
project: cubicell
confidence: high
---

# Cubicell test recovery assessment

## Verdict

Bring the tests back through the original Vitest system. Start with ten node unit files and their thirteen support files. Expand the same suite only after each tranche passes.

Avoid restoring all 272 paths as the first change. Git can recover the deleted bytes exactly, but `fa32189` changed production source in the same commit. A full first run would mix runner faults, assertion drift, UI failures, browser failures, and one known stale import.

The first tranche gives useful confidence in the domain model, face state ownership, authored operations, persistence codecs, pose integrity, selection commands, and score repair. It requires Vitest only. It does not require jsdom, Testing Library, or a new runner.

## What existed

Current HEAD is `fa32189908c18ef3457df0702fc030d7177a804f`. The recoverable parent is `042901d292f013424e11bfebcb2696144ad46f71`.

Commit `fa32189` deleted every path under `tests/` without renames or partial edits. The parent tree remains reachable in Git.

| Item | Parent state |
| --- | ---: |
| Paths under `tests/` | 272 |
| Deleted lines | 53,766 |
| Unit test files | 196 |
| Chromium test files | 17 |
| Benchmark files | 1 |
| Support files | 58 |
| Syntactic `test` or `it` declarations | 1,709 |
| Files with a jsdom directive | 52 |

The old system had one Vitest configuration in `vite.config.ts`:

- `unit` excluded `tests/**/*.browser.test.ts`.
- `chromium` ran the 17 browser files in sequence with a 30 second timeout.
- Both projects loaded `tests/setup.ts`.
- Browser tests launched Playwright against a Vite server through `tests/viteTestServer.mjs`.

The deletion also removed five package scripts and five direct development dependencies. `playwright` remained. `just test` and the gates documented in `WARROOM.md` still name the removed scripts.

The explorer classification found 141 durable core tests, 40 UI tests, 17 browser tests, 58 support files, and 16 stale or brittle files. This classification guides recovery order. It does not replace a test run.

## Why recovery is low risk

Recovery has a strong mechanical base:

- Git holds the exact parent tree and blobs.
- The package and Vite changes in `fa32189` isolate the removed runner wiring.
- A named import scan resolved 2,254 of 2,255 imports against current source.
- The one confirmed missing export is `clearStagedPayloads` in `imagePayloadPromotion.test.ts`.
- The old `tests/setup.ts` is safe in a node environment. DOM access is conditional.
- The existing config already models unit and Chromium work. No second runner is needed.
- Playwright remains a direct dependency.

Behavioral risk remains bounded and visible. `fa32189` changed payload assets, project asset hydration, authored inverses, media capability code, storage records, and cube rendering. Persistence and face media tests are canaries for those edits. They are not presumed green.

## Recommended staged plan

Use one branch and one commit per tranche. Keep runner recovery, test repairs, and production fixes in separate commits. Each green commit becomes a rollback point.

### Stage 0: pin the recovery base

```sh
git status --porcelain
git rev-parse HEAD
git switch -c chore/test-recovery
```

Proceed only when status is empty and HEAD is `fa32189908c18ef3457df0702fc030d7177a804f`.

### Stage 1: restore the first tranche

Restore the parent Vitest config and the exact test closure listed below:

```sh
git restore --source=042901d292f013424e11bfebcb2696144ad46f71 -- \
  vite.config.ts \
  tests/setup.ts \
  tests/domain.test.ts \
  tests/lattice.insert.test.ts \
  tests/lattice.delete.test.ts \
  tests/neighbors.test.ts \
  tests/cubeFaceStateOwner.test.ts \
  tests/authoredOperations.test.ts \
  tests/projectRecordCodecs.test.ts \
  tests/poseRevisionIntegrity.test.ts \
  tests/selection.commands.test.ts \
  tests/score.test.ts \
  tests/sceneTestHelpers.ts \
  tests/stateFixtures.ts \
  tests/stateTestHelpers.ts \
  tests/authoredOperationTestHelpers.ts \
  tests/poseRevisionTestHelpers.ts \
  tests/poseRevisionIntegrityFixtures.ts \
  tests/projectStorageFixtures.ts \
  tests/projectRecordHydrationSupport.ts \
  tests/recordCodecMetrics.ts \
  tests/interaction.testHelpers.ts \
  tests/interactionCoreTestSupport.ts \
  tests/cameraAuthorityTestSupport.ts
```

Restore only the Vitest dependency and the two unit scripts:

```sh
pnpm add -D 'vitest@^4.1.10'
pnpm pkg set \
  'scripts.test=vitest run tests --project unit' \
  'scripts.test:watch=vitest tests --project unit'
pnpm install --frozen-lockfile
```

This updates `package.json` and `pnpm-lock.yaml` from the current dependency graph. Do not restore the parent lockfile for this tranche. The parent lockfile also contains jsdom and Testing Library packages that this tranche does not use.

Verify the tranche:

```sh
pnpm test
pnpm exec tsc -b --pretty false --force
pnpm check
pnpm check:budget
git diff --check
git status --short
```

Commit runner recovery once these commands pass. If a test exposes a production bug, prove the failure in the recovery commit and fix the product in a separate commit.

## First tranche

The ten test files form a useful cross section:

| Test file | Confidence gained |
| --- | --- |
| `tests/domain.test.ts` | Scene, grid, cube operations, and shared model behavior |
| `tests/lattice.insert.test.ts` | Lattice insertion |
| `tests/lattice.delete.test.ts` | Lattice deletion |
| `tests/neighbors.test.ts` | Occupancy, neighbor slots, shell state, and style inheritance |
| `tests/cubeFaceStateOwner.test.ts` | Face state ownership near the current face media work |
| `tests/authoredOperations.test.ts` | Authoring validation, replay, and inverse behavior |
| `tests/projectRecordCodecs.test.ts` | Versioned record codecs and current persistence edits |
| `tests/poseRevisionIntegrity.test.ts` | Pose identity and quarantine behavior |
| `tests/selection.commands.test.ts` | The editor command registry path |
| `tests/score.test.ts` | Assembly order seeding and repair |

The thirteen support files are the closed local import set reported for these tests. `tests/setup.ts` registers the command kinds needed by `selection.commands.test.ts`. Its DOM shims only run when a document exists.

The expected first failures, if any, are in `authoredOperations.test.ts`, `projectRecordCodecs.test.ts`, and `poseRevisionIntegrity.test.ts`. Those tests cross the production modules changed by `fa32189`.

## Later tranches

### Tranche 2: remaining node tests

Restore the remaining node based durable tests in subsystem batches. Start with these current value canaries:

```text
tests/authoredOperationBoundaries.test.ts
tests/historyDiff.test.ts
tests/documentHistory.test.ts
tests/selectionQuery.test.ts
tests/selectionQuery.outerPerimeter.test.ts
tests/selectionQuery.relations.test.ts
tests/selectionQuery.similar.test.ts
tests/pieceMotionEvaluation.test.ts
tests/sceneMorph.test.ts
tests/committedStorePersistence.test.ts
tests/imageAssets.test.ts
```

For each batch, restore the named tests and their local `tests/` imports from `042901d`. Run `pnpm test`, forced TypeScript, `pnpm check`, and `pnpm check:budget` before adding the next batch.

Keep `tests/imagePayloadPromotion.test.ts` out. It imports the removed `clearStagedPayloads` export and needs a new assertion around current payload ownership.

### Tranche 3: jsdom and UI

Add the original UI dependencies to the same package and lockfile:

```sh
pnpm add -D \
  'jsdom@^29.1.1' \
  '@testing-library/dom@^10.4.1' \
  '@testing-library/react@^16.3.2' \
  '@testing-library/user-event@^14.6.1'
```

Begin with `startupIndicator.test.tsx`, `appBootstrap.test.tsx`, and `faceMediaField.test.tsx`, plus their local support closure. Then restore `panels.test.tsx` and `selectorPanel.test.tsx`. Add the five durable tests that use jsdom only after the node suite is green.

Run the focused files first. Then run the complete unit project and the build gates.

### Tranche 4: storage in real Chromium

The first browser batch should prove IndexedDB and recovery:

```text
tests/browserBlank.html
tests/viteTestServer.mjs
tests/viteTestServer.d.mts
tests/indexedDbBrowserLifecycle.ts
tests/indexedDbStorage.browser.test.ts
tests/committedStore.browser.test.ts
tests/saveRecovery.browser.test.ts
```

Add the original scripts:

```sh
pnpm pkg set \
  'scripts.test:browser=vitest run tests --project chromium' \
  'scripts.test:all=vitest run tests'
pnpm test:browser
pnpm test:all
pnpm check
pnpm check:budget
```

After storage is green, restore the rendering browser tests. Start with `stencilRendering.browser.test.ts`, `imageRendering.browser.test.ts`, `demandRendering.browser.test.ts`, and `incrementalScene.browser.test.ts`.

### Tranche 5: resolve the excluded tests

Review the 16 stale or brittle files individually. Rewrite tests that protect a current product contract. Delete tests that encode removed implementation details. Restore `sceneMorph.bench.ts` only when performance work needs it.

Leave `scripts/text-crispness-gate.mjs` deleted. Its parent version imports a driver that was already absent before `fa32189`.

## Options and tradeoffs

| Option | Benefit | Cost and risk | Verdict |
| --- | --- | --- | --- |
| Selective staged recovery | Early signal, small review units, clear failure ownership | Requires import closure work for each batch | Recommended |
| Full byte restore with staged execution | Fastest way to recover every historical file | Large first diff, stale tests return, build and unit faults arrive together | Keep as a fallback after the first tranche |
| Fresh suite | Small initial file count | Discards valuable coverage and risks a second config or runner | Reject |

A wholesale restore is mechanically safe because the Git objects are intact. It is a poor first validation step because the deletion commit also changed product behavior.

## Effort estimate

These estimates assume one engineer and no large production regression. No suite was run during this assessment.

| Work | Estimate |
| --- | ---: |
| First tranche and green unit gate | 2 to 4 hours |
| Remaining durable node tests | 1 to 2 days |
| jsdom and selected UI tests | 1 to 2 days |
| Storage browser tranche | Half a day to 1 day |
| Remaining valuable browser tests and stale test decisions | 1 to 2 days |

The first confidence gain fits within half a day. Recovering the valuable suite should take about 3 to 6 engineering days. A source regression can extend that range and deserves its own fix.

## Stop or rollback points

- Stop Stage 1 if the Vitest project cannot start. Repair the restored config before changing tests or production code.
- Stop after any red batch. Do not add the next batch until failures have a named owner and a passing proof.
- Stop before UI recovery unless the node unit suite and forced TypeScript pass.
- Stop before browser recovery unless the unit project, build checks, and delivery budget pass.
- Keep each tranche in one recovery commit. Roll back a committed tranche with `git revert <tranche-commit>`.
- Before the first commit, return the branch to its pinned base with `git restore --source=HEAD --staged --worktree -- package.json pnpm-lock.yaml vite.config.ts tests`.
- Do not carry skip markers as permanent recovery. A skip requires a named follow up and an explicit reason.

## Verification and open questions

This assessment verified the recoverable Git parent, the deleted suite inventory, the original Vitest configuration, the package changes, the first tranche import closure, and the one confirmed missing production export. The repository remained unchanged during the investigation.

The following questions require an implementation branch and real runs:

- Which first tranche assertions changed under the new payload and video restore behavior?
- Does the current lock resolve Vitest `4.1.10` after a selective add?
- Which of the 16 stale or brittle tests still protect a current product contract?
- Do the storage browser tests pass with the current Playwright cache and local Chromium?
- Which test gates belong in CI after the unit and browser projects are green?

The assessment itself does not claim that any restored test passes current HEAD. The recommended commands are unexecuted because this task prohibited repository, package, lockfile, configuration, and test edits.
