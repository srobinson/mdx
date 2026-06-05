---
title: Transport Matters Resume Feasibility Brainstorm
type: research
tags: [transport-matters, spaces, slice7, native-resume, continuation]
summary: Native resume is feasible by rebuilding a harness native session home from Transport Matters Tier 1 transcript snapshots, while internal continuation remains a separate fork model.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-22
updated: 2026-06-22
---

# Executive Summary

Native resume is feasible, but only if Transport Matters treats the harness native session home as state that can be rehydrated from its owned transcript snapshot. The strongest Slice 7 shape is a durable resume home materialized from Tier 1 on reopen, launched through a harness neutral resume strategy, with internal continuation kept as a separate child session path.

Verified against `main` at `3be3c61` on 2026-06-22. The repo is fmm indexed via `.fmm.db`, and checks used `api/.venv/bin/python` 3.14.5.

# Current Ground Truth

## Process and run lifecycle

`RunManager` is process resident. It keeps live runs in an in memory `_runs` dict, registers a run only after capture preparation, and stores terminal state in process memory. On FastAPI lifespan shutdown, `main.lifespan` closes the run manager, and `RunManager.close()` force tears down every non terminal run with `reason="shutdown"`.

Evidence:

- `api/src/transport_matters/run_manager.py:126` stores `_runs: dict[str, ManagedRun]`.
- `api/src/transport_matters/run_manager.py:198` registers the run in `_runs` after `prepare_request` succeeds.
- `api/src/transport_matters/run_manager.py:275` to `279` marks the manager closed and tears down active runs.
- `api/src/transport_matters/main.py:221` creates one manager on `app.state`; `api/src/transport_matters/main.py:227` closes it in lifespan cleanup.

Implication: desktop quit cannot preserve a live run. Slice 7 should re spawn a new process from the pane's durable `sessionId`, not try to attach to a dead `runId`.

## Tier 1 transcript ownership

The durable run path is derived from workspace identity and run id:

- `api/src/transport_matters/workspace.py:71` to `80`: `workspace_root(cwd)` is `{slug}/{hash}` under the workspaces root.
- `api/src/transport_matters/workspace.py:83` to `92`: `run_root(cwd, run_id)` is `{slug}/{hash}/{run_id}`.
- `api/src/transport_matters/storage/disk_layout.py:69` to `72`: transcript snapshots live under `<run_dir>/transcripts`.
- `api/src/transport_matters/storage/disk_layout.py:74` to `81`: the per session snapshot is `<run_dir>/transcripts/<session_id>.jsonl`.

The transcript tailer copies consumed native transcript bytes into Tier 1 before normalization. This matters because resume needs native bytes, not only normalized Postgres events.

Evidence:

- `api/src/transport_matters/index/tailer.py:378` to `385`: consumed bytes are written to the snapshot writer before the record to event loop.
- `api/src/transport_matters/storage/transcript_snapshot.py:41` to `73`: the writer appends a byte faithful prefix and rejects gaps.

Implication: Tier 1 is a viable seed for rebuilding the harness native session file.

## Native home is currently disposable in captured runs

Captured runs materialize runtime homes under the per run storage directory. `build_captured_run_context()` sets `runtime_home_root = prepared.resolved_storage / "runtime-home"`; when it materializes an overlay it registers `shutil.rmtree(runtime_home_root, ignore_errors=True)` on the resource stack.

Evidence:

- `api/src/transport_matters/captured_run_context.py:100` selects the runtime home root under the run dir.
- `api/src/transport_matters/captured_run_context.py:110` to `116` materializes the overlay and schedules deletion.
- `api/src/transport_matters/cli/runtime_home.py:196` to `207` maps an overlay to `<runtime_home_root>/<harness>`.

Implication: preserving `runtime-home` as currently built is not enough unless Slice 7 intentionally changes its lifetime or rebuilds it on demand.

## Session schema and anchors

The older resume audit said `session_purpose` and `session_visibility` were absent. That is stale on current `main`.

Present now:

- `SessionRow.native_session_id`: `api/src/transport_matters/session/models.py:72`.
- `SessionRow.parent_session_id`: `api/src/transport_matters/session/models.py:82`.
- `SessionRow.forked_at_seq`: `api/src/transport_matters/session/models.py:83`.
- `SessionRow.session_purpose` and `SessionRow.session_visibility`: `api/src/transport_matters/session/models.py:78` to `79`.
- Migration adding purpose and visibility: `api/migrations/versions/0004_session_purpose_visibility.py:18` to `38`.
- Spaces migration adding `session.space_id` and `session.worktree_id`: `api/migrations/versions/0006_spaces_foundation.py:84` to `104`.
- `SessionRow.home_dir` and `template_provenance`: `api/src/transport_matters/session/models.py:75` to `76`.

The session store can already persist these fields through the writer:

- `api/src/transport_matters/session/dao_statements.py:3` to `28`: session columns include the current anchors.
- `api/src/transport_matters/session/dao_statements.py:58` to `94`: upsert writes and preserves them.

Implication: the core DB migration for Slice 7 can be small. The missing durable piece is the native resume state contract, rather than the lineage columns: how a pane session id maps to a rehydratable native home and native launch intent.

## Native id and public session id

For Claude, the native id is the stored session id. For Codex, the native id is kept separately and the stored session id is synthesized from run id, provider, and native id.

Evidence:

- `api/src/transport_matters/index/adapters/claude.py:80` to `97`: Claude bind uses `run.native_session_id` as `session_id`.
- `api/src/transport_matters/index/adapters/codex.py:48` to `67`: Codex bind synthesizes `session_id` while keeping `native_session_id`.
- `api/src/transport_matters/api/v1/run_routes.py:409` to `414`: run views derive `sessionId` the same way, using `synth_session_id` for Codex.

Implication: a pane's `sessionId` must be the TM session id. Native resume lookup then reads `SessionRow.native_session_id` internally.

# Mechanism A: Preserve the Whole Native Home

## Shape

During the original captured run, place the harness child home under a durable per session path, for example:

```text
~/.transport-matters/session-homes/{owner}/{session_id}/{harness}/
```

Do not schedule that directory for deletion when the lease closes. On reopen, pass the same home to the child process and launch the harness with its native resume flag.

Current code seam:

- Change `build_captured_run_context()` so native resume capable runs can choose a durable `runtime_home_root`, rather than always `prepared.resolved_storage / "runtime-home"`.
- Change cleanup so `CapturedRunLease.close()` does not delete a durable session home.

## Pros

- Highest fidelity. The harness sees the same session files, config files, caches, and local metadata.
- Lowest reconstruction complexity after first launch.
- Works even if Tier 1 snapshot lags the native file at process death, provided the home itself survived.

## Cons

- Disk and secret retention are larger. Whole homes can include auth, caches, logs, MCP state, hooks, and unrelated local files.
- Template updates become ambiguous. A resumed session may carry old template content even when the selected runtime template changed.
- Per harness coupling is broad because each harness home layout becomes durable product state.
- This conflicts with the current ephemeral overlay cleanup design, which deliberately deletes `runtime-home` on lease close.

## Correctness risk

Strong replay correctness, weaker operational cleanliness. This mechanism is attractive as a fallback for harnesses whose native resume depends on unknown home files beyond the transcript, but it should not be the default until retention and redaction policy are explicit.

# Mechanism B: Rehydrate a Native Resume Home from Tier 1

## Shape

Keep ordinary runtime homes disposable. On native resume, build a fresh TM owned resume home from durable state:

```text
~/.transport-matters/resume-homes/{owner}/{session_id}/{harness}/
```

Materialize only the files the harness needs for native resume:

1. Read `SessionRow` by pane `sessionId` and owner.
2. Derive the original Tier 1 snapshot path from `workspace_slug`, `workspace_hash`, `run_id`, and `session_id`.
3. Copy or symlink `<run_dir>/transcripts/<session_id>.jsonl` into the harness native location inside the resume home.
4. Launch a new run with the resume home and the native resume flag.
5. Attach the new `runId` to the pane's `runKey`, while retaining the same `sessionId` anchor.

Harness specific materialization:

- Claude expects the transcript at `projects/<claude cwd slug>/<native_session_id>.jsonl`. The slug logic is already centralized in `claude_transcript_source()` at `api/src/transport_matters/index/adapters/claude.py:43` to `73`.
- Codex expects rollout files under `sessions/YYYY/MM/DD/rollout-<wallclock>-<uuid>.jsonl`. The path builder is `codex_rollout_path()` at `api/src/transport_matters/cli/codex_session.py:56` to `63`; matching by native id is `api/src/transport_matters/index/adapters/codex.py:145` to `151`.

For Codex, prefer preserving the original relative rollout path from `source_descriptor` when present. If that path was under an ephemeral home, translate only the home prefix to the new resume home. If no descriptor exists, create a minimal rollout path with `seed_codex_session()` and append or replace it with the Tier 1 snapshot.

## Pros

- Keeps TM's source of truth clear. Tier 1 remains the rebuild seed.
- Avoids retaining a whole harness home indefinitely.
- Lets Slice 7 share the existing runtime template and auth overlay machinery while treating the transcript as durable session state.
- Handles current process resident RunManager reality: every reopen is a new run.

## Cons

- Requires exact per harness mapping from TM snapshot to expected native file path.
- Resume will fail if the snapshot is incomplete at the moment of quit. The tailer currently writes consumed bytes atomically with session event advancement, but a hard kill can still race the native CLI's final write.
- Symlinks may be brittle on Windows if the desktop eventually supports it. Copies are safer, at the cost of duplication.
- Claude and Codex differ in how native ids bind to stored session ids, so the backend must own lookup, not the UI.

## Correctness risk

Medium and manageable. The key property is that the Tier 1 transcript snapshot is byte faithful. The risky part is not normalized replay. The risky part is whether the native CLI accepts a reconstructed home that contains only the transcript plus required skeleton directories. That can be proven per harness with smoke tests.

# Mechanism C: Re seed a New Native File from Postgres Events

## Shape

Ignore the Tier 1 native transcript snapshot. Reconstruct a plausible native transcript from `session` plus `event` rows, write that into a fresh home, then invoke native resume.

## Pros

- Uses the active session store, which already powers list, preview, and continuation APIs.
- Enables transforms, filtering, and repair if native formats evolve.
- Could recover if Tier 1 transcript snapshots are missing but normalized events exist.

## Cons

- Loses native fidelity. The event model omits records the harness file may need, and normalized IR is not guaranteed to round trip into native transcript syntax.
- Replayed context can drift from what the CLI recorded, which undermines the purpose of native resume.
- Much more per harness coupling than Mechanism B.

## Correctness risk

High. This is useful as a disaster recovery path or import tool, not as the first native resume mechanism.

# Recommendation

Build Mechanism B first: a Tier 1 rehydrated native resume home. Keep Mechanism A as an explicit fallback if a harness proves it needs non transcript home state. Avoid Mechanism C for native resume unless Tier 1 is unavailable and the UI clearly labels the result as recovery.

This recommendation preserves the current product model:

- RunManager remains process resident.
- Desktop quit kills live runs.
- The pane persists `sessionId` and worktree identity.
- Reopen spawns a new run that points the native harness at reconstructed local state.
- Internal continuation remains a new child session with lineage, not the same session.

# Harness Native Flag Mechanics

## Existing launch behavior

`LaunchProfile` already owns per harness session mechanics:

- `prepare_managed_session()` mints a native session id and delegates to the profile at `api/src/transport_matters/cli/launch_profile.py:223` to `254`.
- Claude prepare computes the transcript descriptor but does not seed a file: `api/src/transport_matters/cli/launch_profile.py:117` to `137`.
- Codex prepare seeds the initial rollout file: `api/src/transport_matters/cli/launch_profile.py:163` to `185`.
- Current Claude argv with an owned id is `claude --session-id <id>`: `api/src/transport_matters/cli/launch_profile.py:139` to `149`.
- Current Codex argv with an owned id is `codex ... resume <id>`: `api/src/transport_matters/cli/launch_profile.py:187` to `206`.

A Python check confirmed this on current main:

```text
CLAUDE_ARGV ['claude', '--session-id', 'sid']
CODEX_ARGV ['codex', ..., 'resume', 'sid']
```

## Required Slice 7 change

