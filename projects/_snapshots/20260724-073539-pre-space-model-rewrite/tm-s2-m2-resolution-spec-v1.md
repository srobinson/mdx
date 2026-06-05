# S2 M2 resolution — design + build spec v2

Status: build-ready, tests-first. Resolves M2 (design-shaped after 3 patch rounds) + folds in m1.
Date: 2026-07-23
Baseline: worktree @ `09dbc291`.
Sources: codex re-verify notes `~/.mdx/projects/tm-s2-fix-reverify-gpt.md` +
`tm-s2-claims-leases-round2-reverify-gpt.md`; **codex pressure-test
`tm-s2-m2-resolution-spec-v1-pressure-test-gpt.md` (7 required revisions, all incorporated in v2)**;
spec `tm-s2-claims-leases-spec-v1.md`; model `019f8a57`.
Owner ruling (Stuart): fix the synchronous bug + add a reconciler now; defer only the
forced-delete-racing-cancel interaction to S4/S6.
Governing: `CLAUDE.md` (refactor-before-add over 700; no fn >150; DRY), `TLDR.md` (no legacy).

**v2 hardening (pressure-test):** bind is a compare-and-set that rejects a cancelling claim (closes
schedule-3); cleanup confirmation spans process + PTY + capture, and any failure keeps the claim
non-terminal; failed capture-cleanup retains a retryable handle; the reconciler fences a claim before
cleanup; `terminating` desired-state outranks liveness; a durable **creation deadline** owns the whole
create interval; startup reaps by **process epoch** before any new claim. Core shape (state model +
reconciler) unchanged — these are hardening invariants.

## 0. Problem — M2 is two problems, not one patch

The "closed" termination receipt can precede the cleanup of prepared/spawned external work. Codex
proved two schedules of the same class survive three patch rounds:

- **Stale-snapshot race:** `RunTerminationCoordinator._force_resource` decides terminate-vs-skip from
  the inventory snapshot's `resource.run_id`. If `bind_run_id` commits in the gap, it skips
  terminating a now-bound live resource and returns `closed`.
- **Close-before-cleanup:** the `closed` receipt derives from a best-effort durable release
  (`rejectCancelledClaim.releaseResourceBestEffort` wakes the waiter **before**
  `releasePreparedCaptureForCreateError` runs). A failed `releaseCapture` leaves external work without
  its durable guard.

The pressure-test surfaced a third schedule the locked-read alone does not close:

- **Schedule-3 (late bind):** cancellation locks a null-running claim, sets `cancel_requested`, chooses
  `terminating`, and commits. A `bind_run_id` then commits **after** the lock releases, publishing a
  bound live resource **after** the decision that skipped termination. The lock does not help because
  the coordinator's decision happens after the transaction releases it. Closed by making bind a
  compare-and-set that rejects a cancelling claim (§2).

Round-2 conclusion (correct): **a durable "closed" strictly-after-cleanup cannot be guaranteed
synchronously** — best-effort cleanup fails, and a crash interrupts any step. So M2 = a synchronous
tightening **plus** the correct primitive: a **claim reconciler**. Fold in **m1** (Git-unavailable must
fail closed). The forced-delete-racing-cancel residual is **deferred to S4/S6** (§6).

## 1. STEP 0 — mandatory behavior-preserving split (own commit)

`space/runtime_claims.py` is **exactly 700** (ceiling). The fix + reconciler will cross it. Split
first, zero behavior change, existing suite green:

- **`space/runtime_claim_models.py` (new):** move the enums, Pydantic models, and row/stamp helpers
  (`RuntimeResourceKind`, `RuntimeResourceState`, `PreallocatedRuntimeIdentity`, the stamp models,
  `RuntimeResourceClaim`/`View`/`Query`, `WorktreeLease`, `TERMINAL_RESOURCE_STATES`,
  `affinity_stamp_from_launch_fields`, `session_affinity_fields`, `_claim_from_row`, `_lease_from_row`)
  — ~140 LOC out of `runtime_claims.py`, leaving the `RuntimeClaimStore` with headroom.
- **`space/runtime_reconciler.py` (new):** the reconciler (§4) — new code, not a split.

