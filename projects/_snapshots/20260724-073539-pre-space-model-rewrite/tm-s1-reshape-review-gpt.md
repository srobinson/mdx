# PR #316 S1 reshape review

Date: 2026-07-22  
PR: [#316](https://github.com/littleorgans/transport-matters/pull/316)  
Head: `855bd0a938c68123a24178d7c92953e10b720721`  
Reshape baseline: `9ac8d10d2d5304bc579980636729d466e952f404`  
Verdict: **0 blockers, 6 major, 1 minor**

Reviewed against `tm-s1-reshape-proposal.md` v3, Context Matters decision
`019f8a57-c947-7411-8944-be6d9ebfce0f`, and `tm-s1-reshape-panel-gpt.md`.

Builder trust: **low**. The reshape has a coherent aggregate direction, but the low effort build
missed an explicit consumer contract, two malformed metadata cases, two required lifecycle
proofs, and hard repository hygiene gates.

## Findings

### Major 1: malformed Git metadata escapes the three state classifier

Locations: [detection.py:86](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/space/detection.py#L86), [detection.py:130](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/space/detection.py#L130), [detection.py:146](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/space/detection.py#L146), [service.py:399](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/space/service.py#L399)

`_read_gitdir_marker()` can raise `UnicodeDecodeError`. `_resolve_common_dir()` raises
`ValueError` for empty or invalid `commondir`. The surrounding classification boundaries catch
only `OSError` and `RuntimeError`. These errors escape instead of producing
`GitMembership.INCONCLUSIVE`. Projection isolation catches only `SpaceDetectionError`.

One corrupt checkout can therefore fail owner wide Space reads or reconciliation instead of
remaining an isolated unknown projection. This violates the total `git/plain/inconclusive`
contract. The existing malformed marker test covers decodable text only.

Direct reproduction at this head:

```text
empty-commondir RAISED ValueError empty commondir marker: .../commondir
invalid-git-marker-encoding RAISED UnicodeDecodeError 'utf-8' codec can't decode byte 0xff ...
```

Fix the classifier boundary so every metadata read or validation failure returns
`INCONCLUSIVE`, then cover invalid encoding and malformed `commondir`.

### Major 2: the frontend ignores the default Space visibility contract

Locations: [space_routes.py:237](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/api/v1/space_routes.py#L237), [spaceTransport.ts:59](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/www/packages/core/src/spaceTransport.ts#L59), [useSpaces.ts:11](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/www/packages/canvas/src/launcher/useSpaces.ts#L11), [workdirRows.ts:74](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/www/packages/canvas/src/launcher/workdirRows.ts#L74)

The backend correctly emits `showSwitcher = space_count > 1`. `fetchSpaces()` discards the
field and returns only `items`. `useSpaces()` exposes every returned item, and the Workdir rows
render the sole computed default.

The approved model surfaces the default Space in the switcher only when the owner has more than
one Space. The current hook test at [useSpaces.test.tsx:16](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/www/packages/canvas/src/launcher/useSpaces.test.tsx#L16) locks in the leak by returning one default item without consuming
`showSwitcher`.

Preserve the response envelope through the core transport and hook, apply the visibility rule,
and test both one Space and multiple Space responses.

### Major 3: migration downgrade erases durable Space stamps

Location: [0030_space_crud_reset.py:78](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/migrations/versions/0030_space_crud_reset.py#L78)

Both downgrade conversions use `USING NULL::uuid`. Every non null `session.space_id` and
`run_lifecycle_event.space_id` becomes null when 0030 is rolled back. A PostgreSQL probe seeded
a UUID Space stamp at 0030, downgraded to 0029, and read `space_id=None`.

This irreversibly removes historical Space association from sessions and lifecycle events. The
approved design keeps these stamps durable and FK free. Current values are UUID strings, so the
downgrade can cast them. The migration roundtrip test passes because it does not seed a stamp
before downgrade.

Use a checked cast and add roundtrip value preservation for both tables.

### Major 4: valid cross anchor defaults prevent the claimed Worktree delete

Locations: [0030_space_crud_reset.py:328](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/migrations/versions/0030_space_crud_reset.py#L328), [test_space_crud_migration.py:344](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/space/test_space_crud_migration.py#L344), [store.py:58](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/space/store.py#L58)

The model permits a user Canvas anchored to Worktree B to use Worktree A as
`default_worktree_id`. Deleting A then fails at commit on `canvas_default_worktree_fk`. The
current cascade test has one Worktree and gives its user Canvas a null default, so it never
exercises this valid three axis state. No store or service delete seam clears surviving defaults
before deleting the Worktree.

The approved proof requires privileged Worktree deletion to clear surviving defaults, cascade
the anchored subtree and junction rows, and commit atomically. A PostgreSQL reproduction of the
cross anchor state failed at commit on the deferred FK.

Add the guarded deletion transaction and the cross anchor proof. If Worktree deletion is outside
S1, move this acceptance item to a named later slice before merge.

### Major 5: two changed files cross the hard 700 line limit

Locations: [test_capture_rpc_routes.py:325](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/api/v1/test_capture_rpc_routes.py#L325), [test_migrate.py:284](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/session/test_migrate.py#L284)

The reshape changes these file sizes:

| File | Baseline | Head |
| --- | ---: | ---: |
| `api/v1/test_capture_rpc_routes.py` | 697 | 735 |
| `session/test_migrate.py` | 685 | 701 |

The repository rule requires refactoring before adding to a file that would cross 700 lines.
Split Worktree launch resolution cases into a focused module and move reshape migration
assertions into the dedicated Space migration suite. No changed production file exceeds 700
lines, and no changed Python function exceeds about 150 lines.

### Major 6: canonical Worktree path normalization is duplicated across three authorities

Locations: [projection.py:88](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/space/projection.py#L88), [service.py:575](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/space/service.py#L575), [store.py:505](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/space/store.py#L505)

All three new helpers perform `Path(...).expanduser().resolve(strict=False)`. The service and
store versions are identical. Projection adds only nullable input handling.

These copies sit on the identity lookup, runtime projection, and persisted query seams. Future
drift can make a stored Worktree disappear from projection or lookup. This also violates the
repository's explicit zero duplication rule.

Export one canonical path helper from the identity boundary and handle optional values at the
caller.

### Minor 1: the stored and projected boundary retains duplicate and ambiguous types

Locations: [projection.py:23](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/space/projection.py#L23), [models.py:190](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/api/src/transport_matters/space/models.py#L190), [spaceTransport.ts:10](https://github.com/littleorgans/transport-matters/blob/855bd0a938c68123a24178d7c92953e10b720721/www/packages/core/src/spaceTransport.ts#L10)

`SpaceSummary` and `SpaceSnapshot` have identical fields and are repacked in the service.
`Worktree = ProjectedWorktree` retains the retired ambiguous name. `repo_group_key` remains
plain `str` in Python and plain `string` in TypeScript, while the panel requires a nominal
`RepoGroupKey` boundary distinct from `SpaceId`.

No current request schema accepts `repo_group_key`, and no placement or authorization code uses
it. The risk is future type mixing and silent drift. Keep one projection container or make the
summary smaller, remove the alias, and add the nominal group key type at both language
boundaries.

## Verified clean

- Production code contains no `INSERT`, `UPDATE`, or `DELETE` against
  `space_worktree_link`. Detection and reconciliation cannot mutate membership.
- The plain to Git test compares all Space, Worktree, Canvas, and junction rows before read,
  after read, and after reconcile. Its junction is empty, so an additional PostgreSQL probe used
  a real named link and confirmed byte identical rows.
- The forced Git exit 128 test preserves Git classification and the `git:` group label while
  enrichment facts become unknown.
- Default Space creation is idempotent. The partial unique index plus conflict path produces one
  default, and computed membership includes all owner Worktrees without junction rows.
- Junction foreign keys are owner scoped and use `ON DELETE CASCADE` from both Space and
  Worktree. Space deletion removes links without deleting Worktrees or Canvases. Worktree
  deletion removes links and the anchored Canvas subtree when no surviving Canvas default
  targets it.
- Root reciprocity, anchor, parent, and default Worktree constraints reject lone root deletion,
  wrong roots, swapped roots, and cross anchor reparenting.
- Reconciliation materializes Worktrees and roots in one transaction under an advisory
  transaction lock. Partial pairs cannot commit after a crash.
- `repo_group_key` is currently confined to detection, projection, DTOs, and display grouping.
  No authorization or placement consumer exists.
- Explicit named Space launch context is owner scoped and does not require named membership,
  matching the view filter decision.
- Stored Worktrees have no persisted branch, head, primary, missing, or repository group facts.
  MCP refresh input and persisted `canvas.space_id` are removed.

## Verification

- Exact local head and PR head matched `855bd0a938c68123a24178d7c92953e10b720721` before review.
- `git diff --check 9ac8d10d..855bd0a9`: passed.
- Focused PostgreSQL migration, store, and service tests: 36 passed.
- Migration roundtrip: 1 passed.
- Detection and model unit tests: 30 passed.
- Core transport test: 32 passed.
- Shell frontend suite: 168 files and 1,256 tests passed.
- Ruff format, Ruff lint, and mypy checks for the reshape core: passed.
- Exact head GitHub run `29938449826`: all nine jobs passed, including backend, frontend,
  frontend E2E, desktop, product plane, package, and wheel jobs.
- Source tree remained unmodified during review.

## Deferred risk, excluded from counts

Concurrent named link insertion and promotion of that Space to default can pass both trigger
checks and leave a materialized link on the computed default. Both mutation surfaces are
explicitly deferred to the later Space CRUD slice. That slice needs row locking or equivalent
serialization plus a race test.
