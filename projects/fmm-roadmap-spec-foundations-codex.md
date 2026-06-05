---
title: fmm roadmap foundations spec
type: design
tags: [fmm, roadmap, foundations, git, json, snapshots]
summary: Buildable contract for git stamped indexes, stable report JSON, and per SHA structural snapshots.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

# fmm roadmap foundations spec

## Summary

This spec defines the shared data contract that later fmm roadmap features should cite: git metadata in the index, a stable versioned report envelope, and retained structural snapshots keyed by Git SHA.

Validated current state:

- Repository HEAD is `5f8a1296d72f507a2e4bd1950001a442dc6b31fc`.
- `fmm validate` reports all 416 files indexed and current.
- Current index metadata is `schema_version=6`, `fmm_version=0.3.6`, `generated_at=2026-06-04T15:51:31.073140+00:00`, and `next_file_id=416`.
- `files.content_hash` is populated for 416 of 416 rows.
- Current `.fmm.db` is 1.9 MB and contains 416 files, 3,478 exports, 1,269 methods, and 667 reverse dependency rows.
- Current CLI JSON output is command specific and unenveloped. Example: `ls --json` returns an array, `outline --json` returns `{file, imports, exports, loc}`, and `deps --json` returns `{file, local_deps, external, downstream}`.
- Current `status` has no JSON flag.
- Current MCP dispatch exposes 10 tools from `McpServer.handle_tool_call` and gets schemas through `schema::tool_list`.
- Existing git version stamping is split: `just build-local` shells `git rev-parse --short=7 HEAD`, while `build.rs:emit_version` consumes `FMM_GIT_SHA`. The generate path does not read Git today.

## Design goals

1. Make an fmm index self describing enough for agent artifacts to cite exact source state.
2. Make report JSON stable enough for byte based diffs between identical query inputs over the same indexed state.
3. Preserve enough prior structural state to build `fmm diff`, incremental maps, health deltas, and duplicate trend reports.
4. Keep implementation small and aligned with existing seams: `Commands`, `sidecar::generate`, `SqliteStore`, `writer`, `schema`, MCP tool dispatch, and generated MCP schemas.

## Non goals

- fmm does not author a narrative MAP.md in this foundation slice.
- fmm does not parse Git history in this slice.
- fmm does not store source text in snapshots.
- fmm does not claim dead code or clone proof in this slice.

## Piece 1: Git SHA in the index

### Contract

On `fmm generate`, fmm records Git metadata for the indexed root when the root is inside a Git worktree.

```ts
interface FmmGitMetadata {
  git_sha: string | null;       // Full 40 character commit SHA, or caller override.
  git_branch: string | null;    // Current branch name, null for detached HEAD or no Git.
  git_dirty: boolean | null;    // null when Git metadata is unavailable.
  git_metadata_source: "git" | "override" | "unavailable";
  git_error?: string;           // Human safe diagnostic, omitted on success.
}
```

Behavior:

- Git repository, clean tree: store full HEAD SHA, branch when available, `git_dirty=false`, source `git`.
- Git repository, dirty tree: store full HEAD SHA, branch when available, `git_dirty=true`, source `git`. Normal generate remains allowed.
- No Git repository: leave Git meta keys absent. JSON surfaces nulls and source `unavailable`; text status says Git metadata unavailable.
- `fmm generate --sha <sha>`: store the supplied SHA as `git_sha` and set source `override`. Still attempt branch and dirty detection when Git is available.
- Invalid override SHA: fail fast before indexing. Accept 7 to 40 hex characters, normalize real Git SHAs to full 40 characters, and preserve override length only when expansion is impossible.
- Dirty snapshots: `fmm generate --snapshot` refuses a dirty tree unless `--allow-dirty-snapshot` is supplied. This prevents overwriting a clean commit snapshot with uncommitted state.

### Data model

Bump `SCHEMA_VERSION` from 6 to 7.

Use the existing `meta` key value table for current index metadata:

