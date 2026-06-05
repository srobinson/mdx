---
title: Activity Identifier Typing Standard for Transport Matters
type: research
tags: [transport-matters, activity, type-design, harness, product-plane]
summary: Recommends branded opaque ids, opaque harness strings, and named constants for cross boundary protocol strings in the product plane standard.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-03
updated: 2026-07-03
---

## Executive Summary

Reviewed the current `@tm/activity` slice 0 code and companion specs for the product plane standard. The recommended standard is a split: branded strings for opaque identifiers, an open enum for harness ids, and named constants for strings that cross module, package, or plane boundaries.

## Project Metadata

- Project: `transport-matters`
- Package under review: `packages/activity`
- Primary files: `packages/activity/src/domain/runActivityMachine.ts`, `packages/activity/src/ports.ts`
- Specs: `~/.mdx/projects/tm-activity-spec.md`, `~/.mdx/projects/tm-harness-support-standard.md`

## Architecture

Activity is the first TypeScript product plane context. It consumes transcript records and lifecycle facts from the Postgres backed store contract, then projects run status through a pure XState domain machine. Harness specific parsing belongs in bundle adapters, not the Activity domain.

## Key Patterns

- `activityStatuses` is already a domain tuple that should remain the source for status names.
- `RuntimeKind = "claude" | "codex"` in `runActivityMachine.ts` is too closed for the harness bundle standard.
- `RunActivitySeqCursors` uses stream keys, not ids; these should be a local closed vocabulary.
- Protocol strings such as Activity event discriminators, Activity record kinds, `tm_events`, and `run_lifecycle` need named sources because adapters and producers will repeat them.

## Detailed Findings

Canonical position file: `~/.mdx/projects/tm-activity-idtyping-codex.md`.

Recommendation:

1. Use branded strings at IO boundaries for opaque identifiers: `RunId`, `WorkspaceId`, `EventId`, and `RecordId`.
2. Use an open enum for `Harness`: `KnownHarness | (string & {})`, with known harness values exported from the harness bundle registry. Rename Activity `RuntimeKind` and `runtime` to `Harness` and `harness`, and keep the domain from branching on it.
3. Use const tuples for owned finite vocabularies such as Activity statuses and Activity stream keys.
4. Use named constants for any string that crosses module, package, or plane boundaries. The Python producer and TS consumer for `tm_events` and `run_lifecycle` should share a session store contract artifact or generated constants.

## Dependencies

- XState domain machine vocabulary lives in `packages/activity/src/domain/runActivityMachine.ts`.
- Port DTO vocabulary lives in `packages/activity/src/ports.ts`.
- Harness vocabulary should live with the harness bundle registry, per `tm-harness-support-standard.md`.

## Relevance to Helioy

This standard will be copied by future product plane contexts. The split preserves explicit boundaries without forcing domain edits when a new harness appears.

## Open Questions

- Whether the shared cross plane contract artifact should be JSON, TOML, or a small generated package with Python and TypeScript outputs.

## Delta Verification 2026-07-03 dafc38d

Verified the Opus aligned standard application on `feat/activity-slice-0` at `dafc38d`. `Harness` is opaque `string`; `runtime` and `RuntimeKind` are gone from `packages/activity/src`; `RunId` and `WorkspaceId` are branded in `packages/activity/src/ids.ts` with constructors exported at the package boundary; event ids, record ids, and `toolCallId` remain plain strings. `RunActivityEventStream` is the closed `"lifecycle" | "record"` domain set. `docs/ARCHITECTURE.md` now records the identifiers and literals standard plus slice 1 commitments for harness registry, cross plane constants, `tm_events` de-duplication, and the `ActivityRecordKind` mapping.

Verification: pristine `git status --short`; direct Node probe preserved failed tool behavior and accepted `harness: "future-harness"`; Vitest `runActivityMachine.test.ts` reported 25 passed; `tsc -p packages/activity/tsconfig.json --noEmit --incremental false` exited 0; targeted purity search found no domain IO or Effect.
