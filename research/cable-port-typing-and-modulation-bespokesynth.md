---
title: BespokeSynth cable typing and modulation write path
type: research
tags: [bespokesynth, cables, modulation, audio-graph, review]
summary: ConnectionType enforcement, cable colors, allowed source/target pairs, and IModulator vs ModulationChain write rates in BespokeSynth.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# BespokeSynth cable typing and modulation

Commit `3c4259cc4b38878d210fe6d2b8b5ab69c2f06373`. Tree: `/Users/alphab/.cache/bespoke-review/BespokeSynth`.

fmm has no C++ index (languages: TS/JS/Python/Rust). fmm MCP bound to `audioface-next/.fmm.db`. Facts below are from source reads of `Source/`.

There is no `CanConnect` symbol. Enforcement is `PatchCableSource::FindValidTargets` plus `PatchCableSource::IsValidTarget` (membership in `mValidTargets`) plus `IUIControl::CanBeTargetedBy`. There is no `AddModulation` symbol. Voice-mod mix uses `ModulationChain::AppendTo` / `SetSidechain` / `MultiplyIn`. Sample offset is `Value(samplesIn)` / `GetValue(samplesIn)`, not `GetValue(offset)`.

`FloatSlider` lives in `Source/Slider.h`, not `FloatSlider.h`.

## Executive Summary

BespokeSynth types patch cables with `ConnectionType` on `PatchCableSource`. Drop targets are enumerated at grab time. Audio, note, and pulse go to modules that implement `IAudioReceiver` / `INoteReceiver` / `IPulseReceiver`. Modulator, ValueSetter, UIControl, Pulse, and Grid can also land on `IUIControl` / `UIGrid`. Parameter modulation is pull: owners call `FloatSlider::Compute` which reads `IModulator::Value(samplesIn)`. Voice expression (pitch bend, mod wheel, pressure) is a separate `ModulationChain` carried on `NoteMessage`.

## Project Metadata

| Field | Value |
|---|---|
| Language | C++ |
| UI / audio | JUCE + custom OpenFrameworks-style draw, `gBufferSize` blocks |
| Build | CMake |
| Key types | `ConnectionType`, `PatchCable`, `PatchCableSource`, `IModulator`, `ModulationChain`, `FloatSlider` |

## Architecture

A module owns one or more `PatchCableSource` ports. Each source owns a vector of `PatchCable`. `IDrawableModule::CreateUIControls` auto-creates one output cable unless `ShouldSuppressAutomaticOutputCable()`:

| Module interface | Auto `ConnectionType` |
|---|---|
| `IAudioSource` | `kConnectionType_Audio` |
| else `INoteSource` | `kConnectionType_Note` |
| else `IGridController` | `kConnectionType_Grid` |
| else `IPulseSource` | `kConnectionType_Pulse` |
| else | `kConnectionType_Special` (no auto cable) |

Receive capability is stamped in `IDrawableModule::Init` from `ModuleFactory::ModuleInfo` (`mCanReceiveAudio` / `mCanReceiveNotes` / `mCanReceivePulses`) and asserted against `dynamic_cast` of those interfaces.

Two modulation systems:

1. **Parameter cables.** `IModulator` + `kConnectionType_Modulator` onto `IUIControl`, typically `FloatSlider`.
2. **Voice expression.** `ModulationParameters` on `NoteMessage` (`pitchBend`, `modWheel`, `pressure`, `pan`) implemented by `ModulationChain`. Visualized by `ModulationVisualizer`, not by slider overlay.

## Connection types and colors

`ConnectionType` in `Source/PatchCable.h`. Color assigned in `PatchCableSource::SetConnectionType`. Category hues in `IDrawableModule::GetColor` then `mColor.setBrightness(brightness * .8f)`.

ofColor HSB units are 0..255. Statics: `sHueNote=27`, `sHueAudio=135`, `sHueInstrument=79`, `sHueNoteSource=240`, `sSaturation=145`, `sBrightness=220`.

