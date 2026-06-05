# Scout: typography branch archaeology

Agent: cubicell:general:6:3.5 (grok)
Date: 2026-08-09
Main tip audited against: `3725921ae23cd4088b3891b310889c8861ca05eb`
Scope: read-only history and branch audit. Nothing written in the cubicell repo.

## Verdict (one line)

`feat/typography-domain` built structure-as-content (5×7 pixel glyphs → `CubeCell[]`), never face-bound text; salvage the pure domain evaluator for voxel lettering, discard/reimplement the UI session against current shell, and use seeded SVG stencils (#164) for marks on faces.

## Branch identity

| Field | Value |
| --- | --- |
| Branch | `feat/typography-domain` (local; worktree `.claude/worktrees/typography-domain`) |
| Tip | `f325d18d5ea25e52dd618fa447bc64bf07d95af5` — `feat(typography): add interactive text composer` (2026-07-19) |
| Domain commit | `511205f8f4aa193eb85c15605c64fc3136e8dd86` — `feat(typography): add deterministic text domain` (same day) |
| Merge-base with main | `c6a2c2ef4bc7047cf41aeda17483105d3d2ec540` — `docs(lessons): capture Selector spatial-builder iteration lessons (#99)` |
| Ahead / behind main | **2** commits ahead, **62** behind (`main...feat/typography-domain` left-right `62 2`) |
| PR | **None** (`gh pr list --head feat/typography-domain` empty; no open or closed PR for this head) |
| Plan doc (on main ancestry) | `54b5940b08532e21e8c3c1328102e3a95888529e` — adds root `TYPOGRAPHY.md` (merged path; still present on main) |

Commits unique to the branch (main..feat/typography-domain):

1. `511205f8` domain + `tests/typography.test.ts` (+ `CubeAppearance` / `cloneCubeAppearance` on `src/domain/cube.ts`, `CubeStateSnapshot` alias in `src/domain/selectionAspects.ts`)
2. `f325d18d` composer UI, editor session, bake-to-literal, tests

## What it actually built

### Product model: type → structure, not type on faces

`TYPOGRAPHY.md` purpose and the branch implementation agree: typography is **another way into the same confinement** — glyphs evaluate to occupancy (`CubeCell[]`), then ordinary layout/score/morph/render paths. Cell interiors stay opaque. This is **structure-as-content**, not a face label / mesh text / SDF string on `CubeFaceState`.

Evaluation pipeline (`src/domain/typography.ts` on the branch):

```text
TextSource (content + font ref + layout + sampling)
  -> evaluateTextSource
  -> EvaluatedTextGeometry { cells, provenanceByCellId }
  -> optional convertTextSourceToLiteral (drops provenance)
  -> scene.cells replace on Convert
```

Session path only: `editor.textComposerSource` drives a preview scene via `getTextComposerScene` (`src/state/textComposerScene.ts`); convert bakes literal cells into the working scene and clears the composer (`documentActions.convertTextComposer`). **`GeometrySource` is typed and exported but never stored on `Pose` / workbench document.** Persistence of live text sources was never landed.

### Domain inventory (`src/domain/typography.ts` @ `f325d18d`)

| Kind | Symbol |
| --- | --- |
| Types | `FontAssetRef`, `TextUnit`, `TextLayout`, `TextCellSampling`, `TextSource`, `LiteralGeometrySource`, `TextGeometrySource`, `GeometrySource`, `TextCellProvenance`, `EvaluatedTextGeometry`, `TextUnitIdFactory`, `CreateTextSourceOptions` |
| Font assets | `pixelFont5x7Content`, `pixelFont5x7Ref` (`builtin:pixel-5x7` + fixed sha256), `pixelFont5x7SupportedGlyphs` |
| API | `createTextSource`, `normalizePixelFont5x7Text`, `setTextSourceContent`, `reconcileTextUnits` (LCS identity preserve), `evaluateTextSource`, `convertTextSourceToLiteral` |
| Internals (non-export) | `appendGlyphCells`, `buildLcsLengths`, `createWordIds`, `createTextCellId`, `getAlignedOriginX`, `measureLineWidth`, `isBoundaryPixel`, `isGlyphPixelOccupied`, `isPixelOccupied`, `validateTextSource`, `assertUniqueTextUnitIds`, `parsePixelFont` |
| Font constraints | 5×7 bitmap, A–Z + space + `-`, tracking, align `start\|center\|end`, extrusion depth along Z |

Supporting domain deltas on the branch:

- `src/domain/cube.ts`: `CubeAppearance`, `cloneCubeAppearance` (`511205f8`)
- `src/domain/selectionAspects.ts`: `CubeStateSnapshot` = `CubeAppearance` via `cloneCubeAppearance`
- `src/domain/workbench.ts`: `createTextSourceId`, `createTextUnitId` (id factories; not present on current main under those names)
- `src/domain/index.ts`: re-exports typography surface

### App / state / UI inventory (`f325d18d`)

| Path | Role / symbols |
| --- | --- |
| `src/state/cubicellState.ts` | `EditorSessionState.textComposerSource: TextSource \| null` |
| `src/state/actions/types.ts` | `openTextComposer`, `closeTextComposer`, `setTextComposerSource`, `convertTextComposer` |
| `src/state/actions/editorActions.ts` | open creates source from selection appearance prototype; mutually exclusive with grid composer |
| `src/state/actions/documentActions.ts` | `convertTextComposer` → `convertTextSourceToLiteral` → replace `scene.cells` + multi-cube selection |
| `src/state/textComposerScene.ts` | `getTextComposerScene` — WeakMap-cached evaluate over working base scene |
| `src/components/text-composer/TextComposer.tsx` | `TextComposer` rail: content input, align, tracking, extrusion; caps maxCharacters 32, maxPreviewCells 2048, maxExtrusionDepth 6 |
| `src/components/text-composer/text-composer.css`, `index.ts` | styles / barrel |
| `src/app/EditorStage.tsx` | `EditorStage`, `TextComposerOverlay`, `useComposerFraming`, `EmptySceneStart` — App split so composer owns stage scene |
| `src/app/App.tsx` | thinned in favor of `EditorStage` (main has since moved to `StudioShell` / different shell; no `EditorStage`) |
| `src/panels/SceneSection.tsx` | **Create Text** button → `openTextComposer` |
| `src/app/useEditorCommands.ts`, `src/styles/app.css`, `tests/state.test.ts` | minor glue |

### Tests

- `tests/typography.test.ts`: `reconcileTextUnits`, `text source authoring`, `evaluateTextSource`, `convertTextSourceToLiteral`
- `tests/textComposer.test.tsx`: `TextComposer`, `typography composer session`

### What it deliberately did not build

- No face-bound string, glyph atlas, or `CubeFaceState` text field
- No multi-line paragraph model beyond single-line runs (lineId is always `${source.id}:line:0`)
- No font loading beyond bundled 5×7 content string
- No `GeometrySource` on `Pose` / structure asset / persistence
- No PR, no merge, no follow-up commits on this branch after 2026-07-19

## Why it stalled / was abandoned (history lens)

Evidence is **incidental product-sequence stall**, not an explicit kill commit:

1. **No PR.** Work stopped at local tip `f325d18d` the same day both commits landed. Zero review traffic.
2. **21 days frozen** while main advanced ~62 commits (through `3725921`, 2026-08-09), including animation studio, edge shaping spikes, camera KISS, confinement product docs, and **face stencils**.
3. **Incomplete slice.** Plan (`TYPOGRAPHY.md` @ `54b5940b` and still on main) requires `GeometrySource` to replace direct `Pose.cells` ownership. Branch only delivered session preview + bake-to-literal. Authoring model never became first-class document geometry.
4. **Main docs still deny implementation.** `TYPOGRAPHY.md` on main: *“The repository contains no typography implementation.”* Plan status remains “initial proposal… open for design review.” Branch work never reconciled into docs or main.
5. **Product orientation reaffirmation** `de4c6a8fbc170adacfe6fbbfd87de49d6687fe18` (#151): typography reframed as performable cube structure; interiors stay opaque; glyphs resolve to cells and faces, never speculated cell content. Aligns with the branch’s structure model, does not ship it.
6. **Face-mark path shipped instead for surface figures.** `c32bb7263588f2e5963fbbdae88e414d36915408` (#164) seeded SVG stencils on faces (`CubeFaceFigure.stencilId`, `src/domain/stencil.ts`, `src/scene/stencilAtlas.ts`). Campaign docs later extended **TYPOGRAPHY.md** with **concierge mark seeding** (`77849147`, `11bc26fa` on campaign runway lineage, folded via #166 materials) — marks enter the **stencil atlas**, not the pixel-font domain. That is the live “letters/logos on faces” path.
7. **Shell drift.** Composer required `EditorStage` extraction from `App.tsx`. Main editor shell is now `StudioShell` / different app layout; a naive cherry-pick of `f325d18d` does not apply cleanly.

No commit message says “abandon typography.” History shows **unmerged spike + product attention moved to animation + face stencils**.

## Broad history sweep (`git log --all -S` / grep)

| Needle | Material hits (SHAs) | Notes |
| --- | --- | --- |
| `typography` | `54b5940b` plan; `511205f8` / `f325d18d` impl; `de4c6a8f` product sync; older product journey docs; campaign `77849147` / `11bc26fa` mark recipe | Only impl commits are the two on `feat/typography-domain` |
| `glyph` | same typography set + docs; `bc71cb1c` perf slice (incidental); panel transition cards | No second glyph engine |
| `font` | typography pair + many UI/CSS `font-*` and studio CSS false positives | Real font domain only on typography branch |
| `TextSource` / `pixelFont` / `evaluateTextSource` | **only** `511205f8`, `f325d18d` | No parallel attempt on other branches |
| `faceText` / face label string field | **none** as a domain symbol | Face “content” today is `CubeFaceFigure` + stencils (#164), not free text |
| Grep subjects | “structure-as-content” language lives in `TYPOGRAPHY.md` / product docs, not a separate branch name | Only typography-domain branch name matches the scout flag |

**Conclusion of sweep:** there is one prior code attempt for text: `feat/typography-domain`. No hidden face-text renderer. Manual lettering via sculpt/shadow slots is product lore in `TYPOGRAPHY.md` (cm observations), not a code path.

## Salvage call vs current main (`3725921`)

### Reuse for **structure lettering** (text as lattice)

| Salvage | Why |
| --- | --- |
| **Keep / re-land pure domain** `typography.ts` + `tests/typography.test.ts` | Deterministic, browser-free, matches `CUBICELL.md` “Text And Words” and `TYPOGRAPHY.md` first representation. Low coupling. |
| **Keep** `reconcileTextUnits` / unit identity / provenance map | Needed if text remains generative under animation morphs (plan requirement). |
| **Keep** bundled `pixelFont5x7*` as v0 font asset | Honest confinement; matches plan’s cellular first milestone. |
| **Maybe** `CubeAppearance` + `cloneCubeAppearance` | Small DRY; main lacks them; re-derive against current `CubeFaceState` (now includes `figure` / stencil fields — branch appearance pick may need field set update). |
| **Rewrite UI** against current shell | Do not cherry-pick `EditorStage` / old `App.tsx` split. Reattach composer to `StudioShell` + current command/session patterns if structure text ships. |
| **Defer** live `GeometrySource` on `Pose` | Still the plan’s hard part; branch never finished it. Baking to literal remains a valid v0. |

### Discard / wrong layer for **text on cube faces**

| Item | Why discard for face text |
| --- | --- |
| Entire evaluate→`CubeCell[]` pipeline | Occupancy, not face decoration. Wrong primitive for “print on a face.” |
| TextComposer session + convert-to-structure | Produces lattices of cubes spelling letters; does not set `CubeFaceState.figure`. |
| Pixel 5×7 as face renderer | Face path is SVG stencil atlas (`seededStencils`, `stencilAtlasCapacity` 16), campaign mark recipe in `TYPOGRAPHY.md`. |

### Current tree path for face-bound marks

- `src/domain/cube.ts`: `CubeFaceFigure`, `CubeFaceState.figure`
- `src/domain/stencil.ts`, `src/domain/seededStencils.ts`
- `src/scene/stencilAtlas.ts`, face stencil shader path (#164 `c32bb726`)
- Campaign: one gated commit per outlined SVG mark; no runtime font ingestion

Putting **arbitrary live text** on faces is still **unbuilt**. Closest shipped mechanism is **pre-seeded stencil assets**, not the typography branch.

## Deliberate vs incidental restrictions

| Restriction | Classification | Evidence |
| --- | --- | --- |
| No text-inside-cell / mesh content | **Deliberate** product | `TYPOGRAPHY.md`, `de4c6a8f` confinement orientation |
| Typography = cells from glyphs first | **Deliberate** plan | `TYPOGRAPHY.md` proposed outcome; branch implements it |
| No free-form face strings on main | **Deliberate** confinement + stencil closed roster | #164, seeded atlas capacity, campaign C' |
| Typography branch unmerged | **Incidental** sequencing (no PR, shell/studio priority) | 21d stall, 62 behind, zero PR |
| `GeometrySource` not on Pose | **Deliberate incomplete milestone** (planned, not shipped) | plan + types only on branch |

## Citation index (SHAs only; no line numbers)

| SHA | Role |
| --- | --- |
| `3725921ae23cd4088b3891b310889c8861ca05eb` | main tip at audit |
| `c6a2c2ef4bc7047cf41aeda17483105d3d2ec540` | merge-base |
| `511205f8f4aa193eb85c15605c64fc3136e8dd86` | domain + tests |
| `f325d18d5ea25e52dd618fa447bc64bf07d95af5` | composer + session (branch tip) |
| `54b5940b08532e21e8c3c1328102e3a95888529e` | `TYPOGRAPHY.md` plan on main lineage |
| `de4c6a8fbc170adacfe6fbbfd87de49d6687fe18` | product confinement reframe (#151) |
| `c32bb7263588f2e5963fbbdae88e414d36915408` | face stencils shipped (#164) |
| `7784914773bd504fe5e22e14b5cc178380eeb1cb` | concierge mark seeding recipe (docs) |
| `11bc26fa1bd63761df1aeadbb89d74ebdb9032a0` | budget rebaseline steps correction (docs) |

## Bottom line for orchestrator

Hypothesis from grid scout (unmerged typography / structure-as-content branch) is **confirmed**. The branch is a solid **domain spike for voxel type**, abandoned before document geometry and before PR, while **face decoration moved to stencils**. For “text on faces,” salvage is thin: prefer stencil marks; only re-land `evaluateTextSource` if the goal is sculptable letter lattices, not face prints.
