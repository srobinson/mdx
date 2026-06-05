# Architect review — cubicell specs 1–4

Reviewer: grok (`cubicell:general:6:3.6`).  
Contract: `~/.mdx/projects/cubicell-content-scout-synthesis.md` reuse map + dispositions; `LESSONS.md`.  
Snapshot: main @ `3725921` (as bound by the specs).  
Date: 2026-08-09.

## Cross-cutting

| Theme | Finding |
|---|---|
| Union ownership | Spec 1 owns `src/domain/content.ts:CubicellContent`. Spec 4 states this correctly. Spec 2 still names only `CubeFaceContent`. Spec 3 lists field requirements without designing the union (good) but pollutes them with deleted figure language (bad). |
| Naming | Spec 1: `CubicellContent` canonical, `CubeFaceContent` semantic alias. Briefs/scouts used `CubeFaceContent`. Spec 2 never mentions `CubicellContent`. LESSONS approved-name inventory is deferred CI; review must enforce names. Implementers should write `CubicellContent` (and alias only at the face carrier). |
| R8 allocator | Spec 1 fully designs dynamic R8 atlas (`stencilAtlas.ts:createStencilAtlas` + `getSlot` by stencilId). Spec 2 claims the same slice "lands the dynamic slot allocator" for seeds, library, and text. One owner: Spec 1. Spec 2 may only require text keying and `rasterizeTextAlpha` on that owner. |
| RGBA slot API | Spec 3 owns `mediaAtlas.ts:createMediaAtlas` + slot-rect; Spec 4 reuses it for transient motion leases without a second atlas. Correct. |
| Fit | Spec 1 removes inert stencil `fit` and defers optical fit to image review. Spec 3 still says "Existing figure presentation fields (region, fit, tint)". Spec 4 correctly says Spec 1 owns the fit enum for video/shader variants. Spec 3 must drop figure/fit language. |
| Version tables | Spec 1 matches repo (`indexedDbProjectStorageVersion` 9→10). Spec 3 says 4→5. False against main. |
| Timing gates | LESSONS: GPU acceptance gates assert counts, never timings (SwiftShader). Spec 4 hard-gates p50/p95 ms. Diagnostic only. |

## Spec 1 — content union foundation

**Verdict: clean**

Evidence:

- Owns the content union; §12 is requirements intake for 2–4, not dormant members.
- Reuse map §4 is `file:symbol` only (no line anchors).
- Constraints: one-draw, fixed program key `cubicell-face-content-v1`, bump+reset, no WebGPU/TSL, no migrations, single GPU writer.
- Controlled red/green for Library source, dynamic slot, compact discriminant.
- Deliverables, gates, completion line present.
- Dual resolution path (synthesis ownership disagreement) closed on Library `resolveStencilContent`.

Nits (non-blocking): completion line says "CubeFaceContent foundation" while the type table leads with `CubicellContent`; atlas key model is stencilId-only — Spec 2 must extend keys, not re-own the allocator.

## Spec 2 — face text

**Verdict: issue (major + structural)**

1. **Major — dual R8 allocator ownership.** §3: "This slice lands the dynamic slot allocator that replaces the fixed seed map". Spec 1 §8 already lands that owner for Library stencils. Synthesis disposition: one dynamic slot at `getStencilAtlasSlot`. Spec 2 must rephrase as requirements on Spec 1's owner: content-hash keys, refcount, `rasterizeTextAlpha` sibling of `rasterizeSvgAlpha`, generation tokens, overflow counter. "A second allocator anywhere is a build defect" is right; Spec 2 must not be the second design authority.

2. **Major — naming.** Requirements target `CubeFaceContent` only. Spec 1's canonical name is `CubicellContent`; alias is explicit. Spec 2 should require a `text` member of `CubicellContent` (carrier remains `CubeFaceContent` alias).

3. **Structural — checklist (d).** Binding inputs in the intro; no numbered deliverables list; no completion line. Controlled-red appears only for the generation token, not as a systematic invariant set. Reuse citations are `file:symbol` (good).

