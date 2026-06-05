# Transport Matters Desktop Cockpit: Backend Spec

Author: backend-engineer/claude. Status: first author pass, awaiting codex peer review.
Charter: `transport-matters-desktop-cockpit/CHARTER.md`. Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`.

This spec resolves the charter's "Backend (backend-engineer pair)" open questions and
the provisional stream/contract surface into a buildable design. Every reuse claim is
grounded in the actual repo and cited as `path:symbol` with line ranges verified against
the current tree (`main` @ `d8b944a`). The layout engine is the frontend's concern; this
spec covers the per-agent backend each pane subscribes to.

---

## 0. Summary and the one new capability

The desktop is N independent agents per workspace, each agent a managed Transport Matters
run. The backend already produces almost everything the cockpit needs:

- Pane 3 (wire): existing capture stream + REST, reused verbatim.
- Pane 1 (transcript) and artifact detection: existing tier-2 transcript IR + the
  post-commit live push, reused.
- Multi-agent discovery: existing run manifest registry, reused.

There is exactly **one new backend capability**: a per-agent **PTY-over-websocket** so the
child harness, which in a GUI has no host TTY, runs on a pseudo-terminal whose master is
streamed to xterm.js (pane 2). Everything else is composition and a thin derivation layer.

The launch core is reused, not reimplemented (charter locked decision 6). The new code is a
`desktop/` package that sits above the existing layers and orchestrates them, plus a small
headless variant of the already-present PTY spawn.

---

## 1. Grounded reuse map

Each row is a capability the cockpit needs and the existing symbol that provides it. Verdict
is one of: REUSE (call as-is), EXTEND (add an optional field or sibling), NEW (must build).

| Capability | Existing symbol (file:lines) | Verdict |
| --- | --- | --- |
| Per-provider launch profile (mint, prepare, argv) | `cli/launch_profile.py:LaunchProfile`/`ClaudeLaunchProfile`(110-153)/`CodexLaunchProfile`(156-205); `PROFILES`(213-216) | REUSE |
| Mint + prepare owned session | `cli/launch_profile.py:prepare_managed_session`(219-250) | REUSE |
| Persist durable owned-launch facts | `cli/launch_profile.py:persist_owned_session_facts`(253-278) | REUSE |
| Resolve ports, run_id, storage, working dir | `cli/launch_runtime.py:prepare_launch`(335-397), `resolve_launch_ports`(245-285), `resolve_storage_dir`(288-300), `new_run_id`(330-332) | REUSE |
| Free-port allocation | `cli/ports.py:allocate_port_pair`(39-77) | EXTEND (triple) |
| mitmdump argv (proxy bootstrap) | `cli/launch_runtime.py:build_mitmdump_argv`(400-424) | REUSE |
| Shared launch env (addon contract) | `cli/launch_runtime.py:build_launch_env`(445-481) | REUSE |
| Managed child env (proxy/trust hardening) | `cli/launch_runtime.py:build_managed_child_env`(484-531) | REUSE |
| Claude invocation factory (reverse proxy) | `cli/start_cmd.py:_build_start_invocation`(58-141) | REUSE via public wrapper |
| Codex invocation factory (explicit proxy + CA) | `cli/codex_cmd.py:_build_codex_invocation`(146-228) | REUSE via public wrapper |
| Per-run lock + manifest lifecycle | `cli/launch_runtime.py:run_with_workspace_manifest`(534-576) | REUSE |
| Process supervision (spawn/wait/terminate/signals) | `supervisor_core.py:ProcessSupervisor`(19-299) | REUSE |
| PTY create + child wiring (currently TTY-shuttled) | `supervisor_pty_process.py:spawn_with_pty`(27-170) | EXTEND (extract core + headless sibling) |
| PTY winsize / ioctl pattern | `supervisor_pty_process.py`(64-69,135-138); `supervisor_pty.py:install_parent_cbreak`(30-45) | REUSE pattern |
| Workspace identity slug/hash | `workspace.py:workspace_id`(58-68), `workspace_root`(71-80), `run_root`(83-92) | REUSE |
| Run manifest schema + registry read | `manifest.py:Manifest`(34-52), `read_all`(98-113), `read`(69-95), `write`(55-66) | EXTEND (pty_ws_port, token) |
| `list` surface (discovery) | `cli/instances.py:list_instances`(42-69) | REUSE |
| Per-run web API (FastAPI app + CORS + health) | `main.py:create_app`(52-96) | REUSE |
| Web server bind + tier-2 boot inside addon | `addon_runtime.py:load_runtime`(76-163) | REUSE |
| Live SSE stream | `api/v1/stream.py:stream_exchanges`(20-42); `broadcast.py:broadcast` (emit/subscribe/unsubscribe) | REUSE |
| Wire exchange REST | `api/v1/exchanges.py` router (350 LOC) | REUSE |
| Transcript / index REST (timeline, sessions, pivot, raw) | `api/v1/index_routes.py`(149 LOC) | REUSE |
| Breakpoint arm/release REST | `api/v1/breakpoint_routes.py`(265 LOC) | REUSE |
| Post-commit live push (the emit seam) | `index/writer.py:IndexWriter`(53-204), `IndexJob.event`(43); injected `emit=broadcast.emit` at `addon_runtime.py:load_runtime`(116) | REUSE seam |
| Transcript turn IR + content blocks | `index/adapters/base.py:NormalizedTurn`(133-151); `ir.py:ContentBlock`(68-71), `ToolUseBlock`(25-32), `ToolResultBlock`(35-42), `ImageBlock`(53-58) | REUSE |
| Artifact path extraction from tool records | (derived from `ToolUseBlock.input` / `ToolResultBlock.content`) | NEW (`index/artifacts.py`) |
| Workspace + layout persistence | (none) | NEW (`desktop/store.py`) |
| Headless agent run loop + pty-ws app | (none) | NEW (`desktop/`) |

Note on citations: `main.py`, `broadcast.py`, `addon_runtime.py`, `workspace.py`,
`manifest.py`, `config.py`, `env_keys.py`, `ir.py`, `supervisor_*.py` are top-level modules
under `api/src/transport_matters/`. `api/v1/*` is `api/src/transport_matters/api/v1/*`.

---

## 2. Process topology: per-agent subprocess (decided), not a daemon

### 2.1 Today's per-run shape (grounded)

A single `transport-matters claude|codex` launch is three processes:

1. **Launcher** (the CLI process). Resolves launch state via `prepare_launch`
   (`cli/launch_runtime.py:335`), mints the session via `prepare_managed_session`
   (`cli/launch_profile.py:219`), takes the per-run lock and writes the manifest via
   `run_with_workspace_manifest` (`cli/launch_runtime.py:534`), then spawns and supervises
   the next two processes through `ProcessSupervisor` (`supervisor_core.py:19`).
2. **mitmdump** (the proxy). Argv from `build_mitmdump_argv` (`cli/launch_runtime.py:400`),
   `--listen-host 127.0.0.1`. It loads the addon, which calls `load_runtime`
   (`addon_runtime.py:76`): this boots tier-1 storage, the tier-2 `IndexWriter` +
   `TranscriptTailer`, the post-commit `emit=broadcast.emit` push, and a uvicorn server
   hosting `create_app()` on `127.0.0.1:{web_port}` (`addon_runtime.py:148-155`).
3. **Child** (claude or codex). Spawned by the launcher (`cli/runner.py:run_children`(362),
   `_run_client_children`(395)). Today it runs foreground attached to the host TTY, or on a
   PTY shuttled to the host terminal when `pty=True` (`supervisor_core.py:spawn`(56-167)).

Isolation is per-run: own proxy port, own web API, own storage root, own manifest. The
manifest (`manifest.py:Manifest`(34-52)) records `proxy_port`, `web_port`, `storage_dir`,
`run_id`, `slug`, `hash`, `home_dir`.

### 2.2 Decision: one launcher subprocess per agent

The desktop spawns one headless launcher subprocess **per agent**, reusing the launch core
verbatim. Electron's main process is a pure localhost client (websocket + HTTP); it never
spawns proxies or children itself.

Rejected alternative: a single session-manager daemon multiplexing all agents.

Reasons (charter asks for a decision with reasons):

- **Preserves the locked isolation invariant** (charter decision 6). Each agent already
  requires its own proxy port and storage root; a daemon would have to re-multiplex these
  and re-own the per-run lock/manifest lifecycle that `run_with_workspace_manifest` already
  provides.
- **Maximal launch-core reuse.** A subprocess calls `prepare_launch`, `prepare_managed_session`,
  `build_mitmdump_argv`, `build_launch_env`, `build_managed_child_env`, the invocation
  factories, `run_with_workspace_manifest`, and `ProcessSupervisor` unchanged. A daemon would
  fork a parallel supervision and retry path, violating DRY (charter spec bar).
- **Crash isolation.** One agent's launcher or child crashing cannot take down peers. A
  daemon is a single point of failure for every workspace.
- **Discovery is free.** The existing manifest registry (`read_all` (`manifest.py:98`),
  `list_instances` (`cli/instances.py:42`)) already models "many independent runs". One
  agent maps 1:1 to one manifest, so multi-agent discovery is the existing surface.
- **Honors locked decision 7** (Electron out of the Python env). The Python subprocess owns
  the PTY and proxy; Electron only connects over localhost. No node-pty, no node-side launch.

Cost: three OS processes per agent (launcher, mitmdump, child). This equals today's per-run
cost. At the charter's target scale (tens of agents) this is acceptable; the daemon's only
real win is process count, which is not a constraint here.

### 2.3 Desktop per-agent shape

Identical to 2.1 with two changes confined to the launcher:

- The child is spawned on a **headless PTY** (no host TTY), section 4.
- The launcher runs an **asyncio PTY-websocket host** bound to `127.0.0.1:{pty_ws_port}`
  instead of shuttling the PTY to a terminal, section 5.

mitmdump and the child are unchanged. The wire/transcript web API stays in the mitmdump
process on `web_port`. So an agent exposes two localhost endpoints to the UI:

- `http://127.0.0.1:{web_port}` (mitmdump process): wire REST, transcript REST, SSE, breakpoint.
- `ws://127.0.0.1:{pty_ws_port}` (launcher process): the terminal.

```
Electron renderer (xterm.js, chat, wire, viewers)  ── localhost only ──┐
                                                                       │
  per agent A                          per agent B                     │
  ┌─────────────────────────┐         ┌─────────────────────────┐     │
  │ launcher (headless)      │         │ launcher (headless)      │     │
  │  asyncio pty-ws :ptyA ◄──┼─────────┼──────────────────────── ◄─────┤ keystrokes/resize, pty bytes
  │  ProcessSupervisor       │         │  ...                     │     │
  │   ├─ mitmdump :proxyA    │         │                          │     │
  │   │   addon: web :webA ◄─┼─────────┼──────────────────────── ◄─────┘ wire/transcript REST + SSE
  │   └─ child (headless PTY)│         │                          │
  └─────────────────────────┘         └─────────────────────────┘
```

---

## 3. GUI/headless launch mode (reuses the launch core)

### 3.1 Entry point

Add a headless launch command wired into the existing Typer app (`cli/__init__.py:main`(84)):

```
transport-matters agent --client {claude|codex} --work-dir DIR \
    [--proxy-port N] [--web-port N] [--pty-ws-port N] [--home-dir DIR] [--no-system-prompt]
```

It composes the existing per-provider invocation factories and runs the headless run loop
(section 5.4) instead of the interactive TTY path. It prints one JSON line on stdout with the
resolved `{run_id, slug, hash, proxy_port, web_port, pty_ws_port, web_url, pty_ws_url, token}`
so the Electron main process can connect without scraping logs, then it stays in the
foreground of its own subprocess for the run's lifetime.

### 3.2 Reuse the invocation factories without breaking the privacy boundary

`_build_start_invocation` (`cli/start_cmd.py:58`) and `_build_codex_invocation`
(`cli/codex_cmd.py:146`) are module-private (leading underscore) and cannot be imported
across modules (PROJECT.md privacy rule, enforced by `test_private_import_boundary.py`). Two
honoring options; this spec picks (A):

- **(A) Public re-export in the owning module.** Add a public `build_start_invocation` and
  `build_codex_invocation` in `start_cmd.py` / `codex_cmd.py` that the existing private names
  delegate to (or rename the private to public and update the two in-module call sites). The
  desktop command imports the public names. Smallest change, keeps the factory logic where it
  lives. This is the recommended seam.
- (B) A new `desktop/launch.py` that rebuilds the factory. Rejected: duplicates the env +
  argv + ManagedClient assembly already in the two builders (DRY violation).

The factory contract is already provider-neutral:
`build_invocation(proxy_port, web_port) -> (mitmdump_argv, launch_env, ManagedClient | None)`.
`ManagedClient` (`cli/runner.py`) carries `name`, `display_name`, `argv`, `env`, `cwd`. The
desktop run loop calls the factory exactly as `run_client_with_retry` does today.

### 3.3 What is reused, end to end

For one agent, the headless command performs, in order:

1. `resolve_working_dir` + `prepare_launch` (`cli/launch_runtime.py:232,335`) to resolve
   working dir, the port triple (section 6.2), `run_id`, and storage dir.
2. `PROFILES[client]` (`cli/launch_profile.py:213`) then `prepare_managed_session`
   (`:219`) to mint + prepare the owned session (claude creates its transcript via
   `--session-id`; codex seeds a resumable rollout). Codex also resolves its CA via
   `_resolve_codex_ca_certificate_or_exit` (`cli/codex_cmd.py:47`).
3. `build_start_invocation` / `build_codex_invocation` (section 3.2) to get the
   `build_invocation` factory. Claude uses proxy mode `reverse:{upstream}` and child env
   `ANTHROPIC_BASE_URL=loopback_http_url(proxy_port)` (`cli/start_cmd.py:124-128`,
   `cli/net.py:loopback_http_url`(11)). Codex uses proxy mode `regular` with
   `HTTP(S)_PROXY=loopback_http_url(proxy_port)` and `CODEX_CA_CERTIFICATE` injected by
   `build_managed_child_env` (`cli/launch_runtime.py:484`, `cli/codex_cmd.py:198-205`).
4. `run_with_workspace_manifest` (`cli/launch_runtime.py:534`) to take the per-run lock and
   write the manifest (extended schema, section 6.1), passing `home_dir` through.
5. `persist_owned_session_facts` (`cli/launch_profile.py:253`) inside the lock to write the
   durable `sessions.json` for rebuild survival.
6. The headless run loop (section 5.4): spawn mitmdump (log_path) + child (headless PTY) via
   `ProcessSupervisor`, then serve the pty-ws and supervise.

No proxy bootstrap, env injection, mint logic, port logic, or manifest logic is
reimplemented. The only new spawn behavior is the headless PTY.

---

## 4. PTY ownership and the headless spawn

### 4.1 Decision: Python `pty` + asyncio websocket, not node-pty

- The PTY create + child wiring already exists in Python (`supervisor_pty_process.py:spawn_with_pty`(27)),
  and `ManagedProcess` (`supervisor_models.py:17-36`) already carries `master_fd`,
  `stop_event`, `shuttle_thread`, `old_termios_attrs`, `prev_sigwinch_handler`.
- node-pty would move PTY ownership into the Electron main process, which would then have to
  spawn the child directly and reimplement proxy bootstrap, env hardening, mint, and manifest
  in node. That violates locked decisions 6 (reuse launch core) and 7 (Electron out of the
  Python env). Rejected.

So the launcher (Python) owns the master fd; Electron is a websocket client.

### 4.2 The gap in the existing PTY path

`spawn_with_pty` assumes a **host TTY**: it reads `sys.stdin.fileno()` and bails to inherited
stdio if it is not a tty (`supervisor_pty_process.py:40-55`), puts the parent terminal into
cbreak (`install_parent_cbreak`, `supervisor_pty.py:30`), runs `pty_shuttle`
(`supervisor_pty.py:48`) between the parent terminal and the master, and installs a SIGWINCH
handler that re-reads the parent winsize (`supervisor_pty_process.py:135-140`). In a GUI there
is no parent TTY, so this whole branch is wrong for the desktop.

### 4.3 Refactor: extract the PTY-create core, add a headless sibling

Extract the terminal-independent core from `spawn_with_pty` and reuse it for both variants.
Keep both functions in `supervisor_pty_process.py` (currently 206 LOC; the extraction nets a
small delta, staying well under 700).

```python
# supervisor_pty_process.py  (builtins-only typing)
def _open_child_on_pty(
    name: str,
    argv: list[str],
    *,
    env: dict[str, str] | None,
    cwd: Path | None,
    cols: int,
    rows: int,
) -> tuple[subprocess.Popen[bytes], int]:
    """Open a pty, size the slave, spawn argv wired to the slave, close the
    parent slave copy, return (popen, master_fd). No parent-terminal coupling."""
    master_fd, slave_fd = pty.openpty()
    _set_winsize(slave_fd, cols, rows)            # TIOCSWINSZ, pattern from lines 64-69
    try:
        popen = subprocess.Popen(
            argv, env=env, cwd=str(cwd) if cwd is not None else None,
            stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
            start_new_session=True,
        )
    finally:
        with contextlib.suppress(OSError):
            os.close(slave_fd)                    # mirrors lines 115-120
    return popen, master_fd


def spawn_headless_pty(
    name: str,
    argv: list[str],
    *,
    env: dict[str, str] | None,
    cwd: Path | None,
    cols: int = 80,
    rows: int = 24,
) -> ManagedProcess:
    """PTY child for a GUI: no host TTY, no cbreak, no parent shuttle, no
    parent SIGWINCH. The pty-ws host owns master_fd I/O and resize."""
    popen, master_fd = _open_child_on_pty(name, argv, env=env, cwd=cwd, cols=cols, rows=rows)
    return ManagedProcess(
        name=name, popen=popen, process_group=popen.pid, master_fd=master_fd,
        # stop_event / shuttle_thread / old_termios_attrs / prev_sigwinch_handler stay None
    )


def set_pty_winsize(master_fd: int, cols: int, rows: int) -> None:
    """TIOCSWINSZ on the master so the kernel signals SIGWINCH to the child.
    winsize is (rows, cols, xpixel, ypixel)."""
    with contextlib.suppress(OSError):
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
```

`spawn_with_pty` is refactored to call `_open_child_on_pty` for the create step, then keep its
existing cbreak + shuttle + SIGWINCH wiring for the TTY case. `teardown_pty`
(`supervisor_pty_process.py:173-206`) already no-ops cleanly on the headless `ManagedProcess`
(every terminal field is None) and closes `master_fd`, so it is reused as the headless cleanup.

`ProcessSupervisor` gains a headless path. Smallest change: add `headless_pty: bool = False`
to `spawn` (`supervisor_core.py:56`); when set, call `spawn_headless_pty` and do not require
`foreground` or a host TTY. This keeps one spawn entry point and one `_children` registry for
`terminate_all` / signal handling (`supervisor_core.py:250-288,173-199`).

---

## 5. Terminal contract: PTY-over-websocket

This is the single new stream the frontend consumes for pane 2. It is the binding contract
between this spec and `spec-frontend.md` (xterm.js attach).

### 5.1 Endpoint and auth

```
ws://127.0.0.1:{pty_ws_port}/pty?token={run_token}
```

- Bound to `127.0.0.1` only (loopback), matching `build_mitmdump_argv` and the uvicorn host
  in `load_runtime` (`addon_runtime.py:149`).
- One agent serves exactly one PTY (one child), so the path needs no session id; `run_id`
  identity is implicit in the port. The token scopes the connection (section 8).
- Origin check: reject ws upgrades whose `Origin` is not the Electron app origin or an
  allowlisted dev origin, reusing the CORS origin list shape in `config.py`
  (`cors_origins`).

### 5.2 Framing (xterm.js-friendly: binary = data, text = control)

Server to client:

- On attach, one text control frame: `{"type":"hello","cols":C,"rows":R,"scrollback_bytes":N}`.
- Then the scrollback ring (section 5.3) as one or more **binary** frames (raw PTY bytes).
- Then live **binary** frames: raw `master_fd` output bytes, unmodified.
- If the per-client outbound queue overflowed, a text frame `{"type":"gap"}` precedes the
  resumed binary stream so the UI can show a discontinuity.
- On child exit, a text frame `{"type":"exit","code":N}` then a normal close.

Client to server:

- **Binary** frames: raw stdin bytes (keystrokes, paste), written verbatim to `master_fd`.
  No escaping, no envelope.
- **Text** frames: JSON control. `{"type":"resize","cols":C,"rows":R}` calls
  `set_pty_winsize(master_fd, cols, rows)` (section 4.3). `{"type":"ping"}` is answered with
  a text `{"type":"pong"}`.

Rationale: keystrokes are binary and frequent, so they ride frames with zero envelope cost;
control is rare and structured, so it rides JSON. This is the convention xterm.js's attach
addon already expects, minimizing frontend glue.

### 5.3 Backpressure and scrollback

The child must never block on PTY write because the UI lagged (that would freeze the agent).
Therefore the master reader always drains:

- A single asyncio reader registered with `loop.add_reader(master_fd, ...)` reads available
  bytes and (a) appends to a fixed-size **scrollback ring** (default 256 KiB, byte-bounded)
  and (b) fans out to each connected client's bounded outbound queue.
- Per-client outbound queue is bounded (default 1 MiB or 1024 frames). On overflow, drop the
  oldest frames for that slow client and set its `gap` flag; the next flush emits one
  `{"type":"gap"}` text frame before resuming. The ring guarantees a reconnecting client
  re-syncs recent screen state.
- The reader never awaits a slow client, so `master_fd` is drained promptly and the child's
  PTY write buffer stays clear.

Attach-time replay is a raw-byte replay of the ring, which reconstructs the recent screen
(scrollback window), not full history. This is the v1 contract; full-history replay would
require a server-side terminal state model and is out of scope (section 11 open item).

Heartbeat: protocol-level ws ping/pong plus the application `ping`/`pong`. The 15s keepalive
cadence mirrors the SSE keepalive already in `stream_exchanges` (`api/v1/stream.py:29-31`).

### 5.4 Lifecycle (the headless run loop)

`desktop/agent_host.py` owns the loop. It runs uvicorn (a small ASGI app, section 7) on
`pty_ws_port` and uses the uvicorn lifespan to:

1. On startup: spawn mitmdump via `ProcessSupervisor.spawn(..., log_path=...)` (background,
   `supervisor_core.py:56`) and the child via `spawn(..., headless_pty=True)` (section 4.3),
   using the `(mitmdump_argv, env, ManagedClient)` from the invocation factory. Register the
   `master_fd` reader. Install signal handlers (`ProcessSupervisor.install_signal_handlers`,
   `supervisor_core.py:173`).
2. While serving: watch child + mitmdump liveness with `ProcessSupervisor.poll_any`
   (`supervisor_core.py:211`) on a periodic `loop.call_later`, or `asyncio.to_thread` around
   `wait_any` (`:219`). On child exit, emit `{"type":"exit","code":N}` to clients and begin
   shutdown.
3. On shutdown (child exit, SIGINT/SIGTERM, or last detail): `teardown_pty`
   (`supervisor_pty_process.py:173`), then `ProcessSupervisor.terminate_all(grace_seconds=...)`
   (`supervisor_core.py:250`), then drop the manifest (already handled by
   `run_with_workspace_manifest`'s `finally`, `cli/launch_runtime.py:571-575`).

Port bind-failure retry: reuse `handle_bind_failure` (`cli/runner.py:225`) for the proxy/web
ports. The pty-ws port is allocated in the same triple (section 6.2); if uvicorn fails to bind
it, surface the failure on the startup JSON line and exit non-zero (the Electron main respawns
with a fresh triple). This keeps retry semantics consistent with the existing launcher.

---

## 6. Multi-agent registry, discovery, and ports

### 6.1 Manifest extension

Extend `Manifest` (`manifest.py:34-52`) with two optional fields, following the `home_dir`
precedent (optional with default, backward-safe for `read`/`read_all`):

```python
pty_ws_port: int | None = None     # set for desktop/headless agents only
desktop_token: str | None = None   # per-run auth token (section 8)
```

`run_with_workspace_manifest`'s `write_manifest_for` closure (`cli/launch_runtime.py:545-567`)
passes these through for the headless command. Interactive `claude`/`codex`/`start` leave them
None, so the `list`/`paths`/`instances` probes are unaffected.

### 6.2 Port triple

`allocate_port_pair` (`cli/ports.py:39-77`) opens both sockets on port 0 simultaneously so the
kernel cannot hand out a duplicate, then closes and returns the pair. Extend to a triple for
the desktop:

- Add `allocate_port_triple()` in `cli/ports.py` (same simultaneous-bind technique, three
  sockets), or have the desktop command call `allocate_port_pair` then allocate one more under
  the same constraint. `resolve_launch_ports` (`cli/launch_runtime.py:245`) is reused for the
  proxy/web pair; the pty-ws port is resolved alongside with the same "pinned or allocated"
  logic. Keep the simultaneous-open invariant so all three are distinct.

### 6.3 Discovery tied to the existing `list` surface

A workspace is `(slug, hash)` from `workspace_id(cwd)` (`workspace.py:58`). Its live agents are
the manifests under `~/.transport-matters/workspaces/{slug}/{hash}/*/manifest.json`.

- Reuse `read_all` (`manifest.py:98`) to enumerate all runs and `WorkspaceLock.is_held`
  (via `list_instances`, `cli/instances.py:42-69`) to distinguish live from stale, exactly as
  `transport-matters list` does today.
- `desktop/registry.py` filters `read_all(root)` by `(slug, hash)` to list a workspace's live
  agents, returning per agent: `run_id`, `cli`, `proxy_port`, `web_port`, `pty_ws_port`,
  `desktop_token`, `started_at`, `pid`. This is a pure read over manifests; no new registry
  store. `transport-matters list --json` (`list_instances(as_json=True)`) remains the CLI
  view of the same data.
- The Electron main process discovers agents by reading manifests (or by the startup JSON line
  it captured per spawn). The backend does not push a registry; the manifest dir is the source
  of truth, consistent with the capture substrate's tier-1-is-truth design.

---

## 7. The web surface the frontend consumes (consolidated contract)

Per agent, two origins. Nothing here is new except the pty-ws and the artifact event type.

### 7.1 mitmdump-process HTTP on `web_port` (REUSE)

`create_app()` (`main.py:52-96`) mounts `api_router` at `/api` and serves `www/` static at
`/`. CORS from `config.py:cors_origins` (`http://localhost:3000`, `http://localhost:5173`)
and `cors_methods`/`cors_headers`. `GET /health` returns `{"status":"ok"}` (`main.py:82-84`).
Endpoints the cockpit uses:

- `GET /stream` (`api/v1/stream.py:20`): SSE, `text/event-stream`. Server pushes JSON events
  from `broadcast.emit`. The cockpit subscribes once per agent for wire turns, transcript
  turns, and artifact events (section 8 of the index push).
- Wire: `GET /api/exchanges`, `GET /api/exchanges/{id}` (`api/v1/exchanges.py`). Pane 3 reuses
  the existing `www/` wire components against these.
- Transcript: `GET /api/index/sessions`, `GET /api/index/sessions/{session_id}/timeline?stream=transcript&with_bodies=true&seq_from=&seq_to=`, `GET /api/index/sessions/{session_id}/pivot`, `GET /api/exchanges/{id}/raw` (`api/v1/index_routes.py`). Pane 1 renders transcript IR from the timeline; provenance jumps use the same timeline.
- Breakpoint: `api/v1/breakpoint_routes.py` arm/release. Pane 3 reuses existing breakpoint UI.

### 7.2 launcher-process WebSocket on `pty_ws_port` (NEW)

`GET ws /pty?token=` per section 5. Served by a minimal ASGI app in `desktop/pty_ws.py`. It
may be a FastAPI app (reusing the framework already in `main.py`) with a single
`@app.websocket("/pty")` route plus `GET /health`; the master_fd reader and per-client queues
live in the lifespan-scoped state. It does not import `create_app` (that app is the wire API
in another process); it is a separate, tiny app.

