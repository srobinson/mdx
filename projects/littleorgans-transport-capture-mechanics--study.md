# littleorgans transport capture mechanics study

Status: COMPLETE

## Evidence boundary

- Experimental source: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
- Commissioned exact commit: `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55`
- Commit subject: `fix(auth): close credential review residuals`
- Inspection method: immutable `git show <sha>:<path>` objects and `git ls-tree` inventories, with no checkout
- Source baseline after research: clean and unchanged
- Mode: read only
- Excluded: every `NOTES/` path
- Product constraint: learn from this source without a runtime, package, release, process, CLI, or invocation dependency on `tm`

Validity rule: every experimental fact, mechanism, defect, test symbol, and recommendation below is pinned to `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55`. A cited path means the blob at `a252df24:<path>`. No finding relies on the live worktree or a later tree.

### Correction of the prior baseline

The prior audit mistakenly recorded `ed099336ebfa9e72da32ed547b29b932f077ccbd`. The two commits are divergent, with common ancestor `101287bf880d8f2157d5a67b8f91e3d306d78260`. Neither commit is an ancestor of the other.

The immutable tree comparison establishes why the mechanics findings remain valid at the commissioned commit:

- All 84 normalized path and symbol references across 57 files exist at `a252df24`.
- Every cited file has the same blob ID at `a252df24` and `ed099336`.
- The only `ed099336` only entry beneath `api/src/transport_matters` is the unrelated `harnesses/test_inventory_vocabulary.py`.
- Other changed entries are root documentation, shared harness vocabulary, and TypeScript UI files. None supports a report finding.
- No later only `ed099336` capture evidence appears below.

## Verdict

Transport capture belongs in littleorgans as a first class product capability. The experiment proves several mechanics, especially provider interposition, loss tolerant adapters, provisional request capture, response streaming, transcript snapshots, and crash recovery. Those mechanics are useful source material.

The experimental composition should not migrate as a unit. Its process topology, identity scheme, storage authority, environment handling, security posture, and capture failure policy need a fresh design under littleorgans ownership.

The highest value finding is the outbound durability boundary. The experiment tries to persist a provisional request before the proxy hook returns, but a failed write only logs and returns `None`. Provider traffic still proceeds. Mandatory capture requires a durable acknowledgement before provider release. Derived projections may remain best effort after that acknowledgement.

## Current end to end mechanics

### 1. Launch preparation

`api/src/transport_matters/cli/launch_runtime.py::prepare_launch` is the common preparation choke point. It resolves the addon, `mitmdump`, harness binary, working directory, ports, run storage, enablement, and compatibility. It mints an independent UUIDv4 `run_id`.

`api/src/transport_matters/captured/context.py::build_captured_run_context` adds a managed harness home, a native harness session, durable session facts, workspace identity, optional control plane grants, and a provider specific invocation.

`api/src/transport_matters/captured/run.py::prepare_captured_run` then:

1.  Acquires a per run `WorkspaceLock`.
2.  Writes owned session facts.
3.  Writes an advisory live manifest.
4.  Starts the proxy.
5.  Waits for the loopback proxy port.
6.  Retries bind or readiness failures up to three times.
7.  Returns a client spawn specification and a `CapturedRunLease`.

The lock name is misleading. `api/src/transport_matters/launch/manifest.py::run_with_workspace_manifest` states that each fresh run ID gets its own lock, so launches from the same workspace never contend. The lock is a liveness beacon.

### 2. Provider interposition

Claude and Codex need different interception shapes.

| Harness | Experimental mechanism | Source evidence |
|----|----|----|
| Claude | A loopback reverse proxy targets the Anthropic upstream. The child receives `ANTHROPIC_BASE_URL` pointing at that proxy. | `api/src/transport_matters/captured/claude.py::_build_claude_captured_invocation` |
| Codex | A loopback regular HTTP proxy intercepts HTTPS and WebSocket traffic. The child receives upper and lower case proxy variables and a CA bundle. | `api/src/transport_matters/cli/codex_cmd.py::build_codex_invocation`, `api/src/transport_matters/launch/environment.py::build_managed_child_env` |

`api/src/transport_matters/cli/runner.py::start_prepared_proxy` proves readiness with TCP acceptance only. It does not prove the capture store is writable, the addon is healthy, or an adapter can commit.

`api/src/transport_matters/cli/runner.py::run_prepared_client_on_local_tty` keeps the proxy alive after the interactive client exits so the experimental UI remains available. If the proxy exits first, it terminates the client.

