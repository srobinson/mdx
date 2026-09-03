---
title: Audioface foundation runtime probe specification
type: design
tags: [audioface, foundations, runtime, probes, admission, transitions]
summary: Proposed game and sustained edit experiments with bounded runtime ownership, source reuse, browser measurements, and falsifiers.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-dispositions, audioface-scout-foundations-runtime, audioface-scout-foundations-authoring]
confidence: medium
---

# Runtime probe specification

This specification follows the [lead dispositions](audioface-foundation-dispositions.md), [runtime Scout](../projects/audioface-scout-foundations-runtime.md), and [authoring Scout](../projects/audioface-scout-foundations-authoring.md) at `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`. Everything below is proposed. No prototype or benchmark ran in this phase. Shipping budgets remain unset.

## Caller and shared contracts

The minimal page opens two explicitly retained Sounds. Each references a pinned definition and an emitter, with separate seed inputs. `trigger({frame, take})` returns a bounded request ticket and opaque Voice identity. `edit({revision, change, frame})` returns a ticket. `release(voice, frame)` and `dispose()` are idempotent. Callers observe pending, applied, cancelled, or refused outcomes without coordinating compilation or installation.

Proposed interfaces, awaiting document spec agreement:

- `compile(document, dependencies, executionProfile)` returns issues or immutable `ProgramSpec`. It contains ordered operations, placement keys, typed ports, parameter slots, state layouts, latency, declared tail rules, and derived resource demand. The document compiler owns scope validation and edit classification. Engine descriptors own kernel limits. Control composes both without a patch to engine import.
- Program content identity includes resolved content, dependencies, sample rate, and execution format. Revision checks edit ownership. Sound and Voice IDs identify lifecycles. Placement keys identify state. Explicit seed labels determine randomness. Device generation rejects stale work. None substitutes for another.
- `prepare(spec, arena)` constructs private runtime state. `render(state, buffers, offset, frames, absoluteFrame)` uses existing storage. `transfer(old, next, frame)` exists only for named compatible layouts with a bounded cost. No generic serializer.
- Authored value provenance and mutability remain the document owner's responsibility. A derived value refuses writes. Whether a legal edit needs preparation is computed from kernel capability, topology, and installed capacity. Frozen/live metadata gains no synonymous edit flag.

Sound owns its current program, voices, shared effect state, and retirement. One root voice mix boundary suffices. Nested placements inherit scope. Definition capability does not silently create Sound state inside every Voice.

## Admission, scheduling, and reclamation

Use one scheduling owner in `createBusHost`. Remove the second queue in `StampedBus`; migrate offline audition through the host. Preserve frame ordering, equal frame insertion order, and release normalization. Bound queued entries, bytes, lookahead, insertion work, and commands due in any callback window before acceptance. Late commands acknowledge their actual frame. Excess commands refuse before enqueueing.

Admission first reserves a candidate, constructs and validates its complete DSP path, and checks the proposed victim and fade demand. Only then commit membership and victim changes together. Any failure preserves the previous signal, membership, and reservations. Render applies already prepared entries without constructors or validation failures.

`ResourceLedger` owns allocation reservations. Separate realm pools own disjoint memory, with receiver credits reserved before transfer. Count arena backing bytes once, reporting occupied capacity separately. Count shared programs once and independent state separately. Residency states are reserved, prepared, active, fading, draining, or retired. Transition membership references allocations already charged. Retirement releases them exactly once.

Every session fixture specifies finite limits for Sound count, program count, voices, delay frames, state bytes, scratch/output bytes, operation count, transition copies, compile graph size/work, install chunks, messages, pending tickets, and capture storage. Aggregate limits accompany per Sound limits. Derive test limits from fixture demand: exact fit passes, one unit short refuses, including staging, copies, and retirement slots. One compilation and one latest bounded document snapshot may coexist per Sound. Superseding edits cancel preparation before another starts. One pending program does not permit unlimited draining programs.

