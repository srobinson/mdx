---
title: Audioface Studio Impact Bench specification
type: projects
tags: [audioface, studio, product-design, sound-design, impact-bench]
summary: Product specification for the sound-first Audioface Studio built around editable layer clips on a millisecond timeline.
status: active
created: 2026-08-18
updated: 2026-08-18
project: audioface
confidence: high
related: [audioface-studio-concepts, audioface-studio-ia-audit, audioface-audio-controls-implemented, audioface-audio-controls-target]
---

# Audioface Studio Impact Bench specification

## Status and scope

This specification defines the first sound design workspace for the redesigned Audioface Studio. It reflects repository commit `3eb567528dd799961a88aea06c07a4076a9eedf6` and the approved product direction from 2026-08-18.

The sound is the primary object. A token, a theme, and a flow attach to the sound after the sound design workflow works. The base workspace is Impact Bench. It uses layer clips on a millisecond timeline, direct envelope editing, a sound library, analysis, and a parameter rack. Console contributes focus rows and automatic audition. Feel First becomes the later semantic shell. Patch Canvas arrives with the modulation matrix.

The current root remains `apps/studio/src/app/StudioApp.tsx::StudioApp`, which renders `apps/studio/src/components/sequence/SequenceAudition.tsx::SequenceAudition`. The redesign replaces that flow-first composition with one sound-first workbench. The old editor path leaves the product tree when the replacement lands. Pre-release status removes any compatibility requirement.

This document specifies product behavior and information architecture. Current implementation facts carry a source citation. Target controls carry the IDs from `~/.mdx/projects/audioface-audio-controls-target.md`. Current controls and ceilings carry the IDs from `~/.mdx/projects/audioface-audio-controls-implemented.md`.

## Product contract

Impact Bench must satisfy these rules.

1. One open sound owns the work surface.
2. Every layer has stable identity, order, source type, time, envelope, mute, solo, focus, and an addressable parameter set.
3. Direct manipulation and numeric editing update one authoring value.
4. Analysis remains visible during editing.
5. Every parameter is reachable by name.
6. Manual parameter edits survive every later macro move.
7. Keyboard use covers audition, layer operations, time editing, parameter search, and undo.
8. Theme resolution consumes the authored sound and produces a derived view. It never mutates the authored sound.
9. The initial layer model uses the real engine source types: tone, noise, and FM. Current ownership is `packages/core/src/tokens.ts::AudiofaceLayer`, `packages/core/src/tokens.ts::ToneLayer`, `packages/core/src/tokens.ts::NoiseLayer`, and `packages/core/src/tokens.ts::FmLayer`.
10. Studio continues to use package APIs. Root `src` and `apps/lab` remain reference code outside the production app, as required by `ARCHITECTURE.md::Ownership`.

## Current baseline

The implemented control report records 18 exposed parameters E01 through E18, 13 latent parameters L01 through L13, and 35 hardcoded ceilings H01 through H35. Seven of the exposed controls edit the token sound directly. The current Studio cannot add, remove, reorder, or retype a layer under latent parameter L03.

Current theme resolution starts in `packages/core/src/tokens.ts::resolveAudiofaceToken`. `resolveMetrics` derives semantic values. `resolveLayer` applies material, density, politeness, contrast, mechanical, warmth, variation, and velocity to duration, gain, attack, decay, pitch, FM index, filter frequency, and Q. `apps/studio/src/app/useStudioPlayback.ts::auditionTokenDefinition` then passes the resulting `ResolvedPlayback` to the engine.

Impact Bench keeps that one-way resolution shape. The target macro mapping replaces current transform ownership when the semantic shell lands. The implementation must delete the superseded mapping in the same change. Running current and target mappings together would create two writers for one resolved parameter.

## Region map

The reference viewport is 1440 by 900 pixels. The workbench fills the viewport. Page level scrolling is disabled. The library, timeline, rack, and analysis regions own their own overflow.

