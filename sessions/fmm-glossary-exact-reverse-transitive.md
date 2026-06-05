---
title: fmm Glossary Exact and Reverse Transitive Deps
type: sessions
tags: [backend, fmm, cli, mcp, dependency-graph]
summary: Added exact glossary matching plus reverse transitive dependency closure for CLI and MCP.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary
Implemented PR#161 on branch `feat/glossary-exact-reverse-transitive`, commit `2d15a9e`.

Key decisions:

- Added `GlossaryNameMatch` so default glossary behavior remains case-insensitive substring matching, while `--exact` and MCP `exact` require an exact full export name.
- Added graph-backed reverse dependency closure through `reverse_dependency_closure`, with a visited set for cycle safety and deterministic path sorting.
- Added `fmm deps --reverse --transitive` and MCP `reverse: true, transitive: true` output with `reverse_deps_count`.
- Kept existing dependency graph output unchanged unless new flags are supplied.

## API Contract
CLI additions:

```text
fmm glossary <PATTERN> --exact
fmm deps <FILE> --reverse
fmm deps <FILE> --reverse --transitive
fmm deps <FILE> --reverse --transitive --json
```

MCP additions:

```typescript
interface FmmGlossaryArgs {
  pattern: string;
  exact?: boolean;
  mode?: "source" | "tests" | "all";
  limit?: number;
  precision?: "named" | "call-site";
  truncate?: boolean;
}

interface FmmDependencyGraphArgs {
  file: string;
  depth?: number;
  filter?: "all" | "source" | "tests";
  reverse?: boolean;
  transitive?: boolean;
}
```

Reverse JSON output:

```typescript
interface ReverseDepsJson {
  file: string;
  depth: number; // -1 means full closure
  reverse_deps_count: number;
  reverse_deps: Array<{ file: string; depth: number }>;
}
```

## Database Changes
None. The change uses existing manifest files, graph edges, and reverse dependency indexes.

## Security Considerations
No new external input boundary beyond existing CLI and MCP argument parsing. MCP args remain `deny_unknown_fields`. New boolean flags are schema documented through `tools.toml` and generated schema output.

## Performance Notes
Reverse closure uses the existing graph query path when available and falls back to `Manifest::find_dependents` for programmatic manifests. Cycle protection uses a visited set. Results are sorted deterministically after traversal.

Verification performed:

- `just check`
- `cargo test -p fmm-core build_glossary_exact_matches_only_full_export_name -- --nocapture`
- `cargo test -p fmm-core reverse_dependency_closure -- --nocapture`
- `cargo test -p fmm --test cli_glossary -- --nocapture`
- `cargo test -p fmm --test cli_deps -- --nocapture`
- `cargo test -p fmm --test mcp_tools -- --nocapture`
- `cargo test -p fmm --test cli_flags tools_toml_cli_flags_are_exposed_by_clap_commands -- --nocapture`
- `cargo run -q -p fmm -- glossary Manifest --exact --mode all --limit 20`
- `cargo run -q -p fmm -- deps crates/fmm-core/src/manifest/mod.rs --reverse --transitive`

## Open Items
The orchestrator owns full `just ci` gating. No follow-up split was needed for this slice.
