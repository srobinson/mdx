---
title: Issue Review — ALP-973 and ALP-975 Haptic UX Validation Gap Analysis
type: research
tags: [ux-research, haptic, accessibility, visually-impaired, issue-review, methodology, echoecho]
summary: ALP-973 lacks output schema specificity and library constraints; ALP-975 has no recruitment plan, no IRB consideration, no study design, and no success criteria — both need significant revision before execution.
status: active
source: ux-researcher
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Executive Summary

ALP-973 (haptic encoding candidates) is a scoped desk-research task that is partially pre-executed by existing landscape research but lacks the output schema and technical constraints downstream issues (ALP-974, ALP-975) require to consume it. ALP-975 (haptic user study) has four critical gaps that block execution: no participant recruitment plan, no study design specification, no IRB/ethics consideration, and no defined success criteria. Both issues need revision before any work should start.

---

## Detailed Findings

### ALP-973: Research and Document Haptic Encoding Scheme Candidates

#### Research Methodology Assessment

The issue is a literature synthesis task. Existing research in `vi-navigation-technology-landscape.md` (Section 3, "Haptic Navigation Interfaces") already identifies six candidate schemes with prior evidence:

1. Sequential pulse counting — 1/2/3 bursts (EchoEcho prototype approach; no prior validation found in literature)
2. Single burst at spatially meaningful body location (PMC 2017 belt study; finding: "single bursts might be better than sequence vibration patterns")
3. Duration encoding — short = approaching, long = turn now (supported by temporal pattern literature)
4. Continuous intensity ramp as proximity encoding (inferred from proximity-feedback literature)
5. Asymmetric hand-held shear force for directional cues (PMC 2023, n=30, mean directional error ~0.32 radians)
6. Shape-changing haptic device (Nature Scientific Reports 2024; faster target acquisition vs. vibration)

The issue does not specify a search strategy, database list, date range, or inclusion/exclusion criteria. For a desk research task with an existing research baseline, this is acceptable if the issue clarifies that the existing landscape doc is the starting set — but this is not stated.

**Critical missing constraint**: The issue does not require candidates to be filtered by implementability within the `react-native-haptic-patterns` library stack. Options 5 and 6 above require specialized hardware not available on a standard smartphone. ALP-974 (test harness) cannot build stimuli for hardware-dependent schemes. The candidate document must tag each scheme as "feasible," "conditional," or "out-of-scope" for the React Native stack before ALP-974 can proceed.

#### Deliverable Specification Assessment

Output path is named (`~/.mdx/research/haptic-encoding-scheme-candidates.md`) but content schema is not defined. ALP-974 needs timing parameters in milliseconds for each implementable scheme. ALP-975 needs prior evidence, expected dependent variable differences, and confounders to control. Neither need is codified in acceptance criteria.

Required output schema (missing from issue):

```
For each candidate scheme:
- Name and one-sentence description
- Prior research basis: citation, n= count, key finding
- Technical implementation spec: timing arrays in milliseconds, library call
- Platform behavior: iOS Core Haptics vs Android Vibration API differences
- Predicted strengths (what it is optimized for)
- Predicted failure modes (when it breaks down)
- Implementability rating: feasible / conditional / out-of-scope
- Confounders to control in ALP-975
```

#### Missing Research Questions

Three dimensions absent from the issue:

**iOS/Android equivalence**: Core Haptics (iOS) supports amplitude control; Android Vibration API drives a motor. The same timing parameters produce perceptibly different tactile character across platforms. Each candidate must be assessed for whether the cross-platform difference is acceptable or requires separate calibration.

**Low Power Mode / dictation conflict**: iOS Taptic Engine is silenced during dictation. A VI navigation app using voice input for destination entry will have haptics suppressed exactly when the user is most actively engaging with the app. Each candidate scheme must be assessed for graceful degradation in this condition.

**Ambient noise robustness**: In campus environments (footsteps, vehicles, HVAC), false-positive pulse counts are a real risk for sequential encoding schemes. The candidate document should flag expected noise interference per scheme.

#### Participant Recruitment

Not applicable — ALP-973 is desk research only. Appropriate scoping.

#### Confounding Variables

Two confounders should be flagged in the candidate document to prime ALP-975's design:

- **Familiarity bias**: VI participants with prior experience with haptic navigation devices (Sunu, dotLumen, BlindSquare) carry existing mental models that will affect recognition rates for certain pattern types.
- **Vibration fatigue/adaptation**: Prolonged vibrotactile stimulation reduces distinguishability. Session ordering in ALP-975 must counterbalance scheme presentation; this should be noted explicitly in the candidate document.

---

### ALP-975: Design and Execute Haptic User Study with VI Participants

#### Research Methodology Assessment

The issue title commits to "design and execute" but the description leaves all core methodological decisions open.

