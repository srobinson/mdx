# ALP-2226 Pair 4 Review: Prompt Renderer + Gate Sentinel Primitives

Reviewer: nancy-ALP-2212:helioy-tools:code-reviewer:4:4.4
Worktree: /Users/alphab/Dev/LLM/DEV/TMP/nancy-worktrees/nancy-ALP-2212
Targets: ALP-2243 (gate mode prompt renderer), ALP-2244 (gate sentinel primitives)
Parity oracles: ALP-2230 (Bash gate aware behavior), ALP-2215 (gate state model), ALP-2216 (prompt architecture), ALP-2232 (Rust gate type design)

## Summary

Both targets land their declared acceptance criteria. `crates/nancy-live/src/prompt.rs` renders all six gate-aware modes through `templates/PROMPT.md.template` and `templates/modes/*.md.template`, surfaces missing mode templates as hard errors, appends project-local `PROMPT.md`, and selects CLI-sensitive turn-exit text. `crates/nancy-live/src/gate.rs` models `GateMode`, `GateState`, `LoopControl`, `CompletionMarker`, `TaskSentinels`, and `GateSnapshot` with `serde` snake-case serialization that matches selector output, and the typed sentinel reconciliation honors the ALP-2232 failure mode rules. `cargo test -p nancy-live` is green (16 prompt + gate tests, 55 total in this run).

The renderer itself is correct, but its consumer in `crates/nancy-live/src/go.rs` collapses `GateMode::Planning` into `PromptMode::AgentIssueReview`, defeating the renderer's mode coverage when selector emits planning. That regression is owned by ALP-2247, not by ALP-2243, but it is the most material defect surfaced by this review and is documented below.

Other findings are low-severity: cosmetic whitespace drift versus the Bash oracle, lost operator log line on local prompt append, an `Option<IssueRef>` widening in `GateState::Execution`, an `authorized_parent: String` deviation from the spec's `IssueRef`, and DRY/test-coverage notes.

## Per-Issue Findings

### ALP-2243: Implement Rust gate mode prompt renderer

#### F1. `prompt_mode` collapses `Planning` into `AgentIssueReview` (Medium, owner ALP-2247)

`crates/nancy-live/src/go.rs:400-408` maps `GateMode::Planning | GateMode::AgentIssueReview => PromptMode::AgentIssueReview`. The renderer correctly supports `PromptMode::Planning` and the on-disk `templates/modes/planning.md.template` exists with the planning-specific body ("Mode: Planning Gate", "Create or update exactly one focused planning issue at a time"). The wiring discards that template whenever selector emits planning mode, so a planning iteration receives the agent_issue_review prompt instead.

Impact: in planning mode the worker is told to "decide whether the issue is ready, contested, or needs human direction" rather than to "create or update one focused planning issue at a time". Different responsibilities, different boundaries, different handover semantics. The Bash oracle in `src/cmd/start.sh:407-446` drives mode strictly from the selector via `_NEXT_PROMPT_MODE` and does not collapse modes.

This finding sits in ALP-2247's wiring, not in the renderer, but it is reported here because the renderer's mode coverage is silently bypassed.

Recommended fix: drop the union arm and restore the 1:1 mapping
```rust
GateMode::Planning => PromptMode::Planning,
GateMode::AgentIssueReview => PromptMode::AgentIssueReview,
```
Add a regression test in `crates/nancy-live/tests/go.rs` (or similar) that asserts planning mode renders the planning-template-specific header.

#### F2. Whitespace drift versus Bash oracle around `## Turn Exit` and template tails (Low)

Bash `_start_render_worker_prompt` (`src/cmd/start.sh:407-446`) builds the prompt via `$(cat ...)` and `$(_start_turn_exit_instruction)` substitutions, both of which strip trailing newlines. The turn-exit heredoc starts with a single blank line. Net: Bash emits exactly one `\n` before `## Turn Exit` and a single trailing newline from `printf '%s\n'`.

