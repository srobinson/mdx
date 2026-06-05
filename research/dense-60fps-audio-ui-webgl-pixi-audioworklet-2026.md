---
title: Dense 60fps browser audio UI uses WebGL2 plus AudioWorklet, not Canvas 2D or Houdini
type: research
tags: [webgl, webgpu, webaudio, offscreencanvas, pixijs, houdini, spectrogram, accessibility, audioface]
summary: Professional in-browser sound-design UIs split AudioWorklet DSP from GPU visualization (Pixi/WebGL2, WebGPU compute later) and DOM knobs; Canvas 2D, Houdini Paint, and three.js HUD knobs are the wrong stack.
status: active
confidence: high
project: audioface
created: 2026-09-03
updated: 2026-09-03
---

# Dense 60fps browser audio UI

Canonical copy of the pstack note also lives at `~/.mdx/TMP/pstack/audioface-ui-direction/web-rendering.md`.

## Executive Summary

A professional browser sound-design tool must split audio (AudioWorklet, never the main thread) from visualization (GPU canvases in workers) from controls (DOM widgets with compositor-only motion). Canvas 2D is the MDN teaching path for AnalyserNode meters and fails as soon as spectrograms, wavetables, modulation overlays, and a node graph share a frame. WebGL2 is the production baseline. WebGPU compute is the upgrade for GPU FFT and dense heatmaps, with a WebGL fallback. Houdini Paint, three.js HUD knobs, and NexusUI-class widgets are not a DAW stack.

## Detailed Findings

### Renderers

