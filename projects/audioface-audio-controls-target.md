---
title: Audioface audio control surface — the ceiling
type: research
tags: [audioface, web-audio, procedural-audio, sound-design, control-surface]
summary: Target control surface for an unbounded procedural UI sound studio. 188 controls across 9 domains with perceptual role, range, Web Audio feasibility, CPU cost and priority; plus how the eight theme macros should map onto it and the minimum viable build sequence.
status: active
source: general (pane 5:2.2)
confidence: medium-high
created: 2026-08-18
updated: 2026-08-18
---

# Audioface audio control surface — the ceiling

Scope: what a serious, unbounded, layered sound design studio for short interface sounds must be able to control. This is the target, not the inventory. A sibling pane is recording what the engine implements today; nothing here is a claim about current code.

Repo read for grounding only: `/Users/alphab/Dev/LLM/DEV/helioy/audioface` at `3eb5675`, files `AUDIO.md`, `AUDIT.md`, `packages/core/src/themes.ts`. No writes.

Hard constraint carried through every entry: **zero audio assets**. Noise buffers, impulse responses, wavetables and worklet source are all generated from code at runtime. Nothing here requires a file to be fetched.

## 1. Reading the tables

Every control has an ID, so the surface can be counted, diffed and referenced from code.

**Web Audio column**

| Value | Meaning |
|---|---|
| `native` | One or more standard nodes and `AudioParam` automation cover it directly. |
| `native+gen` | Standard nodes, but a buffer or curve must be synthesised in JS first (noise, IR, `PeriodicWave`, waveshaper curve). |
| `native±` | Achievable with standard nodes but with a documented limitation, noted inline. |
| `worklet` | Needs an `AudioWorkletProcessor`; the graph model cannot express it. |
| `host` | Lives above the audio graph: scheduling, policy, state. |

**CPU column**, per voice, for one sound under 500 ms, on a 2020-era laptop core:

| Tier | Meaning |
|---|---|
| `nil` | Under ~0.1% of a core. Oscillators, gains, biquads, stereo panner. A biquad is roughly five multiply-adds per sample; at 48 kHz that is nothing. |
| `low` | Buffer sources, 1x waveshaper, delay lines, constant sources. |
| `mod` | 4x oversampled waveshaper, a short convolver (IR ≤ 300 ms), a modest worklet, a dozen-plus modal filters. |
| `high` | Convolver with IR over ~1 s, `PannerNode` in HRTF mode, per-sample transcendental worklet math, granular clouds over ~100 nodes per event. |

Two costs dominate that nobody budgets for:

1. **Main-thread node churn.** For a 40 ms click the DSP is free and the JS is not. Constructing, connecting, starting and garbage collecting twenty-odd nodes per trigger, thirty times a second during a drag, is the real ceiling. Budget **≤ 24 nodes and ≤ 2 ms of main-thread work per trigger**, and pool or reuse anything reusable (noise buffers, IRs, wavetables, worklet modules are all shareable across voices).
2. **Worklet load latency.** `audioWorklet.addModule()` is async and needs a secure context. Any worklet-backed control must be preloaded at init or on the first user gesture, or the first sound arrives late. Zero-asset loading works via a Blob URL over an inline source string; sites with a strict `script-src` CSP will reject `blob:`, so a build-emitted `.js` sidecar is the fallback. That is still not an *audio* asset, but it is a distribution constraint worth deciding once rather than per control.

**Priority**: `must` = the studio is not credible without it. `high` = the studio is credibly limited without it. `later` = real expressive reach, not on the critical path.

Totals: **188 controls**, of which **51 are must-have**.

## 2. Structural model the controls assume

The tables presuppose a shape. Stating it prevents the surface from reading as a flat pile of knobs.

- **Patch** = one semantic token's sound. Owns a layer list, a patch bus (inserts, sends, output stage), a duration budget and a seed.
- **Layer** = one source plus its own pitch, amplitude, filter and time controls, plus per-layer inserts. `AUDIO.md` already commits to at least a noise layer and a pitched layer per token; the target removes the cap on layer count and on what a layer may be.
- **Modulation matrix** = named sources (envelopes, LFOs, per-trigger random, velocity/intensity, trigger index) routed to any `AudioParam` with a depth and a curve. Without a matrix, every "X modulates Y" becomes a bespoke control and the surface stops being unbounded.
- **Determinism contract** = every random draw comes from a seeded PRNG, never `Math.random`. Seed derives from `(patch seed, token, trigger index)`. This is not a nicety: it is what makes offline-render fingerprint regression tests possible, and worklets need their own PRNG instance because they run on the audio thread with no shared state.
- **Two clocks.** Authoring-time parameters (what the studio edits) versus trigger-time parameters (what a specific playback resolves to after velocity, randomisation and macro evaluation). Controls that only make sense at one of the two are marked in their perceptual note.

Standard automation vocabulary used below: `setValueAtTime`, `linearRampToValueAtTime`, `exponentialRampToValueAtTime` (cannot touch or cross zero — needs an epsilon around 1e-4), `setTargetAtTime` (exponential approach with a time constant, the natural fit for decay), `setValueCurveAtTime` (arbitrary breakpoint array, linearly interpolated between points).

---

## 3. Sources (SRC) — 37 controls, 6 must

