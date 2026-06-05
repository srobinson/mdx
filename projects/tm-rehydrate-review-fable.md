# Review — ml/s5-rehydrate @ 32129cdf (fable)

Scope: 963fd8f8, 068f989e, 32129cdf off `4e0f0e5d`; 10 files, +361/−31. Tree
pristine before and after review (`git status` clean, HEAD 32129cdf). All
severities per brief: blocker / major / minor. Verdict: **issues — 1 blocker,
2 majors, 3 minors.**

## Verdict summary

The headline defect is genuinely fixed for the observed scenario, by the right
seam, with the right fixture state. But the server change flips an existing
client precedence rule (meta over store) whose semantics silently changed:
desktop meta used to be never-usable, now it is always-usable and permanently
stale, and it now overrides the user's live verified selection. Result: the fix
re-introduces the exact user-visible failure (launch 400 + persistence off) on
every worktree other than the backend's launch cwd — including the
switch-away-and-back flow the evidence used as recovery.

## Q1 — Read-only by construction, or by intention? **By intention. (major)**

What the seam actually touches, verified by reading the real
implementations: `space/identity.py:canonical_path` (pure,
`Path.resolve(strict=False)`), `SpaceCrudService.list_worktrees_by_path`,
`SpaceCrudService.resolve_launch_worktree`, `SpaceCrudService.get_canvas` —
all reads; the projection path (`_project_one` → `_detect_paths` →
`detect_space`) shells out to read-only git commands and never calls the
writing paths (`reconcile_detection`, `reconcile_worktrees`,
`_store.upsert_*` are not reachable from these entry points). The pre-#321
seeding shapes (`resolve_cwd(create=True)`, `_materialize_missing_worktree`)
are gone from the tree and nothing equivalent is called. So today, the seam is
read-only.

But the guarantee is convention plus a boundary-mocked test:
`test_existing_canvas_affinity_resolves_with_read_only_service_calls`
monkeypatches `SpaceCrudService` to a fake `Store`
(`test_capture_rpc_worktree_resolution.py:_install_space_store`,
`monkeypatch.setattr(launch_resolution, "SpaceCrudService", Store)`), so the
call-sequence assertion pins which service methods the seam invokes and
nothing about what the real service does transitively. Any future edit to
`resolve_launch_worktree` or `get_canvas` that adds an upsert passes this test
unchanged. The structural option exists and is cheap: open the seam's
connection/transaction read-only (psycopg `Connection.read_only` /
`SET TRANSACTION READ ONLY`), so Postgres itself rejects any write on this
path. Given the standing veto, the veto should be enforced by the database,
not by reviewer inspection. Filed as major M1.

## Q2 — Do the fixtures boot from the right state? **Yes for the headline test.**

`SessionCanvasRoute.test.tsx` "activates a server identity when reload starts
from a scoped unverified route" boots from
`/canvas?space_id=…&canvas_id=…` (scoped tuple, null `worktree_id`,
`canvasIdVerified` false by `parseCanvasLaunchContext`), a pre-seeded
per-canvas cache blob, and a usable meta. It asserts the observable end state
(store tuple set, `fitToContent:false` restored from cache, `worktree_id`
written back into the URL) — the correct fixture class and the correct
assertion altitude. `route.test.ts` covers the `isUsableIdentity` null-worktree
rejection; `test_meta.py` covers fallback-used, fallback-fails-open-to-null,
and explicit-launch-fields-win (with a poisoned stub that raises if the
fallback is consulted — good).

