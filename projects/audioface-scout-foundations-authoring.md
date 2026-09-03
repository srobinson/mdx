---
title: Audioface foundations scout, authoring and domain
type: projects
tags: [audioface, foundations, scout, authoring, data-model, composition, studio, reuse-map]
summary: Source grounded comparison of the Fable and Astra foundation brainstorms in the authoring domain, with reuse and quality maps, dispositions, probe implications and product questions at baseline 10ba9fc.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundations-fable--brainstorm, audioface-foundations-astra--brainstorm, audioface-phase2-data-runtime-design, audioface-astra-phase2-synthesis, sound-runtime-identity-audioface]
confidence: medium
---

# Audioface foundations scout, authoring and domain

Baseline `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`, tree clean before and after; both brainstorms verified by SHA256.

## 1. Comparison

**Shared decisions, reached independently.** Authored document, immutable program, separately owned running state. Placements pin a definition revision and carry local values. Typed ports declare rate, channel layout and scope; fan in and rate changes are explicit; recursion is rejected. Lifetime comes from declared tails, never silence. The seed tree stays. Parameter edits are scheduled commands; structural edits prepare a new program and activate at a frame. Certification names its signal. Exact samples hold on one backend. Four disagreements remain.

| Topic | Fable | Astra | Recommended resolution | Falsifier |
| --- | --- | --- | --- | --- |
| References | Embed nested compositions by value, carrying origin id and revision | A placement references a definition revision plus overrides; a copy starts a new lineage | Astra. An origin field on a copy has no reader and is a second authority beside the placement reference. Reference by pin; a copy is a new lineage | Probe 3 shows a pin costs more than a copy at compile or load |
| Undo | Edit log with inverses over `ControlEdit` | Restore document revisions; deleted identities never reused; insertion mints fresh identity | Astra. No inverse exists at baseline: `packages/patch/src/patch-editing.ts` `editParameter` returns a previous value, `insertMember` and `removeMember` none. Immutable revisions make undo one operation | Revision snapshots exceed the memory a Studio session tolerates, measured |
| Musical time | A transport brick publishing tempo phase; the rest waits | Absolute integer frames, a versioned tempo map, an explicit rounding rule, free running versus retriggered phase decided now | Astra for the data, Fable for the reader: the tempo map is document data with a rounding rule, a brick reads it. Phase policy is one enum per modulator, decided now | A tempo gesture forces recompilation in probe 2 |
| Spatial boundary | Distance and image become sound scoped bricks; native stays after the master sum | Preserve independent emitter signals until spatialisation; probe native panners | Authoring rule only: a Sound's output port names no destination; routing is the host binding. Probe 1 chooses the backend | A backend needs the composition to name its destination |

**Unsupported claims.** Fable said `packages/control/src/manifest.ts` does half of provenance; `projectRoot` projects registry rows and authored values only, and the overlay is invisible to `projectSnapshot`. Fable's inverse edit log has no baseline support. Astra stated as behaviour that insertion mints fresh identity; at baseline `nextMemberId` reuses the lowest free id, executed in section 3.

**Interface audit.** Continuous edits cannot always avoid recompilation until parameters are classified. At baseline numeric parameters are structural switches: `packages/patch/src/voice-binding.ts` `bindEcho` drops the echo when `DLY-12` is zero, and `packages/engine/src/voice-lifetime.ts` `beginVoice` changes the lifetime kind when `AMP-07` crosses zero. `ParameterDefinition.lifetime` knows only frozen and live; the definition needs a class: continuous, preparatory, derived. Neither author bounds programs during structural edits, and two bounds are needed. One pending program per Sound bounds what is not yet active: a newer edit supersedes the pending one before activation. Draining is separate: after activation the previous program still serves its voices until they end plus tails, so rapid activations leave several draining. Bound draining programs per Sound at a count probe 2 measures; past it the oldest draining program's voices take the steal ramp. Draining voices already count against the pool's capacity and class floors. Memory is one active, one pending, the draining count, plus tails. Nested voice scopes are undefined by both. Recommend one scope per nested composition, its placement's own; only the root Sound has a voice region and a sound region with the mixdown seam between. Legal: a filter rack (filter, LFO on cutoff) in the voice region and a space rack (delay, reverb) in the sound region, fed by the mixdown port. Illegal: the space rack placed in the voice region while its delay declares sound scope, or a link from the voice region envelope output into the space rack; both are compile errors.

**Identity duplication.** Fable's origin field, above. `adapters/web/src/game-audio.ts` `GameAudio.trigger` mints a `VoiceId` from emitter, event, take and serial while `VoiceSeed` already carries pack, event and take. `ControlTarget` keys editing by `PatchId` while audition keys by event, bridged by `Audition.targetOf`; `packages/control/src/surface.ts` `initialState` collapses two events sharing one `PatchId` into one edit target, and `packages/content/src/pack.ts` `validatePack` refuses no duplicate. `PatchId` is audible: `packages/patch/src/patch-resolution.ts` `PatchResolver` seeds jitter under it, so a copy with a fresh id changes every seeded value. Decide which identity feeds the seed; recommend the placement path within the Sound.

