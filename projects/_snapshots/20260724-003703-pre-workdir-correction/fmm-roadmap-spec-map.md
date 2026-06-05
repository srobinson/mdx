---
title: fmm Roadmap — `fmm map` Capability Spec
type: spec
tags: [fmm, roadmap, map, codebase-map, aggregator, mcp, json-contract, capability]
summary: Spec for `fmm map` CLI command + `fmm_codebase_map` MCP tool — a structural aggregator that emits a deterministic, commit-able MAP.md skeleton (markdown) or the foundations JSON envelope, composing existing core primitives. fmm stays "index, not author".
status: draft
source: codebase-analyst (warroom fmm-spec2-capabilities)
confidence: high
repo: /Users/alphab/Dev/LLM/DEV/helioy/fmm
head: 5f8a1296d72f507a2e4bd1950001a442dc6b31fc
fmm_version: 0.3.6
index_schema_version: 6
builds_on: ~/.mdx/projects/fmm-roadmap-spec-foundations.md
created: 2026-06-17
updated: 2026-06-17
---

# `fmm map` — codebase map aggregator

Builds on the **canonical foundations contract** (`~/.mdx/projects/fmm-roadmap-spec-foundations.md`). This spec **cites** the foundations envelope, `git_sha`/index-metadata stamp, and determinism rules; it never redefines them. All code anchors verified against HEAD `5f8a129`, `fmm 0.3.6`, index schema v6, via `fmm_*` tools.

## 1. Purpose and positioning

`fmm map` is an **aggregator**, not an author. Today an agent assembles MAP.md from ~7-10 separate calls (`ls --group-by`, `ls --sort-by downstream`, `ls --sort-by loc`, `exports`, `dependency_cycles`, plus workspace/topology). `fmm map` collapses those into **one** call that returns the structural model an agent turns into MAP.md prose.

Two outputs from one aggregation:

- **markdown** (default): a deterministic, commit-able **skeleton** — fmm-generated tables/sections plus explicit narrative placeholders the agent fills. fmm generates the facts; the agent writes the story. This preserves fmm's "index, not author" positioning (README).
- **json**: the foundations `FmmReportEnvelope<CodebaseMapResult>` (cited from foundations D4), for programmatic consumers and deterministic two-run byte-diffing.

**Non-goals:** no narrative generation, no pattern/idiom classification, no file writes (fmm never writes source; the agent redirects stdout if it wants `MAP.md` on disk), no git-history walk (explicit fmm non-goal). Duplication audit (`fmm dupes`), structural diff (`fmm diff`), and health digest (`fmm health`) are **separate** capability specs.

## 2. DRY — primitives composed (never reimplemented)

`fmm map` is **mostly composition**. Every section reuses an existing core path. Traceability is expressed as `field/section -> file::symbol` (no line numbers, per the brief).

