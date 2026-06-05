# S3-delete PR2 review — Opus (Anthropic-family MoE vote)

- **Range:** `git diff df052e65..f470d163` on `ml/s3-delete` (16 files, +859 / −13)
- **Lens:** persistence safety + cascade correctness + IR retention (+ placement/DRY, null-first, builder-trust)
- **Tree:** pristine before verdict (`git status --short` empty)
- **Authority:** cm 019f9297 (provenance-keyed delete: DETECTED de-inventory only; CREATED disk-cleanup deferred), 019f9016 (delete/GC), plus PR1 m1 forward-note (null-first for `canvas_default_worktree_fk` ON DELETE NO ACTION DEFERRABLE)

## Verdict: APPROVE — 0 blockers / 0 majors / 2 minors. Builder-trust: HIGH.

---

## Lens 1 — IR retention ✓ (CRITICAL, clean, tested)

- `test_delete.py::test_inventory_delete_preserves_session_wire_transcript_ir_and_affinity` inserts a `session` row carrying the S1 affinity stamps (`space_id`, `worktree_id`, `canvas_id`, `canvas_path`, `worktree_path`), an `event` row (transcript IR), and a `wire_exchange` row, runs `delete_space`, then asserts **all three survive with the affinity columns byte-intact** as tombstones. This is exactly the critical property the brief demanded.
- Mechanism confirmed: the only DELETE/UPDATE the cascade issues is `SpaceStoreSpaceOps.delete_space` (null foreign-canvas default → `DELETE FROM space`) and `SpaceStoreWorktreeOps.delete_workdir` (null foreign default → `DELETE FROM space_worktree`). Cascade flows `space → space_worktree → canvas` via the inventory FKs only. `session`/`event`/`wire_exchange` hold **no FK into inventory** (S1 stamps are FK-free `uuid`/`text`), so nothing reaches IR. No delete path touches message/block/artifact rows.

## Lens 2 — Cascade correctness ✓

- `delete_workdir`: removes the anchored canvas subtree via `canvas_anchor_worktree_fk … ON DELETE CASCADE`. `test_delete_workdir_stops_every_run_cascades_canvas_and_preserves_disk` builds a child canvas and asserts `{spaces:1, worktrees:0, canvases:0}` — subtree gone, sibling space preserved, disk preserved (`path.is_dir()`).
- `delete_space`: cascades every owned workdir → its canvases. `test_delete_space_stops_space_runs_and_cascades_all_owned_inventory` asserts `{spaces:0, worktrees:0, canvases:0}` across two workdirs. No orphans, no over-broad deletion (owner + space scoped WHERE).

## Lens 3 — Placement / DRY ✓ (one authority, no forked path)

- Row deletion lives in the STEP-0 store modules: `SpaceStoreWorktreeOps.delete_workdir`, `SpaceStoreSpaceOps.delete_space` (pure SQL).
- Run coordination + provenance guard live in the new `space/delete_mutations.py` service module (`delete_workdir`/`delete_space` → `require_director` → `_require_detected` → `_stop_runs` → `store.delete_*` inside `conn.transaction()`). `SpaceCrudService` is a thin facade delegating to it. **No delete SQL in the service, no run logic in the store.**
- `test_reshape_structure.py` extended to lock the boundary: asserts `delete_mutations.delete_space`/`delete_workdir` are the callable authority, the service exposes both facades, and `delete_mutations` imports fresh. No parallel delete implementation anywhere.
- **Contract parity verified:** the hand-rolled `FakeRunManagement` mirrors the real `controlplane.activity.RunManagementPort` Protocol exactly (`create_run`, `list_runs(*, owner, space_id, worktree_id)`, `terminate_run(run_id, *, owner)` — the #320 typed port). No signature drift that would let tests pass while production breaks. `main.py` wires `app.state.run_management = proxy_mount.control_plane_gateway` (or `None` when no gateway); routes + MCP both read it via `getattr(..., "run_management", None)`.

## Lens 4 — default_worktree_id null-first ✓ (honors PR1 m1)

- Both store methods **null foreign canvas defaults before the delete**, precisely honoring PR1's forward-note (the FK is `ON DELETE NO ACTION DEFERRABLE`, so a foreign canvas defaulting to a deleted worktree would otherwise raise). The null-first WHERE deliberately excludes the anchored canvases being cascaded (`anchor <> worktree` / `anchor NOT IN target_worktrees`), so it only clears *foreign* defaults.
- `test_delete_workdir_clears_foreign_canvas_default_before_cascade`: canvas anchored in workdir A defaults to workdir B; delete B succeeds; A's default is cleared to NULL. Directly tested.

## Run-stop semantics (design, sound)

- Deliberate asymmetry, correctly tested: `list_runs` failure **raises** `control_plane_unavailable` (abort before deleting — never delete inventory while unable to confirm runs), while an individual `terminate_run` failure is **swallowed with a warning** (a stuck run must not wedge deletion). `test_delete_workdir_stops_every_run…` exercises a terminate failure (`run-fails`) and asserts deletion still proceeds. Runs are stopped before the DB transaction opens; runs are process-resident, so a stopped-run-without-delete window is benign.
- Authz/owner scoping tested: observer → `forbidden`, foreign director → `space_not_found`, and inventory survives the rejected calls (`test_inventory_delete_is_director_and_owner_scoped`).
- Provenance scope respected: `_require_detected` blocks `created` deletion with `worktree_provenance_unsupported` (409), deferring disk-provisioning to the later slice; `test_created_workdir_delete_waits_for_disk_provisioning_slice` locks it.

## Minors

- **m1 (design, low):** `_require_run_management` returns 503 `control_plane_unavailable` whenever `app.state.run_management is None` (no-gateway install). But a no-gateway process serves zero runs, so there is definitionally nothing to stop — inventory delete is nonetheless impossible there. Fail-closed and safe, but arguably over-strict; consider allowing delete (empty run set) when the run plane is absent. Optional, not blocking.
- **m2 (test-gap, low):** `_require_detected` is shared, but only the `delete_workdir` created-path is tested. A `delete_space`-with-one-`created`-child test would lock the space-level all-or-nothing guard (a space is currently undeletable if *any* member workdir is `created`). Low risk given the shared guard; worth a line.

## Builder-trust verdict (codex build): HIGH

- **Craftsmanship:** clean layering (SQL in STEP-0 store, coordination in a dedicated mutation module, thin service facade); null-first honored per PR1's forward-note; deliberate list-vs-terminate failure asymmetry; owner/director/provenance guards all in place.
- **Test rigor:** strong — 6 focused DB tests covering the exact critical property (IR + affinity survives), foreign-default null-first, full space cascade, terminate-failure resilience, authz/owner scoping, and provenance deferral. The `FakeRunManagement` spy asserts call shape (`list_calls`/`terminate_calls`) not just outcomes.
- **Spec + reuse fidelity:** faithful to 019f9297 (detected-only, created deferred) and to PR1's reshape; reuses the #320 `RunManagementPort` rather than inventing a run API; extends the existing structural guard test.
- **Shortcuts:** none detected. No delete SQL leaked into the service, no forked path, Fake matches the real Protocol, MCP + REST + TS transport all wired symmetrically (`worktree_delete`/`space_delete`, `DELETE /worktrees|/spaces/{id}` → 204, `deleteWorkdir`/`deleteSpace` via `requestApiVoid`).
