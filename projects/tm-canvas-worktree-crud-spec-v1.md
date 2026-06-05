# Canvas and Worktree CRUD foundation v1

Status: build ready specification  
Date: 2026-07-22  
Baseline: `feat/multi-launch` at `b094e80d69ad7d57c5bba0ff8f4d71a986a837f2`  
Governing contract: `LAUNCH-CONTRACT.md`  
Current Alembic head: `0029_native_connection_origin`  
First migration: `0030_space_crud_reset`

## 1. Scope

Version one delivers full Canvas and Worktree CRUD through MCP. CMDK lists and switches Canvas only. Both clients call one Python `SpaceCrudService`. REST, MCP, the browser, the runtime gateway, capture, and session ingestion remain adapters or ports.

Locked requirements:

1. The Director root is a virtual owner presentation. It is never a `canvas` row or a launch target.
2. Every durable Worktree owns exactly one real, protected root Canvas in the same Space.
3. User Canvases form a same Space tree below one Worktree root.
4. Canvas delete hard deletes one user subtree. Protected roots, ancestors, and siblings survive.
5. Every run create takes a durable Canvas claim before preparation and enters pending inventory.
6. Live runs carry immutable Canvas affinity. Sessions carry one immutable point in time Canvas and Worktree stamp.
7. Canvas delete uses restart durable receipts and finalizes the metadata cascade atomically.
8. Worktree deletion is provenance aware. Detected rows are removed from inventory without filesystem mutation. Created rows may remove their checkout through the guarded cleanup path.

> **>> SUPERSEDED (2026-07-24).** TM does **no** `git worktree` create/delete (verified detection-only at `7ffba78b`); domain **"Worktree" = a workdir path-identity TM only OBSERVES** — delete never touches the user's checkout. **Delete** = DB cascade + best-effort run-stop + GC of TM's **own** tier-1 storage under `~/.transport-matters/workspaces/` (PROD always; DEV env-flag preserves). cm repo decisions: *Delete model = HARD DELETE now (soft-delete deferred) for space/canvas/worktree*; *Delete GCs tier-1 storage: PROD always GC, DEV mode preserves, GC sweeps dangling*. Body below is historical and must not drive implementation.

9. Tracked and untracked changes count as dirty. Force confirmation binds the exact content digest. No path silently discards bytes.
10. Git Worktree isolation as a launch or batch constructor is deferred.

There are no production users or persisted data to preserve. Schema changes reset affected tables. This specification contains no data backfill, browser cache migration, storage version bump, reparent migration, or compatibility path.

## 2. Contract invariants

- `SpaceCrudService` is the sole application entry point for approved reads, mutations, detection reconciliation, and runtime claims.
- REST derives a trusted local caller. MCP derives a trusted `ControlPlanePrincipal`. Caller supplied owner values never become authority.
- Observers read their resolved Space. Directors mutate their resolved Space.
- Durable Canvas UUIDs are the only Canvas identity accepted by routes, tools, claims, runtime requests, and client keys.
- `canvas.space_id` remains nonnull. Canvas parent edges remain inside one owner and Space.
- `CanvasKind` is `worktree_root` or `user`. A Worktree root has no parent. A user Canvas has one parent.
- `space_worktree.root_canvas_id` is nonnull and unique. The protected root counts as the required Canvas, so a Worktree may have zero user Canvases.
- User commands cannot rename, reparent, delete, or change the default Worktree of a protected root.
- User reparenting stays inside the current Worktree root. Moving a Canvas between Worktree roots is outside v1.
- `MAX_CANVAS_DEPTH = 32`, with the protected root at depth zero.
- Every tree walk carries visited IDs and fails closed on repetition or depth overflow.
- A nonnull run `canvas_id` is immutable. Presentation does not create or change execution affinity.
- The Canvas tree is navigation and lifecycle structure. A descendant Canvas may launch runs against another stable Worktree in the same Space.
- Plain terminals carry owner, Canvas, and Worktree identity and enter the same durable pending inventory.
- Canvas rows survive every failed or unknown resource stop. Retry resumes the frozen operation.
- Primary Worktree deletion always fails.
- Detection never changes Worktree provenance.
- `canvas.default_worktree_id` remains an existing checkout selector. It is never a Worktree constructor and must never reference a future ephemeral checkout.
- Session affinity has no Canvas or Worktree FK. Deletion and reparent never rewrite history.

## 3. Authority and module shape

```text
CMDK list/switch -> @tm/core transport -> REST adapter -> SpaceCrudService
MCP full CRUD    -> authenticated tool adapter         -> SpaceCrudService

SpaceCrudService -> repositories, operation store, Git port, runtime claim port,
                    Worktree lease port, termination coordinator, audit, events

Director view -> derived owner aggregation -> Spaces -> Worktree root Canvases
```

Recommended focused modules:

- `space/service.py`: application facade and transaction ownership.
- `space/canvas_commands.py`: root guards, tree rules, and Canvas commands.
- `space/worktree_commands.py`: provenance rules and Git coordination.
- `space/operation_store.py`: durable mutations and receipts.
- `space/git_worktrees.py`: fixed argument Git adapter and structured status.
- `space/runtime_claims.py`: durable pending resource claims.
- `space/lifecycle.py`: Worktree lease authority.
- `api/v1/space_mcp.py`: focused MCP tools.
- `www/packages/core/src/spaceTransport.ts`: browser DTOs and reads.
- Focused switcher rows under `www/packages/canvas/src/launcher/`.

