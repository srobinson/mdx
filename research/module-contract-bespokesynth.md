---
title: BespokeSynth module contract (inheritance, ports, factory)
type: research
tags: [bespokesynth, module-contract, dsp, factory, inheritance, ui-controls]
summary: BespokeSynth modules are IDrawableModule plus C++ capability mixins; cables and factory flags replace typed ports; no latency/tail/parameter-descriptor ABI.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# BespokeSynth module contract

Commit `3c4259cc4b38878d210fe6d2b8b5ab69c2f06373`. C++17, JUCE, CMake. Source tree under `Source/` (~398 headers, ~380 cpp). No `.fmm.db`; fmm MCP was bound to another repo, so this is from headers/cpp reads.

Verdict: **ad-hoc C++ multiple inheritance**, not a typed DSP plugin contract. A "module" is a drawable UI node that optionally implements audio/note/pulse/modulator interfaces. Ports are patch cables plus RTTI. Parameters are widgets pointing at member variables.

## Executive summary

BespokeSynth's unit of graph identity is `IDrawableModule`. Signal roles are extra bases (`IAudioSource`, `IAudioReceiver`, `INoteSource`, `INoteReceiver`, `IPulseSource`, `IPulseReceiver`, `IModulator`) mixed in per class. `ModuleFactory` registers a function pointer plus three static `Accepts*` flags and a `ModuleCategory`. There is no port descriptor, no parameter descriptor, no latency/tail report, and no `process(in, out)` block API. In-place FX live in a second factory (`EffectFactory` / `IAudioEffect`) hosted by `EffectChain`.

## Project metadata

| Item | Value |
|---|---|
| Language | C++17 (`CMAKE_CXX_STANDARD 17`) |
| Version | `project(BespokeSynth VERSION 1.3.0 ...)` in `CMakeLists.txt` |
| UI/audio host | vendored JUCE |
| Module count | 223 `REGISTER` + 30 `REGISTER_HIDDEN` in `Source/ModuleFactory.cpp` |
| Effect count | 18 live `EffectFactory::Register` entries in `Source/EffectFactory.cpp` |
| Channel cap | `ChannelBuffer::kMaxNumChannels = 2` |

## Inheritance diagram

```
IClickable                          IPollable
    |                                   |
    +---------------+-------------------+
                    |
              IDrawableModule  ----virtual---- IPatchable
                    |                               ^
     +--------------+---------------+               |
     |              |               |               |
IAudioEffect   (most modules)   IAudioSource -------+
     |                              |
     |                         IAudioProcessor : IAudioReceiver + IAudioSource
     |                              |
     |                         Amplifier, EffectChain, OutputChannel, AudioSplitter, ...
     |
     +-- GainStageEffect, DelayEffect, ... (hosted inside EffectChain, IsSaveable=false)

INoteSource ----virtual---- IPatchable
     |
     +-- NoteOutput (helper INoteReceiver that fans out)
     +-- AdditionalNoteCable
     +-- NoteEffectBase : INoteReceiver + INoteSource   (default passthrough)
            |
            +-- NoteRouter, EnvelopeModulator, Capo, ...

IPulseSource                        IPulseReceiver
     |                                    |
     +-- Pulser, PulseRouter              +-- PulseRouter, NoteCreator, FloatSliderLFOControl, Checkbox, DropdownList

IModulator : IPollable
     |
     +-- FloatSliderLFOControl, EnvelopeModulator, ModulatorAdd, ...

IAudioPoller                        ITimeListener
     |                                    |
     +-- LFO (helper), Pulser, FloatSlider  +-- Pulser, LFO, sequencers
```

`IPatchable` is **virtual** on both `IDrawableModule` and `IAudioSource`/`INoteSource` so a module that is both drawable and a source has one `IPatchable` subobject.

