---
title: Transport Matters Q1 multi instance boundary verification
type: research
tags: [transport-matters, architecture, multi-instance, run-id, storage]
summary: Verifies the same working directory multi instance boundary and corrects stale branch merge claims.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Executive Summary

Transport Matters is a mitmproxy based control plane for Claude Code and Codex traffic. Q1 is mostly confirmed: the live same directory hard gate is the workspace `fcntl.flock`, and the data model already carries `run_id` through launch, API metadata, storage entries, events, and default UI filtering. The substantive correction is branch provenance: the named local feature branch tips are not ancestors of `main`; their relevant work is present on `main`, but two branch histories remain stale and divergent.

## Project Metadata

- Language: Python 3.12 plus TypeScript.
- Backend framework: FastAPI, Uvicorn, mitmproxy addon, Typer CLI.
- Frontend framework: Vite 8, React 19, TypeScript, TanStack Query, Zustand.
- Build system: `uv` with Hatchling and Hatch VCS for the Python package; pnpm for `www` and `desktop`.
- Key dependencies: `fastapi[standard]`, `pydantic-settings`, `httpx`, `mitmproxy`, `aiofiles`, `typer`, `@tanstack/react-query`, `zustand`.
- Indexing: `.fmm.db` is present and `fmm validate` reports all 352 files indexed and up to date.

## Architecture Relevant To Q1

### Launch and process shape

`run_start` and `run_codex` both resolve a working directory, allocate or validate ports, resolve a storage directory, create a fresh `run_id`, then run under `run_with_workspace_manifest` (`api/src/transport_matters/cli/start_cmd.py:196-207`, `api/src/transport_matters/cli/start_cmd.py:255-261`, `api/src/transport_matters/cli/codex_cmd.py:331-342`, `api/src/transport_matters/cli/codex_cmd.py:397-403`).

`build_launch_env` sends `TRANSPORT_MATTERS_STORAGE_DIR`, `TRANSPORT_MATTERS_WEB_PORT`, `TRANSPORT_MATTERS_PROXY_PORT`, `TRANSPORT_MATTERS_RUN_ID`, and `TRANSPORT_MATTERS_CWD` into the child addon process (`api/src/transport_matters/cli/launch_runtime.py:280-295`).

### Workspace identity and singleton root

`workspace_id` derives `{slug}/{hash}` from the resolved CWD (`api/src/transport_matters/workspace.py:55-65`). `workspace_root` maps that identity to `~/.transport-matters/workspaces/{slug}/{hash}` (`api/src/transport_matters/workspace.py:68-75`). `workspace_storage` deliberately returns the same path and creates it (`api/src/transport_matters/workspace.py:78-96`).

The manifest module documents the current per workspace layout as one `lock` file and one `manifest.json` under `{slug}/{hash}` (`api/src/transport_matters/manifest.py:8-16`).

## Detailed Findings

### 1. Hard gate assessment

Confirmed. The only same CWD live process hard gate found is `WorkspaceLock.__enter__`, which opens `{workspace_root}/lock` and attempts `fcntl.flock(fd, LOCK_EX | LOCK_NB)` (`api/src/transport_matters/lock.py:68-88`). `run_with_workspace_manifest` acquires that lock at `workspace_root(working_dir)` before it writes the manifest and runs the launch lifecycle (`api/src/transport_matters/cli/launch_runtime.py:347-376`).

`WorkspaceLock.is_held` is a read only liveness probe. It opens the same lock file without creating it, tries the same non blocking flock, and releases immediately when it can acquire (`api/src/transport_matters/lock.py:103-125`). That supports `list` and `paths`; it is not another launch gate.

No pidfile gate was found. The only production PID use surfaced by fmm is `Manifest.pid` (`api/src/transport_matters/manifest.py:40-49`), and `instances` prints it from the advisory manifest (`api/src/transport_matters/cli/instances.py:45-79`).

### 2. Ports and sockets

Confirmed with qualification. Ports are not a same CWD gate unless the user pins colliding values.

