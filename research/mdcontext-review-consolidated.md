# mdcontext: Consolidated Review

**Date:** 2026-03-13
**Agents:** Architecture, TypeScript, Search/Embeddings, CLI, Security, Performance

---

## Overall Assessment

mdcontext has strong fundamentals: Effect-TS is integrated thoroughly, the error taxonomy is production-grade, config has a mature precedence chain, and strict TypeScript is enforced end-to-end. The codebase is clean and well-organized. The issues below are fixable without architectural surgery.

---

## Critical Bugs (Fix Now)

| # | Issue | Location |
|---|-------|----------|
| C1 | **MCP path traversal** — all 5 path-accepting MCP handlers accept arbitrary absolute paths and `../` sequences. Any connected AI agent can read `/etc/passwd` or `~/.ssh/id_rsa`. | `src/mcp/server.ts:271-501` |
| C2 | **ReDoS** — `new RegExp(userInput)` in search and MCP `md_keyword_search`. Catastrophic backtracking patterns freeze the Node.js event loop. | `src/search/searcher.ts:132,257,270` |
| C3 | **`DimensionMismatchError` not in `createErrorHandler`** — falls through to generic handler. Named errors exist but are never matched. | `src/cli/error-handler.ts:507-526` |
| C4 | **9 search flags missing from argv preprocessor** — `--rerank`, `--quality`, `--hyde`, `--rerank-init`, `--timeout`, `--summarize`, `--yes`, `--stream`, `--auto-index-threshold` are rejected before Effect CLI sees them. | `src/cli/flag-schemas.ts:135-206` |
| C5 | **No in-process index cache** — every search parses `documents.json` + `sections.json` from disk. At 50k sections: 200-400ms added to every request. | `src/index/storage.ts`, `src/search/searcher.ts` |
| C6 | **HNSW store reloaded on every semantic search** — ~300MB binary read per call on large corpora. | `src/embeddings/semantic-search.ts` |

---

## High Priority

| # | Issue | Location |
|---|-------|----------|
| H1 | **400 lines of near-identical code** — `semanticSearch` and `semanticSearchWithStats` implement the same 14-step pipeline diverging only at one point. | `src/embeddings/semantic-search.ts:691,897` |
| H2 | **`SummarizationError` breaks the Effect error contract** — extends plain `Error`, no `_tag` discriminant, absent from `MdContextError` union. Cannot be caught by `Match.exhaustive`. | `src/summarization/types.ts:164-174` |
| H3 | **MCP server bypasses config entirely** — hardcodes default provider, reads no config file or env vars, ignores the precedence chain the CLI uses. | `src/mcp/server.ts` |
| H4 | **Sequential file I/O in `buildIndex`** — one file at a time. Parallelizing to 50 concurrent I/O ops cuts 10k-file indexing time 10-20x. | `src/index/indexer.ts` |
| H5 | **No incremental embedding updates** — `buildEmbeddings` is all-or-nothing. Adding 100 files to a 10k corpus re-embeds everything. | `src/embeddings/` |
| H6 | **No retry/backoff on API rate limits** — a transient 429 destroys the entire embedding build. | `src/embeddings/openai-provider.ts` |
| H7 | **MCP unsafe input coercions** — every handler casts `args.query as string`, `args.limit as number` with no validation. Effect Schema would eliminate all casts. | `src/mcp/server.ts` |
| H8 | **Dynamic `import()` of config files walks to filesystem root** — a malicious `mdcontext.config.js` in any parent directory executes arbitrary code. | `src/config/file-provider.ts:136-137` |
| H9 | **`duplicates` command undiscoverable** — missing from help registry; `mdcontext duplicates --help` exits 1. | `src/cli/help.ts:24` |

---

## Medium Priority

