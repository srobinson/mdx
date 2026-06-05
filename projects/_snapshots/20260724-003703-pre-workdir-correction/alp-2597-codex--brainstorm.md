# ALP-2597 independent brainstorm: tmux pane loss after repeated manual interrupts

Date: 2026-05-21
Repo: `/Users/alphab/Dev/LLM/DEV/helioy/runtime-matters`
Issue: ALP-2597
Scope: investigation only, no code or Linear writes

## Executive summary

The most robust fix is preservation first: make the tmux shim survive user generated SIGINT while the managed runtime handles its own interrupt semantics, then always report the terminal lifecycle before execing the resume shell. Recreating panes is attractive as a recovery story, but current targets use `SESSION:WINDOW.PANE` indexes rather than stable tmux `%pane_id`s, so deterministic recreation can target the wrong logical pane or mutate a user's tmux layout. Typed failure should remain the explicit fallback for genuinely missing panes.

## Project metadata

- Language: Rust, workspace edition 2024.
- Workspace crates: `rtm-core`, `rtm-client`, `rtm-paths`, `rtm-platform`, `rtm-launchers`, `rtm-store`, `rtm-daemon`, `rtm-cli`.
- Build and verification contract from project instructions: `just check && just build && just test`.
- Public protocol crates: `lilo-rm-core` and `lilo-rm-client`, currently referenced as version `0.6.0` in workspace dependencies.
- Relevant dependency surface: `tokio` for daemon async runtime and process spawning, `sqlx` for lifecycle persistence, `clap` for CLI, `serde` for JSON line protocol, tmux through `rtm-platform` commands.
- fmm status: `.fmm.db` exists in the checkout and fmm was used first for topology, symbol outlines, and targeted source reads.

## 1. What the code actually does today

### Tmux target model

- `SpawnTarget` supports a tmux target, and `SpawnTarget::tmux_address` exposes the `TmuxAddress` if present in `crates/rtm-core/src/types.rs:293-304`.
- `TmuxAddress` is parsed and displayed as `SESSION:WINDOW.PANE`, not as a tmux `%pane_id`, in `crates/rtm-core/src/types.rs:139-194`.
- The CLI labels the accepted target shape as `headless|tmux:SESSION:WINDOW.PANE` in `crates/rtm-cli/src/cli/mod.rs:71-87`.

Implication: the current identifier is a positional tmux pane address. It is good enough while the pane exists, but it is not a durable object identity after panes close, indexes shift, windows close, or sessions are recreated.

### Spawn path

- `rtm spawn` captures caller env, captures shell resume only for tmux targets, then calls `RuntimeClient::spawn` with `SpawnRequest` in `crates/rtm-cli/src/cli/mod.rs:191-220`.
- The daemon handles `RuntimeRpc::Spawn` by checking conflicts, building a launch spec, inserting a forking lifecycle, launching the shim, waiting up to 10 seconds for `ShimReady`, then recording running state in `crates/rtm-daemon/src/handler.rs:100-135`.
- The tmux launch path calls `TmuxGateway::respawn_pane` with `rtm __shim --session-id <id>` in `crates/rtm-daemon/src/shim_socket.rs:25-36`.
- `TmuxGateway::respawn_pane` shells out to `tmux respawn-pane -k -t <target> -e RTM_SOCKET_PATH=... -- <argv>` in `crates/rtm-platform/src/tmux.rs:30-40` and `crates/rtm-platform/src/tmux.rs:201-222`.

There is no recreation path. `tmux respawn-pane` requires the pane target to exist.

### Pane liveness validation before spawn

- `spawn_preflight::check` rejects session id reuse and live tmux pane occupancy, but it does not validate the target pane exists before occupancy lookup returns empty in `crates/rtm-daemon/src/spawn_preflight.rs:11-40`.
- `ServerState::begin_spawn` does validate target liveness through `validate_spawn_target` before inserting forking state in `crates/rtm-daemon/src/server.rs:160-199`.
- `validate_target` calls `TmuxGateway::is_alive` and returns `ValidateTargetResponse::tmux_pane_dead` when the target is absent in `crates/rtm-daemon/src/server.rs:214-224`.
- `TmuxGateway::is_alive` checks `tmux has-session -t <session>`, then `tmux list-panes -t <target> -F #S:#I.#P`, and compares output to the target string in `crates/rtm-platform/src/tmux.rs:42-57`.
- `RuntimeFailure::TmuxPaneDead` maps to stable `ErrorCode::TmuxPaneDead` in `crates/rtm-daemon/src/error.rs:15-40` and `crates/rtm-daemon/src/error.rs:90-113`.

Important nuance: spawn already has a typed failure when a pane is missing before spawn. The degraded cases are mostly after a pane existed, a session was recorded, then user interrupts killed the shim or pane.

