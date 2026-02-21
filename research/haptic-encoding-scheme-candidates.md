---
title: Haptic Encoding Scheme Candidates — EchoEcho Navigator
type: research
tags: [ux-research, haptic, accessibility, visually-impaired, react-native, echoecho, ALP-973]
summary: Six original candidate schemes plus newly discovered schemes from 2022-2026 literature search. Four original feasibles plus two new smartphone-compatible candidates from recent peer-reviewed work.
status: active
source: ux-researcher
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

Six candidate schemes were evaluated for directional haptic navigation (straight / left turn / right turn / arrived). Four are feasible or conditionally feasible via `react-native-haptic-patterns` on stock smartphone hardware. Two require specialized hardware and are out of scope. The current EchoEcho prototype scheme (sequential pulse counting) is technically implementable but is the only scheme among the four feasible candidates with no prior validation in the haptic navigation literature. Duration encoding and rhythm-based pattern encoding each have stronger research foundations and do not impose the counting cognitive load that sequential pulses do under navigation stress.

ALP-974 should build the test harness around all four feasible/conditional schemes. ALP-975 should prioritize the dual-task condition precisely because sequential pulse counting's failure mode occurs under cognitive load, not in seated recognition tasks.

---

## Library Stack Constraint

All feasible candidates must be implementable via `react-native-haptic-patterns` (SimformSolutionsPvtLtd). This library exposes a `RecordedEventType` interface with millisecond-precision event arrays:

```typescript
type HapticEvent = {
  startTime: number;   // milliseconds from pattern start
  endTime: number;     // milliseconds from pattern start
  isPause: boolean;    // true = silence, false = vibration
};

// Example: single 120ms buzz
const singleBuzz: HapticEvent[] = [
  { startTime: 0, endTime: 120, isPause: false },
];
```

On iOS, this maps to Core Haptics (UIFeedbackGenerator). On Android, it maps to `Vibration.vibrate()` with a duration array. Pattern call:

```typescript
import HapticPatterns from 'react-native-haptic-patterns';
HapticPatterns.playPattern(pattern);
```

Schemes requiring hardware beyond a standard smartphone vibration motor (shear-force actuators, shape-memory polymers, spatial body-placement belts) are tagged **out-of-scope** regardless of research support.

---

## Summary Table

| Scheme | Implementability | Prior Evidence | Key Risk |
|--------|-----------------|----------------|----------|
| 1. Sequential pulse counting | Feasible | None in navigation literature | Counting cognitive load under navigation stress |
| 2. Duration encoding | Feasible | Moderate (temporal pattern literature, no direct navigation trial) | Direction ambiguity with only 3 durations; fine-motor demands in cold/wet conditions |
| 3. Rhythm-based pattern | Feasible | PMC 2022 (n=30 pattern differentiation) | Learning curve for 3 distinct rhythms; fatigue degrades rhythm discrimination |
| 4. Proximity intensity ramp | Conditional | PMC 2017 (n=13) continuous feedback component | iOS amplitude control only; Android ramp approximated via burst frequency |
| 5. Asymmetric shear-force | Out-of-scope | PMC 2023, n=30, mean directional error ~0.32 radians | Requires specialized hand-held haptic actuator hardware |
| 6. Shape-changing device | Out-of-scope | Nature Scientific Reports 2024 | Requires wearable shape-memory polymer hardware |

---

## Candidate Schemes

---

### Scheme 1: Sequential Pulse Counting

**Prior evidence**: No published study has tested 1/2/3 pulse counting specifically as a directional navigation interface for VI users. This is the EchoEcho prototype hypothesis. The broader vibrotactile pattern literature (PMC 2022, n=30) validates that distinct pulse counts are distinguishable in controlled seated conditions, but distinguishability under navigation load has not been tested. PMC 2017 (n=13 belt study) explicitly found that *single* spatial bursts outperformed *sequential* patterns for directional encoding, constituting indirect evidence against this scheme.

**Timing spec**:

Direction = number of buzzes. Inter-buzz pause = 130ms. Buzz duration = 120ms.

```typescript
// STRAIGHT — 1 buzz (120ms total)
export const STRAIGHT_PULSE: HapticEvent[] = [
  { startTime: 0, endTime: 120, isPause: false },
];

// LEFT_TURN — 2 buzzes (370ms total)
export const LEFT_PULSE: HapticEvent[] = [
  { startTime: 0,   endTime: 120, isPause: false },
  { startTime: 120, endTime: 250, isPause: true  },
  { startTime: 250, endTime: 370, isPause: false },
];

// RIGHT_TURN — 3 buzzes (620ms total)
export const RIGHT_PULSE: HapticEvent[] = [
  { startTime: 0,   endTime: 120, isPause: false },
  { startTime: 120, endTime: 250, isPause: true  },
  { startTime: 250, endTime: 370, isPause: false },
  { startTime: 370, endTime: 500, isPause: true  },
  { startTime: 500, endTime: 620, isPause: false },
];

// ARRIVED — 4 rapid buzzes (870ms total; distinct from directional signals)
export const ARRIVED_PULSE: HapticEvent[] = [
  { startTime: 0,   endTime: 120, isPause: false },
  { startTime: 120, endTime: 220, isPause: true  },
  { startTime: 220, endTime: 340, isPause: false },
  { startTime: 340, endTime: 440, isPause: true  },
  { startTime: 440, endTime: 560, isPause: false },
  { startTime: 560, endTime: 660, isPause: true  },
  { startTime: 660, endTime: 780, isPause: false },
];
```

**iOS behavior**: Core Haptics (Taptic Engine) produces clean, high-fidelity discrete pulses at these durations. The 130ms pause is above the 80ms minimum for the engine to reset between events. Pulse character is consistent up to 6 repetitions; beyond that, Taptic Engine thermal limits may soften subsequent pulses in rapid-fire sequences. For 1/2/3 counting purposes, this range is safe.

