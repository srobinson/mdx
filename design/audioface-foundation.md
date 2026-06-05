---
title: Audioface Foundation, Plugin and Pack Architecture
type: design
tags: [audioface, architecture, engine, plugins, game-audio]
summary: Three layer architecture for a procedural sound engine with domain plugins and stylistic packs
status: draft
project: audioface
---

# Audioface Foundation

Procedural sound engine. Zero audio files. Everything is synthesised at play time from addressed
parameters.

The product claim: a wav pack ships four takes per event so repeated fire does not machine gun.
Audioface ships a seed. Unlimited takes, zero bytes. Near and far are a parameter, not a second
recording.

## Three layers

```
pack      Studio Real, Toon Punch, Tropical Arcade      style
  |
plugin    game, interface, ui, ambience                 vocabulary
  |
foundation  parameters, synthesis, render, measure      physics
```

**Foundation** knows nothing about guns or buttons. Its vocabulary is sources, filters, envelopes,
routing and the addressed parameters that drive them. It renders and it measures.

**Plugin** declares a domain: an event vocabulary, the scenarios that exercise it, and the gates a
pack must pass to ship. `game` declares `gun-ar`, `reload-magout`, `step-dirt`, `hitmarker`.
`interface` declares press, release, success, error.

**Pack** maps every event its plugin declares to a patch, plus a pack level character. Studio Real
and Toon Punch are the same event list with different physics.

**Dependency arrow points one way only.** Pack imports plugin. Plugin imports foundation. Nothing
imports backwards. A pack is data, not code.

## Day one engine requirements

These do not retrofit. The engine is built for them from the first commit or it is rebuilt again
later.

**Polyphony.** Many voices at once through one master bus. The twenty simultaneous shooters case is
not a stress test bolted on afterwards, it is the normal case for a game. Voice allocation, voice
stealing, and a limiter that behaves under load.

**Stereo.** Pan and width per voice. The current engine is mono only and that gap has been carried
since Phase 1. A game engine without placement is not a game engine.

**Seeded variation.** Round robin without files. The same event fired ten times produces ten related
but distinct renders from one patch and a seed sequence. Determinism is required: the same seed
gives the same audio, or nothing can be measured.

**Distance.** Near and far are a render transform, not a volume knob. Different filtering, different
transient, different tail. An addressed parameter, applied at resolution.

**Scenarios.** A scripted multi event timeline, rendered offline as one signal. The eight second
firefight is how a pack is judged, because a pack that sounds fine one shot at a time can still be
exhausting in combat.

**Offline render of all of the above.** Anything that cannot be rendered offline cannot be gated.

## Measurement is a product surface, not a test detail

The pack certification layer ships. It is what prints PASS, the 2 to 5 kHz mean, and the stress
dBFS. A pack author needs it more than we do.

Per pack gates, declared by the plugin:

- Coverage. Every event the plugin declares has a patch.
- Spectral. Energy in a named band stays inside a named bound, so a pack cannot be harsh.
- Stress. Peak and loudness under the scenario at full polyphony stay inside a named bound.
- Distinctness. Sibling events do not collapse onto the same fingerprint.

## What we keep from the current codebase

Copied deliberately into a clean repository. Nothing else comes across, and no migration code is
written.

| What | Lines | Why |
| --- | --- | --- |
| Parameter registry, patch model, resolution, validation, schema, editing | 2377 | The domain model. Addressed parameters as data. Already proven. |
| Measurement: descriptors, render, golden master, runner | 792 | Becomes the pack certification layer. |
| `canonical-patches.ts` and `baseline.jsonl` | 649 + data | A reference recording, not legacy. Gives the new engine a gate on day one. |
| Persistence: loss aware hydration, quarantine, stores | 702 | Hard won, orthogonal to the rewrite. |

Everything else is dropped: root `src/`, the old studio, `AudiofaceTokenDefinition` and its
projector, the second resolver, the token and score subsystems, and effectively all of the existing
tests.

## Testing posture

Test the seams. Test internals only where they are fragile.

The seams are: patch to rendered audio, the pack gates, and persistence round trip. The golden
master already owns the first. Nothing else earns a test by default.

No tests of rendered markup. No tests asserting source text. No tests of a UI that is being
redesigned. No harness that tests the tests.

## Open

- Voice stealing policy when polyphony is exhausted.
- Whether distance is one parameter or a small group.
- Whether pack character is a parameter overlay or its own resolution stage.
- Repository name and location for the fresh tree.
