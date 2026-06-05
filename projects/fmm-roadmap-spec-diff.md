---
title: fmm Roadmap Spec, Structural Diff and Snapshot Surface
type: spec
tags: [fmm, roadmap, diff, snapshots, mcp, cli, map]
summary: Specifies fmm diff, fmm_structural_diff, and snapshot list/prune against the canonical foundations snapshot contract.
status: draft
source: backend-engineer
confidence: high
repo: /Users/alphab/Dev/LLM/DEV/helioy/fmm
head: 5f8a1296d72f507a2e4bd1950001a442dc6b31fc
fmm_version: 0.3.6
created: 2026-06-17
updated: 2026-06-17
depends_on:
  - ~/.mdx/projects/fmm-roadmap-spec-foundations.md
  - ~/.mdx/projects/fmm-eval-codex--brainstorm.md
---

# fmm Structural Diff Spec

This spec builds on the canonical foundations contract at `~/.mdx/projects/fmm-roadmap-spec-foundations.md`. It inherits the foundation envelope, git metadata, and SHA keyed snapshots. It does not redefine the snapshot envelope or table contract.

Load bearing foundation decisions:

- Snapshots live in `.fmm-snapshots.db`, separate from `.fmm.db`.
- Snapshot identity is `UNIQUE(git_sha, scope_digest)`.
- Canonical root scope uses `scope_digest = "root"`.
- Snapshot tables are `snapshots`, `snapshot_files`, `snapshot_exports`, `snapshot_methods`, `snapshot_reverse_deps`, and `snapshot_workspace_packages`.
- JSON output uses `FmmReportEnvelope<StructuralDiffResult>` with `contract_version`, `fmm_version`, `index_schema_version`, `git_sha`, `git_branch`, `git_dirty`, `generated_at`, `command`, `params`, `results`, and `diagnostics`.

## Scope

In scope:

1. CLI: `fmm diff <base_sha> [<head_sha>]`.
2. MCP: `fmm_structural_diff`.
3. CLI: `fmm snapshots list` and `fmm snapshots prune`.
4. Markdown output for a concise per commit changelog that can patch an existing `MAP.md`.
5. JSON output using the foundations envelope.
6. A reserved integration point for `fmm map --update MAP.md --base <sha> --head <sha>`.

Out of scope:

- Designing `fmm map` internals.
- Reindexing historical git commits.
- Content hash dedup storage.
- Map file persistence.
- Heuristic rename or move detection. A move appears as one removed file plus one added file in v1.

## Existing code anchors

Grounding from the live repo:

- `.fmm.db` exists and `fmm validate` reported 416 indexed files current.
- CLI commands are owned by `Commands` in `crates/fmm-cli/src/cli/mod.rs`; that file is already over the 700 line threshold.
- MCP dispatch is centralized in `McpServer.handle_tool_call`.
- MCP tool docs and schemas are generated from `crates/fmm-cli/tools.toml` by `crates/fmm-cli/build.rs`.
- Live index tables are declared in `CREATE_SCHEMA_SQL`.
- File freshness and `content_hash` are written through the existing writer path.
- Symbols load through `load_exports` and `load_methods` into `Manifest`.
- Dependency graph and cycle logic already exist in `GraphIndex`, `Edge`, `EdgeKind`, and `dependency_cycles`.

Implementation must use these seams rather than duplicating command parsing, MCP schema generation, symbol normalization, graph construction, or markdown formatting.

## User surfaces

### `fmm diff`

Default output is markdown.

```bash
fmm diff <base_sha> [<head_sha>] \
  [--scope-digest <digest>] \
  [--edge-mode runtime|all] \
  [--json]
```

Parameters:

- `base_sha`: required snapshot SHA or unambiguous snapshot SHA prefix.
- `head_sha`: optional snapshot SHA or unambiguous snapshot SHA prefix.
- `--scope-digest`: optional. Default `root`.
- `--edge-mode`: optional. Default `runtime`. `all` includes type only dependency edges.
- `--json`: emit `FmmReportEnvelope<StructuralDiffResult>`. Without it, emit markdown.

With one SHA, `head` resolves to the live `.fmm.db` working index. Latest snapshot selection is explicit: pass that snapshot SHA as `head_sha`.

