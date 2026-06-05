# S3 fix re-verify + full gate (Grok)

Date: 2026-07-23  
Fix SHA: `28165a67` (`fix(space): preserve typed Canvas MCP failures`) on `50b35bf5`  
Range: `50b35bf5..28165a67` (7 files, +73/−23)  
Reviewer: `multi-launch:general:1:2.4` (read-only)

## Full gate (independent)

| Gate | Result | Content |
|------|--------|---------|
| `just check` | **PASS** | desktop 102; shell clean; api ruff + mypy 681 "Success" |
| `just test` | **PASS** | JS **1906** passed / **36** skipped + API **3434** passed / 0 failed = **5340 passed / 36 skipped** |
| `just migration-smoke` | **PASS** | **9/9**; head `0030_space_crud_reset` |

## Fix shapes A–D

| ID | Verdict | Evidence |
|----|---------|----------|
| **A** [MAJOR] | **Y** | `default_worktree_id` parse moved into lambda body via `_default_worktree_patch` → executes only when `_invoke` runs the operation inside its `try`. Malformed non-null id raises `SpaceCrudError("invalid_request")` inside the envelope. Regression in `test_canvas_mcp_mutations_share_the_owner_scoped_service_and_rest_cont`: live `session.call_tool("canvas_update", {canvas_id: valid, default_worktree_id: "bad"})` → `isError` + structured `failure.detail == {code: invalid_request, message: default_worktree_id must be a UUID}` — full MCP path, not a shallow mock. |
| **B** [DRY] | **Y** (true single-authority) | Sole implementation: `authz.require_default_space`. Call sites: `service.resolve_cwd`, `service._default_caller`, `canvas_commands._canvas_record`. Grep shows no residual `list_spaces`+`is_default` lookup elsewhere under `space/`. `SpaceStore` is TYPE_CHECKING-only in `authz` (no runtime import cycle; store/service import authz, not the reverse). |
| **C** [LESSONS] | **Y** | `test_space_neutral_seams_import_in_fresh_interpreters` uses `assert_fresh_imports` for `authz`, `space_mutations`, `canvas_commands`. |
| **D** [doc] | **Y** | Tool docstring: "Clearing is REST only." Agent-contract assert: `"REST only" in tools["canvas_update"]["description"]`. |

## Sign-off

Fix round correctly shaped. Full gate green. Ready for Stuart merge from this reviewer's side (prior minor on `store.py` 693 LOC before S4–S6 remains advisory, not reopened by this fix).
