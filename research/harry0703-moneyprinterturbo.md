---
title: MoneyPrinterTurbo (harry0703) — automated short-video generator, family baseline
type: research
tags: [video-generation, tts, llm-orchestration, streamlit, fastapi, moviepy, pipeline, comparative-baseline]
summary: The 77k-star original of the MoneyPrinter family; a config-driven Python pipeline (script -> terms -> TTS -> subtitle -> stock-footage -> compose) with ~18 LLM providers, multiple TTS engines, FastAPI API + Streamlit WebUI, and a real test suite but no CI.
status: active
source: github-researcher
confidence: high
created: 2026-06-02
updated: 2026-06-02
---

# MoneyPrinterTurbo (harry0703)

Repo: https://github.com/harry0703/MoneyPrinterTurbo
Reviewed at HEAD `Sync Chinese README documentation cleanup` (2026-06-02), latest release v1.2.9 (2026-05-30). Clone was shallow (`--depth 50`); metadata cross-checked against the GitHub API.

This is the **original** of a three-repo family. The fork is `Asad-Ismail/MoneyPrinterTurbo-Extended`; the independent rewrite is `FujiwaraChoki/MoneyPrinterV2`. This document characterizes the baseline so the other two can be lined up against it.

## Executive Summary

MoneyPrinterTurbo turns a topic string into a finished narrated, subtitled vertical short video. It is a config-driven Python monolith: an LLM writes the script and search terms, a TTS engine narrates it, stock footage is fetched from Pexels/Pixabay (or supplied locally), subtitles are generated and aligned, and MoviePy/FFmpeg composes the final clip(s). It ships both a FastAPI HTTP API and a Streamlit WebUI over the same service layer. The defining trait of the family is **provider breadth** (roughly 18 LLM providers, 5+ TTS paths) and a **clean staged orchestrator** with checkpointing. It is Chinese-first in heritage but fully internationalized today.

## STATS

- **Stars:** 77,613. **Forks:** 11,012. (Among the most-starred AI-video repos on GitHub.)
- **First commit:** 2024-03-11. **Last commit:** 2026-06-02 (actively maintained; release cadence v1.1.x in 2024 through v1.2.9 in 2026).
- **Contributors:** 47 (per API). Dominated by `harry0703`/`Harry` (38 of the shallow commits); long tail of single-commit external contributors.
- **Language:** Python (399 KB, ~99% of code) plus Shell/Batchfile launchers, a Dockerfile, one HTML shim.
- **License:** MIT.
- **CI:** **None.** `.github/` contains only issue templates and SECURITY.md. No GitHub Actions workflow runs the test suite.
- **Packaging:** `pyproject.toml` (hatchling build, `uv.lock` pinned) is primary; `requirements.txt` kept for legacy pip. Docker via `Dockerfile` + `docker-compose.yml` (and `.gpu` variants). Launch through `webui.sh`/`webui.bat` (Streamlit) or `main.py` (uvicorn API). Python `>=3.11,<3.13`.

## STACK

- **Language:** Python 3.11.
- **Web framework:** Both. FastAPI (`0.136.3`) + uvicorn for the API; Streamlit (`1.58.0`) for the WebUI. Same `app/services` layer underneath.
- **LLM providers (~18, dispatched in `app/services/llm.py::_generate_response`):** openai, moonshot, ollama, aihubmix, oneapi, azure, gemini, grok, qwen (dashscope), cloudflare, minimax, mimo, deepseek, modelscope, ernie, pollinations, litellm, and g4f (optional extra, off by default for provider-risk reasons). Most route through the OpenAI-compatible client; qwen/gemini/cloudflare/ernie/modelscope/litellm have bespoke branches.
- **TTS engines (`app/services/voice.py`, ~1400 LOC):** edge-tts (default), Azure Speech v1 and v2 (`azure-cognitiveservices-speech`), SiliconFlow (CosyVoice), Gemini TTS, Mimo TTS. Voice selection is encoded in the voice-name string (e.g. `siliconflow:model:voice-Gender`), parsed by `is_*_voice` predicates in `tts()`.
- **Subtitle / ASR:** faster-whisper (`1.1.0`, `app/services/subtitle.py`) as the whisper provider; edge-tts word boundaries as the default provider.
- **Video lib:** MoviePy 2.2.1 plus direct FFmpeg (`app/services/video.py`, ~1099 LOC). FFmpeg is resolved at runtime (`get_ffmpeg_binary`), codec is whitelisted with encoder-existence checks and fallback (`_get_effective_video_codec`, `_write_videofile_with_codec_fallback`).
- **State/queue:** in-memory or Redis (`redis 5.2.0`), selected by `enable_redis` config. `pydub` for audio duration, `loguru` for logging.

## PIPELINE

End-to-end, owned by `app/services/task.py::start(task_id, params, stop_at)`. The `stop_at` parameter lets the same pipeline terminate after any stage (script / terms / audio / subtitle / materials / video), which is how the `/subtitle` and `/audio` API endpoints reuse it. Progress is checkpointed to the state store (5/10/20/30/40/50 -> 100%) at each stage.

