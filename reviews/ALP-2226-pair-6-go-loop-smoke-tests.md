# ALP-2226 Pair 6 Review: Gate-Aware Go Loop + Parity Smoke Tests

Reviewer: nancy-ALP-2212:helioy-tools:code-reviewer:4:4.6
Date: 2026-05-02
Scope: ALP-2247 (wire gate-aware go loop) + ALP-2248 (parity smoke tests)
Worktree: `/Users/alphab/Dev/LLM/DEV/TMP/nancy-worktrees/nancy-ALP-2212`

## Summary

The Rust go loop and parity tests land most of the contract. Selector is recomputed every iteration, sentinels are read at iteration boundaries, ISSUES.md is regenerated, prompts are written under the Bash-compatible naming, and the bridge contract from ALP-2230 is exercised end-to-end against a fake binary plus real `nancy-live setup`. The deleted-template tripwire is enforced in both the Rust prompt tests and the Python review-hook tests, so the iter-34 leak cannot recur structurally — there is no review hook in the Rust loop, and the dead Bash callers are gone.

Two findings warrant blocking attention:

1. `unread_human_guidance` is hardcoded to `false` in `final_completion_inputs`, so the gate never honors ALP-2215's "unread direct human guidance blocks final completion" rule.
2. `supervisor::run_agent`'s `AgentRunResult` is dropped on the floor — worker exit codes and stream `is_error` are invisible to the loop, with no log line and no skip of post-iteration steps. Bash parity at minimum requires logging `Iteration #N exited with code X`.

A handful of MEDIUM divergences and quality issues round out the list. Tests cover the happy path well but miss `unread_human_guidance`, worker failure handling, and default-binary-path resolution for the bridge.

## Per-Issue Findings

### ALP-2247 — Wire Rust gate-aware go loop

#### F1. `unread_human_guidance` hardcoded false (HIGH)

`crates/nancy-live/src/go.rs:437-445`

```rust
fn final_completion_inputs(decision: &SelectorDecision, status_graph: &IssueGraph) -> FinalCompletionInputs {
    FinalCompletionInputs {
        post_execution_review_accepted: final_review_accepted(decision, status_graph),
        unread_human_guidance: false,
    }
}
```

ALP-2215 explicitly states "Unread direct human guidance blocks final completion. The loop should drain or surface unread bus messages before writing `COMPLETE`." `gate.rs::FinalCompletionInputs::complete_write_block_reason` does honor the field, but the loop wires it to a constant `false`. As a result, `task::write_final_complete` will write `COMPLETE` regardless of any pending operator directive in `comms/directives/`. This is a correctness gap, not a stub: the existence of the field and the gate-side block reason imply the loop should populate it. At minimum the loop should read `comms/directives/` for unread entries and set the flag.

#### F2. Worker exit/stream errors silently dropped (HIGH)

`crates/nancy-live/src/go.rs:332-377`

```rust
supervisor::run_agent(&AgentInvocation { ... })?;
Ok(())
```

`supervisor::run_agent` returns `AgentRunResult { success, exit_code, stream, ... }`. The `?` propagates `SupervisorError` (spawn/wait/IO), but the run result itself — including `success: bool` (combining process exit code and parsed `is_error`) — is discarded. A worker that exits nonzero or emits `result.is_error=true` in its JSON stream is treated identically to success. The loop:

- does not log iteration failure (Bash logs `Iteration #N exited with code X` at `src/cmd/start.sh:561`),
- does not gate post-iteration logic on success (Bash skips post-worker review and completion checks on failure),
- and does not record the parsed token/tool/session evidence anywhere.

At minimum the loop should log the exit code and `is_error` flag, and treat the failure as Bash does (continue the loop, but skip work that depends on success). Capturing token/session evidence into the task ledger would also remove a clear gap with the supervisor's own work.

#### F3. Planning mode skips the worker stage (MEDIUM)

`crates/nancy-live/src/go.rs:385-408`

