---
title: "EchoEcho VI Spatial Awareness Platform: DimOS Tech + Smart Glasses Synthesis"
type: research
tags: [echoecho, vi-navigation, smart-glasses, dimos, spatial-memory, real-time, perception, indoor-mapping, accessibility, routing, mapbox]
summary: "Unified synthesis combining DimOS robotics perception, smart glasses hardware, and real-time three-segment routing (outdoor Mapbox + entrance handoff + indoor graph) for VI campus navigation"
status: active
project: echoecho
confidence: medium
created: 2026-03-13
updated: 2026-03-13
related: [dimos-analysis-echoecho-interior-mapping, echoecho-realtime-vi-navigation-architecture, smart-glasses-vi-navigation-2026, glasses-phone-vi-products-2026, vi-indoor-navigation-tech-2026, realtime-vlm-vi-navigation-2026, realtime-perception-pipeline-mobile-feasibility-dimos, interior-mapping-proposal, interior-domain-model]
---

# EchoEcho VI Spatial Awareness Platform

## The Opportunity

Indoor spatial navigation for visually impaired users is completely unsolved in production. Ten research documents, five codebase deep-dives, and surveys of every shipping product in the space converge on the same conclusion: no product can answer "how do I get from here to Room 312?"

Every existing product does one thing well. Envision reads text. Be My Eyes describes scenes. GoodMaps positions you on a pre-scanned 3D model. NavGraph routes you along a navigation graph. Aira connects you to a human interpreter. None combines a pre-authored navigation graph with real-time perception from a wearable camera into a single coherent guidance system.

EchoEcho has the navigation graph. DimOS has the perception architecture. Smart glasses have the form factor. Mapbox has the outdoor routing. The synthesis defines a platform that could be the first to close this gap: real-time, any-location-to-any-room navigation combining outdoor walking directions with indoor graph routing, augmented by wearable spatial awareness.

## System Architecture

```
┌─────────────────────────────────┐
│         SMART GLASSES           │
│  (Ray-Ban Meta / Solos AirGo)  │
│                                 │
│  Camera: 720p/30fps ──────────────┐
│  Speakers: spatial audio ◄────────┤
│  IMU: head orientation ──────────┐│
│  Weight: 42-69g                  ││
│  Battery: 8-15hr                 ││
└─────────────────────────────────┘││
                                   ││
      BLE (video + audio)          ││
                                   ││
┌─────────────────────────────────┐││
│         PHONE (in pocket)       │││
│                                 │││
│  ┌───────────────────────────┐  │││
│  │ TIER 1: Hazard Detection  │◄─┘│
│  │ YOLOE-11s via CoreML      │   │
│  │ < 50ms per frame          │   │
│  │ Obstacles, doors, stairs  │   │
│  └────────────┬──────────────┘   │
│               │                  │
│  ┌────────────▼──────────────┐   │
│  │ TIER 2: Scene Context     │◄──┘
│  │ FastVLM-0.5B on-device    │
│  │ 200ms-1s on keyframes     │
│  │ "Elevator lobby ahead"    │
│  └────────────┬──────────────┘
│               │
│  ┌────────────▼──────────────┐
│  │ FRAME SELECTION PIPELINE  │
│  │ (from DimOS)              │
│  │                           │
│  │ sharpness_barrier  (~1ms) │
│  │ fps_sampling       (~0ms) │
│  │ adaptive_keyframes (~1ms) │
│  │ backpressure       (~0ms) │
│  └────────────┬──────────────┘
│               │ keyframes
│  ┌────────────▼──────────────┐    ┌──────────────────┐
│  │ TIER 3: Rich Understanding│───►│   CLOUD          │
│  │ At decision points or     │    │   GPT-4o / Gemini│
│  │ on voice command          │◄───│   1-2s response  │
│  │ "What's around me?"       │    │   $0.05-0.20/    │
│  └───────────────────────────┘    │   session        │
│                                   └──────────────────┘
│  ┌───────────────────────────┐
│  │ POSITIONING               │
│  │ BLE beacons + IMU (2-3m)  │
│  │ Phone in pocket OK        │
│  │ No camera needed          │
│  └────────────┬──────────────┘
│               │
│  ┌────────────▼──────────────┐
│  │ NAVIGATION ENGINE         │
│  │                           │
│  │ Indoor graph routing      │
│  │ (indoor_node/indoor_edge) │
│  │                           │
│  │ Navigation areas          │
│  │ (safe zones around edges) │
│  │                           │
│  │ Graph context enrichment  │
│  │ "Door" → "Room 312"      │
│  │                           │
│  │ Parsimonious instructions │
│  │ (announce at transitions) │
│  └────────────┬──────────────┘
│               │
│  ┌────────────▼──────────────┐
│  │ AUDIO OUTPUT              │
│  │                           │
│  │ On-device TTS (~100ms)    │
│  │ Spatial audio cues        │
│  │ Interrupt-driven alerts   │
│  │ 5-7 word instructions     │
│  └───────────────────────────┘
│
└─────────────────────────────────┘
```

