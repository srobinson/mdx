---
title: Indoor Mapping Data Sources for US University Buildings
type: research
tags: [indoor-mapping, universities, accessibility, IMDF, IndoorGML, ADA, visually-impaired, wayfinding]
summary: Comprehensive landscape of indoor building map data for US universities, covering institutional sources, platform ecosystems, open data, standards, and accessibility-specific solutions.
status: active
source: deep-research
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

US universities almost universally maintain digital floor plans (CAD/BIM) for facilities management, but these are rarely published as open data. Structured indoor map data suitable for navigation is available through a fragmented ecosystem of commercial platforms (MazeMap, Mappedin, Concept3D, Esri ArcGIS Indoors), consumer mapping services (Google Indoor Maps, Apple Indoor Maps), and open data projects (OpenStreetMap Simple Indoor Tagging). For accessibility-focused indoor navigation targeting visually impaired users, the most promising paths are: (1) partnering directly with university facilities departments to obtain CAD/BIM data, (2) leveraging GoodMaps, which already deploys LiDAR-scanned indoor maps at universities specifically for blind users, and (3) building on IndoorGML 2.0 or IMDF as the data standard. ADA Title II's April 2026 compliance deadline for digital accessibility is creating strong institutional pressure for universities to invest in accessible digital maps.

## 1. University-Provided Indoor Maps

### What Universities Have

Every US university with a facilities management department maintains building floor plans. These exist primarily in:

- **AutoCAD (.dwg/.dxf)**: The dominant format for architectural drawings. Nearly all university facilities departments have these.
- **Revit/BIM (.rvt, .ifc)**: Newer buildings increasingly have BIM models with richer semantic data (room types, door widths, accessibility features).
- **PDF floor plans**: Published on university websites for wayfinding, but unstructured and not machine-readable.

### Specific Examples