```rust
fn agent_route(mode: GateMode, config: &NancyConfig) -> AgentRoute<'_> {
    let role = match mode {
        GateMode::Planning | GateMode::AgentIssueReview | GateMode::PostExecutionReview => Reviewer,
        GateMode::Execution | GateMode::CorrectiveResolution | GateMode::NeedsHumanDirection => Worker,
    };
    ...
}

fn prompt_mode(mode: GateMode) -> PromptMode {
    match mode {
        GateMode::Planning | GateMode::AgentIssueReview => PromptMode::AgentIssueReview,
        ...
    }
}
```

Bash flow for `selected_mode == planning`: worker runs with `planning.md.template`, then `_start_should_run_reviewer_after_worker` triggers a second reviewer pass with `agent_issue_review.md.template` (`src/cmd/start.sh:546-552`). Two agents per iteration. The Rust loop collapses this to a single reviewer pass with `agent_issue_review`, never invoking a planning-template worker. The test `go_loop_runs_planning_followup_as_agent_issue_review` (`tests/go.rs:417-460`) confirms this is intentional, but the divergence is significant enough to warrant a Linear decision rather than an implicit collapse: Bash's two-stage flow exists for a reason, and `templates/modes/planning.md.template` is unreachable from the Rust loop while still being shipped. ALP-2247 does not explicitly authorize the collapse.

#### F4. `write_final_complete` block reasons silently discarded (MEDIUM)

`crates/nancy-live/src/go.rs:172-182`

```rust
if derived_final_complete(&snapshot, final_inputs) {
    if task::write_final_complete(...)?.written() {
        return Ok(loop_result(GoLoopStatus::FinalComplete, iterations));
    }
}
```

`task::write_final_complete` returns `CompleteWriteResult::Written` or `Blocked(reason)`. When blocked (review not accepted, unread human guidance, pause, stop), the reason is dropped on the floor. The loop has no record of why `COMPLETE` was not written, and the runtime log already produced earlier in the iteration does not capture this. ALP-2247 AC: "top-level error handling produces actionable messages." This should at minimum append a `complete_write_blocked={reason}` line to `runtime.log`.

#### F5. Bootstrap fetches issue/status graphs that the loop discards (MEDIUM)

`crates/nancy-live/src/go.rs:121-158`

```rust
let initial_issue_graph = input.issue_source.fetch_sub_issues(&input.parent.id)?;
let initial_status_graph = input.issue_source.fetch_sub_issue_statuses(&input.parent.id)?;
let bootstrap = bootstrap_go(GoBootstrapInput { ..., issue_graph: &initial_issue_graph, status_graph: &initial_status_graph })?;
let mut iterations = 0;

loop {
    let sentinels = task::read_task_sentinels(...)?;
    ...
    let issue_graph = input.issue_source.fetch_sub_issues(&input.parent.id)?;
    let status_graph = input.issue_source.fetch_sub_issue_statuses(&input.parent.id)?;
    let decision = selector::evaluate_with_status(&issue_graph, &status_graph);
    ...
}
```

The bootstrap fetch is used to write the initial `ISSUES.md` and prepare the worktree. The first loop iteration immediately fetches both graphs again. Two redundant Linear round-trips on every `nancy go`. Either reuse the bootstrap fetch for iteration 1, or move the bootstrap-only side effects (worktree setup, task tree) ahead of the fetch and let the loop own all selector input.

#### F6. STOP cleanup failure misclassified as runtime-log error (LOW)

`crates/nancy-live/src/go.rs:522-535`

```rust
fn clear_stop(sentinels: &task::TaskSentinels) -> Result<(), GoError> {
    if let Some(stop) = &sentinels.stop {
        match std::fs::remove_file(&stop.path) {
            ...
            Err(source) => Err(GoError::RuntimeLog { path: stop.path.clone(), source }),
        }
    }
    ...
}
```

A real `EACCES` removing the STOP sentinel surfaces as `Could not write runtime log <STOP path>: ...` which is actively misleading. Use a dedicated variant or `GoError::Task(...)`.

#### F7. Iteration counter restarts at 0 on every `nancy go` (LOW)

