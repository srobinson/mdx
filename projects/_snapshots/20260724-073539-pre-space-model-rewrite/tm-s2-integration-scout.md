# S2 integration scout (claims / leases / immutable session affinity)

Date: 2026-07-23  
Tree: `feat/multi-launch` @ `d7bfb9ac` (post S1 + named Space-CRUD #317 + Canvas create/update #318)  
Scope: ground the S2 spec (mig **0031**) in the real integration surface. Read-only.  
Inputs: re-plan `~/.mdx/projects/tm-s2-s6-replan-architect.md` §S2; live symbols below.

Verdict key:

- **GREENFIELD**: S2 substrate/symbol does not exist; build net-new.
- **PARTIAL**: related surface exists but is not the S2 contract (must extend or replace carefully).
- **LIVE (ride)**: already shipped; S2 consumes without reinventing.

---

## Executive split

| Touchpoint | Status | Primary symbol + file |
|------------|--------|----------------------|
| 1. Session stamps `space_id` / `worktree_id` | **PARTIAL** | `SessionRow`; `UPSERT_SESSION_SQL`; mig 0006 + 0030 text cast |
| 1b. Canvas-stamp columns (`canvas_id`/`canvas_path`/`worktree_path`/`worktree_branch`) | **GREENFIELD** | absent on `session` and models |
| 1c. Session write path (`upsert_session`) | **PARTIAL** | `AsyncSessionDao.upsert_session` → `SessionWriter._commit_batch` |
| 1d. Immutable affinity upsert | **GREENFIELD** | no `upsert_session_with_affinity` |
| 2. Launch worktree resolve | **LIVE (ride)** | `resolve_run_worktree` / `resolve_launch_worktree` |
| 2b. Claim-before-preparation + preallocated `resource_id` | **GREENFIELD** | prepare runs without durable resource claim |
| 3. Termination fanout | **PARTIAL** | `ControlPlaneService.close` (no claim inventory / coordinator) |
| 4. Projected missing guard | **PARTIAL (LIVE at launch)** | `launch_resolution` rejects `missing is not False` |
| 4b. Projected `is_primary` guard | **GREENFIELD** (S6 consumer; projected field LIVE) | field exists; no action-time gate |
| 5. `runtime_resource_claim` / `worktree_lease` / affinity SQL | **GREENFIELD** | zero hits in tree |
| 6. STEP 0 LOC | **RISK** | `space/store.py` **693**/700 |

**Count:** 6 brief MAP items expanded → **3 LIVE-ride / 4 PARTIAL / 5 GREENFIELD** core seams (with name-collision traps noted below).

---

## 1. SESSION table / store

### Current columns (session)

Foundation mig `0001_session_store_foundation` + later:

| Column group | Origin | Shape today |
|--------------|--------|-------------|
| Core identity | 0001 | `session_id` PK, provider, harness, run_id, cwd, workspace_slug/hash, native_session_id, minted, source_descriptor, home_dir, owner, status, title, parent/fork, timestamps |
| Purpose / visibility / template | 0004–0005 | `session_purpose`, `session_visibility`, `template_provenance` |
| **Space stamps** | **0006** add; **0030** casts `space_id` → **text** | `space_id text` (FK-free `SpaceRef`), `worktree_id uuid` (FK-free) |
| Indexes | 0006 | `session_space_ix (owner, space_id, …)`, `session_worktree_ix (owner, worktree_id, …)` partial |

**Canvas-stamp columns do not exist** on `session`:

- no `canvas_id`
- no `canvas_path`
- no `worktree_path`
- no `worktree_branch`

Same for models: `SessionRow` / `SessionBinding` only carry optional `space_id` + `worktree_id`.

### `run_lifecycle_event` stamps (sibling)

Mig 0007: `space_id`, `worktree_id` (uuid originally).  
0030: `space_id` → **text**. Still FK-free claim-time recording via `run_lifecycle.py` / capture facts. Not session affinity, but S2 inventory must not confuse the two stamp surfaces.

### Model surface

```text
SessionRow.space_id: SpaceRef | None     # session/models.py
SessionRow.worktree_id: WorktreeId | None
SessionBinding.space_id / worktree_id    # index/adapters/base.py  (feeds build_session)
```

### Where sessions are WRITTEN

| Path | Symbol | File | What it writes |
|------|--------|------|----------------|
| Live transcript commit | `SessionWriter._commit_batch` → `dao.upsert_session` | `session/writer.py` (~682 LOC) | Every tailer/ingest batch upserts the session row first |
| Batch construction | `build_session(SessionBinding)` | `session/ingest.py` | Copies binding stamps into `SessionRow` |
| Binding sources | Claude/Codex adapters; `addon_runtime` wire register | `index/adapters/*`, `addon_runtime.py` | `space_id`/`worktree_id` from run binding when present |
| Startup backfill | `backfill_session_spaces` → `update_session_space_identity` | `session/backfill.py` | Force-sets missing stamps from cwd resolve (NOT first-write-only) |
| Lifecycle (not session) | `emit_run_lifecycle` / capture facts | `run_lifecycle.py`, `capture_rpc.py` | `run_lifecycle_event` stamps |

### Current upsert path S2 extends/replaces

**SQL authority:** `UPSERT_SESSION_SQL` in `session/dao_statements.py` (~677 LOC):

```sql
INSERT INTO "session" (…, space_id, worktree_id, …)
ON CONFLICT (session_id) DO UPDATE SET
  …
  space_id    = COALESCE(EXCLUDED.space_id, "session".space_id),
  worktree_id = COALESCE(EXCLUDED.worktree_id, "session".worktree_id),
  …
```

Semantics today:

- **Fill-if-null only when the new value is non-null preferred:** `COALESCE(EXCLUDED, existing)` means a later non-null EXCLUDED **overwrites** an existing stamp.
- Not immutable claim-time affinity.
- Parallel path `UPDATE_SESSION_SPACE_IDENTITY_SQL` **always overwrites** (backfill).

**Python:** `AsyncSessionDao.upsert_session` (`session/async_dao.py`) is the single DAO entry. S2’s `upsert_session_with_affinity` should either:

1. replace this SQL for stamp columns (first-write-wins + conflict on mismatch), or  
2. sit beside it as a claim-time-only path that launch/session mint must call, leaving event-path upserts non-authoritative for stamps.

Architect note: re-plan says “one immutable affinity stamp.” Live code has **fill-or-overwrite COALESCE**, not that contract.

### S2 column work (0031)

| Column | Status | Action |
|--------|--------|--------|
| `space_id` text | PARTIAL LIVE | Keep; harden immutability |
| `worktree_id` uuid | PARTIAL LIVE | Keep; harden immutability |
| `canvas_id` | GREENFIELD | ADD |
| `canvas_path` | GREENFIELD | ADD (type TBD: text / jsonb path segments) |
| `worktree_path` | GREENFIELD | ADD (snapshot of path at claim) |
| `worktree_branch` | GREENFIELD | ADD (projected branch snapshot at claim; not durable worktree col) |

No FK to `space` / `space_worktree` / `canvas` (reshape: stamps survive delete).

---

## 2. LAUNCH / CLAIM path

### What is LIVE (worktree resolve, not resource claim)

Shared front door: `api/v1/launch_resolution.py`

```text
resolve_run_worktree(request, worktree_id, owner, space_id?)
  → SpaceCrudService.resolve_launch_worktree
  → ProjectedWorktree via _project_one
  → guards (see §4)
```

`SpaceCrudService.resolve_launch_worktree` (`space/service.py`):

1. Load durable `StoredWorktree` (require path).
2. If `space_id` omitted → default Space + `worktree_in_space` membership check.
3. If `space_id` given → space existence only (named Space is view context; placement remains owner-scoped).
4. Project runtime facts; return `ResolvedWorktree` (`space_id`, `worktree_id`, `root_canvas_id`, `cwd`, workspace slug/hash, `lifecycle_state`, `missing`, `repo_group_key`).

### Capture / prepare hook-in

`api/v1/capture_rpc_routes.py` → `_resolved_domain_request`:

```text
if directory is None and worktree_id is set:
    resolve_run_worktree(...)
    domain.directory / space_id / worktree_id ← ResolvedWorktree
→ CaptureLeaseRegistry.prepare_capture
→ prepare_captured_run(...)   # process/port lease, not WorktreeLease
```

`capture_rpc.CaptureLeaseRegistry` stores in-memory `_leases[run_id]` (`CapturedRunLease`) + `_CaptureRunFacts` including optional `space_id`/`worktree_id`, emits `RUN_STARTED` after registration.

### Where S2 claim-before-preparation hooks

Today’s order:

```text
resolve worktree → prepare_captured_run (ports/proxy/home) → register lease → lifecycle RUN_STARTED
```

S2 desired order (from re-plan):

```text
resolve worktree + projected guards
→ atomic claim txn (RuntimeResourceClaim + WorktreeLease + preallocated resource_id)
→ prepare_captured_run (must use preallocated resource_id)
→ register / lifecycle
```

**Hook points (greenfield inserts):**

| Step | File | Notes |
|------|------|-------|
| Pre-prepare claim | `capture_rpc_routes._resolved_domain_request` and any Python run-create route using `resolve_run_worktree` | After resolve, before `prepare_capture` |
| Service authority | **new** module (do **not** grow `space/store.py`) | `claim_runtime_resource` / lease insert |
| Launch ledger | `controlplane/launch_ledger.py` | **Name collision only** — process dispatch idempotency, not resource claim |
| Control-plane launch | `controlplane/launch_service.py` | Uses ledger claim + gateway spawn; may need same resource claim if it places into canvas worktrees |

### Preallocated `resource_id`

**GREENFIELD** for S2’s durable runtime resource identity.

Do not confuse with:

| Existing “resource” | Meaning | File |
|---------------------|---------|------|
| Timeline `resource_id` | transcript/wire content handle | `session/resource_ids.py`, `timeline_resources.py` |
| `CapturedRunLease` | in-process port/proxy cleanup | `captured_run_models.py` |
| Launch ledger claim | dispatch_id idempotency | `controlplane/launch_ledger.py` |

---

## 3. TERMINATION / close fanout

**LIVE (PARTIAL vs S2 inventory needs):**

`ControlPlaneService.close` — `controlplane/service.py:338` (~666 LOC file):

```text
require_director
normalize run_ids (dedupe)
read_workspace_activity(workspace_id) → known set  OR shared failure reason
asyncio.gather(_close_target per run_id)
  → gateway.terminate_run(run_id, owner=…)
  → ManageResult(closed|failed|unknown)
audit manage action + CloseResult(dispatch_id, receipts)
```

Properties:

- Workspace-scoped fanout (grant workspace); unknown runs fail closed without gateway touch.
- Concurrent per-target terminate; no shared transaction across targets.
- **No** query of durable resource claims / worktree leases.
- **No** `RunTerminationCoordinator` type (S4/S6 extract target).
- Process capture release is separate: `CaptureLeaseRegistry` close/release path closes `CapturedRunLease` and emits `RUN_EXITED`.

**S2 alignment requirement:** claim inventory must be queryable by run_id / canvas anchor / worktree so later S4 freeze and S6 delete can enumerate pending managed runs. Close fanout should eventually release or observe those claims; today it only talks to the gateway.

---

## 4. PROJECTED guards at action time

### Missing (launch) — **PARTIAL LIVE**

`resolve_run_worktree` (`launch_resolution.py`):

```text
lifecycle_state must be ACTIVE          → durable column (not projected)
missing is not False                    → projected (True or None both 409 worktree_unavailable)
```

Fail-closed for enrichment failure: `ProjectedWorktree.missing is None` when detection inconclusive → launch rejected. Matches re-plan D4 for **missing-launch**.

Projection path: `resolve_launch_worktree` → `_project_one` → `project_worktree` + `detect_space` / missing detection.

### `is_primary` — projected field LIVE, **guard GREENFIELD**

- Present on `ProjectedWorktree` / `WorktreeRecord` / detection.
- **No** launch or delete guard reads it today (primary-delete-always-fails is S6).
- S2 must keep projection available; primary policy is not S2’s gate unless claim policy wants it.

### Other guards already present

| Guard | Source | Projected? |
|-------|--------|------------|
| Worktree not found / no path | store | durable |
| Not active lifecycle | `lifecycle_state` | durable |
| Membership (default path) | `worktree_in_space` | durable predicate |
| Missing checkout | projection | **yes** |

---

## 5. EXISTING claim / lease / affinity substrate

Confirmed **absent** (repo-wide symbol search @ `d7bfb9ac`):

| Spec name | Present? |
|-----------|----------|
| `runtime_resource_claim` table / type | **NO** |
| `worktree_lease` / `worktree_lifecycle_lease` | **NO** |
| `session_affinity_conflict` | **NO** |
| `upsert_session_with_affinity` | **NO** |
| Atomic claim txn taking `(owner, anchor_worktree_id)` tree lock | **NO** (space store has `lock_owner_scope` advisory for mutations; not claim inventory) |
| Pending claim inventory union for delete-guard | **NO** |

**False friends (do not reuse as S2 substrate):**

| Name | Real role |
|------|-----------|
| `LaunchLedger.claim` | Control-plane launch dispatch idempotency |
| `CapturedRunLease` / `CaptureLeaseRegistry` | Process-local port/proxy lease |
| `UPSERT_SESSION` COALESCE stamps | Soft fill, not immutable affinity |
| Timeline `resource_id` | Content artifact IDs |

Re-plan statement “all S2–S6 substrate absent” remains **true for S2 claims/leases/affinity**. (Space-CRUD and S3 canvas create **have** since shipped; that does not materialize S2 tables.)

---

## 6. LOC / STEP 0 risk

Hard limit: **700 lines/file** (project rule). Measured @ `d7bfb9ac`:

| File | LOC | S2 pressure | Recommendation |
|------|-----|-------------|----------------|
| **`space/store.py`** | **693** | **CRITICAL** | **Do not add claim/lease tables here.** New `session/` or `runtime/` store module. STEP 0 if any space-store touch is required: extract first. |
| `session/writer.py` | 682 | HIGH | Affinity write should stay thin; avoid bulk logic |
| `session/dao_statements.py` | 677 | HIGH | New SQL constants may force split (`dao_statements_session.py` / affinity module) |
| `controlplane/service.py` | 666 | MED | Close stays; claim release later; extract coordinator in S4 |
| `space/service.py` | 594 | MED | Already hosts Space-CRUD + canvas; claim should not land here |
| `session/async_dao.py` | 475 | OK for `upsert_session_with_affinity` method |
| `api/v1/launch_resolution.py` | 86 | OK to add claim call-out or keep pure resolve |
| `capture_rpc.py` / `capture_rpc_routes.py` | 489 / 509 | OK for hook wiring |

**STEP 0 risk file: `api/src/transport_matters/space/store.py` (693).**  
S2 production symbols should land in **new files** (e.g. `session/affinity.py`, `runtime/claims.py`, mig `0031_…`) plus minimal call-site hooks.

---

## Integration map (who calls what today)

```text
UI / gateway / MCP launch
        │
        ▼
capture_rpc_routes._resolved_domain_request
        │  resolve_run_worktree  ──►  SpaceCrudService.resolve_launch_worktree
        │                               │  store.get_worktree (durable)
        │                               │  project missing/branch/primary
        │                               └  lifecycle ACTIVE + missing fail-closed
        ▼
CaptureLeaseRegistry.prepare_capture
        │  prepare_captured_run → CapturedRunLease (ports)
        │  RUN_STARTED (space_id/worktree_id facts if known)
        ▼
Transcript tailer / wire register
        │  SessionBinding(space_id?, worktree_id?)
        │  build_session → SessionWriter → UPSERT_SESSION (COALESCE stamps)
        ▼
ControlPlaneService.close
        │  workspace activity scope → gateway.terminate_run fanout
        └  (no claim inventory)
```

S2 inserts durable claim/lease **between resolve and prepare**, and affinity-hardening **at first session mint / claim stamp**, not on every event upsert overwrite.

---

## What S2 must build vs ride

### Ride (do not reimplement)

- `worktree_in_space` + owner-scoped placement simplification (re-plan D2/D3)
- `ProjectedWorktree.missing` / detection projection
- `resolve_launch_worktree` / `resolve_run_worktree` front door
- FK-free stamp philosophy on session + lifecycle
- Anchored canvas (`anchor_worktree_id`) for future tree locks (claim txn re-scope target)
- `ControlPlaneService.close` fanout shape (extend later; extract in S4)

### Build (greenfield)

- Migration **0031**: claim + lease tables; session canvas-stamp columns
- Atomic claim txn + preallocated `resource_id`
- `WorktreeLease` / `RuntimeResourceClaim` inventory
- `upsert_session_with_affinity` (immutable first stamp; conflict on mismatch)
- Hook claim before `prepare_captured_run`
- Pending inventory readable by close/delete slices

### Harden (partial)

- Session stamp COALESCE → true immutability (and decide fate of `update_session_space_identity` backfill vs affinity rules)
- Launch missing guard already fail-closed; keep that contract in claim path too
- Name isolation from LaunchLedger / CapturedRunLease / timeline resources

---

## Architect assumptions (re-plan §5) — recon status @ d7bfb9ac

| # | Assumption | Status now |
|---|------------|------------|
| 1 | Junction add/remove reserved | **STALE** — Space-CRUD shipped (`add_worktree_link` / `space_mutations`) |
| 2 | `_insert_user_canvas` production-intended | **CONFIRMED** — S3 built `create_canvas` on store insert |
| 3 | Session has FK-free space_id + worktree_id only | **CONFIRMED** — canvas stamps still missing |
| 5 | `ControlPlaneService.close` unchanged by reshape | **CONFIRMED** — gateway fanout only |
| S2 substrate absent | claims/leases/affinity | **CONFIRMED** |

---

## Suggested S2 file plan (non-binding, LOC-safe)

```text
api/migrations/versions/0031_runtime_claims_affinity.py   # GREENFIELD
api/src/transport_matters/runtime/claims.py               # or session/affinity_store.py
api/src/transport_matters/session/affinity.py             # upsert_session_with_affinity
# hooks only:
api/src/transport_matters/api/v1/launch_resolution.py     # optional guard export
api/src/transport_matters/api/v1/capture_rpc_routes.py    # claim-before-prepare
api/src/transport_matters/session/dao_statements.py       # or split if >700
# AVOID growing:
api/src/transport_matters/space/store.py                  # 693 — STEP 0 extract if touched
```

---

## One-line for orchestrator

**6 touchpoints mapped: session stamps PARTIAL (space/worktree only; canvas stamps GREENFIELD); launch resolve LIVE; claim/lease/affinity GREENFIELD; close fanout PARTIAL; missing guard LIVE fail-closed; STEP 0 risk `space/store.py` 693; `~/.mdx/projects/tm-s2-integration-scout.md`.**