| `ConnectionType` | Color source | HSB after category lookup | Extra |
|---|---|---|---|
| `kConnectionType_Note` | `GetColor(kModuleCategory_Note)` | H 27, S 145, B 220 then B*=0.8 | Title-bar receive pip uses the same note hue |
| `kConnectionType_Audio` | `GetColor(kModuleCategory_Audio)` | H 135, S 145, B 220 then B*=0.8 | Cable draws `RollingBuffer` waveform; stereo channel 1 swaps R/G |
| `kConnectionType_Pulse` | `GetColor(kModuleCategory_Pulse)` | H 43, S 145, B 220 then B*=0.8 | `kPulseFlag_Reset` draws a black circle on the history stroke |
| `kConnectionType_Modulator` | `GetColor(kModuleCategory_Modulator)` | H 200, S 100, B 255 then B*=0.8 | Overlay stroke: blue/red from `IModulator::GetRecentChange()` |
| `kConnectionType_ValueSetter` | modulator color, desaturated | sat*=0.6, brightness*=0.7, then B*=0.8 | Comment: one-shot, not continuous |
| `kConnectionType_UIControl` | `GetColor(kModuleCategory_Other)` | H 0, S 0, B 220 then B*=0.8 | Gray. MidiController, Snapshots, EventCanvas |
| `kConnectionType_Grid` | Other + grid icon | same gray | `GridControlTarget::DrawGridIcon` at the jack |
| `kConnectionType_Special` | Other | same gray | Any module; optional `AddTypeFilter` / `SetPredicateFilter` |

`PatchCableSource::GetColor` overrides to pulsing yellow when `mIsPartOfCircularDependency`.

`PatchCableDrawMode` in `Source/PatchCableSource.h` is visibility, not type:

| Mode | Effect (`PatchCableSource::Render`) |
|---|---|
| `kPatchCableDrawMode_Normal` | Always draw source jack and cables |
| `kPatchCableDrawMode_CablesOnHoverOnly` | Cables only when `mHoverIndex != -1` |
| `kPatchCableDrawMode_SourceOnHoverOnly` | Jack only when hovered. Used by `MidiController` |

`CableDropBehavior` (`ShowQuickspawn`, `DoNothing`, `DisconnectCable`) applies when a drag ends with no valid target. Quickspawn only for Note, Audio, Pulse.

## Allowed source to target pairs

`PatchCableSource::FindValidTargets` builds `mValidTargets` on grab (`CableGrabbed`) and on mouse release while dragging. `PatchCable::IsValidTarget` delegates to the owner source. `PatchCable::GetDropTarget` first hits a module, then if type is Pulse / Modulator / ValueSetter / Grid / UIControl, walks that module's `GetUIControls()` and `GetUIGrids()` for a rect hit that is valid.

| Source type | Module targets | Control / grid targets |
|---|---|---|
| Audio | `IDrawableModule::CanReceiveAudio()` (`IAudioReceiver`) | none |
| Note | `CanReceiveNotes()` (`INoteReceiver`) | none |
| Pulse | `CanReceivePulses()` (`IPulseReceiver`) | UI controls with `CanBeTargetedBy` plus pulse (see below) |
| Modulator | none (except via UI walk) | `IUIControl` if `CanBeTargetedBy` |
| ValueSetter | none via module flag | same UI walk as Modulator |
| UIControl | none via module flag | same UI walk |
| Grid | none via module flag | `UIGrid` / `GridControlTarget` if `CanBeTargetedBy` |
| Special | every module except self and parent, after type filter | none |

Always skipped: the owning module, `TheTitleBar` for UI walks, parent module for module targets, hidden controls, controls with `GetShouldSaveState()==false` unless `ClickButton`.

### `IUIControl::CanBeTargetedBy`

Default (`Source/IUIControl.cpp`): `mCableTargetable && !GetNoHover()` and type is Modulator **or** ValueSetter **or** UIControl.

