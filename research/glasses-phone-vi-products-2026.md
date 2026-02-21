---
title: Smart Glasses + Phone Apps for Visually Impaired Assistance - Product and Research Landscape
type: research
tags: [accessibility, smart-glasses, visually-impaired, indoor-navigation, assistive-technology, VI, blind]
summary: Comprehensive survey of shipping products and academic prototypes combining smart glasses with phone apps for VI assistance, covering technical architecture, pricing, user experience, and the unserved indoor navigation gap.
status: active
source: deep-research
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

The smart glasses market for visually impaired users has bifurcated into two tiers: affordable camera-equipped frames ($300-700) that offload processing to phones/cloud, and specialized assistive devices ($2,000-10,000) with dedicated sensors. Every shipping product excels at reading text and describing scenes on demand. None provides autonomous indoor navigation with spatial awareness. This is the killer gap: users can ask "what's in front of me?" but cannot get "turn left in 15 feet, then right at the elevator" inside an unfamiliar building. The gap persists because indoor navigation requires pre-mapped environments, real-time depth sensing, and sub-500ms feedback latency, a combination no current glasses hardware delivers.

## 1. Envision Glasses / Ally Solos

### Hardware Evolution

**Generation 1 (2020-2024):** Built on Google Glass Enterprise Edition 2. Qualcomm Snapdragon XR1 SoC. 8-hour battery. On-device OCR with cloud features for scene description. Priced at ~$3,500.

**Generation 2: Ally Solos (2025):** Partnership with Solos (AirGo V frame). Under 50g. HD cameras. Whisper open-ear audio. 15-hour battery with quick-swap stems. Multiple frame styles. Splash-resistant. Processing offloaded entirely to paired smartphone running the Ally app.

### AI Pipeline

Ally uses a multi-model routing architecture. A custom Envision reasoning model first classifies user intent, then dispatches to the best-fit AI provider (Llama, GPT-class, Gemini, or Perplexity-style retrieval). The "Ask Envision" feature uses GPT-4 (not GPT-5 as some sources claim) for document Q&A. Scene descriptions use cloud-based vision models. Text recognition (OCR) works offline on-device.

Key features: Instant Text, Scan Text, Batch Scan, Describe Scene (short/long), Face Recognition, Find Objects, Detect Colors/Light, Call an Ally (video call to sighted contact), Call Aira integration.

### Pricing

- Ally Solos: $399 launch / $599 after campaign / $699 retail
- Ally Pro subscription: $10/month or $100/year (unlocks unlimited conversations, custom "Allies," conversation history, shortcuts)
- First year of Ally Pro included with hardware purchase
- Free tier available after first year with reduced features
- Original Envision Glasses (GG EE2): ~$3,500

### Navigation Capabilities

None. The device offers basic orientation through object finding and light detection. Users pair with separate GPS navigation apps and white cane / guide dog. Video calling to sighted contacts provides human-mediated wayfinding on demand.

### User Community Assessment

AppleVis discussions show VI users comparing Envision favorably against Meta for dedicated accessibility features but noting the massive price gap (original at $3,500 vs. Meta at $300). The Ally Solos pricing ($399-$699) closes this gap significantly. Co-designed with VI users, elderly users, and caregivers.

## 2. Be My Eyes + Meta Ray-Ban

### Technical Architecture

The Ray-Ban Meta glasses are a four-part system:

1. **Glasses hardware:** 12MP ultra-wide camera, 5 microphones, open-ear speakers, microcontroller for wake word detection, SoC for local processing, specialized ML accelerators. 4-hour battery + 36-hour charging case.

2. **Smartphone intermediary:** Meta AI app handles connectivity to Meta servers, HDR processing, image stabilization, app integrations (Messenger, WhatsApp, Spotify, Be My Eyes).

3. **Cloud AI services:** Meta's Llama-based multimodal models provide conversational AI, scene description, real-time information retrieval.

4. **Performance optimization:** Predictive processing starts photo capture, OCR, and model loading in parallel with speech recognition before the user finishes speaking. On-device commands achieve sub-second response. Complex AI interactions average under 3 seconds.

