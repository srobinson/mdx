---
title: Plan — t3code P1 Slice 4g, continuation + idempotency on the gateway, with a canvas consumer (D3)
type: projects
tags: [transport-matters, t3code, p1, slice-4g, scout, plan, continuation, idempotency, canvas]
summary: Rebuilds the 4e-d-deleted continuation + idempotency on the post-cutover architecture and gives them a real canvas consumer. KEY RECOVERY FINDING — the old continuation NEVER produced resume argv; it built lineage metadata (parent_session_id, forked_at_seq, session_purpose=continuation, resume_context) threaded through launch_fields into the new session row. Parity therefore lands cleanly on the existing seams: continuation fields build Python-side in the prepare RPC (restore run_continuation.py verbatim), idempotency becomes a single-flight dedup map in the gateway RunManager (return-existing, process-lifetime — old parity), and the canvas consumer adds a Continue action with a client-minted idempotencyKey. Two Stuart decisions: the consumer UX (session-picker action vs ended-run relaunch) and whether "real CLI resume" (--resume argv) should ALSO be built — that would be NEW behavior beyond parity, not a port.
status: active
source: scout (fable 5:2.1), first-hand on main @ 7241fff; deleted code recovered from 84da72c
confidence: high
created: 2026-07-08
---

# Plan — Slice 4g: continuation + idempotency + consumer

Recovered sources: `git show 84da72c:api/src/transport_matters/api/v1/run_continuation.py`,
`.../run_routes.py::_launch_fields`, `.../run_manager.py::spawn` (idempotency),
and the deleted `test_run_routes.py` continuation cases (the behavioral contract).

---

## 1. Recovered semantics — the parity bar (Q1)

