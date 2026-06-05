# Spaces package move review

Scope: `~/.mdx/projects/transport-matters-spaces-slice{1,2,3,4,5}--plan.md` plus `transport-matters-spaces--plan.md`.
Lens: Python package layout correctness after moving Space domain modules into `transport_matters.space`.

## Findings

1. Major: `space_store` fixture is announced and later consumed, but the plan never defines it.

   Evidence:
   - `transport-matters-spaces-slice2--plan.md` symbol `api/conftest.py shared space_store fixture`: the section says to add a shared fixture, but the supplied code block only imports `AsyncIterator`, `Path`, `pytest`, `create_async_pool`, `TestDb`, and `SpaceStore`. There is no `@pytest.fixture`, `def space_store`, or `async def space_store` in that slice.
   - `transport-matters-spaces--plan.md` symbol `Slice status table`: Slice 2 is marked as having `space_store` fixture added.
   - `transport-matters-spaces-slice5--plan.md` symbol `test_store_session_resolution`: the tests request `space_store: SpaceStore`, so execution will fail with an unknown pytest fixture before package import correctness is exercised.
   - Repo pattern evidence: live `api/src/transport_matters/session/conftest.py` symbol `test_db` and `api/src/transport_matters/api/v1/conftest.py` symbol `test_db` define fixture functions, not import only snippets.

   Proposed correction: in Slice 2, replace the import only `api/conftest.py` snippet with a complete shared fixture that creates and migrates `TestDb`, opens an async pool with `create_async_pool`, yields `SpaceStore(conn)`, and drops the test database after use. Keep the import path as `from transport_matters.space.store import SpaceStore`.

## Positive checks

- Live `transport_matters.session` layout has the expected package shape: domain files under `api/src/transport_matters/session/`, tests co located under `session/test_*.py`, and public DTOs/routes under `api/src/transport_matters/api/v1/session_models.py` plus `session_routes.py`.
- New Space domain paths in the plans consistently use `api/src/transport_matters/space/__init__.py`, `space/models.py`, `space/detection.py`, `space/store.py`, and co located `space/test_*.py` tests.
- Public Space routes and DTOs stay in `api/src/transport_matters/api/v1/space_routes.py`, including `SpaceSummary`, `WorktreeSummary`, and `CanvasSummary`.
- `workspace.py` remains referenced only as the existing `transport_matters.workspace` helper surface. No plan moves it.
- Exact stale refs were not found for `transport_matters.space_models`, `transport_matters.space_detection`, `transport_matters.space_store`, or top level `api/src/transport_matters/space_*.py` module paths.
- Alembic remains on `api/migrations/versions/0006_spaces_foundation.py` and `api/src/transport_matters/session/test_migrate.py`; the package move does not affect migration location.
- Repo worktree check before review output was pristine: `git status --short` returned no entries.

## Verification

- `git status --short`
- `fmm_list_files(directory="api/src/transport_matters/session")`
- `fmm_file_outline(file="api/src/transport_matters/session/__init__.py")`
- `fmm_file_outline(file="api/src/transport_matters/workspace.py")`
- `fmm_file_outline(file="api/src/transport_matters/session/conftest.py")`
- `fmm_file_outline(file="api/src/transport_matters/api/v1/conftest.py")`
- `rg` checks over all six plan files for stale module paths, route placement, pytest invocations, and missing fixture definition.
