# Audioface Fun: Technical Rigidity Audit

Date: 2026-07-18  
Repository revision: `main` at `9faf83d9cc2fbe3fbd2c9ee98ecbea687b2e1a13`  
Scope: production packages, Studio Sequence Audition, the live root validator and contract generator, plus the legacy implementation where it still controls validation or product policy. Repository source remained read only.

Verification: `pnpm run check` passed TypeScript, all 156 tests, and repository contract validation. `git status --short` remained empty after the audit.

## Executive finding

Studio currently presents a token editor without completing an authoring loop. `useTokenEditor` clones a canonical recipe into component state. The user may change three semantic macros and four parameters on existing layers, then audition that temporary clone. There is no create, copy, save, import, export, or library selection path. Sequence playback ignores the clone and resolves the canonical token again by ID. The declared `@audioface/stores` dependency is unused by Studio.

Evidence:

- `apps/studio/src/app/useTokenEditor.ts` :: `useTokenEditor`, `createDraft`
- `apps/studio/src/app/useSequenceAudition.ts` :: `auditionTokenDraft`, `play`
- `apps/studio/src/app/useStudioPlayback.ts` :: `auditionTokenDefinition`, `auditionFlow`
- `packages/core/src/sequence-timeline.ts` :: `resolveSequenceStepPlayback`
- `packages/core/src/playback.ts` :: `resolvePlayback`, `resolveTokenPlayback`
- `packages/stores/src/tokenLibraryStore.ts` :: `useTokenLibraryStore`
- `apps/studio/package.json` :: `dependencies`

The current pipeline is therefore a closed preset resolver with an editor facade:

```text
23 canonical recipes
        ↓
closed token, action, category, material, and layer unions
        ↓
temporary edits to an existing canonical clone
        ↓
mandatory global theme and action profile transformation
        ↓
three fixed synthesis voices and one fixed output chain
        ↓
audition only

Sequence Play takes a separate path:
fixed fixture step → canonical token ID → mandatory theme → engine
```

The highest payoff change is to make a user authored sound a first class asset that can be saved and used in a sequence. The next highest payoff is to separate safety policy from taste policy. Short, polite, material themed sounds should remain excellent defaults. Raw synthesis and imported samples should remain available.

## Priority ranking

Payoff uses 1 to 5. Effort uses S, M, L, and XL.

| Rank | Change | Payoff | Effort | Why |
|---:|---|---:|:---:|---|
| 1 | Complete the authoring loop: copy or create, save, select from the library, use in sequences, export | 5 | M | Today every token edit is temporary and Sequence Play discards it. |
| 2 | Add raw audition plus per token theme mode: raw, inherit, or blend | 5 | M | Users need to hear the values they authored without mandatory house transformation. |
| 3 | Expose layer structure and the parameters already present in the model | 5 | M | Add, delete, duplicate, reorder, mute, solo, waveform, envelope, filter, Q, FM carrier, modulator, and index unlock far more range than new macros. |
| 4 | Add a sample layer and safe sample import | 5 | L | Comical voice clips, branded recordings, foley, and deliberately rough sounds are impossible today. The validator actively rejects audio files. |
| 5 | Replace closed semantic enums with canonical suggestions plus user values | 4 | M | Categories, actions, materials, origins, and IDs currently gate creation before synthesis begins. |
| 6 | Add per step sound overrides and real user flow creation | 4 | M | Sequences can only rearrange canonical IDs inside four fixtures. Edited tokens and per step timbre cannot participate. |
| 7 | Implement real envelopes and parameter automation | 4 | L | `decay` is resolved but ignored by the engine. Every voice otherwise shares one percussive amplitude shape. |
| 8 | Show uncapped measurements and raw values in Studio | 3 | S | Fingerprints saturate early and hide the differences that advanced authoring creates. |
| 9 | Move the root contract and validator onto package APIs | 3 | M | Two policy engines must currently be loosened together and already disagree on action and category vocabularies. |
| 10 | Make Score Mode extensible only when it has a playback executor | 2 | L | The schema enumerates automation, triggers, and transitions, but the engine does not consume them. |

## 1. Studio authoring gates

### 1.1 The editor cannot create or persist a sound

`apps/studio/src/app/useTokenEditor.ts` :: `useTokenEditor` always obtains its source through `getAudiofaceToken(selectedTokenId)`. `createDraft` only clones that catalog definition. The returned state has no operation for saving, creating a blank token, copying into a library, changing an ID, or selecting a user entry.

