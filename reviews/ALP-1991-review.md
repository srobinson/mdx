---
title: ALP-1991 Review — Refactor resolve_auto_scope
type: reviews
tags: [review, ALP-1991, ALP-1970, cm-capabilities, scope, kiss]
summary: Nancy's KISS polish of resolve_auto_scope accepted with one minor follow-up on threshold naming semantics.
status: active
source: backend-engineer
confidence: high
created: 2026-04-22
updated: 2026-04-22
---

# ALP-1991 Review

**Worktree:** `/Users/alphab/Dev/LLM/DEV/helioy/context-matters-worktrees/nancy-ALP-1970`
**Commit under review:** `8c56d2e nancy[ALP-1991]: Refactor auto scope resolution helpers`
**Current location of code:** Moved to `crates/cm-capabilities/src/scope/resolution.rs` by a subsequent unrelated commit `03dfd5a refactor: split scope module`.
**Parent issue:** ALP-1970.

## Verdict

**ACCEPT WITH FOLLOW-UPS.**

The refactor meets every acceptance criterion. The orchestrator reads as a three-step pipeline, thresholds are named, helpers are private and independently testable, parity tests still pass, clippy is clean. One minor naming deviation from the issue's suggested names plus a thin test-boundary coverage gap are worth noting but do not block acceptance.

## Acceptance criteria checklist

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Named constants replace all magic threshold literals in `scope.rs` | PASS | `resolution.rs:13-17` declares five `AUTO_SCOPE_*` constants. `grep` for the literals `200`, `100`, `30`, `10` inside the scoring/confidence logic returns zero hits — every use goes through a named constant (`resolution.rs:230, 235, 238, 245, 249, 270, 278, 286, 288`). |
| 2 | `resolve_auto_scope` body reads as a short pipeline of three named helper calls | PASS | `resolution.rs:74-100`. Body is 27 lines: `filter_candidates` → `rate_confidence(confidence_score(...))` → `resolution_signals` → struct assembly. Fits one screen. |
| 3 | Each helper independently testable; ≥1 unit test each for `score_candidate` and `rate_confidence` | PASS | `resolution.rs:368-380` (`score_candidate_combines_repo_match_and_specificity`), `resolution.rs:382-400` (`rate_confidence_maps_score_bands`). |
| 4 | All existing parity tests still pass | PASS | `cargo test -p cm-capabilities` — all scope-related tests green (13 tests in `browse_scope::*` including the auto-resolution parity suite). The one workspace failure (`cm-store::project::tests::resolve_home_dir_succeeds_with_home_set`) is a pre-existing test-ordering flake in a file Nancy did not touch; passes under `--test-threads=1`. |
| 5 | No new public types or exports | PASS | `resolve_auto_scope` remains `fn` (not `pub`) — `resolution.rs:74`. The re-export list in `crates/cm-capabilities/src/scope.rs:5-10` is identical to pre-refactor. No new `pub` items added. |
| 6 | No behavioural change | PASS | Constant values equal the prior literals (200/100/30/10/0). `score_candidate`, `rate_confidence`, and `confidence_score` preserve the prior branching semantics. The one behavioural-looking diff — introducing a `.filter()` that drops candidates scoring below `AUTO_SCOPE_PROJECT_FALLBACK_SCORE` inside `filter_candidates` — is functionally equivalent to the prior implicit floor, because the existing upstream candidate-selection logic already refused to emit candidates below that threshold (only `Global`, matched-`Repo`, or matched-`Project` scopes enter the pool). Parity tests confirm. |
| 7 | `cargo clippy --workspace --all-targets -- -D warnings` clean | PASS | Zero warnings. |

## Readability assessment

`resolve_auto_scope` is meaningfully cleaner, not merely shuffled. Pre-refactor it was a 75-line body interleaving candidate-path collection, scoring, sorting, fallback-error construction, confidence derivation, and signal assembly. Post-refactor the body is a genuine pipeline: build candidates → pick top → rate confidence → assemble signals → construct result. The reader can now scan the orchestrator and decide which helper to descend into, rather than tracking three concerns in one mental frame.

`filter_candidates` is a fair name for what it does (candidate-path discovery, scoring, threshold filtering, sorting) though it does a little more than pure filtering. The issue suggested splitting "filter" into its own step, but Nancy's grouping — all candidate-list construction in one place — is defensible and arguably cleaner than three tiny functions that would have to share intermediate state.

The `confidence_score` → `rate_confidence` split is the most elegant part. `confidence_score` handles the one irregularity in the rating logic (the tied-repo demotion from 200→100), and `rate_confidence` is a pure score-band mapping that was trivially easy to unit-test.

## Test quality

**Adequate for the ticket, thin on boundaries.**

