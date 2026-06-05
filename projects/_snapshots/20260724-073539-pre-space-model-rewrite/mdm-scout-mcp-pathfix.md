# MDM MCP path tool root resolution scout

Date: 2026-07-21

Branch: `fix/mcp-path-tool-root-resolution`

Base: `origin/design/federated-knowledge-layer` at `29247fe5533b2f93e56c802fcaad8ff63a4b7d71`

Scope: Finding D scout and plan only, plus the requested Finding F assessment. No source code changed. Finding E was withdrawn after confirming that `CLAUDE.md` was a legitimate symlink to `TLDR.md`.

## Verdict

Root shape: one shared indexed corpus path resolver used by `md_context`, `md_structure`, `md_links`, and `md_backlinks`.

The MCP server does not currently resolve a served source root. `src/mcp/server.ts:main` captures `process.cwd()` as `rootPath`, and `createServer` passes that value to every handler. Search succeeds because the active generation stores canonical absolute `DocumentKey` values and both search handlers print those keys. The four path handlers send the supplied path through the CWD based `resolveAndValidatePath`, which breaks the search to inspect round trip.

The minimal safe fix should resolve input against manifest source roots, validate the result against the active generation document index, and return the canonical indexed `DocumentKey`. Existing realpath behavior must remain intact for symlinks. An existing resolved file with no active document entry should produce a clear `Path not in indexed corpus: <path>` MCP error.

## Verified baseline

1. The new branch matches `origin/design/federated-knowledge-layer` at `29247fe5533b2f93e56c802fcaad8ff63a4b7d71`.
2. The tracked tree is clean. The pre-existing untracked `LESSONS.md` remains untouched.
3. `src/mcp/server.ts:main`, lines 142 to 153, sets `rootPath = process.cwd()` and passes it to `startMcpServer`.
4. The active local manifest currently has two source roots. This confirms that the resolver must support a root set rather than a single hard coded directory.
5. `src/mcp/server.test.ts` is exactly 700 lines. New coverage must live in focused test files. Adding tests to that file would cross the repository limit.

## Reuse map

### Search path authority and emitted references

| Flow | Existing owner | Verified behavior | Reuse decision |
| --- | --- | --- | --- |
| MCP server root | `src/mcp/server.ts:main`; `src/mcp/server.ts:createServer` | `main` obtains `rootPath` from process CWD. `createServer` passes the same string to all seven handlers. There is no distinct served source root value at this boundary. | Keep CWD for config and project selection. Remove it from the four document path handlers. |
| Semantic result identity | `src/embeddings/types.ts:VectorEntry`; `src/embeddings/semantic-search-pipeline.ts:postProcessResults` | Vector entries store `documentPath` as a canonical absolute `DocumentKey`. Search processing preserves that value. | Treat the stored `DocumentKey` as the search reference authority. |
| `md_search` output | `src/mcp/handlers.ts:handleMdSearch`, lines 70 to 82 | The handler acquires the active generation, calls `semanticSearch`, and prints `r.documentPath` verbatim. | Feed this absolute path into the shared corpus resolver without rebasing it on CWD. |
| Keyword result identity | `src/index/types.ts:SectionEntry`; `src/search/content-search.ts:search` | Section entries store `documentPath` as a canonical absolute `DocumentKey`. `search` loads the active generation indexes and returns the entry unchanged. | Use the same document reference contract as semantic search. |
| `md_keyword_search` output | `src/mcp/handlers.ts:handleMdKeywordSearch`, lines 178 to 197 | The handler prints `r.section.documentPath` verbatim. | The same shared corpus resolver must accept this reference. |
| Canonical source opening | `src/db/canonical.ts:resolveSourceFile` | Requires an absolute `DocumentKey` and normalizes it without joining process CWD. Search content readers already use it. | Return a `DocumentKey` from the MCP resolver, then open it through this owner. |
| Manifest source roots | `src/manifest.ts:loadManifest`; `src/index/manifest-build.ts:buildManifestIndex` | `loadManifest` decodes every declared root. `buildManifestIndex` passes those roots into one consolidated generation build. | Load this root set for relative input expansion and per-root boundary validation. Do not invent a second source root configuration. |
| Corpus membership | `src/index/link-index.ts:resolveDocumentKeyFromIndex`; `src/index/link-index.ts:resolveIndexedDocumentKey` | Canonicalizes an existing file and matches identity or a canonical path against active document entries. The private `findStoredDocumentKey` currently falls back to `source.key`, so the public name does not yet prove membership. | Refactor the private lookup to return no key when no entry matches. Existing callers already handle null, so graph and CLI miss behavior remains stable. Reuse the strict result in the MCP resolver. |
| Prefix membership primitives | `src/db/canonical.ts:isPathWithin`; `src/db/canonical.ts:belongsToAnyPrefix` | Own boundary aware path containment across declared and canonical aliases. | Reuse for allowed root checks. |
| Realpath guard | `src/mcp/adapter.ts:resolveAndValidatePath` | Resolves relative input beneath one root, rejects lexical escape, canonicalizes root and target, and rejects symlink escape. It returns the lexical path when the target is missing. | Keep this behavior. Call it through one multi-root corpus resolver rather than from each handler. |

