# Transport Matters Desktop Cockpit / Layout Lab: Unified Spec

Status: orchestrator-merged, buildable. Supersedes the three section specs
(`spec-backend.md`, `spec-frontend.md`, `spec-ux.md`) and folds in the two peer
reviews (`review-backend.md`, `review-frontend.md`). Where a section spec
conflicts with a reconciliation decision, the decision wins; this document
records the resolved position.

Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`. Section specs verified
against `main`; backend citations were grounded at `d8b944a`. Conventions: no em
dashes; repo `CLAUDE.md` / `PROJECT.md` / `api/CLAUDE.md` are binding. Gate is
`cd api && just ci` plus the frontend lint/typecheck/test/build. Every reuse seam
is cited as `path:Symbol` with line ranges where the source specs did.

---

## Top-of-doc note (scope and provisionality)

The proxy and wire capture remain in scope. A **transcript-storage redesign is
forthcoming** for the replay / fork / share / eval / learn product direction.
**Slices 5 and 6, and every backend and frontend decision flagged `PROVISIONAL -
pending transcript redesign`, are provisional and may change after that redesign.**
Build them last and expect churn.

The wire-versus-transcript **DIFF is NOT a product feature and must not be built
as one.** The rawness gradient (transcript to terminal to wire) makes the thesis
spatial; it does not ship a diff view.

---

## 1. Product framing

This desktop UI is a **testbed for the layout / window-management UI that
littleorgans will use at scale.** The genuinely reusable product is a **generic,
content-agnostic layout engine**: panes, splits, focus, slick transitions, a
viewer registry, and event-driven pane spawning. **Transport Matters is its first
content consumer.** Every generic piece is designed to lift out cleanly to
littleorgans; TM-specific content (transcript / terminal / wire / artifact) plugs
in only at the edges. The engine knows rectangles, panes, zones, focus, and
transitions; it never imports transcript, wire, terminal, or any TM type.

A second force shapes the data layer. The existing `www/` app is **single-backend
and global-singleton** by construction: a module-global API transport
(`www/src/api.ts:setApiTransport`), a singleton query cache
(`www/src/lib/queryClient.ts:queryClient`), and a global UI store
(`www/src/stores/uiStore.ts:useUIStore`). The cockpit drives **N backends at
once**, one per agent, so reusing `www/` components requires scoping these globals
per agent. This de-singletonization is the central reuse refactor (section 7.4).

---

## 2. Domain model (workspace = path / agent / pane, tmux mapping)

| Concept | Definition | tmux analogue |
| --- | --- | --- |
| **Workspace** | A working directory. One canvas. Persisted and remembered. **Identity is the resolved-path hash; a workspace IS a work-dir path.** `--work-dir` opens or seeds one. | session |
| **Agent** | One launched `claude` / `codex` run inside a workspace. Multiple agents per workspace. | window |
| **Pane** | One view: an agent's `transcript` / `terminal` / `wire`, or an `artifact` viewer. | pane |
| **Canvas** | The spatial surface for one workspace; hosts every agent's panes plus artifact viewers. | (the screen) |
| **Layout** | An arrangement of panes (a configuration of the split tree), switchable with slick transitions. | layout |

### 2.1 Workspace identity (DECISION: path-scoped, no cross-checkout sharing)

`workspace_id(cwd) -> (slug, hash)` (`workspace.py:workspace_id`(58-68)): canonical
path via `Path.resolve`, `slug` from the last path segments, `hash` =
`blake2b(canonical.as_posix(), digest_size=4)`. Because the hash is over the fully
resolved POSIX path, **two checkouts at different paths get different identities.**

DECISION [review-frontend #1]: reuse `workspace_id` and accept that **a workspace
is a work-dir path.** Drop the charter's "two checkouts of one project share a
workspace" promise. The launcher and layout persistence are path-scoped. No new
repo-identity seam is introduced in v1.

---

## 3. Architecture

### 3.1 Process topology (DECISION: per-agent launcher subprocess; daemon rejected)

The desktop spawns **one headless launcher subprocess per agent**, reusing the
launch core verbatim. Electron's main process is a pure localhost client
(WebSocket + HTTP + IPC); it never spawns proxies or children itself.

Today's per-run shape (grounded) is three processes, preserved per agent:

1. **Launcher** (the CLI process). Resolves launch state via `prepare_launch`
   (`cli/launch_runtime.py:prepare_launch`(335-397)), mints the session via
   `prepare_managed_session` (`cli/launch_profile.py:prepare_managed_session`(219-250)),
   takes the per-run lock and writes the manifest via `run_with_workspace_manifest`
   (`cli/launch_runtime.py:run_with_workspace_manifest`(534-576)), then spawns and
   supervises the next two processes through `ProcessSupervisor`
   (`supervisor_core.py:ProcessSupervisor`(19-299)).
2. **mitmdump** (the proxy). Argv from `build_mitmdump_argv`
   (`cli/launch_runtime.py:build_mitmdump_argv`(400-424)), `--listen-host 127.0.0.1`.
   Its addon calls `load_runtime` (`addon_runtime.py:load_runtime`(76-163)): boots
   tier-1 storage, the tier-2 `IndexWriter` + `TranscriptTailer`, the post-commit
   `emit=broadcast.emit` push (`addon_runtime.py:116`), and a uvicorn server hosting
   `create_app()` on `127.0.0.1:{web_port}` (`addon_runtime.py:148-155`).
3. **Child** (claude or codex). Spawned by the launcher
   (`cli/runner.py:run_children`(362), `_run_client_children`(395)). In the desktop
   it runs on a **headless PTY** (section 3.3).

Rejected: a single session-manager daemon multiplexing all agents.

Reasons: (a) preserves the locked per-run isolation invariant (own proxy port, web
API, storage root, manifest); a daemon would re-multiplex these and re-own the
per-run lock/manifest lifecycle `run_with_workspace_manifest` already provides;
(b) maximal launch-core reuse, no parallel supervision/retry path (DRY); (c) crash
isolation, no single point of failure; (d) discovery is free, the manifest registry
(`manifest.py:read_all`(98-113), `cli/instances.py:list_instances`(42-69)) already
models "many independent runs", one agent maps 1:1 to one manifest; (e) honors the
Electron-out-of-Python-env invariant. Cost is three OS processes per agent, equal
to today's per-run cost, acceptable at the target scale of tens of agents.

### 3.2 Per-agent endpoints

Each agent exposes two localhost origins to the renderer:

- `http://127.0.0.1:{web_port}` (mitmdump process): wire REST, transcript REST,
  SSE, breakpoint. REUSE verbatim.
- `ws://127.0.0.1:{pty_ws_port}/pty` (launcher process): the terminal. NEW.

```
Electron renderer (xterm.js, transcript, wire, viewers) ── localhost only ──┐
                                                                            │
  per agent A                          per agent B                          │
  ┌─────────────────────────┐         ┌─────────────────────────┐          │
  │ launcher (headless)      │         │ launcher (headless)      │          │
  │  asyncio pty-ws :ptyA ◄──┼─────────┼──────────────────────── ◄──────────┤ keystrokes/resize, pty bytes
  │  ProcessSupervisor       │         │  ...                     │          │
  │   ├─ mitmdump :proxyA    │         │                          │          │
  │   │   addon: web :webA ◄─┼─────────┼──────────────────────── ◄──────────┘ wire/transcript REST + SSE
  │   └─ child (headless PTY)│         │                          │
  └─────────────────────────┘         └─────────────────────────┘
```

### 3.3 GUI / headless launch mode (reuses the launch core)

New headless command wired into the Typer app (`cli/__init__.py:main`(84)):

```
transport-matters agent --client {claude|codex} --work-dir DIR \
    [--proxy-port N] [--web-port N] [--pty-ws-port N] [--home-dir DIR] [--no-system-prompt]
```

It prints **one JSON line on stdout** with
`{run_id, slug, hash, session_id, proxy_port, web_port, pty_ws_port, web_url, pty_ws_url, token}`
so Electron main connects without scraping logs, then stays foreground for the run's
lifetime. Order of reuse, end to end (no proxy bootstrap, env injection, mint, port,
or manifest logic reimplemented):

1. `resolve_working_dir` + `prepare_launch` (`cli/launch_runtime.py:232,335`):
   working dir, the port **triple** (section 3.7), `run_id`, storage dir.
2. `PROFILES[client]` (`cli/launch_profile.py:PROFILES`(213-216)) then
   `prepare_managed_session` (`:219`): mint + prepare the owned session. Codex
   resolves its CA via `_resolve_codex_ca_certificate_or_exit`
   (`cli/codex_cmd.py:47`).
3. The **public** invocation factory (DECISION, section 3.4). Claude: proxy mode
   `reverse:{upstream}`, child env `ANTHROPIC_BASE_URL=loopback_http_url(proxy_port)`
   (`cli/start_cmd.py:124-128`, `cli/net.py:loopback_http_url`(11)). Codex: proxy
   mode `regular`, `HTTP(S)_PROXY=loopback_http_url(proxy_port)` +
   `CODEX_CA_CERTIFICATE` via `build_managed_child_env`
   (`cli/launch_runtime.py:build_managed_child_env`(484-531), `cli/codex_cmd.py:198-205`).
