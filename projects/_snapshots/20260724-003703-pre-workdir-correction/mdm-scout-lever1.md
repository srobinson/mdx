# LEVER 1 scout: empty result guidance

Date: 2026-07-22

Branch: `feat/empty-result-guidance`

Base: `origin/design/federated-knowledge-layer` at `67697af`

Scope: scout and plan only. No product code changed.

## Root shape

Use a shared builder. MCP and CLI keep their existing success renderers, but every empty result pointer and typed zero state error is derived from one neutral guidance value. Do not add per surface wording.

## 1. Reuse map

| Concern | Existing seam | Reuse decision |
|---|---|---|
| MCP success envelope | `src/mcp/handlers.ts:48-94` and `src/mcp/handlers.ts:166-211` build `md_search` and `md_keyword_search` text | Preserve successful formatting exactly. On an empty array, call one shared guidance builder and wrap its text with `mcpText`. |
| MCP error envelope | `src/mcp/adapter.ts:31-62` owns `effectToMcpResult` and `mcpError` | Recognize typed missing generation centrally here. Reuse the shared first run value instead of exposing the raw generation read error. Other errors keep their current message unless an in session corpus inspection proves a corpus miss. |
| CLI missing generation | `src/cli/utils.ts:31-70` owns `renderNoIndexGuidance` and `withCurrentGenerationGuidance` | Extract the existing first run data and wording into the neutral builder. Keep `renderNoIndexGuidance` as the text and JSON adapter. Existing guidance is `Run: mdm index /path/to/docs`. |
| CLI search output | `src/cli/commands/search-output.ts:68-368` owns the hybrid, keyword, and semantic renderers | Pass an optional guidance value only when results are empty. Keep every nonempty text and JSON shape unchanged. |
| CLI search dispatch | `src/cli/commands/search-mode.ts:87-457` owns all three mode results before rendering | Resolve empty guidance once after the selected query completes. The three mode runners call the same helper. Do not rerun a mode or query. |
| Corpus roots | `src/manifest.ts:74-100` exposes `loadManifest`; declared paths are expanded during decoding | Reuse `manifest.directories.map(directory => directory.path)` in manifest order for the root list. |
| Document count and real examples | `src/index/storage.ts:305-339` exposes `createStorage` and `loadDocumentIndex`; `src/index/types.ts:19-36` defines `DocumentEntry.path` and aliases | Count `Object.values(documentIndex.documents)`. Sort canonical `entry.path` values and take up to three. These are the same canonical paths search returns. Hardlink aliases remain one document. |
| Path filter truth | `src/search/path-matcher.ts:94-282` owns alias aware, case aware filter preparation | Factor its already loaded manifest and document index path into a reusable internal preparation function. A new corpus inspection helper can then prepare the predicate and count matching documents without loading either artifact twice. |
| Typed path miss | `src/mcp/path-resolution.ts:10-45` owns `PathNotInIndexedCorpusError` and already has manifest roots | Keep the type. Build its message from the shared guidance value, adding corpus roots and canonical examples. Do not fall through to empty links or backlinks. |
| Existing corpus statistics | `src/cli/commands/stats.ts:53-89` computes counts directly; `src/db/generation-validation.ts:196-235` computes validation counts | Neither is a suitable read time accessor. The CLI implementation is command local. Generation validation reads and validates every artifact. Reuse `loadManifest` plus `loadDocumentIndex` for a lightweight read snapshot. |

There is currently no combined read time accessor for roots, document count, examples, and path filter count. The minimal addition is one helper built from the existing manifest, document index, and matcher primitives. `validateGeneration` is deliberately excluded because empty response guidance must not trigger full generation validation.

## 2. Distinguishing the causes without rerunning the query

Define one diagnostic snapshot:

```text
CorpusInspection
  documentCount
  pathFilterDocumentCount
  roots
  examplePaths
```

Load the manifest and document index together once. When `path_filter` is present, prepare the existing user path predicate from those loaded values and count unique indexed documents accepted by it. This reads no markdown source, section index, BM25 index, vector store, or provider.

Classification order:

1. `NoCurrentGeneration` means CORPUS miss. Use the existing first run guidance immediately because no read session exists.
2. With a read session, `documentCount === 0` means CORPUS miss. This rule also handles semantic search failing for missing embeddings over an indexed but empty corpus.
3. With documents present, a supplied filter and `pathFilterDocumentCount === 0` means FILTER miss.
4. Every successful empty query with a satisfiable filter, or no filter, means QUERY miss.
5. `PathNotInIndexedCorpusError` is a typed sibling pointer for path tools. It reports the requested path, roots, and real examples. If its diagnostic snapshot has zero documents, CORPUS miss takes priority.

Required wording:

```text
CORPUS miss
No indexed documents found. Run: mdm index /path/to/docs

FILTER miss
path_filter matched 0 of N docs; filter matches paths like [p1, p2, p3]; corpus roots: [r1, r2]

QUERY miss
no matches for "query" across N indexed documents

OUT OF CORPUS
Path not in indexed corpus: path; use an indexed path like [p1, p2, p3]; corpus roots: [r1, r2]
```

The filter cause is operationally defined by filter satisfiability against indexed documents. Proving that a query matches outside a satisfiable filter would require another whole corpus query. The locked `path_filter matched 0 of N docs` pointer and the no rerun rule make document level filter satisfiability the reliable boundary.

For `md_keyword_search`, use the heading value as the query label. When no heading exists, build a stable criteria label from the active structural flags, such as `has_code=true`, rather than emitting `undefined`.

Error routing:

