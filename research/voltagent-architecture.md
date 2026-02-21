---
title: VoltAgent Architecture & Repository Structure
date: 2026-03-13
tags: [voltagent, architecture, monorepo, typescript]
---

## Overview

VoltAgent is a comprehensive open-source TypeScript framework for building and orchestrating AI agents with built-in support for memory, tools, observability, and sub-agent capabilities. The repository is structured as a pnpm monorepo managed by Lerna (Nx) containing 35+ packages for core framework functionality, database integrations, server implementations, and telemetry exporters.

**Key Facts:**
- Monorepo version: 0.1.0
- Language: TypeScript 5.8.2
- Node requirement: >=20
- pnpm requirement: >=8
- License: MIT
- Package Manager: pnpm 8.10.5

---

## Monorepo Structure

Located at `/Users/alphab/Dev/LLM/DEV/helioy/REF/voltagent/`

```
voltagent/
├── packages/              # 35 core packages and integrations
├── examples/              # 89 example implementations
├── website/               # Docusaurus documentation site
├── docs/                  # Project-level documentation
├── scripts/               # Reusable build and utility scripts
├── .changeset/            # Changesets configuration for versioning
└── package.json           # Root monorepo configuration
```

The pnpm workspace includes: `packages/*`, `examples/*`, `examples/*/client`, and `examples/*/server`

---

## Package Inventory

### Core Framework Packages

**@voltagent/core (v2.6.8)** — `/packages/core`
- Primary agent framework with orchestration, memory management, tools, and OpenTelemetry tracing
- Key features: ConversationBuffer (merges model/tool messages), MemoryPersistQueue (debounced writes)
- 20+ AI SDK providers: Anthropic, OpenAI, Google, Groq, Bedrock, Cerebras, Cohere, DeepInfra, Mistral, etc.
- Dependencies: ai@^6.0.0, zod, ts-pattern, uuid, fast-glob, gray-matter, micromatch, type-fest

**@voltagent/server-core (v2.1.10)** — `/packages/server-core`
- Framework-agnostic server core for handling API requests, schemas, and business logic
- Framework-independent design with edge-function support
- Dependencies: @voltagent/core, ai, jsonwebtoken, ws (WebSockets), zod-from-json-schema

**@voltagent/internal (v1.0.3)** — `/packages/internal`
- Shared internal utilities used across the monorepo
- Provides: `safeStringify` function (replaces JSON.stringify as required by policy)
- Multiple export paths: main, test, utils, a2a, mcp, types
- Minimal external dependencies: only type-fest

**@voltagent/sdk (v2.0.2)** — `/packages/sdk`
- Client SDK for interacting with VoltAgent APIs
- Dependencies: @voltagent/core, @voltagent/internal

### Server Implementation Packages

**@voltagent/server-hono (v2.0.7)** — `/packages/server-hono`
- Hono-based HTTP server with OpenAPI/Swagger support
- Dependencies: hono, @hono/node-server, @hono/swagger-ui, openapi3-ts
- Depends on: core, internal, a2a-server, mcp-server, resumable-streams, server-core

**@voltagent/server-elysia (v2.0.6)** — `/packages/server-elysia`
- Elysia framework implementation (alternative to Hono)
- Dependencies: elysia, @elysiajs/cors, @elysiajs/swagger, @sinclair/typebox

**@voltagent/serverless-hono (v2.0.9)** — `/packages/serverless-hono`
- Fetch-based (edge-runtime) implementation with Hono
- Dependencies: hono, server-core, resumable-streams, internal

### Protocol and Communication Packages

**@voltagent/mcp-server (v2.0.2)** — `/packages/mcp-server`
- Model Context Protocol server implementation
- Exposes agents, tools, and workflows via MCP standard
- Dependencies: @modelcontextprotocol/sdk, internal

**@voltagent/a2a-server (v2.0.2)** — `/packages/a2a-server`
- Agent-to-Agent protocol server implementation
- Dependencies: @a2a-js/sdk, internal, zod

**@voltagent/docs-mcp (v2.0.2)** — `/packages/docs-mcp`
- Documentation server via MCP (CLI tool and library)
- Bin: `voltagent-docs-mcp`
- Dependencies: @modelcontextprotocol/sdk, zod

### Database and Memory Integration Packages

**@voltagent/postgres (v2.1.2)** — `/packages/postgres`
- PostgreSQL memory provider; dependencies: pg@^8.16.0, internal
- Includes integration tests with Docker Compose

**@voltagent/libsql (v2.1.2)** — `/packages/libsql`
- LibSQL/Turso memory provider; dependencies: @libsql/client, internal
- Exports edge-compatible variant for serverless

**@voltagent/supabase (v2.1.3)** — `/packages/supabase`
- Supabase client integration; dependencies: @supabase/supabase-js, internal, ts-pattern