| Key | Value |
| --- | --- |
| `git_sha` | SHA string |
| `git_branch` | branch string |
| `git_dirty` | `true` or `false` |
| `git_metadata_source` | `git`, `override`, or `unavailable` |
| `git_error` | optional diagnostic |

No new table is required for current index Git metadata. The schema bump still belongs in this slice because the same release adds snapshot tables and changes stable metadata semantics.

Migration and compatibility:

- `open_db` keeps its current strict version check.
- `open_or_create` keeps the existing rebuild path through `ensure_schema`. In this pre release repo, rebuilding a regeneratable index is acceptable.
- Existing v6 databases are rebuilt by `fmm generate`.
- Existing current consumers get a staged JSON migration described in Piece 2.

### CLI surface

Extend `Commands::Generate`:

```text
fmm generate [PATHS...] [--sha <sha>] [--snapshot] [--allow-dirty-snapshot]
fmm status --json
```

Status text adds an `Index metadata` section with schema version, fmm version, generated time, Git SHA, branch, dirty state, and snapshot count.

Status JSON uses the stable report envelope with `command="status"` and metadata in `results`.

### MCP changes

Add `fmm_status` as the metadata read tool. Do not overload navigation tools for status.

```ts
interface FmmStatusResult {
  index_schema_version: number;
  indexed_files: number;
  fmm_version: string;
  generated_at: string | null;
  git: FmmGitMetadata;
  snapshots: {
    count: number;
    latest_git_sha: string | null;
    latest_generated_at: string | null;
  };
}
```

Also include the same Git fields in every stable report envelope returned by future JSON capable MCP tools.

### JSON shape

```json
{
  "schema_version": "fmm.report.v1",
  "index_schema_version": 7,
  "fmm_version": "0.3.6",
  "git_sha": "5f8a1296d72f507a2e4bd1950001a442dc6b31fc",
  "git_branch": "main",
  "git_dirty": false,
  "generated_at": "2026-06-17T03:13:00Z",
  "command": "status",
  "params": {},
  "results": {
    "indexed_files": 416,
    "snapshots": {
      "count": 0,
      "latest_git_sha": null,
      "latest_generated_at": null
    }
  },
  "diagnostics": []
}
```

### Implementation traceability

| Field | Code owner |
| --- | --- |
| `index_schema_version` | `crates/fmm-store/src/schema.rs` symbols `SCHEMA_VERSION`, `CREATE_SCHEMA_SQL`, `ensure_schema` |
| `git_sha` | new `crates/fmm-cli/src/git.rs` symbol `resolve_git_metadata`; `crates/fmm-store/src/sqlite_store.rs` symbol `SqliteStore.write_meta`; `crates/fmm-store/src/writer.rs` symbol `write_meta` |
| `git_branch` | new `crates/fmm-cli/src/git.rs` symbol `resolve_git_metadata`; `SqliteStore.write_meta` |
| `git_dirty` | new `crates/fmm-cli/src/git.rs` symbol `resolve_git_metadata`; `SqliteStore.write_meta` |
| `git_metadata_source` | new `GitMetadata` type; `Commands::Generate` for the `--sha` override |
| `generated_at` | `FmmStore.write_meta`; `SqliteStore.write_meta` |
| CLI flags | `crates/fmm-cli/src/cli/mod.rs` symbol `Commands` |
| Generate write path | `crates/fmm-cli/src/cli/sidecar.rs` symbol `generate` |
| Status display | `crates/fmm-cli/src/cli/status.rs` symbol `status` |
| MCP dispatch | `crates/fmm-cli/src/mcp/mod.rs` symbols `McpServer.handle_tool_call`, `McpServer.handle_tools_list` |
| MCP schema | `crates/fmm-cli/src/mcp/schema.rs` symbol `tool_list`; `crates/fmm-cli/build.rs` symbols `generate_mcp_schema`, `generate_skill_md` |

## Piece 2: Stable versioned JSON contract

### Contract

Every report command returns a shared envelope in stable JSON mode.

Applies first to:

- `ls`
- `outline`
- `deps`
- `cycles`
- `glossary`

Applies next to:

- `lookup`
- `exports`
- `search`
- `similar`
- future report commands such as `map`, `diff`, `dupes`, and `health`

Envelope:

```ts
type ReportSchemaVersion = "fmm.report.v1";

type DiagnosticSeverity = "info" | "warning" | "error";

interface FmmDiagnostic {
  code: string;
  message: string;
  severity: DiagnosticSeverity;
  details?: unknown;
}

interface FmmReportEnvelope<TResults> {
  schema_version: ReportSchemaVersion;
  index_schema_version: number;
  fmm_version: string;
  git_sha: string | null;
  git_branch: string | null;
  git_dirty: boolean | null;
  generated_at: string | null;
  command: string;
  params: Record<string, unknown>;
  results: TResults;
  diagnostics: FmmDiagnostic[];
}
```

Required determinism rules:

1. Key order is fixed as shown in `FmmReportEnvelope`.
2. `params` includes defaults after normalization. Example: `ls` includes `directory:null`, `pattern:null`, `sort_by:"loc"`, `order:"desc"`, `group_by:null`, `filter:"all"`, `limit:null`, `offset:0`.
3. Paths are relative to the resolved fmm root and use `/` separators.
4. Result arrays have deterministic tie breakers. Primary sort follows command semantics; ties sort by path, then symbol name, then kind.
5. Maps are serialized as sorted vectors or as objects with lexicographically sorted keys.
6. Null means unavailable. Omitted means the field is outside the schema for that result type.
7. `generated_at` is index metadata, not query time. No query includes `queried_at`.
8. A no op `fmm generate` must not mutate `generated_at`; it may print a human message. If a file row, reverse dependency row, workspace row, or metadata field changes, then `generated_at` changes.
9. Report JSON excludes volatile row fields such as per file `indexed_at` unless explicitly requested by a future debug mode.

### Data model and schema changes

Piece 2 adds no standalone SQLite tables. It depends on the v7 metadata from Piece 1 and the snapshot tables from Piece 3.

Required code model changes:

- Add typed report structs in `crates/fmm-cli/src/report.rs`.
- Add a store metadata reader that returns schema version, fmm version, generated time, and Git metadata.
- Change `generated_at` semantics so no op generate preserves the previous timestamp.
- Keep legacy JSON as adapters over the typed result structs during migration.

### Stable result shapes

`ls`:

```ts
interface ListFilesResult {
  summary: {
    total_files: number;
    total_loc: number;
    returned: number;
    offset: number;
    limit: number | null;
  };
  files: Array<{
    file: string;
    loc: number;
    exports: number;
    downstream: number;
    modified: string | null;
  }>;
}
```

`ls --group-by subdir`:

```ts
interface ListFilesRollupResult {
  summary: {
    total_files: number;
    total_loc: number;
  };
  buckets: Array<{
    path: string;
    files: number;
    loc: number;
  }>;
}
```

`outline`:

```ts
interface OutlineResult {
  file: string;
  loc: number;
  imports: string[];
  dependencies: string[];
  symbols: Array<{
    name: string;
    kind: string | null;
    visibility: string | null;
    signature: string | null;
    lines: [number, number] | null;
    size: number | null;
    members?: Array<{
      name: string;
      kind: string | null;
      visibility: string | null;
      signature: string | null;
      lines: [number, number] | null;
      size: number | null;
    }>;
  }>;
  reexports: Array<{
    name: string;
    origin_file: string;
    origin_lines: [number, number] | null;
  }>;
}
```

`deps`:

```ts
interface DependencyGraphResult {
  file: string;
  depth: number;
  filter: "all" | "source" | "tests";
  local_deps: Array<{ file: string; depth: number }>;
  external: string[];
  downstream: Array<{ file: string; depth: number }>;
}
```

`cycles`:

```ts
interface DependencyCyclesResult {
  filter: "all" | "source" | "tests";
  edge_mode: "runtime" | "all";
  cycles: Array<{
    files: string[];
  }>;
}
```

