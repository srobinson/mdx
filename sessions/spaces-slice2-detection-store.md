---
title: Spaces Slice 2 Detection and Store
type: sessions
tags: [backend, spaces, postgres, testing]
summary: Implemented Space detection and async SpaceStore persistence, then hardened git identity minting against concurrent first detection.
status: active
source: backend-engineer
confidence: high
created: 2026-06-21
updated: 2026-06-21
---

## Summary

Implemented Spaces slice 2 on branch `spaces/slice2-detection-store`, PR #162.

Commits:

- `3fd9fccc feat(spaces): detect git and plain spaces`
- `8091b260 feat(spaces): persist detected spaces`
- `b8e84b99 fix(spaces): atomic mint on repo_instance_key; drop dead git-dir probe`

Key decisions:

- `transport_matters.space.detection` owns git subprocess probes and domain neutral `DetectedSpace` and `DetectedWorktree` values.
- Plain directories become degenerate Spaces with one primary Worktree and no git identity.
- Git repositories are keyed by `sha256(resolved git_common_dir)` and enumerate worktrees through `git worktree list --porcelain -z`.
- Missing linked worktree paths are preserved as Worktrees with `missing=true`.
- `SpaceStore` owns async psycopg persistence, owner scoped reads, worktree reconciliation, canvas helpers, and tier 1 cache writes.
- First git detection now treats `space_git_identity.repo_instance_key` as the atomic arbiter. A losing concurrent candidate Space is deleted in the same transaction before commit, so no orphan Space rows survive.
- The dead `git rev-parse --git-dir` probe output was removed. Detection now expects the three fields it actually consumes.

## API Contract

No HTTP routes were added in this slice.

Internal Python contract:

```python
@dataclass(frozen=True)
class DetectedWorktree:
    path: Path
    workspace_slug: str
    workspace_hash: str
    branch_name: str | None
    head_oid: str | None
    is_primary: bool
    missing: bool = False

@dataclass(frozen=True)
class DetectedSpace:
    name: str
    primary_path: Path
    repo_instance_key: str | None
    git_common_dir: Path | None
    worktrees: tuple[DetectedWorktree, ...]

class SpaceStore:
    async def upsert_detection(self, detection: DetectedSpace, *, owner: str = "local") -> SpaceSnapshot: ...
    async def resolve_cwd(self, cwd: Path | str, *, owner: str = "local", create: bool = True) -> SpaceSnapshot | None: ...
    async def resolve_worktree(self, worktree_id: WorktreeId, *, owner: str = "local") -> ResolvedWorktree | None: ...
```

## Database Changes

No new migration was added. The implementation uses the existing Slice 1 tables:

- `space`
- `space_git_identity`
- `space_worktree`
- `canvas`

Persistence details:

- Git identity minting claims `space_git_identity.repo_instance_key` with `INSERT ... ON CONFLICT DO NOTHING RETURNING space_id`.
- `space_git_identity.space_id` is never updated on conflict. This prevents last writer identity rebinding.
- A losing candidate `space` row is deleted inside the same transaction before selecting the winning identity owner.
- Existing git identities are touched by updating `git_common_dir` and `detected_at` only for the same `space_id` and `repo_instance_key`.
- Worktrees upsert on `(owner, workspace_slug, workspace_hash)`.
- Git reconciliation marks previously seen paths missing when absent from a later detection.
- Plain directory detection intentionally writes no `space_git_identity` row.

## Security Considerations

- Git probes are subprocess argv calls, not shell commands.
- All Postgres writes use psycopg parameter binding.
- Space, worktree, and canvas reads are owner scoped.
- Detection errors are structured with machine readable codes for missing cwd, invalid cwd, unavailable git, timeout, and git probe failure.
- The git identity fix keeps the unique key as the database enforced concurrency boundary instead of relying on application ordering.

## Performance Notes

- Detection uses one `git rev-parse` probe and one `git worktree list --porcelain -z` call for git repositories.
- It does not fan out to `git branch` or `git rev-parse` per worktree.
- Store reads are simple indexed lookups over the Slice 1 unique constraints.
- Concurrent git first detection may briefly insert a losing candidate Space, but the loser is deleted before commit in the same transaction.
- Tier 1 cache writes are atomic JSON replacements under `storage_dir/spaces/{space_id}`.

## Verification

- Red regression confirmed: `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres .venv/bin/python -m pytest src/transport_matters/space/test_store.py::test_concurrent_git_first_detection_mints_one_space_without_orphans -q`, failed with `assert 2 == 1` before the fix.
- Green regression confirmed with the same command after the fix, passed 1 test.
- `cd api && .venv/bin/python -m pytest src/transport_matters/space/test_detection.py -q`, passed 8 tests.
- `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres .venv/bin/python -m pytest src/transport_matters/space/test_store.py -q`, passed 5 tests.
- `cd api && just check && just test`, passed ruff format, ruff check, mypy, and 1687 pytest tests.
- `git push` updated PR #162 branch `spaces/slice2-detection-store` through `b8e84b99`.

## Open Items

- Wire Space resolution into run launch handoff in a later slice.
- Add HTTP read surfaces only when the product slice needs them.
- Decide whether PR #162 should remain draft or be marked ready after orchestrator review.
