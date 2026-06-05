---
title: BespokeSynth scripting, VST hosting, UI drawing, and determinism
type: research
tags: [bespokesynth, python, pybind11, vst, juce, nanovg, modular, ui, determinism, tests]
summary: Bespoke has no C plugin ABI; native modules are compile-in via ModuleFactory REGISTER. Python talks to the engine through pybind11 embedded modules in a .i file that is not SWIG. UI is immediate-mode nanoVG behind an of* shim, tightly coupled to live viz buffers.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# BespokeSynth Q7/Q8: scripting, VST, UI, tests, determinism

Clone: `/Users/alphab/.cache/bespoke-review/BespokeSynth` (commit `3c4259cc4b38878d210fe6d2b8b5ab69c2f06373`).

**Index note.** fmm MCP has no index for this tree (it resolved to `audioface-next/.fmm.db`). Structural reads used file listing plus targeted source reads.

## Executive Summary

Bespoke is a live-patchable modular synth. First-party modules are compiled in via `ModuleFactory::REGISTER` (223 public + 30 hidden, plus one Mac-only hidden). There is no stable C plugin ABI. Runtime extension is Python (`ScriptModule` + pybind11 embedded modules in `Source/ScriptModule_PythonInterface.i`) and JUCE-hosted VST3/AU/LV2 (optional VST2) appearing as hidden type `plugin`. The patcher UI is immediate-mode nanoVG behind an openFrameworks-shaped shim (`OpenFrameworksPort`), not retained JUCE widgets. DSP time (`gTime`) advances in the audio callback; Python and drawing run on the main/render threads and read live viz buffers without a shared lock.

## Project Metadata

- Language: C++17. App target `BespokeSynth` via `juce_add_gui_app` in `Source/CMakeLists.txt`.
- Windowing / audio / plugin host: vendored JUCE (`libs/JUCE`). Defines `JUCE_PLUGINHOST_VST3=1`, `JUCE_PLUGINHOST_LV2=1`, `PLUGINHOST_AU TRUE`, `JUCE_PLUGINHOST_VST` gated on `BESPOKE_VST2_SDK_LOCATION`.
- Drawing: vendored nanoVG GLES2 (`libs/nanovg`, `bespoke::nanovg`). Created in `MainContentComponent::initialise` as `nvgCreateGLES2`.
- Python: CMake `find_package(Python 3.6 COMPONENTS Interpreter Development REQUIRED)`. Bindings are **pybind11**, not SWIG (`bespoke::pybind11` in `libs/CMakeLists.txt`, `PYBIND11_EMBEDDED_MODULE` in `Source/ScriptModule_PythonInterface.i`). The `.i` suffix is leftover naming; the file is `#include`d from `Source/ScriptModule.cpp`.
- Other: Ableton Link, oddsound MTS, freeverb, exprtk, jsoncpp, readerwriterqueue, Push2/Move USB, pybind11 embed.
- Version: CMake `project(BespokeSynth VERSION 1.3.0)`.

## Architecture

### Module factory

`Source/ModuleFactory.h` / `Source/ModuleFactory.cpp`.

- `CreateModuleFn` / `CanCreateModuleFn` function pointers.
- Macros: `REGISTER`, `REGISTER_HIDDEN`, `REGISTER_EXPERIMENTAL`.
- Live counts in `ModuleFactory::ModuleFactory()`: **223** `REGISTER(`, **30** `REGISTER_HIDDEN(`, **0** live `REGISTER_EXPERIMENTAL` (macro exists; only a commented `MidiPlayer` use). Mac-only extra: `REGISTER_HIDDEN(KompleteKontrol, kompletekontrol, ...)`.
- `ModuleInfo` stores category, hidden/experimental flags, and `AcceptsAudio` / `AcceptsNotes` / `AcceptsPulses` from static methods on the class.
- `ModuleFactory::Spawnable` + `SpawnMethod` enum: `Module`, `EffectChain`, `Prefab`, `Plugin`, `MidiController`, `Preset`.
- `MakeModule(type)` looks up `mFactoryMap` and calls `mCreatorFn()`.
- `ModularSynth::CreateModule` special-cases singletons `"transport"` / `"scale"`, otherwise `mModuleFactory.MakeModule(type)` after `ModuleFactory::FixUpTypeName` (`"vstplugin"` -> `"plugin"`).