`glossary`:

```ts
interface GlossaryResult {
  pattern: string;
  mode: "source" | "tests" | "all";
  precision: "named" | "call-site";
  matches: Array<{
    name: string;
    file: string;
    kind: string | null;
    lines: [number, number] | null;
    used_by: string[];
    namespace_callers?: string[];
    reexported_by?: string[];
  }>;
}
```

### Migration from current `--json`

Use a staged migration to avoid breaking existing local consumers while still making the stable contract the target.

Stage 1:

- Add `--json-v1` to `ls`, `outline`, `deps`, `cycles`, and `glossary`.
- Keep current `--json` output unchanged.
- Add `--legacy-json` only as a hidden alias for tests and transition scripts.

Stage 2:

- Make `--json` emit the envelope.
- Keep `--legacy-json` for one minor release.
- Update command help and generated MCP schemas.

Stage 3:

- Remove `--legacy-json` when all Helioy call sites have moved.

Internal implementation should still build one formatter path for the envelope. Legacy output should adapt from the same typed result structs, not duplicate query logic.

### CLI surface

```text
fmm ls [DIR] --json-v1
fmm outline FILE --json-v1
fmm deps FILE --json-v1
fmm cycles [FILE] --json-v1
fmm glossary PATTERN --json-v1
```

After Stage 2, `--json` is equivalent to `--json-v1`.

### MCP changes

MCP tools get a common optional argument:

```ts
interface StableJsonArgs {
  format?: "text" | "json-v1";
}
```

Default stays text for current human friendly tool output. `format:"json-v1"` returns the same stable envelope as CLI. The MCP transport may keep wrapping content in `content:[{type:"text", text:"..."}]`, but the text must be valid pretty printed JSON. A later MCP upgrade can add `structuredContent` without changing the envelope.

### Implementation traceability

| Field | Code owner |
| --- | --- |
| Envelope metadata | new `crates/fmm-cli/src/report.rs` symbols `FmmReportEnvelope`, `ReportMetadata`, `write_json_report` |
| `schema_version` | new `ReportSchemaVersion` constant in `report.rs` |
| `index_schema_version` | `crates/fmm-store/src/schema.rs` symbol `SCHEMA_VERSION`; new metadata reader on `SqliteStore` |
| `fmm_version` | `crates/fmm-core/src/lib.rs` symbol `VERSION`; `crates/fmm-cli/build.rs` symbol `emit_version` |
| `git_sha`, `git_branch`, `git_dirty` | new `GitMetadata` type and metadata reader |
| `generated_at` | `SqliteStore.write_meta`; new metadata reader |
| `command` | `crates/fmm-cli/src/cli/mod.rs` symbol `Commands` |
| `params` | command specific argument structs under `crates/fmm-cli/src/cli/commands/*` |
| `ls.results` | `crates/fmm-cli/src/cli/commands/ls.rs` symbols `ls`, `collect_entries`, `sort_entries` |
| `outline.results` | `crates/fmm-cli/src/cli/commands/outline.rs` symbols `outline`, `OutlineJson`, `OutlineExportJson` |
| `deps.results` | `crates/fmm-cli/src/cli/commands/deps.rs` symbols `deps`, `DepsJson`, `TransitiveDepsJson` |
| `cycles.results` | `crates/fmm-cli/src/cli/commands/cycles.rs` symbols `cycles`, `CyclesJson` |
| `glossary.results` | `crates/fmm-cli/src/cli/glossary.rs` symbol `glossary`; `crates/fmm-core/src/manifest/glossary_builder.rs` symbol `GlossarySource` |
| MCP format argument | `crates/fmm-cli/src/mcp/mod.rs` symbol `McpServer.handle_tool_call`; `crates/fmm-cli/src/mcp/tools/*` tool functions |
| Generated schemas and skill docs | `crates/fmm-cli/tools.toml`; `crates/fmm-cli/build.rs` symbols `generate_mcp_schema`, `generate_skill_md`, `generate_cli_help` |

