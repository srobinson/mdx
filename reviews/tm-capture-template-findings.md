# Review: capture from the tm/capture runtime template

Worktree `.claude/worktrees/capture-home`, commit `838dd3bb` on `slice/capture-template-home`, against `main` (`02e2c241`).

**Blocker 0 | Major 4 | Minor 4 | Note 5**

Verification performed: ran `tests/integration/test_captured_proxy_post.py` (2 passed), ran `test_baseline_capture.py`, `test_baseline_evidence.py`, `test_baseline_harvest.py`, `test_runtime_registry.py`, `cli/test_runtime_home.py` (93 passed), ran the two import boundary tests (2 passed), exercised `runtime_template_content_digest` against seven mutation classes on the repo interpreter (3.14.5), and reproduced the mitmproxy startup death by promoting the addon's log record back to ERROR in a live proxy run.

---

## Major 1. The cell pins the template's recipe, not its bytes, and throws away the digest that would pin the bytes

`baseline_evidence:BaselineTemplateIdentity`, `baseline_capture:_template_identity`, `baseline_capture:_capture_probe`.

`generated_from` is not a digest of the template home. Verified in the generator at `~/.agent-runtimes/bin/agent_runtime_compiler/capabilities.py` (`_capabilities_payload`): it is `sha256(runtime.toml raw bytes || skill frontmatter)`. It moves when the *inputs* move, never when the *output* moves.

Failure scenario. Someone edits `~/.agent-runtimes/runtimes/tm-capture/settings.json` by hand, or agent-runtimes ships a generator change that renders a different `settings.json` from an unchanged `runtime.toml`. Both digests stay put. `_require_comparable_capture_plan` passes. The new bundle is compared against the old reference, and every wire difference the edit caused is attributed to the harness. That is precisely the misattribution this slice exists to prevent, and the cell asserts under oath that it did not happen.

`_capture_probe` already computes the exact digest that closes this (`runtime_template_content_digest`) and discards it after the assertion.

Smallest fix: hoist the digest to `harvest_controlled_baseline`, compute it once before the first probe, pass it into `_template_identity` as a fourth field `content_digest` on `BaselineTemplateIdentity`, and pass the same value down to all three `_capture_probe` calls instead of recomputing per probe. `_require_comparable_capture_plan` then refuses on it for free, since it compares `template_identity.model_dump()`. This also makes the invariant span the whole A/B/A rather than each probe in isolation.

## Major 2. The template assertion is skipped on every failure path

`baseline_capture:_capture_probe`.

```
turn = run_captured_turn(...)
assert_runtime_template_unchanged(runtime_template.template_home, digest=template_digest)
```

Failure scenario. A probe times out, or the provider refuses (`captured_turn:_wait_for_correlated_exchange` raises `CapturedTurnError` on an HTTP error status), or `read_captured_exchange` raises. The exception propagates and the assertion never runs. If that probe wrote into the template through a symlinked entry, the corruption survives. The *next* harvest computes its "before" digest from the already corrupted template, sees no change, and publishes a bundle whose control home silently differs from the reference's. A crashing or refused run is exactly when a harness is most likely to leave partial state behind, so the guard is absent in the case it most needs to cover. The docstring on `home_overlay:assert_runtime_template_unchanged` says "Fail closed"; today it fails open on error.

Smallest fix: `try: turn = run_captured_turn(...) finally: assert_runtime_template_unchanged(...)`. The `ValueError` raised from the `finally` chains the original exception as `__context__`, so no diagnosis is lost.

Two halves of the hypothesis are refuted, and worth recording:

- **No live-writer race on the success path.** `captured_turn:run_captured_turn` terminates the supervisor and closes the lease in its own `finally` before returning. `supervisor/core.py:ProcessSupervisor.terminate_all` SIGTERMs every live child, waits up to a 5s grace, escalates to SIGKILL, and reaps. The child is dead before the digest is taken. The lease close also `shutil.rmtree`s the overlay (`captured/context.py:_prepare_home_and_grant`), and `rmtree` unlinks symlinks rather than following them, so the teardown cannot reach the template. The assertion sitting after the lease close is correct, not incidental.
- **It runs on every probe.** `_capture_probe` computes the "before" digest per call, so all three probes are covered, not just the first. `test_harvest_refuses_a_probe_that_wrote_into_its_own_template` pins the abort on probe 1 via `assert len(prepared) == 1`.

## Major 3. One of four identical best-effort startup handlers was downgraded

`addon_runtime:load_capture_runtime`, `addon_runtime:load_shared_capture_runtime`, `drift_capture:start_drift_capture`, `drift_capture:build_drift_emitter`.

The builder's chain is real, and I proved it rather than taking it on faith. I ran `tests/integration/test_captured_proxy_post.py` with a `sitecustomize` shim on `PYTHONPATH` that attaches a filter to the `transport_matters.addon_runtime` logger promoting its records back to `ERROR`. The shim log shows the mitmdump subprocess inherits `PYTEST_CURRENT_TEST`, that `session capture failed to start` is genuinely reached (via `session/pool:create_async_pool` calling `guard_pytest_session_store_url`, since `config:resolve_session_store_url` yields the channel database name, not a `TEST_DB_PREFIX` name), and that with the record at ERROR the test fails with `http.client.RemoteDisconnected`. `mitmproxy/addons/errorcheck.py:ErrorCheck.shutdown_if_errored` calls `sys.exit(1)` if any record at ERROR reached the root logger during startup.

So the change is right and it is not a test accommodation. The comment above the `try` already reads "Best-effort startup failure must never stop the proxy (§7.1)", and `logger.exception` was quietly breaking that promise in production: a session store that is briefly unreachable when a captured run starts would kill the whole proxy instead of degrading to no transcript capture. `exc_info=True` keeps the full traceback, so nothing is hidden.

The problem is that it fixes one site of four. `ErrorCheck` watches the root logger, so *any* ERROR from *any* module during addon startup kills mitmdump.

Failure scenario. `drift_capture:start_drift_capture` is called from `addon_runtime:_start_session_capture`, i.e. squarely on the addon startup path, and it swallows its own exception and returns `None`, so the outer `logger.warning` never sees it. `local_executor_id()` fails, or `ExecutorBlockStore` construction fails, and `build_drift_emitter` logs at ERROR. The docstring promises "Best-effort: any construction failure ... disables drift evidence with a log and returns None, leaving the caller's live path untouched". Instead mitmdump exits during startup and the capture run dies. Same shape, same contract, unfixed.

Smallest fix: give the three siblings the same treatment. Better, since this is now the fourth site of one rule: one helper, `log_best_effort_startup_failure(logger, message, *args)`, so the rule lives in one place and the next handler cannot get it wrong.

## Major 4. `runtime_template_content_digest` re-implements a helper that already existed

`home_overlay:runtime_template_content_digest`, `home_overlay:_template_entry_digest`, `cli/test_runtime_home.py:_tree_fingerprint`.

`_tree_fingerprint` is on `main`, predates this diff, and is a semantic twin: same `sorted(root.rglob("*"))`, same `relative_to(root).as_posix()` keys, same symlink / dir / file branching, same `readlink` on symlinks and same full byte read on files. Its two callers, `test_codex_template_tree_is_byte_identical_after_full_launch_prep` and `test_claude_template_tree_is_byte_identical_after_full_launch_prep`, are the exact byte-identity property the new production helper now asserts.

The diff leaves both implementations in the tree. Under the repo's zero-tolerance DRY rule this is not complete.

Smallest fix: delete `_tree_fingerprint` and have those two tests call `runtime_template_content_digest`. It also gives the new production helper two more callers exercising it, at no cost.

---

## Minor 5. A fired guard cannot say what changed

`home_overlay:assert_runtime_template_unchanged`.

