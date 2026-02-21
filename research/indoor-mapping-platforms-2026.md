# Indoor Mapping and Wayfinding Platforms (2026)

Researched: 2026-03-13

Scope:
- Current platform patterns for indoor mapping and wayfinding
- Focus on official docs and product pages
- Framed for EchoEcho's likely future split between student, router, and admin

## Executive Summary

The strongest commercial indoor platforms in 2026 all converge on the same core structure:

- venue / campus
- building
- level / floor
- destinations / places
- pathways / route graph
- vertical transitions such as elevators and stairs
- explicit indoor-outdoor handoff points

They differ mostly in:

- how much structure is required up front
- how much authoring happens in a CMS vs GIS tooling
- whether positioning is a core feature or optional

For EchoEcho, the best takeaway is not to copy any one platform wholesale. It is to borrow the shared model:

- web authoring for buildings, floors, and pathway graphs
- mobile validation for route truth, landmarks, and hazards
- route publication only after review

## ArcGIS Indoors

Official sources:
- ArcGIS Indoors information model:
  https://pro.arcgis.com/en/pro-app/latest/help/data/indoors/arcgis-indoors-information-model.htm
- Create floorplan data:
  https://pro.arcgis.com/en/pro-app/latest/help/data/indoors/create-floorplan-data.htm
- Create the Indoors network:
  https://pro.arcgis.com/en/pro-app/latest/help/data/indoors/create-the-indoors-network.htm

Current model:
- facilities and levels are first-class datasets
- pathways and transitions are first-class routing features
- floor-aware maps are central to the system
- indoor and outdoor route networks can be connected

What it does well:
- the most rigorous structured model among mainstream platforms
- very clear separation between floorplan data and navigation network
- strong support for multi-floor routing
- strong reference for route correctness and explicit transitions

What to borrow for EchoEcho:
- floors should be first-class entities
- hallways/pathways should be authored as network data, not only as polygons
- stairs, elevators, ramps, and entrances should be explicit connectors
- indoor/outdoor handoff should be intentional in the graph

What not to copy wholesale:
- the full ArcGIS geodatabase workflow is too heavy for EchoEcho right now

## Mappedin

Official sources:
- Product page:
  https://www.mappedin.com/
- CMS page:
  https://www.mappedin.com/map-cms
- Multi-building / path management announcement:
  https://www.mappedin.com/resources/news/mappedin-launches-multi-building-venue-mapping/

Current model:
- floor plans are turned into searchable digital venue maps
- venue-wide editing is managed through a CMS / editor workflow
- multi-building mapping and seamless indoor-outdoor navigation are core product themes
- path management is explicit in their newer multi-building tooling

What it does well:
- very strong product framing for campus-style venues
- good distinction between map content management and end-user navigation
- increasingly strong multi-building / campus wayfinding support

What to borrow for EchoEcho:
- treat campus + interiors as one connected venue, not separate worlds
- keep venue-wide editing and path management visible as product concepts
- separate visual map management from route publication/review

What to watch:
- Mappedin is a strong benchmark for product direction, not an obvious implementation base for EchoEcho

## MapsIndoors

Official sources:
- Documentation home:
  https://docs.mapsindoors.com/
- CMS:
  https://docs.mapsindoors.com/products/cms
- Wayfinding:
  https://docs.mapsindoors.com/sdks-and-frameworks/web/directions-and-routing
- Route access metadata:
  https://docs.mapsindoors.com/sdks-and-frameworks/integration-api/route-access

Current model:
- CMS-managed indoor map content
- route calculation spans indoor and outdoor navigation
- routes are broken into legs and steps
- entry points support transitions between venues and external maps
- route elements can carry restrictions, wait times, and one-way metadata

What it does well:
- clean productized model for route metadata
- good evidence that indoor routing needs route-level semantics beyond geometry
- accessibility and multi-stop navigation are clearly productized

