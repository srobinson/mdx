---
title: 3dsvg live site UI + controls vs Cubicell
type: projects
tags: [3dsvg, cubicell, review, ui, controls, 3dsvg.design]
summary: Live drive of https://3dsvg.design mapped to packages/web, compared control-for-control against Cubicell's editor. Ranked leverage, rejections, screenshots.
status: active
project: cubicell
created: 2026-08-22
updated: 2026-08-22
confidence: high
source: https://3dsvg.design
---

# 3dsvg live site: editor UI + controls vs Cubicell

Driven on the deployed product at https://3dsvg.design (session `3dsvg-review`, 1440×900 then 390×844). Source map is `packages/web`. Comparison baseline is Cubicell Editor at `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`. No local 3dsvg fallback was needed. No `alert`/`confirm`/`prompt` in `packages/web`.

Labour split in one sentence: 3dsvg's canvas is a stage you rotate and photograph; Cubicell's canvas is a workbench you pick, place, and perform.

Drag on 3dsvg rotates the **mesh** (`SmoothControls` in `packages/engine/src/controls.tsx`) with friction `0.92` and damping `0.08`. The camera stays on Z. Cubicell orbits the **camera** around a target (`createTrackballControls`) and pans with Shift/right/Space, then mirrors into `CameraAuthority`. Same "flick with leftover spin" family, opposite object of the gesture.

## Control Inventory

