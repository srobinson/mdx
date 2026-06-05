# Cubicell spec 4/4: video and seeded shader motion

Spec only, no code. Base: main @ `3725921ae23cd4088b3891b310889c8861ca05eb`. Citations use `file:symbol`.

Binding inputs: `~/.mdx/projects/cubicell-content-scout-synthesis.md`; `~/.mdx/projects/cubicell-f1-spike.md`; `~/.mdx/projects/cubicell-scout-media-grok.md`; the F1 and content direction decisions recorded in Context Matters on 2026-08-09; spec 1, `~/.mdx/projects/cubicell-spec-content-union.md`; and spec 3, `~/.mdx/projects/cubicell-spec-media-store-images.md`.

## Decisions taken as given

- Motion pixels use spec 3's RGBA atlas. Each changed source is copied into its assigned slot with `WebGLRenderer.copyTextureToTexture` before the visible scene renders.
- Media faces remain in the existing instanced face buckets owned by `src/scene/renderCubeScenePartLayers.tsx:renderCubeScenePartLayers`. Motion adds no dedicated face meshes or per source face materials.
- The visible face program has a fixed cache key. Source count, content assignment, playback state, shader seed, and shader parameters never compile another visible program. The single GPU attribute writer remains `src/scene/instancedPartMeshCore.ts:syncInstancedPartMesh` and `patchInstancedPartMesh`.
- Shaders are a seeded, compiled library. User GLSL, TSL, NodeMaterial, WebGPU migration, network streams, audio, and arbitrary uniforms are outside this slice.
- Timing did not choose F1. The architectural gates are flat visible draw count, fixed program count, and exact texture upload or copy counts. Frame timing is a local developer diagnostic only.

## 1. Requirements on the content union

Spec 1 owns `src/domain/content.ts:CubicellContent`, its validation, wire encoding, authoring model, and version bumps. This spec requires these variants and fields; it does not design the union.

| Variant | Required fields | Contract |
|---|---|---|
| `video` | `videoAssetId`, `playbackPolicy`, `loop`, and variant specific `fit` | `playbackPolicy` is `"selected"` or `"always"`. The default is `"selected"`. Spec 1 owns the exact fit enum. The asset reference never carries bytes, payload ids, object URLs, decoder state, or atlas slots. |
| `shader` | `shaderId`, `seed`, `parameters`, and variant specific `fit` | `shaderId` resolves only through the compiled seed library. `seed` is a validated unsigned 32 bit integer. `parameters` must match the selected library entry's bounded, serializable parameter schema. Shader source and uniform names never enter authored state. |

The union must keep the same value usable as cube face decoration and as a future content cell occupant, per the recorded `CellOccupant = Cube | Content | Empty` decision. Runtime placement changes sampling geometry, not content identity.

The `video` reference resolves to an immutable `VideoAsset` sibling of spec 3's `src/domain/image.ts:ImageAsset`. Required asset metadata is `{ id, kind: "video", name, mediaType, byteLength, contentHash, payloadId, width, height, durationMs, posterImageAssetId }`. `posterImageAssetId` resolves through spec 3's image asset and atlas path. Video bytes and poster bytes use spec 3's payload store and atomic promotion contract. Authored operations remain JSON safe.

Import validates browser decodability, dimensions, duration metadata, and the stored hash before the asset becomes referenceable. The first slice rejects sources whose width or height exceeds 256 pixels. The importer extracts the first decodable frame as the deterministic poster image and promotes the video asset, video payload, poster image asset, and poster payload as one durability unit. No second binary store or write path is permitted.

## 2. Runtime ownership

Add one scene runtime owner, `src/scene/motionSourceRegistry.ts:createMotionSourceRegistry`, created and disposed beside `src/scene/CubeScene.tsx:useOwnedStencilAtlas`. It owns only ephemeral source state:

