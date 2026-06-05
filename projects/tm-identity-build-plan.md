# Space/Worktree/Canvas identity — canonical build plan

Authoritative build plan for the identity boundary. Sources: the two boundary
scout reports (`tm-identity-boundary-fable.md`, `tm-identity-boundary-gpt.md`,
both with cross-check and reconciled sections), the owner's binding plane
decision, and baseline `ml/s6-identity` at `963fd8f8`. Citations are
file:symbol, never line numbers.

**Revised 2026-07-26.** PR #328 (the S4 shadow aggregate and dual-write
bridge) was closed unmerged; S4–S6 are superseded by the seam-first T1–T4
sequence in §5. Revision sources: `tm-identity-s4-design-call.md` (its
Adjudication section is authoritative for the browser half) and the two seam
scout reports (`tm-identity-seam-scout-fable.md`,
`tm-identity-seam-scout-opus.md`), all at merged base `d1f499e5` (S1–S3
shipped).

## 1. Why a package, not a patch

"Which Space, worktree and canvas am I acting in" is derived independently in
four places (the URL, `/api/meta`, the persisted client store, the MCP launch
path), none authoritative, with the precedence between them implicit across
`route.ts:isUsableIdentity`, `SessionCanvasRoute.tsx`,
`canvasStoreLifecycle.ts:initializeCanvas`, and
`CanvasCommandDispatcher.ts`. Two consecutive fixes each moved the breakage to
an adjacent state because each edited one derivation site while the others kept
their own rule. The missing thing is an aggregate with one owner: a type that
cannot represent an incomplete or unverified triple, one verification rule both
clients consume, and one stated precedence over the browser's sources.

## 2. The decision, as a rule a newcomer can apply

- **Verification is control-plane.** Does this triple exist; is it complete;
  does this worktree belong to this Space; is this canvas anchored to that
  worktree. Lives in the new node context package `packages/space`
  (`@tm/space`) behind `@tm/contract/space`. The ⌘K palette and the MCP
  director consume the same rule. The gateway origin is never browser-visible
  in any mode (dev, desktop, packaged); the browser reaches this surface only
  through the Python-origin per-route mirror (T1).
- **Source ranking is browser-local.** Which source to believe (sticky explicit
  selection, URL, locator, meta) is a question only a browser can ask, because
  only a browser has those sources. The director has exactly one source: what
  it was told. A browser-side reducer over browser-only inputs is not a plane
  violation and implies no round-trip per worktree switch.
- **The test for a future piece:** if both clients need the rule, it is
  control-plane (`@tm/space` or `@tm/contract/space`); if the rule ranks or
  stores inputs only one client possesses, it lives in that client, and it must
  still obtain verification from the control plane rather than re-deriving it.

Packages: `@tm/space` at `packages/space` (canonical context shape, per
`packages/AGENTS.md`); `@tm/contract/space` + `@tm/contract/space/testing`
subpaths of the existing contract package (verified present:
`packages/contract/package.json` exports `./activity`, `./activity/testing`,
`./runtime`); browser client package `@tm/space-client` at
`www/packages/space-client`. Naming note, recorded: the scouts' names collided
at singular/plural (`@tm/space` vs `@tm/spaces`); the browser package takes the
`-client` suffix so the two cannot be confused. It may depend on `@tm/core`
(for `transport.ts:requestApiJson`), `@tm/contract`, `@tm/common`, `zustand`;
core never imports it back, so no cycle.

## 3. The aggregate

```ts
// @tm/contract/space
type SpaceId    = string & { readonly __brand: "SpaceId" };    // asSpaceId()
type WorktreeId = string & { readonly __brand: "WorktreeId" }; // asWorktreeId()
type CanvasId   = string & { readonly __brand: "CanvasId" };   // asCanvasId()
interface ActingContextReceipt {          // complete by construction
  readonly ownerId: string;
  readonly spaceId: SpaceId;
  readonly worktreeId: WorktreeId;
  readonly canvasId: CanvasId;
}
interface ActingContextCandidate {        // a claim; never launchable
  readonly spaceId: SpaceId | null;
  readonly worktreeId: WorktreeId | null;
  readonly canvasId: CanvasId | null;
}
// typed failures, in capture_rpc_routes → launch_resolution precedence:
// invalid_space_id, invalid_worktree_id, invalid_canvas_id,
// canvas_affinity_required, worktree_not_found, space_mismatch,
// worktree_unavailable, canvas_not_found, canvas_worktree_mismatch, conflict

// @tm/space-client src/domain/actingContext.ts
type ActingContext =
  | { phase: "unresolved" }
  | { phase: "claimed"; claim: ActingContextCandidate & { source: "url" | "locator" };
      generation: number }
  | { phase: "acting"; identity: ActingContextReceipt;
      via: "selection" | "verified-claim" | "workdir-context"; generation: number };
```