Split `SpaceStore`, `RunManager`, `transport.ts`, and `controlplane_mcp.py` before material growth. New responsibilities do not enter files near project limits.

## 4. Typed shapes

Python uses frozen Pydantic models or dataclasses. TypeScript mirrors JSON fields in camel case.

### 4.1 Caller, presentation, and entities

```text
CrudCaller { owner; actor_run_id?; role: observer|director; workspace_id?;
             allowed_space_id: SpaceId; surface: rest|mcp }
CanvasKind = worktree_root | user
WorktreeProvenance = detected | created
WorktreeLifecycleState = creating | active | deleting
CanvasPathSegment { canvas_id: CanvasId; name: string; kind: CanvasKind }
CanvasRecord { canvas_id; space_id; name; kind; parent_canvas_id?;
               default_worktree_id?; path; depth; child_count; created_at; updated_at }
WorktreeRecord { worktree_id; space_id; root_canvas_id; provenance; path;
                 workspace_slug; workspace_hash; branch_name?; head_oid?;
                 is_primary; missing; lifecycle_state; lifecycle_generation;
                 created_at; updated_at }
DirectorTree { kind: director; owner; spaces: tuple[DirectorSpaceNode] }
DirectorSpaceNode { space_id; name; worktree_roots: tuple[CanvasRecord] }
```

The Director has no Canvas ID, parent edge, Space ID, default Worktree, persistence row, or launch action. It is derived from authorized Space and Worktree root reads.

Canvas names are trimmed, nonempty, and at most 120 Unicode scalar values. Sibling names may repeat. Root names are service derived from Worktree facts. `archived`, `layout`, and `layout_version` are absent from the recreated Canvas table and public DTO.

Worktree update means `git worktree move`. Branch and HEAD remain observed facts. Branch switching is outside this contract.

> **>> SUPERSEDED (2026-07-24).** TM does **no** `git worktree` create/delete/move product ops (verified detection-only at `7ffba78b`); domain **"Worktree" = a workdir path-identity TM only OBSERVES** — delete never touches the user's checkout. **Delete** = DB cascade + best-effort run-stop + GC of TM's **own** tier-1 storage under `~/.transport-matters/workspaces/` (PROD always; DEV env-flag preserves). Create/move must be reframed as workdir-record operations, not git subprocess ops. cm: *Delete model = HARD DELETE now (soft-delete deferred) for space/canvas/worktree*; *Delete GCs tier-1 storage: PROD always GC, DEV mode preserves, GC sweeps dangling*. Body below is historical and must not drive implementation.


```text
WorktreeCheckout =
  existing_branch { branch } |
  new_branch { branch, start_point? } |
  detached { commitish }
Patch[T] = absent | present(value: T)
```

Raw Git arguments are never accepted. Patch values distinguish omission from explicit clear.

### 4.2 Atomic runtime claim and affinity stamp

```text
WorktreeCaptureStamp { worktree_id; canonical_path; branch_name? }
CanvasCaptureStamp { canvas_id; parent_canvas_id?; canvas_name;
                     canvas_path: tuple[CanvasPathSegment] }
SessionAffinityStamp { canvas: CanvasCaptureStamp?; worktree: WorktreeCaptureStamp }
PreallocatedRuntimeIdentity { resource_id: UUID }
RuntimeClaimState = pending | running | terminating | terminal | cancelled | failed
RuntimeResourceClaim { resource_id; resource_kind: managed_run|plain_terminal;
                       run_id?; owner; canvas_id?; worktree_id; affinity_stamp;
                       state; worktree_lease_id; created_at; updated_at }
RuntimeResourceView { kind; resource_id; run_id?; owner; canvas_id?; worktree_id;
                      state: pending|running|terminating|terminal }
RuntimeResourceQuery { owner; canvas_ids?; worktree_id?;
                       include_pending=true; include_terminal=false }
SessionAffinityConflictRecord { conflict_id; session_id; owner; stored_stamp;
                                incoming_stamp; incoming_run_id; source_descriptor?;
                                conflict_digest; occurrence_count; first_seen_at; last_seen_at }
SessionUpsertOutcome { status: applied|replayed|affinity_conflict;
                       session?; conflict_id? }
```

`resource_id` is the primary key of the durable claim and the identity carried before any later run ID or terminal session exists. The stamp is one immutable value. No adapter recomputes a Canvas path, Worktree path, or branch after the claim transaction.

### 4.3 Durable operation, receipt, and dirty confirmation

```text
MutationKind = canvas_delete | worktree_create | worktree_move | worktree_delete
MutationState = prepared | frozen | gated | stopping | stop_failed | dirty_blocked |
                git_removing | git_removed | committing | completed | failed
ResourceReceiptStatus = pending | closed | already_terminal | failed | unknown
ResourceReceipt { operation_id; kind; resource_id; canvas_id?; worktree_id?; status;
                  reason?; attempt_count; updated_at }
MutationReceipt { operation_id; dispatch_id; kind; target_id; state; resources;
                  retryable; failure_code?; created_at; updated_at; completed_at? }
DirtyConfirmationClaims { owner; operation_id; worktree_id; canonical_path; head_oid;
                          content_digest; expires_at }
```

The intent digest binds caller, target, command, and confirmation claims. Reusing a dispatch with changed intent returns `dispatch_conflict`.

## 5. Shared service interface

