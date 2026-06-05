# Transport Matters — Desktop Cockpit / Layout Lab (charter v2)

Orchestrator-authored charter. The panel **fleshes this into a buildable spec +
slice plan**. Locked decisions are not up for relitigation; extend, ground in the
actual repo, and harden. Read this instead of the chat that produced it.

## North star

This desktop UI is a **testbed for the layout/window-management UI that
littleorgans will use at scale.** The genuinely reusable product is a **generic,
content-agnostic layout engine** (panes, splits, focus, slick transitions, a
viewer registry, and event-driven pane spawning). **Transport Matters is its
first content consumer.** Design every generic piece so it lifts out cleanly to
littleorgans; keep TM-specific content (chat / TUI / wire / artifacts) plugged in
only at the edges. The engine must know rectangles, panes, and transitions, never
chat or wire.

## Domain model (maps onto tmux)

- **Workspace** = a working directory. One canvas. Persisted and remembered.
  Identity reuses TM's existing canonical-target-path slug/hash, so two checkouts
  of one project share a workspace (DRY with the capture substrate). `--work-dir`
  opens or seeds one. (tmux: session.)
- **Agent** = one launched `claude`/`codex` run inside a workspace. Multiple
  agents per workspace. (tmux: window.)
- **Pane** = one view: an agent's chat / TUI / wire, or an artifact viewer.
  (tmux: pane.)
- **Canvas** = the spatial surface for one workspace; hosts every agent's panes
  plus artifact viewers.
- **Layout** = an arrangement of panes (a configuration of the split tree),
  switchable with slick transitions.

## The layout engine (the reusable heart)

- **Primitive:** a recursive split tree. Leaves are panes; any subtree can be
  tagged as an agent group. The same content renders as different layouts
  ("tile everything", "group by agent", "one pane zoomed, rest docked"). This
  recursion is what scales from 3 panes to 30 without a new model.
- **Layout modes to experiment with:** structured tiling (tmux-style rows/cols,
  even-h/v, main-h/v) AND a free-floating canvas (pan/zoom, spatial). Support both
  and make the **transition between modes** a showpiece. (Open: confirm both vs
  one; recommendation is both.)
- **Focus / zoom:** bring one pane to full focus, restore.
- **Transitions:** FLIP / shared-layout animation (measure old rect, measure new
  rect, invert, play). Every layout change, focus toggle, agent spawn, and
  artifact arrival animates smoothly. "Super slick" is a hard requirement, not
  later polish.
- **Persistence:** layouts, and which agents/panes belong to a workspace, are
  remembered per workspace.

## Content plugged into the engine (TM-specific)

Per agent, three view panes forming a **rawness gradient** (clean → raw), which is
the TM thesis (wire vs transcript is the product) made spatial:

- **Transcript chat pane** — premium render of the transcript IR. Read-only in v1.
- **Real TUI pane** — xterm.js over a per-agent PTY websocket; interactive; the
  single keyboard input surface in v1.
- **Wire pane** — reuse the existing intercept/wire components + capture stream.

Plus artifact viewers (below).

## Viewer registry + event-driven artifact spawn

- **Viewer registry:** content-type to renderer (`.md` to markdown, image to image
  viewer; later code/diff, csv/table, html/preview). Generic and reusable; part of
  what littleorgans inherits.
- **Detection source = wire/transcript tool responses, NOT a filesystem watcher.**
  Rationale (decided, with example): agents write artifacts to arbitrary,
  non-workspace locations. Codex writes generated images to
  `~/.codex.lilo/generated_images/<id>/...png` (the managed `--home-dir`), nowhere
  near the work dir, so a workspace-scoped FS watcher misses them and does not
  scale across scattered locations. The wire/transcript tool records carry the
  actual path (and often the content), are attributed to the exact agent and turn,
  and are location-agnostic and reliable.
- **Mechanism:** parse tool-use / tool-result records (wire and/or transcript) for
  produced artifacts (`Write`/`Edit` paths + content; image-generation result
  paths) → resolve → viewer registry → spawn or update a viewer pane through the
  engine's event-driven spawn API.
