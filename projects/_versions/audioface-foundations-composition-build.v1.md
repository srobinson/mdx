---
title: Audioface foundations composition build
type: projects
tags: [audioface, foundations, composition, contract, compiler, build-report]
summary: Deliverable one of the foundation probes, committed on probe/foundation-composition at 3455fb3 over baseline 10ba9fc, with the gates that ran, the interface refinements made against the document specification, and the exact integration handoff.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-document-spec, audioface-foundation-runtime-probes-spec, audioface-foundation-dispositions, audioface-scout-foundations-authoring]
confidence: medium
---

# Composition build, deliverable one

Worktree `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/composition`, branch `probe/foundation-composition`, baseline `10ba9fc16cea55271c6d428c8fe64c8df0b9c354`, commit `3455fb343f2db6c137c73daff749882db8ef24ac`. Specification pair verified before work: document `e5bce921c9e55a63ece4e17df4e5ed6237d95f988177a870832ea2168a8c73df`, runtime `6615929b170d3681f0fc994985d9f5186316f87b6d0b7322fbcabe5e12f1555d`. The main checkout stayed clean at the baseline throughout; the runtime worktree was not touched.

## What was built, by owner

**Contract.** `ParameterDefinition`, `ParameterDefault` and `ParameterResolution` moved from `packages/patch/src/registry/definition.ts` into `packages/contract/src/parameter.ts`; the unit conversions moved whole from patch to `packages/contract/src/units.ts`, because a kernel's preparation in the engine needs frames from milliseconds and may not import patch. Every caller migrated, the old declarations deleted. New: `composition.ts` (Definition, Placement, Link, Modulation, Exposure, Composition, Library, SeedMap, CompositionEdit, CompositionIssueCode), `program.ts` (ExecutionProfile, ResourceDemand, KernelPreparation, ProgramSpec, ParameterCommand, EditPlan, `programKey`), `digest.ts` (canonical JSON and a hand written SHA-256, tested against the platform digest), `curve.ts` (`applyCurve`, extracted from `PatchResolver.applyConnection`), `graph.ts` (`dependencyCycle`, extracted from `validateConnectionCycles`), and seven identity brands with `toPlacementId` enforcing `[A-Za-z0-9_-]+`.

**Patch.** `src/composition/library.ts` (snapshots keyed by lineage and revision, `copyComposition`), `document.ts` (set, insert, remove, link, unlink, modulate, unmodulate, repin; minting from a cursor that only grows; cascaded removal), `scope.ts` (expansion through pinned references and exposures, region and capability rules, defaults filled after exposures land), `links.ts` (link resolution through rack ports, crossing rule), `compile.ts` (canonical order, sum order, demand per region, path latency, key), `plan.ts` (`planEdit`, the one classifier, with surviving slots for transfer).

**Engine.** `src/kernel-preparation.ts`: preparations for `tone`, `lowpass`, `highpass`, `bandpass`, `envelope`, `echo` (elided at level zero, exact length) and `delay` (preallocated to a power of two). Configuration, state layout and demand in named units, with the worst permitted tail read from the definition's rows. Declarations only: execution against a program is deliverable two's.

**Control.** `src/composition-surface.ts`: `createCompositionSurface(library, profile, kernels)` and `createEngineCompositionSurface` injecting the engine catalogue. Keeps the revision, lands a batch whole or not at all, retains every accepted snapshot.

**Tests.** `packages/patch/test/composition-document.test.mjs` and `composition-scope.test.mjs` over a stub catalogue (specification tests 1 and 2); `test/foundations/fixtures.ts`, `oracle.ts` and `composition.test.mjs` (test 3 key half, test 4, test 5, oracle determinism); `packages/contract/test/digest.test.mjs`; `packages/engine/test/kernel-preparation.test.mjs`; `packages/control/test/composition-surface.test.mjs`.

## Refinements against the document specification

Each is a routine detail resolved in the implementation, none a competing contract.

