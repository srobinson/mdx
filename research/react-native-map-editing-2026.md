# React Native Map Editing Landscape for EchoEcho (2026)

Updated: 2026-03-13

## Scope

Research track 1: current React Native map editing packages/components relevant to EchoEcho's stack:

- Expo `~52.0.49`
- React Native `0.76.9`
- `@rnmapbox/maps` `^10.2.10`

Focus:

- polygon/polyline/marker editing
- vertex drag
- drawing
- snapping
- GeoJSON editing
- maintenance status
- license
- package activity
- whether the option is Mapbox-native, MapLibre-native, or bridgeable from web

## Repo-specific context

EchoEcho already has custom native drawing logic in the admin app on top of `@rnmapbox/maps` for:

- campus boundary creation
- building drawing
- map camera fitting

That matters because the "buy vs build" decision is not starting from zero. The question is whether there is a serious package that can replace or substantially accelerate native editing, especially polygon re-editing and route/path editing.

## Bottom line

There is still no clearly maintained, widely adopted React Native package in 2026 that gives full out-of-the-box geometry editing on top of `@rnmapbox/maps` with:

- vertex drag
- midpoint insertion
- snapping
- select/move/scale/rotate
- robust GeoJSON editing

The strongest options split into two buckets:

1. Native-first: stay on `@rnmapbox/maps` and build editing handles yourselves.
2. Bridgeable web editor: embed a web map editor in a `WebView` for advanced editing workflows.

The best bridgeable editors are `Geoman` and `Terra Draw`.

## Short recommendation

1. Keep the shipping mobile maps native with `@rnmapbox/maps`.
2. Build a focused native editor for the EchoEcho needs you actually have now:
   - polygon vertex drag
   - midpoint insertion
   - delete vertex
   - polyline/path editing
   - optional snapping
3. If you want full-featured editing fast, use a dedicated editor screen with a web editor inside `WebView`.
4. If you do that, `@geoman-io/maplibre-geoman-free` is the strongest "rich editing out of the box" option, and `terra-draw` is the strongest "clean architecture / extensible modes" option.

## Candidate summary

| Option | Native vs bridgeable | Fit for EchoEcho | Editing capability | Activity snapshot | License | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| `@rnmapbox/maps` | Native, Mapbox-native | Excellent current fit | Primitives only; draggable point handles, GeoJSON render, camera bounds | npm `10.2.10`, modified `2026-03-01`; GitHub pushed `2026-03-01` | MIT | Best base for a native custom editor |
| `@maplibre/maplibre-react-native` | Native, MapLibre-native | Medium; migration path, not immediate replacement | Same story as rnmapbox: primitives, not a turnkey editor | npm `10.4.2`, modified `2026-03-11`; GitHub pushed `2026-03-12` | MIT | Good strategic fallback, not a map editor solution |
| `@geoman-io/maplibre-geoman-free` | Web, MapLibre-native | High if using `WebView` editor | Rich draw/edit/drag/cut/rotate/split/scale/measure/snap/pin | npm `0.7.1`, modified `2026-03-06`; GitHub pushed `2026-03-11` | MIT free, commercial Pro tier | Best bridgeable full editor |
| `@geoman-io/mapbox-geoman-free` | Web, Mapbox-native | High if using `WebView` editor and staying Mapbox | Same capabilities as above | npm `0.7.1`, modified `2026-03-06`; package created `2026-02-26` | MIT free, commercial Pro tier | Strong if you want Mapbox web editor parity |
| `terra-draw` + adapters | Web, MapLibre or Mapbox | High if using `WebView` editor | Strong draw/select/edit model, snapping, validation, extensibility | npm `1.25.0`, modified `2026-02-18`; GitHub pushed `2026-03-09` | MIT | Best bridgeable extensible editor |
| `@mapbox/mapbox-gl-draw` | Web, Mapbox-native | Medium | Solid baseline draw/edit/select, large custom-mode ecosystem | npm `1.5.1`, modified `2025-11-03`; GitHub pushed `2026-03-09` | ISC | Stable but less feature-rich than Geoman |
| `maplibre-gl-draw` | Web, MapLibre-native | Low | Basic draw fork of mapbox-gl-draw | npm `1.6.9`, modified `2023-07-21`; GitHub pushed `2025-03-04`, only `11` stars | ISC | Low confidence |
| `@nebula.gl/layers` | Web, deck.gl overlay | Low for this repo | Powerful editable GeoJSON on web | npm `1.0.4`, modified `2023-04-10`; repo last pushed `2024-05-28` | MIT package, repo license metadata unclear | Not a good fit here |
| `react-mapbox-gl-draw` | Web React wrapper | Low | Wrapper around mapbox-gl-draw | npm stale; modified `2022-05-14` | MIT | Not recommended |

## Detailed notes

### 1. `@rnmapbox/maps`

Current repo fit: highest.

What it gives you:

- native map rendering
- `PointAnnotation` with `draggable`
- `ShapeSource` for GeoJSON-backed geometry rendering
- `Camera` bounds fitting
- tap/press events and layer composition

What it does not give you:

- polygon editor
- polyline editor
- midpoint handles
- snapping
- undo/redo editing model
- feature selection model

Implication:

`@rnmapbox/maps` is a very good map engine, not a geometry editor. For EchoEcho, it is still the best native foundation because your current campus/building flows already use it and the app is already integrated with Expo dev clients for Mapbox native.

Best use:

- keep it for production map rendering
- implement editing handles with draggable `PointAnnotation` or `MarkerView`
- store the editable geometry in GeoJSON
- use Turf plus custom logic for snapping and midpoint insertion

### 2. `@maplibre/maplibre-react-native`

Current repo fit: strategic, not immediate.

Pros:

- actively maintained in 2026
- MIT
- fork lineage from rnmapbox
- Camera docs still support bounds-driven fitting

Important caveat from the project README:

- v10 new-architecture support is still via the interoperability layer
- the maintainers point users at the v11 beta branch for better new-architecture support

Implication:

This is a viable future migration path if you want to reduce Mapbox dependency or move toward MapLibre. It does not solve editing by itself. It is still a primitives-first map wrapper.

### 3. `@geoman-io/maplibre-geoman-free`

Current repo fit: strongest web-editor candidate.

What stands out:

- specifically targets MapLibre
- actively maintained
- MIT for free version
- official README explicitly lists:
  - draw
  - edit
  - drag
  - cut
  - rotate
  - split
  - scale
  - measure
  - snap
  - pin
- supports:
  - markers
  - polylines
  - polygons
  - circles
  - rectangles
  - GeoJSON
  - multilines
  - multipolygons

This is the closest thing I found to "serious editing product, already built."

Tradeoff:

It is web-first, not React Native-native. The practical way to use it in EchoEcho would be a dedicated editing screen hosted in `WebView`, with GeoJSON exchanged across the bridge.

### 4. `@geoman-io/mapbox-geoman-free`

Current repo fit: strong if you want a web editor but want to stay Mapbox-aligned.

Observations:

- very new npm package in 2026
- same Geoman family and same repo lineage
- Mapbox-specific packaging now exists rather than only MapLibre packaging

This is relevant because EchoEcho already uses Mapbox native on mobile. If the long-term plan is "native maps for day-to-day use, web editor for advanced edits," then the Mapbox Geoman package is a credible bridge option.

### 5. `terra-draw`

Current repo fit: strongest extensible editor architecture.

What it gives you:

- adapters for MapLibre GL JS and Mapbox GL JS
- drawing modes:
  - point
  - polygon
  - linestring
  - freehand
  - rectangle
  - circle
  - sector
  - sensor
- select mode with feature manipulation flags
- midpoint and coordinate editing
- snapping support
- validation hooks
- render mode for contextual geometry

Important details from the docs:

- selection mode can enable draggable features
- coordinate editing can be draggable and deletable
- midpoints can be draggable
- snapping can target coordinates, lines, or custom sources
- touch support exists but some modes are weaker on small touch devices

Strongest fit:

- if you want a bridgeable editor with a cleaner programmable API than Mapbox Draw
- if route snapping becomes important, `terra-draw-route-snap-mode` exists and is active in 2026

Tradeoff:

Still web-only. No React Native adapter exists.

### 6. `@mapbox/mapbox-gl-draw`

Current repo fit: still relevant, but no longer the strongest option.

Strengths:

- stable baseline for map drawing on Mapbox GL JS
- official support for drawing and editing features
- `simple_select` and `direct_select`
- custom mode system
- ecosystem add-ons exist for:
  - freehand drawing
  - geodesic drawing
  - circles
  - rectangles

Weaknesses for EchoEcho:

- web-only
- core capability is narrower than Geoman
- richer behaviors often require add-on modes or custom work

It is a valid bridgeable option, just not the one I would choose first in 2026 unless you want a very small, composable editing core.

### 7. `maplibre-gl-draw`

Current repo fit: low confidence.

Reason:

- package freshness is old relative to the others
- tiny install base / GitHub footprint
- still described as a drawing component for Mapbox GL JS despite being MapLibre-branded

This feels more like a fork than a product direction.

### 8. `@nebula.gl/layers`

Current repo fit: poor.

Why:

- powerful web GeoJSON editing framework
- but it is centered on deck.gl overlays
- stale npm publishing
- heavy architectural mismatch with the current Expo + rnmapbox mobile stack

I would only consider this if EchoEcho were building a serious web GIS editor from scratch.

### 9. `react-mapbox-gl-draw`

Current repo fit: none.

Reason:

- wrapper around `mapbox-gl-draw`
- stale
- tied to older `react-mapbox-gl` ecosystem

Not worth evaluating further.

## Ecosystem extensions worth noting

