# Review: guard cull on the tm/capture slice

Worktree `.claude/worktrees/capture-home`, commit `d7740e34` on `slice/capture-template-home`, on top of `000d67ff`, against `main` (`02e2c241`). Prior review: `tm-capture-template-findings.md`.

**Blocker 0 | Major 1 | Minor 1 | Note 4**

Verification performed: read the full `d7740e34` diff and the cumulative diff vs `02e2c241`; compared the three `_*_TEMPLATE_LOCAL_WRITABLE_NAMES` sets against `main`'s `home_overlay.py` by parsing both files on the repo interpreter (not by eye); grepped `api/` and `docs/` for every removed symbol, `write through`, `backstop`, `writes_into_template`, `unchanged afterwards`; ran `ruff check` on the five touched Python modules (clean); reproduced the plan document's codex claim first hand (`codex-cli 0.148.0`, `CODEX_HOME` pointed at an empty scratch directory, `codex debug prompt-input` exit 0, home afterwards contains `.sandbox_migration`, `installation_id`, `skills/.system`, `tmp/arg0`); inventoried `~/.agent-runtimes/runtimes` for symlinks and for directories under the two control templates (zero of each). Did not run the gates, did not edit any file.

---

## The five questions, answered

**1. Load-bearing removal.** Nothing load-bearing went. `home_overlay:runtime_template_entry_digests`, `home_overlay:runtime_template_content_digest` and `home_overlay:_template_entry_digest` all survive. Prior Major 1 holds: `baseline_evidence:BaselineTemplateIdentity.content_digest` is still populated by `baseline_capture:_template_identity`, still part of `_require_comparable_capture_plan`'s expected plan, and `test_baseline_capture:test_harvest_refuses_a_reference_taken_from_an_edited_template` still pins it (first harvest passes, hand edit to `settings.json`, second harvest refuses with `capture plan`, no fourth probe launched). Prior Major 4 holds: `cli/test_runtime_home:_tree_fingerprint` stays deleted and its two tests call `runtime_template_entry_digests`. Whether the two-function split still earns its place is Note 4 below: yes.

**2. `try/finally`.** Gone with the assertion, and correctly so. `_capture_probe` is back to a bare `turn = run_captured_turn(...)`. There is no orphaned `try`. The supervisor and lease teardown that the prior review relied on live inside `captured_turn:run_captured_turn`'s own `finally`, so the probe needs none of its own. The test that pinned the error path, `test_harvest_asserts_the_template_even_when_the_turn_fails`, is deleted along with the `writes_into_template` fake parameter.

**3. Writable-name reversion.** Exact. Parsed `_CLAUDE_`, `_CODEX_`, `_GROK_TEMPLATE_LOCAL_WRITABLE_NAMES` from `main`'s `home_overlay.py` and from the worktree's `home_constants.py`: all three sets are equal (11, 33, 9 names). The cumulative `git diff 02e2c241 -- cli/home_constants.py` is pure addition, and no line of `main`'s `home_constants.py` is missing, so nothing that predates the slice went with the cull. The only change vs `main` is the move of the three sets from `home_overlay` to `home_constants`, which is placement, not policy. `.sandbox_migration` is out; judged correctly, see Note 3 on why every one of these names is inert under a clean template.

**4. Dead weight.** None found. `ruff` is clean on the touched modules. `home_overlay`'s `Mapping` import is still used by `runtime_template_content_digest` and four `env:` signatures; `hashlib` and `canonical_digest` by the digest helpers. `cli/home_seed` re-exports only the two digest functions, both consumed by `baseline_capture` and tests. `_template_policy_local_names` is inlined back into its one caller. No test pins deleted behaviour. No docstring or comment describes either assertion. `docs/plans/AUTOPILOT-WIRE-PLAN.md` no longer says `refuses such a template` or `asserts the template is unchanged`; the remaining `assert` hits in that file are about `neutral_cwd`, requirement sets and config byte equality, all unrelated and still true. One docstring still frames a refusal, which is Major 1 / Minor 2.

