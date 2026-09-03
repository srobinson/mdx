---
title: "Transport Matters: api/ Subtree Map"
type: projects
tags: [transport-matters, python, backend, architecture, onboarding, capture-pipeline, postgres, mcp, baseline, shared-proxy]
summary: Exhaustive orientation map of the Transport Matters Python backend (api/), covering entry points, module layout, domain invariants, cross-process seams, three end-to-end traces, persistence, concurrency, conventions and landmines.
status: active
project: tm
confidence: medium
source: e97488ea
---

# MAP: `api/` — the Transport Matters Python backend

Orientation for an agent making its first change. Every non-obvious claim carries a
`path:line` citation. **All paths are repo-relative** from the monorepo root:
`api/...` is the Python backend, `packages/...` and `www/...` are the sibling
TypeScript workspaces. A bare directory name in prose (`session/`, `controlplane/`)
means a subpackage of `api/src/transport_matters/`.

Package root: `api/src/transport_matters/`. Build: hatchling, Python 3.14
(`api/pyproject.toml`). ~110k lines of Python across 20 subpackages plus ~200 top-level
modules, roughly half of which are colocated `test_*.py`.

## Confidence and method

**Provenance.** The map was built against `730aaa96` and re-verified against
`e97488ea`. Two commits landed mid-mapping — `feb6d42c` (*feat(runs): register canvas
runs with the shared proxy*) and `e97488ea` (*docs(tldr): a canvas run's proxy is a
binding*) — touching `capture_rpc.py`, `captured/run.py`, `main.py`, `TLDR.md` and
adding `shared_proxy/registration.py`. The citations below are as of `e97488ea`.

**What the re-verification did.** 22 distinct citations were corrected (31
occurrences in the text). 21 of those occurrences were pure line drift into the three
changed Python files, re-derived from fresh function indexes rather than by adding an
offset. The other 10 were my own errors on files that did **not** change — I had
cited a class or function by a line inside its body rather than its `def`
(`session/wire_store.py`, `storage/disk.py`, `ir.py`, `startup_passes.py`,
`controlplane/lifecycle_authority.py`, `session/listen.py`, `flow_state.py`). That
error rate on a hand-built map is the honest reason to treat any single uncorrected
line number as ±3 rather than exact.

**Citations checked: 87.** 60 unchanged-file citations were spot-checked by printing
the exact cited line; every one of the 13 anchors into the three changed files was
re-derived; and the 14 new citations added for the shared proxy were verified as
written.

**Sections re-checked against `e97488ea`:** §1.2 (lifespan step 5, now passing
`shared_proxy` and `breakpoint_skip_models`), §2.4 (module map, `shared_proxy/` row
rewritten and `registration.py` added), §5.1 step 7, the new §5.1a, §10.10a, §11.
Plus the 60-citation spot-check, which spanned §1, §3, §4, §5.2, §5.3, §6, §7, §8
and §10.

**Sections asserted unaffected because their files did not change:** §3 (domain
models), §4.3-§4.7 (Postgres, mitmproxy hooks, sinks, LISTEN/NOTIFY, MCP), §5.2
(trace B end to end), §5.3 (baseline comparison), §6 (persistence and migrations),
§7 (concurrency and ownership), §8 (conventions), §9 (public contract). `git diff
--stat 730aaa96 e97488ea` touches no file cited by any of them. §4.1 and §4.2 are
partly re-checked: the Python ends moved, the TypeScript ends did not.

This map was otherwise built by reading source, not by inferring from names. It is
not uniformly certain, and the gaps below are real.

**Verified on both sides of the seam** (I opened the file on each end and matched
the call to its handler):

- Python to Gateway: `RunRouteProxy.create_run`
  (`api/src/transport_matters/api/v1/run_proxy.py:241`) against
  `packages/runtime/src/server/runtimeRouter.ts:69`.
- Gateway to Python capture RPC: `CaptureRpcClient.prepareCapture`
  (`packages/runtime/src/adapters/CaptureRpcClient.ts:81`) against
  `prepare_capture` (`api/src/transport_matters/api/v1/capture_rpc_routes.py:249`),
  and the failure-rollback `releaseCapture`
  (`packages/runtime/src/service/RunManager.ts:271`) against
  `CaptureLeaseRegistry.release_capture`
  (`api/src/transport_matters/capture_rpc.py:230`).
- PTY spawn: I read `packages/runtime/src/service/RunManager.ts:195-278` directly,
  so the claim that Python never spawns a managed PTY rests on observed code.
- Sink registration to consumption: `api/src/transport_matters/storage/exchange_sink.py`
  against `WireStoreObserver.register`
  (`api/src/transport_matters/wire_store_observer.py:135`) and each of the four
  handlers.
- Disk persist to wire write: `exchange_recorder/__init__.py` emit calls against
  `wire_store_observer.py:_submit_exchange` against
  `session/writer.py:submit_wire_exchange` against
  `session/wire_store.py:write_wire_exchange`.
- Reap authority: `controlplane/lifecycle_reconcile.py:174` against
  `controlplane/lifecycle_authority.py:51` against
  `controlplane/runtime_liveness.py`, and the lock-key name against its sole
  declaration in `session/run_lifecycle_contracts.py:13`.
- The shared-proxy seam: `create_capture_registry`
  (`api/src/transport_matters/capture_rpc.py:431`) against
  `shared_captured_run_preparer`
  (`api/src/transport_matters/shared_proxy/registration.py:190`) against the
  `supervisor_factory` / `proxy_starter` parameters and the `ctx=ctx` call site in
  `_start_captured_attempts` (`api/src/transport_matters/captured/run.py:393`). I
  read `registration.py` in full.
- The two lint tests: I read `test_private_import_boundary.py` and the head of
  `test_type_mirrors.py` and confirmed the roots and mirror targets they actually
  scan, rather than trusting their names.

**Single-read, not cross-checked** (accurate as to what the file says, but I did not
open the other end):

- Trace C (baseline comparison). I read `launch_verification.py`,
  `support_state.py`, `harnesses/launch_target.py` and
  `harnesses/resolver.py` in full, but `baseline_harvest.py`,
  `baseline_capture.py`, `request_schema_comparison.py`,
  `ir_coverage.py` and `transport_envelope.py` I did **not** open. Everything in
  §5.2 (schema minting, envelope projection, coverage classification) beyond the
  coordinator is taken from the project `CLAUDE.md`, which is authoritative prose
  but is not the source. Treat those steps as documented rather than verified.
- The 30-table inventory. Derived by resolving module-level table-name constants
  across all 39 migrations plus reading `0001` in full; I did not read every
  revision body, so a column-level claim about any table other than `session` is
  not backed here.
- The `RunManager` mirror comment about `RuntimeRunState`: I read the Python side
  and its comment, not `packages/runtime/src/domain/runtimeRun.ts`.
- `storage/disk.py`, `flow_state.py` and `live_status_observer.py` were read at the
  head only; their class and constant claims are verified, their method bodies are
  not.
- Line numbers marked `~` in §4.4 (`addon_handlers.py`) are approximate: I located
  those handlers by grep and read their bodies, but did not re-confirm the exact
  first line of each.

**Scale of the read.** Roughly 60 Python files and 4 TypeScript files were opened,
of which about 20 were read end to end and the rest in targeted ranges. Function and
class indexes (`grep -n "^def\|^class"`) were taken for a further ~10 files whose
bodies I did not read; those supply the `file:line` anchors in §5.1 for
`launch_service.py`, `service.py` and `captured/run.py`, so the anchors are real but
the surrounding behavioural descriptions of those functions are lighter than
elsewhere.

**Ran out of budget to check.** The three largest subpackages are essentially
unread: `harnesses/` (23 484 lines, of which I read 4 files), `cli/` (21 600 lines,
1 file), `codex/` (13 888 lines, 0 files). Also unread: `space/` (5 380),
most of `shared_proxy/` (4 128; I read `registration.py` in full, the rest only
from `TLDR.md`), `index/`
(3 292), `supervisor/` (2 113), and most of `controlplane/` (I read 6 of 43
modules). §2's one-line roles for those packages are inferred from module names plus
their importers, which is exactly the inference the mapping brief warned against —
treat every §2 row outside the layers I read as a pointer, not a fact.

**What this means for a first change.** §1, §4, §5.1, §5.2, §6.3, §7 and §10 are the
sections I would act on without re-reading. §2's unread-package rows, §5.3's schema
steps and §3.5's envelope details should be re-verified against source before they
gate a decision.

---

## 0. The one-paragraph model

`api/` is **two cooperating processes and three storage tiers**. A FastAPI app
(`api/src/transport_matters/main.py`) supervises a Node child called the **Gateway**
(`api/src/transport_matters/gateway_supervisor.py:298`) which owns every PTY. Python never spawns a harness
PTY; it *prepares* one and the Gateway spawns it
(`packages/runtime/src/service/RunManager.ts:253`). Alongside that, a **mitmproxy
addon** (`api/src/transport_matters/addon.py`) sits in front of every provider call the harness makes, parses
each request into a provider-neutral IR (`api/src/transport_matters/ir.py`), optionally rewrites it
(`api/src/transport_matters/overrides/__init__.py:156`), persists it to disk (tier 1,
`api/src/transport_matters/exchange_recorder/__init__.py`), and fans it out to observers that mirror it into
Postgres (tier 2, `api/src/transport_matters/session/wire_store.py`). Tier 3 is the harness's own transcript
files, tailed into the store (`api/src/transport_matters/index/tailer.py`). Disk is authoritative; Postgres is
a best-effort observer, and **every Postgres path in the capture pipeline fails
open**.

---

## 1. Entry points and process lifecycle

### 1.1 Executable entry points

| Entry | File | What it starts |
| --- | --- | --- |
| `python -m transport_matters` | `api/src/transport_matters/__main__.py` | delegates to the CLI |
| `tm` console script | `api/src/transport_matters/cli/__init__.py` (typer app) | all operator commands |
| `tm start` | `api/src/transport_matters/cli/start_cmd.py`, `api/src/transport_matters/cli/managed_start.py` | the backend server |
| uvicorn factory | `api/src/transport_matters/uvicorn_runtime.py` (17 lines) | thin `create_app` shim |
| mitmproxy addon | `api/src/transport_matters/addon.py:1` | loaded by the per-run proxy process |
| Desktop shell | `api/src/transport_matters/desktop_runtime.py` (699), `api/src/transport_matters/cli/desktop_cmd.py` | packaged app |

`api/src/transport_matters/uvicorn_runtime.py` exists only so uvicorn's `--factory` string is stable; the real
app builder is `api/src/transport_matters/main.py`.

### 1.2 Backend lifespan (`api/src/transport_matters/main.py`)

`api/src/transport_matters/main.py` (657 lines) is the composition root for the server process. The FastAPI
lifespan does, in order:

1. Resolve `Settings` (`api/src/transport_matters/config.py`, 318 lines) which resolves the **channel**
   (`api/src/transport_matters/channel.py`, 242) — see §6.1.
2. Apply Alembic migrations under an advisory lock (`api/src/transport_matters/session/migrate.py:_upgrade_under_lock`),
   then best-effort `CREATE EXTENSION pg_stat_statements` (`api/src/transport_matters/session/migrate.py`
   `ensure_statement_stats`).
3. Create the async psycopg pool (`api/src/transport_matters/session/pool.py:create_async_pool`).
4. Spawn the Gateway child (`api/src/transport_matters/gateway_supervisor.py:193` plans, `:298` spawns) and
   mount `RunRouteProxy` (`api/src/transport_matters/api/v1/run_proxy.py:94`).
5. Register the capture RPC registry (`api/src/transport_matters/capture_rpc.py:431
   create_capture_registry`), passing `shared_proxy=app.state.shared_proxy_manager`
   and `breakpoint_skip_models` (`api/src/transport_matters/main.py:441-442`). With a
   shared proxy the registry's `prepare_run` becomes
   `shared_captured_run_preparer(...)`
   (`api/src/transport_matters/shared_proxy/registration.py:190`); without one it
   falls back to bare `prepare_captured_run` and logs
   `"shared proxy unavailable; captured runs start a proxy each"` **once**
   (`api/src/transport_matters/capture_rpc.py:445-446`).
6. Launch three **fire-and-forget startup passes** (`api/src/transport_matters/startup_passes.py`) that are
   never awaited by startup and are cancelled before the pool closes.

The three passes and their teardown order are declared once, in
`api/src/transport_matters/startup_passes.py:45 _PASS_TASKS`:

```python
_PASS_TASKS = (
    ("harness access verification", "harness_access_verification_task"),
    (HARNESS_STATE_REFRESH_LABEL,   "harness_refresh_task"),
    (RECONCILIATION_LABEL,          "lifecycle_reconcile_task"),
)
```

with the comment *"Teardown order: verification awaits the refresh task, so it goes
first."* Every pass runs through `run_startup_pass` (`api/src/transport_matters/startup_passes.py:52`), which
logs and swallows: *"never a startup failure: a raised pass is logged and swallowed"*.

**Consequence for a newcomer:** harness state refreshes **once per backend start,
per channel**. A channel you never launch keeps stale harness evidence forever. This
is called out in the project `CLAUDE.md` and is a frequent source of "why does the
launch view say `target_unavailable`".

Reconciliation retries with backoff: `RECONCILIATION_RETRY_INTERVAL_S = 1.0`
climbing to `RECONCILIATION_RETRY_CEILING_S = 10.0` (`api/src/transport_matters/startup_passes.py:40-42`),
because a stale roster should correct within seconds of the Gateway answering
without a warning every second through a long outage.

### 1.3 Gateway child lifecycle

- `resolve_gateway_entry` (`api/src/transport_matters/gateway_supervisor.py:101`) prefers a packaged entry
  (`:95`), then env override.
- `resolve_node_binary` (`api/src/transport_matters/gateway_supervisor.py:162`) prefers a **bundled** node
  (`:130`, `:148`) over `which node`.
- `GatewaySupervisedProcess.stop` (`api/src/transport_matters/gateway_supervisor.py:269`) is the graceful stop.
- `GatewayAwareServer.shutdown` (`api/src/transport_matters/gateway_supervisor.py:338`) subclasses
  `uvicorn.Server` so the child dies with the parent.
- `watch_supervised_gateway` (`api/src/transport_matters/gateway_supervisor.py:346`) is the supervision loop;
  `_log_gateway_exit` (`:380`) is the single place an unexpected exit is reported.

### 1.4 Capture process lifecycle (the mitmproxy side)

`api/src/transport_matters/addon_runtime.py` (651) is the composition root for a capture process.
`load_capture_runtime` (`api/src/transport_matters/addon_runtime.py:496`) builds everything and **swallows all
startup failure**: *"Best-effort startup failure must never stop the proxy (§7.1)"*.

`_start_session_capture` (`api/src/transport_matters/addon_runtime.py:375`) wires, in order: async pool →
`SessionWriter(pool, loop=loop)` → `start_drift_capture` → `ShardedCommitDispatcher`
with `shard_count = session_pool_max_size - 2` → `LiveStatusObserver` →
`ProviderAccessRecorder(ExecutorEvidenceStore(...))` → `TranscriptTailer` →
`WireStoreObserver(writer, loop, binding_resolver, live_status).register()`.
On any `BaseException` it calls `drift.abort()` because *"Ownership never reached the
caller"*.

The pool reserve constant is documented at `api/src/transport_matters/addon_runtime.py:79`:
`_SESSION_POOL_AUX_CONNECTION_RESERVE = 2` — *"one aux plus the wire-store writer's
single serialized connection"*. That is why `WireStoreObserver._write_slot` is a
`Semaphore(1)` (`api/src/transport_matters/wire_store_observer.py:132`, rationale at `:312`).

`close_capture_runtime` (`api/src/transport_matters/addon_runtime.py:605`) shuts down in a **fixed order** that
you must not reorder:

```
bp.clear_all() → tailer.stop(drain=True) → live_status.aclose → wire_store.aclose
→ drift.aclose → dispatcher.aclose → drain lifecycle tasks → close RUN_EXITED
→ writer.aclose → drain pause-count tasks → http_client.aclose → clear_exchange_sinks()
```

`_emit_close_run_lifecycle_event` (`api/src/transport_matters/addon_runtime.py:157`): **detached** runs always
write the close-time `RUN_EXITED`; **managed** runs stay silent unless
`parent_death_detected()`, in which case the exit reason is `"orphaned"`. Managed
exits are the Gateway's to report (§3.2).

---

## 2. Module map

### 2.1 Layer 0 — no `transport_matters` imports

| Module | Lines | Role |
| --- | --- | --- |
| `api/src/transport_matters/ir.py` | 182 | Provider-neutral request/response IR. **Imports nothing from the package** (enforced convention, `api/CLAUDE.md`). All models `frozen=True`. |
| `api/src/transport_matters/canonicalization.py` | 90 | stdlib-only; shared by `overrides/audit` char accounting |
| `api/src/transport_matters/model_ids.py`, `api/src/transport_matters/product_identity.py`, `api/src/transport_matters/env_keys.py` | small | naming constants |

### 2.2 Layer 1 — parsing and provider adapters

| Module | Lines | Role |
| --- | --- | --- |
| `api/src/transport_matters/adapters/base.py` | 68 | `ProviderAdapter` ABC: `matches` / `inbound_request` / `outbound_request` / `inbound_response`, plus `carries_agent_turn` and `delivered_prompt_text` |
| `api/src/transport_matters/adapters/__init__.py` | 48 | registry `[GrokAdapter(), CodexAdapter(), AnthropicAdapter()]`, first match wins; miss raises `UnsupportedProviderError` |
| `api/src/transport_matters/adapters/anthropic.py` | | Claude request/response ↔ IR |
| `codex/` | 13 888 | the largest provider surface: Responses-API parsing, WebSocket transport, **turn derivation** (`derivation*.py`), repair (`repair*.py`) |
| `grok/` | 320 | Grok adapter + transport |

### 2.3 Layer 2 — pipeline and overrides

| Module | Lines | Role |
| --- | --- | --- |
| `api/src/transport_matters/request_pipeline.py` | 107 | four functions, **all fail open**: `parse_request_ir` → `None` on failure; `run_pipeline` (`:64`) classifies track + applies scoped overrides, returns original IR on any exception; `prepare_outbound_request` (`:91`) returns `(original_ir, None, None)` if serialization throws |
| `api/src/transport_matters/overrides/__init__.py` | 479 | nine `OverrideKind` values, fixed `_PRIORITY` map, `apply_overrides` (`:156`) |
| `overrides/{audit,state,targets,ops_messages,ops_metadata}.py` | | audit ledger, per-run override state, target resolution |
| `api/src/transport_matters/track_manager.py` | 564 | assigns each flow to a track (primary vs subagent) |
| `api/src/transport_matters/request_purpose.py` | 20 | `request_drives_activity(provider, request_kind)` — the single predicate that decides whether a request advances the activity/live-status model |
| `api/src/transport_matters/counting.py` | 303 | token/char accounting for the audit |

### 2.4 Layer 3 — capture (the mitmproxy addon)

| Module | Lines | Role |
| --- | --- | --- |
| `api/src/transport_matters/addon.py` | 151 | the mitmproxy hook surface; delegates every body to `addon_handlers` |
| `api/src/transport_matters/addon_handlers.py` | 698 | the actual hook bodies (§4.4) |
| `api/src/transport_matters/addon_runtime.py` | 651 | composition root, `load_capture_runtime` / `close_capture_runtime` |
| `api/src/transport_matters/flow_state.py` | 228 | typed accessors over mitmproxy's untyped `flow.metadata`; `RequestFlowState` at `:38` |
| `api/src/transport_matters/response_stream.py` | 60 | `install_response_tee` / `restore_streamed_response` |
| `api/src/transport_matters/live_status.py` / `api/src/transport_matters/live_status_observer.py` | 405 / 684 | streaming SSE classification into `RunLiveStatusRow` |
| `api/src/transport_matters/sse.py` | 115 | `IncrementalSseFrames` reframer |
| `api/src/transport_matters/http_transport.py` | 143 | header snapshotting |
| `api/src/transport_matters/breakpoint.py` / `api/src/transport_matters/pause_session.py` | 186 / 435 | request pausing and manual release |
| `api/src/transport_matters/credential_refresh.py` | 92 | refreshes an expired Claude credential mid-flight |
| `shared_proxy/` | 4 128 | the proxy layer: `ProxyRunBinding` (`binding.py`), the shared subprocess and its control channel (`core.py`, `control.py`, `process.py`, `subprocess.py`), `SharedProxyManager` (`manager.py`) |
| `shared_proxy/registration.py` | 236 | **the shared/per-run seam.** Supplies the `supervisor_factory` and `proxy_starter` that make an RPC-prepared run register a listener on the shared proxy instead of spawning mitmdump |
| `api/src/transport_matters/force_http_fallback_addon.py` | 52 | forces HTTP/1.1 where HTTP/2 breaks capture |

### 2.5 Layer 4 — storage (tier 1, disk; authoritative)

