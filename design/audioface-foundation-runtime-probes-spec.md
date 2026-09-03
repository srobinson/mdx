---
title: Audioface foundation runtime probe specification
type: design
tags: [audioface, foundations, runtime, probes, admission, transitions]
summary: Proposed shared program and edit contracts, bounded runtime experiments, transition comparators, and browser verification gates.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-document-spec, audioface-foundation-dispositions, audioface-scout-foundations-runtime]
confidence: medium
---

# Runtime probe specification

Baseline `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`. The [correction decisions](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/correction-brief.md) govern this replacement candidate and supersede conflicting review proposals. All tests below remain proposed. No shipping budgets or sonic policy are accepted.

## 1. Shared contracts and ownership

One serializable `ProgramSpec` in contract serves every probe. Patch owns authored composition, validation, compilation, and edit classification. Control injects engine-owned pure kernel preparation capabilities. These derive normalized configuration and requirements before mutable instances exist. Engine-private execution objects derive from `ProgramSpec`. No second public program type or composition package exists.

`ProgramSpec` contains ordered operations, placement keys, kernel ids and implementation versions, normalized configuration, initial parameters, typed ports, routing, seed labels, execution profile, state descriptors, latency, and tail requirements. `ProgramKey` hashes its canonical immutable content, including sample rate and channel shape. Lineage and document revision identify ownership separately. Runtime root/take seeds remain explicit instance/trigger inputs. No structural digest or cache is required.

Each retained Sound pins a composition revision. References retain immutable snapshots keyed by lineage and revision within a bounded library. Missing pins and reference cycles produce typed errors before expansion. Copies mint fresh lineage. Library edits never implicitly repin retained Sounds.

Nested placements inherit scope; one root Voice mix boundary feeds Sound state. Reject incompatible capabilities in either direction. Broadcast/reduce and nested voice spawning are excluded. Canonical placement ordering and stable Voice admission sequence determine sums, independent of storage ordering. Control binds `{SoundId, outputPort}` to an emitter and preserves independent outputs until spatial routing.

## 2. Authored edits and audible application

The minimal caller opens two retained Sounds, triggers with absolute frame and take seed, and receives a bounded ticket plus opaque Voice identity. Release and disposal are idempotent. Sound owns voices, current program, shared state, and retirement.

`surface.apply` alone checks authored revisions and produces `EditPlan`. Control submits its effect, attaching Sound id, ticket id, generation, base revision, and absolute frame. `ParameterCommand` carries the target path, parameter key, value, and explicit timing policy. Engine and GameAudio never reinterpret authored changes. Control owns compilation scheduling, installation, and correlated pending/applied/cancelled/refused outcomes.

Authored acceptance advances document revision. Instance applied revision advances only on audible application. Refusal preserves playback and exposes desired/applied divergence through the preview boundary. Program identity cannot replace ticket or revision checks. Supersession names tickets. Stale completions cannot activate or roll back newer edits.

The document planner uses kernel capability, old/new configuration, topology, and installed capacity. Derived values refuse. Frozen values remain captured until preparation; live values use their declared read rate and explicit event boundaries. The curated cutoff implementation gains a live command slot. A legal live command changes instance state without compilation or installation. Later preparation from the edited document may produce a different `ProgramKey`.

One compilation and one latest bounded snapshot may coexist per Sound. New edits supersede pending preparation. If the plan's base no longer matches the applied revision, the document surface replans the latest desired snapshot against installed capabilities. Control never supplies a second classifier.

## 3. Admission, installation, and reclamation

Admission checks demand and compatibility before pool mutation. Provisional reservations cover candidate construction. Complete path validation precedes atomic membership/victim commit. Failure reclaims provisional state and preserves previous membership, signal, and reservations. Render consumes prepared entries without constructors or validation failures.

Engine descriptors declare owned bytes, alignment, buffer capacity in frames/channels, operations per rendered frame, installation operations, copy bytes, latency frames, and tail frames. Voice demand multiplies by admitted multiplicity; Sound state counts once. Controls reserve their worst permitted demand, including tail changes. Declared operations bound work; measured CPU cost determines device feasibility.

`ResourceLedger` charges reserved, prepared, active, fading, draining, and transition allocations until actual reclamation. Shared programs and arena backing count once; occupancy is separate. Realm pools are disjoint. Receiver credits precede transfer. Overlap, alignment buffers, silence processing, and pending installation remain charged. Refund bytes and credits exactly once after owner confirmation; performed work is never refunded.

Fixtures bound Sounds, programs, voices, delay/state/scratch/output storage, render/copy/install work, graph size, compilation work, messages, tickets, transitions, retirement slots, and captures. Aggregate limits accompany per Sound limits. Exact fit passes; one unit short refuses. Pending replacements cannot accumulate unlimited draining programs.