**5. Plan document.** Verified, not inverted. The builder kept the observation, named the mechanism (`whatever CODEX_HOME it is given`), added the version, and stated the ownership line. I reproduced it independently and it is exactly right: codex 0.148.0 against an empty `CODEX_HOME` writes `.sandbox_migration`, `installation_id`, `skills/.system` and `tmp/`. The sentence `the dirty templates seen earlier came from harnesses pointed directly at ~/.agent-runtimes outside TM` matches both the owner's ruling and the provenance of the original claim (agent-runtimes `37ad2c3`, `audit.py`: `with CODEX_HOME pointed at a template`).

---

## Major 1. One guard-shaped refusal survived the cull

`home_overlay:runtime_template_entry_digests`, `cli/test_home_seed:test_template_entry_digests_refuse_a_symlink_inside_the_template`.

The traversal still raises `ValueError("runtime template ... contains symlink ...; a template this is measured against must be self contained")` on any symlink anywhere in the template. That sentence is TM telling agent-runtimes what shape a template may take, which is the exact thing the ruling withdrew. It reaches the harvest through `baseline_capture:_template_identity`, before any probe launches.

Failure scenario. agent-runtimes materializes a control template entry as a symlink (they ran a symlink farm for `skills/` until `c1ecbe4`, thirty hours ago, and nothing in their contract says they may not go back). `tm harvest` refuses with `must be self contained`, and agent-runtimes is once again asked to carry a test to keep our assertion satisfiable, the pattern `b51edd4` documents for the guard this commit just removed. The orchestrator's pending message to agent-runtimes would also have to say `no directory constraint, but no symlink either`, which is not the clean `TM neither asserts nor polices it` the plan document now promises.

It is unreachable today: zero symlinks exist under `~/.agent-runtimes/runtimes`, and the two control templates are files only. That bounds the severity at Major rather than Blocker, not at Minor, because the thing it contradicts is the premise of this commit.

Smallest fix: record the link instead of refusing it, which is what the deleted `_tree_fingerprint` did. In `_template_entry_digest` (or inline in the loop), `if path.is_symlink(): return f"symlink:{path.readlink()}"`, drop the raise, rewrite the docstring to say the digest describes the template's own entries and never follows a link out of it, and turn the test into `test_template_entry_digests_notice_a_retargeted_symlink` (create link, digest, repoint it, assert the digest moved). The content digest then honestly says which bytes and links the template carried, with no opinion on whether links are allowed.

## Minor 2. The surviving docstring still argues for the refusal

`home_overlay:runtime_template_entry_digests`.

`Resolving would carry the digest outside the template and measure a tree the caller does not control, so a symlink is refused rather than followed` is the justification for a guard. If Major 1 is taken this rewrites itself. If it is not, the docstring should at least say why refusal rather than readlink was chosen, because today's reader meets a refusal with no stated reason why the `_tree_fingerprint` semantics were rejected. Same edit for the comment in `test_template_entry_digests_refuse_a_symlink_inside_the_template`, which the commit reworded but kept.

## Note 3. Why reverting the writable names is safe, and inert

`home_overlay:_materialize_local_writable_entries`, `home_overlay:_symlink_template_content_entries`.

The builder's commit message says `under a clean template every one of them is inert`. Confirmed from the code: `_materialize_local_writable_entries` only acts when `source_home_dir / name` is a directory in the template, and `_symlink_template_content_entries` only consults the set to skip an entry that exists in the template. A name that the template does not carry has no effect in either direction. Both control templates carry only regular files. So the sixteen grok names and seven codex names were never reached, and removing them changes nothing at runtime. Whether `.sandbox_migration` belongs there is therefore moot until a template ships such an entry, and the handoff's instruction to judge it on its merits resolves to `no entry, no name`.

## Note 4. The digest helper still earns its two-function shape

`home_overlay:runtime_template_entry_digests`, `home_overlay:runtime_template_content_digest`.

