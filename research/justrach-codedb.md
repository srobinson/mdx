---
title: justrach/codedb — Zig code-intelligence MCP server vs fmm
type: research
tags: [github-review, codedb, zig, code-navigation, mcp, trigram, fmm, borrow]
summary: 1.2k-star single-author Zig MCP server claiming "tree-sitter" but actually using line-prefix string matching for 11 languages; the parsers are weak vs fmm, but three primitives (reader.md, codedb_context, MCP error ergonomics) are genuinely worth borrowing.
status: active
source: github-researcher
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

**Stats:** justrach/codedb · Zig 0.15 · BSD-3 · 1,209 stars · 71 forks · 1 contributor (Rach Pradhan) · created 2026-03-03 · last push 2026-05-26 · ~12 weeks old · 46.7K Zig LOC (35.1K src + 11.6K tests in `tests.zig`) · 983 test declarations · zero external Zig dependencies · 11 hand-rolled line-prefix parsers + 14 "outline-only" lightweight languages · trigram + BM25-ready inverted word index · mmap-backed disk trigram, single-file portable `codedb.snapshot` (CDB\x01 magic, versioned section table) · 16 MCP tools · HTTP server on :7719 · polling watcher (2s, FilteredWalker) · auto-registration in Claude Code / Codex / Gemini / Cursor · codesigned + notarized macOS binaries · curl|bash installer · anonymous on-by-default telemetry to a paid SaaS (`api.wiki.codes`, ex-codegraff) for `codedb_remote`.

**Grade: B−.** Anchored next to claudex / metaharness / cozodb / revfactory-harness. The execution discipline is real (release cadence, codesigning, benchmark transparency, error ergonomics) and three primitives are worth lifting. But the substrate is dramatically weaker than fmm's: codedb does not use tree-sitter despite a README sentence claiming it does. All 11 "parsers" are `startsWith("pub fn ")` / `startsWith("def ")` line scanners that miss generics, multi-line decls, conditional compilation, attributes, `//` comments containing `def `, and anything that wraps. fmm's tree-sitter foundation is a different class of artifact. Project is also a single-author, 12-week-old hype cycle — survival risk is high.

## Executive summary

codedb is a Zig single-binary MCP server with strong **distribution and developer ergonomics** wrapped around a **structurally fragile parser layer**. The headline number ("538x faster than ripgrep") is a category error — it's comparing a warm in-memory index against ripgrep's cold filesystem walk, exactly the same trick that makes fmm's `fmm_*` calls fast. The interesting content lives elsewhere:

1. A single-file portable index format (`codedb.snapshot`, CDB\x01 magic) intended to be checked in or shipped alongside a repo.
2. A `codedb_context` composer tool that turns a natural-language task into one composite response (keywords + symbol-defs + ranked files + snippets) instead of forcing the agent to chain 3-5 search/word/symbol calls.
3. A `reader.md` primitive: agent-authored, blake2b-hash-verified codebase orientation file at `.codedb/reader.md`, auto-prepended to context responses, auto-invalidated when the load-bearing files drift.
4. MCP error ergonomics that name the bug back to the caller (`received keys: [...]`, `did you mean: <fuzzy paths>`, `--- partial ---` envelopes with `failed_at: N`).

Everything else codedb does — trigram index, inverted word index, reverse dep graph, structural outline, file watcher, version log, atomic edits, bundle/batching tool — fmm either already does, does better (tree-sitter), or doesn't need.

## Architecture

**Language & substrate.** Pure Zig 0.15+, zero external dependencies (no SQLite, no tree-sitter, no LSP, no SCIP, no embeddings, no vector store). Single binary. Single mutex inside `Explorer` guards all indexes. Threading: main + watcher + ISR (snapshot rebuild) + reap (stale agents) + per-connection HTTP threads (`docs/architecture.md` lines 90-110).

**Parser substrate is the critical finding.** Despite `README.md:356` advertising "codedb = tree-sitter + search index + dependency graph + agent runtime", `grep -rn 'tree-sitter\|tree_sitter' src/ build.zig*` returns **zero hits in source**. The 11 "parsers" (`parseZigLine`, `parsePythonLine`, `parseRustLine`, `parseGoLine`, `parseTsLine`, `parseDartLine`, …) are line-by-line `std.mem.startsWith` prefix matchers (`src/explore.zig:2466-3450`). Concrete consequences:

