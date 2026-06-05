# S3 Canvas CRUD review — opus (aggregate / domain / contract + STEP 0 lens)

Reviewer: opus architect, multilaunch warroom.
Target: `git diff 0905622d..50b35bf5` — STEP 0 refactor `544c0174` + Canvas create/update `50b35bf5`.
Spec: `~/.mdx/projects/tm-s3-canvas-crud-spec-v1.md`. Model: cm `019f8a57`.
Gate reported: `just check` + `just test-affected` PASS. Read-only, tree idle @50b35bf5.

## Verdict

**Blockers: 0 · Majors: 0 · Minors: 1 · Builder-trust: TRUST (strong).**

Faithful to the locked spec, correct on every domain invariant, and the STEP 0 refactor is
behavior-preserving and acyclic. The single minor is a documented MCP capability gap.

## STEP 0 refactor — sound, behavior-preserving

- `space/authz.py` (new leaf): `require_director`, `require_bound_space`, `display_name`,
  `rest_director_caller`. Pure, depends only on `models`. Both reads and mutations consume it — the
  back-edge I flagged in the spec is avoided.
- `space/space_mutations.py` (new): the five Space-mutation bodies as free functions;
  `SpaceCrudService` keeps identical method signatures as thin delegators. Every call site intact.
- **`SpaceCrudError` relocated `service.py` → `models.py`** — a genuine leaf improvement beyond the
  brief: the error type no longer forces `import service`. `service.py` still re-exposes it (imports
  from `models`), so `from …service import SpaceCrudError` still resolves for legacy importers; the
  `launch_resolution.py` ripple was updated. `just check` (mypy) passing proves no dangling import.
- Import graph acyclic: `authz ← {service, space_mutations, canvas_commands}`;
  `space_mutations, canvas_commands ← service`; `models ← all`. No `self._require_director` /
  `self.require_bound_space` / `_require_space_record` references remain in `service`.
- `test_reshape_structure.py` extended to assert the boundaries; reconciliation tests split into a
  focused `test_reconciliation.py` (explains the −93 in `test_service.py`). Clean hygiene, no behavior
  change.

## Canvas domain — all invariants correct

1. **Anchor-scoped, never space-scoped.** `CreateCanvasCommand`/`UpdateCanvasCommand` carry no
   `space_id`; create inherits `anchor_worktree_id` from the parent (`insert_user_canvas`); the
   advisory lock is `lock_owner_scope(owner, anchor)` (reuses the `_lock_detection`
   `pg_advisory_xact_lock(hashtextextended(...))` precedent). ✓
2. **Owner-scoped Director authz.** Both commands call `require_director`, never `require_bound_space`;
   all `get_canvas`/`get_worktree` are owner-scoped. REST uses `rest_director_caller`; MCP uses the
   `director=True` owner-scoped caller. ✓
3. **Depth math is correct.** `canvas_ancestry` is a recursive CTE (self→root, `NOT … = ANY(path)`
   cycle guard). Create: new child depth `= len(ancestry) ≤ 32`. Reparent:
   `parent_depth + 1 + _subtree_height ≤ 32`. Both consistent with the read walk's `depth ≤ 32`. ✓
4. **Cycle is triple-guarded.** Service checks `canvas_id in ancestry(new_parent)` → `canvas_cycle`;
   the CTE path array guards recursion; `_subtree_height` has its own visited guard. ✓
5. **Cross-anchor reparent** → service `canvas_root_mismatch` (parent.anchor ≠ canvas.anchor), with
   the composite `canvas_parent_fk` as the DB backstop. ✓
6. **Root immutability** → `require_user_canvas` before AND after the lock, plus `WHERE kind='user'`
   in `store.update_canvas`. ✓
7. **Mutation-response `CanvasRecord`** is stamped with the owner's default Space (the computed-all
   default always contains the anchor), built by running the shared `canvas_records` walk over
   `list_canvases_by_anchor`. Matches the specced sub-decision. ✓
