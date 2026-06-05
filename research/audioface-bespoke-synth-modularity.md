---
title: BespokeSynth modularity, reviewed for Audioface
type: research
tags: [audioface, bespoke, modular-synth, dsp, plugin-contract, modulation, rack, game-audio]
summary: Source review of BespokeSynth at 3c4259cc. How modules, cables, modulation, racks, persistence, and UI actually work, and what Audioface should borrow or refuse for a uniform DSP plugin contract.
status: active
created: 2026-09-03
updated: 2026-09-03
project: audioface-next
confidence: high
source: https://github.com/BespokeSynth/BespokeSynth
commit: 3c4259cc4b38878d210fe6d2b8b5ab69c2f06373
related:
  - audioface-2026-09-engine-review.md
  - audioface-game-audio-middleware-gaps.md
  - audioface-2026-09-SYNTHESIS.md
---

# BespokeSynth modularity, reviewed for Audioface

Reviewed `https://github.com/BespokeSynth/BespokeSynth` at commit `3c4259cc4b38878d210fe6d2b8b5ab69c2f06373` (shallow clone under `~/.cache/bespoke-review/BespokeSynth`). Source only. Bespoke is a live patching studio written in C++17 on JUCE, with an OpenFrameworks shaped drawing layer in `Source/OpenFrameworksPort.h`. License is GPL-3. Borrow the design. Do not copy the code.

The product Audioface is heading toward is a layer and plugin sound design tool (Scene, Sound, Layer, Plugin, Rack, Bus, Modulation, Macro, RTPC, Gate report) with a uniform DSP plugin contract. Bespoke solves a nearby problem, modular synthesis on an infinite canvas, with a contract that is inheritance, cables, and a factory macro. That is the interesting part.

## 1. Module contract

A module is an `IDrawableModule` (`Source/IDrawableModule.h`). That class is also `IClickable`, `IPollable`, and `IPatchable`. DSP, notes, pulses, and modulation are extra bases mixed in.

| Interface | Path | What it requires |
| --- | --- | --- |
| `IDrawableModule` | `Source/IDrawableModule.h` | `DrawModule`, `CreateUIControls`, layout and state save |
| `IPatchable` | `Source/IPatchable.h` | `GetPatchCableSource`, `PostRepatch` |
| `IAudioSource` | `Source/IAudioSource.h` | `Process(double time)`, viz ring `mVizBuffer` |
| `IAudioReceiver` | `Source/IAudioReceiver.h` | `GetBuffer()` returning `ChannelBuffer`, mono or multichannel `InputMode` |
| `IAudioProcessor` | `Source/IAudioProcessor.h` | receiver plus source, `SyncBuffers` |
| `IAudioEffect` | `Source/IAudioEffect.h` | `ProcessAudio(time, ChannelBuffer*)`, lives inside a chain, `IsSaveable` is false |
| `INoteSource` / `INoteReceiver` | `Source/INoteSource.h`, `Source/INoteReceiver.h` | `PlayNote(NoteMessage)`, `NoteOutput` fan-out |
| `IPulseSource` / `IPulseReceiver` | `Source/IPulseReceiver.h` | `OnPulse(time, velocity, flags)`, `DispatchPulse` |
| `IModulator` | `Source/IModulator.h` | `Value(samplesIn)`, `Active`, min and max range |
| `NoteEffectBase` | `Source/NoteEffectBase.h` | note receiver plus source, default pass-through |

A typical thru module stacks all of this. `Amplifier` (`Source/Amplifier.h`) is `IAudioProcessor`, `IDrawableModule`, and `IFloatSliderListener`. `EnvelopeModulator` (`Source/EnvelopeModulator.h`) is `IDrawableModule`, `NoteEffectBase`, `IModulator`, `IPulseReceiver`, plus four UI listener bases. There is no port table, no parameter descriptor object, no latency or tail field, no seed namespace, no UI descriptor separate from the widgets the constructor allocates.

