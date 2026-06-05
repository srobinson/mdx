# Transport Matters channels post merge review

Reviewed `origin/main` at `c01488d8`, with parent `9da39e12`. The shared worktree remained on `ml/channels-reset` at `8d5ab107873850f24a841daaf4bc242c76c5e946`. `git status --porcelain=v1` was empty before fetch, after fetch, and after the read pass. The worktree was pristine.

Scope was limited to:

1. `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py`
2. `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh`

Verdict: **3 blocker, 4 major, 1 minor**.

## Findings

### Blocker 1: `--skip-db` disables the only broad liveness signal while destructive home cleanup remains enabled

Inputs and state: a preview Claude or Codex capture is live, but no `_desktop-backend --channel preview` process exists. The operator runs:

```text
scripts/reset-channel-store.sh --channel preview --skip-db --yes
```

`gate` sets the connection count to zero when `skip_db` is true. Its remaining process match covers only `_desktop-backend`. The script then removes every child of `STORAGE_ROOT`, including live Tier 1 capture and the managed runtime home. `--force` is unnecessary.

What is lost: the active run's durable capture, settings, runtime records, executor identity, and managed agent home can be deleted while the run still owns them.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:gate`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:skip_db`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:STORAGE_ROOT`.

### Blocker 2: the temporary directory sweep is global and can delete another live channel's state

Inputs and state: stable has a live Codex CA bundle under `${TMPDIR}/transport-matters-codex-ca-*`, or its shared proxy uses `/tmp/tm-sp-*/s.sock`. Preview is idle. The operator runs:

```text
scripts/reset-channel-store.sh --channel preview --skip-db --skip-home --yes
```

Both temporary sweeps still run. They filter only by basename glob. They do not filter by channel, process id liveness, owner run, age, or the selected storage root. `TMPDIR` and `TM_RESET_TM_SP_ROOT` are also accepted without a root safety check.

What is lost: reset of preview can unlink stable's live CA bundle or shared proxy control socket directory. Stable control traffic can fail and in-flight capture can be lost even though stable was never selected and `--allow-stable` was absent.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:tmp_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:tm_sp_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:gate`.

### Blocker 3: the test database sweep treats a name prefix as proof of ownership

Inputs and state: the configured PostgreSQL server contains an idle, non-test database named `tm_test_customer_archive`. The operator resets preview with database cleanup enabled.

The `orphans` query selects every database whose name begins with literal `tm_test_` and has no open connection. No owner, creation record, template lineage, server namespace, or Transport Matters test provenance is required. The script drops each selected database.

What is lost: the complete non-test database is deleted. The stable guard does not apply because the selected channel is preview and this sweep is server wide.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:orphans`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:allow_stable`.

### Major 1: existing override based capture is orphaned with no migration or fallback

Inputs and state: an existing stable installation has:

```text
TRANSPORT_MATTERS_HOME=/srv/tm
/srv/tm/workspaces/acme/abc/run-1
```

Before `c01488d8`, `default_storage_root` returned the expanded override itself. After `c01488d8`, it resolves the channel spec first and appends `spec.home.name`.

The mapping is:

```text
before root: /srv/tm
before run:  /srv/tm/workspaces/acme/abc/run-1

after root:  /srv/tm/.transport-matters
after run:   /srv/tm/.transport-matters/workspaces/acme/abc/run-1
```

The old run directory remains on disk. Neither scoped file provides migration, fallback lookup, or read through to the former root.

What is lost: no bytes are deleted, but prior capture becomes unreachable through the canonical storage root. Existing `settings.toml` at the former root is equally bypassed, so launch or reset can fail before the owner discovers that the capture still exists.

