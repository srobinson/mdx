# 597: Filter MCP tool discovery by run policy

URL: https://github.com/littleorgans/transport-matters/issues/597
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:36:24Z

# Outcome

Return only the Transport Matters MCP tools permitted by the authenticated run policy during `tools/list`.

Parent: #593
Blocked by: #595 and #596

# Scope

- Add a small MCP server adapter that overrides tool listing.
- Resolve the run-scoped bearer for each request.
- Filter the canonical catalog by effective grant and allowed runtime capabilities.
- Preserve canonical deterministic ordering.
- Return the full catalog for explicit in-process contract inspection with no request principal, if that remains the chosen test contract.
- Keep all tools registered internally.
- Preserve existing call-time identity, live-capture, role, domain entitlement, and audit checks.
- Keep filtered policy fixed for the bearer lifetime.

# Protocol constraints

- Filtering must be a pure function of the presented credential.
- The list must not vary by connection identity or prior requests.
- Hidden tools must not leak through `tools/list` metadata.
- Tool annotations remain advisory.
- Call-time authorization remains authoritative.

# Acceptance criteria

- Observer runs list only observer tools within their runtime capabilities.
- Director runs list only director and observer tools within their runtime capabilities.
- Two bearers with different runtime capabilities receive different deterministic catalogs.
- A guessed call to a hidden director tool fails before side effects.
- An expired or revoked bearer receives no usable catalog.
- Catalog filtering does not fork domain authorization rules.
- MCP inventory, auth, action, and real-client smoke tests pass.
- `just check` and `just test` pass.

# Upstream reference

https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx

## Implementation guide

### Start here

Use `api/src/transport_matters/api/v1/mcp_tool_catalog.py` (`McpToolCatalogEntry`, `McpToolRegistry`, `MCP_TOOL_CATALOG`, `catalog_tool_is_eligible`), `api/src/transport_matters/api/v1/controlplane_mcp.py` (`create_control_plane_mcp`, `ControlPlaneMcpAuthApp`, `_McpControlPlaneAdapter._principal`), `api/src/transport_matters/controlplane/models.py` (`ControlPlanePrincipal`), `api/src/transport_matters/capture_rpc.py` (`_CaptureRunFacts`, `CaptureLeaseRegistry.prepare_capture`, `CaptureLeaseRegistry.resolve_control_plane_grant`), `api/src/transport_matters/api/v1/test_controlplane_mcp_discovery.py`, `api/src/transport_matters/api/v1/test_controlplane_skins.py` (`_skin_app`, `_mcp_session`), and `docs/CONTROLPLANE.md`.

### Direction

Start after #595 and #596. This issue applies one role plus capability eligibility rule to `tools/list` and `tools/call` and keeps domain auth. Freeze the validated runtime capability tuple in `_CaptureRunFacts` when `CaptureLeaseRegistry.prepare_capture` registers the live capture, then copy it into `ControlPlanePrincipal` from `CaptureLeaseRegistry.resolve_control_plane_grant`. Add one pure `catalog_tool_is_eligible` predicate beside the canonical catalog. Its only policy inputs are the catalog entry, the principal effective role, and the frozen capability tuple. Both axes are required. Subclass FastMCP so list and call use that predicate for authenticated requests. List keeps eligible original tool objects in canonical order. Call rejects unknown or ineligible names with the existing unknown tool error before FastMCP dispatch. Keep all 34 implementations registered. Eligible calls continue through existing adapters and domain authorization. Hidden calls stop before implementation, adapter, audit, or gateway work. Filtering is a pure function of the presented credential and stays fixed for the bearer lifetime. Direct in process listing with no request principal may retain the full catalog for contract inspection. Network requests always have identity after auth. Keep `tools.listChanged` false. Document the intersection of effective role and frozen capabilities in `docs/CONTROLPLANE.md`.

### Guardrails

Do not add a second grant order, catalog, capability vocabulary, or eligibility rule. Do not unregister hidden tools, mutate the shared tool manager, or infer policy from names, prefixes, runtime ids, or skills. Do not fork domain authorization or drop call time role, workspace, owner, Space, Canvas, Worktree, DevTools, audit, live capture, or revocation checks. Do not change Canvas consent, MCP SDK versions, or transport. Do not add a database migration, connection scoped cache, or registry reread during list or call. Prove the predicate, real client list and call, hidden versus absent error shape, and frozen capability projection. `just check` and `just test` must pass.


## Sub issues
[]
