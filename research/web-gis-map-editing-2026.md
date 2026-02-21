# Web/GIS Map Editing Stacks for Polygon Editing (2026)

Researched: 2026-03-13
Context: EchoEcho admin currently uses `@rnmapbox/maps` in React Native / Expo. This note focuses on web/GIS editing stacks we could borrow from, port patterns from, or use in a future web-based editor. It is not limited to packages that are directly drop-in compatible with React Native.

## Executive Summary

For a modern editable polygon stack in 2026, the strongest open-source foundations are:

1. `terra-draw` for architecture and cross-map editing abstractions.
2. `Mapbox GL Draw` only if we want the simplest legacy-compatible Mapbox/MapLibre web editor.
3. `Geoman` if we want the richest off-the-shelf editing UX on the web, especially for MapLibre or Leaflet.
4. `OpenLayers` if we want maximum GIS power and are willing to accept a heavier, more GIS-centric stack.

For EchoEcho specifically, the important constraint is that the current admin app is React Native using `@rnmapbox/maps`, not web Mapbox GL JS / MapLibre GL JS. That means none of the web packages below are true drop-in dependencies for the existing admin app. The practical value is:

- borrow architecture and interaction patterns
- optionally build a dedicated web or WebView editor later
- avoid inventing editing behavior from scratch

## What Is Current in 2026

### Terra Draw

- Package: `terra-draw`
- Status: actively published in 2026; npm shows `1.13.0` published 9 days before this research.
- Positioning: a cross-map drawing core with adapters for multiple renderers.
- Supported adapters called out on npm: MapLibre, Mapbox, Leaflet, Google Maps, ArcGIS.

Why it matters:

- It separates the editing engine from the map adapter.
- It has a mode-based architecture instead of hardwiring editing logic directly into one map SDK.
- It is the cleanest reference if we want to port an editor to native later.

Strengths:

- Strong architecture for reuse.
- Cross-map abstraction instead of one-off plugin behavior.
- Good match for a "geometry editor core + renderer adapter" design.
- Official MapLibre example ecosystem exists.

Weaknesses:

- Still a web-first library, not a React Native native-map solution.
- Historical reports exist of Mapbox/MapLibre adapter performance sensitivity under heavy pointer activity; this is manageable but worth testing if used directly on web.

Best use for EchoEcho:

- Primary architectural reference.
- Best candidate if a future admin polygon editor becomes web-based or WebView-based.
- Strong source for state machine design: `idle`, `draw`, `select`, `edit vertices`, `drag feature`, `delete`.

### Mapbox GL Draw

- Package family: `@mapbox/mapbox-gl-draw`
- Status: still documented by Mapbox in 2026 examples and still commonly used in MapLibre examples.
- Current evidence:
  - Mapbox docs still ship a polygon-drawing example using Mapbox GL Draw.
  - MapLibre docs still maintain an example showing Mapbox GL Draw running on MapLibre GL JS.

Why it matters:

- It remains the baseline editing library people know in the Mapbox ecosystem.
- There is a large body of examples, custom modes, and community knowledge.

Strengths:

- Battle-tested and familiar.
- Simple mental model.
- Large ecosystem of custom modes and patches.
- Useful if we want the fastest way to add simple polygon editing on the web.

Weaknesses:

- Architecturally older than newer alternatives.
- Core UX is basic unless we invest in custom modes and custom UI.
- Better for "draw/select/trash/update" than for polished production editing flows.

Best use for EchoEcho:

- Good fallback if we only need a lightweight web proof-of-concept.
- Good source of common polygon-editing conventions and custom-mode patterns.
- Not my first choice for a fresh editor in 2026 unless compatibility is the goal.

### Geoman for MapLibre / Mapbox / Leaflet

- Packages:
  - `@geoman-io/maplibre-geoman-free`
  - `@geoman-io/mapbox-geoman-free`
  - `@geoman-io/leaflet-geoman-free`
- Status: clearly active in 2026.
- Current evidence:
  - Geoman homepage and docs are current in 2026.
  - Geoman now documents MapLibre and Mapbox together.
  - npm shows `@geoman-io/maplibre-geoman-free` at `0.4.8`, published 2 months before this research.
  - Geoman homepage lists `Leaflet-Geoman v2.19.2` and `MapLibre-Geoman v0.7.0`.

Why it matters:

- Geoman is the most complete "editing UX out of the box" option in this landscape.
- It goes well beyond basic draw/edit/delete:
  - drag
  - cut
  - rotate
  - split
  - scale
  - measure
  - snap
  - pin

Strengths:

- Best turnkey editing UX among the stacks reviewed.
- Strong precision tools.
- Good documentation.
- Can use built-in toolbar or custom UI.
- Actively maintained and commercially backed.

Weaknesses:

- Some advanced functionality is in Pro tiers.
- Less attractive if the target remains React Native native maps.
- More "productized library" than low-level architecture reference.

Best use for EchoEcho:

- Best web benchmark for the editing UX we should emulate.
- Strongest choice if we ever spin up a dedicated browser-based admin editor quickly.
- Good source for interaction ideas:
  - snapping
  - vertex pinning
  - split/cut workflows
  - mode-specific toolbar patterns

### OpenLayers Editing Stack

- Core interactions:
  - `Draw`
  - `Modify`
  - `Select`
  - `Snap`
  - `Translate`
- Status: current official examples and API docs are active in 2026; examples cite OpenLayers `10.8.0`.

Why it matters:

- OpenLayers still has the deepest OSS GIS editing primitives.
- It is not just a plugin. Editing is built around explicit interactions you compose.

Strengths:

- Excellent editing primitives.
- Strong snapping model, including edges, vertices, and intersections.
- Good support for advanced topological editing concepts.
- Best source for serious GIS interaction patterns.

Weaknesses:

- Heavier and more GIS-oriented than EchoEcho needs today.
- More verbose API.
- Larger conceptual jump from the current RN Mapbox implementation.

Best use for EchoEcho:

- Reference for advanced behavior once we move beyond "redraw polygon":
  - preserve topology
  - edit multiple selected features
  - snap ordering and interaction precedence
  - trace-along-existing-geometry patterns

### Leaflet-Geoman

- Package: `@geoman-io/leaflet-geoman-free`
- Status: active in 2026; npm shows `2.18.3` published 7 months before this research.
- Why it matters:
  - still the most mature Leaflet editing package
  - battle-tested interaction design

Strengths:

- Very polished editing UX.
- Strong toolbar and mode semantics.
- Excellent source of interaction ideas even if we never use Leaflet.

Weaknesses:

- Leaflet is less aligned with the current EchoEcho stack than Mapbox / MapLibre.
- Not a good direct adoption path for the existing RN app.

Best use for EchoEcho:

- UX benchmark.
- Source of editing affordances worth copying:
  - visible vertex handles
  - snapping cues
  - mode-specific tool activation
  - explicit save/discard boundaries

### Leaflet.draw

- Package / docs: `Leaflet.draw`
- Status: still available and documented in 2026, but clearly older.

Strengths:

- Historically important.
- Simple mental model for draw/edit/delete lifecycle.

Weaknesses:

- Older than Geoman and less capable.
- Does not support multigeometries according to its own docs.

Best use for EchoEcho:

- Historical reference only.
- No reason to choose it over Geoman for new work.

## MapLibre-Specific Notes

MapLibre in 2026 clearly supports both major plugin paths:

- official examples using Mapbox GL Draw
- official examples using Terra Draw wrappers

That is a strong signal that the ecosystem has not converged on one editing stack. In practice:

- `Mapbox GL Draw` remains the compatibility path.
- `Terra Draw` is the cleaner architecture path.
- `Geoman` is the richer productized editing path.

If the question is "what should a new web editor use today?", the answer is not Mapbox GL Draw by default anymore.

## Architectural Patterns Worth Borrowing

These are more important than the package choice if EchoEcho stays in React Native:

### 1. Separate editor state from map renderer

Do not let map event handlers directly mutate campus geometry everywhere. Use:

- editor state machine
- geometry reducer or command model
- renderer adapter

The adapter should only translate:

- tap / pointer events
- hit testing
- drag updates
- viewport conversions

Everything else should live in the editor core.

### 2. Explicit modes

Use explicit modes instead of boolean flags scattered through components:

- `idle`
- `draw`
- `select`
- `edit_vertices`
- `drag_feature`
- `delete`
- `review`

This is the cleanest way to grow from "recreate polygon" to real editing later.

### 3. GeoJSON-like in-memory model

Keep an in-memory feature model shaped like GeoJSON or close to it, even if the DB stores PostGIS geometry. Serialize only at save boundaries.

This makes it easier to:

- port UI between web and native
- test geometry logic without the map
- reuse Turf or custom geometry helpers

### 4. Snapping is a policy, not a side effect

Treat snapping as a pluggable capability:

- off by default for POC
- optional vertex snap
- optional midpoint snap
- optional edge / intersection snap
- optional snap-to-building / snap-to-campus-edge

OpenLayers and Geoman are strong references here.

### 5. Whole-shape replace first, vertex editing second

