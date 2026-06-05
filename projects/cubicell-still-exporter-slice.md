---
title: Slice scope — offscreen still exporter at arbitrary dimensions
type: projects
tags:
  - cubicell
  - export
  - renderer
  - slice
  - scope
summary: First slice toward deterministic export. Renders a PNG offscreen at author-chosen dimensions from the live camera pose, independent of viewport size and device pixel ratio. No MediaRecorder, no codec, no ExportJob.
status: proposed
project: cubicell
confidence: high
created: 2026-08-22
updated: 2026-08-22
---

# Slice: offscreen still exporter at arbitrary dimensions

Scoped against `main` at `bd43225`.

## Goal

One still export path that renders offscreen at author-chosen pixel dimensions
from the live camera pose and hands the user a lossless PNG. Output dimensions
are independent of viewport size, CSS size, and device pixel ratio.

This is the smallest slice that produces a final-quality artifact, and it is a
down payment on `PROJECT.EXPORT.md` rather than throwaway scaffolding. The same
path later renders frames for a PNG sequence.

## Reuse map

Everything below already exists and is the intended foundation. This slice adds
no parallel implementation.

- `src/thumbnail/thumbnailRenderer.ts · createOrthographicThumbnailRenderer` —
  already takes `options.size` and validates any positive integer width and
  height. 256 is a default, not a limit. Owns a serialized render queue, one
  bounded WebGL context, `setPixelRatio(1)`, and PNG encode.
- `src/thumbnail/thumbnailView.ts · ThumbnailView` — already has the
  `{ kind: "camera"; pose: CameraPoseSnapshot }` variant, so rendering from the
  live camera pose is supported today. No new view concept is needed.
- `src/thumbnail/thumbnailArtifact.ts · createThumbnailArtifact` — builds the
  full scene artifact without mounting the editor canvas, reusing the same
  layer, material, instance, polarity, and atlas owners as the live render.
- `src/scene/stencilAtlas.ts · createStencilAtlas, collectReferencedContents` —
  content residency before render, so faces are not baked as base.
- `src/scene/cubeInstances.ts · createCubeSceneInstances` — one instance
  derivation feeding both atlas sync and the artifact.
- `src/interaction/commands/registry.ts · capture port` and
  `src/studios/editor/useRecordingCapability.ts · canToggle, toggle` — the
  existing shape a still export command follows.

`src/control/canvasStillCapture.ts · captureCanvasPng` is the development-only
live-canvas path. It is superseded by this slice and should be removed in it,
not left as a second way to get a PNG.

## What is actually missing

1. **Perspective projection.** `createOrthographicThumbnailView` and
   `createThumbnailCamera` build an `OrthographicCamera` only, while the scene
   carries `ProjectionMode` and `P` swaps it. A still of a perspective scene
   would silently render orthographic. This is the largest item in the slice.

2. **Alpha.** `createWebGlRenderer` sets `alpha: false`, and `renderThumbnail`
   always assigns `scene.background` from `scenePolarities[pose.polarity]`. A
   transparent PNG needs both made conditional on a background policy.

3. **A dimension ceiling.** `validateThumbnailSize` checks positive integers and
   nothing else. Above the driver's `MAX_RENDERBUFFER_SIZE` or `MAX_TEXTURE_SIZE`
   the render fails or returns black. The exporter must query the limit and
   refuse with a clear reason rather than writing a black 8K PNG.

4. **A still export port and command**, registered beside the existing capture
   port, so keyboard, panels, and MCP reach it through one registry.

5. **File delivery**, matching however the WebM download already hands the user
   a file.

## Placement decision

Once stills use it, the module is no longer about thumbnails. The reusable core
belongs outside `src/thumbnail/`, with thumbnails and stills as two callers of
one path. Renaming it during this slice keeps a single offscreen render owner;
leaving it named `thumbnail*` invites a second implementation the first time
someone reads the directory and concludes stills need their own.

## Out of scope

Shutter UI, viewfinder, aspect policy, N-pass recording, PNG sequence,
WebCodecs, muxers, and `ExportJob`. `R` and `Shift+R` keep working unchanged as
Quick Capture throughout.

## Gate

- The six repo scripts. Only `pnpm build` typechecks.
- A test that the same pose renders at 256 and at 1920 with framing equivalent
  modulo scale.
- A test that output dimensions are unchanged by window size and by device
  pixel ratio.
- A test that a perspective scene renders through a perspective camera.
- Live proof on dev: export a 4K still and inspect it, per the standing rule
  that a decision can pass review and a green gate yet be unreachable in the UI.

## Risks

- The renderer's serialized queue is sized for many small thumbnails. A 4K
  render on the shared instance would stall thumbnail generation, so the
  exporter should take its own renderer instance from the same factory.
- `preserveDrawingBuffer: true` at 4K and above carries real memory cost.
- `antialias: true` has sample-count limits that vary by driver at high
  resolution, so antialiasing quality may not hold at every size.

## Decided: live camera pose exactly

A still photographs the live camera pose, with no fit mode of its own. Fitting
is already a camera command, so the user frames with `5` and then shoots. The
`{ kind: "camera"; pose }` view variant supports this today.

Verified: `5` and `numpad5` both bind `editorCommandIds.viewReset`. The exported
constant `resetViewCommand` carries `target: null`, but
`src/interaction/commands/view.commands.ts · resolve` intercepts every reset,
calls `core.computeGridFrame(core.framing(), core.viewportSize,
core.initialCamera)`, and rewrites the command to carry the resolved target. The
reducer therefore always takes the `restoreViewPose` branch, so `5` is Frame All
against the staged scene as a complete pose including distance.

### Consequence: the fit is viewport aspect dependent

`computeGridFrame` fits against `core.viewportSize`. "Press `5`, then export" is
correct only while the export aspect matches the editor viewport. Exporting a
9:16 still from a wide editor window fits the subject to the wrong rectangle.

This is not an argument for giving the exporter a fit mode. It is the argument
that the viewfinder is load bearing: once the canvas is letterboxed to the
export aspect, `5` should fit to the viewfinder rectangle rather than the
viewport. The still exporter and the viewfinder are therefore coupled, and the
still slice should not ship a dimension picker whose aspect can diverge from the
viewport until the viewfinder lands, or it ships a framing bug.

Narrowest safe scope for this slice: export at the viewport aspect, with
resolution as the only free variable. Arbitrary aspect waits for the viewfinder.