After the cull, production calls `runtime_template_content_digest(runtime_template_entry_digests(home))` exactly once, in `_template_identity`. The mapping-returning half could look like a leftover from the assertion that needed per-entry names. It is not: six test sites (`cli/test_runtime_home` twice before and after, `tests/integration/test_captured_proxy_post`, two in `cli/test_home_seed`, and `test_baseline_capture:_expected_template_identity`) compare the mapping, and a dict inequality prints which entry moved while a hex digest prints two opaque strings. That is Major 4's dedupe paying for itself. Keep both.

## Note 5. What the remaining template-identity tests now prove

`cli/test_runtime_home:test_codex_template_tree_is_byte_identical_after_full_launch_prep`, `cli/test_runtime_home:test_claude_template_tree_is_byte_identical_after_full_launch_prep`, `tests/integration/test_captured_proxy_post:test_captured_template_proxy_records_real_post_and_leaves_the_template_alone`.

These still assert the template is unchanged after TM's own overlay preparation. That is not policing agent-runtimes; it is pinning that TM's materialization writes only into the overlay. They are correctly kept. The prior review's Note 9 observation stands: no harness process runs in the integration test, so the assertion covers materialization, not a child's behaviour, which under the ruling is exactly the scope TM owns.

## Note 6. Trust has a visible consequence in the cell

`baseline_capture:_template_identity`, `baseline_capture:harvest_controlled_baseline`.

`content_digest` is now taken once, before the first probe, and never rechecked. Under the contract that is the right amount of measurement: the cell records the bytes the harvest started from, and agent-runtimes guarantees nothing changes them. Stating it so nobody reads the single pre-probe digest as a half-finished guard.

---

## Checked and clean