For mobile-first editing, the right sequence is:

1. recreate polygon
2. drag whole polygon
3. edit single vertices
4. advanced split/cut/merge

Trying to jump straight to desktop-style vertex editing on mobile usually creates poor interaction quality.

### 6. Make save/discard explicit

Editing sessions should have their own draft geometry and explicit save/discard semantics. Avoid live-mutating persisted features as the user drags.

## What Fits EchoEcho Specifically

Current EchoEcho admin map stack:

- React Native
- Expo
- `@rnmapbox/maps`
- custom drawing flows already exist for buildings and campus boundaries

Implication:

- web packages are not directly portable into the existing admin app
- the short-term question is not "which package can we install?"
- the short-term question is "which editor architecture and UX should we copy?"

The best fit by time horizon:

### Short term

Keep the native Mapbox stack and implement editing with custom RN components.

Borrow from:

- Terra Draw for mode architecture
- Geoman for editing affordances and toolbar design
- OpenLayers for snapping and interaction ordering

### Medium term

Extract a reusable geometry editor core from the current building/campus flows:

- feature draft model
- undo/redo stack
- mode controller
- geometry validation helpers
- optional snapping hooks

Then use that core from:

- campus boundary editor
- building footprint editor
- hazard area editor if needed later

### Longer term

If polygon editing becomes a serious admin workload, consider a dedicated browser-based editor or a WebView-based editor built on:

- MapLibre + Terra Draw, or
- MapLibre + Geoman

That gives us richer editing faster than trying to reproduce desktop GIS ergonomics purely in React Native.

## Recommended Path

### Option A: Best fit for current app

Build a native editor in the current RN Mapbox app, but structure it like Terra Draw.

Do this:

- create a shared geometry editor state machine
- support `select`, `drag whole polygon`, `move vertex`, `insert vertex`, `delete vertex`
- keep draft geometry separate from persisted geometry
- add explicit `Save`, `Discard`, and `Recreate`

Borrow from:

- Terra Draw architecture
- Geoman UX

This is the recommendation I would pick first.

### Option B: Fastest path to rich editing if web is acceptable

Build a dedicated web editor using MapLibre + Geoman or MapLibre + Terra Draw.

Use Geoman if:

- we want rich editing fastest
- we care more about turnkey UX than framework purity

Use Terra Draw if:

- we want a cleaner, more extensible open architecture
- we are willing to build more UI around it

### Option C: Compatibility-first legacy path

Use Mapbox GL Draw in a web editor only if:

- we want the smallest conceptual jump
- we need compatibility with existing Mapbox Draw patterns or custom modes

Otherwise, I would not start a new editor on Mapbox GL Draw in 2026.

## Bottom-Line Recommendation

1. For EchoEcho's existing admin app, do not chase a direct package port from web GIS libraries into React Native.
2. Use Terra Draw as the main architectural reference.
3. Use Geoman as the main UX reference.
4. Add editing in stages: whole-shape drag and vertex editing before advanced GIS operations.
5. If editing becomes central and frequent, build a dedicated web editor on MapLibre + Terra Draw or MapLibre + Geoman instead of overloading the mobile-native admin map.

## Sources

- Mapbox GL JS example: Draw a polygon and calculate its area  
  https://docs.mapbox.com/mapbox-gl-js/example/mapbox-gl-draw/

- MapLibre GL JS example: Draw polygon with mapbox-gl-draw  
  https://maplibre.org/maplibre-gl-js/docs/examples/draw-polygon-with-mapbox-gl-draw/

- MapLibre GL JS example: Draw geometries with terra-draw  
  https://maplibre.org/maplibre-gl-js/docs/examples/maplibre-gl-terradraw/

- Terra Draw npm package  
  https://www.npmjs.com/package/terra-draw

- Geoman docs for MapLibre and Mapbox  
  https://geoman.io/docs/maplibre

- Geoman homepage / package status  
  https://geoman.io/

- MapLibre-Geoman npm package  
  https://www.npmjs.com/package/@geoman-io/maplibre-geoman-free

- Leaflet-Geoman npm package  
  https://www.npmjs.com/package/@geoman-io/leaflet-geoman-free

- OpenLayers modify features example  
  https://openlayers.org/en/latest/examples/modify-features.html

- OpenLayers snap interaction example  
  https://openlayers.org/en/latest/examples/snap

- OpenLayers draw, modify, trace and snap example  
  https://openlayers.org/en/latest/examples/draw-modify-trace-snap.html

- Leaflet.draw docs  
  https://leaflet.github.io/Leaflet.draw/docs/leaflet-draw-latest.html
