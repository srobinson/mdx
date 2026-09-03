---
title: Audioface worker and browser host milestone review
type: projects
tags: [audioface, foundations, worker, audioworklet, browser, lifecycle, transport, review, verification]
summary: Independent review of the real worker and AudioWorklet host milestone at efa6af6, with fresh headed and headless browser evidence, a three realm Node harness and one low finding.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundations-runtime-host-browser-build, audioface-foundations-runtime-host-node-residuals-review, audioface-foundations-runtime-host-node-residuals]
confidence: high
---

# Worker and browser host milestone review

Target `efa6af6f8283efe0dfd362b74c74c11bdf16d2ca`, baseline `e6ddf9da996e0bf87b0fa3eb0be5f1c7f69f539f`, checkout `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser` on `probe/foundation-browser`. The checkout was at the exact target with zero changes before the review and after every command. Contract hashes verified: host spec `3f32506eb9bbbddc3a9500455d3fa177e23aef370cd3ff2dfbd0f7d8f8aa7574`, document spec `c192750843134c617fafc01836248c2288673c114ef08433e971ecd91c088f6e`, runtime probes spec `6615929b170d3681f0fc994985d9f5186316f87b6d0b7322fbcabe5e12f1555d`. Main README hash `f34eb76a9bd6818ccb3ae8243755c6e4598d93efccfe182d5d37bf550f254525` unchanged. The main checkout's untracked output directory was not inspected. No source, spec or prior report edits, no commits, remote actions or additional agents.

Verdict: one low finding, non blocking. Everything the brief obligates is verified independently. The finding is a guard mismatch at the 64 KiB call envelope boundary that turns one oversized caller request into a generation loss instead of a refused call.

## Delta

Three commits, 41 files, 2,425 insertions and 341 deletions. `34d1647` adds the worker entry, direct port, client, production processor host wiring, seed map threading, the proof worker and page and the migrated verifier. `a9ae324` encodes captures as Float32 bytes. `efa6af6` catches render callback failures, converts port failures into typed generation ends and closes the device on external context closure.

## Ownership trace, reuse and deletions

Main `RealtimeDevice.connect` creates the context, the production `AudioWorkletNode` with `processorOptions.generation`, the worker and one `MessageChannel`, then `ProgramClient` transfers one endpoint to the processor and the other to the worker. Main afterwards carries only bounded control: `program-call`, `program-ticket`, `program-outcome`, `program-end`, `program-failed`. The worker instantiates the existing `ProgramPreparer` with its composition surface, planner and compiler. The processor creates the existing `createBusHost` and `ProgramHost`. The direct `ProgramPort` has one listener and one native post per envelope with no replay or reconnect. The obsolete direct processor and page are deleted and nothing references them.

The product `GameAudio` constructs `RealtimeDevice` without program options, so the program path today is `new RealtimeDevice(url, settings, programs)` followed by `(await open()).programs.request(...)`. That is the shape the realtime proof uses.

## Bounded scheduling, verified

Independent three realm harness `harness.mjs` runs the real `ProgramClient`, `serveProgramWorker` and the actual bundled processor in one Node process with a genuine `MessageChannel` and an explicitly driven render clock. `repro-three-realm.mjs`, exit 0:

- Open at frame 128 applies at 128. Sender backing detaches once, receiver credit becomes resident, installed key matches.
- Over 8,192 rendered frames exactly eight progress notices reach the worker, one per 1,024 frames, and pump work follows each.
- Forty render calls on a stationary clock produce zero progress notices and zero worker posts.
- Two cold installs on two Sounds arriving on a stationary clock: one prepares on receipt, one waits. One quantum later it still waits. After the next coalesced progress wake both are prepared. No spin, no lost wake, bounded latency of one progress interval.
- Two live commands then a trigger submitted before any host reply: planning 4, applied 2, all three apply at their frame and the trigger carries a voice.
- Client end settles a pending caller once as generation ended, the worker and processor end, the processor keeps returning true and rendering silence, receiver resources stay quarantined until disposal, disposal terminates the worker and disconnects the node.
- Worker error event and a throwing render callback each settle once, post one `program-failed`, and leave in transit sender backing quarantined.

Browser instrumentation in both modes: largest worker message task 4 ms, largest processor message task 4 ms, largest process call 1 ms, at most 104 typed array bytes inside a process span. The observer copies each Sound contribution into extra diagnostic outputs and cannot change the mixed bus.

## Transport and lifecycle, verified in Chrome

Fresh private headless and headed sessions on the exact SHA, `verify-program-worklet.mjs`, both exit 0:

- 22 cases at 48 kHz and 44.1 kHz, four channels each, zero mismatches against the Node reference and zero against the oracle. Execution identity `audioface`/`ProgramHost`, `window` undefined, 128 frame quanta, two Sounds, two preparations, two compilations, two resident transfers.
- Native duplicate transfer refused before delivery with backing attached, then one detachment and ordered `valid, barrier` delivery.
- Credited transfer failure: typed error, 32,768 byte backing attached before and after, receiver credit 51,474 bytes retained until confirmed disposal, then zero.
- Lifecycle: open at 128, held voice, four cancelled supersessions, stale base refused, stale generation dropped, 128 ordinary entries then reserved cleanup as entry 129, unadmitted release refused with no history, new identity admitted, admitted replay without a new entry, tail held candidate applied at 727,424, too late cancel, close with a resident voice reclaimed at 1,526,912, lost generation settled once and disposal reclaiming to zero.
- Realtime: running 48 kHz context, base latency 5.8 ms, output latency 216 ms. During a 500 ms main stall the frame counter advanced 1,408 to 25,216 and the worker issued 11 commands, all applied at their requested frames and observed during the stall. Rebuild closed the old context, settled the pending caller unknown and opened `document.3.1` in generation 3.
- Legacy null test five events pass in both modes.
- Negative controls, ten runs, all exit 1 with the intended error: sample corruption, stale outcome, worker error, processor error, timeout, headless and headed.

Artifact hashes equal the author's manifest for all five outputs and were unchanged after each run.

## Identity claim

The per case `sampleSha256` is the pre sum Sound 1 capture from the host origin. For all 22 cases it equals the prior single runtime proof at `2c6b4b6` and `e6ddf9d`, and the mixed channel 0 hash differs from that prior value for all 22. The author digest calls these "final mixed sample hashes". The identity is real but sits at the pre sum signal point, which is the correct comparison point. Wording only.

## Seed map, verified

`ProgramPreparer.open` bounds the map, freezes a shallow copy and stores it on the Sound. The surface passes it to `planEdit` for commands, `reconcile` passes it for coalesced replans, and `open` compiles with it. `program-seeds.test.mjs` proves flat and nested equality before and after cold preparation, caller mutation isolation, unmapped defaults and an unknown placement refusal with zero records. Browser rows confirm flat equals nested equals repeat and other seeds differ.

## Findings

1. Low. `adapters/web/src/program-client.ts:103` measures the bare action while `adapters/web/src/worker.ts:78` measures the wrapped call and routes a failure to `failed`, which ends the generation. An action of 65,535 bytes passes main and the wrapped call exceeds 65,536. Reproduced in `repro-three-realm.mjs` case 4: the caller receives generation ended, the earlier open settles generation ended, main reports the capacity error, and a device rebuild follows. A map 100 characters long is refused per call as expected. Consequence is a bounded but avoidable generation loss for one oversized request. Measure the wrapped call in the client, or refuse the single call in the worker before ending the generation.

Observations, none blocking:

- `worklet.ts:137` and `:168` post directly while `postPortMessage` and `postWorkerControl` are two wrappers for the same suppression. One helper would do.
- `program-disposed` is sent only by proof scripts. Production disposal terminates the worker and closes the node instead, which is confirmed teardown by ownership rather than by message.
- A second or malformed `program-port` control is ignored once a port is attached; a first malformed one would throw inside the processor message task where nothing observes it.
- Browser runs recorded Node v24.20.0 from the login shell; probes and focused tests ran under v25.9.0.

## Gates

| Gate | Result |
|---|---|
| `pnpm run typecheck` | exit 0 |
| Focused: browser, seeds, residuals, host, game audio, worklet registration | 73 pass, 0 fail, 0 skipped |
| Bounds and sizing probe at exact SHA | exit 0, largest file 603, largest function 144 |
| Headless proof | 22 cases, realtime pass, null 5/5, exit 0 |
| Headed proof | 22 cases, realtime pass, null 5/5, exit 0 |
| Negative controls, 10 | all exit 1 |
| Three realm probe | 6 cases, exit 0 |
| Lead full gate log | 502 pass, lint, format, structure pass |

## Limits

Async correctness during one stall on one machine, not deadline or dropout certification. Instrumentation counts typed arrays and millisecond timing only. Arbitrary replay of rejected raw envelopes remains outside the contract. The three realm harness fakes the worker and node bridges; the direct port and all product code are real.

## Evidence

`/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-browser-review/`: environment before and after, `typecheck.log`, `focused.log`, `bounds.json`, `hygiene-static.txt`, `run-browser.sh` and `run-browser.log`, `headless-final/`, `headed-final/`, ten negative control directories with logs, `harness.mjs`, `repro-three-realm.mjs` and `repro-three-realm.log`.