| Control | Where it lives in the UI | Source (path + symbol) | How it feels | Cubicell equivalent or none |
|---|---|---|---|---|
| Draw tab | Left icon rail, default | `InputPanel.tabs` `draw` | Instant Space Invader on a purple stage. The product opens as a toy, not a blank. | None as a 16×16 bitmap. Closest: occupancy painting in `toggleCubeBuilt` / Build mode `B` |
| Pixel grid 16×16 | Left expanded panel | `PixelEditor` `handlePointerDown` | Drag paint is sticky and live. Extra pixels appear in the mesh before you lift. Grid cells have no a11y names. | `StructureSliceMap` cell click. Cubicell's grid is the model, not a sprite sheet |
| Draw / Erase / Clear | Pixel toolbar | `PixelEditor` `tool` / `clearGrid` | Icon-only, `title` only. Clear is a reset, not undo. | `cube.delete`, `selection.clear`, Build hide. No 16×16 eraser |
| Text tab | Left rail | `InputPanel.tabs` `text` / `TextInput` | Type `CUBIC`, pick Bebas Neue, the mesh rebuilds in about a second. Holes in C/U/B cut correctly. | None. Face text is `face.text` on a cube face, not extruded type |
| Font picker (10 Google Fonts) | Text panel `<select>` | `TextInput.FONTS` | Native select. Rubik Mono One default. Live. | None |
| SVG Code tab | Left rail | `InputPanel` textarea | Paste or "Load example (star)". Star extrudes cleanly. Empty tab keeps last mesh (`lastActiveSvg`). | Seeded stencils in `FaceMediaField` / `seededStencils`. No raw markup pane |
| Load example (star) | Code panel, empty only | `InputPanel` star button | One click demo. Good onboarding. | `EmptySceneStart` "CREATE GRID" |
| Upload File tab | Left rail | `InputPanel.handleFileUpload` | Dashed drop zone + Choose File. Hidden `accept=".svg"`. | `FaceMediaField` Import (SVG/PNG/JPEG/WebP/MP4/WebM) |
| Window SVG drop | Full viewport overlay | `Home` drag listeners | Overlay "Drop SVG file". Non-SVG ignored silently. Not exercised as OS drag; file input upload of a heart SVG did work. | Library import, not a window drop overlay |
| Uploaded file preview | File panel | `InputPanel` data-URL `<img>` | Inert image, then filename row with X. Heart extruded under the current texture. | Media library thumbnails |
| Expand / click-outside collapse | Left panel | `InputPanel.expanded` | Opening Settings dismisses the input you were using. Mobile collapse is **mount-only** (`innerWidth < 768` once). Resize does not collapse. | `DockablePanel` collapse, `Shift+Tab` `editor.panels.toggle`. Panels do not vanish because you clicked the other rail |
| Feedback | Top-right chat icon | `Home` / `Freedback` | Icon-only. Dialog sits in the a11y tree even when closed (`heading "What's your feedback?"`). | None |
| Download 3D | Top-right | `Home` `downloadOpen` / `DownloadDialog` | Format cards with taglines. GLB recommended, STL for print, OBJ/PLY buried. Copy is better than the mesh feature. | None for mesh. Recording is `R` / `Shift+R` via `createRecordingController` |
| Embed | Top-right code icon | `EmbedDialog` `generateProps` | Numbered steps: `npm install 3dsvg` then a live `<SVG3D>` snippet. Texture becomes a giant base64 data URL. Smoothness always emitted (editor `0.6` vs engine `0.2`). | None. Closest: MCP `cubicell_snapshot` / `cubicell_describe` |
| Settings gear | Top-right | `Home` `controlsOpen` | Opens a 18rem glass drawer. On 390px it eats the whole screen (`max-md:left-5`). Closed panel stays in the a11y tree (opacity, not unmount). | `LeftRail` / `Inspector` always-on unless `Shift+Tab` |
| Object color + 10 swatches | Settings > Object | `ControlsPanel` `COLOR_PRESETS` | Instant. Swatches have no names (clicked "yellow", got orange `#f97316`). Native color picker behind the hex row. | `cube.color` Theme/Black/White/Accent. `scene.polarity` |
| Depth | Object slider 0.5–10 | `Home.depth` | The extrusion thickness. Default 1 is already 3D enough. Slider thumb is a 16px a11y target. | `cube.dimension.*` scrubs with anchors |
| Smoothness | Object 0–1 | `Home.smoothness` default `0.6` | Bevel. Engine default is `0.2`, so embed always serializes it. | None as a mesh bevel. Edge thickness is `edge.thickness` |
| Zoom slider | Object 2–20 | `Home.zoom` | Dolly on Z. Fights scroll zoom (state vs local `targetZoom`). Reset Position writes state; wheel does not. | `view.zoom.in/out`, wheel via `createCameraWheelZoomHandler` |
| Reset Position | Object | `ControlsPanel` + `resetKey` | Zeros mesh rotation and zoom 8. Does not stop loop animation. | Keypad `5` / `view.reset` frames the structure |
| Background color + swatches | Settings > Background | `Home.bgColor` | Colors a **shadow-catching plane** at z=−3. Engine `SVG3D.background` is hardcoded `#0a0a0a`. | `scene.polarity` black/white. No arbitrary hex wash |
| Material preset (10) | Settings > Material `<select>` | `materialPresets` via `ControlsPanel` | Native select. Chrome/Gold/Glass/Holo on an orange mesh against solid purple look like muddy recolors. No HDRI, so "chrome" is a roughness number with a fancy name. | None as PBR. Face/edge color + `scene.faceLightnessRamp` |
| Material Advanced | Metalness, roughness, opacity, wireframe | `ControlsPanel` collapsible | Hidden by default. Honest PBR knobs. More useful than the preset names. | Opacity/thickness scrubs on parts |
| Texture presets (10) | Settings > Texture | `TexturePresetPicker` / `texturePresets` | Round swatches. Marble and Sunset **did** change the mesh. Stronger than the material dropdown. | `FaceMediaField` library + seeded stencils |
| Texture upload / clear | Texture | `ControlsPanel.handleTextureUpload` | `accept="image/*"`. Blob URL. One slot for the whole object. | Per-face media, import separate from assign |
| Texture Transform | Repeat X/Y, rotation, offset | `textureSettings` | Repeat Y is stored and **not passed** to `SVG3D` (engine has one `textureRepeat`). Dead control. | None at UV grain. Media is a face fill |
| Animation type (7) | Settings > Animation | `ANIMATION_OPTIONS` / `LoopAnimation` | Default **float**. Spin, wobble, swing, pulse, spinFloat, none. Cute embed loops. Combined with drag they fight: the mesh tumbles while the loop keeps spinning. | Piece transport + morph. No idle spin on the sculpture |
| Animation speed / reverse | Animation | `animateSpeed` / `animateReverse` | Reverse only for spin/wobble/swing/spinFloat. | `createTransportSetRateCommand` |
| Follow Cursor | Settings > Interaction | `Home.cursorOrbit` default **false** | On, the mesh eases toward pointer NDC (`orbitStrength` 0.15). Delightful on desktop. Nonsense on a phone (no hover). Engine default is `true`; editor starts off. | None. Trackball is explicit drag |
| Orbit strength | Interaction, if follow on | `orbitStrength` 0.01–0.5 | Fine. | Camera feel scrubs in `FeelFields` |
| Reset on Idle | Interaction | `resetOnIdle` | Off by default. Would lerp home after delay or mouseleave. | `view.reset` is a command, not a timeout |
| Idle delay | Interaction | `resetDelay` 0.5–10s default 2 | Only if idle reset on. | None |
| Key Light X/Y/Z | Settings > Lighting | `defaultLightSettings` 2,2,4 | Three sliders to aim a directional light. Spatial meaning is weak until the helper orb appears. | `LightDirectionPicker` 3×3 compass (`sceneLightDirectionBinding`) |
| Key intensity / Ambient / Shadows | Lighting | 1.2 / 0.3 / on | Immediate. Shadows make the ground plane earn its keep. | Face ramp on/off. No ambient slider |
| Light helper orb | Canvas, while Lighting "open" | `SVGTo3DCanvas` `showLightHelper` | White sphere + glow at the key light. Visible after zoom-out as a sun. **Stays on after you leave Lighting** because `lightingOpen` is not cleared when another accordion opens. | Axis/floor chrome, not a light gizmo |
| Canvas drag rotate | Full-bleed WebGL | `SmoothControls` pointer | Snappy. Sensitivity 0.01. You tumble the object, you do not walk around it. | Left-drag trackball orbit about target |
| Drag momentum | After pointer up | `velocity` `friction=0.92` | Continues the flick. With float+spin it becomes a tumble. Pinch kills velocity. | Trackball `staticMoving=false`, `dynamicDampingFactor` 0.08; `cancelTrackballMomentum` on pan |
| Scroll zoom | Wheel over canvas | `scrollZoom` hardcoded **true** | Dolly 2–20, `preventDefault`. Editor hijacks page scroll (engine default is false for embeds). Wheel does not write `Home.zoom`. | Wheel dolly via `createCameraWheelZoomHandler`, preference sensitivity |
| Pinch zoom | Two-finger | `SmoothControls` touch | Same clamp. | None first-class |
| Intro zoom | Load | `IntroAnimation` `intro="zoom"` | Ease-out from z=18. Marketing entrance. | Projection morph on `P`, not a load sting |
| Portrait auto-zoom | Implicit | `SmoothControls` `responsiveFactor` | If canvas aspect `< 1`, camera Z *= `1/aspect`. On a phone with 16:9 viewfinder the object becomes a postage stamp. | Framing via `view.reset` / focus. No silent Z push |
| Image / Video mode | Bottom camera bar | `ExportModal` `tab` | Segmented. Always on (`exportOpen` is stuck true, `onClose` is a no-op). | `R` canvas capture vs `Shift+R` studio tab. No mode pill |
| Shutter button | Center bottom | `ShutterButton` | White disc for still, red for video. Feels like a phone. **No accessible name.** | `CameraCaptureControl` Capture/Recapture on a State. `RecordingIndicator` REC |
| Aspect Auto / 1:1 / 16:9 / 9:16 | Camera bar, expand on hover/tap | `ExportModal.aspectOptions` / `ViewfinderOverlay` | Best control on the site. Letterbox tells you the take. First tap expands, second tap selects (hover is desktop). 4:3 and 3:2 exist in the switch and not in the UI. | None. Capture is the live canvas |
| Cycle 1x / 2x / 3x | Above shutter in Video | `videoCycles` / `getCycleDuration` | Record N animation loops then auto-stop. Appears because default animate is float. | Loop window on `TransportPlayhead`. Recording itself is manual stop |
| Recording pill | Bottom overlay | `ExportModal` recording state | Red pulse, elapsed, Stop. Replaces the shutter. 7s take worked. | `RecordingIndicator` remaining-bytes, `● REC` title |
| Photo Preview | Dialog after shutter | `ExportModal` image dialog | 1080p default, Background switch, Discard / Download PNG. Preview capture is 720px; download uses the resolution select. Animation pauses (`exportPreviewOpen`). | MCP `cubicell_capture`. No user still-preview dialog |
| Video Preview + trimmer | Dialog after Stop | `VideoTrimmer` | iOS filmstrip, yellow handles, 1080p / High / MP4. First MP4 convert pulls FFmpeg WASM (~30MB). Autoplay skipped below 768px. | None. WebM from `createRecordingController`, no trim UI |
| GLB / STL / OBJ / PLY | Download 3D dialog | `DownloadDialog` / `Download3DCapture` | Copy on the cards is excellent. Mesh export is the product's other job (print / Blender). | None |
| Embed copy | Embed dialog | `CodeBlock` `handleCopy` | Clipboard + `execCommand` fallback. Two steps. | MCP tools |
| GitHub star badge | Bottom-right, `hidden md:block` | `GitHubStarBadge` | 798. Hidden on the phone viewport. | None |
| Keyboard shortcuts | Nowhere | none in `packages/web` | Zero. Escape closes Radix dialogs only. | First-class: `keymap.ts` `getKeyboardShortcut`, keypad, holds |
| Undo | Nowhere | none | Every slider is a one-way trip. Clear grid is destructive. | `edit.undo` / `edit.redo` |
| Persistence | Nowhere | none | Reload is a new invader. | `cubicell.preferences` + `checkpointUserProjectState` |

