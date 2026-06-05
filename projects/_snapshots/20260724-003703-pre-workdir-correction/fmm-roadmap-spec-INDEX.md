---
title: fmm Roadmap — Spec Tree INDEX + Master Build Order (CANONICAL)
type: spec
tags: [fmm, roadmap, spec, index, build-order, wave-b, health, lint-architecture]
summary: Index of the complete fmm roadmap spec tree (foundations + 6 capabilities), Wave B synthesis (health, lint-architecture), and the consolidated build order for the Slice Build Loop.
status: approved-draft
source: orchestrator-synthesis
confidence: high
repo: /Users/alphab/Dev/LLM/DEV/helioy/fmm
head: 5f8a1296d72f507a2e4bd1950001a442dc6b31fc
created: 2026-06-17
---

# fmm Roadmap — spec tree index + master build order

Three warroom phases produced the full spec tree against HEAD `5f8a129`. This file indexes them, synthesizes Wave B (health + lint-architecture), and gives the single consolidated build order.

## ⚠️ DIRECTION CHANGE (2026-06-17) — skill-first, minimal tooling [SUPERSEDES the build order below]

Decision (Stuart): **do not encode in fmm any workflow an agent can perform itself.** Map generation is agent workflow → it lives in a SKILL, not a `fmm map` command. fmm only gains **new primitives the agent cannot cheaply replicate** (repo-wide duplication detection; symbol-level metrics). Mechanism (fmm = structural facts) vs policy (agent = composition / ranking / prose). fmm generates *candidates*; the agent judges.

