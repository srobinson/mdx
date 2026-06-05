---
title: "Scout & Plan: non-blocking port-conflict launch flow (desktop/start)"
type: research
tags: [transport-matters, cli, port-conflict, launch, doctor, dry, scout]
summary: "Two parallel pinned-port preflights (resolve_launch_ports vs desktop._resolve_backend_ports) both hard-exit(2); the recovery branch for our-orphan/our-live/foreign belongs in ONE unified preflight, reusing doctor's injectable-confirm + reap infra."
status: active
source: codebase-analyst
confidence: high
created: 2026-06-23
updated: 2026-06-23
---

# Scout & Plan: non-blocking port-conflict launch flow

**Baseline:** `main @ e3aaecf`, read-only, tree verified pristine. Citations are file+symbol (no line numbers).
**Scope (per brief):** call-site REUSE MAP + user-facing FLOW. The low-level port→PID/ownership classifier is the **peer scout's** mechanism; this report treats `classify(port) → {OUR_ORPHAN, OUR_LIVE, FOREIGN}` as an injected dependency and does not design its internals.

**Problem.** `transport-matters desktop`/`start` call `net.raise_port_in_use` (→ `typer.Exit(2)`) on a pinned-port conflict, blocking the user even when the listener is our own stale orphan. Target: never block. Honor three cases — (a) OUR stale orphan → recover automatically; (b) OUR live instance → do not kill, surface/reuse; (c) FOREIGN process → keep today's error + `--web-port`/`--proxy-port` fallback.

---

## Reuse Map

### The two parallel preflights (the DRY break)

There are **two independent pinned-port preflights**, one per launch family, both ending in `net.raise_port_in_use`:

1. **`start` / `claude` family** — the shared path:
   `start_cmd.run_start` → `captured_run.run_captured_run_on_local_tty` → `launch_runtime.prepare_launch` → **`launch_runtime.resolve_launch_ports`**.
   `resolve_launch_ports` raises at two sites: the capture-only proxy branch, and the proxy+web loop. **Guard: only when `pinned`** (`proxy_user_supplied`/`web_user_supplied` or a `channel_spec`). Auto-allocated ports are intentionally *not* preflighted here — they rely on `ports.allocate_port_pair` returning free ports, with later `bind_failure.handle_bind_failure` retry (`bind_failure.BIND_RETRY_ATTEMPTS = 3`).

2. **`desktop` family** — the duplicate path:
   `desktop_cmd.run_desktop_launch` / `desktop_cmd.run_desktop_detached` → `desktop_cmd.prepare_desktop_launch` → **`desktop_cmd._resolve_backend_ports`** → `net.raise_port_in_use`.
   **Guard: none** — it probes *both* ports unconditionally (no pinned gate), so it also errors on channel-default and freshly-allocated ports.

### Every `raise_port_in_use` call site (non-test)

- `net.raise_port_in_use` — **definition** (emits the red error + `Exit(2)`); the case-(c) terminal.
- `launch_runtime.resolve_launch_ports` — site 1 (capture-only proxy).
- `launch_runtime.resolve_launch_ports` — site 2 (proxy + web loop).
- `desktop_cmd._resolve_backend_ports` — site 3 (proxy + web loop, duplicate).

