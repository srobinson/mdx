# Canvas tree ROOT structure — design pressure test (Grok)

Date: 2026-07-22  
Role: design review (not gate)  
Baseline: `feat/multi-launch` @ `b094e80d69ad7d57c5bba0ff8f4d71a986a837f2`  
Inputs: proposal in bus brief; `/Users/alphab/.mdx/projects/tm-canvas-entity-today.md`; live code  
Checkout: clean tracked tree (`?? .serena/` only, untouched)

## Proposal (restated)

1. One **global** top-level canvas = director / control-plane root, **no workdir**.
2. Every **workdir** = a **LOCKED** canvas, child of that top-level, auto-created; a workdir must contain ≥1 canvas.
3. User canvases nest under the workdir’s locked canvas.

## Recommendation

**adopt-with-changes**

Keep the useful middle layer (per-workdir locked anchor + user canvases under it). **Do not** model a single global no-workdir director as a row in today’s `canvas` table without a deliberate schema inversion.

**Biggest risk:** a global root with no Space/workdir collides with `canvas.space_id NOT NULL` + `canvas_space_fk` and with Space-scoped list/authz; forcing it either nulls the core FK or invents a fake Space and lies about ownership.

---

## 1. FIT — Space scope, nullability, singleton vs per-Space

### As-built facts

| Fact | Symbol / constraint |
| --- | --- |
| Canvas always belongs to a Space | `space.models.Canvas.space_id: SpaceId` (required) |
| DB: `space_id` **NOT NULL** | `0006_spaces_foundation` → table `canvas` |
| FK cascade Space → Canvas | `canvas_space_fk` → `space(space_id)` **ON DELETE CASCADE** |
| Default worktree optional | `default_worktree_id` nullable; `canvas_default_worktree_fk` **ON DELETE SET NULL** |
| List is Space-scoped | `SpaceStore.list_canvases(space_id, owner=…)` |
| Create requires `space_id` | `SpaceStore.create_canvas(space_id, …)` |
| No parent edge | no `parent_canvas_id` on model or table |
| Client default key is **per Space**, not global | `route.defaultCanvasId` → `space:<spaceId>` when no explicit `canvas_id` |
| Client model allows null space (UI only) | `paneRecords.CanvasModel.spaceId: SpaceId \| null` (synthetic / pre-Spaces launch) |
| Control plane does not own Canvas rows | no canvas symbols under `controlplane/` |

### Does a no-workdir / no-space top canvas break FK / NOT NULL?

**Yes, as a normal `canvas` row.**

A durable director with `space_id = NULL` violates `NOT NULL` and cannot reference `canvas_space_fk`. Options and costs:

| Approach | Fits today? | Cost |
| --- | --- | --- |
| A. Null `space_id` only for root | Schema break | New CHECK, nullable FK, rewrite every list/create/patch path, owner-global queries, CASCADE semantics for “orphan” root |
| B. Synthetic “director Space” | Keeps NOT NULL | Fake Space is not a repo; pollutes `SpaceStore.list_spaces`, detection, MCP inventory; deletes cascade all canvases if that Space is removed |
| C. One root **per Space** (parent null) | **Fits** | Not “one global”; forest of Space trees |
| D. Director is **not** a Canvas entity (shell / route / roster) | **Fits** | Product “top” lives in UI/control-plane navigation; durable tree starts at Space or locked worktree canvas |

**Singleton vs per-Space / position relative to Space**

- As-built identity is **owner + Space**, not owner-global canvas.
- Multiple Spaces (multiple repos) are first-class (`space` + `space_git_identity` + N worktrees).
- A **single global** canvas cannot honestly parent locked canvases from **different** Spaces while each child keeps a truthful `space_id` unless the parent is allowed to sit outside Space (A/D) or the product forbids multi-Space under one director tree.

**Position that fits without inversion:**

```text
[Director shell / control plane — NOT canvas table]
        │
        ▼ (navigate)
   Space ──1:N── Worktree
        │
        └──1:N── Canvas (optional parent_canvas_id within same space_id)
                    └── preferred: locked worktree canvas is parent of user canvases
```

Or, if a durable Space root is desired:

```text
Space
 └── Canvas (kind=space_root, parent=null, default_worktree optional)
      └── Canvas (kind=worktree_locked, 1:1 worktree, parent=space_root)
           └── Canvas (kind=user, parent=locked)
```

That is **per-Space forest**, not one global top.

### Client dual authority (still relevant)

Visible IDs today: `route.defaultCanvasId` (`canvas_id` | `space:<spaceId>` | workspace hash | `direct-local`) + `canvasCacheStorage.canvasCacheKey`. Server UUIDs and synthetic keys already diverge. A locked-worktree UUID default must replace `space:<spaceId>` carefully or zombie localStorage namespaces remain (same dual-authority issue as prior CRUD review).

---

## 2. “LOCKED” — CRUD surface and enforcement

