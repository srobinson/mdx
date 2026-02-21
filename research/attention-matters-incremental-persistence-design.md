---
title: Incremental Persistence Design for attention-matters
type: research
tags: [attention-matters, persistence, performance, architecture]
summary: Design specification for replacing full-system serialization with incremental episode-level writes in am-store
status: active
source: rust-engineer
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

# Incremental Persistence for attention-matters

## Problem Statement

`Store::save_system` serializes the entire `DAESystem` to SQLite on every write. The implementation (store.rs:113-150) executes within a single transaction:

1. DELETE all rows from occurrences, neighborhoods, episodes
2. Re-INSERT every episode, neighborhood, and occurrence

This is O(N) where N is the total occurrence count. At 1,000 episodes (~50k occurrences) the write latency will become perceptible in MCP tool responses. At 10,000 episodes it will be unacceptable.

The system already has *some* granular write operations (`increment_activation`, `mark_superseded`, `save_occurrence_positions`, `append_buffer`, `drain_buffer`, `forget_episode`, `forget_conscious`, `forget_term`, `gc_pass`). These operate directly on SQLite rows without touching `save_system`. The goal is to extend this pattern so that `save_system` is only called for bulk operations (import, ingest CLI) while hot-path MCP tools use targeted writes.

## Current Write Paths

### MCP server tools that call save_system (server.rs)

| Tool              | Mutation                                         | Minimal Write Needed                    |
|-------------------|--------------------------------------------------|-----------------------------------------|
| `am_query`        | Drift, activation, Kuramoto coupling on occurrences; orphan buffer flush adds episode | `save_occurrence_positions` + `increment_activation` + `save_episode` |
| `am_query_index`  | Same as am_query                                | Same as am_query                        |
| `am_batch_query`  | Same as am_query (amortized across queries)     | Same as am_query                        |
| `am_activate_response` | Drift + activation on occurrences, Kuramoto coupling | `save_occurrence_positions` + `increment_activation` |
| `am_salient`      | Adds 1 neighborhood to conscious_episode         | `save_neighborhood` (into conscious episode) |
| `am_ingest`       | Adds 1 new episode                               | `save_episode` (single new episode)     |
| `am_buffer` (flush) | Drains buffer, adds 1 new episode              | `drain_buffer` + `save_episode`         |
| `am_import`       | Replaces entire system                           | Full `save_system` (correct here)       |
| `am_feedback`     | Drift on occurrences                             | `save_occurrence_positions`             |

### Granular operations that already bypass save_system

| Method                      | What it writes                        |
|-----------------------------|---------------------------------------|
| `increment_activation`      | Single occurrence activation_count    |
| `mark_superseded`           | Single neighborhood superseded_by     |
| `save_occurrence_positions` | Batch occurrence position + phasor    |
| `append_buffer`             | Single conversation_buffer row        |
| `drain_buffer`              | Deletes conversation_buffer rows      |
| `forget_episode`            | Cascading delete (episode + neighborhoods + occurrences) |
| `forget_conscious`          | Delete + re-create conscious neighborhoods |
| `forget_term`               | Delete occurrences by word            |
| `gc_pass`                   | Cascading delete by activation floor  |

### CLI commands that call save_system (main.rs)

| Command         | Context                              | Full save acceptable? |
|-----------------|--------------------------------------|-----------------------|
| `am ingest`     | Batch file ingestion                 | Yes (batch operation) |
| `am import`     | Full state replacement               | Yes (bulk load)       |

## Dirty Tracking Strategy

### Option A: Per-episode dirty flags

Add a `dirty: bool` field to `Episode` (serde-skipped). Any mutation that touches an episode's neighborhoods or occurrences sets `dirty = true`. On save, only dirty episodes are written.

**Pros:** Simple model, episode is the natural unit of persistence.
**Cons:** A single activation within a 500-occurrence episode rewrites all 500 occurrences. Coarse granularity.

### Option B: Per-occurrence dirty flags

Track dirty state at the occurrence level. Only write changed occurrences.

