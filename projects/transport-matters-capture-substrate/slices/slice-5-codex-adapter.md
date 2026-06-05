# Slice 5 — codex adapter (read-back) + codex wire capture

**Goal:** capture codex sessions end-to-end — wire + transcript + the DIFF — reusing the §4
port, the slice-4b tailer, and the shared `build_wire_job`. codex is the first **read-back**
provider (no mint; native id learned from the proxied frames).

**Depends on:** slices 1-4 (+ fixes #23/#24), all merged. **Unblocks:** slice 7 (live-tail
completion), slice 8 (backfill). gemini/opencode (slice 6) stay parked.

## ⚠️ HARD REQUIREMENT #1 — codex wire capture seam (the #23 gap, codex side)

#23 fixed claude by feeding `emit_to_index` from the provisional finalize seam. **codex's
wire-capture finalize seams do the same persist but never call `emit_to_index`** —
`codex/exchange.py:136/257/403/526` (RE-CONFIRM these lines against current main; #16-#24 moved
code). Without wiring them, a real codex session captures **ZERO rows** — the exact silent
symptom #23 had. This is priority 1.
- Feed `emit_to_index(entry, artifacts)` from codex's durable-persist seam(s), the same DAG-safe
  injected-sink pattern (`make_index_sink`, no `storage → index` import).
- **REAL-RUN PROOF REQUIRED** (not just unit tests — that's what let #23 ship): a real
  `transport-matters codex` session → `wire_exchange` rows + (once the adapter lands)
  `transcript_turn` rows + the DIFF. Add an integration test driving the codex persist→sink path.
- `raw_dir` is already correct (shared `build_wire_job`, #24) — verify `/raw` resolves for codex.

## Read first (canonical spec)

§5.2 (codex adapter), §2 (read-back correlation key), §7.2 (the SHARED `synth_session_id` — both
the codex wire correlation AND the codex transcript adapter must produce the SAME `session_id`),
§9.2/§9.3 (tailer reuse), §15 risk 2 (read-back tail startup). Real sample:
`~/.codex/sessions/YYYY/MM/DD/rollout-*-<thread_uuid>.jsonl` + `~/.codex/session_index.jsonl`.

## ⚠️ Correlation contract (read-back convergence)

codex is READ-BACK: `native_session_id` = the codex thread uuid (`session_meta.payload.id`, also
the rollout filename uuid, carried in the proxied codex websocket frames). `session_id =
synth_session_id(run_id, "codex", native_session_id)` (uuid5, the SHARED helper from slice-1
`sessions.py`). **The wire side and the transcript side MUST compute the same `session_id` via the
same `synth_session_id`** — that's the §7.2 convergence the pivot depends on. Verify both paths
agree on a real paired sample (HARD GATE, like slice 4a's).

## Files (≤700 LOC; functions ≤150)

1. `index/adapters/codex.py` (~170) — §5.2: `bind` (READ-BACK: native thread uuid →
   `synth_session_id`, `minted=False` — this is where `TranscriptAdapter.bind()` + `RunContext`
   go LIVE, resolving audit finding #2), `locate` (glob
   `~/.codex/sessions/**/rollout-*-<native>.jsonl`, `FileTailSource(format="codex_rollout")`),
   `normalize` (process ONLY `type=="response_item"`; skip `session_meta`/`turn_context`/all
   `event_msg`; map `message`/`function_call`/`function_call_output`/`reasoning` per §5.2;
   `turn_id = uuid5(SESSION_NS, f"{session_id}|{seq}")` — no native per-record id;
   `encrypted_content` → `provider_data`, stripped). Register in `adapters/__init__.py`.
2. **codex wire seam** (HARD REQ #1) — `codex/exchange.py` finalize seam(s) call `emit_to_index`.
3. **codex cursor registration** — read-back: the tailer registers the codex cursor after the
   first codex wire frame reveals the native thread uuid (reuse the slice-4b tailer; `provider→cli`
   = codex→codex). §15 risk 2 one-frame startup lag acceptable.
4. **Audit cleanups** (from the post-slice-4 audit): resolve the dead table-mirror models
   `BlockRow`/`WireExchangeRow`/`TranscriptTurnRow`/`BlockEdge` (`index/models.py`) — USE them if
   the codex read-side genuinely needs them, else DELETE + drop the `__all__` entries (keep
   `SessionRow`, it's used); promote the duplicated `_binding()` test factory into
   `index/conftest.py`.

## Invariants (must not break)

- HARD REQ #1 (codex wire seam) + the read-back correlation contract above.
- `normalize` is pure; emits only the 6 content kinds, never system/tool_def (§4.1.4); `parts`
  reuse `ir.ContentBlock` verbatim (cross-stream dedup).
- codex subagent = a separate forked thread/session → within a session `is_sidechain=False`
  (session-grained, NOT a per-record flag like claude) (§5.2).
- `function_call.arguments` is a JSON **string** → `json.loads` into `ToolUseBlock.input`;
  `function_call_output` → `ToolResultBlock(tool_use_id=call_id, …)`.
- ONE iterate path (slice-4b `iter_complete_records`) — codex rollout is FileTail, no new iterator.
- #17 privacy; DAG: adapters import `ir`(+ sibling adapters) only; codex wire seam uses the
  injected sink (no `storage → index`).

## Acceptance (§13.2; real temp SQLite + golden fixtures + REAL run)

- **codex golden fixture** (real `rollout-*.jsonl`) → `normalize` produces correct
  `NormalizedTurn`s (message/function_call/output/reasoning; skips session_meta/turn_context/
  event_msg → None).
- **read-back convergence:** wire-side `synth_session_id` == transcript-side `synth_session_id`
  for a real paired codex sample (HARD GATE — state the evidence).
- **codex pivot/diff:** a codex wire exchange + transcript turn sharing content → `session_pivot`
  correspondence + `session_diff` buckets.
- **REAL-RUN (HARD REQ #1 proof):** `transport-matters codex` real session → `wire_exchange` +
  `transcript_turn` rows + live event + `/raw` resolves + DIFF returns. Integration test on the
  codex persist→sink path.
- Audit cleanups landed; `bind()`/`RunContext` now have a production caller.
- `just ci` green.

## Grounding (RE-CONFIRM current, post #16-#24)

`codex/exchange.py` finalize seams (was :136/257/403/526 — verify current). codex websocket
handling (`codex/transport.py`, `addon_handlers.py`) for where the native thread uuid surfaces on
the wire (feeds read-back registration). `index/sessions.py` `synth_session_id` (slice 1).
slice-4b `tailer.py` (reuse). slice-4a `adapters/base.py` port + `claude.py` (mirror structure).
`~/.codex/sessions/` real samples. `make_index_sink`/`build_wire_job` (#23/#24 — shared).

## Build order (TDD)

RE-CONFIRM codex grounding (seam lines, native-id surfacing) → codex.py normalize (golden fixture)
→ codex.py bind/locate (read-back synth) → **codex wire seam → emit_to_index + real-run proof
(HARD REQ #1)** → read-back convergence test (wire==transcript session_id) → codex pivot/diff →
codex cursor registration on first wire frame → audit cleanups → privacy/DAG.

> Codex is the second-hardest adapter (read-back + a wire-seam fix). If the panel judges it
> should split (wire-seam fix as 5a, adapter as 5b), flag the orchestrator.
