---
title: Smart Glasses for VI Navigation Assistance - Platform Landscape 2025-2026
type: research
tags: [smart-glasses, visually-impaired, navigation, accessibility, wearables, EchoEcho]
summary: Comprehensive survey of smart glasses platforms for VI campus navigation, evaluating camera-to-phone streaming, audio output, developer access, form factor, and cost across 12+ devices
status: active
source: deep-research
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

The smart glasses market underwent a significant inflection in 2025-2026, with shipments doubling YoY and Meta capturing 73% market share (7 million units sold). For EchoEcho's architecture (glasses as camera/audio platform, phone in pocket for compute + positioning), the **Ray-Ban Meta** with the **Meta Wearables Device Access Toolkit** is the strongest current option: 720p/30fps camera-to-phone streaming via BLE, open-ear spatial audio speakers, normal-looking form factor at $299, and 8-hour battery life. The **Solos AirGo V2** (the hardware underlying Envision Ally Solos) is the strongest accessibility-native alternative with a 16MP camera, WiFi data streaming, and an SDK at $299+. **Brilliant Labs Frame** offers the most open developer ecosystem but only supports still image capture over BLE (3fps), unsuitable for real-time video. By late 2026, Apple and Google/Samsung will both launch smart glasses with cameras, creating a much larger addressable hardware base.

---

## 1. Platform Comparison Matrix

| Device | Camera | Audio Output | Weight | Battery | Price | Camera-to-Phone Stream | SDK/API | Form Factor |
|--------|--------|-------------|--------|---------|-------|----------------------|---------|-------------|
| **Ray-Ban Meta Gen 2** | 12MP ultrawide, 3K video | Open-ear directional speakers, spatial audio | 69-70g | 8hr moderate / 5hr continuous | $299 | 720p/30fps via BLE (DAT) | Kotlin (Android), Swift (iOS) - developer preview | Looks like normal Ray-Bans |
| **Meta Ray-Ban Display** | Same as Gen 2 | Same + 600x600 monocular display | 69-70g | 6hr mixed use | ~$399 | Same DAT toolkit | Same | Normal glasses with subtle display |
| **Envision Ally Solos** | 2x 5MP (2048x1944) | Directional stereo speakers, beamforming mics | 42g | 15-16hr | $399 (incl. 1yr Ally Pro) | Phone does all processing; unclear if 3rd party camera access exists | No public 3rd-party SDK for Ally | Normal glasses, 3 colors |
| **Solos AirGo V2** | 16MP with EIS | Stereo speakers | ~45g (est.) | ~12hr | $299+ | Full HD via WiFi (V2 data) + BLE (control) | SDK ($1,999 dev kit), supports ChatGPT/Claude/Gemini | Normal glasses, modular |
| **Brilliant Labs Frame** | 720x720 (OV09734) | No speaker (display only, mic only) | 39g | All-day with charger case | $349 | Still images only, ~3fps via BLE 5.3, 65kB/s | Lua (on-device), Python & Flutter SDKs (BLE) | Thick frames, looks nerdy |
| **Mentra Live** | 12MP, 119-degree FOV | Stereo speakers | 43g | 12hr+ | $299 | HD livestreaming via WiFi | TypeScript SDK, MIT license, full camera access | Normal glasses |
| **Agiga EchoVision** | 13MP wide-angle (est. 150 degree) | Speaker (built-in) | Unknown | 6hr (30min continuous AI) | $599 ($449 preorder) | Unknown | No public SDK | Normal glasses + attachable shades |
| **OrCam MyEye 3 Pro** | 8MP (clip-on device) | Above-ear speaker + BT | Very small (clip-on) | Unknown | ~$4,250 | None - fully on-device processing | No SDK | Magnetic clip on any glasses |
| **Even Realities G1** | **No camera** | **No speaker** (display only) | 45-50g | Unknown | $599 | N/A | MentraOS compatible | Most normal-looking glasses |
| **Halliday** | **No camera** | **No speaker** (display only) | 28.5g | 12hr | $499 | N/A | No SDK | Ultra-lightweight, normal |
| **XREAL Air 2 Ultra** | Dual grayscale (tracking only) | No built-in speaker | ~75g | Powered by phone | $699 | No RGB camera stream | Enterprise SDK only for camera | Tinted AR glasses |
| **NIIRA (Sensotec)** | Intel RealSense D415 depth camera | Bone conduction | Unknown | 10hr | Unknown (EU only) | Processes via pocket unit | No public SDK | Glasses + pocket processor |
| **Vuzix Z100** | Camera (specs unknown) | Speaker | Unknown | Unknown | Unknown | Via Connectivity SDK | Android/iOS SDKs, Unity, Flutter support | Slim smart glasses |