8. **DRY:** the read walk moved to `projection.canvas_records` and is shared by `list_canvases` and
   mutation-record-building — no duplicate walk. `MAX_CANVAS_DEPTH` centralized in `projection`.

## Contract fidelity

- REST: `POST /v1/canvases` (201), `PATCH /v1/canvases/{id}` (200), both origin-guarded, returning
  `CanvasRecord`. ✓
- MCP: `canvas_create`/`canvas_update` via the owner-scoped director path, `CanvasGetResult
  { canvas: CanvasRecord }`. `CanvasRecord` is imported from `space.models` (neutral leaf) — **no
  private cross-adapter import; Space-CRUD blocker #1 does not recur.** ✓
- `@tm/core`: `createCanvas`/`updateCanvas` reuse `requestApiJson`, camelCase bodies. ✓
- **No new error code** (§5): cross-anchor → `canvas_root_mismatch`, cycle/depth/root_locked/
  not_found/invalid_request/forbidden/worktree_not_found all pre-exist; no `status_by_code` change. ✓
- **No new migration**: canvas table + FKs + pair triggers shipped in 0030; Alembic head stays 0030. ✓

## Minor 1 — MCP cannot express `default_worktree_id` clear (contract parity gap)

REST distinguishes set/clear/omit via `model_fields_set` (Pydantic v2 tracks the field name, not the
alias — the engineer got this subtlety right), giving a full `Patch` tri-state. MCP's flat args
(`default_worktree_id: str | None = None`) collapse to set/omit only: `None → Absent`, `value →
Present`. An MCP client therefore cannot **clear** a Canvas default; only REST can.

- Assessment: **sound and defensible.** It is an inherent limitation of a flat MCP arg surface (a
  Patch tri-state needs a sentinel), it is documented (inline comment "Explicit default clearing is
  available through REST"), REST/UI covers clear, and MCP is the automation surface. All reachable
  paths are tested (service set/clear/omit + invalid; REST clear over HTTP; MCP set/omit).
- Disposition: acceptable as-is. Cheap improvement: surface the "clear is REST-only" note in the
  `canvas_update` **tool docstring** (currently only an inline code comment), so MCP consumers see it.
  Not blocking; revisit a sentinel only if automation ever needs to clear a default.

## Forward gate (not a defect in this diff)

`store.py` is now **693 LOC — 7 under the hard 700**. S4 (canvas delete: operation/receipt/member
prims) and S5/S6 (worktree create/move/delete, Git port, lease prims) will pile substantial store
surface on. Mirror the S3 STEP 0 discipline: **S4 should open by splitting `SpaceStore`** into focused
stores (e.g. `space/canvas_store.py` + `space/worktree_store.py`, or a store package) **before**
adding delete/lifecycle prims. Recommend the orchestrator make that split S4's STEP 0. No action on
this slice.

## Builder-trust: TRUST (strong) — delegatable to larger scope

- **Craftsmanship above the brief.** STEP 0 went beyond the ask: relocated `SpaceCrudError` to a leaf,
  consolidated the read walk into `projection` so reads and mutations share one implementation, and
  split reconciliation tests into a focused module. The canvas commands double-read the target after
  taking the lock (TOCTOU), and defend cycles at three layers.
- **Test rigor (red-first, observable end-state).** Every reject asserts the tree is **unchanged via a
  read-back**, not just the raised code. The Patch tri-state is proven at all three levels; the
  depth-32 boundary is asserted via `max(record.depth) == 32`; the write→read HTTP loop includes the
  REST clear path; an MCP tool-schema test pins the registered input contract.
- **Spec + reuse fidelity.** No new migration, no new error code, no cross-adapter private import,
  `CanvasRecord`/`requestApiJson` reused. Naming matches conventions.
- **Shortcuts: none.** The one limitation (MCP clear) is documented, not hidden.

## Gate note

Recommend grok's `just check` + `just test` + `just migration-smoke` confirm no schema delta before
merge (direct proof of the zero-migration claim).
