---
title: Transport Matters desktop port audit mechanics
type: research
tags: [transport-matters, desktop, ports, relaunch, electron, cli]
summary: Desktop port reclaim currently exists in detached recovery and just channel-restart, while foreground and direct Electron paths still raw-error on occupied fixed ports.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-24
updated: 2026-06-24
---

# Executive Summary

Transport Matters desktop launch uses channel fixed ports and a per channel runtime record. Detached CLI launch has discovery and record based recovery, but foreground CLI and direct Electron backend launch still reach the raw port check without reclaim.

The detailed scout report requested by the orchestrator is at `/Users/alphab/.mdx/projects/tm-port-audit-mechanics.md`.

# Project Metadata

Language: Python for API and CLI, TypeScript for Electron desktop. Build and gate surface: root `justfile`; desktop package uses `pnpm` and Electron.

# Architecture

Relevant launch owners:

1. `api/src/transport_matters/cli/__init__.py:desktop` splits foreground and detached launch.
2. `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_launch` serves foreground without discovery.
3. `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached` uses `discover_desktop_runtime` before launch.
4. `desktop/src/main.ts:registerAppLifecycle` performs partial discovery through `transport-matters channel status`, then either attaches or spawns `_desktop-backend`.
5. root `justfile:channel-restart` performs explicit record based stop, database ensure, then detached launch.

# Key Patterns

Runtime identity is channel keyed by default. `api/src/transport_matters/channel.py:ChannelSpec` owns fixed ports, `api/src/transport_matters/storage_roots.py:default_storage_root` maps channel to home, and `api/src/transport_matters/desktop_runtime.py:desktop_record_path` stores `runtime/desktop.json` inside that root.

# Detailed Findings

See `/Users/alphab/.mdx/projects/tm-port-audit-mechanics.md` for the full matrix. In short, reclaim exists in `api/src/transport_matters/cli/desktop_recovery.py:recover_desktop_runtime_or_exit`, `force_restart_desktop_runtime_or_exit`, and `api/src/transport_matters/cli/channel_cmd.py:stop`. It is missing before `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_launch` and before Electron direct child startup in `desktop/src/main.ts:startBackendAndCreateWindow`.

# Dependencies

Critical dependencies for this audit: Typer CLI, Electron main process, uvicorn backend, and the loopback health endpoint.

# Relevance to Helioy

This maps the stable and preview desktop singleton behavior that gates local operator workflows. It identifies the smallest seam for making relaunch reclaim the fixed channel port consistently.

# Open Questions

1. Should `transport-matters desktop` default to restart instead of attach when a healthy same channel runtime exists?
2. Should non Transport Matters port owners be killed, or should the product show a typed refusal after record based reclaim fails?
3. Should foreground and Electron direct launches write runtime records, or should they delegate runtime ownership to the detached CLI parent?