```text
+--------------------------------------------------------------------------------+
| editorial header and transport                                      64 px      |
+-------------+----------------------------------------------+-------------------+
| sound       | summed waveform                              | parameter rack    |
| library     | time ruler                                   |                   |
| 240 px      |                                              | selected layer    |
|             | layer headers and clips                      | patch             |
| warm chrome | dark work surface                            | output            |
|             |                                              | search            |
|             | add layer                                    |                   |
|             |                                    840 px    |          360 px   |
+-------------+----------------------------------------------+-------------------+
| analysis dock: waveform | spectrum | spectrogram                         220 px |
+--------------------------------------------------------------------------------+
```

| Region | Reference size | Proportion | Hard minimum | Behavior below the minimum |
| --- | ---: | ---: | ---: | --- |
| Header and transport | 1440 by 64 px | 7.1% of height | 56 px high | Keeps sound name, save state, audition, velocity, automatic audition, theme lens, and output mute. Secondary actions move into the command menu. |
| Sound library | 240 by 616 px | 16.7% of width | 220 px wide | Collapses to a 56 px rail before the timeline shrinks. Search opens as an overlay from the rail. |
| Millisecond bench | 840 by 616 px | 58.3% of width | 640 px wide and 430 px high | Keeps the sum lane and clip lanes. Horizontal zoom replaces compression. |
| Parameter rack | 360 by 616 px | 25% of width | 320 px wide | Becomes a modal bottom sheet below a 1016 px viewport. It never narrows below 320 px. |
| Analysis dock | 1440 by 220 px | 24.4% of height | 160 px high | Collapses to a 72 px waveform strip. The user can restore the last chosen analysis view. |

The full desktop authoring layout needs 1180 by 720 pixels. At 1016 to 1179 pixels, the collapsed library keeps a 640 px bench and a 320 px rack. Below 1016 pixels, the rack becomes a bottom sheet and the bench uses the viewport width. Below 768 pixels, Studio becomes a review and audition layout. Editing remains limited to one focused clip and one rack group at a time.

Within the bench, the layer header column is 156 px. The sum lane is 72 px high. The time ruler is 28 px high. Each layer lane is 88 px high with a 76 px minimum. The add layer row is 44 px high. Five default lanes fit at 900 px viewport height. More lanes scroll inside the bench while the ruler and sum lane stay pinned.

The initial ruler shows 0 to 500 ms. Zoom presets show 100, 250, 500, 1000, and 2000 ms. Free zoom ranges from 50 to 2000 ms. A vertical playhead spans the sum lane and every clip lane.

## Visual system

Warm editorial chrome frames a dark technical work surface.

- The header and the sound library retain the existing paper, cream, ink, red accent, and serif identity from `apps/studio/src/styles/studio.css`.
- The bench, analysis dock, and parameter rack use a near black background, restrained grid lines, and high contrast type.
- Serif type names sounds, collections, and major regions. Sans serif type labels controls, values, units, and time.
- Layer identity never depends on color. Each source type has a distinct trace, glyph, and waveform treatment.
- Red marks destructive actions, clipping, and unresolved state. It does not mark ordinary selection.
- Focus uses a bright outline and a persistent header marker. Solo uses an audible state label and a filled control. Mute lowers contrast and keeps the clip geometry legible.

The visual split preserves the current Audioface character while giving dense sound work the contrast and precision it needs.

## Layer clip anatomy

Each lane contains a fixed header and a time positioned clip.

### Header

The header contains these controls in order.

1. A drag handle and order number.
2. A source glyph and designed label, such as Tone, Noise, or FM Pair.
3. An editable layer name.
4. A focus button.
5. Mute and solo buttons.
6. A compact gain value and level meter.
7. A menu for duplicate, retype, and delete.

Focus is editorial selection. It chooses the clip, the inline rack, and the full rack. Focus never changes audio. Mute and solo change audio. Keyboard focus remains visible independently from editorial focus.

### Clip body

