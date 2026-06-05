# S2 review — `@tm/space` control-plane verification context (PR #326)

Reviewer: Opus (independent, different family from the builder).
Target: `ml/identity-s2` @ `33f89b83`, base `feat/multi-launch` (`97a80f56`).
Tree verified pristine (`git status --porcelain` empty) before and after review.
Read-only throughout; no repo writes, no subagents.

**Counts: 1 blocker, 3 major, 9 minor.**

Shape of the change: of 1688 added lines in the S2 commit, ~1010 are tests
(`packages/space` 684, Python conformance 196, gateway 109, import-graph 24).
Production code is ~450 lines. The PR also carries two pre-existing branch
commits (`d50b2d82` WARROOM.md, `e4505aa7` LESSONS.md) that are not the
builder's S2 work.

## What is genuinely right

Recording this first because two of the brief's priority questions come back
clean, and the answers are load-bearing for the findings below.

**The repeatable-read claim is real (Q1).**
`PostgresSpaceContextRepository:readSnapshot` takes one client from the pool,
issues `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY`, hands
`PostgresSpaceContextSnapshot` that same `pg.PoolClient`, and commits. Every
read in the tuple goes through `this.client`. Nothing escapes to a second
connection or a second transaction, and the service issues exactly one
`readSnapshot` per public call
(`SpaceContextService:verifyActingContext`, `:resolveWorkdirContext`). Postgres
takes the REPEATABLE READ snapshot at the first statement rather than at
`BEGIN`, which is harmless here: the first statement is the first tuple read.

**The consistency test discriminates (Q2, for that test).**
`pgIntegration.test.ts` — "cannot observe a torn tuple when a canvas is deleted
between row reads" — pauses inside the snapshot after the worktree read,
commits a `DELETE` from a second connection, resumes, and asserts the receipt
still issues. Under READ COMMITTED the second `SELECT` would take a fresh
snapshot, miss the canvas, and return `canvas_not_found`. The test goes red if
the isolation level regresses. It also proves the follow-up read on a fresh
snapshot *does* see the deletion, so it is not merely asserting staleness.

**The no-seeding proof is structural (Q3).**
`ports.ts:SpaceContextRepository` exposes only `readSnapshot`;
`ports.ts:SpaceContextSnapshot` exposes three finders. There is no write method
to call, so seeding is unrepresentable at the type level, and the `READ ONLY`
transaction makes it unrepresentable at the database level as well
(`25006` on any write). `SpaceContextService.test.ts:"makes writes
unrepresentable on the repository interfaces"` pins the interface key sets with
`expectTypeOf(...).toEqualTypeOf`, so adding a write method fails typecheck.
This is the real proof, not a call-sequence assertion.

**Failure vocabulary (Q5, partial).** No second taxonomy is minted. Every code
the domain emits is typed as `ActingContextFailureCode` from
`@tm/contract/space`, so a new string cannot compile. Precedence in
`domain/actingContext.ts` matches the declaration order of
`ACTING_CONTEXT_FAILURE_CODES` exactly, and the corpus pins it.

**Architecture conformance (Q6).** Clean. `domain/` is pure (`pathAncestors.ts`
uses `node:path` for string arithmetic only, no IO). The service depends on
`ports.ts`, never on `adapters/`. `importGraphBoundary.test.ts` was extended to
prove no external import reaches `packages/space/src` except through
`src/index.ts`, and that browsers cannot import `@tm/space` at all. Package
shape matches `packages/AGENTS.md` and `@tm/activity`.

