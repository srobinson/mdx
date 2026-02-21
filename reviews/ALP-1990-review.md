---
title: ALP-1990 Review — CLI error-string parity with MCP
type: reviews
tags: [backend, review, alp-1990, cm-cli, error-parity]
summary: Divergent path taken. CLI adapters routed through cm_err_to_string via new capability_error helper; parity test added.
status: active
source: backend-engineer
confidence: high
created: 2026-04-22
updated: 2026-04-22
---

## Verdict

**ACCEPT.**

Nancy took the divergent path correctly. The pre-ALP-1990 CLI was silently prepending `"validation error: "` to every `CmError::Validation` via `anyhow!("{e}")` → `CmError` `thiserror` Display, while MCP called `cm_err_to_string()` which returns the raw message. Reviewer 2 was right about the risk; reviewer 3's 581-test pass missed it because the cited `metadata_parity_tests` only compares `cx_store` vs. `cx_update` (MCP-to-MCP), never CLI-to-MCP. Nancy added the missing cross-adapter byte-equality test and it passes.

## Which path was taken

**Divergent.** Evidence:

- New helper `capability_error` centralizes the CLI → `cm_err_to_string` conversion:
  `crates/cm-cli/src/cli/errors.rs:17-19`
- Every CLI capability call now routes through `capability_error`:
  - `crates/cm-cli/src/cli/browse.rs:46,51,85`
  - `crates/cm-cli/src/cli/deposit.rs:73`
  - `crates/cm-cli/src/cli/export.rs:44`
  - `crates/cm-cli/src/cli/forget.rs:28`
  - `crates/cm-cli/src/cli/get.rs:22`
  - `crates/cm-cli/src/cli/recall.rs:40,61`
  - `crates/cm-cli/src/cli/stats.rs:29`
  - `crates/cm-cli/src/cli/update.rs:69`
- MCP `cx_get` harmonised: removed the stray local `get_err_to_string` that was adding a `"Validation error: "` prefix. `cx_get` now uses the canonical `cm_err_to_string` like every other tool:
  `crates/cm-cli/src/mcp/tools/get.rs:8,12`
- Corresponding test expectation updated:
  `crates/cm-cli/tests/mcp_tool_error_test.rs:164` — `"Validation error: ids cannot be empty"` → `"ids cannot be empty"`

Single commit: `ddc34ad nancy[ALP-1990]: Unify CLI and MCP error strings`.

## Acceptance criteria checklist

| Criterion | Status | Evidence |
|---|---|---|
| Convergent OR divergent outcome chosen | PASS | Divergent path taken |
| Route all CLI `CmError` through `cm_err_to_string()` (or equivalent) | PASS | `capability_error` helper wraps `cm_err_to_string`; every CLI adapter uses it |
| Parity test covering store, get, update, browse, recall | PARTIAL (acceptable) | `get`, `update`, `browse`, `recall` covered. `store` omitted because the CLI `cm store` handler is a doc-stub (ALP-1781) and never hits `CmError`. Test overcompensates by also covering `stats`, `deposit`, `forget`, `export` |
| Test asserts byte-equality | PASS | `assert_eq!(cli_error, mcp_error, ...)` in `cli_and_mcp_share_adapter_error_strings` at `crates/cm-cli/tests/tools_integration.rs:47-189` |
| No existing test regresses | PASS | `cargo test --workspace` exit 0, 584 tests pass, 0 fail. `mcp_tool_error_test.rs` was updated to match the harmonised `cx_get` output — intentional, not a regression |
| Fix lives in adapter code, not `cm-capabilities` | PASS | All edits are in `crates/cm-cli/src/cli/` and `crates/cm-cli/src/mcp/tools/get.rs`. `cm-capabilities` untouched |

## Test coverage assessment

The new test is **strong, not lipstick**. Rationale:

1. It calls distinct code paths on each side. CLI enters through `cli::<cap>::run(...)`, MCP through `tools::cx_<cap>(store, &json!(...))`. Both paths converge on the same `cm_capabilities::<cap>` call and the same error render (`cm_err_to_string`), so byte-equality is the right invariant to assert.
2. It hits three distinct `CmError` origin sites per adapter: capability-layer validation (`CmError::Validation`), `ScopePath::parse` (returns a type convertible to `CmError` via `Into`), and the `BrowseScopeMode::FromStr` error. If any one CLI site regresses back to `anyhow!("{e}")` on a `CmError`, `CmError`'s thiserror Display will prepend the variant prefix (`"validation error: "`, `"invalid scope path: "`, etc.) and the assertion will fail.
3. It forces errors via the *real* adapter entry points (`cli::get::run`, `tools::cx_get`), not by directly calling `capability_error` — so the test can catch "adapter stops using the helper" regressions.

One genuine gap: the `browse` capability errors at three different conversion sites (scope_path, scope_mode, cwd, kind, capability). The test only exercises two of them (`scope_path`, `cwd`). Adding a case per conversion site would be nice-to-have, but the existing coverage is load-bearing and non-trivial.

## Surprises and smell

1. **Silent MCP behaviour change on `cx_get` error strings.** `cx_get`'s error for empty `ids` changed from `"Validation error: ids cannot be empty"` to `"ids cannot be empty"`. This is a correct harmonisation — every other `cx_*` tool already emitted the raw message — but it is an externally observable wire change for MCP clients that pattern-match on the prefix. Not called out in the commit message. Low risk (the prefix was an inconsistency, not a contract), but worth noting for release notes.

2. **Residual `anyhow!("{e}")` wraps in the CLI are safe but not uniform.** `browse.rs:64`, `recall.rs:36,46`, `stats.rs:25` still use `anyhow!("{e}")` to wrap `Result<_, String>` from `parse_kind` / `parse_tag_sort` / `check_input_size`. These return `String` directly (not `CmError`), so `"{e}"` produces the same bytes that MCP's `?`-propagation emits. Parity holds, but a follow-up to route these through a single String-aware helper (e.g. `cli_string_error`) would make intent more explicit and make future regressions harder.

3. **`store` capability omitted from test.** Correct decision — the CLI `cm store` is a stub printing a pointer to the Curator UI (`crates/cm-cli/src/cli/store.rs:22-55`) and never touches `CmError`. A brief comment on the test explaining the omission would prevent future reviewers from flagging it as a gap.

4. **Cosmetic drift.** `browse.rs:57` changed `"cwd cannot be empty"` → `"Invalid parameters: cwd cannot be empty"` to match MCP's hardcoded string at `mcp/tools/browse.rs:76`. This is a real parity fix (both sides already hardcoded strings there, this aligns them), but it is orthogonal to the `cm_err_to_string` routing and easy to miss in the commit narrative.

None of these rise to the level of a follow-up issue. File at most a lightweight note.

## Recommendation

Ship it. Verdict: **ACCEPT**. Reviewer 2 / reviewer 3 disagreement is resolved with evidence in favour of reviewer 2. Close ALP-1990 with a pointer to `cli_and_mcp_share_adapter_error_strings` as the standing regression guard.
