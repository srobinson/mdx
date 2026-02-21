---
title: Sources of University Campus Polygon Boundary Data
type: research
tags: [geospatial, university, campus, polygon, geofence, GeoJSON, OpenStreetMap, HIFLD]
summary: Comprehensive catalog of free, commercial, and crowdsourced sources for university campus boundary polygons, with programmatic access details for each.
status: active
source: deep-research
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

University campus polygon boundaries are available from multiple sources at varying levels of coverage, accuracy, and cost. The three most practical options for a developer building campus geofencing into a mobile app are: (1) the HIFLD Colleges and Universities Campuses dataset (free, US-only, polygon, ~2000+ campuses), (2) OpenStreetMap via Nominatim or Overpass API (free, global, polygon for well-mapped campuses), and (3) the Google Geocoding API GROUNDS feature (paid, global, returns campus polygon for geocoded addresses within a campus). No single source provides a clean, comprehensive, global polygon dataset for all universities. A practical approach combines HIFLD for US coverage with OSM for gap-filling and international campuses.

## Detailed Findings

### 1. HIFLD Colleges and Universities Campuses (US Government)

**What it is:** A federal dataset maintained by the Homeland Infrastructure Foundation-Level Data (HIFLD) program, specifically the "Campuses" variant (distinct from the point-only "Colleges and Universities" dataset).

**Geometry type:** Polygon. This is confirmed polygon boundary data, not point data. The companion "Colleges and Universities" dataset is point-only; the "Campuses" dataset is the polygon version.

**Coverage:** US only. Includes all postsecondary institutions with enrollment >= 500, plus a subset of smaller institutions. Covers doctoral/research universities, masters colleges, baccalaureate, associates, theological seminaries, medical schools, tribal colleges, and specialized institutions. Excludes online-only institutions and institutions without a verifiable campus map.

**Format:** Downloadable as GeoJSON, Shapefile (zip), KML, CSV, GeoTIFF, PNG. Also accessible via GeoServices REST API, WMS, and WFS.

**Cost:** Free. Public domain federal data.

**Quality:** Authoritative for US institutions. Polygons are derived from campus maps and verified against satellite imagery. The population threshold means very small campuses may be excluded.

**Programmatic access:**
- ArcGIS Hub: https://hifld-geoplatform.opendata.arcgis.com/datasets/colleges-and-universities-campuses
- Direct GeoJSON download available from the hub page
- ArcGIS REST API (FeatureServer) supports spatial and attribute queries with GeoJSON output (`f=geojson`)
- Data.gov catalog: https://catalog.data.gov/dataset/universities-and-colleges

**Key attributes:** NAME, ADDRESS, CITY, STATE, ZIP, NAICS_CODE, POPULATION, and campus boundary polygon geometry.

**Limitation:** US only. No international coverage. Last updated date should be checked on the hub page; HIFLD updates are periodic, not continuous.

### 2. OpenStreetMap (Nominatim + Overpass API)

**What it is:** Crowdsourced global map data. University campuses are tagged with `amenity=university` and mapped as ways (simple polygons) or relations (multipolygons for distributed campuses).

**Geometry type:** Polygon and MultiPolygon. OSM best practice is to map universities as area features (closed ways or multipolygon relations), not nodes.

**Coverage:** Global, but quality varies significantly. Well-mapped in North America, Western Europe, Australia, and urban areas worldwide. Coverage of smaller or newer institutions in developing countries is uneven.

**Verified API tests (2026-03-13):**
- Stanford University: `osm_type=way`, returns `Polygon` with detailed boundary coordinates
- Harvard University: `osm_type=relation`, returns `MultiPolygon` (distributed campus correctly modeled)
- University of Melbourne: `osm_type=way`, returns `Polygon` (confirms international coverage)

**Programmatic access via Nominatim:**
```
GET https://nominatim.openstreetmap.org/search
  ?q=Stanford+University
  &format=jsonv2
  &polygon_geojson=1
  &limit=1
```
Returns GeoJSON polygon in the `geojson` field of the response. Rate limited to 1 request/second on the public instance. Must include a User-Agent header. Usage policy: https://operations.osmfoundation.org/policies/nominatim/

