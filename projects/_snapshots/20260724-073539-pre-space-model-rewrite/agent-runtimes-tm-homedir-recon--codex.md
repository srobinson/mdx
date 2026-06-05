# Agent runtime home directory recon for transport-matters

Date: 2026-06-15
Role: Codex pane
Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
Confidence: high for Transport Matters code paths; medium for exact upstream Claude and Codex private cache names because those are only inferred from child home selection.

## Executive summary

`--agent-home-dir` is accepted as an arbitrary operator supplied home. Transport Matters resolves it to an absolute path in the CLI, records it as managed launch metadata, and maps it to `CLAUDE_CONFIG_DIR` or `CODEX_HOME` at the child boundary. Current behavior does not satisfy a pristine template constraint. Codex terminal launches write directly into the supplied home, while Claude and captured runs use a per-run overlay but still symlink existing state directories from the supplied home and record transcript descriptors under the supplied home.

The single most important finding: pristine templates require a stronger split between template source and writable instance home. The clean seam is already close to `prepare_runtime_home_overlay`, `build_captured_run_context`, `build_managed_child_env`, and `prepare_managed_session`, but writable transcript roots and trust writes must move to the instance home, not the supplied template.

## Project metadata

* Language: Python backend, React and TypeScript frontend, Electron desktop.
* Build and test system: `api/pyproject.toml`, `just`, pytest, ruff, mypy.
* Runtime entry point: `transport-matters = transport_matters.cli:main` in `api/pyproject.toml`.
* fmm status: `.fmm.db` exists in the checkout and fmm indexed 758 files, 114,335 LOC.
* Architecture docs read: `PROJECT.md`, `README.md`, `api/pyproject.toml`, `LESSONS.md`.

## Evidence map

* CLI option definition: `api/src/transport_matters/cli/launch_options.py` `AgentHomeDirOption`.
* CLI path normalization: `api/src/transport_matters/cli/__init__.py` `_resolve_home_dir_option`.
* CLI command plumbing: `api/src/transport_matters/cli/__init__.py` `claude`, `codex`, `desktop`.
* Claude launch path: `api/src/transport_matters/cli/start_cmd.py` `run_start`, `api/src/transport_matters/captured_run.py` `run_captured_run_on_local_tty`, `api/src/transport_matters/captured_run_context.py` `build_captured_run_context`, `api/src/transport_matters/captured_claude.py` `build_claude_captured_invocation`.
* Codex terminal launch path: `api/src/transport_matters/cli/codex_cmd.py` `run_codex`, `build_codex_invocation`.
* Captured pane launch path: `api/src/transport_matters/run_manager.py` `RunManager._captured_request`, `api/src/transport_matters/api/v1/run_routes.py` `_spawn_request`.
* Child env mapping: `api/src/transport_matters/launch_environment.py` `HOME_DIR_ENV_BY_CLIENT`, `build_launch_env`, `build_managed_child_env`.
* Home seeding and overlay: `api/src/transport_matters/cli/home_seed.py` `resolve_source_home_dir`, `prepare_runtime_home_overlay`, `seed_home_dir`, `ClaudeSeeder.seed`, `CodexSeeder.seed`, `_symlink_source_home_entries`, `_copy_overlay_local_files`, `apply_claude_proxy_env_settings`.
* Transcript roots: `api/src/transport_matters/cli/home_seed.py` `claude_projects_root`, `codex_sessions_root`; `api/src/transport_matters/cli/launch_profile.py` `ClaudeLaunchProfile.prepare`, `CodexLaunchProfile.prepare`; `api/src/transport_matters/cli/codex_session.py` `seed_codex_session`.
* Persisted absolute home metadata: `api/src/transport_matters/launch_manifest.py` `write_workspace_manifest`; `api/src/transport_matters/cli/launch_profile.py` `persist_owned_session_facts`; `api/src/transport_matters/session/models.py` `SessionRow`; `api/src/transport_matters/index/adapters/base.py` `FileTailSource`.
* Trust and auth state: `api/src/transport_matters/cli/home_seed.py` `_ensure_claude_trust`, `_ensure_claude_skip_dangerous_prompt`, `_copy_secret_file_if_missing`, `_merge_codex_project_trust`, `_relocate_codex_hook_trust_state`.

