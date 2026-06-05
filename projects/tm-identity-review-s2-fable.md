# S2 review — PR #326, `packages/space` verification context (fable, scout-turned-reviewer)

Head `33f89b83`, base `feat/multi-launch`, tree pristine at review time. CI fully green on the head SHA (all 9 checks). Citations are file:symbol.

Counts: **0 blockers, 1 major, 1 minor.** Drift verdict: **planned, one deviation.**

## Constraint verdicts first

Every owner constraint holds:

1. **No seeding — structural, PASS.** `packages/space/src/ports.ts:SpaceContextRepository` exposes only `readSnapshot`; `SpaceContextSnapshot` exposes three find/list reads. The proof is type-level, not call-sequence: `SpaceContextService.test.ts` ("makes writes unrepresentable") pins the exact key sets with `expectTypeOf`, so adding a write method fails the suite by construction. The pg adapter opens `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY`, so even a smuggled write would be rejected by Postgres.
2. **Whole tuple in one snapshot — PASS, genuinely.** `PostgresSpaceContextRepository:readSnapshot` runs both row reads inside one repeatable-read read-only transaction. This is proven against real Postgres, not a mock: `pgIntegration.test.ts` ("cannot observe a torn tuple") pauses the snapshot after the worktree read via a hooked pool, commits a concurrent canvas DELETE, and asserts the in-flight verification still returns the receipt while a fresh snapshot returns `canvas_not_found`. The zero-row-writes probe plus unchanged `git worktree list` is also present, as the plan's gate demanded.
3. **Fail-closed N:1 — PASS** (`resolveWorkdirCandidate` never picks among multiple candidates), but see the Major: it fails closed on a case Python resolves.
4. **Narrow verification — PASS.** No checkout-presence check anywhere in the package; the corpus documents (`contract fixtures.ts:ActingContextFixtureRecords` doc comment) that live projection fields stay Python launch-readiness authority. `canonicalPath` touches the filesystem only to resolve symlink prefixes and explicitly preserves missing suffixes.
5. **Shipped vocabulary only — PASS.** Every failure literal is a member of `@tm/contract/space:ACTING_CONTEXT_FAILURE_CODES`; no `space_not_found`, no new code. The router's `invalid_request` transport reject matches the established literal in `activityRouter.ts` and `runtimeRouter.ts`. HTTP status classes match Python exactly (`spaceRouter.ts:failureStatus` vs `launch_resolution.py:_raise_space_error` and `capture_rpc_routes.py`: 400 invalid/affinity, 404 not-found pair, 403 `space_mismatch`, 409 the rest), and a router test pins the mapping.
6. **One command surface — PASS.** Nothing client-shaped landed in `@tm/contract/space`; the two POST routes serve any caller. `importGraphBoundary.test.ts` now forbids browser imports of `@tm/space` and enforces its single entrypoint.
7. **DRY — PASS.** `@tm/common` `requiredString`/`nonEmptyString`/`safeRecord` reused; the fixture corpus has one owner (`packages/space/fixtures/README.md` points at `@tm/contract/space/testing` instead of keeping a copy); gateway wiring extracts `main.ts:contextDatabaseUrl` shared by Activity and Space instead of duplicating the warn path.

## Major

### M1 — Nested containment conflated with N:1 ambiguity in `resolveWorkdirCandidate`

`packages/space/src/domain/actingContext.ts:resolveWorkdirCandidate` returns `conflict` whenever more than one owned worktree row matches any ancestor path of the cwd. That merges two distinct situations:

- **Same-path N:1** (two worktrees registered at one `canonical_os_path`, which the schema permits per `store_worktree_ops.py` `ON CONFLICT (space_id, canonical_os_path)`): `conflict` is correct and the "ambiguous workdir" fixture pins it.
- **Nested containment** (worktrees at different depths, both containing the cwd): the plan-cited owner rule `space/detection.py:containing_worktree` returns the deepest containing worktree, and `cli/space_bootstrap.py` ships that behavior today. S2 returns `conflict`.

This is not a corner case: a git worktree checkout registered under the primary checkout, exactly the `.claude/worktrees/*` layout this repository itself uses, produces two candidates at different depths for any cwd inside the nested worktree. The result is two planes with two answers, the disease this refactor exists to cure: CLI bootstrap resolves the nested worktree, `resolveWorkdirContext` (the S6 desktop-relaunch recovery path) refuses. The corpus has no nested-containment fixture, so the divergence is invisible to every test.

**Fix in-slice:** among candidate rows, take the deepest `canonicalPath` that has matches; return `conflict` only when that deepest group holds more than one row. Add a nested-containment fixture to `packages/contract/fixtures/space-parity.json` pinning deepest-wins (the service already receives ancestor-ordered input; `canonicalPathAncestors` emits deepest first, so "first path with candidates" is one small loop). If the builder chose conflict-on-nested deliberately as extra-conservative, that is an owner decision to record, not a builder default; as landed it is a deviation from the plan's named owner.