- **Spawn policy (critical at scale):**
  - dedupe-to-update: the same path updates one pane (gives a live render of a doc
    being authored), never re-spawns;
  - filter to interesting types; ignore temp/build noise;
  - no focus theft: artifacts animate into a calm artifacts zone/dock, not the
    foreground;
  - lifecycle: pin / dismiss / auto-retire; persisted per workspace;
  - provenance link: click an artifact to jump to the originating turn/agent
    (a TM superpower the FS watcher could never give).
- **Engine stays pure:** it receives "open content X in a viewer"; a TM
  orchestration layer decides when to emit that, derived from wire/transcript.

## Screen flow

- **Screen 1 — creative workspace launcher.** NOT a dumb dir selector, NOT a
  claude/codex chooser. Persisted, remembered workspaces with rich metadata (git
  branch, last activity, live agent count, maybe a live canvas thumbnail).
  Directions to explore (ux to recommend one): project-gallery cards /
  command-palette fuzzy finder / drag-a-folder / spatial recents.
- **Open a workspace** to its canvas.
- **Inside the canvas, "spin up an agent"** (choose claude/codex) adds an agent and
  its panes; the engine reflows with a slick transition. Provider choice lives
  here, not on screen 1.

## Locked decisions (do not relitigate)

1. The layout engine is generic, content-agnostic, and extractable; littleorgans
   is the target. TM content plugs in at the edges.
2. Pane 1 = transcript (read-only v1). Pane 2 = real TUI (interactive, single
   input v1). Pane 3 = reuse existing wire UI + capture stream.
3. Multi-agent per workspace; multi-workspace via the launcher.
4. Workspace = work dir; identity reuses TM's canonical-path slug/hash; persisted;
   `--work-dir` opens one.
5. Artifact detection = wire/transcript tool responses, NOT an FS watcher.
6. Launch core is reused, not reimplemented (LaunchProfile /
   `prepare_managed_session` / proxy bootstrap / managed-mint). Per-run isolation
   invariant holds (each agent its own proxy port, web API, storage root).
7. Electron stays out of the `uv tool` (Python) env; built and shipped separately;
   the Python CLI only locates + launches it.
8. Slick FLIP/shared-layout transitions are a hard requirement.

## Provisional stream/contract surface (panel finalizes)

All panes are subscriptions to one run's backend. Two already exist.

- **Wire (pane 3):** existing capture stream + REST. Reuse.
- **Transcript (pane 1 + artifact detection):** transcript turns as IR, live
  append; plus the tool-response records that carry artifact paths/content.
- **Terminal (pane 2) — the one new backend capability:** a per-agent
  bidirectional localhost websocket. Server to client: PTY master output bytes
  (with attach-time scrollback/replay). Client to server: keystrokes +
  `resize(cols, rows)`. No host TTY exists in a GUI, so the managed child runs on
  a PTY whose master is streamed.
- **Artifact events:** a derivation of "artifact produced (path, type, content?,
  agent_id, turn_id)" from wire/transcript tool records, delivered to the UI.
- **Multi-agent lifecycle:** launch N runs per workspace; start/stop/crash/exit;
  workspace + layout persistence store (provisional location under
  `~/.transport-matters/` desktop config; confirm).

## Reuse seams to GROUND (verify in the repo + cite; do not trust this list)

- **Launch:** `api/src/transport_matters/cli/launch_profile.py` (`LaunchProfile`,
  `prepare_managed_session`, `ClaudeLaunchProfile`, `CodexLaunchProfile`) and the
  `claude`/`codex` CLI commands that bootstrap the proxy + launch the child.
- **Workspace identity:** the canonical-path slug/hash logic used for tier-1
  storage roots.
- **Proxy bootstrap:** mitmproxy reverse/explicit spin-up; env injection
  (`ANTHROPIC_BASE_URL` / `HTTPS_PROXY` + CA).
- **Wire capture + stream:** server / broadcast (SSE) layer + intercept routes;
  `www/` intercept/wire/breakpoint components.
- **Transcript IR + tool records:** `index/` (`transcript_turn`, IR
  `ContentBlock`), adapters; where tool-use/tool-result + artifact paths surface.
- **Frontend:** the `www/` React (Vite) app; what is reusable as-is vs coupled to
  the full-page layout.

## Open questions per pillar

### Backend (backend-engineer pair)
- topology: manage `transport-matters claude/codex` subprocess per agent
  (provisional, preserves isolation) vs a session-manager daemon.