## 1. How `--agent-home-dir` resolves

### CLI path handling

`AgentHomeDirOption` is a Typer `Path | None` option named `--agent-home-dir`, with `file_okay=False`, `dir_okay=True`, and `resolve_path=False` (`api/src/transport_matters/cli/launch_options.py` `AgentHomeDirOption`). The CLI resolves it once via `_resolve_home_dir_option`: `expanduser().resolve()`, then `mkdir(parents=True, exist_ok=True)` unless the launch is a dry `--print-command` run (`api/src/transport_matters/cli/__init__.py` `_resolve_home_dir_option`).

The option is passed into `run_start` for Claude, `run_codex` for Codex, and shared desktop launch kwargs for `transport-matters desktop` (`api/src/transport_matters/cli/__init__.py` `claude`, `codex`, `desktop`). There is no hardcoded `~/.agent-runtimes` root and no built in runtime name lookup in Transport Matters. The flag value is just a path.

### Native default resolution

When no explicit home is supplied, `resolve_source_home_dir` chooses the client native home. Claude uses `$CLAUDE_CONFIG_DIR` or `~/.claude`; Codex uses `$CODEX_HOME` or `~/.codex` (`api/src/transport_matters/cli/home_seed.py` `resolve_source_home_dir`, `_default_claude_home`, `_default_codex_home`).

`claude_projects_root` maps a managed home to `<home>/projects`; `codex_sessions_root` maps a managed home to `<home>/sessions` (`api/src/transport_matters/cli/home_seed.py` `claude_projects_root`, `codex_sessions_root`).

### Child environment variables

`build_managed_child_env` maps a non null home to `CLAUDE_CONFIG_DIR` for Claude and `CODEX_HOME` for Codex via `HOME_DIR_ENV_BY_CLIENT` (`api/src/transport_matters/launch_environment.py` `HOME_DIR_ENV_BY_CLIENT`, `build_managed_child_env`). The addon receives the managed home through `TRANSPORT_MATTERS_AGENT_HOME_DIR` in `build_launch_env`, so transcript binding uses the same managed home metadata (`api/src/transport_matters/launch_environment.py` `build_launch_env`).

Current launch paths differ:

* `transport-matters claude`: child `CLAUDE_CONFIG_DIR` is the per-run overlay under `<run storage>/runtime-home/claude`, while `TRANSPORT_MATTERS_AGENT_HOME_DIR` and manifest/session facts record the operator supplied source home (`api/src/transport_matters/captured_run_context.py` `build_captured_run_context`; `api/src/transport_matters/captured_claude.py` `build_claude_captured_invocation`).
* `transport-matters codex`: child `CODEX_HOME` is the supplied `--agent-home-dir` directly (`api/src/transport_matters/cli/codex_cmd.py` `build_codex_invocation`).
* Canvas `/runs` captured panes: `RunManager._captured_request` carries `SpawnRun.home_dir`; `build_captured_run_context` creates an overlay for any client with a client path; child env points to the overlay, while launch metadata records the source home (`api/src/transport_matters/run_manager.py` `RunManager._captured_request`; `api/src/transport_matters/captured_run_context.py` `build_captured_run_context`).

## 2. What is written with `--agent-home-dir`

### Claude terminal and desktop Claude

`transport-matters claude --agent-home-dir <home>` creates `<home>` unless `--print-command` is used (`api/src/transport_matters/cli/__init__.py` `_resolve_home_dir_option`; test: `api/src/transport_matters/cli/test_start_storage.py` `test_start_print_command_home_dir_does_not_create_dir`).

The child does not run directly from `<home>`. `build_captured_run_context` calls `prepare_runtime_home_overlay`, placing the runtime home under `<run storage>/runtime-home/claude` (`api/src/transport_matters/captured_run_context.py` `build_captured_run_context`). `prepare_runtime_home_overlay` does three important things (`api/src/transport_matters/cli/home_seed.py` `prepare_runtime_home_overlay`):

* Symlinks existing source home entries into the runtime home, except local control names and `.git` (`api/src/transport_matters/cli/home_seed.py` `_symlink_source_home_entries`, `_overlay_local_names`).
* Copies local files `.claude.json` and `settings.json` into the runtime home (`api/src/transport_matters/cli/home_seed.py` `_copy_overlay_local_files`).
* Seeds the runtime copy of `.claude.json` and `settings.json` (`api/src/transport_matters/cli/home_seed.py` `ClaudeSeeder.seed`, `_ensure_claude_trust`, `_ensure_claude_skip_dangerous_prompt`).