- Multi-line declarations are missed (`pub fn foo(\n    arg: T,\n) !void` only captures `pub fn foo`).
- Generics, attributes, `#[derive(...)]`, `@decorator`, conditional compilation `#ifdef`, are all string-matched at best.
- A comment line `// def evil` or `// pub fn fake` will register a fake symbol.
- TypeScript heuristic (`src/explore.zig:2592-2600`) uses `containsAny(line, &.{"function ", "const ", "let ", "var ", "class ", "interface ", "enum ", "type "})` — `const handler = useCallback(...)` becomes a "class_def" depending on which `indexOf` fires first.
- Imports for dep graph are extracted by the same line-prefix matchers, so the dep graph inherits the same fragility.

This is closer to ctags-with-language-aware-prefixes than to anything structural. fmm's tree-sitter index is a different category of artifact.

**Storage model.**
- In-memory `Explorer` holds `outlines`, `contents`, `dep_graph` (forward + reverse StringHashMap), `word_index`, `trigram_index` behind one mutex (`docs/architecture.md`, `src/explore.zig:120-260`).
- `WordIndex` (`src/index.zig:13-80`) tracks `word → [(doc_id, line_num)]` with per-file word ownership for incremental re-index. Tracks `doc_lengths` and `total_tokens` for BM25 ranking (currently scaffolded, not load-bearing in the search path).
- `TrigramIndex` (`src/index.zig:791-1180`) packs 3-byte sequences to `u24`, caps posting lists at 512 docs (`MAX_POSTINGS = 512`, line 808 — common trigrams are poor discriminators), and uses sorted-merge intersection of smallest-first posting lists (`src/index.zig:1140-1170`). For queries <3 chars it falls back to brute force.
- `MmapTrigramIndex` (`src/index.zig:1689+`) is a read-only disk layout for "warm restart" — index gets persisted to `~/.codedb/projects/<hash>/` after first build.
- `Store` (`src/store.zig`, ~217 lines) is an append-only monotonically-increasing-seq version log per file, capped at 100 versions per file, with `data.log` for diff persistence.

**Portable snapshot (`codedb.snapshot`).** Single-file binary, magic `"CDB\x01"`, format version 2, 52-byte header + section table + section payloads (`src/snapshot.zig:1-50`). Sections: TREE (JSON), OUTLINE (legacy JSON), CONTENT (binary path+content pairs), FREQ_TABLE (256×256×u16 trigram frequencies), META (JSON), OUTLINE_STATE (binary per-file outline for fast warm restore). Optionally pins to git HEAD SHA. This file is committed to the cloned repo (3.2 MB, `codedb.snapshot` at the root).

**File watcher.** Polling, not OS-level (`src/watcher.zig:1-100`). 2s interval. `FilteredWalker` prunes 37 junk dirs (`.git`, `node_modules`, `target`, `zig-cache`, `dist`, `build`, `.next`, `__pycache__`, `.venv`, …) before descending — this is the obvious correctness fix versus naive `std.fs.Dir.walk()`. Event ring buffer (`EventQueue`, capacity 4096) feeds the HTTP SSE endpoint.

**Multi-language strategy.** No unified AST. Per-language `parseXxxLine` functions branch off file extension. New language = new hand-rolled `parseXxxLine` function. The 14 "lightweight outline" languages (Java, Kotlin, Svelte, Vue, Astro, shell, CSS/SCSS, SQL, protobuf, Fortran, LLVM IR, MLIR, TableGen) appear to use an even simpler regex-style fallback.

**Incremental indexing.** Hash-and-mtime based. `incrementalDiff` (`docs/architecture.md`) compares filesystem vs cached `FileMap`. Single-file re-index claimed <2ms. No file-system inotify/fsevents — polling only.

