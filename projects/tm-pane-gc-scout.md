# Exited pane residue scout

## Scope and verdict

Read only inspection of detached `main` at `ade9c3563471e200fa30a7a78bf0650b084da044`.
No captured run, Postgres, Keychain, Library, or channel home was inspected or changed.
During final validation the shared checkout advanced externally to its direct child
`f56cd4f09118d1954cc9bb52b9dec5c6803b86e9`. The scoped source and test files have no
diff between those commits. The final shared worktree is clean.

A natural captured run exit retains five of the eight requested artifact classes:

1. Canvas pane state and its captured run binding.
2. The mounted renderer terminal and its capped scrollback.
3. The process resident `RunManager` record.
4. The durable run directory.
5. Postgres history.

The PTY, allocated ports, and per run proxy are released during normal settlement. The
server terminal emulator also disposes its buffer. The renderer terminal stays mounted
because the pane stays visible.

The live accumulation is in Canvas and `RunManager`. Disk and Postgres also grow once per
run, but the owner's `just reset` cycle bounds both by deleting the whole selected channel
home and recreating the selected channel database.

Cleanup exists. Manual pane close removes the pane, run binding, and renderer terminal.
Route mount reconciliation also removes every remembered run whose current state is not
`STARTING` or `RUNNING`. Natural exit deliberately does not call either path. `RunManager`
has no per run record deletion path.

## Per run artifact table

Counts below are artifact classes. A row may contain more than one concrete record.

| Artifact class | What one natural exit leaves | Owner symbol | What removes it today | What does not remove it |
| --- | --- | --- | --- | --- |
| Canvas tree nodes | One open pane record plus layout node and order entry, or one dock entry. One separate persisted `CapturedRunRecord` binds the pane key to the run id. | `www/packages/canvas/src/model/canvasActions.ts:createPaneLifecycleActions`, `www/packages/canvas/src/model/capturedRunStore.ts:useCapturedRunStore` | Manual `closePane` or `closeDockedPane` invokes `capturedRunLifecyclePolicy.onClose`, then `stopRun`. Remote `run_closed` invokes `dropRun` and `dropCapturedRunPane`. `SessionCanvasRoute:reconcileCapturedRuns` prunes non attachable remembered runs after rehydration. | `run_exited`, `run_shutdown`, and `capture_lost` do not drop the pane or binding. `CapturedRunPane:AttachedRunTerminal` only drops on `run_closed`. |
| `RunManager` entries | One `ManagedRuntimeRun` remains in `runs`. Normal Canvas launches also leave one completed `PendingCreate` entry because the successful idempotency key stays in `pendingCreates`. | `packages/runtime/src/service/RunManager.ts:RunManager` | Gateway process exit releases the maps with the process. There is no explicit per run map remover. | Natural exit, explicit close, capture loss, and `RunManager.close` settle records but never delete either successful map entry. A closed live run remains listable as `TERMINATED`; a naturally ended run remains listable as `EXITED`. |
| Run directory under channel home | One `workspaces/{slug}/{hash}/{run_id}` directory. A standard managed launch leaves a zero byte `lock`, durable `sessions.json`, `logs/mitmdump.log`, optional `compatibility.json`, transcript snapshots, and per exchange wire artifacts. `manifest.json` is absent after cleanup. | `api/src/transport_matters/workspace.py:run_root`, `api/src/transport_matters/storage/disk_layout.py:DiskStorageLayout` | `just reset` calls `scripts/reset-channel-store.sh`, which sweeps the whole selected channel home. No ordinary per run remover exists. | Natural exit, explicit pane close, gateway close, backend close, and self reap preserve tier 1 history. |
| Postgres rows | Normally two fixed lifecycle rows, `run-started` and `run-exited`, because `(run_id, event_type)` is the primary key. Emission is best effort, so failures can reduce that count. Session, event, live status, wire exchange, normalized wire, compatibility audit, and control plane rows vary with run activity. | `api/src/transport_matters/capture_rpc.py:CaptureLeaseRegistry._emit_lifecycle`, `api/migrations/versions/0007_run_lifecycle_event.py:upgrade` | `just reset` drops and recreates the selected channel database, then migrates it to head. Exchange deletion and wire store sweeping address selected wire rows and shared unreferenced blobs, not normal run exit. | Natural exit, pane close, runtime close, and app quit retain history. |
| PTY handle | Nothing live. The record still references a disposed `PtySession` shell. Node PTY subscriptions and listeners are disposed. | `packages/runtime/src/service/RunManager.ts:RunManager.performSettle`, `packages/runtime/src/adapters/NodePtyAdapter.ts:NodePtySession.dispose` | Every settlement path calls `session.dispose`. Explicit settlement first sends `SIGTERM`, then `SIGKILL` after the grace budget if needed. Natural child exit also makes `NodePtySession` dispose itself. | A direct, uncatchable gateway kill cannot execute JavaScript cleanup. Process exit closes the gateway's own handles, but static source does not prove every descendant has completed. |
| Ports | Nothing bound after a successful release. A managed captured run has a proxy port and, for the embedded topology, a web port. | `api/src/transport_matters/captured/models.py:CapturedRunLease.close`, `api/src/transport_matters/supervisor/core.py:ProcessSupervisor.terminate_all` | Capture lease close terminates the proxy process, which releases its sockets. Backend registry close is a backstop. OS process exit also releases sockets. | A release RPC failure or direct gateway death can leave the Python lease and proxy live until backend shutdown or proxy parent death. |
| Proxy instance | Nothing live after a successful release. | `api/src/transport_matters/captured/models.py:CapturedRunLease.close`, `api/src/transport_matters/capture_rpc.py:CaptureLeaseRegistry.release_capture` | Normal settlement releases the capture. Registry close terminates all remaining leases. `self_reap.install_parent_death_reaping` makes a proxy terminate itself when its Python parent dies, with a 20 second forced exit backstop. | Direct gateway death does not kill the Python owned proxy. The lease persists in the backend registry until registry shutdown because the proxy watches its Python parent. |
| Scrollback rings | The server `TerminalEmulator` is disposed. If the exited pane remains mounted, its renderer xterm remains alive with up to 10,000 scrollback lines so final output stays readable. | `packages/runtime/src/service/TerminalEmulator.ts:TerminalEmulator.dispose`, `www/packages/canvas/src/viewers/terminal/terminalSession.ts:useTerminalSession` | Server settlement disposes server scrollback. Pane close, route reconciliation, renderer shutdown, or any other unmount invokes `term.dispose` for renderer scrollback. Minimizing also unmounts the open pane surface. | Natural `run_exited` closes the socket but does not unmount the pane, so renderer scrollback remains. |

