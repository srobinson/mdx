---
title: Indoor Navigation Technology for Visually Impaired Users (2025-2026)
type: research
tags: [accessibility, indoor-navigation, visually-impaired, BLE, UWB, LiDAR, YOLO, spatial-audio, ARKit, obstacle-detection]
summary: Comprehensive survey of indoor positioning, obstacle detection, navigation graph fusion, audio interfaces, and key projects (NavCog, GoodMaps, Clew, Seeing AI) for VI indoor navigation.
status: active
source: deep-research
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

Indoor navigation for visually impaired (VI) users in 2025-2026 sits at a convergence of maturing technologies: BLE beacon positioning delivers 2-5m accuracy at low cost, phone LiDAR enables real-time obstacle detection within 5m, on-device YOLO models achieve 30fps object detection on modern smartphones, and spatial audio has been validated as a lower-cognitive-load alternative to verbal turn-by-turn. The critical unsolved problem remains **fusing a pre-authored navigation graph with real-time camera perception** into a single coherent guidance system. No production system fully achieves this today. GoodMaps comes closest by matching real-time camera frames against a pre-scanned 3D model, but it does not perform real-time obstacle detection. NavGraph (CMU, 2025) demonstrates that parsimonious graph-based instructions reduce cognitive load by 30%, but explicitly lacks obstacle detection. The gap between "where am I on the graph" and "what is in front of me right now" remains the central engineering challenge.

---

## 1. Indoor Positioning Technologies for VI Users

### BLE Beacons

The dominant deployed technology for VI indoor navigation. NavCog (CMU) installs beacons every 15-30 feet and achieves unparalleled localization accuracy using a novel algorithm combining BLE with smartphone IMU. RightHear uses strategically placed beacons to trigger audio descriptions at key locations.

**Accuracy:** BLE alone delivers room-level (3-5m) accuracy. Combined with inertial sensors (PDR), BLE+inertial achieves 2-3m without calibration or fingerprinting. This is sufficient for corridor-level turn-by-turn guidance.

**Cost:** ~$20-50 per beacon. A typical building deployment (50 beacons across 5 floors) runs $12,500 in hardware plus $10,000 for site survey. Battery replacement every 2-5 years.

**Bluetooth 6.0 Channel Sounding** (emerging): Phase-based ranging theoretically enables centimeter-level precision. Limited device support as of early 2026.

### UWB (Ultra-Wideband)

**Accuracy:** 10-30cm theoretical, 0.5-1m practical with reasonable anchor density. Far superior to BLE for precision.

**Drawbacks:** High infrastructure cost, limited to premium phone models (iPhone 11+ has U1/U2 chip, Android adoption inconsistent). Market projected at $2B in 2025, growing at 18.9% CAGR.

**VI-specific research:** A 2024 MDPI study evaluated UWB-based positioning specifically for VI navigation and found it viable but noted deployment cost and anchor density requirements make it impractical for most accessibility-first deployments.

### WiFi RTT (802.11mc / 802.11az)

**Accuracy:** Sub-1m with compatible access points. One-sided RTT (Android 12+) achieves 3-5m with any AP.

**Limitations:** Requires compatible WiFi hardware. Only ~30% of Android devices support it. iOS does not expose WiFi RTT to third-party apps.

**802.11az** (Android 15+): Successor standard with improved security and accuracy. Chipsets shipping in 2025-2026.

### WiFi Fingerprinting

**Accuracy:** 5-15m typical, highly variable. Requires labor-intensive site surveys that degrade over time as AP configurations change.

**Assessment:** Largely superseded by BLE+inertial for new deployments. Still useful as a coarse fallback where WiFi infrastructure already exists.

### Visual-Inertial Odometry (VIO) / ARKit / ARCore

**Accuracy:** ARKit demonstrates the most stable and accurate VIO among off-the-shelf systems. Maintains sub-meter accuracy over short distances (within a room). In long corridors, progressive drift accumulates. One benchmark showed ARKit maintaining orthogonality and scale consistency with floor plans in U-shaped corridors.

**Drift:** The fundamental limitation. Errors accumulate proportionally to distance traveled and inversely to visual feature density. Featureless corridors (common in institutional buildings) cause rapid degradation.