| Method | Input | Result |
| --- | --- | --- |
| `list_canvases` | caller, Space ID | Canvas tree |
| `get_canvas` | caller, Canvas ID | Canvas record |
| `create_canvas` | `CreateCanvasCommand` | Canvas record |
| `update_canvas` | `UpdateCanvasCommand` | Canvas record |
| `prepare_canvas_delete` | Canvas ID | subtree preview and token |
| `execute_canvas_delete` | dispatch, Canvas ID, token | mutation receipt |
| `resume_canvas_delete` | operation ID | mutation receipt |
| `list_worktrees` | caller, Space ID, refresh | Worktree list |
| `get_worktree` | caller, Worktree ID | Worktree record |
| `create_worktree` | `CreateWorktreeCommand` | Worktree record |
| `update_worktree` | `MoveWorktreeCommand` | Worktree record |
| `execute_worktree_delete` | `DeleteWorktreeCommand` | mutation receipt |
| `resume_worktree_delete` | operation ID, optional token | mutation receipt |
| `reconcile_detection` | trusted detected Space facts | reconciled Space inventory |
| `claim_runtime_resource` | trusted launch or terminal facts | runtime claim and stamp |

```text
CreateCanvasCommand { dispatch_id; space_id; name; parent_canvas_id;
                      default_worktree_id? }
UpdateCanvasCommand { dispatch_id; canvas_id; name: Patch[string];
                      parent_canvas_id: Patch[CanvasId];
                      default_worktree_id: Patch[WorktreeId|null] }
CanvasDeletePreview { root; subtree; resources; confirmation_token; expires_at }
CreateWorktreeCommand { dispatch_id; space_id; destination; checkout: WorktreeCheckout }
MoveWorktreeCommand { dispatch_id; worktree_id; destination; expected_path }
DeleteWorktreeCommand { dispatch_id; worktree_id; confirmation_token? }
```

Only the service creates `worktree_root` Canvases. Public Canvas create always creates `user` under an existing user or root parent.

Stable errors:

- `invalid_request`, `forbidden`, `space_not_found`, `space_mismatch`
- `canvas_not_found`, `canvas_root_locked`, `canvas_self_parent`, `canvas_cycle`, `canvas_depth_exceeded`, `canvas_deleting`, `canvas_root_mismatch`
- `worktree_not_found`, `worktree_primary`, `worktree_deleting`, `worktree_dirty`
- `confirmation_required`, `confirmation_stale`, `runtime_stop_failed`, `git_failed`, `git_recovery_ambiguous`
- `affinity_conflict`, `operation_conflict`, `dispatch_conflict`

REST and MCP return identical codes, details, receipts, and operation IDs where both surfaces expose the method.

## 6. Canvas roots and tree contract

### 6.1 Persisted roots

Every Worktree has one `root_canvas_id`. The root Canvas shares owner and Space with the Worktree, has kind `worktree_root`, has no parent, and uses that Worktree as its pinned default. The composite Worktree reference is nonnull and unique. Its reference check is `DEFERRABLE INITIALLY DEFERRED`, while its `ON DELETE RESTRICT` action remains immediate. This permits the same transaction to insert the Worktree and Canvas pair, prevents direct root deletion, and prevents one Canvas from anchoring two Worktrees.

The service creates the Worktree and root with preallocated UUIDs in one transaction. Deferred constraints validate the pair at commit. Root creation is idempotent under the Worktree uniqueness constraints.

`SpaceCrudService.reconcile_detection` becomes the write boundary for detection. It opens one transaction, calls the repository primitive currently represented by `SpaceStore._upsert_worktree`, and calls `ensure_worktree_root` before commit. Every materialization path, including missing session Worktree creation and explicit Worktree create, uses the same function. Detection inserts `provenance=detected` only for a new row and excludes provenance from conflict updates.

The protected root satisfies the minimum Canvas count. Canvas CRUD cannot delete it. Privileged Worktree deletion removes the Worktree and its root subtree during finalization.

### 6.2 User tree mutation

Create and reparent acquire a transaction scoped advisory lock for `(owner, space_id)`. Under the lock, the service locks target and parent rows, enforces same owner and Space, rejects protected root mutation, and walks parent ancestry with a recursive CTE. The query carries `path uuid[]` and depth. It rejects a target in ancestry, repeated IDs, a different Worktree root, or depth above 32.

Subtree reads start from one owner scoped user Canvas, carry visited IDs, and order by depth then Canvas ID. Corruption blocks mutation. A database check keeps roots parentless and user Canvases parented. The composite self FK enforces same owner and Space and uses `ON DELETE CASCADE` for user subtree metadata.

Root rename, reparent, default change, and Canvas delete return `canvas_root_locked`. Root display labels may change only inside trusted Worktree reconciliation.

## 7. Atomic claims and two affinity planes

### 7.1 Claim before preparation

Every managed run and plain terminal create mints a server owned `PreallocatedRuntimeIdentity` and reserves its `RuntimeResourceClaim` before filesystem preparation, capture preparation, gateway creation, or process spawn. The eventual capture `run_id` is a later binding on the same claim. A plain terminal uses `resource_id` as its `sessionId`.

`RunManager.createWithDisposition` mints `resource_id` immediately for a call without an idempotency key. For an idempotent call, it mints only when it creates a new pending entry and stores that identity in `PendingCreate`; replay reuses the stored identity. Its private call becomes `RunManager.createNew(input, identity)`. `createNew` passes `resourceId` through `PrepareCaptureInput` and `PrepareCaptureRequest`; the Python capture boundary performs the claim transaction before any capture preparation and returns the same identity with the prepared spec.

