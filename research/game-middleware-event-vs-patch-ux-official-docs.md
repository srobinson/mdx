---
title: Game middleware event vs patch UX from official Unreal Wwise FMOD docs
type: research
tags: [game-audio, wwise, fmod, metasounds, three.js, ux, spatialization, profiler]
summary: Official Unreal MetaSounds, Wwise, and FMOD Studio UIs all split a posted 3D event from an internal synth or graph patch; FMOD's event 3D preview is the piece a browser three.js tool should copy first.
status: active
confidence: high
created: 2026-09-03
updated: 2026-09-03
project: audioface
related: [audioface-ui-direction]
---

# Game middleware event vs patch UX

Canonical working copy of this note (product headings, transfer section, user-specified frontmatter): [`/Users/alphab/.mdx/TMP/pstack/audioface-ui-direction/game-audio.md`](/Users/alphab/.mdx/TMP/pstack/audioface-ui-direction/game-audio.md).

## Executive Summary

Wwise, FMOD Studio, and Unreal MetaSounds all treat a **posted 3D event** as a different object from a **synth or DSP patch**. 3D attenuation, voice limits, and banks hang on the event. Graphs, instruments, and source plug-ins hang on the patch. None of the three ships a platform-certification mix report. They ship ITU or EBU loudness meters plus voice-limit settings. A browser three.js sound tool should copy FMOD's in-editor emitter gizmo, Wwise's RTPC curve tab, Unreal's Source vs Patch split, and a master BS.1770 meter.

## Detailed Findings

### Object models