### 7.3 Live SSE event taxonomy (the cockpit reads `type`)

The existing stream carries arbitrary JSON dicts (`api/v1/stream.py:37`,
`broadcast.emit`). Events already include `{"type":"connected"}` and the index live-push
events. This spec adds one event type, `artifact` (section 8). The frontend dispatches on
`type`:

```jsonc
// existing wire/transcript live push (from IndexWriter post-commit, IndexJob.event)
{ "type": "...", "session_id": "...", "turn_id": "...", "exchange_id": "...", ... }

// NEW: artifact produced (section 8)
{ "type": "artifact",
  "session_id": "<agent identity>",
  "turn_id": "<originating turn>",
  "exchange_id": "<wire exchange or null>",
  "tool": "Write|Edit|MultiEdit|NotebookEdit|image_generation|...",
  "path": "/abs/or/~resolved/path",
  "content_type": "markdown|image|code|text|unknown",
  "has_inline_content": true,
  "stream": "transcript|wire" }
```

---

## 8. Artifact-event surface (derived from tool records)

### 8.1 Source of truth: transcript tool records, wire as fallback

Both streams parse to the same IR: `ToolUseBlock(name, input)` and
`ToolResultBlock(tool_use_id, content)` (`ir.py:25-42`), reachable from a transcript
`NormalizedTurn.parts` (`index/adapters/base.py:133-151`) and from wire exchange blocks
(sectioned via `exchange_block`). Block identity is stream-invariant (`identity_canonical`
strips `provider_data`), so the same tool call hashes equal across wire and transcript.