`allocate_port_pair` binds two sockets to `127.0.0.1:0`, reads the kernel selected ports, and returns distinct values (`api/src/transport_matters/cli/ports.py:41-79`). `resolve_launch_ports` only fails fast for user supplied ports that are already listening (`api/src/transport_matters/cli/launch_runtime.py:195-235`).

The proxy and web sockets bind fixed host `127.0.0.1` but variable ports. Claude mode passes `--listen-port <proxy_port>` to mitmdump (`api/src/transport_matters/cli/start_cmd.py:124-134`), Codex mode does the same (`api/src/transport_matters/cli/codex_cmd.py:208-218`), and the addon starts Uvicorn with `settings.web_port` (`api/src/transport_matters/addon_runtime.py:43-52`).

### 3. Process local singletons

No additional cross process gate was found, but several process local singletons matter for product design.

- `get_settings` is `@lru_cache` and reads process environment once (`api/src/transport_matters/config.py:57-59`). Each launch creates a separate mitmdump process with its own environment, so this does not block two same directory instances after a path split. One process cannot host multiple run identities without refactoring settings scope.
- Storage is a module level singleton: `_backend` plus `_init_lock` (`api/src/transport_matters/storage/__init__.py:28-52`). It is per process. It would not prevent two processes if their roots differ. It would be unsafe if roots are shared, because index locking is only an `asyncio.Lock` inside one backend (`api/src/transport_matters/storage/disk.py:42-53`, `api/src/transport_matters/storage/disk.py:223-255`).
- The mitmproxy addon singleton `addons = [TransportMattersAddon()]` is per mitmdump process (`api/src/transport_matters/addon.py:56-97`). It keeps one `AddonRuntime`, which starts one Uvicorn server on the chosen web port (`api/src/transport_matters/addon_runtime.py:27-53`).
- Breakpoint state is process local: `_mode`, `_paused`, `_lock`, and `_pause_serializer` (`api/src/transport_matters/breakpoint.py:54-60`). This is compatible with per instance UI, not with a shared aggregated UI without a coordinator.
- SSE state is process local: `_subscribers` and `_next_id` (`api/src/transport_matters/broadcast.py:17-27`). Events only fan out inside the serving process (`api/src/transport_matters/broadcast.py:36-46`).
- Track state is process local but keyed by `run_id` inside the manager (`api/src/transport_matters/track_manager.py:98-106`, `api/src/transport_matters/track_manager.py:194-205`, `api/src/transport_matters/track_manager.py:462-466`).
- `ProcessSupervisor` tracks children in an instance dictionary and prevents duplicate names only inside that supervisor (`api/src/transport_matters/supervisor.py:120-130`, `api/src/transport_matters/supervisor.py:149-194`). Child names such as `mitmdump` and `codex` are not system wide.

### 4. Shared artifacts beyond the headline list

The lock, manifest filename, and storage root are the important workspace singletons. One additional shared artifact should be called out explicitly: `mitmdump.log` is fixed at `storage_dir / "logs" / "mitmdump.log"` (`api/src/transport_matters/cli/runner.py:512-539`). If two instances share `storage_dir`, their background mitmdump logs append to the same file. A `{hash}/{run_id}/` storage split fixes this because the log path follows `storage_dir`.

Disk storage itself is run aware in data, but root shared in layout. `DiskStorageLayout` writes one `index.jsonl`, one `index.jsonl.tmp`, and flat exchange directories below `root` (`api/src/transport_matters/storage/disk_layout.py:47-83`). `persist_exchange` rewrites the shared index under a process local lock (`api/src/transport_matters/storage/disk.py:223-255`).

### 5. `run_id` threading

Confirmed. `run_id` already threads through the runtime path.

