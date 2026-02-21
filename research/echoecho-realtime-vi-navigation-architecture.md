---
title: "EchoEcho Real-Time VI Navigation: Architecture Proposal"
type: research
tags: [echoecho, vi-navigation, real-time, perception, vlm, indoor-mapping, accessibility]
summary: "Architecture for fusing EchoEcho's indoor navigation graph with real-time phone camera perception for visually impaired students"
status: active
project: echoecho
confidence: medium
created: 2026-03-13
updated: 2026-03-13
related: [dimos-analysis-echoecho-interior-mapping, interior-mapping-proposal, interior-domain-model]
---

# EchoEcho Real-Time VI Navigation Architecture

## The Question

Can DimOS-style perception tech run in real-time on a phone camera, giving visually impaired students immediate spatial awareness feedback while navigating indoor routes?

## Answer: Yes, With a Three-Tier Architecture

The key insight from cross-referencing all research threads: no single perception layer can serve all needs. The architecture requires three tiers operating at different speeds, each covering different aspects of spatial awareness.

## The Three Tiers

### Tier 1: Immediate Hazard Detection (< 50ms)

**What:** On-device YOLO object detection + iPhone LiDAR depth

**Covers:** Obstacles, doors, stairs, people, furniture, wet floors, construction barriers

**How it works:**
- YOLO11/YOLO26 runs at 17-30 FPS on modern phone NPUs via CoreML/ONNX
- iPhone Pro LiDAR provides centimeter-accurate depth within 5m at 60 FPS
- Combined: detect object class + measure exact distance
- Apple's built-in Magnifier Detection Mode already detects doors, people, furniture, signage

**Feedback:** Interrupt-driven audio/haptic alerts. "Obstacle 2 meters ahead." "Door on your left." Bone conduction or single earbud to keep environmental hearing open.

**DimOS parallel:** YOLOE detection with BoT-SORT tracking. The -s model variant is viable for phone NPUs. ObjectDB's persistence threshold (promote after N detections) prevents false alarm spam.

### Tier 2: Scene Context (200ms - 1s)

**What:** On-device small VLM (FastVLM-0.5B or SmolVLM-500M) on keyframes

**Covers:** Scene type recognition, signage reading, landmark identification, corridor vs room vs lobby classification

**How it works:**
- DimOS's adaptive keyframe selector (~1ms, pure pixel-diff) gates which frames go to VLM
- FastVLM-0.5B (Apple, optimized for iPhone) processes selected keyframes
- Provides context-aware descriptions: "elevator lobby with two elevators ahead", "T-intersection, hallway continues left and right"

**Feedback:** Contextual narration triggered by scene changes or user request. Not continuous. Parsimonious instruction design (NavGraph pattern: only announce at navigation area transitions).

**DimOS parallel:** The nav_vlm query pipeline. VLM returns structured scene descriptions. The CLIP-based spatial memory could index scenes for "have I been here before?" recognition.

### Tier 3: Rich Understanding (1-3s)

**What:** Cloud VLM (GPT-4o / Claude / Gemini Flash) on demand or at navigation decision points

**Covers:** Complex scene interpretation, reading detailed signage, answering user questions about the environment, route confirmation

**How it works:**
- Triggered at navigation decision points (intersections, floor changes, destination arrival)
- Or triggered by user voice command: "What's around me?" "Read that sign."
- SpotVLM-style context transfer: Tier 2 on-device VLM provides running context, cloud VLM enriches it
- Cost-effective at ~$0.10-0.40/hour with keyframe-only calls every 5-10 seconds

**Feedback:** Detailed verbal descriptions via on-device TTS (~100ms first chunk, mandatory for responsiveness).

**DimOS parallel:** The temporal entity graph pattern. Accumulate scene knowledge across the walk, enabling the cloud VLM to answer questions with context: "You passed the water fountain about 30 seconds ago, it's behind you to the right."

## The Fusion Layer: Nav Graph + Live Perception

This is the unsolved problem in the field. No production system fuses a pre-authored navigation graph with real-time obstacle detection. EchoEcho's `indoor_node` / `indoor_edge` model is positioned to be the first.

### How it works:

1. **Graph routing** provides the planned path (sequence of nodes and edges)
2. **BLE/IMU positioning** (2-3m accuracy) tracks the student's position along the graph
3. **Tier 1 detection** runs continuously as an independent alert layer
4. **Tier 2 VLM** confirms navigation landmarks at decision points ("you should see an elevator lobby ahead")
5. **Graph context enriches perception:** knowing the student is on edge E47 (a corridor) means "door on left" can be resolved to "Room 204 on your left" from the graph's destination data

### Navigation Areas (NavGraph pattern):

Define safe zones with configurable width around each indoor_edge. If Tier 1 detects an obstacle within the navigation area, alert. If outside the navigation area, ignore. This prevents alert fatigue from irrelevant detections (furniture in adjacent rooms visible through open doors).

### Positioning without screen:

VI users carry phones in pockets or on lanyards, which breaks camera-based VIO (ARKit). Recommended positioning stack:
- Primary: BLE beacons + IMU dead reckoning (2-3m accuracy, phone in pocket)
- Secondary: Camera relocalization against CLIP spatial memory when phone is raised
- Fallback: Step counting + compass along known graph edges

## What EchoEcho Would Need To Build

### Phase 1: Graph-Guided Audio Navigation (no camera)
- Indoor navigation graph (already planned)
- BLE beacon positioning (infrastructure per building)
- Turn-by-turn audio guidance with spatial audio cues
- Parsimonious instruction design (announce at transitions only)
- This alone is a shipping product

### Phase 2: Camera-Assisted Awareness (Tier 1 + Tier 3)
- On-device YOLO for obstacle/door/stair detection
- Cloud VLM on-demand for "what's around me?" queries
- Graph context enriches detections with location semantics
- iPhone Pro LiDAR for precise depth (with graceful degradation for non-Pro)

### Phase 3: Full Fusion (All Three Tiers)
- On-device small VLM for continuous scene context
- Temporal entity graph accumulating spatial knowledge during the walk
- CLIP spatial memory enabling "have I been here before?" recognition
- Adaptive keyframe selection gating cloud VLM calls
- Navigation area obstacle filtering

## Platform Recommendation

**Start with iPhone Pro.** LiDAR depth, CoreML optimization, FastVLM, built-in door detection via Magnifier. The VI assistive tech community already skews heavily iOS due to VoiceOver quality.

**Android support via Tier 1 + Tier 3 only.** YOLO runs on Android NPUs. Cloud VLM works on any platform. Skip on-device VLM on Android initially.

## Cost Model

| Component | Cost | Notes |
|-----------|------|-------|
| BLE beacons per building | $200-500 | 10-20 beacons, $10-25 each |
| Cloud VLM per navigation session | $0.05-0.20 | Keyframe calls every 10s, ~15 min session |
| On-device inference | $0 | Runs on phone hardware |
| Development | High | Novel fusion architecture |

## Source Research

- `~/.mdx/research/realtime-vlm-vi-navigation-2026.md`
- `~/.mdx/research/vi-indoor-navigation-tech-2026.md`
- `~/.mdx/research/realtime-perception-pipeline-mobile-feasibility-dimos.md`
- `~/.mdx/research/dimos-analysis-echoecho-interior-mapping.md`
