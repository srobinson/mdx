---
title: fmm tooling evaluation — Codebase MAP.md generation & Code-health detection
type: research
tags: [fmm, codebase-map, code-health, duplication, tooling-gap, agent-tooling]
summary: fmm supplies strong structural raw material for both tasks but lacks git/SHA awareness, structural diff/history, and a repo-wide duplication scan; both tasks are PARTIAL today.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

# fmm tooling evaluation: MAP.md generation & code-health detection

Scope: can fmm (repo `/Users/alphab/Dev/LLM/DEV/helioy/fmm`, HEAD `5f8a129`, `fmm_version 0.3.6`, schema v6) power, **today**, (1) an LLM-agent Codebase MAP.md and (2) agent-driven code-health analysis — and if not, what to build. Every claim below was tested against this repo's CLI (`crates/fmm-cli/src`), the 10 `fmm_*` MCP tools, fmm-core, and the SQLite schema (`crates/fmm-store/src/schema.rs`).

Surface confirmed: CLI commands `ls outline lookup exports read deps search glossary similar` (navigation) + `init generate watch validate mcp status clean` (project). MCP tools (10): `list_files outline lookup_export list_exports read_symbol dependency_graph search glossary dependency_cycles find_similar` (`crates/fmm-cli/src/mcp/tools/`). Data model (`schema.rs`, schema_version=6): tables `files, file_paths, exports, methods, reverse_deps, workspace_packages, meta` — **no history/snapshot/commit table**.

---

## A. TASK 1 — Codebase MAP.md, SHA-stamped, per-commit incremental diff

### Primitives that already serve it (with evidence)

| MAP need | fmm primitive | Evidence (tested on this repo) |
|---|---|---|
| Module/component topology | `fmm ls --group-by subdir` / `fmm_list_files(group_by:"subdir")` | Returned 3 buckets `crates/ 392f·62,288 LOC`, `fixtures/ 23f`, `npm/ 1f`; drill-down `crates/fmm-cli/src/mcp` = 30 files·4,108 LOC |
| Where weight/hubs live | `fmm ls --sort-by downstream` / `fmm_list_files(sort_by:"downstream")` | `parser/mod.rs` ↓82, `manifest/mod.rs` ↓79, `identity/mod.rs` ↓28 — architectural hubs |
| God-files / size | `fmm ls --sort-by loc` | largest `crates/fmm-cli/src/cli/mod.rs` 719 LOC |
| Per-module internals | `fmm outline FILE` / `fmm_file_outline` | exports, signatures, line ranges, **visibility + declaration_kind** per symbol |
| Seams / boundaries | `fmm deps FILE` / `fmm_dependency_graph`, `fmm glossary` | glossary `FileEntry` → file-level importers across all three crates |
| Coupling / cycles | `fmm dependency_cycles` | found real SCCs (e.g. `search/*`, `resolver/*`, plus Rust sibling-`mod.rs` artifacts) |
| Public API surface | `fmm exports` / `fmm_list_exports`, `fmm search` | per-directory export discovery, regex-scoped |

The data model carries `signature`, `visibility` (`public/crate/protected/private/non_exported`), and `declaration_kind` (`fn/method/struct/trait/impl/enum/...`) per symbol (`schema.rs:123-150`), enough for an agent to describe component shape (trait-heavy, struct+impl, etc.).

### What is missing

