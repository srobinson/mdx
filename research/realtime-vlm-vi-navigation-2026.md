---
title: Real-Time VLM Inference for Visually Impaired Navigation (2025-2026)
type: research
tags: [vlm, vision-language-model, accessibility, navigation, on-device-inference, mobile-ai, assistive-technology]
summary: Comprehensive analysis of on-device and cloud VLM inference feasibility for real-time VI navigation, covering model benchmarks, existing products, hybrid architectures, and audio feedback patterns.
status: active
source: deep-research
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Executive Summary

On-device VLM inference has crossed a practical threshold for assistive navigation in 2025-2026. Sub-billion parameter models (SmolVLM-500M, FastVLM-0.5B, Florence-2-base at 0.23B) can run on modern phones with time-to-first-token under 1 second, while dedicated object detectors (YOLOv11) achieve 17-30 FPS on mobile GPUs. Cloud VLMs via streaming APIs (OpenAI Realtime, Gemini 3 Flash) deliver first-token latencies of 250-500ms over stable connections. The viable architecture for real-time VI navigation is a hybrid: lightweight on-device detection for immediate spatial awareness (obstacles, doors, stairs) combined with cloud VLM calls on keyframes for richer scene understanding. Every major shipping product in this space (Be My Eyes, Seeing AI, Google Lookout, Envision) uses this general pattern, though most lean heavily on cloud inference today.

## 1. On-Device VLM Inference

### Model Landscape and Benchmarks

| Model | Parameters | TTFT (mobile) | Decode Speed | Notes |
|-------|-----------|---------------|--------------|-------|
| SmolVLM-256M | 256M | ~1s (est.) | 2-3k tok/s (MacBook WebGPU) | Smallest video-capable VLM; <1GB RAM |
| SmolVLM-500M | 500M | ~1s (est.) | 2-3k tok/s (MacBook WebGPU) | 1.23GB GPU RAM; strong OCR (61%) |
| Florence-2-base | 230M | Sub-second (est.) | Fast | Detection + grounding + captioning; ONNX optimized |
| FastVLM-0.5B (Apple) | 500M | 85x faster than LLaVA-OV-0.5B | Real-time on iPhone 16 Pro | CVPR 2025; hybrid vision encoder (FastViTHD) |
| MobileVLM 1.7B | 1.7B | ~2-3s | 21.5 tok/s (Qualcomm CPU), 65.3 tok/s (Jetson) | Matches 3B-scale VLMs |
| Moondream2 | 1.8B | 3.8-5.2s (mobile, varies by quant) | Moderate | <5GB memory; runs on Raspberry Pi (slowly) |
| Phi-4-Multimodal | 5.6B | Moderate | ONNX optimized | 128K context; too large for real-time mobile camera |
| OmniVLM | <1B | 8x faster TTFT than baselines | Good | Token compression: 729 to 81 visual tokens |

**Key takeaway**: For real-time camera frame processing (1-5 FPS target), only sub-1B models are viable on current phones. SmolVLM-500M, FastVLM-0.5B, and Florence-2-base are the frontrunners. Models above 1.5B have multi-second TTFT that rules out continuous camera processing.

### Hardware Capabilities (2025-2026)

| Device | NPU TOPS | LLM tok/s (text) | Notes |
|--------|----------|-------------------|-------|
| iPhone 16/17 Pro (A18/A19 Pro) | ~35 TOPS | ~136 tok/s (Cactus benchmark) | ANE + Core ML; FastVLM optimized |
| Galaxy S25 Ultra (Snapdragon 8 Elite) | ~60 TOPS | ~91 tok/s | Hexagon NPU; ExecuTorch VLM support |
| Pixel 10 (Tensor G5) | ~50 TOPS (est.) | Gemini Nano v3 on-device | ML Kit GenAI APIs |

**Inference frameworks**: ExecuTorch 1.0 GA (Meta, Oct 2025) with Core ML backend; Cactus (YC-backed, sub-50ms TTFT claimed); Nexa SDK (cross-platform GPU/NPU/CPU); ONNX Runtime Mobile.

### On-Device Object Detection (YOLO)

For immediate spatial awareness, dedicated detectors remain superior to VLMs:

- **YOLOv11/YOLO26**: 17-30 FPS on modern phones; <10ms per frame on GPU
- **YOLObile**: 19.1 FPS on Samsung Galaxy S20 (2020 hardware)
- Custom training for navigation-relevant classes (doors, stairs, obstacles, curbs, vehicles) is well-supported via Ultralytics tooling

This is the layer that provides the "twitch reflex" spatial feedback a VI user needs for safe navigation.

