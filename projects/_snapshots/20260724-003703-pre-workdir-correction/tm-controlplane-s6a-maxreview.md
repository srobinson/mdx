# Transport Matters control plane S6a MAX review

## Verdict

**Changes required.** The branch is not ready to merge.

Severity count: **8 major, 2 moderate, 4 minor**.

The highest risk defects are concentrated in launch replay and identity. A lost create response can either create two runs or deduplicate the run while permanently dropping its `first_prompt`. Descendant launches also publish a manifest identity that disagrees with the actual lock and storage identity. Workdir checks reject ordinary traversal and existing symlink escapes, but a deliberate replacement race remains between the final Python check and Node PTY spawn. The current fresh to head and genuine 0014 to head database paths are safe, but historical revision 0007 now depends on the live launch kind tuple and makes revision 0014 path dependent.

Review target:

- Branch: `controlplane-s6a-launch`
- Head: `ea8fff41f62e82bb3192212a688dd30f16e3e6fa`
- Base: `38e9f797b5f769ba7e65db8793d52cb9a7c99cde`
- Diff: 55 files, 2,534 insertions, 578 deletions
- Initial worktree: pristine
- GitHub state: local pre-PR branch, with no remote branch or pull request

## Major findings

### 1. Default launch retries can create two runs

**Severity:** Major  
**Confidence:** 100/100

**Mechanism.** `LaunchRequest.dispatch_id` is optional in `api/src/transport_matters/controlplane/run_models.py:17-25`. `ControlPlaneService.launch()` generates a new UUID for every request that omits it at `service.py:254`, then sends that UUID as the gateway idempotency key at `service.py:272-281`. `LaunchResult` does not return the generated dispatch ID at `run_models.py:28-33`.

**Failing scenario.** The gateway creates `run-1`, but its response is lost. The caller has no dispatch ID to reuse and repeats the same default REST or MCP request. The service generates another key and the gateway creates `run-2`. An observed in-memory probe produced:

```text
default-dispatch {'create_calls': 2, 'gateway_run_ids': ['run-1', 'run-2'], 'prompt_run_ids': ['run-2'], 'retry_run_id': 'run-2', 'audit_rows': 1}
```

The first run remains live without its requested prompt or audit row. The second run receives the prompt and is returned to the caller.

**Scope.** Every launch caller that omits `dispatch_id`, including the default REST and MCP schemas. Current tests only retry with an explicit constant dispatch ID.

**Required correction.** Make the idempotency key caller generated and required for launch, or provide an equivalent request identity that survives response loss. Returning a server-generated ID in the lost response does not solve this failure.

### 2. Same-dispatch replay can permanently drop `first_prompt`

**Severity:** Major  
**Confidence:** 100/100

**Mechanism.** The service installs replay state before `gateway.create_run()`, but a create exception exits at `service.py:271-286` with `replay.result` unset. If the gateway completed creation and only the response was lost, a retry with the same dispatch ID returns `created=false`. The branch then sets `first_prompt="skipped"` at `service.py:288-302` even though this service instance never attempted prompt delivery.

The risk is practical. `RunRouteProxy` applies a 10 second timeout to create at `api/src/transport_matters/api/v1/run_proxy.py:78-83`, while the downstream capture RPC explicitly allows 30 seconds at `packages/runtime/src/adapters/CaptureRpcClient.ts:21-23,59-68`.

**Failing scenario.** Capture preparation legitimately exceeds 10 seconds. Python times out while the gateway continues and registers the run. A retry with the same dispatch ID correctly avoids a second spawn, but the prompt obligation is discarded. The observed probe produced:

```text
same-dispatch {'create_calls': 2, 'gateway_runs': 1, 'prompt_writes': 0, 'retry_first_prompt': 'skipped', 'audit_rows': 1}
```

Cancellation after gateway creation and before prompt delivery has the same result.

**Scope.** Post-send transport failures, timeouts, and cancellation during create or the gap before prompt state is committed. The integration replay test retries only after a wholly successful first response, so it cannot detect this interleaving.

**Required correction.** Persist a prompt delivery obligation independently from the gateway `created` disposition. A replay with no recorded prompt attempt must continue that obligation against the deduplicated run. Ambiguous delivery itself needs an explicit `unknown` state or an idempotent input primitive.

### 3. First-prompt ambiguity is converted into a definite failure

