---
title: Audioface Foundation Core, Arena Decision
type: decisions
tags: [audioface, architecture, engine, arena]
summary: Base and grafts selected from three blind foundation designs across Opus, GPT and Grok
status: active
project: audioface
---

# Foundation core, arena decision

Three candidates designed in isolation on three model families against
`~/.mdx/design/audioface-foundation.md`. Candidates at
`~/.mdx/TMP/pstack/audioface-foundation/candidate-{a,b,c}.md`.

## Where all three agreed

Unanimous across three families working blind. Treated as settled, not re-litigated.

1. Delete the semantic branch entirely: `token-set` scope, `SemanticContext`, `AudiofaceToken`,
   `ThemeSnapshot`, `MATERIAL_PROFILES`, and the metric and material connection sources.
2. Delete `resolution.kind: "future"`, `seedValue`, `phase` and
   `PatchParameterNotImplementedError`. A parameter is in the registry or it does not exist.
3. Mute and solo leave the render contract. They are editor state, applied before resolution.
4. A plugin is one frozen data object: events, scenarios, gates. No callbacks, no code, no lifecycle
   hooks, no registry, no event bus. It can never touch a voice, add a source type, add a parameter,
   or execute at render time.
5. Pack character is a declarative parameter overlay merged into a single resolve pass, not a second
   resolution stage and not a macro system.
6. Layers stay mono. Stereo happens exactly once, after the voice sum.
7. One limiter on the master bus, owned by the foundation, unreachable from a patch or a pack.
   Candidate A put it best: a pack that can tune the limiter can defeat the stress gate, which makes
   the gate theatre.
8. Distance is one addressed parameter driving foundation owned physics. Packs scale the response,
   they never author the curves. Four distance knobs would make near and far a mix recipe.
9. The seed is required on every trigger. The engine never invents one.
10. Internal time is frames, not milliseconds.

## Base: candidate A

Selected for the sharpest position and the most complete argument. Its core claim: a resolved patch
never becomes an audio graph, because resolution has already collapsed every connection to scalars.
A voice is a flat list of fixed chains summed into one stereo bus, and there is exactly one renderer,
block driven at a fixed 128 samples, identical online and offline.

Two of three candidates rejected the audio graph independently. That matters, because every problem
this project hit in the last day traces to measuring one code path and shipping another: the
unreliable `getChannelData` view, offline versus realtime divergence, mono only rendering, and a
harness built to test the tests.

A also produced the sharpest critique of the model we are copying. It independently found that
`ResolvedPatch.durationMs` reads `max(TIM-03)` and ignores `TIM-02` layer delay while the derived
patch duration sums them. Two answers to one question. That was already on the defect list from a
separate audit, which makes it the second independent confirmation.

Its strongest structural argument for the copy: pan, width, distance and take all land under the
existing `trigger` root with no new scope. A model that absorbs every day one requirement without a
new root is the right thing to keep.

## Grafts

**From B, labeled child seeds.** The best single idea in the arena. Every jitter connection,
generator, layer and channel derives its own labeled child seed from the voice seed, so graph order
cannot perturb another take. This kills the Phase 1 constraint where draw order defined sound
identity and any reordering moved fingerprints. A reached the same conclusion by keying draws on
`(seed, connectionId)`; B's framing states the property we actually want. Take B's property, A's
mechanism.

**From B, the gate union.** Gates as an explicit discriminated union carrying their thresholds:
coverage, spectral with band and mean bounds, stress with peak and loudness bounds, distinctness with
pairs and a minimum distance. It maps directly onto the PASS badges in the reference tool.

**From C, frames as the unit throughout.** `startFrame`, `endFrame`, `durationFrames`. A agreed in
passing; C made it structural.

**From A over C, the voice seed triple.** `voiceSeed(packId, eventId, take)` rather than C's
`takeSeed(event, take)`. Pack identity belongs in the seed or two packs share a variation stream.

## Rejected, with reasons

- **B's Web Audio node graph.** It preserves the online versus offline divergence that produced
  today's failures, and it puts voice lifetime management inside node disposal. Rejected despite
  being much less code to write.
- **C's single sequential RNG stream.** Order dependent, which is the defect the graft fixes.
- **C's `Float64Array` buffers.** Float32 is what the hardware takes.
- **Per layer stereo decorrelation**, present in B as an allpass stereoizer. A refuses it explicitly
  and is right: constant power pan plus one width control is enough, and richer imaging is a
  foundation change with review.

## Open, and it is the real gap

**Sustained and looping sounds.** Candidate A is fire and forget: no note off, no release stage, a
voice dies when its cursor passes its authored life. That is correct for gunshots, hitmarkers and UI
clicks. It is wrong for engine hum, ambience beds and anything that must sustain until told to stop.
B carries `release(at, duration)` and a stop handle for exactly this.