`apps/studio/src/components/editor/TokenEditor.tsx` :: `TokenEditor` exposes Audition Draft and Reset. It has no save or library action. The identity fields `id`, `action`, and `category` are readouts. `material` and `accent` are not editable.

`apps/studio/src/app/useSequenceAudition.ts` :: `auditionTokenDraft` sends the temporary definition to solo audition. `play` sends the sequence draft, whose steps contain only canonical `TokenId` values.

`apps/studio/src/app/useStudioPlayback.ts` :: `auditionFlow` calls `resolveSequenceStepPlayback` for each step. That function reaches `getAudiofaceToken` through `resolvePlayback`. The edited definition never enters the sequence path.

`packages/stores/src/tokenLibraryStore.ts` :: `useTokenLibraryStore` exists, as do core copy and validation APIs, but no Studio source file imports `@audioface/stores`. The declared dependency provides no user visible capability.

Loosening:

1. Make the editor operate on a `TokenLibraryEntry` draft.
2. For a canonical selection, present Copy to Library. Also present New Sound from Blank.
3. Save through the existing store boundary and regenerate the fingerprint in the same core operation.
4. Let sequence steps reference a stable library asset ID, including `user:*` and `team:*` entries.
5. Resolve the selected asset definition directly during flow playback.
6. Add duplicate, delete, import, and export after the save path works.

### 1.2 The UI exposes a small subset of each recipe

`apps/studio/src/app/useTokenEditor.ts` :: `TokenEditorState` permits label, weight, brightness, tension, layer delay, layer duration, layer gain, and one coupled pitch value.

`apps/studio/src/components/editor/TokenEditor.tsx` :: `TokenEditor` has no controls for:

- adding, removing, duplicating, reordering, muting, or soloing layers
- changing a layer between noise, tone, and FM
- tone waveform or end frequency
- attack, decay, envelope curve, hold, sustain, or release
- noise filter presence, type, frequency automation, or Q
- FM carrier and modulator independently, modulation ratio, modulation index, or modulation envelope
- token action, category, material, accent, ID, seed, or theme response

`apps/studio/src/app/useTokenEditor.ts` :: `tuneLayer` preserves a tone sweep ratio and an FM carrier to modulator ratio. The user cannot break either coupling. For an unfiltered noise layer, it returns the layer unchanged, so the visible Filter slider would have no audible effect.

Loosening: expose the raw layer model first, then add friendly macro views on top. A Basic view can preserve the current controls. An Advanced view should operate on explicit parameters and structure. Numeric entry should accompany sliders so the UI does not become the range authority.

### 1.3 Studio ranges are narrower than core ranges

| Location and symbol | Current rule | Creative effect | Loosening |
|---|---|---|---|
| `apps/studio/src/app/useTokenEditor.ts` :: `updateLayerDuration` | 4 to 240 ms | No tail, drone, spoken fragment, rhythmic body, or intentionally slow response | Make 4 to 240 ms a UI sound preset. Allow advanced seconds with a duration safety budget. |
| `apps/studio/src/app/useTokenEditor.ts` :: `updateLayerGain` | 0.001 to 0.22 linear gain | Layer balance stays close to canonical recipes | Use decibels, allow minus infinity for mute, and protect the final bus. |
| `apps/studio/src/app/useTokenEditor.ts` :: `updateLayerDelay` | 0 to 160 ms | No echo pattern, anticipation gap, or longer composite phrase | Widen numeric entry. Keep a total scheduled duration and voice budget. |
| `apps/studio/src/app/useTokenEditor.ts` :: `tuneLayer` | 40 to 12,000 Hz | Blocks sub audio modulation and the top audible octave | Derive oscillator limits from sample rate. Separate audible pitch from modulation rate. |
| `apps/studio/src/components/editor/TokenEditor.tsx` :: `pitchMax` | Tone and FM stop at 1,400 Hz; noise stops at 12,000 Hz | The visible UI is far narrower than the hook and resolver | Use logarithmic pitch controls with direct numeric entry and mode specific bounds. |
| `apps/studio/src/components/editor/TokenEditor.tsx` :: `EditorSlider` gain control | 1 to 100 percent of 0.22 | Zero gain is impossible and the percentage hides the actual multiplier | Show dB and permit mute. |
| `apps/studio/src/app/useStudioTheme.ts` :: `STUDIO_THEME_CONTROLS` | Five unit macros, variation to 18 percent, volume to 100 percent | The house macro model is the only global sound design surface | Treat these as a default macro bank. Let users add mappings or bypass them. |