**Agent surface.** 16 MCP tools (`src/mcp.zig:481-525`). Distinct from fmm's 9. The codedb set: `tree`, `outline`, `symbol`, `search`, `word`, `hot`, `deps`, `read`, `edit`, `changes`, `status`, `snapshot`, `bundle`, `remote`, `projects`, `index`, plus an undocumented `codedb_context` (`src/mcp.zig:498` enum entry but listed alongside others in the schema block at line 509). `read` and `edit` write to disk (atomic temp-file rename) — fmm explicitly does not.

**Test coverage.** `wc -l src/test_*.zig src/tests.zig src/adversarial_tests.zig` → 22.7K LOC of tests. `grep -c '^test '` across them: 983 test declarations. Tests cover parsing, search, query, mcp, snapshot, index, explorer, plus an `adversarial_tests.zig` (45 tests) that targets crash recovery and malformed input. Comparable to fmm's 907.

**CI.** `.github/workflows/` present (not inspected in depth). Release process: `release.sh` does build, codesign, notarize, GitHub Releases upload. Linux ARM/x86 unsigned; macOS ARM/x86 codesigned + notarized.

**Distribution.** `curl -fsSL https://codedb.codegraff.com/install.sh | bash` — fetches binary from GitHub Releases, auto-registers MCP server in Claude Code, Codex, Gemini CLI, Cursor. Auto-installs Claude Code hooks (recent commit). Self-update via `codedb update`. `codedb nuke` for clean uninstall.

## Primitives that transfer (numbered)

1. **`reader.md` — agent-authored, hash-verified codebase orientation file.**
   - Where in codedb: `src/reader_md.zig:1-114`, spec at `experiments/reader-md/SPEC.md`.
   - Shape: markdown file at `.codedb/reader.md` with YAML frontmatter naming `source_files: [...]` and `source_hash: blake2b:<hex>` computed over the *sorted source_files content* (not the whole repo). Body is ≤200 LOC plain markdown describing layout and load-bearing concepts.
   - Behavior: on `codedb_context`, codedb reads `.codedb/reader.md`, recomputes blake2b over the listed source_files, prepends body if hash matches, emits a "stale: regenerate" hint if drifted, silently skips if missing.
   - Why it transfers: fmm currently has nothing between "no orientation" and "agent does N exploratory `fmm_*` calls". This is the missing layer above `fmm_list_files(group_by: "subdir")`. The hash-over-load-bearing-files (not the whole repo) is the elegant move — orientation files for Helioy/littleorgans monorepo change less than the whole tree.
   - fmm landing target: a new `fmm_orientation` MCP tool that reads `.fmm/reader.md`, validates a hash over a small declared source-file set, returns body if fresh or a "regenerate with source_hash=<recomputed>" hint if stale. Pair with a `fmm orientation regenerate` CLI subcommand that lets an agent write a fresh file. Keep the load-bearing files list explicit and human-pickable; do not auto-detect.

2. **`codedb_context` — task-shaped composer that replaces 3-5 sequential calls.**
   - Where in codedb: `src/mcp.zig:1623-1710` (`handleContext`), tool schema at `src/mcp.zig:509`.
   - Shape: caller passes `task: "natural language description with maybeCamelCase and snake_case and \"quoted strings\""`. codedb extracts up to 5 candidate identifiers via casing heuristics (snake_case OR all-caps acronym 3-8 chars OR camelCase with internal lower→upper transition OR quoted string of 3-64 chars), filters out sentence-leading capital words like `Find` / `React` / `Want` (`src/mcp.zig:1636-1660`). Composes a single response: extracted keywords + symbol defs + ranked top-5 files + top-3 line snippets per file.
   - Why it transfers: this is a genuinely novel ergonomic for agent-first code nav. fmm has 9 narrow primitives, no composer. A first-touch composer that gives the agent everything-it-probably-needs in one round-trip is the right shape for cm/am-driven workflows where token budgets are tight.
   - fmm landing target: `fmm_context(task: string)` MCP tool. Re-use existing `fmm_search`, `fmm_lookup_export`, `fmm_glossary`, `fmm_file_outline` internally; the new code is the identifier-extraction heuristic and the result-merging shape. Steal the camelCase / snake_case / ALL_CAPS-acronym filter directly from `looksLikeContextIdentifier` (`src/mcp.zig:1640-1660`) — it's small, language-agnostic, and avoids the noise from English sentence-leading capitals.