**Changed after slice 1.** The contract preserves Python's shipped failure
vocabulary rather than creating a second taxonomy.
`packages/contract/src/space/wire.ts:ACTING_CONTEXT_FAILURE_CODES` follows
`api/v1/capture_rpc_routes.py:PrepareCaptureRequest.to_domain` and
`_resolved_domain_request`, then
`api/v1/launch_resolution.py:resolve_run_canvas` and
`_resolve_launch_worktree`; `space_not_found` is excluded because that path
cannot emit it.

**Unrepresentability.** Receipt fields are non-null branded; nulls exist only in
candidates, and no launch, persistence-keying, or URL-write API accepts a
candidate. The only constructors of `acting` take server-owned data: a CMDK
selection row (server inventory), a candidate verified by
`@tm/space:SpaceContextService.verifyActingContext`, or the workdir-context
query result. No transition maps `acting` to `claimed`/`unresolved`; a verified
identity is replaced only by another verified identity or the explicit
Space-switch clear. `canvasIdVerified` and every open-coded triple-null check
are deleted; the phase is the state. Every resolution carries a monotonic
`generation`; an async verification result older than the current generation is
discarded, so a slow boot verify can never clobber a newer selection.

**Reader boundaries** (branded ids constructed once): the `@tm/space-client`
inventory adapter mapping `GET /v1/spaces` / `/v1/canvases`;
`core/transport.ts:fetchMeta` mapping `MetaResponse`; the URL codec parsing
`window.location.search` into a candidate; the locator adapter parsing the
stored receipt into a candidate; `@tm/space` repository row mapping; the
runtime router boundary (`runtimeRouter.ts:nonEmptyString`, slice 7). Python
already complies (`space/models.py` nominal `_UuidId` subclasses;
`api/v1/ids.py:parse_uuid_id`; `space_mcp.py:_crud_id`).

## 4. Precedence, written once

Owner: **`@tm/space-client` `src/domain/actingContext.ts:resolveActingContext`**,
a pure reducer exercised only by the single private identity owner (T2's
activation seam, the sole writer). Verification it calls is owned by
**`@tm/space` `src/service/SpaceContextService.ts:verifyActingContext`**
(one-snapshot, read-only), reached from the browser through the T1
same-origin mirror.

1. **Sticky explicit selection wins always.** A CMDK activation carries a
   server-inventory row (a worktree row supplies `rootCanvasId`; a canvas row
   supplies its anchor), so it verifies locally without a round-trip and
   transitions to `acting` synchronously. Only another selection or the
   explicit Space-switch clear replaces it.
2. **On boot: the URL candidate**, when scoped; else **the locator candidate**;
   else rule 4. Whole tuples only; fields from different candidates are never
   combined; meta never fills another source.
3. **A candidate acts only by verification** through
   `verifyActingContext` (or an exact match against fetched inventory rows). A
   scoped URL candidate that fails verification surfaces a visible error and no
   lower source substitutes for it (no-substitution rule). A failed locator
   candidate is the sole exception: discard only the locator entry, then rule 4
   may resolve the current workdir without touching panes, layout, or cache.
   Staleness is semantic: owner differs, row deleted, worktree inactive or
   missing, anchor mismatch; never cache age.
4. **The workdir-context query is the last resort** from `unresolved` with no
   candidate: `@tm/space:SpaceContextService.resolveWorkdirContext(cwd, owner)`
   with `meta.cwd`, read-only, fail-closed on N:1 path matches.
   `core/useMeta.ts:useMeta` keeps `staleTime: Infinity`, which is correct
   precisely because meta no longer carries identity rank.

Both non-negotiable behaviours follow: reload verifies the scoped URL tuple and
rehydrates; a non-cwd selection is `acting` and nothing lower-ranked, meta
included, can demote it.

## 5. Slices

Gate baseline for every slice is the repo recipe, verbatim:
`just check && just test` (includes the shell frontend suite, contract purity,
`importGraphBoundary.test.ts`, and the API pytest run). Per-slice additions
below. `just test-affected` is the inner loop only, never the gate.

