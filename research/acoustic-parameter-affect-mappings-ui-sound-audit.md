---
title: Acoustic Parameters to Perceived Semantics/Affect for Short Non-Speech Sounds (UI Sound Library Audit)
type: research
tags: [psychoacoustics, sound-design, timbre-semantics, auditory-warnings, ui-sound, affective-audio]
summary: Published evidence mapping synthesis parameters (gain, attack, decay, FM index, cutoff, Q, duration, pitch) to perceived politeness, warmth, mechanical feel, contrast, density for a procedural UI sound library.
status: active
confidence: high
created: 2026-07-07
updated: 2026-07-07
---

# Acoustic Parameters and Perceived Affect for Short UI Sounds

## Executive Summary

The perceived-urgency literature (Edworthy, Hellier, and colleagues) is the strongest, most replicated body of evidence and directly supports a "politeness = low urgency" mapping: lower loudness, slower attack, lower pitch, slower repetition, and greater harmonicity all reduce perceived urgency and aggressiveness. Timbre-semantics research (von Bismarck, Zwicker & Fastl, Zacharakis, Saitis & Weinzierl) robustly ties "warm" to low spectral centroid / low sharpness plus energy in low harmonics, and ties "sharp/rough" to high-frequency energy and inharmonic partial interference, both of which load negatively on pleasantness. "Mechanical feel" is the weakest-evidenced axis: it maps most defensibly to timing regularity, sharp transients, spectral cleanliness, and inharmonic/metallic partials via product-sound-design work (Özcan & van Egmond, Parizet), but no single validated "mechanicalness" scale exists. The one mapping to scrutinize hardest is any that raises FM modulation index or filter Q for "warmth": both increase roughness/sharpness and cut against warmth.

## 1. POLITENESS (via urgency, aggressiveness, calmness)

No literature measures "politeness" of a sound directly. The defensible route is inversion: a polite sound is a low-urgency, low-aggressiveness, low-annoyance, high-pleasantness sound. The urgency literature is the best-validated mapping available for any of these axes.

**Foundational study.** Edworthy, Loxley & Dennis (1991), "Improving Auditory Warning Design: Relationship Between Warning Sound Parameters and Perceived Urgency," *Human Factors* 33(2), 205-231. Systematically manipulated pulse-level parameters (fundamental frequency, harmonic series/content, amplitude envelope shape, delayed harmonics) and burst/melodic parameters (speed, rhythm, pitch range, pitch contour, number of repetitions). Findings, all in the direction relevant to a politeness axis:
- Higher fundamental frequency (pitch) -> higher urgency.
- Faster speed / shorter inter-pulse interval / more repetitions -> higher urgency.
- Larger pitch range and irregular harmonic series -> higher urgency.
- **Amplitude envelope: a regular (slow, symmetric) envelope was rated less urgent than one with a fast/abrupt onset.** This is the direct attack-time result (see section 6).
- Inharmonicity / "delayed harmonics" (added roughness/dissonance) -> higher urgency.

**Quantification / power-law follow-up.** Hellier, Edworthy & Dennis (1993), "Improving Auditory Warning Design: Quantifying and Predicting the Effects of Different Warning Parameters on Perceived Urgency," *Human Factors* 35(4), 693-706. Fitted Stevens's power-law exponents to four parameters (speed, fundamental frequency, repetition units, inharmonicity). Practical upshot: **speed (tempo) has the steepest exponent** and is the most powerful urgency lever; pitch and inharmonicity are strong; this lets urgency be scaled predictably. Strong, replicated.

**Speech-warning extension (acoustics vs semantics).** Hellier, Edworthy, Weedon, Walters & Adams (2002), "The Perceived Urgency of Speech Warnings: Semantics Versus Acoustics," *Human Factors* 44(1), 1-17. Urgent-sounding words were spoken louder, at higher F0, and with broader pitch range. Confirms loudness, pitch height, and pitch range as urgency drivers independent of meaning.

**Reaction-time validation.** Suied, Susini & McAdams (2008), "Evaluating Warning Sound Urgency With Reaction Times," *Journal of Experimental Psychology: Applied* 14(3), 201-212. Faster inter-onset interval (tempo) and higher frequency both shortened reaction times, tying subjective urgency ratings to behavioral urgency. Adds behavioral (not just rating) evidence that tempo and pitch drive urgency.

