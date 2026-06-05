# Spec — text on cube faces

Spec 2/4, 2026-08-09, main @ 3725921. No code changes here; this is the build contract. Binding inputs: the reuse map in `cubicell-content-scout-synthesis.md` (§2), scout reports `cubicell-scout-text-fable.md` and `cubicell-scout-text-sol.md`, the F1 decision (dynamic atlas, one-draw intact), and the CellOccupant reframe (face content and future cell-occupant content share one content type). Citations are `file:symbol`.

## Decisions taken as given

- Text-as-stencil: Canvas 2D `fillText` rasterized into dynamic slots of the single-channel R8 atlas, tinted by the existing colour-role contract in `src/scene/faceStencilShader.ts:fragmentPartition`. Zero new programs, zero new draw calls, zero fragment shader change for this slice.
- System fonts only. Zero bundle bytes. Machine portability caveat and the project-owned-font escape hatch are documented in Future Work, not specced.
- Single-channel SDF is a noted growth path (scale quality), not this slice.
- The text variant is a member of the `CubicellContent` union owned by spec 1 (`cubicell-spec-content-union.md`); `CubeFaceContent` is spec 1's semantic alias at the face carrier. This spec does not design the union.
- The dynamic R8 slot allocator is owned by spec 1 §8. This spec designs no allocator; §3 states text's requirements on that owner's API.

## 1. Requirements on the content union (spec 1)

Text needs a `{ kind: "text" }` member of `CubicellContent` (carried at faces through spec 1's `CubeFaceContent` alias) carrying:

| Field | Requirement |
|---|---|
| `text` | The string. Explicit newlines are the only line-break mechanism this slice; no automatic wrapping (no Unicode line-breaking owner exists). Empty string is invalid; validators reject it. |
| font stack ref | A system font stack reference (generic family + style + weight). No asset branch this slice; the shape must leave room for a future `{ kind: "asset" }` arm without a wire break beyond the normal bump. |
| `size` | Em height in face space as a fraction of face height. Atlas pixels and DPR are renderer concerns and must not leak into the domain value. |
| `align` | Logical `start` / `center` / `end` (logical, not left/right, so RTL text keeps meaning; Canvas supports these values directly). |
| weight | Part of the font stack ref (400 / 700 per the shipped precedent in `src/main.tsx`). |
| colour | The existing colour-role type used by `face.color`; colour edits retint the instance attribute and must not re-rasterize. |

Flagged for spec 1's decision, not required by this slice: `blockAlign` (second axis), `direction`, `language` (the sol scout showed Canvas inherits both from the document, whose lang is English; inherited defaults are wrong for authored content). If spec 1 omits them, the rasterizer pins `dir="ltr"` and document language explicitly so behaviour is at least deterministic, and adding them later is a normal bump-and-reset.

Wire encoding, tuple shape, and the schema-version bump table are spec 1's contract (the sol scout's §3–4 is the reference input). Text imposes only: the variant round-trips through `src/persistence/recordCodecs/compactPose.ts:encodeCell` at the existing face payload position, strict validators reject unknown tuple lengths and invalid sizes, and versioning is bump-and-reset (no migrations, single user).

## 2. Rasterization contract

Owner: a `rasterizeTextAlpha` sibling to `src/scene/stencilAtlas.ts:rasterizeSvgAlpha`, inside `stencilAtlas.ts` ownership. Steps:

1. Canonicalize the text content value (NFC normalize the string; canonical field order) — the canonical form is the cache key input.
2. Await font readiness: `document.fonts.ready`, plus a targeted `document.fonts.load` for the resolved stack at the target pixel size, before drawing. Rasterizing early bakes a fallback bitmap; the readiness-then-invalidate pattern is `src/scene/CubeScene.tsx:StencilAtlasReadyDriver`.
3. Draw with `fillText` on a 2D canvas at slot content resolution, one draw per explicit line. Font pixel size = `size × contentSize` where contentSize is the slot content box (slot size minus gutters, per `stencilAtlas.ts:writeStencilSlot`).
4. Measure with `measureText` actual bounding boxes and clamp so ascenders, descenders, and side bearings never clip at the content box edge; apply `align` per line and centre the line block vertically (until spec 1 adds `blockAlign`).
5. Extract alpha and write through the existing `writeStencilSlot` (gutter fill and `region` inversion already live there and apply to text unchanged).

