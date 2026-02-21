---
title: Manicure to Transport Matters Rename Overview
type: research
tags: [helioy, manicure, transport-matters, rename, architecture]
summary: Consolidated rename blast radius for moving Manicure to transport-matters across API, frontend, docs, packaging, tests, and fixtures.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## Executive Summary

The rename from `manicure` to `transport-matters` is a repository, package, command, storage, environment, documentation, and fixture migration. The largest mechanical cost is the Python namespace under `api/src/manicure`; the highest remaining policy decisions are the `MANICURE_*` env prefix, `~/.manicure` storage namespace, PyPI package name, and persisted `manicure_*` schema keys.

Five focused scan artifacts were written by delegated agents. A top level tracked file scan found 371 tracked files, 223 tracked content files with `manicure|Manicure|MANICURE`, 1,707 tracked content occurrences, and 179 tracked path hits.

Decision update: the CLI command is `transport` only. Do not add a `manicure` compatibility alias or a `transport-matters` console command unless this decision changes.

## Project Metadata

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/manicure`
- Indexed by fmm: yes, `.fmm.db` exists at repo root and package subtrees.
- fmm topology: 300 indexed files, 57,576 LOC.
- Main code roots: `api/` with 182 files and 38,557 LOC, `www/` with 118 files and 19,019 LOC.
- Languages and build systems: Python 3.12 package with `uv`, Hatch, Ruff, MyPy, Pytest; React 19 and TypeScript with Vite, pnpm, Vitest, Playwright, Biome.

## Architecture and Rename Surfaces

### API and Python package

Artifact: `~/.mdx/research/manicure-to-transport-matters-api.md`

- Scope: 181 tracked API files, including 178 Python files under `api/src/manicure`.
- The package directory and imports are the core blast radius. The API scan counted 573 import lines referencing `manicure` across 154 files.
- Package metadata declares `name = "manicure"`, entry point `manicure = "manicure.cli:main"`, build paths under `src/manicure`, first party import config, and coverage source in `api/pyproject.toml:4`, `api/pyproject.toml:48`, `api/pyproject.toml:88-97`, `api/pyproject.toml:129`, and `api/pyproject.toml:155`.
- Runtime settings use `env_prefix="MANICURE_"`, default `app_name="manicure"`, and default `storage_dir=Path.home() / ".manicure"` in `api/src/manicure/config.py:16-30`.
- Workspace storage is explicitly `~/.manicure/workspaces/{slug}/{hash}` in `api/src/manicure/workspace.py:1-10` and `api/src/manicure/workspace.py:63-70`.
- The mitmproxy addon class is exported as `ManicureAddon` and instantiated as `addons = [ManicureAddon()]` in `api/src/manicure/addon.py:36-50` and `api/src/manicure/addon.py:91`.

### Frontend and UI

Artifact: `~/.mdx/research/manicure-to-transport-matters-frontend.md`

- Scope: 139 tracked frontend files.
- The frontend scan found 56 case insensitive Manicure occurrences across 22 files.
- Main concerns are visible branding, `ManicureIcon`, local storage keys, Vite globals, output path, test selectors, and fixture truth.
- `www/package.json:2` declares package name `manicure`.
- `www/vite.config.ts:11`, `www/vite.config.ts:27`, and `www/vite.config.ts:43` use `MANICURE_VERSION`, `__MANICURE_VERSION__`, and output to `../api/src/manicure/www`.
- Existing plain `transport` terminology is heavy in the product. A top level scan found 875 lowercase `transport` occurrences across 90 files and 243 capitalized `Transport` occurrences across 44 files. Avoid naming that confuses product identity with protocol transport internals.

### Docs and help

Artifact: `~/.mdx/research/manicure-to-transport-matters-docs-help.md`

- The docs agent found 221 tracked files containing `manicure`, 1,516 tracked occurrences, zero tracked `transport-matters` or `transport matters` occurrences, 18 files with `.manicure`, and 28 files with `MANICURE_*`.
- Primary docs that need current user facing rewrite: `README.md`, `PROJECT.md`, `TLDR.md`, `api/README.md`, `api/src/manicure/cli/help.py`, `install.sh`, `release.sh`, `.github/workflows/release.yml`.
- `README.md` contains install URLs, `uv tool install manicure`, command examples, `~/.manicure` storage, and command lists at `README.md:1`, `README.md:16-19`, `README.md:25-45`, `README.md:90`, and `README.md:198-203`.
- CLI help has 62 tracked occurrences in the help blobs from `api/src/manicure/cli/help.py:26-232`.
- Historical docs under `DOCS/superpowers/plans/` contain many references. Treat these as historical unless a plan remains active.

### Config, packaging, CI, release

Artifact: `~/.mdx/research/manicure-to-transport-matters-config-packaging.md`

- Scope: 23 tracked config and packaging files.
- The config agent found 125 `manicure|Manicure|MANICURE` occurrences.
- Lockfile findings: `api/uv.lock:932` has one project name occurrence; `www/pnpm-lock.yaml` has zero counted package name occurrences.
- Highest risk files: `api/pyproject.toml`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `install.sh`, `release.sh`, `api/justfile`, root `justfile`, `www/vite.config.ts`, `www/package.json`, `api/.env.example`.
- CI builds and smokes the embedded frontend under `api/src/manicure/www` and the `manicure` console command in `.github/workflows/ci.yml:63`, `.github/workflows/ci.yml:107`, `.github/workflows/ci.yml:136-154`, and `.github/workflows/ci.yml:169-182`.
- Release workflow publishes and smokes `manicure` artifacts, including PyPI URL and release asset names in `.github/workflows/release.yml:105`, `.github/workflows/release.yml:115-118`, `.github/workflows/release.yml:137-150`, `.github/workflows/release.yml:175`, and `.github/workflows/release.yml:212-226`.

### Tests and fixtures

Artifact: `~/.mdx/research/manicure-to-transport-matters-tests-fixtures.md`

- Scope: 163 tracked test, fixture, and visual snapshot files.
- The tests agent found 705 case insensitive `manicure` occurrences across 101 files.
- Key counts: 337 Python import namespace occurrences across 94 files, 206 monkeypatch module string occurrences across 34 files, 45 `MANICURE_` occurrences across 11 files, 9 persisted metadata key occurrences across 3 files, and 529 `transport` occurrences across 49 files.
- Test migration needs package import updates, monkeypatch string updates, env var policy updates, storage path expectations, metadata key compatibility tests, and visual snapshot regeneration.

## Key Patterns

- Public identity is spread across code and state. Rename policy needs separate decisions for repository name, PyPI project, import package, console command, environment prefix, storage directory, visible product copy, and persisted schema keys.
- `transport` is already a domain term for Codex and HTTP transport internals. Product names should be explicit as `transport-matters` in docs and likely `transport_matters` in Python to reduce ambiguity.
- The embedded frontend path couples TypeScript build output to the Python package layout. `www/vite.config.ts:43`, CI staging, release workflow, and Hatch artifact globs must move together.
- Compatibility work is more important than search and replace. Existing local state under `~/.manicure`, existing scripts using `manicure`, and persisted `manicure_*` fields need an intentional migration story.

## Recommended Sequencing

1. Decide public compatibility policy.
   - CLI: hard cut to `transport` only. Update every script, smoke test, help example, and installer check to call `transport`.
   - Env vars: accept both `MANICURE_*` and new prefix, with clear precedence.
   - Storage: read old `~/.manicure` and write new `~/.transport-matters`, or keep storage stable.
   - Persisted keys: preserve `manicure_*` keys as schema history, or add migration and tests.

2. Rename Python package and metadata.
   - Move `api/src/manicure` to the chosen import package, probably `api/src/transport_matters`.
   - Update imports, quoted module strings, `api/pyproject.toml`, Hatch artifact globs, Ruff first party config, coverage source, and uv lock.

3. Update embedded frontend coupling.
   - Change Vite build global names and output path.
   - Update Hatch artifact path, CI staging path, release workflow path, and smoke checks in one commit.

4. Update user facing command, docs, and installer.
   - README, TLDR, PROJECT, API README, CLI help, install script, release script, GitHub URLs, PyPI URLs, and issue links.

5. Update tests and fixtures.
   - Package imports first.
   - Monkeypatch strings second.
   - Env and storage expectations third.
   - Fixture and visual snapshots last.

6. Verify.
   - API: `uv run pytest --cov=<new_package> --cov-report=term` from `api/`.
   - Frontend: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` from `www/`.
   - CI parity: build wheel, install into clean venv, smoke the command, verify embedded `www/index.html` in the wheel.

