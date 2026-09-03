---
title: Audioface foundation runtime prerequisite build
type: projects
tags: [audioface, foundations, runtime, admission, scheduling, verification]
summary: Four accepted runtime findings corrected with bounded fade retention, atomic earliest release replacement, observable report windows, and one pool admission path.
status: active
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-runtime-probes-spec, audioface-foundation-document-spec, audioface-scout-foundations-runtime]
confidence: high
---

# Runtime prerequisite build

The focused correction is committed on `probe/foundation-runtime` at `9204eaa9b5be02dffa6b6649110b505c5903b4ff`, parent `28bdd079b825ce9eb5b15e5f5438eeabca7cedb1`. Baseline remains `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`. The runtime worktree is clean at handoff.

All four accepted findings in the [Fable review](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/fable-code-review.md) are resolved within the [correction brief](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-fix-brief.md). Independent verification is pending. The review's SHA256 was verified as `c3011a4c46126ac2a3edfd618689d8cefb564ea6f693b0714058e86bbb39428b`.

The substantive [previous report](/Users/alphab/.mdx/projects/_versions/audioface-foundations-runtime-prerequisites-build.v1.md) is preserved byte for byte, SHA256 `3cd84f89b25664d7cdc23262b623a35cea8faa9beaef1d2d704b5e92298c4c5d`. It records the first unit and its historical evidence.

## Corrections and ownership

### Earliest queued release

`RealtimeBusHost.enqueue` compares release frames after queued start normalization and effective device time clamping. The earliest valid release remains queued. An equal or later request receives a refusal correlated to its own command ID. A valid earlier replacement produces a refusal correlated to the displaced command ID, naming the replacement.

`CommandQueue.receive` accepts the replaced entry as part of the same operation. It validates before removing that entry and reuses its release credit. Invalid frames, oversized commands, and failed admission preserve the existing entry and accounting. Queue removal remains the single credit refund path. Host discard clears the release index, and successful application clears the pending index.

Tests cover both arrival orders, equality, normalized equality before a future start, full ordinary and release capacities, invalid replacement, byte accounting, cancellation, dependent cancellation, and complete resource reclamation. A release requested for frame 256 after one for frame 2000 now retires the held test Voice before frame 1152.

A release for an unretained Voice retains the existing no-op behavior. Terminal acknowledgements and durable command history remain integration work. A superseded or cancelled command has no retained history, so local cancellation returns `unknown`.

### Pool slots and bounded fades

`VoicePool` remains the authority for its 32 active slots, class floors, and victim ordering. `VoiceLimits` extends the existing resource demand with an explicit fade limit. Default total residency is 64, with at most 32 fades. Prepared, active, and fading Voices all remain charged against total residency, graph units, and Float32 bytes.

Pool admission chooses its victim, then asks `MasterBus` to retain the fade before changing pool membership. Fade exhaustion refuses before removing either active signal path. Direct `MasterBus.start` refunds failed activation. The existing host refusal path cancels failed prepared starts and correlates each failure.

The 32 interface start reproduction now admits a bed, retaining 25 active Voices and eight charged fades. A 100 immediate start burst retains 24 active and 32 fading Voices, refuses 44 starts, and leaves no prepared residue. Its 28,672 Voice buffer bytes remain charged until fade retirement. A 100 queued start burst prepares 64, refuses 36 at receipt and eight at activation, then reclaims the same bounded result.

A one-fade test confirms that an exhausted fade limit refuses another steal without changing membership, residency, or subsequent samples. An unused bed slot still admits. Rendering the fade restores capacity. Existing exact-fit and one-unit-short graph budget tests remain passing.

### One reporting window

`StampedBus.report` now observes the current peak accumulator without resetting it. `RealtimeBusHost` begins a new window before the first nonempty render after each cadence emission. Each window covers eight nonempty host render calls, including ragged spans. The completed window remains visible until the next nonempty render; empty renders and explicit reads leave it intact.

Cadence and explicit observation use the same report implementation and accumulator. Reports contain current Voice membership and peaks for that window. They do not define an independent window per reader.

