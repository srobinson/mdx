# Optional git-worktree isolation — design pressure test (Grok)

Date: 2026-07-22  
Role: design review (not gate)  
Baseline: `feat/multi-launch` @ `b094e80d69ad7d57c5bba0ff8f4d71a986a837f2`  
Checkout: clean tracked tree (`?? .serena/` only, untouched)

## Established facts (accepted)

- TM never creates git worktrees today. Inventory is detection-only: `space.detection.detect_space` → `SpaceStore.upsert_detection` / `_upsert_worktree`.
- `space.models.Worktree` is a durable path record (`path`, `workspace_slug`/`workspace_hash`, `is_primary`, `missing`, `archived`). No provenance / owned flag.
- Constraint: git worktrees stay **optional**, never auto-created for ordinary use.
- Isolation pressure comes from batch/eval: N candidates need isolated **writable checkouts** so concurrent launches do not collide on the same tree.

## Recommendation

**defer** product-wide “optional isolation param” on Space / Canvas / Pane.

When isolation is introduced (batch/eval needs it), **add-now at Run / launch-candidate only** — not as a durable Space or Canvas field, and not by reinterpreting pane `worktreeId` as “please create.”

**Biggest risk:** without a durable **TM-created vs detected** provenance bit, any later `git worktree remove` or inventory GC can destroy a user’s real checkout (or, conversely, never clean TM-owned trees because detection cannot tell them apart). Detection upsert already rewrites `archived=false` on rematch (`SpaceStore._upsert_worktree`), so provenance must survive refresh.

---

## 1. Now vs defer — value vs cost

### Value (real)

| Need | Evidence |
| --- | --- |
| Batch multi-launch | `NOW.md` / `LAUNCH-CONTRACT.md` `launch_batch`; per-candidate failure isolation is process-level today, not checkout-level |
| Writable isolation | Shared cwd = shared dirty tree, lockfiles, uncommitted agent edits across candidates |
| Eval / S4 | Runtime surfacing plans call for isolated batch execution |

### Partial isolation already exists (do not reinvent)

Per-run **runtime home + storage** already fork under workspace identity (`captured_run_context` / `run_root_for_workspace`). Agent config and capture artifacts do not share one home. What still collides is the **git working tree** (cwd) when many runs resolve the same `worktree_id`.

### Cost of “add isolation now” across the stack

| Cost | Why high |
| --- | --- |
| First git mutation surface | No product `git worktree add/remove` adapter; scout/CRUD reviews already treat this as PR4–PR5 class work |
| Ownership / GC | Must distinguish owned paths; leak or over-delete |
| Detection interaction | `git worktree list` will observe TM-created trees; upsert must not strip ownership |
| Delete/lifecycle races | Prior review: launch gate, dirty check, pending creates (`RunManager.pendingCreates`, `resolve_run_worktree`) |
| Surface sprawl | Four levels × CMDK/MCP/batch before shared `SpaceCrudService` + Git port exist = dual paths |

### Verdict on timing

| Option | Fit |
| --- | --- |
| **defer** general param | **Yes** — isolation is not required for Canvas CRUD, locked-root, or ordinary single launch |
| **add-now(run/batch candidate)** when `launch_batch` needs checkout isolation | **Yes, gated** — only after Git worktree port + provenance column + cleanup policy |
| **add-now(Space/Canvas/Pane)** | **No** — wrong ownership, auto-create pressure, inventory pollution |
| **reject forever** | **No** — batch/eval will need it; reject only “auto create” and “param on every entity” |

---

## 2. WHERE the optional param belongs

### As-built resolution chain (already)

```text
Canvas.default_worktree_id / CanvasModel.defaultWorktreeId
        │  (default only; optional on server)
        ▼
Pane contentRef.worktreeId   (required for terminal + captured-run)
        │  canvasActions.addCapturedRun: worktreeId ?? defaultWorktreeId
        ▼
POST prepare / RunManager create  (PrepareCaptureInput.worktreeId)
        │  capture_rpc_routes._resolved_domain_request
        │  → resolve_run_worktree when directory is null
        ▼
CapturedRunRequest.directory + space_id + worktree_id
        ▼
RuntimeRunView.worktreeId  (resolved identity; no canvasId)
```

