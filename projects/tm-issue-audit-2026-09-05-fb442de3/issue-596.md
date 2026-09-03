# 596: Define the canonical Transport Matters MCP tool catalog

URL: https://github.com/littleorgans/transport-matters/issues/596
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:10:33Z

# Outcome

Replace decorator order and name-prefix inference with one canonical, ordered catalog for all 34 Transport Matters MCP tools.

Parent: #593

# Current baseline

- 34 tools total.
- 14 tools are available to observers.
- 20 tools require director authority.
- Natural domains are core control plane, Space and Canvas management, and browser control.

# Scope

- Introduce one catalog that maps every tool name to a stable capability identifier and minimum grant.
- Record read-only, destructive, and open-world hints where the current behavior supports them.
- Make the catalog the source for deterministic registration order and contract tests.
- Keep existing tool implementations and response types unchanged.
- Reject duplicate names, missing catalog entries, unknown capabilities, and catalog entries with no registered implementation.
- Document capability identifiers as a contract. Raw prefixes remain an implementation detail.

# Constraints

- No behavior change in this PR.
- Do not split the MCP server.
- Do not move domain operations out of the existing control-plane service.
- Tool exposure remains separate from call-time authorization.

# Acceptance criteria

- All 34 tools appear exactly once.
- Catalog order is deterministic.
- Every tool has one capability and one minimum grant.
- Existing MCP schemas and outputs remain byte-equivalent where ordering permits.
- Contract tests fail when a registrar and catalog drift.
- Existing MCP inventory and skin tests pass.
- `just check` and `just test` pass.

## Implementation guide

### Start here

Reuse `controlplane_mcp.py` (`create_control_plane_mcp`) as the single mounted server, `space_mcp.py` (`register_space_mcp_tools`, `SpaceMcpAdapter`) for the thirteen Space, Canvas, and Worktree callables, and `browsing_mcp.py` (`register_browsing_mcp_tools`) for the eight browser callables. Keep result envelopes in `mcp_tooling.py` (`McpToolOutput`). Reuse the closed capability type from issue 594 in `controlplane/models.py` (`ControlPlaneGrantRole`). Leave call time checks in `ControlPlaneService` and `ControlPlaneLauncher`. Extend `test_controlplane_action_skins.py` (`test_mcp_tool_schemas_are_the_agent_contract`).

### Direction

- Create one ordered catalog for all 34 tools. Each entry has a tool name, the capability identifier from issue 594, a minimum grant, and `ToolAnnotations`. Own that catalog in `mcp_tool_catalog.py` (`McpToolCatalogEntry`, `McpToolRegistry`, `MCP_TOOL_CATALOG`). Collect existing nested callables first, validate catalog and implementation sets, then register with `FastMCP.add_tool` in catalog order.
- Keep the current 34 name order and the fourteen observer / twenty director split. Map tools onto the producer identifiers for core control plane, Space management, and browser control. Do not store domain labels as a second string vocabulary. Read only does not imply observer access. `wait_for_reply`, `space_list`, and `space_get` remain director tools.
- Tool names, descriptions, schemas, and result bodies stay unchanged. Only deterministic order and annotations change in `tools/list`. Catalog metadata is declarative. It never authorizes a call.

### Guardrails

- Existing authorization remains. Bearer resolution, core director checks, Space `require_director` and `require_bound_space`, and browser gateway checks stay on their current paths. No catalog value enters the principal. Validation completes before the first `FastMCP.add_tool`, so a broken catalog never exposes a partial server. Runtime ids, skill names, tool names, and prefixes have no capability meaning.
- Do not filter `tools/list`, parse runtime capability declarations, resolve effective launch authority, split the MCP server, rename tools, or retain prefix inference. Prove exact 34 name order, the grant split, annotation presence, unchanged input and output schemas, and registrar drift, then `just check` and `just test`.


## Sub issues
[]
