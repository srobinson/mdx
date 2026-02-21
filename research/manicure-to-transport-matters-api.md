---
title: Manicure to Transport Matters API Rename Scan
type: research
tags: [helioy, manicure, transport-matters, api, python, rename]
summary: Narrow scan of tracked API and Python package rename blast radius for manicure to transport-matters.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## Executive Summary

The narrowed API scope contains a direct package rename, not just a repository rename. The Python package is `manicure`, the console command is `manicure`, runtime env vars use `MANICURE_`, persisted storage defaults to `~/.manicure`, and several public or persisted strings include `manicure`.

If the new public repo name is `transport-matters`, the Python import package should likely become `transport_matters`. Decision update: the installed CLI command is `transport` only, with no `manicure` compatibility alias. Env prefix, storage path, and persisted data compatibility remain separate decisions.

## Project Metadata

- Scope inspected: tracked files only matching `api/src/manicure/**/*.py`, `api/pyproject.toml`, `api/README.md`, `api/.env.example`.
- Scope file count: 181 tracked files.
- Python package files: 178 files under `api/src/manicure`.
- Production Python files: 81, excluding `test_*.py` and `conftest.py`.
- Test and conftest files in package scope: 97.
- fmm status: indexed. Topology from fmm showed `api/` at 182 files and 38,557 LOC, with `api/src/manicure` as the API package.

## Exact Occurrence Counts

Counts below are within the narrowed tracked scope only.

| Category | Occurrences | Lines | Files | Notes |
|---|---:|---:|---:|---|
| Lowercase word `manicure` | 1,053 | 1,046 | 171 | Imports, paths, CLI text, docs, pyproject, tests |
| Python import lines from or import `manicure` | 573 | 573 | 154 | Main mechanical package rename blast radius |
| Quoted module strings like `"manicure.*"` | 206 | 205 | 37 | Monkeypatch paths, pytest plugins, uvicorn target, logging formatter |
| Env vars `MANICURE_*` | 77 | 76 | 22 | 9 unique env vars |
| Dotdir path `.manicure` | 26 | 26 | 15 | Runtime storage and workspace roots |
| Capitalized `Manicure*` names or prose | 63 | 63 | 23 | `ManicureAddon` is 43 of these |
| Metadata keys with `manicure_` prefix | 28 | 27 | 12 | Flow metadata and manifest fields |
| CLI word `manicure` | 229 | 227 | 65 | CLI command examples, help, errors, docs |

Unique `MANICURE_*` variables:

| Env var | Count |
|---|---:|
| `MANICURE_STORAGE_DIR` | 22 |
| `MANICURE_CWD` | 20 |
| `MANICURE_RUN_ID` | 14 |
| `MANICURE_PROXY_PORT` | 8 |
| `MANICURE_WEB_PORT` | 7 |
| `MANICURE_DEBUG` | 2 |
| `MANICURE_UPSTREAM_URL` | 2 |
| `MANICURE_APP_NAME` | 1 |
| `MANICURE_LOG_JSON` | 1 |

Unique `manicure_` metadata or field names:

| Key | Count |
|---|---:|
| `manicure_version` | 6 |
| `manicure_ir` | 3 |
| `manicure_curated_ir` | 3 |
| `manicure_provisional_exchange_id` | 3 |
| `manicure_codex_transport` | 2 |
| `manicure_audit` | 2 |
| `manicure_mutated_manually` | 2 |
| `manicure_dropped` | 2 |
| `manicure_codex_breakpoint_paused_at_ms` | 1 |
| `manicure_codex_breakpoint_released_at_ms` | 1 |
| `manicure_adapter` | 1 |
| `manicure_raw_req` | 1 |
| `manicure_track_assignment` | 1 |

## Architecture Relevant to Rename

### Package identity and build metadata

- Distribution name is `manicure`: `api/pyproject.toml:4`.
- Console entry point is `manicure = "manicure.cli:main"`: `api/pyproject.toml:47-48`.
- Project URLs point at `srobinson/manicure`: `api/pyproject.toml:50-54`.
- Hatch version file and package include paths are under `src/manicure`: `api/pyproject.toml:87-97`.
- Ruff first party package is `manicure`: `api/pyproject.toml:128-129`.
- Coverage source is `manicure`: `api/pyproject.toml:153-155`.
- Runtime version fallback queries package metadata for `manicure`: `api/src/manicure/__init__.py:11-19`.

Rename implication: change the import package to `transport_matters` and the on disk package directory to `api/src/transport_matters`. The distribution and CLI names may use `transport-matters`, but Python imports cannot use hyphens.

### Import graph and module strings

