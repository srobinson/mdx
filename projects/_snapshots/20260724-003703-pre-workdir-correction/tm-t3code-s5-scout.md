---
title: Plan — t3code P1 Slice 5, cross-platform SIGKILL reaping (spec §3 reconciled with the post-4e tree)
type: projects
tags: [transport-matters, t3code, p1, slice-5, scout, plan, reaping, teardown, self-reap]
summary: Spec §3's "capture sidecar" does not exist — mitmdump hangs directly off the Python backend (canvas + shared proxy) and off the CLI (detached), and our addon already runs INSIDE every mitmdump, which is the real self-reap seam. Plan installs a parent-death watchdog (macOS getppid poll + Linux PR_SET_PDEATHSIG, one module, imported at addon load), leaves the gateway PTY edge to POSIX SIGHUP semantics (verified in the matrix, no new code), OS-branches the genuinely dangerous is_pid_alive Windows landmine, and proposes 5a (POSIX now, closes Stuart's live macOS leak, pure stdlib, locally verifiable) / 5b (Windows Job Objects + Q7 binding, coupled to D1). Q7 turns out to be TS-side only — Python's Windows Job needs just ctypes.
status: active
source: scout (fable 5:2.1), first-hand on main @ 915860f
confidence: high (every spawn site and flag grepped on main; spec process-model corrected from code)
created: 2026-07-08
---

# Plan — Slice 5: SIGKILL reaping

Citations are file + symbol, verified on main @ 915860f.

---

## 1. Reconciled architecture — the REAL spawn tree (spec §3 premise corrected)

**The spec's "dedicated Python capture sidecar (the sidecar IS the child)" does
not exist.** Post-4e reality:

```
Electron (DesktopShutdown; finalizers gateway→python)
├─ gateway (node, @tm/gateway runGatewayProcess)
│   └─ PTY agent (claude/codex) — NodePtyAdapter → node-pty spawn
│        [own session; PTY slave is its controlling terminal]
└─ Python backend (transport-matters _desktop-backend, uvicorn in-process)
    ├─ per-run mitmdump — CaptureLeaseRegistry → prepare_captured_run →
    │    cli/runner.start_prepared_proxy → ProcessSupervisor.spawn("mitmdump",…)
    │    [supervisor_core.spawn: start_new_session=True (own process group),
    │     stdin=DEVNULL, stdout/err → log file]
    └─ shared-proxy mitmdump — SharedProxyManager → shared_proxy/process.py
         (its own ProcessSupervisor.spawn, same flags)

CLI detached (`transport-matters claude`): the CLI process spawns mitmdump
(background, own session) + the agent (foreground/PTY) via the same supervisor.
```

Three consequences that reshape §3's design:

1. **The self-reap seam is the addon, not a sidecar entrypoint.** Every mitmdump
   we ever spawn runs OUR code in-process (`mitmdump -s addon.py`;
   `captured_run_dependencies.require_addon` → `transport_matters/addon.py`).
   `install_parent_death_reaping()` installs at addon import — one seam covers
   the per-run proxies, the shared proxy, and CLI-detached proxies identically.
2. **stdin-EOF watchdog is unavailable as-built**: background spawns wire
   `stdin=subprocess.DEVNULL` (`supervisor_core.ProcessSupervisor.spawn`), so
   the macOS mechanism is the `getppid()` poll alone (the spec offered either).
   No spawn-wiring change needed.
3. **Graceful subtree reap already exists and is per-child, not setsid-leader:**
   each background child is its own process-group leader
   (`start_new_session=True`, `process_group=pid`) and
   `ProcessSupervisor.terminate_all` `killpg`s each group with SIGTERM→grace→
   SIGKILL. §3's "backend as setsid leader killpg'ing its subtree" is already
   satisfied by a better shape; **no new graceful-path code**. The lifespan
   chain (registry.close → lease.close → terminate_all) covers graceful exits;
   slice 5 is purely the SIGKILL'd-parent hole.

**The gateway PTY edge needs no new POSIX code.** node-pty children run with the
PTY slave as their controlling terminal; when the gateway dies (any signal), the
master closes and the kernel delivers SIGHUP to the agent's foreground group —
the agent exits. On Windows, process death closes the ConPTY handle and closing
the pseudoconsole terminates attached clients. The teardown matrix ASSERTS this
(kill -9 the gateway, agent gone) rather than adding code; the residual risk
(an agent that ignores SIGHUP, or its detached grandchildren) is exactly what
the 5b Windows Job / a future POSIX belt would cover — documented, not built.

