## Purpose

Design and execute a usability study comparing implementable haptic encoding schemes for directional navigation with visually impaired participants. Produce a results document that gives ALP-958 (haptic engine) an unambiguous scheme recommendation with timing spec, and gives ALP-976 (iOS conflict resolution) data on haptic/dictation interaction.

## Input

Read `~/.mdx/research/haptic-encoding-scheme-candidates.md` (output of ALP-973) before designing the study. The candidate document provides timing specs, prior evidence citations, and confounder flags per scheme. **ALP-973 must be complete before this issue proceeds past the study design step.**

## Output

Persist to `~/.mdx/research/haptic-user-study-results.md`.

Consumed by:
- ALP-958 (haptic engine): needs a single winning scheme with full timing spec and supporting participant data
- ALP-976 (iOS conflict): needs test results on whether haptics/dictation conflict occurred and its effect on recognition accuracy

### Required output schema

```
## Participants
- n=, VI classification breakdown (congenital vs acquired), age range
- Smartphone experience, prior haptic nav device experience
- Device used (model, iOS/Android version)
- Compensation paid, recruitment channel

## Study Design
- Within/between subjects, counterbalancing scheme used
- Session structure (tasks, order, breaks)
- Dual-task condition description

## Results per Scheme
- Recognition accuracy: first-attempt %, mean across participants (n=)
- Response time: mean (s), range
- Error types: miscounts, non-responses, wrong direction
- Dual-task condition: accuracy delta vs. baseline
- iOS Low Power Mode / dictation incidents: count, effect observed

## Confounder Controls
- Order effects: counterbalancing confirmed
- Familiarity bias: prior device experience recorded and noted
- Fatigue: rest break compliance documented

## Rank Ordering
- Table: scheme × accuracy × response time × error rate × dual-task delta

## Recommendation
- Winning scheme name
- Timing spec (milliseconds, full array)
- Threshold met: yes/no with data citation
- Platform-specific implementation notes

## Participant Quotes
- Minimum 2 verbatim quotes per scheme tested

## Open Questions
- What this study did not answer
```

## Study Design Specification

### Design
Within-subjects. Each participant tests all feasible candidate schemes. Counterbalanced Latin square ordering to control for learning and fatigue effects. Maximum 6 schemes per session.

### Participants
- **n**: Recruit 12, target 10 completions (allow for attrition)
- **Inclusion**: Visually impaired (blind or severe low vision), smartphone user, age 18–65
- **Exclusion**: Deaf-blind (requires separate protocol); no prior study participation in the same month
- **VI classification**: Record congenital vs. acquired; document prior haptic navigation device experience (Sunu, dotLumen, BlindSquare, etc.)
- **Compensation**: $50–75 USD per 60–90 minute session
- **Recruitment channels**: University disability services office (primary), NFB local chapter, Carroll Center for the Blind, ACB campus affiliates
- **Lead time**: Allow 3–6 weeks from first contact to completed sessions

### Session Structure (90 min max)
1. Consent and demographics (10 min)
2. Vibrotactile sensitivity calibration task — establishes individual baseline (5 min)
3. Scheme familiarization block — passive exposure to each scheme in isolation, no recognition task (10 min)
4. Recognition task, baseline condition — seated, no concurrent task (20 min)
   - Per scheme: 10 stimulus presentations, participant identifies direction verbally
   - 90-second rest between schemes
5. Dual-task condition — participant walks a 15m corridor with cane while identifying haptic cues (20 min)
   - Same counterbalance order as baseline
   - 90-second rest between schemes
6. Debrief and preference rating (10 min)

### Primary Dependent Variable
First-attempt recognition accuracy (%) in the dual-task condition. This is the ecologically valid metric. Seated baseline is secondary.

### Secondary Dependent Variables
- Mean response time (seconds from stimulus onset to verbal response)
- Error type breakdown (miscount, non-response, wrong direction)
- Subjective confidence rating (1–5 Likert, post-scheme)

### Control Condition
Include spatial encoding via phone alone as a control: sustained vibration on the left edge of the phone for left turn, right edge for right, center pulse for straight. This is the closest analog to the validated spatial body-placement approach (PMC 2017, n=13) within stock phone hardware. It does not require a smartwatch.

### Success Criteria
A scheme advances to ALP-958 if it meets **all** of the following:
- First-attempt recognition accuracy ≥ 80% in the dual-task condition
- Mean response time ≤ 4 seconds
- Achieved by ≥ 8 of 10 completions

If no scheme meets threshold, the results document must state this explicitly and recommend the highest-performing scheme with the gap to threshold noted.

### Confounders to Control

| Confounder | Control |
|---|---|
| Scheme presentation order | Counterbalanced Latin square |
| Prior haptic device experience | Record at screening; include as covariate in analysis |
| Vibrotactile sensitivity variation | Calibration task at session start |
| Session fatigue | Mandatory 90s rest between schemes; cap at 6 schemes |
| Platform differences (iOS vs Android) | Standardize to one device model for all sessions |
| Ambient noise | Controlled indoor environment; record ambient dB |
| Phone grip posture | Standardize grip instruction; dominant hand, cane in non-dominant |

### iOS Conflict Test
Within the baseline recognition block, include 3 trials per scheme where the participant is simultaneously asked to speak a short phrase ("turn left") before the haptic fires. Record whether haptic was silenced (iOS Low Power Mode / dictation conflict) and whether this affected recognition. Report results in the ALP-976-relevant section of the output doc.

### Pilot Session
Before running VI participants: conduct one pilot session with a sighted participant under blindfold. Validate that the test harness fires stimuli correctly, session timing is accurate, and the walking corridor is safe. Fix any issues before proceeding.

## Acceptance Criteria

- [ ] IRB/ethics approval obtained (or confirmed not required) before any participant sessions begin
- [ ] Recruitment plan executed: 12 VI participants recruited, screened, scheduled
- [ ] Pilot session completed and any harness issues resolved
- [ ] All sessions counterbalanced per Latin square scheme
- [ ] Dual-task (walking) condition included in every session
- [ ] Vibrotactile calibration task run at start of every session
- [ ] iOS dictation conflict probe included in baseline block
- [ ] 90-second rests enforced between schemes
- [ ] Output document contains all required schema fields
- [ ] Winning scheme identified against success criteria, or gap-to-threshold documented
- [ ] Minimum 2 verbatim participant quotes per scheme

## Notes

**Blocking dependency**: IRB approval is a hard prerequisite. File immediately. US timelines: expedited review 2–4 weeks, full board 4–12 weeks. If VI population is classified as vulnerable by the reviewing institution, full board review is required. Do not begin recruitment until approval is in hand.

**ALP-974 dependency**: The test harness (ALP-974) must support randomized counterbalanced scheme ordering per participant. The Latin square design requires this; communicate the counterbalancing scheme to ALP-974 before that issue is implemented.

**Device standardization**: All sessions must use the same device model to eliminate iOS Core Haptics vs Android Vibration API as a confound. Decide platform before recruiting; note in the output doc.

**Familiarity bias risk**: Participants with prior experience on haptic navigation products (Sunu wristband, dotLumen glasses, BlindSquare audio cues) carry existing mental models. Record this at screening and note in results. If the sample is heavily skewed toward experienced users, flag this as a limitation.

**Vibration fatigue**: Prolonged testing reduces distinguishability across schemes. The 90-second rest requirement is mandatory, not optional. If a participant reports fatigue or inability to distinguish patterns, note it and end the session at that point.
