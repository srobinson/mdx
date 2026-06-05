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
| `authored-operation.contract.test.ts` | Validation, domain application, inverse derivation, and history through `reduceAuthoredOperationState` | An incomplete inverse, unstable identity during sequence edits, or replay producing a different document | Replay determinism, stable keyframe identity, and semantic inverse restoration |
| `interaction-dispatch.contract.test.ts` | Real interaction core, command registry, and store across document and view lanes | A command reports success before a rejected edit, document mutation becomes asynchronous, or view coalescing loses the final command | Synchronous dispatch order from `interaction.bus.test.ts` and one real registered selection command from `selection.commands.test.ts` |
| `staged-scene-framing.contract.test.ts` | Evaluation, transport, staged scene reading, and framing | Rendering samples a staged scene while reset or focus reads the authored scene, or framing includes presence zero cells | Authored identity, sampled playback geometry, and comparison visibility before selection framing |
| `incremental-scene-equivalence.contract.test.ts` | Incremental scene ownership against a fresh full rebuild | A stale slot survives addition, face mutation, or removal | One contiguous add, update, and remove lifecycle compared with canonical full resolution after every step |
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
| `indexeddb-recovery.browser.contract.test.ts` | IndexedDB checkpoint persistence, transaction abort recovery, retry, and reopen in real Chromium | An interrupted checkpoint becomes visible, retry loses the changed state, or recovery metadata survives after success | Fresh user Project state reopen and one injected abort followed by retry and another reopen |
| `face-media-loop.browser.contract.test.ts` | Media capability import, image asset authoring, face assignment, full page reload, IndexedDB reopen, and production media atlas rebuild in real Chromium | Payload staging succeeds while durable metadata, face content, reopened bytes, atlas assignment, or media pixels fail | One real PNG loop from import through a written atlas slot after the JavaScript module cache is gone |

### Browser gate budget

- Hard cap of two files and six cases.
- Cold wall time must remain at or below 90 seconds, including the real Vite and Chromium lifecycles.
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

## Implemented recovery

The suite is implemented on `feat/contract-tests` from base `fa32189908c18ef3457df0702fc030d7177a804f`. Deleted tests were used as source material. No old test file or support tree was restored.

The current suite contains:

- Five local files with 13 cases.
- Two real Chromium files with three cases.
- One shared browser lifecycle helper in `tests/contracts/browserContract.ts`.
- One command registry setup file.

`pnpm test` runs governance and the local project. `pnpm test:browser` runs governance and the Chromium project. Both commands disable the Vitest cache, use one worker, measure the complete gate, and stop a run that exceeds its hard budget.

`tests/contracts/governance.json` is the policy source. `scripts/check-test-governance.mjs` enforces the exact file allowlist, group case caps, the 700 line file limit, forbidden imports, forbidden Vitest modifiers, mocks, spies, fake timers, stubs, and snapshots. `scripts/run-contract-tests.mjs` enforces the wall clock budgets. `pnpm check` includes static governance. Pull request CI runs both contract commands before the existing delivery budget.

Vitest was added to the current dependency graph. No DOM testing package was added. The Chromium contracts use the existing Playwright dependency.

## Measured verification

Measured on 2026-08-14:

- `pnpm test`: 13 of 13 cases passed. The complete gate took 2.287 seconds against the 8 second hard limit.
- `pnpm test:browser`: three of three cases passed. The complete gate took 4.816 seconds against the 90 second hard limit.
- `pnpm check`: passed.
- `pnpm build`: passed.
- `pnpm check:budget`: passed.
- `git diff --check`: passed.

Governance received two controlled negative proofs. A temporary undeclared contract failed with `LOCAL_UNDECLARED` and `UNDECLARED_FILE`. A temporary nested contract failed with `UNDECLARED_DIRECTORY`. Removing each probe restored the green result of five local files with 13 cases and two browser files with three cases.

The two browser contracts also passed focused primary pane reruns. After independent review, the face media contract was strengthened with a full page reload and production media atlas assertion. The corrected contract passed twice consecutively in 2.23 and 2.18 seconds.
