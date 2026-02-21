---
title: Manicure to Transport Matters documentation and help rename scan
type: research
tags: [manicure, transport-matters, rename, docs, cli-help]
summary: Documentation and user facing prose still use manicure throughout READMEs, DOCS, CLI help, installer copy, UI labels, package metadata, and storage path examples.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## Executive Summary

The documentation and help surface is still fully branded as Manicure. No tracked file contains `transport-matters` or `transport matters` yet.

The highest risk rename areas are the user facing command name, PyPI package metadata, storage path `~/.manicure`, environment variables `MANICURE_*`, GitHub URLs, and UI branding. The command decision is now settled as `transport` only; docs and help must update every executable example to match that hard cut.

## Project Metadata

- Root: `/Users/alphab/Dev/LLM/DEV/helioy/manicure`
- fmm status: indexed. `fmm_list_files(group_by="subdir")` reported 300 indexed source files and 57,576 LOC.
- fmm topology: `api/` has 182 indexed files and 38,557 LOC. `www/` has 118 indexed files and 19,019 LOC.
- Backend: Python package, FastAPI, mitmproxy, Typer CLI. `api/pyproject.toml:4`, `api/pyproject.toml:34-42`.
- Python version: `>=3.12`. `api/pyproject.toml:7`.
- CLI entry point: `manicure = "manicure.cli:main"`. `api/pyproject.toml:47-48`.
- Frontend: Vite, React 19, TypeScript 5.9, pnpm 10.8. `www/package.json:2-8`, `www/package.json:24-29`, `www/package.json:32-48`.
- Frontend package name: `manicure`. `www/package.json:2`.

## Scan Method

- Used fmm first for structural orientation and key outlines:
  - `fmm_list_files(group_by="subdir")`
  - `fmm_file_outline(api/src/manicure/cli/help.py)`
  - `fmm_file_outline(api/src/manicure/cli/__init__.py)`
  - `fmm_file_outline(www/src/app.tsx)`
- Ran read only searches against tracked files with generated and external output excluded.
- Excluded from primary counts: `dist`, `node_modules`, `htmlcov`, `playwright-report`, `test-results`.
- Did not modify the target repo.

## Exact Counts

Primary tracked file scan, excluding generated and external output:

| Query | Files | Occurrences |
| --- | ---: | ---: |
| `\bmanicure\b`, case insensitive | 221 | 1,516 |
| `transport-matters` or `transport matters`, case insensitive | 0 | 0 |
| `~/.manicure` or `.manicure` path token | 18 | 25 |
| `MANICURE_*` env vars | 28 | 88 |
| `github.com/srobinson/manicure` | 7 | 17 |

Breakdown of tracked `manicure` references by rename ownership category:

| Category | Files | Occurrences |
| --- | ---: | ---: |
| Root docs and scripts | 6 | 105 |
| `DOCS/` architecture notes and plans | 13 | 239 |
| API docs, config, help adjacent files | 4 | 35 |
| API CLI help and user prose | 35 | 404 |
| API source comments and user strings | 59 | 269 |
| Tests and fixtures | 80 | 378 |
| Web UI prose and config | 17 | 25 |
| Other tracked files | 7 | 61 |

## Architecture of the Rename Surface

### Documentation layer

Primary user docs are heavily branded and command specific:

- `README.md` has 46 occurrences. Core examples include install URLs, `uv tool install manicure`, `manicure claude`, `manicure codex`, and `~/.manicure/workspaces/...`. See `README.md:1`, `README.md:16-19`, `README.md:25-45`, `README.md:90`, `README.md:198-203`.
- `PROJECT.md` has 18 occurrences. It defines the product, PyPI package, storage root, install route, command list, and dev command. See `PROJECT.md:1`, `PROJECT.md:5`, `PROJECT.md:24`, `PROJECT.md:60`, `PROJECT.md:97-124`, `PROJECT.md:135`.
- `TLDR.md` has 8 occurrences. It gives the compact install and command story. See `TLDR.md:1`, `TLDR.md:10-13`, `TLDR.md:20`, `TLDR.md:31`, `TLDR.md:40`.
- `api/README.md` has 12 occurrences. It duplicates install, launch, storage, and repository links. See `api/README.md:1`, `api/README.md:12-19`, `api/README.md:26-30`, `api/README.md:70`, `api/README.md:82`.

### CLI help and terminal UX

The CLI help surface is the densest user facing area.

