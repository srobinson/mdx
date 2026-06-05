# S1 review — Canvas+Worktree CRUD foundation (opus, contract/tree/domain-model lens)

PR#316, branch `feat/multi-launch` @ `25f20382` (4 commits over `b094e80d`). Reviewed the diff against `tm-canvas-worktree-crud-spec-v1.md` §15 S1 + locked decisions cm `019f8910`. Read-only; tree pristine throughout.

**Verdict: 0 blockers, 1 major, 3 minors.** S1 is correct and complete for its declared scope (reads + reconciliation + protected roots; no mutations, which are later slices). The one major is a *latent* schema flaw that does not affect S1 behavior but is baked into the 0030 schema S1 ships and will block Slice 6. Cheapest to fix now.

Method note: I ran a targeted DRY/dupe pass on the new surface (fmm + direct reads of the MCP envelope, service, routes) rather than the full `/code-hygiene` whole-repo subagent fan-out, which is disproportionate for a single clean slice. The new surface is DRY-clean (see positives). Say the word if you want the full fan-out.

---

## MAJOR

### M1 — 0030 schema makes Slice-6 worktree+root pair deletion infeasible (latent)
`api/migrations/versions/0030_space_crud_reset.py:_create_final_canvas` / `space_worktree_root_canvas_fk`

Three constraints interact to deadlock the spec's §11 "delete the Worktree row, delete its protected root so user descendants cascade" (one transaction):

- `space_worktree_root_canvas_fk` is `ON DELETE RESTRICT` (deferrable/deferred, proven by `test_root_reference_is_restrict_and_exactly_deferred`). RESTRICT is **not** deferrable in Postgres — it fires immediately. So deleting the root canvas while the worktree still references it errors immediately (`test_root_delete_is_restricted_immediately_even_when_constraint_is_deferred` proves exactly this).
- `canvas_default_worktree_fk` is `ON DELETE SET NULL`. Deleting the worktree row sets the root's `default_worktree_id` to NULL.
- `canvas_kind_shape_ck` requires `kind='worktree_root'` to have `default_worktree_id IS NOT NULL`. CHECK constraints are **not** deferrable. So the SET NULL above violates the CHECK immediately.

Net: deleting the root first → immediate RESTRICT; deleting the worktree first → immediate CHECK violation via SET NULL. No ordering, CTE, or `SET CONSTRAINTS` escapes it (RESTRICT and CHECK both ignore deferral). There is **no test** covering worktree+root pair deletion — the migration suite only proves direct-root-delete-is-restricted, which is the half that works.

Failure scenario: Slice 6 implements `execute_worktree_delete`, its finalization txn attempts to remove the worktree and its protected root, and every path raises `RestrictViolation` or a CHECK violation. The delete lifecycle cannot complete.

Fix (cheap now under break-freely; edit 0030 before more slices build on it): change the root FK to `ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED`. NO ACTION deferred still blocks *direct* root deletion (checked at commit; the service also guards it via `canvas_root_locked`, so the DB is defense-in-depth), while permitting the pair-delete txn to `DELETE canvas (root)` first — deferred, cascading user descendants — then `DELETE space_worktree`, so at commit neither dangling reference exists and the root's `default_worktree_id` is never SET NULL because the root is already gone. Add a pair-deletion test (`delete worktree row + its root in one txn succeeds; direct root delete still blocked`) to lock the invariant before Slice 6.

Confidence: high (traced from Postgres RESTRICT/CHECK non-deferrability, which are documented invariants), but I did not execute it against live Postgres — the recommended pair-deletion test is the empirical proof.

---

## MINOR

### m1 — SpaceCrudService couples to 8 private SpaceStore methods
`api/src/transport_matters/space/service.py` (`reconcile_detection`, `resolve_cwd`, `_resolve_detection_space`, `_materialize_missing_worktree`)

The flagship "one service" reaches into `self._store._upsert_worktree`, `_ensure_worktree_root`, `_find_detection`, `_mark_missing_worktrees`, `_write_cache`, `_claim_git_space`, `_lookup_space_for_detection`, `_insert_space` — eight leading-underscore methods of a different module. `api/CLAUDE.md` module-privacy says non-test code must not use another module's private names. The enforced `test_private_import_boundary.py` is AST-**import**-only and does not inspect attribute access, so the gate is green while the boundary is breached. Fix: promote the reconciliation primitives to public on `SpaceStore` (drop the underscores), or relocate the `reconcile_detection` orchestration into `SpaceStore` behind one public seam the service calls. Low blast radius, mechanical.

### m2 — `director_tree` N+1 over spaces
`api/src/transport_matters/space/service.py:director_tree`