**Mitigation:** Periodic correction via placed visual markers (NavGraph uses markers every 5m), BLE beacons, or WiFi RTT can reset drift. GoodMaps matches camera frames against a pre-built 3D model for continuous relocalization.

**VI-specific concern:** VIO requires the phone camera to see the environment. For VI users who naturally hold phones in pockets or at their sides, this is a significant UX constraint unless a chest mount or clip is used (NavGraph used a chest harness in its study).

### Inertial/PDR (Pedestrian Dead Reckoning)

**Accuracy:** Standalone PDR drifts rapidly. Combined with building floor plan constraints (particle filtering), UCSC's Manduchi group achieves indoor wayfinding without any beacons by enforcing that the navigator cannot walk through walls.

**Key advantage for VI:** Phone can be in pocket. No camera needed. Step counting + magnetometer + floor plan constraints provide coarse but infrastructure-free positioning.

### Technology Comparison Table (2025-2026)

| Technology | Accuracy | Infrastructure Cost | Phone Requirements | VI Suitability |
|---|---|---|---|---|
| BLE + Inertial | 2-5m | Low ($500-15K/building) | Any modern phone | High (phone in pocket OK) |
| UWB | 0.5-1m | High ($50K+/building) | Premium phones only | Medium (cost prohibitive) |
| WiFi RTT | <1m (compatible AP) | None (existing WiFi) | Android 9+ with support | Medium (limited device support) |
| VIO (ARKit/ARCore) | Sub-meter (short range) | None | Camera must see environment | Low-Medium (camera orientation constraint) |
| PDR + Floor Plan | 3-10m | None | Any phone with IMU | High (fully infrastructure-free) |
| GoodMaps (camera relocalization) | ~0.3m (sub-foot) | High (professional LiDAR scan) | iPhone with camera | High (if venue is mapped) |

---

## 2. Real-Time Obstacle Detection on Phones

### YOLO Variants for VI Obstacle Detection

Multiple specialized YOLO architectures have been published for VI obstacle detection:

**YOLO-OD** (Sensors, 2024): Modified YOLO architecture with a Feature Weighting Block for detecting differently-sized obstacles in navigation scenarios. Designed for outdoor environments but applicable indoors.

**YOLO-Extreme** (2025): Based on YOLOv12, designed for degraded visibility conditions (fog, low light). Extends detection reliability to conditions that standard models fail in.

**YOLOv8/YOLO11 on-device performance:**
- Samsung Galaxy S23 Ultra: YOLOv8 detection inference at 9.25ms per frame
- YOLOv8s and YOLO26s: 30fps on modern smartphones via CoreML/TFLite export
- YOLO11m: 22% fewer parameters than YOLOv8m with 1.3% higher mAP on COCO
- YOLO26 (2025): Up to 43% faster CPU inference, improved small-object detection

**Practical obstacle categories:** Stairs (up/down), doors (open/closed/handle type), chairs, tables, pillars, hanging obstacles, floor-level obstacles, people, carts.

### Cross-Modal Detection (Nature Communications, 2025)

A wearable device using cross-modal learning with Transformer-based feature fusion combines separate feature extraction networks for different sensor modalities. Uses cross-modal feature fusion and decision-making networks to explore inherent modal correlations. Designed for real-time obstacle avoidance rather than navigation.

### Apple Built-in Detection (iOS)

**Magnifier Detection Mode** combines camera + LiDAR + on-device ML:
- Door Detection: identifies doors, their state (open/closed), handle type, signs/symbols
- People Detection: distance to nearby people
- Point and Speak: reads text on physical objects when pointed at
- Furniture detection added in recent iOS updates

**RoomPlan API** (ARKit): Creates topological map classifying floors, walls, ceilings, windows, doors, seats. Outputs USD/USDZ with dimensions. Requires LiDAR-equipped device (iPhone Pro models).

**Assessment:** Apple's Detection Mode is the most polished on-device detection system for VI users. It combines LiDAR depth with ML classification and delivers results through VoiceOver. However, it operates as a scanning/exploration tool, not as continuous real-time navigation guidance.

### Phone LiDAR for VI (Section 6 answer)

