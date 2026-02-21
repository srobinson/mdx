---
title: DeepDiagram (twwch) — staff engineering review
type: research
tags: [github-review, langgraph, agentic-ui, fastapi, react, sse, diagram-generation]
summary: LangGraph-routed multi-agent diagram generator (mindmap, flow, mermaid, charts, drawio, infographic, general). Solo author, 5 months old, 896 stars, AGPL-3.0. Working product, but zero tests, a 1803-line ChatPanel, CORS=*, and BYOK keys persisted in localStorage. Engineering grade C.
status: active
source: github-researcher
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

# DeepDiagram — engineering review

## Snapshot

- **Repo**: https://github.com/twwch/DeepDiagram
- **Stars / forks**: 896 / 69 (as of 2026-04-27)
- **Created**: 2025-12-09. About 5 months old.
- **Last push**: 2026-02-04. Repo metadata updatedAt 2026-04-25 reflects star/fork churn, not commits. Active in commits through early February then quiet.
- **License**: AGPL-3.0 (network use counts as distribution; viral copyleft — meaningful constraint for anyone embedding this).
- **Bus factor**: 1. Two committer aliases (`chenhao <chenhao03@xiaoduotech.com>` 30 commits, `陈毫 <2329095893@qq.com>` 20 commits) are the same person. Zero outside contributors in the visible 50-commit window.
- **Disk**: 81 MB. Image-heavy README; code is small.

## What it actually does

A web app that turns a natural-language prompt (plus optional image and document uploads) into one of seven diagram types. A LangGraph router classifies intent, dispatches to a specialized agent prompt, the agent emits `<design_concept>...</design_concept><code>...</code>`, and a streaming XML-tag parser splits those into two SSE channels. The frontend renders the `code` payload through a renderer chosen by agent type: mind-elixir for mindmaps, React Flow for flowcharts, Mermaid.js, ECharts 6, Draw.io for mxGraph XML, AntV Infographic 0.2.11 for infographics. PostgreSQL (SQLModel + asyncpg) stores sessions, messages, and parsed file context. There is also a Next.js marketing site under `website/`.

It is a thin wrapper that puts a chat UI on top of "ask the LLM to emit syntax for renderer X." The interesting work is prompt engineering and stream parsing, not orchestration.

## Architecture

### Backend: LangGraph-as-switch-statement

`backend/app/agents/graph.py:13-53` defines the entire graph. Router → conditional edge → one of seven agent nodes → END. Every agent goes straight to END:

```
workflow.add_edge("mindmap_agent", END)
workflow.add_edge("flow_agent", END)
... etc
```

LangGraph here is doing nothing a `dict[intent, handler]` could not. There is no state machine, no looping, no tool-call cycle (intentionally removed; see commit `43472f6` "架构简化， 移除 tool call 的逻辑"). Each agent node calls `llm.astream` once and returns the message. The "graph" is decorative.

Routing logic in `backend/app/agents/dispatcher.py:9-198`:
- Explicit `@agent` keyword check (lines 22-44) bypasses the LLM call.
- Otherwise an LLM classifier with conversation history and "last active agent" stickiness (lines 46-160).
- Fallthrough keyword matching on the LLM response string (lines 165-180). Substring `"flow"` wins over `"mermaid"` if both are mentioned, which is why the order matters and feels brittle.

### Streaming tag parser

`backend/app/api/routes.py:33-166`. Hand-rolled state machine: INIT → DESIGN_CONCEPT → CODE → DONE. Walks the buffer with `find()` on each chunk, computes deltas via `last_dc_len` / `last_code_len` watermarks. It works, and the "two streams from one LLM response" trick is genuinely clever for UX. Cost: O(n) per chunk because `find()` rescans from offset 0 every time. Fine for short payloads, ugly on long ones.

The `finalize()` method (lines 125-166) duplicates most of the streaming logic to handle truncated tags. A real parser would not need this.

`extract_tag_fields` (lines 173-191) is a separate regex-based fallback used at the end if the parser missed something (lines 619-640). Two parsers for the same format is a smell.

### SSE dispatch loop

`backend/app/api/routes.py:217-679` is `event_generator`, a 460-line async generator that handles session creation, history reconstruction, document parsing, the LangGraph stream, tag parsing, and persistence. It does at least eight distinct jobs in one function. The `accumulated_steps` deduplication block at lines 318-330 walks a list checking JSON-encoded contents for an `index` match — that is the kind of code that exists because turn_index, parent_id, retry, and document chunks were each retrofitted onto an originally simpler shape.

### Provider plumbing

`backend/app/core/llm.py:4-96`. `get_llm` accepts overrides, falls through to DEEPSEEK env, then OPENAI env. `get_configured_llm(state)` reads `state["model_config"]` and forwards. Default model is hardcoded to `"claude-sonnet-3.7"` (lines 47, 74) which is not a real model name. README also tells users to set `MODEL_ID=claude-sonnet-3.7` (README.md:250). This will fail against real OpenAI; the author is presumably proxying through some endpoint that aliases it.