### Be My Eyes Integration

"Hey Meta, Be My Eyes" initiates a live video call through the glasses' camera. A sighted volunteer sees the wearer's POV and provides real-time audio assistance through the open-ear speakers. This is human-mediated, not AI-powered. The user's hands remain free throughout.

Meta AI with Vision (separate from Be My Eyes) provides AI scene descriptions: "Hey Meta, look and describe what's in front of me." This uses Meta's multimodal AI, not GPT-4o. The distinction matters: Meta AI is Llama-based.

### Latency

- On-device operations (photo capture): sub-second
- AI scene description: under 3 seconds average
- Be My Eyes volunteer connection: variable (depends on volunteer availability, typically 30 seconds to 2 minutes)

### User Experience (VI Community)

**Positive (from AFB review, Tim Dixon blind review, AppleVis):**
- Affordable at $299-379
- Socially acceptable design (look like normal Ray-Bans)
- Prescription lens compatible
- Open-ear speakers allow environmental awareness while receiving audio feedback
- WhatsApp bot integrations (PiccyBot, NOA Chat) extend functionality
- Free Be My Eyes volunteer calls are transformative for hands-free sighted assistance
- Meta AI "look and read" works well for menus, signs

**Negative:**
- Navigation unreliable. Cannot provide safe directions for street crossings
- AI hallucinations: contradictory spatial descriptions (left vs. right errors)
- Camera positioned on left side causes right-frame cropping issues
- 4-hour battery life insufficient for all-day use
- Requires internet connectivity (fails in coverage dead zones like some supermarkets)
- "Live mode" (continuous description) still US-only beta
- No dedicated accessibility design; VI users adapt a consumer product

### NFB Assessment

The NFB conducted a week-long evaluation and found the glasses useful but emphasized they are "not a replacement for traditional mobility aids like canes or guide dogs." Meta offers significant potential for reading and description but not for safe navigation.

## 3. Aira

### Human + AI Hybrid Model

Aira connects blind users with trained Visual Interpreters (VIs) via live video call. The user streams camera feed from smartphone or smart glasses. The VI sees the environment and provides real-time verbal guidance.

**Navigation-specific training:** Visual Interpreters complete a dedicated navigation certification as the final piece of training. Newer VIs who have not completed navigation training are not routed navigation calls. This ensures quality for the highest-stakes use case.

**Indoor navigation approach:** Purely human-mediated. The VI describes the environment, reads signage, identifies landmarks, and provides directional guidance based on what they see through the camera. Requires stable camera at chest-level for best results. No pre-mapped environments. No navigation graph. Effectiveness depends entirely on VI skill and internet connectivity.

### Smart Glasses Options

- Historically offered Aira Horizon glasses (proprietary)
- Now integrates with Meta Ray-Ban glasses (Be My Eyes volunteer calls via Ray-Ban)
- Integration with Envision Glasses (Call Aira feature)
- Exploring direct Meta glasses partnership; hoping for developer SDK access in early 2026

### Pricing (2023 plans, current as of 2026)

**Silver tier:**
- 1-star: $26/month, 20 minutes, individual
- 2-stars: $50/month, 35 minutes, shareable with 1 additional member
- 3-stars: $84/month, 55 minutes, shareable with 1 additional member

**Gold tier:**
- 1-star: $132/month, 90 minutes, shareable with 3 members
- 2-stars: $200/month, 125 minutes, shareable with 3 members
- 3-stars: $356/month, 245 minutes, shareable with 3 members

**Platinum tier:**
- 1-star: $528/month, 330 minutes, shareable with 5 members
- 2-stars: $760/month, 550 minutes, shareable with 5 members
- 3-stars: $1,160/month, 880 minutes, shareable with 5 members

**Add-on minutes:** 25 min/$55, 50 min/$100, 100 min/$190

**Free access:** 3 welcome calls (unlimited duration) + 60 minutes after training session. Free at Aira Access partner locations (airports like MSP, HOU, ICT, YWG; retailers like Starbucks, Target, Wegmans; universities; transit systems). Rapidly expanding partner network through 2025-2026.