Effects are a second factory: `Source/EffectFactory.cpp` `Register("delay", &DelayEffect::Create)` etc. Spawned as an `EffectChain` via `SpawnMethod::EffectChain`.

### Adding a first-party module (no ABI)

`CONTRIBUTING.md` (repo root) covers clone, cmake, clang-format, PRs. It does **not** document a plugin API. Adding a module is fork-and-recompile:

1. New `Source/Foo.h` / `Source/Foo.cpp` subclassing `IDrawableModule` (plus `IAudioProcessor` / `INoteReceiver` / `IPulseReceiver` as needed).
2. Static `Create()`, `AcceptsAudio()`, `AcceptsNotes()`, `AcceptsPulses()`.
3. Include the header in `Source/ModuleFactory.cpp` and `REGISTER(Foo, foolabel, kModuleCategory_*)`.
4. Add both files to `target_sources(BespokeSynth PRIVATE ...)` in `Source/CMakeLists.txt`.
5. Optional: pybind11 surface in `Source/ScriptModule_PythonInterface.i`, then regenerate stubs/docs with `bespoke_script_autodoc.py`.

There is no `dlopen` of user modules, no `extern "C"` module API, no COM/C ABI for Bespoke modules. `gShowDevModules` (`Source/SynthGlobals.cpp`, default false) unhides `REGISTER_HIDDEN` types in spawn menus.

VST/AU/LV2 plugins are the only binary extension path, and they appear as one hidden module type wrapping JUCE `AudioProcessor`.

---

## Question 7 — Scripting and extension

### Python: not SWIG

`Source/ScriptModule_PythonInterface.i` is C++ included by `Source/ScriptModule.cpp`. It defines 22 `PYBIND11_EMBEDDED_MODULE` namespaces:

`bespoke`, `scriptmodule`, `notesequencer`, `drumsequencer`, `basslinesequencer`, `grid`, `notecanvas`, `sampleplayer`, `midicontroller`, `linnstrument`, `osccontroller`, `oscoutput`, `envelope`, `drumplayer`, `vstplugin`, `snapshots`, `interface`, `beats`, `abletongriddevice`, `sessionorganizer`, `trackorganizer`, `module`.

Interpreter: `ScriptModule::InitializePythonIfNecessary` calls `py::initialize_interpreter()` then `py::exec(GetBootstrapImportString())` where bootstrap is `"import bespoke; import module; import scriptmodule; import random; import math"`. Portable builds set `Py_SetPythonHome`. `ScriptModule::UninitializePython` calls `py::finalize_interpreter()`.

Trust gate: checksum allow-list; untrusted scripts spawn hidden `scriptwarning` (`ScriptWarningPopup`) and pause audio (`TheSynth->SetAudioPaused(true)`).

### How a script talks to the engine

`ScriptModule::RunCode` is documented in-source as main-thread only. `ScriptModule::RunScript` asserts `IsMainThread()`, then:

```
py::exec("me__N = scriptmodule.get_me(N)", py::globals());
```

`FixUpCode` rewrites `me.` / `this.` to `me__N.` and suffixes callback names (`on_pulse` -> `on_pulse__prefix`) so multiple script modules do not collide. `py::exec` / `py::eval` against `py::globals()`. Exceptions become `mLastError` on the code editor.

Callbacks (from `resource/scripting_reference.txt` and autodoc): `on_pulse()`, `on_note(pitch, velocity)`, `on_grid_button`, `on_osc`, `on_midi`, `on_sysex`, `on_ableton_grid_control`, `update_ableton_grid_leds`. These are invoked from `ScriptModule::Poll` (UI timer), OSC listener, MIDI queue, Ableton grid, not from the audio callback.

`ScriptModule::Poll` is reached from `MainContentComponent::timerCallback` -> `ModularSynth::Poll` -> `ModuleContainer::Poll` -> `IDrawableModule::BasePoll`.

### What Python can do

**Create / wire modules** (`PYBIND11_EMBEDDED_MODULE(module)`):

