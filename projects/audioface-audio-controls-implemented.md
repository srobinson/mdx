---
title: Audioface implemented audio controls
type: projects
tags: [audioface, synthesis, web-audio, studio, controls, inventory]
summary: Exact HEAD inventory of the audio parameters, transforms, node graph, UI controls, and hardcoded limits implemented in Audioface
status: active
created: 2026-08-18
updated: 2026-08-18
project: audioface
confidence: high
---

# Audioface implemented audio controls

## Scope and counting rule

This reference describes commit `3eb567528dd799961a88aea06c07a4076a9eedf6` on local `main`. The worktree was clean before inspection. Sources include `packages/engine`, `packages/core`, root `src`, `apps/lab`, `apps/studio`, `audioface.schema.json`, and the tests that pin these contracts.

The count uses authoring degrees, rather than every field written by one compound control:

- **18 exposed parameters** are distinct Studio controls that can change sound or playback: 7 Token Editor controls, 8 Theme Composer controls, 2 Sequence Node controls, and the raw or themed playback mode.
- **13 latent parameters** are stored or processed synthesis degrees with no direct Studio control. Internal coefficient tables and score fields with no playback consumer are documented separately.
- **35 hardcoded ceilings** are independently enforced ranges or fixed capability blocks. Constants that jointly implement one behavior form one ceiling.

The older product description understates the current Studio. `apps/studio/src/components/editor/TokenEditor.tsx::TokenEditor` also exposes layer delay and a compound pitch control.

## Implemented control summary

| ID | Studio control | Owner | Stored or runtime target | Type and UI range | Scope | Theme transform |
| --- | --- | --- | --- | --- | --- | --- |
| E01 | Weight | `apps/studio/src/app/useTokenEditor.ts::TOKEN_EDITOR_MACRO_CONTROLS` | `AudiofaceTokenDefinition.weight` | percent, 0 to 100; stored unit interval | token | Becomes the base for resolved weight, duration, pitch, and material interaction |
| E02 | Brightness | `apps/studio/src/app/useTokenEditor.ts::TOKEN_EDITOR_MACRO_CONTROLS` | `AudiofaceTokenDefinition.brightness` | percent, 0 to 100; stored unit interval | token | Becomes the base for resolved brightness and pitch or filter frequency |
| E03 | Tension | `apps/studio/src/app/useTokenEditor.ts::TOKEN_EDITOR_MACRO_CONTROLS` | `AudiofaceTokenDefinition.tension` | percent, 0 to 100; stored unit interval | token | Becomes the base for resolved tension, FM index, and noise Q |
| E04 | Gain | `apps/studio/src/app/useTokenEditor.ts::updateLayerGain` | `AudiofaceLayer.gain` | percent, 1 to 100; stored linear gain 0.001 to 0.22 | layer | Scaled by velocity, density, politeness, contrast, mechanical, and variation, then clamped to 0.001 to 0.7 |
| E05 | Duration | `apps/studio/src/app/useTokenEditor.ts::updateLayerDuration` | `AudiofaceLayer.duration` | milliseconds, 4 to 240; stored seconds 0.004 to 0.24 | layer | Scaled by weight, density, mechanical, warmth, material damping, and variation, then clamped to 0.004 to 0.35 seconds |
| E06 | Delay | `apps/studio/src/app/useTokenEditor.ts::updateLayerDelay` | `AudiofaceLayer.delay` | milliseconds, 0 to 160; stored seconds 0 to 0.16 | layer | Passed through unchanged |
| E07 | Pitch or Filter | `apps/studio/src/app/useTokenEditor.ts::tuneLayer` | Tone `frequency`; noise filter `frequency`; FM `carrier` | hertz, 40 to 12,000 for noise and 40 to 1,400 for tone or FM | layer | Themed resolution applies the pitch or filter equations after the edit |
| E08 | Material | `apps/studio/src/components/theme/ThemeComposer.tsx::ThemeComposer` | `ThemeSettings.material` | one of 8 materials | theme | Selects four fixed coefficients: pitch, damping, brightness, and resonance |
| E09 | Density | `apps/studio/src/app/useStudioTheme.ts::STUDIO_THEME_CONTROLS` | `ThemeSettings.density` | percent, 0 to 100; unit interval | theme | Changes weight, duration, gain, pitch, and reported density |
| E10 | Politeness | `apps/studio/src/app/useStudioTheme.ts::STUDIO_THEME_CONTROLS` | `ThemeSettings.politeness` | percent, 0 to 100; unit interval | theme | Changes tension, gain, attack, FM index, and noise Q |
| E11 | Contrast | `apps/studio/src/app/useStudioTheme.ts::STUDIO_THEME_CONTROLS` | `ThemeSettings.contrast` | percent, 0 to 100; unit interval | theme | Changes brightness, tension, gain, attack, FM index, noise Q, and filter frequency |
| E12 | Mechanical | `apps/studio/src/app/useStudioTheme.ts::STUDIO_THEME_CONTROLS` | `ThemeSettings.mechanical` | percent, 0 to 100; unit interval | theme | Changes all three semantic metrics, duration, gain, attack, pitch, FM index, noise Q, and filter frequency |
| E13 | Warmth | `apps/studio/src/app/useStudioTheme.ts::STUDIO_THEME_CONTROLS` | `ThemeSettings.warmth` | percent, 0 to 100; unit interval | theme | Changes weight, brightness, duration, attack, computed decay, pitch, and filter frequency |
| E14 | Variation | `apps/studio/src/app/useStudioTheme.ts::STUDIO_THEME_CONTROLS` | `ThemeSettings.variation` | percent, 0 to 18; stored 0 to 0.18 | theme | Adds seeded multiplicative jitter to duration, gain, tone or carrier start pitch, noise Q, and filter frequency |
| E15 | Volume | `apps/studio/src/app/useStudioTheme.ts::STUDIO_THEME_CONTROLS` | engine master `GainNode.gain` | percent, 0 to 100; unit interval | theme and output | Bypasses token resolution and sets master gain with a 0.012 second target time constant |
| E16 | Start | `apps/studio/src/components/sequence/SequenceNodeEditor.tsx::SequenceNodeEditor` | `SequenceStepDraft.delayMs`, then engine `offsetMs` | milliseconds, 0 to 60,000 in 10 ms steps | sequence step | Passed to `resolveStartAt`; negative engine offsets clamp to zero |
| E17 | Velocity | `apps/studio/src/components/sequence/SequenceNodeEditor.tsx::SequenceNodeEditor` | `SequenceStepDraft.velocity` and `AudiofaceMetrics.velocity` | percent, 5 to 100; unit interval 0.05 to 1 | sequence step and playback | Scales layer gain from 0.38 to 1.08 before other gain factors |
| E18 | Raw or Themed | `apps/studio/src/components/editor/TokenEditor.tsx::TokenEditorActions` | `PlaybackMode` | enum, `raw` or `themed` | playback | Raw clones saved layers. Themed applies all resolver transforms |

