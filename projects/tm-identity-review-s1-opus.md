# S1 review — Space identity contract (Opus pane)

Commit `5c77edf0 feat(contract): add Space identity contract`, parent `963fd8f8`,
branch `ml/s6-identity`. 51 files, +1332/-345. Independent review against
`~/.mdx/projects/tm-identity-build-plan.md` §5 S1. Citations are file:symbol.

**Verdict: 0 blockers, 4 majors, 8 minors. Scope held.**

## Tree state

`git status` at verdict time is **not** the pristine baseline the brief describes.
It shows the expected pre-existing ` M LESSONS.md` plus one untracked file that
appeared mid-review:

```
 M LESSONS.md
?? www/packages/canvas/src/workbench/ZZTemp.probe.test.tsx   (mtime 19:49, review began 19:43)
```

**Attribution, corrected after the fact: this was mine.** A `/code-review`
subagent had been forked in this pane by a local slash command before the brief
arrived, running a whole-branch review (`97a80f56..HEAD`) independently of it. It
wrote the file as a throwaway probe of the meta-vs-worktree-switch precedence,
using `SessionCanvasRoute.testSupport` fixtures, and deleted it when it finished.
So my session did write into the shared tree despite the read-only mandate,
transiently, at a path unrelated to this commit. I wrote nothing myself but this
findings file.

The file was untracked and not part of the commit under review, so it does not
affect the verdict, and final `git status` at verdict time is ` M LESSONS.md`
and nothing else — the pristine baseline the brief describes. Recorded because a
read-only reviewer that writes to a shared tree is worth knowing about even when
it cleans up after itself.

That subagent's findings concern the branch baseline (`963fd8f8` and earlier),
not `5c77edf0`, and are deliberately **not** folded into this review: they are
out of scope for S1 and merging them would collapse the independence the
two-reviewer split exists to provide. One point from it is worth the plan's
attention on its own terms — it empirically reproduced the
`SessionCanvasRoute.tsx` meta-wins demotion (switch to worktree B, store
`canvasId` lands at `null`, not `CB`) against the current baseline, which is
direct evidence that the defect §1 describes is live and that §7's "do not
re-tune this line, it is deleted in S6" is aimed at the right place.

## Verification I ran myself

Targeted, not the full recipe: two other agents share this working tree, so I
did not run `just check && just test` and cannot corroborate the builder's
"3416 Python passed, all JS suites passed".

| Command | Result |
|---|---|
| `pnpm --filter @tm/contract typecheck` | exit 0 |
| `pnpm --filter @tm/core typecheck` | exit 0 |
| `pnpm --filter @tm/canvas typecheck` | exit 0 (`tsc -b`, whole browser graph) |
| `pnpm --filter @tm/contract test` | exit 0, 4 files / 12 tests |
| `grep -rn "type SpaceId\|type WorktreeId\|type CanvasId" www/ packages/` | exactly 3 lines, all `contract/src/space/wire.ts` |
| `grep` for space types imported from `@tm/core` across `www/packages` | zero hits |
| `grep` for `as SpaceId` / `as WorktreeId` / `as CanvasId` | only the three constructor bodies |

The canvas typecheck is the load-bearing one for a type-only slice: it compiles
the whole browser graph and is what actually proves "every consumer migrated".

## Q1 — Is this slice 1?

**Yes. Scope held; nothing from S2+ appears.** No `packages/space`, no
`SpaceContextService`, no `@tm/space-client`, no resolver, no reducer, no
`ActingContext` phase union, no locator, no `sessionStorage` key, no
`storageKeys.ts` change, no persistence-version change, no seeding path, and no
Python file in the commit at all (all 51 files are under `packages/contract/`
or `www/packages/`).

The +1332 accounts for itself: 934 of it is the new contract surface
(`parity-fixtures.json` 480, `fixtures.ts` 194, `wire.ts` 114, `space.test.ts`
109, `index.ts` 27, `testing.ts` 10). The remaining ~400 is import churn and
fixture rebranding across 44 consumer files, most of it 1-3 lines each. The
only file that grew for a non-mechanical reason is `space.test.ts`, which
absorbed the deleted `spaceTransport.contract.test.ts` assertions rather than
dropping them.

One caveat that is not scope creep but reads like it: the parity corpus is
placed in S1 by the plan itself, and authoring it necessarily decided S2's
verification semantics (see M1, M2). Those decisions arrived without an S2
reviewer, and by the time S2 lands the fixtures will read as the spec.

## Q3 — Did any behaviour change?

**No.** I read every non-test hunk. Five runtime-touching edits exist and all
five are identity functions or exact rewrites:

- `core/transport.ts:fetchMeta` — `raw.space_id ?? null` became an explicit
  `undefined`/`null` test then `asSpaceId(...)`. `??` already covers both, and
  the constructors are casts, so behaviour is identical including the `""` case.
