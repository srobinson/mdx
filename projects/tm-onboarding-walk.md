# Transport Matters dev onboarding walk

## Result

The documented path does not bootstrap a new `dev` channel. Seven walls occur
before a working desktop development stack. The earliest executed wall is
`transport-matters doctor`, which the README places before the Postgres and
configuration instructions. The critical bootstrap command,
`transport-matters channel ensure-db dev`, is blocked by the same missing
configuration that blocks `just reset`.

The measured runtime minimum, after the documented source installation, is five
steps. Two are undocumented:

1. Start Postgres with `docker compose up -d`.
2. Run `transport-matters desktop --channel dev`. This undocumented bootstrap
   step creates `~/.transport-matters-dev/settings.toml` and then fails because
   the `dev` database does not exist.
3. Run `transport-matters channel ensure-db dev`.
4. Start or enter tmux. This prerequisite is undocumented.
5. Run `just dev desktop`.

For a fresh clone, prepend the README's `just install` and
`just install-local`. I did not rerun those two mutating installation recipes
against the read-only checkout. The installed editable command reported
`0.3.0.post1.dev342+g41a4e2399`.

## Measurement boundary

- Checkout: detached `41a4e2399868a027bfb3a47000c8788db3fc921c`.
- Initial and final tracked state: pristine.
- Product state began empty. There was no channel home, settings file, or
  channel database.
- `HOME`, `TRANSPORT_MATTERS_HOME`, `TMPDIR`, the tmux socket, Electron user
  data, caches, and logs were confined beneath
  `/private/tmp/tm-onboarding-walk.hphJX2`.
- Database proof used an owned PostgreSQL 18 cluster bound only to
  `127.0.0.1:55439`. The owned `transport_matters_dev` database was dropped,
  and the cluster was stopped.
- No existing `transport_matters`, `transport_matters_preview`, or
  `transport_matters_dev` database was created, altered, migrated, or dropped.
- No real channel home, `~/Library` path, Keychain item, or preferences domain
  was touched.

## Walls in documented order

### 1. README verification runs before setup

Command:

```text
transport-matters doctor
```

Exit status: 1. Surfaced error:

```text
  fail  session store
        set TRANSPORT_MATTERS_DATABASE_URL, or add [database] url to settings.toml under the channel home (default ~/.transport-matters); a starter is created from settings.example.toml on first launch

1 check(s) failed: session store
```

This was not a traceback. The message names the missing database configuration
and the two configuration forms. It does not name the launch command that
creates the starter. A newcomer must skip the README's verification command,
read ahead into QUICKSTART, and know that a failing doctor is expected before
the documented setup.

Unblocked by: continuing to QUICKSTART despite the failed verification.

### 2. QUICKSTART configuration has no executable bootstrap step

QUICKSTART says that first launch writes
`~/.transport-matters/settings.toml`, but it does not identify a first-launch
command in the configuration step. At this point the file does not exist.
For `dev`, the actual path is `~/.transport-matters-dev/settings.toml`.

This is a documentation silence rather than a command failure. A newcomer must
already know which launcher materializes settings, which channel flag to give
it, and that the first attempt may fail after creating the file.

Unblocked by: following `docs/CHANNELS.md` to `just dev desktop`.

### 3. The documented dev command requires undocumented tmux

Command from a normal shell:

```text
just dev desktop
```

Exit status: 2. Exact surfaced error:

```text
"/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/channels/scripts/local-dev-mode.sh" desktop /Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/channels
error: not inside tmux
```

This was not a traceback. The message names the immediate cause. It gives no
installation or invocation command. README, QUICKSTART, CHANNELS, and the root
justfile do not state that tmux is a prerequisite. A newcomer must already have
tmux installed and know how to enter a session.

Unblocked by: starting an owned private tmux server and rerunning the command.

### 4. The dev harness reaches the session store before settings or database bootstrap

Command inside tmux, still with no channel home, settings, or dev database:

```text
just dev desktop
```

The backend pane exited with status 2. The exact surfaced error began:

```text
error: cannot reach the session store at the configured URL: connection failed: connection to server at "127.0.0.1", port 55432 failed: FATAL:  database "transport_matters_dev" does not exist
Multiple connection attempts failed. All failures were:
- host: 'localhost', port: '55432', hostaddr: '::1': connection failed: connection to server at "::1", port 55432 failed: could not receive data from server: Connection refused
- host: 'localhost', port: '55432', hostaddr: '127.0.0.1': connection failed: connection to server at "127.0.0.1", port 55432 failed: FATAL:  database "transport_matters_dev" does not exist
Transport Matters records sessions in a Postgres store. Set one up, then relaunch:
  - Local or cloud Postgres: point Transport Matters at it
      export TRANSPORT_MATTERS_DATABASE_URL=postgresql://USER:PASS@HOST:PORT/DBNAME
      (or edit [database] url in settings.toml under the channel home, default ~/.transport-matters)
  - Docker (local dev): from the repo root run
      docker compose up -d
      (the scaffolded settings.example.toml URL targets this database)
See QUICKSTART.md for the full setup.
```

This was not a Python traceback. It names the real cause, the absent
`transport_matters_dev` database. Its cures do not work for this state:

- Docker was already running.
- `just dev desktop` deliberately removes
  `TRANSPORT_MATTERS_DATABASE_URL`.
- No settings file was created by this command.
- The message does not name `transport-matters channel ensure-db dev`.

Gateway and Vite started concurrently. Activity was disabled because the
gateway had no database URL. Electron waited for backend health and did not
start. A newcomer must know that the channel database has to be created before
the documented dev command, despite QUICKSTART saying launch applies the schema
automatically.