What to borrow for EchoEcho:
- routes need metadata such as restrictions and preferred accessibility behavior
- connectors like doors/stairs/elevators should be treated as route-affecting elements
- route instructions should be step-based, not just polyline-based

## Situm

Official sources:
- Product page:
  https://situm.com/
- Mapping tool intro:
  https://situm.com/docs/introduction-to-situm-mapping-tool/
- Supported cartography:
  https://situm.com/docs/cartography-management/
- Cartography SDK docs:
  https://situm.com/docs/sdk-cartography/
- Wayfinding:
  https://situm.com/docs/wayfinding/

Current model:
- building and floor cartography are first-class
- supports raster images, raster tiles, GeoJSON, and IMDF
- POIs and geofences are built into the data model
- positioning and wayfinding are tightly connected
- mapping tool supports on-site calibration and cartography inspection

What it does well:
- strong example of integrating indoor mapping, wayfinding, and positioning
- practical tooling for mixed indoor/outdoor experiences
- good reminder that indoor cartography and navigation metadata live together

What to borrow for EchoEcho:
- support floor-level cartography and indoor POIs as explicit concepts
- keep optional room for positioning and geofencing later, but do not require it for v1
- treat indoor mapping as more than just polygons; it also needs operational metadata

## ServiceNow Indoor Mapping / Mapwize lineage

Official sources:
- Indoor Mapping docs:
  https://www.servicenow.com/docs/en-US/bundle/zurich-employee-service-management/page/product/wsd-indoor-mapping/reference/Indoor-mapping.html
- ServiceNow Mapwize acquisition context:
  https://www.servicenow.com/blogs/2022/hybrid-work-new-wayfinding-technology.html

Current model:
- campus, building, and floor hierarchy are central
- map authoring is treated as an operational management surface, not just an SDK concern
- role-based management and centralized indoor map governance are part of the product framing

What it does well:
- reinforces that indoor mapping is a content-management and governance problem
- useful reference for admin tooling and hierarchy design

What to borrow for EchoEcho:
- centralized map-studio / CMS mindset
- clear campus -> building -> floor authoring hierarchy
- role-based control over draft, review, and publish behavior

## MazeMap

Official source:
- Campus map JavaScript API example:
  https://www.mazemap.com/post/campus-map-javascript-api

Current model:
- campus-scale academic wayfinding
- browser-centric map consumption and embedding
- strong emphasis on room-level navigation and accessible path finding in large venues

What it does well:
- proves the university/campus use case is real and mature
- strong benchmark for searchable destinations and campus-wide indoor navigation

What to borrow for EchoEcho:
- campus-scale academic framing
- room-level search and navigation expectations
- accessibility-aware route overlays and destination discovery

## Common Platform Pattern

Across ArcGIS Indoors, Mappedin, MapsIndoors, and Situm, the strongest repeatable pattern is:

1. define venue/building/floor structure
2. author floor-aware geometry
3. author a pathway network with explicit transitions
4. connect indoor and outdoor networks
5. attach destinations and metadata
6. review, publish, and operate

## Recommendation for EchoEcho

EchoEcho should not start by trying to build a detailed indoor CAD clone.

It should start with:

- buildings
- levels
- key destinations
- hallway/path graph
- stairs/elevators/ramps
- entrances and outdoor-indoor connectors
- landmarks and hazards

The closest commercial reference model is:

- ArcGIS Indoors for structure and network correctness
- Mappedin for campus-level product framing
- MapsIndoors for route metadata and step semantics
- Situm for mixed cartography/positioning/product pragmatism
- ServiceNow Indoor Mapping for governance/CMS framing
- MazeMap for campus-scale academic wayfinding

## Bottom Line

The commercial market agrees on the hard part:

- indoor navigation is a graph problem layered on top of floor-aware map data

For EchoEcho, that means:

- web should own structural indoor authoring
- mobile should own route validation and refinement
- publication should depend on reviewed, validated route content
