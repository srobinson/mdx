# Map Editing Products And Open-Source Stacks Relevant To EchoEcho (2026)

Date: March 13, 2026

Scope:
- Products and open-source projects with workflows relevant to campus, building, and route authoring
- Emphasis on out-of-the-box polygon editing UX, route/annotation editing, and mobile-admin/accessibility patterns
- Framed for EchoEcho's current stack: Expo/React Native admin app using `@rnmapbox/maps`

## Executive Summary

There is no single out-of-the-box React Native package in 2026 that gives EchoEcho "ArcGIS-grade" polygon, path, annotation, and topology editing directly inside `@rnmapbox/maps`. The mature options cluster in two groups:

1. Web GIS editing toolkits and products
2. Mobile field-mapping products with strong UX patterns but their own full platform assumptions

For EchoEcho, the best practical direction is:

- Keep simple geometry authoring inside the RN admin app
- Borrow interaction patterns from QField, Mergin Maps, Every Door, and Field Maps
- If advanced editing is needed later, add a web-based editor using MapLibre + Geoman or OpenLayers rather than trying to force full topology editing into RN first

## Best Fits For EchoEcho

### 1. Geoman for MapLibre / Mapbox

What it is:
- A dedicated geometry editing toolkit for MapLibre and Mapbox

Why it matters:
- Strongest out-of-the-box editing feature set found in current web-focused tooling
- Official docs now cover `MapLibre-Geoman` directly, not just Leaflet

Capabilities called out in current docs:
- Draw, edit, drag, cut, rotate, split, scale, measure, snap, and pin layers
- Supports markers, polylines, polygons, circles, rectangles, GeoJSON, and multipolygons

Relevant sources:
- Geoman docs say it is "a plugin for creating and editing geometry layers in MapLibre and Mapbox" and lists draw/edit/drag/cut/rotate/split/scale/measure/snap/pin: https://geoman.io/docs/maplibre
- Geoman product page highlights "Edit vertices, drag shapes, rotate, scale, cut, split, and merge" and "snapping and vertex pinning": https://geoman.io/

Assessment:
- Best candidate if EchoEcho adds a desktop or tablet web editor
- Strongest "borrow rather than build" option for advanced polygon UX
- Not a direct RN drop-in for the current admin app

Risk:
- Some advanced capabilities are in Pro tiers rather than the free version

### 2. Terra Draw

What it is:
- Open-source geometry drawing/editing library with adapters for multiple map libraries

Why it matters:
- Cleaner open-source base than older Mapbox-only draw tooling
- Better architectural fit if EchoEcho wants custom authoring UX without paying for a product layer

Capabilities called out in current docs:
- Supports Leaflet, MapLibre, and OpenLayers
- Provides point, line, polygon, rectangle, circle, and select/edit modes
- Current type definitions show select-mode support for snapping, draggable coordinates, resizable geometry, midpoints, delete, rotate, and scale behaviors

Relevant sources:
- OSGeo project page: https://www.osgeo.org/projects/terra-draw/
- Current select-mode type surface indexed from npm/unpkg: https://app.unpkg.com/terra-draw%401.24.2/files/dist/modes/select/select.mode.d.ts
- Current tutorials site updated January 31, 2026: https://workshops.terradraw.water-gis.com/

Assessment:
- Best open-source base if EchoEcho wants to own the UX and data model
- Better long-term fit than `mapbox-gl-draw` for a MapLibre-oriented editor
- Still primarily web-focused, not RN-native

### 3. OpenLayers Editing Stack

What it is:
- Mature web GIS framework with first-party draw/modify/snap interactions

Why it matters:
- Still the most serious open-source choice when topology and editing correctness matter more than visual polish
- Strong if EchoEcho later wants a back-office map authoring console

Capabilities called out in current docs:
- First-party `Draw`, `Modify`, `Select`, and `Snap` interactions
- Snapping to edges, vertices, and intersections
- Touch-sensitive defaults such as click tolerance and drag delays

