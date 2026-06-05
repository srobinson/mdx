# Rehydrate identity regression — scout report (fable)

Branch `ml/s4-adoption` at `4e0f0e5d`, tree pristine before and after this scout.
All citations are file + symbol. Evidence base: `~/.mdx/projects/tm-rehydrate-identity-evidence.md`.

## Root cause in one paragraph

PR #321 (`df052e65`) deleted the server's cwd→tuple resolution from
`api/src/transport_matters/api/v1/meta.py:get_meta` (the old
`_resolve_launch_worktree`, which read the DB by launch cwd) and replaced it with
`session/affinity.py:affinity_from_launch_fields` over `settings.launch_fields`.
Launch fields are stamped only by the CLI launch paths
(`cli/start_cmd.py` and `cli/codex_cmd.py`, both via
`cli/space_bootstrap.py:bootstrap_cli_space_or_exit`); the desktop backend
(`cli/desktop_cmd.py` / `desktop_runtime.py`) never stamps them, so the desktop's
`/api/meta` identity fields are permanently null. The client half of the slice
(`699fb578`, "sticky launch identity") papered over this with a memory-only store
fallback: `SessionCanvasRoute` treats a non-null store `canvasId` as the
last-verified tuple, but nothing persists `spaceId`/`canvasId`/`defaultWorktreeId`
(see Q5), so a reload starts from null. Post-reload the client therefore holds no
usable identity source, `canvasId` stays null, per-canvas persistence is disabled,
and a CMDK launch posts an incomplete tuple that
`api/v1/capture_rpc_routes.py:_resolved_domain_request` rejects with
`canvas_affinity_required` — the exact observed error. A worktree transition
recovers because the CMDK row injects a complete server-inventory triple through
`CanvasCommandDispatcher.ts:activateWorktree`; rehydrate has no equivalent source.

## Q1 — Who produces the launch triple, and where the paths diverge

**CMDK path (browser-composed).** The triple is assembled from client state:
`spaceId` and `canvasId` from the canvas store
(`www/packages/canvas/src/viewers/registry.tsx` captured-run registration passes
`props.canvas.spaceId` and `props.canvas.id`), `worktreeId` from the pane's
persisted `contentRef`. Flow:
`viewers/terminal/CapturedRunPane.tsx:CapturedRunPane` →
`infrastructure/runtime/useCapturedRunBinding.ts:useCapturedRunBinding` →
`model/capturedRunStore.ts:ensureRun` →
`www/packages/core/src/transport.ts:createCapturedRunView` → `POST /v1/runs`.
The request omits `launchKind`, and
`capture_rpc_routes.py:PrepareCaptureRequest.launch_kind` defaults to
`LaunchKind.CANVAS`, which makes the full triple mandatory.

**MCP path (server-composed).** The control-plane launch never consults the
browser: `controlplane/launch_service.py:ControlPlaneLaunchService` takes
`principal.space_id` / `principal.worktree_id` from the calling agent's
launch-stamped principal (guard at `_prepare`: rejects when either is null),
scopes the workdir via `controlplane/launch_policy.py:scoped_launch_workdir`, and
`api/v1/controlplane_gateway_runs.py:create_run` posts explicit `spaceId` /
`worktreeId` with `launchKind: "service"`. SERVICE launches skip the
canvas-triple gate entirely.

**Divergence point and authority.** Both paths converge on the same seam,
`capture_rpc_routes.py:_resolved_domain_request`, which re-resolves whatever was
sent through `api/v1/launch_resolution.py:resolve_run_canvas` /
`resolve_run_worktree` and overwrites the client's values. So the server
resolvers are the authority for *validity*. But *possession* of the triple
diverges upstream, at request composition: MCP identity is server-held state;
CMDK identity is rehydrated browser state, and since #321 no server surface
offers the browser a triple it can boot from. That asymmetry is the whole bug.

## Q2 — What a worktree transition runs that rehydrate does not

A transition runs `CanvasCommandDispatcher.ts:activateWorktree`: it writes the
row's triple into the URL (`route.ts:worktreeSwitchUrl`) and calls
`initializeVerifiedCanvas`, which feeds the CMDK row's **server-inventory
triple** (from `launcher/useSpaces.ts:useSpaces` → `spaceTransport.ts:fetchSpaces`,
carried on the row by `launcher/workdirRows.ts:worktreeRowActions` including
`worktree.rootCanvasId`) into `route.ts:resolveCanvasLaunchIdentity`. That
identity is usable, so `canvasStoreLifecycle.ts:initializeCanvas` receives a
verified durable `canvasId`, captures and restores the per-canvas cache blob, and
calls `persist.rehydrate()` — panes and launch identity both return.

