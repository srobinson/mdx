# Rehydrate identity fix — review (opus)

Branch `ml/s5-rehydrate` at `32129cdf`, three commits off `4e0f0e5d`, 10 files,
+361/-31. Read-only review. Context read first: `tm-rehydrate-identity-evidence.md`,
`tm-rehydrate-scout-fable.md`, `tm-rehydrate-scout-gpt.md`.

**Verdict: issues. 1 blocker, 3 majors, 8 minors.** The reported failure is genuinely
fixed for one worktree — the one the desktop backend was launched in. The same commit
makes the client's identity-precedence rule authoritative for the first time on the
desktop, and that rule discards a verified selection whenever it disagrees with meta.
So the slice trades "no worktree can launch after reload" for "only the backend's own
worktree can launch", on a branch whose purpose is multiple worktrees.

**Tree state at verdict time: NOT pristine.** `git status` shows ` M LESSONS.md` and
untracked `www/packages/canvas/src/workbench/ZzReviewProbe.test.tsx`. Neither is mine;
I wrote only this file. HEAD is `32129cdf` and every tracked file I read is at that SHA,
so the review is unaffected, but nobody should run a gate against this tree until those
are resolved.

---

## BLOCKER 1 — meta outranks the user's verified worktree, so every non-backend worktree loses its Canvas

`SessionCanvasRoute.tsx` (identity precedence, the line above `resolvedLaunch`):

```ts
const identity = isUsableIdentity(meta ?? null) ? (meta ?? null) : storeIdentity;
```

Meta wins unconditionally when complete. Before `068f989e` this branch was dead on the
desktop: `desktop_cmd.py:_DESKTOP_BACKEND_STALE_ENV_KEYS` strips `LAUNCH_FIELDS`, meta's
identity fields were always null, so `storeIdentity` always won. `068f989e` makes meta
resolve on every desktop, and meta is pinned to one thing: the backend process's cwd
worktree and its **root** Canvas.

Failure trace (all symbols, no line anchors):

1. User selects Worktree B in CMDK. `CanvasCommandDispatcher.ts:activateWorktree` writes
   `space_id/worktree_id/canvas_id` = B via `route.ts:worktreeSwitchUrl`, then
   `initializeVerifiedCanvas` → `canvasStoreLifecycle.ts:initializeCanvas` installs
   B's root Canvas. Correct so far.
2. That store write re-renders `SessionCanvasRoute` (it subscribes to `spaceId`,
   `defaultWorktreeId`, `canvasId`). `search` is re-read from `window.location` on every
   render, so `launch` is re-parsed as B — and unverified, because
   `parseCanvasLaunchContext` always stamps `canvasIdVerified: false`.
3. `identity` is meta = A (complete, therefore usable).
4. `route.ts:resolveCanvasLaunchIdentity` compares: `matchesWorktree` is false
   (`launch.worktreeId` B ≠ `identity.worktreeId` A) → returns the **unverified** launch.
   The whole tuple is discarded, not just the worktree.
5. `defaultCanvasId(unverified)` → null, so the new guard in the mount effect falls
   through to `initializeCanvas(resolvedLaunch)`, whose `canvasId === null` branch sets
   `canvasId: null` and `setActiveCanvasId(null)`.
6. Result: per-canvas persistence off (`canvasCacheStorage.ts` keys on the live
   canvasId), and the CMDK spawn posts a CANVAS launch with a null canvasId →
   `capture_rpc_routes.py:_resolved_domain_request` → `canvas_affinity_required`,
   *"Canvas launches require spaceId, worktreeId, and canvasId"*. The exact reported error.
7. It is sticky: the next recompute of `resolvedLaunch` has unchanged deps, so the effect
   does not re-run. Reloading does not help either — the URL still says B, meta still
   says A. `useMeta` uses `staleTime: Infinity` and nothing invalidates `["meta"]`, so
   meta never follows the selection.

