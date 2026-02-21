---
title: ACE Platform Architecture Analysis - Playbooks as a Service
type: research
tags: [ace, saas, mcp, fastapi, three-agent, self-improving-ai, playbooks]
summary: Comprehensive architecture analysis of the ACE Platform, a SaaS product at aceagent.io that turns the ACE three-agent self-improvement loop into a hosted service with MCP integration, Stripe billing, and Fly.io deployment.
status: active
source: codebase-analyst
confidence: high
created: 2026-03-15
updated: 2026-03-15
---

## Executive Summary

ACE Platform is a 60K LOC SaaS product that wraps the ACE (Autonomous Capability Enhancement) research system into a hosted service at aceagent.io. The core innovation is a three-agent loop (Generator, Reflector, Curator) that produces and self-improves "playbooks," structured markdown documents containing strategies, formulas, and heuristics. The platform exposes this through both a REST API and an MCP server, allowing Claude Code users to evolve their playbooks via tool calls. The business model is tiered subscriptions ($9/$29/$79/mo) with usage metering per LLM token consumed during evolution.

## Project Metadata

| Property | Value |
|----------|-------|
| Language | Python 3.10+ (backend), TypeScript (frontend) |
| Backend Framework | FastAPI + SQLAlchemy 2.0 (async) + Celery |
| Frontend Framework | React 19 + Vite 7 + React Router 6 + TanStack Query |
| Database | PostgreSQL 16 (asyncpg for API, psycopg2 for workers) |
| Cache/Queue | Redis 7 (rate limiting + Celery broker) |
| MCP | `mcp` + `fastmcp-mount` libraries |
| Billing | Stripe (subscriptions + webhooks) |
| Auth | JWT + OAuth (Google/GitHub) + API keys |
| Deployment | Fly.io (backend + frontend as separate apps) |
| Observability | Sentry (errors), Prometheus (metrics), structured logging |
| Email | Resend |
| Total LOC | 60,096 across 221 files |
| Test LOC | 20,644 (34% of codebase) |

## Architecture

### Module Layout

```
ace_platform/           # 23,699 LOC - Hosted SaaS layer
  api/                  #  8,031 LOC - FastAPI routes, auth, middleware
    main.py             #  1,811 LOC - App factory, route registration, MCP mounting
    auth.py             #    645 LOC - Dependency injection auth system
    middleware.py        #    408 LOC - Correlation ID, timing, security headers, CSRF
    routes/             #  5,167 LOC - 10 route modules (auth, playbooks, billing, etc.)
  core/                 #  9,964 LOC - Business logic (29 files)
    evolution.py        #    502 LOC - EvolutionService: bridges ace_core agents to platform
    billing.py          #    393 LOC - Stripe checkout, portal, card setup
    rate_limit.py       #    528 LOC - Redis sliding window rate limiter
    limits.py           #    429 LOC - Tier-based feature gating and spending caps
    metering.py         #    604 LOC - LLM token usage tracking and cost aggregation
    security.py         #    283 LOC - JWT, password hashing
    webhooks.py         #    673 LOC - Stripe webhook processing
    audit.py            #    657 LOC - Audit logging for compliance
  mcp/                  #  2,188 LOC - MCP server (4 files)
    server.py           #  1,847 LOC - FastMCP server with 6 ASGI middlewares
  db/                   #  2,279 LOC - SQLAlchemy models + Alembic migrations
    models.py           #    708 LOC - 14 models
  workers/              #    773 LOC - Celery tasks
    evolution_task.py   #    352 LOC - Async evolution job processing
    auto_evolution.py   #    204 LOC - Scheduled auto-evolution checker

ace_core/               #  4,284 LOC - Research/standalone ACE system
  ace/ace.py            #  1,183 LOC - ACE orchestrator (training loops)
  ace/core/             #    874 LOC - Generator, Reflector, Curator agents
  ace/prompts/          #    306 LOC - LLM prompt templates

web/                    # 10,382 LOC - React dashboard
  src/pages/            #  7,481 LOC - 38 page components
  src/components/       #  1,327 LOC - 16 shared components
  src/utils/api.ts      #    508 LOC - Axios API client with typed methods

tests/                  # 20,644 LOC - 54 test files
```

