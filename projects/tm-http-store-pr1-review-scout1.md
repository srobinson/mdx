# PR #258 review — spec anchor (scout 1)

**PR:** `wire-store-pr1-frozen-seam` @ `64a295e` vs `main` (`2e33e6e`). CI 9/9 green (gh confirmed). Tree pristine before and after review (verified twice; the four touched test files re-run locally: 17 passed).
**Anchor:** `~/.mdx/projects/tm-http-store-spec.md` §1 (boundaries), §4 (producer/seam), §8 PR-1. Lenses: code-review (high effort) + code-hygiene.

**Verdict: conditional signoff.** Scope fidelity is exact; one medium doc-contract finding (F1) should be fixed before merge, one minor test hygiene item (F2). No runtime defect found.

## Scope fidelity vs §8 PR-1 (all pass)

| Spec requirement | Evidence |
|---|---|
| `exchange_sink.py` multi-subscriber, no nested wrappers | `storage/exchange_sink.py`: `_sinks`/`_deleted_sinks` lists, `register_exchange_sink`, `register_exchange_deleted_sink`, `clear_exchange_sinks`; flat registry, no wrappers |
| Deleted event `(exchange_id, run_id)` with same registry semantics | `ExchangeDeletedSink = Callable[[str, str], None]`; `emit_deleted` mirrors `emit_to_index` (snapshot iterate, per-subscriber try/except, log+swallow) |
| `emit_exchange_deleted` reaches the registry | `exchange_recorder.py:emit_exchange_deleted` calls `emit_deleted(exchange_id, run_id)` before the SSE broadcast |
| Registration site composes through the new API | `addon_runtime.py:_start_session_capture` → `register_exchange_sink(_make_exchange_cursor_sink(...))`; `close_capture_runtime` → `clear_exchange_sinks()` |
| No store, no schema, behavior identical with one subscriber | Diff is 7 files: the two blessed touches + 4 test files + the sink module. No migration, no writer, no observer module |
| Frozen files untouched | No edits to `addon.py`, `addon_handlers.py`, persist paths, `ir.py`, adapters, `response_parser`, ingest, `pgContracts.ts`, `run_lifecycle`, `SessionWriter`, `docs/ARCHITECTURE.md` (diff stat exhaustive) |
| `addon_runtime.py` gains only wiring lines | 646 LOC before and after (net-zero rename of import + 2 call sites) |
| Old path deleted completely (DRY) | `rg set_exchange_sink\|clear_exchange_sink[^s]` → zero hits at head; no parallel API |
| Acceptance: fan-out + failure isolation tested | `test_emit_fans_out_to_all_subscribers`, `test_failing_subscriber_does_not_stop_peers` (ordering asserted: peers before AND after the failing subscriber fire) |
| Acceptance: deleted event observed by test subscriber, red before recorder touch | `test_emit_exchange_deleted_notifies_deleted_sink_registry` (unit, exercises `recorder.emit_exchange_deleted`) + `test_delete_http_provisional_exchange_notifies_deleted_sink_registry` (integration through the real delete path); both fail without the recorder edit |
| Acceptance: existing sink tests pass unchanged | Assertions preserved verbatim in all pre-existing tests; only the register/clear API rename applied |

Deletion lockstep is correct by construction at both call sites: `exchange_recorder.py:delete_http_provisional_exchange` and `codex/exchange.py` (repair path, :180) fire `emit_exchange_deleted` only after `storage.delete_exchange` succeeds; a failed tier-1 delete returns False before any registry event.

## Findings

### F1 (medium, doc contract) — `storage/exchange_sink.py` module docstring documents a double-fire that no code path emits

The new docstring states: "for HTTP-provisional flows `emit_to_index` fires once when the provisional exchange persists (request side only) and again at finalize … under the same `entry.id`."

That contract does not exist in the capture plane:

- `exchange_recorder.py:persist_http_provisional_exchange` has no `emit_to_index` call (it calls `persist_exchange` then `emit_exchange`, the SSE broadcast).
- All four `emit_to_index` call sites fire at completion only: `persist_http_exchange` (non-provisional), `_finalize_http_provisional_exchange`, `codex/exchange.py:_persist_codex_exchange`, and the codex finalize seam, whose in-code comment says verbatim "feeds the observer here, exactly once … so there is no double emit."
- The regression test docstring (`test_finalize_http_provisional_exchange_feeds_post_persist_sink`) records that `emit_to_index` was historically reached only on the dead non-provisional branch and the fix moved it to finalize.
- The codex test is literally named `test_codex_finalize_feeds_post_persist_sink_once_at_finalize`.

The real contract: exactly one `emit_to_index` per exchange, at completion; and `emit_deleted` can arrive for a provisional exchange the subscriber never saw (repaired away before finalize), so the docstring's "instead" wording is also misleading.

Why it matters: this is the load-bearing contract doc spec §4 asked for, and PR-2's writer design consumes it. Under the frozen boundary (§1: no edits to the recorders' persist paths) a provisional-time fire can never be added, so the docstring is unfixably false as written, not merely forward-looking. No runtime defect: PR-2's UPSERT-by-`exchange_id` absorbs either firing pattern.

Fix: reword the docstring to the single-fire-at-completion contract plus "deletions may reference an exchange never emitted." **Spec-side action (mine, pending orchestrator direction):** spec §4 writer step 2 ("the provisional fire inserts the request side; the finalize fire updates the response columns") carries the same false assumption inherited from the integration scout and needs a matching patch — the wire_exchange row lands once, at finalize, and the delete-then-reinsert idempotency clause covers replays, not provisional/finalize phases.

### F2 (minor, test hygiene) — duplicated autouse fixture in `storage/test_exchange_sink.py`

`_clean_registry` (clear/yield/clear) is declared identically in both `TestExchangeSink` and `TestExchangeDeletedSink`; one module-level autouse fixture serves both. Same file also carries a local `boom` in the deleted-sink test duplicating module-level `_boom` in shape (signatures differ, so parameterizing is optional; the fixture consolidation is the real item).

## Observations (no action for PR-1)

- Registration is append-only with clear-all teardown: a second `_start_session_capture` without an intervening `close_capture_runtime` would now stack two cursor sinks where the old API silently replaced. Not reachable today (only `load_shared_capture_runtime` passes `binding_for_run_id`, the shared runtime is a process singleton, and a double start already leaked the tailer under old semantics); hazard parity with the old `clear_exchange_sink`, which also dropped a sink it did not own. PR-2's observer shares the capture-runtime lifecycle, which is the intended composition.
- The two fan-out loops in `emit_to_index`/`emit_deleted` are near-twins; a generic helper was considered and rejected — the arity difference makes the indirection cost more than the six shared lines.
- Docstring contract addition (double-fire) was spec-mandated for PR-1 ("document … while there"), so its presence is in-scope; only its content is wrong (F1).
