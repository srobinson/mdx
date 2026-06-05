---
title: MCP 2.1.1 Issue Signoff for Transport Matters
type: research
tags: [transport-matters, mcp, issue-review, architecture, control-plane]
summary: Seven Transport Matters issues and one producer issue were reviewed, with a blocking MCPServer.call_tool signature migration defect found in issue 599.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# Executive Summary

The eight issue bodies define a coherent dependency chain from generated runtime policy through effective authority, MCP catalog filtering, Canvas consent, and MCP 2.1.1 transport adoption. Final signoff failed because issue 599 does not migrate the discovery subclass override to the new `MCPServer.call_tool` signature. An executable MCP 2.1.1 probe confirmed that the prescribed mechanical base class rename makes every tool call return an error.

# Project Metadata

| Item | Value |
| --- | --- |
| Project | Transport Matters control plane |
| Languages | Python 3.14, TypeScript |
| API framework | FastAPI |
| MCP baseline | 1.28.1 in the current lock |
| MCP migration target | 2.1.1 with `mcp-types` 2.1.1 |
| Frontend and runtime | React, Electron, Node 20.19 or newer |
| Package management | uv, pnpm 11.18.0 |
| Verification | `just check`, `just test`, focused Python and Vitest suites |
| Structural index | fmm index available for 1,805 files and 328,743 lines |

The `.agent-runtimes` repository was not available in the local fmm index. Its current `main` tree and issue body were inspected through the GitHub API.

# Architecture

## Policy producer and consumer

`.agent-runtimes` issue 2 owns schema version 4, the requested grant, the closed capability vocabulary, valid combinations, and canonical ordering. Its current compiler path is `load_manifest` to `compiler.plan` to `derive_capabilities` to `_materialize_capabilities`. Generated `capabilities.json` files remain disposable verification output.

Transport Matters issue 594 consumes this contract at `read_runtime_template_capabilities`, then projects it through `RuntimeTemplateListing.summary` for REST and MCP catalog responses. The selected policy continues through `resolve_agent`, `RuntimeTemplateRef`, `plan_runtime_home`, and launch provenance. Current schema version 3 ownership is visible in `api/src/transport_matters/runtime_templates.py:99-141`.

## Effective authority

Issue 595 introduces one pure ordered intersection for `none < observer < director`. The trusted runtime request is bounded by Canvas consent or the launching principal, plus an optional MCP override. The resolution boundary belongs after `agent_runtime_ref` and before provisioning in `capture_rpc_routes._resolved_domain_request` at `api/src/transport_matters/api/v1/capture_rpc_routes.py:348-465`.

The existing carrier crosses the browser, Gateway, runtime manager, capture adapter, Python request model, and control plane audit. Important current seams include `RunManager.createNew` at `packages/runtime/src/service/RunManager.ts:190-281`, `RunManager.register` at `packages/runtime/src/service/RunManager.ts:462-557`, and `PrepareCaptureRequest` at `api/src/transport_matters/api/v1/capture_rpc_routes.py:121-221`.

## Catalog and discovery

Issue 596 replaces decorator order with one 34 tool catalog and one registry. The current server registers 13 core tools in `create_control_plane_mcp` at `api/src/transport_matters/api/v1/controlplane_mcp.py:393-529`, then 13 Space related tools and 8 browser tools through the two existing registrars.

Issue 597 filters both `tools/list` and initial `tools/call` dispatch by the intersection of effective role and frozen runtime capability. Domain authorization remains active after this initial eligibility gate. Bearer identity is resolved per request by `ControlPlaneMcpAuthApp` and carried through `ControlPlaneTokenVerifier.verify_token` at `api/src/transport_matters/api/v1/controlplane_mcp.py:146-187`.

## SDK and mount migration

Issue 599 migrates the server and protocol model names to MCP 2.1.1. Issue 600 then centralizes route installation, wrapper composition, server application construction, and lifecycle in `ControlPlaneMcpMount`. The current inline mount is at `api/src/transport_matters/main.py:600-617`, while the current session manager lifecycle is entered at `api/src/transport_matters/main.py:449-450`.

# Key Patterns

1. **One owner per contract.** The producer owns capability values, Transport Matters owns effective authority, and the MCP tool catalog owns registration metadata.
2. **Intersection for authority.** Requested policy can only be reduced by consent, principal authority, and an optional override.
3. **Frozen launch facts.** Effective authority and capabilities are captured once, persisted, and used for identity, discovery, and audit.
4. **Eligibility before dispatch.** Hidden and unknown tools share one error shape, while domain checks still protect visible calls.
5. **Durable transport boundary.** Route ownership, wrappers, SDK settings, and lifecycle converge in one mount object.
6. **Extract before growth.** Issue 594 splits the current 871 line runtime registry test, issue 595 extracts contracts from the 701 line capture route, and issue 599 extracts reusable clients from the 709 line MCP skin test.