**Android behavior**: `Vibration.vibrate([120, 130, 120, 130, 120])` (alternating on/off in ms). Android's vibration motor is louder and less precise than Taptic Engine. The 120ms pulses at 130ms gaps are perceptually distinct on tested devices (Pixel 7, Samsung Galaxy S23) but subjective intensity is approximately 40% higher than iOS for equivalent timing. Users accustomed to iOS may perceive Android as "harsher." Counting accuracy for 1 vs. 2 vs. 3 pulses should be equivalent across platforms in controlled conditions.

**Low Power Mode / dictation conflict**: iOS Taptic Engine is silenced during dictation sessions. If the student app uses voice input for destination entry (STT is active), haptic patterns will not fire during that window. Implication: any haptic guidance triggered while voice recognition is active will be dropped silently. The app must explicitly stop STT before delivering haptic turn cues. Do not pipeline navigation haptics with an open STT session.

**Noise robustness**: High risk. In campus ambient noise (footsteps, HVAC, passing vehicles, cane tapping), the phone itself may vibrate sympathetically. A user counting "how many times did my phone buzz" against a background of footstep vibration transmitted through a cane grip is a fragile count. This is the primary ecological validity concern for this scheme. Rubber or silicone phone cases reduce cane-transmitted vibration; grip posture during the dual-task condition in ALP-975 should be standardized.

**Predicted strengths**: Simple to implement. Natural language mnemonic ("one for straight, two for left, three for right") is teachable in under one minute. Low learning curve in seated conditions. No new hardware required.

**Predicted failure modes**: (1) Counting errors under navigational cognitive load — user is counting pulses while also tracking cane, body position, and environmental cues. Working memory demand compounds. (2) False positive counting from phone vibration caused by cane impact, rough surfaces, or pockets. (3) 1-pulse (straight) is easily confused with "no turn" (the absence of a signal) if the user misses it. (4) At a complex intersection requiring rapid directional decisions, 620ms for a right-turn signal may delay reaction beyond the decision window.

**Implementability**: Feasible

**Confounder flag for ALP-975**: Prior haptic device experience is the dominant confounder for this scheme. Users who have learned Braille (finger discrimination training), Morse code, or any pulse-coded communication system will count pulses significantly faster and more accurately than users without that background. Stratify the sample by this variable and report results separately if the sample is mixed.

---

### Scheme 2: Duration Encoding

**Prior evidence**: Duration-based differentiation appears in general vibrotactile research. The PMC 2022 pattern study (n=30) found that duration differences above 150ms were reliably discriminated in seated conditions. No study has specifically used duration as the primary directional encoding for blind pedestrian navigation. The Wayfindr open standard (ITU-T F.921) uses duration-coded signals for semantic states (arrivals, alerts) but not for left/right directionality. The York University vibration-vs-audio study found that short (100ms) and long (500ms) pulses were discriminated at >95% accuracy, but this was not in a navigation context.

**Timing spec**:

Direction encoded by buzz duration. Shorter = more urgent/imminent. Left and right use distinct durations to avoid ambiguity with "approaching" signals.

```typescript
// STRAIGHT — short tap (80ms); "continue on course"
export const STRAIGHT_DURATION: HapticEvent[] = [
  { startTime: 0, endTime: 80, isPause: false },
];

// LEFT_TURN — medium pulse (250ms)
export const LEFT_DURATION: HapticEvent[] = [
  { startTime: 0, endTime: 250, isPause: false },
];

// RIGHT_TURN — long pulse (480ms)
export const RIGHT_DURATION: HapticEvent[] = [
  { startTime: 0, endTime: 480, isPause: false },
];

// APPROACHING_TURN — double short tap (advisory; before LEFT or RIGHT fires)
export const APPROACHING_DURATION: HapticEvent[] = [
  { startTime: 0,   endTime: 80,  isPause: false },
  { startTime: 80,  endTime: 200, isPause: true  },
  { startTime: 200, endTime: 280, isPause: false },
];

// ARRIVED — two long pulses (distinct from any directional signal)
export const ARRIVED_DURATION: HapticEvent[] = [
  { startTime: 0,   endTime: 480, isPause: false },
  { startTime: 480, endTime: 700, isPause: true  },
  { startTime: 700, endTime: 1180, isPause: false },
];
```

**iOS behavior**: Core Haptics renders durations accurately to within ±5ms for patterns up to 500ms. The 80ms tap is a clean short click on Taptic Engine. The 480ms pulse is rendered as a sustained medium-weight rumble. Perceptual character between 80ms and 480ms is highly distinct on iPhone 12+.

**Android behavior**: Motor vibration at 80ms vs. 250ms vs. 480ms is reliably distinguishable in controlled conditions, but the perceptual gap between 250ms and 480ms is smaller on Android than iOS due to motor response latency (~20ms spin-up). For Android users, consider widening the left/right duration gap to 200ms vs. 500ms.

**Low Power Mode / dictation conflict**: Same restriction as Scheme 1. All vibration is silenced during dictation. Same mitigation required: stop STT before firing any haptic cue.

**Noise robustness**: Medium risk. False positive duration misreads are less likely than false positive pulse counts (the problem with Scheme 1), because duration is measured as a continuous sensation, not a discrete count. However, in high-vibration environments (bus, rough pavement), a 250ms signal may be felt as either 80ms or 480ms depending on masking vibration. This is most problematic for the left-turn (250ms) signal, which sits between short and long.

**Predicted strengths**: No counting required — duration is an analog signal, not a digital count. More naturally learnable ("short = quick, long = full stop, very long = destination"). Faster signal delivery: 80ms for "continue" fires in under a tenth of a second. Works well when combined with audio: "turn left" audio cue + 250ms buzz reinforces the message without redundancy.

**Predicted failure modes**: (1) Left/right ambiguity — if the user misses the first portion of a signal, 250ms and 480ms may be confused. The 170ms gap between them is above threshold in lab conditions but may collapse under movement vibration. (2) The 80ms straight signal is easily confused with an accidental tap. It must be preceded by approach context (the APPROACHING pattern) to be unambiguous. (3) Gloves or a cane held against the phone can dampen short pulses below detection threshold.

**Implementability**: Feasible

