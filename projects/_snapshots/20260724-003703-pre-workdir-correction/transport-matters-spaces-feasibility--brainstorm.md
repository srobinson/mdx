# Transport Matters Space feasibility brainstorm

Status: brainstorm, 2026-06-21.
Lens: identity, persistence, git worktree mechanics, API, migration feasibility.

## Verified current shape

* `workspace.py` owns `WorkspaceId`, `workspace_id`, `workspace_root`, and `run_root`. The key is canonical cwd, then slug plus 4 byte blake2b hash. Tier 1 runs live under `~/.transport-matters/workspaces/{slug}/{hash}/{run_id}/`.
* `run_models.py` has `SpawnRun.cwd`, `ManagedRun.cwd`, `ManagedRunView.cwd`, and `RunFilters.cwd`. `RunManager._resolve_cwd` requires an absolute existing directory and resolves it before launch.
* `run_routes.py` exposes `POST /v1/runs` through `CreateRunRequest.cwd`, maps it to `SpawnRun`, and returns `workspaceId` by recomputing `workspace_id(view.cwd)`.
* `session/models.py` persists `SessionRow.cwd`, `workspace_slug`, and `workspace_hash`. There is no `space_id` or `worktree_id`.
* `api/migrations/versions/0001_session_store_foundation.py` creates Postgres `session` and `event`. `session` has owner scoped indexes and no workspace table.
* `www/src/session-canvas/model/paneRecords.ts` defines `CanvasModel`, `CanvasId`, and pane refs. `canvasStore.ts` stores layout in Zustand, with `initializeCanvas` setting `id` from `workspaceHash`. Persistence is localStorage through `canvasStore.persistence.ts`.
* `NOW.md` says canvas layout is client side today, and a server store should be a sync target, not the owner, if cross profile or share becomes real.
* `PROJECT.md` says the active correlated store is Postgres, and Tier 1 disk remains the run source of truth.
* Current repo git proof: `git rev-parse --show-toplevel --git-common-dir --git-dir` returns this checkout root and `.git`; `git worktree list --porcelain` currently lists one worktree on `main`.

## Recommendation

Use a hybrid model:

1. Keep `WorkspaceId` as the internal per path storage key.
2. Add `Space` above it as the durable product aggregate.
3. Add `Worktree` as the path target inside a Space.
4. Keep `Canvas` as the visual working surface inside a Space.
5. Persist Space and Worktree server side now. Persist Canvas identity and layout only as a sync target, with localStorage as a cache.

This reconciles git worktrees without moving Tier 1 files. A linked git worktree gets its own `WorkspaceId` because it is a different path. The parent Space groups those workspace keys through git common directory detection.

Canvas remains a good name if it means "saved surface of panes, prompt context, and focus". It must not mean project, repo, path, or process. If that distinction stays confusing in the UI, the better rename is `Surface`, but I would not rename it yet.

## Concrete identity keys

### Space

Public key: `spaceId = spc_<uuidv7>`.

A Space is not a path. It is a durable local aggregate with one owner.

For a plain directory:

```text
space.kind = "plain"
space.primaryWorktreeId = one worktree for the canonical path
```

For a git repository:

```text
space.kind = "git"
space.git.commonDir = canonical result of `git rev-parse --git-common-dir`
space.git.repoInstanceKey = sha256(canonical commonDir)
space.git.remoteFingerprint = sha256(normalized primary remote url), nullable
```

`repoInstanceKey` is an internal lookup key, not the public id. It groups local linked worktrees. `spaceId` stays stable after display name changes and lets users adopt or merge spaces later.

### Worktree

Public key: `worktreeId = wkt_<uuidv7>`.

A Worktree is one launchable path within a Space.

```text
worktree.spaceId = spc_...
worktree.path = canonical path
worktree.workspaceId = {WorkspaceId.slug}/{WorkspaceId.hash}
worktree.workspaceSlug = WorkspaceId.slug
worktree.workspaceHash = WorkspaceId.hash
```

For plain Spaces there is exactly one Worktree. For git Spaces, every entry from `git worktree list --porcelain` gets a Worktree row.

`WorkspaceId` remains the Tier 1 and legacy session bridge. It is per worktree path. It should not be renamed in code until the Space model is shipped and tests prove no capture regressions.

### Canvas

Public key: `canvasId = cnv_<uuidv7>`.

A Canvas belongs to a Space and may have a default Worktree. A Canvas can contain panes from multiple Worktrees if the user is comparing agents side by side.

```text
canvas.spaceId = spc_...
canvas.defaultWorktreeId = wkt_... | null
pane refs keep runId, sessionId, resourceId, and optional worktreeId as soft refs
```

## Storage shape

