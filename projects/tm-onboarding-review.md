# PR #344 review — `ml/onboarding-bootstrap` (bootstrap channel configuration during resolution)

Read-only review. Base `main`, head `ml/onboarding-bootstrap` @ `c6619d24`, +339/-142 across 20 files, 9/9 CI green
(`[code]smith` skipped). Reviewed against the scout report `~/.mdx/projects/tm-onboarding-walk.md`.

Working tree pristine at review start and at write time (`git status --porcelain` empty both times; the worktree stayed
on `ml/boundary-lesson` and was never checked out to the PR branch). No edits, no commits, no repo writes.

**Method.** The PR branch and `main` were extracted with `git archive` into a scratchpad and driven with the repo's
existing `api/.venv` interpreter. Every invocation ran under `env -i` with both `HOME` and `TRANSPORT_MATTERS_HOME`
pointed inside the scratchpad, so `~/.transport-matters`, `~/.transport-matters-preview` and `~/.transport-matters-dev`
were never read or written. No Postgres server was contacted except an unreachable `127.0.0.1:1`; `channel ensure-db`
was never run against a live server. No keychain, no `~/Library`, no test suite run.

**Counts: 1 blocker / 2 major / 4 minor.**

**Load-side-effect verdict: wrong shape**, but narrowly and with a one-line remedy. The defect is not that a write
happens; it is that a *read* API became fallible and is now invoked by the diagnostics. See finding 1 and finding 2.

---

## The four factual questions, answered from measurement

### Which commands create a channel home merely by running

Each row is one `env -i` invocation into an empty sandbox home, on both trees.

| command | `main` | PR #344 |
|---|---|---|
| `--help`, `version`, `paths`, `list` | nothing | nothing |
| `channel list`, `channel status`, `channel stop`, `tail` | nothing | nothing |
| **`doctor`** | home **directory** only (its own storage-writability probe) | directory **+ `settings.toml`** |
| **`db status`** | **nothing** (exit 2, "not configured") | **directory + `settings.toml`** (exit 1, connect failure) |
| `claude/desktop --channel <typo>` | nothing (exit 2) | nothing (exit 2) |

So: **yes, `transport-matters doctor` materializes `~/.transport-matters-dev/settings.toml` just by being invoked**
under `TRANSPORT_MATTERS_CHANNEL=dev`; `db status` newly creates the whole home. `channel list` does not, and neither
does any other purely informational command. Beyond the CLI, every settings-resolving process inherits the write: the
desktop backend, the mitmproxy addon, and the dev harness's own gateway URL probe
(`local-desktop-dev-mode.sh`, `database_url=$(… resolve_database_url(get_settings()) …)`).

### Can it create a home for a channel the user never asked for

**Yes for a valid-but-stale channel, no for a typo.** `TRANSPORT_MATTERS_CHANNEL=preview transport-matters doctor`
creates `.transport-matters-preview/settings.toml` — an old export left in a shell silently materializes a channel the
user is not working in. A typo'd value is safe in both forms: `TRANSPORT_MATTERS_CHANNEL=nosuchchannel doctor` and
`--channel nosuch` both fail channel resolution before any write (`error: unknown channel 'nosuch'`, exit 2, nothing
created). `channel ensure-db dev` invoked with no `TRANSPORT_MATTERS_CHANNEL` — exactly what the dev harness runs under
`clean_env` — materializes only `.transport-matters-dev`, because `activate_channel` sets the env and clears the
settings cache before resolution.

### Read-only filesystem, permission failure, full disk

**`Settings.load` now fails where it previously succeeded, and it takes commands that never needed to write with it.**
See finding 1; this is the blocker.

### Idempotent and concurrency-safe

**Yes, and this part is well built.** 2, 12 and 32 simultaneous `Settings.load()` processes into one empty channel home
each produced: exactly one `settings.toml`, one distinct byte size, mode `0600`, zero `.tmp` residue, zero failures,
identical resolved URL in every process. `write_atomic_bytes_once` writes a durable temp then `os.link`s it into place,
so the losers get `FileExistsError` (swallowed) and a crash can never leave a partial document at the destination. The
`0600` mode is also a tightening over the previous `write_text` default.

### Does it ever overwrite or truncate an existing settings.toml

**No.** Two independent guards: `ensure_settings_scaffold` returns early on `target.exists()`, and `os.link` refuses to
replace an existing name. Verified directly: a hand-written `settings.toml` containing
`postgresql://me:secret@prod.example.com:5432/mine` was byte-identical (same SHA) after running `doctor` and
`db status`, with no temp residue left behind. A dangling symlink at that path is also safe — `exists()` is false, the
`link` raises `FileExistsError`, and the handler returns without touching it.

---