Parameters are widgets. `CreateUIControls` builds `FloatSlider`, `Checkbox`, `DropdownList`, and friends, each bound to a member pointer. `IDrawableModule::CreateUIControls` also auto-spawns one output `PatchCableSource` whose `ConnectionType` is inferred by `dynamic_cast`: audio source, note source, grid, or pulse source. `ShouldSuppressAutomaticOutputCable` opts out. `ModuleSaveData` (`Source/ModuleSaveData.h`) holds extra layout properties (ints, floats, bools, strings, enums) that are not the live widgets.

The factory is a constructor full of macros (`Source/ModuleFactory.cpp`). `REGISTER(class, name, type)` stores `class::Create`, `class::CanCreate`, `class::AcceptsAudio`, `AcceptsNotes`, `AcceptsPulses`, a `ModuleCategory`, and hidden or experimental flags. At this commit that is 223 public names, 30 hidden, 2 experimental. `VSTPlugin` is hidden under the type name `plugin`. Instantiation is `ModuleFactory::MakeModule`. Spawn from the UI also covers `SpawnMethod::EffectChain`, `Prefab`, `Plugin` (scanned VST or AU), `MidiController`, and `Preset`.

The one hard check in the contract is `IDrawableModule::Init`. It copies factory flags onto the instance, then asserts `AcceptsAudio()` matches `dynamic_cast<IAudioReceiver*>`, and the same for notes and pulses. If a class inherits `IPulseReceiver` but `AcceptsPulses()` returns false, debug builds abort. That is the closest thing Bespoke has to a typed port declaration.

Worked example. `Amplifier::Create` returns `new Amplifier()`. The factory records `AcceptsAudio() == true`. `CreateUIControls` makes a `FloatSlider` on `mGain`. `Process` reads `GetBuffer()`, multiplies by `mGain` while calling `ComputeSliders` per sample, `Add`s into `GetTarget()->GetBuffer()`, and writes `GetVizBuffer()`. No descriptor was consulted. The C++ type is the contract.

## 2. Cable and port typing

Cables are `PatchCable` objects owned by a `PatchCableSource` (`Source/PatchCable.h`, `Source/PatchCableSource.h`). The type enum is `ConnectionType`.

| `ConnectionType` | Color source | Default fan-out | Valid targets from `PatchCableSource::FindValidTargets` |
| --- | --- | --- | --- |
| `kConnectionType_Note` | `kModuleCategory_Note` hue | multiple | modules with `CanReceiveNotes()` |
| `kConnectionType_Audio` | `kModuleCategory_Audio` hue | multiple | modules with `CanReceiveAudio()` |
| `kConnectionType_Pulse` | `kModuleCategory_Pulse` hue | multiple | modules with `CanReceivePulses()`, plus UI controls that opt in |
| `kConnectionType_Modulator` | `kModuleCategory_Modulator` hue | multiple | `IUIControl` and `UIGrid` that return true from `CanBeTargetedBy` |
| `kConnectionType_ValueSetter` | same hue, lower saturation | multiple | same as modulator, one-shot set rather than a continuous write |
| `kConnectionType_UIControl` | other | as configured | UI controls, used by `Snapshots` and `EventCanvas` |
| `kConnectionType_Grid` | other, with a grid icon | as configured | `UIGrid` targets |
| `kConnectionType_Special` | other | as configured | any module |

`PatchCableSource::SetConnectionType` paints the cable from `IDrawableModule::GetColor`. Category hues live as statics (`sHueNote`, `sHueAudio`, `sHueInstrument`, `sHueNoteSource`) plus hard-coded HSB for processor, modulator, and pulse. A circular audio dependency turns the cable yellow and pulses it (`PatchCableSource::GetColor` when `mIsPartOfCircularDependency`).

