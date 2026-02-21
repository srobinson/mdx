---
title: mdm vs context-mode (ELv2) retrieval primitives gap
type: research
tags: [mdm, markdown-matters, context-mode, fts5, rrf, fuzzy, retrieval, helioy]
summary: mdm has BM25 plus semantic with RRF in CLI but no SQLite/FTS5, no dual-tokenizer, no vocab-backed fuzzy correction, and md_search MCP is semantic-only.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

# mdm vs context-mode (ELv2) retrieval primitives gap

## Executive Summary

mdm does not run on SQLite. Its keyword index is `wink-bm25-text-search` persisted as JSON at `.mdm/bm25.json`, fronted by a single regex tokenizer. The claudex SQLite/FTS5 sidecar pattern referenced in the brief has *not* landed in mdm. RRF fusion already exists, but it fuses semantic embeddings with BM25 in the CLI surface only. The MCP `md_search` tool is wired straight to `semanticSearch` and never consults BM25 at all. Fuzzy matching exists as a per-line Levenshtein scan, with no vocabulary table behind it.

Both context-mode primitives therefore land on a substrate that does not yet exist. The dual-tokenizer + RRF + vocab-fuzzy primitive needs a SQLite/FTS5 substrate before any of the parts can be staged. The worktree-SHA primitive is not applicable today: mdm carries no per-session state.

## 1. Current mdm retrieval shape

### Storage substrate

Index storage is JSON files under `.mdm/`, atomically written via tmp+rename, mtime-cached in process.

- `src/index/storage.ts:240-274` writeJsonFile (atomic tmp+rename)
- `src/index/storage.ts:116-160` readJsonFileCached (mtime-keyed in-memory cache)
- `src/index/types.ts:140-151` getIndexPaths declares `documents.json`, `sections.json`, `links.json`, `cache/parsed/`. No `.db`.
- `src/index/storage.ts:38-82` schemas for DocumentIndex, SectionIndex, LinkIndex.

No SQLite anywhere in `src/`. Grep for `FTS5|sqlite|better-sqlite` returns zero source matches; the only hits are unrelated frontmatter test fixtures.

### Tokenizer and BM25

- `src/search/bm25-store.ts:53-58` `tokenize`: `text.toLowerCase().split(/\W+/).filter(t => t.length > 2)`. Single tokenizer, length>=3 filter, no stemming inside the index, no trigram pass.
- `src/search/bm25-store.ts:113-138` `createBM25Store` instantiates `wink-bm25-text-search`, weights heading=2 vs content=1, persists to `.mdm/bm25.json` and `.mdm/bm25.meta.json`.
- `package.json:73` declares `wink-bm25-text-search ^3.1.2`. The wink BM25 engine is in-process JS, not a SQLite virtual table.
- `src/index/indexer.ts:734,773-849` `buildBM25Index` reads section content, calls `bm25Store.add` and `consolidate`, then `save` to JSON.

### md_search query path

The MCP tool `md_search` is semantic-only. It does not call BM25 or RRF.

- `src/mcp/handlers.ts:47-86` `handleMdSearch` validates args then calls `semanticSearch(rootPath, query, {limit, threshold, pathPattern, providerConfig})`. There is no branch for keyword fallback, no fusion, no fuzzy.
- `src/mcp/handlers.ts:156-197` `handleMdKeywordSearch` (the `md_keyword_search` tool) calls `search(rootPath, options)` from `src/search/searcher.ts`, which is metadata-filter only (heading regex, path glob, hasCode/hasList/hasTable, level range). It does not consult the BM25 store.
- `src/search/searcher.ts:204-285` `search` iterates `sectionIndex.sections` in memory. BM25 is not invoked.

### RRF and fuzzy that already exist (but only in CLI)

- `src/search/hybrid-search.ts:119-234` `fusionRRF` combines `SemanticSearchResult[]` with `BM25SearchResult[]` using `score = weight / (k + rank)` per source, default `k=60`. This is a *cross-method* RRF (semantic vs keyword), not the *cross-tokenizer* RRF that the context-mode primitive describes.
- `src/search/hybrid-search.ts:255-407` `hybridSearch` is the orchestrator. Reachable from CLI at `src/cli/commands/search.ts:29,544`. Not reachable from MCP.
- `src/search/fuzzy-search.ts:47-91` Levenshtein-based `isFuzzyMatch`, no vocabulary. The fuzzy matcher iterates over the text words of every candidate section at query time, in `src/search/searcher.ts:184-231` (`findMatchesInLine`). No prefilter expansion. There is no `tokens` table to lookup against.
- `src/search/fuzzy-search.ts:9-37` Porter stemmer wrapper exists but is used only for highlight-pattern construction at query time, never to populate an index.
- `src/mcp/handlers.ts` does not pass `fuzzy` or `stem` to either `search` or `semanticSearch`. Fuzzy is a CLI flag, not an MCP capability.