**Programmatic access via Overpass API:**
```
[out:json][timeout:25];
(
  way["amenity"="university"]({{bbox}});
  relation["amenity"="university"]({{bbox}});
);
out geom;
```
Returns raw OSM geometry. Use `osmtogeojson` library to convert to GeoJSON. Public Overpass instances have rate limits and can be busy; consider self-hosting for production use. Endpoint: https://overpass-api.de/api/interpreter

**Programmatic access via Bunting Labs API:**
Bunting Labs provides a simplified REST API over OSM data that returns GeoJSON directly, avoiding Overpass QL syntax and rate limits. Free for < 10M features/month, $49/month for larger workloads. https://buntinglabs.com

**Cost:** Free (ODbL license, attribution required). Self-hosted Overpass or Nominatim instances are also free but require infrastructure.

**Quality assessment:** Good for major universities in developed countries. The tagging convention (`amenity=university` on areas) is well-established. However:
- Some campuses are mapped as nodes (points) instead of polygons
- Distributed campuses may be mapped inconsistently (separate polygons vs. multipolygon relations)
- No systematic quality check; data is as good as the local mapping community
- The University of Cambridge case study showed that dense urban campuses require manual mapping effort beyond GPS traces

**OSM tagging reference:** https://wiki.openstreetmap.org/wiki/Tag:amenity=university

### 3. Google Geocoding API - GROUNDS Feature

**What it is:** An experimental feature in the Google Geocoding API that returns the polygon boundary of the "grounds" surrounding a geocoded location. For a building on a university campus, the grounds polygon represents the university campus boundary.

**Geometry type:** GeoJSON Polygon or MultiPolygon (RFC 7946).

**Coverage:** Global, but only works for "some, but not all, places with a precise location." You must geocode a specific address or building within the campus; you cannot query by university name alone to get the campus polygon.

**Programmatic access:**
```
GET https://maps.googleapis.com/maps/api/geocode/json
  ?address=Gates+Building,+Stanford+University
  &extra_computations=GROUNDS
  &key=YOUR_API_KEY
```
Returns a `grounds` object with `outline` (GeoJSON polygon) and `display_name` fields.

**Cost:** Paid. Google Maps Geocoding API pricing applies ($5 per 1,000 requests as of 2025, $200/month free credit).

**Quality:** High accuracy where available, backed by Google's mapping data. However, the feature is marked as "experimental" and has been superseded by the `SearchDestinations` method in Geocoding API v4. Not all campuses return grounds data.

**Limitation:** Requires geocoding a specific address first. Cannot enumerate all campuses. Best used as a point lookup ("is this address on a campus, and if so, what is the campus boundary?") rather than a bulk data source.

### 4. Google Geocoding API - Building Outlines

**What it is:** Returns individual building footprint polygons, not campus-level boundaries.

**Access:** `extra_computations=BUILDING_AND_ENTRANCES` parameter.

**Relevance:** Useful for building-level detection within a campus, not for campus boundary detection. Returns one building per request. Not a substitute for campus polygons.

### 5. Precisely (formerly Pitney Bowes) Colleges Dataset

**What it is:** A commercial geospatial dataset providing polygon boundaries around two-year and four-year colleges and universities in the US with enrollment > 200.

**Geometry type:** Polygon. Reflects both main and satellite campuses. Some colleges have multiple polygon records for geographically dispersed campuses.

**Coverage:** US only.

**Cost:** Commercial license. Pricing not publicly listed; contact sales.

**Quality:** High. Includes adjacent buildings and properties associated with the institution. Isolated facilities are excluded unless they represent areas where students concentrate.

**Access:** Via Precisely data marketplace. Available as Shapefile. https://www.precisely.com/data-guide/products/college-data/

### 6. SafeGraph / Dewey Data (Geometry Dataset)

**What it is:** SafeGraph provides POI data with building footprint polygons, including a parent-child spatial hierarchy. College campuses are modeled as parent polygons containing child POIs (buildings, facilities).

**Geometry type:** Polygon. Campus polygons represent the overall campus footprint, which may include parking lots, land, and multiple buildings.

**Coverage:** Global (~7.8M POIs with geometry metadata).

**Cost:** Commercial. Available through Dewey Data marketplace. Academic access programs may be available.

**Quality:** Good for major institutions. The polygon fitting algorithm adapts to POI type (a college campus polygon encompasses the full campus area, unlike a single retail store which gets a building footprint).

**Key feature:** Placekey identifier system provides stable, persistent IDs for places. Parent-child relationships let you associate buildings with their campus.

