---
title: Desktop cleanup backend analysis for Transport Matters
type: research
tags: [transport-matters, desktop, backend, captured-run, runtime-templates]
summary: Backend run ahead spec analysis for making desktop launches use only the RunManager pane path while parking UI template picker work.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Executive Summary

Transport Matters currently has two desktop launch paths that start Claude or Codex outside the pane path. The run ahead cleanup should make `/v1/runs` plus `RunManager` the only desktop agent launch path and delete the desktop raw passthrough surface. The template picker UI and template list endpoint are parked for the CMD+K palette follow up.

## Project Metadata

- Language: Python 3.14 backend, TypeScript React frontend, Electron desktop shell.
- Backend framework: FastAPI, Typer, Pydantic settings, uvicorn, mitmproxy, psycopg.
- Frontend and desktop tooling: Node 24.16.0, pnpm 11.6.0, React, Zustand, Electron.
- Build system: `api/pyproject.toml` with Hatch and uv. Root justfile coordinates backend, frontend, and desktop gates.
- Index signal: `.fmm.db` exists in the repo root and fmm returned current file topology.

## Architecture

- CLI entrypoint: `api/src/transport_matters/cli/__init__.py` registers `claude`, `codex`, and `desktop`. The `desktop` function currently branches into `run_start` or `run_codex` after parsing passthrough from `ctx.args`.
- Desktop helper: `api/src/transport_matters/cli/desktop_cmd.py` owns Electron resolution, option validation, backend started event construction, and detached Electron spawning.
- Local terminal launch path: `api/src/transport_matters/cli/start_cmd.py:run_start` calls `captured_run.py:run_captured_run_on_local_tty`. `api/src/transport_matters/cli/codex_cmd.py:run_codex` has its own local launch flow through `prepare_launch` and `_prepare_codex_launch_parts`.
- Pane launch path: `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx:CapturedRunPane` calls `useCapturedRunStore.ensureRun`, which calls `www/src/api.ts:createCapturedRun`. Backend `api/v1/run_routes.py:create_run` builds a `SpawnRun`; `run_manager.py:RunManager._spawn_new_admitted` spawns the provider CLI in a PTY and `run_routes.py:run_terminal_socket` attaches xterm.
- Runtime templates: `api/src/transport_matters/runtime_registry.py:resolve_runtime_template` resolves names under `~/.agent-runtimes/runtimes`; there is no list endpoint yet, and that endpoint is parked until the UI picker ships.

## Key Patterns

- The B6 `/v1` run API is already the curated product seam for run lifecycle. It exposes `CreateRunRequest` with `cli`, `cwd`, `terminal`, `oscColorReplies`, `continueFromSessionId`, `idempotencyKey`, and the already shipped `runtimeTemplate` string field.
- Runtime template launch should flow through `RuntimeHomePlan.launch_fields`, not a raw launch field. `captured_run_context.py:build_captured_run_context` merges request launch fields with runtime home launch fields, with runtime home fields winning.
- Desktop should not grow `run_routes.py` or `run_manager.py`; those files are 646 and 684 LOC respectively. A new runtime template route module avoids crossing the project LOC threshold.

## Detailed Findings

### Verified anchors

- `api/src/transport_matters/cli/__init__.py:372-441` registers the current `desktop` command, parses raw passthrough, and branches to `run_start` or `run_codex`.
- `api/src/transport_matters/cli/desktop_cmd.py:73-121` wraps `run_client_with_retry` and launches Electron after backend readiness.
- `api/src/transport_matters/cli/desktop_cmd.py:124-160` builds the current desktop route event with `agent`, `runId`, and `proxyPort`.
- `api/src/transport_matters/cli/start_cmd.py:37-103` implements the Claude terminal launch used by desktop.
- `api/src/transport_matters/cli/codex_cmd.py:540-670` implements the Codex terminal launch used by desktop.
- `desktop/src/backendProcess.ts:66-90` builds the Electron owned backend command as `transport-matters claude` or `transport-matters codex`.
- `api/src/transport_matters/api/v1/run_routes.py:92-102` defines the current `CreateRunRequest`.
- `api/src/transport_matters/api/v1/run_routes.py:341-361` copies settings passthrough into pane spawn requests.
- `api/src/transport_matters/run_manager.py:487-506` maps `SpawnRun` to `CapturedRunRequest`.
- `api/src/transport_matters/runtime_registry.py:18-45` resolves runtime template names under `~/.agent-runtimes/runtimes`.

### Current desktop passthrough

`api/src/transport_matters/cli/__init__.py:desktop` calls `_split_passthrough(ctx)` and stores the result in `shared_launch_kwargs.default_client_passthrough`. It also passes the same passthrough as `claude_passthrough` or `codex_passthrough` to the selected local launch command.

`api/src/transport_matters/launch_environment.py:build_launch_env` serializes default passthrough to `TRANSPORT_MATTERS_DEFAULT_CLIENT_PASSTHROUGH`. `api/src/transport_matters/config.py:Settings.default_client_passthrough` reads it back. `api/src/transport_matters/api/v1/run_routes.py:_spawn_request` copies that setting into `SpawnRun.passthrough`, so later pane launches inherit desktop raw args even though `/v1/runs` has no public passthrough field.

### Current desktop launch paths

`api/src/transport_matters/cli/__init__.py:desktop` currently calls `run_start` or `run_codex`. This creates an agent outside the canvas pane path. `api/src/transport_matters/cli/desktop_cmd.py:prepare_desktop_launch` only wraps the backend ready hook so Electron opens as a detached viewer.

Electron direct launch also starts an agent outside the pane path. `desktop/src/main.ts:registerAppLifecycle` calls `startBackendAndCreateWindow`, which calls `desktop/src/backendProcess.ts:launchBackendProcess`; `buildBackendLaunch` builds `transport-matters claude` or `transport-matters codex` with pinned ports.

### Desired backend shape

Desktop needs a server only backend launch seam. Both Python `transport-matters desktop` and Electron direct launch should start the FastAPI app without spawning a provider CLI. All provider launches should originate from the UI through `POST /v1/runs`.

`api/src/transport_matters/cli/desktop_cmd.py:build_backend_started_event` should no longer require `agent`, `runId`, or `proxyPort` because desktop boot will not have an initial run.

### Parked template list seam

`api/src/transport_matters/runtime_registry.py` currently resolves a name but cannot enumerate names. Do not add `list_runtime_templates` or `/v1/runtime-templates` in run ahead scope. Build that endpoint with the parked CMD+K palette and template picker consumer.

## Dependencies

- FastAPI and Pydantic provide the `/v1` route and response model surface.
- Typer owns the CLI surface that needs narrowing for desktop.
- Electron main process owns packaged app backend child process launch.
- Zustand stores coordinate canvas and captured run pane lifecycle.
- `.agent-runtimes` provides template homes under `~/.agent-runtimes/runtimes`; enumeration waits for the parked UI picker.

## Relevance to Helioy

This cleanup moves Transport Matters toward the Helioy launcher model where TM owns explicit launch configuration. It removes a hidden raw args channel from desktop and aligns desktop launch with the B6 `/v1` product API seam while avoiding premature UI endpoint work.

## Open Questions

- Whether `transport-matters desktop` should be a thin opener that exits or a foreground development command.
- Whether the server only backend command should be public or hidden.
- Standalone `transport-matters claude` and `transport-matters codex` are confirmed keep for terminal users and diagnostics while removing desktop dependency on them.
- Template list and metadata authority remain parked with the UI picker.