Rehydrate (route mount) runs the *same* `initializeCanvas`, but its identity
input comes from `SessionCanvasRoute.tsx:SessionCanvasRoute`
(`identity = isUsableIdentity(meta) ? meta : storeIdentity`). Post-#321 desktop
meta is null and `storeIdentity` starts null, so `route.ts:defaultCanvasId`
gates `canvasId` to null and `initializeCanvas` takes its null-canvasId branch:
it patches `spaceId`/`defaultWorktreeId` from the (unverified) URL launch context
but never re-keys or rehydrates persistence. The code path is shared; the
verification *input* is what rehydrate lacks.

**The guard.** The only already-active early return in the dispatcher is
`CanvasCommandDispatcher.ts:activateSpace`
(`if (useCanvasStore.getState().spaceId === spaceId) return;`, added by
`9c9b06f8`). **`select-worktree` has no guard**: `launcher/commandRows.ts:interactionFor`
gives it the default run-and-close lifecycle and the dispatcher calls
`activateWorktree` unconditionally, so by static reading, pressing Enter on the
already-current *worktree* row should run the identical recovery as
switching away and back. The observed no-op is consistent with the re-select
having happened at the **Space** row (also badged Current; the store's `spaceId`
is patched from the unverified launch context, so the `activateSpace` guard
matches and returns early — same shape as the brief suspected, but living only
at Space level). I could not find any worktree-level guard; if the user
re-selected the worktree row itself, static reading cannot reproduce the no-op
and one targeted live check (Enter on the current worktree row post-reload) is
worth a minute before the fix is scoped.

**Inferred boot state (marked as inference).** The desktop window is created on
`desktop_event.py:build_backend_started_event`'s `routeUrl`
(`/canvas?owner=local&workspace_hash=…`), but `activateWorktree` had earlier
replaceStated the full triple into the address; an Electron menu reload reloads
the current URL, query included. URL retention is the only state consistent with
all three post-reload observations at once: the "Current" badge
(`defaultWorktreeId` patched from URL context), the server 400 rather than the
client-side `worktreeDefaults.ts:requireWorktreeId` throw (worktreeId present,
canvasId null), and the Space-guard no-op (spaceId patched, so the guard
matches). Note `parseCanvasLaunchContext` marks any URL tuple
`canvasIdVerified: false`, so the URL can seed the badge but can never re-enable
persistence or launches — it is a carrier, not a verifier.

## Q3 — Why MCP panes rehydrated and CMDK panes did not

Two independent restore paths exist, and post-reload only one operates:

1. **Per-canvas persistence** (`canvasStore`): the storage adapter
   `infrastructure/persistence/canvasCacheStorage.ts:createCanvasCacheStorage`
   keys every read by the live `canvasId` and returns `null` while it is null.
   With no verified `canvasId` at mount (Q2), the persisted `contentRefs` for
   all five panes are never read. This path is launch-path-agnostic — it would
   have restored all five.
2. **Adoption** (`model/capturedRunAdoption.ts`): the discriminator is
   `capturedRunAdoption.ts:candidateFromWire`, which returns null for any
   activity item whose `launch_kind !== "service"`. Only the two MCP-launched
   runs are SERVICE; the three CMDK runs are CANVAS and are invisible to the
   reconciler. `agentId` plays no role, matching the Claude-2 observation.

So the selective survival is exactly: persistence (the path that knows CMDK
panes) is disabled by the missing verified canvasId, and adoption (the only
path still running) is service-only by design.

## Q4 — Is #321's removal of `_resolve_launch_worktree` causal? — Yes, causal.

Committed answer: **genuinely part of the cause, not a red herring.** On main,
`get_meta`'s `_resolve_launch_worktree` (best-effort DB read of the launch cwd's
Space + primary worktree + root canvas) made meta the boot-time identity
authority; `SessionCanvasRoute` verified the reload against it and everything
downstream (persistence keying, launch triple) followed. #321 replaced that with
launch-field affinity that the desktop process never receives, and no substitute
boot-time source was added — `699fb578`'s sticky store identity is explicitly a
fallback for *re-renders*, not reloads, since it lives only in memory. The fact
that the client recovers once a transition fires does not exonerate #321: the
transition recovery uses a *manual* identity source (the CMDK row the user
clicked). Rehydrate has no automatic source at all, and #321 is the commit that
removed the last one. The DB row for the cwd exists (evidence: worktree
`747d7569…`), so the deleted read would still succeed today.

