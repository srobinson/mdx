# Canvas root model review

Date: 2026-07-22  
Baseline: `feat/multi-launch` at `b094e80d69ad7d57c5bba0ff8f4d71a986a837f2`  
Reference: `/Users/alphab/.mdx/projects/tm-canvas-entity-today.md`  
Scope: design review only

## Verdict

**Adopt with changes.** Adopt one protected Canvas anchor per Worktree and place user Canvases below that anchor. Represent the global Director root as an owner level navigation or control plane container outside the `canvas` table. Keep every persisted Canvas inside one Space.

The proposed literal global Canvas does not fit the current entity contract. `api/src/transport_matters/space/models.py:Canvas` requires `space_id`, and `api/migrations/versions/0006_spaces_foundation.py:upgrade` declares `canvas.space_id NOT NULL` with `canvas_space_fk ON DELETE CASCADE`. A null Space would require weakening the defining Canvas ownership edge. Assigning the Director root to a synthetic Space would make its children cross Space boundaries and would conflict with same Space tree validation.

Recommended hierarchy:

```text
Director container, one per owner, virtual or a separate entity
  Space
    Worktree
      protected Worktree root Canvas
        user Canvas
          user Canvas
```

The biggest risk is coupling structural containment to execution affinity. Current Canvas code deliberately allows panes and launches targeting several Worktrees. The Worktree root should define navigation and lifecycle ownership. It should not require every run on a descendant Canvas to execute in that Worktree.

## 1. Fit with the current model

### Confirmed facts

- `api/src/transport_matters/space/models.py:Canvas` requires `space_id: SpaceId`. It is not nullable.
- `api/migrations/versions/0006_spaces_foundation.py:upgrade` makes `canvas.space_id` `NOT NULL` and references `space(space_id)` through `canvas_space_fk ON DELETE CASCADE`.
- A Canvas without a default Worktree already fits. `Canvas.default_worktree_id` is nullable, and `canvas_default_worktree_fk` uses `ON DELETE SET NULL`.
- `api/src/transport_matters/space/store.py:SpaceStore.list_canvases` scopes Canvas reads by both `space_id` and `owner`.
- `api/src/transport_matters/api/v1/space_routes.py:CanvasSummary` requires a serialized Space ID.
- `api/src/transport_matters/api/v1/space_routes.py:_require_worktree_in_space` enforces same Space defaults at REST. The database FK itself does not enforce that relationship.

### Consequence

The no Worktree part is compatible. The no Space part breaks the current Canvas definition.

A global Director node should be one per owner and should sit above Spaces in the presentation model. If the Director surface must persist its own panes or layout, give it a separate owner scoped entity. Avoid making `canvas.space_id` nullable and avoid manufacturing a special Space that owns unrelated repositories.

Within each Space, Worktree root Canvases remain ordinary durable Canvas identities with additional protection. Their `parent_canvas_id` can be null because the Director and Space levels are composed above the Canvas tree by the server response or client projection.

## 2. Meaning and enforcement of locked

For a protected Worktree root Canvas, user facing CRUD should forbid:

1. hard delete;
2. archive, while that field exists;
3. reparent;
4. rename;
5. clearing or changing its Worktree association;
6. deleting any Canvas subtree that contains it.

The Worktree lifecycle may update its derived display label after a branch or path change. Worktree deletion is the only command allowed to remove the protected root, and that command must own the treatment of its user Canvas descendants.

### Application boundary

Today, `api/src/transport_matters/api/v1/space_routes.py:create_canvas` and `patch_canvas` call `api/src/transport_matters/space/store.py:SpaceStore.create_canvas` and `update_canvas` directly. There is no delete path today. The CRUD foundation should route REST and MCP through one application service and make raw store mutation internal.

That service should:

- reject update or delete when the target is a Worktree root;
- reject reparent across Worktree roots unless a later explicit move command defines that lifecycle;
- inspect the complete subtree under the same tree lock before hard delete and reject when any member is protected;
- prevent user Canvas creation above a protected root;
- serialize root and child mutations with the same owner and Space tree lock.

### Database backstop

Add an explicit reverse reference such as `space_worktree.root_canvas_id`, with these properties:

- `NOT NULL` after backfill;
- `UNIQUE`, so one Canvas cannot anchor two Worktrees;
- a same owner and same Space composite FK to the Canvas scoped key;
- `ON DELETE RESTRICT` or equivalent, so direct deletion and ancestor cascade both fail while the Worktree exists;
- deferred validation where required so a Worktree and its root Canvas can be created in one transaction.

Add a stable Canvas kind such as `worktree_root | user`. `default_worktree_id` must remain separate. It currently means a launch default and has N to optional one cardinality. Reusing it as ownership would allow several roots per Worktree and would let `ON DELETE SET NULL` silently unlock the anchor.

The reverse FK supplies the hard deletion barrier. The application service supplies rename and reparent policy. A database trigger is required only if raw SQL must also be prevented from renaming or reparenting protected rows.

## 3. Cardinality and automatic creation

Current relationships are independent:

- `Space -> Worktree` is 1:N.
- `Space -> Canvas` is 1:N.
- `Canvas -> default Worktree` is N:0..1.

The proposal adds one deliberate relationship:

```text
Worktree -> root Canvas = 1:1, total for every durable Worktree row
```

This coupling is clean when represented explicitly by `root_canvas_id`. It conflicts with the model when inferred from `default_worktree_id` or from names.

### Current automatic creation seam

`api/src/transport_matters/space/store.py:SpaceStore.upsert_detection` is the current authoritative transaction that materializes detected Worktrees. It calls `SpaceStore._upsert_worktree` for every detection. `SpaceStore._ensure_missing_session_worktree` also calls `_upsert_worktree`, so adding root creation only to the outer detection loop would miss durable missing Worktree records.

The shared operation should live at the Worktree persistence boundary used by `_upsert_worktree` and by future explicit Worktree creation. It should create or recover the root in the same database transaction that creates the Worktree.

Race safety requires:

- one durable root Canvas ID stored on the Worktree;
- conflict updates that retain the existing Worktree ID and root Canvas ID;
- uniqueness on `root_canvas_id`;
- an idempotent ensure operation after `INSERT ... ON CONFLICT`;
- concurrency tests matching `api/src/transport_matters/space/test_store.py:test_concurrent_git_first_detection_mints_one_space_without_orphans`.

Define missing semantics explicitly. Current detection marks vanished checkouts `missing` through `SpaceStore._mark_missing_worktrees`; it does not delete them. A missing Worktree should retain its protected root and descendants for history and recovery. Only explicit Worktree deletion should remove them.

## 4. Migration and backfill

### Server data

Use an additive, verified sequence:

1. Add nullable `parent_canvas_id`, Canvas kind, and nullable `space_worktree.root_canvas_id` plus supporting scoped unique keys.
2. Create one protected root Canvas for every existing Worktree, including durable missing Worktrees.
3. Fill every `root_canvas_id` and verify one root per Worktree, one Worktree per protected root, matching owner, and matching Space.
4. Reparent existing user Canvases only when their Worktree can be established safely.
5. Add the self parent FK, root FK, indexes, checks, and `root_canvas_id NOT NULL` after validation.
6. Keep the Director root outside this migration because it is not a Canvas row.

Existing Canvas IDs, names, layout values, and timestamps should survive. Replacing rows would break durable identity and browser cache keys.

### Safe assignment rules

For each existing Canvas:

- A same Space `default_worktree_id` supplies an explicit candidate anchor.
- A Space with exactly one Worktree supplies an unambiguous fallback.
- A null default in a Space with several Worktrees is ambiguous.
- A cross Space default is invalid historical data even though current REST rejects it through `api/src/transport_matters/api/v1/space_routes.py:_require_worktree_in_space`.

Do not assign ambiguous Canvases to the first Worktree. Preserve them in a visible per Space legacy or unassigned bucket, or stop the migration with a report that requires an explicit choice. Remove the temporary bucket only after every Canvas has an owner Worktree.

### Browser state

The database migration cannot migrate the active pane bag. `www/packages/canvas/src/route.ts:defaultCanvasId` currently uses the synthetic key `space:<spaceId>` whenever the URL lacks an explicit Canvas ID. A multi Worktree Space therefore can have one local Canvas cache shared while the default Worktree changes.

Client migration must handle this separately:

- for a one Worktree Space, copy the synthetic key to the protected root or chosen user Canvas UUID and validate before removing the source;
- for a multi Worktree Space, retain the source until the user or a deterministic server mapping chooses one target;
- never copy the same pane bag into every Worktree root;
- never clear the broad Canvas namespace;
- preserve each existing UUID keyed Canvas unchanged.

The synthetic multi Worktree key is the largest data loss risk in the backfill.

## 5. Enforcing at least one Canvas per Worktree

Count the protected Worktree root itself. Then the invariant becomes precise:

```text
Every durable Worktree row has exactly one referenced, same Space root Canvas.
```

`space_worktree.root_canvas_id NOT NULL UNIQUE` plus a scoped FK enforces existence and uniqueness. `ON DELETE RESTRICT` prevents Canvas CRUD and subtree cascade from removing the last Canvas. Worktree creation commits the Worktree and root together. Worktree deletion removes the reference only inside its privileged lifecycle transaction.

If the requirement instead means at least one user Canvas below the protected root, the proposal needs another invariant. Enforce it in the application service by locking the Worktree and root before deleting a last child, and serialize concurrent child deletes. That rule adds little value because the protected root already gives every Worktree a usable Canvas identity. The simpler root counts interpretation is recommended.

## 6. Launch and batch consequences

The structural root must not become an execution prison.

Current behavior explicitly supports per spawn Worktree selection:

- `www/packages/canvas/src/launcher/workdirRows.ts:worktreeRowActions` lets a user drill into agents pinned to a Worktree without changing the Canvas default.
- `www/packages/canvas/src/launcher/templateRows.ts:spawnCommand` carries an optional Worktree target per spawn.
- `www/packages/canvas/src/model/canvasActions.ts:createCapturedRunActions` gives the per spawn Worktree precedence over `defaultWorktreeId`.
- `www/packages/canvas/src/model/canvasState.ts:CanvasStoreActions.addCapturedRun` documents that runs in different Worktrees coexist as isolated panes.
- `www/packages/canvas/src/model/capturedRunStore.ts:CapturedRunState.ensureRun` forwards the selected Worktree through `www/packages/core/src/transport.ts:createCapturedRunView`.

Preserve that behavior. A descendant Canvas may have a home Worktree root for navigation and a default Worktree for convenience, while each run retains its own explicit Worktree identity. `launch_batch` can then place several candidates on one Canvas while targeting different Worktrees.

A rule requiring every run to match the ancestor Worktree would foreclose the current ad hoc multi Worktree launch behavior and would constrain batch candidates unnecessarily. If strict execution isolation is desired later, express it as an explicit Canvas policy with a separate field and versioned launch validation.

The Director container has no default Worktree and should be nonlaunchable. It may aggregate activity across Spaces and navigate into a Canvas. Launch commands require a target Canvas and Worktree.

## Required proof before adoption

1. Migration proves `canvas.space_id` remains nonnull and every root matches its Worktree owner and Space.
2. Concurrent first detection creates one Worktree and one root without orphan rows.
3. `SpaceStore._ensure_missing_session_worktree` also produces one root.
4. REST and MCP both reject protected rename, reparent, archive, and delete through the shared service.
5. Subtree delete rejects any subtree containing a protected root before runtime stop begins.
6. The database root FK rejects a direct protected root delete and an ancestor cascade.
7. Worktree move preserves Worktree ID and root Canvas ID.
8. Worktree delete owns the only privileged root removal path and defines descendant handling.
9. Backfill covers zero, one, and several Worktrees; null, valid, and invalid defaults; and missing Worktrees.
10. Browser migration proves single Worktree key transfer and preserves ambiguous multi Worktree caches.
11. Per spawn Worktree overrides and mixed Worktree batch candidates remain valid below one user Canvas.

## Final recommendation

Adopt the protected Worktree root concept with four locked decisions:

1. Director is an owner scoped container outside the Canvas table.
2. Every durable Worktree owns exactly one protected root Canvas inside its Space.
3. The root counts as the required Canvas.
4. Worktree containment remains separate from per run execution targeting.

This shape preserves the current Space boundary, makes automatic creation and deletion enforceable, provides a data loss safe migration path, and keeps ad hoc multi launch plus `launch_batch` open.
