---
title: MCP 2.1.1 issue handoff corrections for Transport Matters
type: research
tags: [transport-matters, mcp, github-issues, test-support, architecture]
summary: Issues 599 and 600 now consume the canonical MCP registry, respect the test file size limit, and use verified MCP 2.1.1 server and client APIs.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

## Executive Summary

Transport Matters exposes its control plane through one authenticated MCP endpoint mounted in FastAPI. Issues #599 and #600 were corrected so the MCP 2.1.1 port consumes #596's canonical registry, extracts shared client support before touching the 709 line skin test file, and places durable transport ownership plus legacy and modern protocol proof in the following issue.

## Project Metadata

- Primary language: Python 3.14 or newer
- Web stack: FastAPI and Starlette
- MCP baseline: `mcp>=1.28,<2`, currently resolved to MCP 1.28.1
- MCP target: MCP 2.1.1 with `mcp-types==2.1.1`
- HTTP clients: `httpx` for existing application tests and `httpx2` for MCP 2.1.1 transport
- Build and dependency system: uv and Just
- Repository topology: 1,805 indexed files and 328,632 LOC, including 955 API files and 206,408 API LOC
- Helioy signal: the repository is indexed by fmm

## Architecture

### Current mounted MCP path

`create_app` constructs the MCP server, stores it on application state, wraps it with `ControlPlaneMcpAuthApp`, installs an exact `/mcp` route through `ControlPlaneMcpExactPathApp`, then installs the ordinary `/mcp` mount before the frontend bundles (`api/src/transport_matters/main.py:600-619`). The FastAPI lifespan enters the SDK session manager once (`api/src/transport_matters/main.py:449-450`).

`create_control_plane_mcp` currently creates `FastMCP`, passes the three transport arguments into the constructor, decorates thirteen core tools, then gives the same server to the Space and browser registrars (`api/src/transport_matters/api/v1/controlplane_mcp.py:393-410`, `api/src/transport_matters/api/v1/controlplane_mcp.py:527-529`). Issue #596 changes this registration flow so `McpToolRegistry` collects all implementations and performs final ordered registration.

### Current test seam

`test_controlplane_skins.py` is 709 lines. It owns `_skin_app`, `_http_client`, and `_mcp_session` (`api/src/transport_matters/api/v1/test_controlplane_skins.py:200-250`). Five other test modules import `_mcp_session`, and four import `_skin_app`. The MCP session currently uses `httpx.AsyncClient`, unpacks three values from `streamable_http_client`, and constructs `ClientSession` directly (`api/src/transport_matters/api/v1/test_controlplane_skins.py:230-250`).

## Key Patterns

### Catalog owns order, registrars collect

Issue #599 now treats `api/src/transport_matters/api/v1/mcp_tool_catalog.py` as the MCP 2.1.1 server type migration seam. `McpToolRegistry` changes its final server edge from `FastMCP[None]` to `MCPServer[None]`. `register_space_mcp_tools` and `register_browsing_mcp_tools` remain registry collectors after #596 and must not regain server parameters.

### Extract before extending

The corrected #599 guide requires a behavior preserving extraction before any migration edits to the oversized skin test file. The new `controlplane_mcp_test_support.py` owns `control_plane_http_client` and `control_plane_mcp_session`; every caller migrates directly, with no forwarding aliases. The extraction reduces `test_controlplane_skins.py` below the 700 line limit and gives #600 a stable seam.

### Mount policy has one durable owner

The corrected #600 guide retains `ControlPlaneMcpMount` and `mount_control_plane_mcp`. This boundary owns the public path, wrappers, route installation, SDK ASGI construction, and SDK session manager lifetime. `main.py` consumes the bundle rather than reaching through MCP internals.

## Detailed Findings

### Verified MCP 2.1.1 API contract

A Python 3.14 environment with MCP 2.1.1 confirmed:

- `MCPServer` imports from `mcp.server.mcpserver` and remains generic.
- `MCPServer.add_tool`, `MCPServer.tool`, and no argument `MCPServer.list_tools` remain available.
- `MCPServer.streamable_http_app` accepts `streamable_http_path`, `json_response`, `stateless_http`, and `max_request_body_size`.
- The default body limit is 4,194,304 bytes. Oversized requests return HTTP 413 with `Request body too large`.
- `streamable_http_client` accepts `httpx2.AsyncClient` and yields two streams.
- `mcp.types` remains public. Python protocol fields use snake case while `model_dump(mode="json", by_alias=True)` retains camel case wire names.
- `mcp.client.Client` accepts a stream transport, `mode="legacy"` or `mode="auto"`, and `cache=None`.
- An executable in-process ASGI probe negotiated `2025-11-25` in legacy mode and `2026-07-28` in auto mode. Both modes completed `tools/list` and `tools/call` through the same MCP server.

### Issue #599 correction

The original guide assumed the pre-#596 decorator design and told both domain registrars to migrate server types. The final body now:

- includes `mcp_tool_catalog.py` and `McpToolRegistry` in the server migration;
- migrates catalog `ToolAnnotations` Python fields to snake case;
- leaves Space and browser registrars on the shared registry;
- extracts shared client support before any edits to the 709 line test file;
- migrates all known callers to the new public helper names;
- performs the `httpx2` and two stream adaptation in the support module;
- preserves the literal three argument compatibility move into `streamable_http_app()`.

### Issue #600 correction

The final body consumes the extracted support module and removes stale claims that `test_controlplane_skins.py` owns the shared clients. It evolves `control_plane_mcp_session` to the verified high level `mcp.client.Client`, disables response caching, and asserts the exact 2025 and 2026 protocol results. The durable mount design and real mounted endpoint proof remain intact.

The request limit test now exercises the SDK default through `/mcp`: a valid JSON body padded to exactly 4,194,304 bytes must pass the size guard, while 4,194,305 bytes must return the SDK's 413 response. Transport Matters does not copy the limit into a local constant.

### Delivery verification

Both live GitHub bodies matched the staged text byte for byte after `gh issue edit`. Titles, open state, `enhancement` and `P2` labels, native parent #593, body blockers, scope, and acceptance criteria were unchanged. Neither body contains source line anchors or em dashes. The repository worktree remained clean.

## Dependencies

- MCP 2.1.1 provides `MCPServer`, modern discovery, the high level `Client`, Streamable HTTP, and the 4 MiB default boundary.
- `mcp-types==2.1.1` provides the protocol models and JSON aliases through the `mcp.types` namespace.
- `httpx2` and `httpcore2` provide the MCP 2 transport stack.
- `httpx` remains necessary for Transport Matters REST and raw ASGI test traffic.
- `opentelemetry-api` and `truststore` are transitive MCP 2.1.1 dependencies.

## Relevance to Helioy

The corrected handoff preserves the Helioy control plane's central policy model. One catalog owns tool metadata and order, one registry validates implementation completeness, one mount bundle owns transport policy, and domain authorization stays in existing call paths. The extracted client seam also prevents future protocol tests from coupling to a large behavioral test module.

## Open Questions

- The exact method name used by the future `McpToolRegistry` final registration path depends on #596's implementation. The issue intentionally binds to the type and responsibility rather than inventing a method name.
- The real preview run required by #600 remains implementation evidence for that issue.
- The #597 discovery tests should avoid starting the MCP 2.1.1 session manager more than once for one server instance.
