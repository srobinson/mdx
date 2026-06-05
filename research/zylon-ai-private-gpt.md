---
title: PrivateGPT (zylon-ai/private-gpt) — Strengths Capture
type: research
tags: [private-gpt, zylon, local-ai, rag, ingestion, llm-api, anthropic-api, fastapi, dependency-injection, streaming, mcp, skills]
summary: A strengths-only capture of PrivateGPT v1.0.0 — a Claude-API-compatible, provider-agnostic local AI application API layer. What it does well, with file:line citations.
status: active
source: github-researcher
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# PrivateGPT (zylon-ai/private-gpt) — Strengths Capture

> Scope note: this is a pure strengths capture. No comparison to other projects, no grading, no build/borrow/inspiration verdict, no transfer mapping. It records what PrivateGPT does well.

## Stats

57.3K stars, 7.6K forks, created 2023-05-02, last pushed 2026-06-12 (actively maintained, not archived). Apache-2.0. Python 3.11 only (`requires-python = ">=3.11,<3.12"`). 93 contributors total, though recent work is concentrated (Javier Martinez carries the bulk of the v1 commits). Released **v1.0.0 on 2026-06-03** — a ground-up rewrite (`CHANGELOG.md` headline: "PrivateGPT revamp v1", marked BREAKING). The codebase is large and disciplined: ~330 Python modules under `private_gpt/`, 110 test files across ~50 test directories, strict mypy + ruff (13 lint rule families, `ban-relative-imports = "all"`, strict type-checking). Build is Hatchling + uv (`uv.lock` is ~574KB). CI (`.github/workflows/`) covers tests, Fern docs preview/publish, release-please automated releases, and an `update-claude-specs.yml` job that keeps the OpenAPI spec aligned to the Claude API. Docs are a full Fern site at docs.privategpt.dev.

## What it is

PrivateGPT 1.0 is "the open-source API layer that turns local models into production AI applications." It is explicitly **not an inference engine** — it connects to any OpenAI-compatible inference server (Ollama, llama.cpp, vLLM, LM Studio) via `OPENAI_API_BASE` and sits above it, providing the higher-level application primitives: a **Claude/Anthropic-API-compatible** messages API, document/artifact ingestion with citation-backed retrieval, built-in and custom tools, MCP connectors, skills, database and tabular access, and embeddings. A bundled Gradio-free static "workbench" UI ships at `/ui` purely as a demonstrator; the README is emphatic that "the API is the actual product." It is the open-source core beneath Zylon's commercial on-prem enterprise platform.

## What it does well

### 1. Provider abstraction via a uniform factory + registry pattern

Every swappable backend (LLM, embeddings, vector store, node store) follows the same shape: an abstract factory base, a module-level `_PROVIDERS` dict, a `register_*()` function for runtime extension, and a registry that instantiates factories by a config `mode` string.

- LLM: `LLMFactory` ABC (`private_gpt/components/llm/factories/base.py:30`) with the template method `create_llm()` calling abstract `_create_llm()`. The registry maps mode→factory in `_PROVIDERS` (`factories/registry.py:12-15`) and raises a helpful "Available: ..." error on an unknown mode (`registry.py:30-36`). `register_llm()` (`registry.py:18`) lets the application layer inject providers without editing core.
- Embeddings mirror this exactly: `EmbeddingFactoryRegistry` + `_PROVIDERS` (`components/embedding/factories/factory.py:10-20`), selected in `EmbeddingComponent._initialize_models()` (`embedding_component.py:60-76`).
- Vector store: `register_vector_store()` + `_PROVIDERS` (`components/vector_store/factory.py:12-15`); Qdrant is the shipped default, registered in-component (`vector_store_component.py:44`).
- Node store: providers are plain functions ("simple", "postgres") in `_PROVIDERS` (`components/node_store/node_store_component.py:70-73`) with `register_index_store()` (`:76`).

Why it is well done: the same mental model applies everywhere, the extension seam (`register_*`) is consistent and external, and the OpenAI factory further sub-routes by detecting the API base and the per-model `api_type` to pick the Chat Completions vs the Responses API path (`factories/completions/generic.py`, `factories/responses/`). Missing optional dependencies surface as actionable install hints rather than raw ImportErrors (`embedding/factories/openai.py:17-26`).

### 2. Capability-aware model auto-discovery

