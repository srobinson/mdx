---
title: Local-first real-time two-way voice chat — June 2026 landscape
date: 2026-06-06
scope: helioy
status: snapshot (fast-moving field, decays in ~3-4 months)
method: deep-research harness (27 sources fetched, 128 claims, 25 adversarially verified 3-vote, 24 confirmed / 1 killed, 109 agents)
related:
  - helioy-electron-baseline.md
tags: [voice, stt, tts, asr, speech-to-speech, mlx, cuda, local-first, barge-in, real-time]
---

# Local-first real-time two-way voice chat — June 2026

Research baseline for a local-first, sub-500ms, barge-in (interruptible) two-way voice chat app.
Two hardware targets in scope: Apple Silicon (MLX/Metal) and NVIDIA (CUDA/TensorRT/NeMo/vLLM).
Brain is hybrid: local LLM by default, cloud escalation for hard turns.

## The load-bearing architectural fork

Two of the requirements pull in opposite directions:

- **Hybrid brain** (local default + cloud escalate) requires a *text* seam in the middle, which means a **cascaded** pipeline: VAD -> STT -> LLM -> TTS. The transcript is where you swap local for cloud.
- **Sub-500ms barge-in** is best served by an **end-to-end speech-to-speech** model that removes the cascade.

You cannot fully have both in one path. Moshi gives ~200ms full-duplex but is a monolith with no swappable brain. A cascaded pipeline gives the hybrid brain and the cleanup hooks but pays serial latency at each stage.

**Verdict: cascaded pipeline tuned to the sub-600ms class is the v1 foundation. Reserve end-to-end S2S (Moshi) as a research spike, not the base.** The strongest verified open-source prior art already lives in the cascaded sub-600ms class.

## Three projects to clone or study first