**Study design unspecified**: Within-subjects (each participant tests all schemes) or between-subjects (each participant tests one scheme)? For haptic pattern comparison, within-subjects is standard — it controls for individual vibrotactile sensitivity variation and enables direct comparison. However, it requires counterbalanced Latin square ordering to prevent learning effects. The choice directly determines what ALP-974 must implement in the test harness.

**Primary dependent variable unspecified**: The landscape document cites recognition accuracy (82-90% for well-designed patterns, 65% for ambiguous ones) as the most-used metric in the literature. But recognition accuracy in a seated lab task does not predict performance under navigation load. Other candidates: response time, error type classification, subjective confidence rating, cognitive load proxy (secondary task performance). The issue must pick a primary metric and secondary metrics.

**Ecological validity level unspecified**: A seated recognition task will overestimate real-world accuracy for sequential encoding schemes. The cognitive load objection to 1/2/3 counting — documented in both the landscape and technical feasibility research — only manifests under navigation stress. ALP-975 must specify at minimum a dual-task condition: participants perform a concurrent navigation-analog task (walking a short route, following voice directions, counting environmental features) while identifying haptic cues.

**Stimulus delivery unspecified**: Who or what triggers haptic stimuli — the researcher, the ALP-974 test harness, or the participant's own phone? This determines the test harness architecture ALP-974 must build.

**No control condition defined**: The study can rank candidate schemes against each other, but without a control condition it cannot answer whether any of them outperform simpler alternatives. Minimum viable control: spatial smartwatch encoding (right watch buzz = right turn, left watch buzz = left turn) — the approach best supported by the PMC 2017 belt study and the Manduchi group implementation.

**No pilot session specified**: With a small VI participant pool, a failed session design wastes scarce participant access. A pilot session with 1-2 sighted participants under blindfold conditions should be required before running VI participants.

#### Deliverable Specification Assessment

Output path is named but content schema is not defined. Two downstream consumers have distinct needs:

**ALP-958 (haptic engine)** needs: a single recommended scheme with precise timing parameters, participant data supporting the recommendation (e.g., "8 of 10 participants correctly identified direction on first attempt within 3 seconds"), and platform-specific implementation notes.

**ALP-976 (iOS conflict)** needs: whether the dictation/haptics conflict was tested, and if so, how recognition accuracy degraded.

Required output schema (missing from issue):

```
- Participant table: n=, demographics, VI classification, prior haptic device experience, device used
- Per-scheme results: recognition accuracy (%), mean response time (s), error type breakdown
- Dual-task condition results (if included): accuracy delta vs. baseline
- Rank ordering of schemes by composite score
- Winning scheme recommendation with full timing specification
- Observed failure modes per scheme
- iOS-specific findings: Taptic Engine behavior, Low Power Mode/dictation incidents
- Fatigue/adaptation observations across session
- Participant quotes: minimum 2 verbatim per scheme
- Open questions for follow-on study
```

#### Missing Research Questions

**Success criteria undefined**: No recognition threshold is specified to determine which scheme advances to ALP-958. Without a defined minimum (e.g., ">80% first-attempt recognition accuracy in a dual-task condition across at least 8 of 10 participants"), the study produces a rank ordering but no engineering go/no-go decision.

**Dual-task condition absent**: This is the most consequential methodological gap. The landscape document cites multiple papers establishing that spatial encoding outperforms sequential counting under navigation load specifically. A study that does not test under cognitive load cannot validate or invalidate the 1/2/3 scheme for its intended use case.

**No control condition**: See methodology section above.

**No pilot session**: See methodology section above.

#### Participant Recruitment Assessment — Critical Gap

No recruitment plan exists in the issue. VI participant recruitment is the highest-risk, longest-lead-time activity in accessibility research. Required elements that must be added:

**Sample size**: Not specified. Relevant literature benchmarks: n=12 (Snap&Nav MobileHCI 2024), n=30 (PMC 2023 asymmetric haptic study), n=13 (PMC 2017 belt study). For a within-subjects comparison of 4-6 encoding schemes, a minimum of 8-10 VI participants is needed to detect meaningful differences. With typical attrition in scheduling-dependent research, recruit for 12.

**Inclusion/exclusion criteria**: Not defined. Critical distinctions:
- Congenitally blind vs. acquired blindness (different spatial reasoning strategies; should be documented and analyzed separately if mixed)
- Smartphone users vs. non-users (device familiarity affects haptic sensitivity calibration)
- Current campus students vs. external community members (route familiarity creates a confound in any navigation task)
- Age range (vibrotactile sensitivity declines measurably with age)
- Hearing status (if audio fallback cues are used during the study, deaf-blind participants require a separate protocol)

**Compensation**: Not mentioned. Uncompensated VI user testing is ethically problematic and produces unreliable scheduling. Standard practice for a 60-90 minute session: $40-75 USD in gift cards or equivalent.

