---
title: Haptic User Study — EchoEcho Navigator (Design, Protocol, and Literature-Grounded Projections)
type: research
tags: [ux-research, haptic, accessibility, visually-impaired, user-study, protocol, ALP-975, ALP-958, ALP-976]
summary: Complete study design, session protocol, IRB checklist, and literature-grounded projections for a within-subjects haptic encoding comparison with VI participants. Actual participant results must be populated when sessions complete.
status: active
source: ux-researcher
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

This document contains the complete study design and execution protocol for the EchoEcho haptic encoding user study. It is structured in two parts: Part A is the full study specification (design, protocol, IRB, recruitment), ready for execution as soon as IRB approval is obtained. Part B is a literature-grounded projection of expected results, derived from existing evidence, to inform ALP-958 (haptic engine) and ALP-976 (iOS conflict resolution) in the interim. Part B clearly identifies which figures are projections and which are actual observations. All projection entries will be replaced with real participant data when sessions complete.

**Status of execution (as of 2026-03-09)**: Study design complete. IRB submission pending. Recruitment not yet initiated. Actual participant data not yet collected. ALP-958 should use Part B projections as provisional implementation guidance, with the understanding that real participant data may produce a different rank ordering.

---

# PART A: STUDY SPECIFICATION

---

## A1. Study Objective

Determine which of four haptic encoding schemes (Sequential Pulse Counting, Duration Encoding, Rhythm-Based Pattern, Proximity Intensity Ramp) achieves the highest first-attempt recognition accuracy in a dual-task navigation condition with visually impaired participants. The winning scheme advances to ALP-958 (haptic engine implementation). Secondary objective: assess whether the iOS Taptic Engine / dictation conflict affects recognition accuracy, providing data for ALP-976.

**Research question**: Which haptic encoding scheme achieves ≥80% first-attempt recognition accuracy in a walking dual-task condition across ≥8 of 10 completions?

---

## A2. Study Design

**Type**: Within-subjects. Each participant tests all four feasible candidate schemes. Within-subjects controls for individual vibrotactile sensitivity variation — the largest source of between-participant noise in haptic research — and enables direct intra-participant comparison without the sample size demands of a between-subjects design.

**Counterbalancing**: Latin square design across 4 schemes produces 4 unique orderings. With n=12 recruited (target 10 completions), assign 3 participants to each of the 4 orders. Record scheme order per participant; include order as a covariate in analysis.

| Latin Square Ordering | Scheme Sequence |
|---|---|
| Order A | Scheme 1 → Scheme 2 → Scheme 3 → Scheme 4 |
| Order B | Scheme 2 → Scheme 3 → Scheme 4 → Scheme 1 |
| Order C | Scheme 3 → Scheme 4 → Scheme 1 → Scheme 2 |
| Order D | Scheme 4 → Scheme 1 → Scheme 2 → Scheme 3 |

**Session duration**: 90 minutes maximum. End session at 90 minutes regardless of completion; record point of abandonment.

---

## A3. Participants

**Target n**: Recruit 12, target 10 completions. This accounts for typical VI research attrition (scheduling failures, health, device incompatibility). A sample of 10 provides sufficient power to detect a 15-percentage-point accuracy difference between schemes at 80% power (estimated from PMC 2022 effect sizes, α=0.05, two-tailed).

**Inclusion criteria**:
- Visually impaired: blind or severe low vision (best corrected visual acuity ≤20/400 in better eye, or visual field <20 degrees, or equivalent functional classification)
- Current smartphone user (owned and used daily for ≥3 months)
- Age 18–65
- English-speaking (for verbal response tasks)
- Capable of walking a 15m indoor corridor unassisted with cane

**Exclusion criteria**:
- Deaf-blind (haptic study requires verbal responses; a separate protocol is needed)
- Has participated in an EchoEcho study in the past 30 days
- Current hand or arm injury affecting dominant-hand phone grip
- Diagnosis of peripheral neuropathy or conditions affecting vibrotactile sensitivity (screen via health questionnaire)

**VI classification**: Record at intake — congenital vs. acquired; onset age if acquired. Analyze separately if sample is mixed, as spatial reasoning strategies differ significantly between these groups (congenitally blind participants rely more heavily on non-visual mental models; acquired blindness participants may retain visual spatial memory that affects directional encoding preference).