**Residual gap named, out of scope:** gateway SIGKILL with Python still alive
leaves capture leases held (releaseCapture never arrives) — mitmdump keeps
running under a LIVE parent, so parent-death reaping rightly does not fire.
That is a lease-GC/gateway-restart concern (doctor sees it once a gateway is
back), not a reaping one. Flagged for the roadmap, not slice 5.

---

## 2. Mechanism design per edge

### 2a. mitmdump self-reap (the live macOS bug — highest value)

New module `api/src/transport_matters/self_reap.py` (root leaf: shared by the
addon and importable by tests; no api/cli-layer coupling):

- `install_parent_death_reaping(*, expected_parent: int | None = None) -> None`
  - Captures `os.getppid()` at install.
  - **Linux**: `ctypes.CDLL("libc.so.6", use_errno=True).prctl(PR_SET_PDEATHSIG=1,
    SIGTERM)` THEN re-check `os.getppid()` — if the parent already died between
    exec and install (reparented: ppid changed / == 1), self-terminate
    immediately (the race guard). pdeathsig delivers SIGTERM → mitmproxy's own
    handler drains flows.
  - **macOS (and POSIX fallback)**: daemon watchdog thread polling
    `os.getppid()` every ~1s; on change (reparent to launchd/1 or any new pid),
    `os.kill(os.getpid(), SIGTERM)` so mitmproxy shuts down cleanly, then a
    bounded fallback `os._exit(1)` if still alive after a few seconds (a wedged
    proxy must not survive its parent).
  - **Windows**: no-op in 5a (Job Object in 5b); guarded by `sys.platform`.
  - Idempotent; env kill-switch `TRANSPORT_MATTERS_NO_SELF_REAP=1` for
    debugging a proxy past its parent (doctor/docs mention it).
- `addon.py` calls it at import (module top, before runtime load), so every
  mitmdump self-reaps regardless of which surface spawned it.

Threading note: the watchdog is a daemon thread inside mitmdump's process —
it never runs in the backend/CLI, so no interaction with our asyncio loops.

### 2b. Gateway PTY edge

No new code (§1). Matrix test asserts the SIGHUP semantics.

### 2c. POSIX-only debt (§3), OS-branched where cheap

- `desktop_runtime.is_pid_alive` — **a genuine Windows landmine**: on Windows
  `os.kill(pid, 0)` does not probe, it TERMINATES (sig 0 → TerminateProcess
  exit code 0). OS-branch now (cheap, mock-testable): POSIX keeps `os.kill(pid,
  0)`; Windows probes via `ctypes.windll.kernel32.OpenProcess` +
  `GetExitCodeProcess` (stdlib only).
- `desktop_runtime.stop_desktop_record` — injectable `kill` already; document
  that the Windows default is a hard TerminateProcess (no grace) and leave the
  graceful-Windows story to 5b.
- `cli/desktop_cmd.py start_new_session=True` — harmless no-op on Windows
  (POSIX-only semantic); annotate, don't rework.
