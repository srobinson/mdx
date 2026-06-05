---
title: Desktop launcher re-architecture — Electron owns the backend
type: projects
tags: [transport-matters, desktop, launcher, electron, lifecycle, teardown, backend]
summary: Re-architect `transport-matters desktop` so Electron owns the Python backend (VS Code sidecar model), closing the desktop reliably reaps the backend with no orphans.
status: active
source: backend-engineer
confidence: high
created: 2026-07-03
updated: 2026-07-03
---

# Desktop launcher re-architecture — Electron owns the backend

Spec phase only. No product code. Cites file+symbol, never line numbers.

## Goal

Fix `transport-matters desktop` so closing the desktop reliably tears down the
Python backend. Today the default detached path orphans the backend (the user
must `channel list` then manually kill the pid), and `--foreground` needs a
second CTRL-C to fully quit.

Target model (VS Code sidecar): **Electron owns the Python backend**. Electron
main spawns the backend, and every teardown scenario (window close, CTRL-C,
Electron crash/SIGKILL, backend crash, external `channel stop`) converges on a
dead backend with no orphaned uvicorn or `mitmdump` children.

## Linchpin verdict: `launchBackendProcess` is NOT production-ready as written

The whole re-arch rests on `desktop/src/backendProcess.ts::launchBackendProcess`.
Grounded verdict: **prod-ready = NO**, and the reason is the correctness core of
this spec.

`launchBackendProcess` spawns the child with `stdio: "pipe"`, no `detached`, and
no parent-death mechanism. Locked decision #1 states crash-robustness "comes from
process parentage (backend dies with Electron by ANY cause incl. SIGKILL)." On
macOS/POSIX that is **factually false**: when a parent dies (especially SIGKILL,
where no cleanup runs), children are reparented to the init/subreaper process,
**not killed**. Pure parentage only reaps children on Windows (Job Objects) or
Linux (`PR_SET_PDEATHSIG`); macOS has neither. This is a mechanism gap, not a
relitigation of the decision: we honor the decision's **intent** (backend dies
with Electron by any cause) by implementing the correct mechanism.

Concrete gaps that must close before Electron can own the backend:

1. **SIGKILL orphan (the big one).** No OS-level parent-death guarantee. If
   Electron is SIGKILLed, `before-quit` never fires, `desktop/src/main.ts::bindBackendQuitCleanup`
   never runs, and the backend orphans. Fix: a **parent-death watcher** in the
   `_desktop-backend` entrypoint (stdin-EOF primary + `os.getppid()` poll
   fallback) that self-terminates the backend when Electron dies by any cause.
2. **Window close does not tear down on macOS.** `main.ts::registerAppLifecycle`
   calls `main.ts::bindHostedWindowLifecycle` WITHOUT `quitOnWindowAllClosed:
   true`, so on darwin closing the only window leaves Electron (and the backend)
   alive. Fix: pass `quitOnWindowAllClosed: true` in the owned-backend path.
3. **No post-ready backend-exit watcher.** `main.ts::waitForLaunchedBackend`
   races exit only *before* readiness (`backendProcess.ts::watchBackendExitBeforeReady`).
   After the window is up, a backend crash goes unobserved and Electron shows a
   dead window. Fix: a persistent after-ready exit watcher that reaps the backend
   group and calls `app.quit()`.
4. **Bare-PATH command.** `backendProcess.ts::buildBackendLaunch` uses
   `command: "transport-matters"`, relying on PATH. Fine in the CLI-launches-
   Electron flow (PATH inherited) but fragile. Fix: CLI passes the resolved
   absolute bin via env (`TRANSPORT_MATTERS_DESKTOP_APP_BIN`, already defined).
5. **Env/argv parity.** `buildBackendLaunch` sets only CHANNEL/CWD/PROXY_PORT/
   WEB_PORT; the Python builder it replaces (`cli/desktop_cmd.py::_build_desktop_backend_command`
   + `::_build_desktop_backend_env`) also passes `--storage-dir`, `--debug`,
   `TRANSPORT_MATTERS_STORAGE_DIR`, and strips a stale run-specific env allow-list
   (`_DESKTOP_BACKEND_STALE_ENV_KEYS`). Decision #4 makes `buildBackendLaunch` the
   single builder, so it must absorb this parity.