The Web Audio spec anticipates pairing the graph with canvas 2D and WebGL ([Web Audio API 1.1](https://webaudio.github.io/web-audio-api/)). MDN's AnalyserNode sample draws an oscilloscope with `requestAnimationFrame` plus Canvas 2D ([AnalyserNode](https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode)). That is correct for one scope, not a dense studio.

Canvas 2D is a CPU rasterizer. Independent 2D tests put the 60fps ceiling around a few thousand simple draws; past ~10k objects, frame rate collapses ([Habr 2025 bake-off](https://habr.com/ru/articles/970286/)). A UW CSE paper held 60 Hz spectrograms to 4096x4096 on GPU while Plot.ly and Vega failed at 128x128 ([Whitmire 2019](https://cse512-19s.github.io/FP-Signal-Viz/whitmire_paper.pdf)).

WebGL2 is the production GPU path: upload a spectrum row as a 1D texture, scroll history in a shader, color-map in the fragment stage. [Spectro](https://github.com/calebj0seph/spectro) does this (4096 windows, hop 1024, jsfft in a worker, WebGL shader; only new columns uploaded). [PixiJS v8](https://pixijs.com/8.x/guides/components/renderers) recommends WebGLRenderer for production; WebGPU is labeled experimental. Pixi v8 bunnymark: 100k moving sprites ~15 ms CPU / ~2 ms GPU versus v7 ~50 / ~9 ([Pixi v8 beta](https://pixijs.com/blog/pixi-v8-beta)). WAM-studio used pixi.js for GPU-accelerated layered waveforms plus an AudioWorklet VU ([WAM-studio](https://dl.acm.org/doi/fullHtml/10.1145/3543873.3587987)).

three.js `CSS2DRenderer` pins HTML labels onto 3D objects (translation only) ([CSS2DRenderer.js](https://github.com/mrdoob/three.js/blob/master/examples/jsm/renderers/CSS2DRenderer.js)). Use three.js for 3D wavetables or TSL `FFT2D` ([PR 34382](https://github.com/mrdoob/three.js/pull/34382)), not knobs.

WebGPU adds compute ([MDN WebGPU](https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API)). Shipping as of 2025-11-25 in Chrome 113+, Firefox 141/145 (Windows / Apple silicon Tahoe), Safari 26 ([web.dev](https://web.dev/blog/webgpu-supported-major-browsers)). [caniuse/webgpu](https://caniuse.com/webgpu) still shows Safari partial and Firefox disabled on many OS combinations, so v1 needs WebGL2 fallback.

### OffscreenCanvas and AnalyserNode

[OffscreenCanvas](https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas) is Baseline since March 2023. Workers may rAF. Worker animation survives a blocked main thread ([web.dev OffscreenCanvas](https://web.dev/articles/offscreen-canvas)). `BaseAudioContext` is `[Exposed=Window]` ([Web Audio API](https://webaudio.github.io/web-audio-api/)): you cannot poll AnalyserNode in a worker. Correct pattern: control thread copies FFT/samples into SAB; viz worker owns OffscreenCanvas; AudioWorklet writes a lock-free ring; main thread under 5% of one core ([cprimozic 2023](https://cprimozic.net/blog/building-a-signal-analyzer-with-modern-web-tech)).

### Houdini

[CSS Paint API](https://drafts.css-houdini.org/css-paint-api-1/) is a Canvas 2D subset (no ImageData, no text) ([MDN guide](https://developer.mozilla.org/en-US/docs/Web/API/CSS_Painting_API/Guide)). Worklets are for stateless, idempotent, short-running work ([HTML worklets](https://html.spec.whatwg.org/dev/worklets.html)). [caniuse](https://caniuse.com/css-paint-api): Chromium only; Safari disabled by default; Firefox none. Animation Worklet and Layout API remain drafts. `@property` is the only production Houdini piece.

### FFT and meters

`fftSize` is a power of two from 32 to 32768, default 2048 ([fftSize](https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode/fftSize)). A second frequency-data call in the same render quantum returns the previous buffer. Default quantum is 128 frames (~3 ms budget) ([Choi](https://developer.chrome.com/blog/audio-worklet-design-pattern)). AnalyserNode is a convenience FFT. Custom STFT belongs in AudioWorklet+WASM or GPU compute. Superpowered exposes WASM FFT ([Superpowered](https://docs.superpowered.com/)). Winning viz: FFT off main thread, one texture upload per new column, shader does scale/log-f/colormap.

### 60fps modulation

rAF follows display refresh and pauses in background tabs ([rAF](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)). Sync to `currentTime` is at best one display frame. AudioParam automation is sample-accurate on the audio clock ([AudioParam](https://developer.mozilla.org/en-US/docs/Web/API/AudioParam)). Sample it on rAF; do not drive audio from rAF. Animate with `transform`/`opacity`. Honor `prefers-reduced-motion: reduce` ([MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion)).

### Accessibility and MIDI

Knobs are sliders: APG `role="slider"` plus valuemin/max/now/text and arrow keys ([APG slider](https://www.w3.org/WAI/ARIA/apg/patterns/slider/)). Hidden native `<input type="range">` is more robust on mobile AT ([Vispero](https://vispero.com/resources/evolving-custom-sliders/)). [Web MIDI](https://developer.mozilla.org/en-US/docs/Web/API/Web_MIDI_API) is not Baseline; Soundtrap shows MIDI on Chrome/Edge, limited on Safari.

### Products

Audiotool (modular browser DAW, AudioWorklets, Chrome/Firefox), cables.gl (WebGL+WebGPU patcher), Soundtrap/BandLab/AmpedStudio (shipping DAWs), Superpowered WASM demos, Magenta (SVG piano roll over canvas), WAM-studio+pixi, web-synth analyzer. Endlesss Studio is native AU/VST, not a browser DAW.

## Sources Consulted

Specs and vendor docs: Web Audio API 1.1, MDN AnalyserNode/OffscreenCanvas/rAF/WebGPU/SAB/Web MIDI/Paint API/prefers-reduced-motion, W3C WebGPU CR, CSS Paint API, HTML worklets, WAI-ARIA APG slider, Chrome Audio Worklet design pattern, web.dev OffscreenCanvas and WebGPU-in-major-browsers, caniuse webgpu and css-paint-api.

Libraries and demos: PixiJS v8 renderers and bunnymark, Spectro, gl-spectrogram, regl, gpu.js, NexusUI, webaudio-controls, cutoff/audio-ui, Magenta visualizer, React Flow Web Audio tutorial, three.js CSS2DRenderer, Superpowered docs.

Products and papers: Audiotool, cables.gl, WAM-studio ACM paper, Soundtrap browser matrix, Endlesss user guide, cprimozic web-synth analyzer.

## Source Quality Assessment

High: W3C/WHATWG specs, MDN, Chrome/web.dev engineering posts, Pixi official benches, ACM WAM-studio, cprimozic (measured architecture). Medium: caniuse lag vs web.dev on WebGPU, Superpowered vendor timings, product marketing pages. Low/SEO: generic Canvas vs WebGL roundup blogs. Gaps: Audiotool and Soundtrap renderer internals are not public; GPU FFT-in-browser still lacks a single canonical library with published spectrogram fps.

## Open Questions

- Exact Pixi vs raw WebGL2 cost for a 16-channel meter + 4 spectrograms + wavetable at 120 Hz.
- Whether Safari 26 WebGPU compute is good enough to drop the WebGL spectrogram path on Apple hardware.
- Hidden native range vs full APG slider for rotary knobs with VoiceOver/TalkBack.
- COOP/COEP cost for embedding the tool in third-party iframes.

## Actionable Takeaways

Ship the split stack: AudioWorklet+WASM, SAB rings, OffscreenCanvas PixiJS v8 WebGL2 (or raw WebGL2) for dense viz, DOM knobs with hidden range + Web MIDI, xyflow only while graphs stay sparse, WebGPU compute as a later FFT upgrade. Reject Houdini Paint, NexusUI, and three.js HUD as the control surface.

Ranked stack and citations: `~/.mdx/TMP/pstack/audioface-ui-direction/web-rendering.md`.
