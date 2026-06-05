# Space/Worktree/Canvas identity — package boundary design (fable)

Baseline `ml/s6-identity` at `963fd8f8`, tree pristine before and after this pass
(only the pre-existing one-line `LESSONS.md` edit, not mine, not in scope).
Read-only design pass. Citations are file:symbol throughout. Evidence base:
`tm-rehydrate-identity-evidence.md`, both scout reports, both reviews, the two
rejected commits at `ml/s5-rehydrate` (read, not built on), and a fresh two-track
sweep of every TS and Python identity consumer at this HEAD.

## 0. State ownership today (the ground the design stands on)

| State | Owner today | Writers | Readers | Which writer wins today |
|---|---|---|---|---|
| Identity truth (rows) | Postgres via `space/service.py:SpaceCrudService` | CRUD mutations; `cli/space_bootstrap.py:bootstrap_cli_space` create-fallback | `list_worktrees_by_path`, `resolve_launch_worktree`, `get_canvas`, REST `space_routes.py`, MCP `space_mcp.py` | single writer, sound |
| Launch verification | `api/v1/launch_resolution.py:resolve_run_canvas` / `resolve_run_worktree`, sole caller `capture_rpc_routes.py:_resolved_domain_request` | server only; overwrites caller values with resolved ones | both launch kinds | single seam, sound |
| Client acting identity | **nobody** | `canvasStoreLifecycle.ts:initializeCanvas`, `canvasStoreLifecycle.ts:selectSpace`, `canvasState.ts:createInitialCanvasModel`, `worktreeDefaults.ts:adoptDefaultWorktreePatch` via `canvasActions.ts:adoptDefaultWorktree`, plus the URL via `CanvasCommandDispatcher.ts:activateSpace/activateWorktree` | ~20 sites (§5) | folklore: `SessionCanvasRoute.tsx` line `identity = isUsableIdentity(meta) ? meta : storeIdentity`, plus null-coalescing in `initializeCanvas` |
| URL tuple | `route.ts` codecs | `CanvasCommandDispatcher.ts` (only production writer) | `SessionCanvasRoute.tsx`, `canvasStoreLifecycle.ts:resolveLaunchCanvasId` | writer is fine; the defect is that readers treat it as an identity *source* with an unstated rank |
| Desktop meta identity | `api/v1/meta.py:get_meta` ← `session/affinity.py:affinity_from_launch_fields` | CLI launch stamp only; `cli/desktop_cmd.py:_DESKTOP_BACKEND_STALE_ENV_KEYS` strips `LAUNCH_FIELDS`, so desktop meta is null at this HEAD | `SessionCanvasRoute.tsx` (identity + `adoptDefaultWorktree`); frozen per page load by `core/src/useMeta.ts:useMeta` `staleTime: Infinity` | the contested writer: the rejected round made it always-usable and it outranked the user's verified selection |
| MCP/service launch identity | `controlplane/launch_service.py:ControlPlaneLauncher._prepare` ← `capture_rpc.py:CaptureLeaseRegistry.resolve_control_plane_grant` (live lease facts) | server only | `controlplane_gateway_runs.py:create_run` (`launchKind: "service"`, never a canvasId) | single writer, sound |
| Persisted client identity | none (by omission) | `canvasPersistOptions.ts:partializeCanvasState` persists no identity field; per-pane `worktreeId` rides in `contentRefs`; the canvas UUID exists only inside the localStorage *key* (`canvasCacheStorage.ts:canvasCacheKey`) | rehydrate | the bootstrap hole: the id needed to read the blob is stored nowhere readable |

Four derivation sites, no authority, implicit precedence. The design below gives
the client acting identity one owner and one stated rule, and leaves the two
already-sound server seams exactly where they are.

## 1. Boundary

**Context: Spaces.** The owner-organized Space → Worktree → Canvas tree (the
top-level director layer in the repo model) and the client's **acting position**
within it. The missing aggregate is the acting position: "which Space, worktree
and canvas am I acting in", with a verification lifecycle.

**Two homes, per existing repo convention (the Activity precedent):**

1. **`@tm/contract/spaces`** — a new subpath of the existing contract package
   (`packages/contract`, zero-dep, subpath-per-context by design per
   `packages/AGENTS.md`). Owns the branded ids, the complete-triple type, and the
   wire DTO shapes that cross plane seams. Not a new package.
2. **`@tm/spaces` at `www/packages/spaces`** — the new package. A browser-tier
   product-plane package owning the acting-position aggregate, the precedence
   rule, the URL tuple codec, and the Space inventory client adapters.

**What `@tm/spaces` owns:** the `ActingContext` aggregate and its transitions;
the single precedence reducer; claim verification against server data; the URL
tuple codec; the persisted locator; the Space inventory read/mutation transport
(moved out of `@tm/core`); scenario fixtures.

**What it does not own:** identity truth (Postgres via `SpaceCrudService`, capture
plane, unchanged); launch verification (`_resolved_domain_request` +
`launch_resolution.py`, unchanged, still the one seam both clients terminate at);
the launcher command grammar and pane orchestration (canvas product UI); run
identity (`RunId`/`WorkspaceId` stay `@tm/activity`); workspace identity
(slug/hash, stays where it is).

**Plane:** product plane, browser tier (`www/packages/*` per
docs/ARCHITECTURE.md "Product package placement"). The reason: the aggregate is
per-window session state, composed of URL, localStorage, and a user selection.
No server can own it, and no other browser package may own it: `@tm/core` owns no
domain (the junk-drawer fact) so it can host no invariant, and leaving it inside
`@tm/canvas` is what produced the smear across four files. Identity *truth* and
*verification* stay capture-plane Python; this package holds only
server-verified facts plus unverified claims, explicitly typed as such. When
Space CRUD one day migrates to the node Gateway, only the adapter base URL moves;
`@tm/contract/spaces` is already positioned on the seam.

**Canonical context shape, directory by directory:**

