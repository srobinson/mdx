---
title: Audioface foundations runtime host next scout
type: projects
tags: [audioface, foundations, runtime, host, worker, worklet, tickets, scout]
summary: Read-only reuse map at frozen ea487fb across the composition surface, control ledger, ProgramRuntime, the one bus host scheduler and the web device lifecycle, with one recommended next unit, ticketed cross-realm program installation, its browser proof, gates and open decisions.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundations-program-worklet-review, audioface-foundations-program-worklet-proof, audioface-foundations-program-runtime-corrections-review, audioface-foundations-program-runtime-build, audioface-scout-foundations-runtime]
confidence: high
---

# Audioface foundations runtime host next scout

Target `ea487fbb031ec467c24d06ea60008387fc9cb7c7`, worktree `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser`, pristine before and after (0 changes, 0 untracked). Read directly: `audioface-foundation-runtime-probes-spec.md` sections 1 to 3, 5 and 6, `audioface-foundation-document-spec.md` sections 5 to 8, `program-runtime-decisions.md`, and every source file named below. One Node probe ran outside the checkout; it is stored with its output in `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-next-scout/`. Nothing in any checkout was written. Astra's integrated work was not read.

## 1. Reuse map, as built

| Authority | Where | What it owns today | Gap against probes spec sections 2 and 3 |
| --- | --- | --- | --- |
| Planner and compiler | `packages/patch/src/composition/plan.ts` `planEdit`, `commandsFor`; `compile.ts` `compile`, `retainedConfiguration`, `sameConfiguration` | The one classifier and the one compiler. `planEdit` compiles inside `apply` for every `prepare`. | Compile runs on whichever thread calls `apply`. No ticket, no generation. |
| Document surface | `packages/control/src/composition-surface.ts` `createCompositionSurface` | Sealed library, `expectedRevision`, whole batches, revision plus one on acceptance, `installed` lookup injected by an owner. | Synchronous. The comment at lines 22 and 23 already reserves tickets, generations and cross realm acknowledgements as separate. |
| In-process owner | `packages/control/src/composition-runtime.ts` `createInProcessCompositionSurface` | Opens a Sound per `CompositionId`, installs or commands the runtime synchronously, reports `applied`, `refused` or `unopened`, tracks desired versus applied revision. | Same realm as the runtime. A refused cold replacement stays refused; there is no pending state, no ticket, no activation frame. This is the alternate path the next unit replaces. |
| Ledger | `packages/control/src/resource-ledger.ts` `ResourceLedger` | One aggregate account, `reserve` returns a refund closure, `performedInstallationOperations` never refunded. | One realm. No receiver credits, no disjoint pools, no prepared versus active distinction. |
| Executor | `packages/engine/src/program-runtime.ts` `ProgramRuntime` (346 lines) | `install` validates, refuses a profile change and refuses while `voices.size > 0 || clock < tailUntil`, then `prepare` builds the Sound graph; `trigger` resolves values and builds a Voice graph; `command` validates by binding every slot on the prospective values and every resident, then sets cells; `render` reclaims per frame; `dispose` refunds. | Installation is immediate or refused, never pending. Commands apply at `this.clock`, no stamped frame. Admission constructs on the calling thread. |
| Preparation | `packages/engine/src/program-preparation.ts` `validateProgram`, `programInstanceDemand`, `programStorageDemand`; `program-kernels.ts` `bindProgramKernel`, `createProgramKernel`; `kernel-preparation.ts` `ENGINE_KERNELS` | Structural validation including `programKey` recompute, demand in named units, kernel binding and construction. | `validateProgram` recomputes SHA-256 and binds every slot; fine in a worker, unbudgeted on the rendering thread. |
| Storage | `packages/engine/src/layer-echo.ts` `createEchoLine` line 41 `new Float32Array(capacity)` | The only real DSP storage: one Float32 line per Sound delay or echo slot. | Allocated inside the constructor; no way to hand it a transferred buffer. |
| Scheduler | `packages/engine/src/command-queue.ts` `CommandQueue<Entry>` with `commandOf: (entry) => BusCommand`; `packages/control/src/bus-host.ts` `RealtimeBusHost` (246 lines) | Device frame order, equal frame insertion order, release reserve, lookahead, per window density, bytes, origin establishment, correlation by `CommandId`, `refused` replies, reports every eight blocks, local `cancel`. | Entries must be `BusCommand` (`busCommandFrame` and `kind === "release"` are read through `commandOf`). No `ParameterCommand`, no `ProgramSpec`, no ticket, no generation, no terminal acknowledgement other than refusal. The header comment at lines 41 to 43 already assigns those to the integrated protocol unit. |
| Legacy Voice path | `packages/engine/src/master-bus.ts` `prepare`, `activate`, `cancel`; `stamped-bus.ts`; `voice-pool.ts`; `voice-budget.ts`; `packages/contract/src/bus.ts` `BusCommand` | Prepared then activated Voices, class floors and stealing, fade retention, fixed renderer. | Untouched by the ProgramSpec path; carries the shipping pages. |
| Device and page | `adapters/web/src/game-audio.ts` `GameAudio`, `RealtimeDevice`; `worklet.ts` `AudiofaceProcessor`; `worklet-protocol.ts` `postPortMessage` | Context open and resume, rebuild on rate or latency change by closing the context, `pending` and `aging` forgotten after two reports, refusal correlation. | No generation stamped on messages; the processor handles every port message synchronously on the rendering thread; `postPortMessage` takes no transfer list. |
| Test-only proof | `scripts/test-support/program-worklet.ts`, `program-worklet-page.ts`, `test/foundations/program-worklet-support.mjs`, `scripts/verify-program-worklet.mjs` | Real `ProgramRuntime` samples from real `process` callbacks, independently reviewed clean. | `proofCase` compiles inside the worklet message task; the schedule is predetermined; no host, no messages after `prepare`. |