### `fmm_structural_diff`

MCP tool parameters:

```ts
interface StructuralDiffToolArgs {
  base_sha: string;
  head_sha?: string;
  scope_digest?: string;      // default: "root"
  edge_mode?: "runtime" | "all"; // default: "runtime"
  format?: "markdown" | "json"; // default: "markdown"
  truncate?: boolean;         // default: true, follows existing MCP cap behavior
}
```

The MCP transport follows the existing text content wrapper. `format: "json"` returns the serialized foundations envelope as text content. `format: "markdown"` returns the changelog markdown as text content.

`McpServer.handle_tool_call` currently requires a live manifest before dispatching every tool. This must be split so snapshot only calls can run when `.fmm-snapshots.db` exists even if the live `.fmm.db` cannot load. Omitted `head_sha` still requires the live index because the head is the working index.

### `fmm snapshots list`

```bash
fmm snapshots list [--scope-digest <digest>] [--json]
```

Markdown output is a deterministic table sorted by `generated_at` descending, then `git_sha` ascending. JSON output uses the foundations envelope and returns `SnapshotInventoryResult`.

Inventory fields come from `snapshots` plus row counts from `snapshot_files`, `snapshot_exports`, `snapshot_methods`, `snapshot_reverse_deps`, and `snapshot_workspace_packages`.

### `fmm snapshots prune`

```bash
fmm snapshots prune [--keep <n>] [--scope-digest <digest>] [--dry-run] [--json]
```

Rules:

- Default `--keep` is 50, inherited from foundations.
- Prune is explicit. No other command prunes snapshots.
- `--scope-digest` limits deletion candidates to one scope. Without it, prune applies the keep rule independently per scope.
- `--dry-run` returns the deletion plan without deleting rows.
- Deletion starts from `snapshots`; child rows must cascade or be deleted in the same transaction.
- JSON output uses the foundations envelope and returns `SnapshotPruneResult`.

## Snapshot selection

Inputs resolve to exactly one side per comparison.

### Scope selection

1. Resolve `scope_digest` from `--scope-digest` or MCP `scope_digest`.
2. Default to `root`.
3. Load base and head from the same `scope_digest`.
4. If a specified base/head pair resolves to different scopes, return `scope_mismatch`.
5. If no snapshot exists for the selected scope, return `snapshot_missing`.

### Base side

`base_sha` must resolve to one row in `snapshots` for the selected scope. Resolution checks exact SHA first, then unambiguous prefix. Ambiguous prefix returns `snapshot_ambiguous` with the matching SHAs in diagnostics.

### Head side

If `head_sha` is present, it resolves like `base_sha` against `snapshots`.

If `head_sha` is omitted:

1. Open live `.fmm.db` through the current store path.
2. Load files, symbols, dependencies, and metadata from the live index.
3. Stamp `head.source = "working_index"`.
4. Use live index metadata for `git_sha`, `git_branch`, `git_dirty`, and `generated_at`.
5. If the live index lacks foundation git metadata, return `index_missing_git_metadata` with guidance to run `fmm generate` from the foundations implementation.

### Missing data

Required snapshot missing:

```json
{
  "code": "snapshot_missing",
  "message": "Required snapshot is missing",
  "details": { "git_sha": "...", "scope_digest": "root" }
}
```

Missing `.fmm-snapshots.db` returns `snapshot_store_missing`. Missing live index for omitted head returns `index_missing`.

All errors must also be represented in envelope `diagnostics` when JSON output can be produced. CLI exits nonzero for errors.

## JSON contract

Use snake case in JSON.