Reclassification of the spec tree:
- **→ SKILL (drop the command):** `fmm map` aggregator + markdown renderer, `fmm health` report, `fmm diff` markdown/incremental-patch. These are composition/ranking/prose the agent does well.
- **DEFER:** F2 JSON envelope (new commands emit plain deterministically-sorted JSON instead of the versioned-envelope machinery); F3 snapshots + structural diff (agent gets "what changed" from `git diff <old>..HEAD` + targeted re-query — no per-SHA snapshot retention needed).
- **OUT OF SCOPE:** `fmm lint-architecture` (CI enforcement product feature; separate initiative).
- **KEEP as tooling (primitives the agent can't replicate):** `fmm dupes` (repo-wide structural duplicate clusters), `fmm clones` (body fingerprint / LSH), `body_loc` + `fmm symbols` (repo-wide size/kind/visibility query).
- **Shipped & kept:** Slice 0 CLI hygiene (PR #153, merged 072dc83), F1 git_sha (PR #154, merged 805ae4c) — the skill uses git_sha to stamp the map.

New plan (skill-first, evidence-driven — let the workflow reveal the tooling):
1. **MAP.SKILL.md** — standalone map-generation skill at the repo root (`/Users/alphab/Dev/LLM/DEV/helioy/fmm/MAP.SKILL.md`), using only existing primitives + git_sha. Deliberately NOT derived from the `helioy-tools:codebase-map` skill; intended to replace it.
2. **Dogfood:** run the skill to generate `MAP.md` on this repo; record every point where the agent does something expensive or badly.
3. **Build only the proven gaps.** Near-certain: `fmm dupes`. Likely: `body_loc` + `fmm symbols`. Later: `fmm clones`. Don't build speculatively.
4. Each new primitive emits clean deterministic JSON (no envelope machinery), ships via `tools.toml`, gated by `just ci`, surfaced for merge.

The `fmm-roadmap-spec-{duplication,symbols}.md` specs remain valid as the **tooling backlog**. The `{map,diff,health,lint-architecture}` and foundations **F2/F3** specs are superseded/deferred per the above. Everything below predates this pivot — read it as history.

## Spec tree (all on disk under ~/.mdx/projects/)

| Spec | File | Status |
|---|---|---|
| Eval (origin) | `fmm-eval-claude--brainstorm.md`, `fmm-eval-codex--brainstorm.md` | done |
| **Foundations** (git_sha, JSON envelope, snapshots) | `fmm-roadmap-spec-foundations.md` (+ `-claude`/`-codex` drafts) | canonical |
| `fmm map` | `fmm-roadmap-spec-map.md` | drafted |
| `fmm diff` + snapshots surface | `fmm-roadmap-spec-diff.md` | drafted |
| duplication (`fmm dupes` + `fmm clones`) | `fmm-roadmap-spec-duplication.md` | drafted |
| `fmm symbols` + body_loc + complexity | `fmm-roadmap-spec-symbols.md` | drafted |
| Wave A synthesis | `fmm-roadmap-spec-wave-a-synthesis.md` | canonical |
| `fmm health` | `fmm-roadmap-spec-health.md` | drafted |
| `fmm lint-architecture` | `fmm-roadmap-spec-lint-architecture.md` | drafted |
| This index + Wave B synthesis | `fmm-roadmap-spec-INDEX.md` | canonical |

## Wave B synthesis

### Cross-cutting findings

1. **The symbols core helper is a shared dependency for THREE consumers.** `fmm symbols`, `fmm health` (long_symbol/complex_symbol), and `fmm lint-architecture` (symbol_size_limit) all consume the symbols-spec `SymbolQuery`/`SymbolRow` collector + `SymbolMetrics.body_loc` (`crates/fmm-core/src/symbols.rs`, `parser/types.rs`). Build that core helper once, early; the three surfaces are thin consumers. Both Wave B specs correctly degrade (diagnostic + skip the rule) if body_loc is absent.

2. **health vs lint-architecture share signals but are different tools — no duplication.** Both read `FileEntry.loc` (god-file / file_size_limit), `dependency_cycles_*` (cycles), and the symbols helper. The split is deliberate: **health = advisory ranked report** with sensible built-in defaults, no config required; **lint-architecture = enforcement** driven by `.fmmrc.toml` `[architecture]` config with a CI exit code. They compose the same underlying primitives (do NOT re-derive); each applies its own policy layer. Keep the primitive (e.g. `FileEntry.loc`, the cycle engine) single-sourced.

3. **lint extends the existing config, never forks it.** `[architecture]` is a new optional section on `crates/fmm-core/src/config::Config` via `FileConfig`/`apply_file_config`; all fields default empty so existing `.fmmrc.toml` keeps working. A strict-load path is added for lint only (CI must fail on bad architecture config) without changing the lenient posture of other commands.

4. Uniform with Wave A: both add CLI variants ⇒ gated behind **Slice 0** (cli/mod.rs refactor); both are manifest-backed (no MCP manifest-relax needed); all tools/flags via `tools.toml`; all JSON via the foundations envelope; `config_anchor`/symbol names not file:line; determinism gate = double-run byte equality.

### Resolved open questions

**health**
- O-health-1 (biggest): **No composite 0–100 health score in v1.** Emit ranked findings + `by_severity`/`by_confidence`/`by_category` counts. A scalar invites arbitrary weighting and false precision; ranking is reproducible. DECISION.
- O-health-3: `broad_visibility` ships **opt-in** (`--category broad_visibility`, off by default) until calibrated — it is the lowest-confidence signal. DECISION.
- O-health-4: `--verify-dead-exports` (Layer-3 call-site precision) is **opt-in only**, never default (per-candidate file reads). ACCEPT.
- O-health-2: ruleset over MCP = discrete scalar overrides (flat tools.toml params); preset names deferred. ACCEPT.
- O-health-5: `fan_out_max`/`complexity_max`/`nesting_depth_max` defaults calibrate on fixtures; don't block the contract on numbers. ACCEPT.
- Confirmed: dead_export confidence ceiling is **medium even when verified** (dynamic dispatch is structurally invisible to a static index). Good — keep.

**lint-architecture**
- Q1 (`detect_graph_roots`): default **false** (pattern-based entrypoints) until real configs prove the root heuristic is quiet. ACCEPT.
- Q2 (unmatched files / layer coverage): files with no layer are **not** layering violations in v1; layer-coverage enforcement is a later rule. ACCEPT.
- Q3 (strict config scope): strict architecture-config errors apply to **`lint-architecture` only** in v1; other commands keep lenient config loading (least blast radius). DECISION.

## Master build order (Slice Build Loop)

```
SLICE 0  — PREREQUISITE (unblocks everything)
  • Refactor crates/fmm-cli/src/cli/mod.rs Commands enum (719 LOC > 700 limit):
    thin enum + move subcommand option structs into cli/commands/*.
  • Relax MCP handle_tool_call so manifest-free / snapshot-only tools dispatch
    without a live manifest (needed by diff + fmm_status).

FOUNDATIONS  (must precede map/diff; see foundations contract)
  F1 git_sha in meta (+ git.rs, --sha, status --json)   [no index schema bump]
  F2 versioned JSON envelope + print_envelope + no-op generated_at stability
  F3 SHA-keyed snapshots in SEPARATE .fmm-snapshots.db (D1)

CAPABILITIES  (parallel where independent, after their deps)
  symbols   : body_loc + param_count + fmm symbols + fmm_list_symbols   [index → v7]
              ↳ shared SymbolQuery core helper (consumed by health + lint)
  map       : fmm map + fmm_codebase_map + fmm_status   [needs F1,F2]
  dupes-T1  : fmm dupes (reuse similarity.rs, blocking, union-find)   [no schema change]
  diff      : fmm diff + snapshots list/prune + fmm_structural_diff   [needs F3]

  clones-T2 : fmm clones (symbol_fingerprints sidecar + minhash/LSH)   [index bump; after dupes-T1]

WAVE B  (after symbols + dupes-T1)
  health    : fmm health + fmm_health_report (composes symbols, dupes, cycles, glossary)
  lint-arch : fmm lint-architecture + [architecture] config (composes graph, cycles, symbols)
```

Dependencies in one line: `Slice 0 → Foundations → {symbols, map, dupes-T1, diff} → clones-T2 → {health, lint-arch}`. symbols' core helper is on the critical path for health + lint, so prioritize it within the capability wave.

## Status

Full spec tree drafted and synthesized; all open questions resolved or deferred-with-rationale. Ready for the Slice Build Loop starting at Slice 0. Recommend a Peer Consensus sign-off pass on the foundations + Slice 0 specs before the first build slice, since they are the highest-blast-radius (schema, separate DB, CLI refactor everything depends on).
