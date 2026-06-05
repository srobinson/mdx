---
title: TM realtime design-spec adversarial review (Grok)
type: design-review
tags: [transport-matters, activity, realtime, adversarial-review]
summary: Conditional on the live wire-status design spec; blockers on wire.retracted coverage, fold non-pollution, and live-vs-finalize freshness.
status: active
source: grok
confidence: high
created: 2026-07-10
base_commit: ef52af6
spec: ~/.mdx/projects/tm-realtime-spec.md
---

# Adversarial review: `tm-realtime-spec.md`

Tree verified pristine at `main` `ef52af6` before reading. Spec + both scout maps
read; claims checked against source (file + symbol). Findings ranked by blast
radius within each severity band.

## Verdict

**Conditional.** Plane-crossing decision B (ephemeral `run_live_status` + doorbell
`tm_events`) and the capture-side tee/reframer shape are sound. The product-plane
admission/retract story as filed cannot deliver mid-turn block-stop or non-pollution
on the two live states that matter (Thinking / Responding). Three blockers must be
resolved in the spec before implementation.

## Findings

### BLOCKER

[BLOCKER] #3,#1 `packages/activity/src/domain/runActivityMachine.ts`
`WIRE_RETRACTED_TRANSITIONS` + `reasoning` / `generating` state tables — Block-stop
→ `wire.retracted` is dead on the states live work occupies.

Evidence: `WIRE_RETRACTED_TRANSITIONS` is documented as shared by "exactly the
wire-assertable states (needs-you-asked, running-tools, idle, stalled)". Those four
states register `"wire.retracted"`; **`reasoning` and `generating` do not**. PR-3
never wire-asserted into those two states. Spec §5.3 claims stop/terminal with
`kind = null` yields no candidate and the trailing branch sends
`wireRetractedEvent`, then `statusAfterWireRetraction` recomputes. In xstate an
unhandled event is dropped: after a live assert transitions the machine to
`reasoning` or `generating`, the service can send `wire.retracted` and the actor
will ignore it, leaving status and any `wireAssertedExchangeId` stuck. That is the
Thinking→gap and Responding→gap path, i.e. the product.

Why it matters: without retract from active-work states, mid-turn block stop cannot
clear Thinking/Responding; the design reintroduces a stuck-status failure mode on
the exact states it exists to animate.

Required fix (spec must state): add `WIRE_RETRACTED_TRANSITIONS` to `reasoning` and
`generating` (and decide whether `starting` needs it if live can assert pre
turn-open). Slice 4 gates must include red tests: live-reasoning then stop
retracts; live-generating then stop retracts; live-tool then stop retracts.

---

[BLOCKER] #3 `packages/activity/src/domain/runActivityContext.ts`
`foldReasoning` / `foldGenerating` vs §5.4 "exact reuse" of `foldWireAsserted` —
Live reasoning/generating would pollute record-owned baseline.

Evidence: Spec §5.4 maps `live-reasoning → record.reasoning` and
`live-generating → record.generating` with `stream: "wire"` and claims folds route
through `foldWireAsserted`, which never writes `lastActiveStatus` /
`pendingToolCallIds`. Code contradicts that for these two folds:

- `foldReasoning` always `markApplied`s with `lastActiveStatus: "reasoning"` (no
  `eventStream` branch, no `foldWireAsserted`).
- `foldGenerating` always writes `lastActiveStatus: "generating"`.
- Wire-aware folds exist only for `foldToolUse`, `foldTurnIdle`,
  `foldQuestionAsked`, `foldTranscriptError` — matching PR-3's end-of-turn
  candidates only.

Consequence if implemented as written: a live Thinking/Responding assert rewrites
`lastActiveStatus`. Even after machine retract is fixed, `statusAfterWireRetraction`
returns the polluted baseline (e.g. stays `reasoning` after stop). Also
`foldReasoning` does not stamp `wireAssertedExchangeId` from `event.wireExchangeId`,
so §5.3's `context.wireAssertedExchangeId !== null` retract guard never arms for
these events.