3. **MCP error ergonomics: name-the-bug-back diagnostics.**
   - Where in codedb: `src/mcp.zig:2377-2440` (`appendBundleArgKeysDiagnostic`, `appendFuzzyPathSuggestions`, `finishQueryWithFailure`).
   - Three patterns:
     - On missing-arg error, append `received keys: [tool, arguments]` showing the caller exactly which keys their JSON payload actually contained, plus a hint when only administrative keys reached the handler (`hint: no sub-op args reached the handler — your client may be stripping fields. Try inline shape: ...`).
     - On unknown-path error, run `fuzzyFindFiles` and append `did you mean:\n  src/foo.zig\n  src/foo_test.zig`.
     - For multi-step pipelines, emit `--- partial ---\nfailed_at: 2\nreason: <text>` so the caller can read which step failed and reuse earlier output.
   - Why it transfers: fmm errors currently tell the agent what went wrong, not what to do next. Every error that ends in "did you mean X" or "received Y" saves a round-trip and a fmm_search call. This is the highest-leverage pattern in the whole repo — small implementation, large ergonomic win, sets fmm apart from every line-numbered "no results" tool.
   - fmm landing target: a `MCPError` helper in fmm's MCP layer that takes the original input + a context-specific suggestion source (fuzzy file list, fuzzy export list, did-you-mean dictionary) and emits one envelope. Apply across `fmm_file_outline` (fuzzy file), `fmm_lookup_export` (fuzzy export), `fmm_read_symbol` (fuzzy symbol). Add a `received keys: [...]` line to every "missing required arg" error. Cheap to ship; visible on every wrong call.

## Primitives that do NOT transfer (numbered)

1. **Portable single-file snapshot (`codedb.snapshot`).** fmm already has `./.fmm.db` (rusqlite) — same idea, better substrate. The advantage of single-file binary is shipping the index without the database; the disadvantage is reinventing a format. fmm's sqlite path is more queryable, more standard, more debuggable. Skip.

2. **Trigram index + sorted-merge intersection.** fmm's existing `fmm_search` (FTS5 / tantivy / sqlite — confirm in fmm) already covers fast substring lookup. codedb's trigram is well-implemented but not novel; the `MAX_POSTINGS = 512` cap is a nice hygiene detail to verify fmm has equivalent. Skip the substrate transfer; just confirm fmm's search caps common-token posting lists.

3. **Inverted word index (`WordIndex`).** Same — fmm symbol/export tables already do O(1) identifier lookup with proper tree-sitter structural typing. codedb's word index is doing what fmm's `fmm_lookup_export` does, only worse (no kind/visibility/parent).

4. **Reverse dependency graph (`getImportedBy`).** fmm has `fmm_dependency_graph` and `fmm_dependency_cycles`. The codedb implementation matches imports by basename (`src/explore.zig:282-310`) — basename match across files is exactly the false-positive trap fmm avoids by parsing imports structurally. Do not adopt.

5. **`codedb_edit` (atomic line-range edits).** fmm is explicitly read-only by design; Helioy edits flow through the agent harness, not the navigation layer. Out of scope.

6. **`codedb_bundle` (batch up to 20 ops in one round-trip).** Tempting, but the implementation reveals the cost: every sub-op needs special-case handling for recursion, write-op blocking, and the schema for bundle is harder to make discoverable. Better path for fmm: a smaller, *typed* `fmm_overview` that returns several precomputed cuts in one shot, rather than a general-purpose op batcher. Inspiration only; do not copy the generic shape.

7. **`codedb_remote` (query remote indexed repos via `api.wiki.codes`).** This is a SaaS lock-in proxy to a paid service. Helioy's posture is local-first laboratory. Skip outright.

8. **Line-prefix parsers across 11 languages.** This is the worst part of codedb. fmm's tree-sitter substrate is strictly better. Do not even look at the parser code as a reference, except to remind ourselves what the fmm investment buys us.

