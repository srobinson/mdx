---
title: Transport Matters Test Timing Audit
type: projects
tags: [transport-matters, tests, ci, flakiness, timing, pytest, audit]
summary: Where the backend suite's wall clock actually goes, every timing-dependent assertion in it, and a delete/convert/keep verdict for each
status: active
project: transport-matters
confidence: high
created: 2026-08-23
updated: 2026-08-23
---

# Transport Matters Test Timing Audit

Report only. Nothing was written to the repository.

## Headline

**The suite is width-bound, and the width is already provisioned and commented out.**
Every job in `.github/workflows/ci.yml` carries a commented `blacksmith-4vcpu-ubuntu-2404`
line directly above its active `runs-on: ubuntu-latest`. Uncommenting the backend one is a
larger wall-clock win than every test change in this document combined, and it costs no
coverage.

**No test or file is the critical path.** The 20 slowest tests are 23% of measured CPU and
the slowest single file is 25.8s against a 270s CI wall. The theory that a handful of tests
dominate is dead.

**Twelve assertions in the suite depend on wall clock or thread scheduling. Eleven of them
are redundant** with a deterministic assertion already present in the same test. That is the
flakiness story: not thread choreography, which is mostly justified here, but performance
claims bolted onto tests that had already proved the thing.

## Inspection boundary

Measured on this machine (12 workers, Python 3.14.5, `api/.venv`) against
`fix/capture-economics`. **The tree was dirty throughout**: codex is actively editing, and the
modified set grew from two files to five during the audit, including a new
`test_launch_verification_economics.py` that appears to be a split of
`test_launch_verification.py`. Symbol-level findings hold; that file's duration and loadfile
grouping will move under codex.

Four full suite runs, all with `-p no:cacheprovider` so no `.pytest_cache` was written. No
repository file was created, modified, or deleted by me.

| run | wall | user CPU |
| --- | ---: | ---: |
| `-n auto --dist loadfile` | **47.7s** | 154.2s |
| same, `--durations=0` | 52.1s | (capture run) |
| same, `--cov=transport_matters --cov-report=term` | **60.4s** | 205.0s |
| same, `COVERAGE_CORE=sysmon` | 58.4s | 207.2s |

4,101 passed, 0 failed, in every run. Codex's in-flight edits are green.

## 1. The slow list

Twenty slowest, `--durations`, local 12-worker run without coverage:

| # | s | test |
| ---: | ---: | --- |
| 1 | 9.36 | `api/v1/test_run_proxy.py::test_canvas_origin_reaches_space_gateway` |
| 2 | 8.79 | `api/v1/test_run_proxy.py::test_canvas_origin_contract_splits_run_routes_to_gateway` |
| 3 | 8.48 | `tests/integration/test_launch_affinity_authority.py::test_gateway_denies_forged_tuple_and_mcp_foreign_inventory` |
| 4 | 7.81 | `api/v1/test_run_proxy.py::test_plain_terminal_proxies_bytes_to_the_gateway` |
| 5 | 7.69 | `tests/integration/test_launch_affinity_authority.py::test_child_launch_accepts_owned_tuple_and_mcp_owned_read` |
| 6 | 5.47 | `session/test_migration_roundtrip.py::test_alembic_upgrade_and_downgrade_smoke` |
| 7 | 3.82 | `tests/integration/test_shared_proxy_subprocess.py::test_shared_proxy_manager_respawns_and_rehydrates_live_bindings` |
| 8 | 3.75 | `tests/integration/test_backend_launch_smoke.py::test_launched_backend_reads_db_from_home_not_per_run_storage` |
| 9 | 2.85 | `tests/integration/test_captured_proxy_post.py::test_captured_proxy_records_real_post` |
| 10 | 2.85 | `tests/test_release_script.py::test_release_install_waits_installs_exact_version_and_verifies_cli` |
| 11 | 2.73 | `session/test_migrate.py::test_session_classification_migration_backfills_checks_and_downgrades` |
| 12 | 2.69 | `test_main.py::test_startup_access_verification_waits_for_refresh` |
| 13 | 2.68 | `tests/integration/test_capture_launch_target.py::test_capture_prepare_preserves_default_and_resolves_only_explicit_target` |
| 14 | 2.63 | `shared_proxy/test_manager.py::test_shared_proxy_modules_import_in_fresh_interpreter` |
| 15 | 2.59 | `cli/test_home_seed.py::test_home_seed_modules_import_in_fresh_subprocess` |
| 16 | 2.38 | `test_main.py::test_preset_startup_access_verification_wins` |
| 17 | 2.36 | `launch/test_seam_imports.py::test_launch_seam_imports_cleanly` |
| 18 | 2.28 | `session/test_harness_drift_evidence_migration.py::test_harness_drift_evidence_migration_round_trip` |
| 19 | 2.28 | `tests/integration/test_captured_proxy_post.py::test_captured_template_proxy_records_real_post_and_leaves_the_template_alone` |
| 20 | 2.22 | `test_main.py::test_refresh_upserts_run_off_loop_and_persist_through_the_real_store` |