Biggest open risk: **macOS parentage does not reap the backend on Electron
SIGKILL; the design must add a backend-side parent-death watchdog, or the "no
orphan" guarantee fails exactly in the crash case it is meant to cover.**

## Reuse map + dispositions (from scout)

Grounded against `~/.mdx/projects/launcher-scout-desktop-lifecycle.md` and the
current tree.

| Symbol | Disposition | Why |
| --- | --- | --- |
| `cli/desktop_cmd.py::serve_desktop_backend` | **Delete** | In-process uvicorn path; decision #1 removes it. Its uvicorn-run guts move into the new backend-entry module. |
| `cli/desktop_cmd.py::_build_desktop_backend_command` | **Delete** | Decision #4: TS `buildBackendLaunch` is the single command builder. |
| `cli/desktop_cmd.py::_build_desktop_backend_env` | **Delete → port into `buildBackendLaunch`** | Env parity (storage dir, debug, stale-env strip) moves to the single builder. |
| `cli/desktop_cmd.py::_resolve_backend_ports` | **Delete** | Decision #3: CLI calls `cli/ports.py::allocate_port_pair` directly. |
| `cli/desktop_cmd.py::run_desktop_backend_server` | **Modify (rewrite)** | Stays the `_desktop-backend` handler, but owns its own lifecycle: run uvicorn, write/unlink record, setsid, parent-death watcher, killpg children. Moves to a new module. |
| `cli/desktop_cmd.py::spawn_detached_electron` | **Modify** | Stops setting `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL` (that env selects hosted-viewer mode); becomes the owned-backend Electron launcher. |
| `cli/desktop_cmd.py::run_desktop_launch` / `run_desktop_detached` / `prepare_desktop_launch` / `DesktopLaunchPlan` | **Modify (thin dispatch)** | Delegate to the new orchestration module; `desktop_cmd.py` stays a thin surface (697 LOC, at the limit). |
| `cli/ports.py::allocate_port_pair` | **Reuse** | The one allocator. |
| `desktop_runtime.py::DesktopRuntimeRecord` / `write_desktop_record` / `desktop_record_path` / `desktop_log_path` / `discover_desktop_runtime` | **Reuse** | Record contract + path policy unchanged; now written by the backend itself. |
| `desktop_runtime.py::stop_desktop_record` | **Modify** | Decision #5: killpg the backend group instead of single-pid kill. |
| `cli/desktop_recovery.py::prepare_desktop_runtime_for_launch_or_exit` | **Reuse** | Prelaunch stale/wedged recovery stays; still the idempotency gate. |
| `cli/channel_cmd.py::stop` / `list_channels` / `_desktop_status` | **Reuse** | External stop + observability unchanged (they read/kill via the record contract). |
| `cli/tail_cmd.py::run_tail` | **Reuse** | Foreground tails the Tier-1 log through this. |
| `desktop_event.py::build_backend_started_event` | **Not the launch contract** | Viewer-oriented (carries route/url/storage, NOT ports/channel/bin). The owned-backend contract is a distinct env handshake (below). Kept for the reuse-existing-live-runtime attach path. |
| `desktop/src/backendProcess.ts::buildBackendLaunch` | **Modify** | Single authoritative builder; absorb env/argv parity + absolute bin. |
| `desktop/src/backendProcess.ts::launchBackendProcess` | **Modify** | `detached: true`; stdio `['pipe', logFd, logFd]`; keep stdin pipe for EOF detection. |
| `desktop/src/backendProcess.ts::stopBackendProcess` | **Reuse (+ group reap)** | Graceful SIGTERM stays; add a group-reap helper for stragglers. |
| `desktop/src/main.ts::registerAppLifecycle` | **Modify** | `quitOnWindowAllClosed: true`; post-ready exit watcher; SIGTERM/SIGINT → `app.quit()`. |
| `desktop/src/main.ts::registerDesktopLifecycleFromEnv` | **Reuse** | Branch selector: absence of `DESKTOP_ROUTE_URL` already routes to `registerAppLifecycle` (owned-backend). |
| `desktop/src/main.ts::registerHostedDesktopLifecycle` / `hostedLiveness.ts::registerHostedBackendLivenessPoll` | **Reuse** | Still used for the reuse-existing-live-runtime attach case. |
| `run_manager.py::RunManager._teardown_run` | **Pattern only** | Reuse the "one public stop path, close each owned resource once" discipline; do not reuse the object. |