| Control | Override | Extra types |
|---|---|---|
| `FloatSlider` / `IntSlider` / `TextEntry` | inherit default | Modulator, ValueSetter, UIControl |
| `Checkbox` | `Checkbox::CanBeTargetedBy` | Pulse plus default |
| `ClickButton` | `ClickButton::CanBeTargetedBy` | Pulse plus default |
| `RadioButton` | `RadioButton::CanBeTargetedBy` | Pulse plus default |
| `DropdownList` | `DropdownList::CanBeTargetedBy` | Pulse plus default |
| `GridControlTarget` | `GridControlTarget::CanBeTargetedBy` | Grid only |
| `UIGrid` | `UIGrid::CanBeTargetedBy` | UIControl if `mCanBeUIControlTarget` or owner is `Snapshots` |
| `Canvas` | `Canvas::CanBeTargetedBy` | UIControl **and** owner is `Snapshots` |
| `DotGrid` | `DotGrid::CanBeTargetedBy` | same Snapshots-only UIControl |
| `ADSRDisplay` | always false | never a cable target |

Pulse on those discrete controls: they implement `IPulseReceiver::OnPulse`. `PatchCableSource::SetPatchCableTarget` `dynamic_cast`s the target into `mPulseReceivers`. `IPulseSource::DispatchPulse` fans out to that vector.

| Control | `OnPulse` |
|---|---|
| `Checkbox` | toggle `SetValue` |
| `ClickButton` | `DoClick` if velocity > 0 |
| `RadioButton` | step / reset / random using `PulseFlags` |
| `DropdownList` | same step / reset / random |

`FloatSlider` is not an `IPulseReceiver`. Pulse cannot land on a slider.

### Drag a cable onto a slider (IUIControl as patch target)

1. `PatchCable::Grab` sets `sActivePatchCable`, calls `PatchCableSource::CableGrabbed` -> `FindValidTargets`.
2. `IUIControl::DrawPatchCableHover` draws a magenta rect if the active cable type is Pulse / Modulator / ValueSetter / UIControl / Grid and `IsValidTarget(this)`.
3. On release, `PatchCable::GetDropTarget` resolves the control under the plug.
4. `PatchCableSource::SetPatchCableTarget` runs `IPatchable::PreRepatch`, stores the `IClickable` target, casts into note/pulse/audio receiver lists, then `PostRepatch`.
5. Modulator modules call `IModulator::OnModulatorRepatch` from `PostRepatch`. That maps each cable to `mTargets[i]`, `dynamic_cast<FloatSlider*>`, and `FloatSlider::SetModulator(this)`. First slider also `InitializeRange`.
6. Shift during drop (`GetKeyModifiers() == kModifier_Shift`) inserts: the new module's output is patched to the old target if valid (`sAllowInsert`).

`IModulator::OnRemovedFrom` is the reverse: `FloatSlider::SetModulator` of a different modulator calls the old modulator's `OnRemovedFrom`, which deletes that cable.

## Multiple cables, fan-in, fan-out, sidechain

Constructor (`PatchCableSource::PatchCableSource`): `mAllowMultipleTargets` is true for Note, Pulse, Audio, Modulator, ValueSetter. False for UIControl, Grid, Special.

`InAddCableMode`: Shift **and** `mAllowMultipleTargets`, or `kDefaultPatchBehavior_Add`. Default behavior is `kDefaultPatchBehavior_Repatch` (clicking the jack grabs the existing cable).

`AddPatchCable` refuses a second cable to the same target pointer.

| Type | Fan-out from one source | How |
|---|---|---|
| Note | yes | `mNoteReceivers` vector. `NoteOutput::PlayNoteInternal` calls `PlayNote` on every receiver |
| Pulse | yes | `mPulseReceivers` vector. `IPulseSource::DispatchPulse` |
| Modulator | yes, cap 10 | `IModulator::mTargets` `std::array<Target,10>`. Same `Value()` written to each |
| ValueSetter | yes | `ValueSetter::mTargets` filled from cables; `Go` `SetValue` on each |
| Audio | flag true, jack add is special | Shift-add on an occupied **audio** jack spawns `AudioSend` instead of a second cable (`PatchCableSource::TestClick`). `mAudioReceiver` is a **single** pointer, last connected wins |
| UIControl / Grid / Special | flag false | one target unless the module calls `SetAllowMultipleTargets(true)` (`SongBuilder` does; `ControlInterface` forces false) |