**Unreal MetaSounds.** Two graph assets: **MetaSound Source** (plays on AudioComponent / Spawn Sound / AmbientSound) and **MetaSound Patch** (referenced only). Presets inherit a read-only graph and override inputs. ([Epic MetaSounds Reference](https://dev.epicgames.com/documentation/en-us/unreal-engine/metasounds-reference-guide-in-unreal-engine))

**Wwise.** The game posts **Events** (action lists: Play, Stop, Set RTPC, Set State). Designed content lives in the Actor-Mixer Hierarchy. Runtime payload is a **SoundBank**. Sound objects are not in the SDK. ([Creating Events](https://www.audiokinetic.com/library/2025.1.3_9037/?source=Help&id=creating_events); [The Wwise Approach](https://www.audiokinetic.com/download/documents/TheWwiseApproach.pdf))

**FMOD Studio.** The game plays **events** (tracks + instruments + parameters). **Banks** hold metadata and samples. A **master bank** holds the mixer and must stay loaded. Nested events are hidden from mixer and API. Unassigned events tag `#unassigned`. ([Authoring Events](https://www.fmod.com/docs/2.02/studio/authoring-events.html); [Banks](https://www.fmod.com/resources/documentation-studio?version=2.0&page=getting-events-into-your-game.html))

### Authoring layers vs graphs

MetaSounds is a DSP **flow graph** (not Blueprint execution). Live play pulses trigger wires and thickens audio wires. Pages swap graphs per platform. ([MetaSounds Reference](https://dev.epicgames.com/documentation/en-us/unreal-engine/metasounds-reference-guide-in-unreal-engine); [MetaSound Pages](https://dev.epicgames.com/documentation/unreal-engine/metasound-pages-in-unreal-engine))

Wwise layers via containers (Random, Sequence, Switch, Blend). Source plug-ins such as **Synth One** sit on a Sound via Add Source / Source Editor. The Event Editor is an action table. ([Event Editor](https://www.audiokinetic.com/library/?source=Help&id=event_editor); [Synth One](https://www.audiokinetic.com/library/2023.1.0_8367/?source=Help&id=creating_midi_instruments))

FMOD is DAW-like: **action sheets** (concurrent/consecutive playlists) and **parameter sheets** (instrument trigger regions). Instruments include single, multi, scatterer, event, programmer, command, snapshot, plug-in. ([Authoring Events](https://www.fmod.com/docs/2.02/studio/authoring-events.html))

### RTPC / game-parameter curves

Wwise: **RTPC tab** on Property, Attenuation, and Effect Editors. X = Game Parameter or built-in Distance. Y = volume, pitch, LPF, HPF. Control points, multi-curve compare. Runtime `SetRTPCValue`; out-of-range clamps to endpoints. ([RTPC tab](https://www.audiokinetic.com/library/2024.1.7_8863/?source=Help&id=rtpc_tab))

FMOD: transport **number boxes**; **Add Curve** on an automation widget. Built-in Distance / Direction / Elevation / Speed update from 3D preview. ([Parameters](https://www.fmod.com/docs/studio/parameters.html); [Parameters Reference](https://www.fmod.com/docs/2.03/studio/parameters-reference.html))

Unreal: no XY RTPC tab. Graph Inputs + editor Slider/Knob widgets; Blueprint `SetParameter`. Distance arrives via `UE.Attenuation` interface. ([MetaSounds Reference](https://dev.epicgames.com/documentation/en-us/unreal-engine/metasounds-reference-guide-in-unreal-engine); [Sliders and Knobs](https://dev.epicgames.com/community/learning/tutorials/587X/unreal-engine-using-metasound-sliders-and-knobs))

### Attenuation and 3D preview

Wwise Attenuation Editor: distance on X, locked radius-center point, max distance, curves for volume/LPF/HPF/spread, cone, ShareSets. Transport is 2D because emitter equals listener. **Game Object 3D Viewer** (F12) is the live 3D view when connected to a game. ([Attenuation Editor](https://www.audiokinetic.com/library/2025.1.3_9037?id=positioning_attenuation_editor&source=Help); [Positioning tab](https://www.audiokinetic.com/library/2024.1.7_8863/?source=Help&id=positioning_tab); [Game Object 3D Viewer](https://audiokinetic.com/library/2025.1.3_9039/?source=Help&id=game_object_profiler_game_object_3d_viewer))

FMOD: spatializer on the event (3D templates include it). Overview **3D preview**: listener at center, emitter arrow, max-distance radius, elevation via Ctrl-drag. **Sandbox** for many emitters. ([Authoring Events 4.3.2](https://www.fmod.com/docs/2.02/studio/authoring-events.html); [The Sandbox](https://www.fmod.com/docs/studio/the-sandbox.html); [FMODTV Building Blocks: Events](https://www.youtube.com/watch?v=gQFZ4HhoT4A))

Unreal: **Sound Attenuation** asset on the Source (shape + function + panning/binaural). Graph may consume Distance/Azimuth/Elevation. Editor Play has **no** emitter gizmo; 3D is PIE / AmbientSound. ([Quick Start](https://docs.unrealengine.com/5.3/en-US/metasounds-quick-start/); [Sound Attenuation](https://dev.epicgames.com/documentation/en-us/unreal-engine/sound-attenuation))

### Profiler and mix meters

Wwise Voice Inspector: Voice Graph + Contribution List of volume drivers (RTPC, State, attenuation rays, occlusion). Profiler F6 / Voice Profiler F11. Loudness Meter: EBU R128 / ITU-R BS.1770-4. Playback Limit and platform Max Voice Instances. No cert PDF. Device capture still used for console (PS5 Sulpha). ([Voice Inspector](https://www.audiokinetic.com/library/2025.1.3_9037/?source=Help&id=analyzing_voices_voice_inspector); [Loudness Meter](https://www.audiokinetic.com/library/edge/?source=Help&id=loudness_meter); [Mastering a Game with Wwise](https://www.audiokinetic.com/en/mastering-a-game-with-wwise-part1))

FMOD Profiler: CPU, memory, peak/RMS levels, voices (real/virtual), instance lifespans, 3D instance plot. Optional EBU R-128 Loudness Meter effect. Event max instances. ([Profiling](https://www.fmod.com/docs/2.02/studio/profiling.html); [Mixing](https://www.fmod.com/docs/studio/mixing.html))

Unreal Audio Insights: live sources, virtual loops, submixes, ITU-R BS.1770 Loudness Meters on the **final mix** (Momentary 400 ms, Short Term 3 s, Integrated up to 60 min, true peak, target). Sound Concurrency for voice limits. ([Audio Insights](https://dev.epicgames.com/documentation/en-us/unreal-engine/audio-insights-in-unreal-engine); [Analyzers](https://dev.epicgames.com/documentation/en-us/unreal-engine/analyzers-and-output-metering-in-audio-insights-in-unreal-engine); [Sound Concurrency](https://docs.unrealengine.com/5.3/en-US/sound-concurrency-reference-guide/))

### Event vs synth patch

Posted in the scene: Wwise Event, FMOD Event, MetaSound Source. Designed internally: Actor-Mixer + Synth One, FMOD instruments/nested events, MetaSound Patch. Distance/azimuth enter as parameters; the engine panner stays outside the patch.

## Sources Consulted

### Official docs
- Epic: MetaSounds Reference, Pages, Quick Start, Sound Attenuation, Audio Insights, Analyzers, Sound Concurrency
- Audiokinetic: Creating Events, Event Editor, RTPC tab, Attenuation Editor, Positioning, Voice Inspector, SoundBank Manager, Loudness Meter, Wwise Approach PDF
- Firelight: Authoring Events 2.02, Profiling, Sandbox, Mixing, Parameters, Effect Reference (Spatializer)

### Official videos
- [FMODTV Building Blocks: Events](https://www.youtube.com/watch?v=gQFZ4HhoT4A)
- [Wwise Events and Property Editor](https://www.youtube.com/watch?v=P77ao8Ycp9Y)
- [Audio Insights Unreal Fest](https://www.youtube.com/watch?v=o96Ot2UP2xE)
- [GDC 2024 Troubleshooting with Wwise](https://www.youtube.com/watch?v=52WNmIEnvVM)
- [Wwise-101 Integrating a Sound](https://www.youtube.com/watch?v=1EhEhDyZ6o4)

### UI image URLs
- https://d1iv7db44yhgxn.cloudfront.net/documentation/images/21425d5c-4bc3-4db6-b8e2-7debb1ae3f4b/connections.gif
- https://d1iv7db44yhgxn.cloudfront.net/documentation/images/912145d1-1b30-46b7-9d97-5f63e7d00e1d/input_widgets.png
- https://dev.epicgames.com/community/api/documentation/image/a82a433b-691c-44ea-a4a3-2d04da37ea29
- https://dev.epicgames.com/community/api/documentation/image/ef15a779-6369-4f34-b324-f5ca506909a6

## Source Quality Assessment

High. Claims above are from Epic, Audiokinetic, and Firelight docs or official videos. Gaps: Audiokinetic Help is often captcha-gated to fetchers, so Wwise UI screenshots were taken from official YouTube rather than Help CDN frames. FMOD docs embed screenshots but some 2.03 URLs returned empty to fetchers; 2.02 Authoring Events and Profiling fetched cleanly. No vendor documents a one-click platform-certification report; that absence is documented, not inferred from silence about an unnamed feature.

## Open Questions

- Does Unreal plan an in-MetaSound-Editor 3D emitter gizmo, or will Audio Insights remain the spatial debugger?
- FMOD Loudness Meter target range and API exposure still look authoring-only; confirm current Studio version UI against 2.02 docs.
- Wwise auto-defined SoundBanks change the Add-tab workflow; a three.js pack model should pick user-defined vs auto-defined explicitly.

## Actionable Takeaways

For a browser three.js sound engine: two objects (Event + Patch); FMOD-style 3D preview on the Event; shareable attenuation curves; transport parameter boxes plus RTPC curves; live voice/contribution profiler; BS.1770 master meter; explicit load packs; event sheets in front, synth graph behind a patch tab. Full transfer list lives in the TMP working copy.
