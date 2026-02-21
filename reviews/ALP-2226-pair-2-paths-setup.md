# ALP-2226 Pair 2 Review: Path Discovery (ALP-2239) + Setup Parity (ALP-2240)

Reviewer: nancy-ALP-2212:helioy-tools:code-reviewer:4:4.2
Worktree: /Users/alphab/Dev/LLM/DEV/TMP/nancy-worktrees/nancy-ALP-2212
Branch: nancy/ALP-2212

## Summary

Both shipped issues meet their stated acceptance criteria. Path discovery and setup are clean, idiomatic Rust with focused error types, no panics on user-recoverable input, and unit tests that exercise each of the named AC cases. The shared path helper (`worktree_path_from_git`) is reused by `prepare_worktree`; setup composes cleanly on top of `WorkspacePaths` without duplicating path logic.

No blockers. Five findings, all Minor or Trivial. Three are worth filing as Linear sub-issues; two are noted in this report only.

The existing cross-binary parity smoke (`tests/setup_parity.rs`) covers fresh setup only, leaving three of the four AC cases verified by unit tests against fakes rather than against the Bash oracle. That is the highest-value area to harden before bridge promotion.

## Per-Issue Findings

### ALP-2239 — Path discovery primitives

Files reviewed:
- `crates/nancy-live/src/workspace.rs:1-247`
- `crates/nancy-live/src/worktree.rs:1-178`
- `crates/nancy-live/src/lib.rs:1-149`
- `crates/nancy-live/src/main.rs:1-7`

Parity contract anchors:
- `nancy/src/cmd/start.sh:129-180` — `_start_setup_worktree` reference.
- `nancy/src/bus/bus.sh:47-55` — `bus::task_worktree_dir` path helper.
- `nancy/nancy:18-22` — env exports for `NANCY_FRAMEWORK_ROOT`, `NANCY_PROJECT_ROOT`, `NANCY_DIR`, `NANCY_TASK_DIR`.
- `ALP-2210` — main-repo `.nancy/tasks/<task>` versus generated worktree boundary.

Verdict: AC met. Discovery resolves all five named env-derived paths, computes the same sibling worktree path as Bash (`<parent>/<repo>-worktrees/nancy-<task>`), and rejects non-git `cwd`s with `WorkspaceError::NotGitWorktree`. Tests cover env discovery, task path derivation, worktree path derivation against `git_init` fixtures, and the non-git rejection path.

Notes:
- The dual-anchor model (env-provided `project_root` for `.nancy/`; git-discovered toplevel for the worktree path) matches Bash's two-anchor behavior. ALP-2210 boundary preserved.
- `worktree_path_from_git` canonicalizes via `git rev-parse --show-toplevel`, matching Bash. The unit test correctly compares against `project_root.canonicalize()` to validate this.
- `prepare_worktree` is intentionally narrow: create-or-reuse, fetch, copy `.env*` and `.fmm.db`. The `cd` and dependency-install steps from Bash's `_start_setup_worktree` belong to the go-loop wiring (ALP-2247), not to the path primitive. This is the correct seam.

No findings filed against ALP-2239.

### ALP-2240 — Setup command parity

Files reviewed:
- `crates/nancy-live/src/setup.rs:1-511`
- `crates/nancy-live/src/config.rs:1-375`
- `crates/nancy-live/tests/setup_parity.rs:1-121`

Parity contract anchors:
- `nancy/src/cmd/setup.sh:1-112` — config write shape, dep+CLI ordering, reconfigure prompt.
- `nancy/src/core/deps.sh:6-44` — `DEPS_REQUIRED` and `DEPS_CLI` lists.
- `nancy/src/core/ui.sh:21-120` — `gum`-backed UI primitives.
- `nancy/src/live/bridge.sh:1-46` — bridge handoff contract (Rust binary inherits caller env, stdout/stderr go to terminal).

Verdict: AC met. `nancy-live setup` writes the same JSON shape as Bash (verified by smoke parity for fresh setup), creates `.nancy/tasks/`, gates on missing required deps, surfaces a no-AI-CLI failure, and re-prompts on existing config. The `SetupUi` and `CommandLookup` traits make the four AC cases unit-testable against fakes.

Findings:

- F1 (Minor) — Hard-coded token threshold drops Bash's per-CLI table.
  - `crates/nancy-live/src/setup.rs:12` declares `SETUP_TOKEN_THRESHOLD: f64 = 0.30`; `setup.rs:303` writes it unconditionally.
  - Bash `nancy/src/cmd/setup.sh:13-16, 68` uses `NANCY_DEFAULTS_THRESHOLD[claude]=0.30, [codex]=0.30` with a `:-0.20` fallback for unknown CLIs.
  - Today both Bash entries are 0.30, so observable behavior is identical. The parity gap appears the moment a third CLI lands in `DEPS_CLI`/`SUPPORTED_CLIS`: Bash would write 0.20, Rust would still write 0.30. Mirror the per-CLI map (or pull from `config.rs` defaults) to keep parity by construction rather than by coincidence.

