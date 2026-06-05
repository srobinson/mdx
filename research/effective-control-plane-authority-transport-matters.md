---
title: Effective control plane authority in Transport Matters
type: research
tags: [transport-matters, control-plane, mcp, canvas, launch-policy]
summary: Source map and implementation plan for resolving and persisting per-runtime control plane authority.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-02
updated: 2026-09-02
---

# Executive summary

Transport Matters currently carries one launch grant from Canvas or MCP through the TypeScript runtime into Python capture. Issue 595 now has an implementation guide that replaces this ambiguous value with a consent or principal limit plus an optional MCP override, then resolves authority once after Python selects the trusted runtime.

The proposed decision records requested, limiting, override, and effective grants in existing launch provenance. Existing bearer provisioning, home seeding, and self identity continue to consume only the effective grant.

# Project metadata

| Area | Current stack |
| --- | --- |
| Python API | Python 3.14 or later, FastAPI, Pydantic, psycopg, MCP Python SDK 1.28.x |
| Runtime gateway | TypeScript, Fastify, Node PTY, Vitest |
| Canvas | React, Zustand, TanStack Query, Vitest |
| Package management | pnpm 11.18.0 and uv |
| Data | PostgreSQL, one database per release channel |
| Gates | `just check`, `just test` |

# Architecture

## Current direct launch path

Canvas persists `controlPlaneGrant` in `useCapturedRunStore` and sends it for every run creation (`www/packages/canvas/src/model/capturedRunStore.ts:172-364`). `createCapturedRunView` writes the value into the `/v1/runs` body (`www/packages/core/src/transport.ts:376-416`). The Fastify runtime validates and forwards the value to `RunManager.createNew` (`packages/runtime/src/server/runtimeRouter.ts:64-158`, `packages/runtime/src/service/RunManager.ts:190-281`). `CaptureRpcClient` then serializes it as `controlPlaneGrant` (`packages/runtime/src/adapters/CaptureRpcClient.ts:163-201`).

Python parses the value into `CapturedRunRequest.control_plane_grant` (`api/src/transport_matters/api/v1/capture_rpc_routes.py:121-221`). The request defaults to `none`, so the current contract cannot preserve every policy input independently.

## Current MCP launch path

The MCP `launch` tool defaults `grant` to `ControlPlaneGrantOption.NONE` (`api/src/transport_matters/api/v1/controlplane_mcp.py:479-502`). `ControlPlaneLauncher` carries that value into `GatewayCreateRunRequest` (`api/src/transport_matters/controlplane/launch_service.py:218-321`). `controlplane_gateway_runs.create_run` serializes the same `controlPlaneGrant` field used by Canvas (`api/src/transport_matters/api/v1/controlplane_gateway_runs.py:66-103`). Omission and explicit `none` therefore collapse before policy resolution.

## Shared policy boundary

`_resolved_domain_request` resolves the selected runtime through `agent_runtime_ref` and then derives the MCP URL from the current grant (`api/src/transport_matters/api/v1/capture_rpc_routes.py:348-465`). This function is the narrow shared boundary for direct and MCP launches. It has the trusted `RuntimeTemplateRef`, launch origin, limit, and optional override before capture side effects begin.

The implementation guide adds one pure resolver at this boundary. The resolver writes a four-value decision to `CapturedRunRequest.launch_fields` and replaces `CapturedRunRequest.control_plane_grant` with the effective value. The existing downstream path then remains valid:

1. `_prepare_home_and_grant` passes the effective grant to `prepare_control_plane_grant` (`api/src/transport_matters/captured/context.py:272-315`).
2. `prepare_control_plane_grant` returns early for `none`; otherwise it mints a bearer and seeds the runtime home (`api/src/transport_matters/controlplane/provisioning.py:30-67`).
3. `_run_identity_seed` writes the effective value to `RunIdentitySeed.control_access` (`api/src/transport_matters/captured/context.py:179-198`).
4. `ControlPlaneService.whoami` projects the frozen run identity (`api/src/transport_matters/controlplane/service.py:225-235`).

# Key patterns

## Resolve policy after trusted runtime selection

The browser and gateway transport policy inputs. Python resolves authority only after `agent_runtime_ref` produces a trusted `RuntimeTemplateRef`. This preserves the control plane rule that clients express intent but do not select runtime authority.