With no `TRANSPORT_MATTERS_HOME` override, stable remains at `~/.transport-matters`; that case does not move.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:default_storage_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:default_workspaces_root`.

### Major 2: Electron containment is a lexical prefix check

Inputs and state: a future or malformed channel spec resolves Electron data to:

```text
STORAGE_ROOT=/safe/.transport-matters-preview
ELECTRON_USER_DATA=/safe/.transport-matters-preview/../Documents
```

The string begins with `$STORAGE_ROOT/`, so the check passes. `rm -rf` resolves `..` and targets `/safe/Documents`. A path with a symlink in an intermediate component has the same missing canonical containment proof.

What is lost: a directory outside the selected channel home can be recursively deleted.

The script does not call `realpath`, reject `..`, reject symlinked components, or compare canonical parent and child paths.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:ELECTRON_USER_DATA`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:STORAGE_ROOT`.

### Major 3: the preferences target is trusted without a product namespace guard

Inputs and state: a future or malformed channel spec supplies an unrelated bundle domain or a global preferences domain as `APP_ID`. The resolver requires only a nonempty value. On macOS, reset runs `defaults delete "$APP_ID"`.

What is lost: the entire supplied preference domain is deleted, even when it belongs to another application or the global domain.

Shell quoting prevents wildcard expansion and shell injection. It does not prove that the domain belongs to the selected Transport Matters channel. No `io.helioy.transport-matters*` allowlist or equality check is present.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:APP_ID`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:os_name`.

### Major 4: Electron and preferences closure is claimed but legacy state remains

Inputs and state: the owner's machine has the observed canonical and legacy external Chromium profiles plus legacy `com.electron.transport-matters*` preference domains. The operator resets preview.

The script sweeps the selected home. It deletes `ELECTRON_USER_DATA` separately only when the string lies under that home. Any external path is explicitly left alone. Preferences cleanup deletes only the current `APP_ID`.

What is lost: the command's clean-slate guarantee is false. Legacy desktop state remains available to any executable that still resolves the former identity, and the stale UI state that survived the owner's prior nuke remains on disk.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:ELECTRON_USER_DATA`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:APP_ID`.

### Minor 1: cleanup failures can be reported as a clean reset

Inputs and state: a matching temporary directory cannot be removed, or `defaults delete` fails for a reason other than an absent domain.

Both temporary `find` commands discard errors and end with `|| true`. `defaults delete` maps every failure to `(no preferences stored)`. The script later prints that the channel is clean.

What is lost: no additional user data is deleted, but inventory closure and operator trust are lost because retained state is reported as removed.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:tmp_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:APP_ID`.

## Q1: capture path

Resolution order in `default_storage_root` is:

1. Select the supplied environment mapping, or `os.environ` when none is supplied.
2. Resolve the channel spec from the explicit `channel` argument plus that environment.
3. Read `TRANSPORT_MATTERS_HOME`.
4. When the override is nonempty, return `Path(override).expanduser() / spec.home.name`.
5. Otherwise return `spec.home`.
6. `default_workspaces_root` appends `workspaces`.

