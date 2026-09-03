---
title: Audioface host seam audit, after Phase 1
type: research
tags: [audioface, architecture, deep-modules, seams, worklet, control, design-pass]
summary: Design audit of PR #10 (kernel into the AudioWorklet) in deep module vocabulary. The engine is deep; the glue around the bus is shallow. Five findings, one closed in the PR, four proposed as a design pass before Phase 2.
status: reviewed
created: 2026-09-04
updated: 2026-09-04
project: audioface-next
confidence: high
source: https://github.com/littleorgans/audioface/pull/10
related:
  - audioface-2026-09-SYNTHESIS.md
  - audioface-2026-09-engine-review.md
  - audioface-bespoke-synth-modularity.md
---

# Audioface host seam audit, after Phase 1

Reviewed from source at PR #10 head `06024c2`, merged to `main` 2026-09-04. `pnpm run check` green, 260 tests.

## Vocabulary

Module: anything with an interface and an implementation. Interface: everything a caller must know, including invariants, ordering, error modes and configuration. Seam: where an interface lives and behaviour can be swapped without editing there. Adapter: what fills a seam. Depth: behaviour per unit of interface learned. Leverage is what callers get from depth, locality what maintainers get. One adapter is a hypothetical seam, two is real. The deletion test: delete the module; if complexity vanishes it was a pass through, if it reappears across callers it earned its keep.

## What is deep and should be protected

- The engine's stage seam. `SourceGenerator` and `LayerStage` are two one method types over a block of the layer's own clock. Every source, filter and echo sits behind them; the renderer never learns what a layer holds. Allocation free, slice invariant, held by block boundary tests.
- The transcendental seam. One module, verified by walking the syntax tree of every other engine file. A table can replace `Math.sin` without touching a stage.
- `StampedBus`. The master bus behind three commands and one report, with the clock discipline (early holds, late plays now, release before start lands on the start) as implementation. Its test holds it sample for sample against a direct `MasterBus` drive.
- The null test. Exact equality between the offline render and the worklet render, in Node with shimmed globals and in the browser under `OfflineAudioContext`. This is what makes the two paths one engine.

## Findings

### 1. There is no realtime host module

Five places speak the command channel and none owns it: `StampedBus` in engine, `AudiofaceProcessor` in `adapters/web/src/worklet.ts`, `Player` and `Performance` on the page, `nullTest` in `adapters/web/src/differential.ts`, and `throughWorklet` in `test/worklet-null.test.mjs`.

The processor holds the clock translation (device frame origin, a waiting queue for commands that arrive before the first block, `onBusClock` moving every stamp by the origin) and the report cadence (`BLOCKS_PER_REPORT`). All of it is pure. It lives inside a class extending a platform global, so the only way to test it is to shim `AudioWorkletProcessor`, `registerProcessor`, `currentFrame` and `sampleRate`. That is testing past the interface: the module is the wrong shape. Deletion test: remove the processor and the clock logic reappears in the test shim.

Proposal. One deep module in control, working name `BusHost`:

```ts
type BusHost = {
  receive(message: HostMessage): readonly WorkletMessage[];
  render(block: StereoBlock, deviceFrame: number): readonly WorkletMessage[];
};
```

Owns origin, queueing, report cadence, and refusal as a message. No platform globals. The worklet file becomes a ten line adapter that forwards the port and the quantum. The Node null test drives `BusHost` directly, with no shim; the browser null test drives the adapter. Deeper still: let `StampedBus` seed its clock from the first render's device frame, and the origin translation disappears entirely. Two adapters (worklet, Node harness) make this a real seam.

Error mode to settle at the same time: a `refused` message names no command. A page cannot tell which press was refused. A correlation id on `HostMessage` is the smallest fix.

### 2. `StampedBus` re-exported through control is a pass through

`packages/control/src/index.ts` re-exports `StampedBus` from engine verbatim, so the edge rule (adapters reach the engine only through control) is honoured in letter. Delete the re-export and nothing about control changes. `BusHost` from finding 1 is what belongs at that spot, with behaviour behind it, and the re-export retires with it.

### 3. `Audition` carries three concerns

`Audition` in `packages/contract/src/control.ts` holds event rendering (`events`, `render`, `voice`, `targetOf`), the listener's control rows, and the output device's control rows. The output rows have nothing to do with auditioning.

The cost lands in the adapter. `defaultOutput` in `adapters/web/src/output.ts` rebuilds an `OutputField` from leaf defaults by casting; `withField` re-parses text per field with `Number(text)`, bypassing the range parser control already has in `parseControlEdit`. A sample rate of 7 reaches `new AudioContext` and comes back as a worklet refusal instead of a control issue. `wholeListener` in `performance.ts` hardcodes `{ pan: 0, width: 1, distance: 0 }` and then overwrites from leaf defaults: a shadow default. Two representations of five rows, converted by hand in a caller.

Proposal. Two small modules in control, one per device side row set, sharing one shape:

```ts
type RowSet<Field> = {
  readonly schema: Readonly<Record<keyof Field, ControlLeafSchema>>;
  readonly defaults: Field;
  read(current: Field, field: keyof Field, text: string): ControlParse<Field>;
};
```

`outputRows: RowSet<OutputField>` and `listenerRows: RowSet<ListenerField>`, parsing through the same path edits parse through. `Audition` shrinks to the four members about auditioning. Adapters iterate `schema`, start from `defaults`, and never parse.

