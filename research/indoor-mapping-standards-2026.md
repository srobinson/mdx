# Indoor Mapping Standards and Open-Source Approaches (2026)

Researched: 2026-03-13
Scope: official/open sources for IMDF, IndoorGML/OGC, OpenStreetMap indoor tagging, OpenIndoor, and relevant open-source indoor rendering/routing approaches.

## Executive Summary

The current standards/open-source landscape splits into three different kinds of models:

1. `IMDF` is the strongest packaged feature model for deployable indoor maps.
2. `IndoorGML 2.0` is the strongest conceptual/topological model for interoperable indoor navigation networks.
3. `OpenStreetMap Simple Indoor Tagging` is the most flexible community mapping approach, with a useful open ecosystem for viewing and experimenting, but weaker standardization and tool consistency.

For EchoEcho, the best practical direction is:

- use a simple internal venue/building/level/node/edge model for product delivery
- borrow `IMDF` concepts for feature types and floor/building organization
- borrow `IndoorGML` concepts for topology, connectivity, and navigation-network semantics
- treat the OSM/OpenIndoor ecosystem as a source of authoring and rendering ideas, not the primary canonical data model

## IMDF

Official sources:
- Apple / OGC IMDF Community Standard: https://docs.ogc.org/cs/20-094/index.html
- Apple Indoor Maps Program / WWDC references: https://developer.apple.com/news/?id=8lmz909p and https://developer.apple.com/videos/play/wwdc2019/245/ (language-localized variants also indexed)

What it is:
- IMDF is an OGC Community Standard originating from Apple.
- The OGC document describes it as a generalized, comprehensive model for indoor locations, supporting orientation, navigation, and discovery.
- The OGC IMDF spec is GeoJSON-based and explicitly lists indoor feature types such as `venue`, `building`, `footprint`, `level`, `unit`, `fixture`, `section`, `opening`, `amenity`, `occupant`, `address`, and `relationship`.

What it is good at:
- concrete, mobile-friendly feature packaging
- floor-aware indoor map representation
- venue/building/level/unit organization
- interoperability for map display and feature discovery
- clear feature taxonomy that product teams can borrow directly

What it is weaker at:
- the OGC/Apple docs make clear that IMDF provides a comprehensive model to compute paths between mapped features, but the derived network is application specific
- in other words, IMDF is not itself the strongest standard for reusable indoor routing topology

Why it matters for EchoEcho:
- IMDF is probably the best external reference for how to structure indoor place data that a product team can actually author and render
- its feature list is much closer to a production app schema than a pure research/navigation model
- EchoEcho should seriously borrow its building/level/unit/opening/amenity/relationship vocabulary even if it does not adopt IMDF wholesale

## IndoorGML 2.0

Official sources:
- OGC standard page: https://www.ogc.org/standards/indoorgml
- OGC publications page: https://www.ogc.org/publications/standard/indoorgml/
- OGC 2025 announcement for IndoorGML 2.0 Part 1: https://www.ogc.org/announcement/ogc-publishes-indoorgml-2-0-part-1-conceptual-model-standard/

Current status:
- IndoorGML 2.0 Part 1 was published in 2025.
- OGC describes it as a conceptual model for interoperable exchange of indoor navigation network models.
- OGC explicitly says IndoorGML 2.0 Part 1 contains:
  - a core data model for topological connectivity and contexts of indoor space
  - a navigation data model extending that core for navigation applications

What it is good at:
- topology and connectivity
- modelling spaces and subdivisions of spaces
- logical and metric navigation networks
- formal relationships between indoor spaces and the navigation graph
- interoperable conceptual grounding for indoor routing

What it is weaker at:
- it is a conceptual standard, not the most pragmatic authoring/package format for product teams
- it is more abstract and heavier than most app teams want to implement directly
- it is better as a design reference than a drop-in application schema for EchoEcho

Why it matters for EchoEcho:
- IndoorGML is the strongest reference for how to think about indoor routing correctly
- it supports the idea that indoor navigation should be modelled as spaces plus connectivity, not as freehand lines drawn on top of a floorplan
- EchoEcho should borrow its topology/navigation concepts even if the database schema stays much simpler

## OpenStreetMap Simple Indoor Tagging