The clip begins at `TIM-02 Layer start offset` and ends after `TIM-03 Layer duration`. The left edge therefore represents onset. The right edge represents truncation. Dragging the clip body changes `TIM-02`. Dragging the right edge changes `TIM-03`. Numeric fields in the inline and full racks edit the same values.

The rendered source waveform fills the clip. The amplitude envelope sits above it as a solid curve with these handles.

- Attack end edits `AMP-03 Attack time`.
- Peak end edits `AMP-05 Hold or peak time`.
- Tail shape edits `AMP-06 Decay time`.
- The attack segment menu edits `AMP-04 Attack curve`.
- Vertical gain drag edits `AMP-01 Layer gain`.

Envelope handles appear on the focused clip. Unfocused clips keep a thin envelope curve for comparison. Muted clips keep the curve and use a hatched waveform. A soloed clip receives a `Solo` label in its header and the sum lane switches to the solo render.

Small clips keep a minimum 12 px hit target on each edge without changing their measured duration. When two targets overlap, the focused edge receives pointer priority and the inline numeric value remains available.

### Source specific appearance

| Layer | Current source owner | Clip rendering | Inline source controls |
| --- | --- | --- | --- |
| Tone | `packages/core/src/tokens.ts::ToneLayer`; playback in `packages/engine/src/index.ts::scheduleTone` | A regular periodic trace with a thin pitch contour. A frequency sweep slopes through the clip. Wave shape changes the trace silhouette. | `SRC-01 Source type`, `SRC-02 Oscillator waveform`, `PCH-01 Base frequency`, `PCH-03 Detune`, and `PCH-09 Per-layer harmonic ratio`. |
| Noise | `packages/core/src/tokens.ts::NoiseLayer`; playback in `packages/engine/src/index.ts::scheduleNoise` | A dense stochastic fill. Filter cutoff appears as a vertical brightness gradient. Q appears as a narrow or broad highlighted band. | `SRC-01`, `SRC-16 Noise colour`, `FLT-01 Filter slots`, `FLT-02 Lowpass`, `FLT-03 Highpass`, `FLT-04 Bandpass`, `FLT-10 Cutoff`, and `FLT-11 Q`. |
| FM Pair | `packages/core/src/tokens.ts::FmLayer`; playback in `packages/engine/src/index.ts::scheduleFm` | Two interwoven traces identify carrier and modulator. Trace separation and fill intensity show ratio and modulation depth. | `SRC-01`, `PCH-01`, `PCH-03`, `PCH-09`, and the current carrier, modulator, and modulation index values. The later target maps these values to `SRC-08`, `SRC-09`, and `SRC-11`. |

Tone, Noise, and FM Pair are product labels. Raw discriminants such as `tone`, `noise`, and `fm` never appear in the interface. The current editor exposes the raw discriminant in `apps/studio/src/components/editor/TokenEditor.tsx::TokenEditor`; the new clip header removes that debug output.

## Layer lifecycle

### Add

`Add layer` opens a source picker at the playhead. The first release offers Tone, Noise, and FM Pair because both the current core union and the engine support them. The Stage 1 model generalizes the picker through `SRC-01 Source type per layer`. Impulse, modal, pluck, and granular sources appear when their engine implementations exist. Unavailable sources stay out of the picker.

The new layer starts at the playhead. If the playhead is outside the patch duration budget, the layer starts at 0 ms. The source template supplies audible defaults. The new layer receives focus and its inline rack opens.

`SRC-36 Layer count per patch` is implemented by the layer collection and its add or delete actions. It is a count and capacity indicator, never a numeric knob. The Stage 1 target allows 1 to 16 layers and must avoid a type-level count baked into the engine.

### Remove

Delete removes the focused layer after an undoable confirmation. The command includes the layer name and source type. A patch must contain at least one layer, matching the current nonempty token contract recorded under latent parameter L03 and the target range in `SRC-36`. Delete is disabled for the last layer. `Clear sound` returns to a source chooser and commits a replacement only after the user chooses a source.

### Reorder

