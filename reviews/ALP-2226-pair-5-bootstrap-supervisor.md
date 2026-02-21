# ALP-2226 Pair 5 Review: Go Task Bootstrap (ALP-2245) and Worker Supervisor Primitives (ALP-2246)

Reviewer: nancy-ALP-2212:helioy-tools:code-reviewer:4:4.5
Orchestrator: nancy-ALP-2212:general:4:3.1
Worktree: /Users/alphab/Dev/LLM/DEV/TMP/nancy-worktrees/nancy-ALP-2212
Date: 2026-05-02
Review pair: ALP-2245 + ALP-2246
Bash oracle: src/cmd/start.sh, src/cli/drivers/{claude,codex}.sh, src/comms/comms.sh, src/task/task.sh

## Summary

Both targets implement the named primitives, but each ships parity gaps that block clean wiring in ALP-2247. Bootstrap (ALP-2245) is structurally sound: workspace paths, worktree creation, env/.fmm.db copy, ISSUES.md emission, and selector evaluation all match Bash shape. Two issues stand out: an unused stale `PROMPT.md` is written at bootstrap, and the comms tree seeded under the task dir does not match the Bash inbox/outbox layout.

Supervisor (ALP-2246) covers the configured-CLI invocation surface, stream parsing, and Claude hook restoration on Drop. Three lifecycle primitives present in Bash are missing: `.worker_pid`, `.worker_uuid`, and the post-run copy of Claude's session JSONL. `nancy stop` cannot signal the worker, the sidecar cannot track Claude session UUIDs, and per-task durable session evidence is not preserved. The Claude hook installer also overwrites the worktree's existing `settings.local.json` with a hooks-only file, dropping permissions and MCP configuration during the run. Tests pass on the happy path but do not exercise these primitives.

Net read: solid scaffolding, but ALP-2247 cannot wire stop/sidecar/handover until the worker lifecycle files and hook merge land. None of the gaps are architectural; each maps to a small focused change.

## Per-Issue Findings

### ALP-2245 Implement Rust go task bootstrap

**Status: needs corrective work before ALP-2247 wiring.**

| AC | Verdict | Notes |
|----|---------|-------|
| `.nancy/tasks/<task>` only in main repo | Pass | `WorkspacePaths::task_paths` rooted at `project_root/.nancy/tasks`; `bootstrap_go` calls `create_task_tree` against this path. workspace.rs:54-73 |
| Selector evidence to ISSUES.md, no checkbox authority | Pass with cosmetic drift | `go.rs::write_issues_file` writes a "Selector Decision" header that flags ISSUES.md as evidence only. Checkbox column is preserved for parity. See finding F18 for column alignment. |
| Sibling worktree path + `nancy/<task>` branch | Pass | `worktree::prepare_worktree` (worktree.rs:35-56) uses `worktree_path_from_git`, falls back from `-b` to plain checkout for an existing branch, matching start.sh:139-145. |
| Copy `.env*` and `.fmm.db` | Pass | `copy_worktree_inputs` (worktree.rs:118-153) iterates `.env*` and copies `.fmm.db` when present. Matches start.sh:146-156. |
| `nancy start` not exposed | Pass | lib.rs::parse_command only accepts `setup`/`go`. lib.rs:118-124 |
| Tests cover bootstrap and worktree path | Partial | tests/go.rs covers bootstrap+loop; tests/task.rs covers sentinels but does NOT cover `create_task_tree` shape or `write_initial_prompt` template handling. |

Findings:

* **F1 (HIGH).** `create_task_tree` writes a stale bootstrap-time `PROMPT.md` (task.rs:78, 205-226) that contains only `{{TASK_NAME}}` substituted. The actual rendered prompt is written per-iteration to `PROMPT.{task}.md` in `go.rs::write_prompt_file` (go.rs:423-435). Bash never seeds a bootstrap-time prompt. The orphan `PROMPT.md` sits in the task dir with unsubstituted `{{MODE_INSTRUCTIONS_SECTION}}`, `{{NANCY_PROJECT_ROOT}}`, etc. and will confuse anyone inspecting the dir or any tool that reads `PROMPT.md` by convention. Fix: drop `write_initial_prompt` from `create_task_tree`. The task dir is fully created by the per-iteration write path.