## 2. Cloud VLM Streaming Latency

### API Response Times

| Provider/Model | First-Token Latency | Throughput | Vision Support | Notes |
|----------------|---------------------|------------|----------------|-------|
| OpenAI Realtime (GPT-4o) | 250-500ms (WebRTC) | ~116 tok/s | Yes (images via data channel) | Voice round-trip <320ms; live camera demo exists |
| Gemini 3 Flash | ~200-400ms (est.) | ~250 tok/s | Native multimodal | 3x faster than 2.5 Pro; $0.50/1M input tokens |
| GPT-4.1 mini | ~150-300ms (est.) | Higher than 4o | Yes | Half the latency of GPT-4o, similar intelligence |
| Claude 4.5 Sonnet | ~300-600ms (est.) | ~82 tok/s | Yes | Downscales images >1568px; optimize image size |

### Practical Round-Trip for Camera Frame

A realistic pipeline: capture frame (10ms) -> JPEG compress at 512px (5ms) -> upload via WebSocket/WebRTC (50-150ms on LTE) -> model inference to first token (200-500ms) -> stream tokens -> TTS first chunk (100ms on-device).

**Total latency estimate: 500ms-1.5s for first audio output** depending on network conditions and model choice.

This is too slow for obstacle avoidance but adequate for scene description on keyframes ("What's in front of me?"). The OpenAI Realtime API with WebRTC is the lowest-latency option, with demonstrated sub-1s camera-to-voice response.

### Cost Considerations

At 1 FPS continuous processing with Gemini 3 Flash (cheapest frontier model):
- ~500 tokens/image input + ~100 tokens output = ~600 tokens/frame
- 1 FPS = 3,600 frames/hour = 2.16M tokens/hour
- Cost: ~$1.08/hour input + ~$1.08/hour output = ~$2.16/hour

Continuous streaming is expensive. Keyframe-triggered cloud calls (every 5-10 seconds, or on scene change) reduce this to ~$0.10-0.40/hour.

## 3. Hybrid Architectures

### The Emerging Pattern: SpotVLM / Context Transfer

The most promising academic architecture is **SpotVLM** (2025), which formalizes the hybrid approach:

- **Edge tier**: Small VLM (Qwen-VL-2.5-3B or MiniCPM-o-2.6-int4) processes every frame
- **Cloud tier**: Large VLM (Qwen-VL-2.5-72B or GPT-4o) processes keyframes asynchronously
- **Context Transfer**: When cloud responses arrive late (up to 9 second delays tolerated), they are repurposed as contextual priors for the edge model via:
  - **Context Replacement Module**: Injects high-quality cloud descriptions as historical context
  - **Visual Focus Module**: Uses cloud model's grounding to direct edge model's attention to relevant regions

This achieves strong performance even with significant cloud latency fluctuations.

### Distributed VLM Architecture (Columbia University, 2025)

A simpler split: vision encoder runs on edge, language decoder runs in cloud. Achieves 33% throughput improvement over cloud-only. The edge device transmits visual feature embeddings (much smaller than raw frames) to the cloud.

### Practical Hybrid for VI Navigation

**Tier 1 - Immediate (on-device, <50ms)**:
- YOLO for obstacle/door/stair detection
- ARKit/ARCore depth sensing for distance estimation
- Haptic + spatial audio alerts

**Tier 2 - Fast (on-device VLM, 200ms-1s)**:
- SmolVLM-500M or FastVLM-0.5B for quick scene captioning
- Triggered on scene changes or user request
- Provides brief descriptions: "hallway with door on left"

**Tier 3 - Rich (cloud VLM, 1-3s)**:
- GPT-4o Realtime or Gemini 3 Flash for detailed understanding
- Triggered on keyframes, user questions, or complex scenes
- Reads signs, identifies businesses, describes people, answers questions

## 4. Existing Products and Their Technical Approaches

### Be My Eyes + GPT-4 Virtual Volunteer

- **Architecture**: Cloud-only. Camera frame sent to OpenAI GPT-4o API. TTS response played back.
- **Latency**: Multi-second for scene descriptions (not real-time continuous)
- **Interaction model**: User-initiated ("What do I see?") rather than continuous
- **Also supports**: Live video calls with human volunteers as fallback
- **Smart glasses**: Integrated with Ray-Ban Meta glasses for hands-free operation

### Microsoft Seeing AI (iOS)

- **Architecture**: Hybrid on-device + cloud. On-device for text recognition, face detection, currency identification, distance estimation. Cloud for richer scene descriptions.
- **Latency**: On-device features are near-instantaneous. Scene description takes several seconds.
- **Unique features**: Facial recognition (learns and identifies known people), reports distance to detected faces
- **Platform**: iOS only

