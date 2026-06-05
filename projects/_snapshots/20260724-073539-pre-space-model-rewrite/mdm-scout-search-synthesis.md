---
title: CLI and MCP Search and Synthesis Convergence
type: research
tags: [markdown-matters, cli, mcp, search, synthesis, code-hygiene]
summary: The CLI and MCP share low level retrieval primitives, but need one surface neutral request, executor, result, and synthesis pipeline.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-23
updated: 2026-07-23
---

# Executive Summary

The CLI and MCP share semantic, keyword, hybrid, and path matching primitives at lower layers. They do not share an end to end search owner: the CLI dispatches three modes and synthesis, while MCP `md_search` calls semantic search directly with a smaller contract.

Synthesis is CLI only and receives paths, headings, and scores because every production adapter drops content already available from retrieval. The reported unrelated tail does not show a separate synthesis scope bypass: the road test requested `/Users/alphab/.mdx/projects`, both tail files were inside that directory, and synthesis consumed the already filtered result list.

# Project Metadata

| Item | Current state |
|---|---|
| Repository | `srobinson/markdown-matters` |
| Branch and head | `main` at `ee712ed4d37761294fcb2392483ca08c77313088` |
| Package | `markdown-matters` 0.4.0 |
| Language | TypeScript, ESM, strict mode |
| Runtime | Node 18 or newer; CI uses Node 22; local scout used Node 24.18.0 |
| Package and build | pnpm 10, tsup, TypeScript 5.9 |
| Tests and style | Vitest 4, Biome 2 |
| Main frameworks | Effect 3, `@effect/cli`, Model Context Protocol SDK |
| Search dependencies | `wink-bm25-text-search`, `hnswlib-node`, Hugging Face transformers as optional reranker |
| Indexed topology | 252 files, 60,959 LOC by fmm |
| Helioy signal | `.fmm.db` is present and active |

The worktree was already dirty before the scout: modified `LESSONS.md` and untracked `.serena/`. The baseline status hash was `3e9dbafce9f4bb34d08d7042375569fe4d385f51bca92ecc5c29551236d49a18`; no repository write was made by this scout.

# Architecture and Reuse Map

## CLI search definition and wiring

Primary entries:

- `src/cli/commands/search.ts:searchOptions` owns the Effect CLI declaration.
- `src/cli/commands/search.ts:searchCommand` opens a generation read session and calls `runSearchCommand`.
- `src/cli/flag-schemas.ts:searchSchema` independently mirrors the flags for argument reordering and typo validation.
- `src/cli/commands/search-mode.ts:SearchCommandInput` is the CLI shaped input type.
- `src/cli/commands/search-mode.ts:runSearchCommand` validates, resolves path and config, selects a mode, dispatches retrieval, renders, and optionally synthesizes.

Every CLI input:

| Input | Parser default | Current wiring |
|---|---:|---|
| `query` | Required | Sent to mode detection, retrieval, refine reporting, and synthesis prompt context. |
| `path` | None | Must be a directory. It is canonicalized and converted to an absolute subtree pattern. |
| `--keyword`, `-k` | `false` | Forces keyword mode. |
| `--heading-only`, `-H` | `false` | Keyword mode calls structural `search` rather than content search. |
| `--mode`, `-m` | Auto | Accepts `semantic`, `keyword`, or `hybrid`; otherwise `resolveMode` detects the mode. |
| `--limit`, `-n` | `10` | Controls result limit. A value of `10`, including an explicit value, is replaced by `config.search.defaultLimit`. |
| `--threshold` | `0.35` | Controls semantic filtering. A value of `0.35`, including an explicit value, is replaced by `config.search.minSimilarity`. |
| `--context`, `-C` | None | Sets both context before and after. |
| `--before-context`, `-B` | None | Overrides context before. |
| `--after-context`, `-A` | None | Overrides context after. |
| `--auto-index-threshold` | Config | Controls CLI prompting and automatic semantic index creation. |
| `--provider` | Active config | Overrides the embedding provider for semantic retrieval. |
| `--rerank`, `-r` | `false` | Enables cross encoder reranking in hybrid mode. |
| `--quality`, `-q` | Core default | Accepts `fast`, `balanced`, or `thorough`. |
| `--hyde` | `false` | Enables HyDE in semantic retrieval. |
| `--rerank-init` | `false` | Initializes the reranker and exits before search. |
| `--json` | `false` | Selects CLI JSON rendering. |
| `--pretty` | `true` | Pretty prints CLI JSON. |
| `--summarize`, `-s` | `false` | Invokes CLI synthesis after results render. |
| `--yes`, `-y` | `false` | Skips a paid provider confirmation prompt. |
| `--stream` | `false` | Uses provider streaming when supported. |
| `--fuzzy`, `-f` | `false` | Enables fuzzy keyword matching. |
| `--stem` | `false` | Enables stemming in keyword matching. |
| `--fuzzy-distance` | None | Sets edit distance and must be at least one. |
| `--refine` | Empty list | Repeated post retrieval content filters; overfetches five times before filtering. |

