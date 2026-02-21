# mdcontext TypeScript Code Quality Review

**Date:** 2026-03-13
**Scope:** `/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/src/` — 123 files, 38,233 LOC
**Compiler:** TypeScript 5.9.3, strict mode enabled
**Build:** tsup (ESM), vitest tests, biome linter

---

## Executive Summary

The codebase is in good shape for a tool of its complexity. Strict mode is on, the compiler reports zero errors, and the Effect library provides a disciplined async error channel throughout. The three areas that warrant active attention are: (1) a systemic pattern of unsafe type coercions in the MCP server layer, (2) a duplicate-type shadowing problem across several modules, and (3) a handful of `any`-typed AST helpers in the parser that can be replaced with proper mdast node types. Everything else is a collection of minor issues worth noting but not urgent.

---

## 1. TypeScript Configuration

**File:** `/Users/alphab/Dev/LLM/DEV/helioy/mdcontext/tsconfig.json`

The configuration is strong:

- `strict: true` — enables `noImplicitAny`, `strictNullChecks`, `strictFunctionTypes`, etc.
- `exactOptionalPropertyTypes: true` — prevents assigning `undefined` to optional fields declared without explicit `| undefined`
- `noUncheckedIndexedAccess: true` — forces null checks on index access results
- `noImplicitReturns: true`, `noFallthroughCasesInSwitch: true`
- `declaration: true`, `declarationMap: true`, `sourceMap: true`

**Gap 1 — `skipLibCheck: true`:** This suppresses type errors in `node_modules`. The project vendors `@types/mdast` and interacts deeply with `hnswlib-node`, both of which have declaration quality issues. Accepting `skipLibCheck` is pragmatic given these dependencies, but it means that type errors in third-party declarations go unreported. If `hnswlib-node` types worsen, the codebase will not notice.

**Gap 2 — No `paths` aliases:** All cross-module imports use relative `.js` paths (e.g., `../../errors/index.js`). This is correct for NodeNext resolution but makes deep imports verbose. Not a correctness problem, just ergonomics.

**Gap 3 — Build vs. typecheck divergence:** The `build` script uses `tsup`, not `tsc`. `tsup` transpiles without full type-checking. The `typecheck` script runs `tsc --noEmit` separately. This is the standard pattern, but it means CI must run both steps to catch type errors. The `prepublishOnly` script correctly includes both.

---

## 2. Type Safety — `any` Usage and Unsafe Assertions

### 2.1 Parser AST Helpers (Justified `any`, Improvable)

**File:** `src/parser/parser.ts`, lines 67–74

```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const getNodeEndLine = (node: any): number => {
  return node?.position?.end?.line ?? 0
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const getNodeStartLine = (node: any): number => {
  return node?.position?.start?.line ?? 0
}
```

These functions accept `any` because they handle heterogeneous mdast node types (heading, link, image, code) without a shared position interface. The `@types/mdast` package exports `Node` which includes `position?: Position`. Both helpers could be typed as `(node: Node): number`, eliminating the `any`. The `eslint-disable` comments confirm the authors are aware; this is a low-effort fix.

**File:** `src/parser/parser.ts`, lines 145–154

```typescript
const plainText = extractSectionPlainText(raw.contentNodes as Parent[])
const hasCode = (raw.contentNodes as { type: string }[]).some(...)
const hasList = (raw.contentNodes as { type: string }[]).some(...)
const hasTable = (raw.contentNodes as { type: string }[]).some(...)
```

The `RawSection.contentNodes` field is typed as `unknown[]` (line 86). Every consumption site then casts it. This is a self-inflicted cast chain. The field should be `RootContent[]` (the mdast union type for top-level nodes), which carries `.type` natively and is a `Parent` subtype for structured nodes. That would remove all four casts.

### 2.2 MCP Server Layer — Systematic Unsafe Coercions

**File:** `src/mcp/server.ts`

Every handler in the MCP server takes `args: Record<string, unknown>` (correct for protocol compliance) then casts each field:

```typescript
// Lines 208–211
const query = args.query as string
const limit = (args.limit as number) ?? 5
const pathFilter = args.path_filter as string | undefined
const threshold = (args.threshold as number) ?? 0.35
```

And later does inline structural casts on Effect results:

```typescript
// Lines 239–244
const formattedResults = (
  result as Array<{
    sectionId: string
    documentPath: string
    heading: string
    similarity: number
  }>
).map(...)
```

The root issue is how errors are handled. The pattern `Effect.catchAll((e) => Effect.succeed([{ error: e.message }] as const))` converts the typed error channel into an untyped success value, which then requires a runtime `'error' in result[0]` check and a subsequent cast to recover structure. This is a common anti-pattern at protocol boundaries.

A better approach uses a discriminated union result type:

```typescript
type ToolSuccess<T> = { ok: true; value: T }
type ToolFailure = { ok: false; error: string }
type ToolResult<T> = ToolSuccess<T> | ToolFailure
```

This keeps the type information intact through the Effect boundary, eliminates all the casts, and makes the handler code easier to follow. The MCP boundary concern is valid, but the current solution trades one problem (untyped protocol args) for another (untyped success values).

The `args` coercions can be addressed with a small Zod schema or a validated accessor helper. Given the codebase already uses Effect, `Schema.decodeUnknown` from `effect/Schema` could validate the input without adding a dependency.

### 2.3 Vector Store — Non-null Assertion

**File:** `src/embeddings/vector-store.ts`, lines 137–143

```typescript
private index: HierarchicalNSW.HierarchicalNSW | null = null
```

`ensureIndex()` (line 211) initializes and returns this index. Callers inside the class use `this.index!` or call `ensureIndex()`. This pattern is sound and consistent. No issue here, just noting the explicit null initialization is intentional.

**File:** `src/embeddings/semantic-search.ts`, line 347

```typescript
const vectorStore = createNamespacedVectorStore(...) as HnswVectorStore
```

`createNamespacedVectorStore` returns `VectorStore` (the interface). The cast to `HnswVectorStore` (the class) is needed to call `setProvider`, `addCost`, and `getStats`, which are not on the `VectorStore` interface. The fix is to add these methods to `VectorStore` or introduce a `ManagedVectorStore` interface that extends `VectorStore` with those lifecycle methods. The current cast is not dangerous (the factory always returns `HnswVectorStore`) but it is invisible to the type system.

**File:** `src/embeddings/semantic-search.ts`, lines 331–332

```typescript
const nameParts = provider.name.split(':')
providerName = nameParts[0] || 'openai'
```

`nameParts[0]` is `string | undefined` under `noUncheckedIndexedAccess`. The `|| 'openai'` fallback correctly handles `undefined`, but this is a silent assumption about the `name` format. A comment or structured type for `ProviderName` would make this explicit.

---

## 3. Interface Design

### 3.1 Export Shadowing — Mass Duplication Across Module Indexes

fmm reports over 100 shadowing warnings. Representative examples:

- `ContextLine` is exported from `src/embeddings/types.ts`, `src/search/searcher.ts`, and `src/search/hybrid-search.ts` as three separate interface definitions with identical structure.
- `ParseError` is defined as both an interface in `src/core/types.ts` (line 93) and a `Data.TaggedError` class in `src/errors/index.ts` (line 199). The former is a plain object; the latter is an Effect error. Re-exporting both from `src/config/index.ts` creates confusion about which to import.
- `EmbeddingProvider` is exported from both `src/embeddings/types.ts` and `src/config/schema.ts` as different types (an interface vs. a string literal union).
- `IndexConfig` is exported from `src/index/types.ts` and `src/config/schema.ts` as different shapes.
- `PartialMdContextConfig` is exported from both `src/config/service.ts` and `src/index.ts`.

