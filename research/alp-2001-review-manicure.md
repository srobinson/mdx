---
title: ALP 2001 Review for Manicure Full Tool Use IDs
type: research
tags: [manicure, review, alp-2001, frontend, subagent-tracks]
summary: ALP 2001 now renders full tool_use ids and has required Claude toolu and Codex call id coverage.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-25
updated: 2026-04-25
---

## Executive Summary

Reviewed ALP 2001 on branch `nancy/ALP-1847`. The initial commit fixed production rendering but missed required Codex test coverage; follow up commit `4c1f1d2 test(www): cover codex tool use ids` closed the gap. Final status: `LGTM ALP-2001` sent to the backend engineer with CC to `helioy:general:0:1.2`.

## Project Metadata

- Project: manicure
- Area: `www` React TypeScript frontend
- Test runner: Vitest via `pnpm --dir www test`
- Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-1847`
- Branch verified: `nancy/ALP-1847`
- Commits reviewed: `f6ab994`, `4c1f1d2`

## Architecture

ALP 2001 touches the detail rendering path for content blocks:

- `www/src/components/detail/ContentBlocks.tsx:25-43` exports `blockSummary`, which formats labels for text, `tool_use`, `tool_result`, thinking, image, and unknown blocks.
- Full spawn ids matter because ALP 2000 uses Claude `toolu_*` and Codex `call_*` ids as correlation keys for subagent track detection.

## Detailed Findings

### Production behavior is correct

`www/src/components/detail/ContentBlocks.tsx:32-33` now returns the full `tool_use` id:

```ts
case "tool_use":
  return `${block.name}  ·  ${block.id}`;
```

This satisfies the rendering requirement for full spawn ids.

### Required test coverage is now present

`www/src/components/detail/ContentBlocks.test.ts` now parameterizes `blockSummary` assertions for both accepted long ids:

- Claude `toolu_01MiLL7GyXKvFTneZmojAazu`
- Codex `call_Lnc2jHDm8pTHtzdhTGeMOgdH`

This satisfies ALP 2001's unit coverage requirement for both provider id shapes.

## Verification

Ran locally from the worktree:

```bash
pnpm --dir www test src/components/detail/ContentBlocks.test.ts
pnpm --dir www lint
pnpm --dir www typecheck
```

Results:

- Targeted test: 1 test file passed, 7 tests passed
- Lint: passed, 90 files checked
- Typecheck: passed

## Dependencies

No new dependencies observed. This is a focused frontend rendering and test change.

## Relevance to Helioy

This completes the first quick win under ALP 2000. Full spawn ids are now visible, which supports reliable human debugging and the follow on track tree work in ALP 2002 through ALP 2004.

## Open Questions

None for ALP 2001. Await ALP 2002 review handoff.
