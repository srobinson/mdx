# S7 Canvas director scout

Verified against `main` at `e05373b6a4f5a101f1f4da95d499682e6bc8ee11`. The repository tree was pristine before the scout. This is a read only map. The only written artifact is this document.

## Reuse Map

All seven capabilities are implemented behind the MCP skin. They become usable from a Canvas agent only after that run receives an authenticated director grant.

| Capability | Wired for an MCP driven director? | Existing verb and owner |
|---|---|---|
| Discover and list live agents | Yes, conditional on bootstrap | MCP `roster()` and `workspace_summary()` in `api/src/transport_matters/api/v1/controlplane_mcp.py:create_control_plane_mcp`. `api/src/transport_matters/controlplane/service.py:ControlPlaneService._roster_snapshot` joins gateway activity with session and last turn data. `ControlPlaneService._summary_text` groups active states as working and reports idle, needs you, stalled, and exited counts. The status tier authority is `packages/contract/src/activity/wire.ts:activityStatusTier`. |
| Launch agents into the workspace | Yes, conditional on bootstrap | MCP `launch(workdir, harness, dispatch_id, name?, first_prompt?, grant?)` in `controlplane_mcp.py:create_control_plane_mcp`. `api/src/transport_matters/controlplane/launch_service.py:ControlPlaneLauncher.launch` requires a director, scopes the workdir, and calls `RunRouteProxy.create_run`. A service launch is registered on the open Canvas by `www/packages/canvas/src/model/capturedRunAdoption.ts:CapturedRunAdoptionReconciler`. The director can grant the child `none`, `observer`, or `director`. |
| Prompt one or many agents | Yes, conditional on bootstrap | MCP `prompt(targets, text, mode)` in `controlplane_mcp.py:create_control_plane_mcp`. `api/src/transport_matters/controlplane/service.py:ControlPlaneService.prompt` deduplicates targets, fans out through `_deliver_prompt_target`, and returns a receipt per target. `mode="nudge"` queues text for the next turn. `mode="interrupt"` breaks the current turn, settles, then submits text. |
| Read another agent and summarize its work | Yes for transcript text | MCP `conversation(run_id, shape="summary")` in `controlplane_mcp.py:create_control_plane_mcp`. `api/src/transport_matters/controlplane/read_store.py:ControlPlaneReadStore.timeline` reads the owner and workspace scoped Postgres timeline. `api/src/transport_matters/controlplane/conversation.py:project_conversation` strips tools, thinking, injected reminders, and attachments. Summary shape returns the first genuine user message plus the last four messages. The director performs the actual synthesis. There is no MCP surface for raw PTY scrollback and no server generated semantic summary. The normalized transcript surface satisfies this road test. |
| Watch agents and state | Yes, through an explicit subscription | MCP `watch(target, events)` and `unwatch(target)` in `controlplane_mcp.py:create_control_plane_mcp`. `api/src/transport_matters/controlplane/watch.py:ControlPlaneWatchEngine` consumes Activity state changes plus durable wire turn completions, coalesces them, then nudges the watcher PTY. Events are `turn_completed`, `state_changed`, and `needs_you`. A target can be one run id or `workspace`. |
| Interrupt or steer mid turn | Yes, conditional on bootstrap | MCP `interrupt(run_id)` calls `api/src/transport_matters/controlplane/service.py:ControlPlaneService.interrupt`, which sends `text=None, mode="interrupt"`. `packages/runtime/src/service/RunInputDelivery.ts:deliverInput` writes the harness break sequence and returns without submitting text. Text steering uses `prompt(..., mode="interrupt")` through the same primitive. |
| Stop or kill an agent | Yes, conditional on bootstrap | MCP `stop(run_id)` calls `ControlPlaneService.stop`, then `api/src/transport_matters/api/v1/run_proxy.py:RunRouteProxy.terminate_run`, then `packages/runtime/src/service/RunManager.ts:RunManager.terminate`. Runtime teardown performs TERM, bounded grace, KILL, PTY disposal, and capture release. |

The read surface for the requested summary therefore exists. It exposes correlated transcript text and excludes terminal bytes. Calling `conversation(..., shape="summary")`, then synthesizing the returned messages, is the intended director path.

## Grant + MCP bootstrap gap

The normal Canvas launch path gives the agent neither control plane MCP configuration nor authority over peer runs.

The exact missing seam is the browser spawn intent:

1. `www/packages/canvas/src/launcher/templateRows.ts:spawnCommand` creates a spawn command with harness, worktree, and optional runtime template. `www/packages/canvas/src/launcher/commandTypes.ts:LauncherCommand` has no grant field.
2. The command reaches `www/packages/canvas/src/model/capturedRunStore.ts:ensureRun`, then `www/packages/core/src/transport.ts:createCapturedRun`. `CreateCapturedRunOptions` and its request body have no `controlPlaneGrant` field.
3. `packages/runtime/src/server/runtimeRouter.ts:controlPlaneGrantFromBody` defaults an omitted field to `"none"`. `packages/runtime/src/service/RunManager.ts:RunManager.createNew` therefore prepares an ordinary Canvas capture.
4. `api/src/transport_matters/controlplane/provisioning.py:prepare_control_plane_grant` sees `NONE` and returns no prepared grant. No bearer is minted, no grant row is persisted, and no MCP client entry is added to the run home.

The backend path after that seam is complete:

- `runtimeRouter.ts` already accepts `controlPlaneGrant: "director"`.
- `packages/runtime/src/adapters/CaptureRpcClient.ts:prepareCaptureBody` forwards it to the capture RPC.
- `api/src/transport_matters/api/v1/capture_rpc_routes.py:_resolved_domain_request` supplies the local `http://127.0.0.1:<web_port>/mcp` URL for granted launches.
- `prepare_control_plane_grant` mints the bearer and calls `api/src/transport_matters/cli/home_seeders.py:seed_control_plane_client`.
- Claude receives `.mcp.json` plus `--mcp-config` through `captured_run_context.py:_build_provider_invocation` and `captured_claude.py:build_claude_captured_invocation`.
- Codex receives `[mcp_servers.transport-matters]` in its run local `config.toml` through `cli/codex_home.py:apply_codex_control_plane_client`.
- `captured_run.py:_persist_control_plane_grant` persists the digest before the spawn spec returns. `capture_rpc.py:CaptureLeaseRegistry.resolve_control_plane_grant` binds each request to the live run, workspace, and owner.

This makes the crux one browser side propagation gap. A runtime template does not imply a grant. Today, the normal Canvas launcher cannot mint the first director. A handcrafted create request can exercise the backend path, but it does not provide the intended product flow.

Reciprocal wake behavior needs one distinction. Explicit WATCH push is shipped: after the director calls `watch("workspace", ("needs_you", ...))`, a peer entering needs you produces a damped nudge into the director PTY. Automatic prompt origin coupling is absent. Prompting a peer does not automatically register a reciprocal wake relationship. Durable causal protection for reciprocal activity loops is the deferred B1 work in slice 22, documented in `CONTROLPLANE.md` under Watch. For this road test the director must register WATCH explicitly, or poll `roster()` and `conversation()`. It should not rely on automatic reply routing.

Gap count: 2.

1. Canvas does not propagate a director grant, so its launched agent has no authenticated control plane MCP client.
2. Prompting a peer does not create an automatic, causally safe reciprocal wake path. Explicit WATCH or polling is required until B1.

## Plan

One narrow PR can unlock the live Canvas scenario. No new control plane service verb is needed.

1. Put `CONTROL_PLANE_GRANT_OPTIONS` and `ControlPlaneGrantOption` on a browser safe `@tm/contract/runtime` subpath. Update `@tm/runtime` to consume that authority. This removes the current TypeScript vocabulary duplication risk and respects the product plane to browser boundary in `packages/AGENTS.md`.
2. Thread `controlPlaneGrant` through the existing Canvas spawn pipeline: `LauncherCommand` to `createCapturedRunRef` and the captured run pane record, then `CapturedRunPane`, `useCapturedRunBinding`, `EnsureRunOptions`, `CreateCapturedRunOptions`, and finally the `POST /v1/runs` body. Default remains `none`.
3. Add the specified three state Canvas spawn affordance: off, observer, director. Keep it spawn scoped. Selecting director must place `controlPlaneGrant: "director"` on that one create request. Reuse the existing Agents palette and captured run pipeline.
4. Extend focused contract tests at the real seams: core transport serializes the selected grant; Canvas preserves it from command to create; runtime defaults omission to none and forwards director; capture tests prove Claude and Codex homes contain the authenticated MCP server and the grant is revoked with the lease. Keep B1 outside this PR.
5. Road test in the desktop Canvas: launch a director pane, confirm the `transport-matters` MCP server is present, then invoke `roster`, `launch`, fan out `prompt`, `conversation(shape="summary")`, explicit workspace `watch`, `interrupt`, and `stop`. Confirm the director launched service run is adopted into Canvas. Use explicit WATCH before fan out when wake back matters.

The human REST principal and palette control plane REST client are not prerequisites. This scenario stays inside the run scoped MCP principal from launch through every action.

Verification observed on this head: the focused Python MCP, capture request, and grant seeding set passed `28` tests; `@tm/runtime` passed `175` tests; the shell suite, including Canvas service run adoption, passed `1,232` tests. Final `git status --short` was empty and HEAD remained `e05373b6a4f5a101f1f4da95d499682e6bc8ee11`.
