<!-- markdownlint-disable MD013 -->

# S2 claims and leases review

## Verdict

Request changes.

Counts: **0 blocker, 4 major, 3 minor**.

Builder trust: **verification only**. The implementation is not trusted for production until the
major findings are fixed and the affected concurrency paths are proved against PostgreSQL.

Reviewed range:
`d7bfb9acbbb2bc193541fd8a18c2db73d07079b8..7df0d907a505e7c7633567143518880192106757`.

The reviewed HEAD is not present on a remote tracking ref. The source links below use the exact local
SHA and will resolve after that commit is published.

## Findings

### Major 1: cancelled claims can still prepare an external capture

[`capture_rpc_routes.py:418`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/api/src/transport_matters/api/v1/capture_rpc_routes.py#L418-L438)
validates identity and affinity only. It does not require a pending claim with a live, unexpired,
uncancelled lease. The prepare route then calls `CaptureLeaseRegistry.prepare_capture` at line 293.

The cancellation endpoint calls `cancel_and_release_resource` at
[`runtime_claim_routes.py:172`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/api/src/transport_matters/api/v1/runtime_claim_routes.py#L172-L180),
which transitions the claim to `cancelled` and deletes its lease at
[`runtime_claims.py:462`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/api/src/transport_matters/space/runtime_claims.py#L462-L476).
A delayed or retried prepare request carrying the original identity and affinity still passes
validation and starts capture preparation after forced release reported the pending resource closed.

Client cancellation checks narrow the common race but cannot enforce a server invariant. Fence
prepare with an atomic claim state and live lease guard, and add a cancelled claim regression test.

### Major 2: forced cancellation releases the durable guard before process termination

[`run_termination.py:95`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/api/src/transport_matters/controlplane/run_termination.py#L95-L115)
calls the cancellation endpoint before `terminate_run`. As described above, that endpoint immediately
marks the claim terminal and deletes its lease.

If the later gateway termination fails or has an unknown outcome, the managed run or plain terminal
can remain alive while its durable claim is terminal and its lease is gone. Default inventory omits
that claim, and future Canvas or Worktree deletion can proceed without seeing the active process.

The durable test at
[`test_run_termination.py:150`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/api/src/transport_matters/controlplane/test_run_termination.py#L150-L202)
uses a termination fake that always succeeds, so it does not exercise this failure state. Preserve
the live lease until termination settles. Pending, unbound claims can still release immediately.

### Major 3: unkeyed managed creates disappear from pending inventory

[`RunManager.ts:173`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/packages/runtime/src/service/RunManager.ts#L173-L194)
adds only idempotency keyed creates to `pendingCreates`. An unkeyed create mints an identity and calls
`createNew` directly. Inventory consumes `pendingCreates` at
[`RunManager.ts:343`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/packages/runtime/src/service/RunManager.ts#L343-L349).

Suspend an unkeyed `claimResource` before it commits, then list resources. Durable inventory is
empty, no registered run exists, and the preallocated identity is absent from `pendingCreates`.
The resource is therefore invisible during the exact interval that the pending inventory union is
meant to cover. It also cannot be selected for forced cancellation.

Track every create by resource identity. Keep idempotency coalescing as a separate index. The current
inventory test blocks capture preparation after the fake claim has already appeared, so it does not
cover this interval.

### Major 4: cancellation during terminal CWD resolution still permits PTY spawn

[`PlainTerminalSessions.ts:93`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/packages/runtime/src/service/PlainTerminalSessions.ts#L93-L130)
runs both cancellation checks at lines 107 and 109. It then awaits `resolveClaimCwd` at line 116 and
spawns at line 117 without another check.

If cancellation arrives while directory validation is suspended, the shell still spawns. The later
running transition can reject and dispose it, but shell startup and profile side effects have already
occurred. Add a cancellation check after CWD resolution and immediately before spawn. Add a focused
test that suspends directory validation, cancels the claim, resumes validation, and proves no PTY was
created.

### Minor 1: branch affinity is observed before the claim locks

[`runtime_claim_routes.py:99`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/api/src/transport_matters/api/v1/runtime_claim_routes.py#L99-L131)
resolves the live Worktree projection before `claim_resource` starts its transaction.
[`runtime_claims.py:192`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/api/src/transport_matters/space/runtime_claims.py#L192-L233)
then locks and rereads database path and Canvas facts, but stamps `worktree.branch_name` from the
earlier projection.

A branch switch between those operations produces a stale branch combined with the locked database
facts. Observe the branch within the locked claim seam, or persist and read the branch fact under that
same lock. Cover the race with a focused regression.

### Minor 2: malformed Canvas affinity is dropped or leaks a forbidden error code

[`runtimeRouter.ts:95`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/packages/runtime/src/server/runtimeRouter.ts#L95-L147)
validates several optional strings with `optionalStringFromBody`, but reads `canvasId` with
`nonEmptyString`. A nonstring or empty value becomes `undefined`, allowing a run outside the requested
Canvas. A nonempty malformed UUID reaches Python, which emits the new `invalid_canvas_id` code at
[`runtime_claim_routes.py:90`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/api/src/transport_matters/api/v1/runtime_claim_routes.py#L90-L97).
The runtime forwards that internal code to the browser at
[`runtimeRouter.ts:457`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/packages/runtime/src/server/runtimeRouter.ts#L457-L465),
contrary to the locked no new client error rule.

Validate `canvasId` at the runtime boundary. Reject malformed values with the existing
`invalid_request` envelope.

### Minor 3: Python accepts gateway run responses without required identity fields

[`run_models.py:87`](https://github.com/littleorgans/transport-matters/blob/7df0d907a505e7c7633567143518880192106757/api/src/transport_matters/controlplane/run_models.py#L87-L110)
models neither `resourceId` nor `canvasId` on `GatewayRunView`. Pydantic therefore accepts a gateway
create response containing only `runId` and `state`, and it silently drops valid identity fields from
complete responses.

This prevents Python from enforcing the required `resourceId` and nullable `canvasId` cross language
contract. Add the required aliased fields and validate complete gateway responses.

## Confirmed behavior

1. `upsert_session_with_affinity` takes its session advisory lock before reading the row and keeps each
   applied, replayed, or conflict outcome inside one database function.
2. The conflict path leaves the stored affinity unchanged and `SessionWriter` quarantines the whole
   incoming event batch before event insertion.
3. Claims and leases are inserted in one transaction. Claim identity replay is serialized. The
   delete versus claim test uses two connections and proves the losing claim grants no lease.
4. `bind_run_id` uses `COALESCE` plus an equality guard, so current production code never remints or
   rebinds identity.
5. Managed launch claims before capture preparation. The runtime mints `resourceId`; browser callers
   do not supply it. Public Node run views carry required `resourceId` and nullable `canvasId`.
6. Durable, pending, registered, and plain terminal inventory is deduplicated by `resourceId` where
   each source is present.
7. Changed source files remain below the 700 line threshold. `RunManager.ts` is 695 lines.

## Verification and trust

1. `git diff --check d7bfb9ac..7df0d907` passed.
2. Focused test
   `test_run_termination.py::test_force_resources_requests_cancel_before_termination` passed. It
   confirms the ordering behind Major 2.
3. A focused model probe confirmed that `GatewayCreateRunResult` accepts a response with no
   `resourceId` or `canvasId`, supporting Minor 3.
4. PostgreSQL focused tests were not run because no Transport Matters test database setting was
   available.
5. One independent reviewer invoked the runtime package suite despite the narrow gate instruction. It
   reported 204 passed and 2 skipped. This out of scope run does not upgrade the trust verdict.
6. Implementation and tests landed together in `668a66952d7f695a7f6092791e9cf018aa050c90`.
   The documentation commit followed 21 seconds later. Repository history cannot substantiate the
   locked red first claim. This does not prove that tests were never observed failing.
7. Final branch: `feat/multi-launch`, ahead 3 and behind 3. Final HEAD:
   `7df0d907a505e7c7633567143518880192106757`. The tracked tree was pristine at review completion.
