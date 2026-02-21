---
title: Manicure to Transport Matters Config and Packaging Rename Scan
type: research
tags: [manicure, transport-matters, rename, packaging, ci, configuration]
summary: Narrow scan of tracked packaging and config files found 125 Manicure name occurrences across 23 in scope files, with highest risk in Python package metadata, CI release paths, installer commands, and runtime env prefixes.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## Executive Summary

This narrowed scan covers tracked repository level packaging, build, CI, installer, hook, and frontend config files for the planned rename from `manicure` to `transport-matters`. The main rename risk is not the GitHub repo name alone. The package identity, Python import package, console script, wheel artifact names, embedded frontend path, env prefix, storage directory, and CI smoke tests are coupled and must be sequenced deliberately.

## Scope and Method

Used fmm first for structure. `fmm_list_files(group_by: "subdir")` reported 300 indexed files and 57,576 LOC split across `api/` and `www/`. fmm markers exist at `.fmm.db`, `api/.fmm.db`, and `www/.fmm.db`.

Narrowed scan inspected tracked files only from the requested paths and patterns. Excluded `node_modules`, `.venv`, caches, `dist`, `TMP`, `.nancy`, `test-results`, and `playwright-report`. Lockfiles were not inspected line by line. They were searched only for `manicure|Manicure|MANICURE` occurrences.

In scope tracked files: 23.

## Exact Occurrence Counts

Pattern counted: `manicure|Manicure|MANICURE`.

### By file

| File | Count |
|---|---:|
| `.github/workflows/ci.yml` | 18 |
| `.github/workflows/release.yml` | 30 |
| `api/.env.example` | 11 |
| `api/justfile` | 6 |
| `api/pyproject.toml` | 15 |
| `api/uv.lock` | 1 |
| `install.sh` | 31 |
| `justfile` | 2 |
| `release.sh` | 6 |
| `www/package.json` | 1 |
| `www/vite.config.ts` | 4 |
| Other in scope files | 0 |
| **Total** | **125** |

### By category

| Category | Files | Occurrences |
|---|---:|---:|
| Python packaging, `api/pyproject.toml`, `api/uv.lock` | 2 | 16 |
| Frontend packaging, `www/package.json`, `www/pnpm-lock.yaml`, `www/pnpm-workspace.yaml` | 3 | 1 |
| CI and release, `.github/workflows/*`, `release.sh` | 3 | 54 |
| Installer, `install.sh` | 1 | 31 |
| Task runners and hooks, root and app justfiles, lefthook, pre commit | 6 | 8 |
| Runtime env config, `api/.env.example` | 1 | 11 |
| Frontend build config, Vite, Biome, tsconfig files | 5 | 4 |
| **Total** | **21 files with grouped categories** | **125** |

The remaining two in scope files, `Procfile` and `api/.python-version`, had zero occurrences.

## Key Line References

### Python package identity

`api/pyproject.toml` is the core Python package identity file.

- Package name: `api/pyproject.toml:4`, `name = "manicure"`.
- Console script: `api/pyproject.toml:48`, `manicure = "manicure.cli:main"`.
- Project URLs: `api/pyproject.toml:51` to `api/pyproject.toml:54` point to `https://github.com/srobinson/manicure`.
- Hatch generated version path: `api/pyproject.toml:88`, `src/manicure/_version.py`.
- Wheel package path: `api/pyproject.toml:91`, `packages = ["src/manicure"]`.
- Wheel artifacts: `api/pyproject.toml:93`, `src/manicure/_version.py` and `src/manicure/www/**`.
- Sdist include: `api/pyproject.toml:96`, `src/manicure`.
- Ruff first party import: `api/pyproject.toml:129`, `known-first-party = ["manicure"]`.
- Coverage source: `api/pyproject.toml:155`, `source = ["manicure"]`.

`api/uv.lock` has one package name occurrence only:

- `api/uv.lock:932`, `name = "manicure"`.

### Frontend package and build embedding

