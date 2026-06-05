---
title: Transport Matters Channel DB Lifecycle Slice 3
type: sessions
tags: [backend, transport-matters, channels, cli, postgres, justfile]
summary: Implemented channel list, ensure-db, promote code path, and preview channel restart recipe.
status: active
source: backend-engineer
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Summary

Implemented slice 3 of the Transport Matters channels plan on branch `feat/channels`.

Commit: `aef4e922b739b554bd81d4d12c52e130f973cbe6`.

Key decisions:

- Added `transport-matters channel` as a Typer subcommand group beside the existing `db` app.
- Added channel database lifecycle commands without fabricating a database URL. The command requires `TRANSPORT_MATTERS_DATABASE_URL` or `[database]` configuration.
- Reused the configured Postgres server URL, swapped only the database name, created missing channel databases through the `postgres` maintenance database, then ran the existing migration path.
- Kept `promote preview stable` code only. It runs the same local install path as stable and never copies or rewrites data.
- Added root `just channel-restart channel="preview"` to build web, build desktop, ensure the channel database, then launch the requested desktop channel.

## API Contract

No HTTP API contract changed in this slice.

CLI contract added:

```text
transport-matters channel list
```

Prints a table with channel id, home, database name, proxy port, web port, app name, and badge.

```text
transport-matters channel ensure-db [channel]
```

Resolves the channel from the argument, `TRANSPORT_MATTERS_CHANNEL`, or stable default. Requires an explicit configured database server URL. Creates the channel database if absent with `psycopg.sql.Identifier`, applies session migrations to that channel URL, and prints whether the database was created or already existed plus the migration head.

```text
transport-matters channel promote preview stable
```

Runs root `just install-local` and prints the stable desktop launch command. Other argument pairs are rejected.

Justfile contract added:

```text
just channel-restart channel="preview"
```

Runs the web build, desktop build and Electron install, channel database ensure step, then launches `transport-matters desktop --channel {{channel}}` with `TRANSPORT_MATTERS_CHANNEL` set.

## Database Changes

No schema migration was added.

Runtime database lifecycle changed:

- New helper `database_url_with_database_name` centralizes safe database name replacement.
- Channel database creation connects to the same configured server using maintenance database `postgres`.
- Existence checks use parameterized queries against `pg_database`.
- Database creation uses `psycopg.sql.Identifier` for the database identifier.
- Existing `session.migrate.apply_migrations` remains the only migration path, preserving advisory lock behavior.

## Security Considerations

- The command fails closed when no explicit database server URL is configured.
- No default or fabricated Postgres URL is introduced.
- SQL values use parameters. The database identifier uses `psycopg.sql.Identifier`.
- Promotion does not copy data between channel databases.
- The launch preflight remains strict. The new ensure command makes the configured channel satisfy the existing preflight instead of relaxing it.

## Performance Notes

- `ensure-db` does one `pg_database` existence probe before database creation.
- Existing migration advisory locking handles concurrent migration attempts.
- No request path or server runtime hot path changed.

## Verification

- `cd api && just test src/transport_matters/cli/test_channel_cmd.py src/transport_matters/cli/test_launch_preflight.py`: 10 passed in 0.40s.
- `cd api && just ci`: 1636 passed in 45.84s, including migration smoke 7 passed.
- `cd api && just check`: ruff format, ruff check, and mypy passed.
- `git diff --check`: exit 0.
- `fmm validate`: all 847 indexed files up to date.
- `git status --short --branch`: clean on `feat/channels` after commit.

## Open Items

- Later slices own desktop dock naming, app badging, and any channel specific polish outside this database lifecycle slice.