Postgres should be the source for Space and Worktree identity because current launches already require the session store. Tier 1 should keep a cache for diagnostics and future degraded mode.

### Tables

```sql
CREATE TABLE space (
  space_id text PRIMARY KEY,
  owner text NOT NULL DEFAULT 'local',
  kind text NOT NULL CHECK (kind IN ('plain', 'git')),
  display_name text NOT NULL,
  primary_worktree_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  archived_at timestamptz
);

CREATE TABLE space_git_identity (
  space_id text PRIMARY KEY REFERENCES space(space_id) ON DELETE CASCADE,
  repo_instance_key text NOT NULL,
  common_dir text NOT NULL,
  git_dir text NOT NULL,
  primary_remote_url text,
  remote_fingerprint text,
  default_branch text,
  head_oid text,
  detected_at timestamptz NOT NULL,
  UNIQUE (repo_instance_key)
);

CREATE TABLE space_worktree (
  worktree_id text PRIMARY KEY,
  space_id text NOT NULL REFERENCES space(space_id) ON DELETE CASCADE,
  owner text NOT NULL DEFAULT 'local',
  workspace_slug text NOT NULL,
  workspace_hash text NOT NULL,
  path text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('plain', 'git')),
  branch_ref text,
  branch_name text,
  head_oid text,
  detached boolean NOT NULL DEFAULT false,
  dirty_state text NOT NULL DEFAULT 'unknown'
    CHECK (dirty_state IN ('unknown', 'clean', 'dirty')),
  missing boolean NOT NULL DEFAULT false,
  locked boolean NOT NULL DEFAULT false,
  prunable boolean NOT NULL DEFAULT false,
  last_seen_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  archived_at timestamptz,
  UNIQUE (owner, workspace_slug, workspace_hash),
  UNIQUE (owner, path)
);

CREATE TABLE canvas (
  canvas_id text PRIMARY KEY,
  owner text NOT NULL DEFAULT 'local',
  space_id text NOT NULL REFERENCES space(space_id) ON DELETE CASCADE,
  display_name text NOT NULL,
  default_worktree_id text,
  layout_version integer NOT NULL DEFAULT 1,
  layout jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  archived_at timestamptz
);
```

Session linkage should stay soft:

```sql
ALTER TABLE "session" ADD COLUMN space_id text;
ALTER TABLE "session" ADD COLUMN worktree_id text;
CREATE INDEX session_owner_space_started_ix
  ON "session" (owner, space_id, started_at DESC);
CREATE INDEX session_owner_worktree_started_ix
  ON "session" (owner, worktree_id, started_at DESC);
```

No foreign key from `session` to `space` in the first cut. Session history must survive a Space delete or a future merge. The existing `workspace_slug` and `workspace_hash` remain because they address Tier 1.

Indexes needed for API latency:

```sql
CREATE INDEX space_owner_updated_ix ON space (owner, updated_at DESC);
CREATE INDEX space_worktree_space_seen_ix ON space_worktree (space_id, last_seen_at DESC);
CREATE INDEX canvas_space_updated_ix ON canvas (space_id, updated_at DESC);
```

### Tier 1 cache

Keep run directories unchanged.

Add only diagnostic cache files:

```text
~/.transport-matters/spaces/{spaceId}/space.json
~/.transport-matters/spaces/{spaceId}/worktrees.json
~/.transport-matters/spaces/{spaceId}/canvases/{canvasId}.json
```

These mirror Postgres. They are not authoritative while Postgres is available.

## Git detection and persistence

Detection runs in three places:

1. API startup detects `settings.cwd` or `Path.cwd()` so the app always has a current Space.
2. `POST /v1/spaces/resolve` detects any user supplied path.
3. `POST /v1/runs` validates the selected Worktree and refreshes it before launch.

Detection uses subprocess argv, never shell strings, with a small timeout:

```text
git -C <cwd> rev-parse --is-inside-work-tree --show-toplevel --git-common-dir --git-dir
git -C <cwd> worktree list --porcelain -z
git -C <worktree> symbolic-ref -q HEAD
git -C <worktree> rev-parse HEAD
git -C <worktree> status --porcelain=v1 -z
```

`status` should be cached or optional because it can be slow in large repos. `worktree list` is enough to maintain identity.

Failure policy:

* Not inside a work tree: create or update a plain Space and one Worktree.
* Git command timeout: return `git_detection_failed` and preserve the last known record.
* Missing path: mark Worktree `missing=true`, block launches, keep history visible.
* Common directory changes: create a new candidate Space unless the user explicitly merges.
* Remote changes: update metadata only; do not change `spaceId`.

## Worktree lifecycle

### Create

Endpoint calls:

```text
git -C <repoRoot> worktree add <path> <ref>
```

Inputs:

```typescript
interface CreateWorktreeRequest {
  path: string;
  branchName?: string;
  fromRef?: string;
  detach?: boolean;
  idempotencyKey?: string;
}
```

Rules:

* `path` must be absolute, normalized, and not under `~/.transport-matters`.
* `branchName` creates a branch from `fromRef` when supplied.
* Concurrent requests dedupe on `idempotencyKey` or `(spaceId, path)`.
* On success, detection upserts the Worktree and returns it.

### List

`GET /v1/spaces/{spaceId}/worktrees?refresh=true` refreshes from `git worktree list --porcelain` before returning rows. Without refresh, it returns the stored view.

### Switch

There are two meanings. Keep them separate.

* Canvas switch: set `canvas.defaultWorktreeId`.
* Git checkout: change a Worktree branch.

Endpoint for checkout:

```text
POST /v1/spaces/{spaceId}/worktrees/{worktreeId}/checkout
```

Dirty Worktrees return `worktree_dirty` unless `force=true`. Detached Worktrees are valid launch targets, but checkout needs an explicit ref.

### Remove

Endpoint:

```text
DELETE /v1/spaces/{spaceId}/worktrees/{worktreeId}?force=false
```

Rules:

* Return `worktree_has_running_runs` if `RunManager` has active runs for that cwd.
* Return `worktree_dirty` unless force is true.
* Call `git worktree remove` for git Worktrees.
* Archive the row after successful removal. If the path is already gone, mark `missing=true` and offer prune.

### Failure modes to surface

* Detached HEAD: launch allowed, branch fields null, `detached=true`.
* Deleted branch: launch allowed, `branch_ref` stale, status warning shown.
* Branch checked out elsewhere: return `worktree_branch_conflict` from git stderr.
* Dirty tree: block checkout and removal unless force.
* Missing path: block launch, keep history.
* Locked or prunable worktree: expose `locked` and `prunable` so the UI can explain it.
* Git binary missing: plain Space still works; git lifecycle endpoints return `git_unavailable`.

## API contract