### Limitations

- Requires stable internet. Indoor connectivity (hospitals, schools, grocery stores) can be unreliable.
- Per-minute pricing makes continuous use prohibitively expensive for daily navigation.
- Human availability creates latency (connection time) and scalability constraints.
- No spatial memory across sessions; each call starts from scratch.

## 4. OrCam MyEye

### Hardware

Clips magnetically onto any existing glasses frame. Lightweight, compact form factor. 5-megapixel camera. Runs entirely on-device with no internet requirement. Braille-coded controls. Hand gesture and voice command interaction.

### Capabilities

- **Text reading:** Instant offline text-to-speech from any surface (books, menus, screens, mail, handwriting). Core strength. Works in 60+ languages. Translation in 140+ languages.
- **Face recognition:** Stores faces for later identification. Cannot detect emotions. Users report enrollment difficulty.
- **Product identification:** Barcode scanning, currency detection, color detection.
- **Orientation (beta):** Can identify everyday objects (cups, chairs, tables, screens, doors) between 6-30 feet. Does not provide directions or spatial relationships.

### What It Does NOT Do

Explicitly: "The device does not replace the white cane or any other assistive device that is used for navigation or obstacle detection." No turn-by-turn guidance. No maps. No indoor wayfinding. Users pair with separate navigation apps and mobility aids.

### Pricing

$3,689-$4,490 (promotional to retail). 30-day return policy. 2-year warranty. May qualify for VA benefits, state vocational rehabilitation funding.

### Architecture

Entirely on-device processing. No cloud dependency. Privacy-preserving by design. This is a deliberate trade-off: offline reliability and privacy at the cost of no LLM-powered conversational features.

## 5. Microsoft: Seeing AI and Project Tokyo

### Seeing AI (App)

Free app for iOS and Android. Uses Microsoft's computer vision, NLP, and ML. Features: short text, document reading, product identification, face recognition, currency detection, scene description, color identification, handwriting reading, light detection.

**2025 update:** Reorganized interface. Read screen combines Short Text and Document. Describe screen isolates Scene mode as a primary feature. Available on Android as of recent expansion.

Seeing AI is an app, not a glasses product. No wearable hardware. Phone camera only. No navigation capabilities.

### Project Tokyo (HoloLens Research)

Launched 2016 as a cross-lab partnership (US, UK, China, Japan, India). Built on modified HoloLens AR headset. Demonstrated blind navigation through complicated buildings: corridors, corners, stairs, arriving at correct rooms. Also explored helping blind children develop social interaction skills through spatial audio cues about nearby people.

**Current status (as of July 2024):** Still listed as active on Microsoft Research's Cambridge Lab pages. No publications since 2022. No productization timeline. No indication of discontinuation, but no forward momentum visible either. The project appears to have entered a quiet maintenance/research phase.

**Was it productized?** No. HoloLens itself was discontinued for consumers. Project Tokyo remains a research prototype. The navigation capabilities demonstrated in videos (corridor navigation, stair climbing, room finding) were never made available to VI users outside controlled lab settings.

### Microsoft Soundscape (Discontinued)

Spatial audio navigation app for blind users. Used 3D audio beacons placed at points of interest. Discontinued by Microsoft. Open-sourced under MIT license.

**VoiceVista** is the active community fork. Free iPhone app. Active development (latest update March 2025, GPX file import). Focuses on outdoor audio-based navigation. Does not address indoor navigation.

## 6. Academic Prototypes (2024-2026)

### VISA System (PMC 2025)
**Visual Impairment Spatial Awareness System.** Three-tiered architecture on NVIDIA Jetson Orin Nano + Intel RealSense D435 RGB-D camera, worn headlamp-style. YOLOv8s at ~36 FPS for object detection. ArUco marker-based indoor positioning with Dijkstra pathfinding. Depth-based obstacle avoidance with closure-rate calculations. TTS + STT interface.

**Results:** Blindfolded users oriented toward objects within 2-3 seconds. Maintained 10+ FPS. Successfully tested in real building (Siegel Hall).

