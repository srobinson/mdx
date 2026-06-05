# Wikilink scout and implementation plan

## Scope

Branch: `feat/wikilinks`

Base: `c4957198f2e69da3b007128f55be408190aa28d5`

This report covers the locked `[[wikilink]]` feature scope. No source code was
changed.

Root shape: extend the shared internal link resolver and give it a new corpus
basename index. Both Markdown links and wikilinks must enter one resolver and
one edge application path.

## 1. Reuse map

### Link extraction

`src/parser/parser.ts:extractLinks` at line 239 owns link extraction. Its single
AST walk tracks the current source section, recognizes Remark `link` nodes, and
adds images. Standard Markdown links become `MdLink` values at lines 248 to 257.

`src/core/types.ts:MdLink` at line 63 is the shared parser output. It currently
contains `type`, `href`, display text, source `sectionId`, and line number. It
does not distinguish Markdown syntax from wikilink lookup semantics, and it does
not carry a parsed target heading.

Remark parses all four required wikilink forms as `text` nodes. A probe against
the installed parser confirmed that `[[Note]]`, `[[Note|Alias]]`, and
`[[folder/Note#Heading]]` remain together in a text node. Inline code and fenced
code use other AST node types. The safe parser hook is therefore the existing
AST walk over text nodes, rather than a regular expression over the whole source
document.

### Current internal target resolution

`src/index/index-build.ts:resolveDocumentLinks` at line 103 is the only build
caller. It filters `document.links` to internal links, sends every target to
`resolveInternalLink`, then partitions results into resolved `DocumentKey`
values and broken `DeclaredPath` values.

`src/index/link-index.ts:resolveInternalLink` at line 30 is the current shared
resolver. It:

1. Resolves a local fragment to the source document.
2. Ignores HTTP and HTTPS targets.
3. Removes a fragment from a file target.
4. Resolves the remaining path relative to the source file.
5. Rejects targets outside every corpus root.
6. Canonicalizes the declared target and selects its indexed `DocumentKey`.
7. Returns the absolute lexical `DeclaredPath` when canonicalization or corpus
   selection fails.

`src/index/index-build.ts:parseFiles` at line 176 builds
`documentKeysByIdentity` from retained documents and current discovery. Its
`selectDocumentKey` callback at lines 122 to 124 prevents an existing file
outside the indexed corpus from becoming a resolved edge during a complete
build.

### Edge and backlink construction

`src/index/index-state.ts:applyDocument` at line 175 owns graph mutation. It
removes the source document's prior forward edges, writes document and section
entries, adds the source to each target's backward list, replaces the source's
forward list, and updates `brokenBySource`.

`src/index/index-state.ts:saveIndexState` at line 228 derives the global broken
list and saves documents, sections, forward edges, backward edges, and broken
targets together.

`src/index/link-index.ts:loadLinksFor` at line 106 reads the same forward or
backward maps for CLI and MCP consumers. Wikilinks need no separate read path.

### Canonical identity and path helpers

The canonical identity owner is `src/db/canonical.ts`:

* `DocumentKey` at line 13 is the absolute canonical document identity.
* `DeclaredPath` at line 17 preserves the absolute lexical path used at the
  source boundary.
* `expandDeclaredPath` at line 73 normalizes a declared filesystem path.
* `canonicalizeSourceFile` at line 216 resolves a file to its canonical path,
  device and inode identity, and filesystem case policy.
* `fileIdentityKey` at line 243 supplies the identity map key.
* `selectCanonicalSource` at line 246 deduplicates aliases of one physical file
  and deterministically selects one `DocumentKey`.
* `isPathWithin` at line 276 owns safe root containment.
* `resolveSourceFile` at line 323 converts a `DocumentKey` back to a normalized
  filesystem path.

`src/search/path-matcher.ts:matchesDocumentPath` at line 395 is a search filter
for corpus relative glob matching. It does not resolve names and should remain
outside link indexing. The private `documentPaths` helper in that file confirms
that canonical aliases matter, but importing it would invert the index and
search layer boundary.

No basename to `DocumentKey` resolver exists. Build the new basename index next
to `resolveInternalLink` in `src/index/link-index.ts`, using document entries and
canonical discovery selections supplied by `index-build.ts`.

For every document identity, index the basename of each declared alias and each
canonical alias after removing a terminal `.md`, folded to lowercase. Deduplicate
candidates by `DocumentKey` so hardlink aliases do not create false ambiguity.
The index value must retain candidate paths for deterministic selection and
diagnostics.

### Single resolution path

Both syntaxes should normalize to one structured internal target before index
resolution:

* Standard Markdown supplies relative path lookup plus its optional heading.
* A wikilink containing a path separator supplies exact relative path lookup.
* A bare wikilink supplies corpus basename lookup.
* Alias text remains display text and never enters the resolution target.

Every normalized target then passes through the expanded
`resolveInternalLink`. Its result carries the target `DocumentKey`, an optional
target section id, or the existing broken `DeclaredPath`. `applyDocument`
consumes that one result model and constructs outgoing edges and backlinks once.

## 2. Parser and pipeline hook

Add a small text node extractor beside `extractLinks`. The existing AST visitor
should call it when `node.type === 'text'` and append returned values to the same
`links` array used by standard Markdown.

The extractor should:

1. Match complete `[[...]]` spans within the text node.
2. Split once on `|`; the left side is the target and the right side is display
   text.
3. Split the target once on `#`; the left side is the document target and the
   right side is the optional heading.
4. Classify a target containing `/` as exact relative path lookup. Wikilink `/`
   is portable text and should be converted at the filesystem boundary.
5. Classify every other nonempty document target as basename lookup.
6. Preserve the current source `sectionId` and calculate the match line from the
   text node position.
7. Ignore malformed or empty spans without disturbing standard Remark links.

Do not scan raw Markdown. That would index examples inside inline code, fenced
code, and other AST nodes that the Markdown parser already classifies correctly.

`resolveDocumentLinks` remains the only call site. It should pass each structured
target, regardless of syntax, to the same resolver. No wikilink specific edge
builder, backlink builder, or broken link collector should exist.

## 3. Resolution details

### Exact relative targets

For `[[folder/Note]]`, append `.md` when the portable target has no Markdown
extension, resolve from the source document directory, enforce the existing root
containment rule, canonicalize with `discovery.canonicalize`, and select through
the existing identity map. An explicit extension remains unchanged.

This is the same canonical classification used by a standard
`[Note](folder/Note.md)` link.

### Basename targets

For `[[Note]]`, fold `Note` to lowercase, remove a terminal `.md`, and read the
prepared corpus basename index. A single candidate resolves directly to its
canonical `DocumentKey`.

For multiple distinct candidates, sort by normalized corpus relative path
length, then by normalized path text, then by `DocumentKey`. Select the first.
This makes the shortest path policy deterministic even when equal length paths
exist. Record the source, original target, chosen key, and sorted candidates in
the existing nonfatal build diagnostics. There is no current durable ambiguity
schema or inspection API. If durable ambiguity inspection becomes a product
requirement, add it to `LinkIndex` explicitly rather than hiding it in a second
resolver.

For no candidates, construct the source relative `.md` lexical path and return
the same `broken` result used by a missing standard link. `applyDocument` then
updates `brokenBySource` and the aggregate `broken` list without syntax specific
logic.

### Heading targets

The current resolver discards file fragments after document selection. The
current `LinkIndex` also stores only `DocumentKey` arrays. The locked section edge
requirement therefore needs a small target model change.

Resolve the document first. Then look up the lowercased heading within sections
whose `documentPath` equals the selected target key. When found, attach the
section id to the resolved edge. When absent, retain the resolved document edge
without a section id. A missing heading never turns an existing document into a
broken link.

Use the same heading step for standard `file.md#Heading` and wikilink
`[[Note#Heading]]` targets. This preserves the single resolver rule and improves
the existing standard fragment behavior at the same seam.

The persisted link target should become an object containing target
`documentPath` and optional target `sectionId`. Preserve the source `sectionId`
already present on `MdLink`. Forward and backward indexes should be derived from
the same resolved edge. Existing CLI and MCP link commands can project unique
document paths, while the stored graph retains section precision.

## 4. Build order and incremental correctness

Fresh builds currently parse and resolve one document inside the same concurrent
operation. During a fresh build, the target section index does not exist when a
source link resolves. Split this into two phases:

1. Parse changed or required documents.
2. Prepare one corpus resolver from retained state plus every parsed document,
   including basename candidates and document scoped heading candidates.
3. Resolve all internal links through that resolver.
4. Apply every parsed document through `applyDocument`.

This is required for a fresh source document to target a section in another
fresh source document independent of parse order.

Incremental indexing also needs explicit dependency repair:

* A changed target heading must re-resolve sources in its current backward list.
* Adding, deleting, or renaming a document can resolve a previously broken bare
  name or change the deterministic winner for an ambiguous name. Since the
  current index does not persist bare name dependencies, the minimal correct
  approach is to reparse all indexed sources on corpus membership changes.