The function takes an opaque hex digest, so all it can say is `runtime template <path> changed during the run`. The intended operator response is to work out which entry moved and decide whether the name belongs in the harness's `_*_TEMPLATE_LOCAL_WRITABLE_NAMES` set. Today they have to bisect the template by hand, on a home that a failed harvest may have already mutated further.

Smallest fix: factor `_template_entry_digests(home) -> dict[str, str]` (the digest becomes `canonical_digest(sorted(...))` over it), have `assert_runtime_template_unchanged` take the mapping, and name the symmetric difference in the error.

## Minor 6. Two write classes are invisible to the digest, and five are not

`home_overlay:runtime_template_content_digest`.

Measured on the repo interpreter (3.14.5) against a template containing a real subdirectory, a regular file, and a symlink to an outside directory:

| mutation | detected |
| --- | --- |
| new file in a real template subdirectory | yes |
| modified file content | yes |
| retargeted symlink | yes |
| deleted entry | yes |
| entry moved between directories | yes |
| **new file inside a symlinked template subdirectory** | **no** |
| **permission-only change** | **no** |

So the bulk of hypothesis 1 is refuted: the digest is not name-only, it does read every byte of every regular file, and it does not follow symlinks out of the template and digest the wrong tree (`_template_entry_digest` tests `is_symlink()` before `is_dir()`, and `Path.rglob` does not descend into symlinked directories, which is what keeps the traversal inside the template).

The two gaps are unreachable today. `~/.agent-runtimes/runtimes/tm-capture` contains only regular files (`.claude.json`, `capabilities.json`, `config.toml`, `runtime.toml`, `settings.json`) and `tm-capture-grok` only three of those. No directory, no symlink.

Smallest fix, if you want them closed: fold `stat().st_mode & 0o777` into `_template_entry_digest`'s file and dir branches, and either refuse a symlink inside the template outright or digest its resolved subtree. I would take the mode and leave the symlink case to the refusal, since a symlinked directory inside a control home is itself a smell.

## Minor 7. The schema version literal is written in five places, and the pointer is not typed to it

`baseline_evidence:BaselineBundle.artifact_schema_version`, `baseline_store:_CurrentBundlePointer`, `baseline_store:read_current_baseline`, `baseline_store:read_baseline_bundle`, `baseline_store:_write_current`, `baseline_capture:harvest_controlled_baseline`.

The 3 to 4 bump required editing five literals. `_CurrentBundlePointer.artifact_schema_version` is `int`, so the pointer model itself accepts any version on write and the only thing holding the line is the `!= 4` comparison in `read_current_baseline`.

Smallest fix: one module constant in `baseline_evidence`, imported by `baseline_store` and `baseline_capture` for the three comparisons and the two writes; keep `Literal[4]` on `BaselineBundle` and give `_CurrentBundlePointer` the same `Literal[4]`, which makes the pointer's read-side comparison redundant and deletable.

The rest of hypothesis 3 is refuted. `grep artifact_schema_version` over `api/src` and `api/tests` returns 4 everywhere except the two negative tests that deliberately write 3. `bare_home`, `_source_home` and `.baseline-sources` are gone from the entire repo with no orphaned callers, imports or tests. No baseline bundles exist under `~/.transport-matters` in any channel (the only `baselines` directory on disk is in `~/.Trash`), so the bump is free as claimed. The two negative tests are more meaningful than they were, since 3 is now the real predecessor rather than a version two bumps back.

## Minor 8. The capture template map has no bad-key path and no existence check

`runtime_registry:resolve_capture_baseline_template`, `runtime_registry:_CAPTURE_BASELINE_TEMPLATE`, `baseline_harvest:main`.

Hypothesis 7's first half is refuted: `test_capture_baseline_template_map_covers_every_launch_eligible_harness` asserts set equality in both directions, so it cannot pass with a harness missing from the map. It is total.

What it does not cover: the mapped ids are strings that nothing checks against the catalog, and `resolve_capture_baseline_template` indexes the mapping directly. A harness reaching it outside `launch_eligible_harness_ids()` raises `KeyError`, and `baseline_harvest:main` wraps that call in `except ValueError`, so the operator gets a traceback instead of the intended exit 2.

