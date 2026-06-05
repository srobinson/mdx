---
title: Tier 2 Slice 4 Sharded Tailer Dispatch
type: sessions
tags: [backend, tailer, session-store, tier2]
summary: Implemented sharded transcript commit dispatch with cursor advancement gated by commit and dead-letter acknowledgement.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-17
---

## Summary

Implemented Tier 2 Slice 4 sharded transcript commit dispatch on `feat/tier2-slice4-sharded-tailer`, PR #134.

Commits:

- `c50d30a`: initial sharded commit dispatcher and commit acknowledgement gated cursor advance.
- `028c535`: review fix round for worker abort handling, async quarantine acknowledgement, and writer pool headroom.

Key decisions:

- Added `SessionWriter.submit()` as the public async boundary around `_commit_batch()`.
- Added `ShardedCommitDispatcher` with bounded per shard queues and one worker per shard.
- Keyed shards by `hash(session_id) % shard_count`.
- Changed `TranscriptTailer` so durable cursor state advances only after a successful `CommitResult`.
- Kept queue pressure non blocking. `CommitQueueFull` clears the pending commit and lets the cursor retry on the next poll.
- Preserved existing `TranscriptTailer.unregister` child cursor cleanup.
- Hardened dispatcher workers so an in flight future is resolved if a worker hits `BaseException`; the shard worker then restarts.
- Added async whole-window quarantine acknowledgement through `SessionWriter.quarantine_window()` and `TranscriptTailer.pending_quarantine`.
- Reserved one writer pool connection for auxiliary dead-letter inserts by setting dispatcher shard count to `session_pool_max_size - 1` and enforcing `Settings.session_pool_max_size >= 2`.

## API Contract

No public HTTP or websocket API changes.

Internal backend contracts changed:

```python
class SessionWriter:
    async def submit(self, batch: EventBatch) -> CommitResult: ...
    async def quarantine_window(
        self,
        binding: SessionBinding,
        source_path: str,
        byte_start: int,
        byte_end: int,
        raw_excerpt: bytes,
        exc: BaseException,
        attempts: int,
    ) -> bool: ...
```

```python
class ShardedCommitDispatcher:
    def submit(self, batch: EventBatch) -> Future[CommitResult]: ...
    async def aclose(self) -> None: ...
```

`TranscriptTailer` submit callbacks may return a `Future`. When a commit future is returned, the cursor stores pending commit state and waits for acknowledgement before advancing byte offsets or sequence state.

`TranscriptTailer` quarantine callbacks may return `bool` or `Future`. When a quarantine future is returned, the cursor stores pending quarantine state and advances only after the dead-letter write acknowledges successfully.

## Database Changes

No schema or migration changes.

The existing session writer commit path remains the database write path for transcript event batches. Whole-window quarantine uses the existing dead-letter table via `SessionWriter.quarantine_window()`.

## Security Considerations

No new public input boundary was added.

Defense in depth notes:

- The dispatcher is bounded to prevent unbounded memory growth under backpressure.
- Commit worker concurrency is capped below the configured session pool size, leaving one connection for auxiliary dead-letter writes.
- Cursor advancement is tied to successful durable commit or dead-letter acknowledgement, reducing data loss risk under transient database failures.
- Existing quarantine classification remains the poison record and poison window escape hatch after repeated commit failures.

## Performance Notes

- Sharded queues remove cross session head of line blocking while preserving per session commit order.
- Queue full behavior skips only that cursor for the current poll and does not block other cursors.
- Async whole-window quarantine prevents poison dead-letter writes from blocking the single tailer thread.
- Worker abort handling resolves the in flight cursor future and restarts the shard worker so retry can proceed.
- `tailer.py` remains under the 700 line project threshold.

Verification:

- Fail first focused tests before the fix round: 3 failed, `EXIT=1`.
- Focused related tests after fixes: `23 passed`, `EXIT=0`.
- `cd api && just check`: pass, `EXIT=0`.
- `cd api && just test`: pass, `1477 passed in 33.47s`, `EXIT=0`.
- `fmm validate`: pass, all 787 files indexed and up to date, `EXIT=0`.
- `git diff --check`: pass, `EXIT=0`.

## Open Items

- No open implementation items for Slice 4.
- Future tuning may expose a dedicated queue size setting if production telemetry shows the pool sized default is too small or too large.