`net.port_in_use` (the probe) is threaded everywhere as an injected `Callable[[int], bool]` (DI seam — peer's territory); the **only** hard-exit choke points are the three `raise_port_in_use` sites above.

### Where the recovery branch belongs (ONE code path)

Both preflights converge on the identical shape: compute `(label, flag, port, pinned?)`, then `if port_in_use(port): raise_port_in_use(label, flag, port)`. That junction is the single insertion point. DRY-correct move: **collapse `desktop_cmd._resolve_backend_ports` onto `launch_runtime.resolve_launch_ports`**, then replace the bare raise with one classifier-driven helper so both families share the recovery logic. Putting recovery inside `net.raise_port_in_use` itself is wrong — it is a context-free leaf and bakes in `Exit(2)`.

### Existing infrastructure to lean on (do not rebuild)

- **Injectable confirm + skip convention (already shipped in `doctor`):** `doctor` (in `cli/__init__.py`) exposes `--yes/-y` and calls `run_doctor(confirm=(lambda _run: True) if yes else None)`. `diagnose.run_doctor` builds `diagnose._default_confirm` = `typer.confirm(...)` when none is injected, and passes it to `diagnose.report_runs_health(confirm=...)`. This is the exact interactive-prompt-with-non-interactive-override pattern the flow needs — mirror it, do not invent a new one.
- **Orphan reap (live, API-mediated):** `runs_health.orphan_candidates` selects stale RUNNING runs; `runs_health.reap_run` does `POST /v1/runs/{id}/terminate`. This reaps OUR API-tracked runs **only when the local API answers** — it does not PID-kill a wedged orphan (that is the peer's classifier/kill mechanism).
- **Identity probe for "is this OURS?":** `runs_health.fetch_runs` (`GET /v1/runs`, returns `None` on `ConnectError`) + `net.loopback_http_url` can confirm whether the listener is our live API before deciding reuse-vs-foreign.
- **Viewer-attach primitive for case (b):** `desktop_cmd.spawn_detached_electron` already launches the Electron viewer pointed at a backend's `web_port`, and `net.wait_for_port_ready` polls readiness. The components to *attach a viewer to an already-listening backend* exist; what is missing is a branch that detects "backend already up → skip spawn, attach viewer."

---

## Quality Map (code-hygiene lens, read-only)

- **P0 — Duplicated preflight.** `desktop_cmd._resolve_backend_ports` reimplements the `(label, flag, port)` probe-and-raise loop already owned by `launch_runtime.resolve_launch_ports`. Two owners of one policy; any recovery work would otherwise have to be written twice. Consolidate before adding recovery.
- **Behavioral divergence (latent bug).** `resolve_launch_ports` errors only on **pinned** ports; `_resolve_backend_ports` errors on **all** ports including channel-default and just-allocated. The probe on freshly `allocate_port_pair`'d ports in the desktop path is also near-dead work (allocated ports are free by construction). Reconcile to one policy when unifying.
- **`net.raise_port_in_use` couples message + `Exit(2)`.** Correct as the foreign-process terminal, but recovery cannot live inside it. Keep it as case-(c)-only.
- **Doc drift.** `net.py` module docstring says the helpers are "used by `start` and `doctor`"; `desktop` is now a third consumer.
- **LOC pressure.** `desktop_cmd.py` is 652 LOC (under the 700 guard, but close per repo CLAUDE.md). Folding its port preflight onto the shared helper shrinks it and avoids tripping the guard on the next desktop addition.

---

## Plan (recommended; not executed — read-only scout)

1. **Unify the preflight (DRY first).** Route `desktop_cmd.prepare_desktop_launch` through `launch_runtime.resolve_launch_ports` (it already supports `web_required` and channel-spec defaults) and delete `desktop_cmd._resolve_backend_ports`. Reconcile the guard to one policy — recommend matching `start`/`claude`: preflight only pinned/channel-fixed ports; allocated ports keep relying on allocate + `bind_failure.handle_bind_failure` retry. Update `cli/test_desktop.py`, `cli/test_ports.py`, `cli/test_launch_preflight.py`.

2. **Insert ONE recovery seam in `resolve_launch_ports`.** Replace each `if pinned and port_in_use(port): raise_port_in_use(...)` with a single `recover_or_raise(label, flag, port, *, classify, confirm, reap)` that:
   - `classify(port)` (peer's mechanism) → `OUR_ORPHAN` | `OUR_LIVE` | `FOREIGN`.
   - **OUR_ORPHAN → recover:** reap (reuse `runs_health.reap_run` when API-mediated; peer's PID-kill when wedged), then re-probe; proceed if freed.
   - **OUR_LIVE → reuse (case b):** desktop = skip backend spawn, attach viewer via `spawn_detached_electron` at the live `web_port`; `start`/`claude` = surface "already running at `loopback_http_url(web_port)`" and reuse/exit-0 (**product decision — see open questions**).
   - **FOREIGN → `raise_port_in_use`** (unchanged; the message already carries the `--proxy-port`/`--web-port` fallback hint).

3. **Auto-kill vs confirm-then-kill (UX surface).** Mirror `doctor`'s pattern exactly: thread a `confirm: Callable[..., bool] | None` from the command layer; default interactive prompt = `typer.confirm(f"Reclaim {label} port {port} from stale run …?")`; add `--yes/-y` (or `--force`) on `desktop`/`claude`/`codex` that injects `lambda: True`.
   - **Non-interactive / CI degradation (critical, the trap):** `typer.confirm` raises `Abort` with no TTY — which would re-block launch, the exact failure we are removing (and `doctor` has this same latent gap today). Guard with `sys.stdin.isatty()`: when not a TTY and no `--yes`, take the SAFE non-destructive path (OUR_ORPHAN → print reclaim hint and proceed only if auto-recover is chosen; FOREIGN → keep error + `--web-port`). Never silently kill a process in CI.
   - **Default recommendation:** auto-recover `OUR_ORPHAN` without a prompt is defensible (it is our own dead process); reserve confirm for any path that could touch a non-orphan. Final auto-vs-confirm choice is the human's (their two candidates both map onto this seam).
   - **`--yolo` caveat:** `--yolo` today is *only* `launch_profile.CODEX_BYPASS_PERMISSIONS_ARG`, a Codex passthrough — not a TM-launch flag and not wired to confirm-skip. Do not overload it; use `doctor`'s established `--yes/-y`. (NOW.md's `--yolo` references are the separate Codex auto-capture toggle.)

4. **doctor coupling / shared home.** The classify + reap helper is useful to both launch and `doctor`. Place it in a neutral module (e.g. `cli/port_recovery.py`) that imports the peer's classifier and reuses `runs_health.reap_run`; have `resolve_launch_ports` call it, and let a future `doctor` port-reclaim (`doctor --fix`, or extending `--reap-orphans` to free pinned launch ports) call the same helper. `doctor` already owns orphan reaping via `--reap-orphans`; do not duplicate it in the launch path.

5. **Verification gates (when implemented).** `pytest` over `cli/test_ports.py`, `cli/test_launch_preflight.py`, `cli/test_desktop.py`, `cli/test_diagnose.py`, plus the start/desktop acceptance suites; then the repo gate (`just check` / `just test` per repo CLAUDE.md — gates are repo recipes, not bare `pytest`). Add focused cases for all three listener classes (orphan→recover, live→reuse, foreign→error) and the non-TTY degradation default.

### Open questions for the human
- **Case (b) for `start`/`claude`:** "reuse" is well-defined for desktop (attach viewer), but ambiguous for the plain CLI — exit-0 pointing at the running instance, or block? Needs a product call.
- **Default behavior:** auto-kill vs confirm-then-kill for `OUR_ORPHAN` (recommend auto for orphan, never for foreign).
