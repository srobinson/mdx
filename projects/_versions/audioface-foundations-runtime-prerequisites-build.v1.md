---
title: Audioface foundation runtime prerequisite build
type: projects
tags: [audioface, foundations, runtime, admission, scheduling, verification]
summary: Committed bounded Voice admission and host scheduling with executable failure, retention, cancellation, and allocation proofs.
status: active
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-runtime-probes-spec, audioface-foundation-document-spec, audioface-scout-foundations-runtime]
confidence: high
---

# Runtime prerequisite build

The independent first runtime unit is committed on `probe/foundation-runtime` at `28bdd079b825ce9eb5b15e5f5438eeabca7cedb1`. Parent: `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`. Worktree: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/runtime`, clean after commit.

The [implementation brief](/Users/alphab/.mdx/TMP/pstack/audioface-foundations/implementation-brief.md) governs this unit. The authoritative document and runtime specification SHA256 values remain `e5bce921c9e55a63ece4e17df4e5ed6237d95f988177a870832ea2168a8c73df` and `6615929b170d3681f0fc994985d9f5186316f87b6d0b7322fbcabe5e12f1555d`.

## Changed owners

- Engine `MasterBus.prepare` reserves capacity and builds an owned Voice snapshot, lifetime, renderer, distance, and image before pool admission. Constructor failure refunds the provisional reservation. `activate` consumes prepared state without constructing DSP buffers. `VoicePool.admit` retains the existing victim policy.
- Engine `VoiceBudget` counts prepared, active, and fading Voices together. It charges layers, filters, echoes, delay frames, and actual owned Float32 bytes until references are removed. Echo tails remain charged through retirement. The bus reports its separate 1,536 scratch bytes. Cleared lifetime scratch arrays cannot retain retired Voice graphs.
- Control `createBusHost` owns the only scheduler, including preorigin entries. `StampedBus` executes prepared commands immediately and meters output. Offline audition now uses `createBusHost`; the obsolete engine scheduler path is deleted. Its eight scheduling regressions moved to `test/foundations/scheduling.test.mjs`.
- The queue bounds entries, conservative payload bytes, lookahead, insertion work, and ordinary commands in every inclusive render window. Equal frame insertion order and release normalization remain intact. Origin establishment rechecks overdue density and future horizon, with correlated refusal and refunds.
- Each resident Voice reserves release capacity that ordinary commands cannot consume. One pending release per Voice prevents duplicate accumulation. Local `BusHost.cancel(commandId)` removes queued work and dependent releases synchronously, without another queue slot. Cancellation after start activation reports `too-late`; an absent or reclaimed command reports `unknown`.
- Existing DSP stages now accept explicit frame counts. Master and Voice rendering use offsets and lengths throughout. The touched pitch and filter envelope guards share one private module. No DSP algorithm or shared compiler contract was copied.

## Probe limits and semantics

Defaults are finite experimental limits, without device or shipping approval. Aggregate Voice limits are 32 residents, 256 layers, 512 filters, 256 echoes, 1,048,576 delay frames, and 4,211,712 Float32 bytes. Tests override capacities explicitly, including exact fit and one unit short.

The default queue permits 128 ordinary entries, a 1,048,576 byte ordinary payload bound, 65,536 bytes per command, 60 seconds of lookahead, and 64 ordinary commands per 128 frame window. Its separate 32 release entries reserve up to another 2,097,152 payload bytes. Byte charges use three times serialized UTF16 code units, a conservative UTF8 bound. Release normalization precedes this measurement.

Overload now refuses additional starts. A 100 start burst retains 24 active and eight fading Voices, then reclaims the fades. Existing class floors, victim ordering, and the two millisecond steal ramp remain. The original burst retained 76 fades, so overloaded output intentionally changes. Duplicate Voice and invalid DSP refusals now occur during receipt preparation.

## Executable evidence

Environment: Node `v24.20.0`, pnpm `10.17.1`. No browser timing run occurred.

| Command or check | Result |
| --- | --- |
| Initial `node --test test/foundations/runtime.test.mjs` before production edits | Exit 1, three intended failures: poisoned next render, 100 retained renderers, six subarray views. |
| Added release normalization regression before its correction | Exit 1, charged 294 bytes against the required 306 byte conservative bound. |
| `node --test test/foundations/runtime.test.mjs test/foundations/scheduling.test.mjs test/worklet-null.test.mjs` | Exit 0, 27 tests pass, including 16 new runtime regressions. |
| `pnpm run check` on final executable content | Exit 0, typecheck, all 286 tests, lint, formatting, and structure pass. |
| `pnpm --filter @audioface/app-web build` on final executable content | Exit 0, real index and null test bundles emitted. No dependency policy change. |
| `git diff --cached --check`, final status, parent and specification hashes | Pass. Clean tree, exact baseline parent, unchanged authoritative pair. |
| OXC AST inspection of the 22 changed source and test files | No parse errors. Largest file 438 lines; largest function 45 lines. |

Tests verify that failed admission preserves existing membership and exact subsequent samples, every Voice budget refunds, queue cancellation refunds bytes, releases survive saturation, and prepared delay storage remains charged through the last tail frame. Instrumented active rendering includes delayed noise layers, filters, echoes, midblock starts, steals, ragged blocks, and reports. It creates zero Float32 buffers and zero subarray views during the measured renders.

The first full check stopped on two lint findings after its tests passed. Both were corrected. Structure verification first required staging the moved test, then correctly rejected a cross package fixture import. Moving that integration test to the root foundation test directory resolved the boundary violation. The final complete gate passed after these corrections.

## Pending integration and limitations

Fable's reviewed contracts must precede `ProgramSpec` consumption, `EditPlan` and `ParameterCommand` application, retained Sound ownership, the generalized control owned `ResourceLedger`, and the independent compiled sample oracle. `VoiceBudget` covers the current fixed Voice renderer only. No compiler interface or shared parameter definition changed in this unit.

Wire cancellation, terminal applied acknowledgements with actual frames, ticket and generation checks, rebuild cleanup, worker preparation, and bounded cross realm transport remain for integration. Preparation currently runs in host receipt, which can be on the audio thread. Payload accounting does not establish a bound on hostile packet decoding or serialization before admission.

The zero allocation evidence covers Float32 construction and subarray views. Existing JS lifecycle objects, map iteration, origin rebasing, and report objects still allocate. Reclamation means removal of owned references, without a physical garbage collection or process memory claim. Host spans above 128 frames are rejected before state changes; browser handling of unsupported quanta remains unverified.

Program transitions, compatible transfer, wet tail comparators, held edits, independent emitter routing, native equivalence, browser captures, and realtime deadline measurements remain unimplemented. Node host null tests and successful bundling provide no browser performance verdict. Owner sonic policy and device acceptance inputs remain pending.

Only the runtime worktree and the two assigned external handoff files were written. The commit changes no contract, patch, lockfile, or dependency policy files. No other agents, peer messages, pushes, PRs, merges, or publication occurred.
