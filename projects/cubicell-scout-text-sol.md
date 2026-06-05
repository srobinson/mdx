# Cubicell face typography contracts and mechanics scout

Snapshot: `main` at `3725921ae23cd4088b3891b310889c8861ca05eb`.

Scope: read only survey of face typography against the installed Three `0.185.1`. No repository files changed.

## Reuse Map

### 1. Contract location

Typography belongs in the settled `CubeFaceContent` replacement. The grid and cube geometry need no text policy.

Current ownership is:

1. `src/domain/cube.ts:CubeFaceFigure` is the closed optional face value.
2. `src/domain/cube.ts:cubeFaceStateOwner` owns validation, sparse encoding, inheritance, morph classification, and render impact.
3. `src/persistence/recordCodecs/compactPose.ts:encodeCell` writes the encoded face at compact cell position 8.
4. `src/scene/cubeInstances.ts:createCubeCellInstances` copies the face value into the render instance.
5. `src/scene/instancedPartMeshCore.ts:writeStencil` is the sole per instance GPU writer.
6. `src/scene/faceStencilShader.ts:applyFaceStencilShader` samples one mask atlas behind the shared face material.
7. `src/thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer` reuses the same face path.

Replace `CubeFaceFigure` and the optional `figure` field with one optional discriminated `content` field. Preserve `cubeFaceStateOwner`, `setCubeFaceState`, the authored operation funnel, compact pose ownership, and the single GPU writer.

### 2. Minimum text variant

A durable text value needs more than a string. Recommended semantic shape:

```ts
type CubeFaceTextContent = {
  kind: "text";
  text: string;
  font: CubeFaceFontRef;
  size: number;
  align: "start" | "center" | "end";
  blockAlign: "start" | "center" | "end";
  color: CubePartColor;
  direction: "ltr" | "rtl";
  language: string;
};

type CubeFaceFontRef =
  | {
      kind: "system";
      family: "system-ui" | "sans-serif" | "serif" | "monospace";
      style: "normal" | "italic";
      weight: 400 | 700;
    }
  | { kind: "asset"; fontId: FontId };
```

Contract notes:

- `size` should be an em height in face space, expressed as a fraction of face height. Atlas pixels and camera zoom are renderer concerns.
- Logical `start` and `end` alignment preserve meaning for right to left text. Canvas supports these values directly.
- `direction` cannot safely inherit. `index.html:html.lang` is English and Canvas defaults inherit direction from its element or document.
- `language` is a BCP 47 tag. Canvas uses it during font resolution and text preparation. This matters for language sensitive glyph selection.
- `blockAlign` supplies the second axis that a rectangular face requires. Canvas exposes a baseline, but the authored value should remain baseline independent.
- Automatic wrapping is a separate contract. `fillText` prepares one line and the repository has no Unicode line breaking owner. A first slice can support explicit newlines only. Add wrapping after a product requirement defines width, line height, overflow, and maximum lines.
- Ship the system font branch first if portability is not required. Add the asset branch only with the payload store. This avoids a dormant reference that cannot resolve.

The existing `CubePartColor` is enough for monochrome text. It keeps colour interpolation on the instance attribute, so a colour edit does not reraster text. `src/domain/cube.ts:canTweenCubeFaceFigureColor` is the current identity stable colour tween precedent. Text, font, size, alignment, direction, and language changes should remain discrete cuts.

### 3. Compact wire

The current compact face is:

```text
[faceIndex, colorIndex, opacity, visibleBit, figure?]
figure = [stencilId, regionIndex, colorIndex, fitIndex]
```

Evidence: `src/domain/cube.ts:encodeCubeFaceFigure`, `src/persistence/recordCodecs/compactPose.ts:encodeCell`.

Keep face position 4 and replace its payload with a discriminated content tuple:

```text
content = [contentKindIndex, ...variant]
stencil = [0, stencilId, regionIndex, colorIndex, fitIndex]
text = [1, text, fontRef, size, alignIndex, blockAlignIndex, colorIndex, directionIndex, language]

systemFontRef = [0, familyIndex, styleIndex, weightIndex]
assetFontRef = [1, fontId]
```