`api/src/transport_matters/captured/models.py::CapturedRunLease.close` attempts all cleanup operations and aggregates failures. It terminates the proxy, restores signal handlers, removes the manifest, releases the lock, and closes the resource stack.

### 3. HTTP capture path

`api/src/transport_matters/addon.py` delegates mitmproxy hooks to `api/src/transport_matters/addon_handlers.py`.

`addon_handlers.py::handle_http_request` performs this sequence:

1.  Recognize Anthropic Messages or Codex Responses traffic.
2.  Select a provider adapter.
3.  Capture selected authentication headers for token counting.
4.  Parse the request body into immutable internal IR.
5.  Preserve an unparsed request as a synthetic exchange when parsing fails.
6.  Run the override and breakpoint pipeline.
7.  Apply a curated body when the pipeline changed the request.
8.  Attempt to persist a provisional exchange.
9.  Return from the hook, allowing upstream delivery.

`exchange_recorder/__init__.py::persist_exchange` catches every persistence exception, logs it, and returns `False`.

`exchange_recorder/__init__.py::persist_http_provisional_exchange` converts that failure to `None`.

`addon_handlers.py::handle_http_request` records the returned ID when present but does not fail the flow when absent. Unparsed persistence is also guarded and nonfatal.

This ordering shows good intent and an incomplete product contract. The request capture attempt precedes provider release, but the release has no required durable acknowledgement.

At response headers, `addon_handlers.py::handle_response_headers` installs the streaming tee. `api/src/transport_matters/response_stream.py::install_response_tee` appends every chunk to an in memory `bytearray` while returning each chunk unchanged. Observer exceptions are isolated. At response completion, `restore_streamed_response` restores the buffered body and `exchange_recorder/__init__.py::_finalize_http_provisional_exchange` rewrites the provisional exchange with response artifacts.

The tee preserves delivery but has no memory bound, disk spool, or backpressure policy.

### 4. Codex WebSocket capture path

`api/src/transport_matters/codex/transport.py::record_codex_websocket_message` tracks upgrade metadata, frame direction, timestamps, initial client frames, turn boundaries, and close facts.

`addon_handlers.py::handle_codex_websocket_message`:

1.  Captures each newest frame.
2.  Finalizes on terminal server messages.
3.  Rotates the provisional exchange when a new turn begins.
4.  Parses the initial client frame as a request.
5.  Runs the same override pipeline.
6.  Attempts to persist the provisional request.

`codex/transport.py::_message_artifact` stores text frames as decoded text and JSON, and binary frames as base64. Invalid UTF8 in a text frame is decoded with replacement, so exact text frame bytes are not always recoverable.

### 5. Shared proxy option

The experiment also has a pooled proxy.

`api/src/transport_matters/shared_proxy/manager.py::SharedProxyManager` supervises one proxy subprocess and keeps an in memory mirror of run bindings, listener ports, and override snapshots. It rehydrates them after a process restart.

`api/src/transport_matters/shared_proxy/subprocess.py::register_listener` updates mitmproxy modes dynamically, waits for listener acceptance, then registers the transcript binding.

`api/src/transport_matters/shared_proxy/addon.py::SharedProxyBindingTable` maps the actual listener port to a run and pins existing flows to the resolved binding.

`SharedProxyAddon._fail_http` returns 502 when a flow cannot be mapped. `SharedProxyAddon._kill_websocket` closes an unmapped WebSocket with 1011. The fail closed demultiplexing rule is strong.

The pooled topology creates a large fault and resource domain. All sessions share one proxy process, token counter, transcript tailer, database pool, control socket, and listener registry. Start with isolated capture workers. Pooling can be reconsidered after measured need.

The control channel itself is reasonably constrained: `api/src/transport_matters/shared_proxy/control.py::SharedProxyControlServer.start` creates a `0700` directory and a `0600` Unix socket, limits messages to 1 MiB, validates typed JSON, and applies timeouts. Those details are worth retaining for any future local control channel.

## Artifact truth and formats

### Experimental disk layout

`api/src/transport_matters/storage/disk_layout.py::DiskStorageLayout` defines the current run directory:

``` text
<run-root>/
  lock
  manifest.json
  index.jsonl
  index.jsonl.tmp
  sessions.json
  compatibility.json
  transcripts/
    <session-id>.jsonl
  <UTC timestamp>-<first 8 exchange id characters>/
    entry.json
    request.raw
    request.ir.json
    request.curated.raw
    request.curated.ir.json
    request.audit.json
    response.raw
    response.ir.json
    transport.json
    events.jsonl
    turn.json
```

Temporary exchange directories use `.tmp`, rewrite backups use `.bak`, and staged deletes use `.del`.

The filenames encode useful artifact classes:

- `request.raw`: captured provider request body representation.
- `request.ir.json`: normalized request.
- `request.curated.raw`: actual serialized outbound body after an override.
- `request.curated.ir.json`: normalized curated request.
- `request.audit.json`: mutation audit.
- `response.raw`: captured provider response body representation.
- `response.ir.json`: normalized response.
- `transport.json`: HTTP or WebSocket metadata and frames.
- `events.jsonl` and `turn.json`: Codex derived semantic views.
- `entry.json`: recovery sidecar for the index row.

### What “raw” currently means

The HTTP artifacts do not contain network wire octets.

`api/src/transport_matters/exchange_recorder/artifacts.py::request_raw_bytes` prefers `request.get_text()` and encodes it as UTF8. Its docstring explicitly prefers a content decoded, readable body over compressed bytes.

`exchange_recorder/artifacts.py::extract_response` calls `response.get_text()` and encodes it.

Consequences:

- HTTP body bytes can differ from bytes received on the socket.
- Compression, chunking, request line bytes, TLS records, and exact header serialization are absent.
- JSON semantics are usually preserved.
- Invalid text may be replaced.
- Codex binary WebSocket frames are preserved through base64.
- Codex text WebSocket frames can lose invalid UTF8 bytes.

The littleorgans contract should name evidence precisely:

- `client_body_bytes`
- `forwarded_body_bytes`
- `response_body_bytes`
- `http_envelope`
- `websocket_frame_bytes`
- `harness_transcript_bytes`

If the interception library has already decoded content, use a name such as `decoded_provider_body_bytes` and record the transformation. Reserve “wire bytes” for exact octets.

### Disk activation and recovery

`api/src/transport_matters/storage/disk.py::DiskStorageBackend.persist_exchange`:

1.  Writes artifacts into a temporary directory.
2.  Writes the `entry.json` recovery sidecar.
3.  Renames the directory into the live location.
4.  Rewrites the index through `index.jsonl.tmp`.
5.  Rolls the activated directory back if the index rewrite fails.
6.  Removes the old backup after success.

`api/src/transport_matters/storage/disk_helpers.py::DiskStorageRecoveryMixin`:

- removes abandoned temporary directories;
- restores interrupted backups;
- reconciles staged deletes;
- rebuilds missing index rows from `entry.json`;
- falls back to older Codex sidecars when needed.

The mechanics protect readers from partial directory state. They do not provide a power loss durability contract. No storage path calls `fsync`, `fdatasync`, or directory sync.

`index.jsonl` is not append only in practice. `DiskStorageBackend._rewrite_index` rewrites the full file on exchange finalization, recovery, token update, and delete.

`DiskStorageLayout.find_exchange_dir` resolves by the first eight exchange ID characters and returns the first matching directory. Collisions are possible.

`DiskStorageBackend._drop_legacy_flat_anchor_cache` can recursively delete the entire run storage root when it sees old flat anchor keys. The destructive behavior is asserted by `storage/test_disk_legacy_anchor.py::TestLegacyFlatAnchorCacheInvalidation.test_wipes_root_when_index_contains_legacy_flat_anchor_keys`. This must not migrate.

Storage directories and artifacts use the process umask. The capture store does not establish `0700` directories or `0600` files.

### Session and compatibility facts

`api/src/transport_matters/storage/session_facts.py::write_owned_session_facts` atomically upserts a `sessions.json` document with run ID, harness, native session ID, source descriptor, managed home, mint status, and template provenance.

`api/src/transport_matters/harnesses/compatibility_facts.py::write_compatibility_facts` freezes a versioned `compatibility.json` document. An identical retry is accepted. Divergent facts are rejected. Historical readers dispatch by recorded adapter revisions through `api/src/transport_matters/index/adapters/__init__.py::get_adapter_for_recorded`.

Keep the immutable capture contract concept. Use a smaller littleorgans schema that records:

- capture schema version;
- provider adapter revision;
- transcript adapter revision;
- resolved harness binary identity;
- platform `SessionId`;
- capture policy;
- encryption and redaction policy identifiers.

