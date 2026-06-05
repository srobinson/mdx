---
title: Phosphene Presence Stage 3b — face data, provider, faceWeight blend
type: sessions
tags: [frontend, phosphene, presence, sim, attractors, glb, extraction, warroom]
summary: Built slice 3b of the presence form — one-time face-curve extraction from the avatar glb, a face attractor provider, and a faceWeight column blended into the sim via a partition-of-unity identity.
status: active
source: frontend-engineer
confidence: high
created: 2026-07-04
updated: 2026-07-04
---

# Presence Stage 3b: face attractors (data + provider + blend)

Warroom slice. Builder: claude (frontend-engineer, Opus). Reviewer: codex (adversarial).
Branch `idea/presence` @ `d975086` (parent `a023656`, slice 3a). Topic `phos-presence-s3`.

## Summary

Gave the presence organism a face: eyes, brows, and a mouth that opens with speech,
emerging from the same dust the sim already drives. Four deliverables + tests, all gates
green, perf under the 4ms budget.

1. **`scripts/extractFaceCurves.ts` -> `src/presenceFaceData.ts`.** One-time reader of the
   avatar at `2688160`. KEY DISCOVERY: the geometry is NOT in `faceGeometry.ts`/`faceRig.ts`
   (the orchestrator's named files) — those are runtime loaders with zero static
   coordinates. The real geometry is `public/face.glb`, a gltfpack bundle using
   `EXT_meshopt_compression` + `KHR_mesh_quantization`. Faithful per-vertex reconstruction
   needs a full glTF loader + meshopt decoder (out of a slice's scope). So the script reads
   the glTF JSON chunk (decode-free, deterministic): asserts the ARKit rig identity (named
   nodes + 52 morph target names incl. `browInnerUp`/`jawOpen`/`mouth*`), lifts the real
   symmetric eye-group translations (`±3.2895, 2.3816, -2.612`) and head bbox aspect, and
   traces clean landmark curves in canonical `[-1,1]` with eye placement anchored to the
   avatar's real measured ratio (`eyeY = eyeX * eyeHeight/eyeSpanX`). This is the plan's
   sanctioned fallback ("hand-traced control points, still data"), kept honest by the real
   anchors. Re-run is byte-identical.
2. **`src/presenceFace.ts` provider.** Turns the curves into an `AttractorSet` (12 homing
   points: 2 eyes, 4 brow, 6 mouth), mouth upper/lower lips displaced by `signal.level`
   before emission. Allocation-free (member-owned set + baseY/openSign scratch).
3. **`faceWeight` column** (speaking 0.85, thinking 0.3, waiting/sleeping 0; excited +0.4k).
   The integrator blends the abstract attractor SUM toward the face set by the cross-faded
   `faceWeight`. `faceGain` override field on the sim (leva + test hook; 0 = faces off).
4. **Tests**: curves in bounds, mouth monotonic in level, faceWeight continuity through an
   interrupted transition (extends the weights test), faces-off reproduces the 2c signature
   ordering, extraction byte-identical + matches the committed file, and faces-on measurably
   moves the field.

## Architecture Decisions

- **Partition-of-unity blend (the load-bearing idea).** The per-activity `weights[]` always
  sum to 1. So blending EACH activity's abstract set toward the face (spec wording, "M1") is
  mathematically identical to blending the weighted SUM toward the face once ("M2"):
  `F = (1-fw)*Σ wᵢ·abstractᵢ + fw·face`. I implement M2, evaluating the face set ONCE per
  particle instead of once per active set. Identical result, no set mutation, no
  `ATTRACTOR_CAPACITY` pressure, and the transition case (two active sets) stops
  double-counting the face — which is exactly what the perf probe stresses. `fw=0` skips the
  face branch entirely -> 2c exact.
- **Extraction anchors to real data, not invention.** Eye placement ratio comes from the
  glb's actual eye-group translations (decode-free JSON), so the traced face carries the
  avatar's proportions. Provenance asserts guard against tracing the wrong asset.
- **faceGain override** (default 1, leva 0..2, clamped) is both the spec's debug
  "faceWeight override" and the test hook to force faces off. Mirrors 3a's `glyphGain`.
- **Refactor to hold the doctrine limits.** Adding the feature pushed `presenceSim.ts` over
  300, so I split the per-frame physics into `presenceIntegrator.ts` (SimField +
  integrateParticles + physics consts) and moved `accumulateAttractorForce` to
  `presenceAttractors.ts` (cohesive: how a particle feels attractor force). Every touched
  function is < 150, every file < 300.

## Performance Notes

- 12k worst-mood probe (speaking.confused i0.7, transition 0.5 = two active sets, saturated
  signal, dt 0.1): **min 3.66–3.83ms** across runs vs the 4ms budget. 2c full-form baseline
  was 2.4ms; the face adds ~1.3ms (12 homing points × 12k).
- M1 (append face into each active set) first measured **min 4.40ms** (FAILED) because the
  transition case appends the 12 face points into BOTH active sets. M2 (partition-of-unity,
  face once) brought it to 3.8ms. The perf gate is the whole reason M2 beats M1 here.
- Probe asserts on min-of-200 (least-preempted frame); the warroom machine was load 45–76,
  so p50 spikes to 5–7ms are pure scheduler steal. Min stayed < 4ms every run.
- 3c adds proximity shading on top; the spec already plans a precompute distance grid if the
  per-frame cost then breaks budget.

## Deviations from Spec

- **Geometry source is `public/face.glb`, not `faceGeometry.ts`/`faceRig.ts`.** The
  orchestrator named the `.ts` files; they are loaders. The glb is the avatar. The script
  reads the glb (still "the face avatar at 2688160", still the only artifact crossing the
  restore point). Full vertex decode deferred (needs meshopt decoder); decode-free JSON
  anchors used instead — the plan's explicit fallback.
- **`faceGain` multiplier instead of a raw faceWeight override sentinel** (same shape as 3a).

## Open Items / Follow-up

- 3c: proximity-biased density shading (heavy glyphs claim features), palette shift wiring,
  and the live tuning pass (weights, radii, mouth-open amount, faceWeight table) against the
  final skin. The face attractors here are the seam it plugs into.
- Face points currently pass the abstract `coherence` to the force (slight orbit). 3c may
  want homing-only (coherence 0) for crisper features; left consistent for 3b, a tuning call.
- Gap closures (spec §6) still belong to a later slice.
