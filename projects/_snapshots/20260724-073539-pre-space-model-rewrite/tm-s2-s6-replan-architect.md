# S2-S6 reconciled slice map (post-S1-reshape)

Role: domain/contract architect, transport-matters multilaunch warroom.
Date: 2026-07-23
Baseline: `main`/`feat/multi-launch` @ `6453364a` (S1 merged, PR#316).
Model of record: cm `019f8a57` + `~/.mdx/projects/tm-s1-reshape-proposal.md` (v3).
Stale source: `~/.mdx/projects/tm-canvas-worktree-crud-spec-v1.md` §15 (specced against the retired
Space-owns-rows model).
Governing rule: `TLDR.md` "No production, no legacy: break freely" (drop-and-recreate, no shims).

## 0. What actually shipped in S1 (verified against the merged tree)

Read against `api/src/transport_matters/space/{models,store,service,detection}.py` and
`migrations/versions/0030_space_crud_reset.py`:

- Durable `space` (`space_id`, `owner`, `name?`, `is_default`, timestamps; `UNIQUE(owner) WHERE is_default`).
- `space_worktree_link(owner, space_id, worktree_id)` junction, both FKs `ON DELETE CASCADE`, with a
  `validate_named_space_worktree_link()` trigger.
- `worktree_in_space(owner, space_id, worktree_id)` SQL function: the single membership authority
  (`true` for every owner worktree under the computed-all default; link-existence otherwise). Wired into
  every read in `store.py`.
- `space_worktree` durable row with the four runtime columns (`branch_name`/`head_oid`/`is_primary`/
  `missing`) **removed**; `canvas` anchored on `anchor_worktree_id`, **no** `canvas.space_id`.
- Models split: `StoredWorktree`/`ProjectedWorktree`/`WorktreeRecord`, `StoredCanvas`/`Canvas`,
  `space/projection.py`. `SpaceCrudService` exposes **reads + `reconcile_detection` only**.
- `store._upsert_worktree` writes `space_worktree` path identity; it never touches the junction.

**Not built (all of S2-S6 substrate is absent):** no `runtime_resource_claim`, no
`worktree_lifecycle_lease`, no `session_affinity_conflict`, no `space_mutation_operation`, no
`upsert_session_with_affinity`, no session Canvas-stamp columns, no `create_*`/`update_*`/`delete_*`
service methods. **No junction add/remove seam exists anywhere in the space module** — the table,
predicate, and validation trigger are real; membership *mutation* is a reserved stub.

## 1. The reshape deltas that ripple into every downstream slice

| # | Delta | Consequence for S2-S6 |
|---|-------|-----------------------|
| D1 | Canvas anchors on `anchor_worktree_id`, not `canvas.space_id`. | Every tree lock, recursive-CTE walk, subtree read, and "same tree" check re-scopes from `(owner, space_id)` to `(owner, anchor_worktree_id)`. |
| D2 | Worktree membership is M:N; a canvas/worktree lives in many Spaces. | "The Space of X" is no longer a lookup. Consume `worktree_in_space()` for view filtering; use `(owner, anchor_worktree_id)` for tree identity. |
| D3 | A run's/session's Space is no longer derivable from its canvas. | The durable affinity stamp must **explicitly** carry the `SpaceRef` selected at claim time (the reshape kept `space_id` on stamps for exactly this). |
| D4 | `branch/head/primary/missing` are projected (`ProjectedWorktree`), not durable columns. | Primary-delete and missing-launch guards read the **projected** value at action time and **fail closed** when Git enrichment is unavailable. |
| D5 | Detection/reconcile never writes membership (`reconcile_detection` is the sole detection boundary; touches path identity + roots only). | A newly *created* worktree auto-appears in the default Space (computed-all) but joins **no** named Space unless a junction link is added by the (separate) Space-CRUD path. |
| D6 | `repo_group_key` (git common-dir label) is display-only projection, never authority. | Git-observation logic survives but carries no membership/lifecycle/authz weight. |

**Headline finding:** the reshape changed the *substrate* (where canvas/worktree/space live and how
membership is decided). The S2-S6 *features* (atomic claims, delete state machines, Git port) are
substrate-agnostic at their core. **Nothing in S2-S6 is DEAD; every slice is NEEDS-REWORK, and the
rework is re-scoping, not redesign.** Placement/authz is owner-scoped (named Spaces are view filters,
not execution constraints), which in several places *simplifies* the stale spec.

## 2. Per-slice classification (S2-S6)

### S2 — atomic claims, leases, immutable affinity (mig 0031) → **NEEDS-REWORK (moderate)**

Core (claim-before-preparation, preallocated `resource_id`, `RuntimeResourceClaim`, `WorktreeLease`,
pending inventory union, one immutable affinity stamp, `upsert_session_with_affinity`) is
substrate-agnostic and survives.

Rework tied to the model:
- Claim txn step "takes the owner and **Space** tree lock" → **`(owner, anchor_worktree_id)` tree lock**
  (D1). Canvas path/root validation walks by anchor worktree.
- **Drop the space-membership authz** from the claim: placement is owner-scoped (cm `019f8a57`), so the
  stale "verify Space" step collapses to owner + anchor-worktree existence. Simplification.
- Affinity stamp / session columns gain an explicit durable **`space_id` (SpaceRef)** alongside
  `canvas_id`/`canvas_path`/`worktree_path`/`worktree_branch` (D3) — canvas no longer implies Space.
- Missing-launch rejection reads **projected** `missing` at action time, fails closed (D4).
- `RuntimeResourceQuery` canvas enumeration (for delete-guard) enumerates by **anchor worktree** (D1).
- Migration **0031 numbering survives** (0030 is consumed by the reshape); content re-aligns to the
  anchor + M:N shape.

Rides on (shipped): `worktree_in_space`, `space_worktree` row (lease locks it), `ProjectedWorktree`
(projected `missing`/`is_primary`), `reconcile_detection` boundary.
New deps: session table gains the Canvas-stamp column group + `SpaceRef`; the two new claim/lease
tables; the atomic session DB function.

### S3 — Canvas create + update through MCP → **NEEDS-REWORK (light, mechanical)**

Not shipped (no `create_canvas`/`update_canvas` in the service). A store-level `_insert_user_canvas`
primitive already exists (anchor-based), so S3 builds the command/guard/service layer on top.

Rework tied to the model:
- "same **Space** tree" → "same **anchor-worktree** tree"; reparent stays inside the anchor worktree
  root, not the Space (D1).
- Advisory lock `(owner, space_id)` → `(owner, anchor_worktree_id)`; insert inherits
  `anchor_worktree_id` from the parent; no `space_id` written.
- Recursive-CTE ancestry walk (cycle/depth guards) re-scoped to `anchor_worktree_id`.
- `default_worktree_id` still targets any owner worktree (owner-scoped, D2); the stale "cross-Space
  reparent" test class becomes moot (canvas is not in a Space).

Rides on (shipped): `_insert_user_canvas`, `CanvasKind`, anchored canvas constraints.
Assumption to flag: `_insert_user_canvas` is production-intended, not a test-only helper.

### S4 — restart-durable Canvas delete (mig 0032) → **NEEDS-REWORK (moderate)**

Core state machine (prepare/execute/resume, `space_mutation_operation`, per-resource receipts, outbox,
`RunTerminationCoordinator` extraction, atomic cascade finalization, startup reconciler) is
substrate-agnostic and survives.

Rework tied to the model:
- Tree lock + "exact user subtree" read scope by **`anchor_worktree_id`** (D1). Freeze/reject of
  create/reparent/claim keys on the anchor-worktree tree.
- Cascade unchanged in spirit: canvas-delete only ever removes **user** subtrees; the worktree root is
  protected (deferred pair) and deleted only by the S6 privileged path via the anchor FK.
- Depends on S2's runtime-claim inventory to enumerate frozen managed runs/terminals — dependency stands.
- Migration **0032 numbering survives.**

Rides on: S2 claim inventory + termination coordinator; anchored canvas cascade FK (shipped in 0030).

### S5 — provenance-aware Worktree create + move → **NEEDS-REWORK (moderate; one genuinely-new design point)**

Git port (`GitWorktreePort`, extracted `git status --porcelain` digest), durable `created` reservation +
startup recovery, typed create/move, identity-preserving move — substrate-agnostic, survives.

Rework tied to the model:
- **New design point (D5):** creating a `created` worktree writes **only** `space_worktree` + its
  protected root. It auto-appears in the default Space via computed-all; it joins **no named Space**.
  Named-Space membership is an explicit Space-CRUD link op, never written by create/detection. →
  **`create_worktree` should not require a `space_id` param** (old model forced a single mandatory
  `space_id`). *Flag for owner: confirm create takes no Space arg and relies on computed-all.*
- Reconciliation preserving provenance survives (`reconcile_detection` shipped, never writes membership).
- Git grouping is `repo_group_key` projection (D4/D6), not durable columns.

Rides on (shipped): deterministic filesystem classifier in `space/detection.py`, `reconcile_detection`,
`space_worktree` upsert. New: `GitWorktreePort` extraction (from `certification_minting:
require_clean_worktree`), created-reservation operation (reuses the 0032 operation store).

### S6 — Worktree lifecycle + provenance-aware delete → **NEEDS-REWORK (moderate)**

> **>> SUPERSEDED (2026-07-24).** TM does **no** `git worktree` create/delete/move product ops (verified detection-only at `7ffba78b`); domain **"Worktree" = a workdir path-identity TM only OBSERVES** — delete never touches the user's checkout. **Delete** = DB cascade + best-effort run-stop + GC of TM's **own** tier-1 storage under `~/.transport-matters/workspaces/` (PROD always; DEV env-flag preserves). Create/move must be reframed as workdir-record operations, not git subprocess ops. cm: *Delete model = HARD DELETE now (soft-delete deferred) for space/canvas/worktree*; *Delete GCs tier-1 storage: PROD always GC, DEV mode preserves, GC sweeps dangling*. Body below is historical and must not drive implementation.


Deletion gate over S2 leases, pending cancellation (managed + terminal, both checks), detected
de-inventory branch, created dirty-confirmation + `git worktree remove --force` branch, `git_removing`
crash recovery, atomic metadata finalization — substrate-agnostic core survives.

Rework tied to the model:
- Primary-delete-always-fails reads **projected** `is_primary` at action time, fails closed (D4) — not a
  durable column.
- Delete cascades **junction rows**: `space_worktree_link` FKs are `ON DELETE CASCADE` (shipped in
  0030), so deleting the `space_worktree` row removes its links automatically. New obligation vs old
  model, satisfied by FK.
- Delete cascades the **anchored** canvas subtree via the anchor FK (D1), not a Space-scoped cascade.
- Session-stamp survival holds: sessions keep FK-free durable `space_id` + `worktree_id` (D3),
  untouched by delete.

Rides on: S2 leases/claims; projected `is_primary`/`missing`; anchor FK cascade + link cascade (shipped).

### Verdict split (S2-S6)

| Slice | Verdict | Depth |
|-------|---------|-------|
| S2 claims/leases/affinity | NEEDS-REWORK | moderate (+ one simplification: owner-scoped authz) |
| S3 canvas create/update | NEEDS-REWORK | light / mechanical |
| S4 canvas delete | NEEDS-REWORK | moderate |
| S5 worktree create/move | NEEDS-REWORK | moderate (+ new create-membership design point) |
| S6 worktree delete | NEEDS-REWORK | moderate |

**0 survives-as-is, 5 needs-rework, 0 dead.** No feature was invalidated; all rework is substrate
re-scoping (`space_id` → `anchor_worktree_id` / `worktree_in_space`) plus explicit `SpaceRef` on stamps.

## 3. (B) New slice — Space-CRUD (named Spaces + junction references)

The reshape explicitly deferred this and reserved the seams. Draft:

**Deliver:**
- Named Space create (insert `space` with non-null `name`, `is_default=false`), rename, delete.
  Delete of the default Space is rejected (`is_default` guard); deleting a named Space cascades **only**
  its `space_worktree_link` rows (FK `ON DELETE CASCADE`, shipped) — worktrees/canvases survive under the
  computed-all default.
- Add worktree reference: `INSERT INTO space_worktree_link(owner, space_id, worktree_id)`. The shipped
  `validate_named_space_worktree_link()` trigger enforces named-space-only linking (a link into the
  computed-all default is rejected). **No move op** — add/remove references only (per model).
- Remove worktree reference: delete the link row; the worktree stays visible via the default.
- REST + MCP surfaces (`space_create`/`space_rename`/`space_delete`/`space_worktree_link`/
  `space_worktree_unlink`) delegating to `SpaceCrudService`.
- Switcher surfaces Spaces only when `>1` exists (reshape §1).

**Consumes the single authority:** every read/authz/view path already routes through
`worktree_in_space()`; this slice writes the junction that the predicate reads, closing the loop. It must
**not** introduce a second membership path.

**Depends on:** S1 only (shipped junction table + predicate + trigger + `ensure_default_space`).
**Independent of** all runtime machinery (S2/S4/S6). Buildable immediately after S1.

**Reserved-stub reality:** the junction table, predicate, and trigger are shipped; the add/remove link
functions and the `space` insert-named path are **not** — this slice builds them from the reserved seam.

## 4. (C) Sequencing and dependencies

```
S1 (MERGED) ── durable Space + M:N junction + worktree_in_space + anchor canvas + reads/reconcile
   │
   ├─▶ Space-CRUD (NEW) ── junction add/remove + named Space CRUD.  Deps: S1 only.  Parallelizable.
   │
   ├─▶ S3 canvas create/update ── Deps: S1 (anchor canvas + _insert_user_canvas).  Parallelizable.
   │
   ├─▶ S2 claims/leases/affinity ── Deps: S1.  HEAVIEST cross-language.  Gates S4 + S6.
   │        │
   │        ├─▶ S4 canvas delete ── Deps: S2 (claim inventory + coordinator) [+ S3 for user subtrees].
   │        │
   │        └─▶ S6 worktree delete ── Deps: S2 (leases/claims) + S5 (created provenance) + projected is_primary.
   │
   └─▶ S5 worktree create/move ── Deps: S1 (classifier + reconcile) + Git port.  Feeds S6.
```

Recommended order (respecting deps, front-loading the independent/simple work):
1. **Space-CRUD** — smallest, unblocks the whole Director/switcher UX, no runtime coupling.
2. **S3** canvas create/update — light rework, independent of S2.
3. **S2** claims/leases/affinity — heaviest; foundational for both delete slices. Closest review.
4. **S5** worktree create/move — independent of S2/S3; produces `created` worktrees for S6.
5. **S4** canvas delete — after S2.
6. **S6** worktree delete — after S2 + S5.

Steps 1-2 and 3-4 can overlap across panes; 5 can run alongside 2. Only 4 and 6 are hard-gated by S2.

## 5. Assumptions flagged for reconciliation with grok's shipped-seam inventory

1. **Junction add/remove seams are reserved stubs** — no add/remove link function found in the space
   module; Space-CRUD builds them. *Confirm grok found no shipped mutation path.*
2. **`_insert_user_canvas` is production-intended** (anchor-based) — S3 builds on it. *Confirm not
   test-only.*
3. **Session table currently carries FK-free `space_id` + `worktree_id`** post-reshape (0030 did not
   touch `session`; they predate it). S2 assumes it *adds* the Canvas-stamp column group to that
   existing shape. *Confirm the live session column set.*
4. **`require_clean_worktree` still lives at `certification_minting`** for the S5 Git-port extraction.
   *Confirm the reshape did not relocate it.*
5. **`ControlPlaneService.close` termination fanout is unchanged** by the reshape — S4/S6 extract
   `RunTerminationCoordinator` from it. *Confirm.*
6. **`create_worktree` should take no `space_id` param** under computed-all membership (D5). This is a
   design point, not a shipped fact — *owner decision needed.*
7. **`validate_named_space_worktree_link()` rejects links into the computed-all default Space.** Space-CRUD
   add-reference relies on this. *Confirm trigger semantics from grok's read.*
```
