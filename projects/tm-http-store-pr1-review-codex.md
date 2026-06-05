# PR #258 frozen seam review

## Verdict

Issue, high severity, 98/100 confidence. Head `64a295ecac77521794ecd38da0e7fd9890a7222d` should not freeze this seam until the producer contract is reconciled.

## Finding

`api/src/transport_matters/storage/exchange_sink.py:module docstring` promises that provisional HTTP capture calls `emit_to_index` once with the request side and again at finalize under the same exchange id. The live producers implement finalize only delivery:

- `api/src/transport_matters/exchange_recorder.py:persist_http_provisional_exchange` persists tier 1 and broadcasts without calling `emit_to_index`.
- `api/src/transport_matters/exchange_recorder.py:_finalize_http_provisional_exchange` calls `emit_to_index` once after finalization.
- `api/src/transport_matters/codex/exchange.py:finalize_codex_provisional_exchange` also documents and implements one finalize callback.
- `api/src/transport_matters/test_exchange_recorder_http_provisional_finalize.py:test_finalize_http_provisional_exchange_feeds_post_persist_sink` and `api/src/transport_matters/codex/test_exchange_finalize_sink.py:test_codex_finalize_feeds_post_persist_sink_once_at_finalize` assert zero provisional callbacks and one finalize callback.

This contradicts spec section 4 and the PR 2 acceptance sequence in section 8. A PR 2 observer cannot perform the specified provisional insert followed by finalize update, and a repaired provisional can deliver a delete for an exchange the observer never received. Historical PR #23 deliberately established finalize only HTTP delivery, and PR #25 established the same Codex rule.

Resolution requires a contract owner decision because spec section 1 forbids persist path edits while sections 4 and 8 require provisional then finalize delivery. Either bless producer emission changes with red first provisional callback tests, or revise the spec, sink docstring, and PR 2 writer lifecycle to finalized only delivery.

## Verified clean

- `api/src/transport_matters/storage/exchange_sink.py:emit_to_index` and `api/src/transport_matters/storage/exchange_sink.py:emit_deleted` fan out to every subscriber using snapshot iteration and isolate each subscriber failure.
- `api/src/transport_matters/exchange_recorder.py:emit_exchange_deleted` reaches the deleted sink registry before SSE broadcast. The real HTTP and Codex provisional deletion paths both call it.
- `api/src/transport_matters/addon_runtime.py:_start_session_capture` preserves the existing cursor sink through `register_exchange_sink`.
- `api/src/transport_matters/addon_runtime.py:close_capture_runtime` clears both registries. Current standalone and shared proxy topologies own one capture runtime per process, so a subscriber scoped unsubscribe is not required by PR 1.
- The diff changes only the three blessed production files and four colocated tests. `ir.py`, adapters, response parsing, ingest, `pgContracts`, run lifecycle, `SessionWriter`, and `docs/ARCHITECTURE.md` are untouched.
- Production file sizes remain within policy: `addon_runtime.py` 646 lines, `exchange_sink.py` 76 lines, `exchange_recorder.py` 441 lines.

## Verification

- Focused read only pytest run: 14 passed.
- `fmm validate`: all 1090 indexed files current.
- PR checks: 9 of 9 successful.
- Final repository check before verdict: pristine on `wire-store-pr1-frozen-seam` at `64a295ecac77521794ecd38da0e7fd9890a7222d`.