## Piece 3: Snapshot tables keyed by Git SHA

### Contract

`fmm generate --snapshot` writes the current structural index into snapshot tables after the current index and reverse dependency graph are consistent.

Snapshots retain structural rows only:

- file path, LOC, source fingerprint, dependency JSON, import JSON, and function names JSON
- export rows
- method rows
- reverse dependency edges
- workspace package rows
- metadata needed to validate and diff snapshots

No source text is stored.

### Data model

Add these tables to `CREATE_SCHEMA_SQL` in schema v7.

```sql
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id          INTEGER PRIMARY KEY,
    git_sha              TEXT NOT NULL,
    git_branch           TEXT,
    git_dirty            INTEGER NOT NULL CHECK (git_dirty IN (0, 1)),
    generated_at         TEXT NOT NULL,
    fmm_version          TEXT NOT NULL,
    index_schema_version INTEGER NOT NULL,
    command              TEXT NOT NULL,
    params_json          TEXT NOT NULL,
    root_path            TEXT NOT NULL,
    scope_digest         TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    UNIQUE (git_sha, scope_digest)
);
CREATE INDEX IF NOT EXISTS idx_snapshots_git_sha ON snapshots(git_sha);
CREATE INDEX IF NOT EXISTS idx_snapshots_created_at ON snapshots(created_at);

CREATE TABLE IF NOT EXISTS snapshot_files (
    snapshot_id          INTEGER NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    path                 TEXT NOT NULL,
    loc                  INTEGER NOT NULL,
    modified             TEXT,
    imports              TEXT,
    dependencies         TEXT,
    dependency_kinds     TEXT,
    named_imports        TEXT,
    namespace_imports    TEXT,
    function_names       TEXT,
    source_mtime         TEXT,
    source_size          INTEGER,
    content_hash         TEXT NOT NULL,
    parser_cache_version INTEGER,
    PRIMARY KEY (snapshot_id, path)
);
CREATE INDEX IF NOT EXISTS idx_snapshot_files_hash ON snapshot_files(content_hash);

CREATE TABLE IF NOT EXISTS snapshot_exports (
    snapshot_id      INTEGER NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    name             TEXT NOT NULL,
    file_path        TEXT NOT NULL,
    start_line       INTEGER,
    end_line         INTEGER,
    signature        TEXT,
    visibility       TEXT,
    declaration_kind TEXT,
    PRIMARY KEY (snapshot_id, name, file_path)
);
CREATE INDEX IF NOT EXISTS idx_snapshot_exports_name ON snapshot_exports(snapshot_id, name);

CREATE TABLE IF NOT EXISTS snapshot_methods (
    snapshot_id        INTEGER NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    dotted_name        TEXT NOT NULL,
    file_path          TEXT NOT NULL,
    start_line         INTEGER,
    end_line           INTEGER,
    relationship_kind  TEXT,
    signature          TEXT,
    visibility         TEXT,
    declaration_kind   TEXT,
    PRIMARY KEY (snapshot_id, dotted_name, file_path)
);
CREATE INDEX IF NOT EXISTS idx_snapshot_methods_name ON snapshot_methods(snapshot_id, dotted_name);

CREATE TABLE IF NOT EXISTS snapshot_reverse_deps (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    target_path TEXT NOT NULL,
    source_path TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, target_path, source_path)
);
CREATE INDEX IF NOT EXISTS idx_snapshot_reverse_deps_target ON snapshot_reverse_deps(snapshot_id, target_path);

CREATE TABLE IF NOT EXISTS snapshot_workspace_packages (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    directory   TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, name)
);
```

`scope_digest` is the stable digest of normalized generate paths plus filter config. It prevents collisions when the same SHA is indexed with different path scopes. The canonical root snapshot uses `scope_digest="root"`.

### Snapshot write flow

