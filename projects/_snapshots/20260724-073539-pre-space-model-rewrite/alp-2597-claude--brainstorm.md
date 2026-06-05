---
title: ALP-2597 Claude brainstorm — tmux pane loss after repeated manual interrupts
type: research
tags: [runtime-matters, tmux, shim, signals, ALP-2597, brainstorm]
summary: Root cause is shim/runtime co-tenancy in one process group; default SIGINT handling kills the shim, and tmux closes the pane when its pane-command (the shim) dies before shell_resume execs. Recommend signal-isolating the runtime (setpgid + tcsetpgrp) and converting the respawn-pane failure into a typed TmuxPaneUnavailable error.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

# ALP-2597 — Handle tmux pane loss after repeated manual interrupts

Independent Claude analysis. The Codex peer is investigating in parallel; this is the Claude pane's reading.

## 1. What the code actually does today

### Spawn flow (tmux target)

1. `rtm spawn ... --target tmux:S:W.P` arrives at the daemon via `rtm-daemon/src/handler.rs` (`RuntimeRpc::Spawn`).
2. `spawn_preflight::check` enforces session-id uniqueness and tmux occupancy. It does not validate pane liveness.
3. `ServerState::begin_spawn` calls `validate_spawn_target` → `validate_target` → `TmuxGateway::is_alive(address)` (`rtm-platform/src/tmux.rs`). `is_alive` runs `tmux has-session` then `tmux list-panes -F #S:#I.#P` and string-matches the exact `session:window.pane` triple. If false, the daemon returns a typed `RuntimeFailure::TmuxPaneDead { address }` mapped to `ErrorCode::TmuxPaneDead` (see `rtm-daemon/src/error.rs`).
4. If validation passes, the lifecycle is inserted as `Forking`, a launch spec is parked in `pending_launches`, a `ShimReady` oneshot waiter is registered.
5. `shim_socket::launch_shim` issues `tmux respawn-pane -k -t <addr> [-e RTM_SOCKET_PATH=...] -- <shim path> __shim --session-id <id>` (`rtm-daemon/src/shim_socket.rs` and `rtm-platform/src/tmux.rs::build_respawn_pane_args`). `-k` kills whatever command is currently running in the pane and re-execs the shim. The call requires the pane to already exist; there is no recreation path.
6. If `tmux respawn-pane` fails for any reason — pane vanished between step 3 and step 5 included — the failure is wrapped in an anyhow context (`"failed to respawn tmux pane <addr>"`) and surfaces as the generic `ErrorCode::LaunchFailed` in `rpc_error_response` because no `RuntimeFailure::TmuxPaneDead` is attached on this path.
7. On success the shim phones home via `ShimLaunch`, gets a `LaunchSpec`, `spawn`s the runtime as a child, sends `ShimReady`, then enters `wait_for_runtime` (`rtm-cli/src/cli/shim.rs`).

### Shim lifecycle inside the pane

The shim (`rtm __shim --session-id <id>`) is the tmux pane command. It does not call `setpgid` or `setsid` before spawning the runtime, so the runtime inherits the shim's process group. The shim installs only a SIGTERM handler (`install_sigterm_handler` in `rtm-cli/src/cli/shim.rs`); SIGINT, SIGHUP, SIGQUIT are left at their default disposition (terminate).

When the runtime exits, the shim calls `send_exit_blocking` (which feeds `ServerState::record_shim_exit` → `record_exited` → `Lifecycle::mark_exited` → `LifecycleState::Exited`). After exit reporting, if `launch.shell_resume.is_some()` the shim `exec`s into the user's shell with `env_clear` and the original `cwd`. For tmux spawns originating in `rtm-cli/src/cli/mod.rs::spawn` this is always populated via `capture_shell_resume` (`rtm-core/src/spawn_context.rs`), so a clean runtime exit leaves the user in their shell inside the pane and the pane stays alive.

### Lost detection

`ServerState::record_running` starts a `kqueue`-backed `ProcessExitWatcher` on the runtime PID (`rtm-platform/src/kqueue.rs`). When that fires, `record_watcher_exit`:

1. Sleeps 300 ms to let an in-flight `ShimExit` win the race.
2. Reads `is_terminal` to bail if the shim already reported.
3. Calls `watcher_evidence`: if the shim PID is alive, classify as `TerminationEvidence::ProcessExit`; otherwise `TerminationEvidence::Lost(LostEvidence::ShimDiedBeforeReport)`.

`ShimDiedBeforeReport` therefore has one precise meaning: the runtime PID exited and the shim PID is dead, without a `ShimExit` RPC having landed first. The reconcile sweep (`rtm-daemon/src/reconcile.rs::lost_evidence`) emits `PidNotAlive` and `PidReuseDetected` for the orthogonal case where the daemon discovers death later via polling.

