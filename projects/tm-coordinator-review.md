# Launch verification coordinator — adversarial review

Branch `launch-verification-coordinator` @ `707c7dbb` against `main` @ `b6979af4`.
Read-only review from the main checkout (`git diff main...launch-verification-coordinator`).
Working tree pristine, no edits, no checkout, no backend start, no provider turns.

Two properties were under test:

1. **P1 — it can never affect the launch.** Holds for correctness (response body, errors,
   exceptions). Does **not** hold for latency under concurrency: see B3.
2. **P2 — it can never spend more than one capture per cell per harness version.** Does
   **not** hold. See B1 and B5. The property is violated by design in one case and by
   deployment shape in another.

Counts: blockers 2, majors 3, minors 8.

---

## B1 — BLOCKER: any failure after the first probe re-bills on every later launch, forever

**Where:** `launch_verification.LaunchVerificationCoordinator._verify_under_lock`,
`launch_verification._write_verification_receipt`.

The receipt is written **after** `self.harvest(...)` returns. Every failure path inside
`harvest_controlled_baseline` therefore leaves no durable record that money was spent:

- a probe that times out or errors after the CLI has already sent its request
- `project_baseline` refusing the captured body ("a capture that produced a body no
  projection can read fails now, beside the three launches that paid for it")
- `compare_request_schema` / `compare_content` / `BaselineBundle.model_validate` raising
- `write_baseline_bundle` read-back mismatch
- `_require_comparable_capture_plan` / prompt-mismatch refusals (these are free — they
  raise before the first probe)

`_is_current` also stays false, because `write_baseline_bundle` only advances the current
pointer when `promotes_baseline` is true. So the next launch of that cell finds neither a
receipt nor a current pointer, and captures again. There is no attempt counter, no
backoff, and no failure receipt.

This is not an oversight; it is encoded. `test_harvest_failure_fails_open_and_releases_for_a_later_claim`
and `test_aba_timeout_releases_for_a_later_claim` both assert `calls == 2`.

**Failure scenario:** claude/`claude-opus-4-8` is stale after a version bump. The third
probe consistently fails to correlate within `_TURN_TIMEOUT_S` (a delivery-id correlation
regression, a harness that stops emitting the exchange, a mitmdump that binds slowly).
Each launch spends two completed turns plus one partial, logs "failed open", and writes
nothing. An operator launching that cell twenty times in a day spends ~60 turns of a
weekly-capped quota on a capture that never once succeeded. Nothing in the product tells
them, and nothing bounds it.

**Direction:** the receipt must record the *attempt*, not the success — written before the
first probe under the lock, upgraded to a success receipt after. Retry then becomes a
policy decision (attempt count, backoff, a cooling window) rather than "every launch,
forever". The tension the builder was resolving is real (a crashed capture must not wedge
the cell permanently), but "release for a later claim" and "spend again immediately on
the next launch" are not the same requirement.

---

## B2 — BLOCKER: the receipt is a stored derivation that silently suppresses a needed capture

**Where:** `launch_verification._VerificationReceipt`, `_has_verification_receipt`,
`_verification_receipt_path`, `LaunchVerificationCoordinator._is_complete`.

The receipt asserts "this cell was captured at version X" as persisted state, in a private
dot-directory (`baselines/.launch-verification-locks/<executor>/<harness>/<provider>/<model>/completed/<version>.json`),
outside the evidence store it describes. The same fact is derivable from the store: a
bundle exists whose `cell.harness_version` is X. #432 settled that nothing derived is
stored, and #424 was a stored derivation silently disagreeing with its deriver. This is
the same shape.

In the happy path the receipt is redundant — an EXACT or first capture promotes the
current pointer and `_is_current` answers on its own. The receipt is load-bearing exactly
when the evidence did **not** promote, which is where the divergence risk lives.