## Worth Leveraging (ranked, highest value first)

| Idea | 3dsvg owner (path + symbol) | Gap it fills in cubicell | Cubicell landing site (path + symbol) | Effort |
|---|---|---|---|---|
| 1. Camera shutter as the export surface | `ExportModal` `ShutterButton` + always-on camera bar | Recording is a key (`R`) plus a `REC` readout. There is no object you aim before the take. A shutter on the canvas says "this frame is the output" without opening a menu. | `RecordingCapability` / `RecordingIndicator`; overlay next to `FloatingKeypad`, not `CameraCaptureControl` (that binds a `ViewPose` to a State, a different job) | M |
| 2. Viewfinder aspect overlay | `ViewfinderOverlay` + `aspectOptions` | A take has no 16:9 / 9:16 / 1:1 composition. You record the studio rectangle. Letterbox lets you compose the export without resizing the app. | `createRecordingController` / `recordingConfig`; crop at encode time. Overlay chrome in `EditorStudio` canvas slot | M |
| 3. Record N loops then stop | `videoCycles` + `getCycleDuration` | Manual Stop, or remaining-bytes. For a looping morph, "1 cycle" is the honest length. | `TransportPlayhead` already has a loop window. Wire `createRecordingController` to stop when the window wraps N times | S |
| 4. Still preview with background toggle before download | Photo Preview dialog in `ExportModal` | Canvas capture dumps a file. A preview that can drop the studio chrome / floor is the difference between a take and a screenshot of the IDE. | New preview in front of `cubicell_capture` / canvas still path `canvasStillCapture`. Keep Cubicell's black/white language | M |
| 5. Format cards that say when to use the file | `DownloadDialog` `FormatCard` / `PRIMARY_FORMATS` | When Cubicell grows deterministic export (`PROJECT.EXPORT.md`), burying niche formats under "Other" with a one-line "use this when" is the copy to steal. Not the GLB/STL themselves. | Future export UI beside `createRecordingController`. Do not add mesh exporters | S |
| 6. Portrait auto-zoom (the idea, not the 16:9-on-phone bug) | `SmoothControls` `responsiveFactor` | Phone framing currently depends on `view.reset` / focus. A silent "fit the lattice on a tall viewport" would help the keypad overlay. | `CameraDriver` / `view.reset` framing, preference-gated so it cannot fight authored tracks | M |
| 7. Spatial light widget | `SVGTo3DCanvas` light orb + `GlowSprite` | Lighting is a 3×3 compass (`LightDirectionPicker`), which is already better. A dimmable orb is optional sugar on the ramp, not a replacement. | Only if `scene.faceLightnessRamp` wants a scene-space handle. `SceneSection` `SceneFields` | L |