9. **Polling file watcher with 2s interval.** Polling is fine but Helioy already prefers fsevents/inotify on the platforms where it matters. The `FilteredWalker` directory-pruning lesson — prune ignored dirs *before descending* — is universal hygiene fmm presumably already follows; verify, but no transfer needed.

10. **HTTP server on :7719 + thread-per-connection.** fmm is MCP-only by design; an HTTP surface adds attack surface (auth-less localhost-only is a security smell) and parallel API to maintain. Skip.

11. **Agent registry with exclusive file locks + 30s heartbeat reaping.** Multi-agent locking via the navigation tool is the wrong layer. Helioy puts agent coordination on the bus (helioy-bus warroom presets, registered_agents) — the code-nav tool shouldn't know about agents at all.

12. **Curl|bash auto-registration installer.** Slick, but Helioy's installer story belongs to the helioy-plugins layer, not fmm itself. Reference for installer ergonomics if/when fmm ships standalone; not now.

13. **On-by-default telemetry to a third-party SaaS.** `~/.codedb/telemetry.ndjson` syncs to codedb analytics by default unless `CODEDB_NO_TELEMETRY=1`. For Helioy this is a non-starter; fmm should never default-on phone-home.

## Verdict: **inspiration-only, three specific borrows.**

Don't build with codedb. Don't fork it. Don't reuse its parsers — they're a downgrade from fmm's tree-sitter. The repo's value is three specific ergonomic patterns that fmm hasn't shipped yet: `reader.md`, `codedb_context`, and the error-diagnostics envelope. All three are small implementations with outsize agent-ergonomic returns. Estimated ~600 Rust LOC total to land all three behind a `fmm_context` MCP tool, a `fmm_orientation` MCP tool, and an `MCPError` helper used across existing tools.

## Why (deeper motivation)

codedb is what fmm looks like if you optimize for *adoption* over *correctness*: zero deps, single binary, curl|bash installer, signed macOS releases, MCP+HTTP+CLI surfaces, telemetry, hosted SaaS for remote repos, hand-rolled parsers that ship today rather than tree-sitter integration that takes a year. It got to 1,209 stars in 12 weeks because of distribution discipline, not technical depth. fmm has the technical depth (tree-sitter, 18 grammars, 907 tests, proper structural typing) but lacks the surface polish.

The three borrows are the cases where codedb's adoption-first posture produced a genuinely better agent UX, not just a smoother install. `reader.md` is a new idea about how agents orient themselves; it's not "just" a `CLAUDE.md` because it carries a hash-verification protocol that lets the index server enforce freshness. `codedb_context` collapses 3-5 sequential MCP calls into one, which matters disproportionately when each call costs a network round-trip in MCP framing. The error envelopes are pure agent ergonomics — "did you mean" and "received keys" are the difference between an agent giving up after one failed call and an agent self-correcting on the same turn.

Everything else codedb does, fmm either already does (search, symbol lookup, dep graph, outline) or shouldn't do (write edits, host HTTP, manage agents, phone home).

## How to apply (concrete next steps)

1. **fmm_context MCP tool.** Lift `looksLikeContextIdentifier` from `src/mcp.zig:1640-1660` directly (rewrite in Rust, ~25 LOC). Wire it to existing `fmm_lookup_export` + `fmm_search` + `fmm_file_outline`. Return shape: `{ keywords: [...], symbol_defs: [...], ranked_files: [...], snippets: [path:line text] }`. Cap at 5 keywords, 5 files, 3 snippets per file (same as codedb). Behind a feature flag for one release before promoting. Linear: scope as a self-contained sub-issue of the next fmm planning cycle.

2. **fmm_orientation MCP tool + `.fmm/reader.md` contract.** Adopt the codedb format more or less verbatim: frontmatter with `schema_version: 1`, `source_files: [...]`, `source_hash: "blake2b:<hex>"`, `loc_budget`, `loc_actual`. On read, recompute hash with the exact algorithm from `experiments/reader-md/SPEC.md` (`for f in sorted(source_files): h.update(f) + null + open(f).read() + null+null`). Three states: `ready` (prepend body), `stale` (emit regenerate hint with the recomputed hash), `missing` (silent). Pair with a `fmm orientation regenerate <files...>` CLI command that produces the frontmatter and lets an agent fill the body.

