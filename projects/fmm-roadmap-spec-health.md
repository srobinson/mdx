---
title: fmm Roadmap — fmm health Spec (Wave B)
type: spec
tags: [fmm, roadmap, health, code-health, mcp, json-contract, composition, wave-b]
summary: Aggregate, ranked code-health report that COMPOSES existing fmm signals (god-files, hubs, cycles, long/complex symbols, duplication clusters, dead exports, broad visibility) into one finding model. Composes only; never reimplements.
status: draft
source: codebase-analyst
confidence: medium
repo: /Users/alphab/Dev/LLM/DEV/helioy/fmm
head: 5f8a1296d72f507a2e4bd1950001a442dc6b31fc
fmm_version: 0.3.6
created: 2026-06-17
updated: 2026-06-17
inputs:
  - ~/.mdx/projects/fmm-roadmap-spec-foundations.md
  - ~/.mdx/projects/fmm-roadmap-spec-wave-a-synthesis.md
  - ~/.mdx/projects/fmm-roadmap-spec-symbols.md
  - ~/.mdx/projects/fmm-roadmap-spec-duplication.md
---

# fmm health Spec

`fmm health` and MCP `fmm_health_report` produce one aggregate, ranked code-health report by **composing** signals fmm already computes. It is a reporting layer, not a new analysis engine. Every signal traces to an existing or Wave-A core function; health adds the finding model, the ruleset, the rollup, and the ranking. It computes no new structural facts and adds no schema.

This is **Wave B**, gated behind Wave A (symbols + duplication Tier 1) and the foundations envelope. See *Build dependency order* in `~/.mdx/projects/fmm-roadmap-spec-wave-a-synthesis.md`.

## Foundation and Wave-A dependencies (cited contracts — do not redefine)

- **Envelope / determinism** — `~/.mdx/projects/fmm-roadmap-spec-foundations.md`. `--json` emits `FmmReportEnvelope` directly (D5); `contract_version` (D4); `generated_at` comes from index meta, not query time; thresholds live in `params` (key-sorted, defaults resolved); the envelope `diagnostics: []` array carries degradation notes; determinism gate is double-run byte equality. This spec defines only the `results` payload.
- **Symbols** — `~/.mdx/projects/fmm-roadmap-spec-symbols.md`. Health consumes the core `SymbolQuery`/`SymbolRow` collector (`crates/fmm-core/src/symbols.rs`) and `SymbolMetrics` (`crates/fmm-core/src/parser/types.rs`): `body_loc`, `cyclomatic_complexity`, `nesting_depth`, `branch_count`, `match_arm_count`, `param_count`. Complexity metrics are **phased and may be null** (symbols Q1); health must degrade gracefully.
- **Duplication** — `~/.mdx/projects/fmm-roadmap-spec-duplication.md`. Health consumes `find_dupe_clusters(manifest, &DupeOptions) -> DupeClustersResult` (`crates/fmm-core/src/similarity.rs`). Tier 1 (`fmm dupes`) must land before health surfaces duplication findings; absence degrades gracefully.
- **CLI hygiene prerequisite** — Wave A synthesis convergence 1. `crates/fmm-cli/src/cli/mod.rs` is 719 LOC (over the 700 hard limit). Slice 0 (split `Commands` into a thin enum + `cli/commands/*` option structs) is a hard prerequisite before the `Health` variant is added. Health does not relitigate this; it inherits the refactored layout.
- **Single core function, two thin surfaces** — Wave A synthesis convergence 2. CLI `fmm health` and MCP `fmm_health_report` are both thin wrappers over one tested core composer.

## Scope

`fmm health` reports nine finding categories, each composed from a named existing signal:

| Category | Composed from (file::symbol) | What it flags |
| --- | --- | --- |
| `god_file` | `crates/fmm-core/src/manifest/file_entry.rs::FileEntry` field `loc`, via `Manifest.files` | File LOC over threshold |
| `dependency_cycle` | `crates/fmm-core/src/search/dependency_cycles.rs::dependency_cycles_with_path_filter` | Strongly-connected import cycles |
| `fan_in_hub` | `crates/fmm-core/src/manifest/reverse_index.rs::ReverseDeps` via `Manifest.reverse_deps` | Files imported by > N others (blast-radius hubs) |
| `fan_out_hub` | `crates/fmm-core/src/manifest/file_entry.rs::FileEntry` field `dependencies`, via `Manifest.files` | Files importing > N internal deps |
| `long_symbol` | symbols `crates/fmm-core/src/symbols.rs::SymbolRow` field `body_loc` | Symbols over body-LOC threshold |
| `complex_symbol` | symbols `crates/fmm-core/src/parser/types.rs::SymbolMetrics` (`cyclomatic_complexity`, `nesting_depth`) | High-complexity symbols (when metric present) |
| `duplicate_cluster` | duplication `crates/fmm-core/src/similarity.rs::find_dupe_clusters` | Structural duplicate clusters |
| `dead_export` | `crates/fmm-core/src/manifest/glossary_builder.rs::Manifest::build_glossary` (Layer 2) + `crates/fmm-cli/src/glossary.rs::apply_call_site_precision` (Layer 3, opt-in) | Exported symbols with no detected consumer |
| `broad_visibility` | `SymbolMetadata.visibility` + `Manifest.reverse_deps` + `Manifest.workspace_packages` | `pub` symbols used only within their own crate/package |