Nothing is locked today: only `list` / `create` / `update` (incl. `archived` patch) exist; **no delete** (`SpaceStore` / `space_routes`).

### Suggested lock matrix (if workdir-locked is adopted)

| Op | Locked (workdir) canvas | User canvas | Space root (if any) | Global director-as-row (if forced) |
| --- | --- | --- | --- | --- |
| Create | system only (auto) | yes | system only | system only |
| Rename / label | no (or system sync from path/branch) | yes | maybe | n/a |
| Reparent | **no** (fixed under Space root / null) | yes within same Space + under same locked parent policy | no | no |
| Change `default_worktree_id` | **no** (must equal its worktree) | yes (same-Space worktree) | policy | n/a |
| Archive / hard delete | **no** while worktree exists | yes (with ≥1 invariant) | no while Space live | no |
| Subtree delete from parent | deleting Space root or locked node must **not** cascade-delete locked children via user action; only system when worktree/Space goes | subtree of user nodes only | — | — |

### Enforcement (must be multi-layer)

1. **Role column** (or equivalent): e.g. `canvas_kind` ∈ `{user, worktree_locked, space_root}` — not only a naming convention.
2. **DB**: partial unique on locked row per worktree, e.g. unique `(owner, default_worktree_id)` where `kind = worktree_locked` and `default_worktree_id IS NOT NULL`; CHECK that locked rows have non-null `default_worktree_id`.
3. **Service** (`SpaceCrudService` / store): reject user mutate/delete/reparent of locked; reject parent pointing at locked from another Space or wrong worktree lineage.
4. **Subtree-delete interaction:** user subtree delete must stop at locked boundary (cannot delete locked by deleting a parent user node — locked is parent of users, so user delete is leafward). Danger is **delete Space** (`canvas_space_fk ON DELETE CASCADE`) and **future parent FK ON DELETE CASCADE** from a non-locked parent. Do not put locked nodes under a user-deletable parent.

### What stops deleting a workdir’s locked canvas?

Today: nothing (no delete API). After delete lands: **service reject + DB kind/unique**, and worktree lifecycle owns removal: only when worktree is archived/removed/missing policy runs, system deletes or archives the locked canvas (and then user children per delete policy). Detection path (`SpaceStore._upsert_worktree`) must never orphan the 1:1 without a reconcile step.

---

## 3. CARDINALITY — clean or conflict?

### Today

| Edge | Cardinality | Mechanism |
| --- | --- | --- |
| Space → Worktree | 1:N | `space_worktree.space_id` |
| Space → Canvas | 1:N | `canvas.space_id` |
| Canvas → default Worktree | N:0..1 | nullable `default_worktree_id` |
| Worktree → Canvas | **none** | independent siblings under Space |

Confirmed in dig + `tm-multilaunch-canvas-relationship.md`: schema is **Space-centric**, not workdir-centric. Same worktree can host panes on many canvases; canvases do not own workdirs.

### Proposal couples workdir → locked canvas 1:1

**Clean if explicit; conflict if implicit.**

- **Clean:** add 1:1 via `canvas_kind=worktree_locked` + unique worktree key + auto-create.
- **Conflict with independence:** product currently allows many canvases sharing one default worktree (or none). Locked 1:1 is an **additional** system row, not a ban on extra user canvases — OK if user canvases still N per worktree under the locked parent.
- **Conflict with auto-create path:** `SpaceStore.upsert_detection` / `_upsert_worktree` currently upserts worktrees only; **never** creates canvases. Hidden create on every `refresh=true` list path would couple observation to mutation (scout already warned about MCP inheriting hidden writes).

**Where to auto-create locked canvas:**

| Path | Fit |
| --- | --- |
| Inside `_upsert_worktree` | Strong consistency; grows store; every detection write creates canvas side effects |
| After worktree create in `SpaceCrudService` only | Misses detection-only worktrees until first CRUD touch |
| Explicit `ensure_locked_canvas(worktree_id)` called from both detection reconcile and CRUD | **Best** — one function, two callers, idempotent |

Idempotency: unique constraint makes re-ensure a no-op.

**“Workdir must contain ≥1 canvas”** is then satisfied by the locked row itself (always ≥1 while worktree exists). User-visible “must keep one editable canvas” is a **separate** product rule.

---

## 4. MIGRATION / BACKFILL — data-loss-safe?

Existing rows: flat, no parent, no kind, mix of named canvases; client caches under synthetic ids.

### Safe backfill sketch (per Space, not global)

1. Add nullable `parent_canvas_id` (self-FK), `canvas_kind` default `'user'`.
2. For each `space_worktree` row (non-archived preferred): ensure locked canvas  
   `kind=worktree_locked`, `default_worktree_id=worktree_id`, `parent_canvas_id=NULL` (or Space root), name from path/slug.
