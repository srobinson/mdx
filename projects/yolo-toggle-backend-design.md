# Yolo toggle backend design

Created: 2026-06-19
Status: design only

## Recommended seam

Use a per spawn boolean named `bypass_permissions`, exposed on the public request as `bypassPermissions`, and carry it through the existing run request chain:

```python
CreateRunRequest.bypass_permissions: bool = Field(default=False, alias="bypassPermissions")
SpawnRun.bypass_permissions: bool = False
CapturedRunRequest.bypass_permissions: bool = False
```

The cleanest injection seam is the existing harness profile argv seam:

- `api/src/transport_matters/cli/launch_profile.py LaunchProfile.client_argv`
- `api/src/transport_matters/cli/launch_profile.py ClaudeLaunchProfile.client_argv`
- `api/src/transport_matters/cli/launch_profile.py CodexLaunchProfile.client_argv`

Add `bypass_permissions: bool = False` to the profile argv contract and let each profile insert its own fixed flag in its existing argv shape. This keeps arbitrary flags out of the API and avoids new parallel launch paths.

Proposed mapping:

```python
CLAUDE_BYPASS_PERMISSIONS_ARG = "--dangerously-skip-permissions"
CODEX_BYPASS_PERMISSIONS_ARG = "--yolo"
```

Profile placement:

```python
# Claude current shape
[client_path, *passthrough, *bypass_args, *session]

# Codex current shape
[client_path, *_codex_shell_environment_policy_args(), *bypass_args, *resume, *passthrough]
```

The two profile edits are unavoidable because Claude and Codex already have different command shapes. The DRY boundary is that the boolean is threaded once through the run contracts, and the only flag mapping lives in the launch profile layer that already owns provider argv construction.

## Current launch argv assembly

### Claude captured run

Path:

1. `api/src/transport_matters/captured_run.py prepare_captured_run`
2. `api/src/transport_matters/captured_run_context.py build_captured_run_context`
3. `api/src/transport_matters/captured_claude.py build_claude_captured_invocation`
4. `api/src/transport_matters/cli/launch_profile.py ClaudeLaunchProfile.client_argv`

`build_claude_captured_invocation` builds the managed Claude child with `profile.client_argv(...)`. `ClaudeLaunchProfile.client_argv` currently returns:

```python
[client_path, *passthrough, *session]
```

### Codex captured run

Path:

1. `api/src/transport_matters/captured_run.py prepare_captured_run`
2. `api/src/transport_matters/shared_proxy/run_preparation.py prepare_shared_captured_run` for external desktop proxy mode
3. `api/src/transport_matters/captured_run_context.py build_captured_run_context`
4. `api/src/transport_matters/captured_codex.py build_codex_captured_invocation`
5. `api/src/transport_matters/cli/codex_cmd.py build_codex_invocation`
6. `api/src/transport_matters/cli/launch_profile.py CodexLaunchProfile.client_argv`

`build_codex_captured_invocation` delegates to `build_codex_invocation`. `build_codex_invocation` builds the managed Codex child with `profile.client_argv(...)`. `CodexLaunchProfile.client_argv` currently returns:

```python
[client_path, *_codex_shell_environment_policy_args(), *resume, *passthrough]
```

### One place or two

There is one common captured run preparation seam, `api/src/transport_matters/captured_run_context.py build_captured_run_context`, but there is no single existing place where per harness client flags are appended.

The existing provider aware argv seam is `LaunchProfile.client_argv` with two concrete implementations. That is the right home for this feature because it preserves the existing ownership of argv order.

## Passthrough assessment

### Existing mechanisms

- `api/src/transport_matters/cli/__init__.py _split_passthrough` reads CLI args after `--` for `transport-matters claude` and `transport-matters codex`.
- `api/src/transport_matters/cli/start_cmd.py run_start` carries Claude CLI passthrough into `CapturedRunRequest.passthrough`.
- `api/src/transport_matters/cli/codex_cmd.py run_codex` carries Codex CLI passthrough into `prepare_launch` and then into `build_codex_invocation`.
- `api/src/transport_matters/captured_run_models.py CapturedRunRequest.default_client_passthrough` and `api/src/transport_matters/launch_environment.py build_launch_env` expose default passthrough to the launch environment, but this does not append flags to the managed client argv by itself.

### Desktop captured pane path

The desktop path cannot use raw passthrough for this feature:

- `www/src/api.ts createCapturedRun` sends only `harness`, optional `cwd`, `oscColorReplies`, and optional `runtimeTemplate`.
- `api/src/transport_matters/api/v1/run_routes.py CreateRunRequest` has no passthrough field.
- `api/src/transport_matters/api/v1/run_routes.py _spawn_request` sets `passthrough=()` unconditionally.
- `api/src/transport_matters/cli/__init__.py desktop` does not allow extra args, unlike the `claude` and `codex` CLI commands.
- `api/src/transport_matters/cli/test_desktop.py test_desktop_rejects_provider_flags_and_passthrough` asserts provider flags and `--` passthrough are rejected for desktop.
- `api/src/transport_matters/cli/desktop_cmd.py _DESKTOP_BACKEND_STALE_ENV_KEYS` scrubs `TRANSPORT_MATTERS_DEFAULT_CLIENT_PASSTHROUGH` from the desktop backend environment.