### Worktree-scoped state

Grep for `worktree|sessionId|session_id` in `src/` returns zero matches. mdm is a stateless retrieval surface over a markdown root. No per-session db file, no per-worktree isolation problem to solve.

## 2. Gap per primitive

### Primitive 1: Dual-tokenizer FTS5 + RRF fusion + vocab-backed fuzzy correction

**Status: missing on a missing substrate.**

| Sub-component | mdm status | Evidence |
|---|---|---|
| SQLite/FTS5 sidecar (claudex pattern) | not landed | No `better-sqlite3` import, no `.db` file, no virtual table. `.mdm/bm25.json` is a JSON blob (`src/search/bm25-store.ts:115`). |
| Single tokenizer (porter or otherwise) | partial via wink | `src/search/bm25-store.ts:53-58`. Single regex split, no porter normalization in the index. |
| Second tokenizer (trigram) | missing | No trigram code path anywhere. |
| RRF fusion across two BM25 indices | missing | `fusionRRF` in `src/search/hybrid-search.ts:119-234` fuses semantic vs keyword, not tokenizer-A vs tokenizer-B. |
| Token vocabulary table | missing | No tokens table, no `getTokens`-style call site. Fuzzy search at `src/search/fuzzy-search.ts:96-105` iterates `words: readonly string[]` passed in by the caller. |
| Vocab-backed fuzzy correction | missing | Levenshtein is applied per-line at query time (`src/search/searcher.ts` content-search loop), never against a precomputed vocabulary. |

**What would change.** The core change is substrate: introduce a SQLite/FTS5 sidecar at `.mdm/search.db`. On that substrate, add two FTS5 virtual tables (porter and trigram) populated from the same section corpus that `buildBM25Index` already produces. Add a `tokens(token, df, postings_count)` table populated as a side effect of indexing. Reroute `bm25Search` from the wink JSON engine to FTS5 BM25. Extend `fusionRRF` to accept N rank lists rather than two named lists, and call it with porter+trigram results inside the keyword path. Add a `correctTokens(query)` helper that hits the `tokens` table and applies a Levenshtein/edit-distance prefilter; expose it as a flag on `hybridSearch`. Wire `hybridSearch` into `handleMdSearch` so MCP gets the same retrieval as CLI.

### Primitive 2: Worktree-aware session isolation via SHA suffix

**Status: not applicable today.**

mdm has no per-session or per-worktree state. The `.mdm/` directory is colocated with the markdown root, indexed once per root (`src/index/types.ts:140`). Two worktrees of the same repo would each carry their own `.mdm/` and never collide. There is no shared sqlite file at the user level, so the SHA-suffix collision the context-mode primitive solves does not occur here.

The primitive becomes relevant only if mdm grows session-scoped state, for example a per-conversation working set or query history that lives in `~/.mdm/sessions/`. Note for the future: when that happens, name session db files with a 7-char SHA of the worktree path so parallel agents do not stomp.

## 3. Adoption order

Hard dependency chain inside primitive 1:

1. SQLite/FTS5 sidecar substrate (claudex pattern: WAL, busy_timeout, column-name escape) lands first. Without it, none of the rest has a home.
2. Migrate `bm25Search` from wink JSON to FTS5 BM25 over the porter-tokenizer table. `wink-bm25-text-search` and `stemmer` deps come out at this step.
3. Add the trigram virtual table alongside porter. Index-time only; no query change yet.
4. Generalize `fusionRRF` to accept N rank lists. Call it with porter+trigram inside the keyword branch of `hybridSearch`. RRF across tokenizers begins working at this step.
5. Add `tokens(token, df)` materialization during index build. Add a `correctTokens` query-time helper. Surface as a `fuzzy: true` option on `hybridSearch`.
6. Wire `hybridSearch` into `handleMdSearch` (`src/mcp/handlers.ts:47-86`). Decide what to do with `md_keyword_search` (deprecate, or rename to `md_metadata_search` since that is what it actually does).

Steps 2 and 3 can be parallelized after step 1; step 4 needs both. Step 5 needs the substrate but is otherwise independent. Step 6 should land last so MCP behavior changes only once.

Primitive 2 has no dependency on primitive 1 and no relevance until session-scoped state appears.

## 4. Verdict per primitive

- **Dual-tokenizer FTS5 + RRF + vocab fuzzy: adopt-now, but as a full retrieval-substrate migration, not a bolt-on.** The win is real (English-prose recall + partial-token tolerance + typo robustness on a knowledge base whose users do not know exact tokens), and current mdm carries an inconsistency worth fixing in the same pass: MCP `md_search` is semantic-only while CLI `mdm search` already uses RRF. Doing the substrate swap and the MCP wire-up together is one coherent change.
- **Worktree-SHA session isolation: skip until needed.** No collision surface today. Park as a one-line note in whichever module first introduces session state.

