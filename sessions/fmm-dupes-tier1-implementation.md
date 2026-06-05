---
title: fmm dupes Tier 1 implementation
type: sessions
tags: [backend, fmm, cli, mcp, duplication]
summary: Implemented `fmm dupes` Tier 1 structural duplicate clustering across CLI and MCP.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented Tier 1 `fmm dupes` on branch `feat/dupes-tier1`, commit `0627655`, PR#163.

Key decisions:

- Added `crates/fmm-core/src/dupes.rs` rather than growing `similarity.rs` past the line threshold.
- Reused the existing candidate collector and scorer through shared `Candidate`, `collect_candidates`, `score_candidates`, and `candidate_shape_key` seams.
- Split the large CLI command enum into `crates/fmm-cli/src/cli/command_tree.rs` before adding the new command.
- Kept Tier 2 clone detection out of scope.

## API Contract

CLI:

```text
fmm dupes [--dir <prefix>] [--kind <kind>]... [--min-score <float>] [--limit <n>] [--include-tests] [--json]
```

MCP:

```text
fmm_dupe_clusters({
  directory?: string,
  kind?: string[],
  min_score?: number,
  limit?: number,
  include_tests?: boolean
})
```

JSON result shape:

```typescript
interface DupeClustersResult {
  clusters: Array<{
    score: number;
    members: Array<{
      name: string;
      file: string;
      lines: [number, number];
      signature?: string;
      kind?: string;
    }>;
  }>;
  stats: {
    candidates: number;
    blocks: number;
    comparisons: number;
    clusters: number;
  };
  diagnostics?: Array<{
    code: string;
    message: string;
  }>;
}
```

## Database Changes

No database schema changes.

`fmm dupes` reads the existing manifest data from `.fmm.db` and uses current export and method metadata only.

## Security Considerations

- No new network surface.
- No new filesystem writes except normal CLI stdout.
- CLI and MCP inputs are typed and deserialized through existing Clap and Serde boundaries.
- No SQL was added.

## Performance Notes

- Candidate collection is single pass over existing manifest symbols.
- Blocking uses declaration kind, rare name tokens, and signature shape.
- Oversized blocks are split by shape and then capped with structured diagnostics instead of silently truncating.
- The real repo dogfood run completed and surfaced plausible clusters including `ListEntry` CLI/MCP aliases, parser `DESCRIPTOR` constants, and `CallSiteVerifier.bare_call_result` methods.

Verification performed:

- `just check`
- `cargo test -q -p fmm-core dupes`
- `cargo test -q -p fmm --test cli_dupes`
- `cargo test -q -p fmm --test mcp_tools dupe_clusters`
- `cargo test -q -p fmm --test mcp_protocol mcp_protocol_tools_list`
- `cargo test -q -p fmm --test cli_flags tools_toml_cli_flags_are_exposed_by_clap_commands`

## Open Items

- The default `DEFAULT_THRESHOLD` matches `fmm similar` as requested, but real repo output is noisy. Follow up calibration can tune the default or add stronger cluster quality controls.
- Tier 2 body fingerprint clone detection remains out of scope.
- The full `just ci` gate was intentionally left to the orchestrator per the build directive.

## Fix Round: Default Threshold Calibration

Follow-up commit `5ba6a5c` fixed the default real-repo behavior after PR#163 review showed `fmm dupes` inherited the probe-oriented `similarity::DEFAULT_THRESHOLD` and collapsed unrelated same-kind symbols into mega-clusters.

Changes:

- Added `DEFAULT_DUPES_MIN_SCORE = 0.90`, distinct from `fmm similar`.
- Kept `--min-score` overridable for exploratory lower-threshold scans.
- Added a cluster sanity cap diagnostic for clusters over 64 members.
- Reworked the fixture to include several unrelated same-kind, same-shape functions plus one high-similarity pair so the default threshold guards against the real failure mode.

Verification:

- `cargo test -q -p fmm-core dupes`
- `INSTA_UPDATE=always cargo test -q -p fmm --test cli_dupes`
- `cargo test -q -p fmm --test mcp_tools dupe_clusters`
- `cargo run -q -p fmm -- generate --force && cargo run -q -p fmm -- dupes --limit 4`
- `just check`

Real repo default output now starts with tight clusters: `signature_end_byte`, `VERSION`, `extract_top_level_functions`, and `extract_private_members`; no 595-member function mega-cluster.
