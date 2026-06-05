# Accent Colour Slice: Reuse Map

Scope: worktree feat/accent-colour, base main 7293438, with the uncommitted probe in tree (`accent` appended to cubePartColors; `accent: "#c0fac0"` in themeTokens). All claims below are against that tree. Evidence labels: MEASURED means a command was run and its output observed; READ means classified from source.

## Reuse Map

### 1. Consumer enumeration (CubePartColor / cubePartColors)

Measured baseline: `pnpm exec tsc -b --force` produces exactly one error; `pnpm test` (unit project) passes 187 files / 2605 tests with the probe in tree. So the compiler catches one consumer and the test suite catches zero. `pnpm test` does not typecheck; a green unit run proves nothing about this slice.

FAILS CLOSED (1):

- `src/theme/scenePolarity.ts:resolveCubePartColor` — TS7053: `ScenePartColors` is `Record<"black" | "white", string>` and cannot be indexed by `"accent"`. MEASURED (sole tsc error, exit 2). Were it suppressed, an accent part would resolve to `undefined` and `three` `Color.set(undefined)` at `src/scene/instancedPartMeshCore.ts:writeColor`.

FAILS OPEN (1):

- `src/editor/controlBindings.ts:partColorOptions` — hand-synced `Theme/Black/White` list feeding `cubeColorBinding`, `faceColorBinding`, `edgeColorBinding`, rendered by `src/panels/ControlBindingField.tsx:ControlBindingField` through `src/components/ui/segmented/Segmented.tsx:Segmented`. Accent is unauthorable from the UI, and an accent value already in state renders a control with no pressed option (`aria-pressed={option.value === value}` matches nothing). MEASURED that no test notices (full unit suite green). This is the second membership owner the fable5 guardrails warn about; step 2 of the plan deletes it.

EXHAUSTIVE-SAFE (everything else; READ, plus suite green as weak corroboration):

- `src/domain/cubeEdgeState.ts:cubeEdgeStateOwner` color field — `encode`/`decode`/`isEncoded` all derive from the `cubePartColors` array (`indexOf`, index lookup, `isIndex(value, cubePartColors.length)`); appending widens them automatically.
- `src/persistence/recordCodecs/compactPose.ts:encodeCell` / `decodeCell` / `isCompactFace` — same derivation for faces. See Persistence.
- `src/state/workbenchValidation/pose.ts:isFaceState` and `src/state/authoredOperationValidation/scene.ts:isCubeOperation` / `isPartPatch` — delegate to `isCubePartColor`, which iterates the array.
- `src/domain/cube.ts:getCubeUniformPartColor`, `CubeFaceState`, `setAllCubeFacesState`; `src/domain/cubeOperations.ts` set-cube-color; `src/domain/cubeCellOperations.ts:applyCubeOperationToCell`; `src/domain/cubeGeometry.ts` colour fields — value-agnostic carriers or Set/equality logic.
- `src/domain/edgeClaimResolution.ts` (`claim.state.color !== defaultCubePartColor`) — accent correctly counts as authored style.
- `src/domain/selectionAspects.ts:faceStateDistance` — exact colour equality, no distance.
- `src/evaluation/sceneMorph.ts:collectPartColorTweens`, `src/evaluation/scoreAt.ts:PartColorTween`, `src/evaluation/sharedEdgeTweens.ts:planSharedEdgeTweens` — label carriers; tween exists iff `from !== to`. See Transitions.
- `src/scene/colorSpace.ts:resolvePartColor` / `resolveLerpedPartColor`; `src/scene/instancedPartMeshCore.ts:resolveInstanceColor`; `src/scene/cubeInstances.ts` and `src/scene/instanceSlotRegistry.ts:changedAttributes` — equality-based or strictly downstream of the resolver; total once the resolver is total.

No hidden value switches exist: `rg '=== "black"|=== "white"|=== "theme"|case "black"|case "white"|case "theme"'` across src hits only the resolver's `theme` branch (part colour) and `ScenePolarity` checks (a different enum).

