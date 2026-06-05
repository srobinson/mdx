# Review — slice 1, `5c77edf0` feat(contract): add Space identity contract (fable)

Scope: one commit on `ml/s6-identity`, parent `963fd8f8`, 51 files, +1332/−345.
Tree at verdict time: only the pre-existing one-line `LESSONS.md` edit. Reviewer
context: I authored the build plan this slice implements.

**Verdict: clean. 0 blockers, 0 majors, 2 minors.** Scope held exactly; this is
slice 1 and nothing else.

## Q1 — Is this slice 1, or did it start slice 2? **Slice 1, scope held.**

Nothing from any later slice is present: no `packages/space`, no
`www/packages/space-client` (verified by directory listing at HEAD), no
verifier or resolver implementation, no ranking logic, no Python change, no
persistence change (`canvasPersistOptions.ts`, `storageKeys.ts`,
`CANVAS_STORE_STORAGE_VERSION` untouched), no seed path. The parity corpus is
plan-S1 deliverable by name ("`@tm/contract/space/testing` (shared parity
fixtures, the cross-plane fixture table)") and is inert data: it describes
expected outcomes for slice 2's service without implementing any of it.

The +1332 accounts cleanly: ~939 lines are the new contract package
(`wire.ts` 114, `fixtures.ts` 194, `parity-fixtures.json` 480, `space.test.ts`
109, barrel/testing/config ~42); the remaining ~390 spread across 44 consumer
files are import moves and `asSpaceId`/`asWorktreeId`/`asCanvasId` wrapping in
test fixtures. Large by line count, mechanical by content.

## Q2 — Is the branding real? **Yes, to exactly the standard the repo ships.**

`packages/contract/src/space/wire.ts` uses the intersection-brand pattern of
`packages/activity/src/ids.ts` (`string & { readonly __brand: … }`), with
`expectTypeOf<string>().not.toMatchTypeOf<SpaceId>()` locked in
`space.test.ts`, and `RepoGroupKey` retains its stronger unique-symbol brand.
The constructors are unchecked casts, exactly like `asRunId`/`asWorkspaceId`;
that is the shipped standard, and shape validation is deliberately not the
brand's job (claims are unverified by design; `MALFORMED_ID` belongs to slice
2's server verification; `route.ts:isDurableCanvasId` keeps the one existing
UUID gate, now returning `CanvasId`).

Construction sites are genuine reader boundaries: `core/transport.ts:fetchMeta`
(wire → `Meta`), `canvas/route.ts:parseCanvasLaunchContext` +
`durableCanvasIdOrNull` (URL → claim),
`capturedRunAdoption.ts:attachableRun` (run wire row → adoption input), test
fixture factories. DTO fields are branded end to end (locked field-by-field in
`space.test.ts`).

Two deliberate open edges, correct for this stage, stated so nobody mistakes
them for coverage: (a) the launch composition chain
(`capturedRunStore.ts:EnsureRunOptions`,
`core/transport.ts:createCapturedRunView`) still types identity as bare
`string`; branded values widen into it silently. That is plan-conformant — the
chain adopts `ActingContextReceipt` in slice 5 — but the brand does not yet
protect launch requests. (b) One interior mint exists (minor m2 below).

## Q3 — Did any behaviour change? **No.**

Every changed production line is a type annotation, an import move, or an
equivalent-value rewrite. Spot-verified the only two candidates:
`fetchMeta`'s `raw.space_id ?? null` became an explicit
`undefined/null → null : asSpaceId(...)` (identical semantics, `as*` is an
identity function at runtime), and `route.ts` parsing kept byte-identical
trim/UUID logic with only return-type narrowing.
`useCommandCenter.ts` wraps a nav param in `asWorktreeId` (runtime identity).
No Python, no DB, no persistence version. Verified `pnpm --filter @tm/contract
test` (12/12), `pnpm --filter @tm/core typecheck`, `pnpm --filter @tm/canvas
typecheck` first-hand; the full `just check && just test` result is the
builder's claim, consistent with everything I ran.

## Q4 — Is the old surface gone? **Yes, completely.**

The gate grep, run first-hand, returns exactly three declaration lines, all in
`packages/contract/src/space/wire.ts`. `core/spaceTransport.ts` now *imports*
the types (type-only) and re-exports nothing typed — the `export * from
"./spaceTransport"` barrel line now carries only `FetchSpacesOptions` and the
fetch/mutation functions, so `@tm/core` no longer exposes any of the three
ids: no compatibility re-export. `paneRecords.ts:CanvasId` deleted; the file
imports all three from `@tm/contract/space` and `ViewerCanvasContext.spaceId`
tightened from `string | null` to `SpaceId | null`. The deleted
`spaceTransport.contract.test.ts` coverage (RepoGroupKey nominality) moved
into `space.test.ts`, not lost. `importGraphBoundary.test.ts` adds both new
subpaths to the allowlist.

## Q5 — The parity corpus. **Neutral in encoding; two semantic pre-decisions embedded (m1).**

