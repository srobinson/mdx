---
title: Audioface Astra Phase 2 design synthesis
type: projects
tags: [audioface, phase2, design-review, synthesis]
summary: Candidate comparison, selected ownership model, rejected alternatives, verification limits, and proposed issue amendments for Phase 2.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
source: https://github.com/littleorgans/audioface/issues/4
related: [audioface-astra-initial-review, audioface-phase2-data-runtime-design, sound-runtime-identity-audioface]
---

# Audioface Phase 2 design synthesis

The user asked Astra to lead the ongoing design of issue 4. This pass produces a concrete working proposal, not permission to implement or a record of owner approval. The codebase remains at `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`.

## Evidence and method

The initial source review traced pack binding, patch resolution, Voice binding, host commands, pool admission, rendering, controls, and certification. It reproduced identity collisions, deleted-identity resurrection, ineffective control edits, and a failed admission that poisons the next render.

All twelve GitHub issues and their comments were read. The seven documents supplied by the user were then read in full. Current issue bodies take precedence over old candidate proposals. Source control, the issue graph, source tests, and the supplied design record provide the grounding. No deployment telemetry, product analytics, or external team chat service was available or required to establish these local pre-release design constraints.

Two independent candidates were commissioned with isolated outputs and the same acceptance cases:

- Candidate A, Claude: a pack-owned shared patch library with explicit references and retained handles.
- Candidate B, Codex: event-owned authored aggregates, immutable prepared definitions, and retained handles.

Candidate files and proofs are in `/Users/alphab/.mdx/TMP/pstack/audioface-astra-phase2/`. Both complete design packages and sketches were read before selecting a base. A fresh Grok reviewer was commissioned to compare both against the same rubric and check the lead proposal.

## Lead selection

Use Candidate B as the base. It fits current event-owned content and exposes a smaller authoring model. A shared library is a real product feature, not a necessary repair for accidental PatchId collisions.

| Criterion | Candidate A | Candidate B |
| --- | --- | --- |
| Accepted boundaries and bit preservation | Needs revision: adds a legacy loader and an extra source seed child. Root-seed proof does not prove source samples. | Stronger source-label preservation; proposed separate SoundSeedKey departs from the accepted Sound identity seed branch. |
| Ownership and deletion | Coherent explicit sharing, but introduces a library and shared-edit fan out. | Coherent event ownership with smaller scope; simplify redundant binding ids and retain the existing Patch name. |
| Preparation and admission | Fails to separate control-side preparation from realm-local DSP construction; admits factory work during render. | Separates cloneable data from private instances and prepares on receipt; commit eligibility must still be checked before mutation. |
| Control meaning | Reports authored and effective values, but lacks explicit evaluation context and coherent revision pinning. | Pins structure and separates runtime controls; make contextual effective values and Phase 3 setter limits explicit. |
| Public interface and extension | Retains trigger/play aliases and proposes valid handles whose state resets on rebuild. | Explicit handles and rebuild invalidation are clearer. Reuse the existing plugin/catalog boundary. |
| Phase 2 fit | Adds compatibility and shared content beyond current needs. | Better bounded base; remove premature live timing and resource-resolution claims. |

## Grafts and corrections

- Keep A's small caller example and explicit distinction between retained handles and automatic effects, which both candidates support.
- Keep B's event-owned authoring, pinned revision, generation invalidation, receive-time preparation, contextual ownership, and direct preservation of the original source seed label.
- Keep the global Voice accumulation order in the structural slice. A direct Float32 proof demonstrates why empty Sound chains alone are insufficient.
- Retain the accepted SoundInstanceId seed branch. Record ids in create commands and replay those ids. Do not add a second public SoundSeedKey.
- Acknowledge identical explicit take values as deterministic replay. Mutable instances stay independent even when sample streams are deliberately equal.
- Keep `Patch` as the authored type. Do not add a parallel AuthoredSound or a stored binding id redundant with the pack/event key.
- Make preparation data cloneable and constructed DSP instances private to the audio realm. Pre-commit checks remain fallible; the subsequent mutation is atomic.
- Keep runtime latency and tail on initialized plugin instances. Prepared plans may declare requirements and bounds, not pretend to know all effective runtime values.
- Define contextual effective values. A number affected by a trigger cannot be described as globally effective without naming that trigger or instance/frame.
- Use a clean authored schema cutover. No legacy loader or permanent trigger/play compatibility alias is required.

## Rejected alternatives

The shared patch library loses because no current requirement calls for shared edit propagation. It remains the correct alternative if the owner requests that product behavior.

