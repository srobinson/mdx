---
title: Speak Easy Current Voice Runtime Architecture
type: research
tags: [speak-easy, voice, browser, stt, llm, tts, realtime, architecture]
summary: Source verified trace of the committed browser voice runtime at e3fbe641 and the uncommitted Mercury cascade experiment.
status: active
source: codebase-analyst
confidence: high
created: 2026-08-14
updated: 2026-08-14
---

# Executive Summary

Speak Easy is a TypeScript pnpm monorepo that turns browser microphone audio into a spoken response through local Sherpa STT and one of two responder shapes: a Cerebras plus TTS cascade, or OpenAI Realtime used as a fused text to audio responder. `ConversationLoop` is the runtime owner for state, local history, metrics, interruption, and host neutral events. The browser package owns capture, WebSocket transport, playback, and UI projection.

The committed browser defaults to OpenAI Realtime, but still performs local STT and sends text to OpenAI. The current `experiment/cascade-models` worktree adds Mercury 2 as a browser selectable cascade, factors the duplicated OpenAI compatible SSE client into one adapter, and broadens recovery for a Realtime cancellation race. All local unit tests and type checks pass. Live provider tests remain skipped.

# Snapshot and Method

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/speak-easy`
- Branch: `experiment/cascade-models`
- Committed baseline: `e3fbe6415d8149c02daaf4c9110c31d9034aae6e`
- Worktree: 14 modified tracked files and 3 untracked files.
- Baseline size: 112 tracked files, 98 under `packages/`, and 12,242 tracked TypeScript or JavaScript lines.
- FMM was attempted first. No `.fmm.db` exists, so structural analysis fell back to Git, filesystem inventory, source reads, import searches, and package tooling.
- Reference convention: `HEAD:path:lines` names committed source at `e3fbe641`. `WORKTREE:path:lines` names the current uncommitted experiment.

# Project Metadata

| Item | Value |
|---|---|
| Language | TypeScript for Node runtime, vanilla JavaScript for the browser UI and AudioWorklets |
| Runtime | Node `>=22.6.0`; source executes directly as ESM |
| Build | pnpm workspace, TypeScript `5.9.3`, `tsc --noEmit` |
| Framework | No browser framework. DOM, Web Audio, AudioWorklet, HTTP, and WebSocket APIs |
| Test runner | Node test runner through `node --test` |
| Primary entry points | `pnpm browser`, `pnpm convo`, `pnpm demo`, `pnpm bench`, `pnpm tts` |
| Browser host | Loopback HTTP and WebSocket server at port 4317 by default |

The root scripts and runtime constraint are defined in `HEAD:package.json:5-17`. Every package uses strict NodeNext TypeScript with ES2023 and no emit.

## Package boundaries

```text
browser-voice
  -> convo-engine
       -> speech-io
       -> llm
       -> ws
  -> ws