## Exit, close, crash, and quit

### Normal end and harness crash

The PTY exit callback has one path for exit code zero, nonzero exit, and terminal error:
`RunManager.register` records the exit code and calls `settleRun` with `natural-exit`.
`performSettle` then:

1. Stops the capture health monitor.
2. Marks the view `EXITED`.
3. Closes all terminal attachments with `run_exited`.
4. Disposes the PTY session.
5. Disposes the server terminal emulator.
6. Releases the capture with the exit code.

The capture registry pops its lease and facts before closing the lease. The lease terminates
the proxy, removes the manifest, releases the file lock, removes ephemeral runtime home and
grant resources through its `ExitStack`, and emits the `run-exited` lifecycle row.

The Canvas sees `run_exited`. `CapturedRunPane:AttachedRunTerminal` explicitly retains every
ending except `run_closed`, which leaves the final renderer output visible.

### Explicit close and dismissal

Canvas close is the dismissal operation. There is no separate `DISMISSED` runtime state.
`closePane` and `closeDockedPane` remove the visual pane and call
`capturedRunLifecyclePolicy.onClose`. `stopRun` posts termination, then forgets the persisted
binding after the request succeeds.

For a live run, runtime state reaches `TERMINATED` with end reason `explicit`, and attached
viewers receive `run_closed`. For an already exited run, the memoized first settlement wins,
so its runtime state remains `EXITED`; the close request still succeeds and the Canvas removes
the pane and binding. In both cases the `RunManager` record remains.

Minimize is distinct. It removes the open surface, docks the pane, disposes that renderer
terminal, and persists `minimized: true`; it does not terminate or forget the run.

### Crash cases

* Harness crash is the normal PTY exit path above.
* Proxy or Python capture loss is polled every three seconds in the real gateway. The health
  monitor settles the run as `FAILED`, terminates the PTY, disposes server terminal state,
  and retains the Canvas pane because the close reason is `capture_lost`.
* Proxy parent death arms `self_reap`. On POSIX it sends the proxy `SIGTERM`; after 20 seconds
  it calls hard exit if graceful drain has not completed. The addon can emit an `orphaned`
  lifecycle row before that backstop.
* Direct gateway hard kill skips `RunManager.close` and its release RPCs. The in process maps
  disappear with the gateway, but the Python registry can retain the proxy lease, proxy, and
  ports until backend shutdown. Source alone does not certify descendant PTY completion on
  that path.

### Graceful app quit

`DesktopLifecycle.registerShutdownHooks` routes `before-quit`, `SIGINT`, and `SIGTERM`
through `DesktopShutdown`. The finalizer order is gateway first, backend second.
Gateway shutdown calls `RunManager.close`, settling all runs in parallel while Python can
still receive release RPCs. Backend lifespan close then closes any remaining capture leases.

