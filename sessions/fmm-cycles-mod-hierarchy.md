---
title: fmm cycles module hierarchy filtering
type: sessions
tags: [backend, fmm, cycles, mcp]
summary: Implemented default module hierarchy filtering and explainable cycle edges for fmm cycles.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented PR#157 on branch `feat/cycles-exclude-mod-hierarchy` at `9404adf`.

Key decisions:

- `fmm cycles` now excludes module hierarchy facade edges by default.
- `--include-mod-hierarchy` restores the previous SCC set.
- `--explain` and `--edges` show sorted intra-SCC edges with their edge kind.
- Module hierarchy is classified in `EdgeKind`, then filtered through `CycleOptions` instead of being rederived in the cycle command.

## API Contract

CLI:

```text
fmm cycles [FILE] [--filter all|source|tests] [--edge-mode runtime|all] [--include-mod-hierarchy] [--explain|--edges] [--json]
```

MCP:

```typescript
interface DependencyCyclesArgs {
  file?: string;
  filter?: "all" | "source" | "tests";
  edge_mode?: "runtime" | "all";
  include_mod_hierarchy?: boolean;
  explain?: boolean;
}
```

JSON output now returns cycle objects. When `--explain` is set, each object includes sorted edges:

```typescript
interface CycleJson {
  files: string[];
  edges?: Array<{ source: string; target: string; kind: string }>;
}
```

## Database Changes

None. This change uses existing manifest data and graph construction.

## Security Considerations

No new external input surfaces beyond boolean CLI and MCP options. Existing strict MCP argument deserialization remains in place with `deny_unknown_fields`.

## Performance Notes

Cycle filtering remains in graph traversal. Edge explanation walks intra-SCC downstream edges only for reported components, then sorts deterministically.

Verification:

- `just check`
- `cargo nextest run --workspace -E 'test(dependency_cycles)'`
- `cargo test -p fmm every_advertised_schema_property_is_accepted_by_its_struct -- --nocapture`
- `cargo run -p fmm -- cycles --filter source`
- `cargo run -p fmm -- cycles --include-mod-hierarchy --explain`
- `cargo run -p fmm -- cycles --json --explain`

## Open Items

`fmm cycles --filter source` still reports one real source SCC between `resolver/deno.rs` and `resolver/workspace.rs`. That is outside the module hierarchy filtering slice.
