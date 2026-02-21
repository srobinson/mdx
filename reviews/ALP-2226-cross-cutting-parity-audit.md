# ALP-2226 Cross-cutting Parity & Silent-failure Audit

Reviewer agent: nancy-ALP-2212:helioy-tools:engineering-code-reviewer:4:4.7
Worktree: /Users/alphab/Dev/LLM/DEV/TMP/nancy-worktrees/nancy-ALP-2212
Scope: All of `crates/nancy-live/src/*.rs` and `crates/nancy-live/tests/*.rs` produced by ALP-2237 → ALP-2248.
Lens: cross-cutting only — silent failures, parity gaps vs ALP-2230 oracle, missing assertions, unhandled paths, DRY violations, invariant bleed. Per-issue acceptance verification is owned by the six pair reviewers.

## Summary

Verdict: contested. Twelve issues shipped a coherent crate skeleton with strong type design and comprehensive selector unit tests. The crate compiles, the bridge surface is opt-in, and no source path recreates the legacy review hook leak diagnosed in ALP-2230. However, the live `go` loop in `crates/nancy-live/src/go.rs` violates the gate state contract from ALP-2215 / ALP-2232 in three places, the prompt dispatcher silently collapses one of the six surviving mode templates, and several module boundaries swallow errors that the operator needs to see. Twenty findings below; four critical, six high, eight medium, plus test-coverage gaps.

The selector and gate primitives in isolation match the oracle. The integration layer in `go.rs` is where parity slips, and the existing tests in `tests/go.rs` lock several of those slips in as expected behavior.

The iter-34 legacy review hook leak does NOT recur in Rust. There is no `_start_run_review_agent` analogue, no `templates/REVIEW.md.template` reference, and the deleted templates from ALP-2230 are absent from `templates/` and from `crates/nancy-live`. Confirmed at `crates/nancy-live/tests/prompt.rs:121` and by directory listing.

## Silent Failures

### SF-1 (CRITICAL) — Agent run failures silently ignored by the live loop
`crates/nancy-live/src/supervisor.rs:71-106` returns `AgentRunResult { success: false, ... }` when the spawned worker or reviewer CLI exits non-zero or emits a stream `result` with `is_error: true`. `crates/nancy-live/src/go.rs:364-376` calls `supervisor::run_agent(...)?;` and discards the returned `AgentRunResult` — only `SupervisorError` aborts the loop. A failed agent leaves `success=false` on the floor; the iteration counter advances and the loop selects the next issue as if the agent had succeeded.
Affects: ALP-2246, ALP-2247.

### SF-2 (CRITICAL) — `unread_human_guidance` hardcoded false
`crates/nancy-live/src/go.rs:441-445` constructs `FinalCompletionInputs { unread_human_guidance: false }` unconditionally. ALP-2232 explicitly states: "Unread direct human guidance before final completion: block COMPLETE." `gate.rs:165-181` and `task.rs:106-120` both honor the flag, but the field is never populated, so the loop will write COMPLETE while the bus inbox still has unread directives.
Affects: ALP-2215, ALP-2232, ALP-2247.

### SF-3 (HIGH) — `task::write_initial_prompt` silently writes empty PROMPT.md when template missing
`crates/nancy-live/src/task.rs:212-221` matches `io::ErrorKind::NotFound` for `templates/PROMPT.md.template` and falls through to write an empty `PROMPT.md` to the task directory. ALP-2230: "The only live shell prompt is `templates/PROMPT.md.template`." Missing PROMPT template should be a hard error symmetric with `prompt::render_prompt` (`prompt.rs:185-201`), which does error in the same condition. Two divergent reads of the same template file: one fails closed, one fails open.
Affects: ALP-2230, ALP-2243, ALP-2245.

### SF-4 (MEDIUM) — `git_root` discards underlying I/O cause
`crates/nancy-live/src/workspace.rs:127-138` uses `.map_err(|_| WorkspaceError::NotGitWorktree { cwd })`. `git` not installed, PATH issues, sandbox denial, and "not a git worktree" all surface as `NotGitWorktree`. The operator sees a misleading error.
Affects: ALP-2239.

