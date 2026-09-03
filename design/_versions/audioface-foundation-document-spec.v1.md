---
title: Audioface foundation document and composition spec
type: design
tags: [audioface, foundations, spec, composition, data-model, identity, scopes, edit-semantics, probe]
summary: Implementation ready specification of the authored composition document, identity and references, typed scopes, edit semantics, the minimal control surface, and the composition probe with exact assertions, at baseline 10ba9fc.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-dispositions, audioface-scout-foundations-authoring, audioface-scout-foundations-runtime, audioface-foundation-runtime-probes-spec, audioface-foundations-fable--brainstorm]
confidence: medium
---

# Foundation document and composition spec

Baseline `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`, clean. Every test below is proposed; none ran this phase. The only executed evidence is the scout's identity probe at baseline (`fable-scratch/id-reuse-probe.mjs`). Scope: three falsifiable prototypes, not a framework.

## 1. Authored types and ownership

A **Definition** is catalogue code declaring ports, parameters, scope capability and state. A **Composition** is a document of placements, links, modulations and exposures; kind `sound` is the only root the runtime instantiates, kind `rack` is reusable and scope neutral. Values live inside their placement, so a value cannot outlive its owner.

```ts
type Port = { name: string; rate: "audio" | "control"; channels: 1 | 2 };
type Definition = {
  id: DefinitionId; parameters: readonly ParameterDefinition[];
  inputs: readonly Port[]; outputs: readonly Port[];
  scope: "any" | "voice" | "sound";              // capability, never placement
  state: { bytesPerInstance: number } | null;   // declared; the runtime accounts
};
type Placement = { id: PlacementId; region?: "voice" | "sound"; values: ParameterValueMap } & (
  | { kind: "definition"; definition: DefinitionId }
  | { kind: "reference"; composition: CompositionId; revision: number });
type Link = { id: LinkId; from: PortRef; to: PortRef };
type Modulation = { id: ModulationId; source: ControlSource; target: ParameterRef;
  depth: number; curve: ConnectionCurve };
type Composition = { schemaVersion: 1; id: CompositionId; revision: number; minted: number;
  kind: "rack" | "sound"; placements; links; modulations; exposures };
```

Ownership: `packages/contract` gains the types and id brands; a new `packages/composition` owns validation, identity, scopes, compilation and editing; `packages/patch` keeps the registry and curve arithmetic; `packages/content` maps events to sound references. Reused: `Brand` and `toAddressId` in `packages/contract/src/ids.ts` for the three new ids; `ParameterDefinition` in `packages/patch/src/registry/definition.ts` for every brick parameter (section 4); `ConnectionCurve` in `packages/contract/src/patch.ts` for modulation curves; `draftIssue` in `packages/contract/src/issue.ts` for every refusal. New, since the scout found none at baseline: `Port`, `Definition`, `Composition` and the compiler.

## 2. Identity, references, revisions

Four identities, per disposition 2:

| Identity | Purpose and rule |
| --- | --- |
| `CompositionId` | A document lineage; never reused, a copy mints a new one |
| `PlacementId` | A slot within one document; minted from `Composition.minted`, a cursor that only grows; no `.` allowed |
| Flat id, the seed label | A slot within a compiled Sound; placement path joined with `.`, injective because authored ids reserve `.`; feeds `childSeed` |
| Program digest | Compiled content; SHA-256 of canonical slots, edges and values, excluding composition id, revision and seeds |

`revision` is one monotonic integer per document: the concurrency token, as in `packages/control/src/surface.ts` `apply`, the pin a reference names, and the undo unit, since undo restores a prior revision. A reference placement pins `{composition, revision}` and carries local values for the rack's exposures. Editing inside a referenced rack from the referring Sound refuses `pinned_reference`; the author edits the library rack, then `repin` moves the pin. `copyComposition` yields a new id at revision 0, identical content, no origin field; its program digest equals the source's.

**Challenge to disposition 2.** It tolerates origin metadata without authority. This spec omits the field: no reader exists, and a field beside the placement reference is a duplicate authority waiting for one. A "copied from" label, if the Studio wants one, lives outside identity.

