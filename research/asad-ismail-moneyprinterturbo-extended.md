---
title: MoneyPrinterTurbo-Extended (Asad-Ismail) — Fork Delta Analysis
type: research
tags: [moneyprinterturbo, fork-analysis, short-video, tts, semantic-search, comparative]
summary: Single-author standalone copy of harry0703/MoneyPrinterTurbo adding Chatterbox voice-cloning TTS, semantic CLIP-based video matching, and word-by-word subtitle highlighting; diverged May 2025, last commit Apr 2026, no CI, no upstream tracking.
status: active
source: github-researcher
confidence: high
created: 2026-06-02
updated: 2026-06-02
---

# MoneyPrinterTurbo-Extended — Fork Delta Analysis

## Executive Summary

`Asad-Ismail/MoneyPrinterTurbo-Extended` is a single-developer divergence of `harry0703/MoneyPrinterTurbo` (the 77k-star automated short-video generator). It is **not a registered GitHub fork** (`parent: null`); the author copied the codebase into a standalone repo with an "Initial commit" on 2025-05-22 and layered ~22 commits of his own work on top. The delta is narrow but genuinely substantive in three areas: **(1) Chatterbox open-source TTS with voice cloning + WhisperX word timestamps**, **(2) semantic video-clip matching via sentence-transformers and CLIP image similarity**, and **(3) true word-by-word ("karaoke") subtitle highlighting**. It also adds a CUDA/conda environment scaffold. It does NOT add new LLM or video providers, batch mode, or API surface; those exist only as unmerged open PRs.

## Stats