**Anti-duplication guards:** no third backend-command builder (TS `buildBackendLaunch`
is sole owner); no second process registry (`DesktopRuntimeRecord` +
`discover_desktop_runtime` + `stop_desktop_record` stay the only one); no second
port allocator (`allocate_port_pair`); shared-proxy teardown stays under
`main.py::lifespan` (do not terminate `mitmdump` from the launcher).

## Ownership model (who does what)

Each responsibility lands on the process that has the authoritative information.

- **CLI** owns: port allocation (`allocate_port_pair`), resolving storage root +
  Tier-1 log path (`desktop_log_path`) + absolute bin, prelaunch recovery
  (`prepare_desktop_runtime_for_launch_or_exit`), and launching Electron
  (attached for `--foreground`, detached by default). The CLI does **not** write
  the record (it does not know the backend pid).
- **Electron** owns: spawning the backend (`launchBackendProcess`), gating the
  window on readiness (`waitForLaunchedBackend`), quitting on window close,
  quitting + reaping the backend group on backend exit, and SIGTERM on graceful
  quit (`bindBackendQuitCleanup` → `stopBackendProcess`). Electron **reads** the
  record only via the existing `transport-matters channel status` subcommand
  (`desktop/src/desktopRuntime.ts::readDesktopRuntimeStatus`); it never writes it.
- **Backend** (`_desktop-backend`) owns: running uvicorn, becoming its own
  process-group leader (`os.setsid`), writing `DesktopRuntimeRecord` on lifespan
  startup and unlinking on shutdown, the parent-death watcher, and reaping its
  own children (`killpg`) on shutdown. This keeps the record contract entirely in
  Python (no TS record writer) and makes the backend self-reaping.

Rationale for backend-writes-record: only the running backend authoritatively
knows its own pid; the record then works identically in foreground and detached
mode (fixing the scout-noted gap that foreground never wrote a record), and no TS
duplicate of the Python record contract is introduced.

## CLI ↔ Electron launch contract

The contract is an **env handshake** (not `build_backend_started_event`, which is
viewer-oriented and lacks ports/channel/bin). The CLI launches Electron with
`cwd = workspace_dir` and the following env; the **absence** of
`TRANSPORT_MATTERS_DESKTOP_ROUTE_URL` is what selects the owned-backend branch in
`registerDesktopLifecycleFromEnv` → `registerAppLifecycle`.

| Env key (`env_keys.py` / `env.ts` `ENV`) | Value | Consumer |
| --- | --- | --- |
| `TRANSPORT_MATTERS_CHANNEL` | channel id | `resolveDesktopChannelSpec`, backend |
| `TRANSPORT_MATTERS_CWD` | workspace dir | `registerAppLifecycle` (prefer over `process.cwd()`), backend |
| `TRANSPORT_MATTERS_STORAGE_DIR` | channel storage root | backend (record + log paths) |
| `TRANSPORT_MATTERS_PROXY_PORT` | CLI-allocated proxy port | `resolveBackendStartupOptions`, backend |
| `TRANSPORT_MATTERS_WEB_PORT` | CLI-allocated web port | `resolveBackendStartupOptions`, backend |
| `TRANSPORT_MATTERS_DESKTOP_APP_BIN` | absolute `transport-matters` bin | `buildBackendLaunch` command |
| `TRANSPORT_MATTERS_DESKTOP_LOG` | resolved `desktop_log_path(storage)` | `launchBackendProcess` stdout/stderr fd; record `log_path` |
| `TRANSPORT_MATTERS_DEBUG` | `1` when debug | backend |
| `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL` | **unset** | absence ⇒ owned-backend mode |

`main.ts::resolveBackendStartupOptions` already reads CHANNEL/PROXY_PORT/WEB_PORT
from env and lets env win over spec/runtime fallback via `resolvePort`, so the
CLI-allocated ports flow through with no change there. One small robustness edit:
have `registerAppLifecycle` derive `workspaceDir` from `env[ENV.CWD] ??
process.cwd()` so the workspace is explicit rather than relying on Electron's cwd.

