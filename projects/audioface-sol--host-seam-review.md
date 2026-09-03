---
title: Audioface host seam review
type: projects
tags: [audioface, architecture, host, game-audio, review]
summary: Adversarial review of issue 11 from the game module and host message perspectives.
status: active
created: 2026-09-04
updated: 2026-09-04
project: audioface-next
confidence: high
source: https://github.com/littleorgans/audioface/issues/11
related:
  - audioface-2026-09-host-seam-audit
  - audioface-game-audio-middleware-gaps
---

# Audioface host seam review

## Verdict

Conditional signoff. The realtime host and row modules have sound depth. The proposed page bus has one substantive defect: its interface identifies held work by event, so two emitters cannot sustain the same event independently. Issue 11 should name the module `GameAudio`, return a `VoiceId` from `trigger`, accept that id in `release`, and correlate every refusal with the exact host command.

## Findings

1. **`PageBus` loses game identity.** `Performance.trigger` first calls `release(event)`, stores one `VoiceId` per event, and returns listener values rather than the new voice id. `Performance.release` accepts an event. A game cannot address the same sustaining event on two emitters, release one instance, or associate a refusal with one instance. Evidence: `git show main:adapters/web/src/performance.ts`, symbols `Performance.trigger` and `Performance.release`; `git show main:packages/contract/src/control.ts`, symbol `VoiceRequest`. `GameAudio` gives callers leverage through per emitter, per voice control. Its implementation keeps identity, stamping, and held state local.

2. **One public module is right today.** `Player` owns device creation, retry, level changes, and frame access. `Performance` owns voice creation, serials, listener changes, and held state. Both implementations contain real behaviour. Their interface is shallow: `Performance` learns `Player.frameNow`, `Player.output.sampleRate`, and `Player.send`; `mountAudioface` learns that `Player.apply` returning true requires `Performance.forget`. Evidence: `git show main:adapters/web/src/player.ts`, symbols `Player.frameNow`, `Player.send`, and `Player.apply`; `git show main:adapters/web/src/mount.ts`, symbol `mountAudioface`; `git show main:adapters/web/src/performance.ts`, symbol `Performance.forget`. Delete the joint and that coordination moves inside `GameAudio`. The test fake is not a shipping adapter, so the joint has one adapter and remains hypothetical. Callers learn one interface. Maintainers retain locality because the two implementations can remain private.

3. **Correlation belongs to the host envelope.** `HostMessage` wraps `BusCommand`, while `WorkletMessage.refused` contains only text. `AudiofaceProcessor.apply` can refuse a command after queueing, and `Player.failed` can refuse while opening the device. Evidence: `git show main:adapters/web/src/worklet-protocol.ts`, symbols `HostMessage` and `WorkletMessage`; `git show main:adapters/web/src/worklet.ts`, symbols `AudiofaceProcessor.apply` and `AudiofaceProcessor.refuse`; `git show main:adapters/web/src/player.ts`, symbol `Player.failed`. A `commandId` on `BusCommand` would make transport identity part of the engine command used by offline rendering and `StampedBus.receive`. Keep it on the `HostMessage` command variant and echo it in `HostEvent.refused`. This gives every adapter error correlation while keeping engine command logic local.

## Amended interfaces

```ts
type CommandId = Brand<string, "CommandId">;
type EmitterId = Brand<string, "EmitterId">;

type HostMessage =
	| { readonly kind: "command"; readonly commandId: CommandId; readonly command: BusCommand }
	| { readonly kind: "sync" };

type HostEvent =
	| { readonly kind: "report"; readonly report: BusReport }
	| { readonly kind: "synced" }
	| { readonly kind: "refused"; readonly commandId: CommandId; readonly message: string };

type GameAudio = {
	trigger(request: {
		readonly event: string;
		readonly take: number;
		readonly emitterId: EmitterId;
	}): VoiceId;
	release(voiceId: VoiceId): boolean;
	setListener(listener: Partial<ListenerField>): void;
	applyOutput(output: OutputField): void;
	held(): readonly VoiceId[];
	listen(listener: (event: HostEvent) => void): () => void;
};
```

`HostMessage` and `HostEvent` belong beside `BusCommand` in the contract. `BusHost` consumes and returns those neutral types. `worklet-protocol.ts` then contains only the worklet adapter.

## Answers to questions 1 to 3

1. Use the same `GameAudio` module. The threejs binding is an adapter that translates camera and `Object3D` state into this interface. Wwise calls the equivalent entry point `AK::SoundEngine` and identifies game objects and listeners. FMOD uses `Studio::System` plus `EventInstance` handles. Unreal sends gameplay through `UAudioComponent`, while MetaSound stays the render graph. Carry `EmitterId`, `VoiceId`, and command correlation now. Add scoped RTPC commands with the event and parameter model. Add camera pose and emitter transforms in Phase 4. Add a `virtual` voice report when logical and rendered voices separate.

2. Merge the public interface. Keep device lifecycle and voice gestures as private implementations until a second shipping adapter makes their seam real. The resulting depth removes clocks, rates, retries, and rebuild cleanup from every caller while keeping platform work local.

3. Put `commandId` on the `HostMessage` command variant. The `GameAudio` implementation maps it to the voice, emitter, and action. On refusal it removes a refused start, restores a refused release, retains the last accepted placement, and emits a diagnostic. The game caller decides whether to retry.