| ID | Control | Perceptual role for short UI sounds | Range / default / unit | Web Audio | CPU | Priority |
|---|---|---|---|---|---|---|
| SRC-01 | Source type per layer | Decides what kind of physical event the layer implies. The single highest-leverage control in the studio. | enum: `osc`, `noise`, `modal`, `pluck`, `impulse`, `granular` / `osc` | host | nil | must |
| SRC-02 | Oscillator waveform | Sine reads as pure and polite; triangle as soft-bodied; square as hollow and synthetic; sawtooth as buzzy and aggressive. | `sine`\|`square`\|`sawtooth`\|`triangle` / `sine` | native | nil | must |
| SRC-03 | Custom `PeriodicWave` harmonic table | Direct control of the partial series, which is what makes a tone read as ceramic versus metal. Implementations band-limit it, so it never aliases the way a hand-written worklet oscillator does. | real/imag arrays, 2–64 partials useful / 1 partial | native+gen | nil | high |
| SRC-04 | Harmonic count / band limit | Caps brightness and stops content folding near Nyquist on 44.1 kHz contexts. | 1–256 / 32 | native+gen | nil | later |
| SRC-05 | Wavetable morph | Crossfade between two `PeriodicWave`s over the sound's life; gives evolving timbre in 80 ms. Requires two oscillators and a crossfade, since a wave cannot be swapped mid-ramp. | 0–1 / 0 | native+gen | nil | later |
| SRC-06 | Sub-oscillator level | Octave-down sine adds weight and "thunk" without brightness. The cheapest way to make a click feel expensive. | -60–0 dB / off | native | nil | high |
| SRC-07 | Unison voices and cents spread | Thickness and chorusing. Rarely right for UI sound; it smears the transient. | 1–7 voices, 0–30 cents / 1, 0 | native | nil–low | later |
| SRC-08 | FM modulator ratio | Integer ratios give harmonic, bell-like or hollow tones; non-integer gives inharmonic and metallic. The classic route to glass and metal without samples. | 0.1–16.0 / 2.0 | native | nil | high |
| SRC-09 | FM index (peak deviation) | Brightness and bite. At short durations, index is heard as attack character more than as timbre. Connect the modulator into the carrier's `frequency` param; depth is the modulator's gain in Hz. | 0–2000 Hz / 0 | native | nil | high |
| SRC-10 | FM modulator waveform | Non-sine modulators multiply sideband count fast; useful for noisy metallic strikes. | as SRC-02 / `sine` | native | nil | later |
| SRC-11 | FM index envelope | Bright on the transient, clean on the tail. This is what separates a synthetic beep from a struck object. | depth 0–2000 Hz, decay 1–200 ms / 0, 30 ms | native | nil | high |
| SRC-12 | FM feedback (self-modulation) | Continuous control from sine to saw-like; a compact source of grit. Needs per-sample feedback, which the graph cannot do: a `DelayNode` feedback loop imposes a one-render-quantum floor. | 0–1 / 0 | worklet | mod | later |
| SRC-13 | AM depth | Tremolo at low rates; sideband colour above ~30 Hz. Adds roughness that reads as mechanical. | 0–1 / 0 | native | nil | high |
| SRC-14 | AM rate | Below 20 Hz is heard as pulsing, 20–200 Hz as roughness, above as timbre. | 0.1–2000 Hz / 6 | native | nil | high |
| SRC-15 | Ring modulation amount | Bipolar multiply; produces sum and difference tones and instant inharmonicity. A `GainNode` with its `gain` driven to a 0 baseline plus a bipolar modulator is a true ring modulator. | 0–1 wet / 0 | native | nil | high |
| SRC-16 | Noise colour | White is hissy and bright; pink is balanced and natural; brown is dull and heavy; blue and violet read as air and fizz. The noise layer carries most of the material identity in a contact sound. | `white`\|`pink`\|`brown`\|`blue`\|`violet` / `pink` | native+gen | nil | must |
| SRC-17 | Noise density / dust | Sparse random impulses instead of continuous noise. Reads as grit, paper, granular contact. | 1–5000 events/s / continuous | native+gen | low | later |
| SRC-18 | Noise buffer seed | Determinism, and a cheap variation axis: same recipe, different grain. Buffers are shareable across voices, so generating a small pool at init beats regenerating per trigger. | uint32 / patch seed | host | nil | high |
| SRC-19 | Noise playback rate | Shifts the buffer's spectrum and its grain rate together. A fast way to age or brighten a texture. | 0.25–4.0 / 1.0 | native | nil | later |
| SRC-20 | Modal bank size | Number of resonant modes. Two modes read as a simple tap, six-plus as a real object. Modal synthesis (excitation into a parallel bank of high-Q bandpass filters) is the standard procedural route to impact sound, per Cook and van den Doel/Pai. | 1–16 / 3 | native | nil–mod | high |
| SRC-21 | Mode frequency ratios | Harmonic ratios read as pitched and musical; stretched or irrational ratios read as metal, glass, and struck plate. This is the single strongest material cue available. | 1.0–20.0 per mode / material template | native | nil | high |
| SRC-22 | Per-mode decay | High modes decaying faster than low modes is what physical damping sounds like. Uniform decay sounds synthetic. `AUDIT.md` already ranks material ring lengths; this is where that ranking gets expressed. | 5–2000 ms / material template | native | nil | high |
| SRC-23 | Per-mode gain (strike position) | Nulling modes emulates striking a plate off-centre. Cheap realism, no extra nodes. | -60–0 dB per mode | native | nil | high |
| SRC-24 | Excitation type | Impulse gives a clean tap; a short noise burst gives a scuffed or brushed contact; a filtered burst gives everything in between. | `impulse`\|`burst`\|`filtered-burst` / `impulse` | native+gen | nil | high |
| SRC-25 | Karplus-Strong fundamental | Plucked string or tine. Feasible with `DelayNode` feedback, but the loop delay cannot go below one render quantum: 128 / 44100 = **344 Hz maximum fundamental** on a 44.1 kHz context. Above that, a worklet is mandatory. | 40–2000 Hz / 220 | native± / worklet | low–mod | later |
| SRC-26 | KS damping (loop lowpass) | How dead the string is. Controls whether the pluck reads as nylon, steel or muted. | 200–12000 Hz / 4000 | native± | low | later |
| SRC-27 | KS loop feedback | Decay length. Above ~0.995 the tail outlives any UI sound. | 0.80–0.999 / 0.96 | native± | low | later |
| SRC-28 | KS excitation width and colour | Attack character of the pluck. | 0.5–20 ms, noise colour / 2 ms, white | native+gen | nil | later |
| SRC-29 | KS pick position | Comb-filtered excitation; moves the pluck from warm to nasal. | 0–0.5 of string / 0.15 | native± | low | later |
| SRC-30 | Impulse width | A one-to-few-sample impulse is the purest transient available and the seed of every contact sound. Width trades click sharpness against low-end thump. | 1–64 samples / 1 | native+gen | nil | must |
| SRC-31 | Click polarity and DC shape | Positive-going versus negative-going transients differ audibly on small speakers, and an unbalanced click leaves DC that eats headroom. | `+`\|`-`\|`bipolar` / `bipolar` | native+gen | nil | later |
| SRC-32 | Grain size | Under 20 ms grains read as texture and pitchless; 20–80 ms as shimmer. Procedural granular over a generated buffer keeps the zero-asset promise. | 2–200 ms / 30 | native+gen / worklet | mod–high | later |
| SRC-33 | Grain density | Sparse reads as sputter, dense as cloud. Per-grain `AudioBufferSourceNode`s are cheap individually but the scheduling churn is what bites. | 1–500 grains/s / 40 | native+gen | mod–high | later |
| SRC-34 | Grain envelope shape | Hann-like envelopes stay smooth; sharp envelopes add per-grain clicks that can be the point. | enum + skew / hann | native+gen | low | later |
| SRC-35 | Grain jitter (position, pitch, pan) | Turns a mechanical stream into a texture. Must be seeded to stay reproducible. | 0–1 each / 0.2 | native+gen | low | later |
| SRC-36 | Layer count per patch | The difference between a token and a designed sound. Three to five layers covers nearly everything in the interface vocabulary; the studio should not cap it at two. | 1–16 / 2 | host | scales | must |
| SRC-37 | Layer enable / solo / mute | Non-negotiable authoring affordance. Designing a five-layer sound without solo is guesswork. | bool per layer | host | nil | must |

---

## 4. Pitch (PCH) — 14 controls, 6 must

