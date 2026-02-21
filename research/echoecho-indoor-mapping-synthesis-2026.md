# EchoEcho Indoor Mapping Synthesis (2026)

See also:
- `indoor-mapping-platforms-2026.md`
- `indoor-mapping-standards-2026.md`
- `indoor-authoring-workflows-2026.md`
- `echoecho-indoor-mapping-recommendation-2026.md`

## Synthesis

The 2026 landscape is consistent:

- serious indoor systems are floor-aware
- navigation depends on an explicit graph
- vertical transitions are first-class
- indoor/outdoor handoff points are intentional
- publishing wayfinding is a governed workflow

For EchoEcho, indoor mapping should begin as a floor-aware navigation graph, not a floorplan-drawing exercise.

## Recommended EchoEcho v1 Indoor Model

- `building`
- `level`
- `destination`
- `indoor_node`
- `indoor_edge`
- `vertical_connector`
- `outdoor_indoor_connector`
- `landmark`
- `hazard`

## Recommended Workflow Split

- `admin/web`: author buildings, levels, destinations, hallway/path graph, stairs/elevators/ramps, connectors, and publish state
- `router/mobile`: validate routes in the field, correct path truth, add landmarks/hazards, confirm reachability
- `student`: consume published indoor-capable routes

## External References To Borrow From

- `IMDF` for practical feature taxonomy
- `IndoorGML 2.0` for topology and connectivity thinking
- `ArcGIS Indoors` for structured authoring workflow
- `Mappedin`, `MapsIndoors`, and `MazeMap` for campus-scale product framing
- `QField` and `Mergin Maps` for field validation workflow

## Most Important Product Rule

Keep these states distinct:

- structurally authored indoor graph
- walked and validated indoor route
- published student guidance