`IAudioEffect` is **not** `IAudioProcessor`. It is an `IDrawableModule` that processes a `ChannelBuffer*` in place via `ProcessAudio`. It is spawned into an `EffectChain`, not as a first-class graph node (`CanMinimize=false`, `IsSaveable=false`).

There are no C++ mixins in the CRTP sense. Composition is **public multiple inheritance** plus listener interfaces (`IFloatSliderListener`, `IDropdownListener`, ...).

## How a module is defined

Required static factory API (defaults on `IDrawableModule`):

- `static IDrawableModule* Create()`
- `static bool CanCreate()` (default `true`; singleton-style overrides: `LFOController`, `ChaosEngine`, `ModuleSaveDataPanel`)
- `static bool AcceptsAudio()` / `AcceptsNotes()` / `AcceptsPulses()` (default `false`)

Required instance API:

- `DrawModule()` pure virtual
- `CreateUIControls()` (must call `IDrawableModule::CreateUIControls()` then construct widgets)
- `Init()` after UI creation; asserts factory `Accepts*` matches `dynamic_cast` to `IAudioReceiver` / `INoteReceiver` / `IPulseReceiver`

Lifecycle used by `ModularSynth::CreateModule` / `SetUpModule` / `SpawnModuleOnTheFly`:

1. `ModuleFactory::MakeModule(type)` -> `Create()`
2. `CreateUIControls()`
3. `LoadBasics(json, type)` (position, name, minimized)
4. container `AddModule` (if `IAudioSource`, push onto `ModularSynth::mSources`)
5. `LoadLayoutBase` -> `LoadLayout` + optional `transport_priority`
6. `Init()`
7. later `SetUpFromSaveDataBase` / `LoadState`

`IsSingleton()` modules (`Transport`, `Scale`, `TitleBar`, `UserPrefsEditor`, `QuickSpawnMenu`, `ModuleSaveDataPanel`) skip `CreateUIControls` in `CreateModule` and cannot be deleted.

## Interface table

### Graph / UI core

| Interface | File | Required | Role |
|---|---|---|---|
| `IClickable` | `Source/IClickable.h` | `Render`, hit-test, `GetDimensions`; identity via `Name()` / `Path()` | Spatial widget |
| `IPollable` | `Source/IPollable.h` | `Poll()` default empty | UI/main-thread tick (`IDrawableModule::BasePoll`) |
| `IPatchable` | `Source/IPatchable.h` | `GetPatchCableSource(index)` | Owns cables; `PreRepatch` / `PostRepatch` / `OnCableGrabbed` |
| `IDrawableModule` | `Source/IDrawableModule.h` | `DrawModule()`; optional `LoadLayout`/`SaveLayout`/`SetUpFromSaveData`/`SaveState`/`LoadState` | Module node: UI, children, controls, save, enable |

`ModuleCategory` enum on `IDrawableModule`: `Note`, `Synth`, `Audio`, `Instrument`, `Processor`, `Modulator`, `Pulse`, `Other`, `Unknown`. Used for color and spawn menus, **not** for port typing. `IAudioEffect` instances that are not in the factory map become `kModuleCategory_Processor` in `Init()`.

### Audio

| Interface | File | Required | Role |
|---|---|---|---|
| `IAudioSource` | `Source/IAudioSource.h` | `Process(double time)` | Push into `GetTarget()->GetBuffer()`; viz via `RollingBuffer` |
| `IAudioReceiver` | `Source/IAudioReceiver.h` | `GetBuffer()`, `GetInputMode()` (mono or multichannel) | Owns `ChannelBuffer mInputBuffer` |
| `IAudioProcessor` | `Source/IAudioProcessor.h` | none extra; `SyncBuffers()` | Receiver+source; typical FX/mixer node |
| `IAudioEffect` | `Source/IAudioEffect.h` | `ProcessAudio(time, ChannelBuffer*)`, `SetEnabled`, `GetType()` | In-place FX inside `EffectChain` |
| `IAudioPoller` | `Source/IAudioPoller.h` | `OnTransportAdvanced(float amount)` | Audio-thread transport tick (`Transport::AddAudioPoller`) |