**Failure scenario (concrete, and the repo has this history):** a cell verifies cleanly at
2.1.240. The pointer is promoted; the receipt is written. Later the current-pointer
artifact schema is bumped (#431 already decoupled that schema once, #433 bumped the
projection key). `read_current_baseline_ref` deliberately returns `None` for an unknown
pointer schema — "the same `None` shape as an absent pointer" — so `assess_baseline_staleness`
now answers `unknown`, the launch view reports the cell unverified, and the store has no
readable pointer. But `_is_complete` short-circuits on `_has_verification_receipt`, which
is keyed only by version and knows nothing about the pointer schema. The cell is never
re-captured at 2.1.240. Ever. Deleting the bundle, or an operator clearing a bad pointer
by hand, produces the same outcome.

The suppression is **silent**: `_is_complete` returns with no log line, there is no CLI
that lists or clears receipts, and the directory is hidden.

**Direction:** derive completeness from the store (does a bundle exist for this cell at
this version?) and delete `_VerificationReceipt`. If a durable non-derivable fact is truly
needed, it is the *attempt* record from B1, which the store genuinely cannot answer — and
it should live beside the evidence, invalidated by the same schema version, not beside the
lock.

---

## M1 — MAJOR: verification blocks the shared default executor that the launch path itself uses

**Where:** `LaunchVerificationCoordinator._run_candidate` (`asyncio.to_thread(self._verify_under_lock, ...)`),
`OwnedVerificationTasks.submit`.

`_verify_under_lock` occupies one default-executor thread for the whole A/B/A, up to
`_ABA_TIMEOUT_S` (600s). The default executor is `min(32, cpu_count + 4)` threads and is
shared process-wide — `capture_rpc.CaptureLeaseRegistry.prepare_capture` runs
`asyncio.to_thread(self._prepare_with_dependencies, request)` on it, as do
`harnesses/access_verification` and the state-refresh writers. There is no dedicated
executor, and `OwnedVerificationTasks` caps nothing: every distinct cell submitted gets a
task, and `test_different_cells_harvest_concurrently` asserts that different cells run
concurrently by design.

**Failure scenario:** the operator upgrades claude, which invalidates every stale cell at
once. They work through a session touching a dozen model/effort cells across two harnesses.
Twelve verification threads sit in the default executor waiting on CLI subprocesses. On a
10-core Mac the pool is 14 threads. The next `POST /v1/capture/prepare` queues behind them
and the operator's launch stalls for minutes — the exact latency effect P1 forbids. The
existing test only proves the response is fast with *one* verification in flight
(`test_prepare_response_is_identical_while_verification_runs`).

**Direction:** a dedicated single-slot (or small, bounded) executor for verification work,
so verification can never contend with the launch path for threads, and a cap on
concurrently scheduled candidates.

---

## M2 — MAJOR: the A/B/A timeout is cooperative only; nothing bounds the unbounded regions

**Where:** `LaunchVerificationCoordinator._verify_under_lock` (`deadline`, `cancelled=`),
`baseline_capture.harvest_controlled_baseline`.

`aba_timeout` is enforced only where someone calls `cancelled()`: between probes in
`harvest_controlled_baseline`, and inside `captured_turn._wait_for_correlated_exchange`.
Everything else in a probe runs with no deadline — `prepare_captured_run` (port
allocation, addon resolution, credential broker, control-plane grant),
`ProcessSupervisor.spawn`, and `supervisor.terminate_all()` in the `finally`. The brief
asked for a timeout around the A/B/A work; what exists is a cooperative check, not a
timeout.

**Failure scenario:** `resolve_mitmdump` or the port probe hangs against a wedged local
port (the repo already models `CapturedRunProxyStartTimeout` for the launch path, so this
is a known-live failure mode). The verification thread never reaches a `cancelled()` check.
The default-executor thread is held for the process lifetime, the cell's `WorkspaceLock` is
held with it, and `aclose()` at shutdown waits on `gather` for a worker that will not
return. Combined with M1, one wedged probe permanently removes a thread from the pool the
launch path uses.

**Direction:** enforce the deadline in the coordinator, not only inside the harvest — the
worker thread needs a hard bound, or the unbounded calls need their own timeouts.

---

## M3 — MAJOR: two channels on one machine bill the same cell twice

**Where:** `launch_verification.launch_verification_lock_root`,
`create_launch_verification_coordinator` (`output_root=storage_root / "baselines"`).