## 1. BLOCKER — a load path that writes made `Settings.load` fallible, and the diagnostics crash on the environments they exist to diagnose

`api/src/transport_matters/config.py`, `Settings.load` → `ensure_settings_scaffold`;
`api/src/transport_matters/atomic_io.py`, `write_atomic_bytes_once` → `_write_temp`.

`ensure_settings_scaffold` catches only `FileExistsError`. Every other `OSError` — `PermissionError`, `EROFS`,
`ENOSPC`, and an `os.link` refused by a filesystem without hardlink support — propagates out of
`ensure_settings_scaffold`, out of `Settings.load`, out of `get_settings()`, into callers that have no reason to expect
a write to have been attempted. The very first thing `_write_temp` does is `path.parent.mkdir(parents=True,
exist_ok=True)`, so an unwritable channel-home *parent* is enough.

**Failure scenario, reproduced.** Channel-home base at mode `555` (a locked-down or read-only `HOME`, a container with
a read-only home volume, or a `TRANSPORT_MATTERS_HOME` pointed at a read-only mount):

- `main`, `transport-matters doctor` → exit 1 with its designed diagnostic:
  `fail storage — Cannot write to …/.transport-matters: [Errno 13] Permission denied.`
- `main`, `transport-matters db status` → exit 2 with `error: set TRANSPORT_MATTERS_DATABASE_URL, or add …`
- **PR #344, `doctor`** → exit 1 with a raw traceback, frames:
  `cli/__init__.py:510 doctor → diagnose.py:292 run_doctor → config.py:263 get_settings → config.py:153 load →
  config.py:190 ensure_settings_scaffold → atomic_io.py:40 write_atomic_bytes_once → atomic_io.py:73 _write_temp →
  PermissionError`
- **PR #344, `db status`** → exit 1 with a raw traceback through `db_cmd.py:49 status → db_cmd.py:40 _resolve_or_exit`.

`diagnose.py:292` is `settings = get_settings()`, the line immediately before the storage-writability probe whose
`try/except` produces the "Cannot write to …" message. The PR makes `get_settings()` throw on exactly the condition
that check exists to report, so the check can never run. `doctor` is the command the project's own mental model names
first when something feels wrong; it is now the command that crashes first.

**Smallest fix, one line:** widen the handler to `except OSError: return None`. `FileExistsError` is an `OSError`
subclass, so this collapses both branches, and `load_from` already tolerates an absent file. Every property the PR
gained — the cycle break, atomicity, idempotency, no-clobber — is preserved, and an unwritable home degrades to exactly
`main`'s behaviour (defaults plus the new channel-specific guidance) rather than a traceback. This should be in the PR
before merge; it is smaller than the test changes already in it.

## 2. MAJOR — materializing on *resolution* puts state creation behind read-only and diagnostic commands

`api/src/transport_matters/config.py`, `Settings.load`.

The repo carries a standing owner rule that nothing may create a Space, worktree, canvas or row as a side effect of
*resolving* identity. This is the same shape one layer down, and the measurements above show it lands where that rule
would predict: the two commands that newly create channel state are `doctor` and `db status`, both read-only
diagnostics, and a stale `TRANSPORT_MATTERS_CHANNEL` export makes them do it for a channel the user is not working in.
Neither prints that it created anything.

**Failure scenario.** A developer exports `TRANSPORT_MATTERS_CHANNEL=preview` to inspect a preview instance, then days
later, in the same long-lived shell, runs `transport-matters doctor` to debug something unrelated. A
`~/.transport-matters-preview/` home and `settings.toml` appear, silently. Nothing tells them. If they later run
`transport-matters channel ensure-db preview` from a shell where the env var is *not* set, the two configurations they
now own are not the same file.

The scout's own recommendation was narrower: "Make `channel ensure-db <channel>` materialize the channel starter before
resolving its URL." **The smaller alternative** is to keep `ensure_settings_scaffold` an explicit call in the three
bootstrap-shaped seams — `channel ensure-db`, the `reset-channel-store.sh` resolver, and `preflight_session_store_or_exit`
— which is where it was for the launch path already. That is the same three lines the PR deleted, costs one repetition
each, keeps `Settings.load` a pure read, and gives finding 1 for free.

If the single-point materialization is kept deliberately (it is genuinely less code and covers `db` and `doctor` too),
then finding 1's `except OSError` is mandatory, and the trade should be recorded: **config resolution is a state
mutation**, and every future caller of `get_settings()` inherits a filesystem write.

## 3. MAJOR — the rewritten QUICKSTART does not carry a managed-Postgres newcomer, and the re-walk could not have caught it

`QUICKSTART.md` steps 2 and 3; `api/src/transport_matters/config.py`, `resolve_database_url`;
`api/src/transport_matters/cli/channel_cmd.py`, `ensure_channel_database`.