**Severity:** Major  
**Confidence:** 100/100

**Mechanism.** `RunRouteProxy.deliver_input()` correctly returns `GatewayInputOutcome(status="unknown")` after a post-send transport failure at `run_proxy.py:181-209`. `deliver_first_prompt()` maps every outcome other than `delivered` to `failed` at `api/src/transport_matters/controlplane/launch_delivery.py:43-52`. `FirstPromptStatus` cannot represent `unknown` at `run_models.py:12-14`.

**Failing scenario.** The PTY accepts the first prompt, then the HTTP response truncates. Launch returns and audits `failed`, encouraging a duplicate follow-up even though the bytes may already be in the harness. The observed probe produced:

```text
{'gateway_outcome': 'unknown', 'launch_first_prompt': 'failed', 'audit_first_prompt': 'failed'}
```

**Scope.** Launch first prompts only. Ordinary prompt and interrupt results preserve the same gateway ambiguity.

**Required correction.** Add `unknown` to the first-prompt receipt and audit vocabulary, then preserve it end to end.

### 4. Gateway create failures bypass mandatory launch audit

**Severity:** Major  
**Confidence:** 99/100

**Mechanism.** Both create exception branches at `service.py:271-286` exit before `LaunchResult`, `launch_action()`, and `_audit_action()` are constructed at `service.py:288-317`. `CONTROLPLANE.md:24-25,172-182` requires every action to be attributed and persisted. Prompt, stop, and interrupt convert expected action failures into auditable results, while launch does not.

**Failing scenario.** A connection refusal, capture rejection, spawn failure, or ambiguous response loss returns a structured control-plane error but leaves no `control_plane_action`. In the ambiguous case a live run can exist without any action record.

**Scope.** Launch gateway failures before a result is cached. The existing audit failure test starts from a successful create and only fails the audit sink.

**Required correction.** Build and persist a failed or unknown launch action for every attempted create. Ambiguous creates need reconciliation so a later run ID can be attached to the same action instead of creating a second record.

### 5. Descendant launches split manifest identity from lock and storage identity

**Severity:** Major  
**Confidence:** 100/100

**Mechanism.** `captured_run_root()` places the lock and manifest under the explicit workspace root at `api/src/transport_matters/captured_run_context.py:251-252`. `write_captured_run_manifest()` then passes only `ctx.prepared.working_dir` at `captured_run_context.py:280-296`. `write_workspace_manifest()` derives the manifest slug and hash from that child workdir at `api/src/transport_matters/launch_manifest.py:70-77`.

`transport-matters list` reconstructs the lock path from the embedded manifest fields at `api/src/transport_matters/cli/instances.py:49-57`. The real lock is under the root identity, so every descendant launch is omitted as if it were stale. Run metadata also reloads the child `cwd` and recomputes workspace identity from it at `api/src/transport_matters/api/v1/run_storage.py:63-64,80-92`, while grants, lifecycle rows, wire records, live status, and session binding use the root identity.

**Failing scenario.** A director in `/repo` launches into `/repo/review`. The lock and manifest file live under the `/repo` workspace directory, but the manifest claims the slug and hash of `/repo/review`. Instance listing probes the nonexistent child lock and omits the live run. Metadata identifies the same run as a different workspace from Activity and the control-plane grant.

**Scope.** Every service launch whose `workdir` differs from `workspaceRoot`. Same-directory launches are unaffected.

**Required correction.** Pass the root workspace slug and hash when writing the manifest, and carry the authoritative workspace identity through `RunStorageContext` instead of deriving it again from the child cwd. Add a descendant launch test that checks the actual manifest path, fields, lock probe, and meta workspace ID.

### 6. Historical migration 0007 now produces a path-dependent revision 0014

**Severity:** Major  
**Confidence:** 95/100

**Mechanism.** `api/migrations/versions/0007_run_lifecycle_event.py:12-16,24-47` imports the live `RUN_LIFECYCLE_LAUNCH_KINDS`. This branch expands that tuple to `('canvas', 'detached', 'service')` at `api/src/transport_matters/session/run_lifecycle_contracts.py:7`. A fresh migration stopped at 0014 under this code therefore accepts `service`, while a genuine pre-S6 0014 database and an 0015 downgrade use the two-kind constraint frozen at `api/migrations/versions/0015_service_launch_kind.py:17-29`.

