# WS5 — spawn-recovery hardening (R11-bounded)

> Cold-read handoff for the WS5 warroom. Branch `feat/spawn-recovery-hardening`, worktree
> `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans-worktrees/spawn-recovery-hardening`
> (off `main` @ `d756059`). Design settled below; implement, do not re-litigate.

**Goal:** Close the one real spawn-recovery gap — a Tx-B commit failure orphans a running
runtime until the next restart — by making it symmetric with the inline cleanup the
namespace-deleted path already does. Lock the abort-atomicity invariant with a test.

## Finding that reshaped WS5 (verified in code, not assumed)

The originally-specced "window #2" (reconcile stranded `Forking` lifecycles whose intents
are aborted/missing) **cannot happen**. `abort_spawn_intent` (spawn.rs:214-235) runs the
intent UPDATE(→aborted) and the Forking-lifecycle DELETE inside one
`begin_immediate_tx`/`finish_immediate_tx` transaction; `finish_immediate_tx`
(internal/db/src/lib.rs:88-100) COMMITs on Ok and ROLLBACKs on Err. So abort is atomic.
Combined with Tx-A (insert intent+Forking atomically) and Tx-B (resolve intent + Running
atomically), **a Forking lifecycle always has a corresponding `pending` intent**, so
reconcile's `list_pending_spawn_intents` scan (spawn.rs:238-242) already covers every
Forking. No stranded-Forking fix is needed; WS5 only asserts this invariant.

## The one real gap — Tx-B commit-failure asymmetry

`complete_spawn_intent` (spawn.rs:135-212):
- The **namespace-deleted** branch (147-179) cleans up inline: `terminate` the runtime
  (best-effort, logs on `Ok(None)`/`Err`) → `abort_spawn_intent` → bail.
- The **Tx-B commit** at line 205 (`finish_immediate_tx(&mut conn, result, "session spawn
  Tx B").await?`) just `?`-propagates on Err. After the ROLLBACK the intent is still
  `pending` and the Forking row still present, and the runtime spawned at spawn.rs:73 is
  **still running** — orphaned until the next daemon startup runs
  `reconcile_pending_spawn_intents`. A long-lived daemon never sweeps it.

## Card C1 — symmetric inline cleanup + invariant test

**File:** `internal/session/daemon/src/handler/spawn.rs`

1. **Extract a helper** (DRY) from the namespace-deleted branch, e.g.
   `async fn abort_running_spawn(&self, session_id: Uuid, reason: &str) -> Result<()>`:
   best-effort `self.runtime.terminate(&session_id.to_string(), "SIGTERM",
   Duration::from_secs(5))` with the existing `Ok(Some)/Ok(None)/Err` tracing arms
   (lines 159-172), then `self.abort_spawn_intent(session_id, reason).await`. Replace the
   inline sequence at 154-175 with a call to it.
2. **Use it on the Tx-B failure path.** Change line 205 so a `finish_immediate_tx` Err is
   captured (not `?`-propagated raw): on Err, call `self.abort_running_spawn(session_id,
   &format!("session commit failed: {error}"))`, then return the original error. The
   ROLLBACK has already restored intent=pending + Forking, so `abort_running_spawn`
   cleanly kills the runtime, marks the intent aborted, and deletes the Forking row — no
   orphan, no leftover pending intent.
   - Keep `append_event` (line 207-210) on the success path only.
   - Do NOT change the reconcile/recovery paths; they are correct as-is.

**Tests** (`internal/session/daemon/tests/handler/`):
- **Tx-B-failure regression:** force Tx-B to error deterministically (e.g. pre-insert a
  session row that collides with `insert_session_in`, or the smallest seam that makes one
  of the three Tx-B writes fail) for a spawn whose runtime DID start. Assert: the runtime
  was terminated, the intent is `aborted` (not `pending`), the Forking lifecycle is gone,
  and no session row persisted. (Before C1 this would leave a `pending` intent + Forking +
  live runtime.)
- **Abort-atomicity invariant:** after `abort_spawn_intent`, assert no Forking lifecycle
  remains for that session AND the intent is `aborted` — documents why reconcile's
  pending-only scan is complete (window #2 is impossible).

**Acceptance:** `just check && just build && just test` green; Tx-B failure leaves no
orphan/pending; abort-atomicity invariant asserted. One commit
`fix(session): inline-abort the spawned runtime on Tx-B commit failure (WS5)`.

## Out of scope / carry-forward
- Periodic (vs startup-only) reconcile — not needed once Tx-B failure is handled inline;
  R11 keeps recovery startup-driven. YAGNI for v1.
- Runtime-kill reliability when `terminate` itself fails (process won't die) — a
  runtime-layer concern, not R11/WS5.
- WS6 (conformance + Linux + tmux hermeticity) unchanged.