Out of scope: any new parser metric, schema table, embedding, or source-text analysis. Health never writes files (consistent with the map spec's "index, not author").

## Architecture: where the composer lives

Per convergence 2, the composer is one tested core function. All nine signals except the Layer-3 dead-export refinement are derivable inside `fmm-core`, so:

- **`crates/fmm-core/src/health.rs`** (new) — `analyze_health(manifest: &Manifest, ruleset: &HealthRuleset) -> HealthReport`. Composes god-files, cycles, fan-in/fan-out, long/complex symbols, duplication clusters, Layer-2 dead-export candidates, and broad-visibility candidates. Pure over the loaded `Manifest` + Wave-A core helpers. No file reads, no I/O.
- **CLI enrichment (fmm-cli)** — Layer-3 call-site precision (`crates/fmm-cli/src/glossary.rs::apply_call_site_precision`) lives in `fmm-cli`, not core. When `--verify-dead-exports` is set, the CLI runs that precision pass over the core's `dead_export` candidate set to discount re-exports / namespace callers and raise confidence. This is a thin enrichment over the core result, not a reimplementation.
- **CLI `fmm health`** (`crates/fmm-cli/src/cli/commands/health.rs`, new) and **MCP `fmm_health_report`** (`crates/fmm-cli/src/mcp/tools/health.rs`, new) are thin wrappers: load manifest → call `analyze_health` → (optional verify pass) → render text or envelope.

Health is a normal manifest-backed tool. It is **not** snapshot-only and needs no relaxation of the MCP manifest-load path (Wave A convergence 3 does not apply here).

## Composition contracts (how each signal is reused — never recomputed)

1. **god_file** — iterate `Manifest.files`; for each `FileEntry.loc > ruleset.god_file_loc` emit a file-level finding. `include_tests=false` filters test files via `Config::is_test_file` (the same classifier `fmm ls`/cycles already use).
2. **dependency_cycle** — call `dependency_cycles_with_path_filter(&manifest, None, edge_mode, keep_path)`. `edge_mode` defaults to `runtime` (excludes TS type-only edges), matching `fmm cycles`. `keep_path` applies the `include_tests` policy via `Config::is_test_file`, exactly as `crates/fmm-cli/src/cli/commands/cycles.rs` does. Each returned SCC (`Vec<String>` of member paths) becomes one finding; members are evidence.
3. **fan_in_hub** — for each `(path, importers)` in `Manifest.reverse_deps`, if `importers.len() >= ruleset.fan_in_hub_min` emit a finding. Downstream count is exact; this is the same number `fmm ls` reports as `↓ N`.
4. **fan_out_hub** — for each `FileEntry`, count resolved internal forward deps (`FileEntry.dependencies.len()`); if `>= ruleset.fan_out_max` emit a finding.
5. **long_symbol** / **complex_symbol** — collect once with the symbols-spec core collector (`SymbolQuery` over `Manifest.files`, the same path `fmm symbols` uses). `long_symbol`: `SymbolRow.body_loc > ruleset.long_symbol_loc`. `complex_symbol`: `SymbolMetrics.cyclomatic_complexity > ruleset.complexity_max` OR `nesting_depth > ruleset.nesting_depth_max`, **only when the metric is non-null**. One collection pass feeds both categories (no second walk).
6. **duplicate_cluster** — call `find_dupe_clusters(&manifest, &DupeOptions { min_score: ruleset.dupe_min_score, include_tests: ruleset.include_tests, .. })`. Each `DuplicateCluster` with `members.len() >= ruleset.dupe_min_cluster_size` becomes one finding; members are evidence. `dupe_min_score` defaults to the duplication spec's inherited `similarity.rs::DEFAULT_THRESHOLD`.
7. **dead_export** — build the glossary once with `Manifest::build_glossary("", GlossaryMode::Source)` (empty pattern = all exports, source mode = test callers excluded). A `GlossarySource` with empty `used_by` is a **candidate**, then run the discounting heuristic below. Layer-2 `used_by` is **file-level** (`build_glossary` calls `find_dependents(&loc.file)`), so this is a coarse signal → default `confidence: low`. `--verify-dead-exports` runs `apply_call_site_precision` per candidate for symbol-level `used_by` + `reexport_files`, discounting re-exports and raising to `confidence: medium`.
8. **broad_visibility** — join `SymbolRow.visibility == "public"` with `Manifest.reverse_deps[defining_file]` and crate/package membership (`Manifest.workspace_packages` / Rust crate-root prefix). If every importer of the defining file is inside the symbol's own crate, the `pub` could be `pub(crate)`. Heuristic, file-level → `confidence: low`. Phased; see open questions.

## Data model — `results` payload

The full output is the foundations envelope (`FmmReportEnvelope<HealthReport>`). This spec defines `results` only.

```jsonc
{
  "summary": {
    "files_analyzed": 412,
    "symbols_analyzed": 5180,
    "total_findings": 73,
    "by_severity": { "critical": 1, "high": 8, "medium": 41, "low": 23 },
    "by_category": {
      "god_file": 3, "dependency_cycle": 1, "fan_in_hub": 6, "fan_out_hub": 4,
      "long_symbol": 22, "complex_symbol": 0, "duplicate_cluster": 14,
      "dead_export": 18, "broad_visibility": 5
    },
    "by_confidence": { "high": 50, "medium": 0, "low": 23 },
    "degraded": ["complexity_metrics_partial", "duplication_unavailable"]
  },
  "findings": [
    {
      "rule_id": "god_file",
      "category": "god_file",
      "severity": "high",
      "confidence": "high",
      "file": "crates/fmm-cli/src/cli/mod.rs",
      "symbol": null,
      "lines": null,
      "metric": { "name": "file_loc", "value": 719, "threshold": 700 },
      "evidence": "File is 719 LOC, over the 700 threshold.",
      "remediation": "Split into smaller modules; move option structs into cli/commands/*."
    },
    {
      "rule_id": "dependency_cycle",
      "category": "dependency_cycle",
      "severity": "critical",
      "confidence": "high",
      "file": "crates/fmm-core/src/a.rs",
      "symbol": null,
      "lines": null,
      "metric": { "name": "cycle_size", "value": 3, "threshold": 0 },
      "evidence": "Import cycle of 3 files: a.rs -> b.rs -> c.rs -> a.rs (runtime edges).",
      "remediation": "Break the cycle by extracting the shared type or inverting one dependency.",
      "members": ["crates/fmm-core/src/a.rs", "crates/fmm-core/src/b.rs", "crates/fmm-core/src/c.rs"]
    },
    {
      "rule_id": "long_symbol",
      "category": "long_symbol",
      "severity": "medium",
      "confidence": "high",
      "file": "crates/fmm-core/src/parser/builtin/rust/mod.rs",
      "symbol": "RustParser.parse_inner",
      "lines": { "start": 154, "end": 270 },
      "metric": { "name": "body_loc", "value": 117, "threshold": 150 },
      "evidence": "Method body is 117 LOC.",
      "remediation": "Extract cohesive blocks into helpers (CLAUDE.md ~150-line guidance)."
    }
  ]
}
```

### Finding model

The directive's required shape is `{category, severity, confidence, file, lines, evidence, remediation}`. This spec carries those and adds three additive, deterministic fields:

| Field | Type | Notes |
| --- | --- | --- |
| `rule_id` | string | The ruleset rule that produced the finding (enables ruleset toggles + stable tiebreak). |
| `category` | enum | One of the nine category slugs. |
| `severity` | `critical \| high \| medium \| low` | Magnitude-derived (see semantics). |
| `confidence` | `high \| medium \| low` | Signal reliability (see semantics). |
| `file` | string | Primary file path. |
| `symbol` | string \| null | Dotted symbol name for symbol-level findings; null for file-level. |
| `lines` | `{start,end}` \| null | Symbol line range; null for file-level findings. |
| `metric` | `{name, value, threshold}` | The measured number and the rule bound that fired. |
| `evidence` | string | Human-readable justification; category-specific structured fields (`members`) appended where useful. |
| `remediation` | string | Short actionable suggestion. |

`category`-specific evidence extensions: `dependency_cycle` and `duplicate_cluster` add a `members: string[]` (cycle paths / cluster member symbols). `fan_in_hub` adds `top_importers: string[]` (capped, sorted). All such arrays are deterministically sorted.

### Severity semantics (how bad if real — magnitude-derived)

Severity is a deterministic function of how far the measured value exceeds the threshold, so it is reproducible and ruleset-driven, not hardcoded per category:

- `dependency_cycle` → always `critical` (architectural; size scales evidence, not severity).
- Ratio `value / threshold` for magnitude categories: `>= 2.0` → `high`; `>= 1.0` → `medium`; threshold-equal edge cases resolve to `medium`. Categories whose mere presence is the signal (`duplicate_cluster`, `dead_export`, `broad_visibility`) map cluster size / candidate weakness to `medium`/`low`.
- Per-rule `base_severity` and the ratio buckets are part of the ruleset, so a team can retune without code changes.

### Confidence semantics (how sure the signal is real — intrinsic + verification)

- `high` — exactly measured structural facts that cannot be false positives: `god_file` (LOC is exact), `dependency_cycle` (graph-proven), `fan_in_hub`/`fan_out_hub` (exact edge counts), `long_symbol` (`body_loc` exact).
- `medium` — heuristic but calibrated: `duplicate_cluster` (scorer-derived), `complex_symbol` (parser-derived, present), `dead_export` **with** `--verify-dead-exports` (call-site precision applied).
- `low` — heuristic and coarse: `dead_export` without verification (file-level `used_by`; library public API + dynamic dispatch invisible), `broad_visibility` (file-level crate-membership join).

Confidence is independent of severity: a dead export can be `high` severity (large unused symbol) yet `low` confidence (might be a public API entry point). Consumers filter on both.

### Dead-export discounting heuristic (required detail)

A candidate (`GlossarySource.used_by` empty after `build_glossary`) is **discarded** or **down-weighted** when it matches any of:

1. **Re-export** — present in `GlossarySource.reexport_files` (Layer 3 only) or marked as a re-export via the manifest's reexport sidecar. Re-exports are impacted by rename and are not dead. **Discard.**
2. **Public API** — `visibility == "public"` AND defined in a crate-root surface module (`lib.rs`, crate-root `mod.rs`) or matching a configured `public_api_allowlist` glob. Library crates legitimately have no in-repo callers. **Discard by default**; configurable.
3. **Test-only** — symbol in a test file or test export (`is_test_export`). Already excluded when `include_tests=false` (the default); included only under `include_tests=true` and then tagged `confidence: low`.
4. **Dynamic dispatch / entrypoint** — invisible call sites fmm cannot resolve: trait-method impls (`relationship_kind` set), `main`/binary entrypoints, `#[no_mangle]`/`extern` exports, derive- or macro-generated symbols, and serde/registry-driven names. **Discard** the known-dynamic kinds; for the rest, cap at `confidence: low`.

Confidence ceiling for `dead_export` is **`medium`** even verified — dynamic dispatch remains structurally invisible to a static index. Never `high`.

### Summary rollup

`summary` carries counts by severity, category, and confidence; `files_analyzed`; `symbols_analyzed`; and `degraded[]` (graceful-degradation tags, mirrored into envelope `diagnostics`). **No single composite 0–100 "health score" in v1** — see open question O-health-1. Ranking replaces a scalar score.

### Ranking (the "ranked report")

Findings are emitted in a deterministic rank so the worst surfaces first:

1. `severity` descending (`critical > high > medium > low`).
2. `confidence` descending (`high > medium > low`).
3. `metric.value / metric.threshold` descending (magnitude; cycles use member count).
4. Stable tiebreakers: `category` ascending, `file` ascending, `symbol` ascending (null last), `lines.start` ascending (null last), `rule_id` ascending.

This ordering is also the JSON serialization order → double-run byte equality holds.

## Ruleset / threshold config

Thresholds resolve to defaults, carry into envelope `params` (key-sorted), and override via `--ruleset`. Defaults **reuse the map spec's resolved thresholds** (Wave A synthesis O-map-2) and repo conventions for consistency:

```rust
pub struct HealthRuleset {
    pub god_file_loc: usize,        // default 700  (CLAUDE.md hard limit; map O-map-2)
    pub long_symbol_loc: u32,       // default 150  (CLAUDE.md function guidance)
    pub fan_in_hub_min: usize,      // default 10   (map O-map-2 hub min-downstream)
    pub fan_out_max: usize,         // default 20   (propose; calibrate on fixtures)
    pub complexity_max: u16,        // default 15   (cyclomatic; applied only when present)
    pub nesting_depth_max: u16,     // default 5    (applied only when present)
    pub dupe_min_score: f64,        // default similarity.rs::DEFAULT_THRESHOLD (duplication spec)
    pub dupe_min_cluster_size: usize, // default 2
    pub include_tests: bool,        // default false
    pub severity_threshold: Severity, // default Low (report everything)
    pub top_k_per_category: usize,  // default 20   (map O-map-2 top-K cap)
    pub categories: Option<Vec<Category>>, // None = all nine
    pub public_api_allowlist: Vec<String>, // globs discounted from dead_export
}
```

`--ruleset` accepts a path to a TOML overriding any subset; unspecified keys keep defaults. Defaults are the single source of truth in `health.rs`; `tools.toml`/help docs reference them, never re-hardcode. The resolved ruleset is echoed in envelope `params` so a report is self-describing and reproducible.

## CLI surface

```text
fmm health [<paths>...]
           [--include-tests]
           [--ruleset <file>]
           [--severity-threshold <critical|high|medium|low>]
           [--category <cat>]...        # repeatable; default all nine
           [--top <n>]                  # per-category cap; default 20
           [--verify-dead-exports]      # Layer-3 call-site precision (slower)
           [--json]
```

- `<paths>` — in-memory path-prefix scope filter over the loaded index (map O-map-3 pattern; no scoped re-generate). Whole-repo maps to `scope_digest="root"`.
- Text output is a compact, ranked, grouped report (by severity then category) using a new `crates/fmm-core/src/format/health.rs` formatter (mirrors `format::format_dependency_cycles`). `--json` emits the foundations envelope.

## MCP surface

Add `tools.fmm_health_report` to `crates/fmm-cli/tools.toml` so `build.rs` regenerates the MCP schema, CLI help, and skill docs. Dispatch in `crates/fmm-cli/src/mcp/mod.rs::McpServer.handle_tool_call`, module export in `crates/fmm-cli/src/mcp/tools/mod.rs`, implementation in new `crates/fmm-cli/src/mcp/tools/health.rs` (mirrors `mcp/tools/cycles.rs`). MCP returns the serialized envelope in the existing text-content wrapper.

Params mirror the CLI as flat scalars (tools.toml params are flat): `directory?: string`, `include_tests?: boolean`, `severity_threshold?: enum`, `category?: string | string[]`, `top?: number`, `verify_dead_exports?: boolean`, plus discrete optional threshold overrides (`god_file_loc?`, `long_symbol_loc?`, `fan_in_hub_min?`, `fan_out_max?`, `complexity_max?`, `nesting_depth_max?`, `dupe_min_score?`). A file-path `--ruleset` is CLI-only; over MCP the discrete overrides replace it (see O-health-2).

## Graceful degradation (required)

Health degrades per-signal and records the loss; it never aborts because one signal is unavailable.

- **Complexity metrics absent / partial** — `SymbolMetrics.cyclomatic_complexity` / `nesting_depth` are null for unsupported grammars/symbols (symbols spec is phased). `complex_symbol` simply skips null-metric symbols and emits `degraded: ["complexity_metrics_partial"]`. `long_symbol` is unaffected (`body_loc` is near-universal).
- **`body_loc` absent (pre-v7 index)** — if `SymbolRow.body_loc` is null but `lines` exist, derive `end - start + 1` on the fly; emit `degraded: ["body_loc_derived"]`. No hard dependency on the v7 metric columns.
- **Duplication unavailable** — if `find_dupe_clusters` is not present (health run before duplication Tier 1 ships) or returns an error, skip `duplicate_cluster` and emit `degraded: ["duplication_unavailable"]`. All other categories still report.
- **Empty / missing index** — same warning path as `fmm cycles`/`fmm glossary` (`warn_no_sidecars` / "Run fmm generate first").

Each `degraded` tag is mirrored into the envelope `diagnostics[]` as a structured item per foundations D4.

## Traceability (field → file + symbol)

| Result field / signal | Source of truth (file::symbol) |
| --- | --- |
| Envelope wrapper | foundations `FmmReportEnvelope`, shared `print_envelope` helper |
| `god_file` LOC | `crates/fmm-core/src/manifest/file_entry.rs::FileEntry` (`loc`), `crates/fmm-core/src/manifest/mod.rs::Manifest` (`files`) |
| `dependency_cycle` | `crates/fmm-core/src/search/dependency_cycles.rs::dependency_cycles_with_path_filter`; edge mode `crates/fmm-core/src/graph/cycles.rs::CycleEdgeMode` |
| `fan_in_hub` | `crates/fmm-core/src/manifest/reverse_index.rs::ReverseDeps`, `crates/fmm-core/src/manifest/mod.rs::Manifest` (`reverse_deps`) |
| `fan_out_hub` | `crates/fmm-core/src/manifest/file_entry.rs::FileEntry` (`dependencies`) |
| `long_symbol` / `complex_symbol` | symbols `crates/fmm-core/src/symbols.rs::SymbolQuery`/`SymbolRow`; `crates/fmm-core/src/parser/types.rs::SymbolMetrics` |
| `duplicate_cluster` | duplication `crates/fmm-core/src/similarity.rs::find_dupe_clusters`, `DupeOptions`, `DupeClustersResult` |
| `dead_export` candidate | `crates/fmm-core/src/manifest/glossary_builder.rs::Manifest::build_glossary`, `GlossarySource` (`used_by`) |
| `dead_export` verified | `crates/fmm-cli/src/glossary.rs::apply_call_site_precision`, `GlossarySource` (`reexport_files`) |
| `broad_visibility` | `crates/fmm-core/src/manifest/file_entry.rs::SymbolMetadata` (`visibility`) + `Manifest` (`reverse_deps`, `workspace_packages`) |
| Test classification | `crates/fmm-core/src/config` `Config::is_test_file` / `crates/fmm-core/src/manifest` `is_test_export` |
| Core composer | new `crates/fmm-core/src/health.rs::analyze_health` |
| Text formatter | new `crates/fmm-core/src/format/health.rs` |
| CLI command | new `crates/fmm-cli/src/cli/commands/health.rs`; enum `crates/fmm-cli/src/cli/mod.rs::Commands`; dispatch `crates/fmm-cli/src/main.rs::run_command` |
| MCP tool | new `crates/fmm-cli/src/mcp/tools/health.rs`; dispatch `crates/fmm-cli/src/mcp/mod.rs::McpServer.handle_tool_call`; schema `crates/fmm-cli/tools.toml` + `crates/fmm-cli/build.rs` (`generate_mcp_schema`, `generate_cli_help`, `generate_skill_md`) |

## Tests / verification gate

Repo convention (`~/.mdx/projects/fmm-roadmap-spec-foundations.md`): `just check` (fmt + clippy), `just test` (nextest), never `cargo test`.

1. **Composition, not recomputation** — `analyze_health` god-file count equals files in `Manifest.files` with `loc > threshold`; cycle findings equal `dependency_cycles_with_path_filter` SCCs over the same fixture (assert identical member sets).
2. **Determinism** — double-run byte equality on `--json` over a fixture; ranking is stable under HashMap iteration order (the finding order must not depend on `Manifest.files`/`reverse_deps` traversal order).
3. **Ruleset** — thresholds echoed in envelope `params`; an overriding `--ruleset` changes which findings fire; `severity_threshold` filters correctly.
4. **Severity / confidence** — ratio buckets map to expected severities; `god_file` is `high` confidence, unverified `dead_export` is `low`.
5. **Dead-export heuristic** — fixture with (a) a truly-unused private-ish export → candidate; (b) a re-export → discarded; (c) a crate-root public API symbol → discarded by default; (d) a trait-impl method → discarded. `--verify-dead-exports` raises a true candidate to `medium`.
6. **Graceful degradation** — null complexity metrics skip `complex_symbol` and set `degraded`; absent duplication sets `duplication_unavailable` and still reports other categories; pre-v7 index derives `body_loc` from lines.
7. **CLI text** — ranked grouped output is deterministic on a fixture.
8. **MCP** — `fmm_health_report` over the same fixture matches CLI findings; `tools.toml` schema snapshot updates.

## Build order (within health, Wave B)

0. (Prerequisite, Slice 0) `cli/mod.rs` refactor + Wave A symbols + duplication Tier 1 landed.
1. `HealthRuleset`, `Severity`, `Category`, `Finding`, `HealthReport` types in `crates/fmm-core/src/health.rs`.
2. `analyze_health` composing index-only signals (god_file, cycles, fan_in/out) + ranking + summary. Tests 1–4.
3. Wire symbols collector (`long_symbol`, `complex_symbol`) and `find_dupe_clusters` (`duplicate_cluster`) with degradation. Test 6.
4. Layer-2 `dead_export` + `broad_visibility` candidates in core; discounting heuristic. Test 5 (a–c).
5. Text formatter `crates/fmm-core/src/format/health.rs`. Test 7.
6. CLI `fmm health` (command struct, `run_command` dispatch) + JSON envelope.
7. `--verify-dead-exports` CLI enrichment via `apply_call_site_precision`. Test 5 (d + verify).
8. MCP `fmm_health_report` via `tools.toml`, dispatch, `mcp/tools/health.rs`. Test 8.

## Open questions

- **O-health-1 (biggest):** Should v1 emit a single composite 0–100 "health score", or only ranked findings + counts? A scalar invites arbitrary category weighting and false precision; ranking + `by_severity`/`by_confidence` counts is defensible and reproducible. **Recommend: no scalar score in v1.** Needs the user/orchestrator's call because it shapes the summary contract and how agents consume it.
- **O-health-2:** Ruleset over MCP — discrete optional scalar overrides (this spec's default) vs an inline ruleset object vs a named-preset string. Recommend discrete overrides for v1 (flat tools.toml params), preset names deferred.
- **O-health-3:** Does `broad_visibility` belong in v1? It is the lowest-confidence, most heuristic signal (file-level reverse_deps + crate-membership guess) and risks noise. Recommend shipping it behind a `--category broad_visibility` opt-in (off by default) until calibrated, or deferring to v1.1.
- **O-health-4:** `--verify-dead-exports` re-reads files per candidate (Layer-3 cost). Acceptable for an explicit opt-in flag; confirm it should not run by default. Recommend opt-in only.
- **O-health-5:** `fan_out_max` default (proposed 20) and `complexity_max`/`nesting_depth_max` defaults need fixture calibration before v1 ships; do not block the contract on exact numbers.
