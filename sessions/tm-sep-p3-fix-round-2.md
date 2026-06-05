---
title: Transport Matters www/ separation P3 fix round 2
type: sessions
tags: [frontend, transport-matters, www-separation, lefthook, tsconfig, pnpm-workspace]
summary: Fixed all 4 fix round 1 residuals on sep/p3-scaffold (PR#188); amended 7d213b7 to 82a0644, gates and fresh-clone green
status: active
source: frontend-engineer
confidence: high
created: 2026-07-02
updated: 2026-07-02
---

# Summary

Fresh-eyes fix round 2 on PR#188 `sep/p3-scaffold`. Scope was the four residuals in `TMP/review-slice-p3.md` section "Fix round 1 residuals", under the mechanical contract (moves, path repoints, config corrections; no semantic drift). Amended the single slice commit `7d213b7` to `04e9427`, then to final head `82a06447f65847459a800bdba8a5d9fc2084fd4b` after a Stuart-requested lint nit (commandModel.test.ts `noNonNullAssertion`, pre-existing at base; fixed by hoisting `repoMainWorktree` as a named fixture). Force-pushed with lease. Not merged.

# Architecture Decisions

- **Lefthook globs** widened to `www/packages/**/*.{...}` on both hooks rather than adding a `*/*` alternation. Simpler, covers package-root files (the empirically verified 1.13.6 gap), and hook-covers any future sixth package by default.
- **tsconfig.bundler.json promoted to repo root** beside `tsconfig.base.json` rather than skeletons reaching into `../shell/`. Four consumers (shell app and node contexts, three skeletons) now extend one workspace-level intermediate; no cross-package config ownership.
- **Naming layers collapsed toward pnpm scripts**: shell justfile `start` calls `pnpm preview` directly; the `start` alias and the dead `analyze` recipe are gone.

# Verification

- Lefthook fix proven with `lefthook run pre-commit --commands <hook> --file <path>` probes: package-root files trigger lint (Checked 4 files) and typecheck; non-matching control still skips.
- tsconfig refactor proven with `tsc --showConfig` diffs against a HEAD reconstruction: shell node context byte-identical in effective options (preserves the m6 fix); skeleton delta is exactly `+noEmit: true`, inert (no emit path, typecheck passes `--noEmit` on CLI, extending the bundler intermediate was the reviewer-sanctioned fix shape).
- Gates `just check && just test && just build` green in the working tree and in a fresh clone run from nothing (1770 api tests; wheel embeds the www/ bundle) at `04e9427`. The `82a0644` delta is test-file-only, verified with file-scope biome, full shell typecheck, and 66/66 tests in the file; Stuart waived a full gate rerun.

# Deviations from Spec

None. The `noEmit: true` effective-option addition to skeletons is inherent to the residual's prescribed fix and functionally inert.

# Open Items

None in scope. Delta review of `7d213b7..04e9427` is the orchestrator's next gate.
