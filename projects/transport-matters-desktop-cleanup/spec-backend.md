# Desktop Cleanup Backend Spec

## Executive summary

This spec is now scoped to run ahead backend and CLI cleanup only. Desktop launch becomes app owned: Electron owns the backend child, `transport-matters desktop` becomes a thin opener, and all desktop agent starts happen through captured panes via the curated run API.

This removes the current raw CLI option and passthrough surface from desktop. Standalone `transport-matters claude` and `transport-matters codex` stay in scope as terminal commands, but desktop stops depending on them. The template picker UI and runtime template list endpoint are parked for the CMD+K palette follow up.

## Current state

### Desktop command surface

`api/src/transport_matters/cli/__init__.py` registers `desktop` with `PlainCommand`, `allow_extra_args`, and `ignore_unknown_options`. The command currently accepts:

- Desktop selection: `agent`, `route`.
- Launch placement: `work_dir`, `proxy_port`, `web_port`, `storage_dir`, `home_dir`.
- Shared behavior: `debug`, `print_command`.
- Claude only behavior: `upstream`, `claude_bin`, `no_claude`, `no_system_prompt`.
- Codex only behavior: `codex_bin`, `no_codex`, `force_http_fallback`.
- Raw child passthrough via everything after `--`, parsed by `api/src/transport_matters/cli/__init__.py` symbol `_split_passthrough`.

`api/src/transport_matters/cli/help.py` symbol `_DESKTOP_HELP` documents the same surface, including passthrough examples.

`api/src/transport_matters/cli/desktop_cmd.py` symbol `prepare_desktop_launch` validates agent specific options, wraps `run_client_with_retry`, emits a backend started event, and launches Electron after the backend is ready. `build_backend_started_event` builds a route URL containing `cli` and `run_id`. `spawn_detached_electron` sets desktop environment variables, including `TRANSPORT_MATTERS_DESKTOP_CLIENT` and `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL`.

### Passthrough flow

The desktop passthrough flow is:

- `api/src/transport_matters/cli/__init__.py` symbol `desktop` calls `_split_passthrough`.
- The same symbol passes the resulting tuple as `default_client_passthrough` into `run_start` or `run_codex`.
- `api/src/transport_matters/launch_environment.py` symbol `build_launch_env` serializes this into `TRANSPORT_MATTERS_DEFAULT_CLIENT_PASSTHROUGH`.
- `api/src/transport_matters/config.py` symbol `Settings.default_client_passthrough` reads it back in the backend process.
- `api/src/transport_matters/api/v1/run_routes.py` symbol `_spawn_request` copies `settings.default_client_passthrough` into `SpawnRun.passthrough` for pane launches.
- `api/src/transport_matters/run_manager.py` symbol `RunManager._captured_request` copies that into `CapturedRunRequest.passthrough`.
- `api/src/transport_matters/captured_run_context.py` symbol `build_captured_run_context` forwards `CapturedRunRequest.passthrough` into provider invocation builders.

The public `/v1/runs` request has no raw passthrough field. The passthrough reaches panes through process settings seeded by desktop.

### Current launch paths

There are two active desktop agent launch paths.

#### Terminal style desktop launch

`api/src/transport_matters/cli/__init__.py` symbol `desktop` chooses an agent and then calls either:

- `api/src/transport_matters/cli/start_cmd.py` symbol `run_start` for Claude.
- `api/src/transport_matters/cli/codex_cmd.py` symbol `run_codex` for Codex.

That starts the selected agent outside the canvas pane path. The Electron canvas is a detached viewer pointed at the same backend.

For Claude, `run_start` builds a `CapturedRunRequest` and calls `api/src/transport_matters/captured_run.py` symbol `run_captured_run_on_local_tty`. That path uses `build_captured_run_context` and `run_client_with_retry`, then attaches the managed client to the local terminal.

For Codex, `run_codex` uses `prepare_launch`, `_prepare_codex_launch_parts`, and `run_with_workspace_manifest`. It does not go through `prepare_captured_run` or `RunManager`.

#### Electron owned backend launch

When Electron starts without `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL`, `desktop/src/main.ts` symbol `registerDesktopLifecycleFromEnv` falls through to `registerAppLifecycle`. That calls `resolveBackendStartupOptions`, then `startBackendAndCreateWindow`, then `desktop/src/backendProcess.ts` symbol `launchBackendProcess`.

`desktop/src/backendProcess.ts` symbol `buildBackendLaunch` currently executes:

- `transport-matters claude ...`, or
- `transport-matters codex ...`.

This also starts an agent through the terminal style launch command rather than through a pane run.

#### Canvas pane launch

The pane path already exists:

- `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx` symbol `CapturedRunPane` calls `ensureRun`.
- `www/src/session-canvas/model/capturedRunStore.ts` symbol `useCapturedRunStore` calls `createCapturedRun`.
- `www/src/api.ts` symbol `createCapturedRun` posts to `/v1/runs`.
- `api/src/transport_matters/api/v1/run_routes.py` symbol `create_run` validates the payload, resolves continuation and runtime template launch fields, creates a `SpawnRun`, and calls `RunManager.spawn`.
- `api/src/transport_matters/run_manager.py` symbol `RunManager._prepare_request` builds a `CapturedRunRequest`. With external web runtime it prepares the run through the shared proxy manager.
- `api/src/transport_matters/run_manager.py` symbol `RunManager._spawn_new_admitted` spawns the provider client in a PTY.
- `api/src/transport_matters/api/v1/run_routes.py` symbol `run_terminal_socket` attaches the browser terminal to that PTY.

This is the desired desktop launch path.

### Current `/v1/runs` request shape

`api/src/transport_matters/api/v1/run_routes.py` symbol `CreateRunRequest` currently exposes:

- `cli`.
- `cwd`.
- `terminal`.
- `oscColorReplies`.
- `continueFromSessionId`.
- `idempotencyKey`.
- `runtimeTemplate`.

`api/src/transport_matters/api/v1/run_routes.py` symbol `_launch_fields` builds continuation fields from `continueFromSessionId` and `idempotencyKey`.

`api/src/transport_matters/api/v1/run_routes.py` symbol `_runtime_template_ref` resolves `runtimeTemplate` through `api/src/transport_matters/runtime_registry.py` symbol `resolve_runtime_template`.

`api/src/transport_matters/captured_run_context.py` symbol `build_captured_run_context` merges request launch fields with `RuntimeHomePlan.launch_fields`, so runtime home planning remains the authority for `runtime_template` provenance.

## Target state

Desktop owns launch configuration. The user launches the desktop app, then starts Claude or Codex through captured panes. Every desktop agent launch goes through `/v1/runs`, `RunManager`, PTY, and xterm.

The desktop command has no raw child passthrough and no provider specific flag surface. Standalone `transport-matters claude` and `transport-matters codex` remain available for terminal users, proxy only diagnostics, and low level launch debugging.

Run ahead scope stops at backend and CLI cleanup. It does not add the CMD+K palette, template picker, or runtime template list endpoint.

## Proposed backend changes

### Make pane path the only desktop agent launch

Implement a server only backend launch seam for the desktop shell.

Recommended shape:

- Add an internal backend server command or helper owned by `api/src/transport_matters/cli/desktop_cmd.py`.
- The helper starts `transport_matters.main.create_app` on the selected local web port, with settings carrying the initial workspace cwd when available.
- `transport-matters desktop` launches Electron against that backend and does not call `run_start` or `run_codex`.
- Electron direct launch uses the same internal backend command instead of `transport-matters claude` or `transport-matters codex`.

Files and symbols:

- `api/src/transport_matters/cli/__init__.py` symbol `desktop`: replace the current `run_start` and `run_codex` branch with the desktop server launch path.
- `api/src/transport_matters/cli/desktop_cmd.py` symbol `prepare_desktop_launch`: replace the current retry wrapper with a server and Electron launch helper, or split Electron launch resolution into a smaller reusable helper.
- `api/src/transport_matters/cli/desktop_cmd.py` symbol `build_backend_started_event`: trim the event to backend fields: `cwd`, `workspace`, `webPort`, `baseUrl`, `routeUrl`, and `storageDir`. Drop `agent`, `proxyPort`, `runId`, and `homeDir` from the desktop boot event.
- `desktop/src/backendProcess.ts` symbol `buildBackendLaunch`: stop building `transport-matters claude` or `transport-matters codex`. Build the internal desktop backend launch instead.
- `desktop/src/main.ts` symbols `resolveBackendStartupOptions` and `startBackendAndCreateWindow`: remove client selection from backend startup options.
- `www/src/session-canvas/route.ts` symbol `parseCanvasLaunchContext`: continue allowing absent `cli` and `runId`. The launch route should not depend on an initial run.

Avoid adding bulk to `api/src/transport_matters/run_manager.py` or `api/src/transport_matters/api/v1/run_routes.py`; both are close to the project size limit. New desktop server logic should live in `desktop_cmd.py` or a small new module.

### Remove desktop passthrough and option surface

Forward removal map:

| Action | Current file and symbol | Proposed result |
| --- | --- | --- |
| Delete from desktop | `api/src/transport_matters/cli/__init__.py` symbol `desktop` raw `ctx.args` use | No call to `_split_passthrough` inside `desktop`. Extra args should be rejected by Typer. |
| Keep for standalone | `api/src/transport_matters/cli/__init__.py` symbol `_split_passthrough` | Keep only for `claude` and `codex` unless the standalone command decision changes. |
| Delete from desktop | `api/src/transport_matters/cli/__init__.py` symbol `desktop` parameters `agent`, `route`, `proxy_port`, `storage_dir`, `home_dir`, `debug`, `print_command`, provider specific flags | Desktop command takes no product launch flags. Initial workspace comes from cwd or the desktop startup UI. Ports can stay internal env or settings if needed for tests and packaging. |
| Keep for standalone | `api/src/transport_matters/cli/launch_options.py` symbols used by `claude` and `codex` | Keep terminal command options there. Remove `AgentOption` and `RouteOption` if no other caller remains. |
| Delete | `api/src/transport_matters/cli/desktop_cmd.py` symbols `_CLAUDE_ONLY_OPTIONS`, `_CODEX_ONLY_OPTIONS`, `_OPTION_LABELS`, `_reject_irrelevant_options`, `_option_supplied`, `_normalize_agent` | This cluster is already dead AS OF SLICE A (the new `prepare_desktop_launch` validates neither agent nor cross-agent options) but was deliberately deferred to Slice B since it is the same option surface. Delete the whole cluster here PLUS the now-orphaned `AgentName` import at the top of `desktop_cmd.py` — ruff will not flag it because the dead cluster keeps the import live. |
| Trim | `api/src/transport_matters/cli/desktop_cmd.py` symbol `DesktopLaunchPlan` | The plan no longer needs `agent` or a wrapped `run_client_with_retry`. Replace with a backend process or server handle if needed. |
| Trim | `api/src/transport_matters/cli/desktop_cmd.py` symbol `spawn_detached_electron` | Stop setting `TRANSPORT_MATTERS_DESKTOP_CLIENT`, `TRANSPORT_MATTERS_PROXY_PORT`, `TRANSPORT_MATTERS_RUN_ID`, and `TRANSPORT_MATTERS_AGENT_HOME_DIR` for desktop boot. Keep route URL support if using hosted viewer mode. |
| Keep | `api/src/transport_matters/env_keys.py` symbol `DEFAULT_CLIENT_PASSTHROUGH`, `api/src/transport_matters/config.py` field `Settings.default_client_passthrough`, `api/src/transport_matters/launch_environment.py` parameter `default_client_passthrough` | Keep this load bearing channel for standalone `claude` and `codex` plus shared proxy plumbing. Scope the desktop cleanup to two cuts: `desktop` stops populating it, and `_spawn_request` stops sourcing it for pane launches. |
| Trim | `api/src/transport_matters/api/v1/run_routes.py` symbol `_spawn_request` | Do not copy `settings.default_client_passthrough` into `SpawnRun.passthrough`. Pane launches should default to empty passthrough. |
| Keep internal | `api/src/transport_matters/run_manager.py` symbol `SpawnRun.passthrough` and `api/src/transport_matters/captured_run_models.py` symbol `CapturedRunRequest.passthrough` | Keep as provider invocation internals unless a broader cleanup proves there are no users. No public API should expose raw passthrough. |
| Update tests | `api/src/transport_matters/cli/test_desktop.py` | Replace tests that assert forwarding passthrough or agent flags with tests that assert rejection and no `run_start` or `run_codex` call. |
| Update tests | `desktop/src/backendProcess.test.ts` and `desktop/src/main.test.ts` | Replace client based backend launch expectations with server only launch expectations. |
| Update docs | `README.md`, `QUICKSTART.md`, `api/README.md`, `api/src/transport_matters/cli/help.py` | Remove examples that say desktop keeps the agent interactive in the terminal or uses `--agent`. |

### Keep `/v1/runs` as the launch contract

Do not add raw passthrough to `CreateRunRequest`.

Managed launch fields should remain explicit:

- `cli` selects provider.
- `runtimeTemplate` selects a runtime template by name. This field already shipped in Slice 4 and should remain as is.
- `continueFromSessionId` creates a TM internal continuation.
- `idempotencyKey` scopes continuation retry behavior.
- Future model selection should be a first class field, not a raw `--model` passthrough.

No new `runtimeTemplate` wiring is part of run ahead scope. Leave `api/src/transport_matters/api/v1/run_routes.py` symbol `CreateRunRequest` as the shipped string contract.

## Parked: template list seam builds with the UI picker

The frontend template picker still needs a read surface for templates under `~/.agent-runtimes/runtimes`, but the picker is parked with the CMD+K palette follow up. Do not build this endpoint in run ahead scope because there is no consumer until that palette ships.

Parked API shape:

```http
GET /v1/runtime-templates
```

Parked response shape:

```json
{
  "items": [
    {
      "name": "frontend",
      "clients": ["claude", "codex"],
      "description": "Frontend design and UX runtime"
    }
  ]
}
```

Parked contract:

- `name` is the exact string accepted by `CreateRunRequest.runtimeTemplate`.
- `clients` is the set of supported `CreateRunRequest.cli` values.
- `description` is optional display metadata.
- The endpoint must not return filesystem paths.
- Invalid, non directory, or escaping entries are omitted or reported through a typed diagnostic field. The first implementation can omit them and add debug logging.

Parked files and symbols:

- `api/src/transport_matters/runtime_registry.py` symbols `_registry_root`, `_validated_template_name`, and `resolve_runtime_template`: reuse these validation rules. Add `list_runtime_templates` beside them when the UI picker is built.
- `api/src/transport_matters/runtime_templates.py`: add a small immutable summary value if the API layer should avoid dicts.
- New `api/src/transport_matters/api/v1/runtime_template_routes.py`: define response models and `list_runtime_templates` route. Include it from `api/src/transport_matters/main.py` symbol `create_app` under `/v1`.
- `www/src/api.ts`: add `listRuntimeTemplates` and a `RuntimeTemplateSummary` type when the palette consumes it.
- Frontend spawn code should pass the selected summary `name` as `runtimeTemplate` on `createCapturedRun`.

Parked client target derivation:

- Prefer explicit generated metadata when agent runtimes publishes it.
- Until then, derive targets from generated files or the existing dual target convention. Existing templates are expected to support both Claude and Codex unless a target marker says otherwise.
- `runtime.toml` may be read for display metadata, but launch resolution must continue to use `resolve_runtime_template` and `RuntimeTemplateRef`. The manifest should not become a second launch authority.

## Verification requirements

CI alone is insufficient for this change. Desktop launch bugs have shipped with green tests.

Automated gates:

- `cd api && just check`
- `cd api && just test`
- `cd www && pnpm test`
- `cd desktop && pnpm test`

Focused tests to add or update:

- Desktop command rejects `--agent`, provider specific flags, and args after `--`.
- Desktop command does not call `run_start`, `run_codex`, or `run_captured_run_on_local_tty`.
- Electron backend launch no longer builds a `transport-matters claude` or `transport-matters codex` command.
- `/v1/runs` ignores any stale `TRANSPORT_MATTERS_DEFAULT_CLIENT_PASSTHROUGH` environment even though the env key remains for standalone commands and shared proxy plumbing.
- Existing `CreateRunRequest.runtimeTemplate` tests continue passing without new route or frontend wiring.

Required live smoke:

- Launch desktop from a clean shell.
- Verify no Claude or Codex process is attached to the invoking terminal as the initial desktop boot.
- Start a Claude pane from the existing desktop UI affordance, verify it attaches through xterm, and verify no native CLI resume flag appears in the child argv.
- Start a Codex pane from the existing desktop UI affordance, verify auth still comes from the ephemeral runtime home path, and verify no native CLI resume flag appears in the child argv.

## Confirmed decisions and open questions

### Standalone `transport-matters claude` and `transport-matters codex`: keep

Keep both standalone commands. They serve terminal users, proxy only diagnostics, and low level launch debugging. They are separate command contracts from desktop, and removing them would combine a desktop product cleanup with a terminal CLI product decision.

Constraint: docs must clearly separate standalone terminal commands from desktop. Raw passthrough remains a terminal command capability, not a desktop capability.

### Desktop backend process owner

Recommendation: Electron should own the backend child for packaged desktop launches. `transport-matters desktop` can be a thin opener that starts the same app path.

This avoids leaving an interactive terminal as the process owner and matches normal desktop app behavior. If keeping a foreground Python desktop command is desired for development, keep it as a developer mode rather than the product path.

### Public server command

Recommendation: keep the server only backend command internal or hidden initially.

Expose it publicly only if users need a supported headless web mode. Otherwise it becomes another launch surface to document and support.

### Initial workspace

Recommendation: use invocation cwd as the run ahead default workspace hint. Future startup screen and template picker work can override the actual run cwd through `CreateRunRequest.cwd`.

`CreateRunRequest.cwd` already accepts the explicit run cwd. The desktop boot route should not need an initial `runId` or `cli` query parameter.

### Parked template metadata authority

Recommendation for the parked picker phase: use the runtime registry as the backend authority and treat generator metadata as display metadata only.

The launch contract should stay name based. When `GET /v1/runtime-templates` is built with the UI picker, its returned `name` must be the exact string accepted by `runtimeTemplate` on `/v1/runs`.
