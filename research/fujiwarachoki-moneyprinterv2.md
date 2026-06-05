---
title: MoneyPrinterV2 (FujiwaraChoki) — Multi-Capability Money Automation Suite
type: research
tags: [github-review, automation, video-generation, social-bots, affiliate, outreach, selenium, ollama, moneyprinter-family]
summary: V2 is a CLI-driven multi-capability automation suite (YouTube Shorts, Twitter/X bot, Amazon affiliate, cold-email outreach) sharing author and DNA with the original MoneyPrinter, but is a SEPARATE codebase from the harry0703 Turbo line.
status: active
source: github-researcher
confidence: high
created: 2026-06-02
updated: 2026-06-02
---

# MoneyPrinterV2 (FujiwaraChoki)

## Executive Summary

MoneyPrinterV2 (MPV2) is a single-user, CLI-driven Python automation suite that bundles four distinct "make money online" capabilities behind one interactive menu: a YouTube Shorts generator/uploader, a Twitter/X posting bot, an Amazon affiliate-marketing pitch generator, and a Google-Maps-scraping cold-email outreach engine. It is a complete rewrite by the same author (FujiwaraChoki / Sami Hindi) of the original MoneyPrinter, with a deliberately wider scope and a one-class-per-capability modular layout. It is NOT part of, nor forked from, the harry0703/MoneyPrinterTurbo line — Turbo is an independent Chinese rewrite that MPV2's README merely links to as a "community version." The video portion is only one of four pillars and is markedly simpler than Turbo's pipeline (single linear class, AI-generated still images + Ken Burns-free concat, no web UI, no stock-footage search). Verified against real code at commit `eca94cd` (last commit 2026-05-15).

## Stats (verified)

- Stars: 30,726 | Forks: 3,287
- Created: 2024-02-12; first commit 2024-02-17 (FujiwaraChoki)
- Last commit: 2026-05-15 ("docs(post-bridge): use affiliate link in PostBridge.md", by Sami Hindi = same person)
- Contributors: ~15 distinct; dominated by FujiwaraChoki/Sami Hindi (≈46 of ~59 visible commits). Long tail of single-PR contributors.
- Language: Python (~136 KB) + Shell (~4.5 KB). Python 3.12 required (`.python-version`).
- License: AGPL-3.0.
- CI: NONE. `.github/` contains only `FUNDING.yml`. No workflows, no lint, no test runner in CI.
- Packaging: NONE as a distributable. No `pyproject.toml`, no `setup.py`. Install = clone + venv + `pip install -r requirements.txt`. Run = `python src/main.py`. KittenTTS pinned as a direct wheel URL in `requirements.txt`.
- Codebase size: ~4,245 LOC Python total. Largest file `src/classes/YouTube.py` (878 LOC). Tests exist on disk (`tests/`, 4 files, all PostBridge/config-focused) but are not wired to CI.

## Architecture

- **Entry point**: `src/main.py` (493 LOC). A `while True: main()` loop renders a numeric menu (`OPTIONS` in `src/constants.py`) and dispatches to one of four capabilities. Heavily nested inline branching, not subcommand-dispatched.
- **One class per capability** in `src/classes/`:
  - `YouTube.py` (878) — `class YouTube`: full Shorts pipeline + Selenium upload.
  - `Twitter.py` (225) — `class Twitter`: LLM tweet generation + Selenium post to x.com.
  - `AFM.py` (176) — `class AffiliateMarketing`: scrape Amazon product → LLM pitch → post via `Twitter`.
  - `Outreach.py` (293) — `class Outreach`: download/build a Go scraper, scrape Google Maps, extract emails, mass-send via SMTP.
  - `Tts.py` (18) — `class TTS`: thin KittenTTS wrapper.
  - `PostBridge.py` (279) — `class PostBridge` + `PostBridgeClientError`: REST client for the post-bridge.com sponsor API (TikTok/Instagram cross-post).
