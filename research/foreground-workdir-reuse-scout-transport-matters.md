---
title: Foreground Workdir Reuse Scout in Transport Matters
type: research
tags: [transport-matters, desktop, workdir, scout, runtime-recovery]
summary: The foreground reuse bug is rooted in live runtime discovery reading only meta channel, leaving workdir comparison dependent on stale record cwd.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-27
updated: 2026-06-27
---

## Executive Summary

Transport Matters desktop launch uses a shared recovery seam for foreground, detached, and Electron direct relaunch flows. The current #180 workdir switch is correctly centralized, but runtime discovery feeds it `cwd` from `DesktopRuntimeRecord` rather than live `/api/meta`, so a stale record can permit reuse of a healthy backend serving another workdir.

## Project Metadata

- Language: Python API and CLI, TypeScript Electron desktop.
- Frameworks: Typer CLI, FastAPI backend, Electron desktop, Vitest desktop tests, Pytest API tests.
- Build and gates: repo root `just check` runs desktop, www, and api checks; repo root `just test` runs desktop, www, and api tests.
- Current checkout: `transport-matters` at `0c6b0e5`; installed CLI reported `0.3.0.post1.dev156+g108183dec`; both contain `7e122de fix: switch desktop workdir on relaunch (#180)`.

## Architecture

- `api/src/transport_matters/cli/__init__.py+desktop` dispatches `--foreground` to `api/src/transport_matters/cli/desktop_cmd.py+run_desktop_launch`.
- `api/src/transport_matters/cli/desktop_cmd.py+run_desktop_launch` and `api/src/transport_matters/cli/desktop_cmd.py+run_desktop_detached` both call `api/src/transport_matters/cli/desktop_recovery.py+prepare_desktop_runtime_for_launch_or_exit` before attaching to a live runtime.
- `api/src/transport_matters/cli/desktop_recovery.py+prepare_desktop_runtime_for_launch_or_exit` owns the #180 compare through `api/src/transport_matters/cli/desktop_recovery.py+_serves_requested_work_dir`.
- `desktop/src/main.ts+runtimeServesWorkspace` gates Electron direct reuse, while `desktop/src/desktopRuntime.ts+reclaimDesktopRuntime` shells back to `_desktop-reclaim` and the same Python recovery seam.
- `api/src/transport_matters/desktop_runtime.py+discover_desktop_runtime` is the discovery seam that returns `DesktopRuntimeStatus` for all these paths.

## Key Patterns

- The elegant fix is to keep one workdir gate in `api/src/transport_matters/cli/desktop_recovery.py+prepare_desktop_runtime_for_launch_or_exit` and improve the status it receives.
- Avoid a parallel foreground check in `api/src/transport_matters/cli/desktop_cmd.py+run_desktop_launch`; that would duplicate #180 logic and leave Electron direct relaunch dependent on stale status.
- Runtime liveness should include identity checks that matter to reuse. Current discovery validates live channel but drops live cwd.

## Detailed Findings

- Existing positive coverage proves record based workdir mismatch for foreground and detached through `api/src/transport_matters/cli/test_desktop_idempotent.py+test_run_desktop_launch_reclaims_live_different_workdir_before_serving` and `api/src/transport_matters/cli/test_desktop_idempotent.py+test_run_desktop_detached_reclaims_live_different_workdir_before_start`.
- Existing Electron coverage proves direct relaunch rejects a live status whose `cwd` is already different through `desktop/src/main.reclaim.test.ts` and `desktop/src/main.ts+runtimeServesWorkspace`.
- The bug shaped gap is a stale status case: record cwd matches requested cwd, while live `/api/meta.cwd` reports another cwd. `api/src/transport_matters/desktop_runtime.py+_read_runtime_meta_channel` cannot represent that because it parses only channel.
- `api/src/transport_matters/api/v1/meta.py+get_meta` already exposes the authoritative backend cwd. The discovery seam should consume it.
- Targeted verification run: `cd api && uv run python -m pytest src/transport_matters/cli/test_desktop_idempotent.py::test_run_desktop_launch_reclaims_live_different_workdir_before_serving src/transport_matters/cli/test_desktop_idempotent.py::test_run_desktop_detached_reclaims_live_different_workdir_before_start -q` returned `2 passed`.
- Targeted verification run: `cd desktop && pnpm vitest run src/main.reclaim.test.ts` returned `1 passed` file and `2 passed` tests.

## Dependencies

- `api/src/transport_matters/desktop_runtime.py+probe_desktop_liveness` supplies health status for runtime discovery.
- `api/src/transport_matters/api/v1/meta.py+get_meta` supplies live backend identity, including cwd and channel.
- `desktop/src/desktopRuntime.ts+readDesktopRuntimeStatus` consumes the Python `channel status --json` output, so fixing Python discovery improves Electron direct reuse without a TypeScript duplicate.

## Relevance to Helioy

This preserves the Helioy preference for one canonical seam and no duplicate policy. Workdir switching should stay in the existing #180 recovery path, with runtime discovery upgraded to provide live cwd evidence.

## Open Questions

- Confirm the exact stale record sequence from the first hand report, especially whether the record cwd matched the requested cwd while `/api/meta.cwd` differed.
- Decide whether live meta cwd absence should make live reuse fail closed or fall back to record cwd for legacy backends.
