---
title: Desktop Cross-OS Keyboard Foundation — Orchestration Record
type: sessions
tags: [helioy-warroom, orchestration, keyboard, keybindings, cross-os, transport-matters]
summary: Audit+research → spec → 4-slice Slice-Build-Loop with adversarial review and human-delegated auto-merge; desktop keybinding foundation shipped as PRs #146-149.
status: active
source: orchestrator
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

# Desktop Cross-OS Keyboard Foundation — Orchestration

Goal: a centralized, DRY, scalable cross-OS keyboard strategy for the Transport Matters **desktop** app. Result: shipped `www/src/keybindings/` foundation across 4 PRs (main @ e6951ff).

## Phasing

1. **Phase 1 (parallel)** — `keymap` warroom: codebase-analyst audited every keyboard surface (25 surfaces → ~/.mdx/projects/transport-matters-keymap-audit.md); deep-research produced the Electron cross-OS strategy (~/.mdx/research/transport-matters-cross-os-keyboard-electron.md). Key correction: accelerators were ALREADY cross-OS-correct (metaKey||ctrlKey) — the value is DRY centralization + per-OS labels + configurability + a11y, not a bug fix.
2. **Phase 2** — `keymap-spec` warroom: frontend-engineer synthesized the strategy spec (~/.mdx/projects/transport-matters-keymap-strategy-spec.md); independent codex architect review (4 findings, 2 Major: $mod precompile DRY hole + bare-Arrow focus-gate safety) → one correction round → verified.
3. **Scope lock (Stuart)** — desktop-only (intercept web app is a separate concept, untouched); native menu dropped; routes/lab/keyboard-zoom-pan out; the ONLY configurable shortcut today = canvas pan/zoom modifier (Shift|Space); build the full scalable foundation now ("seed not ceiling"). Spec revised to this scope.
4. **Phase 3 (Slice Build Loop, auto-merge delegated)** — `keymap-build` warroom, codex engineer + adversarial reviewer per slice. Human delegated merge authority: auto-merge on review-agent sign-off + CI green.

## Slices (each: build → gh verify → primed /code-review+/code-hygiene → fix round → delta verify → CI → squash-merge → cleanup)

- **#146 platform+format** — 4 Minors (??→|| fallback, globalWindow DRY dup, 2 test gaps), fixed, clean.
- **#147 registry+engine+migrate** — CI caught 2 unit regressions (CanvasSurface command center not opening in isolated render) AND reviewer caught a production Blocker (single-slot fullscreen registration → multi-pane Escape broken; e2e missed it). Combined fix round (per-instance registration + multi-pane test + provider in test + dead-code trim), clean.
- **#148 gesture store+dedupe** — clean; reviewer flagged the Space-scroll/button-activation hazard forward to slice 4.
- **#149 settings+persistence** — MoE review (claude full + codex focused on persistence+Space guard). 1 Minor (isRecord triplication) fixed per DRY zero-tolerance. Clean.

## Lessons

- ALWAYS verify "gates green" against CI; require engineers to quote `just test` pass counts (slice 2 engineer reported green while frontend unit tests failed).
- With auto-merge (no human road-test), the review IS the safety gate: weight reviews on regression/double-handling, verify e2e exercises the migrated behavior, and use MoE on the riskiest slice.
- `gh pr merge --delete-branch` cannot delete a local branch held by a worktree; remove the worktree first, then delete the branch.
- tmux reviewer priming: the first Enter after the standby line is commonly swallowed — send a follow-up bare Enter and confirm via capture-pane before queuing skills.
