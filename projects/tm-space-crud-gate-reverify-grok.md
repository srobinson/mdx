# Space-CRUD fix re-verify + full gate (Grok)

Date: 2026-07-23  
Fix SHA: `3e3afa08` (`fix(space): close CRUD contract gaps`) on top of `e116ffb6`  
Range reviewed: `e116ffb6..3e3afa08` (11 files, +264/−35)  
Reviewer: `multi-launch:general:1:2.4` (read-only)  
Tree: idle at `3e3afa08`

## Full gate (independent re-run)

| Gate | Result | Content |
|------|--------|---------|
| `just check` | **PASS** | desktop 102; shell format/lint/typecheck; api ruff "All checks passed!" + mypy 676 files "Success" |
| `just test` | **PASS** | JS: desktop 102 + shell 1269 + common 24 + contract 8 + activity 288 (34 skip) + runtime 190 (2 skip) + gateway 21 = **1902** passed / **36** skipped. API: **3412 passed / 0 failed**. Combined **5314 passed / 36 skipped** |
| `just migration-smoke` | **PASS** | **9/9**; `alembic heads` = `0030_space_crud_reset` only |

### Formerly-failing contract tests

| Test | Result |
|------|--------|
| `test_private_import_boundary` | **PASSED** |
| `test_mcp_tool_schemas_are_the_agent_contract` | **PASSED** |

## Fix verification (shape, not just green)

| ID | Requirement | Verdict | Evidence |
|----|-------------|---------|----------|
| A | Neutral shared leaf; no private import from routes | **Y** | New `api/v1/space_contracts.py` with public `SpaceSummary` + `space_summary`. `space_mcp.py` imports `from transport_matters.api.v1.space_contracts import SpaceSummary, space_summary`. Grep: no `_space_summary` import from `space_routes`. Routes also consume the leaf. |
| B | MCP allowlist + plain-object outputSchema | **Y** | `test_controlplane_action_skins` allowlist adds all five `space_*` tools. Existing loop still asserts every tool's `outputSchema.type == "object"` and no combinators. |
| C | U+0000 → invalid_request 400 create+rename REST+MCP | **Y** | `validate_display_name` rejects `"\x00"`. Parity assertions in `test_space_mcp_failures_match_the_rest_error_contract` for `nul_create`/`nul_rename` MCP and REST with identical detail message. |
| D | create/rename fixtures `satisfies SpaceSummary` | **Y** | Shared `emptyNamedSpace` + `satisfies SpaceSummary` on create and rename fixtures in `spaceTransport.test.ts`. |
| E | reconcile preserves named membership | **Y** | `test_reconcile_preserves_named_membership_until_an_explicit_link`: link original → reconcile with newly-detected sibling → junction rows byte-stable (`after == before`) → named list still only original → sibling enrolls only after explicit link. |
| F | REST==MCP invalid-UUID parity | **Y** | Same failure-contract test: `not-a-uuid` space_id / worktree_id on MCP and REST share detail payloads. |
| G | fetchSpaces threads cursor/limit; >50 reachable | **Y** | `FetchSpacesOptions` + query encoding; unit test `limit=100&cursor=…`. Server already pages (`DEFAULT_SPACES_LIMIT` / `MAX_SPACES_LIMIT`). `useSpaces` updated to `() => fetchSpaces()`. |

## Snapshot consistency (list_spaces / count_spaces)

**FIXED (principled).** `list_spaces` now wraps `list_spaces` + `count_spaces` in one connection transaction at `REPEATABLE READ`, so `items` and `showSwitcher` (from `space_count > 1`) share one snapshot. Concurrency test `test_list_spaces_items_and_switcher_share_one_snapshot` inserts a named Space after list returns and before the request completes; response still shows only Default and `showSwitcher=false`. Not a special-case race sleep or dual-read hack: standard snapshot isolation.

## Sign-off

Fix round is correctly shaped for A–G. Full gate green on `3e3afa08`. Ready for Stuart's merge decision from this reviewer's side (still note prior minor: `service.py` near 700 LOC before S3; not re-opened by this fix).
