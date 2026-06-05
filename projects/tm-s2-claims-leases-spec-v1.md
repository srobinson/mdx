# S2 — atomic claims, leases, immutable session affinity — build spec v1

Status: build-ready, tests-first. Heaviest / most-foundational slice; gates S4 + S6.
Date: 2026-07-23
Baseline: worktree reset onto `main` @ `d7bfb9ac` (S1 + Space-CRUD + Canvas-CRUD merged).
Model of record: cm `019f8a57`. Slice source: `~/.mdx/projects/tm-s2-s6-replan-architect.md` §S2.
Migration: **0031** (0030 consumed by the reshape). **New client-facing error code: NO** (§10).
**STEP 0 pre-split: NOT mandatory** (§1) — place claim-mint / pending-inventory in support modules and
`dao_statements` nets down under UPSERT→function, so no file crosses 700 by construction.
Reconciled against grok `~/.mdx/projects/tm-s2-reconciliation.md` (4 HOLD / 5 ADJUST + 2 owner rulings).
Governing rules: `CLAUDE.md` (refactor-before-add over 700; no fn >150; DRY), `TLDR.md`
("No production, no legacy: break freely" — reset schema, no backfill/shims).

> **grok is mapping the S2 integration surface (session stamps, launch/claim path, termination
> coordinator, capture_rpc, RunManager) in parallel.** §12 lists every integration assumption to
> reconcile against the real seams before the engineer builds. Treat §3-§9 contracts as the target;
> §12 flags where I inferred a seam I did not fully read.

## 0. Scope

Deliver the durable claim substrate that makes every run/terminal appear in inventory **before** any
external work, carry one immutable affinity stamp, and serialize its session write. Concretely:
preallocated `resource_id`; `runtime_resource_claim` + `worktree_lifecycle_lease` tables;
claim-before-preparation transaction; pending-inventory union; the canvas stamp group on `session`;
and the atomic `upsert_session_with_affinity` function with a durable conflict quarantine.

**Scope boundary (owner ruling, grok Finding 2): in-product runs only** — managed canvas/gateway runs
(via `CaptureLeaseRegistry.prepare_capture`) and plain terminals. **CLI-detached launches
(`cli/_helpers._prepare_captured_run`) are OUT of S2 scope** — see §0.1 Known gap.

Non-goals (later slices): Canvas delete (S4), Worktree delete/cleanup (S6). S2 builds the leases and
claim inventory those slices consume; it does not build the delete state machines — but S2's
lease/claim substrate must support **forced** termination/release, because those guards are advisory
(§8.1).

### 0.1 Known gap — CLI-detached runs (owner ruling)

The CLI-detached path `cli/_helpers._prepare_captured_run` calls `prepare_captured_run` **directly,
bypassing `CaptureLeaseRegistry`** (grok Finding 2). S2 does not thread a claim through it, so a
CLI-detached run **will not appear in claim inventory** and the S4/S6 delete guards will not see it
until a later slice threads the same claim API through the CLI path. This is an accepted gap for S2;
the orchestrator records it in the roadmap. Do not widen S2 to cover it.

## 1. STEP 0 — new-module placement, no mandatory pre-split (grok #9)

The claim/lease/coordinator **bulk lands in new modules**, so no existing file crosses 700 by
construction. There is **no mandatory pre-split**.

- `space/runtime_claims.py` (new) — durable claim + lease store and the claim transaction.
- `controlplane/run_termination.py` (new) — `RunTerminationCoordinator` extracted from
  `ControlPlaneService.close` (behavior-preserving; `service.py` 666 shrinks after the move).
- Migration `0031_runtime_claim_and_session_affinity.py` (new).

The two files grok re-measured stay under 700 **when built as directed** — do not pre-split them:

1. **`session/dao_statements.py` (677).** Replacing the ~37-line `UPSERT_SESSION_SQL` body with a
   ~5-8 line `upsert_session_with_affinity` call nets the file **down (≈653)**; the canvas stamp
   column group adds ~4-6. Only if the affinity-conflict SQL is co-located AND that pushes it over 700
   at build time, extract `session/session_affinity_sql.py` — measure, do not pre-split.
2. **`RunManager.ts` (664).** Thread `resourceId` only in-file (~+10-25). Put the resource-identity
   mint + pending-inventory helpers in `service/runManagerSupport.ts` (or a new
   `service/runtimeClaims.ts`) so the +40-80 LOC of claim/inventory logic does **not** land inline.
   Split further only if a measured in-file patch would exceed 700.

