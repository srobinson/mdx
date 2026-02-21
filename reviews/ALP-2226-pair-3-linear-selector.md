# ALP-2226 Pair 3 Review: Linear graph adapter (ALP-2241) + Selector decision engine (ALP-2242)

Reviewer: nancy-ALP-2212:helioy-tools:code-reviewer:4:4.3
Date: 2026-05-02
Worktree: /Users/alphab/Dev/LLM/DEV/TMP/nancy-worktrees/nancy-ALP-2212
Bash oracle: /Users/alphab/Dev/LLM/DEV/TMP/nancy/

## Summary

Both implementations meet their acceptance criteria. The Linear adapter (ALP-2241) is a clean typed graph layer with no policy leakage. The selector (ALP-2242) is a faithful Rust port of `linear::selector:evaluate` and produces the same output contract as the Bash oracle for every covered fixture. All 8 selector integration tests + 3 linear unit tests pass locally.

The selector keeps adapter and policy layers separated: `linear.rs` handles transport and parsing only; `selector.rs` is pure functions with no I/O. Mode emission is a typed `SelectorMode` enum that the rest of `nancy-live` consumes via `evaluate_with_status`. Wiring through `go.rs` already calls both `fetch_sub_issues` and `fetch_sub_issue_statuses` with the dual-graph contract intact.

Findings below are mostly LOW severity divergences and parity gaps. One MEDIUM concern is that the dual-graph code path is not exercised by any test, so the Rust selector lacks proof that it handles the case where `issue_graph` and `status_graph` differ (which is the production case).

## Per-Issue Findings

### ALP-2241 — Linear graph adapter

**Accuracy and acceptance:**

- Typed structs cover every field the selector consumes (`IssueNode`, `IssueState`, `IssueRelation`, `IssueLabel`, `RelatedIssue`, `IssueGraph`, `ParentIssue`).
- Embeds existing `.gql` files via `include_str!` so the query shape is byte-identical to the Bash oracle (`get_sub_issues.gql`, `get_sub_issue_statuses.gql`, `get_issue.gql`).
- Test `sub_issues_request_preserves_bash_filter_and_variables` (linear.rs:440) verifies the three `["Canceled", "Done", "Duplicate"]` filters and the inverse/relations/children projections.
- Fixture round-trip test (`linear.rs:418`) exercises identifier, title, description, priority label, sort order, state, labels (with parent), inverse relations, forward relations, and children. Matches the audit shape from ALP-2230.

**Findings:**

1. **LOW — `RawParentIssue` discards `priority`, `state.name`, and `labels`** (linear.rs:328-335)
   - `get_issue.gql` selects these fields but `RawParentIssue` only keeps `id`, `identifier`, `title`, `description`. The query and the type are out of sync.
   - Either trim the `.gql` file or extend the parsed struct so the typed contract matches what is actually returned. Currently the type silently drops fields and consumers cannot detect them.

2. **LOW — `compact_query` collapses lines without a separator** (linear.rs:255-257)
   - `query.lines().collect()` joins with no whitespace. Works because the existing `.gql` files keep tokens whole on each line, but is fragile if a future query introduces line-broken identifiers or multi-line strings.
   - Bash `tr -d '\n'` has the same shape, so this is parity-equivalent. Worth a short comment noting the constraint, or a single-space join (`query.lines().collect::<Vec<_>>().join(" ")`) for safety.

3. **LOW — `LinearClient::fetch_sub_issue_statuses` parses with `from_sub_issues_response`** (linear.rs:140-144)
   - The status response is a different (smaller) GraphQL projection but is parsed by the constructor named `from_sub_issues_response`. The parser tolerates missing fields via `#[serde(default)]`, so this works, but the name is misleading. Consider a neutrally named constructor (`IssueGraph::from_response`) used by both paths.

4. **LOW — API key passed via curl `-H` argument** (linear.rs:174-177)
   - `Authorization: $key` lands in the process argv, visible to `ps`. Bash `gql::client::query` (src/gql/index.sh:7-12) has the same exposure, so this is parity-equivalent. Future hardening: pipe the header through a file descriptor (`-H @-`) or `curl --config -`.

### ALP-2242 — Selector decision engine

**Accuracy and acceptance:**

- Mode resolution order matches Bash exactly: `needs_human_direction` → `planning` (open planning or open gate review) → `corrective_resolution` → `post_execution_review` → `execution` → `planning` fallback (selector.rs:269-290 vs selector.sh:94-101).
- Pool selection per mode matches Bash (selector.rs:292-338 vs selector.sh:102-118).
- Blocker release thresholds match: PostExecutionReview requires `Done`; other modes accept `Worker Done` or `Done`; `Canceled` and `Duplicate` always release (selector.rs:604-612 vs selector.sh:28-33).
- Authorized parent and authorized issue ID parsing recognize both `Authorized execution parent:` and `Authorized blocker parent:`, both `Execute:` and `Execute blockers only:` (selector.rs:558-575 vs selector.sh:82-83).
- Output contract emits every field listed in ALP-2230: `selected_mode`, `selected_issue`, `eligibility_reason`, `completion_threshold`, `blocked_candidates`, `unauthorized_backlog_candidates`, `corrective_priority_evidence`, `authorized_parent`, `authorized_issue_ids`, `hierarchy_depth_supported`, `requires_human_direction`.
- All 8 integration tests in `tests/selector.rs` mirror the Python parity tests in `tests/test_linear_selector.py` 1:1 in name, scenario, and assertions.

**Findings:**

