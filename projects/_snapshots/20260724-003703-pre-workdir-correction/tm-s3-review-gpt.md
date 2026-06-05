# S3 Canvas create and update review

## Verdict

**0 blockers, 1 major, 2 minors. Builder trust: HOLD pending the Major.**

Reviewed exact range `0905622d277f6b610db402df4cd241ad61ea41f5..50b35bf534498bdfa06c463defa4ee796d94f3bd` against the locked S3 specification and Context Matters model `019f8a57-c947-7411-8944-be6d9ebfce0f`.

The implementation is architecturally strong. The store to service to REST to MCP to `@tm/core` path is coherent, the transaction locking and tree validation are correctly ordered, and the refactor commit is cleanly isolated. One public MCP input path bypasses the shared failure envelope. Two explicit repository conventions also remain unmet.

## Findings

### Major: malformed MCP default Worktree ids escape the typed failure boundary

[api/src/transport_matters/api/v1/space_mcp.py:164](https://github.com/littleorgans/transport-matters/blob/50b35bf534498bdfa06c463defa4ee796d94f3bd/api/src/transport_matters/api/v1/space_mcp.py#L164)

`canvas_update()` evaluates `_crud_id(default_worktree_id, ...)` while constructing `default_patch`, before calling `_invoke()`. `_crud_id()` raises `SpaceCrudError("invalid_request", ...)`, but `_invoke()` owns the adapter's `SpaceCrudError` to `SpaceCrudFailure` conversion. A malformed non-null `default_worktree_id` therefore escapes the adapter instead of returning the locked typed `invalid_request` result. Other Canvas ids are parsed inside the operation lambda and receive the intended handling.

Focused reproduction:

```text
await adapter.canvas_update(valid_canvas_id, default_worktree_id="bad")
=> uncaught SpaceCrudError: default_worktree_id must be a UUID
```

This breaks the MCP failure contract and REST to MCP error-code parity for malformed update input. Build the `Patch` inside the `_invoke()` operation, or introduce a small presence conversion helper that runs within that boundary. Add a regression asserting a structured MCP `invalid_request` failure for the malformed optional id.

### Minor: default Space resolution is duplicated a third time

[api/src/transport_matters/space/canvas_commands.py:178](https://github.com/littleorgans/transport-matters/blob/50b35bf534498bdfa06c463defa4ee796d94f3bd/api/src/transport_matters/space/canvas_commands.py#L178-L181)

The new mutation-response path repeats `list_spaces(owner, limit=1)`, scans for `is_default`, and raises when absent. The same lookup already exists in `service.py` at lines 90 to 95 and 479 to 482. Current SQL ordering makes all three paths agree, but the repeated policy can drift in ordering assumptions and missing-default behavior. This violates the repository's explicit zero-duplication rule. Extract one lower-level default Space lookup that both service and command boundaries can reuse without creating an import back edge.

### Minor: the new neutral mutation seams lack a fresh-interpreter import regression

[api/src/transport_matters/space/test_reshape_structure.py:83](https://github.com/littleorgans/transport-matters/blob/50b35bf534498bdfa06c463defa4ee796d94f3bd/api/src/transport_matters/space/test_reshape_structure.py#L83-L104)

The structural test imports `authz`, `service`, and `space_mutations` in the pytest process. Collection order can preload packages and conceal a circular import. `LESSONS.md` requires every new neutral seam to have a subprocess import guard. The repository already provides `fresh_import_test_support.assert_fresh_imports`; use it for `transport_matters.space.authz`, `transport_matters.space.space_mutations`, and `transport_matters.space.canvas_commands`.

The current fresh-interpreter probe passed, so this is a missing mandatory regression rather than a present import failure.

## Locked contract review

- STEP 0 is isolated in `544c017489503dd61b1d0087dae999fd719ec787`. The service facade remains stable. `authz.py` is a neutral leaf, mutation modules do not import the service, and `SpaceCrudError` plus `Patch` live in neutral models.
- Create and update derive the immutable anchor, lock on `(owner, anchor_worktree_id)`, then reload mutable state. Reparent ancestry, cycle, and depth validation all execute under the lock.
- The recursive ancestry CTE is owner scoped and cycle guarded. Subtree depth arithmetic is correct for root depth zero and maximum depth 32.
- Cross-anchor reparent is rejected before mutation and backed by the composite `canvas_parent_fk` constraint.
- REST preserves default Worktree omit, set, and clear through `model_fields_set` and `Absent` or `Present`.
- MCP intentionally preserves set and omit. `None` maps to omit, while REST owns explicit clear. This matches the locked brief and MCP test plan.
- Mutation responses select the owner's default Space, rebuild the full anchor tree, and return the projected record. Read-back tests cover depth, path, child count, rename, reparent, and default changes.
- Locked failure codes and REST status mappings are present. REST and MCP share service errors except for the malformed optional MCP id described above.
- `@tm/core` uses the exact methods, encoded paths, camelCase bodies, explicit null transport, and detail-aware error handling.
- `space/store.py` is exactly 693 lines. All changed production files remain within the 700-line limit, and new command functions remain below the function-size threshold.

## Builder trust

**HOLD.** Craftsmanship is otherwise high. The dedicated extraction commit, shared read projection, database constraint backstops, owner scoping, and observable read-back assertions show careful implementation. The malformed MCP input path is a material adapter contract miss and needs correction before unconditional trust.

Test rigor is strong on service behavior, REST shape and status, MCP success and representative parity, store constraints, and core transport. The suite does not include a two-connection Canvas mutation test, so the advisory-lock behavior was verified by code and transaction analysis rather than runtime interleaving. Red-first execution cannot be proven from repository history because production and feature tests landed together in `50b35bf5`; uncommitted red-first work remains possible.

## Verification observed

- `git diff --check 0905622d..50b35bf5`: passed.
- `pnpm --filter @tm/core test -- spaceTransport.test.ts`: exit 0. The package command emitted no summary text.
- Focused malformed-id probe: reproduced the uncaught `SpaceCrudError`, exit 1.
- Fresh-interpreter imports for `authz`, `space_mutations`, `canvas_commands`, and `service`: passed.
- Focused Python selection: 17 cases collected, then all stopped during fixture setup because no Transport Matters test database URL is configured. No test body executed.
- No broad gate was run, per the review directive.
- Review head: `50b35bf534498bdfa06c463defa4ee796d94f3bd`.
- GitHub metadata caveat: `gh pr view` resolves merged PR 317 at an older remote head. The user-specified local full-SHA range is authoritative for this review.