`space/store.py` (693) is untouched by S2 (claim/lease live in `runtime_claims.py`); its split remains
S4's STEP 0.

**Discipline:** if any measured in-file patch would cross 700, extract first (own commit) — but by
placing the bulk in new/support modules that case should not arise.

## 2. Migration 0031

Down revision `0030_space_crud_reset`. Destructive reset (drop+recreate affected tables), no backfill.

1. **`runtime_resource_claim`** keyed by the preallocated `resource_id` (uuid PK):
   `resource_kind (managed_run|plain_terminal)`, `run_id` (nullable, bound later), `owner`,
   `canvas_id` (nullable), `worktree_id`, `affinity_stamp` (jsonb, one immutable value),
   `state (pending|running|terminating|terminal|cancelled|failed)`, `worktree_lease_id`, timestamps.
   FK-free to `session`; owner-scoped. Index `(owner, worktree_id)` and `(owner, canvas_id)` for the
   delete-guard enumeration.
2. **`worktree_lifecycle_lease`**: `lease_id` PK, `owner`, `worktree_id`, `generation`,
   `resource_kind (capture|plain_terminal)`, `resource_id`, `canvas_id?`, `acquired_at`,
   `heartbeat_at`, `expires_at`, `cancel_requested`. Lock target is the `space_worktree` row.
3. **`session` canvas stamp group** (nullable, added to the recreated session family — `space_id`
   and `worktree_id` already exist from S1):
   `canvas_id uuid, parent_canvas_id uuid, canvas_name text, canvas_path jsonb, worktree_path text,
   worktree_branch_name text`. All FK-free. Add the complete-stamp-group CHECK and a partial
   `(owner, canvas_id, started_at DESC)` index.
4. **`session_affinity_conflict`** (FK-free): `conflict_id`, `session_id`, `owner`, `stored_stamp`,
   `incoming_stamp`, `incoming_run_id`, `source_descriptor?`, `conflict_digest`, `occurrence_count`,
   `first_seen_at`, `last_seen_at`. Unique `(session_id, conflict_digest)` so repeated poison input is
   one durable row. Session lookup index.
5. **`upsert_session_with_affinity`** DB function (§6) — the single apply/replay/conflict authority.

Drop `session` (+ `event`, `event_artifact` in dependency order) and recreate with the stamp group,
per the no-backfill charter. Artifact bytes survive (no session identity).

## 3. Durable claim + lease — `space/runtime_claims.py`

Typed shapes (frozen Pydantic / dataclass), mirroring re-plan §S2 and the original spec §4.2:

```text
PreallocatedRuntimeIdentity { resource_id: UUID }
WorktreeCaptureStamp { worktree_id; canonical_path; branch_name? }
CanvasCaptureStamp { canvas_id; parent_canvas_id?; canvas_name; canvas_path: tuple[CanvasPathSegment] }
SessionAffinityStamp { space_id: SpaceRef; canvas: CanvasCaptureStamp?; worktree: WorktreeCaptureStamp }
RuntimeResourceClaim { resource_id; resource_kind; run_id?; owner; canvas_id?; worktree_id;
                       affinity_stamp; state; worktree_lease_id; created_at; updated_at }
RuntimeResourceView { kind; resource_id; run_id?; owner; canvas_id?; worktree_id; state }
RuntimeResourceQuery { owner; anchor_worktree_id?; canvas_ids?; worktree_id?;
                       include_pending=true; include_terminal=false }
WorktreeLease { lease_id; owner; worktree_id; generation; resource_kind; resource_id; canvas_id?;
                acquired_at; heartbeat_at; expires_at; cancel_requested }
```

**Reshape re-scoping (D3):** `SessionAffinityStamp` gains an explicit **`space_id: SpaceRef`** — canvas
no longer implies a Space, so the durable Space selected at claim time is stamped directly (it is not
derivable from `canvas_id`, which appears in many Spaces).

Store methods: `preallocate_identity()`, `insert_pending_claim(...)`, `bind_run_id(resource_id, run_id)`,
`transition_claim(resource_id, state)`, `acquire_lease(...)`, `release_lease(...)`,
`heartbeat_lease(...)`, `list_resources(RuntimeResourceQuery)`.

## 4. Claim-before-preparation flow (re-scoped to the model)

