# Canvas root model review — director + locked-workdir-root (opus)

Date: 2026-07-22
Reviewer: multi-launch opus (read-only)
Baseline: `feat/multi-launch` @ `b094e80d69ad7d57c5bba0ff8f4d71a986a837f2`, tree pristine (only `.serena/` untracked), re-verified after review. No writes.
Reference: `tm-canvas-entity-today.md` (as-built dig, matches my own reads).

## Recommendation

**Adopt with changes.** The per-workdir LOCKED canvas as a guaranteed per-scope tree root is clean and compatible. The GLOBAL SINGLETON DIRECTOR *as a real spaceless canvas row parenting cross-space children* is the incompatible part: it breaks `canvas.space_id NOT NULL`, the `canvas_space_fk` cascade, and — decisively — the just-approved migration `0030_canvas_tree` same-space composite self-FK. Keep the director as a **virtual/presentation root**, not a persisted canvas row.

## Biggest risk

The approved spec's `0030_canvas_tree` adds a composite self-FK `(owner, space_id, parent_canvas_id) -> (owner, space_id, canvas_id) ON DELETE CASCADE` (spec §13.1, §6). This **forbids a cross-space parent edge at the DB layer**: a child's `parent_canvas_id` must resolve to a parent row sharing the child's `(owner, space_id)`. A global director parenting each workdir's per-space locked canvas requires exactly the cross-space parent edges this FK rejects. Adopting the literal proposal therefore **reopens the settled same-space guard** (a locked decision) and forces `canvas.space_id` nullable — a wide blast radius (`SpaceStore.list_canvases` keys every read on `space_id`; `space.store._canvas_from_row`; the composite FK itself cannot include a NULL `space_id`).

## 1. FIT — spaceless top canvas vs FK / NOT NULL

- **`canvas.space_id` is NOT NULL** (`0006_spaces_foundation`, `space.models.Canvas.space_id: SpaceId` required) with `canvas_space_fk -> space(space_id) ON DELETE CASCADE`. A director canvas with "maybe no space" **cannot exist as a canvas row** without either (a) nullable `space_id`, or (b) a synthetic "director Space" singleton in the `space` table. Option (b) pollutes the Space bounded context (Space is the repo-identity container; `SpaceStore._claim_git_space`) with a non-repo row and inherits `space` cascade semantics.
- **Scope granularity mismatch.** Canvas is **Space-scoped**, not workdir-scoped: `canvas.space_id` (NOT NULL) binds it to a Space; `canvas.default_worktree_id` (nullable, `canvas_default_worktree_fk ON DELETE SET NULL`) only *points at* a worktree. A Space owns many worktrees (`Space -> Worktree` 1:N via `space_worktree.space_id`). "One locked canvas per workdir" does not map onto the existing edge: the natural persisted unit is **one locked canvas per Space**, not per Worktree. Per-Worktree would need the locked canvas to *pin* `worktree_id`, but the only worktree edge (`default_worktree_id`) is nullable and `SET NULL`s on worktree delete, so a per-worktree locked root would silently lose its pin on `git worktree remove` (spec §11) — breaking the claimed 1:1.
- **Singleton vs per-Space.** As a real row, the director cannot be a global singleton without breaking the same-space FK for its children. As a *virtual* root it is trivially a singleton. Where it sits relative to Space: **above** Space if virtual; **inside** a synthetic Space if forced into a row.

## 2. LOCKED semantics vs subtree-delete + tree guards

- **No enforcement primitive exists.** The approved tree guards are self-parent, ancestor-cycle, same-space, and depth (spec §6). There is **no "locked/system node" concept**. Enforcing "cannot delete/reparent the locked canvas" needs a NEW discriminator (e.g. `canvas.kind = director|locked|user` or `is_system bool`) plus service-layer rejection in `execute_canvas_delete` and `update_canvas` (reparent). This is additive scope beyond the signed-off spec.
- **Cascade is catastrophic if the lock is bypassed.** `0030`'s self-FK is `ON DELETE CASCADE`. Deleting the director row (if it were a row) cascades **every canvas system-wide**; deleting a workdir's locked canvas cascades **all user canvases in that workdir**. The lock is not cosmetic — it is the only thing standing between subtree-delete and mass data loss. The delete state machine (spec §8) roots at any node and today has nothing that refuses a locked/director target. That guard must be added before Canvas delete ships if this model is adopted.
- **Reparent guards needed both directions:** a user must not reparent a locked canvas out from under its root, and must not reparent any canvas *above* the locked root (which would make the locked/director node a child and invert the tree).

