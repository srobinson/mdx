# Cubicell renderer relief decision

Date: 2026-08-16  
Baseline: `ee511b8a8557c3d4af48079af6dfb4d7a88aab59`

## Decision

Discard the visual spike code. Promote physical edge relief and deterministic shading as a production renderer direction.

The decisive comparison was:

1. Current flat: rigid box geometry with unlit black and white surfaces.
2. Sharp and lit: current rigid geometry with soft light.
3. Physical bevel: rounded geometry with the same soft light.

Lighting materially improves depth. Physical relief remains visibly stronger because it changes silhouette, junction softness, highlights, and shadow falloff. A one segment rounded proxy preserves the visual result. Three's installed geometry costs 324 position vertices at one segment versus 24 for the current box, so it is unsuitable as the production geometry.

## Production shape

Keep Cubicell's six face planes, twelve edge identities, stable instance slots, patches, motion, picking boxes, selection chrome, and thumbnail renderer.

Add one canonical edge relief prism with:

- a low vertex rounded or chamfered longitudinal profile;
- flat rectangular collars at both ends so current junction ownership remains valid;
- an axis aware matrix that rotates the canonical bar onto X, Y, or Z;
- radius derived from local edge thickness;
- deterministic normal shading shared by live and thumbnail renderers.

Target no more than 96 position vertices. Keep the current rectangular picking boxes. Do not add authored bevel state, UI controls, persistence, renderer forks, or new caches.

## Integration seams

- `src/scene/cubeInstances.ts`: derive visible and ghost edge matrices from the canonical relief axis. Keep hit target matrices unchanged.
- `src/scene/instancedPartMeshCore.ts`: select relief geometry and shading for visible edge meshes through the existing shared factory.
- `src/scene/edgeCoverageCore.ts`: align coverage with the same canonical axis and prevent square coverage leaking around the relief.
- `src/thumbnail/thumbnailArtifact.ts`: classify authored edge layers explicitly so the shared factory guarantees parity.

## Promotion gates

- No junction gaps for blocks, unequal thicknesses, rotations, or all three axis corners.
- No radius breathing across size, placement scale, thickness, opacity, or colour motion.
- Face and edge interaction, selection chrome, focus, and neighbor placement remain unchanged.
- Live capture and storyboard thumbnails show the same silhouette and shading.
- Draw calls do not increase. Delivery budgets pass without raised limits.
- Focused geometry and browser contracts pass, followed by the full unit, browser, build, and budget gates.

## Evidence

- Visual comparison: `/Users/alphab/.mdx/TMP/pstack/01a0097c-9174-7e33-8b5d-81eff87f15fc/cubicell-render-spike/visual-gate/`
- Renderer scout: `/Users/alphab/.mdx/projects/cubicell-scout-renderer-spike.md`
