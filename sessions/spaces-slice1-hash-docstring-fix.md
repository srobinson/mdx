---
title: Spaces Slice 1 hash and migration docstring fix
type: sessions
tags: [backend, spaces, migration, models]
summary: Removed migration boilerplate docstring and made Space, Worktree, and Canvas hash by identity.
status: active
source: backend-engineer
confidence: high
created: 2026-06-21
updated: 2026-06-21
---

## Summary

Implemented the PR#161 follow-up on `spaces/slice1-identity-schema`.

Key decisions:

- Removed the Alembic migration module docstring while preserving graph variables.
- Added shared identity hash behavior for `Space`, `Worktree`, and `Canvas`.
- Kept frozen Pydantic models and field-based equality unchanged.
- Added a regression that covers the unhashable `Canvas.layout` dict case and asserts hash identity for all three entities.

Commit: `84c7107`.

## API Contract

No API surface changed.

## Database Changes

No schema SQL changed.

Migration file changed:

- `api/migrations/versions/0006_spaces_foundation.py`

Only the module docstring was removed. Alembic graph variables stayed intact:

- `revision = "0006_spaces_foundation"`
- `down_revision = "0005_session_template_provenance"`
- `branch_labels = None`
- `depends_on = None`

## Security Considerations

No auth, authorization, input validation, or exposed endpoint behavior changed.

## Performance Notes

Entity hashing now uses the scalar identity value for `Space`, `Worktree`, and `Canvas`. This avoids walking model fields and prevents `Canvas.layout` from making the model unhashable.

Verification observed:

- `cd api && .venv/bin/python -m pytest src/transport_matters/space/test_models.py -q`: 8 passed.
- `cd api && just check`: ruff format unchanged, ruff check passed, mypy passed.
- `cd api && just test`: 1674 passed in 48.96s.

## Open Items

None for this fix.
