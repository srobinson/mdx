---
title: Audioface Next, Current Status and Resume Point
type: projects
tags: [audioface, status, handoff]
summary: Where the audioface rewrite stands, what is decided, and what slice 2 must build
status: active
project: audioface
---

# Audioface Next, resume point

Updated 2026-08-19.

## The pivot

The old repo at `/Users/alphab/Dev/LLM/DEV/helioy/audioface` is a DONOR, read only. Work continues in
`/Users/alphab/Dev/LLM/DEV/helioy/audioface-next`, a fresh repository. No migration code is written,
ever. Things are copied deliberately or not at all.

The old repo's `main` is at `664e9ef` with a grooming wave merged. Its `phase2-gate-tests` branch at
`fd347d4` is ABANDONED and will not merge; `render.mjs` does not come across, so its `copyFromChannel`
fix survives only as recorded knowledge.

## The product

A procedural sound engine, zero audio files, aimed at game audio first. Three layers, dependency
arrow one way only:

- **Foundation**: parameters, synthesis, render, measure. Knows nothing about guns or buttons.
- **Plugin**: a domain vocabulary. Frozen data: events, scenarios, gates. No code.
- **Pack**: a stylistic realisation. Data. Studio Real, Toon Punch, Tropical Arcade, Cinematic Soft.

The product claim: a wav pack ships four takes per event for round robin. Audioface ships a seed.
Unlimited takes, zero bytes. Near and far are a parameter, not a second recording.

Ambience IS in scope, so voices must sustain, not only fire and forget.

## Authoritative documents

1. `~/.mdx/design/audioface-foundation.md` — the three layer spec and day one requirements.
2. `~/.mdx/design/audioface-foundation-decision.md` — THE authoritative record. Arena result, ten
   unanimous agreements, base and grafts, rejections with reasons, and the ambience resolution.
   Where this and anything else disagree, this wins.
3. `~/.mdx/TMP/pstack/audioface-next/skeleton-notes.md` — contains "What slice 2 must stand up", a
   table of every import the deleted golden master needed and what replaces it. This is slice 2's
   specification.
4. `~/.mdx/TMP/pstack/audioface-foundation/candidate-{a,b,c}.md` and `ambience-second-opinion.md` —
   the three blind designs and the blind second opinion.
5. `~/.mdx/sessions/audioface-phase2-engine-rewrite.tsv` — the decision trail, including superseding
   rows where a claim was retracted.

## Slice 1, done

`audioface-next` at `5fce65b`. 20 files, 3476 lines, ONE test. `check` exits 0.

Copied: the patch model (registry, schema, patches, resolution, validation, editing), the 23 sounds
as `canonical-patches.ts`, `descriptors.mjs` (verified pure measurement), and `baseline.jsonl`
byte identical at shasum `7286e897…`.

Deleted, not shimmed: the whole semantic branch, the `future` resolution split, mute and solo on the
trigger contract. `scripts/verify-skeleton.mjs` pins the baseline and descriptors by SHA256 and keeps
a forbidden terms list so none of it can quietly return.

**There is no acoustic gate right now, deliberately.** `baseline.jsonl` is inert reference data.

## Structure, decided

Second arena, two blind candidates on GPT and Opus. Full record in
`~/.mdx/design/audioface-foundation-decision.md` under `# Structure, arena decision`. That section is
binding and overrides both candidate documents at
`~/.mdx/TMP/pstack/audioface-next/structure-candidate-{1,2}.md`.

Package graph, `A -> B` means A may import B, no reverse edge:

```
contract   -> nothing in the workspace, zod only
patch      -> contract
engine     -> contract
measure    -> contract
content    -> contract, patch
control    -> contract, patch, engine, measure, content
adapters/* -> contract, control
apps/*     -> control, one adapter, a selected plugin and pack
```

Base is candidate 1 for the control contract: a recursive `ControlManifest` of `number`, `boolean`,
`enum`, `text`, `object`, `list` and `union`, and three exhaustive edit operations `set`, `insert`
and `remove` over one path model, applied atomically against an expected revision. Adding a control
touches no adapter file. Adding a schema KIND breaks `widgetFor` at typecheck through `assertNever`,
which is the correct place to pay.

Grafted from candidate 2: address stability, so every addressable collection member carries an id
from the first commit and a positional index never appears in an address; `lifetime: "frozen" |
"live"` as a registry column, which turns the listener fields correction into data; zod in the
contract; a runtime `loadPack` parser alongside candidate 1's compile time completeness check; the
incremental order; and `scripts/verify-structure.mjs` with one literal `ALLOWED_EDGES` table.

Slice A, in flight on the Opus pane: rename `packages/core` to `packages/patch`, extract
`packages/contract`, split the 598 line parameter registry. Three commits, each ending green.

Then `control` and the CLI adapter land BEFORE any DSP, so the no per adapter work claim is proven
against the parameters that already render. Slice 2, the block renderer, follows.

## Slice 2, next

The block renderer. From the decision record:

- No audio graph. A voice is a flat chain; one block driven renderer at a fixed 128 samples, identical
  online and offline.
- Envelope AHDSR, sustain per layer, sustain linear `0..1` default 0, `sustain === 0` means one shot.
  Event declaration carries a `sustaining` flag as the checkable contract.
- Labeled child seeds per connection, generator, layer and channel, so graph order cannot perturb
  another take.
- Phase accumulators float64 wrapped to `[0,1)`; buffers stay Float32.
- Noise is a counter based PRNG per sample from its child seed. No loop point anywhere.
- Patch scalars freeze at resolve. LISTENER fields (pan, width, distance) live on the voice and change
  between blocks. Distance curves run in the image step.
- One pool, class scoped stealing, reserve floors. Packs get no priority knob.
- One limiter on the master bus, unreachable from patch or pack.
- A held voice never released is a leak and must fail loudly via a `held-leak` gate.

Then the golden adapter, then the first honest acoustic comparison against the reference recording,
with stated per metric tolerances. It will NOT match exactly; different DSP gives different numbers.
That comparison is reviewed once and becomes the new baseline.

## Standing user instructions

- Simple, clean, DRY. No legacy support of any kind. No migration.
- Fewer tests. Less is more. Test the seams only; test internals only where fragile.
- No Fable. Opus, GPT (codex) and Grok runtimes only.

## Known defects carried forward

- Resolved patch duration reads `max(TIM-03)` and ignores `TIM-02` layer delay while the derived
  duration sums them. Two answers to one question. Unfixed.
- Patch duration stops being a total once a patch can sustain.

## Queued: justify or reverse

Stuart asked for the reasoning behind five choices that were made without being argued. Answer AFTER
the hardening slice lands, against a stable tree, as a written justify-or-reverse review rather than
a defence. Each answer is either a reason that holds or a commit that changes it.

1. `apps/http` uses node's own `http` module with no framework.
2. `adapters/cli` parses argv by hand with no CLI library.
3. `node --experimental-strip-types` with no build step.
4. `node:test` with no test framework.
5. The MCP adapter emits JSON Schema by hand rather than depending on the SDK's zod shapes.

These are frozen until that review runs. The hardening brief says so explicitly.