- **Config system**: a single root `config.json` (seeded from `config.example.json`). `src/config.py` (405 LOC) is a flat collection of ~30 `get_*()` accessors, each of which RE-OPENS AND RE-PARSES `config.json` on every call. No caching, no schema object, no dataclass. Some keys fall back to env vars (`GEMINI_API_KEY`, `POST_BRIDGE_API_KEY`). `get_post_bridge_config()` is the only one that normalizes/validates.
- **State/cache**: `src/cache.py` — per-capability JSON files under `.mp/` (`youtube.json`, `twitter.json`, `afm.json`, `scraper_results.csv`). Accounts/products are plain dicts keyed by a UUID4. `get_provider_cache_path()` is the only mild DRY abstraction (twitter|youtube).
- **LLM provider**: `src/llm_provider.py` (63 LOC) — Ollama-only. Module-global `_selected_model`, `select_model()`, `generate_text(prompt, model_name=None)`. No multi-provider abstraction despite the name.
- **Scheduler / "CRON"**: `src/cron.py` (100 LOC) is a one-shot batch runner invoked as `python src/cron.py <twitter|youtube> <account_uuid> <model>`. The actual scheduling lives in `main.py` using the `schedule` library: menu options build a `command` list and register `schedule.every().day.at("10:00").do(job)` where `job()` does `subprocess.run(command)`. This is IN-PROCESS scheduling that only runs while `main.py` stays alive; it is not real OS cron and not persisted. Granularity is fixed presets (once/twice/thrice daily).
- **Sponsor integration**: `src/post_bridge_integration.py` (222 LOC) glues the YouTube success path to the PostBridge client (`maybe_crosspost_youtube_short`). This is the newest and best-engineered module (dependency-injectable `prompt_fn`, has tests). It exists because Post Bridge sponsors the repo.

## Key Patterns (and anti-patterns)

- **Capability = class + cache file + menu branch.** Clean conceptual separation, no shared base class or registry; each capability re-implements Selenium/Firefox bootstrap independently (duplication across YouTube/Twitter/AFM constructors).
- **Selenium-Firefox with a user profile** is the universal "auth" mechanism. No API tokens for YouTube/Twitter; the bot drives a logged-in Firefox profile (`-profile <path>`) and scrapes the DOM. Brittle by design (hardcoded XPaths/test-ids in `constants.py`).
- **LLM-as-content-engine throughout.** Every capability funnels through `generate_text()` with inline f-string mega-prompts (topic → script → metadata → image prompts).
- **Config-read-per-call** is a pervasive smell: ~25 functions each open `config.json` fresh.
- **Bare `except:` swallowing** in critical paths — e.g. `YouTube.upload_video()` wraps the entire Selenium flow in `try/except:` that returns `False` and quits the browser, hiding the actual failure.

## Detailed Findings — Scope (the headline)

Four shipped capabilities, only ONE of which overlaps the Turbo video-gen line:

1. **YouTube Shorts automation** (`YouTube.py`) — OVERLAPS Turbo (this is the video generator). LLM topic+script+metadata, AI image generation (Nano Banana 2 / Gemini image API), KittenTTS voiceover, MoviePy concat with subtitles, Selenium upload to YouTube Studio. NEW territory.
2. **Twitter/X bot** (`Twitter.py`) — NEW vs Turbo. LLM-generates a tweet about a configured topic and posts it via Selenium on x.com. Grows an account on a schedule.
3. **Affiliate marketing** (`AFM.py`) — NEW vs Turbo. Selenium-scrapes an Amazon product page (title + feature bullets via element IDs in `constants.py`), LLM-writes a promo pitch appended with the affiliate link, posts it through the `Twitter` class.
4. **Cold-outreach engine** (`Outreach.py`) — NEW vs Turbo, and the highest-risk module. Downloads + `go build`s the third-party `gosom/google-maps-scraper`, scrapes local businesses for a niche, regex-extracts emails from each business website, then **mass-sends templated SMTP emails via yagmail** in a loop. Requires Go installed.

Plus a non-capability integration:
- **Post Bridge cross-posting** (`PostBridge.py` + `post_bridge_integration.py`) — NEW. After a successful YouTube upload, optionally cross-posts the same video to TikTok/Instagram via the sponsor's API.

