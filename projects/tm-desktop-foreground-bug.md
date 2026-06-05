# `transport-matters desktop --foreground` does not exit on app quit — root cause

Date: 2026-07-07. Debugger session on `feat/desktop-s2` (d17fe69), read-only. Phase 1 of
superpowers:systematic-debugging. No fix applied.

## Bug

Run `transport-matters desktop --foreground`, quit the Electron app (Cmd+Q / window close).
The foreground CLI process never exits; the shell never comes back.

## TLDR root cause

The `--foreground` path hosts uvicorn in-process and blocks on `thread.join()`, while the
Electron viewer is spawned as a fully detached hosted viewer. **No mechanism exists, in either
direction, that tells the foreground backend the viewer quit.** The Popen handle is discarded,
stdio is DEVNULL, the viewer runs in its own session, there is no shutdown endpoint, and the
hosted Electron quit path calls only `app.quit()`. The process is not deadlocked; it is simply
never asked to stop (Ctrl-C still exits it in 0.3s). PR#232 does not touch this path.

Classification: **separate/S5** (pre-existing on main, byte-identical on `feat/desktop-s2`,
out of PR#232's Electron-owned-teardown scope; the desktop-cleanup spec already points at
demoting the CLI-hosted foreground path to developer mode).

## Code path (what keeps the process alive)

- CLI entry: `desktop --foreground` → `run_desktop_launch()`
  (`api/src/transport_matters/cli/__init__.py`, symbol `desktop`;
  `api/src/transport_matters/cli/desktop_cmd.py`, symbol `run_desktop_launch`).
- `serve_desktop_backend()` (same file) runs uvicorn **in-process on a daemon thread**, waits
  for port readiness, calls `on_backend_ready()` (prints the event, spawns the viewer), then
  blocks on `thread.join()`. The only exits from that join are (a) the uvicorn server exiting
  (only ever requested via `server.should_exit`, which nothing sets after a successful start)
  or (b) `KeyboardInterrupt` in the main thread.
- The viewer is spawned by `spawn_detached_electron()`: `start_new_session=True`, all stdio
  `DEVNULL`, `close_fds=True`, and the `Popen` return value is **discarded**. The CLI never
  waits on, polls, or even remembers the viewer pid. (Observed side effect: the viewer
  wrapper becomes a zombie child of the CLI after quit, since nothing reaps it.)