## 2. Reuse map

| Capability | Existing symbol | Disposition and reason |
| --- | --- | --- |
| Branded ids with validated segments | `packages/contract/src/ids.ts` `Brand`, `toAddressId` | Reuse for placement, composition and definition ids; deviate from `toParameterKey`, a Phase 0 catalogue grammar |
| Hierarchical address | `packages/contract/src/address.ts` `buildParsedAddress` | Reuse the alternating collection and id tail for nested placement paths; drop the fixed roots |
| Parameter metadata, ranges, curves, defaults, resolution domain | `packages/patch/src/registry/definition.ts` `parameter`, `linearRange`, `derivedDefault`; `registry/domain.ts` `valueInRange`, `clampParameterResolution`; `registry/units.ts`; `registry/integrity.ts` `validatePatchControlRegistry` | Reuse per brick, as issue 4 plans; the integrity check models a catalogue self check |
| Trigger time modulation | `patch-resolution.ts` `PatchResolver.applyConnection`, `resolveAddress`; `patch-validation.ts` `validateConnectionCycles` | Reuse as the compile pass. Refactor first: `resolvePatchLayer` whitelists addresses per source type, so every new brick edits the resolver |
| Seed tree | `packages/contract/src/seed.ts` `rootSeed`, `childSeed`, `drawAt`; `packages/patch/test/seed-independence.test.mjs` | Reuse; labels become placement paths |
| Validation vocabulary and schema | `packages/contract/src/issue.ts` `draftIssue`, `schemaIssues`; `schema/patch.schema.ts` `checkedString` | Reuse for composition validation |
| Transactional editing, optimistic revision, engine refusal before commit | `packages/control/src/edit.ts` `applyControlEdits`; `surface.ts` `apply`, `accept`; `packages/control/test/apply.test.mjs` | Reuse. Refactor first: id minting and cascade deletion, section 3 |
| Generic control projection, adapter neutrality | `packages/contract/src/control.ts` `ControlSchema`; `manifest.ts` `projectRoot`; `schema.ts` `leafSchemas`, `findList`; `parse.ts` `parseControlValue`; `test/adapter-neutrality.test.mjs` | Reuse. The union already models nested lists, objects and unions; add provenance |
| Pack boundary | `packages/content/src/pack.ts` `loadPack`, `validatePack`; `packages/contract/src/pack.ts` `Pack.character`; `catalogue/audioface` `surfaceFor` | Reuse. The composition replaces `Patch`; the overlay authority rule survives |
| One path from event to sound | `packages/control/src/event-voice.ts` `eventVoice`; `audition.ts` `auditionPack`, `nullVerdict`; `certify.ts` `certifyPack` | Reuse. Add composition hash and revision, which `packages/contract/src/certification.ts` lacks |
| Live command protocol with refusal rollback | `packages/contract/src/bus.ts` `BusCommand`, `HostMessage`; `GameAudio.receive` pending and aging maps; `adapters/web/src/bench.ts` snap back | Reuse. No parameter command exists: `BusCommand` is start, release and listener |
| Live listener | `packages/engine/src/stereo-image.ts` `ListenerSchedule` | Reuse, generalised to emitter transforms. `packages/engine/src/stamped-bus.ts` `StampedBus.start` replaces each voice's listener with one global listener, so per emitter placement does not exist at runtime |

**Checked and rejected.** `packages/patch/src/patch-recipe.ts` `buildPatch` as the authoring API: closed unions, positional ids, and `connectionDraftsForLayer` bakes house style jitter connections into every patch, authoring policy inside a builder. Keep it as the migration source for the 28 shipping sounds. `EnvelopeSegment` across eight files: no parameters, no renderer, `insertMember` refuses it. `ControlTarget` by `PatchId`, above.

**None found, searches run** over packages, adapters and catalogue: musical time (tempo, bpm, beat, transport), assets and sample playback, undo or history, macros and presets, a runtime Sound, a duplicate `PatchId` guard across events; only comments matched.

## 3. Quality map

**Duplication.** Validate then throw the first message appears four times: `patch-editing.ts` and `patch-recipe.ts` each define `checkedPatch`, `patch-resolution.ts` `validateResolutionInput` repeats it, and `patch-validation.ts` owns a `PatchValidationError` only `parsePatch` uses. Duplicate id detection appears three times: `patch-validation.ts` `duplicateIds`, `packages/content/src/domain-validation.ts` `collectDuplicates`, `registry/integrity.ts` `duplicateIssues`. Event lookup by id: `audition.ts` `eventNamed` and an unchecked inline find in `surface.ts` `packControlSurface`. `referencePatch` and `skirmishPatch` are one function twice; id minting has two schemes.