Roadmap (`docs/Roadmap.md`) signals intended expansion: automated cold calling, item flipping (sneakers), long-form→short repurposing.

**Bottom line on scope:** The "broader automation suite" framing is ACCURATE and verified. Three of four pillars (Twitter bot, affiliate, outreach) are entirely outside any video-generation remit. The repo's own tagline is literally "Automate the process of making money online," not "make videos."

## Pipeline (video portion) and how it differs from Turbo

`YouTube.generate_video(tts)` runs a strictly linear pipeline (see docstring at `YouTube.py:39-48`):
1. `generate_topic()` — LLM picks a one-sentence video idea from the niche.
2. `generate_script()` — LLM writes an N-sentence script (`script_sentence_length`, default 4), regex-strips markdown, retries if >5000 chars.
3. `generate_metadata()` — LLM title (<100 chars) + description.
4. `generate_prompts()` — LLM returns a JSON array of AI image prompts (count ≈ len(script)/3).
5. `generate_image()` per prompt — calls Nano Banana 2 (Gemini `:generateContent` image API), base64-decodes inline image data, writes PNGs to `.mp/`.
6. `generate_script_to_speech()` — KittenTTS → WAV.
7. `combine()` — MoviePy: loops the still images to fill TTS duration, crops/resizes each to 1080x1920, mixes TTS + a random background song (`choose_random_song()`), burns subtitles (faster-whisper local OR AssemblyAI), writes MP4.
8. `upload_video()` — Selenium drives youtube.com/upload, sets title/description/"made for kids", publishes as **unlisted**, scrapes the resulting URL.

How it differs from harry0703/MoneyPrinterTurbo's pipeline:
- **Imagery source**: MPV2 generates AI still images (Nano Banana 2) and Ken-Burns-concatenates them. Turbo searches/downloads stock video clips (Pexels/Pixabay) and stitches real footage. Fundamentally different visual substrate.
- **UI**: Turbo ships a Streamlit web UI + FastAPI service. MPV2 is terminal-only, single interactive menu, no API, no web layer.
- **LLM**: MPV2 is Ollama-local-only (`llm_provider.py`). Turbo supports many cloud providers (OpenAI/Moonshot/Azure/Gemini/etc.) via config.
- **TTS**: MPV2 uses KittenTTS (local). Turbo defaults to Edge-TTS / Azure.
- **Upload**: MPV2 auto-uploads via Selenium browser automation. Turbo produces the file and leaves distribution to the user.
- **Scope**: MPV2 wraps video gen inside a four-pillar suite; Turbo is exclusively a video generator.

## Relationship to the Turbo line — evidence

- **Same-name, DIFFERENT project from Turbo.** No shared code, no shared author, no fork relationship. `gh repo view` shows `isFork: false` and owner `FujiwaraChoki`. Turbo is `harry0703`.
- **MPV2's own README** lists Turbo only under "Versions ... developed by the community" → "Chinese: MoneyPrinterTurbo." That is the sole link; it frames Turbo as a community-language variant, not a parent or successor.
- **True lineage is to the ORIGINAL MoneyPrinter** (also FujiwaraChoki). README line 19: "MPV2 ... is the second version of the MoneyPrinter project. It is a complete rewrite ... with a focus on a wider range of features and a more modular architecture." So V2 is a genuine successor to V1 by the same author, and Turbo is a parallel sibling that branched off the V1 idea independently.
- Net: For a comparative breakdown, treat MPV2 and the Turbo line as **convergent-but-independent** descendants of the original MoneyPrinter, sharing only the "LLM script → TTS → stitched media → social" concept, not source.

## Limitations / Smells / Ethics