Mode dispatch:

- `src/cli/commands/search-mode.ts:runSemanticMode` calls `semanticSearchWithStats`.
- `src/cli/commands/search-mode.ts:runHybridMode` calls `hybridSearch`.
- `src/cli/commands/search-mode.ts:runKeywordMode` calls `search` for headings or `searchContent` for content.
- `src/cli/commands/search-refine.ts:filterResultsByRefineTerms` performs surface independent post filtering but currently lives under CLI ownership.

## MCP search definition and wiring

Primary entries:

- `src/mcp/tools.ts:tools` declares the public JSON schema for `md_search`.
- `src/mcp/schemas.ts:MdSearchArgs` independently declares runtime validation.
- `src/mcp/server.ts:createServer` dispatches the tool call.
- `src/mcp/handlers.ts:handleMdSearch` resolves defaults and calls semantic retrieval.
- `src/mcp/handlers.ts:formatSearchOutcome` adds empty corpus guidance and text formatting.

`md_search` exposes four inputs:

| Input | Current behavior |
|---|---|
| `query` | Required string. |
| `limit` | Integer from 1 through 100; handler default is 5. |
| `threshold` | Number from 0 through 1; handler default is `config.search.minSimilarity`, while tool help advertises 0.35. |
| `path_filter` | Optional canonical absolute path, relative glob, or bare path segment. |

`handleMdSearch` resolves the active query provider and calls `src/embeddings/semantic-search.ts:semanticSearch`. It does not expose mode selection, context, reranking, quality, HyDE, refine, or synthesis.

The adjacent `md_keyword_search` tool is a structural section filter. `src/mcp/handlers.ts:handleMdKeywordSearch` calls `search` with heading and section metadata filters. Its semantics differ from the CLI content, boolean, fuzzy, and BM25 keyword path.

## Retrieval core ownership

One shared end to end search function: **none found**.

Searches run:

- `fmm_search(term: "search")`
- `fmm_search(term: "SearchRequest")`
- `fmm_search(term: "ResolvedSearchOptions")`
- dependency graphs for `src/cli/commands/search-mode.ts` and `src/mcp/handlers.ts`
- symbol reads for every CLI mode and `handleMdSearch`

Current reusable owners:

- `src/embeddings/semantic-search.ts:semanticSearch` is the shared semantic function used by MCP and indirectly by hybrid search.
- `src/embeddings/semantic-search.ts:semanticSearchWithStats` is the CLI semantic variant.
- `src/search/hybrid-search.ts:hybridSearch` owns multi channel retrieval and RRF.
- `src/search/content-search.ts:searchContent` owns content keyword search.
- `src/search/content-search.ts:search` owns structural heading and metadata search.
- `src/search/searcher.ts` is a stable facade for content search and context exports.
- `src/search/path-matcher.ts:prepareUserPathFilter` is the shared path scope owner.
- `src/search/path-matcher.ts:canonicalSubtreePathPattern` converts the CLI directory argument to a path filter.
- `src/embeddings/types.ts:SemanticSearchOptions`, `src/search/hybrid-search.ts:HybridSearchOptions`, and `src/search/content-search.ts:SearchOptions` are separate mode contracts.

