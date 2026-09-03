---
title: Runtime Sound identity in Audioface Phase 2
type: research
tags: [audioface, sound, voicing, phase2, issue-tracker]
summary: The tracker requires a persistent runtime Sound across trigger calls but leaves its exact identity, owner, creation, and retirement key unresolved.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-04
updated: 2026-09-04
---

# Executive Summary

The GitHub record supports a runtime `Sound` that persists across trigger calls and owns voicing state shared by its voices. A trigger creates or addresses a voice, while `Sound` retains state needed for retrigger, portamento, voice limits, and sound scoped processing. The tracker does not decide the exact `Sound` identity or lifecycle key.

The proposed slice 3 rule follows the record when stated as an intermediate, behavior preserving step. Structural `Sound` routing can be a bit identical no op, the existing seed derivation should remain unchanged, and delay can remain per layer for that slice. Phase 2 still requires the delay or echo unit to move to sound scope in slice 4.

# Project Metadata

| Item | Value |
|---|---|
| Repository | `littleorgans/audioface` |
| Baseline | `main` at `10ba9fc`, as named in issue #4 and confirmed locally |
| Language and runtime | TypeScript kernel in one `AudioWorkletProcessor` |
| Evidence boundary | GitHub issues, issue comments, issue edit history, linked pull requests, pull request edit history, and repository wide issue search |
| Tracker snapshot | 2026-09-04 |

# Finding 1: Runtime Sound persists across trigger calls

This conclusion is directly supported.

1. [Issue #4](https://github.com/littleorgans/audioface/issues/4) records voicing as a property of `Sound`. It assigns `Sound` the state needed across voices and calls: "portamento with the last pitch held as instance state, not patch state."
2. [Issue #5, owner comment](https://github.com/littleorgans/audioface/issues/5#issuecomment-5522929135) requires a "per Sound instance count" for `maxVoices` and says: "Implement portamento from the Sound instance's last pitch."
3. The same comment defines retrigger behavior across successive notes. Legato reuses a voice, retrigger restarts envelopes while keeping phase, and hard starts a new voice while stealing the old one. These behaviors require a persistent object that observes more than one trigger.
4. [Issue #11](https://github.com/littleorgans/audioface/issues/11) places individual trigger identity below that object: `GameAudio.trigger(...)` returns a `VoiceId`, and `release(voiceId)` releases that voice.
5. Issue #11 also requires two presses of a bed to be two held voices. One trigger therefore cannot define the lifetime or identity of the enclosing `Sound`.

The runtime relationship implied by the accepted decisions is:

```text
persistent Sound instance
  owns voicing state, last pitch, voice count, and sound scoped plugin state
  receives multiple trigger calls
    each trigger creates, reuses, restarts, ignores, or steals a Voice
```

# Finding 2: Exact identity and ownership key remains unresolved

No reviewed issue, comment, edit, or linked pull request states the exact key that creates, looks up, or retires a runtime `Sound`.

The tracker establishes only these boundaries:

1. [Issue #11](https://github.com/littleorgans/audioface/issues/11) explicitly rejects event identity alone: "the event keyed held map permits one held instance per event, which is wrong for a game."
2. Its host call is `trigger(event, { emitter, take, listener })`, returning `VoiceId`.
3. [Pull request #13](https://github.com/littleorgans/audioface/pull/13) describes "per emitter voice identity." That statement concerns voice tracking. It does not define `Sound` identity.
4. [Issue #6](https://github.com/littleorgans/audioface/issues/6) attaches emitters to `Object3D`, but does not say whether one emitter owns one Sound, one Sound per event, or several independently created Sounds.
5. [Issue #4](https://github.com/littleorgans/audioface/issues/4) leaves placement of sound scoped state open: `MasterBus` per Sound or a new `Sound` object between voice and bus.

The unresolved owner decision is the runtime instance key and lifecycle protocol. The record does not choose among an explicit `SoundId`, emitter identity, emitter plus event identity, or another host supplied instance key. It also does not define the creation call or the retirement condition after voices and plugin tails finish. `packId`, `eventId`, and their role in runtime `Sound` identity do not appear in the tracker evidence inspected.

# Finding 3: Proposed slice 3 rule

## Sound routing as a bit identical no op

Supported as an intermediate slice.

[Issue #4](https://github.com/littleorgans/audioface/issues/4) requires every refit to preserve behavior, keeps the worklet null test exact, and requires both shipping pack certifications to remain unchanged. Introducing the routing structure before changing processing ownership follows that sequencing.

The no op qualification cannot describe the completed Phase 2 behavior. Issue #4 eventually requires sound scoped plugins to run once over mixed voices, with a bed containing two voices rendering one echo.

## Preserve the `packId` and `eventId` seed parent and `take` derived voice bits

Supported as preservation policy, without direct tracker confirmation of those exact fields.

Issue #4 requires the deterministic seed namespace to remain a child of the voice seed, keyed by plugin instance id as layers are today. Its exact null and unchanged certification requirements also support leaving the existing seed tree untouched during a structural routing slice.

The tracker never records the specific `packId` plus `eventId` parent or the `take` derived voice bit allocation. Those details are therefore existing behavior to preserve, rather than an owner decision established by the issue record.

## Leave delay per layer

Supported for slice 3 only.

Issue #4 sequences "the filter as one plugin with three modes; delay" in slice 3, followed by "Echo to sound scope" in slice 4. Keeping the current delay or echo placement during the no op routing slice matches that sequence and protects bit identity.

Permanent per layer delay would contradict the Phase 2 decision. Issue #4 says sound scoped delay runs once on the Sound bus over mixed voices, and requires the current per layer, per voice echo to become sound scoped.

# Contradictions and clarifications

1. Issue #11 and pull request #13 establish stronger voice identity through `VoiceId` and emitter aware tracking. They do not answer the separate `Sound` grouping question introduced by issues #4 and #5.
2. Issue #4 asks for behavior preserving refits while also requiring echo ownership to change from each voice to one Sound bus. The slice order resolves this tension: install routing without changing samples, then make the explicit sound scope behavior change in slice 4 with its own proof.
3. The terms `delay` and `echo` refer to the same migration seam in issue #4. Slice 3 refits the delay unit. Slice 4 changes the existing echo stage's ownership.

# Evidence Coverage

GitHub contained 10 issues and 3 pull requests at the snapshot. I inspected every current body, the sole issue comment, all 11 available issue body edits, all 6 available pull request body edits, and the cross reference timelines for issues #1, #4, #5, and #11. The pull requests had no review bodies, review comments, or conversation comments available through GraphQL.

Repository wide GitHub search covered `Sound`, `voicing`, `retrigger`, `portamento`, `emitter`, `take`, and `instance`. Relevant results were issues #1, #2, #4, #5, #6, and #11 plus pull requests #10 and #13. Linked implementation history was checked through [pull request #10](https://github.com/littleorgans/audioface/pull/10) and [pull request #13](https://github.com/littleorgans/audioface/pull/13).

# Open Questions

1. What stable key identifies a runtime `Sound` instance?
2. Which layer creates and owns that instance: `GameAudio`, `BusHost`, `MasterBus`, or an explicit host API?
3. What event retires the instance after its final voice and sound scoped plugin tail complete?
4. Does one emitter host several instances of the same event concurrently? Issue #11 says the game must support more than one held voice per event, but does not settle how those voices group into Sounds.