1. **No document generation.** fmm emits query results (YAML/JSON), never a synthesized narrative. README positions it as "the index you query first," explicitly *not* a doc author. The agent must author MAP.md from ~7-10 calls. Acceptable, but there is no single "architecture digest" call.
2. **No pattern/idiom detection.** "Coding patterns" (error strategy, newtype, builder) are not classified; the agent infers them from outlines.
3. **No git/SHA awareness anywhere.** Verified `meta` table contents: `schema_version=6, next_file_id=416, fmm_version=0.3.6, generated_at=2026-06-04T15:51:31`. There is **no `git_sha`**. `generated_at` is wall-clock, decoupled from commits. `fmm search git` returns only `respects_gitignore` (a test) + `.gitignore` exclusion. fmm cannot supply the SHA to stamp the MAP; the agent must `git rev-parse HEAD` itself.
4. **No diff-aware rerun.** The index holds only current state; `generate` overwrites in place (`schema.rs` ensure_schema nukes-and-rebuilds on version change). No history/snapshot table exists. Closest primitives:
   - **`content_hash` per file** — verified **416/416 populated** (`fnv1a64:...`). fmm already knows each file's content hash, so a structural diff is *computable* — but only if a prior snapshot is retained, which it is not.
   - `fmm generate --dry-run` reports files that *would* update (mtime-based) — a weak file-level "changed since last index", not commit-scoped and not symbol-level.
   - `fmm validate` → exit 1 if stale — signals drift, not deltas.

### Feasibility of SHA-stamping + per-commit incremental diff rerun

- **SHA-stamping: trivial.** One `meta` row (`git_sha`) written at `generate` time via a git shell-out gated on repo presence, plus a `--sha` override for CI. The `meta` table and `fmm status` plumbing already exist.
- **Incremental structural diff: a real build, but the raw material exists.** Needs either snapshot retention (a `history` table keyed by `git_sha` holding file `content_hash` + symbol rows) or a two-DB diff command. The per-file `content_hash` (already populated) gives fast file-level gating; the per-symbol `exports`/`methods` rows give structural deltas (added/removed/signature-changed). The machinery (history + diff) is absent; the inputs are present.

---

## B. TASK 2 — Code health (duplication, refactoring, general health)

### Primitives that already serve it (tested on this repo)

| Health need | fmm primitive | Evidence |
|---|---|---|
| "Does this already exist?" dedup | `fmm similar NAME` / `fmm_find_similar` | Probe `dependency_graph` → 10 ranked matches with score breakdown `[name, shape, kind, nbhd]`; deterministic (token overlap + signature shape + kind + shared-dep neighborhood), no embeddings (`crates/fmm-core/src/similarity.rs`) |
| Circular deps | `fmm dependency_cycles` / `fmm_dependency_cycles` | Found multiple SCCs incl. genuine coupling clusters (`search/*`, `resolver/*`) and Rust `mod.rs` sibling artifacts |
| God-files | `fmm ls --sort-by loc` | `cli/mod.rs` 719 LOC — exceeds the repo's own 700-LOC CLAUDE.md threshold |
| Refactor-risk hubs | `fmm ls --sort-by downstream` | high fan-in files surfaced (↓82, ↓79) |
| Dead-export candidate / change blast radius | `fmm glossary` | empty `used_by` ⇒ unused candidate; populated ⇒ rename blast radius |
| Over-broad visibility | `exports.visibility` + `glossary` | `pub` symbol used only in-crate is detectable by joining visibility with reverse-deps |

### What is missing

1. **No repo-wide duplication scan — the biggest TASK-2 gap.** `find_similar` is **probe-based**: it requires a `name` and answers "what is like THIS one." Auditing the whole repo means probing every symbol (O(N) round-trips) and de-duping by hand. The design doc `docs/FIND_SIMILAR_DESIGN.md` explicitly defers a batch `fmm dupes` command to "a possible later phase."
2. **No complexity metrics.** No cyclomatic complexity, nesting depth, parameter counts, or per-function fan-out. Only file-level LOC; function body-LOC is derivable from `start_line`/`end_line` but not surfaced as a "long function" report.
3. **No dead-code report.** Unused-export detection is *derivable* from glossary (empty `used_by`) but no command does it, and it must discount re-exports, public API, test-only, and dynamic dispatch. Not turnkey.
4. **No churn/hotspot health** — would need git history, which fmm does not read.
5. **No body-level clone detection.** `find_similar` keys on name/signature/kind/neighborhood, not AST-body/token similarity, so copy-pasted bodies under different names/signatures may not surface.