`IAudioSource::GetTarget` reads `PatchCableSource::GetAudioReceiver()`. One audio receiver pointer per cable source. `GetNumTargets()` default 1; `AudioSplitter` overrides from `mDestinationCables`.

Audio render: `ModularSynth` audio callback advances transport, then `mSources[i]->Process(gTime)` in `ArrangeAudioSourceDependencies` order (producer before consumer). No per-module `processBlock`. Upstream `Add()`s into the receiver's `ChannelBuffer`; the processor `GetBuffer()->Reset()` after consume. Circular graphs are detected poorly (`kMaxLoopCount = 1000`) and still processed.

### Notes

| Symbol | File | Required | Role |
|---|---|---|---|
| `NoteMessage` | `Source/INoteReceiver.h` | fields: `time`, `pitch`, `velocity`, `voiceIdx`, `ModulationParameters modulation` | Event payload |
| `INoteReceiver` | same | `PlayNote(NoteMessage)`, `SendCC`; optional `SendPressure`, `SendMidi` | Input |
| `NoteInputBuffer` | same | `QueueNote` / `Process` | Cross-thread queue into receiver (`kBufferSize = 50`) |
| `INoteSource` | `Source/INoteSource.h` | `PlayNoteOutput`, `SendCCOutput` | Output via helper `NoteOutput` |
| `NoteOutput` | same | implements `INoteReceiver` | Fans out to `PatchCableSource::GetNoteReceivers()`, tracks 128 held notes, stack-depth guard |
| `NoteEffectBase` | `Source/NoteEffectBase.h` | default passthrough `PlayNote`/`SendCC` | Note processor mixin |
| `AdditionalNoteCable` | `Source/INoteSource.h` | extra `INoteSource` wrapping another cable | Multi-output notes |
| `NoteOutputQueue` | `Source/NoteOutputQueue.h` | | Main-thread notes marshalled onto audio thread |

`INoteSource::PreRepatch` flushes hanging notes.

### Pulse

| Symbol | File | Required | Role |
|---|---|---|---|
| `PulseFlags` | `Source/IPulseReceiver.h` | bitmask: `Reset`, `Random`, `SyncToTransport`, `Backward`, `Align`, `Repeat` | Event flags |
| `IPulseReceiver` | same | `OnPulse(time, velocity, flags)` | Input |
| `IPulseSource` | same | `DispatchPulse(PatchCableSource*, time, velocity, flags)` | Output; stack-overflow guard on last event time |

Widgets can be pulse targets: `Checkbox`, `DropdownList`, `ClickButton` implement `IPulseReceiver`.

### Modulator (CV onto UI)

| Symbol | File | Required | Role |
|---|---|---|---|
| `IModulator` | `Source/IModulator.h` | `Value(samplesIn)`, `Active()` | Writes `FloatSlider` via `SetModulator` or polls generic `IUIControl` |
| `IModulator::Target` | same | up to 10 targets | `FloatSlider*` and/or `IUIControl*` |
| `kConnectionType_Modulator` | `Source/PatchCable.h` | | Continuous cable onto a control |
| `kConnectionType_ValueSetter` | same | | One-shot set (`ValueSetter::mControlCable`) |

`FloatSlider::Compute(samplesIn)` is the sample-accurate path (`IDrawableModule::ComputeSliders` from inside `Process`). Non-slider targets are UI-thread polled (`TheSynth->AddExtraPoller`).

### Other capability interfaces