Rather than forcing users to hand-list every model, PrivateGPT can interrogate a running inference server and classify what it finds. A two-phase `StrategyChain` (`components/model_discovery/strategies.py:24-65`) first tries provider-specific discovery (OpenAI, Ollama, LlamaCpp, LM Studio), then classifies generic `/v1/models` responses, with a regex fallback (`providers/base.py:35-47`). It fingerprints servers by behavior — e.g. vLLM is detected by `permission[*].allow_logprobs` (`providers/vllm.py:28-29`) — and probes capabilities (tool support, image/audio token counts, reasoning, embedding dimension) so routing decisions are data-driven. Embedding dimension is auto-detected by querying the server (`embedding/discovery.py:79-105`).

### 3. Configuration: layered profiles + Pydantic validation + env-var model injection

Settings is one of the strongest parts. A single ~1,600-line typed `Settings` model (`private_gpt/settings/settings.py:1525`) composes ~40 sub-models, each with field-level descriptions, validators, and `model_post_init` normalization (e.g. coercing `0` → `None` for "unset" semantics, `ChatSettings.model_post_init` at `:505`). Profiles stack: `default` → optional `override` → comma-separated `PGPT_PROFILES` → `test` when running under pytest, deep-merged in order (`settings_loader.py:25-42, 151-165`). Models can be declared entirely from the environment via the `PGPT_MODELS_<ID>_<PARAM>[__<NESTED>]` convention with `__` building nested dicts (`settings_loader.py:80-148`). Discriminated unions cleanly separate LLM vs embedding model configs (`ModelConfigType`, `settings.py:737-740`). Secrets are marked `repr=False` so they never leak into logs. The cert/proxy/SSL settings even validate file existence at load time (`SSLSettings.validate_cert_file`, `:231`).

### 4. Claude/Anthropic-API-shaped server with a clean async-streaming model

The FastAPI app is assembled in `launcher.py:create_app()` with a lifespan that runs migrations, eager-loads components, and provisions a thread pool, plus per-request injector middleware and conditional UI/CORS mounting (`launcher.py:106-264`). Routers mount under `/v1`. The messages surface is Anthropic-shaped: `POST /v1/messages` (streaming + non-streaming with tools, thinking, citations), `POST /v1/messages/count_tokens`, and `POST /v1/messages/validate` (`server/chat/chat_router.py:30, 268, 297`). It also offers a genuinely useful **async messages** lifecycle — `POST /v1/messages/async` returns a `message_id` immediately, then `GET .../stream` (SSE), `GET .../status`, `POST .../cancel`, `DELETE .../delete` (`server/chat_async/chat_async_router.py:99, 242, 355, 492, 594`). Auth is deliberately minimal and pluggable: a timing-safe `secrets.compare_digest` header check that compiles to a no-op dependency when disabled, with a docstring pointing at FastAPI OAuth2 for extension (`server/utils/auth.py:40-69`).

### 5. The streaming / SSE machinery (a standout)

Streaming is modeled with care. Event types mirror the Anthropic stream contract (`message_start`, `content_block_start/delta/stop`, `message_delta`, `message_stop`) as Pydantic models in `events/models/_events.py`, with typed deltas (`TextDelta`, `InputJSONDelta`, `ThinkingDelta`, `SignatureDelta`, `CitationsDelta` in `_deltas.py`). An `SSEProducer` context manager (`events/sse/sse_producer.py`) orchestrates the message/content-block lifecycle, token counting, and `FatalError` emission; `SSEFormatter` renders events to wire format. Crucially, the buffer layer is abstracted behind a `StreamService` protocol (`components/streaming/providers/stream_service.py:15-80`) with two interchangeable backends — Redis Streams (with expiry, max-length, lazy pooled client) and a dict-based in-memory implementation that mirrors the same API for dev/test. A `SSEStreamManager` runs dual sync+async queues with lock-protected dispatch and timeout-guarded cleanup. This dual-backend, protocol-driven design is what makes the async-message endpoints (above) possible: a producer pushes into the stream, and one or many SSE consumers can attach, detach, and reconnect.

### 6. The agentic chat loop: interceptor chain + context stack