## Q5 — Is spaceId or canvasId persisted anywhere? — No.

Deciding symbols: `model/canvasStore.persistence.ts:createCanvasStorePersistOptions`
configures `infrastructure/persistence/canvasPersistOptions.ts:partializeCanvasState`,
whose persisted shape is exactly `contentRefs`, `paneRects`, `order`, `docked`,
`activeStrategyId`, `params`, `fitToContent`, `expandedPaneId`, plus the
`partializeExtras` field `paneCounters`. Neither `spaceId`, `canvasId`, nor
`defaultWorktreeId` is included. `canvasId` exists only inside the localStorage
*key* (`canvasCacheStorage.ts:canvasCacheKey`), which is why the user's capture
found the string "canvasId" zero times in values. The separate
`model/capturedRunStore.ts` partialize persists `runs`, `bypassPermissions`,
`controlPlaneGrant`; per-pane `worktreeId` rides in the canvasStore
`contentRefs` — the only identity field that survives, matching the capture.

## Reuse map

| Capability | Owner | Notes |
|---|---|---|
| Resolve identity from cwd (server) | `cli/space_bootstrap.py:bootstrap_cli_space` | Composite of read-only pieces below, **plus a create-fallback that seeds Space+Workdir — cannot be reused as-is on a read path (standing veto)** |
| … read-only pieces | `space/detection.py:detect_space`, `space/detection.py:containing_worktree`, `space/service.py:SpaceCrudService.list_worktrees_by_path` | Pure reads; the safe ingredients for a no-create cwd resolver |
| Resolve identity from cwd (client) | none found | Searches: `rg "cwd" www/packages/canvas/src`, `rg "resolveCwd\|resolve_cwd\|fromCwd" www/packages` — client never resolves from cwd |
| Verify a triple (server) | `api/v1/launch_resolution.py:resolve_run_canvas`, `resolve_run_worktree` | Read-only; checks ownership, active/present lifecycle, canvas↔worktree anchoring |
| Verify a triple (client) | `route.ts:resolveCanvasLaunchIdentity`, `route.ts:isUsableIdentity` | The single client verification seam; both mount and transition already go through it |
| Hydrate a worktree (client) | `CanvasCommandDispatcher.ts:activateWorktree` → `canvasStoreLifecycle.ts:initializeCanvas` | URL write + verified init + cache restore + `persist.rehydrate()` |
| Worktree inventory fetch | `launcher/useSpaces.ts:useSpaces` → `www/packages/core/src/spaceTransport.ts:fetchSpaces` | `GET /v1/spaces`; `SessionCanvasRoute` already fetches it post-reload (`needsWorktreeInventory`) and resolves `activeWorktree` |
| Invalidate inventory | `workbench/spaceCommandDispatcher.ts:refreshSpaces` (and `freshInventory`) | Query-client refresh keyed by `useSpaces.ts:SPACES_QUERY_KEY` |
| Affinity stamp encode/decode | `session/affinity.py:build_session_affinity_stamp`, `affinity_from_launch_fields` | The launch-fields carrier meta now depends on |

## Proposed fix direction (not implemented)

**Primary (server): restore a read-only boot identity source for the desktop.**
Reinstate cwd→tuple resolution for meta, built from the read-only pieces
(`detect_space` + `containing_worktree` + `list_worktrees_by_path` +
`SpaceCrudService.resolve_launch_worktree` + `get_canvas`), returning nulls when
no row exists — never creating one (`bootstrap_cli_space`'s create-fallback is
explicitly excluded; seeding veto). Shape choice for the owner: stamp
launch_fields at desktop backend start (mirrors `start_cmd`) or resolve
per-request inside `get_meta` like the deleted #321 code. Either way meta again
answers "what is this desktop's tuple" and the existing client seam
(`SessionCanvasRoute` → `resolveCanvasLaunchIdentity` → `initializeCanvas`)
recovers with zero client changes. This is a restoration of main's behavior with
#321's ownership semantics kept for actual launches.