`PlainTerminalSessions.open` mints `resource_id` as its first action, before `resolveCwd` or `PtyPort.spawn`. It calls the shared runtime claim port with the trusted owner, Canvas, and Worktree facts, then carries the identity through spawn, registration, close, and lease release. Claim failure produces no PTY. Spawn failure marks that exact claim failed.

The claim transaction:

1. Locks the Worktree and verifies `active` lifecycle state.
2. For a nonnull Canvas ID, takes the owner and Space tree lock, verifies the complete path and root, and rejects any frozen delete member.
3. Reads Canvas path plus Worktree canonical path and branch under those locks.
4. Creates one immutable `SessionAffinityStamp`.
5. Inserts the pending runtime claim and Worktree lease atomically.
6. Commits before any external work begins.

All run create routes, including single launch, `launch_batch`, and Canvas capture, use this preallocated identity and claim. An unassigned service run stores `canvas_id=null` and still enters pending Worktree inventory. Failure before registration marks the exact claim failed and releases its lease. Runtime registration binds the later `run_id` to the existing claim instead of creating identity or affinity.

`RuntimeResourcePort.list_resources` unions durable claims, `RunManager.pendingCreates`, registered runs, and `PlainTerminalSessions`, then deduplicates by resource ID. Durable claims are authoritative for the pre gateway window, so no create can escape Canvas or Worktree delete enumeration.

Add nullable `canvasId` through these contracts:

- `controlplane.run_models:LaunchRequest`, `GatewayCreateRunRequest`
- `controlplane.launch_service:_NormalizedLaunchRequest`, `_PreparedLaunch`
- `runtimeRouter:CreateRunBody`
- `runManagerTypes:CreateManagedRunInput`, `ManagedRunFilters`
- `ports:PrepareCaptureInput`
- `captured_run_models:CapturedRunRequest`
- `capture_rpc_routes:PrepareCaptureRequest`
- `capture_rpc:_CaptureRunFacts`
- `runtimeRun:RuntimeRunView`
- `transport:RunView`

Create seam signatures change. `RunManager.createNew` gains the required internal identity argument. `PrepareCaptureInput`, `PrepareCaptureRequest`, `_CaptureRunFacts`, and prepared capture facts gain required `resourceId`. `PlainTerminalSessionsOptions` gains the runtime claim port, and `OpenPlainTerminalInput` gains trusted owner, Canvas, and Worktree facts. Browser HTTP and WebSocket callers never supply `resourceId`; Runtime mints it. The public `RunManager.create` and `createWithDisposition` input signature otherwise remains unchanged.

`LAUNCH-CONTRACT.md` gains optional `canvas_id` on `LaunchRequest` and one optional `affinity_stamp` on `FrozenLaunchSpec`. Single launch and batch use the same field. Canonical serialization includes explicit null for unassigned Canvas affinity.

### 7.2 Durable transcript stamp

Add nullable session columns:

```text
canvas_id uuid
parent_canvas_id uuid
canvas_name text
canvas_path jsonb
worktree_path text
worktree_branch_name text
```

Existing `session.worktree_id` remains FK free. The Canvas columns and Worktree path and branch come from the same claim stamp.

Extend `index.adapters.base:SessionBinding`, `session.models:SessionRow`, `session.dao_statements:SESSION_COLUMN_NAMES`, `session.dao_statements:UPSERT_SESSION_SQL`, `session.ingest:build_session`, `shared_proxy.binding:ProxyRunBinding`, `shared_proxy.models:SharedProxyBindingPayload`, `addon_runtime:_make_exchange_cursor_sink`, and public session DTOs.

Migration 0031 creates `session_affinity_conflict` with no Session FK. Each record stores the canonical stored and incoming stamps, incoming run and source facts, a digest, occurrence count, and timestamps. Unique `(session_id, conflict_digest)` makes repeated poison input one durable record.

Migration 0031 also creates `upsert_session_with_affinity`. `session.dao_statements:UPSERT_SESSION_SQL` becomes one call to that database function. Inside the call, the function takes a transaction scoped advisory lock for `session_id`, then locks the existing Session row when present. It executes exactly one branch:

1. Insert a new Session and its complete stamp, returning `applied`.
2. Update a Session with no stored stamp, installing the complete stamp atomically and returning `applied`.
3. Apply the ordinary Session upsert for an exactly equal stamp and return `replayed`.
4. Leave the entire Session row unchanged for a partial or conflicting stamp, insert or increment `session_affinity_conflict`, and return `affinity_conflict` plus its ID.

The DAO commits the function outcome before surfacing a typed affinity conflict to ingestion. The durable conflict row is the quarantine authority, so the caller performs no second write that could split rejection from recording. Concurrent writers serialize inside the function and cannot combine Canvas facts from one tree version with Worktree facts from another. Reparent, rename, move, and hard delete issue no session stamp update.

## 8. Canvas hard delete state machine

### 8.1 Prepare

Under the tree lock, prepare rejects a protected root, reads the exact user subtree and complete runtime inventory, computes a digest, and returns a short lived token. It writes no Canvas state. The token binds owner, Space, root, ordered member IDs and versions, resource IDs, operation kind, and expiry. Execute rejects changed input as `confirmation_stale`.

### 8.2 Execute, restart, and finalization