### 1.4 Sequence Audition is a fixture editor

`packages/core/src/sequence-fixtures.ts` :: `SEQUENCE_FIXTURE_IDS` contains four flows. `apps/studio/src/components/sequence/SequenceAudition.tsx` :: `flowOptions` is derived only from those IDs. There is no new flow command, arbitrary flow ID, flow rename, or persistence.

`apps/studio/src/components/sequence/SequenceNodeEditor.tsx` :: `tokens` comes from `listAudiofaceTokens()`. A step cannot select a user token or its current token draft.

`packages/core/src/sequence-editor.ts` :: `deleteSequenceStep` refuses to delete the final step. A blank sequence cannot be authored. `duplicateSequenceStep` imposes a 90 ms offset. `finalizeDraft` always sorts by delay and then key.

`packages/core/src/sequence-editor.ts` :: `normalizeStep` clamps start to 0 through 60,000 ms, quantizes to 10 ms, clamps velocity to 0.05 through 1, and rounds velocity to hundredths. This blocks pre roll, silence through zero velocity, sub 10 ms timing, and sequences longer than one minute.

`packages/core/src/sequences.ts` :: `SequenceStepDraft` offers only token ID, label, delay, velocity, and seed. It has no transpose, rate, gain, duration, layer mute, theme override, parameter automation, repeat, probability, condition, or branch.

Loosening: preserve the four flows as templates. Let the user create an empty flow, insert any library asset, choose a grid or turn it off, set per step overrides, and save the result. Timing normalization should be explicit and reversible rather than silently imposed on every edit.

## 2. Closed catalog and type surface

### 2.1 Production vocabulary

| Location and symbol | Closed set | Effect | Loosening |
|---|---:|---|---|
| `packages/core/src/tokens.ts` :: `AUDIOFACE_MATERIALS` | 8 materials | Every resolved token must use one fixed profile | Ship these as a canonical material pack. Allow user material profiles and raw mode. |
| `packages/core/src/tokens.ts` :: `TOKEN_CATEGORIES` | 8 categories | User tokens must fit the Audioface interface taxonomy | Keep canonical categories as suggestions. Store arbitrary category strings and tags. |
| `packages/core/src/tokens.ts` :: `TOKEN_ACTIONS` | 18 actions | A new expression requires a core type and resolver profile change | Permit user actions with an optional macro profile. Default unknown actions to neutral. |
| `packages/core/src/token-recipes.ts` :: `TOKEN_RECIPES` | 23 recipes | Studio starts and sequences only from this catalog | Treat the catalog as templates and examples. Make the library the runtime source. |
| `packages/core/src/tokens.ts` :: `AudiofaceLayer` | noise, tone, FM | The synthesis vocabulary ends at three percussive voices | Replace the union with a versioned, extensible source and processor graph. |
| `packages/core/src/playback.ts` :: `PLAYBACK_SOURCES` | 7 sources | Custom integrations cannot describe their origin without a core change | Use a string brand or namespaced source with known suggestions. |
| `packages/core/src/token-library.ts` :: `TOKEN_ORIGINS` | audioface, user, team | Plugins, imported packs, projects, and vendors lack provenance | Use an open namespaced origin plus provenance metadata. |

Canonical values can remain strongly typed in their own pack. User authored values should not require additions to a central union.

### 2.2 IDs and library validation

`packages/core/src/tokens.ts` :: `toTokenId` requires at least two lowercase alphabetic segments separated by dots. Digits, spaces, hyphens, underscores, uppercase letters, and a single segment are rejected. IDs such as `error.404`, `brand.v2`, or `8bit.coin` cannot exist.

`packages/core/src/token-library.ts` :: `TOKEN_LIBRARY_ID_PATTERN` adds a fixed `audioface|user|team` prefix and repeats the lowercase alphabetic restriction.

`packages/core/src/token-library.ts` :: `validateTokenLayers` requires at least one layer and positive duration and gain. An explicit silent token, zero gain muted layer, or empty draft is invalid. It validates only the three known layer types.

`packages/core/src/token-library.ts` :: `validateTokenLibrary` requires a stored fingerprint to equal a recomputed fingerprint exactly. Any editing path that forgets to refresh it is rejected. `sourceTokenId` must resolve to the canonical catalog, so provenance cannot point to another user or team sound.