**Complement (client, optional): verify the URL tuple against inventory at
mount.** When `resolvedLaunch` carries an unverified triple, `SessionCanvasRoute`
already fetches spaces and resolves `activeWorktree`; feeding that
inventory-confirmed tuple into the existing `resolveCanvasLaunchIdentity` seam
makes mount recovery identical to the manual transition (same identity source,
same verification), removing the dependency on meta for the reload case. Pure
reads; no persistence or migrate changes.

Both respect the hard constraints: no seeding; no second command surface (CMDK
and MCP still converge on `_resolved_domain_request`, and identity acquisition
stays server-resolved); persist/partialize untouched, so no data-loss risk.
The whack-a-mole alternative — persisting `spaceId`/`canvasId` client-side —
is explicitly *not* proposed: it duplicates server-owned identity into a second
writer with no precedence rule and touches the persistence surface for no
structural gain.

## Cross-check (after reading ~/.mdx/projects/tm-rehydrate-scout-gpt.md)

**Corrections to this report (gpt was right, I was wrong).**
1. The deleted meta resolver was NOT read-only. Verified against
   `git show df052e65^:api/src/transport_matters/space/service.py`:
   `SpaceCrudService.resolve_session_cwd` called `resolve_cwd(..., create=True)`
   and fell back to `_materialize_missing_worktree` — pre-#321 meta could seed
   inventory on a read. My Q4 phrasing "best-effort DB read" understated this.
   The causal verdict stands (the removal still deleted the only boot-time
   identity source without a replacement), but "reinstate the deleted code" is
   off the table verbatim; only a from-parts read-only rebuild satisfies the
   seeding veto. This strengthens, not weakens, the fix direction above.
2. Class name: the MCP launch owner is
   `controlplane/launch_service.py:ControlPlaneLauncher`, not
   `ControlPlaneLaunchService` as written earlier in this report.

**Conflict I maintain against the gpt report.**
Their Q2 states "route identity, meta identity, and store identity — all three
are empty in the observed reload," and their regression fixture prescribes an
"unscoped URL." The route source cannot have been empty: the post-reload
"Current" badge requires a non-null `defaultWorktreeId`
(`launcher/CommandCenter.tsx` reads `state.defaultWorktreeId`, whose only
writers are the URL launch context via
`canvasStoreLifecycle.ts:initializeCanvas` / `canvasState.ts:createInitialCanvasModel`
and the null desktop meta via `adoptDefaultWorktree`), and the observed server
400 rather than the client-side `worktreeDefaults.ts:requireWorktreeId` throw
requires a non-null `worktreeId` at spawn. Deduction: the reload preserved the
replaceStated `space_id`/`worktree_id` (and likely `canvas_id`) as an
*unverified* URL tuple. Consequently their claim that `needsWorktreeInventory`
"requires Space and Worktree IDs that are already missing" is also wrong — the
unverified URL ids pass through `resolveCanvasLaunchIdentity` and the inventory
fallback DOES fire; it just feeds nothing back into identity verification. Any
regression fixture must cover the scoped-but-unverified URL state, not (only)
the unscoped one, or it will pass while the product stays broken.

**Gaps their report found that mine missed.**
`space/identity.py:canonical_path` as the canonicalization owner; the N:1
ambiguity rule (one canonical path matchable in multiple Spaces → a cwd
resolver must fail closed, as `bootstrap_cli_space` already does); and the
explicit warning that `canvasPersistOptions.ts:createCanvasPersistOptions`'s
`migrate` returns an EMPTY state, so any storage version bump wipes every
saved canvas.

**Endorsed fix after both reports (convergent).** One read-only server seam,
composed from `canonical_path` + `SpaceCrudService.list_worktrees_by_path`
(fail closed on multi-Space matches) + `SpaceCrudService.resolve_launch_worktree`
+ `get_canvas`, verified by the same rules as
`launch_resolution.py:resolve_run_canvas`, surfaced to the desktop boot path
(meta or a thin read adapter) and consumed by `SessionCanvasRoute` only when
route/meta/store lack a usable tuple; extract
`CanvasCommandDispatcher.ts:activateWorktree`'s body into one shared activation
primitive so CMDK selection and reload recovery are the same operation. No
seeding; launch execution stays converged on
`capture_rpc_routes.py:_resolved_domain_request`. Constraints: both hold; no
material cost.
