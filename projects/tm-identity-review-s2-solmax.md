# Identity slice 2 deep review

PR: `#326`

Base: `feat/multi-launch` at `a55371ff06aa4d10ff6fb690ef5c1dc1e227dfcb`

Head: `ml/identity-s2` at `33f89b8308eb92164b4acf8237be005d18b7132e`

Reviewed range: `a55371ff06aa4d10ff6fb690ef5c1dc1e227dfcb...33f89b8308eb92164b4acf8237be005d18b7132e`

Verdict: 0 Blockers, 2 Majors, 2 Minors.

## Four required answers

| Question | Answer | Basis |
| --- | --- | --- |
| 1. Is no seeding structurally unrepresentable, with the old pre `#321` path still absent? | Yes | The router reaches a service whose only repository capability is `readSnapshot`. The snapshot exposes three read methods. The Postgres adapter starts a repeatable read, read only transaction and issues only `SELECT`. No production path can express reconciliation, insertion, update, deletion, worktree creation, or checkout materialisation. |
| 2. Is the whole Space, Worktree, Canvas tuple verified from one repeatable read snapshot? | Yes | Both service operations perform all database reads through one callback bound to one `pg.PoolClient` between `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY` and `COMMIT`. |
| 3. Does N:1 resolution fail closed for nested, root, symlink, case, trailing, and relative path forms? | No | The cardinality check itself fails closed, but the new canonicalizer can compute a different path from Python when `..` follows a symlink. That can produce the wrong candidate set before the N:1 check. See Major 1. |
| 4. Does the Python conformance test truly bind the Python and TypeScript implementations to one rule? | No | Its canvas fake omits a production Space ownership check and rewrites fixture Space identity. A valid cross Space canvas case therefore differs between the implementations while the suite cannot expose it. The corpus also omits accepted UUID spellings on which the planes disagree. See Major 2 and Minor 1. |

## Findings

### Major 1: canonical path normalization can select the wrong worktree

Locations:

- `packages/space/src/adapters/canonicalPath.ts:canonicalPath`
- `api/src/transport_matters/space/identity.py:canonical_path`
- `packages/space/src/adapters/canonicalPath.test.ts:canonicalPath`
- `packages/space/src/service/SpaceContextService.ts:resolveWorkdirContext`

`canonicalPath` calls `path.resolve` before resolving any symlink. `path.resolve` removes `..` lexically. Filesystem path resolution must resolve a preceding symlink before applying the following `..`.

A read only probe on the review host demonstrates the divergence using the existing `/tmp -> private/tmp` symlink:

```text
input                         Python canonical_path       TypeScript canonicalPath
/tmp/..                       /private                    /
/tmp/../does-not-exist        /private/does-not-exist     /does-not-exist
```

The first result comes from `Path.resolve(strict=False)`. The second follows the new TypeScript algorithm exactly.

This is an identity defect, not only a normalization difference. `resolveWorkdirContext` generates ancestors from the wrong canonical path and queries Postgres with them. If the owner has records for either lexical destination, the service can return a receipt for a different worktree. A root record increases the risk because the wrong path still has `/` as an ancestor. Multiple wrong matches produce `conflict`, but one wrong match produces a false verified identity.

The current test covers a symlink followed by a missing child. It does not cover a symlink followed by parent traversal. Relative and trailing forms inherit the same ordering problem after they become absolute.

Required correction:

1. Match `api/src/transport_matters/space/identity.py:canonical_path` ordering exactly.
2. Add parity cases for an existing directory symlink followed by `..`, including a missing suffix after the traversal.
3. Assert the resulting ancestor query cannot return a lexical sibling in place of the symlink target's sibling.

### Major 2: the Python conformance fake masks a real failure code divergence

Locations:

- `api/src/transport_matters/api/v1/test_acting_context_conformance.py:_install_fixture_store`
- `api/src/transport_matters/api/v1/test_acting_context_conformance.py:_canvas_record`
- `api/src/transport_matters/api/v1/launch_resolution.py:resolve_run_canvas`
- `api/src/transport_matters/space/service.py:SpaceCrudService.get_canvas`
- `packages/space/src/domain/actingContext.ts:resolveContextCanvas`
- `packages/space/src/adapters/PostgresSpaceContextRepository.ts:PostgresSpaceContextSnapshot.findOwnedCanvas`

Consider valid records owned by one owner:

```text
Space A -> Worktree A
Space B -> Worktree B -> Canvas B
claim: Space A, Worktree A, Canvas B
```

