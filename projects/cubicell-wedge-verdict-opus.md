# Cubicell wedge verdict: creator lens

Independent review, 2026-08-07. Lens: the working musician or VJ as the user.
Evidence: both project docs, `main` at 7d5e942 read directly, `feat/stencil-build` at 66b4d8d read through `git show` only. Every claim below is anchored to a file or a doc section.

## Scenario: one release, end to end

**The track.** "Ferrous", 128 BPM industrial techno, 6:12, four to the floor, 16 bar phrases, one breakdown at 3:30. Label EP, artist needs a Spotify Canvas loop, an Instagram reel, a YouTube full visual, an announce reveal, and a backdrop for a 90 minute club set.

I picked the most favourable possible genre. A strict grid instrument in black and white is closer to techno than to anything else, so friction found here is a floor on the friction every other genre meets.

**Minute 0 to 5, first open.** The default scene is a single cube (`src/config/cubicellConfig.ts:29`, dimensions 1,1,1) in an untitled unsaved scratch (STUDIO.PROJECT.md, "Editor: the State lifecycle"). Build with `b`, place neighbours, orbit on the numpad, `f` to focus, `0` to reset (`src/editor/keyboard/keymap.ts`).
**Delight.** Nothing to configure, and the travel commands (`view.travel.*`, shift plus arrows) give the Powers of Ten dive immediately. No other tool a musician can reach does this.

**Minute 5 to 40, look development.** Four colour roles per face and per edge, theme, black, white and accent (`src/domain/cubeEdgeState.ts:6`), face and edge opacity, edge thickness, grid gaps, cube dimensions and offsets, projection toggle on `p`.
**Delight.** Orthographic plus polarity is a poster machine, and it arrives in the first hour.
**Friction 1.** No artwork or logo can enter the product. On `main` a face carries no content at all. On the unmerged stencil branch the atlas is built from `seededStencils`, a compile time array of exactly two SVGs, Helioy and Manicure (`git show 66b4d8d:src/domain/seededStencils.ts`), and `getStencilAtlasSlot` returns null for anything else (`git show 66b4d8d:src/scene/stencilAtlas.ts`). The artist's mark and the track title cannot be authored, only compiled.

**Minute 40 to 90, first states.** Snapshot state 1, new from selected, diverge, snapshot again (`src/panels/stateCapture.ts`).
**Delight.** Capture and diverge is fast, and the modified indicator is honest about scratch.
**Friction 2.** The piece is one Structure asset's flat keyframe list, with transitions one to one against adjacent pairs (`src/domain/score.ts`, `StateTransitionTrack`). There is no section, repeat, or reusable phrase in the score model. A 16 bar figure that recurs four times in the arrangement is authored four times.

**Minute 90 onward, timing to the track.** Duration ms per transition in the morph inspector, `min={100}`, `max={8000}`, rounded to integers (`src/panels/motion/MorphInspector.tsx:115-123`). At 128 BPM a bar is exactly 1875 ms, so bar aligned phrases land on integers and the rounding is harmless. At 140 BPM a bar is 1714.28 ms and it is not. The favourable genre is favourable even in the arithmetic.
**Friction 3.** The artist cannot hear the track inside Cubicell. There is no audio anywhere in `src`, no BPM field, no waveform, no beat grid, no MIDI. Timing is arithmetic performed against a DAW playing in another window, and every arrangement edit invalidates it downstream.
**Friction 4, decisive for this genre.** The hard cut on the beat cannot be authored. Duration is floored at 100 ms in the inspector. `TransitionMode` is `"auto" | "cut"` and `src/domain/score.ts:56-60` states plainly that the cut path is working and tested, that it swaps the whole scene at `cutAt * durationMs`, and that the inspector never authors `mode`. Separately, `compilePieceCameraTrack` already compiles a zero duration window into a hard camera cut (`src/domain/pieceCameraTrack.ts`, boundary semantics). Everything required for beat cuts is built, tested and unreachable from the UI. This is the first moment a techno artist concludes the tool does not do their music.

**Hour 3 to 6, the full visual.** 6:12 is 372,000 ms. At four bar phrases (7500 ms) that is roughly 49 transitions and 50 captured states, each with its own morph settings and optionally a captured camera view, with no repeat construct to amortise them.
**Abandonment point 1.** Most working artists stop here and ship the loop instead. The ones who continue are proving a point rather than making a release asset.

