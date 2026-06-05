---
title: "B6 run-teardown rename (stop → terminate) — blast radius + collision check"
type: review
tags: [transport-matters, b6, naming, rename, blast-radius]
summary: terminate is a GOOD rename (it aligns the API verb with the EXISTING internal terminate_* teardown mechanism); the hazard is a naive find/replace hitting the unrelated, pervasive LLM-protocol `stop_reason`. `interrupt` is NOT free — Codex already has an `interrupted` turn status (compatibly aligned).
status: active
source: codebase-analyst
reviewer: transport-matters:helioy-tools:codebase-analyst:1:3.2
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Rename `stop` → `terminate` (run teardown) — blast radius & collision

Verified at `HEAD 16b95d7`. Citations are `file:line symbol`.

## Headline

- **`terminate` is the right name and READS CONSISTENT** — the internal teardown mechanism is
  *already* `terminate` (`pty_session.py:129 terminate_terminal_pty`, `run_manager.py:486
  _teardown_run(terminate: bool)`). Today the API verb (`stop`) and the internal mechanism
  (`terminate`) disagree; the rename aligns them.
- **The real hazard is a false-positive collision:** there are **two unrelated `stop_reason`
  vocabularies**. The run-teardown one is the rename target; the **LLM/provider `stop_reason`**
  (Anthropic/Codex turn-completion reason) is pervasive and must NOT be touched. A naive
  `stop`→`terminate` sweep corrupts it.
- **`interrupt` is NOT free** — Codex already defines an `interrupted` turn status. Reserving
  `interrupt` for the ESC/turn-halt action is *semantically compatible* (an interrupted turn IS an
  ESC-halted turn), so it is an aligned reuse, not a clean name.

---

## Q1 — Blast radius (three token families; keep them separate)

### Family A — RENAME TARGET: the run-teardown verb

**api (`run_manager.py` + `run_routes.py`):**
- `run_routes.py:338 @router.delete(.../{run_id})` `async def stop_run` → returns
  `StopRunResponse(..., stop_reason="explicit-stop")` (`:350`). (Proposal already moves this to
  `POST /stop`; rename → `POST /terminate`, `terminate_run`.)
- `run_routes.py:111 class StopRunResponse` with `stop_reason: Literal["explicit-stop"]` (alias
  `stopReason`, `:116`).
- `run_routes.py:51 "run_stopped"` HTTP-status map entry; the curated error code `run_stopped`
  (in `RunManagerErrorCode`, `run_manager.py:56-66`) → `run_terminated` if the curated code renames.
- `run_routes.py:98 RunViewModel.stop_reason` (alias `stopReason`) — curated `Run` drops `stopReason`
  per the proposal anyway.
- `run_manager.py:354 RunManager.stop(run_id, *, reason: StopReason="explicit-stop")` — the method
  → `terminate`.
- `run_manager.py:55 StopReason = Literal["explicit-stop","shutdown","idle-timeout","natural-exit","failed"]`.
- `run_manager.py:92 RunState.STOPPING = "stopping"`.
- `run_manager.py:153 / :173 / :206 stop_reason` field (ManagedRunView / ManagedRun / `view()`).
- `run_manager.py:334 if run.stop_reason == "explicit-stop"` (attach guard).
- `run_manager.py:494 / :497 / :503 / :521-522` STOPPING state + `stop_reason` inside `_teardown_run`.

**www:**
- `api.ts:411 stopRun` (`DELETE /api/runs/{runId}`, `:415`) → `POST .../terminate`.
- `api.ts:422 RunState = "...|"stopping"|..."` (literal `"stopping"`).
- `api.ts:444 stopReason?: string` on the run type.
- `session-canvas/model/capturedRunStore.ts:73 stopRun(...)` decl + `:138` impl (zustand action).
- `session-canvas/model/capturedRunLifecycle.ts:15 ...stopRun(ref.runKey)` caller; comment refs in
  `lab/canvasLabStore.ts:230`, `lab/canvasLabTypes.ts:45`.

**tests (same-PR updates):** `www/src/api.test.ts` (asserts `DELETE /api/runs/{id}`, lines ~162-167),
`session-canvas/.../terminalSocket.test.ts`, `CapturedRunPane.test.tsx`, and any api-side
`test_run_*` asserting `stop`/`stop_reason`/`STOPPING`.

**No user-visible label rename:** `absent: rg ">...(Stop|Terminate)...<" www tsx -> 0` — teardown is
the pane-close `[X]` affordance, not a "Stop" button. Rename is identifier/API-level only.

### Family B — DO NOT RENAME: LLM/provider `stop_reason` (the false-positive trap)