* A later optimization may persist name dependencies and narrow that work. It
  should replace the full corpus fallback rather than create a parallel path.

The generation writer copies the current indexes into staging, and unchanged
files are skipped by content hash and mtime. The implementation must therefore
include a rebuild policy for the parser semantic change. With the locked no
migration constraint, a required one time forced rebuild or an intentional index
format reset is acceptable. Silent reuse of prefeature link data is not.

## 5. Minimal file design

1. `src/core/types.ts`
   Add the minimum discriminated internal target metadata needed to distinguish
   path and basename lookup and preserve an optional heading.
2. `src/parser/parser.ts`
   Extract wikilinks from text nodes into the existing `MdLink` collection.
3. `src/index/link-index.ts`
   Own basename index preparation, deterministic selection, shared path and
   basename resolution, heading attachment, and ambiguity results.
4. `src/index/index-build.ts`
   Wire the two phase parse and resolve flow, prepare one resolver per build, and
   feed results to `applyDocument`. Keep this wiring small.
5. `src/index/index-state.ts`, `src/index/types.ts`, and
   `src/index/storage.ts`
   Persist the optional section target and derive both graph directions from the
   same resolved edge. Keep broken links on their existing path.

`src/index/index-build.ts` is 651 lines. It has only 49 lines of headroom under
the hard 700 line limit. Move cohesive resolver preparation or parse phase logic
to a focused module before additions would cross the limit. `src/index/indexer.test.ts`
is 667 lines, so new integration coverage belongs in a new focused test file.

No new resolver belongs in `src/search/path-matcher.ts`. No parser side
filesystem lookup belongs in `parser.ts`.

## 6. TDD plan

### Parser tests in `src/parser/parser.test.ts`

1. `[[Note]]` produces one internal link with basename lookup, target `Note`,
   target display text, source section id, and line.
2. `[[Note|alias]]` preserves `alias` as display text while the resolution target
   remains `Note`.
3. `[[Note#Heading]]` preserves document target and heading separately.
4. `[[folder/Note]]` uses exact relative path lookup.
5. Several wikilinks in one text node are emitted in source order.
6. Wikilink shaped text inside inline and fenced code is ignored.
7. Standard Markdown, external links, and images retain their current parser
   results in a mixed document.

### Shared resolver tests in a focused `src/index/link-index.test.ts`

1. Exact relative Markdown and wikilink targets select the same canonical
   `DocumentKey`.
2. Bare basename lookup is case insensitive.
3. `.md` removal does not alter names containing dots.
4. Hardlink aliases collapse to one candidate.
5. Ambiguous basenames select the shortest normalized corpus relative path.
6. Equal length ambiguity uses the lexical tie breaker and emits one diagnostic
   containing the chosen key and all candidates.
7. An unresolved bare target returns the same broken result shape and lexical
   path policy as a missing standard link.
8. A matching target heading attaches its section id.
9. A missing target heading falls back to the resolved document edge.

### End to end tests in a new `src/index/wikilink-indexing.test.ts`

1. `[[Note]]` creates an outgoing edge from the source and a backlink on
   `Note.md`.
2. `[[Note|alias]]` creates the same graph edge as `[[Note]]`.
3. `[[Note#Heading]]` stores the target section id and remains visible through
   document level links and backlinks.
4. `[[folder/Note]]` resolves only the exact relative target.
5. An ambiguous basename chooses the shortest path and records the ambiguity.
6. An unresolved wikilink appears in `brokenBySource` and the aggregate broken
   list.
7. A mixed corpus containing `[Guide](guide.md)` and `[[Note]]` builds both
   through the same forward and backward maps.
8. Bidirectional mixed syntax links produce outgoing and incoming results in
   both directions without duplicate document results.
9. A fresh force build resolves a heading in a different file independent of
   discovery order.
10. An incremental target heading edit updates the stored section edge from an
    unchanged source.
11. Adding a matching basename converts an unresolved link to resolved.
12. Adding or removing a shorter ambiguous candidate updates the selected edge
    and both backlink directions.

### Gates

Run focused parser, resolver, storage, canonical indexing, and wikilink indexing
tests first. Then run typecheck, build, the full test suite, and the repository
format and lint gate. Confirm every modified source file remains below 700 lines
and each changed function remains near the 150 line limit.

## Recommendation

Proceed with a shared resolver plus a new basename index in `link-index.ts`.
Refactor parsing into a two phase parse and resolve flow, persist optional section
targets on the unified edge model, and keep document level CLI and MCP results as
a projection of those edges. This satisfies wikilink, standard link, broken link,
canonical identity, edge, and backlink behavior through one pipeline.
