# MDM CLI read surface scout

Date: 2026-07-21

Branch: `fix/cli-read-guidance-and-search-path`

Base: `origin/design/federated-knowledge-layer` at `29247fe5533b2f93e56c802fcaad8ff63a4b7d71`

Scope: scout and plan only. No source code changed.

## Verdict

Root shape: one shared CLI generation read helper, plus one search scope value passed through every existing `pathPattern` seam.

The missing generation defect is duplicated command boundary plumbing. The search path defect is missing option wiring in all three CLI mode runners. The core filtering implementations already exist and should remain unchanged.

## Verified baseline

1. `pnpm build` passed from the target branch.
2. `pnpm exec vitest run src/cli/generation-session.test.ts` passed: 1 file, 2 tests.
3. A fresh empty `MDM_HOME` produced the following behavior from the rebuilt CLI.

| Command | Exit | Result |
| --- | ---: | --- |
| `search needle . --keyword` | 0 | Friendly `No index found.` guidance |
| `stats` | 2 | Raw `GenerationReadError` and stack |
| `links README.md` | 2 | Raw `GenerationReadError` and stack |
| `backlinks README.md` | 2 | Raw `GenerationReadError` and stack |
| `duplicates` | 2 | Raw `GenerationReadError` and stack |
| `embeddings list` | 2 | Raw `GenerationReadError` and stack |
| `embeddings current` | 2 | Raw `GenerationReadError` and stack |
| `tree README.md` | 0 | Source outline succeeds without an index |
| `context README.md` | 0 | Source summary succeeds without an index |

4. Against the active 36,313 section corpus, these commands returned the same ten `.mdx/design` results and the same global index header:

   1. `mdm search warroom /Users/alphab/.mdx/design --keyword`
   2. `mdm search warroom /Users/alphab/Dev/LLM/DEV/helioy/audioface --keyword`

The second directory is outside the indexed manifest. Its results prove the positional directory remains a silent no op on this base.

## Reuse map

### First run guidance

The current friendly mapping has two parts in `src/cli/commands/search.ts`:

1. `renderNoIndexGuidance` at lines 11 to 31 renders text and JSON guidance.
2. `searchCommand` at lines 169 to 178 catches `GenerationReadError`, checks `error.reason === 'NoCurrentGeneration'`, and calls that renderer. Other generation read failures continue to the existing top level error boundary.

The typed reason originates in `src/db/generation-reader.ts:249-258`. The top level fallback in `src/cli/error-handler.ts:545-557` treats an uncaught `GenerationReadError` as unexpected and prints its stack.

Reuse target: move `renderNoIndexGuidance` into the shared CLI utility boundary and add one generic wrapper around `withCurrentGeneration`. Every database read command calls that wrapper. The wrapper catches only `NoCurrentGeneration`; all other failures remain failures.

### Existing path filter wiring

The MCP handlers show the intended option flow:

| Surface | Existing wiring |
| --- | --- |
| Semantic MCP | `src/mcp/handlers.ts:59-76`, `path_filter` becomes `semanticSearch(..., { pathPattern })` |
| Keyword MCP | `src/mcp/handlers.ts:171-186`, `path_filter` becomes `search(..., { pathPattern })` |

The downstream implementations already consume that option:

| Channel | Existing implementation |
| --- | --- |
| Hybrid semantic | `src/search/hybrid-search.ts:278-287` forwards `options.pathPattern` to `semanticSearch` |
| Hybrid BM25 | `src/search/hybrid-search.ts:295-309` filters BM25 results with `matchesDocumentPath` |
| Direct semantic | `src/embeddings/semantic-search-pipeline.ts:400-418` filters before ranking and limiting |
| Direct heading and content | `src/search/content-search.ts:87-118` and `289-361` apply `matchesDocumentPath` |
| Path matcher | `src/search/path-matcher.ts:31-56` owns portable glob matching and relative document path construction |

No new search filter belongs in the CLI.

## Command boundary audit

`src/cli/generation-session.test.ts:7-23` defines the architectural split. Database commands acquire one generation lease. `tree` and `context` remain source only.

| Command symbol | Current state | Required change |
| --- | --- | --- |
| `src/cli/commands/search.ts:searchCommand` | Owns the only friendly mapping | Use the shared helper after extraction |
| `src/cli/commands/stats.ts:statsCommand` | Calls `withCurrentGeneration` directly | Use the shared helper |
| `src/cli/commands/links.ts:linksCommand` | Calls `withCurrentGeneration` directly | Use the shared helper |
| `src/cli/commands/backlinks.ts:backlinksCommand` | Calls `withCurrentGeneration` directly | Use the shared helper |
| `src/cli/commands/duplicates.ts:duplicatesCommand` | Calls `withCurrentGeneration` directly | Use the shared helper |
| `src/cli/commands/embeddings.ts:listSubcommand` | Calls `withCurrentGeneration` directly | Use the shared helper |
| `src/cli/commands/embeddings.ts:currentSubcommand` | Calls `withCurrentGeneration` directly | Use the shared helper |
| `src/cli/commands/tree.ts:treeCommand` | Reads source files only | Keep outside the generation boundary |
| `src/cli/commands/context.ts:contextCommand` | Reads source files only | Keep outside the generation boundary |

