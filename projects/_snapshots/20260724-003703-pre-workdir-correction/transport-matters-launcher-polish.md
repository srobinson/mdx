---
title: ⌘K Launcher — Post-Merge Visual Polish Punch-List
type: spec
tags: [transport-matters, launcher, cmd-k, visual-polish, post-merge, fidelity]
summary: Fidelity gaps between the approved Raycast-minimal mockups and the merged build (PR #144). Fine-tune post-merge.
status: active
source: orchestrator
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

# ⌘K Launcher — Post-Merge Visual Polish

PR #144 merged the functionally-correct, dual-clean, gate-green slice. Stuart's call: merge now,
fine-tune visuals post-merge. The build diverged from the approved mockups
(`TMP/launcher-mockups/01-raycast-minimal.html` + the brainstorm wireframes). Gaps, from a
mockup(#4/#5)-vs-build(#6) diff:

1. **Icons — missing entirely.** Mockup has per-domain icons in root (Agents=person, Canvas,
   Workdir=sliders, Settings=sun, Sessions=clock) and per-agent icons in the Agents scope. Build
   has none. Add an icon system (reuse existing canvas iconography if present).
2. **Native row treatment.** Build renders separate "Claude Native" / "Codex Native" rows (one per
   CAPTURED_RUN_PROVIDERS). Mockup is a SINGLE "Native — ALWAYS ON" row with a green "● live ·
   default home". Decide harness selection for the single Native entry, add the ALWAYS ON badge +
   live dot.
3. **Subtitle wording.** Build shows raw `claude-opus-4-8 · xhigh · Anthropic`. Mockup shows
   humanized `Opus 4.8 · xhigh · Claude` (pretty model name + vendor shown as the harness label
   "Claude", not "Anthropic"). Add a model-id→label map + vendor→harness-label.
4. **Spacing / rhythm.** Tighten search-bar→AGENTS gap; give the footer breathing space; adopt the
   mockup's more generous two-line row rhythm.
5. **Footer.** Stuart's pick (pre-merge) = keep refined: remove "TRANSPORT MATTERS", add breathing
   space, fix the overlap with the row above. Consider the mockup's inline-on-focused-row hints
   (↵ spawn · → config) as the elevated treatment.
6. **Root command center.** "DOMAINS" rows want subtitles + accelerator badges (⌘A on Agents, ⌘,
   on Settings), an "N domains"/"N" count top-right, and a "TYPE TO SEARCH ALL" hint, per mockup #4.
7. **Focused-row craft.** Confirm the accent rail + inline grammar hints on the focused row (the
   Raycast-minimal signature move) are present and match the mockup.

## Process lesson (for next time)
The review gate verified tokens, a11y, and the four states, but NOT fidelity to the approved mockup.
Add a "design-fidelity vs the approved mockup" check to the design reviewer's brief for visual work,
with the mockup file named explicitly.