The cursor replaces `nextMemberId` in `packages/patch/src/patch-editing.ts`, which reuses the lowest free id; values inside placements replace the flat `Patch.parameters` map `removeMember` leaves orphaned. Both defects, executed in the scout, become the red half of the identity test.

## 3. Typed composition and scopes

Links join ports of equal rate and channel count; anything else is an explicit brick. Control reaches a parameter only through a modulation, reusing the `PatchResolver.applyConnection` arithmetic in `packages/patch/src/patch-resolution.ts` and the cycle walk in `packages/patch/src/patch-validation.ts` `validateConnectionCycles`, both extracted as pure exports first (section 8). Cycles are refused; the feedback brick is excluded.

A `sound` gives every top level placement a region. A `rack` names none; its placements inherit the region of the placement referencing it, recursively. A sound alone has two reserved ports: `voice.out`, the sink for voice region outputs, and `mixdown`, the source for sound region inputs. Mixdown sums `voice.out` per voice, then across voices, in flat id order, so array order cannot change a sum.

Rules, each a compile issue naming the placement paths:

- `scope_capability`: a `sound` capability definition placed, directly or through a rack, in the voice region; disposition 3's hidden Sound lifetime effect per voice.
- `scope_crossing`: a link or modulation between regions other than through `voice.out` and `mixdown`. Cross scope control needs an explicit `broadcast` or `reduce` modulation kind, reserved and excluded.
- `region_missing` or `region_forbidden`: a sound placement without a region, a rack placement with one.

**Reusable rack, instantiated twice.** Rack `tone-voice`: `tone` (capability `any`) into `biquad` into `envelope`, exposing `pitch` and `cutoff`. Sound `pair`: placements `a` and `b` reference `tone-voice` at revision 1 in the voice region, pitch 440 and 660, both linked to `voice.out`; `space` places `echo` (capability `sound`) in the sound region, fed from `mixdown`, linked to output port `main`, which names no destination, per disposition 7.

**Illegal.** Placing `echo` inside `tone-voice` and referencing that rack from the voice region: `scope_capability` at `a.echo` and `b.echo`. Modulating `space` echo level from `a.envelope`'s control output: `scope_crossing` at `a.envelope` and `space`.

## 4. Parameter edit semantics

Disposition 4 wants orthogonal dimensions and no second frozen or live field. `ParameterDefinition.lifetime` already says when a value is read and `resolution.kind` already marks derived. One field is added, `edit: "continuous" | "preparatory"`, saying what an edit costs, correcting the scout's three valued class, which duplicated `derived`.

| Dimension | Source of truth | Outcome |
| --- | --- | --- |
| Edit cost | `edit` on the definition | continuous gives `command`; preparatory gives `prepare` |
| Read timing | `lifetime`, unchanged | none; orthogonal |
| Derivation | `resolution.kind`, unchanged | derived gives `refuse` with `read_only` |
| Topology | the edit operation | insert, remove, link, modulate and repin give `prepare` |
| Mutability | placement kind | inside a reference gives `refuse` with `pinned_reference` |
| Capacity | the runtime | accept or refuse a `prepare`; runtime spec |

Preparatory rows: `DLY-12`, since `packages/patch/src/voice-binding.ts` `bindEcho` elides a zero level echo; `DLY-10`, since it sizes the echo buffer; `AMP-07`, since `packages/engine/src/voice-lifetime.ts` `beginVoice` derives lifetime kind from a zero sustain. All else stays continuous. Disposition 4's zero to positive delay edit is therefore `prepare`; a level edit within the positive range is `command`.

**Deletion and reinsertion.** Removing placement `b` removes its values, cascades to every link and modulation naming `b`, and reports the cascaded ids. Inserting `tone-voice` again mints the next cursor id, never `b`, with definition defaults, never the removed values. Undo to revision 3 brings `b` back with its values, because a revision is content; that is the only route by which a deleted identity reappears.

## 5. Minimal control surface and state changes