`packages/stores/src/tokenLibraryStore.ts` :: `persistedLibraryOrEmpty` replaces an invalid persisted library with an empty one. Experimental fields or a future widened schema can therefore make authored work disappear from Studio unless migration is explicit.

Loosening:

- Use opaque stable asset IDs plus editable slugs and labels.
- Permit namespaced pack and project origins.
- Add an explicit `silent` source or layer mute instead of requiring positive gain everywhere.
- Make fingerprint derived data, never user supplied persistence authority.
- Preserve invalid imports in quarantine with diagnostics. Do not replace them with an empty library.
- Let provenance reference any immutable asset revision.

### 2.3 Semantic metrics are all unit intervals

`packages/core/src/tokens.ts` :: `toUnitInterval` silently clamps to 0 through 1 and converts any nonfinite value to zero. `AudiofaceTokenDefinition` makes weight, brightness, and tension unit intervals. `ThemeSettings` does the same for density, politeness, contrast, mechanical, warmth, and volume.

This makes a useful Basic control contract, but it also turns semantic adjectives into the only authoring coordinate system. There is no representation for an intentionally extreme value, bipolar modulation, or a custom macro with its own range.

Loosening: keep normalized macros as optional controls. Store raw synthesis values independently. User macros should have declared domains, defaults, and mappings. Invalid values should produce validation errors at import and persistence boundaries instead of silent coercion.

## 3. Resolver taste policy

### 3.1 Every preview is transformed

`packages/core/src/playback.ts` :: `playbackTokenOptions` always supplies the theme material and every theme metric to the resolver. `packages/core/src/tokens.ts` :: `resolveAudiofaceToken` therefore applies a material profile and semantic mappings even when Studio auditions a user edited definition.

The token's authored `material` is ignored during playback because the global theme material wins. The exact frequency, gain, duration, attack, and filter values shown in a recipe are base values, not the values the user hears.

Loosening: add a per asset theme mode:

- `raw`: render authored values exactly, then apply safety only
- `inherit`: apply the theme as today
- `blend`: apply the theme with an amount from 0 through 1
- optional per parameter locks, such as keep pitch raw while inheriting gain and warmth

Studio should show base and resolved values side by side when a transform is active.

### 3.2 Fixed profiles and coupled macros

`packages/core/src/tokens.ts` :: `MATERIAL_PROFILES` maps each material to fixed pitch, damping, brightness, and resonance coefficients. Users cannot add a material or edit the meaning of one.

`packages/core/src/tokens.ts` :: `ACTION_PROFILES` adds fixed weight, brightness, and tension biases by action before the user hears a token. Unknown actions are impossible at the type level.

`packages/core/src/tokens.ts` :: `resolveMetrics`, `resolveLayer`, and `pitchFactor` couple every macro to several raw parameters. For example, politeness changes gain, attack, FM index, filter Q, and derived tension. Contrast pushes many of the same parameters in the other direction. Density changes duration, gain, pitch, and weight. A user cannot ask for a polite loud sound, a warm short sound, or a heavy high pitched sound without fighting hidden transformations.

`packages/core/src/tokens.ts` :: the F13 Q compensation inside `resolveLayer` changes gain whenever filter Q changes. This is sensible for theme consistency, but it prevents resonance from altering band energy in raw sound design.

Loosening: make material and action mappings inspectable data. Allow per asset overrides and custom mappings. Apply bandwidth compensation in theme mode and leave it optional in raw mode.

### 3.3 Exact resolver clamps