One scheduler in `createBusHost` preserves frame order, equal-frame insertion order, and release normalization. Bounds cover entries, bytes, lookahead, insertion work, and commands due per callback window. Late commands acknowledge actual frames. Release/dispose/cancellation and terminal acknowledgements reserve capacity at lifecycle admission. Overload stops new admissions while audio renders and retires. Telemetry is one coalesced, expendable snapshot with no lifecycle authority.

Cancellation before activation reclaims prepared state. After activation it reports too late; release or another edit is required. Equal-frame order resolves races with one terminal outcome per ticket. Rebuild increments generation before cleanup, rejects stale messages, and closes the old device. Replay is explicit with recorded seeds. Pending retries occur only after reclamation or explicit resubmission.

Browser compilation and buffer preparation run in a worker. Credited, bounded chunks cross realms. Audio-side packet validation and kernel binding have independent byte/operation/timing budgets. Installation can remain pending or refuse while playback continues. Activation occurs no earlier than the requested frame or completed preparation and acknowledges its actual frame. It performs bounded pointer changes or charged copies.

Rendering uses offsets and lengths, with no subarrays, dynamic growth, report construction, promises, or graph traversal. Instrument the full active call graph. Read actual quantum lengths; unsupported sizes refuse without render-time reallocation. Message handling and installation count as audio-thread work: the [Web Audio rendering algorithm](https://www.w3.org/TR/webaudio-1.1/#rendering-loop) processes rendering-thread tasks outside `process()`.

## 4. Sustained editing and transition comparators

The held sine/filter/delay fixture uses the shared compiler and `surface.apply` throughout. At 48 kHz, cutoff changes at frame 24,064, omitted delay is added at 48,064, larger delay supersedes it at 48,065, and release occurs at 96,000. Repeat at 44.1 kHz with converted frame stamps. Test cutoff as an unsmoothed step and separately as a 128-frame linear ramp. The step takes its target at frame F; the ramp interpolates from its value at F with weight `clamp((frame-F)/128,0,1)`. Both survive ragged slicing. Assert zero compilation/installation on the eligible command path and audible structural adoption by the held voice.

Test positive delay-level changes and preallocated zero crossing as commands only when capability, storage, and tail bounds permit. Omitted zero-level delay and growth beyond capacity prepare. Enable/membership changes and envelope lifetime changes require contextual classification; no default continuous rule covers them.

Transfer is curated. Before committing state or reservations, compare kernel id/version, declared state layout/version, execution profile, sample rate, channels, and kernel-specific configuration/capacity compatibility. Matching paths alone confer no permission. Same-path kernel replacement and delay growth must refuse transfer or use a separately reserved comparator. Transfer preserves supported oscillator phase, modulation clock, and filter state; incompatible new state starts empty.

Compare transfer with a latency-aligned 256-frame linear program transition using bounded compatible copies and weight `w=clamp((frame-F)/256,0,1)`. Rapid edits cannot reset an active transition or accumulate unbounded old graphs. For the curated delay, audition two explicit policies:

1. Whole-output crossfade scales the old complete output away. This deliberately changes its wet tail.
2. Split dry-output and excitation crossfade retains old wet history through a declared wet port. For ramp `w`, dry output is `(1-w)*dryOld+w*dryNew`; incompatible delay inputs receive their respective weighted excitation, and both wet outputs remain unscaled. New incompatible delay starts empty. Compatible wet state has one owner receiving the combined excitation, with one wet contribution.

The split kernel extracts existing echo math with shared consumers, without duplicate DSP. Old excitation ends with the fade; retirement is bounded by last excitation plus declared tail. Unsupported wet-preservation requests remain pending/refused. Resource exhaustion preserves old playback and tails. Neither comparator is a shipping default, and no silent tail-cutting fallback or arbitrary-graph preservation claim is allowed.

Unchanged histories require exact same-implementation samples against uninterrupted rendering. Intentional transitions compare with an independently wired reference implementing that policy. Different wet histories cannot null compare. Measure adjacent-sample peak, excess discontinuity, residual energy, audible latency, copy work, peak residency, and reclamation. Test equal-frame apply/cancel, edits during preparation, release during transition, removal/reinsertion, incompatible transfer, and exhausted overlap. Stale activation, phase reset, premature refund, missing required tail, or retained occupancy after disposal fails. Teardown releases arena backing.

## 5. Game, browser, and measurement gates

Two independent mono emitter outputs feed separate spatial paths and a shared delay return. Final protection follows all contributions. Moving/muting A cannot alter B's isolated pre-sum capture.

Game tests reproduce the valid authored 12 kHz tone with +48-semitone envelope refusal, then compare the next render with an untouched control. Submit 100 same-frame starts, cancel queued starts, saturate each limit, release everything, and verify correlated outcomes and refunds through retirement. Repeat midblock and with ragged slices; count typed-array views across events, fades, and reports.

Compare JS placement with native `StereoPannerNode` using identical precomputed mono input, frame automation, width one, distance disabled, gains, channel layout, summation order, return, and protection. An HRTF demonstration receives no stereo-pan equivalence ranking. A matched whole-graph comparison adds gain and fixed integer delay, excluding feedback. Captures must meet maximum absolute error `1e-6` before timing. This provisional tolerance grants no shipping authority. WASM remains deferred.

Node proves behavior, bounds, and reclamation only. Offline browser captures test routing/equivalence; realtime runs test asynchronous installation and deadlines. Record environment, browser/version, power mode, sample rate, actual quantum, device/latency settings, code/program/trace hashes, and instrumentation overhead. Record unavailable browsers without claiming coverage.

Each candidate gets cold installation, five-second warmup, and three randomized 30-second runs at doubled workloads until refusal or deadline failure. Repeat with a 500 ms main-thread stall and overload. Bound captures/logs. Record compilation, transport, installation, copies, kernels, callbacks, whole rendering-thread time, queue/byte peaks, and acknowledgements. Compare maximum and p99.9 costs with quantum duration. Browser traces cover native work and garbage collection; unavailable timing visibility means inconclusive.

Fail on violated invariants, nonfinite samples, overruns, callback exceptions, or observed dropouts. Use device loopback where available. Counters and percentiles cannot establish dropout absence. Preserve listening captures. Owner environment/workload budgets and sonic acceptance remain pending without blocking local tests.

## 6. Source reuse and three deliverables

Only subsequently authorized isolated worktrees implement this map. Sibling filenames inherit the preceding directory; new symbols/files are proposals.

| Baseline owner | Consuming change |
| --- | --- |
| `packages/patch/src/registry/definition.ts` `ParameterDefinition`; `registry/parameters.ts` `PARAMETER_ROWS` | Move shared declarative types/dependencies to contract; reuse metadata with contextual capabilities. |
| `packages/control/src/surface.ts` `apply`; `packages/patch/src/patch-resolution.ts` `PatchResolver.applyConnection`; `patch-validation.ts` `validateConnectionCycles` | Reuse transaction and arithmetic; extract only with both consumers. Reference-cycle validation is distinct. |
| `packages/engine/src/source-generator.ts` `phaseAccumulator`; `layer-filter.ts` `filtered`; `layer-echo.ts` `echoStage`; `voice-lifetime.ts` `beginVoice`; `packages/contract/src/echo.ts` `echoTailFrames` | Explicit state/spans, cutoff commands, shared split echo math, declared retirement. |
| `packages/engine/src/master-bus.ts` `MasterBus.start`; `voice-pool.ts` `VoicePool`; `command-queue.ts` `CommandQueue`; `stamped-bus.ts` `StampedBus`; `packages/control/src/bus-host.ts` `createBusHost` | Repair admission/residency; delete the second schedule and replaced allocation paths; migrate offline audition. |
| `adapters/web/src/game-audio.ts` `GameAudio`; `worklet.ts` `AudiofaceProcessor`; `packages/engine/src/stereo-image.ts` `StereoImage`; `master-limiter.ts` `MasterLimiter` | Tickets, generations, credits, independent routing; delete report-aging authority and migrated global-listener replacement. |
| `packages/contract/src/seed.ts` `childSeed`, `drawAt`; `scripts/verify-structure.mjs` `ALLOWED_EDGES`; `test/worklet-null.test.mjs` `throughHost` | Reuse seeds, package gate, and host proof. Patch never imports engine. |

The three coherent deliverables are:

1. Contracts/composition proof: one `ProgramSpec`, `EditPlan`, and `ParameterCommand`; legal authored flat ids with explicit fixture seed mapping outside authored identity; independently hand-wired kernels, values, connections, and sum order, no second interpreter. Assert sample equality with mapped seeds without requiring equal keys for differently keyed placements. Assert immutable pins, both scope directions, stable Voice order under shuffled storage, and deletion after setting `b` to 440 followed by fresh default 660 without stale connections.
2. Bounded runtime/game proof: shared `packages/engine/src/program-runtime.ts`, control-owned `ResourceLedger`, admission repairs, scheduling, and game assertions.
3. Sustained-edit/browser measurement proof: shared `test/foundations` fixtures, worker/page, transitions, captures, and bounded JSON export. Extend `apps/web/build.mjs` `bundle` and `emit`. Page verdict is pass/fail/inconclusive with named failures.

Internal steps use focused tests before progression. Reuse the existing bundler and null fixtures. Proposed gates: `node --test test/foundations/runtime.test.mjs`, `node --test test/worklet-null.test.mjs`, `pnpm --filter @audioface/app-web build`, and `node scripts/verify-structure.mjs`.

Search before adding symbols. Delete replaced implementations when callers migrate. Consolidate touched duplicates only. Files remain below 700 lines; functions below 150. Exclude certification, general undo, assets/music systems, arbitrary plugins, unrelated cleanup, and production migration. Exact corrected interfaces require independent delta verification before builds. Unresolved engineering conflicts: 0; pending owner decisions: 2, shipping sonic policy and performance acceptance inputs.
