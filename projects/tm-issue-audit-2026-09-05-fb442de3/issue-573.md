# 573: a second queued nudge strands the first delivery; deliveries only reconcile inside wait_for_reply

URL: https://github.com/littleorgans/transport-matters/issues/573
State: open
Labels: bug, P5
Updated: 2026-09-02T01:09:06Z

## Summary

Two nudges queued during one turn strand at least the first delivery, on Claude and on Codex. The run's live prompt binding holds one slot, so the second nudge overwrites the first, and the first prompt's request goes out with no delivery id. On Codex the queue is also released as one merged user message, so neither digest matches and both strand. Stranded rows stay `pending proof_deadline` through every `wait_for_reply` and only end as `run_ended` / `target_exited` when the run closes. Grok is untested.

Separately, delivery rows are only reconciled inside `wait_for_reply`. A row nobody waits on stays uncorrelated however complete the evidence is. The original report's four rows were this second case: they correlated on the first wait against that run and reached correct terminal states.

## Reproduction (2026-09-02, preview, main at `5a30f478`)

Same steps on both harnesses. Codex run `17d9de97`, Claude run `c540eb28` (sonnet).

1. `prompt` a long task (A). Receipt `submitted`, wire claim recorded.
2. While A runs, `prompt` nudge B1 `... Reply with exactly one word: FIRSTQUEUED`. Receipt `proof_deadline`, as expected mid-turn.
3. `prompt` nudge B2 `... SECONDQUEUED`. Receipt `proof_deadline`.
4. `interrupt` the run. Codex aborts A and releases the queue.

Observed on Claude:

- Claude releases the queue as two separate turns and answers `FIRSTQUEUED` then `SECONDQUEUED`.
- The wire request for the first turn has `delivery_id IS NULL`; the second carries B2's delivery id and the binding file is consumed.
- `wait_for_reply` on B2 returns `completed` with the `SECONDQUEUED` reply. B1 returns `pending` / `proof_deadline`, `prompt_cursor IS NULL`.

Observed on Codex:

- The transcript holds one user turn with both prompts concatenated by a newline:
  `Forget the previous task. Reply with exactly one word: FIRSTQUEUED\nForget the previous task. Reply with exactly one word: SECONDQUEUED`
  The assistant answered `SECONDQUEUED`.
- The wire request for that turn has `delivery_id IS NULL`. The run's `.live-prompt-delivery.json` held only B2's digest (B1's binding was overwritten at step 3) and that digest did not match the merged text, so the binding file is still armed after the turn.
- `wait_for_reply` on B1 and B2 returns `pending` / `proof_deadline`, `prompt_cursor IS NULL`. A on the same run resolves `interrupted` correctly.
- After `close`, both return `run_ended` / `target_exited` with no prompt cursor.

## Why

Correlation requires a wire claim before it will bind. `DeliveryReconciler._claim_deliveries` reads `wire_delivery_claims`, `_bind_deliveries` skips any row whose `claim_exchange_id` is null, so a delivery with no wire claim can never gain a `prompt_cursor`.

Two things remove the claim for queued prompts:

1. Every harness: `LivePromptDeliveryBindings.arm` holds one binding per run and overwrites unconditionally. `claim` only unlinks on a digest match. The second nudge discards the first's binding, so the first prompt's request carries no delivery id.
2. Codex only: queued prompts are merged into one message, so `latest_user_prompt_digests` never contains either prompt's digest, and the transcript digest comparison in `_bind_deliveries` fails the same way. Fixing the binding slot alone does not correlate a merged turn.

## Original report (2026-09-01, run `ff6ca51b`), re-examined against the database

The four deliveries `af63b1c0`, `a3c2dc43`, `766ba874`, `1be4c1b6` are all terminal today with correct ranges (interrupted, completed `REDIRECTED`, interrupted, completed `QUEUED`), all updated at 13:28:34 UTC. `control_plane_action` shows no `wait_for_reply` for any of them. The first wait against that run, for a later delivery, started at 13:28:34 and reconciled every open row. The SQL snapshot in the report predates it.

Their evidence was durable within seconds of each turn. Each queued prompt there was released alone by an interrupt before the next nudge was armed, so its wire request carried the delivery id and correlation succeeded once something ran the reconciler.

`DeliveryReconciler.reconcile_target` is called only from `DeliveryWaiter._reconcile_scoped`. `VerifiedPromptDelivery.deliver` and `_LedgerRecorder._record_receipt` claim or fail, never bind. Nothing since `cd32124a` changes this; the startup reconcile in `#585` covers lifecycle rows only.

## Scope

1. **Multiple pending bindings.** Make `LivePromptDeliveryBindings` hold every pending binding for the run rather than one, claiming each by its own digest. This alone fixes Claude. Test in `test_delivery_binding.py`: arm two, claim requests carrying each digest in turn, both deliveries claimed.
2. **Codex merged queue.** Let `claim` and `_bind_deliveries` match a delivery whose prompt text is one line of a merged user message. Decide the outcome per delivery (both `completed` on the same range, or the earlier one `superseded`). Test in `test_delivery_reconcile.py` with a Codex fixture holding a concatenated queued message.
3. **Lazy correlation.** Either reconcile on evidence (subscribe to wire delivery and run event signals on `SessionEventHub`, run `reconcile_target` for targets with open rows, keep the per target lock from `DeliveryWaiter._serialize`) plus a startup sweep in `startup_passes.py`, or document in the `prompt` and `wait_for_reply` tool descriptions that rows correlate only when waited on. Add a test that one wait binds and finishes a sibling delivery on the same target.


## Sub issues
[]
