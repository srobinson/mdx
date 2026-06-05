---
title: Session Canvas FE Spec
type: sessions
tags: [frontend, transport-matters, session-canvas, spec]
summary: Authored and revised the F1 to F2 frontend spec for the Transport Matters session canvas.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

## Summary

Authored `/Users/alphab/.mdx/projects/transport-matters-session-canvas/fe-spec.md` for the session canvas frontend, revised it after the orchestrator decided that F1 and F2 keep the launched agent interactive in the user's terminal, then applied FE architect round 1 fixes. The canvas opens beside the terminal as observability and replay, auto resolves the launched run, and spawns the live transcript chat pane while the picker browses other sessions in the working directory.

## Architecture Decisions

- The desktop entry opens `/canvas`; the legacy single page wire UI remains in the codebase for direct development access.
- The Python desktop process owns the foreground interactive agent for F1 and F2. Electron does not spawn or embed the terminal.
- The canvas consumes `CanvasLaunchContext` and resolves the launched run with `GET /api/sessions?owner=local&workspace_hash={hash}&cli={agent}`, preferring `run_id` when present.
- The generic layout engine lives under `www/src/engine/**` and must stay content agnostic through a boundary lint.
- Engine pane state is `PaneNode` only: pane id, geometry, lifecycle, z order, and pinned state. Session canvas content state is `PaneRecord`: viewer id, content ref, title, and chrome state.
- Engine `PaneFrame` owns geometry, motion, and gesture plumbing. Session canvas `PaneWindow` owns title, badges, controls, and viewer chrome.
- F1 viewers are `session-picker` and `transcript-chat`; future TUI, wire, file, and image viewers use the same registry seam.
- Transcript panes are keyed by `session_id` and stream events by `seq`; the legacy exchange stream reducer is not reused.
- Persisted session event IR is `NormalizedTurn` JSON. Transcript rendering branches on `kind`, renders turn `ir.parts` under `event.role`, treats meta events as metadata, and handles artifact redacted image blocks.
- Session query keys are centralized in `www/src/lib/queryKeys.ts`.
- The layout planner realigns unpinned panes on spawn and close, with floating in F1 and tiling plus focus in F2.

## Performance Notes

The spec moves the transition stress harness into F1. The harness opens `/canvas?stress=1`, drives synthetic panes through spawn, close, focus, drag, resize, pan, and zoom, then records frame timing. F2 extends the same harness for tiling and mode switches.

## Deviations from Spec

No intentional deviations from the session canvas charter. The post draft charter decision supersedes the earlier assumption that the picker is the only initial pane. The picker now mounts immediately, and launch resolution may spawn the live transcript pane without a picker click. Terminal, wire, file, and image panes remain explicit F3 seams.

## Open Items

- FE architect round 2 verification of `/Users/alphab/.mdx/projects/transport-matters-session-canvas/fe-spec.md`.
- Orchestrator decision on production direct path support for `/canvas` versus a hash route fallback.
- Final transport for `CanvasLaunchContext`, query params or preload IPC.
- Orchestrator decision on whether F2 persists layout or only defines the storage adapter pending desktop persistence work.