- `route.ts:durableCanvasIdOrNull` and the new `route.ts:brandedValueOrNull` —
  same `valueOrNull` trim-and-empty semantics, plus an identity cast.
- `commandRows.ts:buildScopeRows` (agents arm) — `asWorktreeId(param)`, identity.
- `capturedRunAdoption.ts:attachableRun` — `asWorktreeId(value.worktreeId)`
  after the existing `isSafeManagedId` guard, identity.

Tests were migrated, not weakened. Every deleted assertion is either re-homed
(`RepoGroupKey` nominality moved verbatim from `spaceTransport.contract.test.ts`
into `space.test.ts`) or updated in place — including
`transport.test.ts`'s `expectTypeOf<Parameters<typeof fetchWorktrees>>()`, which
was tightened to `[spaceId: SpaceId]` rather than deleted. That is the exact spot
where a rushed migration deletes the type assertion, so it is worth crediting.

## Q4 — Is the old surface gone?

**Yes.** Both declaration sites are deleted
(`core/spaceTransport.ts` lost its five type aliases and all seven DTOs;
`canvas/model/paneRecords.ts` lost `export type CanvasId = string`). No
compatibility re-export: `core/src/index.ts` still has
`export * from "./spaceTransport"`, but the module no longer declares the types,
so `@tm/core` exports none of them — confirmed by grep across `www/packages`,
which returns zero space-type imports from `@tm/core`. Canvas imports
`@tm/contract/space` directly. No parallel path, no alias, no deprecation shim.

`packages/contract/package.json` gains `./space` and `./space/testing`;
`importGraphBoundary.test.ts` gains both to its export-map resolver coverage
list, matching the `@tm/contract/activity` precedent exactly.
`packagePurity.test.ts` needs no change (it asserts the absence of a
`dependencies` key, which still holds).

---

## Majors

### M1 — The corpus demands a fact the control plane cannot read from stored state

`parity-fixtures.json:"worktree presence unknown"` sets `missing: null` and
expects `WORKTREE_INACTIVE`. `missing` is not stored state. Evidence:

- `space/models.py:StoredWorktree` has no `missing` field; it appears only on
  `ProjectedWorktree`.
- `space/projection.py:project_worktree` sets
  `missing=observed.missing if observed is not None else None` — null whenever
  the row has no live git observation.
- `space/detection.py:_missing_state` also returns `None` on `OSError`.
- The only `missing` column in the schema belongs to the **legacy**
  `space_worktree` table (`migrations/0030_space_crud_reset.py:_create_legacy_space_worktree`).
  The live `worktree` table has none.

Plan S2 specifies "read-only Postgres repository" verification in "one
repeatable-read, read-only transaction". A DB-only read sees `missing = null`
for **every** worktree, so a literal implementation of this corpus fails every
verification with `WORKTREE_INACTIVE` — including the reload path S5 exists to
fix. The escape is to join a live git detection pass into the verification
transaction, which is filesystem IO inside the boot-critical path and undercuts
the one-snapshot framing.

This is decidable now and should not be discovered in S2. Either treat unknown
presence as non-fatal (`lifecycleState` alone gates activity), or introduce a
distinct code for it, or commit the plan to detection-joined verification and
say so in §4. Related: the plan's §3 claim "Python already complies" treats the
`WorktreeSummary` DTO as if all its fields were queryable; `missing`,
`repoGroupKey`, `branchName`, `headOid` and `isPrimary` are all observation-only.

### M2 — The corpus does not pin failure-code precedence, so both planes can pass and still disagree

All 15 fixtures are single-fault. Nothing pins what happens when two conditions
hold at once: malformed id *and* partial tuple; owner mismatch *and* canvas
mismatch; inactive worktree *and* absent canvas. Two implementations can each
satisfy the whole corpus and still return different codes for the same input,
which is precisely the divergence a parity corpus exists to prevent — and the
S2 Python conformance test would report green.

`ACTING_CONTEXT_FAILURE_CODES` is declared in a plausible evaluation order, but
nothing states that the array order *is* the precedence. Either say so on the
constant (and add fixtures that would fail if a plane reordered), or add
multi-fault fixtures. The cheap version is three fixtures.

### M3 — `MALFORMED_ID` is declared by the contract, but the id format rule is owned everywhere except the contract

`asSpaceId("not-a-uuid")` succeeds. The corpus nonetheless requires
`MALFORMED_ID`, so the rule that decides it lives outside the type that names
it. Today that rule exists in at least three places:

- `canvas/src/route.ts:isDurableCanvasId` (`UUID_PATTERN`), browser-side, canvas-owned;
- `api/v1/ids.py:parse_uuid_id` with `space/models.py` `_UuidId.parse`;
- implicitly, whatever S2 writes next.

That is the "derived independently in N places with an implicit rule"
pattern from §1, reproduced inside the slice whose stated purpose is single
ownership. The contract should export the predicate — `isSpaceId` /
`parseSpaceId`, or at minimum a shared `ACTING_CONTEXT_ID_PATTERN` — so the URL
codec, the verification service and the Python side consume one rule.