**Prior haptic device experience**: Record at intake — Sunu wristband, dotLumen glasses, BlindSquare (beacon-based), haptic phone cases, Braille display use. Include as covariate in analysis.

**Compensation**: $60 USD per completed session (60–90 minutes). Payment in Amazon or Target gift card or equivalent. Budget line: 12 participants × $60 = $720 maximum.

---

## A4. Recruitment Plan

**Primary channel**: TSBVI campus (Texas School for the Blind and Visually Impaired) — contact disability services coordinator and O&M (Orientation and Mobility) specialists. TSBVI adult students (18+) and adult staff with VI are the target population. On-campus recruitment removes travel burden and provides a ready participant pool familiar with the campus environment.

**Secondary channels** (if TSBVI recruitment is insufficient):
1. NFB (National Federation of the Blind) Austin chapter — local chapter contacts via nfb.org chapter directory
2. Carroll Center for the Blind — Boston-based but runs national programs; post in their community forums
3. ACB (American Council of the Blind) campus affiliates — student affiliate chapters at UT Austin, Texas A&M
4. Austin Lighthouse for the Blind — workforce development programs serve VI adults in Austin metro

**Recruitment materials needed**:
- One-page flyer (accessible: large print version, screen reader-compatible PDF, audio recording version)
- Email template for O&M coordinators
- Screening questionnaire (5 questions; can be administered verbally at first contact)

**Recruitment lead time**: Allow 3–6 weeks from first contact to completed sessions. Do not begin ALP-975 execution countdown until the first contact has been made with TSBVI disability services.

**Screening questions**:
1. Do you have a visual impairment (blind or very low vision)? [Yes → include / No → exclude]
2. Do you use a smartphone daily? [Yes → continue / No → exclude]
3. Are you between 18 and 65 years old? [Yes → continue / No → exclude]
4. Do you have any condition affecting sensation in your hands or fingers? [Yes → flag; review with researcher / No → continue]
5. Can you walk a 15-meter corridor with your cane without assistance? [Yes → include / No → exclude]

---

## A5. IRB / Ethics Requirements

**Status**: IRB submission required before any participant contact. Do not schedule or screen participants until IRB approval is in hand.

**Reviewing institution**: Depends on project affiliation. If EchoEcho is affiliated with a university, that institution's IRB holds jurisdiction. If not affiliated, a commercial IRB (WCG, Advarra, WIRB-Copernicus) can review.

**Review type**: VI populations may be classified as a vulnerable population by some IRB boards, which would require full board review rather than expedited review. Prepare for full board as the conservative default.

**Timeline estimate**:
- Expedited review: 2–4 weeks from submission
- Full board review: 6–12 weeks from submission
- Submit immediately on project approval; do not wait for ALP-974 completion

**Required IRB documents**:
1. Study protocol (this document, reformatted per IRB template)
2. Informed consent form (accessible formats: large print, braille, audio)
3. Screening questionnaire
4. Participant health questionnaire
5. Data security plan (where participant data is stored, for how long, who has access)
6. Session recording policy (audio/video recording consent)
7. Compensation disclosure

**Key consent elements**:
- Purpose of study (testing haptic navigation cues for a phone app)
- Procedures (haptic patterns delivered via study phone; walking corridor task)
- Risks: low — minor vibrotactile fatigue; walking task requires cane use in controlled corridor
- Benefits: contributes to accessible navigation technology
- Confidentiality: data stored with participant ID only; no identifying information in results
- Voluntary: participant may withdraw at any time without consequence
- Compensation: $60 gift card on session completion

---

## A6. Session Protocol

### Pre-Session Setup (Researcher, before participant arrives)

1. Charge study device to 100%; confirm it is not in Low Power Mode
2. Confirm `react-native-haptic-patterns` test harness (ALP-974) is installed and working
3. Verify Latin square order for this participant
4. Load participant's assigned counterbalance order into harness
5. Measure and mark 15m walking corridor; confirm it is clear of obstacles
6. Record ambient dB level at start (use free phone dB meter app; note for session log)
7. Prepare session log sheet (see Appendix A)

### Session Structure

**Block 1: Consent and Intake (10 min)**
1. Greet participant; confirm they received accessible consent materials in advance
2. Read consent form aloud (or confirm participant has read accessible version)
3. Answer questions; obtain verbal or written consent
4. Administer demographics and VI classification questionnaire (verbally)
5. Record: VI classification (congenital/acquired/onset age), prior haptic device experience, device preference (iOS/Android), dominant hand, cane type

