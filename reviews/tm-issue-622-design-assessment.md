# Issue 622 resident delivery reconciler: design assessment

Reviewer: transport-matters:general:1:4.2
Requested by: transport-matters:general:1:4.1
Read on `886608ca` (main). Worktree `.worktrees/issue-622`, branch `fix/622-resident-delivery-reconciler`.

## Verdict

Process scope: **agree**, and for a stronger reason than the issue states.
Registration mechanism: **agree with the store create observer**, conditional on item 5.
Subscription shape: **disagree**, four per delivery is wrong on three counts (items 2, 3, 4).
One fork needs a ruling before code (item 5).

## 1. Process scope is right, and the issue's own reason does not hold

The issue justifies dropping the `settings.run_id` guard with "it acts only on events its own
hub sees". That reason is false on a shared channel database: `SessionEventHub` is fed by
`SessionEventListener` over PG `LISTEN`, so every sibling backend's `_notify` reaches it. Your
observation is correct.

The reason that does hold is that `DeliveryReconciler` **writes**. Reconciling a foreign row:

- `read_workspace_activity` answers only for runs this gateway's `RunManager` holds, so a
  foreign target yields `target is None` and `claim_cursor is None`.
- `_claim_deliveries` then calls `store.claim(..., claim_cursor=claim_cursor or delivery.baseline_cursor)`,
  and `_CLAIM_SQL` flips `pending -> claimed` with `COALESCE`.

A foreign backend therefore persists a different `claim_cursor` than the owning backend would,
from absence. That is the #610 failure class. Put this in the PR body and beside the missing
guard, because a future reader checking the issue's stated reason will find it does not survive
contact with the listener.

Note the safe half: `run_ended` requires `target is not None and target.tier == "terminal"`, so
the reconciler already refuses to kill on absence. Only the claim write escapes.

## 2. The subject is the target, not the delivery

`reconcile_target(principal, target_run_id)` calls
`list_for_target(owner, workspace_id, target_run_id)` and reconciles **every** open delivery on
that run in one pass. Registering per delivery gives N subjects doing byte-identical work on one
run. Register `(owner, workspace_id, target_run_id)`; a second delivery on a live target is a
no-op registration.

This also supplies the retirement rule, which the proposal is missing. A subject retires when a
pass observes all-terminal with no `needs_block_repair` row, the predicate the reconciler already
evaluates at its top. Without a retirement rule the process accumulates one `run_events`
subscription per prompt ever sent, for the life of the process.

## 3. Two of the four subscriptions are per (workspace, owner), not per subject

`subscribe_wire_deliveries` and `subscribe_wire_exchanges` key on `(workspace_id, owner)`.
Opening them per subject duplicates fanout queues and multiplies the `QueueFull` to
durable-catch-up cost on precisely the busy workspace the damping requirement exists for.

Pool them the way `ControlPlaneWatchEngine` already does: `_ensure_feed` builds one
`WorkspaceFeed` per `(workspace_id, owner)` and `_stop_unused_feeds` refcounts it against live
watchers. Per subject you need `subscribe_run_events` only. One per subject plus a shared feed,
not four per subject.

## 4. The control-plane delivery subscription is mostly self-echo

`ControlPlaneDeliveryStore._notify` fires on `create` and on every `_update`, which is what the
reconciler itself writes. `wait_for_reply` tolerates waking on its own writes because it
re-checks terminal and returns. A resident does not return.

Either drop that subscription (run events plus the two pooled workspace feeds already cover the
doorbell the issue names) or make the damper suppress a wake caused by the pass's own write. Do
not leave a self-triggering loop behind a coalescing interval and call it damped.

## 5. Do not synthesize a ControlPlanePrincipal (the fork)

This is the cost of registering off `create`: a row carries `owner`, `workspace_id`,
`target_run_id`, `actor_run_id`. It carries no `role`.

Verified: the entire reconcile path reads exactly `principal.owner` and `principal.workspace_id`.
Every gateway call passes those two, `list_for_target` takes them as keywords, and
`ControlPlaneReadStore.wire_delivery_claims` binds `GET_WIRE_DELIVERY_EXCHANGES_FOR_OWNER_SQL`
with owner and workspace_id alone. `principal.run_id` and `principal.role` are never read.

The tree has exactly one production `ControlPlanePrincipal(...)`, in
`capture_rpc.resolve_control_plane_grant`, and it binds a real stored grant to a live capture. A
resident minting `role=DIRECTOR` would be the first fabricated credential in the codebase.

Two honest routes:

**(A) Carry the real principal from the authenticated call site.** Matches
`ControlPlaneWatchEngine`, which stores `Watcher(principal=principal)` from `watch()`. Cost: the
registrar must reach `VerifiedPromptDelivery.deliver` and
`LaunchDeliveryRecorder.record_launch_delivery`. The latter is constructed inside
`ControlPlaneService.__init__` and handed to `ControlPlaneLauncher`, so this is a new optional
parameter through a constructor that already carries about twenty. It also forces a reorder in
`main.py`, where `prompt_delivery` is built before `delivery_waiter`. `DeliveryReconciler`
untouched.

**(B) Narrow `reconcile_target` to the scope it actually reads.** Registration then needs nothing
but the row, and your store observer stands exactly as proposed with no plumbing and no reorder.
Cost: `DeliveryReadPort.wire_delivery_claims` and `ControlPlaneReadStore` narrow with it, plus
the doubles in `watch_test_support`, `delivery_wait_test_support`, `test_delivery_proof` and
`test_delivery_claimless_starvation`.

Recommend **(B)**. More files, but all of it signature narrowing with no behaviour change, and it
removes the reason to fabricate instead of hiding it. It also settles a question (A) leaves ugly:
one target can carry deliveries from several actors, and `reconcile_target` settles all of them
in one pass. Under (B) that is plainly correct because the scope is exactly what `list_for_target`
filters on. Under (A) it reads as one actor's credential settling another actor's rows.

**Caveat, and why this needs a ruling rather than your judgement or mine:** the issue says
"reusing `DeliveryReconciler` unchanged. No new reconciliation logic." (B) adds no logic but it
does change a signature. Raise it with the issue author before writing it; do not absorb the
wording silently either way. (A) is defensible if the constraint is meant literally.

## 6. Agreed as proposed

- Public serialized reconcile on the shared `DeliveryWaiter`, reusing `_serialize(owner, run_id)`
  and `DeliveryReconciler`. Required by the acceptance criterion about a concurrent
  `wait_for_reply`, and it avoids a fourth copy of the lock-registry idiom already duplicated
  across `DeliveryWaiter._TargetOperation`, `VerifiedPromptDelivery._RunDeliveryOperation` and
  `ControlPlaneWatchEngine._serialize_watcher`.
- `wait_for_reply` keeps its in-loop reconcile.
- No channel-wide scan, no runtime lease.
- Initial durable catch-up plus reconnect catch-up.

## 7. Two details to settle in the implementation

- **Error policy.** A resident has no caller to raise into. `_bind_deliveries` reaches the
  gateway, which can raise `GatewayUnavailableError` / `GatewayResponseError`; the waiter converts
  those for its caller. The resident should swallow into the log and retry on the next signal,
  the convention `run_startup_refresh` already sets.
- **Close site.** `main.py`'s `finally` closes `control_plane_watch` via
  `_close_lifespan_resource` before the gateway supervisor and run proxy. The resident belongs at
  that same site with the same treatment.

## Addendum: route A accepted, three follow-ups

Implementer chose route A (real principal into the shared `_track_delivery`, tracker port on both
producers) to preserve the issue's unchanged-reconciler constraint. No objection to that seam. It
is the single site both producers already funnel through, and it fires on proven persistence.
Registering at create rather than after the receipt is also correct: a receipt whose terminal
write fails is exactly the row that must still settle.

**1. Route A opens a wiring hole route B did not have.** `LaunchDeliveryRecorder` is constructed
inside `ControlPlaneService.__init__`, not in `main.py`, and `main.py:353` is the only production
`ControlPlaneService(` call. The tracker therefore has to be threaded main -> service -> launcher
-> recorder. Wire it only to the `main.py` `VerifiedPromptDelivery` and launch-issued first
prompts stay unregistered, which is half of #622's scope, and every existing test still passes.
`ControlPlaneService` also carries a fallback `VerifiedPromptDelivery` construction; it is
unreachable from `main.py` (`prompt_delivery is None` implies `gateway is None` there) but it
must not be left as an untracked constructor for a future caller. Gate this: assert in the
lifespan test that a tracker is present on both producers wherever the resident exists.

**2. Withdrawing half of item 4, and a hazard in the suppression.** `_LedgerRecorder._record_receipt`
writes `finish` / `claim` / `note` outside any reconcile pass, so the control-plane delivery
stream does carry non-echo signals. Retaining all four streams is right.

