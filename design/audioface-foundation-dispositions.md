---
title: Audioface foundation probe dispositions
type: design
tags: [audioface, foundations, architecture, dispositions]
summary: Lead decisions from the independent foundation scouts, scoped to executable architecture probes.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-scout-foundations-authoring, audioface-scout-foundations-runtime]
---

# Foundation probe dispositions

These are lead engineering decisions for prototypes following Stuart's authorization to reopen the foundations. They do not constitute acceptance of shipping behavior, a production rewrite, or approval of a performance target. Baseline: 10ba9fc16cea55271c6d428c8fe64c8df0b9c354; repository clean at handoff.

Evidence: authoring scout SHA256 fdba34273a81a47c7d85719daaee9d3bd4ff7046966a6599c703a38cea0f564e; runtime scout SHA256 c3fb2c03a13177379d7099a5d43c6b396bedd08c6778b7e772be1d74add7f959. Both independently compared the two brainstorms and checked source. The lead verified hashes and read their commissioned bounded digests. Runtime performance claims remain unmeasured in a real browser.

## Direction selected for testing

1. Authored document, immutable compiled program, and mutable running instance have distinct responsibilities. Compiled JS schedules are the first executable candidate, with no presumption that they outperform native graphs or WASM.
2. Shared composition references pin a revision; independent copies start a fresh lineage. Origin metadata has no authority over content identity. Identity, seed identity, revision and content digest must have defined independent purposes, never duplicate authorities.
3. Composition scope is inherited within a voice or Sound region; the root defines the voice-to-Sound mix boundary. Arbitrary nested voice spawning is excluded from the first probe. Cross-scope control requires an explicit typed broadcast or reduction operation; incidental graph wiring cannot invent that operation. A voice-local rack and a Sound-local effect rack are legal; a hidden Sound-lifetime stateful effect inside each voice is rejected. The spec must distinguish reusable definition capability from placement scope.
4. An edit may require a command, preparation, or rejection depending on topology, capacity, mutability, and parameter semantics. Avoid duplicating frozen/live lifetime with a second field that means the same thing. Derived values are read-only. Specify the orthogonal dimensions and test a zero-to-positive delay edit.
5. Structural edits to sustained playback must demonstrate audible adoption. Draining only new voices is insufficient for an indefinitely held note. Compare bounded program crossfade with explicit compatible-state transfer where supported; no promise of generic state migration.
6. Resource limits count active, prepared, fading, draining and transitioning work. One pending program per Sound may coalesce replacement edits, but separate bounds cover old programs and their voices/buffers. If overlap does not fit, expose pending/refused state; do not silently steal old tails as the prototype default. Atomic admission and reservation refunds are prerequisites.
7. Preserve independent emitter outputs until spatial placement/routing is chosen. A final stereo sum cannot supply independent downstream panners.
8. UI telemetry is bounded and expendable; audio execution never waits for the visual interface. Worklet message handlers and installation run within the audio realm and require their own budget; outside process() is not automatically off the audio thread.
9. Tempo maps are explicit data when needed; processors read the appropriate clock. Probe only timing behavior required by the selected cases. Do not build a general music system, asset catalogue, undo framework, or modulation library speculatively.
10. Exact equality applies to unchanged signal histories within the tested execution environment. Backend/platform comparisons need stated tolerances and evidence. Existing golden samples are useful evidence, not an unexamined constraint on intentional architectural or sonic changes.

## Reuse and quality dispositions

| Scout capability or finding | Lead disposition | Reason and timing |
| --- | --- | --- |
| DSP kernels, lifetime tests, seed primitives, contract ids/addresses/issues | Reuse | Retain proven algorithms and vocabulary, verify semantic fit; do not preserve accidental identity encodings. |
| Structural boundary verifier and host/null fixtures | Reuse | Extend existing gates where applicable; Node host tests do not prove browser deadlines. |
| Parameter definitions, domains, units and integrity | Refactor during consuming probe | Reuse definitions; add only orthogonal preparation/capability meaning justified by executable cases. |
| Resolver curves, cycle refusal and transactional edit surface | Refactor first at the touched seam | Preserve useful resolution/edit logic; establish deletion and identity invariants before relying on reusable documents. |
| Deleted member identities, stale values/connections, PatchId aliasing | Refactor first at the touched seam | Require failing-before and passing-after fixtures; ownership determines edits, not accidental id equality. |
| Control projection, event binding, audition and certification path | Refactor during consuming probe | Preserve adapter separation and useful measurement code; correct contextual control meaning and certificate scope. |
| Pack validation/delivery boundary | Reuse boundary, revise ownership where needed | Event selection need not own the reusable definition. |
| MasterBus admission before factory success | Refactor first | No prototype performance verdict may rely on a host whose failed admission poisons later rendering. |
| Unbounded fades, command queue and render-path subarray views | Refactor first for runtime probe | Establish complete capacity accounting and inspect all deadline-sensitive paths. |
| Bus protocol, correlations and device lifecycle | Refactor during runtime probe | Reuse transport shape with explicit acknowledgements, cancellation and generation checks. |
| Global listener and master-only native output | Deviate | Independent emitter placement needs an earlier routing boundary; reuse schedule concepts where appropriate. |
| Waveform and envelopePeak duplication, duplicate id minting | Refactor during first touched consumer | Use one owner; do not run an unrelated cleanup sweep ahead of the probes. |
| EnvelopeSegment scaffolding and contract firstFilterProcessor heuristic | Deviate at replacement boundary | Exclude unconsumed scaffolding and fixed-shape policy from the new core; remove obsolete paths when callers migrate. |
| Tracked catalogue type declaration | Defer pending consumer/provenance proof | Remove or regenerate when its owning boundary changes; its existence alone is insufficient reason for pre-probe cleanup. |
| PatchRecipe | Defer | Treat as a donor/fixture builder; no compatibility framework. |
| verify-structure.mjs size | Defer | No hard size violation or specific defect found; no mandatory split solely because it has 605 lines. |
| VoiceId encoding emitter/event/take; origin metadata on copies | Deviate | Opaque lifecycle identity and explicit seed inputs have separate roles; eliminate duplicated authority. |
| Full assets, undo, macros and music feature systems | Defer implementation | Reserve clear boundaries; implement only what makes the three probes falsifiable. |

Refactor first means before the relevant probe depends on the defective path, not permission for an unrelated production cleanup. Prototype implementation must use isolated worktrees/directories and retain a forward removal map. Repository migration awaits a reviewed foundation recommendation.

## Verification probes

- Game: failed admission leaves the next render valid; burst starts stay within total rendering/storage capacity; two moving emitter outputs remain independent.
- Studio: sustained note receives a control edit and a structural edit; record transition discontinuity, latency, render cost, memory peak, pending/refused behavior and refunds under resource pressure.
- Composition: a nested rack referenced twice and an explicitly flattened equivalent have matching output under the same compiled semantics, stable replay inputs and intentional identity mapping; delete/insert cannot resurrect values or connections; cancellation and rebuild do not retain stale instances.

Measure compilation, installation and rendering separately. Compare alternatives with matched semantics and work, not one language label versus another. Browser profiling is mandatory before performance acceptance. Every claimed result records environment, commands and limitations.

## Open product decisions

Device/browser/workload baseline is pending Stuart's answer; it blocks shipping performance acceptance but not local behavioral probes. Retained lifetime, shared edit propagation and cross-browser reproducibility are not silently approved through engineering defaults. Probes use explicit retained instances, pinned references, and environment-scoped equality as reversible test assumptions. Capture remaining decisions for the owner after the probes make the tradeoffs concrete.