Relevant sources:
- Draw API: https://openlayers.org/en/latest/apidoc/module-ol_interaction_Draw-Draw.html
- Snap example: https://openlayers.org/en/latest/examples/snap

Assessment:
- Best if EchoEcho later needs serious editing semantics and can tolerate a more GIS-like implementation
- Weaker choice if the goal is a branded, mobile-admin-friendly UX inside the existing RN app

### 4. ArcGIS Field Maps + ArcGIS Indoors

What it is:
- Full commercial field authoring and indoor/campus routing stack

Why it matters:
- This is the benchmark product family for mobile geometry capture plus enterprise indoor routing workflows
- Useful less as a package to embed and more as a workflow model to imitate

Relevant current capabilities:
- Field Maps supports editing tasks and map features in the mobile app, including snapping and vertex averaging for lines/polygons
- ArcGIS JS 5.0 release notes in February 2026 call out active switching between line/freehand/curve tools during drawing, integrated into Sketch and Editor UIs
- ArcGIS Indoors requires explicit pathway and transition authoring for routable networks, including manual outdoor path connections between facilities

Relevant sources:
- Field Maps configuration docs: https://doc.arcgis.com/en/field-maps/android/use-maps/configure-field-maps.htm
- Field Maps map-prep docs: https://doc.arcgis.com/en/field-maps/11.0/prepare-maps/configure-the-map.htm
- ArcGIS JS 5.0 release notes: https://developers.arcgis.com/javascript/latest/release-notes/
- ArcGIS Indoors network authoring: https://pro.arcgis.com/en/pro-app/latest/help/data/indoors/create-the-indoors-network.htm

Assessment:
- Not a realistic embedded stack for EchoEcho
- Very valuable as the reference workflow for route graph authoring

Key lesson:
- Treat route authoring as a network/pathway editing problem, not "draw a pretty line on a map"

### 5. Mergin Maps

What it is:
- Mobile field-mapping product built around QGIS workflows

Why it matters:
- One of the best current examples of mobile-first geometry editing UX that is practical, not flashy

Relevant current capabilities:
- Add, edit, and delete features in the field
- Local-first changes that sync later
- Line/polygon capture via manual vertices or streaming mode
- Geometry editing includes vertex editing, redraw, and split
- Touch feedback, GPS recentering, reusable values, and auto-sync patterns

Relevant sources:
- Mobile feature editing docs: https://merginmaps.com/docs/field/mobile-features/

Assessment:
- Very strong pattern library for EchoEcho mobile-admin UX
- Not something to embed directly into the existing RN app, but excellent to copy interaction decisions from

Patterns worth borrowing:
- Separate "capture geometry" from "fill attributes"
- Support redraw as a first-class action, not only fine-grained vertex surgery
- Allow local unsynced edits and explicit save/submit state

### 6. QField

What it is:
- Mobile QGIS field app with serious geometry editing

Why it matters:
- Strongest evidence that mobile polygon editing can go beyond simple create/recreate flows if the UX is disciplined

Relevant current capabilities:
- Digitize, edit, and delete points, lines, and polygons
- Vertex editor for move/delete/add vertex
- Reshape tool for line/polygon edits
- Freehand digitizing
- Topological editing when configured upstream
- Crosshair-centered geometry capture workflow

Relevant sources:
- QField digitize/edit docs: https://docs.qfield.org/how-to/data-collection/digitize/

Assessment:
- Best source of patterns if EchoEcho later adds vertex editing and reshape tools
- Also a warning: the deeper the editing surface gets, the more state management and topology rules matter

Patterns worth borrowing:
- Crosshair-at-center capture mode for high-precision mobile editing
- Explicit mode switching: browse vs digitize
- Tool-specific editing states rather than one overloaded gesture system

### 7. Mappedin CMS / Mappedin Advanced