Dragging a header reorders the layer. A visible insertion line shows the destination. Keyboard reorder uses `Command+ArrowUp` and `Command+ArrowDown` on macOS, with `Control` on other platforms. Reorder changes the sum order and the visible stack. It does not change time or gain.

Stable layer IDs survive reorder. Index based identity in `apps/studio/src/app/useTokenEditor.ts::useTokenEditor` cannot support reliable focus, undo, macro override, or modulation routing after reorder. The new authoring model addresses every parameter as `sound id + layer id + parameter id`.

### Retype

Retype constructs a new valid source variant and preserves shared authored values: layer ID, name, order, start offset, duration, gain, attack, hold, and decay. It maps one spectral anchor into the destination source.

| From | To | Spectral anchor mapping |
| --- | --- | --- |
| Tone | FM Pair | Tone base frequency becomes carrier frequency. The destination template supplies ratio and modulation index. |
| FM Pair | Tone | Carrier frequency becomes tone base frequency. The destination template supplies waveform and pitch span. |
| Noise | Tone or FM Pair | Filter cutoff becomes the base frequency. Unfiltered noise uses the destination default. |
| Tone or FM Pair | Noise | Base or carrier frequency becomes filter cutoff. The destination template supplies filter type and Q. |

No hidden cache preserves source specific fields. Undo restores the previous variant. This keeps the discriminated union honest and avoids parallel state.

### Duplicate

Duplicate copies the layer into a new stable layer ID and offsets it by 4 ms. The duplicate receives focus. `Option+drag` or `Alt+drag` performs the same action and lets the user place the new onset.

## Parameter disclosure

The target report defines 188 controls. Impact Bench uses three cumulative levels. A control shown on the clip also remains available in the inline and full racks as a numeric field.

### Level 1: clip

The clip holds the parameters that define timing, envelope silhouette, balance, and layer state.

| Stage | Control | Clip affordance |
| --- | --- | --- |
| 1 | `SRC-36 Layer count per patch` | Add and delete actions plus the count in the bench footer. |
| 1 | `SRC-37 Layer enable, solo, and mute` | Header controls. Enable appears as bypass after the source chain gains processors. |
| 1 | `AMP-01 Layer gain` | Vertical drag plus the header value. |
| 2 | `AMP-03 Attack time` | Attack handle. |
| 2 | `AMP-05 Hold or peak time` | Peak handle. |
| 2 | `AMP-06 Decay time` | Tail handle. |
| 2 | `TIM-02 Layer start offset` | Clip position. |
| 2 | `TIM-03 Layer duration` | Right clip edge. |

### Level 2: inline rack

Pressing `Enter` on a focused clip or double clicking its header opens a 120 px rack below the lane. The rack has Source, Pitch, Filter, and Envelope tabs. One tab remains open per source type.

| Group | Stage 1 and Stage 2 controls |
| --- | --- |
| Source | `SRC-01 Source type per layer`, `SRC-02 Oscillator waveform`, `SRC-16 Noise colour`, and `SRC-30 Impulse width`. The rack shows only controls supported by the chosen source. |
| Pitch | `PCH-01 Base frequency`, `PCH-03 Detune`, `PCH-09 Per-layer harmonic ratio`, `PCH-05 Pitch envelope depth`, and `PCH-06 Pitch envelope time`. |
| Filter | `FLT-01 Filter slots per layer`, `FLT-02 Lowpass`, `FLT-03 Highpass`, `FLT-04 Bandpass`, `FLT-10 Cutoff or centre frequency`, `FLT-11 Q or resonance`, `FLT-14 Filter envelope depth`, and `FLT-15 Filter envelope times`. |
| Envelope | Numeric values for `AMP-01`, `AMP-03`, `AMP-05`, `AMP-06`, `TIM-02`, and `TIM-03`, plus `AMP-04 Attack curve`. |

The current Tone, Noise, and FM source model does not yet implement `SRC-30 Impulse width`. The control appears only when an impulse source exists. The target inventory still assigns it to Stage 1, so source work must include that engine path before the picker claims support.