3. **MCPError helper across fmm.** Single Rust trait + impl that wraps every error-returning MCP path. Three diagnostic appenders: (a) `received keys: [...]` on missing-arg errors, (b) `did you mean: <fuzzy>` on unknown-path / unknown-symbol errors using existing fmm path and export tables, (c) `--- partial ---\nfailed_at: N\nreason: ...` envelope for any multi-step pipeline tool. Cost: ~150 Rust LOC. Touches every tool but invisibly — no behavior changes on success path.

4. **Verify fmm has trigram posting-list caps.** Read fmm's search backend; if a hot token like `self` or `the` doesn't have an analog to codedb's `MAX_POSTINGS = 512`, file a hygiene issue. Not a borrow — a verification.

5. **Do not** adopt codedb's parsers, file format, telemetry default, HTTP surface, agent registry, edit pipeline, or `codedb_remote` SaaS dependency.

## Dependencies (codedb's external deps)

None. Pure Zig 0.15+ std library. This is genuinely impressive for the surface area; it means cross-compile + codesign + ship works without a vendor tree. fmm depends on tree-sitter and rusqlite; we're not going to give those up for the wrong reasons.

## Relevance to Helioy

fmm is the canonical code-navigation organ in the Helioy stack. codedb sits in the same product category and made three ergonomic choices fmm has not. The three borrows above are net additions to fmm's surface, none of which conflict with its rusqlite + tree-sitter substrate.

Separately, codedb's distribution playbook (curl|bash installer that auto-registers across Claude Code / Codex / Gemini / Cursor, codesigned macOS binaries, GitHub Releases with checksums) is a useful template when Helioy ships its first user-facing binary, e.g. littleorgans. Filed under future reference, not a current todo.

## Sources consulted

- `README.md` (full, especially status table, MCP tools table, benchmarks, architecture diagram, telemetry section)
- `docs/architecture.md` (full)
- `docs/benchmarks.md` (lines 1-60)
- `experiments/reader-md/SPEC.md` (lines 1-80) and `src/reader_md.zig` (full, 114 LOC)
- `src/explore.zig` (lines 220-310 dep graph, 2398-2401 explorer wiring, 2466-3450 parsers — sampled Zig, Python, TypeScript, Go, Rust, Dart)
- `src/index.zig` (lines 1-80 word index, 791-1180 trigram, 1689+ mmap variant)
- `src/snapshot.zig` (lines 1-100 format header)
- `src/watcher.zig` (lines 1-100, ring buffer)
- `src/mcp.zig` (lines 481-525 tool enum + schemas, 1623-1715 codedb_context, 2377-2450 diagnostics, 2451-2530 bundle handler, 2763-2925 codedb_remote)
- `install/install.sh` (head)
- `benchmarks/v0.2.578-vs-v0.2.572.md` (methodology, hyperfine -N --warmup 5 -r 10)
- `git log --oneline -20`, `git log --reverse --format='%ad' --date=short | head -1`, `git log --format='%an <%ae>' | sort -u`
- `gh api repos/justrach/codedb` (stars, forks, dates)

## Open questions

- fmm's search backend posting-list cap behavior is not verified here; needs a read of fmm's search module to confirm hot-trigram hygiene exists.
- codedb's BM25 scaffolding (`doc_lengths`, `total_tokens` in `WordIndex`) suggests an upcoming ranking change; worth watching what they ship and whether the ranking is meaningful for agent UX.
- The auto-detection of "load-bearing files" for `reader.md` is left to the agent. Is there a recipe Helioy should ship (e.g. "top N by `fmm_glossary` use-site count" or "files with the most exported symbols")? Probably yes; defer to the fmm_orientation impl spike.
- codedb's claim "5,200 mixed files in 310 ms cold index" assumes the line-prefix parsers are correct; an adversarial test on a fmm-indexed corpus where line-prefix mis-fires would quantify the actual-correctness gap vs tree-sitter. Not necessary to do this work; flagged as the natural follow-up if anyone is tempted to take codedb's perf numbers at face value.