The **transcript** is authoritative for artifact detection: it is the harness's own record of
every turn, whereas the wire may drop non-message frames. Use the transcript tool record as
the primary trigger; if a session has no transcript binding yet (early in a run), the wire
`tool_result` is the fallback. Do not emit twice for the same `(session_id, turn_id, tool_use_id)`;
dedupe on that key (the frontend's pane-level dedupe-to-update by path is a separate concern,
charter spawn policy).

### 8.2 Classifier (NEW, pure, in the index layer)

`index/artifacts.py` holds a pure classifier that imports `ir` only (DAG-safe: index imports
`ir` + `canonicalization`, PROJECT.md). It maps a `ToolUseBlock` (and optional matching
`ToolResultBlock`) to an optional artifact descriptor:

```python
# index/artifacts.py  (frozen Pydantic v2, builtins-only typing)
class ArtifactEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    session_id: str
    turn_id: str
    exchange_id: str | None
    tool: str
    path: str
    content_type: str            # markdown|image|code|text|unknown (by extension)
    has_inline_content: bool
    stream: str                  # "transcript" | "wire"

def classify_artifact(
    block: ToolUseBlock, result: ToolResultBlock | None, *,
    session_id: str, turn_id: str, exchange_id: str | None, stream: str,
) -> ArtifactEvent | None: ...
```