| Directory | Verdict | Content |
|---|---|---|
| `src/index.ts` | needed | explicit surface; deep imports fail the existing `importGraphBoundary.test.ts` |
| `src/domain/` | needed, the heart | `actingContext.ts` (aggregate, transitions, the precedence reducer), pure, no IO |
| `src/events.ts` | ceremony today, skip | no second browser context consumes Spaces facts; store subscription serves observers. Add when a real cross-context consumer appears |
| `src/service/` | needed | the activation and boot use cases: the one shared activation primitive both prior scouts demanded (URL write + verify + store install + cache rehydrate as one operation) |
| `src/ports.ts` | needed | `HistoryPort` (URL read/replace), `InventoryReader` (spaces + canvases), `BootAffinityReader` (meta), `LocatorStorage` |
| `src/adapters/` | needed | `spacesApi.ts` (moved from core `spaceTransport.ts`), `urlTupleCodec.ts` (moved from canvas `route.ts`), `browserHistory.ts`, `metaAffinity.ts`, `locatorStorage.ts` |
| `src/projections/` | light | claim-to-row matching selectors over inventory (find the worktree/canvas row a claim names); launcher row *presentation* stays canvas |
| `src/server/` | not applicable | serving is capture-plane Python (`space_routes.py`, `space_mcp.py`); this context deliberately has no TS server half |
| `fixtures/` | needed | the scenario corpus the last round lacked: stale-meta-vs-selection, scoped-unverified URL, dangling locator, N:1 ambiguity. Shared with canvas tests to kill the "suite models a desktop that no longer exists" drift (review m2) |

## 2. Inventory

### Declaration sites of the three ids today