1. Acquire the tree lock and validate the token and digest.
2. Create the durable operation, frozen member rows, and one durable receipt per resource.
3. Mark the operation `frozen`. Create, reparent, run claim, and terminal claim reject every member.
4. Release the transaction. Stop frozen managed runs and plain terminals through the shared coordinator.
5. Persist each result immediately. Any `failed` or `unknown` result sets `stop_failed`, retains all Canvas rows, and returns a retryable receipt.
6. Once every resource receipt is terminal, reacquire the tree lock and verify the frozen subtree.
7. In one database transaction, delete the root so the user subtree cascades, mark the operation completed, preserve every stop receipt, and append the exact `canvas_subtree_deleted` outbox event.

The database operation and receipt rows are restart authority. Startup reconciliation resumes `frozen`, `stopping`, and `stop_failed` operations. It queries each frozen resource, converts proven terminal resources to `already_terminal`, and retries only unresolved stops. Process memory never authorizes finalization. A successful stop remains recorded if a later phase fails.

Extract fanout and receipt behavior from `ControlPlaneService.close` into `RunTerminationCoordinator`. Existing close and both delete flows use it. Reuse `RunManagementPort.terminate_run`, `RunRouteProxy.terminate_run`, and `RunManager.terminate`.

### 8.3 Client reconciliation

On the committed event, clients remove exact deleted UUID keys and matching pane bindings, then navigate to the owning protected root. Canvas list refresh is server authority. There is no browser cache conversion, reparent backfill, selective stale entry migration, storage version bump, or compatibility read.

## 9. Worktree create, move, and provenance

> **>> SUPERSEDED (2026-07-24).** TM does **no** `git worktree` create/delete/move product ops (verified detection-only at `7ffba78b`); domain **"Worktree" = a workdir path-identity TM only OBSERVES** — delete never touches the user's checkout. **Delete** = DB cascade + best-effort run-stop + GC of TM's **own** tier-1 storage under `~/.transport-matters/workspaces/` (PROD always; DEV env-flag preserves). Create/move must be reframed as workdir-record operations, not git subprocess ops. cm: *Delete model = HARD DELETE now (soft-delete deferred) for space/canvas/worktree*; *Delete GCs tier-1 storage: PROD always GC, DEV mode preserves, GC sweeps dangling*. Body below is historical and must not drive implementation.


```text
GitWorktreePort {
  status(path) -> GitWorktreeStatus
  create(primary_path, destination, checkout) -> GitWorktreeMutation
  move(primary_path, source, destination) -> GitWorktreeMutation
  remove(primary_path, target, force) -> GitWorktreeMutation
  list(primary_path) -> tuple[DetectedWorktree]
}
GitWorktreeStatus { canonical_path; head_oid; tracked_changes;
                    untracked_changes; content_digest }
```

Extract `git status --porcelain --untracked-files=all` from `require_clean_worktree` into the neutral Git port. The content digest is SHA 256 over a canonical byte encoding of canonical path, HEAD, and sorted tracked and untracked status entries.

Create validates Space, destination, checkout choice, path collision, and branch collision. Before `git worktree add`, it reserves a Worktree ID, operation, target path, and a `creating` Worktree row with `provenance=created`. It creates the protected root in the same transaction. After the fixed argument Git command, detection reconciliation updates observed facts and preserves provenance. Startup recovery uses the durable create operation to finish or report an ambiguous target. It never converts an unknown existing path into TM ownership.

Detection creates new rows with `provenance=detected`. `SpaceStore._upsert_worktree` conflict updates may refresh path, branch, HEAD, missing state, and timestamps. They cannot write provenance or root identity.

Move accepts a path move only. It validates `expected_path`, gates the Worktree, requires no active leases, runs `git worktree move`, updates the same Worktree ID, and reconciles observation. Move preserves provenance and root Canvas identity. Primary move remains rejected.

The future isolation constructor belongs to the batch layer at Run or candidate intent. V1 adds no isolation field to `LaunchRequest`. Canvas defaults and pane Worktree IDs remain selectors of existing stable Worktrees. They cannot request creation and must never point at a future ephemeral Worktree.

## 10. Persisted Worktree lifecycle and pending cancellation

```text
WorktreeLease { lease_id; owner; worktree_id; generation;
                resource_kind: capture|plain_terminal; resource_id; canvas_id?;
                acquired_at; heartbeat_at; expires_at; cancel_requested }
```

Lease acquisition locks the Worktree row and succeeds only in `active`. Delete changes state to `deleting` and increments generation in the same transaction. Every later claim returns `worktree_deleting`.

Managed capture acquires through the runtime claim transaction before preparation. `CaptureLeaseRegistry` stores the durable lease ID in `_CaptureRunFacts` and releases it after capture release. A pending preparation checks cancellation before every external phase and closes any prepared resource before failing.

`PlainTerminalSessions.open` accepts the trusted facts, preallocates identity, and obtains the claim. It checks `cancel_requested` and generation immediately before spawn. After spawn and before registration or returning the socket, it checks them again. Cancellation during spawn closes the PTY and child, waits for exit, marks the preallocated claim cancelled, and releases the lease. A terminal is never published after a delete gate wins.

Leases heartbeat every ten seconds with a thirty second expiry. Expiry requires runtime liveness proof. A stale generation cannot release a newer lease. `terminating` retains its lease until cleanup finishes.

## 11. Provenance aware Worktree delete

> **>> SUPERSEDED (2026-07-24).** TM does **no** `git worktree` create/delete (verified detection-only at `7ffba78b`); domain **"Worktree" = a workdir path-identity TM only OBSERVES** — delete never touches the user's checkout. **Delete** = DB cascade + best-effort run-stop + GC of TM's **own** tier-1 storage under `~/.transport-matters/workspaces/` (PROD always; DEV env-flag preserves). cm repo decisions: *Delete model = HARD DELETE now (soft-delete deferred) for space/canvas/worktree*; *Delete GCs tier-1 storage: PROD always GC, DEV mode preserves, GC sweeps dangling*. Body below is historical and must not drive implementation.


