---
title: 3dsvg review takeaways for Cubicell
type: projects
tags:
  - 3dsvg
  - cubicell
  - review
  - export
  - capture
  - takeaways
summary: Fifteen takeaways synthesised from three independent reviews of 3dsvg, grouped into what to build, what to guard against, and what to notice.
status: active
project: cubicell
confidence: high
created: 2026-08-22
updated: 2026-08-22
---

# 3dsvg review takeaways

Synthesis of three independent reviews of `/Users/alphab/Dev/LLM/DEV/3dsvg` at
`424b26e`, compared against Cubicell at `bd43225`. Reviewers ran on three model
families with separate lenses and did not coordinate.

Source reports:

- `3dsvg-review-product.md` — product framing, IA, distribution, head to head
- `3dsvg-review-engine.md` — engine architecture, prop contract, renderer boundary
- `3dsvg-review-ui.md` — live drive of https://3dsvg.design, 54 controls, 40 screenshots

Framing: these are ideas to learn from. No 3dsvg code is copied, vendored, or
attributed. The "where it lands" references exist to test whether an idea is real
in Cubicell's own idiom.

Scale, because it reframes everything below: 3dsvg is 7,581 lines across 42 files,
Cubicell is 62,943. One screen with one object, against a studio. The comparison is
only honest on capture, first run, and delivery.

## Build

1. Make capture an aimed act on the canvas rather than a keypress with a byte
   readout, because the shutter is what tells a user the frame is the output.
2. Add a viewfinder that letterboxes the canvas to the target aspect while
   composing, which answers the aspect policy question `EXPORT.md` left open by
   making the user reframe instead of picking a rule.
3. Ship "record exactly N passes, auto stop" driven off the authored score
   duration, where Cubicell is strictly better positioned than 3dsvg because it
   knows the length rather than inferring it from a sine period.
4. Preview cheap and commit expensive: a low resolution still preview on shutter,
   full render only on download, which is what makes a resolution independent
   exporter feel instant instead of feeling like a render queue.
5. When the export picker lands, present two recommended formats with plain
   language "use this when" copy and fold the other thirteen behind a disclosure,
   because `EXPORT.md`'s honest fifteen row table would be a hostile UI.
6. Seed the first run with a score that plays, since Cubicell currently opens on
   one cube with a detached transport and nothing for Play to advance through.

## Guard

7. Keep one defaults table and one serializer shared by editor and player, with a
   parity test, because 3dsvg's two tables silently break its own headline claim
   in at least five props.
8. Never let a recorder hold its own copy of timing the score already owns, which
   is the specific bug behind 3dsvg's loop length.
9. Resolve asset identity before any snapshot references it, because 3dsvg writes
   blob URLs and multi hundred KB base64 into code users copy.
10. Treat every reachable idea in the material and lighting system as blocked by
    the unlit renderer, confirmed live where chrome rendered brown and glass
    rendered opaque.
11. Reject idle animation and cursor follow outright, since both write pose
    outside `CameraAuthority` and would fight track possession during Play.
12. Do not regress to native dropdowns for choices that have a look, which is
    exactly where 3dsvg's shipped panel contradicts its own `DESIGN.md`.

## Notice

13. A fully written, never imported module and a 25KB spec the code contradicts in
    three places is what doc drift looks like from outside, and Cubicell's docs are
    larger and more load bearing with `PROJECT.EXPORT.md` still reading `Proposed`.
14. The strongest lesson from 3dsvg is negative: its mixed prop bag is the
    counterexample that argues for `EXPORT.md`'s immutable snapshot rather than a
    template for it.
15. The two products barely overlap, so the comparison is only honest on capture,
    first run, and delivery, and everywhere else 3dsvg is the smaller idea.

## Convergence notes

Items 1 and 2 were ranked first independently by the UI and product lenses, which
arrived at them from opposite directions. Item 3 was ranked first by product and
third by UI. Item 7 was found independently by all three lenses through three
different symptoms: light position `[2,2,4]` against `[5,8,5]`, dropped `scrollZoom`
and `repeatY`, and smoothness `0.6` against `0.2`.

The rejections were more unanimous than the recommendations, which is the healthier
signal.
