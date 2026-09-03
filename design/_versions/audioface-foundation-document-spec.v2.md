---
title: Audioface foundation document and composition spec
type: design
tags: [audioface, foundations, spec, composition, identity, edit-semantics]
summary: Authored composition document, identity, scopes, edit semantics, the shared ProgramSpec contract, the control surface, and the composition probe with exact assertions, at baseline 10ba9fc.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-dispositions, audioface-scout-foundations-authoring, audioface-scout-foundations-runtime, audioface-foundation-runtime-probes-spec, audioface-foundations-fable--brainstorm]
confidence: medium
---

# Foundation document and composition spec

Baseline `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`, clean. Every test below is proposed; none ran. Scope: three falsifiable prototypes sharing one compiler, one runtime and one fixture set.

## 1. Authored types and ownership

A **Definition** is catalogue code declaring ports, parameters, scope capability and the curated kernel implementing it. A **Composition** is a document of placements, links, modulations, exposures and, for kind `sound`, output ports; only `sound` is instantiated; `rack` is reusable and scope neutral. Values live inside their placement, so a value cannot outlive its owner.

```ts
type Port = { name: string; rate: "audio" | "control"; channels: 1 | 2; tail?: true };
type Definition = {
  id: DefinitionId; kernel: KernelId; parameters: readonly ParameterDefinition[];
  inputs: readonly Port[]; outputs: readonly Port[];
  scope: "any" | "voice" | "sound";              // capability, never placement
};
type Placement = { id: PlacementId; region?: "voice" | "sound"; values: ParameterValueMap } & (
  | { kind: "definition"; definition: DefinitionId }
  | { kind: "reference"; composition: CompositionId; revision: number });
type Modulation = { id: ModulationId; source: ControlSource; target: ParameterRef;
  depth: number; curve: ConnectionCurve };   // Link: id, from, to as PortRef
type Composition = { schemaVersion: 1; id: CompositionId; revision: number; minted: number;
  kind: "rack" | "sound"; placements; links; modulations; exposures; outputs: readonly Port[] };
```

A definition declares no state; kernel preparation supplies layout, version and demand (section 6).

Ownership, no new package. `packages/contract` gains the types above, three id brands, and `program.ts` with `ProgramSpec`, `ProgramKey`, `ParameterCommand`, `KernelPreparation` and `ResourceDemand`. `ParameterDefinition`, `ParameterDefault` and `ParameterResolution` move from `packages/patch/src/registry/definition.ts` into `packages/contract/src/parameter.ts`, which already owns their scope, unit, range and curve types, because `ALLOWED_EDGES` in `scripts/verify-structure.mjs` forbids contract importing patch; one change updates that file, `packages/content/src/pack.ts` and `packages/control/src/manifest.ts`. `packages/patch` gains `src/composition/document.ts`, `scope.ts`, `compile.ts` and `plan.ts`, importing contract only. `packages/engine` owns kernel preparation and execution. `packages/control` builds the engine's kernel catalogue, injects it into compile and planner, and keeps the revision surface. `draftIssue` in `packages/contract/src/issue.ts` shapes every refusal. `toAddressId` in `packages/contract/src/ids.ts` permits `.`, so a new `toPlacementId` enforces the grammar below.

## 2. Identity, references, revisions

Four identities, per disposition 2:

| Identity | Purpose and rule |
| --- | --- |
| `CompositionId` | A document lineage; never reused, a copy mints a new one |
| `PlacementId` | A slot within one document; grammar `[A-Za-z0-9_-]+`, minted from `Composition.minted`, a cursor that only grows |
| `PlacementKey` | A slot within a compiled Sound: the placement path joined with `.`, injective because ids reserve `.`; identifies state and is the default seed label |
| `ProgramKey` | SHA-256 of canonical `ProgramSpec` content: kernel ids and versions, normalized configuration, initial values, routing, seed labels and execution profile; excludes composition id, revision, placement keys and the runtime's root and take seeds |

A `SeedMap` from placement key to seed label is optional compile input, preparation data and never authored identity. A continuous edit changes initial values, so a later full compile has a different key; the live command path never compiles (section 4).

`revision` is one monotonic integer per document: the concurrency token, as in `packages/control/src/surface.ts` `apply`, and the pin a reference names. A `Library` holds immutable snapshots keyed by `{composition, revision}`, retained while any pin names them; the probe collects nothing. A reference placement pins one and carries local values for the rack's exposures; editing inside it refuses `pinned_reference`, and `repin` moves the pin after a library edit. Resolution walks references before expansion, refusing `missing_revision` and `reference_cycle`. `copyComposition` yields a new id at revision 0, identical content and cursor, no origin field, an equal key. Undo is excluded; a later restore mints a new revision and never lowers `minted`.

## 3. Typed composition and scopes

Links join ports of equal rate and channel count; anything else is an explicit brick. Links into one port sum in canonical order: source placement key, then port name. Control reaches a parameter only through a modulation, reusing the `PatchResolver.applyConnection` arithmetic in `packages/patch/src/patch-resolution.ts` and the `validateConnectionCycles` walk in `packages/patch/src/patch-validation.ts`, each extracted as a pure export, `applyCurve` and `dependencyCycle`, with both callers and the replaced body deleted.