### Data Flow

```
User (Claude Code)           User (Dashboard)
      |                            |
  MCP tools                   REST API
  (X-API-Key auth)           (JWT + OAuth)
      |                            |
      +---- FastAPI Application ---+
                    |
           +--------+--------+
           |        |        |
        Routes   MCP Server  Middleware
           |        |        (rate limit, audit,
           |        |         correlation ID)
           |        |
     +-----+--------+-----+
     |                     |
  Core Business Logic    Celery Workers
  (evolution, billing,   (evolution_task,
   limits, metering)      auto_evolution)
     |                     |
     +-----+-------+------+
           |       |
      PostgreSQL  Redis
      (data)      (rate limits, queue)
           |
        Stripe
        (billing webhooks)
```

### Key Abstractions

**1. Playbook**: The central domain object. A versioned markdown document containing bullet-pointed strategies, each with a unique ID (e.g., `[calc-00001]`) and usage counters (helpful/harmful/neutral tags). Playbooks have semantic embeddings for search/matching.

**2. Three-Agent Loop**: Generator produces answers using a playbook. Reflector analyzes correctness and tags which bullets helped or hurt. Curator proposes structural edits (ADD, UPDATE, MERGE, DELETE operations) to the playbook based on reflections.

**3. Evolution Job**: The platform's async wrapper around the three-agent loop. When a user calls `trigger_evolution`, the system gathers recent Outcomes, dispatches a Celery task that runs `EvolutionService.evolve_playbook()`, creates a new PlaybookVersion, and meters the LLM token cost.

**4. Tier/Limits System**: `SubscriptionTier` enum (FREE/STARTER/PRO/ULTRA/ENTERPRISE) with `TierLimits` dataclass controlling evolution runs, cost caps, playbook counts, and feature flags. Clean separation between what a tier allows and how usage is checked.

## The ACE Three-Agent Architecture

This is the intellectual core of the product. The system is based on a training loop where:

### Generator (`ace_core/ace/core/generator.py`, 120 LOC)
- Takes a question, the current playbook, context, and any prior reflection
- Uses a structured JSON prompt requesting reasoning, referenced bullet IDs, and a final answer
- Extracts bullet IDs from the response (JSON parse with regex fallback)
- The bullet ID tracking is what enables the feedback loop: the system knows which playbook entries were actually used

### Reflector (`ace_core/ace/core/reflector.py`, 144 LOC)
- Receives the question, Generator's reasoning trace, predicted/ground-truth answers, and the bullets used
- Tags each bullet as helpful, harmful, or neutral
- Has two prompt variants: one with ground truth (training), one without (platform/online)
- Returns structured `bullet_tags` that feed back into the playbook's usage counters

### Curator (`ace_core/ace/core/curator.py`, 236 LOC)
- Receives the current playbook, recent reflection, playbook stats (bullet counts, token usage), and a token budget
- Proposes operations: ADD new bullets, UPDATE existing ones, MERGE duplicates, DELETE unhelpful ones
- Returns valid JSON with `reasoning` and `operations` fields
- Robust error handling: invalid JSON or failed operations are skipped rather than crashing

### The Self-Improvement Loop (`ace_core/ace/ace.py`)
The `_train_single_sample` method implements the core cycle:
1. **Generate** an initial answer using the playbook
2. **Check** correctness against ground truth
3. **Reflect** on the result (runs even on correct answers to tag helpful bullets)
4. If incorrect: **retry** with reflection feedback (up to `max_num_rounds`)
5. Periodically **curate** the playbook based on accumulated reflections
6. **Re-generate** with the updated playbook to measure improvement