Why it survived the gate: the guarantee is locked by
`SessionCanvasRoute.test.tsx:"keeps a verified worktree selection sticky for captured-run
spawns on a meta-less desktop"` — and its fixture is `metaResponse(workspaceId)` with **no
affinity**. That premise is precisely what `068f989e` deletes from production. Meanwhile
`SessionCanvasRoute.activity.test.tsx` already fixtures this exact configuration twice
("renders a preexisting MCP run from the new Worktree snapshot after a switch" and "uses
the switched Worktree while a captured launch remains unresolved": meta = WORKTREE_A,
`activateTestWorktree(WORKTREE_B)`). Both stay green because they assert panes and
streams, never `canvasId` and never launch capability. The configuration was already on
the shelf; only the assertion was missing.

**Empirically confirmed.** A separate agent (the owner's `/code-review`, run independently
of this review) drove the real route through an A/B probe, switching A → B via
`activateTestWorktree` under two meta shapes: with the pre-S5 meta shape (no affinity)
`canvasId` stays B's root Canvas; with the post-S5 meta shape (cwd tuple for `wt-a`) the
observed store is `{"canvasId": null, "defaultWorktreeId": "wt-b", "search":
"?space_id=space-1&worktree_id=wt-b&canvas_id=2222…"}` — store and URL divergent, exactly
the trace above. That probe file was written into the shared tree and has since been
removed by its author; I did not use it, and my trace was derived independently.

Fix direction: the file already owns the right rule one screen down —
`metaMatchesSelection` guards `workspaceIdentity` with "a selected Worktree's server
projection supersedes stale desktop meta; meta remains valid only for an unscoped launch
or an exact affinity match." Apply the same precedence to `identity`: a verified
`storeIdentity` that agrees with the current route wins over a contradicting meta; meta
supplies identity when the route/store is unscoped or matches. Lock it with a test that
sets meta = A, activates B, and asserts B's root canvasId survives *and* that a spawn
carries the complete triple (assert the capability, not the mapping).

## MAJOR 2 — the seam only ever answers with a root Canvas, so child Canvases stay broken

`resolve_existing_canvas_affinity` resolves `canvas_id=match.root_canvas_id` and nothing
else. Child Canvases are a real routed state: `launcher/commandRows.ts` emits
`select-canvas`, the dispatcher writes it through `route.ts:canvasSwitchUrl`, and
`SpaceCrudService.create_canvas` mints them.

Consequence on the same mismatch path as Blocker 1: reload while sitting on a child
Canvas → URL `canvas_id` = child, meta = root → `matchesCanvas` false → unverified →
`canvasId: null` → panes unreachable, launches rejected. Identical symptom to the bug
this slice fixes, one level down the Canvas tree, and untouched by the fix. Fixing
Blocker 1's precedence does not fix this one: the store is empty on reload, so meta is
the only source and it cannot speak about child Canvases.

Direction: have the read seam **verify the caller's canvas_id** when one is supplied
(the machinery is already there — `_resolve_canvas_launch` checks
`canvas.anchor_worktree_id` against the resolved worktree) and fall back to
`root_canvas_id` only when the caller has none. That needs a carrier for the client's
canvas_id into meta, or a thin `GET`-style verify adapter; the owner should pick the
shape. At minimum, state in the commit that child-Canvas reload is knowingly out of scope.

## MAJOR 3 — read-only is intentional and asserted, not structural (priority question 1)

Behaviourally the seam is clean. I traced every call transitively and confirm **no write
on any path**:

- `SpaceCrudService.list_worktrees_by_path` → `store_worktree_ops.list_worktrees_by_path`
  = one `SELECT` on `space_worktree` by `owner` + `canonical_os_path`, then `_project_one`.
- `_project_one` / `_detect_paths` → `_path_presence` + `detect_space` in threads:
  filesystem/git reads only.
- `resolve_launch_worktree` → `store.get_worktree` (`SELECT`) + projection. No lifecycle
  repair, no `missing`-flag writeback.
- `get_canvas` → `store.get_canvas` (`SELECT`) + `_require_owned_worktree` + `list_canvases`
  → `_require_space` → `_snapshot` → `get_space_inventory` (`SELECT`) + detection.
- No `resolve_cwd(create=True)`, no `_materialize_missing_worktree`, no
  `bootstrap_cli_space`. I verified the pre-#321 code did seed:
  `git show df052e65^:.../space/service.py` shows `resolve_session_cwd` calling
  `resolve_cwd(..., create=True)` with a `_materialize_missing_worktree` fallback. That
  is genuinely gone here.