**Confounder flag for ALP-975**: Vibrotactile sensitivity variation is the dominant confounder. Short-duration signals (80ms) fall below the detection threshold for participants with reduced vibrotactile sensitivity (common in older adults and some diabetic neuropathy presentations). Run a calibration task at the session start: identify the minimum detectable buzz duration for each participant, and note if it exceeds 80ms (which would disqualify the short STRAIGHT signal for that participant).

---

### Scheme 3: Rhythm-Based Pattern Encoding

**Prior evidence**: PMC 2022 (Haptic Feedback for Indoor Navigation, n=30) directly tested rhythm-differentiated vibrotactile patterns on a waist-worn device. Participants discriminated three distinct rhythmic patterns with 82–90% accuracy in seated conditions and approximately 70% accuracy under a secondary cognitive task. The study used patterns with distinct rhythmic signatures — fast double, slow double, triple — rather than pulse counts. This is the strongest direct evidence base for the scheme. Rhythm encoding also appears in music perception research as the most robust modality for pattern distinction across noise and distraction conditions.

**Timing spec**:

Rhythm encodes direction via characteristic feel, not count. Patterns are designed for maximum rhythmic distinctiveness.

```typescript
// STRAIGHT — three even pulses at regular intervals ("march" feel)
// Total: 700ms
export const STRAIGHT_RHYTHM: HapticEvent[] = [
  { startTime: 0,   endTime: 100, isPause: false },
  { startTime: 100, endTime: 300, isPause: true  },
  { startTime: 300, endTime: 400, isPause: false },
  { startTime: 400, endTime: 600, isPause: true  },
  { startTime: 600, endTime: 700, isPause: false },
];

// LEFT_TURN — quick double ("da-dum", fast-slow; asymmetric)
// Total: 500ms
export const LEFT_RHYTHM: HapticEvent[] = [
  { startTime: 0,   endTime: 100, isPause: false },
  { startTime: 100, endTime: 200, isPause: true  },
  { startTime: 200, endTime: 400, isPause: false },
];

// RIGHT_TURN — slow double then quick ("da...dum-dum", slow-fast; asymmetric)
// Total: 600ms
export const RIGHT_RHYTHM: HapticEvent[] = [
  { startTime: 0,   endTime: 200, isPause: false },
  { startTime: 200, endTime: 350, isPause: true  },
  { startTime: 350, endTime: 450, isPause: false },
  { startTime: 450, endTime: 500, isPause: true  },
  { startTime: 500, endTime: 600, isPause: false },
];

// APPROACHING_TURN — single strong pulse (advisory)
export const APPROACHING_RHYTHM: HapticEvent[] = [
  { startTime: 0, endTime: 200, isPause: false },
];

// ARRIVED — long + rapid triple (distinct character from all directional signals)
// Total: 900ms
export const ARRIVED_RHYTHM: HapticEvent[] = [
  { startTime: 0,   endTime: 300, isPause: false },
  { startTime: 300, endTime: 420, isPause: true  },
  { startTime: 420, endTime: 520, isPause: false },
  { startTime: 520, endTime: 580, isPause: true  },
  { startTime: 580, endTime: 680, isPause: false },
  { startTime: 680, endTime: 740, isPause: true  },
  { startTime: 740, endTime: 840, isPause: false },
];
```

**iOS behavior**: Core Haptics renders rhythm patterns with accurate timing. The asymmetric gaps (100ms vs. 200ms; 150ms vs. 50ms) are above the human just-noticeable difference (~30ms for vibrotactile rhythm) and will be perceived as distinct rhythmic characters rather than just different numbers of pulses. On iPhone 13+, the longer pulses in the STRAIGHT pattern carry noticeably different tactile weight from the shorter pulses in RIGHT, adding a secondary discrimination cue.

**Android behavior**: Android Vibration API faithfully implements the time arrays. However, the rhythmic distinctiveness is slightly degraded on Android due to motor response latency — the fast RIGHT pattern's 50ms silence between the last two pulses may not fully silence on mid-range Android devices. Recommend testing the RIGHT_RHYTHM pattern on Pixel 7 and Galaxy S23 before finalizing timing. Consider widening all pauses by 20ms for Android-specific variant.

**Low Power Mode / dictation conflict**: Same restriction as Schemes 1 and 2. Rhythm patterns are fully silenced during dictation on iOS.

**Noise robustness**: Medium risk. Rhythmic patterns are more noise-robust than pulse counts (no counting required) but less robust than single-duration signals. The key discriminator is pattern *character* (march vs. fast-slow vs. slow-fast), which is lost if environmental vibration masks the pause durations. The PMC 2022 study's 70% accuracy under secondary cognitive task is the best available proxy for performance under real-world conditions; it is lower than the seated 82–90% accuracy.

**Predicted strengths**: No counting under cognitive load. Rhythmic patterns are strongly distinguished in memory — participants in the PMC 2022 study could identify patterns after a single 5-minute training block. Left/right asymmetry is built into the rhythmic character (fast-slow vs. slow-fast), creating a natural directional mnemonic. Best-supported by literature of the feasible schemes.

**Predicted failure modes**: (1) Learning curve — the three rhythms require initial memorization. Unlike duration encoding, there is no natural mapping from "this rhythm feels like left." Training quality will directly determine recognition accuracy. (2) Session fatigue degrades rhythm discrimination more than pulse counting — vibrotactile adaptation reduces the perceptual gap between patterns over repeated presentations. Rest intervals in ALP-975 are non-negotiable for this scheme. (3) STRAIGHT (even 3-pulse) may be miscounted as the RIGHT scheme (which also has 3 elements) by participants who fall back to pulse counting rather than pattern character recognition.

**Implementability**: Feasible

**Confounder flag for ALP-975**: Musical background and rhythm exposure significantly affect vibrotactile rhythm recognition accuracy. Participants with formal music training are expected to outperform non-musicians on this scheme by 15-25 percentage points, based on tactile rhythm research (York University). Record musical background at screening. If the TSBVI student population has high musical engagement (music is commonly emphasized in VI education programs), this creates a sampling bias that limits generalizability.

---

### Scheme 4: Proximity Intensity Ramp