**Camera.** Each state may carry one captured view, and playback interpolates between consecutive states' views (`src/domain/pieceCameraTrack.ts`, the KISS model).
**Delight.** Camera authoring is free, riding states that already exist.
**Friction 5.** Camera timing is welded to morph timing, and per segment pose paths compile inert rather than authored. Stage camera work and multi piece composition belong to the Animation Studio (STUDIO.PROJECT.md, "Editor preview and piece motion"), and `src/studios/catalogData.ts` contains exactly two studios, editor and design system. That studio does not exist.

**Output.** `shift+tab` hides panels (`editorCommandIds.panelsToggle`, `panelsHidden` in `src/state/cubicellState.ts:228`), transport loops with a loop window (`src/transport/advanceTransportTime.ts`), `r` toggles capture. The recorder takes `canvas.captureStream(60)`, encodes VP9 webm at 12 Mbps with `audio: false`, and downloads on stop (`src/export/streamRecorder.ts`).
**Friction 6.** Resolution is whatever the canvas is, viewport CSS size times `dpr`. There is no aspect or resolution control anywhere, so vertical means resizing the browser window and 1080 by 1920 is a guess.
**Friction 7.** Retention is capped at 256 MiB and the recorder auto stops and downloads when the next chunk would exceed it. At the configured 12 Mbps that bound arrives near 179 seconds of capture. A sparse black and white scene encodes under target and runs longer, so this is a size bound rather than a clock, but the 6:12 take is not a safe single capture.
**Friction 8.** The only file the product emits is a webm. No still export, no poster, no project export. Cover variants and press images come from screenshots.

**Publishing.** Every deliverable enters another editor to marry audio, crop vertical, and encode H.264. Canvas wants a 3 to 8 second vertical loop, so the loop is the one output that survives this pass almost untouched.
**Abandonment point 2.** If the finished visual drifts against the track because timing was arithmetic, the re-time loop has no shortcut and no audio reference. That is where the artist leaves and does not return.

**Where the scenario lands.** The loop and the reveal come out excellent and fast. The vertical clip falls out of them. The 6 minute visual is a grind that most would abandon. The live scene is camera improvisation over a looping piece with the panels hidden, which is real and thin.

*Flip condition.* If a hands on run of this scenario produces a publishable loop and reveal inside one session, friction 4 and 7 drop to cosmetic and the scenario supports "right call" outright. If the reveal cannot be made at all because no mark can enter, the scenario supports blocking the campaign until ingestion lands.

## The five outputs ranked by identity weight

1. **Title and brand reveal.** Highest. The only output where a cube lattice is categorically better than what a musician can otherwise buy: assembly order across creation, sweep, radial, shell, spiral and random (`src/domain/assemblyOrder.ts:11-17`), cadence curves across linear, accelerando, ritardando and swing (`src/domain/score.ts:8`), and a camera settling onto a wordmark. It is short, it is the announce asset, and it is what a label reposts. Entirely gated on stencil ingestion.
2. **Seamless loop.** Second, and the highest ratio of identity to effort. Repetition is where a visual language becomes legible, the length fits both the retention cap and the authoring cost, `loopWindow` already supports authoring it, and it is the format the AI music market actually consumes.
3. **Live scene.** Third on identity, last on readiness. When it works it is the purest evidence that this is an instrument rather than a renderer. Today the performable vocabulary is play or pause, wheel scrub, the camera commands, and hidden panels. There is no state jump, cue trigger, blackout or crossfade anywhere in `editorCommandIds`, and no audio or MIDI.
4. **Full music visual.** Fourth. Highest cost per minute of output, lowest identity yield per hour, and the format most exposed to the missing audio clock. It measures endurance rather than identity.
5. **Vertical clip.** Last. A crop of one and two rather than an authored artefact. A real deliverable carrying no identity information of its own.

The direction doc lists the five as equal derivations of one project (`## Product home`). They are not equal. Two carry the identity, one is a crop of those two, one is a grind, and one cannot be produced today.

*Flip condition.* If the campaign's first piece shows the full visual reading as a sustained work rather than 50 stitched phrases, its rank rises above the live scene and the ordering above is wrong.

## Where the freeze bites first

