---
title: fmm Roadmap Lint Architecture Spec
type: spec
tags: [fmm, roadmap, lint, architecture, rules, config, mcp, json_contract]
summary: Defines fmm lint-architecture as a deterministic architecture rule engine over the existing dependency graph and .fmmrc.toml config.
status: draft
source: backend-engineer
confidence: high
repo: /Users/alphab/Dev/LLM/DEV/helioy/fmm
head: 5f8a1296d72f507a2e4bd1950001a442dc6b31fc
fmm_version: 0.3.6
created: 2026-06-17
updated: 2026-06-17
inputs:
  - ~/.mdx/projects/fmm-roadmap-spec-foundations.md
  - ~/.mdx/projects/fmm-roadmap-spec-wave-a-synthesis.md
  - ~/.mdx/projects/fmm-roadmap-spec-symbols.md
---

# fmm lint architecture spec

`fmm lint-architecture` is a deterministic rule engine over two inputs:

1. The loaded fmm manifest and dependency graph.
2. An architecture section in the existing `.fmmrc.toml` config path.

It reports architecture violations for layers, dependency allowlists, cycles, size limits, generated code exemptions, missing owners, and missing entrypoint annotations. CLI and MCP share one core engine.

## Grounding

* The foundations spec is binding for the report envelope, deterministic JSON, generated metadata, and `tools.toml` as the source of truth for new tools and flags.
* The Wave A synthesis is binding on build order. `crates/fmm-cli/src/cli/mod.rs::Commands` is already 719 LOC, over the repo limit, so Slice 0 must split that CLI declaration before adding this command.
* The Wave A synthesis is also binding on wrapper shape. New CLI commands and MCP tools must call one tested core helper, not duplicate rule logic.
* The symbols spec is binding for `body_loc`. Symbol size checks depend on `SymbolMetrics.body_loc`; if this command lands before symbols, the symbol size rule must be disabled with a diagnostic rather than infer size from labels or signature text.
* Current code already has the needed graph substrate. `GraphIndex::from_manifest` builds typed edges from `build_dependency_edges`, `Edge` carries `EdgeKind`, `GraphIndex` exposes node and edge accessors, and `dependency_cycles_with_path_filter` returns deterministic path cycles.
* Current config loading lives in `crates/fmm-core/src/config`. Extend this module. Do not add a second config parser.

## Current code facts

* `crates/fmm-core/src/config/mod.rs::Config` loads `.fmmrc.toml` from `Config::load_from_dir` and applies environment overrides through `loader::apply_env_overrides`.
* `crates/fmm-core/src/config/loader.rs::FileConfig` is the deserialized file config seam, and `loader::apply_file_config` merges optional file values into `Config`.
* `crates/fmm-core/src/graph/mod.rs::GraphIndex` builds node and edge arrays from `Manifest` and exposes `node_count`, `file_id_for_node`, `path_for_file_id`, `downstream_edges`, and `upstream_edges`.
* `crates/fmm-core/src/identity/mod.rs::EdgeKind` currently distinguishes `Runtime` and `TypeOnly`.
* `crates/fmm-core/src/search/dependency_cycles.rs::dependency_cycles_with_path_filter` already composes `GraphIndex` with a path filter and cycle edge mode.
* `crates/fmm-core/src/manifest/file_entry.rs::FileEntry` carries file `loc`, dependencies, dependency kinds, and symbol metadata maps.
* `crates/fmm-core/src/manifest/mod.rs::Manifest` carries `files`, `reverse_deps`, and identity backed path maps.
* `crates/fmm-cli/src/cli/commands/cycles.rs::cycles` shows the current pattern for loading a manifest, parsing edge mode, applying config backed test filtering, and producing text or JSON.
* `crates/fmm-cli/src/cli/sidecar.rs::validate` exits nonzero on stale or missing index data. `lint-architecture --ci` should use the same failure posture for violations.
* `crates/fmm-cli/src/mcp/mod.rs::McpServer.handle_tool_call` dispatches MCP tools after loading a manifest and returns tool output as text content. This command can follow that model.
* `crates/fmm-cli/tools.toml` generates MCP schema, CLI help, and skill documentation. Add the tool there first.

