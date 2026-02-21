## Purpose

Research, evaluate, and document implementable haptic encoding scheme candidates for directional navigation (straight / left turn / right turn / arrived). Output feeds ALP-974 (test harness build) and ALP-975 (VI user study). Candidates that cannot be implemented via `react-native-haptic-patterns` on stock iOS/Android hardware are out of scope.

## Input

Baseline research already exists. Do not re-derive from scratch.

- `~/.mdx/research/vi-navigation-technology-landscape.md` — Section 3 "Haptic Navigation Interfaces": six candidate schemes with evidence citations, recognition rate data, response time ranges, and assessment of the 1/2/3 pulse counting approach.
- `~/.mdx/research/echoecho-technical-feasibility.md` — Section 2 "React Native Haptic Feedback": library stack constraints, iOS Core Haptics vs Android Vibration API behavioral differences, Low Power Mode/dictation conflict, timing parameter examples.

## Output

Persist to `~/.mdx/research/haptic-encoding-scheme-candidates.md`.

Consumed by:
- ALP-974 (test harness): needs millisecond-precision timing arrays and implementability tags
- ALP-975 (user study): needs prior evidence citations, predicted dependent variable differences, and confounder flags

## Candidate Set

Start from the six schemes in the landscape doc Section 3. Add any schemes found in literature published 2022–2026 that meet the implementability constraint. Do not manufacture schemes without a literature basis.

Known candidates from existing research:
1. Sequential pulse counting — 1/2/3 bursts (EchoEcho prototype; no prior validation in literature)
2. Single burst at spatially meaningful body location (PMC 2017, n=13)
3. Duration encoding — short = approaching, long = turn now
4. Continuous intensity ramp as proximity encoding
5. Asymmetric shear-force hand-held haptics (PMC 2023, n=30) — likely out-of-scope hardware
6. Shape-changing device (Nature 2024) — out-of-scope hardware

## Required Output Schema

For each candidate, the document must include all of the following fields. Missing fields block ALP-974 and ALP-975.

```
### [Scheme Name]
**Prior evidence**: [citation, n=, key finding — or "none identified"]
**Timing spec**: [burst durations and inter-pulse gaps in milliseconds; exact array format for react-native-haptic-patterns]
**iOS behavior**: [Core Haptics / Taptic Engine characteristics at these parameters]
**Android behavior**: [Vibration API characteristics; note perceptual differences from iOS]
**Low Power Mode / dictation conflict**: [does iOS silence this pattern during dictation? workaround?]
**Noise robustness**: [risk of false-positive counts or misidentification in campus ambient noise]
**Predicted strengths**: [what conditions favor this scheme]
**Predicted failure modes**: [what conditions degrade this scheme]
**Implementability**: feasible | conditional | out-of-scope
**Confounder flag for ALP-975**: [what participant characteristic or session variable would confound this scheme's test results]
```

## Acceptance Criteria

- [ ] All six baseline candidates from the landscape doc are addressed (with implementability tag)
- [ ] Every feasible/conditional candidate has a complete timing spec in milliseconds
- [ ] iOS vs Android behavioral difference is documented for every implementable candidate
- [ ] Low Power Mode / dictation conflict assessed for every iOS candidate
- [ ] Ambient noise robustness assessment included per candidate
- [ ] Familiarity bias and vibration fatigue flagged as confounders ALP-975 must control
- [ ] Out-of-scope hardware schemes are listed and tagged, not silently dropped
- [ ] Document includes a summary table: scheme × implementability × prior evidence × key risk

## Notes

**Dependency**: ALP-974 cannot be fully scoped until this document ships. ALP-975 study design also depends on the candidate list. If delivery is delayed, ALP-974 should begin on the subset of schemes already marked feasible in the landscape doc (schemes 1–4) rather than waiting for the full document.

**Platform target unresolved**: If the project is iOS-only, Android behavioral notes are lower priority. Confirm with the team before spending research time on Android edge cases.

**Research gap confirmed**: Sequential pulse counting (scheme 1, the current EchoEcho prototype approach) has no prior validation in the haptic navigation literature. This does not disqualify it as a candidate, but the document must clearly flag it as an untested hypothesis vs. literature-supported schemes.
