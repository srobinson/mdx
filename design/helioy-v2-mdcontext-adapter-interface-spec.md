# Helioy V2: Mdcontext Adapter Interface Specification

Date: 2026-03-12
Status: Interface spec
Author: Codex

## Purpose

This document defines the provider abstraction for AI-enhanced `mdcontext` tasks.

The goal is to support both:

- API-backed providers
- subscription-backed runtime adapters

through one coherent interface.

This is the contract that future `mdcontext` LLM integrations should build against.

## Design Goals

The adapter layer should:

- preserve the deterministic core of `mdcontext`
- make AI enhancement optional
- support multiple provider classes cleanly
- keep task definitions stable even if provider implementations change
- make local developer workflows and backend workflows both possible

## Non-Goals

This layer is not trying to:

- abstract every possible provider feature
- hide all differences between runtime and API integrations
- become a generic agent framework

It is only trying to provide a clean contract for `mdcontext` tasks.

## Core Model

The adapter boundary should be task-based, not model-based.

That means `mdcontext` should ask for:

- normalize this markdown
- rewrite this file into canonical form
- summarize these search results

not:

- call model X with raw prompt Y

This is important because `mdcontext` should own task intent and provider adapters should own delivery mechanics.

## Adapter Kinds

There are two primary adapter kinds.

### API Adapter

Backed by a standard model API.

Examples:

- `openai-api`
- `anthropic-api`
- `openrouter-api`
- `ollama-local`

Characteristics:

- request/response semantics
- explicit billing
- best for headless automation

### Runtime Adapter

Backed by a user-facing product runtime.

Examples:

- `codex-runtime`
- `claude-code-runtime`

Characteristics:

- local or semi-local execution
- may leverage existing subscriptions
- best for interactive or semi-attended workflows

## Canonical Task Enum

The first version of the adapter system should support a narrow task set.

```typescript
export type MdcontextLlmTask =
  | "summarize_search_results"
  | "normalize_markdown"
  | "rewrite_markdown"
  | "generate_frontmatter"
  | "extract_document_structure"
```

### Task Definitions

#### `summarize_search_results`

Input:

- retrieved search hits
- optional user query
- summarization instructions

Output:

- compact markdown or plain-text synthesis

#### `normalize_markdown`

Input:

- raw markdown
- canonicalization instructions

Output:

- normalized markdown representation

Note:

- intended for sidecar normalization or ingest-time transforms

#### `rewrite_markdown`

Input:

- raw markdown
- target style or canonical format rules

Output:

- rewritten markdown suitable for replacement or new version creation

#### `generate_frontmatter`

Input:

- raw markdown
- optional schema or allowed fields

Output:

- structured frontmatter object or frontmatter + body

#### `extract_document_structure`

Input:

- raw markdown

Output:

- structured interpretation such as title, section labels, doc type, or normalized metadata

## Canonical Request Type

```typescript
export interface MdcontextLlmRequest {
  task: MdcontextLlmTask
  input: string
  instructions?: string
  metadata?: Record<string, unknown>
  budget?: MdcontextLlmBudget
}
```

### Budget Type

```typescript
export interface MdcontextLlmBudget {
  maxInputTokens?: number
  maxOutputTokens?: number
  maxCostUsd?: number
  requireConfirmation?: boolean
}
```

### Metadata Guidelines

The `metadata` field is task-specific and should carry structured input such as:

- original file path
- document role
- project style profile
- allowed frontmatter keys
- expected output schema
- search query and search results

## Canonical Response Type

```typescript
export interface MdcontextLlmResponse {
  adapterId: string
  kind: "api" | "runtime"
  task: MdcontextLlmTask
  output: string
  usage?: MdcontextLlmUsage
  metadata?: Record<string, unknown>
}
```

### Usage Type

```typescript
export interface MdcontextLlmUsage {
  inputTokens?: number
  outputTokens?: number
  estimatedCostUsd?: number
  executionMode?: "api" | "runtime"
}
```

## Adapter Interface

```typescript
export interface MdcontextLlmAdapter {
  readonly id: string
  readonly kind: "api" | "runtime"

  supports(task: MdcontextLlmTask): boolean

  invoke(request: MdcontextLlmRequest): Promise<MdcontextLlmResponse>
}
```

This should remain deliberately small.

## Capability Descriptor

Adapters should also expose a capability descriptor for planning and fallback.

```typescript
export interface MdcontextLlmAdapterCapabilities {
  id: string
  kind: "api" | "runtime"
  supportedTasks: MdcontextLlmTask[]
  interactive: boolean
  headlessSafe: boolean
  supportsStreaming: boolean
  requiresSubscriptionRuntime: boolean
  estimatedStability: "high" | "medium" | "low"
}
```

### Why This Matters

`mdcontext` should be able to make sane decisions such as:

- use API provider in CI
- use Codex runtime locally
- avoid runtime adapters for unattended batch work

without hard-coding provider-specific assumptions into task logic.

## Proposed Adapter IDs

The first adapter namespace should be explicit.

### API Adapters