Both the lock and the receipt are keyed by `executor_id`, and `output_root` is derived from
the channel's `storage_dir`. Per CLAUDE.md, each channel is a separate home with its own
minted `executor-id` and its own database — and canvas runs preview while the CLI defaults
to stable. Neither the lock nor the receipt crosses that boundary.

**Failure scenario:** the operator runs canvas (preview) and the CLI (stable) against the
same installed claude binary, which is what the documented setup produces. They launch
claude/`claude-opus-4-8` from each. Preview captures three turns; stable captures three
more for the identical cell at the identical harness version, because
`~/.transport-matters-preview/baselines/...` and `~/.transport-matters/baselines/...` share
nothing. Six turns for one fact. Running dev as well makes it nine.

The invariant the brief asked for is "one capture per cell per harness version". What ships
is one capture per cell per harness version **per channel home**. That is a defensible
scope, but it is not what is claimed, and it is not stated anywhere in the module.

**Direction:** either key the single-flight domain on something machine-wide (the binary's
resolved path plus version) rather than the executor id, or state the per-channel scope
explicitly in the module docstring and accept the multiplier knowingly.

---

## m1 — MINOR: an ordinary ungated launch logs an exception traceback

**Where:** `_run_candidate` (`raise ValueError("prepared launch recorded no compatibility facts")`
caught by `logger.exception("... failed open ...")`).

`compatibility_service._record` writes the facts artifact only when a release entry and an
installed, versioned, `ok` observation both exist, and `gate_launch_preparation` returns
`None` (ungated) for an unregistered harness name, a client-disabled proxy-only launch, or
any internal gate failure in advisory mode. All of those are normal, expected launches.
Each one now emits an ERROR with a stack trace on a path that is working correctly. Real
failures become unfindable in the noise. Absence of facts is a "nothing to verify" answer,
like `NoVerificationCell` — it should return, at INFO or DEBUG, not raise.

## m2 — MINOR: the diagnostic-test discriminator is right but untested at the seam

**Where:** `api/v1/launch_verification_routes.schedule_prepared_launch_verification`
(`diagnostic_test=provider_access_approval == "diagnostic_test"`).

The discriminator is sound: `ProviderAccessApprovalRequest` is
`Literal["allow_unverified", "diagnostic_test"]`, so the comparison is a real string
match, and `FirstRunScreen.startAccessTest` plus `CapturedRunPane` both send
`providerAccessApproval: "diagnostic_test"`. `LaunchKind.SERVICE` is correctly not used.

But no test drives the route with that body. `_install_resolved_cell` in
`test_launch_verification_routes` asserts `provider_access_approval is None`, so the
diagnostic path cannot be exercised there, and the coordinator test passes
`diagnostic_test=True` directly. The wiring that protects the access test from billing is
the one line no test covers.

Also worth noting: the request body is the operator's *claim*; `ProviderAccessReceipt.approval`
is the server's validated answer to the same question, and the receipt is already parsed
two lines above. The receipt is the sounder discriminator.

## m3 — MINOR: suppression is silent and has no inspection path

`_is_complete` returning true — the single most consequential decision this module makes,
"do not spend money and do not verify" — logs nothing. Success and skip-for-quota both log.
There is no way to answer "why has this cell not verified?" without reading a hidden
dot-directory by hand. This is what makes B2 dangerous rather than merely wrong.

## m4 — MINOR: the quota SQL duplicates an existing statement and lives in the wrong module

`launch_verification._KNOWN_USAGE_LIMIT_SQL` is a near-clone of
`session/controlplane_statements.GET_MODEL_REJECTION_FOR_OWNER_SQL` — the same
`SELECT EXISTS` over `run_live_status` filtered by `owner` and `kind`. Every other module
holding SQL outside `session/` is a `*_store.py`. The statement belongs in
`session/controlplane_statements.py` beside its twin; the reader can stay here.

Separately, the query does not filter `live.closed`, so a finalized usage-limit generation
on a still-running run keeps suppressing verification until that run exits. The direction
is safe (it spends less), but it is unstated.

## m5 — MINOR: `OwnedVerificationTasks.drain` has no production caller