---

## 2. Camera-to-Phone Streaming: Technical Analysis

This is the critical capability for EchoEcho. The phone needs continuous video frames from the glasses camera to run the perception pipeline.

### Tier 1: Production-Ready Streaming

**Ray-Ban Meta (via Meta Wearables Device Access Toolkit)**
- Protocol: BLE (Bluetooth)
- Max resolution: 720p, max framerate: 30fps
- Auto-downgrades when bandwidth is limited
- SDK: Native Kotlin (Android) and Swift (iOS), distributed as Maven/SPM packages
- SDK structure: `mwdat-core` (connectivity), `mwdat-camera` (video/photo), `mwdat-mockdevice` (testing)
- Status: Developer preview since Dec 2025; publishing restricted to select partners, broader publishing expected 2026
- No React Native wrapper exists; would require native module bridge
- Supported devices: Ray-Ban Meta Gen 1 and Gen 2, Oakley Meta HSTN; Oakley Meta Vanguard and Meta Ray-Ban Display coming soon

**Solos AirGo V2 (via AirGo SDK)**
- Protocol: BLE for control, WiFi for V2 data streaming
- Full HD video streaming capability
- SDK cost: $1,999 (includes 2 pairs of glasses + 1 year support)
- Multimodal AI integration (image, video, audio, text)
- Mobile links over BLE (control) and WiFi (V2 data)
- Simple APIs and webhook hooks for streaming data

**Mentra Live (via MentraOS SDK)**
- Protocol: WiFi for HD livestreaming
- TypeScript SDK with full camera, mic, speaker access
- MIT license, 100% open source
- Cross-compatible with Even Realities G1 and Vuzix Z100
- Youngest platform; shipping started Feb 2026 (1,000 unit first batch)

### Tier 2: Limited Streaming

**Brilliant Labs Frame**
- BLE 5.3 only, 65kB/s throughput
- Still images only: 720x720 JPEG, approximately 3fps
- No video stream capability due to BLE bandwidth constraints
- Best for "keyframe capture every few seconds" pattern, not continuous video
- Fully open source, Python/Flutter/Lua SDKs
- No speaker output (mic only), so cannot deliver audio alerts

**Vuzix (via Connectivity SDK)**
- Android-to-glasses connectivity SDK available on GitHub
- Camera API available but documentation is sparse
- Supports VUZIX M400, M4000, SHIELD, BLADE, BLADE 2
- Enterprise-focused, not consumer-oriented

### Tier 3: No Third-Party Camera Access

**Envision Ally Solos**: Processing goes through Envision's Ally app; no evidence of third-party camera access API. Built on Solos AirGo hardware, so theoretically the AirGo SDK could work, but Envision may lock it down.

**OrCam MyEye**: Completely closed system, all processing on-device.

**Agiga EchoVision**: No public SDK, companion app only.

**NIIRA**: Proprietary depth-to-audio pipeline, pocket processing unit.

---

## 3. Audio Output for VI Users

### Open-Ear Speaker Glasses (Best for VI)

VI users need environmental awareness while receiving audio guidance. Open-ear speakers preserve this.

**Ray-Ban Meta Gen 2:**
- Custom-built dual speakers with beamforming (minimal sound leakage)
- 50% louder than Gen 1, improved bass
- Spatial audio capability (sounds positioned in 3D space around user)
- 5-mic array with noise cancellation for clear voice capture
- Meta AI voice assistant built in
- **Verdict**: Best audio quality of any smart glasses. Spatial audio is directly applicable to directional navigation cues ("turn left" sounds like it comes from the left).