### Shim and shell resume behavior

- The shim asks the daemon for `LaunchSpec`, spawns the runtime child, sends `ShimReady`, waits for the runtime, sends `ShimExit`, then execs the captured shell resume command when present in `crates/rtm-cli/src/cli/shim.rs:33-68`.
- The runtime child is spawned by `std::process::Command` with the runtime binary and args in `crates/rtm-cli/src/cli/shim.rs:91-96`.
- The shim installs a SIGTERM handler only while waiting for the runtime, forwards SIGTERM to the child, then waits for the child in `crates/rtm-cli/src/cli/shim.rs:130-158`.
- There is no SIGINT handling in the shim.

This creates the sharp edge. When the TUI is in raw mode, `Ctrl+C` may be consumed by Claude or Codex as input. During shutdown, after the TUI exits or restores cooked terminal mode and before the shim has sent `ShimExit` and execed the shell resume, repeated `Ctrl+C` can become a terminal SIGINT to the shim process. With the default SIGINT disposition, the shim dies. Since the shim is the pane command created by `respawn-pane`, its death can close the tmux pane before shell resume.

### Status, capture, nudge, and log availability

- Status reads lifecycles and populates `log_availability` for each lifecycle in `crates/rtm-daemon/src/server.rs:444-492`.
- For tmux lifecycles, `populate_log_availability` reports `TmuxPaneSnapshot` when `is_alive` succeeds, otherwise `Unavailable { reason: PaneUnavailable }` in `crates/rtm-daemon/src/server.rs:479-486`.
- Capture returns `CaptureError::PaneUnavailable` when the lifecycle has a tmux pane but `is_alive` fails in `crates/rtm-daemon/src/server.rs:396-410`.
- Nudge returns `NudgeOutcome::Failed(TmuxPaneDead)` when `TmuxGateway::nudge` fails liveness in `crates/rtm-daemon/src/server.rs:360-390` and `crates/rtm-platform/src/tmux.rs:19-28`.
- The human status renderer prints lifecycle state and tmux pane, but not log availability, in `crates/rtm-core/src/cli_output.rs:88-118`; JSON status carries `log_availability` through the serialized lifecycle.

### Lost evidence

- If the exit watcher sees the shim pid is no longer alive before a `ShimExit` report, it records `LostEvidence::ShimDiedBeforeReport` in `crates/rtm-daemon/src/server.rs:552-568`.
- `Lifecycle::mark_lost` can mark a forking or running lifecycle lost in `crates/rtm-core/src/types.rs:454-462`.
- `LostEvidence` currently has `ShimDiedBeforeReport`, `PidNotAlive`, and `PidReuseDetected` in `crates/rtm-core/src/types.rs:490-503`.

So `ShimDiedBeforeReport` is accurate about daemon evidence, but it is not operationally specific. The more actionable fact is that the tmux pane may also be gone.

## 2. Root cause hypotheses ranked by likelihood

1. **Most likely: SIGINT hits the shim during the runtime exit to shell resume handoff.** The shim has SIGTERM handling but no SIGINT handling. The shell resume path exists specifically to leave the user in a shell after normal runtime exit, but a SIGINT in the small handoff window can kill the shim before it sends `ShimExit` or execs the shell. That would explain `ShimDiedBeforeReport` and pane closure.

2. **Likely: repeated interrupts race with terminal mode transitions in Claude and Codex.** While the TUI owns raw mode, `Ctrl+C` can be app input. During cleanup it may become a terminal signal. This explains why one or two interrupts can behave cleanly while a burst produces pane loss.

3. **Possible: process group semantics let SIGINT affect both runtime and shim.** The shim spawns the runtime without putting it in a separate process group. If the terminal sends SIGINT to the foreground process group, both processes can receive it. The absence of shim SIGINT handling makes this fragile.

4. **Possible but secondary: tmux pane closure is expected when the pane command exits.** Since `respawn-pane` makes `rtm __shim` the pane command, tmux will close or mark the pane dead when that command exits unless the shim execs the resume shell. Pane preservation therefore depends on the shim reaching `exec_shell_resume`.

5. **Less likely as the primary root cause: spawn preflight misses a dead pane.** `begin_spawn` validates target liveness before creating lifecycle state. A missing pane should already produce typed `tmux_pane_dead` on spawn. Preflight can be made clearer, but it is not the core pane loss cause.

## 3. Options analysis

### Preserve the pane

What it buys:

- Addresses the root cause instead of only improving diagnostics.
- Keeps user tmux layout intact.
- Avoids guessing how to recreate `SESSION:WINDOW.PANE` after indexes shift.
- Preserves the existing shell resume contract for tmux spawns.
- Keeps `sm delete agent` and runtime kill paths clean if scoped to user generated SIGINT, not SIGTERM.

