---
title: PR #263 adversarial review — realtime slice 2 (vocabulary + SSE reframer + dark fold/retract)
type: review-findings
reviewer: claude
pr: 263
branch: realtime-slice2-vocab-reframer-folds
head: 843ebb4445d67af1e00a27c31611dd46c125c402
spec: ~/.mdx/projects/tm-realtime-spec.md (§2, §4.1, §4.2, §5.4, §5.5 slice-2 reds, §7 row 2)
date: 2026-07-10
verdict: 1 MINOR, 0 MAJOR, 0 BLOCKER
---

# Verdict

One MINOR (a test-coverage gap on the reframer's second overflow entry
point). No blockers, no majors. The byte-tail framing is proven correct by
mutation, the classifiers reuse the pinned protocol helpers, the machine
changes match §5.4 exactly and their reds are load-bearing, and the slice is
dark. Every claim verified against source at head `843ebb4`, not diff text.
Working tree confirmed pristine before and after review; all mutation
experiments ran in a scratchpad clone, never in the repo.

# 1. Reframer framing — CONFIRMED, mutation-tested

**Byte tail is real.** `IncrementalSseFrames.feed` (`sse.py`) concatenates
`self._tail + chunk` as bytes, splits with `bytes.splitlines(keepends=True)`,
and pops an unterminated last line back into `self._tail` as bytes. Decoding
happens only in `_sse_data_object` on a complete line
(`body.decode(errors="replace")` before `json.loads`), so a chunk boundary
inside a multi-byte UTF-8 sequence can never corrupt JSON.

**The multi-byte test is red against a string tail.** Mutation M1 (decode the
incoming chunk with `errors="replace"` and re-encode — the exact corruption a
per-chunk string decode produces): both
`test_incremental_sse_matches_whole_buffer_at_every_byte_boundary` (Thai +
`café` payloads, every split point, plus a full byte-by-byte feed) and
`test_incremental_sse_retains_trailing_partial_bytes` (split one byte into a
Thai character) FAILED. Not tautologies. The every-boundary test compares
against `iter_sse_data_objects`, which now shares `_sse_data_object` — that
sharing cannot mask a parse bug because the multiple-events, [DONE]/malformed,
and trailing-partial tests all assert explicit dict literals.

**Other required proof cases present and real:** multiple events per chunk,
`[DONE]` skipped, malformed JSON skipped with later events intact, trailing
partial completed by the next chunk, tail-overflow resync, non-positive cap
rejected. Chunk-boundary `\r|\n` splits are handled (the `\r` line is
processed immediately; the orphan `\n` becomes an ignored empty line —
payload-equivalent to whole-buffer, confirmed by the every-boundary sweep).

**MINOR (the one finding):** the overflow logic has two entry points and only
one is tested. `test_incremental_sse_overflow_drops_record_then_resyncs`
drives the **tail**-overflow path (unterminated giant line →
`_discarding_record` + `_discarding_line`). The **in-loop** path — a single
chunk containing an already-terminated line longer than `max_tail_bytes`
(`if len(line) > self._max_tail_bytes` inside the completed-lines loop, which
sets `_discarding_record` without `_discarding_line`) — is never exercised. I
drove it manually in the clone: a terminated 33-byte line at cap 32 followed
by a normal record correctly discards through the record boundary and
resyncs, including a multi-line oversized record. Correct code, uncovered
branch in brand-new machinery; one test feeding
`b"data: " + b"x"*33 + b"\n\n" + frame` at cap 32 closes it.

**Observation (not a finding):** the shared-helper refactor changes
`iter_sse_data_objects` from decode-then-`str.splitlines` to
`bytes.splitlines`-then-decode-per-line. Verified deltas: `str.splitlines`
splits on NEL/U+2028/U+2029 (legal raw inside JSON strings), so the old code
LOST such payloads; the new code parses them. Raw `\v \f \x1c-\x1e` are
illegal in JSON either way (bytes.splitlines does not split on them —
verified empirically — the line survives and `json.loads` rejects it, same
net outcome). The finalize-path callers (`adapters/anthropic.py`,
`codex/response_parser.py`) keep whole-buffer semantics per the spec's
"never fed raw chunks" pin; behavior is preserved or strictly improved.