| ID | Control | Perceptual role for short UI sounds | Range / default / unit | Web Audio | CPU | Priority |
|---|---|---|---|---|---|---|
| PCH-01 | Base frequency | Perceived size of the object. High reads small, light, and precise; low reads heavy and consequential. Under 100 ms, pitch and brightness partly fuse perceptually. | 20–12000 Hz / 660 | native | nil | must |
| PCH-02 | Note name / MIDI plus reference A4 | Lets a designer tune a whole token set to one key so a flow does not sound accidental. Sequence design needs this the moment more than two sounds play together. | 0–127, A4 = 415–466 Hz / 440 | host | nil | high |
| PCH-03 | Detune | Fine offset without touching the base. Also the unit the whole macro layer should modulate pitch in. | ±1200 cents / 0 | native | nil | must |
| PCH-04 | Octave / semitone transpose | Coarse relocation of an entire patch while keeping its internal ratios. | ±4 oct, ±12 st / 0 | host | nil | high |
| PCH-05 | Pitch envelope depth | A downward sweep is a strike; upward is a release, confirm, or open. This one control carries most of the "up = open, down = close" semantic in a UI set. | ±48 semitones / 0 | native | nil | must |
| PCH-06 | Pitch envelope time | Under 30 ms it fuses into the transient and is heard as timbre; over 80 ms it is heard as a swoop and starts sounding cartoonish. | 1–500 ms / 25 | native | nil | must |
| PCH-07 | Pitch envelope curve | `setTargetAtTime` sounds physical; linear sounds synthetic; exponential ramps cannot pass through or reach zero, so pitch sweeps must stay above an epsilon. | `lin`\|`exp`\|`target`\|`curve` / `target` | native | nil | high |
| PCH-08 | Glide / portamento | Only meaningful for continuous gestures like drag and scrub, where retriggering would machine-gun. | 0–500 ms / 0 | native | nil | later |
| PCH-09 | Per-layer harmonic ratio | Layers at 1.0, 2.76 and 5.4 of the base are a struck bar; at 1.0, 2.0, 3.0 they are a tone. The ratio set is the patch's skeleton. | 0.1–16.0 / 1.0 | host→native | nil | must |
| PCH-10 | Inharmonicity coefficient | One scalar that stretches all partials, sliding a patch from tonal to metallic without re-authoring every ratio. Exactly the kind of control a macro should sit on. | 0–1 / 0 | host→native | nil | high |
| PCH-11 | Microtuning / scale table | Non-12-EDO tuning for token sets that need to sit outside conventional intervals. Real reach, no urgency. | cents table / 12-EDO | host | nil | later |
| PCH-12 | Per-trigger pitch randomisation | The primary defence against the machine-gun effect on repeated interactions. Small and seeded; ±15 cents is usually enough to stop repetition fatigue. | 0–200 cents / 8 | host→native | nil | must |
| PCH-13 | Semantic pitch offset per token | `menu.open` above `menu.close`, `field.reject` below `field.commit`. Encodes meaning in interval rather than in timbre, and survives volume changes. | ±24 st / token table | host | nil | high |
| PCH-14 | Frequency slew limit | Guards against zipper artefacts and supersonic overshoot when a macro drives a fast sweep. A studio without limits produces broken sounds and blames the browser. | 0–10000 cents/s / off | host | nil | later |

---

## 5. Amplitude (AMP) — 18 controls, 9 must

| ID | Control | Perceptual role for short UI sounds | Range / default / unit | Web Audio | CPU | Priority |
|---|---|---|---|---|---|---|
| AMP-01 | Layer gain | Layer balance is where a sound is actually designed. Everything else is ingredients. | -60–+6 dB / -6 | native | nil | must |
| AMP-02 | Patch output level | Per-token trim before the master stage, so tokens balance against each other independent of `volume`. | -40–+6 dB / 0 | native | nil | must |
| AMP-03 | Attack time | Under 2 ms reads as a hard contact; 5–20 ms as a soft or cushioned one; over 40 ms stops feeling like a response to a click at all. Directly implements the `politeness` ruling in `AUDIT.md`. | 0.2–200 ms / 1.5 | native | nil | must |
| AMP-04 | Attack curve | Linear attacks click; exponential and `setTargetAtTime` attacks bloom. At two-millisecond timescales the curve is more audible than the time. | `lin`\|`exp`\|`target`\|`curve` / `lin` | native | nil | must |
| AMP-05 | Hold / peak time | Holding the peak for a few milliseconds gives a body to what would otherwise be an instantaneous spike. | 0–100 ms / 0 | native | nil | high |
| AMP-06 | Decay time | The dominant loudness and material cue after gain. `AUDIT.md` binds decay ranking to material: metal, glass and ceramic ring; wood, paper, rubber and soft do not. | 5–2000 ms / 90 | native | nil | must |
| AMP-07 | Sustain level | Only used by held or continuous tokens (`drag.start`, scrub). Zero for every impact token. | 0–1 / 0 | native | nil | high |
| AMP-08 | Release time | The tail after the gesture ends. Needs a floor of 5–10 ms or stopping a drag sound clicks. | 1–1000 ms / 40 | native | nil | high |
| AMP-09 | Multi-segment envelope | Breakpoint envelopes beyond ADSR: double-decay tails, dips, re-swells. `setValueCurveAtTime` takes an arbitrary array and is the honest way to express these. | 2–32 breakpoints / 4 | native | nil | high |
| AMP-10 | Per-segment curve tension | Convex versus concave between breakpoints. `setValueCurveAtTime` interpolates linearly, so tension must be baked into a denser array. | -1–+1 / 0 | native+gen | nil | later |
| AMP-11 | Velocity / intensity input | Interaction force: pointer velocity, scroll delta, drag distance, confidence. Without an intensity input the whole interface plays at one dynamic and feels dead. | 0–1 / 1.0 | host | nil | must |
| AMP-12 | Velocity → gain curve | Human loudness perception is roughly logarithmic; a linear map wastes most of the range. Prefer a dB span with an exponent, typically 20–30 dB across the range. | exponent 0.3–3.0, span 0–40 dB / 1.0, 24 dB | host | nil | must |
| AMP-13 | Velocity → brightness | Harder contacts are brighter in every real material. Coupling velocity to filter cutoff is what makes intensity feel physical rather than like a volume knob. | 0–100% / 40% | host→native | nil | high |
| AMP-14 | Velocity → pitch | Small upward pitch on hard hits. Subtle, real, easy to overdo. | 0–200 cents / 0 | host→native | nil | later |
| AMP-15 | Per-trigger gain randomisation | Alongside PCH-12, the second half of the anti-repetition defence. 1–3 dB is the useful band. | 0–12 dB / 1.5 | host | nil | must |
| AMP-16 | Anti-click ramp floor | Every gain change needs a minimum 1–2 ms ramp, and every exponential ramp needs an epsilon target because it can never reach zero. Skipping this produces clicks the designer then tries to fix with EQ. | 0.5–10 ms, eps 1e-4 / 2 ms | native | nil | must |
| AMP-17 | Layer crossfade curve | Equal-power versus linear when two layers trade over time. Wrong curve produces an audible dip in the middle of a 60 ms sound. | `lin`\|`equal-power` / `equal-power` | native | nil | later |
| AMP-18 | Intra-patch ducking | One layer's envelope attenuating another, so a transient layer punches through its own body. Standard trick, needs an envelope-follower source in the matrix. | 0–24 dB / 0 | native±/worklet | low | later |

