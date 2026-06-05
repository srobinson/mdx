# PR 294 adversarial review: S2c observations, probes, and connections

Reviewed `main...feat/s2c-observations-probes-connections` at
`43ba3ce3cd58be305e500b0e1be7010437db7a66` against the S2c brief,
`RUNTIME-SURFACING-S2-PLAN.md`, `HARNESS-COMPATIBILITY.md`, `AGENTS.md`,
`LESSONS.md`, and `api/CLAUDE.md`.

Verdict: 2 Blockers, 4 Majors, 2 Minors.

## Blockers

1. **Ambient credentials cross the connection isolation boundary.**
   `api/src/transport_matters/harnesses/probes/runner.py:57-65` copies the complete
   base environment and removes only `CLAUDE_CONFIG_DIR` and `CODEX_HOME` before
   launching the probe. Repository evidence confirms that
   `CLAUDE_CODE_OAUTH_TOKEN` is an active inherited authentication input. A probe
   for a managed connection can therefore authenticate through the parent token
   instead of the selected home. The isolation fixture contains home paths but no
   credential variable, so it cannot detect this bleed.

   [Probe environment](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/probes/runner.py#L50-L65)
   [Isolation fixture](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/probes/test_runner.py#L35-L49)
   [Inherited Claude token precedent](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/cli/test_start_children.py#L68-L85)

2. **The redaction guarantee is conventional rather than structural.**
   `AuthenticationEvidence` and `LocalHarnessAccessObservation` expose unrestricted
   `authentication_method` and `reason` strings, and the store writes those fields
   directly to Postgres. A parser or caller can persist raw output or a credential
   verbatim. The blocker test manually copies fields from one safe Codex parser into
   the persistence model, so it does not exercise an owned conversion boundary.
   The sanitized `evidence_digest` is also discarded before persistence, leaving no
   auditable link to the capture that produced the row.

   [Authentication evidence shape](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/probes/__init__.py#L40-L50)
   [Persisted access shape](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/connections.py#L129-L145)
   [Direct store write](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/connections_store.py#L115-L135)
   [Tautological persistence test](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/probes/test_runner.py#L177-L211)

## Majors

1. **Access evidence is not integrity bound to the selected connection and route.**
   The access table foreign key checks `connection_id` only, while executor, harness,
   route, and revision can disagree. Connection upsert can move the same stable id
   across those scopes without invalidating child evidence. The runner checks only
   the harness, and the adapters accept route incompatible methods. For example, an
   API key Codex login can become authenticated evidence for
   `codex.chatgpt.oauth`, silently changing the credential and billing path.

   [Access table constraint](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/migrations/versions/0022_harness_executor_tables.py#L95-L120)
   [Mutable connection identity](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/connections_store.py#L38-L52)
   [Harness only runner check](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/probes/runner.py#L91-L102)
   [Route incompatible Codex methods](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/probes/codex.py#L31-L51)

2. **Older writes can replace newer connection and observation state.**
   Every conflict update is unconditional. Lower connection revisions and earlier
   `observed_at` values can overwrite newer rows when asynchronous probes or writers
   finish out of order. Reads then expose the remaining row as latest. Rolling a
   connection back can also make old access evidence match the current revision
   again.

   [Connection upsert](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/connections_store.py#L38-L52)
   [Harness observation upsert](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/connections_store.py#L84-L101)
   [Access observation upsert](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/connections_store.py#L115-L135)
   [Target observation upsert](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/connections_store.py#L150-L169)

3. **Target persistence cannot represent complete catalog snapshots.**
   The store upserts one row per model with no snapshot identity, atomic batch, or
   reconciliation of omissions. After a complete refresh changes from `{A, B}` to
   `{A}`, row `B` remains and is still returned. Complete evidence therefore cannot
   establish disappearance as required by the contract. A crash or read during a
   multi model refresh can also expose a mixed snapshot.

   [Per model target upsert](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/connections_store.py#L150-L176)
   [Single row write API](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/connections_store.py#L218-L222)
   [Read returns all retained rows](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/connections_store.py#L251-L258)
   [Completeness contract](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/HARNESS-COMPATIBILITY.md#L453-L486)

4. **The Codex adapter ignores the exit code that its contract declares evidence.**
   Recognized text always wins. Exit 2 with `Logged in using ChatGPT` returns
   `authenticated`, while exit 0 with `Not logged in` returns `login_required`.
   Failed or drifted invocations can therefore produce authoritative state instead
   of degrading to unknown. The tests cover unexpected text with several codes but
   omit contradictory recognized text and exit code pairs.

   [Codex parser](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/probes/codex.py#L39-L63)
   [Missing contradictory fixtures](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/probes/test_codex.py#L59-L74)

## Minors

1. **The focused migration test does not seed the prior revision before upgrade.**
   `test_db` starts at head, the test inserts only after 0022 exists, then downgrade
   drops every seeded row before the reupgrade. The requested 0021 seed, upgrade,
   constraint, and downgrade proof is absent. This is lower risk because 0022 is
   additive, but the test does not prove the brief's existing database path.

   [Head first setup](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/session/test_harness_executor_tables_migration.py#L118-L126)
   [Downgrade then empty reupgrade](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/session/test_harness_executor_tables_migration.py#L201-L211)

2. **The new pure leaf lacks the required fresh interpreter import guard.**
   `connections.py` explicitly declares itself a pure leaf, while `LESSONS.md`
   requires every new neutral seam to prove a fresh subprocess import. The PR adds
   only in process imports, so pytest collection order can still hide a cycle.

   [Pure leaf declaration](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/api/src/transport_matters/harnesses/connections.py#L1-L7)
   [Fresh import rule](https://github.com/littleorgans/transport-matters/blob/43ba3ce3cd58be305e500b0e1be7010437db7a66/LESSONS.md#L307-L313)

## Verified scope

- The tree was clean on `feat/s2c-observations-probes-connections` at the exact PR
  head before verdict.
- The 25 changed files total 3,989 current lines. The largest is 638 lines, so no file
  crosses the 700 line guardrail.
- Migration 0022 is additive, uses frozen enum checks, drops only its five tables,
  updates reset and head state, and has roundtrip present and absent assertions.
- `connections.py` remains free of I/O, store I/O stays in `connections_store.py`,
  probe execution uses `asyncio.to_thread` with a timeout, and no startup hook exists.
- Executor block behavior remains DDL only. `match_release` remains uncalled in
  production. No inventory, REST, activation, or launch gating leaked into S2c.
- Codex version extraction delegates to the shared observation owner while the
  `0.0.0` sentinel and mtime cache remain local.
- No gates were run by this reviewer, per the shared tree brief.

Craftsmanship verdict: Clear ownership and controlled file sizes, with ship blocking gaps at the credential, evidence integrity, and catalog snapshot boundaries.