---

## C. Concrete tooling improvements (ranked, buildable)

1. **`fmm dupes` — repo-wide duplication audit** (new CLI + MCP tool). *Gap:* `find_similar` is probe-only; no batch clone report (TASK 2's #1 blocker). Already designed/deferred in `docs/FIND_SIMILAR_DESIGN.md`. *Shape:* in = optional `--dir` scope, `--kind` filter, `--min-score`; out = clusters `[{score, members:[{name,file,lines,signature}]}]` sorted by score. *Build:* reuse `crates/fmm-core/src/similarity.rs` over the `exports`/`methods` tables with blocking (by kind/token bucket) to avoid O(N²). Highest leverage.

2. **Git-SHA stamping in the index** (fmm-core + `meta` + flag). *Gap:* TASK 1 needs SHA-stamped maps; `meta` has no `git_sha` (verified). *Shape:* on `generate`, `git rev-parse HEAD` (gated on repo) → write `meta.git_sha`; add `fmm generate --sha <sha>` for CI; expose via `fmm status --json`. *Build:* one meta row + shell-out; trivial. Unblocks MAP stamping without a side-channel.

3. **`fmm diff [<old_sha>]` — structural change report** (new command + snapshot retention). *Gap:* no diff-aware rerun for incremental MAP updates (TASK 1). *Shape:* in = two SHAs or "since last index"; out = per-file added/removed/modified + per-symbol added/removed/signature-changed + new/removed dep edges + new cycles, as markdown **and** JSON. *Build:* add a `history` table keyed by `git_sha` (file `content_hash` + symbol rows), gate file-level deltas on the already-populated `content_hash`, then diff symbol rows. The real engineering lift, but inputs already exist.

4. **`fmm health` — aggregate health digest** (new command + MCP). *Gap:* health signals are scattered across `ls`/`cycles`/`glossary`. *Shape:* out = god-files (LOC > threshold), high-fan-in hubs (downstream > N), cycle summary, dead-export candidates, duplication-cluster count (from #1). *Build:* pure composition of existing primitives + #1; cheap once #1 lands. Turnkey TASK-2 call.

5. **Function/symbol-level size + complexity** (fmm-core parser). *Gap:* only file LOC. *Shape:* extend `exports`/`methods` with `body_loc` (nearly free — line ranges exist) and optionally branch/nesting counts from tree-sitter; surface via `fmm outline --large` or `fmm ls --symbols --sort-by loc`. *Build:* body_loc cheap; cyclomatic needs per-language queries (lower priority).

6. **`fmm map` — architecture digest aggregator** (new command, optional). *Gap:* MAP assembly costs ~7-10 calls. *Shape:* one call returns per-directory `{file count, LOC, top exports, top hubs}`, workspace packages, cycle summary, API surface as JSON the agent turns into prose. Does *not* author the MAP (keeps fmm's "index, not author" positioning); collapses round-trips. Mostly composition.

7. **Stable `--json` everywhere** (polish). Several commands already emit `--json` (help shows `fmm lookup ... --json`). Guarantee `ls/outline/deps/cycles/glossary/health` emit stable, versioned JSON so an agent can diff two runs deterministically — enables TASK-1 rerun-and-diff at the agent layer even before #3.

---

## D. Verdict

- **TASK 1 (MAP.md): PARTIAL.** Excellent structural raw material (topology, hubs, outlines, seams) and the agent can author the MAP, but the SHA-stamp + per-commit incremental-diff loop is unsupported. **Biggest blocker: no git awareness and no structural history/diff** (per-file `content_hash` exists, but no prior snapshot is retained).
- **TASK 2 (code health): PARTIAL.** Strong on cycles, blast-radius, god-files, and single-probe dedup, but no repo-wide duplication scan and no complexity/dead-code reports. **Biggest blocker: `find_similar` is probe-only** (no batch `fmm dupes`).