- **University of Colorado Boulder**: Maintains a GIS/CAD office that houses building floor plans in CAD, PDF, and Revit formats. [Source](https://www.colorado.edu/gis-cad/building-floor-plans)
- **Stanford University**: Maps & Records department provides floor plans and infrastructure drawings in PDF and CAD formats. Access is restricted. [Source](https://mapsandrecords.stanford.edu/)
- **University of Pennsylvania**: Facilities Resource Center holds architectural drawings, studies, and CAD files. Requires PennKey (restricted to Penn community). [Source](https://facilities.upenn.edu/services/campus-and-building-plans)
- **Rutgers University**: Uses ArcGIS Indoors for its most complex building, converting CAD data to GIS-navigable indoor maps. [Source](https://www.esri.com/about/newsroom/arcuser/wayfinding)

### Key Finding

Universities maintain the raw data (CAD/BIM) but treat it as restricted institutional data, not open data. Security concerns (building infrastructure details) and licensing (architectural firms retain copyright on drawings) are the primary barriers. However, facilities departments will typically share floor plans with approved partners, especially for accessibility projects. The data quality varies enormously: some buildings have meticulously maintained BIM models, while older buildings may only have scanned paper drawings.

## 2. Apple Indoor Maps / IMDF

### Current State

Apple's Indoor Maps Program accepts venues through their Apple Business Register. As of the current documentation, **only airports are being actively added to Apple Maps** for indoor display. Other venue types (shopping centers, campuses) are considered on a case-by-case basis. [Source](https://register.apple.com/resources/indoor/program/indoor_maps)

### IMDF (Indoor Mapping Data Format)

- **Format**: A set of GeoJSON files describing indoor spaces, levels, units (rooms), openings (doors), and amenities.
- **OGC Standard**: IMDF 1.0.0 was adopted as an OGC Community Standard in February 2021.
- **Cost**: Free to use. No fees for registration or the indoor positioning service.
- **Requirements**: Floor plans must be geo-referenced to lat/lon. An RF survey using Apple's Indoor Survey app is required for positioning.
- **Accessibility data**: IMDF supports `accessibility` properties on units and openings (door widths, ramp presence, elevator locations).
- **Tooling**: Mappedin offers IMDF export. An open-source converter exists from IndoorGML to IMDF ([GitHub: STEMLab/indoorgml-to-imdf](https://github.com/STEMLab/indoorgml-to-imdf)).

### University Adoption

No publicly documented cases of US universities with live Apple Indoor Maps were found. The program's current airport-first focus and the requirement for Apple's proprietary RF survey process likely limit university adoption. Apple may expand venue types over time, but this is not a near-term data source for campus buildings.

### Relevance to Accessibility

IMDF's structured GeoJSON format is well-suited for accessibility applications regardless of whether the data ends up in Apple Maps. The format can represent room types, door characteristics, and accessibility features. It is lightweight and renderable on any platform.

## 3. Google Indoor Maps

### Coverage

Google Indoor Maps has been available since 2012 and covers airports, malls, transit stations, and some university buildings. Coverage of university buildings is inconsistent. A 2012 Google blog post actively recruited universities to submit floor plans. [Source](https://students.googleblog.com/2012/02/google-maps-get-your-university-on.html)

### Submission Process

- Institutions upload floor plan images (PNG, PDF, JPEG) through the Google Maps Content Partners portal.
- Floor plans are aligned to building footprints manually.
- Google reviews and publishes the maps at no cost.
- Contact for Americas: indoorpartners-americas@google.com
- The published maps appear as floor-selectable overlays in Google Maps.

### Limitations for Accessibility

Google Indoor Maps renders floor plans as image overlays, not as structured navigable data. There is no routing between rooms, no semantic information about room types, door widths, or accessibility features. The data is not exportable. This makes Google Indoor Maps unsuitable as a data source for accessibility navigation, though the floor plan images themselves could serve as a starting point for digitization.

## 4. OpenStreetMap Indoor Mapping

### Tagging Standard

**Simple Indoor Tagging** is the consensus schema. Key tags:
- `level=*` for floor assignment
- `indoor=room`, `indoor=corridor`, `indoor=area`
- `room=*` (classroom, office, toilet, elevator, stairs)
- `highway=corridor` or `highway=footway` + `indoor=yes` for navigable paths
- `door=*` with `width=*` for accessibility-relevant door data
- `wheelchair=yes/no/limited` on rooms and corridors

### Tools

- **OsmInEdit**: Web-based indoor editor with floor plan overlay support
- **OpenLevelUp**: Web viewer that renders indoor data level by level
- **OpenIndoor**: 3D viewer based on Mapbox

### University Coverage

Coverage is extremely sparse for US universities. The documented indoor-mapped university buildings are primarily European:
- Technical University of Munich (400+ building parts, imported from NavigaTUM dataset)
- TU Ilmenau, Ostfalia University (Germany)
- University of Toronto Medical Sciences Building (Canada)
- Universidad Publica de Navarra (Spain)

No US university buildings with substantial indoor OSM coverage were found.

### Relevance

OSM's Simple Indoor Tagging schema is well-designed and supports accessibility-relevant properties. However, the community-driven mapping model means coverage depends on volunteer effort, and US university campuses have essentially no indoor data. OSM could be a distribution target (publish your data to OSM) rather than a data source.

## 5. ADA / Accessibility Requirements

### Physical Signage (Existing Law)

ADA Standards for Accessible Design require:
- Tactile signs at permanent rooms, stairways, elevators, exits
- Braille on room identification signs
- Contrasting colors (70% contrast ratio)
- Specific mounting heights (27-80 inches)

### Digital Accessibility (New April 2026 Mandate)

The DOJ published new Title II regulations on April 24, 2024, requiring WCAG 2.1 AA compliance for all digital content of public universities by **April 24, 2026**. This explicitly covers:
- Interactive campus maps
- Online portals
- Mobile apps
- Any web-based wayfinding tools

This means any digital indoor map a public university publishes must be keyboard-operable, screen-reader compatible, and meet WCAG contrast/text requirements. [Source](https://www.ada.gov/resources/2024-03-08-web-rule/)

### No Mandate for Indoor Digital Maps

ADA does not currently require universities to *create* digital indoor maps or provide indoor wayfinding apps. The requirements apply to physical signage and, if digital maps exist, to their accessibility. However, the combination of the new digital accessibility mandate and growing institutional focus on inclusion creates strong tailwinds for accessible indoor mapping solutions.

### Institutional Pressure

Ohio State, UNC Chapel Hill, Boise State, UCSF, University of Washington, and NC State have all published guidance pages about Title II compliance. Universities are actively investing in digital accessibility infrastructure. [Sources: accessibility.osu.edu, digitalaccessibility.unc.edu, boisestate.edu/compliance/ada]

## 6. Indoor Mapping Platforms with University Deployments

### MazeMap (Norway-based, global leader in higher ed)

- **Focus**: Purpose-built for university and hospital campus wayfinding
- **Scale**: Up to 5 million users at deployment scale
- **US Presence**: Oakland Community College confirmed; broader US customer list not publicly available. Recently partnered with Ellucian (dominant higher ed ERP) for integrated campus navigation.
- **Accessibility**: Offers accessibility-focused routing (wheelchair paths, elevator preference)
- **Data model**: Proprietary; they digitize your floor plans
- **Cost**: Enterprise SaaS pricing (not published)
- [Source](https://mazemap.com/intro/university-mapping)

### Concept3D (US-based, strong in higher ed marketing)

- **Focus**: Interactive 3D campus maps, virtual tours, event calendars
- **Customers**: Arizona State University and 300+ campuses
- **Indoor**: Floor-by-floor indoor maps with room-level detail
- **Accessibility**: Wheelchair-accessible route filtering, ADA-compliant entrance labeling, assistive technology compatibility
- **Cost**: SaaS pricing, tiered by campus size
- [Source](https://concept3d.com/use-cases/higher-education/)

### Esri ArcGIS Indoors

- **Focus**: Enterprise GIS extension for indoor space management and navigation
- **University deployments**: Rutgers University (complex building wayfinding), German universities (FHWS, HTW Dresden)
- **Data pipeline**: Converts CAD/BIM floor plans to GIS-navigable indoor maps using the Indoors model
- **Standards**: Supports IMDF export
- **Cost**: Requires ArcGIS enterprise license; significant investment
- [Source](https://www.esri.com/en-us/arcgis/products/arcgis-indoors/overview)

### Mappedin (Canada-based)

- **Focus**: Multi-venue indoor mapping (malls, airports, campuses)
- **University customers**: University of Calgary, University of Ottawa, Mohawk College
- **Features**: SDK/API-first, IMDF export, blue-dot indoor positioning
- **Deployment timeline**: 8-16 weeks single building, 3-6 months multi-building campus
- **Cost**: Enterprise SaaS
- [Source](https://www.mappedin.com/industries/colleges-and-universities/)

### Aruba Meridian (HPE)

- **Focus**: Indoor navigation leveraging existing WiFi/BLE infrastructure
- **University deployment**: University of Oklahoma Libraries (seven-floor, 400,000 sq ft system including libraries, museums, weather center)
- **Technology**: BLE beacons + WiFi fingerprinting
- **Cost**: Bundled with Aruba networking infrastructure
- [Source](https://news.arubanetworks.com/press-release/university-oklahoma-libraries-launches-navapp-provide-mobile-indoor-navigation-and-con)

### GoodMaps (US-based, accessibility-first)

- **Focus**: Specifically designed for blind and visually impaired indoor navigation
- **Founded by**: American Printing House for the Blind (APH) in 2019
- **Technology**: LiDAR backpack scanning (360-degree images, laser measurements, video) to create detailed digital maps. Computer vision for positioning.
- **University deployments**:
  - Michigan State University (STEM Building, Bessey Hall)
  - Ontario Tech University (Library, Business Building, Energy Research Centre, Science Building)
  - Portland State University (Smith Student Union)
- **Accuracy**: Down to one foot using LiDAR + computer vision
- **Cost**: Free app for end users; institutional deployment costs not published
- **Relevance**: The most directly relevant platform for visually impaired campus navigation. GoodMaps handles the full pipeline from scanning to deployment.
- [Source](https://goodmaps.com/), [MSU deployment](https://www.rcpd.msu.edu/news/ability-blog/msu-improves-campus-accessibility-through-introducing-goodmaps)

## 7. Standards Comparison for Accessibility Indoor Mapping

| Standard | Type | Accessibility Support | Navigation Model | Maturity | Best For |
|----------|------|----------------------|-----------------|----------|----------|
| **IMDF** | GeoJSON-based, OGC Community Standard | Accessibility properties on units/openings | Path computation between features | Production (1.0.0, 2021) | Lightweight mapping, Apple ecosystem, cross-platform rendering |
| **IndoorGML 2.0** | XML/GML, OGC Standard | Extension models for mobility disabilities; space-graph supports wheelchair vs. walking user routing | Topological graph of navigable cells and transitions | Published Aug 2025 (Part 1 conceptual model) | Navigation-first applications, multi-modal routing, research |
| **IFC (Industry Foundation Classes)** | BIM standard | Rich geometric/semantic data (door widths, ramp grades, elevator specs) | Not designed for navigation; requires conversion | Mature (ISO 16739) | Source data from architects; convert to IndoorGML/IMDF for navigation |
| **Simple Indoor Tagging (OSM)** | Key-value tags on OSM geometries | `wheelchair=*`, `tactile_paving=*`, door `width=*` | Uses OSM routing engines (OSRM, Valhalla) | Active community standard | Open data distribution, community contribution |

### Key Insight

IFC/BIM is where the data originates (from architects and facilities departments). IndoorGML and IMDF are where it needs to go for navigation. Open-source converters exist: [IFC2IndoorGML](https://filipbiljecki.com/publications/2022_isprs_ifc2indoorgml.pdf) and [IndoorGML-to-IMDF](https://github.com/STEMLab/indoorgml-to-imdf). For an accessibility-focused project, IndoorGML 2.0 has the richest navigation model (separate routing graphs for different mobility profiles), while IMDF has the widest platform support.

## 8. Research and Emerging Approaches

### UC Santa Cruz (Manduchi Lab)

Two experimental apps for blind indoor navigation that work with building floor plan maps and smartphone inertial sensors (accelerometer, gyroscope). Users do not need to hold their phone in front of them. The apps provide wayfinding (navigation to a point) and backtracking (retracing a route). Testing was conducted in the Baskin Engineering building. Future work includes AI-based scene description from photos. [Source](https://news.ucsc.edu/2024/10/manduchi-wayfinding-apps/)

### University of San Diego (RightHear)

Deployed the RightHear assistive technology system that interprets indoor spaces aloud in real-time using BLE beacons. First known building in San Diego County with this technology. [Source](https://www.sandiego.edu/news/detail.php?_focus=94163)

### Snap&Nav (ACM 2024)

A navigation system for blind users in unfamiliar buildings that does NOT require pre-built digital maps. Instead, it photographs physical floor plan signs posted in building lobbies and uses computer vision to extract navigation data. This approach bypasses the data availability problem entirely. [Source](https://dl.acm.org/doi/10.1145/3676522)

## Sources Consulted

### Institutional / University Sources
- [University of Colorado Boulder GIS/CAD](https://www.colorado.edu/gis-cad/building-floor-plans)
- [Stanford Maps & Records](https://mapsandrecords.stanford.edu/)
- [UPenn Facilities](https://facilities.upenn.edu/services/campus-and-building-plans)
- [MSU GoodMaps deployment](https://www.rcpd.msu.edu/news/ability-blog/msu-improves-campus-accessibility-through-introducing-goodmaps)
- [Ontario Tech GoodMaps](https://accessibility.ontariotechu.ca/resources/goodmaps-explore.php)
- [Ohio State ADA Title II guidance](https://accessibility.osu.edu/title-ii)
- [UNC Digital Accessibility](https://digitalaccessibility.unc.edu/ada-title-ii-info-and-faq/)

### Standards Bodies
- [Apple IMDF documentation](https://register.apple.com/resources/imdf/)
- [Apple Indoor Maps Program](https://register.apple.com/resources/indoor/program/indoor_maps)
- [OGC IndoorGML 2.0 announcement](https://www.ogc.org/announcement/ogc-publishes-indoorgml-2-0-part-1-conceptual-model-standard/)
- [OGC IMDF Community Standard](https://www.ogc.org/standards/indoor-mapping-data-format/)
- [IndoorGML accessibility extension paper (MDPI)](https://www.mdpi.com/2220-9964/9/2/66)
- [IFC2IndoorGML converter paper](https://filipbiljecki.com/publications/2022_isprs_ifc2indoorgml.pdf)
- [IndoorGML-to-IMDF converter](https://github.com/STEMLab/indoorgml-to-imdf)

### Platform Vendors
- [MazeMap for universities](https://mazemap.com/intro/university-mapping)
- [Concept3D accessible campus maps](https://resources.concept3d.com/accessible-campus-maps)
- [Esri ArcGIS Indoors](https://www.esri.com/en-us/arcgis/products/arcgis-indoors/overview)
- [Mappedin for universities](https://www.mappedin.com/industries/colleges-and-universities/)
- [GoodMaps](https://goodmaps.com/)
- [Aruba/University of Oklahoma](https://news.arubanetworks.com/press-release/university-oklahoma-libraries-launches-navapp-provide-mobile-indoor-navigation-and-con)

### Google Indoor Maps
- [Google Indoor Maps submission](https://www.google.com/maps/about/partners/indoormaps/)
- [Google student blog (2012)](https://students.googleblog.com/2012/02/google-maps-get-your-university-on.html)

### OpenStreetMap
- [OSM Indoor Mapping wiki](https://wiki.openstreetmap.org/wiki/Indoor_Mapping)
- [Simple Indoor Tagging](https://wiki.openstreetmap.org/wiki/Simple_Indoor_Tagging)
- [NavigaTUM import (TU Munich)](https://wiki.openstreetmap.org/wiki/Import/Indoor_Navigatum)

### ADA / Legal
- [ADA.gov Title II web rule fact sheet](https://www.ada.gov/resources/2024-03-08-web-rule/)
- [AGB Policy Alert on April 2026 deadline](https://agb.org/news/agb-alerts/agb-policy-alert-ada-digital-accessibility-rule-requires-full-compliance-by-april-2026/)

### Research / Blind Navigation
- [UC Santa Cruz Manduchi wayfinding apps](https://news.ucsc.edu/2024/10/manduchi-wayfinding-apps/)
- [University of San Diego RightHear](https://www.sandiego.edu/news/detail.php?_focus=94163)
- [Snap&Nav (ACM)](https://dl.acm.org/doi/10.1145/3676522)
- [GoodMaps and National Federation of the Blind](https://nfb.org/innovating-mapping-technology-mission-built-experience-blind-jose-gaztambide-ceo-goodmaps)

### HackerNews
- [IMDF discussion](https://news.ycombinator.com/item?id=24763023)
- [Indoor map usage discussion](https://news.ycombinator.com/item?id=24787005)
- [FIND3 indoor positioning](https://news.ycombinator.com/item?id=21700689)

## Source Quality Assessment

**High confidence**: ADA Title II requirements, IMDF/IndoorGML standard specifications, GoodMaps university deployments (confirmed by university press releases), platform vendor capabilities (confirmed by documentation).

**Medium confidence**: University floor plan availability patterns (confirmed for three universities, generalized based on facilities management norms). Apple Indoor Maps' airport-only restriction (based on current documentation; may have expanded without public announcement). Google Indoor Maps university coverage (anecdotal, no comprehensive data).

**Low confidence**: Specific customer lists for MazeMap and Concept3D (vendors do not publish comprehensive lists). OSM indoor mapping completeness for any specific campus.

## Open Questions

1. **GoodMaps pricing and partnership model**: What does it cost for a university to deploy GoodMaps? Is there a data-sharing arrangement where the scanned indoor maps could be used by third parties?
2. **IMDF adoption beyond airports**: Has Apple quietly expanded Indoor Maps to any university venues? The documentation lags reality.
3. **BIM/IFC availability**: What percentage of university buildings have BIM models vs. only 2D CAD? BIM models contain accessibility-relevant semantics (door widths, ramp grades) that 2D CAD lacks.
4. **Snap&Nav viability**: The approach of photographing posted floor plan signs and extracting navigation data via CV is compelling for scaling without institutional data partnerships. How robust is it in practice?
5. **Crowdsourced indoor mapping**: Could a volunteer or student-driven effort map university buildings into OSM using Simple Indoor Tagging at meaningful scale?

## Actionable Takeaways

1. **Fastest path to deployed accessibility navigation**: Partner with GoodMaps. They handle the full scanning-to-app pipeline and have an explicit mission around blind navigation. Three US universities already use them.

2. **Build-your-own path**: Obtain CAD/BIM data from university facilities departments (pitch it as an accessibility project; ADA Title II pressure makes this easier). Convert IFC to IndoorGML or IMDF using open-source tools. Build navigation on top of the graph model.

3. **Standards choice**: Use IMDF as the interchange format (lightweight, GeoJSON-based, wide tool support). Use IndoorGML 2.0's navigation model concepts for routing (separate graphs for different mobility profiles). Store source data in IFC/BIM where available.

4. **Leverage ADA Title II deadline**: The April 2026 compliance deadline creates urgency at public universities. Position an accessible indoor mapping solution as helping universities meet their obligations.

5. **Hybrid approach for scale**: For buildings where institutional data is unavailable, explore Snap&Nav-style approaches (CV extraction from posted floor plans) or crowdsourced OSM indoor tagging as fallbacks.

6. **Avoid Google Indoor Maps as a data source**: The data is image-based, non-exportable, and lacks semantic/accessibility information. Apple's IMDF is superior for structured data.