## Architecture config

Add an optional `architecture` field to `Config`. All nested fields default to empty or disabled so existing `.fmmrc.toml` files keep working.

```rust
pub struct Config {
    pub languages: BTreeSet<String>,
    pub test_patterns: TestPatterns,
    pub max_lines: usize,
    pub exclude: Vec<String>,
    pub architecture: ArchitectureConfig,
}
```

Use the existing file path: `<repo>/.fmmrc.toml` loaded through `Config::load_from_dir(root)`. Add a strict load path inside the same config module for `lint-architecture`, because CI lint must not silently pass when architecture config has a parse or validation error. Keep the current lenient behavior for existing commands unless a broader config change is approved.

Recommended implementation shape:

* Add `ArchitectureConfig` and nested structs in `crates/fmm-core/src/config`.
* Add matching optional fields to `FileConfig`.
* Refactor config loading behind one shared private loader so `Config::load_from_dir` and a new strict architecture load path share parsing and merge logic.
* No environment overrides for architecture rules in v1. Existing `FMM_MAX_LINES`, `FMM_LANGUAGES`, and `FMM_EXCLUDE` remain unchanged.
* Validate unique ids, nonempty glob lists, known severities, known rule names, and references to existing layer or owner ids.

### TOML shape

```toml
[architecture]
enabled = true

# Exempt generated artifacts from all architecture rules by default.
generated_paths = [
  "crates/fmm-cli/src/mcp/generated_schema.rs",
  "crates/fmm-cli/src/cli/generated_help.rs",
  "crates/fmm-cli/templates/SKILL.md",
]

[[architecture.layers]]
id = "core"
paths = ["crates/fmm-core/src/**"]
may_depend_on = []
severity = "error"

[[architecture.layers]]
id = "store"
paths = ["crates/fmm-store/src/**"]
may_depend_on = ["core"]
severity = "error"

[[architecture.layers]]
id = "cli"
paths = ["crates/fmm-cli/src/**"]
may_depend_on = ["core", "store"]
severity = "error"

[[architecture.allowed_dependencies]]
sources = ["crates/fmm-core/src/**"]
targets = ["crates/fmm-core/src/**"]
edge_kinds = ["runtime", "type_only"]
severity = "error"

[[architecture.allowed_dependencies]]
sources = ["crates/fmm-cli/src/**"]
targets = [
  "crates/fmm-cli/src/**",
  "crates/fmm-core/src/**",
  "crates/fmm-store/src/**",
]
edge_kinds = ["runtime", "type_only"]
severity = "error"

[architecture.size_limits.files]
include = ["**"]
exclude = []
max_loc = 700
severity = "error"

[architecture.size_limits.symbols]
include = ["**"]
exclude = []
kinds = ["fn", "method"]
max_body_loc = 150
severity = "warning"

[[architecture.owners]]
id = "core"
paths = ["crates/fmm-core/src/**"]

[[architecture.owners]]
id = "cli"
paths = ["crates/fmm-cli/src/**"]

[architecture.entrypoints]
candidate_paths = ["crates/*/src/main.rs", "crates/*/src/bin/**"]
detect_graph_roots = false
severity = "warning"

[[architecture.entrypoints.annotations]]
id = "cli"
paths = ["crates/fmm-cli/src/main.rs"]
owners = ["cli"]
```

### Typed config contract