There are no runtime dependency cycles through either surface according to fmm.

## Existing section content reuse

The code already contains the raw material for source backed synthesis:

- `src/search/content-search.ts:SearchResult` has `sectionContent`.
- `src/search/content-search.ts:searchContent` populates `sectionContent` for content matches.
- `src/search/content-search.ts:searchWithContent` can hydrate structural results.
- `src/embeddings/types.ts:SemanticSearchResult` has optional `content` and `contextLines`.
- `src/embeddings/semantic-search.ts:semanticSearchWithContent` can hydrate semantic results.
- `src/embeddings/semantic-search-pipeline.ts:addContextLinesToResults` reads complete matched section ranges plus requested surrounding context.
- `src/search/hybrid-search.ts:HybridSearchResult` preserves semantic `contextLines` through channel projection.
- `src/cli/commands/search-refine.ts:filterResultsByRefineTerms` already caches file reads while inspecting section ranges.

`searchWithContent` and `semanticSearchWithContent` have no call expressions in `src` or `tests`. Searches run:

- `rg -n 'searchWithContent\\(' src tests`
- `rg -n 'semanticSearchWithContent\\(' src tests`

Both returned zero call sites. Their logic overlaps each other, context hydration, and refine hydration.

## Synthesis path

Primary entries:

- `src/cli/commands/search-summarization.ts:runSummarization` is the production CLI entry.
- `src/cli/commands/search-summarization.ts:runSummarizationUnsafe` owns provider selection, cost display, consent, streaming, timing, and output.
- `src/summarization/pipeline.ts:SummarizableResult` permits optional content.
- `src/summarization/pipeline.ts:formatResultsForSummary` emits numbered path, heading, score, optional similarity, and optional content truncated to 500 characters.
- `src/summarization/pipeline.ts:runSummarizationPipeline` is a second, generic orchestration path used only by its tests and barrel export.
- `src/summarization/prompts.ts:DEFAULT_PROMPT` asks for synthesis but does not require evidence citations.
- `src/summarization/cli-providers/claude.ts:ClaudeCLISummarizer.summarize` spawns one `claude -p` process per request.

Payload by mode today:

| Mode | Payload sent to synthesis | Available data that is dropped |
|---|---|---|
| Semantic | Document path, heading, similarity | `content`, complete section `contextLines`, section identifier |
| Hybrid | Document path, heading, RRF score, optional similarity | `contextLines`, source channels, section identifier |
| Keyword | Document path and heading | `sectionContent`, match excerpts, line ranges, section identifier |

The `-C`, `-B`, and `-A` flags can load complete section content for semantic and hybrid display, but the mode adapters omit that content when building `SummarizableResult`. Adding context did not improve the road test synthesis for this reason.

Current source attribution consists of a numbered absolute path and heading. There is no line range, required excerpt, or prompt requirement to cite numbered sources. The summarizer never reads source files and never runs another search.

## Path scope determination

All three retrieval modes apply `prepareUserPathFilter` before returning hits:

- Semantic filters raw vector hits in `src/embeddings/semantic-search-pipeline.ts:postProcessResults`.
- Hybrid prepares one predicate in `src/search/hybrid-search.ts:collectSearchChannels` and applies it to semantic and BM25 channels.
- Keyword applies it inside `search` and `searchContent`.
- MCP passes `path_filter` directly to semantic search.
- CLI canonicalizes its directory argument and passes an absolute subtree pattern to every mode.

The synthesis function receives only the returned hits, so it cannot widen scope independently. Existing tests cover semantic, hybrid, keyword, absolute MCP filters, canonical path round trips, and outside corpus misses.