| Location and symbol | Hard range | What it removes | Recommended status |
|---|---:|---|---|
| `packages/core/src/tokens.ts` :: `resolveMetrics` | variation 0 to 0.18 | Large pitch, timing, and timbre variation | Soft default. Allow per parameter depth and distributions. |
| `packages/core/src/tokens.ts` :: `resolveLayer` duration | 0.004 to 0.35 seconds | Sustains, tails, phrases, drones, and spoken material | Soft default. Use a larger explicit render budget. |
| `packages/core/src/tokens.ts` :: `resolveLayer` gain | 0.001 to 0.7 | Silence, inversion, and deliberate saturation before the bus | Allow zero and dB control. Keep output safety. |
| `packages/core/src/tokens.ts` :: `resolveLayer` attack | 0.00035 to 0.04 seconds | Slow fades and swell shapes | Soft default. Envelope duration must stay bounded. |
| `packages/core/src/tokens.ts` :: `resolveLayer` decay | 0.003 to 0.35 seconds | Long or abrupt decay design | Remove from the taste clamp after the engine uses it. |
| `packages/core/src/tokens.ts` :: `resolveLayer` tone and FM frequencies | 20 to 12,000 Hz | Top octave, sub audio modulators, and unusual sweeps | Use Nyquist aware source bounds and separate modulation bounds. |
| `packages/core/src/tokens.ts` :: `resolveLayer` noise filter frequency | 80 to 16,000 Hz | Low rumble and upper air | Use Nyquist aware bounds. Protect headroom separately. |
| `packages/core/src/tokens.ts` :: `resolveLayer` FM index | 0 to 140 | Extreme metallic, comic, alarm, and game timbres | Soft default. Bound CPU and numeric stability instead. |
| `packages/core/src/tokens.ts` :: `resolveLayer` filter Q | 0.1 to 32 | Very broad and very resonant filtering | Widen with peak monitoring and final limiting. |
| `packages/react/src/index.js` :: `pressureVelocity` | 0.18 to 1, fallback 0.66 | Very soft pointer expression | Make the pressure curve and floor configurable. Allow zero. |
| `packages/core/src/sequence-editor.ts` :: `normalizeStep` | delay 0 to 60 s, 10 ms grid; velocity 0.05 to 1, 0.01 grid | Pre roll, silence, microtiming, and longer flows | Move grid and duration choices into the editor. Keep finite schedule bounds. |
| `packages/core/src/score-schema.ts` :: `themeSettingsSchema` | macros and volume 0 to 1; variation 0 to 0.18 | Score automation cannot escape the same house range | Follow the raw, inherit, and blend model. |

## 4. Engine capability ceiling

### 4.1 Three fixed voices

`packages/engine/src/index.ts` :: `scheduleLayer` accepts only the three members of `AudiofaceLayer`.

`packages/engine/src/index.ts` :: `scheduleTone` provides one browser oscillator, one waveform, one start frequency, and one exponential ramp to an end frequency over the full layer duration. Studio cannot choose the waveform or end frequency independently. Custom `PeriodicWave` data has no representation.

`packages/engine/src/index.ts` :: `scheduleNoise` uses one cached mono buffer generated by `getNoiseBuffer`. The buffer has a fixed white and low frequency blend. There is no white, pink, brown, blue, violet, impulse, seeded, stereo, or user supplied noise choice. A noise layer can have at most one static biquad filter.

`packages/engine/src/index.ts` :: `scheduleFm` is a two operator sine on sine topology. Modulation index always decays exponentially to near zero across the layer. Carrier waveform, modulator waveform, ratio lock, feedback, additional operators, and independent envelopes are unavailable.

### 4.2 One fixed percussive envelope

`packages/engine/src/index.ts` :: `createLayerOutput` always starts near zero, ramps linearly to gain over attack, then decays exponentially to near zero at `duration`. There is no hold, sustain, release, curve choice, retrigger mode, or multisegment envelope.

`packages/core/src/tokens.ts` :: `resolveLayer` computes and returns `decay`. `packages/engine/src/index.ts` :: `createLayerOutput` never reads it. Warmth modifies decay in the resolver without modifying rendered audio. Exposing the current decay field would therefore give the user a dead control.

Loosening: define an explicit amplitude envelope with segments and curves, then use it for every source. Preserve the current impact envelope as a preset.

### 4.3 Missing synthesis capabilities

| Capability | Current evidence | Creative payoff | Effort |
|---|---|---:|:---:|
| Layer structure controls | `apps/studio/src/components/editor/TokenEditor.tsx` :: `TokenEditor` | 5 | M |
| Real envelope | `packages/engine/src/index.ts` :: `createLayerOutput` | 5 | M |
| Sample source and import | `packages/engine/src/index.ts` has no decode or sample source path; `src/validator.js` :: `validateAudioFiles` rejects assets | 5 | L |
| Waveform and sweep controls | `packages/engine/src/index.ts` :: `scheduleTone` | 4 | S |
| Noise color, seed, stereo, and filter chain | `packages/engine/src/index.ts` :: `getNoiseBuffer`, `connectFilter` | 4 | M |
| FM topology and envelopes | `packages/engine/src/index.ts` :: `scheduleFm` | 4 | L |
| Per parameter automation | No engine or token graph symbol represents it | 4 | L |
| Pan and stereo width | No `StereoPannerNode` or channel graph exists | 3 | M |
| Delay, convolution, distortion, bit crush, and dynamics as optional processors | `packages/engine/src/index.ts` creates only gain, compressor, oscillator, buffer source, and biquad nodes | 4 | L |
| Custom oscillator or wavetable | No `PeriodicWave` data or `setPeriodicWave` call exists | 3 | L |
| Ring modulation, AM, resonators, granular playback | No source or processor representation exists | 3 | XL |