| Metric | Value |
|---|---|
| Stars | 113 |
| Forks | 48 |
| Fork's own first commit | 2025-05-22 ("Initial commit", code copied, not a true GH fork) |
| Last commit | 2026-04-09 |
| Commits (fork's own work) | 23 total |
| Contributors | 1 (Asad-Ismail; two email casings, same person) |
| Tracks upstream? | No. Zero merge commits from harry0703. Frozen against ~May-2025 upstream baseline. |
| Behind upstream | Far behind. Upstream HEAD is 2026-06-02 and has since added `upload_post.py` (social auto-upload), `file_security.py`, `pyproject.toml`/`uv.lock` packaging, GPU Dockerfiles, multi-language READMEs — none present in fork. |
| License | MIT (matches upstream) |
| CI | None. No `.github/` directory. (An "Add GitHub Actions CI" PR sits open and unmerged.) |
| Releases/tags | None |

## Fork Delta (the headline)

### Added — Open-source TTS with voice cloning (the flagship feature)
- `app/services/voice.py` grew **1400 → 2285 LOC (+885)**. Added Chatterbox TTS (`from chatterbox.tts import ChatterboxTTS`) + WhisperX integration.
- New voice namespace `chatterbox:` with `default` and `clone` types. `get_chatterbox_voices()` (voice.py:85) scans a new top-level `reference_audio/` directory and exposes each file as a clonable voice (`chatterbox:clone:<name>-Custom`).
- New functions: `is_chatterbox_voice()` (1146), `chatterbox_tts()` (1514), `chatterbox_tts_chunked()`, `preprocess_text_for_chatterbox()` (1365), `chunk_text_for_chatterbox()` (1468). Voice cloning uses `audio_prompt_path` against a reference clip; WhisperX produces word-level timestamps for subtitle sync.
- Env-var tuning surface: `CHATTERBOX_CFG_WEIGHT` (speech speed), `CHATTERBOX_DEVICE=cpu` (force CPU fallback). CPU fallback is automatic on CUDA error.

### Added — Semantic video-text matching
- `app/services/semantic_video.py` (**684 LOC, fork-only**): sentence-transformers (`all-mpnet-base-v2` default) ranks candidate clips against script text by cosine similarity instead of upstream's random clip selection. Persists per-clip metadata sidecars (`save_video_metadata` / `load_video_metadata`).
- `app/services/image_similarity.py` (**698 LOC, fork-only**): CLIP (`clip-vit-base-patch32`) multimodal text-vs-thumbnail scoring, with embedding caches, retry/backoff, CPU-forcing, and psutil memory guards. Optional layer on top of semantic mode.
- New `VideoConcatMode.semantic` enum value (`app/models/schema.py:19`). `material.py` rewired (imports `semantic_video`, captures `thumbnail_url`/`preview_images`, line 14/86/174). `task.py:200` guards against semantic mode with `video_count > 1` (would produce identical videos).

### Added — Word-by-word subtitle highlighting
- `app/services/video.py`: new `create_word_highlighted_image()` (679) and `create_subtitle_clip()` (780) render PIL images where only the currently spoken word is colored; driven by word-level timestamps.
- `app/services/subtitle.py` grew **306 → 557 LOC (+251)**: `word_timestamps=True` extraction from faster-whisper, plus "enhanced subtitles with word-level timing" generator.
- `task.py:137` gates this behind `enable_word_highlighting`.

### Added — New schema params (`app/models/schema.py`)
`enable_word_highlighting` (default False), `word_highlight_color` (#ff0000); `similarity_threshold` (0.5), `semantic_model`; `enable_image_similarity`, `image_similarity_threshold` (0.7), `image_similarity_model`; `thumbnail_url`, `preview_images` on the material item. Config adds a `verbose` key.

### Added — Ops/scaffolding (top-level, fork-only)
`environment.yml` (conda env pinning CUDA 12.9 / cuDNN 9.10), `requirements-cuda.txt` (full NVIDIA CUDA 12.4 suite + torch 2.5.1), `install_cuda.sh`, `setup_cuda_env.sh`, `api.sh`, `webui.sh`, `prompts.txt`, `notebooks/`, `reference_audio/`.

### NOT changed (despite README ambition and open PRs)
- **LLM providers unchanged** (`app/services/llm.py`): still the stock g4f/openai/moonshot/ollama/azure/gemini/oneapi/qwen set. Groq + Cerebras exist only as **open PR #9**.
- **No new video providers.** Wan2.1/2.2 AI video gen is **open PR #11**, unmerged. Kokoro TTS is **open PR #7**, unmerged.
- **No batch mode, no new API endpoints.** `app/controllers/v1/` is identical shape to upstream.

### Removed relative to upstream
- `app/services/upload_post.py` and `app/utils/file_security.py` are absent — but these are **upstream post-fork additions**, so this is divergence-by-staleness, not deliberate removal.
- Replaced upstream's `pyproject.toml`/`uv.lock` (uv packaging) with `requirements.txt` + conda `environment.yml`. Dropped `Dockerfile.gpu` / `docker-compose.gpu.yml` and the `README-ar.md`/`README-en.md` translations.
- One commit ("removed low quality video merges", 2025-06-02) trimmed upstream clip-merge logic.

## Stack Changes

- **Added heavy ML deps**: `sentence-transformers`, `scikit-learn`, `transformers`, `torch`, `pillow` (in `requirements.txt`); plus Chatterbox TTS (installed from source: `resemble-ai/chatterbox`) and WhisperX (not pinned in requirements — README installs them manually).
- **GPU stack**: new `requirements-cuda.txt` pins the full NVIDIA CUDA 12.4 library suite + torch/torchaudio/torchvision 2.5.1; `environment.yml` pins CUDA 12.9 / cuDNN 9.10 via conda.
- **Packaging regression vs upstream**: upstream moved to `uv` (pyproject + uv.lock); fork stays on pip requirements + conda. Same web framework (Streamlit 1.45, FastAPI 0.115).
- A late cleanup commit (2026-04-09) bumped `edge_tts` 6.1.19 → 7.0.2, torch → 2.6.0 in environment.yml, made API-key rotation thread-safe, removed `verify=False` from HTTP calls, and replaced bare `except` clauses.

## Pipeline Changes

The upstream pipeline (script → terms → TTS audio → subtitle → material download → concat → render) is preserved, with two stages mutated and one added:

1. **TTS stage** (`voice.tts`, voice.py:1151): adds a `chatterbox:` branch routing to local voice-cloning synthesis with WhisperX word timestamps, alongside upstream's edge/azure/siliconflow paths.
2. **Material selection stage** (`material.py` + new `semantic_video.py` / `image_similarity.py`): when `VideoConcatMode.semantic` is set, clip selection becomes embedding-ranked (text→clip cosine, optional CLIP text→thumbnail) instead of random. Metadata sidecars cache per-clip search context.
3. **Render stage** (`video.py` + `subtitle.py`): optional word-level highlighting renders per-word colored subtitle frames synced to WhisperX/faster-whisper timestamps.

Stage *count* is essentially unchanged; two stages gained alternative implementations gated by new flags, and `task.py` orchestrates the gating (137 highlighting, 200 semantic guard).

## Maintenance Signal

**Effectively a stale solo experiment with a recent agent-driven burst, now idle.**
- Real feature work clusters May–Aug 2025 (commits through 2025-08-01), then silence until a single 2026-04-09 batch of small hygiene fixes.
- 6 open PRs (Wan2.1/2.2 video, Groq/Cerebras LLM, Kokoro TTS, API retry, CI, runtime stabilization), all dated 2026-03-29 to 2026-04-09, branch names like `code:codex/stable-runtime-foundation` and `k9135515-…` — signature of an automated/agent contribution sprint that the owner **did not merge**.
- 2 open issues (install/conda-conflict errors), unanswered.
- No CI, no releases, no upstream tracking. Single contributor. The divergence is frozen against a year-old upstream baseline.

## Grade

**B- (claudex/metaharness tier), judged as a fork.**
Justification: the delta is real and non-trivial (voice cloning + semantic matching + word highlighting are three genuinely useful capabilities upstream lacks, ~2,500 net new LOC of working code), which clears the C/DeepDiagram bar of a thin or cosmetic fork. But it is held below B by being a frozen single-author copy with no CI, no upstream sync, unmerged contributor PRs, and code quality that needed a late "replace bare except / remove verify=False" cleanup pass. Worth mining for the ideas, not worth depending on.

## Relevance to Helioy

Mostly orthogonal — this is a media-generation pipeline, not infra. Two thin, honestly-borrowable primitives:

1. **Reference-audio-directory-as-voice-registry** (`get_chatterbox_voices()`, voice.py:85): a filesystem directory scanned at startup to expose each file as a selectable, namespaced capability (`chatterbox:clone:<name>`). This is the same convenience pattern Helioy uses for skills/prompts discovered on disk; clean precedent for a "drop a file in a dir, it becomes a selectable option" UX without a registry.
2. **Embedding-ranked selection with on-disk metadata sidecars + bounded LRU embedding cache + automatic CPU fallback** (`semantic_video.py`, `image_similarity.py`): a self-contained pattern for "rank candidates by cosine similarity, cache embeddings with a size cap, degrade gracefully off-GPU." Adjacent to attention-matters retrieval ergonomics, though Helioy's stores already do this more rigorously.

Nothing here is a must-adopt. The honest read: interesting feature ideas, no infrastructure primitive Helioy doesn't already have better.

## Sources Consulted

- `README.md` (fork feature claims, install flow)
- `app/services/voice.py`, `semantic_video.py`, `image_similarity.py`, `video.py`, `subtitle.py`, `material.py`, `task.py`
- `app/models/schema.py`, `app/models/const.py`
- `webui/Main.py` (semantic settings UI block, lines 542–675)
- `requirements.txt`, `requirements-cuda.txt`, `environment.yml`, `config.example.toml`
- `git log`, `gh repo view`, `gh issue/pr list` for both fork and upstream

## Open Questions

- Exact upstream commit the fork copied from is unrecoverable without a deep upstream clone (current upstream shallow history starts well after the 2025-05-22 divergence). "Behind by N commits" is therefore qualitative (year-plus stale), not an exact count.
- Whether the 6 agent-authored PRs reflect the owner's intent to revive the project or were an unsupervised experiment is unknown.