- `api/src/manicure/cli/help.py` has 62 tracked occurrences. fmm shows help blobs for root, Claude, Codex, doctor, paths, version, list, and subcommand help in `api/src/manicure/cli/help.py:26-232`.
- Root help names the product, commands, examples, env var, and GitHub URL. See `api/src/manicure/cli/help.py:27-53`.
- Claude help uses `Start the manicure workbench`, `~/.manicure`, `--no-system-prompt`, and `manicure claude` examples. See `api/src/manicure/cli/help.py:57-113`.
- Codex help uses `Start the manicure workbench`, proxy wording, CA bundle behavior, and `manicure codex` examples. See `api/src/manicure/cli/help.py:117-162`.
- Doctor, paths, version, and list help use command names and storage paths. See `api/src/manicure/cli/help.py:175-221`.
- Launch banner prints `manicure starting`. `api/src/manicure/cli/banner.py:26`.
- Diagnostic remediation tells users to reinstall with `uv tool install --force manicure`. `api/src/manicure/cli/diagnose.py:58-92`.
- Paths and instance contention UX mention `manicure paths`, `manicure list`, and live instances. `api/src/manicure/cli/paths.py:1-15`, `api/src/manicure/cli/paths.py:145`, `api/src/manicure/cli/instances.py:42-72`, `api/src/manicure/cli/instances.py:102`.

### Installer, release, and package metadata

These references are user facing but must follow packaging decisions.

- Package name is `manicure`. `api/pyproject.toml:4`.
- Console script is `manicure`. `api/pyproject.toml:47-48`.
- Project URLs point at `srobinson/manicure`. `api/pyproject.toml:51-54`.
- Hatch build paths include `src/manicure`. `api/pyproject.toml:88-97`.
- Ruff and coverage know the first party package as `manicure`. `api/pyproject.toml:129`, `api/pyproject.toml:155`.
- `install.sh` has 26 occurrences. It prints installer copy, installs the package, checks the command, and links docs and issues. See `install.sh:3-13`, `install.sh:64-72`, `install.sh:121-157`, `install.sh:163-178`.
- `release.sh` has 5 occurrences in release messages and GitHub workflow URLs. See `release.sh:3-7`, `release.sh:62`, `release.sh:106`, `release.sh:131`, `release.sh:138`.
- `.github/workflows/release.yml` has 30 occurrences. It builds into `api/src/manicure/www`, runs `manicure` smoke checks, names wheel artifacts, and publishes to PyPI project `manicure`. See `.github/workflows/release.yml:11-22`, `.github/workflows/release.yml:78-88`, `.github/workflows/release.yml:137-150`, `.github/workflows/release.yml:175`, `.github/workflows/release.yml:212-226`.

### Web UI branding and browser visible text

- `www/index.html` title is `Manicure`. `www/index.html:10`.
- `www/src/app.tsx` renders `Manicure` in the app bar and waiting screen. `www/src/app.tsx:56`, `www/src/app.tsx:127`.
- `www/src/components/ManicureIcon.tsx` exposes accessible name and SVG title as `Manicure`. `www/src/components/ManicureIcon.tsx:9-11`.
- Placeholder comments mention the faded Manicure motif. `www/src/components/routes/RecallView.tsx:6`, `www/src/components/routes/TraceView.tsx:6`.
- Local storage keys include `manicure-ui`, `manicure-overlays`, and `manicure.panel.dismissed.`. See `www/src/stores/uiStore.ts:87`, `www/src/stores/overlaysStore.ts:147`, `www/src/components/editor/DismissablePanel.tsx:6`.

### Architecture notes and historical docs

Architecture docs contain both branding and path references. These are not all active user docs, but they are searchable project knowledge and should be refreshed or marked historical.

- `DOCS/codex-seam-audit.md` has 48 occurrences, including the title and many referenced paths. See `DOCS/codex-seam-audit.md:1-27`, `DOCS/codex-seam-audit.md:120`.
- `DOCS/mitmproxy.md` has 21 occurrences in architecture and planned CLI design. See `DOCS/mitmproxy.md:5`, `DOCS/mitmproxy.md:12-19`, `DOCS/mitmproxy.md:86-98`, `DOCS/mitmproxy.md:131-138`.
- `DOCS/release.md` has 15 occurrences covering install route, package name, wheel contents, and open questions. See `DOCS/release.md:5-8`, `DOCS/release.md:18-28`, `DOCS/release.md:36-37`, `DOCS/release.md:62`, `DOCS/release.md:102-112`.
- `DOCS/cache.md` has 13 occurrences and describes Manicure as the cache policy owner. See `DOCS/cache.md:43-79`.
- Superpowers plan files under `DOCS/superpowers/plans/` contain 127 occurrences total. These are implementation history and should likely be left as historical or updated only if they remain active planning references.

### Comments intended as docs and user facing diagnostics

These source strings are in scope because they affect help, logs, diagnostics, or generated docs.