- GUI/headless launch mode (no host TTY): attach child to a PTY, expose pty-ws +
  web API; full lifecycle.
- pty ownership/protocol: python pty + ws (provisional, DRY) vs node-pty; framing,
  input, resize, backpressure, attach replay.
- artifact-event surface: derive produced-artifact events from wire and/or
  transcript tool records; which is authoritative (transcript record vs wire
  tool_result); attribution (agent+turn); delivery to UI (SSE?).
- workspace + layout persistence store (schema, location, identity reuse).
- multi-agent run registry/discovery (web port + pty-ws endpoint per agent); tie
  to the existing `list` surface.
- DAG placement, LOC budgets, localhost-bind + optional per-run ws auth.

### Frontend (frontend-engineer pair)
- layout engine: recursive split tree; tiling + free-canvas modes; FLIP
  transitions; focus/zoom; preset layouts; persistence. Tech pick (react-flow /
  tldraw / custom + a layout-animation lib) justified for perf with a live xterm +
  multiple streaming panes.
- pane shell (drag/resize/z-order/focus/minimize), premium feel.
- TUI pane (xterm.js + fit/webgl; attach pty-ws; resize; reconnect + replay).
- chat pane (transcript IR to premium render; live append; read-only).
- wire pane (embed existing components in a floating pane; decoupling needed).
- viewer registry + viewer panes (md/image pluggable); consume the event-driven
  spawn + implement the spawn policy (artifacts zone, dedupe-update, provenance).
- component reuse: ONE UI codebase, the renderer imports `www/` components; vite
  build for the renderer.
- Electron skeleton (main/preload/renderer; single-instance; screen flow; how the
  renderer talks to per-agent backends over localhost).

### UX (ux-designer)
- layout interaction model: configuring rows/cols, switching presets, zoom-focus,
  dragging panes; keyboard (tmux-like) + pointer affordances.
- transition choreography: what animates, timing/easing, the mode-switch showpiece,
  artifact-arrival motion (calm, no focus theft).
- creative workspace launcher: 2-3 concrete directions with one recommended;
  metadata shown; create/open/remember flow.
- artifact/viewer UX: where artifacts land, the dedupe-update feel, provenance.
- the rawness-gradient visual story across the three agent panes.

## Deliverables

1. `transport-matters-desktop-cockpit/spec-backend.md` — backend-engineer/claude
   authors, backend-engineer/codex peer-reviews, both sign off.
2. `transport-matters-desktop-cockpit/spec-frontend.md` — frontend-engineer/claude
   authors, frontend-engineer/codex peer-reviews, both sign off.
3. `transport-matters-desktop-cockpit/spec-ux.md` — ux-designer authors; the
   frontend pair consumes it; the orchestrator adjudicates conflicts.
4. **Orchestrator merges** all three into
   `~/.mdx/projects/transport-matters-desktop-cockpit-spec.md`, reconciles the
   backend↔frontend stream-contract seam, and authors the unified sliced build
   plan (mirroring the capture-substrate slice style: per slice = files, reuse,
   acceptance gate, LOC budget). Slice 1 is the thinnest end-to-end loop:
   launcher → open a workspace → spin one agent → one pane live in the generic
   layout shell.

## Spec acceptance bar (this is a spec, not the build)

- Grounded in actual repo seams (verified + cited, never assumed).
- DRY: reuses the launch core + `www/` components; zero parallel implementations.
- The layout engine is genuinely content-agnostic and extractable to littleorgans
  (no TM-content imports in the engine).
- Respects repo invariants: import DAG, LOC ≤700/file & fn ≤~150, AST privacy
  boundary, builtins-only typing, Pydantic v2, IR frozen.
- The slice plan is incrementally shippable; slice 1 is the thinnest loop above.
- Internally consistent and consistent across the three sections, especially the
  pty-ws, artifact-event, and transcript contracts the frontend consumes.

## Conventions

Repo `CLAUDE.md` / `PROJECT.md` are binding. No em dashes; rarely hyphens. The
code gate is `cd api && just ci`. Build slices land as small, dual-signed PRs like
the capture substrate. Bus discipline: one typed line per message, cite paths, no
pasting; peers read the artifacts live.
