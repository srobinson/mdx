---
title: EchoEcho Technical Feasibility - Haptic/Audio Navigation for Visually Impaired (React Native + Claude Haiku)
type: research
tags: [react-native, accessibility, haptic-feedback, visually-impaired, pedestrian-dead-reckoning, claude-haiku, navigation, IMU, sensors]
summary: The core stack is technically buildable but the pitch significantly underestimates timeline, overestimates LLM suitability for real-time navigation, and has a critical gap in PDR accuracy without correction infrastructure.
status: active
source: deep-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

The proposed EchoEcho stack (React Native + Claude Haiku + phone IMU + haptic feedback) is technically feasible as a proof-of-concept but contains three serious design risks. First, Claude Haiku is unsuitable for real-time turn-by-turn correction -- 0.6-1.2s TTFT is too slow for reactive navigation and offline fallback is entirely absent from the pitch. Second, smartphone-only pedestrian dead reckoning accumulates 1-5% positional error per distance traveled, meaning a 200m walk without GPS correction will have 2-10m of positional error -- unacceptable for a VI user at an intersection. Third, the "Week 1-2 functional prototype" timeline is implausible when accessibility-first development, sensor integration, and reliable haptic pattern encoding are each multi-week engineering efforts.

The good news: React Native's accessibility APIs are mature enough, the haptic pattern encoding scheme (1/2/3 buzzes) is technically achievable, and the IMU polling rates are sufficient. The problems are systemic architecture choices, not implementation details.

---

## Detailed Findings

### 1. React Native Accessibility APIs

**Maturity level: Adequate but requires disciplined implementation.**

React Native exposes a solid accessibility surface: `accessibilityLabel`, `accessibilityRole`, `accessibilityValue`, `accessibilityHint`, and `AccessibilityInfo` for announcing dynamic content changes. These map correctly to both VoiceOver (iOS) and TalkBack (Android).

**Platform character differences:**

- VoiceOver (iOS) is strict and unforgiving. If the accessibility tree is malformed, cluttered, or incorrectly grouped, VoiceOver exposes every mistake to the user. iOS favors explicit semantic structure; you cannot rely on layout inference.
- TalkBack (Android) is more forgiving, attempting to infer meaning when `accessibilityProps` are vague. This masks developer errors during testing but creates inconsistent experiences in production.

