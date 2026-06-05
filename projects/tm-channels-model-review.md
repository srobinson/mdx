# Transport Matters channel model review

Reviewed live PR #341 at `80d10272645e9342b87334c41518891bf671ad22` on branch `ml/channels-model`. GitHub reported 845 additions, 170 deletions, 19 changed files, nine successful checks, and one optional skipped check. The shared worktree was pristine before and after the read pass. No repository file or machine state was changed.

Verdict: **5 blocker, 3 major, 2 minor**.

Concurrent sweep verdict: **unsafe**.

Prior finding closure: **5 of 8 closed**.

## Findings

### Blocker 1: pytest workers from different sessions share the same temporary root

Inputs and state: session A and session B use the same machine temporary base and the same worker name, such as `gw_main` without xdist or `gw0` with xdist. Session A has a live Codex CA bundle under `transport-matters-pytest-gw_main`. Session B starts.

`pytest_temp_root` includes only `_worker_name()`. It has no process id, session id, start time, or nonce. `_manage_test_litter` calls `sweep_test_temp_residue` before redirecting its own temporary files. The sweep deletes every directory in that shared root whose name has the current `mkdtemp` suffix shape. It performs no owner or liveness check.

What is lost: session B can recursively delete session A's live CA bundle. Session A retains a cached path to files that no longer exist, and an active test client can lose its trust material.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/conftest.py:_manage_test_litter`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:pytest_temp_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:sweep_test_temp_residue`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/codex_trust.py:_resolve_generated_codex_ca_certificate`.

### Blocker 2: database ownership checks use the sweeper's PID namespace

Inputs and state: session A and session B share PostgreSQL but run in different process namespaces. Session A owns `tm_test_<A-pid>_<32 hex>`. Its process is live, but A's PID is not visible inside B. A is between connections when B starts.

`drop_orphaned_test_databases` parses A's PID and calls `os.kill(pid, 0)` from B. `ProcessLookupError` classifies A as dead. The query observed zero active connections, so B issues `DROP DATABASE`. The nonforcing drop protects A only if a connection appears before the drop executes. A reconnect gap that lasts through the drop loses the database.

What is lost: a live test session's complete database is deleted and the session fails. The exact name shape and zero connection snapshot do not establish cross namespace liveness.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:drop_orphaned_test_databases`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:_process_is_alive`.

### Blocker 3: template cleanup still treats its prefix as ownership and terminates racing connections

Inputs and state: PostgreSQL contains an unrelated database named `tm_test_template_customer_archive`. It has no Transport Matters metadata, is older than 15 minutes, and has no connection when pytest startup enumerates it.

`_stale_template_database_names` selects every database with `TEMPLATE_DB_PREFIX`. Missing metadata falls through to the database filesystem timestamp. The database is selected by prefix and age. `drop_stale_templates` then uses `drop`, which terminates connections before dropping the database.

What is lost: the unrelated database is deleted. A connection established after enumeration is terminated rather than protecting the database. The ordinary test database regex does not cover this separate template path.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:_stale_template_database_names`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:drop_stale_templates`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:drop`.

### Blocker 4: reset still deletes live captured runs without probing their locks

Inputs and state: a Claude or Codex CLI capture is live in the selected channel. No desktop backend exists. The operator resets that channel with database work skipped.

`gate` checks database connections unless `--skip-db` is set and checks only `_desktop-backend` processes. It never probes `WorkspaceLock`. Both local and prepared captured run paths hold that lock while they own the run directory.

What is lost: reset removes the selected channel home, including the live Tier 1 run, settings, runtime records, and managed agent home. The replacement contains no equivalent of the rejected manifest based gate and does not replace it with direct lock enumeration.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:gate`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/captured/run.py:run_captured_run_on_local_tty`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/captured/run.py:prepare_captured_run`.

### Blocker 5: the dev desktop harness can bind the live stable channel through inherited environment

Inputs and state: the installed stable desktop is the owner's active release. The shell has `TRANSPORT_MATTERS_CHANNEL=stable`, and the owner launches the working tree through `just dev desktop`.

