<!-- markdownlint-disable MD013 -->

# S2 claims and leases Round 2 re-verification

## Verdict

Reviewed range:
`6e644363a0876a93cb26e2f39cba4b83bdf74787..09dbc291f1eedd4e6d70ce75aa4c01629a06fb8d`.

1. M2: **NOT CONFIRMED, same class**
2. m1: **N**
3. Builder trust remains **verification only**

## M2 remains open

### Durable release precedes managed capture cleanup

The new Python cancellation waiter returns when the claim is cancelled and its lease is absent.
After bind resumes, `rejectCancelledClaim` calls `releaseResourceBestEffort` before throwing.
That durable release can wake the waiter and produce the close receipt. Only afterward does the
`RunManager.createNew` catch call `releasePreparedCaptureForCreateError`.

The close receipt can therefore precede proxy and capture lease cleanup. A failed
`releaseCapture` can leave external work without its durable guard.

The managed regression in `RunManager.idempotency.test.ts` embeds the desired ordering in its
fake. Its replacement `requestResourceCancellation` explicitly awaits `cleanupConfirmed`, so it
cannot prove that the production Python waiter observes external cleanup.

Relevant seams:

1. `packages/runtime/src/service/runtimeClaims.ts:132-188`
2. `packages/runtime/src/service/RunManager.ts:236-240`
3. `api/src/transport_matters/api/v1/runtime_claim_routes.py:173-183`
4. `api/src/transport_matters/api/v1/runtime_claim_routes.py:299-317`

### Bind can commit before cancellation classifies the resource

Both new runtime regressions hold bind before calling the original `bindResource`. They cover
cancellation winning the bind race.

The opposite schedule remains:

1. Inventory reads an unbound running resource.
2. Bind commits `run_id`, while its response is delayed.
3. Cancellation locks the now bound row, sets `cancel_requested`, and returns without waiting.
4. `RunTerminationCoordinator` uses the earlier null `run_id` and returns a closed receipt
   without terminating the bound resource.

This schedule applies to managed captures and plain terminals. It preserves the original M2
failure class because the close receipt can precede cleanup.

Relevant seams:

1. `api/src/transport_matters/space/runtime_claims.py:293-308`
2. `api/src/transport_matters/space/runtime_claims.py:465-486`
3. `api/src/transport_matters/controlplane/run_termination.py:95-115`

## m1 remains open

`_observe_branch` now maps a raised `SpaceDetectionError` to `worktree_unavailable`, and its new
database regression correctly asserts zero claims and leases for that injected exception.

The production detector converts `OSError` and `subprocess.TimeoutExpired` into a synthetic Git
return code 127. `detect_worktree_branch` then returns `None`. `_observe_branch` accepts that as a
detached or plain branch result, so the locked claim path continues to lease and claim insertion.

Focused probes that forced either `OSError` or `TimeoutExpired` from `subprocess.run` both
observed `detect_worktree_branch(...) == None`. The claim path therefore still lacks a strict
observation result that distinguishes a legitimate null branch from unavailable Git enrichment.

Relevant seams:

1. `api/src/transport_matters/space/detection.py:133-138`
2. `api/src/transport_matters/space/detection.py:208-239`
3. `api/src/transport_matters/space/detection.py:281-298`
4. `api/src/transport_matters/space/runtime_claims.py:228-255`
5. `api/src/transport_matters/space/runtime_claims.py:688-692`

## Verification

1. Exact HEAD: `09dbc291f1eedd4e6d70ce75aa4c01629a06fb8d`.
2. `git diff --check 6e644363..09dbc291` passed.
3. The focused managed bind suspension Vitest case passed.
4. The focused plain terminal bind suspension Vitest case passed.
5. The focused cancellation RPC timeout exception Vitest case passed.
6. Focused PostgreSQL cases collected four tests but could not start because no Transport
   Matters test database URL is configured.
7. The tracked tree remained pristine.
