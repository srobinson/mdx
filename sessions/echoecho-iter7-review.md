---
title: EchoEcho Navigator MVP — Iteration 7 Code Review
type: sessions
tags: [review, echoecho, ALP-935, ALP-948, ALP-950, waypoint-detection, voice-annotation]
summary: Fixed two algorithm bugs in waypoint detection hysteresis and one race condition in voice annotation re-record flow
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed iteration 7 output: GPS recording service (ALP-947), automatic waypoint detection (ALP-948), voice annotation (ALP-950), photo snapshot (ALP-951), and supporting hooks/store changes. Three bugs found and fixed; all 10 unit tests pass after fixes.

## Issues Found and Fixed

### 1. waypointDetectionService.ts — Stray reset breaks consecutiveStraightCount (ALP-948)

**File:** `apps/admin/src/services/waypointDetectionService.ts`

**Root cause:** A misindented `s.consecutiveStraightCount = 0;` line (indented 6 spaces instead of 10, suggesting it was an editing artifact) appeared in the below-threshold else-branch immediately before `s.consecutiveStraightCount++`. This made the counter permanently stuck at 1. Since `sustainedSamples = 3`, the reference heading could never advance past its initial seed value during normal straight-line travel.

**Fix:** Removed the stray reset. The `++` now accumulates correctly.

Also removed a harmless duplicate `s.consecutiveStraightCount = 0;` in the turn-detection block (same editing artifact).

### 2. waypointDetectionService.ts — Reference heading drifts on gradual turns (ALP-948)

**File:** `apps/admin/src/services/waypointDetectionService.ts`

**Root cause:** After a long straight segment, `consecutiveStraightCount` grew without bound (e.g., 27). During a gradual turn where each step is below the 20° threshold, `consecutiveStraightCount >= sustainedSamples` was always true — so the reference heading updated on every single sample, tracking the gradual turn rather than anchoring to the departure heading. The hysteresis never engaged.

**Fix:** Reset `consecutiveStraightCount = 0` immediately after each reference heading advance. This creates a proper cooldown: the next advance requires `sustainedSamples` fresh consecutive below-threshold readings. A gradual turn cannot supply this once the accumulated deviation from the locked reference exceeds the threshold.

**Test result:** The failing test ("inserts a turn waypoint after a 90-degree turn with sustained samples") now passes. All 10 tests pass.

### 3. useVoiceAnnotation.ts — reRecord() race condition (ALP-950)

**File:** `apps/admin/src/hooks/useVoiceAnnotation.ts`

**Root cause:** `reRecord()` called `void doStop()` (fire-and-forget), then immediately called `reset()` and `void startRecording()`. `doStop()` calls `stopAndUnloadAsync()` and `deactivateRecordingAudioSession()` — both async. Starting a new `Audio.Recording` while the previous audio session is mid-teardown causes an `AVAudioSession` conflict on iOS.

**Fix:** Wrapped `reRecord()` body in an async IIFE that awaits `doStop()` before calling `reset()` and `startRecording()`.

## Patterns Observed

- Misindented stray lines (wrong column depth) are a recurring artifact of multi-step editing in the agent's context. These are structurally invisible to TypeScript but semantically dangerous in algorithms with counter state.
- The waypoint detection algorithm is fundamentally pure-functional (stateless API, immutable-ish state objects) which made the bug easy to isolate and test.
- The `consecutiveStraightCount` reset-after-advance pattern is analogous to a sliding window lock — worth documenting in future algorithm work.

## Open Items

None. All identified issues resolved.