`crates/nancy-live/src/go.rs:136`, vs `src/cmd/start.sh:472`

```rust
let mut iterations = 0;
```

Bash uses `task::count_sessions "$task"` to seed the iteration count from existing session files, so resuming a task continues iteration numbering. The Rust loop restarts at 0, so a resumed task would overwrite or collide with prior `session_*_iter1.md` (the timestamp prefix mitigates filename collision but the iteration label loses meaning). Minor.

#### F8. Per-iteration directive archive missing (LOW)

`crates/nancy-live/src/go.rs:332-377`, vs `src/cmd/start.sh:503-505,545,588-589`

Bash calls `comms::archive_all "$task" "worker"` and `"orchestrator"` before each agent run, before reviewer follow-up, and at end-of-iteration. The Rust loop never archives. Not in ALP-2247 ACs but is real Bash hygiene that prevents the next worker from inheriting stale operator directives. Worth a follow-up.

#### F9. `AgentRunResult` evidence (tokens, tools, session) discarded (LOW)

`crates/nancy-live/src/go.rs:364-375`

`supervisor::run_agent` parses stream evidence (token usage, tools used, session id, cost, num_turns) and reports `session_evidence` (path + exists). All of it is thrown away by the loop. ALP-2247 doesn't explicitly require persistence, but the supervisor goes to non-trivial effort to produce this evidence. If it's not persisted now, a follow-up should either remove the parsing or wire it into a per-iteration log.

#### F10. Duplicate pause/stop handling (LOW)

`crates/nancy-live/src/go.rs:139-146` vs `163-170`

The loop reads sentinels and branches on pause/stop, then derives a `GateSnapshot` whose `LoopControl` produces the same branches via `snapshot.control`. Both produce identical results — the redundancy is harmless but adds reading cost. Pick one.

#### F11. Dead `agent_route` branches (COSMETIC)

`crates/nancy-live/src/go.rs:386-398, 400-408`

`agent_route(GateMode::NeedsHumanDirection) → Worker` is unreachable because the loop returns `NeedsHumanDirection` before invoking `run_selected_agent`. Similarly `prompt_mode(GateMode::Planning) → AgentIssueReview` is the only path through which `Planning` reaches a renderer; `PromptMode::Planning` is therefore dead from the loop's perspective (still reachable via `PromptMode::ALL` in tests). Either prune the dead branches or document why they exist.

### ALP-2248 — Rust live path parity smoke tests

#### F12. No test for `unread_human_guidance` blocking final completion (MEDIUM)

`crates/nancy-live/tests/go.rs`

`go_loop_derives_code_complete_from_linear_and_done_review` exercises the success path. Nothing covers the "unread human guidance blocks COMPLETE" rule from ALP-2215, which compounds with F1: not only is the field hardcoded false, no test would catch a change. Add a test that asserts `COMPLETE` is not written when an unread directive sits in `comms/directives/`.

#### F13. No test for worker exit-code or stream-error handling (MEDIUM)

`crates/nancy-live/tests/go.rs`

The smoke tests use bash workers that always exit 0 (or exit 88/89 only when never invoked). No test asserts the loop's behavior when the worker exits nonzero or emits a stream-level `is_error`. Compounds with F2.

#### F14. Bridge default binary path is not tested (LOW)

`tests/test_live_bridge.py`

All bridge dispatch tests set `NANCY_RUST_LIVE_BIN` to override the binary location. The default path (`$NANCY_FRAMEWORK_ROOT/target/release/nancy-live`) from `src/live/bridge.sh:21` is not exercised. A regression that breaks the default lookup would not surface. Add a test that sets only `NANCY_RUST_LIVE_ENABLED` and stages a binary at the default path.

## Cross-Issue Notes