If, after the synchronous fix, `RuntimeClaimStore` still approaches 700, further extract the lease ops
(`acquire_lease`/`release_lease`/`heartbeat_lease`/`heartbeat_resource`/`get_lease`/
`reap_expired_leases`) into `space/runtime_leases.py`. Prefer the models-extraction first (least
coupling; cancellation touches both claim + lease atomically). `space/store.py` (693) is untouched
(S4's STEP 0).

## 2. Synchronous fix A — decide under the claim lock, never from a snapshot

`RunTerminationCoordinator._force_resource` (`controlplane/run_termination.py`) must NOT branch on
`resource.run_id` (the inventory snapshot). `RuntimeClaimStore.begin_resource_cancellation`
(`space/runtime_claims.py`) already reads `run_id` + `state` under `SELECT … FOR UPDATE`; have it
**return the locked `run_id` + `state` + `cleanup_required`**, and let the coordinator decide
terminate-vs-skip from that locked value.

- If the locked `run_id` is **bound** → `terminate_run` (a bind that committed in the gap is now seen
  under the lock and terminated).
- If the locked `run_id` is null → §3 governs the receipt.

The decision and the cancellation flag are set in the **same locked transaction**. Cancellation
transitions the null-running claim to `terminating` under that lock.

### 2.1 Bind compare-and-set guard (revision 1 — closes schedule-3)

The locked read alone does not close schedule-3, because the coordinator's decision executes after the
cancellation transaction releases the row lock; a late bind can still commit. Make **`bind_run_id` a
compare-and-set** that rejects a claim that is `cancel_requested` or outside its bindable state:

```sql
UPDATE runtime_resource_claim
SET run_id = %(run_id)s, updated_at = now()
WHERE resource_id = %(resource_id)s
  AND run_id IS NULL
  AND cancel_requested = false
  AND state IN ('pending','running')          -- bindable states only
RETURNING *
```

A no-match returns a typed `bind_conflict` (the caller then triggers cleanup of the just-prepared
work). **Invariant — complete dichotomy:**

- **Bind first:** the locked cancellation read sees the bound `run_id` and terminates it.
- **Cancellation first:** the claim is `cancel_requested`/`terminating`, so the late `bind_run_id`
  CAS **cannot commit** — bind fails and its prepared work is cleaned up.

No third ordering exists: a resource is either bound-and-seen or cancelled-and-unbindable. Seams:
`begin_resource_cancellation` return shape, `bind_run_id` CAS, `_force_resource`, `_close_target`,
the Node bind caller (`RunManager.ts`, `runtimeClaims.ts`) which must treat `bind_conflict` as a
cleanup trigger.

## 3. Synchronous fix B — "closed" derives from durable terminal state, never best-effort release

Redefine the coordinator receipt using the existing `cleanup_required` signal
(`cleanup_required = run_id IS NULL AND state = 'running'`):

| Locked claim state | External work? | Action | Receipt |
|--------------------|----------------|--------|---------|
| `run_id` bound | yes (a run) | `terminate_run`; claim → `terminal` on gateway confirm | `closed` (only on confirmed terminate) |
| `run_id` null, `state=running` (prepared, unbound) | maybe (capture/PTY prepared) | set `cancel_requested`; do **not** synchronously release | **`terminating`** — reconciler finalizes |
| `run_id` null, `state=pending` (never prepared) | no | cancel + release lease | `closed` (nothing external exists) |

**`closed` is emitted only when either a bound run was terminated OR a pending claim had no external
resource.** The prepared-but-unbound case returns `terminating`; the best-effort release must **not**
wake a waiter into a `closed` receipt before external cleanup runs. The waiter returns `terminating`,
not `closed`, until the durable claim is `terminal`.

### 3.1 Cleanup confirmation is process + PTY + capture (revision 2)

"Confirmed termination" is defined as confirmed cleanup of **all three**: the child **process** exited,
the **PTY** closed, and the **capture lease** released. The bound branch is currently underspecified:
`RunManager.performSettle` returns a terminated view after `releaseCaptureBestEffort` **even when
capture release times out or fails**. Rule:

- A terminal transition (`terminal`) is permitted **only downstream of confirmed process + PTY +
  capture cleanup**.
- **Any** timeout or failure of any leg → receipt is **`terminating`** (recoverable) or **`unknown`**
  (indeterminate), **never `closed`**; the durable claim **stays non-terminal**; reconciliation is
  **enqueued** for that `resource_id`.
- **The reconciler must NOT transition a claim to `terminal` after a failed force-termination.** A
  failed force-terminate keeps the claim non-terminal and retries.

Node seams: `RunManager.performSettle` must return `terminating`/`unknown` on any cleanup-leg failure
and not report terminated; `runtimeClaims.ts` waiter + `RunManager.ts:createNew` catch must sequence
the durable terminal transition strictly **after** `releasePreparedCaptureForCreateError`.

### 3.2 Retain failed capture-cleanup handles (revision 3)

Today `CaptureLeaseRegistry` removes the capture handle **before** `lease.close` finishes, so a failed
close leaves a live external capture the reconciler cannot see or retry (it went blind). Require: a
**failed capture close retains a retryable handle / tombstone keyed by `resource_id`** in the registry
(remove the handle only after cleanup is *confirmed*). The reconciler force-terminates a leaked capture
**through the retained handle**. Without this, lease expiry identifies the orphan but no authority can
terminate it. Seams: `CaptureLeaseRegistry` handle-retention on close failure; the reconciler's
leaked-resource path (§4.2) consumes the retained handle.

This tightens the synchronous window but cannot close it alone — §4 is the guarantee.

## 4. The reconciler — the correct primitive (`space/runtime_reconciler.py`)

Reconcile durable non-terminal claims against live process reality and reap the residual.

### 4.1 Authority — what it reads vs reality

- **Durable:** `runtime_resource_claim` rows in non-terminal states (`pending`/`running`/`terminating`)
  and their `worktree_lifecycle_lease` rows.
- **Reality (live-resource set, keyed by `resource_id`):** `RunManager` registered runs + pending
  creates, `CaptureLeaseRegistry` live captures, `PlainTerminalSessions` live PTYs.
- **Liveness signal:** the lease heartbeat/expiry. A live preparation/run heartbeats its lease; an
  orphan's lease expires. `RuntimeClaimStore.reap_expired_leases` already exists — the reconciler
  generalizes it: expired lease ⇒ orphan candidate, then confirm against the live set.

### 4.2 Sweep policy — fenced + TOCTOU-safe (revisions 4, 5 + live-set tightening)

`FOR UPDATE` serializes durable claims but **not** the Node maps, capture registry, or PTY
registration. Reading a live set then locking a claim leaves both stale-absence and stale-presence
races. The sound sweep **fences** a claim before touching live owners:

1. **Select** an expired/candidate claim (§4.5 defines candidacy).
2. **Lock + re-read** its current claim, lease, `cancel_requested`, and bind state under `FOR UPDATE`.
3. **Move to a fenced cleanup state** (`terminating` + a monotonically increasing **fencing
   generation** on the claim). This prevents a late bind/registration from publishing backing after
   the cleanup decision — the `bind_run_id` CAS (§2.1) already rejects a `terminating` claim, and live
   registration must carry the fencing generation to be accepted (revision 4).
4. **Command the live owners** by `resource_id` **+ fencing generation** (force-terminate via the
   shared `RunTerminationCoordinator.force_resources`; leaked captures via the §3.2 retained handle).
5. **Transition `terminal` ONLY** on **cleanup confirmation** (process + PTY + capture all confirmed,
   §3.1) **or authoritative absence** (the owner reports the resource unknown/gone). A **failed** force
   force-terminate keeps the claim non-terminal and **re-enqueues** (revision 2). Then `release_lease`.

Per-claim classification after the fenced re-read:

- **`terminating` / `cancel_requested` (explicit cleanup in progress)** → **desired-state outranks
  liveness (revision 5):** drive to confirmed cleanup **regardless of lease validity or a live,
  heartbeating backing.** A schedule-3 resource that bound + registered + keeps its lease valid is
  **not** healthy; it must still be terminated. Lease-expiry grace does **not** apply here.
- **bound `run_id`, no live run** → force-terminate (idempotent), confirm, `terminal` + release.
- **null `run_id`, `running`/`pending`, past its creation deadline (§4.5) or lease expired, no live
  backing** → abandoned orphan → confirm cleanup / authoritative absence → `terminal`/`cancelled` +
  release.
- **not `terminating`, live backing + within creation deadline / valid heartbeat** → healthy → skip.
- **reverse — leaked resource:** a live external resource whose claim is terminal/cancelled/absent
  (best-effort cleanup failed) → force-terminate through the retained handle (§3.2).

### 4.3 Cadence — startup + periodic (+ triggered); process-epoch startup (revision 7)

- **Startup (closes the crash residual):** the reap must run **before any current-generation claim can
  be created** — sequence it at `load_runtime()` **ahead of** exposing the claim/create surfaces.
  Reaping targets an actual **process epoch**, not the worktree lifecycle generation: stamp each claim
  with the API process epoch (e.g., a per-boot uuid/monotonic id) at insert, and at startup reap every
  non-terminal claim whose epoch ≠ the current boot epoch. Under the declared invariant that managed
  runs/captures/PTYs cannot survive an API restart, the prior-epoch live set is empty → reap all (mark
  terminal, release leases).
  - **Externally-owned-gateway caveat (revision 7):** the empty-live-set assumption holds **only if**
    no supported gateway/capture process can outlive the Python API. If a deployment runs an
    externally-owned gateway/capture (surviving process), startup must **first query/terminate that
    owner** by `resource_id` rather than assume absence. Spec a startup capability check: if the
    configured gateway is externally-owned, query its live resources and force-terminate prior-epoch
    backing before reaping; otherwise take the empty-set fast path.
- **Within-session (closes the best-effort-fail residual):** a **triggered** reconcile enqueued when a
  cleanup leg fails (RunManager/coordinator/§3.1), **plus** a **low-frequency periodic backstop**
  (piggyback on the lease-expiry sweep interval) to catch any missed trigger. Triggered is the primary
  driver; periodic guarantees coverage.

**Verdict: startup + periodic** (with triggered-on-failure as the primary within-session driver).

### 4.4 Idempotency + interaction

- Terminal claims are skipped; `transition_claim(terminal)` and `release_lease` are idempotent;
  force-terminate of a gone run → `run_not_found` no-op. Two concurrent reconcilers serialize on the
  per-claim `FOR UPDATE` lock, and cannot race a live `bind_run_id` (same lock).
- The reconciler consumes the shared `RunTerminationCoordinator.force_resources` seam — it does not
  invent a second termination path.
- Fenced cleanup (§4.2) plus the `bind_run_id` CAS (§2.1) guarantee a claim selected for cleanup cannot
  acquire late live backing; the fencing generation makes concurrent reconcilers and late creators
  safe.

### 4.5 Creation-deadline owns the whole create interval (revision 6 — CHOSEN over heartbeat-owner)

The pressure-test showed the "in-flight preparation heartbeats" assumption is false today: managed
heartbeat starts only **after** run registration, and a plain terminal heartbeats only **after** bind.
A long preparation can therefore cross lease expiry and be **false-positive reaped**. Two options were
offered; **this spec chooses the hard creation deadline** (not a heartbeat owner), because a durable
deadline is crash-safe and avoids the detached-heartbeat-outlives-owner failure the pressure-test
flagged for the orphan case.

- Add a durable **`create_deadline`** to the claim, set at claim acquisition to `now() + CREATE_TTL`
  where **`CREATE_TTL` < lease TTL**.
- **Renew** it (`now() + CREATE_TTL`) at **each external transition** of the create interval: prepare
  start, capture/PTY registered, and bind. Each genuine step of progress pushes the deadline forward.
- **Candidacy for reaping in the create phase = `create_deadline` passed** (not lease-expiry). A claim
  making progress renews its deadline and is never swept; a stalled/dead preparation stops renewing →
  deadline passes → abandoned → reap. After settlement (bound + registered), the **lease heartbeat**
  governs the running phase as before.
- This gives a single owner of liveness across the whole interval: the create-phase deadline (durable,
  transition-renewed), then the run-phase lease heartbeat. Neither can be kept alive by a detached loop
  after the real owner disappears.

`terminating`/`cancel_requested` claims ignore both grace gates (§4.2, revision 5) — they are driven to
cleanup immediately.

## 5. m1 — Git-unavailable must fail closed (fold-in)

`detection.py:_run_git` converts `OSError`/`subprocess.TimeoutExpired` into a synthetic return code
127; `detect_worktree_branch` then returns `None`, **indistinguishable from a legitimate detached/plain
no-branch**. So `runtime_claims._observe_branch` accepts unavailable Git as a null branch and the claim
path proceeds (fails **open**).

Fix at the detection boundary: distinguish **"enrichment unavailable"** from **"no branch"**.

- Add a strict branch-observation path (e.g., `detect_worktree_branch_strict`, or have
  `detect_worktree_branch` raise `SpaceDetectionError` on the unavailable case) so the synthetic-127 /
  `OSError` / `TimeoutExpired` path surfaces as **unavailable**, not `None`. Legitimate detached/plain
  HEAD still returns `None`.
- `_observe_branch` already maps `SpaceDetectionError` → `RuntimeClaimError("worktree_unavailable")`.
  Route the unavailable signal through it so the claim path **fails closed**: **no claim or lease is
  inserted** when branch enrichment is unavailable. Seams: `detection.py:_run_git` /
  `detect_worktree_branch`, `runtime_claims._observe_branch` + the claim insertion path.

## 6. Deferred to S4/S6 (documented residual, not a fix)

The **forced-delete-racing-cancel** interaction is explicitly S4/S6 territory — those slices build the
advisory forced-delete UX on this substrate (§8.1 of the S2 spec). The residual where a forced delete
proceeds immediately after a `terminating` receipt, before the reconciler finalizes, is closed by the
S4/S6 forced-delete flow coordinating with the lease/claim state (it force-terminates and waits for
terminal, rather than trusting an interim receipt). **Do not fix it here; carry a "Deferred to S4/S6"
note in the code + spec.**

## 7. Tests-first (all red before impl; observable end-state)

**STEP 0:** existing suite green post models-extraction; import-graph acyclic; `RuntimeClaimStore`
public surface unchanged.

**Synchronous fix A — stale-snapshot race:** hold `bind_run_id` before it commits; start a cancellation
that locks the row; commit the bind; prove the coordinator, reading `run_id` **under the lock**, sees
the bound id and **terminates** (no `closed`-without-terminate). Managed captures + plain terminals.

**Bind CAS rejects a cancelling claim (schedule-3):** cancellation locks the null-running claim → sets
`cancel_requested` + `terminating` → commits; a subsequent `bind_run_id` **fails with `bind_conflict`**
and triggers cleanup of the prepared work. Assert the resource is never left bound-and-live after a
cancellation decision. Managed + plain terminals.

**Synchronous fix B — receipt semantics + cleanup confirmation:**
- a prepared-but-unbound claim under force cancellation returns **`terminating`, not `closed`**; no
  `closed` before the faked capture/PTY cleanup runs.
- **cleanup-leg failure:** fail one of process / PTY / capture release → receipt is `terminating` or
  `unknown` (**never `closed`**), the durable claim stays **non-terminal**, and a reconcile is enqueued.
- `performSettle` returning after a failed `releaseCaptureBestEffort` must **not** report terminated.
- **reconciler must not transition `terminal` after a failed force-termination** (retry instead).

**Reconciler:**
- **startup sweep by process epoch:** seed prior-epoch non-terminal claims (bound + prepared-unbound +
  pending); run startup reconcile; assert all are `terminal`/`cancelled` and leases released. Assert the
  reap runs **before** the create surface accepts a current-epoch claim.
- **within-session best-effort-fail orphan (retained handle):** simulate a failed capture close that
  **retains** its handle keyed by `resource_id`; run reconcile; assert the leaked capture is
  force-terminated **through the retained handle** and only then is the claim `terminal` + lease
  released.
- **terminating outranks liveness (revision 5):** a `terminating`/`cancel_requested` claim with a
  **live, heartbeating** backing is still driven to confirmed cleanup and terminated (not skipped).
- **fenced registration (revision 4):** after the reconciler fences a claim (`terminating` + fencing
  generation), a late `bind_run_id`/registration is **rejected** and cannot publish backing.
- **long-preparation not false-reaped (revision 6):** a preparation that keeps renewing its
  `create_deadline` at each external transition survives repeated reconcile passes; a stalled
  preparation whose deadline passes is reaped.
- **failed force → non-terminal:** a reconcile whose force-termination fails leaves the claim
  non-terminal and re-enqueues.
- **idempotency:** a second reconcile pass is a no-op on already-terminal claims.

**m1:** force `OSError` and `subprocess.TimeoutExpired` from `subprocess.run`; assert the strict branch
path yields **unavailable** (not `None`), the claim path raises `worktree_unavailable`, and **zero
claims + zero leases** are inserted. A legitimate detached HEAD still yields `None` and proceeds.

## 8. Migration + gate

**Schema delta (v2):** the hardening adds durable columns to `runtime_resource_claim`:
`create_deadline timestamptz` (§4.5), `fencing_generation integer` (§4.2/§4.4), and `process_epoch`
(§4.3). No new tables — the retained capture handle (§3.2) lives in-memory in `CaptureLeaseRegistry`
(captures are process-resident; nothing leaks across a restart). Per "No production, no legacy": if
`0031` is still unmerged on the S2 branch, **extend it in-place** (drop-and-recreate the claim table
with the new columns); if `0031` has landed, add **`0032`**. Confirm the choice against the branch
state at build time.

- Engineer + reviewers: `just check` + `just test-affected`.
- Grok local-CI: `just check` + `just test` + `just migration-smoke` (proves the claim-column delta
  applies cleanly to head).

Bounded: STEP 0 keeps `runtime_claims.py` under 700; reconciler in its own module; no function >150.
Cite file+symbol, never file:line.