1. `generate` resolves root and Git metadata.
2. `generate` writes current index rows through the existing transaction path.
3. `generate` rebuilds reverse dependencies.
4. `generate` writes metadata.
5. If `--snapshot` is set, `generate` calls `SqliteStore.write_snapshot(metadata, params)`.
6. `write_snapshot` opens one transaction, upserts the `snapshots` row for `(git_sha, scope_digest)`, deletes prior child rows for that snapshot, and copies current `files`, `exports`, `methods`, `reverse_deps`, and `workspace_packages` rows into child tables.
7. If the tree is dirty and `--allow-dirty-snapshot` is absent, fail before writing snapshot rows. The current index may still be written because normal generate permits dirty state.
8. If Git metadata is unavailable and `--sha` is absent, fail before writing snapshot rows. The caller can pass `--sha` in CI or non Git checkouts.

### Retention and pruning

Default policy:

- Keep the latest 50 canonical root snapshots.
- Keep all snapshots referenced by a named baseline file once that feature exists.
- Prune older unreferenced snapshots with `fmm snapshots prune`.
- Never prune automatically during `fmm generate` unless `--prune-snapshots` is supplied.

CLI:

```text
fmm snapshots list [--json-v1]
fmm snapshots prune [--keep 50] [--dry-run]
fmm snapshots delete <git_sha> [--scope <scope_digest>]
```

MCP:

```text
fmm_snapshot_status
```

### Storage considerations

The current repo index is 1.9 MB for 416 files, 3,478 exports, 1,269 methods, and 667 reverse dependency rows. A structural snapshot copies the row payload but no source text. For this repo, expect low single digit MB per snapshot before SQLite page reuse and WAL effects. A 50 snapshot retention budget should remain practical for medium repos, but large monorepos should use explicit pruning or future compressed snapshot rows. The first implementation should favor correctness and simple SQL copies over deduplicated storage.

### CLI surface

```text
fmm generate [PATHS...] --snapshot [--sha <sha>] [--allow-dirty-snapshot]
fmm diff <base_sha> [<head_sha>] [--json-v1]
fmm snapshots list [--json-v1]
fmm snapshots prune [--keep <n>] [--dry-run]
```

### JSON shape

`fmm snapshots list --json-v1` and `fmm_snapshot_status` return:

```ts
interface SnapshotStatusResult {
  snapshots: Array<{
    git_sha: string;
    git_branch: string | null;
    git_dirty: boolean;
    generated_at: string;
    fmm_version: string;
    index_schema_version: number;
    scope_digest: string;
    files: number;
    exports: number;
    methods: number;
    reverse_deps: number;
  }>;
}
```

`fmm diff` can be implemented after the snapshot writer. The foundation contract should still reserve the result shape:

```ts
interface StructuralDiffResult {
  base: { git_sha: string; generated_at: string; scope_digest: string };
  head: { git_sha: string; generated_at: string; scope_digest: string };
  files: {
    added: string[];
    removed: string[];
    modified: Array<{
      file: string;
      old_content_hash: string;
      new_content_hash: string;
    }>;
  };
  symbols: {
    added: SymbolRef[];
    removed: SymbolRef[];
    signature_changed: Array<{
      before: SymbolRef;
      after: SymbolRef;
    }>;
  };
  dependencies: {
    added_edges: DependencyEdge[];
    removed_edges: DependencyEdge[];
  };
}

interface SymbolRef {
  name: string;
  file: string;
  kind: string | null;
  visibility: string | null;
  signature: string | null;
  lines: [number, number] | null;
}

interface DependencyEdge {
  source_path: string;
  target_path: string;
}
```

### MCP changes

Add these tools after snapshot write support lands:

- `fmm_snapshot_status`: list available snapshots and latest snapshot metadata.
- `fmm_structural_diff`: return `FmmReportEnvelope<StructuralDiffResult>` for `base` and `head`.

Do not add `fmm_structural_diff` before the snapshot tables are written and tested.

### Implementation traceability