Shutdown uses `aclose()`. `drain()` exists only for the nineteen `await coordinator.tasks.drain()`
calls in `test_launch_verification`. It is a test affordance on a production class. The
reuse of `drain_pending` the brief asked for is real, but it is reuse in service of tests
only — either shutdown should drain before cancelling, or `drain` should not be on this class.

## m6 — MINOR: the receipt version-mismatch branch is unreachable

`_has_verification_receipt` raises `ValueError` when `receipt.harness_version != installed_version`,
but `_write_verification_receipt` always writes content and path from the *same* string, so
the two can only disagree under external tampering. The branch is dead defensive code, and
its failure mode is to raise — permanently disabling verification for that cell — rather
than to treat an unreadable receipt as absent, which is what the rest of the store does
(`read_current_baseline_ref` returns `None` for an unknown pointer schema).

## m7 — MINOR: third copy of the depth-relative repo root

`main._SOURCE_ROOT = Path(__file__).resolve().parents[3]` repeats
`baseline_harvest` (`parents[3]`) and `session/migrate` (which already has to try two
depths). Depth-relative joins have broken this repo before. It degrades safely here
(`identify_runtime_source` falls back to the installed distribution when the path is not a
checkout), so this is placement, not correctness: it wants one named helper.

## m8 — MINOR (speculative): all cells share one capture workspace

`create_launch_verification_coordinator` gives every cell the same
`storage_root/runtime/baseline-verification` working directory, and different cells verify
concurrently by design. The captured-run `WorkspaceLock` is per-`run_id`, so there is no
lock contention, and `_ISOLATED_HOME` keeps agent state out of the workspace. I could not
construct a concrete failure, so this is flagged as speculation rather than a finding: any
harness that writes cwd-relative state during a turn would cross-contaminate two
concurrent captures' evidence.

---

## Attacks that did not land

Recorded so the next reader does not repeat them.

- **Exception escape into `prepare_capture` (brief item 1).** Containment is sound.
  `schedule_prepared_launch_verification` wraps the whole body including
  `get_harness_descriptor` and receipt validation; `LaunchVerificationCoordinator.submit`
  wraps coroutine construction; `OwnedVerificationTasks.submit` wraps `create_task` and
  closes the coroutine on failure or after `aclose`. Lock acquisition, staleness, cell
  resolution, quota lookup and the worker all run inside `_run_candidate`'s
  `except Exception`. Only `BaseException` escapes, which is correct. The scheduler-failure
  and blocked-harvest response-equality tests are honest.
- **Recursion (brief item 4).** Structurally prevented, not merely documented — though not
  by the AST test. `harvest_controlled_baseline` reaches `run_captured_turn` by direct
  import, never the RPC, so `prepare_capture` is never re-entered. Even if it were, the
  `flock` in `WorkspaceLock` is held against the open file description, so a second
  acquisition inside the same process fails `LOCK_NB` and returns. The AST test asserts
  only what `baseline_capture` imports; a recursion introduced in `captured_turn` or
  `capture_rpc` would not be caught. Documentation-grade, but the lock is the real guard.
- **Staleness input (brief item 6).** Correct. `installed_version` is
  `facts.observed_version` from the launch's own freshly written artifact, and
  `CompatibilityFactArtifact` validates that it is normalized. `_observe` probes the binary;
  the stored `HarnessInstallationInfo` row is never consulted. Both `_is_current` and the
  post-capture equality check use the same value, and `test_prepared_facts_drive_both_staleness_checks`
  pins it.
- **Lock liveness (brief item 7).** No wedge. `WorkspaceLock` is kernel-held, so process
  death releases it; `__exit__` is in a `finally`; both `_is_complete` early returns are
  inside the `try`. The only way to hold it indefinitely is M2's unbounded region.
- **Tests spending a provider turn (brief item 8).** None do. Every coordinator test injects
  a fake `harvest`; the route test injects a fake `harvest` and a fake `prepare_run`. The one
  real-database test (`test_quota_reader_only_reports_an_active_known_limit`) exercises SQL
  only. `harvest_controlled_baseline` is never called for real.
