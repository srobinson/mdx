---
title: Audioface foundation real worker and browser host milestone
type: projects
tags: [audioface, foundations, worker, audioworklet, browser, lifecycle, verification]
summary: Real worker preparation drives the production AudioWorklet host through a direct transferred port, with corrected call admission and exact browser proof.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundations-runtime-host-node-build, audioface-foundations-runtime-host-node-residuals]
confidence: high
---

# Real worker and browser host milestone

The worker and browser host milestone is implemented at `3221511a59170b3fafaaa6924cf1a25f98a26b37` on `probe/foundation-integrated`. Independent delta review remains pending. The clean source baseline was `e6ddf9da996e0bf87b0fa3eb0be5f1c7f69f539f`.

The source checkpoint contains four commits:

- `34d16473ccd3eff29ebd8abaa1fb13cd86641784`: real worker, direct port and production AudioWorklet host.
- `a9ae324cf5db07310431c3bebcce13a3a46722dc`: bounded Float32 browser capture encoding.
- `efa6af6f8283efe0dfd362b74c74c11bdf16d2ca`: terminal settlement for callback and device failure.
- `3221511a59170b3fafaaa6924cf1a25f98a26b37`: complete call envelope admission at the main to worker boundary.

The active [program host specification](/Users/alphab/.mdx/design/audioface-foundation-program-host-spec.md) has SHA256 `3f32506eb9bbbddc3a9500455d3fa177e23aef370cd3ff2dfbd0f7d8f8aa7574`. During implementation, the lead approved an optional immutable `SeedMap` at `ProgramPreparer.open`. The worker snapshots the caller map, retains it for the Sound lifetime and reuses it through reconciliation and cold preparation. Default compilation remains unchanged. Tests cover flat and nested equivalence before and after cold preparation, mutation isolation, edits during opening and coalesced reconciliation.

The only source writes were made in the integrated worktree. The main README remains SHA256 `f34eb76a9bd6818ccb3ae8243755c6e4598d93efccfe182d5d37bf550f254525`. Specifications, prior reports, other checkouts, remotes and PRs were left unchanged.

## Reuse and deletion

The implementation follows the [reuse map](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-browser-build/reuse-map.md).

| Authority | Reused path |
| --- | --- |
| Document state and preparation | The worker instantiates the existing `ProgramPreparer`, including its composition surface, planner, compiler, caller tickets, transfer accounting and receiver credit protocol. |
| Audio host | The production processor creates the existing `createBusHost` and `ProgramHost`. The existing queue, clock, ledger, preparation, graph, kernels, summation and limiter remain authoritative. |
| Scheduling | Render progress coalesces at 1,024 frame intervals. The worker acknowledges one outstanding progress notice. `ProgramHost.pump()` then runs in an AudioWorklet message task. `process()` advances the real clock and queues candidates. |
| Device lifetime | `GameAudio` and its existing device owner now manage one worker generation, one context and terminal cleanup. There is no parallel rebuild manager. |
| Browser proof | The 22 existing fixtures, Node reference, oracle, browser session driver, source identity checks, artifact hashing and dirty tree checks remain shared. |

The obsolete direct test processor and page were deleted after their callers migrated:

- `scripts/test-support/program-worklet.ts`
- `scripts/test-support/program-worklet-page.ts`

The retained `ProgramProofRun`, fixtures, reference renderer, ramp helpers and oracle continue to serve Node and browser comparison. The production browser path contains one host, one preparer, one scheduler and one direct program protocol.

## Realm and ownership trace

| Stage | Realm | Owner and transition |
| --- | --- | --- |
| Bootstrap | Main | Creates the `AudioContext`, `AudioWorkletNode`, `Worker` and `MessageChannel`. It transfers one endpoint to the worker and the other endpoint to the worklet. |
| Document work | Worker | `ProgramPreparer` owns document mutation, planning, compilation, backing preparation, caller results and sender transfer accounts. |
| Transfer | Worker to AudioWorklet | `ProgramPort` posts each `ProgramPost` once through the direct port. A successful backing transfer detaches the worker buffer and moves the charged installation into transit. |
| Admission and binding | AudioWorklet message task | `ProgramHost.receive` validates bounded envelopes and reserves receiver credit. Coalesced render progress permits paced `pump()` work. Preparation and graph binding remain outside the render callback. |
| Activation and rendering | AudioWorklet render callback | Existing host progress, queue and render logic activate stamped work at the actual device frame. `ProgramRuntime` renders each Sound. `MasterBus` sums in stable open order and applies the existing limiter. |
| Diagnostic capture | AudioWorklet render callback | A proof observer copies separate Sound contributions at the existing pre sum point into extra diagnostic outputs. Output zero remains the production mixed and limited bus. |
| Outcomes | AudioWorklet to worker to main | Audio outcomes travel through the direct port to `ProgramPreparer`. Bounded worker control replies settle the corresponding main caller latch. |
| Teardown | Main, worker and AudioWorklet | The context finishes or closes before the main owner confirms disposal. Ports, listeners, node and worker then close. Unknown outcomes settle once. Quarantined transfer and receiver state clear only after confirmed disposal. |

