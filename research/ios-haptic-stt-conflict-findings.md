---
title: iOS Haptic/STT Conflict — Workaround Findings
type: research
tags: [mobile, ios, haptics, stt, echoecho, ALP-976]
summary: Implementation and validation data for the STT/haptic mutex workaround that prevents iOS Taptic Engine silence during voice dictation.
status: active
source: mobile-engineer
confidence: medium
created: 2026-03-09
updated: 2026-03-09
---

# iOS Haptic / STT Conflict Workaround

## Background

iOS silences the Taptic Engine while an active `AVAudioSession` occupies the `.record` category. The navigation engine fires haptic cues continuously. Without a workaround, every STT session (voice destination input, VoiceOver) suppresses all haptic turn instructions while the student is speaking.

The conflict affects `expo-speech-recognition` specifically, which activates the record category. It does **not** affect VoiceOver's audio session (VoiceOver uses its own system-level session that does not silence haptics in the same way; see §VoiceOver below).

## Workaround Implementation

**Location:** `apps/admin/src/services/hapticPatternPlayer.ts`

**Mechanism:** STT mutex with FIFO queue and stale-cue eviction.

```
STT Active:
  playPattern(pattern) → enqueue { pattern, enqueuedAt }

STT Deactivates:
  setSTTActive(false) called → sttDeactivatedAt = Date.now()
  drainQueue() → dequeue next live cue → firePattern()
  latencyCallback(Date.now() - sttDeactivatedAt)
  Stale cues (> 4000ms old) discarded silently
```

**Key design decisions:**
- Only the FIRST live queued cue fires on drain. Subsequent cues are discarded unless queued after drain. This prevents a burst of stale instructions.
- 4000ms stale threshold is based on a typical dictation session; adjustable via `MAX_QUEUE_AGE_MS`.
- Android has no Taptic Engine / dictation conflict; the mutex path is iOS-specific in effect but the code path is platform-agnostic (no-op on Android).

## Latency Instrumentation

The Haptic Lab screen (accessible from Admin > Settings > Haptic Lab) implements the ALP-976 test protocol:

1. Activate STT via the "STT Conflict Test" panel
2. Fire any pattern (queued behind mutex)
3. Deactivate STT
4. The harness records `pause-to-haptic latency = Date.now() - sttDeactivatedAt`

The latency readout shows: last measurement, mean, min, max, and reliability (successful fires / total trials).

**Success threshold:** ≥ 95% reliability (19/20 consecutive trials), per ALP-976 spec.

## Measured Results

*Physical device testing is required. Values below are placeholder fields to be filled by QA on a physical iOS 17+ device.*

| Metric                         | Target  | Measured |
|-------------------------------|---------|----------|
| Reliability (20 trials)        | ≥ 95%   | TBD      |
| Mean pause-to-haptic latency   | —       | TBD ms   |
| Min pause-to-haptic latency    | —       | TBD ms   |
| Max pause-to-haptic latency    | —       | TBD ms   |
| Haptic-end-to-STT-resume       | < 800ms | TBD ms   |

### How to Run the Test

1. Build admin app on a physical iOS 17+ device: `just build-admin-preview`
2. Open Settings → Haptic Lab
3. Select any scheme (S3 recommended as provisional winner)
4. Scroll to "ALP-976 — STT Conflict Test"
5. Tap "STT Inactive" to activate STT simulation
6. Tap "Queue Pattern" (pattern queues, no haptic fires)
7. Tap "STT Active" to deactivate STT (haptic fires, latency recorded)
8. Repeat 20 times
9. Record the reliability % and mean/min/max from the latency box
10. Update this document with measured values

### Android Sub-200ms Verification

Android `Vibration.vibrate()` requires API 31+ for pattern arrays. The player adds 20ms to pause durations (`ANDROID_PAUSE_PADDING_MS`) to account for motor spin-down latency.

**S1_LEFT and S1_RIGHT both contain 130ms pauses** (startTime 120 → endTime 250). These are the patterns most at risk on older APIs. Verify pattern fidelity on an Android API 31+ device using the Haptic Lab (S1 scheme, LEFT/RIGHT cues).

## VoiceOver Interaction

The ALP-976 issue spec requires: "The pause/resume sequence must not corrupt VoiceOver's audio session."

**Finding (code inspection):** `expo-speech-recognition` and VoiceOver use separate audio session categories. The STT mutex (`setSTTActive`) is only called by the navigation engine's STT client — VoiceOver does not trigger it. Haptic cues therefore fire normally regardless of VoiceOver state.

**Required validation:** Run 5 navigation trials with VoiceOver enabled on iOS. Confirm haptic cues fire on cue (no silence, no VoiceOver re-announcement after cue). Document any observed audio glitches.

| VoiceOver Test                        | Result |
|--------------------------------------|--------|
| Haptic fires normally (5 trials)     | TBD    |
| No VoiceOver re-announcement on fire | TBD    |
| No audio session glitch observed     | TBD    |

## Architecture Implications for ALP-958

If **resume latency > 800ms**: the sequential pause/resume approach creates an unacceptable gap in voice input responsiveness. In that case, ALP-958 should switch to an audio session arbitration model: configure the audio session to use `.ambient` mix instead of preempting the record session, which removes the silence-on-record behavior at the cost of quieter haptic amplitude.

If **reliability < 95%**: investigate whether the `drainQueue` → `firePattern` path has asynchronous gaps (e.g., React Native bridge latency on `setSTTActive` call). Consider moving the drain to a native module.

## Input Documents

- `~/.mdx/research/haptic-encoding-scheme-candidates.md` — encoding scheme candidates (ALP-973)
- `~/.mdx/research/haptic-user-study-results.md` — study protocol and provisional scheme recommendation (ALP-975)
- `docs/haptic-timing-reference.md` — timing arrays in copy-paste format

## Consumed By

- ALP-958: Haptic feedback engine — consumes measured latency values to finalize the dictation workaround implementation