**Iter-34 leak prevention**: structurally cannot recur. The Rust loop has no separate review hook — `run_selected_agent` is the single entry point per iteration, routed by `agent_route(snapshot.mode, ...)`. Bash dead callers are confirmed gone (no `_start_run_review_agent`, `_start_maybe_run_review_agent`, `_start_should_run_review_agent_for_mode`, or `legacy_local_hygiene` references in `src/cmd/start.sh`). Deleted-template tripwires are enforced by `crates/nancy-live/tests/prompt.rs:121-123` and `tests/test_review_hook_modes.py:13-31`.

**Bridge contract (ALP-2230)**: fully covered by `tests/test_live_bridge.py`:
- default-off: `test_setup_uses_bash_by_default_and_preserves_agent_config`, `test_go_default_path_runs_setup_then_rejects_invalid_task_name`
- supported commands only: `test_opt_in_rust_live_bridge_dispatches_only_setup_and_go` (asserts `status` is not bridged)
- `NANCY_LIVE_BRIDGE=rust` exported on dispatch: same test
- missing binary error: `test_opt_in_rust_live_bridge_exits_when_binary_missing` matches the exact stderr text
- gap: default binary path resolution (F14)

**Setup parity (ALP-2240/2248)**: `crates/nancy-live/tests/setup_parity.rs` runs `./nancy setup` and `nancy-live setup` against fake-tooled environments and asserts `read_config(rust) == read_config(bash)`. Strong parity test.

**Selector parity (ALP-2230)**: not in this pair's scope, but the loop reuses `selector::evaluate_with_status`, recomputed every iteration, which matches Bash's `_start_create_issues_file` recompute pattern.

**Sentinel semantics (ALP-2215)**: `gate.rs` correctly distinguishes `CodeComplete` from `FinalComplete`, treats `CODE_COMPLETE` as non-exiting evidence, blocks `COMPLETE` writes under pause/stop, and surfaces stale `CODE_COMPLETE` warnings. F1 is the only sentinel-semantics gap.

**Top-level error handling**: `GoError` variants are well-decomposed and map to actionable messages via `Display` and `Error::source`. `main.rs` exits 2 on any error, printing the chain. F4 and F2 are the open issues.

## Severity Index

| ID  | Severity | Title                                                                  | File:line |
| --- | -------- | ---------------------------------------------------------------------- | --------- |
| F1  | HIGH     | `unread_human_guidance` hardcoded false                                | `crates/nancy-live/src/go.rs:437-445` |
| F2  | HIGH     | Worker exit/stream errors silently dropped                             | `crates/nancy-live/src/go.rs:332-377` |
| F3  | MEDIUM   | Planning mode skips worker stage; routes directly to reviewer          | `crates/nancy-live/src/go.rs:385-408` |
| F4  | MEDIUM   | `write_final_complete` block reasons silently discarded                | `crates/nancy-live/src/go.rs:172-182` |
| F5  | MEDIUM   | Bootstrap fetches issue/status graphs that the loop discards           | `crates/nancy-live/src/go.rs:121-158` |
| F12 | MEDIUM   | No test for `unread_human_guidance` blocking final completion          | `crates/nancy-live/tests/go.rs`       |
| F13 | MEDIUM   | No test for worker exit-code or stream-error handling                  | `crates/nancy-live/tests/go.rs`       |
| F6  | LOW      | STOP cleanup failure misclassified as runtime-log error                | `crates/nancy-live/src/go.rs:522-535` |
| F7  | LOW      | Iteration counter restarts at 0 on every `nancy go`                    | `crates/nancy-live/src/go.rs:136`     |
| F8  | LOW      | Per-iteration directive archive missing                                | `crates/nancy-live/src/go.rs:332-377` |
| F9  | LOW      | `AgentRunResult` evidence (tokens, tools, session) discarded           | `crates/nancy-live/src/go.rs:364-375` |
| F10 | LOW      | Duplicate pause/stop handling                                          | `crates/nancy-live/src/go.rs:139-146,163-170` |
| F14 | LOW      | Bridge default binary path is not tested                               | `tests/test_live_bridge.py`           |
| F11 | COSMETIC | Dead `agent_route` and `prompt_mode` branches                          | `crates/nancy-live/src/go.rs:386-408` |
