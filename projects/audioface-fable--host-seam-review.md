---
title: Audioface #11 host seam review, engine and host side
type: review
tags: [audioface, seams, adversarial-review]
status: active
created: 2026-09-04
project: audioface-next
source: littleorgans/audioface#11
---

# Host seam review: engine and host side

Reviewed read only from `main` at the merge of PR #10. Working tree clean.

## Verdict

Conditional sign off. `BusHost` in control is right and the module is deep. Three defects: the sketch types against a module control may not import, clock seeding widens the engine's interface to buy nothing the translation does not already buy inside `BusHost`, and refusal as a message does not yet cover the render path, where the current processor can die.

## Findings

1. **The sketch is unimplementable as written.** `BusHost` types `receive(message: HostMessage)`, but `HostMessage` and `WorkletMessage` live in `adapters/web/src/worklet-protocol.ts`, and ALLOWED_EDGES gives control no edge to any adapter. The protocol is the interface of the seam, so it moves with the seam: both unions belong in contract (where `BusCommand` and `BusReport` already live), and `worklet-protocol.ts` keeps only `PROCESSOR_NAME`, `BLOCKS_PER_REPORT` becomes `BusHost` implementation, and `postPortMessage` stays with the port it serves.

2. **A deferred refusal kills the processor today, and the proposal must name this as `BusHost` behaviour.** `AudiofaceProcessor.receive` wraps `StampedBus.receive` in try, but `process` calls `this.bus.render` bare. A command stamped in the future passes `receive` unvalidated, waits in `StampedBus.pending`, and applies during `render`, where `MasterBus.start` throws (duplicate voice id, sample rate mismatch). The throw escapes `process` and the worklet stops rendering, silently. So `render(block, deviceFrame): readonly WorkletMessage[]` must catch and convert, which is exactly what the return type permits; the audit never says so. Consequence for the correlation id: it cannot ride only on `HostMessage`, because by the time the refusal happens the message is gone and only the queued `BusCommand` remains. The id must be carried per command through the queue. Cheapest shape: `receive` takes `{ id, message }` and `BusHost` keeps the id alongside the command it queues; `BusCommand` itself stays untouched, so the engine never learns correlation exists.

3. **Construction is missing from the interface.** The processor reads the platform globals `sampleRate` and `currentFrame`. `BusHost` with no constructor argument would have to also. `createBusHost(sampleRate: number): BusHost` puts the device rate on the adapter, where the platform dependency belongs, and `deviceFrame` on `render` puts the clock there. With those two arguments the Node null test drives `BusHost` with no shim at all, which is the leverage the proposal promises.

4. **The `synced` answer should carry the clock now.** Phase 2's seek and latency compensation need the page to relate its stamps to the bus's clock. `{ kind: "synced" }` carrying nothing means changing a message pages already parse when that arrives. `{ kind: "synced", frame: number }` costs one field today and is breaking tomorrow.

## Amended interfaces

```ts
// contract: worklet-protocol moves here
type HostMessage =
  | { readonly kind: "command"; readonly id: number; readonly command: BusCommand }
  | { readonly kind: "sync" };
type WorkletMessage =
  | { readonly kind: "report"; readonly report: BusReport }
  | { readonly kind: "synced"; readonly frame: number }
  | { readonly kind: "refused"; readonly id: number; readonly message: string };

// control
function createBusHost(sampleRate: number): BusHost;
type BusHost = {
  receive(message: HostMessage): readonly WorkletMessage[];
  render(block: StereoBlock, deviceFrame: number): readonly WorkletMessage[];
};
```

## Answers

**1. Control.** Apply the deletion test to each placement. In control, deleting `BusHost` makes the origin, the waiting queue, the cadence and the refusal conversion reappear in `worklet.ts`, in the Node test shim, and in every Phase 2 host adapter: it earns its keep. In engine, the edge rule forces control to re-export it verbatim, and that re-export fails the same deletion test finding 2 of the audit applies to the `StampedBus` re-export; the proposal would recreate the pass through it retires. Widening ALLOWED_EDGES instead would let adapters reach `MasterBus` and `VoicePool` directly, spending locality across the whole engine to save one file. Control already imports engine (`renderEvent` builds a `StampedBus`), so nothing changes in the graph.

**2. Keep the translation, inside `BusHost`.** Seeding moves the origin from implementation to interface. `StampedBus`'s contract is one sentence: frames in the bus's own clock, zero at construction, which `renderEvent` and the sample for sample bus test rely on. Seeding replaces it with a temporal invariant, the first `render` call defines the clock, and needs a signature change (`render` gains a frame, or a seed method) that every caller including the offline path must learn. It also splits the report: `BusReport.frame` would be device absolute realtime and construction relative offline, so the twin paths stop agreeing on anything but samples. The translation inside `BusHost` is invisible to every caller. That is depth; seeding is shallowness with fewer lines.

**3.** The union shape is what makes most of Phase 2 additive: reset, seek, suspend, virtualise and restore arrive as new `HostMessage` kinds, latency and tail as report fields, and the adapters forward opaquely, so callers do not break. Needed now, because retrofit breaks parsers: the correlation id (finding 2) and the clock on `synced` (finding 4). Everything else can wait.
