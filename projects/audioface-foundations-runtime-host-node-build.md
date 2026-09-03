---
title: Audioface foundation program host Node milestone
type: projects
tags: [audioface, foundations, host, runtime, lifecycle, verification]
summary: Committed Node realm ownership, ticketed installation, bounded scheduling and transfer accounting, with browser host migration pending independent review.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundations-runtime-host-design-review, audioface-foundations-worklet-proof-hygiene]
confidence: high
---

# Program host Node milestone

The Node milestone is implemented at `a06c93a2319b34fa00f07de98812ec3d8d67c851` on `probe/foundation-integrated`. Independent review and the worker/browser host milestone remain pending. This report does not declare the full host unit complete.

The sole source worktree is `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated`. The starting tree was clean at `30b15bcf8ff3f42b5afd25c296cc0e8afd633e21`. No other checkout, specification, prior report, remote branch, or PR was changed. No additional agents were invoked.

The active contract is [the program host specification](/Users/alphab/.mdx/design/audioface-foundation-program-host-spec.md), SHA256 `68881c707e78dd6a58a6c3b7926dca81450763d64ef1b8d2f39077358dc94014`. The dispatch version was `44367ec39beba0a7118292a014a7eab3a69e039ea84bd6776b40aa54dc895750`. The lead subsequently recorded [the binding edit-admission decision](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-decisions.md). Every accepted host edit now consumes the existing ordinary admission budget, including edits without an audio effect.

Two local commits form the checkpoint:

- `31df5bb5e2324d4ce1e345e267c308ee75ab07b8`: bounded ticketed program host ownership.
- `a06c93a2319b34fa00f07de98812ec3d8d67c851`: direct transfer backing allocation instrumentation and its regression.

## Reuse and deletion

| Authority | Implementation |
| --- | --- |
| Composition planning | `ProgramPreparer` privately owns one `createCompositionSurface`. Existing `compile` and `planEdit` remain authoritative. Divergence replans with empty edits against the installed program and applied revision. |
| Shared types | `ProgramTrigger` and `ProgramDemand` moved from engine into contract. `ProgramPreparation`, `ProgramPacket`, directional messages, outcomes and limits live in `contract/src/program-host.ts`. Existing CommandId, CompositionId, ProgramKey and VoiceId are reused. |
| Scheduling and clock | `ProgramHost` composes into `createBusHost`. It injects entries into the existing `CommandQueue`. `StampedBus` and `MasterBus` retain the clock and limiter. |
| Demand and resources | Existing `ResourceLedger`, `programStorageDemand` and `programInstanceDemand` are reused. `installationDemand` combines their calculation for both runtime installation and host credit. `installationEnvelopeDemand` adds conservatively charged envelope metadata. |
| Runtime and DSP | Existing `ProgramRuntime`, `ProgramGraph`, kernel binding and `createEchoLine` accept validated supplied backing. No echo arithmetic, classifier or compiler was copied. |
| Admission history | Both realms reuse `ProgramTickets`. The document realm alone owns caller promises and their terminal settlement. |
| Instrumentation | Existing `countStorage` now counts direct ArrayBuffer allocation and distinguishes views over existing backing. |
| Removed path | `packages/control/src/composition-runtime.ts` and its index export were deleted. All seven composition runtime scenarios migrated to cloned realm delivery. No production compatibility wrapper remains. |

The source uses the TypeScript and hygiene guidance to keep directional unions, reuse demand calculations, validate at message boundaries and keep sizing within the requested limits.

## Ownership and lifecycle

[ProgramPreparer](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/program-preparer.ts:55) owns authored state, desired revisions, installed acknowledgements, pending submissions, one coalesced desired revision per Sound, transfers and caller latches. Immutable `document` and `library` queries remain available. The raw mutation surface is private.

Admission precedes `createCompositionSurface.apply`. Validation refusals keep their existing issues and settle their admitted request as refused. Document-only acceptance returns `document-committed` with its revision. It consumes no receiver credit, sends no audio message and does not advance an installed Sound's applied revision. An opening after such an edit compiles the accepted snapshot.

[ProgramHost](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/program-host.ts:59) owns receiver credits, staged packets, candidates, active Sounds, Voice handles and audio outcomes. `pump()` performs paced preparation in an explicit message task after render progress. The Node fixtures control that timing. The process path performs staged activation and rendering, without invoking candidate preparation.