**The most consequential known pain point** for a navigation app is focus management during screen transitions. When a user triggers navigation and presses back, screen reader focus resets to the first element on the previous screen rather than restoring to the triggering element. This is a documented bug in `react-navigation` with open issues as recently as 2024 (issues [#11189](https://github.com/react-navigation/react-navigation/issues/11189), [#12724](https://github.com/react-navigation/react-navigation/issues/12724), and [#10468](https://github.com/react-navigation/react-navigation/issues/10468)). For a VI user in the middle of navigation, unexpected focus jumps are a safety concern, not a UX annoyance.

**RN vs native Swift/Kotlin for VI-first apps:**

Native Swift has direct access to `UIAccessibility` and AVSpeechSynthesizer at zero abstraction cost. UIKit's accessibility model is more composable for custom interaction patterns. React Native's JS bridge adds a layer of indirection that can introduce timing issues in accessibility announcements -- the `accessibilityLiveRegion` equivalent (`AccessibilityInfo.announceForAccessibility`) can fire at unexpected times when the JS thread is busy.

The practitioner consensus from the HN thread ([How I, as someone who is VIsually impaired, use my iPhone](https://news.ycombinator.com/item?id=27302074)) is unambiguous: Apple's VoiceOver is best-in-class, quadriplegic users described it as unmatched in the consumer electronics space, and custom UI libraries that bypass the native accessibility tree (canvas-based rendering, some cross-platform frameworks) are genuinely dangerous for VI users. React Native is not in the "dangerous" category here -- it does use native accessibility primitives -- but it requires more deliberate work than native Swift to get right.

**Bottom line for VI-first:** React Native can work, but every navigation event, every dynamic content change, and every screen transition requires explicit accessibility handling. It cannot be retrofitted. A solo developer who has not built accessible RN apps before should budget 30-50% of their development time on accessibility testing and fixes alone.

---

### 2. React Native Haptic Feedback

**1/2/3 buzz encoding: Technically achievable on both platforms with the right library.**

The ecosystem has three meaningful options:

| Library | Custom Patterns | iOS Engine | Android Engine | Notes |
|---|---|---|---|---|
| `expo-haptics` | No | Taptic Engine | Vibrator API | Preset only: impact, notification, selection |
| `react-native-haptic-feedback` | Limited | UIFeedbackGenerator | Vibration API | Named preset types only |
| `react-native-haptic-patterns` | Yes | Core Haptics (iOS 13+) | Vibration API | Millisecond-level timing control |

For the 1/2/3 buzz encoding scheme, `react-native-haptic-patterns` (by SimformSolutionsPvtLtd) is the only viable choice. It exposes a `RecordedEventType` interface with `{ startTime: number, endTime: number, isPause: boolean }` millisecond-precision event arrays. A three-buzz "turn right" pattern could be defined as:

```
[
  { startTime: 0,   endTime: 120, isPause: false },
  { startTime: 120, endTime: 220, isPause: true  },
  { startTime: 220, endTime: 340, isPause: false },
  { startTime: 340, endTime: 440, isPause: true  },
  { startTime: 440, endTime: 560, isPause: false }
]
```

**iOS vs Android gap is meaningful:**

On iOS, Core Haptics (Taptic Engine) provides nuanced, amplitude-controlled pulses that are genuinely distinct in tactile character. On Android, the Vibration API drives a motor -- simpler, louder, less precise. The qualitative feel of "1 vs 2 vs 3 buzzes" will be perceptibly different between platforms. More critically, iOS Taptic Engine is silenced under Low Power Mode, during camera use, and during dictation. For a VI navigation app that will also use voice input, the dictation condition is a real conflict: if the user is speaking a destination command, haptics will not fire. This needs a design workaround (e.g., stop voice recognition before delivering haptic confirmation).

**Android 12+ rate limit:** Starting with API level 31, Android caps sensor and vibration callbacks at 200ms minimum intervals without the `HIGH_SAMPLING_RATE_SENSORS` permission. For vibration patterns this is less critical, but it is worth noting for the sensor integration below.

**Distinguishability concern:** The 1/2/3 buzz scheme requires the user to accurately count pulses under stress, mid-walk, potentially with street noise. This is a significant usability assumption that should be validated with actual VI users before committing to it as the primary navigation language. Established VI navigation tools (Sunu wristband, [YC S17](https://news.ycombinator.com/item?id=14867312)) use continuous sonar feedback rather than discrete coded patterns precisely because counting pulses under navigation load is cognitively demanding.

---

### 3. Sensor Access in React Native

**IMU access: Functional. Polling rates: Adequate for pedestrian step detection. Limitations matter.**

Two primary libraries:

- **`expo-sensors`**: Unified access to accelerometer, gyroscope, magnetometer, barometer, and pedometer. Configurable via `setUpdateInterval()`. Minimum practical interval is ~16ms (60Hz). The library has a documented cross-platform inconsistency: accelerometer X and Y axis directions are inverted between iOS and Android (GitHub [issue #19229](https://github.com/expo/expo/issues/19229)), requiring normalization in application code.

- **`react-native-sensors`**: RxJS-based reactive API. Default 100ms update interval, configurable to lower values with the appropriate Android permission.

**For pedestrian dead reckoning specifically:**

- Step detection requires ~20-50Hz accelerometer sampling. Both libraries can achieve this.
- Heading estimation via gyroscope + magnetometer fusion requires 50-100Hz.
- The Android 12+ `HIGH_SAMPLING_RATE_SENSORS` permission is required if targeting sub-200ms intervals.

The sensor data itself is available. The accuracy limitations are in the physics, not the API.

---

### 4. LLM Latency for Real-Time Navigation

**Claude Haiku is the wrong tool for turn-by-turn correction. It is the right tool for pre-trip route generation.**

**Quantitative latency:**

Claude 4.5 Haiku (current as of 2026) achieves:
- Time to First Token: 0.60s median (Google Vertex: 0.63s, Anthropic direct: 0.72s)
- Output speed: 93.7 tokens/second
- End-to-end for a 500-token response: approximately 5-6 seconds

For comparison, Claude 3 Haiku was 1.17s TTFT; Claude 3.5 Haiku was 2.1-2.4s TTFT. The trend is improving.

**The navigation problem:** Turn-by-turn corrections require sub-200ms response from the moment a user deviates from a route to the moment they receive a corrective haptic. A 0.6s TTFT plus network round-trip plus any prompt processing overhead puts Haiku-mediated corrections in the 800ms-2s range. For a pedestrian crossing a street, 2 seconds is the difference between a correction that is useful and one that arrives after the decision point has passed.

**Connectivity drops are unaddressed in the pitch.** A VI user navigating outdoors in a campus environment will encounter dead zones, tunnels, and building shadow. No offline fallback is described. This is a safety gap, not a UX gap.

**Recommended architecture:**

1. **Pre-trip (LLM-appropriate):** Use Claude Haiku to generate a structured route plan -- waypoint list, landmark descriptions, turn instructions -- before navigation begins. This is well within Haiku's capabilities and latency is acceptable for a one-time pre-computation. Store the route locally.

2. **In-trip corrections (LLM-inappropriate):** Use deterministic geometry on the pre-computed route. Compare current IMU-estimated position against the nearest waypoint. Trigger haptic correction based on heading deviation threshold (e.g., >15 degrees off bearing for more than 3 steps). No LLM call needed mid-trip.

3. **Re-routing (LLM-acceptable with caveats):** If the user wanders significantly off route, trigger a Haiku re-route call. This is acceptable latency because the user is already stopped or disoriented. But it requires connectivity.

This architecture preserves Haiku's genuine value (natural language destination understanding, smart route description) without relying on it for the real-time loop.

---

### 5. Pedestrian Dead Reckoning Accuracy

**Honest error bounds: 1-5% of traveled distance, compounding without external correction.**

The published literature provides these figures:

- **Best-case (research-grade PDR with sensor fusion):** 0.3-0.9% of total path distance. A 2023 study with ZUPT (zero-velocity update) + magnetometer fusion achieved average positioning error ~0.77m on an ~80m test course.
- **Typical smartphone-based PDR (pocket-worn, sensor fusion):** 1.2-2.5m RMS error on ~80m courses, or roughly 1.5-3% of distance.
- **Without magnetometer / heading correction:** Error grows faster due to gyroscope drift. 3-5% of distance is realistic.
- **Extended distances (200m+):** Error accumulates non-linearly. A 500m walk with 2% distance error gives 10m of positional uncertainty. At an unsignalized intersection, 10m is catastrophic for a VI user.

**What this means practically:**

- For a 50m route segment: 0.5-2.5m error -- manageable, orientation guidance still useful.
- For a 100m route segment: 1-5m error -- getting into dangerous territory at intersections.
- For a 500m route without GPS correction: 5-25m error -- unusable for independent navigation.

**Correction strategies without external infrastructure:**

- **GPS (outdoor):** Obvious but inconsistent in urban canyons, campus building clusters, and indoor corridors.
- **Magnetic field fingerprinting (indoor):** Floor/building-specific maps required, high setup cost.
- **WiFi/BLE positioning:** Requires installed infrastructure (beacons). Not available on arbitrary campuses.
- **Step counting + map snapping:** If the route is pre-computed and constrained to known paths, you can snap PDR estimates to the nearest path segment, limiting accumulated error. This is the most viable low-infrastructure correction strategy.
- **ARCore/ARKit SLAM (outdoor/indoor):** Visual-inertial odometry using the camera provides significantly better positioning than IMU alone. ARCore's VPS (Visual Positioning System) achieves sub-meter accuracy outdoors at mapped locations. For a campus navigation use case, this is a strong candidate for the correction layer.

**ARKit/ARCore viability assessment:**

Research (ARIANNA+, ANSVIP) demonstrates ARCore-based navigation for VI users achieving usable accuracy. ARKit's visual-inertial odometry combines camera and IMU, which is substantially better than IMU alone. The practical constraint: the camera must be held up (not pocket-worn), battery drain is higher, and it fails in low-light. For outdoor campus navigation in daylight, ARCore/ARKit SLAM as the position source -- with haptics as the output channel -- is architecturally superior to IMU-only PDR. However, it substantially increases implementation complexity.

---

### 6. Alternative Technical Approaches

**Native app (Swift/Kotlin):**

The accessibility argument for native Swift is genuine. Direct `UIAccessibility` access, tighter integration with VoiceOver's focus model, and access to Apple's Foundation Models framework (on-device LLM, announced WWDC 2025) without the JS bridge overhead. The trade-off is single-platform (iOS only, or double the development cost). For a solo developer validating a concept, React Native is the pragmatic choice despite its accessibility quirks -- with the important caveat that the developer must be prepared to hand-tune every accessibility interaction.

**On-device models:**

`react-native-executorch` (from Software Mansion, published 2025) enables running LLMs like Llama locally on device. For route generation from a voice command, an on-device model eliminates the connectivity dependency entirely. The trade-off: 3-7B parameter models large enough to understand natural language destinations are 2-4GB on-disk and require mid-range to high-end phones (A14 Bionic, Snapdragon 8 Gen 2 or newer). Whisper runs well on-device via `whisper.rn` (tiny/base models), making fully offline voice-to-route generation technically plausible on 2023+ devices.

Apple's Foundation Models Framework (iOS 18.1+, WWDC 2025) is the most compelling option for iOS: on-device, private, fast, and maintained by Apple. But it is iOS-only and requires iOS 18.1+ (limiting the device target).

**Hybrid recommended architecture:**

```
Voice input  →  on-device Whisper STT  →  Claude Haiku API (route pre-generation)
                                                    ↓
                                        Structured route stored locally
                                                    ↓
                    ARCore/GPS position  →  deterministic navigation loop
                                                    ↓
                                    Haptic patterns via react-native-haptic-patterns
```

This eliminates LLM latency from the critical navigation path while preserving it for the one task it is genuinely good at.

---

### 7. Prototype Timeline Reality Check

**"Week 1-2: functional prototype" is not credible for an accessibility-first navigation app.**

A general React Native MVP with no accessibility requirements can be assembled in 1-2 weeks by an experienced developer. That is the evidence base the pitch seems to be drawing from. But an accessible navigation app with sensor integration, haptic pattern encoding, and VI testing is categorically different.

Realistic minimum timeline for a solo developer who knows React Native:

| Phase | Realistic Duration | Notes |
|---|---|---|
| React Native project setup, Expo config, sensor permissions | 2-3 days | Straightforward |
| Voice input (STT) + Haiku route generation | 3-5 days | Including prompt engineering for structured output |
| Haptic pattern implementation and device testing | 3-5 days | iOS/Android normalization, Low Power Mode edge cases |
| IMU integration + basic step detection | 4-7 days | Sensor fusion, axis normalization, noise filtering |
| Route following logic (deterministic geometry) | 5-7 days | Bearing calculation, waypoint matching, deviation detection |
| Accessibility audit and VoiceOver/TalkBack fixes | 5-10 days | This consistently expands. Cannot be estimated tightly. |
| **Total minimum** | **22-37 days** | Approximately 4-8 weeks |

This is for a functional prototype, not a production-ready app. "Functional" means: a real VI user can enter a destination, receive a pre-generated route, and follow haptic guidance for a short (under 100m) outdoor route with GPS assistance.

Without GPS correction (IMU-only as the pitch implies), the prototype will have accuracy problems on routes longer than 50-80m that no amount of software polish can fix.

**The biggest underestimation in the pitch:** Accessibility testing with actual VI users requires access to VI users. Finding testers, scheduling sessions, and iterating on feedback is not free and is not fast. The pitch treats it as implicit.

---

## Sources Consulted

**Official documentation:**
- [React Native Accessibility Docs](https://reactnative.dev/docs/accessibility)
- [Expo Haptics SDK](https://docs.expo.dev/versions/latest/sdk/haptics/)
- [Expo Sensors SDK](https://docs.expo.dev/versions/latest/sdk/sensors/)
- [Claude Latency Reduction Docs](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-latency)

**Performance benchmarks:**
- [Artificial Analysis: Claude 4.5 Haiku](https://artificialanalysis.ai/models/claude-4-5-haiku) -- TTFT 0.60s, 93.7 t/s
- [Artificial Analysis: Claude 3.5 Haiku providers](https://artificialanalysis.ai/models/claude-3-5-haiku/providers)

**Libraries:**
- [react-native-haptic-patterns (SimformSolutionsPvtLtd)](https://github.com/SimformSolutionsPvtLtd/react-native-haptic-patterns)
- [react-native-haptic-feedback (mkuczera)](https://github.com/mkuczera/react-native-haptic-feedback)
- [react-native-executorch](https://docs.swmansion.com/react-native-executorch/)
- [expo-speech-recognition](https://github.com/jamsch/expo-speech-recognition)

**Academic / research:**
- [Robust PDR Based on MEMS-IMU for Smartphones (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5982656/) -- 1.1-2.5m RMS on 80m courses
- [Smartphone-Based PDR Integrated with VLP (arXiv)](https://arxiv.org/abs/2301.03471) -- 0.5m accuracy with external correction
- [Indoor PDR + Magnetic Field Matching (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6308508/)
- [ARCore Navigation for VI Users (MDPI)](https://www.mdpi.com/2076-3417/9/5/989)
- [ARIANNA+ ARKit navigation for blind (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8125605/)

**Known bugs / community:**
- [react-navigation focus reset issue #11189](https://github.com/react-navigation/react-navigation/issues/11189)
- [react-navigation accessibility issue #12724](https://github.com/react-navigation/react-navigation/issues/12724)
- [expo-sensors axis inconsistency #19229](https://github.com/expo/expo/issues/19229)
- [HN: How a VI user uses iPhone (2021)](https://news.ycombinator.com/item?id=27302074)
- [HN: Sunu haptic wristband for blind navigation (YC S17)](https://news.ycombinator.com/item?id=14867312)

**Engineering blogs:**
- [LogRocket: Customizing haptic feedback in RN](https://blog.logrocket.com/customizing-haptic-feedback-react-native-apps/)
- [Callstack: React Native Accessibility](https://www.callstack.com/blog/react-native-accessibility)
- [Expo blog: Running AI models with react-native-executorch](https://expo.dev/blog/how-to-run-ai-models-with-react-native-executorch)
- [DEV: Offline AI on Mobile with Whisper + LLMs](https://dev.to/ujja/offline-ai-on-mobile-tackling-whisper-llms-and-size-roadblocks-2lb7)

---

## Source Quality Assessment

**High confidence:** LLM latency numbers (multiple independent benchmark sources with consistent results), haptic library capabilities (directly verifiable from GitHub/npm), React Native accessibility bug reports (open GitHub issues with reproduction steps), PDR error bounds (peer-reviewed sensor research).

**Medium confidence:** PDR error extrapolation beyond published test distances (published studies top out at ~100-200m; 500m extrapolation is modeled from observed error growth rates, not directly measured). Timeline estimates (based on practitioner consensus, not controlled studies).

**Low confidence:** ARCore/ARKit accuracy outdoors on a specific campus (highly environment-dependent; published results are from mapped locations). On-device LLM model quality for destination understanding on small models.

**Gaps:** No direct comparative study of React Native vs native Swift for VI navigation apps exists. Timeline estimates for accessibility-specific development are scarce -- most RN MVP timelines in the literature are for non-accessible apps.

---

## Open Questions

1. Does the target user population primarily use iOS or Android? If iOS-primary, the Apple Foundation Models Framework + native Swift path becomes more compelling given Apple's accessibility leadership.

2. Is the campus environment GPS-accessible outdoors? If yes, GPS + map snapping eliminates the PDR accuracy problem entirely for outdoor use. PDR then becomes a backup, not the primary.

3. Has any VI user testing been conducted? The 1/2/3 buzz encoding scheme is a hypothesis, not a validated interaction model. Research on tactile language for navigation suggests simpler is not always better -- continuous directional feedback often outperforms discrete coded patterns.

4. What is the geographic scope? A constrained campus (50-200m routes, known paths) is an entirely different engineering problem from city-scale pedestrian navigation. The former is achievable with GPS + map snapping; the latter requires significantly more infrastructure.

5. What model size is acceptable for on-device route generation? Llama 3.2 1B can run on a Pixel 7 but may not parse natural language destinations reliably. Llama 3.2 3B is better but is a 2GB download. This is a product decision with UX implications.

---

## Actionable Takeaways

1. **Replace the real-time LLM correction loop with deterministic geometry.** Pre-generate the route with Haiku, store it locally, navigate with bearing math. Reserve Haiku calls for route generation and re-routing only.

2. **Add GPS as the primary position source outdoors.** IMU/PDR alone cannot provide VI-safe accuracy at distances above 80m without external correction. React Native has good GPS access via `expo-location`. Use GPS for position, PDR only as fallback when GPS signal is lost.

3. **Switch from `expo-haptics` to `react-native-haptic-patterns`** for the 1/2/3 buzz encoding. `expo-haptics` does not support custom sequences. This is a direct library substitution.

4. **Test the buzz encoding scheme with VI users before building around it.** If the encoding is cognitively confusing under navigation stress, the whole interaction model needs to change. Do this in week 1, not week 8.

5. **Revise the prototype timeline to 6-8 weeks minimum.** Budget specifically for: (a) iOS/Android haptic normalization, (b) VoiceOver/TalkBack testing and bug fixing, (c) at least two VI user testing sessions.

6. **Add an offline mode.** Store the pre-generated route as a local data structure. If connectivity drops, the navigation loop continues from stored waypoints. Haiku calls happen only with connectivity available.

7. **Consider `react-native-executorch` + on-device Whisper** as a longer-term replacement for cloud STT + Haiku for destination input. This eliminates the connectivity dependency for the most safety-critical part of the user flow. Not week 1-2 work, but a clear architectural direction to design toward.