### 11.1 Common gate and stop phases

1. Lock the row and reject a primary Worktree.
2. Change `active` to `deleting`, increment generation, and create or resume the durable operation.
3. Mark current leases `cancel_requested`.
4. Stop frozen registered runs and plain terminals through `RunTerminationCoordinator`.
5. Wait for pending claims, terminating resources, and leases. Stop failure is retryable while the gate remains closed.

### 11.2 Detected Worktree branch

After resources quiesce, a detected Worktree skips status, confirmation, `git worktree remove`, and every filesystem delete. In one transaction, delete the Worktree row, delete its protected root so user descendants cascade, complete the operation and receipts, and append `worktree_deinventoried`.

This command removes TM inventory only. A later explicit detection refresh may materialize the checkout again with a new detected row and protected root. No tombstone or exclusion policy is part of v1.

### 11.3 Created Worktree cleanup branch

1. Run structured status only after managed writers are quiet.
2. A clean status proceeds without force. A dirty status sets `dirty_blocked` and returns `confirmation_required` with the exact content digest and signed claims.
3. Immediately before removal, recheck canonical path, HEAD, tracked entries, untracked entries, and content digest while the lifecycle gate remains closed.
4. Any changed claim returns `confirmation_stale`. A confirmed unchanged dirty snapshot may use `git worktree remove --force`. No other path uses force.
5. Persist `git_removing` with path, HEAD, digest, force authorization, and Git common directory fingerprint before invoking Git.
6. After verified removal, persist `git_removed`.
7. In one transaction, delete the Worktree row, delete its protected root subtree, complete the operation and receipts, preserve sessions, and append `worktree_deleted`.

Startup recovery for `git_removing` compares the durable facts with Git inventory and the filesystem. An absent matching checkout advances to `git_removed`. An exact registered checkout retries only after the content digest and confirmation remain valid. A changed or conflicting path returns `git_recovery_ambiguous` and performs no deletion. Database failure after Git removal resumes from `git_removed`.

Managed writers are excluded by the lifecycle gate. External processes do not honor that gate, so the immediate digest recheck is mandatory and the remaining external write race is an explicit risk.

## 12. REST, MCP, and CMDK contracts

### 12.1 REST adapter

| Method | Path | Service method |
| --- | --- | --- |
| GET, POST | `/v1/spaces/{spaceId}/canvases` | list, create Canvas |
| GET, PATCH | `/v1/canvases/{canvasId}` | get, update Canvas |
| POST | `/v1/canvases/{canvasId}/delete/prepare` | prepare Canvas delete |
| POST | `/v1/canvases/{canvasId}/delete/execute` | execute Canvas delete |
| POST | `/v1/canvas-delete-operations/{operationId}/resume` | resume Canvas delete |
| GET, POST | `/v1/spaces/{spaceId}/worktrees` | list, create Worktree |
| GET, PATCH | `/v1/worktrees/{worktreeId}` | get, move Worktree |
| POST | `/v1/worktrees/{worktreeId}/delete` | execute Worktree delete |
| POST | `/v1/worktree-delete-operations/{operationId}/resume` | resume Worktree delete |

REST exposes typed parity for clients and contract tests. The v1 browser binds only Canvas list and switch. CRUD routes drop public owner query authority.

### 12.2 MCP tools

Expose `canvas_list`, `canvas_get`, `canvas_create`, `canvas_update`, `canvas_delete_prepare`, `canvas_delete_execute`, `canvas_delete_resume`, `worktree_list`, `worktree_get`, `worktree_create`, `worktree_update`, `worktree_delete`, and `worktree_delete_resume` in `space_mcp.py`.

Every tool delegates directly to the matching service method and uses the same command, error, token, and receipt models. MCP accepts no raw CWD discovery, raw Git arguments, owner override, or force boolean.

### 12.3 CMDK v1

CMDK has two Canvas actions:

1. List the authorized Canvas tree, including protected Worktree roots.
2. Switch the active route to one selected Canvas UUID.

CMDK has no create, rename, reparent, default, delete, resume, Worktree mutation, dirty confirmation, or force action in v1. Its switcher calls `SpaceCrudService.list_canvases` through the REST adapter and performs no mutation or safety inventory. Full CRUD remains an MCP surface.

## 13. Reset migrations

The migration contract is destructive by design. There are no backfill branches, preservation checks, staged nullability changes, cache converters, or historical inference. Tests build from an empty database and prove the final schema. Upgrade from `0029` drops affected local tables in dependency order and recreates them.

### 13.1 `0030_space_crud_reset`

Down revision: `0029_native_connection_origin`.

- Drop `canvas`, then `space_worktree`.
- Recreate `space_worktree` with final provenance, lifecycle, generation, and nonnull unique `root_canvas_id` fields.
- Recreate `canvas` with final kind, parent, default Worktree, timestamps, and scoped keys. Omit `archived`, `layout`, and `layout_version`.
- Add the parent check, root or user shape check, unique `(owner, space_id, canvas_id)`, composite same Space parent FK with `ON DELETE CASCADE`, and parent lookup index.
- Add `FOREIGN KEY (owner, space_id, root_canvas_id) REFERENCES canvas(owner, space_id, canvas_id) ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED`. The insert and update reference check is deferred to commit. The `RESTRICT` delete action remains immediate for root protection.
- Recreate `canvas_default_worktree_fk` with `ON DELETE SET NULL`.

