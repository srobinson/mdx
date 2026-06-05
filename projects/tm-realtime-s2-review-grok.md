# Adversarial review — PR #263 / Slice 2 (grok family)

**PR:** https://github.com/srobinson/transport-matters/pull/263  
**Branch:** `realtime-slice2-vocab-reframer-folds` @ `843ebb4`  
**Base:** `main` (stacked after slice 1 `4361d36` / #262)  
**Tree:** pristine (`git status` clean; no local dirty; no writes by this review)  
**Spec:** `~/.mdx/projects/tm-realtime-spec.md` §2, §4.1–§4.2, §5.4–§5.5, §7 slice 2  
**Verdict: CLEAN** — 0 BLOCKER, 0 MAJOR, 0 MINOR

---

## Scope under review

| Path | Role |
|------|------|
| `api/src/transport_matters/live_status.py` | Live-fact vocab + Anthropic/Codex classifiers |
| `api/src/transport_matters/sse.py` | `IncrementalSseFrames` (byte tail) + shared `_sse_data_object` |
| `api/src/transport_matters/test_sse.py` / `test_live_status.py` | Proof suites |
| `api/src/transport_matters/session/live_status_contracts.py` | `RUN_LIVE_STATUS_KINDS = LIVE_STATUS_KINDS` (DRY) |
| `packages/activity/.../runActivityContext.ts` | Wire branches on `foldReasoning` / `foldGenerating` |
| `packages/activity/.../runActivityMachine.ts` | `WIRE_RETRACTED_TRANSITIONS` on reasoning + generating |
| `packages/activity/.../wireActivity.test.ts` + `machineTestEvents.ts` | §5.5 machine reds |

Not in PR (correct for dark slice 2): `LiveStatusObserver`, `on_chunk` tee hook, consumer `readLiveStatusForRun` / live `WireCandidate` arms, capture wiring.

---

## 1. Reframer framing (byte tail) — PASS

`IncrementalSseFrames` keeps `_tail: bytes` only; complete lines decode once via shared `_sse_data_object` (`json.loads(body.decode(errors="replace"))`). Chunk boundaries never decode mid-sequence into a string accumulator.

**Proof suite is non-tautological:**

| Test | Why it would fail if wrong |
|------|----------------------------|
| `test_incremental_sse_matches_whole_buffer_at_every_byte_boundary` | Body includes non-ASCII (`คิด`, `café`); every split + bytewise feed must equal `iter_sse_data_objects`. |
| Independent mutation probe | Naive string-tail (`chunk.decode` then concat) mismatched **7/148** splits on the same body; byte-tail **0** mismatches. |
| `..._emits_multiple_events_from_one_chunk` | Two complete frames in one feed. |
| `..._skips_done_and_malformed_json...` | `[DONE]` + broken JSON; subsequent intact event survives. |
| `..._retains_trailing_partial_bytes` | Splits Thai `สวัสดี` at mid-codepoint of `ว`; empty first feed, complete second. |
| `..._overflow_drops_record_then_resyncs` | Cap 32; oversized line discarded; next record recovered. |
| `..._rejects_non_positive_tail_cap` | Guard on constructor. |

`iter_sse_data_objects` remains whole-buffer for finalize paths (shared line parser only). Default cap `1 << 20` matches §4.1.

---

## 2. Reuse not reinvention — PASS

**Anthropic:** rules re-expressed incrementally (method cannot resume across chunks — matches §4.2). Event types and block/delta kinds mirror `_inbound_response_sse` / complete-block IR without calling `_parse_tool_use_block` (scout: complete-input only).

**Codex:** imports and uses `codex_payload_event_type`, `codex_terminal_status`, `CODEX_*` event/item constants, `codex_tool_call_key`, `CODEX_ANONYMOUS_ASSISTANT_ITEM_ID`. Open-item set is the live-status discipline from §2.2, not a third payload fold of `derive_codex_turn_incremental` (derivation owns text/args commits; live plane owns kind/current).

**SSE:** one `_sse_data_object` for incremental + whole-buffer.  
**Kinds:** contracts re-export `LIVE_STATUS_KINDS` (no parallel tuple).

---

## 3. Classification edges — PASS

| Edge | Evidence |
|------|----------|
| `redacted_thinking` → reasoning | `test_anthropic_classifies_block_starts` param; `_anthropic_start_state` |
| Delta heal missed start | thinking/input_json/text deltas → kind |
| Transition-only affirm | same-kind delta returns `None` |
| Batch coalesce stop→start | final generating; stop+same-kind suppressed |
| Codex multi open, no false global stop | tool done while reasoning open → affirm reasoning; later close of non-current item → `None`; stop only when open set empties |
| Tool item types | function_call / custom_tool_call / tool_search_call |
| Terminals clear open set | response.completed / failed with `terminal=True` |
| WS classifier server frames only | `from_client=True` → None, no state mutation; server then classifies |

Anthropic `content_block_stop` → `kind=None` per §2.1 (sequential block model; map is attribution for deltas, not concurrent multi-slot display).

---

## 4. TS fold / transition (blocker-1 fix) — PASS

**Folds** (`runActivityContext.ts`):

```ts
// foldReasoning / foldGenerating
const patch = { ...clearStalledFields(), status: "…" } as const;
if (eventStream(event) === "wire") return foldWireAsserted(context, event, patch);
return markApplied(context, event, { ...patch, lastActiveStatus: "…" });
```

`foldWireAsserted` stamps `wireAssertedExchangeId` only; never writes `lastActiveStatus` / `pendingToolCallIds`.

**Machine** (`runActivityMachine.ts`): `"wire.retracted": WIRE_RETRACTED_TRANSITIONS` on **reasoning** and **generating** (plus the prior four). Doc comments list the six wire-assertable states.

**Reds would die on the unamended code:**

1. Wire reasoning/generating after record `tool_use` — expects `lastActiveStatus === "running-tools"`, `pendingToolCallIds === ["tool-record"]`, `wireAssertedExchangeId` stamped. Old folds wrote `lastActiveStatus` via `markApplied` → fail.
2. live-reasoning / live-generating / live-tool → `wire.retracted` → restores record baseline and clears wire id. Without transitions, xstate drops the event → status stuck on live state → fail.

`isNewEvent` still short-circuits wire (no cursor advance). Double-assert idempotency re-pinned on `wireGenerating`.

---

## 5. Dark scope — PASS

No `on_chunk` / tee hook, no `LiveStatusObserver`, no producer/consumer admission, no live `WireCandidate` vocabulary arms. Machine changes are dark: only test builders mint wire reasoning/generating. Slice 1 store (`submit_run_live_status`) untouched by this PR’s logic beyond kind DRY.

---

## 6. DRY / sizing — PASS

| File | LOC | Limit |
|------|-----|-------|
| `live_status.py` | 355 | 700 |
| `sse.py` | 81 | 700 |
| `runActivityContext.ts` | 689 | 700 |
| `runActivityMachine.ts` | 641 | 700 |
| `writer.py` | 643 | not modified this PR |

No reinvented helpers beyond the intentional pure classifiers. Shared SSE parse path; shared kind constant; shared `WIRE_RETRACTED_TRANSITIONS` table; shared `wireSimpleRecord` test builder.

---

## Verification run (read-only)

```
cd api && pytest test_sse.py test_live_status.py  → 25 passed
pnpm --filter @tm/activity test                    → 203 passed, 22 skipped
string-tail vs byte-tail probe                     → 7 vs 0 mismatches
git status                                         → clean @ 843ebb4
```

---

## Issues

None.

## Residual (not defects)

- Slice 3 still owns emit seam, deferred-stop slot, subagent skip, abort terminal.
- Slice 4 still owns admission + reconnect.
- `runActivityContext.ts` at 689 is under the hard limit; watch on later edits.
