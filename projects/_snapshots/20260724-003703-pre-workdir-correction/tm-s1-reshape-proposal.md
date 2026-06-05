# S1 persistence reshape proposal v3

Date: 2026-07-22  
Baseline: `9ac8d10d2d5304bc579980636729d466e952f404`  
Status: owner-locked design proposal. No repository code changed.

## Decision

Space is a durable organizational container. Git repository grouping is a runtime label on
Worktrees and has no authority over Space membership.

```text
durable: owner -> Space -> M:N membership links -> Worktree path identity -> anchored Canvas tree
runtime:  Worktree -> repo_group_key + branch/HEAD/primary/missing projection
```

The Space switcher is the Director view. There is no separate Director Canvas row. Every
owner has at least one default Space, created before or during the first Worktree
materialization. The default Space computes membership as all owner Worktrees. Named Spaces
are curated subsets through a junction. The switcher surfaces Spaces only when more than one
exists.

## 1. Durable Space and Worktree membership

### `space`

Restore and retain a durable table:

```text
space {
  space_id uuid primary key
  owner text not null
  name text nullable
  is_default boolean not null default false
  created_at timestamptz not null
  updated_at timestamptz not null
}
```

The default Space receives a system display name when `name` is null. User Space creation,
rename, default switching, and deletion remain a later Space CRUD slice. S1 creates the
repository seam and reads only.

Add a partial unique index `UNIQUE (owner) WHERE is_default` so an owner has exactly one
default Space.

Create `space_worktree_link(owner, space_id, worktree_id)` with owner-scoped foreign keys and
primary key `(owner, space_id, worktree_id)`. A Worktree exists independently and may appear
in several named Spaces. Future Space CRUD adds or removes references. There is no move
operation. The default Space has computed membership over all owner Worktrees and has no
materialized links.

The single membership authority is:

```text
worktree_in_space(worktree_id, space_id) =
  true for every owner Worktree when space.is_default is true;
  link exists in space_worktree_link otherwise.
```

Named Spaces are view filters over this predicate. They never constrain execution placement.
Every authorization, launch, default selection, and future membership operation consumes
this same predicate.

This is the load-bearing invariant:

```text
reconcile_detection may refresh runtime observations, but it never changes the junction or
any default membership computation.
```

Organizational references are therefore stable across `git init`, branch changes,
common-directory changes, and temporary Git probe failures.

## 2. Runtime repository group label

Keep the deterministic filesystem classifier from v2. Its output feeds a projected
`repo_group_key`, separate from `space_id`:

```text
git:<sha256(canonical git common directory)>
path:<sha256(canonical Worktree path)>
```

The label is suitable for CMDK Worktree grouping and display. It carries no authorization,
membership, lifecycle, or persistence authority. Space identity remains the UUID returned by
the durable row.

Detection has two stages:

1. Filesystem classification establishes Git versus plain membership. It walks ancestors,
   resolves `.git` directories or `gitdir` files, resolves relative `commondir`, and returns
   `inconclusive` for permission, malformed, broken-link, or disappearing-path cases.
2. Fact enrichment obtains branch, HEAD, primary, and linked missing status. Enrichment
   failure leaves the established repo label intact and marks only the unavailable facts.

`git worktree list` exit status never converts a proven Git path into a plain path label.
Bare repositories remain plain launch directories in S1.

## 3. Schema delta

### `space_worktree`

Keep:

1. `worktree_id`, `owner`
2. `path`, `workspace_slug`, `workspace_hash`
3. `root_canvas_id`
4. `provenance`, `lifecycle_state`, `lifecycle_generation`
5. `created_at`, `updated_at`

Drop the four runtime columns:

1. `branch_name`
2. `head_oid`
3. `is_primary`
4. `missing`

Unique path and workspace identity constraints remain. Detection upsert can create a path
identity and refresh path identity fields. It never touches organizational membership.

### `space_worktree_link`

The junction uses owner-scoped Space and Worktree foreign keys, both `ON DELETE CASCADE`.
It is the only persisted membership for named Spaces. Its add and remove seams are
reserved for the later Space CRUD slice. Detection has no write path to this table.