Audio fan-out that is actually multiple destinations uses **multiple `PatchCableSource`s**: `AudioSplitter` (grows a new jack when the last is connected), `AudioSend` (`GetTarget(0)` dry, `GetTarget(1)` send), `IAudioSource::GetTarget(index)` via `GetPatchCableSource(index)`.

| Type | Fan-in | How |
|---|---|---|
| Audio | yes, summing | Sources `Add()` into `IAudioReceiver::GetBuffer()`. Consumer `ChannelBuffer::Reset()` after `Process`. `IAudioReceiver::SyncInputBuffer` folds extra channels to mono when `kInputMode_Mono`. Graph order: `ModularSynth::ArrangeAudioSourceDependencies` |
| Note | yes | Independent `PlayNote` calls into the same `INoteReceiver` |
| Pulse | yes | Independent `OnPulse` |
| Parameter modulator | **no** | `FloatSlider::mModulator` is one pointer. A new `SetModulator` disconnects the previous |

**Sidechain** is not a cable type.

- Voice: `ModulationChain::SetSidechain` adds another chain's `GetIndividualValue`. `Modulations` with `isGlobalEffect==true` sidechains each voice chain to the global pitch/mod/pressure chain.
- Audio analog: `AudioSend` (`Source/AudioSend.cpp`) copies input to target 0 and scaled copy to target 1 (`mAmount`, optional `mCrossfade`).
- `ModulationChain::MultiplyIn` is a product mix. `AppendTo` sets `mPrev` so `GetValue` walks the previous chain (used by `PitchBender`, `NoteVibrato`).

## Modulation write path and rate

### Parameter modulators (`IModulator`)

`IModulator::Value(int samplesIn=0)` is pure pull. Nothing in the modulator pushes into the slider except:

| Path | Rate | Who writes |
|---|---|---|
| `IDrawableModule::ComputeSliders(samplesIn)` -> `FloatSlider::Compute` -> `DoCompute` | Per sample when the owner loops `i in 0..gBufferSize-1`; per block when called with 0 | `*mVar = mModulator->Value(samplesIn)` if `Active()` |
| `FloatSlider::Poll` (from `IDrawableModule::BasePoll` each UI frame) | UI frame, and only if last compute is older than 100 ms | same `Compute()` |
| `IModulator::Poll` via `ModularSynth::AddExtraPoller` | UI frame (`ModularSynth` poll before module `Poll`) | `Value()` (LFO/envelope `Value` itself calls `ComputeSliders(0)`). Non-`FloatSlider` targets: `SetValue` or `SetFromMidiCC` |
| `ValueSetter::Go` | Event (pulse or button) | `IUIControl::SetValue(mValue, time, forceUpdate)` |
| Right-click slider LFO | same as IModulator | `FloatSlider::DisplayLFOControl` -> `LFOPool::GetLFO` (pool size 256) -> `SetLFO` -> `SetModulator` |

`DoCompute` skips work when `(mLastComputeTime, mLastComputeSamplesIn)` already match, to break circular modulation. Audio-thread per-sample cache: `mLastComputeCacheTime[samplesIn]`. `mLFOControl->InLowResMode()` (`lite cpu`) computes only `samplesIn==0`.

`IModulator::Target::RequiresManualPolling`: `mUIControlTarget != nullptr && mSliderTarget == nullptr` (anything that is not a `FloatSlider`).

| Target class | Write method | Mapping |
|---|---|---|
| `FloatSlider` | `DoCompute` literal `Value()` | already in slider units |
| `IntSlider` / `TextEntry` (`ModulatorUsesLiteralValue()==true`) | `SetValue(mLastPollValue, ...)` | literal |
| other `IUIControl` (checkbox, radio, dropdown; default `ModulatorUsesLiteralValue()==false`) | `SetFromMidiCC(mLastPollValue, ..., SetValueMethod::Modulator)` | 0..1 |

`FloatSlider::SetValue` from the mouse **disables** a pooled LFO (`DisableLFO`). Dragging a modulated slider with `CanAdjustRange()` writes `mModulator->GetMax()`; vertical drag writes `GetMin()`.

### Concrete `Value()` implementations