- **Outreach = mass cold email.** `Outreach.start()` scrapes businesses off Google Maps, regex-harvests emails from their sites, and SMTP-blasts templated messages with no rate limiting, consent, or unsubscribe. This is spam automation and is GDPR/CAN-SPAM exposed. Highest ToS/legal-risk surface.
- **Selenium account automation** for YouTube and X both violate the respective platform Terms of Service (automated posting via a driven browser profile). Account-ban risk.
- **Affiliate auto-posting** can constitute platform spam and may breach Amazon Associates disclosure rules.
- **Fake-engagement-adjacent**: Twitter bot is positioned to "grow a Twitter account" via automated daily posting.
- **Code-quality flags**: no CI; config re-parsed on every accessor call; bare `except:` in `YouTube.upload_video()`; constructor-level browser-bootstrap duplication across three classes; hardcoded DOM XPaths/IDs that rot whenever YouTube/X redesign; `subprocess` shelling out to `go build` a downloaded archive (supply-chain surface — one historical commit `aa1d8f6` literally fixed "supply chain poisoning vulnerability in song archive download"); tests cover only the sponsor PostBridge path, not the four core capabilities.
- **Sponsor entanglement**: the README banner, the newest module, and the only well-tested code all serve post-bridge.com. The repo's engineering quality is highest exactly where the sponsor benefits.
- Educational-purposes disclaimer present in README (line 97-99), explicitly disclaiming misuse liability — a tell that the authors know the ethics are dicey.

## Dependencies (critical)

- `selenium` + `selenium_firefox` + `webdriver_manager` + `undetected_chromedriver` — browser automation (the auth + posting substrate).
- `ollama` — local LLM inference (only provider).
- `moviepy` (+ ImageMagick, Pillow) — video assembly.
- `kittentts` (pinned wheel URL) + `soundfile` — TTS.
- `faster-whisper` (local STT) and `assemblyai` (cloud STT) — subtitle generation.
- `yagmail` — SMTP for outreach blasts.
- `schedule` — in-process daily scheduling.
- `srt_equalizer` — subtitle line balancing.
- External Go binary: `gosom/google-maps-scraper` (downloaded + built at runtime).
- Gemini image API ("Nano Banana 2") via raw `requests` — AI image generation.

## Relevance to Helioy

Largely a NEGATIVE finding for borrowable engineering, with two narrow, honest takeaways:

1. **Capability-class + cache-file + menu-branch as a poor-man's plugin registry.** MPV2 keeps each capability fully isolated (its own class, its own JSON state, its own menu branch) but has NO registry — `main.py` hardcodes every branch and `cache.py` hardcodes `twitter|youtube`. This is exactly the duplication Helioy's `feedback_check_linear_workflows_first` / provider-factory doctrine warns against. The lesson is confirmatory: a real capability registry (one factory, shared bootstrap) is the right shape; MPV2 shows the cost of skipping it (three duplicated Selenium constructors). Nothing to lift, but a clean negative exemplar.
2. **Scheduler design is the only piece adjacent to a Helioy concern (schedule-matters).** MPV2's scheduler is the weakest plausible reference: `schedule.every().day.at(...)` in an in-process loop shelling `subprocess.run` to a one-shot `cron.py`. It does not persist, does not survive process death, and offers only fixed presets. If Helioy ever builds schedule-matters, MPV2 is a what-NOT-to-do reference (no durability, no catch-up, no cron expression support), reinforcing that a real scheduler needs persisted state and OS-level or daemon-backed triggers.

No config-triad, no provider abstraction, and no testing discipline worth importing. The dependency-injectable `prompt_fn` pattern in `post_bridge_integration.py` is locally tidy but unremarkable.

## Sources Consulted

- `README.md`, `docs/Roadmap.md`, `AGENTS.md` (repo's own)
- `src/main.py`, `src/cron.py`, `src/config.py`, `src/cache.py`, `src/constants.py`, `src/llm_provider.py`
- `src/classes/YouTube.py`, `Twitter.py`, `AFM.py`, `Outreach.py`, `Tts.py`, `PostBridge.py`
- `src/post_bridge_integration.py`
- `config.example.json`, `requirements.txt`, `scripts/setup_local.sh`
- `git log`, `git shortlog`, `gh repo view` metadata

## Open Questions

- Shallow clone (depth 50, 59 commits visible) — the very earliest V1→V2 migration commits are below the horizon; the "complete rewrite" claim rests on README + author identity, not a diffed lineage. A full clone would confirm whether any V1 code survived verbatim.
- The four PostBridge-focused tests are the only tests; actual pass/fail not executed here (no env). They appear unit-level with injected fakes.