The compound pitch control preserves a ratio for tone and FM layers. `tuneLayer` sets tone `frequency` and scales `endFrequency` by the same ratio. It sets FM `carrier` and scales `modulator` by the same ratio. Unfiltered noise has a displayed fallback of 1,200 Hz, but `tuneLayer` leaves that layer unchanged.

## Latent synthesis parameters

| ID | Parameter | Owner | Type, unit, and legal stored range | Default | Scope | Current effect |
| --- | --- | --- | --- | --- | --- | --- |
| L01 | Token action | `packages/core/src/tokens.ts::AudiofaceTokenDefinition.action` | `TokenAction`, 18 values | Recipe value; blank token uses `tick` | token | Selects a fixed weight, brightness, and tension offset before theme transforms |
| L02 | Saved token material | `packages/core/src/tokens.ts::AudiofaceTokenDefinition.material` | `AudiofaceMaterial`, 8 values | Recipe value; blank token uses `soft` | token | Root `src/tokens.js::resolveToken` uses it when no material override exists. Package themed playback replaces it with theme material. Raw playback preserves the label but the engine reads only layers |
| L03 | Layer structure | `packages/core/src/tokens.ts::AudiofaceLayer` | ordered nonempty array of `noise`, `tone`, and `fm` layers | Recipe layers; blank token has one tone | token | Determines source count, source types, and summing. Studio can select an existing layer but cannot add, remove, reorder, or change its type |
| L04 | Attack | `packages/core/src/tokens.ts::NoiseLayer`, `ToneLayer`, `FmLayer` | optional seconds, finite and nonnegative, no stored upper bound | Resolver uses 0.0015 when absent; engine uses 0.001 | layer | Sets the linear amplitude ramp duration after themed scaling |
| L05 | Decay | same layer types | optional seconds, finite and nonnegative, no stored upper bound | Resolver uses resolved duration when absent | layer | Resolver computes and stores it. Neither engine reads `layer.decay`, so it has no audible effect |
| L06 | Tone waveform | `packages/core/src/tokens.ts::ToneLayer.waveform` | `sine`, `square`, `sawtooth`, `triangle`, or `custom` | Recipe value; blank token uses `sine` | tone layer | Assigned to `OscillatorNode.type`. No Studio control exists |
| L07 | Tone pitch span | `ToneLayer.endFrequency` relative to `frequency` | optional positive finite hertz, no stored upper bound | Start frequency when absent | tone layer | Engine exponentially ramps start to end across the layer duration. Studio pitch preserves the existing ratio and cannot edit the span independently |
| L08 | Noise filter presence | `NoiseLayer.filter` | optional object | All canonical noise layers use a filter | noise layer | Selects filtered or unfiltered fixed color noise |
| L09 | Noise filter type | `NoiseLayer.filter.type` | 8 Web Audio biquad types | Canonical recipes use `bandpass` | noise layer | Assigned to `BiquadFilterNode.type`. Filter gain is never set, so shelf and peaking filters retain the Web Audio default gain |
| L10 | Noise filter Q | `NoiseLayer.filter.q` | positive finite scalar, no stored upper bound | Recipe value | noise layer | Sets `BiquadFilterNode.Q`; theme resolution changes it and compensates layer gain by the square root of the Q ratio |
| L11 | FM frequency ratio | `FmLayer.modulator` relative to `carrier` | both positive finite hertz, no stored upper bound | Recipe values | FM layer | Studio pitch preserves the ratio. The ratio has no independent control |
| L12 | FM modulation index | `FmLayer.modIndex` | any finite number in storage | Recipe value | FM layer | Sets the modulation gain in hertz, then decays exponentially to 0.0001. The theme clamps resolved values to 0 to 140 |
| L13 | Variation seed | `PlaybackIntent.seed` and `SequenceStepDraft.seed` | string or number for playback; nonempty string for saved sequence steps | `stable` in token resolution; Studio uses a monotonic counter; sequence uses `draft.id:step.key` | playback or sequence step | Chooses deterministic jitter when variation is above zero |