**Access:** Bulk download via Dewey Data. API access may be available. https://docs.safegraph.com/docs/geometry-data

### 7. Radar.io Geofencing Platform

**What it is:** A geofencing SDK and API. Does NOT provide pre-built university campus polygons, but provides the infrastructure to create and manage polygon geofences programmatically.

**Geometry type:** Supports circle, polygon, and isochrone geofences. Polygon coordinates follow GeoJSON convention (longitude, latitude).

**Coverage:** Global (you supply the polygon data).

**Cost:** Free tier available. Paid plans for higher volume.

**Relevance:** Best used as the geofencing engine, not as the polygon data source. You would import campus polygons from HIFLD or OSM into Radar, then use their SDK for on-device geofence detection.

**Key advantages for mobile apps:**
- Unlimited geofences (overcomes iOS 20 / Android 100 circular geofence limits)
- Cross-platform SDK (iOS, Android, React Native, Flutter)
- 5-meter accuracy claimed
- Campus-specific example in their docs (check if user is inside a "campus" tagged geofence)

**Access:** https://docs.radar.com/geofencing/geofences

### 8. Mapbox Boundaries

**What it is:** Mapbox's boundary data product covering administrative, legislative, postal, and statistical boundaries.

**Relevance:** Does NOT include university campus boundaries. Covers political/administrative divisions only. You would need to upload custom campus polygons as a Mapbox tileset using their Tiling Service.

### 9. NCES/IPEDS/EDGE

**What it is:** The National Center for Education Statistics provides geocodes for postsecondary institutions via the EDGE program.

**Geometry type:** Point only. Provides latitude/longitude centroids derived from IPEDS survey addresses, not polygon boundaries.

**Relevance:** Useful as a lookup table (IPEDS UNITID to lat/lon) but not for campus boundary detection. The UNITID can be used to join with HIFLD data.

**Access:** https://nces.ed.gov/programs/edge/geographic/schoollocations

### 10. University-Published GIS Data