This is the wire-protocol turn-completion reason (`end_turn`, etc.), unrelated to run teardown.
A `stop`→`terminate` global replace would wrongly hit all of these:
- api: `ir.py:160`; `adapters/anthropic.py:210,223,281,299` (Anthropic `stop_reason`);
  `codex/protocol.py:72 codex_terminal_stop_reason` / `:306 codex_close_stop_reason`;
  `codex/derivation_engine.py`, `codex/transport.py`, `codex/events.py:103`, `codex/derivation_events.py`;
  `storage/base.py:66,83,98`; `exchange_stats.py`, `exchange_recorder_artifacts.py`,
  `_exchange_recorder_http_support.py:105`.
- www: `types/ir.ts:106`, `types/codex.ts`, `types/exchanges.ts`; `components/ExchangeTurnCard.tsx`,
  `ExchangePreview.tsx`, `detail/ExchangeCard.tsx`, `detail/CodexTimeline.tsx`,
  `hooks/exchangeStreamEvents.ts`.

### Family C — UNRELATED `stop` (leave alone)
- `index/tailer.py:243 TranscriptTailer.stop(drain)` + caller `addon_runtime.py:252 tailer.stop(...)`
  (tailer lifecycle, not run teardown).
- `components/editor/SamplingRows.tsx:116` "before stopping" (max-tokens help text).

---

## Q2 — Collision check

**`terminate` vs internal `terminate_terminal_pty`: CONSISTENT, even improving.**
- `pty_session.py:129 terminate_terminal_pty` → `:136 terminate_process_group` → `:145
  process.terminate()` (SIGTERM) escalating to `:153 os.killpg(SIGKILL)` / `:158 process.kill()`.
- `run_manager.py:38` imports `terminate_terminal_pty`; `_teardown_run` calls it under
  `:514 if terminate:` (`:515`, `:540`). `terminate=True` for `explicit-stop`/`shutdown`
  (`:356,:363`), `terminate=False` for `natural-exit`/`failed` (`:444,:451`).
- So "terminate" already means *forcibly end the run's process group*. Promoting it to the API verb
  matches the mechanism (whereas `stop` does not). **No semantic clash.**

**One wrinkle (minor):** `RunManager.terminate()` would call `_teardown_run(terminate=True)` — the new
method name lexically shadows the existing `terminate: bool` param (`run_manager.py:486`). Rename that
bool to `force`/`kill_pty` to avoid `terminate(..., terminate=True)` reading.

**`interrupt` is already in use (compatibly).**
- `codex/protocol.py:26 CODEX_INTERRUPTED_STATUS = "interrupted"`;
  `codex/events.py:23 CodexTurnStatus = Literal["open","completed","failed","interrupted"]`;
  www `types/codex.ts:53 CodexTurnStatus = "...|"interrupted"`.
- This is a Codex *turn terminal status* (a turn halted mid-flight). Reserving `interrupt` for the
  ESC/turn-halt **action** is consistent with this existing status vocabulary (the action produces an
  `interrupted` turn). So `interrupt` is a sound reservation, but the token is **not free** — expect
  to coexist with the Codex status, and keep the ACTION verb (`interrupt`) distinct from the STATUS
  noun (`interrupted`). No `cancel`/`kill` product verbs exist today (`kill` is internal-only:
  `pty_session.py:153/158`).

---

## Recommendation

1. Rename the **user-facing verb + curated API surface only**: route `/stop`→`/terminate`,
   `stop_run`→`terminate_run`, `StopRunResponse`→`TerminateRunResponse`, `RunManager.stop`→`.terminate`,
   curated error `run_stopped`→`run_terminated`.
2. **Judgment call to surface:** the internal lifecycle vocabulary (`StopReason`, `stop_reason`,
   `RunState.STOPPING`, `"explicit-stop"`) describes *all* teardown incl. `natural-exit`/`failed`, not
   just the user action — renaming it to `terminate_*` reads oddly for non-user exits. Cheapest correct
   move: keep internal lifecycle names, rename only the verb/response/error. If full alignment is wanted,
   `"explicit-stop"`→`"explicit-terminate"` and `RunState.STOPPING`→`TERMINATING` are bounded but ripple
   into www `RunState` (`api.ts:422`).
3. **Never** sweep Family B. Scope any rename to `run_manager.py`/`run_routes.py`/`api.ts`/
   `capturedRunStore.ts`/`capturedRunLifecycle.ts`; the provider `stop_reason` is off-limits.
4. Rename the `_teardown_run(terminate: bool)` param to avoid shadowing the new method.
