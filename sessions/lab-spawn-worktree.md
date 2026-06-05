---
title: Canvas lab spawn worktree fix
type: sessions
tags: [frontend, transport-matters, canvas-lab, worktree, captured-run]
summary: Fixed canvas lab run spawning by replacing the static lab worktree sentinel with the resolved launch worktree.
status: active
source: frontend-engineer
confidence: high
created: 2026-07-01
updated: 2026-07-01
---

## Summary
Implemented branch `fix/lab-spawn-worktree` and PR #185. The canvas lab now seeds its spawn worktree from an explicit `worktree_id` query or `GET /api/meta`, matching the main canvas path from PR #182. The old static lab worktree sentinel is gone from new lab terminal and captured-run spawns. Follow-up commit `d3674de` restored URL `spaceId` precedence when meta seeds only the missing default worktree.

## Architecture Decisions
- Added `www/src/session-canvas/model/worktreeDefaults.ts` so the main canvas and lab share rooted worktree guard and default adoption helpers. The shared adoption patch preserves an existing state `spaceId` before using meta space.
- Added `spaceId` and `defaultWorktreeId` to the lab store, with `adoptDefaultWorktree` and `setDefaultWorktree` actions.
- Updated lab spawn handlers so terminal and captured-run refs require a rooted worktree before any pane ref can trigger a `/v1/runs` request.
- Kept lab layout and persistence separate from the main canvas because this slice only fixes the stale spawn target.

## Performance Notes
No runtime performance optimization was involved. Validation gates completed successfully, including the fix round `just check` and `just test`.

## Deviations from Spec
No design spec defined this bug fix. The implementation followed the scout plan at `~/.mdx/projects/tm-lab-spawn-scout.md` and reused the main canvas meta seeding behavior.

## Open Items
- Existing canvas lab route remains a large file. It is still below the 700 line limit after local extraction, but future lab work should continue moving route concerns into focused seams.