**Solos AirGo V2 / Ally Solos:**
- Directional stereo speakers with minimal sound leakage
- Beamforming microphones for noisy environments
- Audio quality reported as good for spoken word
- **Verdict**: Strong second option, designed for accessibility from the start.

**Mentra Live:**
- Built-in stereo speakers, three microphones
- Limited reviews of audio quality available

### Bone Conduction

**NIIRA (Sensotec):** Uses bone conduction specifically to keep ears free for environmental sounds. The "sound language" approach (non-verbal spatial audio cues rather than speech) is architecturally interesting for navigation but requires user learning.

**General comparison**: Bone conduction provides superior environmental awareness but weaker audio quality (thin bass, position-sensitive clarity). Open-ear directional speakers (Ray-Ban Meta style) offer a better balance for spoken navigation prompts while still allowing ambient sound.

### Latency Considerations

- Phone-to-glasses audio latency over BLE: typically 150-250ms (standard Bluetooth audio)
- For urgent obstacle alerts, this latency is acceptable if supplemented by on-device TTS (~100ms) on the phone speaker as fallback
- Spatial audio processing adds minimal additional latency when done on the phone

---

## 4. VI-Specific Smart Glasses Products

### Envision (Ally Solos) - $399

**What it does:** Scene description, text reading (OCR), face recognition, object/color/currency identification, "Ask Envision" (GPT-powered Q&A), Aira integration for human assistance. Ally is the upgraded AI assistant.

**Architecture:** All processing on the phone via the Ally companion app. Glasses are sensors (cameras, mics) and output (speakers). Cloud-based AI for complex queries, some offline features.

**Real-world reception:** Highly regarded in the VI community. Purpose-built for accessibility. The partnership with Solos for hardware and dual 5MP cameras is a significant upgrade from the original Google Glass EE2-based Envision Glasses.

**Key limitation for EchoEcho:** No third-party camera access. You would need to partner with Envision or use the underlying Solos SDK.

### OrCam MyEye 3 Pro - ~$4,250

**What it does:** Text-to-speech from any surface, face recognition, product/color/currency identification, translation in 140+ languages, "Just Ask" AI assistant.

**Architecture:** Entirely on-device processing using preloaded database. No internet connection required. Camera clips magnetically to any glasses frame.

**Real-world reception:** Well-established in the VI community. The price is the primary barrier.

**Irrelevant for EchoEcho:** Completely closed system, no SDK, no camera streaming.

### Aira - $89-329/month subscription

**What it does:** Connects VI users with trained human agents who see through the user's camera (phone or smart glasses). Agents provide real-time verbal guidance using GPS, Google Maps, and the video feed.

**Architecture:** Camera stream goes to Aira dashboard where remote human agents interpret visual information. Flutter-based apps for iOS and Android. Has an Aira SDK for integration.

**2025-2026 developments:** Working with Google for a year; Aira service expected to run on Google's Android XR glasses unveiled at I/O 2025.

**Relevance to EchoEcho:** The Aira SDK could be a fallback/complement for situations where AI navigation fails. Human agents as escalation path.

### Be My Eyes on Meta Glasses

**What it does:** Connects VI users to sighted volunteers via video call from Ray-Ban Meta glasses. March 2026 expansion added hands-free video to trusted contacts and branded service teams (Tesco, Hilton, Amtrak, Sony).

**Architecture:** POV video calling via Meta glasses to remote volunteers/agents.

**Relevance:** Demonstrates that the Ray-Ban Meta camera-to-phone-to-cloud pipeline works for real-time VI assistance. Validates the form factor.

---

## 5. Form Factor and Social Acceptability

Ranked from most to least "normal-looking":

1. **Even Realities G1** (45-50g, no camera/speaker, prescription available) - most normal, but useless for EchoEcho (no camera)
2. **Halliday** (28.5g, no camera) - ultralight, invisible display, but no camera
3. **Ray-Ban Meta** (69-70g) - looks like standard Ray-Bans, available in multiple styles (Wayfarer, Headliner, etc.), prescription-compatible. The "recording light" LED is visible but subtle.
4. **Envision Ally Solos** (42g) - designed for accessibility, looks like standard glasses, 3 colors
5. **Mentra Live** (43g) - lightweight, normal-looking
6. **Solos AirGo V2** (~45g) - modular design, normal
7. **Brilliant Labs Frame** (39g) - thick colorful frames, looks like fashion glasses but distinctive
8. **Agiga EchoVision** - center-mounted camera is visible
9. **XREAL** (75g) - tinted lenses, clearly tech glasses
10. **NIIRA** - requires pocket processing unit, depth camera visible