Internal material coefficients and action offsets are also unavailable to Studio. They are fixed policy tables, so they appear under the theme math and hardcoded ceilings rather than in the latent count.

## Core token owner

### Saved token fields

| Parameter | Owning symbol | Type, unit, and legal range | Default or canonical range | Scope | Studio | Clamp or normalization path |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | `packages/core/src/tokens.ts::AudiofaceTokenDefinition` | dotted lowercase `TokenId` matching `^[a-z]+(\.[a-z]+)+$` | Recipe ID | token | Read only | `toTokenId` rejects invalid IDs |
| `label` | same | nonempty string during library validation | Recipe label | token | Editable | No audio effect |
| `category` | same | 8 `TOKEN_CATEGORIES` values | Recipe value | token | Read only | No audio effect; used for sequence lanes |
| `action` | same | 18 `TOKEN_ACTIONS` values | Recipe value | token | Read only | Selects `ACTION_PROFILES` |
| `material` | same | 8 `AUDIOFACE_MATERIALS` values | Recipe value | token | Read only per token | Replaced by theme material in package themed playback |
| `weight` | same | unit interval | canonical 0.18 to 0.76 | token | Editable | `toUnitInterval`, then theme metric equation |
| `brightness` | same | unit interval | canonical 0.32 to 0.90 | token | Editable | `toUnitInterval`, then theme metric equation |
| `tension` | same | unit interval | canonical 0.10 to 0.86 | token | Editable | `toUnitInterval`, then theme metric equation |
| `accent` | same | six digit hex color | Recipe value | token | Read only | No audio effect |
| `layers` | same | nonempty `AudiofaceLayer[]` | 60 canonical layers: 23 noise, 34 tone, 3 FM | token | Existing layer selection only | Each layer resolves independently, then the engine sums all outputs |
| `duration` | same | seconds; must equal `max(layer.duration)` exactly | canonical 0.026 to 0.14 at token level | token, derived | Read only fingerprint | `createTokenLibraryEntry` recomputes it; hydrate validation rejects stale values. Layer delay is excluded from this derivation |

The manual token library validator ignores unknown object keys. `cloneAudiofaceTokenDefinition` also spreads the token and each layer, so extra JSON keys can survive storage and cloning even though the TypeScript types do not declare them. No engine code reads those keys.

### Layer fields

| Parameter | Owning symbol | Type, unit, and legal stored range | Canonical range or default | Studio | Theme transform | Engine consumption |
| --- | --- | --- | --- | --- | --- | --- |
| `type` | `AudiofaceLayer` discriminant | `noise`, `tone`, or `fm` | all three exist | Read only | none | Selects one scheduler |
| `duration` | all layers | positive finite seconds, no stored upper bound | 0.007 to 0.14 | 0.004 to 0.24 | scale and clamp to 0.004 to 0.35 | envelope end and source stop time |
| `gain` | all layers | finite nonnegative linear gain, no stored upper bound | 0.024 to 0.18 | 0.001 to 0.22 | scale and clamp to 0.001 to 0.7 | amplitude envelope peak |
| `delay` | all layers | optional finite nonnegative seconds, no stored upper bound | absent or 0 to 0.11 | 0 to 0.16 | unchanged | shifts source start and layer envelope |
| `attack` | all layers | optional finite nonnegative seconds, no stored upper bound | 0.001 noise or FM; 0.0015 tone | none | scale and clamp to 0.00035 to 0.04 | linear attack, with engine floor 0.0005 |
| `decay` | all layers | optional finite nonnegative seconds, no stored upper bound | canonical value equals duration | none | scale and clamp to 0.003 to 0.35 | unused |
| `waveform` | `ToneLayer` | 5 accepted `OscillatorType` strings | canonical uses sine, square, sawtooth, and triangle | none | unchanged | `OscillatorNode.type` |
| `frequency` | `ToneLayer` | positive finite hertz, no stored upper bound | 108 to 780 | compound Pitch | pitch factor, jitter, clamp 20 to 12,000 | oscillator start frequency |
| `endFrequency` | `ToneLayer` | optional positive finite hertz, no stored upper bound | 78 to 930 | scaled with start pitch | pitch factor, clamp 20 to 12,000 | oscillator exponential ramp target |
| `filter` | `NoiseLayer` | optional object | all canonical noise has bandpass | frequency only | transforms frequency and Q | optional `BiquadFilterNode` |
| `filter.type` | `NoiseLayer` | lowpass, highpass, bandpass, lowshelf, highshelf, peaking, notch, or allpass | bandpass | none | unchanged | biquad type |
| `filter.frequency` | `NoiseLayer` | positive finite hertz, no stored upper bound | 840 to 8,800 | compound Filter | scale, jitter, clamp 80 to 16,000 | biquad frequency |
| `filter.q` | `NoiseLayer` | positive finite scalar, no stored upper bound | 1.5 to 6.4 | none | scale, jitter, clamp 0.1 to 32 | biquad Q |
| `carrier` | `FmLayer` | positive finite hertz, no stored upper bound | 164 to 420 | compound Pitch | pitch factor, jitter, clamp 20 to 12,000 | sine carrier frequency |
| `modulator` | `FmLayer` | positive finite hertz, no stored upper bound | 330 to 840 | scaled with carrier | pitch factor, clamp 20 to 12,000 | sine modulator frequency |
| `modIndex` | `FmLayer` | any finite scalar in storage | 24 to 48 | none | scale and clamp 0 to 140 | modulation gain in hertz |