```typescript
type Severity = "warning" | "error";
type EdgeKindConfig = "runtime" | "type_only" | "all";

interface ArchitectureConfig {
  enabled: boolean;
  generated_paths: string[];
  layers: LayerRule[];
  allowed_dependencies: AllowedDependencyRule[];
  size_limits: SizeLimitsConfig;
  owners: OwnerAnnotation[];
  entrypoints: EntrypointConfig;
}

interface LayerRule {
  id: string;
  paths: string[];
  may_depend_on: string[];
  severity: Severity;
}

interface AllowedDependencyRule {
  sources: string[];
  targets: string[];
  edge_kinds: EdgeKindConfig[];
  severity: Severity;
}

interface SizeLimitsConfig {
  files?: FileSizeLimit;
  symbols?: SymbolSizeLimit;
}

interface FileSizeLimit {
  include: string[];
  exclude: string[];
  max_loc: number;
  severity: Severity;
}

interface SymbolSizeLimit {
  include: string[];
  exclude: string[];
  kinds: string[];
  max_body_loc: number;
  severity: Severity;
}

interface OwnerAnnotation {
  id: string;
  paths: string[];
}

interface EntrypointConfig {
  candidate_paths: string[];
  detect_graph_roots: boolean;
  severity: Severity;
  annotations: EntrypointAnnotation[];
}

interface EntrypointAnnotation {
  id: string;
  paths: string[];
  owners: string[];
}
```

## Core rule engine

Add a core module, for example `crates/fmm-core/src/architecture`, with one public entrypoint:

```rust
pub fn lint_architecture(
    manifest: &Manifest,
    config: &ArchitectureConfig,
    options: ArchitectureLintOptions,
) -> Result<ArchitectureLintResult, ArchitectureLintError>;
```

The CLI and MCP wrappers call this function. The engine builds one `GraphIndex` from the manifest and reuses it for every graph based rule.

### Shared preprocessing

1. Normalize config globs and manifest paths to slash separated repo relative strings.
2. Compile generated path matchers first.
3. Build `GraphIndex::from_manifest(manifest)` once.
4. Enumerate edges by iterating `NodeId(0)..graph.node_count()` and calling `GraphIndex::downstream_edges`.
5. Resolve every edge to `source`, `target`, and `edge_kind` through `file_id_for_node` and `path_for_file_id`.
6. Sort edges by `source`, `target`, then `edge_kind`.
7. Exempt any file or edge where the file path matches `generated_paths`, unless a debug option explicitly includes generated paths.
8. Sort final violations by severity, rule, subject key, and config anchor.

### Rule evaluation

#### `layering_violation`

For each non generated edge, classify source and target files by `layers[].paths`.

* If a file matches multiple layers, emit a config diagnostic and skip layer evaluation for that file.
* A source layer may depend on itself and on `may_depend_on` ids.
* If the target layer is outside that set, emit one violation for the edge.
* If either file has no layer, do not emit a layering violation. Missing layer coverage can be added later as a separate rule if needed.

This catches cases such as `fmm-core` depending on `fmm-cli` without hard coding crate names.

#### `disallowed_dependency`

For each non generated edge, find all `allowed_dependencies` rules whose `sources` match the source and whose `edge_kinds` include the edge kind or `all`.

* If no source rule matches, the edge is allowed. This supports incremental adoption.
* If at least one source rule matches, the target must match the union of matching rule `targets`.
* If it does not, emit one violation for the edge.
* Evidence includes the edge kind and the matched source rule ids or anchors.

This rule handles fine grained exceptions and path level boundaries that are too small for layers.

#### `cycle_violation`

Reuse `dependency_cycles_with_path_filter` with `CycleEdgeMode::Runtime` by default. Add a config option later only if users need all edge cycles in architecture lint.

* The path filter excludes generated paths.
* Each returned cycle becomes one violation.
* The subject key is the sorted list of files joined with `>` for deterministic ordering.
* Evidence includes `files` and `edge_mode`.

Do not implement a second Tarjan traversal.

#### `file_size_limit`

For each non generated `Manifest.files` entry:

* Apply `size_limits.files.include` and `exclude`.
* Compare `FileEntry.loc` to `max_loc`.
* Emit a file violation when `loc > max_loc`.
* Evidence includes `actual_loc` and `max_loc`.

The repo hard limit of 700 LOC can be represented by config rather than hard coded.

