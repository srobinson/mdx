---
title: Cubicell test recovery assessment
type: research
tags: [tests, recovery, vitest, architecture, seams]
summary: A deliberately small contract suite for Cubicell that protects seven architectural seams without restoring the deleted test backlog
status: active
created: 2026-08-14
updated: 2026-08-14
project: cubicell
confidence: high
---

# Cubicell test recovery assessment

## Decision

Do not recover the deleted suite as a backlog.

Create seven permanent contract files. Five belong in the fast local gate. Two belong in a separate real Chromium gate.

Commit `042901d292f013424e11bfebcb2696144ad46f71` contains useful cases, not a suite shape to restore. Its 272 paths and 1,709 test declarations imposed a permanent cost that slowed development to a halt.

The compiler already protects much of the local model. The missing protection sits at behavioural boundaries where several owners must agree at runtime. A failure there can lose authored work, display a different scene from the one controls act on, leave stale GPU data, or break the visible media loop.

## Permanent fast local gate

| Contract file | Seam | Broken implementation it catches | Old cases worth harvesting |
| --- | --- | --- | --- |
| `authored-operation.contract.test.ts` | Validation, domain application, inverse derivation, history, and session repair through `reduceAuthoredOperationState` | An incomplete inverse, unstable identity during sequence edits, or replay producing a different document | The replay, stable keyframe identity, and semantic inverse cases from `authoredOperations.test.ts` |
| `interaction-dispatch.contract.test.ts` | Real interaction core, command registry, and store across document and view lanes | A command reports success before a rejected edit, document mutation becomes asynchronous, or view coalescing loses the final command | Synchronous dispatch order from `interaction.bus.test.ts` and one real registered selection command from `selection.commands.test.ts` |
| `staged-scene-framing.contract.test.ts` | Evaluation, transport, staged scene reading, and framing | Rendering samples a staged scene while reset or focus reads the authored scene, or framing includes presence zero cells | One interpolated transition from `stagedScene.test.ts` and the two staged framing cases from `framingStagedScene.test.tsx`, rewritten without a React mount |
| `incremental-scene-equivalence.contract.test.ts` | Incremental scene ownership against a fresh full rebuild | A stale slot survives migration or removal, or a journal gap patches the wrong base | One contiguous edit equivalence case and one discontinuity reset case from `incrementalCubeSceneOwner.test.ts` |
| `project-durability.contract.test.ts` | Projection, payload storage, promotion, hydration, reopen, retry, and competing work | A payload disappears after reopen, stale work overwrites committed work, or retry recreates consumed pending work | Isolation and idempotent receipt cases from `committedStorePersistence.test.ts`, plus current payload assertions harvested from `imageAssets.test.ts` |

### Fast gate budget

The local gate has a hard cap of five contract files and 20 focused cases.

- Warm wall time must remain at or below 3 seconds on the development machine.
- Cold wall time must remain at or below 8 seconds, excluding dependency installation.
- Do not use jsdom, Testing Library, Playwright, screenshots, network access, fake timers, or module mocks.
- Use real domain functions, the real command registry, real Three data, and `createMemoryProjectStorage`.
- A proposed sixth local file must replace an existing contract or prove an escaped production regression that none of the five contracts can catch.

## Optional real Chromium gate

These files are permanent, but they do not run on every local edit.

| Contract file | Seam | Broken implementation it catches | Old cases worth harvesting |
| --- | --- | --- | --- |
| `indexeddb-recovery.browser.contract.test.ts` | Atomic IndexedDB commit, recovery, reopen, and damaged record preflight in real Chromium | Transaction abort partially commits, reopen loses recovery state, or corrupt bytes cross hydration | Quota rollback from `indexedDbStorage.browser.test.ts` and pending recovery plus damaged pose hash from `saveRecovery.browser.test.ts` |
| `face-media-loop.browser.contract.test.ts` | Import through the real panel, face assignment, canvas pixels, thumbnail parity, and render idle | Payload staging succeeds while authoring, rendering, thumbnail generation, or scheduler shutdown fails | The imported image loop and idle draw assertion from `textContent.browser.test.ts`; keep image only |

### Browser gate budget

- Hard cap of two files and six cases.
- Cold wall time must remain at or below 90 seconds, including one shared Vite server and Chromium process.
- Run on demand before changes to persistence, media, renderer, thumbnail, or scheduler owners.
- Run in CI before merge when CI exists.
- Assert state, pixels, reopen results, and idle behaviour.
- Do not keep screenshots, broad pixel baselines, GPU timing thresholds, or implementation call counts.

## What stays deleted

- Broad domain unit coverage for lattice, neighbors, selection queries, score variants, and every command payload.
- Component snapshots and jsdom rendering tests.
- One test per record codec or schema version.
- Separate browser files for image, text, stencil, thumbnails, demand rendering, and incremental rendering.
- Cache, queue, hook, and private helper assertions.
- Performance microtests and historical frame rate thresholds.
- Old support files restored merely because another old test imports them.

Pure typed modules receive a focused regression test only after a real escaped bug. The seven contracts own cross boundary behaviour. Everything else relies on types, direct code reading, delivery budgets, and deliberate feature verification.

## Adoption rule

Harvest assertions, not files.

Each contract begins with the named historical cases, adapted to current source at `fa32189908c18ef3457df0702fc030d7177a804f`. Delete every assertion that observes a private implementation detail. Prefer real implementations over mocks.

Do not expand the suite after the seven seams pass. A new test must satisfy all of these conditions:

1. It protects a cross owner contract.
2. A plausible broken implementation still compiles.
3. Existing contracts would miss the failure.
4. The assertion observes a user visible result, durable state, or ownership invariant.
5. The suite remains within its file, case, and runtime budgets.

If the budget is exceeded, consolidate or remove tests before adding another. Feature work must not inherit an unbounded test tax.

## Recovery approach

Build the contract suite against the current code. Use the deleted tests only as evidence and source material.

The first implementation slice should restore Vitest and implement one fast contract, preferably `project-durability.contract.test.ts`, because state and persistence form the most porous current boundary and authored data loss is the costliest failure.

Use one runner and two explicit commands:

```json
{
  "test": "vitest run tests/contracts --project unit",
  "test:browser": "vitest run tests/contracts --project chromium"
}
```

Do not restore the old lockfile. Add Vitest to the current dependency graph. Add no DOM testing dependency unless one of the two Chromium contracts proves it is required.

## Verification boundary

This assessment is read only with respect to the repository. It does not claim that any harvested assertion passes current HEAD. Runtime budgets are acceptance limits for implementation, not measurements from an existing suite.

The repository remained clean at `fa32189908c18ef3457df0702fc030d7177a804f` during the investigation.