**@voltagent/cloudflare-d1 (v2.1.2)** — `/packages/cloudflare-d1`
- Cloudflare D1 memory provider for edge environments
- Dependencies: @cloudflare/workers-types, internal

**@voltagent/voltagent-memory (v1.0.4)** — `/packages/voltagent-memory`
- VoltOps-backed managed memory adapter

### Observability and Telemetry Packages

**@voltagent/logger (v2.0.2)** — `/packages/logger`
- Universal logger built on Pino with OpenTelemetry instrumentation
- Dependencies: pino, pino-pretty, @opentelemetry/* packages, internal

**@voltagent/langfuse-exporter (v2.0.3)** — `/packages/langfuse-exporter`
- OpenTelemetry SpanExporter for Langfuse integration
- Dependencies: @opentelemetry/core, langfuse

**@voltagent/vercel-ai-exporter** — `/packages/vercel-ai-exporter`
- Telemetry exporter for Vercel AI SDK (excluded from default builds)

### Evaluation and Tooling Packages

**@voltagent/evals (v2.0.4)** — `/packages/evals`
- Evaluation orchestrator utilities
- Dependencies: scorers, sdk, internal

**@voltagent/scorers (v2.1.0)** — `/packages/scorers`
- Re-exports from Viteval's prebuilt scorer set (autoevals)
- Dependencies: @voltagent/core, internal, autoevals

**@voltagent/rag (v1.0.2)** — `/packages/rag`
- Chunking and RAG utilities for text retrieval
- Dependencies: js-tiktoken

**@voltagent/resumable-streams (v2.0.2)** — `/packages/resumable-streams`
- Stream resumption utilities with Redis backing
- Dependencies: core, internal, redis, resumable-stream

### Specialized Feature Packages

**@voltagent/voice (v2.1.0)** — `/packages/voice`
- Voice interaction capabilities
- Dependencies: elevenlabs, openai, @xsai/generate-speech, @xsai/generate-transcription

**@voltagent/ag-ui (v1.0.5)** — `/packages/ag-ui`
- AG-UI adapter for VoltAgent and CopilotKit runtimes
- Dependencies: rxjs, AG-UI components, CopilotKit runtime

**@voltagent/sandbox-e2b (v2.0.2)** — `/packages/sandbox-e2b`
- E2B sandbox provider for code execution

**@voltagent/sandbox-daytona (v2.0.1)** — `/packages/sandbox-daytona`
- Daytona sandbox provider

### CLI and Scaffolding Packages

**@voltagent/cli (v0.1.21)** — `/packages/cli`
- Command-line tool (`volt` command) for project scaffolding and management
- Dependencies: evals, sdk, internal, commander, inquirer, chalk, boxen, figlet, dotenv, semver

**create-voltagent-app (v0.2.19)** — `/packages/create-voltagent-app`
- Project initialization tool (`create-voltagent` / `create-voltagent-app`)
- Dependencies: chalk, commander, inquirer, figlet, ora, boxen, fs-extra, tar, uuid, posthog-node

---

## Package Dependency Graph

### Core Dependency Hierarchy

```
@voltagent/internal (v1.0.3)
  └─ Consumed by: nearly ALL packages
     Dependencies: type-fest (minimal)

@voltagent/core (v2.6.8)
  └─ Consumed by: server-core, sdk, most specialized packages
     Dependencies: 20+ AI SDKs, zod, ts-pattern, uuid, OpenTelemetry

@voltagent/server-core (v2.1.10)
  └─ Consumed by: server-hono, server-elysia, serverless-hono
     Dependencies: core, internal, ai, jsonwebtoken, ws

@voltagent/resumable-streams (v2.0.2)
  └─ Consumed by: server-hono, server-elysia, serverless-hono

@voltagent/a2a-server (v2.0.2)
  └─ Consumed by: server-hono, server-elysia

@voltagent/mcp-server (v2.0.2)
  └─ Consumed by: server-hono, server-elysia

@voltagent/sdk (v2.0.2)
  └─ Consumed by: cli, evals

@voltagent/scorers (v2.1.0)
  └─ Consumed by: evals

@voltagent/evals (v2.0.4)
  └─ Consumed by: cli

@voltagent/logger (v2.0.2)
  └─ Optional peer dependency for core
     Consumed by: libsql, supabase, cloudflare-d1
```

### Peer Dependencies Pattern

Most framework packages declare `@voltagent/core` as a peer dependency. This allows flexible version management and prevents version conflicts in consumer applications:
- server-core, server-hono, server-elysia, serverless-hono
- postgres, libsql, supabase, cloudflare-d1, voltagent-memory
- voice, sandbox-e2b, ag-ui, mcp-server, scorers

### AI Provider Integrations (in @voltagent/core)

All via Vercel AI SDK (`@ai-sdk/*`):
- `@ai-sdk/anthropic@^3.0.0`
- `@ai-sdk/openai@^3.0.0`
- `@ai-sdk/google@^3.0.0`, `@ai-sdk/google-vertex@^3.0.25`
- `@ai-sdk/groq@^3.0.0`
- `@ai-sdk/amazon-bedrock@^3.0.0`
- `@ai-sdk/azure@^3.0.12`
- `@ai-sdk/cohere@^3.0.8`
- `@ai-sdk/mistral@^3.0.0`
- `@ai-sdk/perplexity@^3.0.8`
- `@ai-sdk/togetherai@^2.0.13`
- `@ai-sdk/xai@^3.0.26`
- `@ai-sdk/cerebras@^2.0.14`
- `@ai-sdk/deepinfra@^2.0.13`
- `@ai-sdk/gateway@^3.0.16`
- `ollama-ai-provider-v2@^1.5.3`
- `workers-ai-provider@^3.0.2`
- Plus GitLab, SAP, AiHubMix providers

---

## Build System & Tooling

| Tool | Version | Purpose |
|---|---|---|
| pnpm | 8.10.5 | Package manager, workspaces |
| Lerna | 7.4.2 | Monorepo orchestration |
| Nx | 20.4.6 | Build graph and caching |
| tsup | 8.5.0 | TypeScript bundling (ESM + CJS) |
| TypeScript | 5.8.2 | Language |
| Biome | 1.9.4 | Linting + formatting (replaces ESLint + Prettier) |
| Vitest | 3.2.4 | Test framework |
| Husky | 8.0.3 | Git hooks |
| Changesets | ^2.28.1 | Versioning and changelogs |
| syncpack | 13.0.2 | Version consistency across packages |

### Root Build Commands

```bash
pnpm build:all          # Build all packages (excludes vercel-ai-exporter, serial -c 1)
pnpm test:all           # Test all @voltagent/* packages
pnpm lint               # Biome check
pnpm lint:fix           # Auto-fix linting
pnpm dev                # Watch mode for all packages
pnpm coffee             # Full reset and rebuild
pnpm clean              # Clean builds and node_modules
pnpm publint:all        # Package export validation
pnpm attw:all           # Type compatibility check
```

All packages export both ESM (`.mjs`) and CommonJS (`.js`) with TypeScript declarations for both formats.

---

## Key Design Principles

1. **Framework Agnostic** — Core is transport-agnostic; server implementations (Hono, Elysia, serverless) share server-core

2. **AI Provider Abstraction** — Unified interface via Vercel AI SDK; 20+ LLM providers supported without core changes

3. **Memory Provider Abstraction** — Database-agnostic persistence; multiple backends with edge-compatible variants

4. **Observable by Default** — OpenTelemetry built into core; multiple exporter support (Langfuse, Vercel AI)

5. **Protocol-First** — MCP and A2A protocol support for standard-based interoperability

6. **Type Safety First** — Strict TypeScript throughout; Zod for schema validation at API boundaries

7. **Modular Opt-In** — Most integrations are peer dependencies; minimal core footprint with pluggable capabilities

8. **Performance-Focused Persistence** — ConversationBuffer pattern, MemoryPersistQueue with debouncing to avoid write thrashing, resumable streams via Redis

9. **Dual-Format Exports** — All packages ship ESM + CJS with conditional exports

10. **Strict Code Policy** — Never use `JSON.stringify`; use `safeStringify` from `@voltagent/internal`

---

## Notable Implementation Details

- **ConversationBuffer** merges rapid model/tool exchanges into consolidated UI messages for efficient persistence
- **MemoryPersistQueue** with debouncing prevents database thrashing on high-frequency updates
- **Read-Only Memory Mode** — added in commit faa5023a for runtime memory operation
- **Sandbox Providers** — E2B and Daytona for safe code execution within agents
- **Voice Capabilities** — ElevenLabs and OpenAI integration for speech synthesis and transcription
- **Evaluation Framework** — Integration with Viteval (autoevals) for agent quality assessment
- **OpenAPI Support** — Server implementations auto-generate OpenAPI/Swagger documentation
- **Edge Compatibility** — LibSQL and Cloudflare D1 packages enable deployment to edge functions

---

## Examples Directory

The `/examples` directory contains 89 reference implementations:

- **Base:** Foundational starter template
- **Integration patterns:** with-anthropic, with-amazon-bedrock, with-google-ai, with-auth
- **Data source integrations:** with-airtable, with-chroma, with-postgres
- **UI frameworks:** with-assistant-ui, with-chat-sdk, with-ag-ui
- **Specialized:** with-ad-creator, with-github-repo-analyzer, with-github-star-stories
- **Full stack:** next-js-chatbot-starter-template, with-agent-tool

All examples follow the naming convention: `with-{integration-or-feature}`
