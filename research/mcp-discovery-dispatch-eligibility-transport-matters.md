---
title: MCP Discovery and Dispatch Eligibility in Transport Matters
type: research
tags: [transport-matters, mcp, control-plane, authorization, issue-597]
summary: Issue 597 now applies one role and capability predicate to both tool discovery and initial call dispatch using the verified MCP 1.28.1 seams.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

## Executive Summary

Transport Matters exposes 34 MCP tools through one authenticated FastMCP server. Issue 597 was corrected so the canonical role and runtime capability predicate governs both `tools/list` and initial `tools/call` dispatch. A hidden call now fails with the existing unknown tool result before registered implementation, adapter, audit, Canvas, or Gateway work.

## Project Metadata

- Language: Python 3.14 or newer
- API framework: FastAPI
- MCP SDK constraint: `mcp>=1.28,<2`
- Installed and locked MCP version: 1.28.1
- Build and dependency system: uv with `api/pyproject.toml` and `api/uv.lock`
- Product role: context control plane and capture proxy for coding agents

## Architecture

The mounted MCP server is created by `create_control_plane_mcp` in `api/src/transport_matters/api/v1/controlplane_mcp.py:393-529`. `ControlPlaneMcpAuthApp` resolves each bearer before SDK authentication in `api/src/transport_matters/api/v1/controlplane_mcp.py:160-187`. `ControlPlaneTokenVerifier.verify_token` projects the resolved principal into `ControlPlaneAccessToken` in `api/src/transport_matters/api/v1/controlplane_mcp.py:146-157`.

The live capture is the policy lifetime boundary. `CaptureLeaseRegistry.prepare_capture` records immutable run facts in `api/src/transport_matters/capture_rpc.py:152-206`. `CaptureLeaseRegistry.resolve_control_plane_grant` requires the matching live lease before constructing `ControlPlanePrincipal` in `api/src/transport_matters/capture_rpc.py:323-345`.

Browser calls demonstrate the vulnerable path addressed by the correction. `BrowsingMcpAdapter.browser_open` delegates into the gateway path in `api/src/transport_matters/api/v1/browsing_mcp.py:70-81`. `open_browser_pane` checks director role immediately before the Gateway request in `api/src/transport_matters/api/v1/controlplane_gateway_browsing.py:94-115`. A director without browser capability passes that role check, so server dispatch must reject the hidden tool earlier.

## Key Patterns

### One catalog predicate

The planned `catalog_tool_is_eligible` predicate belongs beside `MCP_TOOL_CATALOG` in `api/src/transport_matters/api/v1/mcp_tool_catalog.py`. Its policy inputs are the canonical `McpToolCatalogEntry`, effective role, and frozen runtime capability tuple. Both role sufficiency and capability membership are required.

### Registered implementations stay stable

All 34 implementations remain registered in one tool manager. Discovery filters the original tool objects without changing canonical relative order. Dispatch checks the same predicate before delegating to the registered implementation. Existing domain authorization remains additional enforcement for eligible calls.

### Hidden and absent calls are indistinguishable

The installed SDK already raises `ToolError("Unknown tool: {name}")` from `ToolManager.call_tool` for an absent registration. Policy hidden names use the same error. The resulting `CallToolResult` has `isError` true and repeats only the caller supplied name, with no role, capability, annotation, schema, or registration metadata.

## Detailed Findings

### Verified MCP 1.28.1 seams

- `api/.venv/lib/python3.14/site-packages/mcp/server/fastmcp/server.py:302-313`: `FastMCP._setup_handlers` registers the instance `list_tools` and `call_tool` methods.
- `api/.venv/lib/python3.14/site-packages/mcp/server/fastmcp/server.py:315-330`: `FastMCP.list_tools` projects every registered tool into protocol metadata.
- `api/.venv/lib/python3.14/site-packages/mcp/server/fastmcp/server.py:343-346`: `FastMCP.call_tool` delegates directly to `ToolManager.call_tool`.
- `api/.venv/lib/python3.14/site-packages/mcp/server/fastmcp/tools/tool_manager.py:81-93`: `ToolManager.call_tool` resolves the registration, emits the unknown tool error when absent, then runs the tool.
- `api/.venv/lib/python3.14/site-packages/mcp/server/lowlevel/server.py:498-595`: `Server.call_tool` converts thrown tool errors into error results. FastMCP registers this handler with input validation disabled.
- `api/.venv/lib/python3.14/site-packages/mcp/server/lowlevel/server.py:473-480`: `Server._make_error_result` creates the existing one text item `CallToolResult` error shape.

The small Transport Matters subclass is therefore the narrow seam. `list_tools` calls `super().list_tools()` and filters visible objects. `call_tool` resolves the same catalog entry, applies the same predicate, raises the existing unknown tool error when absent or ineligible, and delegates only eligible names to `super().call_tool`.

### Required regression proof

The focused test must authenticate a director principal that has core capability but lacks browser capability, then call `browser_open` by name through the real streamable HTTP client. It must assert the unknown tool error and prove that browser adapter, audit, Canvas, and Gateway sentinels remain untouched.

Separate tests cover:

1. Sufficient role with missing capability.
2. Present capability with insufficient role.
3. Hidden and absent calls sharing one error shape.
4. Visible eligible calls reaching their registered implementation and existing domain checks.
5. Stable canonical ordering and complete removal of hidden list metadata.

### Issue delivery state

GitHub issue `littleorgans/transport-matters#597` was edited through `gh issue edit`. Its title, open state, `enhancement` and `P2` labels, parent, blockers, scope, and acceptance criteria were preserved. The body was fetched again and matched the prepared text exactly. No repository source or git state was changed.

## Dependencies

- MCP 1.28.1 provides FastMCP registration, tool manager dispatch, `ToolError`, and low level error normalization.
- Issue 594 provides the closed runtime capability type and validated tuple.
- Issue 595 provides effective authority and its canonical role order.
- Issue 596 provides the ordered 34 tool catalog, catalog entries, and registration flow.
- FastAPI and the existing auth middleware resolve one request principal for discovery, dispatch, and adapters.

## Relevance to Helioy

This design gives runtime policy a single enforceable boundary without duplicating domain authorization. It also keeps runtime capability denial opaque, deterministic, and independent of mutable registry state during a live capture. The same pattern applies to other Helioy MCP servers that expose a shared implementation catalog to principals with different runtime grants.

## Open Questions

- Recheck the exact capability type and effective role comparator after issues 594, 595, and 596 land. The issue deliberately does not invent replacements for blocker owned symbols.
- Confirm whether trusted direct in process `call_tool` tests need the no identity bypass retained for list inspection. Network calls must always use authenticated eligibility.
- Revalidate the MCP SDK seams if issue 599 changes the installed major version before implementation.