The reference tool shows only one shot events, so nothing in the brief forced the question. Ambience
as a plugin would. This must be decided before the first commit, because adding sustain to a fire and
forget voice model later is a rewrite of voice lifetime.

## Ambience, resolved

Ambience is in scope. Candidate A amended the base; Grok answered the same question blind. They
disagreed on the discriminant and the disagreement resolved in A's favour, but Grok found a hole in
A that A did not see.

**Discriminant: A, with Grok's concern satisfied.** `sustain === 0` on the amplitude envelope is the
mechanism, and the event declaration carries a `sustaining` flag as the checkable contract. Grok was
right that lifetime is control and sustain is signal, and the declaration is what keeps them honest:
the coverage gate fails a pack whose `engine-hum` does not actually sustain. Sustain is linear
`0..1`, never decibels, because dB has no zero and a one shot must be exactly representable.

**Sustain is per layer.** A bed carries a transient onset alongside a sustaining body for free.

**Remaining life of a sustaining voice is its release length**, not infinity. The steal score survives
unchanged. Both candidates then converged independently on stealing only within a class, A with three
declared classes and reserve floors. Packs get no priority knob.

**Grafted from Grok, and it is a real hole in A: listener fields are not frozen at resolve.** A held
bed outlives the player walking around it, so pan, width and distance live on the voice and may change
between blocks, while patch scalars stay frozen. Distance curves move into the image step. The *what*
of agreement 8 holds; the *when* was wrong.

**Grafted from Grok: a leak must fail loudly.** A held voice never released is a bug, not a state. A
`held-leak` gate fails any held voice still open at scenario end. No secret timeout online; a timeout
that fixes rain is a second, quieter bug.

**Two DSP details from A that would have been bugs.** Phase accumulators must be float64 wrapped to
`[0,1)` each sample; buffers stay Float32.

*Refined by measurement, 2026-08-20.* Both prescriptions stand and the rationale above was wrong
about which one does the work. Measured against a reference phase computed by integer arithmetic,
over ten seconds at 48 kHz and 660 Hz: the shipped float64 wrapped accumulator stays within 1e-11
cycles of exact, the same accumulator in float32 reaches 2.2e-3 and grows linearly rather than
settling, and an unwrapped float32 accumulator loses half a cycle, meaning the entire signal, inside
those ten seconds. So the WRAP is what is load bearing on the seconds timescale, and the float64 is
what is load bearing over an ambience bed's lifetime. Wrapped float32 drifts 1.3e-2 cycles a minute,
which is nine orders worse than float64 but is a pitch error of 2e-4 Hz and not by itself audible.
The original claim that float32 loses audible precision within seconds belongs to the unwrapped
accumulator, not the wrapped one. And noise is a counter based PRNG drawn per sample from its labeled child seed, period
2^64, zero memory, seamless by construction, so there is no loop point anywhere.

**Two ramps, two owners.** `AMP-08` release is distinct from the anti click steal ramp. Merging them
would make every steal audible.

**The spectral gate gains a window.** `"whole" | "steady"`. A bed measures steady state only, or a
bright bed hides behind a soft onset in a mean spanning the attack.

**Known casualty, reported by A against itself.** `durationFrames` is null for a sustaining patch, so
patch duration stops being a total. The `TIM-02` summing defect still stands and still needs fixing,
but the single duration number does not survive ambience.

# Structure, arena decision

Two candidates designed blind against one brief on GPT (codex) and Opus. Candidates at
`~/.mdx/TMP/pstack/audioface-next/structure-candidate-{1,2}.md`.

## Where both agreed

Settled, not re-litigated.

1. One contract package with zero workspace edges is the acyclicity anchor. Every seam type lives
   there and both sides import it.
2. `patch`, `engine` and `measure` are siblings that never import each other. They meet only in
   `control`.
3. `control` is the composition root. Adapters import the contract and `control`, nothing else. An
   adapter cannot construct an engine, a resolver or a gate.
4. Adding a control is adding a row or a leaf to authoritative data. No adapter file is touched. The
   CLI takes an address as an argument, never a flag per parameter. MCP tool count equals the
   operation count, never the control count. HTTP puts the address in the path, never a route table.
   The UI switches on the leaf kind.
5. Enforcement is layered and cheapest first: pnpm workspace isolation so an undeclared package is
   not on disk, TypeScript project references so the typecheck fails, then one script in `check`.
6. `measure` is never told what produced a signal. No patch, pack or event id crosses that seam, so a
   gate can never special case a pack.
7. `engine` may not import the patch model, so it can never name a `Patch`.
8. Scenario authoring is the layer that stresses the design hardest. Both named it unprompted.

## Base: candidate 1

Selected for the control contract, which was the hardest requirement in the brief.

