---
title: Phosphene Presence Stage 3a — glyph encoding, ASCII atlas, density-ramp skin
type: sessions
tags: [frontend, phosphene, presence, webgl, glsl, three, glyph, warroom]
summary: Built slice 3a of the presence form — contract-owned glyph encoding, a 16x8 ASCII atlas, arithmetic shader UV mapping, and an allocation-free density-ramp skin with hysteresis.
status: active
source: frontend-engineer
confidence: high
created: 2026-07-04
updated: 2026-07-04
---

# Presence Stage 3a: glyph skin (contract + atlas + ramp)

Warroom slice. Builder: claude (frontend-engineer, Opus). Reviewer: codex (adversarial).
Branch `idea/presence` @ `a023656` (parent `cbf0e3f`). Topic `phos-presence-s3`.

## Summary

Turned the presence form's dot dust into an ASCII "dust-to-type" skin, and made the
WebGL backend agree with SVG on a single glyph byte encoding. Four deliverables + tests,
all gates green, glyph orientation verified upright via headless CDP.

1. **`render/contract.ts` owns the encoding.** Added `GLYPH_DOT=0`,
   `GLYPH_PRINTABLE_MIN/MAX` (33..126), `GLYPH_BULLET`, and `glyphChar()` /
   `glyphIsDot()` / `glyphIsPrintable()`. The one sentence: *a glyph byte is an ASCII
   code; 0 is the dot, 33..126 render that character, everything else renders the
   bullet.* SVG's local `glyphText`/`DOT_GLYPH` collapsed into the contract (DRY).
2. **`glyphAtlas.ts` → 16x8 grid of 64px cells.** Dot (cell 0, radial-gradient SDF,
   `GLYPH_DOT_COVERAGE` kept), bullet (cell 1), 94 printables (cells 2..95) via
   monospace `fillText`; alpha carries the shape. Refcount lifecycle unchanged.
   Exports `glyphAtlasCell()` + grid constants.
3. **`glyphMaterial.ts` arithmetic UV.** Replaced the 2c `glyph*cell` 4-cell
   placeholder (and the `uAtlasCells` uniform) with dot/printable/bullet-fallback cell
   selection, mapped into the grid with a V-flip for `CanvasTexture.flipY`. Shader
   constants are interpolated from the atlas module's exports, so JS `glyphAtlasCell()`
   and the GLSL cannot drift.
4. **`presenceSkin.ts` (new) density ramp.** Allocation-free per-particle selection:
   `weight = clamp01(intensity) * clamp01(glyphWeightBias * glyphGain)`, quantized to a
   ramp index with a 0.15 hysteresis dead-band so glyphs switch on threshold crossings,
   not per frame. Dot is the bias-0 end (no separate mode). `presenceForm.ts` holds
   per-frame `{sim, skin}` and drives it. Ramp string + gain are leva-tunable.

## Architecture Decisions

- **Contract as single owner, both backends implement it.** Rather than duplicate the
  33..126 boundary in SVG and WebGL, the boundary lives once in `contract.ts`; SVG calls
  `glyphChar()`, the atlas calls the same helpers to draw, the shader replicates only the
  cell arithmetic from exported constants. Zero drift by construction.
- **Skin selection lives in the form layer, not the sim.** `presenceSkin.ts` is a
  separate cohesive module (unit-testable in isolation) but is part of "the form"; the
  sim (`presenceSim.ts`) stays glyph-agnostic, as the spec requires.
- **Hysteresis needs per-particle state.** Kept a retained `Uint8Array rampIndex` in the
  skin so the dead-band has a previous index to compare against; reverse-mapping a glyph
  byte back to an index each frame would have been O(rampLen) per particle.
- **Leva "gain" instead of a raw bias override.** Deliverable 4's required leva control
  is the ramp string; the spec's debug surface also lists a `glyphWeightBias override`.
  Shipped it as a `glyphGain` multiplier (default 1, range 0..2) — always meaningful, no
  sentinel/toggle, preserves the state-driven cross-fade, and gain 0 cleanly forces the
  dot skin. See Deviations.

## Performance Notes

- Perf probe (`tests/presencePerf.test.ts`): 12k particles, worst mood
  (speaking.confused i0.7, saturated signal, dt 0.1), full `presenceForm.update` path.
  **min ≈ 2.4ms, p50 ≈ 2.9ms** vs the 4ms budget. Stage 2 baseline "1.68ms" was
  sim-only; this probe measures the wider full-form scope and is still under budget.
- The added skin selection is not the bottleneck (a round + a few float ops per
  particle, no allocation). The measured cost is dominated by the pre-existing
  `sim.tick` + the per-particle intensity `sqrt` loop.
- **Probe asserts on MIN-of-200, not median.** The warroom machine was ~50-60 load on 12
  cores, which inflated the median to 4-7ms (pure scheduler preemption). Min is the
  least-preempted frame ≈ true single-thread cost and is stable across runs. Documented
  in the test.

## Verification

- `vp check` (format + lint + types), `vp test` (146 tests), `vp build` all green.
- **Glyph orientation** (tests can't run GLSL): injected a self-contained WebGL2 replica
  of the atlas + fragment UV math via CDP, rendered an asymmetric 'F', and bucketed
  `readPixels` by quadrant — TL 49120 > TR 32003 > BL 21551 > BR 0, i.e. upright and
  unmirrored (a vertical flip would load BL/BR; a horizontal mirror would load TR/BR).
- Real app under headless Chrome (swiftshader) rendered the presence organism with amber
  dust-to-type glyphs and bloom, zero shader-compile/runtime errors.

## Deviations from Spec

- **`glyphGain` multiplier instead of a raw `glyphWeightBias` override** (spec Debug
  surface). A gain (default 1, 0..2) is always meaningful, needs no sentinel, keeps the
  per-state cross-fade intact, and gain 0 gives the pure dot skin for free. The required
  ramp-string control is present as specified.
- **Gap closures (spec §6) intentionally NOT in 3a**: SVG glyph `depthScale`, the
  `SvgRenderer` one-field-per-frame assert, the `attach()` fallback-transform reset, and
  node-driven test parity. The message's deliverable list scopes 3a to encoding + atlas +
  skin; those belong to later slices (3b touches the sim seams).

## Open Items / Follow-up

- Face attractors (3b) and proximity-biased density shading (3c) are the next slices;
  3a's ramp is the seam they plug into (bias per particle by face proximity).
- The atlas legibility at 64px cells is fine at demo sizes; if small-size glyphs read
  poorly later, bump the cell to 96/128 (power-of-two growth, no code change).
- `presence.test.ts` "maps the sim" now asserts a dust+ramp mix (not all-dots) and a
  gain-0 all-dots case — inherited test updated to the new skin semantics.