A small versioned graph is preferable to adding more cases to `AudiofaceLayer`. Sources, envelopes, filters, modulators, and processors can remain simple discriminated nodes while permitting new node kinds through versioned packs.

### 4.4 The output chain mixes safety with tone

`packages/engine/src/index.ts` :: `createOutput` fixes a `DynamicsCompressorNode` at threshold minus 18 dB, knee 8, ratio 9, attack 2 ms, and release 80 ms. This helps contain peaks, but it also imposes one dynamics character on every sound. `setVolume` trusts the branded type at runtime and does not clamp a forged or imported value.

Loosening: retain a hard final safety stage. Separate it from optional character dynamics. Add peak and loudness metering, clamp runtime master gain, and define a true ceiling. Allow users to add distortion or compression before the safety stage.

## 5. Feedback and inspection also enforce the house range

`packages/core/src/sound-fingerprint.ts` :: `createSoundFingerprint` clamps energy, transient score, noise ratio, and density into unit intervals. Energy saturates at total `gain × duration` of 0.09. For unresolved definitions, density saturates at 160 ms and four layers. Larger or stranger sounds become indistinguishable in the readout.

`packages/core/src/sound-fingerprint.ts` :: `tokenBrightness`, `tokenTension`, and `tokenDensity` often report authored or resolved semantic metrics rather than measuring rendered audio. An extreme filter or imported sample could sound bright while retaining a low semantic brightness score.

`packages/core/src/tokens.ts` :: `calculateAudiofaceTokenDuration` ignores layer delay. `createSoundFingerprint` uses that duration, so a delayed layer can extend audible span without appearing in the duration metric.

`apps/studio/src/components/inspector/SignalInspector.tsx` :: `buildAnatomy` and the associated visual styles impose minimum bar sizes and cap delay position. These are visual choices, but they hide extremes when the authoring ranges expand.

`packages/core/src/score-timeline.ts` :: `timelineEvent` gives every score event a fixed 72 ms display duration, regardless of the token's resolved sound. `clip.durationMs` changes clip extent but does not stretch or otherwise transform child sound events.

Loosening: display uncapped raw values, dB, true audible span including delay, spectrum, waveform, peak, loudness, and voice count. Semantic fingerprints can remain a separate comparison view.

## 6. Score and automation constraints

Score Mode is not the immediate bottleneck because Studio does not expose it and the engine does not execute it. Its types nevertheless encode another closed authoring surface.

`packages/core/src/scores.ts` closes:

- `MOTIF_INTENTS` to 8 values
- `SCORE_TRACK_KINDS` to 5 values
- clip kinds to token, motif, and sequence
- `AUTOMATION_CURVES` to ease in, ease out, linear, and step
- `UNIT_AUTOMATION_TARGETS` to six theme macros
- `SCORE_TRIGGER_EVENTS` to 6 values
- trigger actions to accent, mute, play, and transition

`packages/core/src/score-schema.ts` :: `scoreDraftSchema` and every nested object are strict. Unknown fields are rejected. Times are nonnegative. Unit automation stays at 0 through 1 and variation stays at 0 through 0.18. Automation cannot target a layer, oscillator, filter, envelope, effect, pan, playback rate, or sample region.

`packages/core/src/score-validation.ts` :: `checkAutomation` rejects points that move backward in time. This is correct for an ordered serialization, but the editor should sort or offer deliberate ordering instead of turning authoring gestures into invalid data.

`packages/core/src/score-timeline.ts` :: `buildScoreTimeline` only projects automation, triggers, and transitions into markers. No package engine symbol consumes those markers. The apparent flexibility is contract level only.

Loosening: defer more Score Mode UI until the asset and raw synthesis model works. When resumed, use namespaced event and track kinds, extensible curve definitions, parameter paths into the sound graph, and an executor shared with sequence playback.

## 7. Live legacy policy gates

