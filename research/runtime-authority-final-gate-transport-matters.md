---
title: Runtime Authority Final Gate for Transport Matters
type: research
tags: [transport-matters, agent-runtimes, mcp, authorization, canvas]
summary: The issue chain has coherent launch authority resolution, but MCP capability filtering lacks matching request time enforcement.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

# Executive Summary

The planned contract gives the runtime manifest authority over its requested grant and capability vocabulary, then lets Transport Matters calculate a frozen effective grant from trusted server facts. The launch path is coherent, but Transport Matters issue 597 filters capability membership only during `tools/list`; a direct call to a capability hidden tool can still succeed when the caller has the required grant and domain entitlement.

# Project Metadata

- Languages: Python 3.14 and TypeScript
- API framework: FastAPI with Pydantic
- MCP SDK: `mcp>=1.28,<2`
- Node requirement: Node 20.19 or newer
- Package manager: pnpm 11.18.0
- Build and test systems: uv, pytest, pnpm, Vitest, Playwright, Biome, Ruff, and mypy
- Transport Matters has an FMM index covering 1,805 files and 328,632 lines. `/Users/alphab/.agent-runtimes` has no FMM index, so that repository was inspected with read only source and AST oriented searches.

# Architecture

## Contract production and consumption

`.agent-runtimes` already compiles `runtime.toml` through `plan` and `derive_capabilities` into `capabilities.json` (`bin/agent_runtime_compiler/compiler.py:71-206`, `bin/agent_runtime_compiler/capabilities.py:216-246`). Issue 2 correctly owns the schema version 4 field names, the ordered capability vocabulary, validation, and all ten manifest classifications.

Transport Matters issue 594 places validation at `read_runtime_template_capabilities`, then carries the policy through `RuntimeTemplateListing.summary`, `RuntimeTemplateRef`, `RuntimeTemplateProvenance.as_launch_field`, and `OwnedSessionFacts.template_provenance` (`api/src/transport_matters/runtime_registry.py:67-90`, `api/src/transport_matters/runtime_registry.py:272-291`, `api/src/transport_matters/runtime_templates.py:99-236`, `api/src/transport_matters/storage/session_facts.py:38-56`). This keeps the producer contract distinct from vendor `required_capabilities`.

## Launch authority

Issue 595 has one sound resolution boundary. `_resolved_domain_request` runs after `agent_runtime_ref`, so the runtime request comes from the validated registry rather than a caller supplied field (`api/src/transport_matters/api/v1/capture_rpc_routes.py:348-465`, `api/src/transport_matters/api/v1/launch_resolution.py:166-177`). The proposed pure resolver computes the minimum of runtime request, Canvas or principal limit, and an optional reducing override. It preserves absent override versus explicit `none`, keeps raw launches at `none`, and passes only the effective value to provisioning and self identity.

The named browser, gateway, runtime, and capture carriers exist: `CreateCapturedRunOptions`, `registerRunRoutes`, `CreateManagedRunInput`, `PrepareCaptureInput`, `CaptureRpcClient.prepareCapture`, `PrepareCaptureRequest`, `CapturedRunRequest`, and `CapturedRunSpawnSpec`. The existing 701 line `capture_rpc_routes.py` must be split before extension, as issue 595 requires.

# Key Patterns

- Producer owned closed vocabulary, copied into typed consumer contracts.
- Trusted runtime policy is a ceiling rather than a grant source.
- One pure grant intersection function with frozen provenance.
- Effective authority drives bearer minting, home seeding, and self identity.
- Runtime capabilities freeze with live capture facts rather than being reread during requests.
- Tool registration remains canonical and deterministic while discovery varies by bearer policy.

# Detailed Findings

## Blocking defect: capability policy is absent from request time authorization

Issue 597 adds runtime capabilities to `ControlPlanePrincipal` and filters the result of `FastMCP.list_tools`, while explicitly retaining all tool implementations in the shared registry. Its planned call path does not check whether the invoked tool's catalog capability belongs to the principal's frozen capability tuple.

Current source proves the gap. `BrowsingMcpAdapter.browser_open` passes the principal to `open_browser_pane` (`api/src/transport_matters/api/v1/browsing_mcp.py:70-81`). `open_browser_pane` checks only `require_director` before the gateway side effect (`api/src/transport_matters/api/v1/controlplane_gateway_browsing.py:94-115`). A director principal whose runtime lacks the browser capability can therefore call `browser_open` directly even though `tools/list` hides it. The same class of gap applies to core and Space tools whose grant and domain checks pass.

This conflicts with transport-matters issue 593, whose acceptance criteria require direct calls to hidden tools to fail through authoritative call time checks. The issue 597 test plan covers an observer guessing a director tool, which proves grant enforcement but does not prove capability enforcement.

Required correction: route every MCP tool call through one catalog backed authorization check that validates both minimum grant and capability membership before invoking the existing implementation. Existing role, workspace, owner, Space, Canvas, worktree, DevTools, live capture, revocation, and audit checks should remain in place. Add same grant coverage, such as a director bearer without the browser capability calling `browser_open`, so discovery and invocation consume the same catalog entry.

## Secondary implementation guide omission

Issue 595 removes `GatewayCreateRunRequest.grant`, but `api/src/transport_matters/api/v1/test_run_proxy_harness_enablement.py:_request` still constructs that model with `grant` (`api/src/transport_matters/api/v1/test_run_proxy_harness_enablement.py:31-45`). The owning PR must migrate this fixture to the limit and optional override fields or the full test gate will fail.

# Dependencies

- `mcp.server.fastmcp.FastMCP` supplies registration, list, and call dispatch.
- `ControlPlaneGrantOption` and `ControlPlaneGrantRole` supply the ordered grant vocabulary (`api/src/transport_matters/controlplane/models.py:17-30`).
- `CaptureLeaseRegistry` binds stored grants to live run facts (`api/src/transport_matters/capture_rpc.py:115-206`, `api/src/transport_matters/capture_rpc.py:323-345`).
- `RuntimeTemplateRef` is the trusted selected runtime carrier (`api/src/transport_matters/runtime_templates.py:185-193`).

# Relevance to Helioy

This chain establishes a reusable policy pattern for Helioy runtimes: authored request, caller limit, optional reduction, frozen effective decision, and request time enforcement. Discovery filtering should remain a usability projection of the same policy, never the enforcement boundary.

# Open Questions

- What exact capability identifiers and generated JSON field names will `.agent-runtimes` issue 2 publish?
- Should capability authorization return the existing structured MCP denial envelope or a dedicated capability error code?
- Will the issue 597 correction live in a shared registry invocation wrapper or in the FastMCP subclass call handler?
