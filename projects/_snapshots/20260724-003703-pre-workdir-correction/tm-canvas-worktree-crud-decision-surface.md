# Canvas / Worktree CRUD — decision surface

Date: 2026-07-22  
Inputs: `tm-canvas-worktree-crud-scout.md`, `LAUNCH-CONTRACT.md`, `tm-multilaunch-canvas-relationship.md`  
Checkout: `feat/multi-launch` @ scout head `b094e80d69ad7d57c5bba0ff8f4d71a986a837f2`  
Governing rule: one application service for both skins. REST / CMDK / MCP are adapters. Do not design here.

Cross-check: `LAUNCH-CONTRACT.md` does not define Canvas or Worktree CRUD. It does constrain this work: every launch surface already enters one service; `workdir` is required; resolution pins workspace identity; missing and archived Worktrees fail launch via `launch_resolution.resolve_run_worktree`. Twin-client DRY and delete/launch concurrency are therefore contract-aligned, not optional style.

---

## 1. REUSE dispositions

| # | Capability | Existing owner | Disposition | Reason |
| --- | --- | --- | --- | --- |
| 1 | Durable IDs and domain rows | `space.models::Canvas`, `Worktree`, related IDs | **Reuse** | Models are the durable substrate; no second schema. |
| 2 | FK / uniqueness for Space, Worktree, Canvas, default Worktree | migrations under spaces foundation (e.g. `0006_spaces_foundation`) | **Reuse** | Constraints stay in DB; service must not invent parallel integrity. |
| 3 | Git observation / identity inputs | `space.detection::detect_space` | **Reuse** | Observation only; no production `git worktree add/remove` yet. |
| 4 | Worktree reads | `SpaceStore.get_worktree`, `list_worktrees`, `resolve_worktree` | **Reuse** | Current read authority; promote through service, do not re-SQL. |
| 5 | Canvas list / create / update persistence | `SpaceStore.list_canvases`, `create_canvas`, `update_canvas` | **Refactor** | Persistence works; same-Space validation and patch presence live outside the store. |
| 6 | DTO projection, same-Space check, origin checks | `space_routes` (`_require_worktree_in_space`, create/list/patch handlers) | **Refactor** | Extract into shared service so MCP cannot bypass route-only invariants. |
| 7 | Browser request handling + Space/Worktree read contracts | `@tm/core` transport + Space/Worktree types | **Refactor** | Read contracts exist; DTOs drift (path nullability, archived); split Space/Canvas transport before full CRUD. |
| 8 | Query + invalidation integration | React Query + `useSpaces` | **Reuse** | Natural client cache seam for CRUD invalidation. |
| 9 | CMDK grammar, rows, dispatch | `LauncherCommand`, row builders, `CanvasCommandDispatcher` | **Reuse** | Add entity CRUD commands on existing grammar; no second palette bus. |
| 10 | Visible Canvas identity + local layout cache | `route.defaultCanvasId`, `canvasStoreLifecycle.initializeCanvas`, `canvasCacheStorage.createCanvasCacheStorage` | **Refactor** | Synthetic IDs (`space:…`, workspace hash, `direct-local`) must migrate to durable UUIDs. |
| 11 | Pane Worktree placement + local run ownership | pane content refs, `canvasActions` run attach/stop policies | **Deviate** | Reuse placement facts for cleanup; do **not** treat `canvasActions.clearCanvas` as server delete (owned runs terminate fire-and-forget; adopted service runs are forgotten). |
| 12 | Runtime Worktree filter / terminate | `RunManager.list` + filters, runtime router terminate | **Refactor** | Filtering exists; needs a dedicated inventory/gate port for atomic live+pending+terminating answers. |
| 13 | Principal, Director auth, structured errors, audit | `ControlPlanePrincipal`, `ControlPlaneService`, control-plane error/audit conventions | **Reuse** | MCP trust inputs and error shape stay here; service consumes typed caller context. |
| 14 | MCP auth, adapter delegation, tool registration, envelopes | `ControlPlaneMcpAuthApp`, `_McpControlPlaneAdapter`, `create_control_plane_mcp` | **Refactor** | Pattern reuses; extract focused tool registration before adding CRUD tools (`controlplane_mcp` already near size limit). |

**Counts:** clean **Reuse** = **7** · needs human eye (**Refactor** / **Deviate**) = **7**.

---

## 2. MISSING PRIMITIVES (12)

Each line: net-new code · entity · C/R/U/D · surface.