The exact persisted path remains `PoseRevisionRecord.document.c[*][8][*]`, with the same path below `DraftRecord.document.workingPose`. Strict validators must reject unknown tuple lengths, indexes, invalid language tags, invalid sizes, and invalid font IDs.

### 4. Version plan

Single user reset semantics make this a clean bump with no migration.

| Contract | Current | Text with system font | Project owned font |
|---|---:|---:|---:|
| `src/persistence/indexedDbSchema.ts:indexedDbProjectStorageVersion` | 9 | 10 | 10 |
| `src/persistence/recordCodecs/poseRevisionRecordCodec.ts:poseRevisionRecordSchemaVersion` | 3 | 4 | 4 |
| `src/persistence/recordCodecs/draftRecordCodec.ts:draftRecordSchemaVersion` | 3 | 4 | 4 |
| `src/domain/authoredOperations.ts:authoredOperationSchemaVersion` | 4 | 5 | 5 |
| `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:outboxCommitRecordSchemaVersion` | 3 | 4 | 4 |
| `src/persistence/recordCodecs/localHistoryRecordCodec.ts:localHistoryStepSchemaVersion` | 1 | 2 | 2 |
| `src/persistence/recordCodecs/localHistoryRecordCodec.ts:localHistoryRecordSchemaVersion` | 4 | unchanged | unchanged |
| `src/persistence/recordCodecs/projectRecordCodec.ts:projectRecordSchemaVersion` | 2 | unchanged | 3 |
| `src/persistence/storageRecordTypes.ts:committedRecordSchemaVersion` | 3 | unchanged | 4 if the asset row or payload pointer changes |
| New font record | absent | absent | `fontRecordSchemaVersion = 1` |

Reasoning:

- Pose and draft records embed the compact face tuple.
- Authored scene operations can embed `patch.figure` today and will embed `patch.content`.
- Outbox records embed authored operations.
- Local history steps store JSON patches containing face and Library values. The history spine does not embed either value, so its outer version can remain 4.
- System font references live inside face state and require no Project asset roster change.
- A project owned font adds a `font` kind to `src/domain/project.ts:ProjectAssetKind`, a font collection to `src/domain/workbench.ts:Library`, a strict font record codec, projection and hydration, document operations, and a payload owner. This changes the Project roster codec.

### 5. Font ownership and portability

#### System fonts