Every managed run and plain terminal mints `resource_id` and inserts its `RuntimeResourceClaim` +
`WorktreeLease` **before** filesystem prep, capture prep, gateway creation, or spawn. The claim
transaction:

1. Lock the `space_worktree` row and verify `active` lifecycle.
2. **(D1) Take the `(owner, anchor_worktree_id)` tree lock** (reuse `store.lock_owner_scope` — the
   `pg_advisory_xact_lock(hashtextextended(...))` precedent), **not** a Space lock.
3. **(reshape) Owner-scoped authz only — DROP the "verify Space membership" step.** Placement is
   owner-scoped (cm `019f8a57`); the check collapses to owner + anchor-worktree existence. For a
   nonnull `canvas_id`, verify the canvas path + that it anchors on this worktree and reject a frozen
   delete member (S4 hook).
4. Read Canvas path + Worktree canonical path + branch under the locks.
5. Build ONE immutable `SessionAffinityStamp` (with `space_id`).
6. Insert the pending claim + lease atomically; commit before any external work.

**(D4) Missing-launch rejection reads projected `missing` at action time and fails closed.**
`launch_resolution.resolve_run_worktree` already does this (`resolved.missing is not False` →
`worktree_unavailable` 409; non-`active` lifecycle → `worktree_unavailable`). The claim reuses that
resolution; a temporary inability to enrich Git facts fails closed for launch.

Failure before registration marks the exact claim `failed` and releases its lease. Runtime
registration **binds** the later `run_id` onto the existing claim (`bind_run_id`), never mints
identity or affinity. A plain terminal uses `resource_id` as its `sessionId`.

## 5. Immutable affinity stamp + session stamp group

