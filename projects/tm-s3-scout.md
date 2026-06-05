# Transport Matters S3 Scout

## Scope and recommendation

S3 should ship as two stacked pull requests.

1. S3a owns the mandatory `SpaceStore` extraction, Worktree and Space
   deletion, and best effort run stop.
2. S3b owns the shared tier 1 garbage collection primitive, the production
   policy flag, a new durable capture finalization contract, both garbage
   collection triggers, and the dangling sweep.

This split gives the irreversible recursive directory removal its own review
boundary. S3b is blocked until the finalization contract and the open storage
ownership decisions below are adjudicated. S3a can be reviewed independently,
but both slices must land before the settled delete behavior is considered
complete.

## Authoritative product rulings

1. A Canvas belongs to exactly one anchor Worktree. Canvas launches must use
   that Worktree.
2. Transport Matters performs detection only. Delete never changes a Git
   worktree or the user's source directory.
3. Production removes Transport Matters tier 1 capture storage after a safe
   run end and after target deletion.
4. Development can preserve tier 1 through a dedicated
   `TRANSPORT_MATTERS_*` setting. `channel` has no role in this policy.
5. A run directory can be removed only after its wire IR and transcript events
   are durably committed to Postgres.
6. Space and Worktree delete retain session affinity and lifecycle rows as
   historical tombstones.

## Reuse map

| Concern | Existing authority | Binding for S3 |
|---|---|---|
| Git detection | `api/src/transport_matters/space/detection.py::detect_space`, `::_run_git` | Remains read only. The only Git subprocess is `git worktree list --porcelain -z`. |
| Default run path | `api/src/transport_matters/workspace.py::run_root_for_workspace` | Builds `default_workspaces_root()/slug/hash/run_id` from frozen identity. Use only for default managed storage. |
| Durable run enumeration | `api/src/transport_matters/session/backfill.py::iter_run_dirs` | Reuse its `index.jsonl` discovery for the default root dangling sweep. Do not duplicate the glob. |
| Exchange directory removal | `api/src/transport_matters/storage/disk.py::DiskStorageBackend.delete_exchange` and `storage/disk_helpers.py::DiskStorageFileOpsMixin._stage_exchange_delete` | Extract the generic stage, restore, and recursive remove operations so whole run removal and exchange removal share one implementation. |
| DB wire sweep | `api/src/transport_matters/session/wire_store.py::sweep_wire_store` | Keep as the existing DB row sweep. It does not remove run directories. |
| Session target facts | `api/src/transport_matters/session/models.py::SessionRow` | `space_id`, `worktree_id`, `canvas_id`, `run_id`, `workspace_slug`, and `workspace_hash` identify default run directories. |
| Session queries | `api/src/transport_matters/session/async_dao.py::AsyncSessionDao.list_session_views` | Already filters by Space and Worktree. Add an exhaustive, distinct capture reference query rather than relying on the presentation limit and offset API. Include Canvas for S4b. |
| Active run inventory | `api/src/transport_matters/api/v1/run_proxy.py::RunRouteProxy.list_runs` | Use the exhaustive typed S2 inventory with `space_id` or `worktree_id`. |
| Run termination | `api/src/transport_matters/api/v1/run_proxy.py::RunRouteProxy.terminate_run` and `controlplane/activity.py::RunManagementPort` | Inject the protocol into deletion orchestration. Avoid a concrete HTTP dependency in the Space domain. |
| Space delete | `api/src/transport_matters/space/store.py::SpaceStore.delete_space` | Today this deletes one nondefault Space. The link FK cascades, while Worktree and Canvas rows remain. Add stop and later garbage collection around this mutation. |
| Worktree delete | No method exists | Add one owner scoped store method. The Worktree row owns its anchored Canvas tree and link rows through migration `0030`. |
| FK behavior | `api/migrations/versions/0030_space_crud_reset.py::_create_final_space_worktree`, `::_create_final_canvas` | Worktree link and Canvas anchor FKs cascade. The Worktree root Canvas and Canvas default Worktree FKs are deferred `NO ACTION`, so statement order and foreign defaults need explicit handling. |
| Settings pattern | `api/src/transport_matters/config.py::Settings` | Add one boolean field. Pydantic supplies the `TRANSPORT_MATTERS_*` environment mapping, as it does for `debug` and `gateway_supervise`. |
| Runtime home cleanup | `api/src/transport_matters/captured_run_context.py::_prepare_home_and_grant` | The exit stack removes only `storage_dir/runtime-home`. It does not remove the capture root. |
| Managed release | `api/src/transport_matters/capture_rpc.py::CaptureLeaseRegistry.release_capture` | Closes the lease, then emits `RUN_EXITED`. This is the managed run end integration point after a strict finalization proof exists. |
| Capture shutdown | `api/src/transport_matters/addon_runtime.py::close_capture_runtime` | Stops and polls the transcript tailer, drains live and wire observers, drains the dispatcher, writes the lifecycle event, then closes the writer. This is a global shutdown drain, not a successful per run finalization signal. |
| Transcript commits | `api/src/transport_matters/index/tailer.py::TranscriptTailer`, `index/commit_dispatcher.py::ShardedCommitDispatcher` | Add a final barrier that resolves every accepted window as committed or durably quarantined before finalization. |
| Wire commits | `api/src/transport_matters/wire_store_observer.py::WireStoreObserver` and `session/writer.py::SessionWriter.submit_wire_exchange` | Add strict result aggregation. Current close uses `return_exceptions=True`, and the writer can return `ok=False` without raising. |
| Lifecycle rows | `api/src/transport_matters/session/writer.py::SessionWriter.submit_run_lifecycle_event` | Preserve `RUN_EXITED` as process lifecycle history. Do not reuse it as capture durability proof. |
| Stale manifest reap | `api/src/transport_matters/cli/instances.py::_reap` | Today it only unlinks `manifest.json` so history survives. Make it a finalized garbage collection backstop in production after S3b. |
| Actual storage path | `api/src/transport_matters/manifest.py::Manifest.storage_dir` and `captured_run_models.py::CapturedRunSpawnSpec.storage_dir` | The live process knows the path. The manifest disappears at normal end, and no durable DB row retains this path. |