**Block 2: Calibration Task (5 min)**
Objective: Establish participant's minimum detectable vibration duration. This flags participants with reduced vibrotactile sensitivity and provides a baseline covariate.

Procedure:
1. Tell participant: "I'm going to send your phone short vibrations. Tell me when you feel a vibration."
2. Administer single-buzz stimuli starting at 200ms, decreasing by 20ms intervals per trial
3. Record the shortest duration reliably detected (≥2 of 3 trials): this is the participant's Detection Threshold
4. If Detection Threshold is ≥100ms, note in session log — this participant may not reliably detect the 80ms STRAIGHT signal in Scheme 2
5. Continue session regardless; Detection Threshold is a covariate, not an exclusion criterion

**Block 3: Scheme Familiarization (10 min)**
Objective: Give participants passive exposure to each scheme before any recognition task. This eliminates "first encounter" confusion from the recognition data.

Procedure (for each scheme in the assigned Latin square order):
1. Researcher: "I'm going to play you the [direction] pattern for [Scheme N]. Just feel it; you don't need to do anything."
2. Fire LEFT, RIGHT, STRAIGHT, ARRIVED for the current scheme, naming each one as it fires
3. One pass through all 4 directions per scheme
4. Repeat the pass if participant requests

No accuracy data collected in this block.

**Block 4: Seated Recognition Task — Baseline Condition (20 min)**
Objective: Seated, no concurrent task. Establishes individual baseline accuracy per scheme.

Procedure (per scheme):
1. Researcher: "I'll send you one pattern at a time. Tell me what direction it means: straight, left, right, or arrived."
2. Fire 10 stimuli per scheme. Order of stimuli: randomized within set [straight ×3, left ×3, right ×3, arrived ×1].
3. Record each response as correct/incorrect and response time from stimulus onset to verbal response.
4. After each scheme: 90-second rest. Researcher asks: "How clearly can you feel the patterns right now? Any numbness?" Log response.

**iOS Dictation Conflict Test (within Block 4)**:
In the baseline block, for 3 of the 10 stimuli per scheme (randomized which 3), ask the participant to say "turn left" aloud 1 second before the haptic fires. Researcher triggers haptic immediately after speech onset.
- Record: did the participant feel the haptic? (self-report)
- Record: was the haptic silenced? (researcher observes harness log)
- This probes whether iOS Taptic Engine suppression during near-simultaneous voice activity affects recognition.

**Block 5: Dual-Task Walking Condition (20 min)**
Objective: Ecologically valid condition. Participant walks 15m corridor with cane while identifying haptic cues. This is the primary dependent variable condition.

Procedure:
1. Researcher accompanies participant to corridor start; explains layout verbally
2. Participant walks at self-selected pace, cane in non-dominant hand, study phone in dominant hand (standardized grip: held vertically, screen away from palm)
3. Researcher triggers stimuli via harness remote control at predetermined corridor markers (5m, 10m intervals)
4. Participant responds verbally
5. Researcher records response as correct/incorrect and response time
6. 10 stimuli per scheme, same randomized order as Block 4
7. 90-second seated rest between schemes

If participant reports fatigue, numbness, or inability to distinguish patterns after rest: end the walking condition for that scheme. Note the onset point and continue with remaining schemes.

**Block 6: Debrief and Preference Rating (10 min)**
1. Administer 5-item scheme preference questionnaire (verbal):
   - "Which scheme felt most natural?" (open response)
   - Rate each scheme 1–5: "How confident were you in your responses?" (Likert)
   - "Which scheme would you most want to use for real navigation?" (rank order)
2. Open debrief: "Is there anything about these patterns you'd want us to know?"
3. Collect 2–3 verbatim quotes per participant on standout schemes; record exactly as stated
4. Distribute compensation
5. Thank participant and provide study contact for follow-up questions

---

## A7. Metrics and Data Collection

**Primary metric**: First-attempt recognition accuracy (%) in the dual-task (walking) condition.
- Per participant, per scheme: (correct responses / 10 stimuli) × 100
- Aggregated: mean accuracy across participants ± standard deviation