```ts
interface StructuralDiffResult {
  base: DiffSideRef;
  head: DiffSideRef;
  scope_digest: string;
  files: FileDiff;
  symbols: SymbolDiff;
  dependencies: DependencyDiff;
  cycles: CycleDiff;
  summary: DiffSummary;
}

interface DiffSideRef {
  source: "snapshot" | "working_index";
  git_sha: string | null;
  git_branch: string | null;
  git_dirty: boolean | null;
  generated_at: string;
  fmm_version: string;
  index_schema_version: number;
  snapshot_schema_version?: number;
  scope_digest: string;
}

interface FileDiff {
  added: AddedFile[];
  removed: RemovedFile[];
  modified: ModifiedFile[];
}

interface AddedFile {
  file_path: string;
  new_content_hash: string | null;
  loc: number;
}

interface RemovedFile {
  file_path: string;
  old_content_hash: string | null;
  loc: number;
}

interface ModifiedFile {
  file_path: string;
  old_content_hash: string | null;
  new_content_hash: string | null;
  old_loc: number;
  new_loc: number;
}

interface SymbolDiff {
  added: SymbolRef[];
  removed: SymbolRef[];
  signature_changed: SignatureChange[];
}

interface SymbolRef {
  file_path: string;
  name: string;
  signature: string | null;
  visibility: string | null;
  declaration_kind: string | null;
  source_table: "snapshot_exports" | "snapshot_methods";
}

interface SignatureChange {
  file_path: string;
  name: string;
  before: SymbolRef;
  after: SymbolRef;
}

interface DependencyDiff {
  edge_mode: "runtime" | "all";
  added_edges: DependencyEdge[];
  removed_edges: DependencyEdge[];
}

interface DependencyEdge {
  source_path: string;
  target_path: string;
  kind: "runtime" | "type_only" | null;
}

interface CycleDiff {
  edge_mode: "runtime" | "all";
  new: CycleComponent[];
  resolved: CycleComponent[];
}

interface CycleComponent {
  files: string[];
  edge_count: number;
}

interface DiffSummary {
  files_added: number;
  files_removed: number;
  files_modified: number;
  symbols_added: number;
  symbols_removed: number;
  signatures_changed: number;
  dependency_edges_added: number;
  dependency_edges_removed: number;
  cycles_new: number;
  cycles_resolved: number;
}
```

`command` in the envelope is `"diff"`. `params` includes `base_sha`, `head_sha`, `scope_digest`, `edge_mode`, and `format` with defaults resolved.

For omitted `head_sha`, the envelope top level `git_sha`, `git_branch`, `git_dirty`, and `generated_at` come from the live working index. For two snapshot comparison, they come from the head snapshot.

## Diff algorithm

The algorithm is deterministic and data driven.

1. Resolve base side and head side.
2. Load snapshot rows from `.fmm-snapshots.db`; load live rows from `.fmm.db` only when head is omitted.
3. Normalize each side into an in memory `StructuralSnapshot`:
   - files from `snapshot_files` or live `files`.
   - symbols from `snapshot_exports` and `snapshot_methods`, normalized to `SymbolRef`.
   - dependency edges from stored file dependency data, with `EdgeKind` when available.
   - cycle graph from the same normalized dependency data.
4. File diff:
   - `added = head.files - base.files` by `file_path`.
   - `removed = base.files - head.files` by `file_path`.
   - `modified = common files where old.content_hash != new.content_hash`.
   - Equal `content_hash` means unchanged even if timestamps differ.
5. Symbol diff:
   - Candidate files are added, removed, and modified files.
   - Key symbol rows by `(file_path, name)` as required by the brief.
   - Rows present only in head are `added`.
   - Rows present only in base are `removed`.
   - Rows present in both with different `signature` are `signature_changed`.
   - Visibility or declaration kind changes are diagnostics in v1, not top level change classes.
6. Edge diff:
   - Build edge sets after applying `edge_mode`.
   - Compare edge identity by `(source_path, target_path, kind)` when kind is available.
   - If kind is unavailable because a stored legacy row lacks dependency kind data, compare `(source_path, target_path)` and emit `edge_kind_unavailable` in diagnostics.
7. Cycle delta:
   - Build a `GraphIndex` compatible model for each side.
   - Run existing cycle detection with the selected `edge_mode`.
   - Canonical cycle key is the sorted file path list in the strongly connected component.
   - Components present only in head are `new`.
   - Components present only in base are `resolved`.
8. Sort all result arrays lexicographically:
   - files by `file_path`.
   - symbols by `file_path`, then `name`.
   - edges by `source_path`, then `target_path`, then `kind`.
   - cycles by joined sorted file path key.
9. Render markdown or serialize the envelope.