The production Python path scopes `get_canvas` to Space A. `SpaceCrudService.get_canvas` loads Canvas B, checks its anchor Worktree B through `_require_owned_worktree`, and emits `space_mismatch` because Worktree B belongs to Space B.

The TypeScript repository loads Canvas B by owner and id. `resolveContextCanvas` sees that it is anchored to Worktree B rather than claimed Worktree A and emits `canvas_worktree_mismatch`.

Both paths reject the claim, but they do not enforce the promised shared failure vocabulary and precedence.

The Python conformance fake cannot expose this difference:

- `FixtureSpaceService.get_canvas` never performs the production anchor Worktree and Space check.
- `_canvas_record` discards the fixture canvas `space_id` and assigns the caller's requested Space.
- The existing `canvas worktree mismatch` fixture points at an absent anchor Worktree. The production schema has an owner scoped foreign key from Canvas to its anchor Worktree, so that fixture does not represent a valid persisted state.

The test therefore proves agreement with a simplified fake rather than agreement with `SpaceCrudService.get_canvas` and `resolve_run_canvas`.

Required correction:

1. Add valid fixture Worktrees for both same Space and cross Space canvas mismatch cases.
2. Make the Python fixture adapter derive canvas Space from its real anchor Worktree and apply the production ownership rule.
3. Preserve Python's shipped precedence, or explicitly adjudicate and change the shared contract before later slices depend on error identity.
4. Add a detector that fails if a fixture canvas refers to an absent anchor Worktree.

### Minor 1: the shared corpus does not pin the UUID grammar shared by both planes

Locations:

- `packages/contract/src/space/wire.ts:isCanonicalUuid`
- `packages/space/src/domain/actingContext.ts:validateActingContextCandidate`
- `api/src/transport_matters/space/models.py:_UuidId.parse`
- `api/src/transport_matters/api/v1/ids.py:parse_uuid_id`
- `api/src/transport_matters/api/v1/test_acting_context_conformance.py:_VERIFY_FIXTURES`
- `packages/contract/fixtures/space-parity.json:invalid space id`

TypeScript accepts only canonical hyphenated UUID strings. Python delegates to `uuid.UUID`, which also accepts compact hex, braces, and `urn:uuid:` spellings and normalizes them to the same UUID.

There is another vocabulary difference for the empty string. The TypeScript service emits the matching `invalid_*_id` code. Python `parse_uuid_id` treats `""` as absent, after which a Canvas launch emits `canvas_affinity_required`.

The corpus includes canonical valid UUIDs and `not-a-uuid`. It includes none of these boundary spellings, so the Python test and TypeScript test both pass while public behavior differs.

This does not authorize a different UUID value, so it is a Minor rather than a Major. It still contradicts the one rule conformance claim.

Required correction: choose one grammar, enforce it at both reader boundaries, and add compact, braced, URN, uppercase, and empty string cases for each identity field.

### Minor 2: two unrelated process document commits widen the trust boundary PR

Locations:

- `LESSONS.md:Lessons`
- `WARROOM.md:Current roster`
- `WARROOM.md:Gate split`
- `WARROOM.md:Branch discipline`

The PR contains standalone commits changing context store reference guidance and warroom staffing, CI authority, and branch policy. These changes do not support the Space verification package.

They add no runtime defect, but they widen review and merge scope around a trust boundary slice. Split them into their own change, or land them on the base before rebasing this branch.

## Positive verification

### Structural no seeding trace

The production call chain is:

```text
packages/space/src/server/spaceRouter.ts:createSpaceRouter
  -> packages/space/src/service/SpaceContextService.ts:verifyActingContext
  -> packages/space/src/service/SpaceContextService.ts:resolveWorkdirContext
  -> packages/space/src/ports.ts:SpaceContextRepository.readSnapshot
  -> packages/space/src/adapters/PostgresSpaceContextRepository.ts:PostgresSpaceContextRepository.readSnapshot
  -> packages/space/src/adapters/PostgresSpaceContextRepository.ts:PostgresSpaceContextSnapshot
  -> SELECT only
```

`SpaceContextRepository` exposes only `readSnapshot`. `SpaceContextSnapshot` exposes only:

- `findOwnedWorktree`
- `findOwnedCanvas`
- `listOwnedWorktreesByCanonicalPaths`

The adapter begins the transaction as repeatable read and read only. PostgreSQL itself rejects writes in that transaction. Production code under `packages/space/src` contains no mutation query. Mutation SQL appears only in integration test setup and the deliberate concurrent delete probe.