speech-io -> sherpa-onnx-node, onnxruntime-node, llama-tokenizer-js
llm       -> platform fetch and no production npm dependency
```

- `@speakeasy/speech-io` owns STT, TTS, model assets, rewriting, capture helpers, benchmarks, and terminal audio helpers. Its public surface is centralized in `HEAD:packages/speech-io/src/index.ts:11-80`.
- `@speakeasy/llm` owns the provider neutral `ChatModel` contract and, at HEAD, the Cerebras adapter. The contract is text only: `ChatMessage[]` in and text deltas out. See `HEAD:packages/llm/src/contract.ts:12-30`.
- `@speakeasy/convo-engine` owns `ConversationLoop`, state, local history, metrics, responder abstraction, and the shared composition root. Its dependency boundary is visible in `HEAD:packages/convo-engine/src/loop.ts:33-74` and `HEAD:packages/convo-engine/src/runtime.ts:35-56`.
- `@speakeasy/browser-voice` owns the browser host, WebSocket protocol, browser audio adapters, AudioWorklets, and presentation. One browser socket owns one `BrowserConversationSession` and one loop. See `HEAD:packages/browser-voice/src/session.ts:20-40`.

# Architecture

## Ownership map

| Concern | Owner | Evidence |
|---|---|---|
| Engine selection and construction | `createConversationRuntime` | `HEAD:packages/convo-engine/src/runtime.ts:41-56` |
| Conversation state | `ConversationLoop` and `state.ts` | `HEAD:packages/convo-engine/src/loop.ts:76-111`, `HEAD:packages/convo-engine/src/state.ts:15-33` |
| Local prompt history | `ChatHistory` inside `ConversationLoop` | `HEAD:packages/convo-engine/src/history.ts:9-49`, `HEAD:packages/convo-engine/src/loop.ts:84-85` |
| Per turn metrics | `ConversationLoop` plus `metrics.ts` | `HEAD:packages/convo-engine/src/loop.ts:328-358`, `HEAD:packages/convo-engine/src/metrics.ts:10-47` |
| Host neutral observation | `ConversationEvent` | `HEAD:packages/convo-engine/src/events.ts:9-22` |
| Browser capture and playback | Browser UI, AudioWorklets, browser audio adapters | `HEAD:packages/browser-voice/public/app.js:479-527`, `HEAD:packages/browser-voice/src/browser-audio.ts:7-129` |
| STT decoding and endpointing | `SherpaEngine` and `SherpaSession` | `HEAD:packages/speech-io/src/engines/sherpa.ts:57-93`, `HEAD:packages/speech-io/src/engines/sherpa.ts:97-192` |
| Response generation | `VoiceResponder` implementation | `HEAD:packages/convo-engine/src/responder/contract.ts:23-41` |
| Browser session lifecycle and wire validation | `BrowserConversationSession` and `protocol.ts` | `HEAD:packages/browser-voice/src/session.ts:43-95`, `HEAD:packages/browser-voice/src/protocol.ts:41-100` |

## Committed end user voice path

### 1. Launch and runtime selection

`pnpm browser` executes `packages/browser-voice/src/server.ts`. The entry point loads `.env`, reads a bounded set of settings, and defaults the browser responder to `realtime`. It accepts responder, TTS engine, model, TTS model, and voice from environment variables. See `HEAD:packages/browser-voice/src/server.ts:5-31`.

`startBrowserVoiceServer` binds only `127.0.0.1`, serves a fixed static asset allowlist, exposes `/health`, accepts `/voice` WebSocket upgrades from the same origin, and permits one active local voice session. See `HEAD:packages/browser-voice/src/host.ts:36-108` and `HEAD:packages/browser-voice/src/host.ts:110-155`.

The host injects `createConversationRuntime` into the socket session. That composition root always prepares a Sherpa STT engine and applies the single final transcript rewrite decorator. It then builds either OpenAI Realtime or the Cerebras plus TTS cascade. See `HEAD:packages/convo-engine/src/runtime.ts:45-90`.

### 2. Browser microphone capture

Starting a room creates a mono `getUserMedia` stream with browser echo cancellation, noise suppression, and automatic gain control. The page loads capture and playback AudioWorklets, connects the capture graph through a silent gain node, and connects playback to the audio destination. See `HEAD:packages/browser-voice/public/app.js:479-505`.

`SpeakEasyCapture` downsamples the browser context rate to 16 kHz and emits 20 ms `Float32Array` frames. A frame contains 320 samples and occupies 1,280 bytes. The common 48 kHz case averages each group of three source samples. Other rates use linear interpolation. See `HEAD:packages/browser-voice/public/capture-worklet.js:1-55`.

The page sends the transferred sample buffer as a binary WebSocket message only when the room is ready, unmuted, and, in hold mode, actively capturing. See `HEAD:packages/browser-voice/public/app.js:506-516`.

### 3. Browser protocol and STT ingestion

The browser start command carries mode, pause duration, Realtime voice, barge setting, and optional system prompt. Other commands stop, interrupt, commit manual input, or acknowledge playback drain. See `HEAD:packages/browser-voice/src/protocol.ts:15-39`.

Binary client messages have no envelope. They are raw `Float32` PCM in the platform byte representation. `decodeMicFrame` copies and validates the frame, rejects empty, malformed, non finite, or over one second payloads, then the session forwards it through `BrowserAudioSource` into `ConversationLoop`. See `HEAD:packages/browser-voice/src/protocol.ts:102-119`, `HEAD:packages/browser-voice/src/session.ts:160-167`, and `HEAD:packages/browser-voice/src/browser-audio.ts:7-29`.

In `listening`, `ConversationLoop` forwards frames to `STTSession.pushAudio`. In `thinking` or `speaking`, it discards them unless barge detection is active, in which case they feed the energy VAD. See `HEAD:packages/convo-engine/src/loop.ts:191-209`.

### 4. Local STT and endpointing

The runtime uses a Sherpa online recognizer at 16 kHz. Each frame is accepted, decoded while ready, emitted as a revised partial, and checked for an endpoint. See `HEAD:packages/speech-io/src/engines/sherpa.ts:114-122` and `HEAD:packages/speech-io/src/engines/sherpa.ts:156-187`.

Natural mode configures eager endpointing and maps the browser pause setting to trailing silence. Hold mode configures manual endpointing. Releasing hold waits 200 ms for browser audio already in flight, then sends `commit-input`; the loop timestamps the endpoint and calls `STTSession.flush`. See `HEAD:packages/browser-voice/src/session.ts:120-131`, `HEAD:packages/browser-voice/public/hold-release.js:1-44`, and `HEAD:packages/convo-engine/src/loop.ts:148-155`.

`SherpaSession.flush` adds synthetic silence, decodes pending context, commits without closing the stream, and resets for the next utterance. Automatic commit emits `endpoint`, then `final`, then resets. See `HEAD:packages/speech-io/src/engines/sherpa.ts:124-153` and `HEAD:packages/speech-io/src/engines/sherpa.ts:170-187`.

The rewrite decorator passes partials through unchanged and rewrites only committed finals. See `HEAD:packages/speech-io/src/rewrite/decorator.ts:20-43`.

### 5. Turn creation, state, and history

On a nonempty final, the loop emits a final user transcript and serializes the turn on its promise queue. The turn moves to `thinking`, appends the user message to local history, and calls `ResponderSession.respond` with the system prompt plus the bounded conversation window. See `HEAD:packages/convo-engine/src/loop.ts:157-185`, `HEAD:packages/convo-engine/src/loop.ts:228-260`, and `HEAD:packages/convo-engine/src/history.ts:15-49`.

The legal states are `idle`, `listening`, `thinking`, and `speaking`. The transition table is enforced by `assertTransition`. See `HEAD:packages/convo-engine/src/state.ts:15-33`.

### 6A. OpenAI Realtime responder, the browser default

The adapter opens a server WebSocket, configures 24 kHz PCM audio output and the chosen voice, and installs the system prompt as session instructions. See `HEAD:packages/convo-engine/src/responder/openai-realtime.ts:70-102` and `HEAD:packages/convo-engine/src/responder/openai-realtime.ts:204-219`.

This is a text input Realtime integration. For each turn, it sends only the newest local user message as `input_text`, then sends `response.create`. OpenAI retains its conversation state on the socket. See `HEAD:packages/convo-engine/src/responder/openai-realtime.ts:221-246`.

The adapter routes events by response ID. Transcript deltas become `ResponderEvent` token records. Base64 PCM16 audio deltas become 24 kHz `Float32Array` `AudioSegment` records. A `response.done` ends the stream. See `HEAD:packages/convo-engine/src/responder/openai-realtime.ts:247-303`.

### 6B. Cerebras plus TTS cascade

The committed cascade constructs `CerebrasChatModel` and either Sherpa or Cartesia TTS. The shared runtime is the only engine selection location. See `HEAD:packages/convo-engine/src/runtime.ts:77-117`.

`CerebrasChatModel` posts the full local `ChatMessage[]` history to the OpenAI compatible chat completions endpoint and yields content from SSE `data:` frames. See `HEAD:packages/llm/src/cerebras.ts:41-97` and `HEAD:packages/llm/src/sse.ts:9-38`.

`CascadeSession` taps that text stream so token arrival timestamps remain accurate while the TTS session consumes it. It emits pending token events before each audio segment. See `HEAD:packages/convo-engine/src/responder/cascade.ts:40-69`.

Both Sherpa and Cartesia TTS use the same streaming segmentation and synthesis pipeline. It emits an aggressive first chunk at four words or an earlier clause boundary, then complete sentences. The one deep pipeline synthesizes the next segment while the consumer plays the current segment. See `HEAD:packages/speech-io/src/tts/stream.ts:54-140` and `HEAD:packages/speech-io/src/tts/stream.ts:314-365`.

### 7. Playback and browser drain acknowledgement

The first audio event moves the loop to `speaking`, creates an `AudioSink` at that segment rate, opens it, and writes every segment. See `HEAD:packages/convo-engine/src/loop.ts:252-288`.

`BrowserAudioSink` sends a JSON playback start event, then one binary packet per audio segment. The packet is 9 header bytes followed by `Float32` PCM: byte 0 is kind `1`, bytes 1 through 4 are a little endian playback ID, and bytes 5 through 8 are the sample rate. See `HEAD:packages/browser-voice/src/browser-audio.ts:58-74` and `HEAD:packages/browser-voice/src/protocol.ts:121-139`.

The page decodes the packet and transfers samples to `SpeakEasyPlayback`. The worklet linearly resamples from the input rate to the browser context rate, tracks source samples actually rendered, and reports `drained` after `end` or `clear`. See `HEAD:packages/browser-voice/public/app.js:455-477` and `HEAD:packages/browser-voice/public/playback-worklet.js:17-73`.

The browser sends `playback-drained` with playback ID and rendered source duration. The session resolves only the matching active sink. `ConversationLoop` therefore remains in `speaking` until browser consumption completes, then records the turn and returns to `listening`. See `HEAD:packages/browser-voice/public/app.js:518-525`, `HEAD:packages/browser-voice/src/session.ts:90-94`, and `HEAD:packages/convo-engine/src/loop.ts:288-321`.

### 8. Transcript, state, notices, and metrics

`ConversationLoop` emits one host neutral event union for state, user or assistant transcript, metrics, interruption, and notices. See `HEAD:packages/convo-engine/src/events.ts:9-22`.

The browser session forwards these as JSON. The page replaces revised user text, appends assistant deltas, replaces the assistant draft with the final reply, marks interrupted replies, and displays the latest three latency values. See `HEAD:packages/browser-voice/public/app.js:240-265`, `HEAD:packages/browser-voice/public/app.js:388-445`.

The loop records endpoint to final, endpoint to first token, and endpoint to first audio, plus token count and generated audio duration. Completed, uninterrupted turns enter the in memory metrics array. See `HEAD:packages/convo-engine/src/metrics.ts:10-47` and `HEAD:packages/convo-engine/src/loop.ts:328-358`.

## Interruption path

1. Escape, the main control, hold press during a reply, or sustained energy VAD can call `ConversationLoop.interrupt`. See `HEAD:packages/browser-voice/public/app.js:164-181` and `HEAD:packages/convo-engine/src/loop.ts:191-225`.
2. The loop marks the turn interrupted, asks the active sink to clear playback, passes the promise of rendered audio duration to the responder, resets VAD, returns to `listening`, and emits `interrupted`. See `HEAD:packages/convo-engine/src/loop.ts:216-226`.
3. `BrowserAudioSink.interrupt` sends `playback clear` and waits up to one second for the browser drain position. See `HEAD:packages/browser-voice/src/browser-audio.ts:76-83` and `HEAD:packages/browser-voice/src/browser-audio.ts:114-127`.
4. The Realtime responder sends `response.cancel`, waits for the browser rendered position, and truncates the remote assistant item to the lesser of played and delivered audio. The next response waits for truncation acknowledgement. See `HEAD:packages/convo-engine/src/responder/openai-realtime.ts:306-344` and `HEAD:packages/convo-engine/src/responder/openai-realtime.ts:346-417`.
5. The cascade responder has no explicit provider cancellation call. Breaking the consumer closes the local token and speech generators, and any prefetched synthesis rejection is swallowed. See `HEAD:packages/convo-engine/src/responder/cascade.ts:51-69` and `HEAD:packages/speech-io/src/tts/stream.ts:360-365`.
6. Interrupted assistant text is not appended to local `ChatHistory`, and interrupted turns produce no metrics. Realtime retains the played prefix remotely through truncation.

# Core Data Shapes

| Shape | Fields and semantics | Source |
|---|---|---|
| Mic frame | Raw 16 kHz mono `Float32Array`; normally 320 samples per 20 ms | `HEAD:packages/speech-io/src/contract.ts:35-56` |
| STT events | `partial {text}`, `final {text}`, `endpoint {}`, `error {err}` | `HEAD:packages/speech-io/src/contract.ts:24-52` |
| `ChatMessage` | `{ role: system or user or assistant, content: string }` | `HEAD:packages/llm/src/contract.ts:12-17` |
| `ResponderEvent` | token `{text, at}` or audio `{segment}` | `HEAD:packages/convo-engine/src/responder/contract.ts:21-37` |
| `AudioSegment` | index, sentence, Float32 samples, sample rate, readiness, synth duration, audio duration | `HEAD:packages/speech-io/src/tts/contract.ts:25-49` |
| Browser start command | mode, pause, Realtime voice, barge, optional system prompt | `HEAD:packages/browser-voice/src/protocol.ts:15-29` |
| Browser playback packet | kind, playback ID, sample rate, Float32 samples | `HEAD:packages/browser-voice/src/protocol.ts:121-139` |
| `ConversationEvent` | state, transcript, metrics, interrupted, notice | `HEAD:packages/convo-engine/src/events.ts:9-22` |
| `TurnMetrics` | turn, transcript, three endpoint anchored latencies, token count, spoken duration | `HEAD:packages/convo-engine/src/metrics.ts:21-47` |

# Key Patterns

1. **Dependency injection at the loop boundary.** STT, responder, microphone, and sink construction are injected. Tests can exercise the whole state machine without native models or provider calls.
2. **One response abstraction for two pipeline shapes.** `VoiceResponder` hides both the classic LLM plus TTS cascade and a fused text to audio model. The loop does not branch on provider.
3. **One composition root.** Host code delegates engine construction to `createConversationRuntime`, preventing browser and terminal wiring from diverging.
4. **Consumption acknowledgement.** Playback completion means audio consumed by the browser rather than bytes sent by the server. This makes speaking state and Realtime context truncation reflect local playback.
5. **Cancellation fencing.** Realtime events are tagged and filtered by response ID. The next turn waits for interrupted context truncation, reducing stale output contamination.
6. **Single TTS pipeline.** Sherpa and Cartesia share segmentation, silence trimming, pacing, timing, and one deep synthesis behavior.
7. **Boundary validation and redaction.** Browser commands, PCM frames, voices, ports, and credentials are validated at ingress or composition boundaries. Browser errors redact common provider key formats.

# Current Uncommitted Experiment

The experiment is on branch `experiment/cascade-models` with 14 modified tracked files and 3 untracked files.

## Added behavior

- A shared `OpenAICompatibleChatModel` now owns request assembly, SSE parsing, delta extraction, and error handling. Cerebras becomes a thin configuration subclass. See `WORKTREE:packages/llm/src/openai-compatible.ts:22-73` and `WORKTREE:packages/llm/src/cerebras.ts:1-35`.
- `MercuryChatModel` adds Inception Labs `mercury-2` with `reasoning_effort` constrained to `instant` or `low`. See `WORKTREE:packages/llm/src/mercury.ts:7-35`.
- `RuntimeConfig` gains `llmProvider` and `llmReasoningEffort`. `buildChatModel` selects Cerebras or Mercury behind the existing `ChatModel` and `CascadeResponder` seams. See `WORKTREE:packages/convo-engine/src/runtime.ts:31-43` and `WORKTREE:packages/convo-engine/src/runtime.ts:99-130`.
- The browser start protocol gains `engine` with `realtime`, `mercury-instant`, or `mercury-low`. The UI persists the selection and hides the Realtime voice field for Mercury. See `WORKTREE:packages/browser-voice/src/protocol.ts:15-36`, `WORKTREE:packages/browser-voice/public/index.html:167-180`, and `WORKTREE:packages/browser-voice/public/app.js:571-637`.
- `runtimeConfigFor` maps the browser engine to a fresh responder configuration while preserving shared TTS settings. See `WORKTREE:packages/browser-voice/src/session.ts:179-202`.
- Realtime cancellation recovery now recognizes `response_cancel_not_active` by code or canonical message, including cases where the server omits a usable correlation ID. See `WORKTREE:packages/convo-engine/src/responder/openai-realtime.ts:166-180` and `WORKTREE:packages/convo-engine/src/responder/openai-realtime.ts:434-438`.

## Experiment limitations

- The live Mercury timing test is opt in and was skipped by the normal suite. It measures only first text token latency and chunk count. It does not compare endpoint to first audio, quality, cost, failures, or interruption recovery. See `WORKTREE:packages/llm/src/mercury.test.ts:64-94`.
- The browser selection forces provider defaults. `runtimeConfigFor` removes `llmModel` before both Realtime and Mercury mapping, so `SPEAKEASY_MODEL` no longer changes the browser selected model in this experiment. See `WORKTREE:packages/browser-voice/src/session.ts:183-200`.
- Mercury runs through the existing cascade and whatever TTS engine is configured. The browser hides the voice control for Mercury, so voice remains an environment level cascade setting rather than a browser comparison control.
- The broader Realtime cancellation classifier deliberately swallows an uncorrelated no active response error. Tests cover session health, but this weakens error correlation and could hide a provider protocol fault with the same code or message.

# Surprising Coupling and Explicit Gaps

## 1. “Realtime” still depends on local STT

The OpenAI adapter sends `input_text` and requests audio output. Browser audio never goes to OpenAI. Every browser engine option therefore shares Sherpa STT, endpointing, and rewrite behavior. This is useful for model comparison, but the name can imply a full audio Realtime path that does not exist.

## 2. The default responder depends on the host

`createConversationRuntime` defaults to cascade, while the browser entry point explicitly defaults to Realtime. Terminal and browser behavior differ unless configuration is inspected. See `HEAD:packages/convo-engine/src/runtime.ts:59-79` and `HEAD:packages/browser-voice/src/server.ts:20-30`.

## 3. Local and remote history have different authorities

Cascade providers receive the bounded local `ChatHistory`. Realtime sends only the latest user text and relies on the socket conversation. On interruption, the local history omits the interrupted assistant output while the Realtime server stores a truncated played prefix. A later switch to cascade cannot reconstruct the exact remote context. See `HEAD:packages/convo-engine/src/loop.ts:289-310`, `HEAD:packages/convo-engine/src/responder/openai-realtime.ts:15-18`, and `HEAD:packages/convo-engine/src/responder/openai-realtime.ts:378-396`.

## 4. Browser acknowledgement controls engine progress

The server stays in `speaking` until the browser worklet reports drain. A missing acknowledgement stalls the turn until the 60 second sink timeout. This is correct consumption semantics with a strong runtime dependency on the browser worklet and WebSocket command path. See `HEAD:packages/browser-voice/src/browser-audio.ts:4-5` and `HEAD:packages/browser-voice/src/browser-audio.ts:86-99`.

## 5. Barge input loses its leading audio

During `thinking` or `speaking`, frames feed only the energy VAD. The frames that trigger interruption are not buffered or replayed to STT. Recognition resumes with later frames after state returns to `listening`, so the beginning of a barged utterance can be clipped. See `HEAD:packages/convo-engine/src/loop.ts:191-225`.

## 6. First audio metrics stop at the server boundary

`firstAudioAt` is stamped when the loop receives the first `AudioSegment`, before the browser packet, worklet queue, resampling, and audio device render. The field is described as first spoken word, but it currently measures response audio ready at the host. Playback start is not acknowledged. See `HEAD:packages/convo-engine/src/loop.ts:277-286` and `HEAD:packages/convo-engine/src/metrics.ts:21-30`.

## 7. Metrics exclude important outcomes

Interrupted, failed, and audio only turns are absent. `recordTurn` requires both first token and first audio. The browser shows only the latest completed turn, and no metrics or transcript survive reload. See `HEAD:packages/convo-engine/src/loop.ts:289-317`, `HEAD:packages/convo-engine/src/loop.ts:340-358`, and `HEAD:packages/browser-voice/public/app.js:440-445`.

## 8. Runtime state is ephemeral

Conversation state, prompt history, metrics, transcript DOM, and server side Realtime context are in memory. Browser `localStorage` contains settings only. Closing the socket, stopping the host, or reloading loses the conversation record. See `HEAD:packages/browser-voice/public/app.js:567-618` and `HEAD:packages/convo-engine/src/history.ts:15-49`.

## 9. Audio conversion is intentionally simple

Capture uses group averaging only for the common 48 kHz to 16 kHz ratio and linear interpolation otherwise. Playback also uses linear interpolation. There is no explicit band limited resampler. This keeps the browser path small, but quality can vary by hardware sample rate. See `HEAD:packages/browser-voice/public/capture-worklet.js:22-55` and `HEAD:packages/browser-voice/public/playback-worklet.js:44-63`.

## 10. Documentation lags the code

`DESIGN.md` still describes a three package workspace and says barge in is future work. The repository has four packages, a browser host, and committed barge behavior. `state.ts` also says v1 does not listen while speaking, while `ConversationLoop` routes those frames to VAD. See `HEAD:DESIGN.md:8-31`, `HEAD:DESIGN.md:89-110`, and `HEAD:packages/convo-engine/src/state.ts:1-12`.

# Dependencies

| Dependency | Role |
|---|---|
| `sherpa-onnx-node 1.13.3` | Local streaming STT and local Sherpa TTS bindings |
| `onnxruntime-node 1.27.0` | ONNX execution support used by speech tooling |
| `llama-tokenizer-js 1.2.2` | Tokenization support in speech benchmarks or tooling |
| `ws 8.21.1` | Local browser WebSocket server and OpenAI Realtime client |
| Platform `fetch` | Cerebras, Cartesia, and experimental Mercury HTTP calls |
| Browser Web Audio and AudioWorklet | Microphone capture, resampling, queueing, playback, and drain position |
| `ffmpeg` external executable | Terminal microphone capture, outside the browser path |

# Relevance to Helioy

The reusable architecture is the ownership split. One host neutral loop owns state, history, metrics, and interruption. Browser and terminal surfaces supply capture, playback, and event projection without duplicating conversation logic. The playback drain acknowledgement and Realtime truncation handshake are especially useful for any Helioy surface that needs its remote conversation state to match audio actually consumed by a user.

# Verification

Executed against the current worktree without modifying repository files:

- `git rev-parse HEAD`: `e3fbe6415d8149c02daaf4c9110c31d9034aae6e`
- `git diff --check`: passed
- `pnpm test`: 123 tests discovered, 120 passed, 3 live provider tests skipped, 0 failed
- `pnpm typecheck`: all four packages passed
- Final `git status --short`: unchanged from the initial 14 modified and 3 untracked experiment files

# Open Questions

1. Should barge capture keep a short pre roll and feed it into the fresh STT turn?
2. Should first audio latency be renamed to host audio ready, or should playback start receive its own browser acknowledgement?
3. Which history becomes authoritative if provider switching within one browser conversation becomes a product requirement?
4. Should the experiment preserve explicit model overrides, or intentionally lock every provider to a comparison model?
5. Should completed, interrupted, failed, and no reply outcomes share one metrics record so latency and reliability summaries cannot exclude failures?
6. Should `DESIGN.md` be updated to include `browser-voice`, current barge behavior, the `VoiceResponder` seam, and split local versus remote history ownership?
