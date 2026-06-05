---
title: Audioface game audio middleware gaps
type: research
date: 2026-09-03
tags: [audioface, game-audio, middleware, adaptive-music, procedural-audio, web-audio, threejs]
sources:
  - https://www.audiokinetic.com/en/public-library/2024.1.7_8863/?id=concept_events.html&source=SDK
  - https://www.audiokinetic.com/library/edge/?id=controlling_property_values_using_game_parameters&source=Help
  - https://www.audiokinetic.com/en/public-library/2024.1.8_8893/?id=creating_interactive_music&source=Help
  - https://www.fmod.com/docs/2.03/studio/fmod-studio-concepts.html
  - https://www.fmod.com/docs/2.03/studio/advanced-topics.html
  - https://dev.epicgames.com/documentation/unreal-engine/metasounds-the-next-generation-sound-sources-in-unreal-engine?lang=en-US
  - https://dev.epicgames.com/documentation/unreal-engine/overview-of-quartz-in-unreal-engine?lang=en-US
  - https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html
  - https://docs.unity3d.com/cn/6000.0/Manual/AudioMixer.html
  - https://game.criware.jp/manual/adx2_tool_en/latest/criatom_tools_atomcraft_cue_setting.html
  - https://www.radgametools.com/miles.htm
  - https://elias.audio/products/elias-4/
  - https://patentimages.storage.googleapis.com/a9/f3/5f/026d0ca43dcfea/US5315057.pdf
  - https://mitpress.mit.edu/9780262014410/designing-sound/
  - https://valvesoftware.github.io/steam-audio/doc/capi/guide.html
  - https://resonance-audio.github.io/resonance-audio/develop/web/getting-started
  - https://developers.meta.com/horizon/documentation/unity/meta-xr-audio-sdk-features/
  - https://www.w3.org/TR/webaudio-1.0/
summary: Evidence based comparison of Audioface with game audio middleware, followed by a browser implementation and plugin architecture.
status: active
created: 2026-09-03
updated: 2026-09-03
project: audioface-next
confidence: high
---

# Audioface game audio middleware gaps

## Finding

Audioface is currently a deterministic procedural sound effect renderer with a careful patch contract, voice policy, and certification system. That is a useful core. A complete AAA game audio engine surrounds such a renderer with event logic, live parameters, content selection, mixing, spatial acoustics, streaming, music timing, packaging, and observability.

The current code has 38 registered controls, three sources, four layer processors, AHDSR amplitude envelopes, pitch and filter envelopes, seeded connections, a 32 voice pool, class floors, a two millisecond steal fade, listener pan, width and distance, and a master limiter. Its five certification gates cover sound presence, spectrum, stress, distinctness, and held voice leaks. The browser adapter creates an `AudioBuffer`, copies an already rendered stereo result into it, and starts an `AudioBufferSourceNode`. No live AudioNode graph participates in synthesis or mixing.

The next architectural step is therefore a real time runtime with an audio clock and a stable content model. Adding more oscillators to the current renderer would deepen one layer while leaving the larger product gap intact.

## What established systems contain