`local-desktop-dev-mode.sh` resolves `channel` from that environment before its `dev` default. Its validation accepts every committed channel. The committed integration test explicitly pins `stable` as a supported override. The harness retains its offset ports, so port occupancy does not prevent it from launching against stable's home, database, Electron app id, and user data.

What is lost: working tree code can read and write the shipped release's persistent state while the installed release is active. Database and filesystem writes from the two processes share one channel boundary.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/local-desktop-dev-mode.sh:channel`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/tests/integration/test_local_desktop_dev_mode.py:test_dev_desktop_honors_explicit_channel_override`.

### Major 1: release maturity and channel isolation are not parser invariants

Inputs and state: `channel-specs.json` changes stable's `resetPosture` from `hard-guarded` to `routine`, or changes dev's home, database, and Electron identity to stable's values while retaining its routine posture.

`_build_channel_spec` accepts every supported posture for every channel id. `_channel_specs` checks duplicate ids only. It does not require stable to remain hard guarded or require homes, database names, ports, and Electron identities to be distinct. Reset consumes the resulting posture and targets without an independent stable identity check.

What is lost: the first edit makes `just reset stable` run without `--allow-stable` or typed confirmation. The second makes the default routine dev reset target stable state. Both states are reachable through spec edits alone. The current committed stable spec still requires both safeguards, including when `--yes` is present.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel.py:_build_channel_spec`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel.py:_channel_specs`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:RESET_POSTURE`.

### Major 2: one genuine test database family can never match the startup sweep

Inputs and state: a CLI test creates its temporary channel database and the pytest process is killed before fixture teardown.

`temporary_channel_database` mints `tm_test_channel_<pid>_<32 hex>` and wraps it in `TestDb`. `_TEST_DB_NAME_RE` accepts only `tm_test_<pid>_<32 hex>`. Every leaked CLI channel database is skipped forever by the new startup sweep. This family existed before PR #341 and can already be present on disk.

What is lost: repeated killed CLI test sessions accumulate unbounded PostgreSQL databases. The converse shape guarantee is false even though all names produced by `TestDb.create` itself match.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/conftest.py:temporary_channel_database`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:_TEST_DB_NAME_RE`.

### Major 3: template identity collides across sessions that share worker and PID values

Inputs and state: two containers share the same test database URL, both use worker `gw_main`, and both expose the same local PID, a common container case.

`ensure_template` hashes only the admin URL, worker name, and PID. It omits hostname and a session nonce, so both sessions derive the same template database name. Their concurrent `CREATE DATABASE` calls collide and one session fails. After one container exits, a different hostname makes `_template_owner_is_alive` retain its template indefinitely; a later container with the same PID still derives the occupied name.

What is lost: test startup availability and bounded cleanup. The stale template can permanently block later sessions that reproduce the same worker and PID tuple.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:ensure_template`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:_worker_name`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:_template_owner_is_alive`.

### Minor 1: preexisting Codex CA litter lies outside every new pytest root

Inputs and state: a test run from code before PR #341 left `transport-matters-codex-ca-<suffix>` directly in the system temporary directory.

The new fixture creates and scans only `transport-matters-pytest-<worker>`. It does not inspect the former system temporary location because product runs can own indistinguishable names there.

What is lost: no live state is deleted, but old test litter is never reclaimed by the new startup owner. Disk residue remains until manual cleanup.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/conftest.py:_manage_test_litter`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:pytest_temp_root`.

### Minor 2: preferences read failures still report absence

Inputs and state: `defaults read` fails because the preferences daemon or command failed rather than because the domain is absent.

The script prints `(no preferences stored)`, records no issue, and can finish with the clean result. Delete and `cfprefsd` restart failures are correctly counted by `note_issue`; the unresolved ambiguity occurs before those cleanup calls.

What is lost: operator confidence in the clean report. Existing preferences may remain while the command exits successfully.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:APP_ID`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:note_issue`.

## Concurrent sweep matrix