| Module | `Value(samplesIn)` | Trigger |
|---|---|---|
| `FloatSliderLFOControl` | `ComputeSliders`; `GetLFOValue` = `LFO::Value` then `Spread` then `Interp(GetMin(), GetMax())` clamp to target min/max | Pulse: `LFO::ResetPhase`. Pin button creates `kConnectionType_Modulator` cable |
| `EnvelopeModulator` | `ADSR::Value(gTime + samplesIn * gInvSampleRateMs)` then `Interp(GetMin(), GetMax())` clamp | `PlayNote` starts/stops ADSR; `OnPulse` starts. Auto note cable suppressed (`ShouldSuppressAutomaticOutputCable`) |
| `ModulatorAdd` | `mValue1 + mValue2` clamp to first slider | none |
| `MacroSlider::Mapping` | `ofMap(owner 0..1, GetMin(), GetMax(), clamp)` | none |

`LFO::Value`: default `kLFOMode_Envelope` rescales oscillator to 0..1. `kLFOMode_Oscillator` is bipolar -1..1 (`ModulationChain` sets this). `kInterval_None` returns 1 (envelope) or 0 (oscillator). Phase from transport measure time, or `mFreeRate` when `kInterval_Free`. Drunk/Perlin/free-rate advance in `LFO::OnTransportAdvanced` (audio poller). Random (S&H) on `ITimeListener::OnTimeEvent`.

`LFOController` is a bind helper: `WantsBinding` intercepts `FloatSlider::SetValue` and `AcquireLFO`s that slider.

### Voice `ModulationChain`

`ModulationChain::GetValue(samplesIn)`:

```
individual = ramp(time) + LFO.Value(samplesIn)*mLFOAmount + mBuffer[samplesIn]
then * MultiplyIn, + Sidechain, + Prev
```

`SetValue` ramps over one buffer (`gInvSampleRateMs * gBufferSize`). `RampValue` is timed. `FillBuffer` is per-block audio-rate additive. `GetBufferValue(sampleIdx)` reads that buffer.

`NoteVibrato` / `PitchBender`: on `PlayNote`, `GetPitchBend(voiceIdx)->AppendTo(note.modulation.pitchBend)` then replace the pointer. `PitchBender::FloatSliderUpdated` writes global chain `GetPitchBend(-1)->SetValue`. `NoteVibrato` writes `SetLFO(interval, amount)` on the global chain. Both `ComputeSliders(0)` on `OnTransportAdvanced` (once per audio block).

`Modulations(isGlobalEffect)`: if true, each of `kNumVoices` voice chains `SetSidechain` to the global collection.

## Range and curve handling

`IModulator::GetMin()` / `GetMax()` alias `FloatSlider::GetModulatorMin()` / `GetModulatorMax()` of **target 0**, else `mDummyMin` / `mDummyMax`. Independent of slider `mMin`/`mMax`.

`InitializeRange` (first connect, not during load): copies control `GetModulationRangeMin/Max` unless `InitializeWithZeroRange()` (`FloatSliderLFOControl` returns true: min=max=current value, zero depth until the user spreads). Copies slider `Mode` onto the min/max sliders.

| Mapping | Where |
|---|---|
| Linear interp min..max | `FloatSliderLFOControl::GetLFOValue`, `EnvelopeModulator::Value` |
| `Spread(x, spread)` power curve about 0.5 | `FloatSliderLFOControl` (legacy `-cos` path if `mUseOldSpreadStyle`) |
| Bias / pulse width | `LFO::SetPulseWidth(1 - mBias)` |
| Length (duty of one cycle) | `LFO::TransformPhase` |
| Shuffle / soften | `Oscillator::SetShuffle` / `SetSoften` |
| ADSR stage curve | `ADSR::Stage.curve` |
| Slider display / MIDI position | `FloatSlider::Mode`: `kNormal`, `kLogarithmic`, `kSquare`, `kBezier`. Affects `ValToPos`/`PosToVal` and `SetFromMidiCC`, **not** `IModulator::Value` which writes literal `*mVar` |
| Smoothing | `FloatSlider` `mSmooth`; `OnTransportAdvanced` ramps `mSmoothTarget`. Audio poller |