**For all-day campus wear by a VI student**: Ray-Ban Meta, Ally Solos, and Mentra Live all pass the "would not look conspicuous in a classroom" test. Ray-Ban Meta has the strongest brand recognition advantage. At 69g, it is heavier than alternatives but within comfortable all-day wear range. 8-hour battery handles a full school day.

---

## 6. Developer Ecosystem Assessment

### Best for EchoEcho (ranked)

**1. Ray-Ban Meta + Wearables DAT**
- Pros: 720p/30fps video stream, best audio, most popular glasses, $299
- Cons: Developer preview only (Dec 2025), publishing restricted to partners for now, no React Native wrapper, BLE bandwidth limits resolution under load
- React Native path: Write native modules wrapping `mwdat-camera` and `mwdat-core` for both iOS (Swift) and Android (Kotlin). The glasses already function as BLE audio devices, so audio output is standard Bluetooth audio.
- Risk: Meta controls the platform and could restrict accessibility use cases

**2. Solos AirGo V2 (or Mentra Live via MentraOS)**
- Pros: WiFi data path means higher bandwidth video, multimodal AI support, open SDK
- Cons: $1,999 SDK fee (Solos), smaller installed base, less mature ecosystem
- React Native path: Solos SDK exposes APIs and webhooks; MentraOS TypeScript SDK could potentially integrate via React Native's JS bridge
- Risk: Both are smaller companies

**3. MentraOS (open source)**
- Pros: MIT license, TypeScript SDK, works across Mentra Live + Even Realities + Vuzix, full camera/mic/speaker access
- Cons: Very new (Feb 2026), small community, uncertain hardware quality
- React Native path: TypeScript SDK is the most natural fit for React Native/Expo
- Risk: Early-stage platform stability

**4. Brilliant Labs Frame**
- Pros: Fully open source, Python/Flutter/Lua SDKs, active developer community
- Cons: No video streaming (3fps stills only), no speaker for audio output, 720x720 crops
- React Native path: Flutter SDK or raw BLE GATT
- Verdict: **Not viable** for real-time video perception pipeline

### BLE GATT and React Native/Expo

For any BLE-connected glasses, the Expo ecosystem supports BLE via:
- `react-native-ble-plx` (Expo config plugin available)
- `react-native-ble-manager`
- Requires EAS dev builds (not Expo Go)
- Physical device required (no simulator BLE)

The Meta DAT would require native module bridges since it provides Kotlin/Swift SDKs only.

---

## 7. Emerging 2026 Hardware

### Apple Smart Glasses (late 2026 announce, early 2027 ship)

- **No display** in first generation (audio + camera + Siri only)
- Dual camera system: one for photos/video, one for environmental context and distance measurement
- All components embedded in frame (no external battery)
- Designed as "all-day AI companion"
- Apple paused next Vision Pro to prioritize glasses
- **Implication for EchoEcho**: If Apple provides a camera streaming API (likely, given their accessibility focus), this becomes the premium option. Apple's accessibility ecosystem (VoiceOver, etc.) is the gold standard. Production starts Dec 2026 at earliest.

### Google/Samsung Android XR Glasses (2026)

- Google partnering with Samsung, Gentle Monster, and Warby Parker
- Two Samsung models in development (SM-O200P, SM-O200J)
- Specs: 12MP camera with autofocus, gesture controls, 155mAh battery, ~50g
- Audio-only version launching alongside display version
- Powered by Qualcomm Snapdragon AR1+ Gen 1 (can run Llama 3.2 1B on-device)
- Android XR SDK Developer Preview 3 already available
- Aira confirmed as partner for VI assistance
- **Implication for EchoEcho**: Android XR SDK will be the standard Android glasses platform. React Native compatibility likely through standard Android APIs. Multiple OEMs will ship compatible glasses, expanding the hardware base.