Some universities publish their own campus GIS data through institutional GIS offices or open data portals. Examples:
- NC State Facilities Maps
- Portland State University (https://gis-pdx.opendata.arcgis.com/datasets/campus-boundary)
- Many universities with GIS programs maintain internal datasets

**Format:** Varies (Shapefile, GeoJSON, KML).
**Coverage:** Individual institutions only. No standard format or central registry.
**Quality:** Highest accuracy for that specific campus (authoritative source).
**Limitation:** No programmatic way to discover or aggregate these. Useful for specific high-priority campuses where HIFLD/OSM data is insufficient.

## Recommended Architecture for Mobile Campus Detection

For a mobile app that needs to detect whether a user is on a specific university campus:

1. **Data pipeline:** Start with HIFLD Campuses dataset for US universities (free, polygon, authoritative). Supplement with OSM Nominatim queries for international universities and any US campuses missing from HIFLD.

2. **Storage:** Import polygons into your backend database (PostGIS) or a geofencing service (Radar.io).

3. **On-device detection:** Use Radar SDK or a similar geofencing library that supports polygon geofences. The "minimum enclosing circle" optimization (wrap polygon in circle geofence, then do precise polygon hit-testing only when inside the circle) is the standard approach for battery efficiency.

4. **Fallback:** For campuses without polygon data, use a circular geofence centered on the NCES/IPEDS centroid with a reasonable radius (500m-1km depending on institution size).

5. **Google GROUNDS as supplement:** For individual campus lookups where you have a street address, the Google Geocoding API GROUNDS feature can return the campus polygon. Useful for on-demand lookups but too expensive and address-dependent for bulk data collection.

## Sources Consulted

### Government Data Portals
- [HIFLD Colleges and Universities Campuses](https://hifld-geoplatform.opendata.arcgis.com/datasets/colleges-and-universities-campuses) - ArcGIS Hub
- [HIFLD Colleges and Universities (point data)](https://hifld-geoplatform.opendata.arcgis.com/datasets/colleges-and-universities) - ArcGIS Hub
- [Universities and Colleges - Data.gov](https://catalog.data.gov/dataset/universities-and-colleges)
- [NCES EDGE Geographic Data](https://nces.ed.gov/programs/edge/geographic/schoollocations)

### OpenStreetMap
- [Tag:amenity=university - OSM Wiki](https://wiki.openstreetmap.org/wiki/Tag:amenity=university)
- [Universities - OSM Wiki](https://wiki.openstreetmap.org/wiki/Universities)
- [Key:campus - OSM Wiki](https://wiki.openstreetmap.org/wiki/Key:campus)
- [Mapping University of Cambridge case study](https://osmuk.org/case-studies/mapping-a-distributed-campus-for-the-university-of-cambridge/)
- [Nominatim Search API](https://nominatim.org/release-docs/latest/api/Search/)
- [Overpass API documentation](https://wiki.openstreetmap.org/wiki/Overpass_API)

### Commercial Providers
- [Precisely Colleges Dataset](https://www.precisely.com/data-guide/products/college-data/)
- [SafeGraph Geometry Data](https://docs.safegraph.com/docs/geometry-data)
- [SafeGraph Geometry Blog Post](https://www.safegraph.com/blog/geometry-the-anchor-of-safegraph-places)
- [Radar Geofencing](https://radar.com/product/geofencing)
- [Radar Geofences Documentation](https://docs.radar.com/geofencing/geofences)
- [Radar Student Hackathon Playbook](https://radar.com/blog/radar-student-hackathon-playbook)

### Google Maps Platform
- [Geocoding API - Grounds](https://developers.google.com/maps/documentation/geocoding/grounds)
- [Geocoding API - Building Outlines](https://developers.google.com/maps/documentation/geocoding/building-attributes)

### Other APIs and Tools
- [Bunting Labs OSM API](https://buntinglabs.com/blog/introducing-an-api-to-download-from-openstreetmap)
- [Mapbox Boundaries](https://www.mapbox.com/boundaries)
- [Geoapify Boundaries API](https://www.geoapify.com/boundaries-api/)
- [Overpass Turbo (interactive query tool)](https://overpass-turbo.eu/)

### Geofencing Implementation
- [Transistor Software - Polygon Geofencing](https://transistorsoft.medium.com/polygon-geofencing-d99169a90538) - Minimum enclosing circle optimization
- [Baeldung - Point in Polygon](https://www.baeldung.com/cs/geofencing-point-inside-polygon)

## Source Quality Assessment

**High confidence:** HIFLD Campuses (authoritative US government data, polygon confirmed), OSM/Nominatim (verified via API testing, polygon data confirmed for major universities globally), Google GROUNDS (Google documentation, experimental status noted).

**Medium confidence:** Precisely and SafeGraph (documentation reviewed, but pricing and access details require direct vendor contact). Radar (well-documented, but is an infrastructure tool, not a data source).

**Low confidence:** Individual university GIS portals (anecdotal, no systematic survey conducted).

**Gap:** No Reddit or HackerNews discussions found specifically about campus polygon data sources. The topic appears too niche for community forums; the expertise lives in GIS professionals and geospatial data engineers rather than general developer communities.

## Open Questions

1. **HIFLD Campuses record count:** The exact number of campus polygons in the dataset was not confirmed. Downloading the dataset and counting features would establish this.
2. **HIFLD update frequency:** How often are polygons updated? New campus construction or boundary changes may not be reflected promptly.
3. **OSM coverage completeness:** What percentage of IPEDS-listed institutions have polygon (not point) mappings in OSM? A systematic comparison between IPEDS and OSM would quantify the gap.
4. **Google GROUNDS coverage:** For what percentage of US universities does the GROUNDS feature return a polygon? This requires empirical testing.
5. **Precisely pricing:** Commercial terms for the Colleges dataset are not publicly available.

## Actionable Takeaways

1. **Download the HIFLD Campuses GeoJSON now.** It is the single best free source for US university campus polygons. Direct download from the ArcGIS Hub page.

2. **Build a Nominatim lookup pipeline for international campuses.** Query by university name with `polygon_geojson=1`. Cache results aggressively (OSM data changes slowly). Respect rate limits (1 req/sec on public instance) or self-host.

3. **Evaluate Radar.io as the on-device geofencing engine.** Their SDK handles the hard parts (battery optimization, polygon geofence management, cross-platform support). Import your HIFLD/OSM polygons into Radar.

4. **For a small, known set of campuses:** Manual polygon creation in a tool like geojson.io or QGIS, using satellite imagery, will produce the highest-quality boundaries. This is viable for 10-50 campuses but does not scale.

5. **Test Google GROUNDS** for your specific target universities to assess coverage. If it works reliably for your list, it provides the most authoritative polygon data at the cost of per-request pricing.