Enforcement is a cached list rebuilt when a cable is grabbed. `FindValidTargets` walks every module. Audio and note cables land on modules. Modulator, value setter, UI control, pulse, and grid cables also walk `GetUIControls()` and keep those for which `IUIControl::CanBeTargetedBy` is true. The default implementation (`Source/IUIControl.cpp`) accepts modulator, value setter, and UI control. `Checkbox::CanBeTargetedBy` and `ClickButton::CanBeTargetedBy` also accept pulse, so a pulse cable can click a button or flip a box. `ADSRDisplay` returns false and cannot be targeted. Type filters (`AddTypeFilter`, `SetPredicateFilter`) further restrict some sources.

Dragging a cable onto a slider is the modulation target story. The slider is an `IClickable`. The cable's target is that control. `IModulator::OnModulatorRepatch` then `dynamic_cast`s to `FloatSlider`, calls `FloatSlider::SetModulator(this)`, and initializes min and max from `GetModulationRangeMin` / `Max`. Up to 10 targets sit in `IModulator::mTargets`. Duplicate targets on the same source are rejected in `AddPatchCable`. Cap on cables per source is `IDrawableModule::kMaxOutputsPerPatchCableSource` (32).

Audio sidechain is ordinary extra cables plus `ModulationChain::SetSidechain` on the per-note path. There is no dedicated sidechain port type. Pulse carries `PulseFlags` (`Reset`, `Random`, `SyncToTransport`, `Backward`, `Align`, `Repeat`) as an int, which is the nearest thing to a typed event payload besides `NoteMessage`.

## 3. Modulation

Two systems run in parallel.

**Control modulation.** An `IModulator` writes into widgets. `FloatSliderLFOControl` (`Source/FloatSliderLFOControl.h`) and `EnvelopeModulator` are the usual sources. `IModulator::Value(int samplesIn)` is the read. `FloatSlider::Compute(samplesIn)` calls `DoCompute`, which assigns `*mVar = mModulator->Value(samplesIn)` when the modulator is active. Owners that care about audio rate call `IDrawableModule::ComputeSliders(i)` inside the sample loop (`Amplifier::Process`, `EffectChain::Process` dry or wet). Owners that do not, skip it. `FloatSlider::Poll` will `Compute()` if nothing has computed in 0.1 ms, so a slider still moves when its owner never asks. `IModulator::Poll` is a UI-thread extra poller. It blends with `ofGetFrameRate()` and, for non-slider targets (`RequiresManualPolling`), calls `SetValue` or `SetFromMidiCC`. Continuous modulation of a float is audio rate only if the DSP owner samples it. Modulation of a checkbox or dropdown is UI poll rate.

Range is owned by the slider. The modulator's min and max aliases (`IModulator::GetMin`, `GetMax`) point at `FloatSlider::mModulatorMin` and `mModulatorMax`. `FloatSliderLFOControl::GetLFOValue` runs `LFO::Value`, applies `Spread`, then `Interp(val, GetMin(), GetMax())` clamped to the slider extents. Slider modes (`kNormal`, `kLogarithmic`, `kSquare`, `kBezier`) affect display and mouse mapping through `ValToPos` / `PosToVal`. `LFOSettings` also has interval, oscillator type, offset, bias, soften, shuffle, free rate, length, low-res mode, and `mRandomSeed`. Low-res mode skips `DoCompute` when `samplesIn != 0`.

Visibility is real. A modulated slider draws a green range bar and min or max ticks (`FloatSlider::Render`). The LFO module draws its own waveform. `ModulationVisualizer` (`Source/ModulationVisualizer.h`) is a note-thru module that displays per-note `ModulationParameters`, which is the other system.

**Voice modulation.** `NoteMessage` (`Source/INoteReceiver.h`) carries `ModulationParameters`: pointers to `ModulationChain` for pitch bend, mod wheel, and pressure, plus a pan float. `ModulationChain::GetValue(samplesIn)` (`Source/ModulationChain.cpp`) sums a `Ramp`, an `LFO` scaled by `mLFOAmount`, an optional per-sample `mBuffer`, a multiply-in chain, a sidechain chain, and a previous chain. This is MPE-style note decoration, sampled at `gTime + gInvSampleRateMs * samplesIn`. It does not go through `IModulator` and does not paint a slider.

## 4. Nesting and grouping