### Derived metrics and fingerprints

| Value | Owner | Formula or range | Sound input or diagnostic |
| --- | --- | --- | --- |
| `AudiofaceMetrics.velocity` | `packages/core/src/tokens.ts::resolveMetrics` | playback value or 0.66, unit interval by type | gain input |
| resolved `weight`, `brightness`, `tension` | same | metric equations below, each clamped to unit interval | synthesis inputs |
| resolved `density`, `politeness`, `contrast`, `mechanical`, `warmth` | same | normalized theme values | synthesis inputs |
| resolved `variation` | same | 0 to 0.18 | jitter input |
| `SoundFingerprint.durationMs` | `packages/core/src/sound-fingerprint.ts::createSoundFingerprint` | rounded token duration in milliseconds | diagnostic |
| `layerCount` | same | layer array length | diagnostic |
| `noiseRatio` | same | noise energy divided by all layer energy | diagnostic |
| `pitchFloorHz`, `pitchCeilHz` | same | min and max of noise filter frequency, tone endpoints, and FM frequencies | diagnostic |
| `energy` | same | clamp to unit interval of `sum(gain * duration) / 0.09` | diagnostic |
| `transient` | `transientScore` | clamp to unit interval of `max(gain / max(0.0005, attack or 0.0015)) / 180` | diagnostic |
| fingerprint `brightness`, `tension` | `tokenBrightness`, `tokenTension` | resolved metric when present, saved macro otherwise | diagnostic |
| fingerprint `density` | `calculateAudiofaceTokenDensity` | resolved metric when present; otherwise `min(1,duration/0.16)*0.55 + min(1,layers/4)*0.45` | diagnostic |

## Theme, playback, sequence, and score owners

### Theme and playback

| Parameter | Owner | Type and legal range | Default | Scope | Studio | Consumption |
| --- | --- | --- | --- | --- | --- | --- |
| `material` | `packages/core/src/themes.ts::ThemeSettings` | 8 material enum | ceramic | theme | yes | selects material profile |
| `density` | same | unit interval | 0.4 | theme | yes | metric, duration, gain, pitch |
| `politeness` | same | unit interval | 0.72 | theme | yes | metric, gain, attack, FM index, Q |
| `contrast` | same | unit interval | 0.48 | theme | yes | metric, gain, attack, FM index, Q, filter frequency |
| `mechanical` | same | unit interval | 0.34 | theme | yes | broad transform input |
| `warmth` | same | unit interval | 0.54 | theme | yes | metric, duration, attack, computed decay, pitch, filter frequency |
| `variation` | same | finite number clamped 0 to 0.18 | 0.04 | theme | yes | seeded jitter |
| `volume` | same | unit interval | core 0.34; Studio initial theme 1 | theme and output | yes | master gain only |
| `velocity` | `packages/core/src/playback.ts::PlaybackIntent` | optional unit interval | resolver 0.66; raw mode forces 1; Studio token audition fixes 0.72 | playback | sequence control only | gain transform |
| `seed` | same | optional string or number | `stable` if absent | playback | no | deterministic variation |
| `mode` | `packages/core/src/playback.ts::PlaybackMode` | raw or themed | themed | playback | two audition buttons | transform bypass or apply |
| `offsetMs` | `packages/engine/src/index.ts::PlayResolvedOptions` | optional number; negatives clamp to zero | 0 | playback | sequence Start maps to it | source scheduling only |

`PlaybackIntent.at`, `source`, and `label` are trace metadata. The engine does not read them.

### Sequence composition

| Parameter | Owner | Legal range | Default | Studio | Runtime path |
| --- | --- | --- | --- | --- | --- |
| `delayMs` | `packages/core/src/sequences.ts::SequenceStepDraft` | 0 to 60,000, rounded to 10 ms | fixture value; blank flow 0 | Start control | engine `offsetMs` |
| `velocity` | same | 0.05 to 1, rounded to 0.01 | fixture or blank value | Velocity control | playback gain transform |
| `seed` | same | optional nonempty string | `draft.id:step.key` | no | playback variation |

### Score model declarations