Boundaries missing, in one line each: no owner of a ticket's lifecycle; no owner of the device generation; no owner of a pending installation's storage between realms; no owner of the audio realm's credits; no frame stamped scheduling for `ParameterCommand`.

## 2. Realm ownership, measured

The probe `serialize-and-allocate.mjs` (Node v25.9.0, indicative timings) established:

| Fixture | `ProgramSpec` JSON | Clone keeps key and validates | Install allocates | Admission allocates | `render(128)` | Command | Dispose |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PAIR` | 5,804 B, 7 slots | yes, yes | 10 buffers, 39,756 B (28,800 B echo line), 1.6 ms | 7 buffers, 52 B, 0.27 ms | 0 | 0 buffers, 0.33 ms | 0 B reserved |
| `PAIR_DELAY` | 5,808 B | yes, yes | 10 buffers, 43,728 B (32,768 B line), 0.5 ms | 7 buffers, 52 B, 0.09 ms | 0 | 0 buffers | 0 B |
| `PAIR_JITTERED` | 5,972 B | yes, yes | 10 buffers, 40,308 B | 7 buffers, 52 B | 0 | refused as expected | 0 B |

What `ProgramSpec` serializes: a plain, structured clone safe object (branded strings, numbers, booleans, arrays, `JsonValue` configuration). `structuredClone` preserves `key` and passes `validateProgram`; the clone arrives unfrozen and `ProgramRuntime.prepare` freezes it. Nothing in it is a function, Map or typed array. It fits the existing `commandBytes` bound of 65,536 with room for one delay line.

Off the rendering thread, in the document realm: `planEdit`, `compile`, `validateProgram` including the key recompute, demand arithmetic, storage allocation for every `state !== null` Sound slot (`Float32Array(capacityFrames)`, transferable), ticket minting, supersession, credit checks and the document realm ledger charge.

On the audio side, necessarily: envelope validation (generation, ticket uniqueness, Sound known, byte counts, slot count), `bindProgramKernel` per slot (unit conversion and joint validation, heap objects, no typed arrays), Sound graph construction over the transferred line, the two small buffers (`Float64Array(1)` mixdown, `Float32Array(128)` per output, or preallocated per Sound at open), activation as a pointer swap at a frame boundary, Voice admission, command application, reclamation and refunds.

Voice admission, honestly: `trigger` resolves modulations with seeded draws at the admission frame and constructs a `ProgramGraph` of six kernels: seven typed buffers (52 bytes) plus Maps, closures and generator objects, about 0.1 to 0.3 ms cold in Node. It cannot be prepared in a worker because the frame, seed and trigger are admission inputs and graph objects do not cross realms. It is bounded by the ledger `voices` unit and must additionally be bounded per callback window by the host (admissions per window). Pooling prebuilt Voice graphs per installed program is a later unit. `command` validation binds every slot for the installed values and every resident, so its work is slots times residents, heap only, bounded by the same units.

## 3. Alternate paths to delete when callers migrate

1. `createInProcessCompositionSurface` and its synchronous `Application`; `test/foundations/program-surface.test.mjs` migrates to the in-process realm pair below. No second owner remains.
2. `ProgramRuntime.install` throwing on residency; replaced by staged installation that activates when reclamation and the requested frame allow, or is cancelled or superseded.
3. The test-only proof processor and page (`scripts/test-support/program-worklet*.ts`, `verify-program-worklet.mjs`) once the host page reproduces the same 22 sample equalities through real messages; `program-worklet-support.mjs` cases, references and comparators are reused, not copied.
4. Not this unit, recorded for the Voice migration: `GameAudio` report aging (`pending`, `aging`) and `audition.voice` starts through `BusCommand`, replaced by tickets when the legacy Voice path moves onto `ProgramSpec`.

No second host, scheduler, planner or adapter is proposed. The ProgramSpec family joins the existing `createBusHost` queue and clock.

## 4. Recommended unit: ticketed cross-realm program installation

Two gated steps in one unit. Step one is Node only and lands the contract, engine and control changes with in-process realms. Step two is the browser proof with a real worker, real ports and a real worklet.

### 4.1 Contract (`packages/contract/src/program-host.ts`, new, about 120 lines; `bus.ts` gains two variants)

```ts
type SoundId = Brand<string, "SoundId">;             // minted by control at open
type ProgramTicket = Brand<string, "ProgramTicket">; // one per submitted effect
type InstallationPacket = {
  ticket: ProgramTicket; generation: number; sound: SoundId;
  baseRevision: number; revision: number; frame: number;    // activate no earlier than frame
  program: ProgramSpec; trigger: ProgramTrigger;
  storage: readonly { placement: PlacementKey; line: ArrayBuffer }[]; // transfer list
};
type ProgramHostMessage =
  | { kind: "install"; packet: InstallationPacket }
  | { kind: "command"; ticket; generation; sound; revision; frame; commands: readonly ParameterCommand[] }
  | { kind: "trigger"; ticket; generation; sound; frame; trigger: ProgramTrigger }
  | { kind: "release"; ticket; generation; sound; voice: number; frame }
  | { kind: "cancel"; ticket: ProgramTicket; generation }
  | { kind: "close"; ticket; generation; sound };