```typescript
type SpaceKind = "plain" | "git";
type DirtyState = "unknown" | "clean" | "dirty";

interface Space {
  spaceId: string;
  owner: "local";
  kind: SpaceKind;
  displayName: string;
  primaryWorktreeId: string | null;
  git?: {
    commonDir: string;
    primaryRemoteUrl: string | null;
    defaultBranch: string | null;
    headOid: string | null;
    detectedAt: string;
  };
  createdAt: string;
  updatedAt: string;
}

interface Worktree {
  worktreeId: string;
  spaceId: string;
  workspaceId: string;
  path: string;
  kind: SpaceKind;
  branchRef: string | null;
  branchName: string | null;
  headOid: string | null;
  detached: boolean;
  dirtyState: DirtyState;
  missing: boolean;
  locked: boolean;
  prunable: boolean;
  lastSeenAt: string;
}

interface Canvas {
  canvasId: string;
  spaceId: string;
  displayName: string;
  defaultWorktreeId: string | null;
  layoutVersion: number;
  layout: unknown;
  createdAt: string;
  updatedAt: string;
}

interface ResolveSpaceRequest {
  cwd: string;
  create?: boolean;
}
interface ResolveSpaceResponse {
  space: Space;
  worktree: Worktree;
  canvases: Canvas[];
}

interface CreateRunRequest {
  harness: "claude" | "codex";
  worktreeId: string;
  canvasId?: string;
  terminal?: { cols: number; rows: number };
  oscColorReplies?: boolean;
  runtimeTemplate?: string;
  continueFromSessionId?: string;
  idempotencyKey?: string;
  bypassPermissions?: boolean;
}

interface Run {
  runId: string;
  spaceId: string;
  worktreeId: string;
  workspaceId: string;
  sessionId: string;
  harness: "claude" | "codex";
  state: "RUNNING" | "TERMINATING" | "TERMINATED" | "EXITED" | "FAILED";
  endReason?: "explicit" | "idle-timeout" | "shutdown" | "deploy-restart";
  error?: string;
  createdAt: string;
}

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

Routes:

```text
GET    /v1/spaces?owner=local&kind=&limit=&cursor=
POST   /v1/spaces/resolve
GET    /v1/spaces/{spaceId}
PATCH  /v1/spaces/{spaceId}
GET    /v1/spaces/{spaceId}/worktrees?refresh=false
POST   /v1/spaces/{spaceId}/worktrees
POST   /v1/spaces/{spaceId}/worktrees/{worktreeId}/checkout
DELETE /v1/spaces/{spaceId}/worktrees/{worktreeId}
GET    /v1/spaces/{spaceId}/canvases
POST   /v1/spaces/{spaceId}/canvases
PATCH  /v1/canvases/{canvasId}
POST   /v1/runs
GET    /v1/runs?spaceId=&worktreeId=&state=&limit=&cursor=
GET    /v1/sessions?spaceId=&worktreeId=&workspaceId=&purpose=&visibility=&limit=&cursor=
```

`cwd` should move out of public `POST /v1/runs`. The UI and director should target `worktreeId`. CLI launch can still resolve cwd internally before calling the same run seam.

## Implementation seams

Backend additions:

* `space_models.py`: Pydantic and dataclass shapes.
* `space_detection.py`: pure detection service around subprocess argv and WorkspaceId.
* `space_store.py`: Postgres DAO plus Tier 1 cache writer.
* `api/v1/space_routes.py`: routes above.
* `run_models.py`: add `SpawnRun.worktree_id`, optional `space_id`, and keep resolved `cwd` internal.
* `run_routes.py`: `CreateRunRequest.worktreeId`, response `spaceId` and `worktreeId`, filters.
* `session/models.py` and ingest binding: add soft `space_id` and `worktree_id`.
* Alembic migration: add tables and nullable session columns, with a real downgrade for the new tables and columns.

Frontend additions:

* Replace Workdir launcher scope with Space and Worktree scopes.
* Change `CanvasModel.id` from workspace hash to `canvasId`.
* Treat localStorage as cache keyed by `canvasId`.
* Pane refs may carry `worktreeId` when a pane has a launch target.
* Deleted or missing sessions remain placeholder panes, matching the current NOW.md direction.

## Migration

Because the product is pre release, prefer a direct migration over compatibility layers.

1. Add tables and API with `cwd` still accepted internally.
2. On first API startup, resolve the current cwd into Space and Worktree.
3. Backfill sessions:
   * For each session with an existing `cwd`, run detection.
   * If detection succeeds, set `session.space_id` and `session.worktree_id`.
   * If the path is missing, create a legacy plain Space with `missing=true` Worktree and keep history visible.
4. Keep Tier 1 run directories unchanged.
5. Import localStorage canvas state once per `workspaceHash` into one default Canvas per Space. Mark the local record migrated.
6. Change UI and director flows to `spaceId` plus `worktreeId`.
7. Remove public `cwd` from `POST /v1/runs` after the launcher and CLI both resolve first.

Blast radius:

* Backend: run routes, session routes, session writer and ingest binding, run manager request shape, migrations, tests.
* Frontend: `www/src/api.ts`, command launcher scopes, canvas store persistence, session picker filters, captured run pane spawn.
* Docs: NOW, PROJECT, B6 runs contract, B6 sessions contract.

Low risk because `WorkspaceId`, Tier 1 paths, and run capture stay unchanged.

## Feasibility options

### Option A: pure derived git common directory

Identity:

```text
spaceId = git:<sha256(canonical commonDir)>
plain spaceId = dir:<sha256(canonical path)>
```

Pros:

* Minimal schema.
* No user registration step.
* Groups linked worktrees automatically.

Cons:

* Public ids change if the repository moves.
* Plain directories remain path identity under a new name.
* Hard to merge, rename, archive, or share Spaces.
* Weak for director parity because Canvas identity still lacks a server anchor.

Verdict: useful as an internal detection key, not as product identity.

### Option B: explicit user registered Space

Identity:

```text
spaceId = generated id; every path is attached by user or API registration
```

Pros:

* Stable across path moves.
* Works for plain directories, repos, and future non filesystem Spaces.
* Strong ownership model for Canvases and director commands.

Cons:

* More UI before value.
* Git worktrees do not group automatically unless registration runs detection anyway.
* Easy to create duplicate Spaces for the same repo.

Verdict: good long term, clumsy as the first experience.

### Option C: derived bootstrap into explicit Space

Identity:

```text
Detection finds candidate by repoInstanceKey or canonical plain path.
Store creates or returns generated `spaceId`.
User can later rename, merge, archive, or adopt.
```

Pros:

* Auto groups git worktrees.
* Keeps public ids stable.
* Works for plain directories.
* Gives the director a real API object.
* Lets Tier 1 and `WorkspaceId` remain untouched.

Cons:

* Needs new tables and migration.
* Needs duplicate detection and merge policy.
* Requires careful localStorage canvas import.

Verdict: recommended.

## Final call

Ship Option C.

Space is the product aggregate. Worktree is the launch target. WorkspaceId is the internal path storage key. Canvas is a saved surface inside a Space, not identity. This is the smallest design that handles git worktrees, plain directories, director parity, and existing run storage without moving captured bytes.
