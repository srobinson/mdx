---
title: Audioface UI direction
type: research
date: 2026-09-03
created: 2026-09-03
updated: 2026-09-03
tags:
  - audioface
  - ui
  - sound-design
  - web-audio
  - game-audio
summary: Interface and interaction direction for a browser based professional sound design tool built on layers and plugins, with cited evidence from synths, DAWs, game middleware, web renderers, and hardware.
status: active
project: audioface
confidence: high
sources:
  - https://kilohearts.com/docs/phase_plant
  - https://monosounds.studio/serum-2-modulation-guide/
  - https://davidmvogel.com/docs/Vital/UserGuide/Modulation
  - https://native-instruments.com/ni-tech-manuals/massive-x-manual/en/modulation
  - https://docs.reasonstudios.com/rackplugin13/europa-shapeshifting-synthesizer
  - https://bitwig.com/the-grid/
  - https://www.ableton.com/en/manual/instrument-drum-and-effect-racks
  - https://docs.unrealengine.com/documentation/en-us/unreal-engine/metasounds-reference-guide-in-unreal-engine
  - https://www.audiokinetic.com/library/2025.1.3_9037/?source=Help&id=analyzing_voices_voice_inspector
  - https://www.fmod.com/docs/2.03/studio/parameters-reference.html
  - https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas
  - https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Visualizations_with_Web_Audio_API
  - https://blog.cables.gl/release-august-2021/
---

# Audioface UI direction

Research for a browser sound engine aimed at three.js games. The product goal is a visually dense, layer and plugin oriented professional tool that exposes Web Audio capability for sound effects and scores. The current engine is a deterministic offline renderer: layers of source, filters, envelope, echo, a voice pool, listener pan/width/distance, a master limiter, about forty parameters, a modulation connection list, and certification gates. The current UI is a bench of details blocks and range inputs. This note is about interface direction. It does not copy any named product.

## Design thesis

A professional sound tool is a machine you look at while you listen. Serum, Vital, Pigments, Phase Plant, and Massive X treat the picture of the signal as the primary control, and knobs as handles on that picture. Drag a modulator onto a parameter, a ring appears, the ring moves with the sound. That is the interaction that made wavetable synths teachable. Reason's rack and Phase Plant's snapin lanes show the other half: structure is a stack of devices you add, reorder, and bypass. Game middleware adds a third surface. In Wwise and FMOD the designed object is an event that plays in a room, with RTPC curves, attenuation, a 3D preview, and a voice inspector that explains why a voice is quiet. Audioface should be a rack of plugins that lives inside a scene. The daily view is layers and inserts with live scopes. The specialist view is a graph. The game view is the emitter in three.js plus the gate report. Forty range inputs cannot carry that. Signal flow, modulation, and spatial behavior have to be visible at sixty frames per second, while the controls stay keyboardable, MIDI learnable, and present in the DOM so screen readers can see them.

## Interface concepts

### Chassis

Take the Reason rack and Phase Plant's snapin lanes as the structural model. Phase Plant splits one window into generators on the left, effect lanes on the right, and modulators along the bottom. You add a module by clicking a dashed empty slot. Lanes mute, solo, mix, and send. Polyphonic processing is a property of a lane. Reason's rack plugin does the same at device scale: add a device to a slot, flip the rack with Tab to see CV and audio cables. FL Studio Patcher is the graph version of the same idea, with yellow audio cords and blue event cords, plus a Surface tab that exposes only the controls you mapped.

Audioface's layer should look like a chassis. The source is a plugin at the top. Filters, envelope, echo, and any future insert occupy slots below. Empty slots invite a plugin. Drag to reorder. Bypass is a hardware style LED. The forty parameters of the current engine disappear into the plugins that own them. Screenshot reference: [Phase Plant UI overview](https://kilohearts.com/docs/phase_plant) and the Reason rack plugin walkthrough at [reasonstudios.com](https://www.reasonstudios.com/news/post/reason-rack-plugin-in-any-daw). Video: [Phase Plant GUI tour](https://www.youtube.com/watch?v=CDGMmTomGko).

### Drop rings

