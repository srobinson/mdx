# Session Store Spec Review

Reviewer: backend-engineer/codex. One adversarial pass against repo grounding.

## Findings

1. Blocker: Forked Claude events cannot keep source turn ids while also using regenerated event ids.

   The spec defines `event.event_id` as `NormalizedTurn.turn_id` for turns, or `uuid5(session_id|seq)` only for meta rows (`spec-session-store.md:127-130`, `spec-session-store.md:226-233`). Current Claude normalization makes `turn_id` the native transcript `uuid` (`api/src/transport_matters/index/adapters/claude.py:114-120`). Fork then copies `raw` and `ir` into a new session under regenerated `event_id`s (`spec-session-store.md:387-389`). That creates three incompatible identities for one row: the new `event_id`, the old `ir.turn_id`, and the old `raw.uuid`. If the reconstructed fork transcript is tailed later, Claude normalization emits the old `uuid` again, colliding with the source session primary key or creating duplicate fork rows. `parentUuid` and `ir.parent_id` also keep pointing at the source graph.

   Required correction: make fork rekeying provider aware. For Claude, either rewrite `raw.uuid`, `raw.parentUuid`, `raw.sessionId`, `ir.turn_id`, `ir.parent_id`, and `event_id` consistently, or make the primary key `(session_id, seq)` and store provider turn ids as non global fields. Codex can keep seq derived ids because its adapter already derives `turn_id` from `session_id|seq` (`api/src/transport_matters/index/adapters/codex.py:92-100`).

2. Blocker: The raw JSONB resume proof is asserted but not demonstrated.

   The charter explicitly asked the panel to verify whether the stored raw CLI record suffices for fork. The spec states that JSON reserialization is resume faithful and byte identity is unnecessary (`spec-session-store.md:380-385`, `spec-session-store.md:600-604`). The cited repo evidence proves a different property: tier 1 byte faithful snapshots can rebuild the SQLite projection (`api/src/transport_matters/storage/transcript_snapshot.py:41-73`, `api/src/transport_matters/index/rebuild.py:71-101`). `iter_complete_records` parses bytes into dicts and skips malformed complete lines (`api/src/transport_matters/index/tailer.py:45-65`); no current proof shows Claude or Codex can resume from Postgres JSONB records reserialized back to JSONL.

   Codex also has an unresolved file write detail. `CodexLaunchProfile.prepare` calls `seed_codex_session`, which writes a `session_meta` line to the target rollout (`api/src/transport_matters/cli/codex_session.py:90-94`). Fork then writes the selected raw rows, which include `session_meta`, to the same owned path (`spec-session-store.md:374-380`, `spec-session-store.md:595-599`). The spec must say whether reconstruction overwrites the seed or appends after it. Appending duplicates `session_meta`; overwriting means `prepare_managed_session(write=True)` performed a write that fork discards.

   Required correction: add provider fork fixtures that reconstruct from stored JSONB raw, write a new transcript or rollout, and prove the provider parser or CLI resume path accepts it. Define Codex seed overwrite versus append. Define which provider ids are rewritten before writing the fork file.

3. Blocker: The durable commit acknowledgement guarantee has no implementable seam in the reused tailer.

   The spec says the tailer submits to an async `SessionWriter` and advances the cursor plus snapshot offset only after a durable writer acknowledgement (`spec-session-store.md:219-224`, `spec-session-store.md:267-269`). Current `TranscriptTailer` is a sync thread. It snapshots bytes, calls `ingest_records(records, cursor, source.path, self._submit)`, then advances `cursor.byte_offset` and `stat_signature` (`api/src/transport_matters/index/tailer.py:196-213`). The existing submit path is fire and forget; `IndexWriter.submit` only queues (`api/src/transport_matters/index/writer.py:86-98`) and the commit happens later (`api/src/transport_matters/index/writer.py:169-190`).

   Retargeting `submit` to an async pool does not by itself produce a durable ack. If the async transaction fails after the tailer advances, live capture skips bytes in Postgres. If the sync tailer blocks on the event loop, the design needs explicit backpressure, timeout, cancellation, and shutdown behavior.

   Required correction: specify one concrete seam, for example a `SessionWriter.submit_blocking(job) -> CommitResult` that is safe from the tailer thread and only returns after commit, or convert the tailer consume loop to async. The retry rule must say exactly when snapshot bytes are considered owned versus when Postgres rows are considered owned.

4. Major: The backfill reuse plan crosses the parked wire boundary and depends on modules the spec deletes.

   The spec parks wire storage (`spec-session-store.md:205-211`) but says Postgres backfill reuses `index/rebuild.py:replay_run` and `backfill` with a Postgres writer target (`spec-session-store.md:286-294`, `spec-session-store.md:482-484`). Actual `replay_run` is not transcript only. It reads `index.jsonl`, reads per exchange wire artifacts, calls `bind_exchange`, and submits `build_wire_job` before replaying transcript snapshots (`api/src/transport_matters/index/rebuild.py:71-101`). The same spec later deletes `index/ingest.py`, `index/writer.py`, `index/rebuild.py`, and related SQLite modules (`spec-session-store.md:486-490`).

   Reusing `replay_run` verbatim would build the parked wire store and keep SQLite job types alive. Deleting it makes the promised reuse unavailable.

   Required correction: extract a transcript replay core that yields `(binding, record, seq, source)` from `sessions.json` plus `transcripts/<session_id>.jsonl` and has no wire artifact reads. Keep `bind_exchange` style session binding logic as a small shared capture helper if live wire metadata remains the trigger for transcript tailing, but do not reuse the SQLite wire rebuild path for a transcript only Postgres backfill.

5. Major: `session_native_uq` removes the run scoped readback identity that the current repo relies on.

   The spec creates `session_native_uq` on `(provider, native_session_id)` (`spec-session-store.md:121-122`). Current SQLite scopes that uniqueness by `run_id` (`api/src/transport_matters/index/schema.py:65-67`), and readback providers synthesize `session_id` from `(run_id, provider, native_session_id)` (`api/src/transport_matters/index/sessions.py:22-28`). In a hosted or importable store, two bundles from different roots can have the same provider native id but distinct run ids and distinct synthesized session ids. The proposed unique index rejects the second import even though the current identity contract permits both.

   Required correction: either keep the uniqueness scope aligned with identity, such as `(run_id, provider, native_session_id)`, or introduce an explicit source instance or owner dimension and prove provider native ids are globally unique across imports, forks, and hosted tenants.

6. Major security and portability gap: artifact path capture lacks a verified source field and a safe root.

   The spec adds `artifact_refs(record, turn)` and then reads `ref.path` into Postgres (`spec-session-store.md:312-338`). It also admits the exact Codex tool record field for `generated_images` still needs confirmation (`spec-session-store.md:647-651`). Without a verified field and path policy, a malformed or malicious transcript can point at arbitrary local files and the ingest path will copy those bytes into the durable store and later export them.

   Required correction: before implementation, ground the exact Codex record shape with fixtures. Restrict artifact capture to explicit safe roots, for example managed Codex home generated image directories or a captured tool specific output directory. Reject symlinks escaping the root, impose a size limit, sniff or validate media type, define missing file behavior, and audit every by value capture. The default adapter hook should not authorize arbitrary absolute paths.

## Final verification

Finding 1: RESOLVED
Finding 2: RESOLVED
Finding 3: RESOLVED
Finding 4: RESOLVED
Finding 5: RESOLVED
Finding 6: RESOLVED