## Detailed Findings by Artifact

| Artifact | Scope | Headline |
|---|---|---|
| `manicure-to-transport-matters-api.md` | API and Python package | Direct package rename. CLI decision is now `transport` only; env, storage, addon name, and persisted keys still need policy. |
| `manicure-to-transport-matters-frontend.md` | React UI and frontend config | 56 frontend occurrences, concentrated in branding, icon names, local storage keys, Vite globals, and tests. |
| `manicure-to-transport-matters-docs-help.md` | Docs and help prose | 1,516 tracked docs and user facing occurrences, with README, CLI help, installer, release, and historical docs as main surfaces. |
| `manicure-to-transport-matters-config-packaging.md` | Packaging, config, CI, release | 125 occurrences in config scope, highest risk in pyproject, workflows, installer, release, and embedded frontend paths. |
| `manicure-to-transport-matters-tests-fixtures.md` | Tests, fixtures, snapshots | 705 scoped test and fixture occurrences, especially imports, monkeypatch strings, env vars, metadata, and snapshots. |

## Dependencies

- Python package manager and build: `uv`, Hatch, `uv.lock`, `api/pyproject.toml`.
- Python runtime and API: FastAPI, Uvicorn, Pydantic Settings, mitmproxy.
- Frontend build: pnpm, Vite, React, TypeScript, Vitest, Playwright, Biome.
- Release: GitHub Actions, PyPI trusted publishing, release assets, wheel smoke tests.

## Relevance to Helioy

The rename aligns the repo with the `*-matters` Helioy naming pattern. The work should preserve operational continuity because Manicure is already a transport control plane for Claude and Codex sessions and writes operator state into user scoped storage.

## Open Questions

1. Resolved: the console command is `transport` only. No `manicure` compatibility alias.
2. Should the PyPI project be `transport-matters`, while the import package becomes `transport_matters`?
3. Should existing `MANICURE_*` env vars remain supported, and what precedence should apply when both old and new prefixes are set?
4. Should `~/.manicure` migrate to a new dotdir, remain as legacy storage, or be transparently read through a compatibility layer?
5. Are persisted `manicure_*` metadata keys public schema history that should stay stable?
6. Should historical `DOCS/superpowers/plans/` be rewritten, archived as history, or left untouched?