Three training modes:
- **Offline**: Traditional train/val/test split with periodic evaluation
- **Online**: Windowed approach where each window is tested then trained on
- **Eval-only**: Pure inference with an existing playbook

### Platform Evolution (`ace_platform/core/evolution.py`)
The platform adapts the research loop for a SaaS context:
- No ground truth available (uses `use_ground_truth=False`)
- Batch reflection: analyzes multiple Outcomes at once against the full playbook
- Token budget management per tier
- Returns `EvolutionResult` with diff metadata and per-operation token usage breakdowns

## MCP Server Implementation

This is the most architecturally interesting part for our MCP work.

### Server Construction (`ace_platform/mcp/server.py`, 1,847 LOC)

The MCP server is built with `FastMCP` and mounted inside the FastAPI app as an ASGI sub-application. The construction in `create_mcp_asgi_app()` layers six ASGI middlewares:

```
RequestDBSessionMiddleware       (injects async DB session via contextvars)
  HeaderAuthMiddleware           (extracts API key from X-API-Key or Bearer header)
    LegacySSEDeprecationMiddleware (adds deprecation headers for old SSE clients)
      MCPTransportDispatcher     (routes between Streamable HTTP and legacy SSE)
        StreamableSessionAffinityMiddleware (Fly.io session pinning for Streamable HTTP)
          LazyStreamableHTTPApp  (deferred FastMCP ASGI app)
```

### Transport Support
- **Streamable HTTP** (primary): Modern MCP transport at `/mcp`
- **Legacy SSE** (compatibility): At `/mcp/sse` + `/mcp/messages`, with deprecation window through May 2026
- `MCPTransportDispatcher` routes requests to the correct transport based on path

### Fly.io Session Affinity
Two dedicated middlewares solve the multi-machine session problem on Fly.io:
- **SSE transport** (`FlyReplayMiddleware`): Injects `fly_instance=<machine_id>` into the SSE endpoint URL, then uses `fly-replay` headers to route follow-up POSTs back to the originating machine
- **Streamable HTTP** (`StreamableSessionAffinityMiddleware`): Encodes machine ID into the `mcp-session-id` header (`session@machine_id`), strips it on inbound, adds it on outbound

This is a clean solution to a real problem. The middlewares are no-ops outside Fly.io (check for `FLY_MACHINE_ID` env var).

### MCP Mounting in FastAPI
Key detail at `ace_platform/api/main.py:443-454`:
```python
app.add_route("/mcp", MountedRootPathAdapter(mcp_app, mount_path="/mcp"), ...)
app.mount("/mcp", app=mcp_app, name="mcp")
```
The `MountedRootPathAdapter` handles exact `/mcp` requests without trailing slash redirect, preventing proxies from turning redirected POSTs into GETs (which would break Streamable HTTP initialization). The standard `.mount()` handles everything under `/mcp/`.

### OAuth Discovery Workaround
The server adds `.well-known/oauth-protected-resource` and `.well-known/oauth-authorization-server` endpoints that return spec-compliant 404 JSON responses. Claude Code's MCP client performs RFC 9728 OAuth discovery before connecting, and FastAPI's default 404 format causes a ZodError in the client. Pragmatic fix.

### MCP Tools Exposed
Seven tools registered on the FastMCP server:
- `list_playbooks`, `get_playbook`, `find_playbook` (semantic search)
- `create_playbook`, `create_version`
- `record_outcome`, `trigger_evolution`, `get_evolution_status`

Auth is via API key in HTTP headers (contextvars pattern). Each tool calls `get_api_key()` which reads from a `_request_api_key` contextvar set by `HeaderAuthMiddleware`.

### DB Session in MCP Context
`RequestDBSessionMiddleware` creates an `AsyncSession` per request and stores it in a contextvar. MCP tool handlers access it via `get_db()`. The `mcp_lifespan` also provides an `MCPContext` with a DB session for the server lifecycle.

## Platform/SaaS Patterns

