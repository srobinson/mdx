# PR #259 review: wire store write path

Reviewed branch `wire-store-pr2-write-path` at `deb25b0e3c348c7efaa825ddfcf1d31e9e906c93` against `tm-http-store-spec.md` sections 1, 2, 4, 7, and 8 PR 2. Base: `9f2a3f6e4c99a9c053f1da2cd6d954031c86ee8f`.

## Verdict

Changes requested. Four findings exceeded the 80 confidence threshold.

### HIGH, confidence 100: Codex wire rows use the wrong session key

`api/src/transport_matters/wire_store_observer.py:make_wire_store_sinks.on_exchange` assigns `request_ir.metadata.session_id` directly to `wire_exchange.session_id`. For Codex this value is the native thread UUID. `api/src/transport_matters/addon_runtime.py:_wire_session_id` and `api/src/transport_matters/index/adapters/codex.py:CodexAdapter.bind` instead persist `synth_session_id(run_id, "codex", native_session_id)` as `"session".session_id`.

The values differ for every correlated Codex exchange. A live fixture check produced `native=2195537d-1c16-48b2-8caf-b3ed784564d8`, `synthesized=e80e32ad-e846-5e38-b5f6-84e3982039ec`, and `equal=False`. This breaks the schema section 6 soft join contract.

### HIGH, confidence 94: Wire submissions are not drained before writer shutdown

`api/src/transport_matters/wire_store_observer.py:make_wire_store_sinks` discards both futures returned by `asyncio.run_coroutine_threadsafe`. `api/src/transport_matters/addon_runtime.py:close_capture_runtime` drains transcript dispatcher and run lifecycle work, then closes `SessionWriter`, with no retained wire tasks to drain.

A finalized tier 1 exchange emitted shortly before normal shutdown can remain queued, race the pool close, or be cancelled when the loop stops. PR #196 fixed the same fire and forget ownership defect for run lifecycle tasks by retaining and draining them before `writer.aclose()`.

### HIGH, confidence 90: Dedicated capture notifications lose their workspace identity

`api/src/transport_matters/addon_runtime.py:load_capture_runtime` builds a complete `ProxyRunBinding`, then calls `_start_session_capture` without a `binding_for_run_id` resolver. `api/src/transport_matters/wire_store_observer.py:make_wire_store_sinks.resolve_run` therefore returns `(None, None, None)` for every dedicated capture.

These writes persist `wire_exchange.harness = NULL` and publish `workspace_slug = NULL` plus `workspace_hash = NULL`, despite the locked section 4 observer contract requiring the available binding fields in the typed notification payload.

### MEDIUM, confidence 92: Manual GC can corrupt a concurrent exchange write

`api/src/transport_matters/session/wire_store.py:sweep_wire_store` executes three statements in one default `READ COMMITTED` transaction. `api/src/transport_matters/session/dao_statements.py:DELETE_ORPHANED_WIRE_SET_MEMBERS_SQL` deletes members using the absence of a committed exchange, while `api/src/transport_matters/session/wire_store.py:_ensure_component_set` reads existing members without locking them.

A writer can read an orphan set, GC can delete its members, the writer can commit a new exchange reference, and GC's next statement can see that exchange and preserve the now empty set. The resulting live exchange cannot reconstruct its system or tools list. This contradicts `api/src/transport_matters/cli/db_cmd.py:wire_gc`, which advertises the command as safe to run any time.

## Confirmed contracts

- Migration 0008 follows the 0007 Alembic pattern, adds exactly the six specified tables and three indexes, preserves the specified primary keys, checks, foreign keys, and `run_id NOT NULL`, and makes no destructive change to an existing table.
- `SessionWriter.submit_wire_exchange` is additive to transcript and backfill behavior. The complete wire write and notification share one connection transaction. Blob and component set writes are insert if absent. Exchange replay upserts the exchange and replaces manifests and response blocks in the same transaction.
- `SessionWriter.submit_wire_exchange_deleted` treats a missing exchange as a successful no op.
- No reader, API, gateway, IR, adapter, response parser, ingest, `pgContracts`, run lifecycle, recorder persist path, or `docs/ARCHITECTURE.md` change appears in the PR delta.
- `fmm validate` passed for all 1098 indexed files. New production files are below 700 lines, `addon_runtime.py` is 654 lines, `writer.py` is 532 lines, and no changed production function approaches 150 lines.

## Verification

- `git diff --check` passed.
- 22 pure normalization, notification, and observer tests passed with bytecode and pytest cache writes disabled.
- Database backed tests could not run locally because no Transport Matters test database URL is configured. The attempted suite reported 28 passing tests and 30 setup errors, all with `MissingDatabaseConfigError` before test bodies ran.
- PR eligibility was rechecked after review. It remained open, non draft, human authored, with no comments or reviews. Local and remote heads matched the pinned SHA.
- The repository worktree was pristine before review and remained pristine after verification.