### Level 3: full parameter rack

The full rack shows every control for the focused layer, the patch, and the output. Groups collapse independently. Search uses the control name, ID, source, and layer name. The rack supports `Modified only`, favorites, compare to saved, per parameter revert, and A and B snapshots.

These Stage 1 and Stage 2 controls live only in the full rack because their scope exceeds one clip.

| Scope | Controls |
| --- | --- |
| Patch | `AMP-02 Patch output level` and `TIM-01 Patch duration budget`. |
| Output | `OUT-01 Master gain`, `OUT-02 Global mute`, `OUT-12 Sample rate and latencyHint`, and `FXP-32 DC blocking highpass`. |
| Safety | `AMP-16 Anti-click ramp floor`. It is visible as a patch policy with a safe default and an advanced disclosure. |

The full rack also repeats every clip and inline control. A command palette jump opens the right group, focuses the field, and scrolls the matching clip into view. No target control may exist only behind pointer interaction.

Future stages add their groups to the same rack. Stage 6 adds Modulation and routing from `MOD-01` through `MOD-16`. That stage also unlocks Patch Canvas as another view of the same sound model. Patch Canvas never owns a second patch format.

## Focus rows

Focus rows solve cross layer comparison without weakening the timeline.

Any parameter group offers `Compare across layers`. The rack expands left over part of the bench and changes into a table. Rows are parameters. Columns are layers in stack order. For example, Filter focus shows cutoff, Q, filter type, and envelope depth across every eligible layer. Unsupported cells show `Unavailable` and cannot receive focus.

The selected table cell and the corresponding clip share focus. Arrow keys move between cells. `Shift+Arrow` extends a multi-edit selection. A multi-edit shows the proposed delta before commit. Absolute paste sets the same value. Relative drag adds the same delta while preserving differences.

Focus rows never create a second copy of parameter state. Every cell reads and writes the same addressed parameter as its clip and its normal rack field.

## Audition

The header transport contains Trigger, Stop, velocity, playback scope, repeat, and automatic audition.

- `Space` triggers the full sound from 0 ms.
- `Shift+Space` triggers the focused layer in isolation.
- `Escape` stops current preview playback.
- The velocity field edits audition intensity without changing the authored sound.
- Playback scope offers Authored, Resolved, and In flow after the semantic shell exists. The base workbench starts with Authored.
- The playhead moves across the ruler during every preview.

Automatic audition has three modes.

| Mode | Behavior |
| --- | --- |
| Off | Edits stay silent until an explicit trigger. |
| Release | Default. Pointer edits trigger once on release. Keyboard edits trigger after commit. Numeric fields trigger on Enter or blur. |
| Live | A continuing gesture retriggers at most once every 110 ms. The interval matches `apps/studio/src/app/studioHelpers.ts::THEME_AUDITION_INTERVAL_MS`. The newest preview replaces the previous preview voice with the `AMP-16` ramp floor. |

The first explicit trigger unlocks the audio context. Automatic audition remains disabled until that user gesture succeeds. `apps/studio/src/app/useStudioPlayback.ts::useStudioPlayback` remains the single Studio playback owner. Its `auditionTokenDefinition`, `playResolved`, and engine lifecycle provide the current seam. The workbench retargets that seam from a selected sequence asset to the open authored sound.

The current selection audition in `apps/studio/src/app/useSequenceAudition.ts::auditionStepChange` establishes the throttled interaction pattern. The replacement operates on a sound or a focused layer and removes the flow dependency.

## Analysis surfaces

