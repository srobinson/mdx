# Scout — typography on faces, architecture lens

Read-only recon, 2026-08-09, repo cubicell @ main (3725921). Builds on the converged reuse map in `cubicell-content-scout-synthesis.md`; citations are `file:symbol`. Decisions taken as given: face media first, motion in scope, `CubeFaceFigure` becomes a discriminated `CubeFaceContent` union.

## Existing text machinery: none found

Searches run: `fmm_search term "font"` — only `@fontsource/geist-mono` latin-400/700 CSS imports in `src/main.tsx`; `fmm_search term "glyph"` — nothing; grep `msdf|troika|TextGeometry|fillText|measureText|FontFace` across `src/` and `tests/` — nothing. There is no text rendering, no font asset kind, no glyph pipeline. The one usable font fact: Geist Mono is already delivered to the document, so `CanvasRenderingContext2D.fillText` can rasterize with it once `document.fonts` has loaded it.

## Reuse map deltas for text

The synthesis map (§2) holds unchanged; text adds no new owners, it binds to existing ones:

- **Rasterization seam:** `scene/stencilAtlas.ts:rasterizeSvgAlpha` already proves the canvas-2D → alpha-coverage → slot path. A `rasterizeTextAlpha` sibling is the whole new rendering concept: `fillText` on the same 2D canvas machinery, read alpha, write slot via the existing `writeStencilSlot` (which already handles region inversion). Writer stays inside `stencilAtlas.ts` ownership.
- **Slot resolution:** `scene/stencilAtlas.ts:getStencilAtlasSlot` — today a fixed seed map. Text *requires* the dynamic slot allocator the synthesis already mandates as refactor-first for the half-open stencil library seam. One allocator, keyed by content hash, serves both user stencils and text strings. Text is a second client of that refactor, not a second allocator.
- **Attribute writer:** `scene/faceStencilShader.ts:writeFaceStencilAttribute` unchanged in shape; only the slot lookup routes through the allocator. The single GPU-writer chain (`cubeInstances` builder → `syncInstancedPartMesh`/`patchInstancedPartMesh` → `writeStencil`) is untouched.
- **Fragment shader:** zero change for the first slice. Text is coverage in a slot; `fragmentPartition` already blends it.
- **Domain:** a `{ kind: "text" }` variant of the `CubeFaceContent` union carrying `text`, plus the existing `region`/`fit`/colour-role fields. The string is tiny and plain JSON, so it rides `recordCodecs/compactPose.ts:encodeCell` and the record codecs with only version bumps. **Unlike images and video, text has no binary-store prerequisite.** That is the decisive cost difference.
- **Font readiness:** rasterization must await `document.fonts.ready` (or a `FontFace.load` check) or text bakes with the fallback font; same wake pattern as `scene/CubeScene.tsx:StencilAtlasReadyDriver`, which already exists to invalidate on atlas readiness.

## Candidate evaluation

**A. Text-as-stencil (canvas rasterization into the R8 atlas) — fits, and it is the slice.**
Monochrome coverage is exactly what the atlas and the tint contract express: form/field colour roles, region inversion, per-instance rgb tint all apply to a word with no new semantics. One-draw invariant fully preserved; zero new programs, so no compile hitch risk on the drag path at all. Browser `fillText` provides Unicode shaping, bidi, and font fallback for free, which directly answers the unicode gap (colour emoji flatten to monochrome coverage; acceptable for a tint-contract face, worth stating to Stuart). Recording is free (in-canvas). Costs and limits: bitmap coverage at 512² per slot with LinearFilter and no mipmaps means shimmer when small and softness when a face fills the screen; one slot per distinct string, so capacity is 16 slots today minus 2 seeds (growing the atlas to 4096² gives 64 slots for a 16 MB R8 texture if needed); a word fits, a paragraph does not.

**B. SDF upgrade inside the same seam — the growth path, not the slice.**
Post-process the canvas alpha with a distance transform into the same single-channel slot, and add one code-word flag bit (headroom above 64 exists in `faceStencilShader.ts`) selecting a smoothstep decode branch in `fragmentPartition`. Keeps browser shaping, keeps one draw and one program, fixes scale quality. This is the answer to "text looks soft when zoomed" if it arises; it changes nothing about ownership. Full MSDF (multi-channel, per-glyph atlas, own layout engine) is strictly worse here: it forfeits browser shaping, so Unicode becomes a harfbuzz-class problem, it needs font binaries (the blob-store prerequisite returns), and per-glyph quads either exit the instanced buckets or add a new instanced glyph layer. Nothing in the stated product need (a face can show a word, in Unicode) justifies that concept count.

**C. Geometry text (TextGeometry / troika-three-text) — does not fit.**
Per-face meshes break the one-material-per-bucket invariant for a medium that has a cheaper in-contract answer; troika brings its own SDF pipeline and font parsing against a shared-renderer ceiling with zero headroom (`budgets/initial-delivery.json`); complex-script shaping is again unsolved. Only justified if text must be extruded 3D geometry, which nobody asked for.

## Cross-cutting checks

- **Dynamic vs static atlas:** text forces the atlas from build-time-static to runtime-dynamic. The mutation contract is small: allocator assigns a slot, rasterize, `texture.needsUpdate`, one scheduler pulse. Eviction policy is content-hash LRU only if distinct strings ever exceed capacity; defer until measured.
- **Thumbnail parity:** `thumbnail/thumbnailRenderer.ts:createOrthographicThumbnailRenderer` holds its own atlas instance. The allocator plus rasterizer must be deterministic from document content so both atlases independently converge on the same slots, or the atlas becomes shared state. Deterministic derivation is the cheaper contract; name it in the build brief so gpt-sol does not hide a second allocator in the thumbnail path (seam blindness, exactly his pattern).
- **Motion:** static text needs no producer. If text later animates (per-character reveal, scroll), it re-rasterizes per step under a named `renderProducers` entry per the `TransportFrameDriver` precedent; no new mechanism.
- **Budget:** rasterizer + allocator are a few KB inside `scene/` (shared-renderer, near-zero headroom, but this is small and load-bearing); the text input control belongs with the editor bindings (`editor/controlBindings.ts:faceStencilBinding` pattern, `panels/panelDefinitions.ts:faceBindingIds`), outside the renderer root.
- **Dual resolution paths:** the synthesis flags `seededStencils.ts:resolveStencilContent` vs the direct seed read in `rasterizeSeededStencils`. The allocator refactor is the moment to unify; text content resolution must go through the single unified path, not add a third.

## Cheapest credible first slice: "a face can show a word"

1. `CubeFaceContent` gains `{ kind: "text", text, region, fit, color }`; wire version bump-and-reset (no migrations, single user).
2. Dynamic slot allocator replaces the fixed map at `stencilAtlas.ts:getStencilAtlasSlot` (the already-mandated refactor; seeds become pre-allocated entries).
3. `rasterizeTextAlpha` beside `rasterizeSvgAlpha`, awaiting document fonts, Geist Mono default.
4. No shader change, no new draw calls, no new programs, no binary storage, thumbnails converge by construction.
5. Editor: one text field binding on the face panel.

Everything in that list except step 3 is work the stencil library seam already owes. The genuinely new code is one rasterization function and one input control.