No Worktree, Canvas, parent, root, archive, or layout data survives. Detection and explicit creation materialize final rows and protected roots from fresh facts.

### 13.2 Cross language affinity

This contract change adds nullable Canvas and affinity stamp fields to Python and Node shapes. Contract fixtures prove serialization in both directions. There is no compatibility decoder for preclaim runs.

### 13.3 `0031_runtime_claim_and_session_affinity_reset`

Down revision: `0030_space_crud_reset`.

- Create `runtime_resource_claim` keyed by the preallocated `resource_id` and `worktree_lifecycle_lease` so one transaction can persist the pending resource, immutable affinity stamp, and Worktree lease before preparation.
- Drop `event_artifact`, `event`, and `session` in dependency order.
- Recreate the current session family with the Canvas stamp and Worktree path and branch columns.
- Create FK free `session_affinity_conflict` with its conflict digest uniqueness and Session lookup index.
- Create `upsert_session_with_affinity` as the single statement apply, replay, or conflict recording authority.
- Add the complete stamp group check and partial `(owner, canvas_id, started_at DESC)` index.
- Add no Canvas or Worktree FK.

No session, event, or event artifact row survives. Artifact bytes may remain because they have no session identity.

### 13.4 `0032_space_mutation_operations`

Down revision: `0031_runtime_claim_and_session_affinity_reset`.

Create `space_mutation_operation`, `space_mutation_resource_receipt`, `canvas_delete_member`, and the operation outbox. Operation rows have no target FK, so restart evidence survives hard delete. A partial unique constraint prevents concurrent active operations for one owner, kind, and target.

Extend `session.test_migrate:test_apply_migrations_brings_unmigrated_db_to_head` and schema invariant helpers with final table, column, check, index, FK, cascade, deferred root, and no session affinity FK assertions. Revision IDs remain within the Alembic limit. No downgrade promises data recovery.

## 14. Corrected reuse map

| Capability | Existing owner, file:symbol | Disposition |
| --- | --- | --- |
| Durable IDs | `space.models:CanvasId`, `WorktreeId` | Reuse |
| Canvas row | `space.models:Canvas` | Replace shape in reset |
| Worktree row | `space.models:Worktree` | Replace shape in reset |
| Space persistence | `space.store:SpaceStore` | Split before growth |
| Detection upsert | `space.store:SpaceStore._upsert_worktree` | Put behind service transaction |
| Default cleanup | `0006_spaces_foundation:canvas_default_worktree_fk` | Recreate same behavior |
| Git observation | `space.detection:detect_space` | Keep read only, reconcile through service |
| Dirty precedent | `certification_minting:require_clean_worktree` | Extract neutral status |
| Same Space validation | `space_routes:_require_worktree_in_space` | Move and strengthen |
| REST origin | `origin:require_http_origin` | Reuse |
| MCP principal | `controlplane.models:ControlPlanePrincipal` | Reuse |
| MCP adapter | `controlplane_mcp:_McpControlPlaneAdapter` | Reuse pattern |
| MCP registry | `controlplane_mcp:create_control_plane_mcp` | Extract focused registrar |
| Bulk stop | `controlplane.service:ControlPlaneService.close` | Extract coordinator |
| Stop port | `controlplane.activity:RunManagementPort.terminate_run` | Reuse |
| Gateway stop | `run_proxy:RunRouteProxy.terminate_run` | Reuse |
| Runtime stop | `RunManager:terminate` | Reuse |
| Registered inventory | `RunManager:list` | Add Canvas filter |
| Pending inventory | `RunManager:pendingCreates` | Join durable claims |
| Capture lifetime | `capture_rpc:CaptureLeaseRegistry` | Bind durable lease |
| Plain terminals | `PlainTerminalSessions:PlainTerminalSessions` | Add claim, identity, inventory, lease |
| Session binding | `index.adapters.base:SessionBinding` | Add immutable stamp |
| Session row | `session.models:SessionRow` | Add immutable stamp |
| Session upsert | `session.dao_statements:UPSERT_SESSION_SQL` | Replace with one atomic function call |
| Affinity conflict | no existing durable record | Add FK free conflict quarantine in migration 0031 |
| Proxy binding | `shared_proxy.binding:ProxyRunBinding` | Carry same stamp |
| Browser transport | `transport:fetchSpaces` | Split focused transport |
| Canvas cache | `canvasCacheStorage:createCanvasCacheStorage` | Start fresh on UUID keys |
| CMDK grammar | `commandTypes:LauncherCommand` | Add list and switch only |
| CMDK dispatcher | `CanvasCommandDispatcher:CanvasCommandDispatcher` | Adapter only |
| Local clear | `canvasActions:clearCanvas` | Never map to server delete |

## 15. Ordered PR slices

Every slice starts with failing tests and ends with `just check` plus `just test-affected`.

### Slice 1: service, reset model, protected roots, and read clients

- Deliver: `SpaceCrudService`, migration 0030, final Canvas and Worktree records, virtual Director projection, tree reads, detection reconciliation, idempotent protected root creation, trusted REST and MCP callers, CMDK list and switch.
- Tests first: empty reset, exact deferred root FK flags, same transaction root pair, immediate restricted root delete, one root per Worktree, concurrent detection, provenance preservation, missing Worktree materialization, root guards, same Space tree, Director nonpersistence, caller parity.
- Gate: `just check`, `just test-affected`.

