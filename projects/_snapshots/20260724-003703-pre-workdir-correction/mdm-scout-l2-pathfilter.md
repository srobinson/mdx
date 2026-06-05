# L2 path_filter reuse map

Date: 2026-07-21

Repository: `/Users/alphab/Dev/LLM/DEV/helioy/markdown-matters`

Observed branch: `fix/mcp-path-tool-root-resolution`

Scope: read only scout for the path_filter half of path/root contract
coherence. No repository source was changed.

## Result

`matchesDocumentPath` has seven production call sites.

- USER FACING, migrate: 5
- INTERNAL exclusion and cost, preserve source relative behavior: 2

The central problem is at `src/search/path-matcher.ts:57-68`.
`matchesDocumentPath` converts each canonical `DocumentKey` back to a path
relative to one `sourceRoot`, then matches the raw user pattern. This loses the
canonical absolute coordinate, assumes one root, and prevents a path emitted by
`md_search` from being reused verbatim as `path_filter`.

The clean boundary is to normalize a user filter once, before a result loop,
then compare canonical `DocumentKey` values synchronously. The two internal
exclude paths retain an explicitly named source relative matcher. Async
realpath or index work must not run once per result.

## Call site split

| Category | Call site | Current producer | Required action |
|---|---|---|---|
| USER FACING | `src/duplicates/detector.ts:222-229` | CLI `duplicates --path` passes `DuplicateDetectionOptions.pathPattern` | Migrate to the prepared canonical user matcher. Normalize once before filtering sections. |
| USER FACING | `src/search/hybrid-search.ts:298-308` | Hybrid and keyword search `pathPattern`, including CLI search scope | Migrate the BM25 channel to the prepared canonical user matcher. Share one prepared filter with the semantic channel. |
| USER FACING | `src/search/content-search.ts:103-113` | Keyword heading search, including MCP `md_keyword_search.path_filter` | Migrate to the prepared canonical user matcher. |
| USER FACING | `src/search/content-search.ts:307-313` | Keyword content search and CLI keyword mode | Migrate to the same prepared canonical user matcher. |
| USER FACING | `src/embeddings/semantic-search-pipeline.ts:414-418` | Semantic search, including MCP `md_search.path_filter` | Migrate post processing to the prepared canonical user matcher. Normalize before the raw result loop. |
| INTERNAL | `src/embeddings/semantic-search-build.ts:180-190` | Embedding build `excludePatterns` | Leave behavior source relative. Bind it to an explicitly named internal matcher so future user contract changes cannot reach it. |
| INTERNAL | `src/embeddings/semantic-search-cost.ts:91-100` | Embedding cost `excludePatterns` | Leave behavior source relative and use the same explicit internal matcher as build. |

Count: **5 USER FACING / 2 INTERNAL**.

Upstream user entry points do not call `matchesDocumentPath` directly, but they
must pass the prepared canonical contract into the five sites:

- `src/mcp/handlers.ts:52-82`: `md_search.path_filter` enters semantic search.
- `src/mcp/handlers.ts:169-194`: `md_keyword_search.path_filter` enters keyword
  search.
- `src/cli/commands/search-mode.ts:397-453`: positional search `[path]` builds
  one scope and sends it through hybrid, keyword, content, and semantic modes.
- `src/cli/commands/duplicates.ts:95-119`: `duplicates --path` is another raw
  user pattern producer.
- `src/mcp/tools.ts:27-31,89-92`: live MCP descriptions still say only "Glob
  pattern" and must describe absolute canonical reuse plus relative
  compatibility.

## Canonical helper reuse

Reuse the existing symbols and their ownership chain:

1. `resolveCanonicalPathOrFallbackAsync`
   - Defined in `src/db/canonical.ts`.
   - Already wrapped by `resolveCanonicalSourceRoot` at
     `src/search/path-matcher.ts:15-16`.
   - Used by D at `src/mcp/path-resolution.ts:28` to produce canonical root
     aliases.
   - Use it once for every served root and for an existing literal directory
     prefix. Do not add another realpath fallback helper.

