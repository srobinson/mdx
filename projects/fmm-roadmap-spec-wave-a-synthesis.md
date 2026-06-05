---
title: fmm Roadmap — Spec Phase 2 Wave A Synthesis (CANONICAL)
type: spec
tags: [fmm, roadmap, spec, synthesis, map, diff, duplication, symbols, wave-a]
summary: Orchestrator synthesis of the four Wave A capability specs (map, diff, duplication, symbols). Records cross-spec convergences, resolves open questions, and adds a foundations addendum. Read alongside the four spec files.
status: approved-draft
source: orchestrator-synthesis
confidence: high
repo: /Users/alphab/Dev/LLM/DEV/helioy/fmm
head: 5f8a1296d72f507a2e4bd1950001a442dc6b31fc
created: 2026-06-17
specs:
  - ~/.mdx/projects/fmm-roadmap-spec-map.md
  - ~/.mdx/projects/fmm-roadmap-spec-diff.md
  - ~/.mdx/projects/fmm-roadmap-spec-duplication.md
  - ~/.mdx/projects/fmm-roadmap-spec-symbols.md
builds_on: ~/.mdx/projects/fmm-roadmap-spec-foundations.md
---

# Wave A synthesis

Four capability specs drafted in parallel against the locked foundations contract. All four are individually strong and grounded against HEAD `5f8a129`. This record captures what only the orchestrator can see: cross-spec convergences, a hard prerequisite all specs hit, resolved open questions, and a foundations addendum.

## Cross-spec convergences (independent — strong signal)

1. **PREREQUISITE — `crates/fmm-cli/src/cli/mod.rs` is at 719 LOC, over the repo's 700 hard limit.** The map, diff, AND duplication specs each independently flagged that the `Commands` enum file must be refactored BEFORE any new command variant (`Map`, `Diff`, `Snapshots`, `Dupes`, `Clones`, `Symbols`) is added — per CLAUDE.md "refactor before adding, no exceptions." This is **Slice 0** of the whole build phase: split `Commands` into a thin enum + move subcommand option structs into `cli/commands/*` modules. Nothing else lands until this is done.

2. **Push CLI-private logic into core for reuse (DRY).** map wants `commands/ls.rs::collect_entries` lifted to a core `manifest` helper (O-map-5); symbols wants a shared `SymbolQuery`/`SymbolRow` collector in core; duplication refactors `similarity.rs` so `find_similar` + `find_dupe_clusters` share one scorer; diff puts the diff engine in `fmm-core/src/diff.rs`. Converging principle: **the CLI command and MCP tool are both thin wrappers over one tested core function.** Build the core helper first, wire two surfaces second.

3. **MCP "every tool needs a live manifest" assumption must be relaxed.** diff needs snapshot-only calls to run when `.fmm-snapshots.db` exists even if `.fmm.db` can't load; map's `fmm_status` needs no manifest at all (`status` queries the index DB directly). `McpServer.handle_tool_call` currently loads a manifest before dispatching every tool — split this so manifest-free / snapshot-only tools dispatch without one. Shared MCP refactor, do once.

4. **All new tools/flags via `tools.toml`** (build.rs regenerates schema/help/skill); **all JSON via the foundations `print_envelope`/`FmmReportEnvelope`** (no per-command envelope assembly); **determinism gate = double-run byte equality** on every JSON surface. Uniform across all four.

## Foundations addendum (feed back into the foundations contract)