### SF-5 (MEDIUM) — `add_worktree` fallback swallows the first error
`crates/nancy-live/src/worktree.rs:110-116`: first `git worktree add ... -b <branch>` fails → unconditional retry without `-b`. The first error is dropped via `Err(_)`. Permission, disk-space, missing-fetch, and hook failures cascade into a misleading "branch already exists" retry whose own error wins. The Bash oracle catches the same race only for the "branch exists" case.
Affects: ALP-2245.

### SF-6 (MEDIUM) — Stream parse errors do not flag the agent run as failed
`crates/nancy-live/src/supervisor.rs:108-117` collects malformed stream lines into `evidence.parse_errors`, but `is_error` (line 408-411) is set only by an explicit `result` event. A worker that emits no recognizable stream returns `is_error=false`; combined with a zero exit code, `success=true`. `tests/supervisor.rs:153-175` asserts the `parse_errors` are recorded but does NOT assert that downstream callers treat malformed streams as failures.
Affects: ALP-2246.

### SF-7 (MEDIUM) — `ClaudeHooksGuard::drop` discards restoration errors
`crates/nancy-live/src/supervisor.rs:344-351` uses `let _ = std::fs::write(...)`, `let _ = std::fs::remove_file(...)`, `let _ = std::fs::remove_dir(...)`. If restoration fails, the next agent invocation finds stale hook settings or a leftover `.claude/` directory in the worktree. No log, no propagation. `Drop` cannot return an error, but it can at least eprintln.
Affects: ALP-2246.

### SF-8 (LOW) — `TaskSentinels::modified_at` silently drops metadata errors
`crates/nancy-live/src/task.rs:241-243` uses `metadata().ok().and_then(|m| m.modified().ok())`. Metadata read failure is indistinguishable from "no modification time". Any caller using `modified_at` for ordering or tie-breaking is silently denied evidence.
Affects: ALP-2244.

### SF-9 (LOW) — `setup::ShellCommandLookup::exists` treats sh failures as missing dep
`crates/nancy-live/src/setup.rs:166-172` runs `sh -c 'command -v ...'` and `.unwrap_or(false)`. If `sh` is missing or the spawn itself fails (sandbox, PATH), the dep is silently reported absent.
Affects: ALP-2240.

## Parity Gaps

### PG-1 (CRITICAL) — Planning mode never loads `templates/modes/planning.md.template`
`crates/nancy-live/src/go.rs:400-408`:
```
fn prompt_mode(mode: GateMode) -> PromptMode {
    match mode {
        GateMode::Planning | GateMode::AgentIssueReview => PromptMode::AgentIssueReview,
        ...
    }
}
```
ALP-2230 names six surviving mode templates: `planning`, `agent_issue_review`, `execution`, `corrective_resolution`, `post_execution_review`, `needs_human_direction`. The selector emits `Planning` (selector.rs:280, line 288 default branch). The planning template file exists at `templates/modes/planning.md.template`. But the dispatcher above collapses `GateMode::Planning` into `AgentIssueReview`, so `planning.md.template` is unreachable from the live loop. `prompt::PromptMode::Planning` is exercised only by `tests/prompt.rs:54` (`PromptMode::ALL`), never by `go.rs::run_selected_agent`. `tests/go.rs:417-460` (`go_loop_runs_planning_followup_as_agent_issue_review`) asserts `MODE=agent_issue_review` for a Todo gate review, locking this collapse in as expected behavior.
Affects: ALP-2230, ALP-2243, ALP-2247.