Rust `crates/nancy-live/src/prompt.rs:78-90, 101-114` preserves trailing newlines from `std::fs::read_to_string` and prefixes turn-exit with `\n\n`. Net: Rust emits two-to-three blank lines before `## Turn Exit` depending on whether the local prompt was appended.

Cosmetic only, but visible in saved prompt snapshots that operators diff for parity.

Recommended fix: `trim_end_matches('\n')` on `template`, `mode_instructions`, and `local_prompt` before joining; emit a single leading `\n` for the turn-exit text.

#### F3. Lost operator visibility for local PROMPT.md append (Low)

Bash logs `log::info "Appending local prompt: $prompt_file_local" >&2` (`src/cmd/start.sh:439`) so operators see when a project-local prompt fragment is being merged. Rust `append_local_prompt` (`prompt.rs:249-263`) is silent.

The AC ("Local prompt append logging cannot contaminate the prompt body") is satisfied trivially by emitting nothing, but the test `project_local_prompt_is_appended_without_log_text` only asserts the prompt body; it does not assert that the operator can still observe the append. Operators relying on stderr lines for parity diagnosis will lose this signal.

Recommended fix: add `eprintln!("Appending local prompt: {}", path.display());` (or route through whatever logger the crate ends up adopting) so the message survives without entering the prompt body.

#### F4. `renders_every_gate_mode_with_required_substitutions` asserts loose substring (Low)