## Persist provenance in the existing launch field

`launch_fields` already carries runtime template provenance, Canvas affinity, continuation lineage, provider access receipts, and launch advisories. Adding one `control_plane_authority` object keeps launch explanation on the session record and avoids a parallel table.

## Return the frozen decision for audit

The capture response already returns resolved identity through `CapturedRunSpawnSpec`. Adding the authority decision to that private response lets `RuntimeRunView`, `GatewayRunView`, and `launch_action` record the same decision. The public `LaunchResult` can remain unchanged.

## Respect the repository size limits

`capture_rpc_routes.py` is 701 lines. Its Pydantic request and response models must move to a focused contract module before issue 595 adds fields. `test_controlplane_skins.py` is 709 lines and `test_launch_replay.py` is 714 lines, so new authority coverage belongs in focused test files.

# Detailed findings

## Decision semantics

The ordered grants are `none < observer < director`.

- A direct CMDK launch uses the persisted Canvas value as the limit and has no override.
- An MCP launch uses `ControlPlanePrincipal.role` as the limit and preserves `grant=None` versus explicit `ControlPlaneGrantOption.NONE`.
- A selected runtime supplies the requested grant through the schema version 4 `RuntimeTemplateRef` added by issue 594.
- A raw launch without a selected runtime resolves to `none`.
- A selected runtime uses the explicit override when present. Otherwise it uses the runtime request. The resolver clamps that candidate to the limit.

## Replay identity

Both replay fingerprints currently include the single grant value. Python uses `_intent_fingerprint` (`api/src/transport_matters/controlplane/launch_service.py:497-514`). TypeScript uses `createRunFingerprint` (`packages/runtime/src/service/runManagerSupport.ts:46-70`). Both fingerprints must include the limit and the optional override, including the difference between absent and explicit `none`.

## Audit ownership

`launch_action` currently records the requested model, effort, name, and agent (`api/src/transport_matters/controlplane/action_builders.py:51-81`). The successful action can add the same frozen authority object stored in launch provenance. Failed launch audit can record the known limit and override, but it must not invent requested or effective values when capture did not resolve them.

## Boundary behavior

Effective `none` must leave `control_plane_url` unset. The result creates no bearer row and seeds no Transport Matters MCP client. Invalid limits and overrides must fail in a REST, MCP, runtime router, or capture RPC model before any launch side effect.

# Dependencies

- Issue 594 must add the runtime requested grant to `RuntimeTemplateRef` before issue 595 starts.
- `ControlPlaneGrantOption` and `ControlPlaneGrantRole` provide the Python grant vocabulary.
- `ControlPlaneGrantOption`, `CONTROL_PLANE_GRANT_OPTIONS`, and `isControlPlaneGrantOption` provide the TypeScript vocabulary and validators.
- `prepare_control_plane_grant` and `ControlPlaneGrantStore` already implement effective grant provisioning and persistence.
- `launch_fields` is the durable provenance carrier.

# Relevance to Helioy

This design keeps policy in one typed Python function while JavaScript transports intent. The pattern applies to other Helioy launch systems that combine a runtime request, a user consent ceiling, and a parent principal ceiling. Persisting the complete decision also gives later tool catalog filtering a stable launch-time authority record.

# Verification

The issue body was written with `gh issue edit` and reread with `gh issue view`. A GraphQL before and after comparison confirmed that the title, state, labels, parent issue 593, blocker issue 594, assignees, milestone, issue type, and URL did not change. The final guide has no source line anchors.

The focused Vitest command for the existing core and Canvas tests ran 72 tests across two files successfully:

```bash
pnpm --filter @tm/shell exec vitest run \
  ../core/src/transport.test.ts \
  ../canvas/src/model/capturedRunStore.test.ts
```

No source files or Git state were changed.

# Open questions

- Issue 594 will determine the final name of the requested grant field on `RuntimeTemplateRef`. Issue 595 must reuse that field.
- The implementation must decide whether the private `RuntimeRunView.controlPlaneAuthority` field is required for every captured run or nullable for non-capture adapters. The runtime currently treats capture identity as authoritative, so a required field is the cleaner result after the adapter contract changes.