**Scope (Q7).** `.github/workflows/ci.yml`, `justfile`, and
`api/tests/test_affected_script.py` are necessary, not creep: each registers
`@tm/space` in an existing enumeration of product-plane packages
(`typecheck`, `test`, and the affected-script's fake workspace listing). The
three edits are the minimum required for the new package to be gated at all.
Omitting them would have been the defect.

---

## Blocker

### B1 — `resolveWorkdirContext` enforces a different containment rule than the shipped Python one; nested worktrees resolve to `conflict`

`packages/space/src/service/SpaceContextService.ts:resolveWorkdirContext`,
`packages/space/src/domain/actingContext.ts:resolveWorkdirCandidate`,
`packages/space/src/domain/pathAncestors.ts:canonicalPathAncestors`

The TypeScript path builds every ancestor of the canonical cwd, asks the
repository for all owner-scoped worktrees whose `canonical_os_path` matches
*any* of them, and then treats **any** multiplicity as ambiguity:

```
if (candidates.length === 0) return failure("worktree_not_found");
if (candidates.length !== 1) return failure("conflict");
```

Python — the plane this slice exists to mirror — resolves containment in two
stages, and only the second stage can produce `conflict`:

1. `api/src/transport_matters/space/detection.py:containing_worktree` —
   docstring: *"Return the deepest detected Workdir containing one canonical
   path"*. It filters to containing worktrees and takes
   `max(..., key=len(path.parts))`. Nesting is resolved deterministically and
   never raises.
2. `api/src/transport_matters/cli/space_bootstrap.py:bootstrap_cli_space` then
   calls `list_worktrees_by_path(detected.path)` — one exact path
   (`space/store_worktree_ops.py`: `WHERE owner = %(owner)s AND
   canonical_os_path = %(path)s`) — and raises `conflict` only when that single
   path belongs to multiple Spaces.

So Python's rule is "deepest containing worktree wins; conflict only when one
path maps to N Spaces". The new service's rule is "any two matches anywhere up
the ancestor chain is a conflict". These are different rules, and the schema
permits both situations independently: `space_worktree` is unique on
`(space_id, canonical_os_path)` (migration `0032_space_worktree_ownership`), so
one owner may legitimately hold both `/repo` and `/repo/nested` as distinct
worktrees, in the same Space or different ones.

Failure scenario: owner `local` has a worktree registered at
`/Users/x/proj` and another at `/Users/x/proj/.claude/worktrees/feature`
(git worktrees nested under their own checkout — the layout this repository
itself uses). A gateway `POST /v1/spaces/acting-context/resolve-workdir` with
`cwd = /Users/x/proj/.claude/worktrees/feature/packages/space` returns
`conflict` / HTTP 409. Python, given the same cwd, returns the `feature`
worktree. The two planes disagree on the answer for an ordinary layout, which
is precisely the divergence §2 and the S2 goal ("provably enforce one rule")
exist to prevent.

The corpus does not catch it: `packages/contract/fixtures/space-parity.json`
has exactly one ambiguity case, `"ambiguous workdir"`, and its two worktrees sit
at the *same* path `/worktrees/shared`. That is the N-Spaces-one-path case,
which both planes agree on. There is no nested-containment fixture in either
plane, so this divergence is invisible to `just check && just test`.

The slice ships dark, so nothing is broken for a user today. It is a blocker
because the rule is the deliverable, S4–S6 inherit it unchanged, and
fail-closed makes it safe rather than correct.

Fix: pick the deepest containing candidate and reserve `conflict` for a tie at
that depth — `conflict` when two or more candidates share the longest
`canonicalPath`, otherwise the deepest wins. That is a change inside
`resolveWorkdirCandidate` plus a nested fixture added to the shared corpus. If
the owner intends flat-fail-closed instead, that is a contract decision and
should be written into the plan and the corpus, because it is not what §4's
"containing-worktree normalisation" reads as and it is not what Python does.

---

## Major

### M1 — The "zero row writes" probe cannot fail for the most plausible violation

`packages/space/src/pgIntegration.test.ts:rowCounts`, used by
`:"performs zero row writes and leaves Git worktrees unchanged"`

The probe compares `count(*)` over `space`, `space_worktree`, and `canvas`
before and after the call. Row counts are invariant under `UPDATE`, and
seed-on-read almost always presents as an `UPDATE`/upsert, not an `INSERT`:
touching `updated_at`, reconciling `lifecycle_state`, backfilling
`workspace_slug`/`workspace_hash`, or a `_materialize_missing_worktree` that
finds an existing row. §7 of the plan names exactly these ("no
create-on-resolve"). An `INSERT` followed by a compensating `DELETE` also nets
to zero.

Failure scenario: a future change adds `UPDATE space_worktree SET updated_at =
now() WHERE worktree_id = $1` inside the snapshot read. The probe stays green
and reports "zero row writes". (The `READ ONLY` transaction would in fact
reject it at runtime — but then the probe is asserting a property it does not
measure, and the test named as the S2 gate item is not the thing holding the
line.) The plan's gate wording is literal: *"a transaction probe asserting zero
row writes"*.

Fix: compare table *contents*, not cardinality — e.g. `SELECT md5(string_agg(t::text, '|' ORDER BY t::text))`
per table, or select the full ordered rows before and after. Same cost, and it
goes red on an `UPDATE`. Optionally add the direct proof that the guarantee is
enforced rather than merely respected: assert `SHOW transaction_read_only` is
`on` inside the snapshot.

### M2 — The Python conformance test silently drops every workdir-resolution fixture, including a `shipped` one

`api/src/transport_matters/api/v1/test_acting_context_conformance.py:_VERIFY_FIXTURES`

```
_VERIFY_FIXTURES = [f for f in json.loads(_CORPUS.read_text())
                    if f["operation"] == "verify_acting_context"]
```

Three of the nineteen fixtures are `resolve_workdir_context`, and all three are
filtered out. `packages/contract/src/space/space.test.ts:"marks only the no-seed
unmatched-workdir outcome as proposed"` asserts that `"unmatched workdir"` is
the *only* `proposed` fixture — so `"ambiguous workdir"` → `conflict` and
`"unique containing workdir"` → receipt are both asserted to be **shipped
Python outcomes**. Nothing in either plane executes Python for those two
claims. The TypeScript side runs all nineteen
(`SpaceContextService.test.ts:it.each(actingContextParityFixtures)`).

Failure scenario: Python's containment or conflict behaviour changes (or, per
B1, already differs from what the corpus implies for nesting). The corpus still
labels the expectation `shipped`, the TS suite passes because it tests itself,
and the Python suite never looks. The cross-plane proof the slice was built for
has a hole exactly where B1 lives.

Fix: either execute the workdir fixtures against the Python containment path
(`space/detection.py:containing_worktree` + `list_worktrees_by_path`), or, if
that path is genuinely unreachable from `_resolved_domain_request`, assert the
filter's justification in the test — the excluded set must equal the expected
names, and the corpus should carry the reason. Also add a non-vacuity guard:
`assert len(_VERIFY_FIXTURES) == 16` (or `> 0`) so a corpus rename cannot
reduce the parametrisation to an empty, silently-passing set.

### M3 — The integration DDL hand-writes column names and has no drift guard, against an established repo pattern that has both

`packages/space/src/pgIntegration.test.ts` (`beforeAll` DDL)

The suite creates `space`, `space_worktree`, and `canvas` in a throwaway schema
with literal column names, duplicating the literals that also appear in
`PostgresSpaceContextRepository`'s SQL. The house pattern for exactly this
situation is `packages/activity/src/testSupport/pgIntegrationHarness.ts`, whose
header states the discipline: minimal DDL, but *"sourcing every column name
from the shared `postgresSchema.ts` constants so it cannot drift silently"*,
with the schema **shape** guarded cross-plane by
`api/.../session/test_activity_pg_contracts.py` against the real alembic
migrations.

`@tm/space` has neither: no shared column constants, and no test comparing its
expected columns against `api/migrations/versions/0032_space_worktree_ownership.py`.
This is also the `docs/ARCHITECTURE.md` "Magic string rule" / "Identifiers and
literals standard" the brief names.

Failure scenario: a migration renames `space_worktree.canonical_os_path` (or
drops the `owner` column in favour of a join table). The repository's SQL breaks
in production. The unit test still passes — its fake client matches on
`sql.includes("FROM space_worktree AS w")` and returns a hand-built row object.
The integration test still passes — it created the old schema itself. Both
planes green, gateway 500s on every verification.

Fix: follow the activity precedent — a `postgresSchema.ts`-style constants
module in `adapters/`, consumed by both the repository SQL and the test DDL,
plus a cross-plane column-set assertion against migration 0032.

---

## Minor

Listed in rough value order. Per the standing rule these are in scope for the
slice, not follow-ups.

**m1 — Aborted connection returned to the pool.**
`PostgresSpaceContextRepository:readSnapshot` calls `client.release()` in
`finally` on every path. If `COMMIT` throws and the subsequent
`ROLLBACK` also fails (`.catch(() => undefined)` swallows it), a client with an
open or aborted transaction goes back to the pool and the next borrower gets
`25P02 current transaction is aborted`. Pass the error to discard the
connection: `client.release(error)` on the failure path.

**m2 — `gatewayDeps.ts` has no test.** `packages/space/src/gatewayDeps.ts`
carries real logic: an idempotent `close()`, and a `closed` flag that suppresses
`onPoolError` after shutdown. Neither branch is exercised.
`packages/activity/src/gatewayDeps.test.ts` is the precedent and covers exactly
these (double-close, close ordering, failure-path release).

**m3 — Unknown lifecycle state becomes a 500, not a failure code.**
`PostgresSpaceContextRepository:lifecycleState` throws `TypeError` on any value
outside `creating|active|deleting`. Adding a fourth state in a migration turns
every verification touching such a row into an unhandled 500 rather than
`worktree_unavailable`. It fails closed, so it is safe, but the router has no
error handler and the response carries no contract vocabulary. Consider mapping
an unrecognised state to `worktree_unavailable`.

**m4 — Speculative public surface on a dark slice.** `packages/space/src/index.ts`
exports `PostgresSpaceContextRepository`, `canonicalPath`, `SpaceContextService`,
`SpaceContextRepository`, `SpaceContextSnapshot`, `CanonicalPathResolver`,
`StoredContextWorktree`, and `StoredContextCanvas`. The only external consumer
is `@tm/gateway`, which uses `createSpaceRouter`, `SpaceRouterDeps`,
`createSpaceGatewayDeps`, `SpaceGatewayDeps`, `SpaceGatewayDepsConfig`, and
`ActingContextResult`. The rest have zero consumers, and re-exporting the
Postgres adapter widens the barrel that `importGraphBoundary.test.ts` exists to
keep narrow. Tests import via relative paths and do not need them.

**m5 — Brand constructors bypassed in a gateway test.**
`packages/gateway/src/app.test.ts` builds the receipt as
`{...} as Extract<ActingContextResult, { receipt: unknown }>["receipt"]`.
`ActingContextReceipt` is exported from `@tm/contract/space`, and
`asSpaceId`/`asWorktreeId`/`asCanvasId` are the pinned reader-boundary
constructors (`space.test.ts:"brands aggregate identity keys and constructs them
at reader boundaries"`). The cast reintroduces the raw-string path the brands
exist to close, in the one file that documents the mount contract.

**m6 — Dead `ORDER BY`.**
`PostgresSpaceContextSnapshot:listOwnedWorktreesByCanonicalPaths` sorts by
`canonical_os_path, worktree_id`, but the only consumer discards the list unless
it has exactly one element. The ordering buys nothing today. (It becomes
meaningful under the B1 fix, which is a reason to land B1, not a reason to keep
an unused sort.)

**m7 — `JOIN space` is guaranteed by a foreign key.** Both worktree queries
join `space` on `(owner, space_id)`. Migration 0032 declares
`space_worktree_space_fk FOREIGN KEY (owner, space_id) REFERENCES space(owner,
space_id) ON DELETE CASCADE`, so a worktree row cannot exist without its space
row with the same owner. The join can never filter anything out; it reads as a
check that the schema already makes impossible.

**m8 — No index serves the workdir query.**
`WHERE w.owner = $1 AND w.canonical_os_path = ANY($2::text[])` cannot use
`space_worktree_space_path_uq`, whose leading column is `space_id`. Every
workdir resolution is a sequential scan. Small table today; worth an index on
`(owner, canonical_os_path)` if this becomes a boot-path query in S4–S6.
(Python's `list_worktrees_by_path` has the same shape and the same gap.)

**m9 — Python test couplings.** `test_acting_context_conformance.py` imports the
private `capture_rpc_routes._resolved_domain_request`, and locates the corpus
with `Path(__file__).resolve().parents[5]` — depth-relative path arithmetic that
breaks silently on any file move and is the failure class that has bitten this
repo before. A named repo-root helper (or a pytest fixture resolving the corpus
once) removes both.

---

## Verdict

Nothing here is harmful. The transaction design is right and the no-seeding
boundary is a real structural proof rather than a test-shaped one — the two
hardest things in the slice are done well. The blocker is a semantic divergence
from the shipped Python containment rule that the shared corpus happens not to
cover, and the three majors are all the same shape: a proof that does not
actually execute the property it names (row counts for writes, a filtered
parametrisation for cross-plane parity, a self-authored schema for schema
conformance). Fixing B1 plus a nested fixture, and tightening the three probes,
lands this cleanly.

---

# Delta re-verification — head `c371a64f` (2026-07-26)

Reviewed the delta `33f89b83 → c371a64f` (the pre-rewrite SHA I originally
reviewed against the current head). Tree pristine at `c371a64f`. Read-only.

**Result: 12 of my 13 findings closed at the mechanism level. 1 still open (M3,
partially).**

## Blocker B1 — CLOSED at the mechanism level

`domain/actingContext.ts:resolveWorkdirCandidate` now takes the ancestor list
and iterates it deepest-first (`canonicalPathAncestors` returns cwd → root), so
the first depth that has any candidate decides: exactly one → resolve, more than
one at that same depth → `conflict`. That is Python's two-stage rule
(`space/detection.py:containing_worktree` deepest-wins, then `conflict` only
when one path maps to N Spaces), reproduced faithfully.

The new fixture binds it. `space-parity-s2.json:"deepest containing workdir"` —
worktrees at `/worktrees` (space `55555555…`) and `/worktrees/current` (space
`11111111…`), workdir `/worktrees/current/subdir`, expecting the deeper
worktree's receipt — returns `conflict` under the pre-fix code, so the test
would have gone red on the defect it was written for. It is marked `shipped` and
is now executed on the Python plane too
(`test_acting_context_conformance.py:test_python_workdir_resolution_matches_shared_fixtures`
drives the real `containing_worktree`). Correctly, an inactive worktree at the
deepest match still returns `worktree_unavailable` rather than falling through
to a shallower one; both planes agree.

## M1 — CLOSED

`pgIntegration.test.ts:tableContents` replaces `count(*)` with
`to_jsonb(record)::text` over every row of all three tables, ordered and
compared. An `UPDATE` — the seeding shape the count probe was blind to — now
changes the serialised row and fails the assertion. The test measures the
property it names.

## M2 — CLOSED

The Python conformance test now executes the workdir fixtures rather than
filtering them out, carries a non-vacuity guard
(`test_shared_corpora_are_non_vacuous_and_complete`), locates the corpus with a
`pnpm-workspace.yaml` sentinel walk instead of `parents[5]`, and drives the
verify path through a real `TestClient` POST to `/v1/capture/prepare` instead of
monkeypatching the private `_resolved_domain_request`. That also closes m9.

One residual, not raised as open: the workdir test re-implements
`bootstrap_cli_space`'s orchestration in the test body (real
`containing_worktree`, then a fixture store, then the lifecycle and canvas
steps) rather than calling the shipped function. It binds the *rule*; it does
not bind the *call path*, so a reordering inside `bootstrap_cli_space` would not
be caught. Acceptable for S2 — the rule is what the corpus is for — but worth
knowing when S4–S6 lean on it.

## M3 — PARTIALLY OPEN (the one remaining item)

The DRY half is properly closed: `adapters/postgresSchema.ts` now owns the table
and column literals, the repository SQL and the integration DDL both interpolate
them, and `postgresSchema.test.ts` pins the constants to
`contracts/pg-contracts.json`.

The drift-guard half does not yet cover the failure I described.
`api/.../space/test_pg_contracts.py:test_space_reader_columns_exist_in_owner_migration`
asserts the contract columns are a subset of the columns parsed out of a
hardcoded file: `api/migrations/versions/0032_space_worktree_ownership.py`.
Alembic migrations are append-only and never edited after they ship, so 0032's
text is frozen. A rename landing in a future 0033 leaves that assertion passing
forever.

Failure scenario, unchanged from the original finding: migration 0033 renames
`space_worktree.canonical_os_path`. Python's store
(`space/store_worktree_ops.py:_WORKTREE_COLUMNS`) is updated with it. The TS
constants are not. `test_space_reader_columns_exist_in_owner_migration` still
passes (it reads 0032). `postgresSchema.test.ts` still passes (TS constants and
the JSON agree with each other). `pgIntegration.test.ts` still passes (it builds
the old schema from those same constants). Every gate is green and the gateway
500s on every workdir resolution.

The activity precedent this was modelled on does not have the gap:
`session/test_activity_pg_contracts.py` compares the shared JSON against
**Python production constants** (`session/wire_contracts.py`,
`run_lifecycle_contracts.py`, …), which move when the schema moves. The
equivalent here is to assert each contract column against Python's live reader
literals — `store_worktree_ops.py:_WORKTREE_COLUMNS` (note it aliases
`canonical_os_path AS path`) and the canvas equivalent — rather than against a
frozen migration file. Same size of test, and it tracks the schema instead of
its history.

## Minors — all closed

- **m1** — `readSnapshot` now releases explicitly after `COMMIT`, and on the
  error path releases with the error (`client.release(asError(rollbackError))`)
  when `ROLLBACK` itself fails, so a poisoned connection is destroyed rather
  than returned to the pool.
- **m2** — `gatewayDeps.test.ts` added; it asserts `onPoolError` fires before
  close and is suppressed after, and that a double `close()` ends the pool once.
  Both go red if the `closed` guard regresses. A pg smoke variant runs when the
  test DB URL is set.
- **m3** — `lifecycleState` returns `"unknown"` instead of throwing;
  `StoredContextWorktree.lifecycleState` is widened, and `activeWorktree`'s
  `=== "active"` check maps it to `worktree_unavailable`. Fails closed with
  contract vocabulary instead of a 500.
- **m4** — `src/index.ts` pruned to the four symbols `@tm/gateway` actually
  imports. Verified no consumer references a removed export.
- **m5** — `app.test.ts` no longer casts through
  `Extract<ActingContextResult, …>`.
- **m6** — the unused `ORDER BY` is gone.
- **m7** — the FK-guaranteed `JOIN space` is gone from both worktree queries.
  (A new join to `space_worktree` appears in `findOwnedCanvas`, but that one
  earns its place: it supplies `anchor_space_id` for the new cross-space canvas
  check.)
- **m8** — deferred by the builder; ruling below.
- **m9** — closed with M2.

## Dispute ruling — m8, the `(owner, canonical_os_path)` index: **deferral accepted**

The builder is right and the reasoning is the correct one. No guarantee in this
slice depends on that index. Correctness, owner scoping, snapshot isolation, and
fail-closed N:1 are all enforced by the query predicate and the domain rule; an
index changes only how fast the planner satisfies the same predicate, and it
cannot change which rows come back. My finding said as much — it was raised as a
latency note conditional on S4–S6 making this a boot-path query, and there is no
consumer yet.

The scope argument also holds independently: an index is a new alembic revision
against a shared table, which is a storage change, and §8 of the plan is
explicit that no slice in this sequence touches storage. Landing a migration to
optimise a query with zero callers would be the larger error.

The right time is when a consumer lands and the query is on the boot path — S4
or S6 — measured against real inventory rather than assumed. Python's
`list_worktrees_by_path` shares the same gap, so that is one migration covering
both planes rather than two.

## Blast radius of the fix round

~950 added lines, checked for regressions introduced under review pressure:

- **Id lowercasing** in `validateActingContextCandidate` is sound. The regex
  accepts uppercase (`iu` flags), the candidate is lowercased before it reaches
  the DB query and before `resolveClaimedWorktree`'s `spaceId` comparison, and
  Postgres renders `uuid::text` lowercase — so the comparison is now consistent
  where it previously depended on the caller's casing.
- **`canonicalPath` rewrite** (whole-path walk → per-segment realpath) is a real
  improvement: `..` is applied after symlink resolution, which is the POSIX
  semantic and what Python's `resolve()` does. The new tests discriminate — the
  symlink-then-`..` case returns the lexical parent under the old
  implementation, and the test also asserts the lexical parent is absent from
  `canonicalPathAncestors`, tying it to the workdir query.
- **`resolveContextCanvas`'s new `space_mismatch`** branch is only reachable
  when the canvas is anchored to a worktree in a different Space, which
  previously surfaced as `canvas_worktree_mismatch`. It is a deliberate
  precedence change backed by the new `cross space canvas anchor` fixture. Note
  for the record that `space_mismatch` can now be emitted after a successful
  canvas read, so the emitted order is no longer a strict prefix walk of
  `ACTING_CONTEXT_FAILURE_CODES`; whether that matches Python is the deep
  reviewer's Q4, not re-litigated here.
- **Surface** stays inside S2's five deliverables. The additions are constants,
  fixtures, and tests; no new runtime capability, no consumer, storage untouched.
