# Codebase Map fmm Feedback: runtime-matters

Date: 2026-05-25
Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/runtime-matters`
Artifact: `MAP.md`

## Context

This evaluation records how useful fmm was for generating an onboarding codebase map for `runtime-matters`. The map itself should stay focused on the codebase and diagrams. Tool feedback belongs here.

The final pass used the fmm MCP tools as the primary navigation surface, after an initial correction away from using the fmm CLI and outline only.

## What Was Useful

1. `fmm_list_files` gave a fast, accurate crate level size map and separated source from tests without reading files.
2. `sort_by: "downstream"` identified the real blast radius hubs, especially `rtm-core/src/lib.rs`, `rtm-daemon/src/server.rs`, and `rtm-cli/src/cli/output.rs`.
3. `fmm_dependency_graph` was the best tool for map accuracy. It exposed daemon flow edges such as `handler.rs -> backend.rs -> docker_runtime.rs -> docker_argv.rs`, and store edges such as `lifecycle.rs -> codec.rs`.
4. `fmm_lookup_export` and `fmm_read_symbol` were the safest way to anchor the map to exact contract lines without opening large files.
5. `fmm_glossary` was useful for test routing. It quickly showed which tests import `SpawnRequest`, `RuntimeRpc`, `MountSpec`, `LifecycleStore`, and client symbols.
6. `fmm_dependency_cycles` was useful as a warning system, but the reported Rust cycles mostly describe module facades and re exports rather than design problems.

## Limits To Account For

1. fmm does not replace Cargo metadata. Package names and crate dependency names still came from `cargo metadata`.
2. Rust re export hubs can make `fmm_glossary` broad. `lilo-rm-core/src/lib.rs` causes many contract symbols to look globally imported. Use file qualified symbol reads and dependency graphs to verify actual behavior.
3. Duplicate names need qualified reads. For example, `docker_run_launch` exists in both `docker_argv.rs` and `docker_runtime.rs`.
4. fmm is source focused. Authored TOML, generated README sections, shell scripts, and docs still need direct inspection.
5. Broad fuzzy export searches are less reliable than focused symbol, file, and dependency queries. For map work, small targeted fmm calls beat a single broad search.

## Recommended Codebase Map Pattern

Use fmm MCP tools for source structure:

```text
fmm_list_files(group_by: "subdir")
fmm_list_files(filter: "source", sort_by: "downstream")
fmm_dependency_graph(file: "...", depth: 1, filter: "source")
fmm_lookup_export(name: "...")
fmm_read_symbol(name: "...", line_numbers: true)
fmm_glossary(pattern: "...", mode: "source")
fmm_glossary(pattern: "...", mode: "tests")
fmm_dependency_cycles(filter: "source", edge_mode: "runtime")
```

Then use repo native tools for surfaces fmm does not index:

```text
cargo metadata --no-deps --format-version 1
rg --files
sed -n ...
```

Render validate any Mermaid diagrams with `mmdc` when available.