### PG-2 (CRITICAL) — Loop writes COMPLETE without traversing CodeComplete
`crates/nancy-live/src/go.rs:171-182`, `463-479`:
```
fn derived_code_complete(snapshot: &GateSnapshot) -> bool {
    let selected = snapshot.selector.selected_issue.as_ref();
    let live_mode = matches!(snapshot.selector.selected_mode,
        SelectorMode::Execution | SelectorMode::PostExecutionReview);
    live_mode && snapshot.selector.blocked_candidates.is_empty()
        && selected.is_none_or(|issue| issue.review)
}
fn derived_final_complete(snapshot, final_inputs) -> bool {
    derived_code_complete(snapshot) && final_inputs.post_execution_review_accepted
}
```
ALP-2215 and ALP-2232 require: `Execution` → `CodeComplete` (gated by the `CODE_COMPLETE` sentinel written by the worker) → `PostExecutionReview` → `FinalComplete`. `gate.rs:252-259` correctly requires the `CODE_COMPLETE` sentinel to derive `GateState::CodeComplete`. But `go.rs::derived_code_complete` does not consult sentinels and triggers `task::write_final_complete` whenever the selector returns Execution/PostExecutionReview with no blocked candidates and no selected issue (or a selected review issue). The Rust loop will write the final `COMPLETE` marker without the worker ever having written `CODE_COMPLETE`. This contradicts the explicit ALP-2215 invariant: "`CODE_COMPLETE`: ... It must not make the live loop exit by itself" — but its absence must also not be optional. `tests/go.rs:530-553` (`go_loop_derives_code_complete_from_linear_and_done_review`) asserts COMPLETE is written without any CODE_COMPLETE sentinel, locking the violation in.
Affects: ALP-2215, ALP-2232, ALP-2244, ALP-2247.

### PG-3 (HIGH) — `final_review_accepted` excludes `Duplicate` and ignores execution issues
`crates/nancy-live/src/go.rs:447-461`:
```
!reviews.is_empty() &&
reviews.iter().all(|issue| issue.state.name == "Done" || issue.state.name == "Canceled")
```
Two parity issues:
1. ALP-2230 says `Canceled` and `Duplicate` blockers are always treated as released. A review issue marked `Duplicate` should count as accepted; this filter excludes it.
2. The check filters only review issues; it does not verify that authorized execution issues have all reached `Worker Done`/`Done`/`Canceled`/`Duplicate`. The loop may write `COMPLETE` while authorized execution work is still open, as long as the review issues happen to be Done.
Affects: ALP-2215, ALP-2230, ALP-2247.

### PG-4 (HIGH) — `Planning` routed to reviewer config
`crates/nancy-live/src/go.rs:386-398` maps `GateMode::Planning | GateMode::AgentIssueReview | GateMode::PostExecutionReview => AgentRole::Reviewer`. ALP-2247 authorizes routing only `agent_issue_review` and `post_execution_review` through reviewer config. Planning iterations should run on the worker config, matching Bash. With this routing, planning prompts execute under the reviewer CLI/model — possibly a smaller or differently configured model than intended.
Affects: ALP-2247.

### PG-5 (HIGH) — `In Progress` always selectable
`crates/nancy-live/src/selector.rs:618-620`:
```
fn is_open_state(issue: &EnrichedIssue<'_>) -> bool {
    matches!(issue.node.state.name.as_str(), "Todo" | "In Progress")
}
```
ALP-2217: "`Todo` is selectable. `In Progress` is selectable only for the same active worker/session recovery path." The Rust selector has no recovery-path check; In Progress is unconditionally selectable. A run could pick up a different agent's In Progress issue.
Affects: ALP-2217, ALP-2230, ALP-2242.

### PG-6 (MEDIUM) — Accepted gate hidden whenever open planning issues exist
`crates/nancy-live/src/selector.rs:126-130`:
```
let accepted_gate_status = if open_planning.is_empty() && open_gate_review.is_none() {
    raw_accepted_gate_status
} else {
    None
};
```
If a Phase 2 planning sibling is `Todo` and the gate review for the active phase is already `Worker Done`, the accepted-gate text is suppressed. Mode falls back to Planning even though execution authorization is in place. The Bash selector contract in ALP-2230 does not condition gate parsing on planning siblings being closed.
Affects: ALP-2230, ALP-2242.

### PG-7 (MEDIUM) — Gate review detection by title heuristic
`crates/nancy-live/src/selector.rs:630-633`:
```
fn is_gate_review(issue: &IssueNode) -> bool {
    let title = issue.title.to_ascii_lowercase();
    title.contains("gate review") || title.contains("execution readiness")
}
```
The Bash selector identifies gate reviews structurally (description outcome line plus parent type). Title-substring matching is brittle: gate reviews titled "Phase 2 review checkpoint" are missed; unrelated planning issues whose title contains "gate review" are mis-classified.
Affects: ALP-2230, ALP-2242.

### PG-8 (MEDIUM) — `latest_accepted_gate` ambiguity
`crates/nancy-live/src/selector.rs:463-470` sorts accepted gate reviews by `sub_issue_sort_order` desc and picks the head. With two `Worker Done` gate reviews and missing sort order, the choice is arbitrary (`f64::NEG_INFINITY` ties). The decision is not surfaced as evidence.
Affects: ALP-2230, ALP-2242.