Explicit Transport Matters writes for Claude land in the runtime overlay:

* `<overlay>/.claude.json`: merges `userID`, `oauthAccount`, sets `hasCompletedOnboarding`, and writes `projects[<absolute cwd>].hasTrustDialogAccepted = True` (`api/src/transport_matters/cli/home_seed.py` `ClaudeSeeder.seed`, `_ensure_claude_trust`).
* `<overlay>/settings.json`: sets `skipDangerousModePermissionPrompt = true` and, during invocation build, writes `env.ANTHROPIC_BASE_URL`, `env.TRANSPORT_MATTERS_RUN_ID`, `env.TRANSPORT_MATTERS_AGENT_HOME_DIR = <overlay>`, and `env.NO_PROXY` (`api/src/transport_matters/cli/home_seed.py` `_ensure_claude_skip_dangerous_prompt`, `apply_claude_proxy_env_settings`).
* `<run dir>/sessions.json`: durable owned session facts, including source descriptor and `home_dir` equal to the supplied source home (`api/src/transport_matters/cli/launch_profile.py` `persist_owned_session_facts`; `api/src/transport_matters/storage/session_facts.py` `write_owned_session_facts`).
* `<run dir>/manifest.json`: live manifest while running, with `home_dir` equal to the source home (`api/src/transport_matters/launch_manifest.py` `write_workspace_manifest`).

Source home mutation is conditional and indirect:

* Existing `projects/` in the source home is symlinked into the overlay. Claude transcript writes then hit the source home (`api/src/transport_matters/cli/home_seed.py` `_symlink_source_home_entries`; test: `api/src/transport_matters/cli/test_home_seed.py` `test_claude_runtime_overlay_symlinks_state_and_keeps_control_files_local`).
* Existing read mostly or state directories such as `skills/` are also symlinked. Any child write through those symlinks mutates the source home.
* `daemon`, `daemon.lock`, `daemon.log`, `daemon.status.json`, and `jobs` are excluded from symlinking so daemon control and dispatch state stays local to the overlay (`api/src/transport_matters/cli/home_seed.py` `_CLAUDE_DAEMON_LOCAL_NAMES`, `_assert_overlay_daemon_is_local`).
* `.claude.json` and `settings.json` source files are copied into the overlay and source copies are not mutated by this seeding path (tests: `api/src/transport_matters/cli/test_home_seed.py` `test_claude_launch_runs_from_overlay_seeded_from_agent_home_dir`, `test_apply_claude_proxy_env_settings_updates_overlay_only`).

A probe against the live code found a gap for pristine or empty templates: if `<home>/projects` does not exist before overlay creation, the overlay has no `projects` symlink. A child that creates `<overlay>/projects` writes into the overlay, which `CapturedRunContext.resource_stack` later removes. The owned descriptor still points at `<home>/projects` because `ClaudeLaunchProfile.prepare` used `home_dir=<home>` (`api/src/transport_matters/cli/launch_profile.py` `ClaudeLaunchProfile.prepare`; `api/src/transport_matters/captured_run_context.py` `build_captured_run_context`).

### Codex terminal and desktop Codex

`transport-matters codex --agent-home-dir <home>` launches the child with `CODEX_HOME=<home>` directly (`api/src/transport_matters/cli/codex_cmd.py` `build_codex_invocation`; test: `api/src/transport_matters/cli/test_codex.py` `test_codex_home_dir_sets_codex_home_manifest_and_keeps_ca`).

Transport Matters writes into the supplied home before the child starts:

* `<home>/auth.json`: copied from the source Codex home if missing (`api/src/transport_matters/cli/home_seed.py` `CodexSeeder.seed`, `_copy_secret_file_if_missing`).
* `<home>/config.toml`: updated with `[projects."<absolute cwd>"] trust_level = "trusted"` (`api/src/transport_matters/cli/home_seed.py` `CodexSeeder.seed`, `_merge_codex_project_trust`, `_write_project_trust`, `_codex_project_header`).
* `<home>/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl`: pre-seeded minimal `session_meta` rollout for `codex resume <uuid>` (`api/src/transport_matters/cli/launch_profile.py` `CodexLaunchProfile.prepare`; `api/src/transport_matters/cli/codex_session.py` `seed_codex_session`, `codex_rollout_path`).
* `<run dir>/sessions.json`: durable owned facts, with `home_dir=<home>` (`api/src/transport_matters/cli/launch_profile.py` `persist_owned_session_facts`).
* `<run dir>/manifest.json`: live manifest while running, with `home_dir=<home>` (`api/src/transport_matters/launch_manifest.py` `write_workspace_manifest`).

Because child `CODEX_HOME` is the supplied home, any Codex child history, sessions, logs, caches, lockfiles, and other Codex home writes go into the supplied home. Transport Matters code only names `auth.json`, `config.toml`, and `sessions/`; it has no explicit handling for `.credentials.json`, and repository text search found no `.credentials.json` support.

### Canvas captured Codex panes

Captured panes created through `/runs` use `build_captured_run_context`, so child `CODEX_HOME` points to `<run storage>/runtime-home/codex` (`api/src/transport_matters/captured_run_context.py` `build_captured_run_context`; `api/src/transport_matters/cli/codex_cmd.py` `build_codex_invocation`). The runtime overlay copies `auth.json` and `config.toml`, symlinks other existing source entries, and rewrites copied Codex hook trust keys to the overlay path (`api/src/transport_matters/cli/home_seed.py` `prepare_runtime_home_overlay`, `_copy_overlay_local_files`, `_relocate_codex_hook_trust_state`; tests: `api/src/transport_matters/cli/test_home_seed.py` `test_codex_runtime_overlay_copies_auth_config_and_symlinks_state`, `test_codex_overlay_repoints_hook_trust_state_to_overlay_home`).

However, `prepare_managed_session` still receives `home_dir=request.home_dir`, so `CodexLaunchProfile.prepare` pre-seeds the owned rollout under the source home `<home>/sessions`, not under the overlay (`api/src/transport_matters/captured_run_context.py` `build_captured_run_context`; `api/src/transport_matters/cli/launch_profile.py` `CodexLaunchProfile.prepare`). If `<home>/sessions` was not present during overlay symlink creation, the overlay cannot see the newly created source rollout. The live probe confirmed that sequence.

### Claim check: `tm only writes projects//sessions/ if NO --agent-home-dir is specified`

Refuted.

With `--agent-home-dir` set:

* Codex terminal launches write the pre-seeded rollout to `<home>/sessions/...` before launch (`api/src/transport_matters/cli/launch_profile.py` `CodexLaunchProfile.prepare`; `api/src/transport_matters/cli/codex_session.py` `seed_codex_session`).
* Captured Codex panes also pre-seed `<home>/sessions/...` because `prepare_managed_session` receives `request.home_dir` (`api/src/transport_matters/captured_run_context.py` `build_captured_run_context`).
* Claude managed descriptors point at `<home>/projects/...` when `--agent-home-dir` is set (`api/src/transport_matters/cli/launch_profile.py` `ClaudeLaunchProfile.prepare`; test: `api/src/transport_matters/cli/test_start_mint.py` `test_claude_managed_mint_writes_durable_session_facts_under_home_dir`). If `<home>/projects` exists, the overlay symlink makes actual child transcript writes land there (`api/src/transport_matters/cli/home_seed.py` `_symlink_source_home_entries`; test: `api/src/transport_matters/cli/test_home_seed.py` `test_claude_runtime_overlay_symlinks_state_and_keeps_control_files_local`).

With no `--agent-home-dir`, native defaults are used: Claude source is `$CLAUDE_CONFIG_DIR` or `~/.claude`, Codex session root is `$CODEX_HOME/sessions` or `~/.codex/sessions` (`api/src/transport_matters/cli/home_seed.py` `_default_claude_home`, `_default_codex_home`, `claude_projects_root`, `codex_sessions_root`).

## 3. Auth and trust path keys

### Claude

