# Cubicell wedge verdict (Fable, product-strategy lens, reworked, extended)

Date: 2026-08-07. Inputs read in full: `cubicell-music-visual-identity-direction.md` (direction doc), `cubicell-svg-3d-synthesis.md` (synthesis), repo main `7d5e942`, branch `feat/stencil-build` at `66b4d8d` inspected via `git show` only (worktree dirty with paused Shell E changes, untouched).

## Method

Claims below carry one of three anchor types: a doc section heading, a `file:symbol` reference verified in the working tree at main `7d5e942`, or a sha-backed fact from `git show 66b4d8d`. Where I could not verify, I say so and lower confidence.

## What the evidence confirms, by section

**"Validated capability" (direction doc) — confirmed, high confidence.** `git show 66b4d8d --stat` shows the face render path landing with its guards in the same commit: `src/scene/faceStencilShader.ts` (108 lines), `src/scene/stencilAtlas.ts` (143 lines), plus `tests/faceStencilRender.test.ts` (189 lines), `tests/stencilRendering.browser.test.ts`, `tests/stencilOrientation.test.ts`, and WebGL resource observation (`tests/webGlResourceObserver.ts`, +73 lines). That is consistent with the doc's claim of unit, Chromium, and GPU-evidence gates. I did not re-run the gates; the doc's "owner testing concluded substantial creative potential" is testimony I cannot independently verify, but the engineering substance behind it is real.

**"Typography correction" and synthesis "Stop rules" 1–4 — confirmed in code, high confidence.** One figure owner: `CubeFaceFigure` exported from `src/domain/index.ts:29` with its validation and tween helpers (`canTweenCubeFaceFigureColor`, `cubeFaceFigureRegions`) beside it. One content identity: `stencilId` resolved through `resolveStencilContent` (`src/domain/seededStencils.ts:51`). One plane renderer: `faceStencilShader.ts`. No live text or second text primitive exists anywhere in `src/`. The synthesis's "hard current model boundary" (one face plane, one alpha sample, two colour roles) matches the shipped shader and atlas design.

**"Scope discipline" does not starve the campaign — confirmed, high confidence.** The delivery substrate predates the freeze on main: piece evaluation (`src/evaluation/pieceAt.ts:PieceFrame`, `scoreAt.ts:Moment`, `cameraTrackSampleAt.ts`), an authored score model (`src/domain/score.ts:Score`, `PieceScore`, `ScoreTrack` = piece tracks plus camera track), a recorder (`src/export/streamRecorder.ts:createRecordingController`), and IndexedDB project persistence (`src/persistence/indexedDbProjectStorage.ts`). Every campaign deliverable except two format gaps (next section) is reachable with committed capability.

**"Current repository status" persistence finding — mechanically confirmed, high confidence.** `resolveStencilContent` resolves only through the bundled `seededStencilsById` map and returns `{kind:"unresolved"}` otherwise (`seededStencils.ts:51-53`); nothing in the resolution path writes to the project Library. The doc's ordering (repair before merge, not before visual testing) is correct: the bug affects persistence integrity, not what the owner sees on screen.

**The Shell E pause — confirmed as the freeze working, medium confidence.** The direction doc says it was paused for repeating validated capability rather than advancing product-home validation. The uncommitted worktree contents (`assets/marks/shell-e.svg`, rebaselines) match that description, though I did not inspect the diff in depth per the no-touch instruction.

## What I contradict or qualify, by section

**"Product home" deliverables list — qualified, high confidence.** The only export path records silent, landscape-orientation-agnostic webm: `audio: false` hardcoded in the capture constraints (`streamRecorder.ts:19`), container limited to `video/webm;codecs=vp9` / `video/webm` (`recorderMimeTypes`, `streamRecorder.ts:10`), fixed 60fps at 12Mbps (`src/export/recordingConfig.ts:RECORDING_FRAME_RATE`, `RECORDING_VIDEO_BITS_PER_SECOND`). Two of the six recurring outputs therefore need work outside the engine from piece one: the "full music visual" needs external audio muxing, and the "vertical social clip" needs aspect handling plus likely an mp4 transcode, since webm upload support on vertical-first platforms is inconsistent. This does not break the freeze — "productise only workflow breaks that repeat across real pieces" already covers it, and ffmpeg-on-the-side is a fine concierge answer — but the direction doc should name both as known breaks now rather than discover them mid-campaign. A silent-video engine making music visuals via hand-muxing is exactly the kind of friction Q3's hour budget must include, not exclude.

**"Validation campaign" — contradicted on falsifiability, high confidence; this is the core objection.** The section states a failure condition ("If every result converges on the same Cubicell demonstration, the gimmick diagnosis is confirmed") but names no judge, no threshold, and no protocol. All five questions are graded by the owner, who is simultaneously the builder, the pieces' author, and the person whose year this decision shapes. Prose criteria plus a motivated judge means every question can be argued to pass after the fact. The campaign as written can succeed but cannot visibly fail, which makes it a demonstration, not a test.