| Module | Lines | Role |
| --- | --- | --- |
| `api/src/transport_matters/storage/base.py` | | `StorageBackend` ABC, `IndexEntry`, `ExchangeArtifacts`, `TransportArtifacts` |
| `api/src/transport_matters/storage/disk.py` | 595 | `DiskStorageBackend` (`:37`) — *"Append-only JSONL index with per-exchange artifact directories"*, aiofiles-based |
| `api/src/transport_matters/storage/disk_helpers.py` | 406 | `DiskStorageRecoveryMixin` |
| `api/src/transport_matters/storage/disk_layout.py` | | the filenames: `index.jsonl`, `sessions.json`, `compatibility.json`, `entry.json`, `request.raw`, `request.ir.json`, `request.curated.raw`, `request.curated.ir.json`, `request.audit.json`, `response.raw`, `response.ir.json`, `transport.json`, `events.jsonl`, `turn.json`, `transcripts/`, with `.tmp`/`.bak`/`.del` suffixes |
| `api/src/transport_matters/storage/exchange_sink.py` | 116 | **the DAG inversion point** (§4.5) |
| `api/src/transport_matters/storage/session_facts.py`, `api/src/transport_matters/storage/transcript_snapshot.py` | | read helpers |
| `exchange_recorder/` | 2 948 | the persistence orchestration (§4.6) |
| `api/src/transport_matters/atomic_io.py` | 137 | write-temp-then-rename |

### 2.6 Layer 5 — session store (tier 2, Postgres)

`session/` is 15 847 lines. **`storage` must never import `session`** — the snapshot
sink is injected at `load_runtime()` (`api/CLAUDE.md`).

| Module | Role |
| --- | --- |
| `api/src/transport_matters/session/pool.py` (194) | `connect()` documents all four bounds — `connect_timeout`, `statement_timeout`, keepalives, `tcp_user_timeout` (Linux only) — and notes *"Callers that must never stall (the launch compatibility gate) pass all four."* `create_async_pool` calls `guard_pytest_session_store_url` (`:184`) which **raises under `PYTEST_CURRENT_TEST`** unless the db name starts with `TEST_DB_PREFIX` |
| `api/src/transport_matters/session/migrate.py` (147) | `_MIGRATION_ADVISORY_LOCK_KEY = 0x746D6D6967` ("tmmig"); fast-path skips the lock when already at head |
| `api/src/transport_matters/session/writer.py` (685) | `SessionWriter`, *"Thread-safe blocking facade over an async Postgres commit coroutine"* |
| `api/src/transport_matters/session/wire_store.py` (422) | `WireExchangeWrite`, `write_wire_exchange` (`:117`), `sweep_wire_store` (`:208`) |
| `api/src/transport_matters/session/wire_normalization.py` | component hashing / dedup |
| `api/src/transport_matters/session/listen.py` (491) | LISTEN/NOTIFY hub, `NOTIFY_CHANNEL = "tm_events"` |
| `api/src/transport_matters/session/async_dao.py`, `api/src/transport_matters/dao_statements.py`, `api/src/transport_matters/session_statements.py`, `api/src/transport_matters/controlplane_statements.py` | raw SQL, no ORM |
| `api/src/transport_matters/session/models.py` | row models incl. `RunLifecycleEventRow`, `RunLiveStatusRow`, `MANAGED_LAUNCH_KINDS` |
| `api/src/transport_matters/session/run_lifecycle_contracts.py` (14) | the shared vocabulary (§7.1) |
| `session/timeline*.py`, `api/src/transport_matters/conversation_projection.py` | read-side projections |
| `api/src/transport_matters/session/ingest.py`, `api/src/transport_matters/backfill.py`, `api/src/transport_matters/quarantine.py` | repair paths |
| `api/src/transport_matters/session/testing.py` | ephemeral test databases |

### 2.7 Layer 6 — harnesses, baselines, support state

| Group | Modules | Role |
| --- | --- | --- |
| Resolution | `api/src/transport_matters/harnesses/resolver.py` (692), `api/src/transport_matters/resolver_contracts.py` (43), `api/src/transport_matters/resolver_snapshots.py`, `api/src/transport_matters/resolver_targets.py`, `api/src/transport_matters/launch_target.py` (196) | pure snapshot → `TargetResolution` |
| Compatibility | `api/src/transport_matters/harnesses/compatibility.py`, `api/src/transport_matters/compatibility_facts.py`, `api/src/transport_matters/compatibility_store.py`, `api/src/transport_matters/compatibility_service.py` | blessed range vs installed version |
| Inventory | `api/src/transport_matters/harnesses/inventory.py`, `connections*.py`, `api/src/transport_matters/state_refresh.py`, `enablement*.py`, `blocks*.py` | what is installed, connected, enabled, blocked |
| Certification | `harnesses/certification*.py` (7 modules), `api/src/transport_matters/certification_capture.py` | producing a release's reference schemas |
| Baseline | `baseline_*.py` (18 top-level modules, ~5 000 lines) | capture, harvest, compare, publish, project |
| Schema | `api/src/transport_matters/request_schema.py` (390), `api/src/transport_matters/request_schema_comparison.py` (669), `api/src/transport_matters/request_schema_branch_alignment.py` (122) | schema minting and directional diff |
| Coverage | `api/src/transport_matters/ir_coverage.py` (276), `api/src/transport_matters/ir_coverage_tables.py` (443) | the modeled/normalized/unmodeled declaration |
| Envelope | `api/src/transport_matters/transport_envelope.py` (156), `api/src/transport_matters/transport_redaction.py` (142) | the second schema of a cell |
| Verdict | `api/src/transport_matters/support_state.py` (261), `api/src/transport_matters/support_verdict.py` (35), `api/src/transport_matters/support_verdict_store.py` (283) | the operator-facing axis |
| Verification | `api/src/transport_matters/launch_verification.py` (628), `api/src/transport_matters/verification_cell.py`, `api/src/transport_matters/verification_executor.py` | the lazy comparison at launch |

### 2.8 Layer 7 — control plane and API

| Module | Lines | Role |
| --- | --- | --- |
| `api/src/transport_matters/controlplane/service.py` | 108-628 | `ControlPlaneService`, the 13 verbs |
| `api/src/transport_matters/controlplane/launch_service.py` | 561 | `ControlPlaneLauncher` |
| `api/src/transport_matters/controlplane/activity.py` | | activity projection, `GatewayUnavailableError` / `GatewayResponseError` |
| `api/src/transport_matters/controlplane/roster_projection.py` | 105 | `project_roster`, `MAX_WORKSPACE_SUMMARY_CHARS = 4_000` |
| `controlplane/lifecycle_*.py`, `api/src/transport_matters/reap.py`, `api/src/transport_matters/runtime_liveness.py` | | §7 |
| `api/src/transport_matters/controlplane/prompt_delivery.py`, `delivery_*.py` (9 modules) | | prompt delivery ledger |
| `controlplane/watch*.py` (5 modules) | | watch subscriptions |
| `api/src/transport_matters/controlplane/grants.py`, `api/src/transport_matters/tokens.py`, `api/src/transport_matters/audit.py` | | capability grants |
| `api/src/transport_matters/api/v1/router.py` | | route assembly |
| `api/src/transport_matters/api/v1/run_proxy.py` | 662 | `RunRouteProxy` — the Python→Gateway seam |
| `api/src/transport_matters/api/v1/capture_rpc_routes.py` | 681 | the Gateway→Python seam |
| `api/src/transport_matters/api/v1/controlplane_mcp.py` | 541 | 14 MCP tools |
| `api/src/transport_matters/api/v1/space_mcp.py`, `api/src/transport_matters/browsing_mcp.py` | | two more MCP servers |
| `api/src/transport_matters/capture_rpc.py` | 505 | `CaptureLeaseRegistry` |
| `captured/` | 4 346 | preparing a captured run (`api/src/transport_matters/run.py` 625, `api/src/transport_matters/context.py` 503, `api/src/transport_matters/models.py` 368) |
| `space/` | 5 380 | spaces, canvases, worktrees |
| `supervisor/` | 2 113 | PTY supervision for the *CLI's own* detached runs |
| `cli/` | 21 600 | typer commands |

---

## 3. Core domain models and their invariants

### 3.1 `InternalRequest` / `InternalResponse` (`api/src/transport_matters/ir.py`)

- All models `frozen=True` (`api/CLAUDE.md`: "IR models are `frozen=True` — pipeline
  actions return new instances, never mutate").
- `Message.role` is a **plain `str`, deliberately not an enum**, with the comment at
  `api/src/transport_matters/ir.py` that *"providers occasionally inline unmodeled roles (e.g. Claude Code
  2.1.154 added `{"role":"system"}` to `messages[]`). Preserve the role verbatim
  rather than dropping the request."*
- `InternalRequest.messages` has `min_length=1`, which is why
  `empty_message_placeholder()` (`api/src/transport_matters/ir.py:105`) exists. Its docstring warns:
  *"Pydantic's frozen model prevents field assignment but does not freeze nested
  containers."* **Never mutate a list inside a frozen IR.**
- The IR is **mirrored into TypeScript** and the mirror is test-enforced:
  `api/src/transport_matters/test_type_mirrors.py:20-24` compares `api/src/transport_matters/ir.py` and `api/src/transport_matters/overrides/__init__.py` against
  `www/packages/core/src/types/{ir,overrides}.ts`, and
  `api/src/transport_matters/controlplane/activity.py` against
  `packages/contract/src/activity/wire.ts` (`api/src/transport_matters/test_type_mirrors.py:26-28`).

### 3.2 Run lifecycle

The vocabulary lives in exactly one 14-line file,
`api/src/transport_matters/session/run_lifecycle_contracts.py`:

```python
RUN_LIFECYCLE_EVENT_TYPES        = ("run-started", "run-exited")
RUN_LIFECYCLE_LAUNCH_KINDS       = ("canvas", "detached", "service")
RUN_LIFECYCLE_REAPED_EXIT_REASON = "reaped"
RUN_LIFECYCLE_RETRACTION_REASON  = "runtime_reported_running"
RUNTIME_LOCK_KEY_FUNCTION        = "run_runtime_lock_key"
DEFAULT_ACTIVITY_OWNER           = "local"
```

Invariants:

- A run has at most one standing `run-started` and at most one **standing** exit.
- The only **retractable** exit is a synthetic one, `exit_reason = "reaped"`
  (`api/src/transport_matters/controlplane/reap.py`). `reaped_exit_event` clears `session_id`, `exit_code` and
  `error`; `retracted_reap_event` stamps `runtime_id`, `retracted_at` and
  `retracted_reason`.
- *"A duplicate insert is success: the primary key already holds the exit fact"*
  (`api/src/transport_matters/controlplane/reap.py`).
- Managed runs (`canvas`, `service`) get their exit from the Gateway. Detached runs
  write their own at capture close (`api/src/transport_matters/addon_runtime.py:157`).

### 3.3 Wire exchange

`WireExchangeWrite` (`api/src/transport_matters/session/wire_store.py`) is frozen, with a validator
`response_requires_completion` that **forbids a response IR without
`response_complete=True`**. The write carries `exchange_id`, `delivery_id`,
`generation`, `run_id`, `session_id`, `provider`, `request_kind`, `harness`, `ts`,
`model`, `turn_index`, the track triple (`track_id` / `parent_track_id` /
`track_role`), `request`, `request_curated`, `mutated_manually`, byte evidence
(`request_raw_bytes`, `request_wire_bytes`, `request_body_decoding_diverged`),
`response`, and workspace facts (`api/src/transport_matters/wire_store_observer.py:177-206`).