These are not TypeScript errors because each export points to a different declaration in its own file. However, they create import ambiguity for consumers and make the public API surface opaque. The barrel files (`config/index.ts`, `summarization/index.ts`) re-export everything, amplifying the problem.

**Specific concern:** `ContextLine` at `src/search/searcher.ts:82` and `src/embeddings/types.ts:319` are structurally identical but nominally separate. Code that uses both modules must pick one, and the choice is arbitrary. This should be a single canonical definition in `src/core/types.ts` or `src/types/`.

**Specific concern:** The dual `ParseError` declaration. `src/core/types.ts` declares both an interface `ParseError` and a function `ParseError` with the same name (lines 93 and 104). This is a TypeScript-valid pattern (interface/value merging), but it predates the `Data.TaggedError` version in `src/errors/index.ts`. The comment on line 87 acknowledges the distinction. Consumers need to be careful which one they import; the `src/errors/index.ts` version should be canonical and the `src/core/types.ts` version deprecated.

### 3.2 `src/index/types.ts` — Weak Level Type

**File:** `src/index/types.ts`, line 54

```typescript
export interface SectionEntry {
  readonly level: number  // Should be HeadingLevel
  ...
}
```

`src/core/types.ts` defines `HeadingLevel = 1 | 2 | 3 | 4 | 5 | 6`. The `MdSection` interface uses it correctly. But `SectionEntry` (the persisted/indexed form of a section) uses `number`, losing the constraint. Code that reads from the section index cannot safely use `section.level` as `HeadingLevel` without an assertion. The parser assigns the level correctly, so the serialization roundtrip drops the type information unnecessarily.

### 3.3 `src/index/types.ts` — Mutable `SkipSummary`

**File:** `src/index/types.ts`, lines 100–105

```typescript
export interface SkipSummary {
  readonly unchanged: number
  readonly excluded: number
  readonly hidden: number
  readonly total: number
}
```

This is fine. However, `SkipSummary` does not include `not-markdown`, `binary`, or `oversized` counts even though `SkipReason` (line 81) enumerates them. The summary only tracks `unchanged`, `excluded`, and `hidden`. Callers cannot distinguish between a file being skipped as binary vs. oversized. This may be intentional compression but it loses information.

### 3.4 `VectorStore` Interface Incompleteness

**File:** `src/embeddings/vector-store.ts`, lines 45–77

The `VectorStore` interface declares `add`, `search`, `searchWithStats`, `save`, and `load`. The `HnswVectorStore` class implements this plus `setProvider`, `addCost`, `getStats`, `setNamespace`, `getNamespace`. All callers that need lifecycle management (`buildEmbeddings` in `semantic-search.ts`) cast to `HnswVectorStore` directly. This makes `VectorStore` a misleading abstraction — it is not substitutable without the lifecycle methods.

Either the interface should be extended to include the lifecycle methods, or the factory functions should return `HnswVectorStore` directly and the interface removed or renamed to `ReadonlyVectorStore`.

---

## 4. Async Patterns and Error Handling

### 4.1 Effect Usage — Generally Excellent

The codebase uses Effect consistently for typed async error channels. `Effect.gen` with typed error union return types is the dominant pattern. Error types are discriminated via `_tag` through `Data.TaggedError`. Error hierarchy is documented with codes (`E100`–`E9xx`). This is well-structured.

### 4.2 `Effect.promise` Without Error Channel in Content Search

**File:** `src/search/searcher.ts`, lines 307–313

```typescript
fileContent = yield* Effect.promise(() =>
  fs.readFile(filePath, 'utf-8'),
)
```

`Effect.promise` wraps an unsafe promise — any rejection becomes an `unknown` defect (not a typed error). The surrounding `try { ... } catch { continue }` pattern is JavaScript-style exception handling inside an Effect generator. This works but is inconsistent with the rest of the codebase, which uses `Effect.tryPromise` with a typed `catch` handler. The file read failure here is silently swallowed (the `catch` does `continue`), meaning a missing or unreadable file produces empty results with no diagnostic.

