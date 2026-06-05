# Transport Matters — Session Canvas (charter)

Orchestrator-authored from a design chat. The panel fleshes this into buildable
F1-F2 specs. Settled decisions are not up for relitigation; ground them in the
actual repo + the parked cockpit design, fill the open questions, harden. Read
this instead of the chat.

## North star

The desktop entry is an infinite-canvas cockpit, NOT the legacy single-page UI.
`transport-matters desktop` boots into a new route: a full-screen, pannable and
zoomable infinite surface (a "canvas") on which floating window panes live. This
is also the layout-engine testbed for littleorgans at scale, so the engine must
be content-agnostic and reusable, not chat-specific.

## Settled decisions (build on these)

- New route, legacy hidden. `transport-matters desktop` opens the canvas route.
  The existing wire/exchange single-page UI is NOT shown on load. Keep its code
  (we may cannibalize parts); do not delete it; it is simply not the entry point.
- Canvas = working dir. One canvas is one screen bound to one working dir
  (workspace). The surface is infinite, pannable, zoomable. Multiple canvases
  exist and are switchable; one per working dir. F1 may ship a single canvas, but
  the domain model must allow N from the start.
- Canvas tech = DOM, not pixels. The infinite "canvas" is a CSS-transformed
  pannable/zoomable DOM surface (tldraw / react-flow style); each pane is a real
  React component (it must host markdown chat now and a real terminal later). It
  is NOT an HTML5 `<canvas>` 2D pixel context.
- Floating window panes. Panes float on the canvas: spawn / close / focus / move
  / resize. The FIRST pane on a session canvas is a session-picker pane.
- Picker -> spawn. Selecting a session in the picker spawns a new transcript-chat
  pane for that session. Many session panes cohabit one canvas.
- Layout manager. As panes spawn / close, a layout manager realigns all panes
  into the most efficient layout, with beautiful transitions. Tmux-like tiling +
  floating + focus modes (per the layout-lab charter).
- Content-agnostic engine + viewer registry. The layout/pane engine manages
  panes, not "chat panes". Pane content is a viewer resolved from a registry:
  session-picker and transcript-chat now; real TUI, wire, and auto-spawned
  file/image viewers later. This boundary is load-bearing (littleorgans reuse).
- Web-first in www/, Electron is a shell. Built as a new route in the existing
  www/ React app (local-first web). `transport-matters desktop` (Electron) loads
  that route. Hosting is just deploying the server.
- Data source = the shipped session store (slices 1-3). Picker =
  `GET /api/sessions?owner`. Chat backlog = `GET /api/sessions/{id}/events?owner`.
  Live append = `GET /api/sessions/{id}/events/stream` (SSE, subscribe-first,
  dedup by seq, catch-up-on-reconnect). owner = 'local'. Render from the event IR
  (`api/src/transport_matters/ir.py` blocks: Text/Tool/ToolResult/Thinking/Image/
  Unknown + role). Do NOT reuse the legacy `www/src/hooks/exchangeStreamEvents.ts`
  reducer (it ignores transcript events and reads a module-global singleton; see
  review-frontend.md findings 3-4). This is a fresh transcript stream.

## Desktop CLI (investigate + design — CLI author owns this)

- `transport-matters desktop` defaults to the claude agent.
- `transport-matters desktop --agent claude|codex` selects the agent.
- Beyond `--agent`, `desktop` MUST accept the SAME flags that
  `transport-matters claude` / `transport-matters codex` accept (notably
  `--work-dir`, and the rest of the per-agent launch flag set).
- TASK: investigate whether the existing claude/codex flag definitions + launch
  flow can be REUSED by a new `desktop` command. Ground in
  `api/src/transport_matters/cli/{launch_profile,start_cmd,launch_runtime}.py`
  (the `LaunchProfile` ABC + `ClaudeLaunchProfile`/`CodexLaunchProfile` +
  `prepare_managed_session`, the slice-5c DRY launch-profile port). If the flags
  can be reused, specify exactly how `desktop` composes them (a shared option
  group / parent parser; `--agent` -> `LaunchProfile` resolution). If they cannot
  be reused as-is, propose the MINIMAL refactor to make them reusable (DRY: zero
  duplicated flag definitions), then specify `desktop` on top. `--work-dir` is the
  bridge to the canvas=working-dir model: desktop's work-dir IS the canvas's
  working dir.

### DECIDED (orchestrator, post-draft): terminal stays interactive in F1-F2