### Google Lookout (Android)

- **Architecture**: Primarily on-device. Does not require internet connection for core features.
- **Key capability**: "Find" mode scans surroundings for objects (doors, bathrooms, cups, vehicles) and reports direction and distance using phone sensors
- **Latency**: Real-time for object detection; scene description takes a few seconds
- **2025 update**: TalkBack uses Gemini Nano on-device for rich image descriptions, working fully offline

### Envision (App + Smart Glasses)

- **Architecture**: Cloud-based for AI features (uses OpenAI GPT-5 for "Ask Envision" document Q&A)
- **Hardware**: Envision Glasses built on Google Glass Enterprise Edition 2
- **Features**: OCR in 60+ languages, face recognition, scene description, object detection
- **Latency**: Not publicly benchmarked; cloud-dependent features have multi-second delays
- **Price**: ~$3,500 for glasses

### Ray-Ban Meta Smart Glasses

- **Architecture**: All processing on paired phone/cloud. Glasses are camera + speaker + mic.
- **Interaction**: "Hey Meta, look and describe what's in front of me"
- **Live mode** (US beta): Continuous camera analysis without manual triggering
- **Latency**: Response in "under a second" for simple queries (per demonstrations)
- **Integration**: Be My Eyes available for human volunteer calls through glasses
- **Adoption**: New York Commission distributes to blind students/workers (as of Sept 2025)

### AIDEN (Research System, 2025)

- **Architecture**: YOLO v8 on server GPU (GTX 1080Ti) + LLaVA on A40 GPU + TTS
- **Measured latencies**:
  - Scene description: 7.34s server / 10.10s end-to-end
  - OCR: 7.09s server / 9.54s end-to-end
  - Object finding: 0.23s server / 0.51s end-to-end (~2 FPS)
- **Unique**: Geiger-counter haptic metaphor for object centering (frequency increases as phone approaches target)
- **Hardware**: Tested on LG G6 (2017 phone); modern hardware would improve significantly

## 5. Audio Feedback Patterns

### Modalities

| Method | Pros | Cons |
|--------|------|------|
| **Bone conduction** | Ears open for environmental awareness; safe for navigation | Poor vertical audio localization; lower fidelity |
| **Open-ear speakers** (Ray-Ban Meta style) | Non-intrusive; social acceptable | Audio leakage; poor in noisy environments |
| **Single earbud** (pass-through) | Affordable; decent quality | Blocks one ear partially |
| **Spatial audio** (AirPods Pro) | 3D positioning; excellent quality | Blocks environmental sound (even with transparency mode) |

### Feedback Patterns

**Continuous ambient**: Low-priority background sonification of surroundings. Research shows bone conduction binaural systems can convey horizontal direction effectively. Vertical position conveyed via pitch modulation. Current systems are "not yet sufficient for practical navigation of a blind person walking alone in a city" per PMC review.

**Interrupt-driven**: Alerts triggered by detected hazards. More practical. Used by Google Lookout's Find mode and AIDEN's obstacle detection. Haptic pulses for proximity (Geiger counter pattern). Voice alerts for high-priority items.

**On-demand**: User-initiated scene descriptions. The dominant pattern in shipping products (Be My Eyes, Seeing AI, Envision). Lowest cognitive load. Allows user to control information flow.

### TTS Latency

- **On-device TTS**: ~100ms first-chunk latency (Picovoice Orca benchmark). 6.5x faster than fastest cloud TTS.
- **Cloud TTS** (ElevenLabs, etc.): 300-800ms first-chunk depending on provider
- **Bluetooth overhead**: Adds 150-250ms to any audio path
- **Conversational threshold**: >200ms delay feels awkward; >500ms breaks natural rhythm

**Recommendation**: On-device TTS is mandatory for real-time feedback. Cloud TTS acceptable only for longer scene descriptions where the user is already waiting.

## 6. Apple/Google Platform Capabilities

### Apple (iOS)

**ARKit + LiDAR**:
- Depth maps at 60 FPS from LiDAR Scanner (iPhone Pro models)
- Scene Geometry: 3D mesh with semantic classification (walls, floors, ceilings, doors, windows, seats)
- Instant surface detection on feature-poor surfaces
- Door Detection in Magnifier: detects open/closed state, handle type, signs/symbols, distance. Built-in accessibility feature.
- RoomPlan API: Parametric 3D room scanning

