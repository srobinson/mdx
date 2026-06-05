---
title: Embedded-Postgres-for-Python landscape for Transport Matters (drop docker)
type: research
tags: [transport-matters, postgres, embedded, pglite, pgembed, psycopg]
summary: pgembed is the only confirmed Postgres 17 + full-wheel option; pg0-embedded is the runner-up; PGlite dismissal is correct.
status: active
source: quick-research
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Embedded Postgres for Transport Matters: dropping the docker dependency

## Context

Transport Matters is a single-user local tool: Python FastAPI + a psycopg 3 async
connection pool, plus a dedicated long-lived connection running `LISTEN/NOTIFY`. It
currently requires docker-compose **Postgres 17**. Goal: drop docker, keep a real
Postgres server, no sudo, no system service. This is a research memo, not implementation.

## Recommendation (TL;DR)

- **Use `pgembed` (Ladybug-Memory).** It is the only surveyed package that ships a
  **confirmed Postgres 17** server as **prebuilt wheels covering every target platform**
  (macOS arm64, Linux x86_64 + aarch64, musl/Alpine, Windows amd64), is actively released
  (v0.2.0, 2026-03-18), and is a thin vanilla fork of the well-trodden `pgserver` lineage,
  so all core server features are intact. Apache-2.0.
- **Runner-up: `pg0-embedded` (MIT, v0.14.2, 2026-05-28).** More recent cadence, wider
  Python floor (`>=3.8` vs pgembed's `>=3.12`), and MIT license. Disqualifier-for-now: its
  bundled Postgres major version is **not stated** in metadata and could not be confirmed as
  17. If you adopt it, verify `SELECT version()` first. No musl wheel.
- **PGlite verdict: the dismissal is CORRECT.** PGlite is JS/WASM only; using it from Python
  means supervising a Node sidecar, and the exact workload (a connection pool *plus* a
  long-lived `LISTEN/NOTIFY` listener) lands squarely in PGlite's "not guaranteed" zone.

## A. Embedded-Postgres-for-Python comparison

All "real server" packages below run a genuine `initdb` + `postgres` process from a pip
install, as the calling user, no docker and no root. The differentiators are **PG version**,
**wheel coverage**, and **maintenance**.

| Package | Real PG server? | PG 17? | Wheels (macOS arm64 / Linux x64 / Linux arm64 / Win) | Core features* | Last release | License | Verdict |
|---|---|---|---|---|---|---|---|
| **pgembed** (Ladybug-Memory) | Yes | **Yes (17)** ✅ verified | ✅ / ✅ / ✅ / ✅ (+musl) | Full vanilla + pgvector | v0.2.0, 2026-03-18 | Apache-2.0 | **RECOMMENDED** |
| **pg0-embedded** | Yes | Unconfirmed (likely 17, theseus/zonky lineage) | ✅ / ✅ / ✅ / ✅ (no musl) + sdist | Full vanilla + pgvector | v0.14.2, 2026-05-28 | MIT | **Runner-up** |
| **pixeltable-pgserver** | Yes | No — caps at **PG 16** (16.8→~16.10) | ✅ / ✅ / ✅ / ✅ (+win arm64) | Full vanilla + pgvector | v0.5.x, into 2026 | Apache-2.0 | Solid but wrong major |
| **pgvenv** (Florents-Tselai) | Yes (compiles from source) | Yes (17.4 via `PGVERSION`) | ❌ none — **sdist only**, needs C toolchain | Full vanilla | v0.1.1, 2025-04-18 | BSD-3 | Not turnkey |
| **pgserver** (orm011) | Yes | No — PG 16.2, **stale** | partial (no Linux arm64) | Full vanilla | v0.1.4, 2024-04 | Apache-2.0 | Use a fork instead |
| **postgresql-wheel** (michelp) | Yes | No — PG 14 era, **abandoned** | ❌ Linux x86/i686 only | Full + PostGIS | 2021-12-29 | Apache-2.0 | Dead, Linux-only |
| **testing.postgresql** | **No** — needs system PG in PATH | n/a | n/a | n/a | v1.3.0, **2016** | — | Disqualified ×2 |

\* Core features verified as a checklist: `LISTEN/NOTIFY`, generated columns, GIN +
`tsvector` full-text search, advisory locks, JSONB. Every "Full vanilla" build above is a
standard Postgres compile with **nothing stripped** — these are core-server features, not
optional. The presence of bundled `pgvector` (pgembed, pg0-embedded, pixeltable-pgserver)
is positive evidence of a complete build with contrib/extensions rather than a minimal one.

### The fork lineage matters

`michelp/postgresql-wheel` → `orm011/pgserver` → forked into both
`pixeltable-pgserver` (Pixeltable, caps at PG 16) and `pgembed` (Ladybug-Memory, PG 17).
pgembed is the newest, most-maintained branch of this tree and the only one targeting PG 17.
This shared heritage de-risks pgembed: the binary packaging approach is proven, and the
build is vanilla.

### Why pgembed over pg0-embedded

Both are docker-free, pip-only, pgvector-bundling embedded servers. pgembed wins on the one
fact that matters most here: **its bundled Postgres major version is confirmed 17** (the PyPI
description carries a `PostgreSQL-17` badge), matching the current docker-compose target
exactly, so it is a like-for-like swap. pg0-embedded does not publish its PG version and
could not be confirmed as 17. pg0-embedded's advantages (MIT license, `>=3.8` Python floor,
most-recent release, an sdist fallback) make it the right runner-up and the fallback if
pgembed's `>=3.12` Python floor or single-maintainer status becomes a problem.