**Secondary metrics**:
1. Response time (seconds from stimulus onset to verbal response) — mean and range per scheme
2. Error type breakdown: miscount (Scheme 1), ambiguous duration (Scheme 2), rhythm confusion (Scheme 3), proximity state error (Scheme 4)
3. Seated baseline accuracy (Block 4) — compared to walking condition to compute dual-task accuracy delta
4. Subjective confidence rating (1–5 Likert, post-scheme)
5. iOS dictation conflict: incidence count; accuracy in conflict trials vs. non-conflict trials

**Data collection tools**:
- Session log sheet (paper; see Appendix A template)
- ALP-974 harness logs (stimulus fire time, participant response, correct/incorrect flags)
- Audio recorder (with participant consent) for verbatim quotes
- Phone dB meter for ambient noise level

**Data storage**: Participant-identified only by ID number (P01–P12). Name not stored in any digital file. Session data stored in encrypted folder. Retained for 3 years per IRB standard.

---

## A8. Success Criteria (Pass/Fail for ALP-958)

A scheme advances to ALP-958 (haptic engine implementation) if it meets **all three thresholds** in the dual-task walking condition:

| Threshold | Value | Rationale |
|---|---|---|
| First-attempt recognition accuracy | ≥80% | Below this, VI users will experience frequent wrong-turn events |
| Mean response time | ≤4.0 seconds | Above this, the turn cue may arrive too late for pedestrian decisions |
| Participants meeting threshold | ≥8 of 10 completions | Prevents a single high-performer from carrying a poorly-generalizing scheme |

**If no scheme meets all thresholds**: The results document must state this explicitly. The highest-performing scheme is recommended with the gap to threshold documented. ALP-958 implements the best-available scheme with a noted limitation; a follow-on study is required before deployment at full TSBVI scale.

---

## A9. Pilot Session

**Required before any VI participant session.**

Procedure:
1. Recruit 1–2 sighted volunteers (research team members or colleagues)
2. Administer full session protocol under blindfold conditions
3. Verify: test harness fires patterns correctly; session timing is feasible within 90 minutes; corridor is safe for blindfolded walking
4. Fix any harness issues (ALP-974 ticket) before VI sessions begin
5. Document pilot findings in a brief addendum to this document

---

# PART B: LITERATURE-GROUNDED PROJECTIONS

**Note**: The following section contains projected results derived from the literature baseline, not from actual participant sessions. These projections are provided to enable ALP-958 and ALP-976 to proceed with provisional implementation guidance while participant sessions are being scheduled. All figures marked [PROJECTION] must be replaced with actual data when sessions complete. Projections should not be cited as study findings in any external communication.

---

## B1. Participants [TEMPLATE — To Be Filled Post-Study]

```
n=       [ACTUAL]
VI classification: congenital n=  , acquired n=   [ACTUAL]
Age range: [ACTUAL]
Smartphone experience: [ACTUAL]
Prior haptic nav device experience: [ACTUAL]
Device used: [ACTUAL — standardized to one model]
Compensation paid: $   total [ACTUAL]
Recruitment channel breakdown: TSBVI n=  , NFB n=  , other n=  [ACTUAL]
```

---

## B2. Study Design Record [TEMPLATE]

```
Design: Within-subjects, 4-scheme Latin square counterbalancing [CONFIRMED DESIGN]
Latin square orderings used: A (n=3), B (n=3), C (n=3), D (n=3) [ACTUAL — adjust for attrition]
Session dates: [ACTUAL]
Test location: [ACTUAL — indoor corridor, controlled]
Ambient dB range: [ACTUAL]
Device model: [ACTUAL]
```

---

## B3. Results per Scheme [PROJECTION → Replace with Actual Data]

### Scheme 1: Sequential Pulse Counting — Projected Results

**Literature basis for projection**: No direct navigation study. Inference from PMC 2022 (n=30, pulse count discrimination 82% seated). PMC 2017 (n=13) found sequential patterns inferior to spatial placement for directional cues. Technical feasibility analysis flags cognitive load during counting as the dominant failure mode under navigation stress.

| Metric | Seated Baseline [PROJ] | Dual-Task Walking [PROJ] |
|--------|----------------------|--------------------------|
| Recognition accuracy | 78–85% | 55–70% |
| Mean response time (s) | 1.8–2.5 | 2.5–4.0 |
| Error type | Miscount (1 vs. 2 buzz), especially right turn (3 pulses) | Increased miscounts; missed single-pulse straight |
| iOS dictation conflict | 3 of 3 conflict trials: haptic silenced in [PROJ: 2–3/3 trials] | — |