---

## 6. Filtering (FLT) — 23 controls, 8 must

`BiquadFilterNode` supports `lowpass`, `highpass`, `bandpass`, `lowshelf`, `highshelf`, `peaking`, `notch`, `allpass`. All four of its params (`frequency`, `detune`, `Q`, `gain`) are a-rate, so anything in the modulation matrix can drive them at audio rate.

| ID | Control | Perceptual role for short UI sounds | Range / default / unit | Web Audio | CPU | Priority |
|---|---|---|---|---|---|---|
| FLT-01 | Filter slots per layer | One filter is a tone control. A serial chain of three is a sound design tool. | 0–4 / 1 | native | nil | must |
| FLT-02 | Lowpass | The brightness axis, and therefore the warmth axis. The most-used control in any UI sound set. | — | native | nil | must |
| FLT-03 | Highpass | Removes low-end mud and protects small speakers. Every UI sound should be highpassed somewhere. | — | native | nil | must |
| FLT-04 | Bandpass | The core of modal and formant work; a high-Q bandpass on noise *is* a resonant mode. | — | native | nil | must |
| FLT-05 | Notch | Removes a specific resonance without dulling the sound. Surgical, mostly for fixing. | — | native | nil | high |
| FLT-06 | Peaking | Adds a resonant bump: presence, honk, or a material formant. | — | native | nil | high |
| FLT-07 | Lowshelf | Body and weight without changing the transient. | — | native | nil | high |
| FLT-08 | Highshelf | Air and crispness. The polite way to reduce harshness without dulling the attack, since a shelf preserves transient timing better than a steep lowpass. | — | native | nil | high |
| FLT-09 | Allpass | Phase dispersion. Chirps a transient into a "boing"; also the phaser building block. | — | native | nil | later |
| FLT-10 | Cutoff / centre frequency | Where the spectral action is. Should be settable in Hz and as a ratio of the layer's base frequency. | 20–20000 Hz / 2000 | native | nil | must |
| FLT-11 | Q / resonance | Under 1 is a gentle tone shift; 3–10 is character; over 20 is a pitched ring in its own right. `AUDIT.md` assigns resonance ownership to `politeness` and `contrast`, not `warmth`. | 0.0001–1000 / 0.7 | native | nil | must |
| FLT-12 | Shelf / peaking gain | Applies to `lowshelf`, `highshelf`, `peaking` only; silently ignored elsewhere, which is a common source of "why is nothing happening". | ±40 dB / 0 | native | nil | high |
| FLT-13 | Filter detune | Lets cutoff track a pitch source in musical units instead of Hz. | ±2400 cents / 0 | native | nil | later |
| FLT-14 | Filter envelope depth | A bright-to-dark sweep in the first 30 ms is what a physical contact sounds like: high modes die first. Arguably the most important single control after amplitude decay. | ±96 semitones / +24 st | native | nil | must |
| FLT-15 | Filter envelope times | Attack and decay, independent of the amplitude envelope. Coupling them is the classic beginner shortcut and it flattens every sound. | 1–1000 ms / 0, 60 | native | nil | must |
| FLT-16 | Filter envelope curve | Exponential decay on cutoff reads as damping; linear reads as a sweep effect. | as PCH-07 / `target` | native | nil | high |
| FLT-17 | Key tracking | Cutoff following base frequency keeps timbre constant as pitch moves; zero tracking makes high notes dull and low notes bright. Needed the moment PCH-13 exists. | 0–100% / 50% | host→native | nil | high |
| FLT-18 | Slope / order | 12 dB/oct per biquad. Cascade for 24 or 36 dB. Steeper slopes ring more on transients, which is audible at these durations. | 12/24/36/48 dB/oct / 12 | native | nil | high |
| FLT-19 | Custom IIR coefficients | `IIRFilterNode` for responses the biquad set cannot express. Its coefficients are fixed at construction and not automatable, which rules it out of anything modulated. | b[], a[] arrays | native± | nil | later |
| FLT-20 | Formant / vowel bank | Parallel peaking filters at formant frequencies. Gives voice-adjacent character without a single recorded sample. | 3–5 formants | native | nil | later |
| FLT-21 | Comb filter | Short delay with feedback. Metallic, tuned, hollow. Same one-quantum floor as SRC-25 applies to the tuning range. | 0.3–50 ms, fb 0–0.95 | native± | low | later |
| FLT-22 | Q ceiling / self-oscillation guard | High-Q filters excited by an impulse can spike well above the input level and blow the headroom budget. The studio should cap or auto-compensate rather than let a slider produce a clipped sound. | 1–100 cap / 40 | host | nil | high |
| FLT-23 | Tilt EQ | One bipolar control trading low against high energy around a pivot. Two shelves, one knob, and the most natural single destination for a warmth macro. | ±12 dB @ 700 Hz pivot / 0 | native | nil | high |

---

## 7. Time (TIM) — 14 controls, 7 must

| ID | Control | Perceptual role for short UI sounds | Range / default / unit | Web Audio | CPU | Priority |
|---|---|---|---|---|---|---|
| TIM-01 | Patch duration budget | A hard ceiling, enforced. `AUDIO.md` forbids long decorative tails; a budget makes that a property of the system rather than a note in a doc. | 10–2000 ms / 250 | host | nil | must |
| TIM-02 | Layer start offset | Offsetting a body layer 4 ms behind its transient is the difference between one sound and two ingredients. Sub-10 ms offsets are heard as timbre, not as rhythm. | 0–500 ms / 0 | native | nil | must |
| TIM-03 | Layer duration | Per-layer truncation independent of envelope, so a tail can be cut cleanly at the budget. | 1–2000 ms / envelope | native | nil | must |
| TIM-04 | Source buffer start offset | `AudioBufferSourceNode.start(when, offset, duration)` takes both natively. Random offsets into a shared noise buffer give free variation without new buffers. | 0–buffer length / random | native | nil | high |
| TIM-05 | Per-trigger timing jitter | Humanisation. Two to five milliseconds of seeded jitter across layers stops repeated triggers phase-locking into a machine sound. Directly serves the `variation` axis. | 0–30 ms / 2 | host | nil | must |
| TIM-06 | Swing / groove | Only relevant for multi-hit tokens and authored flows. | 0–66% / 50% | host | nil | later |
| TIM-07 | Repeat / roll | Two or three fast repeats express a distinct semantic (double confirm, error buzz) that no single hit does. Count plus interval plus decay per repeat. | 1–8 hits, 10–300 ms / 1 | host | scales | high |
| TIM-08 | Retrigger policy and voice cap | What happens on the twentieth click in two seconds. Steal, layer, or ignore, plus a hard voice ceiling. Without this the studio sounds fine and the product distorts. | enum + 1–32 voices / `layer`, 8 | host | nil | must |
| TIM-09 | Debounce / throttle window | `AUDIO.md` requires continuous gestures be throttled or physically modelled. Make the window a control, per token. | 0–500 ms / 40 | host | nil | must |
| TIM-10 | Scheduling lookahead | Scheduling at `currentTime + lookahead` trades latency against jitter. UI sound needs to land inside roughly 20 ms of the gesture to feel caused by it, so the window is tight. | 0–50 ms / 8 | host | nil | must |
| TIM-11 | Tail truncation on stop | A fade-out time applied when a sound is cut short by policy or by page navigation. Needs the AMP-16 floor or it clicks. | 2–200 ms / 15 | native | nil | high |
| TIM-12 | Tempo grid | Optional bpm for authored flows, so a success fanfare is rhythmic rather than approximate. | 40–240 bpm / off | host | nil | later |
| TIM-13 | Sequence event offset | Per-event placement in an authored flow. The repo already has flow authoring; the offset is the control the timeline edits. | 0–30000 ms | host | nil | high |
| TIM-14 | Global time scale | Stretch or compress a whole patch's timings by one factor. Makes a token set feel snappier or more relaxed without re-editing every envelope, and is the correct destination for a density or politeness macro. | 0.25–4.0 / 1.0 | host | nil | high |

