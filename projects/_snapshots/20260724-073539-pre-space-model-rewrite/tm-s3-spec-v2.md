# S3 — Worktree/Space delete + managed-run stop + tier-1 GC (v2)

Status: **for Stuart review before implementation**  
Date: 2026-07-24  
Baseline: `feat/multi-launch` @ `7ffba78b`  
Supersedes planning weight in `tm-s3-scout.md` for this cut (simple machinery only).
Space model reconciled to `tm-space-crud-spec-v1.md` + `tm-s2-s6-replan-architect.md` §3 (orphan rule **(a)**).  
Snapshot restore point: `~/.mdx/projects/_snapshots/20260724-003703-pre-workdir-correction/`

## 0. Settled product facts (do not re-litigate)

| Fact | Evidence |
| --- | --- |
| "Worktree" = workdir path-identity TM **observes** only | detection-only `git worktree list`; no product `add/remove` |
| User source checkout: **never** deleted | delete is org-row + managed-run + TM-owned disk only |
| Delete-time run-stop = **gateway RunManager only** | `list_runs` → in-memory Map; detached CLI is out of registry |
| Detached CLI (`transport-matters claude` / `codex`) | **OUT OF SCOPE** for stop + for this GC latch |
| No post-drain tier-1 → Postgres repair path | affinity backfill only; §10.5 rebuild unshipped |
| No finalization gate / run_capture_state machine | not needed; no re-ingest repair |

cm: *Delete model = HARD DELETE…*; *Delete GCs tier-1… PROD always / DEV preserves*.

---

## 1. Scope

**In:** desktop/canvas and any other **gateway-managed** run (RunManager `create` → capture RPC prepare → lease).

**Out:** detached CLI ProcessSupervisor launches; inventing a coordinator, finalization protocol, or wire-store re-ingest.

---

## 1A. Space model (captured — do not re-derive)

Authoritative sources: `tm-space-crud-spec-v1.md`, `tm-s2-s6-replan-architect.md` §3, cm `019f8a57` / S1 reshape (VSCode M:N). Code: `worktree_in_space()`, `show_switcher=space_count > 1` (`space_routes.py`).

| Rule | Spec |
| --- | --- |
| Space ≈ VSCode multi-root workspace | A workdir (Worktree) may appear in **multiple** named Spaces (genuine M:N via `space_worktree_link`). Membership authority is **only** `worktree_in_space()` + junction writes. |
| Default Space | Auto-created (`ensure_default_space`); **never delete / never rename / never link into** (`is_default` SQL guards + `space_worktree_link_named_space_ck`: "Default Space membership is computed and cannot be linked"). Membership of the default is **computed-all** (all owner worktrees), not junction rows. |
| Progressive disclosure (human UI) | Space list / switcher / delete / rename **not** surfaced until **more than one** Space exists (`showSwitcher` / `space_count > 1`). Until then CMDK exposes **Create new space** only — no list/delete/rename UX. Source: replan §3 "Switcher surfaces Spaces only when `>1` exists"; REST `show_switcher`; Stuart ground truth. |
| MCP day 1 | **Full** Space command surface from day 1 regardless of UX disclosure: create / list / rename / delete / link-worktree / unlink-worktree (and peers). Source: `tm-space-crud-spec-v1.md` §7 MCP tools; Stuart ground truth. REST mirrors service. |
| Human CMDK vs MCP | CMDK follows progressive disclosure; MCP does not hide tools when only the default exists. |

### ORPHAN RULE (named membership loss)

**When a named Space is deleted, or a workdir is unlinked from a named Space, the workdir is NOT collected.**

| Case | Behavior | Source |
| --- | --- | --- |
| `delete_space(named)` | Drops named Space row; `space_worktree_link` rows CASCADE; **worktrees + root canvases survive** under computed-all default | `tm-s2-s6-replan-architect.md` §3; `tm-space-crud-spec-v1.md` §3 store `delete_space` + tests § "worktrees + root canvases survive" |
| `unlink_worktree` | Deletes link row only; worktree **stays visible via the default** (computed-all); `worktree_in_space(default)` remains true | replan §3 "Remove worktree reference: delete the link row; the worktree stays visible via the default"; space-crud §4 / tests "unlink leaves the worktree visible via the computed-all default" |
| Last named membership removed | Same as unlink/delete-space: workdir remains inventory + canvases; **falls back to undeletable default** (unfiled in named Spaces, still in default) | **(a)** — not reference-counted hard-delete of the worktree |

