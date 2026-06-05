# PR #296 adversarial review: S2d

Reviewed `main@7dc7dc3f660e1c8b4f972357dcf9408f5f7b5ce3...feat/s2d-block-store@670c4c4196a0069f1b8b46b10e65198cf9e0755e` through `gh pr diff 296`.

Verdict: 0 Blocker, 5 Major, 1 Minor.

## Findings

1. Major, 92/100. `api/src/transport_matters/harnesses/blocks_store.py:94`

   Reusing an `evidence_id` with different immutable content silently preserves the first Postgres row, then `emit_drift_evidence()` constructs its audit action from the second object. A changed executor produces a second audit row because audit uniqueness is `(actor, verb, dispatch_id)`, while the dispatch UUID derives only from `evidence_id`. Durable evidence and its operator mirror can therefore disagree. A same executor collision also returns success for evidence that was discarded. The current test explicitly accepts a changed `detail_code` under the same ID.

   Evidence: [evidence conflict handling](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks_store.py#L94-L101), [audit construction from the incoming object](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks_store.py#L175-L211), [audit unique key](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/migrations/versions/0016_action_dispatch_idempotency.py#L34-L39), [test accepting divergent content](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/test_blocks_store.py#L124-L130).

2. Major, 92/100. `api/src/transport_matters/harnesses/blocks.py:254`

   Empty release, route, and model identifiers count as resolved because attribution checks only `is None`. Evidence with `release_id=""`, `route_id=""`, and `model_id=""` can return `create_block`. The resulting active block persists but cannot match real launch context, so the explicit safety action succeeds without blocking or pausing the release. The contract requires absent resolved context to pause the release.

   Evidence: [optional context without nonempty validation](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks.py#L114-L143), [None only attribution check](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks.py#L245-L256).

3. Major, 87/100. `api/src/transport_matters/harnesses/blocks.py:89`

   `ExecutorVersionBlock` inherits both allowed origins and does not require `origin == "executor"`. The local executor store persists `origin="publisher"`, `merge_executor_blocks()` accepts it, and `match_release()` enforces it without checking provenance. This lets unsigned local state enter the publisher block path, which the compatibility contract reserves for signed channel state.

   Evidence: [executor model validation omits origin](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks.py#L89-L105), [local persistence accepts the model](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks_store.py#L113-L122), [merge validates only harness identity](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks.py#L308-L328).

4. Major, 88/100. `api/src/transport_matters/harnesses/blocks_store.py:124`

   `supersede_block()` accepts `superseded_by == block_id`. A caller typo permanently changes the block to superseded, removes it from `active_blocks()`, and records no later successor. First writer wins then prevents correction to the real successor. The FK less design is valid for publisher references, but a self reference cannot represent the later update or release required by the contract.

   Evidence: [supersession validates only nonempty text](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks_store.py#L124-L143).

5. Major, 82/100. `api/src/transport_matters/harnesses/blocks_store.py:194`

   `emit_drift_evidence()` is async but directly calls synchronous psycopg connection acquisition and insertion before its first `await`. Connection latency, a database lock, or failure recovery blocks the event loop at the drift seam. The synchronous store methods can serve synchronous preparation paths, but this async wrapper must use async database I/O or move the blocking call off loop. `api/CLAUDE.md` assigns I/O to async boundaries.

   Evidence: [synchronous write method](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks_store.py#L145-L148), [async wrapper calling it inline](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks_store.py#L181-L195), [Python async convention](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/CLAUDE.md#L3-L6).

6. Minor, 90/100. `api/src/transport_matters/harnesses/blocks.py:84`

   The new pure vocabulary duplicates two existing contract owners. `_require_nonempty()` repeats the helper in `connections.py`, and `_SCOPE_KEY_FIELDS` repeats the complete scope key map inside `VersionBlock._validate_scope_keys()`. Scope construction and validation can now evolve separately. The root convention requires shared helpers and constants instead of parallel copies.

   Evidence: [new nonempty helper](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks.py#L84-L86), [existing helper](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/connections.py#L62-L68), [new scope map](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/blocks.py#L259-L264), [existing scope map](https://github.com/littleorgans/transport-matters/blob/670c4c4196a0069f1b8b46b10e65198cf9e0755e/api/src/transport_matters/harnesses/compatibility.py#L290-L304).

## Verified

1. Block creation uses immutable `INSERT ... ON CONFLICT (block_id) DO NOTHING`. Supersession uses the required one way conditional update. The tested create, supersede, stale create order cannot resurrect a stored superseded row.
2. Multiple active blocks per natural scope remain allowed. No unique index was added.
3. Migration 0023 adds only the drift evidence table. Downgrade drops only that table. Reset, expected head, focused round trip, and full migration walk were updated.
4. Drift evidence stores a closed kind and detail vocabulary plus a digest. No raw output field reaches the new table or audit mirror.
5. All four S2d typed constructors exist. Automatic emission and block creation remain unwired for S2f. `match_release` has no production caller or launch path import.
6. `ExecutorVersionBlock` composes `VersionBlock`. `compatibility.py` remains flat. All 14 changed files remain below 700 lines, and no changed function approaches 150 lines.
7. The final eligibility check found PR #296 open and non draft, with no prior review from this identity. Local branch and HEAD match the PR head, and `git status --short` is empty.

No gates were run, per the review brief.

Craftsmanship: the domain, store, migration, and test split is clear and size compliant, but unchecked identity, provenance, lineage, and async boundary cases keep this slice from merge quality.