Add an explicit launch intent to the harness neutral seam. Do not overload `native_session_id` alone because the same id currently means "start a managed new Claude session" for Claude and "resume the pre seeded Codex rollout" for Codex.

Suggested model:

```python
@dataclass(frozen=True)
class NativeResumeIntent:
    session_id: str              # TM session id from the pane
    native_session_id: str       # SessionRow.native_session_id
    transcript_snapshot: Path    # Tier 1 source
    resume_home_dir: Path        # Rehydrated child home

class LaunchProfile:
    def prepare_resume(..., intent: NativeResumeIntent, write: bool) -> str: ...
    def resume_argv(..., native_session_id: str, bypass_permissions: bool) -> list[str]: ...
```

Per harness:

- Claude native resume uses `--resume <native_session_id>`. The existing `--session-id` path remains for newly minted sessions.
- Codex native resume uses `resume <native_session_id>`. This shares the current command shape, but the native id comes from `SessionRow.native_session_id` instead of a newly minted id.

Runtime template capability seam:

- Add a capability key such as `native_resume` or a structured `resume` section to runtime template capabilities.
- Keep the actual flags in `LaunchProfile`; templates should declare compatibility, not duplicate argv syntax.
- A template can opt out if its home policy cannot support resume.

# Required Product and Code Changes

## Backend run API

Add a native resume request to the run creation API. A minimal shape:

```json
{
  "harness": "claude",
  "worktreeId": "...",
  "nativeResume": { "sessionId": "..." },
  "idempotencyKey": "pane-run-key-or-new-resume-key"
}
```

Backend behavior:

1. Resolve `sessionId` owner scoped from Postgres.
2. Require `native_session_id` and `harness` on the session row.
3. Validate requested `worktreeId` matches the pane or session worktree, unless the user explicitly chooses another worktree in a later design.
4. Materialize the resume home from Tier 1.
5. Spawn a new `ManagedRun` with a new `run_id`, new storage dir, same TM `sessionId`, and native resume argv.

This should be a run spawn, not a session mutation. The session row already represents the native transcript line; the new run is another process attached to that line.

## Run lifecycle

Change the reopen path from "attach old run id" to "attach if alive, otherwise resume by session id".

Current client state persists `runKey -> runId` only:

- `www/src/session-canvas/model/capturedRunStore.ts:9` to `19`: `CapturedRunRecord` stores provider, runId, and minimized.
- `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx:40` to `50`: the pane seeds from persisted runId and calls `ensureRun()`.

Slice 7 should persist both:

```ts
interface CapturedRunRecord {
  provider: HarnessName;
  runId?: string;
  sessionId?: string;
  minimized?: boolean;
}
```

Reopen behavior:

- If `runId` exists and `/runs/{runId}` or terminal attach succeeds, attach.
- If it returns `run_not_found`, `run_stale`, `run_terminated`, or `run_not_attachable`, and the pane ref has `sessionId`, call native resume spawn.
- If no `sessionId` exists, treat it as an unrecoverable legacy captured run pane and show a transcript or restart affordance.

## Session id population

The API already has the value for managed launches:

- `RunViewModel.session_id`: `api/src/transport_matters/api/v1/run_routes.py:115`.
- `run_view_model()` sets it at `api/src/transport_matters/api/v1/run_routes.py:424` to `439`.

The frontend discards it today:

- `www/src/api.ts:457` requests only `{ run: { runId: string } }`.
- `www/src/api.ts:467` returns only `response.run.runId`.
- `www/src/session-canvas/model/spawn.ts:31` to `46` creates captured run refs without `sessionId`.
- The persisted ref allows `sessionId?: string`: `www/src/session-canvas/model/paneRecords.ts:170` to `178`.

Population options:

1. First class response path: make `createCapturedRun()` return `{ runId, sessionId }`; store both in `CapturedRunRecord`; add a canvas store action that patches matching captured run refs with `sessionId` by `runKey`. This is simplest for current managed Claude and Codex.
2. Bind event path: add an `on_session_bound` event from the backend when the tailer registers a `SessionBinding`. This handles future harnesses where the id is discovered only after wire traffic. The shared proxy already has an `on_session_bound` seam via `register_owned_cursor()` in `api/src/transport_matters/addon_runtime.py:196` to `220`.
3. Poll path: after spawn, call `GET /v1/runs/{runId}` until `sessionId` becomes stable. This is simpler than SSE but worse latency and more UI state.