- `module.create(moduleType, x, y)` -> `TheSynth->SpawnModuleOnTheFly` (takes `mAudioThreadMutex`).
- `module.get(path)`, `set_position`, `set_target` (module pointer, path, or cable index), `set_name`, `delete`, `set`/`get`/`adjust` UI controls, `set_focus(zoom)`.

**Set controls** (`scriptmodule` `me.get`/`me.set`/`me.schedule_set`/`me.adjust`, plus `IDrawableModule.set`): `IUIControl::GetValue` / `SetValue` / `ScheduleUIControlValue`. Paths resolved by `ScriptModule::GetUIControl` (prefab `~` prefix rules).

**Schedule notes** (control-rate, measure-relative):

- `me.play_note` / `schedule_note` / `schedule_note_msg` / `note_msg` / `send_cc`.
- Delay is in **bars**: `GetScheduledTime(delay) = sMostRecentRunTime + delay * TheTransport->MsPerBar()`.
- Immediate notes: `PlayNoteFromScript` uses `sMostRecentRunTime`.
- Future notes go into fixed arrays: `mScheduledNoteOutput` size 200, `mScheduledMethodCall` 50, `mScheduledUIControlValue` 50. Full arrays silently drop.
- Dispatch: `PlayNoteOutput(note, true)` (`isFromMainThreadAndScheduled`). Non-audio-thread notes enqueue on `NoteOutputQueue` (`moodycamel::ReaderWriterQueue`), drained at the **start** of `ModularSynth::AudioOut` via `NoteOutputQueue::Process`.
- Patching a script note cable sets `Transport::sDoEventLookahead = true` (`ScriptModule::PostRepatch`). Lookahead is 150 ms (`Transport::sEventEarlyMs`). Title bar checkbox `lookahead (exp.)` binds the same flag.

**Transport / scale / view** (`bespoke` module): `get_measure_time`, `get_measure`, `reset_transport`, `get_step`, `time_until_subdivision`, `get_tempo`, `get_root`, `get_scale`, `tone_to_pitch`, `pitch_to_freq`, `random(seed, index)` -> `DeterministicRandom`, `get_modules`, `get_controls`, `location_recall`/`location_store` via `LocationZoomer`, `set_background_text`.

**Audio from Python: limited, not a DSP graph node.**

- `ScriptModule::AcceptsAudio()` returns **false**. No `Process(double time)` audio callback, no buffer in/out.
- `sampleplayer.fill(data)` (`SamplePlayer::FillData`) copies a `std::vector<float>` into a new `Sample` (offline buffer replace, not per-block processing).
- `sampleplayer.play_cue` fires `SamplePlayer::PlayNote`.
- `trackorganizer.get_level` reads a live meter (`GetGain()->GetLevel`).
- No API to read or write the audio callback buffer, no Python `IAudioProcessor`.

Specialized bindings exist for sequencers, grid, MIDI, OSC, VST MIDI (`vstplugin.send_cc`/`send_program_change`/`send_data` -> `VSTPlugin::SendMidi`), snapshots, ControlInterface sliders, Ableton grid LEDs.

Docs/stubs: `bespoke_script_autodoc.py` parses `///` comments in the `.i` file into `resource/scripting_reference.txt` and `resource/python_stubs/*/__init__.pyi`. Jedi autocomplete is optional.

### VST hosting

JUCE plugin host, not a custom VST SDK wrapper.