The main thread never relays direct program envelopes after transferring the channel endpoints. Main control messages bootstrap the two realms and expose bounded proof state. The direct port has one listener and one native post per envelope. There is no reconnect replay.

`ProgramClient.request` now constructs the `WorkerCall` once, measures that complete envelope, admits its caller latch, then posts the same object. A request above the 65,536 byte cap fails before serial consumption or caller admission. Worker ingress keeps its independent check. The focused proof covers 65,532 bytes, 65,535 bytes and the next representable size, 65,538 bytes. The rejected call leaves the generation active, preserves an existing pending call and lets a later valid call apply.

## Transport conformity

`ProgramPort` can raise `ProgramPostNotDeliveredError` for a locally closed port or for the narrow synchronous native `DataCloneError` path when every supplied backing buffer remains attached with its original byte length. This follows the message port serialization order defined by the [HTML Standard](https://html.spec.whatwg.org/multipage/web-messaging.html). Other native or callback failures end the generation as application unknown. Resources remain quarantined until teardown confirms disposal.

The browser proof submits one duplicate ArrayBuffer in a native transfer list. Chrome refuses it before delivery, both byte lengths remain unchanged and the post count does not advance. A subsequent valid post detaches its eight byte buffer once. The receiver observes `valid` followed by `barrier`, once each.

The credited transfer failure uses a real `ProgramPreparer` installation. The duplicate list fails with the typed pre delivery error, leaves the 32,768 byte backing attached and produces no receiver preparation. Since receiver credit was already granted, the generation ends and both sides retain their charged ownership until confirmed disposal. Disposal clears both reservations. No automatic resend occurs.

Rejected cleanup requests require a new identity before another admission attempt. Same identity replay is available only after admission. The lifecycle proof fills the ordinary queue to 128 entries, refuses one more ordinary command, then admits a release through reserved lifecycle capacity as entry 129. A pre admission release refusal leaves no history. Its new identity retry is admitted. Replaying the admitted release identity returns its prior pending result without another queue entry or history record.

## Offline browser results

Fresh private headless and headed Chrome 152 sessions each built and executed the shipping worker and production AudioWorklet processor. Each mode passed all 22 cases at 48 kHz and 44.1 kHz. Every case captured four channels: mixed stereo output plus one pre sum channel for each retained Sound. All 88 per mode browser to Node channel comparisons had zero mismatches and maximum difference zero. Both oracle comparisons per case also had zero mismatches.

The 22 `sampleSha256` identities are pre sum Sound 1 captures. Each matches the corresponding value from the prior clean `e6ddf9d` single runtime proof. All 22 final mixed channel 0 hashes differ from that prior value. Each final mixed capture matches the current corresponding Node reference with zero mismatches. Flat, nested and repeat cases share the expected pre sum identities. Alternate seeds produce distinct identities. Ramp boundary cases remain distinct. Captures reject truncated byte payloads, incorrect byte counts and nonfinite samples. Base64 encoded Float32 bytes preserve exact bits, including negative zero.

Two Sounds remain independently visible before summation. Triggers and live commands carry stamped nonzero device origins. Sender buffers detach after successful transfer, receiver credit becomes resident and close refunds it. The processor execution record reports 128 frame quanta and `window === undefined`, confirming AudioWorklet realm execution.

Both modes also pass the five legacy null events. The proof compares the exact emitted `program-worker.js` and `program-worklet.js` bytes with the embedded sources used by the page.

| Artifact | SHA256 |
| --- | --- |
| `index.html` | `52d8bf55f7aef4c46585beb7c2c5e6b0413e42be7718a996dc2ea3308a46339f` |
| `null-test.html` | `5b1eb98a1709149454e6a5b7c0e6a320060e78dbba3aa0ff9e31c1c92552019d` |
| `program-test.html` | `a1df22897543357f65915e65c980f8e24f8d6c9d46b19781493c281cdcd8c181` |
| `program-worker.js` | `7dc3b028d854e8b0615bdeca8263f833dc65f5ba73bf4733a0d251f16a196cc0` |
| `program-worklet.js` | `3584011e097de4a64819b9d6ef3423978a39a0e8581154c096929c7ce78465e5` |

## Lifecycle results

The controlled `OfflineAudioContext` proof advances 1,600,000 frames with suspensions at chosen quantum boundaries. It proves these outcomes:

- Open applies at frame 128. A sustaining Voice triggers at frame 256 and remains resident while a cold candidate waits.
- Four superseded or cancelled preparation requests settle `cancelled`. Candidate state returns from one to zero.
- A stale installed base is admitted and then refused with the authoritative stale base result. A stale generation response is dropped.
- Ordinary saturation reaches 128 entries. Reserved lifecycle capacity admits entry 129 while ordinary work is full.
- A held tail delays candidate activation. The candidate later applies at frame 727,424. Cancellation after application reports too late without rewriting the applied outcome.
- Release applies at frame 768. Close with a resident Voice completes at frame 1,526,912 with reclamation confirmed.
- Reclaimed and disposed states contain zero Sounds and a zero reserved resource vector.
- A lost generation after transferred resident open settles its caller once as `generation-ended` and `application: unknown`. Sender and receiver remain quarantined until explicit disposal. Disposal clears the sender transfer record and receiver reservation.

Worker error, worker message error, worklet callback failure, processor error, direct port failure and external context closure converge through the same terminal generation path. All pending caller latches settle once. A stalled bootstrap can be interrupted, and an obsolete bootstrap cannot create a device after teardown.

## Advancing device result

Realtime status is `pass` in both headless and headed runs. Chrome created an advancing 48 kHz `AudioContext` with 5.8125 ms base latency, 216 ms output latency and 128 frame callbacks. During a 500 ms main thread stall, the frame counter advanced from 1,408 to 25,216. The worker independently issued 11 correlated commands, and their applications advanced from frame 4,224 through frame 24,704.

The same proof rebuilds the device. The previous context reaches `closed`, the previous client reports disposed with zero pending callers and the old pending outcome settles generation ended and application unknown. A fresh explicit replay opens `document.3.1` in a new generation.

This result establishes asynchronous progress and correlated application during a main thread stall. It does not certify p99 latency, deadlines, dropout behavior or a production device matrix.

## Instrumentation limits

Proof instrumentation counts Float32 backing buffers, typed array views and observed elapsed time separately for worker message tasks, AudioWorklet message tasks and `process()` calls. Across offline cases, the largest observed worker message task was 5 ms, the largest AudioWorklet message task was 4 ms and the largest process call was 1 ms. The counters recorded at most 104 typed array bytes inside a process span.

These counters cover the instrumented typed array constructors and views. They exclude arbitrary JavaScript objects, browser structured clone internals, garbage collection and unobservable engine allocation. Empty probe timing is retained beside each run. The evidence makes no heap allocation free, garbage collection or deadline claim.

## Gates and failure controls

The exact SHA verification manifest is [verification-final.json](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-browser-corrections/verification-final.json). `pnpm run check` exits 0 with 503 tests passed, zero failures and successful typecheck, lint, format and structure checks. The repeatable boundary probe passes the existing slot, parameter, connection, voice, program, batch, backing and metadata limits. The largest checked file is 603 lines. The largest checked function is 144 lines.

Each browser mode runs five negative controls. Sample corruption, stale outcome corruption, worker failure, processor failure and timeout all exit 1 with the intended error. Every command records the same clean source SHA before and after execution. Browser sessions created by the verifier are closed. Existing user sessions remain untouched.

Two failed development attempts are retained as diagnostic evidence. The first exposed oversized JSON sample transport through the browser driver and led to bounded binary capture encoding. The second showed that Chrome offline processing did not surface the injected callback failure through the expected event, which led the production processor to catch callback failures, emit one terminal control message and stop.

Repeat the complete exact SHA proof with:

```sh
node /Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-browser-corrections/verify-final.mjs 3221511a59170b3fafaaa6924cf1a25f98a26b37
```

## Pending scope

Independent delta review of `3221511a59170b3fafaaa6924cf1a25f98a26b37` remains required. Arbitrary replay of rejected raw envelopes remains outside the contract. The worker document selection is a prototype boundary and does not define product library persistence. Voice pooling, active transitions, spatial comparators, deadline certification and a broader device matrix remain future milestones.

The persistent report and digest are readable. Markdown indexing was attempted and returned `Path outside root` for `/Users/alphab/.mdx/projects/audioface-foundations-runtime-host-browser-build.md`. The configured root was left unchanged.