Existing data moves only in canonical resolution, not on disk. With an override, the old `<override>/workspaces/{slug}/{hash}/{run}` becomes expected at `<override>/<channel-home-basename>/workspaces/{slug}/{hash}/{run}`. The prior directory is orphaned. There is no fallback or read through. Without an override, the root does not move.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:default_storage_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:default_workspaces_root`.

## Q2: reset blast radius and guards

The script can delete state outside the selected channel. The direct selected database and normal selected home have useful guards. The server wide and temporary sweeps do not share that boundary.

| Case | Present guard | Missing guard or result |
| --- | --- | --- |
| Channel omitted | Defaults to `preview` | Safe from accidental default stable reset |
| Empty `--channel` value | `--channel` without a value aborts; `--channel=` reaches channel resolution and fails | No deletion occurs |
| Stable selected | Refuses before resolution unless `--allow-stable` is present | `--yes` and `--force` do not bypass this direct guard |
| Empty resolved home fields | Requires nonempty `STORAGE_ROOT`, `HOME_BASENAME`, and `APP_ID` | No deletion occurs when resolution is incomplete |
| Literal root `/` | Rejects `STORAGE_ROOT == /` | Raw string comparison only |
| Literal `$HOME` | Rejects `STORAGE_ROOT == $HOME` | With `TRANSPORT_MATTERS_HOME=$HOME`, the new resolver appends the channel basename, so the target is a channel subdirectory |
| Unexpected home basename | Requires equality with `HOME_BASENAME` and `.transport-matters*` | Prefix accepts any future `.transport-matters*` name |
| Symlinked or aliased home | No canonical or symlink guard | Raw string and basename checks cannot prove filesystem identity or cross-channel inequality |
| Shared `TRANSPORT_MATTERS_HOME` | New resolver appends distinct channel basenames | New lexical roots are distinct; old override data is orphaned; canonical aliases or mounts are not compared |
| Electron data outside home | Warns and leaves a plain external path alone | Prefix check is lexical, so `..` and intermediate symlink escapes are not contained |
| `tm_test_*` database | Requires prefix and zero connections; drop omits `FORCE` | No owner or provenance guard; any idle non-test database with the prefix is deleted |
| Preferences domain | Uses one quoted `APP_ID` from the spec | No product namespace allowlist; the whole supplied domain is deleted |
| Temporary CA and socket directories | Restricts basenames to two product globs | No channel, process, age, liveness, or safe-root guard |
| `--skip-db` | Skips PostgreSQL work | Also removes the connection based liveness check while home and temp deletion stay enabled |
| `--skip-home` | Preserves `STORAGE_ROOT` | Preferences and global temporary sweeps still run |
| `--force` | Explicitly bypasses liveness | Stable still requires `--allow-stable` |
| `--dry-run` | Returns before confirmation or deletion | Liveness and resolution still run read only |

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:channel`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:allow_stable`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:gate`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:STORAGE_ROOT`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:ELECTRON_USER_DATA`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:orphans`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:APP_ID`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:tmp_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:dry_run`.

## Q3: nine-leak inventory closure

| Prior leak | Merged disposition | Review result |
| --- | --- | --- |
| 1. Implicit stable Electron path and dual profiles | Claims selected Electron data through `ELECTRON_USER_DATA` and home sweep | **Claimed, not closed.** Current in-home data can be removed. Existing external canonical and legacy profiles remain. |
| 2. Separate preference identities | Deletes current `APP_ID` on macOS | **Claimed, not closed.** Legacy Electron domains remain. |
| 3. Claude Keychain records | Header explicitly excludes deletion; script prints one fleet delete command | **Rejected or downgraded, correctly left alone.** Per-run entries are acknowledged but not enumerated. |
| 4. Shared mitmproxy CA | Header explicitly excludes `~/.mitmproxy` as shared trust | **Rejected or downgraded, correctly left alone.** |
| 5. Partial channel home reset | Deletes every child of the selected resolved home | **Closed for a normal real directory.** The root itself remains. |
| 6. `TRANSPORT_MATTERS_HOME` collapse | Appends the channel home basename under the override | **Closed for new resolution.** Existing override based state is orphaned without migration. |
| 7. Crashed test databases | Drops idle databases with the `tm_test_` prefix | **Closed for genuine generated test databases, but unsafe.** The prefix rule creates Blocker 3. |
| 8. PostgreSQL server and volume lifecycle | Header leaves the server to Docker Compose | **Rejected or downgraded, correctly left alone.** |
| 9. Temporary crash residue | Deletes both temporary basename families | **Closed, but unsafe.** The global rule creates Blocker 2. |

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:default_storage_root`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:STORAGE_ROOT`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:ELECTRON_USER_DATA`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:APP_ID`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:KEYCHAIN_SERVICE`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:orphans`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:tmp_root`.

## Verification of PR #338

Verified against live PR head `d986dcdeddb299eddd141c65cf236b30748ce851` on branch `ml/channels-hardening`. GitHub reported all nine checks successful. The shared worktree was pristine before fetch, after fetch, and after this read pass. No repository file was changed.

Closure verdict: **5 of 8 closed**.

