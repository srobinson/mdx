# Audioface: Fun First — Product and Design Vision Brainstorm

2026-07-18 · Angle: product and design vision · Source: read-only review of audioface repo (AUDIO.md, AUDIOFACE.md, PRODUCT_PROGRESSION.md, packages/core tokens/themes/token-library/sequence-editor, apps/studio token editor)

## Diagnosis: where the rigidity actually lives

The product currently enforces one aesthetic at three layers, and only one of them deserves to be an invariant.

1. **Physics clamps in the engine.** The resolver caps decay at 0.35s, variation at 0.18, attack at 40ms. The Studio token editor is tighter still: layer duration max 240ms, gain ceiling 0.22, delay max 160ms, pitch floor 40Hz. A slide whistle, a cartoon boing, a rising "level up" arpeggio, a wet splat: all structurally impossible. These are not safety limits. They are taste limits compiled into code.
2. **Vocabulary governance.** Locked catalog, ~20 profiled verbs, `category.action` regex, three-rule token admission ("verb discipline", "edge that matters", "sequence test"). Correct for the canonical catalog, wrong when projected onto users.
3. **The identity doc as law.** AUDIO.md says "crisp contact, short decay, low fatigue, silence unless an edge matters." That is a beautiful house style. The product treats it as the definition of correct sound.

The DDD framing makes the fix obvious: there are two bounded contexts here, the **canonical catalog** (Audioface's own curated voice) and the **user library** (the customer's voice). The catalog's invariants leaked into the user context. `token-library.ts` already draws the boundary correctly (`audioface:*` locked, `user:*` editable); the engine and editor just never honored it. The taste rules are catalog invariants, not domain invariants. The only true domain invariants are user-protective: gesture-gated playback, reachable mute, throttled continuous gestures, quiet default volume. Keep those. Everything else is an opinion, and opinions belong in themes and linters, not in clamps.

The one-line philosophy shift:

> Audioface stops being the arbiter of good sound and becomes the instrument that makes your app's sound coherent, whatever that sound is.

Figma does not stop ugly posters. It ships defaults, styles, and libraries that make good ones easy. That is the posture.

## Proposals, ranked by impact

### 1. Demote the house style from law to preset ("Audioface House")

The single highest-leverage change, and mostly a reframe rather than a rebuild.

- The current identity (crisp, short, polite, ceramic) becomes the default **sound personality**: a named profile bundling theme settings, parameter ranges, and lint rules. Users who want tasteful enterprise UI keep it and lose nothing.
- Engine clamps widen to physical and safety limits only (finite, positive, hearing-safe gain, sane scheduler bounds). Duration up to seconds, pitch down to 20Hz, real tails. The 0.22 gain ceiling becomes a House rule, not an engine rule.
- Ship contrasting personalities that prove range on day one: **Arcade** (chippy squares, rising arps), **Toy** (boings, squeaks, slide whistles), **Sci-fi** (sweeps, shimmer tails), **Brutalist** (dry clicks, buzzes), **Retro OS** (chimes). Each is a complete, coherent point in the space. The demo story flips from "listen how tasteful" to "listen how different these five apps feel."
- Creative ceiling test: if a user cannot make a sound that would make a designer wince, the ceiling is too low. The product's job is to make the wince-free path the easy one, not the only one.

### 2. Consistency as advisor, not gatekeeper (the taste linter)

The genuinely valuable thing Audioface knows is what makes a sound *system* coherent. Sell that as feedback, never as a wall.

- Repurpose `SoundFingerprint` and the sequence audition into a **Coherence Report**: loudness spread across the library, duration histogram, spectral centroid clustering, edge-collision detection in sequences, fatigue estimate for high-frequency tokens. "Your `error.honk` is 14dB louder than everything else" is useful. Refusing to save it is hostile.
- Lint severities come from the active personality profile. House flags a 900ms tail; Toy does not.
- Export always works. The report travels with the export (a "sound review" section in the generated AUDIO.md) so teams can hold their own line. This keeps the taste-and-consistency mission alive as tooling revenue ("sound design review as a feature") instead of as gatekeeping.

### 3. Open the synth: full layer editing and a bigger primitive set

The editor currently tunes four numbers on fixed layers. That is a mixer, not an instrument.

- User tokens get add/remove/reorder layers, change layer type, and per-layer envelopes. The layer recipe format already supports this shape; the editor just forbids it.
- Grow the primitive palette while staying true to the real invariant (procedural, zero audio files, no asset pipeline): pitch sweeps/chirps (boing, slide whistle, laser), pluck (Karplus-Strong), resonator/formant (squeak, quack, honk), LFO/vibrato (wobble, comedy), simple echo/spring tail, arpeggio/multi-note phrases for celebrations. "No audio files" is the identity worth defending; "no fun waveforms" never was.
- Keep the three macros (weight, brightness, tension) as the friendly layer on top; add per-personality macros (Toy exposes "bounce", Arcade exposes "bitcrush"). Macros are the gentle default; the full graph is the ceiling.

### 4. Make the studio itself fun: play before parameters

A sound tool earns "fun" through immediacy, surprise, and context, not through sliders.

- **Dice and breed.** "Surprise me" mutates a token within the active personality; "breed" interpolates two tokens. Cheap to build on the resolver, and the fastest route from blank canvas to happy accident.
- **Jam pad.** Map library tokens to keyboard keys, mash to play live, record the jam straight into a SequenceDraft. This turns the sequence surface from an audition rig into an instrument, and it is a genuinely differentiating demo.
- **Onomatopoeia search.** Type "boing", "thunk", "zap", "ka-ching" and get seeded starting tokens. Sound-designers think in onomatopoeia; the browser should speak it. Also the natural prompt surface for agent-generated tokens later.
- **Fake app playground.** A toy UI (buttons, toggles, modal, toast, drag list) wired to the active theme and bindings, so users feel their sounds at real interaction edges within seconds. This is the sequence test transformed from governance rule into toy.

### 5. Free the vocabulary in user space

- The `category.action` regex and verb governance stay for `audioface:*` and become conventions, not validation, for `user:*`. If someone ships `duck.quack`, the product's job is to play it well and export it cleanly.
- User-minted verbs get no ACTION_PROFILE gate; they get a sensible fallback profile plus an optional "map to nearest core verb" suggestion so theming still works. Governance protects the shared ubiquitous language; it should never police a customer's private one.
- Rename the mental model in the UI: not "catalog and copies" but **"references and your sound"**. The locked catalog is the specimen book of a type foundry: inspiring, stable, forkable, never a cage.

### 6. Keep, as gentle defaults, the rules that protect users

Explicitly not on the chopping block, but each becomes a default with a visible override rather than a silent law: gesture-gated playback (keep hard; it is a platform rule anyway), reachable global mute (keep hard), quiet default volume, hover silence by default, throttled continuous gestures, short-tail defaults in the House personality. The distinction that decides every future debate: **rules that protect the end user's ears stay; rules that protect Audioface's brand from its customers' taste go.**

## The strongest single idea

Split the bounded contexts for real: the engine becomes a permissive instrument with only physical and safety invariants, and everything Audioface currently enforces (short decays, gain ceilings, verb discipline, house materials) is repackaged as the default **personality profile plus a taste linter**. Rigidity becomes the flagship preset. Freedom becomes the product.
