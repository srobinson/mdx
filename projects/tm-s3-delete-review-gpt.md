# S3 Delete Review

## Verdict

**CHANGES REQUESTED**

| Severity | Count |
|---|---:|
| Blocker | 0 |
| Major | 2 |
| Minor | 0 |

Builder trust: **MEDIUM**

Review confidence: **HIGH** for the inspected control flow. Per the brief, no gates ran.

## Reviewed range

Branch: `ml/s3-delete`

Range: `df052e6515bc88c036d92ebd9721ab5b93cf5303..f470d163374e3a2fb54191ff256a44642581bcfb`

The range is one commit with 16 changed files, 859 insertions, and 13 deletions. The shared tree was pristine before and after inspection.

## Majors

### M1. A launch can cross the one time run inventory snapshot and survive deletion

`delete_workdir` and `delete_space` resolve the database target, call `_stop_runs` once, then delete the inventory row. No target state transition or coordination barrier prevents a concurrent launch from crossing that sequence.

Evidence:

1. `api/src/transport_matters/space/delete_mutations.py::delete_workdir` at lines 38 to 46 resolves the Workdir, inventories runs once, stops that result, then deletes the row.
2. `api/src/transport_matters/space/delete_mutations.py::delete_space` at lines 57 to 64 has the same one time sequence for a Space.
3. `packages/runtime/src/service/RunManager.ts::createNew` at lines 192 to 259 completes `prepareCapture` and PTY spawn before `register` adds the run to managed inventory.
4. `packages/runtime/src/service/RunManager.ts::list` at lines 287 to 294 sees only entries already present in `this.runs`.
5. `api/src/transport_matters/api/v1/launch_resolution.py::_resolve_launch_worktree` at lines 121 to 139 already rejects a non active Workdir, but delete never moves the target to `deleting`.

Concrete interleaving:

1. Launch resolves an active Workdir and receives a prepared capture.
2. Before `RunManager.register`, delete lists the exact target and sees no run.
3. Delete removes the Workdir or Space row.
4. Launch completes PTY spawn and registers a managed run against deleted authority.

This breaks the core run aware delete guarantee. Exact filtering protects siblings, but the single snapshot does not cover in flight target launches.

Required correction: establish a committed deletion barrier that launch resolution consumes, then close or reject launches already between preparation and registration before the final cascade. Use the existing Worktree lifecycle model or an equivalent shared coordination primitive. Add a controlled concurrency regression with launch paused between preparation and registration. The proof must show the target has no surviving managed run and a sibling remains untouched.

### M2. A concurrent Canvas mutation can recreate the deferred FK reference after the null sweep

The store nulls foreign `canvas.default_worktree_id` values and then deletes the Worktree in one transaction, but no lock coordinates this sequence with Canvas create or update.

Evidence:

1. `api/src/transport_matters/space/store_worktree_ops.py::SpaceStoreWorktreeOps.delete_workdir` at lines 86 to 116 performs the null sweep before `DELETE`.
2. `api/src/transport_matters/space/store_space_ops.py::SpaceStoreSpaceOps.delete_space` at lines 137 to 169 performs the analogous sweep for all target Worktrees.
3. `api/src/transport_matters/space/canvas_commands.py::create_canvas` at lines 43 to 67 locks only the anchor Worktree, validates the selected default Worktree, then inserts the Canvas.
4. `api/src/transport_matters/space/canvas_commands.py::update_canvas` at lines 70 to 106 also locks only the Canvas anchor before changing its default.
5. `api/migrations/versions/0032_space_worktree_ownership.py::_create_canvas` at lines 119 to 123 defines `canvas_default_worktree_fk` as deferred `ON DELETE NO ACTION`.

A concurrent transaction can validate the target, insert or update a foreign Canvas after the delete transaction's null sweep, and commit before the target row is deleted. The delete then reaches commit with a fresh reference and fails the deferred FK check after run stop attempts have already completed.

Required correction: serialize target deletion with every mutation that can add `default_worktree_id`, using a shared target Worktree lock or another database enforced deletion fence. Add a two connection regression that pauses delete after the null sweep and attempts a foreign default mutation. The delete must complete without leaving a fresh reference.

## Blockers

None.

## Minors

None.

## Confirmed properties

1. Exact target filters are passed through `RunManagementPort.list_runs`: Workdir delete supplies only `worktree_id`; Space delete supplies only `space_id`; both include the caller owner.
2. `packages/runtime/src/service/RunManager.ts::list` applies owner, Space, and Worktree filters before returning managed runs.
3. `api/src/transport_matters/space/delete_mutations.py::_stop_runs` attempts every returned run and logs individual termination failures without aborting the database cascade.
4. Both delete commands require Director authority before target lookup. Every lookup and delete is owner scoped. A foreign owner reaches `not_found` before run inventory.
5. Targets are resolved from stored rows. Workdir provenance is checked from the stored record. `created` provenance is rejected for the later disk provisioning slice.
6. The range adds no source directory removal or git worktree removal. Detected Workdir deletion only removes inventory.
7. Run coordination stays in `space/delete_mutations.py`. SQL ownership remains in `store_space_ops.py` and `store_worktree_ops.py`.
8. In the uncontended path, foreign default references are cleared before the N:1 cascade, while anchored Canvas trees cascade with their Worktrees.
9. The persistence regression proves session affinity stamps, transcript IR, and wire IR survive inventory deletion.

## Builder trust

Craftsmanship is strong in decomposition, reuse, owner scoping, provenance enforcement, and adapter parity. The focused 112 line mutation module keeps service and route files below the project limit. Tests cover the linear success path, individual stop failure, owner and role denial, FK cleanup, persistence retention, REST, MCP, and TypeScript transport.

Trust is MEDIUM because the implementation treats both external run inventory and deferred FK cleanup as one time snapshots. The test suite does not exercise either concurrency boundary, and both missed interleavings break explicit delete guarantees.