| # | Issue | Location |
|---|-------|----------|
| M1 | **Glob-to-regex incomplete escaping** — only `*` and `?` replaced; `.`, `+`, `(` etc. unescaped. `docs/v2.0/*.md` matches `docs/v2X0/file.md`. | `src/embeddings/semantic-search.ts:179,385,820,1026` |
| M2 | **Dual `ParseError` declaration** — plain interface in `src/core/types.ts` and Effect TaggedError in `src/errors/index.ts`, both with `_tag: 'ParseError'`. | `src/core/types.ts:93`, `src/errors/index.ts:199` |
| M3 | **`EmbeddingProvider` naming collision** — config schema type (string union) and embeddings interface (runtime contract) share the same name, forcing rename imports. | `src/config/schema.ts`, `src/embeddings/types.ts` |
| M4 | **Business logic in `types.ts`** — ranking boost functions and query preprocessing in `src/embeddings/types.ts:196-307` are algorithms, not type definitions. | `src/embeddings/types.ts` |
| M5 | **`VectorStore` interface too narrow** — callers cast to `HnswVectorStore` to access `setProvider`/`addCost`/`getStats`. Interface needs extending or factory should return concrete type. | `src/embeddings/semantic-search.ts:347` |
| M6 | **`ContextLine` defined identically in 3 files** — canonical definition belongs in `src/core/types.ts`. | `src/embeddings/types.ts:319`, `src/search/searcher.ts:82`, `src/search/hybrid-search.ts` |
| M7 | **Section ID collision in parser** — `${docId}-${slugify(heading)}` produces identical IDs for headings that differ only in punctuation. Second section silently overwrites first. | `src/parser/parser.ts:157` |
| M8 | **No TTY check before interactive prompts** — `readline` prompts in `index-cmd.ts` and `search.ts` block indefinitely in CI/piped contexts. | `src/cli/index-cmd.ts:30-41`, `src/cli/search.ts:144-155` |
| M9 | **ANSI codes emitted unconditionally** — `\x1b[2K\r` written to stdout regardless of TTY. Appears as garbage in piped output. `output.color` config value exists but is never read. | `src/cli/index-cmd.ts:185,319`, `src/cli/search.ts:344` |
| M10 | **API key exposure in debug mode** — `JSON.stringify(error, null, 2)` could serialize HTTP request context including keys. | `src/cli/error-handler.ts:465` |
| M11 | **File watcher re-indexes full corpus on any change** — should pass changed paths through to `buildIndex`. | `src/index/watcher.ts` |
| M12 | **Sequential batch processing** — no controlled concurrency for local providers where network is not the bottleneck. | `src/embeddings/batching.ts` |
| M13 | **BM25 store reloaded from disk on every call** — no module-level cache. | `src/search/` |
| M14 | **`src/summarize/` vs `src/summarization/`** — confusingly similar names for distinct purposes (extractive compression vs AI-powered summarization). | `src/summarize/`, `src/summarization/` |
| M15 | **MCP error handling flattens typed errors to strings** — `DimensionMismatchError`, `EmbeddingsNotFoundError` etc. become `[{ error: string }]`. AI agents cannot take structured corrective action. | `src/mcp/server.ts:239-244` |

---

## Low Priority / Quick Wins

| # | Issue | Fix |
|---|-------|-----|
| L1 | `brokenLinks: string[]` linear scan | Replace with `Set<string>`, one line |
| L2 | `JSON.stringify(data, null, 2)` in `writeJsonFile` | Remove pretty-print, cuts index size ~35% |
| L3 | Two independent Levenshtein implementations | Consolidate to one utility |
| L4 | `--refine` flag absent from help OPTIONS table | Add to `src/cli/help.ts:117-192` |
| L5 | `--threshold` accepts out-of-range floats | Add bounds check |
| L6 | Hardcoded 120-char line clear | Use `process.stdout.columns` |
| L7 | `countTokensApprox` runs 8+ regex passes | Single-pass approach, 5-10x speedup |
| L8 | `SectionEntry.level: number` should be `HeadingLevel` (1-6) | One-line type fix |
| L9 | `RawSection.contentNodes: unknown[]` causes 4 downstream casts | Type as `RootContent[]` from `@types/mdast` |
| L10 | SHA-256 truncated to 64 bits for change detection | Document intentionally or extend to 96 bits |
| L11 | No shell completion support | `@effect/cli` built-in was disabled |

---

## Zero Test Coverage (Critical Gaps)

- `src/mcp/server.ts` — no test file at all
- `src/index/indexer.ts` — no tests
- `src/index/storage.ts` — no tests
- `src/index/watcher.ts` — no tests
- `src/embeddings/vector-store.ts` — no tests

---

## Three-Day Quick Wins (High ROI, Low Risk)

1. **Fix MCP path traversal** (SEC-02): add `if (!resolved.startsWith(rootPath)) throw` after `path.resolve`. The pattern already exists at `src/index/indexer.ts:175`.
2. **Module-level HNSW singleton + index JSON cache**: eliminates the two biggest search latency regressions with ~30 lines.
3. **Add missing 9 flags to `flag-schemas.ts`**: unblocks broken search flags with zero logic changes.

---

## Strengths to Preserve

- Effect-TS throughout with `Data.TaggedError` and `Match.exhaustive`
- Config precedence chain with `ConfigService` layers
- `Redacted<string>` for API keys, only unwrapped at HTTP boundary
- `spawn()` with argument arrays in `src/summarization/cli-providers/claude.ts`
- Clean unidirectional dependency graph, no circular imports
- Strict TypeScript (`exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`)
- Typed error taxonomy with provider-specific messages (Ollama daemon suggestions, etc.)
- Typo suggester with Levenshtein + prefix-match preference

---

## Individual Reports

- `~/.mdx/research/mdcontext-architecture-review.md`
- `~/.mdx/research/mdcontext-typescript-review.md`
- `~/.mdx/research/mdcontext-search-embeddings-review.md`
- `~/.mdx/research/mdcontext-cli-review.md`
- `~/.mdx/research/mdcontext-security-qa-review.md`
- `~/.mdx/research/mdcontext-performance-review.md`
