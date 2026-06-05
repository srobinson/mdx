# S1 persistence reshape proposal

Date: 2026-07-22  
Baseline: `9ac8d10d2d5304bc579980636729d466e952f404`  
Status: proposal for approval. No repository code changed.

## Decision

Keep `space` as the durable owner scoped UUID and metadata registry. Build each current
Space aggregate at read time from live detection plus durable path identities. A Space row
no longer owns Worktree or Canvas rows.

Anchor each durable Canvas tree to one durable Worktree. Replace the persisted Space edge on
both `space_worktree` and `canvas` with `canvas.anchor_worktree_id`. Git grouping then becomes
a runtime property. A plain directory can become a Git repository without moving any
Worktree or Canvas row.

The resulting ownership is:

```text
durable
owner
  Worktree path identity
    protected root Canvas
      user Canvas tree

runtime projection
DetectedSpace
  current Space identity claim
  detected Worktrees
  Canvas trees anchored to those Worktrees
```

## 1. Schema delta

### `space`

Retain the table and stable `space_id`. Its remaining responsibilities are stable UUID,
owner scoped metadata, archival policy, and point in time references from sessions and run
facts. Current membership is absent from this table.

Add `UNIQUE (owner, space_id)` as the scoped target for identity claims.

Generalize `space_git_identity` into `space_identity_claim`:

```text
space_identity_claim {
  owner
  kind: git | path
  identity_key
  space_id
  created_at
}

UNIQUE (owner, kind, identity_key)
FK (owner, space_id) -> space(owner, space_id)
```

For Git, `identity_key` is the existing `repo_instance_key`. For a path fallback, it is the
durable Worktree UUID. Reconciliation creates one path claim with every Worktree and one Git
claim for each observed repository. The path claim supplies a stable singleton Space when a
directory is plain, missing, or no longer observable through a live Git sibling. Projection
chooses the Git claim whenever live detection proves Git membership. Claims never move.

This registry preserves minted UUIDs and concurrent claim behavior. `git_common_dir` and
`detected_at` are live observation data and can leave persistence.

### `space_worktree`

Drop:

1. `space_id`
2. `branch_name`
3. `head_oid`
4. `is_primary`
5. `missing`

Keep:

1. `worktree_id`, `owner`, `path`, `workspace_slug`, `workspace_hash`
2. `root_canvas_id`
3. `provenance`
4. `lifecycle_state`, `lifecycle_generation`
5. `created_at`, `updated_at`

The unique path and workspace identity constraints remain. Detection upsert can create a
path identity and may refresh canonical path identity fields. It cannot write Git facts or a
Space membership edge. Explicit Worktree move retains ownership of path mutation in the
later CRUD slice.

### `canvas`

Drop `space_id`. Add `anchor_worktree_id uuid NOT NULL` to every Canvas row.

The protected root uses its Worktree as the anchor. Every descendant inherits the same
anchor. Use the following constraints:

1. `UNIQUE (owner, anchor_worktree_id, canvas_id)` for scoped parent references.
2. `UNIQUE (owner, worktree_id)` on `space_worktree` for scoped Canvas references.
3. Parent FK `(owner, anchor_worktree_id, parent_canvas_id)` back to `canvas`, with the
   existing user subtree cascade.
4. Worktree root FK `(owner, worktree_id, root_canvas_id)` to
   `canvas(owner, anchor_worktree_id, canvas_id)`, deferred for pair creation.
5. Scoped `anchor_worktree_id` FK to `space_worktree`, with subtree cascade during the
   privileged Worktree deletion transaction.
6. Scoped `default_worktree_id` FK to `space_worktree`, using deferred `NO ACTION`.
   Worktree deletion clears surviving user Canvas defaults explicitly before commit.
7. The existing root versus user shape check and root protection rules.

The deferred pair trigger becomes smaller. For a Worktree row, the referenced Canvas must
have `kind=worktree_root`, `anchor_worktree_id=worktree_id`, and
`default_worktree_id=worktree_id`. For a protected root Canvas, the reciprocal Worktree must
name that Canvas as `root_canvas_id`. A user Canvas can never satisfy the pair.

`canvas.default_worktree_id` remains a durable launch preference. It does not define tree
ownership. Root rows keep the pinned value required by the pair trigger. A user Canvas may
choose another durable Worktree while both Worktrees are members of the same current
projection.

Membership can change after that preference is stored. Reads expose the stored default only
while live projection places it in the Canvas anchor's current Space. Otherwise the effective
default falls back to `anchor_worktree_id`, without rewriting the row. Runtime claim and
launch paths validate membership again at action time. Canvas mutation validates a new
default against the same current projection.

Root names should come from the durable path basename or workspace slug at creation. Branch
changes remain visible through the projected Worktree record and do not rename a durable
Canvas.

### Durable history

Leave session and run lifecycle Space, Worktree, and Canvas stamps unchanged and FK free.
They record the projection used at claim time. An older session may therefore retain the
plain Space UUID after the path becomes a member of a Git Space. That is correct historical
truth.

## 2. Model boundary

Split persisted and projected models so persistence cannot accidentally regain authority:

1. A stored Worktree model contains only the retained `space_worktree` columns.
2. A projected Worktree model, used by `WorktreeRecord`, adds `space_id`, branch, HEAD,
   primary, and missing from `DetectedWorktree`.
3. A stored Canvas contains `anchor_worktree_id`. `CanvasRecord.space_id` remains an API
   projection for current clients.
4. `SpaceSnapshot` becomes a projected aggregate assembled by the service. Store methods
   return durable rows and identity claims only.

