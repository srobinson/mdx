---
title: Technology Landscape for VI Indoor Building Navigation
type: research
tags: [accessibility, indoor-navigation, visually-impaired, BLE-beacons, UWB, LiDAR, spatial-audio, wayfinding]
summary: Comprehensive technology stack analysis for building indoor navigation systems for visually impaired users, covering positioning tech, existing products, feedback mechanisms, map data requirements, standards, costs, and research landscape.
status: active
source: deep-research
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

Indoor navigation for visually impaired (VI) users requires a fundamentally different technology stack than sighted indoor wayfinding. The core challenge is achieving sub-meter positioning accuracy (ideally under 0.5m) while delivering information through audio and haptic channels that do not block environmental awareness. The market is converging on two dominant approaches: BLE beacon-based proximity systems (Lazarillo, RightHear, BlindSquare) that are mature but require physical infrastructure, and infrastructure-free visual positioning systems (GoodMaps) that use LiDAR-scanned 3D maps with camera-based localization. The open Wayfindr standard (ITU-T F.921) provides the only formal specification for audio-based VI wayfinding. Map data requirements for VI navigation are significantly more demanding than sighted navigation, requiring semantic annotation of doors, stairs, obstacles, tactile paths, and landmarks with approximately 820 documented accessibility features.

---

## 1. Indoor Positioning Technologies

### 1.1 Bluetooth Low Energy (BLE) Beacons

**The dominant deployment technology for VI indoor navigation today.**

| Parameter | Value |
|---|---|
| Accuracy | 1-3 meters (room-level) |
| Range per beacon | Up to 70-75 meters |
| Cost per unit | $3-30 (commodity: $10-15 bulk) |
| Battery life | 3-10 years depending on config |
| Key vendors | Kontakt.io, Estimote, Minew, BlueUp |

**Deployment density** varies by approach:
- **Proximity-based** (recommended for VI): Beacons placed at decision points only (doors, stairs, intersections, elevators). Fewer beacons needed. The Wayfindr standard recommends placing beacons 4 +/- 1 meters before key landmarks.
- **Trilateration-based**: Full area coverage requiring 3+ beacons within range at any point. Higher density, ongoing calibration needed.

**Configuration per Wayfindr standard:**
- Advertising interval: 300-350ms (balances signal stability and battery life)
- Mounting height: Above 2.5m to avoid body interference
- Keep 1m distance from metal, fluorescent lights, power conduits
- Corridors under 4m wide: center placement; over 4m: 4m intervals

**Strengths:** Low cost, mature ecosystem, works with any modern smartphone, extensive VI app support (BlindSquare, Lazarillo, RightHear all use BLE).
**Weaknesses:** 1-3m accuracy may be insufficient for precise door-finding. Requires physical installation and battery maintenance. Signal distortion from metal, water, human bodies.

**Estimote specifics:** Bluetooth 4.2 LE, CR2477 coin battery (1000mAh), temperature/light/motion sensors, NFC. Dev kit: $99 for 3 UWB beacons. Also offers UWB chips for inch-level positioning.

**Kontakt.io specifics:** Focused on healthcare RTLS. Wall/ceiling mounted beacons with easy installation (6 minutes per beacon claimed). Case study: 15,000 sq meters of Swiss hospital covered.

### 1.2 Ultra-Wideband (UWB)

| Parameter | Value |
|---|---|
| Accuracy | +/- 0.15m (95% CI) |
| Range | Up to 90m (low-data mode) |
| Cost per anchor | $50-150+ per anchor |
| Battery life | ~2 years sleep / 4000 min active |

UWB provides the highest accuracy of any radio-based positioning technology. A 2024 study confirmed sub-0.85m error for 95% of locations. Does not require line-of-sight between tags and sensors. The precision (15cm) exceeds VI navigation requirements.

**Limitation:** Infrastructure cost is significantly higher than BLE. Requires dedicated UWB anchors rather than commodity beacons. Consumer smartphone UWB support is growing (iPhone 11+, Samsung Galaxy S21+) but the ecosystem for indoor positioning remains immature compared to BLE.