**Super Lidar app:** Uses iPhone LiDAR + AI to parse 3D layout. Provides sonification (high pitch = far, low pitch = near) and haptic feedback for immediate obstacles. Range: up to 5m. Centimeter-level distance accuracy.

**Obstacle Detector app:** Uses LiDAR + TrueDepth camera. Measures distances to 5m with centimeter-level error.

**Seeing AI World Channel:** Uses LiDAR to place object labels in 3D space. Announces objects from their spatial position (spatial audio from the direction of the object).

**iPhone 17 Pro (2025):** Higher resolution LiDAR, improved accuracy, faster response times, works with A19 neural engine for real-time depth interpretation.

**Assessment:** Phone LiDAR is viable for obstacle detection within 5m. The 5m range is sufficient for indoor path clearance verification. However, LiDAR is only on Pro models, limiting the VI user base. The combination of LiDAR depth + YOLO classification is the strongest on-device approach for "what is in front of me and how far away is it."

---

## 3. Navigation Graph + Real-Time Perception Fusion

This is the central architectural question and the least solved problem in the field.

### Current Approaches

**GoodMaps (closest to production fusion):**
1. Professional LiDAR scan creates a 3D model of the venue (point cloud + 2D floorplan + 3D model)
2. At runtime, the phone camera captures frames continuously
3. Computer vision matches real-time camera input against the pre-built 3D model for positioning
4. Uses visually distinct surroundings (patterned carpets, ceiling panels, art) as natural landmarks
5. Achieves sub-foot accuracy positioning
6. Turn-by-turn audio guidance along pre-authored routes

**Limitation:** No real-time obstacle detection. The system assumes the environment matches the scan. A chair moved into a hallway after scanning would not be detected.

**NavGraph (CMU, 2025):**
1. Pre-authored navigation graph with nodes (turning points) and edges (walkable paths)
2. Navigation Areas define safe zones around edges with configurable width
3. VIO (ARKit) + visual markers every 5m for positioning
4. "Parsimonious Instructions" principle: minimize audio output
5. Four instruction types: arrived, walk, rotate, side-step
6. 30% fewer instructions than baseline, 62% reduction in time outside safe areas

**Critical gap explicitly acknowledged by authors:** "Both navigation apps lack a functionality to identify and avoid objects." The graph-based routing assumes a clear path.

**Graph SLAM for VI (MDPI, 2017):**
1. 3D time-of-flight camera on white cane
2. Two-step Graph SLAM: floor plane extraction (6-DOF) + wall line detection (3-DOF)
3. A* path planning on a floorplan graph
4. 0.901m endpoint error (1.69% of path length)
5. 95% POI announcement success rate

**Limitation:** Requires dedicated hardware (SR4000 depth camera on cane), not phone-based.

**Snap&Nav (MobileHCI 2024):**
1. Sighted assistant photographs a building floor map
2. Image analysis generates a node map (intersections, destinations, current position)
3. Scale estimation for distance information
4. Intersection detection tracks user position on the node map
5. IMU-only tracking (no beacons, no camera during navigation)
6. 12 blind participants navigated with increased confidence vs. cane-only

**Limitation:** Requires a sighted assistant for initial photo. Graph is derived from a 2D map photo, so accuracy depends on map quality.

**UCSC Manduchi Wayfinding (2024):**
1. Building floor plan as input (digital, not photo)
2. Path planning on the floor plan graph
3. IMU (accelerometer + gyroscope) for step counting and orientation
4. Particle filtering enforces physical constraints (no walking through walls)
5. Magnetometer detects magnetic anomalies as indoor landmarks
6. Phone can be in pocket (no camera needed during navigation)

### Fusion Architecture Gap Analysis

No existing system fully fuses these three capabilities simultaneously:

1. **Graph-based routing** (knows the building layout, planned path)
2. **Metric localization** (knows exactly where the user is on the graph)
3. **Real-time obstacle perception** (knows what is physically in front of the user right now)