The surface keeps the shape of `packages/control/src/surface.ts`: `targets`, `snapshot`, `apply` with `expectedRevision`, whole batches, refusal before commit. Three changes: the target is a `CompositionId`, so two events sharing one Sound share one target explicitly and the `initialState` aliasing collapse cannot occur; the snapshot returns document, revision and program digest; `apply` returns a plan.

```ts
type EditPlan =
  | { applied: false; issues: readonly ControlIssue[] }
  | { applied: true; revision: number; effect:
      | { kind: "command"; commands: readonly ParameterCommand[] }
      | { kind: "prepare"; program: CompiledProgram;
          transfer: readonly { from: string; to: string }[]; supersedes: string | null } };
```

`transfer` lists surviving flat ids, old to new, for compatible state transfer where the runtime supports it; `supersedes` names the digest of a still pending program this plan replaces.

**Sustained structural edit, caller example.** A Studio holds a `pair` note and inserts a filter after `a`:

```ts
const plan = surface.apply({ target: pairId, expectedRevision: 3, edits: [
  { operation: "insert", region: "voice", definition: "biquad" },        // mints p-04
  { operation: "unlink", id: linkAOut },
  { operation: "link", from: { placement: "a", port: "out" }, to: { placement: "p-04", port: "in" } },
  { operation: "link", from: { placement: "p-04", port: "out" }, to: { placement: "voice.out" } }
]});
if (plan.applied && plan.effect.kind === "prepare") {
  await host.install(instance, plan.effect.program, plan.effect.transfer);
}
```

`transfer` maps `a.tone`, `a.biquad`, `a.envelope`, the three under `b`, and `space` to themselves; `p-04` is absent, having no prior state.

Pack boundary: `Pack.events` maps an event to `{composition, revision}` in a `library`, per the pack disposition; `Certification` gains a program digest per event in the consuming probe; `Pack.character` is excluded.

## 6. Interfaces proposed to the runtime spec

Resolved here, consumed there: `CompiledProgram` carries `digest`; `slots` in topological order, voice before sound, each with `path`, `definition`, `region`, `values`, `inputs` and compiled modulations; `outputs` as named ports with channel counts; `resources` as summed declared state bytes per region; `seedLabels` in slot order. `ParameterCommand` is `{path, key, value}`; frame assignment is the runtime's.

Unresolved, labelled:

1. Slot kernel encoding for the runtime interpreter; the probe's reference interpreter is a stand in.
2. Smoothing and frame placement of `ParameterCommand`.
3. Transition policy on `prepare`, crossfade or state transfer, and how refusal on capacity returns to the surface.
4. Units and completeness of `Definition.state` for the runtime's accounting.
5. Binding of the Sound's output ports to emitters and spatial routing.

## 7. Composition probe

**Environment.** Node only, isolated worktree, no browser. Proposed:

```sh
git worktree add ../audioface-probe-composition -b probe/composition 10ba9fc
pnpm install
node --test packages/patch/test/            # unit 1 gate, unchanged behaviour
node --test packages/composition/test/
pnpm run typecheck && pnpm run verify:structure
```

**Files to create** under `packages/composition`: `package.json`, `tsconfig.json`; `src/document.ts`, `src/identity.ts`, `src/scope.ts`, `src/compile.ts`, `src/edit.ts`, `src/surface.ts`, `src/index.ts`; `test-support/definitions.mjs` binding `tone`, `biquad`, `envelope` and `echo` to `createSourceGenerator`, `filtered`, `stageLevel` and `echoed` in `packages/engine/src`; `test-support/fixtures.mjs` with `tone-voice`, `pair` and the twin `pair-flat` whose ids are `a.tone`, `a.biquad`, `a.envelope`, `b.tone`, `b.biquad`, `b.envelope`, `space`; `test-support/interpret.mjs`, the reference interpreter; five tests named below.

