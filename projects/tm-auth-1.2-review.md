# Review: PR#352 `ml/credential-source-dispatch` (head 99bd449b, baseline main 101287bf)

Adversarial pass against NOW.md 1.1/1.2. Tree verified pristine (`git status --porcelain`
empty) before and after; no writes to the repo by me or any subagent.

**Verdict: 1 Blocker, 2 Major, 6 Minor.** The branch does not build.

Local gates on darwin are green and prove nothing about the deliverable:
`just test-affected main` 3568 passed, `just test-js` all green, `just check` (ruff + mypy on
716 files + every tsc project) clean.

---

## Blocker

### B1. CI is red on this branch. 6 failed, 1 error, 3545 passed.

`gh run list --branch ml/credential-source-dispatch` → run **30587179739**, `completed
failure`, started 22:27:09Z, one minute before the review brief was sent. The `backend · test`
job on `blacksmith-4vcpu-ubuntu-2404` ends:

```
============= 6 failed, 3545 passed, 16 skipped, 1 error in 52.83s =============
```

Every failure is this diff's dispatch. NOW.md 1.2 names the exact reason this is invisible
locally: *"Every backend CI job runs on `blacksmith-4vcpu-ubuntu-2404`, so the whole Python
suite already runs on Linux."* The slice that exists because Linux was never exercised was
merged-ready against a darwin-only gate.

Three distinct causes.

**(a) The broker-identity invariant is void on Linux, and the two tests that assert it are not
`@darwin_only`.**

- `cli/test_home_seed_credentials.py::test_managed_claude_client_rejects_non_broker_credential`
  — `Failed: DID NOT RAISE CredentialBrokerError`
- `cli/test_home_seed_credentials.py::test_reused_claude_home_cannot_launch_with_native_credential`
  — `assert 0 == 1`

`home_overlay.py::assert_claude_runtime_credential_identity` now returns early for any
non-keychain source after checking only that `.credentials.json` `is_file()`. On Linux a
runtime home therefore launches with *any* credential document, including the operator's
native one.