The road test command used `/Users/alphab/.mdx/projects` as the CLI path. The two tail results, `tm-http-store-scout-schema.md` and `cubicell-scout-clientid-grok.md`, are both within that directory. The observed behavior is a broad requested scope combined with low relevance tail hits, rather than a bypass in the synthesis path.

A real parity gap remains. MCP can accept a bare filter such as `b_style`, which `prepareUserPathFilter` matches against path segments and filenames. The CLI path argument only accepts a directory, so it cannot express the same topical filename filter. One shared `pathFilter` field should own both semantics; the CLI directory argument can remain sugar for an absolute subtree filter.

# Quality Map

| Area | Evidence | Consequence |
|---|---|---|
| Surface option duplication | CLI has `searchOptions` plus `searchSchema`; MCP has `tools` JSON schema plus `MdSearchArgs`. | Four declarations can drift before execution begins. |
| Orchestration fork | CLI owns mode selection and three retrieval paths; MCP calls semantic search directly. | Fixes, defaults, degradation, and new features must be repeated. |
| Default drift | CLI parser says 10 results, MCP handler says 5; MCP help hard codes 0.35 while runtime can use config. | Equivalent requests differ by surface. |
| Sentinel defaults | CLI treats any limit of 10 and threshold of 0.35 as omitted. | Explicit user values can be replaced by config. |
| Unenforced config | `SearchConfig.maxLimit`, `includeSnippets`, and `snippetLength` have no runtime search consumers. | Limits and documented snippet policy are inert. The snippet fields are useful inputs for excerpt hydration. |
| Misnamed MCP keyword surface | `md_keyword_search` performs heading and metadata filtering through `search`. | Tool naming suggests parity with CLI keyword search while behavior differs. |
| Synthesis duplication | `runSummarizationUnsafe` duplicates provider, cost, prompt, and execution behavior from `runSummarizationPipeline`. | Production behavior and tested generic behavior can diverge. |
| Metadata only synthesis | Every production mode omits available content; `SummarizableResult.content` is optional. | The provider can only restate headings and scores. |
| Hydration duplication | `searchWithContent`, `semanticSearchWithContent`, `addContextLinesToResults`, and refine filtering repeat file read and section slicing logic. | IO, error policy, caching, and excerpt rules are inconsistent. |
| Source attribution boundary | Formatter emits path and heading; prompt does not require citations or line ranges. | Output is weakly auditable. |
| Provider latency | Claude synthesis spawns a fresh CLI process. The road test measured 18.4 seconds inside generation and 22.8 seconds total. | Larger excerpts may improve quality without fixing process startup latency. No internal latency root cause beyond process invocation is proven. |
| Documentation drift | `TLDR.md` says all three modes exist on CLI and MCP. `PROJECT.md` describes API and multiple CLI summarizers that current factories reject. | Users and agents receive inaccurate capability claims. |
| Boundary concentration | `search-mode.ts` is 500 LOC and mixes config, index lifecycle, mode policy, retrieval, refine, rendering, and synthesis. `handlers.ts` is 379 LOC across all MCP tools. | Adding parity directly to either file will deepen the fork. |
| LOC gate failure | `hybrid-search.test.ts` is 703 LOC. MCP server and path acceptance tests are 698 and 699; keyword integration is 686. | New tests cannot be added safely to these files. The current LOC gate exits 1. |
| Stale LOC baseline | `check-loc-limit.sh` still grants old caps to split files, including 1,316 lines for current 152 line `search.ts`. | Refactored files can regrow above 700 without a gate failure. |

Measured relevant files:

- `src/search/__tests__/hybrid-search.test.ts`: 703 LOC
- `src/mcp/path-round-trip.acceptance.test.ts`: 699 LOC
- `src/mcp/server.test.ts`: 698 LOC
- `src/integration/search-keyword.test.ts`: 686 LOC
- `src/search/hybrid-search.ts`: 608 LOC
- `src/cli/commands/search-mode.ts`: 500 LOC
- `src/embeddings/semantic-search-pipeline.ts`: 466 LOC
- `src/cli/flag-schemas.ts`: 430 LOC
- `src/search/path-matcher.ts`: 406 LOC
- `src/mcp/handlers.ts`: 379 LOC

