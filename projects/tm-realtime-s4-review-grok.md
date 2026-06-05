# Adversarial review: PR #265 Slice 4 (realtime-slice4-consumer-admission)

**Reviewer:** grok (`transport-matters:general:1:2.3`)  
**PR:** https://github.com/littleorgans/transport-matters/pull/265  
**Branch:** `realtime-slice4-consumer-admission` @ `a5331d3`  
**Tree:** pristine (`git status` clean; no local writes by reviewer)  
**Spec:** `~/.mdx/projects/tm-realtime-spec.md` §3.3, §5.1–§5.5, Slice 4 plan row  
**Verdict:** **CLEAN** — 0 BLOCKER / 0 MAJOR / 0 MINOR

Scope: adversarial READ-ONLY check of the CONSUMER admission that makes live states OBSERVABLE end-to-end. One of two independent reviewers; no coordination. PR commits only (vs slice 3 tip `bcfb48d`): `ba7e1a4` (event vocabulary split) + `a5331d3` (live admission). All under `packages/activity/**` — no producer/store Python changes in this slice.

---

## 1. Liveness end-to-end — PASS

PR-3's defect was finalize-only wire assert (`readWireSnapshotForRun` needs a committed response). Slice 4 closes that gap:

1. `ActivityStore.readLiveStatusForRun` → `PostgresActivityReader` + pinned `LIVE_STATUS_BY_RUN_SQL` (columns: `run_id`, `seq`, `kind`, `tool_call_id`, `ts` only; no generation on the DTO — fence stays capture-plane).
2. `liveCandidateFromRow` maps non-null kinds to `live-reasoning` / `live-running-tool` / `live-generating` with `assertId = live:{runId}:{seq}`.
3. `reconcileWireSnapshot` reads **both** planes every pass; prefers a non-null live candidate over finalize (`liveCandidate ?? finalizeCandidate`). Under the generation fence a non-null live kind means the open generation still has an active block; finalize authority is construction (close nulls the row in the same txn as `wire_exchange` insert), not clock.
4. `wireCandidateEvent` mints existing `record.reasoning` / `record.tool_use` / `record.generating` with `stream: "wire"`, `seq: 0`, `wireExchangeId` from `candidateAssertKey`.
5. Payload: identity-only `run_live_status` NOTIFY via `parseTmEventsPayload` → same "run X needs reconcile" path as other flavors.

**Evidence that movement is mid-turn, not finalize-shaped:**

| Test | What it proves |
|------|----------------|
| `wireIngestion` "admits a live $kind fact mid-turn as $expected" | Fake store with **only** lifecycle + live row (no wire snapshot) → machine `reasoning` / `generating` / `running-tools` with `wireAssertedExchangeId = live:…` |
| `pgWireIntegration` **T13** | Real PG + LISTEN: upsert `reasoning`→`generating`→`running_tool`→`null` with NOTIFY; projection moves Thinking→Responding→Tools→starting **before any finalize** |
| `pgWireIntegration` **T14** | Live tool→generating, then closed+null + wire ask → `needs-you-asked`; new generation reopens and admits `live:…:3` |

No frontend change required: projection → existing SSE → `runVitalsStore` path is unchanged; mid-turn status is an ordinary delta.

---

## 2. Admit-once / no flap — PASS

Two independent guards, both load-bearing:

1. **Same-assert-standing no-op** (`reconcileWireSnapshot`): if `candidateAssertKey(candidate) === context.wireAssertedExchangeId`, return without send (no re-assert, no stall-timer reenter).
2. **Admit-once** (`wireCandidateAdmitted` + `entry.lastLiveAssertId`): live `assertId` admitted at most once; tracked on process-local `RunIngestionEntry`, not machine context (survives record supersession that clears `wireAssertedExchangeId`).

`isNewEvent` remains unconditionally true for the wire stream; without admit-once, re-derive+re-send would flap after every record pass.

**Tests:**
- Domain: "admits each live fact once and requires a new assert id for re-admission"
- Service: "does not re-enter a standing live assertion when the row is unchanged" (clock +10min → stall timer not reset; second pass no extra `wireAdmitted`)
- Integration T11 still holds for finalize double-assert; live path covered by unit tests above

**Mutation probe (scratch only, no repo write):** remove the once-guard line
`if ("assertId" in candidate && candidate.assertId === lastLiveAssertId) return false`.
- Domain once-test goes RED (second admit returns true).
- Same-assert-standing alone still protects while ownership stands, but **Esc path fails**: transcript-error clears `wireAssertedExchangeId` on status change; without admit-once the still-non-null live generating row re-admits → sticky Responding. Admit-once is the causal consumer anchor for that handoff.