1. **Script generation** — `task.py::generate_script` -> `llm.py::generate_script`. Uses the topic, language, paragraph count, and an optional custom system prompt. Skipped if a script is supplied.
2. **Search-term generation** — `task.py::generate_terms` -> `llm.py::generate_terms` (asks the LLM for ~5 English keywords). Skipped when `video_source == "local"`. Result persisted to `script.json` via `save_script_data`.
3. **Audio / TTS** — `task.py::generate_audio` -> `voice.py::tts`. Produces `audio.mp3` and a `sub_maker` (word-boundary object) used for subtitle timing. Supports a custom audio file bypass.
4. **Subtitle generation + alignment** — `task.py::generate_subtitle`. Provider `edge` builds the SRT from TTS word boundaries (`voice.create_subtitle`); provider `whisper` (or edge fallback) transcribes with faster-whisper (`subtitle.create`) then **corrects against the source script** via Levenshtein similarity (`subtitle.correct`).
5. **Stock-footage fetch** — `task.py::get_video_materials` -> `material.py::download_videos` (Pexels default, Pixabay alternate) or `video.preprocess_video` for local materials. Downloads enough clips to cover `audio_duration * video_count`.
6. **Compose / concat** — `video.py::combine_videos`. Concatenates/crops clips to the chosen aspect (portrait/landscape/square), applies transition modes, sequential or random concat.
7. **Render final video** — `video.py::generate_video`. Burns subtitles (MoviePy `TextClip` + optional rounded background `_rounded_subtitle_background_clip`), mixes narration with optional BGM (`get_bgm_file`), writes `final-{n}.mp4` with codec fallback.
8. **Cross-post (optional)** — `task.py` tail -> `upload_post.py::cross_post_video`. Auto-uploads to TikTok/Instagram via the upload-post service when configured.

## ARCHITECTURE

Clean three-tier layout: controllers (HTTP) -> services (logic) -> models (schema/const). The WebUI is a parallel front end over the same services.

- **`app/controllers/`** — FastAPI surface.
  - `v1/video.py` (400 LOC): the real API. Routes: `POST /videos` (full generate), `POST /subtitle`, `POST /audio` (partial pipelines via `stop_at`), `GET /tasks`, `GET /tasks/{id}`, `DELETE /tasks/{id}`, BGM list/upload, video-material list/upload, and `GET /stream/{path}` + `GET /download/{path}` with path-traversal guards.
  - `v1/llm.py`: 3 POST routes for script / terms / social-metadata generation.
  - `manager/`: `TaskManager` base with `InMemoryTaskManager` and `RedisTaskManager` implementations plus `TaskQueueFullError` (concurrency cap).
  - `base.py`, `ping.py`, `v1/base.py`: router wiring and health.
- **`app/services/`** — the engine.
  - `task.py` (397): the staged orchestrator (above).
  - `llm.py` (1029): all LLM providers + script/term/social-metadata prompts and response normalization.
  - `voice.py` (1400): all TTS engines + edge-tts SubMaker compatibility shims.
  - `video.py` (1099): MoviePy/FFmpeg composition, codec resolution, BGM, subtitle rendering.
  - `subtitle.py` (306): faster-whisper transcription + Levenshtein subtitle correction.
  - `material.py` (299): Pexels/Pixabay search + clip download.
  - `state.py` (168): `MemoryState` / `RedisState` task-progress store behind a `BaseState` ABC.
  - `upload_post.py` (149): TikTok/Instagram cross-posting.
- **`app/models/`** — `schema.py` (379, Pydantic: `VideoParams`, `VideoAspect`, `VideoConcatMode`, request/response models), `const.py` (task-state constants), `exception.py`.
- **`app/config/`** — TOML loader (`config.toml`, auto-copied from `config.example.toml`); container detection and Ollama base-URL inference; env-var overrides for Redis, ImageMagick, FFmpeg.
- **`app/utils/`** — `utils.py` (helpers, script normalization, punctuation splitting), `file_security.py` (single `resolve_path_within_directory` guard reused by the download/stream routes).
- **`webui/Main.py`** (1355 LOC): the entire Streamlit app in one file, with `i18n/` translation JSONs (en, zh, de, vi, ar, ...) and `.streamlit` config.
- **`resource/`**: bundled fonts, BGM songs, public static assets. **`test/`**: pytest suite (see below). **ASGI** (`app/asgi.py`): mounts `/tasks` and `/` as static dirs, configurable CORS.

## DISTINCTIVE (family baseline)