* **F2 (MEDIUM).** `write_initial_prompt` swallows a missing template silently (task.rs:212-220): `ErrorKind::NotFound` returns `Ok(template = "")` and writes an empty `PROMPT.md`. ALP-2230 explicitly states "Missing mode templates are hard errors". Same expectation applies to the main `PROMPT.md.template`. Fix: even if F1 keeps the function, surface NotFound as `TaskError::ReadPromptTemplate`. Recommend deleting along with F1.

* **F3 (MEDIUM).** Comms subdir layout diverges from Bash. task.rs:195-203 creates `comms/{directives,acks,archive}` upfront. Bash `src/comms/comms.sh:32-36` creates `comms/{orchestrator,worker}/{inbox,outbox}` plus `comms/archive`; Bash `src/task/task.sh:53` creates `comms/directives` for the worker→sidecar directive queue. Rust `acks/` is a new convention; Bash `inbox/outbox` and `<role>/` segmentation are missing. The Rust seed neither matches the Bash convention nor matches the directive queue path. If ALP-2247 wires comms-driven control or sidecar handover against Bash conventions, this seed creates parallel empty trees and leaves the canonical paths absent. Decide one canonical layout and seed only that.

* **F4 (LOW).** `task_dir/outputs` (task.rs:198) is created but no Rust or Bash path writes to it. Dead infrastructure. Remove or document the consumer.

* **F17 (MEDIUM).** Bootstrap and loop redundantly fetch the issue graph. `run_go_loop` (go.rs:121-202) fetches `issue_graph` and `status_graph` once, calls `bootstrap_go` which evaluates a `selector_decision`, then immediately re-fetches both graphs and re-evaluates inside the loop body. `bootstrap.selector_decision` is never read after construction. Either drop it from `GoBootstrapResult` or have the loop reuse it on the first iteration. Wasted Linear roundtrip per `nancy go` invocation.

* **F18 (LOW).** ISSUES.md formatting diverges from Bash. Bash pipes through `column -t -s $'\t'` for fixed-width alignment (start.sh:122). Rust emits raw `\t`-separated rows (go.rs:586-639). The file is human-readable but visually unequal to Bash. Consider an in-Rust column aligner or accept the drift explicitly.

* **F19 (LOW).** Selector marker prefixes diverge. Bash uses `↳ ` (Unicode arrow) for child rows (start.sh:107); Rust uses `-> ` (ASCII) (go.rs:590). Cosmetic.

### ALP-2246 Implement Rust worker supervisor primitives

**Status: needs corrective work before ALP-2247 wiring.**

| AC | Verdict | Notes |
|----|---------|-------|
| Spawn worker CLI with prompt + session file path | Pass | supervisor.rs:71-106 sets env, runs driver, captures output. |
| Spawn reviewer CLI for reviewer modes | Pass | Same `run_agent` path with `AgentRole::Reviewer`. |
| Capture stdout, stderr, exit, session evidence | Partial | stdout/stderr/exit captured. "Session evidence" defined as `session_evidence.session_file_exists` only; the supervisor does not write the session file or copy Claude's project JSONL. See F8. |
| Claude env cleanup + hook restoration | Partial | `remove_nested_claude_env` removes `CLAUDECODE*` (supervisor.rs:264-273). `ClaudeHooksGuard` restores on Drop. But hook install overwrites pre-existing settings during the run; see F5. |
| Stream parsing + token usage with tests | Partial | `parse_stream_evidence` covers Claude `system/init`, `assistant`, `result`, Codex `thread.started`, `item.completed`, `turn.completed`. Output buffered then parsed post-hoc; see F9. |
| Primitives do not write final sentinels or decide gate mode | Pass | Supervisor does not write COMPLETE/CODE_COMPLETE; gate decisions stay in gate.rs. |

Findings:

* **F5 (HIGH).** `ClaudeHooksGuard::install` overwrites the worktree's `settings.local.json` with a hooks-only document (supervisor.rs:325-338). Any pre-existing `permissions.allow`, `mcpServers`, model/agent defaults, or other sections are lost during the run. The Drop handler restores the original after the run, but the agent operates without those settings during execution. The test `spawns_reviewer_with_reviewer_config_and_restores_claude_hooks` (tests/supervisor.rs:83-150) only asserts post-run restoration; it does not verify the merged state during the run. Fix: parse existing settings as `serde_json::Value`, set `["hooks"]["PreToolUse"|"PreCompact"|"Stop"]` while preserving every other key, then write back.

