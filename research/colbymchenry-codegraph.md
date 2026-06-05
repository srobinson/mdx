---
title: "colbymchenry/codegraph — review through the fmm lens"
type: research
tags: [github-review, codegraph, fmm, code-navigation, knowledge-graph, call-graph, mcp, tree-sitter, node-sqlite, agent-ergonomics, dynamic-dispatch]
summary: "Pre-indexed code knowledge graph (node+edge SQLite, WASM tree-sitter, call-graph + framework-aware resolution) shipping as MCP for coding agents; closer to fmm than any prior review. Grade B+/A−; borrow several call-graph and agent-ergonomics primitives."
status: active
source: github-researcher
confidence: high
created: 2026-06-02
updated: 2026-06-02
---

# colbymchenry/codegraph — what can fmm learn or leverage?

Source: https://github.com/colbymchenry/codegraph · Site: https://colbymchenry.github.io/codegraph/
Artifact written: `~/.mdx/research/colbymchenry-codegraph.md`
Reviewed at: v0.9.8 (HEAD `docs(changelog): promote [Unreleased] into [0.9.8]`, 2026-06-01)

## 1. Stats

TypeScript (2.2 MB, 96% of code) on Node ≥20 <25, MIT, ~42k LOC across `src/`. First commit 2026-01-18 (gh `createdAt`), so under five months old. **37,513 stars and 2,325 forks** against a single dominant author (Colby McHenry, 36 of ~50 visible commits; a long tail of one-off external contributors). That star count is wildly out of proportion to age, contributor count, and codebase size — a clear **popularity-vs-maturity mismatch driven by distribution, not engineering mass**: it markets directly at the coding-agent crowd ("Claude Code, Codex, Gemini, Cursor, OpenCode, AntiGravity, Kiro, Hermes — fewer tokens, fewer tool calls, 100% local") and rides the agent-tooling hype wave. That said, the *engineering* is unusually disciplined for its age: a real A/B benchmark matrix (`docs/benchmarks/`), per-language verification loop (`docs/SEARCH_QUALITY_LOOP.md`), design docs per subsystem (`docs/design/`), 55 test dirs, FTS5 sync triggers, migration table, and pragma/index commentary that reads like a staff engineer wrote it. CI is lean: `release.yml` (10 KB, npm publish flow) and `deploy-site.yml`; no broad test matrix in CI, tests run via vitest locally. License MIT, published as `@colbymchenry/codegraph`.

## 2. What it actually is

Not a "graph database" and not a generic code-search tool. It is a **pre-indexed code knowledge graph delivered as an MCP server for coding agents**, whose entire reason for existing is to cut an agent's read/grep tool-call count. Pipeline: **ingestion** (`web-tree-sitter` WASM grammars parse ~28 languages → `src/extraction/`) → **graph construction** (symbols become typed `nodes`, relationships become typed `edges`; a two-pass resolver in `src/resolution/` turns syntactic references into resolved `calls`/`imports`/`extends`/`implements` edges, with framework-specific resolvers for NestJS/React/Vue/Express/Rails/etc. and a heuristic callback/observer edge synthesizer for dynamic dispatch) → **storage** (single SQLite file via Node's built-in `node:sqlite`, no native addon; nodes + edges + FTS5 virtual table kept in sync by triggers) → **query surface** (10 MCP tools centered on call-graph traversal: `codegraph_search`, `codegraph_context`, `codegraph_callers`, `codegraph_callees`, `codegraph_impact`, `codegraph_node`, `codegraph_explore`, `codegraph_trace`, `codegraph_files`, `codegraph_status`). A chokidar file watcher + git-hook sync keeps the index incrementally fresh and marks stale results.

## 3. Grade

**B+ / A−** (sits between superpowers/Understand-Anything and notebooklm-py/mngr/fallow-rs). Justification: it does the one thing fmm doesn't — a *resolved call-graph with framework awareness and dynamic-dispatch synthesis* — and it backs the agent-ergonomics claims with an honest A/B benchmark harness; held just under A− only because it is single-author, hype-inflated, and architecturally heavier (WASM grammars, multi-thousand-line resolvers) than fmm's lean local-first SQLite core.

## 4. Primitives that transfer → fmm