`session.space_id` + `session.worktree_id` already exist (S1) and are COALESCE-preserved in the
current upsert. S2 adds the **canvas stamp group** (`canvas_id`, `parent_canvas_id`, `canvas_name`,
`canvas_path`, `worktree_path`, `worktree_branch_name`) sourced from the SAME claim stamp. Extend
`session.models:SessionRow` + `SessionBinding`, `session.dao_statements:SESSION_COLUMN_NAMES`, and the
proxy binding carriers (`shared_proxy.binding:ProxyRunBinding`,
`shared_proxy.models:SharedProxyBindingPayload`). `session.ingest:build_session` **builds** the
`SessionRow` from `SessionBinding` — it is **not** an upsert caller (grok #5); the write happens in
`SessionWriter._commit_batch` via `AsyncSessionDao.upsert_session`, which S2 routes to the new function
(§6). No adapter recomputes a Canvas path, Worktree path, or branch after the claim transaction.

### 5.1 Backfill reconcile — the legitimate partial stamp (owner ruling, grok Finding 1)

`backfill_session_spaces` **stays** (do not retire it). It is the live startup routine that assigns
Space/Worktree identity to sessions that are **missing** it, by resolving their recorded `cwd` — it is
how imported/historical transcript sessions get a space/worktree stamp. It writes via
`update_session_space_identity` (`UPDATE_SESSION_SPACE_IDENTITY_SQL`), a **second stamp writer** that
today force-fills `space_id`/`worktree_id`.

The load-bearing reconcile: a backfill-stamped session carries **`space_id` + `worktree_id` present,
canvas group absent**. This is a **legitimate partial**, not a conflict — it is the affinity model's
own "install-when-absent" case, and later live-ingest canvas facts **complete** it. S2 must:

1. Make `update_session_space_identity` **fill-when-absent only** (never overwrite an existing
   `space_id`/`worktree_id`), aligning it with the affinity function's immutability rule, OR route it
   through the same install-when-absent guard. It must not overwrite a stamp the claim path installed.
2. Define the "space/worktree present, canvas absent" state as a **valid completable partial** so the
   affinity function's conflict branch (§6) never quarantines it. Canvas facts arriving later install
   the canvas group onto that row and return `applied`, not `affinity_conflict`.

## 6. Atomic `upsert_session_with_affinity` (replace `UPSERT_SESSION_SQL`)

`session.dao_statements:UPSERT_SESSION_SQL` becomes one call to the DB function. Inside it: take a
transaction-scoped advisory lock for `session_id`, lock the existing row when present, then execute
exactly one branch, returning `SessionUpsertOutcome { status: applied|replayed|affinity_conflict;
session?; conflict_id? }`:

1. Insert a new Session with its complete stamp → `applied`.
2. Update a Session with **no stored stamp**, installing the complete stamp atomically → `applied`.
3. **Backfill completion (grok Finding 1):** stored row has `space_id` + `worktree_id` present and
   canvas group **absent** (the backfill/S1 partial), and the incoming stamp's `space_id` +
   `worktree_id` **match** the stored values → install the canvas group onto the row → `applied`. This
   is completion, never a conflict.
4. Ordinary upsert for an exactly-equal stamp → `replayed`.
5. **Genuine conflict only** → incoming `space_id`/`worktree_id` differ from a stored non-null value,
   OR incoming canvas facts differ from an already-installed canvas group. Leave the Session row
   unchanged, insert/increment `session_affinity_conflict`, return `affinity_conflict` + `conflict_id`.

The "space/worktree present, canvas absent" state is explicitly **not** treated as a partial conflict;
only a value mismatch against an already-stored non-null field quarantines. The DAO commits the
function outcome and surfaces a typed conflict to ingestion. Concurrent writers
serialize inside the function and cannot combine Canvas facts from one tree version with Worktree
facts from another. Reparent, rename, move, and hard delete issue **no** session-stamp update.

## 7. Pending-inventory union + anchor-scoped enumeration

`RuntimeResourcePort.list_resources` unions durable `runtime_resource_claim` rows,
`RunManager.pendingCreates`, registered runs (`RunManager.list`), and `PlainTerminalSessions`,
deduplicated by `resource_id`. Durable claims are authoritative for the pre-gateway window, so no
create escapes Canvas/Worktree delete enumeration.

**(D1)** `RuntimeResourceQuery` grows `anchor_worktree_id`; the Canvas-delete-guard (S4) enumerates by
**anchor worktree**, not by Space. Canvas-scoped enumeration resolves `canvas_ids` within one anchor.

## 8. Termination coordinator — `controlplane/run_termination.py`

Extract the fanout + receipt behavior from `ControlPlaneService.close` (`controlplane/service.py`) into
`RunTerminationCoordinator`. Existing close and both later delete flows (S4/S6) use it. Reuse
`RunManagementPort.terminate_run` (`controlplane/activity.py`), `RunRouteProxy.terminate_run`,
`RunManager.terminate`. This is a behavior-preserving extraction plus a reusable seam; S2 ships the
coordinator, S4/S6 consume it.

### 8.1 Forced termination/release — the substrate for advisory delete guards (owner ruling)

The S4/S6 delete guards are **advisory and overridable**, not hard blocks: a user can force-kill a
busy Canvas/Worktree ("Canvas A is busy" → "force kill" proceeds). S2 does not build that UX, but its
lease/claim model **must support the forced path** so S4/S6 can build on it. Confirm the substrate
covers forced termination end to end:

- `worktree_lifecycle_lease.cancel_requested` can be set to signal an in-flight claim to abort.
- `RunTerminationCoordinator` force-terminates active/registered claims (managed runs + plain
  terminals) via the reused `terminate_run` / `RunManager.terminate` fanout.
- Lease **release** and claim transition to `cancelled`/`terminal` complete even when the resource was
  mid-flight, so a delete that force-terminates active claims leaves no dangling lease.

Add a note for the engineer: **S4/S6 build the force-kill flow on this substrate**; S2 only proves the
lease/claim/coordinator primitives support forced termination and release (see §11 forced-release
test).

## 9. Cross-language contract

Thread nullable `canvasId` + required `resourceId` through the run-create surfaces (per original spec
§7.1 field list): `LaunchRequest`/`GatewayCreateRunRequest`, `_NormalizedLaunchRequest`/`_PreparedLaunch`,
`runtimeRouter:CreateRunBody`, `runManagerTypes:CreateManagedRunInput`/`ManagedRunFilters`,
`ports:PrepareCaptureInput`, `captured_run_models:CapturedRunRequest`,
`capture_rpc_routes:PrepareCaptureRequest`, `capture_rpc:_CaptureRunFacts`, `runtimeRun:RuntimeRunView`,
`transport:RunView`.

- `RunManager.createNew` gains a required internal `identity` argument; `PrepareCaptureInput`/
  `PrepareCaptureRequest`/`_CaptureRunFacts` gain required `resourceId`.
- `PlainTerminalSessions.open` mints `resource_id` first, obtains the claim + lease, threads identity
  through spawn/registration/close/lease-release; claim failure produces no PTY.
- Browser HTTP/WS callers never supply `resourceId`; Runtime mints it. Public `RunManager.create` /
  `createWithDisposition` input signatures otherwise unchanged.
- `LAUNCH-CONTRACT.md` gains optional `canvas_id` on `LaunchRequest` and one optional `affinity_stamp`
  on `FrozenLaunchSpec`; canonical serialization includes explicit null for unassigned Canvas affinity.
- Contract fixtures prove Python↔Node serialization both directions; no compatibility decoder for
  pre-claim runs (no legacy).

## 10. Error semantics — no new client-facing code (justified)

Claim failures collapse to existing codes: worktree in `deleting`/inactive/`missing` →
`worktree_unavailable` (409, already emitted by `launch_resolution`, fails closed); unknown worktree →
`worktree_not_found` (404); non-Director where applicable → `forbidden`. The **affinity conflict is not
a request rejection** — it is a durable quarantine outcome surfaced as
`SessionUpsertOutcome.status=affinity_conflict` to the ingestion path (transcript tailer / backfill),
which is not an HTTP client. Therefore **no new API error code**. If grok's integration map shows a
run-create surface that must report "claim lost to concurrent delete" as a distinct client action, a
`worktree_deleting` code could be added then — flag, do not pre-add.

## 11. Tests-first plan (all red-first; assert OBSERVABLE end-state)

**STEP 0:** existing suite green post-extraction; `session/session_affinity_sql.py` + the
`runManagerSupport.ts`/`runtimeClaims.ts` split leave behavior identical; import-graph tests pass.

**Migration (`session/test_migrate` + schema invariants):** empty reset reaches head; the four new
objects exist with the stamp-group CHECK, conflict uniqueness, claim/lease keys, and **no** session
affinity FK.

**Claim / lease (`space/test_runtime_claims.py`):**
- managed identity + pending claim exist **before** capture preparation (assert inventory shows the
  resource before any prep call).
- idempotent replay reuses the stored identity; a second idempotent create does not mint a new one.
- terminal identity exists **before** CWD resolution and spawn.
- claim failure spawns nothing; spawn failure marks the exact claim `failed` and releases its lease.
- no pre-gateway inventory gap: `list_resources` returns the pending resource across the union.
- **delete-vs-claim race:** a claim taken while a worktree flips to `deleting` fails closed
  (`worktree_unavailable`), lease not granted.
- **anchor-scoped enumeration:** `RuntimeResourceQuery(anchor_worktree_id=…)` returns exactly that
  anchor's claims.
- **forced release (§8.1):** setting `cancel_requested` + running the coordinator force-terminates an
  active managed claim and an active plain-terminal claim, transitions each to `cancelled`/`terminal`,
  and releases its lease with no dangling lease row.

**Affinity (`session/test_session_affinity.py`):**
- null and UUID canvas affinity round-trip; single and batch launch produce the same stamp shape.
- tree-consistent stamp (Canvas path + Worktree path/branch from one claim).
- equal replay → `replayed`, no conflict row.
- conflicting upsert leaves the Session row byte-unchanged and commits exactly one
  `session_affinity_conflict`; repeated poison increments `occurrence_count` on one row.
- concurrent conflicting writers serialize inside the function (no mixed Canvas/Worktree facts).
- reparent/rename/move/delete issue no session-stamp update (assert stamp survives a canvas rename).
- **backfill completion (§5.1/§6, Finding 1):** a session with `space_id`+`worktree_id` present and
  canvas group absent (backfill state), given incoming canvas facts whose `space_id`/`worktree_id`
  **match**, returns `applied` (canvas group installed), **not** `affinity_conflict` — no conflict row.
- **backfill fill-when-absent:** `update_session_space_identity` installs identity on an absent-stamp
  session but does **not** overwrite an existing `space_id`/`worktree_id` (assert a claim-installed
  stamp survives a later backfill pass).
- a genuine `space_id`/`worktree_id` value mismatch still quarantines (one conflict row).

**Cross-language (`contract fixtures`, both directions):** Python and Node `resourceId` + nullable
`canvasId` signatures; `affinity_stamp` serialization with explicit null.

Every case asserts observable end-state (inventory contents, durable row contents, `SessionRow`
after upsert), never an intermediate mapping.

## 12. Integration seams — reconciled (grok `tm-s2-reconciliation.md`: 4 HOLD / 5 ADJUST)

1. **HOLD.** `ControlPlaneService.close` (`controlplane/service.py`) is the sole multi-run
   control-plane fanout — director-only, workspace-scoped, `asyncio.gather` of `_close_target` →
   `gateway.terminate_run`. Extract it to `RunTerminationCoordinator`; reuse `terminate_run` /
   `RunManager.terminate`. No second multi-run close path.
2. **ADJUST.** The managed/canvas claim boundary is **`CaptureLeaseRegistry.prepare_capture`** (called
   from `RunManager.createNew` → `capturePort.prepareCapture` → `capture_rpc_routes.prepare_capture`).
   `_CaptureRunFacts` + `CaptureLeaseRegistry._leases` is the in-memory registry; S2 binds a durable
   lease id into `_CaptureRunFacts`. **The CLI path `cli/_helpers._prepare_captured_run` calls
   `prepare_captured_run` directly and BYPASSES the registry** → out of S2 scope (§0.1). Note: the
   process `CapturedRunLease` is **not** the durable `WorktreeLease` — do not conflate them.
3. **HOLD.** `RunManager.createWithDisposition` (public + idempotency), `createNew` (prepareCapture +
   spawn + register), `PendingCreate`/`pendingCreates` (keyed `${owner} ${idempotencyKey}`) are
   the mint sites + pending-inventory source. `CreateManagedRunInput` / `PrepareCaptureInput` /
   `runtimeRouter` create body carry **no `resourceId`** today; Runtime mints it server-side.
4. **ADJUST.** `PlainTerminalSessions.open` (154 LOC) has **no** claim, lease, identity, **or
   cancellation checks today** (order: `resolveCwd` → `ptyPort.spawn` → random-UUID `sessionId` →
   register). S2 **inserts** the claim + two cancel checks **between `resolveCwd` and `spawn`**, and
   rebinds `sessionId` to the minted `resource_id` (greenfield, not an existing field).
5. **ADJUST (keep-and-reconcile).** The only production upsert caller is
   `SessionWriter._commit_batch` via `AsyncSessionDao.upsert_session` (which S2 routes to the new
   function). **`build_session` is a builder, not an upsert caller.** A **second stamp writer exists**:
   `update_session_space_identity` (`backfill_session_spaces`) — it **stays** (owner ruling, §5.1) and
   must become fill-when-absent so it aligns with the affinity immutability rule and its
   space/worktree-only stamp is a completable partial, not a conflict (§6).
6. **ADJUST.** `resolve_launch_worktree(worktree_id, owner, space_id=None)` yields owner-scoped durable
   existence (default computed-all membership). Claim authz collapses to **owner + worktree existence
   (+ canvas anchor check when `canvas_id` set)** and reuses `resolve_run_worktree` for the
   fail-closed `missing` guard. **Drop the Space MEMBERSHIP check only — KEEP the `space_id` stamp**
   on the affinity record (D3: canvas no longer implies Space; stamp the Director-selected or default
   Space).
7. **HOLD.** Session PK is `session_id` (mig 0001, text PK); the affinity function's transaction-scoped
   advisory lock keys on it. No existing session-upsert advisory lock (greenfield inside the function).
8. **HOLD (proxy plane).** `shared_proxy.binding:ProxyRunBinding` + `shared_proxy.models:
   SharedProxyBindingPayload` carry `space_id`/`worktree_id` today; the canvas group is greenfield on
   both. Non-proxy carriers (`SessionBinding`, `SessionRow`, `_CaptureRunFacts`, `CapturedRunRequest`,
   `RuntimeRunView`, launch inputs) are threaded separately (§5, §9).
9. **ADJUST (no mandatory STEP 0).** Measured: `dao_statements.py` nets **down** (677 → ≈653) under
   UPSERT→function, so no split needed unless the affinity-conflict SQL is co-located and crosses 700.
   `RunManager.ts` (664) stays under 700 **if** claim-mint + pending-inventory land in
   `runManagerSupport.ts` / new `runtimeClaims.ts` (as §1 directs), not inline. `store.py` untouched.

## 13. Gate

- Engineer + reviewers: `just check` + `just test-affected`.
- Grok local-CI (tree idle): `just check` + `just test` + `just migration-smoke` (proves the 0031
  reset applies cleanly to head).

Bounded: bulk in new modules; STEP 0 keeps `dao_statements.py` / `RunManager.ts` under 700; no
function exceeds ~150 lines. Cite file+symbol, never file:line.