- `ModularSynth` owns `juce::AudioPluginFormatManager` and `juce::KnownPluginList`.
- Scan: `CustomPluginScanner` (`Source/VSTScanner.h/.cpp`) implements `juce::KnownPluginList::CustomScanner`. Default mode `"Avoid crashes"` launches the same executable as `PluginScannerSubprocess` (`Main.cpp` `initialiseFromCommandLine(..., kScanProcessUID)`). Alternate mode `"Within process"`. Cache file `vst/found_vsts.xml`. Recents `vst/recent_plugins.json`.
- `VSTLookup::GetAvailableVSTs` reads `KnownPluginList`, optional format preference (`UserPrefs.plugin_preference_order`), name sort.
- Module type: `REGISTER_HIDDEN(VSTPlugin, plugin, kModuleCategory_Synth)`. User-facing spawn is `SpawnMethod::Plugin` with `juce::PluginDescription`. `ModularSynth::SpawnModuleOnTheFly` maps that to type `"vstplugin"` then `FixUpTypeName` -> `"plugin"`, then `VSTPlugin::SetVST(spawnable.mPluginDesc)`.
- Load: `VSTPlugin::LoadVST` -> `TheSynth->GetAudioPluginFormatManager().createPluginInstance(desc, gSampleRate, gBufferSize, errorMessage)`, `prepareToPlay`, `setPlayHead(&mPlayhead)` (`VSTPlayhead` implements `juce::AudioPlayHead`).
- DSP: `VSTPlugin::Process` copies Bespoke `ChannelBuffer` into `juce::AudioBuffer<float>`, converts pending notes to `juce::MidiBuffer` with **sample offset** `(note.time - gTime) * gSampleRateMs`, splits events past `gBufferSize` into `mFutureMidiBuffer`, calls `mPlugin->processBlock(buffer, mMidiBuffer)`. MIDI from the plugin is emitted on `mMidiOutCable`. Extra stereo outs via `AddExtraOutputCable` (max 16 stereo). `mVSTMutex` around processBlock.
- UI: Bespoke module chrome via `VSTPlugin::DrawModule` (volume, presets, parameter sliders). Native editor is a separate `VSTWindow` (`juce::DocumentWindow` wrapping `pluginEditor`). Parameter sliders bind `juce::AudioProcessorParameter`.
- Python: MIDI only (`send_cc` / `send_program_change` / `send_data`). No parameter or audio buffer API on `vstplugin`.

### ABI answer

**Add a module = fork and recompile.** No stable Bespoke C plugin ABI. Third-party DSP as a Bespoke-looking box means shipping a VST/AU/LV2 and spawning the hidden `plugin` module, or contributing C++ to this tree.

---

## Question 8 — UI approach

### Immediate-mode per module

Not retained-mode JUCE components for the patcher.

Call chain:

1. `MainContentComponent` is `juce::OpenGLAppComponent` + `AudioIODeviceCallback` + `Timer` (`Source/MainComponent.cpp`). OpenGL 3.2. `openGLContext.setContinuousRepainting(false)`; timer at `UserPrefs.target_framerate` calls `mSynth.Poll()` then `openGLContext.triggerRepaint()`.
2. `render()`: `mSynth.LockRender(true)`, `nvgBeginFrame(gNanoVG, width, height, mPixelRatio)`, `mSynth.Draw()`, `nvgEndFrame`, `PostRender`, unlock.
3. `ModularSynth::Draw` sets `sRenderThreadId`, `mModuleContainer.SetDrawScale(gDrawScale)`, computes `mDrawRect` from pan/zoom, `ofScale(gDrawScale)` + `ofTranslate(GetDrawOffset())`, then `mModuleContainer.DrawContents()`. Separate unscaled pass for `mUILayerModuleContainer` (title bar, profiler, console).
4. `ModuleContainer::DrawContents`: unclipped pre-draw, cables, `DrawModules` (back to front; `AlwaysOnTop` second pass), cables in front, unclipped post-draw.
5. `IClickable::Draw` -> `IDrawableModule::Render` -> `DrawFrame` -> virtual `DrawModule()` (pure virtual, implemented per module).

`DrawFrame` draws title bar, enable checkbox, category-colored rounded rect, optional nanoVG box-gradient inner fade (`nvgBoxGradient` / `nvgFill` on `gNanoVG`), then `ofPushMatrix` + `ofClipWindow` + `DrawModule()`.

`ofPushMatrix` / `ofPopMatrix` are `nvgSave` / `nvgRestore` (`Source/OpenFrameworksPort.cpp`). The entire `of*` API (`ofRect`, `ofSetColor`, `ofLine`, fonts) is a shim over nanoVG. This is **not** openFrameworks; `OpenFrameworksPort` is a compatibility layer so old OF-style drawing compiles on JUCE+nanoVG.

Four nanoVG contexts (`NanoVGRenderContext`): `Main`, `FontBounds`, `AbletonPush2Screen`, `Screenshot`. Push2 and welcome-screen screenshots render to `NVGLUframebuffer`.