Name three worth stealing: **shutter**, **viewfinder**, **loop-length auto-stop**.

Name two not worth stealing: **PBR preset dropdown**, **16×16 pixel editor**. (More in the next two sections.)

## Cubicell Already Does This Better

- **Camera is a camera.** Cubicell `createTrackballControls` + `CameraAuthority` + keypad 45° detents. 3dsvg tumble-rotates the mesh while `LoopAnimation` also rotates it. After a flick, "CUBIC" is a pile of letters. Fine for a logo toy. Wrong for a lattice you must stay oriented in.
- **Lighting is a direction, not three floats.** `LightDirectionPicker` vs Key Light X/Y/Z. The compass matches "only cubes." XYZ sliders are a Blender leftover.
- **Inspector follows selection.** `SelectorPanel` / `CubeSection` / `FaceSection`. 3dsvg Settings is a global dump that covers the sculpture on a phone (`41-mobile-settings.png`).
- **Keyboard is the product.** `keymap.ts` covers orbit, travel, zoom, pan, focus, projection, build, pick mode, panels, undo, capture, transport. 3dsvg has none. Icon rails with empty accessible names (`Draw`/`Text`/`Code`/`File` are tooltip-only).
- **Capture binds a view to a State.** `CameraCaptureControl` `bind-view-to-state`. 3dsvg shutter photographs whatever the mesh is doing, including the leftover spin and the light orb you forgot was on.
- **Scrubs, not generic sliders.** `ScrubField` is compact and undo-aware. 3dsvg `Slider` rows are form-heavy. `PRODUCT.md` already forbids that panel language.
- **Clean canvas is a command.** `Shift+Tab` hides chrome without remounting WebGL. 3dsvg click-outside **steals the tool you were using**.
- **Media is per face, import ≠ assign.** `FaceMediaField`. 3dsvg has one texture for the whole extrusion, and Repeat Y does not even reach the engine.
- **Feel is authored.** `FeelFields` morph/move/zoom/wheel. 3dsvg Follow Cursor is a demo orbit, default off, fighting the loop animation.