Bipolar parameter modulation is just min < 0 < max on the modulator range sliders. LFO used as a cable is unipolar 0..1 (`kLFOMode_Envelope`). LFO inside `ModulationChain` is bipolar (`kLFOMode_Oscillator`).

`GetSliderTarget()` is only `mTargets[0]`. Extra float-slider cables receive that same number; clamp uses slider 0's extents in LFO/envelope `Value()`.

## Modulation visible in the UI

| Surface | What |
|---|---|
| `FloatSlider::Render` | If modulator active: green filled bar from modulator min to current `*mVar`, green min/max ticks. Else red value tick |
| `PatchCable::Render` | If `GetModulatorOwner()`: extra stroke lerp blue..red by `GetRecentChange()/range`. Plug color shifts with delta. `GetRecentChange` is last poll minus framerate-smoothed value |
| Note/pulse/UI history | `NoteHistory` (100 events, `NOTE_HISTORY_LENGTH` 250 ms) thickens the stroke while "on" |
| Audio cable | `IAudioSource::GetVizBuffer()` (`VIZ_BUFFER_SECONDS` 0.1). Yellow `!` if mono/multichannel mismatch |
| Title-bar pips | `IDrawableModule::DrawFrame`: audio / note / pulse colored rects if `CanReceive*` |
| `IUIControl::DrawPatchCableHover` | Magenta outline while dragging a compatible cable |
| `ModulationVisualizer` | Note-effect module. Draws per-voice `pitchBend`/`modWheel`/`pressure` via `ModulationChain::GetValue(0)` plus `pan`. **Does not** visualize `IModulator` slider cables |
| `IControlVisualizer` | Ableton Move LCD (`DrawVisualizationToScreen`). Not cable glow |
| `MacroSlider::Mapping::Draw` | Green line at mapped output on the min/max pair |
| `LFOController` | Bind UI for interval/osc/min/max of the acquired LFO |

`PatchCableDrawMode` does not encode type. Fat cables (thicker, full alpha) when the last-clicked module is either end, or when "accentuate active" mode sees recent history / nonzero viz audio.

## Symbol index (no `CanConnect`, no `AddModulation`)

| Asked symbol | Actual |
|---|---|
| `CanConnect` | absent. Use `PatchCableSource::IsValidTarget`, `FindValidTargets`, `IUIControl::CanBeTargetedBy` |
| `AddModulation` | absent. Voice mix: `ModulationChain::AppendTo`, `SetSidechain`, `MultiplyIn`, `FillBuffer` |
| `GetValue(offset)` | `IModulator::Value(int samplesIn=0)`, `ModulationChain::GetValue(int samplesIn)`, `LFO::Value(int samplesIn, float forcePhase=-1)` |
| `FloatSlider::GetModulator` | `Slider.h` `FloatSlider::GetModulator` returns `mModulator` |
| `ConnectionType` / `kConnectionType_*` | `PatchCable.h` |
| `PatchCableDrawMode` | `PatchCableSource.h` |

## Relevance to Helioy

Typed cables with a grab-time valid-target list (not a static adjacency matrix) is the Bespoke pattern worth copying: one enum on the source, `CanBeTargetedBy` on the sink, UI-control drop via rect hit. Parameter modulation is pull (`Compute(samplesIn)`), so audio-rate and UI-rate share one `Value(samplesIn)` and circular graphs are broken by a per-sample cache. Keep voice expression (`ModulationChain` on the note) separate from slider CV. Slider overlay (min/max ticks + current) plus cable color from recent delta is the cheapest modulation HUD.

## Open Questions

- Whether any audio module other than `AudioSplitter` / `AudioSend` / multi-`PatchCableSource` owners actually stores multiple `kConnectionType_Audio` cables on one source (the jack UI refuses to add them).
- Whether `EnvelopeModulator::PlayNoteOutput` is dead in practice (automatic note cable suppressed; modulator jack does not accept `INoteReceiver`s).
- Per-target range for modulator fan-out beyond index 0 (currently all cables share `Value()` computed against slider 0).
