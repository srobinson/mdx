# Architect review: PR 3 wire derived agent state

Reviewed `~/.mdx/projects/tm-agent-state-spec-pr3.md` against main `157f781ffd1d28b060c19490a17c8e3569b2d478` and the merged PR 2 producer.

## Verdict

The cursorless latest exchange projection is a useful read shape, but the proposed `created_at >= lastEventTs` admission rule is not a sound causal precedence rule. The spec needs revision before build.

## Findings

### HIGH: `created_at` is asynchronous persistence time, so E3 and E4 can admit stale outcomes

Spec anchors: §1 step 3, §3.1, E3, E4.

The crux is partially correct. `wire_exchange.created_at` is independent of the copied provisional `IndexEntry.ts`:

- Migration 0008 defines `created_at timestamptz NOT NULL DEFAULT now()`.
- `UPSERT_WIRE_EXCHANGE_SQL` omits `created_at` from both INSERT values and `DO UPDATE`, so the first insert owns the stable value.

It is not the finalize instant or commit instant. `WireStoreObserver.on_exchange` schedules `submit_wire_exchange` asynchronously behind `_write_slot`; the database transaction starts only when that queued coroutine acquires its turn and connection. PostgreSQL defines `now()` as `transaction_timestamp()`, the transaction start time: https://www.postgresql.org/docs/current/functions-datetime.html

Counterexample:

1. Ask exchange finalizes at F and is queued for the wire writer.
2. The operator answers; the transcript applies `tool_result` at A and projects `reasoning`.
3. The queued wire transaction starts at W, where W > A, and inserts the old ask with `created_at = W`.
4. Reconcile applies the answer, then admits the ask because W >= A, restoring `needs-you-asked` after the answer.

The same ordering lets an exchange N idle write delayed past turn N+1 transcript activity and defeats E4. Same host clock skew does not address queue or pool latency. A causal finalize timestamp must be captured synchronously at the sink, or precedence must use another durable causal rule.

### HIGH: E6 suppression expires after one pass and the cursorless assertion reappears

Spec anchors: §3.1, E6, T3.

For the accepted equality case, let the answer `tool_result.ts` equal the ask `created_at`.

1. The answer batch applies and sets `lastEventTs` to T.
2. Same pass suppression sees the matching tool result and skips the ask snapshot.
3. A later reconnect or forced reconcile has an empty record batch, so suppression has no matching row to inspect.
4. The unchanged ask snapshot satisfies `created_at >= lastEventTs` because T >= T and reasserts `needs-you-asked`.
5. Repeated passes keep admitting the same assertion until a later transcript row advances time.

This is a persistent cross pass conflict, not a one pass transient. T3 only proves the transition out of asked if it pins this equality boundary. A batch local suppression cannot provide durable knowledge that the tool call was answered.

### MEDIUM: E7 has no retraction semantics

Spec anchor: E7.

If the latest admitted ask is deleted, the next snapshot is either absent or older. An absent snapshot emits nothing. An older snapshot fails `created_at >= lastEventTs`. Neither path clears the already applied `needs-you-asked` state, so deletion leaves a stale assertion until some unrelated later activity arrives.

The spec should either state that finalized rows are never deleted and remove E7, or define an explicit retraction and test its projected end state.

### MEDIUM: T1 through T9 do not cover the load bearing conflict matrix

Spec anchors: §3.3, §5 commits 3 and 4, §6.

Section 3.3 says every E1 through E8 case is a test in §6, but the T1 through T9 list has no explicit test for:

- E5 tailer lag flip back.
- E6 equal timestamp followed by a second empty reconcile.
- E7 deletion after a previously admitted assertion.
- A delayed wire insert whose `created_at` is later than the answer or next turn transcript timestamp.

T3 covers answer to reasoning and a forced reconcile in the ordinary strict ordering case, but it does not constrain timestamp equality or delayed persistence. The spec also promises prechange failure only for T1, T2, T4, T5, and T6. The acceptance plan must require a red observation for every newly protected behavior, especially the conflict and retraction cases.

## Confirmed

- `created_at` is a first insert database timestamp and is never overwritten by finalize replay. It is not copied from the provisional request start timestamp.
- The proposed reader can be built from existing `wire_exchange`, `wire_response_block`, and `tm_events` data. No migration is required for the stated read shape.
- No Python API surface is needed. `@tm/activity` already owns the PostgreSQL reader and `tm_events` listener.
- Filtering `track_role IS DISTINCT FROM 'subagent'` handles E8.
- Applying records first, the wire assertion second, and `run-exited` last is structurally clear. The time guard fails to make that precedence causal in the delayed, equality, and deletion cases above.
- The existing `(run_id, ts)` index does not cover `ORDER BY created_at`; this is a performance consideration, not a correctness reason for a migration in the first slice.

## Required spec correction

Replace the timestamp admission rule with a causal assertion and retraction contract, then add red first projected end state tests for delayed persistence, equality across a second reconcile, tailer lag recovery, and deletion. T3 must pin the answer timestamp boundary and prove `needs_you` stays cleared after another empty reconcile.
