---
title: Transport Matters Desktop Port Model Code Reality
type: research
tags: [transport-matters, ports, desktop, run-manager, architecture]
summary: The desktop fixed channel port model conflicts with the dynamic per run listener model already used by canvas runs.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-23
updated: 2026-06-23
---

## Executive Summary

Transport Matters already allocates dynamic per run proxy listeners for canvas spawned runs through RunManager and the shared proxy. The desktop launcher still treats stable and preview channels as fixed port pairs, which caused the observed `8788` conflict and represents a model mismatch rather than only a missing attach check.

## Project Metadata

- Language: Python 3.14 backend, TypeScript Electron desktop, React web UI.
- Backend framework: FastAPI with Typer CLI, mitmproxy, psycopg, Alembic.
- Desktop framework: Electron with TypeScript and Vitest.
- Web framework: React, Vite, TanStack Query, xterm, Zustand.
- Build entries: `api/pyproject.toml` script `transport-matters`, `desktop/package.json`, `www/package.json`.
- fmm: `.fmm.db` is present at repo root.

## Architecture

- Desktop backend launch flows through `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached`, `prepare_desktop_launch`, and `_resolve_backend_ports`.
- Channel defaults live in `api/src/transport_matters/channel-specs.json` and are loaded into `api/src/transport_matters/channel.py:ChannelSpec`.
- Canvas spawned runs flow through `api/src/transport_matters/api/v1/run_routes.py:_spawn_request`, `api/src/transport_matters/run_manager.py:RunManager._prepare_request`, and `api/src/transport_matters/shared_proxy/run_preparation.py:prepare_shared_captured_run`.
- Dynamic allocation is centered on `api/src/transport_matters/cli/ports.py:allocate_port_pair` and `api/src/transport_matters/cli/launch_runtime.py:resolve_launch_ports` when `use_channel_defaults=False`.
- Shared proxy listeners are registered through `api/src/transport_matters/shared_proxy/subprocess.py:SharedProxySubprocess.register_listener`.

## Key Patterns

- A channel should be treated as a state boundary: home, DB, Electron identity, user data, dock identity, and badge.
- Runtime ports are already actual values carried through records and route URLs, not durable identity.
- The live desktop record is the right discovery seam: `api/src/transport_matters/cli/desktop_runtime.py:DesktopRuntimeRecord` stores actual pid and ports.

## Detailed Findings

- `desktop` fixed ports are real in code: `api/src/transport_matters/cli/desktop_cmd.py:_resolve_backend_ports` uses `ChannelSpec.proxy_port` and `ChannelSpec.web_port` when no allocator is injected.
- Canvas runs are dynamic by default: `api/src/transport_matters/run_models.py:SpawnRun` defaults ports to `None` and external web runtime, and `api/src/transport_matters/api/v1/run_routes.py:_spawn_request` does not set ports.
- The shared proxy path uses dynamic listener ports: `api/src/transport_matters/shared_proxy/run_preparation.py:_binding_from_context` maps the prepared dynamic proxy port to `ProxyRunBinding.listen_port`.
- No inspected durable identity requires fixed ports across restart. Runtime record, Electron identity, and hosted route handling can all carry actual ports.
- Literal blast radius for `8787`, `8788`, `8797`, and `8798` is 40 files: 9 source or tool files, 25 tests, 5 docs or examples, and `api/uv.lock` ignored.

## Dependencies

- `fmm` provided topology, symbol outlines, dependency graphs, and symbol source.
- Focused pytest verification covered desktop fixed conflict behavior, captured run retry allocation, shared proxy registration, and RunManager shared proxy routing.

## Relevance to Helioy

This supports the Helioy principle that UI and director clients should share one API first control plane. Ports should be discoverable runtime facts, not hidden identity baked into a UI launch path.

## Open Questions

- Should standalone `claude` and `codex` launches remain channel pinned, or should they also follow dynamic default allocation as the README currently states?
- Should direct packaged Electron self start allocate ports in Electron, or should packaged launch route through the Python hosted desktop command?
- Should channel specs keep preferred port hints for dev ergonomics after runtime records become authoritative?

Primary artifact: `~/.mdx/projects/tm-ports-why--code-reality--brainstorm.md`.