Implicit emitter/event identity loses because it cannot represent independent Sounds on the same emitter and event. Event-only Voice identity was already rejected in issue 11.

Keeping a handle valid after rebuilding the device while resetting its state loses because it weakens the retained-state guarantee. Phase 2 invalidates handles explicitly; future restoration requires honest capabilities.

An extra plugin child below the old source seed loses because it changes source samples. A proof that the unchanged rootSeed function returns the same value twice does not establish the migrated source path.

Construction inside a scheduled render step loses because factory allocation and failure enter the audio quantum. Preparation occurs before scheduled activation, and cancellation releases the prepared resources.

An empty-chain grouped mixer loses because Float32 addition is not associative. The later Sound mixer is a deliberate behavior change and needs its own tests.

Parameters as serialized DSP state lose because phase, filter memory, and delay contents are not parameters.

## Independent review

The independent Grok reviewer selected B. The reviewer found no blocking internal contradiction in the lead draft's cloneable-data boundary, original source seed preservation, rebuild invalidation, or six-slice fit. The reviewer verified the sketches, accumulation example, and relevant baseline source.

Accepted review corrections: reuse the existing `ParameterDefinition.lifetime` field; add concrete `PluginModule.prepare` and `create` signatures; require explicit finite host budgets before exposing retained handles; and retain intentional same-take replay wording.

Two review recommendations were rejected with evidence. First, PatchId does contribute to the connection-jitter seed in `packages/patch/src/patch-resolution.ts` `PatchResolver.constructor`, even though it is absent from the Voice root. The draft now names that narrower role. Second, keeping a permanent separate empty-chain mixer would complicate the runtime to preserve equality outside the designated behavior-preserving slices. The lead instead makes Sound grouping part of the deliberate delay behavior slice and requires its own proof.

Issue 15 blocks the Sound structure slice. It does not block writing the generic contract or the permanent extension fixture. The retained-handle owner choice remains unapproved.

The focused final correction check is clean, including the create acknowledgement, queued starts during preparation, resource refunds, and owned-buffer budget accounting. The independent reviewer checked these exact SHA-256 hashes:

- Design: `7ac42b3097a4ee4baac55811b4dc36db4bda9932d564404fa69190373b1acb0d`.
- Contract sketch: `9541ba2faf48b8c0b58905980082b25893a32d70b1241bc5711710df58bb57de`.

The review record is `/Users/alphab/.mdx/TMP/pstack/audioface-astra-phase2/final-check.md`. Strict TypeScript checking passed. This is a design review result; retained Sound lifetime remains an owner decision, and concrete shipping resource limits require measurements. All review agents created for this design pass have been closed.

## Proposed issue amendments

These are draft changes for the existing issue graph, not new accepted decisions:

- **Issue 4:** link the lead design, make source seed-label preservation explicit, require transactional admission and preparation outside render, distinguish serializable plans from runtime instances, and state the structural accumulation rule. Add concrete ownership/deletion/control acceptance cases to their consuming slices.
- **Issue 15:** after the owner chooses the retained-handle policy, record creation, disposal, idle history, device invalidation, replay identity, and cancellation semantics. Keep this issue open until that decision is explicit.
- **Issue 5:** make live parameter application and latency/tail rescheduling explicit before continuous modulation is enabled. Preserve the Phase 2 definition/instance distinction.
- **Issue 6:** resolve independent native routing versus the existing master-sum boundary before implementing per-Sound native spatial processing.
- **Issue 8:** consume contextual control provenance and read-only derived values. Decide preview re-instantiation behavior before promising live structural authoring.

The existing failed-admission defect is distinct from the closed issue 12 exception-correlation defect. It needs regression proof before the plugin refit relies on safe refusal.

## Verification and limits

- Baseline source review: type checking, 270 Node tests, lint, structure verification, and web build passed.
- Both candidates supplied strict TypeScript sketches; Candidate A's seed proof was inspected and its limits are recorded above.
- The lead sketch imports the actual baseline contract types and passes TypeScript 7 strict checking. Expected errors verify separate Sound/Voice identities, cloneable plan/runtime instance separation, and rejection of derived controls by the authored setter.
- The executable accumulation proof uses ordinary Float32 samples and proves the structural grouping hazard.
- Proposed runtime behavior is not implemented. The type sketch is partial. No claim of allocation-free host execution, safe cancellation, exact restoration, or plugin extension completeness follows from compilation.
- Repository files and GitHub issues remain unchanged during this design pass.

The lead design is `/Users/alphab/.mdx/design/audioface-phase2-data-runtime-design.md`. The partial contract sketch is `/Users/alphab/.mdx/design/audioface-phase2-contract-sketch.ts`.