# 2. Reuse — CONFIRMED

- Codex classifier imports `codex_payload_event_type`,
  `codex_terminal_status`, `codex_tool_call_key`, and the
  `CODEX_*` event/item constants from `codex/protocol.py` (all pre-existing;
  the diff adds no protocol code). Terminal detection defers to
  `CODEX_TERMINAL_STATUS_BY_EVENT_TYPE` (`response.completed`/`failed`) — no
  hand-rolled terminal list.
- The open-item set is the classifier's own state, which is exactly what §4.2
  prescribes ("tracks the open-item set … rather than adding a third payload
  fold"); it mirrors the engine's anonymous-item convention
  (`CODEX_ANONYMOUS_ASSISTANT_ITEM_ID` for id-less text deltas) and keys
  closes by item id with `codex_tool_call_key` fallback.
- Anthropic rules are re-expressed incrementally, per the spec's explicit pin
  that `_inbound_response_sse` cannot resume across chunks; the adapter uses
  inline event-name literals itself, so no shared constant was bypassed.
- `LIVE_STATUS_KINDS` becomes the single source for
  `RUN_LIVE_STATUS_KINDS` (contracts alias); migration 0009 imports the alias
  and the tuple value and order are unchanged, so the generated DDL is
  byte-identical (migrate tests passed in the gate).
- Test scaffolding: shared `_assert_fact` helper; `machineTestEvents.ts` adds
  `wireSimpleRecord` and refactors `wireIdle` onto it instead of copying the
  literal a third time.

# 3. Classification edges — CONFIRMED, mutation-tested

- `redacted_thinking → reasoning` in `_anthropic_start_state`; mutation M3
  (drop it) turned the parametrized start test red.
- Codex interleaved opens: `_close_item` pops the item and reports the newest
  still-open kind; stop (`kind=None`) only when the set empties. Mutation M2
  (emit a global stop on every `output_item.done`) turned
  `test_codex_tracks_interleaved_open_items_without_false_global_stop` red.
  The test also pins: done of a non-current item emits nothing (no fact, not
  even an affirm), done of an unknown/never-opened item is a no-op, and
  `response.completed`/`failed` clear the set (terminal test, both events).
- Server-frames-only: `CodexLiveClassifier.feed`/`feed_batch` take
  `from_client` and return `None` without touching state;
  `test_codex_classifier_ignores_client_frames_without_mutating_state`
  re-feeds the identical payload as a server frame and gets `seq == 1`,
  proving no state mutation — self-evidently non-tautological. (The actual
  tap pinning `message.from_client` is slice 3, as specced.)
- Batch coalescing: `feed_batch` emits at most one fact per batch at
  `initial_seq + 1`; stop→start collapses to the final state, stop→same-kind
  reassert suppresses entirely (and the follow-up terminal getting `seq 2`
  proves the seq counter rolls back on suppression). Terminals bypass
  dedup/suppression. Matches §4.1's coalescing contract; the deferred-stop
  slot cycle is observer-side slice 3.
- Edge noted (observation only): an id-less assistant message opened via
  `output_text.delta` under the anonymous key cannot be closed by an id-less
  `output_item.done` (`_codex_item_key` has no anonymous fallback), so its
  stop arrives at terminal instead of item-done. Real Codex `done` items
  carry ids; consequence is a late stop on a best-effort plane, and the
  derivation engine has the same shape. Also additive beyond the §2 fact
  shape: `LiveStatusFact.terminal` distinguishes terminal from bare stop —
  in-memory only, useful for slice 3's deferral logic, harmless.

# 4. TS fold/transition (blocker-1 fix) — CONFIRMED, mutation-tested

- `foldReasoning`/`foldGenerating` (`runActivityContext.ts`): on
  `eventStream(event) === "wire"` route through `foldWireAsserted` with a
  patch that carries `status` only — `lastActiveStatus` is written solely on
  the record branch, `pendingToolCallIds` is never touched, and
  `foldWireAsserted` stamps `wireAssertedExchangeId` from
  `event.wireExchangeId`. Record-stream behavior byte-identical to the old
  body.
- `WIRE_RETRACTED_TRANSITIONS` is now registered on exactly six nodes —
  verified by enumerating every state node: `reasoning` (new), `generating`
  (new), `running-tools`, `needs-you-asked`, `idle`, `stalled`; `starting`
  and `exited` correctly excluded per §5.4. `WireRetractedEvent` doc comment
  lists the grown state set.
- Mutations: T1 (revert `foldReasoning` to the pre-PR `markApplied` body) →
  both the fold-purity test AND the reasoning retract test FAILED (the
  retract restore recomputes from `lastActiveStatus`, so pollution breaks it
  too — the tests interlock). T2 (remove `wire.retracted` from the
  `reasoning` node) → reasoning retract test FAILED (xstate silently drops
  the event). T3 (same on `generating`) → generating retract test FAILED.
  All dead against the unamended machine, as §5.5 requires.
- The retract tests assert the full §3.3 recompute: restored status equals
  the record baseline (cross-kind: live reasoning over record generating and
  vice versa, plus the tool case), `wireAssertedExchangeId` nulled. The
  fold tests assert `lastActiveStatus` stays `running-tools` and
  `pendingToolCallIds` stays `["tool-record"]` under a live assert, and the
  T11 double-assert idempotency case now runs on `wireGenerating`.

# 5. Dark scope — CONFIRMED

- `IncrementalSseFrames` has zero src callers; `transport_matters.live_status`
  is imported in src only by the contracts alias. No tee/`on_chunk`, no
  `addon_handlers` change, no observer — producer is slice 3.
- `wireCandidateEvent` untouched (its three live arms are slice 4);
  `machineTestEvents.ts` builders are test-only minting. No consumer
  admission, no projection/DTO/SSE-router change.
- Import DAG holds: `live_status.py` imports only `codex/protocol` (pure
  leaf); storage untouched entirely; session's only edit is the constant
  alias. No cycles.

# 6. DRY / sizing

- Touched-file sizes: `live_status.py` 355, `test_live_status.py` 315,
  `sse.py` 81, `test_sse.py` 67, `runActivityMachine.ts` 641,
  `runActivityContext.ts` 689, `machineTestEvents.ts` 264,
  `wireActivity.test.ts` 447. All under 700. Watch item:
  `runActivityContext.ts` at 689 joins `session/writer.py` (643) on the
  approaching-the-limit list before slice 4 lands its admission changes.
- No duplicated parse found; reuse posture per §2 above.

# Gate

Run at head on the reviewer's machine, all three slice-2 gates, judged by
output content: `cd api && just check && just test` → "All checks passed!",
mypy "no issues found in 464 source files", `1919 passed` (up 25 from
slice 1's 1894 — the new suites). `pnpm --filter @tm/activity test` → 203
passed, 22 skipped (the pre-existing `skipIf` pg-integration/pg-smoke suites,
env-gated, untouched by this PR). `pnpm --filter @tm/activity typecheck` →
clean.

# Mutation table

| # | Mutation (scratchpad clone, each reverted) | Red test | Result |
|---|---|---|---|
| M1 | Per-chunk `decode(errors="replace")` of the reframer input | every-byte-boundary + trailing-partial multibyte tests | both FAILED ✓ |
| M2 | `output_item.done` always emits global stop | interleaved-open-items test | FAILED ✓ |
| M3 | Drop `redacted_thinking` mapping | block-start parametrized case | FAILED ✓ |
| T1 | Revert `foldReasoning` wire branch to pre-PR body | fold-purity + reasoning-retract tests | both FAILED ✓ |
| T2 | Remove `wire.retracted` from `reasoning` node | reasoning-retract test | FAILED ✓ |
| T3 | Remove `wire.retracted` from `generating` node | generating-retract test | FAILED ✓ |
