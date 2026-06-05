# PR #299 adversarial review

Scope: `main` `10e922fbbf0414510d62e8d51b7a5c1f1021af62` through `feat/s2f-resolver-gating-setup` `5e1c4eea5e209ed739ea16ca20f9941c75be2912`, 28 files, 2,783 additions, 324 deletions. The review covered only this diff and the named contracts.

## Findings

### Blocker

1. Advisory launch preparation can stall indefinitely on PostgreSQL statements.

   The gate performs the active block read and audit writes synchronously before `prepare_launch()` returns. `GATE_CONNECT_TIMEOUT_S` reaches psycopg only as `connect_timeout`, which bounds connection establishment. The subsequent `SELECT`, audit `INSERT` operations, and transaction commit have no statement, lock, socket, or whole operation deadline. A connected store waiting on a lock or stalled after handshake can therefore hold capture RPC, Claude CLI, and Codex CLI launch preparation forever. The broad exception handler cannot run until the blocked operation returns.

   Evidence: [compatibility_service.py:242](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/compatibility_service.py#L242-L290), [pool.py:123](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/session/pool.py#L123-L141), [audit.py:151](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/controlplane/audit.py#L151-L176). This violates the live launch guarantee documented at [compatibility_service.py:311](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/compatibility_service.py#L311-L321).

   Required correction: bound each read, write, and commit across the complete gate operation, then prove a locked or unresponsive connected store still allows advisory launch preparation to return. The current tests replace the store and audit writer with fakes and do not cover the named manifest, database, probe timeout, and artifact failure cases independently.

### Major

2. Every production compatibility fact records `executable_identity=null`.

   `_observe()` passes the resolved path into `build_harness_observation()` without its `executable_identity` argument. The default is `None`, and `compatibility_fact_artifact()` copies that value into the frozen artifact. Every successful production gate therefore loses the exact binary identity. The run cannot prove that the probed executable is the one later actuated, and historical facts cannot identify the executable they certify.

   Evidence: [compatibility_service.py:153](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/compatibility_service.py#L153-L168), [compatibility_facts.py:139](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/compatibility_facts.py#L139-L153), `HARNESS-COMPATIBILITY.md:372-379` and `HARNESS-COMPATIBILITY.md:570-579`.

3. The resolver accepts access and target evidence outside the pinned executor, release, or harness version.

   `ResolverSnapshots._validate_scopes()` checks only `harness_id`. `_access_evidence()` selects by connection id and checks route plus connection revision. `_target_evidence()` selects only by native model id. The resolver never binds these rows to `snapshots.executor_id`, the active `compatibility_release_id`, or the observed harness version. Persisted evidence naturally survives release activation and binary upgrades until a later probe replaces it, so old successful evidence can authorize and be frozen into a new resolution.

   Evidence: [resolver.py:110](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/resolver.py#L110-L132), [resolver.py:283](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/resolver.py#L283-L336), [connections_store.py:139](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/connections_store.py#L139-L196). This violates the complete tuple and current evidence requirements in `LAUNCH-CONTRACT.md:156-182` and `HARNESS-COMPATIBILITY.md:318-380`.

4. Omitted connection selection computes ambiguity from registered connections rather than ready connections.

   `_select_connection()` sends every registered connection to `resolve_connection()` before access evidence is evaluated. With two registered connections and only one authenticated, access available connection, the resolver returns `connection_ambiguous`. The contract requires the sole ready connection to resolve and reserves ambiguity for several ready connections. The added test at `test_resolver.py:193-202` encodes the contrary behavior.

   Evidence: [resolver.py:248](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/resolver.py#L248-L267), [resolver.py:462](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/resolver.py#L462-L473), `LAUNCH-CONTRACT.md:176-178`.

5. Target tuple readiness is not enforced for explicit targets or effort selection.

   `_validate_explicit_edge()` accepts a target when `_target_evidence()` returns `None`. A complete target snapshot represents confirmed removal by deleting omitted rows, so explicit selection can resurrect a target the latest complete observation marked unavailable. When evidence exists, readiness checks only `status == "ok"`; the resolver never verifies the requested or default effort against `LocalTargetObservation.native_efforts`. It can return a model and effort tuple that complete local evidence says cannot be actuated.

   Evidence: [resolver.py:318](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/resolver.py#L318-L336), [resolver.py:397](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/resolver.py#L397-L435), [resolver.py:475](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/resolver.py#L475-L518), [connections_store.py:199](https://github.com/littleorgans/transport-matters/blob/5e1c4eea5e209ed739ea16ca20f9941c75be2912/api/src/transport_matters/harnesses/connections_store.py#L199-L229). This violates `HARNESS-COMPATIBILITY.md:441-486` and `LAUNCH-CONTRACT.md:175-181`.

## Craftsmanship verdict

Strong decomposition and reuse, blocked from merge by incomplete live launch safety and resolver authority invariants. All 28 changed files remain below 700 lines, no introduced function exceeds about 150 lines, and the Codex trust extraction plus shared store row validation reduce duplication cleanly.

## Review protocol note

No project tests, builds, type checks, migrations, checkout, or branch switch were run by the primary reviewer. One delegated history pass inadvertently ran a targeted read only `git diff --check` on `resolver.py`; it returned clean and made no filesystem changes.