2. `canonicalizeSourceFile`
   - Defined at `src/db/canonical.ts:144-165`.
   - Produces the absolute realpath `DocumentKey`, declared path, file identity,
     and case behavior.
   - This is the canonical file identity owner. A new path_filter module should
     consume its result rather than recreate `realpath + stat + case` logic.

3. `resolveIndexedDocumentKey`
   - Defined at `src/index/link-index.ts:95-104`.
   - Calls `canonicalizeSourceFile` through `resolveDocumentKeyFromIndex` at
     lines 86-93 and maps symlink or hardlink aliases to the stored key.
   - Use it for an absolute exact file filter and any exact relative file
     candidate. This makes a copy pasted `md_search` path and a symlink alias
     converge on one key.

4. D corpus root expansion
   - `resolveMcpDocumentPath` is at `src/mcp/path-resolution.ts:46-68`.
   - Its private `candidatesWithinRoots` at lines 24-44 preserves both declared
     and canonical root aliases, validates containment, and deduplicates
     candidates.
   - L2 must factor the reusable root alias expansion out of D or call a shared
     exported seam. Copying this block into a filter module would violate the
     locked DRY constraint.

Recommended separation:

- Keep `matchPath` as the low level synchronous glob engine.
- Rename or wrap the current relative implementation as an INTERNAL source
  relative matcher used only by build and cost.
- Add one async user filter preparation boundary. It resolves manifest roots
  and exact aliases once, then returns a synchronous canonical matcher for the
  five hot loops.
- The prepared matcher compares canonical absolute `DocumentKey` values. Any
  separator conversion happens only inside the matcher text boundary. Stored
  and displayed paths stay native absolute `DocumentKey` values.

## User filter normalization rules

The prepared user matcher needs three explicit input classes:

1. Absolute exact path without glob characters
   - Resolve with `resolveIndexedDocumentKey`.
   - Match the resulting canonical key exactly.
   - A verbatim path emitted by `md_search` therefore round trips.

2. Relative glob or relative path containing separators
   - Expand against every canonical served root, preserving manifest order.
   - Existing examples such as `docs/*.md` and `docs/**/*.md` keep their glob
     meaning after expansion into the absolute coordinate.
   - Canonicalize an existing literal prefix with
     `resolveCanonicalPathOrFallbackAsync` so a symlinked directory does not
     fork the coordinate.

3. Bare string with no path separator and no glob character
   - Match case insensitively after a `/` or at the canonical path start.
   - Treat it as a segment anchored substring. For example, `docs` can match
     `/docs/guide.md` but must not match `/mydocs/guide.md`.

On Windows, the accepted and displayed coordinate remains the native absolute
`DocumentKey`. The matcher may normalize both sides to `/` internally only
after canonical resolution. It must not interpret backslashes from a copied
Windows path as glob escapes.

## The #71 positional search adapter

Current code at `src/cli/commands/search-mode.ts:397-412`:

- canonicalizes the requested directory into `requestedPath`;
- changes `sourceRoot` to the parent directory;
- emits the relative pattern `${basename}/**`;
- escapes only the basename with `escapePathPatternLiteral`.

That adapter depends on the old relative matcher. With a canonical matcher,
`${basename}/**` no longer carries enough identity and can collide with an
equal basename under another served root.

Required migration:

- Keep `requestedPath` as the already canonical absolute directory.
- Prepare one canonical subtree filter from `requestedPath`, equivalent to the
  canonical directory plus recursive descendants.
- Stop changing the matching coordinate to `path.dirname(requestedPath)`.
- Pass the same prepared filter through all four existing
  `pathScopeOptions(context.pathPattern)` channels.
- Preserve literal `*`, `?`, and backslash directory names by applying pattern
  escaping after canonical path resolution.
- Keep the no indexed path guidance keyed to the canonical `requestedPath`.