`list_spaces(limit=10_000)` then a `list_canvases` per space, and `list_spaces` itself runs a worktree query per space (scout #18). Unbounded by an owner's space count. It is a presentation aggregation (likely small N), so not urgent, but a single joined read of roots-by-owner would remove the amplification.

### m3 — `_write_cache` stale projection preserved
`api/src/transport_matters/space/service.py:reconcile_detection` → `self._store._write_cache(snapshot)`

Scout #19 flagged the filesystem Space cache has no production reader. It is carried forward here (also reached via a store private, see m1). Under "break freely" it is a candidate for deletion rather than preservation, but it is not S1's charter. Low.

Nano: `_upsert_worktree` mints a fresh `root_canvas_id = CanvasId.new()` on every call and discards it on conflict — one wasted UUID per reconcile of an existing worktree. Trivial.

---

## Positives (evidence for the trust verdict)

- **Twin-client is genuinely one path.** Both `space_routes.py` (lines 201–345) and `space_mcp.py` (lines 121–185) delegate every operation to `SpaceCrudService`. No route-local SQL survives — this resolves the scout's route-local Canvas SQL concern.
- **Provenance seam is exactly per spec.** `_upsert_worktree` inserts `provenance='detected'` and its `ON CONFLICT DO UPDATE` refreshes only observed facts (space_id/path/branch/head/is_primary/missing), never `provenance` or `root_canvas_id` — created rows survive reconciliation unclobbered.
- **Exemplary DRY (consolidation, not duplication).** `mcp_tooling.py:McpToolOutput`/`mcp_tool_result` was extracted as a shared envelope and the *existing* `controlplane_mcp.py` was refactored to consume it (line 30), alongside the new `space_mcp.py`. The 72-line controlplane_mcp diff is that adoption.
- **Guards are enforced in code, not just declared.** `require_user_canvas` raises `canvas_root_locked` for `worktree_root`; `_canvas_records` walks with an active-path set + global visited set + `MAX_CANVAS_DEPTH=32`, raising `canvas_cycle`/`canvas_depth_exceeded`/`canvas_root_mismatch`.
- **≥1-canvas-per-worktree is structural.** `reconcile_detection` calls `_ensure_worktree_root` for every materialized worktree (including missing-worktree materialization); DB enforces via `root_canvas_id NOT NULL` + `canvas_kind_shape_ck`.
- **No-backfill honored.** 0030 drops+recreates; `archived`/`layout`/`layout_version` dropped and asserted disjoint; the touched `session/backfill.py` is a pre-existing session→space resolver with a parameter rename (`space_store`→`space_resolver`), not new backfill/compat machinery.
- **Migration test rigor.** Deferred-FK flags introspected (`confdeltype='r', condeferrable, condeferred`), constraint defs asserted, one-canvas-cannot-anchor-two, restrict-immediate-even-when-deferred, PG17 error-class tolerance.

---

## Builder trust verdict (codex engineer)

High craftsmanship and high spec+reuse fidelity. Twin-client one-path, the provenance preservation seam, the DRY consolidation of the MCP envelope into the existing controlplane path, real (not declared) tree/root guards, honored no-backfill, and constraint-introspection tests all indicate careful, spec-faithful work with no shortcuts. The one real design gap (M1, Slice-6 delete deadlock) is a subtle Postgres RESTRICT/CHECK-non-deferrability interaction that also passed three prior spec-review passes including mine — a shared miss, not a builder cut corner. The service→store private coupling (m1) is a minor boundary slip the enforced gate structurally cannot catch. Net: trustworthy for sizeable delegated scope; fix M1 in 0030 now and add the pair-deletion test before Slice 6.

---

## RE-VERIFY (delta @ d9ac6fee) — CLEAN

**M1 resolved, no regression.** `0030` root FK is now `ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED` (`test_root_reference_is_no_action_and_exactly_deferred` asserts `confdeltype='a'`), plus a deferred `CREATE CONSTRAINT TRIGGER validate_space_worktree_root_pair` on both tables enforcing bidirectional pair integrity at commit. `canvas_kind_shape_ck` and every other canvas-tree constraint are retained (`test_canvas_tree_constraints_and_lookup_index_match_the_final_schema`). Behavior proven: `test_root_first_worktree_pair_delete_commits` (root-first delete of the pair commits to {0,0}); `test_lone_root_delete_is_rejected_when_the_transaction_commits` (RESTRICT/FK violation raised at `commit()`, not immediately — by design; the `SpaceCrudService` `canvas_root_locked` guard remains the immediate protection); `test_user_canvas_cannot_become_a_worktree_root` (trigger user-branch). Normal reconcile ordering (`upsert_worktree` → `ensure_worktree_root` in one txn) satisfies the deferred trigger at commit; no regression.

**m5 resolved.** Reconciliation primitives promoted to public on `SpaceStore` (`upsert_worktree`, `ensure_worktree_root`, `find_detection`, `claim_git_space`, `lookup_space_for_detection`); `SpaceCrudService` has zero `self._store._private` calls (`refactor(space): separate reads from reconciliation`).

**m6 resolved.** `director_tree` now issues one `SpaceStore.list_director_spaces(owner)` returning roots + `child_count`; the per-space `list_canvases` loop is gone. Query-count test added.

**m7 resolved.** `_write_cache` is no longer called in the reconcile path.