**Crispness / resolution strategy.** Fixed 512 R8 slot, `LinearFilter`, no mipmaps — the existing atlas policy in `stencilAtlas.ts:createStencilAtlas` stands. No fixed bitmap stays sharp under unbounded zoom; the contract is a gated ceiling, not a promise:

- Rasterize at slot resolution (510 content px). Do not supersample per DPR; DPR (`src/config/cubicellConfig.ts:renderPixelRatioPreferences`, auto 1–2 plus explicit 3/4) affects screen sampling, not the mask.
- Visual gate before merge (test §7): sample strings at small and large `size`, DPR 1/2/4, faces projected at ~128/512/1024 CSS px. If the intended publish framing passes, 512 ships. If close framing fails, the sanctioned fix is a deterministic 1024 tier (atlas growth to 4096², 64 slots), not mipmaps and not SDF.
- Mipmaps stay off: tiled-atlas mips bleed across slots, gutters would need coverage at every level, and every dynamic update would regenerate the chain. Distant shimmer is accepted this slice; texture-array layers are the future escape if it matters.
- Magnification blur beyond the gate ceiling is the SDF growth path's problem (Future Work).

## 3. Text requirements on spec 1's slot allocator

Spec 1 §8 owns the single dynamic R8 slot allocator at `src/scene/stencilAtlas.ts` (the replacement of the fixed seed map at `getStencilAtlasSlot`). This spec designs no allocator; text is that owner's second client, and this slice depends on spec 1's foundation landing first. A second allocator anywhere — including the thumbnail path — is a build defect. Text imposes these requirements on the owner's API:

- **Multi-kind keys.** Spec 1's key model is stencilId-based; text requires the key space to admit a content-hash key: the canonical text value (NFC-normalized string + font ref + size + align + region + resolution tier). Colour is excluded from the key (it lives on the instance attribute). Identical content across faces resolves to one shared slot.
- **Kind-dispatched rasterization.** The allocator accepts `rasterizeTextAlpha` (§2) as the rasterizer for text keys — the sibling of `rasterizeSvgAlpha`. Slot writing stays on the owner's `writeStencilSlot` path (gutters and region inversion unchanged).
- **Reference counting and release.** Text slots release when the document no longer references the key (refcount zero after a document change diff), and never while the sole GPU writer (`src/scene/instancedPartMeshCore.ts:syncInstancedPartMesh` / `patchInstancedPartMesh`) can still point at them: release ordering follows the sync pass.
- **Async safety.** Text rasterization is async (font readiness, §2). Each slot write carries a generation token; a resolving raster with a stale token is discarded. A face whose mask is not yet resident renders base colour (no mask), never a stale or foreign mask.
- **Overflow observability.** Beyond capacity the face renders base colour, identical to today's null-figure path, and the allocator reports the overflow observably (dev warning plus a counter the gate reads). No silent wrong-slot rendering. Eviction beyond refcount-zero release stays deferred until measured.
- **Upload and wake.** On raster completion the owner uploads and pulses the demand loop (the `src/scene/CubeScene.tsx:StencilAtlasReadyDriver` pattern). Full-texture `needsUpdate` at human edit cadence is acceptable this slice; if the edit-latency gate fails, the sanctioned optimization is `copyTextureToTexture` subregion upload from a small R8 `DataTexture` (three's `updateTexture` ranges are RGBA-only, per the sol scout), matching the F1 machinery. Not built speculatively.
- **Program stability.** Text is a slot index like any stencil: no change to the shared face program, its attribute packing, or spec 1's fixed program key. Shader symbols cited in this spec (`src/scene/faceStencilShader.ts:applyFaceStencilShader`, `writeFaceStencilAttribute`) are the pre-foundation names at main and follow spec 1's content renames.

## 4. Editor binding

Precedent: `src/editor/controlBindings.ts:faceStencilBinding`. Text needs one deliberate schema extension plus one binding:

- `src/editor/controlBindings.ts:ControlValueSchema` gains a `{ kind: "string" }` branch (`ControlValue` already includes `string`). `src/panels/ControlBindingField.tsx:ControlBindingField` gains the matching text input field. This is the only editor-infrastructure change; it is shared, not text-private.
- New binding id `face.text` in `ControlBindingId`, registered in `controlBindings.ts` beside `faceStencilBinding` and appended to `src/panels/panelDefinitions.ts:faceBindingIds`.
- `createCommand` routes through the existing `set-face-state` operation with a content patch, scope via `resolvePartEditScope`, exactly as `faceStencilBinding` does. No parallel text store, no new operation kind. `read` returns the current text (empty when the face carries non-text content).
- Committing an empty string clears the content (the null-figure precedent in `faceStencilBinding`). Fields for font, size, and align follow the same binding pattern (enum/number schemas already exist); they may land in the same slice or the next, but text-with-defaults must work with the string field alone.
- How text coexists with the stencil picker on the face panel (one content selector vs stacked fields) follows spec 1's union authoring model; this spec requires only that both route through `set-face-state` and that selecting a stencil clears text and vice versa (one content per face).

Budget: the binding and field code live in editor-studio delivery, not shared-renderer. The rasterizer and allocator live in `src/scene/` under shared-renderer. Both ratchets in `budgets/initial-delivery.json` are at zero headroom (observed: shared-renderer 1 byte, editor-studio 0), so the build includes an observed ratchet update in the same PR; no font bytes ship, so no font asset budget is needed this slice.

## 5. Thumbnail parity

`src/thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer` holds its own atlas instance. Contract: the allocator plus rasterizer are deterministic functions of document content, so the live atlas and the thumbnail atlas independently converge on identical slot contents without shared state. Requirements:

- The thumbnail path resolves slots through the same allocator code path; a thumbnail-private allocator or slot map is a defect (this is the seam the review pass will check first).
- `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` awaits font readiness and all text mask rasterization before capture, extending its existing atlas-ready wait. A thumbnail may never capture a face in the mask-pending state.

## 6. Recording

`src/export/streamRecorder.ts:createRecordingController` captures the live canvas, so resident text records for free at the recording frame rate. Requirements:

- Masks are resident before a cut lands: state playback resolves and uploads all text masks for the target pose before the cut commits, so recording never captures the mask-pending fallback. Same residency rule the sol scout states for morph cuts (`src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` keeps text changes as discrete cuts; colour tweens ride the existing instance-attribute path and never re-rasterize).
- Static text adds zero per-frame work; no render producer is held for resident text. Re-rasterization happens only on content edits.
- Portability caveat (documented, not solved): recordings capture this machine's system-font pixels; regenerating on another machine may differ. See Future Work.

## 7. Tests and gates

Feel-critical surfaces get automated proof on the production component tree — real `src/scene/CubeScene.tsx` layers, not a stripped fixture (a fixture that omits app layers certifies only itself).

1. **Browser gate: a face renders a given string.** Extend the `tests/stencilRenderingBrowserDriver.ts:runStencilRenderingBrowserGate` pattern: author a face with a known string through the production path, await residency, assert (a) covered pixels in the assigned slot region are non-zero and roughly match an independent 2D-canvas raster of the same string, (b) draw count, program count, and material/mesh/texture identity are unchanged from the no-text baseline (one-draw invariant, fixed program key), (c) disposal returns GPU resources to baseline.
2. **Unicode sample coverage.** The gate rasterizes a fixed sample set — Latin, Arabic (RTL), Devanagari, CJK, emoji-as-silhouette — asserting non-empty, non-clipped coverage per sample. Assert coverage presence, not pixel equality: glyph availability is machine-dependent (system fonts), and the gate must not encode one machine's fonts as truth.
3. **Text-key coverage on spec 1's allocator.** Where spec 1's own gates do not already prove it: dedupe (two faces, one string, one slot), release on refcount zero, generation-token staleness (slow raster resolving after a newer edit is discarded), capacity overflow behaviour (base-colour fallback plus observable counter). Controlled-red proof for each invariant: token removed → stale write lands; release broken → slot leaks; counter removed → overflow goes silent.
4. **Editor proof on the production tree.** Typing in the `face.text` field commits through `set-face-state`, the mask appears without a program recompile (probe the program cache), and the demand loop sleeps again after the raster pulse (no producer leak).
5. **Crispness visual gate (pre-merge, human-judged, scripted setup).** The §2 matrix: sizes × DPR 1/2/4 × projected 128/512/1024 px. Output is a pass/fail on the intended publish framing; failure triggers the 1024-tier decision, not ad-hoc tweaks.
6. **Thumbnail parity gate.** Live capture and thumbnail artifact of the same text-bearing document produce matching mask coverage in the face region.
7. **Delivery gate.** `scripts/check-delivery-budget.mjs` passes with the observed ratchet update; renderer ownership rules unchanged (rasterizer/allocator under `src/scene/`, editor field under editor-studio).

## 8. Deliverables

1. `rasterizeTextAlpha` in `src/scene/stencilAtlas.ts`, registered as the text-kind rasterizer on spec 1's allocator (§2, §3).
2. Text key extension on spec 1's allocator API: canonical content-hash keys, generation tokens, overflow counter (§3).
3. `{ kind: "text" }` member of `CubicellContent` through spec 1's requirements intake, with the §1 field set.
4. `{ kind: "string" }` branch of `src/editor/controlBindings.ts:ControlValueSchema` and the matching text field in `src/panels/ControlBindingField.tsx:ControlBindingField` (§4).
5. `face.text` binding beside `faceStencilBinding`, appended to `src/panels/panelDefinitions.ts:faceBindingIds`, routed through `set-face-state` (§4).
6. Font and text-mask residency await in `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` (§5).
7. Mask residency before cut commit in the playback path, so recording never captures the pending state (§6).
8. The §7 gates: browser gate, unicode samples, text-key coverage with controlled-red proofs, editor proof on the production tree, crispness visual gate, thumbnail parity, delivery gate.
9. Observed ratchet update in `budgets/initial-delivery.json` in the same PR (§4).

**Completion:** an authored string renders on a face through the production component tree with §7 gates 1–4 and 6–7 green, the §7.5 crispness gate passed at the intended publish framing, and zero change in draw count, program count, or program key relative to the no-text baseline.

## 9. Future work (documented, not specced)

- **Machine portability.** System fonts trade cross-machine visual identity for zero bytes: font selection, metrics, hinting, and coverage differ per platform. The escape hatch is a project-owned WOFF2 font asset (new `font` asset kind, binary payload store, `FontFace` registration before raster) — blocked on the payload store spec and out of scope here.
- **SDF growth path.** Distance-transform the same canvas alpha into the same R8 slot, one code-word flag bit (headroom above 64 in `writeFaceStencilAttribute`), smoothstep decode branch in `fragmentPartition`. Answers magnification blur without leaving the one-draw contract. Full MSDF stays rejected (forfeits browser shaping, needs font binaries).
- **Wrapping and overflow.** Needs a product definition (width, line height, max lines) and a Unicode line-breaking owner; explicit newlines until then.
- **Colour glyphs.** R8 flattens emoji to silhouettes. Colour emoji require an RGBA path (the F1 media atlas is the natural home) and a stated product requirement first.