## Current deletion model

### Space

`SpaceStore.delete_space` deletes a named Space only. The
`space_worktree_link_space_fk` cascade removes its memberships. Worktrees and
their Canvas trees survive because a named Space is an M:N organizational
view.

Run stop and storage selection for Space delete must use exact `space_id`
affinity. Stopping every run on every linked Worktree would also stop runs
launched from the default Space or another named Space.

### Worktree

Deleting a Worktree removes:

1. Its `space_worktree` row.
2. Every membership through `space_worktree_link_worktree_fk`.
3. Its root Canvas and anchored user Canvas subtree through
   `canvas_anchor_worktree_fk` and `canvas_parent_fk`.

Before the Worktree delete, clear `default_worktree_id` on user Canvases
anchored elsewhere that point at the target. The deferred
`canvas_default_worktree_fk` otherwise rejects the transaction. The target
root Canvas points to its own Worktree and is removed by the anchor cascade.

The `session` and `run_lifecycle_event` affinity columns have no FK to the
Space tables. They survive as the required tombstones.

## Durable finalization finding

### Verdict

There is no trustworthy per run capture finalization signal at `7ffba78b`.
`RUN_EXITED` proves a lifecycle attempt. It does not prove that every wire IR
and transcript event reached Postgres.

This blocks production run directory removal.

### Evidence

1. `CaptureLeaseRegistry.release_capture` waits for
   `CapturedRunLease.close`, then writes `RUN_EXITED`.
2. `CapturedRunLease.close` calls `ProcessSupervisor.terminate_all`.
3. `ProcessSupervisor.terminate_all` waits up to five seconds, then can send
   `SIGKILL`. It does not report whether graceful shutdown completed.
4. A graceful mitmdump exit reaches
   `TransportMattersAddon.done` and `close_capture_runtime`.
5. `close_capture_runtime` performs the correct broad order: final transcript
   poll, live drain, wire drain, drift drain, dispatcher drain, lifecycle
   write, writer close.
6. `WireStoreObserver.aclose` gathers pending writes with
   `return_exceptions=True`. `SessionWriter.submit_wire_exchange` also returns
   `WireExchangeCommitResult(ok=False)` for best effort failures.
7. `TranscriptTailer.stop(drain=True)` can leave a pending future that becomes
   complete only while `ShardedCommitDispatcher.aclose` drains. No later
   per cursor proof checks that result.
8. The same `RUN_EXITED` can therefore follow a successful drain, a swallowed
   DB failure, or a forced proxy kill.

The standalone capture path has the same proof gap. Its global close drains
work before writing `RUN_EXITED`, but it does not aggregate a successful
capture result.

### Required contract

S3b needs a durable run capture state separate from process lifecycle. A
recommended shape is a `run_capture_state` table keyed by owner and run ID:

| Field | Purpose |
|---|---|
| `owner`, `run_id` | Stable identity |
| `workspace_slug`, `workspace_hash` | Default managed path identity |
| `storage_root` | Exact launch storage locator |
| `storage_owned` | Whether Transport Matters may recursively remove this root |
| `state` | `active`, `finalized`, or `collected` |
| `finalized_at` | Durable capture barrier completion |
| `collected_at` | Successful filesystem removal |
| failure summary | Observable reason a run remains preserved |

The capture process may write `finalized` only after all of these conditions
hold:

1. No provider flow can produce another tier 1 write.
2. The transcript tailer has performed its final read.
3. Every accepted transcript batch has committed, or its byte window has
   reached the durable quarantine table.
4. Every accepted wire write returned `ok=True`.
5. The finalization row commits in Postgres.

A forced shutdown, queue failure, DB failure, or unresolved cursor leaves the
state unfinalized. Both run end and target delete then preserve the directory
and report the reason.

`RUN_EXITED` remains the process death certificate. The new state is the only
garbage collection authorization.

## Shared tier 1 garbage collection design

### Neutral primitive

Place the one filesystem primitive in:

`api/src/transport_matters/storage/tier1_gc.py`

It accepts explicit, deduplicated run candidates and returns structured
statistics. It has no Space, Canvas, HTTP, MCP, or Postgres imports.

Each candidate carries:

1. Run ID.
2. Exact storage root.
3. An ownership proof.
4. A durable finalized proof supplied by the coordinator.

The primitive:

1. Preserves every candidate when the settings policy opts out.
2. Rejects an unfinalized or unowned candidate.
3. Validates managed default paths under `default_workspaces_root`.
4. Renames an eligible directory to a sibling staged deletion name.
5. Removes the staged directory through the shared storage executor.
6. Restores the original name when recursive removal fails.
7. Deduplicates by canonical directory path because several sessions may
   share one run ID.
8. Never receives or resolves a user source path.

Extract generic stage and restore functions from
`DiskStorageFileOpsMixin._stage_exchange_delete` so exchange deletion and run
deletion share the same directory operation.

### Coordinator

A Postgres aware coordinator in the session layer should:

1. Resolve target session rows to distinct run IDs.
2. Join each run to its durable capture state.
3. Construct default roots with `run_root_for_workspace`.
4. Pass eligible candidates to `storage/tier1_gc.py`.
5. Mark successful candidates `collected`.
6. Leave normalized IR, events, sessions, and lifecycle rows intact.

Future Canvas delete selects by `canvas_id` and calls the same coordinator.
No target specific recursive delete belongs in Space or Canvas modules.

### Observable result

Return and log a `Tier1GcStats` value with at least:

1. Candidates considered.
2. Directories removed.
3. Missing directories.
4. Development preserved.
5. Unfinalized skipped.
6. Unowned override skipped.
7. Stop failed skipped.
8. Filesystem failures.

Logs include owner, run ID, storage root, trigger, and reason. They never
include captured bytes.

## Trigger 1: run end and reap

### Managed Gateway run

1. Gateway settles the PTY and calls the capture release RPC.
2. The capture lease stops the client and proxy.
3. Capture shutdown runs the strict finalization barrier.
4. Capture shutdown commits `run_capture_state=finalized`.
5. `CaptureLeaseRegistry.release_capture` observes the finalized row.
6. Production calls the shared primitive with the exact spawn storage root.
7. Development records preservation and leaves the directory.
8. Lifecycle `RUN_EXITED` remains independently durable.

The Gateway's current five second release timeout must be reviewed with the
finalization budget. A timeout cannot lead to garbage collection.

### Detached CLI run

After `run_client_with_retry` returns and mitmdump has exited, the local launch
wrapper checks the same finalized row and calls the same primitive. This hook
runs before the launch forgets its exact storage locator.

`cli/instances._reap` becomes a crash backstop. A stale manifest can supply its
recorded storage path, but reap removes the directory only when the durable
state says finalized and the ownership policy permits it.

## Trigger 2: target delete

Use one `SpaceDeletionCoordinator` shared by REST and MCP.

### Common order

1. Authorize Director access and load the target under the owner.
2. Snapshot distinct session capture references before changing Space rows.
3. List active runs through `RunManagementPort`.
4. Request termination for every matching run.
5. Record which runs reached a confirmed terminal result.
6. Commit the Space database mutation.
7. In production, garbage collect only finalized and safely owned roots whose
   run stop succeeded or whose run was already absent.
8. Preserve every uncertain candidate for the later sweep.

No filesystem call runs inside the Space transaction.

### Space delete

List and stop by exact `space_id`. Delete the named Space row and let its links
cascade. Keep Worktree and Canvas rows.

### Worktree delete

List and stop by exact `worktree_id`. In one transaction:

1. Clear foreign Canvas defaults that point at the target Worktree.
2. Delete the Worktree row.
3. Let anchored Canvas and membership rows cascade.

The source directory remains present. The mutation never passes
`StoredWorktree.path` to a filesystem API.

### Future Canvas delete

Select sessions by exact `canvas_id`, stop exact Canvas runs, delete the Canvas
subtree, and pass the same capture candidates to the same coordinator and
filesystem primitive.

## Dangling sweep

The sweep uses `iter_run_dirs(default_workspaces_root())` and compares each run
ID with durable session and capture state.

An orphaned default run directory with no session row is eligible only when
its capture state says finalized. This preserves the hard durability
invariant when session creation or ingestion failed.

The sweep must distinguish:

1. Finalized directory with no session row: remove in production.
2. Active or unfinalized directory with no session row: preserve and report.
3. Finalized DB state whose directory is already absent: mark collected or
   missing without deleting normalized IR.
4. Intentionally collected storage: expected absence.

`sweep_wire_store` remains the authority for DB only orphaned component rows.
Tier 1 collection must not delete normalized wire exchanges or transcript
events.

## Mandatory STEP 0

`api/src/transport_matters/space/store.py` is 693 lines at the reviewed head.
Extract before adding `delete_worktree`.

Recommended behavior preserving extraction:

1. Move `_SPACE_INVENTORY_SELECT_SQL` and the row conversion helpers into
   `space/store_rows.py`.
2. Keep `SpaceStore` as the query and mutation facade.
3. Add a fresh interpreter import test because prior neutral seam moves have
   exposed cycles only outside pytest's warmed module cache.
4. Commit this extraction separately before S3a behavior changes.

This reduces `store.py` by roughly one hundred lines and gives new delete SQL
room without approaching the 700 line limit.

## Slice plan

### S3a: delete and stop

#### Tests first

1. Worktree delete removes its Worktree row, root Canvas, user Canvas subtree,
   and all memberships.
2. Worktree delete clears a default pointer from a Canvas anchored elsewhere.
3. Worktree delete retains `session` and `run_lifecycle_event` tombstones.
4. Space delete removes only the named Space and its links.
5. Space delete stops runs selected by exact Space affinity.
6. Worktree delete stops runs selected by exact Worktree affinity.
7. Multiple active runs are each terminated once.
8. A stop failure follows the adjudicated policy and never causes filesystem
   removal.
9. REST and MCP return equivalent typed errors for missing, protected, and
   unauthorized targets.
10. A sentinel inside the user source directory survives every delete test.
11. A mutation test makes any call that removes the source directory fail the
    suite.

#### Build

1. Perform STEP 0 as a behavior preserving commit.
2. Add owner scoped `SpaceStore.delete_worktree`.
3. Add the shared `SpaceDeletionCoordinator` with an injected
   `RunManagementPort`.
4. Route current Space delete through the coordinator.
5. Add REST `DELETE /v1/worktrees/{worktree_id}`.
6. Add typed MCP `worktree_delete`.
7. Keep all filesystem behavior out of S3a.

### S3b: finalization and shared garbage collection

#### Tests first

1. Delay a transcript commit and prove run end cannot remove the directory.
2. Delay a wire commit and prove run end cannot remove the directory.
3. Return `WireExchangeCommitResult(ok=False)` and prove no finalized state is
   written.
4. Force proxy kill before drain and prove no finalized state is written.
5. Complete every event and wire commit, then prove finalized state commits
   before directory removal.
6. Production run end removes the exact default run directory.
7. The development setting preserves the same directory.
8. Worktree and Space delete remove each eligible directory once, even when
   several sessions share the run ID.
9. An unfinalized run survives target delete.
10. A stop failure preserves the run directory.
11. The dangling sweep removes a finalized orphan run directory with no
    session row.
12. The dangling sweep preserves an unfinalized orphan.
13. A path outside the managed root is rejected unless the adjudicated
    ownership contract marks it removable.
14. A staged recursive removal failure restores the original directory.
15. A missing directory produces an observable stat and leaves DB IR intact.
16. Development mode makes every trigger and sweep filesystem inert.
17. A sentinel inside the user source directory survives run end, target
    delete, and dangling sweep.

#### Build

1. Add the adjudicated durable capture state migration and DAO.
2. Add strict transcript and wire drain result aggregation.
3. Commit finalized state only after the strict barrier.
4. Add the policy setting and environment test.
5. Add `storage/tier1_gc.py` and extract shared staged directory operations.
6. Add managed and detached run end hooks.
7. Add the garbage collection call to `SpaceDeletionCoordinator`.
8. Add the dangling sweep at the adjudicated trigger.
9. Update `_reap` as the stale manifest backstop.
10. Document the production and development storage lifecycle.

