# cubicell colour typecheck probe (re-run)

**Date:** 2026-08-05  
**Worktree:** `/Users/alphab/Dev/LLM/DEV/helioy/cubicell/.claude/worktrees/colour`  
**Branch:** `feat/accent-colour`  
**Topic:** `cubicell-colour-probe`

Prior result discarded: earlier run was invalid (no `node_modules` in this worktree). This document is a full rewrite after `pnpm install`.

## Dirty tree (before)

```
 M src/domain/cubeEdgeState.ts
 M src/theme/themeTokens.ts
```

## Probe validity (scope proof)

| Check | Result |
|-------|--------|
| Local binary | `./node_modules/.bin/tsc` → TypeScript 6.0.3 (exists, executable) |
| Config | `tsconfig.app.json` `"include": ["src", "tests"]`, `"noEmit": true` |
| Full src inventory | `find src …` = **452** files |
| Program file list | `tsc -p tsconfig.app.json --listFilesOnly` lists **452** `/src/` paths |
| Set equality | `comm` of find vs listFilesOnly is **empty** (every src file is in the program) |
| Key consumers listed | `scenePolarity.ts`, `controlBindings.ts`, `edgeClaimResolution.ts`, `colorSpace.ts` all appear in `--listFilesOnly` |
| Cache | Deleted `node_modules/.tmp/*.tsbuildinfo`; ran `tsc -b --force` and `tsc -p tsconfig.app.json --incremental false` |
| Sanity: exhaustive switch | **No** `switch` over `CubePartColor` anywhere in `src/`. Nothing exhaustive that should have failed and did not. Probe is not reconciling a silent miss. |

Commands run (non-writing only; never `pnpm check` / format / lint --fix):

```
./node_modules/.bin/tsc -b --force --pretty false
./node_modules/.bin/tsc -p tsconfig.app.json --pretty false --incremental false
```

Both exit **2** with the same single error.

## Typecheck result

**FAILS — 1 error across 1 file.**

### Raw output (full)

```
src/theme/scenePolarity.ts(41,10): error TS7053: Element implicitly has an 'any' type because expression of type '"black" | "white" | "accent"' can't be used to index type 'ScenePartColors'.
  Property 'accent' does not exist on type 'ScenePartColors'.
```

## Fail-closed (compiler forces fourth case)

| Site | Message |
|------|---------|
| `src/theme/scenePolarity.ts:resolveCubePartColor` | `TS7053: Element implicitly has an 'any' type because expression of type '"black" \| "white" \| "accent"' can't be used to index type 'ScenePartColors'. Property 'accent' does not exist on type 'ScenePartColors'.` |

Body: special-cases `"theme"` → `polarity.contrast`, then indexes `polarity.partColors[color]` where `ScenePartColors = Record<"black" \| "white", string>`. That is the only fail-closed consumer.

Runtime note (if the index were forced past the typechecker): `partColors["accent"]` is `undefined`; `three.Color.set(undefined)` yields **`#ffffff` pure white**. Not live while typecheck fails.

## Fail-open set

Every other site that **reads** a `CubePartColor` and **branches or maps** without the compiler forcing a fourth case. Pure identity compares / opaque pass-through (store, tween payload, equality dirty-checks) omitted.

| # | Site | Pattern | What authored `accent` does today |
|---|------|---------|-----------------------------------|
| 1 | `src/editor/controlBindings.ts:partColorOptions` | Hardcoded enum map `theme` / `black` / `white` only (not derived from `cubePartColors`). Shared by `cube.color`, `face.color`, `edge.color`. | **No segment selected** in `Segmented` (value matches no option). Cannot author `accent` from the control. |
| 2 | `src/domain/edgeClaimResolution.ts:isAuthoredStyle` | Binary branch `color !== defaultCubePartColor` (`"theme"`). | Treated as **authored non-theme style** (same priority class as black/white for edge claim ownership). |

No other branch/map sites over `CubePartColor` values were found. Validation (`isCubePartColor`) and codecs (`cubePartColors` index encode/decode) follow the widened array and therefore accept/persist `accent` without a separate incomplete case list.

### Worst case (one phrase)

**blank color control; claim-as-authored; mesh path type-errors (would be pure white if forced)**

## Dirty tree (after)

```
 M src/domain/cubeEdgeState.ts
 M src/theme/themeTokens.ts
```

**Tree unchanged** — same two modified files, no additional dirt.