A `sound` gives every top level placement a region. A `rack` names none; its placements inherit the referencing placement's region, recursively. A sound alone has two reserved ports: `voice.out`, the sink for voice region outputs, and `mixdown`, the source for sound region inputs. `voice.out` sums in placement key order within a voice and in admission order across voices, owned and tested by the runtime under reordered storage.

Rules, each a compile issue naming the placement paths:

- `scope_capability`: a `sound` capability in the voice region or a `voice` capability in the sound region, directly or through a rack.
- `scope_crossing`: a link or modulation crossing regions except through `voice.out` and `mixdown`; `broadcast` and `reduce` stay reserved and excluded.
- `region_missing` or `region_forbidden`: a sound placement without a region, a rack placement with one.

**Fixture.** Rack `tone-voice`: `tone` into `biquad` into `envelope`, exposing `pitch`, default 660, and `cutoff`, declared `live`. Sound `pair`: `a` and `b` reference `tone-voice` at revision 1 in the voice region, pitch 660 and 440, linked to `voice.out`; `space` places `echo` (capability `sound`) in the sound region, fed from `mixdown`, its outputs `dry` and `wet`, the latter `tail`, linked to output port `main`, which names no destination, per disposition 7. Twin `pair-flat` places the seven definitions directly under ids such as `a-tone`, compiled with a `SeedMap` giving each its nested key.

## 4. Parameter edit semantics

Per disposition 4, no registry field is added; metadata is capability and an edit's cost follows from what it changes.

| Dimension | Source of truth | Outcome |
| --- | --- | --- |
| Configuration | `KernelPreparation.normalize(values, profile)` | unchanged gives `command`; changed gives `prepare` |
| Read timing | `lifetime`, unchanged | `frozen` reaches voices started at or after the frame; `live` reaches running instances at the frame |
| Derivation | `resolution.kind`, unchanged | derived gives `refuse` with `read_only` |
| Topology | the edit operation | insert, remove, link, modulate and repin give `prepare` |
| Mutability | placement kind | inside a reference gives `refuse` with `pinned_reference` |
| Capacity | the runtime | accept or refuse a `prepare` |

One injected predicate covers every scouted case. The baseline echo normalizes level 0 to no stage, as `bindEcho` in `packages/patch/src/voice-binding.ts` elides it: `DLY-12` 0 to 0.5 prepares, 0.3 to 0.5 commands. A preallocated `delay` definition normalizes capacity only: level and time within it command, growth prepares. `SRC-37.enabled` is membership in `bindLayer`; `AMP-07` at zero flips `isSustainingEnvelope`, which `beginVoice` in `packages/engine/src/voice-lifetime.ts` reads; both prepare.

A `set` edit carries `ramp: { frames: number; shape: "linear" } | null`; null is a step at the stamped frame. Nothing smooths implicitly; the fixture cases are a step and a labelled 128 frame ramp.

## 5. Minimal control surface and state changes

Two layers, one authority each. `planEdit(document, library, kernels, edits)` in `packages/patch/src/composition/plan.ts` is pure and classifies every edit into an `EditPlan`. `apply` in `packages/control/src/surface.ts` keeps `expectedRevision`, whole batches and refusal before commit; its target becomes a `CompositionId`, closing the `initialState` aliasing collapse. Control commits the accepted revision, stamps the effect with Sound id, ticket id, generation, base revision and absolute frame, submits it, and correlates pending, applied, cancelled and refused outcomes. A newer `prepare` cancels the Sound's pending ticket by identity. Accepted document revision and applied instance revision are tracked separately; a refused application leaves the document accepted and the snapshot reports the divergence, the Studio's preview boundary.

```ts
type EditPlan =
  | { accepted: false; issues: readonly ControlIssue[] }
  | { accepted: true; document: Composition; effect:
      | { kind: "command"; commands: readonly ParameterCommand[] }
      | { kind: "prepare"; program: ProgramSpec;
          transfer: readonly { from: PlacementKey; to: PlacementKey }[] } };
type ParameterCommand = { placement: PlacementKey; key: ParameterKey; value: ParameterValue;
  ramp: { frames: number; shape: "linear" } | null };
```

`transfer` lists surviving placements whose definition and normalized configuration are unchanged. The runtime validates kernel version, state layout version, execution profile and capacity from both programs before committing state or reservations, else refuses or takes the bounded transition comparator. A `command` plan carries no program and triggers no compile.

Pack boundary, per the pack disposition: `Pack.events` maps an event to `{composition, revision}` in a `library`; `Pack.character` is excluded.

## 6. ProgramSpec, the shared contract