The correct pattern is `Effect.tryPromise({ try: ..., catch: (e) => new FileReadError(...) })` and then either propagate the error or log and continue explicitly.

### 4.3 `detectExactDuplicates` — File Read Swallows Errors

**File:** `src/duplicates/detector.ts`, lines 153–163

```typescript
const content = yield* Effect.promise(async () => {
  try {
    const filePath = path.join(rootPath, documentPath)
    return await fs.readFile(filePath, 'utf-8')
  } catch {
    return null
  }
})
```

Same pattern as above. The `try/catch` inside `Effect.promise` converts a filesystem error into `null` without logging. Callers check `if (!fileContent) return` and proceed silently. For a deduplication tool, this means a missing file causes its sections to be omitted from duplicate detection without any indication. A logged warning at minimum would help.

### 4.4 `buildEmbeddings` — Correct Error Handling Pattern

**File:** `src/embeddings/semantic-search.ts`, lines 468–480

```typescript
const fileContentResult = yield* Effect.promise(() =>
  fs.readFile(filePath, 'utf-8'),
).pipe(
  Effect.map((content) => ({ ok: true as const, content })),
  Effect.catchAll(() =>
    Effect.succeed({ ok: false as const, content: '' }),
  ),
)

if (!fileContentResult.ok) {
  yield* Effect.logWarning(`Skipping file (cannot read): ${docPath}`)
  continue
}
```

This is the correct approach: the discriminated union result type, the `Effect.logWarning` for visibility, and the explicit `continue`. The detector and searcher should mirror this pattern.

### 4.5 `parseFile` — Dynamic Import Inside Effect

**File:** `src/parser/parser.ts`, lines 374–375

```typescript
const fs = yield* Effect.promise(() => import('node:fs/promises'))
```

This pattern dynamically imports `node:fs/promises` on every call to `parseFile`. The module system caches the import after the first resolution, so the performance impact is negligible in practice, but it is unconventional. The top-level `import * as fs from 'node:fs/promises'` pattern (used in `detector.ts`, `indexer.ts`, `semantic-search.ts`) is simpler. There is no reason for the dynamic import here.

### 4.6 `OpenAIProvider.embed` — Mixed Async Paradigm

**File:** `src/embeddings/openai-provider.ts`, lines 225–307

`embed` is a plain `async` method (not an Effect). It uses `try/catch` to convert OpenAI SDK errors to typed domain errors. This is intentional: `EmbeddingProvider.embed` in `src/embeddings/types.ts` is defined as returning `Promise<EmbeddingResult>`, keeping the interface free of Effect. Callers use `wrapEmbedding()` to lift the promise into an Effect with typed errors.

This is a reasonable boundary design. The concern is that `wrapEmbedding` catches `ApiKeyInvalidError` specifically (line 411) but re-wraps everything else as generic `EmbeddingError`. If `embed` throws an `ApiKeyMissingError` (which it currently does not, since `create()` handles key resolution before construction), `wrapEmbedding` would re-wrap it as `EmbeddingError`, losing the specific type. The current code is correct but fragile at this boundary.

---

## 5. `src/embeddings/` — New Files Review

### 5.1 `batching.ts` — High Quality

**File:** `src/embeddings/batching.ts`

Clean, well-typed, all fields `readonly`. The guard logic correctly handles edge cases: single oversized text isolated in its own batch, zero-length input, tokens calculated with `Math.max(1, ...)`. The `BatchTextsOptions` fields should perhaps carry `Positive` branded types to enforce the `>= 1` invariants at the type level rather than runtime guards, but this is a minor point.

### 5.2 `batching.test.ts` — Adequate but Incomplete

**File:** `src/embeddings/batching.test.ts`

Three test cases cover the main paths: count-based splitting, token-budget splitting, and oversized text isolation. Missing cases:

- Empty input array (should return `[]`)
- `maxTextsPerBatch === 1` (every text becomes its own batch)
- Exactly-at-budget boundary (token sum equals `maxTokensPerBatch`)
- Invalid options: `maxTextsPerBatch < 1`, `maxTokensPerBatch < 1` (should throw)

The last two are runtime guards that throw `Error`. They are not tested. With 3 tests on a 75-LOC file, coverage is functional but not exhaustive.

### 5.3 `openai-provider.ts` — Good Design, One Concern

**File:** `src/embeddings/openai-provider.ts`

The `Redacted<string>` usage for API keys is the right call. The `create` static factory returning an Effect is idiomatic. The `classifyError` method provides a well-structured fallback chain.

**Issue — hardcoded provider name check for pricing (line 297):**

```typescript
const pricePerMillion =
  this.providerName === 'openai' || this.providerName === 'openrouter'
    ? (PRICING_DATA.prices[this.model] ?? 0.02)
    : 0
```

This string comparison will silently pass free pricing for any provider whose name is neither `'openai'` nor `'openrouter'`. If a user creates an OpenRouter-compatible provider with a custom `providerName`, they get zero cost tracking. The `PROVIDER_BASE_URLS` constant (in `provider-constants.ts`) is the authoritative list of paid providers; the pricing check should derive from that rather than hardcoding provider names.

The default fallback `?? 0.02` is also opaque. It silently assigns the `text-embedding-3-small` price to any unrecognized model. An explicit `0` with a logged warning would be more transparent.

**Issue — `checkPricingFreshness` and `getPricingDate` re-exported from both `openai-provider.ts` and `semantic-search.ts`:** This is the source of two fmm shadowing warnings. `semantic-search.ts` line 118 re-exports these with `export { checkPricingFreshness, getPricingDate }`. Consumers importing from `semantic-search.ts` get the same functions as from `openai-provider.ts`. The re-export creates confusion about where the canonical definition lives.

### 5.4 `openai-provider.test.ts` — Functional but Brittle

**File:** `src/embeddings/openai-provider.test.ts`

The test patches the private `client` field:

```typescript
;(
  provider as unknown as {
    client: { embeddings: { create: typeof createMock } }
  }
).client.embeddings.create = createMock
```

This is a double cast through `unknown` to access a private field. It will break silently if the field is renamed or the OpenAI client structure changes. The test also relies on the internal structure of `OpenAIProvider` rather than its public interface. This is acceptable for integration-style testing but is fragile.

A better approach: extract the HTTP client as a constructor parameter with a default, making `OpenAIProvider` testable without casting. This is a common pattern with DI-friendly design.

---

## 6. `src/search/` — Search Implementation

### 6.1 Regex Injection Risk in User-Controlled Input

**File:** `src/search/searcher.ts`, lines 131–133

```typescript
const headingRegex = options.heading
  ? new RegExp(options.heading, 'i')
  : null
```

`options.heading` is passed directly to `RegExp`. An invalid regex string (e.g., `"("`) will throw a `SyntaxError` that is not caught. The Effect wrapper around `search` does not declare `SyntaxError` as a possible failure, so the defect propagates up uncaught. The MCP server wraps with `catchAll`, so it surfaces as an error response, but the CLI path may not handle this gracefully.

Same issue exists in `searchContent` (line 269). The fix is `Effect.try({ try: () => new RegExp(...), catch: (e) => new CliValidationError(...) })` or a validation step in the option parsing layer.

### 6.2 `search` Return Type Excludes `IndexNotFoundError`

**File:** `src/search/searcher.ts`, lines 116–119

```typescript
export const search = (
  rootPath: string,
  options: SearchOptions = {},
): Effect.Effect<
  readonly SearchResult[],
  FileReadError | IndexCorruptedError
>
```

When the index is not found, the function returns `[]` (line 126–128) rather than failing. This means callers cannot distinguish "no results" from "no index". `buildIndex` failing should surface as `IndexNotFoundError`, not empty results. The current behavior is a design choice but it means the MCP `md_keyword_search` handler will return "No sections found" when the index has never been built, giving a misleading response.