## Missing Assertions

### MA-1 (HIGH) — Tests do not exercise SF-1 / PG-2 / SF-2
- `tests/go.rs:359-414` (`live_path_smoke_renders_prompt_and_reaches_supervisor_boundary`): no assertion that worker exit code is honored. Replacing the worker script with `exit 1` would still pass.
- `tests/go.rs:530-553` does the opposite of what ALP-2215 requires — it asserts COMPLETE is written without any `CODE_COMPLETE` sentinel. Either ALP-2215 is being ignored or the test should be revised once SF-2 / PG-2 are fixed.
- No test exercises `unread_human_guidance: true` blocking COMPLETE.

### MA-2 (HIGH) — `task::write_final_complete` STOP path untested
`crates/nancy-live/src/gate.rs:170-181` enumerates four block reasons (`FinalReviewNotAccepted`, `UnreadHumanGuidance`, `PauseRequested`, `StopRequested`). `tests/task.rs` covers `FinalReviewNotAccepted` (line 100-116) and `PauseRequested` (line 86-98). Neither `StopRequested` nor `UnreadHumanGuidance` has a test. STOP cleanup at `go.rs:522-535` returns success on `NotFound` but assertion absent in tests.

### MA-3 (MEDIUM) — Deleted-template tripwire only checks REVIEW.md.template
`tests/prompt.rs:121` asserts only `templates/REVIEW.md.template` does not exist. ALP-2230 names three deleted templates: `REVIEW.md.template`, `PROMPT.baseline.md.template`, `PROMPT.sidecar-first.md.template`. The other two have no tripwire test.

### MA-4 (MEDIUM) — Bridge contract not exercised crate-side
ALP-2248 requires bridge smoke covering `NANCY_RUST_LIVE_ENABLED`, `NANCY_RUST_LIVE_BIN`, missing-binary stderr text, and `NANCY_LIVE_BRIDGE=rust` on dispatch. `tests/setup_parity.rs` covers Bash-vs-Rust setup config-shape parity but not the bridge dispatch behaviors. Bash `tests/test_live_bridge.py` may cover the dispatch contract, but the crate has no analogue and no end-to-end bridge test.

### MA-5 (MEDIUM) — Selector edge cases untested
- Authorized parent != "Backlog" — `unauthorized_backlog_candidates` filters `parent_title == "Backlog"`. Untested.
- Multiple accepted gate reviews — tie-breaking path (PG-8) untested.
- `Duplicate` blocker in `PostExecutionReview` mode — tested only for `Execution` (`canceled_or_duplicate_blocker_does_not_block_selection`, `selector.rs:221-247`).
- Gate accepted, all execution issues complete, no review issues at all — `final_review_accepted` returns false (`!reviews.is_empty()`), loop returns `NoEligibleIssue` perpetually. No test, and no transition path defined.

### MA-6 (MEDIUM) — Supervisor success/failure semantics untested
`tests/supervisor.rs:153-175` asserts `parse_errors` are recorded but never that a malformed stream causes `success=false` or that callers act on it. There is no test for an exit-code-1 worker producing `success=false` and the loop reacting.

## Unhandled Paths

### UP-1 (HIGH) — Edge transition: gate accepted, execution complete, no review work
With `has_authorized_ids=true`, `execution_open.is_empty()`, `corrective_open.is_empty()`, `review_open.is_empty()`, `selector.rs:269-290 choose_mode` returns `Execution`. The pool is empty (`execution_open.is_empty()`). `selected_issue=None`. `derived_final_complete` returns false because `final_review_accepted` requires `!reviews.is_empty()`. `gate.rs::gate_state` returns `Execution { selected_issue: None, ... }` (not `CodeComplete` unless sentinel exists). `go.rs::run_go_loop:190-192` returns `NoEligibleIssue` indefinitely. ALP-2232 has no rule for an authorized set with zero post-execution-review issues, so the loop becomes terminal-but-not-final. Either ALP-2232 needs a transition for "no review work required" or the loop needs to recognize and surface the case.