These are not full recommendations on their own, but they matter if you choose a web-editor path.

### `terra-draw-route-snap-mode`

- npm `0.4.1`
- modified `2026-02-22`
- MIT
- purpose-built route-network snapping mode for Terra Draw

Potential EchoEcho use:

- route authoring that snaps to an existing walkway/path graph

### `mapbox-gl-draw-freehand-mode`

- npm `3.0.0`
- modified `2025-05-22`
- ISC
- active enough

Potential use:

- fast rough sketching

### `mapbox-gl-draw-geodesic`

- npm `2.3.1`
- repo archived as of `2025-02-20`

Potential use:

- geodesic lines/circles

Current recommendation:

- do not plan around it

## What this means for EchoEcho

### Native path

This is the most practical path for the current repo.

Build on `@rnmapbox/maps` and treat editing as a UI layer:

- render current polygon/polyline via `ShapeSource`
- render vertices as draggable handles
- render candidate midpoint handles between vertices
- on drag:
  - update local GeoJSON
  - recompute derived bounds
  - re-render source/layers
- add snapping using Turf and your own campus/building/path geometry
- keep the final saved shape in GeoJSON / PostGIS polygon

Why this fits:

- lowest integration risk
- no `WebView` editor complexity
- best touch/mobile control
- easiest to align with current campus/building authoring flows

### Bridgeable web-editor path

This is the fastest path to "lots of editing features now."

Most credible choices:

1. `@geoman-io/maplibre-geoman-free`
2. `terra-draw` with MapLibre adapter
3. `@mapbox/mapbox-gl-draw`

Recommended usage model:

- use native maps for normal in-app experience
- open a dedicated "Edit Geometry" modal/screen backed by `WebView`
- pass the current GeoJSON into the web editor
- return edited GeoJSON back to RN on save

Why this is attractive:

- editing stacks are already mature on web
- snapping and advanced transforms are available now

Why this is risky:

- mobile touch UX inside `WebView`
- style/theming mismatch
- more moving parts
- more testing burden across iOS/Android

## Recommendation list

1. Do not expect to find a maintained React Native package that replaces a custom geometry editor on `@rnmapbox/maps`. That market still is not really there in 2026.
2. For EchoEcho's current scope, keep editing native and build the missing polygon/polyline edit affordances yourselves.
3. If you need advanced editing sooner than the native work allows, prototype a `WebView`-based editor using `@geoman-io/maplibre-geoman-free`.
4. Keep `terra-draw` as the strongest alternative if custom editing rules, custom modes, or route snapping matter more than turnkey UI.
5. Do not invest in `react-mapbox-gl-draw`, `maplibre-gl-draw`, or `nebula.gl` for this repo unless the product direction shifts toward a full web GIS editor.

## Sources

Official / primary sources checked on 2026-03-13:

- `@rnmapbox/maps`
  - https://www.npmjs.com/package/@rnmapbox/maps
  - https://github.com/rnmapbox/maps
  - https://rnmapbox.github.io/docs/components/PointAnnotation

- `@maplibre/maplibre-react-native`
  - https://www.npmjs.com/package/@maplibre/maplibre-react-native
  - https://github.com/maplibre/maplibre-react-native
  - https://maplibre.org/maplibre-react-native/docs/components/general/camera/

- `terra-draw`
  - https://www.npmjs.com/package/terra-draw
  - https://github.com/JamesLMilner/terra-draw
  - https://terradraw.io/
  - https://github.com/JamesLMilner/terra-draw/blob/main/guides/1.GETTING_STARTED.md
  - https://github.com/JamesLMilner/terra-draw/blob/main/guides/4.MODES.md

- `terra-draw-route-snap-mode`
  - https://www.npmjs.com/package/terra-draw-route-snap-mode
  - https://github.com/JamesLMilner/terra-draw-route-snap-mode

- `@geoman-io/maplibre-geoman-free`
  - https://www.npmjs.com/package/@geoman-io/maplibre-geoman-free
  - https://github.com/geoman-io/maplibre-geoman
  - https://raw.githubusercontent.com/geoman-io/maplibre-geoman/master/README.md

- `@geoman-io/mapbox-geoman-free`
  - https://www.npmjs.com/package/@geoman-io/mapbox-geoman-free

- `@mapbox/mapbox-gl-draw`
  - https://www.npmjs.com/package/@mapbox/mapbox-gl-draw
  - https://github.com/mapbox/mapbox-gl-draw

- `maplibre-gl-draw`
  - https://www.npmjs.com/package/maplibre-gl-draw
  - https://github.com/birkskyum/maplibre-gl-draw

- `@nebula.gl/layers`
  - https://www.npmjs.com/package/@nebula.gl/layers
  - https://github.com/uber/nebula.gl

- `react-mapbox-gl-draw`
  - https://www.npmjs.com/package/react-mapbox-gl-draw
  - https://github.com/amaurymartiny/react-mapbox-gl-draw
