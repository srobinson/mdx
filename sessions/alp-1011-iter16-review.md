---
title: ALP-1011 Iteration 16 Code Review
type: sessions
tags: [review, echoecho, ALP-1011, voice-annotation, audio-engine, campus-sync]
summary: Reviewed 5 commits (ALP-1077, ALP-1073, ALP-1101, ALP-1087, ALP-1090). All clean, no fixes needed.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed iteration 16 of the ALP-1011 multi-perspective code review sweep. Five commits spanning admin voice annotation service, student audio engine, student campus context, and student app config. All changes are correct and well-structured. Typecheck passes, lint clean (one pre-existing warning unrelated to changes).

## Commits Reviewed

1. **ALP-1077** (voiceAnnotationService.ts): Replaced base64+Uint8Array upload with fetch/blob pattern via `uriToBlob()`. Correct use of RN's native fetch for local file URIs. Error propagation intact through existing try/catch in both `uploadVoiceAnnotation` and `processAudioUploadRetryQueue`.

2. **ALP-1073** (voiceAnnotationService.ts, useVoiceAnnotation.ts): Replaced monkey-patched `_sttSubs` property on Recording object with explicit `SttSubscription[]` parameter passing. New `sttSubsRef` in hook properly initialized, populated, passed, and cleared on all paths.

3. **ALP-1101** (useAudioEngine.ts): Fixed duplicate turn announcement. The `announce()` function plays clip OR falls back to text (not both), so without a clip, both enqueues produced identical text. Gating second enqueue on `clipUri` is correct.

4. **ALP-1087** (CampusContext.tsx): Added AppState foreground resume listener calling `syncCampus`. Proper `prevAppState` ref pattern, effect cleanup via `sub.remove()`, dependency on `campus?.id` for re-registration.

5. **ALP-1090** (app.json): Removed dead autolinking.exclude entries for packages not in student dependency tree. JSON structure valid.

## Issues Found and Fixed

None.

## Patterns Observed

- Voice annotation service consistently uses the discriminated union return pattern (`ok: true | ok: false`).
- Audio retry queue silently re-queues items whose local files may have been deleted. Pre-existing design choice, not a regression.
- The `announce()` function in useAudioEngine uses clip-or-text semantics (not clip-then-text), which is important context for understanding the ALP-1101 fix.

## Open Items

None.
