# Bug archaeology: desktop seed + sticky-identity collision

Date: 2026-07-25  
Mode: **git archaeology only** (`log` / `show` / `diff` / `blame` / merge-base)  
Tree: transport-matters `.claude/worktrees/multi-launch` (not modified)  
Prior authority: `~/.mdx/projects/tm-cmdk-launch-scout.md` §7 (not re-derived)

SHAs of interest:

| SHA | Role |
|-----|------|
| `7ffba78b` | origin/main (S1+S2) |
| `57d1f087` | STEP-0 store split |
| `df052e65` | PR1 #321 S3-schema |
| `97a80f56` | PR2 #322 S3-delete (feat/multi-launch tip) |
| `0c76d520` | PR3 CMDK (unmerged) |
| `6453364a` | #316 Canvas/Worktree CRUD foundation (pre-S3, on main) |
| `8b236be7` | #39 Session canvas F1 (pre-S3) |
| `0c6b0e58` | #182 desktop meta worktree seed (pre-S3) |

---

## Q1. Desktop cwd seed — PR1 added, removed, or untouched?

### Verdict: **REMOVED by PR1** (`df052e65`, PR #321)

PR1 did **not** add startup seeding. It **deleted** lifespan cwd seed and **replaced** meta’s live DB resolution with launch_fields affinity only.

### Evidence A — lifespan seed removed in `df052e65`

```diff
# df052e65 — api/src/transport_matters/main.py
-async def _resolve_current_space(
-    pool: AsyncConnectionPool[AsyncConnection[DictRow]], settings: Settings
-) -> None:
-    cwd = settings.cwd or Path.cwd()
-    try:
-        async with pool.connection() as conn:
-            await SpaceCrudService(conn).resolve_cwd(cwd, owner="local", create=True)
-    except Exception:
-        logger.exception("Failed to resolve current Space for %s", cwd)
-
-    await _resolve_current_space(session_pool, settings)
-    await _backfill_session_spaces(session_pool)
```

Parent still had seed at `7ffba78b` / pre-PR1:

```python
# 7ffba78b main.py
async def _resolve_current_space(...):
    ...
    await SpaceCrudService(conn).resolve_cwd(cwd, owner="local", create=True)
...
await _resolve_current_space(session_pool, settings)
```

`SpaceCrudService.resolve_cwd(..., create=True)` itself is gone after PR1’s service rewrite (`git log -S'resolve_cwd' -- space/service.py` ends at `df052e65`).

### Evidence B — meta no longer resolves cwd inventory (same PR)

```diff
# df052e65 — api/src/transport_matters/api/v1/meta.py
-    space_id, worktree_id, canvas_id = await _resolve_launch_worktree(request, str(cwd))
+    affinity = affinity_from_launch_fields(settings.launch_fields)
     return _build_meta_response(
         ...
-        space_id=space_id,
-        worktree_id=worktree_id,
-        canvas_id=canvas_id,
+        space_id=None if affinity is None else str(affinity.space_id),
+        worktree_id=None if affinity is None else str(affinity.worktree_id),
+        canvas_id=None if affinity is None else str(affinity.canvas_id),
     )
-async def _resolve_launch_worktree(...):
-    ...
-    resolved = await SpaceCrudService(conn).resolve_session_cwd(cwd, owner="local")
-    return (str(resolved.space_id), str(resolved.worktree_id), str(resolved.root_canvas_id))
```

