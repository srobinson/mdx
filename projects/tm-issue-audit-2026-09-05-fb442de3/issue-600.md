# 600: Relocate MCP transport policy and prove dual-protocol clients

URL: https://github.com/littleorgans/transport-matters/issues/600
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:36:29Z

# Outcome

Complete the MCP 2.1.1 migration by relocating transport policy, setting server identity, and proving legacy and modern clients against the real mounted endpoint.

Parent: #593
Blocked by: #599

# Scope

- Add one owner for constructing the mounted control-plane MCP ASGI app.
- Pass `streamable_http_path="/"`, `json_response=True`, and `stateless_http=True` to `streamable_http_app()`.
- Keep the public endpoint at `/mcp` through the existing exact-path wrapper.
- Supply the Transport Matters server version explicitly.
- Accept and test the MCP 2.x 4 MiB request-body limit.
- Verify that auth and token resolution remain per request.
- Add dual-era tests for the 2025 handshake path and 2026 request path.
- Run one real Claude or Codex home against the preview backend.

# Constraints

- The same URL must serve supported legacy and modern protocol clients.
- Do not add dynamic tool-list changes in this PR.
- Do not add directory or worktree authorization.
- Keep filtered catalogs fixed for each run bearer.

# Acceptance criteria

- Omitting any of the three required transport settings fails a focused test.
- Legacy initialize, `tools/list`, and `tools/call` succeed.
- Modern `server/discover`, `tools/list`, and `tools/call` succeed where supported.
- A valid MCP request of exactly 4194304 bytes reaches normal request handling and returns 200; the same request at 4194305 bytes returns 413.
- Claude, Codex, and Grok seeded configurations remain compatible.
- A real captured run lists its bounded catalog and completes one MCP call.
- The API MCP skin suite passes.
- `just check` and `just test` pass.

# Upstream references

- https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md
- https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/whats-new.md

## Implementation guide

### Start here

Use `api/src/transport_matters/api/v1/controlplane_mcp.py` (`ControlPlaneMcpMount`, `mount_control_plane_mcp`, `create_control_plane_mcp`, `ControlPlaneMcpAuthApp`, `ControlPlaneMcpExactPathApp`), `api/src/transport_matters/main.py` (`create_app`, `lifespan`), `api/src/transport_matters/api/v1/controlplane_mcp_test_support.py` (`control_plane_http_client`, `control_plane_mcp_http_client`, `control_plane_mcp_session`), `api/src/transport_matters/api/v1/test_controlplane_mcp_transport.py`, `api/src/transport_matters/api/v1/test_controlplane_skins.py` (`_skin_app`), `api/src/transport_matters/cli/test_control_plane_home.py`, and `api/src/transport_matters/cli/test_grok_home.py`.

### Direction

Start after #599. This issue owns the durable mount, lifecycle, allowed host test seam, 4 MiB proof, and legacy plus modern client proof. Keep #599 dependency, server, protocol field, catalog registry, and extracted test support changes intact. Add one owner for constructing the mounted control plane MCP ASGI app, public `/mcp` exact path, inner SDK path `/`, wrappers, routes, and session manager lifetime. Pass the three required transport settings to `streamable_http_app` and omit a body size override so the SDK 4 MiB default remains authoritative. Supply the Transport Matters server version explicitly. Keep `control_plane_http_client` as the REST helper. Add `control_plane_mcp_http_client` as the one raw in process MCP HTTP seam with allowed Host and Origin. Evolve `control_plane_mcp_session` to the high level client with explicit protocol mode and disabled response caching. Prove legacy initialize plus list and call, modern discover plus list and call, exact 4194304 byte success, 4194305 byte 413, per request revocation, seeded Claude Codex and Grok homes, and one real captured run against preview.

### Guardrails

Do not change dependencies, lockfile, MCP imports, protocol field names, `McpToolRegistry`, or the two stream adaptation owned by #599. Do not construct another raw MCP client outside `control_plane_mcp_http_client`. Do not add dynamic tool list updates, directory authorization, a separate legacy server, an SSE route, or a Transport Matters body limit constant. Do not disable DNS rebinding protection or change seeded configuration formats. `just check` and `just test` must pass.


## Sub issues
[]
