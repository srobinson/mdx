# S1 persistence reshape v3 panel review

Date: 2026-07-22  
Proposal baseline: `9ac8d10d2d5304bc579980636729d466e952f404`  
Verdict: **major concern**

## Summary

V3 resolves the prior identity instability. Durable Space membership no longer depends on Git detection, and M4 dissolves cleanly when Canvas ownership moves to the anchor Worktree.

The remaining major flaw is the interaction between M:N Worktree membership and one shared Canvas execution state. A Canvas anchored to one Worktree appears in every Space containing that Worktree, but it has one durable `default_worktree_id` and one browser layout keyed only by `canvas_id`. A default or pane target can be valid in one Space response and cross-Space in another. The proposal simultaneously requires shared Canvas identity and rejection of cross-Space placement, without defining which Space owns execution validity.

The default Space also needs a database enforced single-row invariant before concurrent materialization is safe.

## 1. One shared Canvas has no coherent Space execution boundary

Consider these durable rows:

1. Default Space `D` computes all Worktrees.
2. Named Space `A` links `W1` and `W2`.
3. Named Space `B` links only `W1`.
4. Canvas `C` is anchored to `W1`.
5. `C.default_worktree_id` is `W2`, and one persisted pane has `contentRef.worktreeId=W2`.

The proposal projects `C` into `D`, `A`, and `B`. Its default and pane are valid in `D` and `A`, but invalid in `B`. One Canvas row cannot satisfy the stated rule that defaults and pane targets belong to the same durable Space because the row has no single Space context.

Current browser persistence makes the conflict observable. Canvas layout is cached under `transport-matters-canvas:{canvas_id}`. Terminal and captured run content references persist their Worktree IDs inside that shared cache. Opening the same Canvas through a second Space therefore restores the same execution targets.

Link mutation creates the same problem after placement. Removing `W2` from `A` can make an existing default and pane invalid without changing `C`. Validation only when a pane or default is created cannot preserve the invariant.

The design must choose one execution model before implementation:

1. Make Canvas presentation Space scoped. Persist layout and effective default by `(space_id, canvas_id)`, or add a durable Space to Canvas presentation link.
2. Give each Canvas one owning Space and stop projecting the same Canvas into every Space.
3. Define execution placement by owner plus durable Worktree identity, remove the cross-Space placement rule, and treat Space as a view only.

An intersection rule over every Space containing the anchor is technically possible, but named link changes would invalidate existing panes and defaults. It would also make the usable Worktree set unexpectedly narrow.

## 2. Computed default needs an enforced single-row invariant

The proposed `space` schema has `is_default`, but no owner scoped uniqueness constraint. Two first Worktree materializations can both observe no default and insert separate default Spaces. Computed-all then projects every Worktree into both rows, which produces duplicate default views and ambiguous Space stamps.

Required construction:

1. Add a partial unique index such as `UNIQUE (owner) WHERE is_default`.
2. Ensure the default row and first Worktree inside one database transaction.
3. Use an insert conflict path or owner lock that returns the winning default row.
4. Build each Space aggregate from one database statement or one transaction snapshot so a read racing Worktree creation sees the Worktree in the default or sees neither committed row.
5. Reject materialized junction links to the default Space. Computed membership must have one source.
6. Later Space deletion must forbid removing the only default or atomically elect its replacement.

A partial unique index enforces at most one default. The transaction and deletion policy enforce continued existence while Worktrees exist.

## 3. The detection membership invariant needs a capability boundary

V3 states that reconciliation never writes `space_worktree_link`. S1 can make this true by construction because no link mutator needs to exist yet. The later Space CRUD slice will add one, so a prose ownership rule is insufficient over time.

Required construction:

1. Put junction writes behind a dedicated membership repository used only by Director Space CRUD.
2. Give detection reconciliation a narrower durable Worktree and root repository with no membership method.
3. Forbid `space_worktree_link` SQL outside the membership module with a static boundary test.
4. Capture executed SQL in reconciliation tests and reject insert, update, or delete statements against the junction.
5. Fingerprint all junction rows before and after plain to Git, Git to plain, common directory change, inconclusive classification, concurrent reconcile, rollback, and crash recovery.

Under that boundary, plain to Git reconciliation leaves membership byte-identical. It can only upsert the durable Worktree path identity, ensure the anchored root, and return runtime facts.

## 4. Runtime repository labels no longer own correctness

The deterministic classifier is sound for display grouping under the v3 authority split. Git or path label changes cannot move a Worktree, Canvas, Space link, or historical stamp.

The implementation still needs nominally distinct `SpaceId` and `RepoGroupKey` types, and no request authorization schema should accept `repo_group_key`. Branch, primary, missing, and lifecycle facts remain action inputs. The proposal correctly fails destructive and launch actions closed when enrichment is inconclusive while preserving durable Space membership.

## 5. M4 walkthrough

The M4 transition is dissolved:

1. Materialization creates default Space `S`, Worktree `W`, anchored root `C`, and no default junction row.
2. Named Space links, if any, point to `W`.
3. `git init` changes only `repo_group_key` and projected Git facts.
4. Reconciliation keeps `W`, `C`, descendants, and every named junction row unchanged.
5. Git to plain and common directory replacement also change only runtime labels.

The new linked Worktree policy should remain explicit. A newly reconciled sibling enters the computed default Space and no named Space until the user adds a link. Detection must not inherit the source Worktree's named memberships.

## 6. Junction and deletion requirements

The junction needs exact constraints:

1. `UNIQUE (owner, space_id)` on `space` and `UNIQUE (owner, worktree_id)` on `space_worktree` as composite FK targets.
2. Primary key `(owner, space_id, worktree_id)` for duplicate prevention.
3. `(owner, space_id)` FK with `ON DELETE CASCADE`, so deleting a named Space removes only links.
4. `(owner, worktree_id)` FK with `ON DELETE CASCADE`, so privileged Worktree deletion removes every link.

The privileged Worktree deletion transaction should clear surviving Canvas defaults that reference the Worktree, delete the Worktree, and let the anchor and junction cascades remove its Canvas subtree and links. Deferred reciprocal root validation then observes both the Worktree and protected root gone. A crash or rollback leaves the whole set unchanged.

Deleting a Space must not delete Worktrees or Canvases. Deleting a Worktree may leave a named Space empty, which should be an explicit later CRUD policy.

## Panel answers

1. **Detection never writes membership:** enforceable once reconciliation lacks the membership capability and static plus SQL boundary tests protect the table. The proposal currently states the ownership but should add the construction.
2. **Computed default concurrency:** every Worktree is visible if exactly one default exists and creation commits atomically. The current schema permits two concurrent defaults and needs a partial unique index.
3. **Repository group classifier:** display only under v3. It no longer affects Space authorization or membership if types and request contracts preserve the boundary.
4. **M4 under M:N:** dissolved. Plain to Git changes runtime labels while Worktree, Canvas, default membership, and named links remain stable.
5. **Junction lifecycle:** safe with owner scoped composite targets and cascades. The shared Canvas execution context remains unresolved across multiple linked Spaces.

## Recommendation

Do not implement v3 until the Canvas execution context is selected and the default uniqueness constraint is added. Keep the durable Space, M:N membership, runtime repository label, and Worktree anchored Canvas direction. Those pieces are sound once Canvas layout, defaults, and pane authorization have one unambiguous Space scope.