| Case | Guard and result |
| --- | --- |
| Live owner in the same PID namespace | `_process_is_alive` sees the PID and retains the database. |
| Live owner in another PID namespace | No cross namespace guard. A zero connection snapshot permits deletion. |
| PID recycled onto an unrelated live process | The database is retained. This is a false negative and does not destroy a live session. |
| Database created after enumeration | The database is absent from the fetched rows and survives until a later sweep. |
| Connection appears after a zero count | Nonforcing `DROP DATABASE` fails safe if the connection exists by drop time. A continuing gap is unsafe when the owner PID is invisible. |
| Two database sweeps start together | Both can enumerate the same dead orphan. Drop errors are caught. A live database remains protected only by PID visibility or a connection at drop time. |
| Two temp sweeps use the same worker name | Both scan the same root. Either can delete the other's live, exact shape CA directory. |

## Shape coverage

- `TestDb.create` has minted `tm_test_<pid>_<32 lowercase hex>` since the test database helper was introduced. The new regex accepts that current and historical family.
- `temporary_channel_database` mints `tm_test_channel_<pid>_<32 lowercase hex>`. The regex rejects it, so crash residue from that family accumulates.
- Templates use `tm_test_template_<worker>_<12 hex>`. Ordinary cleanup excludes them through the digit requirement. Template cleanup accepts the whole prefix, including unrelated names.
- Current Codex CA directories use the fixed prefix plus Python's eight character `mkdtemp` suffix, which the matcher accepts.
- Older Codex CA directories live in the system temporary root rather than the new pytest worker roots and remain outside startup cleanup.
- Ordinary test database provenance comments from PR #338 are absent. PID embedded Codex CA names from PR #338 are absent. The existing template metadata comment remains in its preexisting template lifecycle.

## Reset policy and dev target

- The reset script initializes `channel=dev` and overwrites inherited `TRANSPORT_MATTERS_CHANNEL`, so inherited channel environment cannot redirect the reset default.
- An explicit reset argument can select another committed channel. The current stable spec requires `--allow-stable` and typed `stable` confirmation. `--yes` does not bypass the typed confirmation.
- The dev desktop harness separately honors inherited `TRANSPORT_MATTERS_CHANNEL`, including `stable`, as described in Blocker 5.
- The current committed specs have distinct homes, database names, ports, and Electron identities. The parser does not enforce that distinctness.

## Original eight findings

| Finding | Verdict | Evidence |
| --- | --- | --- |
| B1, reset can erase live capture | **Open** | `gate` still has no captured run lock probe. |
| B2, temp sweep can erase another live owner | **Open** | Product reset no longer sweeps temp state, but pytest sessions collide on worker only roots. |
| B3, test prefix can delete unrelated data | **Open** | Ordinary names use an exact shape; the template path still uses its prefix and a terminating drop. |
| M1, legacy override capture becomes unreachable silently | **Closed** | `_warn_legacy_override_layout` emits for direct `settings.toml` or `workspaces` and still returns the nested channel path. A genuine old layout therefore produces the warning. |
| M2, Electron containment is lexical | **Closed** | Parser rejects absolute paths and parent traversal. Shell checks canonical containment before removal. |
| M3, arbitrary preferences domain | **Closed** | Parser and shell both enforce the product app id namespace. |
| M4, legacy desktop state is omitted | **Closed** | Reset detects and prints stable, preview, dev, generic Electron profiles, and both legacy preference domains without deleting them. |
| m1, cleanup failure reports clean | **Closed for the original paths** | Preference deletion and daemon restart failures count as issues and exit nonzero. Temp deletion left reset. Minor 2 records the remaining read ambiguity. |

