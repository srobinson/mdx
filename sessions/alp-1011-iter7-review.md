---
title: ALP-1011 Iteration 7 Code Review
type: sessions
tags: [review, echoecho, frontend, react-native, hooks, performance]
summary: Reviewed 5 commits (isDirty flag, useCallback handlers, snapshot revert, dep narrowing, polling removal). All correct. One cosmetic fix applied.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed iteration 7 of the ALP-1011 multi-perspective code review sweep. Five commits touched six files across the admin and student apps, all focused on React hook correctness: eliminating stale closures, reducing unnecessary re-renders, and removing a busy-wait polling loop.

All five changes are structurally sound and correctly implemented.

## Commits Reviewed

| Commit | Issue | Change | Verdict |
|--------|-------|--------|---------|
| cde1ad2 | ALP-1043 | Replace JSON.stringify with isDirty flag in useWaypointEdit | Clean |
| 5fed6b1 | ALP-1104 | Narrow confirm callback deps in useVoiceAnnotation | Clean |
| 3e60044 | ALP-1092 | Wrap useSpeechRecognitionEvent handlers in useCallback | Clean (cosmetic fix applied) |
| 9b4e218 | ALP-1095 | Snapshot favorites before optimistic write | Clean |
| c5585f0 | ALP-1099 | Remove busy-wait polling for STT pause | Clean |

## Issues Found and Fixed

**1. Duplicate section header in useSttDestination.ts** (cosmetic)

The handler reordering in ALP-1092 moved `resetToIdle` and `processTranscript` above the event handlers but left the original `// -- Public API` section header in place. This created two identical section headers, with the first one misleadingly labeling `resetToIdle` (primarily an internal helper for event handlers) as the public API block. Renamed to `// -- State reset (used by event handlers and public API)`.

## Verification Notes

- `isDirty` flag: All five mutation paths set `isDirty: true`. Both `cancel()` and `confirmSave()` reset via `INITIAL` (which has `isDirty: false`). `startEditing` explicitly sets `isDirty: false`. Complete coverage.
- `useVoiceAnnotation.confirm` deps: Callback reads `state.phase`, `state.transcript`, `state.audioUri`. Dependencies match exactly.
- `handleEnd` empty deps: Correct since it only touches refs (`isPausedRef`, `pauseResolverRef`).
- `requestPause()` promise: Already resolves via `pauseResolverRef` on 'end' event or 200ms timeout. Polling was genuinely redundant.
- Snapshot revert pattern: `const snapshot = favorites` correctly captures the closure value before any setState calls.

## Open Items

- Pre-existing typecheck failures: `HazardPickerSheet.tsx` has 14 TS errors (missing module declarations, implicit any). Not related to this iteration.
- Pre-existing infra: ESLint plugin and jest/reanimated PnP resolution broken in this worktree.