**Verdict for VI:** Overkill for most wayfinding use cases. Consider for high-precision zones (e.g., guiding someone to a specific desk or kiosk) in hybrid deployments.

### 1.3 Wi-Fi RTT (Round Trip Time)

| Parameter | Value |
|---|---|
| Accuracy | 1-2m (optimized), raw ranging 0.2-0.8m |
| Infrastructure | Existing Wi-Fi access points (802.11mc) |
| Cost | Low (leverages existing infrastructure) |

Android supports Wi-Fi RTT natively (API level 28+). Requires 802.11mc-compatible access points and 3+ APs for trilateration. The advantage is zero additional hardware if the building already has compatible APs.

**Limitation:** iOS does not expose Wi-Fi RTT APIs. Android-only. Accuracy degrades in complex environments. Not suitable as a standalone solution for VI navigation.

### 1.4 Magnetic Field Mapping (IndoorAtlas)

| Parameter | Value |
|---|---|
| Accuracy | 0.3-1.0m (demonstrated in lab) |
| Infrastructure | None (uses smartphone magnetometer) |
| Cost | Mapping effort only; no hardware |

Every building creates unique magnetic field disturbances from steel structures, wiring, and equipment. IndoorAtlas (founded 2012, Oulu Finland / Mountain View CA) commercialized this approach. Requires a one-time fingerprinting survey of the building.

**Strengths:** Zero hardware infrastructure. Works with any smartphone.
**Weaknesses:** Requires extensive calibration walks. Accuracy degrades when building contents change (furniture, equipment). No VI-specific navigation system has been built on magnetic positioning alone. Best used as a supplementary signal fused with BLE or Wi-Fi.

### 1.5 LiDAR Scanning

**For map creation, not real-time positioning.**

| Method | Accuracy | Cost |
|---|---|---|
| iPhone/iPad Pro LiDAR | Few centimeters | $999-1099 (device cost) |
| Professional (Matterport Pro3) | Sub-centimeter | $5,995+ |
| GoodMaps backpack scanner | High fidelity, 360-degree | Service-based pricing |

iPhone/iPad LiDAR costs 1.5-3% of terrestrial laser scanners, making it viable for low-budget mapping projects. Matterport's Capture app supports iPhone LiDAR. The resulting 3D models can generate floor plans and spatial data for navigation.

GoodMaps uses a professional LiDAR backpack with 360-degree cameras, operated by trained technicians. The scan produces both the navigable map and the visual reference data used for camera-based localization by end users.

### 1.6 Computer Vision / ARKit / ARCore

**Emerging for VI, with significant caveats.**

Both ARKit (iOS) and ARCore (Android) provide Visual-Inertial Odometry (VIO), fusing camera and IMU data for 6-DOF tracking. GoodMaps uses camera-based localization to achieve 3-foot accuracy indoors without beacons.

**For VI users specifically:**
- ARKit powers the Clew app (open source, Olin College OCCaM Lab), which records paths using visual features and provides audio-guided backtracking. Works well for short distances indoors.
- ARCore's Depth API enables real-time obstacle detection with voice warnings.
- The UCSC team (Roberto Manduchi) uses smartphone inertial sensors (accelerometer, gyroscope) plus floor plans for infrastructure-free wayfinding, deliberately avoiding camera-in-face requirements.

**Critical UX constraint:** VI users should not need to hold a phone in front of them like a viewfinder. Manduchi's work and the Wayfindr standard both emphasize that the phone should remain in a pocket or at the side. Camera-based positioning that requires the phone camera to "see" the environment conflicts with this principle, though GoodMaps has worked around this with brief "look around" gestures.

### 1.7 Accuracy Requirements Summary

| Use Case | Required Accuracy |
|---|---|
| Building/wing identification | 5-20m |
| Room-level navigation | 1-3m |
| Door/entrance finding | Under 1m |
| Precise object locating | Under 0.5m |
| Obstacle avoidance | Real-time, under 0.4m |

Research consensus: 0.4m worst-case positioning error is adequate for turn-by-turn VI indoor navigation. Sub-meter accuracy is the practical threshold. BLE proximity (1-3m) works for corridor-level guidance but requires supplementary sensing (white cane, obstacle detection) for the final approach to specific features.