- 573 import lines reference `manicure` across 154 files.
- High density import files include:
  - `api/src/manicure/api/v1/test_exchanges_pipeline_tokens.py`: 22 import lines.
  - `api/src/manicure/codex/exchange.py`: 16 import lines.
  - `api/src/manicure/test_supervisor_pty.py`: 15 import lines.
  - `api/src/manicure/api/v1/test_exchanges_list.py`: 14 import lines.
  - `api/src/manicure/exchange_recorder.py`: 14 import lines.
- Runtime string references include `uvicorn.run("manicure.main:app")`: `api/src/manicure/__main__.py:8-14`.
- Logging formatter string is `manicure.logging.JSONFormatter`: `api/src/manicure/main.py:60-64`.
- `importlib.resources.files("manicure")` locates packaged resources and addon files: `api/src/manicure/cli/__init__.py:119-134`, `api/src/manicure/cli/paths.py:57-59`.

Rename implication: a simple directory move will break module strings, pytest monkeypatch paths, uvicorn startup, logging config, and package resource discovery unless rewritten together.

### CLI entry points and command surface

- Typer app is named `manicure`: `api/src/manicure/cli/__init__.py:85-92`.
- CLI commands include `claude`, hidden `start`, `codex`, `doctor`, `paths`, `list`, and `version`: `api/src/manicure/cli/__init__.py:172-504`.
- CLI options expose env vars directly:
  - Claude proxy, web, upstream, storage: `api/src/manicure/cli/__init__.py:194-244`.
  - Codex proxy, web, storage: `api/src/manicure/cli/__init__.py:349-390`.
- Addon lookup uses `files("manicure") / "addon.py"`: `api/src/manicure/cli/__init__.py:119-134`.
- User docs and local source instructions still use `manicure`: `api/README.md:11-19`, `api/README.md:24-30`, `api/README.md:45-56`.

Rename implication: the installed command becomes `transport` only. Update pyproject, Typer app name, README, help text, installer checks, smoke tests, just recipes, and all CLI tests in the same step. Do not keep `manicure` as a console script alias.

### Runtime env vars

- Settings uses `env_prefix="MANICURE_"`: `api/src/manicure/config.py:16-20`.
- Default app name is `manicure`: `api/src/manicure/config.py:23`.
- CLI launch injects `MANICURE_STORAGE_DIR`, `MANICURE_WEB_PORT`, `MANICURE_PROXY_PORT`, `MANICURE_RUN_ID`, and `MANICURE_CWD`: `api/src/manicure/cli/launch_runtime.py:180-195`.
- `.env.example` documents the prefix and env vars: `api/.env.example:1-13`.
- Meta API explicitly documents and reads `MANICURE_CWD`: `api/src/manicure/api/v1/meta.py:34-49`.

Rename implication: env vars are operational API. Support both `TRANSPORT_MATTERS_*` and `MANICURE_*` during a transition if existing scripts or spawned child processes matter. The Pydantic settings prefix supports one prefix directly, so aliases or a pre-normalization layer may be needed.

### Storage paths and workspace paths

- Default storage dir is `Path.home() / ".manicure"`: `api/src/manicure/config.py:28-30`.
- Workspace root is `~/.manicure/workspaces/{slug}/{hash}`: `api/src/manicure/workspace.py:63-70`.
- Storage backend fallback root is `~/.manicure/exchanges`: `api/src/manicure/storage/disk.py:38-45`.
- CLI paths use `Path.home() / ".manicure" / "workspaces"`: `api/src/manicure/cli/paths.py:45-47`.
- CLI instance listing uses the same root: `api/src/manicure/cli/instances.py:36-38`.
- README describes captured exchanges in `~/.manicure/exchanges/`: `api/README.md:68-70`.

Rename implication: changing the default to `~/.transport-matters` or `~/.transport_matters` creates data migration and workspace discovery risk. If preserving existing captures matters, implement lookup precedence and migration messaging before flipping defaults.

### Public and persisted names

- Public mitmproxy addon class is `ManicureAddon`: `api/src/manicure/addon.py:35-50`.
- Mitmproxy exposes `addons = [ManicureAddon()]`: `api/src/manicure/addon.py:91`.
- Manifest dataclass field is `manicure_version`: `api/src/manicure/manifest.py:32-49`.
- CLI serializes `manicure_version`: `api/src/manicure/cli/instances.py:108-120`.
- Request flow metadata keys use `manicure_*`: `api/src/manicure/flow_state.py:17-25`.
- Codex transport metadata key is `manicure_codex_transport`: `api/src/manicure/codex/transport.py:42-44`.
- Codex breakpoint lifecycle metadata keys use `manicure_codex_*`: `api/src/manicure/codex/exchange_derivation.py:49-50`.

Rename implication: `ManicureAddon` can be renamed with a compatibility alias. Persisted or interop keys like `manicure_version` and flow metadata should either remain legacy for stored data compatibility or support both old and new keys.

### FastAPI metadata and runtime app