## What DimOS Contributes (Technical Patterns)

Each DimOS subsystem maps to a specific layer of the platform. None requires robotics hardware. All have been validated in the DimOS codebase and adapted for mobile constraints.

### 1. Frame Selection Pipeline → Glasses Camera Gating

**DimOS source**: `dimos/perception/experimental/temporal_memory/clip_filter.py`, `dimos/msgs/sensor_msgs/Image.py`, `dimos/stream/video_operators.py`, `dimos/utils/reactive.py`

The glasses camera streams at 30fps. Processing every frame is wasteful and battery-draining. DimOS's frame pipeline solves this:

| Operator | Cost | Purpose |
|----------|------|---------|
| `sharpness_barrier` | ~1ms | Reject blurry frames (motion during walking). Laplacian variance computation. |
| `fps_sampling` | ~0ms | Reduce 30fps to 5fps for Tier 1 detection. Time-based gating. |
| `adaptive_keyframes` | ~1ms | Select 3-5 visually diverse frames per 5-second window for VLM analysis. Pure pixel-diff, despite the filename `clip_filter.py`. |
| `backpressure` (LatestBackPressureStrategy) | ~0ms | If YOLO is still processing, cache only the latest frame and discard the rest. Slow consumers never build up a queue. |

**Total gating cost: < 3ms.** This pipeline runs between the glasses camera stream and the perception tiers, ensuring expensive inference only runs on frames that matter.

### 2. YOLOE Detection → Tier 1 Hazard Alerts

**DimOS source**: `dimos/perception/detection/detectors/yoloe.py`, `dimos/perception/detection/objectDB.py`

YOLOE-11s (small variant) runs at 17-30 FPS on modern phone NPUs via CoreML/ONNX export. DimOS's detection pipeline provides:

- **BoT-SORT tracking** built into the detection call (~5ms overhead). Tracks object identity across frames so the same obstacle is not announced repeatedly.
- **ObjectDB two-tier persistence**: pending objects must be seen N times before promotion to permanent. Prevents false alarm spam from transient detections (shadows, reflections).

**Mobile adaptations needed** (from DimOS analysis):
- Reduce `min_detections_for_permanent` from 6 to 2-3 (walking user moves past objects faster)
- Increase `distance_threshold` from 0.2m to 0.5-1.0m (monocular depth is noisier than RGBD)
- Reduce `pending_ttl` from 5s to 2-3s

**Navigation area filtering** (from NavGraph research): define safe zones with configurable width around each `indoor_edge`. Tier 1 only alerts on objects within the navigation area. A chair visible through an open door in an adjacent room does not trigger an alert.

### 3. VLM Scene Analysis → Tier 2 + Tier 3 Understanding

**DimOS source**: `dimos/perception/detection/module3D.py` (nav_vlm), `dimos/models/vl/qwen.py`, `dimos/perception/experimental/temporal_memory/window_analyzer.py`

DimOS's nav_vlm pipeline is already cloud-based. Camera frame → base64 encode → cloud VLM API → structured JSON response. Total latency: 1-2.5s. This works with a phone camera (or glasses camera via phone) today.

The three-tier split:

**Tier 2 (on-device, 200ms-1s)**: FastVLM-0.5B (Apple, CVPR 2025) or SmolVLM-500M on keyframes selected by the DimOS adaptive keyframe filter. Provides scene classification: corridor, lobby, stairwell, elevator area. Fires only when the scene meaningfully changes.

**Tier 3 (cloud, 1-3s)**: Triggered at navigation decision points (the graph knows when the student approaches a node) or by voice command. Uses DimOS's structured prompt pattern: VLM returns JSON with entity labels and bounding boxes, not free-form text. The SpotVLM "context transfer" pattern (2025 paper) tolerates up to 9-second cloud delays by using Tier 2 as running context.

### 4. Temporal Entity Graph → Accumulated Scene Knowledge

**DimOS source**: `dimos/perception/experimental/temporal_memory/temporal_memory.py` (664 LOC), SQLite graph DB (entities, relations, distances)

DimOS processes video in 5-second windows, extracts entities and typed relations via VLM, stores in a SQLite graph. Rolling summaries every 30 seconds. Natural language queryable.

**EchoEcho application**: As the student walks a route, the system accumulates spatial knowledge:
- Entities: doors, signs, landmarks, hazards detected along the path
- Relations: "elevator is 3 meters past the water fountain", "Room 312 is the second door after the fire extinguisher"
- Queries: "Where was the restroom?" returns location relative to current position