- Config comments and defaults: `api/src/manicure/config.py:10-41`.
- Workspace docstrings and storage path: `api/src/manicure/workspace.py:1-9`, `api/src/manicure/workspace.py:42`, `api/src/manicure/workspace.py:70`, `api/src/manicure/workspace.py:83-84`.
- Manifest docstrings and metadata field: `api/src/manicure/manifest.py:1-10`, `api/src/manicure/manifest.py:34`, `api/src/manicure/manifest.py:47`, `api/src/manicure/manifest.py:100`.
- Codex diagnostics are user visible and include `Manicure proxy` and `manicure codex --debug`. `api/src/manicure/codex/diagnostics.py:48-50`, `api/src/manicure/codex/diagnostics.py:67`, `api/src/manicure/codex/diagnostics.py:83`, `api/src/manicure/codex/diagnostics.py:116-136`.

## Rename Categories

1. Product display name
   - `Manicure` in prose, UI headings, HTML title, SVG accessible label, banner, and diagnostics.
   - Likely target display name: `Transport Matters`.

2. CLI command name
   - `manicure` command examples and help text.
   - Decision settled: replace with `transport` only. Do not document `manicure` as a legacy command.

3. Python import package and source paths
   - `manicure` appears in import paths and references like `api/src/manicure/...`.
   - Other agents own API/config, but docs cannot be fully corrected until module path decisions are final.

4. PyPI and frontend package metadata
   - `api/pyproject.toml` and `www/package.json` still identify packages as `manicure`.
   - This is packaging owned but docs and help depend on it.

5. Storage and local state namespace
   - `~/.manicure`, `MANICURE_STORAGE_DIR`, `MANICURE_CWD`, `MANICURE_VERSION`, and local storage keys.
   - This needs migration policy before help text changes, because stale examples could strand user data.

6. Repository URLs and release assets
   - GitHub URLs and release workflow point at `srobinson/manicure`.
   - Update after repository move or add redirects if GitHub rename is planned.

7. Historical architecture notes
   - `DOCS/` and `DOCS/superpowers/plans/` preserve old state and implementation plans.
   - Decide whether to bulk rename, add a note that they are historical, or archive.

## Risks

- Package and command mismatch risk: changing README and help to `transport-matters` before `api/pyproject.toml:47-48` changes would produce invalid commands.
- Storage migration risk: replacing `~/.manicure` in docs before code supports the new location will confuse users and break copy paste commands.
- Environment variable risk: `MANICURE_*` appears in code, help, Vite version stamping, and tests. Rename requires compatibility aliases or a transition note.
- Searchability risk: historical `DOCS/` files will continue to dominate search results if left unmarked.
- UI persistence risk: local storage key rename can reset UI state. This is low severity but should be intentional.
- Release risk: installer, release workflow, PyPI URL, wheel path assertions, and smoke commands all assume `manicure`.

## Recommended Sequencing

1. Decide canonical names:
   - Display name: `Transport Matters`.
   - CLI command: `transport` only.
   - Python import package: likely `transport_matters` if renamed.
   - Storage dir and env prefix: likely `.transport-matters` and `TRANSPORT_MATTERS_*`, with migration aliases if needed.

2. Let API, config, packaging, and tests agents land executable rename mechanics first.

3. Update user docs in this order:
   - `README.md`, `PROJECT.md`, `TLDR.md`, `api/README.md`.
   - `api/src/manicure/cli/help.py`, `banner.py`, `diagnose.py`, `paths.py`, `instances.py`, and Codex diagnostics.
   - `install.sh`, `release.sh`, `.github/workflows/release.yml`, and package URLs once the release path exists.
   - `www/index.html`, `www/src/app.tsx`, `www/src/components/ManicureIcon.tsx`, route placeholder comments, and local storage key names if desired.
   - `DOCS/` architecture notes. Treat superpowers plans as historical unless they are still active.

4. Add a short rename note to README if helpful, but do not document old command compatibility:
   - Old storage directory compatibility.
   - Old env var compatibility.

5. Run a final read only verification search:
   - `rg -n -i '\bmanicure\b|transport-matters|transport matters' README.md PROJECT.md TLDR.md DOCS api www install.sh release.sh .github`
   - `rg -n 'MANICURE_|~/.manicure|github.com/srobinson/manicure' README.md PROJECT.md TLDR.md DOCS api www install.sh release.sh .github`

## Open Questions

- Resolved: executable command is `transport` only. No legacy command remains.
- Will the Python import package change from `manicure` to `transport_matters`?
- What is the new GitHub repository path?
- Should storage migrate from `~/.manicure` to a new directory, or should docs retain `~/.manicure` for compatibility?
- Should `DOCS/superpowers/plans/` be treated as historical records or updated with the rest of documentation?

## Work Log

- Context Matters startup browse was attempted with `scope="auto"`; the tool reported that `auto` is removed and `cwd_inferred` should be used.
- Used fmm for repository shape and key file outlines before direct inspection.
- Ran read only search commands and inspected representative docs, CLI help, installer, release, config, and UI files.
- Wrote only this research artifact outside the target repo.
- `session-logger` skill is unavailable in this session, so this Work Log is included here.