`packages/core/src/scores.ts` and `score-schema.ts` define a larger composition model. No engine, Studio, or Lab consumer plays a `ScoreTimeline`. `buildScoreTimeline` only validates and projects display data.

| Declared parameter | Owner | Legal range | Current effect |
| --- | --- | --- | --- |
| score, motif, clip, and transition `durationMs` | `ScoreDraft`, `MotifDraft`, `ScoreClipBase`, `ScoreTransition` | optional finite nonnegative milliseconds | timeline extent only; does not stretch or stop audio |
| clip `atMs` | `ScoreClipBase` | finite nonnegative milliseconds | timeline placement only |
| clip `velocity` and `seed` | `ScoreClipBase` | optional unit interval and nonempty string | copied to projected token events, with no score playback consumer |
| automation target | `AutomationLane` | material, variation, contrast, density, mechanical, politeness, volume, or warmth | projected marker only |
| automation point `atMs` and `value` | automation point types | nonnegative milliseconds; unit interval, 0 to 0.18 variation, or material enum | projected marker only |
| automation `curve` | `AUTOMATION_CURVES` | ease-in, ease-out, linear, or step | projected marker only |
| trigger accent `velocity` | `ScoreTriggerAction` | unit interval | projected action only |
| transition `durationMs` and `curve` | `ScoreTransition` | nonnegative milliseconds and curve enum | projected marker only |

## Root v1 model and Lab

### Root model

The Lab imports root `src`, while Studio imports the packages. `test/lab-studio-audio-parity.test.mjs` checks parity for current canonical playback.

| Root owner | Capability | Difference from packages |
| --- | --- | --- |
| `src/tokens.js::TOKENS` | Same 23 procedural recipes and 60 layers | Token objects omit package `category` and stored token `duration` |
| `src/tokens.js::resolveToken` | Accepts token ID or an arbitrary token object plus material, velocity, semantic metrics, theme controls, variation, and seed | Direct calls use the saved token material if no override exists. Action offsets are applied by `src/themes.js::optionsForToken`, rather than inside `resolveToken` |
| `src/themes.js::THEME_PRESETS` | Studio, Console, Soft Office, and Instrument Panel presets | Package core has only `DEFAULT_THEME` |
| `src/themes.js::ACTION_PROFILES` | Fixed semantic offsets | Includes `expand` and `collapse`, which package `TOKEN_ACTIONS` omits |
| `src/audioface.js::createAudiofaceEngine` | Same tone, noise, FM, envelope, filter, noise buffer, and limiter graph | Eager context, `play` resolves raw token calls, no `stopAll`, no scheduled offset option, and runtime volume clamping |

Root `buildTokenCall` exports only material, weight, brightness, tension, and optional variation. Root `buildThemeJson` exports resolved token summaries, not layer parameters.

### Lab controls

| Lab control | Owner | Range | Audio target |
| --- | --- | --- | --- |
| Material | `apps/lab/src/theme-workbench.js::themeControls` | 8 materials | theme material |
| Density, Politeness, Contrast, Mechanical, Warmth | same | 0 to 100 percent | theme unit intervals |
| Variation | same | 0 to 18 percent | theme variation |
| Volume | same | 0 to 100 percent | master gain |
| Sequence Start | `apps/lab/src/sequence-editor-view.js::bind` | 0 to 60,000 ms, 10 ms step | root sequence delay |
| Sequence Velocity | same | 5 to 100 percent | playback velocity |

The Lab has no token recipe editor. `apps/lab/src/app.js` and `integration-playground.js` pass fixed interaction velocities from 0.42 to 0.90, plus a toggle tension pair of 0.42 or 0.8 and a drag brightness override of 0.38. Scrub and drag velocity are simple formulas capped at 1. `theme-workbench.js::auditionVelocity` maps a range control to 0.38 through 0.95. These are hardcoded audition choices rather than visible authoring controls.

## JSON contract coverage

`audioface.schema.json` describes the generated root contract, not the Studio token library.

| Schema area | Audio fields | Range enforcement |
| --- | --- | --- |
| `theme` | material, density, politeness, contrast, mechanical, warmth, variation, volume | numbers have no min or max; material is only a string |
| `materials` | label, pitch, damping, brightness, resonance | numbers have no min or max |
| `tokens[].recipe` | material, action, weight, brightness, tension, and an array of layer type strings from `recipeSummary` | `additionalProperties: true`; no layer parameter schema |
| sequences | delay and velocity | numbers have no min or max |

The generated contract therefore cannot round trip a saved token recipe. It omits layer frequency, waveform, filter, Q, FM parameters, gain, duration, delay, attack, and decay.

## Implemented synthesis capability

### Layer types

| Layer | Source and graph | Implemented control | Fixed behavior |
| --- | --- | --- | --- |
| Tone | one `OscillatorNode` into the shared gain envelope | waveform, start frequency, end frequency, gain, duration, delay, attack | one exponential pitch ramp across the full duration; no detune, phase, periodic wave data, filter, panning, or other modulation |
| Noise | one looping `AudioBufferSourceNode`, optional biquad, shared gain envelope | filter presence, type, frequency, Q, gain, duration, delay, attack | one cached mono, one second noise buffer per context with a fixed white and low frequency blend; no color selector, seed, stereo width, or filter envelope |
| FM | sine modulator through gain into sine carrier frequency, then shared gain envelope | carrier frequency, modulator frequency, modulation index, gain, duration, delay, attack | both waveforms are sine; modulation index decays exponentially to 0.0001 across the duration; no frequency ratio mode, feedback, envelopes per operator, or operator graph |