- `www/package.json:2`, frontend package name is `manicure`.
- `www/vite.config.ts:7` and `www/vite.config.ts:11`, build version uses `MANICURE_VERSION`.
- `www/vite.config.ts:27`, Vite injects `__MANICURE_VERSION__`.
- `www/vite.config.ts:43`, frontend output is embedded at `../api/src/manicure/www`.
- `www/pnpm-lock.yaml` has zero package name occurrences for the counted pattern.

### CI packaging and release chain

`.github/workflows/ci.yml` packages and smokes the current package identity.

- Test coverage command: `.github/workflows/ci.yml:63`, `uv run pytest --cov=manicure`.
- Frontend bundle artifact path: `.github/workflows/ci.yml:107`, `api/src/manicure/www/`.
- Bundle staging: `.github/workflows/ci.yml:136`, `mkdir -p api/src/manicure/www`.
- Wheel install and CLI smoke tests: `.github/workflows/ci.yml:169` to `.github/workflows/ci.yml:175`, `dist/manicure-*.whl` and `/tmp/smoke/bin/manicure`.
- Embedded wheel assertion: `.github/workflows/ci.yml:180` to `.github/workflows/ci.yml:182`, checks `manicure/www/index.html`.

`.github/workflows/release.yml` repeats the package chain and adds publishing identity.

- PyPI trusted publishing comment: `.github/workflows/release.yml:22`, `project=manicure`, `repo=manicure`.
- Frontend build target: `.github/workflows/release.yml:78`, `api/src/manicure/www`.
- Backend coverage: `.github/workflows/release.yml:105`, `--cov=manicure`.
- Wheel filename parse: `.github/workflows/release.yml:115` to `.github/workflows/release.yml:116`, `dist/manicure-*.whl` and `s/^manicure-.../`.
- Smoke tests: `.github/workflows/release.yml:137` to `.github/workflows/release.yml:143`, `dist/manicure-*.whl` and `/tmp/smoke/bin/manicure`.
- PyPI URL: `.github/workflows/release.yml:175`, `https://pypi.org/project/manicure/...`.
- Checksums and release assets: `.github/workflows/release.yml:212`, `.github/workflows/release.yml:225`, `.github/workflows/release.yml:226`, all use `manicure-*`.
- GitHub Release title: `.github/workflows/release.yml:223`, `manicure $VERSION`.

### Installer and release script

`install.sh` assumes PyPI and CLI names stay `manicure`.

- Installer source URL: `install.sh:6`, GitHub release download path.
- PyPI install target: `install.sh:12`, `uv tool install manicure`.
- Env knobs: `install.sh:22` and `install.sh:24`, `MANICURE_INSTALL_VERSION`, `MANICURE_SKIP_UV_INSTALL`.
- Target construction: `install.sh:121` to `install.sh:127`, `manicure==$pin` or `manicure`.
- Command verification and next steps: `install.sh:145` to `install.sh:178`, `manicure` command and GitHub links.

`release.sh` assumes the release title and tag message remain `manicure`.

- Release banner: `release.sh:62`, `manicure release -> $TAG`.
- Tag message: `release.sh:106` and `release.sh:131`, `manicure $VERSION`.
- Workflow URL: `release.sh:138`, GitHub repo path.

### Task runners and runtime env

- Root `justfile:47`, `uv run --project api manicure start {{args}}`.
- `api/justfile:14`, `uv run python -m manicure`.
- `api/justfile:18`, mitmproxy script path `src/manicure/addon.py`.
- `api/justfile:30`, coverage source `--cov=manicure`.
- `api/justfile:42`, wheel check `dist/manicure-*.whl` and `manicure/www/index.html`.
- `api/.env.example:3`, env vars use the `MANICURE_` prefix.
- `api/.env.example:7`, `MANICURE_APP_NAME=manicure`.
- `api/.env.example:13`, default storage is `~/.manicure`.

## Rename Categories

