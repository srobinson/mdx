---
title: Audioface Phase 2, Engine Rewrite Over the Patch Model
type: design
tags: [audioface, audio, engine, rewrite, golden-master]
summary: Phase list for rewriting the audio engine to consume ResolvedPatch directly and close the 21 parameter render gap
status: active
project: audioface
---

# Audioface Phase 2, Engine Rewrite

Grounded in `~/.mdx/design/audioface-phase2-decision-sheet.md`, itself synthesized from
`~/.mdx/projects/audioface-scout-engine.md` and `~/.mdx/projects/audioface-scout-consumers.md`.
Decision trail at `~/.mdx/sessions/audioface-phase2-engine-rewrite.tsv`.

Baseline commit `556b7c8`, tree clean.

## Context

Phase 1 built a parameter registry of 33 addressed parameters and a `Patch` aggregate that can
express all of them. The renderer can hear 12. The remaining 21 have no render path. Phase 2 closes
that gap.

The `packages/engine/src/index.ts` file is 258 lines. Its size is not the size of this phase. The
work is the gap, not the file.

## Definition of done, as a falsifiable predicate

1. `pnpm run check` exits 0.
2. Every one of the 33 registered parameters either renders, with a test that fails when it stops
   rendering, or is explicitly recorded as deferred with a reason.
3. `packages/engine/src/index.ts` in its current form is deleted, not running alongside its
   replacement.
4. Every commit that moves `scripts/golden-master/baseline.jsonl` carries a reviewed metric by
   metric diff and a named cause. No commit moves it silently.

## The single detector problem

Of the four commands `pnpm run check` runs, only `audio:golden` can hear. `typecheck`, `test` and
`validate` stay green through any change to how the engine sounds. Every gate hole below therefore
compounds: there is no second signal to catch what the first one misses.

Recorded gate holes at `556b7c8`:

- `tsconfig.json` references only `tsconfig.packages.json` and `apps/studio`. The entire render
  harness under `scripts/` and every test under `test/` is untyped.
- `test/golden-master.test.mjs` parses the committed baseline and counts tokens. It never compares a
  fresh render to a committed value.
- The rendering tests in that file are self relative, comparing a quiet render against a loud one
  produced by the same code. A uniformly changed engine stays green.
- `test/engine.test.mjs` asserts twelve regexes against engine source text. A behavior preserving
  rename goes red. A behavior changing edit that keeps the strings goes green. This test is hostile
  to exactly the work Phase 2 does.
- `pnpm run validate` reads only root `src/`, which is not what ships.
- The offline harness swaps global `Math.random`. Draw count, not synthesis math, is the invariant
  for every noise fingerprint.

## Decisions taken

**The engine consumes `ResolvedPatch` directly.** The alternative, keeping
`packages/core/src/playback.ts#toResolvedPlayback` and the legacy `AudiofaceLayer` union, was
rejected as a false choice. The projection discards `PCH-03` and `PCH-09` at
`packages/core/src/canonical-patches.ts#projectLegacyLayerFields` and drops structure at the render
boundary, so an engine behind the projection cannot reach the 21 gap parameters at all. Keeping it
would cap the rewrite at the 12 parameters that already work.

The persistence migration is a separate axis. `AudiofaceTokenDefinition` and
`packages/core/src/token-library.ts#TokenLibraryEntry` stay until Phase 3. Studio keeps producing
tokens; the Token to Patch path built in Phase 1 carries them.

**The baseline stays frozen until parity is proven, then moves deliberately.** Three real bugs would
change how the shipping tokens sound: `AMP-06` resolves across 3 to 350 ms with zero acoustic
effect, patch duration derives from `TIM-03` alone while `TIM-01` uses `TIM-02 + TIM-03`, and the
engine floors attack at 0.5 ms under a 0.35 ms resolved minimum. Each is fixed in its own commit
after the rewrite has proven pure parity, so a moved fingerprint has one possible cause.

**Root `src/` and `apps/lab` are deleted in the grooming wave.**
`test/lab-studio-audio-parity.test.mjs` pins new core resolution to a hand written legacy JS model
that Phase 2 will not update, and `pnpm run validate` gates that model rather than what ships.

## Phases

Sequenced so that subtraction precedes scaffolding, scaffolding precedes the rewrite, and the
rewrite precedes every behavior change. Each phase lands on its own and ends in a check.

### Phase 0, groom

Delete before building. `src/audioface.js` and its `./audio` export in root `package.json`,
`apps/lab`, `test/lab-studio-audio-parity.test.mjs`,
`packages/core/src/canonical-tokens.ts#resolveTokenDefinition` and its re-export. Fold
`src/tokens.js#clamp` and `#clamp01` into `packages/core/src/runtime.ts#clamp`. Repoint or retire
`src/validator.js#validateProject` so `check` stops leaning on it. Deduplicate
`scripts/audit/descriptors.mjs#energyWeightedCentroid` against `#energyWeightedMetric` and the nine
metric identities repeated across `descriptors.mjs` and `golden-master.mjs`.