| Interface | File | Role |
|---|---|---|
| `ITimeListener` | `Source/Transport.h` | `OnTimeEvent(double time)` plus `mTransportPriority` |
| `IGridController` / `IGridControllerListener` | `Source/GridController.h` | Hardware grid pads |
| `IDrivableSequencer` | `Source/IDrivableSequencer.h` | External pulse source flag |
| `IInputRecordable` | `Source/IInputRecordable.h` | Record/clear/retroactive record |
| `IModuleDecorator` | `Source/IModuleDecorator.h` | Extra draw over a module |
| `IControlVisualizer` | `Source/IControlVisualizer.h` | Ableton Move LCD viz (`SingleOscillator`) |
| `INonstandardController` | `Source/INonstandardController.h` | Non-MIDI controller backends |
| `IMidiVoice` / `IVoiceParams` | `Source/IMidiVoice.h`, `Source/IVoiceParams.h` | Per-voice synth engine inside a module, not a graph port |
| `IKeyboardFocusListener` | `Source/IClickable.h` | Text entry focus |

### UI listener mixins (not DSP)

Modules accumulate these as extra bases:

- `IFloatSliderListener::FloatSliderUpdated`
- `IIntSliderListener::IntSliderUpdated`
- `IDropdownListener::DropdownUpdated`
- `IButtonListener::ButtonClicked`
- `ITextEntryListener::TextEntryComplete`
- `IRadioButtonListener` (`Source/RadioButton.h`)
- `IDrawableModule::CheckboxUpdated`

A typical synth class lists five to eight bases. Example: `FloatSliderLFOControl` is `IDrawableModule` + `IRadioButtonListener` + `IFloatSliderListener` + `IButtonListener` + `IDropdownListener` + `IModulator` + `IPulseReceiver` + `ITextEntryListener`.

## Cables are the port system

`ConnectionType` (`Source/PatchCable.h`): `Note`, `Audio`, `UIControl`, `Grid`, `Special`, `Pulse`, `Modulator`, `ValueSetter`.

`IDrawableModule::CreateUIControls` auto-creates **one** output `PatchCableSource` unless `ShouldSuppressAutomaticOutputCable()`:

- `IAudioSource` -> `kConnectionType_Audio`
- else `INoteSource` -> `Note`
- else `IGridController` -> `Grid`
- else `IPulseSource` -> `Pulse`

Extra cables are manual (`AddPatchCableSource`). Modulators typically suppress the auto note cable (`EnvelopeModulator::ShouldSuppressAutomaticOutputCable`) and add `kConnectionType_Modulator`.

Validity (`PatchCableSource::FindValidTargets`):

- Audio -> `module->CanReceiveAudio()`
- Note -> `CanReceiveNotes()`
- Pulse -> `CanReceivePulses()` **or** showing UI controls whose `CanBeTargetedBy` allows pulse
- Modulator / ValueSetter / UIControl / Grid -> UI controls and grids

`CanReceive*` is copied from factory `ModuleInfo` in `Init()`, then **asserted equal** to `dynamic_cast` of the instance. The flags exist so spawn UI can filter without constructing the class (`QuickSpawnMenu::MatchesFilter`).

`kMaxOutputsPerPatchCableSource = 32`. Audio cable source holds a **single** `IAudioReceiver*`. Notes/pulses hold vectors.

There are no named ports, no channel-count ports, no sidechain bus objects.

## Parameters and UI controls

`IUIControl` (`Source/IUIControl.h`) : `IClickable`. Contract: `SetFromMidiCC`, `SetValue`, `GetValue`, `SaveState`, `LoadState`, range, MIDI mapping, snapshot, randomize. Identity is the **string `Name()`**. Duplicate names that save state `assert(false)` in `AddUIControl`.

Widget classes:

| Class | File | Bound to | Notes |
|---|---|---|---|
| `FloatSlider` | `Source/Slider.h` | `float*` | LFO acquire, `IModulator`, modes `kNormal/kLogarithmic/kSquare/kBezier`, `IAudioPoller` when smoothing |
| `IntSlider` | same | `int*` | |
| `Checkbox` | `Source/Checkbox.h` | `bool*` | also `IPulseReceiver`; enable checkbox auto-created as `"enabled"` |
| `DropdownList` | `Source/DropdownList.h` | `int*` | also `IPulseReceiver` |
| `RadioButton` | `Source/RadioButton.h` | `int*` | |
| `ClickButton` | `Source/ClickButton.h` | event | |
| `TextEntry` | `Source/TextEntry.h` | string/int/float | `IKeyboardFocusListener` |
| `ADSRDisplay`, `UIGrid`, `GridControlTarget` | various | custom | |