This transforms the indoor navigation graph from a static structure into a living spatial model that gets richer with each walkthrough.

### 5. CLIP Spatial Memory → "Have I Been Here Before?"

**DimOS source**: `dimos/perception/spatial_perception.py` (594 LOC), ChromaDB with HNSW cosine similarity

DimOS stores CLIP image embeddings alongside spatial coordinates. Three query modes: by embedding, by text (CLIP text-to-image), by location.

**EchoEcho application**: As the student navigates, CLIP embeddings of scenes are indexed by position on the indoor graph. On subsequent visits:
- The system recognizes familiar locations and provides context: "You've been here before. The classroom is 20 meters ahead on the right."
- Text-based search: "Where did I see a vending machine?" returns the closest match from spatial memory.
- Cross-visit learning: landmarks discovered on one walkthrough enrich the graph for all future navigations.

**Mobile feasibility**: CLIP ViT-B/32 runs at ~30-50ms on phone NPU. ChromaDB is SQLite-backed; a lighter alternative (sqlite-vss, USearch) would be more appropriate for mobile. The 1-frame/second storage rate with distance gating is designed for continuous real-time operation.

### 6. Voronoi Gradient Costmap → Corridor-Aware Routing

**DimOS source**: `dimos/mapping/occupancy/gradient.py` (lines 84-202)

Standard shortest-path routing through an indoor graph has no awareness of corridor geometry. The Voronoi gradient assigns zero cost to corridor centerlines and increasing cost toward walls, naturally routing through the safest part of the corridor.

**EchoEcho application**: When the admin authors indoor edges, the Voronoi algorithm auto-generates centerline paths from wall boundary outlines. The resulting edges are pre-weighted with corridor-center preference. During navigation, the system guides the student along the center of corridors without explicit "stay in the middle" instructions.

### 7. Frontier Exploration → Graph Completeness Checker

**DimOS source**: `dimos/navigation/frontier_exploration/wavefront_frontier_goal_selector.py` (850 LOC)

BFS detects regions of unknown space adjacent to known space, groups them, scores by accessibility.

**EchoEcho application**: After admin authors the indoor graph, the completeness checker identifies: nodes with missing edges, unreachable destinations, floors without vertical connectors, dead-end corridors with no escape route. Displays a coverage heatmap in the web admin showing where the graph needs attention before field validation begins.

### 8. Delta Compression → Efficient Offline Sync

**DimOS source**: Protocol layer chunk-hash diffing for occupancy grids

**EchoEcho application**: The student app syncs the indoor navigation graph for offline use. When an edge or hazard changes, only the affected subgraph transfers. Particularly relevant for campus-wide deployment where buildings may update independently.

## What Smart Glasses Contribute (Hardware Platform)

### Primary Target: Ray-Ban Meta Gen 2 ($299)

| Spec | Value | Why It Matters |
|------|-------|----------------|
| Camera | 12MP, 720p/30fps streaming | Sufficient for YOLO + VLM inference |
| Audio | Open-ear spatial directional speakers | Navigation cues from the direction of the turn |
| Weight | 69g | Full school day wearable |
| Battery | 8 hours | Covers classes + between-class navigation |
| Form factor | Looks like normal Ray-Bans | Social acceptability (VI users care deeply) |
| Price | $299 | Fundable by university disability offices |
| SDK | Meta Wearables DAT (Kotlin/Swift) | Camera-to-phone streaming via BLE |
| Install base | 7M units sold | Students may already own them |

### The Glasses Solve Three Phone Problems

1. **Camera orientation**: Phone in pocket points at hip/floor. Glasses camera points where the student faces. Natural gaze direction without requiring the student to hold anything.

2. **Hands free**: Cane in one hand, door handle in the other, guide dog leash, carrying books. A phone camera requires a free hand and conscious aiming. Glasses are always on.

3. **Audio at the ear**: Bone conduction or open-ear speakers deliver spatial cues while preserving environmental hearing. No earbuds blocking traffic sounds or conversations. The spatial audio in Ray-Ban Meta can make "turn left" sound like it comes from the left.

### Abstraction Layer for Hardware Independence

```typescript
// Sensor abstraction - glasses are one implementation
interface SpatialSensor {
  streamFrames(): AsyncIterable<CameraFrame>
  getOrientation(): Quaternion  // head direction from glasses IMU
}

// Audio abstraction - glasses speakers are one implementation
interface AudioOutput {
  speakAlert(text: string, priority: 'immediate' | 'queue'): void
  playSpatialCue(bearing: number, distance: number): void
}

// Positioning abstraction - BLE beacons are one implementation
interface IndoorPositioner {
  getPosition(): GraphPosition  // node + edge + parametric distance
  getConfidence(): number
}

// Implementations per hardware
class RayBanMetaSensor implements SpatialSensor { /* DAT SDK wrapper */ }
class SolosAirGoSensor implements SpatialSensor { /* WiFi stream */ }
class PhoneCameraSensor implements SpatialSensor { /* fallback */ }

class GlassesSpeakerAudio implements AudioOutput { /* BLE audio */ }
class PhoneSpeakerAudio implements AudioOutput { /* fallback */ }

class BLEBeaconPositioner implements IndoorPositioner { /* BLE + IMU */ }
class IMUOnlyPositioner implements IndoorPositioner { /* dead reckoning fallback */ }
```