`EffectChain` (`Source/EffectChain.h`) is a module that hosts a rack of `IAudioEffect`. Max 100 effects (`MAX_EFFECTS_IN_CHAIN`). `EffectFactory` (`Source/EffectFactory.cpp`) registers 18 types (bitcrush, delay, djfilter, biquad, distortion, tremolo, compressor, noisify, gate, muter, pumper, granulator, dcremover, freeverb, basiceq, pitchshift, butterworth, gainstage). `EffectChain::Process` copies the input to `mDryBuffer`, calls `ProcessAudio` on each effect, then crossfades with a per-slot dry or wet array while calling `ComputeSliders` per sample. Effects are children drawn in a grid (`mNumFXWide`), with move, delete, and dry or wet controls. They are not canvas modules. `IAudioEffect::IsSaveable` is false, so they serialize through the chain, not as top-level layout entries. This is the rack.

`Prefab` (`Source/Prefab.h`) owns a `ModuleContainer`. Drop a module onto it and `TakeModule` reparents it. Save writes JSON `modules` plus binary state, same split as a full patch (`Prefab::SavePrefab`). Load is `LoadModules` then `LoadState`. Prefabs do not nest. `Prefab::IsAddableModule` rejects another `Prefab` and anything whose parent is already a prefab. Singletons (transport, scale) stay out. Cables into and out of a prefab are ordinary patch cables on the contained modules. Prefab also has a remove-module cable. There is no prefab-level audio or note port. The group is visual and serialisation, not a bus.

`IDrawableModule::GetContainer` is the nesting hook. `Prefab` returns its container. Most modules return null. Children that are not in a container still exist (`mChildren`) and save as named blobs under the parent. That is as deep as grouping goes.

`Snapshots` (`Source/Snapshots.h`) stores control values and can cable `kConnectionType_UIControl` onto grids. `ControlInterface` (`Source/ControlInterface.h`) lets you add sliders by name and is the closest thing to a Macro panel. Neither is a nested graph.

## 5. Audio thread and processing model

The callback is `ModularSynth::AudioOut` (`Source/ModularSynth.cpp`). It records `sAudioThreadId`, disables denormals, takes `mAudioThreadMutex`, drains `NoteOutputQueue`, then for each IO offset equal to `gBufferSize` it clears output, advances `gTime` by `gInvSampleRateMs * mIOBufferSize`, advances `TheTransport`, and calls `mSources[i]->Process(gTime)`. Oversampling (`UserPrefs.oversampling`) repeats that inner size. `gBufferSize` is asserted equal to `mIOBufferSize`. Host block size is the engine block size. `kWorkBufferSize` (`Source/SynthGlobals.h`) is `8192 * 16 * 2`, a global scratch `gWorkBuffer` sized for the largest buffer times oversampling times two, because `EffectChain` uses the scratch twice for dry or wet.

The graph is push from a sorted source list, pull of input buffers. Each `IAudioProcessor` reads `GetBuffer()` (filled by upstream `Add`s), writes into `GetTarget(i)->GetBuffer()`. `IAudioSource::GetTarget` is the cable's `GetAudioReceiver`. There is no compiled node list and no delay-compensated mixer. Ordering is `ArrangeAudioSourceDependencies`, a repeated scan that emits a source only once every dependency is already in `mSources`. The loop cap is 1000. Hitting it sets `mHasCircularDependency`, appends the leftovers anyway, and `FindCircularDependencySearch` paints those cables. Feedback still runs, one block late because the downstream buffer is last block's contents plus this block's adds. There is no plugin latency field and no tail length. `LatencyCalculatorSender` / `Receiver` are ping modules for measuring round trip, not a contract.