| Surface | Location | Visibility | Data |
| --- | --- | --- | --- |
| Layer waveform | Inside each clip | Always visible after a source exists | Authored source preview in Stages 1 and 2. Exact rendered samples after Stage 3 adds `ANL-03 Waveform scope` and offline rendering. |
| Summed waveform | Pinned sum lane | Always visible | The current audition scope. Solo changes it to the solo render. A saved comparison can appear as a thin ghost trace. |
| Envelope curve | Above every clip waveform | Always visible. Handles appear only on the focused clip or during envelope focus rows. | Authored amplitude envelope. When the semantic shell is active, a dotted resolved curve overlays the solid authored curve. |
| Spectrum | Analysis dock | Visible after the first audition when the Spectrum tab is selected | `ANL-01 Realtime spectrum`. It holds the last frame after playback so a short sound remains inspectable. |
| Spectrogram | Analysis dock | Visible after Stage 8 adds `ANL-13 Spectrogram` and the user selects its tab | Time and frequency for the full last render. A vertical cursor follows bench time. |
| Expanded waveform | Analysis dock | Visible when the Waveform tab is selected | Exact patch render, peak markers, zero line, and clip warning. Stage 3 adds `ANL-05 Peak and RMS`. |

The analysis tab never changes automatically after the user selects one. Editing a related parameter may pulse the relevant tab label. This avoids visual movement during precise work.

Before Stage 3, authored previews carry a `Preview` label. Stage 3 replaces their data source through the same analysis view contract. The UI never presents an authored approximation as measured output.

The existing `apps/studio/src/components/inspector/SignalInspector.tsx::SignalInspector` displays text fingerprints from `ResolvedPlayback`. Impact Bench replaces that component with measured and authored graphics. `ResolvedPlayback` remains the shared input for resolved analysis, engine playback, and later recording, as required by `ARCHITECTURE.md::Core Event Flow`.

## Macro ownership and manual override

The semantic shell adds the existing eight controls after the sound workflow is complete. The macro mapping follows `~/.mdx/projects/audioface-audio-controls-target.md::Macro mapping`.

Every parameter has one macro state when a theme lens is active.

- Linked: one macro owns a curve that derives the resolved value from the authored value.
- Manual: the authored value wins and the macro cannot write that parameter.

Directly editing a linked parameter performs one transaction. It writes the chosen value and changes the state to Manual. The control then shows a filled `Manual` badge, a broken link glyph, and the name of the detached macro. The track keeps a faint marker for the value that the macro would have produced.

The next macro move updates linked parameters only. Manual parameters remain fixed. The header reports the manual override count. The macro's detail view lists linked and manual destinations separately.

`Reattach to <macro>` previews the resolved value before commit. `Reset manual value` restores the authored value that existed before detachment. Undo restores both the value and the link state.

Macro ownership is exclusive. `material`, `density`, `politeness`, `contrast`, `mechanical`, `warmth`, `variation`, and `volume` keep the destination ownership defined in the target report. `contrast` uses token set scope. `variation` uses trigger scope. The remaining macros use patch scope.

The current theme controls live in `apps/studio/src/components/theme/ThemeComposer.tsx::ThemeComposer` and `apps/studio/src/app/useStudioTheme.ts::useStudioTheme`. Their current resolver path applies a theme to playback without mutating the saved definition. The later shell preserves that direction and adds typed link state, stable parameter addresses, and visible resolved overlays.

## Keyboard model

Keyboard shortcuts are disabled while a text field or numeric field is accepting text, except Escape, Enter, undo, redo, and save.

| Shortcut | Action |
| --- | --- |
| `Space` | Audition the full sound. |
| `Shift+Space` | Audition the focused layer. |
| `Escape` | Stop preview, close a transient overlay, or return focus to the clip in that order. |
| `J` and `K` | Move focus to the next or previous layer. |
| `Enter` | Open or close the inline rack for the focused layer. |
| `ArrowLeft` and `ArrowRight` | Nudge the selected time handle by 1 ms. |
| `Shift+ArrowLeft` and `Shift+ArrowRight` | Nudge the selected time handle by 10 ms. |
| `Option+ArrowLeft` and `Option+ArrowRight` | Nudge the selected time handle by 0.1 ms when the browser supports that resolution. |
| `Command+ArrowUp` and `Command+ArrowDown` | Reorder the focused layer. Use `Control` on other platforms. |
| `Command+D` | Duplicate the focused layer. |
| `Delete` or `Backspace` | Open the undoable delete confirmation for the focused layer. |
| `M` | Toggle mute on the focused layer. |
| `S` | Toggle solo on the focused layer. |
| `Command+K` | Search every parameter and command. |
| `Command+Z` and `Command+Shift+Z` | Undo and redo. |
| `Command+S` | Save the sound. |