- **Import DAG and sizing.** Clean. `launch_verification` imports no FastAPI or gateway
  types and sits at the package root beside `verification_cell` and the other `baseline_*`
  modules, which matches the ownership argument in `verification_cell`'s docstring. The
  API adapter is confined to `api/v1/launch_verification_routes`, and `app: Any` there
  matches the `close_capture_registry` precedent. `launch_verification.py` is 456 lines;
  `capture_rpc_routes` 641, `main` 663, `baseline_capture` 410 — all under 700.
- **Quota honesty.** `read_known_quota_decision`'s docstring states plainly that absence
  stays unknown and that no positive allowance claim is ever returned, and
  `test_quota_contract_has_no_positive_headroom_claim` pins the two-member enum shut. The
  limitation is stated honestly. What is missing is upward: nothing in the module says a
  verification costs three provider turns, and nothing tells the operator it is happening.

---

# DELTA RE-REVIEW — `707c7dbb` → `9d0bcdc5` (`origin/launch-verification-coordinator`)

Reviewed `git diff 707c7dbb origin/launch-verification-coordinator` only. Read-only from the
main checkout at `b6979af4`; tree pristine, no edits, no checkout, no backend start, no
provider turns. All 16 changed Python files compile on the repo interpreter (3.14.5).

**Verdict:** the fixes are real. Both blockers are genuinely closed, not relocated. Twelve
of the thirteen original findings are closed; **M2 is closed in its consequences but still
open in its substance**, and the fix for it concentrated a new risk. No new blockers.

Delta counts: blockers 0, majors 2, minors 7.

## Status of the original thirteen

| # | Finding | Status |
|---|---|---|
| B1 | Failure re-bills on every launch | **Closed** |
| B2 | Receipt is a stored derivation that suppresses | **Closed** (deleted, not relocated) |
| M1 | Default-executor starvation of the launch path | **Closed** |
| M2 | Cooperative-only timeout, unbounded regions | **Partially closed — see D2** |
| M3 | Cross-channel double billing | **Closed as documented scope** (accepted, now stated) |
| m1 | Traceback on an ordinary ungated launch | **Closed** |
| m2 | Diagnostic discriminator untested at the seam | **Closed** (see d1) |
| m3 | Silent suppression | **Closed** |
| m4 | Quota SQL placement | **Closed** (see d2) |
| m5 | `drain()` had no production caller | **Closed** — `aclose` now drains before shutting the executor |
| m6 | Unreachable receipt-mismatch branch | **Closed** — the receipt is gone |
| m7 | Depth-relative repo root | **Closed** — `source_control.find_source_checkout_root`, three call sites unified, tested |
| m8 | Shared capture workspace | **Closed** — `launch_verification_workspace` per cell and version, asserted distinct |

### Why B1 is closed
`captured_turn.run_captured_turn` now calls `on_client_spawn` after `prepare_captured_run`
and **before** `supervisor.spawn`, and
`LaunchVerificationCoordinator._verify_under_lock.record_provider_start` writes an
`IN_PROGRESS` attempt there. Every exit from the harvest — exception, hard deadline,
version mismatch, missing evidence — reaches `finish_baseline_attempt(FAILED)`, and
`_capture_is_due` then cools that cell for 24h. `test_harvest_ignores_title_request_that_wraps_controlled_prompt`
now asserts the literal ordering `attempt → spawn → terminate` three times, and
`test_cancellation_after_prepare_prevents_client_spawn` proves a cancellation in that
window produces neither. The two tests that encoded the defect are gone, replaced by
`test_failed_provider_attempt_cools_then_retries` (which advances a clock 24h and asserts
`attempt_count == 2`) and `test_attempt_is_written_before_the_provider_boundary`. The
worst case is now three turns per cell per version per day instead of per launch.

