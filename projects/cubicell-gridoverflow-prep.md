# GridOverflow contract prep

## (a) Declaration + every reference

```ts
// src/domain/grid.ts:7
export type GridOverflow = "allow" | "clamp" | "hide";
// GridFormat.overflow; default "allow"; clone: format.overflow ?? default
```

| Site | Role |
|------|------|
| `src/domain/grid.ts` | type, field, default, clone |
| `src/state/workbenchValidation/pose.ts` | wire accept `allow\|clamp\|hide` |
| `src/evaluation/sceneMorph.ts` | morph copies overflow (cut→b else a) |
| `tests/sceneMorph.test.ts` | asserts morph preserves overflow |
| negative-space design spec | "dormant … no code reads" |
| `CUBICELL.md` | aspirational GridFormat sketch |

No production reader branches on the value.

## (b) Introduction intent (git log -S)

`5f708950` **feat: add grid based cube placement** (empty body). Landed with `GridFormat` day one; no prose defines modes. `268eb645` restates dormancy in negative-space spec. Vocabulary in `CUBICELL.md` only.

## (c) Plausible consumers (symbol → behavior)

- **allow** (de facto): `placeCubesAt` / neighbors already unbounded
- **clamp** into bounds: `placeCubesAt`, neighbor seeds, `insertLatticeLine` / insert-with-shift
- **hide**/drop: `placeCubesAt` reject or `resizeGridScene` trim
- Bound source missing: `getSceneGridDimensions` = occupied extent only; needs stored bound first
- Morph fidelity: `sceneMorph` already copies; meaningful once read

## (d) Spec questions for Stuart (max 5)

1. Bounds: new persistent `GridFormat` field, or separate from occupied extent?
2. Apply at placement only, lattice shift, resize, or all structural writes?
3. Exact `clamp` vs `hide`: remap, drop write, or create-hidden cells?
4. Default stays `allow` for existing docs, or migrate saved workbenches?
5. UI expose this cycle, or domain-only with default `allow`?