**Core ML + Neural Engine**:
- ~35 TOPS on A19 Pro
- ExecuTorch Core ML backend for PyTorch VLMs
- ~33 tok/s decode on M1 Max (phone figures slightly lower)
- FastVLM optimized specifically for Apple silicon

**Accessibility APIs**:
- VoiceOver provides system-level screen reader
- UIAccessibility framework for custom announcements
- AVSpeechSynthesizer for on-device TTS with minimal latency

### Google (Android)

**ARCore**:
- Depth API using ToF sensors or dual cameras
- Scene Semantics (outdoor): sky, building, terrain, vegetation classification
- Geospatial API: Precise outdoor positioning using Google Street View data
- No equivalent to Apple's Door Detection built-in

**ML Kit + Gemini Nano**:
- Gemini Nano v3 on Pixel 10 (Tensor G5)
- GenAI APIs launched at I/O 2025
- TalkBack uses Gemini Nano for on-device image descriptions
- Fully offline operation
- Expanding to non-Pixel devices with Android 9+ and 2GB+ RAM

**Accessibility APIs**:
- TalkBack is the system screen reader
- Accessibility Service API for custom overlays
- Android TextToSpeech API for on-device synthesis

### Platform Comparison for VI Navigation

| Capability | Apple (iPhone Pro) | Google (Pixel 10) |
|-----------|-------------------|-------------------|
| LiDAR depth | Yes (hardware) | No (software depth only on most devices) |
| On-device VLM | FastVLM via Core ML | Gemini Nano via ML Kit |
| Door detection | Built-in (Magnifier) | Not built-in |
| Scene mesh | ARKit Scene Geometry | ARCore Scene Semantics (outdoor only) |
| Accessibility TTS | AVSpeechSynthesizer | Android TTS |
| NPU | ~35 TOPS (A19 Pro) | ~50 TOPS (Tensor G5, est.) |

Apple has a significant lead in hardware depth sensing (LiDAR) and built-in accessibility features (Door Detection). Google has an edge in on-device generative AI (Gemini Nano) and outdoor geospatial positioning.

## Sources Consulted