### Oscillator, filter, envelope, and modulation details

- Tone supports the four built in periodic waveforms used by canonical recipes. Library validation also accepts `custom`, but no saved periodic wave data exists and neither engine calls `setPeriodicWave`.
- Noise filters accept all eight `BiquadFilterType` values. The engine sets only `type`, `frequency`, and `Q`. Filter gain, detune, and automation stay at Web Audio defaults.
- The amplitude envelope has one linear attack from 0.0001 to layer gain and one exponential fall to 0.0001 at the layer end. There is no sustain stage or separately scheduled release.
- `layer.decay` does not participate in the engine graph. Theme warmth changes a value that playback never reads.
- Tone frequency has one exponential ramp. FM modulation index has one exponential ramp. No arbitrary automation lane reaches a Web Audio parameter.
- Every layer connects directly to the shared master. There is no per token bus, panning, effects send, delay, reverb, distortion, convolution, waveshaping, or sample playback.

## Exact theme transform

Let `clamp01(x)` clamp to 0 through 1. Let `lerp(a,b,x) = a + (b-a)x`. Let the selected action offsets be `Aw`, `Ab`, and `At`.

### Semantic metrics

```text
weight = clamp01(
  token.weight + Aw
  + (density - 0.5) * 0.34
  + (mechanical - 0.5) * 0.16
  - (warmth - 0.5) * 0.08
)

brightness = clamp01(
  token.brightness + Ab
  + (contrast - 0.5) * 0.32
  + (mechanical - 0.5) * 0.16
  - (warmth - 0.5) * 0.10
)

tension = clamp01(
  token.tension + At
  + (contrast - 0.5) * 0.26
  + (mechanical - 0.5) * 0.22
  - (politeness - 0.5) * 0.28
)
```

An explicit `TokenResolveOptions.weight`, `brightness`, or `tension` bypasses its metric equation in package core. Root theme overrides have the same effect because `optionsForToken` chooses the override after computing the theme metric.

### Variation

When variation is zero, random returns 0.5 and every jitter factor is 1. Otherwise, the seed is the string `token.id:seed`, with `stable` as the missing seed value.

```text
jitter(random, variation, amount)
  = 1 + (random() - 0.5) * 2 * variation * amount
```

The jitter amplitudes are 0.75 for duration, 0.55 for gain, 0.42 for tone start frequency and noise Q, 0.38 for FM carrier, and 0.32 for filter frequency. Tone end frequency, FM modulator frequency, and FM modulation index receive no direct jitter.

### Shared layer values

```text
durationScale
  = lerp(0.60, 1.64, weight)
  * lerp(0.72, 1.36, density)
  * lerp(1.24, 0.72, mechanical)
  * lerp(0.90, 1.16, warmth)

duration
  = clamp(layer.duration * durationScale * material.damping
          * jitter(random, variation, 0.75),
          0.004, 0.35)

gainScale
  = lerp(0.38, 1.08, velocity)
  * lerp(0.78, 1.22, density)
  * lerp(1.16, 0.72, politeness)
  * lerp(0.82, 1.26, contrast)
  * lerp(0.92, 1.18, mechanical)

gain
  = clamp(layer.gain * gainScale * jitter(random, variation, 0.55),
          0.001, 0.7)

attackScale
  = lerp(1.80, 0.45, mechanical)
  * lerp(1.30, 0.75, contrast)
  * lerp(0.70, 1.70, politeness)
  * lerp(0.80, 1.45, warmth)

attack
  = clamp((layer.attack or 0.0015) * attackScale,
          0.00035, 0.04)

decay
  = clamp((layer.decay or resolved duration) * lerp(0.82, 1.18, warmth),
          0.003, 0.35)
```

The resolved decay is dead data in both engines.

### Tone and FM pitch

```text
pitchFactor
  = material.pitch
  * lerp(1.16, 0.72, weight)
  * lerp(0.92, 1.18, brightness)
  * lerp(1.18, 0.76, density)
  * lerp(0.82, 1.28, mechanical)
  * lerp(1.14, 0.86, warmth)

tone.frequency
  = clamp(layer.frequency * pitchFactor
          * jitter(random, variation, 0.42),
          20, 12000)

tone.endFrequency
  = clamp((layer.endFrequency or layer.frequency) * pitchFactor,
          20, 12000)

fm.carrier
  = clamp(layer.carrier * pitchFactor
          * jitter(random, variation, 0.38),
          20, 12000)

fm.modulator
  = clamp(layer.modulator * pitchFactor, 20, 12000)

fm.modIndex
  = clamp(
      layer.modIndex
      * lerp(0.55, 1.90, tension)
      * lerp(0.68, 1.70, mechanical)
      * lerp(1.36, 0.62, politeness)
      * lerp(0.72, 1.35, contrast),
      0, 140
    )
```