# Key Decision

Adopt one surface neutral `SearchRequest` with an optional nested `SynthesisRequest`, one resolver, one executor, and one normalized `SearchHit` result. CLI and MCP should be transport adapters around that owner.

Do not force transport concerns into the shared contract. CLI JSON formatting, pretty output, paid provider confirmation, reranker initialization, and terminal streaming remain adapter concerns. MCP can return a final synthesis unless MCP progress notifications are deliberately added.

Use existing domain types rather than redeclaring them: `SearchMode`, `SearchQuality`, provider identifiers, `PreparedPathFilter`, `AISummarizationConfig`, and generation read session types. `SearchRequest` is currently unused and avoids colliding with the existing mode specific `SearchOptions`.

# Ordered Plan

## 1. Repair guardrails before adding tests

1. Split `src/search/__tests__/hybrid-search.test.ts` by mode, parameters, and performance ownership.
2. Add new focused test files instead of growing the 698, 699, and 686 LOC suites.
3. Remove stale entries from `scripts/check-loc-limit.sh` for files now below 700, including `search.ts`, `embedding-namespace.ts`, `vector-store.ts`, `searcher.ts`, and `help.ts`.
4. Require the LOC gate to pass before the convergence work continues.

## 2. Establish the canonical request and defaults

1. Add a small search domain module under `src/search` that owns `SearchRequest`, `SynthesisRequest`, `ResolvedSearchRequest`, validation, and config default resolution.
2. Include query, mode, limit, threshold, shared path filter, heading and structural filters, context, fuzzy and stem options, refine terms, provider selection, rerank, quality, HyDE, and optional synthesis.
3. Resolve omission explicitly. Remove the `10` and `0.35` sentinel checks.
4. Enforce `config.search.maxLimit` for both surfaces.
5. Make the CLI directory argument normalize into `pathFilter`; add a true CLI path filter option for bare and glob parity.
6. Build CLI and MCP adapter inputs into the same resolved request. Keep one shared metadata specification where practical and add a parity test for any syntax declarations that must remain separate.

Reuse: `SearchMode`, `SearchQuality`, `prepareUserPathFilter`, `canonicalSubtreePathPattern`, provider identifiers, and `SearchConfig`.

## 3. Move search orchestration below both surfaces

1. Extract mode policy and dispatch from `runSearchCommand` into a shared executor under `src/search`.
2. Move refine filtering out of `src/cli/commands` and place it beside the shared executor.
3. Reuse `semanticSearchWithStats`, `hybridSearch`, `searchContent`, and `search` behind one normalized `SearchHit` projection.
4. Keep CLI auto index prompts and reranker initialization outside the executor. Represent missing semantic capability as typed data or a typed error that each adapter can handle.
5. Route `handleMdSearch` through the executor.
6. Fold current `md_keyword_search` capabilities into the shared request. Since the project is pre release, retire or rename the misleading parallel tool after its structural filters are preserved.

## 4. Consolidate section hydration

1. Extract one cached section content loader from the four existing implementations.
2. Load section content only after path filtering and final ranking.
3. Return bounded excerpts with source identifier, canonical document path, heading, section identifier, and line range.
4. Reuse `SearchConfig.includeSnippets` and `snippetLength` for ordinary result excerpts. Add a separate total synthesis input budget because file compression budgets have different semantics.
5. Rewrite or delete `searchWithContent` and `semanticSearchWithContent` after all callers use the shared loader. Remove parallel implementations in the same change.

## 5. Make one synthesis pipeline production authoritative