The experimental release certification subsystem is much larger than the capture requirement and should not migrate wholesale.

## Persistence authority ordering

The experiment has several authorities:

1.  Per exchange files and `index.jsonl`, called Tier 1.
2.  Per session native transcript snapshots.
3.  `sessions.json` and `compatibility.json`.
4.  Postgres transcript events.
5.  Postgres normalized wire rows.
6.  Drift, live status, activity, and UI projections.

The strongest current ordering is in `api/src/transport_matters/storage/exchange_sink.py`:

1.  Persist exchange files first.
2.  Invoke downstream observers after persistence.
3.  Isolate every observer failure.

That ordering should survive. The missing step is a required provider release barrier after Tier 1 request persistence.

`api/src/transport_matters/addon_runtime.py::load_capture_runtime` treats Postgres writer, transcript tailer, snapshot wiring, wire projection, and drift startup as best effort. On failure it logs that transcript capture is disabled and continues the proxy.

`api/src/transport_matters/session/writer.py::SessionWriter.submit_wire_exchange` also treats normalized wire storage as best effort. `api/src/transport_matters/wire_store_observer.py::WireStoreObserver` serializes these writes and drains them on close.

This is acceptable only for rebuildable projections. It is unacceptable for a product promise that every littleorgans run is captured.

## Provider adapters

### Strong mechanics

`api/src/transport_matters/ir.py` defines immutable request, response, message, tool, thinking, image, and unknown block models.

`api/src/transport_matters/adapters/base.py::ProviderAdapter` separates match, request parse, request serialization, and response parse.

`api/src/transport_matters/adapters/__init__.py::get_adapter` dispatches in a single registry.

`api/src/transport_matters/adapters/anthropic.py::AnthropicAdapter` preserves unknown top level fields in `provider_extras`, unknown block siblings in `provider_data`, and unrecognized blocks as `UnknownBlock`. Its serializer restores them. The invariant is semantic JSON round trip, not byte round trip.

`api/src/transport_matters/codex/request_parser.py::parse_codex_request` preserves unsupported input items with stable wire position stamps. `api/src/transport_matters/codex/request_serializer.py::serialize_codex_request` reconciles edits with those preserved entries and fails when it cannot safely serialize.

`api/src/transport_matters/adapters/anthropic.py::unknown_request_fields`, `api/src/transport_matters/codex/request_parser.py::unknown_request_item_fields`, and response event scanners use closed vocabularies to make new provider shapes visible.

### Boundary for littleorgans

Keep provider and harness adapters as anti corruption layers. Their outputs should be immutable and versioned. Preserve unknown shapes and retain original bytes.

Transport capture should observe. The override pipeline, breakpoints, token counting, credential refresh, control plane grants, activity inference, and UI state are separate capabilities. They should not enter the capture core.

## Transcript capture

### Current mechanism

The experiment derives an exact transcript source per managed session:

- `api/src/transport_matters/index/adapters/claude.py::claude_transcript_source` builds Claude’s deterministic JSONL path.
- `api/src/transport_matters/index/adapters/codex.py::CodexAdapter.locate` searches a managed `CODEX_HOME` for exactly one rollout matching the known native session ID. It declines ambiguous results.

`api/src/transport_matters/index/tailer.py::TranscriptTailer._poll_cursor`:

1.  Reads from the last acknowledged byte offset.
2.  Consumes newline terminated records only.
3.  Writes the complete byte prefix to the Tier 1 transcript snapshot.
4.  Normalizes records.
5.  Submits a Postgres event batch.
6.  Advances cursor state only after commit acknowledgement.

`api/src/transport_matters/storage/transcript_snapshot.py::make_transcript_snapshot_writer` uses snapshot length as the owned prefix. Replaying from offset zero appends only a new tail. A gap ahead of the snapshot raises and prevents cursor advancement.

`api/src/transport_matters/index/commit_dispatcher.py::ShardedCommitDispatcher` preserves per session order, isolates slow sessions, uses bounded queues, and returns commit futures to the tailer.

These are strong mechanics.

### Transcript defect

`api/src/transport_matters/index/record_ingest.py::iter_complete_records` logs and skips malformed complete JSON lines while still including their bytes in `consumed`.

The raw snapshot retains the bytes, but the structured projection advances past them without an opaque event, quarantine row, or parse drift record. Replay performs the same skip. The test `index/test_tailer.py::TestIterateSeam.test_skips_malformed_complete_lines` locks this behavior.

