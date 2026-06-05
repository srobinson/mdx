---
title: Transport Matters issue 594 implementation guide
type: research
tags: [transport-matters, agent-runtimes, mcp, control-plane, schema-v4]
summary: Source grounded implementation path for consuming schema version 4 runtime authority and MCP capabilities.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-02
updated: 2026-09-02
---

# Executive summary

Transport Matters issue 594 now has an implementation guide grounded in the live consumer code and the current `.agent-runtimes` contract. The guide maps the schema version 4 policy from registry parsing through REST, MCP, launch resolution, and durable provenance while preserving current launch authority behavior.

The upstream blocker remains real. `.agent-runtimes` main still publishes schema version 3, and its issue 2 remains open. The guide tells the implementation worker to copy the final schema version 4 field names, identifiers, combination rules, and list order after the producer publishes them.

# Project metadata

- Repository: `littleorgans/transport-matters`
- Languages: Python 3.14, TypeScript
- Python validation: Pydantic
- API framework: FastAPI
- JavaScript workspace: pnpm 11
- Test frameworks: pytest, Vitest
- Build and verification entry point: `just`
- Helioy indexing: the repository has FMM indexes for the root, `api`, and `www` code

# Architecture

## Registry boundary

`api/src/transport_matters/runtime_templates.py` defines `RuntimeTemplateCapabilities` at lines 99 through 141. The model accepts producer additions through `RuntimeTemplateArtifactModel`, whose Pydantic configuration uses `extra="ignore"` at lines 61 through 81. `RuntimeTemplateCapabilities.schema_version` currently accepts only version 3.

`api/src/transport_matters/runtime_registry.py` loads `capabilities.json` in `read_runtime_template_capabilities` at lines 272 through 291. It converts JSON and Pydantic failures into `RuntimeTemplateRegistryError`. `resolve_agent` at lines 67 through 90 returns `RuntimeTemplateRef` for a selected catalog runtime.

## Catalog projection

`RuntimeTemplateListing.summary` in `api/src/transport_matters/runtime_templates.py` projects producer data into `RuntimeTemplateSummary` at lines 218 through 236. `api/src/transport_matters/agent_catalog.py` loads that projection once through `load_agent_catalog` at lines 15 through 18.

The REST handler `get_agents` lives in `api/src/transport_matters/api/v1/runtime_template_routes.py` at lines 21 through 34. The MCP adapter uses the same `AgentCatalogResult` through `_McpControlPlaneAdapter.agents` in `api/src/transport_matters/api/v1/controlplane_mcp.py`. This shared projection prevents REST and MCP drift.

## Launch provenance

`api/src/transport_matters/api/v1/launch_resolution.py` resolves a catalog id through `agent_runtime_ref` at lines 166 through 177. The enriched `RuntimeTemplateRef` then reaches `plan_runtime_home` in `api/src/transport_matters/cli/runtime_home.py` at lines 69 through 142.

`RuntimeTemplateProvenance.as_launch_field` in `api/src/transport_matters/runtime_templates.py` serializes template provenance at lines 202 through 208. `persist_owned_session_facts` in `api/src/transport_matters/cli/launch_profile.py` persists it at lines 403 through 424. `OwnedSessionFacts.template_provenance` in `api/src/transport_matters/storage/session_facts.py` currently accepts only `dict[str, str]`, so the type must widen to retain an MCP capability list as JSON.

# Key patterns

- Validate the producer contract once at `read_runtime_template_capabilities`.
- Keep generated artifact parsing forward compatible. Keep internal response models strict.
- Reuse `ControlPlaneGrantOption` from `api/src/transport_matters/controlplane/models.py`. It already owns `none`, `observer`, and `director` at lines 22 through 30.
- Keep `required_capabilities` separate. That field describes vendor requirements derived from skills, not Transport Matters MCP capabilities.
- Preserve producer list order. Do not sort, infer, or encode capability lists as strings.
- Transport requested policy without applying it. Issue 595 owns effective grant resolution.

# Detailed findings

## Required production changes

The guide names these production responsibilities:

1. Add the closed MCP capability identifier type beside `ControlPlaneGrantOption`.
2. Update `RuntimeTemplateCapabilities` to schema version 4 and validate the published combination rules.
3. Add the requested policy to `RuntimeTemplateSummary`, `RuntimeTemplateRef`, and `RuntimeTemplateProvenance`.
4. Copy the policy in `RuntimeTemplateListing.summary` and `resolve_agent`.
5. Keep `load_agent_catalog`, `get_agents`, and `_McpControlPlaneAdapter.agents` as shared projection consumers.
6. Preserve JSON types through `RuntimeHomePlan.template_provenance_field`, `persist_owned_session_facts`, and `OwnedSessionFacts`.
7. Add matching TypeScript contract types in `packages/contract/src/runtime/index.ts` and `www/packages/core/src/types/runtimeTemplates.ts`.

## File size constraint

`api/src/transport_matters/test_runtime_registry.py` has 871 lines. The repository requires files over 700 lines to be refactored before new code is added. The guide directs the worker to move shared capability artifact builders into `api/src/transport_matters/runtime_template_test_support.py` and contract tests into `api/src/transport_matters/test_runtime_template_contract.py` before adding schema version 4 cases.

## Behavior that must stay unchanged

The requested grant must not set `PrepareCaptureRequest.control_plane_grant`, create a bearer, seed the Transport Matters MCP client, filter tools, or change authorization. A raw launch without a selected runtime keeps its current behavior.

## Issue update verification

GitHub issue 594 was updated at `https://github.com/littleorgans/transport-matters/issues/594`.

The final verification confirmed:

- The body matches the prepared implementation guide exactly.
- The title is unchanged.
- The `enhancement` and `P2` labels are unchanged.
- Parent issue 593 is unchanged.
- Assignees, milestone, project items, subissues, state, and linked pull request metadata are unchanged.
- The body contains one `## Implementation guide` section.
- The guide contains no source line anchors.
- The guide names 20 files and 17 existing symbols.

# Dependencies

- `.agent-runtimes` issue 2 publishes schema version 4 and blocks implementation.
- Transport Matters issue 595 owns effective authority.
- Issue 596 owns the 34 tool catalog and minimum grant mapping.
- Issue 597 owns filtered MCP discovery.
- Issue 598 owns Canvas consent and launch UX.
- Issues 599 and 600 own the MCP SDK and transport migrations.

# Relevance to Helioy

The change establishes one typed policy contract between the runtime producer and Transport Matters. The design keeps user consent, requested runtime policy, effective authority, tool catalog membership, and call time authorization as separate concerns. That separation supports later policy work without changing launch behavior in issue 594.

# Open questions

- What exact field names and capability identifiers will `.agent-runtimes` publish in schema version 4?
- What grant and capability combinations will the producer contract declare invalid?
- Will the producer publish a machine readable vocabulary that Python and TypeScript can generate from, or must both consumers maintain checked copies?