## 5. Concrete next steps

Files to touch first, in order:

1. New: `src/search/sqlite-store.ts`. Owns the connection, applies WAL + `busy_timeout=5000`, escapes column names, exposes `openDb`, `migrate`, `close`. Mirror the claudex pattern in shape, reimplement in TS over `better-sqlite3`.
2. New: `src/search/fts-schema.ts`. Declares the migration: `documents`, `sections`, `sections_porter` (FTS5 virtual table, `tokenize='porter unicode61'`), `sections_trigram` (FTS5 virtual table, `tokenize='trigram'`), `tokens(token TEXT PRIMARY KEY, df INTEGER)`. Triggers populate vocab on insert/delete.
3. Replace: `src/search/bm25-store.ts`. Same exported surface (`bm25Search`, `bm25IndexExists`, `createBM25Store`) but backed by SQLite. Keep the names so `hybrid-search.ts` and `indexer.ts` do not change.
4. Edit: `src/index/indexer.ts:730-849`. `buildBM25Index` writes to SQLite instead of `.mdm/bm25.json`. Drop the wink import.
5. Edit: `src/search/hybrid-search.ts:119-234`. Generalize `fusionRRF` to take `RankedList[]` instead of two named arguments. Call it once with `[porterResults, trigramResults]` for the keyword branch and once with `[keywordFused, semanticResults]` for the cross-method outer fuse, or collapse to a single N-way call.
6. New: `src/search/token-correction.ts`. `correctTokens(db, query, {maxDistance})` reads the `tokens` table, returns expansion suggestions; called inside `hybridSearch` when `options.fuzzy` is set.
7. Edit: `src/mcp/handlers.ts:47-86`. Replace `semanticSearch` with `hybridSearch`. Surface a `mode` arg on `MdSearchArgs` so callers can pin to `keyword`/`semantic` if they want. Remove or rename `md_keyword_search` since it is metadata-only.
8. Drop: `wink-bm25-text-search`, `stemmer` from `package.json:69,73` once step 4 lands. Add `better-sqlite3`.

Schema migration shape (single migration, version 2):

```
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;

CREATE TABLE sections (
  id TEXT PRIMARY KEY,
  document_path TEXT NOT NULL,
  heading TEXT NOT NULL,
  content TEXT NOT NULL
);

CREATE VIRTUAL TABLE sections_porter USING fts5(
  heading, content,
  content='sections', content_rowid='rowid',
  tokenize='porter unicode61'
);

CREATE VIRTUAL TABLE sections_trigram USING fts5(
  heading, content,
  content='sections', content_rowid='rowid',
  tokenize='trigram'
);

CREATE TABLE tokens (token TEXT PRIMARY KEY, df INTEGER NOT NULL);

-- Triggers keep FTS tables and tokens in sync with sections.
```

Test surface:

- `src/search/__tests__/sqlite-store.test.ts`: WAL set, busy_timeout honored, column escape round-trips a heading containing a backtick.
- `src/search/__tests__/dual-tokenizer.test.ts`: same query against porter and trigram produces *different* rankings on a fixture where one beats the other (proves both indices are live).
- `src/search/__tests__/rrf-nway.test.ts`: N-way RRF with `[porter, trigram]` matches the existing 2-way result for `[semantic, keyword]` when reduced.
- `src/search/__tests__/token-correction.test.ts`: `correctTokens('autorgressive')` returns `['autoregressive']` from a fixture vocab.
- Reuse `src/search/__tests__/hybrid-search.test.ts` as a regression suite. The existing 30+ cases should pass unchanged after the swap; that is the migration's truth condition.

## 6. License note

context-mode is ELv2. No code may be lifted. Reimplementation in TypeScript over `better-sqlite3` is the path. Schema strings, RRF math, and the dual-tokenizer idea are not copyrightable; the implementation must be ours.

Single-line provenance comment to place at the top of `src/search/sqlite-store.ts` and `src/search/fts-schema.ts`:

```
// Pattern reference: mksglu/context-mode (ELv2). Reimplemented; no code lifted.
```

That is the entire license-hygiene story for this change.

## Open Questions

- Does the wink BM25 index hit a corpus size that justifies the migration today, or is the trigger volume-driven? Worth a quick measurement on `~/.mdx` (largest mdm-indexed root) before scheduling the work.
- Should `md_keyword_search` be deleted or kept as `md_metadata_filter` once the new MCP `md_search` is hybrid? The two tools collapse semantically once `md_search` actually does keyword retrieval.
- The `.mdm/` directory currently colocates with the markdown root. SQLite WAL adds two sidecar files (`.db-wal`, `.db-shm`) that need `.gitignore` coverage in every consumer repo. Worth a one-line note in `BACKLOG.md` when this lands.
