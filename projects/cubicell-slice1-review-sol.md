# Cubicell Slice 1 Review

## Scope

- Target: `19cecbdb27203e9996da1010e59764c063436fef`
- Parent: `3725921ae23cd4088b3891b310889c8861ca05eb`
- Branch: `face-media`
- Lens: read only adversarial review
- Checkout status at final inspection: clean

No source, test, configuration, build output, or dependency file was changed. No build or test command was run. The existing delivery artifacts were inspected with the read only budget checker.

## Findings

### High: atlas capacity is allocated from authored state instead of rendered state

`src/scene/stencilAtlas.ts:collectReferencedStencilIds` walks every face of every authored cell. Live synchronization passes `scene.cells` directly from `src/scene/CubeScene.tsx:useOwnedStencilAtlas`. Thumbnail synchronization does the same with `pose.cells`.

The renderer separately removes hidden cells, invisible faces, buried faces, selection filtered cells, and Moment presence zero cells before it creates instance buckets. The atlas collector does not share that derivation. Sixteen nonrendered stencil IDs can therefore consume every slot and force a visible seventeenth ID into overflow.

This violates sections 8 and 13, which define the atlas as a cache of active rendered references. It also creates a second derivation of render eligibility.

### High: Library removal leaves resolved GPU content stale

`src/scene/stencilAtlas.ts:createStencilAtlas.sync` removes inactive IDs from `slotByStencilId` and `written`, but removal does not set `coverageChanged`. Subscribers are notified only after newly rasterized coverage changes.

`src/scene/CubeScene.tsx:useOwnedStencilAtlas` advances `contentGeneration` only through that subscription. An asset only Library deletion therefore causes no content attribute replay. The existing GPU attribute retains the prior slot code and continues sampling the old pixels. A syntactically valid unresolved reference can keep painting after its Library asset is gone.

This violates the required unresolved base face behavior and the completion replay contract.

### High: a pending raster job can be reused for the wrong slot generation

`src/scene/stencilAtlas.ts:startRasterJob` closes over one slot. `pendingJobs` is keyed only by stencil ID, and `sync` reuses that Promise without checking its slot or generation.

Race:

1. A starts rasterizing in slot 0.
2. B replaces A and receives slot 0.
3. A returns before its first job settles and receives slot 1.
4. The current synchronization reuses A's slot 0 Promise.
5. The old job sees that A now owns slot 1 and skips its write.
6. The current `ready` Promise resolves without starting a slot 1 raster.

A remains empty until another synchronization occurs. The committed stale generation browser case covers two IDs replacing one slot. It does not cover reintroduction at a different slot.

### High: atlas completion rewrites unrelated GPU attributes

`src/scene/InstancedPartMesh.tsx:InstancedPartMesh` calls `syncInstancedPartMesh` whenever `contentGeneration` changes. That full synchronization rewrites matrices, base colours, opacity, and content across the bucket.

On first use of a new stencil, the layout effect initially writes an unresolved content value. The passive atlas effect later rasterizes the asset and advances `contentGeneration`, which forces the full synchronization. The browser proof synchronizes the atlas before applying a direct content patch, so it does not exercise the production replay chain.

Sections 8, 9, and 14 require atlas completion to replay content while identities remain stable, and require a content only mutation to upload exactly four floats with no unrelated instance data.

### Medium: same ID asset replacement retains stale coverage

`src/scene/stencilAtlas.ts:createStencilAtlas.sync` considers an ID complete when `written` contains it. Asset identity and `sourceRegion` are absent from that cache key. Replacing a Library asset with the same source digest and a corrected `sourceRegion` skips rasterization and retains the prior polarity. A pending job for the prior asset is also reused by ID.

`sourceRegion` is separate from the source digest, so this replacement can be valid. The thumbnail cache notices the new asset object, but its shared atlas still serves the old pixels.

### Medium: accepted Stencil records do not bind the ID to the source digest

`src/state/workbenchValidation/assets.ts:isStencilAsset` validates the ID shape and exact source byte length. It never verifies `createStencilId(source) === id`.

The nonseeded fixture in `tests/stencilAssets.test.ts:generatedAsset` deliberately uses a fixed digest unrelated to its SVG and passes validation, projection, hydration, and resolution. Distinct sources can therefore claim the same content address, which undermines Library deduplication, restoration, atlas identity, and thumbnail cache identity.

Section 14 requires source digest equality and a nonseeded proof built from the exact source.

### Medium: the domain barrel still pulls SVG seed sources into shared runtime delivery

`src/domain/index.ts` runtime reexports `helioyStencilId` and `manicureStencilId` from `src/domain/seededStencils.ts`. That module imports both raw SVG files. The existing emitted module graph retains the chain from shared renderer code through the domain barrel into the seed source chunk.

Section 7 requires source bearing seed values to remain out of the barrel and keeps the seed catalog on the editor authoring path. The scene and thumbnail files have no direct seed catalog import, but the barrel preserves the runtime dependency.

### Medium: the required persisted nonseeded thumbnail path has no executable proof

`tests/stencilAssets.test.ts` commits and reopens only the seeded assets. Its nonseeded test stops after in process projection and hydration. `tests/thumbnailRenderer.test.ts` renders a separate in memory nonseeded Library asset.

No test commits a nonseeded asset, reopens storage, resolves the reopened Library entry, then renders its thumbnail. Sections 14 and 17 require that connected path.

### Medium: canonical source region normalization lacks pixel proof

The unit tests inspect the packed face content region and bypass Canvas rasterization. Every generated browser asset uses `sourceRegion: "form"`. No pixel assertion exercises `sourceRegion: "field"` and verifies the inversion in `src/scene/stencilAtlas.ts:startRasterJob`.

Removing or reversing production normalization would leave the current suite green, contrary to the explicit face render and Chromium proof requirements.

### Low: morph integration proof covers only one structural cut

`tests/sceneMorph.test.ts` proves stable colour tweening and a region cut. It does not exercise stencil ID, appearance, or disappearance through `prepareSceneMorph` and `sampleSceneMorph`. Lower level owner tests cover those classifications, but section 14 explicitly requires morph tests for every structural cut.

## Clean checks

- The authored funnel remains on the existing command, reducer, and atomic history owners.
- `syncInstancedPartMesh` and `patchInstancedPartMesh` remain the sole production attribute writers.
- Scene and thumbnail resolution use the Library resolver and have no direct seed catalog import.
- Figure and fit production symbols are removed.
- Compact storage and schema versions match the specification table, including IndexedDB 10.
- The content union, compact discriminant, sparse clear behavior, and future extension boundary are sound.
- `stencilContentRegions` in `stencil.ts`, reexported by `content.ts`, is the correct cycle avoiding owner.
- The thumbnail key uses Pose identity plus the resolved referenced asset subset. Unrelated Library edits do not invalidate the entry.
- Changed delivery ceilings equal the inspected emitted closures with zero headroom. The module graph check passed with 982 default cold closure modules, 848 renderer modules, and 356 editor modules.
- No touched file violates the line thresholds.
- `git diff --check` is clean.

