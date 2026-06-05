# Cubicell slice 3 adversarial review

Target: `050c14dff57b17c503825a50081945dd718ffe87`

Parent: `708b34d8316412db87740517661badea49abf90c`

Verdict: issues found.

The target remained exact and the `face-media` worktree remained clean through the final check. `git diff --check` passed.

## Findings

### Major: the picker creates two durability units

[`FaceImageField.importFile`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/src/panels/FaceImageField.tsx#L30-L51) dispatches `create-image-asset`, then calls `setValue` for the face assignment. The history batch only combines undo history. Each dispatch independently reserves durability and independently enqueues a commit in [`createAuthoredDispatcher`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/src/state/actions/authoredDispatcher.ts#L56-L58), [`createAuthoredDispatcher`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/src/state/actions/authoredDispatcher.ts#L114-L128).

The first commit can promote the asset and payload while the second reservation or commit fails. The specification requires one user action, one durability unit, and one loud failure point. Asset creation and face assignment need one authored operation or another existing atomic owner.

### Major: atlas capacity fails silently in the authoring surface

[`FaceImageField`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/src/panels/FaceImageField.tsx#L59-L84) disables controls only for an empty Library or an active import. It has no capacity state. [`createStencilAtlas.sync`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/src/scene/stencilAtlas.ts#L311-L358) marks the seventeenth referenced image unplaceable, writes a console warning, and renders the base face.

The specification requires allocation failure to reach the authoring surface with a disabled control and explanation. A Library count is not a valid proxy, but silent fallback is also outside the contract. The atlas owner needs to expose the live referenced capacity through an existing state path.

### Major: the delivery gate is red

The new media capability ceiling in [`initial-delivery.json`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/budgets/initial-delivery.json#L84-L99) is a valid completion of a new entry. Its measured gzip size is exactly 999 bytes, so this is not a pre-existing rebaseline.

The recorded target measurement still exceeds the existing bootstrap, editor, shared renderer, default interactive, CSS, and several capability ceilings. Bootstrap moves from two static chunks to three. The extra file is a 694 byte Rolldown CommonJS interop runtime imported by twelve emitted chunks. That extraction is technically credible and reduces duplication, but the hard budget gate remains red. The specification requires a green delivery gate. Any ceiling change requires an explicit owner decision; this review cannot approve one.

### Moderate: each media write requests a full 16 MiB texture upload

[`startRasterJob`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/src/scene/stencilAtlas.ts#L221-L240) writes one slot into the media backing array, then sets `mediaTexture.needsUpdate = true` without an update range. Three uploads the full 2048 by 2048 RGBA page when no range exists. [`observeWebGlResources`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/tests/webGlResourceObserver.ts#L1-L33) observes only resource creation and deletion, so the browser gate cannot verify the required exact partial upload range.

The atlas needs a range that covers only the changed slot and a browser assertion over the actual upload call.

### Moderate: an unplaceable verdict survives reference count zero

[`createStencilAtlas.sync`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/src/scene/stencilAtlas.ts#L289-L329) adds unresolved and overflow keys to `unplaceable`. Reference removal clears only keys present in `assignments`. An unresolved key never had an assignment, so this sequence leaves stale state:

1. A referenced image is unresolved and becomes absent.
2. The reference set becomes empty.
3. The image is reintroduced before the next atlas synchronization.

`getMaskState` still returns absent and `mayCommitStagedContents` can approve a cut before synchronization classifies the key again. This is the slice 2 lifecycle debt on the image path. The current browser test covers immediate unresolved to resolved only.

### Moderate: staged payload precedence ignores the bound project

[`createPayloadBytesSource`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/src/persistence/payloadStore.ts#L55-L71) reads the global staged map by `payloadId` and returns the bytes without checking `projectId`. The committed reader is bound to one project, but a staged row from another project bypasses it whenever identifiers collide.

The module already has project-aware staged lookup. The renderer source should preserve the same boundary while keeping staged-first precedence.

### Moderate: reload integrity trusts payload metadata without verifying bytes

[`decodeAssets`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/src/persistence/projectRecordHydration.ts#L267-L279) receives `PayloadMetadata`. [`payloadMatchesAsset`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/src/persistence/projectRecordHydration.ts#L385-L392) compares only stored metadata. [`loadIndexedDbPayload`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/src/persistence/indexedDbProjectReads.ts#L140-L150) casts an IndexedDB row to `StoredPayloadBytes` without checking Blob shape, Blob size, or SHA256.

A corrupt or forged row with matching metadata survives hydration and renders under the claimed digest. The completion contract says reload verifies the content hash. The untrusted IndexedDB boundary needs row validation and byte verification before admitting the image.

### Moderate: the browser gate bypasses the required production paths

[`runImageRenderingBrowserGate`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/tests/imageRenderingBrowserDriver.ts#L63-L149) registers a test-owned payload source, directly creates the atlas, renderer, and mesh, manually synchronizes the atlas, and manually patches the mesh. Its second context repeats that assembly. It never imports through the payload store, dispatches the authored asset operation, mounts the production `CubeScene`, or creates a thumbnail artifact through the production thumbnail owner.

The pixel and resource assertions are useful component coverage. They do not prove the specified live scene and thumbnail integration chain.

### Moderate: the payload-sized quota recovery gate is absent

[`imageImportBounds.test.ts`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/tests/imageImportBounds.test.ts#L52-L90) covers the early size and storage estimate guards. The slice does not extend the IndexedDB quota recovery browser path with a payload-sized promotion, baseline preservation, loud failure state, and recovery after restart.

The existing general quota gate cannot prove that a native Blob write participates in the same abort and recovery semantics.

### Low: the committed-row mismatch branch has no regression test

[`imagePayloadPromotion.test.ts`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/tests/imagePayloadPromotion.test.ts#L106-L166) covers staged write, missing staged payload, staged metadata mismatch, and committed fallback after reload. It does not cover a pre-existing committed payload row whose metadata contradicts the promoted image claim.

### Low: one recorded controlled red does not sabotage the rejection invariant

The reported hydration red forced `payloadMatchesAsset` to return false. That makes the valid hydration case fail, while the dangling, hash mismatch, and length mismatch rejection cases remain green. [`Image record hydration integrity`](https://github.com/littleorgans/cubicell/blob/050c14dff57b17c503825a50081945dd718ffe87/tests/imageAssets.test.ts#L139-L175) therefore lacks a controlled red that bypasses validation and proves those rejection assertions guard the invariant.

The promote validation, sRGB decode, media selector, and import quota controlled reds were meaningful.

## Architecture checks that passed

- `createStencilAtlas` remains the single allocator and lifecycle owner for coverage and media planes.
- `mayCommitStagedContents` remains the single commit predicate.
- `contentRaster.ts` is a genuine extraction of the prior raster code. No duplicate implementation was found.
- The renderer payload port keeps persistence modules outside the renderer closure. Its project scoping needs the correction above.
- `contentAtlasSlotRect` is shared by current slot writers and is a justified public seam for motion.
- No changed file exceeds 700 lines. No newly enlarged function exceeds the stated threshold.
- No pre-existing delivery ceiling was changed.

## Verification

- `pnpm exec vitest run tests/imageAssets.test.ts tests/imagePayloadPromotion.test.ts tests/imageImportBounds.test.ts tests/faceContentRender.test.ts --project unit`: 4 files passed, 38 tests passed.
- `pnpm exec vitest run tests/imageRendering.browser.test.ts --project chromium`: 1 file passed, 1 test passed.
- `git diff --check 708b34d8316412db87740517661badea49abf90c 050c14dff57b17c503825a50081945dd718ffe87`: passed.
- Final HEAD: `050c14dff57b17c503825a50081945dd718ffe87`.
- Final status: clean `face-media` worktree.

No repository files were changed during this review.