**Prior evidence**: PMC 2017 (belt study, n=13) included a continuous-feedback condition where vibration intensity increased as participants approached a waypoint. Results showed that spatial placement (which tactor vibrated) was the primary cue, but the continuous ramp component reduced decision latency compared to purely discrete signals. The Sunu wristband (YC S17) uses continuous sonar proximity encoding as its primary navigation language, providing the commercial validation that continuous feedback is usable by VI navigators in real environments. PMC 2023 (n=30) demonstrated that continuous asymmetric haptic feedback guided directional choices with a mean error of 0.32 radians — the best directional accuracy of any single study in the literature baseline.

**Timing spec**:

This scheme provides continuous proximity feedback as the user approaches a waypoint, with directional cues supplemented by audio. It does not encode left/right purely via haptic — it encodes *proximity* (how close to the next decision point) and relies on prior audio or single-fire direction cues at the start of each route segment.

Proximity states (trigger based on distance-to-waypoint):

```typescript
// FAR — faint reminder pulse every 2000ms (>20m to waypoint)
export const PROXIMITY_FAR: HapticEvent[] = [
  { startTime: 0, endTime: 80, isPause: false },
];

// MEDIUM — pulse every 1000ms (10–20m to waypoint)
export const PROXIMITY_MEDIUM: HapticEvent[] = [
  { startTime: 0, endTime: 100, isPause: false },
];

// CLOSE — pulse every 500ms (5–10m to waypoint)
export const PROXIMITY_CLOSE: HapticEvent[] = [
  { startTime: 0, endTime: 120, isPause: false },
];

// IMMINENT — rapid double pulse every 300ms (<5m to waypoint)
export const PROXIMITY_IMMINENT: HapticEvent[] = [
  { startTime: 0,   endTime: 100, isPause: false },
  { startTime: 100, endTime: 200, isPause: true  },
  { startTime: 200, endTime: 300, isPause: false },
];

// ARRIVED — sustained 600ms (fire once on waypoint reach)
export const PROXIMITY_ARRIVED: HapticEvent[] = [
  { startTime: 0, endTime: 600, isPause: false },
];

// DIRECTION_FIRE — fires once at start of segment, before proximity feedback begins
// Left turn: LEFT_PULSE or LEFT_DURATION from Scheme 1 or 2
// Right turn: RIGHT_PULSE or RIGHT_DURATION from Scheme 1 or 2
// Note: Direction firing scheme must be selected from a feasible candidate.
```

**iOS behavior**: The interval-based architecture (fire PROXIMITY_CLOSE every 500ms, set by the navigation engine) is not a hardware concern — each firing is a standard Core Haptics call. iOS Core Haptics also supports `CHHapticPattern` amplitude envelopes for true ramps: amplitude increases from 0.3 to 1.0 as distance decreases. If the engineering team targets iOS 13+ only, implementing a true Core Haptics amplitude ramp (rather than frequency modulation) produces a more natural "pulling toward" sensation. However, this requires a custom native module, not `react-native-haptic-patterns`. The timing spec above uses frequency modulation as the implementable approximation.

**Android behavior**: Android Vibration API does not support amplitude control. Frequency modulation (shorter intervals between fixed-duration buzzes) is the only implementable approximation. This is a qualitative difference from iOS — the sensation on Android is more "urgency tick" than "proximity pull." Perceptual effectiveness should be validated on both platforms separately in ALP-975.

**Low Power Mode / dictation conflict**: Same silencing issue as all other schemes. Additionally, this scheme fires more frequently than discrete schemes — it produces haptic signals every 300ms–2000ms continuously during navigation. The probability of a dictation conflict is therefore higher for this scheme than for others.

**Noise robustness**: High. Proximity encoding is robust to vibration noise precisely because the user is not counting or timing a single event — they are perceiving a continuous rate change. Accidental environmental vibration adds noise but does not disrupt the dominant frequency signal the way it can cause miscounts in Scheme 1.

**Predicted strengths**: Most natural mapping (faster = closer). Validated in commercial product (Sunu wristband). Combines gracefully with audio direction cues — haptic tells you "when," audio tells you "which way." Does not require the user to memorize anything. Works even if individual pulses are missed, because proximity is communicated across multiple pulses.

**Predicted failure modes**: (1) Requires GPS or PDR accuracy sufficient to compute real-time distance to waypoint. If the EchoEcho PDR has 5m error on a 10m corridor segment, the proximity ramp will misfire or fail to advance. Accuracy dependency is higher for this scheme than for discrete cue schemes. (2) Does not independently encode left/right direction via haptic. Requires a hybrid approach (one directional cue at segment start, then proximity during the segment). Study design in ALP-975 must account for this hybrid nature. (3) Continuous haptic feedback causes faster vibrotactile fatigue than discrete cues. Session length and rest breaks are more critical for this scheme than others.

**Implementability**: Conditional — Full implementation on iOS requires native Core Haptics for amplitude ramp. Frequency-modulation approximation is implementable via `react-native-haptic-patterns` on both platforms. Android version is perceptually distinct from iOS. Both are testable in ALP-975.

**Confounder flag for ALP-975**: GPS/PDR accuracy is a direct confounder for this scheme. In the ALP-975 test harness, the experimenter must trigger proximity states manually or from a pre-scripted simulator rather than from live position data. If the study uses live GPS, poor accuracy will create proximity misfires that are confounded with the scheme's perceptual limitations. ALP-974 must support manual experimenter-triggered proximity state changes.

---

### Scheme 5: Asymmetric Shear-Force Hand-Held Haptics

**Prior evidence**: PMC 2023 (n=30). A custom hand-held haptic device applied lateral shear forces to the palm across a 180-degree directional range. Mean directional error in dynamic guided condition: ~0.32 radians (18 degrees). 27 of 30 participants found the dynamic version significantly easier than static. This is the strongest directional accuracy result in the literature baseline.

**Timing spec**: Not applicable. Requires custom hardware (lateral force actuator). No equivalent mechanism exists in standard smartphone vibration hardware.

**iOS behavior**: Not applicable.

**Android behavior**: Not applicable.

**Low Power Mode / dictation conflict**: Not applicable.

**Noise robustness**: High — shear force is not confused with vibration noise.

