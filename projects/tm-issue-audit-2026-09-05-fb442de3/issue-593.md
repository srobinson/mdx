# 593: Program: Per-runtime control-plane grants and MCP tool catalogs

URL: https://github.com/littleorgans/transport-matters/issues/593
State: open
Labels: enhancement, P2
Updated: 2026-09-02T15:54:15Z

# Problem

Transport Matters currently combines two mismatched launch policies:

- The persisted Canvas control-plane setting applies one grant to every direct CMDK agent launch.
- MCP `launch()` defaults child authority to `none` unless the caller supplies `grant`.
- A granted run discovers the full 34-tool Transport Matters MCP catalog, even when its runtime needs only a subset.

Agent runtimes need to declare their requested control-plane grant and MCP capabilities. Transport Matters must apply the Canvas setting as the global user consent gate, calculate effective authority, and expose only the permitted tool catalog.

# Decisions

- The persisted Canvas setting remains the global user consent gate.
- Each runtime under `~/.agent-runtimes` declares its requested grant and MCP capabilities.
- Effective authority cannot exceed the Canvas gate or the launching principal.
- Transport Matters keeps one MCP endpoint and one control-plane service.
- `tools/list` is filtered from the run-scoped bearer policy.
- Every tool keeps call-time authorization and audit checks.
- Tool catalogs remain fixed for the lifetime of a run.
- Directory and worktree restrictions belong to a future security design.
- Filtering ships on MCP SDK 1.28.1 before the isolated MCP 2.x migration.

# Work

1. Publish runtime grant and MCP capabilities from `.agent-runtimes`.
2. Consume the runtime capability contract in Transport Matters.
3. Resolve and persist effective control authority.
4. Define the canonical 34-tool MCP catalog.
5. Filter MCP discovery by run policy.
6. Update Canvas consent and launch UX.
7. Migrate mechanically to MCP 2.x.
8. Migrate MCP transport and prove real clients.

# Acceptance criteria

- Each subissue maps to one independently reviewable PR.
- Runtime declarations drive CMDK and MCP launch behavior.
- The Canvas gate can prevent a runtime from receiving its requested authority.
- Observer and director runs receive deterministic, bounded tool catalogs.
- Direct calls to hidden tools still fail through authoritative call-time checks.
- Claude, Codex, and Grok pass real launch and MCP smoke tests.
- `.agent-runtimes` generation and audit pass.
- Transport Matters `just check` and `just test` pass.

# Upstream references

- MCP tools specification: https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx
- Python SDK migration guide: https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md
- Scope-filtered discovery proposal: https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1881

## Sub issues
[
  {
    "number": 2,
    "state": "closed",
    "title": "Publish per-runtime control-plane grants and MCP capabilities"
  },
  {
    "number": 594,
    "state": "closed",
    "title": "Consume runtime authority and MCP capability schema v4"
  },
  {
    "number": 595,
    "state": "open",
    "title": "Resolve and persist effective control-plane authority"
  },
  {
    "number": 596,
    "state": "open",
    "title": "Define the canonical Transport Matters MCP tool catalog"
  },
  {
    "number": 597,
    "state": "open",
    "title": "Filter MCP tool discovery by run policy"
  },
  {
    "number": 598,
    "state": "open",
    "title": "Update Canvas consent and runtime authority UX"
  },
  {
    "number": 599,
    "state": "open",
    "title": "Port Transport Matters mechanically to MCP 2.1.1"
  },
  {
    "number": 600,
    "state": "open",
    "title": "Relocate MCP transport policy and prove dual-protocol clients"
  }
]
