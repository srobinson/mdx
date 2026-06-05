---
title: Transport Matters agent home directory integration
type: research
tags: [transport-matters, agent-home-dir, codex, claude, runtime-home, pristine-template]
summary: Current agent home handling accepts arbitrary paths, mixes source homes with runtime overlays, and cannot guarantee pristine runtime templates.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive Summary

Transport Matters resolves `--agent-home-dir` to an absolute operator supplied home, records it as managed launch metadata, and maps it to `CLAUDE_CONFIG_DIR` or `CODEX_HOME` at the child boundary. Current behavior cannot guarantee pristine templates: Codex terminal launches write directly into the supplied home, and Claude or captured runs use overlays that still symlink existing source state directories.

## Project Metadata

* Language: Python backend, React and TypeScript frontend, Electron desktop.
* Build system: `api/pyproject.toml`, `just`, pytest, ruff, mypy.
* Entry point: `api/pyproject.toml` `transport-matters = transport_matters.cli:main`.
* fmm: indexed through `.fmm.db`, 758 files and 114,335 LOC.

## Architecture

The relevant launch path crosses the CLI, launch environment, overlay seed code, transcript profile code, and captured run manager.

* CLI option and path normalization: `api/src/transport_matters/cli/launch_options.py` `AgentHomeDirOption`; `api/src/transport_matters/cli/__init__.py` `_resolve_home_dir_option`.
* Environment mapping: `api/src/transport_matters/launch_environment.py` `HOME_DIR_ENV_BY_CLIENT`, `build_launch_env`, `build_managed_child_env`.
* Overlay and seeding: `api/src/transport_matters/cli/home_seed.py` `prepare_runtime_home_overlay`, `seed_home_dir`, `ClaudeSeeder.seed`, `CodexSeeder.seed`.
* Transcript roots: `api/src/transport_matters/cli/home_seed.py` `claude_projects_root`, `codex_sessions_root`; `api/src/transport_matters/cli/launch_profile.py` `ClaudeLaunchProfile.prepare`, `CodexLaunchProfile.prepare`.
* Captured pane path: `api/src/transport_matters/captured_run_context.py` `build_captured_run_context`; `api/src/transport_matters/run_manager.py` `RunManager._captured_request`.

## Key Patterns

* CLI `--agent-home-dir` uses `expanduser().resolve()` and creates the directory except for dry `--print-command` runs.
* Claude terminal launches run the child from `<run storage>/runtime-home/claude`, not directly from the supplied home. The supplied home remains the recorded transcript root.
* Codex terminal launches run the child directly with `CODEX_HOME=<supplied home>`.
* Captured panes create an overlay for both clients, but managed session preparation still computes descriptor and rollout roots from the supplied home.
* Overlay construction broadly symlinks existing source entries except local control files. That preserves state fidelity but violates a pristine template constraint when existing mutable dirs are present.

## Detailed Findings

### Resolution and env vars

`api/src/transport_matters/cli/__init__.py` `_resolve_home_dir_option` resolves the CLI path to an absolute path before child cwd changes. `api/src/transport_matters/cli/home_seed.py` `resolve_source_home_dir` falls back to `$CLAUDE_CONFIG_DIR` or `~/.claude` for Claude and `$CODEX_HOME` or `~/.codex` for Codex. `api/src/transport_matters/launch_environment.py` `build_managed_child_env` sets `CLAUDE_CONFIG_DIR` for Claude and `CODEX_HOME` for Codex.

There is no hardcoded `~/.agent-runtimes` root in Transport Matters. Callers choose the path.

### Writes with an explicit home

For Claude, `api/src/transport_matters/captured_run_context.py` `build_captured_run_context` builds a per-run overlay. `api/src/transport_matters/cli/home_seed.py` `ClaudeSeeder.seed` writes `.claude.json` in the overlay with account metadata, onboarding, and cwd trust. `api/src/transport_matters/cli/home_seed.py` `apply_claude_proxy_env_settings` writes proxy env into overlay `settings.json`. Existing source `projects/` is symlinked by `api/src/transport_matters/cli/home_seed.py` `_symlink_source_home_entries`, so child transcript writes can hit the source template when that directory already exists.