| Site | Shape |
|---|---|
| `www/packages/core/src/spaceTransport.ts:SpaceId/WorktreeId/CanvasId` | bare `string` aliases (while `RepoGroupKey` beside them IS branded, so the file already contains the right pattern and didn't use it) |
| `www/packages/canvas/src/model/paneRecords.ts:CanvasId` | second bare alias; the same file imports `SpaceId, WorktreeId` from `@tm/core` and redeclares the third; no external importer |
| `api/src/transport_matters/space/models.py:SpaceId/WorktreeId/CanvasId` | nominal `_UuidId` subclasses, `type(self) is type(other)` equality: the strongest branding in the repo, already the standard |
| `api/src/transport_matters/session/models.py:SpaceRef` | deliberate downgrade of `space_id` to `str` on session rows while `worktree_id`/`canvas_id` on the same rows stay branded |
| `packages/runtime` (node) | no types at all: bare optional strings in `ports.ts`, `runManagerTypes.ts`, `runtimeRouter.ts`, plus `RunManager.ts` `DEFAULT_SPACE_ID = "stub-space"` / `DEFAULT_WORKTREE_ID = "stub-worktree"` sentinels that can reach the persisted `RuntimeRun` |
| `packages/contract` | knows nothing of the three ids (verified: zero hits outside an activity fixture literal) |

Target: one TS declaration site, `@tm/contract/spaces`, branded per the
`packages/activity/src/ids.ts` pattern (`asSpaceId`/`asWorktreeId`/`asCanvasId`),
constructed once at reader boundaries. Python keeps `space/models.py`, already
compliant. Both `string`-alias sites are deleted.

### Moves out of `www/packages/core` into `@tm/spaces`

- `spaceTransport.ts` fetchers and mutations (`fetchSpaces`, `createSpace`,
  `renameSpace`, `deleteSpace`, `createWorkdir`, `deleteWorkdir`,
  `fetchWorktrees`, `fetchWorktree`, `fetchCanvases`, `fetchCanvas`,
  `createCanvas`, `updateCanvas`) plus both test files — the whole Space HTTP
  surface, because transport for a domain belongs to the domain's package.
  Cycle note from the dep sweep: these depend on `core/src/transport.ts:requestApiJson/requestApiVoid`,
  so `@tm/spaces` depends on `@tm/core`; safe because core will no longer
  reference anything in `@tm/spaces` (types come from contract, which core
  already depends on).
- `spaceTransport.ts` DTO types (`WorktreeSummary`, `CanvasSummary`,
  `SpaceSummary`, `SpaceListResponse`, `CanvasPathSegment`, lifecycle enums,
  `RepoGroupKey`) → `@tm/contract/spaces`, because they are wire shapes crossing
  the plane seam and node runtime needs the ids too.
- Note: `fetchWorktree`, `fetchWorktrees`, `fetchCanvas`, `createCanvas`,
  `updateCanvas`, `deleteWorkdir` have zero production consumers today (sweep
  verified). Keep `fetchCanvases`/`fetchCanvas`: claim verification for non-root
  canvases (review M2) gives them their first real consumer. Judge the rest for
  deletion in the move slice rather than porting dead surface.

### Moves out of `www/packages/canvas` into `@tm/spaces`

- `route.ts` identity half: `CanvasLaunchContext`, `parseCanvasLaunchContext`,
  `worktreeSwitchUrl`, `spaceSwitchUrl`, `canvasSwitchUrl`, `isDurableCanvasId`
  → `adapters/urlTupleCodec.ts`, because the URL is one adapter over the tuple
  and must not fork per surface. `isUsableIdentity`, `resolveCanvasLaunchIdentity`,
  `defaultCanvasId`, `canvasIdVerified` are **deleted, not moved**: the aggregate
  subsumes them (§3). `route.ts` keeps `isStressCanvas` and any non-identity
  routing.
- The identity fields and their writers: `paneRecords.ts:CanvasModel.canvasId/spaceId/defaultWorktreeId`,
  `canvasStoreLifecycle.ts:getActiveCanvasId/setActiveCanvasId` module mirror,
  `worktreeDefaults.ts:defaultWorktreePatch/adoptDefaultWorktreePatch`,
  `canvasActions.ts:adoptDefaultWorktree` → replaced by the aggregate store in
  `@tm/spaces` (single writer). `worktreeDefaults.ts:requireWorktreeId` becomes a
  read against the aggregate.
- `paneRecords.ts:CanvasId` → deleted, import from `@tm/contract/spaces`.

### Stays put, one clause each

- `@tm/core`: `transport.ts` HTTP plumbing (generic), exchanges, capabilities,
  `queryClient`/`queryKeys`, `formatting`, `contentBlocks`, `desktopHost`,
  `keybindings`, `persistence.ts:createFrontendPersistStorage`,
  `activityStreamEvents`, `useEventSource` — none of it is Spaces domain.
  `Meta`/`fetchMeta`/`useMeta` stay in core (meta is broader than Spaces: cwd,
  channel, harnesses); its three identity fields become branded types from
  contract, and `@tm/spaces/adapters/metaAffinity.ts` maps `Meta` → boot
  affinity, removing the duck-typing of `Meta` into `CanvasIdentitySource` the
  sweep flagged.
- `@tm/canvas`: launcher grammar (`commandRows.ts`, `workdirRows.ts`,
  `useLauncherRows.ts`, `CommandCenter.tsx`), pane records and layout engine,
  `canvasCacheStorage.ts` and `canvasPersistOptions.ts` (the persistence *of
  panes* is canvas-owned; only its canvasId key source changes),
  `spaceCommandDispatcher.ts` (a client of `@tm/spaces` mutations),
  `CanvasCommandDispatcher.ts` (thin command adapter dispatching aggregate
  transitions).
- Python: everything. This design requires zero Python change to fix the client;
  the optional meta slice (§6 S5) is additive.
- `@tm/activity:ids.ts` (`RunId`, `WorkspaceId`): different aggregates, different
  contexts; do not merge into contract/spaces.

## 3. The aggregate

```ts
// @tm/contract/spaces (types + pure constructors only)
type SpaceId    = string & { readonly __brand: "SpaceId" };
type WorktreeId = string & { readonly __brand: "WorktreeId" };
type CanvasId   = string & { readonly __brand: "CanvasId" };
/** Complete by construction. The only shape a canvas launch accepts. */
interface CanvasLaunchIdentity {
  readonly spaceId: SpaceId;
  readonly worktreeId: WorktreeId;
  readonly canvasId: CanvasId;
}

// @tm/spaces src/domain/actingContext.ts
interface IdentityClaim {
  readonly spaceId: SpaceId | null;
  readonly worktreeId: WorktreeId | null;
  readonly canvasId: CanvasId | null;
  readonly source: "url" | "locator";
}
type ActingContext =
  | { readonly phase: "unresolved" }
  | { readonly phase: "claimed"; readonly claim: IdentityClaim }
  | { readonly phase: "acting"; readonly identity: CanvasLaunchIdentity;
      readonly via: "selection" | "inventory-match" | "boot-affinity" };
```

**Why an incomplete or unverified triple is unrepresentable:**

1. Completeness: `CanvasLaunchIdentity` fields are non-null branded types. Nulls
   exist only inside `IdentityClaim`, and no launch, persistence-keying, or URL
   write API accepts a claim. The open-coded triple-null checks
   (`isUsableIdentity`, the mount-effect completeness re-implementation flagged
   as review minor 3) disappear because the type is the check.
2. Verification: the only constructors of the `acting` variant are three domain
   transitions whose inputs are server-owned rows, never client strings:
   `actFromSelection(row)` (a `WorktreeSummary`/`CanvasSummary` the user picked in
   CMDK; server inventory data), `actFromInventoryMatch(claim, rows)` (a claim
   confirmed field-by-field against inventory rows), and
   `actFromBootAffinity(meta)` (the server-resolved affinity stamp). URL parsing
   and locator parsing can only construct `IdentityClaim`. The
   `canvasIdVerified` boolean is deleted; the phase is the verification state.
3. Demotion is structurally absent: no transition maps `acting` to `claimed` or
   `unresolved`. `acting` is replaced only by another `acting` (new verified
   selection) or by the explicit space-switch clear (the `selectSpace` semantic,
   which resets to a fresh Space scope deliberately). The exact blocker mechanism
   of the rejected round, `initializeCanvas` nulling a just-verified canvasId
   because a stale meta demoted the resolution, has no expressible code path.

**Reader boundaries where ids are constructed** (the doc's "constructed once at
the machine input or reader boundary"):

- `@tm/spaces/adapters/spacesApi.ts` mapping `GET /v1/spaces` / `/v1/canvases`
  responses (brands minted over wire strings, once).
- `@tm/core/transport.ts:fetchMeta` mapping `MetaResponse` (already maps
  snake_case → camelCase; adds branding).
- `@tm/spaces/adapters/urlTupleCodec.ts` parsing `window.location.search` →
  claim.
- `@tm/spaces/adapters/locatorStorage.ts` parsing the persisted locator → claim.
- Python already complies (`capture_rpc_routes.py:PrepareCaptureRequest.to_domain`
  via `api/v1/ids.py:parse_uuid_id`; `space_mcp.py:_crud_id`; `space_routes.py`
  parsers). Node runtime's `runtimeRouter.ts:nonEmptyString` boundary is the S6
  branding target.

The aggregate is hosted in one zustand store in `@tm/spaces`
(`actingContextStore`), the **single writer**; every mutation goes through the
domain transitions. Canvas components read it through exported selectors.

## 4. Precedence, stated once

Owner: **`@tm/spaces/src/domain/actingContext.ts:resolveActingContext`**, a pure
reducer over the four sources, exercised only by `actingContextStore`. The rule,
in full:

Given explicit user selection S (a CMDK activation carrying a server-inventory
row), URL tuple U, persisted locator L, meta tuple M:

1. **S wins over everything, always.** A selection is server data (the inventory
   row the user picked) and transitions the aggregate to
   `acting(via: "selection")` synchronously. It is sticky for the session: only
   another selection, or the explicit Space-switch clear, replaces it. While the
   aggregate is `acting`, U is an *output* (written by activation through
   `HistoryPort`), and M and L are never consulted. This kills the blocker class:
   meta cannot demote worktree B, because after selecting B nothing reads meta as
   an identity source.
2. **On boot (aggregate `unresolved`): U is the primary claim** when it carries
   any identity field; else **L**; else fall to rule 4. A claim never acts by
   itself.
3. **A claim acts only by verification against server data.** Primary verifier:
   the inventory (`InventoryReader`; spaces for worktree/root-canvas claims,
   canvases for non-root canvas claims, which fixes the child-canvas reload class
   from review M2 with machinery meta can never provide). Exact match on present
   fields, fill of absent fields, `acting(via: "inventory-match")` on success. M
   may also confirm or fill a claim, but only when it does not contradict any
   present field; a scoped claim that mismatches M stays `claimed` pending
   inventory rather than being discarded (the rejected round discarded the whole
   tuple on any mismatch). Verification failure after inventory settles leaves
   the aggregate honestly degraded (`claimed`/`unresolved`: no launch, no
   persistence key, visible alert), never a silent null.
4. **M alone acts only from `unresolved` with no claim**, as
   `acting(via: "boot-affinity")`: the true first-boot case.
5. **Staleness, pinned per source.** M is frozen per page load
   (`useMeta` `staleTime: Infinity`), which is now *correct by construction*
   because M ranks last and is only read from `unresolved`; the rejected round
   broke precisely because a frozen source outranked a live one. The inventory is
   the refetchable verification source of record (`SPACES_QUERY_KEY`,
   `refreshSpaces` invalidation). L is a hint with unbounded age: re-verified on
   every boot, discarded (not wiped) when it names deleted rows.

In short: **selection > URL claim > locator claim, each claim requiring server
verification; meta is the boot fallback of last resort; verified state never
demotes.**

Both governing live behaviours check out: reload holds a scoped URL tuple
(corrected evidence), which verifies against the inventory `SessionCanvasRoute`
already fetches (`needsWorktreeInventory` path), activates, restores the
per-canvas cache, and launches, with meta not consulted. Selecting a non-cwd
worktree is an S transition; the frozen cwd meta is unreadable from `acting`, so
nothing demotes it, launches carry B's complete triple.

## 5. Consumers, and what each call becomes

**CMDK / launcher**

- `CanvasCommandDispatcher.ts:activateWorktree/activateSpace` + `select-canvas`
  arm → thin adapters dispatching `actFromSelection` through the
  `@tm/spaces/service` activation use case (URL write via `HistoryPort` + store
  transition + canvas cache rehydrate callback in one primitive). The
  `activateSpace` re-select guard moves into the service (guarding is part of
  the switch semantic, not dispatcher trivia).
- `launcher/workdirRows.ts:worktreeRowActions`, `commandRows.ts`,
  `useLauncherRows.ts`, `commandTypes.ts` → unchanged grammar; row payloads carry
  branded ids from `@tm/contract/spaces`.
- `launcher/useSpaces.ts:useSpaces`, `useCanvases.ts` → call
  `@tm/spaces/adapters/spacesApi.ts`; same query keys.
- `launcher/CommandCenter.tsx` `activeSpaceId/activeWorktreeId/activeCanvasId`
  reads → `actingContextStore` selectors.
- `workbench/spaceCommandDispatcher.ts` mutations → `@tm/spaces` mutation
  adapter; on create-workdir it activates via the same service primitive.

**Rehydrate / route mount**

- `SessionCanvasRoute.tsx` sheds its identity computation entirely: the
  `identity = isUsableIdentity(meta) ? meta : storeIdentity` line, `storeIdentity`
  memo, `resolveCanvasLaunchIdentity` call, and `adoptDefaultWorktree` effect are
  all deleted. It calls the `@tm/spaces` boot use case (claim from
  `urlTupleCodec` / locator, verify against `InventoryReader` + `metaAffinity`)
  and renders from the aggregate phase; `worktreeResolutionFailed` becomes the
  degraded-phase render.
- `canvasStoreLifecycle.ts:initializeCanvas` → keyed by the aggregate: on
  `acting` transitions the activation service invokes the canvas cache
  restore + `persist.rehydrate()` with `identity.canvasId`; the null-coalescing
  identity patches disappear with the store fields.
- `model/capturedRunAdoption.ts:candidateFromWire` → unchanged discriminator;
  adopted rows carry branded ids.

**Launch composition**

- `viewers/registry.tsx` captured-run registration → composes one
  `CanvasLaunchIdentity` (aggregate identity, with per-pane worktree pin applied
  via a domain helper `withWorktree(identity, pin)`) instead of splicing
  `props.canvas.spaceId` + `props.pane.contentRef.worktreeId` + `props.canvas.id`
  from two sources, the desync seam the sweep flagged.
- `CapturedRunPane.tsx` → `useCapturedRunBinding.ts` →
  `capturedRunStore.ts:ensureRun` → `core/transport.ts:createCapturedRunView` →
  the chain's identity parameter becomes `CanvasLaunchIdentity`; the
  `spaceId?/canvasId?` optionality disappears for canvas launches. Server seam
  untouched: `POST /v1/runs` → `_resolved_domain_request` still re-resolves and
  overwrites.
- `canvasActions.ts:addCapturedRun/spawnTerminal/continueSession` +
  `worktreeDefaults.ts:requireWorktreeId` → read the acting worktree from the
  aggregate; same throw semantic on an unrooted canvas.
- `core/transport.ts:RunFilters/listRuns/RunView` → branded id types, no
  behaviour change.

**MCP / control plane (the twin client)**

- `ControlPlaneLauncher._prepare` (principal pair from live lease facts),
  `controlplane_gateway_runs.py:create_run` (`launchKind: "service"`) →
  **unchanged at runtime**. The design change is conformance: the completeness
  rule ("a canvas launch requires the full triple; a service launch requires the
  pair") is stated once in `@tm/contract/spaces` and asserted against
  `capture_rpc_routes.py` behaviour by a cross-plane contract test, per the
  ARCHITECTURE.md magic-string rule. Both clients keep terminating at
  `_resolved_domain_request`; identity acquisition is server-derived on both
  paths (principal stamp vs inventory verification), so no UI-only identity
  logic survives: the browser's only private state is *which verified identity
  the user is acting in*, which is exactly the state a per-window client must
  hold.

**Persistence**

- `canvasCacheStorage.ts:createCanvasCacheStorage` → `getCanvasId` reads the
  aggregate (`acting` phase only), replacing the `getActiveCanvasId` module
  mirror; still returns null while not acting, so persistence stays disabled in
  degraded states instead of writing under a wrong key.
- `canvasPersistOptions.ts` / `canvasStore.persistence.ts` → untouched shape,
  untouched version (see §7).
- New: `@tm/spaces/adapters/locatorStorage.ts`, a separate localStorage entry
  registered in canvas `storageKeys.ts` (registry rule), holding the last
  verified triple as a claim.

**Non-consumers, verified:** inspector and host read only non-identity meta
fields; terminal transport, session picker, and transcript panes carry no triple;
node gateway proxies opaquely. They are untouched.

## 6. Migration order

Each slice ships independently and leaves the product working. Gates are the
repo recipes (`just check` / frontend `pnpm --filter @tm/shell test` full suite
for structural moves), never bare tool invocations.

- **S1 — one declaration site.** Add `@tm/contract/spaces` (ids, constructors,
  `CanvasLaunchIdentity`, DTO types). Retype `core/spaceTransport.ts` and
  `paneRecords.ts` against it; delete both bare-alias declaration sites; mint
  brands at the existing reader boundaries. Pure typing slice, zero behaviour.
  Gate: typecheck + full frontend suite + `packagePurity.test.ts` +
  `importGraphBoundary.test.ts`.
- **S2 — the package, mechanical moves.** Create `www/packages/spaces`; move
  `spaceTransport` fetchers + tests and the `route.ts` URL codec; update
  imports; delete dead fetcher surface not claimed by S3; extend the
  import-graph boundary test to the new package. Zero behaviour. Gate: full
  frontend suite (structural-move rule: full suite, not filtered).
- **S3 — the aggregate. The one slice that cannot be split.** Introduce
  `ActingContext` + `resolveActingContext` + `actingContextStore` + the
  activation/boot services, rewire `SessionCanvasRoute`, the dispatcher, launch
  composition, and persistence keying, and delete the retired symbols
  (`isUsableIdentity`, `resolveCanvasLaunchIdentity`, `defaultCanvasId`,
  `canvasIdVerified`, store identity fields, `adoptDefaultWorktree`,
  `getActiveCanvasId` mirror). Splitting it would leave two writers of acting
  identity live at once, which is the defect class itself. Gate, asserting the
  capability, not the mechanism, each failing before the change: (a) reload from
  a scoped-unverified URL with a populated per-canvas cache restores panes and a
  CMDK launch succeeds (the original regression, the exact 400 re-run); (b) meta
  frozen to worktree A, select worktree B, spawn carries B's complete triple and
  persistence stays keyed to B (the blocker); (c) reload on a non-root canvas
  recovers (M2). Plus the full suite and the existing launch-affinity tests.
- **S4 — the locator.** Additive persisted claim (new storage key) + boot
  recovery when the URL is unscoped. Gate: persist-OLD-snapshot-then-rehydrate
  test (fresh round-trips lie), dangling-locator-discard test, URL-less boot
  test.
- **S5 — server boot affinity (optional, Python, only after S3).** Rebuild the
  rejected `resolve_existing_canvas_affinity` seam for `get_meta`, from parts:
  `canonical_path` + `detection.py:containing_worktree` normalisation first
  (review M4, subdirectory launches), `list_worktrees_by_path` fail-closed on
  N:1, `resolve_launch_worktree` + `get_canvas` verification, logged degradation
  (review m1), and a structural read-only guarantee (read-only `Protocol`
  parameter or `SET TRANSACTION READ ONLY`, review M3) so the seeding veto is
  enforced by structure, not review. Safe now because the client ranks meta
  last: the mechanism that made `068f989e` a blocker no longer exists. Gate:
  `test_meta.py` matrix + read-only structural test + subdirectory-cwd case.
- **S6 — cross-plane conformance.** Contract test pinning field names and the
  completeness rule against Python (`MetaResponse`, `PrepareCaptureRequest`,
  `capture_spawn_spec_payload`) and node runtime; brand the ids at
  `runtimeRouter.ts` boundaries; delete the `RunManager.ts`
  `"stub-space"`/`"stub-worktree"` sentinel defaults so fabricated identity can
  never reach a persisted `RuntimeRun`. Gate: contract tests on both planes +
  runtime suite.

Hard ordering: S5 must not ship before S3. With the current
`SessionCanvasRoute` precedence line still live, a meta that resolves is exactly
the rejected round's blocker.

## 7. Risk

- **S1/S2** — wide but mechanical; the known failure mode is import fixups
  escaping filtered test runs, hence full-suite gates. No runtime risk.
- **S3** — the real one. Blast radius: launch composition, rehydrate, worktree
  and canvas switching, persistence keying. Mitigations: the three capability
  gates above (each reproducing a previously shipped failure), the fixtures
  corpus replacing the drifted desktop model, and the A/B probe pattern from the
  review round for live confirmation. Roll-back is one revert; no schema or
  persisted-shape change rides with it.
- **Persistence: Stuart's canvases reset nowhere in this design.** The canvas
  blob shape and `CANVAS_STORE_STORAGE_VERSION` are untouched in every slice;
  `canvasPersistOptions.ts:migrate` (returns empty state on version mismatch) is
  never triggered. The locator is a new key, additive; per-pane `contentRefs`
  worktree pins are readable unchanged, becoming claims re-verified by the
  server at spawn exactly as today. The compat waiver exists but is not spent.
  The one residual data note: S4's locator starts empty, so the first reload
  after S4 behaves exactly like today's (URL-carried) recovery until one
  activation writes it.
- **S5** — meta hot-path cost: verify the named canvas via `store.get_canvas` +
  the anchor check rather than the `list_canvases → _snapshot` git fan-out
  (review m3); bounded anyway by one call per page load.
- **S6** — removing the runtime stub defaults may surface tests that relied on
  fabricated identity; that is the point, but budget for fixture repair.
- **Cross-cutting** — the aggregate becomes a single point of failure by design;
  a bug in `resolveActingContext` affects every surface at once. That is the
  accepted trade (one place to fix beats four places to disagree), and the
  reducer is pure, so it carries the densest test coverage in the package.

## 8. What not to do

- **Do not re-tune the `SessionCanvasRoute` precedence line.** Any one-file edit
  of `identity = …` is the fourth round of the same class. The line is deleted;
  precedence lives in one reducer or the design has failed.
- **Do not leave the canvas store holding identity fields "for compatibility".**
  A mirrored `spaceId` in `CanvasModel` next to the aggregate is a second writer
  with no precedence rule, invisible in any diff, the exact B1 mechanism.
- **Do not persist identity inside the canvas blob.** Bootstrap circularity (the
  canvasId is needed to read the blob) plus `migrate` returning empty means a
  version bump wipes every canvas. The locator is a separate key for this
  reason.
- **Do not trust a claim.** URL and locator values name rows that may be deleted
  or re-owned; acting requires server verification, every time. Equally, do not
  let a failed verification wipe anything: discard the dangling claim, keep the
  stored panes.
- **Do not let meta be consultable outside `unresolved`.** Its
  `staleTime: Infinity` freeze makes any higher rank a time bomb; the rejected
  round proved it.
- **Do not put the aggregate in `@tm/core`** (owns no domain, cannot host an
  invariant, the junk drawer grows) **or leave it in `@tm/canvas`**
  (recreates the smear behind a bigger wall) **or make it a node context**
  (per-window session state cannot live server-side).
- **Do not brand ephemeral ids.** `PaneId`, run keys, event ids stay plain per
  the ARCHITECTURE.md identifiers standard; brand aggregate identity keys only.
- **Do not resolve cwd on the client, and do not seed on read anywhere.** The
  cwd→tuple capability is server-side, read-only, fail-closed on N:1. The
  pre-#321 shape (`resolve_cwd(create=True)`, `_materialize_missing_worktree`,
  verified present at `df052e65^` and gone at HEAD) must not return under any
  name; the one legitimate creation site outside explicit CRUD remains the CLI
  launch bootstrap (`bootstrap_cli_space`), which is an explicit launch command,
  not identity resolution.
- **Do not add a second launch seam.** Both clients keep terminating at
  `_resolved_domain_request`; the aggregate changes who *holds* identity
  client-side, never who *authorizes* it.
- **Do not ship S5 before S3.**

## Appendix: bind-to-what-exists ledger

Reused: `packages/activity/src/ids.ts` brand pattern; `packages/contract`
subpath-per-context convention and `packagePurity.test.ts`;
`importGraphBoundary.test.ts` fail-closed enforcement; `fetchSpaces`/
`fetchCanvases` + `SPACES_QUERY_KEY`/`refreshSpaces` inventory machinery;
zustand persist + `createFrontendPersistStorage`; canvas `storageKeys.ts`
registry; server verification seam `launch_resolution.py` +
`_resolved_domain_request`; `068f989e`'s `_resolve_canvas_launch` extraction
shape (for S5); `space/detection.py:containing_worktree` and
`space/identity.py:canonical_path` (for S5).

New code, with the search that found nothing to bind to: the precedence reducer
and aggregate (searched `resolveCanvasLaunchIdentity` callers, `isUsableIdentity`
callers, and all writers of store identity: the rule exists only as folklore
across `route.ts`, `SessionCanvasRoute.tsx`, `canvasStoreLifecycle.ts`,
`CanvasCommandDispatcher.ts`, which is the finding this pass exists to fix); the
locator (searched persisted shapes: `partializeCanvasState` and
`capturedRunStore` partialize persist no identity; the canvas UUID exists only
inside a storage key); the `@tm/contract/spaces` subpath (searched
`packages/contract/src`: no space/worktree/canvas identifiers exist there
today).

Verified non-issues for the cross-check round: `except HTTPException,
SpaceCrudError:` and `except OSError, subprocess.TimeoutExpired:` are valid
PEP 758 on this repo (`requires-python >= 3.14`); `space/service.py:
reconcile_detection` at HEAD skips unknown paths (`if existing is None:
continue`), so reconcile no longer seeds; `068f989e` is not an ancestor of
`ml/s6-identity` (confirmed via merge-base), and `resolve_existing_canvas_affinity`
has zero matches at HEAD.

## Cross-check (after reading ~/.mdx/projects/tm-identity-boundary-gpt.md)

Tree re-verified: only the pre-existing `LESSONS.md` line, HEAD `963fd8f8`.

### Their biggest risk: real in their design, manufactured by it

The gpt slice 3 (atomic `ControlPlaneLauncher` → Runtime → capture cutover,
one merge unit spanning TS control plane, node runtime, Python capture, session
affinity, REST, MCP) is real **given their premise** that every launch kind must
carry a complete triple and `resolve_run_worktree`'s pair mode is deleted. I
refute the premise, so my design does not carry that cutover at all:

- `LAUNCH-CONTRACT.md` `LaunchRequest` has no canvas field, requires `workdir`,
  and states "Clients express intent". Canvas placement is not launch intent for
  a director; it is a product-surface concern.
- The shipped placement mechanism for service launches is adoption:
  `capturedRunAdoption.ts:candidateFromWire` accepts `launch_kind === "service"`
  and the canvas places the pane client-side. The evidence session showed
  exactly this working (the two MCP panes rehydrating via adoption).
- The wire agrees placement is not capture's concern:
  `capture_rpc.py:capture_spawn_spec_payload` never echoes a canvasId, and
  `controlplane/grants.py` does not even persist the space pair (re-derived from
  live lease facts). Making `ControlPlanePrincipal` carry a required canvas
  would stamp the *launching agent's* canvas onto every child run, removing the
  canvas's freedom to place adopted runs and coupling the control plane to a UI
  concept.

So the design carries **one** behavioral cutover (client identity ownership),
not two. Their slice 5 (migrating `SpaceCrudService`, the store ops, projection,
authz, REST and MCP routing from Python into a node package, with a node
`GitWorktreeProbe`) I also maintain against: it re-implements
`space/detection.py` in a second language (their own no-duplication rule), it
is a platform migration smuggled into a defect fix, and nothing in the brief's
defect requires it. Aim rigor at the roadmap: NOW.md's focus is multi-launch.

### Splittability: concession

My "S3 is unsplittable" was true only under the design as drawn (single atomic
swap). The better shape is expand-then-contract with a dual-write bridge, and I
now endorse it:

- **S3a (expand, behavior-preserving):** introduce the aggregate + reducer +
  store in shadow. The existing writers (`initializeCanvas`, `selectSpace`,
  dispatcher activations, `adoptDefaultWorktree`) additionally dispatch
  aggregate transitions; legacy state stays authoritative. One write *path*,
  two stores, precedence between the copies stated at the single derivation
  point. Gate: fixture-corpus parity tests, with the intended divergences
  (meta-vs-selection, child canvas) asserted as divergences.
- **S3b (cut reads):** launch composition, persistence keying, route and
  dispatcher reads move to the aggregate. In every state where the copies
  disagree the aggregate is strictly more available (legacy holds null where
  the aggregate holds the verified tuple), so read cutover is monotonic. The
  user-capability fix lands here; the three capability gates run here, plus
  gpt's failed-selection-atomicity gate (a failed activation changes neither
  URL, store, nor cache).
- **S3c (contract):** delete the meta-wins line, `isUsableIdentity`,
  `resolveCanvasLaunchIdentity`, `canvasIdVerified`, the store identity fields,
  and the dual-write bridge. Gate: full suite plus absence greps.

If it had stayed atomic, the pre-landing evidence would have been the fixture
corpus plus the three capability A/B tests plus a live A/B probe; but the split
is strictly better and answers the orchestrator's structural worry.

### Package shape

`@tm/contract` exists, verified first-hand: `packages/contract/package.json`
exports `./activity`, `./activity/testing`, `./runtime`, enforced by
`packagePurity.test.ts` and the shell import-graph test. Both reports
independently chose a contract subpath; converged.

I concede the **name**: singular `@tm/space` / `@tm/contract/space`, matching
the Python `space/` package and the `space_*` MCP tool vocabulary. I maintain
the **location**: `www/packages/space`, browser tier. The aggregate ranks URL,
localStorage, in-memory selection, and a per-page-load-frozen meta; the
director possesses none of those sources, so hosting the ranking server-side
(their `SpaceContextService.resolveActingContext` endpoint) creates a server
endpoint whose only possible caller is the browser: UI-only logic relocated,
not removed, plus a resolve round-trip on every worktree switch. The twin-client
property lives where it belongs: completeness in `@tm/contract/space`,
verification in `launch_resolution.py` behind `_resolved_domain_request`, both
consumed identically by palette and director. Note also that their "browser
never imports `@tm/space`" leaves the client half (candidate collection,
receipt install, receipt cache) with no named owner, smeared across canvas
model files, which is the disease this pass exists to cure.