The scheduling test again renders 1000 frames and checks exact output peaks. Another regression observes before and after each cadence boundary, checks repeated reads, and confirms the next render opens a fresh window. Offline audition continues through the same host, and the worklet versus audition sample comparisons pass.

### One pool admission operation

`VoicePool.start` and its unused `beginVoice` import are deleted. All 17 pool test call sites now use `admit(beginVoice(...))`. Source inspection confirms `MasterBus.activate` is the sole production caller of pool admission. A regression rejects reintroduction of the legacy start method.

## Finite default limits

These are experimental limits without device or shipping approval.

| Resource | Limit |
| --- | --- |
| Active pool slots | 32 |
| Retained fades | 32 |
| Total prepared, active, and fading Voices | 64 |
| Layers, filters, echoes | 256, 512, 256 |
| Delay frames | 1,048,576 |
| Charged Voice Float32 bytes | 4,228,096 |
| Separate fixed bus scratch | 1,536 bytes |
| Ordinary queued commands | 128 entries and 1,048,576 bytes |
| Reserved releases | 64 entries, at most 4,194,304 bytes |
| Per-command conservative payload bound | 65,536 bytes |
| Scheduling horizon | 60 seconds |
| Ordinary commands per inclusive 128-frame window | 64 |

Configured limits can refuse admission earlier. The aggregate reservation includes preparation, and bytes remain charged for every retained fade. No fade or queue path is unbounded.

## Executable evidence

Environment: Node `v24.20.0`, pnpm `10.17.1`. The correction changes nine source and test files.

| Check | Actual result |
| --- | --- |
| Focused tests before production edits | Exit 1, 38 tests, 28 pass and 10 intended failures covering the four findings and changed overload policy. |
| Focused final tests | Exit 0, 55 pass. Runtime, scheduling, pool, master bus, host, and worklet tests included. |
| Full `pnpm run check` at final executable content | Exit 0, 292 tests pass, typecheck, lint, formatting, and structure pass. Run once in this correction round. |
| Reused reviewer reproductions | Baseline admits the bed and retires the earlier release. Original target reproduced both failures before edits. Corrected SHA matches those baseline outcomes. |
| OXC inspection | Nine changed files parse. Largest file is 560 lines; largest function is 53 lines. |
| Final source and Git checks | Clean correction worktree, exact reviewed parent, no contract, patch, lockfile, or package manifest changes. |

Named logs:

- [Failing before](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-fix-before.log)
- [Passing after](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-fix-after.log)
- [Full repository gate](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-fix-check.log)
- [Baseline and corrected reviewer reproductions](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-fix-review-repro.log)

The first post-edit run exposed one existing test's old validation-message expectation. Reusing `assertFrame` consistently and updating that expectation resolved it. No failing behavioral assertion was weakened.

The existing allocation regression still observes zero Float32 buffer construction and zero subarray views during ragged active rendering, including fades and reports. Other JavaScript allocations remain. Reclamation means removal of owned references, without a physical garbage collection or process memory claim.

## Scope and remaining integration

The authoritative document and runtime specification hashes remain `e5bce921c9e55a63ece4e17df4e5ed6237d95f988177a870832ea2168a8c73df` and `6615929b170d3681f0fc994985d9f5186316f87b6d0b7322fbcabe5e12f1555d`.

Shared program contracts, retained Sound ownership, the generalized resource ledger, generation checks, applied acknowledgements, workers, cross-realm transport, sample oracle integration, and browser acceptance remain outside this correction. Preparation still runs in host receipt. Payload accounting provides no hostile decoding bound.

No browser or web build was run in this correction round. Web adapter calls and the wire report shape are unchanged; repository typechecking and the worklet versus audition execution tests cover the changed consumers. No browser deadline or performance claim is made.

The Markdown index refresh rejected the projects directory as outside its configured root. The report, prior version, and digest were verified directly on disk.

Main and composition were not edited. No extra agents, memory writes, dependency changes, pushes, GitHub actions, PRs, merges, or publication occurred.