- one runtime entry per unique `videoAssetId` or canonical shader value, shared by every face that references it;
- video element, Blob URL, `VideoTexture`, decoder callback, playback state, and last copied media time for video;
- seeded shader clock, resolved parameter block, and atlas lease for shader;
- transient slot lease, current eligibility, dirty state, and generation token for either source kind.

The registry receives visible face references and selection state from the existing scene derivation. Selection is resolved through `src/domain/selection.ts:createCubeSelectionIndex`; the registry does not read a second selection store. `src/scene/useCubeSceneRenderState.ts:useCubeSceneRenderState` remains the owner of visibility.

The registry produces pixels and lease changes. It never writes instance attributes. Lease changes invalidate the normal presentation derivation, which resolves the spec 3 media atlas rectangle through `src/scene/cubeInstances.ts:createCubeCellInstances`; the existing sync or patch path writes the rectangle. This preserves the authored single writer and GPU single writer chains.

`src/scene/MotionFrameDriver.tsx:MotionFrameDriver` owns per frame production and is mounted in `src/scene/CubeScene.tsx:CubeScene` after `src/scene/RenderSchedulerDriver.tsx:RenderSchedulerDriver` and before visible layers. It uses the renderer and frame clock supplied by React Three Fiber. No module creates a private `requestAnimationFrame`, interval, or parallel render loop.

## 3. Dynamic motion slot allocation and eviction

Spec 3 owns `src/scene/mediaAtlas.ts:createMediaAtlas`, atlas geometry, static image allocation, upload, readiness, disposal, and the slot rectangle API. This spec adds transient motion leases to that allocator.

Static image slots, including video posters, remain protected until asset deletion as specified by spec 3. Motion never evicts them. A visible shader's canonical poster occupies a protected derived slot keyed by its canonical shader value; that slot releases when the last visible reference disappears. Every active motion source needs one transient slot in addition to its protected poster slot.

Allocation is reconciled once per scene presentation change and before pixel production:

1. Canonical source identity deduplicates faces. One video asset means one decoder, one transient slot, and one copy regardless of referencing face count. Identical shader id, seed, and canonical parameters share one producer and slot.
2. Eligible sources are ordered by priority: the primary selected face, other selected faces, then visible `"always"` sources. Ties use the prior lease first, then most recently presented order, then canonical source key. This makes the result deterministic.
3. Existing eligible leases are retained. Free slots are assigned to the remaining sources in priority order. All leases used by the current frame are pinned until the frame completes.
4. When no free slot remains, the allocator evicts the least recently presented unpinned motion lease. If every motion lease is pinned, lower priority eligible sources are demoted to their poster before the higher priority source is admitted on the next frame boundary.
5. An eligible source that cannot be admitted displays its poster. Video decoding and shader production stop for that source. The renderer never creates a dedicated mesh as an overflow path.
6. Ineligible motion leases become unpinned cache entries. They survive until pressure requires eviction, avoiding churn during selection changes. A source with no visible references is disposed and its lease released.

Every async callback captures the runtime entry generation. A decoded frame, payload load, or `play()` result with a stale generation is ignored. Atlas disposal invalidates every outstanding lease and callback.

## 4. Demand loop and copy pipeline

Extend `src/scene/renderProducers.ts:renderProducers` with two names: `faceVideo` and `faceShader`. They share `MotionFrameDriver` and separate wake semantics.

### Video producer

Each active video registers `HTMLVideoElement.requestVideoFrameCallback` when available. The callback marks that source dirty and calls `RenderScheduler.request(renderProducers.faceVideo)`. This callback is a decoder readiness signal; it does not render or copy pixels. Multiple callbacks before a render coalesce through `src/scene/renderScheduler.ts:createRenderScheduler`.

On browsers without video frame callbacks, `faceVideo` remains live only while an admitted video is playing. `MotionFrameDriver` compares `currentTime` with the last copied time and skips unchanged frames. The fallback still runs through the named demand producer.

### Shader producer