- `spawn_detached_electron()` sets `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL`, so Electron main
  takes the **hosted viewer** branch: `registerDesktopLifecycleFromEnv` →
  `registerHostedDesktopLifecycle` (`desktop/src/main.ts`). That branch wires **no backend
  teardown**: window-all-closed → `app.quit()` and nothing else. `DesktopShutdown` /
  `DesktopBackendManager.stop()` (the PR#232 hardening) are wired only inside
  `registerAppLifecycle`, the Electron-owned `_desktop-backend` path.
- The only liveness coupling in hosted mode is **one-directional and inverted**:
  `desktop/src/hostedLiveness.ts` polls the backend's `/health` and quits the *app* when the
  *backend* dies. Nothing watches the viewer from the backend side.
- There is no process-shutdown HTTP surface on the FastAPI app (the only "shutdown" strings in
  `api/` are run end-reasons in `api/v1/run_routes.py`).

So after quit: no signal (different session), no pipe close (DEVNULL), no waited pid (handle
discarded), no HTTP call (no endpoint), no poll (only backend-health, wrong direction).
`thread.join()` blocks forever. That is the entire bug.

## Reproduction and evidence

Reproduced live on this machine with the **installed build Stuart ran**
(`~/.local/bin/transport-matters`, version `0.3.0.post1.dev208+gd17fe69ec` — built from the
tip of `feat/desktop-s2`), isolated from the running dev desktop session (preview channel,
scratch `--storage-dir`, `--web-port 18899`, real Electron viewer from `desktop/dist`):

1. `transport-matters desktop --foreground --channel preview --web-port 18899 --storage-dir <scratch>`
   → uvicorn up in-process (pid 95155), event JSON printed, real hosted Electron viewer
   spawned (pid 95209), viewer loaded `/canvas` and began 1s `/health` polls (log evidence).
2. Graceful viewer quit (SIGTERM to the Electron process drives its normal quit path,
   equivalent to Cmd+Q for a hosted viewer with no other teardown wiring).
3. **25s+ after quit**: CLI pid 95155 still alive, `GET /health` still returns 200, and the
   discarded viewer-wrapper child (pid 95203, `node electron/cli.js`) is a `<defunct>` zombie
   under the CLI. Repeated in a second controlled run (pid 96536): `cli alive 8s after viewer
   quit: True`.
4. Ctrl-C check (SIGINT with default disposition, as a real terminal delivers it): the CLI
   exits with rc=130 in **0.3s**. So the process is healthy and interruptible — there is no
   shutdown deadlock; there is simply no quit linkage.
   (Note: an earlier SIGINT appeared ignored, but that was an artifact of launching as a
   background job of a non-interactive shell, which spawns children with SIGINT set to
   SIG_IGN; CPython then never installs the KeyboardInterrupt handler. Verified by rerunning
   with `preexec_fn` resetting SIGINT to SIG_DFL.)

## Baseline: main vs feat/desktop-s2 (PR#232)

- `git diff main...feat/desktop-s2 -- api/` is **empty**. The `--foreground` Python path is
  byte-identical on both. The bug exists on main and on the branch equally.
- PR#232 changes only `desktop/` TypeScript: it introduces `DesktopShutdown`,
  `DesktopLifecycle`, `DesktopBackendManager`, and grace-then-force kill — all wired into
  `registerAppLifecycle` (Electron **owns** the `_desktop-backend` child). The hosted-viewer
  branch that `--foreground` uses gained no backend-stop behavior in the diff.
- **S2 does not fix this bug**, and it is not a regression from S2.

### Classification: separate (S5-adjacent), not fold-into-S2

- Folding it into #232 would expand an Electron-main PR into the Python CLI seam; the fix
  lives entirely in `desktop_cmd.py` (see below) and carries its own test surface.
- Direction of travel already on record: the desktop-cleanup spec
  (`~/.mdx/projects/transport-matters-desktop-cleanup/spec-backend.md`, "Desktop backend
  process owner") recommends Electron own the backend for product launches and keep a
  foreground Python desktop command only "as a developer mode rather than the product path".
  This bug is precisely the CLI-hosted path that plan demotes/retires.
- Recommend: small standalone fix PR (or ride the launcher-retirement slice if it lands
  first). Not a merge blocker for #232.

## Proposed minimal fix (NOT applied — awaiting confirmation)

Couple the foreground backend's lifetime to the viewer process it spawned, on the Python
side. The CLI is the only component that knows it both hosts the backend and spawned this
specific viewer, so the linkage belongs there:

1. `spawn_detached_electron()` returns the `Popen` instead of discarding it (other callers
   may ignore the return value).
2. `serve_desktop_backend()` passes a `request_shutdown` callable (closure setting
   `server.should_exit = True`) to `on_backend_ready`.
3. `run_desktop_launch.on_backend_ready` spawns the viewer, then starts a small daemon
   thread: `viewer.wait()` → `request_shutdown()`. Uvicorn's serve loop notices
   `should_exit` within its tick, the daemon thread returns, `thread.join()` unblocks, the
   CLI exits 0. `wait()` also reaps the zombie observed in step 3 above.

Works for both viewer shapes: packaged app binary (Popen is the app itself) and dev
`electron <dir>` (Popen is the `cli.js` wrapper, observed to exit when the app quits).

Rejected alternative: making the hosted Electron kill the backend on quit. Wrong layer —
hosted viewers also attach to **detached** backends (`desktop` without `--foreground`),
which must survive viewer quit by design (runtime record + reattach). Only the foreground
CLI owns its backend.

Test shape (Phase 4, later): unit test in `cli/test_desktop.py` on the existing seams
(`spawn_electron_func` returning a fake process, `serve_backend_func` real) asserting
`serve_desktop_backend` returns once the fake viewer process exits, and that Ctrl-C behavior
is unchanged.
