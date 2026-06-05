---
title: Phosphene Aurora Organic Wallpaper Mode
type: sessions
tags: [frontend, phosphene, aurora, svg, wallpaper]
summary: Added deterministic aurora band variation, calm shimmer and surge controls, plus a no UI wallpaper route.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented the mailbox requested Aurora SVG refinement and wallpaper mode. The aurora form now has deterministic per band character, subtle horizontal shimmer, and a slow global surge. The new `?wallpaper` route renders only the aurora, uses the SVG renderer by default, fills the viewport with the night sky background, and omits Leva plus microphone controls.

## Architecture Decisions

- Centralized URL mode parsing in `src/appMode.ts` so `?embed`, `?wallpaper`, form selection, and SVG renderer selection share one contract.
- Kept `?embed` precedence over `?wallpaper` to avoid changing the existing embed route.
- Precomputed aurora per band character into retained `Float32Array` resources when the frame is created. The steady render path only reads those arrays and applies time math.
- Added Aurora controls for `variation`, `shimmerSpeed`, and `surgeAmount` with calm defaults.
- Used a larger wallpaper scale only in wallpaper mode so the normal app defaults remain unchanged.

## Performance Notes

- No per frame string allocation was added to the SVG band hot path.
- Per band random character is deterministic and computed during frame creation, not during every frame.
- Required gates passed: `vp check`, `vp lint .`, `vp build`, and `vp test`.
- Build output retained the preexisting large chunk warning, with `dist/assets/index-BwB9feBh.js` at 404.22 kB gzip.

## Deviations from Spec

- No design spec existed under `~/.mdx/design/` for this phosphene aurora slice, so the mailbox directive was treated as the source design contract.
- Wallpaper mode increases only the route specific scale to make the aurora fill the viewport edge to edge.

## Open Items

- The Three.js Aurora port remains intentionally out of scope for this slice.
- Further visual tuning can happen after Stuart screenshots `?wallpaper` and reacts.