Second-order, and the sharper half of "is the branding real":
`route.ts:isDurableCanvasId` is typed `value is CanvasId`, which makes it a
**second, implicit branding site** outside the three declared constructors,
reachable from any `string | null` anywhere in canvas. It is a *checked* brand,
so it is better than the constructors, not worse — but the contract does not
know it exists, and S3 moves it into `@tm/space-client` rather than into the
contract, so the split persists.

For the record on the constructors themselves: unchecked casts match the shipped
`packages/activity/src/ids.ts:asRunId` pattern and `docs/ARCHITECTURE.md`, so
they are the house form and not a finding on their own. The brands do their real
job — `SpaceId`, `WorktreeId` and `CanvasId` are mutually unassignable, so the
argument-order class of bug is now a compile error, and
`space.test.ts` pins `string` not being assignable to any of the three.

### M4 — The brand decays back to `string` at the launch and cache-key hops, and the migration claim overstates coverage

The builder's claim "Core transport inputs and DTOs" migrated does not hold.
Still plain `string` after this commit:

- `core/transport.ts:RunView.spaceId` / `.worktreeId` — a **response DTO read at
  a reader boundary**, the sibling of the path that `capturedRunAdoption.ts:attachableRun`
  *does* brand. Same identity, two read paths, one branded and one not.
- `core/transport.ts:RunFilters`, `CreateCapturedRunOptions.spaceId` / `.canvasId`,
  `createCapturedRun(worktreeId?)`, `createCapturedRunView(worktreeId?)` — the
  outbound launch payload.
- `canvas/model/spawn.ts`, `capturedRunStore.ts` and
  `infrastructure/runtime/useCapturedRunBinding.ts` identity triples.
- `infrastructure/persistence/canvasCacheStorage.ts`: `canvasCacheKey(canvasId: string)`,
  `createCanvasCacheStorage(getCanvasId: () => string | null)`, and
  `durableCanvasId(): string | null` — which **discards the `value is CanvasId`
  narrowing `isDurableCanvasId` already provides**, so a branded id goes in and a
  bare string comes out, at the surface that keys persisted canvas state.

`canvasStoreLifecycle.ts:getActiveCanvasId` now returns `CanvasId | null` and
feeds `createCanvasCacheStorage`'s `string | null` parameter silently, so the
gate cannot see the decay. Net effect: type protection covers the
launcher, route and store-state consumers, and stops immediately before the
launch and persistence-keying seams — the hops where a wrong id actually causes
the reported bug.

The plan defers *ownership* of these to S4/S5, so this is not scope creep. But
`RunView` and `canvasCacheStorage` are pure type widenings with zero behaviour
change and belong in S1 by the same argument that put `Meta` in it. At minimum
the claim should be corrected to "Core transport meta reader and Space DTOs".

---

## Minors

1. **Two brand idioms in one file.** `wire.ts` declares the three new ids with
   the `{ readonly __brand: "SpaceId" }` string-literal property (copied from
   `activity/ids.ts`) and, four lines later, `RepoGroupKey` with a
   `declare const ... unique symbol` (moved verbatim from `spaceTransport.ts`).
   The symbol form is strictly stronger: it cannot be spelled outside the module.
   Pick one. If `__brand` is the house style, the comment should say so, because
   the file currently reads as an accident.

2. **The corpus diverges from the shipped cross-plane parity precedent.** One
   already exists and neither the plan nor the build cites it:
   `packages/activity/fixtures/conversation-parity.json`, consumed by
   `packages/activity/src/conversationParity.test.ts` and
   `api/.../session/test_conversation_parity.py`. It lives in a `fixtures/` dir
   outside `src/`, is loaded by path from Python, and uses **snake_case** keys
   (`session_id`, `prefix_visible_turns`). The new corpus lives inside `src/`,
   uses camelCase TS wire keys, and needs `resolveJsonModule` in the contract
   tsconfig. Since S2 verifies against stored rows and
   `space/models.py:StoredWorktree` is snake_case (`lifecycle_state`,
   `root_canvas_id`) with camelCase aliases only on the wire record models, the
   corpus is TS-wire-shaped rather than genuinely neutral. Answering Q5
   directly: it is *portable* (plain JSON, POSIX paths, no TS-only constructs)
   but it is not *neutral* in vocabulary, and it silently picks the browser's
   naming as the cross-plane one.

3. **130 lines of hand-rolled runtime validation over a static in-repo asset.**
   `fixtures.ts` re-implements `isRecord` (a third copy;
   `www/packages/core/src/isRecord.ts` is the existing one) plus `hasExactKeys`,
   six type guards and `parseParityFixtures`. `packages/AGENTS.md` names
   `@tm/common` the single home for `unknown`-to-typed coercions and calls
   cross-package duplication a defect — but the contract's zero-dep purity
   forbids importing it, so the duplication is *forced by the JSON-first choice*,
   not by carelessness. Authoring the corpus as TS
   (`as const satisfies readonly ActingContextParityFixture[]`) and emitting JSON
   for Python would give compile-time enforcement with no validator, no
   `resolveJsonModule`, and no third `isRecord`. Worth deciding before S2 doubles
   down on the current shape.