No N plus one queries: each snapshot side loads files, exports, methods, reverse dependency rows, and workspace rows with one query per table. The in memory set diff performs all comparisons.

## Markdown contract

Markdown is concise and patch friendly. Stable headings allow an agent to locate and update a `MAP.md` section.

```markdown
# Structural diff: <base_short>..<head_short>

Scope: root
Head source: working_index

## Summary

- Files: +A, -R, ~M
- Symbols: +A, -R, signatures ~S
- Dependencies: +A, -R
- Cycles: +N, -R

## Files

### Added
- path/to/file.rs (loc N)

### Removed
- path/to/file.rs (loc N)

### Modified
- path/to/file.rs (old_hash -> new_hash, loc old -> new)

## Symbols

### Added
- path/to/file.rs :: SymbolName

### Removed
- path/to/file.rs :: SymbolName

### Signature changed
- path/to/file.rs :: SymbolName
  - before: ...
  - after: ...

## Dependency edges

### Added
- source.rs -> target.rs (runtime)

### Removed
- source.rs -> target.rs (runtime)

## Cycles

### New
- file_a.rs, file_b.rs

### Resolved
- file_c.rs, file_d.rs
```

Sections with no entries print `None` to preserve anchors.

## Snapshot inventory contracts

```ts
interface SnapshotInventoryResult {
  snapshots: SnapshotInventoryRow[];
  summary: {
    total_snapshots: number;
    scopes: number;
  };
}

interface SnapshotInventoryRow {
  git_sha: string;
  git_branch: string | null;
  git_dirty: boolean;
  generated_at: string;
  fmm_version: string;
  index_schema_version: number;
  snapshot_schema_version: number;
  scope_digest: string;
  rows: {
    files: number;
    exports: number;
    methods: number;
    reverse_deps: number;
    workspace_packages: number;
  };
}

interface SnapshotPruneResult {
  dry_run: boolean;
  keep: number;
  scope_digest: string | null;
  deleted: SnapshotInventoryRow[];
  retained: SnapshotInventoryRow[];
}
```

## Incremental MAP flow

Reserve this shape for the map spec:

```bash
fmm map --update MAP.md --base <sha> --head <sha>
```

This diff spec provides the structural change feed. The map spec owns map sections, rewrite policy, human review controls, and how markdown diff entries patch `MAP.md`.

Expected flow after both specs ship:

1. `fmm generate --snapshot` records the baseline after a commit.
2. Development changes code.
3. `fmm generate` refreshes the live index.
4. `fmm diff <base_sha>` compares the baseline snapshot to the live working index.
5. `fmm map --update MAP.md --base <base_sha> --head <head_sha>` consumes the same structural diff contract.

## Implementation seams

Recommended module split:

- `crates/fmm-core/src/diff.rs`: `StructuralDiffResult`, normalized structs, pure set diff, deterministic sorting.
- `crates/fmm-store/src/snapshots/`: open `.fmm-snapshots.db`, list, prune, load snapshot sides, and preserve the independent snapshot schema lifecycle.
- `crates/fmm-cli/src/cli/commands/diff.rs`: CLI wrapper and markdown/json selection.
- `crates/fmm-cli/src/cli/commands/snapshots.rs`: `list` and `prune` wrappers.
- `crates/fmm-cli/src/mcp/tools/structural_diff.rs`: MCP wrapper calling the same diff engine.
- `crates/fmm-cli/tools.toml`: single source for MCP tool schema and CLI help additions.

`crates/fmm-cli/src/cli/mod.rs` is already over 700 lines. Implementation must refactor before adding new command surface there. Acceptable direction: move subcommand option structs into `cli/commands/*` modules and keep `Commands` as a thin enum.

## Tests and gates

Use repo gates from foundations: `just test` and `just check`.

Required tests:

1. Snapshot selection:
   - exact SHA.
   - unique prefix.
   - ambiguous prefix.
   - missing snapshot.
   - scope mismatch.