The pre `#321` Python shape had `SpaceCrudService.resolve_cwd(create=True)` and `_materialize_missing_worktree`, including startup and session resolution callers. Commit `df052e65` removed those paths. Neither symbol appears in the reviewed production tree, and the new package does not import the Python detection or CRUD service.

Conclusion: the old seeding path was not resurrected.

### Snapshot integrity trace

`SpaceContextService.verifyActingContext` validates string syntax, then performs the owned Worktree read and owned Canvas read inside one `readSnapshot` callback.

`SpaceContextService.resolveWorkdirContext` canonicalizes one input, computes its exact ancestors, then performs the candidate Worktree read and root Canvas read inside one `readSnapshot` callback.

`PostgresSpaceContextRepository.readSnapshot` acquires one client, begins one repeatable read, read only transaction, awaits the complete callback, commits, and releases the client. Error paths attempt rollback before release.

The integration test pauses after the Worktree query, deletes the Canvas through another connection, then confirms the first verification still sees the pre deletion Canvas while a later transaction does not.

Conclusion: the database tuple is one snapshot.

### N:1 cardinality

`canonicalPathAncestors` produces exact path values rather than prefix SQL. The repository returns every owner scoped Worktree whose stored canonical path equals one ancestor. `resolveWorkdirCandidate` returns:

- zero matches: `worktree_not_found`
- one match: continue
- two or more matches: `conflict`

This correctly fails closed for duplicate exact paths, parent plus nested registrations, and matches across Spaces for the same owner. Symlink ordering in Major 1 compromises the candidate set before this correct cardinality rule runs.

### Failure vocabulary

The TypeScript domain returns only `ActingContextFailureCode` from `@tm/contract/space`. The router's status classes match the documented Python classes:

- invalid ids and incomplete affinity: 400
- missing Worktree or Canvas: 404
- Space mismatch: 403
- unavailable Worktree, canvas anchor mismatch, and N:1 conflict: 409

`invalid_request` is limited to malformed HTTP envelope input before the service is called. It is transport vocabulary rather than a second acting context domain result.

Major 2 and Minor 1 are the remaining cross plane vocabulary failures.

### Narrow verification

The new repository reads persisted identity, lifecycle, canonical path, and canvas anchor facts. It does not project or check live checkout presence, inspect Git metadata, or use Python's `ResolvedWorktree.missing`. Filesystem access is limited to canonical path normalization for workdir lookup. This matches the requested narrow verifier boundary.

### Architecture

- `packages/space/src/domain` contains pure rules.
- Database and filesystem effects remain under adapters.
- The service depends on ports.
- Other packages import `@tm/space` only through its public index.
- The import graph gate forbids browser imports of the product plane package and deep imports into package internals.
- The Gateway mounts the router under `/v1`.
- The failure constants remain in `@tm/contract/space`.
- Every new file is below 700 lines. Every production function is below the 150 line threshold.

The public index is broader than current production consumers, but each export belongs to the context's service, port, adapter, or composition boundary. I found no duplicate authority and do not count the barrel as speculative implementation.

### Scope disposition

These changes are necessary build and gate wiring, not scope findings:

- `.github/workflows/ci.yml` adds Space typecheck and Postgres integration execution to the product plane job.
- `justfile` adds Space typecheck and tests to the repository recipes.
- `api/tests/test_affected_script.py` updates the mocked pnpm dependency closure so contract and common changes select the new package.
- `packages/gateway/package.json`, `pnpm-lock.yaml`, and the import graph test wire the package and its boundary.

The process document commits are the only unrelated scope expansion found.

### Forward integration note

The current desktop and shell browser origin is Python. Its narrow Gateway proxy exposes Runtime and Activity routes, not the new Space acting context routes. The S2 plan explicitly says the surface ships dark, so this is not counted as an S2 finding. Before S4 records browser verification results, that slice must either expose these routes through the current same origin bridge or complete the planned Gateway front door transition.

## Verification boundary

- The shared Git working tree was pristine before review.
- The exact local and remote PR head was `33f89b8308eb92164b4acf8237be005d18b7132e`.
- The exact PR base was `a55371ff06aa4d10ff6fb690ef5c1dc1e227dfcb`.
- `git diff --check` reported no whitespace errors.
- GitHub reported all nine PR checks successful: backend lint, backend test, frontend, product plane, frontend end to end, desktop, backend package, desktop standalone, and Linux wheel Gateway spawn.
- No local repository gate was run because this review was strictly read only in a shared working tree. The review does not claim local test evidence.
- The path comparison probes were read only.
- No repository write was made.