The successful open command identifies Sound lifetime through `openedBy`. Audio and document expectations include generation, installed revision and ProgramKey. Runtime clocks begin at the actual absolute host activation frame. Sound outputs remain separate until stable open-order summation before the existing limiter.

Credit reserves the receiver vector before the compliant sender transfers backing. Verified detachment ends the sender's backing charge. Transit and resident demand remain charged. Application releases pending state while the active program's credit remains resident. Rejection drops receiver state before returning credit. Replacement and graceful close dispose their previous owner before refund. Credit identities survive replacement so later reclamation targets the installation that actually owns storage.

Cancellation has a separate identity and terminal outcome. Unknown targets retain no history. A known ordinary target reserves one cancellation record and only its first cancellation identity is admitted. Duplicate requests reuse prior results. Applied targets remain applied when later cancellation reports too-late. Coalesced revisions that have not been transmitted cancel locally.

Graceful close also handles a future opening before activation. An active close releases Voices and waits for their ends and Sound tails. Its terminal outcome is applied with actual frame and reclaimed confirmation. Generation loss settles unresolved callers as generation-ended/application-unknown once. Receiver resources and sender transfer accounts remain quarantined until explicit disposal confirmation. Late results cannot rewrite those caller outcomes. No timeout performs a refund.

## Validation and bounds

[The envelope boundary](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated/packages/control/src/program-envelope.ts:20) walks bounded plain data before JSON charging or hashing. It limits depth to 24 and visited values to 32,768, rejects cycles, nonfinite values and unsupported backing, and charges three bytes per JSON UTF-16 code unit. The program caps bound subsequent structural work. The existing `ProgramRuntime.install` then performs full `validateProgram`, including key recomputation, kernel version, layout and aggregate demand validation, before binding. A matching key never substitutes for authoritative demand validation.

`programStorageLayout` owns required placement and byte descriptors. `validateProgramStorage` rejects missing, extra, aliased, detached, resizable or mismatched backing. The receiver also compares the packet's derived demand with its exact grant. A forged lowered aggregate demand with a correspondingly forged grant still reaches the existing demand validator and is refused.

The queue retains consumed work during its existing inclusive sliding window. Each parameter command counts as one work unit. A batch has at most 32 commands, at most eight batches fit a window, and the total window allowance is 64 work units. Voice construction is limited to one per window. Candidate preparation has its separate retained allowance of one. Program lifecycle entries have a separate reserve of 36; the legacy release reserve remains intact. Cancellation uses no queue entry.

The checked limits include 128 ordinary entries, 1,048,576 queued bytes, 65,536 bytes per ordinary or lifecycle entry, 60 seconds of lookahead, 256 ordinary tickets and at most 768 reserved result records. History does not recycle within a generation.

## Executable evidence

The final focused command passes 55 tests:

```sh
node --test --test-timeout=10000 test/foundations/program-host.test.mjs test/foundations/program-protocol.test.mjs test/foundations/program-surface.test.mjs test/foundations/program-runtime.test.mjs
```

[The focused log](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-build/focused-final.log) records the result. The realm fixtures use actual `structuredClone` transfer, verify detached sender buffers and independently clone replies. Their timing is explicit Node test control.

Meaningful scenario outcomes include:

- Two Sounds keep independent samples equal to their single-runtime controls. Nonzero host origin and ragged rendering also pass.
- Shrink and regrow within delay capacity apply as live commands. Exact wet samples begin at the expected delay. Frozen Voice and Sound edits wait through old playback, supersede candidates and later match the freshly compiled desired state.
- Oversized growth and resource refusal preserve the installed revision, reservations and every subsequent sample. Stale generation, base revision and ProgramKey cannot alter playback.
- Duplicate transfer does not prepare or activate twice. Cancellation before activation reclaims storage; cancellation after activation reports too-late. Closing a future opening prevents later resurrection.
- Ordinary history and queue saturation still permit graceful cleanup. One thousand unknown cancellations and one thousand alternate cancellation identities leave history bounded.
- Generation teardown before activation and after unobserved activation produces one unknown caller result and retains credit until confirmation.
- Every positive receiver demand unit admits exact fit and refuses one unit short before transfer. Performed installation work stays charged after failed preparation.
- The 257th document-only host edit is refused before commit. The immutable library identity and revision remain unchanged. Earlier document-only tickets settle once without audio storage or receiver credit.

Three regressions were observed failing before their fixes: close of a future opening returned stale Sound lifetime; cancellation of a coalesced unsent revision returned unknown; direct ArrayBuffer allocation reported zero backing bytes. The final tests cover each case. The initial supplied-storage test also failed before the new engine export existed.