**Answer to crux:** **(a)** orphaned workdir falls back to the undeletable default Space (survives, unfiled from named Spaces). **Not (b)** canvas-tree/run collection on membership loss.

Hard-delete of a Worktree inventory row (canvas cascade + optional run-stop + tier-1 GC via run teardown) is a **separate** product verb (`delete_worktree`) — not the membership unlink path. Space-CRUD deliberately out-of-scopes worktree/canvas mutation (`tm-space-crud-spec-v1.md` §1).

### User operations (Space vs Worktree)

| User / director op | Effect | Deletes worktree row? |
| --- | --- | --- |
| Create named Space | Insert `space` `is_default=false` | No |
| Rename named Space | Update name | No |
| Delete named Space | Drop space + link CASCADE | **No** — worktrees survive in default |
| Add workdir to named Space | `space_worktree_link` insert | No |
| Remove workdir from named Space | `remove_worktree_link` | **No** — still in default |
| Delete workdir from TM (`delete_worktree`) | Drop `space_worktree` + canvas cascade + stop managed runs | **Yes** — inventory remove only; **never** user git checkout |

### Run-stop: space delete vs worktree delete

| Op | Captured Space-CRUD / replan | This S3 (desktop/gateway) |
| --- | --- | --- |
| Space delete | Space-CRUD: row + links only; **no run-stop in space-crud-spec** | **Add** best-effort stop of gateway-managed runs with `spaceId` (replan Track D / product need) — does **not** delete worktrees or their canvases |
| Unlink workdir | No run-stop; worktree survives | No run-stop required (runs stay attributable by `worktreeId`) |
| Worktree hard-delete | Outside Space-CRUD; replan S3 / inventory delete | Best-effort stop by `worktreeId` + DB cascade canvases/links + runs end → tier-1 GC latch |

---

## 2. PART 1 verification — teardown hook (gateway canvas)

### Path

```
pane close
  → POST /v1/runs/{id}/terminate
  → runtimeRouter → RunManager.terminate → performSettle
  → releaseCaptureBestEffort → POST /v1/capture/{id}/release
  → CaptureLeaseRegistry.release_capture
  → CapturedRunLease.close
```

### Same ExitStack as runtime-home? **YES**

| Step | Symbol |
| --- | --- |
| Shared prepare for gateway | `captured_run.prepare_captured_run` → `build_captured_run_context` |
| Stack created | `captured_run_context.build_captured_run_context` → `stack = ExitStack()` |
| runtime-home callback | `_prepare_home_and_grant`: `stack.callback(shutil.rmtree, runtime_home_root, ignore_errors=True)` when write+overlay prepared (`runtime_home_root = prepared.resolved_storage / "runtime-home"`) |
| Stack on lease | `CapturedRunLease(..., _resource_stack=ctx.resource_stack)` |
| Unwind on release | `CapturedRunLease.close` → `self._resource_stack.close()` **after** `terminate_all` |

CLI and gateway share this prepare/lease seam for managed capture; canvas uses capture-RPC `prepare_captured_run`, not a different stack.

### Ordering vs drain

`CapturedRunLease.close` order:

1. `_supervisor.terminate_all()` — SIGTERM→wait→SIGKILL; waits for mitmdump process exit  
2. signal restore, manifest unlink, workspace lock exit  
3. `_resource_stack.close()` — LIFO callbacks (runtime-home rmtree)

Graceful mitmdump exit runs `TransportMattersAddon.done` → `close_capture_runtime` (tailer drain → wire/live aclose → writer) **inside** process death that `terminate_all` awaits.  
Therefore **resource_stack callbacks run after capture drain has been attempted** (post process-exit). Latching tier-1 rmtree on that stack is **safe for "raw already written; IR/DB best-effort already attempted"**.

(Drain success remains best-effort / uninspected — prior trace. No finalization gate.)

### Exact latch point for tier-1 GC

| Item | Value |
| --- | --- |
| **Register** | Same function as runtime-home: `captured_run_context._prepare_home_and_grant` on `stack` (or equivalent callback registration on the same `ExitStack` before lease ownership) |
| **Execute** | `CapturedRunLease.close` → `_resource_stack.close()` |
| **Path known** | `prepared.resolved_storage` (= default per-run root `workspaces/{slug}/{hash}/{run_id}/` via `run_root` / `run_root_for_workspace`; also `spawn_spec.storage_dir` / `CapturedRunSpawnSpec.storage_dir`) |
| **runtime-home** | `prepared.resolved_storage / "runtime-home"` (subdirectory of tier-1 root) |