- **A1 — edge kind in snapshots (from diff OQ3).** diff wants dependency edges classified `runtime | type_only`, but the foundations `snapshot_reverse_deps` table is only `(target_path, source_path)`. **Resolution: no new column.** The adopted snapshot_files table (foundations D2 = Codex's fuller mirror) already carries `dependencies` + `dependency_kinds` JSON, so `fmm diff` reconstructs edge kind from `snapshot_files.dependency_kinds`. When kind is unavailable on a legacy row, diff compares `(source_path, target_path)` and emits an `edge_kind_unavailable` diagnostic. Confirm this is the contract; do not add a kind column to `snapshot_reverse_deps`.
- **A2 — `fmm_status` MCP tool ships with map, not foundations** (map resolved foundations O2). Foundations delivers `status --json` (CLI); the `fmm_status` MCP wrapper lands in the map slice.
- **A3 — index schema bump to v7.** symbols (body_loc + param_count + complexity columns on `exports`/`methods`) requires the first index `SCHEMA_VERSION` bump (6→7); duplication v2 adds the `symbol_fingerprints` table (another bump or batched). Index bumps are safe (regeneratable, nuke-and-rebuild). Coordinate: batch the body_loc columns into the v7 bump; the fingerprint table can ride a later bump since v2 ships after v1. The separate `.fmm-snapshots.db` is untouched by these.

## Resolved open questions (orchestrator decisions)

**map**
- O-map-1 (biggest): committed artifact = the **markdown skeleton printed to stdout** with explicit `<!-- fmm:narrative -->` placeholders; the agent redirects to `MAP.md`, fills placeholders, and commits. **fmm never writes files.** "Commit-able" = deterministic bytes. (Confirm with user, but this is the default consistent with "index, not author".)
- O-map-2: thresholds carried in envelope `params` — god-file LOC 700, hub min-downstream ≥10, top-K hubs/hotspots 20, cycle-summary cap 20. ACCEPT.
- O-map-3: in-memory path-prefix scope filter (no scoped re-generate); maps to `scope_digest="root"` for whole-repo. ACCEPT.
- O-map-4: public-only API surface by default. ACCEPT.
- O-map-5: lift `collect_entries` to a core helper. ACCEPT (DRY, see convergence 2).

**symbols**
- Q1 (param_count coverage): **null allowed** for grammars without support; Rust + TypeScript + Python first, others as parser tests land. Do NOT block Phase 1 on all-language coverage. Never infer from signature strings.
- Q2 (size vs body_loc redundancy): canonical metric is `body_loc`; "size" is a **text-label only**; JSON exposes `metrics.body_loc` (drop the duplicate top-level `size` in JSON). DRY.
- Q3 (kind aliases): exact `DeclarationKind::as_str` values only for v1; aliases (`function`→`fn`) deferred.

**duplication**
- Q1 (design doc): confirmed canonical path is `docs/superpowers/specs/2026-05-29-find-similar-design.md` (the cited `docs/FIND_SIMILAR_DESIGN.md` does not exist). Update references.
- Q2/Q3 (thresholds): Tier 1 inherits `similarity.rs::DEFAULT_THRESHOLD`; Tier 2 defaults (0.82 similarity, 40 min-tokens) calibrate on fixtures during implementation. Do not change the score formula to fix report noise.
- Q4 (cross-language clones): same-language only by default; `--cross-language` deferred.

**diff**
- Q1 (scope input): expose **`--scope-digest` only** in v1; human path→digest deferred (map may surface it later).
- Q2 (prune safety): `prune` executes on call; `--dry-run` is the safety, no extra `--apply` flag (matches foundations).
- Q3: resolved by A1 above.
- Q4 (SHA prefix): accept ≥7 chars, ambiguity-checked. ACCEPT.

## Build dependency order (capability layer)

```
Slice 0:  refactor cli/mod.rs Commands enum (PREREQUISITE — unblocks all)
          + relax MCP manifest-load (convergence 3)
Foundations (separate contract): git_sha → envelope → snapshots   [must precede map/diff]
Then, in parallel where independent:
  symbols (body_loc + param_count + fmm symbols + fmm_list_symbols)   [index v7]
  map (fmm map + fmm_codebase_map + fmm_status)                       [needs envelope + git_sha]
  duplication Tier 1 (fmm dupes, reuse similarity.rs)                 [no schema change]
  diff (fmm diff + snapshots list/prune + fmm_structural_diff)        [needs snapshots]
Then:
  duplication Tier 2 (fmm clones, fingerprint sidecar + LSH)          [index bump]
Wave B (next spec phase): fmm health (composes symbols + dupes + cycles), fmm lint-architecture
```

## Status

Wave A specs approved as drafts with the above resolutions applied. Pending: Wave B specs (health + lint-architecture), then the full tree is ready for the Slice Build Loop starting at Slice 0 + foundations.