This directly violates the project rule at `LESSONS.md:372-378`: migration revisions freeze literals.

**Failing scenario.** Two databases both report Alembic revision `0014_wire_commit_watermark`. One was created fresh under this branch and accepts `service`. The other was upgraded before S6 or downgraded from 0015 and rejects it. Schema behavior now depends on migration history despite the same revision marker.

**Scope.** Pinned revisions, rollback verification, schema comparisons, and any tooling that assumes an Alembic revision uniquely identifies a schema. Fresh to head and genuine 0014 to head upgrades converge safely, and no current data-loss hazard was found.

**Required correction.** Freeze the original `('canvas', 'detached')` vocabulary inside migration 0007. Let migration 0015 own the expansion. Add a none to 0014 test that rejects `service`, then upgrade that database to head and prove `service` is accepted.

### 7. Workdir confinement can be escaped after the final check

**Severity:** Major  
**Confidence:** 98/100 in the direct adversarial threat model

**Mechanism.** `scoped_launch_workdir()` resolves and checks containment at `api/src/transport_matters/controlplane/launch_policy.py:27-47`. Capture repeats the realpath check at `captured_run_context.py:299-308`. The checked pathname is retained through capture preparation and later passed unchanged to `node-pty` at `packages/runtime/src/service/RunManager.ts:313-319` and `packages/runtime/src/adapters/NodePtyAdapter.ts:52-70`.

**Failing scenario.** A director selects a writable descendant, waits until the second Python validation has completed, renames that directory, and replaces it with a symlink to an outside directory before PTY spawn. Capture preparation provides a material race window. `node-pty` resolves the replacement and starts the child outside the principal workspace.

**Scope.** A deliberate actor that can mutate the selected descendant during launch. Static absolute escapes, relative `..`, sibling prefix tricks, and preexisting outward symlinks are correctly rejected.

**Required correction.** Revalidate the real path against `workspaceRoot` at the actuation boundary in Node and remove the long validation-to-use window. A robust design should bind the spawn to a verified directory handle or equivalent child-side containment check where platform support permits it. Add a replacement-race regression.

### 8. The branch adds meaningful logic to a 184-line function

**Severity:** Major project-convention violation  
**Confidence:** 100/100

**Mechanism.** `build_captured_run_context()` spans `captured_run_context.py:59-242`, or 184 lines. It was already 173 lines at the base. This branch adds workspace validation, storage rewriting, grant workspace propagation, launch-field construction, and return state without first decomposing the function. The repository instruction and the code-hygiene guardrail both require functions over about 150 lines to be broken up with no exception.

**Failing scenario.** Future work must modify one orchestration body that already mixes launch preparation, storage, runtime-home materialization, grant provisioning, session ownership, provider invocation construction, and rollback. The new workspace identity bug in finding 5 is one concrete consequence of those coupled phases.

**Scope.** `build_captured_run_context()`. No new file exceeds 700 lines. `ControlPlaneService` is 697 lines, three lines below the hard file threshold. `RunManager.ts` improved from 692 to 652 lines through the 131-line input extraction.

**Required correction.** Extract named, typed phases for workspace and storage preparation, runtime-home and grant preparation, and provider invocation construction. Keep rollback ownership together and prove the mechanical move before further simplification.

## Moderate findings

### 9. Stop reports an ambiguous termination as definite failure

**Severity:** Moderate  
**Confidence:** 85/100

**Mechanism.** `RunRouteProxy.terminate_run()` uses `_typed_run_request()` at `run_proxy.py:246-284`. Every `httpx.RequestError`, including a protocol failure after the gateway accepted termination, becomes `GatewayUnavailableError`. `ControlPlaneService.stop()` maps that to `failed/busy_gateway` at `service.py:324-347`, despite `ManageStatus` already supporting `unknown` at `run_models.py:14`.

**Failing scenario.** `RunManager` terminates the PTY, then its HTTP response truncates. The caller and durable audit row both say the stop failed. A retry is operationally idempotent, but the receipt is false and can obscure the actual terminal transition.

**Scope.** Post-send transport failures on stop. Pre-connect failures remain definite `busy_gateway` failures.

**Required correction.** Distinguish connection failure from post-send ambiguity, and return and audit `unknown` for the latter.

### 10. Break-only interrupt can report failure after Esc was accepted

