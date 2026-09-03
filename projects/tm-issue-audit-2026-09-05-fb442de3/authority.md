# Authority and MCP catalog backlog audit

Audited at source SHA `535118346ca5d0584a7a4a3da28a55be532dc3bd` on 2026-09-05. Assigned issues: #593, #595, #596, #597, #598, #599, #600. All seven supplied issue bodies were read in full. They contain zero comments.

## Executive reconciliation

The parent #593 is a program umbrella, not an eighth implementation slice. Its two prerequisites are shipped: `.agent-runtimes` issue #2 publishes schema v4, and Transport Matters #594 consumes and transports the requested grant and ordered capability list. The shipped TM implementation is commit `0ee82d2b` / PR #615. It deliberately leaves effective launch authority on `PrepareCaptureRequest.control_plane_grant`, exactly as #594 required.

What is still genuinely missing is the policy and catalog chain:

1. #595 must calculate one effective grant from runtime request, Canvas gate or launching principal, and optional MCP override, then persist the decision and use only the effective value for identity, bearer minting, and home seeding.
2. #596 must replace decorator order with a validated 34-tool catalog and encode the current 14 observer / 20 director split plus capability identifiers.
3. #597 must use that catalog and the frozen run capability tuple to filter `tools/list` and reject hidden calls before dispatch. Current call-time authorization remains necessary and must stay.
4. #598 is the Canvas preview and consent slice. Its UI does not need the filtering adapter itself. The current declared dependency on #597 is sequencing, not a code dependency, unless the UI intentionally consumes a server-produced filtered catalog.
5. #599 and #600 are MCP infrastructure. They are not prerequisites for authority correctness. #599 is the SDK port; #600 is the mounted transport policy and dual-client proof. The two issues currently overlap on moving `stateless_http`, `json_response`, and `streamable_http_path`; that move belongs to #600 and should be removed from #599’s implementation guide.

## Dependency DAG

Declared issue relationships:

```text
agent-runtimes #2 -> TM #594 -> #595
                              \-> #596
#595 + #596 -> #597
#595 + #597 -> #598
#597 -> #599 -> #600
```

Recommended implementation DAG, separating true dependency from convenient sequencing:

```text
#2 -> #594 -> (#595 || #596) -> #597 -> #599 -> #600
                 \------------> #598
```

The direct code dependencies are:

- #595 requires #594 because it reads `RuntimeTemplateRef.requested_grant` and the trusted capability tuple.
- #596 requires #594’s closed capability vocabulary, although the issue body omits that prerequisite and only says to reuse the type.
- #597 requires both #595’s effective role and #596’s catalog. It must not invent a second grant order, capability vocabulary, or authorization rule.
- #598 requires #595’s resolved decision and #594/#596’s requested capability metadata. #597 is a useful sequencing point for shared fixtures, but its discovery adapter is not needed to render requested versus effective authority or to send the existing `agentId` plus Canvas gate payload.
- #599 can be developed independently of #595, #596, and #598 at the semantic level. The declared #597 dependency reduces rework because the SDK port then carries the final filtered adapter shape. Keep it as a coordination dependency only if the team wants that order.
- #600 genuinely follows #599 because it owns the SDK 2.x mounted app and client proof. Its transport correctness is independent of authority policy, though its final captured-run smoke test should run with #595 and #597 complete.

## Current shipped baseline

### Requested runtime policy is present, but not resolved

The runtime contract and TM consumer now carry `requested_grant` and ordered `requested_capabilities` through the registry, catalog projection, `RuntimeTemplateRef`, and template provenance. The producer rules reject `none` with capabilities and require capabilities for observer or director. This is evidence for #2 and #594, not evidence that authority is enforced.