**Pros:** Minimal writes for drift/activation operations.
**Cons:** High memory overhead (one bool per occurrence), complex change tracking for additions/deletions within a neighborhood.

### Option C: Operation-based write dispatch (recommended)

Instead of tracking dirty state, have each MCP tool call the specific granular Store method for what it changed. The in-memory `DAESystem` is the authoritative state; SQLite is kept in sync through targeted writes after each mutation.

**Pros:**
- Zero tracking overhead (no dirty flags, no change sets)
- Each write is exactly as large as the mutation
- Already partially implemented (5 of the 9 MCP tools use granular writes for some operations)
- No new schema required
- Easiest migration path: incrementally replace `save_system` calls one tool at a time

**Cons:**
- Each tool must know which Store methods to call (coupling between server.rs and store.rs)
- Crash between in-memory mutation and SQLite write leaves inconsistency (addressed in Consistency section)

### Recommendation: Option C

Option C requires no schema changes, no new abstractions, and can be adopted incrementally by replacing `save_system` calls in individual tools. The coupling concern is manageable because the server already orchestrates both in-memory and SQLite operations.

## New Store Methods Required

To support Option C, the Store needs these additional methods:

### `save_episode(&self, episode: &Episode) -> Result<()>`

Insert a single episode with all its neighborhoods and occurrences. Used by `am_ingest`, `am_buffer` flush, and orphan buffer flush. This is essentially the inner loop of `save_system` extracted as a public method.

```rust
pub fn save_episode(&self, episode: &Episode) -> Result<()> {
    let tx = self.conn.unchecked_transaction()?;
    self.save_episode_on(&tx, episode)?;
    tx.commit()?;
    Ok(())
}
```

The private `save_episode_on` already exists and handles the nested inserts. This is a one-line wrapper.

### `save_conscious_neighborhood(&self, episode_id: Uuid, neighborhood: &Neighborhood) -> Result<()>`

Append a single neighborhood (with its occurrences) to the conscious episode. Used by `am_salient`.

```rust
pub fn save_conscious_neighborhood(
    &self,
    episode_id: Uuid,
    neighborhood: &Neighborhood,
) -> Result<()> {
    let tx = self.conn.unchecked_transaction()?;
    self.save_neighborhood_on(&tx, &episode_id.to_string(), neighborhood)?;
    tx.commit()?;
    Ok(())
}
```

### `batch_increment_activation(&self, occurrence_ids: &[Uuid]) -> Result<()>`

Batch version of `increment_activation` for query paths that activate many occurrences at once. Wraps all updates in a single transaction.

## Schema Changes Required

None for the initial implementation. The existing schema supports all granular operations.

Future consideration: if per-episode dirty tracking (Option A) is ever needed as a fallback, add:

```sql
ALTER TABLE episodes ADD COLUMN dirty INTEGER NOT NULL DEFAULT 0;
```

This is not needed for Option C.

## Migration Path

The migration is purely a code change with no schema migration. Each step is independently shippable:

### Phase 1: Extract save_episode (low risk, high impact)

1. Make `save_episode` a public method on Store (one-line wrapper around existing `save_episode_on`)
2. Replace `save_system` in `am_ingest` server tool: after `system.add_episode(episode)`, call `store.save_episode(&episode)` instead of `store.save_system(system)`
3. Same for `am_buffer` flush path and orphan buffer flush

This eliminates full rewrites for the two most common write operations (ingestion and buffer flush).

### Phase 2: Targeted writes for query/activation paths

1. Add `batch_increment_activation` to Store
2. In `am_query`/`am_query_index`/`am_batch_query`: after drift and activation, call `save_occurrence_positions` for drifted occurrences and `batch_increment_activation` for activated occurrences instead of `save_system`
3. Same pattern for `am_activate_response` and `am_feedback`

This eliminates full rewrites for the read-heavy query path (the hottest path in MCP usage).

### Phase 3: Targeted write for salient

1. Add `save_conscious_neighborhood` to Store
2. In `am_salient`: after `add_to_conscious` / `extract_salient`, call `save_conscious_neighborhood` for each new neighborhood instead of `save_system`