- F2 (Minor) — Setup banner missing in Rust.
  - `crates/nancy-live/src/setup.rs:56-68` starts straight at `check_required_deps`.
  - Bash `nancy/src/cmd/setup.sh:19` opens with `ui::banner "🤖 Nancy Setup"`.
  - The bridge dispatch (`nancy/src/live/bridge.sh:40-46`) hands stdout straight to the terminal, so users see no header on the Rust path. Not a contract break, but a noticeable UX delta when the bridge flips on. Adding a single `gum style` banner write keeps the surfaces visually equivalent.

- F4 (Minor) — Setup parity smoke covers only fresh setup.
  - `crates/nancy-live/tests/setup_parity.rs:80-121` is the sole cross-binary case and only validates the fresh-setup config-shape.
  - ALP-2240 AC names four cases: fresh setup, existing setup, no available CLI, legacy config replacement. The other three exist as Rust unit tests against the `FakeUi`/`FakeDeps` (`setup.rs:443-492`), which proves Rust internals but not Bash↔Rust agreement.
  - Before the bridge can be promoted (ALP-2248 territory), at least the legacy-config-replacement and no-CLI cases need cross-binary smoke. The fresh case already shows the harness exists; copying it for the remaining cases is mechanical.

Trivial / not filed:

- F3 (Trivial) — Error and info output channel divergence.
  - `crates/nancy-live/src/main.rs:3-5` routes the entire `LiveError` to stderr via `eprintln!`. Bash `nancy/src/cmd/setup.sh:43-48` mixes `log::error` (stderr) with `echo` (stdout) for the no-CLI case.
  - Since the bridge does not capture this stream and the parity test only diffs the config file, the divergence is invisible to consumers. Documenting only.

- F5 (Trivial) — JSON literal divergence on `token_threshold` (`0.30` vs `0.3`).
  - `crates/nancy-live/src/setup.rs:300-322` uses `serde_json::to_string_pretty`, which formats `0.30_f64` as `0.3`. Bash heredoc (`nancy/src/cmd/setup.sh:81-101`) writes literal `0.30`.
  - `setup_parity.rs` parses both as `serde_json::Value`, so the test passes. Byte-level diffs would not match. Not worth fixing unless someone starts byte-diffing.

## Cross-Issue Notes

- DRY across the pair is good: `setup.rs` consumes `WorkspacePaths` directly; `worktree.rs` consumes `worktree_path_from_git` from `workspace.rs`. No path strings are reconstructed inline.
- The bridge contract from `ALP-2230` is honored: the binary reads `NANCY_FRAMEWORK_ROOT`/`NANCY_PROJECT_ROOT` from env, exits non-zero on errors, and emits no contaminating stdout in the fresh-setup case.
- `WorkspacePaths::from_roots` (used in tests) skips git verification, but `prepare_worktree` and `worktree_path_from_git` re-introduce the git boundary check at the right call sites. No way to reach a worktree-affecting operation without a git presence check.
- `WorkspaceError::GitRootHasNoParent` and the `expect("git root with a parent has a final path component")` at `workspace.rs:107-109` are reachable only on a `/`-rooted git repo, which `git rev-parse --show-toplevel` will not produce in practice. Acceptable.
- ALP-2210 boundary is preserved: task state files land under `project_root/.nancy/tasks/<task>/`; source edits land in the sibling `<parent>/<repo>-worktrees/nancy-<task>` worktree. Rust does not blur these surfaces.
- Verification commands named in the AC (`cargo test -p nancy-live workspace`, `cargo test -p nancy-live setup`, `just check`) were not re-run as part of this review; both issues are `Worker Done` and the source tree shows the expected test cases.

## Severity Index

| ID | Severity | Issue | File:Line |
|----|----------|-------|-----------|
| F1 | Minor    | Hard-coded `SETUP_TOKEN_THRESHOLD` drops Bash per-CLI fallback | `crates/nancy-live/src/setup.rs:12,303` |
| F2 | Minor    | Setup banner not emitted on Rust path | `crates/nancy-live/src/setup.rs:56-68` |
| F3 | Trivial  | Error/info output stream divergence vs Bash | `crates/nancy-live/src/main.rs:3-5` |
| F4 | Minor    | Setup parity smoke covers fresh case only | `crates/nancy-live/tests/setup_parity.rs:80-121` |
| F5 | Trivial  | `token_threshold` JSON literal `0.3` vs Bash `0.30` | `crates/nancy-live/src/setup.rs:300-322` |

Filed as Linear sub-issues under ALP-2226:
- F1 → [ALP-2250](https://linear.app/alphabio/issue/ALP-2250)
- F2 → [ALP-2252](https://linear.app/alphabio/issue/ALP-2252)
- F4 → [ALP-2253](https://linear.app/alphabio/issue/ALP-2253)

F3 and F5 documented here only.