Construction **self-registers**: `FloatSlider` ctor `dynamic_cast<IDrawableModule*>(owner)->AddUIControl(this)`. Owner must be both listener and `IDrawableModule`.

Layout helpers: `Source/UIControlMacros.h` (`UIBLOCK`, `FLOATSLIDER`, `INTSLIDER`, `CHECKBOX`, `DROPDOWN`, `BUTTON`, `TEXTENTRY`, `ENDUIBLOCK`). Used by `SingleOscillator::CreateUIControls`, `FloatSliderLFOControl::CreateUIControls`.

`IDrawableModule::ComputeSliders(samplesIn)` iterates `mFloatSliders` and calls `FloatSlider::Compute` for sample-accurate modulation inside audio `Process`.

This is **not** a parameter descriptor table. Range, default, and name live on the widget. Automation is MIDI CC onto `IUIControl`, or a modulator cable onto a slider.

### `ModuleSaveData`

`Source/ModuleSaveData.h`. Layout/config bag, not live DSP params.

`SaveVal`: property name + type `kInt/kFloat/kBool/kString` + min/max + optional enum map / dropdown filler.

API: `LoadInt/LoadFloat/LoadBool/LoadString/LoadEnum` from `ofxJSONElement`; `Get*` / `Set*` after load; `Save` writes back onto the JSON object.

Used from `LoadLayout` / `SetUpFromSaveData`. Example `Amplifier::LoadLayout`: `LoadString("target")`, `LoadBool("show_level_meter")`. `SetUpFromSaveData` does `SetTarget(TheSynth->FindModule(...))`.

`IDrawableModule::GetSaveData()` returns `mModuleSaveData`. Singleton `ModuleSaveDataPanel` (`TheSaveDataPanel`) edits those properties in a side panel. `IsSaveable()==false` on the panel itself.

`LoadLayoutBase` also injects `transport_priority` if the module is `ITimeListener`.

### Two-layer serialization

1. **JSON layout** (`LoadLayoutBase` / `SaveLayoutBase`): position, name, type, minimized, lissajous flag, `ModuleSaveData`, plus per-module `SaveLayout`. Patch targets often stored as string names (`"target"`).
2. **Binary state** (`SaveState` / `LoadState`, `FileStreamOut/In`): `GetModuleSaveStateRev()`, pin, size if resizable, each `IUIControl` name + raw float + `control->SaveState`, child modules or `ModuleContainer`, then each `PatchCableSource`. Separator bytes `"controlseparator"`. `LoadOldControl` / `UpdateOldControlName` for renames.

`CanModuleTypeSaveState`, `ControlsToIgnoreInSaveState`, `ControlsToNotSetDuringLoadState`, `ShouldSerializeForSnapshot` are the escape hatches. `IAudioEffect::IsSaveable()` is false; chain parent serializes them.

Python (`resource/python_stubs/module/__init__.pyi`) is a third ad-hoc surface: `module.create(moduleType, x, y)`, `set(path, value)`, `set_target`. Not the C++ ABI.

## Factory registration and spawn

`Source/ModuleFactory.h` / `Source/ModuleFactory.cpp`.

```
#define REGISTER(class, name, type) \
  Register(#name, &(class::Create), &(class::CanCreate), type, false, false, \
           class::AcceptsAudio(), class::AcceptsNotes(), class::AcceptsPulses());
#define REGISTER_HIDDEN(...)   // hidden=true
#define REGISTER_EXPERIMENTAL(...)  // experimental=true; unused in live list
```