Its `ControlManifest` is a recursive discriminated union of `number`, `boolean`, `enum`, `text`,
`object`, `list` and `union`, with leaves carrying address, label, group, unit, range, curve,
default, authority and write cadence. Its `ControlEdit` has three exhaustive operations, `set`,
`insert` and `remove`, each with a target and a path, applied atomically against an expected
revision.

That shape matches the domain that already exists. `packages/core/src/patch-editing.ts` already
ships `deleteLayer` and `retypeLayer` alongside `editParameter`, so structural editing is present
today, not a future requirement. A patch is a tree of layers and connections, and a flat row list
cannot describe a tree.

Candidate 2 conceded the same point and answered it with a second operation, `structure(target,
edit)`, sitting beside `set`. Two operations means every adapter projects two shapes and the second
one has no stated CLI, HTTP or MCP mapping. Candidate 1's three operations over one path model cover
both cases with one projection.

Candidate 1 also carries an expected revision on apply. Candidate 2 has no concurrency story at all,
and a UI open beside an MCP agent editing the same patch is the normal case, not an edge case.

Its adapter and app split is kept. An adapter is a projection and a library. An app is a thin
composition root that selects the plugin and pack and hands the adapter a `ControlSurface`. That
split is what makes "an adapter cannot construct an engine" structural rather than aspirational.

## Grafts from candidate 2

**Address stability, and it is the best single observation in the round.** `scenario/events/3/at`
reorders on insert. Every addressable collection member carries an id from the first commit, as
layers already do, and a positional index never appears in an address. Candidate 1's path based
edits have exactly this defect and candidate 1 did not see it.

**`lifetime: "frozen" | "live"` as a registry column.** This turns the listener fields correction
into data. The resolver reads the column to decide freeze against pass through, so pan, width and
distance stop being a special case in the resolver and become a property of the row.

**Cost boundary via `assertNever`.** Adding a control is free. Adding a *kind* breaks `widgetFor` at
typecheck, which is the correct place to pay. One conformance test asserts every row has a widget
kind and a parse path. One test, not four.

**Zod lives in the contract.** Candidate 1 kept the contract free of every dependency including Zod.
A contract you cannot parse is not one. The honest framing is candidate 2's: zero *workspace* edges,
one leaf dependency, because third party pack data enters at that boundary.

**A runtime pack parser.** Candidate 1's `PackImplementation<P extends PluginDefinition>` mapped
type is an elegant compile time completeness check and it is kept for workspace packs. It cannot
reach a third party pack shipped as JSON. `loadPack` fails unless the key set equals the event set
exactly, and both checks enforce one invariant at two points.

**The incremental order.** Candidate 2's sequence de-risks and candidate 1's does not. Rename first
to prove the workspace wiring with no content change. Extract the contract. Split the 598 line
parameter registry *before* slice 2 adds sustain and listener rows. Then stand up `control` and the
CLI adapter **before one line of DSP exists**, so the no-per-adapter-work claim is proven against
the parameters that already render. Candidate 1 put control at step 6, after the engine, which would
have had us building a renderer and a control surface at the same time.

**Enforcement mechanics.** `scripts/verify-structure.mjs` parses every import against one literal
`ALLOWED_EDGES` table and rejects deep imports and relative escapes such as `../../engine/src/x.ts`,
the one hole pnpm cannot see. It absorbs the existing `verify-skeleton.mjs` checks rather than
replacing them: the SHA256 pins and the forbidden terms list stay.

## Rejected, with reasons

- **Candidate 2's `set` plus `structure` split.** Structural editing already exists in the code
  being carried across. Three exhaustive operations on one path model is one projection instead of
  two.
- **Candidate 2's `model` package name.** Vague, and candidate 2's own placement rule bans vague
  names. The package is `patch`; it owns patches, the parameter catalogue, validation, editing and
  resolution.
- **Candidate 2's `catalog` package name.** It collides with `ControlCatalog`. The plugin and pack
  seam is `content` and the surface description is `ControlManifest`.
- **Candidate 2 keeping `canonical-patches.ts` in the foundation.** The 23 sounds are a pack. Button
  and modal vocabulary in the foundation is precisely the layering violation the architecture exists
  to prevent, and the one test that binds to it is repointed in the same commit.

## The package graph

`A -> B` means A may import B. There is no reverse edge.

```text
contract   -> nothing in the workspace, zod only
patch      -> contract
engine     -> contract
measure    -> contract
content    -> contract, patch
control    -> contract, patch, engine, measure, content
adapters/* -> contract, control
apps/*     -> control, one adapter, a selected plugin and pack
plugins/*  -> contract
packs/*    -> contract, its plugin
```

## The placement rule

Name the one type the file produces. The package owning that type's contract is where it goes. Two
types means two files. A directory is the plural of the noun its files own. Nothing is named
`runtime`, `utils`, `helpers` or `shared`, because those names mean the rule went unapplied. Only a
package barrel is `index.ts`. Files stay under 700 lines and functions under 150.