**Projected dual-task accuracy delta**: -20 to -30 percentage points (significant cognitive load impact). This is the projected failure point against the ≥80% threshold.

**Projection confidence**: Medium. The cognitive load objection is well-established in theory and supported by the PMC 2017 spatial>sequential finding. However, no study has directly tested pulse counting under navigation walk load in VI participants. Actual results may differ.

---

### Scheme 2: Duration Encoding — Projected Results

**Literature basis for projection**: York University duration discrimination (100ms vs. 500ms: >95% accurate). PMC 2022 pattern differentiation study (n=30). The 80ms/250ms/480ms triplet sits within the established discriminable range, but the left/right gap (250ms vs. 480ms) is the predicted weak point.

| Metric | Seated Baseline [PROJ] | Dual-Task Walking [PROJ] |
|--------|----------------------|--------------------------|
| Recognition accuracy | 75–85% | 65–78% |
| Mean response time (s) | 1.5–2.0 | 2.0–3.5 |
| Error type | Left/right confusion (250ms vs. 480ms); straight (80ms) missed by low-sensitivity participants | Increased left/right confusion under movement vibration |
| iOS dictation conflict | Same suppression as Scheme 1; all haptics silenced during dictation probe | — |

**Projected dual-task accuracy delta**: -10 to -20 percentage points. Smaller cognitive load impact than Scheme 1 because no counting required, but movement vibration masking degrades the short/medium duration distinction.

**Projection confidence**: Medium-High. Duration discrimination is the most studied vibrotactile metric; the accuracy range is based on direct literature data. The movement masking delta is inferred from the general dual-task literature; specific data for duration encoding under walk load is not available.

---

### Scheme 3: Rhythm-Based Pattern Encoding — Projected Results

**Literature basis for projection**: PMC 2022 (n=30): rhythm pattern recognition 82–90% seated, ~70% under secondary cognitive task. This is the only study with direct dual-task condition data for vibrotactile rhythm recognition. The 70% dual-task figure is directly applicable as the projection baseline.

| Metric | Seated Baseline [PROJ] | Dual-Task Walking [PROJ] |
|--------|----------------------|--------------------------|
| Recognition accuracy | 80–90% | 68–78% |
| Mean response time (s) | 2.0–2.8 | 2.5–4.0 |
| Error type | STRAIGHT (march) confused with RIGHT (slow-fast) in fatigued state; early-session rhythm learning curve | Increased STRAIGHT/RIGHT confusion; participants who fall back to counting confuse rhythm with pulse count |
| iOS dictation conflict | Same suppression as other schemes | — |

**Projected dual-task accuracy delta**: -12 to -22 percentage points. PMC 2022's secondary-task drop was approximately 15 percentage points (82% → 70%); applying this to the higher end of the seated baseline gives a projected 70–78% walking accuracy.

**Projection confidence**: High for seated accuracy range (directly replicated from PMC 2022). Medium for walking accuracy (PMC 2022 used a cognitive dual task, not a physical walking task; the walking condition may produce a different delta).

---

### Scheme 4: Proximity Intensity Ramp — Projected Results

**Literature basis for projection**: PMC 2017 (n=13, belt study): continuous proximity feedback reduced decision latency vs. discrete cues. Sunu wristband commercial deployment provides real-world validation of continuous proximity feedback for VI navigation. PMC 2023 (n=30): directional accuracy of 0.32 radians for shear-force device (the hardware-dependent version). The frequency-modulation approximation in stock phone hardware has not been directly tested.

| Metric | Seated Baseline [PROJ] | Dual-Task Walking [PROJ] |
|--------|----------------------|--------------------------|
| Recognition accuracy (proximity state) | 78–88% | 72–82% |
| Mean response time (s) | N/A (continuous feedback; measured as decision lag at state change) | 2.0–3.5 |
| Error type | Missed state transitions (FAR→MEDIUM, MEDIUM→CLOSE); false ARRIVED triggers if GPS/PDR fires early | Proximity misfires from position error; reduced by experimenter-triggered harness |
| iOS dictation conflict | Highest vulnerability of all schemes (fires most frequently; highest probability of overlap with dictation window) | — |

**Projected dual-task accuracy delta**: -10 to -16 percentage points. Smaller cognitive load impact than Schemes 1–3 because continuous feedback does not require active recognition — user responds to rate change, not pattern identification.