**Severity:** Moderate  
**Confidence:** 85/100

**Mechanism.** `deliverInput()` writes the break byte at `packages/runtime/src/service/RunInputDelivery.ts:95-97`, waits, then reports `failed/run_settling` if the run exits or a concurrent stop begins at lines 98-100. It recognizes the no-text case only at line 102.

**Failing scenario.** The PTY accepts Esc and the requested break causes or coincides with the run settling during the delay. The only requested byte was accepted, but the result and audit report failure. Tests set the settle delay to zero and keep the run live, so they miss this interleaving.

**Scope.** Interrupt without follow-up text. Interrupt plus prompt still needs the settle and liveness checks before the text write.

**Required correction.** Return `delivered` immediately after an accepted break when no text remains. Retain the settle path only for interrupt-plus-text.

## Minor findings

### 11. Invalid in-scope workdirs surface as gateway delivery failures

**Severity:** Minor  
**Confidence:** 98/100

**Mechanism.** `scoped_launch_workdir()` checks containment but does not require the resolved path to be a directory. A missing descendant, regular file, or whitespace-padded path passes service policy and fails later in `api/src/transport_matters/cli/launch_runtime.py:107-117`. That exception crosses capture, runtime, and proxy boundaries and becomes control-plane `delivery_failed`, normally HTTP 502.

**Failing scenario.** A caller mistypes an in-workspace path and receives an infrastructure delivery error rather than `invalid_request`.

**Scope.** Missing paths, non-directory paths, and related local path resolution errors inside the allowed root.

**Required correction.** Validate `resolved.is_dir()` at the service policy boundary and translate local path errors into `ControlPlaneError("invalid_request", ...)`.

### 12. Launch replay state is unbounded, including failed creates

**Severity:** Minor  
**Confidence:** 99/100

**Mechanism.** `_launch_replays` is a process-lifetime dictionary at `service.py:128,424-434` with no success, failure, size, or time eviction. Gateway `pendingCreates` deletes rejected entries, while the service retains the corresponding intent and lock forever.

**Failing scenario.** Repeated unique dispatch IDs aimed at launches that fail during create grow service memory without leaving a run. Successful launch entries also accumulate for the entire process lifetime.

**Scope.** Long-lived API processes and high launch or failure volume.

**Required correction.** Define bounded replay retention and safe eviction. Preserve unresolved ambiguous operations until reconciled, then expire completed and definitive-failure entries using a documented limit or TTL.

### 13. The nudge fold leaves dead API and stale launch commentary

**Severity:** Minor  
**Confidence:** 100/100

**Mechanism.** The old `/nudge` route and `RunManager.nudge()` are deleted, but `validRuntimeNudge()` remains defined and exported at `packages/runtime/src/service/RunInputDelivery.ts:44-46` and `packages/runtime/src/index.ts:79-84` with no production caller. `MAX_RUNTIME_NUDGE_CHARS` now limits generic input while retaining the old path-specific name. The new comment at `packages/runtime/src/service/RunManager.ts:90` says existing callers are canvas launches although this branch adds service launches.

**Failing scenario.** Future input work sees two validators and stale vocabulary, chooses the obsolete stricter path, or misses service behavior because the adjacent contract comment says only canvas callers exist.

**Scope.** Runtime public surface and maintainability. Current watch envelopes remain single line, and no present delivery behavior changes because of the dead validator.

**Required correction.** Delete the obsolete validator and export, rename the shared limit around generic control-plane input, and update the launch-kind comment.

### 14. Runtime re-declares the capture launch-kind vocabulary

**Severity:** Minor  
**Confidence:** 100/100

**Mechanism.** `CaptureLaunchKind` is declared in `packages/runtime/src/ports.ts:5-7`, while `runtimeRouter.launchKindFromBody()` independently returns and checks the literal union `"canvas" | "service"` at `packages/runtime/src/server/runtimeRouter.ts:266-269`. This violates the repository rule against re-declared closed types.

**Failing scenario.** A future capture launch kind updates the port type while the wire parser continues rejecting it. The mismatch remains type-correct because the parser owns a separate union.

**Scope.** Runtime launch request parsing. Activity has a wider intentional vocabulary because it also reads detached lifecycle rows.

**Required correction.** Export one canonical runtime value tuple, derive `CaptureLaunchKind` from it, and validate request values against that tuple.