For Codex terminal launches, `api/src/transport_matters/cli/codex_cmd.py` `build_codex_invocation` sets `CODEX_HOME` to the supplied home. `api/src/transport_matters/cli/home_seed.py` `CodexSeeder.seed` copies `auth.json` if missing and updates `config.toml` cwd trust. `api/src/transport_matters/cli/launch_profile.py` `CodexLaunchProfile.prepare` and `api/src/transport_matters/cli/codex_session.py` `seed_codex_session` write the pre-seeded rollout under `<home>/sessions/...`.

The claim that Transport Matters only writes `projects/` or `sessions/` when no `--agent-home-dir` is supplied is refuted. With an explicit home, Codex writes `sessions/`, Claude descriptors target `projects/`, and existing Claude `projects/` is symlinked into the overlay.

### Auth and trust path keys

Claude auth metadata is read and copied from `.claude.json` fields `userID` and `oauthAccount`; project trust is keyed by absolute cwd in `.claude.json` `projects`. Codex auth is `auth.json`; project trust is keyed by absolute cwd in `config.toml` `projects`. Codex hook trust is path sensitive because `api/src/transport_matters/cli/home_seed.py` `_relocate_codex_hook_trust_state` rewrites `[hooks.state."<absolute hooks path>"]` keys from source home to overlay home.

Transport Matters has no `.credentials.json` handling in the inspected code.

### Moving homes to `~/.agent-runtimes/runtimes/<name>`

New launches should work if the caller passes the new path. Existing durable facts and session rows can preserve old absolute paths in `Manifest.home_dir`, `OwnedSessionFacts.home_dir`, `FileTailSource.path`, `FileTailSource.home_dir`, and `SessionRow.home_dir`. Codex hook trust keys may remain tied to the old home path unless rewritten.

### Pristine template seam

Current code cannot launch from a pristine template without mutation risk. The clean fix is to split template source from writable instance home at `api/src/transport_matters/cli/home_seed.py` `prepare_runtime_home_overlay` and carry the instance home through `api/src/transport_matters/launch_environment.py` `build_managed_child_env`, `build_launch_env`, and `api/src/transport_matters/cli/launch_profile.py` `prepare_managed_session`. Child env vars, transcript descriptors, Codex rollout seeding, and addon `TRANSPORT_MATTERS_AGENT_HOME_DIR` should point at the instance home. Template contents should be copied or symlinked only from a read only allowlist, never for `projects`, `sessions`, history, daemon state, jobs, logs, caches, lockfiles, SQLite files, or any child mutable state.

## Dependencies

Critical dependencies in this path are Typer for CLI options, Pydantic settings for `TRANSPORT_MATTERS_AGENT_HOME_DIR`, mitmproxy for capture, and pytest for regression coverage.

## Relevance to Helioy

This directly affects `skill-matters` generated runtimes under `~/.agent-runtimes/<name>` or a future `~/.agent-runtimes/runtimes/<name>`. Transport Matters needs a writable instance home per launch before those runtimes can be treated as immutable templates.

## Open Questions

* Whether instance homes should live under Transport Matters run storage or under a new `~/.agent-runtimes/instances/` namespace.
* How long instance homes must persist after run exit so transcript tailing and snapshots remain reliable.
* Whether Codex hook trust should be regenerated from hooks content or migrated from known prior home roots.

## Verification

* `cd api && .venv/bin/python -m pytest src/transport_matters/cli/test_home_seed.py src/transport_matters/cli/test_start_storage.py src/transport_matters/cli/test_codex.py src/transport_matters/test_captured_run_web_separation.py -q`: 61 passed.
* `cd api && .venv/bin/python -m pytest src/transport_matters/cli/test_start_mint.py src/transport_matters/cli/test_codex_session.py src/transport_matters/cli/test_launch_profile.py -q`: 29 passed.
* Probe against live code confirmed absent Claude source `projects/` produces no overlay symlink, existing source `projects/` is symlinked, and captured Codex source `sessions/` can be created after overlay creation with no overlay symlink.
