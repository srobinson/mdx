# mdcontext Architecture Review

**Date**: 2026-03-13
**Scope**: Full codebase review of `/Users/alphab/Dev/LLM/DEV/helioy/mdcontext`
**Version**: 0.2.0

## Executive Summary

mdcontext is a well-structured TypeScript project that provides markdown indexing, search (keyword, semantic, and hybrid), summarization, and MCP server capabilities for LLM consumption. The codebase demonstrates strong fundamentals: strict TypeScript configuration, Effect-based error handling, a coherent domain model, and professional configuration management. Several architectural issues warrant attention, primarily around module boundary clarity, code duplication in the semantic search layer, the dual summarization subsystem, and a types.ts file that has accumulated responsibilities beyond its natural scope.

---

## 1. Overall Architecture

### Pattern: Layered Architecture with Effect-TS

The project follows a layered architecture:

```
CLI Layer (src/cli/)           -- User interaction, argument parsing
MCP Layer (src/mcp/)           -- Machine interaction, protocol handling
Service Layer (src/config/)    -- Configuration, dependency injection
Domain Layer (src/core/, src/types/, src/embeddings/types.ts)
                               -- Domain types and abstractions
Infrastructure (src/embeddings/, src/search/, src/index/, src/parser/)
                               -- Concrete implementations
```

**Strengths:**
- Effect-TS is used consistently for error handling and dependency injection throughout the service and infrastructure layers.
- The `ConfigService` Context.Tag pattern provides clean DI with testable layers.
- The CLI and MCP layers serve as clean boundary adapters.

**Concern: Mixed paradigms at the embedding layer**. The `EmbeddingProvider` interface (line 20-24 of `src/embeddings/types.ts`) returns plain `Promise<EmbeddingResult>` while the rest of the codebase uses Effect. The `wrapEmbedding` function in `src/embeddings/openai-provider.ts:404-421` exists solely to bridge this gap. This forces every call site to wrap provider operations, adding ceremony. The provider interface should ideally return Effect values directly, or a dedicated adapter layer should handle the translation once rather than at each call site.

---

## 2. Module Boundary Analysis

### 2.1 src/core/ (2 files, 114 LOC) -- Underdeveloped

`src/core/` contains only `types.ts` (the domain model) and `index.ts` (a one-line re-export). The domain model defines `MdDocument`, `MdSection`, `MdLink`, `MdCodeBlock`, and `DocumentMetadata`. These types are well-designed with `readonly` properties throughout.

**Issue:** The `ParseError` type at `src/core/types.ts:93-113` conflicts with the Effect-based `ParseError` at `src/errors/index.ts:199-209`. The comment at line 87-92 acknowledges this explicitly. Having two `ParseError` types with the same `_tag` but different inheritance chains creates confusion and potential bugs if the wrong one is imported.

**Recommendation:** Consolidate the plain `ParseError` interface into the Effect error system or rename one to disambiguate (e.g., `ParserError` for the plain interface).

### 2.2 src/types/ (1 file, 66 LOC) -- Phantom

`src/types/` does not exist at the path `src/types/index.ts`. The topology listing suggests 66 LOC, but the read returned "File does not exist." This may be a stale reference or a file that was moved.

### 2.3 src/embeddings/types.ts (360 LOC) -- Overloaded

This file has grown beyond its stated purpose of "Embedding types for mdcontext." It contains:

1. Provider interfaces (`EmbeddingProvider`, `EmbeddingProviderWithMetadata`) -- appropriate
2. Vector index types (`VectorEntry`, `VectorIndex`, `HnswIndexParams`) -- appropriate
3. Quality mode constants (`QUALITY_EF_SEARCH`) -- borderline, constants with behavior
4. Search option/result types (`SemanticSearchOptions`, `SemanticSearchResult`) -- should live in semantic-search module
5. **Business logic functions**: `preprocessQuery`, `calculateHeadingBoost`, `calculateFileImportanceBoost`, `calculateRankingBoost` -- clearly does not belong in a types file