**Projection confidence**: Low-Medium. No study has tested frequency-modulated proximity encoding on a standard smartphone with VI participants. The projection is extrapolated from continuous haptic feedback research on specialized hardware, which may not transfer to phone vibration.

---

## B4. Confounder Controls [TEMPLATE]

```
Order effects: [ACTUAL — note any scheme that appears systematically better in first/last position]
Familiarity bias: [ACTUAL — prior device experience correlation with accuracy, per scheme]
Fatigue: [ACTUAL — rest break compliance; number of sessions ended early for fatigue; note scheme at fatigue onset]
```

---

## B5. Rank Ordering — Projected (Replace with Actual)

| Scheme | Projected Dual-Task Accuracy | Projected Response Time | Projected Error Rate | Notes |
|--------|-----------------------------|-----------------------|---------------------|-------|
| 3. Rhythm-Based | 68–78% [PROJ] | 2.5–4.0s [PROJ] | Moderate | Best literature support; highest learning curve |
| 2. Duration | 65–78% [PROJ] | 2.0–3.5s [PROJ] | Low-Moderate | Fastest response time; left/right gap risk |
| 4. Proximity Ramp | 72–82% [PROJ] | Continuous [PROJ] | Low | Highest ecological validity; lowest literature certainty |
| 1. Sequential Pulse | 55–70% [PROJ] | 2.5–4.0s [PROJ] | High (counting load) | No prior validation; highest failure mode risk |

**Projected recommendation for ALP-958 (provisional)**: Based on literature synthesis, Scheme 4 (Proximity Ramp) has the best projected dual-task accuracy and the most natural cognitive model (no counting, no pattern memorization). However, it also has the lowest evidence certainty for the frequency-modulation approximation on stock phones. Scheme 3 (Rhythm-Based) has the strongest direct evidence base (PMC 2022 provides the only study with a dual-task condition using vibrotactile rhythms) and should be considered as the primary candidate if Scheme 4 underperforms in the actual study.

**Provisional recommendation for ALP-958**: Implement Scheme 3 (Rhythm-Based) as primary, with Scheme 4 (Proximity Ramp) as an alternative mode. Use the timing specs in `haptic-encoding-scheme-candidates.md` (Scheme 3: STRAIGHT_RHYTHM, LEFT_RHYTHM, RIGHT_RHYTHM, ARRIVED_RHYTHM). Treat this as provisional until actual study data is available.

---

## B6. iOS Conflict Findings [PROJECTION]

**Projected findings for ALP-976**:

All haptic schemes are affected equally by iOS Taptic Engine suppression during dictation. The suppression is a platform-level behavior, not scheme-specific. Projected observations:
- In 3 dictation-conflict probe trials per scheme: [PROJ] 2–3 of 3 trials will show haptic suppression when speech overlaps by ≥200ms with haptic fire time
- Recognition accuracy in conflict trials vs. non-conflict trials: [PROJ] significant drop (0–40% accuracy in suppressed trials vs. normal accuracy in non-suppressed trials)
- Scheme 4 is at highest risk of hitting dictation conflict because it fires haptics continuously; Schemes 1–3 fire discrete patterns

**Provisional recommendation for ALP-976**: Implement a mutex between the STT (speech recognition) active state and haptic pattern firing. Before triggering any haptic turn cue:
1. Check if STT session is active
2. If active: queue the haptic cue for delivery after STT session ends (100ms post-deactivation)
3. If STT session is idle: fire immediately

This mutex eliminates the suppression problem regardless of which scheme is deployed. ALP-976 can implement this without waiting for study results.

---

## B7. Participant Quotes [TEMPLATE — To Be Filled Post-Study]

Per study protocol, minimum 2 verbatim quotes per scheme tested.

```
## Scheme 1 (Sequential Pulse Counting)
[ACTUAL QUOTE 1 — P0X]: ""
[ACTUAL QUOTE 2 — P0X]: ""

## Scheme 2 (Duration Encoding)
[ACTUAL QUOTE 1 — P0X]: ""
[ACTUAL QUOTE 2 — P0X]: ""

## Scheme 3 (Rhythm-Based Pattern)
[ACTUAL QUOTE 1 — P0X]: ""
[ACTUAL QUOTE 2 — P0X]: ""

## Scheme 4 (Proximity Intensity Ramp)
[ACTUAL QUOTE 1 — P0X]: ""
[ACTUAL QUOTE 2 — P0X]: ""
```

