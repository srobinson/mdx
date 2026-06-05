# Backend review: Transport Matters Desktop Cockpit

Reviewer: backend-engineer/codex
Scope: charter v2 plus `spec-backend.md`
Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`, `main` at `d8b944a`

## Findings

1. **High: the transcript timeline contract is lossy, so Pane 1 and artifact detection are not grounded in the existing REST surface.**

   `spec-backend.md:20-21` and `spec-backend.md:471` claim the existing tier 2 transcript IR and `GET /api/index/sessions/{session_id}/timeline?stream=transcript&with_bodies=true` can render transcript IR. The code says otherwise. `api/src/transport_matters/api/v1/index_routes.py:108-121` calls `session_timeline`; `api/src/transport_matters/index/queries.py:236-283` returns `TimelineEntry` values; `_edge_blocks` at `api/src/transport_matters/index/queries.py:325-346` only joins `block.text` and `block.identity_canonical` when `with_bodies` is true. `TimelineBlock` at `api/src/transport_matters/index/models.py:157-167` has `pos`, `block_id`, `role`, optional `section`, `text`, and `identity_canonical`. There is no typed `ContentBlock` body, no `kind` in the timeline block, no `ToolUseBlock.input`, no `ToolResultBlock.content`, and no `ImageBlock.source`. The `block.text` projection is explicitly FTS text, `api/src/transport_matters/index/blocks.py:113-124`. The `block` table also only persists `kind`, `text`, and `identity_canonical`, `api/src/transport_matters/index/schema.py:41-48`.

   Current truth for the contested surface: `with_bodies=true` returns a text projection plus an identity string, not full `ContentBlock` IR.

   Impact: the transcript pane cannot be a premium typed IR renderer from the existing timeline, and artifact detection cannot recover `Write` or `Edit` paths from that route. Sections 7.1 and 8.1 to 8.2 need to stop treating the timeline as full IR. If artifacts are derived in ingest from `NormalizedTurn.parts`, say that explicitly and keep the classifier on the pre projection object. If the frontend needs full transcript IR, add a new read contract or persist typed block JSON.

2. **High: the artifact event delivery plan overstates the current `IndexJob.event` seam.**

   `spec-backend.md:567-574` says artifact events ride the existing post commit emit seam and attach resulting `ArtifactEvent` dicts to the transcript job. Current `IndexJob` has a single `event: dict[str, Any] | None` field, `api/src/transport_matters/index/writer.py:29-43`, and `_emit_events` emits at most that one dict per applied job, `api/src/transport_matters/index/writer.py:192-201`. `build_transcript_job` already uses that one slot for `{"type":"transcript_turn", ...}`, `api/src/transport_matters/index/ingest.py:355-373`. A transcript turn can yield multiple artifacts.

   Impact: the current seam cannot preserve the existing transcript live push and emit N artifact events without changing the writer contract. A naive slice 3 implementation either replaces `transcript_turn`, drops artifacts after the first, or emits before durability through a side channel. Update the spec to extend the writer contract, for example `events: tuple[dict[str, object], ...]`, and add acceptance tests that one committed turn emits the transcript event plus multiple artifact events, while a rolled back job emits none. If dedupe on `(session_id, turn_id, tool_use_id)` remains required, add storage or query logic for that key, because the current idempotent upsert still emits the event on each processed job.

3. **Medium: the PTY token storage claim is not grounded and weakens the input surface.**

   `spec-backend.md:743-748` requires a per run token and says manifest POSIX perms keep it off other users. Current manifest writes are `path.parent.mkdir(parents=True, exist_ok=True)`, `tmp.write_text(...)`, then `tmp.replace(path)`, `api/src/transport_matters/manifest.py:55-66`. No mode is set. `WorkspaceLock` creates the run dir with default `mkdir` and the lock as `0o644`, `api/src/transport_matters/lock.py:96-104`. With a normal umask, the manifest can be `0644`. The proposed registry also returns `desktop_token`, `spec-backend.md:444-447`, which makes an unauthenticated registry read sufficient to attach to the keyboard socket.

   Impact: the PTY is the highest risk surface in this design, and the token may be readable by local users or by any caller allowed to read the registry. Either keep the token out of the manifest and only return it on the spawning stdout channel to Electron main, or harden storage with `0700` directories plus `0600` atomic writes and do not expose the token through read only registry routes. Add a test that the token file mode is private if persisted.

## Positive checks

- The per agent launcher process choice is well grounded in the existing per run isolation model.
- The public wrapper plan for `_build_start_invocation` and `_build_codex_invocation` correctly avoids the private import boundary.
- The Python PTY choice is the right reuse seam. Node side spawning would duplicate launch and proxy policy.
