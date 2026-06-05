---
title: Launcher Sessions scope (option A) implementation
type: sessions
tags: [frontend, transport-matters, launcher, commandModel, sessions-scope, react, ark-ui]
summary: Turned the Sessions ⌘K launcher scope from a deferred placeholder into a real inline-listing scope that browses transcript history and opens transcripts via the existing canvas path.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-23
updated: 2026-06-23
---

## Summary

Built the **Sessions** launcher scope (NOW.md Current Focus — finish the ⌘K launcher) as
`feat/launcher-sessions-scope` @ `e97fd9d`. Scope-corrected the brief first: **Workdir was
already a real scope** (slice 6, `3be3c61`, #166), so only Sessions remained a
`buildDeferredRows("Sessions")` stub. Orchestrator chose **option A** (inline session list
mirroring Agents/Workdir) over a thin "focus the existing picker pane" row (which would have
duplicated Canvas's "Focus picker").

Key decisions:
- Sessions rows reuse the already-wired `useSessions` → `GET /v1/sessions` → `SessionSummary[]`,
  workspace-scoped exactly like the shipped `SessionPickerPane`, lazy until the palette opens.
- `↵` on a session row opens (or focuses) its transcript through a **new `open-session`
  `LauncherCommand` threaded to the EXISTING `spawnOrFocusTranscript`** canvas-store action — no
  parallel handler. The command carries a trimmed `SpawnSessionDescriptor`, not the full summary.
- Four states (loading skeletons / error+retry / empty / populated) mirror `agentsStatusRows`,
  including a `retry-sessions` effect wired alongside `retry-agents`.

## Architecture Decisions

- **Pure model first.** All row grammar lives in `commandModel.ts` (`buildSessionsRows`,
  `sessionRow`, `sessionsStatusRows`, `sessionSpawnDescriptor`) as deterministic functions of
  inputs, unit-tested in isolation. Subtitles avoid relative-time formatting to stay deterministic
  (`harness · N turns`, not "3h ago").
- **DRY grooming (orchestrator-mandated).** Renamed the agent-specific `AgentsStatus` to a shared
  `FetchStatus` and extracted `deriveFetchStatus(isError, data)`, now reused by
  `useRuntimeTemplates` and the new `useSessionHistory`. Removed the now-unused `buildDeferredRows`.
- **Hook mirror.** New `useSessionHistory(workspaceHash, enabled)` returns `{sessions, status,
  retry}` exactly like `useRuntimeTemplates`. `hooks/useSessions` gained an optional `enabled`
  flag (default true → picker unaffected) to support lazy fetch.
- **Threading.** `CommandCenter` sources `workspaceHash` from the canvas store (same as
  `defaultWorktreeId`) and passes it into `useCommandCenter`, which feeds `useLauncherRows` and the
  action interpreter's effect sink.
- **Function-size decomposition (review round, 150-LoC hard limit).** Two functions the slice
  touched were over 150 (both marginally over before the slice too). Fixed by cohesive extraction,
  not line-slicing: `useCommandCenter` 170→138 via a new `useLauncherInputKeys` hook (Escape-close
  window capture + the input's ArrowRight-advance / ArrowLeft|Backspace-back grammar), a sibling to
  `useLauncherHotkeys`; `CanvasSurface` 156→143 by making `useCanvasCommandHandler` self-source its
  store bindings (removing the options object + 5 handler-only selectors). Behavior preserved
  (identical test totals); amended into the same commit.

## Performance Notes

No perf work. Sessions fetch is lazy (gated on `hasOpened`), so a never-opened palette never hits
`/v1/sessions`; the query shares React Query cache with the picker (same key) when both are present.

## Deviations from Spec

- Spec language framed Sessions as "wrap the shipped transcript browse" with "deep internals
  deferred", which read as a thin wrapper. The actual shipped pattern (Settings/Workdir already
  list items inline rather than wrapping) + the orchestrator's "real scope mirroring the pattern"
  resolved this to the inline-list build. Search / replay / denylist internals remain deferred.

## Open Items

- Live-session badge: rows don't mark the currently-live session (the picker does via
  `launchSessionId`). Skipped to stay within "wiring only"; a future polish pass could thread
  `launchSessionId` into `ScopeRowInputs`.
- No CanvasSurface integration test for the `open-session` glue line — follows the existing
  convention (select-worktree glue is likewise untested); the descriptor mapping + 4 states are
  covered in the pure model, and `spawnOrFocusTranscript` is covered in `canvasStore.test.ts`.