| Map section | Reused primitive (`file::symbol`) | Notes |
|---|---|---|
| Per-directory topology (file count, LOC) | `crates/fmm-core/src/format/list_formatters.rs::compute_rollup_buckets` | The exact engine behind `fmm ls --group-by subdir`. Returns `Vec<(bucket, file_count, loc)>`. Map calls it with `prefix=None`, deterministic sort. |
| Per-file entries (loc, exports, downstream, kind) | `crates/fmm-cli/src/cli/commands/ls.rs::collect_entries` | Currently CLI-private; see **O-map-5** (lift to a shared core helper so `ls` + `map` share one path). |
| God-files / LOC | `crates/fmm-core/src/manifest/file_entry.rs::FileEntry` (`.loc` field) | Per-file LOC is stored, not recomputed. Source of `ls --sort-by loc`. |
| Architectural hubs (downstream / blast radius) | `crates/fmm-core/src/manifest/mod.rs::Manifest` (`.reverse_deps` field) | Source of `ls --sort-by downstream`. Top-K by direct dependents. |
| Public API surface (top exports) | `Manifest::export_index` + `FileEntry::exports` + `FileEntry::export_metadata` (`SymbolMetadata.visibility`/`.declaration_kind`) | Source of `exports` / `fmm_list_exports`. Filter `visibility == public`. |
| Dependency seams + cycle summary | `crates/fmm-core/src/search/dependency_cycles.rs::dependency_cycles(manifest, file, edge_mode)` (returns `Vec<Vec<String>>` of file-path SCCs; builds the `GraphIndex` internally; `dependency_cycles_with_path_filter` for `paths` scoping; `CycleEdgeMode` from `crate::graph::cycles`) | The **exact** entrypoint `cycles` / `tool_dependency_cycles` call. Map must reuse it, not the low-level `graph::GraphIndex::from_manifest` Tarjan path. |
| Workspace packages | `Manifest::workspace_packages`, `Manifest::workspace_packages_by_ecosystem`, `Manifest::workspace_roots` (set by `Manifest::set_workspace_info`) | Ecosystem-aware (`WorkspaceEcosystem`). |
| Source/test split | `crates/fmm-core/src/manifest/test_classification.rs` + the `ls` `filter` classification | `include_tests=false` ⇒ source-only (production view), matching `ls --filter source`. |
| `git_sha` + index-metadata stamp | **Foundations envelope** (`Store::write_meta` KV: `git_sha`/`git_branch`/`git_dirty`/`generated_at`/`version`/`index_schema_version`) | **Cited, not redefined.** Map embeds the stamp in its envelope header (json) or HTML-comment header (markdown). |
| Manifest load (CLI) | `crates/fmm-cli/src/cli/commands/mod.rs::load_manifest` | Existing private `() -> Result<(PathBuf, Manifest)>`. No new load path. |
| Manifest (MCP) | server-loaded `&Manifest` arg, exactly like `crates/fmm-cli/src/mcp/tools/cycles.rs::tool_dependency_cycles` | No new load path. |
| Envelope assembly | Foundations shared `print_envelope` / `FmmReportEnvelope<T>` (`contract.rs`/`report.rs`) | **DRY seam — reject per-command envelope assembly** (foundations build-order item 2). |

New code is only: the aggregation orchestrator, the markdown renderer, the CLI/MCP entry points, and the tool declaration. Each is listed in §6.

## 3. Inputs

CLI flags and MCP params are codegen'd from one `tools.toml` block (§7); they stay 1:1 (CLI/MCP parity, `~/.mdx/projects/fmm-cli-mcp-parity.md`).

| Input | Type | Default | Meaning |
|---|---|---|---|
| `paths` | `Vec<String>` (CLI positional; MCP `paths`) | indexed root | Scope filter applied **in-memory** to the loaded Manifest by path prefix (the index is whole-repo; map does not re-`generate`). Empty ⇒ canonical `"root"` scope. |
| `format` | enum `markdown` \| `json` | `markdown` | `markdown` ⇒ skeleton; `json` ⇒ foundations envelope. |
| `include_tests` | bool | `false` | Include test files in topology/totals/API surface. Off = production view. |
| `max_symbols_per_file` | usize | `10` | Cap on exports listed per file/dir in the API-surface section (0 = unbounded). |
| `include_cycles` | bool | `true` | Emit the dependency-cycle summary. |
| `include_hotspots` | bool | `true` | Emit hubs (downstream) + god-files (loc) sections. |

Thresholds (god-file LOC, hub min-downstream, top-K) are **resolved defaults** carried in the envelope `params` (foundations: "sorted params, defaults resolved"). Proposed defaults in **O-map-2**.

## 4. JSON results shape (`CodebaseMapResult`)

Wrapped by the foundations envelope (cited from foundations D4 — reproduced for the `results` slot only):