### UP-2 (MEDIUM) — `Snapshot.mode` and `Snapshot.gate` can disagree
`crates/nancy-live/src/gate.rs:132-145`: when gate is computed (e.g., `CodeComplete`), `mode` is set from the original `selector.selected_mode` (e.g., `Execution`). The snapshot exposes both fields; `go.rs:345 prompt_mode(snapshot.mode)` uses `mode` for the prompt template, not `gate`. Today this does not break because `CodeComplete` always pairs with `selected_issue=None` (gate.rs:252-258), and `run_go_loop` returns `NoEligibleIssue` before launching an agent. But future code that takes any action based on `snapshot.mode` while `snapshot.gate` is `CodeComplete` will use the wrong template.

### UP-3 (LOW) — `agent_route` defines a `NeedsHumanDirection` branch that the loop short-circuits
`crates/nancy-live/src/go.rs:386-398` includes `GateMode::NeedsHumanDirection => AgentRole::Worker`. `run_go_loop:186-188` returns before reaching `run_selected_agent` whenever `gate==NeedsHumanDirection`. The branch is dead; if the early return is removed, the loop will spin up a worker for NHD with the current routing. Defensive programming is fine, but a comment would prevent regressions.

## DRY Violations

### DRY-1 — Stale CODE_COMPLETE warning emitted from two divergent conditions
`crates/nancy-live/src/gate.rs:261-267` emits `GateWarning::StaleCodeComplete` when `CODE_COMPLETE+Execution+selected_issue.is_some`. `crates/nancy-live/src/go.rs:488-491` emits the string `"warning=stale_code_complete"` when `CODE_COMPLETE+blocked_candidates.is_empty()=false`. Same warning vocabulary, two different signals. Operators reading runtime.log cannot tell which of the two stale conditions tripped.

### DRY-2 — `agent_route` and `prompt_mode` are tightly coupled but separately defined
`crates/nancy-live/src/go.rs:386-398` (mode → role) and `:400-408` (mode → prompt template) carry parallel mappings. A future mode added to `GateMode` requires synchronized edits to both. A single `mode_dispatch(GateMode) -> (AgentRole, PromptMode)` closure or struct would prevent drift.

### DRY-3 — GraphQL query inclusion uses brittle relative paths
`crates/nancy-live/src/linear.rs:9-12`:
```
const GET_ISSUE_QUERY: &str = include_str!("../../../src/gql/q/get_issue.gql");
```
Three-level relative traversal from `crates/nancy-live/src/`. If the crate moves, every query path breaks silently at compile time. A workspace-relative env (e.g., `CARGO_WORKSPACE_DIR` or a build script) would be more robust.

### DRY-4 — Selector `is_selectable` collapses to `is_open_state`
`crates/nancy-live/src/selector.rs:614-620`. `is_selectable` is a one-line wrapper. ALP-2217 specifies different selectability rules per mode (especially In Progress as recovery-only). The wrapper hides that the selector currently treats all modes identically.

### DRY-5 — Sentinel filenames duplicated as private constants
`crates/nancy-live/src/task.rs:9-13` defines `CODE_COMPLETE`, `COMPLETE`, `STOP`, `PAUSE`, `WORKER_COMPLETED` as private constants. Other modules access via the `TaskSentinels` struct, so this is fine today, but exporting these would let `go.rs::clear_stop` and `go.rs::log_runtime_evidence` use shared identifiers instead of stringly-typed warning labels.

## Invariant Bleed

### IB-1 (CRITICAL) — Two sources of truth for "code complete"
ALP-2215 / ALP-2232 invariant: `CODE_COMPLETE` is a sentinel file written by the worker; `GateState::CodeComplete` is derived only in its presence; `FinalComplete` is reachable only after `PostExecutionReview` consensus.
- `gate.rs:252-258` honors the sentinel-presence requirement.
- `go.rs::derived_code_complete:463-472` honors a different rule: selector mode + no blockers + no/review-only selected issue. No sentinel check.
- `go.rs::derived_final_complete:474-479` then writes `COMPLETE` based on `derived_code_complete`, bypassing `gate.rs`'s view.
The loop never consumes `gate.rs::GateState::CodeComplete`. It is dead state. The two definitions of "code complete" can diverge without the type system noticing.