Bearer-prefix stripping (line 14) and base-URL normalization (lines 17-26) are reasonable. The `if "nvidia" in url_lower / dashscope / deepseek / openai` provider sniffing for log labels (lines 36-39) is harmless cosmetics.

### Document analysis

`backend/app/services/file_service.py:62-187`. Chunks at 20 KB, fans out with `asyncio.Semaphore(concurrency)`, streams partial results via an `asyncio.Queue`. After all producers finish, runs a synthesis pass over the concatenated summaries. The producer/consumer split with a queue is correct and reads cleanly. This is the best-engineered file in the repo.

### Frontend

`frontend/src/components/ChatPanel.tsx` is **1803 lines**. Stuart's own rule from CLAUDE.md is "files over 700 lines == refactor first." This file imports 22 lucide icons in one import (lines 2-8), inlines the `AGENTS` config (lines 18-73), defines helper components like `DocAnalysisCard` (line 75+), and almost certainly contains the SSE consumer, the resize logic, the history panel, the settings dropdown, and the message renderer in one component. Did not exhaustively read it; size alone is the finding.

`frontend/src/store/chatStore.ts` (735 lines) is the Zustand store. Single big store handling messages, sessions, versions, and SSE state. Same smell at smaller scale.

Renderers live under `frontend/src/components/agents/`: `FlowAgent.tsx` 468 lines, `MermaidAgent.tsx` 318, `MindmapAgent.tsx` 280, `InfographicAgent.tsx` 288. Reasonable sizes.

## Engineering signals

### Bad

- **Zero tests.** `find frontend backend -name '*.test.*' -o -name '*.spec.*'` returns nothing. The two `test_*.py` files in `backend/` (`test_time.py`, `test_sse.py`) are not pytest — they are scratch scripts. CLAUDE.md "Add tests for new features" is in the README contributing guide and is not followed by the author.
- **`ChatPanel.tsx` at 1803 lines.** God component.
- **CORS = `*`.** `backend/app/core/config.py:10` hardcodes `BACKEND_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000", "*"]`. Combined with `allow_credentials=True` in `backend/app/main.py:16-22`, this is invalid CORS (browsers reject `*` with credentials), and on the public demo it means any origin can hit the API.
- **BYOK keys in `localStorage`.** `frontend/src/store/settingsStore.ts:46-49` persists `apiKey` plain via Zustand `persist`. Any XSS exfiltrates every saved provider key.
- **No auth on any endpoint.** `GET /sessions`, `DELETE /sessions/{id}` (`routes.py:686-707`) have no ownership check. The public demo at `deepd.cturing.cn` exposes any user's sessions to any other user by ID enumeration. `chat_service.delete_session` deletes by id with no auth (`backend/app/services/chat.py:91-106`).
- **`print` debugging in production paths.** `dispatcher.py:43, 83, 163` and `migrations.py` use `print` instead of the `logger` defined in `app/core/logger.py`.
- **Two parsers for one format.** `StreamingTagParser` and `extract_tag_fields` both parse `<design_concept>/<code>`. The fallback at `routes.py:619` runs *after* finalize, suggesting the streaming parser is not trusted.
- **`langgraph` is theatrical.** Seven nodes, all going straight to END, no cycles, no shared state mutation across nodes. A `match intent` would be smaller and clearer.
- **Hardcoded `"claude-sonnet-3.7"` default** (`llm.py:47, 74`, README.md:250) is not a real model name and will 404 against OpenAI.
- **Commit messages are noise.** `83cd1a8 fix`, `c39fbc8 fix`, `296b79e fix`, `98a8301 fix: m2 & bug`. Mix of English and Chinese, often duplicated subjects. Not blocking, but signals "solo author iterating fast" rather than "shippable team practice."

### Good

- **Two-stream SSE UX is a real idea.** Splitting `design_concept` (reasoning) from `code` (renderable output) into independent SSE event channels gives the frontend a decoupled UX with no JSON parsing tax. Worth stealing the *concept* even if the implementation is rough.
- **Idempotent migrations.** `backend/app/core/migrations.py` tracks applied filenames in `schema_migrations`. Simple, works, no Alembic dependency.
- **Document analysis fan-out is clean.** `file_service.py:62-187` semaphore + queue + synthesis is textbook async producer/consumer. Best-engineered file in the repo.
- **Persistence-on-cancel.** `routes.py:656-672` uses `asyncio.shield` to save partial assistant messages when the connection drops. Most chat apps lose the in-flight response on disconnect. Nice touch.
- **Message branching via `parent_id` + `turn_index`.** `models/chat.py:24-44`. Git-style branching for retry-and-explore. Modest schema, useful product feature.
- **Multi-stage Infographic pipeline.** `agents/infographic.py:14-95` does template selection (LLM picks from 50+ templates) then template-specific code generation with a per-template syntax-rules block. Two-pass design that respects the structure of the target DSL. The right shape for "many sub-formats under one agent."
- **Docker-first deployment.** Single `docker-compose.yml`, nginx reverse proxy, GitHub Actions builds three images (backend, frontend, website) and pushes to Docker Hub. Reproducible.