Current launch code still exposes `PrepareCaptureRequest.control_plane_grant` as the sole launch authority input (`api/src/transport_matters/api/v1/capture_rpc_routes.py:143-146`, domain carrier `api/src/transport_matters/captured/models.py:207-209`). `_prepare_home_and_grant` passes that raw value directly to `prepare_control_plane_grant` (`api/src/transport_matters/captured/context.py:272-315`), and run identity reports the same raw value (`api/src/transport_matters/captured/context.py:186-197`). No pure resolver or four-value decision exists. The MCP launch path also forwards its `grant` argument directly to the service and gateway (`api/src/transport_matters/api/v1/controlplane_mcp.py:318-345`, `api/src/transport_matters/controlplane/launch_service.py:118-146`, `api/src/transport_matters/controlplane/launch_service.py:247-252`). Its schema default is `none` (`controlplane_mcp.py:490-514`), so omitted and explicit `none` are currently indistinguishable.

This leaves both overgrant and undergrant cases. A direct native or runtime launch can receive the persisted Canvas grant without a runtime request bound. An MCP caller can explicitly grant a selected runtime more than it requested. An omitted MCP grant currently forces `none`, instead of adding no bound. Existing tests assert raw passthrough, for example `api/src/transport_matters/controlplane/test_launch_manage.py:66-103`; they do not prove the #595 intersection table.

### The MCP server has 34 tools, but no canonical catalog

The source has 13 core decorators, 13 Space/Canvas/Worktree decorators, and 8 browser decorators, for 34 unique names. The current registration order is decorator order in `controlplane_mcp.py:417-540`, `space_mcp.py:454-538`, and `browsing_mcp.py:150-215`. There is no `api/src/transport_matters/api/v1/mcp_tool_catalog.py` at this SHA. The existing contract test checks a set of names (`test_controlplane_action_skins.py:91-133`) and therefore discards ordering; it does not validate catalog entries, annotations, capability ids, or registrar drift.

Call-time policy is distributed in the existing service and adapters. The current behavior supports the intended 14/20 classification: observe-only reads include catalog/workspace/self/harness/roster/conversation/watch/unwatch, bound Canvas and Worktree reads, browser pane listing, and browser history listing; director-only operations include prompt, wait, launch, close, interrupt, Space mutations, Canvas and Worktree mutations, browser mutations, and history deletion. That classification is not declared in one source of truth.

### Discovery is unfiltered, while request authentication already exists

`ControlPlaneMcpAuthApp` resolves the bearer before every SDK request and resets the context afterward (`controlplane_mcp.py:160-187`). Revocation coverage already exists in `test_controlplane_skins.py:408-440`. However, `create_control_plane_mcp` returns a plain `FastMCP`, and all 34 tools remain registered and listable (`controlplane_mcp.py:397-415`, `:417-541`). `ControlPlanePrincipal` carries role and scope but no frozen runtime capability tuple (`controlplane/models.py:66-77`); `_CaptureRunFacts` also has no capability field (`capture_rpc.py:105-130`). There is no pure catalog eligibility predicate and no pre-dispatch hidden-tool rejection. A guessed director call can reach the existing adapter/domain guard, but the tool name and metadata already leaked through discovery.

### MCP 2.x and transport proof are not shipped

The project declares `mcp>=1.28,<2` (`api/pyproject.toml:37-48`) and locks `mcp` at 1.28.1 with `httpx-sse` (`api/uv.lock:916-934`). The server imports `FastMCP` and the 1.x settings workaround (`controlplane_mcp.py:11-16`, `:90-91`). `httpx2` is dev-only in the current project metadata (`pyproject.toml:67-79`); `mcp-types` and `opentelemetry-api` are absent from the lock.

The current server constructor already sets `stateless_http=True`, `json_response=True`, and `streamable_http_path="/"` (`controlplane_mcp.py:397-414`), while `main.py` calls `streamable_http_app()` with no arguments and owns the exact `/mcp` wrapper/mount (`main.py:616-633`). There are no current tests for the 4 MiB boundary, modern `server/discover`, legacy plus modern clients, or the exact mounted endpoint against a real seeded home. Per-request auth is an existing partial, not proof of the full #600 outcome.

## Per-issue disposition

### #593, program umbrella: umbrella