Official sources:
- OSM Indoor Mapping wiki: https://wiki.openstreetmap.org/wiki/Indoor_Mapping
- OSM Simple Indoor Tagging wiki: https://wiki.openstreetmap.org/wiki/Simple_Indoor_Tagging

Current status:
- OSM Indoor Mapping wiki was updated recently and still points to `Simple Indoor Tagging` as the current consensus.
- The schema relies heavily on tags such as:
  - `level=*`
  - `min_level=*`, `max_level=*`
  - `indoor=room|area|corridor|level`
  - door/window tags
  - stairs/elevator modelling with level ranges
- The OSM wiki notes that very simple POI-only indoor mapping can work with building-level tags plus POIs tagged by level, but that routing requires additional indoor elements.

What it is good at:
- open, community-editable representation
- flexible enough for many real-world buildings
- can represent rooms, corridors, stairs, elevators, doors, and level-aware POIs
- has a live ecosystem of viewers and editors

What it is weaker at:
- tagging flexibility also means weaker consistency
- editor and renderer support remains fragmented
- it is not a tightly-governed application schema in the same way IMDF is
- quality depends heavily on mapper discipline

Why it matters for EchoEcho:
- OSM gives a useful picture of the minimum viable ingredients needed for indoor navigation content
- its strongest contribution for EchoEcho is practical modelling intuition, not a canonical source-of-truth format
- if EchoEcho ever wants community/open-data interoperability, OSM tagging is the obvious bridge

## OpenIndoor and related OSM/open-source stacks

Official/open sources:
- OpenIndoor site: https://open-indoor.github.io/
- OSM Indoor Mapping wiki tools section: https://wiki.openstreetmap.org/wiki/Indoor_Mapping
- OpenIndoorMaps project: https://github.com/openindoormaps/openindoormaps
- indoorequal / indoor= vector tiles: https://github.com/indoorequal/indoorequal

What exists:
- `OpenIndoor` is a web-based indoor visualization approach with demos for indoor view, levels, and imports.
- `indoorequal` generates vector tiles from OpenStreetMap indoor data.
- The OSM wiki still lists active or semi-active indoor tools such as:
  - `indoor=` / indoorequal
  - `OpenLevelUp`
  - `OsmInEdit`
  - `OpenIndoor`
  - `OpenStationMap`
- `OpenIndoorMaps` positions itself as a self-hostable open-source indoor navigation project, but its GitHub README still describes it as early/pre-alpha.

What this means:
- there is open-source momentum and plenty of components for indoor rendering/viewing
- there is not one dominant, mature, open indoor navigation stack equivalent to what MapLibre/Geoman is for generic polygon editing
- the ecosystem remains useful for experimentation, demos, and selective borrowing, but not obviously strong enough to be EchoEcho's core platform

## Practical Comparison

### If you need a packaged feature model
- choose IMDF as the main reference

### If you need rigorous navigation topology
- choose IndoorGML as the main reference

### If you need open/community mapping compatibility
- choose OSM indoor tagging as the main reference

### If you need an open viewer/rendering ecosystem
- study OpenIndoor, OpenLevelUp, indoorequal, and OpenStationMap

## Recommendation for EchoEcho

Do not adopt any one of these standards wholesale as the product schema.

Instead:
- use `IMDF` as the main reference for venue/building/level/unit/opening/amenity semantics
- use `IndoorGML 2.0` as the main reference for graph topology, connectivity, and navigation modelling
- use `OSM Simple Indoor Tagging` and `OpenIndoor` as references for open interoperability and lightweight viewer/editor patterns

Concretely, EchoEcho should model interiors around:
- venue / campus
- building
- level
- destination / room / unit
- node
- edge
- connector (stairs, elevator, ramp, doorway, entrance)
- landmark / hazard

That is simpler than IMDF or IndoorGML in full, but aligned with both.

## Bottom Line

- `IMDF` is the best external reference for practical indoor feature modelling.
- `IndoorGML 2.0` is the best external reference for indoor routing topology.
- `OSM/OpenIndoor` is the best external open ecosystem for experimentation and interoperability, but it is too fragmented to be EchoEcho's primary data model.

EchoEcho should build a simplified hybrid model informed by IMDF + IndoorGML, rather than directly implementing either standard end-to-end.
