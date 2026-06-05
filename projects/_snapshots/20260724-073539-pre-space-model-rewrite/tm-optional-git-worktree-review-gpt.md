# Optional Git worktree isolation review

Date: 2026-07-22  
Baseline: `feat/multi-launch` at `b094e80d69ad7d57c5bba0ff8f4d71a986a837f2`  
Scope: design review only

## Verdict

**Add now at launch and batch candidate intent.** Add one explicit checkout intent to the server launch contract. A single launch may request an isolated checkout. A batch may explicitly apply isolated checkout intent to every candidate, then freeze the resolved intent per candidate. Absence always means reuse an existing registered Worktree.

Do not add an isolation preference to Space, `Canvas.default_worktree_id`, pane persistence, or `packages/runtime/src/service/RunManager.ts:RunManager.createWithDisposition`. Those layers should hold resolved Worktree identity. Python launch orchestration should own provisioning before Runtime receives a cwd and Worktree ID.

The first slice should support a clean committed source, one detached writable checkout per launch item, durable crash reconciliation, and retain by default cleanup. Fair evaluation remains blocked until one immutable source snapshot can be sealed and materialized for every candidate.

The biggest risk is a provenance error that classifies a user checkout as TM created and later removes it. A path, naming convention, or boolean on `space_worktree` is insufficient authority for deletion.

## 1. Current boundaries

### Detection and inventory

`api/src/transport_matters/space/detection.py:detect_space` probes a path and `api/src/transport_matters/space/detection.py:_detect_git_worktrees` runs `git worktree list`. Both are read only. `api/src/transport_matters/space/store.py:SpaceStore.upsert_detection` persists discovered facts through `SpaceStore._upsert_worktree` and marks absent records missing.

`api/src/transport_matters/space/models.py:Worktree` and `api/migrations/versions/0006_spaces_foundation.py:upgrade` have no origin, provision, or cleanup ownership field. Detection and session backfill converge on the same inventory row. This makes `space_worktree` an observation of a checkout, not sufficient proof that TM created it.

Keep this create versus detect boundary permanent:

* `detect_space` remains read only.
* A new `WorktreeProvisioningService` is the sole Git mutation boundary.
* Detection may refresh an owned Worktree's observed branch, head, path, and missing state. It may never infer or overwrite ownership.

### Launch and Runtime

`api/src/transport_matters/controlplane/run_models.py:LaunchRequest` accepts a workdir and has no checkout intent. `api/src/transport_matters/controlplane/launch_service.py:ControlPlaneLauncher._prepare` resolves that workdir inside the actor workspace, then `ControlPlaneLauncher._execute` sends it to the gateway.

The Canvas path currently skips that service. `www/packages/canvas/src/model/capturedRunStore.ts:CapturedRunState.ensureRun` creates a run through the Runtime API. `packages/runtime/src/server/runtimeRouter.ts:registerRuntimeRoutes` forwards the request to `RunManager.createWithDisposition`. `api/src/transport_matters/api/v1/capture_rpc_routes.py:_resolved_domain_request` asks `api/src/transport_matters/api/v1/launch_resolution.py:resolve_run_worktree` to resolve an existing Worktree ID.

Runtime is an actuation boundary. `RunManager.createWithDisposition` already fingerprints the requested Worktree through `packages/runtime/src/service/runManagerSupport.ts:createRunFingerprint`, while the Python capture response may supply the final resolved ID. Git creation in Runtime would split Space ownership and crash reconciliation across Python and Node.

Before Canvas can request isolation, route its spawn through the same server launch item service as single and batch launch. Runtime should receive only:

* resolved cwd;
* resolved `space_id` and `worktree_id`;
* immutable launch identity and idempotency key;
* optional provision ID as an observed launch fact.

## 2. Parameter level and inheritance

Use a tagged launch value:

```text
CheckoutIntent =
  ExistingCheckout { worktree_ref }
  | IsolatedCheckout {
      source_worktree_ref
      cleanup_policy: retain | remove_if_clean
    }
```

Recommended mapping:

| Surface | Contract |
| --- | --- |
| Space | Inventory and authorization scope. No isolation default. |
| `Canvas.default_worktree_id` | Existing source selection only. Never causes creation. |
| Pane command | May expose an explicit isolate action. It submits launch intent. |
| `PaneContentRef.worktreeId` | Persists the resolved output Worktree ID after success. |
| Single launch item | Owns the explicit checkout intent. |
| Batch | May explicitly default all candidates to isolated checkout, then expands and freezes one exact intent per candidate. |
| Candidate | Owns the resolved provision ID, output Worktree ID, base object ID, and candidate key. |
| `RunManager.createWithDisposition` | Accepts resolved facts only. No Git isolation parameter. |

`www/packages/canvas/src/model/canvasActions.ts:createCapturedRunActions` currently lets a per spawn Worktree override the Canvas default and keeps the default unchanged. `www/packages/canvas/src/model/canvasState.ts:CanvasStoreActions.addCapturedRun` explicitly permits runs from different Worktrees to coexist. Isolation should preserve both properties.

There is one allowed inheritance point. An explicit batch setting such as `isolated_per_candidate` may expand into an `IsolatedCheckout` for every item before dispatch. Each frozen candidate then contains the exact source, base object ID, output identity, and cleanup policy. A missing setting expands to `ExistingCheckout`. A Canvas preference must not participate.

## 3. Durable ownership model

Add a durable provision record, separate from detected inventory:

```text
worktree_provision {
  provision_id
  owner
  space_id
  source_worktree_id
  output_worktree_id
  dispatch_id
  candidate_key
  git_common_dir_fingerprint
  base_oid
  target_path
  cleanup_policy
  state: prepared | creating | active | retained |
         cleanup_pending | removed | failed | quarantined
  created_at
  updated_at
  last_error
}
```

Use unique constraints for `(owner, dispatch_id, candidate_key)`, `output_worktree_id`, and canonical `target_path`. Add a nullable, unique `provision_id` reference on `space_worktree`. A null reference means detected or externally created. A nonnull reference means TM created, subject to full provision validation.

An origin enum such as `detected | tm_created` can improve reads, but removal authority comes from the provision record. `SpaceStore._upsert_worktree` must preserve the provision reference during every detection refresh.

The target must live under one dedicated TM owned checkout root derived from `api/src/transport_matters/config.py:Settings.storage_dir`, with a deterministic leaf based on `provision_id`. Never create under a Canvas supplied path.

## 4. Creation and crash reconciliation

Git and Postgres cannot commit atomically. Use a durable saga:

1. Validate owner, Space, explicit isolated intent, source availability, and source cleanliness. Resolve and freeze the source commit object ID. Reserve provision ID, output Worktree ID, exact target path, dispatch ID, and candidate key in one database transaction with state `prepared`.
2. Change state to `creating`, then run a typed fixed argument command equivalent to `git worktree add --detach <target_path> <base_oid>`. Do not use a shell string.
3. Probe the target and common Git directory with the same parsing discipline as `space.detection`. In one transaction, upsert the output inventory row with its provision reference and mark the provision `active`.
4. Start runtime actuation only after the active state commits.

Startup reconciliation examines all nonterminal provisions:

* `prepared` with no Git checkout is safe to retry using the same IDs and path.
* `creating` with a matching registered checkout is finalized.
* `creating` with no checkout is retried or marked failed.
* a path that exists but is unregistered, points at another common Git directory, or has conflicting contents becomes `quarantined`. No deletion follows.
* an active checkout removed outside TM is marked removed and its inventory row becomes missing.

`api/src/transport_matters/controlplane/launch_ledger.py:LaunchLedger` retains truth for one API process lifetime. It cannot make this saga durable. Provisioning should land with the planned Postgres launch item ledger, or with an equivalent durable store first. If that prerequisite cannot land, defer Git actuation as a whole.

## 5. Cleanup and deletion safety

The provision is owned by a launch item or batch candidate. A browser pane and a `RunManager` process are consumers. They are poor cleanup owners because both may disappear during a crash.

`api/src/transport_matters/capture_rpc.py:CaptureLeaseRegistry` and `packages/runtime/src/service/RunManager.ts:RunManager` are process resident. `api/src/transport_matters/run_lifecycle.py:emit_run_lifecycle_best_effort` deliberately allows lifecycle event loss. None can authorize destructive checkout cleanup.

Persist run use against the provision. A run exit releases that use. Default policy is `retain`, including after failure, crash, or orphan detection. `remove_if_clean` may enqueue cleanup only when the launch item is terminal and no live or uncertain run use remains.

