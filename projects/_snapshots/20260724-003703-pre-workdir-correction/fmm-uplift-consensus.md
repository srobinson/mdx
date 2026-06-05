---
title: fmm uplift consensus — agent UI shape
type: decision
tags: [fmm, agent-ui, consensus, peer-consensus, mixture-of-experts]
summary: Converged shape for fmm's agent-facing surface, produced by MoE peer-consensus (helioy-tools:codebase-analyst on Claude + Codex panes).
status: pending-sign-off
reviewed_by: [fmm:helioy-tools:codebase-analyst:5:3.1, fmm:helioy-tools:codebase-analyst:5:3.2]
orchestrator: context-matters:general:5:2.1
created: 2026-05-22
inputs:
  - ~/.mdx/projects/fmm-uplift-brainstorm-claude.md
  - ~/.mdx/projects/fmm-uplift-brainstorm-codex.md
---

# fmm uplift consensus

The shape below is what an LLM agent navigating an unfamiliar codebase actually wants from fmm. Every decision is framed by two hard constraints: **agent call budget** (a typical orientation pass should converge in ≤3 tool calls) and **performance is sacred** (no default-on field that isn't free or near-free in the index path).

## Decisions

### 1. Default density of `fmm_file_outline`

- **`signature`: default-on.** Universal call saver. Already paid in the tree-sitter pass: raw declaration header from `decl.start_byte()..body_node.start_byte()`.
- **`doc_summary`: opt-in via `include_docs: true`.** Source-derived only — first non-blank line of leading doc comment (`///`, `/**`, `"""`, `//`) with prefix stripped, truncated to 120 chars at extract, omitted entirely when absent. Never generated or paraphrased.
- **`visibility` and `kind`: default-on.** Drop the redundant `# non-exported` suffix; replace with explicit `visibility:` and `kind:` fields. Visibility values: `public`, `crate`, `protected`, `private`, `non_exported`. Kind values: `fn`, `method`, `field`, `const`, `test`, `struct`, `trait`, `impl`, `enum`, `variant`, `module`, `macro`.
- **`freshness` annotation: default-on when stale paths are known.**

### 2. Output format

YAML default, JSON opt-in via `--json` (or `format: json` on MCP). **Never emit both side by side.** YAML is more token-dense for LLM consumption; JSON remains the strict-parser path.

### 3. Presets

**One canonical default, plus two binary flags.** No three-tier preset scheme.

- **Default** = dense structured output: signature + visibility + kind + freshness annotation. No prose framing. `doc_summary` only when `include_docs: true`.
- `--minimal` = structure-only output (name + line range + kind only). The rare case.
- `--human` = adds prose framing for direct human reading.

Same expressive space as a preset triad, fewer named objects to learn.

### 4. Custom fields

**Persist sparse `custom_fields TEXT` column on `files`**, null when absent. Expose only via:

- `include_custom: true` on `fmm_file_outline`,
- `fmm_search --custom key=value` for structured search.

Never in the default response. Honors the parser's existing extraction work (currently discarded in `writer.rs:124-162`) without becoming a junk-drawer default.

### 5. Multi-root MCP vs `fmm_context_pack`

**Complements, not substitutes. Multi-root first.**

- **Tier 1 — Multi-root MCP server.** An agent in a Helioy session crosses 3-4 repos. Today the server binds one `.fmm.db` and silently returns the wrong index for cross-repo queries. The MCP server must accept an optional `root:` per tool, validate every `file:` argument against the resolved root, and never silently answer from the wrong manifest. LRU cache loaded manifests.
- **Tier 3 — `fmm_context_pack`.** A composite MCP tool that returns topology + outline + direct deps + top downstream + tests + freshness in one call for a file or directory. Ship after the index-side wins; this is a UX wrapper, not new capability.

### 6. Freshness

**Warn by default. Strict mode opt-in.**

- Multi-result tools (`fmm_list_files`, `fmm_search`, `fmm_glossary`, `fmm_dependency_graph`) emit one freshness annotation per response when stale paths are known.
- Lookup-style tools (`fmm_lookup_export`, `fmm_read_symbol`, `fmm_file_outline`) tag stale result files inline when known.
- `strict: true` blocks stale answers (returns a freshness error instead of stale data). Opt-in for agents that have explicitly chosen consistency over availability.
- Cheap path: stored validation summary + bounded mtime checks on touched paths. No full reindex on every query.

### 7. Re-export resolver & lookup tie-break

Deterministic priority for `fmm_lookup_export` and friends.

**With a calling context (resolving from file R):**
1. Same workspace package as R
2. Non-fixture, non-test source
3. Tests
4. Fixtures
5. Shortest path depth
6. Lexicographic path

**Without a calling context (bare lookup):**
1. Non-fixture, non-test source
2. Tests
3. Fixtures
4. Shortest path depth
5. Lexicographic path

**Universal rule:** Direct local definitions beat re-exported candidates at the same rank.
**Disclosure:** Always surface the full collision list in a compact footnote (`also: [path:line, path:line, …]`).

### 8. Fixture deprioritization

`is_fixture` and `is_test` are first-class ranking signals across `fmm_lookup_export`, `fmm_list_exports`, `fmm_search`, `fmm_glossary`. The observed failure mode (`fmm_lookup_export("init")` in fmm itself returning `fixtures/sample.lua:[24,28]` as the primary answer ahead of the real `crates/fmm-cli/src/cli/init.rs`) is a wrong-answer failure, not just incomplete output, and must be fixed before any other ranking work.

Implementation: `is_fixture INTEGER` and `is_test INTEGER` on `files`, populated from path heuristics (`fixtures/`, `tests/parser_*/fixtures/`, `__fixtures__/`, `tests/`), configurable via `.fmmrc.toml`. Sort `is_fixture ASC, is_test ASC, …existing`. `include_fixtures: true` and `include_tests: true` bypass.

### 9. External vs unresolved split

**Fast follow.** Pure renderer fix; the data is already classified. `fmm_dependency_graph` currently emits a single `external` list that conflates intra-crate sibling modules (`crate::parser`) with real external packages (`chrono`, `serde`). Split into:

- `external: [chrono, serde, std]` (resolved third-party + std)
- `unresolved: [crate::parser, dependency_matcher, …]` (resolver couldn't map)

Tool minor bump. Zero index cost.

## Priority shape

| Tier | Wins | Why |
|---|---|---|
| **1 — Must ship (agent-budget hits)** | (1) outline density (signature + visibility + kind default-on), (5) multi-root MCP, (6) freshness warn default, (7+8) fixture deprioritization + re-export tie-break | Each closes a specific failure observed in real cross-repo dogfooding. |
| **2 — High value, opt-in / fast follow** | (1b) `doc_summary` via `include_docs: true`, (4) custom_fields opt-in, (3) `--minimal` and `--human` flags, (9) external/unresolved split | Reach extends signal without bloating defaults. External/unresolved is pure honesty fix, ships as fast follow. |
| **3 — UX wrappers** | `fmm_context_pack` MCP tool | Ship after Tier 1 lands; composes existing capability, doesn't expose new data. |

## Performance ledger

| Change | Index growth (50K LOC) | Parse overhead | Query overhead | Verdict |
|---|---|---|---|---|
| `signature` column | +500 KB–1 MB | +<1 µs / export (substring slice) | None | Free win |
| `doc_summary` column (capped, source-only, opt-in render) | +0–300 KB (depends on doc discipline) | +<1 µs / declaration | None unless requested | Free unless surfaced |
| `visibility` + `kind` columns | +<100 KB | None (already classified) | None | Free win |
| `is_fixture` + `is_test` columns | +<10 KB (booleans) | None (path-based) | +1 ORDER BY clause | Free win |
| Custom fields JSON | +0–1 MB (sparse, opt-in only) | None (already extracted) | None unless requested | Free unless surfaced |
| Multi-root MCP | None per repo, +10–20 MB resident per loaded manifest | None | +1 HashMap lookup / call | Free if LRU |
| Freshness annotation | Optional cached summary | None | Bounded mtime checks on touched paths | Free if scoped |
| External/unresolved split | None | None | None (renderer only) | Free win |
| Re-export tie-break + collision footnote | None | None | Minor sort cost on lookup | Free win |
| `fmm_context_pack` | None | None | Sum of existing queries, amortized | Cheap |

Every Tier 1 default-on change is free or near-free in the index path. Stuart's hard constraint holds.

## Out of scope (deliberately deferred)

- Smarter `fmm_read_symbol` truncation (collapse method bodies, keep signatures).
- Enum-aware outline rendering for variant lists.
- Python parser parity sweep (`file_outline` errored on `src/helioy_bus/server.py` despite clean index claim).
- Dropping the redundant `imports` field on `fmm_dependency_graph` (duplicates `external`).
- Eighteen language parsers behind an `--enable-experimental-langs` flag (README only validates Rust/TS/Python).

These are real findings but smaller than Tier 1.

## Sign-off

Both reviewers, please re-read this doc and either send `"I sign off on the fmm agent UI consensus as currently stated"` on topic `fmm-uplift-signoff`, or escalate remaining concerns. This is the final sign-off, not a peer-debate round.
