---
title: Captured Claude terminal pane (C3) implementation
type: sessions
tags: [frontend, transport-matters, captured-claude, canvas, terminal, websocket, dry]
summary: Frontend slice spawning a captured Claude Code session into a canvas pane over the C2 WebSocket seam, reusing the terminal pane via a shared useTerminalSession hook.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Built **C3** of captured-claude-in-pane: the frontend slice where the user sees
it work. A "Spawn Claude (captured)" button opens a canvas pane that runs the
same captured `transport-matters claude` launch as the CLI (reverse proxy, run
dir, owned session), bridged to an xterm pane over the C2 WebSocket seam at
`/api/captured-runs/claude/terminal`.

Branch `feat/captured-claude-pane`, HEAD `fd99790`, **PR #63**, based on
`origin/main @e014e14` (the merged C2 backend). One PR.

Key decision: **reuse over replicate**, mirroring how C2 split the backend into
shared `terminal_bridge.py` primitives + a thin `captured_terminal.py` route.
The frontend now has the same shape: one shared core, two thin variants.

## Architecture Decisions

- **Shared core hook `useTerminalSession({ buildUrl, onTextFrame })`** (new
  `terminalSession.ts`) owns the entire xterm + PTY-socket lifecycle: mount,
  fit, focus, ResizeObserver, teardown, and the involuntary-close code. It is
  the frontend analogue of backend `terminal_bridge.py`. Callbacks are held in
  refs so the mount effect stays one-shot.
- `TerminalPane.tsx` collapsed from ~90 lines to a ~25-line thin wrapper over
  the hook. Its observable behavior (URL, focus, resize, teardown, refused
  banner) is byte-identical, so its 5 existing tests pass **unchanged**.
- `CapturedClaudePane.tsx` is the second thin variant: it passes
  `capturedTerminalSocketUrl` + an `onTextFrame` that parses the typed
  `captured-run.ready` / `captured-run.error` frames, surfaces a `captured`
  badge + run id in a header, and renders an error/closed banner. It reuses the
  shared `.terminal-pane` surface for the xterm body.
- **Protocol delta isolated to one option**: `terminalSocket.ts` gained an
  optional `onTextFrame` hook. The bare terminal omits it, so inbound text
  frames stay ignored (control echoes never hit the screen). The captured
  variant opts in. Added `capturedTerminalSocketUrl(cols, rows, cwd?)` alongside
  the unchanged `terminalSocketUrl`, sharing a `socketScheme` helper.
- **Typed frame parser** `capturedRunFrames.ts` binds field-for-field to the
  backend `_ready_frame` (`runId`, `cwd`, `storageDir`, `proxyPort`, `webPort`,
  `cli`, optional `nativeSessionId`) and `captured-run.error` (`code`,
  `message`). No assumptions; validated against `captured_terminal.py`.
- **Registry / model**: new `captured-claude` `PaneContentRef` + `ViewerId`,
  registry entry (title "Claude (captured)", constant `paneId` → single-instance
  dedupe like the terminal), lazy-loaded. Both terminal-backed panes import the
  shared session core, so the bundler folds xterm into one shared chunk both
  thin chunks reference — xterm stays out of the main bundle, no duplication.
- **Lab command bar**: `addCapturedClaude` store action + a "Spawn Claude
  (captured)" button next to "Add terminal". `addTerminal` and
  `addCapturedClaude` now share one `spawnContentPane(state, ref)` helper (DRY).
  Lab-native: it renders via the shared `renderPaneContent`, so it works in
  `/canvas-lab` with no per-viewer branching.
- **cwd = workspace with zero plumbing**: the pane omits `cwd`, so the backend
  resolves `settings.cwd` (its launch workspace). `ViewerCanvasContext` carries
  no absolute cwd, so threading one would be dead plumbing for the first cut.
- **CSS co-located** in `captured-claude-pane.css` (tokens only;
  `--color-edge`/`--color-label`/`--color-accent`), `index.css` untouched. The
  cssColocation guard now scans two stylesheets and stays green.

## Performance Notes

Bundle (vite build): xterm sits in one shared `terminal-pane-*.js` chunk
(343.9 kB raw / **87.8 kB gzip**, lazy) referenced by both thin pane chunks
(`TerminalPane` 0.41 kB, `CapturedClaudePane` 1.75 kB). Captured CSS split into
its own 0.77 kB co-located asset. Main bundle unaffected (xterm loads only when
a terminal-backed pane opens).

## Deviations from Spec

- The directive said add the button "to the PRIMARY section of
  CommandBarSections.tsx". `CommandBarSections` is a generic component that
  renders whatever `primary` ReactNode it is given; the only host that builds a
  primary group is the lab route (`CanvasLabRoute.tsx`), which is also the only
  place the bare terminal is spawnable today. Added the button there, next to
  "Add terminal" — consistent with the existing pattern and lab-native, exactly
  as the directive's "works via renderPaneContent in /canvas-lab too" intends.
  `CommandBarSections.tsx` itself needed no change (its "append to primary" seam
  was already clean).

## Open Items

- No live `claude` smoke run locally (needs the `claude` binary + the mitm
  addon + a running backend + browser interaction). Per the directive's
  fallback, wiring + frame handling are proven via 18 new tests: frame parser
  (8), captured pane wiring/ready/error/refused/teardown (7), captured URL +
  `onTextFrame` routing (3). WS path + frame keys bound to the backend's own
  test ground truth.
- cwd is not yet threaded from the canvas/workspace context (backend default
  covers the single-workspace case); multi-instance dedupe is single-instance
  for now. Both deferred with the pane-owned/ephemeral first cut.
- Server-managed run-manager (panes attach/reconnect to a server-owned run)
  remains a planned slice (plan B / "server slice").

## Gates

Frontend: `lint` (biome), `typecheck` (tsc), `test` (583 pass), `build` (vite) —
all green; cssColocation green; existing terminal-pane tests unchanged. Desktop:
`typecheck`, `test` (28 pass), `build` — all green (independent of www source;
`package:smoke` is Linux/xvfb CI-only).