Keep as the roll-up and close it only when the slices reconcile. It has eight children, two closed and six open at snapshot time, but it must not be counted as implementation work. Its useful remaining role is acceptance aggregation: authority, catalog, filtering, Canvas, SDK port, and transport proof all pass the shared checks and real-client smoke criteria. Do not duplicate implementation criteria in #593.

### #595, effective authority: keep

Canonical work `authority.resolve`. Priority P1, effort L, confidence high. This is the highest-value remaining slice because the current runtime request is transported but does not constrain the grant actually minted. Keep the issue’s four decision values (`requested`, `limiting`, `override`, `effective`) and its omission-versus-explicit-`none` rule. Use one Python resolver after trusted `agent_runtime_ref`, with direct Canvas and MCP as input adapters. Persist the frozen decision in the existing launch facts, keep `LaunchResult` stable, and make `none` suppress bearer/home seeding. Add tests for all ordered intersections, native/raw launch, MCP omission, explicit none, replay, identity, and audit.

### #596, canonical catalog: keep

Canonical work `catalog.define`. Priority P1, effort M, confidence high. The outcome is distinct from #597: this issue defines and validates the 34-entry registry without changing exposure. Preserve current names and schemas, encode the 14/20 split and capability ids, and add annotations only where behavior supports them. Validation must finish before the first registration. Make the ordered catalog the test source so registrar drift and ordering fail deterministically.

### #597, filtered discovery: keep

Canonical work `catalog.filter`. Priority P1, effort L, confidence high. The missing outcome is run-scoped discovery, not a new call authorization system. Freeze the runtime capability tuple in the capture facts, carry it into the authenticated principal, and apply one pure intersection predicate to role plus capability. Keep all implementations registered, preserve canonical order, reject hidden calls before adapter/audit/gateway work, and retain the existing live identity, role, workspace, Space, Canvas, Worktree, browser, audit, and revocation checks. Current per-request bearer resolution is reusable evidence, not a reason to close this issue.

### #598, Canvas authority UX: rewrite

Canonical work `canvas.authority-ux`. Priority P2, effort M, confidence high. The user outcome is valid, but remove the hard dependency on #597 unless the UI is changed to consume a filtered server catalog. Current Canvas already threads the selected `agentId` and persisted `controlPlaneGrant` through the existing launch path (`www/packages/canvas/src/model/capturedRunStore.ts:207-233`, `www/packages/core/src/transport.ts:400-440`, `CanvasCommandDispatcher.ts:31-43`). The missing work is the preview: requested grant, Canvas ceiling, absent override, effective grant, and requested capabilities for the highlighted runtime. The current Settings copy describes the global setting as access assigned to spawned agents (`www/packages/canvas/src/launcher/commandRows.ts:47-63`, `:168-206`) and launcher rows show no authority fields (`templateRows.ts:95-117`). Preserve future-launch-only semantics and prove existing run records remain frozen.

### #599, SDK migration: rewrite

Canonical work `mcp.sdk2`. Priority P2, effort L, confidence high. Keep this as the mechanical dependency and client-fixture migration: `mcp>=2.1,<3`, lock regeneration, `MCPServer`, snake-case SDK fields, HTTPX 2 client support, and unchanged wire/auth/catalog behavior. Remove the transport policy relocation from the implementation guide. The issue’s constraint says transport configuration moves in the following issue, while its direction also assigns the three `streamable_http_app` settings to #599; #600 assigns exactly the same work. That is a direct overlap and should be resolved before implementation.

### #600, transport policy and dual clients: keep with boundary clarification

Canonical work `mcp.transport-proof`. Priority P2, effort L, confidence medium. Keep the endpoint/mount owner, explicit server version, 4 MiB SDK boundary, per-request auth proof, legacy/modern handshake tests, seeded Claude/Codex/Grok checks, and one real captured run. Make #600 the sole owner of moving `stateless_http`, `json_response`, and `streamable_http_path` from the server constructor to `streamable_http_app()`. Its final bounded-catalog smoke test depends on #595 and #597 transitively, but transport policy itself does not.

## Work packages

