---
title: Shared-proxy orphan subprocess leak — root-cause scout
type: research
tags: [transport-matters, shared-proxy, subprocess-leak, lifecycle, reaping, scout]
summary: Orphans accumulate because shared-proxy reaping is in-memory and per-process; each unclean API exit leaks one detached subprocess and the next startup never detects or kills the survivor.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-27
updated: 2026-06-27
---

# Shared-proxy orphan subprocess leak — root-cause scout

## Executive Summary

The leak is **(b) one subprocess spawned per logical event, old ones never killed** — a
cross-process teardown/reaping gap, **not** a K>1 / respawn bug inside one API process.
Each API process spawns exactly one shared-proxy subprocess and reaps only *its own*
in-memory child, and only on a clean lifespan shutdown. The subprocess is spawned
detached (`start_new_session=True`), so it survives any unclean API exit. The next API
startup spawns a fresh subprocess **blind to the survivor** — there is no stale-PID /
stale-instance detection before binding. N unclean restarts ⇒ N orphans, all pointing at
the same stable control socket.

## Root Cause (the leak chain)

1. **Startup spawns blindly.** `lifespan` (`api/src/transport_matters/main.py:lifespan`)
   builds the manager via `SharedProxyManager.create(runtime_dir=storage_dir/"runtime"/"shared-proxy")`
   then calls `.start()`. No prior-instance detection runs.
2. **`is_running()` is in-memory only.** `SharedProxyManager.start` →
   `SharedProxyManager._ensure_started_locked` spawns when `self._process.is_running()` is
   False. `SupervisorSharedProxyProcess.is_running` returns
   `self._managed is not None and self._managed.popen.poll() is None`. `self._managed` is
   set only by *this* process's own `start()`. A fresh API process always sees
   `_managed is None` ⇒ `is_running()` False ⇒ spawns a new subprocess, unable to observe a
   subprocess left by a prior API process.
3. **The spawned child is detached and outlives the parent.**
   `SupervisorSharedProxyProcess.start` launches `python -m transport_matters.shared_proxy.subprocess`
   through `ProcessSupervisor.spawn`, which sets `start_new_session=True` for background
   (log_path) children. The child becomes its own session/process-group leader with no
   parent-death signal (no `PR_SET_PDEATHSIG`; macOS lacks it anyway). A `SIGKILL`/crash of
   the API, a dev `--reload` worker recycle, or a desktop relaunch that replaces the API
   without a clean shutdown leaves the child running, reparented to launchd/init.