### Pane-availability rendering

`ServerState::populate_log_availability` runs `is_alive` against the lifecycle's stored `tmux_pane` for every status read. Failure → `LogAvailability::Unavailable { reason: LogsUnavailableReason::PaneUnavailable }`. This is evaluated lazily and live, so it reflects the current tmux state, not the state at termination time. That is why `state.lost = ShimDiedBeforeReport` and `log_availability.payload.reason = pane_unavailable` coexist on the same lifecycle row.

Nudge has the same pattern (`ServerState::nudge_runtime` returns `NudgeFailureReason::TmuxPaneDead` on a dead pane). Capture (`ServerState::capture_pane`) checks `is_alive` before delegating to `TmuxGateway::capture_pane` and returns `CaptureError::PaneUnavailable`. Both of these are already typed.

### Existing typed surface

- `ErrorCode::TmuxPaneDead` (`rtm-core/src/error.rs`)
- `ValidateTargetOutcome::TmuxPaneDead { address }` (`rtm-core/src/types.rs`)
- `NudgeFailureReason::TmuxPaneDead`
- `CaptureError::PaneUnavailable`
- `LogsUnavailableReason::PaneUnavailable`
- `LostEvidence::ShimDiedBeforeReport`

The vocabulary already exists. The gap is that the *spawn* path does not use it for the post-validation pane-loss case.

## 2. Root cause hypotheses ranked by likelihood

**H1. Shim and runtime share a process group, and the shim does not trap SIGINT (highest).** Tmux delivers Ctrl+C as SIGINT to the foreground process group of the pane's PTY. Because `runtime_command` in `rtm-cli/src/cli/shim.rs` does not call `setpgid` or `setsid`, the runtime inherits the shim's PG. Both processes receive SIGINT. The runtime (Claude/Codex TUI) traps SIGINT and asks for confirmation. The shim takes the default action and dies. This is the *only* path that makes `ShimDiedBeforeReport` reachable on a tmux target during a Ctrl+C interaction, and it is exactly what road-test observed.

**H2. The pane's command is the shim, so when the shim dies, tmux closes the pane.** Tmux's `remain-on-exit` defaults to off. The pane was respawned with `respawn-pane -k`, which sets the pane's command to the shim invocation. As soon as that command exits, tmux closes the pane. If H1 fires first (shim dies before the runtime), the pane closes while the runtime is still alive; the runtime then loses its PTY and dies on the next IO write or SIGHUP. Net effect: even a single Ctrl+C can decimate the pane, but the timing window varies with how fast tmux notices, hence "repeated Ctrl+C" being the easy-to-repro path rather than the strict requirement.

**H3. `shell_resume` only runs on the clean path.** The `exec_shell_resume` branch in `run_for_session_blocking` is *after* `wait_for_runtime` returns. If the shim is killed mid-wait by SIGINT (H1), `wait_for_runtime` never returns, `send_exit_blocking` never fires, and `exec_shell_resume` never runs. The pane is left with no command at all, regardless of whether the runtime exits cleanly afterward.

**H4. TOCTOU between `is_alive` and `respawn-pane` on subsequent spawns (low-likelihood for this issue, but a real defect).** Once the pane is gone, the next `rtm spawn` against the same address validates → fails fast with `TmuxPaneDead`. But if a user (or session-matters) recreates a pane at the same address between `validate_target` and `launch_shim`, the typed-error guarantee is brittle: a transient race could surface as `ErrorCode::LaunchFailed` (anyhow string) instead of `TmuxPaneDead` because `launch_shim` does not classify respawn-pane errors. This is not the road-test symptom but is the same defect class.