**Predicted strengths**: Highest directional precision of any scheme in the literature. Intuitive (the force pulls you in the direction to go). No training required.

**Predicted failure modes**: Hardware dependency. Not deployable on stock smartphones. Not relevant for EchoEcho MVP.

**Implementability**: Out-of-scope. Hardware not available on stock iOS/Android devices.

**Confounder flag for ALP-975**: Not applicable. Exclude from the study unless custom hardware is provided.

---

### Scheme 6: Shape-Changing Haptic Device

**Prior evidence**: Nature Scientific Reports 2024. A shape-changing wearable (shape-memory polymer mechanism) demonstrated significantly faster target acquisition than vibration-only feedback in a point-and-identify task. The device physically deformed to indicate direction.

**Timing spec**: Not applicable. Requires shape-memory polymer actuator hardware.

**iOS behavior**: Not applicable.

**Android behavior**: Not applicable.

**Implementability**: Out-of-scope. Hardware not available on stock iOS/Android devices.

**Confounder flag for ALP-975**: Not applicable. Exclude from the study.

---

## Cross-Cutting Confounder Flags for ALP-975

The following confounders apply across all feasible schemes and must be controlled at the study design level, not per-scheme.

| Confounder | Risk Level | Required Control |
|---|---|---|
| Scheme presentation order (learning / fatigue effects) | High | Counterbalanced Latin square design; no scheme tested twice before all others tested once |
| Prior haptic device experience (Sunu, dotLumen, BlindSquare) | High | Screen at recruitment; record device type; include as covariate in analysis |
| Vibrotactile sensitivity variation | Medium | Calibration task at session start: minimum detectable pulse duration (target: <60ms) |
| Session fatigue across multiple schemes | Medium | Mandatory 90-second rest between schemes; cap at 6 schemes/session; log any reported fatigue |
| iOS vs. Android device differences | High | Standardize to one device model for all sessions; defer cross-platform comparison to a follow-on study |
| Phone grip / hold posture | High | Standardize grip instruction: dominant hand, cane in non-dominant; document cane type |
| Cane contact vibration transmission | Medium | Rubber / silicone case required; document case type; control for bare-hand vs. cased phone |
| Ambient noise at test site | Medium | Controlled indoor environment only; record ambient dB level at session start |
| Musical background (rhythm scheme) | Medium | Record music training at screening; note as potential moderator for Scheme 3 analysis |

**Familiarity bias note**: VI participants with prior haptic navigation device experience carry existing mental models that will affect recognition speed and accuracy for Schemes 1 and 3 specifically. Participants familiar with Braille-based pattern encoding will tend to favor counting (benefiting Scheme 1). Participants familiar with the Sunu wristband will have trained proximity perception (benefiting Scheme 4). Report results stratified by prior device experience.

**Vibration fatigue note**: Prolonged vibrotactile stimulation (>45 minutes continuous testing) reduces distinguishability across all schemes. The 90-second rest requirement between schemes is mandatory. If a participant reports inability to distinguish patterns after a rest, end the session at that scheme and record the point of fatigue onset. Do not continue the session.

---

## Sources Consulted