## Minor

### m2 — Conformance fake sits at the service seam and re-implements owner logic

`api/v1/test_acting_context_conformance.py:_install_fixture_store` monkeypatches `SpaceCrudService` with a fake whose `resolve_launch_worktree` re-encodes the `space_mismatch` rule and whose `get_canvas` skips the real service's `_require_owned_worktree` step. Consequently the canvas-side ordering of the real Python path is never conformance-driven: for a canvas whose anchor worktree is cross-space or dangling, real Python (`space/service.py:get_canvas` → `_require_owned_worktree`) emits `space_mismatch`/`worktree_not_found` before the anchor comparison, while the node service emits `canvas_worktree_mismatch`. CRUD invariants plus the transactional S3-delete cascade make those states hard to reach in a consistent database, which is why this is a Minor and not a Major, but the test currently proves less than "one rule" at that hop: the fixture asserting `space_mismatch` exercises the fake, not the service.

**Fix in-slice:** add a cross-space-anchor fixture (the corpus record shape already carries `space_id` on canvases) pinned to whichever code the owner declares canonical, and either drive the real `SpaceCrudService` over a store-seam fake or narrow the fake's claim with a comment stating that service-internal ordering is out of the conformance surface.

## The two flagged risks, judged

- **`ci.yml` / `justfile` / `test_affected_script.py` edits: necessary, not scope creep.** All three are mechanical registration of the new package into the existing gate recipes: `@tm/space` typecheck/test lines beside its peers, and inclusion in the product-plane pg job so `pgIntegration.test.ts` fails closed under `TRANSPORT_MATTERS_TEST_DATABASE_URL` exactly as the Activity precedent does. Nothing else changed in those files.
- **+1770 for a dark slice: accounted for, no speculative surface.** The slice commit is +1688; `WARROOM.md`/`LESSONS.md` are two prior doc commits riding the branch (d50b2d82, e4505aa7), not builder edits. Of the slice: ~730 lines are tests, ~28 lockfile, ~250 gateway wiring and its tests, ~200 the Python conformance test. Production source in `packages/space` is roughly 530 lines and maps one-to-one onto the five deliverables. I found no consumer-less surface beyond barrel exports of the repository/ports (consistent with `@tm/activity`'s barrel convention and needed for composition).

## Drift question (scout's answer)

**This is S2 as planned, with one deviation: M1.** All five deliverables are present in the planned shape: whole-tuple one-snapshot `verifyActingContext`, `resolveWorkdirContext` with `canonical_path` parity (the node `canonicalPath` faithfully mirrors `identity.py:canonical_path` including symlink-prefix resolution with missing-suffix preservation, and has a symlink test), the structural read-only repository, `createSpaceRouter` mounted by the gateway with lifecycle (close-ordering, startup-failure, pool-error) tests, and the Python conformance test consuming the shared corpus. The plan's per-slice gate items all exist: fixture matrix covering every failure code plus N:1 (with a coverage assertion so the corpus cannot silently rot), the repeatable-read consistency test, and the zero-writes/unchanged-git-worktrees probe. The precedence ordering pinned by S1's multi-fault fixtures is preserved verbatim in `validateActingContextCandidate` / `resolveClaimedWorktree` / `resolveContextCanvas`. M1 is the single point where the build's rule diverges from the plan's named owner (`containing_worktree` deepest-wins). One recorded shape note, not a defect: the package omits `src/events.ts` and `src/projections/` from the canonical context shape; a read-only verification context emits no facts, so empty placeholders would be worse.

Second-writer check (my standing first check): none introduced. The package is structurally incapable of writing owned state, and the gateway wiring adds mounts only.

## Builder trust verdict (codex/gpt-sol)

**High craftsmanship, one characteristic seam miss.** The strongest work is exactly where corner-cutting usually happens: the no-seed proof is genuinely structural (type-level key-set pinning) rather than a call-sequence assertion, and the torn-tuple probe drives real Postgres through a paused snapshot rather than mocking the property into existence. Reuse fidelity is excellent (common coercions, corpus single-ownership, Activity conventions for pool lifecycle, status-class parity with a pinning test), and the gateway wiring refactored shared logic out instead of copy-pasting the Activity path. Test rigor is well above baseline; transport parsing fails closed before touching the service. No shortcuts found; the out-of-brief file edits were exactly the necessary gate registrations. The two findings are both the same defect class fable5.md predicts for this builder: each component locally correct while a cross-plane rule (deepest-wins containment; real-service canvas ordering) diverges at the seam. Delegation-worthy for slices of this size, with the seam-level conformance questions named explicitly in the brief and a reviewer holding the cross-plane line.