Step 2's second option still reads "**Existing local or cloud/managed Postgres.** Create a database and use its
connection string in step 3." Two things then happen that the step does not say:

1. `resolve_database_url` unconditionally rewrites the database component of that URL to the channel's database name
   (`database_url_with_database_name(resolved, spec.database_name)`). The database the user was told to create is
   ignored; only the server, credentials and port survive.
2. Step 3's now-mandatory `transport-matters channel ensure-db stable` connects to the **`postgres` maintenance
   database** on that server and issues `CREATE DATABASE "transport_matters"`.

**Failure scenario.** A newcomer on a managed Postgres (RDS, Cloud SQL, Neon, Supabase) follows step 2, creates
`myapp_tm`, and pastes its URL into step 3. `ensure-db` ignores `myapp_tm`, tries to connect to the `postgres`
database, and issues `CREATE DATABASE` — both of which managed offerings routinely refuse to a non-superuser role. The
documented path ends in a permission error with no documented next action, which is a wall of exactly the kind the
report was written to remove. The re-walk cannot have surfaced this: its measurement boundary records an owned local
PostgreSQL cluster on `127.0.0.1:55439`, i.e. the local-Docker branch of step 2 only.

The claim "0 walls, 4 steps, 0 undocumented" is **true for the local-Docker path and unproven for the other path the
same step offers.** Minimum fix: say in step 2 that only the server portion of the URL is used and the channel database
name is fixed, and in step 3 that `ensure-db` needs `CREATEDB` plus access to the maintenance database, with the manual
alternative (create `transport_matters` yourself, then `transport-matters db upgrade`) for a locked-down server.

## 4. MINOR — "not configured" is no longer a reachable state, so an unconfigured user is told the wrong thing

Because the starter always materializes, every command sees the packaged
`postgresql://tm:tm@localhost:55432/transport_matters`. Measured: `db status` in an empty home moves from
`main`'s exit **2** with `error: set TRANSPORT_MATTERS_DATABASE_URL, or add [database] url …` to PR #344's exit **1**
with a connection failure against `localhost:55432`.

For the local-Docker user this is an improvement. For the cloud user who has not exported anything, the first error now
names a server they never chose and a port they never opened, rather than saying they have not configured one.
`diagnose` does append `database_url_guidance(settings)` on failure, so the recovery instruction is still present —
which is why this is a minor and not a major. The PR's own tests show the cost: reaching the unconfigured branch now
requires hand-writing a `settings.toml` containing a bare `[database]` (`test_db_cmd.py`,
`test_channel_cmd.py`, `test_launch_preflight.py` all had to do this).

## 5. MINOR — the test suite is now one deleted env var away from writing to the developer's real channel home

`api/conftest.py`, `clear_channel_storage_env`.

The autouse `_isolate_channel_home` fixture pins `TRANSPORT_MATTERS_HOME` into a tmp dir, so the suite is safe today.
But `clear_channel_storage_env` deliberately deletes that pin, and the PR had to add
`monkeypatch.setenv("HOME", str(tmp_path / "os-home"))` plus two `channel_module` cache clears to stop the new write
landing in the developer's real `~/.transport-matters`. That guard is per-fixture discipline, not a structural one.

I checked every other site that deletes the pin — `cli/test_tail_cmd.py` (×3) and `cli/test_channel_cmd.py` (×6) — and
all of them invoke `channel list`, `channel status`, `channel stop` or `tail`, none of which resolve settings
(measured above). **The suite does not currently write to a real channel home.** The hazard is the next test that
deletes the pin and touches a settings-resolving command; nothing fails closed on it. A cheap structural guard: have
the autouse fixture also pin `HOME`, so clearing `TRANSPORT_MATTERS_HOME` falls back to a sandbox rather than `~`.

## 6. MINOR — a filesystem-route test suite acquired a Postgres dependency

`api/src/transport_matters/api/v1/test_local_file_routes.py`.

Fourteen tests about serving local PNGs, markdown and JSON, plus the DNS-rebinding Host allowlist, now take a `test_db`
fixture and build the app with `get_settings().with_session_store_url(test_db.database_url)`. The cause is finding 4:
`create_app()` previously saw no database URL and stayed inert; now it inherits the scaffolded default and tries to use
it. Nothing is wrong with the change as written, but the direction is worth naming — a load-time write turned a
pure-filesystem unit test into one that needs a live Postgres, and the same pull applies to every future in-process
consumer of `get_settings()`.

## 7. MINOR — crash residue in the channel home is possible and unswept