**Recruitment channels**: Not specified. Most effective channels for VI research participant recruitment: university disability services office (fastest for student populations), NFB (National Federation of the Blind) local chapters, Carroll Center for the Blind, ACB campus affiliates.

**Recruitment lead time**: Not accounted for in any dependent timeline. Realistic recruitment timeline for 8-12 VI participants through disability services: 3-6 weeks from first contact to completed sessions.

**IRB/ethics review**: Not mentioned. This is a critical oversight. Human participant research at a university requires IRB approval. VI populations may be classified as a vulnerable population by the reviewing institution, requiring full board review rather than expedited review. US IRB timelines: expedited 2-4 weeks, full board 6-12 weeks. This is a hard dependency that must block ALP-975 execution, not run concurrently.

#### Confounding Variables Assessment

No confounders are identified or controlled in the issue as described. The following must be addressed in the study design:

| Confounder | Risk Level | Required Mitigation |
|---|---|---|
| Scheme presentation order (learning/fatigue effects) | High | Counterbalanced Latin square design |
| Prior haptic device experience | High | Screen at recruitment; record and include as covariate |
| Individual vibrotactile sensitivity variation | Medium | Baseline calibration task at session start |
| Session fatigue across multiple schemes | Medium | Mandatory 90-second rest between schemes; cap at 6 schemes per session |
| iOS vs. Android device differences | High | Standardize to one device model, or run separate platform arms |
| Background noise at test site | Medium | Controlled environment; record ambient dB level |
| Phone grip/hold posture | High | Specify standard grip condition; cane users hold phone differently |
| Participant cane use during dual-task condition | High | Require cane use during walking condition; document cane type |

---

## Recommendations

### ALP-973 — Changes Required Before Execution

Priority | Item
--- | ---
Critical | Add implementability constraint: candidates must be achievable via `react-native-haptic-patterns` on iOS and Android. Tag each scheme feasible / conditional / out-of-scope.
Critical | Define output document schema including millisecond-precision timing arrays per scheme (required by ALP-974).
High | Add three required evaluation dimensions per candidate: iOS/Android behavioral equivalence, Low Power Mode/dictation conflict, ambient noise robustness.
Medium | Flag familiarity bias and vibration fatigue as confounders ALP-975 must control; include in candidate document.
Low | Confirm that the six schemes in the existing landscape research (Section 3) are the intended starting set, or define inclusion/exclusion criteria for additional literature search.

### ALP-975 — Changes Required Before Execution

Priority | Item
--- | ---
Critical | Add IRB/ethics approval as a blocking prerequisite. Estimate approval timeline and add to issue dependencies.
Critical | Define participant recruitment plan: n=8-12 VI, inclusion/exclusion criteria, compensation ($40-75 per session), recruitment channels, lead time (3-6 weeks).
Critical | Specify study design: within-subjects recommended; if so, define counterbalancing scheme. ALP-974 cannot be built without this.
Critical | Define success criteria: minimum recognition accuracy threshold and response time ceiling that must be met for a scheme to advance to ALP-958.
High | Add dual-task / cognitive load condition. Seated recognition testing will not answer whether 1/2/3 counting works under navigation stress.
High | Add control condition: spatial smartwatch encoding (right watch = right turn) as the research-supported comparison baseline.
High | Require a pilot session (1-2 sighted participants, blindfolded) before running VI participants.
High | Standardize test device to one model, or define separate iOS and Android study arms.
Medium | Define results document output schema specifying what ALP-958 and ALP-976 need from the file.
Medium | Add session protocol safeguards: 90-second rest breaks between schemes, maximum session length (90 minutes), abandonment criteria.

---

## Sources Consulted

- `~/.mdx/research/vi-navigation-technology-landscape.md` — Section 3: Haptic Navigation Interfaces (PMC 2017, PMC 2022, PMC 2023, Nature 2024, SAGEPUB Scoping Review 2025)
- `~/.mdx/research/echoecho-technical-feasibility.md` — Sections 2 (Haptic Feedback), 3 (Sensor Access), 6 (Prototype Timeline)
- ALP-973 and ALP-975 issue descriptions as provided in the review prompt

---

## Open Questions

1. Is this project affiliated with a university? If yes, IRB approval is required before any VI participant sessions. Timeline must be built around the review cycle.
2. What is the target platform — iOS only, Android only, or both? This determines whether the iOS/Android cross-platform problem in ALP-973 is a research question or an engineering constraint.
3. Has the project team identified a disability services contact at the target campus? Recruitment cannot begin without this relationship established.
4. What is the budget for participant compensation? This directly caps the achievable n.
5. Is ALP-974 (test harness) blocked until ALP-973 ships? If ALP-973 is delayed, ALP-974 should be parallelized on the known feasible schemes from the existing landscape research rather than waiting for the full candidate document.