**Continuation was lineage metadata, NOT resume argv.** This corrects the
brief's premise. `build_continuation_launch_fields(pool, parent_session_id,
owner)`:

- Owner-scoped parent lookup (`AsyncSessionDao.get_session_for_owner`) —
  missing/foreign owner → 404 `session_not_found`, and NOTHING spawns.
- Builds `launch_fields`:
  `{continue_from_session_id, parent_session_id, forked_at_seq (latest turn
  seq — the fork point), session_purpose: "continuation", resume_context:
  {firstUserPrompt, lastAgentMessage, transcriptRef}}` (prompt/message pulled
  from the parent's first user / last assistant turns).
- Those fields flow through `CapturedRunRequest.launch_fields` →
  `captured_run_context` merge → the addon's `ProxyRunBinding.launch_fields` →
  `addon_runtime` stamps `parent_session_id` onto the NEW session row
  (`_string_launch_field(binding, "parent_session_id")`) — the lineage the
  session store renders. **No `--continue`/`--resume` flag was ever passed to
  either harness.** The continuation run is a fresh agent process whose session
  row knows its parent.
- Coupling rule: `continueFromSessionId` REQUIRES `idempotencyKey` (400
  otherwise); both reject empty strings.

**Idempotency (old `RunManager.spawn`):** a `dict[idempotencyKey → ManagedRun]`
guarded by a lock — the lock held ACROSS the spawn, so concurrent same-key
creates were single-flight; a hit returned the existing run (whatever its
state — never pruned, no TTL, process-lifetime); the key was recorded only
AFTER a successful spawn, so a failed create never poisoned the key (retries
spawn fresh). The old wire test: two identical POSTs → same `runId`, exactly
ONE capture prepare.

## 2. Where each lands (Q2)

### Continuation → the prepare RPC (Python stays the launch authority)

- **Restore `api/v1/run_continuation.py` verbatim** (a git revert of the 4e-d
  deletion — the module is self-contained over the session DAO).
- `PrepareCaptureRequest` gains `continueFromSessionId` (owner is already
  there since 4e-a). `capture_rpc_routes._resolved_domain_request` grows the
  continuation step beside worktree/template resolution: when present,
  `build_continuation_launch_fields(pool, parent, owner)` and MERGE into
  `domain.launch_fields` (caller-supplied fields win? old behavior: the route
  passed continuation fields AS the launch_fields and the Python RunManager
  merged runtime-home fields later — mirror by merging continuation fields
  UNDER any explicit launchFields the runtime sent). Errors:
  `ContinuationSessionNotFound` → 404 `session_not_found`; no pool → 503
  `session_store_unavailable` — both flow to the canvas intact via the C1
  upstreamStatus/upstreamCode plumbing (already live).
- The lineage lands on the session row through the UNCHANGED
  launch_fields→binding→addon path — no session-store changes.

### Idempotency → the gateway RunManager (TS)

`CreateManagedRunInput` gains `idempotencyKey?`; `RunManager.create` wraps in
a single-flight dedup: `Map<idempotencyKey, Promise<RuntimeRunView>>` — a hit
awaits/returns the same promise (concurrent double-submit collapses); on
rejection the key is deleted (failed create never poisons, old parity); on
success the entry resolves to views of the SAME run id thereafter (return
`getView(runId, owner)` freshness — return-existing-even-terminated, old
parity; note the view must be re-read per call so state is current, which the
old impl also did via the live ManagedRun). Process-lifetime, no TTL — runs
are process-resident anyway (CLAUDE.md), and this matches the deleted
behavior exactly. Owner guard: key hits are owner-scoped (key → {owner,
promise}; a different owner with the same key is treated as a distinct key —
the old map was implicitly single-owner; make it explicit).

Coupling rule enforced router-side for parity:
`continueFromSessionId` without `idempotencyKey` → 400 `invalid_request`
(mirrors the deleted `_launch_fields` requirement).

## 3. The canvas consumer (Q3) — D-g1, Stuart's UX call

Existing spawn path: `capturedRunStore.resolveRunId` → `createCapturedRun`
(with client-side in-flight dedup by `runKey` already). Existing session
surface: `SessionPickerPane` lists `SessionSummary` rows with per-row actions
(`spawnOrFocusTranscript`).

- **Option A (recommended): "Continue" on the session picker row.** Each
  session row gains a Continue action → spawns a captured run with
  `continueFromSessionId = session.sessionId`, same harness as the parent,
  and a client-minted `idempotencyKey` (`crypto.randomUUID()` minted once per
  spawn INTENT in the store, so the wire-level double-POST is deduped
  server-side while a deliberate user retry mints a fresh key). Opens the run
  pane exactly like a normal spawn. Session-centric — matches "continue a
  prior session" and reuses a surface that already exists.
- **Option B: relaunch from an ended run pane.** When a `CapturedRunPane`'s
  run reaches EXITED/TERMINATED, offer "Continue this conversation" using the
  pane's `sessionId`. Natural follow-up but only reaches sessions that ended
  in THIS canvas session; A covers the general case. Could ship as a 4g+1.

`transport.ts::createCapturedRun` already has 5 positional params; adding two
more argues for folding the trailing options into an options object
(`createCapturedRun(harness, worktreeId, {oscColorReplies, runtimeTemplate,
bypassPermissions, continueFromSessionId, idempotencyKey})`) — small
type-driven refactor of its ~2 call sites, done in this slice rather than
growing the positional list.

## 4. Contract threading + touch list (Q4)

canvas Continue action → `createCapturedRun(..., {continueFromSessionId,
idempotencyKey})` → POST /v1/runs (proxied) → `runtimeRouter` body
(`continueFromSessionId`, `idempotencyKey`, non-empty validation + coupling
400) → `RunManager.create` (dedup; prepare input gains
`continueFromSessionId`) → `CaptureRpcClient` body → `PrepareCaptureRequest`
→ continuation fields built + merged into `launch_fields` → session row
lineage (unchanged path).

| Area | Files |
| --- | --- |
| Python (restore + 2) | `api/v1/run_continuation.py` (verbatim restore); `api/v1/capture_rpc_routes.py` (field + build/merge + error mapping); tests: port the deleted DB contract test to the capture route (seed parent → prepare → assert the EXACT recovered launch_fields dict incl. `forked_at_seq` + `resume_context`; foreign owner → 404; no pool → 503) |
| TS runtime (4) | `ports.ts` (PrepareCaptureInput.continueFromSessionId; CreateManagedRunInput.continueFromSessionId/idempotencyKey); `service/RunManager.ts` (single-flight dedup map, owner-scoped, delete-on-reject); `server/runtimeRouter.ts` (body fields, coupling 400); `adapters/CaptureRpcClient.ts` (body passthrough) + suites |
| Canvas (3–4) | `core/src/transport.ts` (options-object refactor + 2 fields); `canvas/src/model/capturedRunStore.ts` (thread continuation + mint idempotencyKey per intent); `SessionPickerPane.tsx` (Option A action) or `CapturedRunPane.tsx` (Option B) + tests |

~10 touches + 1 restored file.

**Test plan:** (1) Python capture-route continuation contract (the ported DB
test — dict-equality on launch_fields is the parity proof); (2) TS: double
create same key → same runId + ONE prepareCapture; CONCURRENT double-create →
single spawn (single-flight); failed prepare → key not poisoned (retry
spawns); terminated-run key hit still returns the run (old parity);
continuation-without-key → 400; passthrough to prepare body asserted; (3)
canvas: Continue action posts continueFromSessionId + a stable key per
intent, double-click → one POST; (4) proxy e2e optional (the seams are all
individually proven; the origin-contract harness covers the route shape).

## 5. Risks / decisions

- **D-g1 (Stuart, UX):** Option A vs B above (recommend A; B as follow-up).
- **D-g2 (Stuart, scope):** the brief assumed continuation = CLI resume argv.
  The recovered truth: it never was — it is lineage metadata on a FRESH run.
  Parity (this plan) restores exactly that. If Stuart wants REAL harness
  resume (`claude --resume <native id>` / codex equivalent), that is NEW
  behavior with its own design (native-id mapping, per-harness argv in
  `captured_claude/codex`, what "resume" means for a captured proxy session)
  — recommend a separate slice decision, not silently folded into a "port".
- Idempotency lifetime = process, no TTL, return-existing-even-terminated —
  deliberate old-parity; revisit only if a consumer needs retry-after-exit
  semantics (the canvas retry mints a fresh key, so it does not).
- Blast radius: create-path only; no session-store schema or addon changes;
  the launch_fields merge must not clobber runtime-template fields
  (`captured_run_context` already merges template fields OVER request
  launch_fields — preserved by construction, asserted in the Python test).