The root `src` implementation is reference material for Studio, but it remains live through the root `validate` and `check` scripts. Its restrictions therefore still affect what the repository accepts.

### 7.1 Audio assets are an executable error

`src/validator.js` :: `AUDIO_EXTENSIONS`, `validateAudioFiles` recursively rejects `.mp3`, `.wav`, `.ogg`, `.aac`, and `.flac` anywhere in the project outside `.git` and `node_modules`. This prevents sample import at repository validation time, even if packages and Studio gain support.

Loosening: validate assets instead of banning them. Enforce allowed codecs, decoded duration, channel count, sample rate, file size, license metadata, storage quota, and safe decode behavior. Keep procedural templates as the default pack.

### 7.2 Semantic taste is executable validation

`src/validator.js` :: `validateTokenModel` requires `approve` to alias `confirm`, requires every shipping action to have an action profile, and reserves success for two specific IDs.

`src/catalog.js` :: `CATALOG_VERBS`, `CATALOG_CATEGORIES`, `CORE_CATALOG`, `EXTENSION_PACKS`, and `GOVERNANCE_RULES` define 20 verbs, 8 categories, 49 candidate core entries, 3 fixed extension packs, and three admission rules. `validateCatalog` rejects unknown categories and verbs.

`src/contracts.js` :: `AUDIOFACE_CONSTRAINTS` exports policy statements into the generated agent readable contract, including no audio files, no long decorative tails in default UI sounds, no sound for minor movement, throttled continuous gestures, fixed approval semantics, and rare celebration.

These are valuable product opinions as defaults and lint advice. Several should become warnings or preset guidance. They should not prevent a user from designing a comic hover chirp, a dramatic tail, a dense game UI, or a custom approval vocabulary.

### 7.3 Four house presets remain a reference authority

`src/themes.js` :: `THEME_PRESETS` defines Studio, Console, Soft Office, and Instrument Panel. `normalizeTheme` falls back to Studio and clamps all unit controls plus variation. `ACTION_PROFILES` and `optionsForToken` impose the same semantic biases as production core.

`src/tokens.js` :: `MATERIALS`, `TOKENS`, and `resolveToken` duplicate production material coefficients, recipes, transforms, and clamps.

The two models already drift:

- root catalog actions include `expand` and `collapse`; `packages/core/src/tokens.ts` :: `TOKEN_ACTIONS` does not
- root category IDs include `commandInput`, `surfaces`, and `system`; package category IDs use `command-input`, `surface-navigation`, and `system-transient`
- root has four presets; package core exposes one default theme snapshot

Loosening should happen once. The root contract generator and validator should consume package catalog, resolver, and library APIs or be retired from the shipping path.

### 7.4 Machine and agent contracts reinforce the limits

`audioface.schema.json` requires materials, theme controls, verbs, categories, tokens, sequences, extension packs, and constraints. Many nested objects reject additional properties.

`AUDIO.md` defines crisp contact, short decay, low fatigue, physical material cues, and silence except at meaningful edges as identity. It also asserts that every token carries noise and pitched layers.

`AUDIOFACE.md` governs a tight verb vocabulary, taxonomy over count, meaningful edges, sequence admission, rare celebration, and no new tokens for musical variety.

`ARCHITECTURE.md` explicitly excludes sample import, piano rolls, arbitrary tracks, and DAW language from Score Mode.

These documents shape agent generated work, so changing code alone will preserve the old product behavior. Rewrite the statements as strong defaults, template goals, and lint profiles. Keep only safety requirements as universal constraints.

## 8. What should stay hard

Taste limits and safety limits need separate owners. The following boundaries should remain hard or become stronger:

| Boundary | Existing location | Recommended hard rule |
|---|---|---|
| Final output protection | `packages/engine/src/index.ts` :: `createOutput` | Runtime master gain clamp, measured peak ceiling, transparent final limiter, and no route around it in normal audition. |
| Global mute and volume | `src/contracts.js` :: `AUDIOFACE_CONSTRAINTS` | Keep an immediate mute, conservative default volume, and persistent user level. |
| Finite numeric input | `packages/core/src/token-library.ts` :: `validateTokenLayers`; `packages/core/src/score-schema.ts` | Reject NaN, infinity, invalid automation, and corrupt imported graphs. |
| Scheduler bounds | `packages/engine/src/index.ts` :: `startAndStop`, `stopAll` | Cap total voices, scheduled horizon, loops, and render duration. Always support cancellation. |
| Frequency validity | `packages/engine/src/index.ts` :: oscillator and filter scheduling | Use sample rate aware bounds, block DC and invalid exponential ramps, and monitor resonant peak gain. |
| Sample safety | Missing today | Bound decoded bytes, duration, channels, sample rate, asset count, and decode time. Preserve provenance and license metadata. |
| Browser gesture requirement | `src/contracts.js` :: `AUDIOFACE_CONSTRAINTS`; browser AudioContext behavior | Keep user initiated audio start and predictable autoplay behavior. |
| Persistence recovery | `packages/stores/src/tokenLibraryStore.ts` :: `persistedLibraryOrEmpty` | Version and migrate. Quarantine invalid assets with recovery instead of discarding them. |