`Register` fills `ModuleInfo` `{ mCreatorFn, mCanCreateFn, mCategory, mIsHidden, mIsExperimental, mCanReceiveAudio, mCanReceiveNotes, mCanReceivePulses }` keyed by the **stringified name** (spawn label), not the C++ class name.

`MakeModule(type)`: lookup, `CanCreate()`, `Create()`. Unknown type -> nullptr. `FixUpTypeName` remaps old labels (`"vstplugin"` -> `"plugin"`, `"presets"` -> `"snapshots"`, ...).

### Real `REGISTER` examples

| Macro | C++ class | Spawn label | Category | Accepts |
|---|---|---|---|---|
| `REGISTER(Amplifier, gain, kModuleCategory_Audio)` | `Amplifier` | `gain` | Audio | audio |
| `REGISTER(SingleOscillator, oscillator, kModuleCategory_Synth)` | `SingleOscillator` | `oscillator` | Synth | notes |
| `REGISTER(FloatSliderLFOControl, lfo, kModuleCategory_Modulator)` | `FloatSliderLFOControl` | `lfo` | Modulator | pulses |
| `REGISTER(NoteCreator, notecreator, kModuleCategory_Instrument)` | `NoteCreator` | `notecreator` | Instrument | pulses |
| `REGISTER(Pulser, pulser, kModuleCategory_Pulse)` | `Pulser` | `pulser` | Pulse | none (source only) |
| `REGISTER(EnvelopeModulator, envelope, kModuleCategory_Modulator)` | `EnvelopeModulator` | `envelope` | Modulator | notes+pulses |
| `REGISTER_HIDDEN(VSTPlugin, plugin, kModuleCategory_Synth)` | `VSTPlugin` | `plugin` | Synth | hidden; spawned via plugin list |
| `REGISTER_HIDDEN(LFOController, lfocontroller, kModuleCategory_Other)` | `LFOController` | `lfocontroller` | Other | `CanCreate` singleton |

Transport and Scale are **not** in the map; `CreateModule` special-cases `"transport"` / `"scale"` to `TheTransport` / `TheScale`.

### Spawn methods

`ModuleFactory::Spawnable` + `SpawnMethod`: `Module`, `EffectChain`, `Prefab`, `Plugin`, `MidiController`, `Preset`.

`ModularSynth::SpawnModuleOnTheFly` rewrites type:

- EffectChain -> spawn `"effectchain"` then `EffectChain::AddEffect(label)`
- Prefab -> `"prefab"` then load `.pfb`
- Plugin -> `"vstplugin"` (fixed up to `"plugin"`) then `VSTPlugin::SetVST(pluginDesc)`
- MidiController -> `"midicontroller"` + `devicein`
- Preset -> underlying module type + `ModuleSaveDataPanel::LoadPreset`

UI spawn surfaces:

- `TitleBar` / `SpawnListManager`: dropdowns per `ModuleCategory` (`mInstrumentModules`, `mNoteModules`, `mSynthModules`, `mAudioModules`, `mModulatorModules`, `mPulseModules`, `mOtherModules`, `mPlugins`, `mPrefabs`). `SpawnList::Spawn` -> `SpawnModuleOnTheFly`.
- `ModuleFactory::GetSpawnableModules(category)` lists factory entries; for Audio, appends `EffectFactory::GetSpawnableEffects()` with decorator `kEffectChainSuffix` (`"[effectchain]"`).
- `GetSpawnableModules(keys, continuousString)`: quick-type filter plus VSTs, prefabs, MIDI devices, effects, presets. Used by `QuickSpawnMenu`.
- Cable drop: `CableDropBehavior::ShowQuickspawn`; `QuickSpawnMenu::MatchesFilter` uses `ModuleInfo.mCanReceive*` vs `PatchCableSource::GetConnectionType()`.
- Console: type a label, spawn at mouse.

### Effect factory (second contract)

`Source/EffectFactory.h`. `typedef IAudioEffect* (*CreateEffectFn)(void)`. String map, no categories, no Accepts* flags.