---

## 8. Modulation (MOD) — 17 controls, 3 must

| ID | Control | Perceptual role for short UI sounds | Range / default / unit | Web Audio | CPU | Priority |
|---|---|---|---|---|---|---|
| MOD-01 | LFO count | Two is enough for UI work; unbounded is unnecessary and expensive. | 0–4 / 0 | native | nil | high |
| MOD-02 | LFO waveform | Sine wobbles, square gates, saw sweeps, random steps stutter. | as SRC-02 + `random` / `sine` | native | nil | high |
| MOD-03 | LFO rate | Under 20 Hz is modulation; above is timbre and starts overlapping SRC-13/14. For sounds under 200 ms an LFO below 5 Hz completes less than one cycle and behaves as a random offset, which is usually not what the designer meant. | 0.01–200 Hz / 5 | native | nil | high |
| MOD-04 | LFO depth per destination | Depth belongs to the connection, not the LFO, or one LFO cannot serve two destinations at different amounts. | destination units | native | nil | high |
| MOD-05 | LFO phase and retrigger | Free-running LFOs make short sounds non-deterministic. Phase reset on trigger is close to mandatory at these durations. | 0–360°, `free`\|`retrig` / 0, `retrig` | native± | nil | high |
| MOD-06 | LFO fade-in | Vibrato that arrives after the attack. Rarely fits inside a 200 ms sound. | 0–1000 ms / 0 | native | nil | later |
| MOD-07 | Destination routing | Any source to any `AudioParam`. This is the control that makes the surface unbounded rather than a fixed feature list; everything else adds one knob. | matrix | native | nil | high |
| MOD-08 | Sample and hold | Stepped random. Reads as digital, glitchy, mechanical. | rate 1–200 Hz | native+gen | nil | later |
| MOD-09 | Envelope follower | One signal's amplitude driving another parameter. Enables intra-patch ducking (AMP-18) and dynamic filtering. Needs a worklet for a proper detector. | attack/release ms | worklet | low | later |
| MOD-10 | Per-trigger random depth per destination | Generalises PCH-12, AMP-15 and TIM-05 into one mechanism instead of three special cases. This is the `variation` axis's real home. | 0–1 per destination | host | nil | must |
| MOD-11 | PRNG seed hierarchy | Patch seed, token seed, trigger index. Reproducible renders, diffable sounds, fingerprint regression tests, and shareable "this exact sound". `Math.random` cannot deliver any of that. | uint32 | host | nil | must |
| MOD-12 | Round-robin variant count | Pre-resolve N variants at author time and cycle them. Costs nothing at trigger time and defeats repetition without live randomisation. | 1–16 / 1 | host | nil | high |
| MOD-13 | Modulation depth curve | Linear, exponential, or bipolar shaping between source and destination. A linear macro on a logarithmic parameter feels wrong through most of its travel. | enum + exponent | host | nil | later |
| MOD-14 | Matrix slot count and scaling | A finite, inspectable slot list beats implicit connections. Ten to sixteen slots covers real patches. | 0–16 / 4 | host | nil | high |
| MOD-15 | Velocity / intensity as a matrix source | Once intensity is a first-class source, AMP-13 and AMP-14 stop being bespoke controls and become two matrix rows. | source | host | nil | must |
| MOD-16 | Trigger-index drift | Nth-repeat modulation: slight rise or fall across a rapid burst, the way a real object responds to repeated contact. Distinct from randomness and more convincing on fast repeats. | ±depth over 1–16 triggers | host | nil | high |
| MOD-17 | Continuous gesture sources | Scroll velocity, drag distance, pressure. Turns a discrete token set into a physically modelled continuous surface, which is what `AUDIO.md` asks for on continuous gestures. | 0–1 streams | host | nil | later |

---

## 9. Effects (FXP) — 33 controls, 2 must