## Looked At And Rejected

An empty section here would mean the site was flattered, not reviewed.

- **PBR material presets (chrome, gold, glass, holo).** Live: chrome went brown, glass stayed opaque orange, holo was a darker plastic. No environment map. Names promise a renderer Cubicell has explicitly refused (`PRODUCT.md` anti-reference: Blender lite). Keep polarity + face ramp.
- **16×16 pixel editor.** Cute Space Invader. Cubicell already is a cube grid. Importing a bitmap-to-occupancy toy would split the primitive language. If pixel art ever matters, it belongs as a **stencil import** through `FaceMediaField` / `seededStencils`, not a second grid.
- **Text-to-extrusion + 10 Google Fonts.** The live type is the 3dsvg pitch. Extruded Bebas "CUBIC" is not a cube. Face text (`face.text`) is the confinement-honest version.
- **Follow Cursor / reset-on-idle.** Demo-site gravity. It would yank pose out of `CameraAuthority` and fight `track` possession during Play. Reject for Editor. Revisit only if a VJ tempo wants a "breathe toward the pointer" overlay that **cannot** write the document pose.
- **Idle mesh loops (float/spin/wobble).** Embed candy. Cubicell's motion is the score. An idle bob on the lattice would lie about rest.
- **Glassmorphic floating panels as a look.** The **overlay-on-canvas** split is worth it (idea 1–2). The frosted card, native `<select>`, and accordion of sliders are the generic generated control panel `PRODUCT.md` tells you to avoid.
- **Mesh download (GLB/STL/OBJ/PLY).** Wrong primitive. Steal the **card copy**, not the exporters.
- **Embed `<SVG3D>` snippet.** 3dsvg is a component you paste. Cubicell is a studio. MCP snapshots already serialize. Do not grow an npm embed dialog.
- **Click-outside to collapse the active tool.** Feels slick, costs a misclick every time you reach for Settings. Cubicell's rails stay until you collapse them.
- **Native file/color pickers as the only path.** They freeze automation and feel OS-hosted. Cubicell's media import is already a staged document edit.
- **`userScalable: false` + mount-only mobile collapse.** Phone 16:9 viewfinder plus an uncollapsed pixel panel (`37-mobile-390.png`) is the site at its worst. Do not copy the mobile story.

## Screenshots

Absolute paths under `/Users/alphab/.mdx/projects/3dsvg-review-ui-shots/`.