| Field or row | Code owner |
| --- | --- |
| `snapshots.git_sha` | `schema.rs` symbol `CREATE_SCHEMA_SQL`; new `SnapshotMetadata` type; new `SqliteStore.write_snapshot` |
| `snapshots.scope_digest` | new `scope_digest` helper fed by `Commands::Generate.paths` and resolved root |
| `snapshot_files.path` | current `files.path` from `CREATE_SCHEMA_SQL`; copy query in new writer snapshot function |
| `snapshot_files.content_hash` | `Fingerprint.content_hash`; `source_fingerprint`; `serialize_file_data_with_fingerprint`; `upsert_preserialized_with_file_id` |
| `snapshot_exports.*` | current `exports` table in `CREATE_SCHEMA_SQL`; `serialize_file_data_inner`; `upsert_preserialized_with_file_id` |
| `snapshot_methods.*` | current `methods` table in `CREATE_SCHEMA_SQL`; `serialize_file_data_inner`; `upsert_preserialized_with_file_id` |
| `snapshot_reverse_deps.*` | `writer::rebuild_and_write_reverse_deps`; `writer::write_reverse_deps` |
| `snapshot_workspace_packages.*` | `writer::upsert_workspace_packages`; `SqliteStore.upsert_workspace_packages` |
| Snapshot transaction | new `writer::write_snapshot` called from new `SqliteStore.write_snapshot` |
| `generate --snapshot` | `Commands::Generate`; `sidecar::generate` |
| Snapshot status CLI | new `Commands::Snapshots`; new `crates/fmm-cli/src/cli/snapshots.rs` |
| Structural diff CLI | new `Commands::Diff`; new `crates/fmm-cli/src/cli/diff.rs` |
| MCP status and diff | `McpServer.handle_tool_call`; new `tools/snapshot_status.rs`; new `tools/structural_diff.rs`; generated schemas from `tools.toml` |

## Test plan

Unit tests: schema v7 creation, Git meta write and read, snapshot row copying, no op `generated_at` stability, dirty snapshot gating, envelope key and param ordering, and legacy JSON adapters until Stage 3.

Integration tests: clean Git snapshot, dirty worktree snapshot refusal, non Git snapshot with `--sha`, byte identical repeated JSON reports, no op generate metadata stability, and a two commit signature change smoke test for `fmm diff`.

Verification commands: `cargo fmt --all`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo nextest run --workspace`, `cargo test --workspace --doc`, `cargo run -q -p fmm -- generate --snapshot`, `cargo run -q -p fmm -- status --json-v1`, `cargo run -q -p fmm -- ls --json-v1 --limit 2`, and `cargo run -q -p fmm -- validate`.

## Open design questions

1. Dirty snapshot identity: should dirty snapshots be addressable by `git_sha+dirty_digest` instead of requiring `--allow-dirty-snapshot` on the same `git_sha` key? The proposed v1 default refuses dirty snapshots to keep `git_sha` trustworthy.
2. Partial path snapshots: should v1 forbid non root snapshots, or keep them under `scope_digest` from day one? The proposed v1 stores `scope_digest` immediately and makes `fmm diff <sha>` choose only canonical root snapshots unless a scope is supplied.
3. JSON migration timing: when should `--json` switch from legacy command specific output to `json-v1`? The proposed path adds `--json-v1` first, then flips after Helioy call sites are moved.
4. Git metadata detection scope: should `git_dirty` include untracked supported source files only, all untracked files, or tracked changes only? The proposed default uses the indexed root and supported source paths, then records a diagnostic if Git cannot scope the check.
5. Snapshot pruning default: should generate ever prune automatically? The proposed default does not prune during generate without an explicit flag.

## Recommended implementation order

1. Add `GitMetadata`, metadata reads, and `status --json-v1` without changing command JSON.
2. Add `report.rs` and port `ls --json-v1`, then `outline`, `deps`, `cycles`, and `glossary`.
3. Adjust `generated_at` semantics so no op generate does not mutate stable metadata.
4. Add snapshot schema and writer, gated behind `generate --snapshot`.
5. Add snapshot status, then structural diff.
6. Flip `--json` to the envelope after call sites migrate.