4. `run_with_workspace_manifest` (`cli/launch_runtime.py:534`): per-run lock + write
   the extended manifest (section 3.7), passing `home_dir` through.
5. `persist_owned_session_facts` (`cli/launch_profile.py:persist_owned_session_facts`(253-278))
   inside the lock for rebuild survival.
6. The headless run loop (section 3.6): spawn mitmdump + child (headless PTY) via
   `ProcessSupervisor`, serve the pty-ws, supervise.

### 3.4 Public-wrapper refactor (DECISION)

`_build_start_invocation` (`cli/start_cmd.py:_build_start_invocation`(58-141)) and
`_build_codex_invocation` (`cli/codex_cmd.py:_build_codex_invocation`(146-228)) are
module-private; cross-module import is forbidden by the AST privacy boundary
(`test_private_import_boundary.py`). DECISION: **promote both to public names**
(`build_start_invocation` / `build_codex_invocation`) in their owning modules; the
old private names delegate, or rename and update in-module call sites. The desktop
command imports the public names. The factory contract is provider-neutral:
`build_invocation(proxy_port, web_port) -> (mitmdump_argv, launch_env, ManagedClient | None)`.
Rebuilding the factory in `desktop/` is rejected (DRY).

### 3.5 Contract: PTY-over-websocket (the one new backend capability)

This is the binding terminal contract the frontend consumes for the `terminal` pane.

**Endpoint and auth.** `ws://127.0.0.1:{pty_ws_port}/pty?token={run_token}`. Bound
`127.0.0.1` only. One agent serves exactly one PTY (one child), so the path needs no
session id; `run_id` identity is implicit in the dedicated port. Origin check: reject
upgrades whose `Origin` is not the cockpit origin or an allowlisted dev origin,
reusing the `config.py:cors_origins` shape (section 3.9).

**Framing (xterm.js-friendly: binary = data, text = JSON control).**

Server to client:
- On attach, one text control frame `{"type":"hello","cols":C,"rows":R,"scrollback_bytes":N}`.
- Then the scrollback ring as one or more **binary** frames (raw PTY bytes).
- Then live **binary** frames: raw `master_fd` output bytes, unmodified.
- On per-client queue overflow, a text `{"type":"gap"}` precedes the resumed binary
  stream so the UI shows a discontinuity.
- On child exit, a text `{"type":"exit","code":N}` then a normal close.

Client to server:
- **Binary** frames: raw stdin bytes (keystrokes, paste), written verbatim to
  `master_fd`. No escaping, no envelope.
- **Text** frames: JSON control. `{"type":"resize","cols":C,"rows":R}` calls
  `set_pty_winsize(master_fd, cols, rows)`. `{"type":"ping"}` answered with text
  `{"type":"pong"}`.

**Backpressure and scrollback.** The child must never block on PTY write because the
UI lagged. A single asyncio reader (`loop.add_reader(master_fd, ...)`) always drains:
appends to a fixed-size **scrollback ring (default 256 KiB, byte-bounded)** and fans
out to each client's **bounded outbound queue** (default 1 MiB or 1024 frames). On
overflow, drop oldest frames for that slow client and set its `gap` flag. The reader
never awaits a slow client. Attach replay is a raw-byte replay of the ring
(reconstructs recent screen, not full history; full history is out of scope, section
9). Heartbeat: protocol ws ping/pong plus application `ping`/`pong` at a 15s cadence,
mirroring the SSE keepalive (`api/v1/stream.py:29-31`).

### 3.6 Lifecycle (the headless run loop)

`desktop/agent_host.py` runs uvicorn on `pty_ws_port` and uses the lifespan to:

1. **Startup**: spawn mitmdump via `ProcessSupervisor.spawn(..., log_path=...)` and
   the child via `spawn(..., headless_pty=True)` (section 3.8), using the invocation
   factory's `(mitmdump_argv, env, ManagedClient)`. Register the `master_fd` reader.
   Install signal handlers (`ProcessSupervisor.install_signal_handlers`(173)).
2. **Serving**: watch child + mitmdump liveness via `ProcessSupervisor.poll_any`(211)
   on a periodic `loop.call_later`, or `asyncio.to_thread` around `wait_any`(219). On
   child exit, emit `{"type":"exit","code":N}` and begin shutdown.
