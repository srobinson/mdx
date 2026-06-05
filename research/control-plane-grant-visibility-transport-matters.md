---
title: Control plane grant visibility across Canvas and MCP launches
type: research
tags: [transport-matters, control-plane, mcp, codex, launch, grants]
summary: Canvas-persisted director applies only to CMDK spawns; MCP launch defaults grant to none per call, and codex never puts tools on the wire.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-02
updated: 2026-09-02
---

## Executive Summary

Two independent facts produce the reported contradiction. First, the Canvas
`controlPlaneGrant` (persisted `director`) is applied only to Canvas CMDK spawns;
a run launched by another agent through the `mcp__transport-matters__launch` tool
takes its authority from that call's `grant` argument, which defaults to `none`
and inherits nothing. Second, Codex 0.152.1 sends no `tools` array on the wire at
all, so the absence of `tools/*/name` in a Codex capture is a protocol artifact
and is not evidence about the grant.

There is no agent-template special case and no harness-specific grant handling.

## Root Cause

`grant` is per-call and defaults to `none`:

- `api/src/transport_matters/api/v1/controlplane_mcp.py::launch` (the `@mcp.tool()`
  function and `ControlPlaneMcpAdapter.launch`) — `grant: ControlPlaneGrantOption
  = ControlPlaneGrantOption.NONE`. The tool docstring does not mention `grant`.
- `api/src/transport_matters/controlplane/launch_service.py::ControlPlaneLaunchService.launch`
  — same default.
- `api/src/transport_matters/controlplane/launch_service.py::_normalize_launch_request`
  — takes `bypass_permissions=principal.bypass_permissions` from the launching
  principal but takes `grant` only from the argument. That asymmetry is the shape
  of the surprise: bypass inherits, authority does not.
- `api/src/transport_matters/captured/context.py` (`control_access=request.control_plane_grant.value`)
  — the self-identity `Control access` line is the direct projection of the
  prepare request's grant, so it is the reliable per-run signal.

The behaviour is documented in `tm-orchestrate/SKILL.md` line 25: "children you
launch get the authority you `grant`, defaulting to `none`."

The Canvas side has a single spawn path with no template branch:
`www/packages/canvas/src/infrastructure/runtime/useCapturedRunBinding.ts` →
`capturedRunStore::ensureRun` (sends `controlPlaneGrant: get().controlPlaneGrant`)
→ `www/packages/core/src/transport.ts::createCapturedRunView` → `POST /v1/runs`.
The value is persisted through `partialize`/`migrate` in
`www/packages/canvas/src/model/capturedRunStore.ts`.

## Artifact Evidence (preview home, 2026-09-02)

Origin discriminator in `~/.transport-matters-preview/runtime/desktop.log`:
Canvas spawns appear as the uvicorn line `"POST /v1/runs HTTP/1.1" 201`;
control-plane launches appear as the httpx line
`POST http://127.0.0.1:58244/v1/runs?owner=local` preceded by
`Processing request of type CallToolRequest` and `Control plane launch ledger cardinality=N`.

| run | harness / template | origin | Control access |
| --- | --- | --- | --- |
| a5f292db | claude / orchestrator | Canvas | director |
| e859d99e | codex / imagegen | Canvas | director |
| e644aec8 | claude / generalist | MCP | director |
| 6107cff3 | claude / generalist | MCP | director |
| 26d13d3f | claude / generalist | MCP | director |
| dda34ad8 | codex / generalist | MCP | none |
| 9fb860fb, eb8dd75d, 25eeef9a, ddbe1c99 | claude | MCP | none |

Every Canvas launch that day carried `director`, including a Codex one. Every
`none` run was an MCP launch. Codex therefore does receive `director` when the
caller asks for it, which rules out a harness difference.

## Codex Wire Protocol

`transport.json` for dda34ad8 records `provider: codex`, `protocol: websocket`,
upgrade path `chatgpt.com/backend-api/codex/responses`, with
`client_metadata.ws_request_header_x_openai_internal_codex_responses_lite: "true"`.
Frames are `{"type": "response.create", ...}` and carry no `tools` key. `index.jsonl`
reports `tools_count: 0` for every turn. The same holds for e859d99e, which had
`Control access: director`. Tool definitions on the wire are therefore not a
usable visibility signal for Codex; the self-identity `Control access` line is.

## Bounded Conclusion

The reported "CMDK Agents launches without TM MCP tools" is not reproducible from
these artifacts as a CMDK defect. The runs lacking tools were launched by the
orchestrator through the MCP `launch` tool without a `grant` argument, so they
were provisioned with `none` by design. The remaining question is a product one:
whether `launch` should inherit the caller's authority (as `bypass_permissions`
already does) or keep requiring an explicit grant.