New findings: **3 blocker, 3 major, 2 minor**.

### Part 1: closure of the original eight findings

| Finding | Verdict | Deciding evidence |
| --- | --- | --- |
| B1, `--skip-db` can erase live capture | **Partially closed** | `gate` now calls `partition_run_manifests` and refuses when a readable manifest maps to a held `WorkspaceLock`. `partition_run_manifests` begins with `read_all`, which silently skips missing, malformed, schema-invalid, and unreadable manifests. The held lock is never probed for those run directories. |
| B2, global temporary sweep deletes another live channel | **Closed** | Both current temporary names embed their creator PID. `sweep_dead_owner_dirs` keeps numeric PIDs visible to `ps` and keeps every entry whose PID cannot be parsed. A live owner with a pid-less legacy name can exist, but that entry is retained and reported. |
| B3, `tm_test_*` prefix can delete non-test data | **Partially closed** | `drop_orphaned_test_databases` protects ordinary prefix matches unless they have test metadata, same-host dead ownership, and zero connections. The reset immediately also calls `TestDb.drop_stale_templates`, whose template path still accepts an unstamped old `tm_test_template_*` database by age and name, then terminates connections before dropping it. |
| M1, existing override capture is silently orphaned | **Closed for the original layout** | `_reject_legacy_override_layout` raises before returning the new nested root when direct `settings.toml` or `workspaces` markers exist. Existing bytes remain reachable at the path named in the error, and the error provides the stable migration target. The new false-positive startup blocker is separate below. |
| M2, Electron containment is lexical | **Closed** | `_build_channel_spec` rejects absolute `userDataDir` values and every path containing `..`. Reset also requires canonical `realpath` containment before its separate Electron deletion. |
| M3, arbitrary preferences domain | **Closed** | `_build_channel_spec` accepts only the exact product app id or its dot namespace. Reset repeats the same namespace guard immediately before `defaults delete`. |
| M4, legacy desktop closure is claimed but incomplete | **Partially closed** | Reset now says legacy state remains and prints manual removal commands. Preview reports `Transport Matters Preview` and `transport-matters-desktop`, but it does not report the existing `Transport Matters` profile that development wrote while it was bound to stable. |
| m1, cleanup failures still report clean | **Closed for the original failure paths** | `note_issue` records failed preference deletion and failed temporary deletion. A nonzero issue count exits nonzero and prints `done with warnings` instead of `is clean`. A new `defaults read` ambiguity remains below. |

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:gate`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/launch_manifest.py:partition_run_manifests`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/manifest.py:read_all`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:sweep_dead_owner_dirs`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:drop_orphaned_test_databases`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:TestDb.drop_stale_templates`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:_reject_legacy_override_layout`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel.py:_build_channel_spec`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:note_issue`.

#### B1 residual path

A stale, readable manifest with an unlocked lock does not represent a live capture. Proceeding in that case is correct because the kernel lock is the authority.

The residual destructive path is a live held lock without a readable manifest:

1. `run_with_workspace_manifest` acquires `WorkspaceLock` before `run_launch` reaches its first manifest write.
2. `run_captured_run_on_local_tty` acquires the lock and persists facts before `run_client_with_retry` writes the manifest.
3. `prepare_captured_run` acquires the lock and persists facts before `write_captured_run_manifest`.
4. Cleanup unlinks the manifest before releasing the lock.
5. `read_all` skips a missing, malformed, schema-invalid, or unreadable manifest, so `partition_run_manifests` never discovers and probes that held lock.

Inputs and loss: a reset with `--skip-db` races one of the pre-manifest windows, or a live run's manifest becomes unreadable. The gate reports no live run and deletes the selected home, including the held run directory and active capture. The new gate therefore narrows B1 but does not close it.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/launch_manifest.py:run_with_workspace_manifest`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/captured_run.py:run_captured_run_on_local_tty`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/captured_run.py:prepare_captured_run`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/captured_run_models.py:CapturedRunLease`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/manifest.py:read`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/manifest.py:read_all`.

#### B2 PID conclusions

1. A current Codex CA directory embeds `os.getpid()`.
2. A current long shared-proxy path already embeds `os.getpid()`.
3. A pid-less legacy, malformed, or manually created matching entry can have a live owner. The reset keeps it because ownership is unproven.
4. PID reuse cannot make a directory with its original live owner look dead. A live owner still owns that unique PID.
5. PID reuse can make a dead directory look live when an unrelated process now has the old PID. The reset retains that dead residue until the reused PID disappears.
6. Any `ps -p` failure is interpreted as dead rather than unknown. The target macOS environment supplies readable process state, but the code does not distinguish `PID absent` from `ps unavailable or failed`.

The original cross-channel deletion blocker is closed for the supported local process model. PID reuse creates retention, not live-state deletion.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/cli/codex_trust.py:_resolve_generated_codex_ca_certificate`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/shared_proxy/manager.py:_control_socket_path`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:sweep_dead_owner_dirs`.