**Environmental / affective norming (valence-arousal for short sounds).** Two citable norm sets: Marcell, Borella, Greene, Kerr & Rogers (2000), "Confrontation naming of environmental sounds," *Journal of Clinical and Experimental Neuropsychology* 22(6), 830-864 (the 120-sound corpus, ~0.5 s clips, later reused for affect); and the more directly affective Hocking, Dean et al. NESSTI norms: Yang, W. et al. / "NESSTI: Norms for Environmental Sound Stimuli," *PLOS ONE* 8(9): e73382 (2013), which provides valence and arousal ratings for environmental sounds. Use these for the general principle that loud, fast-onset, rough, high-frequency sounds skew high-arousal and often low-valence.

**Direction and relative strength for the politeness axis (higher value of parameter -> effect on urgency/aggression; invert for politeness):**

| Acoustic parameter | Effect on urgency/aggression | Strength of evidence |
|---|---|---|
| Loudness / gain | Increases | Strong, replicated |
| Attack steepness (short rise time) | Increases | Strong (Edworthy 1991; envelope result) |
| Repetition speed / tempo | Increases (largest single lever) | Strong, replicated, power-law quantified |
| Pitch height (F0) | Increases | Strong, replicated |
| Pitch range / contour spread | Increases | Strong |
| Roughness / inharmonicity | Increases | Strong for urgency; mixed for annoyance (see 4) |
| Harmonicity (tonal, consonant) | Decreases urgency (calmer) | Strong |

Politeness mapping verdict: **well-supported by inversion of urgency.** A polite sound = quieter, slower attack, lower pitch, slower/fewer repetitions, more harmonic. Any parameter mapping that reduces gain, lengthens attack, lowers pitch, and reduces FM index for "more polite" is aligned with the evidence. Note the literature does not equate "polite" with "calm" perfectly: politeness also carries a pleasantness/premium component best handled by the warmth and sharpness/roughness evidence below.

## 2. WARMTH

The user's hypothesis (low spectral centroid, low sharpness, harmonic richness in low partials, longer/softer attack) is **confirmed** by timbre-semantics research, with one caveat about "harmonic richness."

**Sharpness as the anchor.** von Bismarck (1974), "Sharpness as an Attribute of the Timbre of Steady Sounds," *Acustica* 30, 159-172. The dull-sharp / soft-hard / dark-bright factor carried the most variance in timbre semantic space and mapped to the **frequency position of overall spectral energy**: energy concentrated low = dull/soft/dark (i.e., warm); energy high = sharp/bright. Warmth is essentially the low-sharpness pole. Strong, foundational.

**Sharpness formalized.** Zwicker & Fastl, *Psychoacoustics: Facts and Models* (Springer; 1990/1999/2007 editions). Sharpness (unit: acum) is a weighted spectral centroid on the Bark scale, dominated by the proportion of high-frequency energy; largely independent of loudness. Low sharpness is the psychoacoustic definition of warm/dull timbre. Strong.

