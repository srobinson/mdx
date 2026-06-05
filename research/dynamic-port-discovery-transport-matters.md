---
title: Dynamic Port Discovery in Transport Matters
type: research
tags: [transport-matters, desktop, ports, discovery, architecture]
summary: Dynamic desktop ports are feasible through a durable per-channel runtime record exposed as a shipped discovery surface.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-23
updated: 2026-06-23
---

## Executive Summary

Transport Matters can move from fixed desktop ports to dynamic ports if the per-channel desktop runtime record becomes the stable addressability contract. The decisive seam is `api/src/transport_matters/cli/desktop_runtime.py:read_live_desktop_record`, promoted into a JSON discovery surface before any HTTP client tries to connect.

The canvas run path already proves dynamic allocation and port recording in product code. The desktop channel path needs a durable per-channel discovery view, plus targeted consumer flips away from fixed constants.

## Project Metadata

- Language: Python, TypeScript, React, Electron.
- Backend framework: FastAPI.
- Frontend framework: React with Vite.
- Desktop shell: Electron.
- Indexed topology: 876 files, 142,293 LOC.
- Major areas: `api` 453 files, `www` 408 files, `desktop` 15 files.
- Current revision inspected: `e3aaecf`.

## Architecture

### Current channel model

`api/src/transport_matters/channel.py:ChannelSpec` treats `proxy_port` and `web_port` as required channel fields. `api/src/transport_matters/config.py:Settings` also defaults to `8787` and `8788`. Electron startup in `desktop/src/main.ts:resolveBackendStartupOptions` reads env overrides first, then falls back to `DesktopChannelSpec.proxyPort` and `DesktopChannelSpec.webPort`.

### Existing runtime record

`api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord` already persists `channel`, `pid`, `proxy_port`, `web_port`, `log_path`, and `started_at`. `desktop_record_path` resolves the durable location. `write_desktop_record` writes the record atomically. `read_live_desktop_record` validates the pid and unlinks stale records.

This is the correct discovery substrate. The record path should be the well-known channel address. The TCP ports should be runtime facts inside the record.

### API meta limit

`api/src/transport_matters/api/v1/meta.py:MetaResponse` returns project and channel metadata after the backend has already been reached. Extending it can confirm runtime facts after connection, but cannot bootstrap discovery because clients need the port first.

## Key Patterns

### Dynamic allocation already exists

The captured run path already allocates and records dynamic ports:

- `api/src/transport_matters/cli/ports.py:allocate_port_pair` returns two free loopback ports.
- `api/src/transport_matters/cli/launch_runtime.py:resolve_launch_ports` supports dynamic allocation when `use_channel_defaults=False`.
- `api/src/transport_matters/shared_proxy/run_preparation.py:prepare_shared_captured_run` enters that dynamic path.
- `api/src/transport_matters/shared_proxy/run_preparation.py:_finish_shared_preparation` writes run manifests, registers bindings, and returns selected ports in `CapturedRunSpawnSpec`.
- `api/src/transport_matters/run_models.py:ManagedRun.view` includes `proxy_port` and `web_port` in the internal managed run view.

The channel path should adopt the allocation, record, discover sequence. It should not reuse `RunManager` as the channel registry because `RunManager` is process resident and run scoped.

### Consumers split by discovery ability

- Hard consumer: `desktop/src/main.ts:resolveBackendStartupOptions` currently starts from fixed env or channel spec ports.
- Hard consumer: `desktop/src/window.ts:DEFAULT_WEB_PORT` remains a fixed fallback, although `rendererUrlForPort` already accepts any port.
- Soft consumer: `www/vite.config.ts:server.proxy` is dev only and startup-time only.
- Hard consumer: `api/src/transport_matters/channel.py:ChannelSpec` encodes ports as part of channel config.
- Hard consumer: director and MCP clients currently have no shipped bootstrap discovery surface.
- Easy consumer: `api/src/transport_matters/cli/channel_cmd.py:list_channels` already touches the record and can report live ports.

## Detailed Findings

### Discovery seam

Add a discovery model in `api/src/transport_matters/cli/desktop_runtime.py`, for example `DesktopRuntimeStatus`, built from `read_live_desktop_record`. It should return absent, live, stale, or unhealthy state plus `apiBaseUrl` and `rendererUrl` derived from the live `web_port`.

Expose it through a process-external JSON surface such as `transport-matters channel status <channel> --json` or `transport-matters desktop status --json`. The director should consume that JSON before making HTTP calls.

### Vite dev proxy

`www/vite.config.ts:server.proxy` points `/api` at `http://localhost:8788`. Vite evaluates this at dev server startup, so runtime discovery inside the SPA cannot fix the proxy target.

This is dev only. The shipped SPA uses relative API paths through `www/src/api.ts:apiUrl` and reaches the backend same-origin after Electron opens `http://127.0.0.1:{webPort}/canvas`.

Best path: make the Vite proxy target env driven and add a dev wrapper that reads the desktop runtime status before launching Vite.

### Minimal slice

1. Add `DesktopRuntimeStatus` and `discover_desktop_runtime(...)` in `desktop_runtime.py`.
2. Add JSON status in `channel_cmd.py` or the desktop command group.
3. Make `desktop_cmd.py` idempotent: live healthy record opens a hosted viewer, stale or unhealthy starts normally, unrelated listener remains a bind error.
4. Allocate dynamic ports by default only in the CLI desktop launch path, preserving explicit pins.
5. Update `list_channels` to show live ports from the record.
6. Add tests for status JSON, stale cleanup, attach behavior, dynamic defaults, and explicit pins.

## Dependencies

Critical dependencies are mostly internal:

- `desktop_runtime.py` for record storage and liveness.
- `ports.py` for dynamic port allocation.
- `launch_runtime.py` for bind behavior and pinned versus dynamic semantics.
- `shared_proxy/run_preparation.py` and `run_manager.py` as the working product example of dynamic port allocation.
- `desktop/src/main.ts` and `desktop/src/window.ts` for Electron URL construction.
- `www/vite.config.ts` for dev proxy behavior.

## Relevance to Helioy

This supports the Helioy direction that identity should come from durable runtime records and workspace semantics, while transient network addresses remain runtime facts. It also preserves singleton control-plane behavior per channel, which prevents split-brain desktop launches without requiring fixed ports.

## Open Questions

- Should the user-facing command be `channel status --json`, `desktop status --json`, or both?
- Should `ChannelSpec` ports be renamed to defaults first, or removed from the runtime identity contract in one break?
- Should packaged direct Electron read the record directly in TypeScript, or should the Python CLI remain the only supported launcher for dynamic channels?