- `pty_session.py` untouched (4f's deletion, per brief).

### 2d. Windows Job Objects (proposed 5b)

Two owners, per spawn edge (spec §3 confirmed correct here):

- **TS**: `packages/runtime/src/adapters/platform/JobObject.ts` — Job with
  `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` over the node-pty agent (covers the
  agent's SUBTREE, which ConPTY close alone does not).
- **Python**: a Job over each mitmdump — **needs NO binding decision**:
  `ctypes.windll.kernel32` (`CreateJobObjectW`/`SetInformationJobObject`/
  `AssignProcessToJobObject`) is stdlib. Q7 is therefore **TS-side only** —
  a correction to the spec's framing worth recording.

---

## 3. Q7 — the TS-side Win32 binding (Stuart decision, needed for 5b only)

| Option | For | Against |
| --- | --- | --- |
| **(a) In-repo N-API addon** | Full control; smallest runtime surface; prebuild alongside node-pty (which already imposes native-module discipline on packaging) | New native toolchain in CI; prebuild matrix; couples hard to D1 packaging |
| **(b) Prebuilt helper exe** (tiny C/Rust: create Job, spawn target inside it) | No node-ABI coupling at all; testable as a black box | New artifact pipeline + signing; changes the spawn shape (agent runs under a wrapper — must still forward ConPTY correctly, non-trivial) |
| **(c) Existing npm shim / FFI** (survey first per spec; e.g. koffi-based FFI to kernel32) | No native build of our own; fastest to land | Dependency-health risk (the classic ffi-napi is unmaintained); FFI overhead irrelevant here but ABI drift risk on Electron/node bumps |

Recommendation to carry into the 5b decision: **survey (c) first, fall back to
(a)**; (b) only if the packaging story prefers exes. All three are moot until
5b is scheduled, which is why the scope split below keeps Q7 out of 5a.

## 4. Scope split — recommendation (Stuart decision D-5.1)

**5a (this slice): POSIX self-reap.** macOS watchdog + Linux pdeathsig in
`self_reap.py` wired into the addon, the `is_pid_alive` OS-branch, and the
POSIX teardown-matrix tests. Pure stdlib (ctypes/threading), zero native deps,
zero packaging coupling, and it closes the one LIVE bug on Stuart's platform
with a verification he can run himself (§5). **5b (follow-up, coupled to D1):
Windows Job Objects both edges + Q7 binding + Windows matrix legs.** Rationale:
the Windows half is locally unverifiable, needs a native-binding decision, and
inherits D1's packaging pole; holding 5a hostage to it delays the only
currently-reproducible leak for zero macOS/Linux benefit. All-in-one is the
alternative only if Stuart wants Q7 settled now.

## 5. Teardown matrix (§9) — test plan

**Automated (POSIX, run in `just test`):**
1. `self_reap` unit tests (colocated `test_self_reap.py`): watchdog fires on
   ppid change (fake `getppid` sequence → SIGTERM to self observed via injected
   `kill`); bounded `_exit` fallback fires when the process ignores SIGTERM;
   idempotent install; env kill-switch; Linux branch `@skipif(not linux)`:
   prctl installed + already-orphaned early-exit guard.
2. **Integration — the SIGKILL leak repro** (`tests/integration/`): a launcher
   script spawns a python "parent" which spawns a python "mitmdump stand-in"
   that imports `self_reap.install_parent_death_reaping()` and sleeps; test
   SIGKILLs the parent, asserts the child exits within the watchdog budget
   (macOS + Linux paths of the same test). A control case without install
   asserts the child survives — proving the test can fail.
3. **Addon wiring**: assert `addon.py` installs at import (monkeypatched
   installer records the call; runs inside the existing addon test harness).
4. **Gateway PTY SIGHUP leg**: integration test spawns a real node-pty… is
   heavy in Python CI; instead a vitest case in `packages/runtime` spawning
   `NodePtyAdapter` with a `sleep`-ish shell child, SIGKILLing the OWNING
   process is impossible in-process — so this leg lands in the MANUAL matrix
   (below) plus a unit-level note. (Honest limit: in-process tests cannot
   SIGKILL themselves.)
5. `is_pid_alive` OS-branch unit tests (Windows branch via mocked ctypes).

**Manual matrix for Stuart (macOS, the acceptance he asked for):**
```
transport-matters desktop (or pnpm --dir desktop dev) → spawn a canvas run
pgrep -fl mitmdump            # per-run proxy live
kill -9 <python backend pid>  # the hard-kill hole
sleep 3 && pgrep -fl mitmdump # EMPTY → bug closed
# and the gateway edge:
kill -9 <gateway pid> ; sleep 1 ; pgrep -fl "claude" # agent gone via SIGHUP
```
Shipped as a checklist in the PR description (matrix rows: {window close,
backend SIGKILL, gateway SIGKILL, PTY exit, terminate} — graceful rows already
covered by 4e-b ordering tests).

## 6. Touch list (5a)

| File | Change |
| --- | --- |
| `api/src/transport_matters/self_reap.py` (new) | `install_parent_death_reaping` + watchdog + prctl branch + kill-switch |
| `api/src/transport_matters/test_self_reap.py` (new) | unit suite (§5.1) |
| `api/src/transport_matters/addon.py` | install at import |
| `api/tests/integration/test_parent_death_reaping.py` (new) | SIGKILL repro (§5.2) |
| `api/src/transport_matters/desktop_runtime.py` | `is_pid_alive` OS-branch (+ unit tests in its existing test file) |
| PR checklist | manual macOS matrix (§5) |

~6 files, no desktop/TS changes, no packaging changes.

## 7. Decisions for Stuart

- **D-5.1** — scope split 5a/5b as above (recommended) vs all-in-one.
- **Q7** — TS-side Windows binding choice (survey npm/FFI → N-API fallback →
  helper exe), needed only when 5b is scheduled. Python side needs no decision
  (ctypes suffices) — a spec correction.