JUCE widgets are used for: the OS window, OpenGL context, audio devices, plugin editor windows (`VSTWindow`), plugin list (`PluginListWindow` / `CustomPluginListComponent`), file choosers.

### Canvas, zoom, pan, layout

The patcher canvas is **not** `Source/Canvas.h` (that is a piano-roll / clip `IUIControl` used by `NoteCanvas` / `EventCanvas` / `SampleCanvas`).

Patcher camera:

- Global `gDrawScale` (`SynthGlobals.h`).
- Pan: `ModuleContainer` draw offset, `ModularSynth::GetDrawOffset` / `SetDrawOffset` / `PanView` / `PanTo`.
- `ModularSynth::ZoomView(zoomAmount, fromMouse)`: scale `gDrawScale` in `[0.1, 8]`, keep zoom center (mouse or screen center) stable by adjusting offset. `SetZoomLevel` similar.
- `LocationZoomer` (`Source/LocationZoomer.h`): saved `(mZoomLevel, mOffset)` slots, home zoom from `UserPrefs.zoom`, vanity panning. Python `bespoke.location_recall` / `location_store`.
- Grid snap overlay in `ModularSynth::Draw` when `ShouldShowGridSnap()`.
- SpaceMouse optional (`SetRawSpaceMouseZoom` / `Pan` / `Twist`).
- UI chrome lives in `mUILayerModuleContainer` with its own scale (`SetUIScale`), independent of canvas zoom.
- Minimap: `Minimap`.

### DSP / drawing coupling

Yes, Draw reads live audio.

1. **Module highlight (every enabled `IAudioSource`, every frame).** `IDrawableModule::DrawFrame` `dynamic_cast<IAudioSource*>`, then RMS over `min(500, vizBuff->Size())` samples times channels from `IAudioSource::GetVizBuffer()`. `VIZ_BUFFER_SECONDS` is `0.1f`. Result drives title-bar glow (`UserPrefs.draw_module_highlights`).
2. **Background lissajous.** `ModularSynth::Draw` calls `DrawLissajous(mGlobalRecordBuffer, ...)` when `UserPrefs.draw_background_lissajous`. `mGlobalRecordBuffer` is written in `AudioOut`.
3. **Per-module viz.** Audio modules write `GetVizBuffer()->WriteChunk` in `Process`. Viewers read that (or their own copies) in `DrawModule`:
   - `AudioMeter`: `LevelMeterDisplay::Process` on audio thread, `LevelMeterDisplay::Draw` on render thread; `mLevel` slider bound to peak.
   - `WaveformViewer::Process` copies the live buffer into double-buffered `mAudioView[BUFFER_VIZ_SIZE][2]`; `DrawModule` plots it.
   - `SpectralDisplay::Process` FFTs into `mSmoother`; draw reads that.
   - `Looper`, `SlowLayers`, `ClipLauncher`, many others call `DrawAudioBuffer` on live `ChannelBuffer` / `RollingBuffer`.
4. **Note activity.** `DrawFrame` also glows from `PatchCableSource` note history vs `gTime`.
5. **Script overlay.** `ScriptModule::sBackgroundTextString` drawn in `ModularSynth::Draw`. Line-execution trackers compare `gTime`.

`RollingBuffer` (`Source/RollingBuffer.h`) has **no mutex**. Audio thread writes (`Write`/`WriteChunk`); render thread reads (`GetSample`/`Draw`). `gTime` is a global `double` written in `AudioOut`, read everywhere. `IDrawableModule::ComputeSliders` runs on the audio thread from `Process` (commented-out `mSliderMutex`: "mutex acquisition is slow").

Locks that **do** exist:

- `mAudioThreadMutex` around `AudioOut` / `AudioIn` and module spawn.
- `mRenderLock` around `Draw`.
- These are **different** mutexes. Draw does not take the audio mutex.

`MainContentComponent::audioDeviceIOCallbackWithContext` calls `AudioIn` then `AudioOut` on the JUCE audio thread (`sAudioThreadId`).

### Cost of that coupling