Examples: `Register("gainstage", &(GainStageEffect::Create))`, `"delay"`, `"biquad"`, `"freeverb"`, `"pitchshift"`, ...

`GainStageEffect` : `IAudioEffect` + `IFloatSliderListener`; `Create()` returns `IAudioEffect*`, not `IDrawableModule*`. Hosted as a child of `EffectChain` (`IAudioProcessor` + `IDrawableModule`).

## Worked examples: how interfaces stack

### Gain (`Amplifier`, spawn `"gain"`)

```
Amplifier : public IAudioProcessor, public IDrawableModule, public IFloatSliderListener
```

- `Create` / `AcceptsAudio=true`
- ctor: `IAudioProcessor(gBufferSize)`, `IDrawableModule(120, 40)`
- `CreateUIControls`: base (audio output cable) + `new FloatSlider(this, "gain", ..., &mGain, 0, 2)`
- `Process`: `SyncBuffers()`, `ComputeSliders(i)`, multiply into `GetTarget()->GetBuffer()`, `GetBuffer()->Reset()`
- `LoadLayout` / `SetUpFromSaveData`: JSON `"target"` + `"show_level_meter"`
- No notes, no pulses, no modulator interface

### Oscillator (`SingleOscillator`, spawn `"oscillator"`)

```
SingleOscillator : public IAudioSource, public INoteReceiver, public IDrawableModule,
                   public IDropdownListener, public IFloatSliderListener,
                   public IIntSliderListener, public IRadioButtonListener,
                   public IControlVisualizer
```

- `AcceptsNotes=true`, `AcceptsAudio=false` (source, not receiver)
- Auto output cable is **audio** (`IAudioSource` wins over note in `CreateUIControls`)
- Notes enter `PlayNote` -> `NoteInputBuffer` / `PolyphonyMgr` of `IMidiVoice` (`SingleOscillatorVoice`)
- UI via `UIBLOCK` macros (`mVolSlider` binds `&mVoiceParams.mVol`, ADSR, osc type, filter, unison)
- `Process` writes to `GetTarget()`; `SendCC` empty
- Binary rev `GetModuleSaveStateRev() = 1` plus `LoadOldControl`

Helper `Oscillator` (`Source/Oscillator.h`) is **not** a module; it is a wavetable/naive oscillator used by `SingleOscillatorVoice` and `LFO`.

### Note output

There is no spawnable `NoteOutput` module. `NoteOutput` in `Source/INoteSource.h` is the fan-out helper owned by every `INoteSource`. Closest spawnable source: `NoteCreator` (`IDrawableModule` + `INoteSource` + `IPulseReceiver`), which `PlayNoteOutput`s on button or pulse.

`NoteEffectBase` is the note-processor mixin (`NoteRouter` : `NoteEffectBase` + `IDrawableModule` + `IRadioButtonListener`).

### LFO (`FloatSliderLFOControl`, spawn `"lfo"`)

Two layers:

- Helper `LFO` (`Source/LFO.h`): `ITimeListener` + `IAudioPoller`. Not a module.
- Module `FloatSliderLFOControl`: drawable + `IModulator` + `IPulseReceiver` + many UI listeners.
  - `AcceptsPulses=true` (reset via `OnPulse`)
  - `ShouldSuppress` not needed: it is not `IPulseSource`/`INoteSource`/`IAudioSource`, so **no auto cable**
  - Modulator cable created lazily in load/pin (`kConnectionType_Modulator`, `SetModulatorOwner`)
  - `LFOPool` of 256 instances for slider-attached LFOs; `HasSpecialDelete`; `IsSaveable` only when pinned
  - `Value(samplesIn)` is the modulator contract; `Active()` is `mEnabled`

Old `LFOController` is `REGISTER_HIDDEN` with `CanCreate()` singleton.

### Envelope (notes + pulses + modulator)