`atomic_io.write_atomic_bytes_once` writes `.settings.toml.<uuid32>.tmp` beside the target and unlinks it in a
`finally`. A `SIGKILL` (or a power loss) between `_write_temp` and `os.link` leaves that file in the channel home
permanently: the `finally` never runs, and the next `ensure_settings_scaffold` returns early on `target.exists()`
without sweeping. `atomic_io` already exports `remove_atomic_write_residue` for exactly this, and it is not wired here.
Cosmetic litter rather than a correctness problem — the destination is never partial — but the module's own cleanup
helper going unused in the newest caller is worth one line.

---

## Item 2 — the dev harness isolation decision, against #341

**Coherent.** `scripts/local-desktop-dev-mode.sh` builds `clean_env` by unsetting exactly
`TRANSPORT_MATTERS_CHANNEL`, `TRANSPORT_MATTERS_DATABASE_URL`, `TRANSPORT_MATTERS_HOME` and
`TRANSPORT_MATTERS_STORAGE_DIR` — the four #341 closed over — and the new bootstrap line runs under it:
`"${clean_env[@]}" uv run --project "$api_dir" transport-matters channel ensure-db "$channel"`, passing the channel as
an **argument** rather than re-introducing the stripped variable. The gateway URL probe further down does the same and
re-adds only an explicit `TRANSPORT_MATTERS_CHANNEL="$channel"`. Ordering is right: the bootstrap runs before the probe,
so the probe reads a materialized starter, and it runs after the port checks and before any pane spawns.

The builder's decision — keep the isolation, persist a custom server in `~/.transport-matters-dev/settings.toml` — is
the only one consistent with #341, and `docs/CHANNELS.md` now states it with a runnable recipe (`ensure-db` with the
explicit URL, then `$EDITOR` the dev starter, then launch). That closes the scout's item 5, which named precisely the
fact that no document combined "env wins", "dev home is `~/.transport-matters-dev`" and "the dev harness strips the
override".

Two consequences worth stating rather than fixing:

- The script runs `set -euo pipefail`, and the new `ensure-db` line is unguarded, so a failed bootstrap aborts before
  any backend, gateway, Vite or Electron pane starts. The README's claim that `just dev desktop` "creates and migrates
  the disposable `transport_matters_dev` database, then starts the backend…" holds, and wall 4 does not return.
- `just dev desktop` therefore issues `CREATE DATABASE transport_matters_dev` on **whatever server the dev starter
  names**, on every invocation. For a user who followed CHANNELS.md and pointed the dev starter at a shared or
  production server, a routine dev-loop command creates a database there without prompting. That is the documented
  design, not a defect, but it deserves a sentence in CHANNELS.md next to the `$EDITOR` step.

## Item 3 — doc accuracy

Every command the rewritten docs instruct exists and is reachable. Verified against the installed CLI surface:
`channel list | status | stop | ensure-db | promote`, `db status | upgrade | wire-gc`, `doctor`, `tail`, `desktop`,
`claude`, `codex`. `docker-compose.yml` is present at the repo root for the source-checkout variant, and QUICKSTART
correctly gives tool users a self-contained `docker run` instead. `just dev client directory=dev_target_dir` exists and
`local-desktop-dev-mode.sh` defaults `target_path="${1:-$PWD}"`, so both the README's path-bearing form and CHANNELS'
bare `just dev desktop` work. The tmux prerequisite is now stated in README and CHANNELS and the script's own error
names the cure (`tmux new-session -s transport-matters`), pinned by a new integration test.

No stale "created on first launch" wording survives: `settings.example.toml`, QUICKSTART and CHANNELS all now describe
materialization on configuration read, which is an honest description of the new side effect.

**The hand edit is a documented step.** QUICKSTART: "To configure it without a persistent shell export, edit
`[database] url` in the starter created by the command, then unset `TRANSPORT_MATTERS_DATABASE_URL`." CHANNELS, for the
dev channel: `$EDITOR ~/.transport-matters-dev/settings.toml` followed by "Set `[database] url` to the same server URL
before `just dev desktop`." Both name the exact file and the exact key. That satisfies the brief's condition.

## Item 1 — the re-walk claim

For the path it measured — local Docker, source checkout, dev channel — the walls are genuinely gone, not moved into
implicit knowledge: wall 1 by removing `doctor` from the README's pre-setup position and re-placing it after setup,
wall 3 by documenting tmux in two places plus the script's own message, wall 5 by the fix under review, wall 6 by the
`reset-channel-store.sh` resolver's `try/except` that turns the traceback into
`error: cannot resolve 'dev' channel configuration: …` at exit 2 (pinned by a new integration test that asserts
`"Traceback" not in stderr` and that the stale venv hint is gone). Wall 4 is closed structurally, by the harness
bootstrapping the database before any pane starts, rather than by telling the reader to do it.

The claim is overstated in one dimension only, finding 3: step 2 offers two Postgres options and the walk exercised
one.