The layer header, clip, envelope handles, rack tabs, controls, focus rows, analysis tabs, and transport follow one DOM focus order. The hidden selection grid in `apps/studio/src/components/editor/TokenEditor.tsx::TokenEditor` is removed. No interactive layer control may sit inside an `aria-hidden` ancestor.

## Empty and first run states

### No sound open

The warm library shows canonical sounds, user sounds, and recent work. The dark bench shows one centered action: `Create sound`. Secondary actions are `Copy an Audioface sound` and `Open recent` when recents exist. Analysis and the rack show short explanations of what will appear there.

### First sound

`Create sound` opens the source picker before it creates a patch. Choosing Tone, Noise, or FM Pair creates the first valid layer. Cancel returns to the no sound state. The product never stores a zero-layer patch.

The first clip starts at 0 ms and receives focus. Its source template sets an audible duration and envelope. The ruler fits 0 to 250 ms. Three one-time callouts identify the clip body, the envelope handles, and `Space` audition. The callouts disappear after the user performs each action and remain available under Help.

The first explicit audition satisfies browser activation and enables automatic audition. A failed audio context start produces an inline transport error with Retry. It never clears the authored sound.

### Empty library

An empty user library still shows the locked canonical catalog. Copying a canonical sound creates a user-owned sound through the existing store boundary described by `ARCHITECTURE.md::Token Library Ownership`. The canonical source remains locked.

## Authoring limits and current ceilings

Five of the 35 recorded ceilings are direct Studio authoring caps. Impact Bench must remove them.

| ID | Current UI ceiling | Current owner | Impact Bench range |
| --- | --- | --- | --- |
| H14 | Gain stores 0.001 to 0.22 linear even though themed resolution permits 0.7 | `apps/studio/src/app/useTokenEditor.ts::TOKEN_EDITOR_GAIN_CEILING` and `updateLayerGain`; exposed control E04 | `AMP-01` uses -60 to +6 dB. The resolved view shows H04 if the current theme resolver clamps the value. |
| H15 | Duration stores 4 to 240 ms even though themed resolution permits 350 ms | `apps/studio/src/app/useTokenEditor.ts::updateLayerDuration`; exposed control E05 | `TIM-03` uses 1 to 2000 ms and respects the explicit `TIM-01` patch budget. |
| H16 | Layer delay stores 0 to 160 ms | `apps/studio/src/app/useTokenEditor.ts::updateLayerDelay`; exposed control E06 | `TIM-02` uses 0 to 500 ms. |
| H17 | Noise filter input spans 40 to 12,000 Hz while themed resolution permits up to 16,000 Hz | `apps/studio/src/components/editor/TokenEditor.tsx::pitchMax` and `apps/studio/src/app/useTokenEditor.ts::tuneLayer`; exposed control E07 | `FLT-10` uses 20 to 20,000 Hz. |
| H18 | Tone and FM pitch input stops at 1,400 Hz while `tuneLayer` accepts 12,000 Hz | Same symbols as H17; exposed control E07 | `PCH-01` uses 20 to 12,000 Hz. |

H01 through H13 remain resolver constraints until the engine model changes. H19 and H20 belong to the later flow shell. H21 through H35 describe fixed engine capabilities or absent features. Impact Bench must show a resolved clamp, a safety warning, or an unavailable capability explicitly. It must never copy those constraints into an unrelated authoring slider without a named product decision.

### Decay is currently dead

`layer.decay` is latent parameter L05. `packages/core/src/tokens.ts::resolveLayer` scales it with warmth and stores the result under ceiling H06. Neither engine reads the value. `packages/engine/src/index.ts::createLayerOutput` schedules one attack and one exponential fall to the layer end.