Smallest fix: `_CAPTURE_BASELINE_TEMPLATE.get(harness)` with an explicit `ValueError` naming the harness.

Hermeticity is confirmed, refuting the second half. `test_baseline_harvest:_install_command_fakes` monkeypatches `resolve_capture_baseline_template`; `test_baseline_capture` injects a `RuntimeTemplateRef` built under `tmp_path`; `test_runtime_registry` passes `env={"HOME": str(tmp_path)}`. No test in the suite reads the real `~/.agent-runtimes`. Resolving in the CLI rather than the harvest is what buys that, and it holds.

---

## Note 9. The lifted test's template assertion is nearly inert, but everything else in it is honest

`api/tests/integration/test_captured_proxy_post.py`.

No harness process runs. `client_bin=sys.executable` is only ever placed into a spawn spec, never spawned, so the only writer that can touch the template during the test is overlay materialization itself. `test_captured_template_proxy_records_real_post_and_leaves_the_template_alone`'s closing assertion is therefore cheap insurance against a materialization regression, not proof that the write-through channel is guarded. `test_harvest_refuses_a_probe_that_wrote_into_its_own_template` is the test that covers that, and it does.

The rest checks out. Real mitmdump via the production `default_claude_run_dependencies().resolve_mitmdump` with no stub. A real socket POST over TCP to the allocated proxy port. `assert len(recorded) == 1` plus byte-equal JSON, so a silent no-capture fails rather than passes. `_assert_launch_is_on_a_seeded_overlay` pins the overlay to `storage/runtime-home/claude` and reads `hasTrustDialogAccepted` back out of the seeded `.claude.json`. No sleeps, no retries, no broad excepts, `urlopen(timeout=10)` bounded, upstream torn down in `finally`. `testpaths = ["src", "tests"]` so `just test` runs it. It passes (2 passed in 5.12s), and per Major 3 it is the regression test for the `addon_runtime` change: promote that log record to ERROR and it fails.

## Note 10. Judging the decision not to add `skills` and `.sandbox_migration` to the codex writable set

Failing the harvest closed is the right call, and the guard does fire: I confirmed a write landing in a real template subdirectory changes the digest.

The scenario is moot today for a reason worth stating. `_symlink_template_content_entries` only symlinks entries that *exist* in the template. `tm/capture` contains no directories at all, so no `skills` or `.sandbox_migration` symlink is ever created and codex creates both fresh inside its own overlay. The decision costs nothing now and fails loudly the day agent-runtimes ships a directory in the template.

That last part is conditional on Major 2. A codex run that dies mid-turn is exactly how such a write would slip past unnoticed.

For the same reason, the grok concern in the brief does not bite: `tm/capture-grok` carries only `capabilities.json`, `config.toml` and `runtime.toml`, so `skills/`, `sessions/`, `projects/`, `agent_id` and `trusted_folders.toml` are all created inside the overlay, and `_GROK_TEMPLATE_LOCAL_WRITABLE_NAMES` never comes into it.

## Note 11. `assert_runtime_template_unchanged`'s docstring describes a different blind spot than the one the code has

`home_overlay:assert_runtime_template_unchanged`, `home_overlay:runtime_template_content_digest`.

"Today's templates happen to carry no such directory" is true, but the paragraph is about directories the *overlay* symlinks, whereas the traversal's actual blind spot is a symlink *inside* the template (Minor 6). Two different things, and the docstring reads as covering the second while describing the first. `"""Digest every template entry, resolving none of them."""` restates the mechanism; the load-bearing why is that resolving would carry the digest outside the template and measure a tree the capture does not control.

## Note 12. The Claude trust comment states a reason that is not the reason

`cli/claude_home.py:ClaudeSeeder.seed`.