Why it matters: non-pollution is load-bearing for retraction correctness; the
"verbatim PR-3 reuse" claim is false for the two primary live kinds.

Required fix: mirror `foldToolUse`'s wire branch in `foldReasoning` and
`foldGenerating` (or mint dedicated wire events that only call `foldWireAsserted`).
Named red tests in slice 4: wire reasoning/generating leave
`lastActiveStatus`/`pendingToolCallIds` unchanged; double-assert idempotent;
retract restores pre-live baseline.

---

[BLOCKER] #1,#2 Spec §5.3 live-vs-finalize freshness
`live.ts > snapshot.ts` — Wrong clock against Claude's primary wire `ts`.

Evidence: Claude finalize is provisional (`_finalize_http_provisional_exchange` in
`exchange_recorder.py`): `IndexEntry.ts` is minted at provisional **request** time
and **preserved** through finalize (`existing_entry.ts` passed to emit/wire write).
`WireExchangeSnapshot.ts` is that column (`postgresRecords.readWireSnapshotForRun`).
Live facts use emitter classification time during the response stream, which is
**always later** than request-provisional `ts`.

So after finalize, a still-non-null live row (missed/dropped stop or terminal, or
reconcile racing ahead of the kind=null upsert) **keeps winning** over the finalize
snapshot indefinitely under `live.ts > snapshot.ts`. Spec §5.3 calls a live row
"spent" when dated at or before the latest finalized exchange; under provisional
semantics that predicate almost never holds while `kind` is non-null.

Why it matters: end-of-turn handoff to the lossless finalize plane is not
guaranteed; a best-effort live overlay can shadow durable idle/running-tools/asked
outcomes — the inverse of PR-3's "finalize is truth" posture, and a liveness win
that breaks correctness after the turn.

Required fix: do not compare emitter `live.ts` to exchange `ts`. Prefer one of:
(a) live admits only when **no** finalized snapshot exists for the run (or for the
current open turn once that is named); finalize always wins once present; or
(b) compare store write times (`run_live_status.updated_at` vs
`wire_exchange.created_at`); or
(c) explicit live generation / exchange_id binding cleared on finalize.
Red-test: provisional-path finalize with stale live non-null kind must not keep
Thinking/Responding after an idle/tools/asked finalize candidate exists.

### MAJOR

[MAJOR] #1,#9 Spec §5.3 / slice-4 tests — Stop/terminal race with latest-wins slot
not named as a gate.

Even with a correct freshness rule, reconcile can observe a pre-stop live row if
the kind=null write is still in flight while the wire finalize NOTIFY lands (or the
reverse). Spec's latest-wins slot is correct for intermediate facts but does not
state ordering between terminal live clear and finalize, nor require a test that
both orders converge to the same machine state.

Why it matters: flaky post-turn vitals under load; the 35s Thinking bug morphs into
intermittent post-turn lag.

---

[MAJOR] #5 Spec §2.2 Codex mapping — `response.output_item.done` → global stop.

Codex can interleave multiple open items (reasoning, function_call, text). Mapping
any `output_item.done` to `kind = None` clears the whole run's live status when one
item ends while another remains active. Scout/`derive_codex_turn_incremental`
maintains multi-open state; the live classifier as specified is single-slot.

Why it matters: Tools can flash idle mid-turn while another tool or text is still
open; false retract thrash if retract is fixed.

Required: track open item set (or reuse derivation open-tool/text state) and emit
stop only when the open set empties / terminal events fire.

---

[MAJOR] #9 Slice 4 gates — Missing failure modes for the three blockers above.

Named gates cover stop→retraction and live-vs-finalize freshness only as slogans.
They do not pin: (1) retract transitions on reasoning/generating, (2)
foldReasoning/foldGenerating wire non-pollution, (3) provisional `ts` vs live
handoff. Without those reds, slice 4 can land green while product-broken.

### MINOR