# Detailed Findings

## Blocking defect in issue 599

Issue 597 is specified against MCP 1.28.1. Its discovery subclass overrides `FastMCP.call_tool(name, arguments)` and delegates to `super().call_tool`. Issue 599 instructs the worker to rename that base to `MCPServer`, but does not require a signature or delegation change.

MCP 2.1.1 changes the method to `MCPServer.call_tool(name, arguments, context=None)`. Its private handler calls `self.call_tool(params.name, params.arguments or {}, context)` in `mcp/server/mcpserver/server.py:422-441`. A subclass that retains the issue 597 signature receives three positional arguments after `self` and raises `TypeError` before eligibility or tool implementation dispatch.

The repair required in issue 599 is precise:

* Change the issue 597 subclass override to accept the MCP 2.1.1 `Context` parameter.
* Forward the same context to `super().call_tool` after the catalog eligibility check.
* Add or retain a real authenticated `tools/call` regression that proves the context reaches the registered implementation.

Forwarding matters beyond signature compatibility. Calling `super().call_tool` without the request context constructs a context without the active request, which can break authentication dependent behavior.

## Executable proof

The following isolated probe used `mcp==2.1.1` and reproduced the failure with the mechanical rename described by issue 599:

```python
class MigratedFilter(MCPServer[None]):
    async def call_tool(self, name: str, arguments: dict[str, object]):
        return await super().call_tool(name, arguments)
```

An in process `Client` call returned `is_error=True` with:

```text
TypeError: MigratedFilter.call_tool() takes 3 positional arguments but 4 were given
```

This failure prevents issue 599 from passing its preserved discovery, skin, and tool schema suites.

## Other reviewed contracts

No additional definite blocker was needed for the signoff response. The following requested checks were confirmed:

* `.agent-runtimes` issue 2 keeps generated `capabilities.json` files out of authored changes and uses generation plus audit as proof.
* Issue 594 includes schema version 4 route fixtures, shared runtime artifact builders, REST and MCP parity, launch provenance, and Canvas fixture type updates.
* Issue 595 carries limit and optional override separately across the browser, Gateway, runtime, capture RPC, Python resolution, response, replay fingerprint, and audit paths.
* Issue 596 makes the registry the only registration path and validates the complete catalog before the first SDK registration.
* Issue 597 applies the same role and capability predicate to both list and call paths.
* Issue 599 hands the registry from `FastMCP` to `MCPServer` without restoring server ownership to the Space or browser registrars.
* Issue 600 consumes the extracted client seam and moves mount ownership after issue 599.
* MCP 2.1.1 exposes snake case Python fields with camel case aliases for `ToolAnnotations` and `CallToolResult`.
* MCP 2.1.1 defaults the request body limit to 4,194,304 bytes.
* A live isolated probe returned 200 for an exactly 4,194,304 byte padded JSON RPC `ping` and 413 for 4,194,305 bytes.
* The SDK default DNS rebinding policy accepts `Host: localhost:*` and `Origin: http://localhost:*`. Transport Matters also trusts `localhost` at `api/src/transport_matters/config.py:134-147`.
* All eight issues have the Transport Matters program issue as parent. GitHub blocker relationships match the stated chain except issue 596, whose body itself directs workers to rebase after issue 594 if its closed capability type is absent.
* No source line anchors remain in the issue bodies.

# Dependencies

| Dependency | Responsibility in this work |
| --- | --- |
| Pydantic | Generated artifact validation and camel case wire aliases |
| FastAPI and Starlette | REST routes, exact MCP route, mount order, auth wrappers, trusted hosts |
| MCP 1.28.1 | Current `FastMCP` implementation and issue 597 subclass seam |
| MCP 2.1.1 | `MCPServer`, modern and legacy clients, request limit, transport security |
| `mcp-types` 2.1.1 | Protocol models and version constants |
| httpx | Existing REST and non MCP clients |
| httpx2 | MCP 2.1.1 transport and in process MCP test client |

# Relevance to Helioy

This issue chain establishes a reusable Helioy authorization pattern: generated runtimes publish requested capability policy, the launching product intersects it with user and principal limits, and protocol discovery applies the frozen result without replacing domain authorization. The discovered MCP migration defect also demonstrates why base class migrations require method signature comparison and an executable dispatch probe, even when the upstream type name appears mechanically compatible.

# Open Questions

1. Should issue 599 name the new context type explicitly, or reference the landed MCP 2.1.1 signature and require exact forwarding?
2. Should issue 596 gain an explicit GitHub dependency on issue 594 to encode the rebase instruction already present in its body?
3. After issue 599 is corrected, rerun the blocker only review because a body edit invalidates the current signoff.