- `openai-api`
- `anthropic-api`
- `openrouter-api`
- `ollama-local`

### Runtime Adapters

- `codex-runtime`
- `claude-code-runtime`

## Runtime Adapter Expectations

Runtime adapters should be treated as first-class but more constrained.

They should:

- support a subset of tasks
- expose lower stability expectations
- be local-first by default

They should not be assumed safe for:

- unattended long-running jobs
- backend multitenant services
- critical CI paths

This distinction should be reflected in capability descriptors.

## Suggested Task Support Matrix

### `openai-api`

Supports:

- `summarize_search_results`
- `normalize_markdown`
- `rewrite_markdown`
- `generate_frontmatter`
- `extract_document_structure`

Best for:

- backend automation
- batch jobs
- CI

### `anthropic-api`

Supports:

- `summarize_search_results`
- `normalize_markdown`
- `rewrite_markdown`
- `generate_frontmatter`
- `extract_document_structure`

Best for:

- backend automation
- batch jobs
- CI

### `openrouter-api`

Supports:

- same as API adapters above, depending on routed provider

Best for:

- multi-provider flexibility

### `ollama-local`

Supports:

- `summarize_search_results`
- possibly `normalize_markdown`
- possibly `extract_document_structure`

Best for:

- local private usage
- offline-ish workflows

### `codex-runtime`

Supports:

- `summarize_search_results`
- `normalize_markdown`
- `rewrite_markdown`
- `generate_frontmatter`

Best for:

- local developer workflows
- subscription-backed usage where eligible

### `claude-code-runtime`

Supports:

- `summarize_search_results`
- `normalize_markdown`
- `rewrite_markdown`
- `generate_frontmatter`

Best for:

- local developer workflows
- subscription-backed usage where eligible

## Task-Specific Input Shapes

The generic request type is useful, but each task should have a typed helper.

### Search Summarization

```typescript
export interface SummarizeSearchResultsRequest extends MdcontextLlmRequest {
  task: "summarize_search_results"
  metadata: {
    query?: string
    results: Array<{
      path: string
      heading?: string
      content: string
      score?: number
    }>
  }
}
```

### Normalize Markdown

```typescript
export interface NormalizeMarkdownRequest extends MdcontextLlmRequest {
  task: "normalize_markdown"
  metadata: {
    path?: string
    styleProfile?: string
    preserveFrontmatter?: boolean
  }
}
```

### Rewrite Markdown

```typescript
export interface RewriteMarkdownRequest extends MdcontextLlmRequest {
  task: "rewrite_markdown"
  metadata: {
    path?: string
    rewriteMode: "canonical" | "house_style" | "upgrade_structure"
    preserveSemantics?: boolean
  }
}
```

### Generate Frontmatter

```typescript
export interface GenerateFrontmatterRequest extends MdcontextLlmRequest {
  task: "generate_frontmatter"
  metadata: {
    allowedKeys?: string[]
    requiredKeys?: string[]
    path?: string
  }
}
```

## Error Model

The adapter layer should not throw raw provider-specific errors directly into `mdcontext` business logic.

Use a normalized error type:

```typescript
export type MdcontextLlmAdapterError =
  | { type: "unsupported_task"; adapterId: string; task: MdcontextLlmTask }
  | { type: "auth_error"; adapterId: string; message: string }
  | { type: "budget_exceeded"; adapterId: string; message: string }
  | { type: "runtime_unavailable"; adapterId: string; message: string }
  | { type: "provider_error"; adapterId: string; message: string }
```

This keeps task orchestration clean and testable.

## Selection Strategy

`mdcontext` should not force users to think in adapter IDs when it can infer sensible defaults.

A simple selection strategy:

1. explicit adapter if requested
2. explicit provider family if requested
3. local runtime adapter if user asks for subscription-backed mode
4. configured API provider if running in headless mode
5. fail clearly if no capable adapter exists

## Recommended First Implementation

The first implemented shared task should be:

- `summarize_search_results`

Why:

- it already exists conceptually in the codebase
- it is easier than rewrite flows
- it exercises adapter selection, cost handling, and output formatting
- it can be supported by both API and runtime adapters

After that:

- `normalize_markdown`

Then:

- `rewrite_markdown`

## Recommended File Layout

Suggested placement if added to `mdcontext`:

```text
src/llm/
  types.ts
  adapter.ts
  registry.ts
  selection.ts
  tasks/
    summarize-search-results.ts
    normalize-markdown.ts
    rewrite-markdown.ts
  adapters/
    openai-api.ts
    anthropic-api.ts
    openrouter-api.ts
    ollama-local.ts
    codex-runtime.ts
    claude-code-runtime.ts
```

This keeps:

- provider mechanics
- task orchestration
- selection logic

separate from the rest of the parser/index/search core.

## Final Guidance

The key architectural discipline is:

- `mdcontext` owns the tasks
- adapters own how those tasks are executed

Do not let provider prompts leak everywhere.
Do not let task semantics fragment by provider.

If this interface stays clean, `mdcontext` can remain a deterministic markdown system first and an AI-enhanced normalization tool second.