### Current four tool path flow

| Tool | Current path flow | Failure |
| --- | --- | --- |
| `md_context` | `src/mcp/handlers.ts:handleMdm` calls `resolveAndValidatePath(rootPath, path)`, then `summarizeFile`. | Absolute search refs outside process CWD receive `Path outside root`. Relative refs are joined to process CWD. |
| `md_structure` | `src/mcp/handlers.ts:handleMdStructure` calls the same resolver, then `parseFile`. | Same defect. |
| `md_links` | `src/mcp/handlers.ts:handleMdLinks` resolves against process CWD, then calls `resolveIndexedDocumentKey` and `getOutgoingLinks`. | A wrong CWD candidate has no graph entry and produces a misleading empty result. |
| `md_backlinks` | `src/mcp/handlers.ts:handleMdBacklinks` follows the same path before `getIncomingLinks`. | Same defect. |

`src/mcp/adapter.ts:resolveAndValidatePath` is shared mechanically today, but its only root is the wrong CWD value. The correct shared owner should sit above it and supply the manifest root set plus active corpus membership.

## Proposed minimal Finding D fix

### 1. Add one indexed corpus resolver

Create a focused owner such as `src/mcp/path-resolution.ts:resolveMcpDocumentPath`. Keep it below the handler formatting layer.

Inputs:

1. Active `GenerationReadSession`.
2. Resolved `MDM_HOME`.
3. User supplied path.

Algorithm:

1. Load the current manifest roots through `loadManifest(home)`.
2. Load the document index once from `session.indexRoot`.
3. For an absolute input, validate it against every allowed root. For a relative input, construct one candidate under each allowed root and validate each candidate through the existing realpath guard.
4. Canonicalize every existing candidate and match it exactly by identity or stored path through `resolveDocumentKeyFromIndex`.
5. Deduplicate matches by `DocumentKey`.
6. Return the only match through `resolveSourceFile`.
7. Return a clear ambiguity error when the same relative spelling names different indexed documents in multiple roots. The response should request the absolute path already emitted by search.
8. Return `Path not in indexed corpus: <path>` when a resolved existing path has no active document entry. This prevents link and backlink misses from looking like a valid empty graph.
9. Preserve current missing file behavior. A missing candidate continues to the existing file read error for context and structure, or the existing empty graph result for links and backlinks. Preserve symlink realpath resolution and boundary checks.

This resolver is the only new path selection owner. Do not add per-tool path joining or direct manifest reads.

### 2. Route all four handlers through the resolver

`md_links` and `md_backlinks` already hold one generation session. Resolve the document inside that session, then query the graph with the returned key.

`md_context` and `md_structure` currently read source only. Corpus membership now requires the active document index, so each request must acquire one generation session around path resolution and source reading. Update `src/mcp/generation-session.test.ts` to reflect that ownership change. Keep one session per request.

No change belongs in parser, summarizer, graph construction, semantic search, keyword search, or symlink handling.

### 3. Preserve the security contract

The active document entry proves corpus membership. The manifest root guard proves the requested path belongs to an allowed served prefix. Both checks matter.

Keep these outcomes distinct:

1. Lexical traversal or a canonical target outside all allowed roots: structured path boundary error.
2. Existing allowed path absent from the active generation: `Path not in indexed corpus`.
3. Valid in corpus symlink: canonical indexed target, with no warning or fuzzy marker.
4. Missing file: existing downstream miss behavior.

The design contract at `docs/superpowers/specs/2026-06-22-federated-markdown-knowledge-layer-design.md`, lines 490 to 504, requires search references to round trip and the realpath guard to apply per allowed prefix.

## Finding F assessment