- Per visible audio module, every frame: up to 500-sample RMS (plus extra waveform/FFT/meter draws). Cost scales with module count on screen, not with graph size offscreen (`IDrawableModule::IsVisible` uses `mDrawRect`).
- `WaveformViewer` / `SpectralDisplay` do non-trivial DSP **inside `Process`** solely for display (FFT, window, copy). Display work is on the audio budget.
- Unsynchronized viz reads can tear; accepted as visual-only.
- Python `Poll` on the UI timer can stall the frame (and delay note dispatch) if a script is slow. Lookahead (150 ms) is the mitigation for notes, not for UI.
- `UserPrefs.motion_trails` skips `glClear` and overdraws a translucent rect, extra fill cost.
- No dirty-rect / retained layer for modules; full immediate-mode scene every frame.

---

## Tests

**None as a first-class product surface.**

- Root `CMakeLists.txt` and `Source/CMakeLists.txt`: no `enable_testing`, no `add_test`, no Catch2, no `juce_add_console_app` unit-test target, no `JUCE_UNIT_TESTS`.
- `justfile`: `build` / `configure` / `run` / `clean`. No test recipe.
- `azure-pipelines.yml`: matrix builds (macOS, Windows, Linux) plus `code-quality-pipeline-checks` (clang-format over `Source/**/*.cpp,h`). No test job.
- No `test/` / `tests/` tree outside vendored libs. Filename hits on `*test*` are modules (`NoteStepSequencer`, etc.).
- Python: no pytest. `bespoke_script_autodoc.py` is a doc generator, not a test.
- `JUCE_CATCH_UNHANDLED_EXCEPTIONS=0` is a JUCE runtime define, not Catch2.

Testability of the engine is low: `TheSynth` / `TheTransport` globals, audio-thread assumptions, embedded Python, OpenGL render path, no headless/offline bounce target.

## Determinism

Two renders of the same `.bsk` are **not** bit-identical. Evidence:

**What is sample-timestamped**

- Global time `gTime` (`Source/SynthGlobals.cpp`, starts at `1`) advances in `ModularSynth::AudioOut` by `gInvSampleRateMs * mIOBufferSize` per inner loop, i.e. by processed samples, not wall clock.
- `Transport::Advance(ms)` advances `mMeasureTime` by `ms / MsPerBar()`. Tempo from `Transport::GetTempo` (`mTempo`).
- Notes carry `NoteMessage.time` as double milliseconds. `VSTPlugin::PlayNote` converts to MIDI sample offset `(note.time - gTime) * gSampleRateMs`. Events past the current buffer go to `mFutureMidiBuffer` and are shifted by `-gBufferSize` next block.
- `NextBufferTime(includeLookahead)` = `gTime + gBufferSizeMs [+ GetEventLookaheadMs()]`.
- `Transport::sDoEventLookahead` default **false**; `sEventEarlyMs = 150`. Script note cables force it on.
- `NoteOutputQueue` drains **before** `gTime` advances in `AudioOut`.

**What is not deterministic**