4. **The validator checks shape, not internal consistency.** Nothing asserts a
   fixture's `records` actually produce its `expected` — the `canvas not found`
   case could gain a matching canvas and stay green until S2 exists. A few
   cross-checks in `space.test.ts` (candidate ids resolve or provably do not,
   per the expected code) would keep the corpus honest in the window before it
   has an implementation.

5. **`fetchMeta` branding is more surface than it needs.** Three fields each
   spelled `raw.x === undefined || raw.x === null ? null : asX(raw.x)`, where
   `raw.x == null ? null : asX(raw.x)` is the same check in one comparison, and
   the previous `??` form was one token. Six lines became fourteen for no
   semantic gain.

6. **`route.ts:durableCanvasIdOrNull` calls `asCanvasId` on an already-narrowed
   value.** `isDurableCanvasId(candidate)` returns `value is CanvasId`, so the
   cast is a no-op that obscures which construct is doing the branding.

7. **The launcher scope `param` is an unbranded string channel ids round-trip
   through.** `commandRows.ts:buildScopeRows` re-brands it with
   `asWorktreeId(param)` on the agents arm, while
   `workdirRows.ts:buildWorktreeRows` keeps `spaceId: string | undefined` and
   compares it against `space.spaceId` — so any string still selects a Space
   there, in a file whose sibling parameter was branded in the same hunk. Either
   type the scope param or add one comment naming it the deliberate erasure
   point; right now it is neither.

8. **`paneRecords.ts` is internally inconsistent after the migration.** The same
   commit brands `ViewerCanvasContext.spaceId` to `SpaceId | null` and leaves
   `worktreeId?: string` on three pane-ref and spawn-descriptor shapes. If the
   persisted-record shapes are deliberately left unbranded because a persisted
   value is a claim rather than a verified id, that is a good reason and should
   be a comment — plan §7 warns specifically about mirrored identity fields with
   no stated rule.

Corpus coverage gaps worth closing when S2 lands, beyond M2: no
`resolve_workdir_context` case against an inactive or missing worktree; no
workdir case crossing an owner boundary; no exact-path (non-subdir) match; no
trailing-slash or relative-path normalization case; and no version field on the
corpus, so a shape change cannot be detected from the Python side. The two
things it does pin well are worth noting — the `unique containing workdir` case
deliberately includes a second canvas anchored to the same worktree and expects
`rootCanvasId`, and `space.test.ts` asserts the fixture set covers every member
of `ACTING_CONTEXT_FAILURE_CODES`, so the corpus cannot silently lose a code.

---

## Q6 — What this slice exposes about the plan

1. **§6's capability-owner list misses the parity-corpus capability that already
   ships.** `packages/activity/fixtures/conversation-parity.json` +
   `test_conversation_parity.py` is the existing cross-plane pattern, and the
   plan's "None found" list does not mention it. The build consequently invented
   a second convention (minor 2). Both scouts missed it too.

2. **The plan names `MALFORMED_ID` but assigns the id-format rule no owner.**
   §3's reader-boundary list assumes constructors are unchecked casts, which is
   consistent with `activity/ids.ts` but leaves a declared failure code with no
   home (M3). Add the predicate to the contract in S1/S2, or drop the code.

3. **§3's "Python already complies" over-reads the DTO.** `missing` is a live
   observation, not stored state, so S2's read-only repository cannot supply it
   (M1). §4's staleness sentence — "owner differs, row deleted, worktree
   inactive or missing" — needs to say what happens when presence is *unknown*,
   which is the common case for a row nobody has probed.

4. **Minor, forward-looking:** §5 S3 moves the URL codec (and with it
   `isDurableCanvasId`) into `@tm/space-client`. If the format rule becomes
   contract-owned per M3, that move should leave the predicate behind in the
   contract rather than carrying it into a browser package.

## Builder trust