The chat path is built as a composable **interceptor chain** rather than a monolith. `ChatInterceptorService` (`server/chat/interceptors/chat_interceptor_service.py:64-195`) assembles ~20 injected, stateless interceptor singletons into phase-grouped stages (init → tools → preprocess → document → prompt → memory → recalculate). Each request gets a cloned chain over deep-copied mutable state while interceptor instances stay shared, which is both memory-efficient and concurrency-safe. Representative interceptors: `McpRequestInterceptor` (collects MCP tools concurrently, maps auth errors to PermissionError; `mcp_interceptor.py:46`), `SkillsLoopInterceptor` (resolves active skills from history, LIFO eviction; `skills_loop_interceptor.py:80`), `InternalToolsInterceptor` (`:24`), `SystemPromptInterceptor` (builds the prompt from the context stack, recurses if context grows; `:28`). State lives in an immutable **context stack** of typed layers (`components/context/models/context_stack.py`), so prompt assembly is just composition of layers (docs, instructions, skills, tools) — `ChatLoopInputState` keeps `.original_input` so a `RestoreStatelessInputInterceptor` can reset between loop iterations (`engines/chat_loop/models/chat_loop_state.py:18`). The loop tokenizer and context stack are detached during deep-copy and reattached to avoid copying expensive/immutable objects (`chat_loop_state.py:92-119`).

### 7. Tools: definition vs execution cleanly split, Anthropic-aligned

Tools separate **builders** (define a `ToolSpec`: name, description, JSON schema, async callable) from **processors** (late-bind/resolve unresolved tool placeholders in a request). A singleton `ToolPipeline` (`components/tools/tool_pipeline.py:35-75`) iterates processors to a fixed point, which transparently handles tools that depend on other tools. Built-ins span semantic_search, summarize, database_query, tabular_analysis, web_search, web_fetch, code_execution, bash, the text_editor family, and skill management (`components/tools/tool_names.py`). `anthropic_tools.py` translates Anthropic's date-versioned server tools (e.g. `web_search_20250305`) to internal names and models client-executed tools (bash, text_editor) the way the Claude API expects (`components/tools/anthropic_tools.py:17-70`). This dual server-side/client-side tool model is a faithful, forward-compatible take on the Claude tool-use contract.

### 8. Ingestion: a structure-preserving tree-node pipeline

Ingestion converts a raw file into a hierarchical **tree of typed nodes** rather than flat chunks. After format-specific reading (reader registry auto-selects by extension with a fallback chain, e.g. PDF → MarkItDown → Docling; `components/readers/registry.py:42-87`, `reader_component.py:30-46`), the document passes through ~20 transforms: image description (vision-mode or placeholder), markdown→tree (`markdown_to_tree_transform.py:33`), sentence splitting into `ChunkNode`s with overlap (`sentence_tree_node_parser.py`), multi-page tree combination, then flatten-for-embedding. `TreeNode` (`components/readers/nodes/tree_node.py:49`) carries parent/children/depth/height/sibling-index plus next/prev links, with `TreeMetadataMode` controlling what content is emitted per use case (EMBED vs LLM vs RAG vs USER). Specialized node subclasses (`SectionNode`, `TableNode`, `ImageNode`, `ListNode`) preserve document semantics. Three ingest modes (`simple`/`batch`/`parallel`) trade simplicity for throughput (`EmbeddingSettings.ingest_mode`, `settings.py:802`), and heavy ingestion runs async via Celery tasks (`celery/tasks/ingestion/extraction_tasks.py:47`), with a folder watcher (`server/ingest/ingest_watcher.py`) and URI loader for non-upload sources.

### 9. Retrieval-time context expansion

Because structure is preserved, retrieval can re-expand a hit back into its neighborhood. Post-processors include prev/next sibling replacement with overlap dedup (`components/postprocessor/prev_next_replacement.py:14`), token-bounded window expansion (`window_prev_next_replacement.py`), and a tree-expansion post-processor that grows down/across/up within a token budget with explicit CONTINUE/STOP/ROLLBACK failure strategies (`postprocessor/tree_expansion/document_expander.py`). Citations are first-class throughout (`ChatSettings.allow_generate_citations`, `force_to_return_citations`, `numerical_shorter_citations`).

### 10. Skills as sandboxed markdown

Skills are human-authored markdown with YAML frontmatter (name, description, license, `allowed-tools`), parsed and validated (`components/skills/parser.py`), stored in SQLite/Postgres + local/S3 (`components/skills/services/skill_service.py`), and lazily injected either into the system prompt or as a tool result (`SkillSettings.skill_injection_mode`, `settings.py:1386`). The `allowed-tools` frontmatter scopes which internal tools a skill may invoke — a lightweight per-skill sandbox. The design deliberately echoes the Claude Skills format.

### 11. Documentation and deployment ergonomics