## Adjudicated below the publication threshold

These were verified but are not included in the severity count.

- `launch_fields_with_workspace_root()` trusts a caller-supplied `run_lifecycle_workspace_root` when `workspaceRoot` is absent. New session, wire, and live-status consumers can then use a forged workspace identity. Current first-party runtime and control-plane paths do not expose arbitrary launch fields, lifecycle facts and grants still use the actual workdir, and exploitation requires a raw capture-RPC caller. Score: 68/100. Reserve the key or reject it at the capture boundary as hardening.
- `_wait_for_running()` ignores a `RUNNING` state returned by its final poll at `launch_delivery.py:65-78`. Real `RunManager` creates return `RUNNING` immediately under the S6a contract, so the branch cannot currently hit the fabricated `STARTING` path. Score: 50/100.
- Stop and interrupt actuate before auditing and have no caller-supplied dispatch key. If audit persistence fails, retry can send a second Esc. This mirrors the existing prompt ordering and needs a broader manage retry contract. Score: 75/100.

## Clean seams and positive results

- The new `service` launch kind is parameterized through `PrepareCaptureInput`, `CaptureRpcClient`, `PrepareCaptureRequest`, `CapturedRunRequest`, capture lease facts, and both lifecycle events. The previous hardcoded canvas writer is removed.
- Python launch-kind contracts, the Postgres JSON contract, TypeScript Activity values, and Postgres row coercion all recognize `service`.
- Static workdir containment uses canonical paths and component-aware `is_relative_to`; direct absolute escapes, relative traversal, sibling-prefix tricks, and preexisting outward symlinks fail closed.
- Director authorization is centralized and runs before gateway access for launch, stop, and interrupt.
- Watch delivery now uses the shared input primitive without observed queueing, serialization, bracketed-paste, or typed-outcome drift. Unknown watch outcomes are dropped and audited as required; proven connect failures retain facts for retry.
- Codex launches retain the existing managed-home seeding path. `CodexSeeder` writes project trust for the prepared child workdir, and the focused grant/capture tests passed.
- `RunInputDelivery.ts` is a coherent 131-line extraction and reduces `RunManager.ts` from 692 to 652 lines.

## Verification evidence

All root checks used the repository interpreter and avoided bytecode, pytest cache, emitted TypeScript, and incremental state.

| Check | Observed result |
|---|---|
| Exact branch, head, base, one-commit range | Correct |
| `git diff --check main..HEAD` | Clean |
| Focused control-plane, proxy, and skin Python tests | 48 passed |
| Focused capture, lifecycle, mirror, capture-route, and watch Python tests | 84 passed; 3 database-fixture errors |
| Database-backed migration and launch integration attempt | 3 migration-fixture errors; 1 integration skip |
| Runtime Vitest suite | 174 passed |
| Activity Vitest suite | 224 passed, 30 skipped |
| Runtime no-emit, non-incremental TypeScript check | Passed |
| Activity no-emit, non-incremental TypeScript check | Passed |

Database-backed verification was unavailable in this pane. Six database-dependent setups stopped before test execution: two service launch-kind migration tests, the migration round trip, one lifecycle emission case, and two continuation route cases. The launch integration test skipped. Every case reported the absence of `TRANSPORT_MATTERS_TEST_DATABASE_URL`, `TRANSPORT_MATTERS_DATABASE_URL`, or a configured test URL. This environment limitation does not explain the static historical-migration defect.

The focused suites are green but do not falsify the critical failures. They omit create-response loss, cancellation between create and first prompt, unknown first-prompt acceptance, default dispatch retry, descendant manifest identity, replacement-race confinement, post-send terminate ambiguity, and exit during break-only settle.

## Final gate

Before the verdict, the worktree remained at exact head `ea8fff41f62e82bb3192212a688dd30f16e3e6fa`, `git status --porcelain=v1 --untracked-files=all` was empty, and `git diff --check 38e9f797b5f769ba7e65db8793d52cb9a7c99cde..ea8fff41f62e82bb3192212a688dd30f16e3e6fa` was clean. No repository file was written by this review.

## Delta verification: `bb604cf2`

**Range:** `ea8fff41f62e82bb3192212a688dd30f16e3e6fa..bb604cf2430418a78b84f491a9d783a0c065ae41`  
**Verdict:** Issue  
**Workdir actuation:** Closed  
**Replay:** Issue  
**Migration:** Converged

