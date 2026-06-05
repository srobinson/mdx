# Cubicell scout — Area A: grid/content model (archaeology)

Lens: history. Read-only survey of how face and cell content restrictions arrived, whether each was deliberate or incidental, and whether richer content was ever built then removed or left declared-but-unhonored.

Hypothesis under test: *we built a layout engine that does not support content* — the internal grid model has self-imposed restrictions blocking richer face content.

**Verdict: confirmed.** The shipped model is occupancy + part style (and, as of #164, a sealed seeded-mark overlay). It is not a content system. Most hard walls are deliberate product confinement or codec discipline; the largest *incidental* gap is that stencil *library* metadata can persist without payload or render path.

---

## Current face/cell surface (baseline)

| Layer | What exists today | Symbols |
|-------|-------------------|---------|
| Scene occupancy | Flat `cells: CubeCell[]` only; no `CellContent` union | `CubicellScene` / `Pose` in `src/domain/scene.ts` |
| Cell | edges, faces, placement, size, visibility | `CubeCell` in `src/domain/cube.ts` |
| Face state | `color`, `opacity`, `visible`, optional `figure` | `cubeFaceStateOwner` in `src/domain/cube.ts` |
| Figure | `stencilId`, `region` (`form`\|`field`), `fit` (`margin`\|`bleed`), `color` | `CubeFaceFigure` in `src/domain/cube.ts` |
| Colour roles | closed append-only enum `theme`\|`black`\|`white`\|`accent` | `cubePartColors` in `src/domain/cubeEdgeState.ts` |
| Stencil id | content-addressed `sha256:…` | `StencilId` in `src/domain/stencil.ts` |
| Stencil asset (library) | `byteLength`, `id`, `kind`, `mediaType` (fixed `image/svg+xml`), `name` — **no source bytes** | `StencilAsset` in `src/domain/stencil.ts` |
| Renderable marks | two seeded SVG entries only | `seededStencils` in `src/domain/seededStencils.ts` |
| Atlas | fixed 16-slot map over `seededStencils` only | `stencilAtlasCapacity`, `getStencilAtlasSlot` in `src/scene/stencilAtlas.ts` |
| Author UI for faces | visible, color, opacity, stencil enum | `face.*` bindings in `src/editor/controlBindings.ts` |

Docs already record the product posture: interiors deliberately unanswered (`PRODUCT.md`, `ARCHITECTURE.md`); `MODEL.v2.md` §Current model limits lists missing `CellContent` and nested grids as intentional facts about the repository.

---

## Restriction ledger (introducing commit / PR → deliberate vs incidental)

Each row is a restriction on *what a face (or cell) can show*, with the commit that introduced or sealed it.

### 1. Face state is style only (no figure, no media, no text)

- **Restriction:** `CubeFaceState = { color, opacity, visible }`. Faces render as solid (later translucent) planes.
- **Introduced:** `51c14ee7` *feat: model cube edges and faces* (2026-07-06). Geometry: `<planeGeometry>` per face in the same commit.
- **Call:** **Deliberate.** First primitive language was black/white faces + edges; product identity, not an accident.

### 2. Closed colour roles (no free RGB / textures)

- **Restriction:** Part colour is a closed enum, not a free colour or map.
- **Timeline:**
  - `51c14ee7`: `CubePartColor = 'black' | 'white'`
  - `9786f4e6` *feat: add cube layer and theme color controls*: adds `'theme'`, default becomes theme
  - `7d5e942e` / **PR #163** *feat(scene): add accent cube colour role on hue at pinned lightness*: appends `'accent'` with explicit codec comment *“Appended, never reordered”* on `cubePartColors` in `src/domain/cubeEdgeState.ts`
- **Call:** **Deliberate** at each step. Expansion is only by append for compact pose indices.

### 3. Default face opacity full (identity shifted from “glass faces”)

- **Restriction / default:** faces default opaque.
- **Timeline:** `51c14ee7` set `defaultCubeFaceOpacity = 0.08`; `9786f4e6` raised it to `1` (same commit as theme colour). Later face-owner work inherits edge opacity default `1` via `cubeEdgeStateOwner.fields.opacity`.
- **Call:** **Deliberate** product look change (theme + solid faces), not a silent regression.

### 4. Scene is cube occupancy, not `CellContent`

- **Restriction:** No empty/cube/nested-grid content union on cells. Grid rebuild mints a full `CubeCell[]` (`createGridCells` in `src/domain/scene.ts`). Nested grids and interior kinds do not exist in code.
- **Doc aspiration:** `CUBICELL.md` still sketches `CellContent = empty | cube | grid`; `ARCHITECTURE.md` still names it as the intended separation.
- **Code truth:** `MODEL.v2.md` *Current model limits* lists missing `CellContent` and composition Piece-owned grids as intentional repository facts.
- **Product seal:** `de4c6a8f` / **PR #151** *docs(product): sync docs to the confinement-is-the-product orientation* — “What lives inside a cell is deliberately unanswered.”
- **Call:** **Deliberate deferral.** Documented architecture never landed as schema. Not a removed feature on `main`.

### 5. Grid format fields declared then unauthored / unhonored (align, overflow)

- **Restriction (historical):** `GridFormat` carried `align: GridAlign` and `overflow: GridOverflow` from day one of the grid.
- **Introduced:** `5f708950` *feat: add grid based cube placement* — types + defaults `center` / `allow`.
- **Honoring:** layout offset branched on align in `getAlignmentOffset` (`src/domain/gridLayout.ts`), but nothing in editor/panels authored non-default align or overflow.
- **Removal:** `783a5037` / **PR #158** *refactor(schema): remove what nothing authors, name what remains honestly* — deletes `GridAlign` / `GridOverflow` and hard-centers alignment.
- **Call:** **Declared-but-unhonored defaults, then deliberate cleanup.** Lost capability only in the sense of unused schema; never a shipped authoring path.

### 6. Buried faces culled from instances

- **Restriction:** faces fully covered by adjacency do not get instances (`buriedFaces` in `src/domain/cubeRenderResolution.ts`, skipped in `src/scene/cubeInstances.ts`).
- **Introduced:** `6f9a58c2` / **PR #51** *feat(scene): cull buried faces and resolve edge-junction contention* (domain coverage + cull PRs #48–#49 inside).
- **Call:** **Deliberate** render correctness / capacity, not a content schema wall — but it means “content on a buried face” would never draw until revealed.

### 7. Face planes only, inset off the true surface

- **Restriction:** face geometry is unit planes only (`geometryKind: "plane"` in `src/scene/instancedPartMeshCore.ts`); inset so coplanar neighbors do not z-fight.
- **Introduced:** planes from `51c14ee7`; inset `cb580b5c` *fix(scene): inset face planes so touching cubes never share a plane* (**PR #40**).
- **Call:** **Deliberate** geometry/render decision. No path for arbitrary mesh / billboard content on a face without a new part kind.

### 8. Face field schema closed through a single owner

- **Restriction:** only fields registered on `cubeFaceStateOwner` are valid, patchable, morphable, and compact-encoded. Adding content means adding a field (or a figure extension), not free-form props.
- **Introduced:** edge owner first `5f01f744` / **PR #148**; face owner `241f03ca` *refactor(domain): own cube face state* (landed under **PR #164**).
- **Call:** **Deliberate** schema discipline. Self-imposed but intentional.

### 9. First face “content”: optional stencil figure (seeded SVG only)

- **Restriction set introduced together in `c32bb726` / **PR #164** *feat(scene): render seeded SVG stencils on cube faces*:**
  1. Optional `figure` on face state (`cubeFaceStateOwner.figure`, `optional: true`).
  2. Figure payload closed: `stencilId` + `region` ∈ {form, field} + `fit` ∈ {margin, bleed} + colour role (`CubeFaceFigure` / `isCubeFaceFigure` exact key count 4).
  3. `StencilAsset.mediaType` fixed to `image/svg+xml` (`stencilMediaType` in `src/domain/stencil.ts`).
  4. **No SVG (or other) payload on the asset** — only metadata; raster source lives only in `seededStencils` (`src/domain/seededStencils.ts`).
  5. Render atlas maps **only** `seededStencils` (`getStencilAtlasSlot`); unknown ids write `noStencil` and paint nothing extra (`writeFaceStencilAttribute` in `src/scene/faceStencilShader.ts`).
  6. Fixed atlas capacity 16 (`stencilAtlasCapacity`); seed count must fit or throw at module load.
  7. Author UI: stencil enum = `none` + seeded names only; selecting a stencil copies `defaultFigure` from the seed (`faceStencilBinding` / `findFaceStencil` in `src/editor/controlBindings.ts`). **No UI to author `region` / `fit` independently.**
  8. `create-stencil-asset` can put a `StencilAsset` into `library.stencils` (`createStencilAsset` in `src/domain/workbenchOperations.ts`) and history/persistence know stencils — but **resolution and atlas still seed-only** (`resolveStencilContent` returns `unresolved` for non-seeds; tests cover that in `tests/stencilAssets.test.ts`).
- **Call:**
  - Seeded-only marks + closed figure enums + SVG-only media type: **deliberate** first slice (ship a mark language, not a general media pipeline).
  - Library asset without bytes + persist/create path that cannot paint non-seeds: **declared-but-unhonored / incomplete seam** introduced *with* the feature, not a lost older capability. Closest thing to “metadata that looks like content support but is not.”

### 10. Look system knobs (value ramp, adjacency occlusion) — not content, still face appearance walls

- **Directional face values:** `b73d57aa` / **PR #160** — face colour modulated by face id; unlit scene depth cue.
- **Adjacency occlusion:** `e1f8eed7` *feat(scene): occlude faces from the grid's own adjacency* — grid-derived corner weights darken pockets.
- **Call:** **Deliberate** look system. They constrain how authored face colour/stencil read, not what schema can store.

### 11. Typography-as-grid (richer “content”) built off main, never merged

- **What it was:** `GeometrySource = literal | text`; text evaluates to `CubeCell[]` with glyph provenance — structure-as-content, not face media (`src/domain/typography.ts` on that branch).
- **Commits:** `511205f8` *feat(typography): add deterministic text domain*, `f325d18d` *feat(typography): add interactive text composer* on `feat/typography-domain`.
- **Ancestry:** **not** an ancestor of current `main` (`git merge-base --is-ancestor 511205f8 HEAD` fails). `TYPOGRAPHY.md` on main remains a proposal doc.
- **Call:** **Not a removed mainline feature.** Parallel experiment. Confirms richer content was imagined as *cell occupancy from type*, still without interior face media.

### 12. Schema honesty pass removes unauthored layout knobs rather than adding content

- **`783a5037` / PR #158:** renames morph vocabulary; drops grid align/overflow “what nothing authors.”
- **Call:** **Deliberate.** Pattern of the codebase: prefer a smaller honest surface over dormant fields. Aligns with confinement product orientation, and against “open content bags.”

---

## Lost / dead / declared-but-unhonored inventory

| Item | Status | Evidence |
|------|--------|----------|
| `CellContent` / nested grids | Doc-only; never coded on main | `CUBICELL.md` sketch vs `MODEL.v2.md` limits; occupancy-only `scene.ts` |
| `GridAlign` / `GridOverflow` | Typed + defaulted `5f708950`; only center path used; removed `783a5037` | `grid.ts` / `gridLayout.ts` history |
| `StencilAsset` library + `create-stencil-asset` | Present; **does not carry or render mark source** | `stencil.ts` shape; seed-only atlas/resolver |
| `resolveStencilContent` unresolved branch | Live API for the gap | `seededStencils.ts`; tests assert unresolved |
| Figure `region` / `fit` | In domain + shader; not independently authorable in editor | set only via seeded `defaultFigure` on stencil pick |
| Typography domain | Built off-branch; not on main | `feat/typography-domain` only |
| Free face media (raster, video, arbitrary SVG upload) | Never existed | No historical fields in `git log -S` for face textures/images beyond #164 |

Nothing in main history shows a richer *face content* system that was built and then stripped. The pattern is: minimal style → closed colour roles → look knobs → sealed seeded stencils, with docs and one library seam *naming* more than the engine honors.

---

## Hypothesis assessment

**“We built a layout engine that does not support content” — confirmed.**

1. **Layout engine, yes:** grid format (cellSize, gap, gapOverrides, origin), placement home/offset/rotation/scale, occupancy of cubes, instanced face/edge planes, burial and junction resolution.
2. **Content support, no (beyond sealed marks):** face payload is style roles + optional seeded SVG figure. Cell interiors are product-deferred. `CellContent` never shipped. Stencil *library* looks like an asset pipeline but stores no payload and cannot paint anything outside the seed table.
3. **Self-imposed, mostly intentional:** confinement product docs (#151), append-only colour codec (#163), face state owner, PR #158 honesty, PR #164 seeded first slice. The accidental-feeling hole is the stencil asset/create path without source or atlas registration — a seam left half-open, not a once-full feature gutted.

**Implication for richer face content:** any real content path must (a) put payload somewhere the renderer can load, (b) register into the atlas (or replace the fixed seed map), (c) extend or replace the closed figure/colour enums under the part-state owner, and (d) decide whether “content” means face marks, cell interiors (`CellContent`), or structure-as-type (typography branch). The layout engine does not currently block those extensions by accident so much as it was never built to host them.

---

## Key SHAs (quick index)

| SHA | What |
|-----|------|
| `51c14ee7` | Face/edge model; plane faces; style-only face state |
| `5f708950` | Grid placement; `GridAlign`/`GridOverflow` declared |
| `9786f4e6` | Theme colour; face opacity default → 1 |
| `cb580b5c` | Face plane inset (#40) |
| `6f9a58c2` | Buried face cull (#51) |
| `5f01f744` | Edge field owner (#148) |
| `de4c6a8f` | Confinement / interiors unanswered docs (#151) |
| `783a5037` | Remove unauthored grid align/overflow (#158) |
| `b73d57aa` | Directional face values (#160) |
| `e1f8eed7` | Adjacency face occlusion |
| `7d5e942e` | Accent colour role (#163) |
| `241f03ca` | Own cube face state (into #164) |
| `c32bb726` | Seeded SVG stencils on faces (#164) |
| `511205f8` | Typography domain (branch only; not main) |