**Fraction: 83.9s of 363.4s measured CPU, 23.1%.** A further 9,691 entries fell below the 5ms
reporting floor and add at most 48s in aggregate.

Every one of these is a subprocess, a real HTTP proxy hop, a fresh interpreter import, or an
Alembic round trip. None is a sleep and none is choreography. **They are earning their keep**,
and deleting all twenty would remove roughly a fifth of the CPU while removing the only tests
that exercise process boundaries.

### The distribution is flat, and `--dist loadfile` makes the file the unit

| s | file |
| ---: | --- |
| 25.84 | `api/v1/test_run_proxy.py` |
| 16.91 | `harnesses/test_certification_evidence.py` |
| 15.87 | `tests/integration/test_launch_affinity_authority.py` |
| 14.85 | `test_main.py` |
| 13.81 | `harnesses/test_connections_store.py` |
| 11.45 | `tests/integration/test_reset_channel_store.py` |

317 files carry measurable time. The slowest is 25.8s against a 270s CI wall, so **no file is
the critical path on two workers**: even a one-worker-per-file scheduler has 244s of slack.
Local 12-worker wall (47.7s) against CI 2-worker wall (270s) is a ratio of 5.7x against a
worker ratio of 6x. The wall clock is worker count, exactly as the brief states. Nothing here
contradicts it.

## The three wall-clock wins, ranked

### W1. Uncomment the 4-vCPU runner. Largest win, zero risk, no test changes

`.github/workflows/ci.yml` has, above every job:

```yaml
    # runs-on: blacksmith-4vcpu-ubuntu-2404
    runs-on: ubuntu-latest
```

Doubling from 2 to 4 workers on a width-bound suite roughly halves the backend job. Expected
`4m30s` to about `2m20s`. Nothing in the suite resists it: the slowest file is a tenth of the
wall, so there is no serialization floor to hit at four workers either.

Do this before changing a single test.

### W2. `session/test_migrate.py` runs twice per CI job

The backend job runs two pytest invocations:

```yaml
uv run python -m pytest -n0 src/transport_matters/session/test_migrate.py -q
uv run pytest -n auto --dist loadfile --cov=transport_matters --cov-report=term
```

`testpaths = ["src", "tests"]`, so the second invocation collects `test_migrate.py` again. The
file is 7.70s locally, so this is roughly 15s of pure duplication on a CI core, plus a second
interpreter and collection pass.

