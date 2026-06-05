---
title: Cubicell rounded corner rendering
type: design
tags: [cubicell, renderer, geometry, corners, thumbnails]
summary: Scene owned socketed corner caps preserve straight rails and rigid faces
status: active
project: cubicell
confidence: high
created: 2026-08-16
updated: 2026-08-16
---

# Cubicell rounded corner rendering

## Problem

The rejected renderer spike rounded each edge rail along its full length. The desired result keeps every rail straight and every face planar. Softness belongs only at eligible cube vertices.

The current cube remains a hollow assembly of six face planes and twelve rectangular edge bars. Grid coordinates remain placement data. Cubicell content remains face media. Corner treatment is derived scene geometry.

## Usage

`createCubeSceneInstances` remains the shared producer for the live canvas and State thumbnails. Its output gains opaque, translucent, and ghost corner buckets. Existing callers do not author or persist a radius.

`renderCubeScenePartLayers` and `createThumbnailArtifact` consume one shared authored part specification. The specification classifies geometry, part kind, opacity, and picking policy.

## Shape

`CubeCornerLook` is scene policy. It owns the fixed radius, eight corner identities, cap eligibility, rail retreat, cap transforms, and owner edge selection.

`CubeCornerInstance` is a distinct render part. It carries `cubeId`, `cornerId`, an owner `edgeId`, transform, color, opacity, and tween. The stable key is `corner:<cubeId>:<cornerId>`.

The cap uses one shared socketed trihedral `BufferGeometry`. Its three square sockets meet rectangular rails. Curvature exists only around the outer vertex. Geometry is allocated once per mesh and instanced at most eight times per cube.

## Eligibility

A cap exists only when three mutually perpendicular, visually present bars from the same cube meet at one vertex.

Shared, collinear, concave, incomplete, non manifold, and zero gap contended junctions keep square rail ends.

Only the three incident visible rail matrices retreat. Domain edge segments, hit targets, and rectangular junction proofs remain unchanged.

Faces remain full size. Face media keeps its current UV and stencil contract.

## Shared ownership

- `cubeCornerLook.ts` owns the look, eligibility, transforms, and cap geometry.
- `cubeInstances.ts` emits corner instances and retreats eligible visible rails.
- `cubeInstanceSlots.ts` owns corner bucket names and stable keys.
- `cubePartLayerSpecs.ts` owns shared live and thumbnail part metadata.
- `instancedPartMeshCore.ts` accepts the distinct corner part kind through the existing custom geometry path.
- Persistence, authored operations, grid state, content types, domain edge resolution, picking, focus bounds, and selection kinds remain unchanged.

## Synthesis decision

The presentation owner from `candidate-grok.md` is the base. It keeps renderer look policy in `createCubeCellInstances` and leaves rectangular junction resolution unchanged.

The socketed trihedral cap, strict same cube eligibility, bounded geometry, owner edge styling, and shared part specification come from `candidate-codex.md`.

The cross judge rejected the Grok octant, global rail shortening, face inset, and burial only emit rule. It rejected the Codex domain cap map, expanded edge resolution result, incremental cap cache, and new geometry kind on the shared mesh factory.

## Tradeoffs

- We accept up to eight extra instances per cube in exchange for real localized curvature.
- We accept a fixed renderer look in exchange for unchanged document and transition schemas.
- We accept square corners when eligibility is incomplete in exchange for correct seams and hidden edge behavior.
- We keep fat rectangular hit targets in exchange for the current picking grammar.

## Verification

Contracts must prove radius zero equals the baseline, rails keep rectangular cross sections, cap geometry stays below 96 position vertices, cap bounds stay inside the three baseline rail boxes, bucket keys remain stable, and live plus thumbnail part specifications match.

Browser proof must cover face media without cropping, cap clicks selecting the owner edge, hidden edges restoring square ends, mixed thickness sockets, nonuniform cube size, zero gap seams, motion scrub, State thumbnails, and Storyboard.

## First implementation slice

Remove the rejected rounded rail geometry and restore the baseline edge thickness and coverage geometry. Extract shared part specifications. Add scene owned corner look and empty buckets with radius zero equivalence. Then add the socketed cap geometry, eligible rail retreat, live layers, thumbnail layers, and focused contracts.