Transport Matters reads Claude account metadata from `.claude.json`, specifically `userID` and `oauthAccount`, and writes those fields into the target `.claude.json` if missing (`api/src/transport_matters/cli/home_seed.py` `ClaudeSeeder.seed`). It writes cwd trust at `.claude.json` key `projects[<absolute cwd>].hasTrustDialogAccepted = True` (`api/src/transport_matters/cli/home_seed.py` `_ensure_claude_trust`). It writes dangerous mode prompt suppression into `settings.json` (`api/src/transport_matters/cli/home_seed.py` `_ensure_claude_skip_dangerous_prompt`).

In the Transport Matters code, Claude project trust is keyed by absolute cwd, not by home path. Claude auth metadata is stored in `.claude.json`; no Transport Matters code path references `.credentials.json` or a keychain. If Claude Code has additional private auth stores, they are outside this codebase's observed handling.

### Codex

Transport Matters copies `auth.json` into the target home if missing (`api/src/transport_matters/cli/home_seed.py` `CodexSeeder.seed`, `_copy_secret_file_if_missing`). Codex project trust is written into `config.toml` under `[projects."<absolute cwd>"] trust_level = "trusted"` (`api/src/transport_matters/cli/home_seed.py` `_merge_codex_project_trust`, `_write_project_trust`, `_codex_project_header`).

Codex hook trust is home path sensitive. `_relocate_codex_hook_trust_state` says Codex hook state keys trust by the absolute path of the hooks file loaded from `CODEX_HOME`; the overlay copy rewrites source home key prefixes to overlay home key prefixes (`api/src/transport_matters/cli/home_seed.py` `_relocate_codex_hook_trust_state`). Moving a home can leave `config.toml` hook trust keys pointing at the old absolute home path. The current relocation only rewrites keys that start with the current `source_home` path, so stale old root keys will not be repaired automatically.

No Transport Matters code path writes `.credentials.json` for Codex or Claude. The observed Codex auth store is `auth.json` in the selected Codex home.

## 4. Blast radius if homes move to `~/.agent-runtimes/runtimes/<name>`

Transport Matters itself has no hardcoded `~/.agent-runtimes/<name>` root. New launches should work if the caller passes the new path to `--agent-home-dir` or sets `TRANSPORT_MATTERS_AGENT_HOME_DIR` for captured pane routes (`api/src/transport_matters/cli/__init__.py` `_resolve_home_dir_option`; `api/src/transport_matters/api/v1/run_routes.py` `_spawn_request`).

Expected blast radius:

* External launchers, aliases, and runtime manifests outside this repo must pass the new path. Transport Matters has no name resolver for `~/.agent-runtimes`.
* Existing run manifests and durable run facts preserve old absolute `home_dir` values (`api/src/transport_matters/launch_manifest.py` `write_workspace_manifest`; `api/src/transport_matters/cli/launch_profile.py` `persist_owned_session_facts`; `api/src/transport_matters/storage/session_facts.py` `OwnedSessionFacts`).
* Postgres session rows can preserve old absolute `home_dir` and `source_descriptor` fields (`api/src/transport_matters/session/models.py` `SessionRow`). Historical reads or backfills that depend on old transcript source paths will not follow a moved home unless the old files remain or the records are migrated.
* Claude `.claude.json` cwd trust moves with the file and is keyed by cwd, so it is less home path sensitive. Existing transcript descriptors for old sessions still point at the previous home path.
* Codex `config.toml` project trust moves with the file and is keyed by cwd. Codex hook trust may break because hook state table keys embed the old absolute home path (`api/src/transport_matters/cli/home_seed.py` `_relocate_codex_hook_trust_state`).
* Existing source home `projects/`, `sessions/`, logs, caches, lockfiles, and histories may move with the template if the runtime directory is copied wholesale. Future launches may also mutate them through direct Codex home use or overlay symlinks.

## 5. Pristine template feasibility and clean seam

Current Transport Matters cannot guarantee that `--agent-home-dir <template>` remains pristine.

Reasons:

* Codex terminal and desktop Codex launch directly with `CODEX_HOME=<template>` and write `auth.json`, `config.toml`, and `sessions/...` there before the child starts (`api/src/transport_matters/cli/codex_cmd.py` `run_codex`, `build_codex_invocation`; `api/src/transport_matters/cli/home_seed.py` `CodexSeeder.seed`; `api/src/transport_matters/cli/launch_profile.py` `CodexLaunchProfile.prepare`).
* Claude and captured launches create an overlay, but `_symlink_source_home_entries` symlinks all existing source entries except a small local denylist. Existing `projects/`, `sessions/`, histories, caches, plugins, skills, hooks, or logs can be mutated through those symlinks (`api/src/transport_matters/cli/home_seed.py` `_symlink_source_home_entries`, `_overlay_local_names`).
* Captured Codex pre-seeds the source home's `sessions/` after overlay creation, which mutates the source and can leave the overlay unable to see the pre-seeded rollout if `sessions/` did not already exist (`api/src/transport_matters/captured_run_context.py` `build_captured_run_context`; `api/src/transport_matters/cli/launch_profile.py` `CodexLaunchProfile.prepare`).
* Launch metadata currently treats the supplied home as the transcript root. `ClaudeLaunchProfile.prepare`, `CodexLaunchProfile.prepare`, `build_launch_env`, `persist_owned_session_facts`, and `write_workspace_manifest` all publish the supplied home, not a separate instance home (`api/src/transport_matters/cli/launch_profile.py` `ClaudeLaunchProfile.prepare`, `CodexLaunchProfile.prepare`, `persist_owned_session_facts`; `api/src/transport_matters/launch_environment.py` `build_launch_env`; `api/src/transport_matters/launch_manifest.py` `write_workspace_manifest`).

Cleanest seam:

* Treat `--agent-home-dir` as the template source input and create a separate writable instance home for every launch, for example `<run storage>/runtime-home/<client>` or a durable `~/.agent-runtimes/instances/<runtime>/<run>` path.
* Publish the writable instance home to the child via `CLAUDE_CONFIG_DIR` or `CODEX_HOME` and to the addon via `TRANSPORT_MATTERS_AGENT_HOME_DIR`. Source descriptors should use the instance home as the transcript root.
* Keep the template path private to the seeding step or record it in a separate `template_home_dir` field if provenance is needed.
* Change `prepare_managed_session` calls to use the instance home for `claude_projects_root` and `codex_sessions_root`. Codex rollout seeding must happen in the same instance home that the child receives.
* Replace broad source symlinking with an explicit allowlist. Copy mutable config files before mutation. Never symlink or write template paths for `projects`, `sessions`, `history.jsonl`, daemon state, jobs, logs, caches, lockfiles, SQLite files, or any path a child can mutate. Symlink only read only assets when the product can enforce or tolerate read only semantics.
* Keep `_relocate_codex_hook_trust_state` but make it rewrite copied `config.toml` to the instance home. If moved templates can carry old root hook keys, add a migration that rewrites known old template roots or recomputes hook trust.
* Remove `stack.callback(shutil.rmtree, runtime_home_root, ignore_errors=True)` or delay cleanup until transcript tailing and snapshotting are complete when the instance home is the only place transcripts exist (`api/src/transport_matters/captured_run_context.py` `build_captured_run_context`).

This can be done through the existing launch contract because all downstream child home and metadata writes flow through `build_captured_run_context`, `build_managed_child_env`, `build_launch_env`, `prepare_managed_session`, and `write_workspace_manifest`. Codex terminal launch needs to join the overlay or instance path rather than bypass it.

## Verification performed

* fmm structural pass: `fmm_list_files(group_by="subdir")`, outlines for `home_seed.py`, `launch_options.py`, `launch_runtime.py`, `codex_cmd.py`, `captured_run_context.py`, `captured_claude.py`, `captured_codex.py`, `run_manager.py`, `run_routes.py`, `launch_environment.py`, `launch_profile.py`, and dependency graphs for the home and launch modules.
* Focused tests: `cd api && .venv/bin/python -m pytest src/transport_matters/cli/test_home_seed.py src/transport_matters/cli/test_start_storage.py src/transport_matters/cli/test_codex.py src/transport_matters/test_captured_run_web_separation.py -q`: 61 passed.
* Focused tests: `cd api && .venv/bin/python -m pytest src/transport_matters/cli/test_start_mint.py src/transport_matters/cli/test_codex_session.py src/transport_matters/cli/test_launch_profile.py -q`: 29 passed.
* Probe against live code confirmed: absent Claude source `projects/` produces no overlay symlink; existing source `projects/` is symlinked; captured Codex source `sessions/` can be created after overlay creation with no overlay symlink.