This is more than a stale test. `test_reused_claude_home_cannot_launch_with_native_credential`
encodes a security property: a per-run overlay must not hand the child the operator's
refresh-token-bearing credential. On darwin the broker exists to keep that true. On Linux the
branch makes it false by design, and NOW.md 1.1 does prescribe exactly that (*"Claude,
Linux / Windows → `~/.claude/.credentials.json` → link it"*). So the behavior is defensible,
but the branch retires a stated guarantee **silently**: no `@darwin_only` re-scope, no Linux
counterpart test, no note in the commit. Ratify it explicitly (a Linux test asserting the
native link *is* accepted, and the darwin test marked for the platform that still owns the
invariant) rather than leaving a red assertion as the only record.

**(b) On Linux, Claude now fails closed where the fixture has no native credential.** Four
tests, all aborting inside `_resolve_overlay_credential` (`home_overlay.py:438`):

- `cli/test_start_storage.py::test_start_home_dir_sets_claude_config_dir_and_manifest` —
  `error: claude_credential_unavailable: Claude credential unavailable
  (/parent/claude/.credentials.json is not a file); launch aborted.`
- `api/v1/test_capture_rpc_routes.py::test_continuation_lineage_survives_the_template_merge`
- `captured/test_run_web_separation.py::test_prepare_captured_run_native_home_does_not_publish_agent_home_dir`
- `captured/test_run_web_separation.py::test_prepare_captured_run_claude_manual_home_descriptor_matches_launch_home`

Fail-closed is the intent, so these are fixtures owing a credential file. Worth stating in the
PR body regardless: on Linux, `--home-dir X` for Claude now aborts the launch unless the
resolved auth source carries `.credentials.json`. That is a user-visible behavior change on a
platform that previously did not reach this code at all.

**(c) The predicate crashes instead of reporting, on its own default arguments.**

```
ERROR api/v1/test_capture_rpc_routes.py::test_capture_rpc_translates_claude_credential_failure
  - ValueError: claude native credential checks require an auth source home
```

`home_overlay.py::claude_fleet_credential_error` defaults `harness=HARNESS_NAME_CLAUDE` and
`auth_source_home_dir=None`. On non-darwin that combination is unrepresentable and the function
raises `ValueError` — from inside the code path whose job is to *report* credential failures.
Two live callers use exactly those defaults: `_mint_claude_credential` at `home_overlay.py:447`
and `:453`. They are unreachable today only because `_uses_keychain_credential_source` gates
the mint, so the trap is one refactor from firing in production; the fixture already fires it.

Make the invalid state unrepresentable rather than validated at the top of the body: either
`auth_source_home_dir` becomes required, or the keychain branch is a separate function and this
one never takes a harness whose source it cannot check.

---

## Major

### M1. macOS Claude is not byte-identical: +2 keychain reads per launch, +1 per bind retry.

`credential_broker.py::SecurityOwnerCredentialStore.read` shells
`/usr/bin/security find-generic-password -a … -w -s …` (`credential_broker.py:278-289`) — the
prompt-capable form, against the login keychain.

Instrumented one darwin Claude overlay launch on this head, counting `read()` calls with the
broker and store stubbed (script in scratchpad, nothing written to the repo):

```
after overlay materialization:   owner_reads=1 mints=1
after ManagedClient construction: owner_reads=2 mints=1
```

`main` performs **zero** owner reads at either site: `_link_overlay_credential_files` had no
predicate call, and `assert_claude_runtime_credential_identity` was `resolve` + `samefile`
only. Both new reads are redundant work re-establishing a property the caller just settled:

- `home_overlay.py:416` (`_link_overlay_credential_files`) re-derives the same predicate
  `_resolve_overlay_credential` evaluated moments earlier at `:433`, after the mint has already
  succeeded.
- `home_overlay.py:460` (`assert_claude_runtime_credential_identity`) runs the full fleet
  predicate before the samefile check it already had.

`ManagedClient` is rebuilt per attempt inside `run_client_with_retry` (`runner.py:219-292`,
`build_invocation` per iteration), so a bind conflict adds one more `security` invocation each
round. The test suite is blind to this: `conftest.py::_never_mint_from_the_real_keychain`
replaces `SecurityOwnerCredentialStore` wholesale.

Establish the property once. `_resolve_overlay_credential` is the boundary; `_link_…` should
consume its result, not re-check it.

### M2. The invariant has no single home, so it is now checked at four sites.

`_resolve_overlay_credential`, `_link_overlay_credential_files`, `prepare_runtime_home`
(`runtime_home.py:141-151`) and `CodexSeeder.seed` (`codex_home.py:32-38`) each re-evaluate
"this home has a usable credential". B1(c) and M1 are both symptoms of the same shape: the
predicate is called defensively wherever someone remembered, with arguments reconstructed
differently each time.

Traced the reachability, and the redundancy is real rather than defense in depth: the
`prepare_runtime_home` guard fires only for plain `transport-matters codex` with no
`--home-dir` and no template (`codex_cmd.py:304` passes `use_runtime_overlay=False`;
`captured/context.py:299` always yields `runtime_home_dir is not None` for a real Claude
launch, so the guard is dead for Claude), and that same launch is checked again by
`CodexSeeder.seed`. Failing earlier than port allocation is worth having — one guard, sited
deliberately, is worth more than four sited incidentally.

---

## Minor

**m1. The dispatch axis is still a harness switch.** `_uses_keychain_credential_source` is
`harness == HARNESS_NAME_CLAUDE and sys.platform == "darwin"` (`home_overlay.py:542-544`).
NOW.md 1.2 asks to *"dispatch on credential source (native file vs keychain mint), not on
harness name"*. There is no source value anywhere — it is recomputed from `(harness, platform)`
at each site, and the concept re-appears as two more harness ternaries in
`_native_credential_failure` (display name, error code) and a harness tuple in
`diagnose.py::_report_credential_readiness`. A `CredentialSource` carried on the plan would
turn four switches into one. Behaviorally correct for today's 2×2; the modeling claim in the
commit is not met.

**m2. The native failure names no remedy.** `_native_credential_failure` produces
"`… is not a file); launch aborted.`" The `doctor` comment deleted at `diagnose.py:346-352`
existed precisely to prevent this: *"the alternative is the operator reading the harness's own
'Not logged in · Please run /login' … which names neither the fleet home nor the command that
fixes it."* The fleet branch still carries `CLAUDE_FLEET_BOOTSTRAP_COMMAND`; the Codex and
Linux-Claude branches carry nothing. `codex login` is the missing sentence.

**m3. `CredentialBrokerError.code` defaults to a lie.** `credential_broker.py:88-96` defaults
every raise site in the module to `claude_fleet_credential_unavailable`, including
`CredentialWriteBackError`. `prepare_capture` now forwards `exc.code` verbatim to the canvas
(`capture_rpc_routes.py:275`), so the first non-Claude caller that reaches broker code surfaces
a Claude code and a Claude bootstrap command in the UI. Unreachable today; make `code` required
and the default cannot rot.

**m4. Side-effecting validation call, undocumented.** `_uses_keychain_credential_source` calls
`_overlay_credential_names(harness)` at `home_overlay.py:543` purely so an unmapped harness
raises, and discards the result. One comment, or an explicit `_require_mapped_harness`.

**m5. The consolidation fixture consolidated one module.** `_codex_auth_source`
(`test_runtime_home.py:51`) covers 7 call sites in its own file. The same two lines are
hand-rolled in `conftest.py` (×2), `cli/conftest.py`, `test_home_seed.py`, `test_codex.py` and
`test_home_seed_credentials.py`, and `.credentials.json` has no equivalent helper at all
(inlined in 4 new places). A `conftest` helper taking `(home, harness)` would serve all of
them. Against this repo's DRY line, the current split is the version that will drift.

**m6. `claude_fleet_credential_error` now returns `codex_credential_unavailable`.** The brief
asked for one predicate rather than a Codex twin, and that was the right call, but the name is
now wrong at every call site. `harness_credential_error` costs one rename.

---

## Verified sound

- **Error-code plumbing crosses CLI → API → canvas correctly.** Checked the assumption in
  `transport.ts::throwWithDetail` that the runtime router's `error` field is a machine code,
  not prose: `gateway/main.js` emits `error: "invalid_request"`, `"run_not_found"`,
  `"unsupported_harness"`, `"invalid_cursor"`. The mapping `code = orNull(data.error)` is
  right, and `ApiError` → `CapturedRunSpawnError` → `data-error-code` on the pane is clean and
  leaves 1.4 a real seam.
- **The Codex acceptance test drives the actual CLI** (`runner.invoke(main, ["codex"])`) and
  asserts exit 2, the structured code, the offending path, and that no child spawned.
- **`prepare_capture` no longer hardcodes the Claude code**, pinned by a new test asserting the
  Codex envelope.
- **Probes still gate nothing.** `harnesses/connections.py` untouched; only
  `probes/test_runner.py` changed (+6, fixture). RUNTIME-SURFACING-S2-PLAN.md S2g item 4 holds.
- **No duplication of the credential-copy logic.** The non-darwin path reuses the overlay's
  existing `_symlink_file_if_exists` rather than reimplementing Claude Code's copy, which is
  the right reading of NOW.md 1.1's "check it before writing our own".
- **`--print-command` is unaffected** — `codex_cmd.py:307` short-circuits on `print_command`
  before `prepare_runtime_home`.
- **`CODEX_API_KEY` / `CODEX_ACCESS_TOKEN`** correctly added to `HARNESS_CREDENTIAL_ENV_KEYS`.

---

## Builder quality and trust verdict

**Capable on the seam, not yet trustworthy on the gate.** The dispatch reads well, the CLI-level
Codex test and the API envelope test are the right altitude, the FE plumbing was verified
against the gateway's real error shape rather than assumed, and the constraint list (probes stay
diagnostic, no Codex fleet twin, no copy-logic duplication) was honored. The failure is
process: the PR was pushed with CI already failing on the one platform the whole slice is about,
after NOW.md spelled out that CI runs Linux, and the summary asserted "macOS behavior
byte-identical" and "dispatch on source, not harness" — both measurably untrue. Delegate scope
of this size again, but require the builder to post the CI run id and a green summary line
before handing off, and to state platform-behavior claims as measurements rather than
intentions.

