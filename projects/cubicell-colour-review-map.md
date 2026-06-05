# Review: 408b2687 feat: add accent cube colour

Sourced from `git show 408b2687:<path>` blobs per orchestrator correction. Gates run on a pristine `git archive 408b2687` extraction in the reviewer scratchpad, not the shared worktree: `tsc -b --force` exit 0; unit suite 3 runs: 2603/2609 then 2609/2609 twice. The six run-1 failures (cameraTrackMount, cameraTrackPlayback, cubeInstanceSlots bound, incrementalCubeRenderResolution bound) are timing-shaped, never reproduced, and are not colour logic; earlier failures I observed in the shared worktree were the sanctioned controlled-red probes and are void as evidence.

## 1. Deleted guards, adjudicated one by one

tests/instances.test.ts:

- Deleted test `white artifact faces keep an unmistakable three-plane value step`. Invariant: the #160 face ramp applies on the ARTIFACT polarity. That is precisely the ungated behaviour this commit exists to kill; the assertion encoded the defect. CORRECT DEATH. Its successor invariant (artifact faces faithful to authored colour) is guarded by the updated exact-equality assertion in `tests/thumbnailArtifact.test.ts:reuses authored face and edge instances without editor chrome` (front face === unshifted `scenePolarities.black.contrast`).
- Within the deleted test, sub-invariant `bottom < right` ordering: still guarded by `values[side] > values.bottom` in the surviving `face meshes resolve a distinct value for every orientation`.
- Within the deleted test, sub-invariant absolute magnitude bands (front 0.76–0.84, right 0.62–0.72): SILENTLY DROPPED. No surviving test pins the delta magnitudes; see finding below.
- Modified expectation in `face meshes resolve a distinct value for every orientation`: now computes expected colour from `workbenchScenePolarities.black.faceLightnessDeltaById?.[faceId] ?? 0`, the same field the implementation reads — self-referential. Mitigation: the test's independent assertions (6 distinct values, top > sides > bottom) DO fail if the ramp vanishes from workbench configs, so ramp presence and shape remain guarded; only magnitudes are not.

tests/thumbnailArtifact.test.ts:

- Removed shifted-colour expectation and the `shiftLightnessForContrast` / `cubeFaceLightnessDeltaById` imports. Invariant: thumbnails carry the face ramp — old behaviour, CORRECT DEATH. Replaced in place by the new fidelity invariant (exact authored colour), which is the guard my scout map required for the export/thumbnail path.

Net: 2 assertions correctly died with the behaviour they encoded, 2 sub-invariants transferred to surviving symbols, 1 sub-invariant (magnitude bands) silently dropped. The five added guards match my map's plan step 4: resolver-per-polarity (`tests/editorAdapters.test.ts:accent follows polarity...`), options derivation (`tests/panels.test.tsx:options cover every cube part color`), accent codec round trip face+edge (`tests/cubeEdgeStatePropagation.test.ts`), tween samples (`tests/colorSpace.test.ts:black to accent...`), thumbnail fidelity (above).

## 2. Map deviation

None found. Vocabulary bound to `cubeEdgeState.ts:cubePartColors` (append-only comment kept); role→hex stayed inside `scenePolarity.ts:resolveCubePartColor`, body untouched, and `ScenePartColors = Record<Exclude<CubePartColor, "theme">, string>` keeps the map total so a fifth member fails closed again; no parallel resolve path, no second writer to `partColors` (single construction site in `createPolarityConfig`). The one-file shortcut I warned against (keying the face gate off `edgeLightnessDelta` presence) was NOT taken: the gate is the two-file shape, `ScenePolarityConfig.faceLightnessDeltaById` on workbench configs read via `context.polarity` in `instancedPartMeshCore.ts:resolveInstanceColor`, and `rg cubeFaceLightnessDeltaById` shows no remaining direct consumer. Both escalated decisions were taken and recorded in test names: accent flips per polarity (`accentOnLight: "#1c0c43"`, the visual report's dark rail) and the workbench reuses the artifact rails.

## 3. Derivation is real

`git show 408b2687:src/editor/controlBindings.ts` shows `partColorOptions = cubePartColors.map((value) => ({ label: ..., value }))` — derived, not hand-listed, and `tests/panels.test.tsx` asserts the options array equals `cubePartColors` for all three bindings, so a fifth role cannot blank the control again.

## Findings

- Minor — tests/instances.test.ts:`face meshes resolve a distinct value for every orientation`: the per-face expectation is self-referential (`faceLightnessDeltaById?.[faceId] ?? 0`) and the deleted magnitude bands were not re-pinned, so a silent change to the workbench delta values (e.g. all deltas to 0.01) passes distinctness and ordering. If the magnitudes are considered feel knobs this is acceptable; if they are contract, pin them against `cubeFaceLightnessDeltaById` values in one assertion.
- Note, no action: run-1 flakes above are pre-existing timing sensitivity (camera waitFor, perf bounds on cold cache), also seen once against the mutated shared worktree; not attributable to this commit.
