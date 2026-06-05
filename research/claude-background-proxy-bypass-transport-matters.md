---
title: Claude background worker proxy bypass in Transport Matters
type: research
tags: [transport-matters, claude, proxy, captured-runs, managed-home]
summary: Canvas spawned Claude panes can bypass capture when global Claude daemon background workers drop ANTHROPIC_BASE_URL; default managed homes are the recommended guardrail.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

## Executive Summary

A canvas spawned Claude pane can lose wire capture when Claude dispatches a slash sourced background worker through the global `~/.claude` daemon. The observed worker kept `TRANSPORT_MATTERS_RUN_ID` but lacked `ANTHROPIC_BASE_URL`, so the native transcript advanced while Transport Matters stopped seeing provider traffic.

## Project Metadata

- Project: `transport-matters`
- Language: Python 3.14 backend, TypeScript React frontend, Electron desktop
- Backend framework: FastAPI, mitmproxy, Pydantic, Typer, psycopg, Alembic
- Build system: `uv` with Hatchling in `api/pyproject.toml`
- Quality gate: `cd api && just ci`; frontend gate only if the TypeScript API shape changes
- fmm status: `.fmm.db` exists at repo root and under `api/` and `www/`

## Architecture

Canvas run spawning enters FastAPI in `api/src/transport_matters/api/v1/run_routes.py`. `CreateRunRequest` only accepts `cli`, `cwd`, terminal size, and OSC color behavior at lines 68 to 75. `_spawn_request()` maps that request to `SpawnRun` and currently sets `home_dir=settings.agent_home_dir` at lines 220 to 231.

The run manager then carries the value through unchanged. `RunManager._captured_request()` maps `SpawnRun.home_dir` to `CapturedRunRequest.home_dir` at `api/src/transport_matters/run_manager.py:397-416`. `build_captured_run_context()` passes the value into managed session preparation and Claude invocation construction at `api/src/transport_matters/captured_run_context.py:88-121`.

Claude invocation building is split cleanly. `build_claude_captured_invocation()` always sets `ANTHROPIC_BASE_URL` for the primary child at `api/src/transport_matters/captured_claude.py:98-103`. `build_managed_child_env()` only sets `CLAUDE_CONFIG_DIR` when `home_dir` is non null at `api/src/transport_matters/launch_environment.py:187-197`; the client to home env map is `CLAUDE_CONFIG_DIR` for Claude and `CODEX_HOME` for Codex at lines 89 to 92.

## Key Patterns

- Managed home is already the repo's canonical abstraction for agent config and transcript roots. `build_launch_env()` records it for the addon as `TRANSPORT_MATTERS_AGENT_HOME_DIR` at `api/src/transport_matters/launch_environment.py:121-137`.
- `seed_home_dir()` is the existing DRY seeding seam at `api/src/transport_matters/cli/home_seed.py:106-122`. `ClaudeSeeder.seed()` copies required auth fields when missing, records cwd trust, marks onboarding complete, and writes the dangerous mode prompt setting at lines 56 to 76.
- Direct CLI `transport-matters claude --agent-home-dir` already seeds before launch in `api/src/transport_matters/captured_run.py:118-123`. The RunManager path used by canvas captured panes does not yet call this seeder.

## Detailed Findings

### Root cause model

`NOTES/claude-daemon-fork-bypasses-proxy.md` records that the original captured Claude process and its daemon supervisor had `ANTHROPIC_BASE_URL=http://127.0.0.1:57169` plus `TRANSPORT_MATTERS_RUN_ID=a1144e58-538d-432a-bacb-f037296ca766`. The background PTY host and worker retained the run id and `CLAUDE_BG_ISOLATION=none`, but did not have `ANTHROPIC_BASE_URL`.

The likely loss point is Claude's internal daemon dispatch payload, not Transport Matters initial launch. Transport Matters correctly proxied the primary child, but the background worker used a rebuilt environment and bypassed the reverse proxy.

### Recommended fix

Default canvas spawned Claude runs to a managed home when no explicit server `agent_home_dir` exists. The recommended path is:

```text
<default_storage_root>/agent-homes/<workspace_slug>/<workspace_hash>/claude
```

Use `workspace_id(cwd)` from `api/src/transport_matters/workspace.py:58-68` and `default_storage_root()` from `api/src/transport_matters/storage_roots.py:12-24`; do not duplicate workspace slug or hash logic. Keep the generated home outside `workspaces/` so run directory enumeration remains clean.

Add a small resolver, for example `api/src/transport_matters/canvas_agent_home.py`, and call it from `_spawn_request()` after cwd resolution. For Claude, return the configured home if present, otherwise the generated home. For Codex, preserve the current default of `None` unless configured.

Seed the resolved home inside `prepare_captured_run()` before the workspace lock and proxy start. Keep this at the captured run seam rather than in FastAPI routes. The seeder is already idempotent and client keyed.

### Acceptance tests

- Add route tests proving configured home wins, Claude without configured home gets the generated home, Codex stays native by default, and `web_runtime=external` plus `web_port=None` remain unchanged.
- Extend the external web runtime Claude test to assert `ANTHROPIC_BASE_URL`, `CLAUDE_CONFIG_DIR`, `TRANSPORT_MATTERS_AGENT_HOME_DIR`, no nested web port, and seeded home files.
- Run `cd api && just ci`. Run frontend gates only if a TypeScript API shape changes.
- Manual smoke is still required because the bug depends on Claude's daemon internals.

## Dependencies

Critical dependencies for this slice are FastAPI for run routes, mitmproxy for capture, Typer for CLI launch, and the existing home seeding helpers in `api/src/transport_matters/cli/home_seed.py`.

## Relevance to Helioy

This directly affects Helioy canvas captured agents. Without the fix, an operator can believe a Claude pane is captured because the run id remains in the process tree, while provider traffic has already escaped the reverse proxy.

## Open Questions

- Will Claude still create a managed home background worker and drop `ANTHROPIC_BASE_URL` under future daemon behavior?
- Should `transport-matters doctor` add an exact allow listed process env check for Claude processes carrying `TRANSPORT_MATTERS_RUN_ID` without `ANTHROPIC_BASE_URL`?
- Should Codex receive a separate generated home policy later, or stay native by default because its capture uses explicit proxy variables and a CA bundle?