### Precedence

Their rule in one sentence: explicit selection > scoped URL > persisted receipt
(only when the URL is unscoped) > meta, each candidate verified server-side as a
whole tuple, no cross-candidate field merging, semantic staleness, and a failed
higher source is a visible error that no lower source may substitute for. It
satisfies both live behaviours (reload verifies the URL tuple; explicit
selection outranks cwd-frozen meta). Content-wise their rule and mine are
isomorphic; the difference is carrier (server endpoint vs client reducer over
server-fetched data). I adopt two of their refinements into mine: the
**no-substitution rule** (a scoped claim that fails verification surfaces an
error and does not fall through to the locator) and the **semantic staleness
vocabulary** (stale = owner differs, row deleted, worktree inactive or missing,
anchor mismatch; never cache age).

### Gaps

Theirs that I adopt: `ownerId` belongs on the aggregate (NORTHSTAR attribution
lens; mine left `owner: "local"` implicit); failed-selection atomicity as an
explicit gate; the `navigationSpaceId` separation of Space browse scope from
acting context; the broader Python downstream-affinity consumer sweep
(session ingest, shared proxy binding, lifecycle projections) as enumeration
completeness, even though my design leaves them untouched.

Mine that they missed: the dead client fetcher surface (`fetchWorktree`,
`fetchCanvas`, `createCanvas`, `updateCanvas`, `deleteWorkdir` have zero
production consumers; their tables migrate all of them as live);
`RunManager.ts` `"stub-space"` / `"stub-worktree"` sentinels reaching persisted
`RuntimeRun`; `useMeta` `staleTime: Infinity` as the concrete staleness
mechanism and why rank-last neutralizes it; the PEP 758 non-issues.