* **F6 (HIGH).** Supervisor does not write `.worker_pid`. Bash `cli::claude::run_prompt` (claude.sh:185-194) and `cli::codex::run_prompt` (codex.sh:55-69) both record the worker PID at `${NANCY_TASK_DIR}/.worker_pid` before exec. `nancy stop` (start.sh:19-31) reads this file and signals SIGTERM/SIGKILL. Without the Rust supervisor writing this, in-flight Rust-driven workers cannot be stopped externally. The loop's STOP sentinel polling is asynchronous and only checked between iterations; it cannot interrupt a running worker. Fix: write the child PID to `task_dir/.worker_pid` after `command.spawn()` returns, remove the file on completion (success or failure).

* **F7 (HIGH).** Supervisor does not write `.worker_uuid` for Claude. Bash claude.sh:180 writes the UUID to `${NANCY_TASK_DIR}/.worker_uuid` before exec. The sidecar reads this to track which Claude project session belongs to the current iteration and to copy the JSONL post-run. Rust never writes it. Fix: when `DriverKind::Claude`, write the resolved UUID (currently `invocation.uuid.unwrap_or(invocation.session_id)`) to `task_dir/.worker_uuid` before spawn.

* **F8 (HIGH).** Supervisor does not copy the Claude session JSONL into the task dir. Bash `_copy_project_session` (claude.sh:211-228) copies `~/.claude/projects/<encoded-cwd>/<uuid>.jsonl` into `${NANCY_TASK_DIR}/session-state/${nancy_session_id}.jsonl` after the worker exits. This is the durable, task-local audit record of the Claude run. Rust does not perform this copy; `session_evidence.session_file_exists` checks an unrelated path. Per ALP-2246 AC: "Rust captures stdout, stderr, exit status, and session evidence." The session evidence requirement is not met for Claude. Fix: after Claude exit, encode `worktree_dir` per Claude convention (`/` and `.` → `-`), look up `~/.claude/projects/<encoded>/<uuid>.jsonl`, copy to `task_dir/session-state/<session_id>.jsonl`. Codex/Copilot have their own session conventions; capture them as a follow-up.

* **F9 (MEDIUM).** Stream output is buffered fully in memory. `run_driver` calls `child.wait_with_output()` (supervisor.rs:213-216) which collects all stdout/stderr into one `Vec<u8>` before returning. `parse_stream_evidence` then runs over the post-exit string. ALP-2231 mining recommendation cites "stream parsing", "token budget math", "directive queue priority" as live primitives. With the current shape, ALP-2247 cannot inspect token usage mid-stream to handle handovers, and long sessions risk OOM. Fix path: replace `Stdio::piped`/`wait_with_output` with a reader thread that consumes stdout line-by-line, feeds `apply_stream_value` incrementally, and forwards events to a `Sender<StreamEvent>` for the loop to consume.

* **F10 (MEDIUM).** `ClaudeHooksGuard` Drop deletes the worktree `.claude/` directory when no original settings file existed (supervisor.rs:347-350). The `let _ = std::fs::remove_dir(parent)` will succeed if the directory is empty. If Claude wrote nothing under `.claude/` during the run, this rmdir destroys the directory the guard created; harmless. But if the directory was created earlier by something other than the guard (e.g., user setup, prior failed run), the guard now owns its deletion semantics incorrectly. Track whether the guard created `.claude/` and only remove what it created. Better: do not remove the directory at all; only the file the guard wrote.

* **F11 (MEDIUM).** `claude_config_dir` falls back to `"."` when `HOME` is unset (supervisor.rs:275-282). This silently writes Claude config into the current working directory (the worktree), polluting it. Should return a `SupervisorError` or rely on `XDG_CONFIG_HOME`. Bash claude.sh:40 uses `${HOME}/.claude` directly; HOME unset is treated as a system-level error, not silently masked.

* **F14 (LOW).** `serde_json::to_string_pretty(&settings).unwrap()` (supervisor.rs:332). The literal JSON cannot fail to serialize, but `unwrap()` makes the precondition implicit. Use `expect("hooks settings JSON is well-formed")`.