---

# Delta pass — 747a1d6c (99bd449b + 9287a6a8, 1689b976, 747a1d6c)

Tree pristine at 747a1d6c before and after. **8 of 9 findings fixed. 3 residuals, all Minor.**

CI run **30590916642** on `747a1d6c` — `success`, all 9 jobs green including `backend · test`
on ubuntu. Local: `just test-affected main` 3570 passed, `just check` clean (718 files).

The fix round is a redesign rather than a patch: `cli/credential_source.py` (new, 241 lines)
makes `CredentialSource` an actual value — `NativeCredentialSource | KeychainCredentialSource` —
resolved once in `plan_runtime_home` and carried on `RuntimeHomePlan.credential_source` into the
overlay, the template overlay and `CodexSeeder.seed`. Per-harness data moved into one
`_CREDENTIAL_PROFILES` table. `home_overlay.py` lost 217 lines.

| # | Finding | Status |
|---|---|---|
| B1 | CI red on Linux | **Fixed** — run 30590916642 green at this SHA |
| B1(a) | Broker invariant void on Linux, tests unscoped | **Fixed** |
| B1(b) | Linux fail-closed, fixtures not updated | **Fixed** |
| B1(c) | `ValueError` on the predicate's own defaults | **Fixed** |
| M1 | +2 keychain reads per darwin launch | **Fixed, measured** |
| M2 | Invariant checked at four sites | **Fixed** |
| m1 | Dispatch axis is a harness switch | **Fixed** |
| m2 | Native failure names no remedy | **Fixed** |
| m3 | `code` defaults to a lie | **Fixed** |
| m4 | Undocumented side-effecting validation | **Fixed** |
| m5 | Fixture consolidated one module | **Fixed** (one residual) |
| m6 | `claude_fleet_credential_error` misnamed | **Fixed** |