### IB-2 (HIGH) — Mode owned by selector; gate owned by gate module; dispatcher uses mode only
`crates/nancy-live/src/gate.rs:117-145 GateSnapshot::derive` returns both `gate` and `mode`. The dispatcher in `go.rs::run_selected_agent:332-377` uses `snapshot.mode` for routing and template selection. `snapshot.gate` is consumed only by `should_exit` and the `NeedsHumanDirection` early return. The richer gate state machine in ALP-2232 (CodeComplete, FinalComplete, CorrectiveResolution-with-completed-issue) does not influence the prompt or the agent role. The gate module is currently advisory.

### IB-3 (MEDIUM) — `final_review_accepted` reads `status_graph` while selector reads `issue_graph`
`crates/nancy-live/src/go.rs:447-461` looks up the authorized parent in the status graph. The selector's `authorized_parent` was extracted from the description in `issue_graph` (`selector.rs:144-156`). When the two graphs diverge (e.g., a parent exists in one but not the other due to filtered states), `final_review_accepted` returns false silently. The mismatch is plausible because `fetch_sub_issue_statuses` and `fetch_sub_issues` are separate Linear queries with overlapping but not identical filtering.

### IB-4 (MEDIUM) — `accepted_gate_status` cross-graph identifier match
`crates/nancy-live/src/selector.rs:144-148` finds `accepted_gate` by identifier match across `issue_graph` (direct) using a status pulled from `status_graph`. If the status graph contains a Worker Done gate that the issue graph excluded (state filter applied differently), the description-based gate-text parse silently returns empty, and authorized issue IDs are empty.

### IB-5 (LOW) — `clear_stop` mislabels as `RuntimeLog`
`crates/nancy-live/src/go.rs:522-535` returns `GoError::RuntimeLog { ... }` on STOP cleanup failure. The error category implies log writing; it should be a dedicated `RemoveSentinel` variant.

## Severity Index

| ID    | Severity | File                     | Lines           | Affects                              |
|-------|----------|--------------------------|------------------|---------------------------------------|
| SF-1  | CRITICAL | go.rs / supervisor.rs    | 364-376 / 71-106 | ALP-2246, ALP-2247                    |
| SF-2  | CRITICAL | go.rs                    | 441-445          | ALP-2215, ALP-2232, ALP-2247          |
| PG-1  | CRITICAL | go.rs                    | 400-408          | ALP-2230, ALP-2243, ALP-2247          |
| PG-2  | CRITICAL | go.rs                    | 171-182, 463-479 | ALP-2215, ALP-2232, ALP-2244, ALP-2247 |
| IB-1  | CRITICAL | gate.rs / go.rs          | 252-258 / 463-479 | ALP-2215, ALP-2232, ALP-2244          |
| SF-3  | HIGH     | task.rs                  | 212-221          | ALP-2230, ALP-2243, ALP-2245          |
| PG-3  | HIGH     | go.rs                    | 447-461          | ALP-2215, ALP-2230, ALP-2247          |
| PG-4  | HIGH     | go.rs                    | 386-398          | ALP-2247                              |
| PG-5  | HIGH     | selector.rs              | 618-620          | ALP-2217, ALP-2230, ALP-2242          |
| MA-1  | HIGH     | tests/go.rs              | 359-414, 530-553 | ALP-2215, ALP-2232, ALP-2247, ALP-2248 |
| IB-2  | HIGH     | gate.rs / go.rs          | 117-145 / 332-377 | ALP-2232, ALP-2247                    |
| SF-4  | MEDIUM   | workspace.rs             | 127-138          | ALP-2239                              |
| SF-5  | MEDIUM   | worktree.rs              | 110-116          | ALP-2245                              |
| SF-6  | MEDIUM   | supervisor.rs            | 108-117, 408-411 | ALP-2246                              |
| SF-7  | MEDIUM   | supervisor.rs            | 344-351          | ALP-2246                              |
| PG-6  | MEDIUM   | selector.rs              | 126-130          | ALP-2230, ALP-2242                    |
| PG-7  | MEDIUM   | selector.rs              | 630-633          | ALP-2230, ALP-2242                    |
| PG-8  | MEDIUM   | selector.rs              | 463-470          | ALP-2230, ALP-2242                    |
| MA-2  | HIGH     | tests/task.rs            | (missing tests)  | ALP-2244                              |
| MA-3  | MEDIUM   | tests/prompt.rs          | 121              | ALP-2230, ALP-2243                    |
| MA-4  | MEDIUM   | crate                    | (missing tests)  | ALP-2248                              |
| MA-5  | MEDIUM   | tests/selector.rs        | (missing tests)  | ALP-2242                              |
| MA-6  | MEDIUM   | tests/supervisor.rs      | (missing tests)  | ALP-2246                              |
| UP-1  | HIGH     | selector.rs / go.rs      | 269-290 / 190-192 | ALP-2232, ALP-2247                    |
| UP-2  | MEDIUM   | gate.rs / go.rs          | 132-145 / 345    | ALP-2232, ALP-2243, ALP-2247          |
| IB-3  | MEDIUM   | go.rs                    | 447-461          | ALP-2241, ALP-2247                    |
| IB-4  | MEDIUM   | selector.rs              | 144-148          | ALP-2241, ALP-2242                    |
| DRY-1 | LOW      | gate.rs / go.rs          | 264-267 / 488-491 | ALP-2244, ALP-2247                    |
| DRY-2 | LOW      | go.rs                    | 386-408          | ALP-2247                              |
| DRY-3 | LOW      | linear.rs                | 9-12             | ALP-2241                              |
| DRY-4 | LOW      | selector.rs              | 614-620          | ALP-2217, ALP-2242                    |
| DRY-5 | LOW      | task.rs                  | 9-13             | ALP-2244                              |
| SF-8  | LOW      | task.rs                  | 241-243          | ALP-2244                              |
| SF-9  | LOW      | setup.rs                 | 166-172          | ALP-2240                              |
| UP-3  | LOW      | go.rs                    | 386-398          | ALP-2247                              |
| IB-5  | LOW      | go.rs                    | 522-535          | ALP-2247                              |