What it is:
- Commercial indoor/campus map CMS and wayfinding platform

Why it matters:
- Directly relevant to multi-building campus mapping and route/path management
- Strong signal for where the indoor mapping market moved in 2025-2026

Relevant current capabilities:
- CMS for editing venue maps and location information
- Multi-building venue management
- Draft/publish workflow
- June 10, 2025 announcement introduced self-service multi-building mapping, seamless navigation, venue-wide map editing, and path management

Relevant sources:
- CMS page: https://www.mappedin.com/map-cms/
- Multi-building/path-management announcement: https://www.mappedin.com/resources/news/mappedin-launches-multi-building-venue-mapping/
- Routing SDK docs: https://developer.mappedin.com/web-sdk/wayfinding

Assessment:
- Strong competitive benchmark for product direction
- Not likely the implementation base for EchoEcho, but useful to benchmark features and workflow language

Key lesson:
- Building polygons and routing paths should be authored as separate layers with separate tools

### 8. Every Door

What it is:
- Lightweight OpenStreetMap mobile editor focused on POIs and entrances

Why it matters:
- Very relevant reference for highly constrained, fast mobile editing of entrances/POIs

Relevant current capabilities:
- Create and edit nodes and polygons
- Focused modes for different edit tasks
- Left-hand compatible
- iOS and Android

Relevant sources:
- OSM wiki page: https://wiki.openstreetmap.org/wiki/Every_Door
- Product page: https://every-door.app/

Assessment:
- Best model for future EchoEcho entrance/POI authoring
- Not enough for campus route graph editing, but excellent for constrained task-specific editing

Key lesson:
- Specialized edit modes beat "one generic editor for everything" on mobile

## Projects To Be Careful About

### Mapbox GL Draw

Why it is tempting:
- Familiar
- Still widely referenced
- Latest GitHub release is listed as `v1.5.1` on November 3, 2025

Why I would not choose it as the strategic base:
- It is still Mapbox-first
- Historical compatibility issues exist in MapLibre usage; for example, MapLibre issue `#2601` documents it breaking on MapLibre v3
- Geoman and Terra Draw are now cleaner options for new work

Relevant sources:
- GitHub repo/release page: https://github.com/mapbox/mapbox-gl-draw
- MapLibre compatibility issue: https://github.com/maplibre/maplibre-gl-js/issues/2601

Assessment:
- Acceptable only for a quick web prototype if the team already knows it
- Not the best 2026 foundation for EchoEcho

## What These Products Suggest For EchoEcho

### Strong recurring pattern 1: Geometry editing and metadata entry are separate steps

Seen in:
- Mergin Maps
- Field Maps
- QField

Recommendation:
- Keep geometry authoring in a dedicated mode with clear save/reset/cancel controls
- Do not combine geometry editing and complex forms on one overloaded screen

### Strong recurring pattern 2: Mobile editing works best with constrained tools

Seen in:
- Every Door
- QField
- Mergin Maps

Recommendation:
- For mobile admin, prefer specialized flows:
  - recreate campus boundary
  - edit building polygon
  - place entrance
  - add route waypoint/path segment
- Avoid a single omnipotent "edit everything" mode

### Strong recurring pattern 3: Route authoring is a network problem, not just a polyline problem

Seen in:
- ArcGIS Indoors
- Mappedin path management

Recommendation:
- Keep campus/building footprints as polygons
- Keep navigation graph/pathways as a distinct dataset with transitions, constraints, and travel modes
- Do not collapse route authoring into freehand line drawing

### Strong recurring pattern 4: Mobile-first precision benefits from crosshair or guided placement

Seen in:
- QField
- Mergin Maps
- Field Maps

Recommendation:
- Consider a future "crosshair edit mode" for entrances, hazards, and fine-grained waypoint placement
- That is likely more reliable on mobile than free dragging individual vertices