High for mechanical and structural work, with one soft spot: the migration is
faithful and complete where it claims to be (both declaration sites gone, no
compat re-export, tests tightened rather than deleted — including the
`fetchWorktrees` parameter type assertion that a rushed pass would have
dropped), scope held exactly with zero S2 bleed and every inserted line
accounted for, and no behaviour drift in any of the five runtime-touching hunks;
the weak spots are domain judgment exercised unsupervised in the parity corpus
(an unsatisfiable `missing` rule and unpinned failure precedence, neither
flagged as a decision) and one overstated claim ("Core transport inputs and
DTOs" migrated, when `RunView`, `RunFilters` and the launch options were not) —
so delegate slices of this shape and size freely, but hand over cross-plane
semantic decisions pre-made rather than expecting them to surface as questions.

---

# Delta re-review (ceec0a7b)

`git diff 5c77edf0..ceec0a7b`, 38 files, +1139/-787. Parent confirmed
`5c77edf0`. `git status` at verdict time: ` M LESSONS.md` and nothing else.
Deltas only; 5c77edf0 itself not re-reviewed.

**Verdict: 0 new blockers, 1 new major, 4 new minors. Scope still held.
All 13 claimed fixes landed; 12 are real, 1 is partly cosmetic. Dispute m3:
accepted, the builder is right.**

Gates I ran: `@tm/contract` typecheck 0, `@tm/core` typecheck 0, `@tm/canvas`
typecheck 0 (`tsc -b`, whole browser graph), `@tm/contract` test 0 (16 tests, up
from 12). Not the full `just check && just test` — shared tree.

## The owner ruling: applied as a principle, not a patch

Verified every code in `ACTING_CONTEXT_FAILURE_CODES` against Python source, not
against the builder's description. All ten are shipped codes:

| Contract code | Shipped at |
|---|---|
| `invalid_space_id` / `invalid_worktree_id` / `invalid_canvas_id` | `capture_rpc_routes.py:PrepareCaptureRequest.to_domain` via `ids.py:parse_uuid_id` |
| `canvas_affinity_required` | `capture_rpc_routes.py:_resolved_domain_request` |
| `worktree_not_found` | `launch_resolution.py:_resolve_launch_worktree` |
| `space_mismatch` | `service.py:SpaceCrudService.resolve_launch_worktree` |
| `worktree_unavailable` | `launch_resolution.py:_resolve_launch_worktree` |
| `canvas_not_found` | `service.py:SpaceCrudService.get_canvas` |
| `canvas_worktree_mismatch` | `launch_resolution.py:resolve_run_canvas` |
| `conflict` | `space_bootstrap.py:bootstrap_cli_space`, `worktree_mutations.py` |

The invented taxonomy is entirely gone — `PARTIAL_CONTEXT`, `MALFORMED_ID`,
`SPACE_NOT_FOUND`, `WORKTREE_INACTIVE`, `OWNER_MISMATCH`, `AMBIGUOUS_PATH` all
retired. **No remaining invented code.**

The three-way taxonomy checks out against source:

- Foreign-Space Worktree → `space_mismatch`: `resolve_launch_worktree` finds the
  row, then `stored.space_id != space_id` raises it. Correct, and it reverses
  5c77edf0's mapping to `WORKTREE_NOT_FOUND`, which contradicted Python.
- Owner-scoped absence → `worktree_not_found`: `_store.get_worktree(worktree_id,
  owner=owner)` is owner-scoped, returns `None`, and `_resolve_launch_worktree`
  raises 404. The `owner scoped worktree not found` fixture models exactly this.
- Inactive/unavailable → `worktree_unavailable`: both the lifecycle branch and
  the `missing is not False` branch raise it.

The strongest evidence that shipped *behaviour* was followed rather than the
shipped error dictionary: `space_not_found` is a real Python code
(`space_routes.py`, `service.py`, `authz.py`) and is deliberately **absent** from
the contract. That is right — in the resolution order the Worktree resolves
first, so a nonexistent Space yields `space_mismatch` (worktree exists elsewhere)
or `worktree_not_found` (it does not), and `space_not_found` is unreachable on
this path. Omitting it is a judgment call in the right direction.

**Precedence order verified against source**, not asserted:
parse (`space`→`worktree`→`canvas`, the field order in `to_domain`) →
`canvas_affinity_required` (raised in `_resolved_domain_request` *before*
`resolve_run_canvas`) → `worktree_not_found` → `space_mismatch` (inside
`resolve_launch_worktree`: absence is tested before Space membership) →
`worktree_unavailable` → `canvas_not_found` → `canvas_worktree_mismatch`. The
contract's array order matches, and the comment on it now says the order *is*
the precedence. Three multi-fault fixtures pin it.

## Dispositions

Twelve of thirteen are real. Spot-checks that mattered:

- **fable m1 (`expectation_status`)** — real and well-judged. I verified the
  labels against `space_bootstrap.py:bootstrap_cli_space`: `ambiguous workdir` →
  `conflict` is genuinely shipped (`len(matches) > 1`); `unique containing
  workdir` → receipt with the *root* canvas is genuinely shipped (match →
  `resolve_launch_worktree` → `get_canvas(resolved.root_canvas_id)`); and
  `unmatched workdir` is correctly the only `proposed` one, because shipped
  bootstrap **seeds** on absence (`create_space` + `create_workdir`) rather than
  failing. Labelling the no-seed rule as proposed instead of dressing it as
  current fact is the honest call.
- **fable m2 / opus m7 (`LauncherScopeParam`)** — real. The string channel is
  gone end to end: `NavFrame.param`, `RowAction.enter`, `descend`, `pushFrame`,
  `buildScopeRows` all carry the tagged union. I checked both producers
  (`workdirRows.ts:worktreeRowActions` → `{kind:"worktree"}`,
  `spaceManagementRows` → `{kind:"space"}`) and the single consumer; no param is
  silently dropped and no behaviour changes.
- **opus M3** — real and complete. `route.ts` lost `UUID_PATTERN` and
  `isDurableCanvasId` entirely; the contract owns `isSpaceId`/`isWorktreeId`/
  `isCanvasId`; repo-wide grep for the old symbol returns nothing. The second
  branding site is closed.
- **opus M4** — real and complete. Every identity parameter I listed is branded.
  The only unbranded ids left in the browser are `workspaceId`, a different
  aggregate owned by `@tm/activity:asWorkspaceId`, correctly out of scope per the
  plan's "brand aggregate identity keys only".
- **opus m4** — the best fix of the round. `space.test.ts` now asserts receipts
  match owned records, single-fault fixtures actually carry their fault, the
  absent canvas is actually absent, and `containingWorktrees` counts match (0 for
  unmatched, 2 for ambiguous). The corpus can no longer drift from its own
  expectations.
- **opus M1** — real, but resolves by deletion; see the unresolved item below.
- **opus m8 — partly cosmetic**; see new minor 1.

## The corrected migration claim

"Core Space transport DTOs, Meta reader, managed run request/response/filter
carriers, captured run composition, pane identity, and Canvas cache identity are
branded; no broader transport migration is claimed." **Accurate.** I re-ran the
residual-unbranded grep and every hit is `workspaceId`. The claim now names
exactly what it covers and disclaims the rest.

## Accounting for +1139/-787

| Slice of the delta | Lines | Share |
|---|---|---|
| Fixture corpus move (`src/space/parity-fixtures.json` → `fixtures/space-parity.json`) | +506 / -480 | 51% |
| Contract src (`wire.ts` predicates + ordered codes, `fixtures.ts` snake_case, `space.test.ts` consistency assertions) | +263 / -132 | 21% |
| Browser test/fixture rebranding | +267 / -105 | 19% |
| Browser production source | +103 / -70 | 9% |

Half the delta is the file move that my own m2 asked for, which registers as a
delete-plus-add. Only 173 changed lines are production source. Nothing in the
delta is unaccounted for, and the size is not a smell.

## Scope

Still held. No `packages/space`, no service, no resolver, no browser ranking
package, no schema or migration, no seed path. `CANVAS_STORE_STORAGE_VERSION`
is still `1` and `partialize`/`migrate` are untouched — the persistence-adjacent
edits (`canvasCacheStorage.ts`, `canvasStore.persistence.ts`) changed parameter
types only, so the stored JSON shape is byte-identical. No data-loss surface.

## Dispute (opus m3): accepted

The builder is right, and I withdraw the finding.

- The purity constraint is real, not rhetorical: `packagePurity.test.ts` asserts
  the manifest has no `dependencies` key at all, so importing `@tm/common` would
  fail the gate. A local three-line `isRecord` is the only legal option, and the
  file now carries a comment saying exactly why.
- The decoder does a job `satisfies` cannot: TypeScript widens imported JSON
  literals, so `lifecycle_state` arrives as `string` and `failure_code` as
  `string`. Recovering those unions needs a runtime narrowing pass. My proposed
  alternative (author in TS, emit JSON for Python) trades that for a generated
  artifact plus a staleness gate — strictly more machinery for the same
  guarantee.

The one piece of counter-evidence I found, and do not press: the shipped
precedent this corpus was moved to match, `packages/activity/src/conversationParity.test.ts`,
imports its parity JSON with **no decoder at all**. So precedent does not require
one. The material difference is that Activity consumes its corpus inside a test
file, where malformed data is just a test failure, while this one is a package
subpath whose module-level `parseParityFixtures` throws at import. That
difference justifies the asymmetry.

Residual worth knowing, not worth changing now: `hasExactKeys` on every nested
record makes the corpus rigid. When the Python conformance run wants a field of
its own, adding it to the JSON breaks the TS decoder. That is a deliberate
strictness trade, and S2 will be the one to pay or renegotiate it.

## Unresolved from the first round

**opus M1 — the assertion is fixed, the design question is now invisible.** The
corpus no longer claims `missing: null → inactive`, and `fixtures.ts` documents
that live projection fields "cannot be read by the Slice 2 Postgres repository"
with "Python launch readiness remains the authority for live checkout presence."
That is honest scoping. But Python's shipped rule has two branches —
`lifecycle_state is not ACTIVE` **and** `missing is not False` — and the corpus
now pins only the first. A Python conformance test built on it will pass an S2
verifier that never checks checkout presence, after which a browser can verify a
context whose checkout is gone and fail at launch instead. The question I raised
is still open and is now harder to see: **does S2 verification probe the
filesystem, or is verification deliberately narrower than launch readiness?**
Worth an explicit line in the plan before S2 starts, either way.

## New findings

### Major

**N1 — the build plan is now stale on the exact point the owner ruled.**
`~/.mdx/projects/tm-identity-build-plan.md` §3 still lists the retired invented
taxonomy (`PARTIAL_CONTEXT, MALFORMED_ID, SPACE_NOT_FOUND, WORKTREE_NOT_FOUND,
WORKTREE_INACTIVE, CANVAS_NOT_FOUND, CANVAS_WORKTREE_MISMATCH, OWNER_MISMATCH,
AMBIGUOUS_PATH`), and §5 S2 still describes "the fixture matrix covering every
failure code" against that list. The plan is what S2's implementer reads, not
this commit, so as written it instructs them to re-mint the codes the owner just
ruled out. Update §3's taxonomy and §5's S2 gate to the shipped vocabulary, and
add the `expectation_status` concept, in one pass rather than paragraph by
paragraph.

### Minors

1. **`isPaneContentRef`'s new docstring overstates what the guard does.** It now
   reads "Persistence reader boundary for pane refs. Successful identity fields
   become branded here" — but the guard checks `typeof value.worktreeId ===
   "string"` and returns `value is PaneContentRef`, so it mints `WorktreeId` from
   any persisted string, unvalidated, at the moment the contract finally ships
   `isWorktreeId`. This is the same shape as the `isDurableCanvasId` problem just
   fixed in `route.ts`. The types are genuinely branded, so the fix is not
   nothing, but the comment claims a property the code does not enforce. Note the
   fix is not free: switching to `isWorktreeId` would reject every non-UUID test
   fixture (`testUtils.ts:makeCapturedRunRef` uses `asWorktreeId("wt-test")`), so
   it is validate-and-repair-fixtures, or soften the comment. Pick one; do not
   leave the claim standing.

2. **`ACTING_CONTEXT_FAILURE_CODES` is a curated subset with no statement that it
   is one.** Python's Space vocabulary also has `space_not_found`, `forbidden`,
   `invalid_request`, `canvas_cycle`, `canvas_root_mismatch`,
   `worktree_provenance_unsupported` and more. Omitting them is correct — they are
   unreachable on this path — but nothing says so, and a future contributor
   "completing" the list would silently reintroduce unreachable codes. Relatedly,
   `conflict` sits in an array whose comment calls the order precedence, yet it is
   reachable only from `resolve_workdir_context`, never from
   `verify_acting_context`. One sentence naming the list as the acting-context
   resolution subset, ordered by the `capture_rpc_routes` → `launch_resolution`
   sequence, closes both.

3. **One ordering pair is still unpinned.** The three multi-fault fixtures cover
   parse-before-affinity, worktree-before-canvas twice. Not covered:
   `space_mismatch` versus `canvas_not_found`, the one pair whose Python
   reachability is genuinely subtle — the Worktree-level `space_mismatch` fires
   before `get_canvas` is called, while the Canvas-level one
   (`_require_owned_worktree` inside `get_canvas`) fires only after
   `canvas_not_found` has been cleared. A reimplementation that checks Space
   membership once, late, would satisfy the corpus and diverge from Python. One
   fixture closes it.

4. **Formatter reflow unrelated to any finding.** Roughly 30-40 lines across
   `spawn.ts:normalizeRef`/`labelFor`, `capturedRunStore.ts:setMinimized`,
   `testUtils.tsx:makeSessionEvent`, `workdirRows.ts:createWorkdirRow` and
   `canvasDrop.test.ts` had single-line object literals split across lines with no
   semantic change. I verified this does not break the gate — `biome format` on
   the touched files reports no fixes, so both forms are acceptable — but it is
   churn in an already-large round, and it is the kind of noise that hides a real
   edit from a diff reader.

## Builder trust, updated

Raised. This round did the harder thing twice: it checked the failure taxonomy
against Python's actual resolution order rather than its error dictionary
(including the judgment call to *exclude* a real code, `space_not_found`, because
it is unreachable), and it introduced `expectation_status` to mark where the
corpus states intent rather than shipped fact — a distinction I did not ask for
and which is better than what I proposed. It also pushed back correctly on m3
with an argument I can verify. The residue is the same shape as last round and
smaller: one comment that claims more than the code enforces, one design question
closed by deletion rather than decision, and a plan document left behind by its
own fix round.

---

# Closing check (2a23e5af)

`git diff ceec0a7b..2a23e5af`, 9 files, +76/-70. Parent confirmed `ceec0a7b`.
`git status`: ` M LESSONS.md` only. Bounded to my four delta findings.

**All four closed. Nothing unrelated rode along. Guard: accept the comment fix,
and I recommend *not* scheduling the widening.**

Gates I ran: `@tm/contract` test 0 (16 tests), `@tm/contract` typecheck 0,
`@tm/canvas` typecheck 0, and `biome format` on the reverted files (no fixes).

## 1. `isPaneContentRef` docstring — closed, and do not widen the guard

The docstring now reads "Structural reader guard for persisted pane refs. It
validates variants and required field shapes only; identifier formats and the
stored shape are unchanged." That is exactly what the code does: it switches on
`kind`, checks `typeof === "string"` / optional-string / boolean per variant, and
now explicitly disclaims identifier-format validation. The overstated "reader
boundary … identity fields become branded here" is gone. Claim and code agree.

**I accept the reasoning, and I want to go further than accepting it: the guard
should not gain UUID rejection later either.** The orchestrator offered to
schedule it; taking that option would be a mistake, for three reasons.

- It would be a rehydration-time behaviour change. Rejecting a ref drops it, so
  any persisted pane carrying a non-UUID `worktreeId` disappears from the user's
  canvas on reload. That is the persistence data-loss shape, not a hardening.
  Note `RunManager.ts`'s `"stub-worktree"` sentinel (plan §5 S7) is exactly the
  kind of value that can already sit in a persisted ref.
- Nothing downstream needs it. The brand is a compile-time claim and no client
  decision keys off the format. A bad `worktreeId` reaches
  `createCapturedRun` → `POST /v1/runs` → `ids.py:parse_uuid_id`, which fails
  closed with `invalid_worktree_id`. The server is the enforcement point and it
  already works. Contrast `canvasCacheKey`, which *does* validate, because there
  a bad id silently mis-keys persisted state — a real client-side consequence
  that `worktreeId` does not have.
- The cost is a repair of every non-UUID fixture in the canvas suite
  (`testUtils.ts:makeCapturedRunRef`, the `"wt-1"` refs across store, persistence
  and dnd tests), which buys nothing.

If it is ever wanted, it belongs in S6's rehydrate work behind the
persist-OLD-snapshot-then-rehydrate gate, and only on evidence of a concrete
failure. Closing it as a comment correction is the right call.

## 2. Failure-code subset — closed

The comment now names the list a "Curated acting-context resolution subset only",
ties the verify order to "Python precedence from capture_rpc_routes through
launch_resolution", and calls out `conflict` as "the resolve_workdir_context
terminal, outside that sequence". Both halves of the minor are covered: a future
contributor can no longer read the array as the full Space vocabulary, and the
one member that is not part of the verify precedence is identified as such.

## 3. `space_mismatch` before `canvas_not_found` — closed, and correctly

The corpus is now 18 fixtures with the two cases properly separated:

- `worktree belongs to another space` — worktree in Space `5555`, **canvas 3333
  present**. Pure single-fault `space_mismatch`.
- `space mismatch precedes missing canvas` (new) — worktree in Space `5555`,
  **canvases empty**. Multi-fault: `space_mismatch` wins over `canvas_not_found`.

Verified against Python rather than the description: `resolve_launch_worktree`
finds the row via the owner-scoped `get_worktree`, compares `stored.space_id`
against the requested `space_id`, and raises `space_mismatch` before
`resolve_run_canvas` ever calls `get_canvas` — so `canvas_not_found` is
unreachable for this input. The expectation matches shipped behaviour.

`space.test.ts` pins both sides so they cannot drift back together: the new
fixture asserts the worktree's Space differs from the candidate's **and**
`ownedCanvas(...)` is `undefined`; the original fixture now asserts
`ownedCanvas(...)` is `toBeDefined()`. That is the right way to keep a
single-fault and a multi-fault case from collapsing into each other.

## 4. Formatter churn — reverted cleanly

All five files are back to the single-line form. I checked this the strict way,
by diffing `5c77edf0..2a23e5af` on those files rather than reading the revert
hunks: what remains is **only** the semantic branded-id work —
`asWorktreeId` in `canvasDrop.test.ts` and `testUtils.tsx`, the
`LauncherScopeParam` tagged params and `SpaceId` in `workdirRows.ts`, the branded
`EnsureRunOptions` in `capturedRunStore.ts`, and `WorktreeId` on
`createCapturedRunRef`. Zero formatting residue, nothing semantic lost in the
revert. `biome format` reports no fixes on the reverted files, so the gate is
satisfied in this form too.

## Nothing rode along

The 9 files decompose exactly into the four findings: `space-parity.json` (+45,
one new fixture plus the records that give the original its Canvas),
`space.test.ts` (+11, the two assertion pairs), `wire.ts` (comment only, no
code), `paneRecords.ts` (docstring only, no code), and the five reverted files.
No new fixture beyond the one, no other fixture altered, no production logic
touched, no test weakened.

## Standing residue after S1

Not raised again as findings; carried forward so they are not lost:

- **The M1 design question** — does S2 verification probe checkout presence, or
  is verification deliberately narrower than launch readiness? The corpus pins
  only the lifecycle half of Python's two-branch `worktree_unavailable`. Needs a
  line in the plan before S2 starts.
- **Plan §3 and §5 are stale** on the retired invented taxonomy (delta major N1).
  The plan is what S2's implementer reads.

S1 is done as far as my findings go.