3. Reparent existing **user** canvases:
   - If `default_worktree_id` set and locked exists for that worktree → `parent = locked`.
   - Else if Space has primary worktree locked → parent there, or leave `parent=NULL` as Space-level user canvas.
   - **Do not invent a global director row** in this backfill.
4. Preserve `canvas_id`, `layout`, `name`, `archived` — no row delete → **no content loss** of server fields.
5. Client: map old `space:<spaceId>` cache → primary locked or Space root UUID via one-time migration table or redirect; risk is **localStorage orphan**, not server data loss (already dual-authority).

### Unsafe / lossy moves

- Creating one global root and forcing all Spaces’ canvases under it with a single `space_id`.
- `ON DELETE CASCADE` from a user-deletable parent onto locked nodes.
- Overwriting `default_worktree_id` on existing canvases during reparent without product intent.

**Data-loss-safe:** yes for server rows if backfill only adds columns + parents + system locked rows. **Not free** for client cache identity.

---

## 5. “Workdir must contain ≥1 canvas” — enforcement locus

| Layer | Role |
| --- | --- |
| DB | Locked 1:1 unique ⇒ while worktree row exists, locked canvas exists (if ensure is transactional with worktree insert). |
| Delete last **user** canvas | Service: if policy requires a user canvas, block delete when count of non-locked children would hit 0; **or** treat locked as satisfying ≥1 and allow zero user canvases (empty workdir UI). Proposal text is ambiguous — **lock which meaning**. |
| Delete locked | Always block for users; system only on worktree removal. |
| Archive worktree | Policy: archive locked + children vs block. Detection currently forces `archived=false` on rematch (`_upsert_worktree`) — user archive of worktree/canvas can reverse unless intent is separated (scout finding). |

Recommended product reading: **locked row satisfies ≥1**; user canvases may go to zero (empty layout under locked). Stronger “≥1 user canvas” needs an extra counter check on user delete only.

---

## 6. RISKS + multi-launch / batch foreclosure

| Risk | Severity | Notes |
| --- | --- | --- |
| Global root vs `space_id NOT NULL` | **Critical** | Core fit failure |
| Detection auto-create side effects | High | Observation path mutates canvas inventory |
| Subtree delete + locked boundary | High | Must not cascade-stop/delete across worktree locks incorrectly |
| Dual client/server canvas ids | High | `route.defaultCanvasId` / localStorage |
| Cross-Space tree under one director | High | Breaks Space cascade and owner inventory |
| Kind/role without DB unique | Medium | Two locked rows per worktree under races |
| Control plane “director” ≠ Canvas | Medium | `ControlPlaneService` has no canvas model; conflating names confuses MCP tools |
| Multi-launch / batch | Low foreclosure | Many panes per user canvas still works; batch launch still worktree-scoped. Tree adds hierarchy of **layouts**, not a ban on multi-pane or multi-run. Risk is UX (pane tree vs canvas tree), not hard foreclosure. |

**Does not foreclose** ad-hoc multi-launch (multiple captured-run panes) or batch, provided launches still resolve `worktreeId` / cwd as today (`launch_resolution.resolve_run_worktree`, `RunManager` filters by worktree, not canvas).

---

## Assess table (brief answers)

| # | Question | Answer |
| --- | --- | --- |
| 1 | FIT | Global no-space top **breaks** `space_id NOT NULL` / `canvas_space_fk`. Prefer director-as-shell or **per-Space** root. `default_worktree_id` may stay null on roots; locked must set it. |
| 2 | LOCKED | Need `canvas_kind` + unique worktree + service denies; subtree delete must not treat locked as user-deletable; system unlinks on worktree lifecycle. |
| 3 | CARDINALITY | Independent 1:N today; 1:1 locked is additive and clean if ensure is idempotent; create via shared `ensure_locked_canvas`, not only hidden detection. |
| 4 | MIGRATION | Column add + locked ensure + reparent by `default_worktree_id` is server-safe; skip global root; client cache migration separate. |
| 5 | ≥1 canvas | Enforce via locked 1:1; clarify whether user count may be zero. |
| 6 | RISKS | Biggest: Space-scoped model vs global director row. Multi-launch/batch not foreclosed. |

---

## Adopt-with-changes (concrete)

1. **Reject** durable **one global** top-level canvas with no workdir inside `canvas` as currently constrained.
2. **Adopt** per-**Worktree** locked canvas (1:1), auto-ensured, same `space_id` as worktree, `default_worktree_id` pinned.
3. **Adopt** user canvases with `parent_canvas_id` → locked (same Space); cycle/same-space guards as prior CRUD review.
4. **Director / control-plane root:** keep as **shell navigation** (or optional per-Space `space_root` canvas), not a cross-Space canvas row.
5. **Optional later:** owner-global “home” UI that lists Spaces/worktrees without being a parent FK target of all locked canvases.

---

## Sign-off line (for bus)

**adopt-with-changes** — biggest risk: global no-workdir director row vs `canvas.space_id NOT NULL` / Space-scoped inventory and CASCADE.