### 6.3 Content Pattern Used as Both Regex and Fuzzy Trigger

**File:** `src/search/searcher.ts`, lines 241–266

The logic that decides whether `options.content` is treated as a boolean query, a regex, or a fuzzy pattern is complex and sequential. The branches are mutually exclusive but the conditions are non-obvious (`isAdvancedQuery` check, then `useFuzzyOrStem` check, then fallback to regex). This would benefit from a discriminated union for the search mode:

```typescript
type ContentSearchMode =
  | { kind: 'boolean'; query: ParsedQuery }
  | { kind: 'regex'; pattern: RegExp }
  | { kind: 'fuzzy'; terms: string[] }
  | { kind: 'none' }
```

This is a refactoring suggestion, not a bug. The current code is correct.

---

## 7. `src/index/` — Indexer

### 7.1 `walkDirectory` — Mutable Async and Error Handling

**File:** `src/index/indexer.ts`, lines 69–112

`walkDirectory` is a plain `async` function, not an Effect. It handles `readdir` errors by letting them propagate as untyped rejections, caught at the call site (line 246–255) with `Effect.tryPromise`. This is the correct boundary. The function itself does not swallow errors, which is good.

**Minor:** The hidden-file check on line 84 (`entry.name.startsWith('.')`) skips the `.mdcontext` directory (the index itself). This is intentional and correct, but a comment would clarify intent.

### 7.2 `buildIndex` — Mutable State Pattern Inside Effect

**File:** `src/index/indexer.ts`, lines 265–279

The function creates mutable `Record` objects and mutates them inside `Effect.gen`. This is fine since the mutations are sequential and local to the function scope, but it contradicts the immutable style of the rest of the codebase. Given the index building involves many files and sections, this is a pragmatic trade-off for performance (avoiding repeated spreads). The pattern should be documented.

### 7.3 `resolveInternalLink` — Path Traversal Guard

**File:** `src/index/indexer.ts`, lines 174–179

```typescript
if (!resolved.startsWith(rootPath)) {
  return null
}
```

This guards against symlinks or `../` traversal escaping the root. The guard is necessary and present. However, `path.resolve` normalizes the path but `rootPath` may not be normalized (no `path.resolve(rootPath)` call before the comparison). If `rootPath` has a trailing slash in some call contexts and not others, the `startsWith` check could produce false positives. `path.resolve(rootPath)` at function entry would make this robust.

---

## 8. `src/parser/parser.ts` — Parser Robustness

### 8.1 Section ID Collision

**File:** `src/parser/parser.ts`, lines 157–158

```typescript
const section: MdSection = {
  id: `${docId}-${slugify(raw.heading)}`,
```

`slugify` strips non-word characters. Two headings that differ only in punctuation (e.g., `"Setup: Part 1"` and `"Setup. Part 1"`) will produce the same ID. This causes the second section to shadow the first in the `SectionIndex.sections` record. This is a latent bug in documents with similarly-named headings.

A disambiguation suffix (e.g., appending the line number, or a counter for duplicate slugs) would prevent collisions.

### 8.2 `console.warn` Escape in Effect Pipeline

**File:** `src/parser/parser.ts`, lines 310–313

```typescript
console.warn(
  `Warning: Malformed frontmatter in ${path}, skipping: ${msg.split('\n')[0]}`,
)
```

This is a direct `console.warn` inside a function that is otherwise wrapped in `Effect.gen`. It bypasses Effect's logging layer (`Effect.logWarning`), which means it does not participate in structured logging, cannot be suppressed in tests, and cannot be captured by any Effect runtime configuration. All logging inside Effect generators should use `Effect.logWarning` or similar.

### 8.3 `fs` Module Dynamic Import

Covered in section 4.5 above. The `import('node:fs/promises')` call on every invocation is unnecessary.

---

## 9. `src/duplicates/detector.ts` — Deduplication Logic

