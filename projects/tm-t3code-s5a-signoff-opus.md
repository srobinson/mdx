---
title: Sign-off findings — t3code P1 Slice 5a (opus 5:2.3)
type: projects
tags: [transport-matters, t3code, p1, slice-5a, sign-off, review, reaping, self-reap]
summary: Opus independent sign-off on 5a (POSIX self-reap of orphaned mitmdump). Verdict GO-WITH-FIXES. False-reap safety confirmed (no surface daemonizes mitmdump; DETACHED is lifecycle-emission-only). 3 must-fix — sharpest is that addon.py is imported by ~10 test files, so arming the suicide watchdog at module import is a CI hazard. All spawn surfaces + flags grepped first-hand on main @ 915860f.
status: active
source: opus (5:2.3), first-hand on main @ 915860f
confidence: high
created: 2026-07-08
---

# 5a plan sign-off (opus) — GO-WITH-FIXES

Scope reviewed: §1, §2a, §2c, §5, §6 (POSIX self-reap). Windows Job §2d/§3 out of scope (5b).
Core design is sound and the "one addon-import seam covers all surfaces" elegance is real —
**IFF** the install is guarded to arm only in real mitmdump. 3 must-fix.

## Confirmed sound (independently verified on main @ 915860f)

- **False-reap safety holds.** No `os.fork`/daemonize/double-fork/`PR_SET_CHILD_SUBREAPER` anywhere
  in the tree (grepped). All mitmdump spawns go through `ProcessSupervisor.spawn` with
  `start_new_session=True` (own session/group) — ppid stays the spawner, never reparented to 1.
  The three surfaces (per-run `CaptureLeaseRegistry`→`prepare_captured_run`→`cli/runner`; shared
  `SharedProxyManager`→`shared_proxy/process.py`; CLI `transport-matters claude`) all keep mitmdump a
  child of a LIVE parent. No surface intends the proxy to outlive its spawner.
- **`LaunchKind.DETACHED` is NOT daemonization.** It only gates lifecycle-event emission from inside the
  addon (`addon_runtime._detached_lifecycle_enabled` / `_emit_detached_run_lifecycle_event`) so CLI runs
  emit their own RUN_STARTED/EXITED. The mitmdump is still a child of the CLI process. So the watchdog
  firing on CLI death is the correct reap, not a false-reap. Concern #1 resolved.
- **"any ppid change → reap" is safe.** ppid only changes when the real parent dies (no subreaper in the
  tree; macOS always reparents orphans to launchd/1). Concern #2 resolved.
- **The backend never imports the addon module** — it resolves it as a PATH
  (`captured_run_dependencies`: `files("transport_matters") / "addon.py"`, a Traversable) and passes it to
  `mitmdump -s`. So the watchdog never arms in the backend. (But see M1 — the TEST suite does import it.)

## Must-fix

### M1 — Do not arm the suicide watchdog at bare module import; arm in the addon's mitmproxy lifecycle hook (CI/prod hazard)

`transport_matters.addon` is imported by ~10 test files under `just test`
(`from transport_matters.addon import TransportMattersAddon` in test_http_provisional, test_response_stream,
codex/test_transport_turn_*, codex/test_transport_lifecycle, test_exchange_recorder_emit, …). Installing
`install_parent_death_reaping()` at addon.py module top arms a `getppid()`-polling daemon thread **with an
`os._exit(1)` fallback** inside the PYTEST process (and any future/accidental importer). A stable pytest ppid
usually won't fire, but under pytest-xdist workers, a supervised run, or any ppid shift, the watchdog
`os._exit(1)`s the test process — silent, no traceback, bypassing teardown/coverage/atexit. This is a latent
flaky-CI landmine created purely by the "install at import" choice.

Fix: arm inside `TransportMattersAddon.running()` (or `load(loader)`) so it fires ONLY when mitmdump actually
loads the addon — never on a bare import. The race-guard (M2) still catches an already-orphaned proxy at
arm-time, so the marginally-later arm point is safe. If module-import is kept instead, the test env MUST
globally set `TRANSPORT_MATTERS_NO_SELF_REAP=1` (conftest/pyproject) and §5.3 must prove no watchdog thread
survives an addon import — but the lifecycle hook is the elegant answer and keeps the "one seam" property
(the addon still covers every surface).

### M2 — macOS needs an already-orphaned-at-install guard (else it leaks the very bug being fixed)

Linux has the race guard (prctl, then re-check `getppid()`). The macOS path captures `getppid()` at install as
the baseline and reaps on CHANGE. If the parent died in the exec→addon-load window — exactly the backend-SIGKILL
scenario — `getppid()` is ALREADY 1 at install, so baseline==1, the value never changes, and the orphan is
never reaped. Add the macOS analogue of the Linux guard: at arm time, if `os.getppid() == 1` (already reparented
to launchd), reap immediately before entering the poll loop. Without this, a proxy orphaned in the startup
window survives forever on the exact platform the bug was found on.

### M3 — is_pid_alive Windows branch specifics (§2c)

The `os.kill(pid, 0)`→`TerminateProcess` landmine is real (Windows `os.kill` with any non-console signal,
including 0, terminates by pid — and desktop-record pid reuse could kill an unrelated process). The
OpenProcess+GetExitCodeProcess replacement is correct in shape; the build must: OpenProcess with
`PROCESS_QUERY_LIMITED_INFORMATION`; NULL handle → not alive; `GetExitCodeProcess` → `STILL_ACTIVE`(259)=alive
else dead (accept the exit-code-259 ambiguity, a known Win32 gotcha); ALWAYS `CloseHandle`; and define the
ACCESS_DENIED case consistently with the current POSIX `EPERM` branch (which returns False). Confirm the POSIX
path is byte-unchanged.

## Softer notes

- **`os._exit(1)` fallback budget vs emission fidelity.** mitmproxy exits cleanly on SIGTERM (its own handler →
  graceful shutdown → addon `done()` hooks). For CLI-DETACHED runs those hooks emit the RUN_EXITED lifecycle
  row. If the bounded `_exit` budget is shorter than mitmproxy's normal SIGTERM drain + addon `done()`, the
  fallback fires first and the detached run loses its RUN_EXITED row on every reap. Size the budget so
  `os._exit` only reaps a genuinely wedged proxy, not a normally-draining one.
- **§5.2 integration repro** uses a mitmdump STAND-IN (proves the watchdog mechanism, not the real
  addon-in-real-mitmdump path — an honest limit, covered by the manual macOS matrix). With §5.3's wiring
  assertion that's adequate; per M1, make §5.3 assert the lifecycle-hook arm, not module-import.

Scope discipline clean (POSIX-only; Windows Job deferred to 5b; pty_session untouched per 4f). The mechanism is
right; the fixes are the arm-point guard (M1), the macOS orphan guard (M2), and the Windows probe details (M3).