### Remaining findings

#### 1. Workspace identity remains vulnerable to pathname replacement

**Severity:** Major  
**Confidence:** 94/100

`_validated_workspace_root()` in `captured_run_context.py:397-404` freezes a resolved pathname. Storage, lock, manifest, grant, capture facts, and lifecycle code later resolve that mutable path independently through `run_root`, `captured_run_root`, `workspace_id`, and `workspace_key`. An ancestor can be replaced with an outside symlink during preparation, then restored before `secure_workdir` performs its descriptor walk. The child executes in the original directory while grant, storage, manifest, or lifecycle identity can be sampled from another target.

Freeze one validated workspace identity, key, and storage root. Thread those immutable values through every consumer and bind execution to the same directory identity.

#### 2. Audit failure after prompt delivery loses the completed prompt outcome

**Severity:** Major  
**Confidence:** 100/100

`launch_service._execute()` delivers the first prompt before persisting the action, but assigns `replay.result` only after audit persistence. If `persist_action()` or `replace_action()` fails, `_finalize_task()` deletes the replay. A same-dispatch retry sees `created=false`, skips delivery, and persists `first_prompt=skipped` even though the original write was delivered or ambiguous.

The focused fault injection observed one prompt write, a first `delivery_failed`, and a retry receipt plus audit row reporting `skipped`. Retain prompt outcome and unfinished audit obligations independently until both reach terminal state.

#### 3. Definite gateway connection failures can exhaust replay capacity

**Severity:** Moderate  
**Confidence:** 90/100

`GatewayUnavailableError` marks create outcome unknown and retryable. Those entries remain in `_launch_replays`, while `_make_replay_room()` evicts only completed results. After the configured limit of distinct outage attempts, every new dispatch receives `launch replay capacity is exhausted`, including after gateway recovery.

A capacity-two fault injection retained both definite connection failures and rejected a third dispatch. Classify proven pre-connect failures as definite, or provide bounded durable retry state that can recover capacity safely.

#### 4. Terminal create failure releases dispatch identity

**Severity:** Moderate  
**Confidence:** 85/100

A `GatewayResponseError` persists failure, then replay finalization deletes the dispatch entry. Reusing the same dispatch ID with changed intent can subsequently spawn. Even an identical later success creates a second audit row because durable reconciliation only runs when gateway creation returns `created=false`.

The focused probe reused one dispatch after a failed Claude launch for a successful Codex launch and observed two audit rows. Preserve a durable dispatch tombstone and reject changed intent.

### New minor findings and test gaps

- A valid direct child workdir named `--` is rejected because `secure_workdir.main()` finds the first delimiter with `args.index("--")`.
- The secure workdir regressions only require nonzero exit and absence of an outside marker. An always failing wrapper satisfies both assertions. Add an executed descendant happy path and assert the expected confinement failure.
- The branch lacks a readiness regression with more than one poll. A custom `STARTING` then `RUNNING` probe passed with one prompt write, so the implementation works but the requested regression is absent.

### Corrections confirmed

- Descriptor relative `O_NOFOLLOW` traversal plus `fchdir` closes final component and ancestor symlink swaps at execution.
- Caller supplied dispatch identity, lost create replay, concurrent retry sharing, cancellation shielding, and unknown prompt receipts work within one launcher.
- The readiness loop checks the final configured poll.
- Create failures are audited. Stop post-send ambiguity reports `unknown`. Break-only interrupt reports delivery after accepted Esc.
- Stable missing and file workdirs return `invalid_request`. Static descendant manifests carry the principal workspace identity.
- Migration 0007 freezes its historical event and launch-kind literals. Fresh, downgrade, and upgrade definitions are compared as exact PostgreSQL canonical CHECK expression strings.
- Changed files remain below 700 lines. The former 184-line context builder is 78 lines. Dead nudge API and stale commentary are removed, and the runtime capture launch-kind vocabulary is canonicalized.

### Delta verification evidence