Path extraction by tool name:

- `Write`, `Edit`, `MultiEdit`, `NotebookEdit` (claude): `block.input["file_path"]`.
- Codex file edits (apply_patch / shell write tools): extracted from `block.input` per the
  codex tool shape. The codex adapter (`index/adapters/codex.py:82-127`) currently parses
  function_call/message/reasoning; mapping codex edit tools to `file_path` is part of this
  classifier's codex branch.
- Image generation: the charter's example is codex writing to
  `~/.codex.lilo/generated_images/<id>/*.png`. The current codex adapter does **not** surface
  image-gen result paths (they fall to UnknownBlock). This is a real gap, section 11. The
  classifier's image branch reads `ImageBlock.source["path"]` (`ir.py:53-58`) once the codex
  adapter populates it; until then image artifacts for codex are not emitted (logged, not
  silently dropped).

`content_type` is derived from the path extension only (markdown/image/code/text/unknown); the
viewer registry that maps type to renderer lives in the frontend (charter), so the backend
emits a coarse type and the path, not a renderer choice.

### 8.3 Delivery: the existing post-commit emit seam

The `IndexWriter` already carries `emit` and a per-job `event` payload pushed **post-commit**
(`index/writer.py:IndexWriter`(53), `IndexJob.event`(43); `emit=broadcast.emit` injected at
`addon_runtime.py:116`). Artifact events ride this exact seam: when transcript-turn ingest
builds its `IndexJob` (in `index/ingest.py`, the transcript job builder), it also derives
`classify_artifact` over the turn's `ToolUseBlock`s and attaches the resulting `ArtifactEvent`
dicts so they emit after the durable write commits.

