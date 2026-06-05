---
title: Spaces Slice 1 Identity and Schema Foundation
type: sessions
tags: [backend, spaces, migrations, pydantic]
summary: Implemented Spaces identity models and database foundation migration.
status: active
source: backend-engineer
confidence: high
created: 2026-06-21
updated: 2026-06-21
---

## Summary

Implemented Slice 1 of the Spaces foundation on branch `spaces/slice1-identity-schema`, opened PR #161, and preserved runtime behavior. The branch has two commits:

* `044a05b` `feat(spaces): add identity model contracts`
* `5183f0e` `feat(spaces): add schema foundation`

## API Contract

No HTTP endpoints changed in this slice.

Domain contracts added under `transport_matters.space.models`:

```python
SpaceId
WorktreeId
CanvasId
Space
SpaceGitIdentity
Worktree
Canvas
ResolvedWorktree
shortest_unambiguous_prefix
```

Identifiers are uuid4 backed value objects. Pydantic serialization emits bare uuid strings. Domain models serialize snake case. Future public `/v1/` DTOs will project these models through the existing camelCase API convention.

## Database Changes

Added Alembic revision `0006_spaces_foundation`, revising `0005_session_template_provenance`.

New tables:

* `space`
* `space_git_identity`
* `space_worktree`
* `canvas`

Session links:

* `session.space_id uuid NULL`
* `session.worktree_id uuid NULL`

Indexes:

* `session_space_ix` on `(owner, space_id, started_at DESC)` where `space_id IS NOT NULL`
* `session_worktree_ix` on `(owner, worktree_id, started_at DESC)` where `worktree_id IS NOT NULL`

Downgrade removes the session indexes, nullable link columns, and new Spaces tables.

## Security Considerations

The migration is additive and keeps session links nullable. Historical session rows are preserved when Spaces objects are removed. Cascading deletes are limited to the Space owned cluster:

* `space_git_identity_space_fk`
* `space_worktree_space_fk`
* `canvas_space_fk`

No public endpoint or auth behavior changed.

## Performance Notes

Session link lookups use partial indexes, avoiding index entries for legacy rows with null `space_id` or `worktree_id`. The foundation does not introduce runtime queries yet, so there is no latency impact in this slice.

Verification completed:

* `cd api && .venv/bin/python -m pytest src/transport_matters/space/test_models.py`: 5 passed
* `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=${TRANSPORT_MATTERS_TEST_DATABASE_URL:-postgresql://tm:tm@localhost:55432/postgres} .venv/bin/python -m pytest src/transport_matters/session/test_migrate.py -k alembic_upgrade_and_downgrade_smoke`: 1 passed
* `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=${TRANSPORT_MATTERS_TEST_DATABASE_URL:-postgresql://tm:tm@localhost:55432/postgres} .venv/bin/python -m pytest src/transport_matters/session/test_migrate.py`: 7 passed
* `cd api && just check && just test`: ruff format, ruff check, mypy, and 1671 tests passed

## Open Items

* Slice 3 should add public camelCase DTOs and map domain model fields to response summaries.
* Future slices should add runtime resolution and API surfaces without duplicating the domain contracts from this slice.