1. `planEdit` takes the execution profile: `planEdit(document, library, profile, kernels, edits)`. Normalization needs the sample rate.
2. `KernelPreparation.normalize(values, profile, definition)` receives the definition so a kernel reserves the worst its declared ranges permit, rather than duplicating registry ceilings.
3. A slot carries `state: { layout, version } | null` and `demand` separately. A stateless kernel still has demand.
4. `EditPlan.issues` are `CompositionIssue`, a code set of their own, shaped by `draftIssue`. Widening `ControlIssueCode` would have forced the HTTP adapter's exhaustive status map for no consumer.
5. A modulation or a set reaches a reference only through its exposures; a path below a reference refuses `pinned_reference`. The fixture's jitter targets `a`'s `cutoff`, which compiles to `a.biquad` `FLT-10`.
6. Canonical slot order is topological within each region, voice before sound, ties broken by seed label. Sum order follows slot order, then port name. With the seed map this makes the flat twin's key equal to the nested key regardless of its authored ids, which placement key ordering could not.
7. A modulation's seed label is its target slot's label plus its authored id, so nested and flat twins draw one stream.
8. Rack inputs exist beside rack outputs, both forwarded by a reference; a sound has none.

## Gates that ran

Baseline before any change, then the finished unit, both from the worktree root:

```
pnpm run check        # typecheck, node --test, oxlint, oxfmt --check, verify:structure
```

| Run | Tests | Pass | Fail | Skipped | Lint | Format | Structure | Exit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline 10ba9fc | 270 | 270 | 0 | 0 | clean | clean | passed | 0 |
| Commit 3455fb3 | 295 | 294 | 0 | 1 | clean | clean | passed | 0 |

`pnpm --filter @audioface/app-web build` emitted `dist/index.html` and `dist/null-test.html` after the contract move, exit 0; the ignored esbuild install script did not block it. `node --test packages/patch/test/` as written in the specification does not run on Node 25.9.0 (a directory argument is treated as a file); the glob form `node --test 'packages/patch/test/*.test.mjs'` does, and `pnpm test` covers everything. The patch package's own tests passed unchanged after the parameter move, the gate section 8 of the specification names.

Before and after evidence for the identity defect: the authoring scout executed `insertMember` after `removeMember` on the baseline patch model and the removed id returned with the removed value and its orphaned connections. `composition-document.test.mjs` asserts the composition mints `p-04`, carries the default 660 and not the removed 440, cascades `b-mix` and the modulation naming `b`, and that the removed link does not return.

## Pending integration

- **Test 3, sample half.** Nested, flat and the oracle sample for sample through the shared runtime. Marked `skip` in `test/foundations/composition.test.mjs` with the reason. Needs deliverable two: a runtime that instantiates a `ProgramSpec`, applies compiled modulations at a voice's start with `childSeed(root, slot.seedLabel)` then the modulation's label, and renders 48,000 frames under one root seed. The oracle in `test/foundations/oracle.ts` is the specification of that render and asserts its own determinism and finiteness now.
- **Stamping and correlation.** The surface hands back the planner's effect. Attaching Sound id, ticket, generation, base revision and absolute frame, submitting it, cancelling a pending ticket by identity and reporting applied, cancelled and refused outcomes wait for the runtime's ticket API.
- **Transfer validation.** `transfer` names surviving slots by key, kernel, version and configuration. Layout version, execution profile and capacity checks before any state moves remain the runtime's.
- **Split echo.** `echoStage` keeps summing in place; the dry and wet ports are declared on the definition and carried to the output's tail flag. The extraction that reuses one arithmetic for both ports belongs with the transition comparator.
- **Envelope semantics.** The oracle defines the envelope kernel as gain times the stage level until the shape ends. The runtime's envelope kernel must match it or the oracle test will say so.

## Limitations and risks

No sample, browser or performance claim is made. Kernel demand numbers are declarations from the state each engine stage holds, not measurements. Frozen and live read timing is carried by the definition's row (the fixture declares the biquad cutoff live) and not by the program; the runtime reads it from its kernel. No JSON schema exists for compositions yet; documents are constructed in code. `scope.ts` is 518 lines after the link seam was split out. The `TIMING` fixture definition exists only to refuse a derived row and must never be compiled.