This abstraction means:
- Phase 1 ships with `PhoneCameraSensor` + `PhoneSpeakerAudio` (no glasses required)
- Phase 2 swaps in `RayBanMetaSensor` + `GlassesSpeakerAudio`
- Apple Smart Glasses (2027) or Android XR Glasses (2026) become new adapter implementations

## The Fusion Layer: What Nobody Else Has

The graph is the brain. The glasses are the eyes. The phone is the nervous system. The fusion between them is the product.

### How Graph Context Enriches Perception

Raw Tier 1 detection: "Door detected, 3 meters, bearing 330 degrees"

Graph-enriched output: "Room 312 on your left. That's your destination."

The enrichment pipeline:
1. BLE+IMU positions the student on edge E47 (a corridor on Level 2)
2. Tier 1 detects a door at bearing 330 relative to heading
3. The graph knows edge E47 has destination D12 (Room 312) attached at parametric distance 0.7
4. The student's current parametric position on E47 is 0.68
5. D12 is 0.02 * edge_length ahead, on the left
6. Output: "Room 312 on your left. That's your destination."

Without the graph, the glasses see a door. With the graph, they see Room 312.

### Navigation Areas (from NavGraph, CMU 2025)

Each `indoor_edge` has a configurable safe zone width. Tier 1 detection only alerts on objects within this zone:

```
    Wall                    Wall
    ████████████████████████████
    │                          │
    │   Navigation Area (2m)   │
    │   ┌──────────────────┐   │
    │   │  ← student path →│   │
    │   └──────────────────┘   │
    │                          │
    ████████████████████████████
    Wall                    Wall
```

Objects outside the navigation area (furniture in rooms visible through open doors, people in adjacent corridors) are filtered. This prevents alert fatigue, the primary usability complaint from VI users about obstacle detection systems.

### Parsimonious Instructions (from NavGraph)

Four instruction types only:
1. **Walk**: "Continue straight, 15 meters"
2. **Rotate**: "Turn left"
3. **Side-step**: "Step right 1 meter"
4. **Arrived**: "Room 312 is on your left"

Instructions fire only at navigation area transitions (entering a new edge, approaching a node). NavGraph demonstrated 30% fewer instructions with 62% improved safety compared to continuous guidance. Less audio = lower cognitive load = safer navigation.

### Positioning Without Requiring Screen

VI users carry phones in pockets. The positioning stack degrades gracefully:

| Method | Accuracy | Requirements | When Used |
|--------|----------|-------------|-----------|
| BLE + IMU | 2-3m | BLE beacons installed | Primary (phone in pocket) |
| Glasses IMU | Heading only | Glasses worn | Supplements BLE with head direction |
| Camera relocalization | Sub-meter | Phone camera active | Periodic correction (phone raised) |
| CLIP spatial memory | ~5m (scene match) | Prior visit data | "Have I been here before?" recognition |
| PDR + floor plan | 3-10m | Phone IMU only | Infrastructure-free fallback |

## Real-Time Routing: Anywhere to Any Room

### The Problem With Pre-Authored Routes

The original EchoEcho route model assumed: admin authors a route from Point A to Point B, volunteer validates it, admin publishes it, student follows it. This forces the student to first navigate to Point A, which is itself an unsolved navigation problem for a VI student sitting on a campus bench.

Real-time routing eliminates this dependency entirely. The student says **"Take me to Room 312 in Adams Hall"** from wherever they are.

### Three-Segment Route Architecture

```
Student's current location (GPS, anywhere on campus)
        │
        │  SEGMENT 1: OUTDOOR
        │  Mapbox Walking Directions API
        │  Real-time turn-by-turn on existing pedestrian paths
        │  GPS positioning (~3-5m accuracy)
        │  Phone in pocket, spatial audio guidance
        │
        ▼
Building Entrance (outdoor_indoor_connector)
        │
        │  SEGMENT 2: TRANSITION
        │  BLE beacons pick up in overlap zone (~5-10m from entrance)
        │  GPS → BLE positioning handoff
        │  "Entering Adams Hall through the south entrance"
        │
        ▼
Indoor Graph Entry Node
        │
        │  SEGMENT 3: INDOOR
        │  A* on indoor_node/indoor_edge graph
        │  BLE + IMU positioning (2-3m accuracy)
        │  Voronoi-weighted corridor centerline routing
        │  Parsimonious instructions at transitions
        │
        ▼
Room 312 (destination)
```

