---
title: fmm uplift brainstorm (Claude pane)
type: research
tags: [fmm, audit, llm-tools, perf]
summary: Audit of fmm 0.2.9 surface, indexed signal, and query ergonomics. Prioritized changes weighted by (impact × feasibility) / cost.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

# fmm uplift brainstorm

Exercised the MCP surface on fmm (399 files), context-matters (350), helioy-bus (36 Python), then validated each claim against `parser/types.rs`, `fmm-store/src/schema.rs`, and `format/yaml_formatters.rs`.

Headline gap: fmm tells an agent *where* a symbol is and *how big* it is, but rarely *what it is*. Outline is a table of contents with no chapter titles. Closing that gap is the highest-leverage class of change.

## Top 5 wins

### 1. Signatures on outline and lookup

**Problem.** Outline prints `name: [start, end]`, no signature. Stuart's spark (`tool_calls.rs --include-private`) showed thirteen `protocol_*: [start, end]` lines with zero hint what each tests. Same on real source: `McpServer.run: [172, 224]` could be anything.

**Change.** Add `signature TEXT` to `exports` and `methods` (schema v6). The existing tree-sitter pass already has the declaration node; `decl.start_byte()..body_node.start_byte()` is the header for Rust/TS/Python/Go in one slice per export. Render inline: `run: [172, 224]  # 187 lines, pub fn run(&mut self) -> Result<()>`.

**Payoff.** Eliminates 70-90% of follow-up `fmm_read_symbol` calls during orientation. Outline becomes self-sufficient.

**Cost.** ~500 KB-1 MB on a 50K-LOC repo (~80 bytes × 7K exports). Parse overhead: one `node.utf8_text` slice per export.

**Risk.** Generic-heavy Rust signatures wrap. Mitigation: soft cap at ~120 chars, ellipsize the where-clause, emit only for callable kinds.

### 2. Doc-comment first line as outline annotation

**Problem.** Outline names are opaque. A one-line "what does this do?" is the difference between a useful TOC and a list of identifiers.

**Change.** Leading comment block sits as a sibling node before every top-level declaration in every grammar fmm targets (Rust `///`, TS `/**`, Python `"""..."""`, Go `//`). Capture first non-blank line, strip prefix, store `doc_summary TEXT` on `exports`/`methods`. Render: `run: [172, 224]  # 187 lines, <sig>, "Drive the JSON-RPC loop until stdin closes."`.

**Payoff.** Outline starts looking like documentation. Search gains a preview column. Single biggest shift in how agents reason about unfamiliar files.

**Cost.** +1 column, ~300 KB / 50K LOC. Extra sibling-node lookup per declaration. Truncate to 120 chars at extract.

**Risk.** Many functions have no doc comments (8/10 private methods in `typescript/mod.rs` lack them). Degrades gracefully; perceived value depends on repo discipline.

### 3. Deprioritize fixtures and test fixtures in default symbol rankings

**Problem.** `fmm_lookup_export("init")` in fmm returns `fixtures/sample.lua:[24, 28]` as the primary answer; the real `crates/fmm-cli/src/cli/init.rs` is a footnote. Same for `list_exports` and `search`. The repo's own production command loses to a parser fixture for an unrelated language. Worst single failure mode I observed.

**Change.** Add `is_fixture INTEGER` on `files`, populated from path heuristics (`fixtures/`, `tests/parser_*/fixtures/`, `__fixtures__/`). Sort by `is_fixture ASC, ...existing`. Provide `include_fixtures: true` to bypass.

**Payoff.** Restores trust in `lookup_export` as a first-call tool.

**Cost.** One column, one ORDER BY. Zero parse overhead.

**Risk.** Some crates place fixtures outside conventional dirs. Make heuristic conservative; configurable via `.fmmrc.toml`.

### 4. Multi-root MCP server

**Problem.** MCP server binds to one `.fmm.db` at startup. An agent across fmm + context-matters + helioy-bus in one session reaches exactly one. `fmm_list_files(path: "/other/repo")` returns the wrong index silently — I reproduced this: requesting context-matters returned fmm's manifest. Today the agent drops to Bash + `cd` + `fmm`, forfeiting MCP entirely.

**Change.** Either (a) optional `root:` on every tool selects which loaded manifest, or (b) `fmm mcp --root p1 --root p2` and dispatch by path prefix. Cache by canonical root, invalidate on mtime.

**Payoff.** One session covers a monorepo or org. Kills the implicit single-project assumption.

**Cost.** Per-tool: HashMap lookup + on-demand load. Memory: ~10-20 MB / 50K-LOC manifest; LRU evict.

**Risk.** Silent failure if a relative path under root A is queried against bound root B. Validate every `file:` argument against resolved root.

### 5. Split `external` vs `unresolved` in dependency_graph

**Problem.** `fmm_dependency_graph(file: "manifest/mod.rs")` returns `external: [chrono, 'crate::parser', dependency_matcher, file_entry, glossary_builder, reexports, reverse_index, serde, std]`. Six are intra-crate sibling modules the resolver couldn't map to file paths; only three (`chrono`, `serde`, `std`) are real externals. An agent reading "external" believes nine third-party deps. There are three.