Recommendation: use option 1 immediately, with option 2 as the general fallback. Avoid option 3 unless implementation time is the only constraint.

## Schema

Required for basic Mechanism B: no new session table columns.

Already present and verified:

- `native_session_id`.
- `parent_session_id`.
- `forked_at_seq`.
- `session_purpose` and `session_visibility`.
- `space_id` and `worktree_id`.
- `run_id`, `workspace_slug`, and `workspace_hash`, enough to derive the Tier 1 snapshot path.
- `home_dir`, `source_descriptor`, and `template_provenance`, useful for translating original native paths into resume homes.

Potential additions if desired:

- A small `session_resume_state` table or JSON manifest keyed by `session_id` with `resume_home_dir`, `last_materialized_at`, `snapshot_size`, and `materialization_error`. This is observability and caching, not required for correctness.
- A `run.parent_session_id` column is not needed because run metadata already points at the session row. Keep lineage on `session`.

# Internal Continuation Feasibility

Internal continuation is already partially implemented and more feasible than native resume because it does not require harness native files.

Current support:

- `CreateRunRequest.continue_from_session_id`: `api/src/transport_matters/api/v1/run_routes.py:103`.
- `_launch_fields()` validates the parent and builds continuation metadata: `api/src/transport_matters/api/v1/run_routes.py:339` to `362`.
- `build_continuation_launch_fields()` sets `parent_session_id`, `forked_at_seq`, `session_purpose="continuation"`, and a `resume_context`: `api/src/transport_matters/api/v1/run_continuation.py:28` to `61`.
- `build_session()` persists lineage fields into `SessionRow`: `api/src/transport_matters/session/ingest.py:69` to `97`.
- Session list views include purpose, visibility, lineage, current turn count, inherited turn count, and last message preview: `api/src/transport_matters/api/v1/session_models.py:56` to `73`.

Gaps:

- The agent still needs a way to read the prior session beyond the initial `resume_context`. Candidate tools: session timeline fetch, search, artifact fetch, and lineage inspect.
- The UI needs a clear action and copy for "continue from this session".
- The run launch path should pass `continueFromSessionId` from the UI or director agent rather than treating it as native resume.

Product distinction:

- Native resume: same native session id, harness replay from native transcript, best for desktop quit and reopen.
- Internal continuation: new session row with parent lineage and read prior session tooling, best for branching, summarizing, and deliberate fork workflows.

# Open Questions

1. Does Claude `--resume <id>` accept a reconstructed `CLAUDE_CONFIG_DIR` that contains only `projects/<slug>/<id>.jsonl` plus the usual auth source? Smoke test required.
2. Does Codex `resume <id>` search all `CODEX_HOME/sessions/**/rollout-*-<id>.jsonl`, or does it require the original date path? Current adapter locate searches recursively, but Codex CLI behavior must be verified.
3. Should the resume home use symlinks to Tier 1 snapshots or copies? Copies are safer across platforms. Symlinks preserve single source bytes.
4. How should hard quit be handled when the native file has bytes not yet copied into Tier 1? Options: drain on graceful shutdown, tail final bytes before lease close, or label resume as best effort after crash.
5. Should `sessionId` be patched into the pane ref at spawn response time, tailer bind time, or both? Recommendation: both, with spawn response first.

# Suggested Slice 7 Order

1. Add failing tests for captured run pane session id persistence: spawn returns `sessionId`, canvas ref is patched, reload keeps it.
2. Add backend native resume request model and tests for owner scoped lookup, missing native id, worktree mismatch, and Tier 1 snapshot derivation.
3. Add `LaunchProfile` resume strategy methods, with Claude using `--resume` and Codex using `resume`.
4. Implement Tier 1 to resume home materializers for Claude and Codex.
5. Add live smoke tests with real or fake CLI homes proving the resumed process reads prior context.
6. Wire reopen fallback: stale run id plus session id spawns native resume.