Generation is the **store fence** (capture plane, S1); seq-derived `assertId` is the **consumer admit key** (spec §5.2). No timestamp adjudication anywhere between planes.

---

## 3. Retract + handoff — PASS

Block-stop / terminal / abort → `kind = null` → `liveCandidateFromRow` returns null → if finalize also empty, trailing `wireRetractedEvent` → `statusAfterWireRetraction` from record-owned fields only (`pendingToolCallIds` / `lastActiveStatus`).

| Path | Test |
|------|------|
| Block stop → record baseline | `wireIngestion` "retracts a block stop to the record-owned baseline" (generating → reasoning after turn-open; wire id null) |
| Stop vs finalize order | "converges to finalize whether stop or the wire snapshot is observed first" — both interleavings → `needs-you-asked` |
| Closed generation handoff | T14: closed+null live + wire ask → finalize assert; next turn new generation admits fresh live |
| Esc-mid-response | "never re-admits a stale generating row after an Esc interrupt journals" — transcript-error → stalled; re-reconcile with stale live generating still present stays stalled, wire id null |

Abort terminal (slice 3 `kind=null`) is the same retract arm as block stop. Esc without a cleared live row is bounded by admit-once after the interrupt journal; lost abort without journal remains silence-stall recoverable (ephemeral-overlay posture; process-local once memory).

---

## 4. Reconnect relist — PASS

`ActivityIngestion.handleConnected`: `reconcileMaterialized()` **plus** `connectedListeners`.  
`WorkspaceActivityProjections` constructor: `subscribeConnected(() => refreshAllSubscribedWorkspaces())` → `listWorkspaceActivity` for every active owner/workspace key (store discovery, not only already-materialized actors).

**Test:** `workspaceActivity` "re-lists subscribed workspaces on reconnect when lifecycle and live NOTIFYs both dropped" — empty index first, then runs appear only via `onConnected`; projection `generating` from live row, `isMaterialized` true. No per-run doorbell delivered.

---

## 5. Non-pollution preserved — PASS

- Live kinds mint through `wireCandidateEvent` → existing folds; `foldReasoning` / `foldGenerating` / `foldToolUse` wire branch → `foldWireAsserted` (status + `wireAssertedExchangeId` only; **never** `lastActiveStatus` / `pendingToolCallIds`).
- Wire events do not advance `entry.watermark` (`isNewEvent` short-circuit for stream wire; watermark only in record batch).
- Domain tests: foldWireAsserted baseline preservation for live-reasoning / live-generating assert ids; retract restores record baseline.
- Stale/refused live fact: refuse path or retract; cannot write durable record-owned fields.

---

## 6. Refactor (runActivityContext split) — PASS

| | LOC |
|--|-----|
| Before `ba7e1a4` | `runActivityContext.ts` **689** |
| After | **606** + new `runActivityEvent.ts` **128** |

Commit is move-only for the event alphabet (types + `launchKinds`); folds/context unchanged. Public surface stable via re-exports from `runActivityContext` and `domain/index` (package root adds only the intentional new `candidateAssertKey` export).

---

## 7. Scope / DRY / sizing — PASS

- **PR file set:** activity package only (contracts, adapters, domain, service, projections, pg harness/tests). No Python producer, no migration, no gated-state creep.
- **Reuse:** `wireCandidateEvent` / `foldWireAsserted` / S2 retract transitions; `runPayloadIdentity` for live doorbell; existing reconcile order (records → wire → exit).
- **Sizes:** all touched modules under 700 (`runActivityContext` 606, `postgresRecords` 558, `activityIngestion` 327, `workspaceActivity` 322, `wireCandidate` 112).
- **DTO discipline:** `ts` for candidate/event/retract stamps only; never plane adjudication.

---

## Verification run (this review)

```
pnpm --filter @tm/activity test     → 219 passed, 24 skipped (unit; pg skipped without env)
pnpm --filter @tm/activity typecheck → clean
TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres \
  vitest run src/pgWireIntegration.test.ts src/pgIntegration.test.ts
  → 23 passed (incl. T13 mid-turn live projection, T14 handoff)
pnpm --filter @tm/shell test        → 1207 passed
git status                          → clean @ a5331d3
```

---

## Residual notes (not filed)

None material. Consumer correctly trusts the generation fence rather than re-implementing close semantics; unit test "snapshot-first" intermediate (live still wins while non-null) is consistent with that design and with T14's closed-row handoff under real storage.

---

## Verdict

**CLEAN.** Mid-turn live admission is real (T13 + unit mid-turn suite), admit-once stops re-assert flap including after Esc/record supersession (mutation-probed), retract and finalize handoff converge, reconnect relists from store, non-pollution and sizing hold, producer plane untouched.
