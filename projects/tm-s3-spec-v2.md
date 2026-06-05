# S3: Space/Workdir delete, managed run stop, and tier 1 GC (v2)

Status: **for Stuart review before implementation**  
Date: 2026-07-24  
Baseline: `feat/multi-launch` @ `7ffba78b`  
Domain model: cm **Space/Workdir/OS-dir domain model (CONFIRMED)** plus **S3 model refinements (2026-07-24)**  
Snapshot before this rewrite: `~/.mdx/projects/_snapshots/20260724-073539-pre-space-model-rewrite/`  
Supersedes earlier S3 drafts that used computed membership, shared workdir M:N, or a backend default Space.

---

## 0. Confirmed domain model

```
OS dir  ──physical folder on disk (git or plain).
   ↑
   │ many Workdir entities may point at the same OS dir
   │
Workdir ──TM entity. Points to EXACTLY ONE OS dir. Belongs to EXACTLY ONE Space (N:1).
   │      Carries DETECTED or CREATED provenance.
   │      Same folder in two Spaces = TWO workdir rows with the same canonical OS path.
   │
Space   ──contains N workdirs (1:N). == VSCode multi-root workspace.
   │      Backend cardinality is 0..N Spaces. Every Space is equal and deletable.
   │
Canvas  ──anchored to a workdir; canvases are hierarchical/nested (full tree detail → S4b).
   │
Run     ──under a canvas → thus under exactly one workdir → exactly one Space.
```

| Rule | Meaning |
| --- | --- |
| OS dir | Physical path for a git checkout, git worktree, or plain directory |
| Workdir → Space | **N:1** (each workdir has one owner Space) |
| Space cardinality | Backend permits 0..N Spaces; all are equal and deletable |
| Provenance | Existing `WorktreeProvenance.DETECTED` or `.CREATED` marker |
| Detected | Pre-existing directory found through read-only git introspection; TM never changes or removes it on disk |
| Created | Directory or git worktree provisioned by TM on explicit user action |
| Future Workdir create | Requires an existing owning `space_id` and records `created` provenance |
| Path uniqueness | `UNIQUE(space_id, canonical_os_path)` |
| Multi-Space folder | Separate workdir entities per Space, same OS path |

The same canonical OS path in the same Space returns `CONFLICT`; creation never upserts. The same path in another Space creates a separate workdir row.

`WorktreeProvenance`, `StoredWorktree.provenance`, and `WorktreeRecord.provenance` already exist. Migration 0030 constrains the durable value to `detected` or `created`. Re-detection through `SpaceStore.upsert_worktree` updates only path and timestamp on conflict, preserving provenance and root identity.

### Future client-composed bootstrap and active Space

The worktree create primitive lands with the later disk-provisioning slice because no production path emits `created` today.

- `create_workdir` always accepts a valid `space_id`, and the referenced Space must exist.
- When the first create-workdir action starts from zero Spaces, the UI client and MCP client each call `create_space`, then `create_workdir`. The service exposes two honest primitives and no bootstrap composite.
- The seed Space name uses the repository or directory basename when available, with a placeholder fallback. The desktop hides that name while only one Space exists.
- A starter Space may remain empty. Deleting its last workdir is a normal delete.
- The desktop may guard deletion of its last visible Space as a UX affordance. Backend deletion remains valid.
- `switch` means “select active Space for desktop context.” MCP exposes it from day 1. CMDK surfaces it once more than one Space exists. Alternative naming belongs to the later UX pane.

cm: *S3 model refinements (2026-07-24): zero-spaces OK, undeletable-default is UX-only, workdir uniqueness (space_id, os_path), no tier-1 sweep, switch verb*.

---

## 1. Scope

**In:** desktop/canvas, gateway-managed runs (`RunManager` create → capture RPC prepare → lease), and deletion of `detected` workdirs through de-inventory only.

**Out:** `created` provenance disk cleanup; worktree create and `git worktree add`; detached CLI stop; finalization/run_capture_state; dangling tier 1 sweep; full canvas tree product (S4b one-liner only).

S3 implements the `detected` delete branch only. This covers every current workdir because the sole production materialization path is detection and no production symbol sets `created`. Created cleanup and worktree creation land together in the later disk-provisioning slice.