- `01-landing-desktop.png` — Default: pixel invader, float, shutter, left rail. The whole pitch in one frame.
- `02-text-default.png` — Text tab, Rubik Mono One, "3DSVG".
- `03-text-bebas-cubic.png` — "CUBIC" in Bebas Neue. Type as the sculpture.
- `04-after-e5.png` — Settings drawer, Object open. Input panel dismissed by click-outside.
- `05-yellow-deeper.png` — Color swatch hit orange, not yellow. Swatches have no names.
- `06-material-chrome.png` — "Chrome" as muddy brown. Preset without an environment.
- `07-material-glass.png` — "Glass" still reads solid.
- `08-material-gold.png` — "Gold" as dark ochre.
- `09-material-holo.png` — "Holographic" as darker plastic.
- `10-texture-section.png` — Ten round texture swatches + Upload.
- `11-texture-marble.png` — Marble actually changes the mesh.
- `12-texture-sunset.png` — Sunset gradient; textures beat material names.
- `13-anim-spin.png` — Spin + speed + reverse. Still readable.
- `15-lighting.png` — XYZ sliders. No orb visible at default zoom.
- `16-follow-cursor.png` / `17-cursor-orbit-offset.png` — Follow Cursor on; mesh eases off-axis.
- `18-drag-rotate.png` — Flick tumble. Mesh rotation, not camera orbit.
- `20-scroll-zoom.png` — Zoomed out; leftover light orb appears as a sun (Lighting accordion already left).
- `21-aspect-expanded.png` — Auto 1:1 16:9 9:16 chips.
- `22-aspect-16-9.png` — Viewfinder letterbox. The control to steal.
- `23-shutter-capture.png` — Photo Preview, 1080p, Background, Download PNG.
- `24-video-mode.png` — Red shutter, 1x/2x/3x cycles, 16:9.
- `25-recording.png` — Recording pill 7.0s + Stop.
- `26-video-trimmer.png` — iOS filmstrip, MP4/High/1080p.
- `27-embed-dialog.png` — npm install + live props, texture as base64.
- `29-download-3d.png` / `30-download-other-formats.png` — GLB/STL cards; OBJ/PLY under Other.
- `31-svg-code-tab.png` / `32-svg-star.png` — Markup in, star out.
- `33-file-upload-tab.png` / `34-file-uploaded.png` — Heart SVG uploaded, inert preview, live mesh.
- `35-pixel-editor.png` / `36-pixel-draw.png` — Invader + two extra pixels, mesh updates live.
- `37-mobile-390.png` — Failure: 16:9 on portrait, pixel panel overlapping, object as a sliver.
- `38-mobile-9-16.png` — Rail only; viewfinder still landscape.
- `40-mobile-9-16-applied.png` — 9:16 finally fills the phone. This is the mobile story they should have defaulted.
- `41-mobile-settings.png` — Settings as a full-screen sheet. You cannot see the mesh while you light it.

## Open Questions For Stuart

1. Should Cubicell recording grow a **viewfinder** (16:9 / 9:16 / 1:1 letterbox) that crops the take, while the studio canvas stays square to the lattice?
2. Is a **shutter on the canvas** (photograph this pose) allowed next to `CameraCaptureControl` (bind this pose to a State), or does a second capture object split the camera story?
3. Follow Cursor: never in Editor, or a presentation/VJ overlay that cannot write `ViewPose`?
4. When deterministic file export lands (`PROJECT.EXPORT.md`), do you want 3dsvg's **format cards** (recommended vs niche, one-line "use when") as the copy pattern?
5. 3dsvg's whole trick is "the editor is the embed." Cubicell is going the other way (LLM drives the studio). Is there a pasteable **command/snippet** you actually want, or is MCP the only export of state?

## Method

- Live: `agent-browser --session 3dsvg-review` against https://3dsvg.design. Desktop 1440×900, then 390×844. Exercised all four inputs, ten materials, seven animations, ten textures, lighting, follow-cursor, drag+momentum, scroll zoom, shutter, 16:9/9:16, video record+trim, embed, GLB dialog. Did not click Download PNG/MP4/GLB (file save). Did not OS-drag a file (used the file input).
- Source: `packages/web` (`Home`, `InputPanel`, `ControlsPanel`, `ExportModal`, `PixelEditor`, `TextInput`, `EmbedDialog`, `DownloadDialog`, `VideoTrimmer`, `SVGTo3DCanvas`) and engine `SmoothControls` / `LoopAnimation` / `materialPresets`.
- Cubicell: `PRODUCT.md`, `INTERACTIVE.md`, `CAMERA.md`, plus the shipped Editor surface (`StudioShell`, `LeftRail`, `SelectorPanel`, `CubeKeypad`, `CameraCaptureControl`, `RecordingIndicator`, `keymap.ts`).
- Repos were not written. Both working trees stayed clean.
