---
title: Activity Slice 0 Implementation
type: sessions
tags: [frontend, activity, xstate, architecture, identifiers]
summary: Added the Activity product plane standard, @tm/activity skeleton, pure XState status machine, Harness naming, branded aggregate ids, and regression tests.
status: active
source: frontend-engineer
confidence: high
created: 2026-07-03
updated: 2026-07-03
---

## Summary

Implemented Transport Matters Activity slice 0 on `feat/activity-slice-0`. The current head is commit `dafc38d`.

The slice adds `docs/ARCHITECTURE.md`, establishes repo root `packages/*` for product plane node service packages, creates `packages/activity` as `@tm/activity`, and adds the pure Activity status machine with tests. Review rounds hardened tool error semantics, bounded replay idempotency, stalled restore behavior, and the ratified identifier and literal standard.

## Architecture Decisions

- Python remains the capture plane. TypeScript owns new product plane contexts.
- Product plane packages live under repo root `packages/*`; `www/packages/*` remains browser only.
- `@tm/activity` exports only `src/index.ts` through its package exports map.
- Activity domain code uses XState v5.32.4. The machine is pure, receives resolved events, and performs no IO.
- `Harness` is an opaque `string`; Activity does not enumerate known harnesses.
- `RunId` and `WorkspaceId` are branded aggregate identity types in `packages/activity/src/ids.ts`, with `asRunId` and `asWorkspaceId` constructors used at the boundary. Event ids, record ids, and tool call ids stay plain strings.
- `RunActivityEventStream` remains a closed domain union: `lifecycle | record`.
- Consumers and tests derive status names from `activityStatuses`; event discriminants and XState state keys stay bare literals.
- Failed tool result records with `isError: true` annotate `running-tools` and do not transition to `thinking` by themselves.
- `record.tool_error` is a new record in `stalled`; it clears stalled fields, annotates the error, and returns the run to `running-tools`.
- Idempotency is a bounded per producer high water mark: lifecycle and record streams each advance by monotonic `seq` rather than retaining every event id.
- `ActivityRecord` and `RunLifecycleFact` carry `seq` to match the template fact contract.
- Tool correlation ids are required for tool use, tool result, and tool error records. The mismatching fallback to event id was removed.
- `starting` now has a native stall timer; `needs-you` still intentionally has none.
- Stalled restore uses the actual prior active status, including `needs-you` and `starting`, instead of inferring from pending tools.
- `@xstate/graph` v3.0.4 is the current model based testing equivalent used for machine path and exact adjacency coverage.
- The existing shell import graph test resolves both `www/packages/*` and root `packages/*` and fails closed on Activity internals.

## Performance Notes

No runtime UI or server path shipped in this slice. No bundle size impact is expected because `@tm/activity` is not imported by browser bundles.

Verification completed after commit `dafc38d`:

- `fmm generate && fmm validate`, 950 files indexed and valid
- `pnpm --filter @tm/activity typecheck`
- `pnpm --dir www/packages/shell test -- ../../../packages/activity/src/domain/runActivityMachine.test.ts`, 156 files and 1161 tests passed
- Import gate red test with an injected `@tm/activity/src/domain/runActivityMachine` reach in, failed as expected with exit 1, then reverted and reran green
- `just check`
- `just test`, 1792 API tests passed plus desktop and shell suites
- `just build`, inspector, canvas, and API package artifacts built at `gdafc38dee`

## Deviations from Spec

No intentional deviations.

Implementation detail: the Activity tests run through the existing shell Vitest setup, matching the current `www/packages/*` convention where package tests are collected centrally by the shell test config.

## Open Items

- Slice 1 must add transcript fixtures, record mapping tables, Postgres reader seams, and run lifecycle rows.
- Slice 1 must add the harness bundle registry as `HARNESSES` plus `KnownHarness`.
- Slice 1 must single source cross plane constants per plane: `tm_events`, `run_lifecycle`, and `run_lifecycle_event`, with conformance tests.
- Slice 1 must remove the duplicated Python `tm_events` literal in `session/writer.py` and test it against `NOTIFY_CHANNEL`.
- Slice 1 must represent the `ActivityRecordKind` to event `type` mapping as one exhaustive `Record`.
- The Node service packaging answer remains deferred to the later read surface slice, as specified.