### Part 2: new defects in the hardening mechanisms

#### Blocker 1: the lock gate enumerates manifests instead of lock files

Inputs and state: a capture has acquired its run lock but has not written its manifest, or its manifest is missing or unreadable. The operator invokes preview reset with `--skip-db` and without `--force`.

`partition_run_manifests` cannot return that run because `read_all` starts from readable `manifest.json` files. The lock probe is never called for the held `lock` file.

What is lost: reset can delete a live Tier 1 run and managed agent home despite the new lock gate. This is the unresolved B1 path above.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/launch_manifest.py:partition_run_manifests`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/manifest.py:read_all`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:gate`.

#### Blocker 2: the reset still drops unproven template-prefixed databases and now terminates racing connections

Inputs and state: the server contains an idle, non-test database named `tm_test_template_customer_archive`, older than 15 minutes, with no Transport Matters metadata. Reset runs with database cleanup enabled.

`drop_orphaned_test_databases` excludes the template prefix. Reset then calls `TestDb.drop_stale_templates`. `_stale_template_database_names` accepts an empty metadata object, falls back to the database filesystem timestamp, and selects the database by prefix and age. `TestDb.drop` terminates any connections that appeared after the selection query, then drops the database.

What is lost: the entire non-test database. The replacement is worse in the connection race: the previous PR's direct `DROP DATABASE` omitted `FORCE` and retained a database that became busy, while `TestDb.drop` explicitly terminates the racing backend.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:TestDb.drop_stale_templates`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:_stale_template_database_names`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:TestDb.drop`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:drop_stale_templates`.

#### Blocker 3: legacy override detection hard-blocks valid layouts on unrelated marker names

Inputs and state:

```text
TRANSPORT_MATTERS_HOME=/srv/shared
/srv/shared/settings.toml                 # unrelated application
/srv/shared/.transport-matters/           # valid stable channel home
/srv/shared/.transport-matters-preview/   # valid preview channel home
```

The detector checks only whether `/srv/shared/settings.toml` or `/srv/shared/workspaces` exists. It does not inspect ownership, contents, whether nested channel homes already exist, or whether the direct marker is unrelated. It raises `LegacyHomeOverrideLayoutError` for every channel before returning a storage path. No caller catches the exception.

What is lost: startup and every storage-root dependent command are blocked for a correctly nested installation. A generic override base with an unrelated `settings.toml`, an unrelated `workspaces` directory, or an empty leftover marker is a false positive. Users with no override, or an override base containing neither direct marker, cannot hit this error.

Actual legacy users who should hit it are those with a nonempty `TRANSPORT_MATTERS_HOME` whose old Transport Matters `settings.toml` or `workspaces` still lives directly under the override.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:_LEGACY_OVERRIDE_MARKERS`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:_reject_legacy_override_layout`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/storage_roots.py:default_storage_root`.

#### Major 1: test database provenance validates only kind and lacks schema validation or authentication