## Delta re-verification at `c371a64f35a31d4757b5479927aacb7115b86f36`

Delta reviewed: `b98cd998...c371a64f`

Verdict: still open, 1 Blocker.

The fix round closes the original cross Space conformance finding, UUID grammar finding, and process document scope finding. It also fixes the original symlink followed by parent traversal example. Q3 remains open at a different symlink boundary.

### Required answers

| Question | Answer | Basis |
| --- | --- | --- |
| 3. Does N:1 resolution truly fail closed across normalization, ordering, and boundary cases? | No | Deepest match and duplicate cardinality now fail closed, and existing symlink traversal order is correct. A dangling symlink is still preserved lexically by TypeScript while Python resolves its missing target. This changes the ancestor candidate set before cardinality is evaluated and can verify an unrelated lexical parent Worktree. |
| 4. Does the shared corpus truly bind TypeScript to Python `resolve_run_canvas`? | Yes | Both planes load the same acting context and UUID corpora. The Python path enters through `POST /v1/capture/prepare`, calls the shipped `resolve_run_canvas`, and exercises inherited `SpaceCrudService.resolve_launch_worktree` and `get_canvas` checks. The fixture service supplies storage rows and derives Canvas Space from a real owner scoped anchor Worktree. The TypeScript path drives `SpaceContextService`. Fixture validation rejects absent or cross Space anchors. |

The controlled mutation is meaningful. Replacing `space_mismatch` with `canvas_worktree_mismatch` changes only the cross Space Canvas case because that is the only corpus case where the Canvas anchor belongs to another Space. The same Space anchor mismatch must continue returning `canvas_worktree_mismatch`, so its continued success is correct. The checkout projection override fixes `missing=False` because live checkout presence is outside the narrow S2 verifier.

### Blocker: dangling symlinks still produce a false candidate set

Locations:

- `packages/space/src/adapters/canonicalPath.ts:canonicalPath`
- `api/src/transport_matters/space/identity.py:canonical_path`
- `packages/space/src/service/SpaceContextService.ts:resolveWorkdirContext`
- `packages/space/src/adapters/canonicalPath.test.ts:canonicalPath`

`canonicalPath` resolves each candidate with `realpathSync.native`. A dangling symlink makes that call raise `ENOENT`. The catch branch treats the symlink as an ordinary missing path and retains its lexical name. Python `Path.resolve(strict=False)` reads the symlink and incorporates its target even when that target is missing.

A read only probe against an existing dangling system symlink on the review host demonstrates the shipped seam divergence:

```text
input
/System/iOSSupport/usr/lib/swift/libswiftQuickLook.dylib

TypeScript canonicalPath
/System/iOSSupport/usr/lib/swift/libswiftQuickLook.dylib

Python canonical_path
/System/iOSSupport/System/Library/Frameworks/QuickLook.framework/Versions/A/QuickLook
```

The same divergence persists with a missing suffix appended.

This can produce a false verified identity. If a dangling link under `/owned` targets a missing checkout under `/other`, Python identity belongs under `/other`. TypeScript retains the link under `/owned`, includes `/owned` in `canonicalPathAncestors`, and can select an owner scoped parent Worktree registered at `/owned`. The later duplicate check sees one candidate and returns a receipt.

Required correction:

1. Match `Path.expanduser().resolve(strict=False)` for a symlink whose target is missing.
2. Add a dangling directory symlink case with a missing target and missing suffix.
3. Assert that lexical parent Worktrees cannot enter the candidate set for that input.

### Fix round blast radius

The fix commit changes 29 files with 1,254 additions and 222 deletions. The added surface remains inside the five S2 deliverables: shared fixture contracts, Python and TypeScript conformance, canonical resolution, read only Postgres adapter contracts, and Gateway composition tests. Every changed production path supports those deliverables. No additional regression was found.

The disputed `(owner, canonical_os_path)` constraint was not raised by this reviewer. The current service does not depend on that constraint. It queries all owner scoped exact ancestor matches, selects the deepest path, and returns `conflict` when that selected path has more than one record.

### Delta verification boundary

- Local and remote PR head matched `c371a64f35a31d4757b5479927aacb7115b86f36`.
- PR base remained `a55371ff06aa4d10ff6fb690ef5c1dc1e227dfcb`.
- `git diff --check b98cd998..c371a64f` reported no whitespace errors.
- All nine GitHub checks passed.
- No local repository gate was run under the shared worktree read only constraint.
- The canonicalization probes imported the shipped TypeScript function and Python helper without modifying the repository.