Closure: **5 of 8**.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:_warn_legacy_override_layout`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel.py:_build_channel_spec`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:gate`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:legacy_residue`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:note_issue`.

## Scope

The 19 changed files support the three stated commits: dev channel declaration and harness default, spec owned reset policy with its tests and documentation, and pytest owned litter cleanup. No unrelated product feature is present.

The ordinary test database provenance comments and PID embedded Codex temp names from PR #338 were not reintroduced. The remaining `COMMENT ON DATABASE` production call belongs to the older template metadata lifecycle.

Verification was source only to preserve the owner's active stable session and the explicit no write boundary. The live PR checks provide the execution evidence: nine checks succeeded, with one optional external check skipped.

## Re-verification of 45554308

Reviewed the delta from `80d10272645e9342b87334c41518891bf671ad22` to `455543087dd60c45684a9008daab77ef82f91ca4`. GitHub reports PR #341 at the latter head with 1,209 additions, 472 deletions, 19 changed files, nine successful checks, and one optional skipped check. The shared worktree remained pristine.

Per the owner's amendment, reset force and liveness are outside this pass. This section records no verdict on original Blocker 4.

Verdict: **9 of 9 assessed findings closed, zero new findings**. In the original fixed denominator, this is **9 of 10 verified**, with Blocker 4 excluded by scope.

### Creation time ownership

The startup sweeps are gone. The pytest controller creates a 12 character random session id before xdist workers start. Each worker combines that id with its worker name for one temporary root and one database namespace. `TestDb.reserve`, ordinary clones, the template, and `temporary_channel_database` all use that namespace.

Session teardown queries and drops only the exact current namespace. It no longer matches the general `tm_test_` prefix, parses PIDs, infers age, inspects connection counts, or deletes by a temporary name shape. A preexisting temporary root with the same identity makes `mkdir` raise before the session can use or remove it. A crashed session leaves its root and databases in place. Later sessions do not inspect or delete that residue. Manual inspection remains the documented cleanup path.

This closes original Blockers 1 through 3, Major 2, Major 3, and Minor 1 under the creation time ownership policy. Major 2 has no surviving special family: `temporary_channel_database` now calls `TestDb.reserve`.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/conftest.py:_manage_test_litter`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:pytest_session_id`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:pytest_database_prefix`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:pytest_temp_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:TestDb.reserve`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:TestDb.ensure_template`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:TestDb.drop_session_databases`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/conftest.py:temporary_channel_database`.

### Environment completeness

The complete persistent state selector set is:

1. `TRANSPORT_MATTERS_CHANNEL`, which selects the channel spec.
2. `TRANSPORT_MATTERS_HOME`, which selects the base containing channel homes and therefore `settings.toml`.
3. `TRANSPORT_MATTERS_STORAGE_DIR`, which can select run storage directly.
4. `TRANSPORT_MATTERS_DATABASE_URL`, which overrides the database server URL before channel database substitution.

`local-desktop-dev-mode.sh` clears all four in the current shell and applies `env -u` for every config resolution and child command. It then supplies `dev` explicitly. The database resolver reads the dev channel home and returns the dev database name. The gateway receives that resolved URL explicitly.

The remaining keys in `env_keys.py` do not redirect these product state surfaces. `TRANSPORT_MATTERS_TEST_DATABASE_URL` is consumed only by test database resolution. `TRANSPORT_MATTERS_AGENT_HOME_DIR` selects a managed agent home and is removed by the desktop backend's stale environment scrub. `TRANSPORT_MATTERS_CWD`, ports, run identity, gateway, and runtime fields are either explicitly replaced by the desktop launch plan or do not select channel home, run storage, or the product database. No inherited environment path can redirect this harness to stable state.

This closes original Blocker 5.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/local-desktop-dev-mode.sh:persistent_state_env_keys`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/env_keys.py:HOME`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/env_keys.py:STORAGE_DIR`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/config.py:Settings.load`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/config.py:resolve_database_url`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/config.py:resolve_test_database_url`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:default_storage_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/desktop_cmd.py:_DESKTOP_BACKEND_STALE_ENV_KEYS`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/desktop_cmd.py:_build_desktop_backend_env`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/desktop_cmd.py:_apply_desktop_backend_env`.

### Remaining closures and scope

Known channel reset postures are pinned. Homes, databases, every TCP port, Electron names, app ids, and user data paths must be distinct across specs. This closes original Major 1.

Preferences absence now requires the canonical `defaults` absence result. Other read failures record an issue and return nonzero. This closes original Minor 2.

The 13 file fix delta contains the test namespace replacement, channel invariant enforcement, dev environment isolation, associated reset adjustments, tests, and documentation. No unrelated product feature appears.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel.py:_KNOWN_CHANNEL_POSTURES`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel.py:_validate_channel_specs`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:read_preferences_domain`.

Verification remained source only under the owner's live stable testing constraint. `git diff --check` and `bash -n` passed. The live PR head and check rollup were re-read after the amendment. The repository worktree remained pristine.
