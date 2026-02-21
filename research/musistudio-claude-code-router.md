---
title: claude-code-router senior engineering review
type: research
tags: [claude-code, router, llm-proxy, fastify, transformer, monorepo, plugin-system]
summary: Local proxy that intercepts Claude Code's HTTPS calls and re-routes them to arbitrary LLM providers via a transformer pipeline. Massive traction, weak engineering rigor.
status: active
source: github-researcher
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

# musistudio/claude-code-router

Repo: https://github.com/musistudio/claude-code-router
License: MIT
Reviewed at commit `e270dea` (HEAD of `main`, 2026-03-04).

## Executive Summary

Claude Code Router is a Fastify-based local proxy that exposes an Anthropic-compatible `/v1/messages` endpoint, intercepts every Claude Code HTTPS call by setting `ANTHROPIC_BASE_URL=http://127.0.0.1:3456`, applies a configurable router to pick a provider/model, runs the request through a transformer chain, and streams a re-encoded response back. Traction is enormous (33k stars, 2.6k forks, 121 watchers). Engineering quality lags traction by a wide margin. Grade: **C-**.

## Traction Signals

| Metric | Value | Source |
| --- | --- | --- |
| Stars | 32,989 | GitHub API, 2026-04-26 |
| Forks | 2,644 | GitHub API |
| Watchers (subscribers) | 121 | GitHub API |
| Open issues | 781 | search API |
| Closed issues | 348 | search API |
| Total PRs | 212 | search API |
| Open PRs | 121 | search API |
| Merged PRs | 32 (15%) | search API |
| Closed-not-merged PRs | 59 (28%) | search API |
| Repo created | 2025-02-25 | GitHub API |
| First commit | 2025-08-18 (history rewrite) | git log |
| Last commit | 2026-03-04 | git log |
| Bus factor | musistudio: 125 commits, TonyGeez: 15, others: ≤1 each | git shortlog |

Cadence collapse: prolific Dec 2025 (monorepo migration, presets, plugin system, tokenizer, docker, statusline added in two weeks), then a 7-week silence broken only by sponsor banner updates. The last meaningful code change is `4afa571 fix restart error` on 2026-01-06.