littleorgans should emit an explicit opaque transcript record with byte provenance, parse error, and original digest. No complete source record should vanish from the projection silently.

### Identity defect

`api/src/transport_matters/index/sessions.py::wire_session_id` uses the native Claude session ID directly and synthesizes a Codex session ID with UUIDv5 from run ID, provider, and native ID.

littleorgans already owns the platform `SessionId`. That ID must be the join key for capture, transcript, agents, API, and UI. Native provider conversation and transcript IDs remain attributes. Transport must not mint or synthesize a competing session identity.

## Drift and fidelity

### Implemented drift

`api/src/transport_matters/drift_capture.py::WireDriftObserver` runs after exchange persistence. It detects:

- unknown request envelope fields;
- unknown request item shapes;
- unknown HTTP response events;
- unknown WebSocket response events;
- selected malformed tag shapes.

Evidence based on persisted request or response body artifacts is marked capture safe. WebSocket frame summaries without exact bytes are marked capture unsafe.

`drift_capture.py::make_tailer_drift_hook` records unknown transcript shapes and locator mismatches without blocking the tailer.

`api/src/transport_matters/index/record_ingest.py::plan_ingest_records` gives skipped unknown transcript records exact byte provenance.

The principle is valuable: drift detection runs from already owned evidence, uses a closed vocabulary, and cannot break capture.

### Missing fidelity comparison

No source implementation compares provider request content with native harness transcript content.

The only request diff is `api/src/transport_matters/request_diff.py::request_unchanged` and `outbound_request_if_changed`. It compares original request IR with curated request IR.

The wire path writes normalized rows through `wire_store_observer.py::WireStoreObserver`. The transcript path writes events through `index/tailer.py::TranscriptTailer`. The searched source contains no consumer that reads both bodies and produces a fidelity result.

The experiment therefore provides correlation material and drift detection, but no proved wire versus transcript fidelity feature.

### Fidelity contract to build

Create a derived comparator after both evidence streams are durable:

1.  Correlate by platform `SessionId`.
2.  Correlate candidate request and transcript turn by provider sequence, provider IDs, and bounded time.
3.  Compare canonical content components while preserving original evidence.
4.  Report exact, normalized equal, partial, unmatched, ambiguous, and unsupported outcomes.
5.  Include provenance for every compared byte range and adapter revision.
6.  Keep the comparator rebuildable. It must never alter the capture ledger.

## Security findings

### Environment and credentials

`api/src/transport_matters/launch/environment.py::build_launch_env` begins with `os.environ.copy()`.

`build_managed_child_env` removes proxy, trust, and selected internal keys, then injects controlled proxy settings. It deliberately keeps credential variables listed by `HARNESS_CREDENTIAL_ENV_KEYS`.

`api/src/transport_matters/capture_rpc.py::capture_spawn_spec_payload` returns the full `launchEnv`. Its `_client_payload` returns the full child `env`. The route is loopback and origin guarded, but this contract can marshal every ambient secret through JSON.

littleorgans should build an explicit child environment allowlist. Secrets should move by reference or direct process injection and should never appear in API payloads, manifests, logs, or capture metadata.

### Artifact confidentiality

Request bodies, response bodies, transcript bytes, system prompts, tool inputs, tool outputs, and local paths are stored unencrypted. Header redaction in `api/src/transport_matters/transport_redaction.py` covers a heuristic set of header names and prefixes only.

`api/src/transport_matters/storage/disk.py::DiskStorageBackend.read_exchange` redacts old transport headers and rewrites `transport.json` during a read. This destroys original evidence.

The enterprise design needs:

- `0700` capture directories and `0600` files;
- encrypted raw evidence at rest;
- an immutable raw ledger;
- a separate redacted read projection;
- Identity authorization for every read, export, and delete;
- audit records for sensitive access;
- retention and quota policy;
- bounded artifact sizes and stream spooling;
- explicit incomplete and corrupt states;
- no mutation during reads.

`api/src/transport_matters/api/v1/local_file_routes.py` exposes arbitrary absolute local files through an unguarded GET, relying on host restrictions. This route is outside the capture core and must not migrate.

## Crash and shutdown semantics

### Useful behavior