**Limitation:** Requires pre-installed ArUco markers for navigation. Infrastructure-dependent.

### LLM-Glasses (arXiv, March 2025)
**GenAI-Driven Glasses with Haptic Feedback.** ESP32 CAM + YOLO-World object detection + GPT-4o reasoning + temple-mounted haptic actuators using five-bar linkage mechanism. Objects localized in 2x3 spatial grid. Haptic feedback uses taps (discrete events) and sliding motions (continuous guidance) leveraging the "hanger effect" for intuitive head direction.

**Results:** 81.3% haptic pattern recognition. Navigation accuracy: 91.8% (open), 84.6% (static obstacles), 81.5% (dynamic obstacles). Users stayed within tolerance 93-96% of the time.

**Limitation:** 1.25s pattern execution time limits responsiveness during rapid movement. Indoor testing only in 6x6m tracked space.

### EgoBlind (arXiv, March 2025)
**First egocentric VideoQA dataset for VI assistance.** 1,210 first-person videos captured by blind users. 4,927 questions across six categories: Information Reading, Safety Warning, Navigation, Social Communication, Tool Use, Other. Navigation questions are the hardest for all models (best models reach ~60% accuracy vs. 87.4% human performance). Demonstrates that current MLLMs are weakest at exactly the capability VI users need most.

### PathFinder (arXiv, April 2025)
**Map-less wayfinding using monocular depth estimation.** Smartphone-only (single camera). DFS algorithm on 15x15 patch-based depth representation. Three direction schemes: 3-direction, clock-hour (13 directions), degree-based (180 directions).

**Results:** 0.4s indoor response time (3-10x faster than AI alternatives). 73% of 15 blind/low-vision participants learned usage within one minute. 80% preferred DFS over AI approaches.

**Limitation:** Cannot provide destination-based routing. Only identifies short obstacle-free paths in immediate surroundings. Degrades in darkness, stairs, crowded environments.

### dotLumen (Romanian startup, CES 2024 & 2026)
**Self-driving navigation glasses.** Non-visual goggles with 6 cameras, AI computing safe walking paths 100 times per second, haptic feedback via forehead-mounted tactile arms. Vibrations indicate direction (center = clear ahead, sides = adjust course). CES Innovation Awards 2026 Honoree. CTA Foundation 2026 Pitch Competition winner. 300+ blind testers across 30 countries.

**Pricing:** Under EUR 10,000. Limited-series launch late 2024. US expansion 2025. Goal: 10,000 units by end of 2026.

**Limitation:** Bulky non-standard goggles form factor. Extremely expensive. No indoor map-based navigation.

### MDPI Electronics 2025 - Spatial Awareness Augmentation
IoT + AI platform integrating ultrasonic, LiDAR, and RFID sensors for 360-degree obstacle detection. Optimized Dijkstra algorithm for route calculation. Combines multiple sensing modalities for indoor localization. Research paper; no shipping product.

## 7. Emerging Competitors