| Project | Role | License | Why | What to take |
|---|---|---|---|---|
| [GLaDOS](https://github.com/dnhkng/GLaDOS) | clone first | open | Cascaded, explicitly targets <600ms, working barge-in, local Ollama or cloud LLM behind one OpenAI-compatible interface | Full plumbing: Silero VAD (ONNX, 32ms chunks, >0.8 trigger, 800ms pre-activation buffer) -> Parakeet TDT (ONNX) -> LLM -> Kokoro. Barge-in via `currently_speaking_event` + `stop_speaking()`, clipping the reply in conversation history at the interruption point |
| [TEN Framework](https://github.com/TEN-framework/ten-framework) | study | Apache-2.0 (components) | Modular orchestration supporting BOTH cascaded and realtime S2S; ships [ten-vad](https://github.com/TEN-framework/ten-vad) + [ten-turn-detection](https://github.com/TEN-framework/ten-turn-detection) | Interface design for swapping STT/LLM/TTS extensions (TMAN Designer, no code changes). The hybrid local/cloud brain-swap blueprint. `ten-turn-detection` is a fine-tuned Qwen2.5-7B classifier emitting finished/unfinished/wait |
| [Kyutai delayed-streams-modeling](https://github.com/kyutai-labs/delayed-streams-modeling) | study | open | Lowest-latency streaming STT + TTS with first-party MLX ports next to CUDA/Rust | The streaming primitives, and proof one model family covers both hardware targets |

The dual-hardware story is unusually clean: Kyutai (STT/TTS), Parakeet (via `parakeet-mlx`), Moshi, and Kokoro all have first-party or community MLX ports alongside their CUDA/NeMo/PyTorch homes. No disjoint dual stack to maintain.

## Model shortlist per stage

Figures carry a reliability tag. The verification pass flagged several vendor and best-case numbers; they are not laundered into fact here.

### STT / ASR (streaming)

| Model | Fastest | Accurate + streams | Params | Key numbers | Reliability |
|---|---|---|---|---|---|
| **Parakeet TDT 0.6b** | | sweet spot | 0.6B | Dual-target: NeMo/CUDA + `parakeet-mlx` streaming (StreamingParakeet, configurable left/right context). What GLaDOS ships | high |
| **Moonshine v2** | tightest TTFT | | 34M / 123M / 245M | Sliding-window attention = *constant* TTFT (O(Tw), not O(T^2)). M3: Tiny 50ms / Small 148ms / Medium 258ms. Medium ~6.65% WER | vendor preprint, Feb 2026 ([arXiv:2602.12241](https://arxiv.org/abs/2602.12241)) |
| **Kyutai STT 1b** | | + built-in semantic VAD | ~1B | `stt-1b-en_fr`, 0.5s delay, semantic VAD doubles as turn detection. First-party MLX (moshi-mlx, moshi-swift on iPhone 16 Pro). `stt-2.6b-en` = higher capacity, 2.5s delay | high |
| **WhisperKit Large-v3-Turbo** | | highest accuracy | ~1B | ~2.2% WER, ~0.45s/word on-device (Apple Silicon, Core ML/ANE), ties cloud Fireworks. Heavier | self-published ([arXiv:2507.10860](https://arxiv.org/html/2507.10860v1)); related ~2% streaming-WER claim **refuted 0-3** |

Higher absolute accuracy exists in non-streaming models (Canary Qwen 2.5B ~5.63% WER, Granite Speech 8B ~5.85%) but they break the latency budget.

### TTS (streaming, time-to-first-audio)

| Model | Fastest | Best quality that streams | Params | Key numbers | Reliability |
|---|---|---|---|---|---|
| **Kokoro 82M** | default | | 82M | MLX bf16/8/6/4-bit (all in mlx-community), 54 voices. Runs both targets. Canonical fast pick | high; no published e2e Apple-Silicon latency |
| **Kyutai Pocket TTS** | CPU-class | | 100M | ~200ms first-audio, ~6x realtime on M4, local voice cloning. Jan 2026 English-only; 6 languages added May 2026 | 2-1 on the multilingual conflation |
| **Kyutai TTS** | | yes | | Delayed-streams, ~220ms first-token-to-audio (~350ms batched L40S), cloning, first-party MLX | high ([arXiv:2509.08753](https://arxiv.org/abs/2509.08753)) |
| **Chatterbox Turbo** | (CUDA) | | 350M | Vendor: 75ms, 6x realtime, "streaming-ready". Independent benchmark: RTF ~0.499 on RTX 4090, **first-chunk ~472ms** | medium; 75ms is per-inference marketing, contradicted on loop latency |

Unified MLX runtime to build on: [mlx-audio](https://github.com/Blaizzy/mlx-audio) (MIT) runs Kokoro, CSM, Parakeet, Whisper, plus Voxtral Realtime (Mistral 4B streaming STT, configurable <500ms delay, Apache-2.0, Feb 2026).

### End-to-end S2S (the barge-in spike)

- **[Moshi](https://github.com/kyutai-labs/moshi)**: only S2S model shipping PyTorch/CUDA (24GB, no quant) AND MLX (M3, int4) AND Rust/Candle (bf16+int8). Theoretical 160ms (80ms Mimi frame + 80ms acoustic), "as low as 200ms" on L4 ([arXiv:2410.00037](https://arxiv.org/html/2410.00037v2), below the 230ms natural-conversation average). Models two concurrent audio streams + an "inner monologue" of text tokens; natively handles overlap/interruption. **Caveat: issue #229 reports latency drift toward ~1s+ over long sessions on L4.** Promising, not yet dependable for sustained chat.

### Turn-taking (the plumbing that makes it feel alive)

Raw VAD is no longer state of the art. Verified pattern is VAD for endpointing + a **semantic end-of-turn** model:

- **Silero VAD** (endpoint) + **[Pipecat Smart Turn v3](https://github.com/pipecat-ai/smart-turn)** (BSD-2): ~8M params (Whisper Tiny encoder + linear classifier), 8MB int8, 23 languages. 12ms on a fast CPU, 59.8ms on AWS c8g.medium, ~65ms Pipecat Cloud, <100ms most cloud. Classifies finished/unfinished from grammar, tone, pace, acoustic + semantic cues.
- Or TEN's `ten-vad` + `ten-turn-detection`.

## Latency budget (cascaded, either target)

```
turn/endpoint detect    ~10-100ms    Smart Turn / Silero
streaming STT TTFT      ~50-260ms    Moonshine v2 / Parakeet / Kyutai 0.5s
LLM TTFT                see below    <- dominant variable; decode overlaps TTS so TTFT is the serial cost
TTS time-to-first-audio ~200-220ms   Kokoro / Kyutai
```

Everything except the brain fits comfortably under 500ms. **The LLM TTFT is the entire budget question.** The follow-up pass (below) established the framing (TTFT-bound, not throughput-bound, because decode overlaps TTS) but found NO verified consumer-GPU TTFT number. End-to-end Moshi sidesteps the cascade at ~200ms best-case.

## Verdict on the cleanup-pass idea

The user's core idea (local first pass, then a fast model cleans up). The first pass returned zero evidence; **the follow-up pass (2026-06-06) closed this with evidence, see the dedicated section below**. Verdict: keep cleanup off the critical path. The engineering reasoning that follows was independently confirmed.

Both literal forms fight a barge-in loop:

- **ASR-transcript repair before the brain**: inserts a *second full LLM round-trip* on the critical path, ahead of the brain starting. Likely fatal for sub-500ms, and largely redundant since a modern brain LLM tolerates disfluencies. Belongs in a *turn-based* mode, not barge-in.
- **Draft-then-refine the reply**: only saves latency if you speak the draft immediately; waiting for the refiner doubles LLM latency, and correcting speech mid-utterance is jarring. A quality lever, not a latency lever, and it fights interruption.

**Reframe (recommended): the instinct is correct but maps onto the hybrid brain, not an extra serial hop.** The local model *is* the fast first pass. Cloud escalation *is* the cleanup. A cheap classifier on the turn decides which. The two models live in parallel branches selected per turn, never stacked in series on the hot path. If literal text cleanup is still wanted, the only place it survives the budget is off the critical path (speculative, or applied to already-streamed text for the next turn's context).

## Reference architectures

**Apple Silicon (MLX)** — runtime spine: `mlx-audio`
```
Mic -> Silero VAD + Smart Turn v3
    -> Parakeet TDT 0.6b (parakeet-mlx)   [or Moonshine v2 for tightest TTFT]
    -> local LLM (MLX/Ollama, OpenAI-compatible) <-> cloud escalation
    -> Kokoro 82M (4-6 bit)               [or Kyutai TTS for naturalness]
    -> Speaker, barge-in via stop-on-speech
```

**NVIDIA (CUDA)**
```
Mic -> Silero VAD + Smart Turn v3
    -> Parakeet TDT 0.6b (NeMo)           [or faster-whisper large-v3-turbo]
    -> local LLM (vLLM / TensorRT-LLM, OpenAI-compatible) <-> cloud escalation
    -> Kokoro                              [or Chatterbox Turbo, verify latency first]
    -> Speaker, barge-in
```
Optional CUDA research branch: Moshi end-to-end, to feel the ~200ms full-duplex ceiling before committing to the cascade.

## Follow-up pass (2026-06-06): the four critical-path gaps

Second deep-research pass, deliberately skeptical: 25 claims verified, 14 confirmed, **11 killed**. The kill rate is concentrated on consumer-GPU performance numbers.

### Gap 1 — Local LLM brain TTFT

- **Framing (high conf):** in a streaming cascaded pipeline the LLM decode overlaps TTS, so the serial critical-path cost is **TTFT (prefill-to-first-token), not tokens/sec**. Optimize for TTFT. Sources: arXiv 2508.04721, arXiv 2511.05502.
- **Apple Silicon (medium conf, single M2-Ultra preprint arXiv 2511.05502):** **MLC-LLM is latency-optimal for a chat brain** (lower TTFT on short/moderate prompts); **MLX wins sustained decode (~230 tok/s)**. Throughput ranking MLX > MLC (~190) > llama.cpp (~150) > Ollama (20-40) > PyTorch-MPS (~7-9). No Apple runtime implements chunked prefill, but that only hurts past ~100k context, moot for short turns. M5 Neural Accelerators reportedly ~4x TTFT.
- **Consumer NVIDIA (RTX 4090/5090) — LARGEST GAP, no surviving evidence:** every specific TTFT/throughput figure was **refuted** (Qwen3-8B "177ms on 5090" 1-2; NVFP4 sweet-spot 1-2; 411 tok/s decode 0-3; the H100 0.106s TTFT datapoint 0-3). No independently verified sub-300ms consumer-GPU TTFT number exists. **This is a benchmark-locally task, not a research task.**
- **4-bit "sweet spot":** de-facto practice (GGUF/AWQ/MLX) but its specific quality/latency claims were refuted. Treat 4-bit as the practical default pending local validation, not a verified optimum.

### Gap 2 — Per-turn local-vs-cloud routing policy

- **Load-bearing rule (3-0):** **route on the query before generating (pre-generation routing). Never route on a draft.** Uncertainty-based and cascade routers are post-generation and inherently off-path. Sources: arXiv 2603.04445, 2502.00409.
- **The on-the-fly-confidence shortcut was refuted (0-3):** cheap single-pass UQ signals (perplexity, p(True)) are NOT established as viable on the critical path. Do not assume on-path uncertainty routing is free.
- **Libraries (3-0):** RouteLLM (LMSYS/Berkeley, Apache-2.0, drop-in OpenAI replacement) and LLMRouter (UIUC, MIT, Dec 2025, 16+ routers). RouteLLM's "85% cost cut" is MT-Bench best-case/in-distribution; LLMRouterBench (Jan 2026) found many routers fail to beat a trivial baseline. Route for cost control with sober expectations.
- **Off-path (3-0):** cascade/RL-decomposition routers (Router-R1, R2-Reasoner) add seconds of latency (R2-Reasoner ~14s). Offline/turn-based only.

### Gap 3 — Cleanup-pass verdict (replaces prior "no evidence")

- **ASR transcript repair: off-path, turn-based only.** RLLM-CF (arXiv 2505.24347): modest gains (0.34-1.11% absolute WER), **~4x token cost**, no wall-clock latency ever measured. Small benefit, unquantified real-time cost.
- **Draft-then-refine via a second model call: off-path.** Multi-call cascade generation runs into seconds (see Gap 2). Incompatible with barge-in.
- **The one rescued nuance (open):** **in-runtime speculative decoding** (draft model proposes, big model verifies in one pass, same runtime) is a distinct technique, potentially latency-neutral/positive, NOT covered by any surviving claim. The only "fast draft + bigger model" form that could live on the hot path, and a refinement of the original idea worth a dedicated look.

### Gap 4 — End-to-end S2S durability (Moshi)

- **Unresolved.** No claim about Moshi's long-session drift (issue #229) or about an MLX+CUDA full-duplex alternative survived (or reached) verification. The cascaded recommendation stands by default. Needs a narrow pass aimed at issue #229 status and 2026 full-duplex releases.

## Remaining open questions (now benchmarking, not research)

1. **Measure consumer-GPU TTFT locally**: Qwen3 4B/8B, Gemma 3 4B on the actual RTX box via llama.cpp and vLLM, short prompt, log TTFT. All web figures were refuted.
2. **Measure Apple-Silicon short-prompt TTFT** for MLC vs MLX vs llama.cpp-Metal on M3/M4 (the preprint used M2 Ultra and reported decode, not TTFT).
3. **In-runtime speculative decoding** for short conversational turns on target hardware: does it reduce perceived latency? No direct evidence yet.
4. **Moshi issue #229**: fixed bug or fundamental limit, and any cross-platform full-duplex alternative.

## Coverage gaps and reliability caveats

- The CLEANUP ARCHITECTURE (the core idea) has zero verified claims either way. The verdict above is judgment, not evidence.
- HYBRID brain orchestration only partially covered: swappable OpenAI-compatible backend is demonstrated; no verified local-LLM TTFT figures or per-turn routing policy from a shipping app.
- Vendor/best-case numbers flagged: Moshi 200ms ("as low as", documented drift), WhisperKit 0.45s + Moonshine 6.65%/6x (self-published preprints), Chatterbox 75ms (marketing, ~472ms independent first-chunk), Pocket TTS CPU-realtime.
- One claim refuted 0-3: WhisperKit does NOT demonstrably hit ~2% streaming WER matching Deepgram.
- **No claims survived verification** for: full Pipecat framework, LiveKit Agents, Home Assistant Assist/Wyoming, Open WebUI, omi, june, Vocode, Amica, Sesame CSM, Orpheus, XTTS-v2, Piper, NVIDIA Canary, distil-whisper. Absence here is a corpus gap, not a negative assessment. A targeted follow-up would close it.

## Primary sources

- GLaDOS: https://github.com/dnhkng/GLaDOS , https://deepwiki.com/dnhkng/GLaDOS
- Moshi: https://github.com/kyutai-labs/moshi , https://arxiv.org/html/2410.00037v2
- TEN Framework: https://github.com/TEN-framework/ten-framework , /ten-turn-detection , /ten-vad
- Smart Turn: https://github.com/pipecat-ai/smart-turn , https://huggingface.co/pipecat-ai/smart-turn-v3
- Moonshine v2: https://arxiv.org/abs/2602.12241 , https://github.com/moonshine-ai/moonshine
- parakeet-mlx: https://github.com/senstella/parakeet-mlx
- Kyutai delayed-streams: https://github.com/kyutai-labs/delayed-streams-modeling , https://kyutai.org/tts , https://arxiv.org/abs/2509.08753
- Kyutai Pocket TTS: https://github.com/kyutai-labs/pocket-tts
- mlx-audio: https://github.com/Blaizzy/mlx-audio
- Kokoro: https://huggingface.co/hexgrad/Kokoro-82M
- WhisperKit: https://arxiv.org/html/2507.10860v1
- Chatterbox Turbo: https://www.resemble.ai/chatterbox-turbo/
- LiveKit turn detection: https://livekit.com/blog/turn-detection-voice-agents-vad-endpointing-model-based-detection