### Why B2 is closed rather than relocated
Completion is derived: `baseline_store.has_baseline_bundle_for_version` asks the evidence
itself. The attempt artifact carries `artifact_schema_version: BaselineArtifactSchemaVersion`
(`Literal[7]`), the **same** constant the bundles carry, and `read_baseline_attempt`
returns `None` — degrades, does not raise — when the header does not match. So a schema
bump invalidates the evidence and the retry state *together*, which is exactly what the
old receipt could not do. Two tests pin the two directions that matter:
`test_immutable_evidence_survives_pointer_and_attempt_loss` (pointer and attempt deleted,
bundle intact → still suppressed) and `test_success_state_without_evidence_does_not_suppress_capture`
(bundle deleted → captures again). `test_evidence_schema_bump_invalidates_retry_state`
covers v6-under-v7. A `SUCCEEDED` attempt deliberately does not suppress on its own.

### Why M1 is closed
`verification_executor.BoundedDaemonExecutor` owns two named daemon threads and rejects
rather than queues at saturation. `test_prepare_stays_fast_when_verification_workers_are_saturated`
saturates both workers with two distinct cells, asserts the third `POST /v1/capture/prepare`
returns in under 0.5s, and asserts the worker thread names are
`transport-matters-verification-0/1` — which is what actually proves the work left the
default executor. That is a genuine proof, not a proxy.

**Correction to the brief's expectation:** a third and fourth cell are **rejected, not
queued**. `test_candidate_capacity_and_cell_lock_run_one_harvest` asserts
`scheduled == [True, True, False, False, False]`. That is the better choice and is stated
in `BoundedDaemonExecutor`'s docstring ("saturation rejects new jobs instead of growing a
hidden backlog"), and a dropped cell is retried on its next launch because nothing was
recorded. But nothing queues, and no fallback to the default executor exists.

---

## D1 — MAJOR (new): the completeness check fully parses every bundle in the cell, three times per candidate

**Where:** `baseline_store.has_baseline_bundle_for_version`, called from
`LaunchVerificationCoordinator._capture_is_due` (twice: before and under the lock) and
once more after a successful harvest.

The function globs the cell directory and calls `read_baseline_bundle` on every entry —
`json.loads` plus full `BaselineBundle.model_validate`, including the base64 raw request
bodies — until one matches. `baseline_staleness`'s module docstring exists to forbid
exactly this: *"the sixteen pointers in a real store total 4,263 bytes, while the bundles
they name total 56 MB. Nothing here opens a bundle."* The B2 fix now opens them, on every
launch that submits a candidate.

**Failure scenario:** measured against the live stable store — 16 bundles, 54 MB, mean 3.51 MB
each, currently one per cell. That is ~10 MB of JSON parsed and validated per candidate
today. Bundles are immutable and never pruned, and one accrues per harness version per
cell (plus one per degraded or breaking capture, which are written but not promoted). After
a year of monthly harness updates a single cell holds a dozen bundles: ~42 MB parsed per
check, ~126 MB per candidate, with the matching bundle found on average halfway through.
The steady state — everything verified, launches repeating — is the worst case, because the
directory is at its fullest and the scan runs on every launch. It burns CPU and transient
RSS on the operator's machine indefinitely.

It runs on the dedicated worker, so it cannot delay a launch. That is why this is major and
not a blocker.

**Direction:** the repo already has the idiom twice (`_CurrentBundlePointerHeader`,
`_AttemptHeader`) — validate a header-only model carrying `artifact_schema_version` and
`cell.harness_version` and skip the body, or maintain a per-version index beside the
bundles. The current pointer cannot answer this question (it only advances on promotion),
so the scan itself is the right design; parsing 3.5 MB to read one string is not.

## D2 — MAJOR: the hard deadline does not bound the regions M2 named, and two workers make the wedge worse

**Where:** `LaunchVerificationCoordinator._run_candidate` (`async with asyncio.timeout(self.aba_timeout)`),
`verification_executor.BoundedDaemonExecutor`, `captured_turn._raise_if_cancelled`.

`asyncio.timeout` bounds the coordinator's **awaiting**, not the worker thread. The new
`_raise_if_cancelled` calls sit *between* `prepare_captured_run`, `on_client_spawn` and
`supervisor.spawn` — so a hang is now detected between those regions, but each region is
still unbounded: `prepare_captured_run` (port probes, mitmdump resolution, credential
broker, control-plane grant), `ProcessSupervisor.spawn`, and `terminate_all()` in the
`finally`. The brief asked whether the deadline bounds those. It does not; the "post-prepare
spawn gate" covers the seams between them, which was M2's other half.