Total findings: 35 (5 critical, 7 high, 13 medium, 10 low).

## Positive Observations

The crate skeleton is clean: error types are distinct per module, `From` impls compose into `LiveError`/`GoError` hierarchies, and tests exercise individual primitives well in isolation (`tests/selector.rs` covers eight selector contracts; `tests/gate.rs` covers seven gate snapshot scenarios). The legacy review hook leak is verifiably gone — no `_start_run_review_agent` analogue, no `templates/REVIEW.md.template` reference. The bridge surface is opt-in by default. The setup parity smoke test compares Bash and Rust config JSON byte-for-byte. The module ownership boundaries proposed in ALP-2232 ("the Rust state module should not implement Linear querying, prompt rendering, or worker supervision directly") are respected by `gate.rs`. The integration layer in `go.rs` is where parity slips, not the primitives.

## Recommended Sequencing for Corrective Work

1. Fix IB-1 / PG-2 / SF-2 / SF-1 together — the loop's gate-state semantics are coupled. Make `go.rs::run_go_loop` consume `snapshot.gate` rather than `derived_*` helpers, and require `CODE_COMPLETE` evidence from sentinels before transitioning to FinalComplete. Wire `unread_human_guidance` from a real bus probe. Honor `AgentRunResult::success=false` as a loop-exit condition.
2. Fix PG-1 / PG-4 / DRY-2 — collapse `agent_route` and `prompt_mode` into a single dispatch that maps Planning → worker config + planning template, AgentIssueReview → reviewer config + agent_issue_review template, etc.
3. Fix PG-3 — extend `final_review_accepted` to (a) include `Duplicate`, (b) verify all authorized non-review issues are also released.
4. Fix SF-3 / MA-3 / MA-4 — symmetrize template-missing behavior, add tripwire for the other two deleted templates, add bridge contract smoke crate-side.
5. Fix selector parity gaps PG-5 / PG-6 / PG-7 / PG-8 once IB-1 stops masking selector divergence.
6. Test gaps MA-1 / MA-2 / MA-5 / MA-6 should land alongside the fixes that make the tests possible to write.

## What this review skipped

Per assignment scope, no per-issue acceptance criteria checks for ALP-2237 → ALP-2248 (owned by pair reviewers), no style nits, no doc-comment polish. ALP-2236 cleanup of the deleted-template runtime references (Bash side) is out of scope for this Rust audit.