Thread split. Audio holds `mAudioThreadMutex`. Load and save take it too (`LoadLayout`, `CompleteQueuedSaveState`, `Prefab::LoadPrefab`). UI-thread notes go through `NoteOutputQueue` (`Source/NoteOutputQueue.h`, a `readerwriterqueue`). `NoteOutput::PlayNoteInternal` adds transport lookahead and one extra buffer of delay for note-offs when the caller is not the audio thread. Note chains have a stack cap of 100 to stop recursive `PlayNote` cycles (`kMaxDepth`). `EffectChain::Process` takes `mEffectMutex` on the audio thread while iterating effects. `IDrawableModule::ComputeSliders` has a commented `mSliderMutex` with a note that acquiring it was too slow.

Allocation on the audio thread is avoided by habit, not by API. Receivers own a `ChannelBuffer` sized at construction to `gBufferSize`. Effects copy that into `mDryBuffer` every slot every block. Global scratch absorbs the rest. There is no `new` in `Amplifier::Process`. Adding or removing a VST output cable is deferred with `mWantsAddExtraOutput` flags and then mutates bus layout inside `VSTPlugin::Process`.

## 6. Persistence

Two layers.

JSON layout from `ModularSynth::GetLayout`: keys `modules`, `ui_modules`, `zoomlocations`. Each module object comes from `IDrawableModule::SaveLayoutBase`: `position`, `name`, `type`, optional `start_minimized` and `draw_lissajous`, then `ModuleSaveData::Save`, then the virtual `SaveLayout`. Connections in JSON are strings. `UpdateTarget` (`Source/SynthGlobals.cpp`) writes `target`, `target2`, … for audio sources (one name per output index) and a comma-separated `target` list for note, pulse, and grid sources. The blank factory layout (`resource/userdata_original/layouts/blank.json`) looks like this.

```json
{
  "modules": [
    { "name": "gain", "position": [1525.0, 910.0], "target": "splitter", "type": "gain" },
    { "name": "splitter", "position": [1545.0, 990.0], "target": "output 1", "target2": "output 2", "type": "splitter" }
  ],
  "zoomlocations": []
}
```

Load is `ModuleContainer::LoadModules` then `SetUpModule` -> `LoadLayoutBase` -> `SetUpPatchCables`. `ModuleFactory::FixUpTypeName` and `EffectFactory::MakeEffect` (`"eq"` becomes `"basiceq"`) are the migration hooks at type level.

Binary state is a `.bsk` file (`ModularSynth::CompleteQueuedSaveState`). Magic `bskfile`, then `kSaveStateRev` (427), an optional PNG screenshot, the JSON layout as a raw string, then `ModuleContainer::SaveState`. Each module writes `GetModuleSaveStateRev()`, a base rev (4), pin state, size if resizable, then named controls with raw `GetValue()` plus `control->SaveState`, a `"controlseparator"` marker, children or nested container, then each `PatchCableSource::SaveState` as a list of `IClickable::Path()` strings. Paths use `~` for context (`IClickable::SetSaveContext`), so a control inside a prefab round-trips as a relative path. `LoadModuleSaveStateRev` checks `rev <= GetModuleSaveStateRev()` when the file rev is at least 423. Per-control `UpdateOldControlName` and `LoadOldControl` patch old names. `comment_out` in JSON skips a module at load.

This split is why a patch can open after a slider was renamed in code, and why extra cables that never had a `target` key still survive in the `.bsk`.

## 7. Scripting and extension

`ScriptModule` (`Source/ScriptModule.h`) embeds Python through pybind11 (`Source/ScriptModule_PythonInterface.i`). The `bespoke` module exposes transport, scale, tempo, `get_modules`, `get_controls`, and `random(seed, index)` which calls `DeterministicRandom`. The `me` object plays notes, schedules note messages and method calls in measure time, `get`/`set`/`adjust` controls by path, and can grow extra note outputs. The `module` submodule has `module.create(type, x, y)` -> `ModularSynth::SpawnModuleOnTheFly` and `module.get(path)`. Bindings also reach sequencers, VST, snapshots, drums, and `ControlInterface`. Scripts run on the UI poll path (`ScriptModule::Poll`, `RunCode`). Notes they emit still go through `NoteOutputQueue` if that happens off the audio thread. There is a trust flag (`mIsScriptUntrusted`). OSC in and MIDI in are first class.

