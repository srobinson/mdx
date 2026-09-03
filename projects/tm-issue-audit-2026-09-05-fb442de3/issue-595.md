# 595: Resolve and persist effective control-plane authority

URL: https://github.com/littleorgans/transport-matters/issues/595
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:10:31Z

# Outcome

Calculate and persist one effective control-plane grant for every agent runtime launch.

Parent: #593
Blocked by: #594

# Policy

Use the ordered grant set `none < observer < director`.

- The selected runtime supplies its trusted requested grant.
- The persisted Canvas setting supplies the limiting grant for direct CMDK launches.
- The launching principal supplies the limiting grant for MCP launches.
- An optional MCP `launch()` grant supplies one additional bound when present.
- For a selected runtime, the effective grant is the minimum of the runtime request, the limiting grant, and the optional override when present.
- An omitted MCP `launch()` grant adds no bound, so the runtime request remains subject to the launching principal limit.
- An explicit MCP `launch()` grant of `none` reduces the effective grant to `none`.
- An observer or none runtime request cannot be raised by a director override.
- A raw launch with no selected runtime uses the safe effective grant `none`.

# Scope

- Change the MCP launch grant parameter so omitted and explicit `none` remain distinct.
- Add a pure policy function that resolves the effective grant.
- Apply the policy to direct CMDK and MCP launches.
- Persist requested, limiting, override, and effective values as launch provenance.
- Keep control-plane bearer minting and MCP home seeding driven by the effective grant.
- Update self identity to report the effective grant.
- Add audit fields needed to explain the decision.

# Constraints

- Canvas remains the user consent gate.
- Child launches remain bounded by the launching principal.
- Tool discovery filtering lands separately.
- Directory and worktree scope is deferred.

# Acceptance criteria

- A runtime requesting `director` receives no more than the Canvas gate permits.
- An observer principal cannot launch a director.
- Omitted and explicit `none` produce distinct policy inputs.
- CMDK and MCP launches use the same pure resolver.
- Restart and replay preserve the effective policy and provenance.
- No grant creates no bearer and no Transport Matters MCP client.
- Grant resolution, provisioning, launch skin, audit, and exact-response tests pass.
- `just check` and `just test` pass.

## Implementation guide

### Start here

Land issue 594 first and read the trusted requested grant from `runtime_templates.py` (`RuntimeTemplateRef`). Resolve the selected runtime through `launch_resolution.py` (`agent_runtime_ref`). Reuse `controlplane/models.py` (`ControlPlaneGrantOption`, `ControlPlanePrincipal`) for vocabulary and the caller limit. Apply the policy once in `capture_rpc_routes.py` (`_resolved_domain_request`) after runtime selection and before any home is prepared. Keep provisioning on `captured/context.py` (`_prepare_home_and_grant`) and MCP limits on `launch_service.py` (`ControlPlaneLauncher`). Direct CMDK launches send the persisted Canvas setting from `capturedRunStore.ts` (`ensureRun`) as the limit only.

### Direction

- Compute the effective grant as the minimum of the runtime request, the caller limit, and an optional reducing override when present. Use the ordered set `none < observer < director`. Persist the four decision values `requested`, `limiting`, `override`, and `effective`. A missing selected runtime uses null for `requested` and `none` for `effective`. An omitted override uses null. An explicit `none` uses `none`.
- Python owns policy. TypeScript transports inputs without calculating authority. Direct CMDK launches use the Canvas setting as the limit and never send an override. MCP launches use `ControlPlanePrincipal.role` as the limit and the `launch()` grant as the optional additional bound. Omission adds no bound. Explicit `none` reduces to `none`. A director override or director principal cannot raise an observer or none runtime request. A raw launch is effective `none`.
- Replace the single launch grant carrier with a limit plus an optional override, and delete the old carrier in the same change. Pass only the effective value to bearer minting, home seeding, and `whoami`. Return the frozen decision on the private capture and gateway path for audit. Keep public `LaunchResult` unchanged.

### Guardrails

- Resolve authority only after `agent_runtime_ref`. Never accept caller supplied runtime policy. Freeze the decision before `prepare_control_plane_grant`. Effective `none` creates no bearer and no Transport Matters MCP client. `whoami` reports only the effective grant.
- Do not filter `tools/list`, redesign Canvas consent, add directory or worktree authority, or add a database table for provenance. Use existing `launch_fields`. Prove the full ordered intersection table, omitted versus explicit `none`, and restart replay, then `just check` and `just test`.


## Sub issues
[]