What no fixture covers is the state the blocker lives in: **usable meta plus a
user selection that differs from meta.** The pre-existing writer-B switch test
(line ~340) still models the desktop as meta-without-affinity ("Desktop
backend: workspace only, no launch-field affinity") — a contract this very
slice retired. The suite now systematically models a desktop that no longer
exists. Filed under B1/m2.

## Q3 — Does it fix the user-visible failure? **Yes, for the cwd worktree; it breaks the neighbor flow.**

Fixed path, traced: reload with scoped-but-unverified URL →
`meta.py:get_meta` (launch_fields empty) →
`launch_resolution.py:resolve_existing_canvas_affinity` → meta returns the cwd
tuple → `SessionCanvasRoute` `identity = meta` →
`route.ts:resolveCanvasLaunchIdentity` matches URL tuple → verified → new mount
effect calls `CanvasCommandDispatcher.ts:activateWorktree` →
`route.ts:worktreeSwitchUrl` + `canvasStoreLifecycle.ts:initializeCanvas`
(verified id, switching branch) → cache restore + `persist.rehydrate()` → panes
return; CMDK spawn now posts the full triple
(`viewers/registry.tsx` → `useCapturedRunBinding` → `capturedRunStore.ensureRun`
→ `transport.ts:createCapturedRunView`) → `_resolved_domain_request` →
`resolve_run_canvas` → 200. The loop settles: after `activateWorktree` the URL
stabilizes and the effect's second run takes the same-canvas branch.

**B1 (blocker) — stale meta now overrides the user's verified selection and
re-creates the launch failure on every non-cwd worktree.**
`SessionCanvasRoute.tsx` line unchanged by this diff:
`identity = isUsableIdentity(meta ?? null) ? (meta ?? null) : storeIdentity`.
That precedence was written (699fb578) when desktop meta was never usable;
this slice makes desktop meta always usable, cached for the page lifetime
(`useMeta` staleTime Infinity), and frozen to the backend process cwd's root
tuple. Sequence: user CMDK-switches to worktree B (e.g. the cubicell worktree
from the evidence session) → dispatcher `activateWorktree(B)` verifies B and
restores its cache → re-render → `launch` = B tuple from URL, `identity` = meta
= A tuple (meta wins) → `resolveCanvasLaunchIdentity` mismatches
(`matchesWorktree` false) → unverified → the mount effect's verified branch is
skipped and it falls through to `initializeCanvas(unverified)` → the
null-canvasId branch sets `canvasId: null` and `activeCanvasId = null`
(`canvasStoreLifecycle.ts:initializeCanvas`) — demoting the selection the
dispatcher verified milliseconds earlier. Consequences on worktree B: CMDK
launch 400 "Canvas launches require spaceId, worktreeId, and canvasId" (store
canvasId null in `registry.tsx`), and layout persistence disabled
(`canvasCacheStorage` no-ops on null id). Pre-fix, the same flow worked:
meta was unusable, so `storeIdentity` (the just-verified B tuple) won and the
effect took the harmless same-canvas branch. This is a second writer to owned
identity with an inverted precedence rule — the server commit changed the
meaning of the client's `identity` line without touching it, which is why no
diff-local reading catches it and no test fails.
Minimal correction: make meta a boot-time fallback rather than an override —
consult meta only when `storeIdentity` is null (e.g.
`identity = storeIdentity ?? (isUsableIdentity(meta) ? meta : null)` in
`SessionCanvasRoute.tsx`), which preserves the reload fix (store empty at boot
→ meta wins) and restores sticky user precedence afterward; plus one
switch-under-usable-meta test asserting spawn identity and persistence survive
a B-switch. The deeper invariant worth a guard: an unverified launch must
never null a verified store canvasId (`initializeCanvas` demotion path).

## Q4 — N:1 multi-Space. **Fail-closed, server side; client degrades honestly.**

`resolve_existing_canvas_affinity`: `len(matches) != 1 → None`, and
`test_existing_canvas_affinity_fails_closed_for_multiple_spaces` asserts both
the None and that resolution stops after `list_worktrees_by_path` (two
worktrees on one canonical path). Client consequence of None: meta identity
null → post-reload boot stays unverified (pre-fix behavior, honest
degradation); the user can still select an explicit worktree via CMDK, which
does not traverse the seam. No crash path found. Adequate.

## Q5 — One command surface. **One launch seam; identity acquisition remains two paths, per the approved design.**

Launch execution is genuinely one seam: CMDK (`createCapturedRunView`,
launchKind defaulting to CANVAS) and MCP
(`controlplane_gateway_runs.py:create_run`, `launchKind: "service"`) both
terminate in `capture_rpc_routes.py:_resolved_domain_request` →
`launch_resolution.py` resolvers; this slice did not add a launch path and the
new `_resolve_canvas_launch` extraction means `resolve_run_canvas` and the
meta seam share one canvas-verification body — a reuse-map-faithful move.
Identity *acquisition* is still two paths (browser tuple vs principal tuple),
which is the approved direction, but note B1 shows the acquisition side is
where identical-behaviour-by-design still does not hold.

## Q6 — What everyone missed

- **M2 (major): non-root canvas reload remains broken — same defect class,
  adjacent state.** The seam only ever offers the worktree's
  `root_canvas_id` (`resolve_existing_canvas_affinity` uses
  `match.root_canvas_id`), so a reload on a secondary canvas (creatable today
  via MCP `canvas_create`; `select-canvas` and `canvasSwitchUrl` support it)
  has `launch.canvasId = C2` vs meta's root canvas → `matchesCanvas` false →
  unverified → identical launch-400/persistence-off state this slice set out
  to kill. Not a regression (equally broken pre-fix), but "identity present
  and never verified" survives in a supported flow, and the corrected evidence
  note's warning applies: a root-canvas-only fixture passes while this state
  stays broken.
- **m1 (minor): the seam degrades silently.** `resolve_existing_canvas_affinity`
  returns None on any `HTTPException`/`SpaceCrudError` with no log; a
  `worktree_unavailable` 409 — including the known `missing is not False`
  false-positive on a transient git timeout (`resolve_run_worktree`) — makes
  the desktop boot exactly like the original bug with zero diagnostics.
  `transport-matters doctor` and log-readers deserve one warning/info line
  naming the error code before the None.
- **m2 (minor): test-suite desktop model drift.** The writer-B switch test's
  comment and every `metaResponse(workspaceId)` (null affinity) now describe a
  desktop contract this slice retired; the suite should model usable meta as
  the desktop default or it will keep passing flows the product fails (this is
  the mechanism that hid B1).
- **m3 (minor): meta hot path now pays the snapshot git fan-out.**
  `get_canvas` → `list_canvases` → `_require_space` → `_snapshot` →
  `_detect_paths` runs git detection per stored worktree on every desktop page
  load's `/api/meta` (bounded by `MAX_PROJECTION_CONCURRENCY`, 2s timeout per
  probe). Amplifies the pre-existing efficiency finding on `space/service.py`;
  worth noting in whichever slice picks that finding up.