The ranking boost logic (lines 196-277) and query preprocessing (lines 283-307) are algorithms with constants and computation. Placing them in `types.ts` violates the single responsibility principle and makes it harder to find where ranking behavior is defined.

**Recommendation:** Extract search-specific types to `src/embeddings/search-types.ts` or co-locate with `semantic-search.ts`. Move ranking/boost functions to a dedicated `src/embeddings/ranking.ts` module. Move `preprocessQuery` to `src/embeddings/query-preprocessing.ts` (the empty section heading at line 190 suggests this was planned).

### 2.4 src/summarize/ vs src/summarization/ -- Dual Subsystem

Two separate summarization modules exist:

- `src/summarize/` (6 files, 2169 LOC): Token-budget-based compression. Produces structured `DocumentSummary` objects. Exports `summarizeFile`, `formatSummary`, `assembleContext`.
- `src/summarization/` (16 files, 3071 LOC): AI-powered summarization via CLI tools or API providers. Has its own type system, error types, cost estimation, prompt management, and provider factory.

These modules serve genuinely different purposes (deterministic compression vs. LLM summarization), but the naming creates confusion. The `SummarizationConfig` in schema.ts (line 321) controls `src/summarize/` while `AISummarizationConfig` (line 421) controls `src/summarization/`. A developer encountering this codebase for the first time would struggle to understand which is which.

**Worse, `src/summarization/types.ts` defines its own error class:**

```typescript
// src/summarization/types.ts:164-174
export class SummarizationError extends Error {
  constructor(
    message: string,
    public readonly code: SummarizationErrorCode,
    ...
  )
}
```

This breaks the project's established pattern of using `Data.TaggedError` from Effect. The `SummarizationError` class is a plain `Error` subclass with mutable properties, no `_tag` discriminant, and no integration with the `MdContextError` union in `src/errors/index.ts`. It also duplicates error codes that partially overlap with the centralized `ErrorCode` enum.

**Similarly, `src/summarization/types.ts` re-declares:**
- `CLIProviderName` (already in `src/config/schema.ts:391-397`)
- `APIProviderName` (already in `src/config/schema.ts:402-408`)
- `AISummarizationConfig` (already in `src/config/schema.ts:421-479`)

**Recommendation:**
1. Rename `src/summarize/` to `src/context-assembly/` or similar to clarify intent.
2. Migrate `SummarizationError` to `Data.TaggedError` and add it to the `MdContextError` union.
3. Remove duplicated type definitions from `src/summarization/types.ts`, importing from `src/config/schema.ts` instead.

### 2.5 src/integration/ (1 file) -- Misleading

This directory contains only `search-keyword.test.ts`. The topology listing shows 678 LOC but it is a test file, not production code. The directory name "integration" suggests cross-module integration, but it only holds a test. This should be relocated to a test directory or renamed.

---

## 3. Configuration Management (src/config/)

### Strengths

The configuration system is the most mature subsystem in the codebase.

- **Effect Config combinators** (`Config.all`, `Config.nested`, `Config.withDefault`) provide compile-time tracking of config requirements.
- **Precedence chain** is well-documented in `src/config/precedence.ts`: CLI flags > env vars > config file > defaults.
- **ConfigService** uses Effect's `Context.Tag` pattern with `Layer` for clean DI.
- **Testing utilities** (`TestConfigLayer`, `withTestConfig`, `runWithConfig`) in `src/config/testing.ts` show mature test infrastructure.
- **File provider** handles multiple config formats (TS, JS, MJS, JSON) with proper async/sync loading paths.
- **Validation** catches unrecognized config keys with helpful error messages (`src/cli/main.ts:238-251`).

### Concern: Config Schema Type Duplication

`EmbeddingProvider` is defined as a type alias in `src/config/schema.ts:148-154` and is imported by both `src/embeddings/provider-constants.ts:8` and `src/cli/error-handler.ts:20`. The type is also effectively redefined inline within `SemanticSearchOptions.providerConfig` at `src/embeddings/types.ts:135-143` with the same literal union. These should reference a single canonical definition.

### Concern: `Option<string>` in Default Config