**Do not** invent a second teardown path. One trigger: run-end/release → lease.close → stack.

---

## 3. Worktree inventory delete (`delete_worktree`)

**Not** "remove workdir from a Space" (that is `unlink_worktree` — membership only; see §1A orphan rule **(a)**).

### Semantics

Hard-delete the `space_worktree` **inventory** row (TM observation record + canvas tree):

1. Clear foreign `canvas.default_worktree_id` pointers that reference this worktree (**before** drop): `canvas_default_worktree_fk` is `ON DELETE NO ACTION` (deferrable) in `0030` — command must null/repoint or reject, not leak constraint errors.
2. `DELETE FROM space_worktree` → cascades:
   - `canvas_anchor_worktree_fk` ON DELETE CASCADE (root + user subtree)
   - `space_worktree_link_worktree_fk` ON DELETE CASCADE (membership)
3. `space_worktree_root_canvas_fk` is NO ACTION deferrable — use correct statement order / deferral (existing migration test: `test_worktree_delete_cascades_root_subtree_and_membership_then_commits`).

### Run stop (best-effort)

- Enumerate: `RunRouteProxy.list_runs(owner=, worktree_id=)` → gateway `RunManager.list` (in-memory managed only).
- Each: `RunManager.terminate` / existing terminate proxy (same as pane close).
- Failures: log/continue; no force protocol.
- **Never** `git worktree remove` / never touch user checkout path.

### STEP-0

`space/store.py` is **693** lines (hard 700). Extract before adding `delete_worktree` (first nontrivial store method for this track).

### Surfaces

- `SpaceStore.delete_worktree` + service orchestration + REST + MCP parity.
- Tests: cascade guardrail (existing) + `test_worktree_delete_endpoint_drops_rows_and_stops_runs` (new).

**Migration:** none (0030 FKs already).

---

## 4. Space delete (named only)

### Semantics (match Space-CRUD)

Source: `tm-space-crud-spec-v1.md` §3–4; `tm-s2-s6-replan-architect.md` §3.

- **Default Space:** cannot be deleted (`delete_space` `AND NOT is_default` → `space_default_locked`).
- **Named Space:** `DELETE FROM space` → cascades **`space_worktree_link` only**. Worktrees and canvases **survive** under the **computed-all default** (orphan rule **(a)**).
- **Not** worktree inventory delete. **Not** canvas cascade. **Not** auto-GC of tier-1 solely because a named Space vanished (runs may continue under worktreeId; stop is separate below).

### Run stop (best-effort; product add-on)

Space-CRUD build spec does **not** define run-stop. This S3 **adds**:

- `list_runs(owner=, space_id=)` → terminate each **gateway-managed** run.
- Failures: log/continue.
- Surviving worktrees keep their canvas trees; any remaining managed runs bound only by worktree (if any) are out of this space filter.

### Surfaces

- Existing: `SpaceStore.delete_space`, service, REST `DELETE /v1/spaces/{id}`, MCP `space_delete`.
- Extend service with stop step (S3a). MCP remains full Space CRUD day 1.


---

## 5. Tier-1 GC (latch, not a second product)

### Model

- **One trigger:** managed run teardown (`CapturedRunLease.close` / resource_stack).
- Worktree/space **delete only ends managed runs**; GC is a side effect of that teardown (plus optional later dangling sweep — not required for S3a).
- **PROD (`dev_mode=False`):** rmtree the run's tier-1 root (`resolved_storage`) after drain attempt (stack callback post-`terminate_all`).
- **DEV (`dev_mode=True`):** preserve tier-1 and (per ruling) **also skip** runtime-home rmtree so local forensics stay intact — both cleanups gated the same way.

### Implementation notes

- Register beside runtime-home in `_prepare_home_and_grant` (or one combined "cleanup managed storage root" callback that respects `dev_mode`).
- Best-effort: `ignore_errors=True` or staged rename+rmtree; never raise into release path in a way that blocks RUN_EXITED emission more than today.
- **Containment:** resolve path; require it is under `default_workspaces_root()` (channel home `…/workspaces/`); refuse if outside (custom `--storage-dir` / `STORAGE_DIR` override → **preserve / skip GC**, log; unspecified to invent a second GC root).
- Prefer single rmtree of `resolved_storage` (covers `runtime-home/`, exchanges, transcripts, index) over dual callbacks that race.
- **No** finalization gate. **No** `run_capture_state` table.

### Dangling (optional follow-on, not S3a)

`iter_run_dirs` + session/run_id presence can sweep orphans later. Not required to ship delete.

---