- **Provider breadth is the signature.** ~18 LLM providers and 5+ TTS paths, all config-selected, no code change to swap. This is the bar the fork and rewrite are measured against.
- **Staged, resumable orchestrator.** The single `start(..., stop_at=...)` function is the spine of the whole product; partial endpoints (`/audio`, `/subtitle`) are just early exits, not separate code paths. Strong DRY.
- **Two-provider subtitle strategy with script-anchored correction.** Either TTS word boundaries (edge) or whisper ASR, and when whisper drifts, `subtitle.correct` realigns transcribed lines back to the authoritative LLM script using Levenshtein similarity and greedy line-merging (threshold 0.8). This is the most novel algorithm in the repo.
- **Dual front end over one service layer.** FastAPI API and Streamlit WebUI share `app/services`, so the API is a first-class citizen, not an afterthought.
- **Material support:** multi-language (i18n JSONs for en/zh/de/vi/ar and more; per-language script prompts and voice locales). **Chinese-first heritage** (primary README is Chinese, inline comments are Chinese, default example subject `金钱的作用`) but now fully international. Local-footage mode plus stock providers (Pexels, Pixabay). Aspect ratios portrait/landscape/square, BGM, custom fonts, rounded subtitle backgrounds, multi-output (`video_count`), optional auto cross-post to TikTok/Instagram.

## LIMITATIONS / SMELLS

- **No CI.** A 97-function pytest suite exists (`test_llm.py` alone has 45 tests; `test_video.py` 24, `test_voice.py` 18) but nothing runs it on push/PR. Coverage is real but unguarded against regression.
- **Monolith service files.** `voice.py` 1400, `webui/Main.py` 1355, `video.py` 1099, `llm.py` 1029 LOC. Mitigated by good intra-file decomposition (many small named functions), but four files carry most of the system. `webui/Main.py` is a single-file Streamlit app — by far the worst offender for navigability.
- **Provider dispatch is a long if/elif ladder.** `llm.py::_generate_response` is one ~180-line elif chain over 18 providers; adding a provider means editing the ladder rather than registering a strategy. Same pattern (predicate chain) in `voice.py::tts`. No provider-factory/registry abstraction.
- **`llm.py::generate_terms` requires LLM output to be a JSON array** and retries; brittle to provider format drift (hence the `_normalize_text_response` / `_extract_chat_completion_text` shims that already exist to paper over per-provider quirks).
- **Comments are Chinese-only** in the hot paths, raising the bar for non-Chinese contributors.
- **Strengths worth noting (not smells):** no hardcoded secrets (clean config-driven, all keys default to `""`/`[]` in `config.example.toml`); path-traversal protection on file-serving routes via `file_security.resolve_path_within_directory`; codec/encoder existence checks with runtime fallback; edge-tts version-compatibility shims show real maintenance discipline.

## GRADE

**B / B+.** On the Helioy calibration scale (C=DeepDiagram; B-=claudex/metaharness; B=graphify; B+=superpowers/Understand-Anything; A-=notebooklm-py/fallow-rs; A=SurrealDB). Justification: a genuinely useful, heavily adopted product with a clean staged orchestrator, broad config-driven providers, a real (if un-CI'd) test suite, and security-aware file handling — clearly above graphify-tier (B). It misses B+ on engineering hygiene: no CI, four 1000+ LOC monolith files, an if/elif provider ladder instead of a registry, and Chinese-only comments. Call it a high B; B+ only if you weight adoption and breadth over internal structure.

## HELIOY ANGLE

Two primitives are worth a look; the rest does not transfer (Helioy is not building a video product).

1. **The `stop_at` staged orchestrator (`task.py::start`).** A single linear pipeline where each stage checkpoints progress to a pluggable state store and any stage can be a terminal exit, reused by multiple entry points. This is a clean reference for littleorgans pipeline orchestration where one organ's output feeds the next and partial runs (debug, preview) need to stop early without a forked code path. The pattern, not the code, is the takeaway.
2. **Script-anchored subtitle correction (`subtitle.correct`).** Realigning a noisy transcription back to an authoritative source text via Levenshtein similarity with greedy span-merging is a reusable alignment primitive — relevant if any Helioy tool ever needs to reconcile ASR/LLM output against a known ground-truth string (e.g. transcript-to-source matching).

**Anti-pattern to avoid borrowing:** the 18-branch provider if/elif ladder. Helioy already routes providers through a factory (per cm feedback on provider/credential plumbing); this repo is a concrete example of what *not* to do, and validates the existing Helioy factory approach.

## Sources Consulted

- `README.md` / `README-en.md` (feature claims cross-checked against code).
- `app/services/task.py` (orchestrator, read in full).
- `app/services/llm.py`, `voice.py`, `video.py`, `subtitle.py`, `material.py`, `state.py` (structure + key functions).
- `app/controllers/v1/video.py`, `v1/llm.py`, `app/asgi.py` (API surface).
- `app/models/schema.py`, `app/config/config.py`, `app/utils/file_security.py`.
- `pyproject.toml`, `requirements.txt`, `.github/`, `test/services/`.
- GitHub API: stars/forks/createdAt/contributors/releases.

## Open Questions

- Concurrency/throughput under the Redis task manager vs in-memory was not load-tested.
- The g4f optional provider's actual reliability is unknown (intentionally excluded from default install).
- How the fork (Extended) and rewrite (V2) diverge on the provider ladder and subtitle alignment is the next comparison step.