`faceShader` follows `src/transport/TransportFrameDriver.tsx:TransportFrameDriver`: request once when the first admitted shader becomes active, produce inside `useFrame`, then call `RenderScheduler.report` with current liveness. The producer releases when no shader is admitted. Shader elapsed time advances from the frame delta supplied to `useFrame`; wall clock reads do not enter shader output.

### Frame order

For every requested motion frame, `MotionFrameDriver` performs this order before the visible scene draw:

1. Reconcile source eligibility and transient leases.
2. Initialize each dirty `VideoTexture` as needed and copy the newly decoded frame into its assigned atlas rectangle with `copyTextureToTexture`.
3. For each admitted shader, set the shared material's seed, bounded parameters, and elapsed time; render into the shared offscreen target; copy the target texture into the assigned atlas rectangle.
4. Clear only the dirty generations that were successfully copied.
5. Render the existing instanced scene. Report producer liveness for the next demand frame.

The atlas copy updates pixels in place. It does not replace the atlas texture, material, mesh, program key, or instance slot assignment. Recording therefore observes the same canvas and render cadence owned by `src/export/streamRecorder.ts:createRecordingController`.

## 5. Video lifecycle and playback policy

Video bytes load through spec 3's `src/persistence/storagePort.ts:ProjectStoragePort.loadPayload`, then become a Blob URL for one shared `HTMLVideoElement`. The runtime sets `muted = true`, `playsInline = true`, `preload = "metadata"`, and the authored `loop` value. Audio is unsupported, so mute is a runtime invariant rather than an authored field.

- `"selected"`: the poster is shown until any referencing face is selected and admitted. Selection calls `play()` inside the qualifying user gesture path. Deselection pauses the element and returns all referencing faces to the poster. Reselection resumes the retained media time while the source remains visible.
- `"always"`: an admitted visible source calls `play()` as soon as metadata and its slot are ready. Muted inline playback is the only autoplay mode. Offscreen or capacity demoted sources pause.
- A rejected `play()` promise moves the source to `blocked`, releases continuous demand, and leaves the poster visible. The next direct selection gesture retries. Rejections never create retry timers or a spinning render producer.
- A non looping source holds its final copied frame and releases `faceVideo` after `ended`. Deselecting returns to the poster. The next selected playback resets to time zero; an always source resets only after leaving and reentering the visible set.
- When the last visible reference disappears or the asset revision changes, pause, clear `src`, call `load()`, dispose the `VideoTexture`, revoke the Blob URL, cancel the decoder callback, and release the transient lease.

Thumbnails never instantiate a video element. `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` and `src/thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer` resolve `posterImageAssetId` through spec 3 and wait for atlas readiness before capture.

## 6. Seeded shader library

Add `src/domain/seededShaders.ts:seededShaders` and `resolveSeededShader`, following `src/domain/seededStencils.ts:seededStencils` and `resolveStencilContent`. Each compiled entry contains an id, label, bounded parameter schema, defaults, canonical poster time, and parameter packing metadata. The library contains no runtime supplied code.

All entries execute through one shared fullscreen `ShaderMaterial`, one shared 256 by 256 `WebGLRenderTarget`, one vertex shader, and one compiled fragment program. The fragment program contains the fixed library dispatch; `shaderId` selects a branch through a uniform. Seeds and parameters are uniforms. Adding faces, changing seeds, or changing values never changes `customProgramCacheKey` or compiles a program. Adding a library entry is a deliberate source change that reruns the program count gate.

The first library entry is the spike's raymarch class exemplar: a bounded 32 step signed distance field sphere with seed driven phase, palette, radius, rotation, and glow parameters. Parameter validation clamps finite values to entry bounds before they reach uniforms. Given `(shaderId, seed, canonical parameters, elapsedMs)`, output is deterministic.

The poster for shader content is the same library entry rendered once at its canonical poster time into the context's protected derived slot. The thumbnail context performs the same deterministic one frame render before capture. No poster payload is persisted, and thumbnail rendering never holds `faceShader` live.

## 7. Tests and gates