- Atomic temp and backup activation protects exchange directories.
- `entry.json` permits index recovery.
- Staged delete recovery distinguishes indexed and unindexed state.
- Transcript snapshots are idempotent and reject gaps.
- Tailer cursors wait for durable projection acknowledgement.
- `CapturedRunLease.close` attempts all cleanup after one failure.
- `api/src/transport_matters/self_reap.py::install_parent_death_reaping` handles Linux parent death signals and a macOS parent watchdog.
- `api/src/transport_matters/addon_runtime.py::close_capture_runtime` stops and drains producers before consumers: transcript tailer, live status, wire observer, drift, commit dispatcher, writer, pending tasks, then HTTP client.

### Missing behavior

- No file or directory sync before a durability acknowledgement.
- No bounded response stream spool.
- No boot reconciliation that marks open exchanges and sessions interrupted in one authoritative ledger.
- No mandatory store health check before the agent starts.
- No capture fault propagated into Runtime and Session reconciliation.
- No explicit policy for a storage failure after response streaming begins.
- No disk quota, retention, encryption, or secure default permissions.

## Keep, reshape, delete

### Keep as design evidence

1.  Interpose capture before launching the harness.
2.  Use separate provider adapters with immutable IR.
3.  Preserve unknown provider and transcript shapes.
4.  Record both original and actual outbound request bodies.
5.  Persist the outbound request before provider delivery.
6.  Tee streamed responses without changing forwarded chunks.
7.  Store complete native transcript byte prefixes before cursor advancement.
8.  Advance projections only after commit acknowledgement.
9.  Fan out rebuildable observers only after authoritative persistence.
10. Fail closed when listener to session demultiplexing is unknown.
11. Version capture and adapter contracts in the capture header.
12. Recover partial directory activation and staged deletion.
13. Drain lifecycle dependencies in producer to consumer order.

### Reshape

1.  Use the littleorgans `SessionId` as the sole platform join key.
2.  Move capture lifecycle under Session and Runtime authority.
3.  Replace TCP acceptance readiness with proxy, adapter, and store readiness.
4.  Replace in memory response buffering with bounded disk spooling.
5.  Preserve exact bytes for all WebSocket frames, including text frames.
6.  Separate immutable raw evidence from redacted and normalized projections.
7.  Turn malformed transcript lines into durable opaque records.
8.  Add a real wire versus transcript comparator as a derived service.
9.  Replace per run JSON indexes with one transactional append ledger and rebuildable indexes.
10. Use typed exchange identifiers and exact lookup.
11. Add file and directory sync where the product claims durability.
12. Add security, retention, quotas, and access audit before shipment.

### Delete and start again

1.  Any `lilo` to external `tm` CLI launch chain.
2.  Runtime, package, release, or process dependency on the experimental repository.
3.  The capture HTTP RPC that serializes full environments.
4.  Independent transport run and session identity.
5.  Path derived workspace authority and eight character exchange lookup.
6.  The shared proxy as the initial littleorgans topology.
7.  Silent fail open capture writes.
8.  Ambient environment inheritance.
9.  Destructive legacy cache migration.
10. Read time mutation of raw evidence.
11. Whole file index rewrites.
12. Capture core ownership of overrides, breakpoints, token counting, credential refresh, activity, grants, canvas, or UI state.
13. Arbitrary local file routes.
14. Claims that HTTP `request.raw` and `response.raw` are exact wire octets.
15. Claims that wire versus transcript fidelity already exists.

## Recommended littleorgans boundary

### Ownership

- Session authorizes a user run and assigns the existing typed `SessionId`.
- Runtime owns process preparation, proxy worker lifecycle, harness launch, status, exit, and cleanup.
- Transport owns provider interception, capture persistence, transcript ingestion, capture health, and read models.
- Identity authorizes and audits capture access.
- Derived fidelity, search, and UI projections consume immutable capture evidence.

Transport does not authorize, decide what to spawn, reconcile session intent, refresh credentials, or mutate prompts.

### Launch sequence

1.  Session persists authorized run intent and `SessionId`.
2.  Runtime asks the in repository Transport application service to prepare capture for that `SessionId`.
3.  Transport creates a secure capture root and commits a versioned capture header.
4.  Runtime starts an isolated capture worker.
5.  Readiness proves listener ownership, adapter availability, writable store, and durable header readback.
6.  Runtime launches the harness with a minimal explicit environment.
7.  Every provider request waits for an authoritative request commit.
8.  Runtime terminates or reconciles the run when mandatory capture faults.
9.  Response and transcript evidence append to the same capture ledger.
10. Derived projections consume committed ledger positions.
11. Shutdown appends a terminal record, drains projections, and releases the worker.