### Authentication Layer (`ace_platform/api/auth.py`)
Well-designed dependency injection auth system using FastAPI's `Depends()`:

```python
# Composable auth dependencies
OptionalAuth = Depends(get_optional_auth)
RequiredAuth = Depends(require_auth)
RequiredUser = Depends(require_user)
ActiveUser = Depends(require_active_user)
VerifiedUser = Depends(require_verified_user)
PaidUser = Depends(require_paid_access)
VerifiedPaidUser = Depends(require_verified_paid_user)
AdminUser = Depends(require_admin)
```

Each builds on the previous. `AuthContext` dataclass carries user_id and scopes. Dual auth paths: JWT Bearer tokens (dashboard) and API keys (MCP/programmatic access). OAuth via Google/GitHub using `authlib`.

### Billing (`ace_platform/core/billing.py` + `stripe_config.py` + `webhooks.py`)
- Stripe Checkout for subscription creation
- Billing portal for self-service management
- Webhook processing with idempotency (`ProcessedWebhookEvent` model prevents duplicate processing)
- Tier mapping: Stripe price IDs mapped to internal `SubscriptionTier` enum
- Trial support with `has_used_trial` and `trial_ends_at` fields

### Rate Limiting (`ace_platform/core/rate_limit.py`)
Redis-based sliding window implementation. `RateLimiter` class with configurable windows per endpoint:
- Login: 5/min, 20/hour
- Register: 3/min, 10/hour
- OAuth: 10/min, 50/hour
- Evolution: 10/min, 100/hour
- Dedicated limiters for password reset, email verification, contact form, analytics events

### Usage Metering (`ace_platform/core/metering.py`, 604 LOC)
Granular LLM token tracking:
- Per-user, per-playbook, per-operation, per-model breakdowns
- Daily aggregation views
- Billing period calculations
- Spending limit enforcement tied to subscription tier
- Platform-wide admin summaries (daily totals, top spenders)

### Tiered Feature Gating (`ace_platform/core/limits.py`)
Five tiers with clear limits:
| Tier | Price | Evolutions/mo | Cost Cap | Playbooks | Premium Models |
|------|-------|---------------|----------|-----------|----------------|
| Free | $0 | 5 | $1 | 1 | No |
| Starter | $9 | 100 | $9 | 5 | Yes |
| Pro | $29 | 500 | $29 | 20 | Yes |
| Ultra | $79 | 2,000 | $79 | 100 | Yes |
| Enterprise | Custom | Unlimited | Unlimited | Unlimited | Yes |

Cost caps match subscription prices, which is a clean alignment.

### Middleware Stack (`ace_platform/api/middleware.py`)
Ordered middleware with clear documentation:
1. **CorrelationIdMiddleware** (outermost): Generates/propagates `X-Correlation-ID` for request tracing
2. **RequestTimingMiddleware**: Logs slow requests with timing in `X-Process-Time` header
3. **SecurityHeadersMiddleware**: HSTS, CSP, X-Frame-Options, etc.
4. **CORSMiddleware**: Standard CORS with explicit allowed headers
5. **SessionMiddleware** (innermost): For OAuth state

The middleware ordering documentation in `create_app()` is exemplary. Each layer's purpose and interaction is explained.

### Audit Logging (`ace_platform/core/audit.py`, 657 LOC)
30 `AuditEventType` values covering auth, playbook CRUD, billing, admin actions, and account management. `AuditSeverity` levels. Full audit trail stored in PostgreSQL.

## Testing and CI/CD

### Test Strategy
- **54 test files, 20,644 LOC** (34% of total codebase)
- Largest test: `test_mcp_server.py` (2,792 LOC, 29 test cases)
- E2E tests: `test_e2e_full_flow.py` (836 LOC), `test_e2e_billing_flow.py` (694 LOC)
- Dedicated tests for: rate limiting, auth middleware, API key auth, login lockout, webhooks, evolution idempotency, content conversion, Stripe config, billing routes, admin, logging, limits, LLM proxy, OAuth
- `pytest-asyncio` with `asyncio_mode = "auto"` for async test support
- Real Postgres + Redis in CI (service containers), no mocking of infrastructure