Pre-PR1 meta path (from #182 `0c6b0e58`, still on main `7ffba78b`) resolved **primary worktree + root canvas** from session-store cwd.

### Current behavior on `feat/multi-launch` @ `97a80f56`

**No.** A fresh desktop start with empty DB does **not** create a Space+Worktree from process cwd.

- No `_resolve_current_space` / `resolve_cwd` / lifespan seed in `main.py` at `97a80f56` (confirmed absent).
- Desktop backend clears `LAUNCH_FIELDS` (`cli/desktop_cmd.DESKTOP_BACKEND_STALE_ENV_KEYS`); meta affinity is therefore **null**.
- Inventory only appears via explicit create (CLI `space_bootstrap`, REST/MCP, or later CMDK).

Removing SHA: **`df052e65` (PR #321)** — not STEP-0 (`57d1f087`), not S3-delete (`97a80f56`).

---

## Q2. When was the sticky-identity bug introduced?

Two writers (scout §7):

| Writer | Role |
|--------|------|
| **A** | `SessionCanvasRoute`: non-reactive `search` snapshot → `resolveCanvasLaunchIdentity(launch, meta)` → `useEffect(() => initializeCanvas(resolvedLaunch))` |
| **B** | `activateWorktree` / `select-worktree`: `history.replaceState` + live parse of URL → verified canvas init |

### Writer A — non-reactive search + re-init

**Introduced (base hazard):** `8b236be7` (#39)

```tsx
// new SessionCanvasRoute.tsx
const search = typeof window === "undefined" ? "" : window.location.search;
const launch = useMemo(() => parseCanvasLaunchContext(search), [search]);
useEffect(() => {
  initializeCanvas(launch);
}, [initializeCanvas, launch]);
```

`search` is captured once per mount; `replaceState` does not update the memo.

**Modern demotion rules (verified flag + meta merge):** `6453364a` (#316)

```diff
+  const resolvedLaunch = useMemo(
+    () => resolveCanvasLaunchIdentity(launch, meta ?? null),
+    [launch, meta],
+  );
   useEffect(() => {
-    initializeCanvas(launch);
-  }, [initializeCanvas, launch]);
+    initializeCanvas(resolvedLaunch);
+  }, [initializeCanvas, resolvedLaunch]);
```

And in `route.ts` (same commit):

```diff
+export function resolveCanvasLaunchIdentity(launch, identity) {
+  const unverified = { ...launch, canvasIdVerified: false };
+  if (identity === null || identity.spaceId === null || !isDurableCanvasId(identity.canvasId)) {
+    return unverified;
+  }
+  const matchesSpace = launch.spaceId === null || launch.spaceId === identity.spaceId;
+  // null launch fields are wildcards (scout §7 step 5)
+  ...
+}
+export function defaultCanvasId(launch) {
+  return launch.canvasIdVerified === true && isDurableCanvasId(launch.canvasId)
+    ? launch.canvasId
+    : null;
+}
```

When `meta` loads/refetches, `resolvedLaunch` recomputes from **stale empty URL launch + meta** and re-runs `initializeCanvas`, overwriting a prior verified selection.

### Writer B — `replaceState` worktree activation

**Already present before `6453364a`:**

```tsx
// 6453364a^ CanvasCommandDispatcher select-worktree
case "select-worktree": {
  window.history.replaceState(
    {},
    "",
    worktreeSwitchUrl(pathname, search, command.spaceId, command.worktreeId),
  );
  useCanvasStore.getState().initializeCanvas(
    parseCanvasLaunchContext(window.location.search),
  );
  return;
}
```

**`6453364a`** upgraded the switch URL to include `canvas_id` and introduced `initializeVerifiedCanvas` + `canvasIdVerified`.

**`8e240663` / `0c76d520` (CMDK, unmerged)** only **extract** `activateWorktree` and call it from create-workdir; they did not invent the dual-writer pattern.

### Collision timing

| Event | SHA | In S3 chain? |
|-------|-----|--------------|
| Non-reactive `search` + init | `8b236be7` (#39) | **pre-S3** (on main) |
| `replaceState` select-worktree writer | pre-`6453364a` (already on main) | **pre-S3** |
| Collision in §7 form (meta-driven re-init + verified demotion) | **`6453364a` (#316) arrives second** | **pre-S3** (ancestor of `7ffba78b` / STEP-0) |
| create-workdir → activateWorktree | `8e240663` / `0c76d520` | CMDK only (unmerged) — amplifies exposure, not the collision invent |

**Answer:** collision introduced by **`6453364a` (#316)** relative to existing `replaceState` writer; **pre-S3**. Not introduced inside `57d1f087` / `df052e65` / `97a80f56` / `0c76d520`.

---

## Q3. Latent vs new — masked by meta seed?

### Verdict: **LATENT, unmasked by PR1** (`df052e65`)

### Pre-PR1 masking (on main / `7ffba78b`)

1. Lifespan: `_resolve_current_space` → `resolve_cwd(..., create=True)` materializes default Space + detected worktree inventory for process cwd.
2. Meta (`0c6b0e58` #182 → still on `7ffba78b`): `_resolve_launch_worktree` → `resolve_session_cwd` returns `(space_id, worktree_id, root_canvas_id)`.
3. `SessionCanvasRoute`: empty desktop URL launch fields are **null** → `resolveCanvasLaunchIdentity` treats nulls as wildcards (`matchesSpace` / `matchesWorktree` / `matchesCanvas` all true when launch sides are null) → **adopts meta’s durable triple** with `canvasIdVerified: true`.
4. User `replaceState` activation is still non-sticky vs later `meta` recompute, but if meta’s triple is the same primary worktree the user would spawn into, overwrite is **coherent** and spawn POST gets space/worktree/canvas.

### Post-PR1 unmask (`df052e65` → `97a80f56`)

1. No lifespan inventory seed.
2. Meta affinity only from `settings.launch_fields`; desktop clears launch fields → **meta triple null**.
3. `resolveCanvasLaunchIdentity(staleEmptyLaunch, nullMeta)` → **unverified** (`identity.spaceId === null` early exit).
4. `initializeCanvas(unverified)` sets `canvasId: null` (verified gate) and nulls `launch.spaceId` / `canvasId` for spawn readers (scout §7).
5. Backend rejects: `canvas_affinity_required` / “Canvas launches require spaceId, worktreeId, and canvasId”.

Sticky dual-writer hazard is **older than S3** (`6453364a`); S3-schema **unmasks** it by removing the meta/cwd seed that previously re-hydrated a verified, spawnable triple after every overwrite.

---

## One-line answers

1. **Seed:** **removed** by `df052e65` (PR #321); current `97a80f56` fresh empty DB **does not** create Space+Worktree from cwd.  
2. **Collision:** dual-writer collision in §7 form introduced by **`6453364a` (#316)** (second writer over existing `replaceState`); **pre-S3**.  
3. **Latent vs new:** **latent-unmasked** by PR1 meta/lifespan seed removal.

---

## Bus line

`done: ~/.mdx/projects/tm-bug-archaeology.md — seed removed by df052e65; collision introduced 6453364a (pre-S3); latent-unmasked`