Charge render work for active, fading, draining, and overlapping programs, including silent effect buffers. Reserve the worst permitted controls. Pending programs consume memory and preparation/install work. Estimated operations bound executed work; measured timings determine whether that work fits a device. Byte accounting does not prove a bound on browser heap or garbage collection.

Reserve release/dispose/cancellation capacity when admitting a lifecycle. Release closes its excitation and reaches its declared tail deadline. Resource pressure leaves an edit visibly pending or refuses it, preserving old playback and tails. A pending edit retries only after retirement or explicit resubmission. No busy loop.

Cancellation before activation discards reserved/prepared state. Cancellation after activation reports too late and requires release or another edit. Equal frame insertion order decides cancellation races, with exactly one terminal outcome per ticket. Refund bytes and credits only after their owner confirms reclamation. Cancellation never refunds work already performed. Rebuild increments generation before asynchronous cleanup, rejects stale completions and messages, and closes the old device. Replay is explicit and uses unchanged recorded seeds.

Terminal acknowledgements have reserved slots per admitted ticket and survive telemetry loss. Sender credits cap outstanding port traffic. No further admission occurs when acknowledgement storage is full. Audio keeps rendering and retiring. Metering uses one outstanding bounded snapshot, coalesces while the UI stalls, and never carries lifecycle authority.

## Compile, install, and render boundaries

Compilation and buffer preparation run in a worker for the browser probe. Only serialized configuration and transferable buffers cross realms. A credited transfer delivers bounded chunks. The audio realm validates the packet boundary and binds realm local curated kernels into reserved storage. Installation has independent operation/byte limits and timing. It may refuse or remain pending while current audio continues.

