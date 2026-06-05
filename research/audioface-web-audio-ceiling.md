---
title: The Web Audio Capability Ceiling in 2026, and What audioface Is Not Yet Reaching
date: 2026-09-03
tags: [web-audio, audioworklet, wasm, game-audio, dsp, spatial-audio, research]
sources:
  - https://www.w3.org/TR/webaudio-1.1/
  - https://developer.mozilla.org/en-US/docs/Web/API/AudioContext
  - https://web.dev/articles/profiling-web-audio-apps-in-chrome
  - https://cprimozic.net/blog/webaudio-audioworklet-optimization/
  - https://emscripten.org/docs/api_reference/wasm_audio_worklets.html
  - https://github.com/andremichelle/openDAW
  - https://github.com/chaosprint/glicol
  - https://rnbo.cycling74.com/learn/the-web-export-target
  - https://github.com/grame-cncm/faustwasm
  - https://www.webaudiomodules.com/docs/intro/
  - https://github.com/GoogleChrome/omnitone
  - https://caniuse.com/midi
---

## Scope

This report covers what the browser can actually do with audio in 2026, where the platform stops, how the current state of the art pushes against those stops, and what that means for a deterministic offline sound engine aimed at three.js games. It is written from the platform side. It does not read the audioface source.

## The node inventory, and what each node cannot do

