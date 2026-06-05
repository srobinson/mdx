<!-- markdownlint-disable MD013 -->

# S2 claims and leases fix re-verification

## Verdict

Reviewed range:
`7df0d907a505e7c7633567143518880192106757..6e644363a0876a93cb26e2f39cba4b83bdf74787`.

Direct result:

1. M1: **CONFIRMED**
2. M2: **NOT CONFIRMED**
3. M3: **CONFIRMED**
4. M4: **CONFIRMED**
5. m1: **N**
6. m2: **Y**
7. m3: **Y**

Builder trust remains **verification only**.

## Confirmed fixes

### M1

`capture_rpc_routes._durable_claim_guard` locks a pending claim and its live, unexpired,
uncancelled lease for the complete capture preparation. A cancelled claim cannot pass
`lock_preparable_claim`.

The regression creates a real claim, cancels it, submits the original prepare payload,
expects `409 bind_conflict`, and proves the capture preparation fake was not called. This
reproduces the original late cancelled then prepare failure.

### M3

`RuntimeCreateTracker` now stores every create by `resourceId` in `pending`, while the
owner plus idempotency key map is a separate coalescing index. Inventory reads the identity
map. Cancellation first marks the local pending create, then requests durable cancellation.

The regression blocks `claimResource` before the fake records the durable claim, lists the
unkeyed resource, cancels that exact identity, resumes the claim, and proves creation rejects
as cancelled. The focused Vitest case passed.

### M4

`PlainTerminalSessions.open` now checks cancellation after `resolveClaimCwd`, heartbeats, and
checks again immediately before spawn.

The regression suspends directory resolution. Its queued results make the first two checks
false and the new post-resolution check true. On the old implementation the true result is
never consumed and the PTY spawns, so this is a valid red to green race regression. The
focused Vitest case passed and no PTY was created.

### m2

The runtime boundary parses `canvasId` through the shared UUID primitive and rejects empty,
nonstring, and malformed UUID values as `invalid_request` before claim creation. Python also
collapses internal Canvas parse failures to `invalid_request`. No `invalid_canvas_id` symbol
remains. The focused runtime route test passed.

### m3

`GatewayRunView` now requires aliased `resourceId` and nullable `canvasId`. A focused model
probe rejected a response missing both fields. Proxy tests assert both decoded values.

## Remaining issue 1: M2 still releases a guard around prepared, unbound work

The bound failure path is repaired. `request_resource_cancellation` preserves the live claim
and lease when `run_id` is present, and the new failing termination regression proves a
running claim remains visible with its lease after failed or unknown termination.

One mid-flight schedule remains:

1. Python holds the preparable claim lock while `CaptureLeaseRegistry.prepare_capture`
   creates and registers the external capture.
2. The prepare transaction commits before Node receives the response and calls
   `bindResource`.
3. A waiting cancellation acquires the claim row during this interval. The durable
   `run_id` is still null, so `request_resource_cancellation` transitions the claim to
   `cancelled` and deletes the lease.
4. `RunTerminationCoordinator` sees the inventory item's null `run_id` and reports
   `closed` without calling `terminate_run`.
5. Node normally notices local cancellation and releases the capture later. A Node crash
   or a forced delete proceeding immediately after the closed receipt leaves prepared work
   without its durable guard.

The same class of interval exists for a plain terminal after the final cancellation check and
PTY spawn, before `bindResource`.

The guard must remain live until prepared or spawned work is either bound and terminated, or
its creating operation has settled and cleanup is confirmed. Add a regression that suspends
bind after external preparation, requests force cancellation, and proves the close receipt
cannot precede capture or PTY cleanup.

Relevant seams:

1. `capture_rpc_routes.py:421-452`
2. `RunManager.ts:202-237`
3. `PlainTerminalSessions.ts:114-126`
4. `runtime_claims.py:465-485`
5. `run_termination.py:95-115`

## Remaining issue 2: m1 fails open when locked branch observation fails

The successful observation path is correctly moved under the row and owner scope locks, and
the regression proves a stale pre-lock projection is ignored.

`runtime_claims._observe_branch` catches `SpaceDetectionError` and returns null. This turns a
Git observation failure into a nullable detached or plain branch stamp. The locked S2 spec
requires temporary inability to enrich Git facts to fail closed. A focused probe forced the
detector to raise and observed a null result.

Propagate this as `worktree_unavailable` and assert no claim or lease is inserted when the
locked branch observation fails.

Relevant seam: `runtime_claims.py:683-687`.

## Verification

1. Exact HEAD: `6e644363a0876a93cb26e2f39cba4b83bdf74787`.
2. `git diff --check 7df0d907..6e644363` passed.
3. Focused M3, M4, and malformed Canvas Vitest cases passed.
4. The focused gateway model probe rejected missing `resourceId` and `canvasId`.
5. Focused PostgreSQL cases for M1, M2, and m1 could not start because no Transport Matters
   test database setting is available in this runtime.
6. The tracked tree remained pristine.