---

## 2. Existing VI Indoor Navigation Products

### 2.1 GoodMaps (Flagship, Infrastructure-Free)

- **Technology:** LiDAR-scanned 3D maps + camera-based visual positioning (no beacons required)
- **Accuracy:** "Down to the foot" (approximately 30cm)
- **Platform:** iOS and Android
- **Pricing:** Service-based; GoodMaps sends technicians with LiDAR backpacks to scan venues
- **University deployments:** Michigan State University (STEM building, Bessey Hall)
- **Other deployments:** Louisville Muhammad Ali International Airport, Portland International Airport, Eugene Airport
- **Key advantage:** No physical infrastructure to install or maintain
- **Key limitation:** Requires professional scanning service; camera-based positioning needs the user to briefly expose the phone camera

### 2.2 Lazarillo (BLE-Based, Free App)

- **Technology:** BLE beacon scanning for indoor; GPS + OpenStreetMap for outdoor
- **Platform:** iOS and Android (free)
- **University deployments:** Pontifical Catholic University of Chile (campus-wide, full indoor + outdoor mapping)
- **Approach:** Digital maps with beacon-triggered audio guidance
- **Strength:** All-in-one solution (indoor + outdoor); free to end users; organization pays for mapping + beacons

### 2.3 BlindSquare (BLE + GPS, Paid App)

- **Technology:** BPS (BlindSquare Beacon Positioning System), also supports Wayfindr standard, iBeacons, RightHear beacons, and Okeenea audio beacons
- **Platform:** iOS only ($39.99 one-time purchase)
- **Deployments:** Melbourne Zoo, various public buildings globally
- **Strength:** Most widely used accessible GPS app for blind users; works with multiple beacon ecosystems
- **Limitation:** iOS only; requires third-party navigation app for turn-by-turn directions outdoors

### 2.4 RightHear (BLE Beacon System)

- **Technology:** Proprietary Bluetooth beacons (sensors) with companion app
- **Platform:** iOS and Android
- **University deployments:** University of San Diego (5 beacons in engineering building), University of Alaska Anchorage (campus-wide)
- **Installation:** Sensors attach to walls with adhesive stickers; placement determined in consultation with RightHear
- **Approach:** Location-triggered audio descriptions rather than turn-by-turn navigation

### 2.5 NavCog / HULOP (Open Source, Research)

- **Technology:** BLE beacons + BLE fingerprinting (blelocpp library) + semantic map annotations
- **Institutions:** Carnegie Mellon University + IBM Research (Chieko Asakawa, Kris Kitani)
- **Open source:** HULOP (Human-scale Localization Platform) on GitHub, 26 repositories
- **Deployments:** CMU campus, five-story shopping mall (three buildings + underground area)
- **Strength:** Most academically rigorous system; open source; detailed semantic features (points of interest, surface changes, obstacles)
- **Limitation:** Last active development appears pre-2022; iOS-focused

### 2.6 Microsoft Soundscape (Discontinued, Open-Sourced)

- **Technology:** Spatial audio (3D soundscapes) using GPS + compass; outdoor only
- **Status:** Discontinued June-August 2023; code released as open source
- **Successors:**
  - **Soundscape Community** (by original co-founders, near-identical to original)
  - **VoiceVista** ("Soundscape Resurrection" in App Store)
  - **Soundscape by Scottish Tech Army** (launched August 31, 2023)
- **Relevance:** The spatial audio approach pioneered by Soundscape (3D audio beacons placed at real-world locations) is the gold standard for outdoor VI navigation and informs indoor audio design

### 2.7 Aira (Human + AI Assistance)

- **Technology:** Live video from smartphone camera streamed to human agents or AI visual interpreter
- **Platform:** iOS and Android
- **Recent development:** Partnership with Google DeepMind (Project Astra) announced at Google I/O 2025 for AI-powered visual interpretation
- **Indoor use:** Provides live assistance in hundreds of major venues
- **Strength:** Works anywhere without pre-mapping; handles ambiguous situations
- **Limitation:** Subscription cost; requires data connection; AI visual interpreter still in trusted tester phase

### 2.8 Clew (Open Source, ARKit)