Finding F is a facet of Finding D. The CLI is the reference behavior.

Relative CommonMark link extraction and graph resolution already normalize `./` correctly:

1. `src/parser/parser.ts:extractLinks` stores the parser supplied `link.url`, including `./NOW.md`, and classifies it as internal.
2. `src/index/index-build.ts:resolveDocumentLinks` passes the href plus the source document declared path to the graph resolver.
3. `src/index/link-index.ts:resolveInternalLink` removes any fragment, then calls `path.resolve(path.dirname(fromPath), linkPath)`. This normalizes `./NOW.md` to an absolute sibling path before canonical identity selection.
4. `src/index/canonical-indexing.test.ts`, lines 53 to 72, directly proves `./target.md` resolves to the target `DocumentKey`.
5. `src/index/indexer.test.ts`, lines 107 to 143 and 477 to 506, proves standard relative CommonMark links populate forward and backward graph entries.

Graph construction never uses MCP process CWD. The empty MCP result occurs later in `src/index/link-index.ts:loadLinksFor`: it resolves the path supplied by `handleMdLinks` or `handleMdBacklinks` to a document key, then reads the graph entry. Finding D supplies the wrong CWD based file at that query boundary, so the lookup returns no key or queries the wrong document.

The D resolver should make an in corpus relative link document reach its existing graph entry. No extraction or normalization change is justified. Retest backlog item 8 after D; a remaining failure would need fresh evidence before any graph slice.

## TDD list

### Shared resolver tests

Create `src/mcp/path-resolution.test.ts`. Do not add lines to the 700 line `src/mcp/server.test.ts`.

1. Server CWD and manifest root are different. A unique relative document path resolves beneath the manifest root.
2. A canonical absolute `DocumentKey` resolves unchanged.
3. An absolute declared symlink resolves to its indexed canonical target. Pin the current `CLAUDE.md` to `TLDR.md` behavior with a temporary fixture.
4. A symlink whose canonical target escapes every allowed root remains rejected.
5. An existing markdown file under an allowed root but absent from the active document index returns `Path not in indexed corpus`.
6. An existing absolute file outside all manifest roots returns the same clear corpus signal without exposing content.
7. A missing path preserves the existing miss result path. No new fuzzy or basename behavior appears.
8. Two manifest roots with unique relative names resolve both documents. Equal relative names in both roots return an ambiguity error that requests an absolute path.
9. Lexical `..` traversal remains rejected.

### Search to inspect integration

Create a focused MCP integration test file and extract any shared deterministic embedding fixture rather than copying it from `src/mcp/index-generation.test.ts`.

1. Build an active generation from a manifest root that differs from server CWD.
2. Call `md_search`, capture the emitted absolute document path, and pass that exact string to `md_context`, `md_structure`, `md_links`, and `md_backlinks`.
3. Assert all four calls succeed and identify the same canonical document.
4. Call all four tools with a unique relative path. Assert they resolve against the manifest root.
5. Add a second manifest root and repeat the absolute round trip for one document in each root.
6. Call all four tools with an existing out of corpus CWD file. Assert a structured `Path not in indexed corpus` error. For links and backlinks, assert the response does not say `No outgoing links` or `No incoming links`.
7. Include `[Target](./target.md)` in the source fixture. Assert `md_links` returns the target and `md_backlinks` returns the source after the D resolver runs. This pins the Finding F conclusion without changing graph code.

### Architecture and gates

1. Update `src/mcp/generation-session.test.ts` so all six generation reading MCP handlers acquire one current generation session. `md_index` remains the writer.
2. Add a source architecture assertion that the four path handlers call the single MCP document resolver and contain no direct `path.resolve` or `resolveAndValidatePath` calls.
3. Run focused MCP path, generation session, canonical indexing, and indexer tests.
4. Run `pnpm typecheck`.
5. Run `pnpm build`.
6. Run the full `pnpm test` command to its final summary and record pass, skip, and failure counts.
7. Run the repository formatting and lint gate.

## Change boundary

Expected production owners:

1. One focused MCP path resolution module.
2. `src/mcp/handlers.ts` for the four call sites.
3. `src/index/link-index.ts` only if needed to make its indexed key lookup return a real miss instead of falling back to the candidate key.
4. Focused MCP tests and the generation session ownership assertion.

Keep `src/mcp/server.ts`, search engines, parser, link extraction, graph construction, CLI commands, and symlink behavior unchanged unless a failing test proves a narrower dependency.