**Change.** Split rendering: `external: [chrono, serde, std]` and `unresolved: [...]`. The resolver already knows the difference; don't bucket failures with successes.

**Payoff.** Trustworthy blast-radius reads. Today `external` is actively misleading on every Rust file with sibling imports.

**Cost.** Zero. Pure renderer change; data is already classified.

**Risk.** Agents may rely on current shape. Bump tool minor.

## Secondary ideas

`Commands: [60, 672]  # 613 lines` in `cli/mod.rs` is an enum with ~20 variants — outline treats it as opaque. Enum-aware rendering could enumerate variant names with line ranges (tree-sitter already produces variant nodes). Same opportunity for trait impls.

Re-export resolver cross-resolves wrong: `init: fixtures/sample.lua:[24, 28]` for the CLI's `init`, `search: lib.rs:[11, 11]`. Prefer same-crate candidates before global name match.

`# non-exported` comment per line under a `non_exported:` heading is pure redundancy (~5% bytes on test-heavy outlines). Drop it.

`fmm_search(term: "init")` ranks by kind section, so fixtures dominate the EXPORTS block. A unified relevance score with sections below the fold would invert the noise.

`dependency_kinds` is in the schema and never surfaced. Expose on dependency_graph (`runtime`, `dev`, `test`) or drop the column.

`fmm_glossary` runs a tree-sitter second pass per query for call-site precision (per SKILL.md). Precomputing a `call_sites` table at index time converts O(file size) per call to O(1).

LOC ranking rewards long test files over small re-export hubs. `cm-core/src/lib.rs` is 23 LOC, 125 downstream — the most important file by impact. Add `sort_by: complexity` combining exports × downstream.

`fmm mcp` has no scope filter; agents filter every `list_files` result. A `--scope crate-name` startup flag or per-tool `crate:` filter would tighten output.

Outline on re-export-only modules (`format/mod.rs`) is nearly empty though those files are the public API. Render the re-export graph as primary content when `exports.is_empty() && !reexports.is_empty()`.

`fmm_read_symbol` truncates at 10 KB. Smarter on a 1,200-line class: collapse method bodies to `{...}`, keep signatures. Same budget, better signal.

Python parity gap: helioy-bus indexed cleanly but `fmm_file_outline` errored on `src/helioy_bus/server.py` despite a 36/37 indexed claim. Worth a Python parity sweep.

`fmm ls` is correct but SKILL prose uses `fmm_list_files` exclusively; a human reaching for `fmm list` gets an unrecognized-subcommand error.

## Dead weight / simplification candidates

- The `imports` field on `fmm_dependency_graph` output duplicates `external`. Pick one.
- Eighteen language parsers when the README admits only TS/Python/Rust are validated. Move untested parsers behind a `--enable-experimental-langs` flag; halve the binary footprint.
- `nested-fn` and `closure-state` kinds (ALP-922) add schema and rendering complexity but only surface under `include_private: true`, which agents rarely set. Either promote them or compile them out.
- Fixtures in the production index inflate every result set. Index them under a separate `is_fixture=1` flag (see win #3); exclude from rankings by default.
- `function_names TEXT` (JSON-encoded) on the `files` table is denormalized non-exported names — duplicates of what could live in `exports` with a `visibility` column.

## Open questions

- Does Stuart want signature + doc on the *default* outline, or behind an `include_docs: true` flag? Default-on is denser; opt-in keeps payload small.
- Is the long-tail goal to support cross-repo navigation (multi-root MCP) or to make single-repo navigation so good that switching is rare?
- Re-export resolution rules: when a symbol exists in both a same-crate module and a foreign fixture, what's the deterministic priority? (Current: ambiguous.)
- Acceptable index size ceiling on a 100K-LOC monorepo before perf becomes a concern? That bounds how much we can spend on signatures + docs + call sites.

## Performance ledger

| Proposal | Index growth (50K LOC) | Parse overhead | Query overhead | Net verdict |
|---|---|---|---|---|
| 1. Signatures column | +500 KB-1 MB | +<1 µs / export | None | Free win |
| 2. Doc 1-liner column | +300 KB | +<1 µs / declaration | None | Free win |
| 3. is_fixture column + sort | +<10 KB (boolean) | None (path-based) | +1 ORDER BY clause | Free win |
| 4. Multi-root MCP | None per repo, +10-20 MB resident per loaded manifest | None | +1 HashMap lookup / call | Free if LRU |
| 5. Split external / unresolved | None | None | None (rendering only) | Free win |
| Secondary: call_sites table | +1-3 MB | +5-15 ms / file at index time | -100% on glossary call-site mode | Worth it |
| Secondary: enum variant outline | +50-100 KB | +<1 µs / enum | None | Free win |
| Secondary: drop redundant `# non-exported` | -3-5% on test-heavy outline payloads | None | None | Trivial |

Performance budget is preserved on every top-5 proposal. The only one with non-trivial cost (multi-root MCP) pays it in RAM, not in query latency.
