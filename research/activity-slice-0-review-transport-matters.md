---
title: Activity Slice 0 Review for Transport Matters
type: research
tags: [transport-matters, activity, code-review, xstate, import-boundary]
summary: Reviewed the new @tm/activity package and found two status machine fidelity defects around failed tool records.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-03
updated: 2026-07-03
---

## Executive Summary

Activity slice 0 adds the first TypeScript product plane context package, `@tm/activity`, plus architectural standards and an import boundary gate. The package shape, domain purity, package export surface, XState API usage, architecture documentation, and import boundary mechanism are mostly aligned with the spec, but the XState status machine mishandles failed tool records in two load bearing paths.

## Project Metadata

- Language: TypeScript for the new product plane package, Python remains the capture plane.
- Package: `packages/activity`, published in workspace as private `@tm/activity`.
- Key dependencies: `xstate` 5.32.4, `@xstate/graph` 3.0.4, TypeScript 5.9.3, Vitest 4.1.4.
- Build and verification: `packages/activity/package.json` exposes `typecheck`; root `just check` adds `pnpm --filter @tm/activity typecheck`; shell Vitest config includes activity tests.
- Branch and commit reviewed: `feat/activity-slice-0` at `0851f78f14eef6f66e2301912f4da39fd618b837`.

## Architecture

- `docs/ARCHITECTURE.md` establishes the two plane rule: Python owns capture and frozen Inspector surfaces; TypeScript owns new product contexts.
- `pnpm-workspace.yaml` adds the root `packages/*` workspace glob for product plane node service packages.
- `packages/activity` follows the canonical context package shape with `src/index.ts`, `src/domain`, `src/events.ts`, `src/service`, `src/ports.ts`, `src/adapters`, `src/projections`, `src/server`, and `fixtures`.
- `packages/activity/src/index.ts` is the sole package export target through `packages/activity/package.json`.
- The import boundary gate extends the existing shell import graph tests so `@tm/activity` resolves to `./src/index.ts`, while deep package imports resolve to the unexported sentinel and fail closed.

## Key Patterns

- The domain machine is pure XState: fmm reports `runActivityMachine.ts` imports only `xstate`, and targeted search found no Effect, node IO, pg, network, fetch, file reads, or file writes under `packages/activity/src/domain`.
- The machine keeps replay idempotency through `RunActivityContext.appliedEventIds`, checked by `isNewEvent` and updated by `markApplied`.
- The stalled timeout uses native XState delayed transitions in the `thinking` and `running-tools` states, with default `DEFAULT_STALL_TIMEOUT_MS` equal to ten minutes.

## Detailed Findings

The canonical findings artifact is `~/.mdx/projects/tm-activity-review-s0.md`.

### Blocker: failed tool result records flip out of running-tools

File and symbol: `packages/activity/src/domain/runActivityMachine.ts`, `runActivityMachine`, `toolResultLeavesNoPending`, `applyToolResult`.

Spec §6.2 says a failed tool call annotates `running-tools` and never flips status by itself. The machine treats `record.tool_result` with `isError: true` as a normal no pending result for transition selection, so a single failed tool result targets `thinking` and only then records the error annotation. A direct Node probe against the branch machine sent `record.tool_use` followed by `record.tool_result` with `isError: true`; the resulting snapshot was `status: "thinking"`, `pendingToolCallIds: []`, `toolErrorCount: 1`.

### Major: stalled ignores record.tool_error

File and symbol: `packages/activity/src/domain/runActivityMachine.ts`, `runActivityMachine`, `stalled` state.

Spec §6.2 says a new record clears `stalled`, and a failed tool call annotates `running-tools` without flipping status by itself. The `stalled` state's transition table has no `record.tool_error` handler. A direct Node probe sent `record.tool_use`, advanced the configured stall timeout, then sent `record.tool_error`; the snapshot stayed `status: "stalled"`, preserved `stalledReason: "silence-timeout"`, left `appliedEventIds` at only the original tool event, and kept `toolErrorCount: 0`.

## Dependencies

- `xstate`: provides `setup`, `assign`, `createActor`, and `SimulatedClock` for the pure domain machine and probes.
- `@xstate/graph`: provides `getAdjacencyMap` and `getSimplePaths` for model based transition tests.
- `typescript` and `vitest`: repo level TypeScript and test infrastructure used through the root workspace.

## Relevance to Helioy

This slice sets the reusable package and boundary standard for future product plane contexts. The import boundary pattern is suitable as a template, but the status machine should be corrected before other contexts copy the current transition and test shape.

## Verification

- `git status --short` returned no output before review and after probes.
- `node_modules/.bin/tsc -p packages/activity/tsconfig.json --noEmit --incremental false` exited 0.
- `git diff --check $(git merge-base HEAD main)..HEAD` exited 0.
- Node export probe confirmed the installed XState and graph APIs used by the code exist.
- Scratch package export probe confirmed `@tm/activity` is exported and deep activity paths are unexported.

## Open Questions

- Decide whether relative imports from another package to `packages/activity/src/index.ts` should be considered acceptable because the target is the entrypoint, or forbidden because they bypass the package name and exports map.
