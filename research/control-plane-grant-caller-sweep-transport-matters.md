---
title: Control Plane Grant Caller Sweep for Transport Matters
type: research
tags: [transport-matters, control-plane, authority, issue-595, migration]
summary: A live caller sweep found one omitted GatewayCreateRunRequest test helper and corrected issue 595 without changing source or git state.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

## Executive Summary

Transport Matters issue 595 specifies the migration from one ambiguous control plane grant carrier to a limit, an optional override, and one resolved authority decision. A live source sweep found that the issue omitted `_request` in the harness enablement tests, which still constructs `GatewayCreateRunRequest` with the field scheduled for deletion. The issue now covers that caller in the implementation guide, test plan, and focused verification command.

## Project Metadata

- Languages: Python and TypeScript
- Repository shape: monorepo with `api`, `packages`, `www`, and `desktop` areas
- Python: 3.14 or newer
- Python build system: Hatchling with Hatch VCS
- Node.js: 20.19.0 or newer
- JavaScript package manager: pnpm 11.18.0
- Project state: pre release
- Structural index: fmm indexed, with 1,805 files and 328,732 lines at inspection time

## Architecture

The authority migration crosses the MCP launch service, Python gateway request, runtime router, capture RPC, captured run model, Canvas transport, provisioning, self identity, and audit path. Python owns authority resolution. TypeScript validates and transports the limiting grant and optional override.

`GatewayCreateRunRequest` is the private Python gateway boundary. Its live constructors are in the launch service and two API test modules. The capture boundary resolves the trusted runtime request against the supplied limit and optional override, then keeps `CapturedRunRequest.control_plane_grant` as the effective authority consumed by provisioning and identity code.

## Key Patterns

- Migrate all callers when deleting a model field. Test helpers are live constructors and must move with production callers.
- Keep persisted Canvas consent named `controlPlaneGrant` inside Canvas state while renaming transport carriers. State vocabulary and wire vocabulary have different ownership.
- Preserve omitted override and explicit `none` as distinct values through fingerprints, provenance, replay, and audit.
- Use one pure authority resolver. Transport layers must not duplicate ordering or intersection policy.

## Detailed Findings

### Omitted gateway caller

`api/src/transport_matters/api/v1/test_run_proxy_harness_enablement.py:31-45` defines `_request`. It constructs `GatewayCreateRunRequest` with `grant=ControlPlaneGrantOption.NONE`.

The issue already covered the production constructor in `api/src/transport_matters/controlplane/launch_service.py` and the typed gateway contract constructor in `api/src/transport_matters/api/v1/test_run_proxy_controlplane.py`. The harness enablement helper was the only additional live constructor omitted from the issue body.

Issue 595 now directs `_request` to use:

- `control_plane_grant_limit=ControlPlaneGrantOption.NONE`
- `control_plane_grant_override=None`

This preserves the tests' harness enablement purpose while adopting the replacement request contract.

### Caller and spelling sweep

The final search covered:

- Every `GatewayCreateRunRequest` construction under `api`
- Every `PrepareCaptureRequest` construction under `api`
- Every `CapturedRunRequest` construction under `api`
- Every `controlPlaneGrant` spelling across `api`, `packages`, `www`, and `desktop`

No additional omitted old gateway or capture carrier required an issue body addition. Remaining Canvas launcher and workbench occurrences represent the persisted user consent setting that issue 595 explicitly retains. Existing `CapturedRunRequest.control_plane_grant` occurrences represent the resolved effective value that the issue also retains.

### Issue correction

The GitHub issue body was edited in three places:

1. The exact changes section now names the harness enablement file and `_request`.
2. The tests section now names the same helper and replacement fields.
3. The focused Python pytest command now includes the harness enablement test module.

No repository source file or git state changed.

### Verification

A fresh GitHub read confirmed:

- Issue: transport-matters 595
- Title: `Resolve and persist effective control-plane authority`
- State: open
- Labels: `enhancement`, `P2`
- Assignees: none
- Milestone: none
- Full source path appears in both descriptive sections
- Focused command path appears in the pytest command
- `_request`, the limit value, and the absent override are named in both descriptive entries
- No em dash or source line anchor was introduced into the issue body

## Dependencies

- Pydantic models define the Python request boundaries.
- The shared runtime contract package defines TypeScript grant vocabulary and wire validation.
- pytest and Vitest cover Python and TypeScript migration behavior.
- GitHub CLI provided the read, edit, and verification path for issue metadata and body content.

## Relevance to Helioy

The correction prevents a full repository test run from reaching a stale constructor after `GatewayCreateRunRequest.grant` is deleted. It also keeps the issue executable as an implementation specification: production callers, focused tests, and repository gates now describe the same migration surface.

## Open Questions

- The implementation remains pending in issue 595.
- The eventual change should rerun the final carrier sweep after executable edits because new callers could appear before implementation lands.