The `defaultConfig` object in `src/config/schema.ts:546-603` uses `Option.none()` for optional fields like `baseURL`, `apiKey`, and `root`. While correct for the Effect type system, this creates friction when constructing configs manually (e.g., in tests or CLI overrides). The `PartialMdContextConfig` type in `src/config/service.ts:185-187` helps but uses `Partial` at one level of depth, which does not deeply handle `Option` fields. The `mergeWithDefaults` function (`src/config/service.ts:210-223`) uses shallow spreading, which would lose `Option.none()` if a partial config provides `undefined` for an optional field. This is a subtle correctness risk.

---

## 4. Error Handling (src/errors/)

### Strengths

The error system is exceptionally well-designed:

- **Comprehensive taxonomy** with categorized error codes (E1xx through E9xx).
- **Tagged errors** using `Data.TaggedError` enable exhaustive pattern matching at `src/cli/error-handler.ts:136-418` using `Match.exhaustive`.
- **Structured error data** (e.g., `ConfigError` carries `field`, `expectedType`, `actualValue`, `validValues`) enables rich user-facing messages without embedding formatting in the error types themselves.
- **Clear separation** between technical error data and user-facing presentation. The comment block at `src/errors/index.ts:11-36` documents this convention well.
- **Union types** (`FileSystemError`, `ApiError`, `IndexError`, `SearchError`, `MdContextError`) allow error handling at different granularity levels.

### Concern: Inconsistent Error Propagation

The `SummarizationError` class in `src/summarization/types.ts:164-174` operates outside this system entirely. Functions in `src/summarization/` throw plain errors or `SummarizationError` instances, which cannot be caught by `catchTag` or matched exhaustively. Any code calling summarization functions must handle these separately from the Effect error channel.

### Concern: DimensionMismatchError Missing from createErrorHandler

The `createErrorHandler` function at `src/cli/error-handler.ts:507-526` does not include a handler for `DimensionMismatchError`. The `formatError` function handles it (line 364-376), but the handler map used by `catchTags` is incomplete. If a command catches errors via `createErrorHandler()`, `DimensionMismatchError` will fall through to the generic error handler. This is a bug.

---

## 5. MCP Server (src/mcp/server.ts)

### Strengths

- Clean tool definitions with proper JSON Schema input specifications.
- Correct use of `CallToolRequestSchema` and `ListToolsRequestSchema` from the MCP SDK.
- Graceful shutdown handling with `SIGINT` and `SIGTERM`.
- The `catchAll` at the MCP boundary is appropriate and documented with comments explaining why.

### Concern: Monolithic File

At 612 lines, `server.ts` handles tool definitions, tool handler implementations, server setup, and the main entry point. Each tool handler is a standalone function with repeated patterns (path resolution, Effect.runPromise, catchAll, error formatting). This could be extracted into separate handler modules with a shared utility for the Effect-to-MCP-response conversion pattern.

### Concern: Hardcoded Default Provider

The MCP handler for `md_search` (line 216-224) calls `semanticSearch` without passing any provider configuration. The function falls back to `{ provider: 'openai' }` hardcoded in `semantic-search.ts:722`. This means the MCP server ignores the user's config file for provider selection. There should be config loading in the MCP server startup, similar to the CLI.

### Concern: No Config Loading in MCP

The MCP server at `src/mcp/server.ts:588-612` uses `process.cwd()` as rootPath but does not load any configuration. The CLI has a sophisticated config loading pipeline (file detection, env vars, precedence chain). The MCP server bypasses all of this. Users cannot configure embedding providers, search thresholds, or other settings when using the MCP interface.

---

## 6. Semantic Search Code Duplication

`src/embeddings/semantic-search.ts` is 1270 lines and contains significant internal duplication.

`semanticSearch` (lines 691-878) and `semanticSearchWithStats` (lines 897-1093) share approximately 85% of their logic. Both functions:
1. Resolve root path
2. Get active namespace
3. Create embedding provider
4. Verify dimension match
5. Load vector store
6. Check HNSW mismatch
7. Handle HyDE query expansion
8. Preprocess query
9. Embed query
10. Search vector store
11. Apply path filter
12. Apply ranking boost
13. Sort and limit results
14. Optionally load context lines