- Missing generation maps to CORPUS guidance at the shared boundary.
- A search error inside a valid session performs one diagnostic snapshot. Zero documents maps to CORPUS guidance. A nonempty corpus preserves the original provider, embedding, manifest, or index error.
- A successful nonempty response bypasses inspection and guidance entirely.
- A successful empty response performs one diagnostic snapshot. The original query function has already returned and is never called again.

## 3. Proposed minimal design

### A. Add one neutral guidance module

Add `src/read-guidance.ts` with a small discriminated union for `corpus`, `filter`, `query`, and `out-of-corpus`, plus pure classification and text formatting functions. Export the first run guidance data used by `renderNoIndexGuidance`.

The builder accepts facts. It does not load files and has no MCP or CLI dependency. Both output systems consume the same exact wording.

### B. Add one corpus inspection helper

Add an alias aware inspection helper beside the path matcher, or in a small `src/search/corpus-inspection.ts` module:

1. Load `loadManifest(session.home)` and `loadDocumentIndex(createStorage(session.indexRoot, session.indexRoot))` once with `Effect.all`.
2. Reuse a factored path matcher preparation function with the loaded values.
3. Return document count, matching document count, roots, and up to three sorted canonical document paths.

Keep `prepareUserPathFilter` as the public search API. Make it delegate to the same internal matcher preparation. This avoids a second implementation of path semantics and retains hardlink, literal glob, case sensitivity, and multi root behavior from L2.

### C. Route MCP search outcomes through one helper

Add one generic search outcome helper used by `handleMdSearch` and `handleMdKeywordSearch`:

- Nonempty success calls the existing formatter unchanged.
- Empty success inspects once and returns shared guidance through `mcpText`.
- Failure inspects once only while a session exists. It substitutes CORPUS guidance only when the document count is zero, otherwise it rethrows the original error.

Extend `effectToMcpResult` only for typed `GenerationReadError` with reason `NoCurrentGeneration`. This centralizes missing generation guidance for every MCP read tool without changing unrelated failures.

### D. Keep the path error typed

When `resolveMcpDocumentPath` finds no candidate inside any served root, reuse the manifest already loaded there and inspect the document index once. Construct `PathNotInIndexedCorpusError` with the shared out of corpus text. All four path tools retain `isError: true` through `effectToMcpResult`.

### E. Add CLI guidance where the data is already cheap

In `search-mode.ts`, call the same empty outcome helper after the selected mode returns zero results and pass its structured value to the existing renderer. Text renderers print the pointer after `Results: 0`. JSON renderers add one `guidance` object only for empty results. Nonempty output remains byte for byte unchanged.

Keep `withCurrentGenerationGuidance` and `renderNoIndexedPathGuidance`, but source their wording from the neutral builder. The existing positional path preflight should use corpus scope inspection instead of a synthetic `search(..., limit: 1)` call when this slice touches it.

### F. Scope boundaries

- Do not change ranking, thresholds, limits, or success result schemas.
- Do not query providers, vectors, BM25, sections, or source files for diagnostics.
- Do not turn provider or corruption failures into query misses.
- Do not add a guidance header to successful nonempty output.
- Do not duplicate wording between MCP, CLI text, and CLI JSON.

## 4. TDD test list

Write failing tests before implementation.

### Shared builder and inspection

1. CORPUS priority: zero documents plus any filter builds first run guidance.
2. FILTER: three documents plus an impossible filter builds the exact `path_filter matched 0 of 3 docs` pointer with sorted canonical examples and manifest roots.
3. QUERY: a satisfiable filter plus an empty query result builds `no matches for "query" across N indexed documents`.
4. Alias contract: a hardlink alias filter counts the deduplicated document once and uses the canonical survivor path as the example.

### MCP search surfaces

5. `md_search`, missing generation: returns the CORPUS pointer and hides `GenerationReadError`, `No current generation exists`, and stack text.
6. `md_keyword_search`, indexed empty generation: returns the same CORPUS pointer.
7. Both search handlers, impossible `path_filter`: return the exact FILTER pointer, real example paths, and every manifest root. Assert the semantic query mock was called once.
8. `md_search`, no semantic matches with a nonempty corpus and no filter: returns the QUERY pointer with the query and document count.
9. `md_keyword_search`, no heading match with a satisfiable filter: returns the QUERY pointer with the heading and document count.
10. Both search handlers, nonempty success: assert the complete existing success text and assert absence of `path_filter matched`, `corpus roots`, `no matches for`, and `mdm index`.

Use the multi root fixture in `src/mcp/path-round-trip.acceptance.test.ts`. It already supplies canonical paths, manifest roots, a hardlink alias, and a semantic search mock.

### MCP path tools

11. Pass one outside path through `md_context`, `md_structure`, `md_links`, and `md_backlinks`. Assert all four remain typed errors and contain the requested path, roots, and canonical examples. Assert links and backlinks never return their ordinary empty messages.

### CLI equivalents

12. Keyword query miss, text and JSON: zero results include QUERY guidance and corpus size.
13. Indexed empty corpus, text and JSON: search includes the shared CORPUS guidance.
14. Positional path matching zero documents: preserve the existing index pointer and prove no result from another root leaks.
15. Nonempty keyword and hybrid responses: compare the complete prior text and JSON shapes and assert no guidance field or pointer text appears.

### Focused verification commands for the later build

```bash
npx vitest run src/mcp/path-round-trip.acceptance.test.ts src/mcp/server.test.ts src/cli/cli-read-surface.test.ts src/search/path-matcher.test.ts
npm run typecheck
npx biome check .
npm run build
git diff --check
```

Then run the repository default test matrix before publication.

## Recommendation

Proceed with the shared builder shape. The corpus snapshot is small, deterministic, generation pinned, and sufficient to classify the three search zero causes without running a query twice. The only wider refactor should be the internal path matcher preparation needed to keep corpus inspection single load and DRY.