- **Technology:** ARKit visual-inertial odometry for path recording and backtracking
- **Open source:** github.com/occamLab/Clew (Swift, Olin College)
- **Use case:** Record a path, retrace it later with audio guidance
- **Strength:** No infrastructure; free; open source
- **Limitation:** Short-distance only; iOS only; requires a sighted person to walk the path first (or the VI user on a first visit)

### 2.9 Mapxus (SDK Platform)

- **Technology:** Indoor mapping platform with accessibility mode
- **Deployment:** Hong Kong smart city proof of concept (2021+)
- **Features:** Audio-driven screen reader navigation, audio buttons for nearby locations, route summaries, turn-by-turn with distance and floor transitions
- **Approach:** SDK/platform rather than end-user app; organizations build on top of it

---

## 3. Audio and Haptic Feedback Mechanisms

### 3.1 Spatial Audio

The Microsoft Soundscape approach established the paradigm: 3D audio beacons placed at real-world locations, audible through headphones, that appear to come from the direction of the landmark. This creates "audio augmented reality" where users build mental maps from spatial sound cues.

**Implementation requirements:**
- Head-Related Transfer Functions (HRTFs) for accurate spatial rendering
- Compass/heading data from the smartphone for directional accuracy
- Bone conduction headphones are strongly recommended (see below)

### 3.2 Bone Conduction Headphones

**The consensus recommendation for VI navigation audio.**

Bone conduction headphones bypass the outer ear, allowing VI users to hear both navigation audio and environmental sounds simultaneously. This is a hard requirement for safe navigation: VI users rely on ambient sound (traffic, footsteps, doors) as primary environmental information.

The Wayfindr standard and virtually all VI navigation research emphasize keeping ears open. Standard earbuds or over-ear headphones are contraindicated.

Recommended devices: Shokz OpenRun (consumer), AfterShokz (now Shokz) various models. Research prototypes include custom bone conduction arrays for richer spatial audio.

### 3.3 Haptic Feedback

**Emerging, not yet mainstream in deployed products.**

- **NYU Tandon haptic belt (2024):** 10 precision vibration motors in a belt; NSF awarded $5M grant (Dec 2023). VR-tested with 72 participants; significantly reduced obstacle collisions.
- **MIT CSAIL ALVU system:** LiDAR + linear vibration motors array for obstacle detection; hands-free wearable.
- **Wrist vibrotactile devices:** 90.6% localization accuracy for vibration signals.
- **Elitac Mission Navigation Belt:** Commercial haptic navigation belt.

Haptic feedback is most effective as a **supplementary** channel alongside audio, particularly for obstacle warnings where audio alone may be too slow or ambiguous.

### 3.4 Screen Reader Integration

Apps must be fully VoiceOver (iOS) and TalkBack (Android) compatible. Key requirements:
- All UI elements need proper `accessibilityLabel` values
- Navigation instructions should be delivered through the system speech synthesizer or spatial audio, not requiring visual attention
- Test on real devices (simulators miss touch interaction and voice feedback timing)
- Support "screen off" navigation where the phone is in a pocket

React Native provides accessibility APIs (`accessible`, `accessibilityLabel`, `accessibilityHint`, `accessibilityRole`) that map to native VoiceOver/TalkBack properties.

---

## 4. Map Data Requirements for VI Navigation

### 4.1 What VI Navigation Requires Beyond Sighted Navigation

Research identifies approximately **820 documented indoor accessibility features** relevant to VI orientation and navigation. A survey of 25 blind experts ranked priorities:

| Feature | Priority Weighting |
|---|---|
| Room numbers / labels | 0.642 (highest) |
| Elevator locations | 0.083 |
| Stairs | 0.056 |
| Entrances / exits | High |
| Obstacles (permanent and temporary) | Critical |

**Critical semantic annotations for VI maps:**

- **Doors:** Location, type (push/pull/automatic/revolving), width, which side opens
- **Stairs:** Location, direction (up/down), number of steps, handrail presence/side
- **Elevators:** Location, button height, floor announcements
- **Floor surface changes:** Carpet to tile, tactile paving, ramps, thresholds
- **Overhead obstacles:** Signs, awnings, protruding objects above white-cane detection height (above ~1.2m)
- **Landmarks:** Distinctive features usable for orientation (water fountains, large pillars, reception desks)
- **Temporary hazards:** Wet floor signs, construction, moved furniture