Place projection in a focused module such as `space/projection.py`. `store.py` is already
661 lines, so adding projection there would cross the repository limit during later slices.

## 3. Read time projection

Build one owner scoped projection index per service operation:

1. Load the owner's durable Worktree identities and Space identity claims.
2. Run `detect_space` for existing paths. Once one path returns a Git group, mark every path
   in that detection as covered so the repository is detected once.
3. Match `DetectedWorktree` entries to durable rows by canonical path, with workspace
   slug/hash as the identity cross check.
4. Attach durable rows observed in one `DetectedSpace` to that Space's Git identity claim.
5. Attach each remaining plain or unobservable row to its immutable path identity claim.
   A detected plain row uses the facts in its `DetectedWorktree`. An unobservable row
   projects `missing=true`; branch and HEAD are null; primary is false.
6. Exclude detected paths without a durable Worktree row. Explicit reconciliation creates
   their identity and protected root.
7. Join Canvas trees by `anchor_worktree_id` after the Worktree groups are known.
8. Sort and paginate the projected Space groups after grouping.

This index serves `list_spaces`, `get_space_snapshot`, Worktree list/get, Canvas list/get,
the Director tree, workspace caller resolution, and launch resolution. One operation uses
one index, which keeps authorization and response projection coherent.

Reads perform no inserts or updates. If a detection group has no identity claim, a
noncreating resolve returns absent and ordinary reads fail closed with
`space_identity_missing`. Director reconciliation owns claim creation.

The current MCP `refresh` flag should be removed. Every read already refreshes runtime
facts. `POST /spaces/{id}/worktrees/reconcile` remains the explicit mutation surface and
retains Director and origin checks.

## 4. Reconciliation

`reconcile_detection` remains the sole write boundary for detection:

1. Lock the owner plus detection identity.
2. Upsert durable Worktree path identities only.
3. Create the immutable path Space claim for each new Worktree.
4. Claim the Git Space identity when detection reports a repository.
5. Ensure the Worktree and protected root pair using `anchor_worktree_id`.
6. Return a projection assembled from the supplied detection and the durable rows created
   in the transaction.

Delete `mark_missing_worktrees`. Reconciliation never stores branch, HEAD, primary, missing,
or current Space membership. Root ensure is idempotent and leaves an existing root name and
Canvas subtree unchanged.

## 5. Plain to Git walkthrough

1. Resolving a missing or plain path creates Worktree `W`, protected root Canvas `C`, and
   path Space claim `P`. `C.anchor_worktree_id=W` and `W.root_canvas_id=C`.
2. The user runs `git init` at the same path.
3. Detection returns a Git identity plus a `DetectedWorktree` for that path.
4. Reconciliation claims Git Space `G`, finds `W` by its path identity, and confirms the
   existing `W` to `C` pair. No persisted membership changes.
5. The returned projection reports `W.space_id=G`, current Git facts, and
   `C.space_id=G`.
6. `P` remains available for older session stamps. New claims stamp `G`. Worktree `W`, root
   `C`, every descendant Canvas, and their durable IDs remain unchanged.

The former M4 rollback path disappears because there is no Worktree Space update and no
Canvas Space FK to conflict with it. Git to plain follows the same mechanism in reverse and
selects `P` on the next read.

## 6. Required proof

The implementation should prove:

1. Migration 0030 installs the reduced Worktree row, Worktree anchored Canvas tree, scoped
   parent FK, and reciprocal root trigger.
2. Direct root deletion, user Canvas as root, swapped roots, wrong anchors, and cross anchor
   reparent all fail.
3. Branch, HEAD, primary, and missing changes appear on reads without changing durable row
   bytes or timestamps.
4. Observer reads execute no write statements. Reconcile remains Director only.
5. A newly detected Git worktree remains absent from public inventory until reconcile, then
   receives one Worktree ID and one protected root under concurrency.
6. Missing linked Worktrees stay in their Git Space while any live sibling reports them.
   With no live Git evidence, they use their path Space and project missing.
7. Plain or missing path to `git init` preserves Worktree ID, root Canvas ID, user subtree,
   provenance, lifecycle, and prior session stamps while changing the current projected
   Space.
8. A sibling Worktree default remains effective while membership matches. Membership drift
   falls back to the anchor without a persistence write, and launch revalidates.
9. REST and MCP continue to emit the same projected Worktree and Canvas JSON contracts.
10. `just check`, `just test`, and migration smoke pass against Postgres.

## 7. Estimated implementation surface

Approximately 40 production symbols across:

1. `0030_space_crud_reset` schema, downgrade, and pair validation.
2. `space/models.py` persisted versus projected records.
3. `space/store.py` identity claims and durable row reads/writes.
4. New `space/projection.py` projection index and pure assembly.
5. `space/service.py` read, authorization, reconcile, Director, and launch resolution paths.
6. `api/v1/space_routes.py` snapshot adapters and removal of refresh semantics.
7. `api/v1/space_mcp.py` worktree list contract.
8. `www/packages/core/src/spaceTransport.ts` only if the effective default contract needs an
   explicit field rather than retaining the current JSON name.

Expect roughly 12 test modules to change, concentrated in migration, model, store, service,
REST, MCP, launch resolution, and the browser transport fixtures. Canvas layout persistence
and transcript ingestion remain outside the change.

## Approval recommendation

Approve this reshape before the later CRUD slices. It gives durable identity to the facts TM
owns, keeps filesystem and Git facts live, preserves Canvas and transcript history, and
removes the identity transition that caused M4.