#### `symbol_size_limit`

Use the shared symbol collection helper from the symbols spec once it exists. Do not duplicate symbol row collection in this command.

* Apply `size_limits.symbols.include`, `exclude`, and `kinds`.
* Compare `metrics.body_loc` to `max_body_loc`.
* Emit a symbol violation when `body_loc > max_body_loc`.
* If `body_loc` is absent because the symbols slice has not landed, add a diagnostic and skip this rule.

`body_loc` comes from `SymbolMetrics::from_line_range` in the symbols spec. Do not infer it from rendered outline `size` text.

#### `missing_owner`

For each non generated source file:

* A file is covered when it matches at least one `owners[].paths` pattern.
* If no owner matches, emit a file violation.
* Evidence includes the candidate file and the configured owner count.

Multiple owners are allowed. Owner ids are annotations only in v1.

#### `missing_entrypoint`

Entrypoint annotations are checked against deterministic candidates.

* Candidate files are any files matching `entrypoints.candidate_paths`.
* If `detect_graph_roots` is true, also include non generated files with zero direct downstream dependents and at least one direct upstream dependency.
* A candidate is annotated when it matches at least one `entrypoints.annotations[].paths` pattern.
* If no annotation matches, emit a file violation.
* Evidence includes `candidate_reason`, `downstream_count` when graph root detection was used, and the configured annotation count.

The default `detect_graph_roots = false` avoids noisy library leaf files. Projects can opt in when their graph shape is clean enough.

## Violation output model

The rule engine emits a stable typed result. This is the `results` payload inside the foundations envelope.

```typescript
type ArchitectureRule =
  | "layering_violation"
  | "disallowed_dependency"
  | "cycle_violation"
  | "file_size_limit"
  | "symbol_size_limit"
  | "missing_owner"
  | "missing_entrypoint";

type ArchitectureSubject =
  | { type: "file"; file: string }
  | { type: "edge"; source: string; target: string; edge_kind: "runtime" | "type_only" }
  | { type: "cycle"; files: string[] }
  | { type: "symbol"; file: string; name: string; lines?: [number, number] };

interface ArchitectureViolation {
  rule: ArchitectureRule;
  severity: "warning" | "error";
  file_or_edge: ArchitectureSubject;
  evidence: Record<string, unknown>;
  config_anchor: string;
}

interface ArchitectureLintSummary {
  files_checked: number;
  edges_checked: number;
  symbols_checked: number;
  violations: number;
  errors: number;
  warnings: number;
}

interface ArchitectureLintResult {
  summary: ArchitectureLintSummary;
  violations: ArchitectureViolation[];
}
```

`config_anchor` is a semantic path such as `architecture.layers.core.may_depend_on` or `architecture.size_limits.files.max_loc`. Do not depend on TOML line spans in v1.

### JSON envelope

`--json` and the MCP tool serialize the foundations envelope:

```jsonc
{
  "contract_version": 1,
  "fmm_version": "0.3.6",
  "index_schema_version": 7,
  "git_sha": "5f8a1296d72f507a2e4bd1950001a442dc6b31fc",
  "git_branch": "main",
  "git_dirty": false,
  "generated_at": "2026-06-17T00:00:00+00:00",
  "command": "lint-architecture",
  "params": {
    "ci": true,
    "fail_on": "error",
    "include_generated": false,
    "rule": null,
    "severity": null
  },
  "results": {
    "summary": {
      "files_checked": 416,
      "edges_checked": 812,
      "symbols_checked": 2200,
      "violations": 2,
      "errors": 1,
      "warnings": 1
    },
    "violations": [
      {
        "rule": "layering_violation",
        "severity": "error",
        "file_or_edge": {
          "type": "edge",
          "source": "crates/fmm-core/src/foo.rs",
          "target": "crates/fmm-cli/src/bar.rs",
          "edge_kind": "runtime"
        },
        "evidence": {
          "source_layer": "core",
          "target_layer": "cli",
          "allowed_layers": []
        },
        "config_anchor": "architecture.layers.core.may_depend_on"
      }
    ]
  },
  "diagnostics": []
}
```

