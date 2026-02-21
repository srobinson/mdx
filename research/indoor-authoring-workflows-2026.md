# Indoor Authoring Workflows For Building Interiors And Indoor Routes (2026)

Date: 2026-03-13

Scope:
- Practical authoring workflows for building interiors and indoor routes
- Emphasis on floors, hallway graphs, vertical connectors, rooms/destinations, and route validation
- Focus on official docs and current product guidance
- Framed for EchoEcho's likely workflow split between `router` and `admin`

## Executive Summary

The strongest 2026 pattern is not "draw a beautiful indoor map first." It is:

1. build a structured indoor dataset
2. create a navigable network
3. connect floors and entrances explicitly
4. validate routes in the field
5. publish reviewed guidance

The practical takeaway for EchoEcho:

- interiors should be authored as a routable graph, not only a visual floorplan
- building/floor structure and pathway network should be web-admin tasks
- field validation and landmark refinement should be router tasks
- "walked and validated" should remain distinct from "drafted from a map"

## What Strong 2026 Workflows Have In Common

Across ArcGIS Indoors, QGIS/QField, Mergin Maps, and OpenStreetMap indoor practice, the repeatable workflow is:

1. establish building and floor structure
2. import or trace floor geometry
3. build a path network or hallway graph
4. add vertical connectors such as stairs, elevators, ramps
5. connect destinations to the network
6. validate in the field and refine

The biggest difference between systems is where they put the complexity:

- ArcGIS Indoors pushes more structure into the data model up front
- QGIS/QField and Mergin Maps give more flexible field-edit workflows
- OpenStreetMap indoor practice is lighter-weight but less opinionated for routing correctness

## ArcGIS Indoors

### Current workflow pattern

ArcGIS Indoors documents a very structured indoor authoring workflow:

- create or import floorplan/unit/facility data
- create levels/floors explicitly
- build the indoor network as pathways and transitions
- connect facilities and outdoor paths
- validate route behavior after the network is built

The current official Indoors guidance emphasizes:

- floor-aware datasets
- explicit pathway features
- explicit transition features for stairs/elevators
- connecting indoor and outdoor networks

Relevant official references:

- Create floorplan data:
  https://pro.arcgis.com/en/pro-app/latest/help/data/indoors/create-floorplan-data.htm
- Create the Indoors network:
  https://pro.arcgis.com/en/pro-app/latest/help/data/indoors/create-the-indoors-network.htm
- Overview of Indoors geodatabases:
  https://pro.arcgis.com/en/pro-app/latest/help/data/indoors/arcgis-indoors-information-model.htm

### What to borrow

The best ideas for EchoEcho are:

- represent floors as first-class entities
- represent pathways as first-class features
- represent vertical transitions explicitly, not implicitly
- treat indoor/outdoor handoff points as intentional network connectors

### What not to copy wholesale

ArcGIS Indoors is more enterprise-heavy than EchoEcho needs right now. The full geodatabase workflow is too much for a first indoor release.

## QGIS + QField

### Current workflow pattern

QField remains one of the strongest field-edit examples in 2026. The relevant authoring pattern is:

- build or import the structural data in QGIS
- send the project to QField
- let field users digitize, edit, and validate geometry on site
- sync corrections back into the authoritative dataset

QField's current docs still emphasize:

- point/line/polygon digitizing
- vertex editing
- reshape tools
- freehand capture where needed
- explicit edit modes

Relevant official references:

- Digitize and edit data:
  https://docs.qfield.org/how-to/data-collection/digitize/

### What to borrow

The strongest QField ideas for EchoEcho are:

- field editing is a validation/refinement tool, not only an initial authoring tool
- editing modes should be explicit
- redraw/reset should be first-class
- precision workflows matter on mobile

For EchoEcho interiors, that suggests:

- admin/web creates floors and baseline hallway graph
- router/mobile validates and corrects the graph in the field

## Mergin Maps

### Current workflow pattern

Mergin Maps continues to present a practical field-mapping workflow in 2026:

- define the project and schema first
- capture or edit geometry in the field
- support offline work and later sync
- keep geometry editing and attribute editing closely linked

Current docs emphasize:

- adding, editing, and deleting features in the field
- vertex editing and redraw workflows
- offline capture and sync
- practical touch-friendly field authoring

Relevant official references:

- Mobile feature editing:
  https://merginmaps.com/docs/field/mobile-features/

### What to borrow

The strongest ideas for EchoEcho are:

- keep route or hallway validation available offline
- allow routers to refine geometry and metadata in one pass
- make redraw and reset easy, not hidden

## OpenStreetMap Indoor Practice

### Current workflow pattern

OpenStreetMap indoor mapping in 2026 is still centered on structured tagging rather than a single official indoor route-authoring product. The common pattern is:

- map building shell
- add levels
- map rooms/corridors/doors/stairs/elevators with level-aware tags
- use JOSM or other editors with indoor tagging support

Relevant official references:

- Simple Indoor Tagging:
  https://wiki.openstreetmap.org/wiki/Simple_Indoor_Tagging
- Indoor Mapping overview:
  https://wiki.openstreetmap.org/wiki/Indoor_Mapping
- JOSM IndoorHelper plugin:
  https://wiki.openstreetmap.org/wiki/JOSM/Plugins/IndoorHelper

### What to borrow

The valuable ideas for EchoEcho are:

- level awareness should be explicit
- corridors, rooms, doors, stairs, and elevators should be separate concepts
- indoor destinations are not the same thing as routable pathway geometry

### What not to borrow directly

OpenStreetMap indoor tagging is useful as a conceptual model, but it is too loose by itself for reliable assistive routing. EchoEcho needs stronger review and publication semantics.

## Best-Practice Workflow For EchoEcho

### Phase 1: Structural authoring

Done primarily by admin on the web.

Create:

- building
- floors
- key rooms/destinations
- hallway/path network
- stairs/elevators/ramps
- outdoor-to-indoor connectors

This should create a draft indoor graph.

### Phase 2: Field validation

Done primarily by router on mobile.

Validate:

- hallway graph correctness
- room labels and reachability
- usable entrances
- elevator and stair access
- landmarks and hazards
- route clarity for blind or low-vision users

This should produce a walked and validated revision.

### Phase 3: Review and publish

Done by admin.

Review:

- route quality
- network completeness
- accessibility semantics
- landmark/hazard sufficiency

Then publish the reviewed indoor-capable route set.

## Recommended Data/Authoring Shape

For EchoEcho, the authoring workflow should be graph-first, not floorplan-first.

Minimum authoring objects:

- `building`
- `level`
- `indoor_node`
- `indoor_edge`
- `vertical_connector`
- `destination`
- `landmark`
- `hazard`
- `outdoor_indoor_connector`

Suggested authoring responsibilities:

- admin/web: create and manage `building`, `level`, `destination`, `indoor_edge`, `vertical_connector`
- router/mobile: validate and refine `indoor_edge`, `landmark`, `hazard`, `destination access`

## Recommendation For EchoEcho

Do not start with detailed polygon editing of every interior room.

Start with:

1. floor structure
2. hallway/path graph
3. vertical connectors
4. important destinations
5. field validation workflow

That gets EchoEcho to useful indoor routing much faster than trying to build a full indoor cartography system.

If indoor mapping expands later, the strongest pattern is still the same:

- web for structured authoring
- mobile for validation
- publish only reviewed, field-validated indoor guidance