**Readiness.** No IPC handshake needed. Electron gates the window on
`waitForLaunchedBackend` (health poll on `webPort`, racing exit-before-ready).
The CLI, which allocated the web port, learns readiness by the same signal it
already has (`wait_for_port_ready(web_port)`) for a foreground "ready" banner;
this is a convenience, not a correctness dependency.

**Reuse-existing-runtime.** `registerAppLifecycle` already short-circuits to the
hosted viewer when a live runtime serves the workspace (`liveRuntimeRouteUrl`),
and reclaims stale runtimes (`reclaimDesktopRuntime`) otherwise. Running `desktop`
twice in one workspace still attaches to the running backend rather than spawning
a second. This idempotency is preserved.

## Foreground redefinition

`--foreground` survives, redefined from "run uvicorn in this Python process" to
"attach to Electron and tail the backend log."

- **`transport-matters desktop --foreground`:** CLI allocates ports, resolves
  storage/log/bin, runs prelaunch recovery, launches Electron **attached** (CLI
  is Electron's parent; no `start_new_session`), installs a SIGINT handler, tails
  `desktop_log_path` via `tail_cmd.run_tail`, and waits on the Electron child.
  CTRL-C on the CLI → CLI signals Electron to quit → Electron `before-quit` →
  `stopBackendProcess` (SIGTERM backend) → backend graceful shutdown → CLI sees
  Electron exit → returns. One CTRL-C, clean exit (today's two-CTRL-C bug is
  gone because there is no in-process uvicorn competing with the Electron child).
  Closing the window also ends the foreground session symmetrically (Electron
  quits → CLI observes exit → returns).
- **Default (detached):** CLI allocates ports, launches Electron **detached**
  (`start_new_session`), returns the shell immediately. Backend + Electron run
  independently; `channel list` shows the backend pid (backend wrote the record);
  `channel stop` or closing the window tears it down.

To make the foreground CTRL-C path graceful, Electron main installs a
SIGTERM/SIGINT handler that calls `app.quit()` (so `before-quit` runs and the
backend is SIGTERM'd, not hard-killed). The parent-death watcher is the backstop:
even if Electron is force-killed, the backend still reaps itself.

## Port allocation

Decision #3: the **CLI allocates** via `cli/ports.py::allocate_port_pair` and
hands the pair to Electron through `TRANSPORT_MATTERS_PROXY_PORT` /
`TRANSPORT_MATTERS_WEB_PORT`. This reuses the single allocator and keeps the
record's ports consistent with what the CLI reserved. The rejected alternative
(Electron allocates) would duplicate the allocator in TS and force ports back up
to the CLI/record.

**TOCTOU note.** `allocate_port_pair` binds two sockets to `("127.0.0.1", 0)`,
reads the assigned ports, then closes — it does **not** hold the reservation.
There is a window between CLI close and the backend's actual `bind` where another
process could take the port. Mitigation: the window is small (Electron spawns the
backend promptly), and on collision the backend fails to bind and exits before
readiness, which surfaces as `backendProcess.ts::BackendProcessExitError` via
`watchBackendExitBeforeReady` → `main.ts::showBackendStartupFailure`. This is the
same TOCTOU the allocator already documents; no new exposure.

## Record + teardown (killpg)

`DesktopRuntimeRecord` fields are unchanged (`schema_version`, `channel`, `pid`,
`proxy_port`, `web_port`, `log_path`, `cwd`, `storage_dir`, `version`, `instance`,
`started_at`). What changes:

- **Writer:** the backend, on lifespan startup, via `write_desktop_record`
  (own `os.getpid()`, ports from argv, `log_path` from `TRANSPORT_MATTERS_DESKTOP_LOG`).
- **Unlink:** the backend on graceful lifespan shutdown; `stop_desktop_record` on
  `channel stop` (idempotent); `prepare_desktop_runtime_for_launch_or_exit` cleans
  stale records on the next launch.
- **`stop_desktop_record` → killpg.** Today it does `os.kill(record.pid, …)` on a
  single pid. Decision #5: escalate to the **process group**
  (`os.killpg(os.getpgid(record.pid), SIGTERM)` → poll → SIGKILL → unlink) so
  uvicorn reload/worker children and `mitmdump` are reaped. This is **safe only
  because the backend is its own group leader** (`os.setsid` at entry): killpg
  targets the bounded backend subtree, never Electron or the user's shell. If the
  backend were left in Electron's group (spawned non-detached), killpg would climb
  into Electron/the CLI — so `launchBackendProcess` uses `detached: true` and the
  backend calls `setsid` to guarantee a clean group boundary.

Group topology (the safety argument): `detached: true` puts the backend in a new
session; `setsid` in the entrypoint makes it the group leader; its uvicorn/mitmdump
children inherit that group. `killpg(backend_pgid)` reaps exactly that subtree.
The stdin pipe stays held by Electron even when detached, so EOF-based
parent-death detection still works.

## Teardown matrix (correctness core)

Invariants assumed: Electron spawns backend `detached`, stdin=pipe (held by
Electron), stdout/stderr → Tier-1 log; Electron sets `quitOnWindowAllClosed:
true`, has a post-ready exit watcher that reaps the backend group + `app.quit()`,
and a SIGTERM/SIGINT → `app.quit()` handler; backend is a group leader with a
parent-death watcher (stdin-EOF + `getppid()` poll) and a SIGTERM handler that
runs lifespan shutdown (unlink record, `killpg` children).

| Scenario | Foreground | Detached | No-orphan reason |
| --- | --- | --- | --- |
| **Window close** | Window-all-closed → `app.quit` → `before-quit` → SIGTERM backend → graceful shutdown (unlink record, killpg children). CLI sees Electron exit → stops tail → returns. | Same, minus CLI (already returned). | `quitOnWindowAllClosed: true` + `bindBackendQuitCleanup` |
| **CTRL-C on CLI** | CLI SIGINT → signals Electron quit → `before-quit` → SIGTERM backend → graceful. CLI waits, returns. Backstop: CLI escalates SIGKILL to Electron → backend parent-death watcher fires. | N/A — detached Electron is in a new session; shell CTRL-C does not reach it. Use window close or `channel stop`. | Electron SIGTERM→quit handler + watcher backstop |
| **Electron crash / SIGKILL** | `before-quit` does NOT fire. Electron's held stdin pipe closes → backend reads EOF → parent-death watcher → graceful (killpg children, unlink). CLI (Electron's parent) observes exit → returns. | Same, minus CLI. | **Parent-death watcher** (this is the case pure parentage fails) |
| **Backend crash** | Post-ready exit watcher fires → Electron reaps backend group (`kill(-pid)`) to sweep straggler `mitmdump` → `app.quit`. Stale record cleaned on next launch. CLI observes Electron exit → returns. | Same, minus CLI. | Post-ready exit watcher + group reap |
| **External `channel stop`** | `stop_desktop_record` → `killpg(backend group)` → backend + children die, record unlinked. Electron post-ready exit watcher → `app.quit`. CLI observes Electron exit → returns. | Same, minus CLI. | killpg group + Electron exit watcher |

**Residual note (pre-existing, now mitigated):** on a *hard* backend crash that
skips lifespan shutdown, `mitmdump` could orphan. This risk pre-dates the re-arch
(lifespan owns `SupervisorSharedProxyProcess.terminate`). It is mitigated here
because Electron's post-ready exit watcher issues a group reap
(`process.kill(-backendPid, "SIGKILL")`) on observing backend exit, sweeping
stragglers before quitting.

## Files touched

Added / Modified / Deleted, by file + symbol (no line numbers).

**Added (Python)**
- `api/src/transport_matters/cli/desktop_orchestration.py` (new module,
  decision #6): `launch_desktop(foreground: bool, …)` — port allocation, env
  contract assembly, attached/detached Electron launch, foreground tail + wait +
  SIGINT quit. Keeps `desktop_cmd.py` under the LOC limit.
- `api/src/transport_matters/desktop_backend_process.py` (new module): the
  `_desktop-backend` lifecycle owner — `setsid`, run uvicorn (guts moved from the
  deleted `serve_desktop_backend`), record write/unlink, parent-death watcher
  (stdin-EOF thread + `getppid` poll), `killpg` children on shutdown.

**Modified (Python)**
- `cli/__init__.py::desktop` and the hidden `_desktop-backend` command — dispatch
  `desktop` to `desktop_orchestration.launch_desktop`; point `_desktop-backend`
  at `desktop_backend_process`.
- `cli/desktop_cmd.py` — reduce to thin dispatch; delete the symbols below.
- `desktop_runtime.py::stop_desktop_record` — killpg escalation (SIGTERM group →
  poll → SIGKILL group → unlink).
- `env_keys.py` — add `DESKTOP_APP_BIN` (if absent), `DESKTOP_LOG`, `STORAGE_DIR`
  keys; keep in lockstep with `desktop/src/env.ts` per its header comment.

**Deleted (Python)**
- `cli/desktop_cmd.py::serve_desktop_backend`
- `cli/desktop_cmd.py::_build_desktop_backend_command`
- `cli/desktop_cmd.py::_build_desktop_backend_env`
- `cli/desktop_cmd.py::_resolve_backend_ports`
- (Rewrite, not delete) `cli/desktop_cmd.py::run_desktop_backend_server`,
  `run_desktop_launch`, `run_desktop_detached`, `spawn_detached_electron`,
  `prepare_desktop_launch` → thin delegators or moved into the new modules.

**Modified (TS / Electron)**
- `desktop/src/backendProcess.ts::buildBackendLaunch` — absorb `--storage-dir`,
  `--debug`, `STORAGE_DIR`/`DESKTOP_LOG` env, absolute bin from
  `env[ENV.DESKTOP_APP_BIN]` (fallback `"transport-matters"`), stale-env handling.
- `desktop/src/backendProcess.ts::launchBackendProcess` — `detached: true`, stdio
  `['pipe', logFd, logFd]` (stdin pipe kept for EOF; stdout/stderr → log file).
- `desktop/src/main.ts::registerAppLifecycle` — `quitOnWindowAllClosed: true`;
  wire the post-ready exit watcher (reap group + `app.quit`); install
  SIGTERM/SIGINT → `app.quit`; derive `workspaceDir` from `env[ENV.CWD]`.
- `desktop/src/env.ts::ENV` — add `STORAGE_DIR`, `DESKTOP_LOG`, `DESKTOP_APP_BIN`
  (mirror `env_keys.py`).

**Added (TS / Electron)**
- `desktop/src/backendProcess.ts::watchBackendExitAfterReady` (persistent
  after-ready exit watcher) and a `reapBackendGroup(pid)` helper (`process.kill(
  -pid, signal)`).

## PR-slice plan

Each slice is independently shippable and gated on the repo recipe.

1. **Ports off fixed (decision #3).** CLI allocates via `allocate_port_pair`,
   threads ports into the env contract; delete `_resolve_backend_ports` fixed
   default. Low blast radius; ships first.
2. **Single backend-command builder (decision #4).** Extend TS `buildBackendLaunch`
   for full env/argv/bin parity; delete Python `_build_desktop_backend_command` /
   `_build_desktop_backend_env`. TS + Python tests.
3. **Backend self-lifecycle (decisions #1, #5, #6) — correctness core.** New
   `desktop_backend_process.py`: uvicorn run + `setsid` + record write/unlink +
   parent-death watcher + killpg children; rewrite `_desktop-backend` handler;
   delete `serve_desktop_backend`.
4. **Electron owns backend + teardown wiring (decision #1).** Stop setting
   `DESKTOP_ROUTE_URL` for desktop launch; `registerAppLifecycle`
   `quitOnWindowAllClosed` + post-ready exit watcher + group reap + SIGTERM
   handler; `launchBackendProcess` detached + log-fd.
5. **Foreground redefinition (decision #2).** New `desktop_orchestration.py`:
   attached Electron launch + `run_tail` + SIGINT quit + wait; rewire
   `run_desktop_launch`; default detached path rewired; `desktop_cmd.py` slimmed.
6. **killpg external stop (decision #5).** `stop_desktop_record` group escalation;
   verify `channel stop` reaps the full backend subtree.

Dependency order: 1 → 2 → 3 → 4 → 5, with 6 landable after 3 (needs the group
leader). Slices 3–4 are the coupled correctness pair; review them together.

## Tests & gates

**Gates (repo recipes, verbatim).** Root `justfile`:
- `just check` — runs desktop/shell/@tm-* typecheck + api check.
- `just test` — runs `cd desktop && just test`, `cd www/packages/shell && just
  test`, `cd api && just test`.
- Focused passthroughs: `just api test`, `just desktop test`, `just api check`,
  `just desktop check`.

Every slice must pass `just check` and `just test`. Do not cite bare `pytest`,
`tsc`, or `vitest`.

**Python tests (`cd api && just test`)**
- `desktop_backend_process`: record write on startup + unlink on graceful
  shutdown; parent-death watcher triggers shutdown on simulated stdin EOF and on
  `getppid()==1`; killpg reaps a real child tree (spawn a dummy child in the
  group, assert reaped).
- `desktop_runtime.py::stop_desktop_record`: killpg reaps a spawned process group
  (leader + child), then unlinks; dead-pid path still returns `nothing`.
- `desktop_orchestration.launch_desktop`: allocates ports, assembles the env
  contract (asserts `DESKTOP_ROUTE_URL` absent, ports/bin/log present), foreground
  tail + SIGINT-quit-and-wait sequencing (with a fake Electron child).

**TS tests (`cd desktop && just test`)**
- `buildBackendLaunch`: argv + env parity (storage-dir, debug, absolute bin,
  stale-env), channel fallback.
- `launchBackendProcess`: `detached: true`, stdio shape (stdin pipe, stdout/stderr
  = log fd).
- `registerAppLifecycle`: `quitOnWindowAllClosed: true`; post-ready exit watcher
  reaps group + quits; SIGTERM/SIGINT → `app.quit`.
- `watchBackendExitAfterReady` / `reapBackendGroup`: negative-pid signal.

**Teardown matrix verification.** A scripted harness (documented, likely manual
given Electron E2E weight) that for each {foreground, detached} × {window close,
CTRL-C, Electron SIGKILL, backend crash, `channel stop`} launches, applies the
teardown, then asserts no surviving backend pid and no orphaned `mitmdump` (e.g.
`pgrep -f _desktop-backend` and the shared-proxy pid record are empty). This is
the acceptance test for the correctness core; call it out explicitly rather than
relying on unit tests alone.

## Open questions — resolved

- **Is `launchBackendProcess` prod-ready?** No. See the linchpin verdict; gaps 1–5
  above must close (parent-death watcher, quitOnWindowAllClosed, post-ready exit
  watcher, absolute bin, env/argv parity).
- **CLI ↔ Electron contract?** Env handshake (table above), not
  `build_backend_started_event` (viewer-oriented, lacks ports/channel/bin).
  Absence of `DESKTOP_ROUTE_URL` selects owned-backend mode.
- **Port allocation ownership?** CLI allocates (`allocate_port_pair`), hands via
  env; TOCTOU documented + surfaced through `BackendProcessExitError`.
- **Who writes/unlinks the record?** Backend writes on lifespan startup (only it
  knows its pid) and unlinks on shutdown; `stop_desktop_record` unlinks on
  `channel stop`; recovery cleans stale on next launch. Electron only reads (via
  `channel status`).
- **Backend Tier-1 log path/ownership?** `desktop_log_path(storage)`, resolved by
  the CLI, passed as `TRANSPORT_MATTERS_DESKTOP_LOG`; Electron redirects the
  child stdout/stderr to it; `--foreground` tails it via `tail_cmd.run_tail`.
- **Readiness?** Electron gates the window on `waitForLaunchedBackend` (health
  poll on `webPort`); CLI foreground optionally polls `wait_for_port_ready` for a
  banner. No IPC handshake.
- **Teardown matrix?** Above; closes with the parent-death watcher +
  `quitOnWindowAllClosed` + post-ready exit watcher + killpg group.

## Notes on honoring the locked decisions

All six locked decisions are designed to, not relitigated. The one nuance: the
spec implements decision #1's **intent** (backend dies with Electron by any cause)
with a backend-side parent-death watchdog, because the stated **mechanism**
(process parentage) does not reap children on macOS/POSIX. This is the specific
"what must change" the brief asked the linchpin analysis to surface.
