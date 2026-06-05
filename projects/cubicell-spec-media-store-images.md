# Cubicell spec 3/4 — payload store, RGBA media atlas, images

Spec only, no code. Base: main @ 3725921. Citations `file:symbol`. Binding inputs: the reuse map in `~/.mdx/projects/cubicell-content-scout-synthesis.md`; STORAGE.md (the durable-persistence authority — this spec adds to it, never re-specs it); the F1 decision (dynamic RGBA atlas, one-draw intact, cm 2026-08-09); the content union spec `~/.mdx/projects/cubicell-spec-content-union.md` (referenced by name, may be in flight). No migrations: every wire change bumps its version and resets.

Correction to the brief's premise: project persistence is no longer JSON-in-localStorage. It is IndexedDB behind `src/persistence/storagePort.ts:ProjectStoragePort` with atomic promotion (`src/persistence/promoteContract.ts:createPromotePlan`, `src/persistence/indexedDbCommit.ts:issuePromoteWrites`), and quota failure already rolls back and surfaces as a blocking save failure (`src/state/projectDurabilitySaveState.ts:failureSaveState`, `src/app/PersistenceStatus.tsx:PersistenceStatus`, proven in `tests/indexedDbStorage.browser.test.ts` and `tests/cubicellStoreBrowserDriver.ts:runQuotaStoreRecovery`). IndexedDB stores Blobs natively. The payload store is therefore an extension of the existing transaction machinery, not a new storage system. What remains true from the brief: authored operation bodies must stay JSON safe (STORAGE.md, Authored operation contract), so image bytes can never ride an operation — that is the gap the payload store closes.

## 1. Payload store

**Domain.** A payload is immutable project-scoped binary content, identified by `payloadId` (UUIDv4 per STORAGE.md, Durable identity) and verified by `contentHash` (SHA-256 of the bytes). One payload record: `{ payloadId, projectId, mediaType, byteLength, contentHash, bytes: Blob }`. Payloads carry no authored meaning; assets reference them. This matches the STORAGE.md Binary output row (hosted home: Supabase Storage; the Postgres metadata boundary there already names media type, byte length, and content hash — the local record mirrors those fields so phase-2 sync is a transport problem, not a remodel).

**Schema.** Add a `payloads` object store, keyPath `["projectId", "payloadId"]`, to `src/persistence/indexedDbSchema.ts:createIndexedDbProjectSchema` and `indexedDbProjectStoreNames`; bump `indexedDbProjectStorageVersion`. The constant is 9 on main today; spec 1 lands 9 → 10, and this slice builds on that landing, bumping 10 → 11 (if the slices combine into one release, one combined bump is fine — the rule is one coherent chain, never parallel claims on the same version). The destructive upgrade resets, per the pre-release rule. Update the STORAGE.md Local persistence store list in the same PR.

**Write path.** Payload writes join the existing durability unit; no second writer, no side channel:

- Import stages the payload (bytes held in memory or a draft row) and dispatches the create-asset operation through the single authored funnel (`src/state/actions/authoredReducer.ts`).
- `createPromotePlan` gains payload validation: every payload referenced by a promoted asset must be present in the plan or already committed; a plan referencing a missing payload fails before any write.
- `issuePromoteWrites` writes payload rows in the same IndexedDB transaction as project, assets, and outbox. A quota failure aborts the whole transaction, preserves the committed baseline, and reports through `failureSaveState` — the existing loud path, now covering media-sized writes.
- `ProjectStoragePort` gains `loadPayload(projectId, payloadId)` (and inclusion of payloads in project deletion). Hydration (`src/persistence/projectRecordHydration.ts:hydrateProjectRecords`) validates that every image asset's `payloadId` resolves and that `contentHash` matches; a dangling reference rejects the asset record the same way other integrity checks do.

**Quota made loud, earlier.** The save-time path is already loud. Add the import-time guard: before staging, check `navigator.storage.estimate()` (nowhere used yet — searched `storage.estimate`, `navigator.storage` across src/ and tests/, zero hits) and enforce a per-payload byte cap (implementation picks the number; it is a config knob, not a hardcoded literal, per surface-feel precedent). Oversized or quota-threatened imports fail at the picker with a user-facing message instead of poisoning the next promotion.

**Retention.** Payloads are append-only in this slice. `delete-image-asset` leaves the payload; mark-and-sweep across durable roots is the retention work already ledgered in `~/.mdx/projects/cubicell-audit-durable-core.md` (Durable retention TAX) and stays deferred. Record byte totals per store so the policy is measured when it comes.

## 2. Image asset and import op

Mirror the stencil precedent exactly; it is the asset-pipeline path of least resistance.