Conclusion: `-- args` is usable for direct CLI launches, not for captured panes spawned by the desktop launcher. `default_client_passthrough` is metadata for the launch environment and shared proxy binding, not a safe public control surface for this setting.

## Boolean threading plan

Mirror the current `runtime_template` carrier path:

1. `api/src/transport_matters/api/v1/run_routes.py CreateRunRequest`
   - Add `bypass_permissions: bool = Field(default=False, alias="bypassPermissions")`.
2. `api/src/transport_matters/api/v1/run_routes.py _spawn_request`
   - Pass `bypass_permissions=body.bypass_permissions` into `SpawnRun`.
3. `api/src/transport_matters/run_models.py SpawnRun`
   - Add `bypass_permissions: bool = False`.
4. `api/src/transport_matters/run_manager.py RunManager._captured_request`
   - Pass `bypass_permissions=request.bypass_permissions` into `CapturedRunRequest`.
5. `api/src/transport_matters/captured_run_models.py CapturedRunRequest`
   - Add `bypass_permissions: bool = False`.
6. `api/src/transport_matters/captured_run_context.py build_captured_run_context`
   - Pass the boolean into both provider invocation builders, or keep it on the request object and let builders read it.
7. `api/src/transport_matters/captured_claude.py build_claude_captured_invocation`
   - Forward `bypass_permissions` to `profile.client_argv(...)`.
8. `api/src/transport_matters/captured_codex.py build_codex_captured_invocation`
   - Forward `bypass_permissions` to `build_codex_invocation(...)`.
9. `api/src/transport_matters/cli/codex_cmd.py build_codex_invocation`
   - Forward `bypass_permissions` to `profile.client_argv(...)`.
10. `api/src/transport_matters/cli/launch_profile.py LaunchProfile.client_argv`
   - Add the boolean and perform profile owned insertion in the two concrete profiles.

This mirrors the verified `runtime_template` chain:

- `api/src/transport_matters/api/v1/run_routes.py CreateRunRequest.runtime_template`
- `api/src/transport_matters/api/v1/run_routes.py _runtime_template_ref`
- `api/src/transport_matters/api/v1/run_routes.py _spawn_request`
- `api/src/transport_matters/run_models.py SpawnRun.runtime_template`
- `api/src/transport_matters/run_manager.py RunManager._captured_request`
- `api/src/transport_matters/captured_run_models.py CapturedRunRequest.runtime_template`
- `api/src/transport_matters/captured_run_context.py build_captured_run_context`

Frontend can persist the global toggle wherever launcher settings live, then pass the current value on each call to `www/src/api.ts createCapturedRun`. Backend state stays per spawn.

## Flag validation

### Claude

Repo evidence confirms the current Claude bypass flag name is `--dangerously-skip-permissions`:

- `api/src/transport_matters/test_captured_run_web_separation.py` uses it in `CapturedRunRequest.passthrough` and asserts it reaches `spawn_spec.client.argv`.
- `api/src/transport_matters/test_config.py` uses it in default client passthrough config.
- Local `claude --help` lists `--dangerously-skip-permissions` as the flag that bypasses permission checks.

### Codex

Repo source does not currently hard code `--yolo`. Current local Codex accepts it:

- `codex --yolo --version` exited 0 and printed `codex-cli 0.141.0`.
- `codex --definitely-not-a-codex-option --version` exited 2 with an unexpected argument error.
- `codex resume 00000000-0000-4000-8000-000000000001 --yolo --version` exited 0 and printed `codex-cli-resume 0.141.0`.
- Local `codex --help` exposes the long equivalent `--dangerously-bypass-approvals-and-sandbox`.

Use `--yolo` for the requested product behavior because the current installed CLI recognizes it, while noting it is not documented in repo code today.

## API contract delta

```typescript
type CapturedRunHarness = "claude" | "codex";

interface CreateRunRequest {
  harness: CapturedRunHarness;
  cwd?: string;
  terminal?: { cols: number; rows: number };
  oscColorReplies?: boolean;
  continueFromSessionId?: string;
  idempotencyKey?: string;
  runtimeTemplate?: string;
  bypassPermissions?: boolean; // default false
}
```

No arbitrary argv field should be added to `/v1/runs`.

## Security notes

- Default is `false`.
- The public API accepts a boolean only. It never accepts raw provider flags.
- Invalid harness handling stays in `api/src/transport_matters/api/v1/run_routes.py _validated_harness`.
- This setting applies only to subsequent spawns. Existing runs are unchanged.
- A follow up implementation should add tests that assert the exact managed client argv for both harnesses and that unknown request fields do not become arbitrary flags.

## Minimal test plan for implementation

- API route test: `POST /v1/runs` with `bypassPermissions: true` produces a `SpawnRun` carrying `bypass_permissions=True`.
- Run manager test: `RunManager._captured_request` preserves the boolean into `CapturedRunRequest`.
- Claude argv test: captured Claude client argv includes `--dangerously-skip-permissions` exactly once when enabled and omits it by default.
- Codex argv test: captured Codex client argv includes `--yolo` exactly once when enabled and omits it by default.
- Frontend API test: `createCapturedRun` includes `bypassPermissions` only when the launcher setting is on, or sends explicit `false` if the chosen frontend contract prefers explicitness.
