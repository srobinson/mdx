# TM reload→launch regression: canvas_affinity_required after refresh

Scout: fable5 (`multi-launch:general:1:3.2`), topic `ml-reload-launch-regression`.
Tree examined: ml/s4-adoption at 350ce173 (pristine, no writes). Known-good baseline: origin/main 7ffba78b (owner-verified live).

## Verdict

**First bad sha: df052e65 (`feat(space): S3-schema — N:1 workdir ownership + launch-affinity authority (#321)`).**
Server-side. Pre-dates PR #323 and every client slice on this branch. The client slices neither caused nor fixed it.

**Missing field at POST /v1/runs: `canvas_id`** (spaceId and worktreeId survive via URL adoption; canvasId is gated on verification and verification has no source after a reload).

## 1. Mechanism

The failing path, symbol by symbol, at 350ce173:

1. After a desktop refresh the URL still carries the triple (`?space_id&worktree_id&canvas_id` written by `route.ts:worktreeSwitchUrl` via replaceState), but `route.ts:parseCanvasLaunchContext` always yields `canvasIdVerified: false`. Verification requires an identity source.
2. The two identity sources in `SessionCanvasRoute.tsx` are dead after a reload:
   - **meta**: `api/v1/meta.py:get_meta` since df052e65 returns `affinity_from_launch_fields(settings.launch_fields)`. The desktop backend strips `LAUNCH_FIELDS` from its env (`cli/desktop_cmd.py:_DESKTOP_BACKEND_STALE_ENV_KEYS`), so `session/affinity.py:affinity_from_launch_fields` returns None and meta's `space_id`/`worktree_id`/`canvas_id` are all null → `route.ts:isUsableIdentity` false.
   - **storeIdentity**: the zustand store is fresh on reload. Persistence cannot help: the per-canvas cache key needs `canvasStoreLifecycle.ts:resolveLaunchCanvasId` → `route.ts:defaultCanvasId`, which returns null for an unverified launch, so rehydration is disabled (circular by design; the store was never the verifier).
3. `route.ts:resolveCanvasLaunchIdentity(launch, null)` → unverified → `canvasStoreLifecycle.ts:initializeCanvas` takes the `canvasId === null` branch: store `spaceId`/`defaultWorktreeId` adopt the URL values, store `canvasId` stays **null**.
4. Spawning an agent: `registry.tsx` passes `props.canvas.id` (store canvasId, null) → `CapturedRunPane` → `useCapturedRunBinding` → `capturedRunStore.ensureRun` → `transport.ts:createCapturedRunView` posts `canvasId: null`.
5. Backend: `captured_run_models.py:CapturedRunRequest.launch_kind` defaults to `LaunchKind.CANVAS`; `capture_rpc_routes.py:_resolved_domain_request` rejects a CANVAS launch missing any of the three → 400 `canvas_affinity_required` "Canvas launches require spaceId, worktreeId, and canvasId" → surfaced verbatim by `useCapturedRunBinding.ts:spawnErrorMessage`.

## 2. When it broke (A/B)

The break is server-side in `/api/meta`, so the client sha is irrelevant; what matters is whether the backend build includes df052e65.

- **origin/main 7ffba78b — GOOD.** `get_meta` calls `_resolve_launch_worktree(request, cwd)` → `SpaceCrudService.resolve_session_cwd` → populated `(space_id, worktree_id, canvas_id)` for the launch cwd. After reload, `resolveCanvasLaunchIdentity(launch, meta)` verifies the URL triple → store canvasId set → spawn carries the triple. Owner-verified live; also corroborated on this Mac: a still-running pre-#321 desktop backend on 127.0.0.1:8788 returns `"space_id":"ac158c65-…","worktree_id":"eeffd838-…"` populated for a bare desktop launch.
- **57d1f087 — GOOD** (precedes the meta change; `_resolve_launch_worktree` still present).
- **df052e65 (#321) — FIRST BAD.** Deletes `_resolve_launch_worktree` and the session-store fallback; meta identity now comes only from launch fields the desktop never has.
- **97a80f56 (#322), 9c9b06f8 (PR #323 tip), 991b698c, 350ce173 — all BAD** for the same reason; none of them touch `get_meta`'s identity sourcing.

Note on prior evidence: the earlier warroom A/B tested pane restoration (which works everywhere — pane records persist and re-attach by runId without needing a verified canvas) and the unit suites pass at every sha because `test_meta.py` was rewritten by #321 to assert the new affinity-only behaviour. Only launch-after-reload against a live backend exposes it.

## 3. Caused vs exposed

**#321 caused it.** Verification-gating on the client (`defaultCanvasId` on `canvasIdVerified`, PR #316) and the backend triple requirement (`canvas_affinity_required`, PR #319) are both on main and are satisfied there because meta supplied the tuple. #321 removed the supply without replacing it for the desktop launch.

The branch client slices interact but are not causal:
- 699fb578 added the storeIdentity fallback, which fixes in-session demotion but deliberately cannot survive a reload (fresh store). The reload gap was flagged during that build as out-of-scope pending a backend verification read; #321 is precisely the removal of that read.
- The S4 adoption slice's `metaMatchesSelection` logic remains coherent if meta is restored: explicit selection still outranks cwd-resolved meta, and an unscoped desktop falls back to meta exactly as its tests assume.

## 4. Smallest correct fix (recommendation, not implemented)

Reinstate the cwd resolution in `api/v1/meta.py:get_meta` as a **fallback**, preserving #321's authority model:

- `affinity = affinity_from_launch_fields(settings.launch_fields)`; if None, fall back to the deleted `_resolve_launch_worktree(request, str(cwd))` (best-effort, session-store, returns `(None, None, None)` in degraded/no-DB mode). Explicit launch fields keep priority, so managed-child launches are unchanged; only the desktop (no launch fields) regains its identity tuple.
- Restore/adapt the #321-deleted `test_meta.py` coverage for the fallback leg, plus one test asserting launch-fields-present still wins.
- No client change needed; `isUsableIdentity`/`resolveCanvasLaunchIdentity` verify the reload triple again as on main.

Alternative considered and rejected as larger: a client-side verification read (e.g. resolve the URL triple against `/v1/spaces` inventory on mount). It duplicates identity authority in the client and leaves a fetch-race window; the meta fallback is one function in the server that already owned this.

## 5. The cross-repo "Current" worktree badge

Not a separate defect on current evidence. Two by-design facts compose into the confusing display: Spaces are owner-scoped and workdir-agnostic (a Space legally holds worktrees across repos, so `review/pingdotgg-main` from /t3code appearing in the palette is correct), and the "Current" badge (`workdirRows.ts:buildWorktreeRows` trailing) reflects store `defaultWorktreeId`, which after a reload is adopted from the URL's `worktree_id` — the last explicitly switched worktree. With verification broken, the canvas content fails to rekey to that worktree while the badge still names it, so the palette and canvas appear to disagree. Restoring meta (fix above) removes the mismatch. Worth one re-check after the fix; if the badge still names a foreign-repo worktree the owner never selected, that would be a real defect (likely in URL adoption), and should be re-scouted then.