Symbols:

- `space.models.Canvas.default_worktree_id`
- `paneRecords.PaneContentRef` (`terminal` / `captured-run` require `worktreeId`)
- `canvasActions.addCapturedRun` / `spawnCapturedRunPane`
- `ports.PrepareCaptureInput.worktreeId`
- `capture_rpc_routes._resolved_domain_request` + `launch_resolution.resolve_run_worktree`
- `runtimeRun.RuntimeRunView.worktreeId`

### What each level means today

| Level | Role today | Isolation param? |
| --- | --- | --- |
| **Space** | Repo container; 1:N worktrees via detection | **No.** Space does not pick a cwd. |
| **Canvas** | Named pane group; optional default worktree | **Select only.** `default_worktree_id` names an inventory row, does not create git trees. |
| **Pane** | Spawn/bind target worktree id | **Select only.** Required id for runnable panes. |
| **Run / launch candidate** | Actual prepare + cwd resolution | **Create-or-select belongs here** if anywhere. |

### Recommended placement

1. **Durable selection chain (keep):**  
   `run.worktree_id` explicit → else pane → else canvas default → else error.  
   All of these reference **existing** `WorktreeId`s.

2. **Optional isolation (new, launch-only):**  
   On single launch / `launch_batch` candidate, e.g.  
   `checkout_isolation: "none" | "ephemeral_worktree"`  
   (name TBD), default `"none"`.  
   Server path: if ephemeral → `git worktree add` under a TM-managed base → register `Worktree` with provenance → resolve that id → prepare capture.

3. **Do not** put `create_git_worktree: true` on Space or Canvas rows (auto-create pressure, long-lived orphans, locked-canvas coupling).

4. **Do not** overload pane `worktreeId` to mean “create if missing.” Missing id is already a client error (`requireWorktreeId`).

One level for **creation**; a **resolution chain** for **which inventory id** to use. Creation is not inheritance — a pane does not silently mint a worktree because its canvas has a flag.

---

## 3. OWNERSHIP / LIFECYCLE

### Opt-in means TM runs `git worktree add`

Yes, on explicit launch/batch opt-in only. That breaks “only detect, never create” **for that path only**. Detection remains the source of truth for **user** checkouts.

### Owned vs detected

| Kind | How it appears | `git worktree remove`? | User primary path? |
| --- | --- | --- | --- |
| **detected** | `detect_space` / list porcelain | **Never** via TM delete of “inventory only”; user owns path | Possible (`is_primary`) |
| **tm_created** | Explicit add under TM base dir | **Yes**, only these | Must be non-primary |

**Where the flag lives:** on the durable worktree row (and model), e.g.:

- `space.models.Worktree.provenance: Literal["detected", "tm_created"]` (or `managed_by`)
- DB column + **not** cleared by `_upsert_worktree` ON CONFLICT updates  
- Optional: `created_by_run_id` / `created_by_dispatch_id` / `ttl` for GC

Path policy: TM-created checkouts under a controlled prefix (e.g. under Space meta or `~/.transport-matters/.../linked-worktrees/`), never `git worktree add` into arbitrary user paths without explicit target.

### Cleanup owner

| Event | Action for `tm_created` |
| --- | --- |
| Run terminate / batch receipt complete | Prefer **retain until explicit GC** or “delete when no runs reference worktree” — not always delete on first terminate (user may want to inspect) |
| Explicit Worktree delete (CRUD) | Allowed only if `tm_created`; runs gate + dirty policy from prior delete review |
| Detection “missing” | Mark missing; GC may remove after grace if still tm_created |
| Space delete CASCADE | DB rows go; must still `git worktree remove` owned paths or leave orphans on disk (receipt) |

