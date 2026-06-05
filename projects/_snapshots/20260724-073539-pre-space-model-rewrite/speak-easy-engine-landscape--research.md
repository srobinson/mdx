---
title: speak-easy engine landscape — local streaming STT for sub-200ms finalization on Apple Silicon / Electron
type: research
tags: [stt, speech-to-text, streaming, moonshine, parakeet, kyutai, whisper-cpp, sherpa-onnx, electron, apple-silicon, latency, endpointing]
summary: Moonshine-first is defensible on raw model latency but the realistic winner for a true-streaming, in-process, Electron/Node Apple-Silicon engine is sherpa-onnx streaming zipformer (native N-API addon, built-in endpointing). Sub-200ms finalization is an endpointing-config problem, not a model-selection problem.
status: active
source: warroom-research (speak-easy pane); refresh of cm 019e9a41
confidence: medium
created: 2026-06-21
updated: 2026-06-21
---

# speak-easy engine landscape research

Scope: best LOCAL streaming speech-to-text to hit **sub-200ms finalization** (end-of-speech → committed final transcript), wired into a **Node/Electron** runtime on **Apple Silicon**, transcript **quality deprioritized**. Refreshes cm decision `019e9a41` (2026-06-06 two-way voice-chat snapshot). Web-sourced June 2026; all latency claims tagged verified vs vendor/paper.

## TL;DR / verdict

- **Challenge, do not blindly accept, "Moonshine-first."** Moonshine v2 (Feb 2026) has the **tightest published finalization numbers** of any candidate, but its realistic Node path is **non-streaming** and it has **no built-in endpointer**. It is the best *model*, not the best *integration*.
- **The realistically-wireable, truly-streaming, in-process winner is `sherpa-onnx` streaming zipformer transducer** (k2-fsa): prebuilt native **N-API Node addon** (`npm i sherpa-onnx`, `sherpa-onnx-darwin-arm64`), emits incremental partials, has **built-in `IsEndpoint()` endpointing**, runs in the Electron **Node main process with zero IPC**, RTF 0.009–0.033 verified on Apple Silicon. This is the substrate; it can *also* host Moonshine as a (non-streaming) model.
- **Key reframe:** for these tiny transducers, **inference compute is not the bottleneck** (RTF ≈ 0.01, single-digit ms on a finalized utterance). The sub-200ms budget is dominated by the **endpoint lookahead / VAD silence-hangover**. So "hit sub-200ms" is an **endpointing-config problem**, not an engine horse-race. Pick an engine with **tunable endpointing + small right-context**, then tune.
- **Integration shape:** native N-API addon (sherpa-onnx) > sidecar > onnxruntime-node CoreML EP > in-renderer WASM. CoreML EP is a **trap** for these models (slower than CPU, and the official `onnxruntime-node` arm64 binary ships **CPU-only**).
- **Contract** (frame-in / event-out) is the right boundary for both consumers. **One real fork risk:** baking a single endpoint policy. Add per-session endpoint config + an explicit `.flush()/.finalize()` + `.reset()` and neither consumer forks.

## What CHANGED since anchor 019e9a41 (2026-06-06)

The anchor was a *two-way voice-chat* study (cascaded VAD→STT→LLM→TTS, barge-in, MLX+CUDA dual-target). It named Parakeet TDT 0.6b / Moonshine v2 / Kyutai STT 1b / WhisperKit as STT candidates but did **not** evaluate the Node/Electron integration axis or a dictation-grade endpoint→final metric. New since then:

1. **Moonshine v2 shipped (Feb 2026, arXiv 2602.12241).** Useful Sensors → **Moonshine AI** (`moonshine-ai/moonshine`). True **streaming encoder** (sliding-window attention, no positional embeddings → constant-time TTFT). Sizes: Tiny 33.6M / Small 123.4M / Medium 244.9M. Emits self-correcting provisional partials. This is a genuine upgrade over v1's VAD-gated chunking.
2. **sherpa-onnx emerged as the integration answer** the anchor never mentioned: a prebuilt streaming-transducer Node addon with built-in endpointing. This is the single most important new finding for the Electron target.
3. **Parakeet streaming reality clarified.** The famous `parakeet-tdt-0.6b-v2/v3` checkpoints are **OFFLINE** (NVIDIA `nithinraok` confirmed; "streaming" = slow buffered chunking). True streaming needs distinct models: `parakeet-unified-en-0.6b`, `nemotron-speech-streaming-en-0.6b`, or **FluidAudio's `parakeet-realtime-eou-120m-coreml`** (Swift/CoreML/ANE, true partials + built-in end-of-utterance).
4. **Nemotron-3.5-ASR-streaming-0.6b** (NVIDIA, Jun 2026, arXiv 2604.14493): cache-aware streaming, controllable 80–1120ms chunks, int4 0.67GB. NeMo/CUDA-first, **no Node binding**.
5. **Kyutai STT unchanged** (still stt-1b-en_fr @ 0.5s delay + semantic VAD; stt-2.6b-en @ 2.5s delay). The "flush trick" (~125ms) story is now documented but remains vendor-only and shaky on Mac (maintainer issue #123: Rust mic STT "painfully slow").
6. **whisper.cpp confirmed structurally unable** to hit sub-200ms finalization (sliding-window re-decode + VAD hangover), though it has the easiest Node bindings.

## Latency budget decomposition (the reframe that matters)

```
endpoint→final  =  VAD/endpoint silence-hangover            ← DOMINATES (200–500ms typical for Silero)
                +  streaming model right-context/lookahead   ← 80–500ms, model-dependent, TUNABLE
                +  decode of the trailing window             ← single-digit ms (RTF ≈ 0.01) — negligible
                +  IPC / frame transfer                       ← ~0 in-process; small for raw-PCM sidecar
```

Implication: a faster *model* barely moves the number once you are below RTF 0.1. What moves it is **how aggressively you let the endpointer fire** and **how small the model's right-context is**. Sub-200ms is therefore reachable only with an **eager endpoint rule + small-lookahead streaming model**, and is fundamentally **a tuning task to benchmark on Stuart's Mac**, exactly as the anchor predicted ("next step is benchmark, not research").

## Engine comparison

| Engine (mid-2026) | True streaming + partials | Built-in endpointing | Realistic Node/Electron path | Sub-200ms endpoint→final? |
|---|---|---|---|---|
| **sherpa-onnx streaming zipformer** (k2-fsa) | **Yes**, incremental | **Yes** (`IsEndpoint`, tunable) | **Native N-API addon, in-process** (`npm i sherpa-onnx`) | **Yes, by config** — best bet |
| **Moonshine v2** (Moonshine AI) | Yes (streaming encoder) | **No** (external VAD) | Transformers.js → `onnxruntime-node` (**non-streaming**); or as non-streaming model inside sherpa-onnx | Plausible (model 50–148ms paper) **+ VAD hangover** |
| **Parakeet — FluidAudio EOU 120M** (CoreML/ANE) | Yes, partials + EOU | **Yes** (EOU token) | **Swift sidecar** (no Node binding) | Borderline yes (160ms chunk) via sidecar |
| **Parakeet TDT 0.6b v2/v3** (NeMo/MLX) | **No** (offline checkpoint) | No | parakeet-mlx Python **sidecar** | No (offline) |
| **Nemotron-3.5-ASR-streaming-0.6b** | Yes, cache-aware | Yes (chunks 80–1120ms) | NeMo/CUDA, **no Node binding** → ONNX-export or sidecar | Possibly, but hardest to wire |
| **Kyutai STT 1b-en_fr** | Yes (delayed streams) | Yes (semantic VAD) | **Rust/MLX WebSocket sidecar** (no JS) | Vendor-claimed ~125ms ("flush trick"), **shaky on Mac** |
| **whisper.cpp streaming** | **No** (sliding-window re-decode) | No (silence-gated chunk) | Easiest Node bindings (`smart-whisper`, Metal, Float32 in-process) | **No** — structural floor several-hundred-ms to ~1s |

## Per-engine notes

### Moonshine v2 — best raw model latency, weakest streaming integration
- **Paper M3 endpoint→final (VENDOR/PAPER, ONNX-on-CPU):** Tiny **50ms** / Small **148ms** / Medium **258ms** (vs Whisper Tiny 289ms, Small 1940ms). **No independent consumer-Apple-Silicon verification found.** Treat as plausibly-sub-200ms model compute only.
- **No internal endpointer** — paper defines latency as *after a VAD fires*. Real perceived finalization = model latency **+ Silero silence-hangover (~200–500ms)**. To hit sub-200ms *perceived*, the VAD tuning matters more than the model choice.
- **No Node binding** for the official C++ `moonshine-voice` lib. Only real npm route: **Transformers.js**, which loads Moonshine ONNX via `onnxruntime-node` in a **non-streaming** mode. `sherpa-onnx` carries Moonshine as a **non-streaming** model too. So in Node you lose the streaming encoder advantage unless you write a native addon.
- Since quality is deprioritized, **Tiny-Streaming** is the natural pick if you go Moonshine.

### sherpa-onnx streaming zipformer — the integration winner
- Prebuilt native **N-API addon**, `sherpa-onnx-darwin-arm64` binaries (no compile). True streaming: `stream.acceptWaveform(16k Float32)` → poll `recognizer.getResult()` for **partials** → `recognizer.isEndpoint(stream)` to **commit final** + `reset()`.
- **In-process in Node main → zero IPC.** RTF **0.009–0.033 verified on Apple Silicon M5** (Soniqo). Endpointing is built-in and tunable (trailing-silence rules).
- Quality deprioritized *helps here*: a 3.5M–small zipformer is CPU-fast, making ANE/CoreML pointless and removing build/packaging pain.
- Electron packaging: run `@electron/rebuild` for ABI, mark `.node`+dylibs `asar.unpacked`. Bounded, well-trodden.

### Parakeet — only via sidecar; FluidAudio is the streaming path
- 0.6b TDT is **offline**; do not expect streaming from it. The streaming story is **FluidAudio `parakeet-realtime-eou-120m-coreml`** (M2: 160ms chunk → 8.29% WER, 4.78× RTFx; 320ms chunk → 4.87% WER, 12.48× RTFx) — true partials + built-in EOU, but **Swift, no Node binding → sidecar**. `parakeet-mlx` has `transcribe_stream` (finalized+draft tokens) but is CLI-only, rough, no merge strategy.
- `@qvac/transcription-parakeet` (npm, ONNX C++ addon) claims streaming+EOU — unverified, worth a look if you want Parakeet in-process.

### Kyutai STT — only credible sub-200ms *design*, but vendor-only and Mac-shaky
- 1b-en_fr: **500ms delay floor** + semantic VAD; documented "flush trick" exploits ~4× realtime headroom → **~125ms** endpoint→final (**VENDOR claim**, kyutai.org/stt). Depends on sustaining 4× realtime on your Mac — maintainer issue #123 reports Rust mic STT "painfully slow," so the 4× assumption is **not guaranteed**.
- macOS: Rust/Candle `moshi-server` (Metal) or `moshi-mlx`. **No JS** — WebSocket **sidecar** streaming partials/finals.

### whisper.cpp — easiest Node, wrong finalization model
- `stream` example re-decodes a sliding window (not true streaming). VAD mode waits for silence then re-decodes the trailing `--length` window. Finalization gated by **silence-hangover + full-window re-decode** → realistic floor **several-hundred-ms to ~1s**. Cannot meet target by design.
- Node: `smart-whisper` (native addon, Metal auto on macOS, accepts Float32Array 16k mono) is the cleanest in-process binding, but exposes whole-buffer `transcribe`, not streaming finalization. Good fallback for *quality* dictation, not for *latency*.

## Integration shape — which is realistically wireable into Electron Node main on macOS

| Shape | True streaming? | Overhead | macOS accel | Verdict |
|---|---|---|---|---|
| **(c) Native N-API addon** (sherpa-onnx) | **Yes** (frames in, partials + `isEndpoint`) | **None** (in-process) | CPU (enough at RTF 0.01) | **Recommended** — already-built, zero-IPC, in Node main |
| **(d) Sidecar** (Swift FluidAudio / Python parakeet-mlx / Rust moshi-server) | Yes (socket/SSE) | IPC + frame transfer (send **raw PCM bytes**, not JSON) | **Full ANE/MLX/Metal** | Reserve — for FluidAudio/Kyutai/MLX; heavy packaging (PyInstaller codesign saga) |
| **(b) onnxruntime-node + CoreML EP** | Yes | None | **Trap**: official arm64 npm binary is **CPU-only** (#15226); self-built CoreML is **slower than CPU** for these models (sherpa #2910: RTF 0.470 CoreML vs 0.427 CPU) | Avoid |
| **(a) in-renderer WASM** (onnxruntime-web) | Yes | In-process but UI-thread risk | WASM-SIMD CPU only; WebGPU often **slower** than CPU for sub-1B ASR (#27809) + 1–5s shader warmup | Weakest |

**Recommendation: shape (c).** Renderer captures 16kHz mono Float32 via `getUserMedia`→AudioWorklet → frames over `ipcRenderer` to main → `sherpa-onnx` in-process → partials/finals back. CoreML/ANE is a deliberate non-goal (slower for tiny transducers; removes a whole class of build/packaging pain). Keep sidecar (d) in reserve only if you later want FluidAudio Parakeet or Kyutai specifically.

## Contract sanity-check: frame-in / event-out

Proposed contract: `VoiceToText.open(config) -> STTSession`; `pushAudio(frame 16kHz mono Float32)`, `.end()`; emits `partial{text}` / `final{text}` / `endpoint{}` / `error`.

**Verdict: correct boundary for BOTH consumers.** It maps 1:1 onto sherpa-onnx's API (`acceptWaveform` → `getResult` → `isEndpoint`) and onto every streaming candidate. 16kHz mono Float32 is the universal format (sherpa, Moonshine, whisper, AudioWorklet all want it) — **no fork risk on the frame format**.

**The ONE real fork risk: a single hardcoded endpoint policy.** The two consumers want *different* finalization behavior:
- **transport-matters director (one-way dictation):** ack-fast, eager endpointing — commit on short trailing silence; engine *owns* endpointing.
- **littleorgans (real-time conversational):** wants turn-aware finalization (semantic end-of-turn, must not clip the user); will likely run its **own** turn-detector (Smart-Turn-class) and treat the engine's `endpoint{}` as **advisory**.

If the contract bakes one endpoint rule, littleorgans forks it. **Three additions prevent the fork:**

1. **Per-session endpoint config** in `open(config)` — silence threshold, min trailing silence, min utterance length; ideally a pluggable endpoint mode (`eager` | `turn-aware` | `manual`).
2. **Explicit `.flush()` / `.finalize()`** — commit the current hypothesis as `final` *without closing the session*. Lets littleorgans drive finalization from its own turn detector, and lets dictation force-commit on a PTT release, **without either consumer forking the engine**. (Current contract only has `.end()`, which closes the session — insufficient for a continuous conversational stream.)
3. **`.reset()` / cancel** — drop the current hypothesis mid-stream cheaply (sherpa-onnx `reset()` supports this). Needed so a barge-in/cancel consumer can restart without tearing down the session. Barge-in orchestration stays consumer-owned (scope-out), but the engine must expose the primitive.

With (1)–(3), `endpoint{}` becomes a signal the consumer MAY act on rather than a mandate, partials can be ignored by the dictation consumer with no cost, and both consumers share one engine. **No fork.**

## Latency claims — verified vs vendor (per brief: most consumer-hardware figures are unverified)

| Claim | Source | Status |
|---|---|---|
| sherpa-onnx zipformer RTF 0.009–0.033 on M5 | Soniqo benchmarks | **Independent-ish** (throughput, not endpoint→final) |
| Moonshine v2 M3 endpoint→final 50/148/258ms (Tiny/Small/Medium) | arXiv 2602.12241 Table 2 | **Vendor/paper**, ONNX-on-CPU, no independent Mac verify |
| FluidAudio Parakeet-EOU 120M: 160ms→8.29% WER / 320ms→4.87% WER on M2 | FluidAudio benchmarks | **Vendor benchmark** (chunk processing, not endpoint→final) |
| Kyutai 1b "flush trick" ~125ms endpoint→final | kyutai.org/stt | **Vendor**, assumes 4× RT margin; issue #123 contradicts on Mac |
| Kyutai Rust server ~94ms/step on M4 Max | jeanjerome installer | **Community/vendor**, no RTF |
| whisper.cpp ~10× RT on M2 Pro; CoreML encoder +2–3× | voicci/justvoice/Fazm | **Community**; still cannot hit sub-200ms *finalization* by design |
| CoreML slower than CPU for transducer/conformer ASR | sherpa-onnx #2910, ort #27809 | **Independent (maintainer/issue)** |
| onnxruntime-node arm64 npm binary = CPU-only (no CoreML) | onnxruntime #15226 | **Independent (issue)** |
| Dictato "80ms mic-to-text", MetalRT RTF 0.0014, WhisperKit 0.46s | vendor blogs | **Vendor marketing**, discount |

**No independent end-to-end Electron + (sherpa-onnx/Moonshine) endpoint→final benchmark exists.** That is a measure-locally task.

## Recommendation

1. **Adopt `sherpa-onnx` (streaming zipformer transducer) as the v1 engine + integration substrate**: native N-API addon, in-process Node main, built-in tunable endpointing. It satisfies "truly streams partials + low-latency endpointing + realistically wireable into Electron" better than any alternative.
2. **Treat sub-200ms as an endpointing-tuning task**, not a model choice. Tune trailing-silence/min-utterance + keep right-context small.
3. **Benchmark spike on Stuart's Mac** (the decisive step): measure endpoint→final for (a) sherpa-onnx streaming zipformer, (b) Moonshine v2 Tiny via onnxruntime-node + Silero VAD. Do not pre-pick; both are plausible, neither is verified on consumer Apple Silicon.
4. **Moonshine-first is a defensible *model* hedge** (tightest published numbers) but should ride **inside** the sherpa-onnx integration (as a non-streaming model) or via Transformers.js — its lack of a streaming Node binding and built-in endpointer means it is not, by itself, the integration answer.
5. **Harden the contract** with per-session endpoint config + `.flush()/.finalize()` + `.reset()` so littleorgans (turn-aware, owns its endpointer) and the director (eager, engine-owned endpointing) share one engine without forking.

## Sources
- Moonshine v2: https://arxiv.org/abs/2602.12241 ; https://github.com/moonshine-ai/moonshine ; https://huggingface.co/posts/Xenova/486935205804807
- sherpa-onnx Node: https://www.npmjs.com/package/sherpa-onnx ; https://github.com/k2-fsa/sherpa-onnx/blob/master/nodejs-addon-examples/README.md ; https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/zipformer-transducer-models.html ; CoreML<CPU: https://github.com/k2-fsa/sherpa-onnx/issues/2910
- Parakeet: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3 ; offline confirm https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2/discussions/3 ; streaming https://huggingface.co/nvidia/parakeet-unified-en-0.6b ; https://huggingface.co/nvidia/nemotron-speech-streaming-en-0.6b ; FluidAudio https://github.com/FluidInference/FluidAudio/blob/main/Documentation/Benchmarks.md ; https://huggingface.co/FluidInference/parakeet-realtime-eou-120m-coreml ; parakeet-mlx https://github.com/senstella/parakeet-mlx ; npm https://www.npmjs.com/package/@qvac/transcription-parakeet
- Nemotron streaming: https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b ; https://arxiv.org/abs/2604.14493
- Kyutai: https://github.com/kyutai-labs/delayed-streams-modeling ; https://kyutai.org/stt ; slow-on-Mac issue https://github.com/kyutai-labs/delayed-streams-modeling/issues/123 ; https://github.com/jeanjerome/moshi-stt-apple-installer
- whisper.cpp: https://github.com/ggml-org/whisper.cpp/blob/master/examples/stream/README.md ; https://jacoblincool.github.io/smart-whisper/
- Integration/Electron: onnxruntime-node CPU-only https://github.com/microsoft/onnxruntime/issues/15226 ; WebGPU<CPU https://github.com/microsoft/onnxruntime/issues/27809 ; https://github.com/electron/rebuild ; PyInstaller codesign gotcha https://github.com/electron-userland/electron-builder/issues/3940
- Verified benchmarks: https://soniqo.audio/benchmarks
- Anchor: cm decision 019e9a41 (`~/.mdx/research/2026-06-local-voice-chat-realtime.md`)

## Open questions (measure locally, not researchable)
1. Actual endpoint→final for sherpa-onnx zipformer vs Moonshine-Tiny on Stuart's specific M-series — no public number exists.
2. Can Kyutai's 4×-RT flush trick actually sustain on this Mac, given issue #123? Only worth it if you want its semantic VAD.
3. Does `@qvac/transcription-parakeet` deliver real in-process streaming + EOU (would make Parakeet a Node-native option without a sidecar)?
4. Silero VAD silence-hangover tuning floor — how low before false endpoints hurt dictation usability.
