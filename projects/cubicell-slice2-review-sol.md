# Cubicell Face Text Slice 2 Adversarial Review

Reviewed target `106bae6480a2f0f057d608ee74a016ca6ac1be59` on `face-media`, against parent `70ae938131dcc066b4d7f1349641285367b43f66`.

The target checkout was pristine before review. The review was read only. I did not run tests or a build. I ran the existing delivery budget checker against the retained build artifacts, inspected the retained crispness artifacts, and ran `git diff --check`.

## Findings

### High: playback can commit before the target masks are resident

Location: [`src/scene/CubeScene.tsx:193`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/src/scene/CubeScene.tsx#L193-L258), `useOwnedStencilAtlas`

The owner includes upcoming contents in the same atlas synchronization, then launches `atlas.sync(...)` from a passive effect and discards its `ready` promise. The staged scene exposes the destination endpoint, but no readiness state reaches transport or frame commit. A cut immediately returns the destination scene when its threshold is reached, including a zero duration cut at its first sample. A pending slot is written as `noContent` by `writeFaceContentAttribute`.

This leaves two deterministic failure paths:

1. A zero duration transition or a cut at time zero can commit the destination before the passive synchronization completes.
2. Sixteen distinct visible source masks plus sixteen distinct destination masks fill the sixteen slot atlas. Current contents are deliberately ordered first, so the destination cannot become resident during warming. At the cut, source references release and destination raster work starts asynchronously. The first destination frames render base coverage. Recording can capture them because `streamRecorder` has no atlas residency wait.

This violates the contract that playback target masks must be resident before cut commit. There is no test that exercises `upcomingScene` or `StagedScene.upcoming`.

Relevant flow:

* [`src/transport/stagedScene.ts:119`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/src/transport/stagedScene.ts#L119-L148)
* [`src/evaluation/sceneTransition.ts:66`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/src/evaluation/sceneTransition.ts#L66-L72)
* [`src/scene/faceContentShader.ts:81`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/src/scene/faceContentShader.ts#L81-L99)
* [`src/export/streamRecorder.ts:145`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/src/export/streamRecorder.ts#L145)

### Medium: warming omits faces rendered as hidden ghosts

Location: [`src/scene/CubeScene.tsx:270`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/src/scene/CubeScene.tsx#L270-L295), `useUpcomingSceneContents`

The live instance owner passes `includeHiddenGhosts: ghostHiddenParts` and renders the ghost bucket. The upcoming derivation uses default options and collects only opaque and translucent faces. Editor playback normally enables hidden ghosts outside preview mode.

A destination hidden face can therefore appear as a ghost at the cut without having participated in warming. Its content starts as base coverage while its raster is produced. The upcoming derivation must use the same eligibility options and buckets as the live renderer.

Relevant flow:

* [`src/scene/useCubeSceneRenderState.ts:62`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/src/scene/useCubeSceneRenderState.ts#L62-L70)
* [`src/studios/editor/EditorStudio.tsx:244`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/src/studios/editor/EditorStudio.tsx#L244-L267)

### High: the required crispness matrix contains visible clipping

Location: [`src/scene/stencilAtlas.ts:285`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/src/scene/stencilAtlas.ts#L285-L324), `rasterizeTextAlpha`

The rasterizer scales an oversized ink block to exactly the atlas width or height, then clamps its draw position exactly to the measured bounds. There is no safety inset for raster rounding and antialiasing.

The retained required matrix visibly crops the left stroke of `Nova` in both `size-0.6-dpr-1-px-128.png` and `size-0.6-dpr-4-px-1024.png`. The DPR 1 tile confirms ink at the left image boundary: pixel `(0, 48)` is `srgba(192,250,192,1)`. The corresponding default size tile is white at that boundary. This fails the contract's no clipping requirement. The script generates the contact sheet but records no durable human pass judgment.

### Medium: required rendered and parity gates substitute synthetic live paths

Location: [`tests/stencilRenderingBrowserDriver.ts:384`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/tests/stencilRenderingBrowserDriver.ts#L384-L459), `runTextRenderingBrowserGate`

The rendered text gate manually creates a Three.js scene, one instanced mesh, an atlas, and direct synchronization and patch calls. It bypasses the production `CubeScene` tree, live eligibility, atlas effect, layer ownership, content generation replay, and demand scheduling.

The editor browser gate mounts the production tree and proves commit, mask residency, attribute replay, program stability, and idle demand behavior. It does not prove rendered pixel coverage through that tree. The thumbnail parity probe calls a manual atlas plus `createCubeSceneInstances` its live path, then captures only the thumbnail side. A divergence in the live material, shader, replay, or scheduling path can pass both required gates.

Relevant test:

* [`tests/textContentBrowserDriver.tsx:67`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/tests/textContentBrowserDriver.tsx#L67-L162)
* [`tests/textContentBrowserDriver.tsx:176`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/tests/textContentBrowserDriver.tsx#L176-L240)

### Medium: the slice violates the repository refactoring limits

Locations:

* [`tests/sceneMorph.test.ts:403`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/tests/sceneMorph.test.ts#L403-L441)
* [`tests/panels.test.tsx:92`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/tests/panels.test.tsx#L92-L391)
* [`src/scene/stencilAtlas.ts:86`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/src/scene/stencilAtlas.ts#L86-L256)

`tests/sceneMorph.test.ts` already had 729 lines at the parent and now has 772. The slice added a text test without the required prior refactor. The `control binding round trips` block spans about 300 lines after the new text case. `createStencilAtlas` now spans about 171 lines after absorbing multi kind dispatch. These exceed the hard 700 line file rule and the approximately 150 line function or callback rule in the repository instructions.

### Low: the claimed controlled red coverage leaves text identity gaps

Location: [`tests/faceContentRender.test.ts:278`](https://github.com/littleorgans/cubicell/blob/106bae6480a2f0f057d608ee74a016ca6ac1be59/tests/faceContentRender.test.ts#L278-L300)

The canonical key test varies text, size, alignment, weight, and NFC form. It never varies font family or style. Removing either field from the atlas key leaves this test green. The morph test varies only text, so regressions in size, alignment, family, style, or weight comparisons can also survive. The memo proof covers production text authoring, while stencil generation replay remains proven only below the production tree.

The stale async assignment and overflow cases are covered generically. The release, overflow, and text memo cases have credible mutation sensitivity by inspection. The complete six red claim is not recoverable from this single commit and the missing identity variations prevent an independent proof of all stated invariants.

## Clean evidence

* One dynamic R8 allocator remains the live owner. Thumbnail rendering owns its isolated atlas.
* Matrix, colour, opacity, and content attributes remain under the existing mesh synchronization and patch owners.
* Library stencils resolve through the Library owner. No seeded fallback was added.
* `TextContent` has no region field. The single line text editor is within the recorded minimum slice.
* Opaque, translucent, and ghost bucket memo dependencies include both stable slots and patch identities.
* Thumbnail rendering awaits its atlas synchronization before capture.
* `git diff --check 70ae938..106bae6` passed.
* The retained delivery artifacts pass every zero headroom ceiling. The nine slice ceilings are bootstrap JS 62,656 B, editor studio JS 381,029 B, editor studio CSS 7,620 B, shared renderer JS 413,299 B, default interactive JS 448,280 B, default interactive CSS 7,620 B, motion 9,982 B, thumbnails 2,397 B, and camera motion 833 B.

## Verdict

The slice is not clean. Playback residency and crispness fail required product contracts. The live visual proof, eligibility parity, structural limits, and controlled red matrix also need correction before acceptance.