**Semantic-differential timbre spaces.** Zacharakis, Pastiadis & Reiss (2014), "An Interlanguage Study of Musical Timbre Semantic Dimensions and Their Acoustic Correlates," *Music Perception* 31(4), 339-358; and Zacharakis, Pastiadis & Reiss (2015), "An Interlanguage Unification of Musical Timbre," *Music Perception* 32(4), 394-412. Three cross-language dimensions: **luminance** (brilliant/sharp vs deep), **texture** (soft/rounded/**warm** vs rough/harsh), and **mass** (dense/rich/full/thick vs light). "Warm" sits on the soft/rounded texture pole, opposite rough/harsh. Texture correlated with the energy distribution of harmonic partials; luminance/brightness with spectral centroid. Strong, cross-language replication.

**Survey synthesis.** Saitis & Weinzierl (2019), "The Semantics of Timbre," in *Timbre: Acoustics, Perception, and Cognition* (Siedenburg, Saitis, McAdams, Popper & Fay, eds.), Springer Handbook of Auditory Research 69, 119-149. Consolidates the field into brightness, roughness, and fullness/richness families; confirms warmth as low-brightness/low-centroid, with fullness contributed by strong low-order harmonics. Authoritative review.

**Acoustic correlates of "warm" (verified):**
- Low spectral centroid / low sharpness: **confirmed, strong.** This is the single most reliable correlate. Maps to lower filter cutoff and rolled-off highs.
- Energy in low-order harmonics / fullness: **confirmed** as the "mass/fullness" contribution to warmth.
- Longer/softer attack: **supported** (soft attack reduces perceived brightness/sharpness of the onset and is part of the "rounded/soft" texture pole), though attack is a weaker correlate of warmth than the steady-state spectral centroid.
- "Harmonic richness": **needs care.** Richness in *low* partials adds warmth/fullness, but richness that adds *high* partials raises the centroid and reads as bright, not warm. If the FM index parameter increases sidebands (thus high-frequency and often inharmonic content), raising it will move a sound *away* from warm. A "warmth" mapping that increases FM modulation index is likely miscalibrated; warmth should if anything reduce FM index and lower cutoff.

Warmth mapping verdict: **align warmth with low cutoff, low Q (see 4), low FM index, softer attack, and low-harmonic emphasis.** Flag any mapping that raises cutoff, Q, or FM index in the "warmer" direction.

## 3. MECHANICAL FEEL

Weakest-evidenced axis. There is no validated "mechanicalness-vs-organic" perceptual scale analogous to sharpness or urgency. The defensible mapping comes from product-sound-design taxonomy and impact-sound studies.

**Product sound categories.** Özcan & van Egmond (2009), "The effect of visual context on the identification of ambiguous environmental sounds," and Özcan & van Egmond (2012), "Basic Semantics of Product Sounds," *International Journal of Design* 6(2), 41-54. They derive **six perceptually relevant product-sound categories: air, alarm, cyclic, impact, liquid, and mechanical.** "Mechanical" sounds are characterized by repetitive/cyclic structure, tonal + noisy components from motors/gears, and metallic/inharmonic resonances. They also enumerate 11 conceptual descriptors including psychoacoustic ("sharp," "loud"), material ("metal," "plastic"), and temporal ("repetitive," "constant") terms. Useful as a vocabulary, not a parameter law.

**Impact / product-quality sound (the clearest parameter evidence).** Parizet, Guyader & Nosulenko (2008), "Analysis of car door closing sound quality," *Applied Acoustics* 69(1), 12-22. Two timbre parameters governed perceived quality: **frequency balance** (more low-frequency energy = "solid," high-quality; more high-frequency = cheap/tinny) and **cleanness** (only one temporal event audible; multiple audible impacts read as rattly/low-quality). Perceived solidity/quality was tied to impact energy, damping, and the time between component impacts. This directly informs a "mechanical/premium" mapping: crisp single transient + fast decay + controlled low-frequency body reads as a precise, high-quality mechanism.

**Ecological/organic contrast.** Gaver (1993), "What in the World Do We Hear? An Ecological Approach to Auditory Event Perception," *Ecological Psychology* 5(1), 1-29, and Gaver (1993), "How Do We Hear in the World? Explorations in Ecological Acoustics," *Ecological Psychology* 5(4), 285-313. Establishes "everyday listening" (hearing sound-producing events and their material/interaction) vs "musical listening." Material perception (wood vs metal, solid vs hollow) and interaction type (impact, scraping, rolling) are heard directly. "Mechanical" reads as rigid-material impact/rotation events; "organic" as softer, more damped, more variable events.

**Acoustic correlates plausibly driving perceived "mechanical" (moderate-to-weak evidence, largely inferential):**
- Timing regularity/precision: perfectly periodic or quantized timing reads as machine-made; micro-timing jitter reads as organic/human. (Consistent with the cyclic/mechanical category; not independently quantified for affect.)
- Sharp transients / short rise time: reads as hard-material contact (switch, relay, click). Supported by product-sound and timbre-onset work.
- Noise content: broadband noise bursts read as air/friction/motor mechanisms (the "air" and "mechanical" categories). Too much noise, though, reads as low-quality (Parizet cleanness result).
- Inharmonicity / metallic partials: inharmonic resonances read as metal/machine; harmonic tonal spectra read as more organic/vocal/instrumental. Supported by material-perception literature.
- Fast, tightly damped decay: reads as rigid, precise mechanism; long resonant decay reads as bell/organic.

Mechanical mapping verdict: **the least literature-backed axis.** A mapping that increases timing precision, transient sharpness, controlled noise, and inharmonic content for "more mechanical" is *consistent with* the product-sound literature but is not backed by a validated perceptual scale. Recommend treating this axis as a design heuristic and validating with a small listening test rather than citing it as established science.

## 4. SHARPNESS and ROUGHNESS (Zwicker) and their affective loadings

Both are formally defined psychoacoustic sensations in Zwicker & Fastl, *Psychoacoustics: Facts and Models* (Springer, 3rd ed. 2007).

**Sharpness (acum).** A measure of the balance of high- vs low-frequency energy, computed as a Bark-weighted spectral centroid with a steep weighting above ~16 Bark. Reference: 1 acum = narrowband noise at 1 kHz, 60 dB. Largely independent of overall loudness. Affective loading: **higher sharpness = lower sensory pleasantness.** Fastl & Zwicker's sensory-pleasantness model makes pleasantness *decrease monotonically* with sharpness. See Zwicker & Fastl, "Sharpness and Sensory Pleasantness" chapter. Strong.

**Roughness (asper).** The sensation from rapid amplitude/frequency modulation, maximal for modulation rates near **70 Hz** (range ~20-300 Hz), arising when adjacent partials fall within a critical band and beat. 1 asper = 1 kHz tone, 60 dB, 100% amplitude-modulated at 70 Hz. Affective loading: roughness lowers sensory pleasantness and contributes to aggressiveness; it is a component of Zwicker's Psychoacoustic Annoyance (PA) model.

**Sensory pleasantness model.** Fastl & Zwicker (2007): sensory pleasantness rises with tonalness and falls with roughness, sharpness, and loudness. This is the cleanest published "pleasantness law" and directly supports both the politeness and warmth axes.

**Psychoacoustic Annoyance (PA).** Zwicker's PA combines loudness (dominant term), sharpness, roughness, and fluctuation strength. Loudness dominates; sharpness adds a strong high-frequency penalty; roughness and fluctuation strength add modulation penalties. Caveat worth flagging: some field studies find roughness's independent contribution to *annoyance* weaker or inconsistent (roughness is more tightly tied to *aggressiveness/power* than to annoyance per se), whereas sharpness and loudness are consistently annoying. So "roughness = annoyance" is real but softer than "sharpness = unpleasant" or "loudness = annoying."

Design implication for your library: **filter Q and FM modulation index are your roughness/sharpness levers.** High Q with a high cutoff produces a peaky high-frequency emphasis (raises sharpness). A high FM index produces dense, often inharmonic sidebands whose spacing can fall in the roughness-maximal region (raises roughness). Both reduce pleasantness. Therefore high FM index / high Q belong on the *aggressive / attention-grabbing / less-polite / less-warm* end, and should be reduced for polite and warm settings. Verify your axes do this.

## 5. UI/HCI SOUND DESIGN (earcons, auditory icons, calm technology, pleasantness)

**Auditory icons.** Gaver (1986), "Auditory Icons: Using Sound in Computer Interfaces," *Human-Computer Interaction* 2(2), 167-177; and Gaver (1989), "The SonicFinder: An Interface That Uses Auditory Icons," *Human-Computer Interaction* 4(1), 67-94. Icons are caricatures of everyday sounds with an ecological link to their referent; parameters of the source event (size, material, force) map to interface variables (e.g., bigger file = bigger/lower sound).

**Earcons.** Blattner, Sumikawa & Greenberg (1989), "Earcons and Icons: Their Structure and Common Design Principles," *Human-Computer Interaction* 4(1), 11-44. Earcons are abstract, structured musical motives (timbre, register, rhythm, pitch) that build a grammar of interface messages. Brewster, Wright & Edwards (1993), "An Evaluation of Earcons for Use in Auditory Human-Computer Interfaces," *Proc. INTERCHI '93* / ACM CHI, 222-227; and Brewster (1998), "Using Nonspeech Sounds to Provide Navigation Cues," *ACM Transactions on Computer-Human Interaction (TOCHI)* 5(3), 224-259. Brewster's guidelines: **use timbre families that are easy to tell apart; avoid harsh/piercing timbres; use register and rhythm as the strongest discriminators; keep intensity modest and within a controlled range because loudness is the crudest and most annoying variable.**

**Meta-analytic comparison.** For a modern consolidated source: a 2023 systematic review/meta-analysis "Auditory Icons, Earcons, Spearcons, and Speech: A Systematic Review and Meta-Analysis of Brief Audio Alerts in Human-Machine Interfaces" (ResearchGate 371527094) summarizes learnability and urgency tradeoffs across the four alert types. Use for the general finding that auditory icons are learned faster and speech/spearcons are least ambiguous, while earcons scale best for structured families.

**Calm technology.** Weiser & Brown (1996), "The Coming Age of Calm Technology," in *Beyond Calculation: The Next Fifty Years of Computing* (Denning & Metcalfe, eds.), Springer. The design principle that ambient/notification signals should sit at the periphery of attention and move to the center only when needed. Directly motivates "polite" UI sound = low-arousal, non-startling, easy to ignore until relevant. Foundational but conceptual (not an acoustic study).

**What makes interface sounds feel polite/premium vs annoying (synthesis of the above):**
- Loudness relative to context is the dominant annoyance driver; a polite sound is quiet relative to the ambient floor and does not spike. (PA model; Brewster guidelines.)
- Soft/slow attack avoids the startle of an abrupt transient (Edworthy envelope result; see 6).
- Low sharpness and low roughness read as pleasant/premium; piercing high-frequency or buzzy modulated sounds read as cheap/annoying (Fastl & Zwicker pleasantness; Parizet "frequency balance" and "cleanness").
- Harmonic, tonal, consonant spectra read as refined; inharmonic/noisy spectra read as harsh unless deliberately "mechanical."
- Short, single, clean events read as high-quality; smeared or multi-event onsets read as rattly/cheap (Parizet cleanness).

## 6. ATTACK TIME SPECIFICALLY

**Claim: longer attack reads as softer / gentler / less urgent. Verified, with the caveat that it is a moderate rather than the dominant urgency lever.**

- Edworthy, Loxley & Dennis (1991), *Human Factors* 33(2): amplitude-envelope shape is one of the manipulated pulse parameters. A **regular/gradual (slow-onset, symmetric) envelope was rated less urgent than an envelope with an abrupt (fast) onset.** This is the primary published basis for "slow attack = less urgent/gentler."
- Mechanistic support from timbre onset research: attack time (log-attack-time) is one of the principal perceptual timbre descriptors (McAdams, Winsberg, Donnadieu, De Soete & Krimphoff 1995, "Perceptual scaling of synthesized musical timbres," *Psychological Research* 58, 177-192; Peeters et al. timbre-toolbox work). Short attack correlates with "percussive/hard/sharp" onset percepts; long attack with "soft/blown/bowed/gentle" onsets. This is why a long attack reads as gentle even though it is not itself an "urgency" study.
- Startle/arousal rationale: abrupt onsets (short rise time) drive the acoustic startle response and higher initial arousal; lengthening the rise time reduces startle. This is well established in the startle-reflex literature (rise-time is a known modulator of startle magnitude) and is consistent with the perceptual result. If you cite this, attribute it as startle-reflex research generally rather than to a single canonical UI paper.

Practical: mapping longer attack time to "more polite / warmer / gentler / less urgent" is **evidence-aligned.** It is a secondary lever behind loudness, tempo, and pitch for urgency, but a primary contributor to the "soft/gentle" percept.

## Sources Consulted

Peer-reviewed / book (primary):
- Edworthy, Loxley & Dennis (1991), *Human Factors* 33(2), 205-231. https://journals.sagepub.com/doi/10.1177/001872089103300206
- Hellier, Edworthy & Dennis (1993), *Human Factors* 35(4), 693-706. https://journals.sagepub.com/doi/10.1177/001872089303500408
- Hellier, Edworthy, Weedon, Walters & Adams (2002), *Human Factors* 44(1), 1-17. https://journals.sagepub.com/doi/10.1518/0018720024494810
- Suied, Susini & McAdams (2008), *J. Exp. Psychol.: Applied* 14(3), 201-212. https://www.mcgill.ca/mpcl/files/mpcl/suied_2008_jepappl.pdf
- von Bismarck (1974), *Acustica* 30, 159-172. https://www.semanticscholar.org/paper/Sharpness-as-an-attribute-of-the-timbre-of-steady-Bismarck/9576a2a74bff46ee0cded25bfd9e4302b4fb0470
- Zwicker & Fastl, *Psychoacoustics: Facts and Models*, Springer (3rd ed. 2007). https://link.springer.com/chapter/10.1007/978-3-540-68888-4_9
- Zacharakis, Pastiadis & Reiss (2014), *Music Perception* 31(4), 339-358. https://online.ucpress.edu/mp/article-abstract/31/4/339
- Zacharakis, Pastiadis & Reiss (2015), *Music Perception* 32(4), 394-412. https://online.ucpress.edu/mp/article-abstract/32/4/394
- Saitis & Weinzierl (2019), "The Semantics of Timbre," in *Timbre*, SHAR 69, Springer, 119-149. https://link.springer.com/chapter/10.1007/978-3-030-14832-4_5 (chapter PDF: https://comma.eecs.qmul.ac.uk/assets/pdf/Saitis_chap5.pdf)
- Özcan & van Egmond (2012), "Basic Semantics of Product Sounds," *Int. J. Design* 6(2), 41-54. http://www.ijdesign.org/index.php/IJDesign/article/view/957/473
- Parizet, Guyader & Nosulenko (2008), *Applied Acoustics* 69(1), 12-22. https://hal.science/hal-00849046/document
- Gaver (1986), *Human-Computer Interaction* 2(2), 167-177.
- Gaver (1989), "The SonicFinder," *Human-Computer Interaction* 4(1), 67-94.
- Gaver (1993), *Ecological Psychology* 5(1) & 5(4).
- Blattner, Sumikawa & Greenberg (1989), *Human-Computer Interaction* 4(1), 11-44.
- Brewster, Wright & Edwards (1993), *Proc. ACM INTERCHI '93*, 222-227. https://www.researchgate.net/publication/221515744
- Brewster (1998), *ACM TOCHI* 5(3), 224-259.
- Weiser & Brown (1996), "The Coming Age of Calm Technology," in *Beyond Calculation*, Springer.
- McAdams, Winsberg, Donnadieu, De Soete & Krimphoff (1995), *Psychological Research* 58, 177-192.
- Marcell, Borella, Greene, Kerr & Rogers (2000), *J. Clin. Exp. Neuropsychology* 22(6), 830-864.
- NESSTI norms: *PLOS ONE* 8(9): e73382 (2013). https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0073382

Review/secondary:
- "Auditory Icons, Earcons, Spearcons, and Speech: A Systematic Review and Meta-Analysis" (2023). https://www.researchgate.net/publication/371527094

## Source Quality Assessment

High confidence: urgency parameters (Edworthy/Hellier line, multiply replicated + RT-validated), sharpness/roughness definitions and their pleasantness loadings (Zwicker & Fastl, textbook standard), warmth = low centroid/sharpness (von Bismarck + Zacharakis + Saitis/Weinzierl, cross-language replication), attack-time-as-gentle (Edworthy envelope + timbre onset descriptors).

Medium confidence: roughness->annoyance specifically (real but weaker/less consistent than sharpness->unpleasant), premium/polite UI heuristics (well-reasoned from PA + Parizet but not a single controlled "politeness" study), attack-time as urgency lever (secondary, not dominant).

Low confidence / thin literature: "mechanical vs organic" as a measurable perceptual axis. Product-sound taxonomy names a mechanical category and impact-sound studies give correlates, but no validated mechanicalness scale with parameter mappings exists. Timing-regularity-as-mechanical is intuitive but not independently quantified for affect.

## Open Questions

- Is there any direct "politeness" or "premium" rating study for short synthetic UI sounds (vs inferring from urgency/pleasantness)? Not found; likely a genuine gap.
- Quantitative mapping of FM modulation index -> roughness (asper) for short percussive tones: the roughness model predicts it, but a direct study for UI-length sounds would strengthen the audit.
- Validated organic-vs-mechanical perceptual scale with acoustic predictors: appears not to exist; candidate for a bespoke listening test.
- Contrast and density axes were not named in the literature ask; "contrast" likely maps to attack/decay ratio + dynamic range, "density" to spectral/temporal event count. Neither has a dedicated affective-mapping literature; treat as design constructs.

## Actionable Takeaways for the Audit

1. Politeness axis: keep it wired to lower gain, longer attack, lower pitch, slower repetition, lower FM index. This inverts the urgency evidence cleanly. Strongest-supported axis after warmth.
2. Warmth axis: ensure it *lowers* cutoff, *lowers* Q, and *lowers or holds* FM index while softening attack. Flag and fix any warmth mapping that raises cutoff, Q, or FM index. Warmth = low spectral centroid first, everything else second.
3. FM index and filter Q are roughness/sharpness levers: they belong on the aggressive/attention/contrast end and should decrease for polite and warm. Verify sign.
4. Attack time: long attack = gentle/polite is correct; treat it as a primary lever for the "soft" percept but a secondary one for urgency (tempo, loudness, pitch dominate urgency).
5. Mechanical axis: relabel internally as a design heuristic, not an evidence-backed perceptual law. If it must be defensible, run a small pairwise listening test using Özcan & van Egmond's mechanical category and Parizet's cleanness/frequency-balance parameters as the design basis.
6. Loudness is the single strongest annoyance and urgency driver: make sure gain is context-relative (calm-technology principle), not absolute, or the whole library risks reading as impolite regardless of other parameters.