**Hard rule:** delete path that runs `git worktree remove` checks `provenance == tm_created` (and non-primary). Detected rows: archive / unlink inventory only, never remove.

### Detection collision

After `git worktree add`, next `detect_space` lists the new path. `_upsert_worktree` keys on `(owner, workspace_slug, workspace_hash)`. Ensure:

- workspace identity for linked trees is stable and unique per path (already path-based hash inputs via `workspace_id`)
- upsert **preserves** `provenance=tm_created`
- do not treat rematch as “user tree” for force-remove

---

## 4. COHERENCE with other directions

| Topic | Interaction |
| --- | --- |
| **Locked-root / workdir locked canvas** | Locked canvas is 1:1 with a **stable workdir** inventory row. Ephemeral isolation worktrees must **not** auto-mint locked canvases. User canvas stays parented under the durable workdir lock; batch candidates may point runs at ephemeral worktree ids without new canvas nodes. |
| **Durable transcript stamp** | Session already has `worktree_id` (nullable, no FK). Stamping the **resolved** worktree (including tm_created) is correct. No need for a second “isolation id” on session if worktree_id is the checkout. |
| **run → canvas affinity** | Still absent (`RuntimeRunView` has space/worktree only). Isolation does not require canvas affinity; batch can remain control-plane / candidate-keyed. |
| **Canvas CRUD / twin-client** | Git create adapter belongs in shared service + Git port (scout PR4), not MCP-only. |
| **Foreclosure** | Does **not** foreclose multi-launch or batch; it enables safer batch. Forecloses only “all launches share one dirty cwd without an opt-in.” Does not force isolation on interactive canvas use. |

---

## 5. Risks (ranked)

1. **Critical — provenance gap:** remove without owned flag → user data loss.  
2. **High — inventory pollution:** ephemeral trees flood CMDK workdir lists unless filtered (`provenance`, TTL, or `list` default hides tm_created).  
3. **High — detection upsert clobber:** lose owned bit / archive intent on refresh.  
4. **High — launch/delete races:** create worktree then launch vs delete; need same lifecycle gate as Worktree delete review.  
5. **Medium — primary / main checkout:** never allow tm_created on primary; never remove primary.  
6. **Medium — path security:** add only under allowlisted bases (echoes secure captured workdir concerns).  
7. **Low — product confusion:** pane worktreeId vs “isolation on” if overloaded.

---

## Assess answers (brief)

| # | Answer |
| --- | --- |
| 1 | **Defer** stack-wide. Value is batch/eval cwd isolation; cost is full Git lifecycle. Per-run storage isolation already exists. |
| 2 | **Creation param: Run / launch_batch candidate only.** Selection chain: run → pane → canvas default. Space: no. Canvas/Pane: select existing ids only. |
| 3 | Opt-in `git worktree add` via Git port; **`provenance` on Worktree row**; remove only `tm_created`; GC/delete service owns cleanup; detection must preserve flag. |
| 4 | Compatible if ephemeral trees stay out of locked-canvas auto-create; transcript uses resolved `worktree_id`; no foreclosure of multi-launch. |
| 5 | **defer** (+ later **add-now(run/candidate)** with provenance). **Biggest risk: deleting or GC’ing a detected user checkout for lack of owned-vs-detected distinction.** |

---

## Suggested later slice (when batch needs it)

1. Migration: `space_worktree.provenance` (+ optional creator dispatch/run id).  
2. Git worktree port: `add` / `remove` under managed base; no call from detection.  
3. Launch flag on prepare / batch candidate only; default off.  
4. List filters: hide or group `tm_created` in casual CMDK.  
5. Delete/GC: owned-only remove; launch gate; dirty/force policy as prior Worktree delete review.  
6. Tests: temp repo add → launch → terminate → remove; detection rematch preserves provenance; refuse remove on detected/primary.

Until then: batch can still ship with **shared checkout + per-run runtime home**, documenting cwd non-isolation as a known limit.