### 4.2 How VI Map Data Differs from Sighted Navigation

| Dimension | Sighted Navigation | VI Navigation |
|---|---|---|
| Route visualization | Map display with highlighted path | Verbal turn-by-turn with distance counts |
| Obstacle handling | Visual avoidance | Must be pre-mapped or detected in real-time |
| Landmark types | Visual (signs, colors) | Tactile, auditory, olfactory (e.g., "near the coffee shop") |
| Level of detail | Room-level sufficient | Door-by-door, surface-by-surface |
| Dynamic obstacles | User sees and avoids | System must detect or pre-warn |
| Orientation | "You can see the elevator on the left" | "The elevator is 15 meters ahead on your left, past two doors" |

### 4.3 Data Formats

- **IMDF (Indoor Mapping Data Format):** Apple-developed, now OGC Community Standard. GeoJSON-based archive format. Comprehensive model for indoor locations. Lightweight, mobile-friendly. Royalty-free. The primary standard for Apple Maps indoor integration.
- **OpenIndoorMap / OpenStreetMap Indoor:** Community-driven. Less comprehensive but open.
- **GoodMaps proprietary:** LiDAR-derived 3D model with visual reference data.
- **NavCog/HULOP format:** Custom semantic map with edge-based routing graph.

---

## 5. Standards and Guidelines

### 5.1 Wayfindr Open Standard (ITU-T F.921)

The only formal international standard for audio-based indoor wayfinding for VI users. Published as ITU-T F.921 Recommendation 2.0. Covers:
- Environmental features to map
- Mobile application design for VI users
- BLE beacon placement and configuration
- Audio instruction design principles

### 5.2 W3C/WAI Cognitive Accessibility

The W3C COGA Task Force has published issue papers on technology-assisted indoor navigation and wayfinding, covering cognitive accessibility considerations alongside visual impairment.

### 5.3 WCAG 2.0/2.1 Level AA

Section 508 incorporates WCAG 2.0 Level AA. Any navigation app receiving federal funding or deployed in federal buildings must comply. Key requirements: text alternatives, keyboard/gesture operability, screen reader compatibility, sufficient contrast for low-vision users.

### 5.4 ADA and Physical Signage Standards

Physical wayfinding standards (ADA, SAD) cover reach ranges, tactile features, and mounting style of signs. Digital wayfinding must complement, not replace, physical accessibility infrastructure.

### 5.5 Gaps in Standards

No specific NFB (National Federation of the Blind) or ACB (American Council of the Blind) formal technical standards for indoor navigation apps were identified. The NFB has published evaluations of specific products (e.g., coverage of the Aira/Google partnership) and provides testing feedback, but has not issued a formal specification. The Wayfindr standard remains the primary reference.

---

## 6. Implementation Approaches

### 6.1 Survey-Based Mapping

**Traditional approach:** Surveyors walk the building with measuring tools, create floor plans, annotate features.
- Time: Days to weeks per building depending on size
- Accuracy: High for static features
- Cost: Labor-intensive
- Maintenance: Manual resurvey needed for changes

### 6.2 LiDAR Scanning

**GoodMaps approach:** Technicians with LiDAR backpack + 360-degree cameras.
- Time: Hours per building (scanning), days-weeks for processing
- Accuracy: Sub-centimeter for geometry
- Cost: Professional service; no public pricing (estimate: $5,000-20,000+ per venue based on comparable services)
- Maintenance: Rescan needed for major structural changes; minor changes can be updated digitally

**DIY with iPhone/iPad Pro LiDAR:**
- Time: Hours per floor
- Accuracy: Few centimeters (adequate for floor plans, not for visual positioning reference)
- Cost: Device cost only ($999-1099)
- Apps: Matterport Capture, Polycam, 3D Scanner App

### 6.3 Infrastructure-Free (Inertial + Floor Plan)