### Noise filter

```text
q
  = clamp(
      layer.filter.q * material.resonance
      * lerp(0.55, 2.10, tension)
      * lerp(0.72, 1.70, mechanical)
      * lerp(1.45, 0.58, politeness)
      * lerp(0.70, 1.36, contrast)
      * jitter(random, variation, 0.42),
      0.1, 32
    )

noise.gain
  = clamp(sharedGain * sqrt(q / layer.filter.q), 0.001, 0.7)

filter.frequency
  = clamp(
      layer.filter.frequency * material.brightness
      * lerp(0.52, 1.72, brightness)
      * lerp(0.78, 1.38, contrast)
      * lerp(0.82, 1.52, mechanical)
      * lerp(1.28, 0.64, warmth)
      * jitter(random, variation, 0.32),
      80, 16000
    )
```

### Material coefficients

| Material | Pitch | Damping | Brightness | Resonance |
| --- | ---: | ---: | ---: | ---: |
| soft | 0.82 | 0.72 | 0.72 | 0.62 |
| rubber | 0.76 | 0.78 | 0.66 | 0.55 |
| plastic | 0.88 | 0.96 | 0.98 | 0.88 |
| ceramic | 1.26 | 1.28 | 1.12 | 1.08 |
| glass | 1.12 | 1.32 | 1.32 | 1.32 |
| metal | 1.10 | 1.36 | 1.20 | 1.45 |
| wood | 0.94 | 1.06 | 0.74 | 0.68 |
| paper | 1.02 | 0.86 | 0.86 | 0.72 |

### Action offsets

| Action | Weight | Brightness | Tension |
| --- | ---: | ---: | ---: |
| press | 0.02 | -0.02 | -0.04 |
| release | -0.08 | 0.04 | -0.08 |
| snap | 0.06 | 0.08 | 0.16 |
| select | -0.14 | -0.02 | -0.12 |
| confirm | -0.06 | 0.12 | -0.04 |
| reject | 0.08 | -0.06 | 0.18 |
| commit | -0.02 | 0.08 | -0.02 |
| clear | -0.10 | 0.02 | -0.10 |
| open | -0.04 | 0.06 | 0.04 |
| close | 0.08 | -0.04 | -0.04 |
| dock | 0.14 | -0.10 | -0.04 |
| undock | 0.02 | 0.04 | 0.02 |
| tick | -0.18 | 0.02 | -0.16 |
| grab | 0.12 | -0.12 | -0.02 |
| settle | 0.16 | -0.14 | -0.08 |
| arrive | -0.08 | 0.14 | 0.02 |
| success | -0.12 | 0.18 | -0.06 |
| celebrate | -0.16 | 0.24 | 0.08 |

Root `src/themes.js::ACTION_PROFILES` adds `expand = {-0.02, 0.04, 0.06}` and `collapse = {0.08, -0.06, -0.02}`. No root shipping recipe uses them.

## Hardcoded engine literals

The package engine and root engine duplicate the same synthesis constants. The table names package symbols; root equivalents live under the same function names in `src/audioface.js`.

| Owner | Literal | Effect |
| --- | --- | --- |
| `resolveStartAt` | 0.006 seconds | fixed scheduling lookahead |
| `resolveStartAt` | minimum offset 0; divisor 1,000 | rejects negative offset and converts milliseconds to seconds |
| `setVolume` | 0.012 seconds | master gain target time constant |
| `createOutput` | 0.34 | engine volume fallback |
| `createOutput` | threshold -18 dB | fixed compressor threshold |
| `createOutput` | knee 8 dB | fixed compressor knee |
| `createOutput` | ratio 9:1 | fixed compressor ratio |
| `createOutput` | attack 0.002 seconds | fixed compressor attack |
| `createOutput` | release 0.08 seconds | fixed compressor release |
| `scheduleTone` | end frequency floor 20 Hz | guards exponential ramp target |
| `scheduleFm` | carrier and modulator type `sine` | fixed FM waveforms |
| `scheduleFm` | modulation floor 0.0001 | exponential modulation index target at layer end |
| `createLayerOutput` | attack floor 0.0005 seconds | engine envelope floor |
| `createLayerOutput` | missing attack 0.001 seconds | engine fallback after raw playback |
| `createLayerOutput` | amplitude floor 0.0001 | start, minimum peak, and end of envelope |
| `startAndStop` | 0.025 seconds | source stop padding after the requested duration |
| `getNoiseBuffer` | one channel | mono noise source |
| `getNoiseBuffer` | `floor(sampleRate)` samples | one second buffer |
| `getNoiseBuffer` | white random `random*2-1` | unseeded white component |
| `getNoiseBuffer` | low update `(low + 0.02*white) / 1.02` | fixed low frequency component |
| `getNoiseBuffer` | output `white*0.66 + low*2.4` | fixed noise color and component mix |

Zero delay fallbacks and loop indices are implementation values rather than authoring ceilings.

## Hardcoded ceilings