### Authoritative event shape

A minimal ledger can carry:

- `capture_opened`
- `provider_request_observed`
- `provider_request_forwarded`
- `provider_response_started`
- `provider_response_chunk`
- `provider_response_completed`
- `websocket_frame`
- `transcript_chunk`
- `capture_fault`
- `capture_closed`

Large bodies can live in content addressed encrypted blobs. Ledger records carry digest, size, codec, byte provenance, and blob reference. Redacted IR, search text, fidelity results, and UI rows are projections.

### Failure policy

Before provider delivery, mandatory capture failure fails the request and run. After delivery has begun, a capture failure appends or attempts a terminal capture fault, stops forwarding further data, and surfaces a runtime failure for Session reconciliation.

A future break glass fail open mode would need an explicit operator setting and Identity audit. Silent degradation has no place in the default contract.

## Tests worth porting

These tests express useful behavior independent of the experimental topology.

| Behavior | Experimental test symbol |
|----|----|
| Clean abandoned temp directories | `storage/test_disk_atomic_write.py::TestAtomicWrite.test_crash_recovery_cleans_tmp_on_init` |
| Restore original exchange after activation failure | `storage/test_disk_atomic_write.py::TestAtomicWrite.test_rewrite_failure_restores_original_exchange_dir` |
| Recover interrupted staged deletion | `storage/test_disk_delete_recovery.py::test_init_restores_staged_delete_when_index_row_still_present` |
| Finalize a committed staged deletion | `storage/test_disk_delete_recovery.py::test_init_finalizes_staged_delete_when_index_row_missing` |
| Preserve transcript bytes exactly | `storage/test_transcript_snapshot.py::test_fresh_append_writes_consumed_bytes_verbatim` |
| Idempotent transcript retail | `storage/test_transcript_snapshot.py::test_retail_from_offset_zero_appends_only_the_new_tail` |
| Reject transcript snapshot gaps | `storage/test_transcript_snapshot.py::test_gap_ahead_of_snapshot_raises_rather_than_silently_advancing` |
| Wait for complete newline records | `index/test_tailer.py::TestIterateSeam.test_complete_records_only_leaves_trailing_partial` |
| Snapshot before observers | `index/test_tailer.py::TestTailerPoll.test_record_observer_runs_only_after_tier_one_snapshot` |
| Retry snapshot failure without advancing | `index/test_tailer.py::TestSnapshotTee.test_snapshot_failure_does_not_advance_and_retries_next_poll` |
| Retry commit failure without advancing | `index/test_tailer_dispatcher.py::test_async_commit_failure_does_not_advance_and_retries_same_batch` |
| Preserve per session order | `index/test_tailer_dispatcher.py::test_per_session_ordering_waits_for_prior_commit_ack` |
| Isolate healthy sessions from quarantine | `index/test_tailer_dispatcher.py::test_async_quarantine_ack_does_not_stall_healthy_cursor_or_advance_early` |
| Preserve streamed response chunks | `test_response_stream.py::test_response_tee_accumulates_and_passes_chunks_through` |
| Isolate stream observer failures | `test_response_stream.py::test_response_tee_isolates_observer_exceptions_and_preserves_forwarding` |
| Fail closed on unmapped listener | `shared_proxy/test_addon.py::test_unmapped_http_listen_port_fails_closed_and_never_calls_kernel` |
| Reject listener port mismatch | `shared_proxy/test_addon.py::test_listen_port_mismatch_fails_closed` |
| Preserve provider unknown fields | `adapters/test_anthropic.py`, `adapters/test_codex.py` round trip suites |
| Retain historical adapter revisions | `index/adapters/test_registry.py::test_newer_registration_retains_older_recorded_dispatch` |
| Authenticate drift evidence against stored bodies | `test_drift_capture.py::TestWireDigestProvenance.test_digests_resolve_to_persisted_tier1_bytes` |
| Drain drift before writer close | `test_addon_runtime_drift.py::test_close_capture_runtime_drains_drift_before_the_writer_closes` |
| Clean every lease resource after one cleanup failure | `test_capture_rpc.py::test_captured_run_lease_attempts_every_cleanup_after_failure` |
| Reap an already orphaned proxy | `test_self_reap.py::test_orphaned_at_arm_reaps_immediately` |

