---
title: Visually Impaired Navigation Technology Landscape — EchoEcho Navigator Evaluation
type: research
tags: [accessibility, navigation, blind, visually-impaired, haptic, indoor-navigation, AI, campus, IMU, dead-reckoning]
summary: Comprehensive landscape of VI navigation apps, indoor positioning accuracy without beacons, haptic research, AI/LLM nav, campus pilots, and competitor funding — evaluated against EchoEcho Navigator pitch claims.
status: active
source: deep-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

The visually impaired (VI) navigation technology space is active but genuinely unsolved at the indoor/campus level. The dominant apps (BlindSquare, Aira, GoodMaps) either require expensive infrastructure or human interpreters. Phone-only dead reckoning via accelerometer and gyroscope yields 1-5 meter errors that accumulate rapidly, making corridor-level turn guidance unreliable without correction anchors. Haptic vibration research confirms vibration is an effective modality, but the specific "pulse count = direction" encoding (1=straight, 2=left, 3=right) proposed by EchoEcho is not validated in literature — research favors spatial placement on the body over sequential counting. The LLM-for-navigation space is nascent (2023-2024) with no production-scale systems yet. Campus-specific pilots exist (GoodMaps at MSU/Ontario Tech, RightHear at USD, Aira at Harvard/Syracuse) but all require either pre-mapped LiDAR data or infrastructure. EchoEcho's "no infrastructure needed" claim is the central technical question that the pitch does not adequately address.

---

## Detailed Findings

### 1. Existing VI Navigation Apps — State of the Market

#### Microsoft Soundscape — Discontinued

Microsoft Soundscape was discontinued in January 2023, with the Azure back-end shut down by June 2023. The app used 3D spatial audio cues rather than turn-by-turn directions, providing ambient awareness of nearby points of interest (streets, intersections, landmarks) via binaural sound. Microsoft open-sourced the codebase on GitHub at discontinuation. This was a research project, not a commercial product, and it only worked outdoors with GPS. It did not solve indoor navigation.