4. **Sequencing.** Binds `faceStencilShader.ts` / `faceStencilProgramKey` while Spec 1 renames to content symbols and `cubicell-face-content-v1`. Depends on Spec 1; should cite post-foundation symbols or state the dependency.

Honored: text-as-stencil R8, system fonts, one-draw, no program change for text, no WebGPU, thumbnail/recording parity, no union redesign.

## Spec 3 — payload store, images, RGBA atlas

**Verdict: issue (major + structural)**

1. **Major — wrong IndexedDB version.** "bump `indexedDbProjectStorageVersion` 4 → 5". Repo is **9** (`src/persistence/indexedDbSchema.ts:indexedDbProjectStorageVersion`, test pins 9). Spec 1 correctly uses 9→10. After Spec 1, this slice needs 10→11 (or a single combined bump plan). As written, the version plan is false.

2. **Major — figure/fit language vs Spec 1.** §2: "Existing figure presentation fields (region, fit, tint) apply per spec-1's discretion". Spec 1 deletes `CubeFaceFigure` and removes `fit`. Image optical policy is open intake in Spec 1 §12 (contain/cover, optional focal), not "existing figure fields". Rewrite as: union needs `image` + `imageAssetId` only; presentation fields Spec 1 defines for the image variant after review.

3. **Structural — checklist (d).** No completion line; deliverables are prose, not a closed list. Gates and controlled-red present. Reuse bindings `file:symbol`.

4. **Minor — program key sequencing.** Introduces `cubicell-face-media-v1` while Spec 1 ships `cubicell-face-content-v1`. One composed program: Spec 3 must version the single fixed key once when the media sampler lands, not invent a parallel program identity.

Honored: payload via existing promote transaction (not a second storage system), one-draw, fixed key rule intent, capabilityIncrements `media`, no WebGPU, slot-rect shared with motion, no migrations, out of scope for union design.

## Spec 4 — video and seeded shader motion

**Verdict: issue (major + structural)**

1. **Major — timing as acceptance gate vs LESSONS.** LESSONS (GPU gates): assert programs, buffers, mesh/material identity; **never timings**; wall clock is diagnostic only. Spec 4 §7 makes p95 ≤ 3.0 ms and p50 ≤ 2.0 ms the "initial gate" with remeasurement triggers. Keep draw/program/upload/copy counts as gates; demote ms numbers to retained diagnostics with two clean reruns, not pass/fail.

2. **Structural — checklist (d).** Strong runtime design, gates, controlled-red list, out of scope. Missing formal deliverables list and completion line.

Honored: Spec 1 owns union (lists `video`/`shader` fields only); Spec 3 owns RGBA atlas + slot-rect; one-draw; fixed visible program; seeded shaders only; no user GLSL/TSL/WebGPU; named producers (`faceVideo`, `faceShader`); single GPU writer; poster/thumbnail without motion producers; capacity demotion to poster not dedicated meshes.

## Required patches before build approval

| Spec | Must change |
|---|---|
| 1 | Optional: completion line lead with `CubicellContent`; note that later R8 kinds extend slot keying on the same owner. |
| 2 | Drop "lands the dynamic slot allocator"; require text raster + multi-kind keys on Spec 1's atlas; name `CubicellContent`; add deliverables + completion line; bind post-Spec-1 content shader symbols. |
| 3 | Fix IDB bump from actual version (9 or post-Spec-1 10); delete figure/fit language; single program key succession; deliverables + completion line. |
| 4 | Timing → diagnostic only; count gates remain; deliverables + completion line. |

## Checklist scorecard

| Check | Spec 1 | Spec 2 | Spec 3 | Spec 4 |
|---|---|---|---|---|
| (a) Union ownership / intake / naming | pass | fail name + dual allocator claim | fail figure/fit | pass |
| (b) Slot allocator seams | owns R8 | conflicts with 1 | owns RGBA; 4 reuses | reuses 3 correctly |
| (c) One-draw, fixed key, seeded shaders, bump+reset, no WebGPU, budget | pass | pass | pass (key succession note) | fail timing vs LESSONS |
| (d) Inputs, file:symbol, deliverables, gates+red, completion | pass | partial | partial | partial |
| (e) Reuse-map fidelity | pass | pass if allocator rephrased | pass | pass |