---

## 2. Delete semantics (confirmed cascade)

### DELETE workdir

Read the stored Workdir provenance before mutation. Both branches stop scoped gateway-managed runs, clear foreign `canvas.default_worktree_id` references, delete the Workdir inventory row, cascade its anchored Canvas tree through the existing anchor FK, and retain historical session, wire, transcript IR, and FK-free affinity stamps.

| Provenance | Delete contract | Delivery |
| --- | --- | --- |
| `detected` | De-inventory only. The pre-existing OS directory is never removed or changed on disk | **S3** |
| `created` | De-inventory plus disk cleanup. Use `git worktree remove` when clean. Dirty state requires explicit confirmation or refusal; silent `--force` is forbidden | **Later disk-provisioning slice** |

Other Spaces' Workdir rows that point at the same OS path remain unaffected. Tier 1 collection occurs only in run-end teardown for runs that settle. Deleting the last workdir in a Space is a normal delete, and an empty Space is valid.

### DELETE Space

- List and stop gateway-managed runs for the target Space.
- Drop the named Space and cascade all owned workdirs and their anchored Canvas trees.
- Apply each Workdir's provenance contract independently: detected directories stay on disk; created directories use the later clean-or-confirm cleanup path.
- Retain session, wire, and transcript IR plus FK-free affinity stamps as historical tombstones.
- Other Spaces remain unaffected, including workdirs that point at the same OS path.
- Deleting the final Space is valid backend behavior and leaves zero Spaces.

### Managed run stop sequence

1. Call existing `RunManagementPort.list_runs` through `RunRouteProxy`, filtered by the target `space_id` or `worktree_id`.
2. Call `RunManagementPort.terminate_run` for every returned run.
3. Continue after individual stop failures and record the failures for typed response or logs.
4. Apply the database cascade mutation after all stop attempts.
5. Let settled runs collect tier 1 only through their run-end teardown. A run that fails to stop keeps its directory.

S3 introduces no new HTTP client, delete coordinator, process scan, or OS directory cleanup path. Detached CLI runs remain outside this registry.

### Command surface

| Surface | Behavior |
| --- | --- |
| **MCP** | Full Space CRUD, detected Workdir list/delete, and `switch` in S3; Workdir create completes CRUD in the later disk-provisioning slice |
| **CMDK / human** | Desktop seeds a starter Space; progressive disclosure hides Space naming and `switch` until more than one Space exists |

---

## 3. Teardown hook (gateway canvas): settled

```
pane close / terminate
  → POST /v1/runs/{id}/terminate
  → RunManager.performSettle
  → releaseCapture → CaptureLeaseRegistry.release_capture
  → CapturedRunLease.close
```

| Item | Symbol / fact |
| --- | --- |
| Stack | `build_captured_run_context` ExitStack → `CapturedRunLease._resource_stack` |
| runtime-home | `_prepare_home_and_grant`: `stack.callback(shutil.rmtree, runtime_home_root, …)` |
| Close order | `terminate_all` (mitmdump exit / drain attempt) **then** `_resource_stack.close()` |
| Latch tier 1 GC | Run-end callback after the capture drain settles; path = `prepared.resolved_storage` |
| Failed stop | Preserve the run directory when the run does not settle |

Verified: canvas prepare uses `prepare_captured_run` → same stack as runtime-home.

Target deletion owns run discovery and stop attempts. Tier 1 and runtime-home cleanup remain inside this teardown lifecycle. Created OS directory cleanup belongs to the later disk-provisioning slice.

---

## 4. Implementation notes (DB seams at HEAD)

Current schema still uses names `space_worktree` / links / `worktree_in_space` and may still encode **computed-all default** membership. That is **legacy relative to the CONFIRMED model**.

Rewrite store, service, REST, MCP, and tests to N:1 ownership:

- Workdir owns one required `space_id`.
- Enforce `UNIQUE(space_id, canonical_os_path)`.
- Replace HEAD's `UNIQUE(owner, path)` and `(owner, workspace_slug, workspace_hash)` constraints.
- Delete `space_worktree_link`, `worktree_in_space(...)`, and every link/unlink store, service, REST, MCP, and test path.
- Remove the M:N implementation in the same slice. No parallel compatibility path remains.
- Keep detection as the S3 Workdir materialization path and preserve `detected` provenance.
- Reserve `create_workdir` for the later disk-provisioning slice. It takes an owning `space_id`, requires that Space to exist, records `created`, and returns `CONFLICT` for the same canonical path in the same Space.