Serum 2 still starts modulation with a drag. Grab the handle beside LFO 1, drop it on filter cutoff, a ring appears around the knob, pull the ring for depth. Every connection also lands in a matrix for bipolar/unipolar, curve, and aux scaling. Vital lights every legal target while you drag, then paints small colored dials at both source and destination. Massive X calls the same overlay Saturn rings: color coded rings or lines next to a control show source type and amount, two slots under each control. Pigments 6 added hover pie charts for every assigned modulator and lets you drag a source onto a pie to sidechain one modulator with another.

This is the modulation language Audioface should speak. The current modulation connection list is the matrix. The missing piece is the overlay on the control. Do not invent a new cable grammar for ordinary control rate routing. Drag, ring, matrix. Keep cables for audio rate and for the specialist graph. Sources: [Serum 2 modulation](https://monosounds.studio/serum-2-modulation-guide/), [Vital modulation](https://davidmvogel.com/docs/Vital/UserGuide/Modulation), [Massive X modulation](https://native-instruments.com/ni-tech-manuals/massive-x-manual/en/modulation), [Pigments 6 review](https://musictech.com/reviews/software-instruments/arturia-pigments-6-review/). Video: [Serum 2, drag any source](https://www.youtube.com/watch?v=X5t8WIFDOqY), [Massive X walkthrough](https://www.youtube.com/watch?v=T4mfM73egsQ).

### Engine bay

Europa's three engines are selected by LED radio buttons. The waveform display is a control: drag it to change Shape. Pigments puts two engines side by side with live harmonic and filter visuals, plus a Play view for performance. Vital keeps an oscilloscope or spectrum on the Voice tab. Phase Plant draws every generator's output on the module, same path as the sound, at a fixed frequency so the picture stays readable.

Audioface sources should be bays. A noise source shows noise. A sample source shows the sample and loop points. A wavetable source shows frames. The envelope is a drawable curve. The echo is a time picture. If a parameter cannot be seen on its plugin face, it belongs in another plugin. Sources: [Europa operation manual](https://docs.reasonstudios.com/rackplugin13/europa-shapeshifting-synthesizer), [Pigments 6](https://www.kvraudio.com/news/arturia-releases-pigments-6---free-update-62802), Phase Plant generator scopes as cited above. Video: [Pigments 6 deep dive](https://www.youtube.com/watch?v=SZfg6S5NM6o).

### Two surfaces

Bitwig Grid is modular sound design inside a device: 200 plus modules, in ports left, out ports right, inspector scopes on every connected port. MetaSounds is a typed flow graph. You can promote a value to a graph input and draw it as a knob on the graph. FL Patcher and Max/MSP sit here too. Max uses gray cords for control, yellow-black stripes for audio, green for Jitter.

The trap is making the graph the home screen. Bitwig still ships Polymer and device chains. Phase Plant keeps structure on one page. Audioface should default to the chassis. Open a graph for audio between layers, sidechain, or the compiled Web Audio graph. Sources: [The Grid](https://bitwig.com/the-grid/), [Bitwig Grid editor](https://www.bitwig.com/userguide/latest/welcome_to_the_grid), [MetaSounds reference](https://docs.unrealengine.com/documentation/en-us/unreal-engine/metasounds-reference-guide-in-unreal-engine), [Max patch cords](https://docs.cycling74.com/max8/vignettes/patch_cords). Video: [Getting around in The Grid](https://www.bitwig.com/learnings/getting-around-in-the-grid-39/).

### Event in the room

The load bearing split is posted-in-scene versus designed-internally. FMOD's playable is an event. A 3D event has a spatializer and a 3D preview (listener center, emitter arrow, max-distance radius, elevation). Built in Distance parameters follow that gizmo. The Sandbox auditions many emitters before the game exists. Wwise's game API is Events (Play, Stop, Set RTPC). Designed content lives in the Actor-Mixer. Wwise Transport is 2D. Live 3D is the Game Object 3D Viewer (F12). Attenuation curves are ShareSets. MetaSound Source plays. Patch is reuse only. Spatialization is a Sound Attenuation asset on the Source, not a graph node. MetaSound Editor Play has no 3D gizmo.

Audioface already has listener pan, width, and distance. Put the FMOD-style gizmo on the Sound. Put attenuation on the Sound as a shareable asset. Keep the chassis and graph off the game API. Bind game parameters as RTPC curves. When a gate fails because a voice was stolen or a limiter slammed, a Voice Inspector contribution list is how you find out why. Sources: [FMOD authoring events](https://www.fmod.com/docs/2.02/studio/authoring-events.html), [FMOD sandbox](https://www.fmod.com/docs/studio/the-sandbox.html), [Wwise creating events](https://www.audiokinetic.com/library/2025.1.3_9037/?source=Help&id=creating_events), [Wwise 3D Viewer](https://audiokinetic.com/library/2025.1.3_9039/?source=Help&id=game_object_profiler_game_object_3d_viewer), [Wwise Voice Inspector](https://www.audiokinetic.com/library/2025.1.3_9037/?source=Help&id=analyzing_voices_voice_inspector), [MetaSounds reference](https://dev.epicgames.com/documentation/en-us/unreal-engine/metasounds-reference-guide-in-unreal-engine).

### Gate dock

Wwise and Unreal Audio Insights meter loudness on EBU R128 / ITU-R BS.1770 (momentary, short term, integrated). FMOD's profiler shows CPU, peak/RMS, real versus virtual voices, and a 3D instance plot. Voice limits are Sound Concurrency, Playback Limit, or event max instances. None of these tools ship a pass/fail certification report as an editor.

Audioface already has certification gates. That report is a product gap. Each gate is a row with a verdict, a measured value, a threshold, and a deep link into the chassis or the voice inspector. Loudness, peak, voice count, limiter gain reduction, missing modulation, silent layer. Click a failed gate and the UI focuses the plugin that caused it. Sources: [Wwise Loudness Meter](https://www.audiokinetic.com/library/edge/?source=Help&id=loudness_meter), [Unreal Audio Insights metering](https://dev.epicgames.com/documentation/en-us/unreal-engine/analyzers-and-output-metering-in-audio-insights-in-unreal-engine), [FMOD profiling](https://www.fmod.com/docs/2.02/studio/profiling.html).

### Face macros

Macro counts cluster: four (Vital, Pigments, Arcade, Serum), eight (Phase Plant, Ableton default), sixteen (Ableton max, Massive X). Reason Combinator and FL Patcher's Control Surface are custom panels. Ableton Map mode highlights mappable parameters. Macro variations store snapshots. Output Arcade hides the engine behind kits, black-key modifiers, and Tweak.

The Audioface sound should have a face. Eight macros, named by the designer, MIDI learnable, visible when the chassis is collapsed. The face is what a game designer or a three.js coder touches. The chassis is what the sound designer touches. Sources: [Ableton racks manual](https://www.ableton.com/en/manual/instrument-drum-and-effect-racks), Phase Plant macros as cited, [Massive X control](https://www.native-instruments.com/en/massive-x-quickstart/playing-and-controlling-massive-x/). Video: [Ableton racks explained](https://www.youtube.com/watch?v=oWuc79ljuoE).

### Signal chroma

Cord appearance is data rate. Max/MSP/Jitter paint control, audio, and matrix. User color is annotation only. Pure Data uses thickness and rejects illegal connects. cables.gl colors the port by type, inserts an op on a cable, and animates flow. nodes.io draws triggers solid and parameters dotted. TouchDesigner paints operator family and puts a viewer on every node. MetaSounds use circle pins for scalars, blocks for arrays, and a Trigger type. Phase Plant paints audio rate green, control orange, modulation of modulation yellow. Massive X rides the source color on the destination ring. MIDI learn is a purple overlay.

Pick a small, stable palette and never reuse it for decoration.

- Audio: one warm hue
- Control rate modulation: one cool hue
- Audio rate / FM: a third, high chroma hue
- Trigger / gate / note: a fourth
- Certification fail: a reserved error hue, kept apart from audio

Typography should be tabular for values, a condensed sans for labels, and a mono cut for graph port names. u-he's Zebra proves a dense rack can stay readable if module panels share one grid and one type ramp. Teenage Engineering's OP-1 assigns color to function (synth, tape, mixer, FX) and keeps four encoders mapped to whatever the current screen is. On the OP-Z the encoder color matches the graphic. Four knobs always meaning the current page is more useful than drawing plastic knobs. Ableton's MIDI Map mode paints the whole UI: a fader is a track. Sources: [Max patch cords](https://docs.cycling74.com/userguide/patch_cords/), [cables.gl ports](https://cables.gl/docs/5_writing_ops/dev_creating_ports/dev_creating_ports), [nodes.io manual](https://nodes.io/docs/manual/), [TouchDesigner intro](https://derivative.ca/UserGuide/Intro_to_TouchDesigner), [OP-Z interface](https://teenage.engineering/guides/op-z/interface-overview), [Ableton MIDI mapping](https://www.ableton.com/en/manual/midi-and-key-remote-control/).

### Eight up

Elektron Digitakt (and Digitakt II) puts track editing on five parameter pages: TRIG, SRC, FLTR, AMP, LFO. Eight data entry encoders always control the eight visible parameters. Parameter locks invert the value graphics on a step. The hardware never shows forty knobs. Teenage Engineering does the same with four colored encoders and a 60 fps OLED.

Audioface plugins should paginate. A filter plugin shows cutoff, resonance, type, drive on page one, and key track, envelope amount, slope on page two. MIDI learn binds the eight visible controls. This is how a dense engine stays performable without a wall of ranges. Source: Digitakt user manual panel layout (parameter keys SRC, FLTR, AMP, LFO, data entry knobs A to H), [OP-1 field 60 fps display](https://teenage.engineering/products/op-1/original/modules).

### Kit well

Arcade's primary surface is a browser of lines, kits, and loops, then a two octave keyboard of loops and modifiers. Spitfire puts mic positions on a mixer face with articulation switchers. Pigments, Phase Plant, and Serum 2 treat the preset browser as a full panel, with undo beside it.

Audioface needs a well: tagged presets, undo/redo at the sound level, and a way to preview without destroying the current edit. Dedicated A/B patch pairs are not documented in the manuals surveyed. Serum 2, Phase Plant, and u-he expose undo/redo, and u-he's Diva browser has Restore. Treat undo plus a preview slot as the compare tool. The well is also where certification badges live. A preset that fails a gate should show the badge in the list. Sources: [Arcade walkthrough](https://www.youtube.com/watch?v=gSpDqkikaKg), [Spitfire SSO mics](https://support.spitfireaudio.com/en/articles/11815958-approaching-microphone-mixes-in-the-sso), [Serum 2 undo](https://xferrecords.com/web-manual/serum-2/undo-and-redo), Phase Plant Browse and Undo as cited.

## Information architecture

These are the nouns. Keep them stable across UI, renderer, and three.js bindings.

**Scene.** A three.js world with one listener and many emitters. Owns listener orientation, a preview camera, and the currently auditioned sound. This is FMOD's sandbox scaled down. The sound lives elsewhere.

**Sound.** The playable. Closest to a Wwise Event, an FMOD event, or a MetaSound Source. This is what the game posts. It owns transform, an attenuation asset, RTPC bindings, voice limits, macros, buses, layers, and the certification report. Internals (layers, plugins, graph) stay off the game API, like a MetaSound Patch.

**Layer.** One voice path. Closest to a Phase Plant generator group plus its output. Has a source plugin, an insert rack, mix/pan/send, mute/solo, and a voice allocation share of the pool. Layers mix. They do not nest infinitely. If you need a submix, you send to a bus.

**Plugin.** A named device with a type (source, filter, envelope, delay, spatial, meter, limiter), a parameter schema, a visualization contract, and a list of modulation destinations. The current source/filter/envelope/echo split is four plugins, not four sections of one form.

**Rack.** The ordered insert list on a layer, with optional parallel lanes. Phase Plant's three snapin lanes are the model: serial inside a lane, send between lanes, poly as a lane flag. A rack is an insert list, separate from the mixer's bus strip.

**Bus.** A mix destination with its own insert rack. Master limiter lives on the master bus. Sidechain and echo sends land here.

**Modulation.** A connection from a source (envelope, LFO, macro, RTPC, audio) to a destination parameter, with amount, polarity, and curve. Visible as a ring on the control and as a row in the matrix.

**Macro.** A named face control. One macro may drive many destinations.

**RTPC.** A game parameter with a curve, identical in kind to Wwise RTPC or FMOD parameters. Distance and cone are built in RTPCs derived from the scene.

**Attenuation.** A shareable curve set (distance, cone, occlusion) applied at the emitter, not per layer.

**Gate report.** The certification document for a sound. First class, clickable, stored with the preset.

**Voice.** A runtime instance. The inspector shows why it sounds the way it does.

Do not collapse Sound and Scene. Do not collapse Plugin and Parameter. Do not show the voice pool as a setting buried in a details block. It is a scene resource with a meter.

## Tech stack for the UI layer

Render the chrome in the DOM. Render the pictures on a canvas. Keep three.js inside the scene pane.

**DOM and CSS for structure.** Knobs, racks, trees, browsers, and the gate dock must be real elements. Cables.gl's own accessibility writeup is blunt: GPU pixels are not buttons. They overlay HTML on the canvas when they need a control to be readable by assistive tech. Use `role="slider"` with arrow keys, Home/End, and `aria-valuenow`, with a visually hidden native range as the accessible twin. Steal MIDI learn and sprite knobs from older kits if useful. Do not adopt NexusUI or stock webaudio-controls as the design system. Cutoff's AudioUI is a closer starting kit (knob, slider, cycle button). Sources: [cables.gl accessible UI](https://github.com/cables-gl/cables_docs/discussions/934), [ARIA slider](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/slider_role), [Cutoff AudioUI](https://github.com/cutoff/audio-ui), [NexusUI](https://nexus-js.github.io/ui/).

**Live audio path for pictures.** A professional live meter cannot share the main thread with pointer handling. Chrome's AudioWorklet design pattern plus WASM DSP, with SharedArrayBuffer ring buffers into the visualizer, is the documented split. AnalyserNode remains the cheap fallback. Keep the current offline renderer as the bounce of record. Certify that the live graph matches it, or drive scopes from the bounce buffer. Sources: [AudioWorklet design pattern](https://developer.chrome.com/blog/audio-worklet-design-pattern), [Web Audio on the web, ACM 2023](https://dl.acm.org/doi/fullHtml/10.1145/3543873.3587987).

**OffscreenCanvas plus WebGL 2 for meters, spectrograms, wavetables, and modulation overlays.** `HTMLCanvasElement.transferControlToOffscreen()` moves drawing to a worker. PixiJS v8 on WebGL 2 is the practical batcher for scrolling spectrograms, polar wavetable views, and the moving arcs on Drop rings. Canvas 2D is enough for a handful of small scopes. cables.gl rebuilt its patch editor from SVG to a full WebGL 60 fps editor because large graphs made SVG fall over. Use a DOM graph library (xyflow) only while the graph is sparse. Chromatone and calebj0seph/spectro do FFT on the CPU then a GPU fragment shader for color and scroll. That split holds until WebGPU is a given. Sources: [OffscreenCanvas](https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas), [PixiJS v8](https://pixijs.com/blog/pixi-v8-beta), [cables.gl August 2021](https://blog.cables.gl/release-august-2021/), [spectro](https://github.com/calebj0seph/spectro).

**three.js only for the scene.** The product is a sound engine for three.js games. The 3D preview is a first class pane, like FMOD's 3D preview and sandbox. Draw knobs in the DOM. Keep the scene in its own pane. Coplanar HTML over a canvas is a known pain.

**WebGPU as a progressive compute path.** MDN documents compute pipelines. Hugging Face now ships in-browser WGSL kernels. GPU FFT is real. WebGPU is still a capability check (`"gpu" in navigator`). Use it to replace the CPU FFT behind the spectrogram when present. Do not block the UI on it. Sources: [MDN WebGPU](https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API), [huggingface kernels](https://huggingface.co/blog/webgpu-kernels).

**CSS Houdini stays optional.** Paint, Animation Worklet, and Layout can draw a knob background from custom properties. Support is uneven. Hit testing and accessibility stay in the DOM. Use CSS variables for the signal chroma theme. Draw the interactive knob in DOM or on the WebGL overlay. Source: [CSS Paint API](https://drafts.css-houdini.org/css-paint-api-1/), [caniuse Paint API](https://caniuse.com/css-paint-api).

**MIDI and reduced motion.** `navigator.requestMIDIAccess()` is the learn path for Face macros and Eight up. Honor `prefers-reduced-motion: reduce` by freezing modulation overlays and spectrogram scroll, and by showing a numeric readout and a static ring. The picture of the sound is information, so keep a still. Sources: [Web MIDI](https://developer.mozilla.org/en-US/docs/Web/API/Web_MIDI_API), [prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion).

Audiotool already ships devices, cables, a sequencer, and MIDI in Chrome and Firefox. cables.gl ships a 60 fps WebGL patcher. Soundtrap and Endlesss prove layered loop UIs can live on the web. Audioface should look like Phase Plant inside Audiotool's desktop, with a Wwise inspector docked.

Ranked stack:

| Layer | Choice | Evidence | Risk |
| --- | --- | --- | --- |
| Chrome, racks, knobs, browser | DOM + ARIA slider + hidden native range | cables.gl a11y, ARIA slider, Cutoff AudioUI | Easy to slip back into visible range inputs |
| Live audition DSP | AudioWorklet + WASM + SAB rings | Chrome AudioWorklet pattern, ACM 2023 | COOP/COEP headers for SAB |
| Meters, spectrograms, mod rings | OffscreenCanvas + PixiJS v8 WebGL 2 | Pixi v8, spectro, cables.gl editor | GPU contention with three.js |
| Sparse routing graph | xyflow (DOM) until it janks | cables.gl SVG failure | Must swap to WebGL if patches grow |
| Scene preview | three.js, own pane | FMOD 3D preview / sandbox | No HUD knobs on the scene |
| Heavy FFT | WebGPU compute when available | MDN compute, caniuse WebGPU | Capability gated |
| Control | Web MIDI + keyboard | MDN Web MIDI, ARIA keys | Safari MIDI gaps |
| Reject | Houdini as core, NexusUI as skin, three.js HUD | caniuse Paint, NexusUI, CSS2DRenderer | Looks like a toy or a game menu |

## Risks

**Pretty ranges.** The failure mode is restyling the current details/summary bench as dark knobs and calling it Serum. If adding a filter still means opening a list of ranges, Chassis has not landed.

**Graph as home.** MetaSounds and Bitwig Grid are powerful and slow to learn. A game sound (gunshot, footstep, sting) is a layer stack. Default to Chassis. Open the graph on demand.

**Two GPUs fighting.** three.js in the scene pane plus a WebGL spectrogram plus a worker canvas will stall a laptop if they share one context badly or if rAF work mutates React state every frame. Keep feature arrays allocated once. Do not setState on the analyser.

**Offline renderer versus live picture.** Phase Plant's scopes cheat: fixed frequency, same path. Audioface's renderer is deterministic and offline. A live AnalyserNode on a different graph will lie. Drive scopes from the bounce buffer, or run an AudioWorklet graph certified to match. If the picture and the bounce disagree, the UI is untrustworthy. SharedArrayBuffer rings also need COOP/COEP headers.

**Clone gravity.** Drag rings, snapin lanes, and Saturn overlays are load bearing. Palette, type, and the scene/gate surfaces have to be original or the tool will read as a Vital skin. Teenage Engineering and Elektron are safer visual north stars than a 3D skeuomorphic knob.

**Accessibility debt.** A canvas only rack will fail keyboard, screen reader, and reduced motion. Every control needs a DOM twin even if the ring is drawn in WebGL.

**Game versus instrument split.** Arcade and Spitfire optimize browsing. Serum optimizes patching. Wwise optimizes why-is-this-quiet. Audioface has to ship all three or it will satisfy no one. Sequence them: Chassis and Drop rings first (the engine is already a layer stack with modulation), Gate dock and Event in the room second (the engine already has gates and a listener), Kit well third.

**WebGPU and Safari.** Requiring WebGPU or AudioWorklet will strand the tool. Baseline is Web Audio, Canvas, and WebGL 2. Everything else is a faster path.

## References

Vendor and specs are listed in frontmatter. Additional image and video references used above:

- [Serum 2 beginner guide, interface shots](https://www.edmprod.com/serum-2-guide/)
- [Vital interface and matrix](https://www.edmprod.com/vital-synth/)
- [Europa shapeshifting synthesizer](https://www.reasonstudios.com/devices/europa)
- [Audiotool modular desktop](https://www.audiotool.com/product)
- [Endlesss 8 channel looper](https://endlesss.net/)
- [Soundtrap studio](https://www.soundtrap.com/content/product/online-daw-features)
- [TouchDesigner audio CHOPs](https://derivative.ca/UserGuide/Creating_Audio_with_CHOPs)
- [u-he Zebra2 grid](https://u-he.com/products/zebra-legacy/)
- [FL Studio Patcher](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual-zh/html/plugins/Patcher.htm)
- [Projektor, full Serum 2 UI tour](https://www.youtube.com/watch?v=ItRL3FNpd-8)