The example uses schema version 7 because the symbols slice is expected to add `body_loc` before this command ships.

## CLI contract

Add a new command variant after the Slice 0 CLI refactor:

```text
fmm lint-architecture [--json] [--ci] [--fail-on <warning|error>] [--rule <rule>] [--severity <warning|error>] [--include-generated]
```

Flags:

* `--json`: print `FmmReportEnvelope<ArchitectureLintResult>`.
* `--ci`: exit nonzero when violations meet `--fail-on`. This mirrors the failure posture of `Commands::Validate` and `cli::validate`.
* `--fail-on <warning|error>`: default `error`. Only meaningful with `--ci`.
* `--rule <rule>`: evaluate or display one rule. Helpful for local cleanup.
* `--severity <warning|error>`: minimum severity to display. Does not change engine evaluation.
* `--include-generated`: include files that match `architecture.generated_paths`. Default false.

Exit behavior:

* Config parse or validation error: exit nonzero.
* Missing `.fmm.db` or stale index: exit nonzero with the existing missing index diagnostic style.
* `--ci` and at least one violation at or above `--fail-on`: exit nonzero.
* No `--ci`: exit zero when the engine ran successfully, even if it printed violations.

Text output should group by severity then rule, with deterministic order matching JSON. Avoid printing generated path exemptions unless `--include-generated` is set.

## MCP contract

Add the tool in `crates/fmm-cli/tools.toml`:

```toml
[tools.fmm_lint_architecture]
cli_name = "lint-architecture"
mcp_description = "Run deterministic architecture lint rules over the fmm dependency graph and .fmmrc.toml architecture config. Returns the foundations JSON envelope."
cli_about = "Run architecture lint rules over layers, dependency allowlists, cycles, size limits, owners, and entrypoints."

[[tools.fmm_lint_architecture.params]]
name = "rule"
type = "string"
enum = ["layering_violation", "disallowed_dependency", "cycle_violation", "file_size_limit", "symbol_size_limit", "missing_owner", "missing_entrypoint"]
mcp_description = "Optional single rule to evaluate or display."
cli_help = "Only show one architecture rule"
cli_flag = "--rule"

[[tools.fmm_lint_architecture.params]]
name = "severity"
type = "string"
enum = ["warning", "error"]
mcp_description = "Minimum severity to include in the returned report."
cli_help = "Minimum severity to display"
cli_flag = "--severity"

[[tools.fmm_lint_architecture.params]]
name = "ci"
type = "boolean"
mcp_description = "CLI only. Exit nonzero when violations meet fail_on. Ignored by MCP."
cli_help = "Fail the process when architecture violations meet --fail-on"
cli_flag = "--ci"

[[tools.fmm_lint_architecture.params]]
name = "fail_on"
type = "string"
enum = ["warning", "error"]
mcp_description = "CLI only. Minimum severity that fails --ci."
cli_help = "Minimum severity that fails --ci"
cli_flag = "--fail-on"

[[tools.fmm_lint_architecture.params]]
name = "include_generated"
type = "boolean"
mcp_description = "Include paths that architecture.generated_paths would normally exempt."
cli_help = "Include generated files in lint output"
cli_flag = "--include-generated"
```

MCP should return the JSON envelope as text content, matching the current `McpServer.handle_tool_call` model. The `ci` and `fail_on` inputs are accepted for parity but have no process exit effect in MCP.

## Traceability

