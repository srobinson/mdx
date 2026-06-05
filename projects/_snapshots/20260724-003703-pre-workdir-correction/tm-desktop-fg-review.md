# PR#233 review — desktop `--foreground` exits when the viewer quits

- **Branch/head:** `feat/desktop-fg-exit` @ `0bed661`
- **Baseline:** `main` @ `cb2bf6f` (cited via `git show main:<path>`)
- **Scope:** the in-process `transport-matters desktop --foreground` launcher teardown.
- **Method:** xhigh adversarial pass, 2 independent read-only finders (teardown/race/extraction-fidelity; tests/scope/conventions) + first-hand verification + ran the suite. Tree pristine throughout.
- **Verdict:** No Blocker, no Major. Fix is correct, tested, and merge-ready. **1 Minor (scope, non-blocking).** One further scope item (the `desktop_viewer.py` extraction) was assessed and found justified, so it is not counted as a finding.

---

## The fix is sound (all correctness/behavior focus areas clean)

Baseline `serve_desktop_backend` already parked the main thread on `thread.join()` after `on_backend_ready()`, but `on_backend_ready()` took no arguments and `spawn_detached_electron` returned `None`, so the detached viewer's `Popen` was discarded and nothing ever set `server.should_exit`. The join blocked forever = the reported hang. The fix is minimal and targets exactly that:

- `spawn_detached_electron` now **returns** the `Popen` (`desktop_viewer.py:41`); `_spawn_or_exit` forwards it; `on_backend_ready(request_shutdown)` wires `_request_shutdown_on_viewer_exit(viewer, request_shutdown)`.
- `_request_shutdown_on_viewer_exit` (`desktop_cmd.py:231`) starts a daemon thread that blocks on `viewer.wait()` then calls `request_shutdown()`, which sets `server.should_exit = True` (`desktop_cmd.py:473`). Uvicorn's run loop (daemon thread) then returns, `thread.join()` (`desktop_cmd.py:492`) unblocks, and the command exits.

Verified against the brief's focus:

1. **Root-cause / no busy-wait / no leak/deadlock/race.** The watch thread is wired inside `on_backend_ready`, which runs only after `wait_for_port_ready` succeeds, so it never races readiness. If the viewer exits instantly, `viewer.wait()` returns immediately, `should_exit` is set, and `join()` returns as soon as uvicorn notices; the `finally` then sees the thread dead and no-ops. `should_exit` is a plain bool read in uvicorn's loop and written from the watch thread, safe under the GIL (uvicorn's own signal pattern). The watch thread completes at `request_shutdown()`, so it does not leak.
2. **Ctrl-C not regressed.** Uvicorn runs on a *daemon* thread, so `install_signal_handlers()` early-returns (not main thread) and leaves SIGINT to Python's default handler on the main thread, where `run_desktop_launch` parks on `thread.join()`. On CPython an infinite `join()` on the main thread is SIGINT-interruptible → `except KeyboardInterrupt: server.should_exit = True; raise` → bounded `finally: thread.join(timeout=5.0)` reaps the backend. This structure is pre-existing on `main`; the PR preserves it. Covered by `test_desktop_foreground_keyboard_interrupt_still_stops_backend`.
3. **Failing-before test is genuine.** `test_desktop_foreground_exits_when_viewer_quits` drives the **real** `serve_desktop_backend` (real in-process uvicorn on a daemon thread, real `thread.join`), patching only `preflight_session_store_or_exit` and `create_app` (a 204 stub). Removing the `_request_shutdown_on_viewer_exit` wiring makes `thread.join()` block forever → the 10s assertion times out. It asserts both that the command returns and that the backend port closes.
4. **No new orphan.** The backend is an in-process daemon thread; every exit path (readiness failure, `on_backend_ready` raising, viewer quit, Ctrl-C) routes through the bounded `finally` join, so it cannot outlive the command. (Detached-viewer survival on Ctrl-C is pre-existing and explicitly out of scope per the brief.)
5. **Extraction fidelity.** Every function moved into `desktop_viewer.py` (`resolve_electron_launch`, `_resolve_desktop_app_dir`, `_resolve_electron_binary`, `_packaged_app_binary`, `_path_from_env`, `_require_desktop_app_dir`, `_is_desktop_app_dir`, `_require_file`, `ElectronLaunch`, `ElectronResolutionError`, the four `DESKTOP_*_ENV` constants) is verbatim; `spawn_detached_electron` is verbatim plus the intended `return`. No dropped guard or error path; no leftover reference to a moved symbol in `desktop_cmd.py` (the `shutil` import was correctly removed).

**Conventions (`api/CLAUDE.md`) clean:** module-privacy boundary holds (only public names cross the `desktop_cmd → desktop_viewer` edge; `test_private_import_boundary` passes); all return types annotated; `raise ElectronResolutionError(...) from exc`; `ViewerProcess` is a `Protocol` (shape-only contract, correct); import DAG acyclic (`desktop_viewer` imports only `env_keys`); no em dashes.

**Gate observed:** `pytest test_desktop_foreground.py` → 2 passed; `test_desktop.py` + `test_desktop_idempotent.py` + `test_private_import_boundary.py` → 47 passed.

---

## Findings

### 1. [Minor — scope, non-blocking] `scripts/local-desktop-dev-mode.sh` bundles a separate dev-tooling change
`scripts/local-desktop-dev-mode.sh:96`

The PR also rewrites the tmux dev-mode script so a clean viewer quit (`exit 0`) tears down the whole dev window (`&& tmux kill-window -t <window_id>`, with the window id now captured via `tmux new-window -P -F '#{window_id}'`). It shares the *theme* of the fix (viewer quit → teardown) but not the mechanism (tmux `kill-window` vs uvicorn `should_exit`) or the surface, and it sits outside the brief's stated scope (`desktop_cmd.py` + its tests). The change is correct on its own and dev-only (unshipped), so this is a scope/process note, not a defect: it enlarges the blast radius of a fix PR and couples an untested dev script to the merge gate. Consider splitting it into its own dev-tooling change. Non-blocking.

---

## Assessed, not a finding: the `desktop_viewer.py` extraction

The new 163-LOC `desktop_viewer.py` extracts Electron resolution/spawn out of `desktop_cmd.py`, which the minimal fix did not strictly require. However, baseline `desktop_cmd.py` was **697 lines** (3 under the 700 guardrail), and the fix would push it over 700. Repo `CLAUDE.md` mandates: "Files already over 700 lines must be refactored *before* new code is added." So the extraction is the convention-correct move to make room, and `desktop_cmd.py` now sits at 599. Entangling a refactor with a bugfix does widen the diff (import churn across three test files), but here it is justified, verbatim, and low-risk. Not counted as a finding.