The Fern docs tree (`fern/docs/pages/`) is broad and well-organized: getting-started (quickstart, how-it-works), per-provider guides (Ollama, llama.cpp, LM Studio, vLLM), configuration (settings, CLI, advanced), an API guide (sync/async messages, embeddings, ingestion, tools, skills), an OpenAPI-backed API reference + SDKs page, integrations (Claude Desktop/Cowork, Claude for Office, Claude Code, OpenCode), storage, and observability. The OpenAPI spec is generated and kept in sync via CI. Deployment is profile- and extras-driven: `pyproject.toml` defines a carefully layered extras graph (`sdk-openai` base shared by `llm-*`/`embedding-*`; feature groups `ingest`, `storage`, `tools`, `media`, `queue`, `database`, `observability`; the `core` flavor composes the common set, `pyproject.toml:35-295`). The multi-stage `Dockerfile` reads `ARG EXTRAS` to install only the OS packages the requested extras need, pre-caches NLTK/tiktoken/Playwright assets, and runs as a non-root user. The `Makefile` gives one-line `run`/`dev`/`prod-run`/`celery`/`flower`/`ingest`/`update-openapi-spec` targets, and a single CLI (`private-gpt serve` / `worker`) covers both API and Celery worker roles.

## Notable engineering details

- **Loop-aware DI container** (`private_gpt/di.py`): the injector is stored on the running asyncio loop when present, falling back to a lock-guarded global, with a `clean_global_injector` that calls `.close()` on every bound singleton during teardown. `auto_bind=True` keeps wiring terse.
- **"Unset means None" discipline**: repeated `model_post_init` coercions (`0`→`None`) give settings a clean tri-state without sentinel values.
- **Tokenizer caching** keyed by `mode::model_id` at the factory base (`llm/factories/base.py:55-82`), with remote vs local huggingface paths selected by `tokenizer_mode`.
- **Timing-safe auth** that degrades to a literal no-op dependency when disabled, avoiding any per-request overhead in the common local case (`server/utils/auth.py:48-69`).
- **Strict quality gates**: ruff with `ban-relative-imports = "all"` and strict flake8-type-checking, mypy `strict = true` run via the `dmypy` daemon, branch coverage on. Tests are organized to mirror the source tree (per-component, per-interceptor, per-reader, SSE, anthropic model fixtures).
- **Migrations built in** (`components/migrations/`, `components/persistence/migrations.py`) run on startup via the lifespan, with a SQLAlchemy backend.
- **Concurrency primitives** abstracted behind a semaphore manager with memory and Redis backends (`components/concurrency/`), matching the Redis/in-memory duality used in streaming.

## Caveats / rough edges (brief)

- Single-maintainer velocity: the v1 rewrite is largely one person's work, which is a sustainability consideration more than a code issue.
- Surface area is very large for a self-hostable project (Celery, Redis, Postgres, S3, RabbitMQ, Qdrant, multiple OCR/vision stacks). The extras graph and `core` flavor mitigate this, but a full-featured deployment has real operational weight.
- A few cosmetic settings-doc inconsistencies (e.g. the `ingest_mode` docstring mentions a "pipeline" mode while the Literal enumerates `simple`/`batch`/`parallel`; `settings.py:802-815`).
- Prompt caching and OAuth/organizations are explicitly listed as not-yet-supported in the Claude-API compatibility matrix (README).

## Sources consulted

- `README.md`, `CHANGELOG.md`, `pyproject.toml`, `Makefile`, `Dockerfile`, `version.txt`
- `private_gpt/settings/settings.py`, `settings/settings_loader.py`, `di.py`
- `private_gpt/components/llm/factories/{base,registry}.py`; embedding/vector_store/node_store factories; `components/model_discovery/`
- `private_gpt/server/{chat,chat_async,utils/auth}.py` routers/services; `server/utils/auth.py`
- `private_gpt/events/` + `events/sse/` + `components/streaming/`
- `private_gpt/components/engines/chat_loop/`, `server/chat/interceptors/`, `components/tools/`, `components/skills/`, `components/toolsets/`, `server/mcp/`
- `private_gpt/components/ingest/`, `components/readers/`, `components/postprocessor/`, `celery/tasks/ingestion/`
- `fern/docs/pages/` tree; `.github/workflows/`; `tests/` layout
- `gh` API for stars/forks/contributors/releases

## Open questions

- Actual measured RAG quality of the tree-node + expansion approach vs flat chunking (no benchmarks were inspected).
- Real-world operational footprint of the async-messages + Redis-stream path under concurrency (designed for it; not load-tested here).
- How complete the "basic" Skills support is relative to the full Claude Skills spec.
