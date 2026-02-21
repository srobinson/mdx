# EchoEcho Map Editing Proposal (2026)

Date: March 13, 2026

Supporting notes:
- `react-native-map-editing-2026.md`
- `web-gis-map-editing-2026.md`
- `map-editing-products-2026.md`

## Decision

Do not try to find a drop-in React Native package for full polygon editing on `@rnmapbox/maps`.

There is no strong maintained option that cleanly solves EchoEcho's needs in 2026.

## Proposed Product / Technical Direction

### Phase 1: Native Admin Editor

Build a reusable RN geometry editor module inside the admin app.

Supported tools:
- redraw polygon
- edit vertices
- add/delete vertices
- place entrances and POIs
- author route segments intentionally, not freehand
- reset / undo / save / discard

Implementation approach:
- keep `@rnmapbox/maps`
- render editable geometry with `ShapeSource`, `FillLayer`, `LineLayer`, and point handles
- use draggable handles where supported
- centralize editor state in a mode-driven controller

Primary references:
- `terra-draw` for architecture
- `Geoman` for editing UX
- `QField` and `Mergin Maps` for mobile editing workflow

### Phase 2: Optional Web Editor

If editing grows into a power-user workflow, add a separate web editor instead of overloading RN.

Preferred stacks:
- `MapLibre + Geoman` for fastest delivery
- `MapLibre/OpenLayers + Terra Draw` for more control

## Why

- Lowest disruption to the current app
- Reuses existing map investment
- Lets EchoEcho ship practical editing sooner
- Avoids committing to the wrong web/RN package abstraction
- Leaves room for a stronger web editor later if the workflow demands it