Activation runs at an acknowledged frame and performs bounded pointer changes or explicitly charged state copies. Rendering uses offset/length arguments throughout, with no subarrays, dynamic array growth, report construction, promises, or graph traversal. Instrument the entire active call graph. Message deserialization and installation still need profiling: the [Web Audio rendering algorithm](https://www.w3.org/TR/webaudio-1.1/#rendering-loop) includes rendering thread tasks outside `process()`. Draft quantum options establish no browser support guarantee. Read actual output lengths and reject unsupported sizes without reallocating during rendering.

## Sustained edit probe

Use one held sine, frame based cutoff modulation, and an explicit delay return. No Studio import. Schedule cutoff changes inside a block. At 48 kHz, use a test trace with edits at frames 24,064, 48,064, and 48,065, then release at 96,000. Repeat at 44.1 kHz using frame conversion. These are fixtures, not shipping targets.

The first edit changes cutoff within installed capacity. The next adds delay from zero wet level. The third supersedes it with a larger delay. Zero level omitted by `bindEcho` therefore needs preparation. Also test a preallocated delay whose wet level crosses zero without new storage. Delay growth beyond capacity always prepares. Existing delay state continues to its declared end.

Compare two strategies on the same trace:

1. Compatible transfer moves unchanged oscillator phase, modulation clock, and matching filter state at activation. Incompatible/new delay starts empty. A layout mismatch refuses transfer before mutation.
2. Aligned crossfade initializes unchanged state with the same bounded compatible copies, then overlaps the programs. Incompatible downstream state starts empty. Use a fixture linear ramp of 256 frames and explicit latency alignment. Count both programs and alignment buffers. Rapid edits cannot reset an in progress transition or accumulate unbounded old graphs.

Lead challenge, U2: a whole output interpretation of disposition 5's crossfade can suppress an existing wet tail, conflicting with disposition 6 if that tail must survive. Proposed default crossfades dry output and excitation into each delay, then drains the old wet return without scaling it away. Unchanged wet state retains one owner; only retired incompatible effects drain. Keep a whole output fade as an explicitly tail changing comparator. Lead confirmation is required before accepting either sonic policy.

Identical content replacement acknowledges without transition. Assert exact samples for unchanged JS histories against uninterrupted rendering. For intentional edits, compare against a reference render implementing the selected transition equation. Measure peak adjacent sample difference, excess discontinuity versus reference, residual energy, request to audible change latency, copy work, peak residency, and final reclamation. Apply/cancel at the same frame, change revision during preparation, remove/reinsert a placement, release during transition, and exhaust overlap capacity. Any stale activation, phase reset, premature refund, missing tail, or nonzero occupied capacity after disposal falsifies the contract. Session teardown releases arena backing storage.

## Game and alternative comparison

Two independent mono emitter outputs feed separate spatial paths and one shared delay return. Final protection follows every dry and wet contribution. Muting/moving emitter A cannot change B's isolated pre-sum capture. The host owns routing; authored ports name no device destination.

Game tests reproduce the Scout's valid authored 12 kHz tone with +48 semitone envelope refusal, then compare the next render with an untouched control. Submit 100 same frame starts, cancel queued starts, saturate each limit individually, and release everything. Assert every accepted allocation stays charged through fade/tail retirement and all terminal outcomes remain correlated. Repeat with midblock starts and ragged slices. Count typed array views on active rendering, events, fades, and report boundaries.

Compare JS placement with native `StereoPannerNode` using identical precomputed mono input, width one, distance disabled, identical frame automation, gains, channel layout, summation order, shared return, and final protection. Capture both before comparison. This isolates the placement choice. An additional HRTF route demonstrates independent spatial capability and receives no equivalence/performance ranking against stereo pan. Count native nodes and automate setup explicitly.

For a whole graph alternative, feed the same input through gain, fixed integer delay, and stereo placement in JS and native graphs. Exclude feedback from this matched comparison. Gate normalized captures at maximum absolute error `1e-6` before timing, a provisional comparison tolerance without shipping acoustic authority. A WASM backend is deferred; a mixer benchmark cannot decide whole runtime architecture.

## Measurements and gates

Node proves transactional refusal, deterministic schedules, exact same implementation replay, bounds, cancellation, layout transfer, and reclamation. It cannot prove browser installation safety or device deadlines. Browser offline capture proves signal routing/equivalence. Realtime runs measure deadline behavior and asynchronous lifecycle.

Record OS, CPU, browser/version, power mode, sample rate, actual quantum, output device, latency settings, code/program/trace hashes, and instrumentation overhead. Start with installed desktop browsers, explicitly recording unavailable engines. This matrix claims no shipping coverage.

Each browser candidate gets cold install, five seconds warmup, and three randomized 30 second runs at each doubled workload until refusal or deadline failure. Repeat under a 500 ms main thread stall and event overload. Bound recordings and request logs. Record compilation, transport, install, state copy, kernel, callback, and whole rendering thread timings separately. Compare maximum and p99.9 costs with actual quantum duration. Record queue/byte peaks and acknowledgements. Use browser traces for native work and garbage collection. Unsupported timing visibility produces an inconclusive comparison.

Fail on any functional invariant, nonfinite output, resource overrun, escaped callback exception, or observed dropout. Compare recorded device loopback with expected output when available. Callback frame counters and percentiles alone cannot prove no dropouts. Retain captures for listening and inspect transitions before accepting sonic behavior. A passing local run leaves shipping performance undecided until the owner supplies environments, workloads, and numeric budgets.

## Source bindings and isolated implementation

Only a subsequently authorized isolated worktree may implement this map. Source paths below name baseline owners; new filenames and symbols are proposals.

| Disposition | Existing owner and proposed work |
| --- | --- |
| Reuse R1/R3, refactor during | `packages/engine/src/source-generator.ts` `phaseAccumulator`, `layer-filter.ts` `filtered`, `layer-echo.ts` `echoStage`: expose explicit state and spans, reuse algorithms. `voice-lifetime.ts` `beginVoice` and `packages/contract/src/echo.ts` `echoTailFrames`: preserve declared retirement. |
| Refactor first R4/Q1/Q2/Q3 | `packages/engine/src/master-bus.ts` `MasterBus.start`, `voice-pool.ts` `VoicePool`, `voice-renderer.ts` `VoiceRenderer.renderBlock`, `command-queue.ts` `CommandQueue`, `renderPart`: atomic preparation, total residency, bounded scheduling, spans. Remove replaced allocation paths. |
| Refactor during R4/R6 | `packages/control/src/bus-host.ts` `createBusHost`, `packages/engine/src/stamped-bus.ts` `StampedBus`, `packages/control/src/audition.ts` `auditionCommands`: one host schedule. `adapters/web/src/game-audio.ts` `GameAudio`, `RealtimeDevice`, and `worklet.ts` `AudiofaceProcessor`: tickets, generations, multioutput, credits. `packages/contract/src/bus.ts` `HostMessage`, `WorkletMessage`: one protocol. Delete report aging authority. |
| Reuse R2, document owned seam | `packages/patch/src/patch-resolution.ts` `PatchResolver.resolveAddress`, `voice-binding.ts` `bindEcho`, `registry/definition.ts` `ParameterDefinition`; `packages/contract/src/seed.ts` `rootSeed`, `childSeed`, `drawAt`; `ids.ts` `Brand`: reuse metadata/seed rules. Document probe supplies deletion, scope, and identity guarantees. |
| Deviate R5/Q4 | `packages/engine/src/stereo-image.ts` `ListenerSchedule`, `StereoImage`; `master-limiter.ts` `MasterLimiter`: per emitter routing and final protection. Delete global listener replacement from migrated path. |
| Reuse R7/R8 | `packages/control/src/audition.ts` `nullVerdict`, `test/worklet-null.test.mjs` `throughHost`, `scripts/verify-structure.mjs` `ALLOWED_EDGES`: extend proof and preserve package boundaries. |

Sibling filenames inherit the preceding directory. Create `packages/contract/src/program.ts` for `ProgramSpec` and demand types, `packages/engine/src/program-runtime.ts` for prepared execution, and `packages/control/src/runtime-budget.ts` for `ResourceLedger`. Reuse these across all three probes. Change `packages/engine/src/layer-stage.ts` `LayerStage`/`SourceGenerator` and every consumer to spans. Search before each symbol. Consolidate touched envelope validators and Waveform ownership. Delete obsolete wrappers and migrated fixed-shape paths; leave unrelated catalogue/recipe cleanup deferred. Keep files below 700 lines and functions below 150.

Create `test/foundations/runtime.test.mjs`, `browser.ts`, `worker.ts`, and `fixtures.ts`. Extend `apps/web/build.mjs` `bundle`/`emit` with minimal page/worker entries, reusing its bundler. Export bounded JSON results from the page. Proposed commands:

```sh
node --test test/foundations/runtime.test.mjs
node --test test/worklet-null.test.mjs
pnpm --filter @audioface/app-web build
node scripts/verify-structure.mjs
```

The generated `apps/web/dist/foundation-probes.html` exposes Run game, Run edits, Run comparisons, and Export results. Page assertions set `h1.dataset.verdict` to pass/fail/inconclusive and name every failed invariant.

Implementation units: first failing admission/bounds fixtures and repairs; then shared contracts plus deterministic Node runtime; then sustained transitions and cancellation; then browser routing/capture and measurements. Each unit passes its focused assertions before the next. Document probe interfaces integrate before browser work. No broad suite was run for this specification.

Unresolved: **3**. U1 is agreement with the document spec on compilation, edit tickets, placement/seed mapping, and deletion interfaces. U2 is the tail/crossfade policy above. U3 is shipping acceptance inputs. Excluded: full Studio, assets, arbitrary plugins, nested voice spawning, external feedback graphs, general tempo/undo/macros, and production migration.

Verification: both Scout hashes matched. Checked 35 symbols across 26 baseline files, artifact schemas, links, word limits, and clean repository. Only assigned artifacts were written.