### CI Pipelines
**ci.yml** (push to main/dev, PRs):
- Lint + format check with ruff
- Full test suite with coverage upload to Codecov
- Postgres 16 + Redis 7 service containers
- Alembic migrations run before tests

**staging.yml** (push to main):
- Backend tests (Postgres 15 + Redis 7)
- Frontend tests (vitest) + lint + build
- Deploy backend to `ace-platform-staging` on Fly.io
- Deploy frontend to `ace-platform-web-staging` on Fly.io
- Retry logic: 3 attempts with escalating backoff
- Stale release machine cleanup (handles Fly.io deploy artifacts)
- Post-deploy health check verification

**production.yml**: Manual dispatch with confirmation gate

### Deployment Architecture
- Backend and frontend as separate Fly.io apps
- Separate staging and production environments with distinct databases
- Docker multi-stage builds (migrate, api targets)
- Celery beat for scheduled tasks (auto-evolution checks)

## Key Patterns Worth Learning From

### 1. ASGI Middleware Composition for MCP
The MCP server's middleware stack is a reference implementation for mounting MCP inside an existing web framework. The pattern of wrapping the MCP ASGI app with auth, session, and transport-dispatch middlewares is directly applicable to any project that needs to expose MCP tools alongside a REST API.

### 2. Contextvars for Request-Scoped State
Both the API and MCP server use Python `contextvars` to propagate request-scoped state (API keys, DB sessions, correlation IDs) without passing them through every function signature. This avoids polluting business logic with transport concerns.

### 3. Composable Auth Dependencies
The `auth.py` dependency chain (`OptionalAuth` -> `RequiredAuth` -> `RequiredUser` -> `ActiveUser` -> `VerifiedUser` -> `PaidUser`) is clean FastAPI practice. Each layer adds one check, and route handlers declare exactly what auth level they need.

### 4. Research-to-Product Bridge
The `EvolutionService` cleanly adapts the research `Curator` and `Reflector` for platform use. It handles the differences (no ground truth, batch processing, token metering) without modifying the core agents. The `ace_core` module remains runnable standalone.

### 5. Idempotent Webhook Processing
The `ProcessedWebhookEvent` model ensures Stripe webhooks are processed exactly once, even under retry conditions. Simple pattern, easy to overlook.

### 6. Fly.io Session Affinity via ASGI
The `FlyReplayMiddleware` and `StreamableSessionAffinityMiddleware` encode machine IDs into transport-layer identifiers (query params for SSE, header values for Streamable HTTP) and use Fly's `fly-replay` header for routing. No external session store needed.

### 7. Structured Playbook Format with Trackable Bullets
Each bullet in a playbook has a unique ID, usage counters, and section membership. This makes the self-improvement loop quantifiable. The Curator can make informed decisions about what to keep, merge, or delete based on actual usage data.

## What Could Be Improved

### 1. `main.py` is a God File (1,811 LOC)
`_register_routes` is 1,418 lines of inline route definitions that duplicate the router-based routes. The function includes full landing page HTML, inline CSS, SVG icons, and JavaScript. This should be extracted: the landing page as a static/template file, and the route registration simplified to just `include_router` calls (which already exist at lines 410-419).

### 2. MCP Server Monolith (1,847 LOC)
`ace_platform/mcp/server.py` contains middlewares, tool definitions, helper functions, auth logic, and the server factory all in one file. The middlewares alone (6 classes) deserve their own module. Tool implementations could be split by domain (playbook tools, evolution tools).

### 3. Dual Sync/Async Database Drivers
The project uses `asyncpg` for the API and `psycopg2-binary` for Celery workers. While technically necessary (Celery is sync), the `ace_platform/db/session.py` must maintain both connection paths. This increases the surface area for connection pool issues and configuration drift.