### Why This Works: The Division of Labor

Every college campus outdoors is already mapped. OSM, Google, and Mapbox have walking paths, sidewalks, building footprints, and pedestrian routing data for every US university. Universities themselves contribute GIS data, and OSM communities actively maintain campus detail.

EchoEcho does not need to map outdoors. It consumes existing infrastructure.

| Segment | Who Maps It | Who Routes It | Who Positions | EchoEcho Work |
|---------|------------|--------------|---------------|---------------|
| Outdoor | OSM / Google / Mapbox (already done) | Mapbox Directions API | GPS (phone in pocket) | API call only |
| Entrance zone | EchoEcho (`outdoor_indoor_connector`) | EchoEcho (entrance scoring) | GPS → BLE overlap | Connector entities + 1-2 BLE beacons |
| Indoor | EchoEcho (admin-authored graph) | EchoEcho (A* on graph) | BLE + IMU | The actual product work |

**EchoEcho's entire mapping burden is indoors. Outdoors is free infrastructure.**

### Outdoor Routing: Technical Details

**API**: Mapbox Directions API, `mapbox/walking` profile. Accepts up to 25 coordinates per request. Returns route geometry (polyline), step instructions, distance, and duration.

**Walking-specific parameters**:
- `walking_speed`: 0.14 to 6.94 m/s (default 1.42 m/s). Adjustable per student profile.
- `walkway_bias: 1`: strongly prefers dedicated sidewalks and footpaths over roads.

**React Native integration**: No official Mapbox Navigation SDK wrapper for React Native exists. The established pattern:
1. Call Mapbox Directions API as a REST request
2. Render route geometry as a polyline on @rnmapbox/maps
3. Track user location with Expo Location
4. Compare current position against route geometry for deviation detection
5. Re-call Directions API when >20m off-route for >3-5 seconds
6. Synthesize step instructions with Expo Speech for voice output

**Accessibility routing gap**: Neither Mapbox nor Google Directions API supports wheelchair routing, stair avoidance, or ramp preference. `walkway_bias` prefers pedestrian infrastructure but cannot distinguish accessible from inaccessible paths. For accessibility-specific outdoor routing, two options:
- **HERE Routing API v8**: documented `avoid[features]=stairs` and `pedestrian[type]=wheelchair` parameters. Most capable commercial accessibility routing API.
- **Pre-authored accessible outdoor routes**: for a bounded campus, manually author and cache the accessible paths. This sidesteps API limitations and is the most reliable approach.

For VI students (primary use case, not wheelchair), `walkway_bias: 1` on the walking profile is likely sufficient.

**Offline strategy**: Mapbox Directions API requires network. For offline-first:
- Pre-compute route cache at app startup or sync. For 20 buildings, 190 unique building pairs is a manageable pre-computation set.
- Store route geometry + step instructions in SQLite/MMKV.
- Serve cached routes offline; use live API for cache misses when online.
- @rnmapbox/maps supports offline tile packs for map rendering without network.

**Cost**: ~$0 at campus scale. Mapbox free tier covers ~100K requests/month. Google Routes API offers a $200/month credit covering ~40K requests. At ~500 route requests/day (~15K/month), both are free.

**Important validation step**: Check openstreetmap.org for the target campus to verify pedestrian path coverage. Paths not in OSM cannot be routed by Mapbox. Well-mapped campuses route correctly; incomplete campuses may need OSM contributions first.

### Route Computation Pipeline

```
1. Student: "Take me to Room 312 in Adams Hall"
   │
2. Resolve destination
   │  Look up "Room 312" in destinations table
   │  → building: Adams Hall
   │  → level: 3
   │  → attached_node: N47
   │
3. Select best entrance
   │  Query all outdoor_indoor_connectors for Adams Hall
   │  Score each by:
   │    - Walking distance from current GPS (via Mapbox, not Euclidean)
   │    - Accessibility match (student profile: needs ramp? elevator?)
   │    - Access hours (card-access? currently open?)
   │    - Floor proximity (entrance near elevator if destination is floor 3)
   │  → selected: South Entrance (connector C12, GPS: 30.2861, -97.7394)
   │
4. Compute outdoor segment
   │  Mapbox Directions API:
   │    origin: student GPS position
   │    destination: C12 GPS coordinates
   │    profile: walking
   │  → turn-by-turn outdoor route
   │
5. Compute indoor segment
   │  A* on indoor graph:
   │    origin: C12's attached indoor_node (N01, Level 1)
   │    destination: N47 (Level 3), via vertical_connector (elevator V2)
   │    weights: Voronoi corridor preference + accessibility + confidence
   │  → sequence of nodes and edges with instructions
   │
6. Concatenate and begin guidance
   │  Outdoor turn-by-turn (Mapbox) → "Entering Adams Hall" → Indoor turn-by-turn (graph)
```