### 2. Resolution path

Role → hex is owned by `src/theme/scenePolarity.ts:resolveCubePartColor`: `theme` → `polarity.contrast`, else `polarity.partColors[color]`. The polarity tables are `scenePolarities` (artifact family, `artifactPartColors`) and `workbenchScenePolarities` (workbench family, `workbenchPartColors`), both built by `createPolarityConfig`. The accent hooks in by widening `ScenePartColors` to include `accent` and adding an entry to both family maps. No new branch in the resolver, no parallel path, no default case; keeping the map total is what preserves the fail-closed property for the next member.

Open resolution decision the builder must not guess (see Plan): `artifactPartColors` is one object shared by both polarities, so a single accent hex renders `#c0fac0` (OKLab L 0.93) on the white polarity's `#ffffff` background at roughly 1.2:1 — invisible. The visual report defines two rails (light `#c0fac0` h145, dark `#1c0c43` h290); resolving accent to the rail opposite the background requires per-polarity part colour maps, a shape change to `artifactPartColors` / `workbenchPartColors` ownership.

### 3. Persistence

No wire version bump. Faces: `encodeCell` stores `cubePartColors.indexOf(face.color)`, `isCompactFace` guards with `isIndex(value[1], cubePartColors.length)`, `decodeCell` reads `cubePartColors[color]`. Edges: identical pattern inside `cubeEdgeStateOwner`. Appending a fourth member leaves every persisted index 0–2 decoding to the same label and makes index 3 valid; the wire shape is unchanged, so nothing needs the bump-and-reset rule (`authoredOperationSchemaVersion`, `indexedDbProjectStorageVersion` untouched). The probe's append-only comment on `cubePartColors` is the load-bearing contract that keeps this true; keep it, and its wording is fine.

### 4. Transitions — MEASURED

Probe (vitest, run against `src/scene/colorSpace.ts`, 2/2 passing; runtime-extended polarity config since types are erased):

- `resolveLerpedPartColor(black → accent)` at progress 0/.25/.5/.75/1 produced five distinct monotone samples: the OKLab lerp accepts an accent endpoint with no code change.
- `shiftLightnessForContrast(#c0fac0, 0.12)` moves lightness and preserves chroma, so accent survives the workbench edge/form shift.

Tween creation is value-agnostic (READ): `src/evaluation/sceneMorph.ts:collectPartColorTweens` emits a `PartColorTween` whenever labels differ, and `src/evaluation/sharedEdgeTweens.ts:SharedEdgeTween` carries the same labels. So black→accent and accent→white transitions ride the existing path for free. The reviewer's dispute of the free-lunch claim stands only for the case it named: re-valuing the hex behind an unchanged `accent` label is invisible to the label-diff classifier. That case is out of scope for this slice (one fixed accent per polarity family) but binds any future keyframe-palette work.

### 5. Grooming that rides along

- `src/theme/scenePolarity.ts:cubeFaceLightnessDeltaById` is applied unconditionally for faces in `src/scene/instancedPartMeshCore.ts:resolveInstanceColor`, so the artifact preview and thumbnails mutate authored face colours today. `edgeLightnessDelta` shows the correct gate: an optional `ScenePolarityConfig` field present only on the workbench configs, read in `createColorWriteContext`. Matching that gate is NOT a one-file change done cleanly: carry the face delta on `ScenePolarityConfig` (workbench configs only) and read it from `polarity` in `resolveInstanceColor`, dropping the direct import — two files, roughly 15 lines. The one-file shortcut (gate faces on `polarity.edgeLightnessDelta !== undefined`) couples two knobs and should be rejected.
- Paths that must show accent faithfully: `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` + `src/thumbnail/thumbnailRenderer.ts` (both `scenePolarities`), and the `previewing` branch of `src/studios/editor/EditorStudio.tsx` (also `scenePolarities`), which is the canvas `src/export/streamRecorder.ts` records via display capture. Gating the face ramp fixes all three at once because they share `resolveInstanceColor`.

