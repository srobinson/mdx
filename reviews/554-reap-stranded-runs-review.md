# Review: #554 reap stranded runs

Reviewed `c66e7b55f39f216851bb3be4736a454a9d367b77` on `fix/554-reap-stranded-runs`.
Blessed. Final head: `32a1416133d4a7fd37192296e1e13ba61de5b838` (local == origin, tree clean).

Branch history: `c66e7b55` implementation, `fba4ab9f` my review pass, `341f70e2` the
implementer's style trim, `32a14161` my restatement of the rationale that trim removed.

Reviewer: `transport-matters:general:1:4.2`. Implementer: pane `1:4.1`.

## Verdict

The design is right. Close retains the durable activity target, attempts live
termination, and on a gateway 404 writes an idempotent `run-exited` row with
`exit_reason=reaped`; only a successful durable write reports `closed`.

## Verified before changing anything

- `launch_kind` really is on the activity wire: `packages/contract/src/activity/wire.ts:118`
  declares it, and `activityRouter` emits `projection.launchKind`. The reap engages in
  production, not only against the test fake.
- The written row genuinely reaps: `packages/activity/src/adapters/postgresRecords.ts`
  derives `exited` via `bool_or(<run-exited filter>)`, so one `run-exited` row flips the
  run terminal and the roster stops listing it as `idle`.
- The emitter is always wired: `_start_session_backed_services` returns early when the
  session store is missing, so `session_pool` at `main.py:344` is non-None and
  `run_lifecycle_emitter` is built on the lifespan loop.
- `close_target` has exactly one caller (`ControlPlaneService.close`).
- Owner safety: `terminate_run` also returns `None` on an owner mismatch, but the activity
  read that produces `target` is owner-scoped, so a foreign run can never reach the reap.

## Changes made on top

1. **One emitter type, not three spellings.** `RunLifecycleEmitter` moved to
   `session/writer.py`, beside the `RunLifecycleCommitResult` it returns, and
   `run_lifecycle_emitter` now declares it instead of respelling the same callable.
   Dropped the `RunLifecycleEmissionResult` protocol: its only implementations are
   `SessionWriter.submit_run_lifecycle_event` and the test fake, which already returns
   the concrete result, so the indirection abstracted nothing. Dependency direction is
   unchanged (writer imports run.lifecycle, never the reverse).
2. **Workspace resolution is a precedence chain.** `capture_rpc` already passes working
   dir, workspace root and identity together and expects the narrowest to win, so
   exclusivity was a rule only the new source imposed. The canonical key joins the chain
   as the most resolved source. Four branches and two raises collapsed into
   `_workspace_parts`.
3. **`close_target` owns the `run_not_found` decision.** The call site had spelled the
   membership test twice (`in` and `.get`); it now passes only `shared_reason`, and the
   invariant `reason is None` iff `target is not None` lives in one place.
4. **Coverage for the guard that decides whether the reap engages.** A target with no
   launch kind is reported `run_not_found` and no exit fact is invented for it.

## Gates

`just check` green and `just test` green in `api/` (4477 passed). No JS, desktop or shell
source touched, so the implementer's full-suite pass at `c66e7b55` still stands there.

## Left for the owner to rule

- `GatewayActivityRun.launch_kind` is bound to the strict Python `LaunchKind` enum, and
  `RUN_LIFECYCLE_LAUNCH_KINDS` / `launchKinds` are two hand-maintained literal lists either
  side of the wire. A TS-side addition would fail validation of the whole activity payload
  and break roster, not just the reap. This matches how `tier` is already handled (while
  `status` is deliberately loose), so the house style was left alone.
- A gateway crash can orphan a live PTY child; close then records an exit for a process
  that may still be running. The control plane has no handle either way and
  `exit_reason=reaped` is honest about it. Not a defect, worth knowing.
- The audit trail records a reap as an ordinary successful close. The reap fact lives only
  in `exit_reason` on the lifecycle row.