Promote the isolated spike pattern from `.claude/worktrees/f1-spike/tests/f1MediaStrategyBrowserDriver.ts:runF1MediaStrategySpike` into the browser suite. Reuse `tests/webGlResourceObserver.ts:observeWebGlResources`, `tests/rendererDrawObserver.ts:observeRendererDraws`, and `tests/frameTimeMetrics.ts:summarizeFrameTimes`; consolidate the spike's `observeTextureUploads` beside the other WebGL observers before production use. The production gate uses the real scene matrices and instanced face path, matching `tests/stencilRenderingBrowserDriver.ts:runStencilRenderingBrowserGate`.

Count gates are exact after warmup:

- A populated face bucket remains one visible draw at 1, 4, and 8 unique active video sources plus one seeded shader.
- The isolated motion harness compiles exactly two programs: the fixed visible media program and the one shared offscreen shader program. The production scene creates zero new programs when sources play, pause, change slots, change seeds, or change parameters.
- With `N` newly decoded videos and one shader, upload or copy calls remain `2N + 1`: one video texture upload and one atlas copy per video, plus one shader target to atlas copy.
- One shader adds one offscreen draw. Video source count adds no draws. Texture and buffer disposal return to the observer baseline; one video texture exists per unique admitted asset, never per face.
- Capacity pressure evicts only transient motion leases, preserves protected image and poster slots, and returns demoted faces to the correct poster without a draw or program increase.

Local measurement note, never a CI or browser acceptance gate: retain the spike's 768 by 768 moving camera case, 24 warmup frames, 120 measured frames, `gl.finish()`, and the 1, 4, 8 source matrix at 256 pixels plus one raymarch source. Developer runs record p50 and p95 beside their machine, browser, and source revision. The author and verifier spike runs both stayed below 1.5 ms p95, but no millisecond value passes or fails the build. Draw calls, program count, and texture uploads or copies per frame are the acceptance gates. Any claimed timing change requires two clean local reruns with raw results retained.

Additional behaviour gates:

- `"selected"` remains poster only until selection, wakes on the user gesture, pauses on deselection, and releases demand without a leaked callback.
- `"always"` autoplays only muted and inline; a forced `play()` rejection leaves the poster and a sleeping scheduler, then retries on selection.
- Two faces sharing a video or canonical shader value produce one runtime, one slot, and one producer update.
- A stale decoded frame or stale shader task cannot write into a reassigned slot.
- Live scene and thumbnail capture use the same poster pixels while thumbnails create no motion producers.
- Controlled red proofs cover visible draw growth, program key drift, stale generation writes, protected slot eviction, and producer liveness leaks.

## 8. Supported envelope and remeasurement trigger

The supported first slice is at most eight concurrently admitted unique motion sources, each producing no more than 256 pixels on either axis. This limit counts video and shader sources together. More faces may reference those sources because identity deduplication keeps producer count flat.

Projects may author more than eight motion values. Sources outside the admitted set show posters and consume no decoder, shader draw, or transient slot. The UI exposes the active limit and current poster fallback rather than failing the document.

Before raising either eight active sources or 256 source pixels, rerun the exact observer harness on the proposed counts or dimensions. CI acceptance remains draw count, fixed programs, `2N + S` upload or copy traffic, and live texture count. Record p50 and p95 in the local measurement note for developer judgment. Do not extrapolate from the F1 result.

## Out of scope

Arbitrary user shaders; audio; remote URLs, HLS, or WebCodecs; video transcoding; sources above 256 pixels; more than eight concurrent active sources; dedicated media face meshes; CSS3D; TSL, NodeMaterial, or WebGPU; motion slot persistence; thumbnail animation; cross context GPU sharing. Spec 1 owns the content union. Spec 3 owns payload durability, static image allocation, RGBA atlas geometry, and image upload.

## Completion

```text
done: Video and seeded shaders use transient RGBA atlas leases, named demand producers, fixed program counts, exact texture traffic gates, and local timing diagnostics only.
```
