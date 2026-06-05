# Canvas PR 4 Review — Interactions / Viewer Seam

**PR:** #210 · branch `refactor/canvas-interactions-seam` · HEAD `b9792ad` (pre-PR main `3b4d18f`)
**Scope audited:** Task 4 / "PR 4" slice of `docs/superpowers/plans/2026-07-05-canvas-repo-reset.md`, under the authoritative scoping decision: **seam only, dnd/ folder kept** (the Task 4 folder-rename sketch is deliberately deferred — absent rename is NOT a finding).
**Diff:** +20/-14 across 14 files
**Reviewer:** transport-matters:general:2:7.2 (adversarial, read-only; one authorized throwaway probe, tree left clean)
**Date:** 2026-07-05

## Verdict: **PASS** — 0 blockers / 0 majors / 0 minors

Behavior-preserving. The generic paste-target registry moves out of
`viewers/terminal` into a neutral `interactions/pasteTargetRegistry.ts`; dnd importers
repoint there; the terminal viewer still self-registers; a new `dnd !-> viewers/terminal`
boundary rule is added and empirically bites. Verified by byte-diff of the moved file,
grep sweeps, an injected-violation probe, the named vitest suite, and typecheck.

Evidence of green:
- `pnpm exec vitest run canvasDrop paneDndCallbacks useCanvasDropTargets pasteTargetRegistry sessionCanvasBoundary TerminalPane CapturedRunPane` → **66 passed** (7 files).
- `pnpm --filter @tm/canvas typecheck` → exit 0.

---

## Audit findings (four points, hardest first)

### 1. New `dnd !-> viewers/terminal` rule actually bites — PASS

`sessionCanvasBoundary.test.ts` adds `DND_ROOT` and `TERMINAL_VIEWER_ROOT =
join(VIEWERS_ROOT, "terminal")` and a third case
`boundaryViolations(DND_ROOT, TERMINAL_VIEWER_ROOT)` through the **same** `importGraph`
`boundaryViolations` helper as the existing rules — no allow-list, no exception, no
watering down.

Empirically proven with an authorized probe (injected, run, removed; `git status`
clean after): three throwaway files each importing a viewer path reddened all three
rules simultaneously:
- `dnd/__probe__.ts` importing `../viewers/terminal/terminalSession` →
  `keeps dnd files from importing terminal viewer modules` FAILED with
  `... -> session-canvas/viewers/terminal/terminalSession.ts` (resolved inside
  `TERMINAL_VIEWER_ROOT`).
- `model/__probe__.ts` and `persistence/__probe__.ts` importing `../viewers/registry`
  → the pre-existing model and persistence rules FAILED too. Both still bite.

### 2. Zero `dnd -> viewers/terminal` imports remain — PASS

Grep of `dnd/**` (including test files) for `viewers/terminal` → none. The paste-registry
importers now import `../interactions/pasteTargetRegistry`:
`dnd/canvasDrop.ts`, `dnd/canvasDrop.test.ts`, `dnd/paneDndCallbacks.ts` +
`.test.ts`, `dnd/useCanvasDropTargets.ts` + `.test.tsx`. (`dnd/dockDragSource.ts` and
`dnd/dropTargetStore.ts` each changed one **comment** line referencing the registry's
new name, not an import.)

### 3. Behavior-preserving move, not a rewrite — PASS

- `interactions/pasteTargetRegistry.ts` is **byte-identical** to
  `git show 3b4d18f:.../viewers/terminal/pasteRegistry.ts` (`diff` empty; git tracks it
  as an R100 rename). `registerPasteHandle` / `resolvePasteHandle` / `escapeDropLocator`
  and types are unchanged.
- `viewers/terminal/pasteRegistry.ts` deleted.
- Its test relocated to `interactions/pasteTargetRegistry.test.ts`, changing only the
  import specifier (`./pasteRegistry` → `./pasteTargetRegistry`) and the `describe`
  label — no assertion changed.
- `viewers/terminal/terminalSession.ts` now imports `registerPasteHandle` from
  `../../interactions/pasteTargetRegistry` and still registers the terminal's own paste
  handle (`registerPasteHandle(paneId, (text) => term.paste(text))`). The terminal
  keeps registering itself against the neutral contract.

### 4. No reverse edge / no scope bleed — PASS

- `interactions/` imports neither `dnd/` nor `viewers/` (grep clean) — the seam points
  one way.
- Scope is only the paste-registry move + importer repoints + terminal self-registration
  + the boundary rule. No `CanvasSurface` decomposition (PR 5), no store change (PR 3),
  no launcher change (PR 6). The dnd folder is kept (per the scoping decision).
- No `terminalPasteAdapter.ts` was added; `interactions/` contains only the moved
  `pasteTargetRegistry.ts` (+ its test). The terminal registers directly through
  `registerPasteHandle` — simpler than the plan's deferred adapter sketch, and it
  introduces no new behavior.

---

## Verification note

The one throwaway probe was authorized by the review brief; it was created and removed
inside a single command sequence and `git status` is clean afterward. Otherwise
read-only: `git show` for pre-PR state, no branch switch.