### Slice 2: atomic claims, leases, and immutable affinity

- Deliver: migration 0031, server preallocated resource identity, changed managed run, capture, and terminal create seams, durable runtime claims and Worktree leases, pre preparation claim transaction, pending inventory, nullable Canvas ID through launch, batch, capture, gateway, runtime and browser, one affinity stamp, durable affinity conflict records, and the atomic Session function.
- Tests first: managed identity exists before capture preparation, idempotent replay reuses identity, terminal identity exists before CWD resolution and spawn, claim failure spawns nothing, spawn failure closes the exact claim, no pre gateway inventory gap, delete versus claim race, Python and Node signature fixtures, null and UUID affinity, single and batch parity, tree consistent stamp, Worktree path and branch history, equal replay without conflict, conflicting upsert leaves Session unchanged and commits one conflict, repeated poison increments one record, concurrent conflicting writers serialize, no affinity FK.
- Gate: `just check`, `just test-affected`.

This is the heaviest cross language slice and receives the closest interface and migration review.

### Slice 3: Canvas create and update through MCP

- Deliver: user Canvas create, rename, same root reparent, default set and clear, cycle and depth guards, REST parity, MCP mutations, UUID browser authority with fresh local state.
- Tests first: root only bootstrap, user parent requirement, omission and null, root mutation denial, concurrent cycles, cross Space and cross root reparent, depth boundary, mixed Worktree launch default, REST and MCP fixtures.
- Gate: `just check`, `just test-affected`.

### Slice 4: restart durable Canvas delete

- Deliver: migration 0032, operations, members, durable receipts, outbox, shared termination coordinator, plain terminal inventory and stop, prepare, execute, resume, restart reconciler, atomic cascade finalization, client event cleanup.
- Tests first: protected root denial, exact subtree, unchanged siblings and ancestors, pending claims, running resources, plain terminals, failed and unknown stop, restart at every state, preserved successful receipts, create and reparent freeze, one transaction finalization.
- Gate: `just check`, `just test-affected`.

### Slice 5: provenance aware Worktree create and move

- Deliver: neutral Git port, status digest, durable created reservation and recovery, typed create, identity preserving move, detection preservation, REST parity, MCP create and update.
- Tests first: detected and created provenance, reconciliation cannot clobber, Git crash boundaries, unknown path quarantine, branch modes, collisions, expected path, primary move rejection, fixed arguments, stable root identity.
- Gate: `just check`, `just test-affected`.

### Slice 6: Worktree lifecycle and provenance aware delete

- Deliver: deletion gate over the Slice 2 leases, managed and terminal pending cancellation, common stop phase, detected de-inventory branch, created dirty confirmation and Git cleanup branch, `git_removing` recovery, atomic metadata finalization, REST parity, MCP delete and resume.
- Tests first: launch before and after gate, cancellation before and after terminal spawn, registered and terminating resources, primary block, detected zero Git calls, rediscovery behavior, clean created cleanup, tracked and untracked digest, stale confirmation, exclusive force, external change recheck, every `git_removing` restart case, session stamp survival.
- Gate: `just check`, `just test-affected`.

New slice count: 6. Delta from the prior plan: minus 2.

## 16. Open risks

1. Preallocated identity must remain inside each create seam's idempotency authority. Minting on replay or after preparation reopens the pending inventory gap.
2. The deferred Worktree to root Canvas pair is a circular schema edge. Migration and concurrent insert tests must prove commit behavior.
3. Plain terminal cancellation crosses database, Node spawn, PTY cleanup, and socket publication. Both cancellation checks are required.
4. Git and Postgres cannot commit together. Durable create, move, `git_removing`, and `git_removed` states must cover every crash boundary.
5. External processes do not honor the Worktree lifecycle gate. The immediate content digest recheck narrows the dirty force race but cannot eliminate an external write between check and Git removal.
6. Detected de-inventory is intentionally reversible by later detection. Permanent exclusion would require a separate tombstone policy.
7. Operation and receipt retention needs an administrative policy. Immediate deletion would weaken restart and diagnosis.
8. Future ephemeral isolation must add ownership and candidate lifecycle at the batch layer. It cannot reuse Canvas defaults as a constructor.

No locked design decision remains open. These are implementation risks with explicit test boundaries.

## 17. Completion proof

- MCP exposes full Canvas and Worktree C, R, U, and D through `SpaceCrudService`.
- CMDK lists and switches Canvas only through the same service.
- Every materialized Worktree has one protected real root Canvas. The Director remains virtual.
- Canvas create and reparent prove kind, root, cycle, depth, and same Space invariants.
- Every run and terminal has one server preallocated resource identity and appears in durable pending inventory before external preparation, CWD resolution, or spawn.
- Session history keeps an atomic immutable Canvas path plus Worktree ID, path, and branch after rename, reparent, move, and hard delete. A conflicting upsert leaves it unchanged and commits one durable affinity conflict in the same database function call.
- Canvas delete resumes after process restart and finalizes cascade, operation, receipts, and event atomically.
- Detected Worktree delete performs no Git or filesystem mutation.
- Created Worktree delete blocks writers, proves the exact dirty content digest, and uses force only after bound confirmation.
- Pending terminal cancellation is proven before and after spawn.
- Every migration resets affected schema without backfill or compatibility logic.
- All six slices pass `just check` and `just test-affected`.
- No new file exceeds 700 lines and no function exceeds approximately 150 lines.