| ID | Control | Perceptual role for short UI sounds | Range / default / unit | Web Audio | CPU | Priority |
|---|---|---|---|---|---|---|
| FXP-01 | Waveshaper drive | Adds harmonics and perceived loudness without peak level. On a 40 ms click, saturation is heard as density and expensiveness. | 0–40 dB / 0 | native+gen | low | high |
| FXP-02 | Shaper curve type | tanh is warm and forgiving; hard clip is aggressive; wavefolding is metallic and electronic; a quantised table is lo-fi. The curve is a `Float32Array`, generated in code. | enum / `tanh` | native+gen | low | high |
| FXP-03 | Oversampling | `none`, `2x`, `4x`. Without it, drive folds aliases back into the audible band, and on short bright sounds that reads as cheap digital grit. Costs real CPU. | enum / `2x` | native | low–mod | high |
| FXP-04 | Shaper wet/dry | Parallel saturation keeps the transient clean while thickening the body. | 0–1 / 1 | native | nil | high |
| FXP-05 | Bit depth reduction | Quantisation noise; deliberate retro or "digital" character. | 1–16 bits / 16 | native+gen | low | later |
| FXP-06 | Sample rate decimation | Aliasing as an effect. Distinct from bit crushing and more aggressive. | 1–48 kHz / off | worklet | mod | later |
| FXP-07 | Reverb IR generator | A decaying noise burst is a serviceable procedural IR and needs no file. This is the single control that keeps reverb inside the zero-asset promise. | generator params | native+gen | mod | high |
| FXP-08 | Reverb decay (RT60) | Under 200 ms reads as a room or a body resonance and is usable in UI. Over 600 ms violates the no-long-tails constraint. | 20–2000 ms / 180 | native+gen | mod–high | high |
| FXP-09 | IR spectral damping | High frequencies decaying faster is what makes a synthetic IR stop sounding like filtered noise. | 500–16000 Hz / 4000 | native+gen | nil | high |
| FXP-10 | Pre-delay | Separates the direct hit from its space. Ten to twenty milliseconds keeps the transient legible. | 0–100 ms / 8 | native | nil | high |
| FXP-11 | Early reflection taps | Discrete taps before the tail; gives a sense of a specific small space rather than generic wash. | 2–12 taps | native+gen | low | later |
| FXP-12 | Reverb send / wet level | Send-per-layer beats insert-per-layer: one convolver serves the whole patch, which matters because the convolver is the expensive node. | -60–0 dB / -24 | native | nil | high |
| FXP-13 | IR seed | Determinism for the generated IR, and a variation axis in its own right. Generate once at init and share; regenerating per trigger is wasteful. | uint32 | host | nil | high |
| FXP-14 | Delay time | Under 30 ms is comb and metallic; 30–120 ms is slapback; above that it is a repeat and usually too long for UI. | 0.5–500 ms / 60 | native | low | high |
| FXP-15 | Delay feedback | Repeat count. Above 0.6 the tail outlives the budget. | 0–0.95 / 0.25 | native | low | high |
| FXP-16 | In-loop filtering | Repeats getting darker each pass. Without it, delay sounds artificial. | 200–16000 Hz / 3000 | native | nil | later |
| FXP-17 | Ping-pong / stereo delay | Movement and width from a single hit. | L/R offset ms | native | low | later |
| FXP-18 | Chorus | Multiple detuned delayed copies; thickness and shimmer. Smears transients, so it is a body-layer effect only. | rate, depth, voices, mix | native | low | later |
| FXP-19 | Flanger | Sweeping comb; strongly synthetic. Same one-quantum feedback floor. | delay, fb, rate, depth | native± | low | later |
| FXP-20 | Phaser | Allpass chain plus LFO. Cheaper and subtler than flanging. | stages, rate, depth, fb | native | nil | later |
| FXP-21 | Compressor threshold / ratio / knee / attack / release | Evens out a token set's dynamics and adds punch. Note `DynamicsCompressorNode`'s params are k-rate, so they cannot be modulated at audio rate, and its attack behaviour is fixed. | -100–0 dB, 1–20:1, 0–40 dB, 0–1 s, 0–1 s | native | low | high |
| FXP-22 | Makeup gain | The node does not provide one. `reduction` is readable, so makeup can be derived, but it has to be an explicit control. | 0–24 dB / 0 | native | nil | high |
| FXP-23 | Transient shaper | Independent attack and sustain gain. The most useful single effect for interface sound, and the one that most needs a worklet: a proper differential envelope detector is not expressible in the graph. | ±20 dB each / 0 | worklet | mod | later |
| FXP-24 | Pan position | Placing a sound where its UI element is, is the strongest spatial cue available and costs nothing. `StereoPannerNode` uses an equal-power law. | -1–+1 / 0 | native | nil | must |
| FXP-25 | Per-trigger pan randomisation | Small random placement breaks up repetition without any timbral change. Must stay small or list navigation feels seasick. | 0–0.5 / 0.1 | host | nil | high |
| FXP-26 | Stereo width | Mid-side scaling through splitter and merger. Narrow reads as focused and near, wide as ambient and large. | 0–2 / 1 | native | nil | high |
| FXP-27 | Haas widening | Sub-20 ms inter-channel delay for width. Destroys mono compatibility, which is exactly why OUT-10 exists. | 0–20 ms / 0 | native | low | later |
| FXP-28 | Per-layer pan spread | Transient centred, body spread. Adds depth without moving the perceived source. | 0–1 / 0 | native | nil | high |
| FXP-29 | HRTF spatial panner | `PannerNode` with `panningModel: "HRTF"` for genuinely positional UI audio. Convincing and by far the most expensive routine node in the API. | x, y, z | native | high | later |
| FXP-30 | Insert versus send routing | Per-layer inserts for character, patch-level sends for shared space. The distinction is what keeps the convolver count at one. | topology | host | nil | high |
| FXP-31 | Patch wet/dry | One control to pull all ambience back at once when a token set turns out too wet in situ. | 0–1 / 0 | native | nil | high |
| FXP-32 | DC blocking highpass | Asymmetric shapers and single-polarity impulses leave DC that steals headroom and thumps on small speakers. A 20 Hz highpass at the patch bus is unglamorous and mandatory. | 10–40 Hz / 20 | native | nil | must |
| FXP-33 | Harmonic exciter | Band-limited saturation on highs only; adds presence without brightening the whole spectrum. | amount, band | native+gen | low | later |

---

## 10. Output (OUT) — 16 controls, 6 must

| ID | Control | Perceptual role for short UI sounds | Range / default / unit | Web Audio | CPU | Priority |
|---|---|---|---|---|---|---|
| OUT-01 | Master gain | The `volume` macro's destination. `AUDIO.md` commits to quiet by default, and the current default of 0.34 reflects that. | 0–1 / 0.34 | native | nil | must |
| OUT-02 | Global mute | Required to be easy to reach by the project's own constraints. Ramp it, do not switch it. | bool / false | native | nil | must |
| OUT-03 | Per-token output trim | Balancing a 23-token set is trim work, not redesign work. Distinct from AMP-02 in that it survives patch edits. | -24–+12 dB / 0 | native | nil | high |
| OUT-04 | Headroom ceiling | A declared peak target, typically -6 dBFS, that the studio verifies rather than hopes for. Sounds that clip on a phone speaker are the most common failure in UI audio. | -24–0 dBFS / -6 | host | nil | must |
| OUT-05 | True-peak measurement | Inter-sample peaks exceed sample peaks after resampling. Needs 4x oversampled measurement offline. | dBTP | host | low | later |
| OUT-06 | Lookahead limiter | The last line of defence when many sounds overlap. `DynamicsCompressorNode` is not a brickwall limiter and has no lookahead, so a real one is a worklet. | ceiling, release | worklet | mod | high |
| OUT-07 | Output soft clip | A tanh curve at the output is the cheap, always-on version of OUT-06. Never ship a synthesis engine that can emit above full scale. | on/off, knee / on | native+gen | low | must |
| OUT-08 | Per-token loudness normalisation | Two tokens at the same peak can differ by 10 dB in perceived loudness. Normalising to a perceptual target rather than to peak is what makes a token set feel even. | target LU / -20 | host | nil | high |
| OUT-09 | Loudness model choice | BS.1770 K-weighting is the standard, but its momentary window is 400 ms and most UI sounds are shorter, so a single-block momentary reading is unstable. Integrate over the sound's own length, or use A-weighted energy, and record which model produced the number. | enum / `integrated-BS1770` | host | low | high |
| OUT-10 | Mono compatibility check | UI sound plays on laptop speakers, phone speakers and single Bluetooth pucks. Anything phase-widened must be auditioned folded to mono, and FXP-27 makes this non-optional. | fold-down toggle | native | nil | high |
| OUT-11 | Channel count and downmix policy | Explicit behaviour on non-stereo outputs instead of implicit up/downmixing. | enum / stereo | native | nil | later |
| OUT-12 | Sample rate and `latencyHint` | `interactive` versus `playback` changes buffer size and therefore input-to-sound latency. Sample rate changes the aliasing budget and the one-quantum feedback floor (128 / 44100 = 344 Hz, 128 / 48000 = 375 Hz). A studio that ignores context configuration produces sounds that behave differently in the host app. | 44.1/48 kHz, enum / `interactive` | native | nil | must |
| OUT-13 | Polyphony gain law | Ten simultaneous sounds should not be ten times as loud. Scaling by roughly 1/sqrt(n) tracks perception better than either no scaling or 1/n. | enum / `sqrt` | host | nil | high |
| OUT-14 | Reduced-sound preference | Respect the platform and user preference for reduced motion and reduced sound. An audio product that ignores it is not shippable into other people's interfaces. | auto / respect | host | nil | must |
| OUT-15 | Recording tap | `MediaStreamAudioDestinationNode` for capturing what was actually heard, including timing and polyphony. Different from an offline render, and the only way to capture a live flow. | on/off | native | low | high |
| OUT-16 | Offline render and WAV export | `OfflineAudioContext` renders deterministically and faster than realtime. It is the foundation of every analysis control in the next section, of fingerprint tests, and of handing a designer a file even though the runtime ships none. | duration, rate | native | low | high |