### Qualcomm Snapdragon AR1+ Gen 1

- Purpose-built for lightweight all-day smart glasses
- Can run 1B parameter LLMs on-device
- 20% thinner temple design vs previous gen
- Improved power efficiency for computer vision and video streaming
- **Implication**: Every major glasses maker will use this or similar silicon, standardizing capabilities

---

## 8. Cost and Funding Pathways

### Device Costs (EchoEcho-relevant options)

| Device | Price | Subscription |
|--------|-------|-------------|
| Ray-Ban Meta Gen 2 | $299 | None |
| Mentra Live | $299 | None |
| Solos AirGo V2 | $299+ | None for hardware |
| Brilliant Labs Frame | $349 | None |
| Envision Ally Solos | $399 | Ally Pro $200/yr (1st year included) |
| Agiga EchoVision | $599 | None (early adopter) |
| OrCam MyEye 3 Pro | ~$4,250 | None |

### Funding Sources for Universities/Students

1. **State Vocational Rehabilitation (VR) agencies**: Every US state has one. Will fund AT if it supports education or employment goals. Can cover smart glasses after evaluation and inclusion in Individualized Plan for Employment (IPE).

2. **Assistive Technology Fund (ATF)**: Covers 50% of retail price of adaptive devices.

3. **University Disability Services**: Most universities have AT budgets. At $299-399 per student for Ray-Ban Meta or Ally Solos, this is comparable to other AT devices already funded.

4. **Lions Clubs International**: Provide vocational assistance and equipment to legally blind individuals.

5. **VA Health Coverage**: Veterans who are legally blind may qualify for device coverage.

6. **ACB Scholarships**: $2,000-$7,500 for legally blind students, can cover AT costs.

7. **State AT Programs (ATAP)**: Offer device loans, reutilized equipment, grants, or low-interest financing.

8. **Medicaid/Medi-Cal**: Classifies AT as "durable medical equipment" with prior authorization.

### Affordability Assessment