Encoding is genuinely language-neutral: plain JSON, string ids, POSIX absolute
paths, exact-key runtime validation in `fixtures.ts:parseParityFixtures` (a
malformed corpus throws at import, so drift cannot pass silently), and
`space.test.ts` asserts every one of the nine failure codes appears plus at
least one receipt case. 15 fixtures cover both operations
(`verify_acting_context`, `resolve_workdir_context`), including the N:1
`AMBIGUOUS_PATH` case, missing-from-disk and presence-unknown worktrees, and
canvas anchor mismatch.

Two mappings are semantic decisions the corpus makes without saying so, which
slice 2 will inherit as spec (m1):

1. "worktree belongs to another space" → `WORKTREE_NOT_FOUND`. Today's Python
   seam answers the same situation with `space_mismatch` (403, via
   `space/service.py:resolve_launch_worktree` →
   `launch_resolution.py:_raise_space_error`). Not-found is the defensible
   anti-enumeration choice, but it is a divergence from shipped behaviour that
   the slice-2 Python conformance test must map consciously, not accidentally.
2. "unmatched workdir" → failure `WORKTREE_NOT_FOUND` rather than a soft
   empty result. Fine as a wire code, but the boot path treats no-match as
   ordinary degradation (plan §4 rule 4), so slice 2's client must map this
   failure to `unresolved`, not to an error surface.

One neutrality caveat, not a defect: fixture paths are pre-canonicalized;
canonicalization itself (`space/identity.py:canonical_path` semantics,
symlinks, case folding) is deliberately out of corpus scope and must stay a
slice-2 implementation concern fed by already-canonical inputs.

## Q6 — What this slice exposes about the plan itself

- The plan's S1 gate wording ("a one-declaration-site grep") is imprecise: the
  natural grep pattern matches the three *new* branded declarations, so the
  pass condition is "exactly three lines, all in
  `packages/contract/src/space/wire.ts`", not zero. The builder interpreted it
  correctly; the plan should say so for future re-runs.
- The plan did not specify the two corpus mappings in m1; the corpus decided
  them. Right mechanism (one fixture table), but the owner should get one
  sentence of visibility on the `space_mismatch` → `WORKTREE_NOT_FOUND`
  divergence before slice 2 hardens it.

## Minors

- **m1 — corpus intent is silent.** Add one comment line each (in
  `fixtures.ts` or the fixture `name`s) stating the anti-enumeration intent of
  cross-space → `WORKTREE_NOT_FOUND` and the boot-degradation intent of
  unmatched-workdir → `WORKTREE_NOT_FOUND`, so slice 2 implements them as
  decisions rather than inheriting them as accidents.
- **m2 — interior brand mint.** `launcher/useCommandCenter.ts` erases a
  `WorktreeId` into a string nav param and re-mints it with `asWorktreeId`
  outside any reader boundary. Typing the nav frame param (or carrying the
  branded value through) would keep construction confined to boundaries per
  the doc's standard. Craftsmanship, not risk: the value provenance is a row
  action that was branded to begin with.

## Builder trust, one line

Scope fidelity is exemplary (exactly S1, resisted every adjacent temptation,
no verifier smuggled in), migration is complete and consistent with typechecks
proving it, and the corpus is genuinely well-built (exact-key validation,
full-taxonomy assertion); the one habit to watch is embedding semantic
decisions (the two m1 mappings) in artifacts without flagging them for review.

## Delta re-review (ceec0a7b)

Delta `5c77edf0..ceec0a7b`, 38 files, +1139/−787. Tree at verdict time: only
the pre-existing `LESSONS.md` line. **Delta verdict: clean. 0 new blockers, 0
new majors, 0 new minors. All prior findings resolved. Dispute: builder's
refutation accepted.**

### Dispositions, each verified in the diff, none cosmetic

- **fable m1 — real.** Every fixture carries `expectation_status`; grep of the
  corpus shows 16 `shipped`, exactly one `proposed` (unmatched workdir), and
  `space.test.ts:"marks only the no-seed unmatched-workdir outcome as
  proposed"` locks it.
- **fable m2 / opus m7 — real.** `launcher/navigation.ts:LauncherScopeParam`
  is a discriminated union of branded members; `NavFrame.param` is no longer a
  string; `useCommandCenter.ts` and row builders carry it end to end. The
  interior re-mint is gone.
- **opus M1 — real.** Worktree records in the corpus are StoredWorktree fields
  only (`worktree_id`, `space_id`, `owner_id`, `root_canvas_id`,
  `lifecycle_state`, `path`); `missing` deleted, with an in-place doc note
  that live checkout presence stays Python launch-readiness authority. The
  unavailable fixture now runs on `lifecycle_state`.
- **opus M2 — real.** `ACTING_CONTEXT_FAILURE_CODES` is ordered as precedence
  with a comment saying so, and three multi-fault fixtures pin selection
  (malformed-id over partial context, missing worktree over missing canvas,
  unavailable worktree over missing canvas), consistent with
  `_resolved_domain_request`'s parse → affinity → worktree → canvas order.