---

## 11. Analysis (ANL) — 16 controls, 4 must

Analysis is a design surface, not a debugging afterthought. Most bad UI sound is bad in ways a meter shows instantly: too much energy at 3 kHz, a 900 ms tail nobody intended, two tokens 8 dB apart.

| ID | Control | What it tells the designer | Range / default / unit | Web Audio | CPU | Priority |
|---|---|---|---|---|---|---|
| ANL-01 | Realtime spectrum | Where the energy is. The fastest way to see why a sound is harsh. | `AnalyserNode` FFT | native | low | must |
| ANL-02 | FFT size and smoothing | 512 gives time resolution for transients, 8192 gives frequency resolution for tails. For sounds under 500 ms, time resolution usually wins. | 32–32768, 0–1 / 2048, 0.6 | native | low | high |
| ANL-03 | Waveform scope | Attack shape, envelope, clipping, DC offset, all visible at a glance. | time domain | native | low | must |
| ANL-04 | Offline render buffer | The exact samples, not a smoothed realtime view. Everything below is more accurate computed from this. | Float32Array | native | low | high |
| ANL-05 | Peak and RMS | Headroom compliance and rough level matching across a token set. | dBFS | host | nil | must |
| ANL-06 | Loudness meter | Perceived level, the number that actually matters when balancing tokens. Constrained by the OUT-09 windowing problem. | LU | host | low | high |
| ANL-07 | Spectral centroid | A single number for brightness. Makes the `warmth` axis measurable instead of a matter of opinion, and `AUDIT.md` already defines warmth as centroid-first. | Hz | host | low | high |
| ANL-08 | Spectral flatness | Noisy versus tonal, as a number. Useful for verifying that a material's noise-to-pitch balance is what the recipe claims. | 0–1 | host | low | later |
| ANL-09 | Decay time measurement | Measured ring time versus authored decay. The direct check on the material damping ranking in `AUDIT.md`. | ms to -60 dB | host | low | high |
| ANL-10 | Onset / attack timing | Time from trigger to peak. The number behind "does this feel instant". Also catches layers accidentally arriving 30 ms late. | ms | host | low | high |
| ANL-11 | Crest factor | Peak-to-RMS. Low crest means a squashed sound that will feel loud and fatiguing at any volume. | dB | host | nil | later |
| ANL-12 | Stereo correlation | Predicts mono collapse before a user finds it. | -1–+1 | host | low | later |
| ANL-13 | Spectrogram | Time and frequency together over the whole sound. The only view that shows a filter envelope doing what you asked. | image | host | mod | high |
| ANL-14 | A/B and null test | Subtract two renders. Silence proves two paths are identical, which is how a refactor is verified rather than asserted. | dB residual | host | low | later |
| ANL-15 | Render fingerprint | A hash of a deterministic offline render, so a sound change becomes a failing test rather than a discovery in production. The repo already carries fingerprint tests; this is the control that keeps them meaningful as the surface grows. | hash | host | low | must |
| ANL-16 | Flow fatigue estimate | Repeated-listening and masking analysis over a whole authored flow. `AUDIO.md` is right that a token that works alone can fail in rhythm; this is the measurement of that. | score | host | mod | later |

---

## 12. Macro mapping

Once the full surface exists, the eight theme controls stop being the engine and become a view onto it. That reframing has consequences worth stating before the mapping table.

**A macro is a function, not a value.** Each macro maps its input to a curve per destination, not a linear scale. `politeness` at 0.5 should not mean "half the attack time"; it should mean a specific point on an authored curve for each destination it owns. Linear macros feel dead through most of their travel because almost every audio parameter is logarithmic.

**Ownership must stay exclusive.** `AUDIT.md` already enforces this: `politeness` leaves pitch alone so `warmth` and `density` keep it; `warmth` leaves resonance and modulation harshness alone so `politeness` and `contrast` keep them. Extend that discipline as the surface grows. Two macros writing the same parameter produces a control surface where nothing does what its label says.

**Hand edits must detach.** The moment a designer sets a filter cutoff directly, that parameter leaves macro control and the UI must show it. Without an override flag, the first manual edit is silently destroyed by the next macro move, and the studio becomes untrustworthy. This is the standard macro-patch problem and it needs solving once, in the model.

**Macros are lossy and that is fine.** Eight numbers cannot address 188 controls. The macro layer's job is to get a designer to 80% in four seconds. The full surface's job is the last 20%. A studio that only has macros is a toy; a studio that only has the full surface is a synthesiser nobody on a product team will open.

**`material` is not a scalar.** It selects a patch template: source topology, mode ratios, damping profile, noise colour, spectral tilt, transient width. Treating it as another 0–1 axis is what forces every material to be a filter setting, which is why materials converge and stop being distinguishable. The other seven macros then modulate whatever template `material` chose.

