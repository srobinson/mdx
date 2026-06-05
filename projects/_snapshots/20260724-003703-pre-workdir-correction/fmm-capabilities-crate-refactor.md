# fmm Capabilities Crate Refactor

Date: 2026-04-21

Status: research note and recommendation

## Question

Should `frontmatter-matters` introduce a `fmm-capabilities` crate to improve separation, reduce repeated logic, and reuse behavior across CLI and MCP?

## Recommendation

Yes. Do it as a staged refactor.

The clean target is a new `crates/fmm-capabilities` crate that owns manifest backed application capabilities. Keep CLI and MCP as adapters. Keep index generation, validation, watching, init, and status in the CLI crate until another consumer needs them.

Recommended LOE: 4 to 6 focused days.

Minimum useful LOE: 2 to 3 days.

Full split including a separate `fmm-mcp` crate: 7 to 10 days.

## Research Method

The local fmm index was valid at the time of research:

```text
Validating index...
Validating 367 files against index...
All 367 files are indexed and up to date
```

The context-matters index was revalidated after Stuart updated it:

```text
Validating index...
Validating 223 files against index...
All 223 files are indexed and up to date
```

fmm structural navigation used local `fmm` commands, including:

```bash
fmm ls crates --group-by subdir
fmm ls crates/fmm-cli/src --sort-by downstream --limit 80
fmm outline crates/fmm-cli/src/mcp/mod.rs --include-private
fmm outline crates/fmm-cli/src/mcp/tools/common.rs --include-private
fmm outline crates/fmm-cli/src/cli/commands/ls.rs --include-private
fmm outline crates/fmm-cli/src/mcp/tools/list_files.rs --include-private
fmm outline crates/fmm-cli/src/cli/search.rs --include-private
fmm outline crates/fmm-cli/src/mcp/tools/search.rs --include-private
```

context-matters was used as the design reference:

```bash
fmm ls crates --group-by subdir
fmm ls crates/cm-capabilities/src --sort-by downstream --limit 100
fmm outline crates/cm-capabilities/src/recall.rs --include-private
fmm outline crates/cm-cli/src/cli/recall.rs --include-private
fmm outline crates/cm-cli/src/mcp/tools/recall.rs --include-private
```

## Current fmm Shape

Workspace crates:

```text
crates/fmm-core/    243 files, 33,224 LOC
crates/fmm-cli/      92 files, 15,060 LOC
crates/fmm-store/     9 files, 2,694 LOC
```