## 3. CARDINALITY + auto-create path

- Today `Space -> Canvas` and `Space -> Worktree` are **independent 1:N** (`tm-canvas-entity-today.md` §4). Coupling workdir->locked-canvas 1:1 is a genuinely new invariant. As a **per-Space** root it is a clean addition (each Space gains a guaranteed root canvas). As a **per-Worktree** root it conflicts with the nullable/`SET NULL` worktree edge (see §1).
- **No canvas auto-create seam exists.** Worktrees auto-materialize through detection: `space.detection.detect_space -> SpaceStore._upsert_worktree` (invoked by detection only). **Canvases have no equivalent** — `SpaceStore.create_canvas` is called only explicitly from `space_routes.create_canvas`. The spec's closest seam is on-demand ("A Space with no Canvas creates one root through the service", §6), not detection-triggered. Auto-creating a locked canvas "when a workdir appears" is **net-new wiring** into either `_upsert_worktree` (detection path) or the space-open path — there is no existing hook. Placing canvas creation inside detection also crosses a boundary (detection is Git observation; minting a canvas is a CRUD mutation) and should route through `SpaceCrudService`, not `_upsert_worktree`.

## 4. Migration / backfill

- **Contradicts the approved 0030 backfill.** Spec §13.1 states existing rows "become roots. No row or layout backfill occurs." This proposal requires an **active data-mutating backfill**: mint the director, mint per-Space locked canvases, and reparent existing canvases (set `parent_canvas_id` from null). That is a different, higher-risk migration than the one signed off.
- **Row creation is additive/safe; reparenting is the risk.** Reparent writes are recoverable in principle (parent was null), but the ordering runs straight into the same-space FK: director-first, then per-Space locked (parent = director) **fails the composite FK** the instant the locked canvas's `space_id` differs from the director's. There is no ordering that satisfies a cross-space parent edge under `0030` as approved. A per-Space locked root with a **virtual** director avoids the backfill entirely for the top tier (director is not persisted) and only reparents within each Space (same `space_id`, FK-safe).
- **Default/ordering for a real director:** unresolved — what `space_id`, what owner, one global vs one per owner. All of these evaporate if the director is virtual.

## 5. Transcript stamp

- **Neutral, slightly heavier.** The durable stamp denormalizes `canvas_path` = ordered `[{canvasId,name}]` root-through-captured (spec §7.2, §13.3), immutable and FK-less. Rooting every path at a director adds a constant director+locked prefix to **every** stamp — longer paths, marginally closer to `MAX_CANVAS_DEPTH = 32` (still ample), redundant prefix on every record. It does not threaten immutability (point-in-time capture is unchanged) and self-description survives canvas deletion regardless. A **virtual** director keeps stamps identical to the signed-off design (paths root at the per-Space locked canvas, which is a real row); a **real** director lengthens every path with a segment whose name can drift as workdirs are renamed/moved.

## 6. Risks + multi-launch / batch

- **Does not foreclose ad-hoc multi-launch or batch.** The opposite: a guaranteed per-workdir root gives `launch_batch` (spec §7.1) a natural canvas home to affine N runs into (via the `canvas_id` live-affinity plane). The director tier is orthogonal to launch. No foreclosure either way.
- **Ranked risks:** (1) same-space composite self-FK forbids the cross-space director edge [BIGGEST]; (2) `space_id NOT NULL` + cascade blocks a spaceless director row; (3) no locked-node guard exists, so subtree-delete can mass-delete via the director/locked root; (4) no canvas auto-create seam — new detection/space-open wiring; (5) backfill contradicts the approved no-backfill `0030`.

## Net

Split the proposal in two. **Adopt** the per-Space (not per-Worktree) LOCKED root canvas: it satisfies the ≥1-canvas minimum, is a real per-space tree root fully compatible with `space_id NOT NULL`, `canvas_space_fk`, and the `0030` same-space self-FK, and gives every space a stable delete-protected root — provided a `kind`/`is_system` discriminator and matching delete/reparent guards are added. **Change** the global director from a persisted spaceless cross-space canvas row to a **virtual/derived presentation root** that aggregates each Space's locked root, so the control-plane "director" tier lives above persistence rather than fighting the same-space FK and `space_id NOT NULL`. If a persisted global director is truly required, it is a deliberate reopening of the same-space guard plus a `space_id` nullability change, and must be escalated as such, not folded in silently.