4. **Reaping is scoped to the current process and only fires on clean shutdown.** The only
   reap path is `lifespan` finally → `SharedProxyManager.close` →
   `SupervisorSharedProxyProcess.terminate` → `ProcessSupervisor.terminate_all`, which
   iterates `self._children` (this process's in-memory map). It cannot reach a prior
   process's subprocess. If the lifespan `finally` never runs, even this process's child
   leaks.
5. **Socket unlink hides, does not heal.** When the new subprocess boots,
   `SharedProxyControlServer.start` does `self.socket_path.unlink()` then
   `asyncio.start_unix_server(...)`. This lets the *new* child steal the control socket from
   the old one, so the bind never fails with "address in use" — but the **old subprocess is
   not killed**. It keeps running its mitmproxy `DumpMaster`, idle, control socket stolen,
   never reaped.
6. **Stable socket path ⇒ all orphans look identical.**
   `_control_socket_path(runtime_dir)` returns `runtime_dir/"shared-proxy.sock"` for the
   stable home, so every restart references the same `--control-socket` argv. That is why
   `ps` shows ~14 on one stable socket; the "several more on the preview socket" are the same
   mechanism under the desktop relaunch / preview `runtime_dir`.

### Why it is not (a) K>1 within one process

`_monitor_loop` → `SharedProxyManager.supervise` re-enters `_ensure_started_locked` only
when `is_running()` is False (the child already **exited**, `poll()` non-None ⇒ dead — so
the respawn replaces a corpse, no leak) or when `_needs_rehydrate` is True. In the rehydrate
case `_ensure_started_locked` checks `is_running()` first, finds the child alive, and
**does not spawn** — it only re-pings and replays bindings/overrides via
`_rehydrate_locked`. The test
`shared_proxy/test_manager.py:test_monitor_retries_failed_rehydrate_without_dying` pins
exactly this: the retry path rehydrates without a second spawn. Intra-process there is
always at most one live subprocess.

## Reuse Map

The repo already has the exact reaping idiom this fix needs — reuse it, do not add a
parallel reaper:

- **PID liveness probe**: `transport_matters.desktop_runtime.is_pid_alive` (re-exported by
  `transport_matters.cli.desktop_runtime.is_pid_alive`). Signal-0 liveness used to detect a
  dead backend.
- **Dead-PID reap precedent**: `desktop_runtime.discover_desktop_runtime` reads a persisted
  record, checks `is_pid_alive(record.pid)`, and unlinks the stale record when the PID is
  dead (`_unlink_desktop_record`). The shared-proxy fix mirrors this: persist the
  subprocess PID, probe it on startup, kill + unlink if stale.
- **Atomic record write**: `transport_matters.atomic_io` (the module `desktop_runtime` uses
  to write its runtime record) is the seam for writing the shared-proxy PID file.
- **Signal escalation already owned**: `ProcessSupervisor._signal_child` /
  `ProcessSupervisor.terminate_all` already do SIGTERM→grace→SIGKILL against a process group.
  A prior-instance kill can route through the same escalation rather than a bare `os.kill`.
- **Spawn/terminate home**: `SupervisorSharedProxyProcess.start` / `.terminate`
  (`shared_proxy/process.py`) is the concrete OS-process layer where `control_socket`,
  `runtime_dir`, and the child `popen.pid` are all in scope. PID-file write and prior-instance
  reap belong here, keeping the substrate-agnostic `SharedProxyProcess` Protocol and the
  manager's `is_running()` contract untouched.

## Quality Map

- **Single-owner design is correct.** `lifespan` creates one `SharedProxyManager` and hands
  it to `run_routes.create_run_manager(shared_proxy_manager=...)`; `RunManager` does **not**
  spawn its own proxy. K=1 per process is intended and upheld — the defect is purely
  cross-process survival.
- **In-memory liveness is the core gap.** `SupervisorSharedProxyProcess` tracks only
  `self._managed`. There is no on-disk PID record, no `os.kill(pid, 0)` probe, and no
  "is something already bound to this control socket?" check before spawn. Nothing bridges
  process generations.
- **`terminate_all` is robust but unreachable for orphans.** It already escalates to SIGKILL
  and warns on non-reap, but it only knows `self._children`. Correct within a process,
  blind across processes.
- **`grep -r` shows no existing shared-proxy PID file** (`pidfile` search: zero hits). The
  fix introduces the first one; the desktop runtime record is the template.
- **Trigger surface is the desktop relaunch churn.** Recent history
  (`reclaim desktop relaunch ports`, `switch desktop workdir on relaunch`,
  `resolve a default worktree so canvas agent spawn works`) shows the API is relaunched
  repeatedly; each relaunch that does not cleanly stop the prior API leaks one subprocess,
  matching the observed ~14.

## Plan

Reap the prior shared-proxy instance at startup, in the layer that already owns the OS
process. No new background reaper, no second subprocess class.

1. **Persist the child PID on spawn.** In `SupervisorSharedProxyProcess.start`
   (`shared_proxy/process.py`), after `self.supervisor.spawn(...)` returns the
   `ManagedProcess`, write `self._managed.popen.pid` to a sibling PID file
   (`runtime_dir/"shared-proxy.pid"`, alongside `_control_socket_path`) using
   `transport_matters.atomic_io`. Include enough identity to defend against PID reuse (the
   control-socket path and/or `SHARED_PROXY_PROCESS_NAME`).
2. **Reap a stale instance before binding.** At the top of
   `SupervisorSharedProxyProcess.start` (before the `is_running()` early return, or in a
   small private helper it calls), read the PID file; if present and
   `is_pid_alive(pid)` (reuse `transport_matters.desktop_runtime.is_pid_alive`) and the
   recorded identity matches a shared-proxy process, kill it (SIGTERM→grace→SIGKILL — route
   through `ProcessSupervisor._signal_child` semantics or a small kill helper), then unlink
   the PID file, mirroring `discover_desktop_runtime`'s dead-PID unlink. Guard the kill on
   identity match so a recycled PID is never killed.
3. **Unlink the PID file on clean teardown.** In `SupervisorSharedProxyProcess.terminate`
   (after `terminate_all`), remove the PID file so a clean shutdown leaves no stale record.
4. **Keep the manager contract intact.** `SharedProxyManager` and the `SharedProxyProcess`
   Protocol stay unchanged; all OS-identity logic stays in the concrete supervisor process.

### Tests to add (TDD)

- `shared_proxy/test_manager.py` (or a new `process` test): spawn a fake/real prior
  subprocess, write its PID file, assert `start()` kills it and unlinks the file before the
  new spawn (a faked live PID + asserted kill).
- Stale/dead-PID path: PID file points at a dead PID ⇒ `start()` unlinks the file and does
  not attempt a kill, with no exception.
- PID-reuse guard: PID file points at a live but non-shared-proxy PID ⇒ `start()` does not
  kill it.
- Clean teardown: `terminate()` removes the PID file.

### Gates

- `just check`
- `just test`

(Note: `just ci` is **not** a recipe in this repo — `just --summary` lists only `check` and
`test`.)

## Open Questions

- **PID-file vs control-socket peer-cred probe.** A PID file is the lowest-friction match to
  the existing desktop-runtime idiom. An alternative is connecting to the stale control
  socket and asking the live subprocess to self-terminate, but a stuck/wedged child may not
  answer, so an OS-level kill via PID is the more reliable reaper. Recommend PID file.
- **Preview/relaunch homes.** Confirm the desktop preview/relaunch path uses a distinct
  `runtime_dir` (hence distinct PID file); the same reap logic covers it for free since it
  lives in `SupervisorSharedProxyProcess.start` keyed on `runtime_dir`.