| ID | Owner | Ceiling or fixed capability | Consequence for sound design |
| --- | --- | --- | --- |
| H01 | `packages/core/src/tokens.ts::toUnitInterval` | semantic and theme unit values clamp to 0 through 1 | semantic controls cannot exceed the normalized range |
| H02 | `packages/core/src/themes.ts::createThemeSnapshot` | variation clamps to 0 through 0.18 | jitter depth cannot exceed 18 percent through themes |
| H03 | `packages/core/src/tokens.ts::resolveLayer` | themed duration clamps to 0.004 through 0.35 seconds | no themed layer shorter than 4 ms or longer than 350 ms |
| H04 | same | themed gain clamps to 0.001 through 0.7 | themed layers cannot be silent or exceed 0.7 before summing |
| H05 | same | themed attack clamps to 0.00035 through 0.04 seconds | no themed attack longer than 40 ms |
| H06 | same | computed decay clamps to 0.003 through 0.35 seconds | computed value is bounded even though the engine ignores it |
| H07 | same | tone start frequency clamps to 20 through 12,000 Hz | themed tone start pitch stays inside this band |
| H08 | same | tone end frequency clamps to 20 through 12,000 Hz | themed tone pitch ramps stay inside this band |
| H09 | same | FM carrier clamps to 20 through 12,000 Hz | themed carrier stays inside this band |
| H10 | same | FM modulator clamps to 20 through 12,000 Hz | themed modulator stays inside this band |
| H11 | same | FM modulation index clamps to 0 through 140 | negative and deeper resolved modulation are unavailable |
| H12 | same | noise filter Q clamps to 0.1 through 32 | themed resonance stays inside this range |
| H13 | same | noise filter frequency clamps to 80 through 16,000 Hz | themed noise filtering stays inside this band |
| H14 | `apps/studio/src/app/useTokenEditor.ts::updateLayerGain` | Studio gain authoring clamps to 0.001 through 0.22 | saved Studio edits use less than one third of the themed resolver maximum |
| H15 | `updateLayerDuration` | Studio duration authoring clamps to 0.004 through 0.24 seconds | Studio cannot author the full themed 350 ms maximum or longer raw layers |
| H16 | `updateLayerDelay` | Studio layer delay clamps to 0 through 0.16 seconds | longer layer offsets require external JSON or code |
| H17 | `TokenEditor.tsx::pitchMax` and `useTokenEditor.ts::tuneLayer` | noise Filter UI spans 40 through 12,000 Hz | Studio cannot author the full 16,000 Hz themed filter band |
| H18 | same | tone and FM Pitch UI spans 40 through 1,400 Hz, although `tuneLayer` accepts up to 12,000 | the visible input blocks high tonal and FM base frequencies |
| H19 | `packages/core/src/sequence-editor.ts::normalizeStep` | sequence delay clamps to 0 through 60,000 ms and rounds to 10 ms | sequence timing has a 60 second cap and 10 ms grid |
| H20 | same | velocity clamps to 0.05 through 1 and rounds to 0.01 | sequences cannot author silence or finer velocity changes |
| H21 | `packages/core/src/scores.ts` and `score-schema.ts` | fixed automation targets and four fixed curve names | scores cannot target layer or engine parameters |
| H22 | `packages/core/src/tokens.ts::MATERIAL_PROFILES` | eight fixed four coefficient material profiles | users cannot define or edit material acoustics |
| H23 | `packages/core/src/tokens.ts::ACTION_PROFILES` | fixed action offsets | semantic meaning always imposes these metric shifts |
| H24 | `packages/engine/src/index.ts::resolveStartAt` | 6 ms lookahead and no negative offset | all package playback uses the same scheduling lead |
| H25 | `createOutput` and `setVolume` | 0.34 fallback, fixed 12 ms smoothing | no authoring control for gain smoothing or engine fallback |
| H26 | `createOutput` | one fixed compressor with -18 dB threshold, 8 dB knee, 9:1 ratio, 2 ms attack, and 80 ms release | no bypass or output dynamics control |
| H27 | `scheduleFm` | sine carrier and sine modulator only | FM waveforms and operator topology are fixed |
| H28 | `scheduleFm` | one modulation index ramp to 0.0001 at layer end | FM modulation has no attack, sustain, release, feedback, or arbitrary automation |
| H29 | `createLayerOutput` | one linear attack and one exponential fall to 0.0001 | amplitude has no sustain level, hold, release, envelope curve choice, or use of saved decay |
| H30 | `startAndStop` | source stop is duration plus 25 ms | stop padding is fixed and independent of envelope or effect tail |
| H31 | `getNoiseBuffer` | one cached mono, one second, unseeded fixed color buffer | no noise color, stereo, seed, length, or regeneration control |
| H32 | `connectFilter` | filters exist only on noise and expose type, frequency, and Q | no tone or FM filter, filter gain, detune, or filter envelope |
| H33 | layer union and both engines | no sample or buffer asset layer | imported recordings and samples cannot play |
| H34 | `ToneLayer.waveform` validation and `scheduleTone` | `custom` is accepted, but no periodic wave data or `setPeriodicWave` path exists | users cannot define a custom oscillator shape |
| H35 | score types and `buildScoreTimeline` | score automation, triggers, transitions, and duration remain projection data | the larger score model cannot drive synthesis today |