**B1(c).** `harness_credential_error(source)` now takes a resolved source, so the
darwin-only-valid default argument pair no longer exists. The invalid state is
unrepresentable rather than validated.

**M1, measured.** Re-ran the instrumented count against this head: `owner_reads=0 mints=1`
after overlay materialization *and* after `ManagedClient` construction (was 2 and 2).
`_link_overlay_credential_file` now only symlinks. Pinned permanently by a new test,
`test_claude_overlay_does_not_probe_owner_store_after_mint`, asserting `owner_reads == 0` —
the measurement became a gate.

**M2.** `CodexSeeder.seed` no longer re-checks; it calls `resolve_credential_path` only on the
branch that actually copies. `_resolve_materialization_credential_source` additionally asserts
`source.harness == harness`, so a mismatched source cannot be threaded in.

**m1.** `_CREDENTIAL_PROFILES` holds display name, credential filename, error code, login
command and the keychain flag per harness; `credential_harness_names()` drives `doctor`.
`_credential_profile` raises on an unmapped harness, which absorbs m4.

**m3.** `CredentialBrokerError.__init__` takes `code` with no default; all four construction
sites pass one explicitly.

**Docs.** The `docs/ARCHITECTURE.md` "Credential isolation" bullet was rewritten and reads true
against the code, including the honest statement that file-backed sources link the harness's
**refresh-capable** native credential — the B1(a) design change is now declared in the
governing doc rather than implied. One imprecision, see r2.

## Residuals

**r1. The spawn boundary now enforces nothing on non-darwin.** `credential_source.py:169-170`
— `assert_claude_client_credential_identity` returns as soon as the source is native, without
checking `source.credential_path.is_file()`. At 99bd449b that path still ran the file check;
the fix round removed it along with the redundant keychain read. On darwin nothing is lost (the
`samefile` check subsumes existence). On Linux the function its own docstring calls "the
unavoidable spawnable boundary" is a no-op. Traced the reachability: not a live hole, because
every current Claude CLI path resolves through `resolve_credential_path` first
(`captured/context.py:299` yields an overlay for any real launch). Restoring it is one
`harness_credential_error(source)` call with no keychain cost, and it is the check that would
catch a future path that skips the overlay.

**r2. `ARCHITECTURE.md` overstates the shared predicate.** "Both paths fail closed through
`credential_source.harness_credential_error`" — the keychain path at the overlay boundary fails
closed through `resolve_credential_path` → `_mint_claude_credential`, which never calls
`harness_credential_error`. Both *do* fail closed; they do not both go through that function.

**r3. m5 residual.** `conftest._credential_source_home` re-hardcodes `".credentials.json"` and
`"auth.json"`, which `home_constants` already owns and `_CREDENTIAL_PROFILES` now owns again.
Test code may import those privates. Third copy of the same mapping.

## Builder trust verdict, revised

**Trust raised: this is the response you want from a builder under review.** The fix round did
not patch the six symptoms; it found the shared cause — a source concept with no
representation — and introduced the type, which closed the blocker, both majors and four minors
at once. It converted my ad-hoc keychain measurement into a permanent regression test rather
than just making the number go down, re-scoped the platform tests honestly instead of deleting
the assertions, and amended the governing doc to declare the security property it changed.
Three residuals remain, all Minor, one of them introduced by the fix. The earlier caveat stands
unchanged in kind but not in weight: the first round was pushed with CI already red, and the
gate discipline, not the engineering, is the thing to keep watching.

---

# Micro-round — a252df24. Clean.

Tree pristine at a252df24. CI run **30591768274**, `success`, all 9 jobs green at this SHA.
Local `just test-affected main` 3572 passed, `just check` clean (718 files).
All three residuals closed.

**r1 — closed with a pinning test.** `credential_source.py:169-171` restores
`if error := harness_credential_error(source): raise error` on the native branch of the spawn
boundary. Pinned by `test_non_darwin_managed_claude_client_fails_closed_if_credential_disappears`,
parametrized `linux` / `win32`: it resolves the source, `unlink()`s the credential behind it,
then asserts `ManagedClient` construction raises with code `claude_credential_unavailable`.
The test genuinely fails before the fix — at 747a1d6c that branch returned unconditionally, so
nothing could raise. Cost is one `is_file()`; re-measured the darwin path and it is unchanged at
`owner_reads=0 mints=1`, so M1 is not reintroduced.

**r2 — closed.** The `ARCHITECTURE.md` bullet now names both mechanisms separately: native
sources through `harness_credential_error`, macOS minting through `resolve_credential_path` and
`_mint_claude_credential`. Reads true against the code.

**r3 — closed.** `conftest._credential_source_home` reads
`home_constants._CLAUDE_CREDENTIAL_FILENAME` / `_CODEX_AUTH_FILENAME` instead of restating them.

**No new findings.** Nothing outstanding from any round.