An exchange row goes through **up to three writes**: provisional (outbound request,
`response_complete=False`), optional unparsed, and final
(`response_complete=True`). It may instead be **deleted** if the flow dropped
(`api/src/transport_matters/exchange_recorder/__init__.py:451`).

### 3.4 Prompt delivery

`delivery_id` binds an operator-issued prompt to the wire request that actually
carried it. `LivePromptDeliveryBindings(...).claim(outbound_request)` **consumes**
the binding it matches (`api/src/transport_matters/wire_store_observer.py:96`). Because a claim is consumed
once, `WireStoreObserver` retains it across the provisional→final writes
(`_retained_claim`, `:210`) and releases it only when
`result.ok and write.response_complete` (`:279`). The docstring records why (#619):
*"If the outbound wire write fails, claiming again during finalization finds
nothing and leaves the completed row without a durable delivery id."*

The retention is bounded FIFO, `max_retained_claims = 256`
(`api/src/transport_matters/wire_store_observer.py:123`), because `handle_http_error` deliberately strands
some provisional exchanges that are neither finalized nor deleted
(`api/src/transport_matters/wire_store_observer.py:21-26`).

**Purpose vs claim** (`api/src/transport_matters/wire_store_observer.py:218-222`): *"Purpose belongs to the raw
harness request; the claim digest belongs to the request sent on the wire."* Overrides
can rewrite tools, sampling and prompt text, so the two are read from different IRs
— `artifacts.request_ir` for purpose, `request_curated_ir or request_ir` for the
claim (`:164`, `:226-231`).

### 3.5 Support state

`api/src/transport_matters/support_state.py` is the authority. `SupportState` is a **two-member** StrEnum
(BLESSED / DEGRADED) with the note that *"A version that has not been compared yet
has no state at all"* — unknown is the absence of a row, never a third member.

`SupportFinding` carries `profile`, `pointer`, `branch_tag`, `reason`, `coverage`,
`degrades`, `moved_to`.

`assess_support_state` (`api/src/transport_matters/support_state.py:171`) opens with *"Argument order is the
whole contract"* — it is **directional**, reference on the left. It compares the
envelope schema only when both sides carry one, folding it by the same rule as a
second request shape. `fold_support_verdicts` (`:130`): degraded anywhere is degraded.

The symmetric worst-of-both fold belongs **only** to the cohort gate,
`baseline_comparison.compare_model_pair`, where two models of one harness are peers
of equal standing. Do not import that fold into the reference comparison.

`DriftOutcome` (EXACT / DEGRADED / BREAKING) is a property of one **comparison**;
`SupportState` is a property of a **version**. They share a word and are different
axes.

### 3.6 Resolution

`ResolverSnapshots._validate_scopes` rejects any connection or observation belonging
to a different harness or executor (`api/src/transport_matters/harnesses/resolver.py`). `TargetResolution.
_validate_exclusivity` enforces **exactly one** of resolved / rejection.
`resolve_target` (`api/src/transport_matters/harnesses/resolver.py:473`) applies authorities in a fixed
mismatch-table order: installation → enablement → compatibility → release presence →
connection → certified route → offered targets → effort → target compatibility.

`ResolutionRejectionCode` is a **closed 13-member literal**
(`api/src/transport_matters/harnesses/resolver_contracts.py`). `ProviderAccessRejectionCode` has exactly one
member, `provider_access_assessment_unavailable`: **provider access never refuses a
launch.**

`launch_target_advisory` (`api/src/transport_matters/harnesses/launch_target.py:150`) raises
`LaunchTargetRejected` unless `_passes_to_harness` (`:185`) allows it, which it does
for exactly four cases: `invalid_effort`; `target_unverified_opt_in_required`;
`target_ambiguous` with no model but an effort; `target_unavailable` with
`reason == "not_observed"`.

`_launch_verification_cell` (`api/src/transport_matters/harnesses/launch_target.py:72`) is documented as
*"An observation, never an actuation."*

---

## 4. The seams (both sides verified)

### 4.1 Python → Gateway (HTTP + WebSocket)

**Python side:** `RunRouteProxy` (`api/src/transport_matters/api/v1/run_proxy.py:94`). Methods:
`create_run` (`:241`), `list_runs` (`:261`), `terminate_run` (`:275`),
`deliver_input` (`:219`), `runtime_identity` (`:112`), `read_conversation` (`:167`),
`read_terminal_snapshot` (`:211`), `devtools_attach` (`:244`),
`resolve_workdir_context` (`:247`), plus raw `forward_http` (`:125`),
`forward_sse` (`:328`), `forward_terminal` (`:372`) and `forward_plain_terminal`
(`:381`).

WebSocket bridging is `_bridge_websockets` (`:420`) driving
`_downstream_to_upstream` (`:548`) and `_upstream_to_downstream` (`:570`), with
`_wire_close_code` (`:649`) / `_closed_code` (`:655`) / `_closed_reason` (`:660`)
translating `ConnectionClosed`.

`gateway_unavailable_error` (`:325`) is the single place an `httpx.RequestError`
becomes a domain error; the wire code is `GATEWAY_UNAVAILABLE_CODE =
"gateway_unavailable"` (`api/v1/errors.py:11`).

**Gateway side:** `packages/runtime/src/server/runtimeRouter.ts` — `POST /runs`
(`:69`), `GET /runs` (`:191`), `GET /runs/:runId` (`:219`), `POST /runs/:runId/...`
(`:240`), input delivery (`:257`), terminal WS (`:289`), plain terminal (`:280`).

### 4.2 Gateway → Python (capture RPC)

**Gateway side:** `packages/runtime/src/adapters/CaptureRpcClient.ts` —
`prepareCapture` (`:81`) POSTs `/v1/capture/prepare` (`:84`), `releaseCapture`
(`:90`) POSTs `/v1/capture/{runId}/release` (`:93`), `captureHealth` (`:100`) GETs
`/v1/capture/{runId}/health`. The port contract is `packages/runtime/src/ports.ts:141`.

Timeout note at `CaptureRpcClient.ts:21-22`: *"Must exceed the Python prepare budget:
proxy readiness polls 5s per attempt (`loopback.wait_for_port_ready`) across bind
retries before prepare fails server-side."* If you change the Python retry budget,
this TS constant must move too.

**Python side:** `api/src/transport_matters/api/v1/capture_rpc_routes.py`, `router = APIRouter(prefix="/capture")`
(`:93`). Handlers: `prepare_capture` (`:249`), `release_capture` (`:636`),
`capture_health` (`:653`). The request model is `PrepareCaptureRequest` (`:98`) with
a cross-field validator `paired_initial_prompt` (`:152`) and `to_domain` (`:156`).

### 4.3 Postgres

Two distinct clients:
- **Async pool** in the backend and the capture process (`api/src/transport_matters/session/pool.py`).
- **Sync** paths for the CLI and `sweep_wire_store` (`api/src/transport_matters/session/wire_store.py:210`).

`SessionWriter` (`api/src/transport_matters/session/writer.py`) is the thread↔loop bridge: capture runs on the
mitmproxy thread, the writer owns an asyncio loop, and
`_raise_if_target_loop` / `_require_target_loop` enforce which loop each method may
be called from. Getting this wrong deadlocks silently.

### 4.4 mitmproxy hooks

`api/src/transport_matters/addon.py` (151) declares the hook names; every body is in `api/src/transport_matters/addon_handlers.py` (698).

- `handle_http_request` (`~:207`) gates on `/v1/messages` or a Codex/Grok responses
  flow, snapshots headers + raw body, `set_recent_auth`, `parse_request_ir`, then:

```python
curated_ir, audit, track_assignment, outbound = await _run_prepared_pipeline(
    adapter, ir, flow.id, run_id)
skip_breakpoint, pause_request = _breakpoint_disposition(ir.model, binding)
request_state = capture_request_flow_state(...)
if not pause_request and outbound is not None:
    flow.request.set_text(outbound.decode())
provisional_exchange_id = await persist_http_provisional_exchange(
    flow, request_state, binding, outbound=not pause_request)
```

- `_should_stream_response` (`~:193`) declines 101 / websocket-upgrade and requires
  `server_conn.timestamp_start`.
- `handle_response_headers` starts the live-status chunk observer, then
  `install_response_tee`.
- `handle_response` (`~:542`) runs `restore_streamed_response` →
  `refresh_expired_claude_credential` → `persist_http_exchange`.
- `handle_http_error` (`~:585`) **retains** an incomplete provisional exchange and
  finalizes only when `_http_response_capture_is_complete` proves a terminal payload
  or an exact content-length.
- `handle_codex_websocket_message` (`~:343`) owns Codex turn rotation.

Flow state crosses the hooks through `api/src/transport_matters/flow_state.py`'s string keys
(`_ADAPTER_KEY` … `_DRIVES_ACTIVITY_KEY`, `api/src/transport_matters/flow_state.py:20-32`) hydrated into the
`RequestFlowState` dataclass (`:38`).

### 4.5 storage → session (the dependency inversion)

`api/src/transport_matters/storage/exchange_sink.py` (116) is the only bridge. Four registries — `_sinks`,
`_outbound_request_sinks`, `_unparsed_sinks`, `_deleted_sinks` — plus a generic
`_register[SinkT]` returning an idempotent unregister handle, and `_fan_out`, which
**logs and swallows per subscriber** so *"the wire path never fails because of an
observer"*.

Emission contract (module docstring):
`emit_outbound_request` on provider release; `emit_to_index` exactly once per
completed exchange; `emit_unparsed_exchange` per synthetic parse-failure row;
`emit_deleted` for a provisional repaired away.

`WireStoreObserver.register()` (`api/src/transport_matters/wire_store_observer.py:135`) subscribes all four and
keeps the handles; `aclose` (`:295`) unregisters, then drains every pending future.

The observer's own docstring (`api/src/transport_matters/wire_store_observer.py:5-8`) states the threading
rule: *"Sinks run on the proxy thread, so they only pluck fields and schedule onto
the writer loop via `run_coroutine_threadsafe` ... normalization and hashing run
inside the scheduled coroutine, off the proxy hot path."*

### 4.6 LISTEN/NOTIFY

`api/src/transport_matters/session/listen.py` (491). `NOTIFY_CHANNEL = "tm_events"`, `QUEUE_MAX_SIZE = 1000`.
Five subscription types: session events, wire exchanges, wire deliveries, run events,
control-plane deliveries — each with a matching `*CatchUpSignal(reason=
"listener_reconnected")`.

`SessionEventListener._listen_forever` (`api/src/transport_matters/session/listen.py:461`) opens an autocommit connection,
records `pg_backend_pid()`, issues `LISTEN`, calls `self._hub.publish_catch_up()`
**before** entering the notify loop, and reconnects after 0.25 s on any failure.
`_replace_queue_with_catch_up` drains a queue and replaces its contents with the
catch-up signal — a slow consumer loses individual notifications but never loses
correctness, because it is told to re-read.

Writers fire notifies from `SessionWriter.submit_wire_exchange`
(`api/src/transport_matters/session/writer.py:188`): one for the exchange, one more for the delivery if present.

### 4.7 MCP

Three MCP servers are mounted. The control plane one is
`api/src/transport_matters/api/v1/controlplane_mcp.py:397 create_control_plane_mcp`, registering **14 tools**:
`agents`, `workspace_summary`, `whoami`, `harnesses`, `roster`, `conversation`,
`prompt`, `wait_for_reply`, `launch`, `close`, `interrupt`, `watch`, `unwatch`.

Two ASGI wrappers matter:
- `ControlPlaneMcpAuthApp.__call__` (`:167`) resolves the principal into a
  `ContextVar` **before** the SDK hook and returns a 503 envelope on
  `ControlPlaneIdentityUnavailable`.
- `ControlPlaneMcpExactPathApp` (`:191`) rewrites the ASGI scope so bare `/mcp`
  serves without a redirect.

Auth: `resolve_control_plane_bearer` (`api/src/transport_matters/api/v1/controlplane_auth.py`) re-resolves on
**every** request "without caching". `resolve_devtools_principal` documents why:
*"The capability holds the run rather than the bearer, so nothing on this path can
act as the Director. Revocation deletes the grant row keyed by that run, which is
what makes this read the revocation check."*

### 4.8 PTY

Python owns PTYs **only** for its own detached/CLI runs (`api/src/transport_matters/supervisor/pty.py`,
`api/src/transport_matters/supervisor/pty_process.py`). Managed runs' PTYs are the Gateway's
(`packages/runtime/src/service/RunManager.ts:253 this.ptyPort.spawn`).

---

## 5. Three end-to-end traces

### 5.1 Trace A — run launch, request to live PTY

1. **MCP `launch` tool** → `ControlPlaneService.launch`
   (`api/src/transport_matters/controlplane/service.py:345`).
2. `ControlPlaneLauncher.launch` (`api/src/transport_matters/controlplane/launch_service.py:118`) →
   `_prepare_and_execute` (`:183`) → `_prepare` (`:386`) → `_execute` (`:223`).
   The request is normalized by `_normalize_launch_request` (`:504`) and
   fingerprinted for idempotency by `_intent_fingerprint` (`:540`) /
   `_candidate_dispatch_id` (`:561`). Failures land in `_finish_failure` (`:329`)
   and `_persist_frozen_audit` (`:369`); the first prompt is recorded by
   `_record_first_prompt` (`:452`).
3. `RunRouteProxy.create_run` (`api/src/transport_matters/api/v1/run_proxy.py:241`) HTTP-POSTs the Gateway.
4. **Gateway** `POST /runs` (`packages/runtime/src/server/runtimeRouter.ts:69`) →
   `RunManager.create`.
5. `RunManager` calls back into Python:
   `this.capturePort.prepareCapture({...})`
   (`packages/runtime/src/service/RunManager.ts:205-237`) via
   `CaptureRpcClient.prepareCapture` (`adapters/CaptureRpcClient.ts:81`) →
   `POST /v1/capture/prepare` (`:84`).
6. **Python** `prepare_capture` (`api/src/transport_matters/api/v1/capture_rpc_routes.py:249`) →
   `_resolved_domain_request` (`:328`) → `_verified_launch_directory` (`:448`) →
   `_resolve_launch_target` (`:460`). Rejections map to HTTP through
   `_launch_target_rejection_status` (`:567`) and `_launch_target_rejection_detail`
   (`:574`); provider-access rejections through `_provider_access_rejection_detail`
   (`:581`), and the gate decision is logged once by `_log_access_gate` (`:591`).
7. `CaptureLeaseRegistry.prepare_capture` (`api/src/transport_matters/capture_rpc.py:155`) →
   `_prepare_with_dependencies` (`:214`) → the injected `prepare_run`, which is
   `prepare_captured_run` (`api/src/transport_matters/captured/run.py:232`) either
   bare or partial-bound to the shared proxy (§5.1a). That runs
   `_acquire_captured_run_resources` (`:325`), `_start_captured_attempts` (`:343`)
   with `_next_attempt_ports` (`:451`), `_persist_control_plane_grant` (`:482`) and
   `_spawnable_invocation_builder` (`:501`).
8. The spawn spec is serialized by `capture_spawn_spec_payload` (`api/src/transport_matters/capture_rpc.py:464`)
   with `_client_payload` (`:496`) and `_managed_session_payload` (`:509`) and
   returned over the RPC.
9. **Gateway** requires a client process, else `launch_failed`
   (`RunManager.ts:246-251`), then spawns the PTY:
   `await this.ptyPort.spawn({argv, env: browserPtyEnvironment(client.env,
   input.harness), cwd, cols, rows})` (`RunManager.ts:253-259`), then `register`
   (`:263`).
10. **Rollback on any spawn failure** (`RunManager.ts:265-278`): it calls
    `releaseCapture(spec.runId, {endReason: "failed", error})` with the comment
    *"Carry the failure facts so the capture side records a real STARTED+EXITED(error)
    pair rather than a phantom clean exit."* Python's side is
    `CaptureLeaseRegistry.release_capture` (`api/src/transport_matters/capture_rpc.py:230`), which emits the
    lifecycle pair through `_emit_lifecycle` (`:374`).

Abandoned prepares are cleaned by `_close_abandoned_prepare` (`api/src/transport_matters/capture_rpc.py:413`)
and logged by `_log_abandoned_close_failure` (`:423`).

#### 5.1a A canvas run's proxy is a binding

Two proxy shapes exist, and they walk **one** code path:

```
per-run   the CLI's embedded launch: one mitmdump child; liveness is the process
shared    a run prepared over the capture RPC: one reverse listener on the channel
          backend's SharedProxyManager; liveness is the binding
```

`prepare_captured_run` parameterises exactly two things
(`api/src/transport_matters/shared_proxy/registration.py:3-9`): the
`supervisor_factory` attached to the run's resources, and the `proxy_starter` that
brings a proxy up for one port attempt. Everything else — context, workspace lock,
owned session facts, manifest, invocation, port stepping on bind conflicts, retry
with jitter on readiness timeouts, identity, prompt-delivery arming, grant
persistence — is the single shared path. *"Nothing here duplicates that path."*

- **Default starter:** `_start_per_run_proxy`
  (`api/src/transport_matters/captured/run.py:612`), which discards `ctx` and calls
  `start_prepared_proxy`. It was introduced by `feb6d42c` purely so `ctx` could be
  threaded to a starter that needs it; `_start_captured_attempts` now passes
  `ctx=ctx` on every attempt (`api/src/transport_matters/captured/run.py:393`).
- **Shared starter:** `shared_proxy_starter(...)`
  (`api/src/transport_matters/shared_proxy/registration.py:154`) builds the binding
  and registers it. Control failures are classified by code: `_BIND_CONTROL_CODES`
  (`:48`, currently `{"duplicate_listen_port"}`) become a `LaunchBindFailureOutcome`
  so the port loop steps to the next pair; `_TIMEOUT_CONTROL_CODES` (`:50`,
  `control_connect_timeout`, `control_ready_timeout`, `control_request_timeout`,
  `listener_ready_timeout`) become `PROXY_START_TIMEOUT_MESSAGE` so the readiness
  retry-with-jitter fires. Anything else re-raises.
- **Supervisor shape:** `SharedProxyRegistration`
  (`api/src/transport_matters/shared_proxy/registration.py:94`) implements only what
  `CapturedRunResources` drives — `poll_any`, `terminate_all`, and the signal-handler
  pair (which are no-ops, `:144-148`) — so the lease, registry, release and health
  paths are untouched.
- **Liveness is the binding, not the process** (`registration.py:120-132`):
  `poll_any` returns `None` while `self.run_id in self._manager.by_run_id`. The
  manager's mirror survives a subprocess restart and is replayed into the new
  process, so a restart in flight must not read as run death — the Gateway's health
  monitor tears a run down the *first* time it sees a dead proxy.
- **The binding is derived from the launch environment**, not from a parallel config:
  `binding_from_launch_env` (`registration.py:61`) reads `env_keys.STORAGE_DIR`,
  `RUN_ID`, `HARNESS`, `CWD`, `PROXY_PORT`, `AGENT_HOME_DIR`,
  `OWNED_NATIVE_SESSION_ID`, `OWNED_SOURCE_DESCRIPTOR`, `LAUNCH_FIELDS` and
  `DEFAULT_CLIENT_PASSTHROUGH` — the same carrier the per-run addon reads through
  `Settings`. `upstream` is the one exception: it rides the per-run mitmdump argv,
  so the shared starter takes it from `ctx.request.upstream` (`registration.py:69-71`,
  `:171`). Parity between the two is asserted by a test
  (`api/src/transport_matters/shared_proxy/test_registration.py`).
- **Deregistration is the one async act**, driven from the worker thread onto the
  backend loop through `_await` (`registration.py:150`, a
  `run_coroutine_threadsafe(...).result(15.0)`). A `SharedProxyRegistryError` on
  deregister is swallowed: *"Already gone: a restarted subprocess rehydrates only
  live bindings"* (`registration.py:140-142`).

### 5.2 Trace B — a captured request, harness egress to persisted wire exchange

1. Harness makes a provider call. Its base URL was redirected to the per-run proxy
   (`EndpointRedirect`, `shared_proxy/`). No CA install: reverse mode.
2. mitmproxy calls `request` → `api/src/transport_matters/addon.py` → `handle_http_request`
   (`api/src/transport_matters/addon_handlers.py:~207`). Gate: `/v1/messages` or a Codex/Grok responses flow.
3. `parse_request_ir` (`api/src/transport_matters/request_pipeline.py`) → `InternalRequest`, or `None`
   (fail open, the flow still forwards).
4. `run_pipeline` (`api/src/transport_matters/request_pipeline.py:64`) classifies the track
   (`api/src/transport_matters/track_manager.py`) and scopes overrides to `(run_id, track_id)` or
   `root_scope(run_id)`; any override exception returns the **original** IR.
5. `apply_overrides` (`api/src/transport_matters/overrides/__init__.py:156`) applies the batch in `_PRIORITY`
   order, computes `_shadowed_targets` (`:198`), and on any **miss** rolls the whole
   batch back via `_rolled_back_entry` (`:214`), logging
   `"Override batch rolled back, missed ..."`. Message sanitization runs **only**
   when the batch contains a message operation, so an empty override set is byte
   identical.
6. `prepare_outbound_request` (`api/src/transport_matters/request_pipeline.py:91`) serializes; on **any**
   exception it returns `(original_ir, None, None)` — no audit, no bytes.
7. `capture_request_flow_state` (`api/src/transport_matters/flow_state.py:78`) stashes everything on the flow.
8. `persist_http_provisional_exchange` (`api/src/transport_matters/exchange_recorder/__init__.py:333`) writes
   **tier 1 to disk before forwarding**. Comment at `~:378-380`: *"The request hook
   awaits Tier 1 persistence before forwarding. Including transport here keeps the
   original boundary snapshot durable if the process exits before a response
   arrives."*
9. That persist calls `publish_stored_outbound_request`
   (`api/src/transport_matters/exchange_recorder/__init__.py:85`) → `emit_outbound_request` →
   `api/src/transport_matters/storage/exchange_sink.py:_fan_out`.
10. `WireStoreObserver.on_outbound_request` (`api/src/transport_matters/wire_store_observer.py:144`) →
    `_submit_exchange(response_complete=False)` (`:153`). It resolves the run
    (`_resolve_run`, `:322`), claims the delivery once (`_retained_claim`, `:210`),
    builds a `WireExchangeWrite` (`:177`), and `_schedule`s it (`:306`) onto the
    writer loop through `_serialized` (`:311`, `Semaphore(1)`).
11. `SessionWriter.submit_wire_exchange` (`api/src/transport_matters/session/writer.py:188`) →
    `write_wire_exchange` (`api/src/transport_matters/session/wire_store.py:121`): normalize → upsert blobs
    (`_upsert_blobs` pre-checks existing hashes because the steady state is ~98%
    duplicates) → ensure component sets → take
    `pg_advisory_xact_lock(WIRE_COMMIT_WATERMARK_LOCK_KEY)` (*"Replay cursors take
    the shared side of this transaction lock"*) → insert-or-update the exchange row →
    delete+reinsert manifests → response blocks **only when complete**.
12. Response path: `handle_response_headers` installs the tee; `handle_response`
    (`api/src/transport_matters/addon_handlers.py:~542`) restores the stream and calls `persist_http_exchange`
    (`api/src/transport_matters/exchange_recorder/__init__.py:255`), which routes to
    `_finalize_http_provisional_exchange` (`:475`). Comment at `~:540`: *"Streaming,
    Claude's primary path, finalizes here, not in `persist_http_exchange`'s
    non-provisional branch."*
13. Finalize emits `emit_to_index` → `WireStoreObserver.on_exchange` (`:147`) →
    a second write with `response_complete=True`, after which
    `_release_claim` runs (`:279-280`).
14. `SessionWriter.submit_wire_exchange` fires `pg_notify` for the exchange and, if
    present, the delivery, and closes a live-status generation when
    `notify_required and response_complete and track_role != subagent and
    request_drives_activity(...)`. It self-heals a stale `_verified_wire_sets` cache
    on `psycopg.errors.ForeignKeyViolation` by clearing and retrying once
    (`api/src/transport_matters/session/writer.py:188`ff). Failures go to `_record_wire_failure` (`:318`),
    which counts and logs and **never raises into capture**.
15. `api/src/transport_matters/session/listen.py` delivers the notification to subscribers.

Dropped flow: `delete_http_provisional_exchange`
(`api/src/transport_matters/exchange_recorder/__init__.py:451`) → `emit_deleted` →
`WireStoreObserver.on_exchange_deleted` (`:283`), which releases the claim first
(`:284`) and then submits the delete.

### 5.3 Trace C — baseline comparison, launch to support verdict

1. A launch resolves a target. `resolve_launch_target_views`
   (`api/src/transport_matters/harnesses/launch_target.py:55`) returns the strict `TargetResolution` plus a
   `LaunchVerification` cell built by `_launch_verification_cell` (`:72`), which
   replays **only** for `target_unverified_opt_in_required` or a configured model
   with no explicit request model.
2. `LaunchVerificationCoordinator.submit` (`api/src/transport_matters/launch_verification.py:118`) — never
   raises. It skips a diagnostic probe, a non-`VerificationCell`, and a missing
   provider or executor.
3. `_run_candidate` (`:175`) reads compatibility facts from the **live run**
   (`read_compatibility_facts(turn.storage_dir)`, per the project `CLAUDE.md`:
   *"Bundles read the live run, not the store"*), refuses a facts artifact naming
   another harness, and **skips unless** `range_position` is `above_ceiling` or
   `unknown`. Then it checks the usage-limit quota.
4. `_verify_under_lock` (`:280`) takes a per-cell `WorkspaceLock` and captures each
   due `RequestShape` **in sequence**.
5. `_capture_shape` (`:355`) records an attempt via `BaselineAttemptRecorder`, calls
   `self.harvest(...)` (`api/src/transport_matters/baseline_harvest.py`), then
   `require_persisted_baseline_for_version`, then `self.support_verdict_writer(...)`
   which **fails open with a logged exception**.
6. The comparison itself: `api/src/transport_matters/request_schema.py` mints the body schema;
   `transport_envelope.project_request_envelope` (`api/src/transport_matters/transport_envelope.py`) reduces
   the probe's `transport.json` to **names only** (protocol, method, host, path,
   query parameter names, header names, content-encoding tokens), each spelled as a
   key with `true` beneath it so a value change reads as a property change. A name
   `transport_redaction` would redact is **dropped, not redacted**, so an auth header
   arriving or departing is invisible by design.
7. `api/src/transport_matters/request_schema_comparison.py` (669) diffs reference against candidate;
   `api/src/transport_matters/request_schema_branch_alignment.py` (122) handles discriminator branches.
8. `api/src/transport_matters/ir_coverage.py` + `api/src/transport_matters/ir_coverage_tables.py` decide whether a lost position is read
   by a consumer: `modeled` / `normalized` / `unmodeled`. Consumers are an IR field
   (`ir_target`, checked against `api/src/transport_matters/ir.py`) or a browser reader of `provider_extras`
   (`ui_target`, checked against the TypeScript source). An unclassified position
   **still degrades**.
9. `assess_support_state` (`api/src/transport_matters/support_state.py:171`) folds body and envelope into one
   `SupportState` + findings. `fold_support_verdicts` (`:130`) folds across the two
   `RequestShape`s of one model.
10. `api/src/transport_matters/support_verdict_store.py` (283) persists; the launch view reads it back.

Timeouts, all in `api/src/transport_matters/launch_verification.py`: `_TURN_TIMEOUT_S = 180.0`,
`_CAPTURE_TIMEOUT_PER_SHAPE_S = 600.0`,
`_CAPTURE_TIMEOUT_S = 600 * len(RequestShape)`,
`_ATTEMPT_RECOVERY_WINDOW_S = 600.0`, `_OPERATION_TIMEOUT_S = 10.0`.

---

## 6. Persistence

### 6.1 Channels: one database per channel

From the project `CLAUDE.md`, resolved in `api/src/transport_matters/channel.py` (242) and `api/src/transport_matters/config.py` (318):

| channel | home | database | ports |
| --- | --- | --- | --- |
| stable | `~/.transport-matters` | `transport_matters` | 8787/8788 |
| preview | `~/.transport-matters-preview` | `transport_matters_preview` | 8797/8798 |
| dev | `~/.transport-matters-dev` | `transport_matters_dev` | 8807/8808 |

Canvas runs **preview**; the CLI defaults to **stable**. They share no rows. Inventory
is keyed by an `executor-id` minted per home (`api/src/transport_matters/harnesses/executor_identity.py`), so
querying the wrong channel's database yields an **empty inventory, not an error**.

### 6.2 Tables (30, from `api/migrations/versions/`)

`session`, `event`, `event_artifact`, `artifact`, `event_dead_letter`, `space`,
`space_git_identity`, `space_worktree`, `space_worktree_link`, `canvas`,
`run_lifecycle_event`, `run_live_status`, `wire_blob`, `wire_component_set`,
`wire_component_set_member`, `wire_exchange`, `wire_request_message`,
`wire_response_block`, `control_plane_grant`, `control_plane_action`,
`control_plane_delivery`, `harness_connection`, `harness_observation`,
`harness_target_observation`, `harness_target_snapshot`, `harness_access_observation`,
`harness_authentication_observation`, `harness_drift_evidence`,
`harness_executor_block`, `harness_enablement`.

`run_turn_boundary` was created and later dropped (revision `0035`).

`0001` establishes the `session` shape, including a `session_native_uq` unique index
on `(owner, run_id, provider, native_session_id)` and
`session_fork_ck CHECK ((parent_session_id IS NULL) = (forked_at_seq IS NULL))`.

### 6.3 Migration authoring style (important)

39 revisions, `0001`…`0038`, all raw SQL via `op.execute`. **Table names come from
module-level constants interpolated into the SQL**, so `op.create_table` never
appears and a naive `grep "CREATE TABLE <name>"` under-reports. To inventory tables
you must resolve the constants.

Mechanics (`api/src/transport_matters/session/migrate.py`): `apply_migrations` fast-paths when already at head
**without taking the lock**, then `_upgrade_under_lock` re-checks under
`_MIGRATION_ADVISORY_LOCK_KEY = 0x746D6D6967`. `migrations_dir()` probes
`parents[3]/migrations` then `parents[2]/migrations` so it works both from source and
from an installed wheel. `ensure_statement_stats` installs `pg_stat_statements`
whenever the store is migrated, best-effort and never fatal, motivated in-comment by
the 2026-09-05 reconcile-pass saturation.

### 6.4 Writers

| Table group | Writer |
| --- | --- |
| `wire_*` | `api/src/transport_matters/session/wire_store.py:write_wire_exchange` (`:117`), only ever called from `SessionWriter.submit_wire_exchange` |
| `run_lifecycle_event` | `api/src/transport_matters/controlplane/reap.py` (`persist_reaped_exit`, `persist_retracted_reap`, `persist_runtime_adoption`) and `SessionWriter`'s `RunLifecycleEmitter` |
| `run_live_status` | `api/src/transport_matters/live_status_observer.py` via `SessionWriter` |
| `harness_*` | `harnesses/*api/src/transport_matters/_store.py` (`ExecutorEvidenceStore` and friends) |
| `control_plane_*` | `controlplane/{grants,audit,delivery_store}.py` |
| `session`, `event`, `artifact` | `api/src/transport_matters/session/ingest.py`, `api/src/transport_matters/index/record_ingest.py` |

### 6.5 GC

`sweep_wire_store` (`api/src/transport_matters/session/wire_store.py:210`) is **sync**, takes
`LOCK TABLE wire_exchange IN SHARE MODE`, and deletes orphaned members → sets →
blobs, in that order. Its only caller is the `db` CLI command (`api/src/transport_matters/cli/db_cmd.py`).

### 6.6 Tier 1 (disk) is authoritative

`DiskStorageBackend` (`api/src/transport_matters/storage/disk.py:38`) is an *"Append-only JSONL index with
per-exchange artifact directories"*. Layout constants in `api/src/transport_matters/storage/disk_layout.py`.
Writes go through `api/src/transport_matters/atomic_io.py` (temp + rename, with `.tmp`/`.bak`/`.del`
suffixes). `redact_transport_artifacts` (`api/src/transport_matters/transport_redaction.py`) runs before the
transport artifact is written.

---

## 7. Concurrency and ownership

### 7.1 `runtime_id` and the lease

- `runtime_id` is minted once per Gateway process at boot and stamped on every
  managed `run-started` row.
- The Gateway holds `pg_advisory_lock(run_runtime_lock_key(runtime_id))` for its
  whole life. `run_runtime_lock_key` is a **SQL function**, named in Python only at
  `api/src/transport_matters/session/run_lifecycle_contracts.py:13`.
- The **only** Python caller is `PgRuntimeLivenessProbe.claim_dead`
  (`api/src/transport_matters/controlplane/runtime_liveness.py`), which runs
  `SELECT pg_try_advisory_xact_lock(run_runtime_lock_key(%s))`. Its docstring gives
  the reason for the transaction-level variant: *"A transaction-level lock conflicts
  with the gateway's session-level lock on the same key and is released with the
  transaction, so no unlock can be skipped by a failure inside the claim."*

**Absence is not death, a lock is.** A gateway inventory answers only for the runs
its own `RunManager` holds.

### 7.2 The single decision point

`claim_reap_authority` (`api/src/transport_matters/controlplane/lifecycle_authority.py:51`):

- yields `None` when either runtime id is missing;
- yields a claim **immediately** when `runtime_id == current_runtime_id`;
- otherwise defers to `liveness.claim_dead`.

`PgRunLifecycleAuthority.claim` reads the started row via
`GET_RUN_LIFECYCLE_START_FOR_OWNER_SQL`, scoped by owner + run_id + workspace_id.

### 7.3 Reconciliation

`reconcile_lifecycle_runs` (`api/src/transport_matters/controlplane/lifecycle_reconcile.py:110`). Seven outcome
buckets (`_Tally`, `:82`): `reaped`, `live`, `retracted`, `adopted`, `held`,
`unowned`, `unresolved`.

Distinctions that matter:
- **`held`** — the foreign runtime's lock did not acquire, so that gateway is alive.
  Never reap (`:179-181`).
- **`unowned`** — the row carries no `runtime_id` (a legacy row). Inert until a live
  inventory adopts it (`:168-170`).
- **`unresolved`** — the Gateway could not answer, or the exit row did not land.
  A failure to resolve runtime identity marks **every** run unresolved and returns
  early (`:126-128`).

Terminal Gateway states are hand-mirrored:
```python
# Mirrors RuntimeRunState in packages/runtime/src/domain/runtimeRun.ts by hand,
# like the LaunchKind literal lists: a new terminal state must land on both sides.
_TERMINAL_GATEWAY_RUN_STATES = frozenset({"TERMINATED", "EXITED", "FAILED"})
```
(`api/src/transport_matters/lifecycle_reconcile.py:56-58`)

Retraction: a run present in the inventory that has a standing reaped row gets
`retracted_reap_event(...)` (`:156-164`). Adoption: a present run with
`runtime_id is None` is stamped with the answering runtime (`:150-154`).

`pooled_lifecycle_reconciler` (`:212`) pins `started_before = datetime.now(UTC)` **at
construction** (`:220`) and reads only `MANAGED_LAUNCH_KINDS`, so a pass never
considers runs started after it was created.

`_lifecycle_runs` (`:199`) treats a reaped row as standing only when
`row.retracted_at is None` (`:205`).

### 7.4 Advisory lock keys in use (three, all distinct)

| Key | Where | Purpose |
| --- | --- | --- |
| `0x746D6D6967` ("tmmig") | `api/src/transport_matters/session/migrate.py` | serialize Alembic upgrades |
| `WIRE_COMMIT_WATERMARK_LOCK_KEY` | `api/src/transport_matters/session/wire_store.py:121` | order wire commits against replay cursors |
| `run_runtime_lock_key(runtime_id)` (SQL fn) | Gateway session lock / `api/src/transport_matters/runtime_liveness.py` xact lock | prove a gateway is alive |

### 7.5 Other concurrency facts

- `WireStoreObserver` serializes to **one** in-flight write
  (`api/src/transport_matters/wire_store_observer.py:132`, `:311-315`), budgeted against the pool reserve at
  `api/src/transport_matters/addon_runtime.py:79`.
- `ShardedCommitDispatcher` uses `shard_count = session_pool_max_size - 2`
  (`api/src/transport_matters/addon_runtime.py:375`ff).
- Losing the lease keeps every PTY alive; the Gateway reacquires the same
  `runtime_id` with backoff and answers `runtime_unleased` (503) to new managed
  creates until it holds the key (project `CLAUDE.md`).
- `api/src/transport_matters/bounded_call.py` (62) and `api/src/transport_matters/controlplane/async_wait.py` are the timeout primitives.
- `api/src/transport_matters/lock.py` (153) is `WorkspaceLock`, used by launch verification (`:280`).

---

## 8. Conventions a newcomer will violate

These are enforced or explicitly documented. Violating them fails tests or review.

1. **Import DAG, no cycles** (`api/CLAUDE.md`):
   `ir → adapters → rules → pipeline → storage → breakpoint → server`.
   `api/src/transport_matters/ir.py` imports nothing from `transport_matters`. `api/src/transport_matters/canonicalization.py` is
   stdlib-only.

2. **`storage` must never import `session`.** The snapshot sink is injected at
   `load_runtime()`. If you need Postgres from a storage path, add a sink in
   `api/src/transport_matters/storage/exchange_sink.py` and subscribe from a composition-level module
   (`api/src/transport_matters/addon_runtime.py` or `api/src/transport_matters/wire_store_observer.py`, whose docstring names itself
   *"Composition level module, like `addon_runtime`: this keeps `storage` free of
   `session` imports"*).

3. **Module privacy is lint-enforced.** `api/src/transport_matters/test_private_import_boundary.py` walks the
   AST of every non-test file under `api/src/transport_matters` and `api/tests` and
   fails on any `from ... import _name` or import of a `_module`
   (`api/src/transport_matters/test_private_import_boundary.py:23-52`). Test files are exempt, where "test" means
   basename starting `test_`, ending `api/src/transport_matters/_support.py`, containing `fixtures`, or equal to
   `api/src/transport_matters/conftest.py` (`:13-20`). To share a private, **promote it to a public name**.

4. **Type mirrors are lint-enforced.** `api/src/transport_matters/test_type_mirrors.py` compares Python
   definitions against TypeScript in three places (`:20-28`): IR + overrides against
   `www/packages/core/src/types/`, activity against
   `packages/contract/src/activity/wire.ts`, and run input against
   `packages/runtime/src/service/RunInputDelivery.ts`. Adding an IR field or an
   override kind in Python alone will fail.

5. **Hand-mirrored literals.** `_TERMINAL_GATEWAY_RUN_STATES`
   (`api/src/transport_matters/lifecycle_reconcile.py:58`) and the `LaunchKind` lists are mirrored by hand, and
   the comment says so. A new terminal state must land on both sides.

6. **Async boundary** (`api/CLAUDE.md`): I/O is async (hooks, routes, storage); pure
   computation is sync (pipeline actions, rule matching, adapter parsing). Do not
   make a pure function async for symmetry.

7. **Frozen IR.** Return new instances. And remember `empty_message_placeholder`'s
   warning (`api/src/transport_matters/ir.py:105`): frozen does not freeze nested containers.

8. **Errors:** domain exceptions in `api/src/transport_matters/exceptions.py`, translated at the FastAPI
   layer; always chain with `raise X from original`; never swallow silently
   (`api/CLAUDE.md`). The exception to "never swallow" is explicit and documented:
   the best-effort observer paths (§10.1).

9. **API errors go through the helpers.** `api_error(code, message, details)`
   (`api/src/transport_matters/api/v1/errors.py:14`) and `raise_api_error(...)` (`:22`). Do not construct a
   bare `HTTPException` with a string detail on a v1 route.

10. **Colocated unit tests.** `api/src/transport_matters/foo/test_bar.py` lives next to
    `api/src/transport_matters/foo/bar.py`. Integration tests live in `api/tests/integration/`.

11. **Builtin generics only** (`list[str]`, `X | None`). Annotate all return types.
    Any `Any` needs a comment saying why — see
    `api/src/transport_matters/live_status_observer.py:12` (*"Any: provider live payload JSON is opaque"*).

12. **ABC for runtime dispatch (adapters, storage), Protocol for shape-only
    contracts** (`api/CLAUDE.md`). `ProviderAdapter` is an ABC
    (`api/src/transport_matters/adapters/base.py`); `RuntimeInventoryReader` is a Protocol
    (`api/src/transport_matters/lifecycle_reconcile.py:64`).

13. **Tests cannot point at a real database.** `guard_pytest_session_store_url`
    (`api/src/transport_matters/session/pool.py:184`) raises under `PYTEST_CURRENT_TEST` unless the database
    name starts with `TEST_DB_PREFIX`.

---

## 9. Public contract vs internal

### 9.1 Public — MCP tools

The stable agent-facing surface. 14 tools in `api/src/transport_matters/api/v1/controlplane_mcp.py:397`:
`agents`, `workspace_summary`, `whoami`, `harnesses`, `roster`, `conversation`,
`prompt`, `wait_for_reply`, `launch`, `close`, `interrupt`, `watch`, `unwatch`.
Two more MCP servers exist: `api/src/transport_matters/api/v1/space_mcp.py` and `api/src/transport_matters/api/v1/browsing_mcp.py`.

Changing a tool's name, arguments, or result shape is a **contract change**.

### 9.2 Public — HTTP

- `/v1/...` routes assembled in `api/src/transport_matters/api/v1/router.py`. Error bodies are `ApiError`
  (`api/src/transport_matters/api/v1/session_models.py`) produced by `api_error` (`api/src/transport_matters/api/v1/errors.py:14`).
- **`/v1/capture/*` is a private-but-cross-language contract**
  (`api/src/transport_matters/api/v1/capture_rpc_routes.py:93`): the only consumer is
  `packages/runtime/src/adapters/CaptureRpcClient.ts`. Both sides must move together,
  including the timeout relationship documented at `CaptureRpcClient.ts:21-22`.
- The Gateway's own HTTP surface (`packages/runtime/src/server/runtimeRouter.ts`) is
  proxied through `RunRouteProxy` and is not directly public.

### 9.3 Public — rejection codes

`ResolutionRejectionCode` is a **closed 13-member literal**
(`api/src/transport_matters/harnesses/resolver_contracts.py`), unioned into `RunRequestRejectionCode`
(`api/src/transport_matters/exceptions.py:21-23`). `RUN_REQUEST_ERROR_CODES` (`api/src/transport_matters/exceptions.py:31`) is derived by
`get_args` over the literals and deduped with `dict.fromkeys`, so adding a member to
the literal automatically widens the tuple. `RUN_REQUEST_UNAVAILABLE_ERROR_CODES`
(`:43`) is the hand-maintained subset that maps to 503 rather than 4xx.

### 9.4 Public — the on-disk artifact layout

`api/src/transport_matters/storage/disk_layout.py`'s filenames are read by the CLI, the inspector, and
`read_compatibility_facts`. Renaming one breaks readers outside `api/`.

### 9.5 Public — the mirrored types

Anything listed in `api/src/transport_matters/test_type_mirrors.py:20-28` is a cross-language contract.

### 9.6 Internal

Everything under a `_` prefix; every `*api/src/transport_matters/_test_support.py`; the entire `cli/`
implementation surface below its typer commands; the raw SQL constants in
`session/*api/src/transport_matters/_statements.py`.

---

## 10. Landmines

### 10.1 Fail-open is the design, not a bug

These paths deliberately swallow. Do **not** "fix" them into raising:

| Path | Citation |
| --- | --- |
| `parse_request_ir` returns `None` on parse failure | `api/src/transport_matters/request_pipeline.py` |
| `run_pipeline` returns the original IR on any override exception | `api/src/transport_matters/request_pipeline.py:64` |
| `prepare_outbound_request` returns original IR, no audit, no bytes | `api/src/transport_matters/request_pipeline.py:91` |
| `_fan_out` logs and swallows per subscriber | `api/src/transport_matters/storage/exchange_sink.py` |
| `_record_wire_failure` counts and logs, never raises into capture | `api/src/transport_matters/session/writer.py:318` |
| `load_capture_runtime` swallows all startup failure | `api/src/transport_matters/addon_runtime.py:496` |
| `run_startup_pass` logs and returns `None` | `api/src/transport_matters/startup_passes.py:52` |
| `LaunchVerificationCoordinator.submit` never raises | `api/src/transport_matters/launch_verification.py:118` |
| `support_verdict_writer` fails open with a logged exception | `api/src/transport_matters/launch_verification.py:355` |
| `ensure_statement_stats` never fatal | `api/src/transport_matters/session/migrate.py` |

The rule behind them: **the wire path never fails because of an observer.**

### 10.2 Fail-closed is also the design, in one place

`apply_overrides` (`api/src/transport_matters/overrides/__init__.py:156`) is a **transaction**. Every operation
is required; one miss rolls back the entire batch and returns the original IR. Every
audit entry then reads `applied: false`. A rewrite shadowed by a disable of its own
target in the same batch is audited as not applied and is **never** a miss
(`_shadowed_targets`, `:198`), so disabling a tool that still carries an edited
description keeps working.

Index-based overrides (`system_part_*`, `message_text`) always refer to positions in
the **original** IR; when earlier overrides remove items, later indices are adjusted
(`api/src/transport_matters/overrides/__init__.py:166-171`).

### 10.3 Thread and loop boundaries

Capture runs on the mitmproxy thread. `SessionWriter` owns an asyncio loop.
`_raise_if_target_loop` / `_require_target_loop` (`api/src/transport_matters/session/writer.py`) enforce which
loop each method may be called from. Calling a writer coroutine directly from the
proxy thread, or a blocking facade method from the writer loop, deadlocks. The safe
idiom is `asyncio.run_coroutine_threadsafe` — `_make_exchange_cursor_sink` /
`WireStoreObserver._schedule` (`api/src/transport_matters/wire_store_observer.py:306`).

### 10.4 Ordering constraints

- **Request is persisted to disk before it is forwarded**
  (`api/src/transport_matters/exchange_recorder/__init__.py:~378-380`). Moving the persist after the forward
  loses the boundary snapshot on a crash.
- `close_capture_runtime`'s twelve-step order (`api/src/transport_matters/addon_runtime.py:605`) is load-bearing:
  sinks are cleared **last**, the writer closes **after** the observers drain.
- `_PASS_TASKS` teardown order (`api/src/transport_matters/startup_passes.py:45`) — verification awaits refresh.
- `write_wire_exchange` takes the watermark lock **after** blobs and sets, **before**
  the exchange row (`api/src/transport_matters/session/wire_store.py:121`).

### 10.5 Stale evidence

- Harness state refreshes only at backend startup, per channel
  (`api/src/transport_matters/startup_passes.py`). Force a pass with
  `refresh_harness_state(ExecutorEvidenceStore(url, pool))`.
- `_refresh_harness` returns early when the harness has no embedded release, **before**
  the probe that enumerates models. Result: an observation row with the fallback
  revision, zero target observations, and a launch view reporting
  `target_unavailable`.
- Inventory is keyed by `executor-id` per home. Wrong channel → **empty inventory,
  not an error**. Orphan ids from a wiped home are harmless.
- Bundles read the live run (`read_compatibility_facts(turn.storage_dir)`), not the
  store. A stale store changes what the launch view *offers* but never what the
  evidence *says*.

### 10.6 Comparison direction

`assess_support_state` is asymmetric — reference on the left
(`api/src/transport_matters/support_state.py:171`, *"Argument order is the whole contract"*). A candidate that
merely **adds** a field must never answer for the reference's lack of it. The
worst-of-both symmetric fold lives only in
`baseline_comparison.compare_model_pair`, which is right for two peer models of one
harness and wrong everywhere else.

### 10.7 The delivery claim is consumed

`LivePromptDeliveryBindings.claim` consumes. Calling it twice for one exchange loses
the delivery id. This is why `_retained_claim` exists (`api/src/transport_matters/wire_store_observer.py:210`)
and why the release is gated on `result.ok and write.response_complete` (`:279`).
Bounded FIFO eviction (`max_retained_claims = 256`) means a very old live exchange
can lose its retained claim and fall back to claimless persistence — accepted, and
documented at `api/src/transport_matters/wire_store_observer.py:21-26`.

### 10.8 `handle_http_error` strands provisionals on purpose

It retains an incomplete provisional exchange and finalizes only when
`_http_response_capture_is_complete` proves a terminal payload or an exact
content-length (`api/src/transport_matters/addon_handlers.py:~585`). Those rows are neither finalized nor
deleted; that is the direct cause of §10.7's bounded retention.

### 10.9 `captured_nothing` is derived at read time, never stamped

`captured_nothing = turns >= 1 and exchanges == 0`, computed by `project_roster`
(`api/src/transport_matters/controlplane/roster_projection.py`) from a turn count per run in `event` and an
exchange count per run in `wire_exchange`. It is derived rather than stamped because
exchange persistence is asynchronous to harness exit, so a fact written at release
could record a false zero and never correct itself. Derived, it heals on the next
roster read and covers runs already in the database. It is **advisory and never
fatal**.

### 10.10 Migration greps lie

`op.create_table` never appears; table names are module-level constants interpolated
into raw `op.execute` SQL. Resolve the constants before concluding a table does not
exist. `run_turn_boundary` exists in history and was dropped at `0035` — finding its
`CREATE` proves nothing.

### 10.10a The shared proxy silently degrades, and breakpoints do not follow

If `app.state.shared_proxy_manager` is `None` — it failed to start, or a test built
the app without one — `create_capture_registry` falls back to the per-run path and
logs **once** (`api/src/transport_matters/capture_rpc.py:445-446`). Every run then
costs its own mitmdump process and writer pool. The only signal is that single
warning line, so a degraded backend looks healthy.

Overrides reach canvas runs because `manager.by_run_id` lists them
(`api/src/transport_matters/shared_proxy/registration.py:130`). **Breakpoints do
not**: arm, pause and release are process-local and the shared proxy's control
channel carries no message for them (`TLDR.md`, "A canvas run's proxy is a
binding"). Do not assume a feature that works on a CLI-launched run works on a
canvas run.

### 10.11 Two backends on one channel database

They cannot reap each other's live runs (#610), because reaping requires either the
answering gateway's own `runtime_id` stamp or a successful
`pg_try_advisory_xact_lock` on the foreign key. But they *will* both run
reconciliation, both hold pools against the same database, and both apply migrations
(serialized by the migration lock). Prefer one backend per channel.

### 10.12 File size limits are hard

Per the global instructions: new files never exceed ±700 lines, and files already
over 700 must be refactored **before** new code is added. Several modules sit right
at the edge — `api/src/transport_matters/baseline_store.py` (699), `api/src/transport_matters/desktop_runtime.py` (699),
`api/src/transport_matters/addon_handlers.py` (698), `api/src/transport_matters/credential_broker.py` (695), `api/src/transport_matters/session/writer.py` (685),
`api/src/transport_matters/live_status_observer.py` (684) — so adding to any of them means refactoring first.

### 10.13 `Message.role` is not an enum

Deliberate. Do not tighten it; a provider inlining an unmodeled role must be
preserved verbatim rather than dropping the request (`api/src/transport_matters/ir.py`).

---

## 11. Where to start for a given change

| Task | Start here |
| --- | --- |
| Add a provider | `api/src/transport_matters/adapters/base.py`, then register in `api/src/transport_matters/adapters/__init__.py` (order matters, first match wins) |
| Add an IR field | `api/src/transport_matters/ir.py` **and** `www/packages/core/src/types/ir.ts`; `api/src/transport_matters/test_type_mirrors.py` will tell you if you missed one |
| Add an override kind | `api/src/transport_matters/overrides/__init__.py` (kind + `_PRIORITY` + `_apply_*`), the TS mirror, and decide whether it is a message operation |
| Change what is captured | `api/src/transport_matters/addon_handlers.py:handle_http_request` gate (~`:207`) |
| Add a persisted wire field | `api/src/transport_matters/session/wire_store.py:WireExchangeWrite`, a migration, and `api/src/transport_matters/wire_store_observer.py:_submit_exchange` (`:153`) |
| Add an MCP tool | `api/src/transport_matters/api/v1/controlplane_mcp.py:397` + a verb on `api/src/transport_matters/controlplane/service.py` |
| Change launch rejection behaviour | `api/src/transport_matters/harnesses/resolver.py:473` (order) and `api/src/transport_matters/harnesses/resolver_contracts.py` (the closed literal), then `api/src/transport_matters/exceptions.py:43` for the 503 subset |
| Change reap behaviour | `api/src/transport_matters/controlplane/lifecycle_authority.py:51` — the single decision point |
| Change how a canvas run gets its proxy | `api/src/transport_matters/shared_proxy/registration.py` — supply a starter/supervisor, never a second copy of `prepare_captured_run` |
| Add a startup pass | `api/src/transport_matters/startup_passes.py:45 _PASS_TASKS` |
| Add a table | a new `api/migrations/versions/00NN_*.py` using the constant-interpolation style, plus a DAO in `session/` |