- `src/domain/image.ts:ImageAsset`: `{ id: ImageId, kind: "image", name, mediaType: "image/png" | "image/jpeg" | "image/webp", byteLength, contentHash, payloadId, width, height }`. Sibling of `src/domain/stencil.ts:StencilAsset`, which stays as-is (SVG stencils remain source-in-record; they are text).
- `ImageDocumentOperation` in `src/domain/workbenchOperations.ts`: `create-image-asset` (carries the full asset; ids minted before the reducer per STORAGE.md) and `delete-image-asset`, mirroring `workbenchOperations.ts:StencilDocumentOperation`. Reducer through `workbenchOperations.ts:applyDocumentOperation`; validation beside `src/state/workbenchValidation/assets.ts:readStencils` as `readImages`; roster via `src/domain/workbench.ts:Library` and `getProjectAssetRoster`.
- `src/persistence/recordCodecs/imageRecordCodec.ts` over `simpleAssetRecordCodec.ts:encodeSimpleAssetRecord`/`decodeSimpleAssetRecord`, `imageRecordSchemaVersion = 1`, registered wherever `stencilRecordCodec` is (projection, hydration, preparation, validation — the fan-out the audit's codec-registry GROOM wants centralized; if that registry lands first, register there instead).
- Import flow: file picker → `createImageBitmap` decode (also yields width/height; enforce a max source dimension config knob, downscaling on import rather than rejecting) → hash → stage payload → dispatch `create-image-asset`. One user action, one durability unit, one loud failure point.

**Requirements on `CubicellContent`** (the union is owned by spec-1; this spec lists intake only):

- An `image` member carrying `imageAssetId` (asset reference — never `payloadId`, never bytes, never atlas slots; resolution is renderer-side). That reference is the only field this spec requires.
- Image presentation policy (contain/cover, optional focal point, tinting) is open intake in spec 1 §12, defined there after image review; this spec neither requires nor names presentation fields.
- A stable wire discriminant for the `image` member in the `compactPose.ts:encodeCell` cell tuple's content position; version bump and reset.
- Every variant must admit a deterministic poster derivation (section 4 depends on it).

## 3. RGBA media atlas

- `src/scene/mediaAtlas.ts:createMediaAtlas`: RGBA8 `DataTexture`, same geometry as the stencil atlas (`stencilAtlas.ts:stencilAtlasSize` 2048, 512px slots, capacity 16, gutter 1 — share these constants, do not redeclare), ~16 MiB GPU per context, no mipmaps. If extraction of a shared atlas primitive from `stencilAtlas.ts:createStencilAtlas` keeps both owners under one lifecycle implementation, do it (media-sol's "shared atlas primitive" note); otherwise mirror and note the debt.
- **Dynamic slot allocator**, the deliberate divergence from the seeded map behind `stencilAtlas.ts:getStencilAtlasSlot`: slots keyed by `imageAssetId`, allocated on first use, freed on asset delete. At capacity, allocation fails loudly to the authoring surface (picker disables/explains); eviction policy is deferred until a real project hits 16 concurrent images. The allocator's slot-rect API is shared with the motion path: F1's per-frame `copyTextureToTexture` writes into a slot of this same atlas, so the allocator must not assume slots are write-once (spec 4/4 consumes this).
- Upload: `loadPayload` → `createImageBitmap` → draw into slot region → partial texture update. Async readiness follows `src/scene/CubeScene.tsx:StencilAtlasReadyDriver`; ownership follows `CubeScene.tsx:useOwnedStencilAtlas`.
- Shader: extend the one composed patch `src/scene/faceStencilShader.ts:applyFaceStencilShader` — one new sampler, a media-mode selector in the packed code word written by `faceStencilShader.ts:writeFaceStencilAttribute` (headroom exists above bit 6), neutral 1×1 fallback bound when unused. One new fixed program key (`cubicell-face-media-v1` per `LESSONS.md` fixed-key rule). Zero draw growth, zero program creation on content edits — same invariants the current gate asserts.
- Instance writes stay in the single GPU writer chain: `src/scene/cubeInstances.ts:createCubeCellInstances` → `src/scene/instancedPartMeshCore.ts:syncInstancedPartMesh`/`patchInstancedPartMesh`. No second writer.

## 4. Poster and thumbnail parity

`src/thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer` owns its own context and atlas; the media atlas must be mirrored there through `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact`, sharing decoded CPU bytes where possible (GPU allocations cannot cross contexts). An image's poster is the image itself; the parity requirement is that a face bearing an image renders identically in thumbnails, enforced by the gate below, not by convention.

## 5. Delivery budget

New `capabilityIncrements` entry `media` in `budgets/initial-delivery.json`: root `src/capabilities/media/MediaCapability.tsx`, `baselineRoots` identical to the motion/recording/thumbnails precedent. Ownership: `capabilitySourceRules` rows for `src/capabilities/media/` and `src/media/` (import UI, decode, hashing live lazy under the capability). The atlas, shader extension, and allocator are shared-renderer code; their byte cost lands inside the existing `shared-renderer` ceiling and the cap for the increment is set from measured output at implementation time (media-sol: rebaseline only to measured), gated by `scripts/check-delivery-budget.mjs`.

## 6. Tests and gates

All gates pass/fail with controlled-red proofs (break the invariant once, watch the gate go red, restore).

- **Browser render gate**: sibling of `tests/stencilRenderingBrowserDriver.ts:runStencilRenderingBrowserGate` proving an imported image (real bytes through payload store → asset op → atlas → face) renders on a face via pixel readback, in both the live scene and a thumbnail artifact.
- **Resource observer** (`tests/webGlResourceObserver.ts:observeWebGlResources`): unchanged draw count per populated face bucket, zero program creation on image assign/edit, exactly one new texture per context (the media atlas), exact partial upload ranges, full disposal.
- **Quota**: extend the `runQuotaStoreRecovery` pattern with a payload-sized write — promotion fails, baseline intact, `failureSaveState` surfaced, recovery after restart. Plus an import-time cap rejection test.
- **Integrity**: codec round-trip for `imageRecordCodec`; hydration rejects a dangling `payloadId` and a `contentHash` mismatch; promote plan rejects a missing referenced payload.
- **Budget**: delivery gate green with the `media` entry; renderer ownership gate green.

## Out of scope

Video/motion playback (spec 4/4, rides the F1 decision and this atlas's slot API); hosted payload sync (STORAGE.md phase 2, Supabase Storage boundary already specified); payload garbage collection (audit retention TAX); atlas slot eviction beyond loud capacity failure; the `CubicellContent` union itself (spec-1).

## Completion

This slice is complete when an image imported through the picker persists as a payload in IndexedDB, survives reload with its content hash verified, and renders on a cube face and in that face's thumbnail through the RGBA media atlas with zero draw-call and zero program growth — with every gate in §6 green and its controlled-red proof recorded.