### Type safety

TypeScript strict-by-default via Vite + React 19 template. Backend uses Pydantic models for the API surface (`ChatRequest`, `TestModelRequest`) and SQLModel for ORM. No `mypy` config visible. `state["intent"]` is a free-form string with downstream `.startswith` and `in` checks (`dispatcher.py:165-180`). Adequate for a solo project; not what a staff engineer would call rigorous.

### Error handling

Top-level FastAPI exception handler dumps tracebacks (`main.py:41-49`). The SSE generator wraps the LangGraph stream in try/except and yields `event: error` (`routes.py:674-679`). The `/test-model` endpoint translates 401/404/timeout to friendly strings (`routes.py:740-749`). Error handling is "best effort" rather than systematic — there is no retry, no circuit breaker, no rate limiting on the public BYOK endpoint.

### CI

One workflow: `.github/workflows/docker-build-push.yml` builds three Docker images on push to `main` and tags. No tests, no lint, no type-check, no scan. CI is "ship the container."

## Security smells

1. **Wildcard CORS with credentials.** `config.py:10` + `main.py:16-22`. Either misconfigured or deliberately open. On the public demo, this is exploitable.
2. **No auth, public DELETE.** `DELETE /api/sessions/{id}` with no ownership check (`routes.py:703-707`). Anyone can wipe anyone's sessions on the demo by ID guessing.
3. **API keys in localStorage.** `settingsStore.ts:46-49`. Standard browser-app pitfall. The "BYOK as the security model" pattern means an XSS is catastrophic.
4. **User-supplied `base_url` to `ChatOpenAI`.** `routes.py:716-738` test-model endpoint and the main chat endpoint both accept arbitrary `base_url` from the client. SSRF surface: a malicious caller can point the backend at internal services. There is no allowlist.
5. **Document base64 round-tripped without size cap.** `file_service.py:16-60` decodes user-provided base64 with no size limit, then `pd.read_excel` / `fitz.open` it. Memory DoS.

For a self-hosted single-user tool, none of these matter. For the public demo at `deepd.cturing.cn/`, all five are real.

## Distribution model

Self-host via `docker-compose up -d`. There is also a hosted demo and a marketing site (`website/`, Next.js 15) with i18n via `next-intl`. The marketing site predates the project's stability — there is a `website-architecture.md` at the repo root, which is unusual and reads like the author shipped a landing page early to capture stars. Star count (896) supports the read: high stars on a single-author 5-month repo with zero tests usually means the README and demo are doing the work.

## Comparison

- **Excalidraw + AI plugins**: also natural-language-to-diagram, but Excalidraw is a real graphics editor with collaborative editing. DeepDiagram is "render the LLM's syntactic output." Different ambition.
- **Mermaid Chart, Eraser.io**: commercial competitors with vector editing, real auth, and team features.
- **napkin.ai**: closest in spirit (text-to-visual), much more polished, closed source.
- **chartdb / chartGPT-style toy projects**: DeepDiagram is meaningfully larger than these — it's not a toy. But the gap to a real product is wide.

The genuine novelty is the seven-renderer fan-out under one chat. Pulling six diagram libraries together with one routing UI is real integration work, even if each individual agent is "prompt + render."

## Engineering grade

**C.**

Justification: The product works, the document-parsing service is genuinely well-built, message branching and partial-save-on-disconnect are thoughtful. But: zero tests, an 1803-line god component, wildcard CORS with credentials, no auth on a publicly-deployed multi-user-shaped API, BYOK keys in localStorage, two parsers for one format, LangGraph used as a switch statement, and a hardcoded fake model name as the default. A staff engineer would not approve this for production. A solo dev shipping fast would call it shipped. It is the latter.

If the public demo is removed and the project is reframed as "self-hosted, single-user, BYOK," half the issues disappear and the grade rises to a B-.

## Sources consulted

- README.md (full)
- backend/app/agents/dispatcher.py, graph.py, mindmap.py, infographic.py
- backend/app/api/routes.py (full, in two reads)
- backend/app/core/llm.py, config.py, migrations.py
- backend/app/services/file_service.py, chat.py
- backend/app/models/chat.py
- backend/app/main.py
- backend/pyproject.toml
- frontend/package.json
- frontend/src/store/settingsStore.ts
- frontend/src/components/ChatPanel.tsx (first 120 lines)
- .github/workflows/docker-build-push.yml
- git log (50 commits visible), shortlog
- File-size scan (`wc -l` on all .py / .ts / .tsx)

## Open questions

- Is the public `deepd.cturing.cn` demo actually shared multi-user, or is each visitor sandboxed somehow not visible in the code? The schema and endpoints suggest no sandboxing.
- The `MODEL_ID=claude-sonnet-3.7` default — is the author proxying through a custom endpoint that aliases this? If so, the README example will not work for anyone else.
- How does the "Infographic Agent" template selection actually perform? 50 templates, single-shot LLM choice — would expect frequent mis-selection without measurement.