**"Scope discipline" freeze list — qualified on one item, medium confidence.** "General SVG import" is frozen, yet each of the three tracks needs its artist mark and wordmark arriving as outlined SVG paths ("Typography correction"). Today's only ingestion is code-seeded: the `seededStencils` array literal (`seededStencils.ts:18`) with two entries (`helioyStencilId`, `manicureStencilId`). Hand-adding per-track entries to that array is concierge seeding through the existing resolver and atlas, consistent with the synthesis's stop rule 2 ("one content identity"). The doc should state this carve-out explicitly, because an agent applying the freeze literally would refuse the campaign's own inputs. Nothing else on the freeze list touches the campaign path: audio analysis, live typography, extrusion, SDF relief, multi-atlas, new shapes, and the VJ suite are all genuinely speculative relative to the six deliverables.

## The five decisive questions, one at a time

**Q1. Do three tracks produce three genuinely different visual identities?**
As written: judged by the person who authored all three, with "genuinely different" undefined. Convergence is easy to rationalise as intentional house style.
Proposed criterion: blind panel of at least 10 uninvolved viewers recruited outside Helioy (X followers, a producer or VJ Discord). Two tasks: (a) match each visual to its track given only name, genre, and three mood words — pass at ≥70% correct matches against a 33% chance baseline; (b) asked "same piece re-skinned, or three different works?" — pass if ≤3 of 10 say re-skinned.
External judge: the panel. The owner's role ends at submitting the pieces.
Confidence in this criterion: high. It is cheap, fast, and directly operationalises the doc's own gimmick-vs-instrument dichotomy.

**Q2. Does Cubicell remain enjoyable and surprising on the third piece?**
As written: a retrospective feeling, maximally vulnerable to sunk-cost grading.
Proposed criterion: a same-day session log per working session, written before any review or discussion, recording one engagement score (1–5) and any unplanned discoveries. Pass: the piece-3 logs record at least one unplanned discovery that was adopted into the final piece, and the engagement score has not declined monotonically across pieces 1→3.
External judge: none available — this question is intrinsically first-person. The pre-committed instrument (log before review, no retro-editing) is the honesty mechanism. A second-best check: the panel from Q1 ranks piece 3 no worse than the median.
Confidence: medium. Self-report is unavoidable here; the instrument reduces but cannot eliminate motivated grading.

**Q3. Can a creator reach publishable output quickly?**
As written: "quickly" is unquantified, so any duration passes.
Proposed criterion: wall-clock hours per piece, logged per session, including concierge steps (SVG prep, audio mux, transcode) so the true cost of the silent-webm gap is measured rather than hidden. Pass: piece 1 completes inside 40 hours, and piece 3 inside 60% of piece 1's hours at equal or better Q1 panel distinctness. Falling wall-time with non-falling distinctness is the signature of an instrument rather than a demo.
External judge: the clock. The 40-hour anchor is my estimate of what a solo motion designer would spend on a bespoke piece; the owner may re-anchor it before piece one, but must commit the number before piece one.
Confidence: high on the mechanism, medium on the specific 40-hour figure.

**Q4. Does the constraint produce authorship or repetition?**
As written: this restates Q1 subjectively and adds no independent signal.
Proposed criterion: make it structural. Piece state is persisted structured data (`src/domain/score.ts:Score` with `ScoreTrack`s, project records in `src/persistence/indexedDbProjectStorage.ts`), so authored-state overlap is computable. Pass: no pair of pieces shares more than 30% of authored scene, choreography, and palette state (excluding engine defaults), and the Q1 panel majority reads them as "different works". The 30% line is a pre-commitment, not a law; its job is to exist before the pieces do.
External judge: the state diff (mechanical) plus the Q1 panel. This folds Q4 into Q1's protocol with one added objective measurement instead of a second opinion.
Confidence: medium-high. The diff needs a small script and a decision on what counts as "authored", which must also be fixed before piece one.

**Q5. Would a creator return for the next release?**
As written: unanswerable — the only creator in the campaign is the owner, and the owner asking whether the owner would return is not a test.
Proposed criterion: pass only on external behaviour: one musician or VJ outside Helioy uses a concierge-produced piece for a real release or live set and requests a second piece. If no external creator engages during the campaign window, record Q5 as explicitly deferred to the next stage rather than self-scored — a deferral is honest; a self-score is noise.
External judge: the creator's behaviour (a request for a second piece), not their sentiment or politeness.
Confidence: high that the rescope is necessary; medium that an external creator can be engaged inside this campaign's window.

## The question the campaign does not ask