```
EnvelopeModulator : IDrawableModule + NoteEffectBase + IModulator + IPulseReceiver + listeners
```

`AcceptsNotes=true`, `AcceptsPulses=true`, `ShouldSuppressAutomaticOutputCable=true`, then manual modulator cable. `PlayNote` both starts ADSR and `PlayNoteOutput`s.

### Pulse source (`Pulser`)

```
Pulser : IDrawableModule + ITimeListener + IAudioPoller + IPulseSource + listeners
```

`AcceptsPulses=false` (does not receive). Auto cable is pulse because it is `IPulseSource` and not an audio/note source.

## What is missing vs a typed DSP plugin contract

| Typed plugin ABI (VST3/CLAP/JUCE `AudioProcessor`) | BespokeSynth |
|---|---|
| Port/pin descriptors (id, direction, type, channels) | `ConnectionType` + RTTI + `CanReceive*` statics |
| Parameter descriptors (id, range, units, automatable, gesture) | `IUIControl` widgets + `float*` members; names are strings |
| `process(block, inBuses, outBuses)` | `IAudioSource::Process(double time)` with hidden `ChannelBuffer` |
| Latency / tail samples | **Absent** on module interfaces. `LatencyCalculatorSender/Receiver` are user-facing measurement modules. Looper/pitch-shift have local `GetLatencyInSamples` hacks |
| Bus layouts, sidechain, >2 channels | `ChannelBuffer::kMaxNumChannels = 2` |
| Sample-rate / block-size prepare | Global `gSampleRate` / `gBufferSize`; no per-module prepare |
| Thread contract | Informal: audio `Process`, UI `Poll`, notes marshalled by `NoteOutputQueue` |
| Single plugin factory | Two factories (`ModuleFactory`, `EffectFactory`) plus hidden VST wrapper plus prefab/preset spawn methods |
| Stable parameter IDs | Control **names**; rename needs `UpdateOldControlName` |
| UI separated from DSP | `IDrawableModule` **is** the DSP node |
| MIDI ports | Folded into `INoteReceiver` (`PlayNote`/`SendCC`/`SendMidi`) |
| Event buses typed in the graph | Notes, pulses, modulator-to-widget, value-setter, grid, special all as cables |

Uniform pieces that **do** exist: `Create`/`CanCreate`/`Accepts*`, `CreateUIControls`/`Init`, JSON layout + binary state, one automatic output cable, dependency-sorted `Process` list.

That is a **closed, compiled-in module set** with MI capability flags, not an ABI a third-party DSP can implement without linking the whole UI stack.

## Relevance to Helioy / Audioface

If Audioface wants a modular engine, treat Bespoke as a negative space:

- Split **node DSP** from **panel UI**. Do not make the drawable the processor.
- Declare **ports** (audio block, note event, pulse/trigger, modulation) as data, not `dynamic_cast`.
- Declare **parameters** as descriptors with stable ids; widgets bind to them.
- One `process` with explicit buffers; report latency/tail.
- One factory. In-place FX should still be graph nodes (or a declared inner-chain type), not a second `IAudioEffect` hierarchy with `IsSaveable=false`.
- Keep Bespoke's useful bits: cable-type coloring, spawn-by-category, sample-accurate slider compute, note flush on repatch, stack-depth guards.

## Open questions

- Exact `IMidiVoice` voice stealing and how `voiceIdx` maps across note cables (out of Q1 scope).
- Whether `ScriptModule` / pybind exposes a stable subset of this contract beyond the stubs.
- How `Prefab` nested `ModuleContainer` interacts with `CanReceive*` of the outer module.
- Full `VSTPlugin` mapping from JUCE `AudioProcessor` onto Bespoke cables (hidden module; spawned as `SpawnMethod::Plugin`).

## Method note

fmm MCP resolved to `audioface-next/.fmm.db` (missing). Target tree has no fmm index. Analysis used `Source/*.h` and the listed `.cpp` files directly.