The freeze is right in kind. Extrusion, SDF relief, rounded cubes, a text primitive and multi atlas pages block nothing in this scenario, and the synthesis doc's ladder correctly refuses to climb without a visual answer.

It is wrong in one specific. **General SVG import is not speculative capability, it is the campaign's own input path.** Freezing it means the wedge's two highest identity outputs are gated on a rebuild per asset revision. "Concierge inputs" (direction doc, `## Scope discipline`) reads as hand prepared files; the code makes it a developer build per title card. Three tracks becomes three compiles, and the title iteration loop runs in builds instead of seconds.

**Audio is second and correctly frozen in scope, wrongly frozen in framing.** Nobody needs FFT reactivity for this campaign. What is missing is a clock: hearing the track while authoring, and a tempo aware duration field. That is far below "speculative audio analysis" on the frozen list and it is the difference between arithmetic and authorship.

**The cheapest unfreeze is not on the list at all.** Exposing `mode` as a two value control in the morph inspector surfaces a transition path that `src/domain/score.ts` documents as already working and tested. No new state, no new owner, no new render path. For a music wedge, the beat cut is the highest value single control in the product and it already exists.

Runtime stencil ingestion is the second cheapest and introduces no new concept either: `StencilAsset` with its source already persists through `stencilRecordCodec`, and the recorded merge blocker (direction doc, `## Current repository status`) is precisely that the Library path is half wired. The atlas has 16 slots and uses 2.

*Flip condition.* If the first piece is authored end to end with only the two seeded marks and the owner judges the results publishable, the ingestion argument collapses and the freeze stands as written.

## Does constraint read as authorship or sameness

The vocabulary is genuinely wide: four colour roles with polarity, lattice density and gaps, cube dimensions and offsets, six order modes with six sweep variants, four morph forms across grow, slide, drop and turn (`src/domain/morphSettings.ts:15`), four easings including an overshooting settle, stagger, quantize steps, projection, and per state camera. Three tracks will differ in structure and rhythm, and that difference will be real.

They will also all be cubes on a dark ground. Signature reads as sameness to a viewer who did not author the differences, so campaign question 1 graded by the person who made all three is the least trustworthy of the five. Show the three finished pieces to someone who has never seen Cubicell before answering it, or the answer is worth nothing.

Questions 2 and 3 are the trustworthy signals, because neither can be flattered by the author: was the third piece faster than the first, and was it more boring. Question 3 as written is unanswerable by this campaign at all. Stuart is not the creator, and the pipeline he will use (a rebuild for every mark, millisecond arithmetic for sync, an external composite for audio) is not the pipeline any creator would have. Grade it as author velocity and accept that creator velocity stays untested until ingestion and a clock exist.

*Flip condition.* Three pieces that an outside viewer describes as three different artists' work would make the constraint argument settled and the wedge unambiguously right. Three that read to that viewer as one house style would not condemn the wedge, but it would relocate the product from identity engine to house style for hire, which is a different business.

## Would a working artist return

Return depends only on piece two costing materially less than piece one: template the project, swap the mark, swap the title, retime to the new tempo. Projects, the structure library and state reuse make that structurally available (STUDIO.PROJECT.md, "Persistence"), and IndexedDB durability is real rather than aspirational (`src/persistence/indexedDbProjectStorage.ts`).

Two things block it today. With build time stencils, piece two costs a build, and no working artist returns to a tool that requires a developer for a title change. With no tempo in the model, a retime to a different BPM is a manual pass over every transition, so the template saves the look and none of the timing.

*Flip condition.* Piece three authored in under half the wall time of piece one, with the mark and tempo as the only real edits, proves return and settles the wedge. Piece three costing the same as piece one means the engine has depth but no leverage, and the product is a service.

## Summary of position

The wedge is correct and the discipline is correct. Music visual identity is the right first market, output before capability is the right sequencing, and the five outputs derived from one project is the right shape for the deliverable. The stop rules in the synthesis doc are the best written part of either document.

Three corrections stand between this plan and a campaign that can answer its own questions: the beat cut must be exposed because it already exists, marks must be able to enter at runtime because they are the campaign's own input, and the live VJ scene must leave the required five until a performance surface exists. Without the first two, the campaign measures Stuart's patience rather than the engine's depth.

## Cross-examination

