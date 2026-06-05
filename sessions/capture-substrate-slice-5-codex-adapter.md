---
title: Capture Substrate Slice 5 — Codex Adapter (read-back) + Codex Wire-Capture Sink Seam
type: sessions
tags: [backend, transport-matters, capture-substrate, slice-5, codex, read-back, correlation, moe]
summary: Codex transcript adapter + codex tier-2 emit_to_index seam (HARD REQ #1) + read-back session correlation; convergence proven end-to-end on a real codex run; author signed off @ 55754e2.
status: complete
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

## Summary

Built slice 5 of the Transport Matters capture substrate as the authoring agent in an MoE warroom (peer reviewer `:3.2`, orchestrator `:2.1`). Branch `feat/capture-slice-5-codex-adapter`, first cut @ `9d5ab4e`, `just ci` green (1097 passed). Codex is the first **read-back** provider: no proxy `--session-id` mint; the native thread uuid is learned from the wire and the `session_id` is synthesized via the shared `synth_session_id` so the wire correlation and the transcript adapter converge on the same id (§7.2).

Key decisions:
- **Emit seam placement (HARD REQ #1):** `emit_to_index` wired into the DURABLE seams only — `finalize_codex_provisional_exchange` (streaming PRIMARY) + `_persist_codex_exchange` (direct). NOT the provisional seam (an abandoned provisional is deleted → a provisional emit would orphan the tier-2 row + dangle `raw_dir`, a #24-class bug) nor the handshake-failure seam (no half-row). Mirrors the claude #23 fix; idempotent UPSERT; finalize→direct delegation does not double-emit.
- **bind()/RunContext made live (audit #2):** `register_session_cursor` now re-binds via `adapter.bind(RunContext(...))`, making the adapter the single authority for session_id derivation, with a runtime convergence guard.
- **Audit premise corrected:** of the 4 "dead" models the brief named, only `BlockRow` was actually dead; `WireExchangeRow`/`TranscriptTurnRow`/`BlockEdge` are live via the slice-3 read API. Deleted only `BlockRow`.

## API / Contract changes

- `index/adapters/codex.py` (new): `CodexAdapter(provider="codex", cli="codex")`.
  - `bind(RunContext) -> SessionBinding`: read-back, `session_id = synth_session_id(run_id, "codex", native_session_id)`, `minted=False`; raises if `native_session_id` is None.
  - `locate(SessionBinding) -> FileTailSource(format="codex_rollout")`: globs `~/.codex/sessions/**/rollout-*-<native>.jsonl`, newest match.
  - `normalize(record, ctx)`: process only `type=="response_item"`; map `message`/`function_call`/`function_call_output`/`reasoning` per §5.2; `developer`→`system` role; `function_call.arguments` JSON-string → `ToolUseBlock.input`; `function_call_output` → `ToolResultBlock(tool_use_id=call_id)`; `reasoning` → `ThinkingBlock` with `encrypted_content` in `provider_data` (stripped from identity); `turn_id = uuid5(SESSION_NS, f"{session_id}|{seq}")`; `is_sidechain=False` (session-grained); `model`/`parent_id` threaded from ctx; unmapped response_items → `UnknownBlock` (captured, not dropped).
- Registered in `index/adapters/__init__.py`; `addon_runtime._PROVIDER_CLI` gains `codex: codex`.

## Database / index changes

- No schema change. Codex wire exchanges flow through the existing `build_wire_job`/`_WIRE_UPSERT`; codex transcript turns through `build_transcript_job`. Both correlate on the synthesized read-back `session_id`.
- Deleted dead `BlockRow` model (+ `__all__` entry + self-test); kept the live mirror models.

## Security / correctness considerations

- `emit_to_index` is best-effort (swallows + logs at WARNING); tier-1 stays authoritative — a tier-2 failure never breaks the wire path.
- DAG preserved: codex/exchange.py imports `emit_to_index` from `storage.exchange_sink` (storage layer), not `index` — no `storage → index` back-edge. codex.py imports `synth_session_id`/`SESSION_NS` from `index.sessions` (acyclic).
- `encrypted_content` rides `provider_data` so it is stripped from block identity (cross-stream dedup, #17 privacy). Golden fixture is structurally faithful but synthetic.

## Performance notes

- Read-back cursor registration fires on `on_binding` at finalize (one-frame startup lag, §15 risk 2 acceptable; tailer reads from byte_offset 0 so nothing is lost). `tailer.register` is idempotent on session_id.

## Convergence resolution (the live run, @ 6a20e08)

Stuart's real `transport-matters codex` run was decisive: 5 codex `wire_exchange` rows, **all session_id NULL** (`/api/index/sessions` empty) — but the rows existed, confirming the emit seam works. Root-caused on the real captured data:
- Codex puts NO top-level `session_id` in `client_metadata`; the id is nested in `client_metadata["x-codex-turn-metadata"]` (a JSON string). `_parse_metadata` only read the top level → `metadata.session_id=None`. `bind_exchange` reads that field directly → NULL-session wire rows that never join a transcript. (This is the [[direct field read vs resolver]] lesson — a richer resolver existed but the join bypassed it.)
- **Convergence equality proven on real paired data:** re-parsing the 4 steady-state captured frames yields `019e9553-56f8-71e2-b4b5-d555aac856d9` == the littleorgans rollout `payload.id`. Frame 1 carries the throwaway window-id `019e9551` (no thread yet → §15 risk-2 startup lag, no rollout).

**Fix (orch-approved, parser-level, DRY):** `_parse_metadata` resolves `session_id` via the shared `codex_session_id_from_provider_metadata` (parses the nested turn-metadata). NOT a header injection (the orch's earlier assumption) and NOT a capture-seam model_copy — the parser is the source of truth so every consumer is correct.

**Blast radius (guard a) — found + fixed a real leak:** `serialize_codex_request` would have injected a top-level `session_id` into re-serialized (mutated) codex frames the client never sent (confirmed on the real capture). `_metadata_to_dict` now skips the top-level write when the id is already encoded nested; a future proxy mint still writes. Added a parse→serialize transparency test.

## Open items

- ~~Tailer `turn_context.model`~~ RESOLVED (F1 @ e8a3006).
- **FRAME-1 disposition (guard b — needs orch call):** the throwaway first frame carries a populated `thread_id` (`019e9551`, == its window-id), structurally indistinguishable from a real thread, so it resolves to `019e9551` → an **isolated** phantom session (its own synth id; no rollout → no transcript via locate-miss). There is NO wrong-join risk (it never mis-joins the real `019e9553` session). The orch's "frame 1 → None" is not achievable at the parser (the real data contradicts the "only window-id" assumption). Recommendation: accept per §15 risk 2; suppression would need a fragile heuristic.
- **Final live confirmation — DONE (green @ 55754e2):** Stuart's codex re-run with the fix passed all three checks — codex `wire_exchange` rows correlated (only the frame-1 phantom NULL), `/api/index/sessions` non-empty with the codex session, `/diff` returns. HARD REQ #1 + the §7.2 convergence HARD GATE are proven end-to-end on a real run.
- **Sign-off:** author signed off on slice-5 as currently filed @ 55754e2; peer (`:3.2`) cleared all code gates via an independent probe + `just ci` 1103 and issues the clean sign-off on the green live proof. GATE (ci green) met; no PR (orch handles merge).
