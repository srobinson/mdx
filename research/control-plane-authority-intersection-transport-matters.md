---
title: Control Plane Authority Intersection in Transport Matters
type: research
tags: [transport-matters, control-plane, authorization, launch-policy, provenance]
summary: Issue 595 now specifies effective launch authority as the ordered intersection of runtime request, launch limit, and any present override.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

## Executive Summary

Transport Matters issue 595 now defines one authority rule for direct CMDK and MCP launches. For a selected runtime, the effective grant is the minimum of the trusted runtime request, the Canvas or principal limit, and the optional override when present.

## Project Metadata

- Project: `littleorgans/transport-matters`
- Primary issue: `#595`, Resolve and persist effective control-plane authority
- Parent: `#593`
- Blocker: `#594`
- Upstream contract: `littleorgans/.agent-runtimes#2`
- Status verified: open
- Labels verified: `enhancement`, `P2`

## Architecture

Python owns authority resolution at the capture boundary after `agent_runtime_ref` resolves the trusted runtime. TypeScript transports the limit and optional override without calculating effective authority. The frozen decision contains `requested`, `limiting`, `override`, and `effective`, then flows through capture, runtime, gateway, audit, launch provenance, provisioning, and self identity.

Direct CMDK launches use the persisted Canvas grant as the limit and omit the override. MCP launches use `ControlPlanePrincipal.role` as the limit and treat the MCP `grant` input as an optional additional bound.

## Key Patterns

- The grant order is `none < observer < director`.
- A selected runtime resolves with `min(requested, limiting, override when present)`.
- An omitted override contributes no additional bound.
- Explicit `none` reduces effective authority to `none`.
- A director override cannot raise an observer or none runtime request.
- A raw launch without a selected runtime remains effective `none`.
- Null and explicit `none` stay distinct in intent fingerprints, provenance, replay, and audit.
- Only the effective grant reaches bearer provisioning and `RunSelfIdentity.control_access`.

## Detailed Findings

The previous guide described the override as a replacement for the runtime request followed by a clamp to the caller limit. That rule allowed a director override to raise an observer runtime request. The corrected guide uses one ordered intersection and adds explicit regression coverage for observer and none runtime requests combined with director limits and overrides.

The implementation guide identifies `api/src/transport_matters/controlplane/authority.py` as the owner of `ControlPlaneAuthorityDecision` and `resolve_control_plane_authority`. Transport carriers use `control_plane_grant_limit` and optional `control_plane_grant_override`. The existing `controlPlaneGrant` request field and aliases are deleted in the same change.

The documentation work names `docs/CONTROLPLANE.md` and `docs/LAUNCH-CONTRACT.md`. Both must explain intersection semantics, omission versus explicit `none`, frozen provenance, replay identity, and the rule that an override can only reduce authority.

## Dependencies

- `.agent-runtimes#2` publishes the runtime requested grant and capability contract.
- Transport Matters `#594` consumes that trusted contract into `RuntimeTemplateRef`.
- Transport Matters `#597` later filters MCP tool discovery using the effective grant and runtime capabilities.
- Transport Matters `#598` later presents Canvas consent, requested authority, and effective authority.

## Relevance to Helioy

The design separates authored runtime intent, user or principal limits, optional launch restrictions, and effective authority. This produces explainable launch provenance and prevents a caller supplied field from escalating the trusted runtime request.

## Open Questions

- Confirm the landed schema from `#594` before implementation begins.
- Confirm whether failure audit details use the same null representation as successful authority provenance.
- Revalidate named files and symbols against the implementation branch when `#594` lands.
