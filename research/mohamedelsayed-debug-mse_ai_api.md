---
title: MohamedElsayed-debug/mse_ai_api review for Helioy
type: research
tags: [github-review, mse_ai_api, helioy, python, fastapi, playwright, mit, scraper, openai-shim, skip]
summary: Single-file FastAPI shim that scrapes chatgpt.com via Playwright and dresses it as OpenAI. Off-mission for Helioy. Skip.
status: active
source: github-researcher
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## 1. Stats

- Repo: https://github.com/MohamedElsayed-debug/mse_ai_api
- Stars: 238. Forks: 81 (anomalously high for a 17KB file; consistent with YouTube-driven copy-deploy traffic, not engineering interest).
- Age: ~6 weeks (created 2026-03-19, last push 2026-04-15).
- Contributors: 1 (Mohamed Elsayed, all 9 commits).
- Surface: 1 Python file (`main.py`, 453 lines, 17KB), `Dockerfile` (47 lines), `docker-compose.yml`, `requirements.txt` (5 pins), README, MIT LICENSE. No tests. No `.github/workflows`; only `.github/FUNDING.yml`.
- Stack: FastAPI 0.110, uvicorn 0.27, Playwright 1.42, pydantic 2.6. Python 3.10+.
- Purpose: proxy that automates the chatgpt.com web UI (headless Chromium with anti-bot evasion), exposing `/v1/chat/completions`, `/v1/responses`, and `/v1/models` for n8n. Monetised via a closed "PRO" Django version.

## 2. Grade

**C** (DeepDiagram tier). Single-author tutorial-grade scraper with no tests, no CI, hardcoded selectors, and a TOS-adverse runtime model. The OpenAI shim shape is competent but trivial; the browser-thread plumbing has correctness holes. Below B− (claudex/cozodb) on every axis except "did ship something runnable".

## 3. Primitives that transfer

Two narrow primitives are worth lifting as patterns. License is MIT so direct code use is allowed; both are small enough to reimplement without copying.

1. **Single-thread asyncio worker exposed to a sync caller via `run_coroutine_threadsafe`.** `main.py:16-95` wraps a long-lived event loop in a `threading.Thread`, signals readiness with `threading.Event`, and submits work with `asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout=120)`. Useful pattern when a sync FastAPI handler or sync caller needs to drive a stateful async resource (browser, persistent websocket, model client) without spinning one up per request. Landing target: **helioy-bus** (any future place where a sync tmux-spawned worker needs to talk to an async transport) and **nancyr** (Python interop layer, if any synchronous host code drives async tokio bridges through a runner).

2. **Tool-call extraction by JSON-island regex with multi-candidate fallback.** `main.py:232-270` strips fenced code blocks, then runs both the cleaned text and a `\{[\s\S]*"tool_calls"[\s\S]*\}` regex through `json.loads`, taking the first that parses to a dict containing `tool_calls`. Same shape Helioy needs whenever a model is asked for structured output but may wrap it in markdown. Landing target: **nancyr** (agent output parser), **helioy-bus** (any place a free-form agent reply is interpreted as a structured directive), and the **am** ingest path if AM ever accepts model-authored payloads.

Two more are demotable to "noted, not borrowed":

3. **OpenAI Chat Completions / Responses dual-shape envelope.** `main.py:310-347` (`chat.completion`) and `main.py:391-435` (Responses API `function_call` items) show the exact JSON shapes a Helioy provider mock needs to satisfy both legacy and modern OpenAI clients. Useful as a reference if Helioy ever stubs OpenAI for offline tests; the OpenAI SDK docs are the better source.

4. **Tool-call instruction prompt template.** `main.py:185-230` builds an aggressive "RESPOND ONLY WITH JSON" instruction with a worked example seeded from `tools[0]`. Mildly informative for any Helioy component coercing a non-tool-trained model into emitting tool calls; the Helioy stack already has tool-trained providers, so this is a fallback recipe rather than a primary pattern.

## 4. Does NOT transfer

1. **Whole-product mission (browser-scraping ChatGPT to fake the OpenAI API).** TOS-adverse, brittle against any chatgpt.com DOM change (the code hardcodes `#prompt-textarea` and `[data-message-author-role="assistant"]` at `main.py:61,66`), and orthogonal to Helioy, which uses authenticated provider APIs and pays for tokens by design.

2. **Anti-bot evasion stack** (`--disable-blink-features=AutomationControlled`, spoofed UA, `webdriver` getter override at `main.py:38-53`). Useful only for circumventing bot detection. No Helioy component scrapes consumer LLM UIs.

3. **`AsyncBrowserThread` as a reusable component.** It only handles one request at a time (`process_request` blocks on a single `future.result`), creates a fresh browser context per call (`main.py:48`) which defeats session persistence, and has no recovery path: the bare `except Exception as e: raise e` at `main.py:83-85` discards the traceback and the browser stays dirty. Below the bar for nancyr/helioy-bus reuse.

4. **Token "counting" via `len(prompt.split())`** (`main.py:303-304`, repeated at `main.py:384-385`). Misleading. Helioy already uses provider-reported usage; never substitute whitespace splitting for tokens.

5. **Auth model.** Bearer token compared via `authorization.replace("Bearer ", "").strip() != API_SECRET_KEY` at `main.py:287` is a non-constant-time string compare against a default secret of `change-secret-key-2026`. Anti-pattern.

6. **Build choices.** Dockerfile installs both `playwright install chromium` AND `google-chrome-stable` (lines 33, 38) so the runtime ends up with two browsers; the launch then forces `channel="chrome"` (`main.py:37`) ignoring Playwright's bundled chromium. Wasteful image, fragile pinning. Skip.

7. **Single-file architecture and no tests.** Helioy's senior-engineer bar requires verification; this repo has zero. Nothing structural to copy.

## 5. Verdict

**Skip.** Acknowledge the two transferable patterns (asyncio-worker-from-sync-caller, JSON-island tool-call parser) as already well-known idioms; do not depend on or borrow from this repo.

## 6. Why

The repo is a YouTube tutorial artifact with a freemium funnel to a "PRO" Django version. Stars and forks track the video, not engineering signal. Helioy gains nothing from the product, the architecture is a 453-line single-file scraper, and the two patterns worth noting are textbook idioms documented in Python's stdlib and any LLM tool-calling tutorial. Spending more attention on it has a worse return than picking any current Helioy thread (HyDE, code-nav, code marks, T3 eval).

## 7. How to apply

- Do not open a follow-up. No cm decision is needed beyond the review summary.
- If, in the future, **nancyr** or **helioy-bus** needs a sync-to-async runner for a stateful async resource, the `run_coroutine_threadsafe` pattern at `main.py:90-95` is the reference shape; reimplement, do not import.
- If a Helioy parser must extract structured JSON from a free-text LLM reply that may be fenced, mirror the multi-candidate fallback at `main.py:232-270` (raw, then regex-bounded slice). Keep this in mind for the **am** ingest path or any nancyr supervisor that interprets agent output.
- Calibration: anchor this review at C alongside DeepDiagram. Any future "tutorial-grade single-file scraper" can be compared to it directly without re-reviewing.

## 8. Sources consulted

- `README.md` (full file)
- `main.py` (full file, 453 lines)
- `Dockerfile`, `docker-compose.yml`, `requirements.txt`
- `git log --oneline` (9 commits, single author)
- `gh repo view` (stars, forks, license, sizes, dates)

## Open questions

None worth investigating. The repo's surface is fully covered by one file read.