**A. Pre-committed external pass criteria. Adopt, with one rebuttal.** Numeric is right wherever a clock or a count applies: wall hours per piece, rebuilds per piece, re-time passes per arrangement edit. It is wrong for question 1. "Do three tracks produce three identities" has no honest number, and forcing one invites a score the author calibrates after seeing the work. The correct external instrument there is a blind description task: show the three finished pieces to a viewer who has never seen Cubicell and ask what each is for. Pre-commitment matters more than the metric, because every finding in my scenario is one an invested author can explain away afterwards.

**B. Engine validation only, no product-home claim. Adopt, on evidence rather than on market opinion.** Whether music beats brand motion systems is outside my lens. What is inside it: this campaign cannot support a product-home claim whatever it returns, because the pipeline Stuart will run (a rebuild per mark, arithmetic sync, an external composite) is not a pipeline any creator has. There is also a discrimination problem. My highest ranked output, the title reveal, is market agnostic; a wordmark assembling from a lattice is the same asset for a techno EP and for a software brand. Success on the strongest output is therefore evidence for both markets and distinguishes neither.

**C vs C'. Resolve for C, scoped.** C' has a real defence: two seeded marks are enough to test the choreography of face content, and the campaign asks whether pieces differ rather than whose logo appears. It fails on the campaign's own terms. The direction doc lists artist and track name among the recurring inputs (`## Product home`), so under C' the title reveal, the highest identity output of the five, is not testable for three real tracks, and question 5 is unanswerable because piece two costs a build. C' is coherent only if the required five also drops the reveal, which removes the best evidence the campaign could produce. Adopt C narrowly: runtime ingestion into the existing `StencilAsset` and `stencilId` path only. Not layers, fills, live font layout, or a second content primitive. So scoped it violates no stop rule in the synthesis doc, including stop rule 2.

**D vs D'. Resolve for D', reversing my own earlier position.** I recommended dropping the live scene. My own evidence contradicts that. `panelsHidden` (`src/state/cubicellState.ts:228`) gives a chrome free canvas, `loopWindow` sustains an indefinite loop, and the camera command set with wheel scrub is a real live vocabulary. A prepared scene performed by camera over a looping piece is producible today, costs nothing beyond the piece already authored, and is a cheap honest test of the instrument claim. Keep it, defined exactly as that, with the constraint stated up front: no cue triggering, no state jump, no audio, no MIDI, none of which exist in `editorCommandIds`. Grade it on whether camera alone sustains attention, never as a VJ suite.

**E. Expose the cut before piece one. Adopt, and sequence it first.** `TransitionPatch` already carries `mode` (`src/domain/stateTransition.ts:22-25`), the evaluator already honours it, and `src/domain/score.ts:56-60` records it as working and tested with the inspector as the only gap. One segmented field on an existing patch path. For a music wedge this is the highest value control in the product and the cheapest item on this list.

**F. Land the persistence repair. Adopt, as one change with C.** F is the persistence half of C. Landing F alone inserts the asset into the library while `stencilAtlas.ts` stays compile time bound, which repairs the record and not the workflow. Splitting them produces two passes over one seam.

**G. Audio and delivery external. Adopt for delivery, rebut in part for audio.** Delivery tooling is genuinely external and no argument survives against it. Audio is being frozen under the wrong name. Nothing in my scenario needed analysis or reactivity; what was missing was a clock, meaning hearing the track while authoring and a tempo aware duration field. Freeze it as written for piece one, and use A's own machinery: pre-commit a re-time threshold, measure the wall time spent retiming against the track, and unfreeze a project BPM that snaps Duration ms to bar and beat multiples for pieces two and three if the threshold is exceeded. Contingent and measured rather than speculative.

**FINAL condition set: A (external, numeric only where a clock or count applies; blind description for question 1), B, C (scoped to the existing stencilId and atlas path), D' (prepared camera-only scene, explicitly not a VJ suite), E (first), F (landed as one change with C), G (delivery external throughout; tempo field unfrozen only on a pre-committed measured trigger).**

verdict: conditional — right wedge and right freeze in principle, proceed on A, B, C-scoped, D', E, F and G-with-trigger, with E first because the beat cut is already built and tested and only the inspector is missing, and C and F landed as one change because they are two halves of the same seam.