Sources: [AppleVis](https://www.applevis.com/blog/microsoft-discontinue-its-soundscape-app-make-code-available-open-source-software), [TechCrunch](https://techcrunch.com/2022/12/13/microsoft-sunsets-soundscape-3d-audio-app-but-will-open-source-the-code/amp/)

#### Be My Eyes — Human + AI Hybrid

Be My Eyes connects blind users with sighted volunteers via live video. In March 2023, it launched "Be My AI" (Virtual Volunteer), powered by GPT-4 Vision, which provides AI-generated image descriptions and contextual advice without requiring a human volunteer. Beta users described it as "life-changing." Average resolution time with AI was 4 minutes, roughly half that of human agents. Some inaccuracies in image recognition require human fallback.

**Navigation gap**: Be My Eyes is reactive (user asks, gets answer) rather than proactive navigation. It does not provide continuous turn-by-turn guidance. It addresses scene understanding, not route following.

Sources: [OpenAI](https://openai.com/index/be-my-eyes/), [BusinessWire](https://www.businesswire.com/news/home/20230314005425/en/Be-My-Eyes-Announces-New-Tool-Powered-by-OpenAIs-GPT-4-to-Improve-Accessibility-for-People-Who-are-Blind-or-Have-Low-Vision/)

#### Aira — Human Expert Network with Campus Licensing

Aira connects blind users with trained sighted "agents" who access the user's phone camera and provide real-time guidance. The campus model is a geofenced Access Partnership: universities pay an annual fee, and all users on campus get free unlimited access. Adopted by 100+ universities including Harvard, Syracuse, Columbia, Rutgers, Texas A&M, and Utah State (pilot launched 2025).

**Navigation gap**: Aira requires trained human interpreters. It scales via the network but has inherent latency, cost per seat, and dependency on agent availability and skill. It is not an autonomous system.

Sources: [Syracuse University](https://news.syr.edu/blog/2024/05/01/syracuse-university-to-provide-aira-visual-interpreting-service-to-campus-community/), [Harvard Accessibility](https://accessibility.harvard.edu/news/2024/04/harvard-offers-site-wide-access-visual-interpreting-service-aira)

#### BlindSquare — Outdoor/Beacon-Indoor Hybrid

BlindSquare is the world's most widely adopted app for VI navigation, combining GPS-based outdoor navigation with Bluetooth beacon-based indoor guidance. Indoor functionality requires campus-specific installation of iBeacon hardware at doorways, stairwells, and junctions. Multiple campuses have deployed this (Columbus State Community College documented as early as 2018). Users receive voice prompts when passing beacons. The database of points of interest is community-maintained.

**Navigation gap**: Infrastructure dependency is the critical constraint. Each building requires a physical beacon installation project. Coordination of language/instructions across buildings requires ongoing maintenance.

Sources: [BlindSquare Indoor](https://www.blindsquare.com/indoor/), [Canadian Assistive Technologies](https://canasstech.com/blogs/news/let-it-beacon-creating-accessible-indoor-spaces)

#### GoodMaps — LiDAR-Based Campus Navigation

GoodMaps is the most technically sophisticated campus indoor navigation system currently deployed. It uses a LiDAR backpack to scan buildings at centimeter-level precision, creating digital maps from 360-degree imagery and laser measurements. The app then provides turn-by-turn guidance using camera-based positioning (visual odometry against the pre-built map), achieving sub-30cm accuracy without requiring ongoing beacon infrastructure.

Deployed at: Michigan State University (STEM building, Bessey Hall), Ontario Tech University, Eugene Airport. A student at MSU called it "intuitive" and "could have a lot of positive impact."

**Gap**: GoodMaps requires an upfront LiDAR scanning engagement by the company for every building. This is infrastructure-as-service, not zero-infrastructure. General LiDAR mapping projects are resource-intensive (equipment, skilled operators, processing). A campus with 50 buildings would require 50 separate scan engagements.

Sources: [MSU RCPD](https://www.rcpd.msu.edu/news/ability-blog/msu-improves-campus-accessibility-through-introducing-goodmaps), [GoodMaps LiDAR](https://goodmaps.com/newsroom/lidar-mapping-for-precise-indoor-navigation/), [Ontario Tech](https://accessibility.ontariotechu.ca/resources/goodmaps-explore.php)

#### Google Lookout (2024) — Scene Understanding, Not Navigation

Google Lookout (Android only) was significantly updated in 2024, adding "Find mode" (locating objects like doors and bathrooms by panning camera), AI-generated image captions powered by Gemini, and follow-up Q&A on captured images. It covers seven modes: Text, Documents, Explore, Currency, Food labels, Find, and Images.

**Navigation gap**: Lookout is a scene-interrogation tool, not a continuous navigation system. It does not track position or provide route guidance.

Sources: [Google Blog](https://blog.google/company-news/outreach-and-initiatives/accessibility/ai-accessibility-update-gaad-2024/), [Google Accessibility](https://support.google.com/accessibility/android/answer/9031274?hl=en)

#### Lazarillo — GPS + Beacon Outdoor/Indoor

Lazarillo (Chilean startup, Forbes Best Chilean Startup 2024) provides real-time audio navigation for outdoor environments and beacon-mapped indoor spaces. In 2024 the company launched MapVX, a digital mapping platform targeting shopping centers, airports, universities, and medical centers. Indoor navigation is fully dependent on buildings having been added to the Lazarillo/MapVX database with beacon or digital map configuration.

**Navigation gap**: Same infrastructure dependency as BlindSquare for indoor. Outdoor-first product with indoor as an add-on requiring the venue to participate.

Sources: [Lazarillo 2024 Expansion](https://lazarillo.app/uncategorized/lazarillocomprehensivesolutions/)

#### Snap&Nav — MobileHCI 2024 Research System

Snap&Nav (IBM Research, MobileHCI 2024) takes a different approach: a sighted person photographs a physical floor map posted in the building, the system analyzes the floor map to extract a navigable node graph of intersections and destinations, and then guides the blind user turn-by-turn using intersection detection. User studies with 12 blind participants showed increased confidence and reduced cognitive load versus cane-only navigation.

**Significance**: This demonstrates that AI analysis of existing building assets (floor maps) can substitute for bespoke digital maps. It still requires a sighted assist to capture the initial photo but removes the need for pre-installed beacons or LiDAR scans. This is the closest research precedent to a "low-infrastructure" indoor navigation approach.

Sources: [ACM Digital Library](https://dl.acm.org/doi/10.1145/3676522), [Snap&Nav Project Page](https://wotipati.github.io/projects/other_papers/MobileHCI2024_SnapAndNav/MobileHCI2024_SnapAndNav.html)

#### Wayfindr — Open Standard (BLE-Based)

Wayfindr developed the world's first ITU-approved open standard (ITU-T F.921) for accessible indoor audio navigation. Trials ran on London Underground, Sydney, Oslo, Barcelona, Venice. The standard defines how BLE beacon networks should be structured, what language audio cues should use, and how app interfaces should behave. It does not eliminate infrastructure — it standardizes it.

Sources: [Wayfindr](https://www.wayfindr.net/), [ITU](https://www.itu.int/hub/2020/06/how-the-wayfindr-open-standard-uses-new-tech-to-help-the-visually-impaired/)

---

### 2. Indoor Navigation Without Beacons — Technical Realities

#### Pedestrian Dead Reckoning (PDR) via Accelerometer + Gyroscope

PDR is the most studied phone-only approach. The phone detects steps via accelerometer, estimates stride length, and tracks heading via gyroscope/magnetometer. This is well-understood and widely implemented.

**Accuracy findings from 2023-2024 research:**

- Best-case published result (2024, improved PDR): sub-0.5m error over a 108-meter walk under controlled conditions
- Typical published results: 1.6-1.8m horizontal positioning error (RMSE) under normal conditions
- Relative precision: approximately 1-2.3% of distance traveled
- Real-world corridor navigation: accumulating drift means the system can guarantee less than 3m error for 95% of positions over moderate distances with filtering; classic implementations show up to 5m error at 80% confidence
- Long distances: drift accumulates rapidly. Gyroscope bias (MEMS sensor zero-offset instability) causes heading error that compounds into large positional error

**Core problem**: A campus corridor is 2-4 meters wide. A 3-5 meter positional error means the system cannot reliably tell the user which side of a corridor junction they are on. Turns that should occur at specific doorways cannot be reliably triggered. The "1.6m RMSE" figure sounds manageable, but in a complex building with many doors and intersections at 10-20 meter intervals, this is not navigation-grade accuracy.

**Drift correction strategies** studied in literature:
- Magnetic field anomaly detection (large appliances create repeatable field signatures) — works in some buildings
- Building map constraint projection (particle filter forces trajectory to plausible corridors) — effective but requires a floor plan in digital form
- WiFi fingerprinting fusion — reduces to 1-2m accuracy indoors, but WiFi signal maps must be pre-collected per building
- Visual-Inertial Odometry (VIO, camera + IMU) — 90th percentile error under 3m in a 2-minute walk; requires camera active, which is impractical for cane users

**The "no infrastructure" problem**: Pure PDR without any external correction or map constraint degrades rapidly in real corridors. All high-accuracy phone-only approaches in 2024 research either require a pre-built floor plan or a pre-collected environmental fingerprint (WiFi RSSI map, magnetic map), both of which are forms of infrastructure even if not physical hardware.

Sources: [ScienceDirect 2024 PDR](https://www.sciencedirect.com/science/article/abs/pii/S0263224124003014), [PMC RadarPDR](https://pmc.ncbi.nlm.nih.gov/articles/PMC10007269/), [Tandfonline 2024](https://www.tandfonline.com/doi/full/10.1080/10095020.2024.2338225), [PMC Indoor Systems Review](https://pmc.ncbi.nlm.nih.gov/articles/PMC7038337/)

#### Accuracy Comparison by Technology (PMC 2020 Review, confirmed 2024)

| Technology | Accuracy | Infrastructure |
|---|---|---|
| UWB | ±0.15m (95% CI) | Hardware beacons required |
| BLE | 1-2m | Hardware beacons required |
| WiFi fingerprinting | ±0.6m median | Pre-collected RSSI map |
| RGB-D camera | ±0.2m | Pre-built map or known environment |
| Pure IMU/PDR | 1.6-5m RMSE | None, but drifts badly over time |
| Sensor fusion (EKF WiFi+IMU) | 0.24-0.38m | Pre-collected WiFi map |

The UCSC Manduchi group (October 2024) demonstrated a phone-only indoor navigation system (Wayfinding and Backtracking apps) that uses IMU sensors plus building floor plan maps. They tested it in the Baskin Engineering building and users successfully navigated. Critically, their system does require a digital floor plan — it uses the map to constrain PDR drift. They are planning to add AI-powered scene description as a future feature for hard-to-navigate open spaces.

Source: [UCSC News](https://news.ucsc.edu/2024/10/manduchi-wayfinding-apps/), [ScienceDaily](https://www.sciencedaily.com/releases/2024/10/241008103803.htm)

---

### 3. Haptic Navigation Interfaces — Research Findings

#### What Works

Vibration is a confirmed effective modality for VI navigation. Key validated findings from literature:

1. **Spatial placement beats sequential patterns**: The most rigorous body-placement study (PMC 2017) tested 13 vibration patterns on a tactile belt. Results: single bursts at spatially meaningful locations (left tactor for left turn, right tactor for right turn, front tactor for straight) outperformed sequential pulse patterns. Conclusion: "single bursts might be better than sequence vibration patterns."

2. **Differentiated patterns are better than uniform ones**: Research consistently shows that using different vibration characteristics (frequency, duration, rhythm) for different commands achieves better recognition rates than simple uniform pulses. Recognition rates of 82-90% for well-designed patterns, dropping to 65% for ambiguous ones.

3. **Response time**: Pattern response times ranged 2.9-4.5 seconds in one study. Shorter patterns enable faster user response in urgent situations. This matters for real-time navigation where turn cues must arrive before the user reaches the decision point.

4. **Fatigue is a real concern**: Prolonged vibrotactile stimulation causes adaptation, reducing the ability to accurately perceive cues. A full campus navigation session could encounter this.

5. **Hand-held directional haptics**: A 2023 PMC study tested asymmetric vibration (shear forces) on a hand-held device for directional cues across a 180-degree range. Mean error in dynamic guided conditions: ~0.32 radians (18 degrees), with 27 of 30 participants finding the dynamic version significantly easier than static.

#### Assessment of EchoEcho's Proposed Encoding (1=straight, 2=left, 3=right)

The research literature does not validate counting sequential pulses as a primary directional navigation interface. Several problems with this approach:

- **Cognitive load during counting**: Under navigational stress (cane in one hand, unfamiliar space, time pressure), counting pulses introduces working memory demand. The user must count to determine direction rather than feel an immediate spatial cue.
- **Absence of prior validation**: No published study has specifically tested pulse counting (1/2/3 bursts) as a directional encoding for blind users. This is an untested design hypothesis.
- **Literature preference for spatial encoding**: Every spatial navigation haptics study found that body-location cues (left = left side, right = right side) were more intuitive and learned faster than symbolic encoding.
- **Confusion potential**: 1 pulse vs. 2 pulses vs. 3 pulses must be reliably distinguishable. In a noisy campus environment with background vibrations (footsteps, passing vehicles, HVAC), false positive pulse counts are a real concern.

**Better approaches supported by research**:
- Phone vibration duration (short = turn approaching, long = turn now)
- Spatial cues via smartwatch (right watch = right turn, no buzz = straight) — Manduchi group has implemented this
- Continuous vibration intensity that increases as turn approaches (proximity encoding)
- Shape-changing haptic devices (Nature Scientific Reports 2024 study) showed significantly faster target acquisition vs. vibration

Sources: [PMC 2017 Belt Study](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5366061/), [PMC 2022 Patterns](https://pmc.ncbi.nlm.nih.gov/articles/PMC8749676/), [PMC 2023 Hand-Held](https://pmc.ncbi.nlm.nih.gov/articles/PMC10611303/), [Nature 2024](https://www.nature.com/articles/s41598-024-79845-7), [SAGEPUB Scoping Review 2025](https://journals.sagepub.com/doi/10.1177/10711813251360706)

---

### 4. AI/LLM-Powered Navigation for VI

#### Current Research State (2023-2025)

The LLM-for-VI-navigation field emerged in 2023-2024. Several approaches:

**Turn-by-Turn with Vision LLM (arXiv Oct 2024)**: A system using ViLT/BLIP multimodal models and on-device Llama on a Raspberry Pi. The smartphone camera feeds real-time images to the Pi via WiFi, which analyzes signs, obstacles, and architectural features and generates "detailed descriptive narratives." A primary bottleneck: BLIP has "large computation cost" limiting real-time deployment. No accuracy numbers published; still a prototype paper.

**Be My AI (GPT-4V, production 2023)**: Functional LLM-in-the-loop system. Not continuous navigation but reactive scene description. Demonstrates that VLMs can reliably describe a scene and answer navigational questions.

**VIALM Survey (arXiv 2024)**: Survey benchmarking LLMs, VLMs, and embodied agents for VI assistance. Establishes the research taxonomy.

**VIAssist (arXiv 2024)**: Multi-modal LLM adapted specifically for VI users, with interface modifications (larger haptic triggers, simplified prompting).

**Eyedaptic perspective on LLMs for navigation**: Identifies three emerging patterns — Scene Graph Generation (spatial object relationships), Visualization of Thought (multi-step spatial reasoning), and cognitive mapping. All are research-stage, none production-deployed.

**Real-Time Wayfinding Assistant (arXiv 2025)**: A "voice-driven, LLM-powered assistive framework" designed for low-latency context-aware responses. Still preprint/prototype.

**Human-AI Collaboration for Remote Sighted Assistance (MDPI 2024, PMC 2024)**: Interviews with 12 Aira agent users. Identified four main challenge categories: localizing users, interpreting surroundings, situational specificity, and poor network connectivity. This is a critique of current human-in-the-loop systems, not a purely AI solution.

**Assessment for EchoEcho**: Using Claude AI for navigation instruction generation is technically plausible. The VLM-to-instruction pipeline exists and works for scene understanding. The unsolved problem is position tracking — Claude cannot know where the user is without reliable localization. LLM-generated instructions are only useful if the system knows when and where to trigger them. The AI component of EchoEcho is probably the most commercially sound element of the pitch; the sensor-based positioning is the weak link.

Sources: [arXiv 2410.19954](https://arxiv.org/html/2410.19954v1), [arXiv VIALM](https://arxiv.org/html/2402.01735v1), [arXiv VIAssist](https://arxiv.org/html/2404.02508v1), [arXiv Real-Time](https://arxiv.org/html/2504.20976v1), [MDPI Human-AI](https://www.mdpi.com/1999-5903/16/7/254)

---

### 5. Campus-Specific Navigation — Pilot Programs and Outcomes

#### GoodMaps at Michigan State University (2023)

GoodMaps LiDAR-scanned the STEM building and Bessey Hall at MSU. Student feedback was positive ("intuitive," "good impact"). The deployment required a GoodMaps team to walk the campus with a LiDAR backpack — infrastructure-as-service, not zero-infrastructure. Only two buildings covered in the documented deployment.

#### RightHear at University of San Diego (Spring 2024)

Engineering students deployed RightHear in the Belanich Engineering Center as part of a User Centered Design course. RightHear provides audio guidance ("Welcome to the Belanich Engineering Center. You are in the main lobby...") as users move through space. This appears to be beacon-based audio signage rather than turn-by-turn navigation.

#### Aira Campus Access Partner Network (2024, 100+ universities)

The most widely deployed campus VI assistance program. University pays annual fee, campus is geofenced, blind users get on-demand interpreter access. Harvard announced campus-wide coverage April 2024. Syracuse joined May 2024. USU launched pilot 2025 via IDRPP grant funding.

**Model assessment**: Aira has successfully penetrated university disability services as a budget line item, demonstrating that universities will pay for VI access solutions. This is a useful commercial precedent for EchoEcho if it can demonstrate ROI relative to Aira's model.

#### Ontario Tech University (GoodMaps Explore)

Ontario Tech deployed GoodMaps Explore campus-wide as an inclusive navigation solution, not just for blind users. App is free to download. This is a more ambitious deployment than MSU's two-building pilot.

#### NYU Tandon (VR-Tested Navigation System)

NYU Tandon engineers developed a navigation aid tested first in virtual reality to reduce real-world risk during trials. Demonstrated that VR pre-testing is a viable methodology for campus navigation systems. Results showed "promise."

#### Snap&Nav User Study (MobileHCI 2024)

12 blind participants navigated with Snap&Nav. Results: increased confidence, lower cognitive load vs. cane-only. However, the system still requires a sighted person to photograph the floor map — not fully independent.

Sources: [USD News](https://www.sandiego.edu/news/detail.php?_focus=94163), [GoodMaps Connect](https://connect.goodmaps.com/docs/supporting-students-with-disabilities/), [Aira Education](https://aira.io/education/), [Ontario Tech](https://accessibility.ontariotechu.ca/resources/goodmaps-explore.php), [NYU Tandon](https://engineering.nyu.edu/news/new-virtual-reality-tested-system-shows-promise-aiding-navigation-people-blindness-or-low)

---

### 6. Competitor Landscape and Funding

#### GoodMaps

Private company, Kentucky-based, former subsidiary of the American Printing House for the Blind. Targets airports, campuses, transit systems. Commercial model: LiDAR scanning service contract + app licensing to venue operators. Deployed in: Eugene Airport, MSU, Ontario Tech, and others. No public funding round data found; appears to operate B2B. Technically the most capable campus indoor navigation system currently in production.

#### Aira

Private company. B2B campus licensing model (annual geofence fee). 100+ university partners as of 2024. Revenue model validated by sustained university adoption. Human-in-the-loop means cost scales with usage in ways pure-software does not. [Crunchbase shows Aira raised approximately $20.5M across multiple rounds as of last public data.]

#### Lazarillo

Chilean startup. Named among best Chilean startups of 2024 by Forbes. Launched MapVX platform in 2024 targeting shopping centers, airports, resorts, universities, medical centers. Revenue model: venue mapping + app subscriptions. Expanding into B2B digital mapping as a service.

#### Haptic (Haptic Works / Kevin Yoo)

Presented at TechCrunch Disrupt 2024 Startup Battlefield. Available in 31 countries. Non-visual, non-verbal navigation via haptic feedback for both blind and sighted users. Signed contract with Aira. Mid-raise at time of TechCrunch coverage (late 2024). Approach: haptic cues replace audio, targeting sighted users in non-look situations as well as blind users. Positioning: broader than pure-VI accessibility play.

Sources: [TechCrunch Haptic](https://techcrunch.com/2024/10/29/haptics-touch-based-navigation-helps-blind-and-sighted-alike-get-around-without-looking/)

#### dotLumen

Romanian startup. Smart glasses with haptic forehead feedback for depth/obstacle awareness. Partnership with Dassault Systèmes. Limited-series late 2024, US market planned late 2025. Hardware play, not a software-only campus solution.

Sources: [CES 2024 coverage](https://www.letsenvision.com/blog/ces-2024-dotlumens-haptic-navigation-smart-glasses)

#### PetaNetra (Indonesia)

Indoor navigation app for VI, grant-funded (International Trade Center, She Trades Innovator Award 2024). Preparing to scale. AR-based approach. Not campus-specific.

Sources: [WIPO](https://www.wipo.int/pressroom/en/stories/indonesia-peta-netra-2024.html)

#### Wayfindr (UK)

Standard-setting body, not a commercial product. The Wayfindr ITU standard shapes how BLE beacon networks are built. Consulted by venues, not competing for end-user market directly.

#### BlindSquare

Established Finnish app (sampled as world's most-used VI navigation app), beacon-based, iOS-only. Commercial model: $39.99 per user app purchase. Indoor requires venue to deploy iBeacons. Mature product, but infrastructure-dependent and not updated with AI capabilities.

#### NSF Commute Booster ($5M, Dec 2023)

NSF Convergence Accelerator granted $5M to an assistive/rehabilitative technology cluster including Commute Booster (transit navigation for VI). This is the largest single public funding amount identified in this research.

---

## Sources Consulted

### Discontinued/Pivoted Apps
- [Microsoft Soundscape Discontinuation — AppleVis](https://www.applevis.com/blog/microsoft-discontinue-its-soundscape-app-make-code-available-open-source-software)
- [TechCrunch Soundscape Open Source](https://techcrunch.com/2022/12/13/microsoft-sunsets-soundscape-3d-audio-app-but-will-open-source-the-code/amp/)

### Active Apps and Platforms
- [BlindSquare Indoor](https://www.blindsquare.com/indoor/)
- [Lazarillo 2024 Expansion](https://lazarillo.app/uncategorized/lazarillocomprehensivesolutions/)
- [GoodMaps](https://goodmaps.com/)
- [Wayfindr Open Standard](https://www.wayfindr.net/)
- [Aira Education](https://aira.io/education/)
- [Google Lookout 2024 Update](https://blog.google/company-news/outreach-and-initiatives/accessibility/ai-accessibility-update-gaad-2024/)
- [Be My Eyes / Be My AI](https://openai.com/index/be-my-eyes/)

### Campus Deployments
- [GoodMaps MSU](https://www.rcpd.msu.edu/news/ability-blog/msu-improves-campus-accessibility-through-introducing-goodmaps)
- [Ontario Tech GoodMaps](https://accessibility.ontariotechu.ca/resources/goodmaps-explore.php)
- [USD RightHear](https://www.sandiego.edu/news/detail.php?_focus=94163)
- [Harvard Aira](https://accessibility.harvard.edu/news/2024/04/harvard-offers-site-wide-access-visual-interpreting-service-aira)
- [Syracuse Aira 2024](https://news.syr.edu/blog/2024/05/01/syracuse-university-to-provide-aira-visual-interpreting-service-to-campus-community/)
- [NYU Tandon VR Test](https://engineering.nyu.edu/news/new-virtual-reality-tested-system-shows-promise-aiding-navigation-people-blindness-or-low)

### Technical / Academic
- [PMC Indoor Navigation Systems Review 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7038337/)
- [ScienceDirect PDR Multi-Source 2024](https://www.sciencedirect.com/science/article/abs/pii/S0263224124003014)
- [Tandfonline Context-Assisted PDR 2024](https://www.tandfonline.com/doi/full/10.1080/10095020.2024.2338225)
- [PMC RadarPDR](https://pmc.ncbi.nlm.nih.gov/articles/PMC10007269/)
- [PMC On Indoor Localization WiFi BLE UWB IMU](https://pmc.ncbi.nlm.nih.gov/articles/PMC10610672/)
- [UCSC Manduchi Wayfinding 2024](https://news.ucsc.edu/2024/10/manduchi-wayfinding-apps/)
- [ScienceDaily Manduchi 2024](https://www.sciencedirect.com/releases/2024/10/241008103803.htm)
- [arXiv Turn-by-Turn Indoor LLM 2024](https://arxiv.org/html/2410.19954v1)
- [arXiv Real-Time Wayfinding 2025](https://arxiv.org/html/2504.20976v1)
- [VIALM Survey arXiv 2024](https://arxiv.org/html/2402.01735v1)
- [VIAssist arXiv 2024](https://arxiv.org/html/2404.02508v1)
- [Snap&Nav MobileHCI 2024 ACM](https://dl.acm.org/doi/10.1145/3676522)
- [ResearchGate GoodMaps Assessment](https://www.researchgate.net/publication/382864586_GoodMaps_Assessing_an_Indoor_Navigation_App_Built_on_Camera-based_Positioning)

### Haptic Research
- [PMC Haptic Feedback Indoor 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC8749676/)
- [PMC Vibration Patterns for Blind 2017](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5366061/)
- [PMC Hand-Held Haptic Directional 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10611303/)
- [Nature Shape-Changing Haptic 2024](https://www.nature.com/articles/s41598-024-79845-7)
- [SAGEPUB Haptic Navigation Scoping Review 2025](https://journals.sagepub.com/doi/10.1177/10711813251360706)
- [Springer Haptic+Auditory Study 2025](https://link.springer.com/article/10.1007/s12193-025-00463-2)
- [York University Vibration vs Audio](https://www.yorku.ca/mack/hcii2018a.html)

### Competitor / Startup Funding
- [TechCrunch Haptic Disrupt 2024](https://techcrunch.com/2024/10/29/haptics-touch-based-navigation-helps-blind-and-sighted-alike-get-around-without-looking/)
- [dotLumen CES 2024](https://www.letsenvision.com/blog/ces-2024-dotlumens-haptic-navigation-smart-glasses)
- [WIPO PetaNetra Indonesia 2024](https://www.wipo.int/pressroom/en/stories/indonesia-peta-netra-2024.html)
- [All_Aboard Bus App — Mass Eye and Ear 2024](https://masseyeandear.org/news/press-releases/2024/01/all-aboard-app-effectively-aids-blind-and-visually-impaired-commuters)
- [Eyedaptic LLMs for VI Navigation](https://eyedaptic.com/llms-navigation/)

---

## Source Quality Assessment

**High confidence**: PDR accuracy numbers are well-replicated across multiple independent academic groups. The Soundscape discontinuation is confirmed fact. Campus deployment data (GoodMaps at MSU, Aira at 100+ universities) comes from institutional press releases and is reliable.

**Medium confidence**: Specific accuracy claims for GoodMaps ("sub-30cm") come from GoodMaps marketing. The 2024 Manduchi Wayfinding app results are from a news release without published peer-review data yet.

**Low confidence**: Funding amounts for most startups (Haptic Works, dotLumen) are not publicly disclosed. The LLM-based navigation papers (arXiv 2024-2025) are preprints without peer review; accuracy claims are preliminary.

**Gaps**: No Reddit or community forum data was successfully retrieved (site: queries returned zero relevant results). Community sentiment about existing apps comes only from isolated quotes in press coverage, not systematic user feedback. No pricing data was found for GoodMaps per-building scan costs.

---

## Open Questions

1. What is GoodMaps's actual per-building scanning cost? This is critical to understanding whether it is a defensible moat or a replicable service model.

2. What floor plan data formats are available for US campuses? Many universities publish PDF floor plans; could a vision LLM extract navigable graphs from these automatically (removing the need for any sighted assist, as Snap&Nav requires)?

3. Has anyone tested smartwatch-only haptic guidance (right watch = right turn, left watch = left turn) in a systematic trial? This is the spatial encoding approach the research supports, and a smartwatch is already infrastructure on many users' wrists.

4. What is the Aira annual fee for university licensing? This sets the competitive price ceiling for a campus software solution.

5. Does EchoEcho plan to use Claude Vision (multimodal) or text-only Claude? The scene understanding use case (identifying landmarks for drift correction) requires vision capability.

6. How does EchoEcho plan to acquire floor plan data for its routing engine? This is the single most important unanswered question in the pitch.

---

## Actionable Takeaways for EchoEcho Navigator Evaluation

**Strengths of the pitch with research support**:
- AI-generated natural language navigation instructions are technically validated (Be My AI, Manduchi group future work, arXiv 2024 systems all converge here)
- The market gap is real: indoor campus navigation without infrastructure is genuinely unsolved
- University willingness to pay is validated (Aira model, GoodMaps model, RightHear deployments)
- Haptic feedback as a modality is research-validated

**Weaknesses / claims requiring scrutiny**:

1. **"No infrastructure needed"** is the most important claim to interrogate. The research literature shows pure IMU dead reckoning on a smartphone yields 1.6-5m error, which is insufficient for corridor-level navigation. Any accurate phone-only system found in 2024 research uses either a pre-collected WiFi/magnetic fingerprint map or a digital floor plan — both of which are forms of infrastructure. The pitch must explain how the system handles drift without any correction anchor.

2. **Vibration pulse counting (1=straight, 2=left, 3=right)** lacks research validation and contradicts the dominant finding that spatial body placement is more intuitive than symbolic pulse encoding. This specific design choice should be stress-tested with blind users before the team commits to it.

3. **Claude AI's role in real-time turn-by-turn guidance** requires clarification. LLMs have high latency relative to real-time navigation demands. If Claude is being polled continuously during a walk, the latency and cost profile may be unacceptable. If it is used to pre-generate a route description once (not in real-time), the architecture is more plausible.

4. **Competition from GoodMaps** is stronger than the pitch likely acknowledges. GoodMaps is infrastructure-free at use-time (no beacons needed while using the app) and has proven university partnerships. The only differentiation EchoEcho offers over GoodMaps is removing the initial LiDAR scanning requirement — which is a real differentiator if it can be delivered.

**Suggested due diligence steps**:
- Ask the team how the system performs in a building with no pre-loaded floor plan and no WiFi map
- Ask for video of the app in use in an unfamiliar multi-story building
- Compare Aira annual campus cost to EchoEcho's proposed pricing model
- Run a user test of the 1/2/3 pulse encoding with 5 blind users before endorsing the interface design
- Investigate whether campus floor plans (typically available as PDFs) can be automatically parsed to generate routing graphs — this would be the actual technical moat if it works