| Field or behavior | Existing anchor |
| --- | --- |
| Config path and merge | `crates/fmm-core/src/config/mod.rs::Config.load_from_dir`, `crates/fmm-core/src/config/loader.rs::FileConfig`, `crates/fmm-core/src/config/loader.rs::apply_file_config` |
| Strict config load addition | `crates/fmm-core/src/config/mod.rs::Config.load_from_dir` |
| File LOC | `crates/fmm-core/src/manifest/file_entry.rs::FileEntry.loc` |
| Symbol body LOC | `~/.mdx/projects/fmm-roadmap-spec-symbols.md::SymbolMetrics` |
| Graph construction | `crates/fmm-core/src/graph/mod.rs::GraphIndex.from_manifest`, `crates/fmm-core/src/manifest/dependency_matcher/reverse.rs::build_dependency_edges` |
| Edge model | `crates/fmm-core/src/graph/mod.rs::Edge`, `crates/fmm-core/src/identity/mod.rs::EdgeKind` |
| Graph edge reads | `crates/fmm-core/src/graph/mod.rs::GraphIndex.downstream_edges`, `crates/fmm-core/src/graph/mod.rs::GraphIndex.upstream_edges` |
| Cycle detection | `crates/fmm-core/src/search/dependency_cycles.rs::dependency_cycles_with_path_filter` |
| CLI declaration | `crates/fmm-cli/src/cli/mod.rs::Commands` |
| CLI dispatch | `crates/fmm-cli/src/main.rs::run_command` |
| CI failure precedent | `crates/fmm-cli/src/cli/sidecar.rs::validate` |
| MCP dispatch | `crates/fmm-cli/src/mcp/mod.rs::McpServer.handle_tool_call` |
| MCP argument structs | `crates/fmm-cli/src/mcp/args.rs` |
| Generated tool schema and help | `crates/fmm-cli/tools.toml` |

## Tests and gates

Unit tests:

1. Config parses a representative `[architecture]` section and validates unique ids.
2. Strict architecture load errors on invalid TOML or invalid architecture references.
3. Generated paths exempt file, edge, symbol, owner, and entrypoint rules.
4. Layering violations use `GraphIndex` edges and stable layer classification.
5. Allowed dependency rules union matching target patterns and respect edge kinds.
6. Cycle rule delegates to `dependency_cycles_with_path_filter` and excludes generated files.
7. File LOC rule uses `FileEntry.loc`.
8. Symbol size rule uses `body_loc` from the symbols helper and emits a diagnostic when metrics are absent.
9. Missing owner and missing entrypoint rules produce stable config anchors.
10. Sorting is deterministic for violations with equal severity and rule.

CLI integration tests:

1. `fmm lint-architecture --json` emits the foundations envelope and deterministic bytes on a double run.
2. `fmm lint-architecture --ci --fail-on error` exits nonzero with an error violation.
3. `fmm lint-architecture --ci --fail-on warning` exits nonzero with a warning violation.
4. `fmm lint-architecture --rule file_size_limit` displays only that rule.
5. Invalid architecture config fails before reporting a clean result.

MCP tests:

1. `tools/list` includes `fmm_lint_architecture` after generated schema refresh.
2. `tools/call` returns the envelope JSON as text content.
3. `rule`, `severity`, and `include_generated` filter output without changing deterministic ordering.

Repo gate remains `just test` and `just check`. Do not use `cargo test`.

## Build order

1. Slice 0 from Wave A: split `crates/fmm-cli/src/cli/mod.rs::Commands` before adding this command.
2. Foundations: ship git metadata and the shared JSON envelope helper.
3. Symbols: ship `body_loc` and the shared symbol collection helper.
4. Config: add `ArchitectureConfig` under the existing config module, including strict load behavior for this command.
5. Core engine: implement `fmm-core/src/architecture` with shared rules and typed results.
6. CLI wrapper: add `lint-architecture` command and CI exit handling.
7. MCP wrapper: add `fmm_lint_architecture`, args, dispatch, and generated schema.

## Open questions

1. Should `detect_graph_roots` ever default to true for application repos, or should entrypoint detection stay pattern based until real project configs prove the root heuristic is quiet?
2. Should unmatched files with no layer be violations in v1, or should layer coverage remain a later rule after owners provide enough coverage signal?
3. Should architecture config parse errors become strict for every fmm command, or only for `lint-architecture` in v1?