1. **`SpaceCrudService`** (typed caller context, commands, results, receipts, stable errors) · both · all · **server** (authority both skins call)
2. **Owner-scoped Canvas get-by-id** repository op · Canvas · **R** · **server**
3. **Browser Canvas DTOs / queries / mutations / selection on server UUIDs** · Canvas · **C/R/U** · **CMDK** (client substrate)
4. **Canvas patch field-presence + layout authority / version policy** · Canvas · **U** · **server**
5. **Canvas delete** (cache invalidation, panes, run policy, fallback navigation, receipt) · Canvas · **D** · **server** (+ CMDK/MCP skins)
6. **Git Worktree create adapter** (`git worktree add`) · Worktree · **C** · **server**
7. **Worktree update command** (label / move / archive / branch subset TBD) · Worktree · **U** · **server**
8. **Safe Worktree deletion preflight + operation** · Worktree · **D** · **server**
9. **Atomic launch gate / lease** covering pending + registered runs by Worktree · Worktree · **D** (safety) · **server**
10. **Cross-reference cleanup** (Canvas defaults, sessions, pane caches, query state) · both · **D** · **server** (+ client invalidation)
11. **CMDK CRUD commands** (rows, confirm, progress, error, receipt) · both · all approved · **CMDK**
12. **MCP CRUD tools + schemas** through shared service · both · all approved · **MCP**

---

## 3. SCOPE DECISIONS (for human disposition)

### 3a. V1 matrix — Canvas/Worktree × CRUD × CMDK/MCP

Mark is **scout rec**. Adjust cells before implementation.

| Entity | Op | CMDK | MCP | Scout rec v1 | Defer notes |
| --- | --- | --- | --- | --- | --- |
| Canvas | **C** create | yes | yes | **v1** | Metadata first; layout hydration is an open sub-question. |
| Canvas | **R** list + one | yes | yes | **v1** | Archived-in-list default still open. |
| Canvas | **U** update | yes | yes | **v1** | Name + default Worktree; layout mutation may defer. |
| Canvas | **D** delete | pending | pending | **policy-gated** (PR3 after policy) | No implementation without delete semantics (3b). |
| Worktree | **C** create | yes | yes | **v1** | Implies real `git worktree add` (scout rec: yes). |
| Worktree | **R** list + one | yes | yes | **v1** | MCP inventory: full owner vs principal Space only (open). |
| Worktree | **U** update | pending | pending | **defer until defined** | Subset of rename/move/label/archive/branch not chosen. |
| Worktree | **D** delete | pending | pending | **policy-gated** (PR5 after policy) | Highest risk; server lifecycle gate required. |

**Scout coherent minimum:** read parity both surfaces + every approved mutation only through `SpaceCrudService`. Layout mutation and destructive Worktree ops held until policy.

`LAUNCH-CONTRACT` alignment: launch already rejects missing/archived Worktrees; archive-as-soft-delete is compatible with existing launch resolution if you choose it.

### 3b. DELETE SEMANTICS (crux)

Candidate policies for every row: **block** · **cascade-delete** · **detach/orphan** · **archive** · **force-with-confirm**.

#### Canvas delete

| Conflicting state | Candidate policies | Scout rec default |
| --- | --- | --- |
| Durable metadata row exists | archive · cascade-delete (hard) · force-with-confirm | **Needs human.** Scout leaves archive vs hard open; PR3 assumes “archive or delete” with receipt. |
| Browser local panes + localStorage cache for that Canvas ID | cascade-delete (clear cache/panes) · detach (leave cache) · force-with-confirm | **Scout rec lean: cascade-delete local cache/panes with the approved durable action** so dual authorities do not leave a zombie namespace. Explicit coordination called out. |
| Active Canvas is the one being deleted | cascade + fallback route · block | **Scout rec: fallback navigation required** (active route fallback is in PR3). Exact target (synthetic Space Canvas vs another named Canvas) needs human. |
| Local panes present (no runs) | cascade-delete panes · detach · force-with-confirm | **Scout rec lean: cascade with Canvas delete** (not silent orphan of pane records under deleted ID). |
| LIVE runs owned by this Canvas (canvas launch_kind / pane-owned) | block · cascade terminate · detach/orphan · force-with-confirm | **Needs human.** `clearCanvas` terminates fire-and-forget today; scout says that must not become server policy without an explicit choice. |
| LIVE adopted service runs (not Canvas-owned) | block · detach/orphan · cascade terminate · force-with-confirm | **Needs human.** `clearCanvas` forgets without terminate; scout flags this split. |
| PENDING / creating runs tied to Canvas panes | block · cascade cancel · detach · force-with-confirm | **Needs human.** No Canvas-side pending inventory today. |
| Server `layout` jsonb / `layout_version` | cascade clear · archive-with-layout · preserve | **Needs human** (depends on layout authority decision). |
| Future durable session/run history linked to Canvas | retain · tombstone · cascade | **Scout rec lean: open / future**; no server run→canvas edge today. |

**Canvas rows needing a human call (no safe default locked):** durable archive-vs-hard, owned-run policy, adopted-run policy, pending-run policy, layout retention, active fallback target · **6**.

#### Worktree delete