There is no current `fmm-mcp` crate. MCP lives inside the CLI crate at:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/mcp/
```

Key files:

```text
crates/fmm-cli/src/mcp/mod.rs
crates/fmm-cli/src/mcp/tools/*.rs
crates/fmm-cli/src/mcp/args.rs
crates/fmm-cli/src/read_symbol.rs
crates/fmm-cli/src/glossary.rs
crates/fmm-cli/src/cli/commands/*.rs
crates/fmm-cli/src/cli/search.rs
```

The CLI crate currently has three jobs:

1. CLI argument surface and terminal output.
2. MCP protocol server and tool wrappers.
3. Shared application behavior for navigation capabilities.

The third job is the boundary problem.

## context-matters Reference Pattern

context-matters uses a middle crate:

```text
crates/cm-core/
crates/cm-store/
crates/cm-capabilities/
crates/cm-cli/
crates/cm-web/
```

`cm-capabilities` is the application behavior layer. It owns typed requests, typed results, validation, projection, and shared operations. CLI and MCP call the same functions.

Example:

```text
crates/cm-capabilities/src/recall.rs
  RecallRequest
  RecallResult
  recall(store, request)

crates/cm-cli/src/cli/recall.rs
  parse CLI args
  build RecallRequest
  call recall()
  print text or JSON view

crates/cm-cli/src/mcp/tools/recall.rs
  parse MCP args
  build RecallRequest
  call recall()
  return MCP dual response
```

This pattern maps directly to fmm navigation commands.

## Evidence In fmm

### MCP Is Embedded In The CLI Crate

`McpServer` is defined in:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/mcp/mod.rs
```

Important ranges:

```text
McpServer: lines 79 to 84
McpServer::from_store: lines 130 to 141
McpServer::handle_tool_call: lines 275 to 352
```

`handle_tool_call` dispatches directly to `tools::tool_*` functions:

```text
fmm_lookup_export
fmm_list_exports
fmm_dependency_graph
fmm_search
fmm_read_symbol
fmm_file_outline
fmm_list_files
fmm_glossary
```

This is acceptable for protocol dispatch. The problem is that some of those tools contain business logic that is repeated in CLI commands.

### Shared Code Depends Back On MCP Helpers

`read_symbol.rs` is shared by CLI and MCP, but it lives in the CLI crate and reaches into MCP internals:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/read_symbol.rs
```

Important ranges:

```text
ReadSymbolResult: lines 4 to 10
ReadSymbolContent: lines 12 to 16
ReadSymbolGuidance: lines 24 to 28
read_symbol_result: lines 121 to 181
resolve_export: lines 324 to 342
```

Boundary issue:

```text
read_symbol_result uses crate::mcp::MAX_RESPONSE_BYTES
resolve_export uses crate::mcp::tools::is_reexport_file
resolve_export uses crate::mcp::tools::find_concrete_definition
```

`glossary.rs` has the same pattern:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/glossary.rs
```

It uses:

```text
crate::mcp::tools::compute_import_specifiers
```

Those helpers belong in a shared capabilities layer, not under MCP.

### Repeated CLI And MCP Logic

Several commands duplicate logic across CLI and MCP.

#### list files

CLI:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/cli/commands/ls.rs
ls: lines 14 to 207
```

MCP:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/mcp/tools/list_files.rs
tool_list_files: lines 9 to 184
```

Shared behavior inside both:

```text
directory normalization
pattern matching
test/source/all filtering
sorting by name, loc, exports, downstream, modified
rollup by subdir
pagination
text formatting
```

#### list exports

CLI:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/cli/commands/exports.rs
exports: lines 18 to 46
export_matcher: lines 121 to 134
collect_pattern_matches: lines 136 to 163
print_all_exports: lines 165 to 202
```

MCP:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/mcp/tools/exports.rs
tool_list_exports: lines 7 to 105
```

Repeated behavior:

```text
regex versus substring matcher detection
directory filtering
method_index inclusion
pagination
format_list_exports_* selection
```

#### lookup

CLI:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/cli/commands/lookup.rs
lookup: lines 26 to 99
```

MCP:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/mcp/tools/lookup.rs
tool_lookup_export: lines 7 to 60
```

Repeated behavior:

```text
lookup order: export_locations, export_index, method_index
file entry lookup
collision note generation
format_lookup_export
```

#### outline

CLI:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/cli/commands/outline.rs
outline: lines 35 to 137
```

MCP:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/mcp/tools/outline.rs
tool_file_outline: lines 9 to 60
```

Repeated behavior:

```text
file lookup
directory validation
private member extraction
top level function extraction
reexport collection
format_file_outline
```

#### deps

CLI:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/cli/commands/deps.rs
deps: lines 14 to 139
```

MCP:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/mcp/tools/graph.rs
tool_dependency_graph: lines 9 to 79
```

Repeated behavior:

```text
depth validation
file lookup
source/test/all filtering
single hop versus transitive graph selection
format_dependency_graph*
```

#### search

CLI:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/cli/search.rs
SearchOptions: lines 60 to 71
search: lines 73 to 190
bare_search: lines 194 to 253
flag_search: lines 257 to 371
```

MCP:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/mcp/tools/search.rs
tool_search: lines 7 to 122
```

Repeated behavior:

```text
term plus structured filter intersection
filter file set construction
empty export note
export only fast path
depends_on footer
format_bare_search and format_filter_search choices
```

### Some Sharing Already Exists, In The Wrong Crate

`read_symbol` and `glossary` are partly shared:

```text
crates/fmm-cli/src/read_symbol.rs
crates/fmm-cli/src/glossary.rs
```

That is useful evidence. The codebase already wants a middle layer. It just does not have the crate boundary yet.

## Current Test Coverage That Reduces Risk

The repo already has strong parity tests.

CLI text versus CLI JSON:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/tests/cli_output_parity.rs
cli_text_and_json_outputs_have_semantic_parity: lines 29 to 51
```

MCP text versus CLI JSON:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/tests/cli_output_parity.rs
mcp_text_and_cli_json_outputs_have_semantic_parity: lines 53 to 76
```

Covered projections:

```text
Deps
ExportsFile
ExportsPattern
Glossary
Lookup
Ls
Outline
Read
SearchBare
SearchExport
SearchFilter
```

MCP integration tests also call through the real `SqliteMcpServer::call_tool` path:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/tests/mcp_tools.rs
```

Snapshot tests cover MCP text response formats:

```text
/Users/alphab/Dev/LLM/DEV/helioy/fmm/crates/fmm-cli/src/mcp/snapshot_tests.rs
```

These tests make the refactor much safer than a typical boundary move.

## Proposed Target Architecture

```text
fmm-core
  parser, manifest, resolver, search primitives, formatting primitives

fmm-store
  SQLite and in memory store implementations

fmm-capabilities
  typed navigation operations over Manifest and root Path
  request structs
  result structs
  shared validation
  projection helpers
  adapter neutral errors

fmm
  CLI args
  terminal rendering
  MCP protocol server
  MCP JSON argument parsing
  index lifecycle commands
```

Important rule:

```text
fmm-capabilities must not depend on fmm, fmm-cli, or MCP modules.
```

Preferred dependency shape:

```text
fmm-capabilities depends on:
  fmm-core
  serde
  serde_json, only if projections need it
  regex
  glob
  anyhow or thiserror

fmm-capabilities dev dependencies:
  fmm-store with test-support
  tempfile
  insta if snapshotting capability projections
```

`fmm-store` should remain outside normal capability dependencies unless the capabilities become store backed. The current fmm operations only need `Manifest` plus `root`.

## Candidate API Shape

Example module layout:

```text
crates/fmm-capabilities/src/lib.rs
crates/fmm-capabilities/src/error.rs
crates/fmm-capabilities/src/common.rs
crates/fmm-capabilities/src/list_files.rs
crates/fmm-capabilities/src/list_exports.rs
crates/fmm-capabilities/src/lookup.rs
crates/fmm-capabilities/src/outline.rs
crates/fmm-capabilities/src/dependency_graph.rs
crates/fmm-capabilities/src/search.rs
crates/fmm-capabilities/src/read_symbol.rs
crates/fmm-capabilities/src/glossary.rs
crates/fmm-capabilities/src/projection.rs
```

Example operation pattern:

```rust
pub struct ListFilesRequest {
    pub directory: Option<String>,
    pub pattern: Option<String>,
    pub sort_by: SortBy,
    pub order: Option<SortOrder>,
    pub group_by: Option<GroupBy>,
    pub filter: FileFilter,
    pub limit: Option<usize>,
    pub offset: usize,
}

pub enum ListFilesResult {
    Files(ListFilesPage),
    Rollup(ListFilesRollup),
}

pub fn list_files(
    manifest: &Manifest,
    root: &Path,
    request: ListFilesRequest,
) -> Result<ListFilesResult, FmmCapabilityError>;
```

Adapter use:

```text
CLI:
  load manifest
  build request
  call capability
  print text or JSON

MCP:
  parse JSON args
  build request
  call capability
  return text in MCP content wrapper
```

## What Should Move First

Move these first because they are already shared or boundary inverted:

```text
crates/fmm-cli/src/read_symbol.rs
crates/fmm-cli/src/glossary.rs
crates/fmm-cli/src/mcp/tools/common.rs
```

Then move duplicated operation logic:

```text
lookup
list exports
outline
dependency graph
list files
search
```

Leave these in CLI for now:

```text
generate
validate
clean
watch
init
status
completions
MCP JSON RPC server loop
build.rs generated help and schema work
```

## Concrete Work Plan

### Phase 1: Crate scaffold

Add `crates/fmm-capabilities/Cargo.toml`.

Update workspace dependencies:

```text
Cargo.toml
crates/fmm-cli/Cargo.toml
```

Add `src/lib.rs`, `src/error.rs`, and `src/common.rs`.

Move helper functions out of `mcp/tools/common.rs`:

```text
is_reexport_file
find_concrete_definition
compute_import_specifiers
glob_filename_matches
build_rollup
validate_not_directory
```

Expected value:

```text
read_symbol.rs and glossary.rs stop importing crate::mcp::tools
```

### Phase 2: Move existing shared behavior

Move:

```text
read_symbol.rs
glossary.rs
```

Change references:

```text
crate::read_symbol -> fmm_capabilities::read_symbol
crate::glossary -> fmm_capabilities::glossary
crate::mcp::MAX_RESPONSE_BYTES -> fmm_capabilities::constants::MAX_RESPONSE_BYTES
```

Keep exact text behavior at first.

### Phase 3: Extract duplicated operations

Extract one operation at a time:

1. `lookup`
2. `list_exports`
3. `outline`
4. `dependency_graph`
5. `list_files`
6. `search`

For each operation:

```text
create request type
create result type
move shared computation
leave CLI specific JSON structs if needed
leave MCP arg parsing in MCP
run parity tests
```

### Phase 4: Tighten adapters

After behavior is centralized:

```text
CLI command modules should mostly load manifest, build request, print result
MCP tool modules should mostly parse Value, build request, wrap ToolResult
No non MCP code should import crate::mcp
No MCP tool should reimplement capability logic
```

### Phase 5: Test and verify

Run:

```bash
cargo test -p fmm
cargo test -p fmm-capabilities
cargo test --workspace
fmm generate
fmm validate
```

Run parity focused tests while moving each command:

```bash
cargo test -p fmm --test cli_output_parity
cargo test -p fmm --test mcp_tools
cargo test -p fmm mcp::snapshot_tests
```

## LOE Detail

### Minimum useful refactor: 2 to 3 days

Scope:

```text
create fmm-capabilities
move common helpers
move read_symbol
move glossary
extract lookup and list_exports
fix imports
run focused tests
```

Benefits:

```text
removes inverted MCP helper dependency
reduces obvious repeated logic
creates the correct crate boundary
sets up future moves
```

Risks:

```text
some duplicated logic remains
CLI JSON projection may still be partly separate
search and list_files remain relatively heavy in adapters
```

### Clean target: 4 to 6 days

Scope:

```text
all minimum scope
extract outline, dependency graph, list_files, search
add typed requests and typed results
centralize shared validation
add capability unit tests
keep parity tests green after each move
```

Benefits:

```text
meaningful separation
less drift between CLI and MCP
easier future MCP improvements
easier future web or agent consumers
clear ownership of application behavior
```

Risks:

```text
search has subtle formatting and filter semantics
list_files has sorting, filtering, rollup, and pagination edge cases
snapshot churn if text formatting moves too aggressively
```

### Full separation: 7 to 10 days

Scope:

```text
all clean target scope
create separate fmm-mcp crate
move MCP server and tools out of fmm CLI crate
adjust build schema generation boundaries
update docs and release packaging
ensure binary distribution still includes the right server behavior
```

Benefits:

```text
strongest crate boundaries
MCP becomes independently testable
CLI crate becomes smaller
```

Risks:

```text
more packaging and release surface
more workspace churn
less direct value than the capabilities split
```

Recommendation: defer separate `fmm-mcp` until the capabilities crate is proven.

## Why This Is Worth Doing

The refactor has immediate value because the codebase already contains the symptoms:

```text
shared behavior inside fmm-cli
shared behavior reaching into mcp internals
duplicated CLI and MCP logic
parity tests that exist mainly because drift is possible
```

The capabilities crate gives fmm the same middle layer that context-matters already uses successfully.

The change should pay off if any of these are true:

```text
MCP tools will keep evolving
CLI JSON output will keep evolving
new navigation capabilities are planned
another consumer may need fmm behavior without the CLI crate
we want smaller, easier reviews for feature changes
```

## When To Skip Or Delay

Delay if the next work is only:

```text
small parser fixes
one off CLI help changes
release cleanup
bug fixes isolated to fmm-core or fmm-store
```

Do not start with a separate `fmm-mcp` crate unless there is a concrete need. The useful boundary is capabilities first.

## Success Criteria

The refactor is successful when:

```text
fmm-capabilities owns manifest backed navigation behavior
CLI and MCP adapters are thin
non MCP code no longer imports crate::mcp
MCP tools no longer duplicate CLI logic
cli_output_parity remains green
mcp_tools remains green
MCP snapshots remain intentionally unchanged or reviewed
fmm validate passes after reindexing
```

## Suggested First PR

First PR should stay small:

```text
add fmm-capabilities crate
move constants and common helpers
move read_symbol
move glossary
update CLI and MCP imports
run focused tests
```

Expected files changed:

```text
Cargo.toml
crates/fmm-cli/Cargo.toml
crates/fmm-capabilities/Cargo.toml
crates/fmm-capabilities/src/lib.rs
crates/fmm-capabilities/src/error.rs
crates/fmm-capabilities/src/common.rs
crates/fmm-capabilities/src/read_symbol.rs
crates/fmm-capabilities/src/glossary.rs
crates/fmm-cli/src/read_symbol.rs, removed or reduced
crates/fmm-cli/src/glossary.rs, removed or reduced
crates/fmm-cli/src/mcp/tools/common.rs
crates/fmm-cli/src/mcp/tools/read.rs
crates/fmm-cli/src/mcp/tools/glossary.rs
crates/fmm-cli/src/cli/commands/read.rs
crates/fmm-cli/src/cli/glossary.rs
```

That first PR should not try to move search, list files, or all projections. Those are better as follow up work once the crate boundary is established.