5. **MEDIUM — Dual-graph branch (`evaluate_with_status`) has no test coverage** (tests/selector.rs)
   - All selector integration tests call `evaluate(graph)`, which forwards to `evaluate_with_status(graph, graph)` (selector.rs:97-99). The status-graph branch — where `status_graph` includes Done states that `issue_graph` filters out — is never exercised.
   - Production calls `fetch_sub_issues` (filters `Canceled, Done, Duplicate`) and `fetch_sub_issue_statuses` (filters only `Canceled, Duplicate`) and feeds them as different graphs (go.rs:148-152). The very purpose of the split is to surface accepted gate reviews that have moved to `Done` while keeping the selector pool clean.
   - Without a fixture where a `Done` gate review appears in `status_graph` but is filtered out of `issue_graph`, there is no proof that `latest_accepted_gate` and `find_accepted_gate` cooperate correctly. The Bash test file has the same gap, so this is not a regression, but the Rust port is the right place to close it.
   - Recommended: add a fixture with a `Done` gate review whose Outcome line should be parsed, and assert that `selected_mode == Execution` and `authorized_issue_ids` is populated.

6. **LOW — `sub_issue_sort_order` null sentinel diverges from Bash** (selector.rs:489-491)
   - Rust uses `f64::NEG_INFINITY` for missing sort order. Bash `sort_by(.subIssueSortOrder // 0)` uses `0`.
   - With non-negative sort orders (the realistic Linear case), both implementations rank `null` first ascending and last descending — equivalent behavior. With any negative sort order in the same set, ordering diverges.
   - Recommend `unwrap_or(0.0)` for byte-for-byte parity with the oracle. Low risk because Linear sort orders are conventionally positive.

7. **LOW — `final_completion` mode is reserved in Bash but absent from `SelectorMode`** (selector.rs:20-28, selector.sh:30-32, 142-144)
   - Bash's `released` and `blocker_release_states` switch on `post_execution_review OR final_completion`. Rust only checks `PostExecutionReview` (selector.rs:526, 607).
   - Bash never emits `final_completion` from `evaluate`, so the case is dead today, but ALP-2230 documents it as a reserved mode and ALP-2215 plans `CODE_COMPLETE` versus `COMPLETE` semantics that may need it. Without an enum variant, future emission requires touching every match arm.
   - Either add a `FinalCompletion` variant now (with `released` and `blocker_release_states` parity) or drop the reserved case from Bash. Currently the two oracles drift in shape.

## Cross-Issue Notes

- **Adapter / selector boundary is clean.** No GraphQL types leak into `selector.rs`. The selector consumes `IssueGraph` and `IssueNode` only. No filesystem or process work in either module.
- **`evaluate_with_status` dual-graph contract is in place** (selector.rs:101-196) and is invoked from `go.rs:105` and `go.rs:152`. Status graph drives `open_planning`, `open_gate_review`, and `latest_accepted_gate`; issue graph drives `direct`, `children`, `accepted_gate`, and authorized issue lookups. This matches the Bash contract from selector.sh:64-71.
- **Issue ID parsing is permissive but bounded.** `issue_ids` (selector.rs:577-602) extracts every `[A-Z]+-[0-9]+` from the matched line and uses the first for `authorized_parent`. Bash uses a regex capture for the parent and a `scan` for `Execute:`. Both behave identically on the documented description format. If a description ever lists multiple identifiers on the `Authorized execution parent:` line, Rust would return the first one it sees; Bash would only return the captured backtick form. Recommend keeping the documented description shape strict.
- **`unauthorized_backlog_candidates.gate_review_issue` fallback** prefers `gate_review` (a direct issue with the gate-review title) and falls back to `accepted_gate`, matching Bash `(($gate_review.identifier // $accepted_gate.identifier) // "")`. Verified at selector.rs:411-417.
- **Tests run green:** `cargo test -p nancy-live --test selector` passes 8/8; `cargo test -p nancy-live --lib linear` passes 3/3.

## Severity Index

| # | Severity | Issue | File:Line | Sub-issue |
|---|----------|-------|-----------|-----------|
| 5 | MEDIUM   | Dual-graph branch (`evaluate_with_status`) has no fixture covering distinct issue/status graphs | crates/nancy-live/tests/selector.rs | ALP-2254 |
| 6 | LOW      | `sub_issue_sort_order` null sentinel uses `NEG_INFINITY` instead of `0.0` | crates/nancy-live/src/selector.rs:489-491 | ALP-2255 |
| 7 | LOW      | `final_completion` reserved mode not represented in `SelectorMode` enum | crates/nancy-live/src/selector.rs:20-28 | ALP-2256 |
| 1 | LOW      | `RawParentIssue` discards `priority`/`state`/`labels` selected by `get_issue.gql` | crates/nancy-live/src/linear.rs:328-335 | ALP-2257 |
| 2 | LOW      | `compact_query` joins lines without a separator | crates/nancy-live/src/linear.rs:255-257 | not filed (parity-equivalent with Bash) |
| 3 | LOW      | `from_sub_issues_response` is reused to parse status responses, masking schema intent | crates/nancy-live/src/linear.rs:140-144 | not filed (style nit) |
| 4 | LOW      | API key surfaces in process argv via curl `-H` | crates/nancy-live/src/linear.rs:174-177 | not filed (parity-equivalent with `gql::client::query`) |

No HIGH findings. No accuracy regression against the Bash oracle on any covered fixture. The selector and graph adapter are ready to advance; sub-issues track the actionable gaps above.
