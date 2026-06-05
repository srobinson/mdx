<!-- markdownlint-disable MD013 -->

# S2 M2 resolution spec v2 revalidation

## Verdict

**v2 is not build ready.**

The seven requested revisions are present as intentions. Their combined contracts remain incomplete,
and one new false positive schedule exists between the creation deadline and lease expiry.

## Schedule 4A: renewed creation deadline, stale lease expiry

The acquisition invariant `CREATE_TTL < lease TTL` holds only at acquisition.

1. A claim starts with lease expiry at `t0 + lease TTL` and creation deadline at
   `t0 + CREATE_TTL`.
2. Near lease expiry, a real external transition renews only `create_deadline` to
   `now + CREATE_TTL`.
3. The renewed creation deadline is now later than the unchanged lease expiry.
4. The sweep policy names `create_deadline passed OR lease expired` as create-phase candidacy.
5. The lease expires while the create is still within its renewed deadline.
6. The reconciler fences and reaps a healthy progressing create.

Section 4.5 says create-phase candidacy is the deadline, not lease expiry. Section 4.2 still permits
lease expiry. The two rules conflict.

Required invariant: every create progress mutation must atomically renew both `create_deadline` and
the worktree lease, preserving `lease.expires_at > create_deadline`, or the reconciler and the
existing lease reaper must ignore lease expiry while the durable phase is creating. The phase switch
to running liveness also needs a durable marker, such as clearing `create_deadline` only after fenced
live registration succeeds.

## Schedule 4B: bind first, live registration later

The bind compare and set closes a bind that starts after cancellation. It does not make durable bind
and live owner registration atomic.

1. External capture or PTY creation succeeds.
2. `bind_run_id` commits.
3. Its response is delayed before `RunManager` or `PlainTerminalSessions` publishes the live entry.
4. Cancellation reads the bound run ID under the row lock and calls `terminate_run`.
5. The runtime owner reports `run_not_found` because registration has not happened.
6. The spec treats gone run as a no op or authoritative absence even though a capture or unregistered
   PTY can already exist.

`run_not_found` from one owner is not cleanup confirmation across process, PTY, and capture. The
coordinator must return `terminating`, fence the claim, and obtain confirmation from every relevant
owner. A managed capture must be closed through the capture handle keyed by `resource_id`. A spawned
plain PTY must enter a pending live registry immediately on spawn, before bind, so it remains
terminable during this interval.

## Owner-side fencing handshake

The spec increments `fencing_generation` in Postgres and sends it to live owners. Passing a number is
insufficient by itself.

An owner can validate generation `g`, then the reconciler can fence the claim at `g + 1`, observe the
owner as absent, and terminalize the claim before the owner publishes generation `g`.

Each owner needs an atomic fence protocol:

1. A cleanup command at generation `g` installs a persistent in-process fence floor for
   `resource_id`, even when the owner currently reports absent.
2. Registration is one atomic map operation that rejects any generation below that floor.
3. Cleanup generation `g` terminates retained resources whose generation is less than or equal to
   `g`. It must not reject an older retained capture merely because the claim generation increased.
4. Authoritative absence is accepted only after every relevant owner acknowledges installing the
   fence.

A durable check followed by in-memory publication has the same check-then-publish race and is not
sufficient.

## Seven revision checks

### 1. Bind compare and set

**Partial.** The intended bind-first or cancellation-first dichotomy is correct for the durable bind.
The SQL example references `cancel_requested` as if it were a claim column. It currently lives on
`worktree_lifecycle_lease`, and the v2 schema delta does not add it to the claim. The build spec must
choose one atomic representation: move or duplicate it transactionally on the claim, or make the bind
compare and set lock and test the joined lease.

The pre-registration interval in schedule 4B also needs the owner fence handshake.

### 2. Cleanup confirmation

**Partial.** Process, PTY, and capture confirmation plus non-terminal retry on failure is the correct
contract. It conflicts with the statement that `run_not_found` is a no op. Absence from one owner is
not aggregate cleanup confirmation. A failed or missing owner response must keep the claim
non-terminal.

### 3. Retained capture handle

**Present.** Retention by `resource_id` closes the registry blindness issue if the handle remains
until confirmed close. The spec must also require per-handle serialization for concurrent close
attempts and the cleanup-generation rule above so a generation increment cannot make the old handle
unaddressable.

### 4. Fenced cleanup

**Incomplete.** The durable increment and bind compare and set are correct. Live publication is safe
only with the owner-side persistent fence acknowledgement described above. The current text says
registration carries a generation but does not define what atomically accepts it.

### 5. Terminating outranks liveness

**Correct.** Explicit cancellation must drive cleanup regardless of deadline, lease validity, or live
heartbeat.

### 6. Creation deadline

**Not yet sound.** It avoids a detached create heartbeat, but renewing only at transition boundaries
cannot distinguish a dead operation from one healthy external transition that runs longer than
`CREATE_TTL`. Either every external operation must have a hard timeout shorter than `CREATE_TTL`, or
the chosen design still intentionally kills slow work and must state that policy.

The deadline and lease must also obey the invariant in schedule 4A. The current text simultaneously
calls the deadline the sole create liveness authority and permits lease expiry to reap a create.

### 7. Startup process epoch

**Mostly correct.** Reap before exposing current-epoch creation, and query externally owned gateways
before assuming absence. The missing failure policy matters: if an external owner is unavailable or
cannot prove cleanup, startup must retain prior claims and keep create surfaces closed or degraded.
It must not mark them terminal and proceed.

## Required v2 corrections

1. Resolve create-phase deadline versus lease expiry with one atomic invariant and a durable phase
   switch.
2. Define the owner-side fence floor and atomic registration protocol.
3. Require aggregate absence or cleanup confirmation from every relevant owner.
4. Register spawned PTYs as pending live resources before bind.
5. Define cleanup generation ordering for retained capture handles.
6. Correct the `cancel_requested` storage and compare-and-set contract.
7. Bound each external transition below `CREATE_TTL`, or explicitly accept slow-create cancellation.
8. Define fail-closed startup behavior when an external owner cannot be queried or terminated.

## Build gate

The new deadline and lease conflict is a new reconciler false positive class. The registration and
aggregate confirmation gaps preserve the prior close-before-cleanup class. Revise the spec before the
attempt 4 build.