### 4. `Player` and `Performance` split one module with a leaky joint

`Performance` reaches into `player.frameNow()` and `player.output.sampleRate` to build a voice, then calls `player.send`. `mountAudioface` must know that when `player.apply(next)` returns true it has to call `performance.forget()`. That coordination invariant is part of the interface and lives in a caller. Voices are stamped at the requested rate, not the device's actual rate; any divergence refuses every voice.

Proposal. One page side module, "the page's bus":

```ts
type PageBus = {
  trigger(event: string, take: number, listener?: Partial<ListenerField>): void;
  release(event: string): boolean;
  place(listener: Partial<ListenerField>): boolean;
  apply(output: OutputField): void;
  held(): readonly string[];
  listen(listener: (message: WorkletMessage) => void): void;
};
```

Stamping, the device lifecycle, and forgetting on rebuild become implementation. The `Performance` test's hand rolled fake player (a structural type named nowhere) goes away; the module is tested through `listen` and a fake port.

### 5. Duplication introduced by the PR (closed in `06024c2`)

Three `post()` copies became `postPortMessage`. The audition gesture became `auditionCommands(voice)`, and the offline render now drives a `StampedBus` with it, so offline and realtime share the gesture and the clock discipline by construction. The null verdict became one `nullVerdict` used by both tests. `nullVerdict` still lives in the web adapter; it depends on nothing in the browser and belongs beside `auditionCommands` in control when finding 1 lands.

## Smaller notes

- `SourceGenerator` and `LayerStage` are the same shape with different verbs. The fills versus works in place distinction is real but the type does not carry it, and `filtered` pays a wrapper. Leave until the plugin contract (Phase 2) subsumes both.
- `StampedBus.release` allocates a lifetimes array on the audio thread per release. Not a per quantum allocation. A pool lookup by id removes it.
- `catalogue/*/types/` is missing from `.gitignore`; one generated declaration file is tracked.

## Sequencing

Findings 1 to 4 are one design pass, sequenced between Phase 1 and Phase 2. Reason: Phase 2 defines the contract every plugin implements and the host adapters (offline, worklet, native) that render it. If the host seam is still five places, Phase 2 inherits the shape and three more adapters copy it. Each finding is behaviour preserving and held by the existing null test and 260 tests, so the pass can land as PR sized slices.

## Questions for adversarial review

1. Should `BusHost` live in control or in engine? Control is the layer adapters may reach; engine is where the clock discipline already lives. The answer decides whether the `StampedBus` re-export is replaced or the edge rule changes.
2. Is seeding the bus clock from the device frame better than an origin translation, or does it leak the device into the engine?
3. Is `RowSet<Field>` the right generalisation, or are the listener rows (trigger authority, live) and output rows (output authority, device) different enough that one shape is false economy?
4. Does `PageBus` become the threejs binding's interface in Phase 4, or is that a second module over the same host? If the former, the interface should be named for a game, not a page.
5. What does the plugin contract in Phase 2 need from the host seam that these interfaces do not carry: reset, suspend, virtualise, latency, tail?

## Review outcome, 2026-09-04

Three model families reviewed the proposal independently (Fable on the engine and host side, GPT Sol on the game side, Grok on the adapter and rows side). All three signed off conditionally; every condition was folded into issue #11. Reviews: `~/.mdx/projects/audioface-fable--host-seam-review.md`, `audioface-sol--host-seam-review.md`, `audioface-grok--host-seam-review.md`.

Decisions taken against this audit's proposals:

- `BusHost` lives in control. `HostMessage` and `WorkletMessage` move to contract, since control has no edge to adapters. Construction seam is `createBusHost(sampleRate)`; adapters own the platform globals.
- Rejected: seeding `StampedBus` from the device frame. It widens the engine bus's interface, makes its clock depend on call order, and splits `BusReport.frame` between device absolute (realtime) and construction relative (offline). The origin translation stays in the host.
- Correlation id on the `HostMessage` envelope, echoed on `refused`, never on `BusCommand`. Fable and Sol reached this independently. `synced` carries the bus frame, for Phase 2 seek and latency compensation.
- A live defect surfaced: a queued command the bus refuses throws out of `StampedBus.render` and so out of `process`, killing the processor. Filed as #12; fixed by the `BusHost` slice.
- Rejected: a generic `RowSet<Field>`. It erases `ControlNumber` on the listener side and is a seam with one adapter. Two concrete modules, `ListenerRows` and `OutputRows`, share one leaf parser with `parseControlEdit`. `ListenerRows.complete` replaces `wholeListener`. `OutputRows.read` refuses an illegal sample rate as `value_out_of_range`; `OUT-12.sample-rate` is an enum row while `OutputField.sampleRate` is a number, reconciled in the read.
- The page module is `GameAudio`, the same module the Phase 4 threejs binding drives. `trigger` takes an emitter and returns a `VoiceId`; `release` takes a `VoiceId`, since an event keyed held map permits one held instance per event. The public interface of `Player` and `Performance` merges; the implementations may stay private parts.
- Grok's second round added `OutputRows.accept(field)`: `read` covers text only, and a game binding that never had text would still reach `AudioContext` with an illegal rate through `GameAudio.apply`. `apply` runs `accept` first and returns issues.