| Macro | Owns | Destinations | Deliberately does not touch |
|---|---|---|---|
| `material` | Patch topology | SRC-01, SRC-16, SRC-20 through SRC-24 (mode ratios, damping, gains, excitation), SRC-30, AMP-06 base, FLT-23 base, PCH-09 ratio set | Nothing below is off limits to it, but it sets baselines only and never overrides an explicit macro |
| `density` | Mass and compactness | PCH-01 (down with density), SRC-06 sub level, AMP-06 decay, SRC-36 effective layer count, FLT-10 downward, TIM-14, TIM-02 tightening | Resonance, drive |
| `politeness` | Aggression and urgency | AMP-03 attack up, AMP-01/OUT-03 level down, FLT-11 Q down, FXP-01 drive down, FLT-08 highshelf down, SRC-09/SRC-13 modulation depth down, TIM-05 jitter mild | Pitch, per the `AUDIT.md` ruling |
| `contrast` | Inter-token separation | The *spread* of PCH-13 semantic offsets, AMP-02 level differences, TIM-01 duration differences, FLT-23 tilt differences across the token set | Any single token's absolute value. This macro operates on a differential, which is why it is the one that most needs the whole surface to exist before it can be honest |
| `mechanical` | Precision and snap | SRC-30 narrower, click layer level up, PCH-10 toward machined ratios, PCH-06 faster, TIM-05 jitter down toward zero, SRC-16 toward filtered white, AMP-04 harder | Overall level, reverb |
| `warmth` | Spectral centroid | FLT-10 down, FLT-08 down, FLT-23 tilt negative, SRC-09 FM index down, FXP-02 toward even-harmonic saturation | Resonance and modulation harshness, per the `AUDIT.md` ruling |
| `variation` | Per-trigger divergence | MOD-10 depth across all destinations, MOD-12 round-robin count, PCH-12, AMP-15, TIM-05, FXP-25, SRC-18 buffer selection | Anything at author time. Variation is strictly a trigger-time macro, which is the cleanest ownership boundary in the set |
| `volume` | Output level | OUT-01, and nothing else, with OUT-08 normalisation underneath so tokens keep their relative balance at every volume | Everything. A volume control that changes timbre is a bug |

Two observations that fall out of the table.

`contrast` and `variation` are structurally different from the other six. `contrast` operates across tokens; `variation` operates across triggers. The other six operate within a patch. A macro model that treats all eight identically will get those two wrong, which matches `AUDIT.md`'s note that `contrast` and `density` are design constructs without literature behind them. The fix is not more research, it is a model with three macro scopes: patch, token-set, and trigger.

The `politeness`-versus-`contrast` budget already documented in `AUDIT.md` (both high, settle to the middle) is a symptom of two macros pulling on the same destinations from opposite directions. With the full surface available, they can be separated: `politeness` takes the level, attack and drive destinations, `contrast` takes only differentials. Then high on both is coherent rather than a compromise.

---

## 13. Minimum viable studio

The smallest control set that makes this genuinely unbounded rather than a toy, ordered so each stage ends in something a designer can use and a test can verify. The test is not "how many knobs" but "can a designer make a sound the authors did not anticipate". That threshold is crossed at stage 4.

**Stage 1 — Layers that are real.** SRC-01, SRC-02, SRC-16, SRC-30, SRC-36, SRC-37, AMP-01, AMP-02, AMP-16, PCH-01, PCH-03, PCH-09, FLT-01 through FLT-04, FLT-10, FLT-11, OUT-01, OUT-02, OUT-12, FXP-32.
Unlocks: arbitrary N-layer patches, each with a source, pitch, level and a filter. Everything after this is refinement of a shape that already holds. *Verify:* a four-layer patch renders offline and its layer count is not baked into any type.

**Stage 2 — Envelopes with teeth.** AMP-03 through AMP-06, FLT-14, FLT-15, PCH-05, PCH-06, TIM-01, TIM-02, TIM-03.
Unlocks: the difference between a beep and a struck object. The filter envelope is the highest-value single addition in this list; a bright-to-dark sweep in the first 30 ms is what physical contact sounds like. *Verify:* ANL-09 measured decay matches authored decay within tolerance.

**Stage 3 — Measurement.** ANL-01, ANL-03, ANL-05, ANL-15, OUT-04, OUT-07, OUT-16.
Placed third on purpose. Without offline render and a fingerprint, every stage after this is unverifiable and every refactor is a gamble. This stage is why the later stages can move fast. *Verify:* two renders of the same seed hash identically; a deliberately clipped patch fails the headroom check.

**Stage 4 — Determinism and variation.** MOD-10, MOD-11, MOD-15, PCH-12, AMP-15, TIM-05, AMP-11, AMP-12, TIM-08, TIM-09, TIM-10.
Unlocks: sounds that survive repetition, intensity that responds to the interaction, and reproducibility. This is the stage where the studio stops being a sound generator and becomes an interface sound system. **The unbounded threshold sits here**, because MOD-10 plus MOD-15 introduce the matrix concept even in reduced form. *Verify:* fifty rapid triggers produce fifty distinct renders from one seed, and replaying the seed reproduces all fifty.

**Stage 5 — Material credibility.** SRC-20 through SRC-24, PCH-10, FLT-18, FLT-23, SRC-06, ANL-07.
Unlocks: materials that are genuinely different objects rather than the same object behind different filters. This is what makes the eight-material claim in `AUDIO.md` defensible, and ANL-07 is what proves it rather than asserting it. *Verify:* spectral centroid and measured decay separate the eight materials on a chart without overlap.

**Stage 6 — The matrix proper.** MOD-01 through MOD-05, MOD-07, MOD-12, MOD-14, MOD-16, AMP-09, AMP-13, FLT-17, PCH-07, PCH-13.
Unlocks: any source to any destination. After this stage, new expressive capability stops requiring new controls, which is the actual definition of unbounded. *Verify:* a patch using a routing the implementer never wrote a special case for.

**Stage 7 — Character and space.** FXP-01 through FXP-04, FXP-07 through FXP-10, FXP-12, FXP-13, FXP-24, FXP-26, FXP-28, FXP-30, FXP-31, FXP-14, FXP-15, FXP-21, FXP-22.
Unlocks: saturation, procedurally generated reverb, stereo placement, glue. Deliberately after the matrix, because effects on an unexpressive source only make it louder. *Verify:* the whole patch runs one convolver via sends, not one per layer, and stays inside the node budget.

**Stage 8 — Balance and safety.** OUT-03, OUT-06, OUT-08, OUT-09, OUT-10, OUT-13, OUT-14, OUT-15, ANL-06, ANL-10, ANL-13, TIM-07, TIM-11, TIM-13, TIM-14, FLT-22, FXP-25, MOD-01 remainder.
Unlocks: a token set that is even, safe on every speaker, honest about polyphony, and respectful of user preference. The stage that makes it shippable into someone else's product rather than demoable in ours.

**Beyond.** Everything marked `later`: Karplus-Strong, granular, worklet-backed transient shaping and limiting, microtuning, HRTF, formants, envelope followers, flow fatigue analysis. Each is real reach. None is on the path to unbounded.

Two ordering notes. Stage 3 before stage 4 is deliberate: determinism is only worth anything if something checks it. And the worklet decision (blob URL versus emitted sidecar, preload timing) has to be made before stage 8 needs OUT-06, so it should be prototyped during stage 7 rather than discovered at the end.
