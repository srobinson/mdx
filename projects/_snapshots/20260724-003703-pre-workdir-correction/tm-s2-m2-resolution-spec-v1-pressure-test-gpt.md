<!-- markdownlint-disable MD013 -->

# S2 M2 resolution spec v1 pressure test

## Verdict

1. Design closes both schedules: **N**
2. Schedule 3 exists after a null locked read and before bind.
3. Reconciler sound: **N**
4. m1 sound: **Y**, with strict failure classification at the Git boundary.

## 1. Stale snapshot

Returning `run_id` and state from `begin_resource_cancellation` under `FOR UPDATE` fixes one half
of the stale inventory problem. A bind that commits before cancellation obtains the lock is visible
to cancellation, so the coordinator can terminate that bound run.

The opposite ordering is still open:

1. Cancellation locks a null, running claim.
2. It sets `cancel_requested` and chooses `terminating`.
3. The transaction commits and releases the row lock.
4. `bind_run_id` commits afterward because the proposed design does not require bind to reject a
   cancelled or terminating claim.
5. The coordinator uses its correct locked result, but that result is already stale with respect to
   the late bind.

The receipt is `terminating`, so this does not recreate the exact early `closed` response. It creates
schedule 3: a bound live resource can appear after the decision that skipped termination.

Required design invariant:

- Cancellation must transition the null running claim to `terminating` under the lock.
- `bind_run_id` must be a compare and set operation that rejects `cancel_requested` or any claim
  outside its bindable state.

That yields a complete dichotomy. Bind first means the locked cancellation read sees the run and
terminates it. Cancellation first means a later bind cannot commit.

The lock alone does not provide this invariant because the coordinator decision occurs after the
transaction releases it.

## 2. Close before cleanup

The `terminating` receipt for null running claims prevents that branch from returning `closed`
before cleanup. It is safe only if every later terminal transition is downstream of confirmed
external cleanup.

The bound branch remains underspecified. Current `RunManager.performSettle` returns a terminated
view after `releaseCaptureBestEffort`, even when capture release times out or fails. The current
capture registry also removes the capture handle before `lease.close` finishes. A failed close
therefore has three effects:

1. The gateway can report terminate success.
2. The coordinator can emit `closed`.
3. The reconciler cannot see or retry the leaked capture because the registry discarded its handle.

The spec must define confirmed termination as confirmed PTY, process, and capture cleanup. Timeout
or cleanup failure must produce `terminating` or `unknown`, retain the non-terminal durable claim,
and enqueue reconciliation. A failed capture close must retain a retryable handle or tombstone keyed
by `resource_id`. A reconciler must not transition terminal after a failed force termination.

For the prepared unbound branch, the proposed Node ordering is correct: external release completes
before durable terminal transition. If external release fails, the claim must remain non-terminal.
No waiter may derive `closed` from a best effort durable release.

## 3. Reconciler pressure test

### Orphan with a valid lease

An orphan can evade reaping until its lease expires. That delay is the intended grace window. It can
evade indefinitely if a detached heartbeat loop continues after the live owner disappears. Heartbeat
ownership must be coupled to the same registration that defines live backing, and removal must stop
the heartbeat.

A failed capture close is worse in the current shape. The external process can remain alive while
the capture registry has already removed its handle. Lease expiry identifies a candidate, but the
reconciler has no authority capable of terminating it. Retaining a retryable handle is mandatory.

### Healthy preparation false positive

The spec states that an in-flight preparation heartbeats, but the current lifecycle does not provide
that invariant. Managed heartbeat starts after run registration. Plain terminal performs one renewal
before spawn, then starts its heartbeat after bind and session registration.

A long preparation can therefore cross lease expiry. The row lock delays the reaper until prepare
commits, but a live-set snapshot taken before that commit can still say absent. After the lock is
released, the reconciler can act on expired lease plus stale absence and reap newly created work.

The design needs either a heartbeat owner active from claim acquisition through create settlement,
or a hard creation deadline shorter than the lease TTL with renewal at each external transition.

### Live-set TOCTOU

`FOR UPDATE` serializes durable claim changes. It does not serialize the Node maps, the capture
registry, or PTY registration. Reading a live set, then locking a claim, leaves both stale absence and
stale presence schedules.

A sound sweep needs:

1. Select an expired candidate.
2. Lock and re-read its current claim, lease, cancellation state, and bind state.
3. Move it to a fenced cleanup state that prevents new bind or registration.
4. Query or command the live owners using the same resource identity and fencing generation.
5. Transition terminal only after cleanup confirmation or authoritative absence.

Concurrent reconcilers then serialize on the claim lock, and late creators cannot publish backing
after the cleanup decision.

### Terminating claims with live backing

The proposed `live backing + valid lease heartbeat -> healthy -> skip` rule is incomplete. A
`terminating` or `cancel_requested` claim with live backing is not healthy. Schedule 3 can bind and
register such a resource, then keep its lease valid. The reconciler will skip it forever.

Desired state must outrank liveness. A terminating claim with live backing must be driven toward
confirmed cleanup regardless of lease validity. Lease expiry is the grace gate for abandoned
pending or running claims, not for explicit cancellation already in progress.

### Startup

Reaping every prior process generation is sound under the declared invariant that managed runs,
captures, and PTYs cannot survive an API restart. The sweep must run before current-generation
claims can be created, and it must target an actual process epoch rather than worktree lifecycle
generation.

This remains conditional for externally owned gateway configurations. If any supported gateway or
capture process can survive the Python API, startup must first query or terminate that owner rather
than assume an empty live set.

## 4. m1

The proposed strict detection shape is sound:

- Valid Git observation with detached HEAD returns `None`.
- Plain workspace returns `None`.
- `OSError`, timeout, synthetic return code 127, and any other failed Git enrichment return an
  unavailable result or raise `SpaceDetectionError`.
- `_observe_branch` maps unavailable to `worktree_unavailable` before lease or claim insertion.

The strict path should classify every nonzero Git enrichment result as unavailable unless a specific
nonzero result has an explicit semantic meaning. Tests must cover `OSError`, timeout, return code
127, detached HEAD, and a plain workspace.

## Required spec revisions before build

1. Add a bind compare and set guard against `cancel_requested` and `terminating`.
2. Define cleanup confirmation across process, PTY, and capture release. Cleanup failure cannot
   produce `closed` or terminal durable state.
3. Retain failed capture cleanup handles for reconciliation.
4. Fence live registration against a claim selected for cleanup.
5. Treat explicit `terminating` state as cleanup work even while the lease is valid.
6. Establish heartbeat ownership for the complete creation interval.
7. Define startup ordering and the process epoch used by prior-generation reaping.