The five questions all test supply: can the engine produce distinct, fast, enjoyable output. None test demand: whether any musician chooses this over a generic visualiser, a template pack, or nothing. The direction doc's market claim ("AI-assisted music increases the number of tracks... without a corresponding supply of coherent visual identity", section "Product home") is plausible and completely untested by this campaign. That is acceptable for a stage-gate — supply-side failure would make demand moot — but the doc should state it, so a supply-side pass is not misread as market validation. Q5's rescope above is the earliest demand signal available.

## Confidence summary

Wedge choice (music visual identity over other wedges): medium-high — it exercises every engine strength the synthesis catalogues (polarity, camera, choreography, face content) and has a recurring buyer-shaped input/output loop; I cannot verify the market claim.
Freeze list scope: high — verified against the deliverables path in code; one carve-out (concierge SVG seeding) and two named format gaps (audio mux, vertical/mp4) needed.
Campaign-as-written falsifiability: high confidence it is inadequate; that is the conditional.
Proposed criteria: high for Q1/Q3 mechanisms, medium for Q2/Q4 parameters, high for Q5's rescope.

## The single piece of evidence that would flip this verdict

To "right call" unconditionally: the owner commits the pass/fail sheet (Q1 panel protocol, Q3 hour budget, Q4 overlap line, Q5 deferral rule) in writing before piece one begins. The condition is procedural, so meeting it dissolves it.
To "wrong call": the Q1 blind panel failing on the *first two* pieces — outsiders reading them as one demonstration re-skinned despite materially different tracks. That would confirm the gimmick diagnosis early, and no amount of piece-3 polish should override two-for-two convergence from external eyes. Nothing I found in the code or docs predicts that outcome, but the campaign only means something because it is possible.

## Cross-examination

Adjudicating the unattributed union of conditions from the four reviews.

**A (pre-commit external numeric criteria) — adopt.** This is my core condition; criteria and judges are specified per question above.

**B (engine validation only, no product-home claim on success) — adopt.** It matches my "missing question" section: the campaign tests supply, and the "Product home" market claim (AI-music volume without visual identity supply) stays untested even on a full pass. A pass earns "workable wedge", not "durable market versus brand motion systems".

**C (unfreeze runtime stencil ingestion) versus C' (keep frozen, concierge seeding) — adopt C', rebut C.** "Half built" overstates the evidence: the persistence substrate exists (`StencilAsset` with content-addressed `StencilId = sha256:...`, `git show 66b4d8d:src/domain/stencil.ts:3,17`; library hydration codecs in `04f12b2`), but no import UI, file picker, or upload path exists anywhere at `66b4d8d`. The campaign needs roughly three to six marks; hand-seeding the `seededStencils` array (`seededStencils.ts:18`) costs minutes per mark, and content-addressed IDs make seeded assets portable, not throwaway. If seeding hurts three times, that is precisely the repeated workflow break the doc's own productisation clause then licenses. Building ingestion UI first is capability work before evidence — the exact pattern the freeze exists to stop.

**D (drop live VJ scene) versus D' (keep, narrowly defined) — adopt D', rebut D.** The doc already separates the deliverable from the suite: "Scope discipline" freezes "a full VJ suite" while "Product home" lists the scene and calls VJ "the purest expression of the engine". A prepared, loopable, performable project through the existing studio surface (`src/studios/StudioHost.tsx`; `RecordingSource = "canvas" | "studio"`, `streamRecorder.ts:56`) needs no new performance surface. Dropping it would remove the purest-expression claim from the test and weaken the "consistent identity across formats" deliverable that Q1 rests on.

**E (expose the cut transition before piece one) — adopt.** The anchor is unambiguous: `src/domain/score.ts:56-61` states 'cut' is "a working, tested transition capability" that "has no Editor control today; the inspector never authors `mode`", while `MorphInspector.tsx:129-131` already authors `cutAt`. Cutting on the beat is the most basic music-video gesture; withholding a committed, tested capability from the instrument risks a false negative on Q1 and Q2 — the campaign would be testing a handicapped engine, not the engine. Exposing one authored field in an existing inspector is not speculative capability work.

**F (land the persistence repair first) — adopt.** This is the direction doc's own pre-merge requirement ("Current repository status": repaired before merge and persistence approval); adopting it here only fixes sequencing so campaign pieces sit on repaired persistence. Mechanically confirmed above (`resolveStencilContent`, `seededStencils.ts:51-53`).

**G (audio analysis and delivery tooling stay external all campaign) — adopt.** Consistent with the freeze list and with the recorder evidence (`audio: false`, `streamRecorder.ts:19`; webm-only, fixed 60fps/12Mbps). One rider from Q3: external-step hours count inside the piece budget, so the concierge cost stays measured.

**Final condition set: A, B, C', D', E, F, G.**

verdict: conditional — right wedge and right freeze, but pre-commit external and numeric pass criteria before piece one or the campaign cannot visibly fail.