Verified along the way: `except HTTPException, SpaceCrudError:` is valid
PEP 758 on this repo (`requires-python >=3.14`; compiled clean under
`api/.venv`). The `createCanvasPersistOptions.migrate` change is comment-only;
no persisted shape or version changed. Meta wire shape unchanged
(`fetchMeta` consumers unaffected). `activateWorktree` export adds a second
caller, not a second writer — both callers funnel through the one
URL-plus-store body.

## Builder quality and trust verdict

Candid: this is the strongest slice this builder has produced at the seam
level, and it still shows the known boundary blind spot at the system level.

Strengths, specific: the fixture state for the headline test is exactly the
class four prior rounds missed, asserted at observable end-state altitude
(store tuple + persisted `fitToContent` + URL write-back); `_resolve_canvas_launch`
is a genuine reuse extraction, not a copy — `resolve_run_canvas` and the new
seam share one verification body; the launch-fields-win test poisons the
fallback so precedence is proven, not assumed; N:1 fails closed with a test
asserting where resolution stops; PEP 758 used correctly for the repo's
interpreter; commits are cleanly split by concern and each claimed test
maps to a real assertion.

Weaknesses, specific: the builder's own claim sheet says "explicit
launch_fields still win" and "resolveCanvasLaunchIdentity remains the trust
gate" — both literally true, while the change inverted the *effective*
precedence between meta and the user's verified store selection (B1). That is
a cross-component consequence of a server-side change, invisible in any single
file, and it is precisely the seam-versus-file blind spot flagged in this
warroom's builder profile. Second, "read-only, with a regression test
asserting the exact call sequence" oversells a test that mocks out the entire
service; the structural enforcement (read-only transaction) was available and
not taken. Third, the builder worked around, rather than updated, a test suite
whose desktop model its own change retired.

Trust calibration: delegate seam-scoped slices with confidence — the
craftsmanship, test rigour, and reuse fidelity are real. For slices whose
change alters the *meaning* of state another component already consumes
(precedence, caching, identity), keep a mandatory cross-component consequence
pass in the brief (the GENERALIST LENS block earned its place here) and an
independent reviewer on the consuming side. Not yet unsupervised on
contract-touching work.