In F1-F2, `transport-matters desktop` launches the agent INTERACTIVE in the user's
terminal exactly like `transport-matters claude`/`codex` do today, AND opens the
Electron canvas as an observability + replay window alongside it (live
transcript-to-chat of the running run + the history picker). The user types to the
agent in the terminal; the canvas is the rich read surface. The "real TUI as a
canvas pane" (the original pane-2) is deferred to F3.

Process topology consequence (CLI author, revise the launch-design section): the
Python `desktop` process is PRIMARY in the terminal and owns the agent foreground
(stdin/TTY -> agent), reusing today's foreground launch. It additionally spawns
Electron as a DETACHED canvas viewer pointed at the already-running web backend.
Electron does NOT own or spawn the agent child; it only loads the canvas route at
the web port and learns ports/run identity from the startup-JSON line + manifest.
Everything else in cli-spec.md (flag-alias extraction, --work-dir migration, the
port-allocation retry insight, startup-JSON contract, canvas lookup rule) stands.

### RATIFIED open questions (Stuart, F1-F2)

1. `/canvas` is a REAL route. Add the small SPA catch-all fallback (serve
   index.html for non-`/api`, non-asset paths) so a hard load of `/canvas`
   resolves to the app shell. No hash route.
2. `CanvasLaunchContext` via query params first; keep a thin adapter so a preload
   IPC can supply the same object later.
3. Layout persistence deferred. In-memory layout/canvas state uses Zustand (the
   app already uses it in `www/src/stores/{uiStore,overlaysStore}.ts`, v5 with the
   `persist` middleware). The deferral seam is Zustand `persist`'s `storage`
   config (localStorage now, IndexedDB later); F2 decides whether to enable
   persist + which backend. No separate hand-rolled adapter; this reuses the
   existing store pattern, no overcomplication.
4. Transcript `thinking` blocks render COLLAPSED by default; per-block expansion
   remembered in UI state (`session_id:seq:blockKey`).
5. F1 = one EventSource per transcript pane, closed with the pane; F2 may
   consolidate streams by `session_id`.

## Scope

IN (F1-F2): the canvas route + infinite DOM surface; the floating-pane window
system; the layout manager + transitions; the viewer registry; the session-picker
pane; the transcript-chat pane (IR->chat + SSE live append); the desktop CLI flag
reuse.

FUTURE (F3+ — design the seam, do NOT build): multi-canvas / working-dir
switching + persistence; more viewers (real TUI pane, wire pane, auto-spawned
file/image viewers from tool responses); focus modes + configurable tiled
layouts; fork / share / eval UI.

## Reuse, do not reimplement

- The parked cockpit spec (`transport-matters-desktop-cockpit-spec.md`, ~1236
  lines) and the layout-lab charter (`transport-matters-desktop-cockpit/
  CHARTER.md`) already designed the layout engine, viewer registry, FLIP
  transitions, and workspace-per-canvas. Ground F1-F2 in them and reconcile
  against the now-shipped session store. That spec was parked pending the
  transcript redesign, which is DONE (slices 1-3), so its PROVISIONAL parts are
  unblocked and several review-frontend.md findings (transcript addressing, the
  SSE reducer, turn-vs-exchange provenance) are now cleanly resolvable with the
  new session_id-keyed API.
- The launch-profile port is the DRY home for launch flags; reuse it.

## Deliverables

- `transport-matters-session-canvas/fe-spec.md` (author: frontend-engineer/codex)
  — the F1-F2 buildable frontend spec.
- `transport-matters-session-canvas/cli-spec.md` (author: backend-engineer/codex)
  — the desktop CLI flag-reuse investigation + design.

FE spec is reviewed by the FE architect (frontend-engineer/claude, MoE pair). The
CLI spec is reviewed by the orchestrator; the FE architect does a contract-level
glance (the desktop command launches the agent the canvas displays).

## Acceptance bar

Grounded + cited in the actual repo + the parked cockpit spec; DRY (reuse the
layout-engine design, the launch-profile port, the session API; no parallel
impls); content-agnostic layout engine; data contracts match slices 1-3; respects
repo invariants (LOC <=700/file & fn <=~150 across www/ TS and api/ py; import
boundaries; Pydantic v2 for any py). The CLI spec must prove flag reuse or propose
the reuse refactor with zero duplicated flag definitions. No em dashes.

## Comms protocol (anti-chatter)

No pane messages another except the author<->architect review loop (CC the
orchestrator on typed lines only). All other replies go to the orchestrator
(`transport-matters:general:1:2.1`). One-line `done:`/`blocked:` on the bus; all
content lives in files. The architect reviews after the orchestrator signals a
draft is ready; the orchestrator integrates and is the only one who opens a round
2. Open questions go in an "Open questions for orchestrator" section in the file,
each with a working assumption.