### Phase 4: Remove save_system from MCP hot path

After phases 1-3, the only `save_system` callers are:
- `am_import` (correct, full state replacement)
- CLI `am ingest` (batch, acceptable)
- `BrainStore::mark_salient` (can be migrated to targeted write)

`save_system` remains as a bulk operation for import/migration scenarios.

## Consistency Guarantees

### Current model

`save_system` is transactional: it wraps all DELETEs and INSERTs in a single `unchecked_transaction`. If the process crashes mid-write, SQLite's WAL journaling rolls back to the pre-write state. The in-memory `DAESystem` and SQLite are always either both updated or neither.

### Incremental model

With Option C, each tool performs:
1. Mutate in-memory `DAESystem`
2. Write targeted changes to SQLite

If the process crashes between steps 1 and 2, the in-memory state is lost (process died) and SQLite retains the pre-mutation state. On restart, `load_system` reads from SQLite, so the mutation is lost. This is acceptable: the system operates under an "at-most-once" persistence guarantee for any given tool call. The MCP client (Claude Code) will re-issue the tool call on the next session.

If the process crashes during step 2 (mid-transaction), SQLite's WAL journaling rolls back the partial write. The in-memory state is lost. Same recovery as above.

### Invariant to maintain

The critical invariant: **SQLite must never contain data that the in-memory DAESystem does not have.** This holds because:
- Writes always go in-memory first, then to SQLite
- `load_system` reads everything from SQLite into memory
- Granular writes (save_episode, save_occurrence_positions, etc.) only add or update data that exists in the in-memory system

The one exception: `append_buffer` and `drain_buffer` operate on the `conversation_buffer` table, which is not part of `DAESystem`. This is already handled correctly and does not change.

## Trade-offs: Complexity vs. Performance Gain

### At current scale (~100 episodes, ~5k occurrences)

Full `save_system` takes ~5-15ms. No user-perceptible latency. Incremental persistence provides no visible benefit.

### At 1,000 episodes (~50k occurrences)

Full `save_system` estimated at ~100-300ms (DELETE 50k rows + INSERT 50k rows). Perceptible as MCP tool response latency. Incremental persistence reduces query-path writes to ~1-5ms (batch UPDATE on ~100 drifted occurrences).

**Estimated speedup: 50-100x on query path.**

### At 10,000 episodes (~500k occurrences)

Full `save_system` estimated at ~1-3s. Unacceptable for interactive MCP usage. Incremental persistence keeps write latency constant at ~1-10ms regardless of total system size.

**Estimated speedup: 100-1000x on query path.**

### Complexity cost

- Phase 1: ~20 lines of code change. Trivial.
- Phase 2: ~50 lines. Moderate. Requires collecting drifted occurrence IDs from the query engine, which currently does not expose them.
- Phase 3: ~15 lines. Trivial.
- Total: ~85 lines of net new code, replacing ~12 `save_system` calls with targeted writes.

The complexity cost is low relative to the scaling benefit. The primary risk is Phase 2, which requires the query engine to return a manifest of what it changed. This is a clean API improvement regardless of the persistence strategy.

## Open Questions

1. **Query engine change manifest:** `QueryEngine::query` and related functions currently mutate the `DAESystem` in place without reporting which occurrences were drifted or activated. Phase 2 requires them to return `Vec<Uuid>` of changed occurrence IDs. This is a design change to am-core's query module.

2. **Kuramoto coupling scope:** `apply_kuramoto_coupling` modifies occurrence positions across multiple neighborhoods. The set of affected occurrences is determined by the coupling algorithm. This needs to be surfaced for targeted persistence.

3. **Conscious episode management:** The conscious episode is append-only for neighborhoods but the `forget_conscious` operation deletes selectively. The current `save_conscious_neighborhood` proposal handles the append case. Deletion is already handled by `forget_conscious` (granular method exists).

4. **Benchmarking:** Before implementation, add criterion benchmarks for `save_system` at 100, 1000, and 10000 episodes to validate the performance model and measure the actual improvement.