### AGIGA EchoVision
$599 retail ($449 pre-order, no subscription for early adopters). 13MP wide-angle camera (50% wider FOV than Meta glasses, ~150 degrees). 6 hours battery (30-60 min with continuous AI). Designed by blind users for blind users. Scene description, OCR, Aira/Be My Eyes integration. Centered camera position (avoids Meta's left-side framing issues). Shipping late 2025.

### Apple Spatial Audio Navigation (Patent)
Apple holds a patent for spatial audio navigation providing indoor turn-by-turn guidance through AirPods or smart glasses. Uses binaural audio for directional cues. Not productized as of March 2026. The combination of AirPods + iPhone + Apple Maps indoor maps could theoretically deliver this, but Apple has not shipped it.

### ARxVision Headset
Integrates with Seeing AI and NaviLens apps. Text reading, object recognition, navigation assistance. Limited market presence.

## 8. User Experience Research: What VI Users Want

### Sources Consulted
AFB AccessWorld review, Tim Dixon (blind reviewer), AppleVis forums, NFB evaluations, PMC user studies (SVG study with 85 participants), PathFinder study (15 blind/low-vision participants in Bangladesh).

### What Works

1. **Hands-free operation** is the single most valued capability. Smart glasses free hands for cane, guide dog, or carrying items.
2. **Text reading** is the most-used feature (72.9% in SVG study rated it most valuable). Menus, signs, mail, medications.
3. **Social acceptability** matters. Meta Ray-Bans look normal. dotLumen goggles draw attention. Users want to be "indistinguishable from fully sighted people."
4. **Affordability** has shifted the landscape. Meta at $299 and Ally Solos at $399 make smart glasses accessible for the first time. Previous devices at $3,500-$4,500 were prohibitive for most.
5. **Open-ear audio** preferred over earbuds/headphones. Maintaining environmental awareness is a safety requirement, not a preference.
6. **Terse audio feedback** preferred: 5-7 words. Not verbose descriptions. Distance in meters, not relative terms like "close" or "far."

### What's Annoying

1. **AI hallucinations.** Contradictory spatial descriptions are dangerous, not just annoying. Left/right errors in a navigation context could lead to traffic.
2. **Battery life.** 4 hours (Meta) is not enough for a day. 15 hours (Ally Solos) is better. 6 hours (EchoVision) is marginal.
3. **Internet dependency.** Cloud-based AI fails in connectivity dead zones (underground, some buildings, rural areas). OrCam's offline-first approach addresses this at the cost of AI capability.
4. **Subscription fatigue.** Aira at $26-$1,160/month. Ally Pro at $10/month. Stacking subscriptions for different services adds up.
5. **Camera framing.** Left-mounted cameras (Meta) miss right-side content. Center-mounted (EchoVision) is better.
6. **Slow response for navigation.** 3-second AI response time is acceptable for reading but dangerous for walking. Obstacle avoidance needs sub-320ms (per NFB standard).

### What's Missing (The Killer Gap)

**Indoor spatial navigation.** Every product reviewed can answer "what do you see?" but none can answer "how do I get from here to Room 312?"

The specific unmet needs:

1. **Turn-by-turn indoor routing.** GPS fails indoors. No product integrates with indoor positioning (BLE beacons, UWB) to provide step-by-step directions inside buildings. Aira approximates this with human interpreters but at $2+/minute and with no spatial memory.

2. **Spatial mental model building.** Users want to understand the shape of a space, not just what's immediately visible. "You're in an L-shaped corridor. The elevator is around the corner to your left, 40 feet." No product provides this.

3. **Persistent spatial memory.** Each interaction starts from zero. No product remembers that the user has been to this building before and learned the layout. Aira VIs have no access to building maps or prior visit data.

4. **Obstacle avoidance at walking speed.** Smart glasses cameras lack depth sensing (except research prototypes with LiDAR/RealSense). AI-based scene description at 3-second latency cannot warn about obstacles in time. The NFB requires sub-320ms for collision avoidance. Only dotLumen (100 computations/second) and research prototypes with depth sensors meet this threshold.

5. **Seamless outdoor-to-indoor transition.** Users navigate to a building via GPS, then lose all guidance upon entering. No product handles the handoff from outdoor maps to indoor navigation.

6. **Pre-visit building familiarization.** Users want to explore a building's layout before visiting. "Show me the route from the entrance to the admissions office." No product offers this.

## 9. Product Comparison Matrix

| Product | Price | Weight | Battery | Processing | Navigation | Indoor Nav | Text Reading | Scene Description | Depth Sensing |
|---------|-------|--------|---------|------------|------------|------------|--------------|-------------------|---------------|
| Meta Ray-Ban | $299-379 | ~50g | 4h | Phone + Cloud | None | None | Good (AI) | Good (AI, 3s) | None |
| Envision Ally Solos | $399-699 + $10/mo | <50g | 15h | Phone + Cloud | None | None | Excellent | Good (AI) | None |
| OrCam MyEye 3 Pro | $3,689-4,490 | ~30g | ~4h | On-device | None | None | Excellent (offline) | Limited | None |
| AGIGA EchoVision | $449-599 | ~50g | 6h | Phone + Cloud | None | None | Good | Good | None |
| dotLumen | <EUR 10K | ~150g+ | ~4h est. | On-device | Obstacle avoid | None | None | None | 6 cameras + AI |
| Envision GG EE2 (legacy) | ~$3,500 | 46g | 8h | Hybrid | None | None | Excellent | Good | None |
| Aira (service) | $26-1160/mo | N/A | N/A | Human + phone | Human-guided | Human-guided | Human-guided | Human-guided | None |

## Sources Consulted

### Product Pages and Official Documentation
- [Envision Ally Solos Launch](https://www.letsenvision.com/blog/ally-solos-glasses)
- [Be My Eyes on Ray-Ban Meta](https://www.bemyeyes.com/be-my-eyes-smartglasses/)
- [Meta AI Glasses Accessibility](https://www.meta.com/ai-glasses/blind-visually-impaired/)
- [OrCam MyEye 3 Pro](https://www.orcam.com/en-us/orcam-myeye-3-pro)
- [Aira Pricing](https://aira.io/plans-and-prices/)
- [Aira Navigation Guide](https://aira.io/understanding-navigation-with-aira/)
- [AGIGA EchoVision](https://echovision.agiga.ai/)
- [dotLumen Glasses](https://www.dotlumen.com/glasses)
- [Seeing AI](https://www.seeingai.com/)
- [Project Tokyo - Microsoft Research](https://www.microsoft.com/en-us/research/project/project-tokyo/)
- [VoiceVista](https://drwjf.github.io/vvt/index.html)

### User Reviews and VI Community
- [AFB AccessWorld: Ray-Ban Meta Review (Fall 2025)](https://www.afb.org/aw/fall2025/meta-glasses-review)
- [Tim Dixon: Blind Meta Ray Ban Review 2025](https://www.timdixon.net/blog/2025/04/blind-meta-ray-ban-review-2025/)
- [AppleVis: Comparison of Smart Glasses for the Blind](https://www.applevis.com/forum/assistive-technology/comparison-all-new-smart-glasses-blind)
- [AppleVis: Envision vs Meta Glasses](https://www.applevis.com/forum/assistive-technology/envision-glasses-versus-or-addition-meta-glasses)
- [AppleVis: Big Flaw with Meta AI Glasses](https://www.applevis.com/forum/apple-hardware-compatible-accessories/big-flaw-meta-ai-glasses)
- [NFB Access Podcast: Echo Vision, Meta Glasses](https://nfb.org/resources/publications-and-media/access-podcast/echo-vision-smart-glasses-accessible-televisions)
- [OrCam vs Envision vs Ally Solos Comparison](https://floridareading.com/blogs/news/orcam-vs-envision-vs-ally-solos-an-in-depth-guide-to-wearable-assistive-technology)

### Academic Papers
- [VISA System - PMC 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11766877/)
- [LLM-Glasses - arXiv 2503.16475](https://arxiv.org/html/2503.16475)
- [EgoBlind - arXiv 2503.08221](https://arxiv.org/abs/2503.08221)
- [PathFinder - arXiv 2504.20976](https://arxiv.org/html/2504.20976v1)
- [AI-Powered Smart Vision Glasses - PMC 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12178407/)
- [Wearable Obstacle Avoidance - Nature Communications 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11933268/)
- [Meta Ray-Ban Edge AI Architecture - ZenML](https://www.zenml.io/llmops-database/edge-ai-architecture-for-wearable-smart-glasses-with-real-time-multimodal-processing)
- [Comprehensive Review of VI Navigation Systems - ScienceDirect 2024](https://www.sciencedirect.com/science/article/pii/S2405844024078563)
- [Indoor Navigation Review - Springer 2026](https://link.springer.com/chapter/10.1007/978-3-031-91550-5_18)

### Industry and News
- [Hable: Best Smart Glasses for VI 2026 Guide](https://www.iamhable.com/en-am/blogs/article/the-best-smart-glasses-for-visually-impaired-people-a-2025-guide)
- [Smart Glasses Find Purpose Among Blind Users - TechXplore Jan 2026](https://techxplore.com/news/2026-01-smart-glasses-purpose-users.html)
- [Apple Spatial Audio Navigation Patent - Patently Apple 2023](https://www.patentlyapple.com/2023/07/apple-wins-a-patent-for-spatial-audio-navigation-providing-an-indoor-turn-by-turn-like-system-for-users-wearing-airpods-sma.html)

## Source Quality Assessment

**High confidence:** Product specs, pricing, and feature lists are well-documented across multiple independent sources. Aira pricing confirmed from their official page. Meta architecture details from ZenML case study and official Meta documentation.

**Medium confidence:** User experience reports from AFB and AppleVis are credible but represent limited sample sizes. Academic prototype results are from controlled settings. dotLumen market timeline may slip (common for hardware startups).

**Lower confidence:** Project Tokyo status. No recent publications or updates since 2022 despite the research page remaining active. Microsoft may have deprioritized this without formal announcement. Envision's claim of GPT-5 integration appears to be GPT-4 based on support documentation.

**Gap:** AppleVis forum content was blocked (403) during this research. Reddit r/blind yielded no direct results for smart glasses discussions. The VI community conversation about these products is fragmented across AppleVis, NFB podcasts, and individual blind tech reviewers (Tim Dixon, Blind Abilities podcast) rather than centralized forums.

## Open Questions

1. **Meta developer SDK timing.** When will third-party apps get direct camera/sensor access on Meta glasses? Aira and others are waiting for this. Would enable custom VI navigation apps on affordable hardware.

2. **Apple smart glasses.** Apple holds spatial audio navigation patents and has indoor maps for many buildings. If/when Apple ships smart glasses with spatial audio wayfinding, it could leapfrog the entire market. No timeline visible.

3. **Ally Solos real-world performance.** Shipping October 2025. No independent reviews yet. The multi-model AI routing architecture is interesting but unproven at scale.

4. **dotLumen commercialization.** Can they deliver 10,000 units by end of 2026 at under EUR 10K? Hardware manufacturing at this scale with six cameras and haptic actuators is challenging.

5. **EgoBlind navigation gap.** Best MLLMs achieve only 60% accuracy on navigation questions (vs. 87% human). What architectural changes are needed to close this gap?

6. **Indoor positioning infrastructure.** Who deploys BLE beacons in buildings? Building owners have no incentive unless accessibility regulations require it. Apple's U1 chip and indoor maps cover some venues but coverage is spotty.

## Actionable Takeaways

1. **The indoor navigation gap is real and large.** Every product and research prototype confirms that autonomous indoor wayfinding for VI users is unsolved in production. The technology exists in pieces (BLE positioning, depth sensing, navigation graphs, spatial audio) but nobody has integrated them into a wearable system.

2. **Phone-as-hub architecture is dominant.** The winning pattern is lightweight glasses (camera + mic + speaker) tethered to phone for compute, with cloud AI for heavy inference. On-device processing is reserved for latency-critical operations (wake word, photo capture, basic OCR).

3. **Sub-$700 price point is the new bar.** Meta Ray-Ban ($299), Ally Solos ($399-699), and EchoVision ($449-599) have reset accessibility device pricing expectations. Anything above $1,000 faces adoption resistance.

4. **Haptic feedback is the research frontier for navigation.** LLM-Glasses and dotLumen both demonstrate that haptic directional cues can guide walking without occupying the audio channel. This preserves environmental awareness. The "hanger effect" (sliding patterns on temples inducing head turns) is a notable interaction pattern.

5. **The three-tier perception architecture maps to glasses:** YOLO-class detection (<50ms) for obstacle avoidance, on-device VLM (200ms-1s) for quick scene understanding, cloud VLM (1-3s) for detailed description. No shipping product implements all three tiers. This is the architectural blueprint for the next generation.

6. **User preference data is clear:** terse audio (5-7 words), distance in meters, hands-free operation, open-ear audio, socially acceptable form factor, offline fallback for text reading. Any product that violates these preferences will face adoption friction.