### The GPS-to-BLE Handoff

The transition from outdoor GPS positioning to indoor BLE positioning is the trickiest physical moment. GPS accuracy degrades near buildings (multipath reflections off walls). BLE beacons are indoor-only.

**Solution: overlap zone.**

Place 1-2 BLE beacons at or immediately outside each building entrance. This creates a 5-10m zone where both GPS and BLE signals are available. The system monitors confidence from both:

```
         Outside              Overlap Zone            Inside
    ◄──────────────────►◄──────────────────►◄──────────────────►

    GPS: ████████████████████████▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░
    BLE: ░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓████████████████████████

    Position source:  GPS only  │ Blended  │   BLE + IMU only
                                │          │
                          outdoor_indoor_connector triggers here
```

When BLE confidence exceeds GPS confidence, the system switches positioning mode and announces: "Entering Adams Hall through the south entrance."

### Entrance Selection: Not All Entrances Are Equal

The `outdoor_indoor_connector` entity needs these attributes:

```
outdoor_indoor_connector:
  id: uuid
  building_id: references building
  indoor_node_id: references indoor_node  # where the indoor graph begins
  location: geometry(Point, 4326)          # GPS coordinate for outdoor routing
  name: "South Entrance"
  connector_type: main | side | service | emergency
  is_accessible: boolean                    # ramp, automatic door
  requires_card: boolean
  hours: jsonb                              # operating hours, null = always open
  floor_level: integer                      # which level the entrance is on
  notes: text                               # "Heavy manual door" or "Revolving door"
```

Entrance scoring function (pseudocode):

```
score(connector, student_profile, destination) =
    w1 * walking_distance(student_gps, connector.location)     # via Mapbox
  + w2 * accessibility_match(connector, student_profile)       # hard filter if needed
  + w3 * floor_proximity(connector.floor_level, destination.level)  # prefer same floor
  + w4 * hours_penalty(connector, current_time)                # closed = infinite
  + w5 * card_access_penalty(connector, student_has_card)
```

### Real-Time Recalculation

The student drifts off-route outdoors? Mapbox recalculates. Indoors, a wrong turn means recalculating A* from the nearest detected node. The system needs:

- **Outdoor rerouting**: Mapbox Directions API recalculation (sub-second response)
- **Indoor rerouting**: A* on the indoor graph from current BLE-detected position (milliseconds, graph is small)
- **Entrance re-evaluation**: If the student is closer to a different entrance after drifting, switch the target entrance and recompute both segments

### What Happens to Pre-Authored Routes

Pre-authored routes do not disappear. They become **curated experiences**:

- **Orientation day walkthrough**: "Follow the campus tour route"
- **Accessible-only paths**: pre-validated routes avoiding all stairs and heavy doors
- **Scenic or preferred paths**: routes chosen for landmark richness, safety, or social context
- **Emergency evacuation routes**: pre-authored with specific hazard and exit information

These are content, not infrastructure. The infrastructure is the indoor graph + entrance connectors + Mapbox. Any point on campus to any room in any building, computed on demand.

### Voice-First Interaction Model

The real-time routing model enables a fully voice-driven experience:

- **"Take me to Room 312"** → full three-segment route computed and guidance begins
- **"Find the nearest restroom"** → query destinations by type, route to closest
- **"How do I get to the library?"** → building-level destination, entrance auto-selected
- **"Where am I?"** → current position described relative to graph context
- **"What's nearby?"** → query destinations within radius on current floor
- **"Take me back to where I was"** → reverse route from spatial memory
- **"Is there an elevator nearby?"** → query vertical_connectors on current level

## Product Phases

### Phase 1: Real-Time Routing + Audio Navigation (no glasses, no camera)

**What ships**: Real-time three-segment routing (outdoor + transition + indoor), indoor navigation graph, BLE positioning, turn-by-turn audio, voice-first interaction
**Hardware**: Phone only (in pocket), BLE beacons in buildings
**DimOS tech used**: Voronoi centerline derivation, frontier completeness checker, delta sync
**Key integration**: Mapbox Directions API for outdoor segment, A* on indoor graph for indoor segment
**User experience**: Student says "Take me to Room 312." System computes the full route from current GPS position through the best building entrance to the destination. Spatial audio cues guide the student outdoors. Parsimonious instructions guide indoors. Landmarks announced as context.

**This is a shipping product by itself.** It addresses the killer gap (any-location to any-room routing) without requiring any camera or glasses hardware.

