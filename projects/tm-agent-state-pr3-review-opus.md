# PR #260 review — PR-3 wire-driven agent state (code)

**Branch:** `agent-state-pr3-wire-activity` · **head:** `342bc57` · **base:** `main`
**Reviewer:** Opus 4.8 (contract-weight, read-only) · **CI:** 9/9 green · **tree:** pristine (`git status --porcelain` empty at `342bc57`)
**Spec:** `~/.mdx/projects/tm-agent-state-spec-pr3.md` · **Lenses:** code-review (8 angle) + code-hygiene · **Emphasis:** adversarial state-machine interleavings

## Verdict

**Signoff with one MEDIUM and three LOW notes.** The causal-resolution admission, baseline preservation,
and retraction wiring faithfully implement the spec; I could not find an interleaving that strands a
reachable run or double-applies. The MEDIUM is a live/replay `sinceTs` divergence from a wall-clock
timestamp in the retraction path; the rest are latent/hygiene.

## Brief verification (1–4)

| Ask | Result | Evidence |
|---|---|---|
| (1) `wire.retracted` + `wireAssertedExchangeId` cannot strand or double-apply | PASS (reachable states) | `runActivityMachine.ts` attaches `WIRE_RETRACTED_TRANSITIONS` to exactly the four wire-assertable states (`running-tools`, `needs-you-asked`, `idle`, `stalled`) and nowhere else; the six guards cover every reachable restore target of `statusAfterWireRetraction` (`starting/reasoning/generating/running-tools/idle/needs-you-asked`). Double-apply is idempotent: `markApplied` stamps `sinceTs` only when `nextStatus !== context.status`, so a re-admitted ask leaves `sinceTs` unmoved (T11). One latent gap: `needs-you-gated` (see LOW-1). |
| (2a) asked → answer(`tool_result`) leaves asked promptly | PASS | `foldToolResult` sets `status = lastActiveStatus` (transcript baseline, never the wire status since wire folds don't write `lastActiveStatus`); the status change makes `markApplied` clear `wireAssertedExchangeId` (non-wire event changed status). Next reconcile re-derives `asked(X)`, `X ∈ resolvedToolCallIds` → refused, and ownership already null → no retraction. |
| (2b) asked → `wire_exchange_deleted` retracts | PASS | Deleted row → snapshot null → candidate null → `reconcileWireSnapshot` sees `wireAssertedExchangeId !== null` → sends `wireRetractedEvent`; `foldWireRetracted` restores `statusAfterWireRetraction` and nulls ownership. |
| (2c) two empty reconciles after answer → no re-assert (E6) | PASS | `resolvedToolCallIds` is context state rebuilt by replay, not batch state; every subsequent pass re-derives `asked(X)` and `wireCandidateAdmitted` refuses on `resolvedToolCallIds.has(X)`. No timestamp equality to exploit. |
| (3) delayed/out-of-order write for a resolved id refused (E3/E4) | PASS | `wireCandidateAdmitted` keys purely on `resolvedToolCallIds` (asked/running-tools) and `recordSessionId === null` (idle/anomaly); no clock or cursor participates, so commit order is irrelevant. |
| (4) idle/anomaly cannot false-fire outside cold start | PASS (see LOW-2 for the running-tools analogue) | `wireCandidateAdmitted` gates `idle`/`anomaly` on `context.recordSessionId === null`; any applied record refuses them. |

## Findings

### MEDIUM 1 (correctness / replay-safety) — `service/activityIngestion.ts` `reconcileWireSnapshot`
The retraction event is minted with a wall-clock stamp: `actor.send(wireRetractedEvent(new Date().toISOString()))`.
Two problems. (a) It bypasses the injected clock the class already holds (`this.clock`, wired to the actor at
construction) — every other time source in this service is the `Clock` port, and tests use `SimulatedClock`;
`new Date()` here is non-deterministic and unmockable. (b) It breaks the `sinceTs` "data-derived, replay-safe"
invariant (`runActivityContext.ts` field comment). When retraction changes status (the common
`needs-you-asked → reasoning` case), `markApplied` stamps `sinceTs = event.ts = wall-clock now`. On a fresh
replay the deleted row is absent, so no retraction fires and the restored status carries the transcript's own
`sinceTs`. Live and replay therefore diverge: the user sees "reasoning since \<retraction-instant\>" live vs
"reasoning since \<original-reasoning-ts\>" on reload — precisely the drift spec T10(a)'s "EXACTLY the pre-wire
transcript state … transcript-derived `since_ts` semantics" forbids. **Fix:** derive the ts from record-stream
data, e.g. `wireRetractedEvent(context.lastEventTs ?? this.clock…)`, so the restored `sinceTs` equals what
replay produces.

### LOW 1 (latent, altitude) — `domain/runActivityMachine.ts` `WIRE_RETRACTED_TRANSITIONS`
`statusAfterWireRetraction` returns `lastActiveStatus`, typed `ActiveActivityStatus`, which includes
`needs-you-gated`; the transition set has no `retractionRestoresGated` entry (and the machine has no
`needs-you-gated` state). Unreachable today — no fold sets `lastActiveStatus = needs-you-gated`, per the
in-file note that gate detection is a later slice — but when gate detection lands, a retraction from a
gated baseline would match no transition, xstate would drop the event, and the run would strand
wire-owned with `wireAssertedExchangeId` never cleared. Worth a guard or an explicit exhaustiveness
assert now so the future slice fails loud, not silent.

### LOW 2 (correctness, defensive gap) — `service/runActivityEvents.ts` `wireCandidateFromSnapshot` + `domain/wireCandidate.ts` `wireCandidateAdmitted`
Priority-2 `running-tools` builds `toolCallIds` by filtering out null `tool_use_id`s; if every tool_use
block on the exchange has a null id, the list is empty and `toolCallIds.every(...)` is vacuously `true`,
so the candidate is admitted unconditionally — NOT cold-start gated, unlike idle/anomaly which face the
same "no cross-plane anchor" situation. A late/stale wire row whose tool_use blocks lack ids would then
assert `running-tools` despite transcript ownership. Not reachable with well-formed provider data
(`wire_store._insert_response_blocks` writes `block.id` for every `ToolUseBlock`; Claude/Codex always
carry ids), so severity is LOW, but the guard is vacuous by construction. **Fix:** treat empty
`toolCallIds` as inadmissible (fall through to idle, or require ≥1 id) so the resolution guard is never bypassed.

### LOW 3 (simplification) — `service/activityIngestion.ts` `reconcileWireSnapshot`
`actor.getSnapshot()` is read twice (`.context.status` guard, then `const context`). One read into a local
`const snapshotState = actor.getSnapshot()` suffices; minor.

## Hygiene (code-hygiene lens)

- **File sizes:** `runActivityContext.ts` 675 (+150, approaching the 700 guardrail — the wire additions are the
  clean seam if it crosses: `foldWireAsserted`/`statusAfterWireRetraction`/`foldWireRetracted`/
  `withResolvedToolCallId` form a cohesive "wire fold" cluster that could move to a `wireFold.ts` sibling
  importing the shared markApplied primitives). `runActivityMachine.ts` 636, `postgresRecords.ts` 509 — under guardrail.
- **DRY honored well:** `askToolNames`/`isAskToolName`/`REFUSAL_STOP_REASON`/`REFUSED_TURN_REASON` are extracted
  once in `harnessRegistry.ts` and consumed by both `transcriptRecords.ts` and `runActivityEvents.ts` — no third
  copy, exactly as spec §2 required. The 4× `if (eventStream(event) === "wire") return foldWireAsserted(...)`
  fold-heads are spec-sanctioned (§1 step 7 "each status fold gains a one-line head") and differ by status
  patch; acceptable, not worth a helper.
- **Boundaries clean:** `wireCandidate.ts` (domain) owns the pure admission contract and imports no ports;
  the snapshot→candidate mapping lives in `service/runActivityEvents.ts` (needs the reader DTO + harness vocab);
  the reader SQL is subagent-excluded at the DB level (E8). Discriminator-first `eventStream` keeps wire events
  out of the record cursor space as designed.

## Acceptance (spec §3/§6)
- Baseline preservation (wire never writes `lastActiveStatus`/`pendingToolCallIds`) — met (`foldWireAsserted`).
- Retraction recompute-not-retain (`statusAfterWireRetraction` over record-owned fields) — met.
- Cold-start gate for idle/anomaly; resolution-set gate for asked/running-tools — met (MEDIUM/LOW-2 aside).
- `wire.retracted` on the four wire-assertable states, cursor-less wire stream — met.