This pre-release schema change resets the development database. An Alembic revision reshapes the schema; existing dev data needs no preservation, upgrade transformation, or downgrade transformation.

**STEP 0:** `space/store.py` is 693 lines. First extract SQL and row conversion seams in an independent, behavior-neutral slice. The ownership rewrite starts only after that slice lands.

**Delete order:** for `delete_workdir`, null foreign `canvas.default_worktree_id` references before deleting the workdir row, then cascade its anchored Canvas tree.

**Provenance reuse:** use the existing `WorktreeProvenance` enum, `StoredWorktree.provenance`, `WorktreeRecord.provenance`, and migration 0030 constraint. Keep `SpaceStore.upsert_worktree` marker preservation. The later created cleanup generalizes `harnesses/certification_minting.py::require_clean_worktree`, which already runs `git status --porcelain --untracked-files=all`; do not add another git-status caller.

**Surfaces:** `SpaceStore`, `SpaceCrudService`, REST, MCP, and shared contracts move together. S3 tests:

- zero Spaces is valid; every Space can be deleted
- same path in one Space conflicts; same path in two Spaces creates independent workdir rows
- re-detection preserves `created` provenance and root identity
- detected Workdir delete de-inventories and cascades Canvas inventory while preserving the OS directory
- Space delete applies detected de-inventory to every current Workdir
- deleting workdir B clears a Canvas in workdir A whose `default_worktree_id` points to B
- workdir and Space deletion cascade inventory while session, wire, transcript IR, and affinity stamps survive
- managed run stop stays scoped by Space or workdir

The later disk-provisioning slice tests `create_workdir`, client-composed bootstrap, created provenance, clean removal, dirty confirmation or refusal, and the ban on silent `--force`.

---

## 5. Tier 1 GC and `dev_mode`: settled

| Item | Spec |
| --- | --- |
| Trigger | One: managed run teardown (`CapturedRunLease.close` → resource_stack) |
| Delete role | Stop managed runs; settled run teardown owns tier 1 and runtime-home cleanup |
| PROD (`dev_mode=False`) | Collect the run's tier 1 root and runtime-home after the capture drain |
| DEV (`dev_mode=True`) | Preserve tier 1 and runtime-home |
| Containment | Only under `default_workspaces_root()`; skip custom `--storage-dir` outside |
| Finalization gate | **No** (no shipped tier-1→DB repair path) |
| Flag | `Settings.dev_mode: bool = False` → `TRANSPORT_MATTERS_DEV_MODE` |
| Do not reuse | `debug` (logging), `channel` (stable/preview isolation) |
| Defaults | Code default is false; development launch scripts set true; CI explicitly stamps the production false value |
| Dangling sweep | None in S3 |

The run-end callback executes after `close_capture_runtime` drains accepted transcript and wire work. A stop failure preserves that run's directory.

Tier 1 is TM scratch under `~/.transport-matters`, separate from the Workdir's OS directory. Detected OS directories are never changed or removed. Created OS directory cleanup is governed by provenance in the later disk-provisioning slice.

Tests cover both assets under both modes:

- development preserves tier 1 and runtime-home
- production collects tier 1 and runtime-home

---

## 6. Slicing

| Slice | Deliverable |
| --- | --- |
| **S3-STEP-0** | Independent behavior-neutral extraction from the 693 line `space/store.py` |
| **S3a-ownership** | Rewrite schema, store, service, REST, MCP, and tests to N:1 ownership; delete the M:N surface; preserve provenance through detected Workdir inventory |
| **S3a-delete** | Detected Workdir and Space de-inventory, `default_worktree_id` clearing, historical IR retention, and managed run orchestration through `RunManagementPort` |
| **S3b** | `dev_mode`, development and CI defaults, runtime-home gating, and the run-end tier 1 teardown latch |
| **Later disk-provisioning** | Worktree create with `created` provenance plus clean-or-confirm created Workdir disk cleanup |