PR throughput is the loudest signal. 781 open issues against a project that has merged 32 PRs total. Recent closed-not-merged PRs include real upstream-quality work: byte-perfect SSE buffering (#1352), XML tool-call parsing (#1340), Windows argv preservation (#1289), TextDecoderStream insertion (#1243). The maintainer sometimes re-implements them and sometimes drops them entirely. This is a single-author project with 33k stars of demand wrapped around it.

## What It Does (read from code, not marketing)

`ccr code` does two things. (1) Calls `createEnvVariables()` (`packages/cli/src/utils/createEnvVariables.ts:7`) to produce `ANTHROPIC_BASE_URL=http://127.0.0.1:3456`, `ANTHROPIC_AUTH_TOKEN`, `DISABLE_TELEMETRY=true`, `CLAUDE_CODE_USE_BEDROCK=undefined`. (2) `spawn`s the real `claude` binary with those env vars injected via a temp `--settings` JSON file (`packages/cli/src/utils/codeCommand.ts:86`).

The local Fastify server exposes `POST /v1/messages` (`packages/core/src/server.ts:144`). Each request flows: parse `body.model` as `provider,model` (`packages/core/src/server.ts:228`); compute token count via tiktoken cl100k_base or a HuggingFace/API tokenizer (`packages/core/src/utils/router.ts:218`); run a router that picks one of `default | background | think | longContext | webSearch` based on token count, tool list, model name regex, or a `<CCR-SUBAGENT-MODEL>` tag in the system prompt; optionally hand off to a user-provided `CUSTOM_ROUTER_PATH` JS file (`packages/core/src/utils/router.ts:271`); rewrite `req.body.model`; pass through a per-provider transformer chain (`packages/core/src/api/routes.ts:55`); send to the upstream provider; transform the response back to Anthropic format; stream SSE back through `SSEParserTransform` and `SSESerializerTransform` (`packages/server/src/index.ts:252`). An optional Agent layer can intercept tool calls mid-stream and re-issue a follow-up local request (e.g. `imageAgent` for image generation, `packages/server/src/agents/image.agent.ts`).

There is also a Preset system (shareable provider+router bundles installed from a GitHub marketplace), a React/Vite Web UI served at `/ui/`, a plugin system (`token-speed`), and `ccr statusline` for live in-claude status integration.

## Architecture

Pnpm monorepo, five packages.

```
packages/
  cli/      # @CCR/cli            CLI wrapper, presets, statusline, model selector
  core/     # @musistudio/llms    Fastify server, routing, transformer chain, tokenizers
  server/   # @CCR/server         Wraps core with config dir, agents, SSE rewriting, UI
  shared/   # @CCR/shared         Constants, preset schema/install/merge/sensitive-fields
  ui/       # @CCR/ui             React 19 + Vite SPA, Monaco editor, Tailwind
docs/                             Docusaurus site (en + zh-CN)
```

The `core` package is also published to npm as `@musistudio/llms` and reused independently. `cli` depends on `server`; `server` depends on `core`; everything depends on `shared`. The UI is bundled with `vite-plugin-singlefile` and served as static assets from the server.

Key abstractions:

- `Server` class (`packages/core/src/server.ts:69`) encapsulates a `FastifyInstance` plus `ConfigService`, `ProviderService`, `TransformerService`, `TokenizerService`. The `registerNamespace()` method (line 135) is the lever for presets: each installed preset gets a fully isolated set of services mounted under `/preset/<name>`, so per-preset Provider/Router config exists in the same process without globals.
- `Transformer` interface (`packages/core/src/types/transformer.ts`): each provider gets a `transformRequestIn`, `transformRequestOut`, `transformResponseIn`, `transformResponseOut`, `auth`. 21 built-in transformers cover Anthropic, OpenAI, OpenAI Responses, Gemini, Vertex Gemini, Vertex Claude, OpenRouter, DeepSeek, Groq, Cerebras, Vercel, plus orthogonal ones (`maxtoken`, `tooluse`, `enhancetool`, `reasoning`, `forcereasoning`, `cleancache`, `sampling`, `streamoptions`, `customparams`, `maxcompletiontokens`).
- `router(req, res, ctx)` (`packages/core/src/utils/router.ts:218`) is a pure function over `(req.body, configService, sessionUsageCache)`. It writes back `req.body.model` and `req.scenarioType`. Project-level routing (`~/.claude/projects/<id>/config.json`) and session-level routing override the global `Router`.
- Preset system (`packages/shared/src/preset/`): manifest.json with `Providers`, `Router`, `schema` (input fields), `userValues` (filled-in secrets). `extractPreset` validates against zip-slip (`packages/shared/src/preset/install.ts:56`) and `validatePresetName` blocks path traversal.
- Plugin system (`packages/core/src/plugins/plugin-manager.ts`): in-process Fastify plugins with a registry-and-lifecycle pattern. Currently one plugin (`token-speed`).
- SSE pipeline (`packages/core/src/utils/sse/`): custom `Transform` streams (`SSEParserTransform`, `SSESerializerTransform`) plus a `rewriteStream` helper that lets agents synchronously edit the event stream and inject follow-up requests (`packages/server/src/index.ts:261`).

Request flow at a glance:

```
claude → ANTHROPIC_BASE_URL=127.0.0.1:3456
         → preHandler: APIKEY auth (auth.ts)
         → preHandler: split provider,model (server.ts:228)
         → preHandler: agentsManager.shouldHandle (index.ts:215)
         → preHandler: router → model+scenarioType (router.ts:218)
         → handler:   transformer chain in/out (routes.ts:55)
         → upstream:  fetch via undici/google-auth-library
         → onSend:    SSE rewrite + agent tool-call interception (index.ts:247)
         → response:  stream SSE back to claude
```

## Engineering Grade: C-

**Type discipline (D).** `tsconfig.base.json` enables `strict: true` and `noImplicitAny: true`, then 368 explicit `: any` annotations and 54 `as any` casts across 66 files dilute the guarantee. Hot paths take `req: any` (`router.ts:218`, `routes.ts`, `server/src/index.ts`). The route handlers cast `(app as any)._server` (`packages/server/src/server.ts:40`) to reach into private state. `AppConfig` is `{ [key: string]: any }` (`config.ts:16`). Strict TS is performative here.

**Error taxonomy (D).** Single `ApiError` interface with optional `statusCode/code/type` (`packages/core/src/api/middleware.ts:3`). The error handler concatenates `error.message + error.stack` into the public response body (`middleware.ts:32`). That ships full stack traces and file paths to the caller. No `Result` type, no domain-specific error classes, just `throw new Error(...)` mixed with `createApiError(...)` whose `code` is a freeform string.

**Tests (F).** Zero test files. `find . -name "*.test.*" -o -name "*.spec.*"` returns nothing. No `vitest`, `jest`, or `mocha` config. No CI for tests. The two GitHub Actions workflows (`docker-publish.yml`, `docs.yml`) build and publish artifacts; neither runs anything that could be called verification. Releases ship straight from `main`. Given that the project's job is round-tripping every byte of an LLM stream across 21 transformers and 9 providers, this is the single biggest weakness.

**Module size discipline (D).** Six files exceed the Helioy 700-line refactor threshold:

| File | LOC |
| --- | --- |
| `packages/core/src/transformer/anthropic.transformer.ts` | 1069 |
| `packages/core/src/utils/gemini.util.ts` | 1044 |
| `packages/cli/src/utils/statusline.ts` | 1026 |
| `packages/core/src/transformer/openai.responses.transformer.ts` | 792 |
| `packages/shared/src/preset/schema.ts` | 720 |
| `packages/core/src/api/routes.ts` | 692 |

Several others are in the 400 to 600 range and trending upward. Transformers in particular bundle request/response/auth/streaming for one provider into a single file; splitting them would be straightforward.

**Concurrency patterns (B-).** `Promise.all` for project-folder lookup (`router.ts:331`) instead of sequential `for await`. `LRUCache` for session-to-project mapping (max 1000) and session-usage cache. Custom `Transform` streams for SSE. The agent SSE rewriter (`packages/server/src/index.ts:261`) is genuinely tricky: it tees the upstream stream, feeds one branch to usage-tracking, and lets the other branch be edited mid-flight to splice in synthesized tool results from a re-issued local fetch. Some abort handling (`AbortController`, `ERR_STREAM_PREMATURE_CLOSE` checks). No worker threads, no cluster, single-process.

**Distribution (B).** This is the strongest area. Two distribution targets out of one repo:

1. **npm**: `@CCR/cli` for end users (gives `ccr` binary), `@musistudio/llms` for library consumers. The release script (`scripts/release.sh:75`) mutates `cli/package.json` at publish time to strip workspace dependencies, replace them with the published `@musistudio/llms` version, then restores the original. Functional but brittle. There is no version locking between the two npm packages.
2. **Docker**: `packages/server/Dockerfile` is a multi-stage Alpine build that bakes in PM2 and pm2-logrotate for in-container process supervision. CI publishes to Docker Hub on tag push (`v*.*.*`).

The Docusaurus site (`docs/`) is bilingual (en + zh-CN) and auto-deployed via `docs.yml`. There is a Discord, sponsor banners, and a preset marketplace fetched from GitHub.

**Configuration (B).** JSON5 with comments, env-var interpolation (`$VAR` and `${VAR}`) recursive through nested objects, three-deep config backups, a UI-driven editor at `/ui/`, hot reload by `ccr restart`. The Preset system layers per-preset overrides cleanly via Fastify namespaces (`server.ts:135`), which is genuinely the best architectural decision in the codebase.

## Anti-Patterns and Hazards

Findings a staff engineer would flag:

1. **Stack traces in HTTP responses.** `errorHandler` puts `error.message + error.stack` in the response body (`packages/core/src/api/middleware.ts:32`). This leaks file paths and source structure to anyone hitting `/v1/messages`.
2. **UI exposed without auth.** `apiKeyAuth` (`packages/server/src/middleware/auth.ts:8`) bypasses authentication for any URL starting with `/ui`. Combined with `HOST: 0.0.0.0` and the `/api/config` POST endpoint that overwrites the config file (`packages/server/src/server.ts:103`), any attacker on the same network with `/ui` access can rewrite providers and exfiltrate keys.
3. **Plain string compare for APIKEY.** `token !== apiKey` (`auth.ts:52`) instead of `crypto.timingSafeEqual`. Timing attack surface, low-stakes locally but an issue when `HOST` is `0.0.0.0`.
4. **`spawn(claudePath, args, { shell: true })`.** `packages/cli/src/utils/codeCommand.ts:115` uses `shell: true` with arguments that are pre-quoted via `shell-quote` and minimist-roundtripped. The argv handling has been buggy enough that PR #1289 had to fix Windows argv semantics. Local code only, but still a smell.
5. **`require(customRouterPath)` directly off config.** `router.ts:273` does `require(customRouterPath)` against a string from disk. The config file is user-owned, so this is acceptable, but the pattern shows how thin the trust boundary is.
6. **`require()` in an ESM-marked package.** `packages/core/package.json` declares `"type": "module"` yet the runtime uses `require(require.resolve(config.path))` (`packages/core/src/services/transformer.ts:88`) and `require()` for the custom router. This works only because the build output is dual (`dist/cjs` + `dist/esm`) and CJS is what gets loaded.
7. **Async constructor footgun.** `Server.constructor` (`packages/core/src/server.ts:91`) starts `transformerService.initialize().finally(() => { providerService = new ProviderService(...) })` without awaiting. If `registerNamespace` is called synchronously after construction, `providerService` is undefined and the routes blow up.
8. **`(app as any)._server` reach-around.** `packages/server/src/server.ts` calls `(app as any)._server!.tokenizerService` repeatedly to climb out of Fastify back into the `Server` instance. The proper pattern is `fastify.decorate('server', this)` once.
9. **Comments in Chinese inside published code.** CLAUDE.md mandates English comments, but `scripts/release.sh` and the Dockerfile are still half Chinese, and old transformers carry mixed-language comments. Low impact, but it tells you the contributor pipeline is mostly one person.
10. **Mutation-during-publish.** The release script literally rewrites `cli/package.json` then restores it (`scripts/release.sh:93-127`). If the publish fails mid-script the working tree is left dirty. Should be a generated `package.publish.json` consumed by `npm publish --pkg-json package.publish.json` or a build-time copy under `dist/`.
11. **15% PR merge rate.** Out of 212 PRs, 32 merged. A community is providing fixes faster than the maintainer can review or accept them. Forks are likely to win medium-term: 2.6k of them.

## Top Helioy Takeaways

### 1. Local proxy as a Claude Code interception primitive

`createEnvVariables.ts:7-22` is the entire trick. Set `ANTHROPIC_BASE_URL=http://127.0.0.1:3456` plus `ANTHROPIC_AUTH_TOKEN=anything`, spawn `claude`, and you own every request and response. No fork of Claude Code, no plugin API, no upstream cooperation needed.

**Helioy mapping.** This is the right pattern for any helioy-bus or helioy-plugins surface that needs to observe or modify Claude Code's traffic without forking. nancyr can use the same approach to inject context-matters lookups, attention-matters retrievals, or fmm symbol resolutions before Claude even sees the request. The local Anthropic-compatible endpoint is the cheapest possible MITM.

Cite: `packages/cli/src/utils/createEnvVariables.ts:7`, `packages/core/src/server.ts:144`, `packages/cli/src/utils/codeCommand.ts:86`.

### 2. Fastify namespaces as a clean per-tenant config boundary

`Server.registerNamespace()` (`packages/core/src/server.ts:135`) constructs a fresh `ConfigService`/`ProviderService`/`TransformerService`/`TokenizerService` triple per preset and mounts them under `/preset/<name>` via `app.register(plugin, { prefix })`. No singletons, no module-level state, no per-request branching. Each preset is fully isolated in the same process.

**Helioy mapping.** This is the cleanest answer to "how do I run multiple isolated configs in one process" that I have seen in this stack. The upcoming installer and helioy-plugins should adopt this exact pattern when one process needs to host multiple agent profiles or scopes (e.g. a shared `cm` server hosting per-project scopes). It also informs how nancyr can run multiple tenant graphs without bleed.

Cite: `packages/core/src/server.ts:135-196`.

### 3. Preset = manifest + schema + userValues, distributed via GitHub archive

Presets (`packages/shared/src/preset/`) are directories with a `manifest.json` containing config, a `schema` array of input fields, and a separate `userValues` object holding user-provided secrets. Installation downloads `https://github.com/<owner>/<repo>/archive/refs/heads/main.zip`, validates manifest, extracts with zip-slip protection (`install.ts:56`), and the marketplace itself is just a curated JSON list fetched at request time.

**Helioy mapping.** This is the distribution shape for knowledge-matters packs, attention-matters preset memories, fmm language-config bundles, or the future installer's "bundle of skills + memories + commands". Stuart's existing instinct (`feedback_provider_plumbing_duplication`, `project_notebooklm_py_lessons` env-var profile triad) lines up with this. The `userValues` separation also matters: it keeps secrets out of the redistributable manifest. Helioy's installer should adopt the same `manifest + schema + userValues` triple instead of inventing a new package format.

Cite: `packages/shared/src/preset/install.ts:73`, `packages/shared/src/preset/types.ts`, `packages/server/src/server.ts:364` (GitHub install endpoint).

### 4. Anti-pattern: 33k stars without tests is a stable equilibrium when traction outruns rigor

Zero test files, 781 open issues, 15% PR merge rate, and the project still grows. The lesson for Helioy is the inverse: this is what happens when you optimize for distribution and not engineering. A small project with tests, fast PR throughput, and a coherent grammar will out-compound a viral one over a 12-month window. fmm, cm, am, mdm should not chase claude-code-router's reach without first establishing a test discipline that the maintainer here never bothered to install.

Cite: `find . -name "*.test.*"` returns empty; `.github/workflows/` has no test workflow; PR throughput from search API.

## Dependencies (notable)

- `fastify` 5.x with `@fastify/cors`, `@fastify/static`, `@fastify/multipart`. Reasonable default.
- `@anthropic-ai/sdk` 0.54, `openai` 5.6, `@google/genai` 1.7, `google-auth-library` 10.1: each provider's official SDK, used selectively.
- `tiktoken` 1.0 (cl100k_base) + `@huggingface/tokenizers` 0.0.6 for HF tokenization. Tokenizer service can hot-swap.
- `undici` 7.10 for outbound fetches.
- `lru-cache` 11 for session caches.
- `json5` for config (comments-in-config), `jsonrepair` for malformed JSON tool args.
- `adm-zip` for preset archive handling, `archiver` for export.
- React 19 + Vite 7 + Tailwind 4 + Monaco for the UI.

## Sources Consulted

- `README.md`, `CLAUDE.md`, `docs/docs/`
- `packages/core/src/server.ts`, `utils/router.ts`, `services/{config,provider,transformer}.ts`, `api/{routes,middleware}.ts`, `plugins/plugin-manager.ts`
- `packages/server/src/{index,server}.ts`, `middleware/auth.ts`, `agents/image.agent.ts`
- `packages/cli/src/cli.ts`, `utils/{codeCommand,createEnvVariables,activateCommand}.ts`
- `packages/shared/src/preset/{install,schema,types}.ts`
- `scripts/release.sh`, `packages/server/Dockerfile`, `.github/workflows/`
- GitHub API: stars, forks, watchers, issues, PRs, contributors, search counts as of 2026-04-26

## Open Questions

1. Is `@musistudio/llms` (the core npm package) used anywhere other than this repo? If yes, the API surface matters more than this review treats it.
2. The 7-week silence on `main`: is the maintainer waiting to merge `feature/2.0` (still referenced in the log) or is the project drifting toward a long-tail of forks? A check of fork activity (gh api `/repos/.../forks?sort=newest`) would tell.
3. The `@CCR/cli` scoped name implies a private scope, yet the publish script uses `--access public`. Worth verifying whether `npm install -g @musistudio/claude-code-router` (the README's published entry point) actually resolves to this scope or to a different binary.