| Conflicting state | Candidate policies | Scout rec default |
| --- | --- | --- |
| Inventory row only (no Git remove) | archive · cascade-delete row · force-with-confirm | **Needs human** whether “delete” means archive row or `git worktree remove`. Detection currently resets `archived=false` on match, so user archive must be stored separately from detected facts if archive is chosen. |
| Primary checkout / main worktree | **block** (unconditional) · force-with-confirm | **Scout rec lean: protect primary checkout** (PR5 enforces; still confirm “always block” vs force). |
| Dirty tracked files | block · force-with-confirm | **Needs human.** Scout asks if dirty always blocks; force in v1 is open. |
| Untracked files | block · force-with-confirm · ignore | **Needs human.** |
| LIVE registered runs on this Worktree | block · cascade terminate · detach · force-with-confirm | **Scout rec lean: server inventory must observe them**; default policy still human. Frontend preflight is not authority. |
| PENDING launches (passed availability, not yet registered) | block via launch gate · cascade · force-with-confirm | **Scout rec: atomic launch gate/lease required** so delete cannot race launch. Policy for in-flight create still human (block vs wait vs force). |
| TERMINATING runs | block until quiet · force-with-confirm · proceed | **Needs human**; inventory port must see terminating state. |
| Canvas `default_worktree_id` points here | block · cascade null/clear · reassign · force-with-confirm | **Scout rec: cross-ref cleanup required**; exact policy needs human. |
| Durable session Space/Worktree refs (indexes, no FK) | retain (dangling) · tombstone · clear · block | **Needs human.** Hard delete can leave unresolvable session refs today. |
| Git remove succeeds, DB reconcile fails | receipt partial · retry · compensate | **Scout rec: structured multi-phase receipt**; no silent success. |
| Git remove fails after launch gate acquired | release gate · leave archived/blocked · force retry | **Scout rec: receipt every phase**; exact recovery path human. |

**Worktree rows needing a human call:** archive-vs-git-remove, primary force, dirty, untracked, live runs, pending launches, terminating, Canvas defaults, session refs · **9** (receipt shape is scout-fixed; recovery detail still open).

**Delete-semantics rows needing a human call (combined, no locked scout default):** **15** (Canvas 6 + Worktree 9). Receipt + server-side gate + “no browser-owned safety” are scout-fixed non-negotiables, not open policy.

### 3c. Twin-client contract

**One shared Python path (DRY).** Scout rec and `LAUNCH-CONTRACT` pattern (one launch service, many skins):

```text
CMDK → browser transport → REST adapter → SpaceCrudService
MCP  → authenticated tool adapter      → SpaceCrudService
                                         → repositories / Git worktree port / run inventory+launch gate / audit
```

Seam to introduce: **`SpaceCrudService`** (net-new application service; no existing symbol). Adapters: REST via `space_routes` extraction; MCP via `_McpControlPlaneAdapter` + focused registration extracted from `create_control_plane_mcp`. Direct `SpaceStore` from MCP and browser-owned deletion safety are excluded by structure.

---

## 4. OPEN QUESTIONS (scout raised, unresolved)

1. Canvas create: metadata only, or create plus layout hydration?
2. Canvas list: include archived by default?
3. Canvas update: name + default Worktree only, or layout too? What does `layout_version` mean (concurrency vs schema)?
4. Canvas patch: how to clear `defaultWorktreeId` (field presence / sentinel)?
5. Canvas default Worktree: reject missing/archived at write time (scout lean yes) — confirm.
6. Director MCP scope: mutate every Space owned by principal, or only Space resolved from workspace?
7. MCP Worktree inventory: full owner vs principal Space only?
8. MCP path resolve (`detect_space` / CWD): constrain to principal workspace / approved Space so it does not enumerate filesystem?
9. Worktree update subset: rename label, move path, archive, branch change, or selected subset?
10. Worktree create: always `git worktree add`, or inventory-only registration ever allowed?
11. Synthetic → UUID Canvas identity migration / fallback for existing localStorage keys?
12. `refresh=true` Worktree list mutation: keep hidden write on REST, or make observation vs mutation explicit for MCP?
13. Filesystem Space cache (`SpaceStore._write_cache`): retain as diagnostic or kill as stale parallel projection?
14. Stub runtime identities (`RunManager.DEFAULT_SPACE_ID` / `DEFAULT_WORKTREE_ID`): confirm CRUD safety rejects unresolved fixture IDs.

---

## Disposition checklist (human)

- [ ] Approve / edit **3a v1 matrix** cell by cell  
- [ ] Lock **Canvas delete** policies for the 6 open rows  
- [ ] Lock **Worktree delete** policies for the 9 open rows  
- [ ] Confirm **3c** single `SpaceCrudService` (scout rec: yes)  
- [ ] Answer open questions that unblock PR1–PR2 (UUID migration, patch presence, layout in/out of v1, MCP Space scope)

**Non-negotiables unless you override:** twin-client DRY; server-side Worktree lifecycle gate; structured delete receipts; no `clearCanvas` as server delete; no frontend preflight as safety authority.
