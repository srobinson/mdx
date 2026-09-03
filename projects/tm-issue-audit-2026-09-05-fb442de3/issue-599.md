# 599: Port Transport Matters mechanically to MCP 2.1.1

URL: https://github.com/littleorgans/transport-matters/issues/599
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:36:27Z

# Outcome

Port the Transport Matters MCP code and tests mechanically from Python MCP SDK 1.28.1 to MCP 2.1.1 without changing transport behavior.

Parent: #593
Blocked by: #597

# Scope

- Change the dependency to `mcp>=2.1,<3` and regenerate `uv.lock`.
- Replace `FastMCP` imports and annotations with `MCPServer`.
- Delete the obsolete `FastMCPSettings.model_rebuild()` workaround.
- Rename SDK model fields from camel case to snake case.
- Preserve wire assertions with `model_dump(mode="json", by_alias=True)`.
- Update the shared test client fixture for `httpx2` and the two-item `streamable_http_client()` result.
- Update all affected MCP skin tests.

# Dependency expectations

- Add the matching `mcp-types` package.
- Add `opentelemetry-api`.
- Promote the existing `httpx2`, `httpcore2`, and `truststore` packages to runtime dependencies.
- Remove the MCP 1.x `httpx-sse` edge.
- Keep the direct Transport Matters `httpx` dependency.

# Constraints

- Keep the existing endpoint, stateless behavior, JSON response mode, and auth behavior unchanged.
- Transport configuration moves in the following issue.
- Do not add 2026-only cache or subscription features.

# Acceptance criteria

- No `mcp.server.fastmcp` import remains.
- No SDK camel-case attribute access remains.
- Dependency resolution succeeds on Python 3.14.
- MCP schema, inventory, auth, and action tests pass.
- `just check` and `just test` pass.

# Upstream reference

https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md

## Implementation guide

### Start here

Use `api/pyproject.toml`, `api/uv.lock`, `api/src/transport_matters/api/v1/controlplane_mcp.py` (`create_control_plane_mcp`, `ControlPlaneMcpAuthApp`), `api/src/transport_matters/api/v1/mcp_tool_catalog.py` (`McpToolRegistry`, `MCP_TOOL_CATALOG`), `api/src/transport_matters/main.py` (`create_app`), `api/src/transport_matters/api/v1/mcp_tooling.py` (`mcp_tool_result`), `api/src/transport_matters/api/v1/controlplane_mcp_test_support.py` (`control_plane_http_client`, `control_plane_mcp_session`), and `api/src/transport_matters/api/v1/test_controlplane_skins.py` (`_skin_app`, `FakeService`, `FakeResolver`).

### Direction

Start after #597. This is the mechanical MCP 2.1.1 port with the minimal transport argument move, `McpToolRegistry`, and extracted shared MCP test support. Port the landed FastMCP shape: one server in `create_control_plane_mcp`, one `McpToolRegistry` that registers collected callables, and Space plus browsing registrars collecting into that registry. Do not restore server ownership to the domain registrars. Change the direct SDK range to `mcp>=2.1,<3` and regenerate `api/uv.lock` for that path only. Replace FastMCP with `MCPServer`. Delete the obsolete settings rebuild workaround. Rename Python protocol fields to snake case and keep wire assertions with JSON aliases. Extract the two reusable client context managers into `controlplane_mcp_test_support.py` before protocol adaptation, then migrate every caller without forwarding aliases. Adapt the MCP session helper to `httpx2` and the two stream result. Keep the REST helper on `httpx`. Move the existing three transport arguments from `create_control_plane_mcp` to the existing `streamable_http_app` call in `create_app`. Keep endpoint, stateless behavior, JSON response mode, auth, catalog, filtered discovery, and call time authorization unchanged.

### Guardrails

Do not change tool catalog, effective authority, runtime capabilities, or discovery policy from #597. Do not restore direct SDK registration in Space or browsing modules. Do not add a compatibility wrapper, parallel server, or direct `mcp-types` import. Do not redesign transport policy; #600 owns the durable mount, server version, 4 MiB boundary, and dual protocol proof. Do not add cache, subscriptions, dynamic tool list changes, or SSE. Do not remove the direct `httpx` dependency or convert unrelated HTTP clients. `just check` and `just test` must pass.


## Sub issues
[]