**Infrastructure per building**: 10-20 BLE beacons ($200-500) including 1-2 at entrances for overlap zone.

### Phase 2: Camera-Assisted Awareness (glasses as peripheral)

**What ships**: Phase 1 + real-time obstacle detection + on-demand scene description
**Hardware**: Phone + Ray-Ban Meta ($299) or Solos AirGo
**DimOS tech used**: Frame selection pipeline, YOLOE detection, ObjectDB persistence, nav_vlm cloud queries
**User experience**: Tier 1 alerts interrupt navigation when obstacles appear in the path. "Obstacle 2 meters ahead." Voice command triggers Tier 3: "What's around me?" Graph context enriches every detection. Works during both outdoor and indoor segments.

**Native module work**: Expo native modules wrapping Meta Wearables DAT for iOS (Swift) and Android (Kotlin). Camera frames received via `mwdat-camera` StreamSession. Audio output via standard BLE audio.

### Phase 3: Full Spatial Intelligence (temporal memory, CLIP recognition)

**What ships**: Phase 2 + on-device VLM + temporal entity graph + spatial memory
**Hardware**: Same as Phase 2
**DimOS tech used**: Temporal memory pipeline, CLIP spatial memory, window analyzer, entity graph
**User experience**: The system accumulates knowledge during the walk. "You passed the water fountain 30 seconds ago." Spatial memory persists across visits. "You've been to this building before. The elevator is ahead on the right." Pre-visit familiarization: explore the building's layout through spatial memory before physically visiting. Reverse routing: "Take me back to where I was."

### Phase 4: Multi-Campus Platform

**What ships**: Phase 3 + campus marketplace + crowd-sourced graph refinement
**Hardware**: Expanding glasses platform support (Apple, Android XR, MentraOS)
**User experience**: Students at different campuses contribute to indoor graph quality. Temporal memory from walkthroughs enriches graphs for all users. The platform effect: each new campus and each new walkthrough makes every navigation better.

## Cost Model

### Per-Building (Infrastructure)

| Item | Cost | Frequency |
|------|------|-----------|
| BLE beacons (10-20 per building) | $200-500 | One-time + battery every 2-5yr |
| Graph authoring (admin time) | ~4-8 hours per building | One-time + maintenance |
| Field validation (volunteer time) | ~2-4 hours per building | Per-revision |

### Per-Student (Hardware)