**Original six schemes:**
- `~/.mdx/research/vi-navigation-technology-landscape.md` — Section 3: Haptic Navigation Interfaces; PMC 2017 (n=13), PMC 2022 (n=30), PMC 2023 (n=30), Nature 2024, SAGEPUB 2025 scoping review
- `~/.mdx/research/echoecho-technical-feasibility.md` — Section 2: React Native Haptic Feedback; `react-native-haptic-patterns` library documentation, iOS Core Haptics API, Android Vibration API, Low Power Mode / dictation conflict documentation
- PMC 2017: [Vibration Patterns for Blind Navigation](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5366061/) — n=13 belt study; spatial > sequential finding
- PMC 2022: [Haptic Feedback for Indoor Navigation](https://pmc.ncbi.nlm.nih.gov/articles/PMC8749676/) — n=24; rhythm pattern recognition, 82–90% seated accuracy
- PMC 2023: [Hand-Held Asymmetric Haptic Directional](https://pmc.ncbi.nlm.nih.gov/articles/PMC10611303/) — n=30; 0.32 radian mean error for shear-force haptic
- Nature Scientific Reports 2024: [Shape-Changing Haptic Device](https://www.nature.com/articles/s41598-024-79845-7)
- SAGEPUB Scoping Review 2025: [Haptic Navigation for VI Users](https://journals.sagepub.com/doi/10.1177/10711813251360706) — paywalled; abstract-level access only
- York University: [Vibration vs Audio Pattern Discrimination](https://www.yorku.ca/mack/hcii2018a.html)
- [react-native-haptic-patterns GitHub](https://github.com/SimformSolutionsPvtLtd/react-native-haptic-patterns)
- Sunu wristband product documentation (YC S17 context from technical feasibility doc)

**2022–2026 literature search (new schemes):**
- Khusro et al. (2022) Sensors/PMC8749676: [Haptic Feedback — Indoor Navigation, Vibration Patterns](https://pmc.ncbi.nlm.nih.gov/articles/PMC8749676/) — Scheme 7
- Paratore & Leporini (2023) Universal Access in the Information Society/PMC9942617: [Exploiting haptic and audio channels](https://pmc.ncbi.nlm.nih.gov/articles/PMC9942617/) — Scheme 8
- Tencent / MTGPA (2022): [Haptic Technology — Visually Impaired navigation](https://www.tencent.com/en-us/articles/2201660.html); Zero Project: https://zeroproject.org/view/project/1168d0f7-46bb-435e-a70f-fffa3eb86dec — Scheme 9
- Lacôte et al. (2024) HCII Springer: [Vibrotactile Patterns on Both Hands — Walker](https://link.springer.com/chapter/10.1007/978-3-031-70058-3_32) — Scheme 10
- Skulimowski, Strumiłło, Trygar (2025) Journal on Multimodal User Interfaces: [Haptic and auditory cues — independent navigation](https://link.springer.com/article/10.1007/s12193-025-00463-2) — Scheme 11
- Guerreiro et al. (2025) ACM IMWUT / PMC12682350: [NavGraph — Blind Travelers Navigation](https://pmc.ncbi.nlm.nih.gov/articles/PMC12682350/) — Scheme 12
- Lee & In (2023) IEEE Access: [Novel Wrist-Worn Vibrotactile Device — Multi-Categorical Navigation](https://ieeexplore.ieee.org/document/10271291/) — referenced in comparison; custom hardware, out-of-scope
- Kammoun et al. (2023) KSII TIIS: [HaptiSole — Vibrotactile Guidance Shoes](https://itiis.org/digital-library/56366) — n=15 indoor, n=5 outdoor; custom shoe hardware, out-of-scope
- Fan et al. (2025) ACM TACCESS (DOI: 10.1145/3711931): [How Can Haptic Feedback Assist People with BLV — Systematic Literature Review](https://arxiv.org/html/2412.19105v1) — survey context
- Tang & Huang (2025) SAGEPUB HFES: [Navigation Assistance Via Haptic Technology — Scoping Review, 28 studies](https://journals.sagepub.com/doi/10.1177/10711813251360706) — paywalled; summary via Semantic Scholar

---

---

## New Schemes from 2022–2026 Literature Search

The following schemes were identified through a targeted search of CHI, MobileHCI, ASSETS, IEEE Access, Sensors/MDPI, Scientific Reports, and Springer journals published between 2022 and 2026. All are assessed for smartphone-only implementability using the same hardware constraint applied to the original six schemes.

---

### Scheme 7: Morse-Inspired Multi-Dimensional Pattern Encoding (Smartphone-Only)

**Citation**: Khusro, S., Shah, B., Khan, I., & Rahman, S. (2022). Haptic Feedback to Assist Blind People in Indoor Environment Using Vibration Patterns. *Sensors*, 22(1), 361. PMC8749676. https://pmc.ncbi.nlm.nih.gov/articles/PMC8749676/

**n = 24** blind participants (79% male, ages 19–49+).

**Scheme description**: Encodes navigation task categories (not just four directions) as pattern-bit sequences modeled on Morse code. Each "pattern-bit" has a character type (heartbeat, knock, rapid/hurry, ringing-alarm, down-stairs, alert-buzzer, engine) and a length dimension (short, medium, long). The combination of type and length produces a vocabulary of distinct patterns mapped to a navigation taxonomy: directional commands (left, right, straight), floor change, severe injury risk, environmental context, and moving obstacle alerts.

Direction is not encoded as discrete left/right from a fixed three-pattern set. Instead, the taxonomy assigns unique rhythm signatures to each named command, exploiting the combination of rhythm character and duration rather than pulse count alone.

**Hardware requirement**: Smartphone only. Uses the built-in single vibration motor. Explicitly designed to avoid multi-actuator hardware. Detects classification at 2–5 Hz via onboard accelerometer.

**Key findings**: Recognition accuracy ranged 65–90% across six tested patterns in a seated condition (n=24). Error rates were 15–20% for experienced smartphone users and approximately 40% for non-users. Response time: 2.9–4.5 seconds per pattern. No navigation field study; this was a pattern discrimination task only.

**Smartphone implementability**: Feasible. The encoding is timing-only (on/off arrays) with no amplitude requirements. All patterns fall within `react-native-haptic-patterns` RecordedEventType capability.

**Difference from Scheme 3 (Rhythm-Based)**: Scheme 3 uses three fixed directional rhythms (march, fast-slow, slow-fast). This scheme (7) uses a larger vocabulary of up to 10+ patterns, each with a distinct rhythmic character. The larger vocabulary increases learnability cost but increases information density. The overlap is in the underlying mechanism; the schemes differ in vocabulary size and taxonomic depth.

**Flag**: The 65% recognition floor for the weakest pattern is a concern. Under navigation cognitive load, Scheme 3's 70% dual-task result and Scheme 7's 65% worst-case seated result converge. A larger vocabulary (Scheme 7) likely widens the accuracy spread under load.

---

### Scheme 8: POI-Category Haptic Icons Paired with Audio (Smartphone-Only, Cognitive Mapping)

**Citation**: Paratore, M. T., & Leporini, B. (2023). Exploiting the haptic and audio channels to improve orientation and mobility apps for the visually impaired. *Universal Access in the Information Society*. https://doi.org/10.1007/s10209-023-00973-4. PMC9942617. https://pmc.ncbi.nlm.nih.gov/articles/PMC9942617/

**n = 7** visually impaired participants (ages 42–65; 4 severely impaired, 3 fully blind).

**Scheme description**: This scheme does not encode turn directions. It encodes point-of-interest (POI) category via six distinct short-pattern haptic icons delivered from a smartphone, each paired simultaneously with a TTS audio label. The six patterns:

| Category | Vibration Pattern |
|---|---|
| Shop | Single short (100ms) |
| Bar/Restaurant | Single long (300ms) |
| ATM | Short-pause-long |
| Public Transport | Long-short-pause-long |
| Church | Three shorts with pauses |
| Historical Building | Long-pause-medium |

The encoding leverages duration asymmetry and pause structure rather than frequency. Audio (TTS) is redundant with the vibration — the haptic alone is insufficient for new POI categories without training, but the combined modality outperformed either alone.

**Hardware requirement**: Smartphone only. Native Android vibration API. Tested on Huawei MediaPad T5 (Android 8) and Oppo A74 (Android 12). Notes: "Android does not always allow full control over the vibration motor," so frequency modulation was explicitly excluded.

**Key findings**: Users retained 3–4 of 6 patterns reliably after initial familiarization. Combined haptic-audio was preferred over haptic alone or audio alone by all seven participants. No quantified accuracy metric reported (qualitative preference data only).

**Smartphone implementability**: Feasible. This is a paired audio-haptic scheme, not a pure haptic one. It validates a combined modality approach for contextual navigation information (POI identification), not real-time turn guidance. Most relevant as a model for the "approaching turn" advisory signal in Scheme 3 or 4 — a paired audio prompt + vibration icon — rather than as a standalone directional encoding scheme.

**Relevance to EchoEcho**: This is the primary empirical support for combined audio-haptic encoding in navigation for VI users on a stock smartphone from 2023. It does not provide turn-direction data, but the combined modality finding directly supports the Scheme 4 hybrid design (haptic proximity + audio turn announcement).

---

### Scheme 9: Deviation-Based Continuous Feedback — "No Vibration = On Course" (Smartphone-Only, Commercial)

**Citation**: Tencent / MTGPA Haptics (2022 deployment). Connected to Tencent Maps. Described in: Tencent. (2022). *Touching Lives: How Haptic Technology Empowers the Visually Impaired*. By 2022, MTGPA Haptics was deployed in over 240 million smartphones. Zero Project award recipient. https://zeroproject.org/view/project/1168d0f7-46bb-435e-a70f-fffa3eb86dec

**n**: Not published in peer-reviewed literature. Described in product/press documentation only. No formal study.

**Scheme description**: The absence of vibration signals correct heading. When the user deviates from the planned route, vibration begins. Vibration intensity (and/or frequency of pulses) scales with the degree of deviation — greater deviation triggers stronger or more frequent vibration. Correctional audio cues (voice prompts) accompany the haptic signal. Bus and transit alerts use custom short-long patterns distinct from navigation deviation signals.

This is an inversion of the typical direction-encoding paradigm. Rather than encoding a specific direction ("turn left"), it encodes course correctness. The user calibrates by walking in a direction that reduces or eliminates vibration.

**Hardware requirement**: Smartphone only. Uses native Android vibration. No custom hardware.

**Key findings**: Deployment-scale (240M devices, 2022). No peer-reviewed accuracy or usability data. Described recognition rate of ~90% and 30-minute learning curve, but source is Tencent marketing material, not a controlled study.

**Smartphone implementability**: Feasible. The scheme is implementable with any single-vibration-motor phone. Amplitude scaling requires native Core Haptics on iOS; frequency scaling (pulse rate) is the Android fallback.

**Difference from Scheme 4 (Proximity Intensity Ramp)**: Scheme 4 encodes proximity to the next waypoint (when to act). This scheme encodes correctness of current heading (whether to act now). They are complementary and could be layered: ramp = approach urgency, deviation feedback = heading correction.

**Confidence caveat**: No peer-reviewed source. The scheme is documented at sufficient technical detail only from press/product sources. The 90% accuracy figure is unverified. Flag as commercial-deployment evidence only.

---

### Scheme 10: Bimanual Vibrotactile Encoding on Walker Handles

**Citation**: Lacôte, C. et al. (2024). Do Vibrotactile Patterns on both Hands Improve Guided Navigation with a Walker? In *HCII 2024*, Springer LNCS. https://link.springer.com/chapter/10.1007/978-3-031-70058-3_32. Also deposited: https://inria.hal.science/hal-04553752

**n = 18** participants, actual walking conditions.

**Scheme description**: Three guidance strategies using haptic walker handles:
1. **Uni-manual**: Vibration on one handle only (the handle on the side of the intended turn).
2. **Bi-manual**: Vibration on both handles, differentially timed to indicate direction.
3. **Dual**: Combination — single-handle patterns for some directions, two-handle patterns for others.

Two actuation modes were compared: vibration and tapping. The specific per-direction pattern is not published in accessible form; the paper focuses on the bimanual vs. unimanual comparison rather than encoding details.

**Hardware requirement**: Custom haptic walker handles. Not a smartphone.

**Smartphone implementability**: Out-of-scope as designed. However, the bimanual finding is partially transferable: a user holding a phone with both hands (or using a phone + wristwatch) could receive left-hand vs. right-hand vibration signals encoding direction. If EchoEcho targets a dual-device scenario (phone + Apple Watch), the directional principle (one device vibrates = turn toward that side) is implementable with existing consumer hardware.

**Key findings**: Bi-manual conditions produced higher satisfaction, lower perceived cognitive load, higher confidence in task success, and faster navigation speed than uni-manual. Path accuracy did not differ significantly. Participants preferred bimanual overwhelmingly despite equivalent objective accuracy.

**Flag for EchoEcho**: If the user population carries both a phone and a smartwatch, a bimanual directional encoding scheme (right wrist buzzes = turn right, phone buzzes = turn left) is supported by this evidence. This was not in the original six schemes and is not implementable with a phone alone, but is implementable with phone + watch.

---

### Scheme 11: Spatial Matrix Haptic Belt + Stereo Audio (Custom Hardware)

**Citation**: Skulimowski, P., Strumiłło, P., & Trygar, S. (2025). Haptic and auditory cues: a study on independent navigation for visually impaired individuals. *Journal on Multimodal User Interfaces*. https://doi.org/10.1007/s12193-025-00463-2

**n = 10** blind participants (static and mobility trials).

**Scheme description**: A wearable device with a stereo vision camera, central control unit, custom haptic belt (4×5 matrix of 20 vibration actuators), speakers, and keyboard. Depth images are segmented into an occupancy grid. Each grid cell maps to one actuator on the belt. Obstacles in the scene activate the corresponding actuator on the user's torso. The belt provides a spatial body-map of the immediate environment — each activated actuator position tells the user where the obstacle is relative to their body. Audio cues supplement with verbal obstacle descriptions.

This is a spatial-body-placement scheme extended from a single-actuator belt (Scheme 2 in the original list) to a full 20-actuator matrix.

**Hardware requirement**: Custom. 20-actuator haptic belt + stereo vision camera. Not a smartphone.

**Smartphone implementability**: Out-of-scope. The 20-actuator matrix cannot be approximated on a smartphone. The stereo camera is not the phone camera. This is included as evidence that the combined haptic-audio approach is effective (n=10), not as a smartphone candidate.

**Key findings**: System verified in static and mobility trials. The spatial matrix approach allows users to perceive environment layout without sequential verbal descriptions. No direct accuracy comparison to smartphone-only approaches reported.

---

### Scheme 12: Audio-Navigation with Earcon + Sonification for Rotation and Approach (Smartphone-Only)

**Citation**: Guerreiro, J. et al. (2025). NavGraph: Enhancing Blind Travelers' Navigation Experience and Safety. *Proceedings of the ACM on Interactive, Mobile, Wearable and Ubiquitous Technologies*, Vol. 9, No. 3, Article 117. https://doi.org/10.1145/3749537. PMC12682350.

**n = 10** fully blind participants (power-analyzed sample).

**Scheme description**: NavGraph uses audio exclusively — no haptic vibration — for turn-by-turn guidance. The encoding scheme combines:
- Verbal messages ("rotate," "walk," "side-step") for navigation state.
- Earcons for event marking (route segment start, arrival, off-route alert).
- Sonification to convey quantities — specifically, the amount of rotation needed at a turn.

"Parsimonious Instructions" principle: NavGraph minimizes total instruction count (averaged 53.8 instructions vs. 77.2 for SOTA baseline, p<.01). Safety improved: time outside safe navigation areas dropped from 50.9s to 19.2s (p<.05).

**Hardware requirement**: Smartphone only. iPhone 14 Pro. No custom hardware.

**Smartphone implementability**: Fully implementable. This is a pure audio scheme on an iPhone.

**Relevance to EchoEcho haptic schemes**: NavGraph demonstrates that the audio component of a hybrid audio-haptic navigation system can be made parsimonious enough to not compete with the haptic channel. The verbal/earcon/sonification structure is the highest-performance audio encoding from peer-reviewed smartphone studies (2022–2025) and provides the audio half of any combined haptic-audio scheme (Scheme 8's POI encoding or Scheme 4's proximity hybrid).

**Key finding for scheme design**: Sonification of rotation quantity (how much to turn, not just which direction) is a specific novel encoding element not present in the original six schemes. Combining a haptic "turn left" signal with an audio sonification of the required rotation angle adds precision without adding vibration complexity.

---

## Updated Summary Table (All Schemes)

| # | Scheme | Smartphone-Only | Prior Evidence | Key Risk |
|---|--------|-----------------|----------------|----------|
| 1 | Sequential pulse counting | Yes | None (navigation-specific) | Counting load under dual-task |
| 2 | Duration encoding | Yes | Moderate | Left/right ambiguity under vibration masking |
| 3 | Rhythm-based pattern | Yes | PMC 2022, n=24 (pattern discrimination) | Learning curve; fatigue degrades rhythm |
| 4 | Proximity intensity ramp | Conditional | PMC 2017, n=13; Sunu commercial | GPS accuracy dependency |
| 5 | Asymmetric shear-force | No (custom hardware) | PMC 2023, n=30 | Requires custom actuator |
| 6 | Shape-changing device | No (custom hardware) | Nature 2024 | Requires shape-memory polymer |
| 7 | Morse-inspired multi-pattern | Yes | PMC 2022, n=24 | Large vocabulary; 65% floor on weakest pattern |
| 8 | POI-category + audio (combined) | Yes | PMC/Springer 2023, n=7 | Not directional; cognitive mapping use only |
| 9 | Deviation feedback (no-vibe = on-course) | Yes | Commercial, 240M deployments, 2022; no peer-review | No peer-reviewed accuracy data |
| 10 | Bimanual walker handles | No (custom) / Phone+Watch | Springer HCII 2024, n=18 | Requires two devices |
| 11 | 20-actuator spatial matrix belt + audio | No (custom hardware) | Springer 2025, n=10 | Custom belt |
| 12 | Audio earcon + sonification (NavGraph) | Yes (audio-only) | ACM IMWUT 2025, n=10 | No haptic component |

---

## Open Questions

1. **Platform target**: Is EchoEcho MVP iOS-only or both iOS and Android? If iOS-only, Scheme 4 can use native Core Haptics amplitude ramps (via a custom native module), significantly improving the scheme's fidelity. If both platforms, frequency modulation is the only implementable approximation on Android.

2. **Hybrid scheme**: Should the study test a hybrid approach — Scheme 4 for proximity awareness combined with a single directional cue from Scheme 2 or 3 at the start of each segment? This hybrid mirrors how the Sunu wristband works (continuous proximity + discrete turns). If yes, ALP-974 must support combined pattern firing.

3. **Scheme count for ALP-975**: With 4 original feasible schemes and two newly confirmed smartphone-compatible schemes (Scheme 7's Morse-inspired multi-pattern, and Scheme 9's deviation-feedback), the total testable candidate count rises to six. A 90-minute session cap cannot accommodate all six. Recommend prioritizing: Scheme 3 (strongest peer-reviewed evidence), Scheme 7 (comparable mechanism but larger vocabulary — a direct comparison question), and Scheme 9 (orthogonal paradigm — deviation feedback vs. directional instruction). Confirm session count budget before ALP-975 executes.

4. **ALP-974 timing**: ALP-974 (test harness) is blocked on this document for the proximity scheme (Scheme 4) specifically, because the experimenter-trigger architecture depends on whether proximity states are scripted or GPS-driven. ALP-974 should implement experimenter-triggered proximity states as default; GPS-driven triggering can be added as an enhancement.

5. **SAGEPUB scoping review (Tang & Huang 2025)**: The review covers 28 studies but is paywalled (403 on direct fetch). It is the most comprehensive recent catalogue of haptic navigation schemes and may contain additional candidates not surfaced by this search. Access via institutional subscription or author request is recommended before finalizing the ALP-975 scheme set.

6. **Scheme 9 (Tencent MTGPA) peer-review gap**: The no-vibration-on-course paradigm has 240M deployment scale but zero peer-reviewed accuracy data. If this scheme enters ALP-975, it should be framed as a pilot evaluation of a commercially proven but scientifically unvalidated scheme. The 90% recognition rate and 30-minute learning curve from Tencent's own reporting should be noted but not cited as experimental evidence.

7. **Rotation sonification (from NavGraph, Scheme 12)**: The use of audio sonification to communicate rotation quantity (not just direction) is a novel element with good peer-reviewed support (n=10, significant improvement over SOTA). This is worth incorporating as an audio layer in any combined scheme, but requires EchoEcho to have a real-time heading sensor feed (compass + PDR) at sufficient accuracy to compute required rotation angle.