The comment explains the intent ("worker startup adds cost without parallelizing these
tests"), which is true of running it *alone*, but the second command does not deselect it.
Either `--ignore` it in the parallel run or drop the serial pass entirely; `--dist loadfile`
already keeps the file on one worker, which is exactly what the comment wants.

### W3. Coverage costs 27% of wall, and the cheap backend does not help

Measured on identical trees: 47.7s without coverage, 60.4s with, a **+26.6% wall and +33% CPU**
tax. On CI that is roughly 60 to 70 seconds of the 4m30s.

I tested the obvious lever and it failed. `COVERAGE_CORE=sysmon`, the `sys.monitoring` backend
that is usually a large win on 3.12+, produced 58.4s against 60.4s: **3%, inside noise.** Do
not spend time on it.

`fail_under = 80` in `api/pyproject.toml` is a real gate, so coverage cannot simply be dropped.
The options are to accept the tax or to run coverage in its own job in parallel with the plain
suite, so the gate's wall clock is the faster of the two rather than the sum. That is a
judgment call about CI minutes, not correctness.

## 2. The faulty list

Twelve assertions across eleven tests depend on wall clock or scheduling. I searched the whole
suite for `perf_counter`, `monotonic()`, `time.sleep`, negative `wait(...)`, `is_alive()`
assertions, and short `join`/`wait` budgets. The `deadline = monotonic() + N; while ...` polling
helpers in `test_main`, `test_lock`, `test_gateway_support`, `cli/test_desktop_foreground`,
`tests/integration/test_parent_death_reaping`, `tests/integration/test_gateway_wheel_spawn` and
`tests/integration/test_shared_proxy_subprocess` are **not** in this list: they wait for a
condition and assert after it, which can only be slow, never wrong.

Nine are upper-bound wall-clock assertions. Three are negative or liveness assertions about
threads.

| # | test (path::SYMBOL) | assertion | asserts | verdict |
| ---: | --- | --- | --- | --- |
| 1 | `api/v1/test_launch_verification_routes.py::test_prepare_stays_fast_when_verification_workers_are_saturated` | `elapsed < 0.5` | performance | CONVERT |
| 2 | `api/v1/test_launch_verification_routes.py::test_prepare_response_is_identical_while_verification_runs` | `elapsed < 2` | performance | CONVERT |
| 3 | `test_launch_verification.py::test_hard_deadline_and_shutdown_do_not_wait_for_uncooperative_worker` | `monotonic() - before < 0.5` | performance | CONVERT |
| 4 | `test_bounded_call.py::test_timeout_releases_the_caller_and_cleans_up_a_late_result` | `< 0.2` | performance | CONVERT |
| 5 | `supervisor/test_operation_timeout.py::test_detached_spawn_timeout_releases_caller_and_terminates_late_child` | `< 0.2` | performance | CONVERT |
| 6 | `test_captured_turn_operations.py::test_blocking_preparation_dependencies_have_hard_bounds` | `< 0.2` | performance | CONVERT |
| 7 | `test_credential_broker.py::test_concurrent_caller_blocks_then_rereads_without_second_exchange` | `assert not store.second_read.wait(timeout=0.2)` | scheduling | CONVERT |
| 8 | `test_self_reap.py::test_watchdog_stays_quiet_while_parent_lives` | `assert not probe.done.wait(timeout=0.05)` | scheduling | CONVERT |
| 9 | `harnesses/test_connections_store.py::test_concurrent_revision_bump_cannot_slip_stale_access_evidence` | `join(0.5)` then `assert upserter.is_alive()` | scheduling | CONVERT |
| 10 | `test_main.py::test_startup_access_verification_waits_for_refresh` | `< 10` | performance | CONVERT |
| 11 | `test_breakpoint.py::TestBreakpointTimeout::test_event_wait_with_timeout_fires` | `pytest.raises(TimeoutError)` on `wait_for(..., 0.01)` | stdlib behaviour | **DELETE** |
| 12 | `test_captured_turn.py::test_a_refused_provider_fails_before_the_timeout` | `< 5.0` against a 30s deadline | correctness | **KEEP** |
| 13 | `test_captured_turn.py::test_codex_server_refusal_fails_fast_with_the_provider_reason` | `< 5.0` against a 30s deadline | correctness | **KEEP** |

## 3. Verdict per test

Ranked by flakiness risk, tightest budget first.

### CONVERT 1. `test_prepare_stays_fast_when_verification_workers_are_saturated` (0.5s)

The name is the defect: it is a performance property by title. It is also the tightest budget
in the suite measured across a live `TestClient` POST on a contended runner, which makes it my
first pick for the CI reds.

**Replace with what is already there.** Two lines below the timing assertion sit
`assert sorted(workers) == ["transport-matters-verification-0", "transport-matters-verification-1"]`
and `assert any("candidate capacity unavailable" in error for error in capacity_errors)`. Those
prove the pool is bounded at two and the third submission was refused rather than queued. A
third request that had blocked on a saturated pool would produce neither. **Delete
`assert elapsed < 0.5`, keep everything else.** The test stays; the claim is unchanged.

### CONVERT 2. `test_hard_deadline_and_shutdown_do_not_wait_for_uncooperative_worker` (0.5s)

This one is subtly worse than it looks. The line above already reads
`await asyncio.wait_for(coordinator.aclose(), timeout=0.5)`, which enforces the bound
structurally. But `before` is taken *before* `await coordinator.tasks.drain()`, so the
measurement charges drain plus aclose against 0.5s while the structural guard allows 0.5s for
aclose alone. **The assertion is a second, tighter, undocumented budget on a superset of the
work.**

`assert not stopped.is_set()` immediately after is the real claim: shutdown did not wait for
the uncooperative worker. That is deterministic state. **Delete the elapsed assertion**; the
`wait_for` already says what it was trying to say, and says it correctly.

### CONVERT 3, 4, 5. The three 0.2s hard-bound tests

`test_bounded_call.py::test_timeout_releases_the_caller_and_cleans_up_a_late_result`,
`supervisor/test_operation_timeout.py::test_detached_spawn_timeout_releases_caller_and_terminates_late_child`,
and `test_captured_turn_operations.py::test_blocking_preparation_dependencies_have_hard_bounds`
are the same shape at three layers: configure a 0.02s bound, block, assert `TimeoutError`,
assert it returned within 0.2s.

That the same shape appears three times is correct layering, not duplication: the primitive,
the supervisor spawn, and the capture dependencies each have their own wiring.

The elapsed assertion in all three is redundant. `pytest.raises(TimeoutError, match=...)` is
the correctness claim, and it is deterministic: a broken bound would wait out the inner
`release.wait(timeout=5)`, which returns `False` rather than raising, so `pytest.raises` would
fail. The 0.2s check adds only "within 10x the configured bound", and 10x of 20ms is 180ms of
slack for thread start, GC, and worker contention on a two-core runner. That is not generous.

**Delete all three elapsed assertions.** Keep `pytest.raises` and keep the
`assert cleaned.wait(timeout=1)` late-result assertions, which are positive waits.

### CONVERT 6. `test_concurrent_caller_blocks_then_rereads_without_second_exchange` (200ms)

One of the two the brief names. Confirmed present.

`assert not store.second_read.wait(timeout=0.2)` claims the second caller is blocked on the
file lock. It passes vacuously if the second thread has not started yet, which on a loaded
two-worker runner is exactly what happens.

**It is entirely redundant.** Below it the test already asserts
`store.read_count == 3`, `store.write_count == 1`, and
`exchanger.calls == [("synthetic-refresh-before", SCOPES)]`. One exchange, one write, three
reads is the complete proof that the second caller blocked and then re-read rather than
minting again, and every one of those is deterministic. **Delete the negative wait.**

### CONVERT 7. `test_watchdog_stays_quiet_while_parent_lives` (50ms)

The other one the brief names. Confirmed present, and it is worse than flaky.

`probe.done` is set only by the reap path, which runs only when `getppid()` returns 1. The
test pins the parent at 4242 until after this line. **The assertion can never fail.** It is a
50ms sleep wearing an assertion's clothes, and it makes a negative claim that no defect could
falsify.

The line immediately after, `assert probe.kills == []`, makes the same claim as state, for
free, and *can* fail. The lines after that flip the pid and assert `probe.done.wait(timeout=2)`,
which is the real correctness property. **Delete the negative wait; keep the rest.**

### CONVERT 8. `test_concurrent_revision_bump_cannot_slip_stale_access_evidence` (500ms)

`upserter.join(0.5)` then `assert upserter.is_alive(), "the revision guard did not wait for the
concurrent bump"`. This is the most defensible of the scheduling assertions, and it is still
redundant.

The test's tail already proves it. The upserter's captured outcome must be a `ValueError`
reading `"carries revision 1, current is 2"`, and the final assertion requires
`latest_access_observations(...) == ()`. A guard doing a plain read would see the uncommitted
revision 1, pass, and insert, producing `outcome == [None]` and a non-empty observation list.
**Observing the committed revision 2 is only possible by having waited for the commit**, so the
`ValueError` message is the proof that the block happened.

**Delete `join(0.5)` and the `is_alive()` assertion.** The test remains a real two-connection
concurrency test; only its assertions become state-based, and it drops 500ms.

### CONVERT 9. `test_prepare_response_is_identical_while_verification_runs` (2s)

`assert elapsed < 2` sits directly above
`assert with_verification.json() == without_verification.json()`, which is the actual claim:
the prepare response is unchanged while verification runs. `assert started.wait(timeout=2)`
above it proves verification really started, and is a sound positive wait.

**Delete the elapsed assertion.** Lower risk than the others at 2s, but it is the same
redundant performance claim and should go with them.

### CONVERT 10. `test_startup_access_verification_waits_for_refresh` (10s)

`assert time.monotonic() - t0 < 10` guards liveness while a worker thread is parked on a
barrier. It cannot do the job: if the request genuinely blocked, it would block until
`gate.set()` further down, so the suite hangs rather than failing, and an assertion evaluated
after the request returns never runs. The 200 status codes already asserted are the real
liveness proof.

**Delete it.** Lowest priority of the ten; the margin means it essentially never fires, but it
buys nothing.

### DELETE 1. `TestBreakpointTimeout::test_event_wait_with_timeout_fires`

Its own docstring gives it away: *"Simulates the timeout pattern used in `_handle_breakpoint`."*
It never calls `_handle_breakpoint`. It asserts that
`asyncio.wait_for(event.wait(), timeout=0.01)` raises on an unset `asyncio.Event`, which is a
property of the standard library.

The only claims it makes about `breakpoint` are `pf is not None` and `pf.dropped is False`
after the timeout, and both are already covered: `test_pop_removes_and_returns` proves pop
returns the flow, and `test_release_sets_event` already asserts `pf.dropped is False`. Nothing
is lost.

**Delete the test.**

### KEEP 1 and 2. The two `test_captured_turn` refusal tests

`test_a_refused_provider_fails_before_the_timeout` and
`test_codex_server_refusal_fails_fast_with_the_provider_reason` assert
`time.monotonic() - started < 5.0` against a configured `timeout=30.0`.

These are the one case where the clock is the assertion and nothing else can be. Both the
fail-fast path and the sit-on-the-deadline path raise `CapturedTurnError`; only elapsed time
distinguishes them. The docstring records the incident that motivated it: *"Three probes at the
180s default turned one refusal into nine minutes of silence and pointed debugging at the wrong
subsystem."*

The margin is 6x, the widest in the suite. **Keep both.** If either ever flakes, the conversion
is to count entries into the transcript-wait fake in `_install_capture_fakes` and assert it was
never entered, which turns the same claim into state.

### What is justified and stays untouched

The thread choreography in `harnesses/test_certification_minting::test_concurrent_writers_yield_one_complete_record`,
`test_credential_refresh::test_concurrent_expired_oauth_401s_remint_off_loop` (a `threading.Barrier`,
which is a rendezvous rather than a timing bet), `test_lock::test_exclusive_file_lock_blocks_until_holder_releases`,
`shared_proxy/test_core::test_shared_snapshot_writer_unregister_races_child_cursor_registration`,
and the delivery and watch families under `controlplane/` are all positive waits on real
concurrency invariants that a single-threaded test cannot express. They can be slow. They
cannot be wrong. Leave them.

## 4. The two unsound negative assertions

Both confirmed present at the audited tree.

**`test_self_reap.py::test_watchdog_stays_quiet_while_parent_lives`**, 50ms.
Fix: delete `assert not probe.done.wait(timeout=0.05)`. The next line,
`assert probe.kills == []`, is the same claim as state and can actually fail.

**`test_credential_broker.py::test_concurrent_caller_blocks_then_rereads_without_second_exchange`**,
200ms. Fix: delete `assert not store.second_read.wait(timeout=0.2)`, keeping the
`try/finally` that sets `release_exchange`. The three count assertions at the end of the test
already prove it deterministically.

**The brief's count is stale, and low.** An earlier pass counted about 39 `wait(timeout=...)`
sites; the tree today has **122**. That growth is almost entirely benign positive waits, and
the count is not the right metric anyway: 122 waits produced 3 unsound assertions, and the
audit found a third the earlier pass missed, `test_connections_store`'s `is_alive()` check,
plus nine wall-clock bounds it did not look for at all.

## 5. `pytest-timeout`

**Yes, add it. Set `timeout = 120`, not 60.**

Confirmed absent: not in `api/pyproject.toml` dependencies, and `[tool.pytest.ini_options]`
carries only `testpaths`, `asyncio_mode`, `addopts` and `filterwarnings`.

The case for it is not flakiness, it is the hang. **The backend job has no `timeout-minutes`**,
so a test that deadlocks burns GitHub's 360 minute default before anyone sees a red. A suite
this thread-heavy has real hang paths: any rendezvous where an `Event.set()` is missed parks a
worker forever.

**Why 120 and not 60.** `test_launch_verification.py` defines
`_RENDEZVOUS_TIMEOUT_S = 60.0`. A 60s per-test timeout would race its own rendezvous budget and
turn a legitimate slow release into a timeout kill. Other long internal budgets: 20s in
`test_gateway_support`, 15s in `cli/test_desktop_foreground`, 10s in
`supervisor/test_detached_pty`, `test_gateway_supervisor`,
`tests/integration/test_backend_launch_smoke` and `tests/integration/test_shared_proxy_subprocess`.

**Which tests would break at 120s: none.** The slowest test in the suite is 9.36s locally.
Even at CI's roughly 2x slower contended core that is under 20s, leaving 6x headroom. The
subprocess and migration tests named in the brief are all well inside it:
`test_alembic_upgrade_and_downgrade_smoke` 5.47s,
`test_launched_backend_reads_db_from_home_not_per_run_storage` 3.75s,
`test_release_install_waits_installs_exact_version_and_verifies_cli` 2.85s.

**Use `timeout_method = "thread"`, not the signal default.** SIGALRM does not interrupt a
thread blocked in `flock`, `Event.wait`, or a subprocess read, which is precisely where this
suite hangs. The thread method costs the rest of that worker's file when it fires, which is
acceptable for an event that should never happen.

```toml
[tool.pytest.ini_options]
timeout = 120
timeout_method = "thread"
```

**Also add `timeout-minutes: 20` to the backend job in `.github/workflows/ci.yml`.** The
per-test timeout catches a hung test; the job timeout catches a hung fixture, a wedged
Postgres service container, or a worker that never starts, none of which `pytest-timeout`
sees. Twenty minutes is roughly 4x the current 4m30s.

If `_RENDEZVOUS_TIMEOUT_S` is lowered to 15s (nothing in that file legitimately needs 60s to
release a test-owned `Event`), the global timeout can come down to 60s and the guard gets
sharper. That is an independent, optional improvement.

## 6. One standard

> A test may drive threads only to create a state that one thread cannot reach. Once that
> state exists, assert it as state, never as elapsed time.
>
> Concretely: a rendezvous that makes two writers contend is legitimate, because contention is
> the condition under test. A stopwatch reading afterwards is not, because it asserts how fast
> the code was rather than what it did. If the only way a test can fail is by waiting out a
> timeout, it is measuring the runner and must be deleted or converted.
>
> Never assert that something has *not* happened yet by waiting a short interval. That
> assertion passes when the code is broken and the thread is merely slow. Count the calls
> instead.

`test_launch_verification::test_different_cells_harvest_concurrently` is the worked example the
owner already ruled on: two threads through a rendezvous to assert a concurrency *performance*
property, failing only by timeout, replaced by a pure assertion on lock addressing. Every
CONVERT above is the same trade, and in ten of eleven cases the replacement assertion is
already sitting in the test.

## Summary of recommended actions, in order

1. Uncomment `blacksmith-4vcpu-ubuntu-2404` on the backend job. Roughly halves the wall clock.
2. Stop collecting `session/test_migrate.py` twice.
3. Delete ten timing assertions across nine tests. About 1.2s of wall clock, and every known
   flake source in the suite. No test is lost and no claim is weakened.
4. Delete `TestBreakpointTimeout::test_event_wait_with_timeout_fires`.
5. Add `pytest-timeout` at 120s with `timeout_method = "thread"`, plus `timeout-minutes: 20`
   on the job.
6. Decide whether coverage belongs in the gate job or a parallel one. It costs 27% of wall and
   `sysmon` does not recover it.

Items 3 and 4 are eleven line-level edits in ten files. None changes production code.

---

# Missed-idiom census review 5632a6b9

PR #445, branch `fix/test-timeout-census` at `5632a6b9`, against `main` `96ef6f39`.
One question: did any coverage die?

**0 major, 0 minor. MERGE. No, nothing lost its proof.**

Every changed property is still proved, and four of the five sites are proved **more
strongly** than before: by deterministic state after a real barrier, rather than by sampling a
short window. Tree pristine, read only, `4143 passed in 46.27s`, and the three affected files
pass on their own in 5.03s.

The census gap is real and I accept it. My #442 audit counted `wait(timeout=)` and wall-clock
upper bounds. It did not count `asyncio.wait_for`, `asyncio.sleep` polling loops, or process
waits, which is why a 200ms `wait_for` budget survived to fail CI later.

## What actually changed, by site

I classified every removed assertion and every removed polling loop in the diff rather than
working from the summary. Fourteen `for _ in range(N)` loops were removed; **thirteen were
converted** to deadline-bounded `while loop.time() < deadline` loops with an identical body and
break condition, which changes a bounded iteration count into a bounded wall-clock budget and
changes no property. **One** was deleted outright. Three `pytest.raises(TimeoutError)` blocks and
one hand-rolled negative wait were replaced.

That leaves five distinct sites where a property's proof changed. Each below.

### 1 to 3. `pytest.raises(TimeoutError)` on a queue read, replaced by `assert queue.empty()`

`codex/test_transport_addon.test_addon_websocket_message_pauses_and_rewrites_on_release`,
`codex/test_transport_lifecycle.test_addon_websocket_end_skips_persisting_dropped_codex_exchange`,
`codex/test_transport_lifecycle.test_addon_websocket_end_persists_codex_exchange`.

Was: `with pytest.raises(TimeoutError): await asyncio.wait_for(queue.get(), timeout=0.01)`.
Now: `assert queue.empty()`.

Property: exactly one broadcast event was emitted, or in the dropped-exchange case, none.

**Preserved, and strengthened.** `broadcast.emit` is a plain synchronous `def` that ends in
`subscriber.queue.put_nowait(data)`. There is no scheduling gap between emitting and
enqueueing, so once the awaited production call (`await addon.websocket_end(flow)`,
`await addon.websocket_message(flow)`, `await task`) has returned, every event it will ever
emit is already in the queue. `queue.empty()` therefore observes the final state, where the old
form observed a 10ms sample of it. A second event that appeared at 11ms would have passed the
old assertion and fails the new one.

### 4. The duplicate SSE suppression assertion

`api/v1/test_session_routes`, the test that publishes one `SessionEventSignal` **twice**
(`hub.publish(signal)` on two consecutive lines) and proves the stream does not double emit.

Was:

    try:
        await asyncio.wait_for(anext(stream), timeout=0.2)
    except TimeoutError:
        pass
    else:
        raise AssertionError("duplicate SSE event emitted")

Now: insert a third event at `seq=2`, publish its signal, take the next frame and
`assert third["seq"] == 2`.

**Preserved, and this is the strongest of the five.** This is the correct replacement for a
negative stream assertion: rather than waiting to observe nothing, it puts a known next item in
the stream and proves that item is what arrives next. A duplicate of `seq=1` would necessarily
sit ahead of `seq=2` in stream order, so it fails the assertion deterministically no matter
when it would have been emitted. The old form could only catch a duplicate that arrived inside
200ms.

### 5. The deleted polling loop, and the negative case hiding inside it

`codex/test_transport_lifecycle.test_handshake_rejection_activity_follows_request_kind`.
Deleted:

    for _ in range(100):
        if writer.rows:
            break
        await asyncio.sleep(0.01)

This is the one the orchestrator was right to point at, because the test is parametrized on
`expected_rows` and one case expects **zero**:

    (json.dumps({"request_kind": "turn"}),   1),
    (json.dumps({"request_kind": "memory"}), 0),
    (None,                                   1),
    ("not-json",                             1),

crossed with every status in `CODEX_AUTH_REJECTED_STATUSES`. For the `memory` case the loop
could never break, so it ran all 100 iterations and cost a full second per status code, then
fell through to the same assertion it always would have reached. **The loop was never the proof
for that case**; it was a one second delay in front of one.

**Preserved, and strengthened, for both directions.** The line immediately after the deleted
loop is `await observer.aclose()`, which was already there. `LiveStatusObserver.aclose` is
documented as "Abort remaining taps, then drain all scheduled live writes" and implements
exactly that: it finishes every tap, marks itself closed, and `asyncio.gather`s every pending
future to completion. So by the time `assert len(writer.rows) == expected_rows` runs, every
scheduled write has finished.

For the three `expected_rows=1` cases that is a stronger guarantee than the poll, which would
have given up after one second. For the `expected_rows=0` case it is a genuine proof of absence
rather than a sampled one: nothing is pending, so nothing more can arrive.

This is the same shape as the two deletions I cleared in #442. The barrier that proves the
property was already on the next line, so the wait was redundant, not load bearing.

## Was anything waiting on something that should have arrived?

No. I checked this specifically, because it is the failure mode that hides a real defect.

The deleted loop breaks the moment `writer.rows` is non-empty, so it was waiting for arrival,
not asserting absence, and the case where nothing arrives is the one the parametrization
declares as `expected_rows=0` with a documented reason: a `memory` request kind must not
produce a live activity row. The three `expected_rows=1` cases still assert the row, its kind,
its run id, and the load-bearing identity `row.generation == persisted_exchange_id`, none of
which changed.

The three queue assertions are the same: each is preceded by a successful `queue.get()` that
proves the expected event *did* arrive, and the changed assertion only governs whether a
*second* one follows. Nothing that should have arrived is now unobserved.

## A note on the count

The brief describes six negative assertions eliminated and four sites converted. I found five
distinct source sites where a property's proof changed, listed above. The larger figure is
consistent with counting parametrized cases rather than sites: site 5 alone is four
parametrizations crossed with the rejected-status set, and one of those parametrizations is the
negative case. I am reporting sites because a property is proved per site, not per parameter,
and I would rather state what I verified than reconcile to a number.

If any changed property exists outside these five, it is not visible in
`git diff 96ef6f39...5632a6b9`: I swept every removed line matching `assert`,
`raises(TimeoutError)`, `for _ in range(`, `asyncio.sleep`, `.wait(`, `.empty()`, `is_alive`
and `poll()`, and classified each.

## Standard applied

The bar from #442 was that a wait may be deleted only when a deterministic assertion already
present proves the same property. All five clear it:

- Sites 1 to 3: the property is queue state, and the queue is filled synchronously by
  `broadcast.emit` before the awaited call returns.
- Site 4: the property is stream ordering, and it is now proved by the identity of the next
  frame rather than by its absence.
- Site 5: the property is the final row set, and `observer.aclose()` drains before it is read.

## Verdict

**MERGE.** No property lost its proof, no removed wait was the only thing standing between a
green suite and a real defect, and the four negative assertions that were genuinely asserting
absence are all now proved by state after a barrier rather than by a timing window. The one
deletion that could have been dangerous turned out to be redundant with a drain that already
followed it.