`_parse_database_metadata` accepts any JSON object whose `kind` matches. It does not require `owner_host`, `owner_pid`, or `created_at`. `_database_owner_is_alive` treats a missing, non-integer, or nonpositive owner PID as dead unless a string `owner_host` names another host.

Inputs and loss: an idle non-test `tm_test_*` database has comment `{"kind":"transport_matters.test_db.v1"}`. The stamp is accepted, the absent PID is treated as dead, and the database is dropped. A database owner can forge the comment with `COMMENT ON DATABASE`. A valid stamp also survives a rename or repurposing of the same database object; it stops matching only when the name leaves the `tm_test_` prefix or the comment is removed.

PostgreSQL template cloning does not copy database comments. `TestDb.create` therefore stamps each clone explicitly. Template metadata uses a different kind and is excluded from the ordinary test-database query.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:_parse_database_metadata`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:_database_owner_is_alive`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:_set_database_metadata`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:TestDb.create`.

#### Major 2: the create-then-comment window can produce permanent unstamped test databases

`TestDb.create` clones the database and then issues a separate `COMMENT ON DATABASE`. PostgreSQL database creation cannot share a transaction with that later comment. A process killed after clone creation and before the comment leaves a genuine `tm_test_*` database without provenance.

Pre-PR databases without stamps are also kept. The sweep reports all such databases but never adopts or deletes them. The preexisting set is finite. Repeated hard kills in the new create-to-comment window can continue adding unsweepable databases, so growth is not bounded by the upgrade.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:TestDb.create`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:_clone_database_from_template`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:_set_database_metadata`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/session/testing.py:drop_orphaned_test_databases`.

#### Major 3: preview legacy reporting misses the owner's former stable-bound development profile

Inputs and state: the owner resets preview after upgrading. The machine still contains `~/Library/Application Support/Transport Matters`, written by development before `just dev desktop` was rebound from stable to preview.

The report derives one path from the selected channel's `APP_NAME`. Preview therefore checks `Transport Matters Preview`, plus the generic `transport-matters-desktop` path. It does not check `Transport Matters`.

What is lost: no bytes are deleted, but the new manual-cleanup report omits one of the two observed external profiles and can still lead the owner to believe all known legacy state was disclosed.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:APP_NAME`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:legacy_residue`.

#### Minor 1: PID reuse retains dead temporary residue

A PID cannot be reused while its original owner is alive, so reuse cannot make a current live directory look dead. After the owner exits, an unrelated process can receive the same PID. `ps -p` then makes the dead directory look live, and reset retains it until that unrelated process exits.

The check proves only PID occupancy. It does not compare process start time, executable identity, or a nonce from the directory owner.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:sweep_dead_owner_dirs`.

#### Minor 2: preferences read failure is still reported as absence

If `defaults read "$APP_ID"` fails because the domain is absent, printing `(no preferences stored)` is correct. The same branch handles command failure, daemon failure, or an unreadable domain. Those states also print absence, do not increment `issues`, and permit the final clean result.

The original delete-failure path is closed. This is a narrower read-failure ambiguity.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:APP_ID`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/scripts/reset-channel-store.sh:note_issue`.

### Committed channel validator proof

Both committed channel specs satisfy the new parser:

| Channel | appId | userDataDir | Result |
| --- | --- | --- | --- |
| stable | `io.helioy.transport-matters` | `electron-user-data` | accepted |
| preview | `io.helioy.transport-matters.preview` | `electron-user-data` | accepted |

Both app ids are the exact product namespace or its dot child. Both user-data paths are relative and contain no `..` path component.

Evidence: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel.py:PRODUCT_APP_ID_NAMESPACE`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel.py:_build_channel_spec`, `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch/api/src/transport_matters/channel-specs.json:channels`.

### Part 3: comparison with the replaced code

**Yes.** The false-positive legacy marker guard makes a valid generic override base fail startup where the replaced code started normally. The template cleanup is also worse during a connection race because it terminates newly connected backends before dropping, while the replaced direct drop failed safe when the database became busy.