- Commit is a plain commit on top of `000d67ff`, no amend, no rebase, conventional title, no em dashes.
- `home_overlay.py` 547 lines, `baseline_capture.py` 361, `test_baseline_capture.py` 746 (was 849; already over 700 on `main` at this slice's parent and shrank here, so the cull did not add to an over-limit file).
- `_template_identity` docstring and `BaselineTemplateIdentity` docstring are still accurate after the digest moved inside.
- `test_baseline_capture:_install_capture_fakes` still uses `request.runtime_template.template_home` for `CLAUDE_CONFIG_DIR`, so dropping `writes_into_template` left no dead parameter path.
- agent-runtimes side, for the orchestrator's outstanding message: `b51edd4` (`AGENTS.md` paragraph `Control templates must stay directory free` and `tests/test_skills.py:test_a_bare_control_home_materializes_no_directory`) now documents a constraint TM no longer imposes. If Major 1 is taken the message can be unconditional; if not it must carry the symlink exception.

---

# Addendum: commit `ac76b671` (second commit, reviewed as a pair with `d7740e34`)

**Blocker 0 | Major 0 | Minor 0 | Note 1**

Verification performed: read the full `ac76b671` diff; `ruff check` on `home_overlay.py` and `test_home_seed.py` (clean); ran `test_template_entry_digests_measure_a_symlink_by_its_link_text`, `test_template_entry_digests_notice_a_permission_only_change` and `test_harvest_refuses_a_reference_taken_from_an_edited_template` on the repo interpreter (3 passed); counted my own scratch `CODEX_HOME` from the earlier repro (85 entries under `skills/.system` plus `.codex-system-skills.marker`, six skills: `imagegen`, `openai-docs`, `plugin-creator`, `review-agent`, `skill-creator`, `skill-installer`, zero symlinks).

**Major 1 resolved.** `home_overlay:runtime_template_entry_digests` no longer raises on a symlink. `_template_entry_digest` tests `is_symlink()` first and returns `symlink:<readlink>`, which is `_tree_fingerprint`'s semantics and also what keeps a dangling link from reaching `stat()`. The comprehension stays inside the template because `Path.rglob` does not descend into a symlinked directory on the repo interpreter. `ValueError` over template shape is gone from the harvest path entirely; `grep -n 'refus\|self contained' home_overlay.py` returns nothing.

**Minor 2 resolved.** The docstring now states the never-follow mechanism and explicitly disclaims any assertion about template contents. The test comment matches.

**Test is a real positive test.** `test_template_entry_digests_measure_a_symlink_by_its_link_text` asserts both halves: a write behind the link leaves the digest unmoved, a retarget moves it. The retarget points at a nonexistent directory, so it also exercises the dangling-link branch.

**Plan document.** The expanded `skills/.system` sentence matches my independent repro byte for byte on skill names and marker, and `roughly ninety` is fair for 85 plus the marker. Still verified, not asserted.

## Note 7. The orchestrator's message to agent-runtimes can now be unconditional

With the symlink refusal gone, TM imposes no shape constraint on a template: no directory rule, no symlink rule. `b51edd4`'s `Control templates must stay directory free` paragraph and `test_a_bare_control_home_materializes_no_directory` can be retired on their side without exception.

## Checked and clean

- Plain commit on top of `d7740e34`, conventional title, no em dashes.
- `home_overlay.py` is 541 lines.
- No other caller of `runtime_template_entry_digests` relied on the raise: `cli/test_runtime_home` and `tests/integration/test_captured_proxy_post` compare mappings and neither builds a template with a symlink.

---

# Addendum 2: commit `baa3b2ce` (third commit, CI fix for `tests/integration/test_captured_proxy_post.py`)

**Blocker 0 | Major 0 | Minor 0 | Note 2**

Verification performed: read the full diff; read the failing CI log for run `32390859971` (the run for `ac76b671`); confirmed the fixture's home; ran the two integration tests on the repo interpreter at `baa3b2ce` (2 passed in 5.7s) and `ruff check` on the file (clean); grepped every `sys.platform` branch in `api/src`; checked `origin/slice/capture-template-home`.

**Diagnosis confirmed.** CI failed exactly one test, `test_captured_template_proxy_records_real_post_and_leaves_the_template_alone`, with `CredentialBrokerError: Claude credential unavailable (.../home/.claude/.credentials.json is not a file)`. `credential_source:resolve_harness_credential_source` takes the keychain broker only when `sys.platform == "darwin"`, and everywhere else the native file under the test's overridden `HOME`, which nothing seeded. The non-template test passed on Linux, so the native-home launch path never needed the file; only the template overlay's credential link (`home_overlay:_symlink_file_if_exists`, `symlink_to(source.resolve())`) does.

**Fix is the existing idiom, correctly applied.** `cli/test_home_seed_credentials` pins `sys.platform` and seeds through `credential_source_home`; the fixture lives in the root `api/conftest.py`, so it is visible to `tests/integration` (I checked, since a fixture in `cli/conftest.py` would not have been). The new assertion that the overlay's `.credentials.json` resolves to the seeded file is a real positive check the template case previously lacked. No skip, no platform guard, both platforms now take one path.

**Blast radius of patching `sys.platform` in a test that spawns a real mitmdump is bounded.** The five branches in `api/src` are `credential_source` (the intended one), `claude_fleet_auth` (only reached via the keychain route, now bypassed), `cli/_helpers` (an import-time skip marker), `self_reap` (takes platform as a parameter) and `desktop_runtime` (`win32`, not on this path). Nothing on the proxy spawn or port allocation path reads it, which the local pass on macOS under the linux pin also shows.

## Note 8. `baa3b2ce` is not on origin yet

`origin/slice/capture-template-home` is still at `ac76b671`, so the CI proof the builder cites has not run. Whoever owns the push for this branch should push before merge; no review action beyond that.

## Note 9. The commit message slightly overstates what macOS did

`_never_mint_from_the_real_keychain` in `api/conftest.py` is autouse, so macOS was green through the fake broker seam, not the real keychain. The real keychain was never in the test; the commit's value is the platform-neutral single path, not keeping the keychain out. Wording only, nothing to change.

## Checked and clean

- Plain commit on top of `ac76b671`, conventional title, no em dashes.
- Shared helper `_record_one_post` seeds the credential for both tests; the non-template test does not need it but pays nothing for it, and the alternative (seed only in the template branch) would split the helper's setup for no gain.