```jsonc
// FmmReportEnvelope<CodebaseMapResult>.results :
{
  "scope": {
    "paths": ["."],            // normalized, sorted
    "include_tests": false,
    "scope_digest": "root"     // foundations D3 scope_digest; "root" when whole-repo
  },
  "totals": {
    "files": 416, "loc": 63978,
    "source_files": 393, "test_files": 23,
    "exports": 1234, "workspace_packages": 2
  },
  "directories": [             // compute_rollup_buckets; sort: path asc
    { "path": "crates/fmm-core/src/parser", "files": 71, "loc": 15000 }
  ],
  "workspace_packages": [      // sort: ecosystem asc, name asc
    { "name": "fmm-core", "ecosystem": "cargo", "root": "crates/fmm-core" }
  ],
  "hubs": [                    // reverse_deps; sort: downstream desc, path asc; top-K
    { "file": "crates/fmm-core/src/parser/mod.rs", "downstream": 82, "loc": 600, "exports": 12 }
  ],
  "hotspots": [                // FileEntry.loc; sort: loc desc, path asc; loc > threshold
    { "file": "crates/fmm-cli/src/cli/mod.rs", "loc": 719, "exports": 34, "downstream": 7 }
  ],
  "api_surface": [             // sort: directory asc; exports sort: name asc; max_symbols_per_file
    { "directory": "crates/fmm-core",
      "exports": [ { "name": "Manifest", "kind": "struct", "visibility": "public",
                     "file": "crates/fmm-core/src/manifest/mod.rs" } ] }
  ],
  "cycles": {                  // search::dependency_cycles; sort: size desc, first-member path asc
    "count": 4,
    "summary": [ { "size": 3, "members": ["a","b","c"] } ]  // capped (O-map-2)
  }
}
```

**Determinism (foundations mandate).** Every array carries an explicit total order with a stable tiebreaker (above). No query wall-clock: `generated_at` comes from the index meta (foundations D6 no-op stability), never `Utc::now()`. Two `fmm map --json` runs at the same `git_sha` over an unchanged index produce **byte-identical** envelopes — the gate is double-run byte equality (foundations Tests/gate).

Empty sections are present-but-empty (`[]` / `{count:0,summary:[]}`), never omitted, so the shape is stable across repos.

## 5. Markdown skeleton (deterministic, commit-able)

Default CLI output. fmm owns the tables; the agent owns prose. The boundary is explicit `<!-- fmm:narrative ... -->` placeholders; everything else is fmm-generated and byte-stable.

```markdown
<!-- fmm:map contract_version=1 git_sha=5f8a129 git_branch=main git_dirty=false
     index_schema_version=6 fmm_version=0.3.6 generated_at=2026-06-04T15:51:31+00:00 -->
# Codebase Map

<!-- fmm:narrative section="overview" — author 1-3 sentences on what this codebase is -->

## Overview
- 393 source files (+23 test) · 63,978 LOC
- Workspace: `fmm-core`, `fmm-cli` (cargo)
- git: `main` @ `5f8a129` (clean)

## Topology
| Directory | Files | LOC |
| --- | ---: | ---: |
| crates/fmm-core/src/parser | 71 | 15,000 |
| crates/fmm-core/src/manifest | 35 | 6,487 |

## Architectural Hubs (highest blast radius)
| File | Downstream | LOC |
| --- | ---: | ---: |
| crates/fmm-core/src/parser/mod.rs | 82 | 600 |

## God-files (LOC > 700)
| File | LOC | Exports |
| --- | ---: | ---: |
| crates/fmm-cli/src/cli/mod.rs | 719 | 34 |

## Public API Surface
### crates/fmm-core
- `Manifest` — struct (pub)
- `FileEntry` — struct (pub)

## Dependency Cycles
4 cycles. Largest size 3: `a` → `b` → `c` → `a`.

<!-- fmm:narrative section="closing" — author component responsibilities + seams -->
```

The HTML-comment header carries the same stamp the json envelope carries (`contract_version`, `git_sha`, `generated_at`, …), so a committed `MAP.md` is self-describing and a reviewer can tell which commit it reflects. Section visibility honors `include_cycles` / `include_hotspots`.

## 6. Code placement (new code only)