`compile(document, library, profile, kernels, seedMap?)` returns issues or an immutable `ProgramSpec`: `key`; `profile` with sample rate, channel shape and execution format; `slots` in topological order, voice before sound, each with `placement` key, `kernel` id and version, `region`, normalized `configuration`, `initial` values, `inputs`, compiled modulations, `state` as `{ layout, version, demand } | null`, and `seedLabel`; `outputs` with tail flags; `demand` summed per region; `latency`. `ResourceDemand` uses named units: owned bytes and alignment, delay frames, render operations, copy operations, tail frames. The runtime multiplies voice demand by admitted voices and counts sound state once. Engine private objects derive from it and define no second program type. `KernelPreparation` is the engine's pure capability per kernel: `version`, `normalize`, `stateLayout` and `demand`.

The five interfaces close: kernel encoding by `kernel` and `version`; smoothing by the explicit ramp, frame stamped by control; transition and refusal in the runtime, reported through the ticket; state units by `ResourceDemand`; emitter binding by control over `{SoundId, outputPort}` from `Composition.outputs`.

## 7. Composition probe

**Environment.** Node only, in the lead's isolated worktree:

```sh
node --test packages/patch/test/
node --test test/foundations/composition.test.mjs
pnpm run typecheck && pnpm run verify:structure
```

**Files.** Beyond section 1: `packages/patch/test/composition-document.test.mjs` and `composition-scope.test.mjs` over a stub catalogue; `test/foundations/fixtures.ts`, shared with the runtime probe: the three documents, the `SeedMap` and definitions bound to `createSourceGenerator`, `filtered`, `stageLevel` and the split echo; `test/foundations/oracle.ts`, a hand wired straight line render of the seven kernels from fixture values with `childSeed` and `drawAt` in `packages/contract/src/seed.ts`, never reading a `ProgramSpec`; `test/foundations/composition.test.mjs`, ungoverned by `ALLOWED_EDGES`. In `packages/engine/src/layer-echo.ts`, `echoStage` separates its line update from its in place sum so `dry` and `wet` ports reuse one arithmetic while the baseline stage keeps summing. Delete nothing now; `patch-editing.ts`, `patch-recipe.ts` and `Patch.parameters` leave with the shipping migration.

**Assertions**, each a named test:

1. Document: remove `b`; its values and every link and modulation naming it go, the result listing the cascaded link id; insert `tone-voice`; id is `p-04`, never `b`, pitch the default 660, never the removed 440. Baseline `insertMember` and `removeMember` fail the same sequence, the red half the scout executed: `nextMemberId` reuses the lowest free id and `Patch.parameters` keeps orphans.
2. Scope: `pair` compiles; `echo` inside `tone-voice` referenced from the voice region refuses `scope_capability` at `a.echo` and `b.echo`; `space` level modulated from `a.envelope` refuses `scope_crossing` at `a.envelope` and `space`; a rack placement with a region, `region_forbidden`; a `voice` definition in the sound region, `scope_capability`; a rack referencing itself through the library, `reference_cycle`; an absent revision, `missing_revision`.
3. Equivalence: `compile(pair).key === compile(pairFlat, seedMap).key`, unchanged under a reversed placement array; seed labels equal the seven nested keys; with one seeded jitter modulation on `a.biquad` cutoff in both, 48,000 frames through the shared runtime under one root seed match each other and the oracle sample for sample.
4. References: editing `tone-voice` to revision 2 leaves `compile(pair).key` unchanged; `repin` to revision 2 changes it; `copyComposition(toneVoice)` has a new id, revision 0, no origin property, an equal key; a `set` inside `a` refuses `pinned_reference`.
5. Plan: cutoff 2000 to 2400 gives `command`, `ramp` null, no program, and a full compile of the accepted document then has a new key; the same edit with a 128 frame ramp carries it; `DLY-12` 0 to 0.5 on the baseline echo gives `prepare`, 0.3 to 0.5 `command`; `DLY-10` beyond a preallocated capacity gives `prepare` whose `transfer` omits `space`; a derived key refuses `read_only`; inserting `biquad` after `a` in a held `pair`, minting `p-04`, gives `prepare` whose `transfer` maps the seven prior placements to themselves and omits `p-04`; a stale `expectedRevision` refuses `revision_mismatch` and changes nothing.

**Falsifiers.** A sample differs among nested, flat and oracle with the jitter present; a continuous edit produces a program; a deleted id returns or a reference to it survives; a library edit changes a pinned Sound; an illegal document compiles. Any blocks the runtime probe.

**Intentional exclusions.** Tempo maps and clocks; assets; undo and restore; `Pack.character`; certification; the feedback brick; `broadcast` and `reduce`; `ControlSchema` projection; nested voice spawning; any performance judgment.

## 8. Deliverable

Deliverable one, contracts and composition proof, in gated steps: contract types, brands and the `ParameterDefinition` move, gated by `verify:structure` and unchanged `packages/patch/test/`; document, identity and scope, tests 1 and 2; compiler, key and `ProgramSpec`, test 3 key half and test 4; planner and surface, test 5; fixtures and oracle, test 3 sample half on the shared runtime, deliverable two's first consumer of `ProgramSpec`, `EditPlan` and `ParameterCommand`.

**Second challenge.** Instances exist only in the runtime, so the dispositions' stale instance assertion splits: revision ordering here, ticket cancellation in the runtime probe.

Unresolved interfaces: 0.