**H5. Daemon/shim version drift after `just install-local` (mentioned in the issue's Related Caveat).** Real, but orthogonal to ALP-2597's core bug. Worth a separate enforcement issue.

H1 + H2 + H3 together explain every observation in the issue: `state.lost = ShimDiedBeforeReport`, `log_availability.reason = pane_unavailable`, and the variation between "exited cleanly" and "lost" (depending on whether the runtime got to call its SIGINT handler before tmux tore down the PTY).

## 3. Options analysis

The acceptance criteria lists three candidate directions: preserve, recreate, fail-typed. Below is each on its own, followed by the hybrid that I think we should actually ship.

### A. Preserve the pane across repeated interrupts

**Approach.** Make the shim survive Ctrl+C. Two sub-options:

- **A1 (preferred): signal-isolate the runtime.** Before `spawn()`, set the runtime to its own process group (`setpgid(child_pid, child_pid)`), then promote that PG to the PTY's foreground PG (`tcsetpgrp(stdin_fd, child_pid)`). The shim stays in the original PG. Ctrl+C delivers SIGINT only to the runtime, never the shim. This is the standard shell job-control pattern (bash/zsh do this for foreground jobs).
- **A2: trap and forward.** Shim installs SIGINT/SIGQUIT/SIGHUP handlers that forward the signal to the runtime PID (or its PG) and reset an atomic so the wait loop knows. Simpler to write but doesn't fix the fact that the runtime still receives every duplicated SIGINT from the same PG.

**What this buys.** Direct fix for H1. `ShimDiedBeforeReport` becomes a real Lost state (process killed externally), not a side-effect of Ctrl+C. The clean-exit ladder (`wait_for_runtime` → `send_exit_blocking` → `exec_shell_resume`) runs every time, so H3 stops mattering for the Ctrl+C case.

**What it doesn't fix.** Does nothing for panes the user closes via `tmux kill-pane`, panes destroyed by tmux server crash, panes never created in the first place. Pure preservation still needs a typed-fail safety net.

**Risks.** The PTY foreground-PG promotion is platform-sensitive (Linux, macOS, BSD all behave subtly differently). Tests for both Claude and Codex need to cover the SIGINT-while-prompted state. Existing tests like `process_exit_watcher_reports_lost_when_shim_dies_before_exit_report` (`rtm-cli/tests/integration_pass2.rs`) deliberately SIGKILL both processes; that contract must keep working.

### B. Recreate the pane deterministically before respawn

**Approach.** When `is_alive` returns false on the spawn path, allocate a fresh pane (via `tmux new-window` or `tmux split-window`) and use its new address.

**What this buys.** Spawn succeeds even if the original pane is gone.

**What it doesn't fix.** Does not prevent `ShimDiedBeforeReport` — that's a shim-signal-handling problem, not a pane-shape problem. Recreation only addresses the *next* spawn, not the *current* shim death.

**Why I'd reject this as the primary fix.** Three reasons.

1. *Address mutation breaks the contract.* `TmuxAddress` is the stable identifier callers store and reuse for nudge/capture/status. A new pane lives at a different `S:W.P` triple. Either rtm silently swaps the address (callers' cached state becomes wrong) or rtm tells callers "your address is now X" (a new RPC shape). Both are layering churn.
2. *Pane placement loses intent.* The original pane was created somewhere specific — a window the user named, a layout split they arranged. Allocating a "fresh pane" picks a new window or splits an arbitrary one. Runtime-matters does not know enough to make this decision well; the caller (session-matters or a human) does.
3. *Recreation hides destructive operator actions.* If the user ran `tmux kill-pane` on purpose, rtm silently spinning up a new pane defeats their intent.

Recreation as an *option* on the request — `--recreate-pane-if-missing` — could be added later for callers that genuinely want this, but it should not be the default and it should not be implicit.

### C. Fail with a precise typed `tmux_pane_unavailable` outcome

**Approach.** Convert the `tmux respawn-pane` failure inside `launch_shim` (or before, by re-checking liveness immediately before the respawn) into `RuntimeFailure::TmuxPaneDead { address }`. Same for any future operation that hits tmux without a preflight.

**What this buys.** Closes H4. Every consumer (humans, MCP, session-matters, future Nancy paths) gets a single typed contract: "pane is gone, recreate or pick a different target." No more ambiguous `LaunchFailed` strings to parse.

**What it doesn't fix.** Does not prevent the pane from dying in the first place. Without A, this is the consolation prize: "the pane is dead, here is a clean error" instead of "the pane is dead, here is a clean error and also it died because we killed the shim."

**Risks.** Almost none. The error variants already exist (`ErrorCode::TmuxPaneDead`, `ValidateTargetOutcome::TmuxPaneDead`). Adding the conversion is mechanical.

### D. Hybrid (recommended)

Combine A1 + C:

- **Shim signal isolation (A1):** runtime in its own PG, runtime PG is the PTY foreground, shim stays out of the SIGINT blast radius. Plus an explicit SIGINT/SIGQUIT/SIGHUP no-op handler on the shim so a stray signal (e.g. tmux server delivering SIGHUP on detach) does not kill the shim either.
- **Typed pane-unavailable error (C):** classify `respawn-pane` failures as `RuntimeFailure::TmuxPaneDead { address }` in `launch_shim`, with a `tmux list-panes` re-probe to distinguish "pane gone" from "tmux server gone" from "permissions or version oddities." Surface the same typed outcome anywhere a tmux call could legitimately fail because the pane vanished.
- **Explicitly do not recreate (B).** Pane lifecycle is owned upstream. Leave a documented seam (a future `--recreate-pane-if-missing` flag) but ship the default as fail-typed.

Why this combination and not A alone or C alone: A is the *fix* for the bug as reported; it stops the bleeding. C is the *contract hardening* that makes runtime-matters safe to consume even when A is bypassed (user kills the pane manually, tmux crashes, session-matters tears down a window). Shipping both means callers have one clean contract regardless of cause.

## 4. Recommendation

Ship hybrid D. Specifically, in this order:

1. **Signal-isolate the shim from its runtime.** In `run_for_session_blocking` (`rtm-cli/src/cli/shim.rs`), give the runtime its own process group and make that PG the PTY foreground PG (POSIX `setpgid` + `tcsetpgrp`). Add explicit `SIG_IGN` (or stub-handler-that-logs) for SIGINT, SIGQUIT, SIGHUP on the shim process so a stray PG-wide signal cannot kill it. Keep the SIGTERM handler intact for daemon-initiated termination.

2. **Reaffirm the shell-resume guarantee.** With H1 closed, the existing `exec_shell_resume` after `wait_for_runtime` reliably hands the pane to the user's shell on every clean exit. Verify this with a Claude + Codex repro test (see worker issues below). No structural change should be needed.

3. **Type the spawn-side pane-loss failure.** In `shim_socket::launch_shim`, when `TmuxGateway::respawn_pane` returns an error, re-probe with `is_alive`; if the pane is no longer alive, return `RuntimeFailure::tmux_pane_dead(address.clone())`. Otherwise preserve the existing anyhow context. This closes the TOCTOU gap with zero behavior change on the happy path.

4. **Optionally tighten the `is_alive` window before respawn.** Either move the liveness probe from `validate_target` into `launch_shim` (right before respawn) or call it twice. The double-check is cheap; one extra `tmux list-panes` per spawn is in the noise.

This is the most robust path because it (a) treats the shim as a proper process supervisor instead of a tmux command that happens to spawn a child, (b) preserves the existing typed-error vocabulary by extending it to the one path that bypassed it, and (c) does not invent pane-allocation semantics in runtime-matters. Every behavior change is local: the shim file gains ~30 lines of POSIX signal/PG setup, `launch_shim` gains a few lines of error classification.

### Why not also recreate

I considered adding optional recreation behind a flag. It is the wrong default for runtime-matters because pane allocation is policy, not mechanism. If session-matters or a human operator wants "pane gone, please recreate one," they can implement that on top of a typed `TmuxPaneDead` outcome: the policy lives where the placement decisions also live. Bolting recreation into runtime-matters duplicates that policy and forks the address contract.

## 5. Open questions and risks worth flagging

**Q1. Job control on tmux PTYs.** Tmux's pane PTYs are real PTYs, so `tcsetpgrp` from the shim should work. Confirm on Linux and macOS, particularly that the shim is the session leader of the PTY (which it should be by virtue of being the pane command). If the shim isn't session leader, `tcsetpgrp` fails with `ENOTTY` or `EPERM`. The harness in `crates/rtm-cli/tests/common/tmux.rs` can drive this.

**Q2. Foreground-PG handoff back to the shim on runtime exit.** After the runtime exits, the shim needs to either exec `shell_resume` (which becomes the new foreground PG) or quietly become the foreground PG itself before reporting `ShimExit`. The natural ordering is: runtime exits → shim regains FG PG → shim sends `ShimExit` → shim execs `shell_resume`. Need to validate the SIGTTOU/SIGTTIN scenarios.

**Q3. What about `kill_runtime` semantics under the new PG layout?** `ServerState::kill_runtime` calls `send_signal_for_kill(runtime_pid, ...)`. It targets the runtime PID specifically, not a PG. That should keep working unchanged. If the daemon ever wants to signal the whole tree, it should use `killpg(runtime_pgid, ...)`; not needed for ALP-2597 but worth noting.

**Q4. Is `remain-on-exit` ever set by upstream callers?** If session-matters or some workflow sets `remain-on-exit on` for the pane, then dead-shim-pane stays around as a tombstone and `is_alive` still returns true (the pane is in `list-panes` output). A later `respawn-pane -k` succeeds, but the user has staring at "Pane is dead" until then. Not strictly an ALP-2597 issue, but worth confirming the assumption is "remain-on-exit off everywhere."

**Q5. The Related Caveat from the issue (daemon/shim drift after `just install-local`).** Worth a separate issue under the runtime-matters spin tree: enforce that `just install-local` restarts (or warns about) a running daemon. Not blocking on ALP-2597 but the road-test surfaced it for a reason.

**R1. Risk: SIGINT-during-runtime-confirmation.** Even with signal isolation, a user who hammers Ctrl+C while Claude is in the "press CTRL+C again to quit" prompt will deliver many SIGINTs to the runtime. The runtime decides what to do — that is by design. If a runtime version mishandles a flurry of SIGINTs, that's a runtime bug, not a shim bug. We should not paper over runtime fragility in the shim.

**R2. Risk: existing process-exit-watcher tests assume the current shim PG.** `integration_pass2.rs::process_exit_watcher_reports_lost_when_shim_dies_before_exit_report` uses SIGKILL on both PIDs; the new layout must still surface `ShimDiedBeforeReport` when both PIDs are externally killed. SIGKILL bypasses PG semantics, so this should keep working, but it must be in the worker's verification list.

**R3. Risk: the typed-fail change is observable.** Callers that previously saw `ErrorCode::LaunchFailed` on a vanished pane will now see `ErrorCode::TmuxPaneDead`. That is the *correct* contract, but any caller currently special-casing the anyhow string needs to migrate. Likely zero internal callers; worth a grep across helioy repos before merge.

## 6. Selector-compatible issue structure proposal

High-level only; bodies stay as signposts per `helioy-tools:linear-workflows`, no inline Rust.

```
ALP-2597  [Master, Backlog]  Handle tmux pane loss after repeated manual interrupts
├── ALP-XXX-1  [Gate review, Todo]  Execution readiness for ALP-2597
└── ALP-XXX-2  [Execution parent, Backlog]
    ├── ALP-XXX-3  [Worker]  Reproducible failure test for Ctrl+C-induced pane loss (Claude + Codex)
    ├── ALP-XXX-4  [Worker]  Signal-isolate runtime from shim (process group + PTY foreground)
    ├── ALP-XXX-5  [Worker]  Shim ignores or no-ops SIGINT / SIGQUIT / SIGHUP
    ├── ALP-XXX-6  [Worker]  Type respawn-pane failure as TmuxPaneDead in launch_shim
    ├── ALP-XXX-7  [Worker]  Status / capture / nudge contract guardrails after the shim hardening
    └── ALP-XXX-8  [Post execution review]  Verify ALP-2597 acceptance criteria
```

Worker intent summary (signposts only, leave shape decisions to the worker):

- **ALP-XXX-3 — Repro test.** Establish the failing baseline as a `#[test]` (or `just`-driven integration scenario) that drives a real tmux pane, spawns a runtime, simulates rapid Ctrl+C delivery, and asserts the current bad outcome (`ShimDiedBeforeReport` + `PaneUnavailable`). Worker decides the harness shape. This must exist *before* the fix lands so the fix has something to flip green. Cover both `claude` and `codex` runtimes per acceptance criteria.

- **ALP-XXX-4 — Signal isolation.** In the shim, place the runtime in its own process group and make that PG the PTY foreground PG. Verify that SIGINT delivered to the pane reaches only the runtime, not the shim. Behavior change is observable as `wait_for_runtime` continuing through one or more Ctrl+Cs and the shim still being alive to report `ShimExit`.

- **ALP-XXX-5 — Shim signal disposition.** SIGINT, SIGQUIT, SIGHUP on the shim process must not terminate it. Decide between `SIG_IGN` and a logging handler. SIGTERM behavior stays as documented (daemon-initiated termination).

- **ALP-XXX-6 — Type the spawn-side failure.** When `respawn-pane` returns an error and a follow-up liveness probe shows the pane is gone, return the existing `RuntimeFailure::tmux_pane_dead(address)`. Other respawn failures keep their current generic context. Same outcome shape as the validate-time error; consumers see one contract.

- **ALP-XXX-7 — Status / capture / nudge guardrails.** Confirm that after the shim hardening, the lazy `populate_log_availability` continues to reflect live pane state, and that nudge/capture/status still produce typed `*PaneDead` / `PaneUnavailable` outcomes when the pane really is gone. Make sure the existing `process_exit_watcher_reports_lost_when_shim_dies_before_exit_report` integration test still passes against the new shim layout.

- **ALP-XXX-8 — Post execution review.** Verify each acceptance criterion against the merged code: repro covers both runtimes, repeated Ctrl+C does not silently kill the pane, every typed failure path is reachable, subsequent spawn to the same address either succeeds or fails with `TmuxPaneDead`, existing `sm delete agent` semantics unchanged.

A separate, sibling issue (not part of this gate) should be filed for the Related Caveat (`just install-local` daemon/shim version drift). It is orthogonal cleanup and should not block ALP-2597.