The only difference is that `semanticSearchWithStats` calls `vectorStore.searchWithStats` instead of `vectorStore.search` and includes below-threshold stats in the return value.

**Recommendation:** Extract the shared pipeline into a private function and have both public functions call it with a flag or generic parameter to control stats inclusion.

---

## 7. Build and Tooling

### package.json

**Build system:** tsup with three entry points (`cli/main.ts`, `mcp/server.ts`, `index.ts`). Clean separation between CLI binary, MCP binary, and library exports.

**Dependencies of note:**
- `effect` (core framework) -- well-integrated
- `hnswlib-node` (native addon with postinstall rebuild) -- operational risk; native addons complicate CI and cross-platform distribution
- `wink-bm25-text-search` -- keyword search, has a `.d.ts` declaration in `src/search/wink-bm25.d.ts` indicating the library lacks official TypeScript types
- `openai` SDK -- used for all OpenAI-compatible providers (correct decision)

**Concern: `postinstall` script.** The `rebuild-hnswlib.js` script runs on every `npm install`. For library consumers who only use the keyword search or summarization features, this native addon compilation is unnecessary overhead and a potential installation failure point.

### tsconfig.json

Excellent strictness settings:
- `strict: true`
- `exactOptionalPropertyTypes: true`
- `noUncheckedIndexedAccess: true`
- `noUnusedLocals: true`
- `noUnusedParameters: true`

These settings provide strong compile-time guarantees.

### biome.json

Two rules are disabled:
- `noExplicitAny: off` -- acceptable for a project with Effect-TS patterns that sometimes require escape hatches
- `noNonNullAssertion: off` -- more concerning, as `noUncheckedIndexedAccess` in tsconfig partially compensates but non-null assertions can hide runtime errors

---

## 8. Dependency Direction

The dependency graph flows cleanly in most cases:

```
cli/ --> config/, embeddings/, search/, index/, summarize/, summarization/
mcp/ --> embeddings/, search/, index/, parser/, summarize/
embeddings/ --> config/, errors/, index/, utils/
search/ --> embeddings/, errors/, index/
index/ --> errors/, parser/
summarize/ --> parser/, utils/
config/ --> (standalone, leaf dependency)
errors/ --> (standalone, leaf dependency)
core/ --> (standalone, leaf dependency)
```

**No circular dependencies detected.** The layering is sound.

**Concern:** `src/embeddings/provider-factory.ts:10` imports from `../config/index.js` using `ConfigService` and `EmbeddingProvider`. The `EmbeddingProvider` re-exported from config is the schema type, while `src/embeddings/types.ts` defines the `EmbeddingProvider` interface (the runtime contract). These are different things with the same name. The import at line 15 (`import type { EmbeddingProvider as EmbeddingProviderInterface } from './types.js'`) shows the rename needed to disambiguate. This naming collision should be resolved at the source.

---

## 9. Scalability Assessment

The architecture handles its target workload well (indexing and searching markdown corpora up to thousands of documents). Key scalability considerations:

- **Embedding batching** (`src/embeddings/batching.ts`) properly respects both item count and token budget limits per batch. The 250K token safety margin (`OPENAI_COMPATIBLE_SAFE_BATCH_TOKENS`) is conservative and appropriate.
- **Incremental indexing** in `buildEmbeddings` skips files when vectors already exist (cache-hit logic at lines 357-379).
- **HNSW vector store** provides O(log n) approximate nearest neighbor search, appropriate for the scale.
- **File caching** in `addContextLinesToResults` (line 601) avoids repeated reads of the same file.

**Limitation:** The entire section index is loaded into memory (`loadSectionIndex`). For very large corpora (tens of thousands of documents), this could become a memory bottleneck. The MessagePack serialization (`@msgpack/msgpack`) helps with storage efficiency but does not solve the in-memory footprint.

---

## 10. Security Architecture

