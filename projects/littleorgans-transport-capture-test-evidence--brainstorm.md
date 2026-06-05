---
title: Transport capture test evidence for littleorgans — reuse map
type: research
tags: [littleorgans, transport, capture, testing, acceptance-evidence]
summary: Mining transport-matters tests, fixtures, invariants, and failure experiments as acceptance evidence for a littleorgans-owned capture capability
status: complete
source: codebase-analyst
confidence: high
created: 2026-07-31
updated: 2026-07-31
---

Status: COMPLETE

# Transport capture test evidence for littleorgans

## Pinned inputs

- transport-matters: `a252df24a7e3` ("fix(auth): close credential review residuals"), inspected via isolated worktree `/tmp/tm-a252df2` (repo HEAD `ed099336` is 3 commits ahead; the pinned commit was checked out detached, read only).
- littleorgans: `98d8928941b5` (current HEAD of the monorepo working tree).
- Constraints honored: transport-matters NOTES not read; no repo edits; no code port proposed, test evidence only.

## Executive summary

transport-matters carries ~340 test files; roughly 60 of them encode capture invariants and failure experiments worth recreating as acceptance evidence for a littleorgans-owned capture capability, with zero tm dependency. littleorgans today has no wire-capture code (`internal/wire` is only the `LilodRpc` envelope; `lilo capture` is runtime's tmux verb), so everything below is greenfield acceptance evidence, not regression parity. The single highest-value acceptance proof: the real 3-turn captured fixture corpus (`claude_messages`, `codex_http_fallback`) driving three invariants at once: real captures are drift-silent, cross-turn prefix dedup yields at least 96 percent against true wire bytes, and reconstruction round-trips exactly.

## Test reuse map (consolidated, ranked)

Classification legend: RC = reuse concept, RF = recreate fixture, RTP = recreate test pattern, REJ = reject. Full path+symbol evidence in the cluster sections below.

| # | Invariant | Source evidence (path:symbol) | Class | Failure experiment |
|---|---|---|---|---|
| 1 | Real 3-turn capture corpus: drift-silent, dedup >= 96% vs true wire bytes, exact round-trip | `api/tests/fixtures/{claude_messages,codex_http_fallback}/turn-*` + `session/test_wire_normalization.py::test_fixture_prefix_dedups_completely` (:167), `::test_fixture_request_round_trips_exactly` (:184), `test_drift_capture.py::test_real_captured_request_is_silent` (:111) | RF+RTP | no |
| 2 | Capture observer failure never degrades the proxied stream | `test_response_stream.py::test_response_tee_isolates_observer_exceptions_and_preserves_forwarding` (:73) | RC+RTP | yes |
| 3 | SSE incremental parse == whole-buffer parse at every byte boundary (multibyte UTF-8), resync after malformed/oversized records, bounded tail | `test_sse.py` (:13, :41, :47, :56, :65) | RTP (proptest) | yes |
| 4 | Streamed capture == buffered capture (bytes, IR, index, derived counts) | `test_response_stream_capture.py::test_streamed_provisional_finalize_matches_buffered_response` (:102) | RC+RF | yes |
| 5 | Never lose bytes: unparseable payload keeps raw + parse-failure marker; empty persists nothing; sink explosion never escapes the proxy hook | `codex/test_exchange_unparsed.py` (:45, :75, :84), `exchange_recorder/test_unparsed.py` (:53, :132), `test_wire_store_observer.py` (:414) | RTP | yes |
| 6 | Atomic write: 4 crash injection points leave zero residue; rewrite failure restores original; init sweep is not over-eager | `storage/test_disk_atomic_write.py` (all 5), `test_atomic_io.py` (:15) | RTP | yes |
| 7 | Two-phase delete: index row arbitrates roll-forward vs roll-back on `.del` staging at bootstrap | `storage/test_disk_delete_recovery.py` (:20, :50, :69) | RTP | yes |
| 8 | All-or-nothing persist; index is a rebuildable cache from sidecars; whole-tree byte snapshot equality | `storage/test_disk_persist.py` (:24, :97, :120, :273, :329), helper `storage/test_exchange_support.py::complete_file_snapshot` (:27) | RTP | yes |
| 9 | Transcript snapshot: restart-idempotent append-only tee; gap ahead raises rather than silently advancing | `storage/test_transcript_snapshot.py` (all 6), `tests/integration/test_transcript_snapshot_roundtrip.py` (:113, :166, :200) | RTP | yes |
| 10 | Tailer: byte-contiguous tee equals source file; cursor advances only after tee + submit both succeed; torn/malformed lines safe | `index/test_tailer.py` (:317, :124, :136, :279, :371) | RTP | yes |
| 11 | Quarantine: transient retries forever, permanent dead-letters with exact bytes + range after bounded attempts, dead-letter ack gates the skip; one poison never loses the stream | `index/test_tailer_quarantine.py` (:23, :68, :113), `session/test_ingest.py` (:295, :371, :415) | RC+RTP | yes |
| 12 | Drift is observational only: raising hook leaves capture byte-identical; typed deduped byte-quoted evidence; digest-anchored to persisted tier-1 bytes; `capture_safe` labeling | `index/test_tailer_drift.py` (:64, :313, :388), `test_drift_capture.py` (:534, :564, :506) | RC+RTP | yes |
| 13 | Replay determinism: incremental derivation byte-identical to whole-input replay; 7-scenario timeline contract table | `codex/test_derivation_incremental.py` (:145), `codex/test_timeline_contract.py::REPLAY_CASES` (:36-142) | RTP+RF | yes |
| 14 | Repair never fabricates; repaired equals live derivation; raw transport untouched | `codex/test_repair_safety.py` (:120, :22), `codex/test_repair_rebuild.py` (:31, :108) | RTP | yes |
| 15 | Provisional lifecycle: finalize in place preserving identity; orphaned provisional recovers; delete idempotent, failure keeps retryable state; dual-path parametrize (fresh vs provisional) | `exchange_recorder/test_http_provisional_finalize.py` (:30, :157, :186), `test_http_provisional_flow.py` (:33, :137, :167), `test_http_provisional_delete.py` (:48, :90), `test_codex_http_artifacts.py` (:108) | RTP | yes |
| 16 | Turn boundaries by (event_type, direction) only; mid-turn disconnect yields interrupted turn, prior finalized turn untouched; multiplexed turns isolated | `codex/test_turn_boundary.py`, `codex/test_transport_turn_close.py` (:17, :117) | RC+RTP | yes |
| 17 | Capture works standalone: disk + Postgres + NOTIFY chain with no web layer imported | `session/test_capture_without_web.py` (:46) | RTP | yes |
| 18 | Wire-writer idempotence: replay yields whole-store snapshot equality, zero duplicate notifications; store outage counted not thrown | `session/test_wire_writer.py` (:139, :298, :341, `_wire_state` :405) | RTP | yes |
| 19 | Normalization: NUL stripped before hash (Postgres jsonb); negative control on strip breadth; set-hash order/kind sensitivity | `session/test_wire_normalization.py` (:91, :72, :132) | RTP | yes |
| 20 | Secret redaction: narrow header allowlist (`authorization` provably absent); transport-layer redaction; read-time redaction self-heals legacy files | `test_flow_state.py` (:71), `exchange_recorder/test_codex_http_artifacts.py` (:165-170), `storage/test_disk_exchange.py` (:181) | RC+RTP | partial |
| 21 | Session correlation: deterministic uuid5 synthesis converges wire and transcript sides; fail closed on ambiguous binding; trusted launcher stamp beats derived re-bind; no ambient run identity | `index/test_sessions.py` (:9), `index/adapters/test_codex.py` (:344, :277), `test_owned_transcript_binding.py` (:85), `test_proxy_run_binding.py` (:106-109) | RC+RTP | yes |
| 22 | Subagent correlation corpus: parent tool_use to sidecar meta to child file; spawn call_id to agent_id; fork_context replay dedup | `api/tests/fixtures/subagents/` (7 files) + `session/test_subagents.py` (:83, :113, :147) | RF | yes |
| 23 | Zero-impact tap: baseline-vs-tapped whole-tree byte identity; generation-fenced last-writer-wins | `test_live_status_observer.py` (:571, :235, :411) | RTP | yes |
| 24 | Forward compat: parser never raises on any JSON body; degrades one block to Unknown, never the request; adapter round-trip re-emits unparseable items verbatim | `adapters/test_anthropic.py::TestForwardCompat*` (:422, :593), `adapters/test_codex.py` (:758, :770) | RTP+RF | yes |
| 25 | Process lifecycle: parent-death reaping armed/late/control triad; pid-reuse-safe supervision; SIGTERM-to-SIGKILL escalation; shutdown ordering proven at a real socket | `tests/integration/test_parent_death_reaping.py` (:101, :114, :127), `shared_proxy/test_process.py` (:124, :161), `test_gateway_supervisor.py` (:270, :236) | RTP | yes |
| 26 | Fail-closed demux: unmapped port never reaches the capture kernel; interleaved flows keep storage isolated | `shared_proxy/test_addon.py` (:482, :431, :337) | RTP | yes |
| 27 | Postgres test infra: template-clone TestDb, namespace-scoped sweep, fixture-tests-the-fixture, `pg_terminate_backend` reconnect injection | `session/testing.py`, `session/test_testing.py` (:54, :100), `session/test_listen.py` (:317) | RC (littleorgans `internal/db/src/test_support.rs::TestDb` exists; deltas: template clone, scoped sweep, notify await) | yes |
| 28 | Canonical digest: sha256 of canonical JSON, key-order invariant, code-point ordering, non-finite rejected | `test_canonicalization.py` (:16, :20, :35, :40) | RC+RTP | partial |
| 29 | Fidelity no-op detection: structural equality of distinct instances; no-op path observably work-free via counting spy | `test_request_diff.py` (:41, :54) | RC+RF | no |
| 30 | Cross-language parity corpus: TS expectations, projector, and SQL held to identical answers over every cursor | `session/test_conversation_parity.py` (:27, :106) | RC | no |

## Missing tests (gaps in transport-matters littleorgans must author fresh)

1. Tailer rotation/truncation: `index/tailer.py:213` keys only on `(st_size, st_mtime)` with a blind seek; no inode tracking, zero rotation tests. Needed: truncate-then-append resync; same-name-new-inode reopen.
2. Timestamp monotonicity: no test feeds out-of-order or duplicate frame timestamps; nearest precedent is equal-timestamp precedence (`codex/test_derivation_contract.py:88`).
3. Repair after byte-level corruption: repair covers missing sidecars and absent turns, never truncated or garbage `events.jsonl`/`transport.json`.
4. Concurrent atomic-write race: `atomic_io.py:32-45` documents the `os.link` exactly-one-winner invariant with no test.
5. Golden wire-bytes round-trip: no parse-then-serialize test against real captured provider wire bytes; `test_ir.py:167` round-trips only the IR's own dump (adapter fixture tests come closest).
6. Secret never-capture: `test_transcript_denylist.py` is a display-layer hide filter that fails OPEN on malformed config; no test proves a secret is never written to disk. littleorgans needs the real never-capture test with fail-closed semantics.

## littleorgans baseline checks (at 98d8928)

- No wire-capture code exists: `internal/wire/src/lib.rs` is the 8-line `LilodRpc` envelope only; `capture` hits in `crates/lilo-rm-core/src/capture.rs` are the tmux pane-capture verb.
- Postgres test isolation exists: `internal/db/src/test_support.rs::TestDb` (unique-name create, migrate, explicit async cleanup, `now_micros` truncation). The transport-matters deltas worth adopting: template-clone speed, namespace-scoped litter sweep proven safe by a fixture-tests-the-fixture suite, and NOTIFY-await helpers.
- House gates: `just check && just build && just test`, `cargo nextest`; the acceptance sets above map onto workspace tests plus proptest for #3 and #13.

## Methodology lessons worth adopting as house style

- Surgical failure injection: fail exactly one operation identified by an argument predicate, never a blanket mock.
- Residue assertion after every injected failure: no `*.tmp` / `*.bak` in root, as a shared helper.
- Two-sided fuzz assertions: no-crash plus a named, reportable drift finding; silence is indistinguishable from data loss.
- Dual-path parametrization: run every capture assertion over both fresh and provisional-finalize lifecycles.
- Byte-level determinism: compare canonical serialized output, not parsed structures.
- Whole-tree byte snapshot (`complete_file_snapshot`) and whole-store DB snapshot (`_wire_state`) equality as the idempotence oracle.
- Control tests that prove the repro is probative (unarmed process survives; legitimate zero left alone).
- One-knob builders and shared scenario modules before writing tests; fixed timestamp constants for deterministic snapshots.

## Worker Status

Five read-only Explore subagents were spawned over the pinned worktree; no worker made any edits.

| Worker scope | Final state |
|---|---|
| Wire capture core (sse, response stream, atomic io, canonicalization, request diff, flow state, lock, breakpoint, broadcast, counting, json tags, pause) | completed |
| Exchange recorder + disk storage + fixture corpus | completed |
| Provider adapters + codex turn machinery (timeline, derivation, repair, preserved raw, continuity) | completed |
| Index/tailer + drift + session/run binding + live status + track manager | completed |
| Integration suite + wire store/session persistence + shared proxy | completed |

## Cluster findings (raw, pre-consolidation)

### Wire capture core (done)

All paths under `api/src/transport_matters/`.

Priority acceptance candidates:

1. `test_sse.py::test_incremental_sse_matches_whole_buffer_at_every_byte_boundary` (line 13): incremental SSE parse equals whole-buffer parse at every byte split, with multibyte UTF-8 payloads. Recreate test pattern (proptest in Rust). Companions: malformed-frame resync (line 41), trailing partial UTF-8 retention (line 47), bounded tail with resync (lines 56, 65).
2. `test_response_stream.py::test_response_tee_isolates_observer_exceptions_and_preserves_forwarding` (line 73): a raising capture observer must not break forwarding or accumulation. Reuse concept, the number one acceptance claim for capture. Companions: identity pass-through (line 57), buffer release on error/abort (lines 224, 239), reflective metadata-key collision guard (line 206).
3. `test_response_stream_capture.py::test_streamed_provisional_finalize_matches_buffered_response` (line 102): streamed capture equals buffered capture across raw bytes, IR, index entry, and derived counts, with a mid-frame byte-80 split and absent transport body. Reuse concept plus recreate fixture (`ANTHROPIC_SSE_BODY`, line 22: realistic 6-frame SSE transcript with usage numbers).
4. `test_atomic_io.py::test_guarded_atomic_write_failure_preserves_complete_destination` (line 15): failed temp write preserves complete destination and leaves zero residue files. Reuse concept plus recreate test pattern. Gap: `atomic_io.py:32-45` documents a concurrent-writers `os.link` race invariant with no test; close it in littleorgans.
5. `test_canonicalization.py`: digest is definitionally sha256 of canonical JSON (line 35), key order not observable (line 40), code-point key ordering pinned with private-use vs astral chars (line 16), non-finite numbers rejected (line 20). Reuse concept plus recreate test pattern; highest carry-over per line.
6. `test_request_diff.py`: structural (not identity) equality drives change detection (line 41); the no-op path is observably work-free via a counting spy adapter (line 54). Reuse concept plus recreate fixture (one-knob `_request(*, system_text=...)` builder shape, repeated in four files).
7. `test_flow_state.py::test_capture_request_flow_state_snapshots_narrow_codex_headers` (line 71): header capture is a narrow allowlist; `authorization: Bearer` provably absent. Secret-redaction acceptance in disguise. Companions: partial state updates never clobber earlier fields (lines 133, 171).
8. `test_lock.py`: kernel flock releases on SIGKILL of holder, real subprocess with stdout handshake and polling deadline (line 90); exact interleaving ledger for blocking lock (line 172); both fail-fast and blocking policies pinned. Recreate test pattern.
9. `test_breakpoint.py::TestConcurrency::test_concurrent_pop_only_one_wins` (line 197): concurrent take-once yields exactly one winner; timeout does not orphan state (line 213). Reuse concept.
10. `test_broadcast.py`: bounded queue plus loud drop for slow subscribers (lines 50, 54). Recreate test pattern. `test_pause_session.py::test_drain_cancels_straggler` (line 50): bounded shutdown despite hung capture-side task. Reuse concept.
11. `test_counting.py::TestTokenCounterFailurePaths` (lines 243-284): seven named upstream failure modes each degrade to None, never an exception or bogus value; failures are not negatively cached (line 299). Recreate test pattern (the failure-table format).
12. `test_json_tags_totality.py`: reuse methodology, reject code. One malformed field per case; every fuzz case asserts both no-crash and a named drift finding; kind-vector times position-matrix parametrization (lines 294, 310). In Rust, serde removes much of the bug class; the port is total error paths producing reportable drift findings.

Rejections: mitmproxy flow-shape selection matrices, provider host routing, `TestContentBlocks` getters, track-scoped override tests (mutation scope, not capture), pydantic frozen-model tests (immutability is default in Rust).

Gaps in transport-matters worth closing: untested `write_atomic_bytes_once` concurrency race; no golden round-trip of real captured provider wire bytes through parse then serialize (`test_ir.py:167` only round-trips the IR's own dump).

### Adapters + codex turn machinery (done)

All paths under `api/src/transport_matters/`.

Priority acceptance candidates:

1. `codex/test_timeline_contract.py::test_replay_fixture_contracts` (line 193) over `REPLAY_CASES` (lines 36-142): seven named wire scenarios (success, failed, interrupted, handshake failure, dropped initial frame, tool-result-only continuation, multi-turn) each replay to a fully specified timeline: ordered event kinds, contiguous seq 1..N, per-event `transport_ref.message_index`, full turn summary. Recreate test pattern plus recreate fixture (`ReplayExpectation` table shape; scenario builders in `codex/derivation_test_replay_scenarios.py`). Detail: two turns on one connection restart event ids at `evt_000001` (event ids are turn-scoped, lines 232-233).
2. `codex/test_derivation_incremental.py::test_incremental_advance_serializes_identically_to_replay` (line 145): incremental derivation across arbitrary cut points is byte-identical to whole-input replay (`serialize_codex_events_jsonl` concat and `serialize_codex_turn_json`). Recreate test pattern, top priority; natural proptest. Cursor-geometry violations raise specific errors (lines 72, 96, 108).
3. `codex/test_repair_safety.py::test_repair_does_not_invent_sidecars_for_non_turn_transport` (line 120): repair is conservative; non-turn transports produce `action="none"`, diagnostic `codex_turn_not_present`, and provably no `events.jsonl`/`turn.json` on disk (lines 140-147). Audit presence alone never synthesizes a curated event (line 22). Recreate test pattern, top priority.
4. `codex/test_repair_rebuild.py`: repaired-equals-live oracle. Delete derived sidecars, repair, assert derived artifacts equal a fresh live derivation over the same raw, and `transport.json` bytes unchanged (lines 74, 92-95). Identity recoverable from headers when IR metadata wiped (line 179). Recreate test pattern.
5. `codex/test_turn_boundary.py`: turn boundaries decided by (event_type, direction) pairs only; client `response.create` starts, server `response.completed`/`failed` terminates, close-before-terminal is interrupted with `ws_close_{code}`. Zero fixtures. Reuse concept plus recreate test pattern; cheapest high-value evidence.
6. `codex/test_exchange_unparsed.py` (lines 45, 75, 84): the never-lose-bytes triad: unparseable payload stores raw plus synthetic IR marked `transport.parse_failure`; empty payload persists nothing; storage sink raising never propagates out of the capture path. Recreate test pattern, top priority.
7. `codex/test_transport_turn_derivation.py::test_addon_websocket_message_preserves_open_sidecars_when_derivation_fails` (line 20): fault-injected derivation failure at finalize still lands raw and response capture, preserves prior derived sidecars unchanged, and logs a warning. Recreate test pattern (capture survives its own analysis layer failing).
8. `codex/test_transport_turn_close.py` (lines 17, 117): two turns multiplexed on one websocket persist as independent exchanges; close 1006 mid-second-turn yields interrupted turn with `stop_reason="ws_close_1006"` while the finalized first turn is untouched. Recreate test pattern (canonical mid-turn disconnect).
9. `codex/test_preserved_raw.py`: original wire bytes per input item survive edits/deletions via wire-index stamps; stamp-first reconcile, kind-match fallback, leftover entry is a hard error not silent loss (lines 42-90). Recreate test pattern.
10. `adapters/test_anthropic.py::TestForwardCompat` plus `TestForwardCompatContentShapes` (lines 422, 593): ~17 degradation experiments; parser never raises on any JSON body, unknown shapes degrade to `UnknownBlock` or sentinel scalars losing exactly one block, round-trip lossless including unmodeled extras. Recreate test pattern (strongest capture-degrades-never-fails evidence).
11. `adapters/test_codex.py` (lines 510, 758, 770): round-trip byte equivalence over real captured fixtures including deliberately unparseable items which are re-emitted verbatim, never phantom-deleted. Recreate test pattern plus recreate fixture (real provider bytes as checked-in fixtures).
12. `codex/test_continuity.py`: turn-index allocator idempotent per (thread_id, turn_id), strictly monotonic per thread, malformed metadata degrades to lossy but still consumes an index (lines 8, 45, 77). Recreate test pattern; fixture-free.
13. `codex/test_derivation_replay.py`: committed-vs-in-flight rule: deltas are transport, not semantics; only `.done` frames emit events; interrupted close retains partial `text_chars`; pending tool activity counted once (lines 225, 296, 317, 325). Recreate fixture plus reuse concept.
14. `codex/test_derivation_contract.py`: illegal-states checklist for the derived-turn constructor (open turns need cursors, cursor geometry, canonical event id format); equal-timestamp operator facts have a total precedence order, a determinism prerequisite (line 88). Reuse concept.
15. `codex/test_exchange_finalize_sink.py` (lines 48, 221): sinks fire exactly once, at finalize, with a complete artifact; provisional deleted out from under the finalizer recovers by rewriting. Reuse concept (infra-heavy).
16. `adapters/test_adapter_registry.py::test_flow_selection_and_ir_provider_ignore_launch_harness` (line 93): provider identity derives from the wire, never from the launching harness. Reuse concept; reject registry-dispatch and import-cycle tests.

Rejections: pause/edit/release machinery (out of capture scope, keep only the stale-state-leak regression), Python import-cycle guards, registry dispatch internals.

Gaps confirmed absent in transport-matters: no timestamp-monotonicity experiment (out-of-order or duplicate frame timestamps); no repair-after-byte-corruption experiment (truncated or garbage `events.jsonl`/`transport.json`). Both should be authored fresh in littleorgans.

Cross-cutting: determinism is always proven at the byte level (serialized output comparison), not value level; three-layer test shape (pure predicates, pure derivation over builders, full integration) with the middle layer carrying most acceptance evidence; shared scenario builders are the highest-leverage fixture investment.

### Index/tailer, drift, binding (done)

All paths under `api/src/transport_matters/`.

Priority acceptance candidates:

1. `index/test_tailer.py::TestSnapshotTee::test_poll_tees_consumed_bytes_at_cursor_offset` (line 317): concatenated tee snapshots byte-equal the source file, no gap or overlap. Non-negotiable capture fidelity anchor. Companions: torn trailing line never consumed (line 124), malformed line skipped with byte-exact spans for the next record (line 136), cursor advances only after tee plus submit both succeed (line 279), snapshot failure leaves offset and stat signature reset so an unchanged file retries (line 371), five same-cwd sessions with zero cross-binding (line 561). Recreate test pattern.
2. Rotation/truncation gap confirmed: `index/tailer.py:213` uses only `(st_size, st_mtime)`, blind `seek` at 216-218, no inode tracking; zero rotation tests exist. Author fresh in littleorgans: truncate-then-append resync, same-name-new-inode reopen.
3. `index/test_tailer_quarantine.py`: transient failures retry forever without quarantine (line 23); permanent failures dead-letter after a bounded attempt cap with exact raw bytes and byte range, and only the dead-letter ack gates the cursor skip (lines 68, 113). Reuse concept plus recreate test pattern.
4. `index/test_tailer_drift.py`: drift is observational only. Unknown record shape emits typed, deduped, byte-quoted evidence while all records still ingest (line 64); a raising drift hook leaves the quarantine flow byte-identical (line 313); sentinel-lookalike strings do not collide with real drift keys (line 224); wire-vs-transcript session-id divergence keeps the wire id and emits `transcript_locator_mismatch` (line 388). Reuse concept plus recreate test pattern; single most valuable file in this cluster.
5. `test_drift_capture.py`: anti-false-positive gate: every real captured fixture must read as silent (line 111); evidence digests resolve to persisted tier-1 bytes (line 534); `capture_safe` labels whether evidence has byte-exact durable backing (line 564); emitter or store failure invisible to the capture path (line 506); vocabulary certification pinned to a wire revision (lines 220, 245); shutdown drains in-flight evidence (line 595). Reuse concept plus recreate fixture.
6. `test_drift_capture_hook.py`: infrastructure failures (DB outage) are not contract drift (line 74); sync-thread to async-emitter handoff safe (line 50). Reuse concept.
7. `index/test_sessions.py::TestSynth::test_deterministic_uuid5` (line 9): synthetic session id is a pure function of (run_id, provider, native_session_id) so wire and transcript sides converge without coordination; convergence proven at `index/adapters/test_codex.py:277`. Reuse concept, tiny but load-bearing.
8. `index/adapters/test_codex.py`: fail closed on ambiguous binding (duplicate native rollouts return None, line 344); no implicit global-home discovery (line 320). `index/adapters/test_claude.py`: harness-byte-exact path slugging pinned by a live-probe comment (line 214); total-coverage gate: every fixture record is turn or certified meta, no silent third bucket (line 114). Recreate test pattern.
9. `test_owned_transcript_binding.py` (line 26): trusted launcher stamp always overlays untrusted adapter re-bind; adapter can add facts, never erase trusted ones (line 85). Reuse concept, high value.
10. `test_proxy_run_binding.py` (line 55): capture routes by explicit binding object; ambient env run identity never claims a bound capture (`global_entries == []`, lines 106-109). Recreate test pattern (no-global-singleton guard).
11. `api/tests/fixtures/subagents/` (7 files, under 5 KB, real harness captures): Claude parent tool_use id to sidecar meta to child file join (child shares parent sessionId so capture must synthesize one); Codex spawn call_id to returned agent_id to child rollout, including fork_context replay content that must be deduped. Consumed by `session/test_subagents.py` (lines 83, 113, 147). Recreate fixture, top fixture priority; copy verbatim.
12. `test_live_status_observer.py::test_live_tap_preserves_complete_tier1_manifest_and_bytes` (line 571): baseline-vs-tapped runs produce identical file snapshots; observation is provably zero-impact. Plus generation-fenced last-writer-wins (lines 235, 411) and no writer I/O on the capture thread (line 78). Recreate test pattern, high value.
13. Track manager (`test_track_manager_core.py`, `test_track_manager_lifecycle.py`): every exchange attributed to exactly one live track; late tool_result for a closed track falls back to the parent, never resurrects (lifecycle lines 167, 214); two-phase and single-shot APIs equivalent (core line 12); `AnchorCase` table-driven harness (lifecycle line 536). Recreate test pattern; provider-vocabulary files reuse concept only.
14. `test_live_status.py`: delta heals a missed start (line 79); no false global stop with interleaved open items (line 171). Reuse concept.
15. `index/test_subagents.py::test_yielded_records_have_sanitized_tags` (line 20): post-boundary tags are always str or None, never unhashable. Recreate test pattern.

Correction to brief: `test_transcript_denylist.py` is a display-layer hide-rule config, not capture-time secret redaction, and it fails OPEN on malformed config. No test in transport-matters proves a secret is never written to disk. littleorgans must author the real never-capture test fresh, with fail-closed semantics.

Helper patterns worth copying: `_drive_until` bounded predicate pump for deterministic async tests (`index/test_tailer_dispatcher.py:53`); `test_replay_support.py` as a shared run-dir seeder consumed by both live and replay paths (lines 77, 103).

### Exchange recorder + disk storage + fixtures (done)

All paths under `api/src/transport_matters/` unless noted.

Fixture corpus facts (first-hand verified):

- `api/tests/fixtures/claude_messages/turn-{0,1,2}/`: real captured Claude Code `/v1/messages` triple (run `71d0469e`, 2026-07-10). Each turn: `request.ir.json` (~195-200 KB pretty IR), `response.ir.json` (~0.7-1.1 KB), `meta.json` with `request_raw_bytes` measured from the TRUE wire body, not the pretty IR (the honest dedup denominator). Locked facts: 16 to 18 to 20 messages, prefix hash-identical after `cache_control` strip, system and tools byte-identical across turns, dedup yield 98.4 and 98.8 percent against wire bytes clearing a 96 percent bound. README warns mid-session tool-registry growth legitimately depresses yield; pick stable-registry triples.
- `api/tests/fixtures/codex_http_fallback/turn-{0,1,2}/`: same shape plus `transport.json` (302 KB, HTTP fallback proof) on turn-0 only. HTTP-fallback requests are cumulative (6 to 12 to 15 messages) unlike WS incremental; `input_item_raw` ~96-98 KB per turn makes the strip clause load-bearing.
- Consumers: `test_drift_capture.py:113` (real capture is drift-silent), `session/test_wire_normalization.py:167,184` (prefix dedup, exact round-trip), `session/wire_writer_test_support.py:26-50`. Storage and recorder layers use synthetic builders, not these fixtures.

Priority acceptance candidates:

1. `storage/test_disk_atomic_write.py` (all five, lines 19-121): four distinct crash injection points (serialize, replace, open, final rename) each leave zero residue; rename is the commit point; init-time crash-recovery sweep removes `.tmp` dirs but preserves same-shaped non-tmp siblings; rewrite failure restores original bytes at the original path. Recreate test pattern, port all five. Technique: surgical failure injection predicated on exact args, never blanket mocks.
2. `storage/test_disk_delete_recovery.py` (lines 20, 50, 69): two-phase delete (`.del` staging); the index row is the arbiter at bootstrap: row present rolls the staged dir back, row absent finalizes the delete. Complete portable crash-consistency protocol. Recreate test pattern, port all three.
3. `storage/test_disk_persist.py`: all-or-nothing persist with full rollback at index-rewrite or sidecar-write failure (lines 97, 120, 168); index is a rebuildable cache, recoverable from `entry.json` sidecars or even legacy artifact sets (lines 273, 329); whole-tree byte snapshot equality via `complete_file_snapshot` (line 24; helper at `storage/test_exchange_support.py:27`). Recreate test pattern; build the snapshot helper day one.
4. `storage/test_transcript_snapshot.py` (all six, lines 28-94): append-only tee is restart-idempotent (offset-0 re-read appends nothing; partial overlap appends only the new tail) and a gap ahead of the snapshot raises rather than silently advancing, preserving a valid prefix. Recreate test pattern, port all six.
5. `exchange_recorder/test_http_provisional_finalize.py` (lines 30, 157, 186, 220): finalize mutates the pending row in place preserving id, ts, path, and track fields (second track resolution deliberately ignored); missing entry returns False with zero side effects, no phantom row; post-persist sink fires exactly once at finalize (docstring records the real regression it pins). Recreate test pattern, top priority.
6. `exchange_recorder/test_http_provisional_flow.py` (lines 33, 137, 167): dropped request deletes provisional without finalize or fallback (guard callbacks raise if the wrong branch runs); orphaned provisional recovers via a fresh exchange with a different id; readback fallback closes the original live generation. Reuse concept plus recreate test pattern.
7. `exchange_recorder/test_unparsed.py` (lines 53, 89, 132): unparseable traffic still captured raw with `transport.parse_failure` marker and best-effort model/client-version; non-JSON garbage omits bad keys rather than writing them; recording failure never propagates out of the proxy hook. Reuse concept, strongly.
8. `exchange_recorder/test_codex_http_artifacts.py` (line 108): every capture assertion parametrized over both the fresh path and the provisional-finalize path; transport-layer secret redaction (`authorization` and `set-cookie` redacted, benign headers verbatim, lines 165-170). Reuse concept plus recreate test pattern; the dual-path parametrize is the highest-leverage structural idea.
9. `storage/test_disk_codex_artifacts.py`: write ordering asserted explicitly (transport before events before turn, line 117); structural validation before any bytes land, invalid input leaves no partial write (lines 167, 187); completed turns strip the resume cursor (line 62). Recreate test pattern.
10. `storage/test_disk_delete.py::test_rewrite_failure_preserves_cache_order` (line 59): delete rollback restores position, not just membership; a naive map-based rollback fails this. Recreate test pattern.
11. `storage/test_disk_cache_backfill.py`: lazy repair from authoritative artifacts is durable, never manufactures data for legitimate zeros, and never reads a tmp dir as authoritative (lines 53, 86, 108, 139). Reuse concept plus recreate test pattern.
12. `storage/test_exchange_sink.py` (lines 54, 67): tier-1 durability first; observers are best-effort, isolated, order-preserved; three independent registries. Reuse concept plus recreate test pattern.
13. `storage/test_disk_exchange.py::test_read_exchange_redacts_and_rewrites_legacy_transport_headers` (line 181): read-time redaction self-heals the file on disk. Reuse concept.
14. `storage/test_disk_layout.py` (line 80): layout golden pinning the `.tmp`/`.bak`/`.del` suffix vocabulary and all artifact filenames; prerequisite for the recovery tests. Recreate test pattern; adopt the three-suffix vocabulary directly.
15. `exchange_recorder/test_http_provisional_persist.py` (line 99): a no-op pipeline must not record curated artifacts even when the serializer would reorder keys; `_make_noop_state` deliberately builds non-canonical key order. Recreate test pattern; non-obvious trap.
16. `exchange_recorder/test_stats.py` (line 176): adapter parse failure yields a recorded `response_parse_failure` status, not a dropped record; call-count-as-cost assertions. Reuse concept.

House-style techniques: surgical failure injection by argument predicate; residue assertion (`no *.tmp / *.bak in root`) after every injected failure, as a shared helper; shared builder module per layer with a fixed timestamp constant for deterministic snapshots.

Rejections: `storage/test_disk_legacy_anchor.py` nuclear-wipe migration (keep only malformed-index-line tolerance), provider-specific text extraction in `test_stats.py`, SSE payload shape in `test_emit.py` (keep the assert-legacy-key-absent idiom).

### Integration + wire store + shared proxy (done)

Paths under `api/` in the worktree.

Priority acceptance candidates:

1. `src/transport_matters/session/testing.py` (`TestDb`, lines 65-198) plus `conftest.py` (`test_db` line 260, `_manage_test_litter` line 269): template-clone Postgres provisioning (`CREATE DATABASE ... TEMPLATE`, per-test DB in milliseconds), session-plus-xdist-worker namespaced names capped at 63 bytes, litter sweep that can only reach its own namespace, `pg_terminate_backend` before drop, `next_notify_payload` for awaiting typed NOTIFY signals, pinned migration-head constant. Recreate fixture concept. Note: littleorgans already has `internal/db/src/test_support.rs::TestDb` (unique-name create plus migrate); the template-clone speedup and the namespace-scoped sweep are the deltas worth adopting.
2. `session/test_testing.py`: the fixture tests the fixture. Namespace isolation proven with an owned DB, a foreign-session DB, and a customer-decoy name, sweep drops exactly one (line 54); partial-clone failure leaves no orphan DB (line 100). Recreate test pattern; mandatory before trusting any DB-dropping fixture.
3. `tests/integration/test_transcript_snapshot_roundtrip.py` (lines 113, 166, 200): one poll writes session events plus a byte-identical tier-1 snapshot including normalizer-dropped records; idempotent across fresh-process re-tail from offset 0; snapshot dir removed mid-run halts cursor advance exactly (session events never get ahead of a snapshot hole). Recreate test pattern, top priority.
4. `session/test_capture_without_web.py::test_exchange_and_session_capture_work_with_web_runtime_off` (line 46): disk write, Postgres event write, and LISTEN/NOTIFY fan-out all function with no HTTP app imported anywhere in the test module; whole chain asserted in one test; per-test private NOTIFY channel name. Recreate test pattern, top priority; this is the capture-is-standalone separation proof.
5. `session/test_wire_writer.py`: replay idempotence asserted as whole-store snapshot equality across six tables (`_wire_state`, lines 405-429) with zero duplicate notifications (line 139); dedup byte budget measured against true wire bytes from `meta.json` (lines 224, 245-251); store outage is a counted, logged non-throw (line 298); GC-vs-cached-verified-set self-heal (line 341). Recreate test pattern.
6. `session/test_wire_normalization.py`: NUL bytes stripped before hashing (Postgres jsonb cannot hold `\x00`; hash, stored body, and reconstruction must agree, line 91); negative control proving stamp-stripping is not over-broad (line 72); set hash sensitive to order and kind (line 132); exact reconstruction round-trip (line 79); cross-module constant mirror pinned by test (line 100). Recreate test pattern, top priority for a content-addressed store.
7. `tests/integration/test_parent_death_reaping.py` (lines 101, 114, 127) plus `src/transport_matters/test_self_reap.py`: armed / armed-late / unarmed-control triad with real processes; the control proves the repro is probative. Unit layer fully seam-injected (`getppid`, `kill`, `hard_exit`, `sleep` as parameters), idempotent install proven by thread count. Recreate test pattern.
8. `tests/integration/test_shared_proxy_subprocess.py`: real loopback origin via `asyncio.start_server`, `assert_port_closed` polling, register-serve-deregister-port-closes-re-register cycle (line 62); SIGTERM the proxy child then `supervise()` rehydrates both bindings under a new pid (line 129). Recreate fixture plus test pattern; the only genuine end-to-end proxy harness. Companion `net_helpers.py::poll_http`: retry only on connection failure, any HTTP status is a real answer; ports allocated by the production allocator so there is one bind-port-0 implementation.
9. `session/test_ingest.py`: one poison record must not lose the stream. Real manufactured poisons (140k tokens for tsvector program limit 54000; literal NUL forcing 22P05); good records commit around the hole (`seq == [0, 2]`), dead-letter row carries byte-range provenance and capped excerpt, SQLSTATE asserted; dead-letter insert failure aborts the batch and holds the cursor (lines 295, 371, 415, 492). Recreate test pattern.
10. `session/test_listen.py`: NOTIFY listener survives `pg_terminate_backend` of its own connection (reconnect, catch-up signal, resume, line 317); queue overflow degrades to a durable catch-up request, never silent loss (line 273); `connection_pid` exposed purely as a test seam. Recreate fixture plus test pattern; cheapest realistic DB connection-failure injection.
11. `session/test_wire_writer_live_status.py`: generation-fenced live status; late finalize of a superseded generation is a no-op (lines 130, 192); notify failure rolls back the data write together with the status close (line 273); subagent finalize cannot close parent status (line 224). Recreate test pattern.
12. `session/test_conversation_parity.py` (lines 27, 62, 106): one cross-language golden corpus (`packages/activity/fixtures/conversation-parity.json`) holds the TS expectations, the Python projector, and the SQL count query to identical answers, exhaustively over every cursor position. Reuse concept, strongly; the right shape for Rust-plus-Postgres projector/query drift.
13. `session/test_session_affinity_stamp.py`: provenance stamp is write-once, atomic group, forgery-proof from client input, and survives referent hard-delete as a tombstone (lines 98, 120, 233, 506). Recreate test pattern for capture provenance columns.
14. `shared_proxy/test_process.py`: pid-file recovery safe under pid reuse; a live non-matching pid is never killed (line 124); SIGTERM-to-SIGKILL escalation bounded (line 161). Recreate test pattern; prevents a capture supervisor killing an unrelated process after pid rollover.
15. `shared_proxy/test_addon.py`: about nine fail-closed experiments: unmapped listen port never reaches the capture kernel (line 482), port reuse after rebind fails closed (line 431), interleaved flows keep run storage isolated on real disk (line 337). Recreate test pattern; mitmproxy doubles do not port.
16. `shared_proxy/test_manager.py` and `test_core.py`: desired-state rehydration after subprocess restart (line 142); failed ack preserves the previous snapshot (line 223); transactional binding registration proven by ordered call ledger (`register:run-1`, `unregister:run-1`); `SlowItemsDict` blocking-iterator race injection without sleeps (line 418). Recreate fixture (countdown-failure fake) plus test pattern.
17. `test_wire_store_observer.py`: `max_in_flight == 1` connection-concurrency assertion (line 401); `aclose` drains pending writes (line 375); parse-failed response still recorded as a complete exchange (line 414). Recreate test pattern.
18. `test_gateway_supervisor.py`: shutdown ordering proven by a fake child whose `stop()` performs a real HTTP GET against the parent's still-accepting socket (line 270); genuine SIGTERM-ignoring child escalated to SIGKILL within a bounded grace (line 236). Recreate test pattern; encoding ordering as a callback-must-succeed-at-a-real-socket beats call-order lists.
19. `test_capabilities.py`: external-binary probing is total; absence proven by making `subprocess.run` raise if invoked (a negative seam, line 47); probe failures of three exception classes never escape (line 144); real tiny shell scripts as installed binaries. Recreate test pattern.

Rejections: `tests/integration/test_health.py` (canary only), `test_storage_roots.py` (concept only: deprecation warns, never blocks), mitmproxy-shaped doubles.