What did close: shutdown. `BoundedDaemonExecutor.shutdown` never joins, the threads are
daemons, and `test_hard_deadline_and_shutdown_do_not_wait_for_uncooperative_worker` proves
`aclose()` returns in under 0.5s against a worker that ignores cancellation. The lock is no
longer held hostage across shutdown, and an `IN_PROGRESS` attempt converts a wedge into a
24h cooling rather than a permanent one.

**Failure scenario (introduced by the M1 fix):** `_MAX_CANDIDATES = 2`, so the dedicated
pool is two threads. A `port_in_use` probe against a wedged socket, or a mitmdump
resolution that blocks, parks one worker permanently — `time.monotonic() >= deadline` is
never evaluated because control never returns to a check. One wedged capture halves
verification throughput; two wedge it entirely, and every later candidate logs
`worker capacity unavailable` at INFO and does nothing, for the life of the process. Before
this change the same hang consumed one of ~14 shared threads. The fix correctly stopped
verification from starving launches and, in doing so, made verification able to starve
itself with two incidents.

**Direction:** bound the regions themselves (timeouts on the probe and spawn calls), or
detect exhausted capacity and log at ERROR rather than INFO so the operator learns that
verification has stopped rather than inferring it from silence.

## d1 — MINOR: half the diagnostic-discriminator test asserts an unreachable state

**Where:** `api/v1/test_launch_verification_routes.test_validated_receipt_approval_is_the_diagnostic_discriminator`.

Moving the discriminator to `receipt.approval` (from the request body) is right, and it
carries a property worth naming: `executor_id` and `diagnostic_test` are both read off the
receipt, so a receipt that fails validation yields `executor_id=None` and the submission is
refused outright — the two facts fail together and a bad receipt can never bill.

But the test's first half builds `request_approval="diagnostic_test"` with
`receipt_approval="not_required"` and asserts the request claim is ignored.
`access_policy.assess_provider_access` cannot produce that pair: `approval` is
`"diagnostic_test"` unconditionally whenever `provider_access_approval == "diagnostic_test"`,
as the first branch of the expression, before any state check. So the case is unreachable,
and the assertion encodes a divergence that would be a resolver bug rather than a policy.
The second half — receipt says diagnostic, coordinator skips — is the real test.

## d2 — MINOR: `live.closed = false` loosens the money guard and is untested

**Where:** `session/controlplane_statements.GET_ACTIVE_USAGE_LIMIT_FOR_OWNER_SQL`.

The move to `controlplane_statements` is exactly what m4 asked for. The statement also
gained `AND live.closed = false`, which was not in the version I reviewed. That is a
behaviour change, not a relocation: a finalized usage-limit generation on a still-running
run now returns `UNKNOWN` where it previously refused, so verification will spend in a state
the old code protected. The reading is defensible — `dao_statements` treats `closed = true`
as "the generation is finalized" — and it matches the new name. But
`test_quota_reader_only_reports_an_active_known_limit` never writes a closed row, so the
one predicate that decides whether to spend money in this state has no test.

## d3 — MINOR: the attempt is recorded one cancellation check too early

**Where:** `captured_turn.run_captured_turn` — `on_client_spawn()` fires, then
`_raise_if_cancelled`, then `supervisor.spawn`.

A cancellation or deadline landing in that window writes an `IN_PROGRESS` attempt for a
probe that never spawned, and the failure path then cools the cell for 24 hours having
spent nothing. Swapping the check and the callback closes all of it except the
irreducible record-then-die window. `test_cancellation_after_prepare_prevents_client_spawn`
proves the earlier check works; it does not cover this one.

## d4 — MINOR: two daemon threads start at construction, not at first use

**Where:** `OwnedVerificationTasks.__post_init__`.