## 6. Flag: `TRANSPORT_MATTERS_DEV_MODE`

| Item | Spec |
| --- | --- |
| Settings | `dev_mode: bool = False` on `config.Settings` |
| Env | `env_keys.DEV_MODE = f"{ENV_PREFIX}DEV_MODE"` → `TRANSPORT_MATTERS_DEV_MODE` |
| Pattern | Same as `debug` / `gateway_supervise` (bool + env_prefix) |
| **Do not** | Reuse `debug` (logging only) or `channel` (stable/preview isolation) |

### Defaults / CI stamp

**Today:** no build-time product flag stamp exists (hatch-vcs versions the wheel; `__version__` from package metadata; no `_build_defaults` module for feature flags). **Seam: unspecified** for "stamp prod into artifact."

**Recommended prod-safe default (implements the spirit without a missing stamp machinery):**

- **Default `dev_mode=False`** (GC on) in code — shipped wheel is prod-safe without CI rewrite.
- Local dogfood / preview: set `TRANSPORT_MATTERS_DEV_MODE=1` in env (or channel docs).
- CI tests that need preserve: set env in job; jobs that assert GC leave unset.

If Stuart requires an explicit CI stamp later: add a generated `transport_matters/_build_flags.py` force-included by hatch in `release.yml` / `api/just build` — **not present today**; flag as future.

---

## 7. Slicing

| Slice | Deliverable | Gate |
| --- | --- | --- |
| **S3a** | STEP-0 store extract; `delete_worktree` + service/route/MCP; space-delete run-stop; best-effort `list_runs`+terminate by worktree/space | `just check` + `just test`; cascade + stop tests |
| **S3b** | `Settings.dev_mode`; gate runtime-home + tier-1 cleanup on stack; containment check; light tests (preserve vs GC) | same full gates; no migration |

S3b stays thin: no dangling sweeper, no CLI coverage, no finalization.

---

## 8. Reuses existing machinery

| Capability | Existing owner | Do not invent |
| --- | --- | --- |
| Stop managed run | `RunManager.terminate` / POST `/v1/runs/{id}/terminate` / `performSettle` | New kill protocol |
| List by worktree/space | `RunManager.list` + `controlplane_gateway_runs.list_runs` | Process scan of detached CLI |
| Capture teardown + stack | `CapturedRunLease.close` + `ctx.resource_stack` from `build_captured_run_context` | Second ExitStack |
| runtime-home cleanup | `_prepare_home_and_grant` `stack.callback(shutil.rmtree, …)` | Parallel home GC |
| Run storage path | `prepared.resolved_storage` / `run_root` / `run_root_for_workspace` / `spawn_spec.storage_dir` | New identity scheme |
| Enumerate run dirs (later) | `session.backfill.iter_run_dirs` | New walker |
| Staged FS delete patterns | `storage.disk_helpers` exchange stage/rmtree (optional reuse for safety) | Ad-hoc `rm -rf` without containment |
| Space delete row | `SpaceStore.delete_space` | Rewrite membership rules |
| Cascade proof | `test_worktree_delete_cascades_root_subtree_and_membership_then_commits` | Skip schema tests |
| Env bool flag pattern | `Settings` + `env_keys` + `TRANSPORT_MATTERS_*` | Ad-hoc os.environ |

---

## 9. Explicit non-goals (this S3)

- Detached CLI stop or tier-1 GC latch on CLI-only ExitStack paths beyond shared prepare (CLI already shares prepare when using the same seam; **stop** still out of RunManager).
- Git worktree create/move/remove.
- Finalization / drain success bit / `run_capture_state`.
- Rebuilding Postgres from tier-1.
- GC of custom `--storage-dir` outside workspaces root.
- Canvas delete (S4b) and create/move (S5) — separate tracks; S5 still reframed as workdir-record, not git ops.

---

## 10. Review checklist for Stuart

- [ ] Space model §1A matches captured Space-CRUD (M:N, default undeletable, orphan **(a)**)  
- [ ] CMDK progressive disclosure vs MCP full day 1 is correct  
- [ ] Worktree **inventory** delete vs **unlink** membership is not conflated  
- [ ] Scope desktop/gateway-only is correct  
- [ ] Hook latch on `_prepare_home_and_grant` / `CapturedRunLease.close` stack is the right place  
- [ ] `dev_mode` default False (prod GC) is acceptable without CI stamp machinery  
- [ ] S3a then S3b split is right  
- [ ] No finalization gate stays locked  

**Ready to implement only after Stuart sign-off on this file.**