The closest integration would combine:
- Pre-authored navigation graph (like EchoEcho's indoor_node/indoor_edge model) for route planning
- BLE + IMU for coarse localization on the graph (2-3m accuracy, phone in pocket)
- Phone camera + YOLO/LiDAR for obstacle detection and path clearance verification
- Camera-based relocalization (like GoodMaps) for drift correction when camera is available

This layered approach would allow the system to degrade gracefully: full guidance when camera is available, reduced (graph + IMU only) guidance when camera is pocketed.

---

## 4. Audio-First Navigation Interfaces

### Spatial Audio

**Microsoft Soundscape / VoiceVista:** Pioneered the spatial audio beacon approach. 3D audio cues emanate from the direction of the destination, allowing users to "follow the sound." Open-sourced in 2023 after Microsoft discontinued it. VoiceVista (community fork) continues active development.

**Seeing AI World Channel:** Objects announced from their spatial position via spatial audio (e.g., "chair" seems to come from where the chair actually is).

**Research findings (Frontiers in Neuroscience, 2025):** Binaural audio feedback leverages the auditory system's natural 3D localization ability. When performing cognitive tasks while navigating, spatial audio produced better performance on secondary cognitive tasks than verbal instructions.

**Assessment:** Spatial audio reduces cognitive load compared to verbal turn-by-turn instructions. Users "follow the sound" rather than interpreting left/right/distance commands. Most effective in simpler environments; complex spaces (shopping malls, transit hubs) still increase cognitive load.

### Verbal Turn-by-Turn

**NavCog3:** Synthesized speech for distance and direction, earcons for status changes, sonification for continuous orientation feedback.

**NavGraph:** Four instruction categories (arrived, walk, rotate, side-step) with "parsimonious" delivery. 30% fewer instructions than baseline with maintained navigation accuracy.

**Wayfindr Standard (ITU-T F.921):** Open standard for indoor audio wayfinding. Specifies instruction timing, content, and delivery. Approved by ITU as international standard.

### Haptic Feedback

**Systematic review findings (ACM TACCESS, 2025):**
- Vibration and kinesthetic feedback most effective for navigation cues
- Hands and fingers are the primary stimulation sites for navigation
- Rotational vibration patterns convey turns (clockwise = right, counterclockwise = left)
- Shape-changing devices (bending in the hand) outperform vibration-only for directional guidance

**NaviRadar:** Radar metaphor with tactile sweep. Users identified correct direction with mean deviation of 37 degrees across full 360 degrees.

**UCSC apps:** Smartwatch pairing provides vibration cues, freeing the phone for pocket-based IMU tracking.

### Clock-Face Directions

Referenced frequently in O&M (Orientation and Mobility) training literature as the standard verbal framework. "Door is at your 2 o'clock" maps direction to the 12-position clock face centered on the user's heading. Used by human sighted guides and some apps (Lazarillo, BlindSquare). The haptic literature reviewed did not identify specific clock-face haptic implementations, though the concept maps naturally to a circular vibration array.

### Cognitive Load Research

- Audio instructions increase working memory demands compared to haptic cues
- Navigation speed decreases when audio augmented reality messages are being processed
- Spatial audio (follow-the-sound) reduces cognitive load vs. verbal instructions
- Parsimonious instruction design (NavGraph) reduces instruction count by 30% without degrading accuracy
- Complex environments (malls, airports) increase disorientation regardless of interface modality
- The "Aerial Guide Dog" concept (PMC, 2024) explicitly targets low-cognitive-load design as its primary objective

---

## 5. Academic and Open-Source Projects

### NavCog (CMU / IBM Research)

**Status:** Research project, code available. NavCog3 published 2019.
**Architecture:** BLE beacons (15-30 ft intervals) + smartphone IMU. Novel localization algorithm. Speech + earcons + sonification output.
**Strengths:** Largest-scale blind indoor navigation study. Semantic feature callouts (doorways, shops).
**Limitations:** Requires dense beacon infrastructure. No active maintenance apparent.

### NavGraph (CMU / Smith-Kettlewell Eye Research, 2025)

**Status:** Active research. Published December 2025.
**Architecture:** ARKit VIO + visual markers every 5m. Pre-authored graph with navigation areas. Parsimonious instruction generation.
**Strengths:** 30% instruction reduction, 62% safety improvement. Rigorous study with 10 blind participants.
**Limitations:** No obstacle detection. Requires chest-mounted phone. Visual markers needed every 5m.

### Clew (Olin College OCCaM Lab)

**Status:** Active, free on iOS App Store.
**Architecture:** ARKit breadcrumb recording. Records a path, converts to keypoints, guides return via voice/sound/haptic.
**Use case:** Short-distance indoor retracing (find your seat, return to a table). Not full building navigation.
**Strengths:** Zero infrastructure. Works immediately.
**Limitations:** Path retracing only (no map, no routing). Drift in long distances. Requires initial sighted setup of paths.

### Seeing AI (Microsoft)

**Status:** Active, iOS App Store.
**Architecture:** Camera + LiDAR (on Pro models) + on-device ML. World Channel uses LiDAR for 3D spatial awareness. Indoor navigation feature uses ARKit + spatial audio for route following.
**Route creation:** User records a route (or receives a shared route). System provides spatial audio guidance to follow it.
**Strengths:** Mature, well-tested with VI community. LiDAR integration for 3D scene understanding.
**Limitations:** Route recording requires sighted assistance or prior knowledge. Not a full indoor navigation system.

### GoodMaps (American Printing House for the Blind)

**Status:** Active commercial product. Deployed at Nashville Airport (2025), Brownsville Airport (2026), DC Public Library, many others.
**Architecture:** Professional LiDAR scan (830nm laser, 360-degree capture) creates 3D model. Phone camera matches against model for sub-foot positioning. Turn-by-turn audio + haptic + tonal signals + braille display output.
**Strengths:** Sub-foot accuracy. No beacon infrastructure needed at runtime. Mature deployment pipeline.
**Limitations:** Requires professional scanning ($$$). Cannot detect dynamic obstacles. Camera must be active for positioning.

### Lazarillo

**Status:** Active, iOS and Android.
**Architecture:** Google Maps + OpenStreetMap + Foursquare + proprietary databases. BLE beacons for indoor. GPS for outdoor. Audio guidance.
**Strengths:** All-in-one indoor/outdoor solution. Broad venue coverage.
**Coverage:** Latin America focus, expanding globally.

### RightHear

**Status:** Active.
**Architecture:** BLE beacons + OpenStreetMap + proprietary data. Multilingual audio descriptions. Supports Wayfindr standard.
**Strengths:** Standards-compliant. Multilingual. Good for POI announcements.

### Wayfindr Standard

**Status:** ITU-approved standard (ITU-T F.921). Not a product but a specification.
**Scope:** Defines requirements for indoor audio wayfinding: instruction content, timing, delivery consistency.
**Impact:** GoodMaps, RightHear, and others reference Wayfindr for design decisions.

### VoiceVista (Soundscape Community Fork)

**Status:** Active, iOS App Store. MIT License.
**Architecture:** Fork of Microsoft Soundscape. 3D spatial audio beacons. Street/POI callouts. Apple Watch support.
**Strengths:** Open source. Active development. Spatial audio approach validated by years of Soundscape research.
**Limitations:** Outdoor/POI focus. Limited indoor capability.

### Navigine (Open Source Routing Library)

**Status:** Active on GitHub.
**Architecture:** Indoor routing algorithms for navigation graphs. BLE + WiFi positioning SDK.
**Relevance:** Provides the graph-routing layer that could underpin a VI navigation system. Not VI-specific but general indoor routing.

---

## 6. Phone LiDAR for VI (Dedicated Section)

### Hardware Capabilities

iPhone LiDAR (Pro models, iPhone 12 Pro through 17 Pro):
- dToF (direct Time of Flight) sensor
- Range: ~5m indoors
- Resolution: improved with each generation (iPhone 17 Pro highest)
- Operates at 830nm near-infrared
- Provides per-pixel depth map accessible via ARKit

### Existing VI Implementations

**Super Lidar:** 3D environment parsing with sonification. High pitch = far, low pitch = near. Haptic alert for immediate obstacles.

**Obstacle Detector:** LiDAR + TrueDepth camera. Distance measurement to 5m with centimeter accuracy.

**Seeing AI World Channel:** Spatial audio object placement using LiDAR depth.

**Apple Magnifier Detection Mode:** LiDAR + camera + ML for door/people/furniture detection.

### Path Clearance Verification

LiDAR depth maps can verify path clearance by:
1. Segmenting the ground plane from the depth point cloud
2. Identifying any objects protruding into the walking corridor
3. Estimating clearance width and height
4. Detecting floor-level hazards (steps, curbs, dropped objects)

No production app currently performs continuous real-time path clearance verification during navigation, but the sensor capability exists. The combination of LiDAR depth + YOLO object classification running concurrently is technically feasible on iPhone Pro models (A15+ neural engine handles both).

### Limitations

- Pro models only (significant cost barrier for VI users)
- 5m range limits lookahead
- Performance degrades in direct sunlight and with highly reflective surfaces
- Camera must be facing forward (conflicts with natural phone carrying positions)

---

## Sources Consulted

### Academic Papers
- NavGraph: Enhancing Blind Travelers' Navigation Experience and Safety (PMC, 2025) - https://pmc.ncbi.nlm.nih.gov/articles/PMC12682350/
- Real-Time Wayfinding Assistant for Blind and Low-Vision Users (arXiv, 2025) - https://arxiv.org/html/2504.20976v1
- Snap&Nav: Smartphone-based Indoor Navigation for Blind People (MobileHCI 2024) - https://dl.acm.org/doi/10.1145/3676522
- YOLO-OD: Obstacle Detection for VI Navigation (Sensors, 2024) - https://www.mdpi.com/1424-8220/24/23/7621
- Cross-modal wearable obstacle avoidance (Nature Communications, 2025) - https://www.nature.com/articles/s41467-025-58085-x
- Haptic Feedback for BLV: Systematic Review (ACM TACCESS, 2025) - https://arxiv.org/html/2412.19105v1
- Spatialized audio and mental representations (Frontiers in Neuroscience, 2025) - https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2025.1660373/full
- UWB for VI Indoor Positioning (MDPI Applied Sciences, 2024) - https://www.mdpi.com/2076-3417/14/13/5646
- Indoor Wayfinding via Geometric Features + Graph SLAM (IEEE/PMC, 2017) - https://pmc.ncbi.nlm.nih.gov/articles/PMC5659309/
- NavCog3 in the Wild (ACM TACCESS, 2019) - https://dl.acm.org/doi/10.1145/3340319
- WiFi and BLE Indoor Positioning Systematic Review (Sensors, 2025) - https://pmc.ncbi.nlm.nih.gov/articles/PMC12656469/
- Shape-changing haptic navigation (Scientific Reports, 2024) - https://www.nature.com/articles/s41598-024-79845-7

### Product / Project Pages
- GoodMaps: https://goodmaps.com/how-it-works/
- Clew (OCCaM Lab): https://github.com/occamLab/Clew
- VoiceVista: https://drwjf.github.io/vvt/index.html
- Soundscape Community: https://github.com/soundscape-community/soundscape
- Lazarillo: https://lazarillo.app/
- RightHear / Wayfindr: https://www.right-hear.com/wayfindr-standard-how-to-use-it-in-no-time/
- Navigine Indoor Routing Library: https://github.com/Navigine/Indoor-Routing-Library
- Apple RoomPlan: https://developer.apple.com/augmented-reality/roomplan/
- Apple Magnifier Detection Mode: https://support.apple.com/guide/iphone/detect-doors-around-you-iph35c335575/ios

### Industry / Technology Reviews
- Indoor Positioning Technology Review 2025 (Crowd Connected) - https://www.crowdconnected.com/blog/indoor-positioning-tech-update-2025/
- BLE vs UWB vs WiFi comparison (Seeed Studio, 2025) - https://www.seeedstudio.com/blog/2025/11/13/ble-vs-uwb-vs-gps-vs-wifi/
- WiFi RTT Android documentation - https://developer.android.com/develop/connectivity/wifi/wifi-rtt
- YOLO Evolution Overview (arXiv, 2025) - https://arxiv.org/html/2510.09653v2

### News / Press
- Nashville Airport GoodMaps launch (2025) - https://www.futuretravelexperience.com/2025/10/nashville-international-airport-launches-goodmaps/
- UCSC Wayfinding Apps (2024) - https://news.ucsc.edu/2024/10/manduchi-wayfinding-apps/
- Soundscape discontinuation / open-source release - https://techcrunch.com/2022/12/13/microsoft-sunsets-soundscape-3d-audio-app-but-will-open-source-the-code/

---

## Source Quality Assessment

**High confidence:** Technology accuracy numbers (BLE, UWB, WiFi RTT) are well-established across multiple independent sources. NavGraph and NavCog architectures are documented in peer-reviewed publications with user studies.

**Medium confidence:** GoodMaps' sub-foot accuracy claim is self-reported and repeated by partners but not independently benchmarked in peer-reviewed literature. YOLO on-device performance numbers come from Ultralytics documentation and product benchmarks, not independent VI-specific testing.

**Low confidence / gaps:** Reddit and HackerNews yielded essentially zero relevant discussions on VI indoor navigation. The VI user community appears to discuss these tools primarily on AppleVis (applevis.com) and specialized mailing lists rather than mainstream tech forums. Real-world user satisfaction data is sparse outside of controlled studies.

---

## Open Questions

1. **Dynamic obstacle integration:** No system fuses graph routing with real-time obstacle detection. When a chair blocks a pre-authored path, what happens? How should the system re-route vs. instruct the user to navigate around?

2. **Phone orientation for VI users:** VIO and camera-based systems require forward-facing camera. VI users naturally carry phones differently. What is the best mounting solution that VI users will actually adopt? Chest mount? Lanyard? Pocket with separate camera (glasses)?

3. **Wearable shift:** Envision Glasses, Ray-Ban Meta, and similar smart glasses solve the camera orientation problem but add cost and adoption friction. Is the glasses form factor the eventual answer?

4. **Infrastructure chicken-and-egg:** BLE beacons require building owners to install and maintain them. GoodMaps requires professional scanning. Who pays, and how do you achieve coverage beyond airports and libraries?

5. **Multi-floor transitions:** All reviewed systems handle single-floor navigation well. Elevator and stairwell transitions remain poorly addressed. How does positioning survive a floor change?

6. **Cognitive load ceiling:** Even with parsimonious instructions, navigating an unfamiliar building while processing audio guidance while using a cane/guide dog while maintaining spatial awareness imposes substantial cognitive demand. What is the practical upper limit on route complexity for audio-only guidance?

7. **Emergency/dynamic rerouting:** If a hallway is blocked (construction, emergency), how quickly can the system detect the change and reroute? No current system handles this.

---

## Actionable Takeaways for EchoEcho

1. **The indoor_node/indoor_edge graph model aligns well with the state of the art.** NavGraph, Navigine, GoodMaps, and IndoorAtlas all use similar node/edge representations. The addition of "navigation areas" (safe zones around edges with configurable width) from NavGraph is worth considering.

2. **BLE + IMU is the pragmatic positioning choice.** Achieves 2-3m accuracy without calibration, works with phone in pocket, lowest infrastructure cost. UWB and WiFi RTT are not yet viable for accessibility-first deployments.

3. **Obstacle detection should be a separate, optional layer.** No existing system has successfully integrated it into graph-based routing. Treating it as an independent alert system (phone camera + LiDAR when available) that operates alongside but independently of route guidance is the most realistic architecture.

4. **Spatial audio reduces cognitive load over verbal instructions.** VoiceVista's open-source implementation (MIT license) provides a proven spatial audio engine that could be integrated. The Soundscape codebase is available on GitHub.

5. **Wayfindr standard (ITU-T F.921) should inform instruction design.** It is the only internationally standardized specification for indoor audio wayfinding for VI users.

6. **GoodMaps' camera-against-3D-model approach is the accuracy gold standard** but requires professional venue scanning. A hybrid that uses GoodMaps-style relocalization where scans exist, falling back to BLE+IMU elsewhere, would provide the best coverage.

7. **Apple's Detection Mode APIs (door detection, people detection, Point and Speak) are ready to use** and could provide the "what's in front of me" layer without training custom models. They require LiDAR (Pro models only) but represent the lowest-effort path to obstacle awareness.

8. **YOLO26/YOLO11 running via CoreML at 30fps is viable** for custom obstacle detection on recent iPhones. This would enable detection of VI-relevant categories (stairs, doors, floor obstacles) that Apple's built-in detection does not specifically target.
