---
title: Transport Matters MCP 2.1.1 Migration Guide Research
type: research
tags: [transport-matters, mcp, python, fastapi, migration, github-issue]
summary: Source grounded implementation map for the mechanical MCP 1.28.1 to 2.1.1 port in Transport Matters issue 599.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# Executive Summary

Transport Matters exposes one authenticated MCP control plane through FastAPI, with control plane, Space, and browser tools registered on one high level SDK server. Issue [#599](https://github.com/littleorgans/transport-matters/issues/599) now has a verified implementation guide covering 14 files and 48 repository symbols for the mechanical MCP 2.1.1 port.

The migration requires five coupled changes: the `MCPServer` rename, deletion of the MCP 1.x settings workaround, snake case Python model fields with camel case wire aliases, an `httpx2` test client, and a minimal three argument transport move. Durable transport policy and dual protocol proof remain in issue #600.

# Project Metadata

- **Language:** Python 3.14, with TypeScript product surfaces elsewhere in the monorepo.
- **API framework:** FastAPI and Starlette.
- **Package manager and lockfile:** uv with `api/pyproject.toml` and `api/uv.lock`.
- **Build system:** Hatchling with Hatch VCS.
- **Quality gates:** Ruff, mypy strict mode, pytest, and repository wide `just check` and `just test`.
- **Current MCP dependency:** `mcp>=1.28,<2`, resolved to 1.28.1. The direct `httpx>=0.28` dependency and development `httpx2>=2.12` floor coexist in the current project (`api/pyproject.toml:37-48`, `api/pyproject.toml:67-79`).
- **Helioy signal:** the repository has an active `.fmm.db` index. FMM reports 1,805 indexed files and 328,632 LOC across `api`, `www`, `packages`, and `desktop`.

# Architecture

## MCP server construction

`create_control_plane_mcp` creates the shared SDK server, configures auth, registers the core control plane tools, then delegates Space and browser tool registration (`api/src/transport_matters/api/v1/controlplane_mcp.py:393-529`). The current MCP 1.28.1 constructor owns `streamable_http_path="/"`, `json_response=True`, and `stateless_http=True` (`api/src/transport_matters/api/v1/controlplane_mcp.py:393-410`).

`create_app` stores that server on FastAPI state, creates the streamable HTTP ASGI app, wraps it with request identity and exact path adapters, then registers both the exact `/mcp` route and mounted `/mcp` application (`api/src/transport_matters/main.py:600-617`). The outer lifespan enters the SDK session manager once.

## Shared result boundary

`mcp_tool_result` is the single result construction seam. It serializes domain Pydantic models with `mode="json"`, `by_alias=True`, and optional null exclusion, then builds a `CallToolResult` containing identical text and structured payloads (`api/src/transport_matters/api/v1/mcp_tooling.py:18-40`). This is the correct DRY boundary for the `structuredContent` and `isError` field migration.

## Test client boundary

`_mcp_session` is the shared real client fixture for MCP skin tests. It starts the session manager, supplies an in process ASGI client to `streamable_http_client`, initializes `ClientSession`, and yields the session (`api/src/transport_matters/api/v1/test_controlplane_skins.py:230-250`). Other skin suites import this fixture rather than duplicate transport setup.

# Key Patterns

- **One server, several tool domains:** core, Space, and browser tools share one authenticated server and one session manager.
- **Exact path plus mounted route:** the explicit route protects `/mcp` semantics while the mount handles the SDK subapplication.
- **REST and MCP parity:** tests compare REST responses with MCP structured results to prove one domain projection across both skins.
- **Wire aliases are deliberate:** domain payloads already use `by_alias=True`. The MCP tool schema contract test must adopt the same rule because MCP 2 protocol models use snake case Python fields and camel case JSON aliases.
- **Client package identity matters:** `httpx` and `httpx2` APIs are similar, but transports and clients cannot be mixed. REST tests remain on `httpx`; the SDK client path moves to `httpx2` end to end.

# Detailed Findings

## Dependency graph

Changing only the direct range to `mcp>=2.1,<3` and running an MCP scoped lock refresh produces this graph:

- `mcp` 1.28.1 becomes 2.1.1.
- `mcp-types==2.1.1` is added through the SDK's exact dependency.
- `opentelemetry-api>=1.28.0` is added, currently resolving to 1.44.0.
- Existing `httpx2` 2.12.0, `httpcore2` 2.12.0, and `truststore` 0.10.4 become runtime reachable through MCP.
- `httpx-sse` 0.4.3 disappears.
- Direct `httpx` 0.28.1 remains because Transport Matters uses it independently.

No separate `mcp-types` declaration is appropriate. The supported `mcp.types` alias preserves the SDK owned exact version pairing.

## Applicable SDK compatibility changes

1. Replace `mcp.server.fastmcp.FastMCP` with `mcp.server.mcpserver.MCPServer` in `controlplane_mcp.py`, `space_mcp.py`, and `browsing_mcp.py`.
2. Delete the `FastMCPSettings` import and `FastMCPSettings.model_rebuild()` workaround. The workaround is isolated in `controlplane_mcp.py` (`api/src/transport_matters/api/v1/controlplane_mcp.py:88-91`).
3. Move the three current transport arguments to `streamable_http_app()`. MCP 2 rejects them on the server constructor. This literal move is required for issue #599 to land independently.
4. Change `CallToolResult` construction to `structured_content=` and `is_error=`.
5. Change Python result reads from `.structuredContent` and `.isError` to `.structured_content` and `.is_error`.
6. Keep wire keys `inputSchema`, `outputSchema`, `structuredContent`, and `isError`. Add `by_alias=True` when dumping MCP protocol models. The tool contract currently dumps without it (`api/src/transport_matters/api/v1/test_controlplane_action_skins.py:88-93`).
7. Use `httpx2.AsyncClient` with `httpx2.ASGITransport` for `_mcp_session`. Keep the REST fixture on `httpx` (`api/src/transport_matters/api/v1/test_controlplane_skins.py:209-250`).
8. Unpack `streamable_http_client()` as `(read_stream, write_stream)`. MCP 2 removes the third session ID callback.
9. Keep `instructions` as a keyword. MCP 2 adds positional constructor parameters before it.
10. Preserve the `list_tools` override delivered by blocker #597. The v1 and v2 high level methods both use the no argument `list_tools(self)` signature.

The current tree does not use removed MCP aliases, `McpError`, MCP resource URI models, roots, sampling, logging, SSE, or the low level server.

## Affected tests

An AST audit found camel case MCP result access in 34 tests across seven files:

- `test_agent_catalog_skins.py`
- `test_browsing_skins.py`
- `test_controlplane_action_skins.py`
- `test_controlplane_mcp_inventory.py`
- `test_controlplane_skins.py`
- `test_space_mcp.py`
- `tests/integration/test_launch_affinity_authority.py`

The schema contract also needs `by_alias=True`. Existing `test_mcp_mount_precedes_and_is_not_shadowed_by_spa` and `test_lifespan_runs_the_mcp_session_manager` prove that the minimal transport move preserves the mount and lifecycle.

## Verification performed

The final GitHub issue body was read back with `gh issue view`. Its title, labels, state, assignees, milestone, project items, parent #593, and URL match the pre-edit metadata. The published guide contains one `## Implementation guide` section and no source line anchors.

A temporary copy of the API received the exact mechanical edits without touching the target worktree. Results:

- Ruff check passed.
- mypy passed across 884 source files.
- 56 focused MCP skin tests passed.
- Two authority integration tests reached their existing repository root discovery guard and failed because the temporary copy intentionally lacked the monorepo root. They did not fail on MCP behavior.

# Dependencies

- **mcp 2.1.1:** high level server, auth, protocol client, and streamable HTTP transport.
- **mcp-types 2.1.1:** generated protocol Pydantic models, exact pinned by MCP.
- **httpx2 2.12.0:** MCP 2 transport client with integrated SSE support.
- **httpcore2 2.12.0 and truststore 0.10.4:** `httpx2` runtime transport and system certificate trust.
- **opentelemetry-api:** trace metadata propagation required by MCP 2.
- **httpx 0.28.1:** Transport Matters REST and non SDK HTTP client surface, retained directly.
- **FastAPI and Starlette:** host application, route mounting, middleware, and lifespan.

# Relevance to Helioy

This migration preserves the Transport Matters control plane contract while aligning its MCP surface with other Helioy services moving to MCP 2. The key reusable lesson is to migrate the dependency, server import, protocol model fields, generated wire aliases, and client package identity as one verified unit. Splitting these changes produces imports that compile while silently serializing the wrong keys or supplying incompatible client objects.

# Open Questions

- Issue #597 must land first. Its discovery subclass and tests need the same import and field audit after the blocker is present.
- Issue #600 owns the durable transport policy owner, mount cleanup, explicit server version, 4 MiB request boundary, and dual protocol client proof. The minimal argument move in #599 should remain literal so #600 can establish the final ownership cleanly.