**UCSC/Manduchi approach:** Use building floor plans + smartphone IMU (accelerometer, gyroscope, step counter) for dead reckoning.
- Time: Minutes (import floor plan, define routes)
- Accuracy: Degrades with distance; needs periodic correction
- Cost: Minimal (software only)
- Maintenance: Update floor plan when layout changes
- Limitation: Drift accumulates; works best for pre-planned routes

### 6.4 Maintenance Burden

Indoor maps require frequent updates. MapsPeople's largest customers update floor plans up to 30 times per day. For VI navigation specifically:
- Room occupant/label changes: Weekly to monthly
- Furniture and temporary obstacle changes: Daily in active environments
- Structural changes: Rare (annual or less) but require resurvey
- Beacon battery replacement: Every 3-10 years depending on configuration

**If maps become outdated, users stop trusting the system.** This is especially critical for VI users who cannot visually verify discrepancies.

### 6.5 Cost Estimates for a Typical University Building

**Scenario: Single 50,000 sq ft (4,600 sq m) multi-story academic building**

| Component | Estimated Cost |
|---|---|
| **BLE Beacon Hardware** (proximity approach, ~50-100 beacons at decision points) | $500-3,000 |
| **BLE Beacon Hardware** (full trilateration, ~200-500 beacons) | $2,000-15,000 |
| **Professional LiDAR scanning** (GoodMaps or equivalent) | $5,000-20,000 (estimated) |
| **DIY LiDAR scanning** (iPad Pro + Matterport) | $1,099 (device) + labor |
| **Map annotation and semantic labeling** | 40-80 hours labor |
| **Navigation platform licensing** (Navigine, Mapxus, etc.) | $500-5,000/month |
| **Free platform** (NavCog/HULOP, Clew) | $0 (software) + labor |
| **Annual beacon maintenance** | $200-500 (battery replacement) |
| **Annual map updates** | 20-40 hours labor |

**Total first-year estimate (beacon-based):** $5,000-25,000
**Total first-year estimate (GoodMaps service):** $10,000-30,000+ (vendor pricing not public)
**Total first-year estimate (open-source + DIY):** $2,000-5,000 + significant developer time

---

## 7. Research and Academic Work

### 7.1 Key Research Groups

| Group | Institution | Focus |
|---|---|---|
| Chieko Asakawa / Kris Kitani | CMU + IBM Research | NavCog/HULOP, BLE localization, semantic navigation |
| Roberto Manduchi | UC Santa Cruz | Infrastructure-free wayfinding, inertial navigation, Clew Maps |
| James Coughlan | Smith-Kettlewell Eye Research Institute | NavGraph, orientation aids, NIDILRR-funded RERC |
| OCCaM Lab | Olin College | Clew app, ARKit-based path recording |
| VISA team | Illinois Institute of Technology | AR markers + neural networks for spatial awareness |
| NYU Tandon | NYU | Haptic belt navigation, VR testing ($5M NSF grant) |
| MIT CSAIL | MIT | ALVU wearable LiDAR + vibrotactile system |

### 7.2 Recent Breakthroughs (2024-2026)

- **Neural Radiance Fields (NeRF) + SLAM:** Photorealistic 3D scene understanding for richer path planning in cluttered indoor environments.
- **Vision Language Models (VLMs) for navigation:** PathFinder system uses VLMs and monocular depth estimation for map-less navigation with depth-first search on depth images.
- **AI Visual Interpretation:** Aira + Google DeepMind Project Astra partnership (2025) for continuous AI-powered visual scene description.
- **Smart cane evolution:** Modern smart canes now support SLAM, object recognition, and multimodal feedback (no longer simple obstacle detectors).
- **SightLine (Intel Global AI Award 2025):** Apple Depth Pro metric depth maps + YOLOv8 object detection on ESP32S3 smart glasses.

### 7.3 Government Funding

- **NIDILRR (National Institute on Disability, Independent Living, and Rehabilitation Research):** Primary US federal funder. Funds RERCs (Rehabilitation Engineering Research Centers) including Smith-Kettlewell's RERC on Blindness and Low Vision. NRTC received RRTC funding for 2025-2030.
- **NSF:** $5M grant to NYU Tandon for haptic assistive technology (December 2023).
- **NIH:** Funded UCSC wayfinding app development.
- **ACL SBIR:** Small business innovation grants for assistive technology.
- **Grants.gov:** Search "NIDILRR" or program number 93.433 for current opportunities.