Canvas 2D accepts the CSS font shorthand and turns prepared text into positioned glyph shapes. It supplies shaping, kerning, bidirectional direction, language aware font resolution, and installed font fallback without a JavaScript shaping dependency. [WHATWG Canvas text styles](https://html.spec.whatwg.org/dev/canvas.html#text-styles) and [WHATWG text preparation](https://html.spec.whatwg.org/dev/canvas.html#text-preparation-algorithm) define this behavior.

The claim has two firm limits:

1. Full Unicode is accepted as text input, but glyph coverage is not guaranteed. CSS font matching can reach installed fallback, then a missing glyph if no font covers a character. The set of installed fonts is explicitly platform, browser, locale, privacy, and user dependent. [CSS Fonts 4 font matching](https://www.w3.org/TR/css-fonts-4/#font-matching-algorithm)
2. Raster output is not deterministic across machines. Font selection, metrics, hinting, antialiasing, browser implementation, and operating system fonts can differ. CSS Fonts permits user agent and platform choices and notes that metric sources can yield different layouts.

Current environment probe, Chromium `149.0.7827.55`, drew English, Arabic, Devanagari, Thai, Japanese, and emoji through `64px system-ui, sans-serif`. Every sample produced nonempty coverage and `document.fonts.check` returned true. This proves the mechanism on this machine. It does not establish portable coverage.

System fonts therefore cost zero shipped font bytes and zero shaping library bytes. They spend CPU during each uncached raster and trade away cross machine visual identity.

#### Bundled or project owned fonts

A loaded `FontFace` must enter `document.fonts` before rasterization. `document.fonts.ready` or a targeted `document.fonts.load` prevents an early fallback bitmap from being cached. The [CSS Font Loading specification](https://www.w3.org/TR/css-font-loading/#font-face-set-ready) defines the readiness boundary.

The repository already ships Geist Mono Latin 400 and 700 through `src/main.tsx:module imports`. Current production artifacts contain `9,864` and `10,180` byte WOFF2 files, `20,044` bytes total. Reusing those exact Latin faces adds zero incremental font bytes, but unsupported scripts still fall through to system fonts.

A new fixed application font can ship as a build asset. A project owned font needs stronger ownership:

- `src/domain/project.ts:ProjectAssetKind` needs `font`.
- `src/domain/workbench.ts:Library` needs font metadata and lookup.
- A `FontAsset` needs content addressed `FontId`, byte length, media type, family, style, weight, and subset coverage.
- `src/persistence/storageRecordTypes.ts:StoredAssetBytes` currently stores JSON `documentBytes`. It has no binary payload field.
- `src/persistence/indexedDbSchema.ts:indexedDbProjectStoreNames` has no payload store.
- Project projection, hydration, storage preparation, and reads need the new asset kind and payload lifecycle.

Using the same WOFF2 bytes and explicit language, direction, weight, style, and size makes layout substantially more reproducible. Pixel identical regeneration still requires a pinned browser and raster environment, or persistence of the derived raster. The current recording path captures the live WebGL canvas via `src/export/streamRecorder.ts:createRecordingController`; the resulting recording contains the pixels seen in that session. Recreating the recording on another machine with system fonts can differ.

### 6. Raster and atlas mechanics

The current stencil path already performs the expensive shape conversion once:

- `src/scene/stencilAtlas.ts:rasterizeSvgAlpha` draws into Canvas 2D and reads RGBA pixels.
- `src/scene/stencilAtlas.ts:writeStencilSlot` extracts alpha into a retained R8 atlas.
- `src/scene/stencilAtlas.ts:createStencilAtlas` creates one `2048 x 2048` `DataTexture` with sixteen `512 x 512` slots, one pixel gutters, linear filters, and no mipmaps.
- `src/scene/faceStencilShader.ts:fragmentPartition` combines the sampled mask with face and figure colours.

Refactor these owners into a general face mask atlas. Text rasterization becomes:

1. Canonicalize and validate the text content value.
2. Resolve and await the font.
3. Draw the shaped lines into a temporary Canvas 2D surface.
4. Extract alpha to an R8 slot.
5. Cache by canonical content, resolved font identity, and resolution tier.
6. Upload the slot and wake the existing demand render scheduler. `src/scene/CubeScene.tsx:StencilAtlasReadyDriver` is the current ready then invalidate pattern.

Identical content across faces should share one slot. Rapid edits need a generation token so a late font or raster promise cannot overwrite a newer value.

#### R8 versus RGBA

| Slot format | `512 x 512` retained slot | `2048 x 2048` atlas | Capability |
|---|---:|---:|---|
| R8 | 262,144 bytes | 4,194,304 bytes | Monochrome glyph coverage with instance colour. Preserves the current two colour shader and one draw. |
| RGBA8 | 1,048,576 bytes | 16,777,216 bytes | Colour emoji, colour fonts, gradients, and per pixel colour. Four times the retained CPU and GPU memory. |

Canvas `getImageData` temporarily returns RGBA in both cases, so a `512 x 512` raster allocates about 1 MiB before alpha extraction. R8 remains the correct first format for authored text colour. RGBA is justified only when colour glyphs are a product requirement. An R8 path can render emoji silhouettes, but it cannot preserve colour emoji palettes.

The installed Three `0.185.1` confirms the options:

- `node_modules/three/src/textures/CanvasTexture.js:CanvasTexture` starts dirty, defaults to RGBA, and defaults to mipmapped minification.
- `node_modules/three/src/textures/DataTexture.js:DataTexture` accepts raw R8 bytes and defaults to no mipmaps.
- `node_modules/three/src/renderers/WebGLRenderer.js:copyTextureToTexture` supports a destination offset and subregion upload. It regenerates the destination mip chain when enabled.
- `node_modules/three/src/renderers/webgl/WebGLTextures.js:updateTexture` supports update ranges only for RGBA. An R8 dynamic atlas should use `copyTextureToTexture` from a small R8 `DataTexture`, or accept a full atlas upload.

The current atlas has fourteen unused slots after the two seeds. That is useful for a proof and insufficient as a general text contract. Unique text layouts consume slots even when they reference no Project asset. A production owner needs capacity, reuse, eviction, and stale instance repair. A whole face bitmap is still the smallest mechanism. A glyph atlas would require shaped glyph placement and new geometry or shader data.

#### Resolution and mip policy

The present `512` slot has `510` content pixels after gutters. `src/config/cubicellConfig.ts:renderPixelRatioPreferences` allows auto DPR `1..2`, plus explicit DPR 3 and 4. Camera zoom can make a face occupy far more than 510 device pixels. A fixed 512 mask will blur at close zoom.

No fixed texture resolution can remain sharp under unbounded camera zoom. The contract must declare a publish zoom ceiling or adopt resolution tiers.

Recommended first gate:

1. Keep the current 512 R8 slot, linear filters, and no mipmaps.
2. Render the same Latin, Arabic, CJK, and emoji silhouette samples with small and large type at DPR 1, 2, and 4.
3. Capture faces at 128, 512, and 1024 CSS pixel projected sizes.
4. Keep 512 if the intended publish framing passes. Move to deterministic 512 and 1024 tiers only if close framing fails.

Mipmaps improve distant minification but complicate a tiled atlas. Gutters must cover every mip level, distant levels eventually mix neighboring slots, and each dynamic update can regenerate the full mip chain. The current no mip policy avoids that bleed. If distant shimmer becomes visible, texture array layers with independent mip chains are cleaner than tiled atlas mips, but they change the shader contract and should follow the visual gate.

### 7. Render and authoring consumers

Text layout properties disappear into the raster. The GPU still needs resolved colour and mask slot, so the current four float instance attribute can survive a first text slice. Required refactors:

- `src/scene/instancedPartMeshCore.ts:InstancedFaceFigure` becomes content based.
- `src/scene/instancedPartMeshCore.ts:writeStencil` becomes the one content attribute writer.
- `src/scene/faceStencilShader.ts:faceStencilProgramKey` bumps when the attribute code gains content kind semantics.
- `src/scene/stencilAtlas.ts:getStencilAtlasSlot` becomes a runtime content resolver rather than a seeded ID map.
- `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` must wait for text masks and fonts.
- `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` can retain the owner supplied discrete cut versus colour tween policy.

The editor requires one deliberate extension. `src/editor/controlBindings.ts:ControlValueSchema` supports boolean, enum, and number only. `src/panels/ControlBindingField.tsx:ControlBindingField` has no text field. Add a shared string schema and field, then compose text, font, size, alignment, direction, and language under `src/panels/PartSection.tsx:FaceSection`. Continue routing edits through `set-face-state`; do not create a parallel text store.

Motion does not require per frame rerasterization when cubes move or content colour changes. Layout identity changes are discrete cuts. Both masks should be resident before the cut so state playback and recording never expose an unresolved slot.

### 8. Delivery bytes

Current package evidence:

- `package.json:dependencies.three` and `pnpm-lock.yaml:three@0.185.1` pin Three 0.185.1.
- Canvas 2D and system shaping add zero dependency bytes.
- Existing Geist Mono Latin WOFF2 assets total 20,044 bytes across two weights and are already part of the application delivery.
- `troika-three-text` is present only as a transitive Drei dependency. No source imports it. Its full ESM artifact is 195,391 bytes and 56,429 bytes at gzip level 9. That is an upper bound, not a measured tree shaken increment. It would also create a second text mesh and shader path, so it is outside the recommended atlas slice.

The existing production artifacts have effectively zero static headroom:

| Delivery | Observed gzip | Limit | Headroom |
|---|---:|---:|---:|
| bootstrap JS | 62,671 | 62,673 | 2 bytes |
| editor studio JS | 378,909 | 378,909 | 0 bytes |
| shared renderer JS | 414,045 | 414,046 | 1 byte |
| default interactive JS | 445,821 | 445,821 | 0 bytes |

Evidence: read only execution of `scripts/check-delivery-budget.mjs:checkDelivery` against the existing production artifacts passed. A fresh build was intentionally skipped because the brief forbids repository writes.

Any text implementation requires an observed ratchet update. Core decode, raster, and render support belongs in the shared renderer delivery because an opened project must display text. A lazily loaded authoring panel can use a named `budgets/initial-delivery.json:capabilityIncrements` entry.

Font files currently escape the static byte ratchet. `scripts/check-delivery-budget.mjs:checkDelivery` sums emitted JavaScript and CSS. `scripts/measure-initial-delivery.mjs:getDeliveryFiles` tracks the bootstrap, editor, and renderer JavaScript resources. It serves WOFF and WOFF2 correctly but does not declare them as measured delivery files. Any newly shipped font family needs an explicit font asset byte budget in addition to the JavaScript and CSS ratchets.

## Quality Map

### Proven reusable strengths

- `src/domain/cube.ts:cubeFaceStateOwner` is the correct single face content owner.
- `src/persistence/recordCodecs/compactPose.ts:encodeCell` keeps face content sparse.
- `src/scene/stencilAtlas.ts:rasterizeSvgAlpha` already proves Canvas 2D to R8 conversion in production code.
- `src/scene/faceStencilShader.ts:applyFaceStencilShader` preserves one face material and program.
- `src/scene/instancedPartMeshCore.ts:writeStencil` keeps one GPU writer.
- `src/scene/CubeScene.tsx:StencilAtlasReadyDriver` already reconnects asynchronous atlas readiness to demand rendering.
- `src/thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer` provides a second consumer that prevents silent export divergence.
- `src/export/streamRecorder.ts:createRecordingController` captures current canvas pixels, so a resolved mask is directly recordable.

### Contract risks

- System font output varies across machines and can display missing glyphs.
- The document language is English. Inherited Canvas language and direction are unsuitable authored defaults.
- Text wrapping and overflow have no current owner.
- Fourteen free stencil slots do not constitute a general text capacity.
- Fixed 512 masks have a known close zoom blur ceiling.
- Tiled mipmaps can bleed and make dynamic updates expensive.
- Project owned fonts cannot round trip until binary payload storage exists.
- Current delivery ratchets have zero practical JavaScript headroom and no font asset byte gate.

### Searches proving absence

No face text, Canvas text rasterizer, font asset, font payload, or text geometry implementation was found. The only font imports are UI CSS. `troika-three-text` appears only in the lockfile.

```text
rg -n --glob '*.{ts,tsx,js,mjs,json}' 'troika|TextGeometry|FontLoader|CanvasTexture|OffscreenCanvas|FontFace|document\.fonts|fillText|strokeText|measureText' src tests scripts package.json pnpm-lock.yaml
rg -n --glob '*.{ts,tsx}' '(font|text)(Id|Asset|Source|Reference|Content)|face(Text|Typography)' src tests
rg -n --glob '*.{ts,tsx}' -i 'font payload|font bytes|binary asset|asset payload|unicode|glyph|shaping' src tests
rg -n '@fontsource|geist' src package.json pnpm-lock.yaml
```

## Verdict

Verdict: supported with a portability boundary.

Canvas 2D text rasterization is the path of least resistance for the first face typography slice. It uses browser shaping, keeps the face plane and single draw contract, reuses the existing R8 atlas and colour shader, adds no shaping dependency, and costs zero font bytes when system fonts are used.

The phrase “full Unicode for free” overstates the guarantee. Canvas accepts Unicode and shapes complex text, while actual glyph coverage and pixels depend on available fonts and the raster environment. System font projects cannot reproduce the same visual output across machines. A project owned WOFF2 reference improves portability and requires the binary payload store already identified by the media scouts.

Use R8 for the first slice. Reserve RGBA for a stated colour emoji or colour font requirement. Gate 512 versus 1024 masks at the maximum intended publish zoom before changing atlas geometry. Replace `CubeFaceFigure` cleanly, bump and reset the face carrying records, and keep text authoring, scene rendering, thumbnails, motion cuts, and recording on the existing owner chains.
