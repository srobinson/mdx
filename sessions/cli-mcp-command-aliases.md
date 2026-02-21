---
title: CLI and MCP command alias alignment
type: sessions
tags: [backend, fmm, cli, mcp, aliases, alp-2707]
summary: Added visible CLI aliases that mirror MCP navigation tool names while preserving short canonical commands.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented and pushed `7defc6b feat(cli): add MCP-derived command aliases` on `nancy/ALP-2707`.

The canonical CLI remains short and ergonomic, while long aliases mirror MCP tool names with the `fmm_` prefix removed and underscores converted to CLI hyphens. Phase A and Phase B reviewer signoff were received over helioy-bus before push.

## API Contract

No HTTP or GraphQL API changes.

CLI contract added:

| MCP tool | Canonical CLI | CLI alias |
|---|---|---|
| `fmm_lookup_export` | `fmm lookup` | `fmm lookup-export` |
| `fmm_list_exports` | `fmm exports` | `fmm list-exports` |
| `fmm_dependency_graph` | `fmm deps` | `fmm dependency-graph` |
| `fmm_dependency_cycles` | `fmm cycles` | `fmm dependency-cycles` |
| `fmm_read_symbol` | `fmm read` | `fmm read-symbol` |
| `fmm_file_outline` | `fmm outline` | `fmm file-outline` |
| `fmm_list_files` | `fmm ls` | `fmm list-files` |

`fmm_search` and `fmm_glossary` already align after removing the `fmm_` prefix.

## Database Changes

No database schema or migration changes.

## Security Considerations

No authentication, authorization, or data mutation surface changes. The change only adds clap aliases for existing command paths.

## Performance Notes

Aliases dispatch through the same clap variants and execution paths as the existing canonical commands. Manual equivalence check confirmed byte-identical JSON output for `fmm deps crates/fmm-cli/src/cli/mod.rs --json` and `fmm dependency-graph crates/fmm-cli/src/cli/mod.rs --json`.

## Verification

- `just check` passed.
- `just test` passed: 1258 tests passed, 3 skipped, doctests ok.
- `fmm validate` passed: 410 files current.
- Manual help check passed for canonical and alias commands.
- `fmm --help` remained the curated short command list.
- Reviewer independently re-ran checks and signed off with: `I sign off on the CLI/MCP naming fix as currently filed`.

## Open Items

Reviewer noted one non-blocking future improvement: `fmm <cmd> --help` does not render an explicit aliases line under the current clap help configuration. Alias discoverability is currently covered by shell completions plus README and generated SKILL mapping tables.