| Component | New `file::symbol` | Mirrors existing |
|---|---|---|
| Aggregation orchestrator (core) | `crates/fmm-core/src/map/mod.rs::build_codebase_map(manifest, graph, options) -> CodebaseMapResult` | new module; pure composition, fully unit-testable in core |
| Result types (core) | `crates/fmm-core/src/map/mod.rs::{CodebaseMapResult, MapDirectory, MapHub, MapExport, MapCycleSummary, MapOptions}` | `serde::Serialize` like `commands/ls.rs::ListFileJson` |
| Markdown renderer (core) | `crates/fmm-core/src/format/map_formatters.rs::format_codebase_map_markdown(&CodebaseMapResult) -> String` | `format/list_formatters.rs::format_list_files_rollup` pattern |
| CLI command | `crates/fmm-cli/src/cli/commands/map.rs::map(paths, format, include_tests, max_symbols_per_file, include_cycles, include_hotspots) -> Result<()>` | `commands/cycles.rs::cycles` shape; loads via `commands/mod.rs::load_manifest` |
| CLI dispatch | `Map` variant on the clap `Commands` enum + match arm in `crates/fmm-cli/src/cli/mod.rs`; `mod map;` + re-export in `crates/fmm-cli/src/cli/commands/mod.rs` | every other `commands/*` entry |
| MCP tool | `crates/fmm-cli/src/mcp/tools/map.rs::tool_codebase_map(manifest, root, args) -> Result<String, String>` | `mcp/tools/cycles.rs::tool_dependency_cycles` exactly |
| MCP wiring | `mod map;` + re-export `tool_codebase_map` in `crates/fmm-cli/src/mcp/tools/mod.rs`; dispatch arm in `crates/fmm-cli/src/mcp/mod.rs` | existing tool registration |
| Tool declaration | `[tools.fmm_codebase_map]` block in `crates/fmm-cli/tools.toml` | §7 |
| Envelope | reuse foundations `print_envelope` / `FmmReportEnvelope<T>` | **do not** hand-assemble |

Keeping `build_codebase_map` in **core** (not the CLI) lets both the CLI command and the MCP tool call one tested function; the CLI adds only flag plumbing + format dispatch. No new file exceeds the 700-LOC limit (CLAUDE.md); `cli/mod.rs` is already at 719 and must be refactored before the `Map` variant is added there (CLAUDE.md hard rule — flag in **O-map-6**).

## 7. MCP additions via `tools.toml`

New tools/flags are codegen'd: editing `tools.toml` regenerates `src/mcp/generated_schema.rs`, `src/cli/generated_help.rs`, and `templates/SKILL.md` via `build.rs` (foundations convergence + tools.toml header). The block mirrors the existing `[tools.fmm_dependency_cycles]` / `[tools.fmm_list_files]` shape:

```toml
[tools.fmm_codebase_map]
description = "One-call structural digest for authoring a codebase MAP.md: per-directory topology, hubs, god-files, public API surface, dependency cycles, workspace packages, git/index stamp. Returns a deterministic markdown skeleton or the JSON envelope. fmm indexes; you author the narrative."

[[tools.fmm_codebase_map.params]]
name = "paths"
# array<string>, optional; in-memory scope filter, default whole index

[[tools.fmm_codebase_map.params]]
name = "format"
# "markdown" (default) | "json"

[[tools.fmm_codebase_map.params]]
name = "include_tests"   # bool, default false

[[tools.fmm_codebase_map.params]]
name = "max_symbols_per_file"  # int, default 10

[[tools.fmm_codebase_map.params]]
name = "include_cycles"  # bool, default true

[[tools.fmm_codebase_map.params]]
name = "include_hotspots"  # bool, default true
```

Also add a `## Codebase Map` stanza to the `[skill]` workflow so agents reach for `fmm_codebase_map` first when onboarding ("Orient me / map this repo").

MCP default `format` is `markdown` (the skeleton an authoring agent consumes); `format:"json"` returns the envelope. Existing MCP tools return text/YAML, so markdown-by-default is consistent.

## 8. Resolved: O2 — `fmm_status` MCP tool ships **with map**

