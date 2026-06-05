# Transport Matters Spaces locked model review

Date: 2026-06-21
Reviewer: backend-engineer
Scope: identity, persistence, migration feasibility
Artifact: `~/.mdx/projects/transport-matters-spaces--proposal.md`
Repo proof: `main` at `2323169613fae7a21e885da382c18f53011eec22`; `git status --short` was clean before this review. This file is outside the repo.

## Verdict

Conditional signoff. The locked Spaces model is feasible, and the uuid4 plus native Postgres `uuid` decision ports cleanly to this Python backend. I found no reason to keep prefixed text ids. I do see three seams that must be explicit in the spec so the detect first slice does not lose the product identity after resolving a worktree to a path.

## Positive checks

- `crates/lilo-common/src/id.rs::define_id` mints with `Uuid::new_v4()`, serializes through `serde(transparent)`, displays a bare UUID string, parses from that same string, and uses `#[sqlx(transparent)]` over `uuid::Uuid` for native Postgres `uuid` columns.
- `crates/lilo-common/src/id.rs::shortest_unambiguous_prefix` uses `MIN_SHORT_PREFIX_LEN = 7`; the tests confirm the singleton short id is seven characters and that longer hyphenated prefixes are allowed when needed.
- The Python API already depends on Pydantic v2 and `psycopg[binary,pool]>=3.2`. A local Pydantic probe confirmed `uuid.UUID` fields dump to bare UUID strings in JSON mode, so the API model can expose `spaceId`, `worktreeId`, and `canvasId` as strings without storing them as text.
- App minted uuid4 is the better fit here. It matches littleorgans, gives the API an id before related inserts, and avoids tying identity to a database default.

## Findings

1. **Major: the run path needs a first class `ResolvedWorktree` handoff, not only `worktreeId -> cwd` at the route edge.**

   Evidence:
   - `api/src/transport_matters/api/v1/run_routes.py::CreateRunRequest` currently accepts public `cwd`.
   - `api/src/transport_matters/api/v1/run_routes.py::_spawn_request` maps `body.cwd` to `SpawnRun.cwd`.
   - `api/src/transport_matters/run_models.py::SpawnRun`, `ManagedRun`, and `ManagedRunView` carry `cwd`, with no `space_id` or `worktree_id`.
   - `api/src/transport_matters/api/v1/run_routes.py::_workspace_id_for_view` and `run_view_model` recompute `workspaceId` from `view.cwd`.
   - `api/src/transport_matters/run_models.py::RunFilters` and `api/src/transport_matters/run_manager.py::RunManager.list` can filter by `cwd`, harness, and state only.

   Risk: if the first implementation only changes `POST /v1/runs` to accept `worktreeId` and resolves it to `cwd` before calling the existing `RunManager`, the stable product identity is gone from the process resident run. `GET /v1/runs/{id}`, `GET /v1/runs`, terminal ready frames, idempotent create results, and run filters would have to rediscover `spaceId` and `worktreeId` from `cwd`, or would keep returning only `workspaceId`. That weakens the locked claim that public launch and observe move from `cwd` to `worktreeId`.

   Required spec change: define one DTO, for example `ResolvedWorktree`, returned by the Space store. It should contain `space_id`, `worktree_id`, `cwd`, `workspace_slug`, `workspace_hash`, and missing or archived status. Pass it through `SpawnRun`, store it on `ManagedRun`, expose it through `ManagedRunView`, and bind it into the session writer. Keep `cwd` internal, but do not make it the only identity carried by the run.

2. **Major: backfill needs an explicit answer for sessions whose `cwd` is empty, not just paths that are now missing.**

   Evidence:
   - `api/migrations/versions/0001_session_store_foundation.py::upgrade` creates `session.cwd` as `text NOT NULL DEFAULT ''`.
   - `api/src/transport_matters/session/models.py::SessionRow` also defaults `cwd` to an empty string.
   - `api/src/transport_matters/session/backfill.py::_cwd` returns an empty string when no transcript record carries a cwd.
   - `api/src/transport_matters/session/backfill.py::_workspace_identity` can recover `workspace_slug` and `workspace_hash` from the Tier 1 run directory, but not the original canonical path.
   - `api/src/transport_matters/api/v1/session_routes.py::list_sessions` currently preserves a `workspaceId` filter, and `api/src/transport_matters/api/v1/session_models.py::workspace_id_from_row` derives that from `workspace_slug/workspace_hash`.

   Risk: the proposal says the one time backfill runs git detection over each existing session `cwd`, and creates a missing Worktree when the path is gone. That covers missing paths, but it does not cover rows with `cwd = ''`. Those rows cannot be detected as git or plain directories, and a schema with `space_worktree.path NOT NULL` has no natural row for them. If the new UI and director rely only on `spaceId` or `worktreeId`, these sessions survive in Postgres but disappear from Space scoped history.

   Required spec change: add an explicit legacy path. Either keep `/v1/sessions?workspaceId=` as a supported history surface and show an unassigned legacy workspace group, or allow a legacy Worktree record with `path = NULL`, `missing = true`, and `workspace_slug/workspace_hash` as the only locator. Do not silently assign empty cwd rows to a current Space.

3. **Minor: `repo_instance_key` is correct only if relative git directory outputs are resolved against the target cwd.**

   Evidence:
   - Live repo proof for this checkout: `git rev-parse --show-toplevel --git-common-dir --git-dir` returns the checkout root, then `.git`, then `.git`.
   - `api/src/transport_matters/api/v1/meta.py::get_meta` documents that the user cwd can differ from the API process cwd.
   - `api/src/transport_matters/api/v1/run_routes.py::_validated_existing_dir` resolves a user supplied cwd before launch.

   Risk: `git -C <cwd> rev-parse --git-common-dir` may return a relative path such as `.git`. If the new detector canonicalizes that relative string from the API process cwd instead of the target cwd, unrelated repositories can be grouped together or a linked worktree can miss its Space.

   Required spec change: make `space_detection.py` resolve relative `--git-common-dir` and `--git-dir` values relative to the target working directory or the reported toplevel, then hash the resolved common dir. Add a unit test with process cwd different from target cwd.

## Migration notes

- The additive migration shape is safe if the new migration has a real downgrade that drops new indexes, nullable session columns, and new tables in dependency order. Existing migration `0001_session_store_foundation.py::downgrade` is forward only, while later migrations have downgrades. That does not block a `0006 -> 0005` downgrade, but the spec should avoid claiming the entire historical chain can downgrade to base.
- Native `uuid` columns are fine for new Space, Worktree, and Canvas ids. Keep existing `session_id`, `run_id`, `workspace_slug`, and `workspace_hash` as text unless a separate migration justifies changing them.
- `repo_instance_key = sha256(canonical git-common-dir)` should remain a derived lookup column with a unique constraint. It should not become public identity.

## Verification performed

- Read the locked proposal in full and the two supporting brainstorm artifacts.
- Verified the targeted backend symbols with fmm before reading code: `WorkspaceId`, `workspace_id`, `CreateRunRequest`, `_spawn_request`, `_workspace_id_for_view`, `run_view_model`, `SpawnRun`, `ManagedRunView`, `RunManager._resolve_cwd`, `RunManager.list`, `SessionRow`, session migrations, and session backfill helpers.
- Verified the littleorgans id convention in `crates/lilo-common/src/id.rs`.
- Verified live git output for this checkout and observed the repo was clean before writing this review artifact.