1. **Distribution identity**: PyPI package `manicure`, wheel and sdist names, GitHub release assets, install target, PyPI trusted publishing project.
2. **Runtime command identity**: console script `manicure`, smoke tests, just recipes, installer verification, docs in installer output.
3. **Python import package identity**: `src/manicure`, `manicure.cli:main`, `known-first-party`, coverage source, embedded `manicure/www` path.
4. **Frontend package identity**: `www/package.json` name and Vite constants.
5. **Build embedding path**: `www/vite.config.ts` emits into `api/src/manicure/www`, while Hatch includes `src/manicure/www/**`.
6. **Runtime config namespace**: `MANICURE_` env prefix and `~/.manicure` storage directory.
7. **Repository URLs**: GitHub URLs in package metadata, installer, release script, and release workflow comments.
8. **Generated metadata references**: Hatch generated `_version.py` path and uv lock package entry.

## Rename Risks

- **Package name and import package can diverge**. A PyPI name of `transport-matters` can still ship import package `manicure`, but that leaves visible old names in build config. Renaming both requires coordinated source directory changes outside this narrowed ownership area.
- **Console script hard cut is intentional**. Change every `manicure` command invocation to `transport`. Do not retain an alias script during migration.
- **PyPI trusted publishing must be changed before release**. `.github/workflows/release.yml:20` to `.github/workflows/release.yml:23` documents PyPI trusted publishing for project `manicure`, repo `manicure`. Publishing under `transport-matters` needs a new PyPI project binding.
- **Wheel checks are path sensitive**. CI and release assert `manicure/www/index.html`; if the Python package directory changes, update Vite outDir, Hatch artifacts, CI staging, zip checks, and smoke tests together.
- **Lockfiles need regeneration after metadata changes**. `api/uv.lock:932` records the editable project name. `www/pnpm-lock.yaml` has no counted occurrence, but `www/package.json:2` should still be updated and lock consistency verified with pnpm.
- **Env and storage namespace are migration decisions**. `MANICURE_` and `~/.manicure` can remain as compatibility aliases or move to a new namespace. A hard cut risks orphaning existing user configuration and captured workspaces.
- **Installer is user facing and high risk**. `install.sh` contains the largest single count at 31 occurrences and couples GitHub URL, PyPI package, command name, env knobs, and support links.

## Recommended Sequencing

1. Decide remaining identity policy first: PyPI package name, import package name, env prefix, and storage directory. CLI command is already decided as `transport` only.
2. Apply the CLI hard cut consistently: update console scripts, CI smoke commands, just recipes, installer checks, release scripts, README examples, and CLI tests from `manicure` to `transport`.
3. Rename Python packaging next: `api/pyproject.toml`, source package paths, Hatch artifacts, Ruff first party config, coverage source, and `api/uv.lock` regeneration.
4. Update frontend build embedding in the same change as Python package paths: `www/vite.config.ts`, CI staging, wheel assertions, and release workflow asset checks.
5. Update installer and release scripts after package identity is stable: `install.sh`, `release.sh`, GitHub URLs, PyPI target, and smoke test commands.
6. Update CI release publishing last, after PyPI trusted publishing and GitHub repo rename are configured.
7. Regenerate lockfiles and run packaging verification: `uv sync --locked` or deliberate lock update, `uv build`, `pnpm install --frozen-lockfile`, `pnpm build`, CI smoke tests.

## Open Questions

- Should the import package become `transport_matters`, or should only the distribution and repo names change?
- Resolved: the CLI command is `transport` only. No `manicure` alias.
- Should `MANICURE_` and `~/.manicure` remain compatibility surfaces for one or more releases?
- Is the target GitHub owner still `srobinson`, and will the new repo URL be `srobinson/transport-matters`?

## Work Log

- Used fmm first for repo topology and confirmed indexed structure.
- Interrupted broad scan and narrowed scope to requested tracked config and packaging files only.
- Counted exact occurrences for the narrowed file set.
- Inspected lockfiles only for counted package name occurrences.
- Wrote this artifact outside the target repo at `~/.mdx/research/manicure-to-transport-matters-config-packaging.md`.