The renderer does not delete persisted Canvas nodes or captured run bindings before quit.
They remain in Electron local storage until the next Canvas route mount. On that mount,
`SessionCanvasRoute:reconcileCapturedRuns` looks up every remembered run and drops any state
outside `STARTING` or `RUNNING`. A new gateway returns no process resident records, so stale
exited panes are pruned. The existing test
`SessionCanvasRoute.identity.test.tsx:prunes an exited remembered run only after its cached Canvas rehydrates`
pins this behavior.

On macOS, closing the last window does not quit by default:
`DesktopLifecycle.shouldQuitOnWindowAllClosed` returns false for Darwin unless the caller opts
in. A real app quit runs the coordinated finalizers.

Desktop launched gateways arm a stdin EOF parent watch. If Electron dies, including by
`SIGKILL`, the closed pipe asks the gateway to run its normal shutdown. This improves the
desktop death path but does not make app close a universal GC trigger. Direct gateway
`SIGKILL`, power loss, and process termination before event loop drain cannot run the
JavaScript finalizers.

## Accumulation and bounds

### Process and renderer memory

Per normal Canvas launch and exit:

* Canvas adds one pane or dock record, one captured run binding, and, while visibly mounted,
  one renderer xterm.
* `RunManager` adds one managed run entry.
* The ordinary idempotent create path adds one successful `pendingCreates` entry.

None has a count cap or exit eviction. Renderer scrollback is bounded per mounted pane at
10,000 lines. Aggregate renderer memory is unbounded by run count. The disposed server
emulator no longer carries an active 10,000 line buffer, though its small disposed object
shell remains reachable through the `RunManager` entry.

### Disk

Disk growth is one run directory per launch. Bytes are workload dependent:

* `lock` is zero bytes and persists.
* A static unit fixture with one short owned session serializes `sessions.json` to 353 bytes.
  Production identifiers, paths, descriptors, and template provenance are longer.
* `logs/mitmdump.log`, `compatibility.json`, transcript snapshots, raw request and response
  bytes, normalized JSON, transport metadata, and derived artifacts add variable bytes.

No source level maximum bounds a run directory. `just reset` bounds the selected channel by
the owner's reset interval because it deletes the whole channel home.

### Postgres

Lifecycle contributes normally two rows per run. Other tables scale with sessions, transcript
records, turns, request messages, response blocks, distinct content addressed blobs, audit
actions, and live status. A single byte per run figure is not derivable from schema because
JSON payloads, indexes, TOAST storage, and shared content addressed rows vary.

`just reset` bounds this history by the same owner cycle because it drops and recreates the
selected channel database. Postgres server and cluster lifecycle stay external.

## Existing cleanup reachability

Cleanup is present at two reachable UI seams:

1. Manual close removes a pane now, terminates when necessary, forgets its binding, and
   disposes renderer scrollback.
2. Route mount reconciliation removes persisted bindings and panes for `EXITED`,
   `TERMINATED`, `FAILED`, or missing process resident runs.

Natural exit is not wired to these removers. The socket contract preserves `run_exited`,
`run_shutdown`, and `capture_lost` panes by design. Only `run_closed` removes immediately.
`RunManager` has no record eviction method, so UI cleanup does not shrink its maps.

For app close scoped to exited pane clutter, process memory already disappears with the
gateway and renderer. Persisted Canvas state is cleaned on the next route mount, not during
quit. Tier 1 directories and Postgres rows remain historical records until channel reset.

## Verification

* `pnpm --filter @tm/runtime exec vitest run src/service/RunManager.test.ts src/server/runTerminalConnection.test.ts --reporter=dot`
  passed: 2 files, 48 tests.
* `pnpm --dir www/packages/shell exec vitest run ../canvas/src/model/canvasStore.capturedRuns.test.ts ../canvas/src/viewers/terminal/CapturedRunPane.test.tsx ../canvas/src/workbench/SessionCanvasRoute.identity.test.tsx --reporter=dot`
  passed: 3 files, 55 tests. Existing React `act` warnings were emitted.
* `PYTHONDONTWRITEBYTECODE=1 api/.venv/bin/python -m pytest -p no:cacheprovider -n0 api/src/transport_matters/test_capture_rpc.py api/src/transport_matters/cli/test_captured_run.py api/src/transport_matters/test_self_reap.py api/tests/integration/test_reset_channel_store.py -q`
  passed: 57 tests.
* Static `OwnedSessionFacts` serialization of the existing short unit fixture measured
  353 bytes in process and wrote no file.

No repository or live user state was changed.
