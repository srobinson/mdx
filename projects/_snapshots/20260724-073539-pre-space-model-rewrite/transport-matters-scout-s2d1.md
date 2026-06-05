# Scout S2d.1 — drift-emitter seam wiring

Baseline main @ c8fe0094 (S2d merged, PR#296). Scope: wire the four drift-evidence
emitter call sites into the live paths. Emission/recording only; no automatic block
creation, no `match_release` call (S2f). Tree pristine, no source writes made.

One brief correction: `transcript_failure_is_drift` lives in
`harnesses/blocks_store.py`, not `session/quarantine.py`. It wraps
`session/quarantine.is_storage_plane` deliberately so the pure vocabulary
(`harnesses/blocks.py`) never imports the storage plane. Reuse it from there.

## Reuse Map

**S2d machinery to reuse verbatim (no new emit path):**

- `harnesses/blocks.py` — `wire_parse_drift`, `transcript_reader_drift`,
  `session_bootstrap_drift`, `actuation_drift`. All share
  `_SeamEvidenceFields` (kwargs: `evidence_id`, `executor_id`, `harness_id`,
  `run_id`, `evidence_digest` (sha256 hex), `observed_at`, `capture_safe`,
  optional `exchange_id`/`release_id`/`route_id`/`model_id`/`normalized_version`).
  Resolved context stays None until S2f; `attribute_drift_evidence` then routes
  everything to `pause_release`, which is correct and untouched by this slice.
- `harnesses/blocks_store.py` — `ExecutorBlockStore` (needs `database_url` +
  async pool), `emit_drift_evidence(store=, audit=, evidence=)` (async; store
  write off-loop via `asyncio.to_thread`, audit mirror idempotent by
  `uuid5(evidence_id)` dispatch id), `transcript_failure_is_drift`.
- `controlplane/audit.py` — `ControlPlaneAuditWriter(session_pool)` satisfies the
  `ControlPlaneAuditSink` protocol; already constructed in `main.py` lifespan
  (`app.state.control_plane_audit`).
- **Best-effort emission precedent:** `run_lifecycle.py`
  `emit_run_lifecycle_best_effort` + `RunLifecycleEmissionFailureCounter` —
  swallow every failure, count, log, never fail the producing operation. The
  drift wrapper should be the same shape (one shared helper, not four copies).
- **Injection precedent for the tailer:** `TranscriptTailer` already takes
  injected callables (`snapshot`, `quarantine_window`, `submit_batch`) built at
  `addon_runtime._start_session_capture`, explicitly to keep storage APIs out of
  the index layer (DAG). The drift hook must follow this pattern.
- Test support: `harnesses/connections_test_support.make_drift_evidence`,
  `session/testing.py` migration harness (0023 table exists,
  `session/test_harness_drift_evidence_migration.py`).

**Critical wiring fact — nothing constructs the store today:** no production code
constructs `ExecutorBlockStore` (or any harness store), and there is **no
production source of `executor_id`** anywhere (probes/connections receive it as a
parameter; connections are never created by production code yet). S2d.1 must
either (a) mint a stable local executor identity (decision needed: derived
machine id vs config), or (b) treat executor identity as a prerequisite gap.
Emission cannot be wired without resolving this; flagging as the slice's one
open decision for the orchestrator.

**Process topology (governs where store+sink can live):**

- Wire parse + transcript tailer run in the **mitmproxy addon process**
  (`addon_runtime.load_runtime`; owns `create_async_pool()` for `SessionWriter`,
  so it can host an `ExecutorBlockStore` + `ControlPlaneAuditWriter`).
- Actuation runs in the **API server process** (`main.py` lifespan already has
  `session_pool` + `control_plane_audit`). Cheapest seam to wire.
- Session bootstrap runs via `prepare_captured_run()` from two hosts: the API
  server (`capture_rpc.CaptureLeaseRegistry`, Postgres guaranteed by
  `check_session_store`) and the **detached CLI** (`run_captured_run_on_local_tty`,
  Postgres NOT guaranteed — capture works without web/Postgres by design).
  Emission there must degrade to a silent no-op when no store is available.

## Quality Map

Hygiene assessment (scoped to the eleven seam/machinery files; no repo fanout):

- `index/tailer.py` is **677 LOC — 23 under the 700 hard limit**. Any inline
  emitter code pushes it over, which mandates refactor-before-add. The injected
  callable pattern avoids both the LOC breach and an index→harnesses import
  edge. Do not add drift logic inside tailer.py beyond invoking one injected
  hook.
- `adapters/anthropic.py` (573) and `exchange_stats.py` (168) are healthy;
  detection belongs at call sites, keeping adapters as pure parse (per
  api/CLAUDE.md async boundary: pure computation stays sync/pure).
- Duplication risk: four seams × (build fields → construct → best-effort emit)
  is four near-identical blocks. One shared helper (a small `DriftEmitter`
  holding store+sink+executor identity, with a `emit_best_effort(constructor
  result)` method mirroring `emit_run_lifecycle_best_effort`) is the DRY seam.
  Natural home: a new small module beside `blocks_store.py` (e.g.
  `harnesses/drift_emitter.py`), NOT inside blocks_store (keeps I/O store free
  of scheduling policy) and NOT per-seam copies.
- Package back-edge caution: `harnesses/blocks_store` imports
  `controlplane/audit` (models + sink protocol). Wiring `controlplane/
  prompt_delivery` or `launch_service` to import `harnesses/blocks_store`
  creates a controlplane↔harnesses package cycle. Inject the emitter as a port
  (like `PromptDeliveryLedgerPort`), never a direct import from controlplane.
- `blocks.py`/`blocks_store.py`/`quarantine.py`/`run_lifecycle.py`/`
  prompt_delivery.py`: clean, well under thresholds, clear ownership. No
  pre-refactor needed anywhere except the tailer LOC constraint above.

## Plan

### Per-seam audit

**Seam 1 — wire parse (`adapters` ProviderAdapter, addon process)**

- (a) Detectability: **partial today.**
  - `unknown_request_field`: detectable now — `AnthropicAdapter.inbound_request`
    captures unmapped top-level keys into `ir.provider_extras`
    (`_MAPPED_REQUEST_KEYS`), and `UnknownBlock` marks unknown content shapes.
    Caveat: extras/UnknownBlock are round-trip preservation by design and may
    include long-standing benign fields; a naive "any extras ⇒ drift" emitter
    will fire on every request. Needs either a small allowlist of known-benign
    extras per adapter or acceptance that evidence is idempotent-deduped (see
    dedup note below). Codex request side tracks `extra_fields` per item
    similarly (`codex/request_parser.py`).
  - `unknown_response_event`: **not detectable today** — both SSE loops
    (`AnthropicAdapter._inbound_response_sse`, `codex/response_parser.py`)
    silently ignore unrecognized event types. Needs a closed known-event
    allowlist per adapter (anthropic: message_start, content_block_start/
    delta/stop, message_delta, message_stop, ping, error; codex: the
    CODEX_*_EVENT_TYPES set) and a way to surface unknowns. Malformed
    bytes/transport failure stays generic parse failure
    (`parse_request_ir`/`parse_response_ir` return-None paths) — **no drift
    constructor there**, per the `wire_parse_drift` docstring.
- (b) Call site: NOT inside the adapters (keep them pure). Post-parse at the
  live boundary: request side in `addon_handlers.handle_http_request` after
  `parse_request_ir`; response side where `exchange_stats.parse_response_ir`
  returns, and the codex websocket path in `codex/exchange.py`. One injected
  emitter on the addon runtime; adapters gain only a pure
  "unknown shapes observed" report (e.g. returned alongside or derived from IR).
- (c) Async boundary: addon handlers are async on mitmproxy's loop —
  `asyncio.create_task(emitter.emit_best_effort(...))` fire-and-forget with the
  run_lifecycle-style swallow/count/log wrapper. Never awaited inline on the
  proxy hot path; a failed emit only logs.
- (d) Run correlation: `binding.run_id` (`ProxyRunBinding`) or
  `get_settings().run_id` fallback, exactly as `handle_http_request` line
  computing `run_id` does; `exchange_id` from `request_state.provisional_exchange_id`.
  `harness_id` from binding.harness / adapter name mapping (anthropic→claude,
  codex→codex).
- (e) Acceptance test: feed a request body with an unmapped top-level field /
  an SSE stream with an alien event type through the handler seam with a fake
  emitter injected; assert exactly one typed `wire_contract_drift` evidence
  with the right detail code and run correlation, and assert the exchange
  still persists when the emitter raises (red-first: alien event today
  produces no emission).

**Seam 2 — transcript reader (`index/tailer.py`, addon process, tailer thread)**

- (a) Detectability: **yes for `transcript_record_shape_mismatch`** — in
  `_handle_commit_failure`, any exception where
  `transcript_failure_is_drift(exc)` is True (non-storage-plane raise from
  `_plan_ingest_records`/normalize/build) is exactly the drift condition; the
  storage-plane path stays quarantine's. **Partial for
  `transcript_locator_mismatch`** — the concrete detectable condition today is
  the read-back session_id divergence in `register_session_cursor` (logged
  "read-back session_id divergence"); that function is async (API/addon loop),
  which is convenient. If the orchestrator wants locator mismatch scoped to
  something else, say so; otherwise wire the divergence branch.
- (b) Call site: inject an `on_drift(binding, exc | detail)` callable into
  `TranscriptTailer.__init__` (same pattern as `quarantine_window`), invoked in
  `_handle_commit_failure` when `transcript_failure_is_drift(exc)` — emission
  alongside, not replacing, the existing raise/quarantine flow. Divergence
  branch in `register_session_cursor` calls the emitter directly (it's async).
  Built and injected at `addon_runtime._start_session_capture`. This respects
  the 677-LOC ceiling and the index-layer DAG.
- (c) Async boundary: **the riskiest seam.** `_handle_commit_failure` runs on
  the tailer thread with no loop. The injected callable must hand off to the
  addon loop via `asyncio.run_coroutine_threadsafe` (the loop is available at
  `_start_session_capture` time, where `SessionWriter(create_async_pool(),
  loop=loop)` is built) and NOT wait on the future. Blocking or raising there
  would stall every cursor poll. The wrapper swallows scheduling failures too.
- (d) Run correlation: `cursor.binding.run_id` / `binding.session_id`;
  harness from `cursor.binding.provider`/`harness`.
- (e) Acceptance test: register a cursor whose adapter `normalize` raises a
  non-storage exception; drive `poll()`; assert one
  `transcript_contract_drift/transcript_record_shape_mismatch` emission with
  the cursor's run id AND that quarantine/retry behavior is byte-identical to
  today (existing `test_tailer_quarantine.py` must stay green). Storage-plane
  exception ⇒ zero emissions. Divergence test through
  `register_session_cursor` with a re-bind returning a different session_id.

**Seam 3 — session bootstrap (session lifecycle via `prepare_captured_run`)**

- (a) Detectability: **not detectable today — documented gap.** TM prepares the
  proxy and spawn spec, but the harness client is spawned by the caller
  (CLI tty / gateway PTY); a harness rejecting the minted `--session-id` or the
  seeded codex rollout surfaces only as an undifferentiated client exit.
  Prepare-time failures (`CapturedRunBindConflict`,
  `CapturedRunProxyStartTimeout`) are TM-side operational failures, not harness
  contract rejections — emitting drift for them would be false evidence.
  `ContinuationSessionNotFound` (resume path,
  `api/v1/run_continuation.py`) is likewise a TM-side lookup miss, not
  `session_resume_rejected`. Recommendation: do NOT force an emission; land the
  constructor call sites as a documented gap with an acceptance-test stub
  proving the seam contract (given a classified bootstrap/resume rejection
  signal, the emitter records `session_contract_drift`), and record the missing
  classifier (harness exit taxonomy) as follow-up scope. Forcing a heuristic
  ("client exited fast after bootstrap") would emit unattributable evidence.
- (b) Call site (for the stub/wiring): `capture_rpc.CaptureLeaseRegistry` —
  it already owns best-effort lifecycle emission (`_emit_lifecycle`,
  RUN_STARTED/RUN_EXITED with exit_reason/error) and is the one bootstrap host
  with guaranteed Postgres. The CLI detached path degrades to no-op (no store).
- (c) Async boundary: registry methods are async on the API loop — direct
  fire-and-forget task, same wrapper.
- (d) Run correlation: `spawn_spec.run_id`; harness from request.
- (e) Acceptance test: stub-level — inject a fake emitter into the registry,
  simulate the classified rejection signal, assert typed emission; assert
  prepare/release flows never fail when the emitter raises.

**Seam 4 — actuation (`controlplane/prompt_delivery.py`, API server process)**

- (a) Detectability: **yes, with a reason taxonomy.** The deliver pipeline
  already centralizes outcomes as `PromptReceipt`. Drift =
  harness-contract-shaped rejection: gateway accepted the call but the harness
  rejected the actuation (`outcome.status == "failed"` with a harness reason,
  `GatewayResponseError`). NOT drift (operational): `busy_gateway`
  (GatewayUnavailableError), `proof_unavailable`, `delivery_ledger_unavailable`,
  proof timeout. The wiring must carry an explicit closed mapping from receipt
  reasons to `actuation_rejected` so operational noise never becomes contract
  evidence. `startup_prompt_rejected`: the launch path
  (`launch_service._resolve_first_prompt` → failed first-prompt receipt) is the
  detection point, distinct from post-launch prompt delivery.
- (b) Call site: NOT inside `VerifiedPromptDelivery` (keep it
  gateway+proof-focused; also avoids the harnesses import back-edge). Wire at
  the owning callers: `controlplane/service.py` `_deliver_prompt_target`
  receipt handling (actuation_rejected) and `launch_service.py` first-prompt
  resolution (startup_prompt_rejected), with the emitter injected as a port on
  service construction in `main.py` (store from `session_pool` +
  `app.state.control_plane_audit`). Alternative if reviewers prefer one
  choke point: a receipt-observing decorator around the
  `PromptDeliveryCoordinatorPort`; either way, injected, never imported.
- (c) Async boundary: native async context — `asyncio.create_task` fire-and-
  forget with the shared wrapper; never await inline before returning the
  receipt (a slow Postgres emit must not delay prompt actuation or the API
  response).
- (d) Run correlation: `run_id` is a direct `deliver` argument;
  `exchange_id` = `receipt.wire_exchange_id`; owner/actor from principal.
- (e) Acceptance test: drive `deliver` with a fake gateway returning a
  harness-shaped failure ⇒ one `launch_contract_drift/actuation_rejected`
  emission; `busy_gateway`/proof-timeout ⇒ zero emissions; emitter raising ⇒
  receipt unchanged and delivery flow unaffected. Launch first-prompt failed
  receipt ⇒ `startup_prompt_rejected` (red-first: none of these emit today).

### Cross-cutting design points

- **One shared emitter helper** (`harnesses/drift_emitter.py`, ~80 LOC):
  holds `ExecutorBlockStore + ControlPlaneAuditSink + executor_id`, exposes a
  best-effort submit (fire-and-forget task on a provided loop, plus a
  thread-safe variant for the tailer via `run_coroutine_threadsafe`), swallow/
  count/log per `RunLifecycleEmissionFailureCounter` precedent. All four seams
  call constructors + this helper; zero new emit paths.
- **Evidence identity/dedup:** derive `evidence_id` deterministically (uuid5
  over seam + run_id + detail + evidence_digest) so a hot loop (e.g. every
  request carrying the same unknown field) collapses into idempotent no-op
  inserts instead of unbounded rows; `record_drift_evidence` already makes
  replays no-ops and divergent reuse a hard error.
- **`evidence_digest`:** sha256 of the raw evidence excerpt that stays in the
  run directory (wire bytes / transcript window / receipt payload); only the
  digest rides to Postgres, per the structural redaction rule. `capture_safe`
  = whether that raw evidence was durably captured tier-1.
- **Live-path risk verdict:** wiring is safe **only** as injected fire-and-
  forget with swallow-all wrappers. Three concrete hazards for the builder:
  (1) tailer thread → loop handoff must never wait or raise
  (`run_coroutine_threadsafe` result discarded); (2) no controlplane→harnesses
  or index→harnesses imports — ports/callables only (package cycle + DAG);
  (3) tailer.py at 677 LOC cannot absorb inline logic. A failed or slow emit
  must be provably invisible to parse/read/bootstrap/actuation — every
  acceptance test needs the "emitter raises ⇒ live path unchanged" assertion.
- **S2f leak check:** no `match_release`, no `block_from_evidence`, no
  automatic block creation anywhere in this slice; `attribute_drift_evidence`
  stays uncalled by seam code. Resolved-context fields stay None.
- **Open decision (blocker-adjacent):** production `executor_id` source does
  not exist; neither does any production `ExecutorBlockStore` construction.
  The slice needs a decision on executor identity (stable local id: config
  value vs derived machine identity) before the first emission can be real.

### Suggested build order

1. Executor identity decision + `drift_emitter.py` helper with unit tests
   (including thread-safe submit and swallow-on-failure).
2. Seam 4 actuation (cleanest host: API process, everything on app.state).
3. Seam 1 wire parse (allowlist detectors + addon runtime construction).
4. Seam 2 transcript reader (injected hook; most delicate, gate on existing
   quarantine suite unchanged).
5. Seam 3 bootstrap stub + documented gap.
   Gates per repo recipe: `just check` + `just test-affected` in the loop;
   full `just check` + `just test` pre-merge.