## Open design forks

### A. Explicit `--storage-dir`

Current behavior is unsafe for whole directory removal:
`cli/launch_runtime.py::resolve_storage_dir` treats an explicit path as
caller owned and uses it verbatim. It may contain unrelated user files. The
manifest records the path only while live, and the DB retains no locator.

Options:

1. Skip all explicit overrides and report `unowned_override`.
2. Make the option a base directory and allocate an owned
   `<base>/<run_id>/` child.
3. Require an empty directory plus an ownership marker before launch.

Recommendation: choose option 2 as a deliberate pre release contract change.
Until that choice lands, skip override roots for every recursive garbage
collection path.

### B. Dangling sweep trigger

Options:

1. Scan the complete default tree after every target delete.
2. Run a separate maintenance command.
3. Run a bounded startup or scheduled sweep.

Recommendation: use a separate explicit tier 1 garbage collection command
with a dry run view, then an explicit apply action. Exact target and run end
garbage collection remain automatic. This keeps an O(all history)
irreversible scan out of ordinary delete latency.

### C. Settings name and default

Options:

1. `preserve_tier1: bool = False`, exposed as
   `TRANSPORT_MATTERS_PRESERVE_TIER1=true` for development.
2. `tier1_gc_enabled: bool = True`, exposed as
   `TRANSPORT_MATTERS_TIER1_GC_ENABLED=false` for development.

Recommendation: option 1 states the exceptional behavior directly. Production
defaults to collection, and development opts into preservation. Do not derive
this from `channel`.

### D. Stop failure

Options:

1. Fail the complete delete before DB mutation.
2. Continue DB deletion, preserve all uncertain run directories, and let the
   finalized dangling sweep retry later.

The settled run stop wording is best effort. Recommendation: option 2, with a
clear partial result in MCP and structured logs for REST. Garbage collection
still requires confirmed finalization, so an active or stuck run cannot lose
its storage.

### E. Durable finalization authority

Options:

1. Extend `run_lifecycle_event` with a capture finalized event.
2. Add a dedicated `run_capture_state` table and strict writer path.

Recommendation: option 2. Lifecycle emission is intentionally best effort and
already conflates graceful and forced process exit. A separate state gives
garbage collection a narrow, enforceable contract and stores the exact path
ownership facts needed after the manifest disappears.

### F. Intentional raw absence

After production collection, `wire_exchange.exchange_id` no longer resolves
to raw tier 1 bytes. The DB should distinguish intentional collection from
accidental loss.

Recommendation: keep normalized IR and events, mark the run state
`collected`, and make raw resource reads report an intentional collected
reason. Do not delete DB IR to make the pointer disappear.

## Quality map

| Risk | Required control | Proof |
|---|---|---|
| Premature raw deletion | Dedicated finalized state written after a strict barrier | Delayed and failed commit tests stay green only when the directory survives |
| Recursive delete escapes managed storage | Canonical containment and ownership proof | Outside root and traversal candidates are rejected |
| Explicit override contains user files | Skip or allocate a managed child | Override fixture with unrelated sentinel survives |
| Active run writes into a removed root | Stop first and require finalized state | Call order test and stuck run retention test |
| Space M:N overreach | Select active and historical runs by exact `space_id` | Other Space run and storage survive |
| Duplicate session references | Deduplicate canonical run paths | Two sessions for one run produce one removal |
| Deferred FK failure | Clear foreign defaults, then delete Worktree in one transaction | Cross Worktree default test commits |
| Partial recursive removal | Stage, remove, restore on failure | Injected recursive removal failure restores the directory |
| Development data loss | One Settings boolean gates every trigger | Run end, delete, and sweep are inert under the flag |
| Silent partial completion | Structured stats and reasoned logs | Tests assert counts for removed, preserved, missing, and failed |
| User checkout mutation | No source path enters the primitive | Source sentinel survives all integration tests |
| Dangling false positive | Require finalized state even when no session exists | Unfinalized orphan survives |

## Verification gates for implementation

Each slice should run:

1. Focused Space, storage, capture lifecycle, and API tests.
2. Mutation proofs for finalization and source directory safety.
3. `just check`.
4. `just test-affected`.
5. `just test`.
6. `just api migration-smoke` for S3b.
7. A final repository search proving no target specific `rmtree` copy exists.
8. A file length check proving every touched and new file remains below 700
   lines.

The external plan is read only with respect to the repository. No source file,
Git checkout, or branch state changes are part of this scout.