VST and AU hosting is `VSTPlugin` (`Source/VSTPlugin.h`) wrapping `juce::AudioProcessor`. `VSTLookup::GetAvailableVSTs` fills `ModuleFactory::Spawnable` with `SpawnMethod::Plugin`. The module is an `IAudioProcessor` and `INoteReceiver`. Extra stereo outs are extra cables. The plugin window is `VSTWindow`. This is the only way a third party ships DSP without a Bespoke rebuild.

A first-party module is a rebuild. Add `Foo.h` / `Foo.cpp`, implement `Create`, `AcceptsAudio` / `Notes` / `Pulses`, `DrawModule`, `CreateUIControls`, then `REGISTER(Foo, foo, kModuleCategory_*)` in the `ModuleFactory` constructor and a CMake source list. There is no C ABI, no process isolation, no descriptor file. `CONTRIBUTING.md` talks about issues and Discord, not a plugin SDK. Hidden modules (`REGISTER_HIDDEN`) stay out of the spawn menu, which is how `VSTPlugin` itself is registered while scanned plugins appear under `[plugin]`.

## 8. UI approach

Drawing is immediate, once per frame, per module. `IDrawableModule::Render` -> `DrawFrame` -> `DrawModule`. `DrawFrame` samples up to 500 frames of `IAudioSource::GetVizBuffer()` (0.1 s of `RollingBuffer`) and turns RMS into title-bar highlight. Receive pips on the title bar show whether the module accepts audio, notes, or pulses, in those hues. `ModuleContainer::DrawModules` walks the list, `DrawPatchCables` behind then in front so modulator cables sit above audio. Zoom and pan are `LocationZoomer` (`Source/LocationZoomer.h`) plus `ModuleContainer::mDrawScale` and `mDrawOffset`. Letter keys store camera bookmarks (`WriteCurrentLocation`). Vanity panning wanders those bookmarks. There is no automatic layout.

The coupling cost is that every module is a UI widget and a DSP object. `Amplifier::Process` writes `LevelMeterDisplay` from the audio thread. `DrawFrame` reads the viz ring from the UI thread with no obvious fence beyond the hope that a rolling buffer of floats is safe enough. `ComputeSliders` mutates the same `float*` the slider draws. Extra pollers (`IModulator::Poll`) write controls on the UI thread while audio may be reading them. Push 2 and Ableton Move get their own draw paths (`DrawToPush2Screen`, `DrawToAbletonMoveScreen`). The canvas is the product. There is no rack view, no mixer view, no graph-only view. Minimized modules and prefabs are the only compression.

## Conclusion

### (a) Five things Audioface should borrow

1. **Every control is a modulation target.** `IUIControl::CanBeTargetedBy` plus `PatchCableSource::FindValidTargets` is the whole trick. A cable type that lands on a parameter, not only on a module, is how LFO, envelope, Macro, and RTPC become one gesture. Keep the colored type map (`ConnectionType` -> hue). Drop the walk-every-module scan; an index of ports should answer the same question.

2. **Factory flags that must match the real inputs.** `IDrawableModule::Init` asserting `AcceptsAudio` against `IAudioReceiver` is the right instinct. Audioface's plugin contract should make illegal combinations unrepresentable (typed audio, control, and event ports on the descriptor), so a debug assert is unnecessary. The idea to steal is "declare receives X, and the runtime believes only that."

3. **`Value(samplesIn)` as the modulator read.** `IModulator::Value` and `FloatSlider::DoCompute` let the same object be sampled once per block or once per sample, depending on the owner. That is how a Plugin reports a control-rate port and an audio-rate port without two modulator types. Pair it with an explicit rate on the port, which Bespoke never wrote down.

4. **EffectChain as a rack of inserts.** `EffectChain` plus `IAudioEffect` plus `EffectFactory` is the Rack. Ordered slots, per-slot dry or wet, a second factory, no canvas cables between slots. Audioface Layers and insert Plugins belong here. Graph cables belong on Scene, Bus, and sidechain.