- `gRandom` is `bespoke::core::Xoshiro256ss` seeded from `std::random_device`. `ofRandom` uses `gRandom01(gRandom)`.
- `Transport::Transport()` calls `SetRandomTempo()` (`gRandom() % 80 + 75`) unless save-state overwrites.
- Many musical modules use `ofRandom` (e.g. `RandomNoteGenerator`, `NoteHumanizer` path, `SingleOscillatorVoice` detune `ofRandom(-1,1)`, `NoiseEffect`). A subset has an opt-in seed via `DeterministicRandom` / `DeterministicRandomFloat01` (`NoteChance`, `NoteHocket`, `PulseChance`, `PulseHocket`, `VelocityToChance`, `NoteCounter`, `LFO` random/drunk). Python `bespoke.random(seed, index)` is the deterministic helper; bootstrap also `import random` (Python's unseeded RNG).
- Python may `import time` / block; `RunCode` sets `sMostRecentRunTime` from caller `time` (often `gTime` or a scheduled timestamp) but execution itself is UI-thread and races the audio thread.
- Ableton Link (`AbletonLink`) uses `ableton::link::HostTimeFilter` wall clock in `OnTransportAdvanced`.
- Hosted VSTs have their own state, GUI thread, and no PDC (`getLatencySamples` / `getTailLengthSeconds` / `setLatencySamples` are absent in Source).
- Audio callback jitter: internal `gTime` still steps by buffer size, but underruns, device buffer-size changes, and `UserPrefs.oversampling` (inner loop vs drop-sample downsample) change the sound. `mAudioPaused` zeros output and skips advance.
- UI-thread scheduling of script notes vs audio-thread consumption is a race; lookahead reduces late notes, it does not freeze a schedule.
- `gTime` is `double` with an in-source comment about losing nanosecond accuracy.

No offline renderer, no seed in save-state for `gRandom`, no bit-exact bounce path.

## Latency / tail APIs

No host-style latency or tail reporting:

- No `getTailLengthSeconds`, `getLatencySamples`, `setLatencySamples`, no PDC.
- `PitchShifter::GetLatencyInSamples` is an internal FFT latency used by `Looper` and `Beats` to offset read position.
- `LooperRecorder` / `TapeLooper` expose `mLatencyFixMs` sliders. `AudioSyncer` has `mLatencyMs`.
- `LatencyCalculatorSender` / `LatencyCalculatorReceiver` (`Source/LatencyCalculator.h`): user-triggered 440 Hz ping, receiver measures samples/ms/meters and **draws the number**. Not a graph-wide compensation API.
- VST `processBlock` runs at `gBufferSize` with no delay compensation for plugin reported latency.

## Key Patterns

- Compile-in module registry (`REGISTER` + `Create()` + `Accepts*()` statics), two factories (modules vs effects).
- Python as **control-rate** scripting with measure-time scheduling, not audio-rate processing.
- pybind11 embedded modules in a file still named like SWIG.
- JUCE hosts third-party plugins; Bespoke chrome is a thin module wrapper plus a JUCE `DocumentWindow` for the native editor.
- Immediate-mode nanoVG with an `of*` facade; patcher camera is `gDrawScale` + draw offset.
- Viz buffers (`RollingBuffer`, 100 ms) shared unsynchronized between audio and UI.
- Timestamped `NoteMessage` + lock-free queue from UI to audio; sample offsets only materialized at VST (and similar) boundaries.

## Dependencies (relevant)

| Dep | Role |
| --- | --- |
| JUCE (`juce_audio_processors`, `juce_opengl`, `juce_gui_basics`, `juce_osc`, devices/formats) | App, audio IO, plugin host, plugin GUI, OSC |
| pybind11 + CPython | Embedded scripting |
| nanoVG GLES2 | Immediate-mode 2D |
| readerwriterqueue | `NoteOutputQueue` |
| Ableton Link | Optional clock sync |
| jsoncpp / ofxJSONElement | Layout / save |

## Relevance to Helioy / AudioFace

- **Extension model:** Bespoke treats first-party modules as compile-in C++ and third-party DSP as industry VSTs. A C plugin ABI for custom nodes is not a pattern you can lift from here.
- **Python:** Useful as a control/sequencing layer with explicit timestamps. Unsuitable as the audio callback. `sampleplayer.fill` is the only buffer inject, and it replaces a sample, it does not stream.
- **UI:** Immediate-mode vector UI over OpenGL, module `DrawModule` each frame, live meters from DSP viz rings. Cheap to author, couples UI FPS to scene complexity, and puts some viz DSP on the audio thread (`WaveformViewer`, `SpectralDisplay`).
- **Determinism:** Even with sample timestamps, global RNG, UI-thread Python, Link, and VSTs make bit-identical reruns impossible. If AudioFace needs reproducible bounces, that has to be designed in (seeded RNG, audio-thread-only scheduling, no wall clock, plugin delay comp, offline device).

## Open Questions

- Whether any save-state path snapshots `gRandom` (not seen in the files read; `Transport` tempo is saved, the RNG engine is not obviously serialized).
- Exact `BUFFER_VIZ_SIZE` and how many modules do FFT-in-`Process` for display only (at least `SpectralDisplay`, `FilterViz`).
- Whether `Prefab` / `.pfb` is intended as a user extension format (JSON/binary grouping of compiled modules, not new DSP types).
- Historical SWIG: `.i` filename and comment style; no SWIG toolchain remains in CMake or Source.