- Created by `new_run_id` as a UUID (`api/src/transport_matters/cli/launch_runtime.py:270-272`).
- Passed to both launch modes and into the manifest wrapper (`api/src/transport_matters/cli/start_cmd.py:207-261`, `api/src/transport_matters/cli/codex_cmd.py:342-403`).
- Exported as `TRANSPORT_MATTERS_RUN_ID` (`api/src/transport_matters/cli/launch_runtime.py:280-295`).
- Stored on the advisory manifest (`api/src/transport_matters/manifest.py:32-49`, `api/src/transport_matters/cli/launch_runtime.py:352-367`).
- Exposed through `/api/v1/meta` (`api/src/transport_matters/api/v1/meta.py:84-113`).
- Written into `IndexEntry.run_id` for HTTP, HTTP provisional, Codex websocket, Codex provisional, Codex finalization, and Codex handshake failures (`api/src/transport_matters/storage/base.py:117-145`, `api/src/transport_matters/exchange_recorder.py:284-331`, `api/src/transport_matters/exchange_recorder.py:352-393`, `api/src/transport_matters/exchange_recorder.py:488-537`, `api/src/transport_matters/codex/exchange.py:97-163`, `api/src/transport_matters/codex/exchange.py:225-291`, `api/src/transport_matters/codex/exchange.py:530-560`).
- Used by `/api/v1/exchanges`; the default list filters to `get_settings().run_id`, and `include_history=true` removes that filter (`api/src/transport_matters/api/v1/exchanges.py:127-148`, `api/src/transport_matters/storage/disk.py:257-271`).
- Surfaced in frontend metadata and used as the current session key (`www/src/api.ts:313-330`, `www/src/app.tsx:35-112`).

Correction to the draft: pushing the storage root down to `{hash}/{run_id}/` is not a pure path helper change because `run_id` is currently created after `resolve_storage_dir` in both launch modes (`api/src/transport_matters/cli/start_cmd.py:203-207`, `api/src/transport_matters/cli/codex_cmd.py:338-342`). The launch order or `resolve_storage_dir` signature must change.

### 6. Branch inspection

The draft claim that all three named branch histories are already merged into `main` is too strong.

Observed commands:

```text
git log --oneline main..feat/multi-instance
git diff --stat main..feat/multi-instance
git log --oneline main..feat/multi-instance-phase2
git diff --stat main..feat/multi-instance-phase2
git log --oneline main..feat/run-id-boundary
git diff --stat main..feat/run-id-boundary
git cherry -v main <branch>
```

Results:

- `feat/multi-instance`: local branch only, tip `0c6bdbf`, not an ancestor of `main`, 14 commits ahead, `git diff --shortstat main..feat/multi-instance` reports 410 files changed. `git cherry -v main feat/multi-instance` marks the listed commits with `+`, so the branch history is not patch equivalent to `main` by Git's patch id check.
- `feat/multi-instance-phase2`: local branch only, tip `487b178`, not an ancestor of `main`, 22 commits ahead, `git diff --shortstat main..feat/multi-instance-phase2` reports 412 files changed. `git cherry` marks the shown commits with `+`.
- `feat/run-id-boundary`: local branch only, tip `52acc19`, not an ancestor of `main`, one commit ahead, large tree diff against `main`, but `git cherry -v main feat/run-id-boundary` marks that commit with `-`, meaning the patch is already equivalent to work on `main`.

Functional provenance still supports the draft's broad direction: `main` contains `2aa9fe8 feat: own the claude process + multi-instance support (#4)` and `7b16d9b feat: add per-run manicure session boundary (#8)`. The exact correction is that feature work exists on `main`, but the named branch histories are stale or divergent and should not be described as cleanly merged.

## Real Blast Radius For `{hash}/{run_id}/`

Expected code surface:

1. Launch ordering. Generate `run_id` before default storage resolution, or pass it into `resolve_storage_dir` (`api/src/transport_matters/cli/start_cmd.py:203-207`, `api/src/transport_matters/cli/codex_cmd.py:338-342`, `api/src/transport_matters/cli/launch_runtime.py:238-240`).
2. Workspace storage policy. Change the default returned by `workspace_storage` from `{slug}/{hash}` to `{slug}/{hash}/{run_id}` or an equivalent run scoped directory, while preserving explicit `--storage-dir` semantics (`api/src/transport_matters/workspace.py:78-96`).
3. Lock and manifest policy. `WorkspaceLock` currently binds `lock` and `manifest.json` to the workspace root (`api/src/transport_matters/lock.py:68-72`). To allow same CWD concurrency, either remove the workspace level launch lock, replace it with a per run lock, or use a brief registry lock only for manifest publication.
4. Instance discovery. `read_all` currently scans exactly `root/*/*/manifest.json` (`api/src/transport_matters/manifest.py:95-109`). `_list_instances` rebuilds `ws_dir` from `m.slug/m.hash` and probes one workspace lock (`api/src/transport_matters/cli/instances.py:82-109`). `_reap` deletes `ws_dir/manifest.json` (`api/src/transport_matters/cli/instances.py:127-142`). These must understand multiple manifests per workspace.
5. Path resolution. `paths` assumes a live manifest at `ws_root/manifest.json` and a slug scan of `{slug}/*/manifest.json` (`api/src/transport_matters/cli/paths.py:104-115`, `api/src/transport_matters/cli/paths.py:118-179`). A multi run layout needs a run selector, an active instance disambiguation rule, or a clear error on same CWD multiple live instances.
6. Tests and docs. The direct dependent graph points at `workspace.py`, `manifest.py`, `lock.py`, `storage/disk_layout.py`, `storage/__init__.py`, and their CLI/API tests. Targeted tests that currently cover this surface include lock, start storage, instances, exchanges list, and meta.

The backend storage code is otherwise close to ready. `DiskStorageBackend` accepts any root (`api/src/transport_matters/storage/disk.py:42-53`), `IndexEntry.path` is already relative to the storage root (`api/src/transport_matters/exchange_recorder.py:289-302`, `api/src/transport_matters/codex/exchange.py:246-263`), and the API list filter already defaults to the current `run_id` (`api/src/transport_matters/api/v1/exchanges.py:127-148`).

## Web UI Fork Assessment

The per instance versus aggregated web UI question is a real design fork.

Per instance UI is the low blast radius path. Current architecture already starts one Uvicorn server per mitmdump addon process, on that instance's `web_port` (`api/src/transport_matters/addon_runtime.py:43-52`). The frontend fetches metadata from that backend and keys UI state by `meta.runId` (`www/src/api.ts:313-330`, `www/src/app.tsx:35-112`). SSE also remains simple because events are process local (`api/src/transport_matters/api/v1/stream.py:17-39`, `api/src/transport_matters/broadcast.py:17-46`).

Aggregated UI requires new architecture. It would need to discover all live manifests, open or proxy to multiple storage roots, merge indexes from multiple `index.jsonl` files, route breakpoint actions to the correct process, and fan in SSE from multiple process local broadcasters. Current process globals in settings, storage, breakpoint, broadcast, and track manager are compatible with one instance per web server, not one web server supervising several runs.

## Dependencies

- `fcntl.flock`: kernel held workspace liveness gate.
- `mitmproxy`: proxy runtime and addon host.
- `uvicorn` and FastAPI: in process web UI/API server.
- `pydantic-settings`: environment backed process configuration.
- `aiofiles` and thread pool file IO: disk storage implementation.
- React, TanStack Query, Zustand: frontend state and API flow.

## Relevance to Helioy

This validates a useful Helioy pattern: `run_id` is already the right logical boundary, but filesystem layout and process ownership must match it. The safest next step is to split default storage and manifests by run, keep UI per instance, and defer aggregation until there is an explicit multi process coordinator.

## Open Questions

1. Should explicit `--storage-dir` remain caller owned and therefore allow deliberate sharing, or should the CLI append `run_id` under explicit roots too?
2. Should same CWD `paths` return the newest live run, require `--run-id`, or show all live runs?
3. Should instance discovery use per run manifest directories, manifest filenames scoped by run id, or a workspace registry file guarded by a short lock?

## Verification

- `fmm validate`: all 352 files indexed and up to date.
- Targeted tests: `uv run python -m pytest src/transport_matters/test_lock.py src/transport_matters/cli/test_start_storage.py src/transport_matters/cli/test_instances.py src/transport_matters/api/v1/test_exchanges_list.py src/transport_matters/api/v1/test_meta.py -q`, 35 passed in 0.99s.
- Branch inspection: `git log`, `git diff --shortstat`, `git cherry -v`, `git merge-base --is-ancestor` on `feat/multi-instance`, `feat/multi-instance-phase2`, and `feat/run-id-boundary`.