- `rate_confidence_maps_score_bands` tests one value per band: `AUTO_SCOPE_REPO_MATCH_SCORE` → High, `AUTO_SCOPE_PROJECT_MATCH_SCORE` → Medium, `AUTO_SCOPE_REPO_SPECIFICITY_SCORE` → Low, `AUTO_SCOPE_NO_SIGNAL_SCORE` → VeryLow. This hits the `>=` boundary on High and Medium and the `>` boundary on Low but does **not** test the off-by-one cases (score = `AUTO_SCOPE_REPO_MATCH_SCORE - 1` → Medium, score = `AUTO_SCOPE_PROJECT_MATCH_SCORE - 1` → Low, score = 1 → Low). Those are the cases most likely to regress if someone later flips `>=` to `>`. Worth a three-line extension.
- `score_candidate_combines_repo_match_and_specificity` tests the additive `REPO_MATCH + REPO_SPECIFICITY = 230` case. It does not cover `project_cwd`, `project_parent`, the `has_cwd = false` path, or `ScopeKind::Global` fallback. One test is what the ticket asked for; more would be better.

This is happy-path-plus-one coverage. Acceptable for KISS polish, not comprehensive.

## Surprises and smells

- **Threshold names diverge from the issue's suggestion.** The issue recommended generic, semantic names: `AUTO_SCOPE_EXACT_MATCH`, `AUTO_SCOPE_STRONG_SIGNAL`, `AUTO_SCOPE_WEAK_SIGNAL`, `AUTO_SCOPE_FALLBACK_FLOOR`. Nancy chose concrete names tied to the scoring dimension: `AUTO_SCOPE_REPO_MATCH_SCORE`, `AUTO_SCOPE_PROJECT_MATCH_SCORE`, `AUTO_SCOPE_REPO_SPECIFICITY_SCORE`, `AUTO_SCOPE_PROJECT_FALLBACK_SCORE`, `AUTO_SCOPE_NO_SIGNAL_SCORE`. The issue explicitly said "Pick names that reflect what each threshold means, not just its numeric bracket." Nancy's names reflect **which signal earned the points**, which is a defensible reading — and arguably more informative than the suggested abstraction, because the same constant is reused in `rate_confidence` as a confidence boundary. The risk is that `AUTO_SCOPE_PROJECT_MATCH_SCORE` reads weird when it appears in `rate_confidence` as a Medium-confidence boundary (it's not matching a project there, it's a boundary value that happens to equal the project-match score). This is a mild ubiquitous-language smell, not a bug.
- **`confidence_score` introduces a funky value coupling.** When there are tied repo scores at 200, `confidence_score` returns `AUTO_SCOPE_PROJECT_MATCH_SCORE` (100) to demote to Medium. The use of the constant here is semantic reuse (we want the Medium boundary), but it reads as "tied repos → the project-match score" which is misleading. A separate `AUTO_SCOPE_MEDIUM_THRESHOLD` alias — even if numerically equal — would decouple the two meanings. Not a blocker.
- **Scope creep: none.** Only `scope.rs` was edited, no unrelated drive-by changes. Public API unchanged. Nancy did not attempt to refactor `resolution_signals` or `filter_candidates`' inner structure despite both being arguably ripe.
- **No half-finished work.** Tests compile, helpers are wired up, imports are clean, no dead code.
- **Commit hygiene is correct.** One logical commit, clear message, scoped to the issue.
- **Current file location mismatch.** The issue referenced `crates/cm-capabilities/src/scope.rs`; code now lives in `crates/cm-capabilities/src/scope/resolution.rs` due to a later `refactor: split scope module` commit (03dfd5a). Not Nancy's fault — this happened after ALP-1991 was merged — but reviewers tracing from the ticket will need the hint.

## Suggested follow-ups (non-blocking)

1. Add three boundary tests to `rate_confidence_maps_score_bands` for `SCORE - 1` on each band edge. Three `assert_eq!` lines.
2. Consider whether `confidence_score` should return a named `AUTO_SCOPE_MEDIUM_BOUNDARY` constant distinct from `AUTO_SCOPE_PROJECT_MATCH_SCORE` despite their numeric equality, to document the semantic distinction.

Neither item warrants a new issue on its own; fold into the next touch of `resolution.rs`.

## Files inspected

- `/Users/alphab/Dev/LLM/DEV/helioy/context-matters-worktrees/nancy-ALP-1970/crates/cm-capabilities/src/scope.rs` (module root, unchanged by Nancy)
- `/Users/alphab/Dev/LLM/DEV/helioy/context-matters-worktrees/nancy-ALP-1970/crates/cm-capabilities/src/scope/resolution.rs` (post-split location of the refactored code)
- Commit `8c56d2e` full diff