This honors the project's own lesson set: emit only at the terminal/durable seam, never a
provisional one, so a retracted provisional turn never orphans an artifact event. Reusing the
post-commit push means the cockpit gets artifacts on the same `/stream` it already consumes,
with no new transport.

Attribution: `session_id` is the agent identity (the minted/native session id, the universal
correlation key, `SessionBinding.session_id`, `index/adapters/base.py:24-46`); `turn_id` is
the originating turn; `exchange_id` ties to the wire exchange when the trigger is the wire
stream. Provenance click in the UI uses `GET /api/index/sessions/{session_id}/timeline`
(`api/v1/index_routes.py`) to jump to `turn_id`. The FS watcher could never give this link;
the tool-record derivation does (charter rationale).

---

## 9. Workspace + layout persistence store

### 9.1 Identity reuse

Workspace identity is `workspace_id(cwd) -> (slug, hash)` (`workspace.py:58-68`): canonical
path via `Path.resolve`, `slug` from the last path segments, `hash` =
`blake2b(canonical.as_posix(), digest_size=4)`. Two checkouts of one project share a
workspace, identical to tier-1 (DRY with the capture substrate). The desktop store keys
everything on `(slug, hash)`; it never invents a second identity.

### 9.2 Location

- **Per-workspace layout** (survives across runs; runs are ephemeral, the workspace is not):
  `~/.transport-matters/workspaces/{slug}/{hash}/desktop/layout.json`. This reuses the
  existing workspace root from `workspace_root(cwd)` (`workspace.py:71-80`), with a `desktop/`
  subdir so it never collides with run dirs (`{run_id}/`).
- **Global launcher registry** (the screen-1 recents/gallery): `~/.transport-matters/desktop/workspaces.json`.
  This is the list of known workspaces with display metadata. It is a convenience index;
  ground truth for "what exists" is still the workspace dirs on disk.

The `~/.transport-matters/` root and the workspaces layout are the existing storage roots
(`storage_roots.py:DEFAULT_STORAGE_DIRNAME`, `cli/disk_layout.py`). The `desktop/` subtrees
are new but live under the same root.

### 9.3 Schema (frozen Pydantic v2, builtins-only typing)

`desktop/models.py`:

```python
class PaneRef(BaseModel):
    model_config = ConfigDict(frozen=True)
    pane_id: str
    kind: str                       # "chat" | "tui" | "wire" | "viewer"
    agent_session_id: str | None    # which agent this pane belongs to (None for shared viewers)
    content_ref: str | None         # viewer: artifact path; else None

class SplitNode(BaseModel):
    model_config = ConfigDict(frozen=True)
    orientation: str                # "row" | "col"
    ratio: list[float]              # child weights, len == len(children)
    children: list["LayoutNode"]

LayoutNode = PaneRef | SplitNode    # discriminated recursive split tree (leaf = PaneRef)

class WorkspaceLayout(BaseModel):
    model_config = ConfigDict(frozen=True)
    slug: str
    hash: str
    mode: str                       # "tiling" | "free"
    tree: LayoutNode | None
    floating: list[PaneRef]         # free-canvas panes (pos/size carried by the frontend mirror)
    artifact_pins: list[str]        # pinned artifact paths (charter lifecycle: pin/dismiss)
    updated_at: str

class DesktopWorkspaceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    slug: str
    hash: str
    root: str                       # canonical path
    display_name: str
    created_at: str
    last_opened_at: str
```

