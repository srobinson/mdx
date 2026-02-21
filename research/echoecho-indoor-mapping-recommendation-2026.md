# EchoEcho Indoor Mapping Recommendation (2026)

See also:
- `indoor-mapping-platforms-2026.md`
- `indoor-mapping-standards-2026.md`
- `indoor-authoring-workflows-2026.md`

## Recommendation

Treat building interiors as a routable graph, not just a floorplan.

For EchoEcho, the best near-term model is:

- campus
- building
- level
- destination
- node
- edge
- connector
- landmark
- hazard

### Authoring Split

- `admin/web`: buildings, floors, hallway/path graph, destinations, vertical connectors
- `router/mobile`: field validation, landmarks, hazards, route truth, targeted corrections
- `student`: published routes only

### Product Rule

Keep these distinct:

- structurally drafted indoor graph
- walked and validated indoor route content
- published student guidance

### What Not To Do First

- exhaustive room polygon editing
- BIM/CAD-perfect digital twins
- dependence on indoor blue-dot positioning
- floorplan beauty before graph correctness

### Best External References

- `IMDF` for practical indoor feature taxonomy
- `IndoorGML 2.0` for navigation topology concepts
- `ArcGIS Indoors` for structured authoring workflow
- `Mappedin` for campus-scale product framing
- `MapsIndoors` for route metadata and step semantics
- `QField` / `Mergin Maps` for field validation workflow
