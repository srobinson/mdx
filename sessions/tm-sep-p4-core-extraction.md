---
title: Transport Matters P4 — @tm/core extraction (sep/p4-core)
type: sessions
tags: [frontend, transport-matters, monorepo, separation, pnpm-workspace, tm-core]
summary: Cut api.ts once and populated @tm/core (transport, stream port, keybinding primitives, types entrypoints); PR#189
status: active
source: frontend-engineer
confidence: high
created: 2026-07-02
updated: 2026-07-02
---

# Summary

Phase 4 (semantic) of the www/ separation plan v5: populated `@tm/core` from the
`@tm/shell` app on branch `sep/p4-core` (a13eb2c, PR#189, awaiting merge). One
commit, 163 files, all moves as tracked `git mv` renames.

# Architecture Decisions

- **api.ts one-shot cut**: neutral fetchers + transport machinery →
  `core/src/transport.ts`; overrides + breakpoint endpoints remain as
  `shell/src/api.ts` on core's exported `requestApiJson`/`requestApiVoid`
  (`RequestApiOptions.detailAware` replaces the old positional boolean; shared
  `ensureOkResponse` guard). The remainder is inspector-shaped for a wholesale
  P5 move.
- **StreamSideEffects port (5 members)**: core `exchangeStreamEvents.ts` is
  store-free; reads `getForwardingFlowId/getPausedFlow/getSelectedId`, effects
  `bumpForwardingActivity/setForwardingFlowId`. Shell binds it to `uiStore`
  with a module-level adapter object; reads go through `getState()` at event
  time so the adapter never goes stale.
- **PausedFlow rides into core** (`types/exchanges`): the port and the
  `"paused"` parser construct it, so it cannot stay in the product-side
  `types/breakpoints`. Only `BreakpointStatusDetail` remains there. This is the
  one spec deviation, stated in the PR.
- **Keybindings**: `@tm/core/keybindings` = platform + command types
  (`commands.ts`, cut from `registry.ts`) + gestureModifier + domFocus;
  `COMMANDS`/engine/gestures stay in shell pending the P5 canvas move.
- **Exports maps as the only entry**: core `.` + `./keybindings` + `./types/*`;
  host gained `src/index.ts` + `.`; the `@/host` vite/tsconfig alias is gone.
  Type imports are per-entrypoint (`@tm/core/types/ir` etc.), no barrel shim.

# Implementation Notes

- Consumer repoint (~115 files) done with a one-off codemod that resolved each
  relative/`@/` specifier against the moved-file set and split barrel/api/
  persistence/breakpoints imports by symbol; biome's format pass normalized
  ordering afterwards.
- `vi.mock` of moved symbols must target `@tm/core` with an `importOriginal`
  spread; two mocks of the same module in one file need merging (last wins
  otherwise). Dynamic `await import("../api")` sites needed manual repoints.
- `testSupport/importGraph.ts` resolves `@tm/<pkg>[/<subpath>]` through each
  package's real `exports` map (exact keys + single-`*` patterns, cached), so
  on-disk-but-unexported subpaths like `@tm/core/transport` fail closed. This
  was fix round 1 (review Major on a13eb2c): the first cut resolved any
  existing subpath. Tests written red-first pin both directions (forbidden
  deep imports throw; declared entrypoints resolve). Amended head 0ac9edd.
- vitest include gained `../core/src/**/*.test.*`; 6 core test files collected.
- `CORE_TYPES_ROOT` in `test_type_mirrors.py` same commit (spec gate).

# Deviations from Spec

- PausedFlow → core types/exchanges (forced by the port's type surface).
- Core carries a `zustand` dependency beyond the spec's react/react-query peer
  list, dragged in by `persistence.createFrontendPersistStorage`.
- Host test files keep `@/session-canvas/testUtils` (test-only edge; production
  host code has zero shell imports).

# Open Items

- P5 moves inspector/canvas trees; shell api.ts remainder, COMMANDS registry,
  engine.ts, gestures, keymapStore, FRONTEND_STORAGE_KEYS split all queued there.
- Enforcement import-graph test + dep-lint (inspector⊥canvas) go green in P5.