- **API key handling** uses Effect's `Redacted` type (`src/embeddings/openai-provider.ts:5, 191-193`), which prevents accidental logging of sensitive values. This is good practice.
- **`.env` file** at the project root (`/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/.env`) exists and is 164 bytes. It should be in `.gitignore` (checking the gitignore shows `.env` is listed, confirming proper handling).
- **No input sanitization** on MCP tool arguments. The `args` parameter is typed as `Record<string, unknown>` and cast with `as string` without validation (e.g., `server.ts:208`). Malicious input through the MCP channel could cause unexpected behavior (path traversal via `path.join` with unsanitized input at `server.ts:271-272`).

---

## 11. Technical Debt Summary

| Priority | Issue | Location | Impact |
|----------|-------|----------|--------|
| High | `semanticSearch`/`semanticSearchWithStats` duplication | `src/embeddings/semantic-search.ts` | 400 lines of near-identical code; maintenance hazard |
| High | `SummarizationError` outside Effect error system | `src/summarization/types.ts:164-174` | Breaks error handling contract |
| High | `DimensionMismatchError` missing from `createErrorHandler` | `src/cli/error-handler.ts:507-526` | Unhandled error at CLI boundary |
| Medium | `ParseError` dual definition | `src/core/types.ts:93-113` vs `src/errors/index.ts:199-209` | Import confusion |
| Medium | Business logic in types.ts | `src/embeddings/types.ts:196-307` | Violates SRP |
| Medium | MCP server lacks config loading | `src/mcp/server.ts` | Users cannot configure MCP behavior |
| Medium | `EmbeddingProvider` naming collision | `src/config/schema.ts` vs `src/embeddings/types.ts` | Requires rename aliasing at import |
| Medium | Duplicate type definitions in summarization module | `src/summarization/types.ts:12-18, 28-34, 139-152` | Type drift risk |
| Low | `src/summarize/` vs `src/summarization/` naming confusion | Both directories | Onboarding friction |
| Low | Unsanitized MCP input parameters | `src/mcp/server.ts:208-211` | Path traversal risk |
| Low | `src/integration/` contains only a test file | `src/integration/` | Misleading directory |
| Low | `postinstall` hnswlib rebuild for all consumers | `package.json:21` | Installation friction |

---

## 12. Recommendations

### Immediate (next sprint)

1. **Fix `DimensionMismatchError` in `createErrorHandler`** -- add the missing handler. This is a bug.
2. **Extract shared semantic search pipeline** -- reduce `semantic-search.ts` from 1270 lines by factoring the common search pipeline.

### Short-term (1-2 sprints)

3. **Migrate `SummarizationError` to `Data.TaggedError`** and integrate with `MdContextError` union.
4. **Move ranking/boost logic out of `types.ts`** into a dedicated module.
5. **Add MCP config loading** -- load `mdcontext.config.*` at MCP server startup, mirroring the CLI behavior.
6. **Add input validation to MCP handlers** -- validate and sanitize path arguments before `path.join`.

### Medium-term (next quarter)

7. **Rename `src/summarize/` to `src/context-assembly/`** to clarify distinction from AI summarization.
8. **Consolidate `ParseError` definitions** -- one canonical definition.
9. **Resolve `EmbeddingProvider` naming collision** -- rename the config schema type to `EmbeddingProviderName` or similar.
10. **Consider making `hnswlib-node` an optional peer dependency** for library consumers who only need keyword search.

---

## 13. Architecture Strengths Worth Preserving

- The Effect-TS integration is thorough and well-executed. The `ConfigService` layer pattern, tagged errors, and generator-based Effect pipelines demonstrate strong functional programming practices.
- The error taxonomy with structured error codes is production-grade. The separation of error data from error presentation is particularly well done.
- The configuration precedence chain (CLI > env > file > defaults) is correct and well-tested.
- Domain types in `src/core/types.ts` use `readonly` throughout and are well-structured.
- The embedding provider abstraction cleanly supports multiple backends (OpenAI, Ollama, LM Studio, OpenRouter, Voyage) through a single interface.
- Test infrastructure with config test utilities shows investment in testability.
