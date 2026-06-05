---
title: MoneyPrinter family — comparative breakdown (Turbo vs V2 vs Turbo-Extended)
date: 2026-06-02
reviewer: claude-code (helioy CWD)
scope: standalone capability research, secondary lens = littleorgans video-gen
repos:
  - https://github.com/harry0703/MoneyPrinterTurbo
  - https://github.com/FujiwaraChoki/MoneyPrinterV2
  - https://github.com/Asad-Ismail/MoneyPrinterTurbo-Extended
individual_artifacts:
  - ~/.mdx/research/harry0703-moneyprinterturbo.md
  - ~/.mdx/research/fujiwarachoki-moneyprinterv2.md
  - ~/.mdx/research/asad-ismail-moneyprinterturbo-extended.md
---

# MoneyPrinter family — comparative breakdown

## The lineage is not what the names imply

The three names suggest one project at three stages. The code says otherwise. The real
tree has one root and two **convergent-but-independent** descendants, plus one copy:

```
MoneyPrinter (FujiwaraChoki, original)
├── MoneyPrinterTurbo   (harry0703)        ← independent rewrite, Chinese-first. NOT a fork. Shares only the concept.
│   └── MoneyPrinterTurbo-Extended (Asad-Ismail)  ← code copy of Turbo (isFork:false), 3 ML features bolted on. Stale.
└── MoneyPrinterV2      (FujiwaraChoki)     ← the original author's own "complete rewrite", scope-expanded into a 4-pillar suite.
```

Turbo and V2 share **no source and no author**. They are sibling reinterpretations of the
same idea (LLM script → TTS → stitched media → social), not versions of one another.
Extended is a literal copy of Turbo's tree (not even a registered GitHub fork), never synced upstream.

## Side by side

| Axis | **MoneyPrinterTurbo** (harry0703) | **MoneyPrinterV2** (FujiwaraChoki) | **Turbo-Extended** (Asad-Ismail) |
|---|---|---|---|
| Relationship | Independent rewrite of original | Original author's own rewrite | Copy of Turbo + ML bolt-ons |
| Stars / forks | 77.6k / 11.0k | 30.7k / 3.3k | 113 / 48 |
| Age / last commit | 2024-03 / active (2026-06-02) | 2024-02 / 2026-05-15 | 2025-05 / stale (2026-04-09) |
| License | **MIT** | **AGPL-3.0** (copyleft) | MIT |
| Scope | Short-video generator | 4-pillar automation suite | Short-video generator |
| Frontend | Streamlit WebUI + FastAPI | Terminal numeric menu | Streamlit + FastAPI (inherited) |
| LLM providers | ~18 (cloud + local) | Ollama-local only | ~18 (unchanged) |
| Video source | Stock clips (Pexels/Pixabay/local) | AI-generated stills (Nano Banana 2) | Stock clips + semantic ranking |
| TTS | edge-tts default, +Azure/Gemini/etc | KittenTTS | + Chatterbox (voice cloning) |
| Distribution | Optional cross-post; user owns it | **Auto-uploads via Selenium** | Inherited |
| CI | None | None | None |
| Packaging | uv + Docker + compose | None (clone + venv) | pip + conda/CUDA |
| Grade | **B / B+** | **C+** | **B-** |

## Per-repo characterization

**MoneyPrinterTurbo (harry0703) — the engineered one, B/B+.**
The family's reference implementation. A single staged, resumable orchestrator
(`app/services/task.py::start` with a `stop_at` early-exit) feeds both a FastAPI surface and a
Streamlit WebUI over one service layer — strong DRY. Provider breadth is the signature:
~18 LLM providers and 5+ TTS engines, all config-selected. The one genuinely novel algorithm
is script-anchored subtitle correction (realign noisy ASR back to the authoritative script via
Levenshtein + greedy merge). Held below B+ only by hygiene: no CI despite a real 97-function
pytest suite, four 1000+ LOC files, and an ~180-line if/elif provider ladder (no factory).

