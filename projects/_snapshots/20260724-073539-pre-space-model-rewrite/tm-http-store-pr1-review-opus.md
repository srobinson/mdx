# PR #258 review — wire-store PR-1 (frozen seam)

**Branch:** `wire-store-pr1-frozen-seam` · **head:** `64a295e` · **base:** `main` (`2e33e6e`)
**Reviewer:** Opus 4.8 (contract-weight, read-only) · **CI:** 9/9 green · **tree:** pristine (`git status --porcelain` empty)
**Spec:** `~/.mdx/projects/tm-http-store-spec.md` §1 (producer/seam), §4 (frozen touches), §8 PR-1

## Verdict

**Signoff with two LOW notes.** Zero correctness defects on any real path. The frozen capture-plane
surface is respected exactly: the only non-test files changed are the three blessed edits
(`exchange_sink.py`, `exchange_recorder.py::emit_exchange_deleted`, `addon_runtime.py` cursor-sink
registration). Every brief verification (a)–(f) passes. The two notes below are minor and may be
folded in before merge or deferred to PR-2, which touches the same seam.

## Frozen-surface audit (brief item e)

Changed non-test files: `addon_runtime.py` (import rename + two call renames), `exchange_recorder.py`
(one `emit_deleted` call + import), `storage/exchange_sink.py` (the seam). Untouched, as required:
`ir.py`, adapters, `response_parser`, ingest paths, `pgContracts.ts`, `run_lifecycle`, `SessionWriter`,
`addon.py`, `addon_handlers.py`, recorder persist paths. No schema, no store. Confirmed via
`git diff --stat main...HEAD` and symbol grep.

## Verification matrix

| Ask | Result | Evidence |
|---|---|---|
| (a) single-subscriber semantics preserved | PASS | `emit_to_index` over `tuple([sink])` is one call; spec "behavior identical with one subscriber" holds. |
| (a) subscribe/unsubscribe orphan-free | PASS (with note 1) | `register_exchange_sink` appends; `clear_exchange_sinks` (in `close_capture_runtime`) drops all; registration is the last statement in `_start_session_capture` so it is all-or-nothing. No per-subscriber unregister exists. |
| (a) one failing subscriber cannot starve peers | PASS | `emit_to_index`/`emit_deleted` wrap each `sink(...)` in its own try/except; `test_failing_subscriber_does_not_stop_peers`, `test_failing_deleted_subscriber_does_not_stop_peers`. |
| (b) deleted event reaches every subscriber | PASS | `emit_deleted` iterates `tuple(_deleted_sinks)`; `test_deleted_event_reaches_subscriber`. |
| (c) `emit_exchange_deleted` fires on real deletion paths | PASS | Real callers `exchange_recorder::delete_http_provisional_exchange` and `codex/exchange` both reach `emit_exchange_deleted` → new `emit_deleted`; arg order `(exchange_id, run_id)` matches `ExchangeDeletedSink`; `test_delete_http_provisional_exchange_notifies_deleted_sink_registry` covers the real path. Sink notified before the SSE broadcast, per spec "store deletes run lockstep with tier-1." |
| (d) cursor sink not dropped | PASS | `register_exchange_sink(_make_exchange_cursor_sink(...))` appends; nothing removes it; the sole registrant survives the rename. |
| (e) no frozen-plane file touched beyond blessed edits | PASS | See frozen-surface audit above. |
| (f) working tree pristine | PASS | `git status --porcelain` empty at head `64a295e`. |

## Notes

### Note 1 (LOW, removed-behavior / altitude) — `storage/exchange_sink.py::register_exchange_sink`
`set_exchange_sink` (replace) became `register_exchange_sink` (append), and the registry exposes only
`clear_exchange_sinks` (clear-all), no per-subscriber unregister. The old replace semantics were
self-healing: a second registration overwrote the first. Append is not. Today there is exactly one
registration site (`_start_session_capture`) cleared once (`close_capture_runtime`), so this is safe.
The latent risk lands in PR-2, which composes the store observer at the same site: if capture is ever
re-initialized in-process without an intervening `clear_exchange_sinks`, the cursor sink accumulates and
`register_session_cursor` is scheduled N times per persisted exchange. Not a defect in PR-1's scope;
worth a one-line guard (idempotent append, or dedup on registration) when the second subscriber arrives.

### Note 2 (LOW, DRY) — `storage/exchange_sink.py::emit_to_index` / `emit_deleted`
The two emitters duplicate the fan-out-with-isolation pattern verbatim: snapshot `tuple(registry)`,
per-sink try/except, `_log.warning("... failed for exchange %s", id, exc_info=True)`. Repo CLAUDE.md
states zero tolerance for duplication. A shared private helper (`_fan_out(sinks, invoke, exchange_id, label)`)
collapses both to one line each. Trivial; bodies are tiny, so this is a craftsmanship fold-in, not a blocker.

## Acceptance (spec §8 PR-1)
- registry fan-out + per-subscriber failure isolation — met (`test_emit_fans_out_to_all_subscribers`, both failure-isolation tests).
- deleted event observed by a test subscriber, red before the recorder touch — met (`test_emit_exchange_deleted_notifies_deleted_sink_registry`, `test_delete_http_provisional_exchange_notifies_deleted_sink_registry`).
- existing sink tests pass — met; the sink tests were renamed to the new API (unavoidable given the rename), semantics unchanged.