### 9.1 Race Condition in Parallel Hash Collection

**File:** `src/duplicates/detector.ts`, lines 237–276

```typescript
yield* Effect.all(
  Array.from(sectionsByFile.entries()).map(([documentPath, sections]) =>
    Effect.gen(function* () {
      ...
      const existing = hashGroups.get(hash)
      if (existing) {
        existing.push(info)
      } else {
        hashGroups.set(hash, [info])
      }
    }),
  ),
  { concurrency: 10 },
)
```

`hashGroups` is a `Map` shared across parallel Effect fibers running with `concurrency: 10`. Effect's concurrency is cooperative (not OS-threaded), meaning fibers yield at `yield*` boundaries. The critical section (lines 266–272) has no `yield*` inside it, so it executes atomically from Effect's scheduler perspective. This is safe in Effect's single-threaded JavaScript execution model.

However, it is a subtle correctness argument that depends on knowing Effect's scheduler does not interleave between synchronous statements. A comment explaining why this is safe would prevent future bugs if the logic is refactored to include async operations.

### 9.2 `matchPathPattern` — Duplicated Glob Implementation

**File:** `src/duplicates/detector.ts`, lines 315–325

The file contains its own `matchPathPattern` function (local). `src/search/path-matcher.ts` exports `matchPath` which does the same thing. Both implement the same glob-to-regex conversion. They are not identical (different handling of edge cases), creating divergence. The deduplication module should import from `path-matcher.ts`.

---

## 10. `src/core/types.ts` — Interface vs. Value Merging

**File:** `src/core/types.ts`, lines 93–113

```typescript
export interface ParseError { ... }
export const ParseError = (...): ParseError => ({ ... })
```

TypeScript allows a `const` and an `interface` to share the same name (namespace merging). This works but it is non-obvious. The `ParseError` at this location is an older plain-object error. The `ParseError` in `src/errors/index.ts` is the Effect `TaggedError`. The fmm shadowing warning for `ParseError` arises because `config/index.ts` re-exports both versions. The comment at line 87 acknowledges this but consumers must still know which to import. This dual-definition pattern should be resolved by deprecating `src/core/types.ts:ParseError` in favor of the Effect version.

---

## 11. `src/config/` — Configuration Design

### 11.1 `PartialMdContextConfig` Exported from Two Locations

`src/config/service.ts` and `src/index.ts` both export `PartialMdContextConfig`. They reference the same underlying type from `service.ts`, so this is not a structural divergence, but the re-export from the root `index.ts` is undocumented. Consumers should import from `src/config/service.ts` directly.

### 11.2 `mergeWithDefaults` — Shallow Merge

**File:** `src/config/service.ts`, lines 210–223

The merge is shallow (one level). `MdContextConfig` sections are flat objects, so this is correct today. If any section gains a nested object in the future, the merge will silently overwrite the nested object rather than deep-merging it. A `deepMerge` utility would be safer. A comment explaining the intentional shallow merge would help.

---

## 12. Pattern Consistency

### 12.1 `IndexNotFoundError` vs. Empty Result

Some functions return `Effect.fail(new IndexNotFoundError(...))` when the index is missing (e.g., `buildEmbeddings`, `estimateEmbeddingCost`). Others return `[]` (e.g., `search`, `detectExactDuplicates`). The inconsistency means callers must know which behavior to expect per function. A consistent contract would be: functions that require an index fail with `IndexNotFoundError`; functions that are advisory (search, duplicate detection) return empty results. Currently this convention is partially followed but not enforced by types.

### 12.2 `getIndexPaths` Using String Concatenation

**File:** `src/index/types.ts`, lines 139–147

```typescript
export const getIndexPaths = (rootPath: string) => ({
  root: `${rootPath}/${INDEX_DIR}`,
  config: `${rootPath}/${INDEX_DIR}/config.json`,
  ...
})
```