Automated removal requires every condition below:

1. matching durable provision, owner, output Worktree ID, dispatch ID, and candidate key;
2. canonical target below the dedicated TM checkout root;
3. matching Git common directory fingerprint;
4. Git still registers that exact checkout;
5. no active or uncertain run use;
6. clean tracked and untracked status;
7. cleanup state transitioned durably to `cleanup_pending`.

Then call `git worktree remove <target_path>` without force and mark the provision removed after verification. Never use recursive filesystem deletion. Never delete a detected Worktree. A dirty owned checkout becomes retained and visible for explicit review. Force discard requires a separate user command with content bound confirmation.

An orphan is a cleanup candidate for inspection, not permission to delete. Startup repair and quota policy should surface retained, dirty, failed, and quarantined provisions with their disk use.

## 6. Workspace and evaluation semantics

A detached Worktree created from `head_oid` isolates writes and branch refs. It excludes dirty tracked changes and untracked files. The first slice should reject a dirty source with a precise error. Silently using HEAD would make candidates evaluate different input from the operator's visible checkout.

The current multi launch design records `workspace_snapshot_id=null`, uses `live_worktree`, and requires distinct preexisting Worktrees for `per_candidate`. Optional provisioning removes that manual setup cost and prevents candidate write collisions. It still does not satisfy fair evaluation.

Fair evaluation requires this later sequence:

1. seal one immutable workspace snapshot once;
2. freeze its identity and digest for the batch;
3. create one writable materialization per candidate from that same snapshot;
4. bind `(owner, dispatch_id, candidate_key)` idempotently to one provision;
5. stamp every result with snapshot, provision, output Worktree, and base object identity.

Repeated dispatch with the same candidate key must return the same provision. A changed intent under the same key must fail. This extends the existing intent fingerprint behavior in `api/src/transport_matters/controlplane/launch_service.py:_intent_fingerprint` and `RunManager.createWithDisposition`.

## 7. Locked roots, transcript facts, and Canvas affinity

### Locked Worktree root

When protected Worktree root Canvases land, provision finalization should create the output Worktree inventory row and its root Canvas in the same database transaction. The root is a navigation and lifecycle anchor. It does not constrain where its runs appear.

Creating an isolated candidate from Canvas A should keep the run on Canvas A. Do not switch `Canvas.default_worktree_id`, move the pane to the new root, or make the root the run affinity. The user may later navigate to the output Worktree root explicitly.

### Transcript and run facts

`api/src/transport_matters/index/adapters/base.py:SessionBinding`, `api/src/transport_matters/session/models.py:SessionRow`, and `api/src/transport_matters/session/models.py:RunLifecycleEventRow` already carry a resolved Worktree ID. Stamp the isolated output ID there as today.

Historical meaning also needs immutable facts that survive Worktree deletion:

* provision ID;
* source Worktree ID;
* frozen base object ID;
* workspace snapshot ID and digest when available;
* dispatch ID and candidate key.

Put these in the frozen launch specification and owned transcript launch metadata. Denormalize the key source facts into an immutable session or evaluation record if historical queries must work without joining a deleted inventory row.

Current server run contracts do not carry `canvas_id`. `www/packages/canvas/src/model/paneRecords.ts:CanvasModel` and the client cache own Canvas placement, while `RunLifecycleEventRow` records only `launch_kind`. Server owned immutable Canvas affinity is a separate contract gap. When it lands, freeze `canvas_id` beside checkout intent. Never derive it from the source or output Worktree.

## 8. Implementation gates

Ship add now only when all gates pass:

1. durable provision schema and state machine;
2. idempotent creation across retry and restart;
3. reconciler tests for every crash boundary around Git and database writes;
4. proof that detection refresh cannot grant or erase TM ownership;
5. deletion tests covering detected, dirty, path escape, common directory mismatch, active use, and repeated cleanup;
6. single launch and batch candidate integration through one provisioning service;
7. Runtime tests proving it accepts resolved facts and never invokes Git;
8. session and result tests proving immutable provenance survives checkout removal;
9. explicit UI copy that isolation is optional and retained checkouts consume disk;
10. source cleanliness enforcement until sealed snapshots exist.

This is an add now recommendation for the launch contract and durable lifecycle substrate. A partial feature that adds an `isolated` boolean before durable ownership and restart reconciliation should not ship.