3. **Shutdown**: `teardown_pty` (`supervisor_pty_process.py:173-206`), then
   `ProcessSupervisor.terminate_all(grace_seconds=...)`(250), then drop the manifest
   (`run_with_workspace_manifest`'s `finally`, `cli/launch_runtime.py:571-575`).

Port bind-failure retry reuses `handle_bind_failure` (`cli/runner.py:225`) for the
proxy/web ports; pty-ws bind failure is surfaced on the startup JSON line with a
non-zero exit (Electron respawns with a fresh triple).

### 3.7 Manifest extension and port triple

Extend `Manifest` (`manifest.py:Manifest`(34-52)) following the `home_dir` optional
precedent (backward-safe for `read`/`read_all`):

```python
pty_ws_port: int | None = None     # set for desktop/headless agents only
desktop_token: str | None = None   # per-run auth token (section 3.9, perms-gated)
```

`run_with_workspace_manifest`'s `write_manifest_for` closure
(`cli/launch_runtime.py:545-567`) passes these through for the headless command;
interactive `claude`/`codex`/`start` leave them None.

`allocate_port_pair` (`cli/ports.py:allocate_port_pair`(39-77)) opens both sockets on
port 0 simultaneously so the kernel cannot duplicate. **EXTEND** to a triple: add
`allocate_port_triple()` (same simultaneous-bind technique, three sockets).
`resolve_launch_ports` (`cli/launch_runtime.py:resolve_launch_ports`(245-285)) is
reused for proxy/web; the pty-ws port resolves alongside with the same pinned-or-
allocated logic, preserving the distinctness invariant.

### 3.8 Headless PTY spawn (refactor)

`spawn_with_pty` (`supervisor_pty_process.py:spawn_with_pty`(27-170)) assumes a host
TTY: it reads `sys.stdin.fileno()`, sets cbreak (`supervisor_pty.py:install_parent_cbreak`(30-45)),
runs `pty_shuttle` (`supervisor_pty.py:48`), and installs a parent SIGWINCH handler
(`supervisor_pty_process.py:135-140`). In a GUI there is no parent TTY, so that branch
is wrong. Extract the terminal-independent create core and add a headless sibling
(builtins-only typing):

```python
def _open_child_on_pty(name, argv, *, env, cwd, cols, rows) -> tuple[Popen[bytes], int]:
    """Open a pty, size the slave (TIOCSWINSZ, pattern from lines 64-69), spawn argv
    wired to the slave, close the parent slave copy (mirrors lines 115-120),
    return (popen, master_fd). No parent-terminal coupling."""

def spawn_headless_pty(name, argv, *, env, cwd, cols=80, rows=24) -> ManagedProcess:
    """PTY child for a GUI: no host TTY, no cbreak, no parent shuttle, no parent
    SIGWINCH. stop_event / shuttle_thread / old_termios_attrs /
    prev_sigwinch_handler stay None. The pty-ws host owns master_fd I/O + resize."""

def set_pty_winsize(master_fd, cols, rows) -> None:
    """TIOCSWINSZ on the master so the kernel signals SIGWINCH to the child."""
```

`spawn_with_pty` is refactored to call `_open_child_on_pty` for the create step,
keeping its cbreak + shuttle + SIGWINCH wiring for the TTY case. `teardown_pty`
(`:173-206`) already no-ops cleanly on the headless `ManagedProcess` (terminal fields
None) and closes `master_fd`, so it is the headless cleanup. `ProcessSupervisor.spawn`
(`supervisor_core.py:56`) gains `headless_pty: bool = False`; when set it calls
`spawn_headless_pty` and skips the TTY requirement, keeping one spawn entry point and
one `_children` registry for `terminate_all`/signals (`supervisor_core.py:250-288,173-199`).

DECISION (LOC): **pre-split `desktop/pty_ws.py` into `pty_ws.py` (ASGI app + routes)
+ `pty_bridge.py` (master_fd reader, ring buffer, per-client queues, resize),** so the
bridge mechanics stay separate from routes regardless of growth.

DECISION: Python `pty` + asyncio WebSocket, **not node-pty.** node-pty would move PTY
ownership into Electron, forcing a node reimplementation of proxy bootstrap, env
hardening, mint, and manifest. Rejected.

### 3.9 Contract: artifact events [PROVISIONAL - pending transcript redesign]

DECISION [review-backend #1]: artifact detection runs **at INGEST from
`NormalizedTurn.parts`** (the classifier on the pre-projection object), **NOT a tier-2
query.** The tier-2 timeline is lossy (section 3.10) and cannot recover
`ToolUseBlock.input`.

DECISION [review-backend #2]: extend the writer event seam from a single event to
**`IndexJob.events: tuple[dict, ...]`** and emit a `transcript_turn` event plus N
`artifact` events **atomically post-commit**, deduping on
`(session_id, turn_id, tool_use_id)`. Grounded gap: `IndexJob` today carries a single
`event: dict | None` (`index/writer.py:IndexJob`(29-43)); `_emit_events` emits at most
that one dict (`index/writer.py:192-201`); `build_transcript_job` already uses that
slot for `{"type":"transcript_turn", ...}` (`index/ingest.py:build_transcript_job`(347-373)).
A turn can yield multiple artifacts, so the contract must widen. Acceptance tests: one
committed turn emits the transcript event plus multiple artifact events; a rolled-back
job emits none.

Classifier `index/artifacts.py` (NEW, pure, imports `ir` only; DAG-safe):

```python
class ArtifactEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    session_id: str
    turn_id: str
    exchange_id: str | None
    tool: str
    path: str
    content_type: str    # markdown | image | code | json | text | unknown (by extension)
    has_inline_content: bool
    stream: str          # "transcript" | "wire"

def classify_artifact(block: ToolUseBlock, result: ToolResultBlock | None, *,
    session_id, turn_id, exchange_id, stream) -> ArtifactEvent | None: ...
```

Both streams parse to the same IR: `ToolUseBlock(name, input)` /
`ToolResultBlock(tool_use_id, content)` (`ir.py:ToolUseBlock`(25-32),
`ToolResultBlock`(35-42)), reachable from `NormalizedTurn.parts`
(`index/adapters/base.py:NormalizedTurn`(133-151)). Path extraction by tool: claude
`Write`/`Edit`/`MultiEdit`/`NotebookEdit` -> `block.input["file_path"]`; codex file
edits from `block.input` per the codex tool shape; image generation from
`ImageBlock.source["path"]` (`ir.py:ImageBlock`(53-58)) once the codex adapter
populates it (section 9, residual gap). `content_type` derives from the path
extension only; the viewer-to-renderer mapping lives in the frontend.

Delivery rides the post-commit emit seam (`emit=broadcast.emit` at
`addon_runtime.py:116`), so the cockpit gets artifacts on the same `/stream` it
already consumes, no new transport. SSE event shape (frontend dispatches on `type`):

```jsonc
{ "type": "artifact",
  "session_id": "<agent identity>", "turn_id": "<originating turn>",
  "exchange_id": "<wire exchange or null>",
  "tool": "Write|Edit|MultiEdit|NotebookEdit|image_generation|...",
  "path": "/abs/or/~resolved/path",
  "content_type": "markdown|image|code|json|text|unknown",
  "has_inline_content": true, "stream": "transcript|wire" }
```

Attribution: `session_id` is the agent identity (the universal correlation key,
`SessionBinding.session_id`, `index/adapters/base.py:24-46`); `turn_id` is the
originating turn; `exchange_id` ties to the wire exchange when the trigger is the wire
stream. Provenance jumps use `GET /api/index/sessions/{session_id}/timeline` (section
3.11) to reach `turn_id`.

### 3.10 Contract: transcript IR read [PROVISIONAL - pending transcript redesign]

DECISION [review-backend #1, review-frontend #2]: the `transcript` pane (pane 1)
renders the **full transcript IR read back from TIER-1, re-normalized via the
adapter.** Add a **tier-1 transcript-IR read surface**; **do NOT use the lossy tier-2
timeline projection.** Pane 1 stays `transcript`.

Grounded reason the timeline is insufficient [review-backend #1]: `session_timeline`
(`api/v1/index_routes.py:108-121`) returns `TimelineEntry`; `_edge_blocks`
(`index/queries.py:325-346`) joins only `block.text` (FTS projection,
`index/blocks.py:113-124`) and `block.identity_canonical` when `with_bodies` is true.
`TimelineBlock` (`index/models.py:157-167`) has `pos`, `block_id`, `role`, optional
`section`, `text`, `identity_canonical`. There is no typed `ContentBlock`, no `kind`,
no `ToolUseBlock.input`, no `ToolResultBlock.content`, no `ImageBlock.source`; the
`block` table persists only `kind`, `text`, `identity_canonical`
(`index/schema.py:41-48`). The tier-1 read surface re-normalizes the owned transcript
copy through the existing adapter to recover the full IR union.

### 3.11 Contract: REST + SSE surface the frontend consumes (REUSE)

Per agent, on `web_port` (`create_app()`, `main.py:create_app`(52-96), CORS from
`config.py:cors_origins`, `GET /health` -> `{"status":"ok"}`):

- `GET /stream` (`api/v1/stream.py:stream_exchanges`(20-42)): SSE,
  `text/event-stream`, pushing JSON from `broadcast.emit`. Carries wire turns,
  `transcript_turn`, and (provisional) `artifact` events. Subscribed once per agent.
- Wire: `GET /api/exchanges`, `GET /api/exchanges/{id}` (`api/v1/exchanges.py`),
  `GET /api/exchanges/{id}/raw`.
- Transcript / index: `GET /api/index/sessions`,
  **`GET /api/index/sessions/{session_id}/timeline`** (DECISION [review-frontend #2]:
  the correct path; **not** `/api/index/timeline`),
  `GET /api/index/sessions/{session_id}/pivot` (`api/v1/index_routes.py`(108-126)).
- Breakpoint: `api/v1/breakpoint_routes.py` arm/release.

### 3.12 Contract: persistence via Electron (DECISION)

DECISION: **Electron main owns the workspace/layout JSON.** Under the per-agent-
subprocess topology, Electron main is the only workspace-scoped long-lived process,
so it is the correct owner. It reuses the **backend on-disk schema and location**
(section 8). **DROP the backend's ASGI-route persistence variant** (the spec-backend
"layout routes on the pty-ws app" option and its open item are withdrawn). The pure
store functions (`desktop/store.py`, section 8.3) remain the schema/IO authority; the
renderer reaches them through the preload IPC bridge (`loadLayout` / `saveLayout` /
`listWorkspaces`, section 7.5), not over HTTP.

### 3.13 Import-DAG placement

Python DAG (`api/CLAUDE.md`, verbatim): `ir -> adapters -> rules -> pipeline ->
storage -> breakpoint -> server`. `ir.py` imports nothing and is frozen.
`canonicalization.py` is layer 1 (stdlib only). The `index/` package sits after
`storage`, importing `ir` + `canonicalization` only; the write sink is injected at
`load_runtime` so there is no `storage -> index` back-edge.

- `index/artifacts.py` (NEW) imports `ir` only; wired into the transcript ingest job
  builder; no new back-edge.
- `desktop/` is a NEW terminal sink **above** `cli` and `server`. It imports the
  launch core, `supervisor_*`, `manifest`, `workspace`, `config`, `broadcast`, and the
  `index` read side. **No core module imports `desktop`.**

Frontend DAG mirrors the Python discipline (section 4.6): engine depends on nothing
above it; the content layer depends on the engine and `www/`; the Electron shell
depends on neither renderer layer.

---

## 4. The layout engine (content-agnostic, extractable)

The reusable heart. It knows rectangles, panes, zones, focus, modes, and transitions;
it never imports transcript, wire, terminal, or any TM type. Extraction to littleorgans
is a directory lift plus a `package.json`; the boundary lint (section 4.7) guarantees
nothing TM-specific leaked in.

### 4.1 Tech pick (DECISION)

**Custom recursive split-tree core + Framer Motion (FLIP via `layoutId`) +
`@use-gesture/react` for floating-canvas pointer gestures.** Content-agnostic and
extractable.

Rejected, grounded in the perf requirement (a live xterm plus multiple streaming
panes, 3 to 30 panes): **react-flow (`@xyflow/react`)** models a node-edge graph with
no recursive split-tree or tiling model, so the charter primitive would be rebuilt on
top of it; node re-render under continuous byte streams is an avoidable risk.
**tldraw** is a shape-centric whiteboard, heavyweight for rectangle management, and
fights an embedded live xterm. The custom split tree is small: tiling is a pure
function from tree to rectangles; the floating canvas is absolute positioning under
one pan/zoom transform.

Framer Motion supplies the FLIP / shared-layout primitive (`layout` prop, `layoutId`
shared-element animation: measure old rect, measure new rect, invert, play) on
compositor-friendly transforms, which keeps 30 panes at 60fps under the rule that only
the pane wrapper transform animates (section 4.5).

### 4.2 Data model (DECISION: n-ary split tree; canonical conventions)

The split tree is **n-ary `children[] + sizes[]`**, never binary first/second + scalar
ratio. The engine stores `paneId` and geometry only; pane content is supplied through a
render prop, so no content type enters the engine.

```ts
type Axis = "row" | "col";

interface SplitNode {
  kind: "split"; id: string; axis: Axis;
  children: LayoutNode[];
  sizes: number[];        // fractions summing to 1; sizes.length === children.length
  groupTag?: string;      // opaque; consumer may tag a subtree (e.g. an agent group)
}
interface LeafNode { kind: "leaf"; id: string; paneId: string; }
type LayoutNode = SplitNode | LeafNode;

interface FloatingRect { x: number; y: number; w: number; h: number; }
interface PaneMeta {
  id: string; zone?: string;       // named zone, e.g. "artifacts"; engine has no opinion
  minimized?: boolean; pinned?: boolean;
  floating?: FloatingRect; z?: number;
}
interface Viewport { panX: number; panY: number; scale: number; }  // floating only

interface LayoutState {
  mode: "tiling" | "floating";     // canonical mode names
  tree: LayoutNode;
  panes: Record<string, PaneMeta>;
  focusedPaneId: string | null;
  zoomedPaneId: string | null;
  viewport: Viewport;
}
```

`sizes[]` stores fractions that sum to 1 after normalization (UI may display
percentages, persistence stores fractions). `sizes.length` must equal
`children.length` for every split.

### 4.3 Public API

Framework-agnostic pure reducers over `LayoutState` (no React, no TM), wrapped by thin
React bindings:

```ts
// structure
splitPane(target, axis, newPaneId, ratio?); closePane(id); resizeSplit(node, sizes[]);
// focus / zoom
focusPane(id); clearFocus(); zoomPane(id); restoreZoom();
// modes
setMode("tiling" | "floating");
// floating
moveFloating(id, rect); bringToFront(id); setViewport(partial); minimize(id); restore(id);
// event-driven spawn (consumed by the TM artifact orchestrator)
spawnPane({ paneId, place: "tile-with" | "floating" | "zone", anchor?, zone? });
updatePaneMeta(id, patch);
// presets
applyPreset(spec);
// persistence
serialize(): SerializedLayout; hydrate(s);
```

Presets are generic: `{kind:"even"}`, `{kind:"main"; axis; mainPaneId}`,
`{kind:"grid"; cols}`, `{kind:"group"; partition: (paneId) => string}`. "Group by
agent" is the consumer passing `paneId => agentIdOf(paneId)`; the engine never learns
what an agent is.

### 4.4 Rendering surface

```tsx
<LayoutCanvas
  renderPane={(paneId) => ReactNode}     // content; consumer-owned
  renderChrome={(paneId) => ReactNode}   // optional pane header/controls
/>
```

`LayoutCanvas` computes rectangles from `LayoutState` (tiling: walk the tree allocating
fractions; floating: read `PaneMeta.floating` under the viewport transform) and renders
each pane as a `motion.div` with a stable `layoutId={paneId}`. Tree changes, mode
switches, focus toggles, and spawns all FLIP automatically because `layoutId` is stable
across states.

### 4.5 Transitions and the 60fps guarantee

1. Animate `transform` and `opacity` only; never width/height/top/left of content.
2. Pane content is **not** re-laid-out during a transition; xterm refit and size-
   dependent reflow run once on `onLayoutAnimationComplete`.
3. `React.memo` every pane content component with a stable `paneId`; a layout change
   re-renders wrappers, not content.
4. `will-change: transform` on panes only while a transition is in flight, then clear.
5. Streaming content (xterm, live append) writes via refs and imperative APIs, so byte
   arrival never triggers a layout React render.
6. Floating pan/zoom mutates one transform on the canvas layer, not per-pane styles.

The mode switch is the showpiece: same `layoutId` per pane, so panes fly between their
tile cell and their floating rectangle in one shared-layout animation. `zoomPane`
animates the target to the full-canvas rectangle while the rest dim and recede.

### 4.6 Repo placement and build topology

Grounded facts: no root pnpm workspace; `www/` (package `transport-matters`) and
`desktop/` (package `transport-matters-desktop`, `electron@^39`) are independent pnpm
projects. `desktop/src/rendererBoundary.test.ts` enforces the Electron main bundle is
React-free. `www/vite.config.ts` builds the single-page app into
`../api/src/transport_matters/www`.

1. **`www/` is the one UI codebase.** It gains a second Vite build target, the
   **cockpit renderer**, sharing `www/src/components/*`, `www/src/hooks/*`,
   `www/src/api.ts`, and design tokens. No fork. New entry `www/cockpit.html` +
   `www/src/cockpit/main.tsx`; new config `www/vite.cockpit.config.ts` ->
   `www/dist-cockpit/`.
2. **The engine lives at `www/src/engine/`** with a public barrel
   `www/src/engine/index.ts`. It may depend only on `react`, `framer-motion`,
   `@use-gesture/react`.
3. **`desktop/` keeps its main process** and is generalized one -> N (section 7.5). It
   loads `www/dist-cockpit/index.html` in production, the cockpit dev URL in dev.

New `www/package.json` deps: `framer-motion`, `@xterm/xterm` + `@xterm/addon-fit` +
`@xterm/addon-webgl`, `@use-gesture/react`, `react-markdown` + `remark-gfm`. React 19,
Tailwind v4, TanStack Query v5, Zustand v5, `@tanstack/react-virtual` already present.

DECISION (cockpit renderer is served over loopback http) [review-frontend #6]: the
cockpit renderer is **served over loopback http, NOT `file://`.** Its origin is added
to each backend's `cors_origins` and to the ws `Origin` allowlist (section 3.5). This
withdraws the `file://`/null-origin discussion in the section specs and resolves
OQ-5/OQ-6.

### 4.7 Boundary lint (DECISION)

An ESLint `no-restricted-imports` rule on **`www/src/engine/**`** forbids importing
`@/components`, `@/api`, `@/stores`, `@/hooks`, and any TM path. This is the TypeScript
analogue of the Python AST privacy boundary (`test_private_import_boundary.py`) and is
the mechanical guarantee of extractability. CI fails on violation. A content-layer rule
additionally requires the TM layer to import the engine only through its barrel.

---

## 5. Canonical conventions (use exactly; all variants replaced)

```ts
export type PaneKind = "transcript" | "terminal" | "wire" | "artifact";
export type LayoutMode = "tiling" | "floating";
export type ContentType = "markdown" | "image" | "code" | "json" | "text" | "unknown";

export interface ArtifactProvenance { session_id: string; turn_id: string; }
```

- **Pane kinds**: only `transcript | terminal | wire | artifact`. Drop `chat` / `tui`
  / `viewer`. **`agentSummary` is deferred post-v1.**
- **Layout modes**: only `tiling | floating`. Drop `tiled` / `free`.
- **Split tree**: n-ary `children[] + sizes[]`; never binary `first`/`second` + scalar
  `ratio`. `sizes[]` are fractions summing to 1.
- **Artifact provenance keys**: `session_id` + `turn_id` (snake_case).
- **Content-type enum**: `markdown | image | code | json | text | unknown`.

These names are binding across backend, frontend, and UX. Where a section spec used a
dropped variant (`chat`, `tui`, `viewer`, `tiled`, `free`, `mode "free"`, binary split
fields, `agent_id`), the canonical name above supersedes it.

---

## 6. Backend design (reconciled, grounded, cited)

### 6.1 Grounded reuse map

| Capability | Existing symbol (file:lines) | Verdict |
| --- | --- | --- |
| Per-provider launch profile | `cli/launch_profile.py:LaunchProfile`/`ClaudeLaunchProfile`(110-153)/`CodexLaunchProfile`(156-205); `PROFILES`(213-216) | REUSE |
| Mint + prepare owned session | `cli/launch_profile.py:prepare_managed_session`(219-250) | REUSE |
| Persist durable owned-launch facts | `cli/launch_profile.py:persist_owned_session_facts`(253-278) | REUSE |
| Resolve ports/run_id/storage/wd | `cli/launch_runtime.py:prepare_launch`(335-397), `resolve_launch_ports`(245-285), `resolve_storage_dir`(288-300), `new_run_id`(330-332) | REUSE |
| Free-port allocation | `cli/ports.py:allocate_port_pair`(39-77) | EXTEND (triple) |
| mitmdump argv | `cli/launch_runtime.py:build_mitmdump_argv`(400-424) | REUSE |
| Shared launch env | `cli/launch_runtime.py:build_launch_env`(445-481) | REUSE |
| Managed child env hardening | `cli/launch_runtime.py:build_managed_child_env`(484-531) | REUSE |
| Claude invocation factory | `cli/start_cmd.py:_build_start_invocation`(58-141) | REUSE via public wrapper |
| Codex invocation factory | `cli/codex_cmd.py:_build_codex_invocation`(146-228) | REUSE via public wrapper |
| Per-run lock + manifest lifecycle | `cli/launch_runtime.py:run_with_workspace_manifest`(534-576) | REUSE |
| Process supervision | `supervisor_core.py:ProcessSupervisor`(19-299) | REUSE |
| PTY create + child wiring | `supervisor_pty_process.py:spawn_with_pty`(27-170) | EXTEND (core + headless sibling) |
| PTY winsize/ioctl pattern | `supervisor_pty_process.py`(64-69,135-138); `supervisor_pty.py:install_parent_cbreak`(30-45) | REUSE pattern |
| Workspace identity | `workspace.py:workspace_id`(58-68), `workspace_root`(71-80), `run_root`(83-92) | REUSE |
| Run manifest schema + registry | `manifest.py:Manifest`(34-52), `read_all`(98-113), `read`(69-95), `write`(55-66) | EXTEND (pty_ws_port, token) |
| `list` surface | `cli/instances.py:list_instances`(42-69) | REUSE |
| Per-run web API | `main.py:create_app`(52-96) | REUSE |
| Web bind + tier-2 boot | `addon_runtime.py:load_runtime`(76-163) | REUSE |
| Live SSE stream | `api/v1/stream.py:stream_exchanges`(20-42); `broadcast.py:broadcast` | REUSE |
| Wire exchange REST | `api/v1/exchanges.py` | REUSE |
| Transcript / index REST | `api/v1/index_routes.py`(108-126) | REUSE |
| Breakpoint REST | `api/v1/breakpoint_routes.py` | REUSE |
| Post-commit emit seam | `index/writer.py:IndexWriter`(53-204), `IndexJob`(29-43); `emit=broadcast.emit` at `addon_runtime.py:116` | REUSE + EXTEND (events tuple) |
| Transcript turn IR | `index/adapters/base.py:NormalizedTurn`(133-151); `ir.py:ContentBlock`(68-71), `ToolUseBlock`(25-32), `ToolResultBlock`(35-42), `ImageBlock`(53-58) | REUSE |
| Tier-1 transcript-IR read | (none) | NEW [PROVISIONAL] (`index/` read surface, section 3.10) |
| Artifact path extraction | (derived from `ToolUseBlock.input`/`ToolResultBlock.content`) | NEW [PROVISIONAL] (`index/artifacts.py`) |
| Workspace + layout persistence | (none) | NEW (`desktop/store.py`, owned by Electron, section 3.12) |
| Headless run loop + pty-ws | (none) | NEW (`desktop/`) |

### 6.2 Module layout and budgets

- `index/artifacts.py` (NEW, ~120 LOC) [PROVISIONAL]: `ArtifactEvent` +
  `classify_artifact`; imports `ir` only; wired into `index/ingest.py`'s transcript job
  builder.
- `index/writer.py` (EXTEND) [PROVISIONAL]: `IndexJob.events: tuple[dict, ...]`;
  `_emit_events` iterates the tuple; dedupe on `(session_id, turn_id, tool_use_id)`.
- Tier-1 transcript-IR read surface (NEW, in `index/`) [PROVISIONAL]: re-normalize the
  owned transcript copy through the adapter to full IR (section 3.10).
- `supervisor_pty_process.py` (EXTEND): `_open_child_on_pty`, `spawn_headless_pty`,
  `set_pty_winsize`; refactor `spawn_with_pty`.
- `supervisor_core.py` (EXTEND): `headless_pty: bool` on `spawn`.
- `cli/ports.py` (EXTEND): `allocate_port_triple`.
- `manifest.py` (EXTEND): `pty_ws_port`, `desktop_token` optional fields.
- `cli/start_cmd.py` / `cli/codex_cmd.py` (EXTEND): public invocation factory.
- `desktop/` (NEW package, terminal sink): `models.py` (frozen layout/workspace
  models, ~150 LOC), `store.py` (pure JSON persistence, ~200 LOC), `registry.py`
  (discovery over `read_all`, ~120 LOC), `pty_ws.py` (ASGI app + routes) +
  `pty_bridge.py` (master_fd bridge, ring, queues, resize) [pre-split per section 3.8],
  `agent_host.py` (headless run loop, ~220 LOC).
- `cli/agent_cmd.py` (NEW, ~150 LOC): `transport-matters agent` wired into
  `cli/__init__.py:main`, mirroring `start_cmd.py` / `codex_cmd.py`.

Files <= 700 LOC, functions <= ~150. Builtins-only typing. Pydantic v2 frozen models.
IR untouched and frozen. Domain exceptions in `exceptions.py`, translated at the
FastAPI layer, chained (`raise X from e`).

### 6.3 Discovery and registry

A workspace is `(slug, hash)` from `workspace_id(cwd)`. Its live agents are the
manifests under `~/.transport-matters/workspaces/{slug}/{hash}/*/manifest.json`.
`desktop/registry.py` filters `read_all(root)` (`manifest.py:98`) by `(slug, hash)`,
using `WorkspaceLock.is_held` (via `list_instances`, `cli/instances.py:42-69`) to
distinguish live from stale, returning per agent `run_id`, `cli`, `proxy_port`,
`web_port`, `pty_ws_port`, `started_at`, `pid`. A pure read; no new store.
`transport-matters list --json` remains the CLI view of the same data. **The
`desktop_token` is NOT returned by the registry** (section 6.4).

### 6.4 Security (DECISION [review-backend #3])

- **Localhost only.** mitmdump (`build_mitmdump_argv`(409-412)), the wire-API uvicorn
  (`addon_runtime.py:149`), and the pty-ws app all bind `127.0.0.1`. Never `0.0.0.0`.
- **PTY token handling (hardened).** The PTY is an input surface driving a real coding
  agent (file writes, shell), so it requires a per-run token
  (`secrets.token_urlsafe`). DECISION: the token is **handed to Electron main ONLY via
  the launcher stdout startup JSON line.** It is **never persisted in the manifest and
  never returned by the registry.** Grounded reason: manifest writes set no mode
  (`manifest.py:55-66`); `WorkspaceLock` creates the run dir with default `mkdir` and a
  `0o644` lock (`lock.py:96-104`), so a persisted token could be world-readable and a
  registry read would suffice to attach to the keyboard socket.
- **Harden run-dir/manifest perms regardless.** `0700` directories and `0600` atomic
  writes for any token that is persisted. Add a test asserting private file mode if a
  token is ever written to disk.
- **WebSocket origin allowlist.** The pty-ws upgrade checks `Origin` against the cockpit
  loopback-http origin plus dev origins (section 4.6), reusing `config.py:cors_origins`.
  Loopback bind + token + origin check is defense in depth.
- **Child env hardening reused.** `build_managed_child_env`(484-531) strips
  proxy/trust-bypass vars and pins proxy + CA, unchanged.
- **No secrets in code.** Tokens are runtime-generated; codex CA via
  `_resolve_codex_ca_certificate_or_exit`(47).
- web_port auth parity: the read-only wire/transcript API stays token-optional for v1
  (loopback only); same token in a later hardening pass.

---

## 7. Frontend design (reconciled, grounded, cited)

### 7.1 Layer model

```
Electron shell (desktop/, main + preload)       Node, React-free
  spawns N backends, discovers ports, bridges to renderer
        | localhost HTTP/SSE/WS, IPC
TM content layer (cockpit renderer)             imports www/ + engine
  paneRegistry, agentManager, artifactOrchestrator, AgentBackendProvider,
  launcher, transcript/terminal/wire/artifact panes
        | engine public API only
GENERIC LAYOUT ENGINE (extractable, zero TM imports)   the littleorgans payoff
```

Arrows down are the only permitted dependency directions, enforced by the boundary lint
(section 4.7).

### 7.2 Content panes (the rawness gradient)

Four pane kinds, registered in `paneRegistry` keyed by `PaneKind`, rendered through
`LayoutCanvas.renderPane`, scoped to one agent's backend via `AgentBackendProvider`
(section 7.4).

- **`transcript`** (read-only v1) [PROVISIONAL - pending transcript redesign]: renders
  the **full transcript IR from the tier-1 read surface** (section 3.10), reusing
  `www/src/components/detail/ContentBlocks.tsx:ContentBlockRow` (text, tool_use,
  tool_result, thinking, image, unknown), composed turn-grouped and conversational with
  editor affordances dropped (`MessagesSection.tsx`, `InspectTab.tsx:ResponseCard`).
  Live append via SSE `transcript_turn` (section 7.3). States: empty, loading,
  streaming, error, plus per-block expand/collapse from `ContentBlockRow`.
- **`terminal`** (the one pane on the new backend capability; single keyboard input
  surface in v1): `@xterm/xterm` + `@xterm/addon-fit` + `@xterm/addon-webgl` (canvas
  fallback). Attach to `ws://127.0.0.1:{pty_ws_port}/pty?token=` per section 3.5;
  `term.onData` -> binary frames; resize debounced to `onLayoutAnimationComplete`;
  reconnect with backoff then `term.reset()` + ring replay. States: connecting,
  connected, reconnecting, error, closed (exit code), empty.
- **`wire`**: reuse `www/src/components/ExchangeList.tsx:ExchangeList`,
  `ExchangeDetail.tsx:ExchangeDetail`, optionally
  `editor/BreakpointEditor.tsx:BreakpointEditor` + `ArmToggle.tsx:ArmToggle`. Once a
  pane is wrapped in `AgentBackendProvider`, these render unchanged. States: empty,
  loading, live, paused, error. Breakpoint editing optional for v1.
- **`artifact`** [PROVISIONAL]: viewer registry (section 7.6) renders md/image; the
  artifact orchestrator (section 7.6) drives spawn/update.

### 7.3 SSE reducer [PROVISIONAL - pending transcript redesign]

DECISION [review-frontend #3]: the SSE reducer gains a **`transcript_turn` branch +
scoped transcript query keys** for transcript live append. Grounded gap:
`applyExchangeStreamEvent` (`www/src/hooks/exchangeStreamEvents.ts`(292-302)) currently
handles only `paused`, `paused_tokens`, `exchange`, `exchange_deleted`, silently
ignoring `transcript_turn` (which the backend already emits post-commit,
`index/ingest.py:347-373`). Add a typed transcript branch, scoped transcript keys, and
tests that a committed transcript turn updates the transcript-pane cache.

### 7.4 Data layer and multi-agent scoping (DECISION: complete de-singletonization)

`AgentBackendProvider` React context scopes the data layer to one agent: a scoped API
transport from `http://127.0.0.1:{web_port}`, a scoped `QueryClient` (own
`QueryClientProvider`), a scoped SSE connection (`useExchangeStream` against that
agent's `/api/stream`) feeding that agent's cache via `applyExchangeStreamEvent`, and a
scoped `useUIStore` instance for independent selection.

DECISION [review-frontend #4]: the de-singletonization is **COMPLETE** via a scoped-
store factory through `AgentBackendProvider`. **Remove EVERY singleton import**
(`useUIStore.getState`, `queryClient`, `apiTransport`) from reusable pane code,
**including `applyExchangeEvent` forwarding-state and `ExchangeDetail` 404 selection-
clear.** Grounded gap: `applyExchangeEvent` reads/mutates the module-global
`useUIStore.getState()` for forwarding state
(`www/src/hooks/exchangeStreamEvents.ts`(7-12,253-267)) and `ExchangeDetail` clears
selection through the global store on 404 (`www/src/components/ExchangeDetail.tsx`(195-219)),
so with two agent panes an event in one could mutate the original singleton. Pass a
scoped store API through the event context or a store factory that removes every
singleton import from reusable pane code.

The DRY refactor lands in `www/` (shared by the single-page app and the cockpit, no
fork): the single-page app wraps one `AgentBackendProvider` at the root (behavior
unchanged); the cockpit wraps one per agent. Components and hooks
(`ExchangeList`, `ExchangeDetail`, `ContentBlockRow`, `BreakpointEditor`,
`useExchanges`, `useMeta`, `useTurnContent`, `useBreakpoint`, `useOverrides`) keep
signatures and read from context. The six agent-rail colors (`--color-agent-rail-0..5`)
map to per-agent pane accenting.

DECISION: `AgentHandle` **MUST carry `sessionId`** [review-frontend #2] so the
transcript timeline and pivot routes (keyed by `session_id`) are addressable; cache
keys use it. The renderer learns `sessionId` from the launcher startup JSON line
(section 3.3).

### 7.5 Electron shell (build on `desktop/`, generalize one -> N)

Reuse `desktop/src/main.ts`, `window.ts` (contextIsolation true, sandbox true,
nodeIntegration false, navigation guard), `preload.ts`, `backendProcess.ts`,
`backendHealth.ts`, `env.ts`. `rendererBoundary.test.ts` continues to scope only
`desktop/src/`.

DECISION (preload IPC surface, single-instance, generalize backendProcess one -> N):

```ts
window.cockpit = {
  listWorkspaces(): Promise<WorkspaceCard[]>;
  openWorkspace(workDir: string): Promise<WorkspaceId>;      // canonical slug/hash via the CLI seam
  spawnAgent(workspace, kind: "claude" | "codex"): Promise<AgentHandle>;
  stopAgent(agentId): Promise<void>;
  onAgentEvent(cb: (e: AgentLifecycleEvent) => void): Unsubscribe;  // started, exited, crashed
  loadLayout(workspace): Promise<SerializedLayout | null>;
  saveLayout(workspace, layout: SerializedLayout): Promise<void>;
};
```

`AgentHandle = { agentId, kind, baseUrl, webPort, ptyWsUrl, runId, sessionId }`. Main
learns ports + token + sessionId deterministically from the spawn's startup JSON line
(section 3.3), with manifests / `list --json` as a fallback discovery path.

- **Single-instance lock**: `app.requestSingleInstanceLock()` (currently missing) so
  one cockpit owns the workspace registry; a second launch focuses the existing window.
- **Generalize `backendProcess.ts`** from one child to a keyed registry of children,
  one per agent, each its own port triple and manifest, preserving the per-run isolation
  invariant by spawning one `transport-matters agent --work-dir` subprocess per agent.
- **Persistence** is owned by Electron main (section 3.12): `loadLayout` / `saveLayout`
  / `listWorkspaces` go through `desktop/store.py`'s schema, reusing the backend on-disk
  location (section 8).

DECISION (packaging) [review-frontend #6]: the **packaging step includes the cockpit
build inside the app resources** (the `electron-packager` root currently excludes the
sibling `../www/dist-cockpit`), and the smoke test asserts the renderer loads (the
current smoke only writes `status: "main-window-created"`). The renderer is served over
loopback http (section 4.6), so packaging copies `www/dist-cockpit` into the app and the
main process serves it from a loopback http server.

### 7.6 Viewer registry and artifact orchestration [PROVISIONAL]

**Viewer registry** (generic, engine-adjacent, ships to littleorgans, zero TM types):

```ts
interface ViewerContext { ref: ContentRef; }   // ContentRef = { uri; mime?; inlineText? }
interface Viewer { id; canRender(ref): boolean; render(ctx): ReactNode; }
registerViewer(v); resolveViewer(ref): Viewer | null;
```

v1 viewers: markdown (`react-markdown` + `remark-gfm`) and image. `paneRegistry` maps
`artifact` panes to `resolveViewer`.

**Artifact orchestration** (TM layer). The engine stays pure ("spawn or update a pane
in a zone"); a TM `artifactOrchestrator` decides when, consuming the backend `artifact`
SSE events (section 3.9; the frontend does not re-derive). Spawn policy:

- **dedupe-to-update**: a `Map<path, paneId>`; the same path calls `updatePaneMeta` +
  content refresh, never `spawnPane` again. Dedupe key is the normalized path; if
  absent, a stable id from `session_id` + `turn_id` + content type + ordinal.
- **type filter**: only allowlisted types with a registered viewer (md, image v1).
- **no focus theft**: `place: "zone", zone: "artifacts"`; animate into a calm dock;
  never `focusPane`.
- **lifecycle**: pin / dismiss / auto-retire (capped, least-recently-updated). Persisted
  per workspace.
- **provenance link** (DECISION [review-frontend #5]): each artifact stores a
  **discriminated provenance target (transcript turn vs wire exchange).** Clicking it
  focuses the originating pane and selects the source. Because existing wire selection is
  exchange-based (`selectedId` matches `IndexEntry.id`,
  `www/src/components/ExchangeDetail.tsx`(209-219)), a raw transcript `turn_id` would
  fail visibility lookup or 404 `/api/exchanges/{turnId}`. So when the target is the
  wire pane, **pivot `turn_id` -> `exchange_id` via the existing correspondence model**
  (`index/models.py`(184-191), `GET /api/index/sessions/{session_id}/pivot`) before
  focusing. Provenance keys shown in UI are exactly `session_id` and `turn_id`.

### 7.7 Frontend invariants

LOC <= 700/file, functions <= ~150; engine and TM layer decomposed accordingly.
TypeScript strict, no `any` in props/state; engine public types exported from the
barrel. Boundary lint (section 4.7) enforces extractability. Tokens reused from
`www/src/index.css`, extracted to `www/src/styles/tokens.css` and imported by both the
single-page app and the cockpit (defined once). The engine ships neutral default tokens
and reads consumer CSS variables, so littleorgans restyles without code changes. Gate
adds `pnpm -C www lint && typecheck && test && build:cockpit`.

---

## 8. Persistence schema and location (DECISION: Electron-owned, backend schema reused)

Electron main owns reads/writes (section 3.12); `desktop/store.py` is the schema/IO
authority; the renderer reaches it via the IPC bridge.

### 8.1 Identity and location

Identity is `workspace_id(cwd) -> (slug, hash)` (`workspace.py:58-68`), path-scoped
(section 2.1). Keyed on `(slug, hash)`; no second identity.

- **Per-workspace layout** (survives runs):
  `~/.transport-matters/workspaces/{slug}/{hash}/desktop/layout.json`, under
  `workspace_root(cwd)` (`workspace.py:71-80`), a `desktop/` subdir so it never collides
  with run dirs.
- **Global launcher registry** (screen-1 recents/gallery):
  `~/.transport-matters/desktop/workspaces.json`. A convenience index; ground truth for
  "what exists" is still the workspace dirs.

Both live under the existing storage root (`storage_roots.py:DEFAULT_STORAGE_DIRNAME`,
`cli/disk_layout.py`).

### 8.2 Schema (frozen Pydantic v2, builtins-only typing)

`desktop/models.py`. The split tree is **n-ary** (canonical conventions), structurally
content-agnostic, with TM content only at the leaf:

```python
class PaneRef(BaseModel):
    model_config = ConfigDict(frozen=True)
    pane_id: str
    kind: str                       # "transcript" | "terminal" | "wire" | "artifact"
    agent_session_id: str | None    # which agent (None for shared viewers)
    content_ref: str | None         # artifact path for an artifact pane; else None

class SplitNode(BaseModel):
    model_config = ConfigDict(frozen=True)
    orientation: str                # "row" | "col"
    sizes: list[float]              # fractions summing to 1; len == len(children)
    children: list["LayoutNode"]

LayoutNode = PaneRef | SplitNode    # discriminated recursive n-ary split tree

class WorkspaceLayout(BaseModel):
    model_config = ConfigDict(frozen=True)
    slug: str; hash: str
    mode: str                       # "tiling" | "floating"
    tree: LayoutNode | None
    floating: list[PaneRef]
    artifact_pins: list[str]
    updated_at: str

class DesktopWorkspaceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    slug: str; hash: str; root: str; display_name: str
    created_at: str; last_opened_at: str
```

### 8.3 Access

`desktop/store.py`: pure `load_layout(slug, hash)`, `save_layout(WorkspaceLayout)`,
`list_workspaces()`, `upsert_workspace(entry)`. Writes are atomic (temp file +
`os.replace`), matching `manifest.py:write`(55-66). No DB; JSON files keyed by identity
(only SQLite is the rebuildable tier-2 index). The backend persists/returns these; it
never interprets layout geometry. Live free-canvas pixel geometry is a frontend runtime
mirror, snapshotted into `floating` on save.

---

## 9. UX design (folded; canonical conventions)

The cockpit is a power-user workbench for many live agents inside one workspace.
Baseline WCAG 2.2 AA plus WAI-ARIA APG keyboard conventions. The `agentSummary` pane is
deferred post-v1.

### 9.1 Design system

Dark, low-glare base (focused engineering room, often dim, several streaming panes).
Keep the existing product language (dark layers `--color-well/canvas/surface/raised/hover`,
six stable agent rails, one bright accent, JetBrains Mono, square corners radius 0,
chiaroscuro `--shadow-rgb`/`--highlight-rgb`) and add cockpit-specific tokens rather
than replacing the app theme. Cockpit tokens (oklch surface scale, text tiers meeting
AA, focus ring >= 2px and >= 3:1, agent rails, rawness gradient
`--rawness-transcript/terminal/wire/artifact`, spacing scale, type scale, motion
easings/durations) are added beside `www/src/index.css`. Contrast: body text >= 4.5:1
(current 14.6:1), meaningful muted text >= 4.5:1 (current 6.6:1); faint labels are
decorative chrome only; state never relies on color alone.

### 9.2 Layout patterns

Content-driven breakpoints: `bp-min` (<840px, focused-pane guard, floating editing
disabled), `bp-compact` (840-1023, focused pane + collapsible rail, bottom artifact
shelf), `bp-workbench` (1024-1279, two zones), `bp-studio` (1280-1599, default rawness
row transcript 34% / terminal 42% / wire 24%, bottom artifact shelf), `bp-lab`
(1600-2199, agent rows/cols + right artifact rail, floating mini-map), `bp-wall`
(>=2200, two agent groups + rail, persistent mini-map).

Default presets (saved split-tree templates; never change pane content contracts):
`rawness-row` (one agent, `row([transcript, terminal, wire], [0.34, 0.42, 0.24])`),
`agent-stack` (multi-agent, `col([agentGroup...], even)` each `rawness-row`),
`terminal-command` (terminal 70%, transcript/wire docked 15%), `wire-audit` (wire 50% /
transcript 30% / terminal 20% + artifact rail), `artifact-review` (artifact 52% /
transcript 24% / wire 24%, terminal docked), `focus-plus-dock` (active 78% / dock 22%).

Canvas regions: header strip (workspace name, branch, live agent count, capture health,
mode, preset; min 44px), command bar (APG toolbar roving focus), canvas body (engine,
no TM imports), pane chrome (title, agent rail, kind badge, live state, controls),
artifact rail/shelf, leader overlay.

### 9.3 Interaction model

**Launcher** (DECISION: project gallery primary, with command-palette overlay). Gallery
teaches workspace memory and metadata; the palette keeps expert throughput high.
Spatial recents wait until thumbnails are generated from layout geometry (not
screenshots). Create/open/remember: `Open workspace` resolves canonical path and
computes identity via the existing slug/hash model; provider choice is deferred to `Add
agent` inside the canvas; the canvas restores last mode, preset, pinned artifacts, last
focused pane. Empty state shows one primary action, one drop target, one explanation;
no provider buttons.

**Layout editing**: pointer (`Edit layout`) or keyboard (`Ctrl+B` then `e`). Gutters
expand to 10px visual with 24px hit zones; every drag has a keyboard equivalent (focus
handle with `Tab`, resize with arrows, faster with `Shift+Arrow`, balance `B`, confirm
`Enter`, cancel `Escape`). Splits insert n-ary siblings; mismatched orientation wraps
the pane in a new group. Minimum pane 260x180 in tiling; below minimum, collapse
lowest-priority panes into a dock.

**Preset switching / zoom / modes**: preset switch animates via FLIP; content
subscriptions never remount (a pane may change size, never identity). Zoom focus is a
first-class layout, not an overlay; restore via `Escape` / repeat / `Restore layout`.
On zoom, terminal panes take DOM focus after the animation; other kinds focus the pane
heading (`tabindex="-1"`) so screen-reader users hear context first. Mode switch
(`tiling` <-> `floating`) is the showpiece: capture old rects, compute new rects from
the same pane ids, freeze content layers visually while live streams keep running,
animate transform + opacity only, fade gutters to outlines.

**Keyboard leader** (default `Ctrl+B`, rebindable; `Ctrl+B Ctrl+B` sends literal):
`z` zoom, `h/j/k/l` directional focus, `e` edit, `p` presets, `m` mode, `a` add agent,
`r` reset preset, `[` `\` `]` focus transcript/terminal/wire of the active agent, `1..9`
focus agent group, `?` help. Leader overlay appears after 80ms, polite announce on first
use per session.

### 9.4 Artifact arrival and provenance [PROVISIONAL]

Rail placement: right rail (320px, 240-520) at `bp-lab`+, bottom shelf (180px) at
`bp-studio` and narrower, collapsed badge in zoom. A new artifact creates or updates an
`artifact` pane through the engine event API. Dedupe key is the normalized path; if
absent, a stable id from `session_id` + `turn_id` + content type + ordinal. Same path
updates one pane (220ms edge glow, timestamp, `Updated from turn N`). New arrival slides
12px and fades in with **no focus change.** Provenance click selects the originating
turn across transcript and wire panes (pivoting `turn_id` -> `exchange_id` for the wire
pane, section 7.6), scrolls into view, applies a 1400ms highlight; if the source pane is
hidden, an inline `Open source panes` action (no layout move without user action).
Lifecycle: pin (persisted), dismiss, auto-retire unpinned after 30 min idle or >20
count. Unknown content uses a safe text shell with copy-path / open-external /
provenance.

### 9.5 Rawness gradient

| Pane | Visual role | Treatment | Label |
| --- | --- | --- | --- |
| `transcript` | Clean narrative | More spacing, 75ch cap, calm green marker, rendered blocks | `Transcript` |
| `terminal` | Live operation | Dense monospace, strong caret, warm ivory marker, input indicator | `Terminal` |
| `wire` | Raw evidence | Highest density, amber marker, byte/header affordances, request ids | `Wire` |
| `artifact` | Produced output | Purple marker, content-type badge, provenance crumb | `Artifact` |

Color never carries pane kind alone (always label + icon + `aria-label`). Agent rail
color identifies the agent consistently across all panes. Rawness increases by density,
border texture, and metadata exposure, never by reducing readability.

### 9.6 Transition choreography and reduced motion

Motion tokens: button press 90ms, hover/focus 120ms, preset switch 280ms zoom 260ms
(`ease-out-quint`), agent spawn 320ms (55ms stagger), artifact arrival 220ms, tiling ->
floating 480ms / floating -> tiling 420ms (`ease-out-expo`). Animate transform + opacity
only; during FLIP live terminal and wire streams keep receiving data (visual freeze is a
compositor layer, not a data pause); mode switch stays under 500ms and input stays
responsive. `prefers-reduced-motion`: immediate rect update + 80ms opacity crossfade; no
scale/parallax/drift; an in-app `Motion: minimal` overrides OS no-preference.

### 9.7 Components

Content-agnostic shell components (`PaneShell`, `SplitHandle`, `LayoutCommandBar`,
`PresetSwitcher`, `LeaderOverlay`) and TM-edge components (`WorkspaceLauncher`,
`CanvasFrame`, `AgentLauncher`, `ArtifactRail`, `ArtifactSurface`, `ProvenanceButton`)
each implement the eight interaction states (default, hover, active, focus-visible,
disabled, loading, error, empty), responsive behavior per breakpoint, APG accessibility
(roles, roving focus, labelled regions, focus return), and FLIP-only layout animation.
`SplitHandle` uses `role="separator"` with `aria-orientation`/`aria-valuenow/min/max`,
arrow-key resize (2%), `Shift+Arrow` (10%), `Home`/`End` to min/max. The shared types
align to the canonical conventions (`PaneKind`, `LayoutMode`, `ContentType`,
`ArtifactProvenance`).

### 9.8 Accessibility (summary)

All functionality keyboard-reachable; leader commands have pointer equivalents; drag /
split / resize have keyboard and single-pointer alternatives; `Tab` order follows DOM
order (workspace, command bar, agent group, pane kind, artifact rail); no positive
`tabindex`. Focus ring visible everywhere; focus never disappears after pane close,
preset/mode switch, or artifact jump; during FLIP logical focus stays on the same pane
id. Regions labelled; pane labels include agent id, kind, live state; live updates
polite (assertive only when user action is blocked). Minimum target 24x24 (32x32
preferred for chrome); split handles keep a 24px hit zone. Terminal receives all
keystrokes except the leader sequence; reconnect preserves scrollback when the backend
replays.

---

## 10. Unified slice plan (layout-lab-first)

Each slice is a small dual-signed PR. Gate: `cd api && just ci` plus the frontend
`pnpm -C www lint && typecheck && test && build:cockpit` (and the boundary lint).
LOC budgets are per file (<=700) and per function (<=~150).

### Slice 1: Skeleton (thinnest end-to-end loop)

Goal: launcher -> spin one claude agent (reuse launch core, headless) -> ONE `wire`
pane in a single-pane Electron shell (single-instance, preload IPC, loopback-served
renderer, packaging + smoke). Begin `AgentBackendProvider` scoped store; wire pane
reuse; minimal single-pane engine. Codex parity after claude.
- Backend: `cli/ports.py` `allocate_port_triple`; `manifest.py` `pty_ws_port` +
  `desktop_token`; `cli/agent_cmd.py` reusing `prepare_launch` + the public claude
  factory + `run_with_workspace_manifest`; startup JSON line (incl. `session_id`,
  token); loopback http for the renderer + `cors_origins`/ws-origin allowlist.
- Frontend: minimal single-pane engine (split tree, `LayoutCanvas`); `AgentBackendProvider`
  (scoped transport + QueryClient + SSE + uiStore, begun); wire pane reusing
  `ExchangeList`/`ExchangeDetail`; Electron single-instance lock, preload IPC bridge,
  `backendProcess` generalized toward N (one for now), packaging includes
  `www/dist-cockpit` + smoke asserts the renderer loads.
- Reuse: `desktop/src/*`, `ExchangeList.tsx`, `ExchangeDetail.tsx`, `useExchangeStream`,
  `api.ts`, `workspace_id`, the launch core.
- Gate: launch the cockpit, open a workspace, spin one claude agent, see its live wire
  pane in the engine shell over loopback http; `just ci` + frontend lint/build green.

### Slice 2: Layout engine (the reusable centerpiece)

Goal: recursive n-ary split-tree, `tiling` + `floating`, presets (even/main/grid/group),
focus/zoom, FLIP transitions, pane shell (drag/resize), the engine extraction boundary
lint, **and the transition stress / frame-timing harness PROVING 60fps here**
(DECISION [review-frontend #7]: the harness lands WITH this slice, not deferred to
polish, so the tech pick is proved, not asserted).
- Frontend: `www/src/engine/**` (core reducers, react bindings, `LayoutCanvas`,
  gestures, presets, `PaneShell`/`SplitHandle`/`LayoutCommandBar`/`PresetSwitcher`/
  `LeaderOverlay`); `no-restricted-imports` boundary lint; stress harness (spawn N
  synthetic panes, drive mode switches/zooms, assert frame timing) for tiled, floating,
  and zoom transitions.
- Reuse: tokens extracted to `www/src/styles/tokens.css`.
- Gate: boundary lint green; harness asserts sustained 60fps for tiled/floating/zoom.

### Slice 3: Multi-agent + persistence

Goal: N agents per workspace; Electron main owns layout/workspace JSON; **complete
de-singletonization.**
- Backend: `desktop/registry.py` discovery over `read_all`; `desktop/store.py` +
  `desktop/models.py` (n-ary schema, Electron-owned per section 3.12).
- Frontend: per-agent `AgentBackendProvider` (one per agent); remove EVERY singleton
  import from reusable pane code (incl. `applyExchangeEvent` forwarding-state +
  `ExchangeDetail` 404 clear) [review-frontend #4]; `AgentHandle.sessionId`; per-agent
  rail coloring; layout persistence via IPC.
- Gate: two agents in one workspace are discoverable; a workspace reopens to its
  remembered layout; no singleton import remains in reusable pane code.

### Slice 4: Terminal pane

Goal: the one new backend capability + the xterm pane. Codex parity.
- Backend: `desktop/pty_bridge.py` (master_fd reader, 256 KiB ring, per-client queues,
  resize, framing) + `desktop/pty_ws.py` (ASGI app + routes, pre-split per section 3.8);
  `supervisor_pty_process.py` `_open_child_on_pty` + `spawn_headless_pty` +
  `set_pty_winsize`; `supervisor_core.py` `headless_pty`; `desktop/agent_host.py`
  headless run loop; token via stdout only.
- Frontend: `terminal` pane (`@xterm/xterm` + fit + webgl, attach, resize debounced to
  `onLayoutAnimationComplete`, reconnect + ring replay).
- Gate: a real claude/codex on a headless PTY; xterm is interactive with correct
  resize, reconnect, and replay.

### Slice 5: Transcript pane [PROVISIONAL - pending transcript redesign]

Goal: premium read-only transcript + live append.
- Backend: tier-1 transcript-IR read surface (re-normalize the owned transcript via the
  adapter; NOT the lossy tier-2 timeline) [review-backend #1].
- Frontend: `AgentHandle.sessionId` consumed for the timeline/pivot routes; SSE
  `transcript_turn` branch + scoped transcript query keys [review-frontend #3]; premium
  read-only render reusing `ContentBlockRow`, live append.
- Gate: the transcript pane renders full IR and live-appends on a committed turn.

### Slice 6: Artifacts [PROVISIONAL - pending transcript redesign]

Goal: ingest-time detection + viewer registry + artifact dock + provenance.
- Backend: `index/artifacts.py` classifier from `NormalizedTurn.parts` (NOT a tier-2
  query) [review-backend #1]; `IndexJob.events: tuple[dict, ...]` emitting
  `transcript_turn` + N `artifact` events atomically post-commit, dedupe on
  `(session_id, turn_id, tool_use_id)` [review-backend #2].
- Frontend: viewer registry (md/image); artifact dock with spawn policy
  (dedupe-to-update, no focus theft); provenance link (discriminated target + pivot
  `turn_id` -> `exchange_id`) [review-frontend #5].
- Gate: a `Write` produces an `{"type":"artifact"}` SSE event with correct
  `session_id`/`turn_id`/`path`; the same path updates one pane without stealing focus;
  provenance resolves via the timeline/pivot.

### Slice 7: Premium polish

Goal: full creative launcher (gallery + command-palette per UX), transition showpiece,
a11y audit, visual pass.
- Frontend: eight-state coverage audit, keyboard model, transition choreography per UX,
  performance harness extension, screen-reader pass.
- Gate: keyboard-only path (open workspace, add agent, switch preset, resize split,
  zoom, open artifact, jump provenance); reduced-motion correctness; mode switch <500ms.

---

## 11. Spec acceptance bar and conventions

- **Grounded** in actual repo seams, verified and cited as `path:Symbol` with line
  ranges; never assumed.
- **DRY**: reuses the launch core + `www/` components; zero parallel implementations;
  the public-factory refactor exists so no `_`-prefixed name is imported cross-module.
- **Engine is content-agnostic and extractable** to littleorgans; no TM-content import
  in `www/src/engine/**`, enforced by the boundary lint (the TS analogue of the Python
  AST privacy test).
- **Repo invariants**: import DAG acyclic (`desktop/` a terminal sink above
  `cli`/`server`; `index/artifacts.py` imports `ir` only; no `storage -> index`
  back-edge); LOC <=700/file and functions <=~150; builtins-only typing; Pydantic v2
  frozen models; IR frozen.
- **Incrementally shippable**: slice 1 is the thinnest loop (launcher -> one agent ->
  one wire pane in the generic shell); slices 5 and 6 are provisional pending the
  transcript redesign.
- **Internally consistent** across backend, frontend, and UX, especially the pty-ws,
  artifact-event (provisional), and transcript-IR-read (provisional) contracts.
- **Canonical conventions** (section 5) are binding across all sections.
- Gate for every slice: `cd api && just ci` plus the frontend lint/typecheck/test/build
  and the boundary lint. Build slices land as small, dual-signed PRs.

### Residual conflict (could not be fully eliminated)

**Codex image-gen artifact paths** remain a real gap, surfaced by the backend spec and
unaddressed by the decisions. The codex adapter (`index/adapters/codex.py:82-127`) does
not surface `~/.codex.lilo/generated_images/<id>/*.png` paths; they fall to
`UnknownBlock`. The classifier's image branch reads `ImageBlock.source["path"]` once the
adapter populates it. Until then, codex image artifacts are logged, not emitted. This is
tracked as a fast-follow codex-adapter change within the slice-6 (provisional) scope;
ship claude `Write`/`Edit` + codex file edits first.
