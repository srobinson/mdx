---
title: K1 Multi Instance Review for Transport Matters
type: research
tags: [transport-matters, k1, alp-2866, code-review, multi-instance, paths]
summary: Final K1 re-review passed after F1 paths selector and F2 nested launch storage inheritance fixes landed in 97fc276.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Executive Summary

Reviewed branch `feat/k1-multi-instance-per-cwd` through commit `97fc276`. The original F1 blocker and peer F2 medium finding are fixed, the full gate is green, and CODEX signed off with the exact line: `I sign off on K1 as currently filed`.

## Project Metadata

- Language: Python 3.13, TypeScript frontend present but not changed for K1.
- Backend framework: FastAPI with Typer CLI.
- Build and test: `uv`, `just`, `ruff`, `mypy`, `pytest`.
- Indexed by fmm: yes. `fmm validate` reported all 359 files up to date.
- Review scope: `git diff main...HEAD`, 18 files, 590 insertions, 314 deletions.
- Final reviewed commit: `97fc276 fix: address MoE review of K1 (paths selector + nested storage inheritance)`.

## Architecture

K1 moves the default launch boundary from workspace to run:

- Default storage: `~/.transport-matters/workspaces/{slug}/{hash}/{run_id}/` via `workspace_storage(cwd, run_id)` in `api/src/transport_matters/workspace.py:98`.
- Per run lock and manifest: `run_with_workspace_manifest` locks `run_root(working_dir, run_id)` and writes the manifest there in `api/src/transport_matters/cli/launch_runtime.py:366-385`.
- Child environment: `build_launch_env` exports `TRANSPORT_MATTERS_STORAGE_DIR`, ports, run id, and CWD in `api/src/transport_matters/cli/launch_runtime.py:293-308`.
- Discovery: `manifest.read_all` scans `root/*/*/*/manifest.json` in `api/src/transport_matters/manifest.py:99-114`.
- Listing: `_list_instances` reconstructs each run dir as `{root}/{slug}/{hash}/{run_id}` and probes its lock in `api/src/transport_matters/cli/instances.py:56-64`.
- API run scope: `/api/v1/meta` reports `settings.run_id` in `api/src/transport_matters/api/v1/meta.py:102-109`; `/api/v1/exchanges` filters by that run unless history is requested in `api/src/transport_matters/api/v1/exchanges.py:135-142`.

## Key Patterns

- The lock is now a liveness beacon, not an exclusion gate. Fresh UUID run dirs make same CWD launches independent.
- Manifest removal preserves capture history. `_reap` deletes only `manifest.json`, leaving `index.jsonl`, `exchanges/`, and `lock` in place in `api/src/transport_matters/cli/instances.py:95-109`.
- The implementation avoids a central registry and uses file layout enumeration as the source of truth.
- Launch control and session discovery are separated: `TRANSPORT_MATTERS_STORAGE_DIR` remains a child session pointer for addon settings and `paths`, but no longer auto populates the outer `--storage-dir` launch option.

## Detailed Findings

### F1 resolved: `paths --workspace <storage_dir>` now selects printed run storage

Original issue: `paths` ambiguity recovery listed storage dirs but path shaped selectors were treated as CWDs, so the listed value could not be consumed.

Final state:

- `_resolve_storage` now checks path shaped selectors with `_names_known_storage(candidate)` before CWD resolution in `api/src/transport_matters/cli/paths.py:104-113`.
- `_names_known_storage` compares the candidate against every recorded manifest `storage_dir`, using resolved path equality in `api/src/transport_matters/cli/paths.py:118-129`.
- This design covers explicit `--storage-dir` runs outside the workspaces tree because it matches manifest values, not path prefixes.
- `_exit_ambiguous_runs` now tells the user to re-run `paths --workspace <storage-dir>` using one of the listed dirs in `api/src/transport_matters/cli/paths.py:214-228`.
- Regression coverage: `test_paths_workspace_flag_resolves_a_runs_storage_dir` creates two runs with explicit stores outside the workspaces tree and verifies `--workspace <store_b>` returns `store_b` in `api/src/transport_matters/cli/test_paths.py:218-245`.

### F2 resolved: nested launches do not inherit parent storage as explicit storage

Original issue: `TRANSPORT_MATTERS_STORAGE_DIR` was both the child session storage pointer and the Typer envvar for `--storage-dir`. A nested `transport-matters claude` or `codex` inside an existing session could inherit the parent storage dir and silently co-reside.

Final state:

- Both `--storage-dir` Typer options dropped `envvar="TRANSPORT_MATTERS_STORAGE_DIR"` and include a regression comment in `api/src/transport_matters/cli/__init__.py:253-270` and `api/src/transport_matters/cli/__init__.py:385-402`.
- `build_launch_env` still exports `TRANSPORT_MATTERS_STORAGE_DIR` for the managed session in `api/src/transport_matters/cli/launch_runtime.py:293-308`.
- The addon settings and `paths` env first behavior remain intact because they read the env var directly, not through the outer CLI option.
- Regression coverage: `test_start_nested_session_does_not_inherit_storage_dir` sets a parent `TRANSPORT_MATTERS_STORAGE_DIR`, launches `claude`, and verifies the child storage is a fresh per run dir in `api/src/transport_matters/cli/test_start_storage.py:71-97`.

### Documentation updated for operator recovery

- README describes per run storage under `{slug}/{hash}/{run_id}` in `README.md:90-92`.
- README explains that a bare shell with several live runs can pass one of the listed storage dirs back with `--workspace <storage-dir>` in `README.md:122-126`.

### Non gating cleanup items

- n1: With zero live runs, `_storage_for_cwd` returns the workspace container `{slug}/{hash}/`, while data is now per run. This is recoverable via slug or known storage dir and was accepted as cleanup pass work.
- n2: `--print-command` can still create an empty per run dir. Accepted as cleanup pass work.

## Verification

Commands run during final re-review:

```bash
git status --short --branch
git log --oneline -3
git diff --stat main...HEAD
git diff --name-only main...HEAD
cd api && just check && just test
fmm validate
git status --short
```

Results:

- Branch: `feat/k1-multi-instance-per-cwd`.
- Head: `97fc276 fix: address MoE review of K1 (paths selector + nested storage inheritance)`.
- `just check`: `ruff format`, `ruff check --fix`, and `mypy` all passed.
- `just test`: 931 passed in 5.83 seconds.
- `fmm validate`: all 359 files indexed and up to date.
- Final `git status --short`: clean.

## Dependencies

Critical dependencies touched by this review:

- `typer`: CLI command and option parsing, including `--workspace` and `--storage-dir` behavior.
- `fcntl`: lock liveness through `WorkspaceLock`.
- `pytest`: acceptance and regression coverage.
- `fmm`: structural navigation and index validation.

## Relevance to Helioy

The final K1 design matches the Helioy preference for isolated runs, explicit liveness, and operator visible recovery. The review found an operator contract bug and a nested launch inheritance bug, both fixed before signoff.

## Open Questions

- Should `--workspace` accept run id as a first class selector in a later cleanup pass?
- Should the zero live runs `paths` fallback point somewhere more useful than the workspace container now that default data is per run?