The end to end contract is pinned by
`src/cli/cli-read-surface.test.ts:128-298`. The static four channel guard is
`src/cli/generation-session.test.ts:40-45`.

## Existing tests that pin the old user contract

These user facing tests must be updated or extended. Relative forms should stay
green as compatibility cases, while their expectations become canonical:

- `src/search/path-matcher.test.ts:8-311`
  - Retain `matchPath` glob engine cases.
  - Add direct prepared canonical matcher cases for absolute DocumentKeys,
    relative glob expansion, case insensitive bare segment matching, symlink
    aliases, and Windows separator input.
- `src/embeddings/semantic-search-path-filter.test.ts:17-60`
  - Explicitly names and uses a source relative `docs/*.md` user filter.
- `src/search/__tests__/hybrid-search.test.ts:511-527`
  - Pins a database relative `docs/*.md` filter across hybrid results.
- `src/duplicates/detector.test.ts:194-239`
  - Pins `docs/*.md` for the user supplied duplicates path option.
- `src/search/searcher.test.ts:120-128,225-288`
  - Pins `doc1*` and `stem-test*` relative patterns.
- `src/integration/search-keyword.test.ts:139-181,410-529,610-650`
  - Repeats `authentication*`, `database*`, and `nonexistent*` across content
    search behavior.
- `tests/integration/search-context.test.ts:131-446`
  - Pins bare `example.md` and `multiline.md` filters. These need decoys to
    prove the new segment anchor rather than incidental substring matching.
- `src/cli/cli-read-surface.test.ts:128-298`
  - Pins the #71 positional path adapter for keyword, hybrid, no index
    guidance, empty directories, and literal glob metacharacters.
- `src/cli/generation-session.test.ts:40-45`
  - Pins delivery of one CLI scope to all four search channels.

The internal contract guards stay unchanged and should be named as deliberate
non migrations:

- `src/embeddings/semantic-search-build-path-filter.test.ts:90-122`
- `src/embeddings/semantic-search-cost.test.ts:17-55`
- `tests/integration/embed-index.test.ts:584`

## Shared acceptance suite extension

Extend `src/mcp/path-round-trip.acceptance.test.ts`. Do not create a second
multi root fixture.

Add these assertions to the existing `.mdx` plus repository roots and symlink
fixture:

1. Capture every canonical `DocumentKey` emitted by `md_search`.
2. Reuse each value verbatim as `path_filter` in `md_search` and
   `md_keyword_search`.
3. Assert both surfaces return only the same canonical document.
4. Repeat with `fixture.sourceAlias` and assert it converges on
   `fixture.source`.
5. Assert a relative `content/*.md` filter works against the second manifest
   root while the process CWD remains unrelated.
6. Add a bare mixed case segment and a prefix decoy. Prove matching is case
   insensitive and anchored after `/`.
7. Add a same basename document under the `.mdx` root to prove canonical root
   identity prevents cross root leakage.

Important test seam: the suite currently mocks `semanticSearch` at
`src/mcp/path-round-trip.acceptance.test.ts:23-30`, above the production path
filter at `semantic-search-pipeline.ts:414-418`. L2 must lower that mock or feed
the fixture results through the real `postProcessResults`. Reimplementing filter
logic inside the mock would allow a production regression to pass.

## Suggested L2 execution order

1. Split the current matcher into explicit user and internal contracts.
2. Prepare canonical user filters once from manifest roots and current read
   session, reusing D root expansion and index identity helpers.
3. Migrate the five USER FACING call sites.
4. Bind the two INTERNAL call sites to the preserved source relative matcher.
5. Migrate the #71 positional adapter to a canonical subtree filter.
6. Update MCP tool descriptions.
7. Extend the shared acceptance suite and the listed compatibility tests.
8. Run focused matcher, semantic, hybrid, keyword, duplicates, CLI, MCP, and
   internal exclusion suites before repository gates.