## B. Adversarial check: "PGlite is the wrong fit for a Python psycopg backend"

**Verdict: the dismissal is CORRECT. But if it was justified with "PGlite only allows one
connection," that justification is now stale** — PGlite v0.4 (March 2026) added a
multiplexer. The correct reasons to reject it are the runtime mismatch and the unverified
`LISTEN/NOTIFY`-over-multiplexer behavior.

1. **JS/WASM only — confirmed.** PGlite is a WASM Postgres build packaged as a
   TypeScript/JS library for browser, Node, Bun, Deno. There is **no native Python binding**.
   Using it from Python requires hosting it in a Node (or Bun/Deno) process. This defeats the
   stated goal: you would not remove a daemon, you would **swap the docker daemon for a
   long-lived Node sidecar** your Python app must spawn, supervise, and keep alive. The
   simplicity win is largely illusory.

2. **psycopg can connect — in principle, via a bridge.** `@electric-sql/pglite-socket`
   (`PGLiteSocketServer`) speaks the Postgres wire protocol over TCP/unix socket; a Node
   process hosts PGlite + the socket server and Python connects as a normal wire client.
   Caveats: **no SSL** (`PGSSLMODE=disable` required); the docs validate only `psql`,
   `node-postgres`, `postgres.js` — **psycopg is not on the tested list**; and the bridge is
   `~0.0.x` immature.

3. **Single-connection — was, until v0.4.** PGlite runs Postgres in single-user mode (one
   backend). v0.4 added a multiplexer (`--max-connections`, default 1) so a psycopg *pool*
   is no longer categorically impossible. But the maintainers warn verbatim that multiplexed
   connections are *"different from a normal Postgres installation, so not all use cases are
   guaranteed to work."* Session-scoped state — `LISTEN` registrations, advisory locks, temp
   tables, GUCs — all sit over one shared backend, which is exactly Transport Matters'
   hardest requirement: **a dedicated long-lived `LISTEN/NOTIFY` listener alongside a pool.**
   No source confirms async `NOTIFY` propagates to an external wire client across the
   multiplexer. The Supabase team evaluated this same multiplex-over-one-PGlite pattern for
   Live Share and concluded it was "a bad idea."