**MoneyPrinterV2 (FujiwaraChoki) — the broad-but-risky one, C+.**
Not a video tool, a four-pillar automation suite: YouTube Shorts (`YouTube.py`, the only video
overlap), a Twitter/X bot (`Twitter.py`), affiliate marketing (`AFM.py`), and cold-email outreach
(`Outreach.py`). Browser automation (Selenium driving a logged-in Firefox) is the auth substrate;
LLM is Ollama-only. It generates AI **stills** stitched to TTS, not stock video. Architecturally
weak: terminal `while True` menu, one class per capability with **no shared base or registry**
(Selenium bootstrap duplicated three times), config re-parsed on every accessor call, a "CRON"
that is in-process `schedule` shelling `subprocess.run` with no persistence. Tests cover only the
sponsor's PostBridge path. Two hard blockers for any reuse: **AGPL-3.0** (copyleft) and the ethics
surface — `Outreach` is unsolicited mass cold-email (Maps-scrape → regex harvest → SMTP blast,
no consent/opt-out, GDPR/CAN-SPAM exposed) and Selenium social posting violates platform ToS.

**MoneyPrinterTurbo-Extended (Asad-Ismail) — the idea-menu fork, B-.**
A stale single-author copy of Turbo (~2,500 net new LOC, feature work ended Aug 2025) adding three
real capabilities upstream lacks: (1) Chatterbox open-source TTS with **voice cloning** via a
`reference_audio/` directory + WhisperX word timestamps; (2) **semantic clip matching**
(sentence-transformers cosine + CLIP text↔thumbnail, new `VideoConcatMode.semantic`); (3)
**word-by-word subtitle highlighting**. No new providers, no new endpoints; six contributor PRs
(Groq, Wan2.1 video, Kokoro TTS) sit unmerged. Mine the ideas, do not depend on the repo.

## Verdict for Helioy: inspiration-only

If littleorgans ever grows a video-generation capability, the path is clear:

- **Study Turbo, build fresh.** Its staged orchestrator and dual-frontend-over-one-service-layer
  are the architecture worth emulating. MIT-licensed, so even direct reference is safe.
- **Ignore V2 as a codebase.** AGPL-3.0 plus a spam-automation core rule it out. Keep it only as a
  *scope cautionary tale* (what happens when one tool tries to be four) and an ethics line marker.
- **Treat Extended as an enhancement menu**, not a dependency: voice cloning, semantic clip ranking,
  word-level subtitle highlighting are the features to consider if/when the baseline exists.

## Borrowable primitives (honest, mostly thin)

1. **Staged resumable orchestrator** (Turbo, `app/services/task.py::start`). One linear pipeline,
   per-stage checkpoint to a pluggable state store, any stage a terminal exit, reused by multiple
   entry points. The cleanest external reference for **littleorgans pipeline orchestration**.
2. **Script-anchored subtitle correction** (Turbo, `voice.create_subtitle` / `subtitle.correct`).
   Reconciling noisy transcripts back to authoritative source text — reusable for any
   transcript-to-source alignment problem, not just video.
3. **Reference-audio-dir-as-voice-registry** (Extended, `voice.py:get_chatterbox_voices`). Drop a
   file in a dir, it becomes a namespaced selectable option, no registry code. Mirrors Helioy's
   on-disk skill/prompt discovery UX. Thin.

## Confirmatory negatives (they validate existing Helioy doctrine)

- The **18-branch provider if/elif ladder** (Turbo) and **three duplicated Selenium constructors**
  (V2, no registry) are exactly the cost Helioy's provider-factory / DRY doctrine avoids. Do not borrow; cite as evidence.
- V2's **toy scheduler** (in-process `schedule` + `subprocess.run`, no persistence, no catch-up,
  fixed presets) is a what-not-to-do reference for **schedule-matters**: a real scheduler needs
  persisted state and daemon/OS-level triggers.

## Nothing else transfers

WASM/native tree-sitter is irrelevant here; the Chinese-first heritage, the stock-footage provider
plumbing, the Streamlit monolith, and V2's browser-automation auth substrate are all
domain-specific to consumer video automation and carry no infra primitive Helioy lacks.