`crates/nancy-live/tests/prompt.rs:50-83` reads the mode template file, substitutes `{{NANCY_CURRENT_TASK_DIR}}`, and asserts `prompt.contains(expected_mode_text.trim())`. The match is satisfied by any rendered prompt that embeds the file contents, but it does not pin the mode-specific header (for example the planning template's `## Mode: Planning Gate`). A wiring regression that swaps mode templates at the call site (see F1) would not fail this test because the wrong template's body would still match its own file.

Recommended fix: assert each mode's unique header line per mode, e.g. `"## Mode: Planning Gate"` for `PromptMode::Planning`, `"## Mode: Agent Issue Review"` for `PromptMode::AgentIssueReview`. This shifts the test from "the template body appears" to "the correct template body appears".

### ALP-2244: Implement Rust gate sentinel primitives

#### F5. `GateState::Execution.selected_issue: Option<IssueRef>` admits a stuck state (Low)

ALP-2232 specifies `GateState::Execution { selected_issue: IssueRef, authorized_parent: IssueRef }` (non-Option). Rust models it as `selected_issue: Option<IssueRef>` (`gate.rs:26-29`). The fall-through in `gate_state` returns `GateState::Execution { selected_issue: None, ... }` whenever selector emits Execution mode without a selectable issue and CODE_COMPLETE is absent (`gate.rs:269` → `selector_gate_state` at `gate.rs:272-294`).

Selector can land in this state when `authorized_issue_ids` is non-empty but every authorized execution issue is blocked, in `Done`, or absent from the graph; the `choose_mode` path at `selector.rs:269-290` still returns `Execution` because `has_authorized_ids` is true. The gate then has no transition signal: not CodeComplete (no sentinel), not Execution-with-issue (no selection), not NeedsHumanDirection. The loop driver in ALP-2247 will dispatch a worker against an `Option<IssueRef>::None` selection.

ALP-2232 transition table implies this should be NeedsHumanDirection or a revised selector contract.

Recommended fix: when `selector.selected_mode == Execution && selector.selected_issue.is_none() && code_complete.is_none()`, return `NeedsHumanDirection` with reason "Authorized execution mode with no selectable issue and no CODE_COMPLETE", source `LinearSelector`. Alternatively narrow the type to `selected_issue: IssueRef` and force the upstream to surface NHD before construction.

#### F6. `authorized_parent: String` deviates from spec `IssueRef` (Low)

`gate.rs:26, 30, 38` use `authorized_parent: String`. ALP-2232 specifies `authorized_parent: IssueRef`. The selector itself only carries the identifier (`selector.rs:14`), so the deviation is currently necessary, but it loses parity with `selected_issue: Option<IssueRef>` in the same variants.

Recommended fix: thread parent title through the selector by enriching `SelectorDecision::authorized_parent` to `IssueRef`, then promote the gate field. Defer if Linear adapter cannot resolve the parent title in this iteration.

#### F7. `CompletionMarker` enum has no consumer in this changeset (Info)

`gate.rs:60-63` defines `enum CompletionMarker { CodeComplete, Complete }` and derives `Serialize`. Nothing in `nancy-live` calls it; AC requires the model to exist. Fine to land as-is, but a doc comment ("Used by ALP-2247 wiring to disambiguate which sentinel to write at task transitions") would prevent future cleanup that interprets it as dead code.

Recommended fix: add a one-line doc comment naming the intended consumer.

#### F8. `should_exit()` semantics are narrow; STOP-driven exit is implicit (Info)

`gate.rs:147-149` returns true only for `FinalComplete` with `LoopControl::Running`. Operator stop is intentionally separate, but the function name reads as "exit the loop". A loop driver that writes `if !snapshot.should_exit() { continue; }` would silently skip STOP handling.

Recommended fix: add a doc comment to `should_exit` clarifying that STOP is surfaced via `snapshot.control == LoopControl::StopRequested` and that the loop driver must check both.

## Cross-Issue Notes

### N1. `GateMode` and `PromptMode` are duplicate enums

Both have the same six variants and the same `as_str` snake-case mapping (`gate.rs:8-15, 196-206` and `prompt.rs:10-39, 41-51`). The translation `prompt_mode(GateMode) -> PromptMode` in `go.rs:400-408` is the bridge. Consolidating to one canonical enum (in a new `mode` module, or by re-exporting `PromptMode` as `GateMode`) would eliminate the manual mapping that masked F1.

### N2. Coupling direction is clean

`gate.rs` consumes `crate::selector::*` and `crate::task::TaskSentinels`. `prompt.rs` consumes `crate::selector::SelectorMode` for the `From` impl. No cycles; gate can be exercised without prompt and vice versa. Keep as-is.

### N3. STOP-driven exit lacks a gate test

`tests/gate.rs::stop_blocks_final_completion_validation` asserts that `STOP + COMPLETE + accepted_inputs` keeps gate at `PostExecutionReview` and reports `LoopControl::StopRequested`. There is no assertion that the loop driver's expected exit path triggers. STOP-driven exit belongs to ALP-2247 wiring tests, but worth flagging here so it is not lost during pair-7 review.

## Severity Index

| ID | Severity | Issue | File:line |
|----|----------|-------|-----------|
| F1 | Medium | `prompt_mode` collapses Planning to AgentIssueReview | crates/nancy-live/src/go.rs:400-408 |
| F2 | Low | Whitespace drift around `## Turn Exit` and template tails | crates/nancy-live/src/prompt.rs:78-114 |
| F3 | Low | Lost operator visibility for local PROMPT.md append | crates/nancy-live/src/prompt.rs:249-263 |
| F4 | Low | Prompt mode test asserts loose substring | crates/nancy-live/tests/prompt.rs:50-83 |
| F5 | Low | `GateState::Execution.selected_issue: Option` admits stuck state | crates/nancy-live/src/gate.rs:26-29, 272-294 |
| F6 | Low | `authorized_parent: String` deviates from spec `IssueRef` | crates/nancy-live/src/gate.rs:26, 30, 38 |
| F7 | Info | `CompletionMarker` has no consumer; document intent | crates/nancy-live/src/gate.rs:60-63 |
| F8 | Info | `should_exit()` semantics narrow; document STOP path | crates/nancy-live/src/gate.rs:147-149 |
| N1 | Info | `GateMode` and `PromptMode` duplicate variants | gate.rs:8-15, prompt.rs:10-39 |
| N3 | Info | STOP-driven exit lacks a gate test | crates/nancy-live/tests/gate.rs |

No High-severity findings. Pair 4 is acceptable to mark `Worker Done` once F1 (owned by ALP-2247) is tracked as a corrective sub-issue.