- **opus M3 — real.** `isSpaceId`/`isWorktreeId`/`isCanvasId` live on the
  contract; `route.ts:isDurableCanvasId` and its local UUID regex are deleted;
  `canvasCacheStorage.ts` consumes `isCanvasId`. One UUID rule remains.
- **opus M4 / m8 — real.** Branding now flows through
  `CreateCapturedRunOptions`, `createCapturedRun`/`createCapturedRunView`,
  `RunView`, `RunFilters`, `capturedRunStore.ts:EnsureRunOptions`,
  `CapturedRunPane.tsx` props, `useCapturedRunBinding.ts`,
  `spawn.ts:createCapturedRunRef`, and the `PaneContentRef` carriers. My
  earlier "open edge" note on the launch chain is superseded. Critically,
  `paneRecords.ts:isPaneContentRef`'s runtime body is unchanged: persisted
  pane refs are narrowed type-level only, no UUID validation was added, so no
  stored ref can be dropped on rehydrate and no persistence behaviour changed.
- **opus m1 — real** (`RepoGroupKey` now the `__brand` string-literal idiom).
- **opus m2 — real** (`packages/contract/fixtures/space-parity.json`, outside
  `src`, snake_case fields, `owner_id` on every record).
- **opus m4 — real** (new tests: success-record consistency, single-fault
  internal consistency, exact shipped vocabulary, shipped-vs-proposed status,
  precedence pinning; contract suite is now 16 tests, run first-hand, green).
- **opus m5 — real** (`transport.ts:brandedIdOrNull`, one generic helper).
- **opus m6 — real** (`durableCanvasIdOrNull` uses the predicate's narrowing,
  the redundant `asCanvasId` call is gone).

### The dispute (opus m3): builder's refutation accepted

Adjudicated third-party with evidence:
`packages/contract/src/packagePurity.test.ts:"declares no runtime
dependencies"` asserts the manifest has **no `dependencies` property at all**,
so importing `isRecord` from `@tm/common` (a workspace runtime dependency)
would fail a shipped test and break the contract package's core guarantee.
The JSON fixture import is a genuine untrusted reader boundary needing an
exact decoder, and the builder documented the duplication decision in place
("Deliberately local. Contract packages have zero runtime dependencies…").
The four-line local `isRecord` is the correct cost of the zero-dep guarantee.
One boundary on the acceptance: if a third copy ever appears inside the
contract package, the answer is one contract-internal shared helper file,
never `@tm/common`.

### The owner ruling: applied as a principle, verified against Python itself

All ten taxonomy codes grep-verified as shipped vocabulary in non-test Python
sources: `invalid_space_id`/`invalid_worktree_id`/`invalid_canvas_id` and
`canvas_affinity_required` (`capture_rpc_routes.py`), `worktree_not_found`
(404), `space_mismatch` (`launch_resolution.py`, `space_routes.py`),
`worktree_unavailable` (409), `canvas_not_found` (`space/service.py`),
`canvas_worktree_mismatch`, and `conflict`
(`cli/space_bootstrap.py`'s N:1 code). The three-way worktree taxonomy matches
`resolve_launch_worktree`/`_resolve_launch_worktree` behaviour exactly:
another Space's worktree → `space_mismatch`, owner-scoped absence →
`worktree_not_found`, inactive → `worktree_unavailable`. The one genuinely
novel outcome (no-seed unmatched workdir, where shipped CLI behaviour seeds)
is the one fixture marked `proposed` rather than presented as current fact.
No invented code remains; the SCREAMING_CASE taxonomy is fully deleted.

### Scope, size, and regressions

- **Scope held.** No `packages/space`, no ranking logic, no persistence shape
  or version change (`canvasStore.persistence.ts` delta is the `getCanvasId`
  type only), no seed path, no Python file touched, directory listing clean.
- **Size accounted.** ~986 of the churn is the corpus move-and-rewrite
  (−480 old JSON, +506 new with two added fixtures and per-record
  `owner_id`/`expectation_status`); fixtures.ts decoder rewrite (~164) and
  space.test.ts growth (~110) cover the contract rest; the ~40-file canvas
  tail is test-fixture branding plus prettier reflows in files the type
  tightening touched (`spawn.ts`, `capturedRunStore.ts` object-literal
  rewraps). Nothing found unrelated to a finding.
- **Migration claim now accurate.** The corrected claim lists exactly the
  carriers verified branded above and claims nothing broader. `RunView`
  branding is cast-at-transport rather than per-field minting, consistent
  with the file's existing decode style.
- **Nothing newly broken found.** Run first-hand at `ceec0a7b`: contract suite
  16/16, full shell frontend suite 171 files / 1309 tests green, and
  contract + core + canvas typechecks clean.

### Trust delta

Fix-round discipline was excellent: fourteen findings addressed without one
cosmetic disposition, the disputed item argued from a shipped structural test
rather than taste, the owner's ruling generalized into a taxonomy principle
(vocabulary sourced from Python, novelty explicitly quarantined as
`proposed`) rather than a one-line patch, and the highest-risk temptation
(runtime-validating persisted pane refs) was correctly declined.