| Item | Cost | Funding Path |
|------|------|-------------|
| Phone (student's own) | $0 | Already owned |
| Ray-Ban Meta (Phase 2+) | $299 | University disability services, VR agencies, Lions Clubs |

### Per-Session (Cloud Services)

| Service | Cost | Notes |
|---------|------|-------|
| Mapbox Directions API | ~$0.001-0.005 per route | 100K free requests/month; ~$0.50/1K after |
| Phase 1 cloud total | ~$0.005 per session | Mapbox routing + reroutes only |
| Phase 2 (+ Tier 3 VLM on demand) | $0.05-0.20 per 15-min session | Keyframe calls every 10s |
| Phase 3 (+ temporal memory) | $0.20-0.50 per 15-min session | VLM calls every 5s on keyframes |

### University Deployment (20 VI students, 5 buildings)

| Item | Cost |
|------|------|
| BLE beacons (5 buildings) | $1,000-2,500 |
| Ray-Ban Meta (20 students) | $5,980 |
| Graph authoring (40 hours) | Internal staff time |
| Cloud inference (academic year) | ~$200-500 |
| **Total Year 1** | **~$8,000-9,000** |

Compare to: Aira at $26/month/student * 20 students * 9 months = $4,680/year with zero spatial memory, zero offline capability, and human availability constraints.

## Confidence Assessment

**High confidence**:
- The indoor navigation gap is real. Confirmed by every product survey, academic paper, and VI community source.
- Outdoor campus routing via Mapbox/Google Directions API is a solved problem. Campus walking paths are well-mapped in OSM.
- The three-segment route architecture (outdoor API + entrance handoff + indoor graph) is architecturally sound. Each segment uses proven technology.
- The `outdoor_indoor_connector` entity is the natural handoff point. It already exists in the EchoEcho domain model.
- DimOS's frame selection pipeline (sharpness + keyframe + backpressure) is directly portable. Pure numpy, no hardware dependency, < 3ms total.
- BLE + IMU positioning at 2-3m accuracy works for corridor-level guidance with phone in pocket.
- YOLOE-11s runs on phone NPUs. Well-documented Ultralytics export pipeline.
- Ray-Ban Meta has a shipping camera-to-phone streaming SDK.

**Medium confidence**:
- GPS-to-BLE handoff in the overlap zone. Conceptually sound, but real-world signal behavior near building entrances (GPS multipath, BLE range through walls/doors) needs field testing.
- Entrance scoring function weights. The accessibility, floor proximity, and distance factors need calibration with actual VI users on actual campuses.
- FastVLM-0.5B on-device performance. Apple demonstrated it but published no sustained FPS benchmarks for continuous camera processing.
- Temporal entity graph quality for accessibility-specific content. DimOS targets robotics entities; landmark/hazard detection for VI navigation needs evaluation.
- Meta DAT publishing timeline. "2026" is the only guidance. Could delay Phase 2.
- BLE beacon deployment logistics. Building owners need incentives or regulatory pressure.

**Low confidence / needs investigation**:
- Mapbox walking directions quality on specific campuses. Some campuses may have incomplete or inaccurate pedestrian path data in OSM. Needs per-campus validation.
- Indoor rerouting responsiveness. If BLE positioning is 2-3m and the student takes a wrong turn, how quickly does the system detect the deviation and recalculate?
- Battery impact of continuous YOLOE + VLM + BLE streaming on phone. No published data.
- Spatial audio effectiveness through Ray-Ban Meta speakers for navigation. Published research says bone conduction spatial audio is "not yet sufficient for practical navigation." Has open-ear improved this?
- CLIP spatial memory usefulness for cross-visit recognition in indoor environments. Academic concept, no production validation.
- Whether 720p/30fps over BLE from Ray-Ban Meta sustains under real-world BLE interference on a busy campus.

## What We Do Not Know

1. **Campus-specific OSM walking path quality.** Major universities are well-mapped, but smaller campuses or recently renovated areas may have gaps. Need to audit target campuses before committing to Mapbox-only outdoor routing.

2. **GPS-to-BLE transition reliability.** The overlap zone concept needs field testing at actual building entrances. Variables: building material (glass vs concrete), door type (recessed vs flush), weather, time of day.

3. **Real-world BLE latency for video frames from Meta glasses.** No published benchmarks. Could be the make-or-break for Tier 1 hazard detection at walking speed.

4. **Battery drain under full perception pipeline.** Phone running YOLO + BLE + GPS + VLM calls. Glasses streaming camera + audio. Could both survive a 4-hour class block?

5. **User acceptance of glasses for VI navigation.** VI users want glasses (hands-free, camera at gaze). But they also report sensitivity to looking different. Need user research with actual VI students on campus.

6. **Acoustic environment in corridors.** Open-ear glasses speakers may be drowned out by hallway noise between classes. Need to test spatial audio cue clarity in real campus buildings.

7. **Multi-floor positioning continuity.** Elevator and stairwell transitions disrupt both BLE and IMU. The vertical_connector model in the indoor graph helps logically, but physical positioning recovery after a floor change is an open problem.

8. **Mapbox Directions API cost at scale.** Need to model request volume: N students * M navigation sessions/day * rerouting frequency. Free tier may suffice for pilot; production pricing needs evaluation.

## Source Research Documents

This synthesis draws from eleven research documents produced by parallel investigation agents:

### DimOS Codebase Analysis (5 agents)
1. `~/.mdx/research/memory-architecture-dimos.md` - Spatial memory, temporal memory, time-series stores
2. `~/.mdx/research/mapping-navigation-architecture-dimos.md` - Occupancy grids, Voronoi costmaps, A* planning, frontier exploration
3. `~/.mdx/research/core-architecture-deep-dive-dimos.md` - Module system, reactive streams, blueprints, @skill decorator
4. `~/.mdx/research/perception-detection-architecture-dimos.md` - YOLOE, 3D detection, ReID, VLM integration, object tracking
5. `~/.mdx/research/protocol-middleware-web-visualization-dimos.md` - PubSub abstraction, Rerun bridge, web layer, delta compression

### Real-Time VI Navigation (5 agents)
6. `~/.mdx/research/realtime-vlm-vi-navigation-2026.md` - On-device VLM benchmarks, cloud latency, hybrid architectures, audio feedback
7. `~/.mdx/research/vi-indoor-navigation-tech-2026.md` - Indoor positioning, obstacle detection, nav graph fusion, academic projects
8. `~/.mdx/research/realtime-perception-pipeline-mobile-feasibility-dimos.md` - DimOS component latencies, mobile adaptation requirements
9. `~/.mdx/research/smart-glasses-vi-navigation-2026.md` - 12+ glasses platforms, SDKs, camera streaming, developer ecosystems
10. `~/.mdx/research/glasses-phone-vi-products-2026.md` - Envision, Be My Eyes, Aira, OrCam, academic prototypes, VI user research

### Routing & API (1 agent)
11. `~/.mdx/research/mapbox-googlemaps-walking-navigation-react-native-accessibility.md` - Mapbox/Google walking directions, React Native integration, accessibility routing gaps, offline strategy, cost