- App title comes from `settings.app_name`: `api/src/manicure/main.py:66-68`.
- `settings.app_name` defaults to `manicure`: `api/src/manicure/config.py:23`.
- Static assets are served from package local `www`: `api/src/manicure/main.py:86-90`.
- Dev server target is `manicure.main:app`: `api/src/manicure/__main__.py:8-14`.

Rename implication: FastAPI title is externally visible via docs and generated metadata. Update `app_name`, env aliases, module target, and any generated OpenAPI snapshots together if such snapshots exist outside this narrowed scope.

## Direct Test Blast Radius

Tests are in scope only where they reveal API rename behavior.

- 342 of the 573 `manicure` import lines are in test or conftest files.
- 206 quoted module strings are mostly test monkeypatch paths and pytest plugin names.
- Representative monkeypatch or pytest plugin paths:
  - `api/src/manicure/cli/conftest.py:100` patches `manicure.cli.runner._run_children`.
  - `api/src/manicure/test_supervisor_pty.py:15` uses `pytest_plugins = ("manicure.test_supervisor_support",)`.
  - `api/src/manicure/codex/test_transport_turn_derivation.py:18` uses `pytest_plugins = ("manicure.codex.test_transport_support",)`.
- Env behavior tests assert the current prefix:
  - `api/src/manicure/api/v1/test_meta.py:47-69` covers `MANICURE_CWD`.
  - `api/src/manicure/api/v1/test_meta.py:77-84` covers `MANICURE_RUN_ID`.
  - `api/src/manicure/cli/test_start_storage.py` contains 16 env var occurrences.
- Workspace tests pin slug behavior from the old path name:
  - `api/src/manicure/test_workspace.py:23-24` expects `helioy-manicure-api`.
  - `api/src/manicure/test_workspace.py:163` expects the `.manicure/workspaces` path.

## Rename Risks

1. Import package name risk: `transport-matters` is invalid as a Python module. Use `transport_matters` for imports and package directory.
2. Runtime string risk: uvicorn targets, logging formatter paths, package resource lookup, pytest plugins, and monkeypatch paths will not be caught by import-aware refactors alone.
3. CLI hard cut risk: every command invocation must change from `manicure` to `transport`. Because there are no external users, prefer failing fast over retaining a stale alias.
4. Env compatibility risk: `MANICURE_*` variables are used by parent CLI, child addon process, API endpoints, and tests. Renaming them atomically without aliases can break child process coordination.
5. Storage migration risk: default state is under `~/.manicure`. Switching the path can hide existing captures, rules, manifests, and workspace locks.
6. Persisted schema risk: `manicure_version` appears in manifest JSON. Flow metadata keys are in mitmproxy flow metadata and may be stored indirectly in transport or exchange artifacts.
7. Public class risk: `ManicureAddon` is exported and instantiated by mitmproxy. Rename with alias rather than a hard cut if third party integrations import it.

## Recommended Sequencing

1. Decide naming contract first:
   - Distribution and repo: `transport-matters`.
   - Python package: `transport_matters`.
   - CLI command: `transport` only. No `manicure` alias and no `transport-matters` command.
2. Move package directory and rewrite imports:
   - `api/src/manicure` to `api/src/transport_matters`.
   - Rewrite all imports and `manicure.*` module strings.
   - Update `pyproject.toml` package, version file, hatch artifacts, Ruff first party, coverage source, and script target.
3. Update runtime strings:
   - `files("manicure")`, `"manicure.main:app"`, `"manicure.logging.JSONFormatter"`, pytest plugins, and monkeypatch strings.
4. Add compatibility shims where needed:
   - Optional `manicure` package shim importing from `transport_matters`.
   - No optional console script alias for `manicure`.
   - Optional `ManicureAddon = TransportMattersAddon` alias.
5. Handle env vars deliberately:
   - Introduce `TRANSPORT_MATTERS_*` with fallback reads from `MANICURE_*`.
   - Keep launch env and API settings synchronized before renaming tests.
6. Handle storage migration deliberately:
   - Keep `~/.manicure` as default for one release, or add migration lookup from old to new path with clear diagnostics.
   - Update `paths`, `list`, workspace manifest handling, and storage backend together.
7. Update public docs and direct tests last:
   - README and `.env.example`.
   - CLI, meta, workspace, manifest, and addon tests that pin the old surface.

## Work Log

- Used fmm first for topology and package outlines.
- Restricted final scan to tracked narrowed scope only.
- Ran read-only `git ls-files`, `rg`, and line-number inspection commands.
- Did not modify the target repository. Only wrote this artifact under `~/.mdx/research/`.
- `session-logger` skill was not available in this session, so this Work Log is included here.

## Open Questions

- Resolved: `manicure` should not remain as a compatibility CLI alias. The command is `transport` only.
- Should existing data stay under `~/.manicure` or migrate to a new transport path?
- Should persisted keys such as `manicure_version` be renamed now, or retained as stable legacy schema fields?