But `VerifiedPromptDelivery._registry_lock` / `_operations` and `DeliveryWaiter._registry_lock` /
`_operations` are separate registries, so an actuation receipt write can land *during* a resident
pass on the same `(owner, run_id)`. Suppression must key on the identity of the rows the pass
actually mutated. A time window around the pass swallows the receipt signal, and the delivery
that loses it is the one whose actuation just failed.

**3. Name the retained principal for what it is.** Only `owner` and `workspace_id` are ever read
from it, and the actor run may have exited. Say so at the field. Without it a later reader takes
a stale grant for a live one and adds a `role` check or a `run_id` use on top of it.

Replay is safe: `store.create` returns the existing row on conflict and `_track_delivery` returns
True, so a replayed dispatch re-registers. Under target keying that is a no-op.

## Review of 6ac2ff16, and the fix at ff7833ef

Wiring verified correct. Both producers and the `ControlPlaneService` fallback carry the tracker,
`_track_delivery` registers on proven persistence, the retained principal is named
`scope_principal` with a comment, workspace wires are pooled per `(owner, workspace)`, the target
task is per `(owner, workspace, target_run_id)`, and the resident closes beside
`control_plane_watch`. My three earlier follow-ups are all addressed.

Self-echo is handled by proof rather than a window, which is stronger than what I asked for:
`drain()` runs immediately before the durable read, so events arriving during a pass survive it,
and a write-free follow-up pass ends the echo. The time-window hazard I raised does not apply.

### Defect found: an open question never retires its target

`_retire_settled` treated `needs_block_repair(row)` as keeping a delivery active. That predicate
is `state == "needs_you" and reason is None`, which is exactly what `_resolve_deliveries` writes
when a boundary ends `needs_you` with no run-wide block, and what `_finish_blocked` writes under
`_OPEN_QUESTION`. An open question therefore satisfies it forever, because the block the repair
looks for never arrives.

Consequence: every prompt whose turn ends with the agent asking a question permanently pinned its
target feed, its run subscription and its workspace wire feed, running a full reconcile pass
(workspace activity plus completed turns plus conversation scans) on every damped wake for the
life of the process. Cost grew with every prompt the process had ever sent. The 17 added cases
had no `needs_you` coverage and no retirement assertion outside the completed path, so the gate
was green.

Fix: a repairable row earns exactly one further pass, the same single repair attempt
`wait_for_reply` makes before it returns a terminal row, then settles.

Two regression cases added. `test_open_question_delivery_retires_its_target` fails on 6ac2ff16
(retirement never reached, 30s hang guard) and passes on ff7833ef.
`test_terminal_needs_you_still_earns_one_repair_pass` drives the ordering race `_repair_blocked`
exists for and proves the repair was not deleted; it passes on both, which is its job.

### Accepted cost, not changed

Each pass runs `list_for_target` twice, once inside `reconcile_target` and once in
`_retire_settled`. Removing it means returning rows from `DeliveryReconciler.reconcile_target`,
which the issue's unchanged-reconciler constraint forbids. It is one indexed read per pass on a
path damped to at most four passes per second per target. This is the price of route A and it is
worth paying; do not restructure the reconciler to save it without the issue author.

### Dropped

I had flagged the missing exception guard on the resident's `_consume_wire`. `ControlPlaneWatchEngine._consume_wire`
carries no guard either, and unlike that one the resident's consumer performs no I/O: it reads
signals and sets events. I could not construct a failure, so it does not meet the bar.

## Blessing: 477d7f6ed0a23352d27154ff579c0b0945f867f3

The implementer found a real hole in my retirement fix and closed it. My "one further pass" was
eligible but unscheduled when registration catches up with a row that is *already* terminal
`needs_you`: `_track_delivery` calls `track` with whatever `create` returns, and on the
`ON CONFLICT DO NOTHING` replay path that is the existing row. No further write means no further
notification, so the feed waited forever on a pass it had already granted. I had considered this
path and wrongly dismissed it as unreachable from the create seam. `feed.events.wake()` at the
moment the pass is granted is the correct fix: it is called once per delivery per feed, so it
cannot loop.

Independently verified, not taken on report:

- `test_open_question_delivery_retires_its_target[True]` FAILS on `ff7833ef` (30s hang guard) and
  `[False]` passes, reproduced by running their test file against my source.
- All 15 resident cases pass on `477d7f6e`.
- `just check` green: 926 files, mypy clean, workspace checks.
- `just test-affected 886608ca` green: 4766 passed, 13 skipped.
- Tree clean at `477d7f6e`, matching origin.

Logs: /tmp/tm-622-bless-check.log, /tmp/tm-622-bless-affected.log.

Blessed for PR.