`BoundedDaemonExecutor.__init__` starts its threads eagerly, so every
`OwnedVerificationTasks()` costs two threads immediately. Production builds one. The test
suite builds one per coordinator — roughly twenty in `test_launch_verification` plus the
route tests — and most never call `aclose()`, so each leaves two threads blocked on
`Queue.get()` for the rest of the session. Harmless (daemon, idle), but it is avoidable
with a lazy start on first submit.

## d5 — MINOR: a corrupt attempt file blocks its cell permanently

**Where:** `baseline_attempts.read_baseline_attempt`.

An old-schema attempt degrades to `None` (correct, and tested). A *current*-schema file that
fails validation, or whose coordinates disagree with its path, raises `ValueError`. That
propagates out of `_capture_is_due`, fails the candidate open, and repeats on every launch —
the cell never verifies again until someone deletes a file in a directory nothing surfaces.
`read_current_baseline_ref` faces the same choice for pointers and answers `None`. Absent
and unreadable should degrade the same way here.

## d6 — MINOR: `has_baseline_bundle_for_version` does not catch `OSError`

**Where:** `baseline_store.has_baseline_bundle_for_version` (`except ValueError, ValidationError`).

A corrupt bundle is skipped; an unreadable one (permissions, a vanished file between `glob`
and `read_bytes`) raises out of `_capture_is_due` and fails the candidate open. The two
should be treated alike — a bundle that cannot be read is not evidence.

The unparenthesized multi-`except` is correct PEP 758 on this repo's 3.14 floor and matches
ten existing sites; verified compiling on `api/.venv/bin/python` (3.14.5), not the ambient
3.13.

## d7 — MINOR: tests reach into other test modules' private names

**Where:** `test_launch_verification` and `test_launch_verification_routes` both import
`_bundle` (and `_compared`) from `transport_matters.test_baseline_evidence`;
`test_valid_degraded_evidence_skips_before_locking` also does its imports inside the test
body.

Sharing the builder is right — the alternative is duplicating bundle construction — but a
leading underscore imported across modules says the opposite of what the code does. Promote
the two builders to public names in a shared test-support module, as
`test_capture_rpc_support` already is.

---

## Delta items verified clean

- **No provider turns, still.** Every fake harvest writes a real bundle via
  `write_baseline_bundle` rather than a `SimpleNamespace` — a strictly stronger fixture — and
  none reaches `harvest_controlled_baseline`. `test_captured_turn`'s harvest tests use the
  installed capture fakes. The one real-database test is SQL only.
- **Out-of-coordinator changes are each warranted.** `source_control.find_source_checkout_root`
  is m7's fix, with its own test; `channel_cmd.repo_root` is the same walk it already
  performed, now shared; `main._SOURCE_ROOT` falls back to the package directory instead of
  a wrong `parents[3]`, and both non-checkout paths degrade identically through
  `identify_runtime_source` to the installed distribution, so #435's source identity is
  untouched; `baseline_harvest` now fails with a clear error instead of passing a wrong path
  to `require_clean_worktree`, inside the existing `try`. `captured_turn` and
  `baseline_capture` gained one optional keyword each, defaulting to `None`, so no existing
  caller changes behaviour.
- **Cooldown keying and expiry.** Keyed on harness, provider, launch model and harness
  version, under the channel's own `output_root`. `retry_after = started_at + cooldown`,
  validated non-preceding and timezone-aware, so a naive datetime cannot slip in. `SUCCEEDED`
  never suppresses on its own — only evidence does — so the cooldown cannot outlive the
  thing it is protecting. A backend crash mid-capture leaves `IN_PROGRESS` and costs the cell
  one day, which is the conservative direction. A clock jumped far forward while an attempt
  is written would suppress that cell until the recorded `retry_after`, but nothing in the
  design amplifies that beyond one cell and one version.
- **Executor accounting.** Capacity covers queued and running work; `_worker` releases in a
  `finally`; `shutdown` releases exactly the futures it cancels and then feeds one sentinel
  per thread. Candidate capacity and worker capacity are both two and are acquired in a fixed
  order with the facts-read slot released before the verify slot is taken, so the two
  semaphores cannot deadlock.
- **Containment into `prepare_capture`** is unchanged and still sound; the only edit to the
  route adapter is the discriminator expression.