2. One SHA diff compares base snapshot to live working index.
3. Two SHA diff compares snapshot to snapshot without requiring live manifest load.
4. File diff is gated by `content_hash`.
5. Symbol diff detects added, removed, and signature changed rows keyed by `(file_path, name)`.
6. Dependency edge diff honors `edge_mode`.
7. Cycle delta reports new and resolved strongly connected components.
8. JSON output is byte stable across repeated runs with unchanged inputs.
9. Markdown output preserves stable anchors and prints `None` for empty sections.
10. `fmm snapshots list --json` reports row counts per foundation table.
11. `fmm snapshots prune --dry-run` deletes nothing.
12. `fmm snapshots prune --keep N` deletes only older rows for the targeted scope and removes child rows transactionally.
13. MCP `fmm_structural_diff` returns markdown by default and envelope JSON when requested.
14. MCP snapshot to snapshot diff works when the live `.fmm.db` is absent or stale.

## Traceability

| Contract field | Code anchor |
| --- | --- |
| CLI command surface | `crates/fmm-cli/src/cli/mod.rs` + `Commands` |
| CLI command handlers | `crates/fmm-cli/src/cli/commands/mod.rs` + command module re exports |
| MCP tool registry | `crates/fmm-cli/tools.toml` + `crates/fmm-cli/build.rs` `generate_mcp_schema` |
| CLI help generation | `crates/fmm-cli/tools.toml` + `crates/fmm-cli/build.rs` `generate_cli_help` |
| MCP dispatch | `crates/fmm-cli/src/mcp/mod.rs` + `McpServer.handle_tool_call` |
| MCP response cap | `crates/fmm-cli/src/mcp/mod.rs` + `cap_response` |
| Live DB filename pattern | `crates/fmm-store/src/connection.rs` + `DB_FILENAME` |
| Live DB opening pattern | `crates/fmm-store/src/connection.rs` + `open_or_create`, `open_db` |
| Live schema columns | `crates/fmm-store/src/schema.rs` + `CREATE_SCHEMA_SQL` |
| Schema version behavior | `crates/fmm-store/src/schema.rs` + `ensure_schema`, `drop_all_tables` |
| Store trait seam | `crates/fmm-core/src/store.rs` + `FmmStore` |
| SQLite store implementation | `crates/fmm-store/src/sqlite_store.rs` + `SqliteStore` |
| Memory store test seam | `crates/fmm-store/src/memory_store/mod.rs` + `InMemoryStore` |
| File rows and content hash | `crates/fmm-store/src/schema.rs` + `CREATE_SCHEMA_SQL` |
| Fingerprint loading | `crates/fmm-store/src/writer.rs` + `load_fingerprints` |
| Metadata writing pattern | `crates/fmm-store/src/writer.rs` + `write_meta` |
| Manifest aggregate | `crates/fmm-core/src/manifest/mod.rs` + `Manifest` |
| Export symbol loading | `crates/fmm-store/src/reader/exports.rs` + `load_exports` |
| Method symbol loading | `crates/fmm-store/src/reader/exports.rs` + `load_methods` |
| File loading | `crates/fmm-store/src/reader/files.rs` + `load_files_map` |
| Reverse dependency loading | `crates/fmm-store/src/reader/reverse_deps.rs` + `load_reverse_deps` |
| Dependency graph model | `crates/fmm-core/src/graph/mod.rs` + `GraphIndex`, `Edge` |
| Dependency edge kind | `crates/fmm-core/src/identity/mod.rs` + `EdgeKind` |
| Cycle detection | `crates/fmm-core/src/graph/cycles.rs` + `dependency_cycles` |
| Snapshot table names | `~/.mdx/projects/fmm-roadmap-spec-foundations.md` + `D2` |
| Envelope fields | `~/.mdx/projects/fmm-roadmap-spec-foundations.md` + `D4` |

## Open questions

1. Should v1 expose only `--scope-digest`, or should it also accept human path scope input and compute the digest? The map spec may need the human form.
2. Should `fmm snapshots prune` execute on call as specified, or require an explicit `--apply` flag beyond the command name?
3. Should the foundations snapshot writer persist edge kind in `snapshot_reverse_deps`, or should diff always reconstruct kind from `snapshot_files.dependencies` and `snapshot_files.dependency_kinds`?
4. What minimum SHA prefix length should v1 accept before checking ambiguity? Seven characters matches common git output, but the final value should be implementation policy.