What the seam does **not** have is a structural guarantee. It holds a full
`SpaceCrudService` — the same object exposes `create_space`, `create_workdir`,
`create_canvas`, `delete_space`, `delete_workdir`, `reconcile_detection` — on an ordinary
read-write pool connection. The only thing standing between the standing veto and a
future edit is a call-sequence assertion against a hand-written double in
`test_capture_rpc_worktree_resolution.py`, which constrains the *test's* Store, not the
real service. Answering the question asked: **intentional, plus a behavioural test. Not
structural.**

Two cheap ways to make it structural, either sufficient:

- Type the parameter as a read-only `Protocol` with exactly `list_worktrees_by_path`,
  `resolve_launch_worktree`, `get_canvas` (repo convention: "Shape-only contracts:
  Protocol"), so a mutation call fails mypy at the seam rather than at review time.
- Open that connection `READ ONLY` (`SET TRANSACTION READ ONLY`) so Postgres enforces the
  veto regardless of what anyone calls.

## MAJOR 4 — exact-path match, so a desktop launched from a subdirectory never resolves

`resolve_existing_canvas_affinity` matches `canonical_path(cwd)` verbatim against
`space_worktree.canonical_os_path`. What is stored there is not an arbitrary cwd: it is
the **containing worktree root**, because `worktree_mutations.create_workdir` runs
`detect_space(target)` → `containing_worktree(detection, target)` and persists
`detected.path`. The desktop's cwd gets no such normalisation —
`cli/desktop_launch_config.py:resolve_desktop_work_dir` is `Path.cwd().expanduser().resolve()`
with an existence check and nothing more, and `get_meta` uses `settings.cwd` directly.

So `cd ~/repo/api && transport-matters desktop` stores `TRANSPORT_MATTERS_CWD=~/repo/api`,
`list_worktrees_by_path` returns zero rows, and the entire slice silently no-ops back to
the reported bug. `cli/space_bootstrap.py:bootstrap_cli_space` already performs the
containing-worktree step before its own `list_worktrees_by_path` call, and both scouts
listed `space/detection.py:containing_worktree` in the reuse map as a required read-only
piece; it was dropped. Reuse it, or resolve the cwd to its worktree root before the lookup.
The reported capture happened to be launched from the worktree root, which is why the
evidence does not show this.

Credit: independently surfaced by the owner's `/code-review` run; I verified it against
`create_workdir`, `resolve_desktop_work_dir` and `bootstrap_cli_space` before recording it.

## Minors

1. **Silent swallow** (`launch_resolution.py:resolve_existing_canvas_affinity`).
   `except HTTPException, SpaceCrudError: return None` discards the reason. A 409
   `canvas_worktree_mismatch`, a 403 `space_mismatch`, a 404 `worktree_not_found` and
   "this cwd is simply not in any Space" become one indistinguishable `None`.
   `api/CLAUDE.md` says "Never swallow silently". Log the code at debug/warning.
2. **N:1 ambiguity is invisible** (priority question 4). Fail-closed: yes —
   `len(matches) != 1` returns `None`, and the test covers two matches in two Spaces
   (`resolved_worktree` mints a fresh `SpaceId` per call, so the fixture really is
   multi-Space). But the client behaviour on that failure is: meta returns nulls, identity
   falls back to a null store, and the user gets the original broken state with no log,
   no message, and no way to tell ambiguity from "never inventoried". Log the match count;
   consider a distinguishable signal so the UI can say "this path is in two Spaces, pick one".
3. **DRY: the completeness predicate is re-implemented.** The new mount effect open-codes
   `spaceId !== null && worktreeId !== null && canvasId !== null`, which is exactly what
   `route.ts:isUsableIdentity` owns (and which commit `963fd8f8` just tightened for this
   very reason). Express it once.
4. **Placement/naming of the shared primitive.** Both scouts asked for `activateWorktree`'s
   body to be *extracted* into one activation primitive; the commit instead exports the
   dispatcher's private function, so route mount now calls a symbol named and documented
   for a user-initiated switch. The codebase already has the precedent for the other half
   of this pair: `canvasStoreLifecycle.ts:selectSpace` lives in the model layer with a
   docstring explaining that the dispatcher is its only caller. A `canvasStoreLifecycle`
   sibling named for "install this verified worktree identity" would match it and keep the
   dispatcher's command vocabulary intact.
5. **Test-double type fidelity.** The fake `list_worktrees_by_path` is annotated and
   returns `tuple[ResolvedWorktree, ...]`; production returns `tuple[WorktreeRecord, ...]`.
   It passes only because both models happen to carry `space_id`, `worktree_id`,
   `root_canvas_id`. Since the double is monkeypatched onto the module, mypy cannot catch
   a drift here. Return `WorktreeRecord`.
6. **Fixture start state** (priority question 2). The new
   `SessionCanvasRoute.test.tsx:"activates a server identity when reload starts from a
   scoped unverified route"` boots from `?space_id=…&canvas_id=…` with **no**
   `worktree_id`, while the corrected evidence says the real reload carried a full
   unverified tuple. It does exercise the new branch — the `worktree_id`-appears-in-URL
   assertion can only be satisfied by `worktreeSwitchUrl`, and asserting
   `fitToContent: false` against `createInitialCanvasModel`'s default of `true` is a real
   proof that the cached blob was rehydrated (good instinct, credit given). But: because
   `launch.worktreeId === null`, the pre-existing `adoptDefaultWorktree` effect can satisfy
   the `defaultWorktreeId` assertion independently, and the cached blob has
   `contentRefs: {}`, so "the three CMDK panes come back" — half the user-visible failure —
   is never asserted. Add the full-tuple variant and put at least one `contentRef` in the blob.
7. **Per-request cost of the read seam.** Verifying a Canvas the caller already named goes
   through `get_canvas` → `list_canvases` → `_require_space` → `_snapshot`, which runs
   `detect_space` over **every** worktree in the Space (bounded at 8 concurrent), plus
   `_project_one` per path match. That is a git-subprocess fan-out on `/api/meta` for
   unstamped launches. Bounded by `staleTime: Infinity` to roughly once per page load, so
   not urgent — but `store.get_canvas` + the existing anchor check would give the same
   verification without the inventory sweep.
8. **Nit: the `migrate` comment.** `canvasPersistOptions.ts` grows a block body solely to
   host a comment. The hazard it documents (a version bump empties every saved Canvas) is
   real and worth writing down, but it belongs on `createCanvasPersistOptions`'s docstring
   where a caller contemplating a version bump will see it, not inside the callback.

## Verified non-issues (do not spend a round on these)

- `except HTTPException, SpaceCrudError:` **is valid**. PEP 758 (unparenthesized
  `except` tuples) landed in 3.14 and `api/pyproject.toml` sets
  `requires-python = ">=3.14"`. Compiled clean under `api/.venv/bin/python3.14` (3.14.5).
- Meta wire shape unchanged: `MetaResponse` and `core/transport.ts:Meta` already carried
  `space_id`/`worktree_id`/`canvas_id`; only their population changed.
- Explicit launch fields still win, and it is tested properly: the launch-affinity test
  now installs a resolver that raises `AssertionError` if it is ever consulted.
- No persisted shape or storage-version change; the fixture writes
  `CANVAS_STORE_STORAGE_VERSION`, so it is a real round-trip and not a fresh-write lie.
- `list_worktrees_by_path` cannot be polluted by soft-deleted rows:
  `delete_mutations.delete_workdir` is a hard delete.

## Priority questions, answered

**Q1 — read-only?** Yes in behaviour, verified transitively (Major 3). No, in structure:
a call-sequence test over a hand-written double, and a full mutation-capable service on a
read-write connection. Two one-line structural options above.

**Q2 — do the fixtures boot from the right state?** The Python fixtures do. The client
fixture does not boot from the reported state (Minor 6), and no fixture anywhere boots
from the state that breaks: a verified selection that disagrees with meta (Blocker 1).
The two fixtures that already hold that configuration assert around it.

**Q3 — does it fix the user-visible failure?** Yes, for the backend's own worktree and its
root Canvas. Path: `meta.py:get_meta` → (launch fields absent, desktop) →
`launch_resolution.py:resolve_existing_canvas_affinity` → `space/identity.py:canonical_path`
→ `SpaceCrudService.list_worktrees_by_path` (exactly one match) → `_resolve_canvas_launch`
→ `_resolve_launch_worktree` + `get_canvas` + anchor check →
`session/affinity.py:build_session_affinity_stamp` → `MetaResponse`. Client:
`SessionCanvasRoute` → `isUsableIdentity(meta)` → `resolveCanvasLaunchIdentity` (URL tuple
matches, `canvasIdVerified: true`) → `defaultCanvasId` → `activateWorktree` →
`initializeVerifiedCanvas` → `canvasStoreLifecycle.initializeCanvas` (switching branch,
cache blob restored, `persist.rehydrate()`) → panes return, store `canvasId` set → CMDK
spawn posts the triple → `_resolved_domain_request` accepts.
Worth noting for scope: commit `32129cdf` is not what makes the launch work — with a
verified `resolvedLaunch`, the previous `initializeCanvas(resolvedLaunch)` reached the
same restore-and-rehydrate branch. `32129cdf` buys the URL write and the shared primitive.

**Q4 — N:1 multi-Space.** Fail-closed, yes, and tested. Client-side it degrades silently
into the pre-fix broken state (Minor 2).

**Q5 — one command surface?** One *authority* seam, two composition paths. CMDK composes a
CANVAS launch in the browser from store + contentRef; MCP composes a SERVICE launch in
`controlplane_gateway_runs.create_run` from `ControlPlaneLauncher._prepare`'s frozen
principal. They converge on `_resolved_domain_request`, which is genuinely single-sourced
for validation, resolution and error codes — but it then *branches on launch kind*, and
the two kinds carry different affinity contracts (triple vs pair). So identical behaviour
is a property of the shared validator, not of the design: the browser adapter is required
to possess a triple it has no durable way to hold, which is the root cause this slice is
patching a source for. Unchanged by this diff, and not something I would ask this slice to
take on — but it should not be described as already satisfied.

**Q6 — missed by both scouts and the builder.** Blocker 1 and Major 2. Both were reachable
from the gpt scout's own observation that `isUsableIdentity` gates which source may verify
a launch; nobody asked what happens when two *usable* sources disagree.

## Trust verdict on the builder

**Craftsmanship: good.** The commits are cleanly separated by concern, the shared
`_resolve_canvas_launch` extraction removes real duplication rather than adding a
parallel path, and the seam is composed from the exact read-only pieces both scouts
mapped. The scout reports were clearly read, not skimmed: the seeding veto, the N:1
fail-closed rule, the `isUsableIdentity` latent defect and the `migrate`-wipes-everything
warning are each answered in the diff.

**Test rigour: above average, with one systematic hole.** Asserting `fitToContent: false`
against a default of `true` is a genuine rehydration proof rather than a proxy; writing
`CANVAS_STORE_STORAGE_VERSION` into the fixture blob makes it a real round-trip; making
the precedence test *fail if the resolver is consulted* is exactly the right shape. The
hole is that every new test asserts the mechanism the commit added, and none asserts the
capability the user lost. No test in this diff answers "can I launch?" — they answer "did
identity get installed on this path?". Blocker 1 lives in the gap between those two
questions, and so did the four prior rounds.

**Fidelity to spec and reuse map: high, with one substitution.** The endorsed fix was
followed nearly verbatim; the deviation is exporting `activateWorktree` where both scouts
asked for an extracted primitive (Minor 4). No new duplication, no invented abstraction,
no persistence surface touched, no seeding.

**Shortcuts: none found.** No plaster, no special-case, no disabled test, no widened type
to make something pass. The `except Exception` in `get_meta` is defensible (it must not
break boot) and it logs; the inner swallow does not (Minor 1).

**Where I would and would not delegate.** I would give this builder scoped work inside a
well-specified seam — the Python half of this slice is solid and I would take it as-is
modulo Major 3. I would not yet give it unsupervised ownership of cross-component state
precedence. Blocker 1 is not a coding error; it is the failure to ask "who wins now?"
after promoting one of two competing identity sources from always-null to always-present.
That question is the whole slice, it was one screen away from the code that was edited
(`metaMatchesSelection` states the correct rule in a comment), and two existing fixtures
already sat in the failing configuration. Pair this builder with an explicit
"enumerate the sources and their precedence after your change" step, or keep a reviewer
on any slice that changes who is authoritative for shared state.
