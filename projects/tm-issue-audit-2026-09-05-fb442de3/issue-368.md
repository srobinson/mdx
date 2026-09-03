# 368: Intercept: auto-passthrough aux turns (title generation) when a breakpoint is armed

URL: https://github.com/littleorgans/transport-matters/issues/368
State: open
Labels: 
Updated: 2026-08-08T06:53:49Z

## Problem

An armed breakpoint pauses every request on the flow, including harness machinery turns the user never composed. In live run `163c35b4` (claude 2.1.225, 2026-08-08) the title-generation turn paused under the armed breakpoint alongside the real user turn. The user's mental model of arming is "pause *my* message"; pausing aux turns is UX noise, and an edit made against an aux shape can be stored as a standing override that later applies to the wrong shape (observed: a positional `system:2` edit from the title shape clobbered the main turn's output-style part in the curated view, chars_delta -17574).

## Evidence (captured run 163c35b4)

- Title turn `8ef59528`: 715 input tokens, `max_tokens` small, `tools=0`, **zero `cache_control` breakpoints, zero cache creation/read** — the harness itself treats the shape as disposable machinery.
- Quota probe `90dd55dc`: `messages=[{user:"quota"}]`, `max_tokens=1` — same aux class.
- Main turn `4ebc9944`: the only turn the user actually composed.

## Direction (agreed 2026-08-08)

- Auto-passthrough aux turns at the **pause branch only** (`addon_handlers` breakpoint evaluation). The overlay/curation layer needs no special-casing: content-digest operations apply wherever preimages match.
- **Detection ships as data, not code**: aux-shape fingerprints belong in the managed overlay artifact (same fingerprint machinery as variant selection in the overlay registry spec), never hardcoded in intercept code — what a title turn looks like is harness-shape knowledge that churns with every release. Corroborating signals available in-shape: no cache breakpoints, tiny `max_tokens`, zero tools.
- Interim acceptable: a conservative built-in heuristic behind the same seam the fingerprint data will later own, provided the seam is the artifact-consuming one.

## Acceptance

- With a breakpoint armed, a title-generation turn and the quota probe cross the wire un-paused; the user-composed turn still pauses.
- Aux passthrough is visible in the exchange record (aux classification recorded), not silent.
- Pinning test derived from run `163c35b4`'s three captured shapes.

Refs: overlay registry spec (`~/.mdx/projects/transport-matters-spec-overlay-registry.md`) aux-turn ruling; positional-clobber repro same run.

## Sub issues
[]