### Academic Papers
- [AIDEN: Design and Pilot Study of an AI Assistant for the Visually Impaired](https://arxiv.org/html/2511.06080) - Detailed latency measurements
- [SpotVLM: Cloud-edge Collaborative Real-time VLM](https://arxiv.org/html/2508.12638v1) - Hybrid architecture with context transfer
- [Distributed VLMs: Cloud-Edge Collaboration](https://wimnet.ee.columbia.edu/wp-content/uploads/2025/04/DistributedVLMs_Efficient_Vision-Language_Processing_through_Cloud-Edge_Collaboration.pdf) - Columbia University
- [SmolVLM: Redefining small and efficient multimodal models](https://arxiv.org/html/2504.05299v1) - HuggingFace
- [FastVLM: Efficient Vision Encoding for VLMs](https://machinelearning.apple.com/research/fast-vision-language-models) - Apple ML Research, CVPR 2025
- [AI-Powered Assistive Technologies for Visual Impairment](https://arxiv.org/html/2503.15494v1) - Survey paper
- [Bone Conduction Auditory Navigation Device](https://www.mdpi.com/2076-3417/11/8/3356)
- [Review of Navigation Assistive Tools for the Visually Impaired](https://pmc.ncbi.nlm.nih.gov/articles/PMC9606951/)

### Product Documentation & Reviews
- [Be My Eyes on Ray-Ban Meta Glasses](https://www.bemyeyes.com/be-my-eyes-smartglasses/)
- [AFB Review: Ray-Ban Meta AI Glasses for Low Vision](https://www.afb.org/aw/fall2025/meta-glasses-review)
- [Blind User Meta Ray-Ban Review](https://www.timdixon.net/blog/2025/04/blind-meta-ray-ban-review-2025/)
- [Apple Door Detection](https://www.apple.com/sa/newsroom/2022/05/apple-previews-innovative-accessibility-features/)
- [Google Lookout App](https://play.google.com/store/apps/details?id=com.google.android.apps.accessibility.reveal)
- [Envision Smart Glasses](https://www.letsenvision.com/glasses/home)
- [Seeing AI - Guide Dogs UK](https://www.guidedogs.org.uk/getting-support/information-and-advice/how-can-technology-help-me/apps/seeing-ai/)

### Developer Platforms & APIs
- [OpenAI Realtime API with WebRTC](https://platform.openai.com/docs/guides/realtime-webrtc)
- [Gemini 3 Flash](https://deepmind.google/models/gemini/flash/)
- [ExecuTorch](https://executorch.ai/)
- [Gemini Nano on Android](https://android-developers.googleblog.com/2025/08/the-latest-gemini-nano-with-on-device-ml-kit-genai-apis.html)
- [Apple ARKit](https://developer.apple.com/augmented-reality/arkit/)
- [Claude Vision API](https://platform.claude.com/docs/en/build-with-claude/vision)

### Engineering Blogs & Analysis
- [On-Device LLMs: State of the Union, 2026](https://v-chandra.github.io/on-device-llms/)
- [Picovoice: iOS Real-Time TTS](https://picovoice.ai/blog/ios-streaming-text-to-speech/)
- [Picovoice: TTS Latency](https://picovoice.ai/blog/text-to-speech-latency/)
- [Cactus: Cross-Platform LLM Inference on Mobile](https://www.infoq.com/news/2025/12/cactus-on-device-inference/)
- [OpenAI Realtime + GPT-4o Vision Agents](https://skywork.ai/blog/agent/openai-realtime-gpt-4o-vision-build-multimodal-voice-agents-2025/)

### HackerNews Discussions
- [FastVLM HN Discussion](https://news.ycombinator.com/item?id=43968897)
- [Apple Intelligence Foundation Models](https://news.ycombinator.com/item?id=44596275)

## Source Quality Assessment

**High confidence**: On-device model benchmarks (published papers with reproducible results), Apple/Google platform capabilities (first-party documentation), AIDEN latency measurements (controlled study with specific numbers).

**Medium confidence**: Cloud API latency figures (vary significantly by region, load, and time of day; numbers cited are typical rather than guaranteed). Product architecture descriptions (inferred from public information, not confirmed by vendors). Cost estimates (based on current pricing, subject to change).

**Low confidence**: Specific FPS claims for VLMs on phones (few published mobile-specific VLM benchmarks exist; most numbers are extrapolated from desktop/server results). Gemini Nano vision capabilities on Android (limited public benchmarking of on-device multimodal Nano).

**Gap**: No published head-to-head benchmark of multiple VLMs running on the same phone hardware with consistent methodology. The MobileAIBench framework is the closest, but its VLM coverage is limited to Moondream2.

## Open Questions

1. **FastVLM on-device FPS**: Apple demonstrated FastVLM-0.5B on iPhone 16 Pro but has not published frame-rate benchmarks for continuous camera processing. What is the sustained FPS for captioning camera frames?

2. **Gemini Nano multimodal quality**: Google claims Gemini Nano handles image understanding on-device, but independent benchmarks of its vision quality versus SmolVLM/FastVLM are absent.

3. **Battery impact**: No published data on battery drain for continuous on-device VLM inference + camera + LiDAR. This is a critical factor for a navigation app that must run for hours.

4. **Latency under movement**: All benchmarks assume stationary or controlled conditions. How does inference quality degrade with motion blur from walking?

5. **Optimal keyframe selection**: When running a hybrid architecture, what triggers should select frames for cloud processing? Scene change detection, user request, time interval, or detection of unrecognized objects?

6. **Spatial audio effectiveness**: Published research says bone conduction spatial audio is "not yet sufficient for practical navigation." Has this improved with AirPods Pro spatial audio or newer bone conduction hardware?

## Actionable Takeaways

1. **Start with YOLO + ARKit/LiDAR for Tier 1**: This provides the immediate obstacle/door/stair detection at 17-30 FPS that a walking user needs. This layer should never depend on network connectivity.

2. **Use SmolVLM-500M or FastVLM-0.5B for on-device captioning**: These models fit within phone memory constraints and can provide brief scene descriptions in under 1 second. Florence-2-base is an alternative if grounding/detection is more important than open-ended captioning.

3. **Route keyframe cloud calls through Gemini 3 Flash**: Best cost/latency ratio for rich scene understanding. Use OpenAI Realtime API if voice-first interaction is the primary modality.

4. **Mandatory on-device TTS**: 100ms first-chunk latency versus 300-800ms for cloud. Non-negotiable for real-time haptic/audio feedback.

5. **iPhone Pro is the preferred initial platform**: LiDAR depth, built-in Door Detection, FastVLM/Core ML optimization, and stronger accessibility ecosystem make it the better starting point.

6. **Adopt interrupt-driven feedback as default**: Continuous sonification is cognitively overwhelming and technically immature. Alert on hazards, describe on request, narrate on significant scene changes.

7. **Budget for hybrid cost**: Keyframe cloud calls every 5-10 seconds at ~$0.10-0.40/hour is sustainable. Continuous 1 FPS cloud processing at ~$2/hour is not.