Both missed: multi-window coherence (two windows share the locator key but hold
separate aggregates; URL-outranks-locator makes it benign, but last-writer-wins
on the locator deserves one stated line in S4).

### Converged plan

Package `@tm/space` at `www/packages/space` + `@tm/contract/space` subpath.

1. Contract + brands, delete both bare-alias sites — full frontend suite,
   typecheck, purity, import-graph, one-declaration grep.
2. Package skeleton + mechanical moves (spaceTransport, URL codec, dead-fetcher
   prune) — full frontend suite.
3. Aggregate in shadow, dual-write bridge — fixture-corpus parity tests.
4. Cut reads (launch, persistence keying, route, dispatcher) — the three
   capability A/B gates + failed-selection atomicity.
5. Delete legacy precedence and identity fields — full suite + absence greps.
6. Locator, additive key — persist-old-snapshot-then-rehydrate, dangling
   discard, URL-less boot.
7. Python read-only meta boot affinity, only after slice 5 — `test_meta`
   matrix, structural read-only guarantee, subdirectory cwd.
8. Cross-plane conformance + runtime branding + stub-default removal —
   contract tests on both planes, runtime suite.

Rejected from the converged plan: gpt slices 3 and 5 (triple-everywhere launch
cutover; Python→node space-domain migration), for the reasons above.

