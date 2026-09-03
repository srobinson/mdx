# 598: Update Canvas consent and runtime authority UX

URL: https://github.com/littleorgans/transport-matters/issues/598
State: open
Labels: enhancement, P2
Updated: 2026-09-02T19:36:26Z

# Outcome

Make Canvas show and enforce the relationship between user consent, runtime requested authority, and effective launch authority.

Parent: #593
Blocked by: #595 and #597

# Scope

- Keep the persisted Canvas control-plane setting as the global user consent gate.
- Show the selected runtime requested grant and MCP capabilities in the launch expansion.
- Show the effective grant when the Canvas gate limits the runtime request.
- Ensure direct CMDK launches send the global gate and selected runtime identity through the canonical launch path.
- Remove copy or controls that imply one global grant is assigned directly to every runtime.
- Add clear consent copy for enabling observer or director access.
- Preserve keyboard navigation and compact CMDK behavior.

# Constraints

- This issue does not add directory or worktree scoping.
- This issue does not add per-launch tool checkboxes.
- Runtime manifests own requested capability defaults.
- Transport Matters owns effective policy.

# Acceptance criteria

- A user can see the requested and effective grants before launch.
- A runtime requesting `director` is visibly limited when the Canvas gate is `none` or `observer`.
- Changing the gate persists through reload.
- Existing runs do not silently change policy when the gate changes.
- CMDK, captured-run store, transport payload, accessibility, and keyboard tests pass.
- One browser test proves the consent flow and resulting launch payload.
- `just check` and `just test` pass.

## Implementation guide

### Start here

Use `packages/contract/src/runtime/index.ts` (`CONTROL_PLANE_GRANT_OPTIONS`, `ControlPlaneGrantOption`, `DEFAULT_CONTROL_PLANE_GRANT`), `www/packages/core/src/types/runtimeTemplates.ts` (`RuntimeTemplateSummary`), `www/packages/core/src/transport.ts` (`createCapturedRunView`), `www/packages/canvas/src/model/capturedRunStore.ts` (`useCapturedRunStore`, `cycleControlPlaneGrant`), `www/packages/canvas/src/launcher/commandTypes.ts` (`CommandRow`, `LauncherCommand`), `www/packages/canvas/src/launcher/templateRows.ts` (`buildAgentRows`, `agentSpawnRows`, `spawnCommand`), `www/packages/canvas/src/launcher/CommandCenter.tsx` (`CommandCenter`, `LauncherRow`), and `www/packages/shell/tests/e2e/spawn-palette.spec.ts`.

### Direction

Start after #595 and #597. Keep Canvas as the global ceiling for new launches and leave existing runs frozen. Consume the authority decision and filtered catalog contracts as shipped. Do not recreate the Python resolver, capability vocabulary, or tool mapping. Carry requested grant and ordered MCP capability identifiers from catalog fixtures into launcher rows. Change Settings copy so the persisted value is a ceiling for future launches rather than authority assigned to every runtime. For the highlighted agent row only, show requested grant, Canvas consent, absent launch override as `Not set`, effective grant, and requested MCP capabilities. When Canvas reduces the request, mark it limited by Canvas consent. Native harness rows stay native launches with no requested capabilities and effective `none`. Keep launch execution on the existing path: selected runtime id with the spawn command, current Canvas consent as the limit, and no override. Canvas never raises a request. Changing consent persists through reload and must not mutate existing captured run records. Python remains authoritative. Use `CONTROL_PLANE_GRANT_OPTIONS` for the direct CMDK comparison.

### Guardrails

This issue does not add directory or worktree scoping, per launch tool checkboxes, or an override control. Do not duplicate authority resolution or tool filtering from #595 through #597. Do not infer policy from names, skills, descriptions, MCP server names, or tool prefixes. Do not change MCP SDK versions, transport, bearer minting, or home seeding. Prove persistence, frozen existing run policy, payload shape, accessibility, keyboard behavior, and one browser consent flow. `just check` and `just test` must pass.


## Sub issues
[]