| Check | Observed result |
|---|---|
| Focused control-plane Python suite | 47 passed |
| Runtime Vitest suite | 18 files, 175 passed |
| Migration convergence test | 3 setup errors before test execution because no database URL was configured |
| Custom final-poll readiness probe | Passed; 2 state reads, 1 prompt write, 1 spawn |
| Custom audit retry probe | Reproduced false `skipped` outcome after one prompt write |
| Custom replay capacity probe | Reproduced capacity exhaustion after 2 retained failures |
| Custom failed-dispatch probe | Reproduced changed-intent reuse and duplicate audit rows |

The migration correction is statically converged and its assertion is meaningful for CHECK expression equivalence. Database-backed execution remains unavailable in this pane.

### Delta final gate

Immediately before the delta verdict, the branch was `controlplane-s6a-launch` at exact head `bb604cf2430418a78b84f491a9d783a0c065ae41`. `git status --porcelain=v1 --untracked-files=all` was empty, and `git diff --check ea8fff41f62e82bb3192212a688dd30f16e3e6fa..bb604cf2430418a78b84f491a9d783a0c065ae41` exited zero. No repository file was written by this review or its subagents.

## Correct replay design

**Adjudication:** Revise the proposed service ledger before implementation.

The authority split is correct. The gateway owns spawn deduplication through its owner-scoped creation disposition. The service owns its prompt, receipt, and audit side effects. The proposed key and entry are not sufficient to implement that split safely.

### Key and immutable intent

Key the service ledger by `(owner, dispatch_id)`, matching gateway scope. A global `dispatch_id` key would collide across owners. Store a complete normalized intent fingerprint inside the entry and reject any mismatch with `invalid_request` before gateway access. The fingerprint must cover:

- actor run ID
- principal workspace ID
- canonical workdir and workspace root
- harness, name, and grant
- normalized first prompt, or a cryptographic digest of it

`first_prompt` is service-owned and absent from the gateway request. A ledger that stores only the resulting receipt cannot determine whether a replay changed that prompt. Returning the original `delivered` receipt to a caller that supplied different text would misrepresent which text was delivered.

### Entry state

A sufficient process-resident entry is:

```text
intent_fingerprint
task
phase = creating | prompting | audit_pending | terminal
run_id
prompt_state = none | delivered | failed | unknown | skipped
receipt_or_error
frozen_audit_action
audit_written
```

Insert the entry atomically before starting side effects. One shared task owns the operation, and every caller awaits it through cancellation shielding. In an asyncio service, a lock or an await-free `setdefault` section must combine lookup, intent comparison, entry creation, and task installation. This prevents two same-dispatch callers from becoming leaders.

### Terminal and failure rules

Once gateway creation succeeds, first-prompt delivery is attempted at most once. Its typed outcome is terminal:

- `delivered`, `failed`, or `unknown` is stored exactly as observed.
- A readiness failure is stored as `failed`.
- No replay sends prompt bytes again.

After the prompt attempt, build and freeze the receipt and its exact audit action. If audit persistence succeeds, mark `audit_written=true` and the entry terminal. Replays then return the recorded receipt without delivery or audit.

If audit persistence fails, retain the exact receipt and frozen action with `phase=audit_pending`. Return `delivery_failed`. A replay retries only that audit write. It returns the recorded receipt after the action becomes durable. Repeating prompt or reconstructing its outcome is forbidden.

A create failure should also retain its complete intent and terminal error. Replays with that dispatch return the recorded error. A caller that intentionally starts a new launch attempt uses a new dispatch ID. This preserves dispatch identity and prevents failed-dispatch rebind. If the product later permits same-dispatch retry after a proven pre-connect failure, model that as an explicit `create_retryable` phase under the same immutable intent and shared task. Never delete the intent guard.

### Memory and lifetime

No eviction removes the earlier capacity failure and preserves process-lifetime truth, but an unbounded map remains a memory exhaustion surface. For the process-resident design:

- scope accounting and rate limits per owner
- expose ledger cardinality and audit-pending counts
- compact terminal entries to the intent fingerprint, receipt, and audit flag

A hard memory bound requires durable terminal tombstones before eviction. The durable form must contain enough intent to reject changed replays and enough receipt data to return the original outcome. Eviction without that durable record recreates the blind replay defect.

### Result

With owner scoping, full intent comparison, atomic single flight, cancellation shielding, terminal prompt outcomes, and an independently retryable audit obligation, the service ledger closes successful-audit overwrite, service-only intent blindness, failed-dispatch rebind, prompt double delivery, and auditless replay success. Gateway disposition remains the sole spawn authority.