String concatenation instead of `path.join`. On Windows (not a stated target, but worth noting), this produces incorrect paths. `path.join(rootPath, INDEX_DIR)` is the portable form. This is a minor issue given the tool targets Node.js on Unix-like systems.

---

## 13. Summary of Findings by Priority

### High Priority

| ID | File | Issue |
|----|------|-------|
| H1 | `src/mcp/server.ts` | Unsafe type coercions on all MCP handler arguments and results — replace with validated accessors or discriminated union result type |
| H2 | `src/search/searcher.ts:131,269` | Unguarded `new RegExp(userInput)` — can throw untyped `SyntaxError` defect |
| H3 | `src/parser/parser.ts:157` | Section ID collision for headings that differ only in punctuation |

### Medium Priority

| ID | File | Issue |
|----|------|-------|
| M1 | `src/embeddings/vector-store.ts:347` | `createNamespacedVectorStore` cast to `HnswVectorStore` — extend the interface instead |
| M2 | `src/index/types.ts:54` | `SectionEntry.level: number` should be `HeadingLevel` |
| M3 | `src/parser/parser.ts:67-74` | `any`-typed AST helpers — replaceable with `Node` from `@types/mdast` |
| M4 | `src/parser/parser.ts:86` | `RawSection.contentNodes: unknown[]` — type as `RootContent[]` to eliminate downstream casts |
| M5 | `src/search/searcher.ts:307` | `Effect.promise` without error handling for file reads — use `Effect.tryPromise` |
| M6 | `src/duplicates/detector.ts:153` | File read errors silently become `null` — add `Effect.logWarning` |
| M7 | `src/duplicates/detector.ts:315` | Duplicate glob implementation — import from `path-matcher.ts` |
| M8 | Multiple | `ContextLine` interface defined in 3 locations — canonicalize in `src/core/types.ts` |

### Low Priority / Improvements

| ID | File | Issue |
|----|------|-------|
| L1 | `src/parser/parser.ts:310` | `console.warn` bypasses Effect logging layer |
| L2 | `src/parser/parser.ts:374` | Dynamic `import('node:fs/promises')` on every call — use static import |
| L3 | `src/embeddings/openai-provider.ts:297` | Pricing check by string comparison — derive from `PROVIDER_BASE_URLS` |
| L4 | `src/embeddings/openai-provider.ts` | `checkPricingFreshness`/`getPricingDate` re-exported from `semantic-search.ts` — remove re-export |
| L5 | `src/index/types.ts:139` | `getIndexPaths` uses string concatenation — use `path.join` |
| L6 | `src/index/indexer.ts:175` | `startsWith(rootPath)` without normalizing `rootPath` first |
| L7 | `src/core/types.ts:93` | Dual `ParseError` (plain object vs. TaggedError) — deprecate `core/types.ts` version |
| L8 | `src/embeddings/batching.test.ts` | Missing tests for empty input, boundary conditions, and invalid options |
| L9 | `src/embeddings/openai-provider.test.ts` | Private field access via `unknown` cast — use constructor injection for testability |
| L10 | Multiple | Mass re-export shadowing in barrel files — deduplicate or namespace exports |

---

## 14. What Is Working Well

- The Effect error type system is used consistently and correctly. Error channels are typed, discriminated, and well-documented.
- The `tsconfig.json` is one of the strictest configurations commonly seen in production TypeScript — `exactOptionalPropertyTypes` and `noUncheckedIndexedAccess` are both on.
- The `batching.ts` module is clean, well-typed, and properly handles edge cases.
- The `openai-provider.ts` `Redacted<string>` API key handling is the correct approach.
- The `VectorStore.add` using `Effect.try` with a typed `VectorStoreError` catch is the correct pattern for wrapping synchronous throwing code.
- The error code system (`E100`–`E9xx`) provides stable programmatic identifiers, which is good library design.
- `noUnusedLocals` and `noUnusedParameters` being enforced keeps dead code minimal.
- The `tsc --noEmit` typecheck produces zero errors, confirming the type-level correctness of what exists.