Likely implementation shape:

- Install a SIGINT handler in the shim after spawning the runtime child, so the runtime starts with the normal/default SIGINT disposition but the shim no longer exits on subsequent terminal SIGINTs.
- Continue to report `ShimExit` once the runtime exits.
- Proceed to `exec_shell_resume` even if SIGINT was seen during the handoff.
- Ensure the resumed shell receives default SIGINT behavior after exec. POSIX resets caught signal handlers on exec, so a caught SIGINT handler is safer here than setting SIGINT to ignored.
- Add tests that use a real tmux pane and a fake runtime or controlled command to hit the post runtime exit/pre shell resume race deterministically.

What it breaks or risks:

- If the runtime is a simple cooked mode CLI rather than a raw mode TUI, terminal SIGINT will also hit the shim. A catching handler should avoid killing the shim while allowing the child to receive its own SIGINT.
- If implemented by ignoring SIGINT before child spawn, the child could inherit ignored SIGINT. That would be wrong. The handler should be installed after child spawn or the child should explicitly reset SIGINT before exec.
- Signal handling must stay small and async safe. The existing SIGTERM handler pattern already uses an atomic flag, so this can reuse the same discipline.

### Recreate the pane

What it buys:

- Gives a recovery path after pane loss has already happened.
- Could allow a subsequent spawn to the same target to succeed even if the original pane command died.

What it breaks or risks:

- Current target identity is positional. `SESSION:WINDOW.PANE` is not a stable tmux pane id. Recreating pane index `1` inside window `3` may be impossible, may require layout mutation, or may target a different user pane after indexes shift.
- If the entire session or window is gone, recreating it is a large side effect. Runtime Matters would become a tmux layout manager rather than a runtime supervisor.
- If another pane has taken the same address, recreation can conflict with occupancy semantics and user expectations.
- Deterministic recreation needs a stronger target contract: probably tmux `%pane_id` for stable references, plus explicit policy for window/session recreation. That is larger than ALP-2597's likely safe fix.

Verdict: do not ship automatic recreation as the first fix under the current address contract. Consider a later explicit recovery command or a target contract upgrade.

### Typed fail only

What it buys:

- Smallest product change.
- Spawn already has `tmux_pane_dead`; capture already has `pane_unavailable`; nudge already has `tmux_pane_dead`; status JSON already has `log_availability.unavailable.reason=pane_unavailable`.
- Can improve ambiguity by adding more specific lost evidence or status annotation.

What it breaks or risks:

- Does not meet the user expectation that repeated interrupts should not silently leave the managed tmux target unusable. It merely describes the failure after the pane is gone.
- Leaves shell resume fragile.
- Still leaves humans with `ShimDiedBeforeReport` as the main lifecycle state, which is accurate but not the operational repair instruction.

Verdict: necessary as a fallback, insufficient as the main solution.

### Hybrid: preserve first, typed fail when preservation cannot help

What it buys:

- Fixes the root cause for the common repeated interrupt race.
- Leaves explicit typed failure for externally killed panes, killed sessions, and stale positional targets.
- Avoids unsafe automatic tmux layout mutation.
- Matches the acceptance criteria: repeated interrupts should not silently make the pane unusable; if missing, APIs expose typed failure; subsequent spawn either succeeds when pane survived or fails clearly when it did not.

What it breaks or risks:

- Requires careful tests for both Claude and Codex launch paths without making integration tests flaky.
- May require one new protocol or diagnostic enum if the team wants status to distinguish `shim_died_before_report` caused by user SIGINT from other shim death cases.

Verdict: this is the path I would ship.

## 4. Recommendation

Ship a hybrid with **preserve as the primary fix** and **typed fail as the explicit fallback**.

The code level reason is straightforward: the pane is lost because the pane command is `rtm __shim`, and the only thing that keeps the pane useful after the runtime exits is the shim reaching `exec_shell_resume`. Current shim code handles SIGTERM but not SIGINT. Repeated `Ctrl+C` during TUI teardown can kill the shim during exactly the window where it needs to send `ShimExit` and exec the resume shell. The daemon then records the only evidence it has, `ShimDiedBeforeReport`, and later `log_availability` correctly reports `pane_unavailable` because the tmux target is gone.

I would not ship automatic pane recreation in the first pass. The address model is not stable enough. A tmux `%pane_id` based contract or an explicit layout ownership model would be required before Runtime Matters can safely recreate panes without surprising users.

Concrete behavior target:

- A user may press `Ctrl+C` repeatedly in a tmux backed Claude or Codex pane.
- The runtime may terminate.
- The shim should survive long enough to report `ShimExit` and exec the resume shell.
- Status should become `Exited(...)` rather than `Lost(ShimDiedBeforeReport)` for this path.
- `tmux_pane` should remain live and `log_availability` should remain `tmux_pane_snapshot` after the shell resume.
- If a pane is killed externally, status/capture/nudge/spawn should keep returning typed pane unavailable/dead outcomes.

## 5. Open questions and risks

- Should Runtime Matters explicitly support `%pane_id` targets in addition to `SESSION:WINDOW.PANE`? This would make later recreation safer and make liveness checks less vulnerable to index churn.
- Should `LostEvidence` grow a more operational variant such as `TmuxPaneUnavailable` only when the shim was tmux backed and the pane is gone? That would improve diagnostics, but it should not replace the preservation fix.
- Can the integration test use a fake runtime that exits after a marker and a deterministic interrupt window, rather than trying to drive real Claude and Codex TUIs? Acceptance needs Claude and Codex coverage, but the race itself needs a deterministic unit/integration harness.
- Does `exec_shell_resume` always reset signal behavior correctly on macOS and Linux for caught SIGINT? POSIX says caught handlers reset on exec, but this should be proved in the road test.
- Should human `rtm status` render log availability for tmux targets? JSON already does. Human output currently hides it, which may make field debugging harder.
- The issue caveat is important: after `just install-local`, restart `rtm daemon` before testing shim behavior to avoid daemon/shim version drift.

## 6. Selector compatible issue structure proposal

Master parent: **ALP-2597: Robust tmux pane survival after manual interrupts**

Direct child gate review issue: **Gate review: ALP-2597 execution readiness**

Execution parent: **Backlog**

Worker issues, high level only:

1. **Reproduce tmux interrupt pane loss for Claude and Codex**
   - Entry points: tmux spawn path, shim wait and shell resume path, existing tmux integration test helpers.
   - Acceptance: reproducible evidence or a deterministic surrogate test demonstrates the pane loss window; road test covers both Claude and Codex launchers.
   - Verification: repo native test command plus documented manual road test transcript.

2. **Preserve tmux pane through user SIGINT during shim handoff**
   - Entry points: shim runtime wait, signal handling, shell resume execution.
   - Acceptance: repeated user interrupts no longer kill the shim before lifecycle reporting and shell resume; existing SIGTERM and runtime kill behavior remains clean.
   - Verification: targeted tests plus `just check && just build && just test`.
   - Depends on issue 1.

3. **Keep pane unavailable failures typed and observable**
   - Entry points: validate target, spawn target validation, capture, nudge, status log availability, human status rendering if accepted.
   - Acceptance: externally missing panes produce stable typed responses; JSON status continues to expose pane unavailable; human diagnostics are clear enough for operators.
   - Verification: targeted tests plus snapshots where public output changes.
   - Can run after issue 1; can run in parallel with issue 2 if write scopes are separated.

4. **Regression road test for delete, kill, and repeated interrupts**
   - Entry points: CLI tests, tmux helper, manual road test docs.
   - Acceptance: `sm delete agent` behavior remains clean; runtime kill remains clean; repeated interrupt behavior is proved for Claude and Codex.
   - Verification: `just check && just build && just test` plus manual road test evidence.
   - Depends on issues 2 and 3.

Post execution review issue: **Post execution review: ALP-2597 tmux pane survival**

Suggested accepted gate body shape:

```text
Planning complete. Outcome: Ready for execution.
Authorized execution parent: `BACKLOG-ID`.
Execute: WORKER-1, WORKER-2, WORKER-3, WORKER-4, REVIEW-ID.
Required order: WORKER-1 before WORKER-2. WORKER-1 before WORKER-3. WORKER-2 and WORKER-3 before WORKER-4. WORKER-4 before REVIEW-ID.
```

## Evidence index

- fmm topology: 95 Rust files, 14,619 LOC, primary crates under `crates/`.
- `crates/rtm-platform/src/tmux.rs:30-57`, `201-222`: tmux `respawn-pane`, liveness checks, target args.
- `crates/rtm-daemon/src/handler.rs:100-135`: spawn RPC flow and ready wait.
- `crates/rtm-daemon/src/shim_socket.rs:25-36`: tmux shim launch.
- `crates/rtm-daemon/src/server.rs:160-224`: spawn target validation.
- `crates/rtm-cli/src/cli/shim.rs:33-68`, `130-158`: shim lifecycle reporting, shell resume, SIGTERM only handling.
- `crates/rtm-daemon/src/server.rs:396-410`, `444-492`: capture and log availability for dead panes.
- `crates/rtm-core/src/types.rs:490-503`: lost evidence variants.
- `crates/rtm-core/src/capture.rs:8-27`, `48-62`: log availability and capture error wire shapes.
- Linear ALP-2597 body fetched live on 2026-05-21.