**S1 — Contract and brands.**
Goal: add `@tm/contract/space` (brands + constructors, `ActingContextReceipt`,
`ActingContextCandidate`, shipped Python failure codes) and
`@tm/contract/space/testing`
(shared parity fixtures, the cross-plane fixture table); move the wire DTOs out
of `core/spaceTransport.ts`; delete the bare aliases there and the duplicate
`paneRecords.ts:CanvasId`.
`packages/contract/src/space/fixtures.ts:ActingContextParityFixture` records
`expectation_status: shipped | proposed`: `shipped` pins an existing Python
outcome, while `proposed` is reserved for the unmatched-workdir no-seed case.
Gate: `just check && just test`, plus
`grep -rn "type SpaceId\|type WorktreeId\|type CanvasId" www/ packages/` proving
one TS declaration site.
Works without S2: yes (typing only, zero behaviour).
**Shipped** (`a55371ff`, PR #325).

**S2 — `packages/space`, the verification context.**
Goal: `@tm/space` with `SpaceContextService.verifyActingContext` (whole-tuple
verification in one repeatable-read, read-only transaction) and
`resolveWorkdirContext` (cwd→tuple, `canonical_path` + containing-worktree
normalisation, fail-closed on N:1); read-only Postgres repository as the
structural no-seeding proof; `createSpaceRouter` mounted by `@tm/gateway`;
Python conformance test consuming the `@tm/contract/space/testing` fixtures so
`api/v1/launch_resolution.py:resolve_run_canvas` and the new service provably
enforce one rule.
Gate: `just check && just test`, plus the fixture matrix covering every failure
code and N:1, a repeatable-read consistency test, and a transaction probe
asserting zero row writes and unchanged git worktrees.
Works without S3: yes (surface ships dark, no consumer).
**Shipped** (`cea43eea`). Post-ship finding, recorded honestly: the verify
surface was mounted only on the gateway origin, which no browser can reach in
any mode, and no test asserted the browser origin serves it. T1 exists
because of this.

**S3 — Browser client package, mechanical moves.**
Goal: create `@tm/space-client`; move the Space fetchers from
`core/spaceTransport.ts` and the URL tuple codec out of `canvas/src/route.ts`
into it; prune the dead fetcher surface (`fetchWorktree`, `fetchWorktrees`
outside tests, `fetchCanvas`, `createCanvas`, `updateCanvas`, `deleteWorkdir`
have zero production consumers; keep `fetchCanvases`/`fetchCanvas` only where
T3's child-canvas verification claims them); delete core's `spaceTransport`
barrel line (no permanent re-export).
Gate: `just check && just test` (full-suite rule for structural moves), plus a
dead-surface absence grep.
Works without later slices: yes (canvas still runs legacy ownership).
**Shipped** (`d1f499e5`).

**Superseded, 2026-07-26: S4, S5, S6.** PR #328 (S4's implementation) was
closed unmerged and the S4–S6 sequence is replaced by T1–T4 below. What this
plan got wrong, on the record. First, S4's dual-write bridge was maintained by
enumeration against four named legacy writers, but under the adjudicated
counting rule there are twelve production acting-identity mutation operations
across three representations (§6), and the exported raw
`useCanvasStore.setState` makes any enumeration non-total, so the bridge
could not hold and the shadow store added a fourth live representation to a
system whose defect was already too many. Second, the plan moved from
"identity must not be in the persist blob" (§7, §8) to "identity needs its
own store" without arguing the step; the persistence whitelist already keeps
identity out of the blob while it lives in the canvas store, so persistence
never forced separation. The separate-owner conclusion survived, but for a
different, argued reason: removing the fields from `CanvasStoreState` is the
only mechanism that makes a stray identity write a compile error rather than
a reviewed convention.

- **S4 — superseded.** Live shadow aggregate plus dual-write bridge; three
  reviewers each found a different hole in the same convention, which is the
  empirical signal the enumeration could not be total.
- **S5 — superseded.** The flip survives as T3, over a compiler-enforced
  single writer instead of a bridge a reviewer must trust; its six red-first
  evidence tests carry over unchanged.
- **S6 — superseded.** Contraction and the locator survive as T4 in
  substance; the deletion list shrinks because T2 absorbs the writer symbols
  and the mirror earlier.

**T1 — Reach the control plane.**
Goal: make the S2 verification surface reachable. Today
`gateway/src/app.ts:buildGateway` mounts `spaceRouter.ts:createSpaceRouter`
on the gateway origin only, and the browser's origin is Python in all three
modes, so the routes 404 from every browser. Mirror
`POST /v1/spaces/acting-context/verify` and `/resolve-workdir` through the
Python origin beside `run_proxy.py:create_run_proxy_mount` (precedent: the
activity mirror, "Mirror gateway-owned activity through the Python origin"),
with an explicit 503 degrade when no gateway is configured, in the
`runs_unavailable` style, so "no gateway" is distinguishable from "route
missing". Put the two route paths in the shared contract fixture corpus
(`packages/contract/fixtures/`), consumed by
`spaceTransport.ts:verifyActingContext` on the TS side and asserted against
the app's route table on the Python side, so path drift is unshippable from
either plane. Re-implementing verification in Python is ruled out by the
one-control-plane rule; pointing the browser at the gateway origin is ruled
out by the one-origin contract.
Gate: `just check && just test`, plus `test_space_proxy.py` forward and
degrade tests in the `test_run_proxy.py` style,
`testSupport/originContractGateway.ts` extended to mount the space router,
and the cross-plane path assertion from both planes.
Works without T2: yes — dark surface end to end, independently revertable.

**T2 — Single private owner, behaviour preserving.**
Goal: identity leaves `CanvasStoreState` entirely. Delete `spaceId`,
`defaultWorktreeId`, and `canvasId` from the state type; a private identity
owner module holds them, keeps its raw store unexported, and exposes
selectors plus a closed `IdentityCommand` union (`initialize-from-launch`,
`select-space`, `select-worktree`, `select-canvas`,
`adopt-default-worktree`). The owner absorbs all twelve mutation operations
enumerated in §6: the six canvas store paths, the three `activeCanvasId`
mirror assignments (the mirror becomes the owner's cache-key derivation
feeding `canvasCacheStorage.ts:createCanvasCacheStorage`), and the three
`CanvasCommandDispatcher.ts` URL writes, so URL replacement, cache selection
and `persist.rehydrate()`, Space clear, selection, and workdir adoption are
one module's job. It writes legacy-equivalent values only: no aggregate
state, no behaviour change; migrated readers preserve per-field null
semantics (a worktree-only tuple still marks "Current"). Existing canvas
actions keep their unrestricted setter, yet an attempted identity write
anywhere outside the owner is now a compile error, which also closes the
exported `setState` escape for identity. The owner's package home is fixed at
build time by §2's placement test (the seam scouts split between `@tm/canvas`
and `@tm/space-client`; the adjudication binds the ownership properties, not
the path) and the choice is recorded in the T2 PR. Pure rules (the reducer,
the URL codec, transport) stay in `@tm/space-client` either way.
Gate: `just check && just test` (full-suite rule, structural), a grep proving
zero identity fields on `CanvasStoreState` and `replaceState` confined to the
owner module, the "Current"-marker per-field pin, and
persist-OLD-snapshot-then-rehydrate.
Works without T3: yes — pure refactor; one writer already holds.

**T3 — Authority flip.**
Goal: `ActingContext` (§3) becomes the owner's state from its first
production commit; there is never a second live identity representation.
Every command runs `resolveActingContext`, repaired from #328's known reducer
defects (the generation watermark survives `clear`/`unresolved`;
verified-claim precedence over workdir-context); legacy-shaped selectors
become projections of the aggregate. CMDK selections install verified
inventory rows synchronously, with the receipt's anchor worktree
(`commandRows.ts:anchorWorktreeId`) kept distinct from the spawn-target
default; URL and locator candidates verify through T1's mirror under the
generation guard; failed selection is atomic (URL, store, cache, locator all
unchanged); `navigationSpaceId` splits Space browse scope out of acting
identity. Per-pane worktree pins become receipt-derived via
`withWorktree(receipt, pin)`, so the wire-sourced worktree in
`capturedRunAdoption.ts:candidateFromWire` cannot enter a pane record
unmediated. Boot becomes candidates → verification → aggregate.
This is the slice a diff reader demonstrably cannot judge, so the evidence is
pre-landing, each test red before the flip:
(a) reload from a scoped-unverified URL with a populated per-canvas cache
restores panes and a CMDK launch succeeds — the exact
`canvas_affinity_required` 400 re-run; (b) meta frozen to worktree A, select B:
the spawn carries B's complete triple and persistence stays keyed to B; (c)
child-canvas reload recovers with no root-canvas substitution; plus stale-meta,
late-boot-response (generation guard), and failed-selection probes, and one
live browser A/B probe against a running desktop.
Gate: `just check && just test` plus the six named tests and the live probe.
Works without T4: yes (projections feed the remaining legacy readers).

**T4 — Contraction and locator.**
Goal: delete the remaining legacy symbols: the `SessionCanvasRoute.tsx`
meta-wins line, `route.ts:isUsableIdentity`, `resolveCanvasLaunchIdentity`,
`defaultCanvasId`, `canvasIdVerified`, and the legacy-shaped projections T3
left for unmigrated readers (`adoptDefaultWorktree` and the
`getActiveCanvasId` module mirror were already absorbed by T2). Add the
locator: a **window-scoped `sessionStorage`** entry (gpt's shape, adopted: it
removes the multi-window last-writer-wins race outright) registered in canvas
`infrastructure/persistence/storageKeys.ts`, holding the last receipt +
generation as a boot candidate; re-verified through T1; dangling → discarded,
never wiped. Desktop relaunch (fresh session) recovers via S2's
`resolveWorkdirContext` instead.
Gate: `just check && just test`, plus persist-OLD-snapshot-then-rehydrate,
dangling-locator discard, URL-less boot, two-window isolation test, absence
greps for every retired symbol, and an assertion that
`CANVAS_STORE_STORAGE_VERSION` is unchanged.
Works without S7: yes.

**S7 — Cross-plane conformance and runtime hygiene.**
Goal: brand ids at the `runtimeRouter.ts` boundary from `@tm/contract/space`;
delete `RunManager.ts:DEFAULT_SPACE_ID` / `DEFAULT_WORKTREE_ID`
(`"stub-space"`/`"stub-worktree"` sentinels that can reach persisted
`RuntimeRun`); conformance tests pinning field names and the completeness rule
against Python (`meta.py:MetaResponse`,
`capture_rpc_routes.py:PrepareCaptureRequest`,
`capture_rpc.py:capture_spawn_spec_payload`). Independent of the deferred
launch question (the sentinels are fallbacks production paths never rely on:
canvas launches carry the triple, service launches the pair).
Gate: `just check && just test`, budgeting repair of fixtures that leaned on
the sentinels.
Works alone: yes. Follows T4. End of the committed plan.

Unsplittable: none. The former atomic rewire is now T2–T4 (seam, flip,
contract), each independently gated, with a compiler-enforced single writer
from T2 onward rather than one held by convention.

## 6. Writers and consumers

### The twelve mutation operations

The reconciled writer inventory at `d1f499e5`, under the adjudicated counting
rule: count each direct production operation that can change the browser's
active Space, Worktree, Canvas, or Canvas cache key; count each branch-local
Zustand write, module assignment site, and identity URL rewrite once; do not
multiply a mutation by its transitive callers; exclude tests, unused mutation
capabilities, PR #328's shadow state, and per-pane worktree pins, which are
launch bindings rather than acting context. Under this rule the superseded S4
bridge covered four writers of twelve.

| # | Operation | Representation | Absorbed by |
|---|---|---|---|
| 1 | store initialization via `canvasState.ts:createInitialCanvasModel` at module load | canvas store | T2 |
| 2 | `canvasStoreLifecycle.ts:initializeCanvas`, null-canvas branch | canvas store | T2 |
| 3 | `initializeCanvas`, switching-canvas branch | canvas store | T2 |
| 4 | `initializeCanvas`, same-canvas branch | canvas store | T2 |
| 5 | `canvasStoreLifecycle.ts:selectSpace` | canvas store | T2 |
| 6 | `canvasActions.ts:adoptDefaultWorktree` → `worktreeDefaults.ts:adoptDefaultWorktreePatch` | canvas store | T2 |
| 7 | `canvasStoreLifecycle.ts:resolveLaunchCanvasId` assignment at module load | `activeCanvasId` mirror | T2 |
| 8 | `initializeCanvas` direct `activeCanvasId` assignment | mirror | T2 |
| 9 | the `setActiveCanvasId` callback threaded through `createInitialCanvasModel` | mirror | T2 |
| 10 | `CanvasCommandDispatcher.ts` `select-canvas` arm → `canvasSwitchUrl` + `replaceState` | URL | T2 |
| 11 | `CanvasCommandDispatcher.ts:activateSpace` → `spaceSwitchUrl` + `replaceState` | URL | T2 |
| 12 | `CanvasCommandDispatcher.ts:activateWorktree` → `worktreeSwitchUrl` + `replaceState` | URL | T2 |

### Current T2 production operation count

The twelve above are the historical base inventory that T2 must discharge,
not the direct write count after consolidation. At PR #330 the current
production count is five under the same rule:

| # | Current operation | Representation |
|---:|---|---|
| 1 | `canvasIdentityOwner.ts:useCanvasIdentityStore` initialization | private identity owner |
| 2 | `canvasIdentityOwner.ts:initializeFromLaunch` state write | private identity owner |
| 3 | `canvasIdentityOwner.ts:selectSpace` state write | private identity owner |
| 4 | `canvasIdentityOwner.ts:adoptDefaultWorktree` state write | private identity owner |
| 5 | `canvasIdentityOwner.ts:replaceIdentityUrl` for all three route transitions | URL |

The figure moves from twelve to five because the three branch-local
`initializeCanvas` writes consolidate into one owner write, the three mirror
assignments disappear with the mirror, and the three URL writers consolidate
into one URL operation. The base count remains twelve for discharge
accounting, with all twelve routed or deleted.

Excluded by the rule, with dispositions so nothing is silently absent: the
raw Canvas Zustand setter is module-private; Canvas actions receive a
`CanvasStoreSet` capability whose patches forbid the retired identity fields,
including structurally wider functional returns; and compile pins keep both
field removal and setter restriction loud. Test reset and patch capabilities
live in `canvasStore.testSupport.ts`, receive their private callbacks once at
module wiring, and throw unless `import.meta.env.MODE === "test"`. The per-pane
pin flows
(`canvasActions.ts:addCapturedRun` / `adoptCapturedRun` / `continueSession` /
`spawnTerminal`, plus persist rehydrate via
`canvasStore.persistence.ts:paneRefsForOpenRecords`) are launch bindings and
keep their own boundary: T3 makes them receipt-derived through
`withWorktree(receipt, pin)`, the sharp case being
`capturedRunAdoption.ts:candidateFromWire` branding a wire-sourced worktree
straight into a pane record. PR #328's `actingContextStore.ts` writers were
discarded with the PR.

### Consumer table

Every identity consumer today and what its call becomes. Omission of this step
is what broke worktree switching last round.

| Consumer today | Becomes | Slice |
|---|---|---|
| `CanvasCommandDispatcher.ts:activateWorktree` / `activateSpace` / `select-canvas` arm | thin adapters dispatching `IdentityCommand`s to the private owner (URL write + install + cache rehydrate as one primitive; re-select guard moves into the owner) | T2 |
| `launcher/workdirRows.ts:worktreeRowActions`, `commandRows.ts:buildCanvasRows`, `useLauncherRows.ts`, `commandTypes.ts` | unchanged grammar; payloads carry one whole candidate/row with branded ids | S1, T3 |
| `launcher/CommandCenter.tsx` (`activeSpaceId`/`activeWorktreeId`/`activeCanvasId`), `useCommandCenter.ts`, `useLauncherData.ts` | identity-owner selectors (legacy per-field semantics in T2, phase-based after the flip); Space browse scope from `navigationSpaceId` | T2, T3 |
| `launcher/useSpaces.ts:useSpaces`, `useCanvases.ts` | `@tm/space-client` inventory adapter, same query keys | S3 |
| `workbench/spaceCommandDispatcher.ts:dispatchSpaceMutation` | `@tm/space-client` mutation adapter; create-workdir activates via the shared primitive | S3, T3 |
| `SessionCanvasRoute.tsx` (meta-wins line, `storeIdentity`, `resolveCanvasLaunchIdentity`, `adoptDefaultWorktree` effect) | boot use case: candidates → S2 verification via T1's mirror → aggregate; renders from phase; `worktreeResolutionFailed` becomes the degraded-phase render | T3, deleted T4 |
| `canvasStoreLifecycle.ts:initializeCanvas` / `selectSpace` / `getActiveCanvasId` | absorbed into the owner as commands; cache restore + `persist.rehydrate()` invoked by the owner; the mirror becomes the owner's cache-key derivation | T2 |
| `viewers/registry.tsx` captured-run registration (today splices `props.canvas.spaceId` + pane `contentRef.worktreeId` + `props.canvas.id` from two sources) | one `ActingContextReceipt` with per-pane worktree pin via `withWorktree(receipt, pin)` | T3 |
| `CapturedRunPane.tsx` → `useCapturedRunBinding.ts` → `capturedRunStore.ts:ensureRun` → `core/transport.ts:createCapturedRunView` | chain carries the receipt; optionality gone for canvas launches; server seam unchanged (`POST /v1/runs` → `capture_rpc_routes.py:_resolved_domain_request` still re-resolves) | T3 |
| `canvasActions.ts:addCapturedRun` / `spawnTerminal` / `continueSession`, `worktreeDefaults.ts:requireWorktreeId` | read acting worktree from the identity owner; same unrooted-canvas throw | T2, T3 |
| `capturedRunAdoption.ts:candidateFromWire`, `CapturedRunAdoptionReconciler` | unchanged discriminator (`launch_kind === "service"`); branded ids; the wire-sourced worktree admitted only through the receipt-derived pin constructor | S1, T3 |
| `canvasCacheStorage.ts:createCanvasCacheStorage` | keyed from the owner's cache-key derivation, the aggregate's acting `canvasId` after the flip; null while not acting | T2, T3 |
| `canvasPersistOptions.ts`, `canvasStore.persistence.ts` | untouched shape and version | never |
| `CanvasWorkbench.tsx`, `CanvasPaneLayer.tsx`, `ViewerCanvasContext` | props/context built from owner selectors, the receipt after the flip | T2, T3 |
| MCP director: `controlplane/launch_service.py:ControlPlaneLauncher._prepare` (principal pair from `capture_rpc.py:CaptureLeaseRegistry.resolve_control_plane_grant` live lease facts), `controlplane_gateway_runs.py:create_run` (`launchKind: "service"`) | unchanged at runtime; completeness rule conformance-pinned; whether it later carries a full receipt is the deferred question (§9) | S7; §9 |
| Runtime: `runtimeRouter.ts`, `RunManager.ts`, `CaptureRpcClient.ts`, `runtimeRun.ts` | branded ids at the router boundary; stub sentinels deleted; shapes otherwise unchanged pending §9 | S7 |
| Python downstream affinity consumers (`session/ingest.py:_binding_affinity`, `session/dao_rows.py:session_params`, `session_models.py:session_view_from_row`, `shared_proxy/binding.py:trusted_binding_affinity`, `run_lifecycle.py:build_run_lifecycle_event`, `index/adapters/base.py:SessionBinding`) | untouched; they consume the server-built `SessionAffinityStamp`, whose production path this plan does not change | none |
| Inspector, host, terminal transport, session picker, transcript panes | no identity usage (verified); untouched | none |

Capability owners the plan binds to, or "none found": brand pattern
`packages/activity/src/ids.ts`; contract subpath convention + purity test
`packages/contract/src/packagePurity.test.ts`; boundary enforcement
`www/packages/shell/src/testSupport/importGraphBoundary.test.ts`; inventory
fetch + invalidation `launcher/useSpaces.ts:SPACES_QUERY_KEY`,
`workbench/spaceCommandDispatcher.ts:refreshSpaces`; server verification
`api/v1/launch_resolution.py:resolve_run_canvas` behind
`capture_rpc_routes.py:_resolved_domain_request`; read-only cwd pieces
`space/identity.py:canonical_path`, `space/detection.py:containing_worktree`,
`space/service.py:SpaceCrudService.list_worktrees_by_path`; persist plumbing
`core/persistence.ts:createFrontendPersistStorage`, canvas
`storageKeys.ts` registry; same-origin mirror precedent
`run_proxy.py:create_run_proxy_mount` (the activity mirror comment states the
rule) with `runs_unavailable` as the degrade shape; cross-plane fixture
corpus `packages/contract/fixtures/`, consumed by
`packages/contract/src/space/fixtures.ts` and
`api/src/transport_matters/space/testing.py`. None found (searches in the
scout reports): an existing precedence owner (the rule is folklore across the
four files named in §1); a client cwd resolver; any prior `@tm/contract`
space subpath; a non-seeding cwd→tuple server read (the pre-#321 one seeded:
`resolve_cwd(create=True)` + `_materialize_missing_worktree`, verified at
`df052e65^`); any test asserting the browser origin serves the
acting-context routes (T1's reason for existing).

## 7. What not to do

- Do not re-tune the `SessionCanvasRoute.tsx` precedence line; it is deleted in
  T4, and precedence lives in one reducer or the design has failed.
- Do not put identity fields on `CanvasStoreState`, ever again. There is no
  bridge window: from T2 onward the fields do not exist on the state type, so
  a mirrored field beside the owner is a compile error, not a convention a
  reviewer must police. A mirrored field with no stated precedence is the
  exact prior blocker mechanism, and the enumeration-maintained bridge over
  it is what sank S4.
- Do not export the identity owner's raw store or `setState`; selectors and
  the closed `IdentityCommand` union are its entire surface.
- Do not duplicate verification in Python and do not point the browser at the
  gateway origin; the browser reaches `@tm/space` only through the T1
  same-origin mirror.
- Do not persist identity inside the canvas blob:
  `canvasPersistOptions.ts:migrate` returns empty, so any
  `CANVAS_STORE_STORAGE_VERSION` bump wipes every canvas, and the canvasId
  needed to read the blob cannot live inside it.
- Do not trust a candidate: URL, locator, and persisted values are claims;
  acting requires server verification every time; a failed verification
  discards the claim, never the stored panes.
- Do not let meta be consulted outside `unresolved`, and never let it fill a
  field of another source.
- Do not merge fields across candidates; whole tuples only.
- Do not infer a root canvas when a child canvas claim fails; surface the
  failure.
- Do not seed on read anywhere: no `resolve_cwd(create=True)`, no
  `_materialize_missing_worktree`, no create-on-resolve. The one legitimate
  creation site outside explicit CRUD stays
  `cli/space_bootstrap.py:bootstrap_cli_space` (an explicit launch command).
- Do not brand ephemeral ids (`PaneId`, run keys, event ids): brand aggregate
  identity keys only.
- Do not add a second launch seam; both clients keep terminating at
  `_resolved_domain_request`.
- Do not put Space concepts in `@tm/common`, and do not leave a compatibility
  re-export in `@tm/core`.
- Do not import `@tm/space` from any browser package; browsers consume
  `@tm/contract/space` and `@tm/space-client`.

## 8. Persistence

**No slice bumps `CANVAS_STORE_STORAGE_VERSION` and no canvases reset.** The
canvas blob shape (`canvasPersistOptions.ts:partializeCanvasState`) is
untouched in every slice, so `migrate` (which returns empty state) is never
triggered. The single persistence addition is the T4 locator: one new
**window-scoped `sessionStorage`** entry registered in canvas
`infrastructure/persistence/storageKeys.ts`, additive, discardable, holding the
last verified receipt + generation. Nothing in the union contradicts this; both
reconciled plans state it identically, and the owner's compat waiver goes
unspent.

## 9. Deferred, open question: launch-context propagation

Owner's disposition: **deferred, not rejected and not adopted.** Decide after
the committed sequence (S1–S3 shipped, T1–T4, S7) has shipped, on evidence
from working code. This is gpt's reconciled
slices 7–8: expand every launch hop (principal, `ControlPlaneLauncher`,
`GatewayCreateRunRequest`, runtime spawn spec, capture prepare, lease facts,
session affinity) to accept and dual-emit a complete `ActingContextReceipt`
beside the legacy fields with equality assertions and field-drop mutation
tests, then flip to require it, reject pair-shaped authority, and delete the
legacy fields.

The case for it (gpt's terms): the service pair is a second completeness rule;
a director launch that carries no canvas cannot prove placement, adoption
compares partial contexts, and one receipt through every hop gives CMDK and MCP
one identical launch shape with drift caught by construction rather than by
convention; `ControlPlanePrincipal` today "loses Canvas and therefore cannot
prove launch placement".

The case against it (fable's terms): `LAUNCH-CONTRACT.md:LaunchRequest` has no
canvas field and states clients express intent; canvas placement is a
product-surface concern, and placement-by-adoption is the shipped mechanism
(`capturedRunAdoption.ts:candidateFromWire` accepts service runs; the evidence
session's MCP panes rehydrated exactly this way);
`capture_rpc.py:capture_spawn_spec_payload` never echoes a canvasId and
`controlplane/grants.py` does not persist the space pair, so the wire treats
placement as outside capture's contract; a required canvas on the principal
would stamp the launching agent's canvas onto every child run.

Also parked here, distinct and further out: gpt's reconciled slice 9 (moving
Space CRUD, projections, REST and MCP ownership behind `@tm/space`, retiring
the Python owners). Proposed by gpt, contested by fable (platform migration
beyond this defect; a node `GitWorktreeProbe` would duplicate
`space/detection.py`), not covered by the owner's decision. Decide it after the
launch question, not before.