### Token judgment

`#c0fac0` matches the adjudicated light rail exactly (h145, cusp-normalised C 0.097, L 0.93 per the visual report's rail table), and the guaranteed worst-pair contrast 14.3:1 quoted in the token comment is the visual report's measured floor. Value and comment are right for the black polarity. What the token table is missing is the white-polarity counterpart (dark rail `#1c0c43`) and a decision on a workbench variant: black/white carry workbench remaps (`workbenchBlack`/`workbenchWhite`) but the visual report states the workbench can carry rail chroma at zero contrast cost, so `accent` may serve both families unchanged. Decision, not defect.

### Existing infra / rejected / none found

- Existing infra: everything in the prior scout map (`~/.mdx/projects/cubicell-colour-scout.md`) holds at this SHA; this map narrows it to the accent slice rather than restating it.
- Similar checked and rejected: a resolver default branch (`partColors[color] ?? contrast`) — would convert the one fail-closed consumer into a silent fallback, the exact defect class this brief forbids.
- None found: no value-conditional switches on `CubePartColor` outside the resolver (search above); no existing guard test over resolver totality or codec round-trip of the colour index (searched `rg -l "cubePartColors|resolveCubePartColor" tests/` mentally via suite run — the green suite with a red build is the proof); no CSS twin needed for accent yet (chrome swatches, if built, can import `themeColorTokens` directly).

## Quality Map

- Duplication: `partColorOptions` is a second membership owner for the colour vocabulary. Consolidate by deriving options from `cubePartColors` with a label map; this is the single ride-along both prior consensus rounds already approved.
- Boundary: `ScenePartColors` widening must stay total (no optional accent, no fallback) so the next appended member fails closed again.
- Boundary: per-polarity accent resolution, if chosen, moves `artifactPartColors` from one shared object to per-polarity maps; that is a shape change inside `scenePolarity.ts` only.
- Test gap (measured): the unit gate passes with a red build. The slice should land a resolver totality test (`cubePartColors.every(color => resolveCubePartColor(color, config))` over all four polarity configs) so this defect class is caught by tests, not only by `tsc -b`.
- Grooming recommendation: gate `cubeFaceLightnessDeltaById` to workbench inside this slice (consensus F already requires it; export fidelity is a precondition for judging accent, and the fix shares the accent's own file surface).

## Plan

Decision needed (owner): does accent flip with polarity — light rail `#c0fac0` on the black background, dark rail `#1c0c43` on the white background — or stay one fixed hex and accept ~1.2:1 on white? The rail system in the visual report implies flip; the code shape supports either. Second, smaller: does the workbench family reuse the artifact accent hex (visual report says it can) or carry a remapped variant like black/white do?

Steps, each bound to the map:

1. Widen `ScenePartColors` and add `accent` to both family maps in `src/theme/scenePolarity.ts` (per the polarity decision). This clears the sole compile error; the resolver body does not change.
2. Derive `partColorOptions` from `cubePartColors` in `src/editor/controlBindings.ts` (labels as UI metadata), adding the Accent option to all three bindings for free and deleting the fail-open list.
3. Gate the face ramp: move `cubeFaceLightnessDeltaById` behind an optional `ScenePolarityConfig` field on workbench configs; read it from `polarity` in `resolveInstanceColor` (two files).
4. Tests: resolver totality over all four polarity configs; compact pose round-trip of an accent face and accent edge (index 3); a black→accent tween sample test (port of the probe); an artifact-path fidelity test asserting a face's resolved colour equals its token with no lightness shift (guards step 3, and would have caught the #160 regression).
5. Gates: `pnpm exec tsc -b --force` (the only current gate that sees this slice), `pnpm test`, then the live UX gate before merge per standing rule.

Not looked at: e2e/browser suites (none run), bundle budget impact (none expected; no new dependency), and `Segmented` swatch rendering design (UX report covers it; no code inspected beyond selected-state logic).