The split-tree schema is content-agnostic at the structural level (orientation, ratio,
children) so it mirrors the engine's recursive split tree (charter heart). `PaneRef.kind` and
`content_ref` are the only TM-content fields, kept at the leaf edge. The backend persists and
returns these; it does not interpret layout geometry. Live per-pane pixel geometry for the
free-canvas mode is the frontend's runtime concern; the backend stores the logical tree and
ratios so a workspace reopens to its remembered arrangement.

### 9.4 Access

`desktop/store.py` provides pure load/save:
`load_layout(slug, hash) -> WorkspaceLayout | None`, `save_layout(WorkspaceLayout) -> None`,
`list_workspaces() -> list[DesktopWorkspaceEntry]`, `upsert_workspace(DesktopWorkspaceEntry)`.
Writes are atomic (temp file + `os.replace`), matching the manifest write pattern
(`manifest.py:write`(55-66)). No DB; JSON files keyed by identity, consistent with the
manifest/sessions.json approach (tier-1 is plain files; the only SQLite is the rebuildable
tier-2 index, PROJECT.md).

These reads/writes are driven by the Electron main process over the launcher's HTTP surface,
or by a small `desktop/` REST app. To avoid a third long-lived server, the simplest seam is to
add layout read/write routes to the **pty-ws launcher app** (`desktop/pty_ws.py` is already an
ASGI app on `pty_ws_port`): `GET /desktop/layout`, `PUT /desktop/layout`,
`GET /desktop/workspaces`. The store functions stay pure and framework-free in
`desktop/store.py`; the routes are thin. (Open item 11.4: whether persistence should instead
be a standalone short-lived `transport-matters desktop` control process is an orchestrator
call.)

---

## 10. Module layout, DAG placement, and budgets

### 10.1 Import DAG (PROJECT.md, verbatim)

```
ir → adapters → rules → pipeline → storage → breakpoint → server
```

`ir.py` imports nothing from the package and is frozen. `canonicalization.py` is layer 1
(stdlib only), shared by override audit and the index. The `index/` package sits after
`storage`, importing `ir` and `canonicalization` only; `storage` must never import `index`,
and the index write sink is injected at `load_runtime` so there is no `storage -> index`
back-edge.

### 10.2 Where the new code lands

- **`index/artifacts.py`** (NEW): `ArtifactEvent` + `classify_artifact`. Imports `ir` only.
  Lives in the index layer (after storage). Wired into the existing transcript ingest job
  builder in `index/ingest.py` (no new back-edge; reuses the post-commit emit). Budget ~120 LOC.
- **`supervisor_pty_process.py`** (EXTEND): `_open_child_on_pty`, `spawn_headless_pty`,
  `set_pty_winsize`; refactor `spawn_with_pty` to call the shared core. Stays a top-level
  module alongside `supervisor_core.py`. Net delta small; remains under 700.
- **`supervisor_core.py`** (EXTEND): add `headless_pty: bool` to `spawn`. Small.
- **`cli/ports.py`** (EXTEND): `allocate_port_triple`. Small.
- **`manifest.py`** (EXTEND): two optional fields. Small.
- **`cli/start_cmd.py` / `cli/codex_cmd.py`** (EXTEND): promote the invocation factory to a
  public name (section 3.2). Small.
- **`desktop/`** (NEW top app package, imported by nothing in core):
  - `desktop/models.py`: frozen layout + workspace models (~150 LOC).
  - `desktop/store.py`: pure JSON persistence (~200 LOC).
  - `desktop/registry.py`: multi-agent discovery over `read_all` (~120 LOC).
  - `desktop/pty_ws.py`: ASGI app, the master_fd bridge, ring buffer, per-client queues,
    resize, plus the layout/registry routes (~280 LOC; split into `pty_ws.py` +
    `pty_bridge.py` if it approaches 700, keeping the bridge mechanics separate from routes).
  - `desktop/agent_host.py`: the headless run loop composing the launch core + supervisor +
    the ASGI app (~220 LOC).
  - `cli/agent_cmd.py`: the `transport-matters agent` Typer command wired into
    `cli/__init__.py:main` (~150 LOC), mirroring `start_cmd.py` / `codex_cmd.py`.

`desktop/` sits above `cli` and `server` (it orchestrates a launch and hosts a server). It
imports the launch core (`cli/launch_runtime`, `cli/launch_profile`, the public invocation
factories), `supervisor_*`, `manifest`, `workspace`, `config`, `broadcast`, and `index`
read-side as needed. No core module imports `desktop`. This keeps the DAG acyclic: `desktop`
is a new terminal sink above the existing top layer.

### 10.3 Budgets and conventions (PROJECT.md)

Files <= 700 LOC, functions <= ~150. Builtins-only typing (`list[str]`, `X | None`).
Pydantic v2 idioms; IR frozen; pipeline actions return new instances. Domain exceptions in
`exceptions.py`, translated at the FastAPI layer, always chained (`raise X from e`), never
swallowed. Quality gate: `cd api && just ci` (format, lint, type-check, tests). Module privacy:
no cross-module import of `_`-prefixed names (so the section 3.2 public-factory refactor is
mandatory, not optional).

---

## 11. Security

- **Localhost only.** mitmdump binds `127.0.0.1` (`build_mitmdump_argv`(409-412)); uvicorn for
  the wire API binds `127.0.0.1` (`addon_runtime.py:149`); the pty-ws app binds `127.0.0.1`.
  No `0.0.0.0`, ever.
- **PTY is an input surface, so it requires a token.** The PTY accepts keystrokes that drive a
  real coding agent (file writes, shell). A per-run `desktop_token` (`secrets.token_urlsafe`,
  generated in the headless command, stored in the manifest, returned on the startup JSON line)
  is **mandatory** for the pty-ws connect (query param or `Sec-WebSocket-Protocol`), so another
  local process cannot attach to the keyboard of an agent. The manifest file's POSIX perms
  (user-only) keep the token off other users.
- **Wire/transcript API token is optional** (read-only observability, loopback). For parity and
  defense in depth, the same token may gate `web_port` too; recommended but lower priority than
  the pty-ws token. Open item 11.3.