---

## 8. Actionable Recommendations for University Campus VI Navigation

### 8.1 Recommended Technology Stack

**For a new project targeting university campuses:**

1. **Positioning: Hybrid BLE + Camera-based**
   - Deploy BLE beacons at decision points (proximity approach, not trilateration)
   - Use smartphone camera for localization where beacons are sparse
   - Fall back to IMU dead reckoning between beacons

2. **Mapping: LiDAR scan + manual semantic annotation**
   - Scan with iPad Pro LiDAR (Polycam or Matterport) for geometry
   - Manually annotate accessibility features using IMDF or custom schema
   - Consider GoodMaps service for flagship buildings, DIY for the rest

3. **Audio output: Spatial audio through bone conduction headphones**
   - Follow Wayfindr standard for audio instruction design
   - Support standard screen readers (VoiceOver/TalkBack) as fallback
   - Implement "screen off" navigation mode

4. **Data format: IMDF (GeoJSON-based)**
   - OGC standard, Apple Maps compatible
   - Extensible for custom accessibility annotations

### 8.2 Start Small

The GoodMaps Connect documentation warns about the "ups and downs of small-scale pilots." Begin with one high-traffic building (student union, main library) before scaling campus-wide. This constrains initial investment and surfaces integration issues early.

### 8.3 Engage VI Users Early

The NIDILRR study on user preferences found that VI users prioritize: (1) what types of buildings to map first, (2) what information to receive, and (3) output modality preferences. These preferences vary significantly between individuals. Co-design with actual VI users from the target campus population.

### 8.4 Consider Existing Platforms Before Building Custom

If budget allows, GoodMaps offers the lowest-maintenance path (no beacons to maintain) with proven university deployments. If budget is constrained, NavCog/HULOP is open source and academically validated but requires developer investment to deploy and maintain.

---

## Sources Consulted