* **F15 (LOW).** `tests/supervisor.rs:115-117, 130-132` mutates `CLAUDECODE` via `unsafe std::env::set_var`. cargo test runs tests in parallel by default; another test that reads `CLAUDECODE` (none currently, but easy to add) can race. Mark this test serial or scope the env mutation more narrowly; a `#[serial]` attribute or a `Mutex` guard around the test body removes the risk.

## Cross-Issue Notes

* **F16 (HIGH).** Test coverage is shallow for supervisor lifecycle. `tests/supervisor.rs` exercises a single happy-path execution per driver. It does not cover: writing `.worker_pid`/`.worker_uuid`, hook merge with pre-existing permissions during the run, JSONL copy after Claude exits, subprocess interruption / SIGTERM, streaming consumption mid-process, generic-driver argv contracts, or HOME-unset behavior. Once F5-F8 land, each needs a dedicated test. Recommend a single `tests/supervisor_lifecycle.rs` covering the worker process model end-to-end with stub binaries.

* **Bridge readiness.** The Bash bridge (`src/live/bridge.sh`) is wired and defaults off, so these gaps do not regress production. They block ALP-2247 (loop wiring) and ALP-2248 (parity smoke tests) from passing because the smoke harness needs `.worker_pid` and `.worker_uuid` to run a stop scenario, and needs the JSONL copy to verify session evidence parity.

* **Vertical AC summary.** ALP-2245 meets each AC if F1/F2 are accepted as scope drift to fix; ALP-2246 misses the "captures session evidence" AC for Claude (F8) and partially the "preserves Claude environment cleanup and hook settings restoration" AC (F5).

* **Horizontal coupling.** `bootstrap_go` and `run_go_loop` are clean handoffs: bootstrap returns a `GoBootstrapResult`, loop consumes `worktree.dir` and `task_paths`. No process state leaks between layers. Supervisor is invoked from the loop with all path inputs explicit; no globals. F17 is a redundant Linear fetch, not a coupling defect.

## Severity Index

| ID | Severity | Title | File:Line |
|----|----------|-------|-----------|
| F1 | HIGH | Stale bootstrap PROMPT.md never read or updated | crates/nancy-live/src/task.rs:78,205-226 |
| F5 | HIGH | Claude hook install overwrites pre-existing settings.local.json | crates/nancy-live/src/supervisor.rs:325-338 |
| F6 | HIGH | Supervisor does not write .worker_pid; nancy stop cannot signal worker | crates/nancy-live/src/supervisor.rs:165-217 |
| F7 | HIGH | Supervisor does not write .worker_uuid for Claude | crates/nancy-live/src/supervisor.rs:230-243 |
| F8 | HIGH | Supervisor does not copy Claude session JSONL into task dir | crates/nancy-live/src/supervisor.rs:71-106 |
| F16 | HIGH | Supervisor lifecycle tests do not cover pid/uuid/jsonl/hooks-merge/streaming | crates/nancy-live/tests/supervisor.rs |
| F2 | MEDIUM | write_initial_prompt swallows missing template silently | crates/nancy-live/src/task.rs:212-220 |
| F3 | MEDIUM | comms subdir layout diverges from Bash inbox/outbox | crates/nancy-live/src/task.rs:195-203 |
| F9 | MEDIUM | Stream output buffered fully in memory; no live consumer | crates/nancy-live/src/supervisor.rs:189-217 |
| F10 | MEDIUM | ClaudeHooksGuard Drop removes worktree .claude dir when empty | crates/nancy-live/src/supervisor.rs:342-352 |
| F11 | MEDIUM | claude_config_dir silently falls back to "." when HOME unset | crates/nancy-live/src/supervisor.rs:275-282 |
| F17 | MEDIUM | Bootstrap and loop fetch issue graph twice; bootstrap selector unused | crates/nancy-live/src/go.rs:121-202 |
| F4 | LOW | task_dir/outputs created but never written | crates/nancy-live/src/task.rs:198 |
| F14 | LOW | unwrap on infallible serde_json::to_string_pretty | crates/nancy-live/src/supervisor.rs:332 |
| F15 | LOW | tests/supervisor.rs mutates CLAUDECODE without serial guard | crates/nancy-live/tests/supervisor.rs:115-132 |
| F18 | LOW | ISSUES.md not column-aligned vs Bash `column -t` | crates/nancy-live/src/go.rs:578-639 |
| F19 | LOW | Selector marker child prefix is "-> " not "↳ " | crates/nancy-live/src/go.rs:590 |