Wwise puts authored Events between game code and sound objects. Each Event holds actions such as play, stop, volume, and state changes, and SoundBanks carry those Events into the game. Game Parameters feed RTPC curves, while Switches and States choose discrete content. Random, Sequence, Blend, and Switch Containers express reusable selection behavior. Its separate Interactive Music Hierarchy adds segments, tracks, playlists, music switches, transition rules, sync points, and stingers. The profiler records voices, buses, sends, memory, streams, CPU, SoundBanks, and API calls. Virtual voices preserve playback state while removing inaudible DSP work. These are distinct systems joined by identifiers and runtime state, rather than one large sound patch. [Wwise Events](https://www.audiokinetic.com/en/public-library/2024.1.7_8863/?id=concept_events.html&source=SDK), [RTPC curves](https://www.audiokinetic.com/library/edge/?id=controlling_property_values_using_game_parameters&source=Help), [interactive music](https://www.audiokinetic.com/en/public-library/2024.1.8_8893/?id=creating_interactive_music&source=Help), [virtual voices](https://www.audiokinetic.com/en/library/edge/?id=concept_virtualvoices.html&source=SDK), and [profiling](https://www.audiokinetic.com/en/public-library/2024.1.8_8893/?id=profiling&source=Help) document the division.

FMOD Studio uses instanceable Events containing tracks, instruments, action sheets, parameter sheets, and timeline sheets. Parameters may be local or global and can drive properties, conditions, and timeline logic. Multi instruments provide shuffled, random, or sequential selection. Group buses, return buses, sends, snapshots, and effects form the mix. Banks separate runtime content for memory control. Its virtual voice system chooses real voices by priority and audibility, and its timeline callbacks report bars, beats, tempo, time signature, and markers. [FMOD Studio concepts](https://www.fmod.com/docs/2.03/studio/fmod-studio-concepts.html), [instruments](https://www.fmod.com/docs/2.03/studio/working-with-instruments.html), [mixing](https://www.fmod.com/docs/2.03/studio/mixing.html), [virtualization](https://www.fmod.com/docs/2.03/studio/advanced-topics.html), and [timeline callbacks](https://fmod.com/docs/api/content/generated/FMOD_Studio_EventInstance_Start.html) show the same broad decomposition as Wwise with a timeline centered authoring model.

Unreal splits the problem across several systems. MetaSounds are extensible, sample accurate DSP graphs for sources and reusable patches. Audio Modulation routes control values through parameter buses. Quartz schedules work against clocks, bars, beats, and quantization boundaries on the audio render thread. The Audio Mixer handles decoding, source effects, spatialization, submix graphs, and auxiliary sends. Sound Concurrency assets set count limits and resolution rules such as oldest, farthest, quietest, and lowest priority. Audio Insights and stream cache tools expose runtime cost and asset behavior. [MetaSounds](https://dev.epicgames.com/documentation/unreal-engine/metasounds-the-next-generation-sound-sources-in-unreal-engine?lang=en-US), [Audio Modulation](https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-audio-modulation-in-unreal-engine?application_version=5.2), [Quartz](https://dev.epicgames.com/documentation/unreal-engine/overview-of-quartz-in-unreal-engine?lang=en-US), [the Audio Mixer](https://dev.epicgames.com/documentation/unreal-engine/audio-mixer-overview-in-unreal-engine?lang=en-US), and [Sound Concurrency](https://dev.epicgames.com/documentation/unreal-engine/sound-concurrency-reference-guide?lang=en-US) make those ownership lines explicit.

Godot and Unity expose a smaller native stack. Godot provides positional stream players and a freely routed bus graph with ordered effects, metering, and automatic disabling of silent buses. Unity joins `AudioSource`, 3D attenuation, reverb zones, a tree of Audio Mixer groups, sends, returns, snapshots, sidechain ducking, load types, and an audio profiler. Both require game code or third party middleware for richer event and adaptive music policy. [Godot audio buses](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html), [Unity Audio Mixer](https://docs.unity3d.com/cn/6000.0/Manual/AudioMixer.html), [Unity mixer sends](https://docs.unity.cn/Documentation/Manual/AudioMixerInspectors.html), and [Unity clip load types](https://docs.unity3d.com/ja/current/ScriptReference/AudioClipLoadType.html) define their native scope.

CRI ADX uses Cues as playback units. Cue sequence types include polyphonic, sequential, shuffle, random, random without repeat, switch, combo sequence, and track transition by selector. AISAC curves map controls to sound properties. Selectors and game variables choose content. Categories handle group volume, limits, priority, and REACT ducking. ASR racks and buses own effects and sends. ACB and AWB files divide cue metadata, memory audio, and streamed audio. The profiler reports voice allocation, virtualization, streaming throughput, CPU, bus levels, and memory. Its block and selector systems support beat synchronized music changes. [Cue settings](https://game.criware.jp/manual/adx2_tool_en/latest/criatom_tools_atomcraft_cue_setting.html), [streaming](https://game.criware.jp/manual/native/adx2_en/latest/criatom_feat_streaming.html), [profiling](https://game.criware.jp/manual/native/adx2_en/latest/criatom_tools_atomcraft_profiler_item.html), and [synchronous music switching](https://game.criware.jp/manual/native/adx2_en/latest/craftv2_tips_performance_sync_change_music.html) describe that model.

Miles 10 follows the same production concerns with events, game parameters, buses, filters, spatialization, streaming, compressed runtime packs, voice limits, live editing, and a connected debugger. Its debugger records event origins, parameter values, evicted voices, data starvation, CPU, memory, bus levels, and duck state. [RAD's overview](https://www.radgametools.com/miles.htm) and [Miles Studio features](https://www.radgametools.com/msssdk.htm) are less detailed than the public Wwise and FMOD manuals, but they confirm the common architecture.

## Capability and implementation gap

Status below refers to the Audioface checkout inspected on 2026-09-03. "Worklet" means an `AudioWorkletProcessor`, usually with WebAssembly for heavier DSP. "Runtime" means TypeScript control logic scheduled against `AudioContext.currentTime` and the render frame counter.

| Capability | Audioface | Web Audio route | Browser implementation |
| --- | --- | --- | --- |
| Events and actions | Partial. Plugin events declare an id, label, class, and sustain policy. A pack maps each event to one patch. There are no action lists. | Runtime and AudioWorklet | Add an event runtime whose actions start, stop, pause, seek, set a parameter, set a state, trigger another event, or change a mix snapshot. Schedule audio actions on the audio clock. |
| Game parameters and RTPC curves | Partial. Connections read velocity, variation, or another authored or resolved parameter. They resolve once before a voice starts, except listener fields. | Native nodes and AudioWorklet | Store typed global, object, and event parameters. Curves produce control values. Use `AudioParam` automation for native nodes and control inputs for Worklets. |
| Switches and states | Absent. | Runtime | Add discrete scoped values and subscription indexes in the runtime. Resolve a switch at trigger time or react to later state changes according to authored policy. |
| Random, sequence, blend, and switch containers | Absent as reusable content objects. Seeded jitter changes values, while layers only mix together. | Runtime and native nodes | Implement deterministic selectors in the event layer. Start selected sample, patch, or nested event instances. Blends drive gains from parameter curves. |
| Sample and wavetable playback | Absent. Tone, five noise colours, and two operator FM are present. | Native nodes and AudioWorklet | Use `AudioBufferSourceNode` for resident samples, `PeriodicWave` for wavetables, and a Worklet for granular or custom resampling. |
| Seek, loop points, and cue markers | Absent. Patches have a maximum duration of 2.5 seconds. | Native nodes and AudioWorklet | Use source offsets plus `loopStart` and `loopEnd` for buffers. Keep markers and regions in asset metadata. A Worklet transport handles exact region changes and overlapping tails. |
| Real time DSP graph | Absent. Pure TypeScript renders PCM before playback. | Native nodes, AudioWorklet, and offline render | Compile plugin graphs into native AudioNodes where possible. Run custom sources and processors in Worklets. Keep the pure renderer as the reference and offline certification backend. |
| Filters, delay, dynamics, and convolution | Partial. LP, HP, BP, feedback echo, and a fixed master limiter are present. | Native nodes and AudioWorklet | Map standard filters, delay, gain, waveshaping, compression, and convolution to Web Audio nodes. Use Worklets for sidechain dynamics, lookahead limiters, multiband work, and custom feedback graphs. The Web Audio API provides modular routing and these standard nodes directly. [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) |
| LFOs, envelopes, and modulation graph | Partial. AHDSR amplitude, AD filter, pitch bend, glide, and four connection curves exist. No cyclic LFO or audio rate modulation exists. | Native nodes and AudioWorklet | Make modulators plugins with control and audio rate outputs. Native oscillators and constant sources can connect to `AudioParam`; complex modulation belongs in a Worklet. |
| Buses, submixes, and auxiliary sends | Only one master sum and limiter. | Native nodes | Build named gain nodes as a directed bus graph. Split source output to dry buses and auxiliary returns. Detect routing cycles when loading content. |
| Snapshots, ducking, sidechain, and HDR mixing | Limiting exists. Snapshots, ducking, sidechain, loudness ranges, and HDR priority mixing are absent. | Native nodes and AudioWorklet | Automate bus gains for snapshots. Implement key input duckers and HDR window logic in Worklets. Wwise HDR moves a logical loudness window so louder sounds suppress lower level content. [Wwise HDR guide](https://www.audiokinetic.com/download/documents/Wwise_HDR_UserGuide_en.pdf) |
| Attenuation curves and source cones | Partial. One fixed normalized distance curve also lowers high frequencies. There is no world unit, source orientation, cone, or author curve. | Runtime and native nodes | Use `PannerNode` distance and cone settings for a baseline, or custom gain and filter curves. Feed source orientation from threejs. |
| Occlusion, obstruction, diffraction, and transmission | Absent. | Runtime, native nodes, and AudioWorklet | Raycast in the scene, smooth results, then automate dry gain and filters. Multiple rays estimate partial obstruction. Steam Audio or a custom geometry service can add material transmission, diffraction, reflections, and pathing. [Steam Audio guide](https://valvesoftware.github.io/steam-audio/doc/capi/guide.html) |
| HRTF and point source spatialization | Absent. Current stereo is constant power pan. | Native node or AudioWorklet | `PannerNode` offers the browser's HRTF mode. Custom HRTFs require convolution or a spatial Worklet because `PannerNode` cannot load an HRTF set. |
| Ambisonics and sound fields | Absent. | AudioWorklet or Web Audio library | Decode Ambisonic channels in a Worklet or library. Resonance Audio already builds a scalable Ambisonic scene on Web Audio and accepts a threejs listener matrix. [Resonance Audio Web](https://resonance-audio.github.io/resonance-audio/develop/web/getting-started) |
| Reverb zones, rooms, and sends | Absent. The distance code explicitly has no reflection tail. | Native nodes and AudioWorklet | Crossfade auxiliary sends as emitters and listeners enter zones. Use `ConvolverNode` for impulse responses or a Worklet for algorithmic reverb. Model portals as send and filter paths. |
| Voice priority, limits, stealing, and virtualization | Partial. A 32 voice pool has floors for bed, interface, and world classes, plus deterministic same class stealing. It does not use priority, distance, measured audibility, or virtual playback. | Runtime and AudioWorklet | Separate logical instances from rendered voices. Score candidates by class, authored priority, gain, distance, and age. Advance virtual sample and music cursors without DSP, then restore a real voice at the correct position. |
| Streaming, decode, and memory budgets | Absent. Every audition buffer is resident. | Native media node and runtime | Use `MediaElementAudioSourceNode` for long streamed assets and decoded `AudioBuffer` data for short precise sounds. Add per bank memory, decode, and stream bandwidth budgets. Browser decoder choice and cache behavior remain user agent controlled. [Web Audio loading guidance](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices) |
| SoundBanks and platform packaging | Absent. Packs contain event to patch data, with no audio assets or build output. | Offline build and runtime | Build immutable content bundles containing manifests, plugin versions, graphs, event metadata, sample hashes, markers, and target encodings. Load and unload bundles by scene or feature. Service workers and HTTP caches can distribute them. |
| Profiler, capture, and live authoring | Partial. Certification is strong offline evidence, but no runtime trace exists. | Runtime, AudioWorklet, and offline render | Record event actions, parameter changes, voice decisions, graph cost, underruns, assets, bus meters, and memory. Export a deterministic replay log. Use `AnalyserNode` only for signal views, with explicit engine instrumentation for causes. |
| Output and platform control | Stereo browser playback only. | Impossible at exact native parity | Web Audio can implement the product model. Exact parity with native middleware on every platform is impossible because the browser owns device access, thread priority, decoder selection, output layout, and the built in HRTF. |

Steam Audio and Meta XR Audio show what the spatial layer can become in native integrations. Steam Audio covers custom HRTFs, Ambisonics, occlusion, transmission, reflections, reverb, and baked pathing. Meta XR Audio provides HRTF object rendering, Ambisonic playback, room acoustics, and geometry based acoustic ray tracing for occlusion, obstruction, diffraction, reflections, and reverb. Meta has placed version 85 on feature freeze, so it is a design reference rather than a durable browser dependency. Resonance Audio has the direct Web Audio implementation among these three systems. [Meta XR Audio features](https://developers.meta.com/horizon/documentation/unity/meta-xr-audio-sdk-features/), [Acoustic Ray Tracing](https://developers.meta.com/horizon/documentation/unity/meta-xr-acoustic-ray-tracing-unity-overview/), and [version 85 status](https://developers.meta.com/horizon/downloads/package/meta-xr-audio-sdk/) document the distinction.

## Adaptive music requires its own runtime

Adaptive music is a timed state machine over musical content. Horizontal resequencing chooses the next segment. Vertical layering keeps synchronized stems running and changes their gains or content. Stingers place short phrases over the score. Transition rules choose when and how the current segment may move to the next one. Quantization expresses that point as a beat, bar, phrase, marker, or custom grid.

Wwise exposes these ideas as Music Segments, Tracks, Playlist Containers, Switch Containers, transitions, and stingers. FMOD uses synchronous instruments, tempo markers, destinations, regions, and beat callbacks. Unreal Quartz schedules commands on an audio render clock and reports metronome events to gameplay. Elias adds per track state rules, musical segue points, motifs, tonal stingers, and preserved loop tails. Its arrangement is a grid of tracks and states. [Wwise music](https://www.audiokinetic.com/en/public-library/2024.1.8_8893/?id=creating_interactive_music&source=Help), [FMOD beat callbacks](https://www.fmod.com/docs/2.03/unity/examples-timeline-callbacks.html), [Quartz](https://dev.epicgames.com/documentation/unreal-engine/overview-of-quartz-in-unreal-engine?lang=en-US), and [Elias arrangements](https://elias.helpjuice.com/v4x-elias-studio-elias-assets/arrangement) provide concrete models.

iMUSE established the deeper principle in 1991. A directing system sent unpredictable game events into a music system that could branch, loop, transpose, and wait for annotated transition points while preserving musical continuity. Land and McConnell's patent describes dynamic composition driven by game events, time control, and separate MIDI, CD, and audio modules. [US Patent 5,315,057](https://patentimages.storage.googleapis.com/a9/f3/5f/026d0ca43dcfea/US5315057.pdf)

Audioface needs a `MusicClock` owned by the audio thread, with tempo maps, time signatures, transport position, lookahead scheduling, and exact conversions among frames, beats, bars, and markers. `MusicSession` should own the current segment, synchronized stems, pending transitions, stingers, and parameter state. Gameplay callbacks may arrive on the main thread, but audio changes must be queued ahead and executed by frame in the Worklet. Callback notifications to the game can be late without moving the sound.

## Procedural audio broadens the source library

Andy Farnell's approach treats sound as a process driven by physics and live input. His examples progress from the physical cause to a model and then a Pure Data patch. [MIT Press](https://mitpress.mit.edu/9780262014410/designing-sound/) Nemisindo applies that idea to live models for engines, footsteps, weather, water, wind, and action effects. GameSynth supplies focused models for whooshes, impacts, contacts, footsteps, weather, motors, particles, and modular patches. Sound Particles takes a different route: it scatters, moves, and randomizes many sound emitters in a 3D particle simulation, often as an authoring and rendering tool. [Nemisindo](https://nemisindo.com/), [GameSynth](https://tsugi-studio.com/blog/2018/03/08/gamesynth-1-0-release/), and [Sound Particles](https://soundparticles.com/products/soundparticles/overview/) define those scopes.

Audioface has good seeds for this work: deterministic randomness, frame based rendering, coloured noise, oscillator phase, envelopes, and exact offline tests. The missing source families are sample, wavetable, additive, granular, subtractive, physical model, and modal synthesis. A modal impact source can take collision impulse, material, object size, and resonant modes, then excite damped resonators. Research has demonstrated real time rigid body sound from precomputed deformation modes and physics force data. [O'Brien, Shen, and Gatchalian](https://graphics.berkeley.edu/papers/Obrien-SSR-2002-07/)

Useful product plugins follow game causes. Footsteps need gait, speed, shoe, surface, weight, and scuff. Wind needs speed, gust, turbulence, and obstruction. Fire needs intensity, fuel, crackle events, and room response. Rain needs rate, drop size, surface mix, shelter, and spatial spread. Engines need RPM, load, cylinders, intake, exhaust, and drivetrain layers. Weapons need mechanism, muzzle blast, projectile, impact, tail, and environment. Each model can mix synthesis with samples. The uniform plugin contract should allow both.

## Layered plugin architecture

The clean design preserves the deterministic renderer and places it behind a shared plugin graph contract.

1. **Core DSP.** Pure block processors, deterministic seed streams, parameter evaluation, channel layouts, frame clocks, and offline rendering. This layer has no DOM, scene, or authoring dependency.
2. **Graph runtime.** Graph compilation, native AudioNode adapters, Worklet instances, buffer ownership, latency compensation, tail retirement, and graph changes at safe frame boundaries.
3. **Event and parameter model.** Events, actions, scoped parameters, RTPC curves, switches, states, selectors, containers, instance lifetimes, and replayable command logs.
4. **Music.** Tempo maps, transport, segments, stems, playlists, transitions, stingers, quantization, and beat notifications.
5. **Spatial.** Listeners, emitters, attenuation, cones, HRTF, Ambisonics, occlusion, propagation, rooms, portals, and reverb sends.
6. **Mix.** Buses, sends, returns, snapshots, meters, dynamics, HDR policy, loudness targets, voice budgets, and virtualization.
7. **Content and tools.** Plugin discovery, patch authoring, event authoring, asset import, bank builds, validation, certification, live connection, profiler, capture, and replay.

Every source, processor, and modulator plugin should carry the same outer contract:

- Stable id, semantic version, role, supported channel layouts, and compatibility range.
- Typed audio, control, and event ports. Parameters need ids, units, legal ranges, defaults, curves, and control or audio rate support.
- A deterministic seed namespace and a declared response to reset, seek, suspend, virtualize, and restore.
- Reported latency in frames and tail length in frames. Dynamic values need query methods and change notifications.
- Serializable runtime state with an explicit schema version and migration hook.
- Resource declarations for assets, working memory, persistent memory, and expected processing cost.
- One render definition that works in blocks, plus adapters for offline TypeScript, WebAssembly Worklet, or a native AudioNode.
- A UI descriptor containing labels, groups, units, display transforms, safe ranges, meters, and custom editor capability.
- Diagnostics that identify underruns, invalid values, missing assets, unsupported layouts, and state restore failures.

Specialized interfaces can add source generation, processor input and output, or modulator rates without changing the shared lifecycle. Graph and content files refer only to plugin ids, ports, parameters, and versions. This keeps the engine open to third party plugins while making a project fully inspectable and reproducible.

## threejs integration

The integration should expose an `AudiofaceListener` bound to a camera and an `AudiofaceEmitter` bound to any `Object3D`. Each animation frame samples world transforms, converts threejs coordinates and units into the audio world, timestamps the update against the audio clock, and sends compact position, orientation, and velocity changes to the runtime. One shots retain their trigger transform. Held and moving sounds continue to read emitter state.

Occlusion uses threejs raycasts from each active listener to important emitters. A direct ray handles the common case. Additional rays around large sources estimate partial obstruction. Material tags map hits to gain and frequency loss, while attack and release smoothing prevents chatter at geometry edges. Voice priority decides how often each emitter receives the more expensive query.

Reverb zones are scene volumes with an auxiliary bus, impulse or algorithm, priority, and fade distance. The listener selects the receiving room. Emitters send to their local room and through declared portals. Outdoor zones may use sparse reflection sends or an Ambisonic ambience instead of a box room. The same scene adapter publishes game parameters such as speed, surface, biome, threat, and weather into the event and music layers.

This arrangement lets threejs describe the world while Audioface owns every audio decision. The render loop supplies timestamped facts. The audio clock, event runtime, and plugin graph decide what the player hears.

## References

- Audiokinetic, [Understanding Events](https://www.audiokinetic.com/en/public-library/2024.1.7_8863/?id=concept_events.html&source=SDK), [Game Parameter RTPCs](https://www.audiokinetic.com/library/edge/?id=controlling_property_values_using_game_parameters&source=Help), [Interactive Music](https://www.audiokinetic.com/en/public-library/2024.1.8_8893/?id=creating_interactive_music&source=Help), [Spatial Audio Rooms and Portals](https://www.audiokinetic.com/en/library/edge/?id=spatial_audio_roomsportals_apioverview.html&source=SDK), [File Packages](https://www.audiokinetic.com/en/public-library/2024.1.8_8893/?id=managing_file_packages&source=Help).
- Firelight Technologies, [FMOD Studio Concepts](https://www.fmod.com/docs/2.03/studio/fmod-studio-concepts.html), [Mixing](https://www.fmod.com/docs/2.03/studio/mixing.html), [Advanced Topics](https://www.fmod.com/docs/2.03/studio/advanced-topics.html), [Bank API](https://www.fmod.com/docs/2.03/api/studio-api-bank.html).
- Epic Games, [MetaSounds](https://dev.epicgames.com/documentation/unreal-engine/metasounds-the-next-generation-sound-sources-in-unreal-engine?lang=en-US), [Quartz](https://dev.epicgames.com/documentation/unreal-engine/overview-of-quartz-in-unreal-engine?lang=en-US), [Audio Mixer](https://dev.epicgames.com/documentation/unreal-engine/audio-mixer-overview-in-unreal-engine?lang=en-US), [Stream Caching](https://dev.epicgames.com/documentation/en-us/unreal-engine/audio-stream-caching-overview?application_version=4.27).
- Godot Engine, [Audio Buses](https://docs.godotengine.org/en/stable/tutorials/audio/audio_buses.html).
- Unity Technologies, [Audio Mixer](https://docs.unity3d.com/cn/6000.0/Manual/AudioMixer.html), [Audio Profiler](https://docs.unity3d.com/cn/6000.0/Manual/ProfilerAudio.html), [AudioClip Load Type](https://docs.unity3d.com/ja/current/ScriptReference/AudioClipLoadType.html).
- CRI Middleware, [Cue Settings](https://game.criware.jp/manual/adx2_tool_en/latest/criatom_tools_atomcraft_cue_setting.html), [Streaming](https://game.criware.jp/manual/native/adx2_en/latest/criatom_feat_streaming.html), [Profiler](https://game.criware.jp/manual/native/adx2_en/latest/criatom_tools_atomcraft_profiler_item.html).
- RAD Game Tools, [Miles Sound System](https://www.radgametools.com/miles.htm), [Miles Studio Features](https://www.radgametools.com/msssdk.htm).
- Elias Software, [Elias 4](https://elias.audio/products/elias-4/), [Arrangement](https://elias.helpjuice.com/v4x-elias-studio-elias-assets/arrangement), [Stinger](https://elias.helpjuice.com/v4x-elias-studio-elias-assets/stinger).
- Michael Land and Peter McConnell, [Method and apparatus for dynamically composing music and sound effects](https://patentimages.storage.googleapis.com/a9/f3/5f/026d0ca43dcfea/US5315057.pdf), US Patent 5,315,057, 1994.
- Andy Farnell, [Designing Sound](https://mitpress.mit.edu/9780262014410/designing-sound/), MIT Press, 2010.
- Valve, [Steam Audio Programmer's Guide](https://valvesoftware.github.io/steam-audio/doc/capi/guide.html).
- Google, [Resonance Audio SDK for Web](https://resonance-audio.github.io/resonance-audio/develop/web/getting-started).
- Meta, [Meta XR Audio SDK Features](https://developers.meta.com/horizon/documentation/unity/meta-xr-audio-sdk-features/), [Acoustic Ray Tracing](https://developers.meta.com/horizon/documentation/unity/meta-xr-acoustic-ray-tracing-unity-overview/).
- W3C, [Web Audio API](https://www.w3.org/TR/webaudio-1.0/).