`statsCommand` and `duplicatesCommand` contain local `No index found` output after lease acquisition. Route those branches through the extracted renderer as well so the wording remains singular. Embedding namespace absence remains separate because a valid structural generation may intentionally contain no embeddings.

## Search path root cause

`runSearchCommand` resolves the positional path at `src/cli/commands/search-mode.ts:352-357`, then stores it only as `ExecutionContext.sourceRoot` at lines 403 to 416.

All three mode runners omit `pathPattern`:

1. `runHybridMode`, lines 84 to 107.
2. `runKeywordMode`, lines 161 to 183.
3. `runSemanticMode`, lines 226 to 249.

`sourceRoot` is an anchor for relative matching and source resolution. It does not itself select matching documents. With `pathPattern` absent, `matchesDocumentPath` returns `true` for every document at `src/search/path-matcher.ts:46-56`.

## Minimal fix plan

### 1. Centralize missing generation guidance

1. Move `renderNoIndexGuidance` from `search.ts` to `src/cli/utils.ts`.
2. Add `withCurrentGenerationGuidance` beside it. Inputs are `json`, `pretty`, and the generation read callback. It resolves the MDM home, calls `withCurrentGeneration`, catches only `NoCurrentGeneration`, and delegates to `renderNoIndexGuidance`.
3. Replace direct lease calls in search, stats, links, backlinks, duplicates, and both embedding subcommands with the helper.
4. Keep `tree` and `context` unchanged and index independent.
5. Update `generation-session.test.ts` so command files own no raw lease plumbing, the shared helper owns exactly one raw `withCurrentGeneration` call, and the source only commands own neither.

This preserves one lease per database command and one mapping for every command.

### 2. Represent the positional directory as an existing path pattern

Add one small search scope constructor in `search-mode.ts`:

1. Canonicalize the requested directory through the existing canonical path utility.
2. Use its parent as the filter `sourceRoot`.
3. Use `<directory basename>/**` as the portable `pathPattern`.
4. Retain the requested directory separately for user output and embedding setup.

The parent anchor matters. A bare `**` with the requested directory as `sourceRoot` also matches relative paths beginning with `../`, which would preserve the cross root leak.

Add `pathPattern` to `ExecutionContext`, then pass it through the exact existing seams:

1. `hybridSearch(..., { pathPattern })` in `runHybridMode`.
2. `search` and `searchContent` options in `runKeywordMode`.
3. `semanticSearchWithStats(..., { pathPattern })` in `runSemanticMode`.

No change is required in MCP handlers, `hybrid-search.ts`, `semantic-search-pipeline.ts`, `content-search.ts`, or `path-matcher.ts`.

### 3. Guide an unindexed or empty subtree

Before mode dispatch, query the structural index with the same `sourceRoot` and `pathPattern`, no content predicate, and `limit: 1`.

If no indexed section exists in scope:

1. Text output says `No indexed documents found in <path>.` and `Run: mdm index <path>`.
2. JSON output carries the same error, path, and guidance fields.
3. Return before semantic provider resolution or full corpus search.

This distinguishes an empty scope from a valid indexed scope whose query has zero matches. It also reuses the existing keyword path filter rather than scanning or matching paths in the CLI.

## TDD list

### Shared first run boundary

1. Extend the fresh home CLI test into a table covering search, stats, links, backlinks, duplicates, embeddings list, and embeddings current.
2. For every text invocation, assert exit 0, `No index found.`, `Run: mdm index /path/to/docs`, and no `GenerationReadError`, `No current generation exists`, or stack trace on either stream.
3. Repeat each command's JSON form and assert parseable guidance with no diagnostic leakage.
4. Run `tree README.md` and `context README.md` against the same empty home and assert their normal source output. This pins their source only contract.
5. Update the source architecture test to assert one shared raw lease call and shared helper use at every database command boundary.

### Positional search scope

1. Create an isolated corpus with the same marker inside `scope/inside.md` and outside it in `outside.md`.
2. Run keyword CLI search with the `scope` positional directory. Assert only `inside.md` appears in text and JSON.
3. Run forced hybrid mode against a BM25 fixture. Assert the same subtree restriction.
4. Unit test the semantic runner boundary so its `semanticSearchWithStats` call receives the same `pathPattern`. Existing semantic pipeline path filter tests continue to prove downstream behavior.
5. Unit test the scope constructor with relative, absolute, nested, trailing separator, symlink, and portable separator inputs. Assert the pattern cannot match a sibling through `../`.
6. Run a query with no matches in an indexed subtree. Assert ordinary zero result output without reindex guidance.
7. Run against an existing unindexed directory and an indexed root containing an empty subtree. Assert explicit scoped guidance and no result outside the requested path.

### Gates

1. Targeted CLI, generation session, keyword path, hybrid path, and semantic path tests.
2. `pnpm typecheck`.
3. `pnpm build`.
4. Full `pnpm test` with its final pass and failure count recorded.

## Change boundary

The implementation should touch the shared CLI utility, the seven generation reading command callbacks, `search-mode.ts`, and focused tests. Core search filtering and MCP behavior remain unchanged.
