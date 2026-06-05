---
title: Sea-scene signal response (Open Water reacts to agent state)
type: sessions
tags: [frontend, webgl, glsl, ambient, signal, little-background-lab, transport-matters]
summary: Made reference-sea / reference-sea-ii consume the ambient setSignal via a chroma-gated, luminance-preserving mood wash; verified headless and shipped (PR #16).
status: active
source: frontend-engineer
confidence: high
created: 2026-06-13
updated: 2026-06-13
---

# Sea-scene signal response

## Summary

The transport-matters agent greenlit Phase 3 (`setSignal`) host-side, but the sea
scenes — `reference-sea` and `reference-sea-ii` (their Open Water default) — were
**signal-inert**: only `proof-grid` / `solid` / `photo-study` read `signalColor()` /
`uIntensity` in their fragment bodies. So Phase 3 would have shipped invisible on the
only scene users see. Stuart greenlit authoring the sea response (the palette is fixed;
the "how it reads on water" was the engineering call).

Shipped to lab `main` as squash `6b1520c` (PR #16, `littleorgans/little-themes`):
`reference-sea.ts` (the wash) + `createAmbientBackground.ts` (`export const STATE_BLEND_MS`).

## Architecture Decisions

- **Global wash, not localized.** The engine takes ONE `AmbientSignal {state, intensity}`;
  there are no per-pane signals. Multiplicity is folded host-side (transport-matters:
  `waiting > error > working > idle`, max-severity wins). The sea is one full-screen
  fragment shader with global uniforms and is screen-space (ignores pan/zoom), so it
  physically cannot render per-pane state. The response is therefore a uniform wash.
- **Chroma-gate, not just intensity.** Gate the wash by the signal color's chroma
  (`max(rgb)-min(rgb)`), so idle "ivory" (near-grey, chroma≈0) is an automatic no-op
  regardless of its intensity, while sage/amber/rose read clearly — without the shader
  needing to know the discrete state name. `sigStrength = clamp01(chroma*3.2) * intensity`.
- **Luminance-preserving recolor.** `mix(col, sig * dot(col,LUMA) * 1.18, sigStrength*0.5*pulse)`
  re-hues the sea at its own brightness, so exposure is unchanged — same sea wearing a mood.
  Applied to the water body; foam tint and a horizon sky tint reinforce it.
- **Reduced-motion contract.** The state cross-fade (`signalColor` via `uStateBlend`) runs
  off the engine's `performance.now()` clock, so state changes still animate under reduced
  motion; only `pulse` (rides `uTime`, which is frozen when reducedMotion) stops. Motion
  stilled, mood still legible — matches the contract handed to transport-matters.
- **STATE_BLEND_MS exported.** Was a private const; now `export const` so the TM port's
  signal-dwell shares the 900ms constant instead of duplicating the literal (DRY across the
  verbatim port; pre-empts keyword drift).

## Performance Notes

First attempt used a flat intensity-scaled multiplicative tint and measured a <3% color
shift — effectively invisible at midday. Recalibration to chroma-gating + luma-preserving
recolor is what made idle-vs-active read while keeping idle a true no-op. No runtime cost
change (same per-frame uniform writes; the shader math is a handful of extra ops).

## Verification

`tsc` only validates the shader as a string; GLSL compiles at runtime. Proved it headless
via CDP (Node 25 global WebSocket, chrome-headless-shell + swiftshader, no deps): booted the
built app at a simulated noon clock (injected `Date` override via
`Page.addScriptToEvaluateOnNewDocument` before navigate), selected Open water
(`reference-sea-ii`), drove all four states through the harness's real pane-click→`setSignal`
path, captured per state. Result: zero shader-compile errors in a live WebGL context, idle
natural blue, working/waiting/error visibly distinct, exposure preserved. `npm run build`
clean, 50/50 tests pass.

## Deviations from Spec

None on the palette (idle ivory / working sage / waiting amber / error rose is the prelude's
fixed vocabulary). The wash *magnitude* and the chroma-gate are engineering choices, not
spec'd. The lab harness's own `STATE_PRESENCE` (idle .3 / working .7 / waiting .85 / error .8)
differs slightly from the host-locked intensities (.3/.5/.8/1.0); the shader calibrates to the
locked values, and the harness presence map is only for the lab demo.

## Open Items

- The wash is subtler at night (dark scene) by design; clearest at midday. Frame-diff
  verification (TM Playwright) should pin a fixed `dayProgress`.
- Inter-active separation (working vs waiting vs error) is compressed over deep blue water
  because the hues partly cancel the blue base; idle-vs-active is unmistakable. Could push
  harder if Stuart wants stronger per-state distinction, at some cost to subtlety.
- transport-matters picks this up on their next `ambient/` port re-sync (their agent went
  offline before I could notify; the change is in lab main regardless).
- Parked (not started, need Stuart's word): fold-order and count-sensitivity of the host
  signal fold (his product calls); legibility-floor text-shadow measurement; the `ambient/`
  naming/placement refactor (rides the next consumer migration — lilo first).