5. **JSON graph plus versioned blob.** `SaveLayoutBase` (`type`, `name`, `position`, `target`) is diffable and greppable. `GetModuleSaveStateRev` plus named controls is how widgets evolve. Audioface should keep that split for Scene and Sound files, with the blob covering serialisable plugin state the descriptor promised.

### (b) Five things to avoid

1. **Inheritance as the plugin contract.** `EnvelopeModulator`'s base list is the failure mode. A uniform contract is a descriptor (ports, parameters, seed namespace, latency, tail, state, UI) and a `process(block)` function. C++ mixins will not survive WASM, worklets, or third-party Plugins.

2. **One object that draws and processes.** `IDrawableModule::DrawFrame` reading `GetVizBuffer` while `Process` writes it, and `ComputeSliders` aliasing the slider's `float*`, is why a live patching app feels alive and why a game kernel cannot ship that way. UI descriptors render on the authoring thread. Meters consume a lock-free peek. The Plugin never includes `DrawModule`.

3. **Cycles handled by a loop cap.** `ArrangeAudioSourceDependencies` with `kMaxLoopCount == 1000` still runs the cycle and paints the cable. A game mixer that feedbacks without an explicit delay line is a glitch. Detect at content load. Either insert a one-block delay and report it as latency, or refuse the graph. Plugins should declare latency and tail so the host can do that without guessing.

4. **Global scratch and mutexes on the audio thread.** `gWorkBuffer` and `EffectChain::mEffectMutex` are the opposite of a block renderer you can certify. Audioface already renders from owned buffers with a seed tree. Keep that. A Plugin gets input and output spans. It does not take a process-wide lock to reorder its Rack.

5. **Compile-in `REGISTER` as the extension path.** First-party modules should load from a descriptor and a package, the way Audioface already wants Plugins to work. VST via `VSTPlugin` is a host feature, not the Audioface plugin model. Also, the tree is GPL-3. Ideas move. Code does not.

### (c) Infinite canvas versus chassis plus graph

Bespoke's UI is `ModuleContainer` plus `LocationZoomer`. The patch is the instrument. Bookmarks and prefabs exist because a flat plane of 223 module types does not scale. That is correct for a modular synth and wrong as the default for a game sound tool.

A sound designer shipping footsteps needs a Sound, its Layers in a Rack, a few Macros, RTPC bindings, and a Gate report. That is a chassis. Buses and sends are a mixer strip. The specialist graph (typed cables, modulation onto parameters, feedback with declared delay) is the Plugin editor and the Bus editor, opened when the chassis is not enough. Bespoke's canvas is that specialist graph, promoted to the whole application. Steal the cable semantics for the graph view. Do not steal the canvas as home.

`Prefab` as one-level group is a weak Scene. A Scene in Audioface has policy (voice class, steal, spatial) that a rectangle full of modules does not. Use containment in the data model. Do not use a draggable window as the model.

### (d) Determinism and testability

What Bespoke has: `bespoke.random(seed, index)` -> `DeterministicRandom`; `LFO::SetRandomSeed`; timestamped `NoteMessage`; `gTime` advanced from buffer length; `Transport`; Python schedule in measure time; a note queue that makes UI-thread triggers audio-thread ordered.

What it lacks: a test target (no `add_test`, no Catch2, no unit tests in `CMakeLists.txt`); an offline bounce that must match the callback sample for sample; a seed namespace that DSP owns rather than a Python helper; a block renderer with no host `gBufferSize`; a prohibition on UI-rate `IModulator::Poll` affecting the sound; a Plugin latency and tail number; a certification gate. Circular graphs, VST, `ofGetFrameRate()` blends, and `mAudioThreadMutex` contention all make bit identity impossible.

Audioface already has the property Bespoke only touches: frames, linear gain, counter hashed noise labeled by id, certification gates. The lesson from this tree is which modular synth habits would throw that property away. Inheritance as the contract, canvas as the product, global scratch, a mutex on process, and undelayed feedback are the ones that would.