1. Change the synthesis input from optional metadata to a required `SynthesisSource` with a bounded excerpt and attribution fields.
2. Extend `runSummarizationPipeline` with the streaming callback and provider resolution behavior needed by CLI.
3. Replace `runSummarizationUnsafe` orchestration with the shared pipeline; leave terminal consent and rendering in the CLI adapter.
4. Route MCP synthesis through the same pipeline when `SynthesisRequest` is present.
5. Update the prompt to answer the query directly, cite numbered sources, and state when evidence is insufficient.
6. Return retrieval, hydration, provider, and generation durations separately. Treat the 18.4 second provider latency as a measured provider characteristic until a benchmark proves a code level remedy.

## 6. Converge outputs and documentation

1. Make CLI and MCP project the same normalized hits and synthesis result.
2. Keep CLI text and JSON formatters and MCP content formatting as thin views.
3. Update `README.md`, `TLDR.md`, and `PROJECT.md` from implemented capability truth.
4. Document shared path filter semantics with a narrow `b_style` example and distinguish path scope from topic relevance.

# Tests and Gates

## Focused tests

1. Request resolver tests: omitted values use config, explicit `10` and `0.35` remain explicit, maximum limit is enforced, and both adapters resolve equal requests.
2. Mode parity tests: semantic, keyword, and hybrid requests through CLI and MCP produce the same mode and normalized hit paths.
3. Keyword semantics tests: CLI and MCP keyword mode use the same boolean, fuzzy, stem, heading, and structural filter behavior.
4. Path tests: absolute directory, relative glob, bare filename segment, alias, outside corpus miss, and Windows separators behave identically.
5. Synthesis scope test: an off scope high score result is removed before hydration and cannot appear in the captured provider payload.
6. Synthesis payload tests: each source contains bounded body text, canonical path, heading, line range, and stable source number.
7. Context regression test: `-C`, `-B`, and `-A` content reaches synthesis when requested rather than being discarded.
8. Source backed acceptance fixture: a fake summarizer captures the exact input and proves that the relevant decisions are present; a prompt contract requires citations.
9. Provider adapter tests: streaming and nonstreaming use the same source payload and report phase timings.
10. Breaking surface test: the final MCP tool list and help text reflect the single search contract and any retirement or rename of `md_keyword_search`.

## Commands

Run the new focused Vitest files first, then:

```bash
pnpm exec vitest run
pnpm typecheck
pnpm exec biome check .
./scripts/check-loc-limit.sh
pnpm build
npx publint
npx attw --pack .
node dist/cli/main.js search --help
```

Do not use `pnpm check` as a verification only gate because it writes through `format` and `lint`. Use the nonwriting Biome command above for proof.

Run one manual road test with a narrow `b_style` path filter. Record retrieval, hydration, time to first output, generation, and total duration. Acceptance requires a direct answer about what the project is, what to preserve, and the rebuild decisions, with numbered source citations and no path outside the filter.

# Dependencies

- Effect supplies typed effects, schemas, services, config, and CLI integration.
- Model Context Protocol SDK supplies the tool server and public tool schema.
- `wink-bm25-text-search` supplies keyword ranking.
- `hnswlib-node` supplies semantic nearest neighbor search.
- Hugging Face transformers supplies optional cross encoder reranking.
- The provider factory and Claude CLI adapter supply synthesis today. Other declared providers are not implemented.
- `tiktoken` can enforce a total synthesis input budget with existing token utilities.

# Relevance to Helioy

This convergence gives Helioy agents one predictable retrieval contract regardless of whether they invoke `mdm` through shell or MCP. Source backed excerpts and stable attribution also reduce extra context fetches and make synthesis auditable.

# Open Questions

1. Should MCP return structured hit and synthesis fields rather than one text block? A structured response would preserve attribution without reparsing.
2. Should `md_keyword_search` be removed, renamed to structural section search, or folded completely into `md_search`? Pre release status permits the cleaner breaking change.
3. What total synthesis input budget and per source minimum produce acceptable answers on real corpora?
4. Is sub 10 second generation a product requirement? The current evidence only proves fresh Claude CLI process latency, so a target should precede provider or process architecture changes.