Foundations O2 deferred to this spec the question of whether the `fmm_status` MCP tool ships in foundations or with map; both drafts leaned "with map." **Decision: ship `fmm_status` with map.** Rationale:

- Foundations gives `fmm status` (CLI) a git/index-metadata section + `--json` envelope, but there is **no `fmm_status` MCP tool today** (the 10 MCP tools omit status; `status` is a project command). The map-authoring agent works over MCP and needs the stamp + freshness without shelling to the CLI.
- `fmm_status` is a thin wrapper over the same `status --json` envelope foundations defines — `crates/fmm-cli/src/mcp/tools/status.rs::tool_status(root, args)`, declared as `[tools.fmm_status]` in `tools.toml`, wired like every other tool. Shipping it in the same phase as `fmm_codebase_map` restores CLI/MCP parity (`~/.mdx/projects/fmm-cli-mcp-parity.md`) in one stroke.
- Division of labor: `fmm_codebase_map` embeds the stamp in its own header so a caller that wants the digest needs only one call; `fmm_status` is the **cheap** freshness/staleness probe (indexed-vs-source counts, drift, git stamp) without paying for a full aggregation. Distinct jobs, same capability phase.
- `tool_status` does **not** require a Manifest (current `status` queries the index DB directly via `fmm_store::open_db`), so it is a lighter wiring than `fmm_codebase_map`.

## 9. Tests / gate

Per repo convention: `just test` (nextest, **never** `cargo test`) + `just check` (fmt + clippy). Key assertions:

- **Double-run byte equality** for `fmm map --json` and for the markdown skeleton over an unchanged index (the foundations determinism gate, applied to map).
- Composition fidelity: `map` topology equals `ls --group-by subdir` rollups (same `compute_rollup_buckets`); `map` hubs equal `ls --sort-by downstream` top-K; `map` cycles equal `dependency_cycles` — proves no reimplementation drift.
- `include_tests` toggles source/test totals; `paths` scoping filters the in-memory Manifest correctly; empty sections render as present-but-empty.
- Stamp round-trip: markdown header and json envelope carry the same `git_sha`/`generated_at` the foundations meta holds.
- CLI/MCP parity: `fmm map --json` results equal `fmm_codebase_map(format:"json")` results.

## 10. Open questions (flagged, not guessed)

- **O-map-1 (biggest).** Is the committed artifact the **skeleton itself** (the agent edits `fmm map > MAP.md` in place, filling `fmm:narrative` placeholders, and commits it) or a **read-only digest** the agent consumes to author MAP.md elsewhere? This drives whether the markdown carries narrative placeholders at all and how "commit-able" is defined. Recommendation: print to stdout only (fmm never writes files); "commit-able" = deterministic bytes suitable to redirect-and-commit; placeholders included. **Needs user confirmation.**
- **O-map-2.** Default thresholds: god-file LOC (propose 700, matching repo CLAUDE.md), hub min-downstream (propose ≥10), top-K hubs/hotspots (propose 20), cycle-summary cap (propose 20, largest-first). Carry all in envelope `params`.
- **O-map-3.** `paths` scoping by in-memory Manifest prefix-filter vs. requiring a scoped `generate`. Recommendation: in-memory filter (the index is whole-repo, filtering is cheap and avoids re-indexing); reconcile with foundations D3 `scope_digest`.
- **O-map-4.** "Public API surface" for non-Rust: include only `visibility == public`, or also `crate`/package-internal? Visibility domain is `public/crate/protected/private/non_exported` (`SymbolMetadata.visibility`). Recommendation: `public` only by default.
- **O-map-5 (DRY).** Lift `commands/ls.rs::collect_entries` into a core `manifest`-level helper so `ls` and `map` share the per-file entry path instead of two collectors over the same fields. Recommended as part of this build.
- **O-map-6 (blast radius).** `cli/mod.rs` is already 719 LOC (over the 700 hard limit); the `Map` clap variant cannot be added until it is refactored first (CLAUDE.md "refactor before adding"). Sequence the refactor ahead of map wiring.
