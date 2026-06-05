# cubicell-colour-review-radius

Seat: third family (large-context radius). Target: `408b2687` on `feat/accent-colour`, base `7293438`.

Read-only. No source writes. Verdict line on bus only.

## Verdict

**Superseded.** Initial radius pass on commit `408b2687` content was clean. Immediately after, `git status --porcelain` showed an **uncommitted working-tree mutation** not present in the commit and not authored by this seat (read-only). Re-verdict:

`review: issue Blocker src/domain/cubeEdgeState.ts:isCubePartColor working tree rejects accent while cubePartColors still lists it`

Commit blob remains correct (`return cubePartColors.some(...)`). Working tree is:

```ts
return value !== "accent" && cubePartColors.some((color) => color === value);
```

Effect if left in place: UI/options from `cubePartColors` can still surface Accent; validators and codecs that use `isCubePartColor` reject it — silent fourth-member mishandle on the live tree.

## 1. Value ramp / design invariant

### Authored rails (measured OKLab L, linear sRGB → OKLab same transform family as `colorSpace.ts`)

| Token | Hex | OKLab L | Chroma | Role |
|-------|-----|---------|--------|------|
| `accent` | `#c0fac0` | **0.9308** | 0.097 | dark-bg rail; matches claim L 0.93 |
| `accentOnLight` | `#1c0c43` | **0.2199** | 0.096 | light-bg rail |
| black / white | `#050505` / `#ffffff` | 0.115 / 1.000 | 0 | value carriers |

Polarity wiring (`scenePolarity.ts`):

- black polarity → `themeColorTokens.accent` (`#c0fac0`)
- white polarity → `themeColorTokens.accentOnLight` (`#1c0c43`)
- workbench reuses the **same** rails (does not compress accent into workbench greys the way black/white compress)

Discrete token switch on polarity flip: no intermediate grey. Mid-OKLab between the two rails is L≈0.58 with low chroma, but that path is not a continuous polarity morph of part color.

### Paths that do change lightness (and why they are not a reintroduced grey ramp)

1. **Workbench form grooming** (`resolveInstanceColor` → `shiftLightnessForContrast` via `edgeLightnessDelta` / `faceLightnessDeltaById`). Applies to **all** part colors including accent. Bottom face on light accent: L 0.93 → ~0.57. Chroma is preserved (`shiftLightnessForContrast` keeps a/b), so faces stay tinted, not boring greys. This is the #160 edit-mode form cue, not accent-as-value identity. Artifact configs omit both deltas.

2. **OKLab morph midpoints** (`resolveLerpedPartColor`). Black→accent at 0.5 is L≈0.52 with half chroma. Inherent to any cross-token lerp; endpoints remain pure rails. Not a fourth-member mishandle.

### What does **not** reappear

- No face-value identity for accent tokens.
- No domain occlusion path in this commit.
- Workbench black/white still use compressed greys (`workbenchBlack` / `workbenchWhite`); accent deliberately does not join that compression.

## 2. Blast radius beyond the 11-file diff

Searches run:

```text
rg CubePartColor|cubePartColors|isCubePartColor|ScenePartColors|partColors\[  (src)
rg scenePolarities|workbenchScenePolarities|resolveCubePartColor          (src)
rg faceLightnessDeltaById|cubeFaceLightnessDeltaById                      (repo)
rg switch/case on color tokens                                            (src: none)
rg hardcoded ["theme","black","white"]                                    (tests only: colorSpace.test.ts)
```

### Production consumers of the widened union (outside the commit’s production files)

| Area | Path | Handling of fourth member |
|------|------|---------------------------|
| Compact pose codec | `src/persistence/recordCodecs/compactPose.ts` | `cubePartColors.indexOf` / `cubePartColors[i]` / `isIndex(..., cubePartColors.length)` — length-driven |
| Edge state field codec | `src/domain/cubeEdgeState.ts` | same index table (commit updated the table; append-only comment) |
| Validators | `authoredOperationValidation/scene.ts`, `workbenchValidation/pose.ts` | `isCubePartColor` |
| Resolve / lerp | `src/scene/colorSpace.ts` | `resolveCubePartColor` → `partColors[color]`; maps include `accent` |
| Instances / morph / score | `cubeInstances.ts`, `sceneMorph.ts`, `scoreAt.ts`, `sharedEdgeTweens.ts` | typed `CubePartColor`; no 3-way switches |
| Geometry / ops | `cubeGeometry.ts`, `cubeOperations.ts` | type only |
| Edge claims | `edgeClaimResolution.ts` | `!== defaultCubePartColor` only |
| Editor stage | `EditorStudio.tsx` | polarity family switch only |
| Thumbnails | `thumbnailArtifact.ts`, `thumbnailRenderer.ts` | `scenePolarities` (artifact rails; accent present on maps) |
| CSS tokens | `tokens.css` etc. | selection/recording accents only; not cube part palette |

**No production consumer found that hardcodes a three-member palette or exhaustive switch missing `accent`.**

### Test-only gap (not a silent runtime mishandle)

- `tests/colorSpace.test.ts` still pairs `["theme","black","white"]` for workbench lerp bounds; accent covered only by a black→accent distinct-samples test. Completeness nit for the other seats, not a radius collision.

## 3. Gate second direction (workbench keeps #160 face cue)

| Family | `faceLightnessDeltaById` | `edgeLightnessDelta` |
|--------|--------------------------|----------------------|
| `workbenchScenePolarities` | set (`cubeFaceLightnessDeltaById`) | `0.12` |
| `scenePolarities` (artifact) | **absent** | **absent** |

Wire-up:

- `instancedPartMeshCore.resolveInstanceColor`: face delta from `context.polarity.faceLightnessDeltaById?.[faceId]` (optional).
- `EditorStudio`: `previewing ? scenePolarities : workbenchScenePolarities`.
- Thumbnails: `scenePolarities` only.
- Tests: `instances.test.ts` “face meshes resolve a distinct value for every orientation” still drives workbench face deltas; edge test asserts artifact byte-identical authored colors.

Both directions hold: export/preview fidelity without form ramp, edit-mode form cue retained.

## Hygiene / code-review lenses (read-only notes)

- Append-only `cubePartColors` + index codecs: correct migration shape.
- `ScenePartColors = Record<Exclude<CubePartColor,"theme">, string>` forces accent into maps; `createPolarityConfig` injects rail hex — avoids partial records.
- Control options derived from `cubePartColors.map` — no second palette list (DRY).
- No file-size or spaghetti growth in this slice; small, central type widen.

## Pristine tree / concurrent mutation

- Pre-review and mid-review: `HEAD` = `408b2687cd0393f533f3f77afd93d407ab29a6ae`.
- First porcelain check during radius work: empty.
- After first clean bus reply: uncommitted `isCubePartColor` sabotage (`value !== "accent" &&`) on `cubeEdgeState.ts` (not authored by this seat; later disappeared from the working tree).
- Immediately after that report: uncommitted `colorSpace.ts` sabotage — `resolveLerpedPartColor` uses `resolveCubePartColor(from, ...)` for the *to* sample, collapsing mid-lerp to identity from color.

This seat performed no source writes (only `~/.mdx/projects/cubicell-colour-review-radius.md` and bus messages). Concurrent mutation prevents a lasting pristine porcelain; commit blob content for `408b2687` remains the review target and answers Q1–Q3 clean.
