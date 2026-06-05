---
title: Transport Matters www Phase 3 Workspace Scaffold
type: sessions
tags: [frontend, transport-matters, www-separation, pnpm]
summary: Implemented and review hardened the Phase 3 mechanical repo-root pnpm workspace scaffold for www separation.
status: active
source: frontend-engineer
confidence: high
created: 2026-07-02
updated: 2026-07-02
---

## Summary

Implemented Phase 3 of the Transport Matters www separation plan v5 on branch `sep/p3-scaffold`, PR#188. The existing Vite app now lives at `www/packages/shell` and still builds as one bundle into `api/src/transport_matters/www`. The repo root owns the pnpm workspace, shared lockfile, shared TypeScript base config, and cross package recipes.

Fix round 1 amended the branch to commit `7d213b7a48449aee44c13106ec7607c425d1a7f2`. The review fixes kept the slice mechanical: tightened root, shell, desktop, CI, release, and hook gates; covered skeleton packages with explicit typecheck scripts; restored synchronous root shell theme assertions; narrowed the release script test guard to the exact `install-local` recipe; removed dead scripts and stale mapping metadata; and updated project docs to name the repo-root gates.

## Architecture Decisions

- Kept the shell package as the only production bundle for Phase 3.
- Added skeleton packages for `@tm/core`, `@tm/inspector`, and `@tm/canvas` with placeholder exports only.
- Moved the desktop host source to `www/packages/host/src` so it has a package boundary without changing behavior.
- Delegated root `just` recipes to package-local justfiles so `just www` and `just desktop` keep package semantics after the move.
- Made root, CI, release, and lefthook typecheck all current www packages, not just `@tm/shell`.
- Kept one root pnpm lockfile and removed dead package scripts that could create false green results.

## Performance Notes

No runtime performance optimization was targeted. The production bundle still builds through the shell package and embeds in the Python wheel. The fresh clone build produced the embedded bundle and wheel successfully.

Verification completed:

- `fmm generate && fmm validate`
- `git diff --check`
- Local `/private/tmp/tm-sep-p3-scaffold`: `just check && just test && just build`, EXIT=0 in `/tmp/tm-p3-fix-round-1-local.log`
- Fresh clone `/tmp/tm-p3-fix-fresh.mnghtM/transport-matters`: `just check && just test && just build`, EXIT=0 in `/tmp/tm-p3-fix-round-1-fresh.log`
- Remote branch verified at `7d213b7a48449aee44c13106ec7607c425d1a7f2`

## Deviations from Spec

No semantic extraction was performed. The only source relocation beyond moving the shell app was the host source move required to create the package scaffold.

## Open Items

- Future phases can move real core, inspector, and canvas ownership into their skeleton packages.
- Existing lint warnings remain in moved shell files: two important cursor styles and one test non null assertion.