"A runtime template carries no `projects` trust key: template validation forbids account fields". `home_overlay:_validate_template_secret_free` forbids `oauthAccount` and `userID`. It says nothing about `projects`, so nothing stops a template from shipping a trust key. The real, and stronger, why is that `_ensure_claude_trust` keys trust by absolute cwd and the capture cwd is per-run, so no shared static template can carry it.

Secondary: the comment explains a template-specific fact at a call site shared by native, manual and template launches, where the trust key usually arrives from the source `.claude.json`.

The second sentence is good and should stay: the failure mode (the launch parks on the trust dialog until its correlation timeout expires) is exactly the non-obvious consequence a reader needs.

## Note 13. Probe independence is no longer asserted

`test_baseline_capture:test_harvest_runs_fresh_correlated_aba_and_persists_bundle`.

The old assertions `len({request.home_dir ...}) == 3` and `all(request.home_dir.is_dir() ...)` were the only thing pinning that the three A/B/A probes launch from three independent homes. They are replaced by `all(request.home_dir is None ...)` and `{request.runtime_template.agent_id ...} == {"tm/capture"}`, which pin the opposite: one shared template.

The property still holds. `storage_dir=None` with `workspace_root` set routes through `resolve_run_storage=lambda run_id: run_root_for_workspace(...)`, giving each run its own storage root and therefore its own `runtime-home/<harness>` overlay, which the `ExitStack` rmtrees at lease close. But `_install_capture_fakes` replaces `prepare_captured_run` wholesale, so that seam is not observable from this test file and the coverage lives elsewhere (`captured/test_run_web_separation.py`). Worth knowing that the A/B/A independence guarantee moved out of the baseline tests and nothing in them notices if it breaks.

---

## Checked and clean

- `_require_comparable_capture_plan` still refuses every coordinate it refused before (harness, provider, launch_model, request_shape, no_system_prompt, bypass_permissions) and now refuses a moved template generation. The nested `model_dump()` comparison works because `BaselineCell.model_dump(include=...)` recurses into the nested model. The expected-plan definition is not duplicated: `_template_identity` is called once in `harvest_controlled_baseline` and the same value feeds both the refusal and the persisted cell.
- Two bundles from different templates can never compare EXACT. `compare_content` and the structure comparison are reached only from inside `harvest_controlled_baseline`, downstream of `_require_comparable_capture_plan`, and `read_current_baseline` is already keyed by harness, provider and model. Subject to Major 1, which is about what "different templates" means.
- `_template_identity`'s strictness is right and its stated rationale holds: `runtime_registry:_list_runtime_templates_in_root` skips an unreadable template rather than failing the catalog, so a bundle that cannot name its generation must be refused at capture time. Both real capture templates publish both digests (`generated_from` and `launch_requirements_digest` present in each `capabilities.json`), so the strictness does not brick the harvest.
- `RuntimeTemplateCapabilities.launch_requirements_digest` as `str | None = None` on an extra-ignoring model is the right shape given that agent-runtimes may add keys without bumping `schema_version`.
- The `AUTOPILOT-WIRE-PLAN.md` `ENABLE_TOOL_SEARCH` paragraph is accurate. `~/.agent-runtimes/runtimes/tm-capture/runtime.toml` does declare `env = { ENABLE_TOOL_SEARCH = "auto:100" }` under `[settings.claude]`, and the generator does seed the `generated_from` digest with `runtime.toml`'s raw bytes before anything else. Not adding it as a cell coordinate is correct, and the doc's reasoning for why is correct. The doc's revised "what TM owes" paragraph accurately narrows the outstanding work to the requirement set, `neutral_cwd`, and the grok seed path.
- `provenance` gaining two keys does not break the launch metadata surface. `runtime_templates:RuntimeTemplateProvenance.as_launch_field` merges the whole mapping into the session's `template_provenance`, which is typed `Mapping[str, str]` and asserted only against hand-built refs in `cli/test_runtime_home.py` and `cli/test_runtime_home_launch_fields.py`. Both import boundary tests pass.
- The 93 unit tests across the five touched test modules pass, as does the new integration file.