- **WebSocket origin allowlist.** The pty-ws upgrade checks `Origin` against the Electron app
  origin plus dev origins, reusing the `config.py:cors_origins` shape. A loopback bind plus a
  token plus an origin check is defense in depth against a malicious local web page driving the
  socket.
- **Child env hardening is already enforced.** `build_managed_child_env` (`launch_runtime.py:484`)
  strips proxy/trust bypass vars and pins the proxy + CA so the child cannot escape interception.
  The desktop reuses it unchanged.
- **No secrets in code.** Tokens are runtime-generated; the upstream/CA handling stays in the
  existing codex CA path (`cli/codex_cmd.py:_resolve_codex_ca_certificate_or_exit`(47)).

---

## 12. Backend contribution to the slice plan

The orchestrator authors the unified sliced plan; this is the backend's view of how to land
incrementally, with slice 1 as the thinnest end-to-end loop (charter).

- **Slice 1 (thinnest loop): one agent, one live TUI pane.** `cli/ports.py`
  `allocate_port_triple`; `supervisor_pty_process.py` core extraction + `spawn_headless_pty` +
  `set_pty_winsize`; `supervisor_core.py` `headless_pty` flag; `desktop/pty_ws.py` PTY bridge
  (framing, ring, resize, token); `desktop/agent_host.py` headless run loop; `cli/agent_cmd.py`
  `transport-matters agent` reusing `prepare_launch` + the public claude factory +
  `run_with_workspace_manifest`. Acceptance: `transport-matters agent --client claude` launches
  a real claude on a headless PTY, an xterm.js client over `ws://127.0.0.1:{pty_ws_port}/pty`
  is interactive with correct resize, and `cd api && just ci` is green. Manifest extension
  (`pty_ws_port`, `desktop_token`) lands here.
- **Slice 2: wire + transcript panes against the existing API.** No backend build beyond
  confirming the per-agent `web_port` REST + SSE are reachable from the renderer (CORS/origin
  for the Electron origin). Acceptance: panes 1 and 3 render live for the agent from slice 1.
- **Slice 3: artifact events.** `index/artifacts.py` classifier + wiring into the transcript
  ingest job builder so `ArtifactEvent`s ride the post-commit `emit`. Acceptance: a `Write` by
  the agent produces an `{"type":"artifact"}` SSE event with correct `session_id`/`turn_id`/`path`,
  and provenance resolves via the timeline endpoint. Codex image-gen flagged (11.1).
- **Slice 4: multi-agent + persistence.** `desktop/registry.py` discovery over `read_all`;
  `desktop/store.py` + `desktop/models.py` + layout/registry routes. Acceptance: two agents in
  one workspace are discoverable, and a workspace reopens to its remembered layout.

Codex parity (the `--client codex` path through the public codex factory + CA) lands with or
right after slice 1, since it is the same composition with a different invocation factory.

---

## 13. Invariants honored (checklist)

- Import DAG acyclic: `index/artifacts.py` imports `ir` only; `desktop/` is a terminal sink
  above `cli`/`server`; no core module imports `desktop`; no `storage -> index` back-edge.
- LOC: every new file budgeted <= 700; functions <= ~150 (the run loop and bridge are split if
  they approach the limit).
- Builtins-only typing throughout; Pydantic v2 frozen models for `ArtifactEvent` and the
  layout/workspace schema; IR untouched and still frozen.
- AST privacy boundary respected: the section 3.2 public-factory refactor exists precisely so
  no `_`-prefixed name is imported across modules.
- Launch core reused, zero parallel launch implementation (charter decision 6).
- Per-run isolation preserved: own proxy/web/pty-ws ports, own storage root, own manifest.
- The layout schema's structural core is content-agnostic; TM content sits only at `PaneRef`
  leaves (charter heart, extractable to littleorgans).
- Gate: `cd api && just ci` is the acceptance command for every slice.

---

## 14. Open questions for orchestrator

Each carries a stated working assumption so the build proceeds without bus chatter.

1. **Codex image-gen artifact paths.** The codex adapter (`index/adapters/codex.py:82-127`)
   does not currently surface `~/.codex.lilo/generated_images/<id>/*.png` paths; they fall to
   UnknownBlock. The charter's marquee artifact example therefore needs a codex-adapter
   extension (map the image-gen response item to `ImageBlock.source["path"]`).
   Working assumption: ship slices 1 to 4 with claude `Write`/`Edit` + codex file edits
   working, and treat codex image-gen as a fast-follow adapter change tracked as its own
   sub-issue. The classifier already has the image branch; only the adapter feed is missing.
2. **pty-ws server library.** Working assumption: FastAPI/Starlette WebSocket on uvicorn
   (already repo deps), one tiny app in `desktop/pty_ws.py`, so no new dependency and the
   `loop.add_reader(master_fd)` bridge runs in uvicorn's loop. If the panel prefers the
   stdlib `websockets` lib to keep the launcher app minimal, the bridge mechanics are
   unchanged; only the route shell differs.
3. **web_port auth parity.** Working assumption: pty-ws token is mandatory (input surface);
   the read-only wire/transcript `web_port` stays token-optional for v1 (loopback only) and
   gains the same token in a hardening pass. Flag if the orchestrator wants both mandatory from
   slice 1.
4. **Persistence transport.** Working assumption: layout/registry reads/writes are thin routes
   on the launcher's `pty_ws_port` ASGI app (no third server), with pure store functions in
   `desktop/store.py`. Alternative: a standalone short-lived `transport-matters desktop` control
   process owns persistence and spawns agents. Orchestrator decides; the store layer is
   identical either way.
5. **Free-canvas geometry persistence.** Working assumption: the backend persists the logical
   split tree + ratios + floating pane refs; live pixel positions/zoom for the free-canvas mode
   are a frontend runtime mirror, snapshotted into `floating` on save. Confirm the granularity
   the frontend wants persisted.
6. **`transport-matters agent` vs flags on existing commands.** Working assumption: a new
   dedicated headless subcommand keeps the interactive TTY path untouched and avoids flag
   overload. If the orchestrator prefers `claude --headless --pty-ws-port`, the composition is
   identical; only the command shell moves.

End of backend spec.