Unblocked by: trying the documented channel database command.

### 5. The documented database bootstrap command is itself blocked

Command:

```text
transport-matters channel ensure-db dev
```

Exit status: 2. Exact surfaced error:

```text
error: set TRANSPORT_MATTERS_DATABASE_URL, or add [database] url to settings.toml under the channel home (default ~/.transport-matters); a starter is created from settings.example.toml on first launch
```

This was not a traceback. It hits the same configuration resolution wall as
reset. It names the missing configuration and two possible forms, but it does
not name the command that creates the starter or explain the required ordering.
It creates neither the settings file nor the database.

Unblocked by: continuing through the remaining documented channel commands,
then deliberately probing the public desktop launcher.

### 6. The documented safe reset produces a raw traceback

Command:

```text
just reset
```

Exit status: 1. Exact surfaced error:

```text
"/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/channels/scripts/reset-channel-store.sh" --channel dev
Traceback (most recent call last):
  File "<stdin>", line 33, in <module>
  File "/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/channels/api/src/transport_matters/config.py", line 220, in resolve_database_url
    raise MissingDatabaseConfigError(DATABASE_URL_GUIDANCE)
transport_matters.config.MissingDatabaseConfigError: set TRANSPORT_MATTERS_DATABASE_URL, or add [database] url to settings.toml under the channel home (default ~/.transport-matters); a starter is created from settings.example.toml on first launch
error: config resolution failed (channel=dev); is the api venv set up?
```

This is a raw Python traceback. The exception names the actual missing
configuration. The shell wrapper adds an inaccurate virtual environment hint.
Neither output names the starter creator. A newcomer must understand that reset
resolves the database URL before it can reset an absent channel.

Unblocked by: no documented reset action. The bootstrap probe below was
required.

### 7. The public desktop launcher creates settings and fails in the same run

Command:

```text
transport-matters desktop --channel dev
```

Exit status: 1. Exact outer error:

```text
error: desktop backend exited before it became ready on http://127.0.0.1:8808 with exit code 2. Inspect logs with `transport-matters tail dev` or read /private/tmp/tm-onboarding-walk.hphJX2/normal-base/.transport-matters-dev/runtime/desktop.log.
```

This command created
`.transport-matters-dev/settings.toml` from the packaged template before the
backend failed. The outer error does not name the cause. The referenced log
contains the session store error from wall 4 and reports that
`transport_matters_dev` does not exist.

The generated starter points at:

```toml
[database]
url = "postgresql://tm:tm@localhost:55432/transport_matters"
test_url = "postgresql://tm:tm@localhost:55432/postgres"
```

Its comments list stable and preview channel defaults but omit dev. The
configured server URL is rewritten to the dev database name at runtime.

Unblocked by: using the now-existing settings file, then rerunning
`transport-matters channel ensure-db dev`.

## Proven working sequence

The isolated proof used a nonstandard private PostgreSQL port, so I changed
only the sandbox starter URLs from port 55432 to 55439. Then:

```text
$ transport-matters channel ensure-db dev
database transport_matters_dev: created
session store at head (0032_space_worktree_ownership)
```

Database inspection returned only `postgres` and `transport_matters_dev`, and
the latter reported Alembic revision `0032_space_worktree_ownership`.

After entering tmux, `just dev desktop` produced all four live panes. The
backend completed startup, `GET /health` returned `{"status":"ok"}`,
`GET /api/meta` reported `"channel":"dev"`, the gateway listened on 18789,
Vite returned HTTP 200 on 15173, and Electron ran with:

```text
--user-data-dir=/private/tmp/tm-onboarding-walk.hphJX2/normal-base/.transport-matters-dev/electron-user-data
```

## Hand edit requirement

No hand edit is required for QUICKSTART's exact local Docker server on port
55432 after a launcher has created the starter. A different Postgres server
requires a hand edit for the local desktop development path because
`just dev desktop` removes `TRANSPORT_MATTERS_DATABASE_URL`.

QUICKSTART says to edit `~/.transport-matters/settings.toml` for a different
database and also says the environment variable wins. CHANNELS separately says
the dev home is `~/.transport-matters-dev` and that the dev harness removes the
database and home overrides. No document combines these facts into the required
dev instruction: edit
`~/.transport-matters-dev/settings.toml` before running the dev harness.

## Session store gate position

The session store gate runs after the public launcher materializes settings but
before backend readiness and before Electron opens. In the local tmux harness,
the backend gate runs concurrently with gateway and Vite startup. Backend
failure prevents Electron from starting. The gate does not provision the
channel database, despite QUICKSTART's statement that launch applies the schema
automatically.

## Smallest changes that make the documented path complete

Ranked by the earliest blocker:

1. Put setup before verification in README, or make `doctor` treat absent
   first-run database configuration as a guided setup state. Name the exact
   next command and channel settings path.
2. Make `channel ensure-db <channel>` materialize the channel starter before
   resolving its URL. This removes the configuration cycle for both initial
   database creation and reset.
3. State the tmux prerequisite and provide an exact command before
   `just dev desktop`.
4. Make the dev launch sequence run the database bootstrap before backend
   startup, or document the required starter, ensure-db, tmux, launch order
   verbatim.
5. Reconcile custom database instructions with the dev harness policy. Either
   preserve an explicit database override or document the exact dev settings
   file that must be edited.
6. Catch missing configuration in reset and report a concise setup action.
   An absent disposable channel must not surface a traceback.