### Academic Papers
- [UWB-Based Indoor Positioning for VI Navigation](https://www.mdpi.com/2076-3417/14/13/5646) - MDPI Applied Sciences, 2024
- [Indoor Navigation Systems for VI: Mapping Features to User Needs](https://pmc.ncbi.nlm.nih.gov/articles/PMC7038337/) - PMC, 2020
- [NavCog3 in the Wild: Large-scale Blind Indoor Navigation](https://dl.acm.org/doi/10.1145/3340319) - ACM TACCESS
- [Turn-by-Turn Indoor Navigation for the VI](https://arxiv.org/html/2410.19954v1) - arXiv, October 2024
- [VISA System for Indoor Navigation and Daily Activities](https://pmc.ncbi.nlm.nih.gov/articles/PMC11766877/) - MDPI J. Imaging, 2025
- [Navigation Assistance Via Haptic Technology: Scoping Review](https://journals.sagepub.com/doi/10.1177/10711813251360706) - SAGE, 2025
- [iPhone LiDAR vs Terrestrial Laser Scanner Accuracy](https://www.tandfonline.com/doi/full/10.1080/16874048.2024.2408839) - Taylor & Francis, 2024
- [Wi-Fi RTT Ranging for Personal Mobility](https://pmc.ncbi.nlm.nih.gov/articles/PMC10007519/) - PMC Sensors, 2023

### Products and Platforms
- [GoodMaps](https://goodmaps.com/) - LiDAR-based indoor navigation
- [Lazarillo](https://lazarillo.app/) - BLE-based accessible GPS
- [BlindSquare](https://www.blindsquare.com/) - Accessible GPS with beacon support
- [RightHear](https://www.right-hear.com/) - BLE beacon orientation system
- [Mapxus Accessibility](https://www.mapxus.com/accessibility) - Indoor mapping SDK with VI support
- [Navigine Accessible Navigation Guide](https://navigine.com/blog/accessible-indoor-navigation-the-2026-guide-to-compliance-and-universal-design/)
- [Aira AI Visual Interpreter](https://aira.io/projectastra/) - Google DeepMind partnership

### Open Source
- [HULOP / NavCog](https://github.com/hulop) - CMU/IBM open platform (26 repos)
- [Clew](https://github.com/occamLab/Clew) - ARKit path recording app
- [Microsoft Soundscape](https://github.com/microsoft/soundscape) - Open-sourced spatial audio navigation
- [SightLine](https://github.com/JoshuaChil/SightLine) - AI smart glasses (Intel Award 2025)

### Standards
- [Wayfindr Open Standard (ITU-T F.921)](https://www.wayfindr.net/open-standard) - Audio wayfinding for VI
- [Wayfindr BLE Beacon Guidelines](https://www.wayfindr.net/open-standard/wayfinding-technologies/bluetooth-low-energy-beacons)
- [IMDF (Indoor Mapping Data Format)](https://www.ogc.org/standards/indoor-mapping-data-format/) - OGC Standard
- [W3C Accessible Maps](https://www.w3.org/WAI/RD/wiki/Accessible_Maps)

### University Deployments
- [Michigan State University + GoodMaps](https://www.rcpd.msu.edu/news/ability-blog/msu-improves-campus-accessibility-through-introducing-goodmaps)
- [University of San Diego + RightHear](https://www.sandiego.edu/news/detail.php?_focus=94163)
- [University of Alaska Anchorage + RightHear](https://canasstech.com/pages/indoor-navigation-beacons-from-right-hear)
- [Pontifical Catholic University of Chile + Lazarillo](https://lazarillo.app/ourprojects/)

### Government and Funding
- [ACL Improving Indoor Navigation](https://acl.gov/ada/improving-indoor-navigation)
- [Smith-Kettlewell RERC](https://www.ski.org/center/rehabilitation-engineering-research-center/)
- [NIDILRR RRTC Funding 2025-2030](https://www.blind.msstate.edu/news/2025/09/nrtc-receives-nidilrr-rrtc-funding-2025-2030)
- [UCSC Wayfinding Apps (NIH funded)](https://news.ucsc.edu/2024/10/manduchi-wayfinding-apps/)
- [NYU Tandon Haptic Belt ($5M NSF)](https://engineering.nyu.edu/news/new-virtual-reality-tested-system-shows-promise-aiding-navigation-people-blindness-or-low)

---

## Source Quality Assessment

**High confidence:** Technology specifications (BLE accuracy, UWB accuracy, LiDAR capabilities) are well-documented across multiple peer-reviewed sources. Product features are verified from vendor sites and independent reviews.

**Medium confidence:** Cost estimates for deployment are extrapolated from component pricing and comparable projects. No vendor publicly discloses full deployment pricing for VI-specific installations. The "50-100 beacons per building" estimate for proximity-based deployment is derived from Wayfindr guidelines and case studies, not from a controlled study.

**Low confidence:** The GoodMaps service pricing estimate ($5,000-20,000+) is speculative, based on professional LiDAR scanning service market rates. Contact GoodMaps directly for actual pricing.

**Reddit/HN gap:** Reddit searches for VI indoor navigation topics returned no results. HackerNews had no relevant threads. The VI accessibility community appears to concentrate on AppleVis forums, dedicated mailing lists, and vendor-specific channels rather than general tech forums.

---

## Open Questions

1. **GoodMaps pricing:** No public pricing available. Essential to contact sales for university-specific quotes.
2. **BLE vs. camera-based: long-term winner?** GoodMaps' infrastructure-free approach is compelling but depends on a single vendor. BLE is vendor-neutral but maintenance-heavy.
3. **AI visual interpretation timeline:** When will Aira/Google's AI interpreter move beyond trusted tester? Could this make pre-mapping obsolete for some use cases?
4. **Temporary obstacle handling:** No system solves dynamic obstacle detection well. This remains the hardest unsolved problem.
5. **Multi-building campus scale:** No published case study covers a full large university campus (50+ buildings). Lazarillo at PUC Chile is the closest but details are limited.
6. **Hybrid positioning fusion:** How to optimally combine BLE, IMU, camera, and magnetic signals for VI-grade accuracy remains an active research question.