### 4. Semantic Embeddings Stored as JSONB
`Playbook.semantic_embedding` is a `JSONB` column storing a list of floats. For any meaningful volume of playbooks, this prevents efficient vector similarity search. A migration to `pgvector` would enable proper nearest-neighbor queries. The current `playbook_matching.py` (267 LOC) likely computes cosine similarity in Python.

### 5. ace_core Coupling to File System
The `ACE` class writes results, playbooks, and logs directly to the filesystem. While fine for research, this makes it harder to integrate into the platform where results should flow through the database. The `EvolutionService` works around this by calling `Curator` and `Reflector` directly rather than using the `ACE` orchestrator.

### 6. No Database Connection Pooling Configuration Exposed
The `session.py` file (161 LOC) creates engines but the pool configuration is not surfaced in `Settings`. For a production SaaS, pool size, overflow, and timeout should be tunable via environment variables.

### 7. Test Coverage Gaps
The `test_e2e_billing_flow.py` is excluded from CI (`--ignore=tests/test_e2e_billing_flow.py`). Billing is one of the highest-risk areas. The exclusion is likely due to Stripe API dependency, but a recorded/mocked integration test would be valuable.

### 8. Frontend Has No State Management Library
The frontend uses React Context + `useState` for auth state and TanStack Query for server state. For the current size this is adequate, but the 911-LOC `ApiKeys.tsx` and 709-LOC `Settings.tsx` suggest some pages are accumulating local state complexity that could benefit from extraction.

### 9. LLM Model Parameter Handling
`_run_batch_reflection` has manual branching for `max_tokens` vs `max_completion_tokens` based on model name prefixes (`gpt-4o`, `gpt-5`, `o1`, `o3`). This is fragile and will break as new models are released. Should be abstracted into a model capabilities registry.

## Relevance to Helioy

### MCP Mounting Pattern
The ASGI middleware composition pattern for mounting MCP inside FastAPI is directly transferable. The specific solutions for:
- Auth via contextvars (no MCP protocol modification needed)
- Fly.io session affinity via header/URL encoding
- Transport dispatch between Streamable HTTP and legacy SSE
- OAuth discovery endpoint workarounds for Claude Code

These are battle-tested patterns from a production MCP deployment.

### Self-Improving Agent Architecture
The three-agent loop (Generator/Reflector/Curator) with trackable bullet IDs is a concrete implementation of self-improving prompts. The key insight is making playbook entries individually addressable and measuring their contribution to outcomes. This pattern could inform how context-matters manages and evolves stored context.

### SaaS Infrastructure Patterns
The tier/limits/metering stack is a clean reference for any Helioy component that needs usage-based gating. The composable auth dependency chain is worth adopting for any FastAPI service.

## Open Questions

1. **How effective is the evolution in practice?** The platform removes ground truth from the loop (`use_ground_truth=False`). Without correctness signals, the Reflector relies on user-provided outcome status (success/partial/failure). The quality of evolution depends heavily on outcome reporting fidelity.

2. **Playbook size management at scale**: Token budget is set per tier, but there is no visible garbage collection for stale bullets beyond the Curator's DELETE operations. Long-running playbooks could accumulate noise.

3. **Auto-evolution triggers**: `auto_evolution.py` checks for playbooks with enough unprocessed outcomes and triggers evolution. The threshold (`DEFAULT_OUTCOME_THRESHOLD`) and scheduling cadence are not visible from the outline. Worth understanding if this is configurable per user.

4. **LLM proxy purpose**: `llm_proxy.py` (414 LOC) exists but its role relative to direct OpenAI client usage in `EvolutionService` is unclear. May be a routing layer for model selection or cost tracking.

5. **Content converter**: `content_converter.py` (406 LOC) with 13 exports suggests format translation between playbook representations. Its role in the MCP tool pipeline deserves investigation if adapting these patterns.