**Steelman (then rejected):** a single-user, low-concurrency local tool over plain SQL
*could* run a small psycopg pool through pglite-socket on a unix socket. But the deciding
reasons stand: (1) Node-runtime dependency makes it lateral, not simpler; (2) pool + separate
long-lived LISTEN/NOTIFY connection is the maximally adversarial case for a single-backend
multiplexer, with NOTIFY-to-external-client unverified; (3) `0.0.x` bridge, no SSL, no
psycopg validation. **A real embedded Postgres binary (pgembed) preserves true psycopg
semantics — independent connections, working LISTEN/NOTIFY, GIN/tsvector, advisory locks —
with no Node dependency.** That is strictly the better docker-free path.

## Top risks (for the recommended path, pgembed)

1. **Python floor `>=3.12`.** Confirm the `api` package's `requires-python` and runtime are
   already 3.12+. If pinned lower, this blocks pgembed and pushes you to pg0-embedded
   (`>=3.8`). Verify before committing.
2. **Young, single-maintainer project (v0.2.0, ~298 commits, first half 2026).** Bus-factor
   risk. Mitigated by: thin vanilla fork of the proven pgserver lineage, Apache-2.0
   (forkable), binaries from the theseus-rs/zonky embedded-binaries ecosystem. pg0-embedded
   is the standing fallback.
3. **No sdist.** If a future deploy platform lacks a wheel, there is no source-build fallback
   (pg0-embedded ships an sdist). Current targets — macOS arm64 dev, Linux x86_64/arm64
   deploy — are all covered, so low risk today.
4. **Operational model shift.** The embedded server is process-resident and single-user
   oriented (fine for this tool), not a shared service. App code barely changes: it still
   connects to a real PG over host:port/socket, so the psycopg async pool + LISTEN/NOTIFY
   listener work unchanged. Lifecycle (initdb-on-first-run, start/stop with the app) is the
   new surface to own.
5. **PG minor-version tracking.** Confirm pgembed tracks current 17.x for security patches;
   pin/update deliberately.

## Sources

- pgembed: https://github.com/Ladybug-Memory/pgembed , https://pypi.org/pypi/pgembed/json
- pg0-embedded: https://pypi.org/pypi/pg0-embedded/json , https://pypi.org/project/pg0-embedded/
- pixeltable-pgserver: https://pypi.org/pypi/pixeltable-pgserver/json , https://github.com/pixeltable/pixeltable-pgserver
- pgserver (orm011): https://github.com/orm011/pgserver , https://pypi.org/pypi/pgserver/json
- pgvenv: https://github.com/Florents-Tselai/pgvenv , https://pypi.org/pypi/pgvenv/json , https://tselai.com/pgvenv
- postgresql-wheel: https://github.com/michelp/postgresql-wheel , https://pypi.org/pypi/postgresql-wheel/json
- testing.postgresql: https://pypi.org/pypi/testing.postgresql/json
- embedded-binary lineage: https://github.com/zonkyio/embedded-postgres-binaries , https://crates.io/crates/postgresql_embedded
- PGlite: https://pglite.dev/docs/about , https://pglite.dev/docs/pglite-socket , https://electric.ax/blog/2026/03/25/announcing-pglite-v04
- PGlite socket: https://www.npmjs.com/package/@electric-sql/pglite-socket , https://github.com/electric-sql/pglite/tree/main/packages/pglite-socket
- Supabase assessment: https://supabase.com/blog/database-build-live-share , https://github.com/supabase-community/pg-gateway

## Open questions

- pg0-embedded's exact bundled Postgres major version (verify `SELECT version()` before
  treating it as a PG17 fallback).
- Whether Transport Matters' `api` is already on Python 3.12+ (gates pgembed directly).
- pgembed minor-version update cadence relative to upstream Postgres 17.x security releases.