At $299 (Ray-Ban Meta), the per-student cost is dramatically lower than traditional VI assistive glasses ($2,500-$4,500). A university providing 20 pairs of Ray-Ban Meta would spend $5,980, well within most disability services budgets. The EchoEcho app itself (on students' own phones) has zero marginal hardware cost.

---

## 9. Recommended Architecture for EchoEcho

### Primary Hardware Target: Ray-Ban Meta Gen 2

**Why:**
- Only glasses with a shipping, documented camera-to-phone streaming SDK
- 720p/30fps is sufficient for VLM inference (most models process at 720p or lower)
- Spatial audio speakers deliver directional navigation cues
- $299 price point is fundable by university disability offices
- 8-hour battery covers a full school day
- Looks like normal glasses (critical for student adoption)
- 69g weight is comfortable for all-day wear
- Be My Eyes integration already validates the VI use case
- 7 million units sold means students may already own them

**Architecture:**
```
Ray-Ban Meta (camera + mic + speakers)
    |-- BLE (720p/30fps video stream) --> Phone (in pocket)
    |                                      |-- VLM inference
    |                                      |-- BLE/IMU positioning
    |                                      |-- Navigation graph
    |-- BLE Audio <------------------------|-- Spatial audio cues
```

**Implementation path:**
1. Write Expo native modules wrapping Meta Wearables DAT for iOS (Swift) and Android (Kotlin)
2. Camera frames received via `mwdat-camera` StreamSession
3. Frames fed to on-device VLM (FastVLM-0.5B or similar) for scene understanding
4. Navigation audio pushed back to glasses as standard BLE audio
5. Audio cues use spatial audio positioning for directional guidance

### Secondary Target: Solos AirGo V2 / MentraOS-compatible glasses

**Why:**
- WiFi data path offers higher bandwidth than BLE
- Open SDK with direct AI integration hooks
- Solos is the hardware partner for Envision Ally Solos (accessibility credibility)
- MentraOS TypeScript SDK has natural React Native affinity

### Future Target: Apple Smart Glasses (2027) and Android XR Glasses (2026)

**Why:**
- Both will have cameras, speakers, and developer APIs
- Apple's accessibility ecosystem guarantees VI support
- Android XR will standardize the glasses companion app pattern
- Multiple OEM hardware options will drive prices down

---

## Sources Consulted

### Product Pages and Documentation
- [Ray-Ban Meta specs](https://www.ray-ban.com/usa/discover-ray-ban-meta-ai-glasses/clp)
- [Meta Wearables Device Access Toolkit FAQ](https://developers.meta.com/wearables/faq/)
- [Meta Wearables DAT Android SDK (GitHub)](https://github.com/facebook/meta-wearables-dat-android)
- [Meta Wearables DAT iOS SDK (GitHub)](https://github.com/facebook/meta-wearables-dat-ios)
- [Meta Wearables DAT Blog Post](https://developers.meta.com/blog/introducing-meta-wearables-device-access-toolkit/)
- [Brilliant Labs Frame Hardware Manual](https://docs.brilliant.xyz/frame/hardware/)
- [Envision Ally Solos](https://www.ally.me/glasses/solos)
- [Envision Ally Solos Launch Blog](https://www.letsenvision.com/blog/ally-solos-glasses)
- [Solos SDK Developer Program](https://solosglasses.com/products/sdk-developer-program)
- [MentraOS GitHub](https://github.com/Mentra-Community/MentraOS)
- [Mentra Live](https://mentraglass.com/live)
- [OrCam MyEye 3 Pro](https://www.orcam.com/en-us/orcam-myeye-3-pro)
- [Agiga EchoVision](https://echovision.agiga.ai/)
- [NIIRA Smart Glasses](https://www.pro.sensotec.com/post/niira-glasses-launch)
- [Even Realities G1](https://www.evenrealities.com/g1)
- [Halliday Glasses](https://hallidayglobal.com/)
- [Vuzix Developer Resources](https://support.vuzix.com/docs/developer-resources)
- [XREAL SDK Docs](https://docs.xreal.com/)

### News and Reviews
- [Meta's Smart Glasses SDK public preview (UploadVR)](https://www.uploadvr.com/meta-wearables-device-access-toolkit-public-preview/)
- [Solos AirGo V2 launch (VentureBeat)](https://venturebeat.com/business/solos-unveils-airgo-a5-and-airgo-v2-smart-glasses-with-hands-free-ai/)
- [Apple Smart Glasses 2026 features (MacRumors)](https://www.macrumors.com/2025/10/02/2026-smart-glasses-features/)
- [Apple Smart Glasses launching 2026 (MacRumors)](https://www.macrumors.com/2025/05/22/apple-smart-glasses-launching-in-2026/)
- [Google Android XR Glasses 2026 (9to5Google)](https://9to5google.com/2025/12/08/android-xr-glasses-displays-2026/)
- [Samsung Smart Glasses 2026 (Next Reality)](https://virtual.reality.news/news/samsung-smart-glasses-launch-2026-with-android-xr/)
- [Qualcomm AR1+ Gen 1 at AWE (The Ghost Howls)](https://skarredghost.com/2025/06/11/snap-spectacles-qualcomm-ar1-plus/)
- [Brilliant Labs Frame Review (Skywork)](https://skywork.ai/blog/brilliant-labs-frame-ai-glasses-review-2025/)
- [Best Smart Glasses for VI 2026 Guide (Hable)](https://www.iamhable.com/en-am/blogs/article/the-best-smart-glasses-for-visually-impaired-people-a-2025-guide)

### Community Discussions
- [AppleVis: Comparison of smart glasses for the blind](https://www.applevis.com/forum/assistive-technology/comparison-all-new-smart-glasses-blind)
- [AppleVis: Envision vs Meta glasses](https://www.applevis.com/forum/assistive-technology/envision-glasses-versus-or-addition-meta-glasses)
- [AppleVis: Be My Eyes on Meta glasses](https://www.applevis.com/forum/assistive-technology/today-be-my-eyes-launches-meta-smart-glasses)
- [AppleVis: Meta glasses community feedback](https://www.applevis.com/forum/assistive-technology/meta-glasses-what-do-people-think)

### Accessibility Partnerships
- [Be My Eyes + Meta partnership expansion](https://www.bemyeyes.com/news/be-my-eyes-and-meta-launch-new-accessibility-functions/)
- [Aira service overview](https://aira.io/)
- [Aira pricing](https://aira.io/pricing/)

### Funding Resources
- [Envision AT Funding Guide](https://www.letsenvision.com/blog/assistive-technology-scholarships-and-grants-in-the-united-states)
- [ACB Funding Resources](https://www.acb.org/content/funding-assistive-technology-resources)
- [ATIA Funding Guide](https://www.atia.org/home/at-resources/what-is-at/resources-funding-guide/)

### Academic / Technical
- [Meta AI glasses and LLMs for VI (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11009354/)
- [AI-powered smart vision glasses (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12178407/)
- [Building multimodal AI for Ray-Ban Meta (Engineering at Meta)](https://engineering.fb.com/2025/03/04/virtual-reality/building-multimodal-ai-for-ray-ban-meta-glasses/)
- [Smart glasses sensor fusion for VI (Electropages)](https://www.electropages.com/blog/2025/05/new-glasses-allows-visually-impaired-people-avoid-obstacles)

---

## Source Quality Assessment

**High confidence**: Ray-Ban Meta specs (official product page + Wikipedia + multiple reviews), Meta DAT SDK (official GitHub repos + developer docs), pricing for all devices (official stores), Apple/Google/Samsung 2026 plans (multiple corroborating sources from MacRumors, 9to5Google, UploadVR, and TrendForce).

**Medium confidence**: Solos AirGo V2 SDK capabilities (official product pages but limited third-party validation), MentraOS capabilities (official docs but platform is very new), audio quality comparisons (review-based, subjective).

**Lower confidence**: Actual BLE video stream latency for Meta DAT (no published benchmarks found), Envision Ally Solos third-party camera access (unclear from available sources), Agiga EchoVision technical architecture (limited documentation).

---

## Open Questions

1. **Meta DAT latency**: What is the actual end-to-end latency from camera capture to frame delivery on the phone? No benchmarks published.
2. **Meta DAT publishing timeline**: When will Meta open publishing beyond select partners? "2026" is the only guidance.
3. **Ally Solos + Solos SDK**: Can a third-party app use the Solos SDK on Ally Solos hardware, or does Envision lock it to their app?
4. **MentraOS camera frame format**: What resolution/format are camera frames delivered in via the TypeScript SDK? Documentation is sparse.
5. **React Native native module complexity**: How much effort to wrap Meta DAT's Kotlin/Swift SDKs for Expo?
6. **Apple accessibility APIs**: Will Apple's smart glasses SDK expose camera streaming to third-party accessibility apps?
7. **Android XR glasses camera API**: Will the Android XR SDK provide a standardized camera streaming interface for companion apps?

---

## Actionable Takeaways

1. **Start with Ray-Ban Meta Gen 2 as primary target hardware.** At $299, it is the most affordable option with proven camera-to-phone streaming. Apply for Meta DAT developer preview access immediately.

2. **Build the Expo native module bridge for Meta DAT early.** This is the highest-risk integration work. Prototype the `mwdat-camera` StreamSession to verify 720p/30fps is achievable under real BLE conditions.

3. **Design the architecture to be glasses-agnostic.** Abstract the "camera frame source" and "audio output sink" so EchoEcho can support Solos AirGo V2, MentraOS glasses, and future Apple/Android XR glasses without architectural changes.

4. **Validate spatial audio on Ray-Ban Meta.** The open-ear speakers support spatial audio positioning. Test whether directional navigation cues ("obstacle on your left") can be delivered with perceptible spatialization.

5. **Investigate Solos SDK as secondary path.** The $1,999 dev kit is a reasonable investment. WiFi data streaming avoids BLE bandwidth constraints and may deliver higher resolution frames.

6. **Monitor Apple and Android XR announcements closely.** Both platforms will launch in 2026, potentially with purpose-built accessibility APIs. EchoEcho should be ready to support them at launch.

7. **Engage university disability offices early on funding.** At $299/pair, Ray-Ban Meta is comparable to other funded AT devices. Prepare a funding justification template that disability offices can use with VR agencies.

8. **Consider Aira SDK as human-in-the-loop fallback.** For situations where AI navigation confidence is low, escalating to a human Aira agent provides a safety net that VI users already trust.