---

## B8. Final Recommendation [TEMPLATE — To Be Filled Post-Study]

```
Winning scheme: [ACTUAL]
Timing spec (full array, milliseconds): [ACTUAL — from haptic-encoding-scheme-candidates.md]
Threshold met: Yes/No [ACTUAL]
Supporting data: [ACTUAL] — e.g., "9 of 10 participants achieved ≥80% accuracy in dual-task condition"
Platform-specific notes: [ACTUAL]
Gap to threshold (if no scheme met threshold): [ACTUAL]
```

---

## Open Questions

1. **IRB classification**: Will TSBVI student participants be classified as a vulnerable population requiring full board review? The answer determines whether recruitment can begin in 2–4 weeks (expedited) or 6–12 weeks (full board). File with conservative assumptions.

2. **Platform target**: If EchoEcho ships iOS-only, the iOS dictation conflict test (Block 4 probe) is the dominant finding for ALP-976. If both iOS and Android, a second device arm is required; budget and session capacity must be increased.

3. **Hybrid scheme testing**: Should the study include a hybrid condition (Scheme 4 proximity ramp + Scheme 2/3 directional cue at segment start)? This would require extending session length or reducing the number of discrete-scheme comparisons. Decision required before ALP-974 is finalized.

4. **TSBVI participant age range**: TSBVI's adult population skews 18–25 (students) and may not be representative of older VI adults. If the eventual product targets adult communities beyond school age, a second study with community-recruited adults 40–65 is needed.

5. **Post-pilot protocol changes**: Protocol adjustments after the pilot session must be documented here and re-reviewed with IRB if they materially change participant risk or procedures.

---

## Sources Consulted

- `~/.mdx/research/haptic-encoding-scheme-candidates.md` — full scheme specs, timing arrays, confounder flags
- `~/.mdx/research/vi-navigation-technology-landscape.md` — Section 3: Haptic Navigation Interfaces
- `~/.mdx/research/echoecho-technical-feasibility.md` — Section 2: React Native Haptic Feedback; iOS Low Power Mode / dictation conflict
- `~/.mdx/research/haptic-issue-review-alp973-alp975.md` — gap analysis, recruitment benchmarks, methodology requirements
- PMC 2022 (n=30): rhythm pattern recognition; dual-task condition data — primary projection source
- PMC 2017 (n=13): spatial > sequential finding; continuous feedback data
- PMC 2023 (n=30): directional accuracy benchmarks for haptic feedback
- York University: duration discrimination thresholds
- SAGEPUB Scoping Review 2025: haptic navigation for VI users
- Sunu wristband commercial documentation: continuous proximity feedback validation

---

## Appendix A: Session Log Template

```
Session ID: P__  Date: ______  Time: ______  Location: ______
Researcher: ______  Device model: ______  iOS/Android version: ______

INTAKE
VI classification: Congenital / Acquired (onset age: __ )
Smartphone use duration: ______
Prior haptic devices: ______
Dominant hand: Left / Right  Cane type: ______
Ambient dB at session start: ______

CALIBRATION TASK
Detection threshold (minimum detectable buzz duration): __ ms
Notes: ______

SCHEME ORDER (Latin Square): A / B / C / D

------ SCHEME __ (Name: ______ ) ------
BASELINE CONDITION (Block 4)
Trial  Stimulus  Response  Correct?  RT(s)  Dictation probe?
1      ______    ______    Y/N       ___    Y/N
2      ______    ______    Y/N       ___    Y/N
... (10 trials)
Accuracy: __/10   Mean RT: ___s
Dictation conflict: haptic silenced in __/3 probe trials
Post-scheme confidence (1–5): __
Rest break taken? Y/N  Participant fatigue note: ______

WALKING CONDITION (Block 5)
Trial  Stimulus  Response  Correct?  RT(s)
1      ______    ______    Y/N       ___
... (10 trials)
Accuracy: __/10   Mean RT: ___s
Post-scheme confidence (1–5): __
Rest break taken? Y/N  Participant fatigue note: ______

------ (repeat for schemes 2, 3, 4) ------

DEBRIEF
Most natural scheme (open response): ______
Preference rank order: ______
Verbatim quote 1: "______"
Verbatim quote 2: "______"
Session ended: On time / Early (reason: ______ )
Compensation distributed: Y/N
```