type ProgramOutcome = {
  ticket; generation; sound; frame;                            // the actual frame
  state: "pending" | "applied" | "refused" | "cancelled" | "superseded" | "stale";
  revision: number | null; voice?: number; message?: string;
};
type ProgramCredit = { sound: SoundId; pendingInstallations: number; bytes: number };
// bus.ts: HostMessage | { kind: "program"; message: ProgramHostMessage }
//         WorkletMessage | { kind: "outcome"; outcome: ProgramOutcome }
//                        | { kind: "credits"; generation: number; credits: readonly ProgramCredit[] }
```

Rules: one terminal outcome per ticket; `pending` is the only non terminal state; a newer `install` for the same Sound supersedes the pending ticket by identity; a message whose generation is not the host's current one is answered `stale` and touches nothing; late commands apply at arrival and acknowledge the actual frame; `close` refunds Voices and staged state and acknowledges.

### 4.2 Engine

- `program-runtime.ts`: move the private `prepare` into `program-installation.ts` as `prepareInstallation(program, storage, sampleRate, reserve, clock)` taking provided lines; add `stage(candidate, frame)`, `cancelStaged()`, and activation inside `render` at a frame boundary when `clock >= frame && voices.size === 0 && clock >= tailUntil`, recording `activatedAt`. The constructor takes a prepared candidate. `install` as a throwing method goes.
- `layer-echo.ts`: `createEchoLine(capacityFrames, line = new Float32Array(capacity))`, one parameter, both consumers unchanged.
- `command-queue.ts`: replace `commandOf` with `describe: (entry) => { frame: number; release: boolean }`; `afterQueuedStart` moves to `bus-host.ts` where the Voice start logic lives. Existing queue tests in `test/foundations/runtime.test.mjs`, `scheduling.test.mjs` and `packages/control/test/bus-host.test.mjs` are the gate for zero behaviour change.

### 4.3 Control

- `program-host.ts` (new, audio realm): `ProgramHost` owns `Map<SoundId, { runtime, revision, staged }>`, the audio realm `ResourceLedger`, generation, ticket uniqueness, envelope validation, the per window admission bound, outcomes and credits. Each accepted message becomes an entry in the one `CommandQueue` at its frame; at drain it calls `trigger`, `command`, `stage`, `release` or `close` and emits the outcome with the actual frame. `RealtimeBusHost` composes it: `receive` routes `kind: "program"`, `render` drains the shared queue, the eight block report window also posts credits. `bus-host.ts` stays under 400 lines.
- `program-preparer.ts` (new, document realm): wraps `createCompositionSurface` with the `installed` lookup fed from outcomes; `open(composition, trigger)` compiles, validates, allocates lines, charges the document realm ledger, checks credits, mints the ticket and returns the packet with its transfer list; `apply(request)` turns a `command` effect into a command message and a `prepare` effect into a packet, superseding the Sound's pending ticket; `outcome(outcome)` correlates, advances applied revision on `applied`, refunds the prepared charge exactly once on any terminal state; `snapshot(sound)` reports desired, applied and pending ticket. Realm neutral: it takes a `post(message, transfer)` sink.
- `composition-runtime.ts`: deleted; `createInProcessProgramPair()` in `program-preparer.ts` or test support wires preparer and host through a synchronous port pair for Node.

### 4.4 Adapter and app

- `adapters/web/src/program-worker.ts` (new second export `./worker`, about 60 lines): runs the preparer over `self.onmessage`, posts packets with transfer lists to the worklet port it was handed.
- `worklet-protocol.ts`: `postPortMessage(port, message, transfer = [])`.
- `game-audio.ts`: a generation counter incremented in `RealtimeDevice.apply` on rebuild and exposed to the worker; nothing else moves.
- `apps/web/build.mjs`: bundle the worker as `PROGRAM_WORKER_SOURCE`, emit `dist/program-host.html`; shipping `index.html` and `null-test.html` unchanged by hash.

## 5. Browser proof

Page `scripts/test-support/program-host-page.ts` with the library holding `PAIR` and `PAIR_DELAY` as two retained Sounds, the real worker, a `MessageChannel` whose one port is transferred to the worklet and the other to the worker, and `program-worklet-support.mjs` references reused for sample equality.

Correctness runs in `OfflineAudioContext` with `suspend(frame / sampleRate)` at planned quantum boundaries: at each suspension the page sends the next step to the worker, awaits the outcome on the node port, then `resume()`s. The transport is genuinely asynchronous across three realms while the audio clock is held, so every scenario is deterministic and frame exact.

| Scenario | Invariant |
| --- | --- |
| Open both Sounds, trigger at stamped frames | `applied` outcomes carry the stamped frames; samples equal the Node pair rendered through the in-process pair |
| Live cutoff ramp on A and delay time on B, stamped | Applied at the stamp, zero installations, samples equal `proofReference` style closed forms |
| Frozen `DLY-11` edit on B while its Voice is held | `pending`; after release and `tailUntil`, `applied` at an actual frame not below `tailUntil`; later samples equal a fresh render of the desired document |
| Two prepares for B in a row | First `superseded`, second `pending` then `applied`; exactly one terminal outcome each |
| Cancel before and after activation | `cancelled` with both realms' prepared bytes back to their pre edit values; after activation, `refused` too late |
| Rebuild generation | A packet from the old generation is `stale`, installs nothing, refunds nothing twice |
| Close A with Voices resident | Voices refunded, outcome `applied`, both ledgers at zero for A, B unaffected sample for sample |
| Negative controls | Corrupted key, packet beyond credit, unknown Sound, processor error: each forces a page failure |

Deadline measurement is separate and never a correctness verdict: the same steps in a realtime `AudioContext` with wall clock stamps, ack frame minus stamp recorded, one 500 ms main thread busy loop while commands are in flight, results recorded with environment and marked `inconclusive` when headless output does not advance.

## 6. Gates, failing before, blast radius

Gates, in order: `node --test test/foundations/ packages/control/test packages/engine/test packages/patch/test`; `node --test test/worklet-null.test.mjs`; `pnpm run typecheck`; `node scripts/verify-structure.mjs` (the worker export follows the `./worklet` precedent, no new edges); `pnpm --filter @audioface/app-web build`; `pnpm run check`; `node scripts/verify-program-host.mjs` headless and headed in fresh private sessions with screenshots, sharing session helpers extracted from `verify-program-worklet.mjs` rather than copied; file and function limits; `git status` clean.

Cheap failing before scenarios at ea487fb: a frozen edit with a resident Voice through `createInProcessCompositionSurface` returns `refused` at once, never `pending`; `ProgramRuntime.install` throws under residency; a second `prepare` produces no supersession; `CommandQueue` rejects a non `BusCommand` entry at the type level; installation through `countStorage` allocates a 28,800 byte line, so a test that hands a transferred line and expects zero line allocation fails before.

Blast radius: contract 2 files; engine 4 files; control 4 files with one deleted; adapters/web 3 files; apps/web 1 file; scripts 3 files; tests: one new `test/foundations/program-host.test.mjs`, `program-surface.test.mjs` migrated, three queue test files unchanged as gates. Roughly plus 1,400 lines across two steps; no file above 700.

## 7. Choices the source leaves open

1. Document authority realm. Recommended: the whole `createCompositionSurface` lives in the worker, so one planner and one compiler run off both the main and the rendering thread. Alternative: keep the surface on the main thread and split `planEdit` so the worker compiles; that needs two compile passes or deferred compile failure after acceptance, which breaks the document spec's refusal before commit.
2. Worker to worklet channel. Recommended: a transferred `MessagePort`, so a main thread stall cannot delay installation. Alternative: relay through the main thread. The adapter differs by a few lines; the page proves which one Chrome honours.
3. Audio side validation budget. Recommended: envelope plus `bindProgramKernel`; the SHA-256 key recompute is a worker gate. Alternative: full `validateProgram` on the rendering thread.
4. Pending installation policy. Recommended: activate when reclamation and the requested frame allow, as adjudicated for cold replacement; active transitions stay in section 4 of the probes spec.
5. Home of the audio side program table. Recommended: composed into `RealtimeBusHost`; the alternative, inside `AudiofaceProcessor`, would hand lifecycle to the adapter.

Items 1 to 3 and the contract types in 4.1 need independent design review before implementation; 4 and 5 follow the approved spec and decisions.

## 8. Temporary prototype assumptions and pending owner decisions

Assumptions: Chrome accepts a data URL worker from a one file page opened from disk; a `MessagePort` can be transferred into an `AudioWorkletNode` port; `OfflineAudioContext.suspend` lands on quantum boundaries; Sound identity is a control minted `SoundId` over one composition per Sound; credits are one pending installation per Sound plus a byte budget; no Voice classes or stealing on the ProgramSpec path yet.

Pending owner decisions, unchanged: realtime deadline budgets and device acceptance; shipping sonic policy; whether the document library lives in a worker in the product.

## 9. Later units, split explicitly

Prepared Voice admission by pooling graphs per installed program; migration of the legacy Voice path and deletion of report aging; transfer and transition comparators; emitter and spatial binding; the section 5 deadline campaign.

## 10. Limitations

Node timings are indicative only; no browser ran in this scout; the probe reads `test/foundations` helpers rather than the public control surface; the transferred port and data URL worker assumptions are unverified until step two; the credit shape is a proposal.

Proposed done line for the unit: `build: target=<sha> unit=program-host tickets=... outcomes=... credits=... node=<pass/fail/skip> browser=headless <n> scenarios, headed <n> scenarios, realtime <measured|inconclusive> gates=... deleted=composition-runtime.ts,program-worklet proof tree=clean`.