## Reconciled plan (under the owner's decision)

Decision applied: verification (completeness, existence, worktree ∈ Space,
canvas anchored to worktree) is a control-plane rule living in a new node
context package `packages/space` (`@tm/space`) behind `@tm/contract/space`,
consumed by palette and director alike; source ranking (selection vs URL vs
locator vs meta) is a browser-local pure reducer over inputs only a browser
has, with no round-trip per switch. Precedence ranks stand: sticky explicit >
URL > locator > meta, whole tuples, server-verified, meta never fills another
source; reload recovers and a non-cwd selection is never demoted.

Structural consequences I now adopt, revising my earlier sections:

- **No new browser package.** With the invariant control-plane and the types in
  contract, the browser residue (reducer, `actingContextStore`, URL codec,
  locator adapter, Space API fetchers) is canvas product state; it lives in one
  named canvas module (`www/packages/canvas/src/space/`), and the fetchers land
  in canvas `infrastructure/api/` (gpt's placement). My `www/packages/space`
  proposal is dropped.
- **My Python meta-affinity slice (old S5/7) is dropped.** The first-boot
  cwd→tuple read becomes a query on `@tm/space` (read-only repository,
  fail-closed on N:1, `canonical_path` + containing-worktree normalisation),
  callable by browser boot and director alike. Python `get_meta` stays
  launch-fields-only; `useMeta` `staleTime: Infinity` stays correct because
  meta ranks last and the boot query replaces its identity role.
- **The verification rule has one canonical home and two enforcement points.**
  `@tm/space` owns the predicates, typed failure codes
  (`PARTIAL_CONTEXT`, `WORKTREE_INACTIVE`, `CANVAS_WORKTREE_MISMATCH`, …), and
  one executable fixture table under `fixtures/`. The Python launch seam
  (`launch_resolution.py` behind `_resolved_domain_request`) keeps enforcing at
  actuation time and is conformance-bound to the same fixture table (the
  ARCHITECTURE.md cross-plane single-sourcing pattern), until the gateway flip
  retires it. No in-process delegation across languages.
- **Both jointly-missed items are folded in.** One-snapshot verification: the
  `@tm/space` repository verifies a whole tuple inside one read
  transaction/snapshot, never piecemeal queries (kills tuple-TOCTOU).
  Monotonic resolution generation: the aggregate stamps every resolution
  attempt with a generation; an async verification result whose generation is
  older than the current selection is discarded, so a slow boot verify can
  never clobber a newer explicit selection. Multi-window locator
  last-writer-wins is accepted and stated (benign because URL outranks
  locator; the locator write carries the generation for diagnosis).
- Service launches keep the pair contract; placement-by-adoption stands. The
  decision adopts neither the triple-everywhere cutover nor the Python→node
  CRUD migration, and both stay rejected. `SpaceCrudService` mutations remain
  Python. Brands stay in `@tm/contract/space` (one declaration site for both
  planes' TS; gpt's brands-in-package split would leave the browser holding
  bare strings again).

### The slices

Each ships alone; the product works with slice N landed and N+1 not.

1. **Contract and brands.** `@tm/contract/space`: branded
   `SpaceId`/`WorktreeId`/`CanvasId` + constructors, `CanvasLaunchIdentity`
   (complete triple, plus `ownerId`), wire DTOs moved from
   `core/spaceTransport.ts`; delete the core bare aliases and the
   `paneRecords.ts:CanvasId` duplicate. Typing only, zero behaviour.
   Gate: full frontend suite + typecheck + `packagePurity.test.ts` +
   `importGraphBoundary.test.ts` + one-declaration-site grep.
2. **`packages/space`, the verification context.** Domain predicates + typed
   failures + the executable fixture table; read-only Postgres repository
   (read-only transaction/role as the structural no-seeding proof);
   `createSpaceRouter` mounted via the gateway serving two reads: verify-tuple
   (one-snapshot) and resolve-workdir-context (cwd→tuple, fail-closed N:1);
   Python conformance test consuming the same fixture JSON. Surface ships dark
   (no consumer yet), so the product is unchanged.
   Gate: fixture-table tests (every failure code + N:1 + one-snapshot proof) +
   gateway inject tests + Python conformance run + a transaction probe showing
   zero row writes.
3. **Mechanical browser moves.** Space fetchers from `core/spaceTransport.ts`
   → canvas `infrastructure/api/` consuming contract types; URL tuple codec
   out of `route.ts` → `src/space/`; prune the dead fetcher surface; delete
   core's `spaceTransport` barrel line. Zero behaviour.
   Gate: full frontend suite (structural-move rule).
4. **Shadow aggregate.** `src/space/` gains `ActingContext` (with `ownerId`),
   the reducer with no-substitution and semantic staleness, the store, the
   generation counter, and the dual-write bridge: existing writers
   (`initializeCanvas`, `selectSpace`, dispatcher activations,
   `adoptDefaultWorktree`) also dispatch aggregate transitions; legacy stays
   authoritative; claim verification calls the slice-2 surface with results
   recorded only. No behaviour change.
   Gate: parity fixtures over the corpus, intended divergences asserted as
   divergences; generation-guard unit tests (stale async verify discarded).
5. **Read cutover.** Launch composition (`registry.tsx` chain), persistence
   keying (`canvasCacheStorage`), route and dispatcher reads move to the
   aggregate; monotonic, since wherever the copies disagree the aggregate
   holds the verified tuple where legacy holds null. The user-capability fix
   lands here. Pre-landing evidence, because a diff reader cannot catch this
   class: the three capability A/B gates, each red before the slice — reload
   from a scoped-unverified URL restores panes and a CMDK launch succeeds (the
   exact 400 re-run); meta frozen to A, select B, spawn carries B's complete
   triple and persistence stays keyed to B; child-canvas reload recovers —
   plus failed-selection atomicity (URL, store, cache all unchanged on a
   failed activation) and a live A/B probe on the running desktop.
6. **Delete legacy.** The meta-wins line, `isUsableIdentity`,
   `resolveCanvasLaunchIdentity`, `canvasIdVerified`, the store identity
   fields, `adoptDefaultWorktree`, and the dual-write bridge all go; the
   aggregate transitions become the only writer.
   Gate: full suite + absence greps for every retired symbol.
7. **Locator.** Additive localStorage key (registered in `storageKeys.ts`)
   holding the last verified receipt + generation as a boot claim; re-verified
   through slice 2's surface; dangling → discarded, never wiped; multi-window
   last-writer-wins accepted and documented.
   Gate: persist-OLD-snapshot-then-rehydrate, dangling-discard, URL-less boot,
   two-window write note/test.
8. **Cross-plane conformance and runtime hygiene.** Brand ids at the
   `runtimeRouter.ts` boundary; delete `RunManager.ts`
   `"stub-space"`/`"stub-worktree"` sentinels; completeness-rule conformance
   across contract, Python (`MetaResponse`, `PrepareCaptureRequest`,
   `capture_spawn_spec_payload`), and runtime.
   Gate: contract tests on both planes + runtime suite (budgeting fixture
   repair where tests leaned on the sentinels).

**Unsplittable: none.** The former atomic swap is slices 4–6
(expand, cutover, contract), each independently gated.

**Persisted shape: no slice changes it.** Slice 7 adds a new key only;
`CANVAS_STORE_STORAGE_VERSION` is never bumped, `canvasPersistOptions.ts:migrate`
is never triggered, and the owner's canvases reset nowhere. The compat waiver
goes unspent.

**Disagreements resolved.** Dropped from mine: the `www/packages/space` browser
package (decision moves the invariant control-plane; a canvas module carries
the rest) and the Python meta-affinity slice (superseded by slice 2's
workdir-context read). Dropped from gpt's, carried from the cross-check with
the decision silent on them, so my rejection stands for the union: the
triple-everywhere launch cutover (contradicts `LAUNCH-CONTRACT.md` and
placement-by-adoption) and the Python→node Space-CRUD migration (a platform
rewrite this defect does not need). Adopted from gpt throughout: the node
verification home, canvas-adapter placement for fetchers, no-substitution,
semantic staleness, failed-selection atomicity, `ownerId`, the
`navigationSpaceId` split (rides slice 4).