Stage 2 must make `AMP-06 Decay time` audible before Impact Bench exposes a decay handle. The implementation must either give decay a real segment in the amplitude envelope or remove the field and replace it with the new envelope model. A decorative handle backed by dead data is unacceptable. `ANL-09 Decay time measurement` provides the Stage 2 verification target named in the control report.

## Semantic shell without a rewrite

The foundation needs four stable concepts from its first implementation.

1. A sound definition owns a stable sound ID and an ordered layer list.
2. Each layer owns a stable layer ID and a discriminated source variant.
3. Each parameter has a stable control ID and scope.
4. Playback resolution derives a resolved sound from the authored sound plus trigger context and an optional semantic context.

Impact Bench edits the authored sound. `apps/studio/src/app/useStudioPlayback.ts::useStudioPlayback` sends one resolved object to `packages/engine/src/index.ts::AudiofaceEngine`. Analysis and later recording consume that same resolved object. Persistence remains in `packages/stores`, as assigned by `ARCHITECTURE.md::Ownership`.

The later shell adds these regions around the existing bench.

- Theme Lens adds Material plus the seven scalar macros, resolved ghost curves, and manual override state. It replaces the current Raw and Themed buttons from exposed control E18 with one authored or resolved view toggle.
- Token identity adds the semantic ID, action, category, and set context to the library detail view.
- Flow context docks below analysis. Selecting a flow step changes the open sound while the flow transport remains available.
- Feel First becomes an alternate macro view over the same parameter addresses and macro bindings.
- Patch Canvas becomes an alternate routing view after Stage 6 introduces `MOD-07 Destination routing` and the full modulation matrix.

`apps/studio/src/components/sequence/SequenceAudition.tsx::SequenceAudition` therefore becomes a later context surface. It cannot remain the root owner. `apps/studio/src/components/theme/ThemeComposer.tsx::ThemeComposer` becomes a shell control. `apps/studio/src/components/sequence/SequenceGraph.tsx::SequenceGraph` does not become Patch Canvas because it projects a flow graph rather than a synthesis graph.

No shell creates another sound store, playback path, parameter type, or analysis model.

## Acceptance proof

The first complete Impact Bench release needs the following evidence.

1. A designer creates a four-layer sound containing Tone, Noise, and FM Pair, then adds, duplicates, reorders, retypes, mutes, solos, and deletes layers with pointer and keyboard input.
2. Reorder preserves focus, values, undo history, and stable parameter addresses.
3. Every Stage 1 and Stage 2 control ID in this document is reachable through the command palette. Controls without an engine implementation remain absent and are reported as build gaps.
4. The five UI ceilings H14 through H18 no longer constrain authored values. The authored and resolved views show any resolver clamp.
5. `AMP-06` changes rendered audio. `ANL-09` confirms that measured decay matches the authored value within the implementation tolerance.
6. Release and Live automatic audition follow their trigger policy. Live mode never exceeds one trigger per 110 ms.
7. Waveform, envelope, and the chosen analysis tab stay visible while the rack changes groups.
8. Focus rows edit the same state as normal rack fields and direct clip manipulation.
9. A manual parameter edit detaches its macro binding. Repeated macro changes leave the manual value unchanged. Undo restores the value and binding together.
10. A keyboard-only run can create a sound, add and reorder a layer, edit onset and duration, audition the full sound and one layer, search for a parameter, save, and undo.
11. A theme and a flow attach through the shell while the underlying sound definition, layer IDs, parameter IDs, playback owner, and analysis owner remain unchanged.

## Exclusions from the base workbench

The base Impact Bench does not include sample import, piano rolls, free routing, arbitrary music tracks, or Score Mode. The target remains procedural audio with generated buffers and zero audio assets. Free routing arrives with the modulation matrix. Score Mode remains a later interface soundtrack capability under `ARCHITECTURE.md::Score Mode Target`.