1. `authority-core` (#595), P1 / high value / L. Depends on #594. Acceptance: one pure resolver; min(requested, limiting, optional override); omitted versus explicit none; direct and MCP launch paths; frozen provenance and identity; no bearer/client for effective none; restart/replay and full checks. Risk: an adapter accidentally trusts caller policy or a replay recomputes against current Canvas/runtime state.
2. `catalog-contract` (#596), P1 / high value / M. Depends on #594. Acceptance: all 34 names exactly once in stable order, 14/20 grant split, capability ids, annotations, unchanged schemas/results, pre-registration validation, registrar drift tests. Risk: catalog metadata is accidentally used as authorization or current domain auth is duplicated.
3. `catalog-enforcement` (#597), P1 / high value / L. Depends on #595 and #596. Acceptance: observer/director and capability intersections, credential-only deterministic list, frozen capabilities, hidden-call rejection before dispatch, revoked/expired bearer behavior, real-client list/call, unchanged domain checks. Risk: a connection cache or registry reread makes catalogs mutable during a run.
4. `canvas-authority` (#598), P2 / medium-high value / M. Depends on #595 and #596; #597 is optional sequencing. Acceptance: selected-row preview of requested, ceiling, override state, effective, and capabilities; payload uses runtime id plus Canvas ceiling; reload persistence; existing-run freeze; keyboard/accessibility/browser coverage. Risk: TypeScript reimplements Python policy or implies that changing the gate mutates existing runs.
5. `mcp-sdk2` (#599), P2 / medium value / L. Recommended after #597 to avoid porting an intermediate adapter, though semantically independent. Acceptance: no FastMCP imports, SDK 2.1.1 dependency and lock, extracted shared client support, snake-case internals with alias-preserving wire assertions, unchanged endpoint/auth/catalog/call behavior, full checks. Risk: lock/dependency churn or a compatibility wrapper leaves two server paths.
6. `mcp-transport-proof` (#600), P2 / high integration value / L. Depends on #599; final smoke also requires #595/#597. Acceptance: one mounted app owner, exact `/mcp`, explicit server version, required transport settings, 4194304 success and 4194305 rejection, legacy and modern list/call, per-request revocation, seeded homes, one real bounded run. Risk: SDK defaults drift or the real client path is only tested through an in-process helper.

## Reconciliation and uncertainty

- #2 and #594 are historical shipped prerequisites verified from GitHub read-only and commit `0ee82d2b` / PR #615. No assigned issue comments supersede their bodies.
- The code and tests prove structure and current policy paths. No provider-spending probe or live Claude/Codex/Grok smoke was run, as the brief excludes it. Real-client compatibility, SDK 2.1.1 exact API behavior, and the 4 MiB boundary remain implementation-time verification items.
- Existing direct call-time authorization is a safety backstop. It does not satisfy discovery minimization, frozen runtime capabilities, or pre-dispatch hidden-call rejection.
- The current docs still describe a single launch-time grant (`docs/CONTROLPLANE.md:38-54`) and must be updated with #595’s effective-decision semantics after the code lands. The docs should not be changed as part of this audit.

Completion footer: assigned issue count 7; total comments read 0; source SHA `535118346ca5d0584a7a4a3da28a55be532dc3bd`; source files/PRs checked include `api/src/transport_matters/runtime_templates.py`, `runtime_registry.py`, `api/v1/capture_rpc_routes.py`, `capture_rpc.py`, `captured/context.py`, `captured/models.py`, `controlplane/models.py`, `controlplane/launch_service.py`, `api/v1/controlplane_mcp.py`, `space_mcp.py`, `browsing_mcp.py`, `main.py`, `api/pyproject.toml`, `api/uv.lock`, `docs/CONTROLPLANE.md`, `www/packages/canvas/src/model/capturedRunStore.ts`, `launcher/commandRows.ts`, `launcher/templateRows.ts`, `www/packages/core/src/transport.ts`, current MCP skin tests, agent-runtimes issue #2, Transport Matters issue #594, and shipped PR #615 (`0ee82d2b`).