[The repeatable boundary probe](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-build/verify-node-bounds.mjs) passes at the final SHA:

```sh
node /Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-build/verify-node-bounds.mjs /Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated a06c93a2319b34fa00f07de98812ec3d8d67c851
```

[Its results](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-build/bounds-final.json) include successful installations with 16 slots, 256 parameters and 128 connections. One greater is refused. The 17-slot fixture also exceeds envelope bytes, and the independent structural check confirms slot refusal. The probe admits 32 resident Voices, four receiver program reservations and 32 commands per batch, then refuses the next unit. Backing accepts 65,536 bytes and refuses 65,537. Since JSON charging is a multiple of three, the largest representable metadata charge is 32,766; the next charge is 32,769. The 98,304-byte combined cap equals the two component caps.

The same probe parses changed files with the installed Oxc parser. The largest changed source file is 550 lines. The largest function is 104 lines. No changed file exceeds 700 lines or function exceeds 150 lines.

## Allocation evidence

[The allocation record](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-build/allocation.json) covers PAIR_DELAY at 48 kHz. Worker backing preparation allocates one 32,768-byte buffer. Receiver runtime construction, including validation and hash scratch, allocates 7,568 numeric bytes across eight buffers and creates two views. The transferred echo line itself is reused. Voice construction allocates 52 numeric bytes across seven buffers. A 128-frame render allocates zero observed backing or views. Disposal leaves zero reserved owned bytes.

These counters exclude ordinary JavaScript objects, structured-clone internals and timing. Ledger work totals are conservative charges recorded at reservation. Actual operation counts and CPU duration are unmeasured. Receiver validation, hashing, binding, graph construction and views still consume rendering-thread work. Voice admission remains a constructor operation. The milestone makes no allocation-free admission, deadline, dropout, garbage-collection timing or realtime performance claim.

## Gates and browser compatibility

At the final SHA, `pnpm run check` exits 0 with 422 tests passed, no failures, no skips, and successful typecheck, lint, format and structure gates. [Final check log](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-build/check-final.log).

The existing verifier performs a real web build and proves clean, unchanged source before and after browser execution. Fresh headless and headed sessions each execute all 22 existing program cases at 48 kHz and 44.1 kHz. They also run the legacy null fixture, with all five shipping events passing. Commands and results are retained under [headless-final](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-build/headless-final/result.json) and [headed-final](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-build/headed-final/result.json).

```sh
node scripts/verify-program-worklet.mjs headless /Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-build/headless-final
node scripts/verify-program-worklet.mjs headed /Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-node-build/headed-final
```

Environment: macOS arm64, Node v24.20.0, agent-browser 0.36.0, Chrome 152.0.0.0. Browser sessions are isolated and closed by the verifier. The previous 22 sample hashes at clean baseline 30b15bc are preserved, while embedded artifact hashes change because shared host/runtime code changed.

| Artifact | Baseline SHA256 | Final SHA256 |
| --- | --- | --- |
| index.html | `8db6ed638ad32095d5b8a3c3979beed48900a4dd840d2b4f07f0ea49f67c2a31` | `c81ed95b95d94557ba9c292b9012d40f3b8ed428823976ac49b71da58162fb60` |
| null-test.html | `b484bf05971c65357c7566dd7fd9cc61d68f2ac4a014d8183a2d88888a1cf38a` | `9b14a5ad00bc242ec5008122a832ddd05435f15a99418b520e506b22821a7a5f` |
| program-test.html | `f75cb67f10edfe99436de17c09cb5c95fe4574bfc91be7622d905fe48538c5cf` | `c6c932e1e30cf8b1107f5400b1649f54be42e021fbb5372a2c42f534afccda0e` |

An early unstaged structure run encountered the deleted file through Git's tracked-file inventory. Staging the intentional deletion resolved that inventory condition. No structure rule or baseline expectation was weakened.

## Pending scope

Independent review of this exact Node checkpoint is required before actual worker entry, transferred-port bootstrap or browser host migration. Existing program proof glue remains intentionally present for that later migration.

The next milestone must move all 22 comparisons through the real host path, prove advancing AudioContext execution during a worker-produced 500 ms main-thread stall, and then delete superseded browser glue. Voice pooling, active transitions, native spatial work, deadline campaigns and product library policy remain outside this checkpoint.

The persistent report exists and is readable. Markdown indexing was attempted but the configured tool returned `Path outside root: /Users/alphab/.mdx/projects`. Index roots were not changed.