[MINOR] #3 Spec §5.2 — `wireAssertSuppressedBySilenceStall` "unchanged over
assertId".

Current helper compares `candidate.exchangeId` only. Live variants are specified
with `assertId`, not `exchangeId`. Implementers must extend the candidate type or
the helper; "unchanged" is imprecise. Low blast radius once typed.

---

[MINOR] #4 Spec §4.3 — Live upsert requires NOT NULL workspace/owner; binding can
omit workspace (`WireStoreObserver._resolve_run` returns null slugs).

Spec should state: skip schedule when identity incomplete (same best-effort
posture as wire notify), so a hard NOT NULL constraint cannot throw into the writer
path under partial binding.

---

[MINOR] #7 Spec §6.2 — `PRIMARY_SESSION_FILTER` vacuous-true claim under LEFT JOIN.

Verified: with all `s.*` NULL, the `NOT EXISTS` parent-session subquery matches
nothing and lifecycle-only rows survive. Owner `COALESCE(s.owner, l.owner) = $3`
and lifecycle `owner DEFAULT 'local'` match source (`SessionRow.owner`,
`CapturedRunRequest` has no owner, `RunLifecycleEventRow` has no owner today).
No defect; optional extra gate: multi-primary-session run still one GROUP BY row
(already true).

---

[MINOR] #6 Reuse — No reinvent of ExchangeSink, `iter_sse_data_objects` (finalize),
or Activity SSE/projections. Incremental reframer is correctly new.
`derive_codex_turn_incremental` is cited as precedent but not reused; acceptable if
Codex open-set issue (MAJOR above) is fixed without a third fold.

---

[MINOR] #8 Scope — Stays on live active-work + Starting; asked/needs_you and gated
explicitly out. OK.

---

[MINOR] #4 Frozen plane — `on_chunk` try/except, exact chunk return, composition-level
`LiveStatusObserver` (mirrors `WireStoreObserver`), storage↛session Import DAG,
ExchangeSink final-only by non-use: sound as written. Slice 3 red list is adequate
for the tee seam itself.

## What is solid (no finding)

- Decision B preserves doorbell-only NOTIFY if commit+notify share one transaction
  like `submit_wire_exchange` / `_commit_run_lifecycle_event` (same-connection
  `pg_notify` inside the transaction). Payload identity-only matches
  `workspaceIdFromPayload` (slug+hash) and existing `parseTmEventsPayload` style.
- Reconnect via `onConnected → reconcileMaterialized` still heals dropped NOTIFYs
  **if** the store row is the truth and admission does not permanently prefer a
  stale live overlay (see freshness BLOCKER).
- Capture emit off `capture_chunk` / Codex WS is genuinely mid-stream, not
  finalize-shaped; PR-3's `readWireSnapshotForRun` / `response_id IS NOT NULL` lag
  diagnosis is correct.
- Empty-at-spawn owner resolution (lifecycle column + LEFT JOIN + COALESCE) is
  the right minimal SQL shape given no capture-plane owner fact today.
- Slice plan (dark store → pure → producer → consumer → empty-at-spawn) is
  independently landable **after** the product-plane blockers are written into
  slice 4 (and machine retract into the same slice).

## Criterion scorecard

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Liveness mid-turn | Emit path yes; admission/retract/handoff no (blockers) |
| 2 | NOTIFY doorbell invariant | Structure yes; stale-live shadow breaks "store truth" intent |
| 3 | Non-pollution | Fail as filed (`foldReasoning`/`foldGenerating` + retract table) |
| 4 | Frozen plane | Pass as designed |
| 5 | SSE reframer + mappings | Anthropic OK; Codex open-set MAJOR |
| 6 | Reuse | Pass (with Codex note) |
| 7 | Empty-at-spawn | Pass |
| 8 | Scope | Pass |
| 9 | Slices + tests | Structure OK; missing reds for blockers |

## Sign-off line (for orchestrator)

`conditional: 3 blockers / 3 majors / 5 minors ~/.mdx/projects/tm-realtime-review-grok.md`