Frequency, duration, layer gain, Q, FM index, token vocabulary, sample use, and theme character are poor substitutes for hearing safety. Hearing risk depends on output level, duration, repetition, device gain, and cumulative exposure. Protect the output and scheduler, then let the synthesis space expand.

## 9. Proposed boundary

An elegant split has four independent layers:

1. **Sound asset**: raw sources, envelopes, processors, routing, parameters, metadata, and optional sample references.
2. **Canonical pack**: Audioface recipes, categories, actions, materials, themes, and recommended ranges. This remains curated and locked.
3. **Theme transform**: optional mappings from semantic macros to raw parameters, with raw, inherit, blend, and per parameter lock modes.
4. **Safety policy**: numeric validation, resource budgets, sample limits, runtime master gain, metering, and final output ceiling.

Suggested minimal shape:

```ts
type SoundAsset = {
  id: AssetId;
  label: string;
  category?: string;
  action?: string;
  tags: readonly string[];
  theme: { mode: "raw" | "inherit" | "blend"; amount?: number };
  graph: SoundGraph;
};

type SoundSource =
  | OscillatorSource
  | NoiseSource
  | FmSource
  | SampleSource;

type SafetyPolicy = {
  maxVoices: number;
  maxScheduledSeconds: number;
  maxDecodedBytes: number;
  masterGainMax: number;
  peakCeilingDb: number;
};
```

The canonical pack can still produce the current Audioface identity with no migration burden because the project is pre release. User assets can leave category or action empty, use new strings, bypass themes, and contain sample sources. The engine enforces safety after all creative transforms.

## 10. Practical sequence

### Slice 1: Make current authoring real

- Wire `useTokenLibraryStore` into Sequence Audition.
- Copy a canonical token or create a blank token.
- Save and reload it.
- Select it in a sequence step.
- Make Play resolve the saved definition.
- Add raw audition and resolved audition.

Proof: modify a token, save it, reload Studio, place it in a flow, press Play, and compare the resolved layer object with the saved definition under raw and themed modes.

### Slice 2: Expose current model completely

- Add, duplicate, reorder, mute, solo, and delete layers.
- Expose waveform, end frequency, attack, decay, filter type and Q, and all FM parameters.
- Implement decay in the engine.
- Replace percentage gain with dB and logarithmic pitch controls.
- Convert current ranges to Basic view defaults.

Proof: author a sustained square sweep, an unfiltered noise burst, a high index FM buzz, and a silent muted layer without editing code.

### Slice 3: Add the missing creative primitives

- Add a sample source and safe import.
- Add parameter envelopes and automation.
- Add pan, delay, distortion, and convolution as processors.
- Add noise colors and seeded noise.

Proof: author one comic voice clip, one deliberately brash game sound, one wide foley sound, and one quiet canonical UI tick through the same asset model and safety bus.

### Slice 4: Open semantics and flows

- Replace user facing category, action, material, source, and origin enums with suggestions plus namespaced strings.
- Add user material and macro mapping editors.
- Add empty flow creation, user assets, per step overrides, optional timing grid, and persistence.
- Move root validation to package APIs and change taste failures to selectable lint profiles.

Proof: create a project vocabulary and material that do not exist in Audioface core, export it, import it into a fresh store, and play it unchanged.

## Conclusion

Audioface already contains useful curated taste, typed playback intent, deterministic resolution, sequence context, and an output safety stage. The rigidity comes from placing taste at every authority boundary: closed types, catalog validation, editor ranges, mandatory transforms, fixed engine topology, fixed fixtures, and agent readable contracts. The fastest route to fun is to make authored assets real, let users audition raw sound, and move universal enforcement into a narrow safety policy.