**Files to change.** `scripts/verify-structure.mjs` `ALLOWED_EDGES`: one row for `packages/composition`, allowing contract and patch, engine as `devAllow`. `tsconfig.json`: one reference. `packages/patch/src/registry/definition.ts`: the `edit` option and field, default continuous; `registry/parameters.ts`: three preparatory rows. `packages/patch/src/patch-resolution.ts`: extract `applyCurve` from `PatchResolver.applyConnection`, called from there. `packages/patch/src/patch-validation.ts`: extract `dependencyCycle` from `validateConnectionCycles` and `visit`. **Delete:** nothing in the probe. Forward removal map: `patch-editing.ts`, `patch-recipe.ts`, `Patch.parameters`, `ControlTarget` by `PatchId` and `EnvelopeSegment` leave when the 28 shipping sounds migrate.

**Assertions**, each a named test:

1. `identity.test.mjs`: remove `b`, no link, modulation or value names `b`, result lists the cascaded link id; insert `tone-voice`, id is `p-04`, pitch is the default 660, not 440; the same sequence through baseline `insertMember` and `removeMember` fails them, the red half.
2. `scope.test.mjs`: `pair` compiles; the two illegal documents refuse with `scope_capability` at `a.echo` and `b.echo`, and `scope_crossing` naming `a.envelope` and `space`; a rack placement with a region refuses `region_forbidden`.
3. `compile-equivalence.test.mjs`: `compile(pair).digest === compile(pairFlat).digest`; with one seeded jitter modulation on `a.biquad` cutoff in both, 48000 frames through the reference interpreter under one `VoiceSeed` are equal sample for sample; a reversed placement array and a second compile give the same digest; `seedLabels` equals the seven flat ids; compile time is recorded, not judged.
4. `reference.test.mjs`: editing `tone-voice` to revision 2 leaves `compile(pair).digest` unchanged; `repin` to revision 2 changes it; `copyComposition(toneVoice)` has a new id, revision 0, no origin property, and its program digest equals the original's; a `set` inside `a` on a rack internal parameter refuses `pinned_reference`.
5. `edit-plan.test.mjs`: cutoff 2000 to 2400 gives `command` and an unchanged digest; `DLY-12` 0 to 0.5 gives `prepare` and a new digest; a derived key refuses `read_only`; the section 5 batch gives `prepare` whose `transfer` has exactly seven entries and omits `p-04`; a second `prepare` before any install carries `supersedes` equal to the first digest; a stale `expectedRevision` refuses `revision_mismatch` and changes nothing.

**Falsifiers.** A sample differs between nested and flat with the jitter present, meaning the identity mapping or sum order is underdefined. A continuous parameter changes the digest. A deleted id returns or a reference to it survives. A library edit changes a pinned Sound. An illegal document compiles. Any of these blocks the runtime probe.

**Intentional exclusions.** Tempo maps and clocks; assets; undo beyond revision restore; macros and presets; `Pack.character`; the feedback brick; `broadcast` and `reduce`; `ControlSchema` projection, refactor during the Studio slice; nested voice spawning; any performance judgment.

## 8. Implementation sequence

Each unit is gated and depends only on those above it.

1. Registry `edit` field with three preparatory rows; `applyCurve` and `dependencyCycle` extracted. Gate: `node --test packages/patch/test/` unchanged, `verify:structure` passes; the dispositions' refactor first at the touched seam.
2. Document types, validation, minting, copy, flat ids. Gate: test 1.
3. Scope checker. Gate: test 2.
4. Compiler with canonical order and digest. Gate: test 3 digest half.
5. Reference interpreter over the reused kernels. Gate: test 3 sample half.
6. References and repin. Gate: test 4.
7. Edit planner and surface. Gate: test 5.
8. Handoff: the runtime probe consumes `CompiledProgram`, `EditPlan` and `ParameterCommand`; the lead closes the five unresolved interfaces first.

**Second challenge.** The dispositions place "cancellation and rebuild do not retain stale instances" in the composition probe. Instances exist only in the runtime; this spec asserts the authoring half through `supersedes` and hands the rest to the runtime probe, since a Node assertion without a host proves nothing.

Unresolved interfaces: 5.