Gate: `pnpm run check` exits 0 and `baseline.jsonl` is byte identical.

### Phase 1, harden the gate

The gate is the only detector, and it must be trustworthy before the rewrite leans on it. Replace
the twelve source text regexes in `test/engine.test.mjs` with renders through
`scripts/audit/render.mjs#renderResolvedPlayback`. Retire the same `readFileSync` pattern in
`test/studio-dom.test.mjs` and `test/studio-sequence-audition.test.mjs`. Bring `scripts/` and
`test/` under `tsc`. Give `pnpm test` an absolute acoustic anchor rather than a self relative
comparison. Cover the ungated valid boundaries: 0.35 ms resolved attack against the engine's 0.5 ms
floor, 40 ms attack against a 4 ms minimum duration, and 500 ms delay plus 350 ms duration against
the 0.75 s `OFFLINE_RENDER_SECONDS` window.

Each hardening must be proven load bearing by perturbation, the way the Phase 1 gate wiring was:
break the thing, watch the new check go red, restore.

Gate: `pnpm run check` exits 0, `baseline.jsonl` byte identical, and a recorded perturbation run per
new check.

### Phase 2, design the graph model

One way door. How a `ResolvedPatch` becomes an audio graph determines whether the remaining phases
are additive or a fight. Run competing isolated candidates across model families with a read only
judge on a different family, per the `architect` skill. Deliverable is a chosen model with named
grafts and recorded rejections, not code.

### Phase 3, parity rewrite

The engine consumes `ResolvedPatch` directly and renders exactly the 12 parameters that render
today. Nothing new. Migrate all three callers,
`apps/studio/src/app/useStudioPlayback.ts`, `scripts/audit/render.mjs` and `test/engine.test.mjs`,
and delete the old path in the same wave.

Gate: `baseline.jsonl` byte identical across all 230 fingerprints. This is the clean signal the whole
sequence is built to produce.

### Phases 4 onward, one parameter group per phase

Each phase closes one group of the 21 gaps and ends in the same check: the parameter demonstrably
changes the rendered sound, and the 230 fingerprints do not move. Ordered by how much later phases
depend on them.

- Layer amplitude envelope, `AMP-04`, `AMP-05`, `AMP-06`.
- Patch amplitude constants, `AMP-02`, `AMP-16.ramp-ms`, `AMP-16.epsilon`, currently literals in
  `#createLayerOutput` and `#setVolume`.
- Output level and mute, `OUT-01`, `OUT-02`, currently filtered out at `#toResolvedPlayback`.
- Context capability, `OUT-12.sample-rate`, `OUT-12.latency-hint`.
- Layer filter reach, lifting `#connectFilter` off noise only.
- Filter envelope, `FLT-14`, `FLT-15.attack-ms`, `FLT-15.decay-ms`.
- Pitch fine tune and ratio, `PCH-03`, `PCH-09`, blocked today by `#projectLegacyLayerFields`.
- Pitch envelope, `PCH-05`, `PCH-06`.
- Impulse source, `SRC-30`, currently rejected by `#requireImplementedLayer`.
- Output chain DC block, `FXP-32`, currently rejected by `#requireImplementedOutput`.

### Final phase, the three semantic fixes

One commit each, each with a reviewed metric by metric baseline diff and a named cause. `AMP-06`
made audible, patch duration derivation reconciled with `TIM-01`, attack floor lowered to the
resolved minimum.

## Carried constraints from Phase 1

- Close the mono only render gap before pan or stereo width lands.
- Revisit the single clamp once authored gain can reach the `AMP-01` +6 dB ceiling.
- Reconsider absolute `PCH-01.end-hz` and `SRC-08.modulator-hz` against interval and ratio encoding,
  with the golden master adjudicating.
- `initialParameterValue("SRC-16")` returns `audioface-v1` rather than the documented `pink`. The
  spec is wrong, the code is right, and Phase 2 should correct the spec.

## Applicable skills for implementers

`how` over the engine and the render harness before changing either. `architect` for Phase 2.
`no-comments` over every diff before review. `interrogate` if the graph model is contested after the
arena. `technical-writing` and `unslop` for any spec text.

## Verification

Project level: `pnpm run check`, which runs `typecheck`, `test`, `validate` and `audio:golden`.
Per phase gates are named above. No phase is complete on a green `check` alone if it claims a new
check; the new check must be proven to fail under perturbation.