**Identity defect, executed.** `fable-scratch/id-reuse-probe.mjs` imports the patch package read only from the baseline: build a two layer patch, remove `layer-01`, insert a tone layer. Observed: 17 orphaned addresses survive, the new layer receives `layer-01` again, its `PCH-01` is the removed layer's 440 rather than the default 660, and four orphaned connections become current. Cause: `removeMember` filters only the layer array, `nextMemberId` reuses the freed id, `initializeSourceParameters` skips present addresses. A value outlives its owner.

**Obsolete or misplaced.** Envelope segment scaffolding in contract, schema, ids, registry owner, validation, editing and manifest, with no behaviour. `packages/contract/src/patch.ts` `firstFilterProcessor` puts authoring policy in the contract, consumed by the recipe, `retypeLayer`, and the resolver. `catalogue/audioface/types/index.d.ts` is a tracked build output while `.gitignore` excludes every other `types` directory.

**Boundary.** `scripts/verify-structure.mjs` `ALLOWED_EDGES` holds: control is the only composer, adapters reach patch only in tests. The script is 605 lines carrying six independent rules; reading found no functional defect, so size alone argues for a split, deferred until the next rule is added. `EmitterId` reaches the engine only inside a `VoiceId` string.

**Hard size violations.** None: largest file 605 lines, longest function 67 lines (`adapters/mcp/src/server.ts` `createMcpServer`), measured by `fable-scratch/fn-lengths.mjs`.

## 4. Disposition table

| Finding | Disposition | Reason |
| --- | --- | --- |
| Ids, address, issue, schema, seed vocabulary | Reuse | Generic and tested |
| Registry definition, domain, units, integrity | Reuse, refactor during | Per brick; add the edit class |
| Resolver curves and cycle refusal | Reuse, refactor first | Remove the per source whitelist in `resolvePatchLayer` |
| Transactional edit surface | Reuse, refactor first | Id cursor, cascade delete, duplicate `PatchId` refusal |
| Control projection and adapters | Reuse, refactor during | Provenance fields and nested collections |
| Pack boundary and catalogue | Reuse | Composition replaces the patch value |
| Event to sound path, audition, certification | Reuse, refactor during | Hash and revision on `Certification` |
| Bus protocol and refusal rollback | Reuse, refactor during | Add a parameter command |
| `ListenerSchedule` | Reuse, deviate | Per emitter transforms replace the global listener |
| `PatchRecipe` builder | Defer | Migration source; retire after the port |
| Envelope segment scaffolding | Refactor first | Delete |
| `firstFilterProcessor` and retype heuristic | Refactor first | Out of contract |
| Duplicated helpers | Refactor first | Mechanical, one owner each |
| Two id minting schemes | Refactor first | One cursor |
| Tracked catalogue types file | Refactor first | One ignore line |
| `scripts/verify-structure.mjs` at 605 lines | Defer with reason | No functional defect found; split when the next rule is added |
| `VoiceId` built from emitter, event and take | Deviate with reason | Opaque ids; the seed is the authority |
| Origin id on embedded compositions | Deviate with reason | Duplicates the placement reference |
| Tempo map, assets, undo, macros absent | Defer with reason | Tempo and undo enter through probes 2 and 3 |

## 5. Probe implications

- **Probe 3, reusable composition.** Smallest scope, Node only: a composition schema with placements, links, modulations and exposures; a compiler flattening one nested rack referenced twice; a hand flattened twin. Gates: sample equality nested versus flat; a deterministic program digest across two compiles, which Astra's delivery digest needs; compile time recorded. Depends on the identity and reference decisions.
- **Probe 2, edits during playback.** Authoring contributes the parameter classification; include `DLY-12` and `AMP-07` as switches. Falsifier: a parameter marked continuous whose edit changes program shape. A tempo edit belongs here, requiring the tempo map as data now.
- **Identity probe.** The section 3 script, red on the baseline and green on the new editing kernel, plus duplicate `PatchId` refusal.
Product decisions blocking these probes: none.

## 6. Product questions

1. **Shared racks, reference or copy?** Assume pinned references with explicit update, copy as a new lineage; both brainstorms default here.
2. **Who compiles for the game?** Assume the game compiles at load and ships a digest of composition plus catalogue versions; probe 3 measures whether precompiled export is needed.
3. **Is cross browser bit equality a promise?** Assume no: exact samples on one backend, fingerprint tolerance elsewhere, as `packages/measure/src/fingerprint.ts` `ACOUSTIC_TOLERANCES` encodes.

All three are explicit reversible assumptions. Blockers: 0.