Web Audio API 1.1 reached First Public Working Draft on 5 November 2024 and remains the working reference ([W3C](https://www.w3.org/TR/webaudio-1.1/)). The node set is small and has been stable for years: `AnalyserNode`, `AudioBufferSourceNode`, `BiquadFilterNode`, `ChannelMergerNode`, `ChannelSplitterNode`, `ConstantSourceNode`, `ConvolverNode`, `DelayNode`, `DynamicsCompressorNode`, `GainNode`, `IIRFilterNode`, `MediaElementAudioSourceNode`, `MediaStreamAudioSourceNode`, `MediaStreamTrackAudioSourceNode`, `MediaStreamAudioDestinationNode`, `OscillatorNode`, `PannerNode`, `StereoPannerNode`, `WaveShaperNode`, `AudioDestinationNode`, plus `AudioWorkletNode`.

The important part is the negative space. `DynamicsCompressorNode` exposes threshold, knee, ratio, reduction, attack and release, and nothing else. It has no sidechain input, a gap raised against the spec in 2015 and still open ([WebAudio/web-audio-api#246](https://github.com/WebAudio/web-audio-api/issues/246)); the working answer in 2026 is to write your own compressor as an AudioWorklet with a second input as the key signal ([jadujoel/sidechain-compressor-audio-worklet](https://github.com/jadujoel/sidechain-compressor-audio-worklet)). Its internal detector is unspecified in detail, so its output differs between engines. `PannerNode` in HRTF mode is defined for stereo output only, and its distance models are limited to linear, inverse and exponential. `IIRFilterNode` takes fixed feedforward and feedback coefficient arrays that cannot be automated, so a sweeping filter has to be a biquad or your own code. `ConvolverNode` has one buffer, a `normalize` flag, and no way to change impulse response without a glitch or a crossfade between two convolvers. `WaveShaperNode` takes a curve and an `oversample` value of none, 2x or 4x, which is the platform's entire built in answer to aliasing in nonlinear processing.

The conclusion for a professional tool is direct: the built in nodes are a convenience layer, not a capability layer. Everything expressive lives in AudioWorklet.

## AudioWorklet is the real ceiling, and it has sharp edges

The render quantum is fixed at 128 frames. Web Audio 1.1 adds `renderSizeHint` on `AudioContextOptions` with values `"default"` and `"hardware"`, where hardware lets the user agent pick the size best suited to the device, at the cost of exposing information the spec explicitly flags as a fingerprinting vector ([W3C](https://www.w3.org/TR/webaudio-1.1/)). At 44.1 kHz, 128 frames is a 2.9 ms deadline per callback. Miss it and you get a dropout.

That deadline is why the practical rules are so strict. JavaScript garbage collectors are not real time safe, so anything that allocates inside `process()` is a latent glitch: no `new`, no array literals, no string concatenation, no `new Float32Array(128)`, all buffers preallocated in the constructor ([loke.dev](https://loke.dev/blog/stop-allocating-inside-audioworkletprocessor), [Mozilla Hacks](https://hacks.mozilla.org/2020/05/high-performance-web-audio-with-audioworklet-in-firefox/)). WebAssembly is not automatically faster, it is more predictable, and Emscripten's Wasm Audio Worklets runtime is specifically built so that no temporary JavaScript garbage is produced on the audio thread ([Emscripten](https://emscripten.org/docs/api_reference/wasm_audio_worklets.html)). Where a WASM kernel wants a block size other than 128, the standard bridge is a ring buffer inside the processor ([Chrome Labs](https://googlechromelabs.github.io/web-audio-samples/audio-worklet/design-pattern/wasm-ring-buffer/)); where work needs to leave the audio thread entirely, the pattern is AudioWorklet plus SharedArrayBuffer plus Worker, with a wait free single producer single consumer queue between them ([Chrome Labs](https://googlechromelabs.github.io/web-audio-samples/audio-worklet/design-pattern/shared-buffer/), [Paul Adenot](https://blog.paul.cx/post/a-wait-free-spsc-ringbuffer-for-the-web/)).

The least obvious hazard is `AudioParam` count. Casey Primozic traced clicking in a polyphonic WASM synth not to the DSP but to Chrome's per callback parameter marshalling, `ParamValueMapMatchesToParamsObject`, which allocated strings and hash maps across 34 audio rate parameters per voice, 544 across sixteen voices. Cutting to six per voice, 96 total, took total `AudioDestination::RequestRender` from 5.936 ms to 2.311 ms and removed the artefacts entirely ([cprimozic.net](https://cprimozic.net/blog/webaudio-audioworklet-optimization/)). For an engine with roughly forty registry parameters per layer, this is the single most important implementation constraint on the page: do not express a large parameter set as AudioParams. Express it as timestamped control events over a shared ring buffer.

Two further constraints on the worklet global scope: it forbids network access and dynamic imports, so module bytes must be fetched on the main thread and passed in; and SharedArrayBuffer requires cross origin isolation via COOP and COEP headers, which you cannot assume in an arbitrary embed.

## Automation, offline rendering, and observability

`AudioParam` offers `setValueAtTime`, `linearRampToValueAtTime`, `exponentialRampToValueAtTime`, `setTargetAtTime`, `setValueCurveAtTime`, `cancelScheduledValues` and `cancelAndHoldAtTime`, evaluated either a-rate, once per sample, or k-rate, once per 128 frame quantum. `setValueCurveAtTime` is the closest thing the platform has to a baked envelope, and it is the natural bridge for an engine that already computes envelopes in the sample domain.

`OfflineAudioContext` renders faster than real time into an `AudioBuffer` and supports `suspend` and `resume` for scheduling changes mid render. It is deterministic with respect to system timing, but it is not deterministic across browsers: any graph containing `DynamicsCompressorNode`, `PannerNode` in HRTF mode, or a resampler will produce different samples in different engines. An engine that computes its own DSP in its own code and uses Web Audio only as a sink is therefore the only design that can make a certification gate mean anything across browsers. That is a genuine architectural advantage, not an accident.

For observability the platform has finally caught up. `AudioRenderCapacity`, reachable from the context, offers `start()`, `stop()` and an `onupdate` event delivering average, minimum, maximum and underrun ratios, where capacity is render time divided by quantum duration times one hundred and values near 100 predict glitches ([W3C](https://www.w3.org/TR/webaudio-1.1/), [web.dev](https://web.dev/articles/profiling-web-audio-apps-in-chrome)). `AudioPlaybackStats` adds `underrunEvents` and `underrunDuration` on the context ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/AudioPlaybackStats)). `baseLatency` and `outputLatency` report the pipeline delay, `getOutputTimestamp()` correlates context time with performance time for audio to visual sync, and `setSinkId()` with the `sinkchange` event allows output device selection in a secure context ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/AudioContext)).

## Spatialisation

Two options exist. The built in `PannerNode` with `panningModel: "HRTF"` uses the browser's own HRTF dataset and is stereo out only. The alternative is ambisonic rendering with your own decoder: Omnitone decodes first, second and third order ambisonics and renders binaurally through eight virtual speakers convolved with HRTFs, with a rotation matrix so the field follows head or camera orientation ([GoogleChrome/omnitone](https://github.com/GoogleChrome/omnitone)). Resonance Audio builds on Omnitone and adds source directivity, spread, near field effects and a simple room model. Notably, a WebXR comparison found the plain `PannerNode` HRTF path outperformed both equalpower panning and Resonance Audio for correct source identification, so the expensive path is not automatically the better one ([White Rose / ResearchGate survey](https://www.researchgate.net/publication/374413358)).

For a three.js engine the practical shape is a per source direction and distance model computed in your own code, feeding either a stereo binaural convolution you control or an ambisonic bus decoded once at the listener. The second scales better with voice count, because HRTF convolution cost is paid once rather than per voice.

## Adjacent APIs

`WebCodecs` `AudioDecoder` and `AudioEncoder` handle AAC, Opus, FLAC and raw PCM. Safari reached audio parity only in Safari 26; Firefox 130 and later supports the full API on desktop but not on Android, and AAC encoding is missing in Firefox on every platform ([digitalsamba](https://www.digitalsamba.com/blog/webcodecs-api-explained), [MDN codec selection](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API/Codec_selection)). Web MIDI ships in Chrome 43 and later, Edge 79 and later, Opera and Firefox 108 and later, and remains entirely absent from Safari and iOS on fingerprinting grounds with no published roadmap ([caniuse](https://caniuse.com/midi)). WebGPU shipped by default in Chrome, Firefox, Safari and Edge as of November 2025, and three.js ships a `webgpu_compute_audio` example, but GPU readback latency makes compute shaders a tool for offline baking rather than for the audio callback ([webgpu.com](https://www.webgpu.com/news/webgpu-hits-critical-mass-all-major-browsers/), [three.js](https://threejs.org/examples/webgpu_compute_audio.html)).

The most consequential platform quirk is on iOS: Web Audio output respects the hardware mute switch while `<audio>` and `<video>` elements do not, so a muted phone plays no Web Audio at all ([adactio](https://adactio.com/journal/19929)). Any browser game shipping to iOS needs to detect and explain this.

## State of the art

The field splits into three groups. Framework layers such as Tone.js remain the common entry point, still maintained, with 15.1.22 stable in April 2025 and a 15.5.12 preview in May 2026 ([GitHub](https://github.com/Tonejs/Tone.js/releases)); its cost is size, and Glicol notes 2.1 MB for `glicol.js` against 11.3 MB for `tone.js` ([chaosprint/glicol](https://github.com/chaosprint/glicol)). Compilation targets are the second group: Faust exports web nodes through `faustwasm`, a TypeScript and JavaScript wrapper around the WASM compiler ([grame-cncm/faustwasm](https://github.com/grame-cncm/faustwasm)); Cycling '74 RNBO compiles a patch to WASM via a cloud compiler and wraps each device as an `AudioWorkletNode`, free to ship below 200k in annual revenue or funding ([Cycling '74](https://rnbo.cycling74.com/learn/the-web-export-target), [licensing FAQ](https://support.cycling74.com/hc/en-us/articles/10730637742483)); Elementary Audio takes the opposite route with a declarative JavaScript DSP graph that reconciles like a UI tree, MIT licensed, targeting native and web from one description ([elementary.audio](https://www.elementary.audio/)). Web Audio Modules 2.0, stable since 2021, remains the only real plugin interop story, with an SDK, host and plugin APIs and WASM based processors ([webaudiomodules.com](https://www.webaudiomodules.com/docs/intro/)).

The third group is applications. Glicol writes both language and engine in Rust, compiles to WASM, runs in AudioWorklet and communicates over SharedArrayBuffer, proving sample accurate synthesis under live coding pressure ([Web Audio Conference 2021](https://webaudioconf.com/posts/2021_8/)). Strudel brings the TidalCycles pattern model to the browser. openDAW, released into public view during 2026, is the most instructive reference for audioface: pure TypeScript with minimal dependencies, AGPL v3, a box graph data layer separated from an engine facade that talks to a single AudioWorklet, a processor running BlockRenderer then ClipSequencing then per channel AudioUnits then effect DeviceChains once per 128 frame quantum, and all heavy non real time work such as peak generation, file decoding and FFmpeg pushed into plain Web Workers ([andremichelle/openDAW](https://github.com/andremichelle/openDAW), [DeepWiki](https://deepwiki.com/andremichelle/openDAW)). Audiotool, BandLab and Soundtrap represent the commercial browser DAW tier. Chrome Music Lab and Ableton Learning Synths remain the reference points for approachable audio interfaces, both built on Web Audio, Web MIDI and Tone.js ([Google Developers Blog](https://developers.googleblog.com/introducing-chrome-music-lab/)). Game middleware has not followed: Wwise and FMOD reach the browser through WebAssembly builds, and developers still report feature gaps in those targets, which leaves an open field for a native browser engine.

## (a) The fifteen capabilities that matter most

Ranked by impact for game sound effects and adaptive music, given an engine that renders offline, deterministically, in the sample domain, with a 2.5 second patch ceiling.

1. Real time parameter control of a sounding voice. Without it there is no engine RPM, no continuous filter sweep tied to player state, no crossfade under game input. This is the difference between a sound generator and a game audio engine.
2. Sustaining and looping sources. A 2.5 second ceiling excludes ambience beds, engine loops, weapon loops and music. Loop points, sustain regions and seamless retrigger are prerequisites for the next four items.
3. Sample and wavetable playback. Professional game sound is layered synthesis over recorded material. Without buffer playback the tool cannot be used on a real project.
4. Adaptive music: a tempo grid, transition sync points, vertical layer mutes and horizontal stinger scheduling. This is the second half of the stated product goal and is currently absent entirely.
5. Convolution reverb on a shared send bus, with impulse response swapping and per source send levels. Reverb is what makes a game world sound like a place.
6. Binaural or ambisonic spatialisation driven by the three.js camera, with occlusion and obstruction filtering, replacing the current pan, width and one pole air filter model.
7. A modulation source layer: free running LFOs with tempo sync and phase reset, step and random sources, feeding the existing connection list. The modulation matrix exists; the sources are thin.
8. Nonlinear processing: waveshaping, saturation, bitcrush and fold, with oversampling. Almost every AAA impact and weapon sound relies on it.
9. Dynamics with sidechain: a compressor whose key input is another bus, for ducking dialogue and music against effects.
10. A bus architecture with sends, returns and submix groups, so layers can share processing rather than each carrying its own echo.
11. Playback containers: round robin, random with weighting, blend containers driven by a game parameter. This is the middleware behaviour designers expect and it does not require new DSP.
12. Granular and time domain stretching, for texture, debris and slow motion.
13. Analyser taps exposing spectra and envelopes to the visual layer, which is the differentiator for a tool sold on being visually stunning next to three.js.
14. Asset ingest through WebCodecs, so designers can drop recorded material in and have it decoded off the audio thread.
15. Runtime observability and routing: render capacity, underrun counters, per voice metering, output device selection, and Web MIDI controller binding where the browser supports it.

## (b) Marrying the deterministic offline renderer to a real time graph

Three architectures are available.

The first keeps the TypeScript renderer as the offline bounce path and writes a separate real time AudioWorklet engine. It is the fastest to demonstrate and the worst to live with: two DSP implementations drift, and a certification suite that only measures one of them certifies nothing about what the player hears.

The second rewrites the DSP in Rust or C, compiles to WASM, and runs the identical binary in both an OfflineAudioContext bounce and a real time AudioWorklet. This is the Glicol architecture and it gives bit identical offline and online output by construction. The costs are real: a language boundary through the whole codebase, a build pipeline, and a deployment that wants cross origin isolation for SharedArrayBuffer.

The third, and the recommendation, is a single TypeScript DSP core restructured as an allocation free block processor with a 128 frame quantum, hosted in three places from one source: a Node test harness for the certification gates, an OfflineAudioContext or direct buffer fill for deterministic bounces, and an AudioWorklet for real time. Determinism survives because the same code and the same seeded PRNG run in every host; the frames rather than milliseconds convention already matches the quantum; the linear gain convention already avoids per sample conversions. Control flows one way over a SharedArrayBuffer ring buffer carrying timestamped parameter events, deliberately not through dozens of AudioParams, per the Primozic finding. Voice allocation, class floors and steal ramps move into the worklet and run at quantum granularity. Heavy work, decode, peak generation and offline bounces, goes to Workers, following openDAW. WASM enters later as a drop in replacement for individual hot kernels, filters and oscillators, once profiling names them, without disturbing the graph. Guard the whole thing with a differential test: render a patch offline, render it through the worklet under an OfflineAudioContext, and require a null result. That test is what makes the two paths one engine.

## (c) The hard limits

The 128 frame quantum is fixed, and `renderSizeHint: "hardware"` only lets the user agent choose, so a floor of roughly 2.9 ms of buffering at 44.1 kHz cannot be removed. There is no hard real time guarantee anywhere in the platform; the audio thread is best effort and subject to GC and OS scheduling, an issue the working group has acknowledged and not solved ([WebAudio/web-audio-api#1327](https://github.com/WebAudio/web-audio-api/issues/1327)). The audio worklet scope cannot fetch or dynamically import. SharedArrayBuffer needs cross origin isolation, which you do not control inside a third party embed. Contexts require a user gesture to start. Sample rate belongs to the device, and asking for another one buys a resampler. Built in HRTF panning is stereo out only. `DynamicsCompressorNode` has no sidechain and no exposed detector. `IIRFilterNode` coefficients are not automatable. Native node output is not identical across browsers, so cross browser determinism is only achievable by owning the DSP. Web MIDI does not exist on Safari or iOS. iOS silences Web Audio when the hardware mute switch is on. WebGPU compute cannot participate in the audio callback because readback is not real time safe.

Every one of those is a reason the existing audioface design, own DSP, own scheduling, browser as sink, is the correct foundation. The gap is not the foundation. The gap is that the foundation currently only renders, and a game engine has to also play, react and sustain.

## References

- W3C, Web Audio API 1.1, First Public Working Draft, 5 November 2024. https://www.w3.org/TR/webaudio-1.1/
- MDN, AudioContext. https://developer.mozilla.org/en-US/docs/Web/API/AudioContext
- MDN, AudioPlaybackStats. https://developer.mozilla.org/en-US/docs/Web/API/AudioPlaybackStats
- MDN, WebCodecs codec selection. https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API/Codec_selection
- web.dev, Profiling Web Audio apps in Chrome. https://web.dev/articles/profiling-web-audio-apps-in-chrome
- Chrome for Developers, Audio worklet design pattern. https://developer.chrome.com/blog/audio-worklet-design-pattern/
- Chrome Labs, WASM ring buffer in AudioWorkletProcessor. https://googlechromelabs.github.io/web-audio-samples/audio-worklet/design-pattern/wasm-ring-buffer/
- Chrome Labs, AudioWorklet, SharedArrayBuffer and Worker. https://googlechromelabs.github.io/web-audio-samples/audio-worklet/design-pattern/shared-buffer/
- Casey Primozic, Finding and Fixing an AudioWorkletProcessor Performance Pitfall. https://cprimozic.net/blog/webaudio-audioworklet-optimization/
- Loke.dev, Stop Allocating Inside the AudioWorkletProcessor. https://loke.dev/blog/stop-allocating-inside-audioworkletprocessor
- Paul Adenot, A wait free SPSC ring buffer for the web. https://blog.paul.cx/post/a-wait-free-spsc-ringbuffer-for-the-web/
- Mozilla Hacks, High Performance Web Audio with AudioWorklet in Firefox. https://hacks.mozilla.org/2020/05/high-performance-web-audio-with-audioworklet-in-firefox/
- Emscripten, Wasm Audio Worklets API. https://emscripten.org/docs/api_reference/wasm_audio_worklets.html
- WebAudio/web-audio-api issue 246, sidechain compression. https://github.com/WebAudio/web-audio-api/issues/246
- WebAudio/web-audio-api issue 1327, hard real time guarantees. https://github.com/WebAudio/web-audio-api/issues/1327
- jadujoel, Sidechain compressor AudioWorklet. https://github.com/jadujoel/sidechain-compressor-audio-worklet
- GoogleChrome/omnitone. https://github.com/GoogleChrome/omnitone
- Google Open Source Blog, Omnitone: spatial audio on the web. https://opensource.googleblog.com/2016/07/omnitone-spatial-audio-on-web.html
- How to Spatial Audio with the WebXR API. https://www.researchgate.net/publication/374413358
- caniuse, Web MIDI API. https://caniuse.com/midi
- Digital Samba, What is the WebCodecs API, browser codec guide 2026. https://www.digitalsamba.com/blog/webcodecs-api-explained
- webgpu.com, WebGPU hits critical mass. https://www.webgpu.com/news/webgpu-hits-critical-mass-all-major-browsers/
- three.js, WebGPU compute audio example. https://threejs.org/examples/webgpu_compute_audio.html
- Adactio, Web Audio API update on iOS. https://adactio.com/journal/19929
- Tone.js releases. https://github.com/Tonejs/Tone.js/releases
- chaosprint/glicol. https://github.com/chaosprint/glicol
- Web Audio Conference 2021, Glicol: a graph oriented live coding language with Rust, WebAssembly and AudioWorklet. https://webaudioconf.com/posts/2021_8/
- andremichelle/openDAW. https://github.com/andremichelle/openDAW
- DeepWiki, openDAW architecture. https://deepwiki.com/andremichelle/openDAW
- Elementary Audio. https://www.elementary.audio/
- grame-cncm/faustwasm. https://github.com/grame-cncm/faustwasm
- Faust, deploying on the web. https://faustdoc.grame.fr/manual/deploying/
- Cycling '74, the RNBO web export target. https://rnbo.cycling74.com/learn/the-web-export-target
- Cycling '74, RNBO export licensing FAQ. https://support.cycling74.com/hc/en-us/articles/10730637742483
- Web Audio Modules 2 introduction. https://www.webaudiomodules.com/docs/intro/
- Web Audio Modules 2.0: An Open Web Audio Plugin Standard, ACM. https://dl.acm.org/doi/fullHtml/10.1145/3487553.3524225
- Google Developers Blog, Introducing Chrome Music Lab. https://developers.googleblog.com/introducing-chrome-music-lab/
- Web Audio Conference 2025, IRCAM Paris, 19 to 21 November 2025. https://wac-2025.ircam.fr/