### `canvas`

Drop `canvas.space_id`. Add `anchor_worktree_id uuid NOT NULL`.

The protected root and every descendant inherit one anchor Worktree. A Canvas appears in
every Space for which `worktree_in_space(anchor_worktree_id, space_id)` is true. Use these
constraints:

1. `UNIQUE (owner, worktree_id)` on `space_worktree`.
2. `UNIQUE (owner, anchor_worktree_id, canvas_id)` on `canvas`.
3. Parent FK `(owner, anchor_worktree_id, parent_canvas_id)` to `canvas`, retaining the
   user subtree cascade.
4. Worktree root FK `(owner, worktree_id, root_canvas_id)` to
   `canvas(owner, anchor_worktree_id, canvas_id)` with `ON DELETE NO ACTION DEFERRABLE
   INITIALLY DEFERRED`.
5. Anchor FK to `space_worktree` with `ON DELETE CASCADE`, used only by the guarded
   Worktree deletion state machine.
6. `default_worktree_id` FK to `space_worktree` with deferred `NO ACTION`; deletion clears
   surviving user Canvas defaults before commit.
7. Existing root versus user shape and reciprocal pair trigger.

The deferred pair trigger requires a protected root with
`anchor_worktree_id=worktree_id`, `default_worktree_id=worktree_id`, and
`kind=worktree_root`. The reciprocal Worktree must name the Canvas as `root_canvas_id`.

The three-axis invariant is explicit:

1. `anchor_worktree_id` is organizational and lifecycle home.
2. `default_worktree_id` is a durable launch preference and may target any Worktree owned by
   the caller.
3. Browser `contentRef.worktreeId` is execution placement and may target any Worktree owned
   by the caller.

A Canvas may contain panes targeting multiple Worktrees. Named Spaces filter what is visible;
they do not constrain where a Canvas runs. Deleting the anchor Worktree cascades the Canvas
subtree even when a pane targets a surviving sibling Worktree.

Root names derive from durable path basename or workspace slug at creation. Runtime branch
changes never rename a durable Canvas.

### Durable stamps

Keep session and run lifecycle `space_id`, `worktree_id`, and Canvas stamps FK free and
unchanged. They record the durable Space and Worktree selected at claim time. Space IDs stay
UUIDs. Repo group labels do not replace them.

Under S1, the default Space contains every owner Worktree, so owner-scoped placement and
same-Space placement coincide. Named Spaces remain view filters and never become execution
constraints.

## 4. Persisted and projected model boundary

Split models so runtime facts cannot regain persistence authority:

1. `StoredWorktree` contains durable path and lifecycle fields, with no Space membership.
2. `ProjectedWorktree`, surfaced through `WorktreeRecord`, adds `repo_group_key`, branch,
   HEAD, primary, and missing.
3. `StoredCanvas` contains `anchor_worktree_id`. A Space-scoped `CanvasRecord.space_id` is
   response context, so the same Canvas can appear in several Space responses.
4. `SpaceSnapshot` contains a durable Space plus projected Worktrees and anchored Canvases.
5. `space/projection.py` owns pure assembly and keeps `store.py` focused on persistence.

The public `space_id` remains UUID. Add a projected `repo_group_key` field to Worktree DTOs
only where display needs it. It must never be used as an authorization key.

## 5. Reads and reconciliation

### Reads

Reads load durable Spaces, computed default membership, named junction membership, and
Worktrees, then enrich each path with the current projection. A Worktree may appear in many
Space responses, with the runtime repo label shown inside each Worktree row. Canvas trees are
loaded by `anchor_worktree_id` and appear in every referencing Space.

Point reads classify only the requested Worktree path. Owner-wide lists use bounded
concurrency and isolate one inconclusive checkout from healthy Spaces. Reads perform no
inserts or updates. The MCP `refresh` flag becomes redundant and should leave the contract;
explicit reconciliation remains a Director mutation.

Primary protection, missing launch rejection, and lifecycle guards read projected values at
action time. A temporary inability to enrich Git facts fails closed for destructive or launch
actions while preserving the durable Space membership.

### Reconciliation

`reconcile_detection` is the sole detection write boundary:

1. Lock the detection target.
2. Classify membership and enrich current facts.
3. Upsert path identities and create missing Worktree roots.
4. Preserve every existing membership link exactly. Default membership remains computed.
5. Return a fresh projection from the successful detection and durable rows.

The default Space is ensured before the first Worktree row is inserted. New Worktrees appear
there through computed membership. Delete `mark_missing_worktrees`, Space-keyed Git claims,
and any conflict update that assigns a Worktree to the detected repo group.

## 6. Plain to Git walkthrough

1. First materialization ensures the owner's default Space `S`, Worktree `W`, and root Canvas
   `C`. `C.anchor_worktree_id=W` and `W.root_canvas_id=C`; computed default membership makes
   `W` visible under `S`.
2. Reads label the plain path `path:P`.
3. The user runs `git init` at the same path.
4. Filesystem discovery labels it `git:G`.
5. Reads still show `W` and `C` under `S`, with `repo_group_key=git:G`.
6. Reconciliation updates only runtime projection inputs and leaves every membership link
   unchanged.
7. Prior and later session stamps retain the durable Space UUID selected by the caller; runtime display shows
   the new Git group label.

M4 dissolves because Git initialization changes a display label. It never rebinds the
Worktree, junction, or root Canvas to another Space, so no root FK transition can roll back.

## 7. Director and scope map

The durable Space layer realizes the earlier virtual Director decision. The Space switcher
is the Director presentation, with Spaces as top-level nodes and Worktree root Canvases below
them. A Worktree and its Canvas tree may appear under multiple Spaces. There is no Director
Canvas row or launch target.

S1 includes durable Space creation of the default row, computed default membership, Space
list/detail reads, Worktree grouping by Space, Canvas reads through anchors, and the
projection seams. A later Space CRUD slice owns named Space creation, rename, adding and
removing Worktree references, default switching, and Space deletion policy. Detection never
gains those mutation powers.

## 8. Required proof

1. Migration 0030 restores durable Space, creates the M:N junction, removes four runtime
   Worktree columns, installs anchored Canvas constraints, and keeps UUID stamps.
2. Default Space creation is idempotent and every owner Worktree appears in its computed
   membership.
3. Plain to Git reconciliation leaves every membership link unchanged and leaves computed
   default membership unchanged.
4. Branch, HEAD, primary, missing, and repo-group changes appear on reads without changing
   durable Worktree, Space, or Canvas bytes and timestamps.
5. Direct root deletion, user Canvas as root, swapped roots, wrong anchors, and cross-anchor
   reparent all fail.
6. Privileged Worktree deletion cascades root and user Canvas subtree through the anchor FK
   and commits, and cascades its junction rows. Space deletion cascades its junction rows.
   A direct or lone root delete fails at deferred pair validation.
7. Primary protection and missing/lifecycle launch guards use projected values at action time.
8. Observer reads execute no writes. Reconcile remains Director only and never writes the
   membership junction.
9. Git classifier covers primary and linked Worktrees, relative markers, commondir, plain
   ancestor walk, malformed markers, permission errors, broken links, and disappearance.
10. A newly enumerated linked Worktree remains absent until explicit reconcile, then gets one
    Worktree ID and one protected root under concurrency.
11. REST and MCP emit the same projected Worktree and Canvas contracts; repo group labels
   never authorize a request.
12. All authorization, launch, default selection, and future membership paths consume the
    same `worktree_in_space` predicate.
13. `just check`, `just test`, and migration smoke pass against Postgres.

## 9. Estimated implementation surface

Approximately 52 production symbols across migration 0030, Space models and store, the new
projection module, detection classifier, Space service, REST/MCP adapters, launch resolution,
and the `@tm/core` transport. Expect roughly 15 test modules across migration, detection,
model, store, service, REST, MCP, launch resolution, and browser transport.

Canvas layout persistence and transcript content remain outside this reshape.

## Approval recommendation

Approve the durable organizational Space model, runtime-only repo grouping, Worktree anchored
Canvas tree, and explicit reconciliation boundary before implementation. Add the later Space
CRUD slice before introducing user authored Space mutations.