1. **Typed node+edge graph with a `calls` edge kind (vs fmm's export/import model).** `src/types.ts:48-60` defines twelve `EdgeKind`s — `contains, calls, imports, exports, extends, implements, references, type_of, returns, instantiates, overrides, decorates` — over a single `edges(source, target, kind, metadata, line, col, provenance)` table (`src/db/schema.sql`). fmm today answers blast-radius via `fmm_glossary` (use-sites) and dependency via `fmm_dependency_graph` (import-level). This is the central lesson: **promote fmm's edge store from import-graph to a typed call-graph** so `fmm_glossary`/`fmm_dependency_graph` can answer "who *calls* this function" (not just "who imports this file"), and add a `calls`/`extends`/`implements` edge kind to the schema. This is the single highest-leverage borrow.

2. **Two-pass resolution via an `unresolved_refs` staging table + `provenance` column.** `src/db/schema.sql` has a dedicated `unresolved_refs` table (`from_node_id, reference_name, reference_kind, candidates JSON`) and `edges.provenance` (e.g. `'heuristic'`). Pass 1 extracts symbols + raw references per-file (embarrassingly parallel); pass 2 (`src/resolution/index.ts`) resolves names to node IDs after the whole graph exists, honoring imports, path aliases, go modules, JVM packages. **fmm lands this by adding an unresolved-reference staging step between extraction and the final edge write**, letting it resolve cross-file `calls` edges that a single-file tree-sitter pass cannot. The `provenance` column lets fmm tag low-confidence edges so `fmm_glossary` can rank exact resolutions above heuristics.

3. **Heuristic callback/observer edge synthesis for dynamic dispatch.** `src/resolution/callback-synthesizer.ts:1-55` synthesizes `calls` edges across observer/EventEmitter/JSX/Vue boundaries (`onUpdate(cb)`→dispatcher, `.emit('mount')`→handler, JSX `<Child/>`→component) — high-precision/low-recall, every synthesized edge tagged `provenance:'heuristic'`, capped by fan-out (`EVENT_FANOUT_CAP=6`). fmm's static call-graph will have the same dynamic-dispatch holes. **fmm lands this as an optional post-resolution pass** that adds heuristic edges visible to `fmm_glossary`/impact but distinguishable by provenance so users can trust-but-verify.

4. **Adaptive, project-size-scaled output budget for the agent-facing tool.** `src/mcp/tools.ts:86-200` (`getExploreBudget` + `getExploreOutputBudget`) scales `maxOutputChars`, `defaultMaxFiles`, `maxCharsPerFile`, and whether to include relationship/completeness meta-text across tiers (<150, <500, <5000, <15000, <25000+ files). The iteration comments cite real A/B results (excalidraw `App.tsx`, cobra `command_test.go`, OkHttp interceptor chain). fmm's `fmm_read_symbol`/`fmm_search` return fixed-shape output. **fmm lands this by sizing `fmm_read_symbol`/`fmm_glossary` response caps to indexed file count**, and by hard-excluding test/spec files from top-N relevance on tiny repos unless the query mentions tests (`excludeLowValueFiles`).

5. **Staleness banner on tool results instead of blocking on reindex.** `src/sync/watcher.ts:65,305,360-397` tracks per-file pending state and *marks results stale* rather than forcing the agent to wait for reindex — biased toward false-positive staleness ("shown stale, actually fresh → one extra Read") over false-negative ("shown fresh, actually stale → misleads agent"). fmm uses fingerprint-based incremental reindex but (per the brief) returns results without a freshness signal. **fmm lands this as a per-file dirty flag surfaced in every `fmm_*` response header**, so an agent editing live code knows when an answer predates its own edits.

6. **NL-query preprocessing before FTS (stop-words + stemming + prefix expansion).** `src/search/query-utils.ts:14-60` filters code-aware stop words (keeps `get/set/add/build/find/list`, drops `fix/bug/method/class`) and generates stem variants (`caching→cach/cache`, `eviction→evict`) used as FTS prefix matches; `src/context/index.ts` extracts likely symbol names from NL (CamelCase, snake_case, SCREAMING_SNAKE, dot.notation). fmm's `fmm_search` is structural. **fmm lands this as a query-normalization layer in `fmm_search`** so a natural-language phrase from an agent maps onto FTS5 symbol matches without the agent pre-tokenizing.

## 5. Does NOT transfer

1. **WASM tree-sitter (`web-tree-sitter` + `tree-sitter-wasms`).** codegraph ships WASM grammars to avoid native addons (`src/extraction/wasm/`). fmm already uses native tree-sitter and is Rust-based; WASM grammar loading is a workaround for shipping a bundled Node runtime, irrelevant to fmm's design.
2. **`node:sqlite` adapter shim (`src/db/sqlite-adapter.ts`).** A better-sqlite3-shaped wrapper over Node's built-in SQLite so they ship zero native deps with a bundled Node. fmm has its own (likely `rusqlite`) binding; this is a JS-ecosystem-specific dodge.
3. **Framework-specific resolvers (`src/resolution/frameworks/` — nestjs, drupal, fabric, react-native, swift, ruby, vue, …).** 15+ files, several 400-760 LOC, encoding per-framework dependency-injection and routing conventions. High maintenance surface, JS/web-framework-centric, and a poor fit for fmm's lean general-purpose model unless fmm deliberately targets web stacks.
4. **The multi-target installer + 8-agent fan-out (`src/installer/targets/`).** Claude/Codex/Gemini/Cursor/Hermes target adapters. This is distribution machinery; fmm has its own install story and Helioy already has installer lessons logged.
5. **The Astro marketing site (`site/`) and the hype-grade README copy ("94% fewer tool calls").** Calling-card material for codegraph's distribution, not fmm engineering.
6. **`codegraph_explore`/`codegraph_context` as monolithic "do-the-whole-flow" tools.** They bundle search + traversal + source assembly into one fat call. fmm's composable single-purpose tools (`lookup_export`, `read_symbol`, `glossary`) are the better contract; borrow the *budgeting* (4.4) without collapsing fmm's tools into a mega-tool.

## 6. Verdict

**Borrow** — specifically the typed call-graph edge model, two-pass resolution with provenance, and the staleness banner. Inspiration-only for dynamic-dispatch synthesis and adaptive budgets. Skip the WASM/installer/framework-resolver/site mass.

## 7. Why

This repo puts one sharp design pressure on fmm: **fmm indexes *structure* (exports, imports, file topology); codegraph indexes *behavior* (who calls whom, across dynamic-dispatch boundaries, with confidence provenance).** For an agent answering "what breaks if I change this function," an import-graph gives the file-level blast radius; a resolved call-graph gives the *function-level* answer in one hop. codegraph proves, with an honest A/B harness, that the call-graph is what collapses an agent's read/grep spiral (159→38 reads across 37 cells). fmm's fingerprint-incremental SQLite core is the right substrate; the gap is that fmm stops at the import edge where codegraph pushes through to the call edge. The cost of closing that gap is a two-pass resolver and a per-symbol reference-resolution step — exactly the architecture codegraph documents.

## 8. How to apply

1. **Schema:** add `calls` (and `extends`/`implements`/`overrides`) to fmm's edge-kind enum and a `provenance` column to fmm's edge table. Mirror codegraph's `edges(source, target, kind, line, col, provenance)` shape.
2. **Resolver:** insert an `unresolved_refs` staging step between fmm's tree-sitter extraction and final edge write. Pass 1 emits raw references per file; pass 2 resolves names → symbol IDs across the whole index. Reuse fmm's existing import resolution as the first resolution strategy.
3. **Glossary/impact:** extend `fmm_glossary` to walk `calls` edges (transitive callers/callees with a depth cap) so blast-radius answers at function granularity, not file granularity. This is the analog of `codegraph_callers`/`codegraph_callees`/`codegraph_impact` folded into fmm's existing tool rather than new tools.
4. **Freshness:** add a per-file dirty flag to fmm's fingerprint table and surface a one-line staleness header in every `fmm_*` MCP response, biased to false-positive (matches codegraph `src/sync/watcher.ts` rationale).
5. **Search:** add a query-normalization layer (stop-words + stemming + FTS prefix expansion) in front of `fmm_search`'s FTS5 query so NL phrases from agents resolve to symbol matches. Port `src/search/query-utils.ts` STOP_WORDS/`getStemVariants` semantics, not the TS code.
6. **Defer (inspiration-only):** the heuristic callback synthesizer and adaptive output budget — adopt only after the call-graph edge ships and fmm has a benchmark to prove the budget tuning the way codegraph's `docs/benchmarks/codegraph-ab-matrix.md` does.

## Sources consulted

`src/db/schema.sql`, `src/types.ts`, `src/db/sqlite-adapter.ts`, `src/resolution/index.ts`, `src/resolution/callback-synthesizer.ts`, `src/graph/traversal.ts`, `src/mcp/tools.ts` (tool list + `getExploreBudget`/`getExploreOutputBudget`), `src/search/query-utils.ts`, `src/context/index.ts`, `src/sync/watcher.ts`, `docs/benchmarks/codegraph-ab-matrix.md`, `docs/SEARCH_QUALITY_LOOP.md`, `package.json`, gh repo metadata.

## Open questions

- Resolution accuracy/recall: the design docs claim high-precision call edges, but I did not run the eval harness against a known repo to measure false-edge rate. Worth a one-shot `npm run eval` before fmm copies the heuristic synthesizer.
- How codegraph handles cross-language call edges (e.g. TS→WASM, iOS↔React-Native bridge) — `mixed-ios-and-react-native-bridging.md` exists but I did not read the implementation. Likely irrelevant to fmm v1.