Every slice finishes with `just check` and `just test`. `just test-affected` is a local aid and never replaces the final gate.

Canvas nesting detail and create/move UX polish beyond these contracts belong to later slices. Created provenance disk cleanup and worktree create are deferred to disk provisioning; S3 delete handles detected workdirs through de-inventory.

---

## 7. Reuses existing machinery

| Capability | Existing owner | Do not invent |
| --- | --- | --- |
| Stop managed run | `RunManagementPort.terminate_run` through `RunRouteProxy` | New HTTP client or delete coordinator |
| List by Space/workdir | `RunManagementPort.list_runs` through `RunRouteProxy` | Process table scan |
| Teardown stack | `CapturedRunLease.close` + `_prepare_home_and_grant` ExitStack | Second lifecycle |
| Run storage path | `prepared.resolved_storage` / `run_root*` | New identity |
| Env bool flag | `Settings` + `env_keys` + `TRANSPORT_MATTERS_*` | Ad-hoc env |
| Tier 1 removal patterns | `storage.disk_helpers` within run teardown | Delete-time scratch traversal |
| Provenance authority | Existing `WorktreeProvenance`, record fields, and migration 0030 constraint | New enum or duplicate marker |
| Re-detection | Existing `SpaceStore.upsert_worktree` conflict update | Provenance overwrite |
| Future dirty check | Generalize `require_clean_worktree` from `certification_minting.py` | Third git-status caller |

---

## 8. Explicit non-goals

- Detached CLI in the stop and GC set
- Backend default Space, `is_default` delete enforcement, or a minimum one-Space constraint
- M:N link/unlink surface; membership is ownership
- Shared single workdir entity across Spaces
- Created-provenance disk cleanup plus worktree create are deferred to the disk-provisioning slice; S3 delete handles detected workdirs through de-inventory
- Removal or mutation of a detected OS directory
- Finalization or DB rebuild from tier 1
- Delete-time tier 1 collection
- Dangling tier 1 sweep. Rare crash or stuck-run leftovers are acceptable bounded scratch with no DB home and no replay path; `doctor` can reclaim them later if needed
- Full Canvas tree product (S4b)
- Workdir health/status (see §8A)

---

## 8A. Deferred: workdir health/status (separate slice)

**Out of workdir-CRUD / this S3.** Own slice later. cm: *DEFERRED intent: workdir health/status is a separate slice; status is a LOG not a snapshot*.

Headline principles only:

1. **Status is an append-only LOG** of health transitions. A mutable snapshot field on the workdir row is excluded.
2. **Health is a property of the OS dir** shared by all workdirs that point at it, delivered as a genuinely **live/streaming** signal. View-time recomputation is excluded.

Do not design the full status schema or stream surface here.

---

## 9. Review checklist for Stuart

- [ ] Backend permits 0..N equal, deletable Spaces; default behavior exists only in desktop UX
- [ ] UI and MCP bootstrap with `create_space`, then `create_workdir`
- [ ] Workdir owns one Space and uniqueness is `(space_id, canonical_os_path)`
- [ ] Existing provenance enum, record fields, migration constraint, and re-detection preservation are reused
- [ ] The M:N link/unlink surface is deleted
- [ ] S3 Workdir delete handles detected provenance through de-inventory only
- [ ] Space deletion applies each Workdir's provenance contract
- [ ] Created cleanup and worktree create remain paired in the later disk-provisioning slice
- [ ] Created cleanup uses clean removal and explicit dirty confirmation or refusal, with no silent `--force`
- [ ] `default_worktree_id` is cleared before the target workdir cascade
- [ ] Session, wire, transcript IR, and affinity stamps survive inventory deletion
- [ ] Managed runs stop through `RunManagementPort`; stop failures do not block the database mutation
- [ ] Tier 1 scratch cleanup remains separate from Workdir OS directory cleanup
- [ ] Tier 1 and runtime-home are preserved in development and collected in production
- [ ] No dangling sweep or delete-time filesystem path is introduced
- [ ] S3-STEP-0, S3a-ownership, S3a-delete, and S3b each gate on `just check` and `just test`

**Ready to implement only after Stuart sign-off.**