### Strong recurring pattern 5: Redraw is more valuable than full arbitrary editing early on

Seen in:
- Mergin Maps
- QField

Recommendation:
- EchoEcho's current "recreate boundary" approach is directionally correct
- For the next step, add:
  - vertex edit for polygons
  - split/reshape for buildings later
  - route segment add/delete before full topology editing

## Recommended Direction For EchoEcho

### Recommendation A: Near-term

Stay inside the RN admin app and add constrained editing tools:
- Polygon vertex editing for campuses/buildings
- Entrance and POI placement with crosshair-centered placement
- Route-path authoring as explicit segment creation between nodes

Borrow most heavily from:
- QField
- Mergin Maps
- Every Door

### Recommendation B: Mid-term

If advanced editing becomes important, build a separate web authoring console instead of forcing all complexity into RN.

Preferred stack:
- MapLibre + Geoman if you want fastest feature delivery
- MapLibre/OpenLayers + Terra Draw if you want more ownership and open-source control

### Recommendation C: Data model

Keep these layers separate:
- Campus footprints
- Building footprints
- Entrances / POIs / hazards
- Route graph / pathways / transitions

This matches how the serious products handle authoring.

## Concrete Recommendation List

1. Do not look for a single RN package that solves full campus/building/route editing out of the box. That market is effectively web-first or product-platform-first.
2. For EchoEcho mobile admin, borrow UX patterns from QField, Mergin Maps, and Every Door rather than trying to copy ArcGIS's full surface area.
3. If you need advanced polygon editing soon, Geoman is the strongest 2026 web toolkit to borrow from.
4. If you need open-source control and a cleaner long-term editor base, Terra Draw is the best starting point.
5. Treat route authoring as explicit pathway/network editing, following ArcGIS Indoors and Mappedin patterns, not arbitrary line drawing.
6. Keep "recreate/redraw" as a first-class recovery workflow even after adding vertex editing.
7. Consider a later desktop/tablet web editor for heavy map editing; keep RN for field-friendly lightweight edits.

## Sources

- Geoman MapLibre docs: https://geoman.io/docs/maplibre
- Geoman overview/product page: https://geoman.io/
- Terra Draw (OSGeo): https://www.osgeo.org/projects/terra-draw/
- Terra Draw workshops/tutorials: https://workshops.terradraw.water-gis.com/
- OpenLayers Draw API: https://openlayers.org/en/latest/apidoc/module-ol_interaction_Draw-Draw.html
- OpenLayers Snap example: https://openlayers.org/en/latest/examples/snap
- ArcGIS Field Maps configure app: https://doc.arcgis.com/en/field-maps/android/use-maps/configure-field-maps.htm
- ArcGIS Field Maps configure map: https://doc.arcgis.com/en/field-maps/11.0/prepare-maps/configure-the-map.htm
- ArcGIS JS release notes: https://developers.arcgis.com/javascript/latest/release-notes/
- ArcGIS Indoors network creation: https://pro.arcgis.com/en/pro-app/latest/help/data/indoors/create-the-indoors-network.htm
- Mergin Maps mobile feature editing: https://merginmaps.com/docs/field/mobile-features/
- QField digitize/edit docs: https://docs.qfield.org/how-to/data-collection/digitize/
- Mappedin CMS: https://www.mappedin.com/map-cms/
- Mappedin multi-building and path management announcement (June 10, 2025): https://www.mappedin.com/resources/news/mappedin-launches-multi-building-venue-mapping/
- Mappedin wayfinding docs: https://developer.mappedin.com/web-sdk/wayfinding
- Every Door product page: https://every-door.app/
- Every Door OSM wiki page: https://wiki.openstreetmap.org/wiki/Every_Door
- Mapbox GL Draw repo: https://github.com/mapbox/mapbox-gl-draw
- MapLibre issue about Mapbox Draw compatibility: https://github.com/maplibre/maplibre-gl-js/issues/2601