Two current tests should become inverse acceptance tests:

- Replace `exchange_recorder/test_http_provisional_persist.py::test_persist_http_provisional_exchange_returns_none_on_failure` with proof that persistence failure prevents provider release and reaches Runtime.
- Replace `index/test_tailer.py::TestIterateSeam.test_skips_malformed_complete_lines` with proof that malformed complete records produce durable opaque evidence.

Add new littleorgans tests for:

1.  Platform `SessionId` flows unchanged through Session, Runtime, capture, transcript, API, and UI.
2.  A full disk before provider release blocks the provider call.
3.  A disk failure during a streamed response terminates the flow and records a capture fault.
4.  Capture root, blobs, ledger, and control socket have exact secure modes.
5.  No inherited secret appears in a spawn specification or API response.
6.  Power loss recovery after each write and rename boundary.
7.  Text WebSocket frames preserve invalid UTF8 bytes.
8.  Retention and quota enforcement cannot delete an active capture.
9.  Raw evidence never changes during read or redaction.
10. Fidelity reports exact, normalized, partial, unmatched, ambiguous, and unsupported outcomes from a shared fixture corpus.

## Verification performed

### Pinned source proof

The commit object and tree were read without checking out the commissioned commit:

``` text
git show --no-patch --format=%H \
  a252df24a7e3cc0f7dabd3fa1faef35d6f052b55

a252df24a7e3cc0f7dabd3fa1faef35d6f052b55

git ls-tree -r --name-only \
  a252df24a7e3cc0f7dabd3fa1faef35d6f052b55 | wc -l

1744
```

Normalized reference validation against `git show a252df24:<path>` produced:

``` text
path_and_symbol_references=84
unique_cited_files=57
missing_references=0
cited_blob_mismatches_against_ed099336=0
```

The whole Python capture package comparison through `git ls-tree` produced one difference:

``` text
ed099336 only:
api/src/transport_matters/harnesses/test_inventory_vocabulary.py
```

That file is unrelated to this audit and is neither cited nor used. The selected test files, selected implementation files, `api/pyproject.toml`, `api/uv.lock`, and the root `justfile` have identical blob IDs in both trees.

### Earlier execution evidence

The following focused tests were run during the mistaken `ed099336` audit. They were not executed from an `a252df24` checkout. They corroborate the commissioned source because every selected test, implementation, and dependency manifest blob is identical, but this report does not describe them as an execution of the commissioned commit.

Focused recovery and capture mechanics:

``` text
uv run --project api python -m pytest -n0 \
  api/src/transport_matters/storage/test_disk_atomic_write.py \
  api/src/transport_matters/storage/test_disk_delete_recovery.py \
  api/src/transport_matters/storage/test_transcript_snapshot.py \
  api/src/transport_matters/index/test_tailer.py \
  api/src/transport_matters/index/test_tailer_dispatcher.py \
  api/src/transport_matters/test_response_stream.py \
  api/src/transport_matters/shared_proxy/test_addon.py \
  api/src/transport_matters/test_drift_capture.py -q

121 passed in 0.70s
```

Focused adapters, launch lifecycle, facts, and cleanup:

``` text
uv run --project api python -m pytest -n0 \
  api/src/transport_matters/adapters/test_anthropic.py \
  api/src/transport_matters/adapters/test_codex.py \
  api/src/transport_matters/index/adapters/test_claude.py \
  api/src/transport_matters/index/adapters/test_codex.py \
  api/src/transport_matters/index/adapters/test_registry.py \
  api/src/transport_matters/exchange_recorder/test_http_provisional_persist.py \
  api/src/transport_matters/test_capture_rpc.py \
  api/src/transport_matters/test_self_reap.py \
  api/src/transport_matters/harnesses/test_compatibility_facts.py \
  api/src/transport_matters/storage/test_session_facts.py -q

167 passed in 0.90s
```

Final repository checks:

``` text
git status --short

(empty)

git show --no-patch --format=%H \
  a252df24a7e3cc0f7dabd3fa1faef35d6f052b55

a252df24a7e3cc0f7dabd3fa1faef35d6f052b55
```

No live provider traffic, real credential probe, Postgres integration suite, or power loss experiment was run. Runtime claims in this report are pinned source findings. The focused tests are comparison tree execution over identical selected blobs. The report does not convert those checks into live production evidence.

## Worker Status

No nested agents were spawned for this assigned research scope.
